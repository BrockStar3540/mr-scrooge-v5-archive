#!/usr/bin/env python3
"""Re-examine the 'redundant' V3 candidates per-cell + year-over-year.

For trend_1h, trend_4h, htf_bias_20, htf_bias_60:

  A. PER-CELL on full corpus (from existing JSONs):
     - baseline OOS corr   vs.   ablation OOS corr when this candidate removed
     - delta_OOS — if ~0, the candidate added no information (truly redundant)
     - importance of the candidate itself per cell

  B. YEAR-OVER-YEAR (re-train on 2024 window vs 2026 window):
     - importance shift per cell
     - OOS shift per cell
     - the V5 features that LOST importance when this candidate was present
       (so we can see which V5 it's actually summarizing — and if that
       summarization is stable across years)

Outputs `redundant_recheck.txt` to the test dir.
"""
from __future__ import annotations
import json, time
from pathlib import Path
import numpy as np
import pandas as pd
import xgboost as xgb

CORPUS_DIR = Path("/Volumes/Alien Device/direction_ml/corpus")
OUT = Path("/Volumes/Alien Device/scrooge-research/v5_aggregator_test_2026-06-18")
PAIRS = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
SESSIONS = ["asia","london","ny"]

# the V3 candidates I previously KEPT — apples-to-apples to the redundant ones
SUSPECTS = ["wall_frac","ema50_atr_frac","atr_conc"]

V5_DIR = [
    "h1_ret_1bar","rsi_slope","zscore_1h","h1_ret_4bar","d_ret",
    "ema20_1h_dist_pct","pdh_dist_pips","pdl_dist_pips",
    "pdl_dist_atr_pct","pdh_dist_atr_pct","rsi14","htf_pct_20","htf_pct_60",
    "ema20_dist_pct","bb_pos","zscore_5m","ema5_dist_pips",
    "ret_5m","ret_15m","ret_30m","ret_1h",
    "ema50_dist_pct","close_pos_daily","ema_cross_pips",
]
V5_MOM = [
    "atr_5m","rvol_5bar","atr_1h","rvol_12bar","bb_width",
    "range_5bar","range_12bar","atr_d_pips","d_range_pips","adr_consumed",
]
V5_ALL = V5_DIR + V5_MOM
V3_IN_CORPUS = ["trend_1h","trend_4h","atr_conc","htf_bias_20","htf_bias_60"]
V3_DERIVED = ["wall_frac","ema50_atr_frac"]
V3_CANDIDATES = V3_IN_CORPUS + V3_DERIVED


def derive_v3(df):
    atr = df["atr_5m"].replace(0, np.nan)
    df["wall_frac"]      = np.minimum(df["pdh_dist_pips"].abs(), df["pdl_dist_pips"].abs()) / atr
    df["ema50_atr_frac"] = df["ema50_dist_pct"] * 10000.0 / atr
    return df


# ── PART A: per-cell ΔOOS from existing JSONs ────────────────────────────
def part_a():
    rows = []
    for pair in PAIRS:
        for sess in SESSIONS:
            fp = OUT / f"{pair}_{sess}.json"
            if not fp.exists(): continue
            d = json.loads(fp.read_text())
            base_oos = d.get("baselines", {}).get("direction", {}).get("oos_corr")
            for v3 in SUSPECTS:
                ab = d.get("ablations", {}).get(v3, {})
                ab_oos = ab.get("oos_corr", {}).get("direction")
                imp = d.get("baselines", {}).get("direction", {}).get("importance", {}).get(v3)
                if base_oos is None or ab_oos is None: continue
                rows.append({
                    "pair": pair, "session": sess, "v3": v3,
                    "imp": imp,
                    "base_oos": base_oos,
                    "ab_oos": ab_oos,
                    "delta_oos": ab_oos - base_oos,  # positive = removing it HELPED
                })
    return rows


# ── PART B: per-cell year-over-year ──────────────────────────────────────
def train_one(df_window):
    df = df_window.replace([np.inf, -np.inf], np.nan).dropna(
        subset=V5_ALL + V3_CANDIDATES + ["net_60m"])
    if len(df) < 2000: return None
    n = len(df)
    split = int(n * 0.7)
    train, test = df.iloc[:split], df.iloc[split:]
    feats = V5_ALL + V3_CANDIDATES
    m = xgb.XGBRegressor(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0,
        tree_method="hist", n_jobs=8, random_state=42,
    )
    m.fit(train[feats].values, train["net_60m"].values, verbose=False)
    imp = {f: float(v) for f, v in zip(feats, m.feature_importances_)}
    pred = m.predict(test[feats].values)
    oos = float(np.corrcoef(pred, test["net_60m"].values)[0,1]) if test["net_60m"].std() > 0 else None
    return {"n": n, "oos": oos, "imp": imp}


def train_dropped(df_window, dropped):
    df = df_window.replace([np.inf, -np.inf], np.nan).dropna(
        subset=V5_ALL + V3_CANDIDATES + ["net_60m"])
    if len(df) < 2000: return None
    n = len(df)
    split = int(n * 0.7)
    train, test = df.iloc[:split], df.iloc[split:]
    feats = [f for f in V5_ALL + V3_CANDIDATES if f != dropped]
    m = xgb.XGBRegressor(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0,
        tree_method="hist", n_jobs=8, random_state=42,
    )
    m.fit(train[feats].values, train["net_60m"].values, verbose=False)
    pred = m.predict(test[feats].values)
    oos = float(np.corrcoef(pred, test["net_60m"].values)[0,1]) if test["net_60m"].std() > 0 else None
    return {"oos": oos}


