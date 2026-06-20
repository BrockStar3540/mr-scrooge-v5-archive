#!/usr/bin/env python3
"""V5 live smoke test v2 — pip-high MFE + trend_4h + momentum module + per-cell buckets.

Per trade:
  - entry/exit times, direction, entry price, realized approx_net pips
  - PIP HIGH (MFE — max favorable excursion using M1 candles within hold window)
  - PIP LOW (MAE — max adverse excursion)
  - Hold duration in minutes
  - V5's logged: score, d_cert, m_cert, expected_pips, vol_regime

Per feature at entry (computed from fresh OANDA):
  DIRECTION (24): V5's _FACTOR_DEFS
  MOMENTUM (10):  atr_5m, rvol_5bar, atr_1h, rvol_12bar, bb_width,
                   range_5bar, range_12bar, atr_d_pips, d_range_pips,
                   adr_consumed
  V3 candidate (1): trend_4h (sign of 4-bar H1 return)

Buckets — every test is PER (pair × session):
  - Was the COMPOSITE V5 score on the right side of realized direction?
  - Per-direction-feature accuracy (was its contribution sign right?)
  - Per-momentum-feature correlation with realized pip_high
  - trend_4h accuracy specifically

Output: tables per (pair × session) bucket. NO global rollups.
"""
import os, re, json, urllib.parse, urllib.request
from pathlib import Path
import numpy as np
import pandas as pd

PAIRS = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
PIP_SIZE = {
    "AUD_JPY": 0.01, "EUR_JPY": 0.01, "USD_JPY": 0.01,
    "AUD_USD": 0.0001, "EUR_USD": 0.0001, "GBP_USD": 0.0001,
    "USD_CAD": 0.0001, "USD_CHF": 0.0001,
}

LOG_FP = Path("/tmp/v5_today_trades.log")

# V5 _FACTOR_DEFS exactly as in modules/signals/direction.py
V5_DIR_FACTORS = [
    ("h1_ret_1bar",       +17.61), ("rsi_slope",         +10.41),
    ("zscore_1h",          +8.73), ("h1_ret_4bar",        +7.35),
    ("d_ret",              +7.09), ("ema20_1h_dist_pct",  +6.37),
    ("pdh_dist_pips",      +5.95), ("pdl_dist_pips",      +5.88),
    ("pdl_dist_atr_pct",   +5.69), ("pdh_dist_atr_pct",   +5.62),
    ("rsi14",              +4.79), ("htf_pct_20",         +1.91),
    ("htf_pct_60",         +1.01),
    ("ema20_dist_pct",     -0.57), ("bb_pos",             -0.55),
    ("zscore_5m",          -0.55), ("ema5_dist_pips",     -0.53),
    ("ret_5m",             -0.50), ("ret_15m",            -0.45),
    ("ret_1h",             -0.44), ("ret_30m",            -0.41),
    ("ema50_dist_pct",     -0.39), ("close_pos_daily",    -0.30),
    ("ema_cross_pips",     -0.27),
]
V5_MOM_FEATURES = [
    "atr_5m","rvol_5bar","atr_1h","rvol_12bar","bb_width",
    "range_5bar","range_12bar","atr_d_pips","d_range_pips","adr_consumed",
]
FALLBACK_ANCHORS = {
    "h1_ret_1bar":      (-12.0,  12.0),  "rsi_slope":         ( -9.0,  9.0),
    "zscore_1h":        ( -2.0,   2.0),  "h1_ret_4bar":       (-20.0, 20.0),
    "d_ret":            (-40.0,  40.0),  "ema20_1h_dist_pct": ( -0.15, 0.15),
    "pdh_dist_pips":    (-20.0,  20.0),  "pdl_dist_pips":     (-20.0, 20.0),
    "pdh_dist_atr_pct": ( -3.0,   3.0),  "pdl_dist_atr_pct":  ( -3.0,  3.0),
    "rsi14":            ( 35.0,  65.0),  "htf_pct_20":        ( -3.0,  3.0),
    "htf_pct_60":       ( -3.0,   3.0),
    "ema20_dist_pct":   ( -0.10,  0.10), "bb_pos":            (  0.1,  0.9),
    "zscore_5m":        ( -2.0,   2.0),  "ema5_dist_pips":    ( -5.0,  5.0),
    "ret_5m":           ( -3.0,   3.0),  "ret_15m":           ( -5.0,  5.0),
    "ret_30m":          ( -8.0,   8.0),  "ret_1h":            (-12.0, 12.0),
    "ema50_dist_pct":   ( -0.20,  0.20), "close_pos_daily":   (  0.1,  0.9),
    "ema_cross_pips":   ( -3.0,   3.0),
}


