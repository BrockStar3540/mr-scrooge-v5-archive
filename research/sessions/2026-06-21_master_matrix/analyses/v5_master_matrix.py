"""V5 MASTER MATRIX builder — per (pair × session × direction) × all evidence.

For each of 48 cell-directions, accumulate:
  - V5 current state: profile, evidence tag, live N
  - 2026 monthly ΔAUC stability (Jan/Feb/Mar/Apr/May/Jun) → consistency score
  - 2024+2025+2026 yearly ΔAUC stability (recent-3-year consistency)
  - Best aggregator rule per feature (top-5 by importance): threshold + side + WR delta
  - Feature role categorization (direction / momentum / distance / regime / volume)
  - Live trade replay: would each rule have changed trade outcome?
  - Final recommendation: profile + features + rules + enable/disable

Output ONE master CSV + per-cell JSON config + readable markdown.

ALL per-cell. NO global rules.
"""
import os, json, time, subprocess
from pathlib import Path
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from xgboost import XGBClassifier
from sklearn.metrics import roc_auc_score
from sklearn.tree import DecisionTreeClassifier

def assert_on_mini():
    s = subprocess.run(["system_profiler","SPHardwareDataType"], capture_output=True, text=True).stdout
    if "CPYQTH294R" not in s: raise RuntimeError("NOT ON MINI")
    print("✓ device verified: Mini CPYQTH294R")
assert_on_mini()

ROOT     = Path.home() / "qtl-discovery-8yr"
FEATURES = ROOT / "features"
OUT      = ROOT / "master_matrix"
OUT.mkdir(exist_ok=True)

PAIRS    = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
SESSIONS = ["asia","london","ny"]
DIRECTIONS = ["long","short"]
MONTHS_2026 = list(range(1, 7))   # Jan..Jun
RECENT_YEARS = [2024, 2025, 2026]
N_JOBS   = 8
META_COLS = ("session","label","fwd_ret_pips")

CURRENT_ASSIGNMENTS = {
    ("AUD_JPY","asia","long"):    ("default","NO_DATA"),
    ("AUD_JPY","asia","short"):   ("continuation_strong","STRONG"),
    ("AUD_JPY","london","long"):  ("reversion","BAD"),
    ("AUD_JPY","london","short"): ("default","WEAK"),
    ("AUD_JPY","ny","long"):      ("continuation_strong","MODERATE"),
    ("AUD_JPY","ny","short"):     ("continuation_strong","MODERATE"),
    ("AUD_USD","asia","long"):    ("default","NO_DATA"),
    ("AUD_USD","asia","short"):   ("continuation_strong","MEDIUM"),
    ("AUD_USD","london","long"):  ("default","NO_DATA"),
    ("AUD_USD","london","short"): ("default","NO_DATA"),
    ("AUD_USD","ny","long"):      ("reversion","WEAK"),
    ("AUD_USD","ny","short"):     ("reversion","WEAK"),
    ("EUR_JPY","asia","long"):    ("continuation_strong","MODERATE"),
    ("EUR_JPY","asia","short"):   ("continuation_strong","MODERATE"),
    ("EUR_JPY","london","long"):  ("reversion","WEAK"),
    ("EUR_JPY","london","short"): ("reversion","BAD"),
    ("EUR_JPY","ny","long"):      ("continuation_strong","WEAK"),
    ("EUR_JPY","ny","short"):     ("default","NO_DATA"),
    ("EUR_USD","asia","long"):    ("default","NO_DATA"),
    ("EUR_USD","asia","short"):   ("default","NO_DATA"),
    ("EUR_USD","london","long"):  ("default","NO_DATA"),
    ("EUR_USD","london","short"): ("reversion","MEDIUM"),
    ("EUR_USD","ny","long"):      ("default","NO_DATA"),
    ("EUR_USD","ny","short"):     ("reversion","STRONG"),
    ("GBP_USD","asia","long"):    ("default","NO_DATA"),
    ("GBP_USD","asia","short"):   ("default","NO_DATA"),
    ("GBP_USD","london","long"):  ("continuation_strong","MEDIUM"),
    ("GBP_USD","london","short"): ("continuation_strong","STRONG"),
    ("GBP_USD","ny","long"):      ("default","NO_DATA"),
    ("GBP_USD","ny","short"):     ("reversion","STRONG"),
    ("USD_CAD","asia","long"):    ("default","NO_DATA"),
    ("USD_CAD","asia","short"):   ("default","NO_DATA"),
    ("USD_CAD","london","long"):  ("default","NO_DATA"),
    ("USD_CAD","london","short"): ("default","NO_DATA"),
    ("USD_CAD","ny","long"):      ("reversion","MODERATE"),
    ("USD_CAD","ny","short"):     ("default","NO_DATA"),
    ("USD_CHF","asia","long"):    ("default","NO_DATA"),
    ("USD_CHF","asia","short"):   ("default","NO_DATA"),
    ("USD_CHF","london","long"):  ("continuation_strong","MODERATE"),
    ("USD_CHF","london","short"): ("default","NO_DATA"),
    ("USD_CHF","ny","long"):      ("reversion","MODERATE"),
    ("USD_CHF","ny","short"):     ("default","NO_DATA"),
    ("USD_JPY","asia","long"):    ("continuation_strong","WEAK"),
    ("USD_JPY","asia","short"):   ("continuation_strong","MEDIUM_STRICT"),
    ("USD_JPY","london","long"):  ("default","NO_DATA"),
    ("USD_JPY","london","short"): ("default","NO_DATA"),
    ("USD_JPY","ny","long"):      ("continuation_strong","WEAK"),
    ("USD_JPY","ny","short"):     ("continuation_strong","WEAK"),
}

