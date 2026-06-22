# inverted_live_cells live test (2026-06-22 onward)

**Date:** 2026-06-22
**Trigger:** Brock observed live signals reversed on AUD_JPY/asia + USD_JPY/asia. Extended to test the inversion thesis at scale across 9 cells (4 pairs).
**Cells under test (inverted_live_cells):**
- AUD_JPY/asia, USD_JPY/asia
- EUR_USD/london, EUR_USD/ny
- GBP_USD/london, GBP_USD/ny
- USD_CHF/london, USD_CHF/ny
- USD_CAD/ny — historical STAR (+6.61p n=7); flipping it is the cleanest disconfirmation lever.

**Mechanism (commit 200629f):** `playmaker.pick_best()` flips the winner ticket's direction when `(pair, session) ∈ inverted_live_cells`. `engine.py` SIGNAL log appends `INVERTED_LIVE signal_dir=X trade_dir=Y` for traceability.

## Two competing theses
1. **Live signal reversed** — v2/v3 modules emit the wrong direction systemically. If true, inversion wins broadly, including on USD_CAD/ny/long.
2. **Historical broker forward predicts in-sample but not next-bar live** — the JPY/asia reversal was specific, not systemic. If true, this test bleeds, esp. on USD_CAD/ny/long.

## Reader script
[`analyses/v5_inverted_live_report.py`](analyses/v5_inverted_live_report.py) — pulls SIGNAL→ENTERED→EXIT triples from the V5 journal, reports per-cell n, mean pip, win rate, and the baseline (= negative of realized, valid for the comparison because market orders + symmetric SL/ratchet make a flipped trade exactly mirror the original).

```bash
# default: since first inverted_live commit (2026-06-22 04:14)
python3 analyses/v5_inverted_live_report.py
# narrow to one pair
python3 analyses/v5_inverted_live_report.py --pair USD_CAD
# custom window
python3 analyses/v5_inverted_live_report.py --since "2026-06-23 00:00:00"
```

## Reporting cadence
After ~10 closed inverted-live trades, snapshot to `data/snapshot_<date>.txt` and judge. Headline outcome will be: does inversion net-positive across the 9 cells, or do specific cells (esp. USD_CAD/ny/long) show inversion is wrong for trend-style cells.
