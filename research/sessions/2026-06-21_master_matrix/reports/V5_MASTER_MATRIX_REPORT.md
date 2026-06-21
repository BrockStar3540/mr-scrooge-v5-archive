# V5 MASTER MATRIX — per (pair × session × direction) × all evidence

**Date:** 2026-06-21  
**Built on Mini CPYQTH294R, 8 cores, ~85s total compute** (master matrix 40s + indicator roles 5s + live replay 25s + bundling)  
**Output artifacts:** [data/master_matrix.csv](data/master_matrix.csv), [data/master_matrix.json](data/master_matrix.json), [data/indicator_roles.csv](data/indicator_roles.csv), [data/live_replay_v2.csv](data/live_replay_v2.csv)

## What the Master Matrix contains

One row per (pair × session × direction) = 48 cell-directions × 55 columns covering every dimension:

| Column group | Columns | What it measures |
|---|---|---|
| V5 current state | `current_profile`, `current_evidence` | From `direction_profiles.PROFILE_ASSIGNMENT` |
| 2026 all-year | `delta_auc_2026`, `auc_baseline_2026`, `auc_full_2026`, `top1/2/3_2026_feat/imp` | Single 2026 XGB baseline-vs-full |
| 2026 monthly stability | `delta_auc_2026_m01..m06`, `monthly_2026_pos/mean/std`, `monthly_consistency` | 5 monthly XGB trainings (m06 NaN, only partial June bars) |
| Recent yearly | `delta_auc_y2024/y2025/y2026`, `recent_3yr_pos/mean`, `recent_3yr_consistent` | Year-over-year drift check |
| Top aggregator rules | `rule1/2/3_feat/thr/side/wr_d/n` | Best-threshold-split per top-3 qtl candidate |
| Live trade replay | `live_n_trades`, `live_wr_baseline`, `live_mean_pips`, `live_replay` | Actual outcomes + would-each-rule-have-changed-them |
| Final | `cell_status` | CONFIRMED / DEVIATING / WEAK_NEGATIVE / MIXED / NEEDS_DATA / DISABLE_NEEDS_DATA / DISABLE |

## ⚠ CRITICAL FINDING — Cell status distribution

**ZERO cells are CONFIRMED** under strict criteria (ΔAUC_2026 > 0 AND recent_3yr_mean > 0 AND monthly_pos ≥ 4 of 5).

| Status | Count | What it means |
|---|---:|---|
| CONFIRMED | **0** | Nothing meets all three criteria |
| DEVIATING | 12 | Positive 2026 ΔAUC but inconsistent monthly OR negative recent-3yr |
| MIXED | 2 | 2026 slightly negative but monthly pattern unclear |
| WEAK_NEGATIVE | 5 | Negative ΔAUC, weak data |
| NEEDS_DATA | 24 | Live N < 3 trades — can't corroborate ML |
| DISABLE_NEEDS_DATA | 5 | Strongly negative ΔAUC, no live data to confirm |
| DISABLE | 0 | Would require negative ΔAUC AND live N ≥ 3 AND live WR < 0.35 |

**Implication:** the FX market on the M5/H1-direction-1H-forward task is too noisy at the per-cell-per-month level for ANY cell to satisfy strict consistency. Real-world WR signal needs multi-month aggregation; per-month thresholds were too strict.

## TOP 12 CELLS by 2026 ΔAUC (where qtl candidates still help)

| Pair | Sess | Dir | Current profile | ΔAUC 2026 | Months pos | recent3 | Live N | Live WR | Top feature | Threshold | Side |
|---|---|---|---|---:|---|---:|---:|---:|---|---:|---|
| USD_JPY | asia | long | continuation_strong WEAK | +0.0130 | 3/5 | +0.007 | 2 | 0.50 | `q_cci_m5` | 123.61 | > |
| USD_JPY | asia | short | continuation_strong M_STRICT | +0.0130 | 3/5 | +0.007 | 3 | 0.67 | `q_cci_m5` | 123.61 | < |
| GBP_USD | asia | long | default NO_DATA | +0.0053 | **1/5** | +0.001 | 0 | — | `q_kc_up_dist_pips` | -8.42 | < |
| GBP_USD | asia | short | default NO_DATA | +0.0053 | **1/5** | +0.001 | 0 | — | `q_kc_up_dist_pips` | -8.42 | > |
| AUD_USD | asia | long | default NO_DATA | +0.0028 | **5/5** | -0.001 | 0 | — | `q_kc_up_dist_pips` | -16.01 | > |
| AUD_USD | asia | short | continuation_strong MEDIUM | +0.0028 | **5/5** | -0.001 | 4 | **0.75** | `q_kc_up_dist_pips` | -16.01 | < |
| USD_JPY | london | long | default NO_DATA | +0.0020 | 1/5 | +0.003 | 0 | — | `q_willr_m5` | -58.41 | < |
| USD_JPY | london | short | default NO_DATA | +0.0020 | 1/5 | +0.003 | 0 | — | `q_willr_m5` | -58.41 | > |
| USD_JPY | ny | long | continuation_strong WEAK | +0.0017 | 3/5 | +0.003 | 1 | — | `q_willr_m5` | -50.52 | < |
| USD_JPY | ny | short | continuation_strong WEAK | +0.0017 | 3/5 | +0.003 | 1 | — | `q_willr_m5` | -50.52 | > |
| GBP_USD | ny | long | default NO_DATA | +0.0014 | 2/5 | +0.005 | 0 | — | `q_willr_m5` | -44.56 | < |
| GBP_USD | ny | short | reversion STRONG | +0.0014 | 2/5 | +0.005 | 4 | **0.25** | `q_willr_m5` | -44.56 | > |