# Load V5 live trade matrix for replay (44 trades)
LIVE_MATRIX_PATH = "/home/ubuntu/mr-scrooge-v5/research/matrices/v5_full_matrix_v2_36cols.csv"
try:
    LIVE_TRADES = pd.read_csv(LIVE_MATRIX_PATH)
    LIVE_TRADES["dir"] = LIVE_TRADES["dir"].str.lower()
except Exception:
    LIVE_TRADES = pd.DataFrame()

XGB_KW = dict(n_estimators=120, max_depth=4, learning_rate=0.05, subsample=0.8,
               colsample_bytree=0.8, eval_metric="auc", tree_method="hist", n_jobs=1, verbosity=0)

def best_threshold_two_sided(feature_vals, y, min_n=200):
    valid = ~feature_vals.isna() & ~pd.isna(y)
    if valid.sum() < min_n * 2: return None
    fv = feature_vals[valid].values
    yv = (y[valid] if isinstance(y, np.ndarray) else y[valid].values)
    stump = DecisionTreeClassifier(max_depth=1, min_samples_leaf=max(min_n, int(len(fv)*0.05)))
    try:
        stump.fit(fv.reshape(-1,1), yv)
    except Exception:
        return None
    if stump.tree_.node_count < 3: return None
    T = float(stump.tree_.threshold[0])
    above = yv[fv > T]; below = yv[fv <= T]
    if len(above) < min_n or len(below) < min_n: return None
    wr_above = float(above.mean()); wr_below = float(below.mean())
    if wr_above >= wr_below:
        return {"threshold": round(T, 4), "side": "gt",
                "wr_when_fires": round(wr_above, 4), "wr_when_not": round(wr_below, 4),
                "wr_delta": round(wr_above - wr_below, 4),
                "n_fires": int(len(above)), "n_not": int(len(below))}
    else:
        return {"threshold": round(T, 4), "side": "lt",
                "wr_when_fires": round(wr_below, 4), "wr_when_not": round(wr_above, 4),
                "wr_delta": round(wr_below - wr_above, 4),
                "n_fires": int(len(below)), "n_not": int(len(above))}

def train_xgb_get_metrics(df_clean, v5_cols, use_cols):
    n = len(df_clean)
    if n < 1500: return None
    split = int(n * 0.7)
    ytr = df_clean.iloc[:split]["dir_y"].values
    yte = df_clean.iloc[split:]["dir_y"].values
    if len(set(yte)) < 2: return None
    try:
        m_base = XGBClassifier(**XGB_KW)
        m_base.fit(df_clean.iloc[:split][v5_cols].values, ytr)
        m_full = XGBClassifier(**XGB_KW)
        m_full.fit(df_clean.iloc[:split][use_cols].values, ytr)
        auc_base = float(roc_auc_score(yte, m_base.predict_proba(df_clean.iloc[split:][v5_cols].values)[:,1]))
        auc_full = float(roc_auc_score(yte, m_full.predict_proba(df_clean.iloc[split:][use_cols].values)[:,1]))
        imp = dict(zip(use_cols, m_full.feature_importances_.tolist()))
        return {
            "n_train": int(split), "n_test": int(n - split),
            "base_rate": round(float(ytr.mean()), 4),
            "auc_baseline": round(auc_base, 4),
            "auc_full": round(auc_full, 4),
            "delta_auc": round(auc_full - auc_base, 4),
            "feature_importance": {k: round(v, 4) for k, v in imp.items()},
        }
    except Exception:
        return None

