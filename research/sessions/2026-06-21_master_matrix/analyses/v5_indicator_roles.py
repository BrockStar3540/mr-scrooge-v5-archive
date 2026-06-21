"""Indicator role categorization — what does each feature DO?

For each of ~56 features, classify by primary role using 2026 corpus correlations:
  - DIRECTION: sign of feature correlates with sign(fwd_ret) (directional predictor)
  - MOMENTUM: |feature| correlates with |fwd_ret| (move-size predictor)
  - DISTANCE: feature is a level-distance metric (PDH/PDL/DC/KC/VWAP)
  - VOLATILITY/REGIME: feature is vol/regime-classifier (atr_*, bbwp, hurst, entropy, vhf, chop)
  - VOLUME: feature uses volume input (obv, cmf, mfi, adl, adosc, efi, rvol*)
  - CYCLE: feature is cycle-phase (ht_dcperiod, ht_dcphase, ebsw)
  - DERIVED: feature is a combination/ratio

Use feature name heuristics + correlation analysis.
"""
import json, time, subprocess
from pathlib import Path
import numpy as np
import pandas as pd
from joblib import Parallel, delayed

def assert_on_mini():
    s = subprocess.run(["system_profiler","SPHardwareDataType"], capture_output=True, text=True).stdout
    if "CPYQTH294R" not in s: raise RuntimeError("NOT ON MINI")
    print("✓ device verified: Mini CPYQTH294R")
assert_on_mini()

ROOT     = Path.home() / "qtl-discovery-8yr"
FEATURES = ROOT / "features"
OUT      = ROOT / "master_matrix"

PAIRS = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]

# Hard-classified by name pattern + known function
ROLE_CLASSIFICATION = {
    # === DIRECTION (signed predictors of price direction) ===
    "h1_ret_1bar": "DIRECTION",  "h1_ret_4bar": "DIRECTION",
    "trend_4h": "DIRECTION",     "rsi_slope": "DIRECTION",
    "zscore_1h": "DIRECTION",    "zscore_5m": "DIRECTION",
    "d_ret": "DIRECTION",        "ret_5m": "DIRECTION",
    "ret_15m": "DIRECTION",      "ret_30m": "DIRECTION",
    "ret_1h": "DIRECTION",       "ema20_1h_dist": "DIRECTION",
    "ema20_dist_pct": "DIRECTION", "ema5_dist_pips": "DIRECTION",
    "ema50_dist_pct": "DIRECTION", "ema_cross_pips": "DIRECTION",
    "htf_pct_20": "DIRECTION",   "htf_pct_60": "DIRECTION",
    "q_macd_m5": "DIRECTION",    "q_tsi_m5": "DIRECTION",
    "q_fisher_m5": "DIRECTION",  "q_cci_m5": "DIRECTION",
    "q_willr_m5": "DIRECTION",   "q_aroonosc_h1": "DIRECTION",
    "q_super_dist_h1": "DIRECTION", "q_vortex_diff_h1": "DIRECTION",
    "q_stochrsi_m5": "DIRECTION", "q_ht_dcphase_m5": "DIRECTION",
    "q_ebsw_m5": "DIRECTION",
    # === OSCILLATOR (bounded; OB/OS — quasi-direction but range-bound) ===
    "rsi14": "OSCILLATOR",
    "bb_pos": "OSCILLATOR",
    "close_pos_daily": "OSCILLATOR",
    # === DISTANCE (level-based offsets in pips or normalized) ===
    "pdh_dist": "DISTANCE", "pdl_dist": "DISTANCE",
    "pdh_dist_atr_pct": "DISTANCE", "pdl_dist_atr_pct": "DISTANCE",
    "q_dc_up_dist_pips": "DISTANCE", "q_dc_lo_dist_pips": "DISTANCE",
    "q_kc_up_dist_pips": "DISTANCE",
    "q_vwap_dist_pips_m5": "DISTANCE",
    # === VOLATILITY / REGIME (magnitude/regime classifiers) ===
    "atr_5m": "VOLATILITY", "atr_1h": "VOLATILITY", "atr_d_pips": "VOLATILITY",
    "atr_conc": "REGIME", "atr_h1_relative": "REGIME",
    "adr_consumed": "REGIME", "bb_width": "VOLATILITY",
    "q_atrn_m5": "VOLATILITY", "q_bbwp_m5": "REGIME",
    "q_yzv_m5": "VOLATILITY",
    "q_hurst_m5": "REGIME", "q_entropy_m5": "REGIME",
    "q_vhf_h1": "REGIME", "q_chop_h1": "REGIME",
    "q_adx_h1": "REGIME",
    "q_kurtosis_m5": "REGIME", "q_skew_m5": "REGIME",
    # === RANGE ===
    "range_5bar": "VOLATILITY", "range_12bar": "VOLATILITY",
    "d_range_pips": "VOLATILITY", "wall_frac": "REGIME",
    # === VOLUME ===
    "rvol_5bar": "VOLUME", "rvol_12bar": "VOLUME",
    "q_obv": "VOLUME", "q_cmf": "VOLUME", "q_mfi": "VOLUME",
    "q_adl": "VOLUME", "q_adosc": "VOLUME", "q_efi": "VOLUME",
    # === CYCLE (other than dcphase which is directional) ===
    "q_ht_dcperiod_m5": "CYCLE",
}

