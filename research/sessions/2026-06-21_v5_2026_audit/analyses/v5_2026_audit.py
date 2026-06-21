"""V5 2026 re-audit: profiles + aggregator rules + qtl candidates, ALL on 2026 data ONLY.

Three concurrent audits, one per cell × direction (48 cells):
  A) Direction PROFILE assignment audit:
     For each cell × direction, compute the bar-by-bar "profile score" using each of
     V5's three profile templates (continuation_strong, reversion, default). Measure
     each profile's per-cell AUC at predicting that direction's win-label. The
     best-AUC profile is the optimal 2026 assignment. Compare to V5's current.

  B) Aggregator rule audit:
     For each rule (atr_conc>2.5, atr_h1_relative>1.6 reversion-boost,
     atr_h1_relative>1.6 HTF-suppress), measure:
       - trigger rate in 2026 (% of bars firing)
       - per-cell AUC of "amplified features" subset score when triggered vs not
     A rule HOLDS if AUC delta > 0 when triggered. Otherwise flag.

  C) QTL candidate config (2026 only):
     Re-run the per-cell XGB but on 2026 data only. Output ready-to-paste config
     with per-cell-direction top-3 features + threshold + side, all derived from
     2026 alone (NOT averaged with prior years).
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
OUT      = ROOT / "audit_2026"
OUT.mkdir(exist_ok=True)

PAIRS    = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
SESSIONS = ["asia","london","ny"]
DIRECTIONS = ["long","short"]
N_JOBS   = 8

# ── V5's existing profile weight templates (lifted from direction_profiles.py) ──
PROFILE_WEIGHTS = {
    "default": [
        ("h1_ret_1bar",+17.61),("rsi_slope",+10.41),("zscore_1h",+8.73),
        ("h1_ret_4bar",+7.35),("d_ret",+7.09),("ema20_1h_dist_pct",+6.37),
        ("pdh_dist_pips",+5.95),("pdl_dist_pips",+5.88),("pdl_dist_atr_pct",+5.69),
        ("pdh_dist_atr_pct",+5.62),("rsi14",+4.79),("htf_pct_20",+1.91),
        ("htf_pct_60",+1.01),("ema20_dist_pct",-0.57),("bb_pos",-0.55),
        ("zscore_5m",-0.55),("ema5_dist_pips",-0.53),("ret_5m",-0.50),
        ("ret_15m",-0.45),("ret_1h",-0.44),("ret_30m",-0.41),
        ("ema50_dist_pct",-0.39),("close_pos_daily",-0.30),("ema_cross_pips",-0.27),
    ],
    "continuation_strong": [
        ("h1_ret_1bar",+26.0),("rsi_slope",+10.41),("zscore_1h",+8.73),
        ("h1_ret_4bar",+9.0),("d_ret",+7.09),("ema20_1h_dist_pct",+7.5),
        ("pdh_dist_pips",+4.0),("pdl_dist_pips",+2.5),("pdl_dist_atr_pct",+2.5),
        ("pdh_dist_atr_pct",+4.0),("rsi14",+4.79),("htf_pct_20",+3.5),
        ("htf_pct_60",+2.0),("ema20_dist_pct",-0.57),("bb_pos",-0.55),
        ("zscore_5m",-0.55),("ema5_dist_pips",-0.53),("ret_5m",-0.50),
        ("ret_15m",-0.45),("ret_1h",-0.44),("ret_30m",-0.41),
        ("ema50_dist_pct",-0.39),("close_pos_daily",-1.5),("ema_cross_pips",-0.27),
    ],
    "reversion": [
        ("h1_ret_1bar",+17.61),("rsi_slope",+5.0),("zscore_1h",+4.0),
        ("h1_ret_4bar",+2.5),("d_ret",+2.0),("ema20_1h_dist_pct",+2.0),
        ("pdh_dist_pips",+1.5),("pdl_dist_pips",+1.5),("pdl_dist_atr_pct",+1.5),
        ("pdh_dist_atr_pct",+1.5),("rsi14",+3.0),("htf_pct_20",+0.5),
        ("htf_pct_60",+0.3),("ema20_dist_pct",-2.5),("bb_pos",-2.0),
        ("zscore_5m",-2.5),("ema5_dist_pips",-2.5),("ret_5m",-2.0),
        ("ret_15m",-2.0),("ret_1h",-2.0),("ret_30m",-2.0),
        ("ema50_dist_pct",-2.0),("close_pos_daily",-2.5),("ema_cross_pips",-2.0),
    ],
}

# ── V5's current assignments (lifted from direction_profiles.PROFILE_ASSIGNMENT) ──
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

META_COLS = ("session","label","fwd_ret_pips")

def compute_profile_score(df, profile_weights):
    """Per-bar normalized profile score = sum(normalized_feat × weight) / sum(|weight|).
    Each feature is z-score normalized over the cell's full data (one-time training)."""
    score = pd.Series(0.0, index=df.index)
    total_abs_w = sum(abs(w) for _, w in profile_weights) or 1.0
    for fname, w in profile_weights:
        if fname not in df.columns: continue
        v = df[fname].astype(float)
        # Z-score normalize
        mean = v.mean(); std = v.std()
        if std == 0 or pd.isna(std): continue
        norm = (v - mean) / std
        score += norm * w / total_abs_w
    return score

