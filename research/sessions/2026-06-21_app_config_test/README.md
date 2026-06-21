# 2026-06-21 — App-config edge test (RSI/EMA/StochRSI MTF)

**Author:** claude-code/MBP
**Trigger:** Brock asked whether the signal-app's multi-timeframe RSI(7)/EMA(5,20)/StochRSI(14,5,3) configurations actually improve 1H forecast accuracy, or are just visually persuasive. Provided a full test framework (8 configs, mechanical scan, signed forward pip, expectancy ranking).

## What

Tested 8 configs (RSI cross only → full MTF-aligned + EMA-state + StochRSI stack) against 8yr × 8 pairs, scanning every M5 bar mechanically (not app alerts). 910,406 signals. Measured signed forward pip at 15/30/60/90/120 min. Mid-price (pre-spread).

## Answer

**No edge. Visually persuasive only.** Every config: WR < 48%, expectancy −0.18 to −0.22 pips, profit factor < 1.0 — and that's *before* spread.

- The multi-timeframe alignment filters thin the sample 72% (260k→73k) without improving expectancy at all — they remove signals at random w.r.t. outcome.
- The signal slightly anti-predicts at all 5 horizons (RSI(7) M15 cross = lagging exhaustion marker).
- London is the only non-terrible session (flat); NY is actively destructive (−0.5).
- 5× more (config×pair×session) cells where the signal is reliably wrong than reliably right.

## Files

| File | Purpose |
|---|---|
| `reports/APP_CONFIG_TEST_REPORT.md` | Full report + Brock's table format + session/cell breakdowns |
| `analyses/v5_app_config_tester.py` | The 8-config mechanical scanner (2.5s on Mini) |
| `analyses/v5_app_horizons.py` | Multi-horizon + per-cell + fade-edge analysis |
| `data/per_config_summary.csv` | Per-config expectancy table |
| `data/per_config_session.csv` | Per-config × session |
| `data/per_config_pair.csv` | Per-config × pair |

`all_signals_raw.csv` (145MB, 910k signals) stays on Mini at `~/qtl-discovery-8yr/app_config_test/` — too large for the repo, reproducible via the script.

## Takeaway

Confirms the methodology lesson from the broker-validation session: a signal that looks right (on a chart or an app's confluence panel) ≠ a signal that predicts forward price. Only "scan every occurrence, measure the forward move" tells the truth. Don't wire app-confluence logic into V5's direction engine.
