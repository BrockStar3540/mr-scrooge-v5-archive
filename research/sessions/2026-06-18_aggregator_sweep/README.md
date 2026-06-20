# 2026-06-18 — Aggregator sweep on Mini

## What

Two XGBoost regressors per (pair × session) trained from scratch on 7.5yr OANDA M5 corpus. Sweep across 8 pairs × 3 sessions × 7 V3-candidate aggregator ablations.

- **Compute location**: Mac Mini `~/scrooge-aggregator-test/`
- **Data location**: `/Volumes/Alien Device/scrooge-research/v5_aggregator_test_2026-06-18/`
- **Why on the Mini**: heavy compute rule — EC2 is the live trader's 3.7GB box, this would have OOM'd it.

## Why

Validate which V3 aggregators actually contribute edge versus being noise:
- `trend_1h`, `trend_4h`
- `atr_conc`
- `htf_bias_20`, `htf_bias_60`
- `wall_frac`
- `ema50_atr_frac`

Earlier dm05-dm09 work (in `../../reference/`) suggested these were candidates but didn't pin down per-cell behavior at corpus scale.

## How

Smoke test pass on EUR_USD/london first (8.8s, dir_OOS=0.65, mom_OOS=0.55) confirmed pipeline. Full sweep then ran on 8 cores in background — 24 cells × ~9s/cell = ~4 minutes.

Two models per cell:
- **ML#1 direction** — XGBRegressor predicting `net_60m`
- **ML#2 momentum** — XGBRegressor predicting `|net_60m|`

For each model + each candidate aggregator, fit twice (with and without the aggregator) and measure feature_importance + permutation_importance + OOS Pearson delta.

## Findings

Synthesized in `docs/EDGE_REPORT.md` (committed). Top-level:

### Tier 1 (universal — confirmed at corpus scale)

- **`h1_ret_1bar`** — strongest direction predictor in every cell. Lab + cross-broker concur.
- **`atr_conc` Q4 magnitude penalty** — universal. High atr_conc → smaller pip_high. Kept as V5's chaos gate.
- **`atr_conc` direction amplifier** — bidirectional: penalizes pip_high but amplifies HTF direction signals when paired with htf_pct features.

### Tier 2 (cell-conditional)

- **`wall_frac`** — amplifies pip_high in 3 of 5 multi-trade cells (later live-confirmed in smoke v3).
- **`trend_4h`** — continuation in NY, reversion in asia (later live-confirmed in 44-trade matrix).
- **`htf_pct_20/60`** — strong in continuation_strong cells, near-zero in NY non-JPY.

### Tier 3 / not-edge

- **`ema50_atr_frac`** — independent signal but small contribution. Kept on the view but not boosted.

## Files in this session folder

- `analyses/` — the Python scripts that ran the sweep
- `logs/` — `.log` outputs from each phase (sweep, kept_recheck, redundant_recheck, monthly, test_b, dynamic, full_ml, hf_recipe, forexsb_h1, forexsb_perm, path_a)
- `data-pointers.md` — pointers to raw JSON outputs on Mini (too large to commit; ~9MB dynamic_weights.json + 1.8MB of per-cell JSONs)

## Outcome

This session's findings drove:

- V5 v1 dm_04 module calibration → `docs/signal-module-spec.md`
- `data/factor_sweep.json` with per-cell D1-D10 anchors
- The first `docs/EDGE_REPORT.md` writeup
- Matrix vault note `wiki/systems/note_scrooge_v5_findings_matrix_2026-06-18.md` — the rolling synthesis

Direct downstream:
- [2026-06-19 matrix_compilation](../2026-06-19_matrix_compilation/) — adapted these findings into 44-trade live correlations
- [2026-06-19 per_direction_extension](../2026-06-19_per_direction_extension/) — extended to (pair × session × direction)

## Reproducibility

To re-run the sweep:

```bash
ssh -i ~/.ssh/mac_mini_austin brock-mini-mac@[REDACTED-IP]   # from EC2
cd ~/scrooge-aggregator-test
python3 v5_aggregator_synth.py            # builds the synthesis matrix
python3 v5_aggregator_kept_recheck.py     # validates the kept candidates
python3 v5_aggregator_redundant_recheck.py # tests redundancy in remaining factors
python3 v5_aggregator_percell.py          # per-cell breakdown
```

The Mini was 8 cores allocated; bumping to all 10 would shave ~20% off wall-clock.

## Sample-size honesty

- Each cell's XGB model was trained on the full 7.5yr corpus (~555k bars per pair).
- OOS validation was walk-forward, expanding window, no leakage.
- Per-bar prediction errors aggregate over millions of bar-pair labels — N is not the limitation; the limitation is the matrix synthesis (24 cells across 8 pairs × 3 sessions).
- Live confirmation was deferred to the [2026-06-19 matrix_compilation](../2026-06-19_matrix_compilation/) and live smoke runs.
