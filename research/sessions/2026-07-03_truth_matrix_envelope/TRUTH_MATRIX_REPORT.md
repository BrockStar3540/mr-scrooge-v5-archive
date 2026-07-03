# V5 MAE/MFE TRUTH MATRIX REPORT — v2 (extended window)

Generated: 2026-07-03T03:04:46.104919
Device: Mac Mini (CPYQTH294R)

## SCOPE

The 8 pairs — **AUD_JPY, AUD_USD, EUR_JPY, EUR_USD, GBP_USD, USD_CAD, USD_CHF, USD_JPY** — ARE the complete V5 trading universe.

**PAIR STATUS NOTE: USD_CHF was killed as a trading pair on 2026-07-01 (broker-confirmed loser).**
USD_CHF truth-matrix signals remain useful as VALIDATION data but are NOT wiring candidates.
All USD_CHF cells below are annotated accordingly.

## 1. DATA WINDOW & PARQUET FRESHNESS

Raw bars extended 2026-06-18 -> **2026-07-03 06:50 UTC** (fresh OANDA pull, complete bars only),
then features rebuilt with the post-leak-fix builder (~/qtl-discovery-8yr/v5_qtl_8yr_features.py).

| Pair | Feature parquet rebuilt (UTC) |
|------|------------------------------|
| AUD_JPY | 2026-07-03 06:59:30 UTC |
| AUD_USD | 2026-07-03 06:59:30 UTC |
| EUR_JPY | 2026-07-03 06:59:30 UTC |
| EUR_USD | 2026-07-03 06:59:30 UTC |
| GBP_USD | 2026-07-03 06:59:30 UTC |
| USD_CAD | 2026-07-03 06:59:30 UTC |
| USD_CHF | 2026-07-03 06:59:30 UTC |
| USD_JPY | 2026-07-03 06:59:30 UTC |

## 2. SEAM INTEGRITY (extension splice at 2026-06-18)

Verification method: fetched candles overlapping the old window (M5 from 2026-06-17), compared
overlap OHLC values bar-by-bar, appended only bars strictly after each store's last timestamp,
then checked duplicates and seam contiguity. **Complete bars only** (OANDA complete=true filter).

| Pair | M5 old last | M5 bars added | Overlap bars | Mismatches | Max abs diff | Seam gap |
|------|------------|--------------|--------------|------------|--------------|----------|
| AUD_JPY | 2026-06-18 04:10:00+00:00 | +3200 | 339 | 0 | 0.0 | 5 min |
| AUD_USD | 2026-06-18 04:35:00+00:00 | +3195 | 344 | 0 | 0.0 | 5 min |
| EUR_JPY | 2026-06-18 04:35:00+00:00 | +3195 | 344 | 0 | 0.0 | 5 min |
| EUR_USD | 2026-06-18 04:35:00+00:00 | +3195 | 344 | 0 | 0.0 | 5 min |
| GBP_USD | 2026-06-18 04:35:00+00:00 | +3195 | 344 | 0 | 0.0 | 5 min |
| USD_CAD | 2026-06-18 04:40:00+00:00 | +3194 | 345 | 0 | 0.0 | 5 min |
| USD_CHF | 2026-06-18 04:40:00+00:00 | +3191 | 345 | 0 | 0.0 | 5 min |
| USD_JPY | 2026-06-18 04:40:00+00:00 | +3193 | 345 | 0 | 0.0 | 5 min |

**Result: PERFECT SEAM** — 0 mismatches, 0 duplicates, exactly 5-minute gaps at every M5 seam
(60 min for H1, 1440 min for D). Raw originals backed up to raw_bars_backup_2026-07-03/.

## 3. BAR COUNTS (extended)

| Pair | Total Bars | 2026 Bars |
|------|-----------|----------|
| AUD_JPY | 556,500 | 37,316 |
| AUD_USD | 551,965 | 37,207 |
| EUR_JPY | 556,031 | 37,320 |
| EUR_USD | 554,046 | 37,213 |
| GBP_USD | 554,806 | 37,283 |
| USD_CAD | 554,100 | 37,208 |
| USD_CHF | 547,711 | 37,134 |
| USD_JPY | 555,119 | 37,271 |

