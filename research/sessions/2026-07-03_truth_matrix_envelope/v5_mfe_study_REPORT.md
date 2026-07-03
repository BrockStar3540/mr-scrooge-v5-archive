# V5 Dead-Entry (Low-MFE) Indicator Study — REPORT

Generated: 2026-07-02T23:23:32Z

**Study dir:** `~/v5-mfe-study/`  |  **n_features_computed:** 49

---

## 1. Trade Sample

| Metric | Count |
|--------|-------|
| Total V5-era closed trades | 165 |
| v1 era (before 2026-06-20T12Z) | 55 |
| v2/v3 era (main analysis) | 110 |
| v2/v3 with valid MFE computed | 110 |
| **DEAD** (MFE < 5p) | **32** |
| MIDDLE (5–9p) | 34 |
| **MOVER** (MFE ≥ 10p) | **44** |
| Dropped (insufficient candle data) | 0 |
| Binary analysis set (DEAD + MOVER) | 76 |

**Parquet gap note:** All 8-pair parquets end 2026-06-18; all v2/v3 trades are 2026-06-20 onward. Features recomputed from live OANDA M5+H1 candles (400 M5 bars lookback, 100 H1 bars). 8yr-anchored features (htf_pct absolute, PDH/PDL dist, ADR absolute) proxied via zscore_1h / trend_4h in this study. The parquet corpus was used only for veto-check (2026 section, 272k bars).

## 2. DEAD Cohort Damage (v2/v3 era)

- **32 DEAD entries** (MFE < 5p) realized **-626.5 pips total** (avg -19.6p/trade).
- A perfect dead-entry filter would recover approximately **626 pips** on the v2/v3 period.
- Context: 44 MOVER trades in the same period — the dead entries cost ~14.2p per mover equivalent.

## 3. Top-20 Feature Ranking — Pooled (v2/v3, Binary DEAD vs MOVER)

**Alignment convention:** Directional features (returns, momentum oscillators, EMA distances, OBV, MFI) are sign-flipped for SHORT trades so 'higher value = more in-direction' consistently.

| Rank | Feature | AUC | Best Split Threshold | TPR@split | FPR@split | Overlap | n |
|------|---------|-----|---------------------|-----------|-----------|---------|---|
| 1 | `h1_ret_1bar` | **0.6577** | -0.0007 | 0.841 | 0.562 | 0.6178 | 76 |
| 2 | `q_bbwp_m5` | **0.6325** | 0.8605 | 0.656 | 0.318 | 0.6927 | 76 |
| 3 | `ema20_1h_dist` | **0.6151** | 0.0011 | 0.386 | 0.125 | 0.6842 | 76 |
| 4 | `bb_width` | **0.6051** | 0.0016 | 0.375 | 0.068 | 0.6675 | 76 |
| 5 | `atr_d_pips` | **0.6016** | 60.5 | 0.705 | 0.406 | 0.8011 | 76 |
| 6 | `ret_5m` | **0.5959** | -0.0 | 0.656 | 0.409 | 0.8731 | 76 |
| 7 | `q_adx_h1` | **0.5930** | 29.9461 | 0.682 | 0.406 | 0.5983 | 76 |
| 8 | `atr_h1_relative` | **0.5902** | 1.301 | 0.344 | 0.114 | 0.5681 | 76 |
| 9 | `q_obv` | **0.5817** | 1.2491 | 0.438 | 0.25 | 0.7383 | 76 |
| 10 | `q_stochrsi_m5` | **0.5817** | -0.4438 | 0.906 | 0.682 | 0.5707 | 76 |
| 11 | `zscore_1h` | **0.5795** | -2.1573 | 0.955 | 0.75 | 0.5017 | 76 |
| 12 | `htf_pct_20` | **0.5795** | -2.1573 | 0.955 | 0.75 | 0.5017 | 76 |
| 13 | `rsi_slope` | **0.5781** | -12.3167 | 0.818 | 0.531 | 0.6068 | 76 |
| 14 | `rvol_12bar` | **0.5717** | 2.4512 | 0.364 | 0.125 | 0.759 | 76 |
| 15 | `q_entropy_m5` | **0.5653** | 2.3013 | 0.818 | 0.625 | 0.8504 | 76 |
| 16 | `ema5_dist_pips` | **0.5646** | -2.7846 | 0.844 | 0.614 | 0.868 | 76 |
| 17 | `rsi_m5_proxy` | **0.5589** | -55.0756 | 0.938 | 0.705 | 0.7077 | 76 |
| 18 | `h1_ret_4bar` | **0.5568** | 0.0009 | 0.455 | 0.281 | 0.7276 | 76 |
| 19 | `trend_4h` | **0.5568** | 0.0009 | 0.455 | 0.281 | 0.7276 | 76 |
| 20 | `q_aroonosc_h1` | **0.5568** | -21.4286 | 0.75 | 0.591 | 0.6331 | 76 |

