"""Per-(cell × direction × year) profile-best stability check.

For each cell × direction × year (2019-2026), compute which V5 profile template
(default / continuation_strong / reversion) yields highest direction-prediction
AUC. Then identify cells where:
  - Same profile wins in ≥5 of 8 years (STABLE)
  - Same profile wins in 2024+2025+2026 (RECENT STABLE)
  - 2026-best matches 44-trade matrix initial assignment (TWO-WAY CONFIRMED)

Plus cross-reference with year-by-year ΔAUC (qtl candidate wire-in consistency).
"""
import os, json, time, subprocess
from pathlib import Path
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import roc_auc_score

def assert_on_mini():
    s = subprocess.run(["system_profiler","SPHardwareDataType"], capture_output=True, text=True).stdout
    if "CPYQTH294R" not in s: raise RuntimeError("NOT ON MINI")
    print("✓ device verified: Mini CPYQTH294R")
assert_on_mini()

ROOT     = Path.home() / "qtl-discovery-8yr"
FEATURES = ROOT / "features"
OUT      = ROOT / "consistency"
OUT.mkdir(exist_ok=True)

PAIRS    = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
SESSIONS = ["asia","london","ny"]
DIRECTIONS = ["long","short"]
N_JOBS   = 8
YEARS    = list(range(2019, 2027))

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
    score = pd.Series(0.0, index=df.index)
    total_abs_w = sum(abs(w) for _, w in profile_weights) or 1.0
    for fname, w in profile_weights:
        if fname not in df.columns: continue
        v = df[fname].astype(float)
        mean = v.mean(); std = v.std()
        if std == 0 or pd.isna(std): continue
        norm = (v - mean) / std
        score += norm * w / total_abs_w
    return score

def best_profile_for_slice(pair, session, direction, year):
    df = pd.read_parquet(FEATURES / f"{pair}_features.parquet")
    df = df[df["session"] == session]
    df = df[df.index.year == year].copy()
    if direction == "long":
        df["dir_y"] = (df["fwd_ret_pips"] > 0).astype(int)
    else:
        df["dir_y"] = (df["fwd_ret_pips"] < 0).astype(int)
    if len(df) < 1500:
        return {"pair": pair, "session": session, "direction": direction, "year": year,
                "best_profile": None, "best_auc": None, "n_bars": len(df), "error": "too few rows"}
    aucs = {}
    for name, weights in PROFILE_WEIGHTS.items():
        score = compute_profile_score(df, weights)
        valid = ~score.isna() & ~df["dir_y"].isna()
        if valid.sum() < 1000: continue
        try:
            sign_aligned = score if direction == "long" else -score
            auc = roc_auc_score(df["dir_y"][valid].values, sign_aligned[valid].values)
            aucs[name] = float(auc)
        except Exception:
            aucs[name] = None
    if not aucs:
        return {"pair": pair, "session": session, "direction": direction, "year": year,
                "best_profile": None, "best_auc": None, "n_bars": len(df), "error": "no aucs"}
    best = max(aucs.items(), key=lambda kv: kv[1] if kv[1] else 0)
    return {
        "pair": pair, "session": session, "direction": direction, "year": year,
        "best_profile": best[0], "best_auc": round(best[1], 4),
        "default_auc":  round(aucs.get("default", 0.5), 4),
        "continuation_strong_auc": round(aucs.get("continuation_strong", 0.5), 4),
        "reversion_auc": round(aucs.get("reversion", 0.5), 4),
        "n_bars": len(df),
    }

