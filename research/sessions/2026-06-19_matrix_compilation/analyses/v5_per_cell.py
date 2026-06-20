#!/usr/bin/env python3
"""Per-session aggregator correlations + per-(pair, session) summary stats."""
import csv
from pathlib import Path
from collections import defaultdict
from statistics import correlation as pearson, mean


SRC = Path("/tmp/v5_full_matrix.csv")
rows = list(csv.DictReader(SRC.open()))

# === Per-session aggregator correlations ===
FEATS = ["raw_dir", "d_cert", "m_cert", "h1_ret_aligned",
         "atr_5m", "atr_1h", "atr_conc", "atr_h1_relative",
         "wall_frac", "trend_4h_pips", "htf_pct_20", "htf_pct_60"]

def to_float(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def session_corr_table(feature, target, sessions):
    """Pearson(feature, target) for each session — and 'global' across all."""
    out = {}
    for sess in sessions + ["ALL"]:
        bucket = rows if sess == "ALL" else [r for r in rows if r["session"] == sess]
        xs, ys = [], []
        for r in bucket:
            x = to_float(r.get(feature)); y = to_float(r.get(target))
            if x is None or y is None:
                continue
            xs.append(x); ys.append(y)
        if len(xs) < 3:
            out[sess] = None
        else:
            try:
                out[sess] = (pearson(xs, ys), len(xs))
            except Exception:
                out[sess] = None
    return out


sessions = ["asia", "london", "ny"]

print("=" * 110)
print("PER-SESSION PEARSON CORRELATIONS")
print("=" * 110)
print(f"{'feature':<22}{'asia':>14}{'london':>14}{'ny':>14}{'ALL':>14}")
print("-" * 110)
print("\n--- vs peak_pips (does signal predict pip travel?) ---")
for feat in FEATS:
    res = session_corr_table(feat, "peak_pips", sessions)
    cells = []
    for sess in sessions + ["ALL"]:
        if res[sess] is None:
            cells.append(" " * 14)
        else:
            c, n = res[sess]
            cells.append(f"{c:+.3f}(n={n:>2})".rjust(14))
    print(f"{feat:<22}{cells[0]}{cells[1]}{cells[2]}{cells[3]}")

print("\n--- vs exit_net (does signal predict outcome) ---")
for feat in FEATS:
    res = session_corr_table(feat, "exit_net", sessions)
    cells = []
    for sess in sessions + ["ALL"]:
        if res[sess] is None:
            cells.append(" " * 14)
        else:
            c, n = res[sess]
            cells.append(f"{c:+.3f}(n={n:>2})".rjust(14))
    print(f"{feat:<22}{cells[0]}{cells[1]}{cells[2]}{cells[3]}")


# === Per-(pair, session) cell summary ===
print()
print("=" * 110)
print("PER-(PAIR × SESSION) CELL SUMMARY")
print("=" * 110)
print(f"{'pair':<10}{'session':<10}{'n':>4}{'wins':>6}{'losses':>8}{'WR':>7}"
      f"{'avg_peak':>10}{'avg_out':>10}{'sum_out':>10}"
      f"{'avg_h1':>10}{'avg_atrconc':>13}")
print("-" * 110)

cells = defaultdict(list)
for r in rows:
    key = (r["pair"], r["session"])
    cells[key].append(r)

cell_summary = []
for key in sorted(cells.keys()):
    pair, session = key
    bucket = cells[key]
    outs = [to_float(r["exit_net"]) for r in bucket]
    outs = [o for o in outs if o is not None]
    if not outs:
        continue
    n = len(bucket)
    wins = sum(1 for o in outs if o > 0)
    losses = sum(1 for o in outs if o <= 0)
    wr = wins / n
    avg_peak = mean([to_float(r["peak_pips"]) for r in bucket if to_float(r["peak_pips"]) is not None])
    avg_out = mean(outs)
    sum_out = sum(outs)
    h1s = [to_float(r["h1_ret_aligned"]) for r in bucket if to_float(r["h1_ret_aligned"]) is not None]
    avg_h1 = mean(h1s) if h1s else None
    accs = [to_float(r["atr_conc"]) for r in bucket if to_float(r["atr_conc"]) is not None]
    avg_acc = mean(accs) if accs else None
    cell_summary.append((pair, session, n, wins, losses, wr, avg_peak, avg_out, sum_out, avg_h1, avg_acc))
    print(f"{pair:<10}{session:<10}{n:>4}{wins:>6}{losses:>8}{wr:>6.0%} "
          f"{avg_peak:>+9.2f} {avg_out:>+9.2f} {sum_out:>+9.2f}"
          f"  {(avg_h1 if avg_h1 is not None else 0):>+8.2f}"
          f"  {(avg_acc if avg_acc is not None else 0):>+11.2f}")

# === Per-session aggregate roll-up ===
print()
print("=" * 110)
print("PER-SESSION AGGREGATE")
print("=" * 110)
print(f"{'session':<10}{'n':>4}{'WR':>7}{'sum_out':>10}{'avg_out':>10}{'avg_peak':>10}")
print("-" * 60)
for sess in sessions:
    bucket = [r for r in rows if r["session"] == sess]
    outs = [to_float(r["exit_net"]) for r in bucket if to_float(r["exit_net"]) is not None]
    peaks = [to_float(r["peak_pips"]) for r in bucket if to_float(r["peak_pips"]) is not None]
    wins = sum(1 for o in outs if o > 0)
    print(f"{sess:<10}{len(outs):>4}{wins/len(outs):>6.0%} "
          f"{sum(outs):>+9.2f} {mean(outs):>+9.2f} {mean(peaks):>+9.2f}")
