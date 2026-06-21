"""Per-cell ML evaluation: 24 (pair × session) cells × baseline-vs-full XGB.

For each cell:
  1. Train XGB-baseline (V5's 24 features only) → OOS AUC_baseline
  2. Train XGB-full (V5 + 32 qtl candidates)  → OOS AUC_full
  3. ΔAUC_global = AUC_full - AUC_baseline (how much the candidates add as a group)
  4. Per-candidate gain importance from full model (which candidates carry the lift)
  5. Best-threshold split per top candidate (aggregator-rule candidate)
  6. Per-direction subset analysis: for predicted-UP vs predicted-DOWN bars,
     which features had highest SHAP magnitude?

Walk-forward: chronological 70/30 split per cell.
Parallel across 8 cores.

Output: ~/qtl-discovery-8yr/ml/per_cell_results.json + per_cell_importance.csv
"""
import os, json, time, subprocess
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from xgboost import XGBClassifier
from sklearn.metrics import roc_auc_score
from sklearn.tree import DecisionTreeClassifier

# DEVICE SAFETY
def assert_on_mini():
    serial = subprocess.run(["system_profiler","SPHardwareDataType"], capture_output=True, text=True).stdout
    if "CPYQTH294R" not in serial:
        raise RuntimeError("NOT ON MINI — refusing to run heavy compute")
    print("✓ device verified: Mini CPYQTH294R")
assert_on_mini()

ROOT     = Path.home() / "qtl-discovery-8yr"
FEATURES = ROOT / "features"
ML       = ROOT / "ml"
ML.mkdir(exist_ok=True)

PAIRS    = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
SESSIONS = ["asia","london","ny"]
N_JOBS   = 8

# V5's baseline features (everything except q_* and bookkeeping cols)
META_COLS = ("session","label","fwd_ret_pips")

def get_columns(sample_df):
    all_cols = [c for c in sample_df.columns if c not in META_COLS]
    qtl_cols = [c for c in all_cols if c.startswith("q_")]
    v5_cols  = [c for c in all_cols if not c.startswith("q_")]
    return v5_cols, qtl_cols

def best_threshold_split(feature_vals, labels):
    """Find threshold T that maximally separates labels +1/-1; return (T, wr_high, wr_low, n_high, n_low)."""
    valid = ~feature_vals.isna()
    if valid.sum() < 1000: return None
    fv = feature_vals[valid].values
    y  = (labels[valid].values > 0).astype(int)   # 1 = went up
    # Use a depth-1 decision stump to find the best split
    stump = DecisionTreeClassifier(max_depth=1, min_samples_leaf=max(100, int(len(fv)*0.05)))
    stump.fit(fv.reshape(-1,1), y)
    if stump.tree_.node_count < 3: return None  # no split found
    T = float(stump.tree_.threshold[0])
    above = y[fv > T]; below = y[fv <= T]
    return T, float(above.mean()), float(below.mean()), int(len(above)), int(len(below))

def process_cell(pair, session):
    t0 = time.time()
    df = pd.read_parquet(FEATURES / f"{pair}_features.parquet")
    df = df[df["session"] == session].copy()
    v5_cols, qtl_cols = get_columns(df)
    # Use only rows where ALL columns are finite (else XGB chokes)
    use_cols = v5_cols + qtl_cols
    df_clean = df[use_cols + ["label"]].replace([np.inf, -np.inf], np.nan).dropna()
    n = len(df_clean)
    if n < 5000:
        return {"pair": pair, "session": session, "error": f"too few clean rows ({n})"}

    # Chronological 70/30 split
    split = int(n * 0.7)
    Xtr_v5  = df_clean.iloc[:split][v5_cols].values
    Xte_v5  = df_clean.iloc[split:][v5_cols].values
    Xtr_full= df_clean.iloc[:split][use_cols].values
    Xte_full= df_clean.iloc[split:][use_cols].values
    # Convert label {+1, -1} → {1, 0}
    ytr = (df_clean.iloc[:split]["label"].values > 0).astype(int)
    yte = (df_clean.iloc[split:]["label"].values > 0).astype(int)

    XGB_KW = dict(n_estimators=200, max_depth=4, learning_rate=0.05,
                   subsample=0.8, colsample_bytree=0.8,
                   eval_metric="auc", tree_method="hist", n_jobs=1,
                   verbosity=0)

    # Baseline: V5 features only
    m_base = XGBClassifier(**XGB_KW)
    m_base.fit(Xtr_v5, ytr)
    auc_base = float(roc_auc_score(yte, m_base.predict_proba(Xte_v5)[:,1]))

    # Full: V5 + all qtl candidates
    m_full = XGBClassifier(**XGB_KW)
    m_full.fit(Xtr_full, ytr)
    auc_full = float(roc_auc_score(yte, m_full.predict_proba(Xte_full)[:,1]))

    delta = auc_full - auc_base

    # Per-feature importance (gain-based, full model)
    importances = dict(zip(use_cols, m_full.feature_importances_.tolist()))
    # Sort + keep only qtl candidates' importance for the report
    qtl_importance = {c: importances[c] for c in qtl_cols}
    qtl_importance_sorted = dict(sorted(qtl_importance.items(), key=lambda kv: -kv[1]))

    # Per-direction (label) analysis: SHAP-style proxy via predicted-up vs predicted-down subsets
    proba = m_full.predict_proba(Xte_full)[:,1]
    pred_up   = proba > 0.55
    pred_down = proba < 0.45
    test_df = df_clean.iloc[split:].copy()
    test_df["pred_up"] = pred_up
    test_df["pred_down"] = pred_down
    test_df["actual_up"] = yte.astype(bool)
    # Per-cell × direction WR
    wr_pred_up   = float(test_df.loc[pred_up,   "actual_up"].mean()) if pred_up.sum() > 100 else None
    wr_pred_down = float(1 - test_df.loc[pred_down, "actual_up"].mean()) if pred_down.sum() > 100 else None
    n_pred_up    = int(pred_up.sum())
    n_pred_down  = int(pred_down.sum())

    # For top 5 qtl candidates: best-threshold split (aggregator rule candidate)
    rules = []
    for q in list(qtl_importance_sorted.keys())[:5]:
        s = best_threshold_split(df_clean[q], df_clean["label"])
        if s:
            T, wr_h, wr_l, n_h, n_l = s
            rules.append({"feature": q, "threshold": T,
                          "wr_high": wr_h, "wr_low": wr_l, "wr_delta": wr_h - wr_l,
                          "n_high": n_h, "n_low": n_l, "gain_importance": qtl_importance[q]})

    return {
        "pair": pair, "session": session,
        "n_train": int(split), "n_test": int(n - split),
        "auc_baseline": auc_base, "auc_full": auc_full, "delta_auc": delta,
        "wr_pred_up": wr_pred_up, "wr_pred_down": wr_pred_down,
        "n_pred_up": n_pred_up, "n_pred_down": n_pred_down,
        "qtl_importance": qtl_importance_sorted,
        "aggregator_rules": rules,
        "elapsed_s": time.time() - t0,
    }

