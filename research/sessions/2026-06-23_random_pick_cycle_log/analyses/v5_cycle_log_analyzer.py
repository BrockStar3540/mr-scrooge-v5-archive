#!/usr/bin/env python3
"""V5 CYCLE log analyzer — backtest alternative rankings against per-cycle ticket data.

Reads the V5 systemd journal for CYCLE lines emitted by engine.py since the
random_pick + CYCLE log change (commit c43c38c, 2026-06-23 ~05:52 UTC).

For each cycle, parses all 8 pairs' state + which one was actually picked.
Then re-applies 4 alternative rankings to the same eligible-candidate set
and reports per-cell fire counts under each:

  1. max-composite  — current default; ranks by abs(composite_score)
  2. random         — uniform random choice (what live is doing now)
  3. vortex-aligned — prefer trades where vortex_diff direction matches trade dir
  4. comp x vortex  — abs(composite) x (1 + max(0, vortex_aligned))

Eligibility (per playmaker):
  - act=T (passes gates)
  - session is valid for the pair (PAIR_SESSIONS check)
  - cell not in disabled_cells (snapshotted from config at analysis time)

This gives an apples-to-apples view: same candidate set per cycle, different
ranker. Output shows distribution + diversity (how many distinct cells each
ranker would have fired across the window).

For outcome attribution (did the picked trade win/lose), join with the
per-trade ENTERED/EXIT lines using v5_mfe_mae_report.py + the journal trade_id.

Usage:
  python3 v5_cycle_log_analyzer.py                              # since 2026-06-23 05:52
  python3 v5_cycle_log_analyzer.py --since '2026-06-24 00:00:00'
  python3 v5_cycle_log_analyzer.py --csv                        # also dump per-cycle CSV
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from collections import defaultdict, Counter
from pathlib import Path
import random

SINCE = "2026-06-23 05:52:00"

# Pair sessions from V5's config/pairs.py (snapshotted; update if pairs.py changes)
PAIR_SESSIONS = {
    "AUD_USD": ["asia", "london", "ny"], "AUD_JPY": ["asia", "london", "ny"],
    "EUR_JPY": ["asia", "london", "ny"], "EUR_USD": ["london", "ny"],
    "GBP_USD": ["london", "ny"],         "USD_CAD": ["ny"],
    "USD_CHF": ["london", "ny"],         "USD_JPY": ["asia", "london", "ny"],
}

CONFIG_PATH = Path("/home/ubuntu/mr-scrooge-v5/config/playmaker_config.json")

# CYCLE 2026-06-23T05:52:14.655824+00:00 picked=NONE method=none | AUD_JPY/asia/short act=T dscore=-0.470 dcert=0.53 mcert=0.00 comp=-0.0000 vortex=-0.562 close_pos=0.102 | ...
CYCLE_HDR = re.compile(
    r"CYCLE (?P<ts>\S+) picked=(?P<picked>\S+) method=(?P<method>\S+)"
)
TICKET_RE = re.compile(
    r"(?P<pair>\w+)/(?P<sess>\w+)/(?P<dir>\w+) "
    r"act=(?P<act>[TF]) "
    r"dscore=(?P<dscore>[+-]?[\d.]+) dcert=(?P<dcert>[+-]?[\d.]+) "
    r"mcert=(?P<mcert>[+-]?[\d.]+) comp=(?P<comp>[+-]?[\d.]+) "
    r"vortex=(?P<vortex>[+-]?[\d.]+) close_pos=(?P<cpos>[+-]?[\d.]+)"
)


def load_disabled():
    try:
        cfg = json.loads(CONFIG_PATH.read_text())
        return frozenset(tuple(x) for x in cfg.get("disabled_cells", []) if len(x) == 3)
    except Exception:
        return frozenset()


def parse_cycles(since: str):
    raw = subprocess.check_output(
        ["journalctl", "--user", "-u", "mr-scrooge-v5",
         "--since", since, "--no-pager", "-o", "cat"],
        text=True,
    )
    cycles = []
    for line in raw.splitlines():
        if "CYCLE " not in line:
            continue
        # Strip everything before "CYCLE " (the python log prefix)
        idx = line.find("CYCLE ")
        body = line[idx:]
        parts = [p.strip() for p in body.split(" | ")]
        hdr = CYCLE_HDR.search(parts[0])
        if not hdr:
            continue
        tickets = []
        for chunk in parts[1:]:
            m = TICKET_RE.search(chunk)
            if not m:
                continue
            tickets.append({
                "pair": m["pair"], "session": m["sess"], "dir": m["dir"],
                "actionable": m["act"] == "T",
                "dscore": float(m["dscore"]),
                "dcert":  float(m["dcert"]),
                "mcert":  float(m["mcert"]),
                "composite": float(m["comp"]),
                "vortex":  float(m["vortex"]),
                "close_pos": float(m["cpos"]),
            })
        cycles.append({
            "ts": hdr["ts"], "picked": hdr["picked"], "method": hdr["method"],
            "tickets": tickets,
        })
    return cycles


def eligible(t, disabled):
    """Mirror playmaker's session + disabled filter (gates already encoded in act=T)."""
    if not t["actionable"]:
        return False
    if t["session"] not in PAIR_SESSIONS.get(t["pair"], []):
        return False
    if (t["pair"], t["session"], t["dir"]) in disabled:
        return False
    return True


