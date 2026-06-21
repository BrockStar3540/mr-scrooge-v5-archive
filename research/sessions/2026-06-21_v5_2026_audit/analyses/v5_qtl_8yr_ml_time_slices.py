"""Time-sliced per-(cell × direction) ML — addresses the drift concern.

Two passes:
  A) Per YEAR: 2019..2026 × 48 cell-directions × baseline-vs-full XGB.
     Shows how feature importance shifts across years (avoids averaging away regime change).
  B) Per MONTH of 2026: 01..06 × 48 cell-directions × same.
     Shows recent-month dynamics (what's been working LATELY).

Same methodology as the all-time 48-cell sweep so deltas are directly comparable.
"""
import os, json, time, subprocess
from pathlib import Path
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from xgboost import XGBClassifier
from sklearn.metrics import roc_auc_score

def assert_on_mini():
    s = subprocess.run(["system_profiler","SPHardwareDataType"], capture_output=True, text=True).stdout
    if "CPYQTH294R" not in s: raise RuntimeError("NOT ON MINI")
    print("✓ device verified: Mini CPYQTH294R")
assert_on_mini()

ROOT     = Path.home() / "qtl-discovery-8yr"
FEATURES = ROOT / "features"
ML       = ROOT / "ml_v3_time_slices"
ML.mkdir(exist_ok=True)

PAIRS    = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
SESSIONS = ["asia","london","ny"]
DIRECTIONS = ["long","short"]
N_JOBS   = 8
META_COLS = ("session","label","fwd_ret_pips")

def process_slice(pair, session, direction, time_filter, slice_label):
    """time_filter(df) → boolean Series selecting rows for this slice."""
    df = pd.read_parquet(FEATURES / f"{pair}_features.parquet")
    df = df[df["session"] == session]
    df = df[time_filter(df)].copy()
    if direction == "long":
        df["dir_y"] = (df["fwd_ret_pips"] > 0).astype(int)
    else:
        df["dir_y"] = (df["fwd_ret_pips"] < 0).astype(int)

    all_cols = [c for c in df.columns if c not in META_COLS + ("dir_y",)]
    qtl_cols = [c for c in all_cols if c.startswith("q_")]
    v5_cols  = [c for c in all_cols if not c.startswith("q_")]
    use_cols = v5_cols + qtl_cols
    df_clean = df[use_cols + ["dir_y"]].replace([np.inf,-np.inf], np.nan).dropna()
    n = len(df_clean)
    if n < 2000:
        return {"slice": slice_label, "pair": pair, "session": session, "direction": direction,
                "error": f"too few rows: {n}", "n": n}
    split = int(n * 0.7)
    ytr = df_clean.iloc[:split]["dir_y"].values
    yte = df_clean.iloc[split:]["dir_y"].values
    Xtr_v5   = df_clean.iloc[:split][v5_cols].values
    Xte_v5   = df_clean.iloc[split:][v5_cols].values
    Xtr_full = df_clean.iloc[:split][use_cols].values
    Xte_full = df_clean.iloc[split:][use_cols].values

    # Need at least one positive + one negative in test set
    if len(set(yte)) < 2:
        return {"slice": slice_label, "pair": pair, "session": session, "direction": direction,
                "error": "single-class test set", "n": n}

    KW = dict(n_estimators=150, max_depth=4, learning_rate=0.05, subsample=0.8,
              colsample_bytree=0.8, eval_metric="auc", tree_method="hist", n_jobs=1, verbosity=0)
    m_base = XGBClassifier(**KW); m_base.fit(Xtr_v5, ytr)
    m_full = XGBClassifier(**KW); m_full.fit(Xtr_full, ytr)
    auc_base = float(roc_auc_score(yte, m_base.predict_proba(Xte_v5)[:,1]))
    auc_full = float(roc_auc_score(yte, m_full.predict_proba(Xte_full)[:,1]))
    qtl_imp = dict(zip(use_cols, m_full.feature_importances_.tolist()))
    qtl_imp = {c: qtl_imp[c] for c in qtl_cols}
    qtl_imp_sorted = dict(sorted(qtl_imp.items(), key=lambda kv: -kv[1]))
    top3 = list(qtl_imp_sorted.items())[:3]

    return {
        "slice": slice_label,
        "pair": pair, "session": session, "direction": direction,
        "n_train": int(split), "n_test": int(n - split),
        "base_rate": float(ytr.mean()),
        "auc_baseline": auc_base, "auc_full": auc_full,
        "delta_auc": auc_full - auc_base,
        "top3_qtl": [(f, round(v, 4)) for f, v in top3],
        "all_qtl_importance": {k: round(v, 4) for k, v in qtl_imp_sorted.items()},
    }