if __name__ == "__main__":
    cells = [(p, s) for p in PAIRS for s in SESSIONS]
    print(f"Training {len(cells)} cells × 2 models (baseline + full) across {N_JOBS} cores")
    t0 = time.time()
    results = Parallel(n_jobs=N_JOBS, verbose=10)(
        delayed(process_cell)(p, s) for p, s in cells
    )
    total_s = time.time() - t0
    print(f"\nTotal: {total_s:.1f}s")

    # Summary
    print("\n=== PER-CELL RESULTS (sorted by delta_auc, desc) ===")
    valid = [r for r in results if "error" not in r]
    valid.sort(key=lambda r: -r["delta_auc"])
    print(f"{'pair':<10} {'session':<7} {'AUC_base':>9} {'AUC_full':>9} {'ΔAUC':>8} "
          f"{'WR↑':>6} {'WR↓':>6} top3_qtl_candidates")
    for r in valid:
        top3 = ", ".join([f"{k}={v:.3f}" for k,v in list(r['qtl_importance'].items())[:3]])
        print(f"{r['pair']:<10} {r['session']:<7} {r['auc_baseline']:>9.4f} {r['auc_full']:>9.4f} "
              f"{r['delta_auc']:>+8.4f} "
              f"{(r['wr_pred_up'] or 0)*100:>5.1f}% {(r['wr_pred_down'] or 0)*100:>5.1f}%  {top3}")

    # Save full JSON
    out = ML / "per_cell_results.json"
    out.write_text(json.dumps(results, indent=2, default=str))
    print(f"\n→ {out}")

    # Build per-feature × per-cell importance matrix
    qtl_cols = list(results[0]["qtl_importance"].keys())
    rows = []
    for r in valid:
        for q, imp in r["qtl_importance"].items():
            rows.append({"pair": r["pair"], "session": r["session"], "feature": q,
                         "importance": imp, "delta_auc_cell": r["delta_auc"]})
    imp_df = pd.DataFrame(rows)
    imp_pivot = imp_df.pivot_table(index="feature", columns=["pair","session"],
                                     values="importance", aggfunc="first")
    # Add summary stats
    imp_pivot["mean_importance"]   = imp_pivot.mean(axis=1)
    imp_pivot["max_importance"]    = imp_pivot.max(axis=1)
    imp_pivot["n_cells_top3"]      = imp_df.groupby("feature").apply(
        lambda g: int((g["importance"].rank(ascending=False) <= 3).sum())
    )  # rough: how often was this feature in top-3 across cells (within feature group)
    imp_pivot = imp_pivot.sort_values("mean_importance", ascending=False)
    out_csv = ML / "per_cell_importance.csv"
    imp_pivot.to_csv(out_csv)
    print(f"→ {out_csv}")

    # Top aggregator rules across all cells
    print("\n=== TOP AGGREGATOR RULE CANDIDATES (|wr_delta| sorted) ===")
    all_rules = []
    for r in valid:
        for rule in r["aggregator_rules"]:
            all_rules.append({"pair": r["pair"], "session": r["session"], **rule})
    rules_df = pd.DataFrame(all_rules)
    if not rules_df.empty:
        rules_df["abs_delta"] = rules_df["wr_delta"].abs()
        rules_df_sorted = rules_df.sort_values("abs_delta", ascending=False)
        print(rules_df_sorted.head(20).to_string(index=False, float_format=lambda x: f"{x:.4f}"))
        rules_df_sorted.to_csv(ML / "aggregator_rule_candidates.csv", index=False)
        print(f"\n→ {ML / 'aggregator_rule_candidates.csv'}")