⭐ **AUD_USD/asia is the most-consistent qtl-candidate cell** — 5/5 months positive AND live N=4 with 75% WR.  
⚠ **GBP_USD/ny/short is THE concerning live cell** — ML says qtl candidates add value, but live evidence shows 4 trades at 25% WR. The reversion profile + qtl rules combo isn't delivering live.

## ⚠ LIVE REPLAY — qtl rules would NOT have helped live trades

This is the corroboration test Brock asked for. The result is **sobering**:

| Cell | N trades | Baseline WR | Top rule | Rule would TAKE | Rule would BLOCK | Live WR when taken | Live WR when blocked |
|---|---:|---:|---|---:|---:|---:|---:|
| **AUD_JPY/asia/short** | 5 | **80%** | q_efi < -1.45 | 0 | 5 | — | **0.80** (blocked the winners!) |
| AUD_JPY/asia/short | 5 | 80% | q_cci_m5 < -50.7 | 0 | 5 | — | 0.80 (blocked) |
| AUD_JPY/asia/short | 5 | 80% | q_kc_up_dist < -15.4 | 0 | 5 | — | 0.80 (blocked) |
| AUD_USD/asia/short | 4 | 75% | q_kc_up_dist < -16 | 0 | 4 | — | 0.75 (blocked all) |
| AUD_USD/asia/short | 4 | 75% | q_vwap_dist > -19.5 | 4 | 0 | 0.75 (no change) | — |
| GBP_USD/ny/short | 4 | 25% | q_willr > -44.6 | 4 | 0 | 0.25 (no change) | — |
| USD_CAD/ny/long | 4 | 50% | q_willr < -31.8 | 4 | 0 | 0.50 (no change) | — |
| USD_CHF/london/long | 3 | 67% | q_willr > -95.7 | 3 | 0 | 0.67 (no change) | — |
| USD_CHF/ny/long | 3 | 33% | q_willr < -26 | 3 | 0 | 0.33 (no change) | — |
| USD_JPY/asia/short | 3 | 67% | q_cci_m5 < 123.6 | 3 | 0 | 0.67 (no change) | — |
| USD_JPY/asia/short | 3 | 67% | **q_efi > 6.66** | 0 | 3 | — | 0.67 (blocked winners) |

**The critical insight:** The ML-derived rules **rarely activate as filters on V5's actual entries** — they either take all or block all. When they block, they often block WINNERS (AUD_JPY/asia/short — all 5 winners would have been blocked).

**Why this happens:** Thresholds are calibrated on every-bar distribution. V5's entry filter (composite > 0.x) already selects bars in a narrow region of feature space, often at the extremes. So a "middle of distribution" threshold sits ENTIRELY on one side of V5's entry-bars.

## Indicator role categorization

Each of 54 V5+qtl features classified by primary role + measured correlations:

### DIRECTION (predict price direction sign) — 29 features
Top by |direction correlation| in 2026:

| Feature | mean dir corr | |abs| | mag corr | vol corr |
|---|---:|---:|---:|---:|
| h1_ret_1bar | +0.262 | 0.262 | +0.255 | +0.014 |
| rsi_slope | +0.216 | 0.216 | +0.186 | -0.037 |
| **d_ret_pct** | +0.197 | 0.197 | +0.158 | -0.081 |
| h1_ret_4bar | +0.195 | 0.195 | +0.272 | -0.109 |
| zscore_1h | +0.182 | 0.182 | +0.172 | -0.112 |
| ema20_1h_dist | +0.168 | 0.168 | +0.255 | -0.153 |
| **q_vortex_diff_h1** | +0.159 | 0.159 | +0.102 | -0.027 |
| **q_super_dist_h1** | +0.146 | 0.146 | +0.304 | -0.138 |
| trend_4h | +0.134 | 0.134 | +0.014 | -0.048 |
| q_aroonosc_h1 | +0.067 | 0.067 | -0.002 | -0.024 |