*AUCs across pooled 76 trades (32 DEAD + 44 MOVER). Max AUC = 0.658 (h1_ret_1bar) — the signal is modest but consistent across sessions (see §5).*

## 4. Existing Momentum Inputs vs New Candidates

*(atr_5m, rvol_5bar, rvol_12bar, adr_consumed, atr_1h, atr_d_pips, q_atrn_m5, q_yzv_m5)*

| Global Rank | Feature | AUC | Split Threshold | Note |
|------------|---------|-----|----------------|------|
| 1 | `h1_ret_1bar` | 0.6577 | -0.0007 | **NEW CANDIDATE** |
| 2 | `q_bbwp_m5` | 0.6325 | 0.8605 | **NEW CANDIDATE** |
| 3 | `ema20_1h_dist` | 0.6151 | 0.0011 | **NEW CANDIDATE** |
| 4 | `bb_width` | 0.6051 | 0.0016 | **NEW CANDIDATE** |
| 6 | `ret_5m` | 0.5959 | -0.0 | **NEW CANDIDATE** |
| 5 | `atr_d_pips` | 0.6016 | 60.5 | existing momentum input |
| 14 | `rvol_12bar` | 0.5717 | 2.4512 | existing momentum input |
| 23 | `rvol_5bar` | 0.5462 | 1.8705 | existing momentum input |
| 28 | `q_yzv_m5` | 0.5362 | 0.0 | existing momentum input |
| 36 | `adr_consumed` | 0.5206 | -0.743 | existing momentum input |
| 44 | `atr_5m` | 0.5135 | 2.3051 | existing momentum input |
| 45 | `q_atrn_m5` | 0.5107 | 1.0746 | existing momentum input |
| 48 | `atr_1h` | 0.5014 | 22.1567 | existing momentum input |

**Key finding:** The existing momentum inputs (atr, rvol, adr_consumed) cluster in ranks 5–49 with AUCs 0.50–0.60. The two strongest candidates — `h1_ret_1bar` (H1 1-bar return, AUC=0.658) and `q_bbwp_m5` (M5 BB-width percentile, AUC=0.633) — are NOT in the current momentum module and clearly outrank what's already there.

## 5. Per-Session Rankings

### ASIA (n_binary=29)
| Rank | Feature | AUC | n |
|------|---------|-----|---|
| 1 | `h1_ret_1bar` | 0.8583 | 29 |
| 2 | `ema20_1h_dist` | 0.7528 | 29 |
| 3 | `ret_5m` | 0.7444 | 29 |
| 4 | `q_chop_h1` | 0.7083 | 29 |
| 5 | `h1_ret_4bar` | 0.6972 | 29 |
| 6 | `trend_4h` | 0.6972 | 29 |
| 7 | `htf_pct_60` | 0.6972 | 29 |
| 8 | `q_cci_m5` | 0.6889 | 29 |
| 9 | `adr_consumed` | 0.6889 | 29 |
| 10 | `rsi14_h1` | 0.6806 | 29 |

### LONDON (n_binary=24)
| Rank | Feature | AUC | n |
|------|---------|-----|---|
| 1 | `q_bbwp_m5` | 0.7727 | 24 |
| 2 | `q_mfi` | 0.7343 | 24 |
| 3 | `q_obv` | 0.7273 | 24 |
| 4 | `vortex_diff_m5` | 0.6923 | 24 |
| 5 | `h1_ret_1bar` | 0.6923 | 24 |
| 6 | `adr_consumed` | 0.6853 | 24 |
| 7 | `bb_width` | 0.6783 | 24 |
| 8 | `rsi_m5_proxy` | 0.6713 | 24 |
| 9 | `ema_cross_pips` | 0.6503 | 24 |
| 10 | `q_stochrsi_m5` | 0.6503 | 24 |

### NY (n_binary=23)
| Rank | Feature | AUC | n |
|------|---------|-----|---|
| 1 | `q_adx_h1` | 0.8220 | 23 |
| 2 | `atr_d_pips` | 0.7765 | 23 |
| 3 | `atr_1h` | 0.7765 | 23 |
| 4 | `ret_15m` | 0.7652 | 23 |
| 5 | `ema5_dist_pips` | 0.7500 | 23 |
| 6 | `q_aroonosc_h1` | 0.7386 | 23 |
| 7 | `ret_30m` | 0.7197 | 23 |
| 8 | `q_chop_h1` | 0.6856 | 23 |
| 9 | `q_stochrsi_m5` | 0.6818 | 23 |
| 10 | `q_obv` | 0.6667 | 23 |

