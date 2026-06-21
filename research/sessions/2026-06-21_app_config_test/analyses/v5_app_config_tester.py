"""App-config tester: do the multi-timeframe RSI/EMA/StochRSI configurations
actually predict 60-min forward direction, or are they visually persuasive only?

For each of 8 configs:
  - Scan every historical M5 bar for signal occurrences
  - For each signal: compute 15/30/60/90/120-min signed forward pip
    (positive = signal was right, negative = wrong)
  - Aggregate per pair, per session, per pair-group
  - Compute expectancy + profit factor

Runs on Mini. Uses qtl + pandas. 8 pairs × 8yr × 8 configs.
"""
import os, json, subprocess, time
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
from joblib import Parallel, delayed

def assert_on_mini():
    s = subprocess.run(["system_profiler","SPHardwareDataType"], capture_output=True, text=True).stdout
    if "CPYQTH294R" not in s: raise RuntimeError("NOT ON MINI")
    print("✓ device verified: Mini CPYQTH294R")
assert_on_mini()

# Use pandas-native RSI / EMA / Stoch math — bit-exact vs V5's hand-codes (verified prior session)
# This avoids quantalib's strict OHLCV signature for our resampled timeframes

ROOT = Path.home() / "qtl-discovery-8yr"
RAW = Path("/Volumes/Alien Device/direction_ml/raw_bars")
OUT = ROOT / "app_config_test"
OUT.mkdir(exist_ok=True)

PAIRS = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
PIP = {"AUD_JPY":0.01,"EUR_JPY":0.01,"USD_JPY":0.01,
       "AUD_USD":0.0001,"EUR_USD":0.0001,"GBP_USD":0.0001,
       "USD_CAD":0.0001,"USD_CHF":0.0001}
N_JOBS = 8

# Horizons in M5 bars (15/30/60/90/120 min)
HORIZONS_MIN = [15, 30, 60, 90, 120]

def wilder_rsi(close, period=14):
    """Wilder RSI: EWM(alpha=1/period) on gains/losses."""
    delta = close.astype(float).diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100/(1+rs)

def ema(close, span):
    return close.astype(float).ewm(span=span, adjust=False).mean()

def stoch_rsi(close, rsi_period=14, k_period=5, d_period=3):
    """StochRSI %K and %D (0-100 scale)."""
    rsi = wilder_rsi(close, rsi_period)
    rsi_min = rsi.rolling(rsi_period).min()
    rsi_max = rsi.rolling(rsi_period).max()
    stoch = (rsi - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan) * 100
    k = stoch.rolling(k_period).mean()
    d = k.rolling(d_period).mean()
    return k, d

def resample_ohlc(m5, rule):
    """Resample M5 OHLC to a higher timeframe using right-closed bars."""
    return m5.resample(rule, label='right', closed='right').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()

def session_from_hour(h):
    if 22 <= h or h <= 5: return 'asia'
    if 6 <= h <= 12:      return 'london'
    if 13 <= h <= 14:     return 'overlap'   # London/NY overlap
    return 'ny'

def detect_cross(series, level=50):
    """Returns (bull_cross, bear_cross) boolean Series — bar where series crosses level."""
    prev = series.shift(1)
    bull = (prev < level) & (series >= level)
    bear = (prev > level) & (series <= level)
    return bull, bear

def detect_event_cross(fast, slow):
    """EMA event cross — bull = fast crosses above slow, bear = fast crosses below."""
    d = fast - slow
    bull = (d.shift(1) <= 0) & (d > 0)
    bear = (d.shift(1) >= 0) & (d < 0)
    return bull, bear