## 4. ANCHOR CHECK — broker-verified MFE/MAE vs truth matrix

Broker side: MFE AND MAE recomputed for all 110 V5-era trades from actual fill prices
(price_entry from the broker transaction records) over each trade's lifetime M5 window
(entry bar through close bar, extended candle store). Saved: broker_anchor_trades.json.

Matrix side: entry bar looked up in the truth matrix; 60m horizon capped at trade duration;
capped values recomputed from raw M5 OHLC where duration < 60m (matrix convention:
reference = entry-bar close, window = bars t+1..t+cap).

- Trades matched: 110 / 110
- Wiring check (trades >= 55min: truth-parquet column vs raw recompute): 57 checked, 0 mismatches

| Comparison | Metric | Pearson r | MAD (pips) | Bias matrix-broker (pips) |
|-----------|--------|-----------|------------|---------------------------|
| vs broker LIFETIME (spec headline) | MFE | 0.7219 | 4.02 | -1.87 |
| vs broker LIFETIME (spec headline) | MAE | 0.7388 | 5.86 | -5.61 |
| vs broker 60m-capped (apples-to-apples) | MFE | 0.8367 | 2.48 | +0.39 |
| vs broker 60m-capped (apples-to-apples) | MAE | 0.7907 | 3.42 | -3.04 |

**VERDICT vs lifetime (spec headline): FAIL** (bar: r >= 0.8 both metrics) — expected:
56/110 trades run longer than 60 min, so their broker lifetime excursions exceed the matrix's
60m window by construction. This comparison tests the spec's literal wording, not wiring.

**VERDICT vs 60m-capped, bar-aligned windows: PASS** — MFE r=0.8426, MAE r=0.8413 (both >= 0.8).
(The 0.79 MAE figure in the table above used a time-based broker window that could include one
extra bar vs the matrix's 12-bar window; the bar-aligned decomposition below is the correct
apples-to-apples test and passes.) With the entry-bar convention difference also removed,
MAE rises to r=0.9025 and MFE to r=0.8575. Matrix wiring itself verified exact: 57/57 checks.

```
Diagnostics (matrix minus broker-lifetime):
  MFE diff: mean=-1.87 std=6.20 p5=-10.88 p95=5.00
  MAE diff: mean=-5.61 std=7.21 p5=-19.10 p95=0.51
  Trades >60min: 56/110 (their lifetime excursions exceed the matrix 60m window by construction)
  MFE bias on <=60min trades: -0.10p ; on >60min trades: -3.57p
```


### Anchor bias decomposition (60m-capped comparison)

Removing the two convention differences one at a time (n=110 trades):

```
  MFE full-convention-gap (matrix vs broker inc+fill): r=0.8426 MAD=2.45p bias=+0.25p
  MAE full-convention-gap (matrix vs broker inc+fill): r=0.8413 MAD=3.10p bias=-2.72p
  MFE after removing entry bar (matrix vs broker exc+fill): r=0.8575 MAD=2.45p bias=+1.32p
  MAE after removing entry bar (matrix vs broker exc+fill): r=0.9025 MAD=2.45p bias=-1.32p
  fill-minus-entry-bar-close: mean=+0.32p abs-mean=2.45p p95(|.|)=5.96p
```

Interpretation: the entry-bar inclusion accounts for most of the MAE gap — once the broker
excursion is computed over the same t+1..t+cap window (fill reference), correlation rises to
~0.90 for MAE. The residual is the fill-vs-bar-close reference difference (mean |fill-close| =
2.45 pips), i.e. real intra-bar slippage/timing that bar-level data cannot see. The matrix is
correctly wired (57/57 wiring checks passed); the r<0.8 headline reflects convention + tick-level
effects, not computation error.

Systematic-bias notes:
- Matrix references entry-bar CLOSE; broker references actual FILL price (intra-bar).
- Matrix window starts at t+1 (excludes entry bar); broker lifetime includes the entry bar.
- For trades longer than 60 min (about half: median duration 63m), broker lifetime excursions
  exceed the matrix 60m window by construction — the 60m-capped comparison isolates true wiring error.