def part_b():
    WINDOWS = {"2024": ("2024-01-01","2024-06-18"), "2026": ("2026-01-01","2026-06-18")}
    rows = []
    for pair in PAIRS:
        df_pair = pd.read_parquet(CORPUS_DIR / f"{pair}_corpus.parquet")
        df_pair = derive_v3(df_pair)
        for sess in SESSIONS:
            df_sess = df_pair[df_pair["session"] == sess]
            per_yr = {}
            for yr, (s_, e_) in WINDOWS.items():
                df_w = df_sess.loc[s_:e_].copy()
                base = train_one(df_w)
                if base is None: continue
                yr_data = {"base": base, "ablations": {}}
                for v3 in SUSPECTS:
                    ab = train_dropped(df_w, v3)
                    if ab is None: continue
                    yr_data["ablations"][v3] = ab
                per_yr[yr] = yr_data
            for v3 in SUSPECTS:
                r = {"pair": pair, "session": sess, "v3": v3}
                for yr in WINDOWS:
                    pd_yr = per_yr.get(yr, {})
                    base = pd_yr.get("base", {})
                    ab   = pd_yr.get("ablations", {}).get(v3, {})
                    r[f"{yr}_imp"]       = base.get("imp", {}).get(v3)
                    r[f"{yr}_base_oos"]  = base.get("oos")
                    r[f"{yr}_ab_oos"]    = ab.get("oos")
                    r[f"{yr}_delta_oos"] = (ab.get("oos") - base.get("oos")) if (
                        ab.get("oos") is not None and base.get("oos") is not None) else None
                rows.append(r)
            print(f"  done {pair}/{sess}", flush=True)
    return rows


def fmt(x, w=8, p=4):
    if x is None: return f"{'—':>{w}}"
    return f"{x:>{w}.{p}f}"


def main():
    print("PART A: ΔOOS when each suspect is removed (full-corpus from existing JSONs)", flush=True)
    a_rows = part_a()
    print("PART B: year-over-year per-cell retrain", flush=True)
    t0 = time.time()
    b_rows = part_b()
    print(f"part B done in {(time.time()-t0)/60:.1f}min", flush=True)

    L = []
    L.append("="*94)
    L.append("REDUNDANCY RE-CHECK — per-cell ΔOOS + year-over-year for the 4 'redundant' candidates")
    L.append("="*94)
    L.append("")
    L.append("ΔOOS = OOS_corr(model WITHOUT feature) - OOS_corr(model WITH feature).")
    L.append("  positive  -> removing the feature IMPROVED OOS  -> truly redundant or noise")
    L.append("  ~ 0       -> removing the feature was neutral   -> redundant")
    L.append("  negative  -> removing the feature HURT OOS      -> the feature carries unique info")
    L.append("")

    for v3 in SUSPECTS:
        L.append("="*94)
        L.append(f"SUSPECT  :  {v3}")
        L.append("="*94)
        L.append("")
        L.append("PART A — Full-corpus (7.5yr, 70/30 chrono split per cell)")
        L.append(f"  {'cell':<20}  {'imp':>8}  {'base_oos':>9}  {'ab_oos':>9}  {'ΔOOS':>9}")
        sub = [r for r in a_rows if r["v3"] == v3]
        # sort: most negative delta_oos (= most needed) first
        sub.sort(key=lambda r: r["delta_oos"])
        for r in sub:
            L.append(f"  {r['pair']+'/'+r['session']:<20}  "
                     f"{fmt(r['imp'],8,4)}  "
                     f"{fmt(r['base_oos'],9,3)}  "
                     f"{fmt(r['ab_oos'],9,3)}  "
                     f"{fmt(r['delta_oos'],9,4)}")
        # quick stats
        deltas = [r["delta_oos"] for r in sub if r["delta_oos"] is not None]
        L.append(f"  --- mean ΔOOS = {np.mean(deltas):+.5f}   "
                 f"min = {min(deltas):+.5f}   max = {max(deltas):+.5f}   "
                 f"cells_where_removing_hurts = {sum(1 for d in deltas if d < -0.005)}/{len(deltas)}")
        L.append("")
        L.append("PART B — Year-over-year (2024 vs 2026, same 5.5-mo window)")
        L.append(f"  {'cell':<20}  "
                 f"{'2024_imp':>9}  {'2026_imp':>9}  "
                 f"{'2024_ΔOOS':>10}  {'2026_ΔOOS':>10}  {'verdict':>10}")
        sub_b = [r for r in b_rows if r["v3"] == v3]
        for r in sub_b:
            d24 = r.get("2024_delta_oos"); d26 = r.get("2026_delta_oos")
            verdict = ""
            if d24 is not None and d26 is not None:
                if d24 < -0.01 and d26 < -0.01:  verdict = "NEEDED"
                elif d24 > 0.01 and d26 > 0.01:  verdict = "redundant"
                elif (d24 < -0.01) != (d26 < -0.01):  verdict = "REGIME"
            L.append(f"  {r['pair']+'/'+r['session']:<20}  "
                     f"{fmt(r.get('2024_imp'),9,4)}  "
                     f"{fmt(r.get('2026_imp'),9,4)}  "
                     f"{fmt(d24,10,4)}  "
                     f"{fmt(d26,10,4)}  "
                     f"{verdict:>10}")
        L.append("")

    (OUT / "kept_recheck.txt").write_text("\n".join(L))
    print(f"wrote {OUT/'kept_recheck.txt'}")


if __name__ == "__main__":
    main()
