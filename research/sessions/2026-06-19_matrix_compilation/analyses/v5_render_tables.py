#!/usr/bin/env python3
"""Print the v5_full_matrix.csv as two readable tables + per-feature correlations."""
import csv
from pathlib import Path
from statistics import correlation as pearson


def f(v, w=6, p=2, sign=False):
    if v == "" or v is None:
        return " " * w
    try:
        v = float(v)
    except Exception:
        return str(v).rjust(w)
    fmt = f"{{:>+{w}.{p}f}}" if sign else f"{{:>{w}.{p}f}}"
    return fmt.format(v)


def s(v, w=8):
    return str(v).rjust(w) if v else " " * w


def main():
    rows = list(csv.DictReader(Path("/tmp/v5_full_matrix.csv").open()))

    # Sort by tid asc
    rows.sort(key=lambda r: int(r["tid"]))

    # === View A: Entry signals + outcome ===
    print("=" * 130)
    print("VIEW A — entry signals + outcome   (n=44)")
    print("=" * 130)
    hdr = f"{'tid':<5}{'pair':<8}{'sess':<7}{'dir':<6}{'compos':>8}{'d_cert':>7}{'m_cert':>7}{'dir_sc':>8}{'h1_aln':>8}{'peak':>7}{'outcome':>9}"
    print(hdr)
    print("-" * 130)
    for r in rows:
        tag = ""
        try:
            peak = float(r["peak_pips"])
            outcome = float(r["exit_net"])
            if peak < 4.5 and outcome < -10:
                tag = "  NO-MOM"
            elif outcome > 5:
                tag = "  W"
            elif outcome < -10:
                tag = "  L"
        except Exception:
            pass
        print(f"{r['tid']:<5}{r['pair']:<8}{r['session']:<7}{r['dir']:<6}"
              f"{f(r['composite'],8,3,True)}{f(r['d_cert'],7,3)}{f(r['m_cert'],7,3)}"
              f"{f(r['raw_dir'],8,3,True)}{f(r['h1_ret_aligned'],8,2,True)}"
              f"{f(r['peak_pips'],7,2)}{f(r['exit_net'],9,2,True)}{tag}")

    # === View B: Aggregators from the matrix work ===
    print()
    print("=" * 130)
    print("VIEW B — matrix aggregators at entry")
    print("=" * 130)
    hdr = f"{'tid':<5}{'pair':<8}{'sess':<7}{'atr_5m':>7}{'atr_1h':>7}{'atr_d':>7}{'atr_conc':>9}{'h1_rel':>8}{'wall':>6}{'tr_4h':>8}{'htf20':>7}{'htf60':>7}{'peak':>7}{'out':>7}"
    print(hdr)
    print("-" * 130)
    for r in rows:
        print(f"{r['tid']:<5}{r['pair']:<8}{r['session']:<7}"
              f"{f(r['atr_5m'],7,2)}{f(r['atr_1h'],7,2)}{f(r['atr_d'],7,1)}"
              f"{f(r['atr_conc'],9,2)}{f(r['atr_h1_relative'],8,2)}"
              f"{f(r['wall_frac'],6,2)}{f(r['trend_4h_pips'],8,2,True)}"
              f"{f(r['htf_pct_20'],7,2)}{f(r['htf_pct_60'],7,2)}"
              f"{f(r['peak_pips'],7,2)}{f(r['exit_net'],7,1,True)}")

    # === Correlation block — aggregators vs peak_pips and vs exit_net ===
    def fcol(name):
        return [float(r[name]) for r in rows if r[name] not in ("", None) and r[name] != "None"]
    def pair_lists(name, tgt):
        xs, ys = [], []
        for r in rows:
            if r[name] in ("", None, "None") or r[tgt] in ("", None, "None"):
                continue
            try:
                xs.append(float(r[name])); ys.append(float(r[tgt]))
            except Exception:
                pass
        return xs, ys

    print()
    print("=" * 130)
    print("AGGREGATOR CORRELATIONS (Pearson)")
    print("=" * 130)
    feats = ["atr_5m", "atr_1h", "atr_d", "atr_conc", "atr_h1_relative", "wall_frac",
             "trend_4h_pips", "htf_pct_20", "htf_pct_60",
             "raw_dir", "d_cert", "m_cert", "h1_ret_aligned"]
    print(f"{'feature':<22}{'vs peak_pips':>16}{'vs exit_net':>16}{'sign_match%':>14}")
    print("-" * 70)
    for f_ in feats:
        xs_p, ys_p = pair_lists(f_, "peak_pips")
        xs_e, ys_e = pair_lists(f_, "exit_net")
        pp = f"{pearson(xs_p, ys_p):+.3f}" if len(xs_p) > 2 else "—"
        pe = f"{pearson(xs_e, ys_e):+.3f}" if len(xs_e) > 2 else "—"
        # Sign match: does sign(feature) predict sign(exit_net)?
        sm = "—"
        if xs_e:
            match = sum(1 for x, y in zip(xs_e, ys_e) if (x > 0) == (y > 0)) / len(xs_e)
            sm = f"{match:.1%}"
        print(f"{f_:<22}{pp:>16}{pe:>16}{sm:>14}")


if __name__ == "__main__":
    main()