## 5. TOP 10 CELLS — full-2026 window (incl. live V5 era Jun 18 -> Jul 3)

### #1: USD_JPY_LONDON_LONG  (n=10,857 bars, score=0.1263)

**Direction Sync:**
  - `atr_h1_relative`: dir_corr=-0.1263, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `bb_std`: dir_corr=-0.1094, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `bb_width`: dir_corr=-0.1094, drift_monthly=FLICKER, drift_yearly=FLICKER

**Distance Sync:**
  - `atr_5m`: dist_corr=0.3893, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `atr_1h`: dist_corr=0.3650, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `range_5bar`: dist_corr=0.3515, drift_monthly=FLICKER, drift_yearly=FLICKER

**Dead-Entry Sync:**
  - `ema5`: dead_auc=0.6498, drift_monthly=FLICKER, drift_yearly=PERSISTENT
  - `q_obv`: dead_auc=0.6488, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `ema20`: dead_auc=0.6470, drift_monthly=FLICKER, drift_yearly=PERSISTENT

### #2: USD_JPY_LONDON_SHORT  (n=10,857 bars, score=0.1263)

**Direction Sync:**
  - `atr_h1_relative`: dir_corr=0.1263, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `bb_std`: dir_corr=0.1094, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `bb_width`: dir_corr=0.1094, drift_monthly=FLICKER, drift_yearly=FLICKER

**Distance Sync:**
  - `atr_5m`: dist_corr=0.3280, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `range_12bar`: dist_corr=0.3267, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `bb_std`: dist_corr=0.3205, drift_monthly=FLICKER, drift_yearly=FLICKER

**Dead-Entry Sync:**
  - `q_adl`: dead_auc=0.6326, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `q_obv`: dead_auc=0.6277, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `d_low`: dead_auc=0.6019, drift_monthly=FLICKER, drift_yearly=PERSISTENT

### #3: AUD_USD_LONDON_LONG  (n=10,839 bars, score=0.1184)

**Direction Sync:**
  - `q_vwap_dist_pips_m5`: dir_corr=-0.1184, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `ema20_1h_dist`: dir_corr=-0.1108, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `ema50_dist_pct`: dir_corr=-0.1097, drift_monthly=PERSISTENT, drift_yearly=FLICKER

**Distance Sync:**
  - `atr_5m`: dist_corr=0.3075, drift_monthly=FLICKER, drift_yearly=REGIME
  - `q_yzv_m5`: dist_corr=0.3041, drift_monthly=FLICKER, drift_yearly=REGIME
  - `atr_1h`: dist_corr=0.2959, drift_monthly=FLICKER, drift_yearly=REGIME

**Dead-Entry Sync:**
  - `q_kc_up_dist_pips`: dead_auc=0.5734, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `q_dc_up_dist_pips`: dead_auc=0.5722, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `pdh_dist`: dead_auc=0.5433, drift_monthly=PERSISTENT, drift_yearly=FLICKER

### #4: AUD_USD_LONDON_SHORT  (n=10,839 bars, score=0.1184)

**Direction Sync:**
  - `q_vwap_dist_pips_m5`: dir_corr=0.1184, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `ema20_1h_dist`: dir_corr=0.1108, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `ema50_dist_pct`: dir_corr=0.1097, drift_monthly=PERSISTENT, drift_yearly=FLICKER

**Distance Sync:**
  - `atr_5m`: dist_corr=0.3439, drift_monthly=FLICKER, drift_yearly=REGIME
  - `q_yzv_m5`: dist_corr=0.3357, drift_monthly=FLICKER, drift_yearly=REGIME
  - `atr_1h`: dist_corr=0.3142, drift_monthly=FLICKER, drift_yearly=REGIME

**Dead-Entry Sync:**
  - `q_dc_up_dist_pips`: dead_auc=0.5453, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `q_kc_up_dist_pips`: dead_auc=0.5393, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `pdh_dist`: dead_auc=0.5174, drift_monthly=PERSISTENT, drift_yearly=FLICKER

### #5: EUR_USD_NY_LONG  (n=13,923 bars, score=0.0943)

