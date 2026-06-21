"""8yr per-pair feature computation: V5 baseline + 30 qtl candidate indicators
   + forward-return label. Parallel across 8 cores. Runs on Mini ONLY.

For each pair: load M5/H1/D parquets, compute features at every M5 bar
(joining most-recent H1/D values via merge_asof), compute label
sign(close[t+H] - close[t]) at H=12 M5 bars (1H forward return).

Output: ~/qtl-discovery-8yr/features/<PAIR>_features.parquet
"""
import os, sys, socket, subprocess, time
from pathlib import Path
from datetime import timezone
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
import quantalib as qtl

# ── DEVICE SAFETY ─────────────────────────────────────────────────────────────
def assert_on_mini():
    serial = subprocess.run(["system_profiler", "SPHardwareDataType"], capture_output=True, text=True).stdout
    if "CPYQTH294R" not in serial:
        raise RuntimeError(f"NOT ON MINI! Serial not CPYQTH294R. Refusing to run heavy compute.")
    print(f"✓ device verified: Mini CPYQTH294R")

assert_on_mini()

ROOT      = Path.home() / "qtl-discovery-8yr"
RAW_BARS  = Path("/Volumes/Alien Device/direction_ml/raw_bars")
OUT       = ROOT / "features"
OUT.mkdir(parents=True, exist_ok=True)

PAIRS = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
PIP_SIZE = {p: (0.01 if "JPY" in p else 0.0001) for p in PAIRS}
N_JOBS = 8   # Brock said 8/10 cores

# Forward-return horizons (in M5 bars)
HORIZON_BARS = 12   # 60 min = 12 M5 bars

