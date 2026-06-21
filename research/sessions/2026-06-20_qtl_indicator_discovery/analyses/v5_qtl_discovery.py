"""Phase 2: per-trade qtl-indicator sweep + accuracy + orthogonality vs V5 features.

For each of 44 trades, compute ~25 qtl indicators at entry_time, then:
  - Signed indicators: predict direction, measure accuracy vs actual price movement
  - Magnitude indicators: bucket by quartile, measure WR delta high vs low
  - Orthogonality: max correlation with V5's existing features
Output: ranked table + per-area markdown report.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import quantalib as qtl

BUNDLE = Path.home() / "qtl-discovery" / "v5_qtl_prefetch_bundle.json"
MATRIX_V2 = Path.home() / "qtl-discovery" / "v5_full_matrix_v2.csv"
OUT_DIR = Path.home() / "qtl-discovery"

bundle = json.loads(BUNDLE.read_text())
matrix = pd.read_csv(MATRIX_V2)
matrix["tid"] = matrix["tid"].astype(str)
print(f"loaded {len(bundle['trades'])} trades with candles; matrix has {len(matrix)} rows")

PIP_SIZE = {
    "AUD_USD":0.0001, "EUR_USD":0.0001, "GBP_USD":0.0001, "USD_CAD":0.0001,
    "USD_JPY":0.01,   "USD_CHF":0.0001, "AUD_JPY":0.01,   "EUR_JPY":0.01,
}

def candles_to_arrays(candle_rows):
    """[[time, o, h, l, c, v], ...] → o, h, l, c, v as np float arrays"""
    if not candle_rows: return None
    a = np.array([(r[1], r[2], r[3], r[4], r[5]) for r in candle_rows], dtype=np.float64)
    return a[:,0], a[:,1], a[:,2], a[:,3], a[:,4]  # o, h, l, c, v

def safe_last(x):
    """Return last element as float, or NaN if empty/None/all NaN."""
    if x is None: return np.nan
    if hasattr(x, "__len__") and len(x) == 0: return np.nan
    try:
        v = float(np.asarray(x)[-1])
        return v if not np.isnan(v) else np.nan
    except Exception:
        return np.nan

def safe_call(fn, *args, **kw):
    """Call qtl fn; return result or None on error."""
    try:
        r = fn(*args, **kw)
        return r
    except Exception as e:
        return None

# Per-trade feature extraction
def compute_features(tid, pair, candles):
    f = {}
    pip = PIP_SIZE[pair]
    m5 = candles_to_arrays(candles["m5"])
    h1 = candles_to_arrays(candles["h1"])
    if m5 is None or h1 is None: return f
    o5, h5, l5, c5, v5 = m5
    o1, h1h, l1, c1, v1h = h1
    close_m5 = pd.Series(c5); close_h1 = pd.Series(c1)
    high_m5 = pd.Series(h5);  high_h1 = pd.Series(h1h)
    low_m5 = pd.Series(l5);   low_h1 = pd.Series(l1)
    open_m5 = pd.Series(o5);  open_h1 = pd.Series(o1)
    vol_m5 = pd.Series(v5);   vol_h1 = pd.Series(v1h)
    last_close = float(c5[-1])

    # ── VOLUME (M5 tick-volume) ────────────────────────────────────────────────
    f["obv"]   = safe_last(safe_call(qtl.obv,   close_m5, vol_m5))
    f["cmf"]   = safe_last(safe_call(qtl.cmf,   high_m5, low_m5, close_m5, vol_m5, period=20))
    f["mfi"]   = safe_last(safe_call(qtl.mfi,   high_m5, low_m5, close_m5, vol_m5, period=14))
    f["adl"]   = safe_last(safe_call(qtl.adl,   high_m5, low_m5, close_m5, vol_m5))
    f["adosc"] = safe_last(safe_call(qtl.adosc, high_m5, low_m5, close_m5, vol_m5))
    f["efi"]   = safe_last(safe_call(qtl.efi,   close_m5, vol_m5, period=13))

    # ── DYNAMICS / TREND STRENGTH (H1) ────────────────────────────────────────
    # ADX already in matrix as adx14_h1, skip
    f["chop_h1"]      = safe_last(safe_call(qtl.chop,     open_h1, high_h1, low_h1, close_h1, vol_h1, period=14))
    f["aroonosc_h1"]  = safe_last(safe_call(qtl.aroonosc, high_h1, low_h1, period=14))
    # SuperTrend returns array of trend values; we want the most recent value's sign-of-cross to price
    # supertrend signature: (open, high, low, close, volume, period, multiplier)
    super_st = safe_call(qtl.supertrend, open_h1, high_h1, low_h1, close_h1, vol_h1,
                         period=10, multiplier=3.0)
    if super_st is not None:
        # If it's a tuple/DataFrame, take the trend line as the comparison
        if isinstance(super_st, tuple): st_val = safe_last(super_st[0])
        elif isinstance(super_st, pd.DataFrame): st_val = safe_last(super_st.iloc[:,0])
        else: st_val = safe_last(super_st)
        f["super_dist_h1"] = (last_close - st_val) / pip if not np.isnan(st_val) else np.nan
    else:
        f["super_dist_h1"] = np.nan
    f["vhf_h1"] = safe_last(safe_call(qtl.vhf, close_h1, period=28))
    # Vortex: usually returns (+VI, -VI); use VI+ - VI- as signed measure
    vortex = safe_call(qtl.vortex, high_h1, low_h1, close_h1, period=14)
    if vortex is not None:
        if isinstance(vortex, tuple) and len(vortex) >= 2:
            f["vortex_diff_h1"] = safe_last(vortex[0]) - safe_last(vortex[1])
        elif isinstance(vortex, pd.DataFrame):
            cols = list(vortex.columns)
            if len(cols) >= 2:
                f["vortex_diff_h1"] = safe_last(vortex.iloc[:,0]) - safe_last(vortex.iloc[:,1])
            else:
                f["vortex_diff_h1"] = safe_last(vortex.iloc[:,0])
        else:
            f["vortex_diff_h1"] = safe_last(vortex)
    else: f["vortex_diff_h1"] = np.nan

    # ── OSCILLATORS (mix of M5 + H1) ──────────────────────────────────────────
    macd = safe_call(qtl.macd, close_m5, fastPeriod=12, slowPeriod=26, signalPeriod=9)
    if macd is not None:
        if isinstance(macd, tuple) and len(macd) >= 3:
            f["macd_hist_m5"] = safe_last(macd[2])
        elif isinstance(macd, pd.DataFrame):
            cols = [c for c in macd.columns if "hist" in c.lower() or "h_" in c.lower()]
            f["macd_hist_m5"] = safe_last(macd[cols[0]]) if cols else safe_last(macd.iloc[:,-1])
        else:
            f["macd_hist_m5"] = safe_last(macd)
    else: f["macd_hist_m5"] = np.nan
    f["cci_m5"]      = safe_last(safe_call(qtl.cci,      open_m5, high_m5, low_m5, close_m5, vol_m5, period=20))
    f["willr_m5"]    = safe_last(safe_call(qtl.willr,    high_m5, low_m5, close_m5, period=14))
    f["fisher_m5"]   = safe_last(safe_call(qtl.fisher,   close_m5, period=10))
    f["tsi_m5"]      = safe_last(safe_call(qtl.tsi,      close_m5, longPeriod=25, shortPeriod=13))
    stochrsi = safe_call(qtl.stochrsi, close_m5, period=14)
    if stochrsi is not None:
        if isinstance(stochrsi, tuple): f["stochrsi_m5"] = safe_last(stochrsi[0])
        elif isinstance(stochrsi, pd.DataFrame): f["stochrsi_m5"] = safe_last(stochrsi.iloc[:,0])
        else: f["stochrsi_m5"] = safe_last(stochrsi)
    else: f["stochrsi_m5"] = np.nan

    # ── CHANNELS / LEVELS (M5) ────────────────────────────────────────────────
    # Donchian-20 on M5 (qtl.dchannel)
    dc = safe_call(qtl.dchannel, high_m5, low_m5, period=20)
    if dc is not None:
        if isinstance(dc, pd.DataFrame):
            cols = list(dc.columns)
            # Heuristic: 1st col upper, 2nd col middle, 3rd lower (or look for 'upper'/'lower')
            up_col = next((c for c in cols if any(k in c.lower() for k in ("u_", "upper", "uppr"))), cols[0])
            lo_col = next((c for c in cols if any(k in c.lower() for k in ("l_", "lower"))),       cols[-1])
            f["dc_up_dist_pips"] = (last_close - safe_last(dc[up_col])) / pip
            f["dc_lo_dist_pips"] = (last_close - safe_last(dc[lo_col])) / pip
        elif isinstance(dc, tuple) and len(dc) >= 2:
            f["dc_up_dist_pips"] = (last_close - safe_last(dc[0])) / pip
            f["dc_lo_dist_pips"] = (last_close - safe_last(dc[-1])) / pip
        else:
            f["dc_up_dist_pips"] = np.nan; f["dc_lo_dist_pips"] = np.nan
    else:
        f["dc_up_dist_pips"] = np.nan; f["dc_lo_dist_pips"] = np.nan
    # Keltner-20 ATR-mult=2 (qtl.kchannel)
    kc = safe_call(qtl.kchannel, high_m5, low_m5, close_m5, period=20, multiplier=2.0)
    if kc is not None:
        if isinstance(kc, pd.DataFrame):
            cols = list(kc.columns)
            up_col = next((c for c in cols if any(k in c.lower() for k in ("u_","upper"))), cols[0])
            f["kc_up_dist_pips"] = (last_close - safe_last(kc[up_col])) / pip
        elif isinstance(kc, tuple): f["kc_up_dist_pips"] = (last_close - safe_last(kc[0])) / pip
        else: f["kc_up_dist_pips"] = np.nan
    else: f["kc_up_dist_pips"] = np.nan
    # Anchored VWAP on M5: use rolling 96-bar (8h) VWAP as a proxy for session VWAP
    typprice = (high_m5 + low_m5 + close_m5) / 3
    rolling_vwap = (typprice * vol_m5).rolling(96).sum() / vol_m5.rolling(96).sum()
    vwap_val = safe_last(rolling_vwap)
    f["vwap_dist_pips_m5"] = (last_close - vwap_val) / pip if not np.isnan(vwap_val) else np.nan

    # ── VOLATILITY (M5) ──────────────────────────────────────────────────────
    f["bbwp_m5"] = safe_last(safe_call(qtl.bbwp, close_m5, period=20, lookback=100))
    f["atrn_m5"] = safe_last(safe_call(qtl.atrn, open_m5, high_m5, low_m5, close_m5, vol_m5, period=14))
    f["yzv_m5"]  = safe_last(safe_call(qtl.yzv, open_m5, high_m5, low_m5, close_m5, period=20))

    # ── CYCLES (M5) ──────────────────────────────────────────────────────────
    f["ht_dcperiod_m5"] = safe_last(safe_call(qtl.ht_dcperiod, close_m5))
    f["ht_dcphase_m5"]  = safe_last(safe_call(qtl.ht_dcphase,  close_m5))
    f["ebsw_m5"]        = safe_last(safe_call(qtl.ebsw,        close_m5))

    # ── STATISTICAL REGIME (M5) ──────────────────────────────────────────────
    f["hurst_m5"]    = safe_last(safe_call(qtl.hurst,    close_m5, period=100))
    f["entropy_m5"]  = safe_last(safe_call(qtl.entropy,  close_m5, period=100))
    f["kurtosis_m5"] = safe_last(safe_call(qtl.kurtosis, close_m5, period=100))
    f["skew_m5"]     = safe_last(safe_call(qtl.skew,     close_m5, period=100))

    return f

# ── Compute features for all trades ───────────────────────────────────────────
print("\n=== computing features for 44 trades ===")
rows = []
for t in bundle["trades"]:
    feats = compute_features(t["tid"], t["pair"], bundle["candles"][t["tid"]])
    feats["tid"] = t["tid"]; feats["pair"] = t["pair"]; feats["dir"] = t["dir"]
    feats["session"] = t["session"]; feats["exit_net"] = t["exit_net"]
    rows.append(feats)
df = pd.DataFrame(rows)
print(f"  computed {len(df.columns)-5} features × {len(df)} trades")
# Coverage check
print("  NaN counts per feature:")
for c in df.columns:
    if c not in ("tid","pair","dir","session","exit_net"):
        nn = df[c].isna().sum()
        if nn > 0: print(f"    {c}: {nn} NaN / {len(df)}")

# ── Build target arrays ──────────────────────────────────────────────────────
df["dir_sign"]       = df["dir"].map({"long": 1, "short": -1})
df["realized_sign"]  = np.sign(df["exit_net"])
# Actual price movement direction = trade dir × win/loss sign
df["actual_price_dir"] = df["dir_sign"] * df["realized_sign"]
df["win"]            = (df["exit_net"] > 0).astype(int)
print(f"\nTotal: {df['win'].sum()}/{len(df)} wins  ({df['win'].mean()*100:.0f}% WR)")

# ── Join V5 features for orthogonality check ─────────────────────────────────
m2 = matrix[["tid","atr_5m","atr_1h","atr_conc","atr_h1_relative","wall_frac",
             "rvol_5bar","rvol_12bar","rsi14_m5","rsi14_h1","bb_pos_h1","htf_pct_20","htf_pct_60",
             "ema20_dist_pct","ema50_dist_pct","adx14_h1","adr_consumed","composite"]]
df_full = df.merge(m2, on="tid", how="left")
v5_cols = ["atr_5m","atr_1h","atr_conc","atr_h1_relative","wall_frac","rvol_5bar","rvol_12bar",
           "rsi14_m5","rsi14_h1","bb_pos_h1","htf_pct_20","htf_pct_60","ema20_dist_pct","ema50_dist_pct",
           "adx14_h1","adr_consumed","composite"]

# ── Per-feature analysis ──────────────────────────────────────────────────────
INDICATORS = [c for c in df.columns if c not in ("tid","pair","dir","session","exit_net",
                                                  "dir_sign","realized_sign","actual_price_dir","win")]
# Classify: signed (zero-centered) vs magnitude (positive-only)
SIGNED = {"obv","cmf","mfi","adl","adosc","efi","aroonosc_h1","super_dist_h1","vortex_diff_h1",
          "macd_hist_m5","cci_m5","fisher_m5","tsi_m5","dc_up_dist_pips","dc_lo_dist_pips",
          "kc_up_dist_pips","vwap_dist_pips_m5","ebsw_m5","ht_dcphase_m5","skew_m5"}
# WILLR is -100..0, treat as signed via 50-distance: signed = willr + 50
# stochrsi is 0..100; signed = stochrsi - 50
# Magnitude: chop_h1, vhf_h1, bbwp_m5, atrn_m5, yzv_m5, ht_dcperiod_m5, hurst_m5, entropy_m5, kurtosis_m5, mfi (0-100 signed via -50)
SIGNED_CENTERED_50 = {"willr_m5":50, "stochrsi_m5":50, "mfi":50}
MAGNITUDE = {"chop_h1","vhf_h1","bbwp_m5","atrn_m5","yzv_m5","ht_dcperiod_m5","hurst_m5","entropy_m5","kurtosis_m5"}

def directional_accuracy(feature_vals, actual_dir, center=0):
    """For signed features: pred = sign(feature - center); accuracy vs actual_price_dir."""
    valid = ~feature_vals.isna()
    if valid.sum() < 10: return np.nan, 0
    pred = np.sign(feature_vals[valid] - center)
    pred = pred.replace(0, 1)  # treat exact-zero as long-pred (conservative)
    actual = actual_dir[valid]
    acc = (pred.values == actual.values).mean()
    return float(acc), int(valid.sum())

def magnitude_wr_split(feature_vals, win, q=0.5):
    """Bucket by median; WR_high vs WR_low; return (wr_high, wr_low, n_high, n_low)."""
    valid = ~feature_vals.isna()
    if valid.sum() < 10: return None
    fv = feature_vals[valid]; w = win[valid]
    thr = fv.quantile(q)
    hi = w[fv >= thr]; lo = w[fv < thr]
    return float(hi.mean()), float(lo.mean()), int(len(hi)), int(len(lo))

def max_v5_corr(feat, v5_cols, df_full):
    valid = ~df_full[feat].isna()
    if valid.sum() < 10: return np.nan
    cors = []
    for c in v5_cols:
        try:
            r = df_full[feat][valid].astype(float).corr(df_full[c][valid].astype(float))
            if not np.isnan(r): cors.append(abs(r))
        except Exception: pass
    return max(cors) if cors else np.nan

print("\n=== signed-direction accuracy + orthogonality ===")
signed_report = []
all_signed = SIGNED | set(SIGNED_CENTERED_50.keys())
for f in INDICATORS:
    if f not in all_signed: continue
    center = SIGNED_CENTERED_50.get(f, 0)
    acc, n = directional_accuracy(df_full[f], df_full["actual_price_dir"], center)
    if np.isnan(acc): continue
    corr = max_v5_corr(f, v5_cols, df_full)
    signed_report.append({"indicator": f, "type": "signed", "accuracy": acc, "n": n,
                          "max_v5_corr": corr,
                          "orthogonal_lift": (acc - 0.5) * 2 * (1 - (corr if not np.isnan(corr) else 0))})
signed_df = pd.DataFrame(signed_report).sort_values("orthogonal_lift", ascending=False)
print(signed_df.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

print("\n=== magnitude features: WR high-half vs low-half ===")
mag_report = []
for f in INDICATORS:
    if f not in MAGNITUDE: continue
    r = magnitude_wr_split(df_full[f], df_full["win"])
    if r is None: continue
    wr_hi, wr_lo, n_hi, n_lo = r
    corr = max_v5_corr(f, v5_cols, df_full)
    mag_report.append({"indicator": f, "type": "magnitude",
                       "wr_high": wr_hi, "wr_low": wr_lo, "n_high": n_hi, "n_low": n_lo,
                       "wr_delta": wr_hi - wr_lo,
                       "max_v5_corr": corr})
mag_df = pd.DataFrame(mag_report).sort_values("wr_delta", key=lambda x: x.abs(), ascending=False)
print(mag_df.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

# ── Save outputs ─────────────────────────────────────────────────────────────
out_csv = OUT_DIR / "discovery_features.csv"
df_full.to_csv(out_csv, index=False)
print(f"\n→ per-trade feature matrix: {out_csv}")

(out_dir := OUT_DIR / "discovery_signed_rank.csv").write_text(signed_df.to_csv(index=False))
print(f"→ signed-indicator rank: {out_dir}")

(out_dir := OUT_DIR / "discovery_magnitude_rank.csv").write_text(mag_df.to_csv(index=False))
print(f"→ magnitude-indicator rank: {out_dir}")
