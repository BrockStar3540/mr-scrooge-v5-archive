#!/usr/bin/env python3
"""V5 live smoke test v5 — aggregator amplification PER BUCKET.

For each (pair × session) bucket, compute aggregator amplification on
direction features WITHIN that bucket only. Show the data for ALL buckets,
including small ones — let the user see what's there.

Per bucket:
  - Trade-by-trade table with aggregator values per trade
  - For buckets with >=3 trades: per-aggregator HIGH/LOW split + amplification
  - For 2-trade buckets: just the value comparison
  - For 1-trade buckets: just show the trade

NO global aggregation. NO cross-bucket pooling.
"""
import os, re, json, urllib.parse, urllib.request
from pathlib import Path
import numpy as np
import pandas as pd

PAIRS = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
PIP_SIZE = {"AUD_JPY":0.01,"EUR_JPY":0.01,"USD_JPY":0.01,"AUD_USD":0.0001,
            "EUR_USD":0.0001,"GBP_USD":0.0001,"USD_CAD":0.0001,"USD_CHF":0.0001}
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
DIRECTION_FEATURES = [f for f, _ in V5_DIR_FACTORS] + ["trend_1h","trend_4h","htf_align_signed"]
AGGREGATORS = ["wall_frac","ema50_atr_frac","atr_conc","htf_align_best",
               "adr_consumed","atr_h1_relative","d_cert","m_cert"]
FALLBACK_ANCHORS = {
    "h1_ret_1bar":(-12.0,12.0),"rsi_slope":(-9.0,9.0),"zscore_1h":(-2.0,2.0),
    "h1_ret_4bar":(-20.0,20.0),"d_ret":(-40.0,40.0),"ema20_1h_dist_pct":(-0.15,0.15),
    "pdh_dist_pips":(-20.0,20.0),"pdl_dist_pips":(-20.0,20.0),"pdh_dist_atr_pct":(-3.0,3.0),
    "pdl_dist_atr_pct":(-3.0,3.0),"rsi14":(35.0,65.0),"htf_pct_20":(-3.0,3.0),
    "htf_pct_60":(-3.0,3.0),"ema20_dist_pct":(-0.10,0.10),"bb_pos":(0.1,0.9),
    "zscore_5m":(-2.0,2.0),"ema5_dist_pips":(-5.0,5.0),"ret_5m":(-3.0,3.0),
    "ret_15m":(-5.0,5.0),"ret_30m":(-8.0,8.0),"ret_1h":(-12.0,12.0),
    "ema50_dist_pct":(-0.20,0.20),"close_pos_daily":(0.1,0.9),"ema_cross_pips":(-3.0,3.0),
}


def session_from_hour(h):
    if 22 <= h or h <= 5: return "asia"
    if 6 <= h <= 12:      return "london"
    if 13 <= h <= 21:     return "ny"
    return "asia"


def safe_norm(v, lo, hi):
    if hi <= lo: return 0.0
    return float(np.clip(2 * (v - lo) / (hi - lo) - 1, -1, 1))


def pull_candles(pair, granularity, count):
    token = os.environ["OANDA_API_TOKEN"]
    base  = os.environ.get("OANDA_API_URL", "https://api-fxtrade.oanda.com")
    url = f"{base}/v3/instruments/{pair}/candles?" + urllib.parse.urlencode({
        "count": count, "granularity": granularity, "price": "M"})
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    rows = []
    for c in data.get("candles", []):
        if not c.get("complete"): continue
        m = c["mid"]
        rows.append({"time": pd.Timestamp(c["time"], tz="UTC"),
                     "open": float(m["o"]), "high": float(m["h"]),
                     "low": float(m["l"]), "close": float(m["c"]),
                     "volume": int(c.get("volume", 0))})
    return pd.DataFrame(rows).set_index("time").sort_index()


def parse_trades(log_fp):
    sig_re = re.compile(r"(\S+ \S+) INFO v5\.engine  SIGNAL (\w+) (\w+) \| score=([\-\d.]+) d_cert=([\d.]+) m_cert=([\d.]+) expected=([\d.]+)p vol=(\w+)")
    ent_re = re.compile(r"(\S+ \S+) INFO v5\.engine  ENTERED (\w+) (\w+) @ ([\d.]+) \| (\d+) units \| .* trade_id=(\d*)")
    exit_re = re.compile(r"(\S+ \S+) INFO v5\.engine  EXIT .* (\w+) \| trade_id=(\d*) \| approx_net=([\-\d.]+)p")
    signals, entries, exits = [], {}, {}
    for line in log_fp.read_text().splitlines():
        if "SIGNAL" in line:
            m = sig_re.search(line)
            if m:
                ts, pair, direction, score, d, mom, exp, vol = m.groups()
                signals.append({"time": pd.Timestamp(ts, tz="UTC"),
                                "pair": pair, "direction": direction,
                                "score_logged": float(score),
                                "d_cert": float(d), "m_cert": float(mom),
                                "expected_pips_logged": float(exp)})
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
                if tid and tid in exits: td.update(exits[tid])
                trades.append(td); break
    return trades