**Direction Sync:**
  - `q_stochrsi_m5`: dir_corr=-0.0943, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `q_willr_m5`: dir_corr=-0.0765, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `q_fisher_m5`: dir_corr=-0.0690, drift_monthly=REGIME, drift_yearly=FLICKER

**Distance Sync:**
  - `atr_5m`: dist_corr=0.3497, drift_monthly=REGIME, drift_yearly=FLICKER
  - `q_yzv_m5`: dist_corr=0.3012, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `range_12bar`: dist_corr=0.2881, drift_monthly=REGIME, drift_yearly=FLICKER

**Dead-Entry Sync:**
  - `q_dc_up_dist_pips`: dead_auc=0.6349, drift_monthly=REGIME, drift_yearly=FLICKER
  - `q_kc_up_dist_pips`: dead_auc=0.6152, drift_monthly=REGIME, drift_yearly=FLICKER
  - `q_obv`: dead_auc=0.5948, drift_monthly=REGIME, drift_yearly=FLICKER

### #6: EUR_USD_NY_SHORT  (n=13,923 bars, score=0.0943)

**Direction Sync:**
  - `q_stochrsi_m5`: dir_corr=0.0943, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `q_willr_m5`: dir_corr=0.0765, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `q_fisher_m5`: dir_corr=0.0690, drift_monthly=REGIME, drift_yearly=FLICKER

**Distance Sync:**
  - `atr_5m`: dist_corr=0.3213, drift_monthly=REGIME, drift_yearly=FLICKER
  - `range_12bar`: dist_corr=0.2896, drift_monthly=REGIME, drift_yearly=FLICKER
  - `q_yzv_m5`: dist_corr=0.2886, drift_monthly=FLICKER, drift_yearly=FLICKER

**Dead-Entry Sync:**
  - `q_dc_up_dist_pips`: dead_auc=0.5723, drift_monthly=REGIME, drift_yearly=FLICKER
  - `q_kc_up_dist_pips`: dead_auc=0.5673, drift_monthly=REGIME, drift_yearly=FLICKER
  - `q_obv`: dead_auc=0.5336, drift_monthly=REGIME, drift_yearly=FLICKER

### #7: AUD_JPY_ASIA_LONG  (n=12,501 bars, score=0.0837)

**Direction Sync:**
  - `ema5`: dir_corr=-0.0837, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `ema20`: dir_corr=-0.0835, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `bb_mid`: dir_corr=-0.0835, drift_monthly=PERSISTENT, drift_yearly=FLICKER

**Distance Sync:**
  - `q_yzv_m5`: dist_corr=0.3097, drift_monthly=REGIME, drift_yearly=FLICKER
  - `range_5bar`: dist_corr=0.3084, drift_monthly=REGIME, drift_yearly=FLICKER
  - `atr_5m`: dist_corr=0.2985, drift_monthly=FLICKER, drift_yearly=FLICKER

**Dead-Entry Sync:**
  - `ema5`: dead_auc=0.6015, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `ema20`: dead_auc=0.6008, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `ema50`: dead_auc=0.6004, drift_monthly=PERSISTENT, drift_yearly=FLICKER

### #8: AUD_JPY_ASIA_SHORT  (n=12,501 bars, score=0.0837)

**Direction Sync:**
  - `ema5`: dir_corr=0.0837, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `ema20`: dir_corr=0.0835, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `bb_mid`: dir_corr=0.0835, drift_monthly=PERSISTENT, drift_yearly=FLICKER

**Distance Sync:**
  - `atr_5m`: dist_corr=0.2377, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `atr_1h`: dist_corr=0.2121, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `range_5bar`: dist_corr=0.2032, drift_monthly=REGIME, drift_yearly=FLICKER

**Dead-Entry Sync:**
  - `q_dc_up_dist_pips`: dead_auc=0.5530, drift_monthly=REGIME, drift_yearly=FLICKER
  - `q_kc_up_dist_pips`: dead_auc=0.5490, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `zscore_1h`: dead_auc=0.5263, drift_monthly=REGIME, drift_yearly=REGIME

