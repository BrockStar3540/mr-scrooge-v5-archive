#!/usr/bin/env python3
"""EUR_JPY/ny/short 2026 backtest with cpos + willr filter rules (Brock).

Filter: cpos in [0.06, 0.60] AND willr in [-85.0, -7.0]
"""
import os, sys, subprocess
from pathlib import Path
from datetime import timezone
import pandas as pd

out = subprocess.run(["system_profiler", "SPHardwareDataType"], capture_output=True, text=True).stdout
assert "CPYQTH294R" in out, "NOT ON MINI"
print("device verified: CPYQTH294R")

V5_ROOT = Path.home() / "v5_backtest"
sys.path.insert(0, str(V5_ROOT))

from modules.signals.base import MarketView
from modules.signals.direction_v2 import DirectionModule
from modules.signals.momentum_v3 import MomentumModule

PAIR = "EUR_JPY"
PIP = 0.01
PARQ = Path.home() / f"qtl-discovery-8yr/features/{PAIR}_features.parquet"

# Filter ranges (Brock observation from live trades)
CPOS_MIN, CPOS_MAX = 0.06, 0.60
WILLR_MIN, WILLR_MAX = -85.0, -7.0

df = pd.read_parquet(PARQ)
df = df[df.index >= pd.Timestamp("2026-01-01", tz="UTC")]
df = df.dropna(subset=["fwd_ret_pips"])
print(f"2026 EUR_JPY bars with fwd: {len(df):,}\n")

dm_ny = DirectionModule(PAIR, "ny")
mm_ny = MomentumModule(PAIR, "ny")
mv_fields = {f.name for f in MarketView.__dataclass_fields__.values()}
aliases = {"rsi14": "rsi14_h1"}
required = ["h1_ret_1bar","h1_ret_4bar","rsi14","rsi_slope","zscore_1h","ema20_1h_dist"]

rows = []
for ts, r in df.iterrows():
    h = ts.hour
    if not (13 <= h < 22):  # ny only
        continue
    mv_kw = {"pair": PAIR, "session": "ny", "timestamp": ts}
    for f in mv_fields:
        if f in ("pair","session","timestamp"): continue
        src = aliases.get(f, f)
        if src in r.index and not pd.isna(r[src]):
            mv_kw[f] = float(r[src])
    if not all(k in mv_kw for k in required):
        continue
    try: view = MarketView(**mv_kw)
    except TypeError: continue
    try: ds = dm_ny.stamp(view)
    except: continue
    if ds.bias != "short":  # short side only
        continue
    try: ms = mm_ny.stamp(view, ds.bias)
    except: continue
    if abs(ds.score) < 0.25 or ds.certainty < 0.30 or ms.certainty < 0.25:
        continue
    fwd = float(r["fwd_ret_pips"]) * -1   # SHORT direction
    cpos = float(r.get("close_pos_daily", 0))
    willr = float(r.get("q_willr_m5", 0))
    rows.append({
        "ts": ts, "m_cert": ms.certainty, "d_cert": ds.certainty,
        "dir_score": ds.score, "cpos": cpos, "willr": willr,
        "vortex": float(r.get("q_vortex_diff_h1", 0)),
        "fwd_pip": fwd,
    })

print(f"V5-actionable EUR_JPY/ny/short bars in 2026: {len(rows):,}\n")
out_df = pd.DataFrame(rows)

def summ(seg, label):
    if len(seg)==0: return f"{label:<40} n=0"
    n = len(seg); m = seg["fwd_pip"].mean(); s = seg["fwd_pip"].sum()
    wr = 100*(seg["fwd_pip"]>0).mean()
    return f"{label:<40} n={n:>5}  mean={m:>+6.3f}p  WR={wr:>4.1f}%  sum={s:>+9.1f}p"

print("="*90)
print("Baseline (V5-actionable EUR_JPY/ny/short, no filter)")
print("="*90)
print(summ(out_df, "  ALL"))

print()
print("="*90)
print(f"BROCK'S FILTER: cpos in [{CPOS_MIN}, {CPOS_MAX}] AND willr in [{WILLR_MIN}, {WILLR_MAX}]")
print("="*90)
keep = out_df[
    (out_df.cpos >= CPOS_MIN) & (out_df.cpos <= CPOS_MAX) &
    (out_df.willr >= WILLR_MIN) & (out_df.willr <= WILLR_MAX)
]
block = out_df.drop(keep.index)
print(summ(keep,  "  KEEP (both filters pass)"))
print(summ(block, "  BLOCKED (one or both fail)"))

# Per-filter individual effect
print()
print("="*90)
print("Each filter alone")
print("="*90)
cpos_keep = out_df[(out_df.cpos >= CPOS_MIN) & (out_df.cpos <= CPOS_MAX)]
willr_keep = out_df[(out_df.willr >= WILLR_MIN) & (out_df.willr <= WILLR_MAX)]
print(summ(cpos_keep,  "  cpos in [0.06, 0.60] alone"))
print(summ(willr_keep, "  willr in [-85, -7] alone"))

# Per-quarter time-stability check
print()
print("="*90)
print("Time stability — filter performance by quarter")
print("="*90)
keep["ts"] = pd.to_datetime(keep["ts"])
out_df["ts"] = pd.to_datetime(out_df["ts"])
for q in ["2026Q1","2026Q2"]:
    qd = pd.Period(q).start_time.tz_localize("UTC"), (pd.Period(q).end_time + pd.Timedelta(days=1)).tz_localize("UTC")
    al = out_df[(out_df.ts >= qd[0]) & (out_df.ts < qd[1])]
    kp = keep[(keep.ts >= qd[0]) & (keep.ts < qd[1])]
    print(f"  {q}: ALL n={len(al):>4} mean={al['fwd_pip'].mean() if len(al) else 0:+.2f}p WR={100*(al['fwd_pip']>0).mean() if len(al) else 0:.0f}% | KEEP n={len(kp):>4} mean={kp['fwd_pip'].mean() if len(kp) else 0:+.2f}p WR={100*(kp['fwd_pip']>0).mean() if len(kp) else 0:.0f}%")

# Per-direction not relevant since we already filtered to short
# But also useful: m_cert distribution of KEEP set
print()
print("="*90)
print("KEEP set: m_cert distribution")
print("="*90)
for lo, hi in [(0.25, 0.40), (0.40, 0.55), (0.55, 0.70), (0.70, 1.0)]:
    bucket = keep[(keep.m_cert >= lo) & (keep.m_cert < hi)]
    if len(bucket):
        print(f"  m_cert [{lo:.2f}, {hi:.2f}):  n={len(bucket):>4} mean={bucket['fwd_pip'].mean():+.2f}p WR={100*(bucket['fwd_pip']>0).mean():.0f}%")
