# 2026-06-20 — QuanTAlib 8yr per-cell discovery sweep

**Author:** claude-code/MBP, session 2026-06-20  
**Builds on:** [2026-06-20_qtl_indicator_discovery](../2026-06-20_qtl_indicator_discovery/) (44-trade pilot)  
**Trigger:** Brock asked for the proper test — 8 years of M5 ticks, per (pair × session × direction), ML-driven, ALL 8/10 Mini cores. The 44-trade pilot was too small-N to be definitive.

## What's in this folder

| File | Purpose |
|---|---|
| `reports/QTL_8YR_DISCOVERY_REPORT.md` | Full report: ΔAUC per cell, feature ranking, aggregator rule candidates, recommendations for V5 modules |
| `analyses/v5_qtl_8yr_features.py` | Feature computation pipeline (parallel, 8 cores). 16.5s wall time for 8 pairs × 550K bars × 84 features. Device serial check + V5 baseline replica + 32 qtl candidates + 1H forward label. |
| `analyses/v5_qtl_8yr_ml.py` | Per-cell XGB eval (parallel, 8 cores). 28.5s wall time for 24 cells × 2 trainings. Walk-forward 70/30 split, gain-based importance, best-threshold-split per top candidate. |
| `data/per_cell_importance.csv` | 32 qtl features × 24 cells matrix of gain-based importance |
| `data/aggregator_rule_candidates.csv` | Top-5 per cell × 22 cells = 110 candidate aggregator rules with threshold + WR delta |
| `data/per_cell_results.json` | Full JSON: AUC baseline/full, ΔAUC, per-cell qtl importance dict, per-direction WR |

The `data/v5_qtl_*_features.parquet` per-pair files (~80MB total) and the `data/v5_qtl_prefetch_bundle.json` from the 44-trade pilot live on Mini at `~/qtl-discovery-8yr/features/` and `~/qtl-discovery/` respectively (gitignored — too large for the repo; reproducible via the scripts).

## Headlines

1. **24/24 cells improve** when V5 baseline gets qtl candidates added. ΔAUC range +0.0026 to +0.0065, mean +0.0052. Zero regressions.

2. **Williams %R (M5) is the dominant new feature** — top-3 importance in **24/24 cells**, mean gain importance 0.052 (~3× the next feature). V5 has neither Williams %R nor any Stoch family member. **This is the single highest-confidence change V5 should make.**

3. **Aroon Oscillator H1 with threshold ±3.57 is the dominant aggregator-rule candidate** — appears in top-5 of 22/24 cells with 6.5-10.9pp WR delta per cell. Threshold magnitude `3.57` is consistent; the SIGN flips per cell (16 cells use `>+3.57`, 6 use `<-3.57`). This per-cell asymmetry is exactly what `direction_v2`'s per-(pair × session × direction) profile architecture is designed for.

4. **The 44-trade matrix winners didn't replicate.** `q_kurtosis_m5` (Δ +40.9pp on matrix) → 8yr importance #21 (0.005). `q_bbwp_m5` (Δ +36.2pp) → 8yr importance #20. **This is exactly why we did the 8yr validation** — small-N findings on already-filtered V5 trades don't reliably extrapolate. Brock's "do it properly with the 8yr corpus" call was the right one.

5. **Donchian channel distances, Elder's Force Index, Keltner upper distance, VWAP distance** are second-tier wins — each top-3 in 4-7 cells with meaningful importance.

## Recommended V5 changes (in priority order)

| Priority | Change | File(s) | Expected effect |
|---|---|---|---|
| 1 (highest confidence) | Add `willr_m5` to MarketView + every direction profile | `modules/signals/base.py`, `core/feed/oanda.py`, `direction_profiles.py` | +~0.5pp AUC in every cell; negligible risk |
| 2 (high payoff) | Wire Aroon ±3.57 aggregator rule per cell | `direction_profiles.py` (new lookup table + rule) | ~3-5pp WR lift when rule active (~35-45% of bars) |
| 3 (orthogonal structure) | Add `dc_up_dist_pips`, `dc_lo_dist_pips`, `kc_up_dist_pips`, `vwap_dist_pips_m5`, `efi` | `base.py` + feed + profiles | each adds 0.01-0.02 marginal importance |

See `reports/QTL_8YR_DISCOVERY_REPORT.md` for code snippets, full per-cell ΔAUC table, and the AROON_THRESHOLDS lookup table (all 22 cell-direction sign assignments).

## Sample-size + methodology

- 4.4M M5 bars (7.5 years × 8 pairs × 553K avg)
- Per cell n = 30K-100K bars after dropping NaN warmup + zero-label bars
- Chronological 70/30 split — genuine OOS, not random shuffle
- Label = sign(close[t+12] - close[t]) = 1H forward return direction
- V5 baseline features (24) computed identically to live `core/feed/oanda.py` (verified bit-exact on prior validation session)
- Trained on EVERY bar, not just V5's selected entries — no selection bias (unlike the 44-trade pilot)

## Compute

| Phase | Time | Cores |
|---|---|---|
| Feature pipeline (84 features × 4.4M bars) | 16.5s | 8 |
| ML eval (24 cells × 2 trainings) | 28.5s | 8 |
| **Total wall** | **45 s** | — |

Confirmed on Mini CPYQTH294R (M4, 10-core, 16GB). `cat ~/.device_id` checked at script entry; refused to run if not on Mini.

## Reproduction

```bash
# On Mini (script checks serial CPYQTH294R first):
~/.venvs/quantalib/bin/python ~/qtl-discovery-8yr/v5_qtl_8yr_features.py   # 16.5s
~/.venvs/quantalib/bin/python ~/qtl-discovery-8yr/v5_qtl_8yr_ml.py         # 28.5s
# Outputs land in ~/qtl-discovery-8yr/{features,ml}/
```

## Open follow-ups (NOT done in this session)

- **Implement priority #1** — wire `willr_m5` into V5 live feed + direction_v2 profiles
- **Implement priority #2** — add Aroon aggregator rule with per-cell threshold sign lookup
- **Per-direction split analysis** — currently the ML trains one classifier per cell on direction-agnostic label. A second-pass analysis could split features by predicted-UP vs predicted-DOWN subsets to give per-direction profile-tuning insights
- **Monthly re-run** — V5's live trader drifts; rerun this sweep monthly to track whether the feature signal is shifting (especially after live profile changes)
- **2-feature interaction sweep** — for top-5 candidates, test pairwise interactions (e.g., `willr_m5 < -80 AND aroonosc_h1 > +3.57`) as compound aggregator rules