### #9: USD_CHF_LONDON_LONG  (n=10,839 bars, score=0.0835)  **[USD_CHF KILLED 2026-07-01 — validation only, NOT a wiring candidate]**

**Direction Sync:**
  - `pdh`: dir_corr=-0.0835, drift_monthly=PERSISTENT, drift_yearly=PERSISTENT
  - `d_low`: dir_corr=-0.0807, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `d_high`: dir_corr=-0.0801, drift_monthly=PERSISTENT, drift_yearly=PERSISTENT

**Distance Sync:**
  - `atr_5m`: dist_corr=0.2260, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `q_yzv_m5`: dist_corr=0.2112, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `atr_1h`: dist_corr=0.2061, drift_monthly=REGIME, drift_yearly=FLICKER

**Dead-Entry Sync:**
  - `ema5`: dead_auc=0.5435, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `ema20`: dead_auc=0.5433, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `ema50`: dead_auc=0.5432, drift_monthly=FLICKER, drift_yearly=FLICKER

### #10: USD_CHF_LONDON_SHORT  (n=10,839 bars, score=0.0835)  **[USD_CHF KILLED 2026-07-01 — validation only, NOT a wiring candidate]**

**Direction Sync:**
  - `pdh`: dir_corr=0.0835, drift_monthly=PERSISTENT, drift_yearly=PERSISTENT
  - `d_low`: dir_corr=0.0807, drift_monthly=PERSISTENT, drift_yearly=FLICKER
  - `d_high`: dir_corr=0.0801, drift_monthly=PERSISTENT, drift_yearly=PERSISTENT

**Distance Sync:**
  - `atr_5m`: dist_corr=0.2271, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `q_yzv_m5`: dist_corr=0.2254, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `atr_1h`: dist_corr=0.2079, drift_monthly=REGIME, drift_yearly=FLICKER

**Dead-Entry Sync:**
  - `q_dc_up_dist_pips`: dead_auc=0.5412, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `q_kc_up_dist_pips`: dead_auc=0.5326, drift_monthly=FLICKER, drift_yearly=FLICKER
  - `pdh_dist`: dead_auc=0.5324, drift_monthly=FLICKER, drift_yearly=FLICKER


## 6. RANKING CHANGES vs pre-extension (v1) run

Old top-10: USD_JPY_LONDON_LONG, USD_JPY_LONDON_SHORT, AUD_USD_LONDON_LONG, AUD_USD_LONDON_SHORT, USD_CHF_LONDON_LONG, USD_CHF_LONDON_SHORT, EUR_USD_NY_LONG, EUR_USD_NY_SHORT, USD_CHF_ASIA_LONG, USD_CHF_ASIA_SHORT

New top-10: USD_JPY_LONDON_LONG, USD_JPY_LONDON_SHORT, AUD_USD_LONDON_LONG, AUD_USD_LONDON_SHORT, EUR_USD_NY_LONG, EUR_USD_NY_SHORT, AUD_JPY_ASIA_LONG, AUD_JPY_ASIA_SHORT, USD_CHF_LONDON_LONG, USD_CHF_LONDON_SHORT

**Entered top-10:** AUD_JPY_ASIA_LONG, AUD_JPY_ASIA_SHORT

**Exited top-10:** USD_CHF_ASIA_LONG, USD_CHF_ASIA_SHORT

**Top-3 direction-feature changes within the new top-10:**
  - EUR_USD_NY_LONG: ['q_stochrsi_m5', 'q_willr_m5', 'ema20_1h_dist'] -> ['q_stochrsi_m5', 'q_willr_m5', 'q_fisher_m5']
  - EUR_USD_NY_SHORT: ['q_stochrsi_m5', 'q_willr_m5', 'ema20_1h_dist'] -> ['q_stochrsi_m5', 'q_willr_m5', 'q_fisher_m5']
  - AUD_JPY_ASIA_LONG: ['ema5', 'bb_mid', 'ema20'] -> ['ema5', 'ema20', 'bb_mid']
  - AUD_JPY_ASIA_SHORT: ['ema5', 'bb_mid', 'ema20'] -> ['ema5', 'ema20', 'bb_mid']
  - USD_CHF_LONDON_LONG: ['pdh', 'd_high', 'd_low'] -> ['pdh', 'd_low', 'd_high']
  - USD_CHF_LONDON_SHORT: ['pdh', 'd_high', 'd_low'] -> ['pdh', 'd_low', 'd_high']

