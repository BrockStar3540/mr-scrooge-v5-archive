#!/usr/bin/env python3
"""Per-cell excursion geometry -> ratchet tailoring study.

Q1: lopsided bars — which features scale one-sidedness |L|? does signed L
    (direction) clear noise per cell? (prior verdict: no — retest honestly)
Q2: balanced bars — which features scale total travel R? (low/med/high distance
    -> earlier / current / wider ratchet)
Q3: per-cell ratchet class: QUICK-SLICE vs STANDARD vs RUNNER, from R240/R60
    growth + offer/dead rates + broker-trade anchor.

Corpus: ~/v5-truth-matrix/<PAIR>_truth.parquet (leak-clean, broker-anchored).
Window: 2026 bars. Walk-forward: train Jan-Apr, test May-Jul. Robustness:
30m-thinned rho must agree in sign (overlap-inflation guard).
Anchor: ~/v5-trade-excursions/excursions.csv (230 broker trades).
Output: ~/v5-ratchet-profiles/{RATCHET_PROFILE_REPORT.md, cell_profiles.csv,
        feature_scaling.csv}
"""
import json, subprocess
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

s = subprocess.run(["system_profiler","SPHardwareDataType"], capture_output=True, text=True).stdout
if "CPYQTH294R" not in s: raise RuntimeError("NOT ON MINI")

TM  = Path.home() / "v5-truth-matrix"
OUT = Path.home() / "v5-ratchet-profiles"; OUT.mkdir(exist_ok=True)
PAIRS = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
FEATS = ["atr_5m","q_kc_up_dist_pips","atr_conc","rvol_5bar","q_willr_m5","atr_h1_relative"]
TCOLS = ["mfe_long_60","mae_long_60","mfe_long_240","mae_long_240"]
RT_COST = {"AUD_USD":1.35,"USD_JPY":1.6,"EUR_USD":1.6,"USD_CHF":1.6,"USD_CAD":1.8,
           "GBP_USD":1.95,"AUD_JPY":2.35,"EUR_JPY":2.7}
sess_of = lambda h: "london" if 7 <= h < 13 else ("ny" if 13 <= h < 22 else "asia")
EPS = 1e-9

def rho(a, b):
    m = a.notna() & b.notna()
    if m.sum() < 300: return np.nan
    return spearmanr(a[m], b[m]).statistic

scal_rows, prof_rows = [], []
for pair in PAIRS:
    df = pd.read_parquet(TM / f"{pair}_truth.parquet", columns=FEATS + TCOLS)
    df = df[df.index >= "2026-01-01"].copy()
    df["sess"] = [sess_of(h) for h in df.index.hour]
    up, dn = df["mfe_long_60"], df["mae_long_60"]
    df["R60"]  = up + dn
    df["L60"]  = (up - dn) / (up + dn + EPS)
    df["absL"] = df["L60"].abs()
    df["R240"] = df["mfe_long_240"] + df["mae_long_240"]
    train = df[df.index < "2026-05-01"]
    test  = df[df.index >= "2026-05-01"]
    thin  = df.iloc[::6]  # 30m spacing — overlap guard
    for sess in ("asia","london","ny"):
        gtr, gte, gth = (g[g["sess"]==sess] for g in (train, test, thin))
        g = df[df["sess"]==sess]
        # Q1/Q2 feature scaling
        for f in FEATS:
            for tgt, name in ((("absL"), "onesidedness"), (("L60"), "signedL"), (("R60"), "travel")):
                sub_tr, sub_te, sub_th = gtr, gte, gth
                if name == "travel":  # balanced subset
                    sub_tr = gtr[gtr["absL"] < 1/3]; sub_te = gte[gte["absL"] < 1/3]; sub_th = gth[gth["absL"] < 1/3]
                r_tr, r_te, r_th = (rho(x[f], x[tgt]) for x in (sub_tr, sub_te, sub_th))
                ok = (not np.isnan(r_tr) and not np.isnan(r_te) and not np.isnan(r_th)
                      and np.sign(r_tr) == np.sign(r_te) == np.sign(r_th) and abs(r_tr) >= 0.10 and abs(r_te) >= 0.07)
                scal_rows.append(dict(pair=pair, sess=sess, feature=f, target=name,
                    rho_train=round(r_tr,3) if r_tr==r_tr else None,
                    rho_test=round(r_te,3) if r_te==r_te else None,
                    rho_thin=round(r_th,3) if r_th==r_th else None, robust=ok))
        # Q2 terciles on balanced bars (test window only, honest view)
        bal = gte[gte["absL"] < 1/3]
        # Q3 geometry profile
        b = g[g["absL"] < 1/3]
        prof_rows.append(dict(pair=pair, sess=sess, n2026=len(g),
            balanced_share=round(float((g["absL"] < 1/3).mean()),3),
            med_up60=round(float(g["mfe_long_60"].median()),2),
            med_R60=round(float(g["R60"].median()),2),
            med_R240=round(float(g["R240"].median()),2),
            growth=round(float(g["R240"].median()/(g["R60"].median()+EPS)),2),
            p75_up240=round(float(g["mfe_long_240"].quantile(0.75)),2),
            rt_cost=RT_COST[pair]))