# ── BUILD JOB LIST: years + 2026 months ──────────────────────────────────────
YEARS  = list(range(2019, 2027))     # 2019..2026
MONTHS_2026 = list(range(1, 7))      # Jan..Jun 2026
def year_filter(yr):
    return lambda df: df.index.year == yr
def month_filter(yr, mo):
    return lambda df: (df.index.year == yr) & (df.index.month == mo)

jobs = []
# Per-year
for yr in YEARS:
    for p in PAIRS:
        for s in SESSIONS:
            for d in DIRECTIONS:
                jobs.append((p, s, d, year_filter(yr), f"year_{yr}"))
# Per-month 2026
for mo in MONTHS_2026:
    for p in PAIRS:
        for s in SESSIONS:
            for d in DIRECTIONS:
                jobs.append((p, s, d, month_filter(2026, mo), f"2026-{mo:02d}"))

print(f"Total jobs: {len(jobs)}  (8 years × 48 cells + 6 months × 48 cells = {8*48 + 6*48})")
print(f"Running across {N_JOBS} cores...")
t0 = time.time()
results = Parallel(n_jobs=N_JOBS, verbose=10)(
    delayed(process_slice)(*j) for j in jobs
)
print(f"\nTotal: {time.time() - t0:.1f}s")

# Save
out_json = ML / "time_slice_results.json"
out_json.write_text(json.dumps(results, indent=2, default=str))
print(f"→ {out_json}")

# Build matrices for easier digestion
df = pd.DataFrame([r for r in results if "error" not in r])
df["slice_type"] = df["slice"].apply(lambda s: "year" if s.startswith("year") else "month")

# Year × cell-direction × delta_auc table
year_pivot = df[df["slice_type"] == "year"].pivot_table(
    index=["pair","session","direction"], columns="slice", values="delta_auc")
year_pivot.to_csv(ML / "year_x_cell_delta_auc.csv")

# 2026 month × cell-direction × delta_auc
month_pivot = df[df["slice_type"] == "month"].pivot_table(
    index=["pair","session","direction"], columns="slice", values="delta_auc")
month_pivot.to_csv(ML / "month2026_x_cell_delta_auc.csv")

# Aggregate per-feature importance per year (top-3 occurrences)
rows = []
for r in results:
    if "error" in r: continue
    for f, imp in r["all_qtl_importance"].items():
        rows.append({"slice": r["slice"], "pair": r["pair"], "session": r["session"],
                      "direction": r["direction"], "feature": f, "importance": imp})
imp_df = pd.DataFrame(rows)
# Mean importance per (slice, feature)
mean_imp = imp_df.groupby(["slice","feature"])["importance"].mean().unstack(level=0)
mean_imp.to_csv(ML / "feature_importance_by_slice.csv")
print(f"→ {ML / 'year_x_cell_delta_auc.csv'}")
print(f"→ {ML / 'month2026_x_cell_delta_auc.csv'}")
print(f"→ {ML / 'feature_importance_by_slice.csv'}")

# Quick summary
print(f"\n=== ΔAUC SUMMARY BY YEAR (averaged across 48 cells) ===")
year_summary = df[df["slice_type"]=="year"].groupby("slice").agg(
    mean_delta_auc=("delta_auc","mean"),
    median_delta_auc=("delta_auc","median"),
    n_cells_positive=("delta_auc", lambda x: (x>0).sum()),
    n_cells_total=("delta_auc","count"),
).round(4)
print(year_summary.to_string())

print(f"\n=== ΔAUC SUMMARY BY 2026 MONTH (averaged across 48 cells) ===")
month_summary = df[df["slice_type"]=="month"].groupby("slice").agg(
    mean_delta_auc=("delta_auc","mean"),
    median_delta_auc=("delta_auc","median"),
    n_cells_positive=("delta_auc", lambda x: (x>0).sum()),
    n_cells_total=("delta_auc","count"),
).round(4)
print(month_summary.to_string())

# Top feature drift — which features are gaining/losing importance over time
print(f"\n=== TOP-3 FEATURE COUNT PER SLICE (top-3 of qtl candidates in each cell-direction) ===")
top3_rows = []
for r in results:
    if "error" in r: continue
    for f, _ in r["top3_qtl"]:
        top3_rows.append({"slice": r["slice"], "feature": f})
top3_df = pd.DataFrame(top3_rows)
slice_x_feat = top3_df.groupby(["slice","feature"]).size().unstack(fill_value=0)
# Sort cols by total across slices
col_totals = slice_x_feat.sum(axis=0).sort_values(ascending=False)
print(slice_x_feat[col_totals.head(10).index].to_string())
slice_x_feat.to_csv(ML / "top3_features_by_slice.csv")
print(f"→ {ML / 'top3_features_by_slice.csv'}")
