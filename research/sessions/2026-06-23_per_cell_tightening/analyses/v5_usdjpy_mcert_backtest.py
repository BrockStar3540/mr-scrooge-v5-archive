#!/usr/bin/env python3
"""USD_JPY m_cert floor=0.75 backtest on 2026 V5-actionable bars.

For each M5 bar in 2026, runs V5's direction_v2 + momentum_v3 modules,
captures dir_score / d_cert / m_cert per direction, filters to
V5-actionable bars (passes all current gates), then groups by:
  session × m_cert bucket (< 0.75 vs >= 0.75) × forward 1H pip outcome.

Uses ~/qtl-discovery-8yr/features/USD_JPY_features.parquet which has all
the V5 MarketView features + fwd_ret_pips already computed.

Reports:
  - n bars per bucket
  - mean fwd_ret_pips per bucket
  - WR per bucket
  - Implied saved-loss / lost-win if floor 0.75 applied
"""
from __future__ import annotations
import os, sys, subprocess
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
import pandas as pd
import numpy as np

# Verify Mini before any heavy compute
out = subprocess.run(["system_profiler", "SPHardwareDataType"], capture_output=True, text=True).stdout
assert "CPYQTH294R" in out, "NOT ON MINI"
print("device verified: CPYQTH294R (Mac mini)")

# Make V5 modules importable
V5_ROOT = Path.home() / "v5_backtest"
sys.path.insert(0, str(V5_ROOT))

from modules.signals.base import MarketView
from modules.signals.direction_v2 import DirectionModule
from modules.signals.momentum_v3 import MomentumModule

PAIR = "USD_JPY"
PARQ = Path.home() / f"qtl-discovery-8yr/features/{PAIR}_features.parquet"
MCERT_FLOOR_PROPOSED = 0.75
MIN_DIR_SCORE = 0.15  # direction_v2 emits 'block' below this
MIN_DIR_SCORE_PLAYMAKER = 0.25
MIN_DIR_CERT = 0.30
MIN_MOM_CERT = 0.25

# 1. Load features
df = pd.read_parquet(PARQ)
print(f"Loaded {len(df):,} bars, {df.index.min()} -> {df.index.max()}")
df = df[df.index >= pd.Timestamp("2026-01-01", tz="UTC")]
print(f"2026 only: {len(df):,} bars")
df = df.dropna(subset=["fwd_ret_pips"])
print(f"With forward-pip available: {len(df):,} bars")

# 2. Per-session iteration. Build DirectionModule + MomentumModule per session once.
sessions = ["asia", "london", "ny"]
dir_mods = {s: DirectionModule(PAIR, s) for s in sessions}
mom_mods = {s: MomentumModule(PAIR, s) for s in sessions}

# 3. For each bar, construct MarketView, run direction + momentum per direction
# V5 evaluates a single direction module that dual-computes long/short scores;
# momentum module is also direction-aware.
rows = []
mv_field_names = {f.name for f in MarketView.__dataclass_fields__.values()}

print(f"\nIterating bars (this takes a moment)...")
n_processed = 0
for ts, r in df.iterrows():
    sess = r.get("session", None)
    if sess not in sessions:
        # Use UTC-hour mapping
        h = ts.hour
        if 7 <= h < 13: sess = "london"
        elif 13 <= h < 22: sess = "ny"
        else: sess = "asia"
    # Build MarketView from row
    mv_kw = {"pair": PAIR, "session": sess, "timestamp": ts}
    # Parquet → MarketView field aliases
    aliases = {"rsi14": "rsi14_h1", "ema20_1h_dist": "ema20_1h_dist"}
    for f in mv_field_names:
        if f in ("pair", "session", "timestamp"): continue
        src = aliases.get(f, f)
        if src in r.index and not pd.isna(r[src]):
            mv_kw[f] = float(r[src])
    # Required fields (no default in MarketView) — must be present
    required = ["h1_ret_1bar","h1_ret_4bar","rsi14","rsi_slope","zscore_1h","ema20_1h_dist"]
    if not all(k in mv_kw for k in required):
        continue
    try:
        view = MarketView(**mv_kw)
    except TypeError:
        continue
    # Run direction module (dual computes long+short)
    try:
        dstamp = dir_mods[sess].stamp(view)
    except Exception:
        continue
    # Direction module emits 'block' if |score| < 0.15
    if dstamp.bias == "block":
        continue
    # Run momentum module for the chosen direction
    try:
        mstamp = mom_mods[sess].stamp(view, dstamp.bias)
    except Exception:
        continue
    # Gates check (mirror playmaker)
    if abs(dstamp.score) < MIN_DIR_SCORE_PLAYMAKER: continue
    if dstamp.certainty < MIN_DIR_CERT: continue
    if mstamp.certainty < MIN_MOM_CERT: continue
    # Forward pip: parquet has fwd_ret_pips (forward 1H signed). Re-sign to trade direction.
    fwd_signed = float(r["fwd_ret_pips"]) * (1 if dstamp.bias == "long" else -1)
    rows.append({
        "ts": ts, "session": sess, "dir": dstamp.bias,
        "dir_score": dstamp.score, "d_cert": dstamp.certainty,
        "m_cert": mstamp.certainty,
        "fwd_pip": fwd_signed,
    })
    n_processed += 1
    if n_processed % 2000 == 0:
        print(f"  ...{n_processed} V5-actionable bars processed")