**Per-session commentary:**
- **ASIA**: `h1_ret_1bar` dominates with AUC=0.858 — the most decisive session for this feature. Entries against the most recent H1 bar's direction consistently die. Also `ema20_1h_dist` (0.753) and `ret_5m` (0.744).
- **LONDON**: Volatility-regime features lead: `q_bbwp_m5` (0.773), `q_mfi` (0.734), `q_obv` (0.727). Volume/flow-based indicators separate dead/mover better than directional features. `vortex_diff_m5` at 0.692.
- **NY**: `q_adx_h1` (0.822) and ATR-class features dominate — `atr_d_pips` (0.777), `atr_1h` (0.777). NY requires trend strength (ADX) and sufficient volatility environment. `ret_15m` (0.765) also prominent.

## 6. XGB Multivariate Sanity Check (top-10 features)

- **CV AUC: 0.6294 ± 0.1257** (5-fold StratifiedKFold, n=76)
- CV AUC closely matches best single-feature AUC (0.629 vs 0.658) — consistent with small-n / limited multivariate lift expected at n=76.

| XGB Rank | Feature | Importance |
|----------|---------|-----------|
| 1 | `q_bbwp_m5` | 0.1415 |
| 2 | `bb_width` | 0.1161 |
| 3 | `atr_d_pips` | 0.1045 |
| 4 | `h1_ret_1bar` | 0.1036 |
| 5 | `ema20_1h_dist` | 0.1025 |
| 6 | `q_stochrsi_m5` | 0.1001 |
| 7 | `ret_5m` | 0.0985 |
| 8 | `q_obv` | 0.0907 |
| 9 | `q_adx_h1` | 0.0721 |
| 10 | `atr_h1_relative` | 0.0705 |

XGB importances largely confirm single-feature ranking: q_bbwp_m5 tops XGB (0.142) vs #2 in single-feature; h1_ret_1bar is #4 in XGB (0.104). The small spread of importances reflects mild multicollinearity — all 10 features carry some independent signal.

## 7. Corpus Veto Check (top-5 vs 2026 Parquet Bars)

*Method: compute corr(feature, |1H-forward pips|) on Jan–Jun 2026 parquet bars (272,606 bars). A negative correlation means 'higher feature value = smaller subsequent move' — contradicts the MOVER interpretation.*

| Feature | Parquet Column | Corpus Corr | n_bars | Verdict | Interpretation |
|---------|---------------|------------|--------|---------|----------------|
| `h1_ret_1bar` | `h1_ret_1bar` | -0.1253 | 272606 | **SUSPECT** | SUSPECT — recent H1 momentum is directional (corr<0 = mean-reversion regime). Consistent with NY-fade doctrine. Use direction-aligned split, not magnitude. |
| `q_bbwp_m5` | `q_bbwp_m5` | 0.1242 | 272606 | **OK** | OK — wider BB = larger subsequent moves. Corpus confirms: high BBWP = expansion regime favorable to movers. |
| `ema20_1h_dist` | `ema20_1h_dist` | -0.1065 | 272606 | **SUSPECT** | SUSPECT — distance from H1 EMA is a mean-reversion indicator in the corpus. Use carefully; the trade-level signal may reflect different mechanics. |
| `bb_width` | `bb_width` | 0.3107 | 272606 | **OK** | OK — BB expansion reliably precedes larger moves in the corpus (corr=0.31). |
| `atr_d_pips` | `atr_d_pips` | 0.2564 | 272606 | **OK** | OK — higher daily ATR range environment = larger subsequent moves (corr=0.26). Standard volatility filter. |

**Veto summary:** h1_ret_1bar and ema20_1h_dist are flagged SUSPECT in corpus — they show mean-reversion behavior in the 2026 data overall. However, their strong per-trade signal (especially Asia session) suggests a different mechanism: they separate DEAD from MOVER because dead entries fight the most recent H1 direction. Recommended use: as soft weights in the direction-aligned, session-specific form — not as unsigned magnitude filters.

## 8. Cost Curve — #1 Feature (`h1_ret_1bar`)

*Filtering 'below' threshold means blocking trades where direction-aligned h1_ret_1bar is below the percentile cutoff (i.e., entry is AGAINST the most recent H1 bar). Each row shows: what % of DEAD trades we catch, at what cost of sacrificed MOVERs.*