def session_from_hour(h: int) -> str:
    """V5 coarse session mapping."""
    if 22 <= h or h <= 5:  return "asia"
    if 6 <= h <= 12:       return "london"
    if 13 <= h <= 21:      return "ny"
    return "asia"


def safe_norm(v, lo, hi):
    if hi <= lo: return 0.0
    return float(np.clip(2 * (v - lo) / (hi - lo) - 1, -1, 1))


def pull_candles(pair, granularity, count, from_time=None, to_time=None):
    token = os.environ["OANDA_API_TOKEN"]
    base  = os.environ.get("OANDA_API_URL", "https://api-fxtrade.oanda.com")
    params = {"granularity": granularity, "price": "M"}
    if from_time and to_time:
        params["from"] = from_time; params["to"] = to_time
    else:
        params["count"] = count
    url = f"{base}/v3/instruments/{pair}/candles?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    rows = []
    for c in data.get("candles", []):
        if not c.get("complete"): continue
        m = c["mid"]
        rows.append({
            "time":   pd.Timestamp(c["time"], tz="UTC"),
            "open":   float(m["o"]), "high": float(m["h"]),
            "low":    float(m["l"]), "close":float(m["c"]),
            "volume": int(c.get("volume", 0)),
        })
    return pd.DataFrame(rows).set_index("time").sort_index()


def parse_trades(log_fp):
    sig_re  = re.compile(r"(\S+ \S+) INFO v5\.engine  SIGNAL (\w+) (\w+) \| score=([\-\d.]+) d_cert=([\d.]+) m_cert=([\d.]+) expected=([\d.]+)p vol=(\w+)")
    ent_re  = re.compile(r"(\S+ \S+) INFO v5\.engine  ENTERED (\w+) (\w+) @ ([\d.]+) \| (\d+) units \| .* trade_id=(\d*)")
    exit_re = re.compile(r"(\S+ \S+) INFO v5\.engine  EXIT .* (\w+) \| trade_id=(\d*) \| approx_net=([\-\d.]+)p")
    signals, entries, exits = [], {}, {}
    for line in log_fp.read_text().splitlines():
        if "SIGNAL" in line:
            m = sig_re.search(line)
            if m:
                ts, pair, direction, score, d, mom, exp, vol = m.groups()
                signals.append({
                    "time": pd.Timestamp(ts, tz="UTC"),
                    "pair": pair, "direction": direction,
                    "score_logged": float(score),
                    "d_cert": float(d), "m_cert": float(mom),
                    "expected_pips_logged": float(exp),
                    "vol_regime_logged": vol,
                })
        elif "ENTERED" in line:
            m = ent_re.search(line)
            if m:
                ts, pair, direction, price, units, tid = m.groups()
                entries[(pair, ts)] = {
                    "entry_time": pd.Timestamp(ts, tz="UTC"),
                    "entry_price": float(price), "units": int(units),
                    "trade_id": tid or None,
                }
        elif "EXIT" in line:
            m = exit_re.search(line)
            if m:
                ts, pair, tid, net = m.groups()
                if tid:
                    exits[tid] = {
                        "exit_time": pd.Timestamp(ts, tz="UTC"),
                        "approx_net_pips": float(net),
                    }
    trades = []
    for sig in signals:
        for (pair, ts), ent in entries.items():
            if pair == sig["pair"] and abs((ent["entry_time"] - sig["time"]).total_seconds()) < 2:
                td = {**sig, **ent}
                tid = ent.get("trade_id")
                if tid and tid in exits:
                    td.update(exits[tid])
                trades.append(td)
                break
    return trades