print(f"\nTotal V5-actionable bars in 2026 USD_JPY: {len(rows):,}")
out = pd.DataFrame(rows)
out.to_csv(V5_ROOT / "usdjpy_2026_actionable.csv", index=False)
print(f"Saved {V5_ROOT}/usdjpy_2026_actionable.csv")

if len(out) == 0:
    print("No actionable bars — nothing to analyze.")
    sys.exit(0)

# 4. Per-session group: ALL vs FLOOR-FILTERED
def summarize(df, label):
    n = len(df); m = df["fwd_pip"].mean(); s = df["fwd_pip"].sum()
    wr = 100 * (df["fwd_pip"] > 0).mean()
    return f"{label:<28} n={n:>6}  mean={m:>+6.3f}p  sum={s:>+9.1f}p  WR={wr:>4.1f}%"

print("\n" + "="*78)
print("USD_JPY 2026 V5-actionable bars — m_cert floor 0.75 simulation")
print("="*78)
for sess in sessions:
    seg = out[out.session == sess]
    if len(seg) == 0:
        print(f"\n[{sess.upper()}] no actionable bars")
        continue
    print(f"\n[{sess.upper()}] — {len(seg):,} actionable bars total")
    print(f"  ALL (current floor 0.25):")
    print(f"    {summarize(seg, sess + ' all')}")
    for dr in ["long", "short"]:
        sg = seg[seg.dir == dr]
        if len(sg):
            print(f"    {summarize(sg, '  ' + dr)}")

    lo = seg[seg.m_cert < MCERT_FLOOR_PROPOSED]
    hi = seg[seg.m_cert >= MCERT_FLOOR_PROPOSED]
    print(f"  PROPOSED FLOOR 0.75:")
    print(f"    {summarize(lo, 'BLOCKED (m_cert<0.75)')}")
    print(f"    {summarize(hi, 'KEPT (m_cert>=0.75)')}")
    # Per direction within the keep bucket
    for dr in ["long", "short"]:
        sg = hi[hi.dir == dr]
        if len(sg):
            print(f"    {summarize(sg, '  KEEP/' + dr)}")
    # Delta if we applied the floor
    delta_sum = hi["fwd_pip"].sum() - seg["fwd_pip"].sum()  # what we GIVE UP by blocking
    print(f"  Δ vs current: {delta_sum:+.1f}p sum impact (KEPT minus ALL)")
    print(f"    Blocked-bucket lost-pip (if positive, blocking COSTS us): {lo['fwd_pip'].sum():+.1f}p over {len(lo)} bars")
    print(f"    Mean fwd_pip difference: KEPT {hi['fwd_pip'].mean():+.3f}p vs ALL {seg['fwd_pip'].mean():+.3f}p")

print("\n" + "="*78)
print("Overall")
print("="*78)
print(f"  ALL:    {summarize(out, 'all sessions')}")
lo = out[out.m_cert < MCERT_FLOOR_PROPOSED]
hi = out[out.m_cert >= MCERT_FLOOR_PROPOSED]
print(f"  FLOOR:  BLOCKED n={len(lo):,} sum={lo['fwd_pip'].sum():+.1f}p mean={lo['fwd_pip'].mean():+.3f}p WR={100*(lo['fwd_pip']>0).mean():.1f}%")
print(f"  FLOOR:  KEPT    n={len(hi):,} sum={hi['fwd_pip'].sum():+.1f}p mean={hi['fwd_pip'].mean():+.3f}p WR={100*(hi['fwd_pip']>0).mean():.1f}%")