def compute_features_at(m5, h1, d1, entry_time, pip):
    m5_pos = m5.index.get_indexer([entry_time], method="ffill")[0]
    h1_pos = h1.index.get_indexer([entry_time], method="ffill")[0]
    d1_pos = d1.index.get_indexer([entry_time], method="ffill")[0]
    if m5_pos < 100 or h1_pos < 50 or d1_pos < 60: return None
    m5_close = m5["close"].iloc[m5_pos]
    h1_close = h1["close"].iloc[h1_pos]
    f = {}
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
    # momentum + aggregators
    h1_tr = pd.concat([
        h1["high"].iloc[h1_pos-13:h1_pos+1] - h1["low"].iloc[h1_pos-13:h1_pos+1],
        (h1["high"].iloc[h1_pos-13:h1_pos+1] - h1["close"].shift(1).iloc[h1_pos-13:h1_pos+1]).abs(),
        (h1["low"].iloc[h1_pos-13:h1_pos+1]  - h1["close"].shift(1).iloc[h1_pos-13:h1_pos+1]).abs(),
    ], axis=1).max(axis=1)
    f["atr_1h"] = float(h1_tr.mean() / pip)
    f["wall_frac"]     = float(min(abs(f["pdh_dist_pips"]), abs(f["pdl_dist_pips"])) / (atr5_pips + 1e-6))
    f["ema50_atr_frac"]= float(abs(f["ema50_dist_pct"]) * 10000.0 / (atr5_pips + 1e-6))
    f["atr_conc"]      = float(atr5_pips * 12 / (f["atr_1h"] + 1e-6))
    f["atr_d_pips"]    = float((d1["high"].iloc[d1_pos-13:d1_pos+1] - d1["low"].iloc[d1_pos-13:d1_pos+1]).rolling(14).mean().iloc[-1] / pip)
    d_high = d1["high"].iloc[d1_pos]; d_low = d1["low"].iloc[d1_pos]
    f["adr_consumed"] = float((d_high - d_low) / pip) / (f["atr_d_pips"] + 1e-6)
    h1_atr_series = pd.concat([
        h1["high"].iloc[:h1_pos+1] - h1["low"].iloc[:h1_pos+1],
        (h1["high"].iloc[:h1_pos+1] - h1["close"].shift(1).iloc[:h1_pos+1]).abs(),
        (h1["low"].iloc[:h1_pos+1]  - h1["close"].shift(1).iloc[:h1_pos+1]).abs(),
    ], axis=1).max(axis=1).rolling(14).mean().iloc[-200:]
    f["atr_h1_relative"] = float((h1_atr_series.iloc[-1] / h1_atr_series.mean()) if h1_atr_series.mean() > 0 else 1.0)
    f["trend_1h"] = int(np.sign(f["h1_ret_1bar"]))
    f["trend_4h"] = int(np.sign(f["h1_ret_4bar"]))
    htf_up = ((f["trend_1h"]>0)+(f["trend_4h"]>0)+(f["htf_pct_20"]>0)+(f["htf_pct_60"]>0))
    htf_dn = ((f["trend_1h"]<0)+(f["trend_4h"]<0)+(f["htf_pct_20"]<0)+(f["htf_pct_60"]<0))
    f["htf_align_signed"] = int(htf_up - htf_dn)
    f["htf_align_best"]   = int(max(htf_up, htf_dn))
    return f


