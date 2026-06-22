#!/usr/bin/env python3
"""V5 inverted_live_cells outcome reader.

Reads the V5 systemd journal, pairs each INVERTED_LIVE SIGNAL with its ENTERED +
EXIT lines, and reports per-cell outcomes for cells in inverted_live_cells.

The "baseline" column is what we WOULD have netted by NOT inverting — it's the
negative of the inverted realized net pips. (Market orders + symmetric SL/ratchet
distances make this a fair comparison: the same bar moves the price one direction
or the other; if we flip the trade, we flip the sign of the outcome.)

Usage:
    python3 v5_inverted_live_report.py             # since first inverted_live commit
    python3 v5_inverted_live_report.py --since "2026-06-22 12:00:00"
    python3 v5_inverted_live_report.py --pair AUD_JPY
"""
from __future__ import annotations
import argparse, re, subprocess, sys
from collections import defaultdict
from statistics import mean

DEFAULT_SINCE = "2026-06-22 04:14:00"   # commit 200629f: inverted_live_cells went live

SIGNAL_INV = re.compile(
    r"SIGNAL (?P<pair>\w+) (?P<trade_dir>long|short) .* "
    r"INVERTED_LIVE signal_dir=(?P<signal_dir>\w+) trade_dir=(?P<trade_dir2>\w+)"
)
ENTERED = re.compile(
    r"ENTERED (?P<pair>\w+) (?P<direction>long|short) @ (?P<entry>[\d.]+) "
    r".*trade_id=(?P<tid>\d+)"
)
EXIT = re.compile(
    r"EXIT.*?(?P<pair>\w+) \| trade_id=(?P<tid>\d+) \| approx_net=(?P<net>[+-]?[\d.]+)p"
)


def journal_lines(since: str) -> list[str]:
    out = subprocess.run(
        ["journalctl", "--user", "-u", "mr-scrooge-v5",
         "--since", since, "--no-pager", "-o", "cat"],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.splitlines()


def parse(lines: list[str]):
    """Return (signals, trades). signals = list in chronological order;
    trades = dict[trade_id] -> {pair, direction, entry, net_pips}."""
    signals, trades = [], {}
    # SIGNAL → next ENTERED for same pair → keyed to that trade_id
    pending_signal_by_pair: dict[str, dict] = {}
    for ln in lines:
        if m := SIGNAL_INV.search(ln):
            sig = {"pair": m["pair"], "signal_dir": m["signal_dir"],
                   "trade_dir": m["trade_dir2"], "trade_id": None}
            pending_signal_by_pair[m["pair"]] = sig
            signals.append(sig)
        elif m := ENTERED.search(ln):
            tid = m["tid"]
            trades[tid] = {"pair": m["pair"], "direction": m["direction"],
                           "entry": float(m["entry"]), "net_pips": None}
            if sig := pending_signal_by_pair.pop(m["pair"], None):
                sig["trade_id"] = tid
        elif m := EXIT.search(ln):
            tid = m["tid"]
            if tid in trades:
                trades[tid]["net_pips"] = float(m["net"])
    return signals, trades


def report(signals, trades, pair_filter=None):
    # Filter to signals with a trade_id (i.e., trade was placed) and closed
    rows = []
    for s in signals:
        if pair_filter and s["pair"] != pair_filter:
            continue
        if s["trade_id"] is None:
            continue
        t = trades.get(s["trade_id"])
        if t is None or t["net_pips"] is None:
            continue
        rows.append({**s, "net_pips": t["net_pips"]})

    if not rows:
        n_open = sum(1 for s in signals
                     if (not pair_filter or s["pair"] == pair_filter)
                     and s["trade_id"] is not None
                     and trades.get(s["trade_id"], {}).get("net_pips") is None)
        print(f"No CLOSED inverted-live trades yet. (open/unmatched: {n_open})")
        return

    # Per-cell aggregation: (pair, signal_dir)
    per_cell = defaultdict(list)
    for r in rows:
        per_cell[(r["pair"], r["signal_dir"])].append(r["net_pips"])

    print(f"INVERTED_LIVE outcome report — {len(rows)} closed trade(s)\n")
    print(f"{'cell (pair/signal_dir → trade_dir)':<40} {'n':>3} "
          f"{'invert_mean':>12} {'invert_wr':>10} {'baseline_mean':>14}")
    print("-" * 82)
    overall_inv = []
    for (pair, sig_dir), pips in sorted(per_cell.items()):
        traded_dir = "short" if sig_dir == "long" else "long"
        n = len(pips)
        avg = mean(pips)
        wr = 100.0 * sum(1 for p in pips if p > 0) / n
        cell = f"{pair}/{sig_dir} → {traded_dir}"
        print(f"{cell:<40} {n:>3} {avg:>+11.2f}p {wr:>9.0f}% {-avg:>+13.2f}p")
        overall_inv.extend(pips)

    n = len(overall_inv)
    avg = mean(overall_inv)
    wr = 100.0 * sum(1 for p in overall_inv if p > 0) / n
    print("-" * 82)
    print(f"{'OVERALL':<40} {n:>3} {avg:>+11.2f}p {wr:>9.0f}% {-avg:>+13.2f}p")
    print(f"\nNet inversion benefit (invert_mean − baseline_mean): "
          f"{2 * avg:+.2f}p per trade")
    print(f"(baseline_mean = −1 × invert_mean; assumes symmetric SL/ratchet — "
          f"valid for this comparison.)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=DEFAULT_SINCE,
                    help=f"journalctl --since (default: {DEFAULT_SINCE})")
    ap.add_argument("--pair", default=None, help="filter to one pair")
    args = ap.parse_args()
    lines = journal_lines(args.since)
    signals, trades = parse(lines)
    if not signals:
        print(f"No INVERTED_LIVE signals found since {args.since}.")
        return 0
    report(signals, trades, pair_filter=args.pair)
    return 0


if __name__ == "__main__":
    sys.exit(main())