# ── Per-pair pipeline ────────────────────────────────────────────────────────
def process_pair(pair):
    t0 = time.time()
    pip = PIP[pair]
    m5 = pd.read_parquet(RAW / f"{pair}_M5.parquet")
    # Resample to higher TFs
    m15 = resample_ohlc(m5, '15min')
    m30 = resample_ohlc(m5, '30min')
    h1  = resample_ohlc(m5, '1h')
    h4  = resample_ohlc(m5, '4h')

    # Indicators on each TF
    rsi7_m15 = wilder_rsi(m15['close'], 7)
    rsi7_m30 = wilder_rsi(m30['close'], 7)
    rsi7_h1  = wilder_rsi(h1['close'],  7)
    rsi7_h4  = wilder_rsi(h4['close'],  7)
    ema5_m15  = ema(m15['close'], 5);  ema20_m15 = ema(m15['close'], 20)
    ema5_m30  = ema(m30['close'], 5);  ema20_m30 = ema(m30['close'], 20)
    stochk_m15, stochd_m15 = stoch_rsi(m15['close'], 14, 5, 3)
    stochk_m5,  stochd_m5  = stoch_rsi(m5['close'],  14, 5, 3)

    # Detect crosses on M15 RSI7
    bull_rsi_m15, bear_rsi_m15 = detect_cross(rsi7_m15, 50)
    # EMA crosses on M15
    bull_ema_m15, bear_ema_m15 = detect_event_cross(ema5_m15, ema20_m15)
    # EMA states (per-bar) on M15 + M30
    ema_state_m15 = (ema5_m15 > ema20_m15)   # True = bullish state
    ema_state_m30 = (ema5_m30 > ema20_m30)

    # Helper: get higher-TF value as of m15-bar
    def asof_value(higher_series, m15_idx):
        # Reindex higher TF series to m15_idx using ffill (last known value)
        return higher_series.reindex(m15_idx, method='ffill')

    # Align all higher-TF stuff to m15 timeline
    rsi7_m30_at_m15 = asof_value(rsi7_m30, m15.index)
    rsi7_h1_at_m15  = asof_value(rsi7_h1,  m15.index)
    rsi7_h4_at_m15  = asof_value(rsi7_h4,  m15.index)
    ema_state_m30_at_m15 = asof_value(ema_state_m30, m15.index)
    # StochRSI: use M15 same TF
    stoch_m15_aligned = stochk_m15

    # Forward pip per signal — for each m15-bar signal time t, find the M5 bar at the same timestamp
    # Then compute close[t+horizon_bars] - close[t] using M5 close
    m5_close = m5['close']
    m5_index = m5.index

    # Pre-compute forward close at each horizon for every M5 bar
    fwd_close = {}
    for h_min in HORIZONS_MIN:
        bars = h_min // 5
        fwd_close[h_min] = m5_close.shift(-bars)

    # For each signal at m15 timestamp T: look up the M5 bar at T, get fwd_close at all horizons
    def fwd_pips_at(m15_signal_idx, side):
        """Returns dict of {h_min: signed_pip} for each horizon."""
        # m15 timestamp T = end of M15 bar. Use M5 bar at T (or just-before).
        m5_pos = m5_index.get_indexer(m15_signal_idx, method='ffill')
        valid = m5_pos >= 0
        if not valid.any(): return None
        results = {}
        for h_min in HORIZONS_MIN:
            entry_close = m5_close.iloc[m5_pos[valid]]
            entry_close.index = m15_signal_idx[valid]
            exit_close = fwd_close[h_min].iloc[m5_pos[valid]]
            exit_close.index = m15_signal_idx[valid]
            pip_move = (exit_close - entry_close) / pip
            if side == 'sell':
                pip_move = -pip_move
            results[h_min] = pip_move.dropna()
        return results

    # ── DEFINE THE 8 CONFIGS ─────────────────────────────────────────────────
    configs = {
        '1_rsi7_cross_only': {
            'buy_mask':  bull_rsi_m15,
            'sell_mask': bear_rsi_m15,
        },
        '2_rsi7_plus_m30': {
            'buy_mask':  bull_rsi_m15 & (rsi7_m30_at_m15 > 50),
            'sell_mask': bear_rsi_m15 & (rsi7_m30_at_m15 < 50),
        },
        '3_rsi7_plus_m30_h1': {
            'buy_mask':  bull_rsi_m15 & (rsi7_m30_at_m15 > 50) & (rsi7_h1_at_m15 > 50),
            'sell_mask': bear_rsi_m15 & (rsi7_m30_at_m15 < 50) & (rsi7_h1_at_m15 < 50),
        },
        '4_rsi7_plus_m30_h1_h4': {
            'buy_mask':  bull_rsi_m15 & (rsi7_m30_at_m15 > 50) & (rsi7_h1_at_m15 > 50) & (rsi7_h4_at_m15 > 50),
            'sell_mask': bear_rsi_m15 & (rsi7_m30_at_m15 < 50) & (rsi7_h1_at_m15 < 50) & (rsi7_h4_at_m15 < 50),
        },
        '5_rsi7_plus_ema_m15_state': {
            'buy_mask':  bull_rsi_m15 & ema_state_m15,
            'sell_mask': bear_rsi_m15 & ~ema_state_m15,
        },
        '6_rsi7_plus_ema_m30_state': {
            'buy_mask':  bull_rsi_m15 & ema_state_m30_at_m15,
            'sell_mask': bear_rsi_m15 & ~ema_state_m30_at_m15,
        },
        '7_rsi_align_plus_ema_state': {
            'buy_mask':  bull_rsi_m15 & (rsi7_m30_at_m15 > 50) & (rsi7_h1_at_m15 > 50) & ema_state_m15,
            'sell_mask': bear_rsi_m15 & (rsi7_m30_at_m15 < 50) & (rsi7_h1_at_m15 < 50) & ~ema_state_m15,
        },
        '8_full_with_stoch_filter': {
            'buy_mask':  bull_rsi_m15 & (rsi7_m30_at_m15 > 50) & (rsi7_h1_at_m15 > 50)
                          & ema_state_m15 & (stoch_m15_aligned < 80),
            'sell_mask': bear_rsi_m15 & (rsi7_m30_at_m15 < 50) & (rsi7_h1_at_m15 < 50)
                          & ~ema_state_m15 & (stoch_m15_aligned > 20),
        },
    }

    # ── Per-config signal scan + forward measurement ────────────────────────
    rows = []
    for cname, cfg in configs.items():
        for side, mask in [('buy', cfg['buy_mask']), ('sell', cfg['sell_mask'])]:
            mask = mask.fillna(False)
            sig_times = m15.index[mask]
            if len(sig_times) == 0: continue
            fwd = fwd_pips_at(sig_times, side)
            if fwd is None: continue
            # For each signal: record + session classification
            for ts in fwd[60].index:
                rows.append({
                    'pair': pair, 'config': cname, 'side': side,
                    'signal_time': ts,
                    'session': session_from_hour(ts.hour),
                    'fwd_15m': fwd[15].get(ts, np.nan),
                    'fwd_30m': fwd[30].get(ts, np.nan),
                    'fwd_60m': fwd[60].get(ts, np.nan),
                    'fwd_90m': fwd[90].get(ts, np.nan),
                    'fwd_120m': fwd[120].get(ts, np.nan),
                })

    df = pd.DataFrame(rows)
    elapsed = time.time() - t0
    print(f"  {pair}: {len(df):,} signals across 8 configs in {elapsed:.1f}s")
    return df