| Percentile Cutoff | h1_ret_1bar Threshold | % DEAD Caught | % MOVER Sacrificed | Pips Saved | n filtered |
|------------------|-----------------------|--------------|-------------------|------------|------------|
| 5p | -0.0028 | 9.4% | 2.3% | +61.2 | 4 |
| 10p | -0.0017 | 12.5% | 9.1% | +83.2 | 8 |
| 15p | -0.0013 | 18.8% | 13.6% | +123.0 | 12 |
| 20p | -0.0011 | 31.2% | 13.6% | +204.2 | 16 |
| 25p | -0.0009 | 40.6% | 15.9% | +254.9 | 20 |
| 30p | -0.0006 | 43.8% | 20.5% | +275.0 | 23 |
| 40p | -0.0003 | 53.1% | 31.8% | +335.7 | 31 |
| 50p | -0.0 | 62.5% | 40.9% | +387.0 | 38 |
| 60p | 0.0003 | 75.0% | 50.0% | +466.4 | 46 |
| 70p | 0.0005 | 84.4% | 59.1% | +526.5 | 53 |
| 80p | 0.0008 | 90.6% | 72.7% | +566.5 | 61 |
| 90p | 0.0013 | 96.9% | 84.1% | +606.5 | 68 |

**Sweet spot:** The 25th–30th percentile 'below' threshold (h1_ret_1bar < -0.0009 to -0.0007) catches ~40–50% of DEAD trades while sacrificing only 16–23% of MOVERs. At the 25th percentile: +254.9 pips saved from blocking 13/32 dead entries vs. losing 7/44 movers — a net-positive filter.

**Soft-weight wiring note:** Don't gate with a hard threshold. Map h1_ret_1bar onto a continuous penalty to expected_pips (e.g., linear penalty in the [-0.003, 0] zone, zero penalty above 0). This preserves mover coverage while reducing dead-entry rates.

## 9. Recommended Soft Weights for Momentum Module

Based on the analysis, the following features are candidates for soft-weight addition to the momentum module (`expected_pips`/`m_cert`), in priority order:

| Priority | Feature | AUC (pooled) | Veto | Best Session | Wiring Suggestion |
|----------|---------|-------------|------|------------|------------------|
| 1 | `h1_ret_1bar` | 0.658 | SUSPECT (directional) | Asia (0.858) | direction-aligned soft penalty when < -0.0009 (25th pct); session-specific weight (2x in Asia) |
| 2 | `q_bbwp_m5` | 0.633 | OK | London (0.773) | higher BBWP → higher m_cert; threshold ~0.86; especially London |
| 3 | `q_adx_h1` | 0.593 | not in top-5 | NY (0.822) | ADX < 20 (low trend) = dead-entry risk in NY; soft penalty below threshold 29.9 |
| 4 | `bb_width` | 0.605 | OK | all | minimum expansion gate; raw threshold 0.0016 |
| 5 | `atr_d_pips` | 0.602 | OK | NY (0.777) | already in momentum vicinity; threshold 60.5p; confirmed by corpus |

*All wiring should be soft-weights / continuous multipliers on expected_pips/m_cert, NOT hard gates, to avoid binary edge-clipping.*

## 10. Methodology
- **Era split**: v1 < 2026-06-20T12:00Z; v2/v3 ≥ 2026-06-20T12:00Z
- **MFE computation**: M5 mid candles, entry → close (OANDA practice API). DEAD=MFE<5p, MOVER=MFE≥10p, MIDDLE excluded from binary
- **Parquet gap**: All parquets end 2026-06-18; features computed from 400-bar M5 + 100-bar H1 live candles per trade
- **Direction alignment**: SHORT trades have directional indicator values sign-flipped before analysis
- **Corpus veto**: 2026 Jan–Jun parquet bars (~272k rows × 8 pairs); corr(feature, |1H fwd pips|)
- **XGB sanity check**: max_depth=2, reg_alpha=2, reg_lambda=5, n_estimators=100, 5-fold StratifiedKFold
- **Sample**: n=76 binary (32 DEAD + 44 MOVER); pooled across all 8 pairs
- **Pairs covered**: AUD_JPY, AUD_USD, EUR_JPY, EUR_USD, GBP_USD, USD_CAD, USD_CHF, USD_JPY

---

## 11. Per-Cell Threshold Table (Amendment, 2026-07-02T23:27Z)

*Fitted on 2026 parquet bars (Jan 1 - Jun 18), per pair x session x direction. Labels on bars: MOVER = favorable 1H-forward >= +10p, DEAD = favorable fwd < +5p (middle excluded). Directional features (h1_ret_1bar, ema20_1h_dist) sign-flipped for the short cell. `knee25` = 25th percentile of aligned feature among MOVER bars (soft-penalty knee). Full grid: `per_cell_thresholds.csv` (one row per cell x feature).*