def analyze_feature(fname, role, pair_dfs):
    """For each pair, measure feature's predictive correlations."""
    # Aggregate across all pairs × all 2026 data
    stats = {"feature": fname, "role": role}
    all_corrs_dir = []
    all_corrs_mag = []
    all_corrs_vol = []
    for pair, df in pair_dfs.items():
        if fname not in df.columns: continue
        df_2026 = df[df.index.year == 2026].copy()
        if len(df_2026) < 1000: continue
        f = df_2026[fname].astype(float)
        fwd = df_2026["fwd_ret_pips"].astype(float)
        # Direction correlation: feature vs fwd_ret signed
        c1 = f.corr(fwd)
        # Magnitude correlation: |feature| vs |fwd_ret|
        c2 = f.abs().corr(fwd.abs())
        # Vol correlation: feature vs atr_5m
        if "atr_5m" in df_2026.columns:
            c3 = f.corr(df_2026["atr_5m"])
        else:
            c3 = np.nan
        if not pd.isna(c1): all_corrs_dir.append(c1)
        if not pd.isna(c2): all_corrs_mag.append(c2)
        if not pd.isna(c3): all_corrs_vol.append(c3)
    if all_corrs_dir:
        stats["mean_dir_corr"] = round(float(np.mean(all_corrs_dir)), 4)
        stats["abs_mean_dir_corr"] = round(float(np.mean([abs(c) for c in all_corrs_dir])), 4)
    if all_corrs_mag:
        stats["mean_mag_corr"] = round(float(np.mean(all_corrs_mag)), 4)
    if all_corrs_vol:
        stats["mean_vol_corr"] = round(float(np.mean(all_corrs_vol)), 4)
    return stats

if __name__ == "__main__":
    print("Loading per-pair 2026 feature parquets...")
    pair_dfs = {p: pd.read_parquet(FEATURES / f"{p}_features.parquet") for p in PAIRS}
    print(f"  Loaded {len(pair_dfs)} pairs, ~{sum(len(d) for d in pair_dfs.values()):,} bars total")

    # Get list of all features (V5 + qtl)
    sample_df = pair_dfs[PAIRS[0]]
    all_cols = [c for c in sample_df.columns if c not in ("session","label","fwd_ret_pips")]
    print(f"  Analyzing {len(all_cols)} features")

    t0 = time.time()
    results = []
    for fname in all_cols:
        role = ROLE_CLASSIFICATION.get(fname, "UNCLASSIFIED")
        stats = analyze_feature(fname, role, pair_dfs)
        results.append(stats)
    print(f"\nTotal: {time.time() - t0:.1f}s")

    df = pd.DataFrame(results)
    df = df.sort_values(["role", "abs_mean_dir_corr"], ascending=[True, False])

    # Save CSV
    out_csv = OUT / "indicator_roles.csv"
    df.to_csv(out_csv, index=False)
    print(f"→ {out_csv}")

    # Print by role
    print(f"\n=== INDICATOR ROLE CATEGORIES (sorted by abs direction-correlation) ===")
    for role in df["role"].unique():
        sub = df[df["role"]==role]
        print(f"\n--- {role} ({len(sub)} features) ---")
        cols = ["feature","mean_dir_corr","abs_mean_dir_corr","mean_mag_corr","mean_vol_corr"]
        print(sub[cols].to_string(index=False, float_format=lambda x: f"{x:+.4f}" if x is not None and not pd.isna(x) else "-"))
