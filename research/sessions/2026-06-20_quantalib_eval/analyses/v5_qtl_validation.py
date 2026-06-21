"""V5 hand-coded indicators vs QuanTAlib reference — bit-for-bit comparison.

V5 source: /home/ubuntu/mr-scrooge-v5/core/feed/oanda.py
  _atr14        Wilder ATR14 = EWM(alpha=1/14, adjust=False) on TR
  _rsi14_series Wilder RSI14 = EWM(alpha=1/14, adjust=False) on gains/losses
  _ema          EWM(span=N, adjust=False)
  BB            inline: SMA(20) ± 2 * stdev(ddof=1)

QuanTAlib: pip install quantalib[pandas]  (v0.8.8, NativeAOT C# core)
"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import quantalib as qtl

CSV = sys.argv[1] if len(sys.argv) > 1 else "/tmp/EUR_USD_H1_500.csv"
df = pd.read_csv(CSV)
df["time"] = pd.to_datetime(df["time"])
print(f"loaded {len(df)} H1 bars from {CSV}  range {df['time'].iloc[0]} → {df['time'].iloc[-1]}")
print(f"close range {df['close'].min():.5f} .. {df['close'].max():.5f}")
print()

# ── V5 EXACT REPLICAS (lifted from oanda.py:106-131) ────────────────────────
def v5_atr14_series(df, pip):
    h = df["high"].astype(float); l = df["low"].astype(float); pc = df["close"].astype(float).shift(1)
    tr = pd.concat([(h - l).abs(), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0/14, adjust=False).mean() / pip

def v5_rsi14_series(closes):
    delta = closes.astype(float).diff()
    gain = delta.clip(lower=0).ewm(alpha=1.0/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1.0/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100/(1+rs)

def v5_ema(closes, span):
    return closes.astype(float).ewm(span=span, adjust=False).mean()

def v5_bbands(closes, period=20, mult=2.0):
    s = closes.astype(float).rolling(period)
    mid = s.mean(); sd = s.std(ddof=1)
    return mid + mult*sd, mid, mid - mult*sd  # upper, mid, lower

PIP_EUR_USD = 0.0001
close = df["close"].astype(float)
high  = df["high"].astype(float)
low   = df["low"].astype(float)

# ── COMPARISON ──────────────────────────────────────────────────────────────
def cmp(name, v5_series, qtl_array, skip_first=20, also_skip_50=True):
    v5 = np.asarray(v5_series, dtype=np.float64)
    qt = np.asarray(qtl_array,  dtype=np.float64)
    n_v5, n_qt = len(v5), len(qt)
    print(f"--- {name} ---  V5_len={n_v5} QTL_len={n_qt}")
    # Align lengths (some libraries pad with NaN at front, others omit)
    L = min(n_v5, n_qt)
    a, b = v5[-L:], qt[-L:]
    # Skip initial warmup bars where one or both are NaN / unstable
    mask = ~(np.isnan(a) | np.isnan(b))
    if mask.sum() < 10:
        print(f"  too few overlapping non-NaN bars ({mask.sum()})")
        return
    a2, b2 = a[mask][skip_first:], b[mask][skip_first:]
    diff = a2 - b2
    abs_diff = np.abs(diff)
    rel_diff = abs_diff / (np.abs(b2) + 1e-12)
    print(f"  compared {len(a2)} bars (after skipping {skip_first} warmup of {mask.sum()} non-NaN)")
    print(f"  last bar:   V5={a[-1]:.8f}  QTL={b[-1]:.8f}  diff={a[-1]-b[-1]:+.2e}")
    print(f"  abs diff:   mean={abs_diff.mean():.2e}  max={abs_diff.max():.2e}  median={np.median(abs_diff):.2e}")
    print(f"  rel diff:   mean={rel_diff.mean():.2e}  max={rel_diff.max():.2e}")
    bit_match = abs_diff.max() < 1e-10
    tight     = abs_diff.max() < 1e-6
    loose     = abs_diff.max() < 1e-3
    verdict = "✓ BIT-EXACT" if bit_match else ("✓ TIGHT (<1e-6)" if tight else ("⚠ LOOSE (<1e-3)" if loose else "✗ DIVERGES"))
    print(f"  verdict: {verdict}")
    # If divergent, show where the worst bar is + neighbor values
    if abs_diff.max() > 1e-6:
        worst = abs_diff.argmax()
        print(f"  worst bar idx={worst}  V5={a2[worst]:.8f}  QTL={b2[worst]:.8f}")
    # Also show steady-state-only stats: skip more aggressive warmup for EWM-based indicators
    if also_skip_50 and len(a2) > 100:
        a3, b3 = a2[80:], b2[80:]
        d3 = np.abs(a3 - b3)
        steady_verdict = "✓ BIT-EXACT" if d3.max() < 1e-10 else ("✓ TIGHT" if d3.max() < 1e-6 else f"DIVERGES max={d3.max():.2e}")
        print(f"  steady-state (skip first 80): {steady_verdict}  max_abs={d3.max():.2e}  n={len(d3)}")
    print()
    return {"name": name, "verdict": verdict, "last_diff": float(a[-1]-b[-1]),
            "max_abs_diff": float(abs_diff.max()), "mean_abs_diff": float(abs_diff.mean()),
            "n_compared": int(len(a2))}

results = []

# 1. ATR14 — V5 in pips, QuanTAlib returns raw price units → multiply V5 series by pip
# Note: qtl.atr signature is (open, high, low, close, volume, period=14) — Wilder ATR
#   doesn't actually need open/volume but qtl normalizes all OHLCV-input indicators
v5_atr_pips  = v5_atr14_series(df, PIP_EUR_USD)
v5_atr_price = v5_atr_pips * PIP_EUR_USD     # back to price units to match qtl
qtl_atr      = qtl.atr(df["open"].astype(float), high, low, close, df["volume"].astype(float), period=14)
results.append(cmp("ATR14 (price units)", v5_atr_price, qtl_atr))

# 2. EMA-20
v5_ema20  = v5_ema(close, 20)
qtl_ema20 = qtl.ema(close, period=20)
results.append(cmp("EMA-20", v5_ema20, qtl_ema20))

# 2b. EMA-50
results.append(cmp("EMA-50", v5_ema(close, 50), qtl.ema(close, period=50)))

# 2c. EMA-5
results.append(cmp("EMA-5",  v5_ema(close,  5), qtl.ema(close, period=5)))

# 3. RSI-14
v5_rsi  = v5_rsi14_series(close)
qtl_rsi = qtl.rsi(close, period=14)
results.append(cmp("RSI-14 (Wilder)", v5_rsi, qtl_rsi))

# 4. Bollinger Bands (20, 2σ) — qtl returns (upper, mid, lower) tuple
v5_bb_u, v5_bb_m, v5_bb_l = v5_bbands(close, period=20, mult=2.0)
qtl_bb = qtl.bbands(close, period=20, std=2.0)
# qtl returns a pandas DataFrame when pandas input given; columns probably ('upper', 'mid', 'lower') or similar
if isinstance(qtl_bb, pd.DataFrame):
    print(f"qtl.bbands DataFrame columns: {list(qtl_bb.columns)}")
    cols = list(qtl_bb.columns)
    # qtl convention: BBU_period_std (upper), BBM (mid), BBL (lower) — match by letter
    def pickcol(letter, *fallback_substrs):
        for c in cols:
            cl = c.lower()
            if cl.startswith(f"bb{letter}") or cl.startswith(f"bband_{letter}"):
                return c
            for f in fallback_substrs:
                if f in cl: return c
        raise KeyError(f"no col for BB{letter.upper()} among {cols}")
    qtl_u = qtl_bb[pickcol("u", "upper")]
    qtl_m = qtl_bb[pickcol("m", "middle", "mid_")]
    qtl_l = qtl_bb[pickcol("l", "lower")]
    print(f"  → upper={qtl_u.name}  mid={qtl_m.name}  lower={qtl_l.name}")
elif isinstance(qtl_bb, tuple) and len(qtl_bb) == 3:
    qtl_u, qtl_m, qtl_l = qtl_bb
else:
    print(f"qtl.bbands unknown shape: {type(qtl_bb)}")
    qtl_u = qtl_m = qtl_l = None

if qtl_u is not None:
    results.append(cmp("BB-upper(20,2σ)", v5_bb_u, qtl_u))
    results.append(cmp("BB-mid(20)",      v5_bb_m, qtl_m))
    results.append(cmp("BB-lower(20,2σ)", v5_bb_l, qtl_l))

# ── SUMMARY ──────────────────────────────────────────────────────────────────
print("="*64)
print("SUMMARY")
print("="*64)
for r in results:
    if r:
        print(f"  {r['name']:<22}  {r['verdict']:<22}  max_abs={r['max_abs_diff']:.2e}  n={r['n_compared']}")