def process_audit_cell(pair, session, direction):
    """Returns dict with profile audit + aggregator audit + qtl-2026 config for this cell-direction."""
    df = pd.read_parquet(FEATURES / f"{pair}_features.parquet")
    df = df[df["session"] == session]
    df = df[df.index.year == 2026].copy()
    if direction == "long":
        df["dir_y"] = (df["fwd_ret_pips"] > 0).astype(int)
    else:
        df["dir_y"] = (df["fwd_ret_pips"] < 0).astype(int)

    # Need at least 2K bars for stable AUC
    if len(df) < 2000:
        return {"pair": pair, "session": session, "direction": direction,
                "error": f"too few 2026 rows: {len(df)}"}

    # === A) PROFILE AUDIT ===
    profile_aucs = {}
    for name, weights in PROFILE_WEIGHTS.items():
        score = compute_profile_score(df, weights)
        valid = ~score.isna() & ~df["dir_y"].isna()
        if valid.sum() < 1000: continue
        try:
            # For long direction: positive score should predict win. For short: negative score should predict win.
            # So flip sign for short:
            sign_aligned = score if direction == "long" else -score
            auc = roc_auc_score(df["dir_y"][valid].values, sign_aligned[valid].values)
            profile_aucs[name] = float(auc)
        except Exception:
            profile_aucs[name] = None

    best_profile = max(profile_aucs.items(), key=lambda kv: kv[1] if kv[1] else 0)[0] if profile_aucs else "default"
    best_auc = profile_aucs.get(best_profile, 0.5)
    current_profile, current_evidence = CURRENT_ASSIGNMENTS.get((pair, session, direction), ("default", "NO_DATA"))
    current_auc = profile_aucs.get(current_profile, 0.5)
    profile_audit = {
        "current_assignment": current_profile,
        "current_evidence": current_evidence,
        "best_2026": best_profile,
        "best_2026_auc": round(best_auc, 4),
        "current_2026_auc": round(current_auc, 4) if current_auc else 0.5,
        "all_profile_aucs": {k: round(v, 4) for k, v in profile_aucs.items() if v},
        "mismatch": current_profile != best_profile,
        "lift_if_switched": round(best_auc - (current_auc or 0.5), 4),
    }

    # === B) AGGREGATOR RULE AUDIT ===
    agg_audit = {}
    # Rule 1: atr_conc > 2.5 → HTF features amplified ×1.5
    htf_features = ["htf_pct_20", "htf_pct_60", "h1_ret_4bar", "d_ret"]
    htf_default_w = {f: w for f, w in PROFILE_WEIGHTS["default"] if f in htf_features}
    htf_score = compute_profile_score(df, [(f, w) for f, w in htf_default_w.items()])
    sign_aligned_htf = htf_score if direction == "long" else -htf_score
    rule1_trigger = (df["atr_conc"] > 2.5).fillna(False) if "atr_conc" in df.columns else pd.Series(False, index=df.index)
    valid = ~sign_aligned_htf.isna() & ~df["dir_y"].isna()
    if rule1_trigger[valid].sum() >= 100 and (~rule1_trigger[valid]).sum() >= 100:
        try:
            auc_trig = roc_auc_score(df["dir_y"][valid & rule1_trigger].values, sign_aligned_htf[valid & rule1_trigger].values)
            auc_no   = roc_auc_score(df["dir_y"][valid & ~rule1_trigger].values, sign_aligned_htf[valid & ~rule1_trigger].values)
            agg_audit["atr_conc>2.5_amplifies_HTF"] = {
                "trigger_rate_2026": round(float(rule1_trigger.mean()), 4),
                "auc_when_triggered": round(auc_trig, 4),
                "auc_when_not": round(auc_no, 4),
                "auc_delta": round(auc_trig - auc_no, 4),
                "rule_holds_2026": auc_trig > auc_no,
            }
        except Exception:
            agg_audit["atr_conc>2.5_amplifies_HTF"] = {"error": "auc-compute"}

    # Rule 2: atr_h1_relative > 1.6 → reversion features amplified ×1.3
    rev_features = ["ema20_dist_pct", "bb_pos", "zscore_5m", "ret_15m", "ema5_dist_pips", "ret_5m", "ret_30m", "close_pos_daily"]
    rev_default_w = {f: w for f, w in PROFILE_WEIGHTS["default"] if f in rev_features}
    rev_score = compute_profile_score(df, [(f, w) for f, w in rev_default_w.items()])
    sign_aligned_rev = rev_score if direction == "long" else -rev_score
    rule2_trigger = (df["atr_h1_relative"] > 1.6).fillna(False) if "atr_h1_relative" in df.columns else pd.Series(False, index=df.index)
    valid = ~sign_aligned_rev.isna() & ~df["dir_y"].isna()
    if rule2_trigger[valid].sum() >= 100 and (~rule2_trigger[valid]).sum() >= 100:
        try:
            auc_trig = roc_auc_score(df["dir_y"][valid & rule2_trigger].values, sign_aligned_rev[valid & rule2_trigger].values)
            auc_no   = roc_auc_score(df["dir_y"][valid & ~rule2_trigger].values, sign_aligned_rev[valid & ~rule2_trigger].values)
            agg_audit["atr_h1_rel>1.6_amplifies_reversion"] = {
                "trigger_rate_2026": round(float(rule2_trigger.mean()), 4),
                "auc_when_triggered": round(auc_trig, 4),
                "auc_when_not": round(auc_no, 4),
                "auc_delta": round(auc_trig - auc_no, 4),
                "rule_holds_2026": auc_trig > auc_no,
            }
        except Exception:
            agg_audit["atr_h1_rel>1.6_amplifies_reversion"] = {"error": "auc-compute"}

    # Rule 3: atr_h1_relative > 1.6 → HTF features SUPPRESSED ×0.5 (so rule predicts HTF gets WORSE when triggered)
    sign_aligned_htf_for_rule3 = sign_aligned_htf  # reuse from rule 1
    if rule2_trigger[valid].sum() >= 100 and (~rule2_trigger[valid]).sum() >= 100:
        try:
            auc_trig = roc_auc_score(df["dir_y"][valid & rule2_trigger].values, sign_aligned_htf_for_rule3[valid & rule2_trigger].values)
            auc_no   = roc_auc_score(df["dir_y"][valid & ~rule2_trigger].values, sign_aligned_htf_for_rule3[valid & ~rule2_trigger].values)
            agg_audit["atr_h1_rel>1.6_suppresses_HTF"] = {
                "trigger_rate_2026": round(float(rule2_trigger.mean()), 4),
                "auc_when_triggered": round(auc_trig, 4),
                "auc_when_not": round(auc_no, 4),
                "auc_delta": round(auc_trig - auc_no, 4),
                "rule_holds_2026": auc_trig < auc_no,  # suppress rule HOLDS if HTF AUC is LOWER when triggered
            }
        except Exception:
            agg_audit["atr_h1_rel>1.6_suppresses_HTF"] = {"error": "auc-compute"}

    # === C) QTL 2026-only top candidates + thresholds (re-run XGB on 2026 only) ===
    qtl_cols = [c for c in df.columns if c.startswith("q_")]
    v5_cols  = [c for c in df.columns if c not in META_COLS + ("dir_y",) and not c.startswith("q_")]
    use_cols = v5_cols + qtl_cols
    df_clean = df[use_cols + ["dir_y"]].replace([np.inf, -np.inf], np.nan).dropna()
    qtl_config = None
    if len(df_clean) >= 1500:
        split = int(len(df_clean) * 0.7)
        ytr = df_clean.iloc[:split]["dir_y"].values
        yte = df_clean.iloc[split:]["dir_y"].values
        if len(set(yte)) >= 2:
            Xtr_v5   = df_clean.iloc[:split][v5_cols].values
            Xte_v5   = df_clean.iloc[split:][v5_cols].values
            Xtr_full = df_clean.iloc[:split][use_cols].values
            Xte_full = df_clean.iloc[split:][use_cols].values
            KW = dict(n_estimators=120, max_depth=4, learning_rate=0.05, subsample=0.8,
                      colsample_bytree=0.8, eval_metric="auc", tree_method="hist", n_jobs=1, verbosity=0)
            try:
                m_base = XGBClassifier(**KW); m_base.fit(Xtr_v5, ytr)
                m_full = XGBClassifier(**KW); m_full.fit(Xtr_full, ytr)
                auc_base = float(roc_auc_score(yte, m_base.predict_proba(Xte_v5)[:,1]))
                auc_full = float(roc_auc_score(yte, m_full.predict_proba(Xte_full)[:,1]))
                imp = dict(zip(use_cols, m_full.feature_importances_.tolist()))
                qtl_imp = sorted({c: imp[c] for c in qtl_cols}.items(), key=lambda kv: -kv[1])
                top3 = qtl_imp[:3]
                # Best threshold per top-3 candidate
                rules = []
                for fname, imp_val in top3:
                    fv = df_clean[fname]
                    valid_mask = ~fv.isna()
                    if valid_mask.sum() < 500: continue
                    stump = DecisionTreeClassifier(max_depth=1, min_samples_leaf=max(100, int(valid_mask.sum()*0.05)))
                    stump.fit(fv[valid_mask].values.reshape(-1,1), df_clean["dir_y"][valid_mask].values)
                    if stump.tree_.node_count < 3: continue
                    T = float(stump.tree_.threshold[0])
                    y = df_clean["dir_y"][valid_mask].values
                    fv_v = fv[valid_mask].values
                    above = y[fv_v > T]; below = y[fv_v <= T]
                    wr_above = float(above.mean()); wr_below = float(below.mean())
                    if wr_above >= wr_below:
                        side = "gt"; wr_t = wr_above; wr_o = wr_below; n_t = len(above); n_o = len(below)
                    else:
                        side = "lt"; wr_t = wr_below; wr_o = wr_above; n_t = len(below); n_o = len(above)
                    rules.append({
                        "feature": fname, "importance": round(imp_val, 4),
                        "threshold": round(T, 4), "side": side,
                        "wr_when_rule_fires": round(wr_t, 3),
                        "wr_when_rule_doesnt": round(wr_o, 3),
                        "wr_delta": round(wr_t - wr_o, 3),
                        "n_fires": int(n_t), "n_doesnt": int(n_o),
                    })
                qtl_config = {
                    "auc_baseline_2026": round(auc_base, 4),
                    "auc_full_2026":     round(auc_full, 4),
                    "delta_auc_2026":    round(auc_full - auc_base, 4),
                    "wire_in":           (auc_full - auc_base) > 0.0,
                    "top3_rules":        rules,
                }
            except Exception as e:
                qtl_config = {"error": str(e)}

    return {
        "pair": pair, "session": session, "direction": direction,
        "n_2026_bars": len(df),
        "profile_audit": profile_audit,
        "aggregator_audit": agg_audit,
        "qtl_2026_config": qtl_config,
    }