def main():
    print("V5 LIVE SMOKE V5 — PER-BUCKET aggregator amplification (NO global pool)\n", flush=True)
    print("Pulling OANDA candles...", flush=True)
    data = {}
    for pair in PAIRS:
        data[pair] = {
            "m5": pull_candles(pair, "M5", 1000),
            "h1": pull_candles(pair, "H1", 300),
            "d1": pull_candles(pair, "D",  150),
        }

    trades = parse_trades(LOG_FP)
    rows = []
    for t in trades:
        if "approx_net_pips" not in t: continue
        pair = t["pair"]
        if pair not in data: continue
        pip = PIP_SIZE[pair]
        feats = compute_features_at(data[pair]["m5"], data[pair]["h1"], data[pair]["d1"],
                                     t["entry_time"], pip)
        if feats is None: continue
        realized_sign = (1 if t["approx_net_pips"] > 0 else -1) if t["direction"] == "long" \
                        else (-1 if t["approx_net_pips"] > 0 else 1)
        votes = {}
        for fname, signed_w in V5_DIR_FACTORS:
            v = feats.get(fname)
            if v is None: continue
            lo, hi = FALLBACK_ANCHORS[fname]
            votes[fname] = (1 if safe_norm(v, lo, hi) * signed_w > 0
                            else (-1 if safe_norm(v, lo, hi) * signed_w < 0 else 0))
        votes["trend_1h"] = int(feats["trend_1h"])
        votes["trend_4h"] = int(feats["trend_4h"])
        votes["htf_align_signed"] = int(np.sign(feats["htf_align_signed"]))
        agg_vals = {a: feats.get(a) for a in AGGREGATORS if a in feats}
        agg_vals["d_cert"] = t["d_cert"]; agg_vals["m_cert"] = t["m_cert"]
        rows.append({"pair": pair, "session": session_from_hour(t["entry_time"].hour),
                     "direction": t["direction"], "entry": t["entry_time"],
                     "approx_net": t["approx_net_pips"], "realized_sign": realized_sign,
                     "votes": votes, "aggregators": agg_vals,
                     "win": t["approx_net_pips"] > 0})

    print(f"Records: {len(rows)}\n", flush=True)

    buckets = {}
    for r in rows: buckets.setdefault((r["pair"], r["session"]), []).append(r)

    L = []
    L.append("="*100)
    L.append("V5 SMOKE V5 — PER-BUCKET AGGREGATOR AMPLIFICATION (no global rollup)")
    L.append("="*100)

    for (pair, sess), brs in sorted(buckets.items()):
        L.append("")
        L.append("─"*100)
        L.append(f"BUCKET: {pair} / {sess}  (n={len(brs)} trades, wins={sum(1 for r in brs if r['win'])})")
        L.append("─"*100)

        # 1) trade table with all aggregator values per trade
        L.append(f"  {'entry':<16}  {'dir':<5}  {'net':>6}  {'real':>5}  "
                 + "  ".join(f"{a[:10]:>10}" for a in AGGREGATORS))
        for r in brs:
            L.append(f"  {str(r['entry'])[:16]:<16}  {r['direction']:<5}  "
                     f"{r['approx_net']:>+6.1f}  {r['realized_sign']:>+5d}  "
                     + "  ".join(f"{(r['aggregators'].get(a) or 0):>10.3f}" for a in AGGREGATORS))

        if len(brs) < 3:
            L.append(f"  (only {len(brs)} trades — too few for HIGH/LOW split within bucket)")
            continue

        # 2) for each aggregator: split within bucket, compute per-feature accuracy
        for agg in AGGREGATORS:
            vals = [r["aggregators"].get(agg) for r in brs]
            if any(v is None for v in vals): continue
            med = float(np.median(vals))
            high = [r for r in brs if r["aggregators"].get(agg) > med]
            low  = [r for r in brs if r["aggregators"].get(agg) <= med]
            if len(high) < 1 or len(low) < 1: continue
            L.append(f"\n  ── {agg}  median={med:.3f}  n_high={len(high)} n_low={len(low)} ──")
            # win rate split
            wr_h = sum(1 for r in high if r["win"]) / len(high)
            wr_l = sum(1 for r in low  if r["win"]) / len(low)
            L.append(f"    WR_high={wr_h*100:.0f}%  WR_low={wr_l*100:.0f}%  lift={ (wr_h-wr_l)*100:+.0f}p")
            # per-feature accuracy
            L.append(f"    {'feature':<22}  {'acc_high':>9}  {'acc_low':>9}  {'amplif':>7}")
            rows_data = []
            for df in DIRECTION_FEATURES:
                ag_h = dis_h = 0
                for r in high:
                    v = r["votes"].get(df)
                    if v is None or v == 0: continue
                    if v == r["realized_sign"]: ag_h += 1
                    else: dis_h += 1
                ag_l = dis_l = 0
                for r in low:
                    v = r["votes"].get(df)
                    if v is None or v == 0: continue
                    if v == r["realized_sign"]: ag_l += 1
                    else: dis_l += 1
                if ag_h + dis_h < 1 or ag_l + dis_l < 1: continue
                acc_h = ag_h / (ag_h + dis_h)
                acc_l = ag_l / (ag_l + dis_l)
                amplif = acc_h / acc_l if acc_l > 0 else float("inf") if acc_h > 0 else 1.0
                tag = ""
                if amplif > 1.3:   tag = " ✓"
                elif amplif < 0.7: tag = " ✗"
                rows_data.append((df, acc_h, acc_l, amplif, tag))
            # sort by amplification desc
            rows_data.sort(key=lambda x: -x[3])
            for df, acc_h, acc_l, amplif, tag in rows_data:
                amp_str = f"{amplif:.2f}" if amplif != float("inf") else "inf"
                L.append(f"    {df:<22}  {acc_h*100:>8.0f}%  {acc_l*100:>8.0f}%  {amp_str:>7}{tag}")

    out = Path("/tmp/v5_smoke/smoke_v5.txt")
    out.write_text("\n".join(L))
    print(f"wrote {out}  ({len(L)} lines)")


if __name__ == "__main__":
    main()