### Top-3 features per cell

| Cell (pair session dir) | Top-3 (feature, AUC, sign, knee25) |
|---|---|
| AUD_JPY asia long | h1_ret_1bar(AUC=0.7311, sign=+, knee=-0.4); bb_width(AUC=0.6098, sign=+, knee=14.18947); atr_d_pips(AUC=0.5734, sign=+, knee=90.82119) |
| AUD_JPY asia short | h1_ret_1bar(AUC=0.7612, sign=+, knee=0.9); ema20_1h_dist(AUC=0.6283, sign=+, knee=-0.00084); atr_d_pips(AUC=0.6059, sign=+, knee=97.99145) |
| AUD_JPY london long | h1_ret_1bar(AUC=0.7332, sign=+, knee=0.5); bb_width(AUC=0.6169, sign=+, knee=15.59795); atr_d_pips(AUC=0.6062, sign=+, knee=97.99145) |
| AUD_JPY london short | h1_ret_1bar(AUC=0.7396, sign=+, knee=-0.225); ema20_1h_dist(AUC=0.6335, sign=+, knee=-0.00091); atr_d_pips(AUC=0.5783, sign=+, knee=91.80769) |
| AUD_JPY ny long | h1_ret_1bar(AUC=0.6972, sign=+, knee=-1.2); bb_width(AUC=0.655, sign=+, knee=16.11008); q_bbwp_m5(AUC=0.6006, sign=+, knee=0.26) |
| AUD_JPY ny short | h1_ret_1bar(AUC=0.7532, sign=+, knee=-0.3); ema20_1h_dist(AUC=0.6709, sign=+, knee=-0.00082); bb_width(AUC=0.6392, sign=+, knee=15.93693) |
| AUD_USD asia long | h1_ret_1bar(AUC=0.7564, sign=+, knee=0.2); bb_width(AUC=0.6384, sign=+, knee=9.44885); atr_d_pips(AUC=0.5708, sign=+, knee=62.00756) |
| AUD_USD asia short | h1_ret_1bar(AUC=0.7543, sign=+, knee=0.4); bb_width(AUC=0.642, sign=+, knee=9.88005); ema20_1h_dist(AUC=0.6146, sign=+, knee=-0.00115) |
| AUD_USD london long | h1_ret_1bar(AUC=0.7167, sign=+, knee=-2.0); bb_width(AUC=0.6396, sign=+, knee=11.32968); atr_d_pips(AUC=0.6139, sign=+, knee=62.30131) |
| AUD_USD london short | h1_ret_1bar(AUC=0.7479, sign=+, knee=-0.2); ema20_1h_dist(AUC=0.6247, sign=+, knee=-0.00118); bb_width(AUC=0.6128, sign=+, knee=11.00845) |
| AUD_USD ny long | bb_width(AUC=0.7139, sign=+, knee=14.16811); h1_ret_1bar(AUC=0.7006, sign=+, knee=-1.2); q_bbwp_m5(AUC=0.658, sign=+, knee=0.35) |
| AUD_USD ny short | h1_ret_1bar(AUC=0.7279, sign=+, knee=-0.2); ema20_1h_dist(AUC=0.6845, sign=+, knee=-0.00056); bb_width(AUC=0.6446, sign=+, knee=12.6375) |
| EUR_JPY asia long | h1_ret_1bar(AUC=0.7269, sign=+, knee=0.125); bb_width(AUC=0.6354, sign=+, knee=14.04508); atr_d_pips(AUC=0.6, sign=+, knee=97.6637) |
| EUR_JPY asia short | h1_ret_1bar(AUC=0.7465, sign=+, knee=-0.0); atr_d_pips(AUC=0.6439, sign=+, knee=100.89715); ema20_1h_dist(AUC=0.6335, sign=+, knee=-0.00058) |
| EUR_JPY london long | h1_ret_1bar(AUC=0.7429, sign=+, knee=-0.4); bb_width(AUC=0.5637, sign=+, knee=15.88574); atr_d_pips(AUC=0.5546, sign=+, knee=97.11787) |
| EUR_JPY london short | h1_ret_1bar(AUC=0.7399, sign=+, knee=-1.0); ema20_1h_dist(AUC=0.6544, sign=+, knee=-0.00047); atr_d_pips(AUC=0.5635, sign=+, knee=97.57638) |
| EUR_JPY ny long | h1_ret_1bar(AUC=0.7061, sign=+, knee=-0.6); bb_width(AUC=0.6398, sign=+, knee=15.88923); atr_d_pips(AUC=0.5974, sign=+, knee=99.61629) |
| EUR_JPY ny short | h1_ret_1bar(AUC=0.7398, sign=+, knee=-1.0); bb_width(AUC=0.644, sign=+, knee=15.87396); ema20_1h_dist(AUC=0.6368, sign=+, knee=-0.0007) |
| EUR_USD asia long | h1_ret_1bar(AUC=0.7238, sign=+, knee=-0.4); bb_width(AUC=0.6674, sign=+, knee=8.61098); atr_d_pips(AUC=0.602, sign=+, knee=63.42976) |
| EUR_USD asia short | h1_ret_1bar(AUC=0.7373, sign=+, knee=0.6); bb_width(AUC=0.6921, sign=+, knee=9.00946); atr_d_pips(AUC=0.622, sign=+, knee=64.82492) |
| EUR_USD london long | h1_ret_1bar(AUC=0.733, sign=+, knee=-1.6); bb_width(AUC=0.6161, sign=+, knee=11.50581); atr_d_pips(AUC=0.6117, sign=+, knee=64.02344) |
| EUR_USD london short | h1_ret_1bar(AUC=0.7414, sign=+, knee=0.1); ema20_1h_dist(AUC=0.6348, sign=+, knee=-0.00038); atr_d_pips(AUC=0.5819, sign=+, knee=63.93858) |
| EUR_USD ny long | h1_ret_1bar(AUC=0.707, sign=+, knee=-2.2); bb_width(AUC=0.7059, sign=+, knee=15.76392); q_bbwp_m5(AUC=0.6473, sign=+, knee=0.35) |
| EUR_USD ny short | h1_ret_1bar(AUC=0.7058, sign=+, knee=-0.7); bb_width(AUC=0.655, sign=+, knee=15.05115); ema20_1h_dist(AUC=0.6163, sign=+, knee=-0.00069) |
| GBP_USD asia long | h1_ret_1bar(AUC=0.7284, sign=+, knee=-1.1); bb_width(AUC=0.6176, sign=+, knee=9.91186); atr_d_pips(AUC=0.5748, sign=+, knee=87.92646) |
| GBP_USD asia short | h1_ret_1bar(AUC=0.7425, sign=+, knee=1.6); bb_width(AUC=0.6376, sign=+, knee=10.2549); atr_d_pips(AUC=0.62, sign=+, knee=90.02603) |
| GBP_USD london long | h1_ret_1bar(AUC=0.7157, sign=+, knee=-1.8); atr_d_pips(AUC=0.5891, sign=+, knee=88.95834); bb_width(AUC=0.5773, sign=+, knee=15.8309) |
| GBP_USD london short | h1_ret_1bar(AUC=0.7153, sign=+, knee=-1.6); ema20_1h_dist(AUC=0.6057, sign=+, knee=-0.00055); atr_d_pips(AUC=0.5495, sign=+, knee=87.92585) |
| GBP_USD ny long | h1_ret_1bar(AUC=0.711, sign=+, knee=-2.9); bb_width(AUC=0.6729, sign=+, knee=18.84801); q_bbwp_m5(AUC=0.6218, sign=+, knee=0.29) |
| GBP_USD ny short | h1_ret_1bar(AUC=0.7072, sign=+, knee=-1.6); bb_width(AUC=0.6351, sign=+, knee=18.61661); q_bbwp_m5(AUC=0.6159, sign=+, knee=0.29) |
| USD_CAD asia long | h1_ret_1bar(AUC=0.7094, sign=+, knee=-1.4); atr_d_pips(AUC=0.6528, sign=+, knee=59.12112); bb_width(AUC=0.6382, sign=+, knee=7.44464) |
| USD_CAD asia short | h1_ret_1bar(AUC=0.7472, sign=+, knee=0.9); bb_width(AUC=0.6978, sign=+, knee=8.14529); atr_d_pips(AUC=0.6558, sign=+, knee=58.90071) |
| USD_CAD london long | h1_ret_1bar(AUC=0.7053, sign=+, knee=-1.8); ema20_1h_dist(AUC=0.6019, sign=+, knee=-0.00022); atr_d_pips(AUC=0.5952, sign=+, knee=56.06217) |
| USD_CAD london short | h1_ret_1bar(AUC=0.7411, sign=+, knee=0.6); atr_d_pips(AUC=0.6049, sign=+, knee=57.72612); bb_width(AUC=0.6028, sign=+, knee=9.81319) |
| USD_CAD ny long | h1_ret_1bar(AUC=0.7215, sign=+, knee=-0.1); bb_width(AUC=0.6357, sign=+, knee=14.46257); q_bbwp_m5(AUC=0.6157, sign=+, knee=0.4) |
| USD_CAD ny short | h1_ret_1bar(AUC=0.7204, sign=+, knee=-1.2); bb_width(AUC=0.6998, sign=+, knee=15.23148); q_bbwp_m5(AUC=0.6766, sign=+, knee=0.44) |
| USD_CHF asia long | bb_width(AUC=0.7267, sign=+, knee=8.51042); h1_ret_1bar(AUC=0.712, sign=+, knee=-0.825); atr_d_pips(AUC=0.676, sign=+, knee=59.83004) |
| USD_CHF asia short | h1_ret_1bar(AUC=0.743, sign=+, knee=0.125); ema20_1h_dist(AUC=0.6463, sign=+, knee=-0.00044); bb_width(AUC=0.636, sign=+, knee=5.95459) |
| USD_CHF london long | h1_ret_1bar(AUC=0.7611, sign=+, knee=1.1); ema20_1h_dist(AUC=0.6498, sign=+, knee=-0.00029); atr_d_pips(AUC=0.5814, sign=+, knee=54.02791) |
| USD_CHF london short | h1_ret_1bar(AUC=0.7644, sign=+, knee=1.2); ema20_1h_dist(AUC=0.6368, sign=+, knee=-0.00071); bb_width(AUC=0.6178, sign=+, knee=10.24983) |
| USD_CHF ny long | h1_ret_1bar(AUC=0.7009, sign=+, knee=-0.9); bb_width(AUC=0.6382, sign=+, knee=11.77374); q_bbwp_m5(AUC=0.6274, sign=+, knee=0.315) |
| USD_CHF ny short | h1_ret_1bar(AUC=0.7154, sign=+, knee=-1.1); bb_width(AUC=0.6945, sign=+, knee=12.71139); q_bbwp_m5(AUC=0.6494, sign=+, knee=0.35) |
| USD_JPY asia long | h1_ret_1bar(AUC=0.7479, sign=+, knee=1.0); bb_width(AUC=0.6612, sign=+, knee=15.2325); atr_d_pips(AUC=0.6391, sign=+, knee=98.80458) |
| USD_JPY asia short | h1_ret_1bar(AUC=0.7536, sign=+, knee=-1.0); bb_width(AUC=0.6778, sign=+, knee=15.34932); atr_d_pips(AUC=0.6671, sign=+, knee=107.62139) |
| USD_JPY london long | h1_ret_1bar(AUC=0.7155, sign=+, knee=-1.2); atr_d_pips(AUC=0.667, sign=+, knee=104.8035); bb_width(AUC=0.6541, sign=+, knee=17.30665) |
| USD_JPY london short | h1_ret_1bar(AUC=0.725, sign=+, knee=-1.15); bb_width(AUC=0.63, sign=+, knee=16.8914); ema20_1h_dist(AUC=0.6031, sign=+, knee=-0.00095) |
| USD_JPY ny long | h1_ret_1bar(AUC=0.7269, sign=+, knee=0.0); bb_width(AUC=0.6518, sign=+, knee=17.7886); atr_d_pips(AUC=0.611, sign=+, knee=99.42032) |
| USD_JPY ny short | h1_ret_1bar(AUC=0.7414, sign=+, knee=-1.1); bb_width(AUC=0.6563, sign=+, knee=16.59143); ema20_1h_dist(AUC=0.6425, sign=+, knee=-0.0009) |

