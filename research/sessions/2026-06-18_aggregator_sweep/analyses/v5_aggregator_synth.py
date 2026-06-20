#!/usr/bin/env python3
"""Synthesize the 24 per-cell aggregator-test JSONs into a verdict report.

For each V3 candidate factor f, across 8 pairs * 3 sessions = 24 cells:
  WIPE-OUT EVIDENCE     mean delta_importance[v5] = imp(without f) - imp(with f)
                         positive = V5 feature's importance ROSE once f was
                         removed, i.e. f was suppressing it (wipe-out).
  AMPLIFIER EVIDENCE    span_ratio[v5] = decile_span(net_60m | v5 within HI tertile of f)
                                       / decile_span(net_60m | v5 within LO tertile of f)
                         span_ratio > 1.3 = amplifier; < 0.7 = suppressor.
  NUMERICAL VARIATION   per-tertile spans tell us at WHICH f-bin the lift lives.

Outputs:
  report.txt   human-readable per-factor verdicts
  matrix.json  full per-factor x per-V5 matrix for follow-on
"""
from __future__ import annotations
import json
from pathlib import Path
from statistics import mean, median

OUT = Path("/Volumes/Alien Device/scrooge-research/v5_aggregator_test_2026-06-18")
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


def load_cells():
    cells = []
    for fp in sorted(OUT.glob("*_*.json")):
        if fp.name in ("summary.json", "matrix.json"): continue
        try:
            cells.append(json.loads(fp.read_text()))
        except Exception as e:
            print(f"skip {fp.name}: {e}")
    return [c for c in cells if "error" not in c]


def safe_mean(xs):
    xs = [x for x in xs if x is not None]
    return mean(xs) if xs else None


def safe_med(xs):
    xs = [x for x in xs if x is not None]
    return median(xs) if xs else None


def per_factor_summary(cells, v3, ml):
    """For one (V3 candidate, ML), aggregate across the 24 cells."""
    # 1) WIPE-OUT: mean delta over cells, per V5 feature
    wipeout_rows = []
    for v5 in V5_ALL:
        deltas = []
        for c in cells:
            ab = c.get("ablations", {}).get(v3)
            if not ab: continue
            d = ab.get("delta_vs_baseline", {}).get(ml, {}).get(v5)
            if d is None: continue
            deltas.append(d)
        if not deltas: continue
        wipeout_rows.append({
            "v5": v5,
            "mean_delta": safe_mean(deltas),
            "med_delta": safe_med(deltas),
            "n_cells": len(deltas),
            # positive shares = how often the delta was positive
            "pct_positive": sum(1 for d in deltas if d > 0) / len(deltas),
        })
    return wipeout_rows


def per_factor_amplifier(cells, v3, ml):
    """span_ratio = decile-span of net_60m vs V5, conditional on V3-tertile."""
    rows = []
    for v5 in V5_ALL:
        ratios = []
        lo_spans, hi_spans, mid_spans, base_spans = [], [], [], []
        for c in cells:
            cond = c.get("conditional_decile_span", {}).get(v3)
            if not cond or "error" in cond: continue
            lo = cond.get("lo", {}).get(v5)
            hi = cond.get("hi", {}).get(v5)
            mid = cond.get("mid", {}).get(v5)
            uncond = cond.get("unconditional", {}).get(v5)
            if uncond is not None: base_spans.append(uncond)
            if lo is not None: lo_spans.append(lo)
            if hi is not None: hi_spans.append(hi)
            if mid is not None: mid_spans.append(mid)
            if lo is None or hi is None: continue
            # span_ratio uses absolute magnitude — direction can flip across cells
            if abs(lo) < 0.05: continue  # avoid blow-up on tiny denominators
            ratios.append(abs(hi) / abs(lo))
        if not ratios: continue
        rows.append({
            "v5": v5,
            "median_span_lo": safe_med(lo_spans),
            "median_span_mid": safe_med(mid_spans),
            "median_span_hi": safe_med(hi_spans),
            "median_span_unconditional": safe_med(base_spans),
            "median_hi_over_lo_ratio": safe_med(ratios),
            "n_cells": len(ratios),
        })
    return rows


def fmt_signed(x, w=8, prec=4):
    if x is None: return f"{'—':>{w}}"
    return f"{x:+{w}.{prec}f}"


def fmt(x, w=8, prec=3):
    if x is None: return f"{'—':>{w}}"
    return f"{x:>{w}.{prec}f}"