if __name__ == '__main__':
    print(f"App-config tester: 8 configs × 8 pairs × 8yr corpus")
    print(f"Parallel across {N_JOBS} cores...")
    t0 = time.time()
    results = Parallel(n_jobs=N_JOBS, verbose=10)(delayed(process_pair)(p) for p in PAIRS)
    print(f"\nTotal compute: {time.time()-t0:.1f}s")

    all_signals = pd.concat(results, ignore_index=True)
    all_signals.to_csv(OUT / 'all_signals_raw.csv', index=False)
    print(f"\nTotal signals: {len(all_signals):,}")
    print(f"→ {OUT / 'all_signals_raw.csv'} ({os.path.getsize(OUT/'all_signals_raw.csv')/1e6:.1f} MB)")

    # ── Aggregate per config × per pair × per session ────────────────────────
    def agg_stats(g):
        n = len(g)
        if n == 0: return None
        fwd = g['fwd_60m'].dropna()
        if len(fwd) == 0: return None
        wins = (fwd > 0).sum()
        losses = (fwd < 0).sum()
        wr = wins / len(fwd)
        avg_win = fwd[fwd > 0].mean() if wins else 0
        avg_loss = fwd[fwd < 0].mean() if losses else 0  # negative
        pf = (-avg_win * wins) / (avg_loss * losses) if losses and avg_loss else float('inf')
        expectancy = wr * avg_win + (1 - wr) * avg_loss
        return pd.Series({
            'n': len(fwd),
            'wr': round(wr, 3),
            'avg_pips': round(fwd.mean(), 2),
            'median_pips': round(fwd.median(), 2),
            'avg_win': round(avg_win, 2) if wins else 0,
            'avg_loss': round(avg_loss, 2) if losses else 0,
            'profit_factor': round(pf, 2) if not np.isinf(pf) else 0,
            'expectancy': round(expectancy, 2),
            'pct_reach_3p': round((fwd >= 3).mean(), 3),
            'pct_reach_5p': round((fwd >= 5).mean(), 3),
            'pct_loss_3p':  round((fwd <= -3).mean(), 3),
        })

    print(f"\n=== AGGREGATING: config × pair × session ===")
    by_cps = all_signals.groupby(['config', 'pair', 'session']).apply(agg_stats).reset_index()
    by_cps.to_csv(OUT / 'per_config_pair_session.csv', index=False)
    print(f"→ {OUT / 'per_config_pair_session.csv'}")

    # Per config × pair (all sessions)
    by_cp = all_signals.groupby(['config', 'pair']).apply(agg_stats).reset_index()
    by_cp.to_csv(OUT / 'per_config_pair.csv', index=False)

    # Per config (all pairs, all sessions) — Brock's main table
    by_c = all_signals.groupby('config').apply(agg_stats).reset_index()
    by_c = by_c.sort_values('expectancy', ascending=False)
    by_c.to_csv(OUT / 'per_config_summary.csv', index=False)

    # Per config × session
    by_cs = all_signals.groupby(['config', 'session']).apply(agg_stats).reset_index()
    by_cs.to_csv(OUT / 'per_config_session.csv', index=False)

    print(f"\n=== SUMMARY: per-config across all pairs/sessions (ranked by expectancy) ===")
    print(by_c.to_string(index=False))

    print(f"\n=== PER-CONFIG × SESSION ===")
    pivot = by_cs.pivot_table(index='config', columns='session', values='expectancy', aggfunc='first')
    print(pivot.round(2).to_string())

    # Best pair per config
    print(f"\n=== BEST PAIR PER CONFIG (by expectancy, n>=100) ===")
    sig = by_cp[by_cp['n'] >= 100].copy()
    if len(sig) > 0:
        best_per_config = sig.loc[sig.groupby('config')['expectancy'].idxmax()]
        print(best_per_config[['config','pair','n','wr','avg_pips','expectancy','profit_factor']].to_string(index=False))
    else:
        print("(no cells with n>=100)")