def process_cell(pair, session, direction):
    """Returns one row of the Master Matrix."""
    fp = FEATURES / f"{pair}_features.parquet"
    df = pd.read_parquet(fp)
    df = df[df["session"] == session].copy()
    if direction == "long":
        df["dir_y"] = (df["fwd_ret_pips"] > 0).astype(int)
    else:
        df["dir_y"] = (df["fwd_ret_pips"] < 0).astype(int)

    all_cols = [c for c in df.columns if c not in META_COLS + ("dir_y",)]
    qtl_cols = [c for c in all_cols if c.startswith("q_")]
    v5_cols  = [c for c in all_cols if not c.startswith("q_")]
    use_cols = v5_cols + qtl_cols

    row = {"pair": pair, "session": session, "direction": direction}
    cur_prof, cur_evid = CURRENT_ASSIGNMENTS.get((pair, session, direction), ("default", "NO_DATA"))
    row["current_profile"] = cur_prof
    row["current_evidence"] = cur_evid

    # ── 1) 2026 ALL ──
    df_2026 = df[df.index.year == 2026].copy()
    df_2026_clean = df_2026[use_cols + ["dir_y"]].replace([np.inf,-np.inf], np.nan).dropna()
    m_2026 = train_xgb_get_metrics(df_2026_clean, v5_cols, use_cols)
    if m_2026:
        row["n_2026"] = len(df_2026_clean)
        row["delta_auc_2026"] = m_2026["delta_auc"]
        row["auc_baseline_2026"] = m_2026["auc_baseline"]
        row["auc_full_2026"] = m_2026["auc_full"]
        # Top-3 qtl features by importance
        qtl_imp = {k: v for k, v in m_2026["feature_importance"].items() if k in qtl_cols}
        qtl_imp_sorted = sorted(qtl_imp.items(), key=lambda kv: -kv[1])
        top3_2026 = qtl_imp_sorted[:3]
        row["top1_2026_feat"]   = top3_2026[0][0] if len(top3_2026) > 0 else None
        row["top1_2026_imp"]    = top3_2026[0][1] if len(top3_2026) > 0 else None
        row["top2_2026_feat"]   = top3_2026[1][0] if len(top3_2026) > 1 else None
        row["top2_2026_imp"]    = top3_2026[1][1] if len(top3_2026) > 1 else None
        row["top3_2026_feat"]   = top3_2026[2][0] if len(top3_2026) > 2 else None
        row["top3_2026_imp"]    = top3_2026[2][1] if len(top3_2026) > 2 else None
    else:
        row.update({"n_2026": len(df_2026_clean), "delta_auc_2026": None,
                    "auc_baseline_2026": None, "auc_full_2026": None,
                    "top1_2026_feat": None, "top1_2026_imp": None,
                    "top2_2026_feat": None, "top2_2026_imp": None,
                    "top3_2026_feat": None, "top3_2026_imp": None})

    # ── 2) 2026 per-month ΔAUC ──
    monthly_aucs = []
    for mo in MONTHS_2026:
        df_mo = df[(df.index.year == 2026) & (df.index.month == mo)].copy()
        df_mo_clean = df_mo[use_cols + ["dir_y"]].replace([np.inf,-np.inf], np.nan).dropna()
        m = train_xgb_get_metrics(df_mo_clean, v5_cols, use_cols)
        d = m["delta_auc"] if m else None
        row[f"delta_auc_2026_m{mo:02d}"] = d
        if d is not None: monthly_aucs.append(d)
    if monthly_aucs:
        row["monthly_2026_mean"]   = round(float(np.mean(monthly_aucs)), 4)
        row["monthly_2026_pos"]    = int(sum(1 for d in monthly_aucs if d > 0))
        row["monthly_2026_total"]  = int(len(monthly_aucs))
        row["monthly_2026_std"]    = round(float(np.std(monthly_aucs)), 4)
        row["monthly_consistency"] = row["monthly_2026_pos"] >= 4 and row["monthly_2026_mean"] > 0
    else:
        row.update({"monthly_2026_mean": None, "monthly_2026_pos": 0,
                    "monthly_2026_total": 0, "monthly_2026_std": None,
                    "monthly_consistency": False})

    # ── 3) Recent-3-year (2024+2025+2026) consistency ──
    yearly_aucs = []
    for yr in RECENT_YEARS:
        df_yr = df[df.index.year == yr].copy()
        df_yr_clean = df_yr[use_cols + ["dir_y"]].replace([np.inf,-np.inf], np.nan).dropna()
        m = train_xgb_get_metrics(df_yr_clean, v5_cols, use_cols)
        d = m["delta_auc"] if m else None
        row[f"delta_auc_y{yr}"] = d
        if d is not None: yearly_aucs.append(d)
    if yearly_aucs:
        row["recent_3yr_mean"] = round(float(np.mean(yearly_aucs)), 4)
        row["recent_3yr_pos"]  = int(sum(1 for d in yearly_aucs if d > 0))
        row["recent_3yr_total"] = int(len(yearly_aucs))
        row["recent_3yr_consistent"] = row["recent_3yr_pos"] >= 2 and row["recent_3yr_mean"] > 0
    else:
        row.update({"recent_3yr_mean": None, "recent_3yr_pos": 0,
                    "recent_3yr_total": 0, "recent_3yr_consistent": False})

    # ── 4) Per-feature best aggregator rule (top 5 by 2026 importance) ──
    rules = []
    if m_2026:
        qtl_imp = {k: v for k, v in m_2026["feature_importance"].items() if k in qtl_cols}
        qtl_top5 = sorted(qtl_imp.items(), key=lambda kv: -kv[1])[:5]
        for fname, imp_val in qtl_top5:
            rule = best_threshold_two_sided(df_2026_clean[fname], df_2026_clean["dir_y"], min_n=200)
            if rule:
                rules.append({"feature": fname, "importance": round(imp_val, 4), **rule})
    row["best_rules"] = json.dumps(rules)
    for i, r in enumerate(rules[:3], 1):
        row[f"rule{i}_feat"]   = r["feature"]
        row[f"rule{i}_thr"]    = r["threshold"]
        row[f"rule{i}_side"]   = r["side"]
        row[f"rule{i}_wr_d"]   = r["wr_delta"]
        row[f"rule{i}_n"]      = r["n_fires"]

    # ── 5) Live trade replay ──
    cell_trades = LIVE_TRADES[(LIVE_TRADES["pair"]==pair) &
                                (LIVE_TRADES["session"]==session) &
                                (LIVE_TRADES["dir"]==direction)] if not LIVE_TRADES.empty else pd.DataFrame()
    row["live_n_trades"] = len(cell_trades)
    row["live_wr_baseline"] = round(float((cell_trades["exit_net"] > 0).mean()), 4) if len(cell_trades) >= 2 else None
    row["live_mean_pips"]   = round(float(cell_trades["exit_net"].mean()), 2) if len(cell_trades) >= 1 else None
    # Replay top-3 rules: if rule fired, would V5 still have taken the trade?
    replay = []
    for r in rules[:3]:
        f = r["feature"]
        if f not in cell_trades.columns: continue
        thr = r["threshold"]; side = r["side"]
        fires_mask = (cell_trades[f] > thr) if side == "gt" else (cell_trades[f] < thr)
        n_would_block = int((~fires_mask).sum())   # would NOT have taken these
        n_would_take  = int(fires_mask.sum())
        wr_after_filter = float((cell_trades[fires_mask]["exit_net"] > 0).mean()) if fires_mask.sum() >= 1 else None
        wr_blocked      = float((cell_trades[~fires_mask]["exit_net"] > 0).mean()) if (~fires_mask).sum() >= 1 else None
        replay.append({
            "rule": f"{f} {side} {thr}",
            "n_taken_with_rule": n_would_take, "wr_taken": round(wr_after_filter, 4) if wr_after_filter is not None else None,
            "n_blocked_by_rule": n_would_block, "wr_blocked": round(wr_blocked, 4) if wr_blocked is not None else None,
        })
    row["live_replay"] = json.dumps(replay)

    # ── 6) Cell status ──
    # CONFIRMED: monthly_consistency AND recent_3yr_consistent AND delta_auc_2026 > 0
    # DEVIATING: 2026 positive but some months negative
    # NEEDS_DATA: live N < 3
    # DISABLE: delta_auc_2026 < 0 AND recent_3yr_mean < 0 AND live_wr_baseline < 0.4 (if data)
    delta_2026 = row.get("delta_auc_2026", 0) or 0
    recent_mean = row.get("recent_3yr_mean", 0) or 0
    monthly_mean = row.get("monthly_2026_mean", 0) or 0
    monthly_pos  = row.get("monthly_2026_pos", 0)
    live_n = row["live_n_trades"]
    live_wr = row["live_wr_baseline"]

    if delta_2026 > 0 and recent_mean > 0 and monthly_pos >= 4:
        status = "CONFIRMED"
    elif delta_2026 < -0.005 and recent_mean < -0.002:
        if live_n >= 3 and live_wr is not None and live_wr < 0.35:
            status = "DISABLE"
        elif live_n == 0:
            status = "DISABLE_NEEDS_DATA"
        else:
            status = "WEAK_NEGATIVE"
    elif delta_2026 > 0 and (recent_mean < 0 or monthly_pos < 4):
        status = "DEVIATING"
    elif live_n < 3:
        status = "NEEDS_DATA"
    else:
        status = "MIXED"
    row["cell_status"] = status

    return row