def write_report(cells):
    lines = []
    add = lines.append
    add("=" * 78)
    add("V5 AGGREGATOR TEST  —  Mr. Scrooge, 2026-06-18")
    add(f"  cells_completed = {len(cells)}  (of 24)")
    add(f"  V5 direction features = {len(V5_DIR)}")
    add(f"  V5 momentum features  = {len(V5_MOM)}")
    add("=" * 78)
    add("")
    add("DELTA = imp(without V3) - imp(with V3).")
    add("  positive on a V5 feat = V3 was SUPPRESSING that V5 (wipe-out behavior).")
    add("  negative on a V5 feat = V3 was AMPLIFYING that V5's signal.")
    add("")
    add("HI/LO RATIO = |decile_span(V5 vs net_60m within V3-HI-tertile)|")
    add("            / |decile_span(V5 vs net_60m within V3-LO-tertile)|.")
    add("  > 1.3 = V5 feature's signal grows in V3's high tertile  (amplifier).")
    add("  < 0.7 = V5 feature's signal shrinks in V3's high tertile (suppressor).")
    add("")

    # V3 candidates: read from first cell's ablations dict
    v3_list = list(cells[0]["ablations"].keys()) if cells else []

    for v3 in v3_list:
        add("=" * 78)
        add(f"V3 CANDIDATE FACTOR :  {v3}")
        add("=" * 78)

        for ml in ("direction", "momentum"):
            add(f"\n  ── ML: {ml.upper()}  (target = {'net_60m' if ml=='direction' else '|net_60m|'}) ──\n")

            # A) wipe-out / amplifier via importance delta
            rows = per_factor_summary(cells, v3, ml)
            rows.sort(key=lambda r: -(r["mean_delta"] or 0))
            add("    Importance DELTA across 24 cells (top suppressed / top amplified):")
            add(f"      {'V5 feature':<22}  {'mean_d':>9}  {'med_d':>9}  {'pct>0':>6}  n")
            # top 8 wipe-out (positive deltas)
            for r in rows[:8]:
                if (r['mean_delta'] or 0) <= 0: break
                add(f"      {r['v5']:<22}  {fmt_signed(r['mean_delta'],9,5)}  {fmt_signed(r['med_delta'],9,5)}  {r['pct_positive']*100:>5.0f}%  {r['n_cells']:>2}")
            add("      ... (amplification — negative deltas) ...")
            for r in sorted(rows, key=lambda r: (r["mean_delta"] or 0))[:8]:
                if (r['mean_delta'] or 0) >= 0: break
                add(f"      {r['v5']:<22}  {fmt_signed(r['mean_delta'],9,5)}  {fmt_signed(r['med_delta'],9,5)}  {r['pct_positive']*100:>5.0f}%  {r['n_cells']:>2}")

            # B) conditional span ratio (only meaningful for direction; the
            # decile-span was computed against net_60m anyway)
            if ml == "direction":
                amps = per_factor_amplifier(cells, v3, ml)
                amps.sort(key=lambda r: -(r["median_hi_over_lo_ratio"] or 0))
                add("\n    Conditional decile-span on net_60m, by V3 tertile (top amplifiers):")
                add(f"      {'V5 feature':<22}  {'unc':>7}  {'LO':>7}  {'MID':>7}  {'HI':>7}  {'HI/LO':>7}")
                for r in amps[:10]:
                    add(f"      {r['v5']:<22}  "
                        f"{fmt(r['median_span_unconditional'],7,3)}  "
                        f"{fmt(r['median_span_lo'],7,3)}  "
                        f"{fmt(r['median_span_mid'],7,3)}  "
                        f"{fmt(r['median_span_hi'],7,3)}  "
                        f"{fmt(r['median_hi_over_lo_ratio'],7,2)}")
                add("    Suppressors (HI/LO < 1):")
                for r in sorted(amps, key=lambda r: r["median_hi_over_lo_ratio"] or 99)[:6]:
                    if (r["median_hi_over_lo_ratio"] or 0) >= 1: break
                    add(f"      {r['v5']:<22}  "
                        f"{fmt(r['median_span_unconditional'],7,3)}  "
                        f"{fmt(r['median_span_lo'],7,3)}  "
                        f"{fmt(r['median_span_mid'],7,3)}  "
                        f"{fmt(r['median_span_hi'],7,3)}  "
                        f"{fmt(r['median_hi_over_lo_ratio'],7,2)}")
        add("")

    # OOS table per cell
    add("=" * 78)
    add("BASELINE ML PERFORMANCE PER CELL  (OOS Pearson corr on last 30%)")
    add("=" * 78)
    add(f"  {'pair':<10} {'session':<8} {'n_train':>8}  {'dir_corr':>9}  {'mom_corr':>9}")
    for c in cells:
        b = c.get("baselines", {})
        add(f"  {c['pair']:<10} {c['session']:<8} {c['n_train']:>8}  "
            f"{fmt(b.get('direction',{}).get('oos_corr'),9,3)}  "
            f"{fmt(b.get('momentum',{}).get('oos_corr'),9,3)}")

    (OUT / "report.txt").write_text("\n".join(lines))

    # also dump a structured matrix for follow-on
    matrix = {"v3_candidates": v3_list, "v5_all": V5_ALL,
              "per_factor": {}}
    for v3 in v3_list:
        matrix["per_factor"][v3] = {}
        for ml in ("direction", "momentum"):
            matrix["per_factor"][v3][ml] = {
                "importance_delta": per_factor_summary(cells, v3, ml),
                "amplifier_ratio":  per_factor_amplifier(cells, v3, ml),
            }
    (OUT / "matrix.json").write_text(json.dumps(matrix, indent=2, default=str))
    print(f"wrote {OUT/'report.txt'} and {OUT/'matrix.json'}")


def main():
    cells = load_cells()
    if not cells:
        print("no completed cells found"); return
    write_report(cells)


if __name__ == "__main__":
    main()