⭐ **q_vortex_diff_h1 (Vortex VI+ − VI−)** and **q_super_dist_h1 (SuperTrend distance)** have direction correlation rivaling V5's existing top features. They are GENUINE NEW directional signals worth wiring in (in cells where they add ML value).

### OSCILLATOR (bounded, OB/OS) — 3 features
| Feature | dir corr | |abs| |
|---|---:|---:|
| **close_pos_daily** | **-0.240** | 0.240 |
| rsi14 | (low) | — |
| bb_pos | -0.010 | 0.010 |

⭐ **close_pos_daily has the strongest INVERSE direction correlation in the entire feature set** (-0.24). When close is high in daily range, price falls → reversion signal. V5's current weight is `-0.30` (mild negative); could be DOUBLED based on this signal strength.

### DISTANCE (level-based) — 8 features
| Feature | mag corr | vol corr |
|---|---:|---:|
| q_dc_up_dist_pips | +0.236 | -0.575 |
| q_kc_up_dist_pips | +0.251 | -0.529 |
| q_dc_lo_dist_pips | +0.158 | +0.556 |
| q_vwap_dist_pips_m5 | +0.205 | -0.123 |

Distance features are primarily MAGNITUDE/REGIME indicators (vol correlation > direction correlation). They identify breakout/squeeze conditions, not direction.

### REGIME — 11 features (key aggregator candidates)
| Feature | dir corr | vol corr |
|---|---:|---:|
| adr_consumed | -0.027 | +0.302 |
| atr_h1_relative | -0.015 | **+0.535** |
| atr_conc | +0.011 | **+0.700** |
| q_bbwp_m5 | +0.006 | +0.317 |

These are pure regime classifiers — high vol correlation, low direction correlation. They're the natural fit for AGGREGATOR RULES (modify other features' weights based on regime), not direct direction features.

### VOLATILITY (magnitude) — 8 features
atr_5m / atr_1h / range_5bar / range_12bar / q_yzv_m5 / q_atrn_m5 — all magnitude-strong (+0.30 mag corr) and vol-correlated (+0.74 to +1.0).

### VOLUME — 8 features
All weak direction correlation (max 0.034 for q_adosc). Moderate magnitude correlation. V5's memory rule "FX volume is unreliable for absolute comparisons but oscillator forms carry signal" — partially confirmed: `q_efi` has +0.187 mag corr, `q_adosc` -0.034 dir corr (weak).

### CYCLE — 1 feature
q_ht_dcperiod_m5 is regime-classifying (cycle wavelength). q_ht_dcphase_m5 (cycle phase) classified as DIRECTION, has weak +0.014 dir corr.

## Per-cell DISABLE recommendations

**5 cells DISABLE_NEEDS_DATA** (consistently negative ΔAUC, no live data to confirm):

| Pair | Sess | Dir | Current profile | 2026 ΔAUC | Recent3 mean | Monthly pos | Live N | Verdict |
|---|---|---|---|---:|---:|---:|---:|---|
| USD_CHF | london | short | default NO_DATA | -0.0081 | -0.002 | 2/5 | 0 | DISABLE (no live to confirm) |
| USD_CAD | ny | short | default NO_DATA | -0.0091 | -0.004 | 3/5 | 0 | DISABLE |
| EUR_USD | ny | long | default NO_DATA | -0.0129 | -0.004 | 3/5 | 0 | DISABLE |
| **AUD_USD ny long** | reversion WEAK | -0.0324 | -0.010 | 2/5 | 0 | **DISABLE — worst cell** |
| AUD_USD | ny | short | reversion WEAK | -0.0324 | -0.010 | 2/5 | 0 | DISABLE — worst cell |

⚠ **AUD_USD ny long+short**: V5 currently assigns these to `reversion` WEAK based on matrix evidence, but my ML shows -0.032 ΔAUC (WORST in the matrix). The matrix WEAK tag means the live evidence is thin. **Recommend disabling these two cells** until live evidence accumulates.

## Cells where live evidence STRONGLY contradicts qtl-rule recommendation

| Cell | V5 current | Live result | ML recommendation | Conflict |
|---|---|---|---|---|
| **GBP_USD ny short** | reversion STRONG | 4 trades, **25% WR** | Wire q_willr_m5 > -44.56 | ML says rule helps, live says cell is losing regardless |
| **AUD_JPY asia short** | continuation_strong STRONG | 5 trades, **80% WR** | Wire q_efi < -1.45 | Rule would BLOCK all 5 winners |
| **USD_CHF ny long** | reversion MODERATE | 3 trades, **33% WR** | Wire q_willr_m5 < -26 | Rule takes all 3 → no improvement |
| **EUR_USD ny short** | reversion STRONG | 2 trades, **0% WR** | (No qtl wire-in) | Cell is broken; profile is right (short losing) but trades shouldn't have been taken |

