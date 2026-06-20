#!/usr/bin/env python3
"""Per-session Pearson on the full extended aggregator set.

For each feature: asia / london / ny / ALL — vs peak_pips and vs exit_net.
Print also a 'rvol_alignment' check: does rvol_5bar > 1 (volume spike)
predict bigger peaks? does adr_consumed < 0.5 (room left) predict travel?
"""
import csv
from pathlib import Path
from statistics import correlation as pearson, mean


SRC = Path("/tmp/v5_full_matrix_v2.csv")
rows = list(csv.DictReader(SRC.open()))


def to_float(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def session_corr_table(feature, target, sessions):
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

# === group 1: prior signals (for reference baseline) ===
BASELINE = ["raw_dir", "m_cert", "h1_ret_aligned", "atr_conc", "atr_5m", "trend_4h_pips"]
# === group 2: NEW aggregators ===
NEW_FEATS = [
    "rvol_5bar", "rvol_12bar",
    "rsi14_m5", "rsi14_h1",
    "bb_pos_h1",
    "ema20_dist_pct", "ema50_dist_pct",
    "ret_5m_aligned", "ret_15m_aligned", "ret_30m_aligned",
    "adx14_h1", "adr_consumed",
]

def print_block(label, feats, target):
    print(f"\n=== {label} ({target}) ===")
    print(f"{'feature':<20}{'asia':>14}{'london':>14}{'ny':>14}{'ALL':>14}")
    print("-" * 78)
    for feat in feats:
        res = session_corr_table(feat, target, sessions)
        cells = []
        for sess in sessions + ["ALL"]:
            if res[sess] is None:
                cells.append(" " * 14)
            else:
                c, n = res[sess]
                cells.append(f"{c:+.3f}(n={n:>2})".rjust(14))
        print(f"{feat:<20}{cells[0]}{cells[1]}{cells[2]}{cells[3]}")


print("=" * 78)
print("BASELINE (previously analyzed) — reference")
print("=" * 78)
print_block("vs peak_pips", BASELINE, "peak_pips")
print_block("vs exit_net",  BASELINE, "exit_net")

print()
print("=" * 78)
print("NEW AGGREGATORS — volume / RSI / BB / EMA / short-term ret / ADX / ADR")
print("=" * 78)
print_block("vs peak_pips", NEW_FEATS, "peak_pips")
print_block("vs exit_net",  NEW_FEATS, "exit_net")

# === per-session top 3 for travel + top 3 for direction ===
print()
print("=" * 78)
print("TOP PREDICTORS PER SESSION (|Pearson| ranking)")
print("=" * 78)

ALL_FEATS = BASELINE + NEW_FEATS

for sess in sessions:
    print(f"\n--- {sess.upper()} (n=?) ---")
    rank = []
    for feat in ALL_FEATS:
        res = session_corr_table(feat, "peak_pips", [sess])
        if res[sess] is None: continue
        c, n = res[sess]
        rank.append((feat, c, n))
    rank.sort(key=lambda t: -abs(t[1]))
    print(f"  Predicting peak_pips (top 6):")
    for feat, c, n in rank[:6]:
        sign = "+" if c >= 0 else "−"
        print(f"    {feat:<22} {sign}{abs(c):.3f}  (n={n})")
    rank = []
    for feat in ALL_FEATS:
        res = session_corr_table(feat, "exit_net", [sess])
        if res[sess] is None: continue
        c, n = res[sess]
        rank.append((feat, c, n))
    rank.sort(key=lambda t: -abs(t[1]))
    print(f"  Predicting exit_net (top 6):")
    for feat, c, n in rank[:6]:
        sign = "+" if c >= 0 else "−"
        print(f"    {feat:<22} {sign}{abs(c):.3f}  (n={n})")

# === RSI + BB position pattern check ===
print()
print("=" * 78)
print("PATTERN CHECK — does extreme RSI/BB predict reversion? continuation?")
print("=" * 78)
print(f"{'cohort':<30}{'n':>4}{'WR':>7}{'avg_out':>10}{'avg_peak':>10}")

def cohort(label, predicate):
    matched = [r for r in rows if predicate(r)]
    if not matched:
        print(f"  {label:<28} (no matches)"); return
    outs = [to_float(r['exit_net']) for r in matched if to_float(r['exit_net']) is not None]
    peaks = [to_float(r['peak_pips']) for r in matched if to_float(r['peak_pips']) is not None]
    if not outs:
        print(f"  {label:<28} (no outs)"); return
    wr = sum(1 for o in outs if o > 0) / len(outs)
    print(f"  {label:<28}{len(outs):>4}{wr:>6.0%} {mean(outs):>+9.2f} {mean(peaks):>+9.2f}")

cohort("RSI_h1 oversold (<35)",   lambda r: (v := to_float(r['rsi14_h1'])) is not None and v < 35)
cohort("RSI_h1 neutral (35-65)",  lambda r: (v := to_float(r['rsi14_h1'])) is not None and 35 <= v <= 65)
cohort("RSI_h1 overbought (>65)", lambda r: (v := to_float(r['rsi14_h1'])) is not None and v > 65)
cohort("BB_h1 stretched (|x|>0.7)", lambda r: (v := to_float(r['bb_pos_h1'])) is not None and abs(v) > 0.7)
cohort("BB_h1 neutral (|x|<=0.7)",  lambda r: (v := to_float(r['bb_pos_h1'])) is not None and abs(v) <= 0.7)
cohort("ADX > 50 (strong trend)",  lambda r: (v := to_float(r['adx14_h1'])) is not None and v > 50)
cohort("ADX <= 20 (no trend)",     lambda r: (v := to_float(r['adx14_h1'])) is not None and v <= 20)
cohort("rvol_5bar > 1.5 (vol spike)", lambda r: (v := to_float(r['rvol_5bar'])) is not None and v > 1.5)
cohort("rvol_5bar < 0.8 (dead bar)",   lambda r: (v := to_float(r['rvol_5bar'])) is not None and v < 0.8)
cohort("ADR_used > 1.2 (range exhausted)", lambda r: (v := to_float(r['adr_consumed'])) is not None and v > 1.2)
cohort("ADR_used < 0.7 (room to run)", lambda r: (v := to_float(r['adr_consumed'])) is not None and v < 0.7)
cohort("ret_30m_aligned > +5p",     lambda r: (v := to_float(r['ret_30m_aligned'])) is not None and v > 5)
cohort("ret_30m_aligned < -5p",     lambda r: (v := to_float(r['ret_30m_aligned'])) is not None and v < -5)