# ── V5 BASELINE FEATURES (lifted from core/feed/oanda.py + base.py) ─────────
def v5_baseline_features(m5: pd.DataFrame, h1: pd.DataFrame, d: pd.DataFrame, pip: float) -> pd.DataFrame:
    """Compute V5's 24 direction features at every M5 bar. Pure-pandas vector ops."""
    df = m5.copy()
    close = df["close"]; high = df["high"]; low = df["low"]
    # 5m vol/regime
    df["atr_5m"]     = _wilder_atr(high, low, close, 14) / pip
    df["bb_width"]   = (close.rolling(20).std(ddof=1) * 4) / pip   # 2σ band width in pips
    df["bb_mid"]     = close.rolling(20).mean()
    df["bb_std"]     = close.rolling(20).std(ddof=1)
    df["bb_pos"]     = (close - (df["bb_mid"] - 2*df["bb_std"])) / (4*df["bb_std"])
    df["zscore_5m"]  = (close - close.rolling(20).mean()) / close.rolling(20).std(ddof=1)
    df["ema20"]      = close.ewm(span=20, adjust=False).mean()
    df["ema5"]       = close.ewm(span=5,  adjust=False).mean()
    df["ema50"]      = close.ewm(span=50, adjust=False).mean()
    df["ema20_dist_pct"] = (close - df["ema20"]) / close
    df["ema5_dist_pips"] = (close - df["ema5"]) / pip
    df["ema50_dist_pct"] = (close - df["ema50"]) / close
    df["ema_cross_pips"] = (close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()) / pip
    df["ret_5m"]   = close.diff() / pip
    df["ret_15m"]  = (close - close.shift(3))  / pip
    df["ret_30m"]  = (close - close.shift(6))  / pip
    df["ret_1h"]   = (close - close.shift(12)) / pip
    df["rvol_5bar"]  = df["volume"].rolling(5).mean()  / df["volume"].rolling(32).mean()
    df["rvol_12bar"] = df["volume"].rolling(12).mean() / df["volume"].rolling(32).mean()
    df["range_5bar"]  = (high.rolling(5).max()  - low.rolling(5).min())  / pip
    df["range_12bar"] = (high.rolling(12).max() - low.rolling(12).min()) / pip

    # H1 features — join most-recent completed H1 bar
    h1f = h1.copy()
    h1c = h1f["close"]; h1h = h1f["high"]; h1l = h1f["low"]
    h1f["h1_ret_1bar"] = (h1c - h1c.shift(1)) / pip
    h1f["h1_ret_4bar"] = (h1c - h1c.shift(4)) / pip
    h1f["trend_4h"]    = np.sign(h1f["h1_ret_4bar"]).fillna(0)
    delta = h1c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    h1f["rsi14_h1"] = 100 - 100/(1+rs)
    h1f["rsi_slope"] = h1f["rsi14_h1"] - h1f["rsi14_h1"].shift(3)
    h1f["zscore_1h"] = (h1c - h1c.rolling(20).mean()) / h1c.rolling(20).std(ddof=1)
    h1f["ema20_1h"]  = h1c.ewm(span=20, adjust=False).mean()
    h1f["ema20_1h_dist"] = (h1c - h1f["ema20_1h"]) / h1c
    h1f["atr_1h"]    = _wilder_atr(h1h, h1l, h1c, 14) / pip
    # atr_h1_relative: current ATR / 100-bar rolling mean
    h1_atr_raw = _wilder_atr(h1h, h1l, h1c, 14)
    h1f["atr_h1_relative"] = (h1_atr_raw / h1_atr_raw.rolling(100, min_periods=20).mean()).fillna(1.0)
    h1f_subset = h1f[["h1_ret_1bar","h1_ret_4bar","trend_4h","rsi14_h1","rsi_slope","zscore_1h",
                       "ema20_1h_dist","atr_1h","atr_h1_relative"]].reset_index()
    h1f_subset.columns = ["h1_time"] + list(h1f_subset.columns[1:])

    # Daily features
    df_d = d.copy()
    df_d["pdh"]        = df_d["high"].shift(1)
    df_d["pdl"]        = df_d["low"].shift(1)
    df_d["d_ret_pct"]  = df_d["close"].pct_change()
    df_d["htf_pct_20"] = df_d["close"].pct_change(20)
    df_d["htf_pct_60"] = df_d["close"].pct_change(60)
    atr_d_raw = _wilder_atr(df_d["high"], df_d["low"], df_d["close"], 14)
    df_d["atr_d_pips"] = atr_d_raw / pip
    df_d_subset = df_d[["pdh","pdl","d_ret_pct","htf_pct_20","htf_pct_60","atr_d_pips",
                          "high","low","close"]].reset_index()
    df_d_subset.columns = ["d_time","pdh","pdl","d_ret_pct","htf_pct_20","htf_pct_60",
                              "atr_d_pips","d_high","d_low","d_close"]

    # Merge: as-of join M5 ← H1 (backward; H1 from before this M5 bar) ← D
    df_reset = df.reset_index()
    df_reset = pd.merge_asof(df_reset, h1f_subset, left_on="time", right_on="h1_time",
                              direction="backward").drop(columns=["h1_time"])
    df_reset = pd.merge_asof(df_reset, df_d_subset, left_on="time", right_on="d_time",
                              direction="backward").drop(columns=["d_time"])
    df = df_reset.set_index("time")

    # Daily-derived (using joined daily values)
    df["pdh_dist"]         = (df["close"] - df["pdh"]) / pip
    df["pdl_dist"]         = (df["close"] - df["pdl"]) / pip
    df["pdh_dist_atr_pct"] = df["pdh_dist"] / df["atr_d_pips"]
    df["pdl_dist_atr_pct"] = df["pdl_dist"] / df["atr_d_pips"]
    df["close_pos_daily"]  = (df["close"] - df["d_low"]) / (df["d_high"] - df["d_low"]).replace(0, np.nan)
    df["d_ret"]            = df["d_ret_pct"] * 10000 if "JPY" not in str(df.index.name) else df["d_ret_pct"] * 100  # rough pips conversion via %
    df["adr_consumed"]     = ((df["d_high"] - df["d_low"]) / pip) / df["atr_d_pips"]
    df["atr_conc"]         = df["atr_5m"] / df["atr_1h"].replace(0, np.nan)

    return df