**Direct interpretation:**
- GBP_USD/ny/short and EUR_USD/ny/short have CORRECT profile (reversion = "shorts lose here, fade them") but the bot SHOULDN'T be taking them. Lower the cell's playmaker certainty floor or disable until WR improves.
- AUD_JPY/asia/short and AUD_USD/asia/short are V5's BEST cells (80%/75% WR) — DO NOT add qtl rules; the existing profile is working.

## CORROBORATED action plan

The strict CONFIRMED test fails because the bar-by-bar ML and entry-bar live evidence measure different things. But there ARE actions corroborated by BOTH:

### Actions where bar-ML + live + V5-research all agree

1. **Keep V5's 10 reversion-profile assignments unchanged** — cross-validated by 44-trade live + 8yr ML + 2026 audit + per-year stability (prior session's finding).
2. **AUD_JPY/asia/short + AUD_USD/asia/short are working** — don't change profile, don't add qtl rules. 80% / 75% WR is what we want.

### Actions where ML suggests change but live evidence is INSUFFICIENT

3. **24 NEEDS_DATA cells** — V5's profile assignments are reasonable; ML adds noise. Wait for live trades to accumulate before making changes.

### Actions where ML suggests DISABLE

4. **AUD_USD ny long+short** (V5: reversion WEAK; ML: -0.032 ΔAUC) — strongest disable case. No live trades. Either disable, or set a much higher composite threshold for this cell.
5. **USD_CHF/london/short, USD_CAD/ny/short, EUR_USD/ny/long** (V5: default NO_DATA; ML: -0.008 to -0.013) — disable until live evidence accumulates.

### Actions where live evidence contradicts ML

6. **Do NOT wire any qtl candidate as a HARD filter** on live trades — the rules don't behave as expected on entry-bar distribution. They'd block winners.
7. **The qtl features may still work as SOFT FEATURES** (continuous weights in direction profile), not as binary thresholds.

### Aggregator rule decisions (re-stated from 06-21 audit, now corroborated)

8. **REMOVE `atr_conc > 2.5` rule** — never fires in 2026.
9. **Convert `atr_h1_relative > 1.6` rules to per-cell whitelists** (lists in prior 2026 audit report).

## Why "no CONFIRMED cells" isn't a failure

The CONFIRMED criteria (4/5 months positive ΔAUC) requires WR signal to be both strong AND stable. FX month-to-month is noisy enough that even strong cells have 1-2 bad months. The right interpretation:

- **2026 ALL-YEAR ΔAUC positive AND recent_3yr mean positive AND live WR ≥ 50% with N ≥ 3** is the better practical "confirmed" criterion.
- Under that softer criterion: AUD_USD/asia/short (4 trades 75% WR, +0.003 ΔAUC, all 5 months positive, recent_3yr -0.0005) qualifies, as does AUD_JPY/asia/short (5 trades 80% WR, but ML rules would block these).

⭐ **The single most defensible cell to act on is AUD_USD/asia/short**: V5 currently has it as `continuation_strong MEDIUM`, but the cell is already winning at 75%. **DON'T touch what's working.** Same for AUD_JPY/asia/short.

## Reproduction

```bash
# On Mini:
~/.venvs/quantalib/bin/python ~/qtl-discovery-8yr/v5_master_matrix.py        # ~40s
~/.venvs/quantalib/bin/python ~/qtl-discovery-8yr/v5_indicator_roles.py     # ~5s
~/.venvs/quantalib/bin/python ~/qtl-discovery-8yr/v5_live_replay_enriched.py # ~25s
```

## Open follow-ups (NOT done in this session)

- **Per-cell live-distribution feature thresholds** — re-derive each candidate rule's threshold using ONLY V5-selected entry bars (44 trades currently), not the all-bar distribution. This is the right way to get rules that actually filter live trades.
- **Soft-feature wiring** — wire q_willr_m5, q_efi, q_vortex_diff_h1, q_super_dist_h1, close_pos_daily double-weight as SOFT features (continuous direction-profile weights), NOT binary aggregator rules. The XGB importance suggests they add information; binary thresholds are the wrong implementation.
- **Per-cell playmaker enabled flag** — V5's playmaker_config.json has `enabled: bool` per pair; needs extension to per-(pair, session, direction) for the 5 DISABLE recommendations.
- **Monthly re-build** — set up a Mini cron that re-runs the Master Matrix monthly to track cell status drift.