if __name__ == "__main__":
    print(f"=== V5 MASTER MATRIX BUILDER ===")
    print(f"Building per (pair × session × direction) = 48 cells × all metrics on Mini ({N_JOBS} cores)")
    print(f"Live trades loaded: {len(LIVE_TRADES)}")
    t0 = time.time()
    cells = [(p, s, d) for p in PAIRS for s in SESSIONS for d in DIRECTIONS]
    results = Parallel(n_jobs=N_JOBS, verbose=10)(delayed(process_cell)(*c) for c in cells)
    elapsed = time.time() - t0
    print(f"\nTotal: {elapsed:.1f}s")

    # Save full JSON
    out_json = OUT / "master_matrix.json"
    out_json.write_text(json.dumps(results, indent=2, default=str))
    print(f"→ {out_json}")

    # CSV
    df_master = pd.DataFrame(results)
    # Sort by status priority + delta_auc_2026 desc
    status_order = {"CONFIRMED":0, "DEVIATING":1, "MIXED":2, "WEAK_NEGATIVE":3, "NEEDS_DATA":4, "DISABLE_NEEDS_DATA":5, "DISABLE":6}
    df_master["status_rank"] = df_master["cell_status"].map(status_order)
    df_master = df_master.sort_values(["status_rank","delta_auc_2026"], ascending=[True, False])
    df_master.to_csv(OUT / "master_matrix.csv", index=False)
    print(f"→ {OUT / 'master_matrix.csv'}")

    # Summary
    print(f"\n=== CELL STATUS DISTRIBUTION ===")
    print(df_master["cell_status"].value_counts().to_string())

    print(f"\n=== TOP 12 CELLS by delta_auc_2026 (where qtl candidates still help) ===")
    top12 = df_master[df_master["delta_auc_2026"] > 0].head(12)
    print(top12[["pair","session","direction","current_profile","current_evidence",
                  "delta_auc_2026","monthly_2026_pos","monthly_2026_total","recent_3yr_mean",
                  "live_n_trades","live_wr_baseline","cell_status",
                  "top1_2026_feat","rule1_thr","rule1_side","rule1_wr_d"]].to_string(index=False))

    print(f"\n=== CELLS RECOMMENDED FOR DISABLE (no edge) ===")
    disable = df_master[df_master["cell_status"].str.startswith("DISABLE")]
    print(f"{len(disable)} cells")
    if len(disable) > 0:
        print(disable[["pair","session","direction","current_profile","current_evidence",
                        "delta_auc_2026","recent_3yr_mean","monthly_2026_pos","live_n_trades",
                        "live_wr_baseline","cell_status"]].to_string(index=False))