# ── Alternative rankers ──
def rank_max_composite(cands):
    return max(cands, key=lambda t: abs(t["composite"]))

def rank_random(cands, rng):
    return rng.choice(cands)

def rank_vortex_aligned(cands):
    """Prefer trades where vortex_diff sign matches trade direction.
       For 'long', positive vortex aligned; for 'short', negative vortex aligned.
       Score = vortex × (+1 if long else -1). Higher = better alignment."""
    def aligned(t):
        sign = 1 if t["dir"] == "long" else -1
        return t["vortex"] * sign
    return max(cands, key=aligned)

def rank_comp_x_vortex(cands):
    def score(t):
        sign = 1 if t["dir"] == "long" else -1
        aligned = max(0.0, t["vortex"] * sign)
        return abs(t["composite"]) * (1.0 + aligned)
    return max(cands, key=score)

RANKERS = {
    "max-composite":  lambda cs, _: rank_max_composite(cs),
    "random":         lambda cs, rng: rank_random(cs, rng),
    "vortex-aligned": lambda cs, _: rank_vortex_aligned(cs),
    "comp*vortex":    lambda cs, _: rank_comp_x_vortex(cs),
}


def cell_key(t):
    return f"{t['pair']}/{t['session']}/{t['dir']}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=SINCE)
    ap.add_argument("--csv", action="store_true",
                    help="also dump per-cycle CSV of all candidates + picks")
    args = ap.parse_args()

    cycles = parse_cycles(args.since)
    if not cycles:
        print(f"No CYCLE lines found since {args.since}.")
        return 1

    disabled = load_disabled()
    rng = random.Random(42)   # seed for reproducible sim

    # Per-cell counters
    actionable_count = Counter()
    actual_pick = Counter()
    ranker_picks = {name: Counter() for name in RANKERS}
    no_eligible = 0
    total_cycles = len(cycles)

    for c in cycles:
        cands = [t for t in c["tickets"] if eligible(t, disabled)]
        for t in cands:
            actionable_count[cell_key(t)] += 1
        if c["picked"] != "NONE":
            actual_pick[c["picked"]] += 1
        if not cands:
            no_eligible += 1
            continue
        for name, ranker in RANKERS.items():
            chosen = ranker(cands, rng)
            ranker_picks[name][cell_key(chosen)] += 1

    print(f"V5 CYCLE log analyzer — window since {args.since}\n")
    print(f"Cycles parsed: {total_cycles}")
    print(f"Cycles with NO eligible candidates: {no_eligible} "
          f"({100*no_eligible/total_cycles:.0f}%)")
    print(f"Cycles with picked trade: {sum(actual_pick.values())} "
          f"({100*sum(actual_pick.values())/total_cycles:.0f}%)")
    print()

    cells_seen = sorted(actionable_count.keys())
    if not cells_seen:
        print("No eligible cells in window.")
        return 0

    print(f"=== Per-cell counts (eligibility + picks across rankers) ===")
    print(f"{'cell':<30} {'eligible':>9} {'actual':>7} "
          + "".join(f"{name:>15}" for name in RANKERS))
    for cell in cells_seen:
        elig = actionable_count[cell]
        actual = actual_pick.get(cell, 0)
        cols = "".join(f"{ranker_picks[name].get(cell, 0):>15}" for name in RANKERS)
        print(f"{cell:<30} {elig:>9} {actual:>7}{cols}")

    print()
    print(f"=== Diversity (distinct cells each ranker would fire) ===")
    actual_cells = sum(1 for c in cells_seen if actual_pick.get(c, 0) > 0)
    print(f"  actual live:   {actual_cells} distinct cells")
    for name in RANKERS:
        n = sum(1 for c in cells_seen if ranker_picks[name].get(c, 0) > 0)
        print(f"  {name:<14} {n:>2} distinct cells")

    # Skew metric: top-1 cell share (lower = more spread)
    print()
    print(f"=== Top-1 cell share (lower = more spread) ===")
    def top_share(counter):
        total = sum(counter.values())
        if not total: return 0.0
        return 100 * max(counter.values()) / total
    print(f"  actual live:   {top_share(actual_pick):.0f}%")
    for name in RANKERS:
        print(f"  {name:<14} {top_share(ranker_picks[name]):.0f}%")

    if args.csv:
        out = Path(__file__).resolve().parent.parent / "data" / "cycle_log_dump.csv"
        out.parent.mkdir(exist_ok=True)
        import csv
        with out.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ts","picked","method","pair","session","dir","actionable",
                        "dscore","dcert","mcert","composite","vortex","close_pos","eligible"])
            for c in cycles:
                for t in c["tickets"]:
                    w.writerow([c["ts"], c["picked"], c["method"],
                                t["pair"], t["session"], t["dir"], t["actionable"],
                                t["dscore"], t["dcert"], t["mcert"], t["composite"],
                                t["vortex"], t["close_pos"], eligible(t, disabled)])
        print(f"\n→ wrote {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