if __name__ == "__main__":
    jobs = [(p, s, d, y) for p in PAIRS for s in SESSIONS for d in DIRECTIONS for y in YEARS]
    print(f"Running {len(jobs)} (cell × direction × year) profile-best computations × 8 cores")
    t0 = time.time()
    results = Parallel(n_jobs=N_JOBS, verbose=10)(delayed(best_profile_for_slice)(*j) for j in jobs)
    print(f"Total: {time.time() - t0:.1f}s")

    df = pd.DataFrame(results)
    df.to_csv(OUT / "best_profile_per_cell_year.csv", index=False)

    # ── Build the stability matrix per (cell × direction) ─────────────────
    print(f"\n=== STABILITY: same profile wins across N years (per cell × direction) ===")
    pivot = df.pivot_table(index=["pair","session","direction"], columns="year",
                            values="best_profile", aggfunc="first")
    pivot.to_csv(OUT / "stability_matrix.csv")
    # For each cell × direction: mode profile + agreement count
    rows = []
    for (p, s, d), row in pivot.iterrows():
        vals = row.dropna().tolist()
        if not vals: continue
        mode_profile = max(set(vals), key=vals.count)
        agree = vals.count(mode_profile)
        # Recent: 2024+2025+2026
        recent = [row.get(y) for y in [2024, 2025, 2026] if y in row.index and pd.notna(row.get(y))]
        recent_mode = max(set(recent), key=recent.count) if recent else None
        recent_agree = recent.count(recent_mode) if recent_mode else 0
        # 2026
        y2026 = row.get(2026)
        # Current assignment
        cur_prof, cur_evid = CURRENT_ASSIGNMENTS.get((p, s, d), ("default", "NO_DATA"))
        rows.append({
            "pair": p, "session": s, "direction": d,
            "current": cur_prof, "current_evidence": cur_evid,
            "y2019": row.get(2019), "y2020": row.get(2020), "y2021": row.get(2021),
            "y2022": row.get(2022), "y2023": row.get(2023), "y2024": row.get(2024),
            "y2025": row.get(2025), "y2026": y2026,
            "mode_8yr": mode_profile, "agree_8yr": agree,
            "mode_recent": recent_mode, "agree_recent": recent_agree,
            "current_matches_2026": cur_prof == y2026,
            "current_matches_recent_mode": cur_prof == recent_mode,
            "2026_matches_recent": y2026 == recent_mode,
            "fully_stable_recent": (recent_agree == 3),
            "fully_stable_8yr": (agree == 8),
        })
    s_df = pd.DataFrame(rows)
    s_df.to_csv(OUT / "consistency_summary.csv", index=False)

    print(f"\n=== Cells where 2024+2025+2026 ALL agree on same profile (recent-stable) ===")
    recent_stable = s_df[s_df["fully_stable_recent"] == True]
    print(f"  {len(recent_stable)}/48 cells are recent-stable")
    if not recent_stable.empty:
        print(recent_stable[["pair","session","direction","current","mode_recent","current_matches_recent_mode"]].to_string(index=False))

    print(f"\n=== Cells where ALL 8 years agree on same profile (fully stable across 8yr) ===")
    fully_stable = s_df[s_df["fully_stable_8yr"] == True]
    print(f"  {len(fully_stable)}/48 cells are 8yr-stable")
    if not fully_stable.empty:
        print(fully_stable[["pair","session","direction","current","mode_8yr","current_matches_2026"]].to_string(index=False))

    print(f"\n=== Cells where V5 CURRENT assignment matches 2026 best (no change needed) ===")
    matches_2026 = s_df[s_df["current_matches_2026"] == True]
    print(f"  {len(matches_2026)}/48 cells current = 2026-best")
    print(matches_2026[["pair","session","direction","current","current_evidence","mode_recent","agree_recent","agree_8yr"]].to_string(index=False))

    print(f"\n=== TIER 1: GOLD-STANDARD CELLS (current=2026, recent-stable 3/3, ≥6/8 years agree) ===")
    gold = s_df[(s_df["current_matches_2026"]) & (s_df["fully_stable_recent"]) & (s_df["agree_8yr"] >= 6)]
    print(f"  {len(gold)}/48 cells")
    if not gold.empty:
        print(gold[["pair","session","direction","current","current_evidence","agree_8yr"]].to_string(index=False))

    print(f"\n=== TIER 2: RECENT-CONSISTENT (current=2026, recent-stable 3/3) ===")
    tier2 = s_df[(s_df["current_matches_2026"]) & (s_df["fully_stable_recent"])]
    tier2_only = tier2[~tier2.index.isin(gold.index)]
    print(f"  {len(tier2_only)}/48 cells")
    if not tier2_only.empty:
        print(tier2_only[["pair","session","direction","current","current_evidence","agree_8yr"]].to_string(index=False))

    # Aggregate profile flipping per pair × session
    print(f"\n=== Profile flip frequency: how many distinct profiles appeared in 8 years per cell ===")
    s_df["n_distinct_profiles"] = pivot.apply(lambda r: r.dropna().nunique(), axis=1).values
    print(s_df.groupby("n_distinct_profiles").size())
