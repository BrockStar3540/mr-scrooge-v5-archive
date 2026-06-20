#!/usr/bin/env python3
"""V5 live smoke test v3 — extends v2 with momentum-module magnitude tests +
HTF alignment composite + V3 candidates.

Adds per-bucket:
  - Pearson correlation of EACH momentum feature with realized pip_high
  - Whether HIGH feature value (above bucket median) coincides with above-median pip_high
  - V5's expected_pips → pip_high calibration slope + intercept per bucket
  - HTF alignment composite (signed -4..+4) as a direction vote
  - V3 candidates: wall_frac, ema50_atr_frac, atr_conc as direction-or-magnitude tests

Direction-vote tests (same as v2): for each feature in:
    V5 24 direction factors + trend_4h + htf_align_signed + V3 candidates
Momentum/magnitude tests (NEW):
    For 10 momentum features + V5's expected_pips:
      - correlation(feature_value, realized_pip_high)
      - HIGH-vs-LOW pip_high comparison
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
V3_CANDIDATES = ["wall_frac","ema50_atr_frac","atr_conc"]
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
    if 22 <= h or h <= 5:  return "asia"
    if 6 <= h <= 12:       return "london"
    if 13 <= h <= 21:      return "ny"
    return "asia"


def safe_norm(v, lo, hi):
    if hi <= lo: return 0.0
    return float(np.clip(2 * (v - lo) / (hi - lo) - 1, -1, 1))


def pull_candles(pair, granularity, count):
    token = os.environ["OANDA_API_TOKEN"]
    base  = os.environ.get("OANDA_API_URL", "https://api-fxtrade.oanda.com")
    url = f"{base}/v3/instruments/{pair}/candles?" + urllib.parse.urlencode({
        "count": count, "granularity": granularity, "price": "M",
    })
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    rows = []
    for c in data.get("candles", []):
        if not c.get("complete"): continue
        m = c["mid"]
        rows.append({"time": pd.Timestamp(c["time"], tz="UTC"),
                     "open": float(m["o"]), "high": float(m["h"]),
                     "low":  float(m["l"]), "close":float(m["c"]),
                     "volume": int(c.get("volume", 0))})
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
                entries[(pair, ts)] = {"entry_time": pd.Timestamp(ts, tz="UTC"),
                                       "entry_price": float(price), "units": int(units),
                                       "trade_id": tid or None}
        elif "EXIT" in line:
            m = exit_re.search(line)
            if m:
                ts, pair, tid, net = m.groups()
                if tid:
                    exits[tid] = {"exit_time": pd.Timestamp(ts, tz="UTC"),
                                  "approx_net_pips": float(net)}
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


def compute_pip_high_low(m1, entry_time, exit_time, entry_price, direction, pip):
    sub = m1.loc[entry_time:exit_time]
    if len(sub) == 0: return None, None
    if direction == "long":
        pip_high = (sub["high"].max() - entry_price) / pip
        pip_low  = (sub["low"].min()  - entry_price) / pip
    else:
        pip_high = (entry_price - sub["low"].min())  / pip
        pip_low  = (entry_price - sub["high"].max()) / pip
    return float(pip_high), float(pip_low)


def compute_features_at(m5, h1, d1, entry_time, pip):
    m5_pos = m5.index.get_indexer([entry_time], method="ffill")[0]
    h1_pos = h1.index.get_indexer([entry_time], method="ffill")[0]
    d1_pos = d1.index.get_indexer([entry_time], method="ffill")[0]
    if m5_pos < 100 or h1_pos < 50 or d1_pos < 60: return None
    m5_close = m5["close"].iloc[m5_pos]
    h1_close = h1["close"].iloc[h1_pos]
    f = {}
    # direction features (24)
    f["h1_ret_1bar"] = (h1_close - h1["close"].iloc[h1_pos-1]) / pip
    f["h1_ret_4bar"] = (h1_close - h1["close"].iloc[h1_pos-4]) / pip
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
    tr = pd.concat([
        m5["high"].iloc[m5_pos-13:m5_pos+1] - m5["low"].iloc[m5_pos-13:m5_pos+1],
        (m5["high"].iloc[m5_pos-13:m5_pos+1] - m5["close"].shift(1).iloc[m5_pos-13:m5_pos+1]).abs(),
        (m5["low"].iloc[m5_pos-13:m5_pos+1]  - m5["close"].shift(1).iloc[m5_pos-13:m5_pos+1]).abs(),
    ], axis=1).max(axis=1)
    atr5_pips = float(tr.mean() / pip)
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
    # momentum module (10)
    f["atr_5m"]      = atr5_pips
    f["rvol_5bar"]   = float(m5["volume"].iloc[m5_pos-4:m5_pos+1].mean() / (m5["volume"].iloc[m5_pos-100:m5_pos+1].mean() + 1e-6))
    f["rvol_12bar"]  = float(m5["volume"].iloc[m5_pos-11:m5_pos+1].mean() / (m5["volume"].iloc[m5_pos-100:m5_pos+1].mean() + 1e-6))
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
    # V3 candidates
    f["wall_frac"] = float(min(abs(f["pdh_dist_pips"]), abs(f["pdl_dist_pips"])) / (atr5_pips + 1e-6))
    f["ema50_atr_frac"] = float(f["ema50_dist_pct"] * 10000.0 / (atr5_pips + 1e-6))
    # atr_conc = atr_5m * 12 / atr_1h — captures whether vol is concentrated in this M5 bar relative to the hour
    f["atr_conc"] = float(atr5_pips * 12 / (f["atr_1h"] + 1e-6))
    # trend signals
    f["trend_1h"] = int(np.sign(f["h1_ret_1bar"]))
    f["trend_4h"] = int(np.sign(f["h1_ret_4bar"]))
    # HTF signed alignment composite
    htf_up = ((f["trend_1h"] > 0)
              + (f["trend_4h"] > 0)
              + (f["htf_pct_20"] > 0)
              + (f["htf_pct_60"] > 0))
    htf_dn = ((f["trend_1h"] < 0)
              + (f["trend_4h"] < 0)
              + (f["htf_pct_20"] < 0)
              + (f["htf_pct_60"] < 0))
    f["htf_align_signed"] = int(htf_up - htf_dn)  # -4..+4
    return f


def safe_corr(a, b):
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0: return None
    return float(np.corrcoef(a, b)[0, 1])


def main():
    print("V5 LIVE SMOKE TEST V3 — direction + momentum + V3 + HTF composite, per bucket\n", flush=True)
    print("Pulling fresh OANDA candles...", flush=True)
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
        realized_sign = (1 if t["approx_net_pips"] > 0 else -1) if t["direction"] == "long" \
                        else (-1 if t["approx_net_pips"] > 0 else 1)
        session = session_from_hour(t["entry_time"].hour)
        # direction votes (V5 24 + extras)
        votes = {}
        for fname, signed_w in V5_DIR_FACTORS:
            v = feats.get(fname)
            if v is None: continue
            lo, hi = FALLBACK_ANCHORS[fname]
            norm = safe_norm(v, lo, hi)
            contrib = norm * signed_w
            votes[fname] = (1 if contrib > 0 else (-1 if contrib < 0 else 0))
        votes["trend_4h"] = int(feats["trend_4h"])
        votes["trend_1h"] = int(feats["trend_1h"])
        votes["htf_align_signed"] = int(np.sign(feats["htf_align_signed"]))
        # V3 candidate votes (interpret sign as direction signal; wall_frac/ema50_atr_frac are signed)
        votes["wall_frac_sign"] = int(np.sign(feats["wall_frac"]))  # always positive — not directional really
        votes["ema50_atr_frac_sign"] = int(np.sign(feats["ema50_atr_frac"]))
        rows.append({
            "pair": pair, "session": session, "direction": t["direction"],
            "entry_time": t["entry_time"], "exit_time": t["exit_time"],
            "approx_net_pips": t["approx_net_pips"],
            "pip_high": pip_high, "pip_low": pip_low,
            "realized_sign": realized_sign,
            "score_logged": t["score_logged"],
            "expected_pips_logged": t["expected_pips_logged"],
            "votes": votes, "feats": feats,
            "win": t["approx_net_pips"] > 0,
        })

    if not rows:
        print("no trades"); return
    print(f"Complete records: {len(rows)}", flush=True)

    # ── aggregation per bucket ──
    buckets = {}
    for r in rows:
        buckets.setdefault((r["pair"], r["session"]), []).append(r)

    L = []
    L.append("="*100)
    L.append("V5 LIVE SMOKE V3 — direction + momentum-magnitude + HTF composite + V3, per bucket")
    L.append("="*100)
    L.append(f"\n  trades: {len(rows)}   wins: {sum(1 for r in rows if r['win'])}\n")

    direction_features = [f for f, _ in V5_DIR_FACTORS] + ["trend_1h","trend_4h","htf_align_signed"]
    magnitude_features = V5_MOM_FEATURES + ["wall_frac","ema50_atr_frac","atr_conc","expected_pips_logged"]

    for (pair, sess), brs in sorted(buckets.items()):
        L.append("─"*100)
        L.append(f"BUCKET: {pair} / {sess}  ({len(brs)} trades)")
        L.append("─"*100)
        # 1) trade table (compact)
        L.append(f"  {'entry':<17}  {'dir':<5}  {'pip_high':>8}  {'pip_low':>7}  {'net':>6}  "
                 f"{'pred':>5}  {'score':>7}  {'win?':>4}")
        for r in brs:
            L.append(f"  {str(r['entry_time'])[:16]:<17}  {r['direction']:<5}  "
                     f"{r['pip_high']:>+8.2f}  {r['pip_low']:>+7.2f}  {r['approx_net_pips']:>+6.2f}  "
                     f"{r['expected_pips_logged']:>5.1f}  {r['score_logged']:>+7.3f}  "
                     f"{'WIN' if r['win'] else 'LOSS':>4}")
        # 2) DIRECTION FEATURE ACCURACY (vote vs realized sign)
        L.append(f"\n  ── DIRECTION feature accuracy (vote vs realized) ──")
        L.append(f"    {'feature':<22}  {'agree':>5}  {'dis':>4}  {'n':>3}  {'acc':>6}")
        feat_acc = {}
        for f in direction_features:
            ag = dis = n = 0
            for r in brs:
                v = r["votes"].get(f)
                if v is None or v == 0: continue
                n += 1
                if v == r["realized_sign"]: ag += 1
                else: dis += 1
            if n: feat_acc[f] = (ag, dis, n, ag/n)
        for f, (ag, dis, n, acc) in sorted(feat_acc.items(), key=lambda x: -x[1][3]):
            L.append(f"    {f:<22}  {ag:>5}  {dis:>4}  {n:>3}  {acc*100:>5.0f}%")
        # 3) MOMENTUM/MAGNITUDE feature CORRELATIONS with pip_high
        L.append(f"\n  ── MAGNITUDE feature corr with realized pip_high ──")
        pip_highs = [r["pip_high"] for r in brs]
        L.append(f"    {'feature':<22}  {'corr':>7}  {'low_pip_high':>13}  {'high_pip_high':>14}")
        if len(brs) >= 2:
            for f in magnitude_features:
                vals = [r["feats"].get(f) if f != "expected_pips_logged" else r["expected_pips_logged"]
                        for r in brs]
                vals = [v for v in vals if v is not None]
                if len(vals) < 2: continue
                c = safe_corr(vals, pip_highs[:len(vals)])
                # median split
                med = float(np.median(vals))
                lows  = [ph for v, ph in zip(vals, pip_highs[:len(vals)]) if v <= med]
                highs = [ph for v, ph in zip(vals, pip_highs[:len(vals)]) if v >  med]
                lo_pip = np.mean(lows) if lows else float("nan")
                hi_pip = np.mean(highs) if highs else float("nan")
                cs = f"{c:+.3f}" if c is not None else "—"
                L.append(f"    {f:<22}  {cs:>7}  {lo_pip:>12.2f}p  {hi_pip:>13.2f}p")
        else:
            L.append("    (need >=2 trades to compute correlations)")
        # 4) V5 expected_pips → pip_high calibration
        if len(brs) >= 2:
            ep = np.array([r["expected_pips_logged"] for r in brs])
            ph = np.array([r["pip_high"] for r in brs])
            if ep.std() > 0:
                # OLS slope (no intercept = how much of pip_high V5 captures per unit prediction)
                slope_no_intercept = float((ep * ph).sum() / (ep * ep).sum())
                # OLS slope with intercept
                cov = float(np.cov(ep, ph, bias=False)[0,1])
                slope = cov / (ep.var(ddof=1) + 1e-12)
                intercept = float(ph.mean() - slope * ep.mean())
                L.append(f"\n  ── V5 expected_pips → realized pip_high calibration ──")
                L.append(f"    OLS slope (with intercept):  {slope:+.3f}   intercept:  {intercept:+.2f}p")
                L.append(f"    OLS slope (origin-forced):   {slope_no_intercept:+.3f}")
                L.append(f"    perfect calibration would be slope=+1, intercept=0")
                L.append(f"    today: V5 predicts {ep.mean():.1f}p mean, realized {ph.mean():.2f}p mean "
                         f"({(ph.mean()/ep.mean()-1)*100:+.0f}% off)")
        L.append("")

    out_path = Path("/tmp/v5_smoke/smoke_v3.txt")
    out_path.write_text("\n".join(L))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
