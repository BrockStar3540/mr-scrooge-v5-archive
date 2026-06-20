#!/usr/bin/env python3
"""Live smoke test — V5's trades today as ground truth.

For each of today's V5 trades:
  - Parse SIGNAL / ENTERED / EXIT from journalctl
  - Recompute V5's direction features at the entry timestamp from fresh OANDA candles
  - Apply V5's signed-weight contributions per feature
  - Check: did each feature's directional vote match the realized price move?

Per-feature output:
  - n trades the feature voted on
  - n agree with realized direction
  - accuracy %
  - rank of features by who was 'right' most often today

This is the empirical reality check on the matrix's feature rankings.
"""
import os, sys, re, json, time, urllib.parse, urllib.request
from datetime import datetime, timezone
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
OUT_DIR = Path("/tmp/v5_smoke")
OUT_DIR.mkdir(exist_ok=True)


# V5 _FACTOR_DEFS — exactly as in modules/signals/direction.py
V5_FACTORS = [
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
        rows.append({
            "time":   pd.Timestamp(c["time"], tz="UTC"),
            "open":   float(m["o"]), "high": float(m["h"]),
            "low":    float(m["l"]), "close":float(m["c"]),
            "volume": int(c.get("volume", 0)),
        })
    return pd.DataFrame(rows).set_index("time").sort_index()


def parse_trades(log_fp: Path):
    """Parse SIGNAL / ENTERED / EXIT lines into trade records."""
    sig_re   = re.compile(r"(\S+ \S+) INFO v5\.engine  SIGNAL (\w+) (\w+) \| score=([\-\d.]+) d_cert=([\d.]+) m_cert=([\d.]+)")
    ent_re   = re.compile(r"(\S+ \S+) INFO v5\.engine  ENTERED (\w+) (\w+) @ ([\d.]+) \| (\d+) units \| .* trade_id=(\d*)")
    exit_re  = re.compile(r"(\S+ \S+) INFO v5\.engine  EXIT .* (\w+) \| trade_id=(\d*) \| approx_net=([\-\d.]+)p")
    signals = []
    entries = {}
    exits = {}
    for line in log_fp.read_text().splitlines():
        if "SIGNAL" in line:
            m = sig_re.search(line)
            if m:
                ts, pair, direction, score, d, mom = m.groups()
                signals.append({
                    "time": pd.Timestamp(ts, tz="UTC"),
                    "pair": pair, "direction": direction,
                    "score_logged": float(score),
                    "d_cert": float(d), "m_cert": float(mom),
                })
        elif "ENTERED" in line:
            m = ent_re.search(line)
            if m:
                ts, pair, direction, price, units, tid = m.groups()
                entries[(pair, ts)] = {
                    "time": pd.Timestamp(ts, tz="UTC"),
                    "pair": pair, "direction": direction,
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
    # zip signals with entries by timestamp (sequential, same ms-level)
    trades = []
    for sig in signals:
        # find matching entry within 1 second
        for (pair, ts), ent in entries.items():
            if pair == sig["pair"] and abs((ent["time"] - sig["time"]).total_seconds()) < 2:
                td = {**sig, **ent}
                tid = ent.get("trade_id")
                if tid and tid in exits:
                    td.update(exits[tid])
                trades.append(td)
                break
    return trades


def safe_norm(v, lo, hi):
    if hi <= lo: return 0.0
    return float(np.clip(2 * (v - lo) / (hi - lo) - 1, -1, 1))


# Heuristic anchors (fallbacks — V5 normally loads from factor_sweep.json
# per pair*session; for the smoke test these approximate anchors give us
# directionally meaningful contributions).
FALLBACK_ANCHORS = {
    "h1_ret_1bar":      (-12.0,  12.0),
    "rsi_slope":        ( -9.0,   9.0),
    "zscore_1h":        ( -2.0,   2.0),
    "h1_ret_4bar":      (-20.0,  20.0),
    "d_ret":            (-40.0,  40.0),
    "ema20_1h_dist_pct":( -0.15,  0.15),
    "pdh_dist_pips":    (-20.0,  20.0),
    "pdl_dist_pips":    (-20.0,  20.0),
    "pdh_dist_atr_pct": ( -3.0,   3.0),
    "pdl_dist_atr_pct": ( -3.0,   3.0),
    "rsi14":            ( 35.0,  65.0),
    "htf_pct_20":       ( -3.0,   3.0),
    "htf_pct_60":       ( -3.0,   3.0),
    "ema20_dist_pct":   ( -0.10,  0.10),
    "bb_pos":           (  0.1,   0.9),
    "zscore_5m":        ( -2.0,   2.0),
    "ema5_dist_pips":   ( -5.0,   5.0),
    "ret_5m":           ( -3.0,   3.0),
    "ret_15m":          ( -5.0,   5.0),
    "ret_30m":          ( -8.0,   8.0),
    "ret_1h":           (-12.0,  12.0),
    "ema50_dist_pct":   ( -0.20,  0.20),
    "close_pos_daily":  (  0.1,   0.9),
    "ema_cross_pips":   ( -3.0,   3.0),
}


def compute_features_at(m5: pd.DataFrame, h1: pd.DataFrame, d1: pd.DataFrame,
                         entry_time: pd.Timestamp, pip: float) -> dict | None:
    """Compute V5 direction features at the M5 bar containing or before entry_time."""
    # nearest M5 bar at-or-before entry
    m5_pos = m5.index.get_indexer([entry_time], method="ffill")[0]
    h1_pos = h1.index.get_indexer([entry_time], method="ffill")[0]
    d1_pos = d1.index.get_indexer([entry_time], method="ffill")[0]
    if m5_pos < 100 or h1_pos < 50 or d1_pos < 60:
        return None
    m5_close = m5["close"].iloc[m5_pos]
    h1_close = h1["close"].iloc[h1_pos]
    h1_close_prev = h1["close"].iloc[h1_pos - 1]
    h1_close_4 = h1["close"].iloc[h1_pos - 4]
    d1_close = d1["close"].iloc[d1_pos]
    d1_close_prev = d1["close"].iloc[d1_pos - 1] if d1_pos >= 1 else d1_close

    f = {}
    # h1_ret_1bar in pips
    f["h1_ret_1bar"] = (h1_close - h1_close_prev) / pip
    f["h1_ret_4bar"] = (h1_close - h1_close_4) / pip
    # rsi_slope: change in RSI14 (on M5) over 3 bars
    delta = m5["close"].iloc[m5_pos-13:m5_pos+1].diff()
    up = delta.clip(lower=0).rolling(14).mean()
    dn = (-delta.clip(upper=0)).rolling(14).mean()
    rsi = 100 - 100 / (1 + up / (dn + 1e-12))
    rsi14_now = float(rsi.iloc[-1]); rsi14_3ago = float(rsi.iloc[-4]) if len(rsi) >= 4 else rsi14_now
    f["rsi14"] = rsi14_now
    f["rsi_slope"] = rsi14_now - rsi14_3ago
    # zscore_1h: zscore of m5 close over 20-bar window (proxy for 1h)
    win20 = m5["close"].iloc[m5_pos-19:m5_pos+1]
    f["zscore_1h"] = (m5_close - win20.mean()) / (win20.std() + 1e-12)
    # zscore_5m: same idea on shorter window
    win5 = m5["close"].iloc[m5_pos-4:m5_pos+1]
    f["zscore_5m"] = (m5_close - win5.mean()) / (win5.std() + 1e-12)
    # d_ret: today's daily return so far
    f["d_ret"] = (d1_close - d1_close_prev) / pip
    # ema20 on h1
    h1_ema20 = h1["close"].iloc[:h1_pos+1].ewm(span=20).mean().iloc[-1]
    f["ema20_1h_dist_pct"] = (h1_close - h1_ema20) / h1_close
    # PDH/PDL — yesterday's high/low (d1_pos - 1)
    pdh = d1["high"].iloc[d1_pos - 1] if d1_pos >= 1 else d1["high"].iloc[d1_pos]
    pdl = d1["low"].iloc[d1_pos - 1] if d1_pos >= 1 else d1["low"].iloc[d1_pos]
    f["pdh_dist_pips"] = (m5_close - pdh) / pip
    f["pdl_dist_pips"] = (m5_close - pdl) / pip
    # ATR for the normalization
    tr = pd.concat([
        m5["high"].iloc[m5_pos-13:m5_pos+1] - m5["low"].iloc[m5_pos-13:m5_pos+1],
        (m5["high"].iloc[m5_pos-13:m5_pos+1] - m5["close"].shift(1).iloc[m5_pos-13:m5_pos+1]).abs(),
        (m5["low"].iloc[m5_pos-13:m5_pos+1]  - m5["close"].shift(1).iloc[m5_pos-13:m5_pos+1]).abs(),
    ], axis=1).max(axis=1)
    atr5 = tr.mean()
    atr5_pips = atr5 / pip if pip > 0 else atr5
    f["pdh_dist_atr_pct"] = f["pdh_dist_pips"] / (atr5_pips + 1e-6)
    f["pdl_dist_atr_pct"] = f["pdl_dist_pips"] / (atr5_pips + 1e-6)
    # htf_pct_20 / 60
    f["htf_pct_20"] = (d1_close - d1["close"].iloc[d1_pos - 20]) / d1_close * 100
    f["htf_pct_60"] = (d1_close - d1["close"].iloc[d1_pos - 60]) / d1_close * 100
    # ema20/ema50 distance on M5
    ema20_m5 = m5["close"].iloc[:m5_pos+1].ewm(span=20).mean().iloc[-1]
    ema50_m5 = m5["close"].iloc[:m5_pos+1].ewm(span=50).mean().iloc[-1]
    ema5_m5  = m5["close"].iloc[:m5_pos+1].ewm(span=5).mean().iloc[-1]
    f["ema20_dist_pct"] = (m5_close - ema20_m5) / m5_close
    f["ema50_dist_pct"] = (m5_close - ema50_m5) / m5_close
    f["ema5_dist_pips"] = (m5_close - ema5_m5) / pip
    # BB pos on M5
    bb_win = m5["close"].iloc[m5_pos-19:m5_pos+1]
    bb_mean = bb_win.mean(); bb_std = bb_win.std()
    bb_upper = bb_mean + 2 * bb_std; bb_lower = bb_mean - 2 * bb_std
    f["bb_pos"] = (m5_close - bb_lower) / (bb_upper - bb_lower + 1e-12)
    # multi-window m5 returns in pips
    f["ret_5m"]  = (m5_close - m5["close"].iloc[m5_pos-1]) / pip
    f["ret_15m"] = (m5_close - m5["close"].iloc[m5_pos-3]) / pip
    f["ret_30m"] = (m5_close - m5["close"].iloc[m5_pos-6]) / pip
    f["ret_1h"]  = (m5_close - m5["close"].iloc[m5_pos-12]) / pip
    # close_pos_daily — within today's intraday range
    today_high = m5["high"].iloc[max(0, m5_pos-288):m5_pos+1].max()
    today_low  = m5["low"].iloc[max(0, m5_pos-288):m5_pos+1].min()
    f["close_pos_daily"] = (m5_close - today_low) / (today_high - today_low + 1e-12)
    # EMA cross 12/26 (pips)
    ema12 = m5["close"].iloc[:m5_pos+1].ewm(span=12).mean().iloc[-1]
    ema26 = m5["close"].iloc[:m5_pos+1].ewm(span=26).mean().iloc[-1]
    f["ema_cross_pips"] = (ema12 - ema26) / pip
    return f


def main():
    print("Live smoke test — V5's trades today + fresh OANDA features\n", flush=True)
    print("Pulling fresh OANDA candles...", flush=True)
    data = {}
    for pair in PAIRS:
        m5 = pull_candles(pair, "M5", 1000)
        h1 = pull_candles(pair, "H1", 300)
        d1 = pull_candles(pair, "D",  150)
        data[pair] = {"m5": m5, "h1": h1, "d1": d1}
        print(f"  {pair}: m5={len(m5)} h1={len(h1)} d1={len(d1)}", flush=True)

    print("\nParsing trades from journalctl log...", flush=True)
    trades = parse_trades(LOG_FP)
    print(f"  parsed {len(trades)} trades (with signal+entry+optional exit)", flush=True)

    # Compute per-feature directional vote per trade
    print("\nComputing features per trade entry...", flush=True)
    rows = []
    for t in trades:
        if "approx_net_pips" not in t:
            continue  # skip open trades
        pair = t["pair"]
        if pair not in data: continue
        feats = compute_features_at(
            data[pair]["m5"], data[pair]["h1"], data[pair]["d1"],
            t["time"], PIP_SIZE[pair],
        )
        if feats is None: continue
        # realized_sign — was the market move actually in the entry direction?
        # +1 = realized went UP (was good for long, bad for short)
        # -1 = realized went DOWN
        if t["direction"] == "long":
            realized_sign = 1 if t["approx_net_pips"] > 0 else -1
        else:
            realized_sign = -1 if t["approx_net_pips"] > 0 else 1
        # per-feature contribution and vote
        contribs = {}
        votes    = {}
        for fname, signed_w in V5_FACTORS:
            v = feats.get(fname)
            if v is None: continue
            lo, hi = FALLBACK_ANCHORS[fname]
            norm = safe_norm(v, lo, hi)
            contrib = norm * signed_w
            contribs[fname] = contrib
            votes[fname] = 1 if contrib > 0 else (-1 if contrib < 0 else 0)
        rows.append({
            "time": t["time"], "pair": pair,
            "direction": t["direction"],
            "score_logged": t["score_logged"],
            "approx_net_pips": t["approx_net_pips"],
            "realized_sign": realized_sign,
            "win": t["approx_net_pips"] > 0,
            "features": feats,
            "contribs": contribs,
            "votes": votes,
        })

    print(f"\nComplete trade records: {len(rows)}", flush=True)
    if not rows:
        print("no trades to analyze"); return

    # Aggregate per-feature accuracy
    feature_stats = {}
    for fname, signed_w in V5_FACTORS:
        agrees = 0; disagrees = 0; total = 0
        for r in rows:
            v = r["votes"].get(fname)
            if v is None or v == 0: continue
            total += 1
            if v == r["realized_sign"]:
                agrees += 1
            else:
                disagrees += 1
        if total == 0: continue
        feature_stats[fname] = {
            "agree": agrees, "disagree": disagrees, "n": total,
            "accuracy": agrees / total,
            "signed_w": signed_w,
        }
    ranked = sorted(feature_stats.items(), key=lambda x: -x[1]["accuracy"])

    # Composite test: did V5's logged score match realized?
    composite_correct = sum(1 for r in rows if np.sign(r["score_logged"]) == r["realized_sign"])
    n_with_score = sum(1 for r in rows if r["score_logged"] != 0)

    print("\n" + "="*90)
    print("V5 LIVE SMOKE TEST — TODAY'S TRADES + FRESH OANDA FEATURE RECOMPUTE")
    print("="*90)
    print(f"\n  Trades analyzed: {len(rows)}")
    print(f"  Wins: {sum(1 for r in rows if r['win']):>3} / {len(rows)} ({sum(1 for r in rows if r['win'])/len(rows)*100:.1f}%)")
    print(f"  Composite V5 score → realized direction: {composite_correct}/{n_with_score} = {composite_correct/n_with_score*100:.1f}%")
    print(f"\n  Per-feature accuracy (was this feature on the right side of the realized move?):")
    print(f"  {'rank':>4}  {'feature':<22}  {'V5_weight':>9}  {'agree':>5}  {'dis':>4}  {'n':>4}  {'acc':>6}")
    for i, (f, s) in enumerate(ranked, 1):
        print(f"  {i:>4}  {f:<22}  {s['signed_w']:>+9.2f}  "
              f"{s['agree']:>5}  {s['disagree']:>4}  {s['n']:>4}  {s['accuracy']*100:>5.1f}%")

    # Trade-by-trade table
    print(f"\n  Trade-by-trade (first 20):")
    print(f"  {'pair':<8}  {'time':<19}  {'dir':<5}  {'net_p':>7}  {'realized':>8}  {'score_logged':>12}")
    for r in rows[:20]:
        print(f"  {r['pair']:<8}  {str(r['time'])[:19]:<19}  {r['direction']:<5}  "
              f"{r['approx_net_pips']:>+7.2f}  {r['realized_sign']:>+8d}  {r['score_logged']:>+12.4f}")

    # save
    OUT_DIR.mkdir(exist_ok=True)
    summary = {
        "n_trades": len(rows),
        "n_wins": sum(1 for r in rows if r["win"]),
        "composite_score_accuracy": composite_correct / n_with_score if n_with_score else None,
        "per_feature": feature_stats,
    }
    (OUT_DIR / "smoke_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nwrote {OUT_DIR/'smoke_summary.json'}")


if __name__ == "__main__":
    main()