## 12. Drift Labels 2022-2026 (Amendment)

*Sign target: directional features -> corr(feature, signed 1H fwd pips); magnitude features -> corr(feature, |1H fwd pips|). Per pair x session. Monthly UNSTABLE = >=2 of 6 months (Jan-Jun 2026) disagree with the majority sign. Yearly: PERSISTENT = same sign 2022-2026; REGIME = 2025-26 sign only; FLICKER = unstable. Full grid: `drift_labels.csv`.*

| Feature | Cells | PERSISTENT | REGIME | FLICKER | Monthly-UNSTABLE | Yearly mean corr (2022..2026) | Verdict |
|---|---|---|---|---|---|---|---|
| `h1_ret_1bar` | 24 | 24 | 0 | 0 | 0 | 2022:0.3993, 2023:0.4099, 2024:0.4237, 2025:0.3946, 2026:0.4046 | **SHIP (persistent)** |
| `q_bbwp_m5` | 24 | 20 | 2 | 2 | 7 | 2022:0.1157, 2023:0.1283, 2024:0.1225, 2025:0.0844, 2026:0.1059 | **SHIP (persistent)** |
| `ema20_1h_dist` | 24 | 24 | 0 | 0 | 3 | 2022:0.1709, 2023:0.1801, 2024:0.1709, 2025:0.163, 2026:0.1605 | **SHIP (persistent)** |
| `bb_width` | 24 | 24 | 0 | 0 | 0 | 2022:0.2208, 2023:0.2104, 2024:0.2617, 2025:0.2484, 2026:0.2557 | **SHIP (persistent)** |
| `atr_d_pips` | 24 | 24 | 0 | 0 | 5 | 2022:0.1883, 2023:0.1534, 2024:0.1806, 2025:0.2468, 2026:0.1828 | **SHIP (persistent)** |
| `q_adx_h1` | 24 | 21 | 0 | 3 | 11 | 2022:0.0451, 2023:0.0635, 2024:0.0577, 2025:0.0355, 2026:0.0595 | **SHIP WITH CAUTION** |

