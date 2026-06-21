"""Speed benchmark: V5 pandas indicators vs QuanTAlib on 100K+ bars."""
import time, json, sys
import numpy as np
import pandas as pd
import quantalib as qtl

SIZES = [10_000, 100_000, 500_000]
REPS  = 5  # average over N runs to dampen noise

# Synthesize a Brownian-walk OHLCV series
def make_corpus(n):
    rng = np.random.default_rng(42)
    log_ret = rng.normal(0, 0.0003, n)  # ~3 bp std per bar (M5 EURUSD-ish)
    close = 1.10 * np.exp(log_ret.cumsum())
    # OHLC: high/low = close ± random spike
    spread = rng.exponential(0.00005, n)
    high = close + spread
    low  = close - spread
    open_ = np.r_[close[0], close[:-1]]
    volume = rng.integers(50, 5000, n).astype(float)
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})
    return df

# V5 implementations (lifted from core/feed/oanda.py)
def v5_atr14_series(df):
    h = df["high"]; l = df["low"]; pc = df["close"].shift(1)
    tr = pd.concat([(h-l).abs(), (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0/14, adjust=False).mean()

def v5_rsi14_series(closes):
    delta = closes.diff()
    gain = delta.clip(lower=0).ewm(alpha=1.0/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1.0/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100/(1+rs)

def v5_ema(closes, span):
    return closes.ewm(span=span, adjust=False).mean()

def v5_bbands(closes, period=20, mult=2.0):
    s = closes.rolling(period); mid = s.mean(); sd = s.std(ddof=1)
    return mid + mult*sd, mid, mid - mult*sd

def time_it(fn, reps=REPS):
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        _ = fn()
        times.append(time.perf_counter() - t0)
    return min(times), np.mean(times), np.median(times)

results = []
for n in SIZES:
    print(f"\n========= corpus size: {n:,} bars =========")
    df = make_corpus(n)
    close = df["close"]
    high  = df["high"]; low = df["low"]; open_ = df["open"]; volume = df["volume"]
    print(f"  data ready ({df.memory_usage(deep=True).sum() / 1e6:.1f} MB)")

    cases = [
        ("EMA-20",  lambda: v5_ema(close, 20),                  lambda: qtl.ema(close, period=20)),
        ("EMA-50",  lambda: v5_ema(close, 50),                  lambda: qtl.ema(close, period=50)),
        ("ATR-14",  lambda: v5_atr14_series(df),                lambda: qtl.atr(open_, high, low, close, volume, period=14)),
        ("RSI-14",  lambda: v5_rsi14_series(close),             lambda: qtl.rsi(close, period=14)),
        ("BB(20,2)", lambda: v5_bbands(close, 20, 2.0),         lambda: qtl.bbands(close, period=20, std=2.0)),
        ("SMA-20",  lambda: close.rolling(20).mean(),           lambda: qtl.sma(close, period=20)),
    ]
    for name, v5_fn, qtl_fn in cases:
        v5_min, v5_avg, _ = time_it(v5_fn)
        qtl_min, qtl_avg, _ = time_it(qtl_fn)
        speedup = v5_avg / qtl_avg
        throughput_v5 = n / v5_avg / 1e6   # M bars/sec
        throughput_qt = n / qtl_avg / 1e6
        verdict = ("✓ qtl wins" if speedup > 1.5 else
                   "= tied"    if 0.67 <= speedup <= 1.5 else
                   "✗ v5 wins")
        print(f"  {name:<10}  V5 {v5_min*1000:>8.2f} ms ({throughput_v5:.1f} Mb/s)  "
              f"QTL {qtl_min*1000:>8.2f} ms ({throughput_qt:.1f} Mb/s)  "
              f"speedup={speedup:>6.2f}x  {verdict}")
        results.append({
            "n": n, "indicator": name,
            "v5_min_ms": v5_min*1000, "qtl_min_ms": qtl_min*1000,
            "speedup": float(speedup), "verdict": verdict,
        })

print("\n=============== SUMMARY ===============")
print(f"{'Indicator':<10}  {'Size':<10}  {'V5 (ms)':>10}  {'QTL (ms)':>10}  {'Speedup':>10}  Verdict")
for r in results:
    print(f"{r['indicator']:<10}  {r['n']:>10,}  {r['v5_min_ms']:>10.2f}  {r['qtl_min_ms']:>10.2f}  "
          f"{r['speedup']:>9.2f}x  {r['verdict']}")

# Save JSON
import os
out = os.path.expanduser("~/quantalib-validation/benchmark_results.json")
with open(out, "w") as f: json.dump(results, f, indent=2)
print(f"\n→ saved {out}")