scal = pd.DataFrame(scal_rows); scal.to_csv(OUT/"feature_scaling.csv", index=False)
prof = pd.DataFrame(prof_rows)

# ratchet class: growth terciles across 24 cells
g1, g2 = prof["growth"].quantile([1/3, 2/3])
def klass(r):
    viable_quick = r["med_up60"] >= r["rt_cost"] + 2.0   # a 60m slice must clear cost + real lock
    if r["growth"] <= g1 and viable_quick: return "QUICK-SLICE"
    if r["growth"] >= g2: return "RUNNER"
    return "STANDARD"
prof["klass"] = prof.apply(klass, axis=1)

# broker anchor: winners' median duration + MFE per cell
exc = pd.read_csv(Path.home()/"v5-trade-excursions"/"excursions.csv")
exc_w = exc[exc["real_pips"] > 0]
anch = exc_w.groupby(["pair","sess"]).agg(n_w=("real_pips","size"),
        med_dur_w=("dur_min","median"), med_mfe_w=("mfe","median")).reset_index()
prof = prof.merge(anch, on=["pair","sess"], how="left")
prof.to_csv(OUT/"cell_profiles.csv", index=False)

# report
rb = scal[scal["robust"]]
L = ["# Ratchet Profile Study — per-cell excursion geometry (2026 corpus, walk-forward)\n",
     f"24 cells, 2026 bars, train Jan-Apr / test May-Jul, 30m-thinned sign guard. "
     f"Balanced bar = |L60|<1/3 where L=(up-dn)/(up+dn).\n",
     "## Q1 — signed direction from features (lopsidedness -> direction?)",
     f"Robust signed-L relationships: {len(rb[rb['target']=='signedL'])} of {len(scal[scal['target']=='signedL'])} tested.",
     rb[rb["target"]=="signedL"].to_markdown(index=False) if len(rb[rb["target"]=="signedL"]) else "**NONE cleared the bar — confirms 07-04 direction-horizon verdict (WHEN not WHICH WAY).**",
     "\n## Q1b — one-sidedness |L| scaling (trendiness magnitude, unsigned)",
     rb[rb["target"]=="onesidedness"].to_markdown(index=False) if len(rb[rb["target"]=="onesidedness"]) else "none robust",
     "\n## Q2 — total travel R60 scaling on balanced bars (ratchet distance knob)",
     rb[rb["target"]=="travel"].to_markdown(index=False) if len(rb[rb["target"]=="travel"]) else "none robust",
     "\n## Q3 — per-cell ratchet class",
     f"growth = med R240 / med R60 (how much the move extends past the first hour); "
     f"tercile cuts at {g1:.2f}/{g2:.2f}. QUICK-SLICE requires med up60 >= RT cost + 2p. "
     "Broker anchor: winners' median duration/MFE from the 230-trade table (small n — anchor, not proof).\n",
     prof.sort_values(["klass","growth"]).to_markdown(index=False)]
(OUT/"RATCHET_PROFILE_REPORT.md").write_text("\n".join(str(x) for x in L))
print("robust rels:", len(rb), "| classes:", prof["klass"].value_counts().to_dict())
print("done ->", OUT)