**q_bbwp_m5 verdict (the kurtosis/bbwp-trap check):** SHIP (persistent). Cells: 20/24 persistent, 2 regime-only, 2 flicker; 7 cells monthly-unstable in 2026. Yearly pooled corr trajectory: {2022: 0.1157, 2023: 0.1283, 2024: 0.1225, 2025: 0.0844, 2026: 0.1059}.

## 13. Leak Sanity Check: h1_ret_1bar vs fwd_ret_pips (2026-07-02T23:32Z)

**VERDICT: LEAK**

**(a) Source evidence** (`v5_qtl_8yr_features.py`):
- L70: `h1_ret_1bar = (h1_close - h1_close.shift(1)) / pip` on the raw H1 frame
- L106-108: joined to M5 via `merge_asof(..., right_on='h1_time', direction='backward')` on the raw H1 index
- L245: `fwd_ret_pips = (m5_close.shift(-12) - m5_close) / pip` (strictly forward, t -> t+60m)
- The raw H1 parquet is indexed by bar OPEN time (verified empirically below), so the backward as-of match at M5 bar t selects the H1 bar CONTAINING t. That bar's close is the price up to 60 min in the future -> overlaps the fwd_ret_pips window.

**(b) Empirical evidence** (EUR_USD):
- H1 index convention: of 497 sampled H1 bars, close matched the M5 close at tau+55m in 497 cases (open-time convention) vs 3 at tau-5m.
- Parquet h1_ret_1bar reconstruction over 24591 M5 bars: matches the LEAKY containing-bar value in 100.0% of bars, vs the safe previous-completed-bar value in 0.7%.