if __name__ == "__main__":
    cells = [(p, s, d) for p in PAIRS for s in SESSIONS for d in DIRECTIONS]
    print(f"Auditing {len(cells)} cell-directions against 2026 data, parallel across {N_JOBS} cores")
    t0 = time.time()
    results = Parallel(n_jobs=N_JOBS, verbose=10)(
        delayed(process_audit_cell)(p, s, d) for p, s, d in cells
    )
    print(f"\nTotal: {time.time() - t0:.1f}s")

    # Save
    out_json = OUT / "audit_2026_per_cell.json"
    out_json.write_text(json.dumps(results, indent=2, default=str))
    print(f"→ {out_json}")

    # ── SUMMARY: profile audit ─────────────────────────────────────────────
    print(f"\n=== A) PROFILE AUDIT — V5's current direction profile assignments vs 2026-best ===")
    rows = []
    for r in results:
        if "error" in r: continue
        pa = r["profile_audit"]
        rows.append({
            "pair": r["pair"], "session": r["session"], "direction": r["direction"],
            "current": pa["current_assignment"], "current_evidence": pa["current_evidence"],
            "best_2026": pa["best_2026"], "best_2026_auc": pa["best_2026_auc"],
            "current_2026_auc": pa["current_2026_auc"], "mismatch": pa["mismatch"],
            "lift_if_switched": pa["lift_if_switched"],
        })
    pa_df = pd.DataFrame(rows)
    pa_df.to_csv(OUT / "profile_audit_2026.csv", index=False)
    print(f"  Mismatches (current assignment ≠ 2026-best): {pa_df['mismatch'].sum()}/{len(pa_df)}")
    print(f"  Mean AUC lift if switched to 2026-best:  {pa_df['lift_if_switched'].mean():+.4f}")
    print(f"\n  Top 15 cells where switching profile would help most:")
    print(pa_df.sort_values("lift_if_switched", ascending=False).head(15).to_string(index=False))

    # ── SUMMARY: aggregator audit ──────────────────────────────────────────
    print(f"\n=== B) AGGREGATOR RULE AUDIT ===")
    rule_rows = []
    for r in results:
        if "error" in r: continue
        for rule_name, r2 in r.get("aggregator_audit", {}).items():
            if "error" in r2: continue
            rule_rows.append({"pair": r["pair"], "session": r["session"], "direction": r["direction"],
                               "rule": rule_name, **r2})
    rule_df = pd.DataFrame(rule_rows)
    if not rule_df.empty:
        rule_df.to_csv(OUT / "aggregator_audit_2026.csv", index=False)
        print(f"  Per-rule HOLD rate in 2026 (cells where rule_holds=True):")
        hold_rate = rule_df.groupby("rule")["rule_holds_2026"].agg(["sum","count"])
        hold_rate["rate"] = (hold_rate["sum"] / hold_rate["count"] * 100).round(1)
        print(hold_rate.to_string())
        print(f"\n  Mean AUC delta per rule in 2026:")
        print(rule_df.groupby("rule")["auc_delta"].agg(["mean","std","min","max"]).round(4).to_string())

    # ── SUMMARY: qtl 2026 ΔAUC ─────────────────────────────────────────────
    print(f"\n=== C) QTL CANDIDATES 2026-ONLY ΔAUC ===")
    qtl_rows = []
    for r in results:
        if "error" in r: continue
        q = r.get("qtl_2026_config")
        if q and "error" not in q:
            qtl_rows.append({
                "pair": r["pair"], "session": r["session"], "direction": r["direction"],
                "delta_auc_2026": q["delta_auc_2026"],
                "wire_in": q["wire_in"],
                "top1": q["top3_rules"][0]["feature"] if q["top3_rules"] else None,
                "top1_thr": q["top3_rules"][0]["threshold"] if q["top3_rules"] else None,
                "top1_side": q["top3_rules"][0]["side"] if q["top3_rules"] else None,
                "top1_wr_when_fires": q["top3_rules"][0]["wr_when_rule_fires"] if q["top3_rules"] else None,
            })
    qtl_df = pd.DataFrame(qtl_rows)
    qtl_df.to_csv(OUT / "qtl_2026_per_cell.csv", index=False)
    print(f"  Cells where qtl candidates wire in (ΔAUC > 0): {qtl_df['wire_in'].sum()}/{len(qtl_df)}")
    print(f"\n  All cells, sorted by 2026 ΔAUC:")
    print(qtl_df.sort_values("delta_auc_2026", ascending=False).to_string(index=False))

    # ── Build ready-to-paste 2026 config ────────────────────────────────────
    config = {}
    for r in results:
        if "error" in r: continue
        key = f"({r['pair']},{r['session']},{r['direction']})"
        config[key] = {
            "direction_profile_recommended": r["profile_audit"]["best_2026"],
            "direction_profile_current":     r["profile_audit"]["current_assignment"],
            "profile_mismatch":              r["profile_audit"]["mismatch"],
            "profile_auc_lift_if_switched":  r["profile_audit"]["lift_if_switched"],
            "qtl_wire_in_2026":              r.get("qtl_2026_config", {}).get("wire_in", False),
            "qtl_delta_auc_2026":            r.get("qtl_2026_config", {}).get("delta_auc_2026"),
            "qtl_top3":                      r.get("qtl_2026_config", {}).get("top3_rules", []),
        }
    (OUT / "config_2026_per_cell.json").write_text(json.dumps(config, indent=2))
    print(f"\n→ {OUT / 'config_2026_per_cell.json'}")