def _wilder_atr(high, low, close, period):
    pc = close.shift(1)
    tr = pd.concat([(high - low).abs(), (high - pc).abs(), (low - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()

# ── QTL CANDIDATE INDICATORS ─────────────────────────────────────────────────
def qtl_features(m5: pd.DataFrame, h1_aligned: pd.DataFrame) -> pd.DataFrame:
    """Compute the qtl candidate indicators. Returns DataFrame indexed like m5."""
    df = pd.DataFrame(index=m5.index)
    o, h, l, c, v = m5["open"], m5["high"], m5["low"], m5["close"], m5["volume"]

    # Volume (M5)
    df["q_obv"]      = _safe(qtl.obv,  c, v)
    df["q_cmf"]      = _safe(qtl.cmf,  h, l, c, v, period=20)
    df["q_mfi"]      = _safe(qtl.mfi,  h, l, c, v, period=14)
    df["q_adl"]      = _safe(qtl.adl,  h, l, c, v)
    df["q_adosc"]    = _safe(qtl.adosc, h, l, c, v)
    df["q_efi"]      = _safe(qtl.efi,  c, v, period=13)
    # Oscillators (M5)
    df["q_cci_m5"]   = _safe(qtl.cci, o, h, l, c, v, period=20)
    df["q_willr_m5"] = _safe(qtl.willr, h, l, c, period=14)
    df["q_fisher_m5"]= _safe(qtl.fisher, c, period=10)
    df["q_tsi_m5"]   = _safe(qtl.tsi, c, longPeriod=25, shortPeriod=13)
    macd = _safe_tuple(qtl.macd, c, fastPeriod=12, slowPeriod=26, signalPeriod=9)
    df["q_macd_m5"] = _safe(qtl.macd, c, fastPeriod=12, slowPeriod=26, signalPeriod=9)
    df["q_stochrsi_m5"] = _safe(qtl.stochrsi, c, period=14)
    # Channels (M5) — qtl returns DataFrame with named columns 'middle','upper','lower'
    dc = _safe_df(qtl.dchannel, h, l, period=20)
    if dc is not None and "upper" in dc.columns:
        df["q_dc_up_dist_pips"] = (c - dc["upper"]) / _pip(m5)
        df["q_dc_lo_dist_pips"] = (c - dc["lower"]) / _pip(m5)
    kc = _safe_df(qtl.kchannel, h, l, c, period=20, multiplier=2.0)
    if kc is not None and "upper" in kc.columns:
        df["q_kc_up_dist_pips"] = (c - kc["upper"]) / _pip(m5)
    # VWAP proxy (M5 96-bar rolling)
    tp = (h + l + c) / 3
    rv = (tp * v).rolling(96).sum() / v.rolling(96).sum()
    df["q_vwap_dist_pips_m5"] = (c - rv) / _pip(m5)
    # Volatility (M5)
    df["q_bbwp_m5"]  = _safe(qtl.bbwp, c, period=20, lookback=100)
    df["q_atrn_m5"]  = _safe(qtl.atrn, o, h, l, c, v, period=14)
    df["q_yzv_m5"]   = _safe(qtl.yzv,  o, h, l, c, period=20)
    # Cycles (M5)
    df["q_ht_dcperiod_m5"] = _safe(qtl.ht_dcperiod, c)
    df["q_ht_dcphase_m5"]  = _safe(qtl.ht_dcphase,  c)
    df["q_ebsw_m5"]        = _safe(qtl.ebsw,        c)
    # Statistics (M5)
    df["q_hurst_m5"]    = _safe(qtl.hurst,    c, period=100)
    df["q_entropy_m5"]  = _safe(qtl.entropy,  c, period=100)
    df["q_kurtosis_m5"] = _safe(qtl.kurtosis, c, period=100)
    df["q_skew_m5"]     = _safe(qtl.skew,     c, period=100)
    # Dynamics (H1)  — these go through h1_aligned so the same H1 value applies until next H1 bar
    if h1_aligned is not None:
        h1o, h1h, h1l, h1c, h1v = (h1_aligned["open"], h1_aligned["high"], h1_aligned["low"],
                                    h1_aligned["close"], h1_aligned["volume"])
        df["q_chop_h1"]     = _safe(qtl.chop, h1o, h1h, h1l, h1c, h1v, period=14)
        df["q_aroonosc_h1"] = _safe(qtl.aroonosc, h1h, h1l, period=14)
        df["q_vhf_h1"]      = _safe(qtl.vhf, h1c, period=28)
        vrtx = _safe_df(qtl.vortex, h1h, h1l, h1c, period=14)
        if vrtx is not None and "viPlus" in vrtx.columns:
            df["q_vortex_diff_h1"] = vrtx["viPlus"] - vrtx["viMinus"]
        st = _safe(qtl.supertrend, h1o, h1h, h1l, h1c, h1v, period=10, multiplier=3.0)
        df["q_super_dist_h1"] = (h1c - st) / _pip(m5)
        df["q_adx_h1"] = _safe(qtl.adx, h1h, h1l, h1c, period=14)
    return df

def _pip(m5):
    # Infer pip from close magnitude (>50 → JPY pair, pip=0.01; else 0.0001)
    return 0.01 if m5["close"].iloc[-1] > 10 else 0.0001

def _safe(fn, *args, **kw):
    try:
        r = fn(*args, **kw)
        if r is None: return pd.Series(np.nan, index=args[0].index if hasattr(args[0], 'index') else None)
        return pd.Series(np.asarray(r), index=args[0].index)
    except Exception as e:
        return pd.Series(np.nan, index=args[0].index)

def _safe_tuple(fn, *args, **kw):
    try:
        r = fn(*args, **kw)
        if r is None: return None
        if isinstance(r, tuple): return r
        if isinstance(r, pd.DataFrame): return tuple(r.iloc[:, i] for i in range(r.shape[1]))
        return (pd.Series(np.asarray(r), index=args[0].index),)
    except Exception:
        return None

def _safe_df(fn, *args, **kw):
    try:
        r = fn(*args, **kw)
        if isinstance(r, pd.DataFrame): return r
        if isinstance(r, tuple): return pd.DataFrame({f"c{i}": s for i, s in enumerate(r)})
        return None
    except Exception:
        return None

# ── PER-PAIR PIPELINE ────────────────────────────────────────────────────────
def session_from_hour(hr: int) -> str:
    if 22 <= hr or hr <= 5: return "asia"
    if 6 <= hr <= 12:       return "london"
    return "ny"

def process_pair(pair: str) -> dict:
    t0 = time.time()
    pip = PIP_SIZE[pair]
    m5 = pd.read_parquet(RAW_BARS / f"{pair}_M5.parquet")
    h1 = pd.read_parquet(RAW_BARS / f"{pair}_H1.parquet")
    d  = pd.read_parquet(RAW_BARS / f"{pair}_D.parquet")

    # V5 baseline features (joins h1 + d as-of)
    base = v5_baseline_features(m5, h1, d, pip)

    # For qtl H1-section, build an h1-aligned dataframe at M5 resolution
    h1_aligned = h1.reindex(m5.index, method="ffill")

    # qtl candidates
    qtl_df = qtl_features(m5, h1_aligned)
    full = pd.concat([base, qtl_df], axis=1)

    # Label: sign of forward 1H return (12 M5 bars)
    full["fwd_ret_pips"] = (m5["close"].shift(-HORIZON_BARS) - m5["close"]) / pip
    full["label"] = np.sign(full["fwd_ret_pips"]).fillna(0).astype(int)

    # Session tag
    full["session"] = full.index.hour.map(session_from_hour)

    # Drop bars where label is 0 (rare; mostly weekend gap) or label is NaN at the tail
    full = full[full["label"] != 0].copy()
    full = full.dropna(subset=["label"])

    # Save
    out = OUT / f"{pair}_features.parquet"
    full.to_parquet(out)
    elapsed = time.time() - t0
    return {"pair": pair, "rows": len(full), "out": str(out), "elapsed_s": elapsed,
            "n_features": len([c for c in full.columns if c not in ("session","label","fwd_ret_pips")])}

if __name__ == "__main__":
    print(f"computing 8yr features for {len(PAIRS)} pairs across {N_JOBS} cores")
    t0 = time.time()
    results = Parallel(n_jobs=N_JOBS, verbose=10)(delayed(process_pair)(p) for p in PAIRS)
    print(f"\nTotal time: {time.time() - t0:.1f}s")
    for r in results:
        print(f"  {r['pair']}: {r['rows']:,} bars  {r['n_features']} features  {r['elapsed_s']:.1f}s  → {r['out']}")
