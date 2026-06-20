#!/usr/bin/env python3
"""Per-(pair, session) breakout for the wall_frac and ema50_atr_frac findings.

For each V3 factor + each V5 feature it interacts with most strongly, show
the 24-cell matrix so we can see if the effect is uniform or concentrated
in specific pairs/sessions.
"""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path("/Volumes/Alien Device/scrooge-research/v5_aggregator_test_2026-06-18")
PAIRS = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
SESSIONS = ["asia","london","ny"]

def load_cells():
    out = {}
    for fp in sorted(OUT.glob("*_*.json")):
        if fp.name in ("summary.json","matrix.json"): continue
        try: d = json.loads(fp.read_text())
        except Exception: continue
        if "error" in d: continue
        out[(d["pair"], d["session"])] = d
    return out


def matrix_delta(cells, v3, v5, ml):
    """24-cell grid of importance delta (positive = wipe-out by V3)."""
    grid = {}
    for (pair, sess), c in cells.items():
        ab = c.get("ablations",{}).get(v3,{})
        grid[(pair, sess)] = ab.get("delta_vs_baseline",{}).get(ml,{}).get(v5)
    return grid


def matrix_spanratio(cells, v3, v5):
    """24-cell grid of HI/LO span ratio (>1 = amplifier in V3 HI tertile)."""
    grid = {}
    for (pair, sess), c in cells.items():
        cond = c.get("conditional_decile_span",{}).get(v3,{})
        lo, hi = cond.get("lo",{}).get(v5), cond.get("hi",{}).get(v5)
        if lo is None or hi is None or abs(lo) < 0.05:
            grid[(pair, sess)] = None
        else:
            grid[(pair, sess)] = abs(hi) / abs(lo)
    return grid


def print_grid(title, grid, fmt="{:+.4f}"):
    print(f"\n{title}")
    print(f"  {'PAIR':<10}", " ".join(f"{s:>9}" for s in SESSIONS))
    for p in PAIRS:
        row = [f"  {p:<10}"]
        for s in SESSIONS:
            v = grid.get((p, s))
            row.append(f"{fmt.format(v):>9}" if v is not None else f"{'—':>9}")
        print(" ".join(row))


def main():
    cells = load_cells()
    print(f"loaded {len(cells)} cells")

    # ── wall_frac on DIRECTION ML ──
    print("="*78)
    print("WALL_FRAC  ── per (pair, session) variation ──")
    print("="*78)
    # wipe-out side (importance delta on h1_ret_1bar — the most universally
    # suppressed V5 feature, mean +0.0097 across cells)
    print_grid(
        "wall_frac WIPE-OUT of h1_ret_1bar (importance delta, direction-ML)",
        matrix_delta(cells, "wall_frac", "h1_ret_1bar", "direction"),
    )
    print_grid(
        "wall_frac WIPE-OUT of ret_1h (direction-ML)",
        matrix_delta(cells, "wall_frac", "ret_1h", "direction"),
    )
    # amplifier side
    print_grid(
        "wall_frac AMPLIFY of htf_pct_20 (HI/LO decile-span ratio on net_60m)",
        matrix_spanratio(cells, "wall_frac", "htf_pct_20"),
        fmt="{:>6.2f}",
    )
    print_grid(
        "wall_frac AMPLIFY of pdh_dist_pips (HI/LO)",
        matrix_spanratio(cells, "wall_frac", "pdh_dist_pips"),
        fmt="{:>6.2f}",
    )
    print_grid(
        "wall_frac AMPLIFY of rsi14 (HI/LO)",
        matrix_spanratio(cells, "wall_frac", "rsi14"),
        fmt="{:>6.2f}",
    )
    # suppressor side
    print_grid(
        "wall_frac SUPPRESS bb_pos signal (HI/LO < 1 = suppressed)",
        matrix_spanratio(cells, "wall_frac", "bb_pos"),
        fmt="{:>6.2f}",
    )

    # ── ema50_atr_frac on DIRECTION ML ──
    print("\n" + "="*78)
    print("EMA50_ATR_FRAC  ── per (pair, session) variation ──")
    print("="*78)
    print_grid(
        "ema50_atr_frac WIPE-OUT of h1_ret_1bar (direction-ML)",
        matrix_delta(cells, "ema50_atr_frac", "h1_ret_1bar", "direction"),
    )
    print_grid(
        "ema50_atr_frac AMPLIFY of ema5_dist_pips (HI/LO)",
        matrix_spanratio(cells, "ema50_atr_frac", "ema5_dist_pips"),
        fmt="{:>6.2f}",
    )
    print_grid(
        "ema50_atr_frac AMPLIFY of ret_15m (HI/LO)",
        matrix_spanratio(cells, "ema50_atr_frac", "ret_15m"),
        fmt="{:>6.2f}",
    )
    print_grid(
        "ema50_atr_frac AMPLIFY of ret_5m (HI/LO)",
        matrix_spanratio(cells, "ema50_atr_frac", "ret_5m"),
        fmt="{:>6.2f}",
    )

    # ── atr_conc (HTF suppressor) ──
    print("\n" + "="*78)
    print("ATR_CONC  ── per (pair, session) variation ──")
    print("="*78)
    print_grid(
        "atr_conc SUPPRESS htf_pct_20 (HI/LO; mean 0.35× — strongest single signal)",
        matrix_spanratio(cells, "atr_conc", "htf_pct_20"),
        fmt="{:>6.2f}",
    )
    print_grid(
        "atr_conc SUPPRESS adr_consumed (HI/LO; mean 0.42×)",
        matrix_spanratio(cells, "atr_conc", "adr_consumed"),
        fmt="{:>6.2f}",
    )

    # OOS baselines (which cells are best behaved)
    print("\n" + "="*78)
    print("DIRECTION OOS CORR per cell — where does the ML fit best?")
    print("="*78)
    grid = {(c["pair"], c["session"]): c["baselines"]["direction"]["oos_corr"]
            for c in cells.values()}
    print_grid("direction OOS corr", grid, fmt="{:>6.3f}")
    grid = {(c["pair"], c["session"]): c["baselines"]["momentum"]["oos_corr"]
            for c in cells.values()}
    print_grid("momentum OOS corr", grid, fmt="{:>6.3f}")


if __name__ == "__main__":
    main()