def compute_pip_high_low(m1: pd.DataFrame, entry_time, exit_time, entry_price, direction, pip):
    """Pip MFE (favorable excursion) and pip MAE during hold window from M1."""
    sub = m1.loc[entry_time:exit_time]
    if len(sub) == 0:
        return None, None
    if direction == "long":
        pip_high = (sub["high"].max() - entry_price) / pip
        pip_low  = (sub["low"].min()  - entry_price) / pip
    else:
        pip_high = (entry_price - sub["low"].min())  / pip   # MFE for short = price drop
        pip_low  = (entry_price - sub["high"].max()) / pip   # MAE = price rise
    return float(pip_high), float(pip_low)


def compute_features_at(m5, h1, d1, entry_time, pip):
    """Compute V5 direction + momentum + trend_4h features at entry."""
    m5_pos = m5.index.get_indexer([entry_time], method="ffill")[0]
    h1_pos = h1.index.get_indexer([entry_time], method="ffill")[0]
    d1_pos = d1.index.get_indexer([entry_time], method="ffill")[0]
    if m5_pos < 100 or h1_pos < 50 or d1_pos < 60:
        return None
    m5_close = m5["close"].iloc[m5_pos]
    h1_close = h1["close"].iloc[h1_pos]
    f = {}
    # ── direction features ──
    f["h1_ret_1bar"] = (h1_close - h1["close"].iloc[h1_pos-1]) / pip
    f["h1_ret_4bar"] = (h1_close - h1["close"].iloc[h1_pos-4]) / pip
    # rsi14 + slope (M5)
    delta = m5["close"].iloc[m5_pos-13:m5_pos+1].diff()
    up = delta.clip(lower=0).rolling(14).mean()
    dn = (-delta.clip(upper=0)).rolling(14).mean()
    rsi = 100 - 100 / (1 + up / (dn + 1e-12))
    f["rsi14"] = float(rsi.iloc[-1])
    f["rsi_slope"] = float(rsi.iloc[-1] - rsi.iloc[-4]) if len(rsi) >= 4 else 0
    win20 = m5["close"].iloc[m5_pos-19:m5_pos+1]
    f["zscore_1h"] = float((m5_close - win20.mean()) / (win20.std() + 1e-12))
    win5 = m5["close"].iloc[m5_pos-4:m5_pos+1]
    f["zscore_5m"] = float((m5_close - win5.mean()) / (win5.std() + 1e-12))
    d_close_prev = d1["close"].iloc[d1_pos-1] if d1_pos >= 1 else m5_close
    f["d_ret"] = (d1["close"].iloc[d1_pos] - d_close_prev) / pip
    h1_ema20 = h1["close"].iloc[:h1_pos+1].ewm(span=20).mean().iloc[-1]
    f["ema20_1h_dist_pct"] = (h1_close - h1_ema20) / h1_close
    pdh = d1["high"].iloc[d1_pos - 1]; pdl = d1["low"].iloc[d1_pos - 1]
    f["pdh_dist_pips"] = (m5_close - pdh) / pip
    f["pdl_dist_pips"] = (m5_close - pdl) / pip
    # ATR for ATR-normalization
    tr = pd.concat([
        m5["high"].iloc[m5_pos-13:m5_pos+1] - m5["low"].iloc[m5_pos-13:m5_pos+1],
        (m5["high"].iloc[m5_pos-13:m5_pos+1] - m5["close"].shift(1).iloc[m5_pos-13:m5_pos+1]).abs(),
        (m5["low"].iloc[m5_pos-13:m5_pos+1]  - m5["close"].shift(1).iloc[m5_pos-13:m5_pos+1]).abs(),
    ], axis=1).max(axis=1)
    atr5_pips = float(tr.mean() / pip if pip > 0 else tr.mean())
    f["pdh_dist_atr_pct"] = f["pdh_dist_pips"] / (atr5_pips + 1e-6)
    f["pdl_dist_atr_pct"] = f["pdl_dist_pips"] / (atr5_pips + 1e-6)
    f["htf_pct_20"] = (d1["close"].iloc[d1_pos] - d1["close"].iloc[d1_pos - 20]) / d1["close"].iloc[d1_pos] * 100
    f["htf_pct_60"] = (d1["close"].iloc[d1_pos] - d1["close"].iloc[d1_pos - 60]) / d1["close"].iloc[d1_pos] * 100
    ema20_m5 = m5["close"].iloc[:m5_pos+1].ewm(span=20).mean().iloc[-1]
    ema50_m5 = m5["close"].iloc[:m5_pos+1].ewm(span=50).mean().iloc[-1]
    ema5_m5  = m5["close"].iloc[:m5_pos+1].ewm(span=5).mean().iloc[-1]
    f["ema20_dist_pct"] = (m5_close - ema20_m5) / m5_close
    f["ema50_dist_pct"] = (m5_close - ema50_m5) / m5_close
    f["ema5_dist_pips"] = (m5_close - ema5_m5) / pip
    bb_win = m5["close"].iloc[m5_pos-19:m5_pos+1]
    bb_mean = bb_win.mean(); bb_std = bb_win.std()
    bb_upper = bb_mean + 2 * bb_std; bb_lower = bb_mean - 2 * bb_std
    f["bb_pos"] = float((m5_close - bb_lower) / (bb_upper - bb_lower + 1e-12))
    f["ret_5m"]  = (m5_close - m5["close"].iloc[m5_pos-1]) / pip
    f["ret_15m"] = (m5_close - m5["close"].iloc[m5_pos-3]) / pip
    f["ret_30m"] = (m5_close - m5["close"].iloc[m5_pos-6]) / pip
    f["ret_1h"]  = (m5_close - m5["close"].iloc[m5_pos-12]) / pip
    today_high = m5["high"].iloc[max(0, m5_pos-288):m5_pos+1].max()
    today_low  = m5["low"].iloc[max(0, m5_pos-288):m5_pos+1].min()
    f["close_pos_daily"] = float((m5_close - today_low) / (today_high - today_low + 1e-12))
    ema12 = m5["close"].iloc[:m5_pos+1].ewm(span=12).mean().iloc[-1]
    ema26 = m5["close"].iloc[:m5_pos+1].ewm(span=26).mean().iloc[-1]
    f["ema_cross_pips"] = (ema12 - ema26) / pip

    # ── momentum module features ──
    f["atr_5m"] = atr5_pips
    f["rvol_5bar"]  = float(m5["volume"].iloc[m5_pos-4:m5_pos+1].mean() / (m5["volume"].iloc[m5_pos-100:m5_pos+1].mean() + 1e-6))
    f["rvol_12bar"] = float(m5["volume"].iloc[m5_pos-11:m5_pos+1].mean() / (m5["volume"].iloc[m5_pos-100:m5_pos+1].mean() + 1e-6))
    # atr_1h
    h1_tr = pd.concat([
        h1["high"].iloc[h1_pos-13:h1_pos+1] - h1["low"].iloc[h1_pos-13:h1_pos+1],
        (h1["high"].iloc[h1_pos-13:h1_pos+1] - h1["close"].shift(1).iloc[h1_pos-13:h1_pos+1]).abs(),
        (h1["low"].iloc[h1_pos-13:h1_pos+1]  - h1["close"].shift(1).iloc[h1_pos-13:h1_pos+1]).abs(),
    ], axis=1).max(axis=1)
    f["atr_1h"] = float(h1_tr.mean() / pip)
    f["bb_width"] = float((bb_upper - bb_lower) / pip)
    f["range_5bar"]  = float((m5["high"].iloc[m5_pos-4:m5_pos+1].max() - m5["low"].iloc[m5_pos-4:m5_pos+1].min()) / pip)
    f["range_12bar"] = float((m5["high"].iloc[m5_pos-11:m5_pos+1].max() - m5["low"].iloc[m5_pos-11:m5_pos+1].min()) / pip)
    f["atr_d_pips"]  = float((d1["high"].iloc[d1_pos-13:d1_pos+1] - d1["low"].iloc[d1_pos-13:d1_pos+1]).rolling(14).mean().iloc[-1] / pip)
    d_high = d1["high"].iloc[d1_pos]; d_low = d1["low"].iloc[d1_pos]
    f["d_range_pips"] = float((d_high - d_low) / pip)
    f["adr_consumed"] = f["d_range_pips"] / (f["atr_d_pips"] + 1e-6)

    # ── trend_4h (V3 candidate) ──
    f["trend_4h"] = int(np.sign(f["h1_ret_4bar"]))

    return f