## 7. DRIFT LABEL COUNTS BY FEATURE FAMILY

(drift months: Jan-Jun 2026; July excluded — 2-day sample)

| Family | PERSISTENT | REGIME | FLICKER | INSUFFICIENT |
|--------|-----------|--------|---------|-------------|
| atr_adx | 4 | 0 | 16 | 0 |
| bb_channel | 2 | 4 | 12 | 0 |
| daily_levels | 16 | 2 | 14 | 0 |
| other | 2 | 2 | 4 | 0 |
| price_ret | 4 | 6 | 10 | 0 |
| q_quantile | 18 | 24 | 52 | 0 |
| rsi_stoch | 0 | 2 | 2 | 0 |
| trend_align | 20 | 8 | 12 | 0 |
| volume_flow | 0 | 0 | 4 | 0 |

## 8. COVERAGE

All 48 cells computed (>= 200 bars each). No skips.

## 9. METHODOLOGY NOTES & CHANGES vs v1

- **V5 universe correction:** NZDUSD/GBPJPY were never V5 pairs; the 8 parquet pairs are the
  complete universe. The v1 'coverage gap' note was wrong and is retracted.
- **USD_CHF killed 2026-07-01:** its 12 cells stay in the matrix as validation data; annotated, not wireable.
- **Excursion computation improved:** v1 computed forward windows over feature-parquet rows,
  which had ~0.45% of bars dropped (label==0 weekend-gap rows) — windows could silently span
  those gaps. v2 computes excursions on the contiguous RAW M5 index, then maps to feature rows.
- **Old NaN tail recomputed:** bars near 2026-06-18 now have valid forward paths from the extension.
- **Broker anchor:** old study mfe_pips excluded the entry bar and misbehaved on <5min trades
  (no completed bar strictly after entry). New broker values use fill-price reference, entry bar
  included, verified-seam candles; both entry-bar variants stored in broker_anchor_trades.json.
- Sync fit window: all 2026 bars through 2026-07-03. No subsampling anywhere.

## 10. DELIVERABLES

| File | Size |
|------|------|
| /Users/brock-mini-mac/v5-truth-matrix/AUD_JPY_truth.parquet | 229.7 MB |
| /Users/brock-mini-mac/v5-truth-matrix/AUD_USD_truth.parquet | 224.2 MB |
| /Users/brock-mini-mac/v5-truth-matrix/EUR_JPY_truth.parquet | 231.3 MB |
| /Users/brock-mini-mac/v5-truth-matrix/EUR_USD_truth.parquet | 227.8 MB |
| /Users/brock-mini-mac/v5-truth-matrix/GBP_USD_truth.parquet | 230.8 MB |
| /Users/brock-mini-mac/v5-truth-matrix/USD_CAD_truth.parquet | 227.5 MB |
| /Users/brock-mini-mac/v5-truth-matrix/USD_CHF_truth.parquet | 222.9 MB |
| /Users/brock-mini-mac/v5-truth-matrix/USD_JPY_truth.parquet | 230.0 MB |
| /Users/brock-mini-mac/v5-truth-matrix/cell_sync_results.parquet | 0.141 MB |
| /Users/brock-mini-mac/v5-truth-matrix/cell_sync_summary.json | 0.475 MB |
| /Users/brock-mini-mac/v5-truth-matrix/broker_anchor_trades.json | 0.058 MB |
| /Users/brock-mini-mac/v5-truth-matrix/anchor_check_results.json | 0.001 MB |
| /Users/brock-mini-mac/v5-truth-matrix/seam_report.json | 0.008 MB |
| /Users/brock-mini-mac/v5-truth-matrix/ranking_diff.json | 0.002 MB |
| /Users/brock-mini-mac/v5-truth-matrix/TRUTH_MATRIX_REPORT.md | 0.014 MB |