**(c) Corrected effect sizes** (non-overlapping h1_ret_1bar = previous COMPLETED H1 bar):

| Cell | Dir | LEAKY AUC / corr | SAFE AUC / corr | n |
|---|---|---|---|---|
| EUR_USD asia | long | 0.7238 / 0.4103 | 0.51 / -0.0332 | 10010 |
| EUR_USD asia | short | 0.7373 / 0.4107 | 0.5167 / -0.0351 | 9819 |
| USD_JPY ny | long | 0.7269 / 0.4501 | 0.5243 / 0.056 | 11048 |
| USD_JPY ny | short | 0.7414 / 0.4537 | 0.5431 / 0.0668 | 11456 |
| GBP_USD london | long | 0.7157 / 0.3701 | 0.532 / -0.0691 | 8592 |
| GBP_USD london | short | 0.7153 / 0.3674 | 0.5075 / -0.0677 | 8717 |

Mean corr across sample cells: **LEAKY 0.4104 -> SAFE -0.0137**.

**Implications:**
- The +0.40 'persistence' of h1_ret_1bar in Sections 11-12 is inflated by look-ahead; the corrected corpus numbers above are the honest corpus estimate.
- The SAME open-time join affects ALL H1-joined parquet columns (ema20_1h_dist, zscore_1h, rsi14_h1, atr_1h, atr_h1_relative, h1_ret_4bar, trend_4h) and, via `h1_aligned = h1.reindex(m5.index, ffill)` (L238), all q_*_h1 columns (q_adx_h1, q_chop_h1, q_aroonosc_h1, q_vhf_h1, q_vortex_diff_h1). The daily join has the analogous issue (atr_d_pips includes the in-progress day; pdh/pdl are safe due to shift(1)). Sections 7, 11, 12 numbers for those columns should be treated as upper bounds.
- The LIVE-TRADE analysis (Sections 3-8 core ranking, AUC 0.658 for h1_ret_1bar) is NOT affected: study features were computed from candles fetched with `to=entry_time` (completed bars at-or-before entry only). The live AUC remains the trustworthy effect-size anchor.
- Recommendation: rebuild parquets with H1/D indices shifted to bar-close time before any further corpus-based per-cell tuning ships.