def main():
    print("V5 LIVE SMOKE TEST V2 — per (pair × session) buckets + pip-high MFE\n", flush=True)
    print("Pulling fresh OANDA candles (M1+M5+H1+D)...", flush=True)
    data = {}
    for pair in PAIRS:
        m1 = pull_candles(pair, "M1", 5000)
        m5 = pull_candles(pair, "M5", 1000)
        h1 = pull_candles(pair, "H1", 300)
        d1 = pull_candles(pair, "D",  150)
        data[pair] = {"m1": m1, "m5": m5, "h1": h1, "d1": d1}
        print(f"  {pair}: m1={len(m1)} m5={len(m5)} h1={len(h1)} d1={len(d1)}", flush=True)

    trades = parse_trades(LOG_FP)
    print(f"\nParsed {len(trades)} trades", flush=True)

    rows = []
    for t in trades:
        if "approx_net_pips" not in t: continue
        pair = t["pair"]
        if pair not in data: continue
        pip = PIP_SIZE[pair]
        feats = compute_features_at(data[pair]["m5"], data[pair]["h1"], data[pair]["d1"],
                                     t["entry_time"], pip)
        if feats is None: continue
        pip_high, pip_low = compute_pip_high_low(
            data[pair]["m1"], t["entry_time"], t["exit_time"],
            t["entry_price"], t["direction"], pip)
        if pip_high is None: continue
        hold_min = (t["exit_time"] - t["entry_time"]).total_seconds() / 60
        realized_sign = (1 if t["approx_net_pips"] > 0 else -1) if t["direction"] == "long" \
                        else (-1 if t["approx_net_pips"] > 0 else 1)
        session = session_from_hour(t["entry_time"].hour)
        # per-direction-feature votes
        votes = {}
        for fname, signed_w in V5_DIR_FACTORS:
            v = feats.get(fname)
            if v is None: continue
            lo, hi = FALLBACK_ANCHORS[fname]
            norm = safe_norm(v, lo, hi)
            contrib = norm * signed_w
            votes[fname] = (1 if contrib > 0 else (-1 if contrib < 0 else 0))
        # trend_4h sign
        votes["trend_4h"] = int(feats["trend_4h"])
        # composite vote
        composite_vote = 1 if t["score_logged"] > 0 else -1
        rows.append({
            "pair": pair, "session": session, "direction": t["direction"],
            "entry_time": t["entry_time"], "exit_time": t["exit_time"],
            "hold_min": hold_min,
            "approx_net_pips": t["approx_net_pips"],
            "pip_high": pip_high, "pip_low": pip_low,
            "realized_sign": realized_sign,
            "score_logged": t["score_logged"],
            "expected_pips_logged": t["expected_pips_logged"],
            "votes": votes,
            "feats": feats,
            "win": t["approx_net_pips"] > 0,
            "composite_vote": composite_vote,
        })

    print(f"Complete records: {len(rows)}\n", flush=True)
    if not rows: return

    # ── per-(pair × session) bucket aggregation ──
    out_lines = []
    out_lines.append("=" * 100)
    out_lines.append("V5 LIVE SMOKE TEST V2 — PER (pair × session) BUCKETS")
    out_lines.append("=" * 100)
    out_lines.append("")
    out_lines.append(f"  Total trades analyzed: {len(rows)}")
    out_lines.append(f"  Total wins: {sum(1 for r in rows if r['win'])} ({sum(1 for r in rows if r['win'])/len(rows)*100:.0f}%)")
    out_lines.append("")

    # Group by bucket
    buckets = {}
    for r in rows:
        key = (r["pair"], r["session"])
        buckets.setdefault(key, []).append(r)

    # ── Per-bucket trade table + per-feature accuracy ──
    all_feat_names = [f for f, _ in V5_DIR_FACTORS] + ["trend_4h"]
    for (pair, sess), bucket_rows in sorted(buckets.items()):
        out_lines.append("─" * 100)
        out_lines.append(f"BUCKET: {pair} / {sess}  ({len(bucket_rows)} trades)")
        out_lines.append("─" * 100)
        # trade-by-trade table
        out_lines.append(f"  {'entry':<17}  {'dir':<5}  {'hold_m':>6}  {'pip_high':>8}  {'pip_low':>7}  {'net':>6}  "
                          f"{'pred_pips':>9}  {'score':>7}  {'realized':>8}  {'win?':>4}")
        for r in bucket_rows:
            out_lines.append(f"  {str(r['entry_time'])[:16]:<17}  {r['direction']:<5}  "
                              f"{r['hold_min']:>6.1f}  {r['pip_high']:>+8.2f}  {r['pip_low']:>+7.2f}  "
                              f"{r['approx_net_pips']:>+6.2f}  "
                              f"{r['expected_pips_logged']:>9.2f}  "
                              f"{r['score_logged']:>+7.3f}  {r['realized_sign']:>+8d}  "
                              f"{'✓' if r['win'] else '✗':>4}")
        # composite accuracy in bucket
        comp_right = sum(1 for r in bucket_rows if r["composite_vote"] == r["realized_sign"])
        out_lines.append(f"  V5 COMPOSITE in bucket: {comp_right}/{len(bucket_rows)} = {comp_right/len(bucket_rows)*100:.0f}%")
        # per-feature accuracy in bucket
        out_lines.append(f"  Per-feature accuracy in this bucket:")
        out_lines.append(f"    {'feature':<22}  {'agree':>5}  {'dis':>4}  {'n':>3}  {'acc':>6}")
        feat_in_bucket = {}
        for f in all_feat_names:
            ag = 0; dis = 0; n = 0
            for r in bucket_rows:
                v = r["votes"].get(f)
                if v is None or v == 0: continue
                n += 1
                if v == r["realized_sign"]: ag += 1
                else: dis += 1
            if n > 0:
                feat_in_bucket[f] = (ag, dis, n, ag/n)
        # sort by accuracy
        for f, (ag, dis, n, acc) in sorted(feat_in_bucket.items(), key=lambda x: -x[1][3]):
            out_lines.append(f"    {f:<22}  {ag:>5}  {dis:>4}  {n:>3}  {acc*100:>5.0f}%")
        # momentum: predicted vs realized pip_high
        out_lines.append(f"  Momentum module accuracy (predicted expected_pips vs realized pip_high):")
        for r in bucket_rows:
            pct_err = (r["pip_high"] - r["expected_pips_logged"]) / (r["expected_pips_logged"] + 1e-6) * 100
            out_lines.append(f"    {str(r['entry_time'])[11:16]}  predicted={r['expected_pips_logged']:.1f}p  realized_high={r['pip_high']:.1f}p  ({pct_err:+.0f}% vs prediction)")
        out_lines.append("")

    out_path = Path("/tmp/v5_smoke/smoke_v2.txt")
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text("\n".join(out_lines))
    # also save raw rows as JSON for follow-on
    json_rows = []
    for r in rows:
        j = {k: v for k, v in r.items() if k != "feats"}
        for k, v in j.items():
            if isinstance(v, pd.Timestamp): j[k] = str(v)
        json_rows.append(j)
    Path("/tmp/v5_smoke/smoke_v2.json").write_text(json.dumps(json_rows, indent=2, default=str))
    print(f"wrote {out_path}")
    print(f"      /tmp/v5_smoke/smoke_v2.json")


if __name__ == "__main__":
    main()
