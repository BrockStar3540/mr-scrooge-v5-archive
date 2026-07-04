# RANGE-HARVEST INDICATOR SCREENING REPORT — v2 (MULTI-HORIZON + VALIDATED EXIT-WALK)
Generated: 2026-07-04 | Window: Jan-Jun 2026 | 8 pairs x 3 sessions x 2 directions = 48 cells
Horizons: 20/30/60/120/240 min. 20/30/120 computed from raw M5 (strictly-after-t, convention validated 98.4% vs stored 60m). Floors 6.0 + 7.5.

## 0. RECONCILIATION — v1 EV FIGURES RETRACTED
v1 sequential sanity (+4.1 to +6.4p EV) used a CRUDE exit model:
  (a) winners scored MFE_60 - trail = PERFECT PEAK CAPTURE (no first-passage walk, no return-to-stop)
  (b) never-triggered bars scored MFE - 2.0 (usually small positive) instead of walking to stop/horizon
  (c) flat 2p cost only on non-triggered bars; no per-pair 2x spread
  (d) no adverse-first intrabar ordering
Re-run with the VALIDATED simulator mechanics (ratchet_ev_study.py: adverse-first first-passage,
locks=peak-trail, exit on return to locked stop, 48-bar horizon, MTM-at-locked-SL for survivors,
net of 2x typical spread) on the SAME v1 filter sets:

                cell       geometry         v1_filter    n  crude_ev_v1  validated_ev_net  validated_ev_gross  validated_wr_net  engage_rate  survivor_rate  avg_bars_held  closeMTM_ev_net
   AUD_JPY asia long trail2.5_lock5   ema5 - 110.1788 4067        5.427            -2.147               1.853             0.754        0.754          0.026           12.6           -1.781
   AUD_JPY asia long trail1.5_lock6   ema5 - 110.1788 4067        5.951            -1.931               2.069             0.754        0.754          0.026           12.5           -1.564
 USD_CAD london long trail2.5_lock5 q_yzv_m5 + 0.0001 9505        4.173            -4.110              -1.110             0.672        0.672          0.134           22.9           -2.240
 USD_CAD london long trail1.5_lock6 q_yzv_m5 + 0.0001 9505        4.580            -3.946              -0.946             0.672        0.672          0.132           22.6           -2.084
 EUR_USD london long trail2.5_lock5  atr_1h + 12.0059 4139        5.051            -2.476              -0.076             0.691        0.691          0.047           15.1           -1.750
 EUR_USD london long trail1.5_lock6  atr_1h + 12.0059 4139        5.533            -2.151               0.249             0.691        0.691          0.047           14.9           -1.427
EUR_USD london short trail2.5_lock5  atr_1h + 12.0059 4139        5.143            -2.559              -0.159             0.694        0.694          0.068           15.7           -1.728
EUR_USD london short trail1.5_lock6  atr_1h + 12.0059 4139        5.629            -2.377               0.023             0.694        0.694          0.067           15.5           -1.549
     EUR_JPY ny long trail2.5_lock5   atr_5m + 5.7132 5644        5.814            -2.372               1.228             0.734        0.734          0.057           11.9           -1.560
     EUR_JPY ny long trail1.5_lock6   atr_5m + 5.7132 5644        6.370            -2.005               1.595             0.734        0.734          0.057           11.8           -1.194

VERDICT: the v1 +5p figures were exit-modeling artifacts. Validated EV on the same bars: -1.9 to -4.1p net
(gross before spread: -1.1 to +2.1p; close-MTM sensitivity: -1.2 to -2.2p). This MATCHES the broker-anchored
ratchet-EV study (-2 to -4.5p, 43/44 cells negative). The indicator filters DO produce consistent lift
(+0.7 to +2.7p vs unfiltered baseline) but do not turn per-bar ratchet EV positive at current geometry.
Trail 2.5->1.5 remains directionally positive but small: +0.16 to +0.37p on filtered sets, never sign-flipping.

## 1. BASE RATES BY HORIZON (median across 48 cells, floor 6.0)
 horizon_min  pct_RANGE_HARVEST  pct_RUNNER  pct_DEAD  pct_PIERCE  pct_GOOD
          20             20.200       2.950    74.355       2.990    23.260
          30             24.350       5.180    64.065       5.270    31.165
          60             29.065      11.595    44.275      11.960    41.670
         120             27.775      20.710    25.320      23.670    49.925
         240             20.735      30.410     9.675      39.725    49.905

RH offer rate peaks at 60m (29.1% median). Shorter horizons starve the class (less time to reach 6p:
DEAD 74.4% at 20m vs 44.3% at 60m); longer horizons bleed RH into RUNNER/PIERCE (PIERCE 39.7% at 240m).

Top-10 cells RH% by horizon:
                cell    20    30    60   120   240
   AUD_JPY asia long 26.13 30.17 34.13 26.33 12.43
 AUD_JPY london long 27.96 32.29 33.35 24.87 11.39
AUD_JPY london short 27.57 31.60 32.80 24.56 11.27
 AUD_USD london long 16.96 23.47 32.68 32.78 23.09
     EUR_JPY ny long 26.23 30.70 33.36 28.69 19.72
 EUR_USD london long 20.52 26.79 33.88 30.34 18.73
EUR_USD london short 21.30 27.19 33.46 30.39 16.89
 USD_CAD london long 15.53 22.60 33.98 34.29 20.62
USD_CAD london short 16.78 23.55 32.89 32.76 20.49
USD_CHF london short 15.53 22.48 33.08 34.73 26.26

## 2. FLOOR SENSITIVITY 6.0 vs 7.5 (median RH drop, pp) BY HORIZON
 horizon  median_rh_drop
      20            7.06
      30            7.94
      60            7.80
     120            6.52
     240            3.57

## 3. CROSS-HORIZON COMPARISON
- 30m best-AUC beats 60m in 48/48 cells (edge >= 0.01). Median edge: 0.0572
- Winner-horizon distribution: {20: 47, 240: 1}
- 20m CONDITIONAL TRIGGERED. 20m beats 30m in 48/48 cells (median edge 0.0289) — trend CONTINUES at 20m on AUC,
  BUT the class starves: median RH offer 20.2% (vs 24.4% at 30m), DEAD 74.4% median. The floor bites hardest in
  non-JPY asia/london-quiet cells (USD_CAD/USD_CHF/AUD_USD london ~15-17% RH at 20m).
- Top indicator differs across 30/60/120 within the same cell in 40/48 cells.

Drift label distribution (top-3 features per cell) by horizon:
drift_label  FLICKER  PERSISTENT  REGIME
horizon_min                             
20                17          49      78
30                 9          40      95
60                37          27      80
120               79          31      34
240               81          30      33

## 4. TOP-5 CELLS — CROSS-HORIZON DETAIL (wire-ready = plateau-valid, non-price-scale)

### AUD_JPY asia long (winner horizon: 20m)
   20m: atr_5m                 AUC=0.6724 drift=REGIME
   30m: atr_5m                 AUC=0.6409 drift=PERSISTENT
   60m: q_yzv_m5               AUC=0.5763 drift=nan
  120m: q_obv                  AUC=0.5465 drift=nan
  240m: adr_consumed           AUC=0.5745 drift=REGIME

### USD_CAD london long (winner horizon: 20m)
   20m: atr_5m                 AUC=0.6533 drift=REGIME
   30m: atr_5m                 AUC=0.6198 drift=PERSISTENT
   60m: q_yzv_m5               AUC=0.5767 drift=REGIME
  120m: adr_consumed           AUC=0.5487 drift=PERSISTENT
  240m: adr_consumed           AUC=0.5946 drift=REGIME

### EUR_USD london long (winner horizon: 20m)
   20m: atr_5m                 AUC=0.6557 drift=REGIME
   30m: q_yzv_m5               AUC=0.6324 drift=REGIME
   60m: atr_1h                 AUC=0.5952 drift=REGIME
  120m: adr_consumed           AUC=0.5483 drift=FLICKER
  240m: q_hurst_m5             AUC=0.566 drift=FLICKER

### EUR_USD london short (winner horizon: 20m)
   20m: atr_5m                 AUC=0.6588 drift=REGIME
   30m: atr_5m                 AUC=0.6325 drift=REGIME
   60m: atr_1h                 AUC=0.5767 drift=REGIME
  120m: q_hurst_m5             AUC=0.5453 drift=FLICKER
  240m: atr_1h                 AUC=0.5935 drift=REGIME

### EUR_JPY ny long (winner horizon: 20m)
   20m: atr_5m                 AUC=0.6902 drift=PERSISTENT
   30m: atr_5m                 AUC=0.6632 drift=PERSISTENT
   60m: atr_5m                 AUC=0.6182 drift=REGIME
  120m: q_atrn_m5              AUC=0.5615 drift=FLICKER
  240m: q_atrn_m5              AUC=0.5564 drift=FLICKER

NOTE: price-scale features (ema5/ema20/ema50/bb_mid/bb_std/pdh/pdl/d_*) are excluded from wire-ready
selection — v1's AUD_JPY ema5<=110.18 filter zeroed the May-Jun holdout when USD/JPY-cross levels moved (regime-fragile).

## 5. SEQUENTIAL SANITY v2 — VALIDATED WALK, BOTH TRAILS, h60 + BEST HORIZON
(ev_perbar_net = mean over all filtered bars net of 2x spread; ev_seq_net = non-overlapping sequential subset)
                cell horizon_label       geometry           split          set  n_perbar  ev_perbar_net  wr_perbar  n_seq  ev_seq_net  avg_bars_held  engage_rate
   AUD_JPY asia long           h60 trail2.5_lock5       full_2026     filtered      4762         -3.747      0.705    570      -2.727           11.5        0.705
   AUD_JPY asia long           h60 trail2.5_lock5       full_2026 baseline_all     12241         -4.452      0.686    904      -3.701           16.7        0.686
   AUD_JPY asia long           h60 trail1.5_lock6       full_2026     filtered      4762         -3.456      0.705    573      -2.507           11.4        0.705
   AUD_JPY asia long           h60 trail1.5_lock6       full_2026 baseline_all     12241         -4.225      0.686    912      -3.454           16.5        0.686
   AUD_JPY asia long           h60 trail2.5_lock5 holdout_May-Jun     filtered       695         -3.521      0.734     76      -1.309           15.9        0.734
   AUD_JPY asia long           h60 trail2.5_lock5 holdout_May-Jun baseline_all      4107         -6.870      0.610    209      -5.722           20.7        0.610
   AUD_JPY asia long           h60 trail1.5_lock6 holdout_May-Jun     filtered       695         -3.022      0.734     77      -0.609           15.8        0.734
   AUD_JPY asia long           h60 trail1.5_lock6 holdout_May-Jun baseline_all      4107         -6.663      0.610    213      -5.242           20.5        0.610
   AUD_JPY asia long      best_h30 trail2.5_lock5       full_2026     filtered      4802         -3.625      0.707    604      -2.819           11.3        0.707
   AUD_JPY asia long      best_h30 trail2.5_lock5       full_2026 baseline_all     12241         -4.452      0.686    904      -3.701           16.7        0.686
   AUD_JPY asia long      best_h30 trail1.5_lock6       full_2026     filtered      4802         -3.348      0.707    606      -2.568           11.2        0.707
   AUD_JPY asia long      best_h30 trail1.5_lock6       full_2026 baseline_all     12241         -4.225      0.686    912      -3.454           16.5        0.686
   AUD_JPY asia long      best_h30 trail2.5_lock5 holdout_May-Jun     filtered       735         -2.023      0.786     94      -1.349           14.9        0.786
   AUD_JPY asia long      best_h30 trail2.5_lock5 holdout_May-Jun baseline_all      4107         -6.870      0.610    209      -5.722           20.7        0.610
   AUD_JPY asia long      best_h30 trail1.5_lock6 holdout_May-Jun     filtered       735         -1.560      0.786     94      -0.733           14.8        0.786
   AUD_JPY asia long      best_h30 trail1.5_lock6 holdout_May-Jun baseline_all      4107         -6.663      0.610    213      -5.242           20.5        0.610
 USD_CAD london long           h60 trail2.5_lock5       full_2026     filtered      4439         -3.334      0.702    331      -3.341           19.0        0.702
 USD_CAD london long           h60 trail2.5_lock5       full_2026 baseline_all     10671         -4.470      0.660    534      -4.518           23.7        0.660
 USD_CAD london long           h60 trail1.5_lock6       full_2026     filtered      4439         -3.166      0.702    335      -3.080           18.7        0.702
 USD_CAD london long           h60 trail1.5_lock6       full_2026 baseline_all     10671         -4.313      0.660    541      -4.371           23.3        0.660
 USD_CAD london long           h60 trail2.5_lock5 holdout_May-Jun     filtered       893         -3.192      0.717     71      -2.038           23.2        0.717
 USD_CAD london long           h60 trail2.5_lock5 holdout_May-Jun baseline_all      3580         -3.211      0.706    166      -2.846           25.5        0.706
 USD_CAD london long           h60 trail1.5_lock6 holdout_May-Jun     filtered       893         -2.786      0.717     71      -1.768           23.0        0.717
 USD_CAD london long           h60 trail1.5_lock6 holdout_May-Jun baseline_all      3580         -2.988      0.706    171      -2.892           25.0        0.706
 USD_CAD london long      best_h30 trail2.5_lock5       full_2026     filtered      4517         -3.564      0.694    339      -3.893           19.2        0.694
 USD_CAD london long      best_h30 trail2.5_lock5       full_2026 baseline_all     10671         -4.470      0.660    534      -4.518           23.7        0.660
 USD_CAD london long      best_h30 trail1.5_lock6       full_2026     filtered      4517         -3.364      0.694    348      -3.627           19.0        0.694
 USD_CAD london long      best_h30 trail1.5_lock6       full_2026 baseline_all     10671         -4.313      0.660    541      -4.371           23.3        0.660
 USD_CAD london long      best_h30 trail2.5_lock5 holdout_May-Jun     filtered       971         -3.575      0.703     76      -4.011           23.3        0.703
 USD_CAD london long      best_h30 trail2.5_lock5 holdout_May-Jun baseline_all      3580         -3.211      0.706    166      -2.846           25.5        0.706
 USD_CAD london long      best_h30 trail1.5_lock6 holdout_May-Jun     filtered       971         -3.167      0.703     80      -3.968           23.1        0.703
 USD_CAD london long      best_h30 trail1.5_lock6 holdout_May-Jun baseline_all      3580         -2.988      0.706    171      -2.892           25.0        0.706
 EUR_USD london long           h60 trail2.5_lock5       full_2026     filtered      4139         -2.476      0.691    321      -1.646           15.1        0.691
 EUR_USD london long           h60 trail2.5_lock5       full_2026 baseline_all     10684         -3.845      0.651    621      -2.721           21.0        0.651
 EUR_USD london long           h60 trail1.5_lock6       full_2026     filtered      4139         -2.151      0.691    318      -1.343           14.9        0.691
 EUR_USD london long           h60 trail1.5_lock6       full_2026 baseline_all     10684         -3.545      0.651    629      -2.346           20.8        0.651
 EUR_USD london long           h60 trail2.5_lock5 holdout_May-Jun     filtered       587         -3.239      0.654     41      -2.171           17.2        0.654
 EUR_USD london long           h60 trail2.5_lock5 holdout_May-Jun baseline_all      3583         -4.694      0.622    185      -3.578           23.4        0.622
 EUR_USD london long           h60 trail1.5_lock6 holdout_May-Jun     filtered       587         -2.749      0.654     41      -1.893           17.1        0.654
 EUR_USD london long           h60 trail1.5_lock6 holdout_May-Jun baseline_all      3583         -4.416      0.622    193      -2.980           23.1        0.622
 EUR_USD london long      best_h30 trail2.5_lock5       full_2026     filtered      4602         -2.363      0.696    419      -1.485           15.8        0.696
 EUR_USD london long      best_h30 trail2.5_lock5       full_2026 baseline_all     10684         -3.845      0.651    621      -2.721           21.0        0.651
 EUR_USD london long      best_h30 trail1.5_lock6       full_2026     filtered      4602         -2.053      0.696    421      -1.096           15.6        0.696
 EUR_USD london long      best_h30 trail1.5_lock6       full_2026 baseline_all     10684         -3.545      0.651    629      -2.346           20.8        0.651
 EUR_USD london long      best_h30 trail2.5_lock5 holdout_May-Jun     filtered      1051         -3.396      0.660     91      -3.171           18.1        0.660
 EUR_USD london long      best_h30 trail2.5_lock5 holdout_May-Jun baseline_all      3583         -4.694      0.622    185      -3.578           23.4        0.622
 EUR_USD london long      best_h30 trail1.5_lock6 holdout_May-Jun     filtered      1051         -2.964      0.660     94      -2.703           17.9        0.660
 EUR_USD london long      best_h30 trail1.5_lock6 holdout_May-Jun baseline_all      3583         -4.416      0.622    193      -2.980           23.1        0.622
EUR_USD london short           h60 trail2.5_lock5       full_2026     filtered      4139         -2.559      0.694    321      -2.158           15.7        0.694
EUR_USD london short           h60 trail2.5_lock5       full_2026 baseline_all     10684         -3.592      0.658    624      -3.520           20.8        0.658
EUR_USD london short           h60 trail1.5_lock6       full_2026     filtered      4139         -2.377      0.694    325      -1.612           15.5        0.694
EUR_USD london short           h60 trail1.5_lock6       full_2026 baseline_all     10684         -3.402      0.658    630      -3.109           20.6        0.658
EUR_USD london short           h60 trail2.5_lock5 holdout_May-Jun     filtered       587         -2.816      0.685     41      -2.371           16.5        0.685
EUR_USD london short           h60 trail2.5_lock5 holdout_May-Jun baseline_all      3583         -3.564      0.661    182      -4.055           22.3        0.661
EUR_USD london short           h60 trail1.5_lock6 holdout_May-Jun     filtered       587         -2.699      0.685     42      -1.986           16.3        0.685
EUR_USD london short           h60 trail1.5_lock6 holdout_May-Jun baseline_all      3583         -3.300      0.661    184      -3.765           22.0        0.661
EUR_USD london short      best_h30 trail2.5_lock5       full_2026     filtered      4475         -2.875      0.681    406      -2.762           16.5        0.681
EUR_USD london short      best_h30 trail2.5_lock5       full_2026 baseline_all     10684         -3.592      0.658    624      -3.520           20.8        0.658
EUR_USD london short      best_h30 trail1.5_lock6       full_2026     filtered      4475         -2.775      0.681    408      -2.239           16.2        0.681
EUR_USD london short      best_h30 trail1.5_lock6       full_2026 baseline_all     10684         -3.402      0.658    630      -3.109           20.6        0.658
EUR_USD london short      best_h30 trail2.5_lock5 holdout_May-Jun     filtered       924         -3.646      0.657     90      -2.924           18.7        0.657
EUR_USD london short      best_h30 trail2.5_lock5 holdout_May-Jun baseline_all      3583         -3.564      0.661    182      -4.055           22.3        0.661
EUR_USD london short      best_h30 trail1.5_lock6 holdout_May-Jun     filtered       924         -3.474      0.657     89      -2.557           18.4        0.657
EUR_USD london short      best_h30 trail1.5_lock6 holdout_May-Jun baseline_all      3583         -3.300      0.661    184      -3.765           22.0        0.661
     EUR_JPY ny long           h60 trail2.5_lock5       full_2026     filtered      5644         -2.372      0.734    739      -2.249           11.9        0.734
     EUR_JPY ny long           h60 trail2.5_lock5       full_2026 baseline_all     13758         -5.080      0.651   1027      -3.291           19.9        0.651
     EUR_JPY ny long           h60 trail1.5_lock6       full_2026     filtered      5644         -2.005      0.734    739      -1.947           11.8        0.734
     EUR_JPY ny long           h60 trail1.5_lock6       full_2026 baseline_all     13758         -4.759      0.651   1029      -3.046           19.7        0.651
     EUR_JPY ny long           h60 trail2.5_lock5 holdout_May-Jun     filtered      1073         -5.062      0.648    152      -3.937           14.9        0.648
     EUR_JPY ny long           h60 trail2.5_lock5 holdout_May-Jun baseline_all      4616         -7.578      0.570    270      -5.497           25.1        0.570
     EUR_JPY ny long           h60 trail1.5_lock6 holdout_May-Jun     filtered      1073         -4.811      0.648    148      -3.811           14.8        0.648
     EUR_JPY ny long           h60 trail1.5_lock6 holdout_May-Jun baseline_all      4616         -7.316      0.570    268      -5.535           24.9        0.570
     EUR_JPY ny long      best_h30 trail2.5_lock5       full_2026     filtered      5644         -2.372      0.734    739      -2.249           11.9        0.734
     EUR_JPY ny long      best_h30 trail2.5_lock5       full_2026 baseline_all     13758         -5.080      0.651   1027      -3.291           19.9        0.651
     EUR_JPY ny long      best_h30 trail1.5_lock6       full_2026     filtered      5644         -2.005      0.734    739      -1.947           11.8        0.734
     EUR_JPY ny long      best_h30 trail1.5_lock6       full_2026 baseline_all     13758         -4.759      0.651   1029      -3.046           19.7        0.651
     EUR_JPY ny long      best_h30 trail2.5_lock5 holdout_May-Jun     filtered      1073         -5.062      0.648    152      -3.937           14.9        0.648
     EUR_JPY ny long      best_h30 trail2.5_lock5 holdout_May-Jun baseline_all      4616         -7.578      0.570    270      -5.497           25.1        0.570
     EUR_JPY ny long      best_h30 trail1.5_lock6 holdout_May-Jun     filtered      1073         -4.811      0.648    148      -3.811           14.8        0.648
     EUR_JPY ny long      best_h30 trail1.5_lock6 holdout_May-Jun baseline_all      4616         -7.316      0.570    268      -5.535           24.9        0.570

## 6. XREF vs DEAD-ENTRY SCREENING (from v1, unchanged)
Rising under oscillation target: atr_5m (44 cells), range_5bar (37), q_yzv_m5 (34), range_12bar (34), atr_1h (21), bb_std (14)
Dropping: q_bbwp_m5 (48), ema20_1h_dist (48), h1_ret_1bar (48), atr_d_pips (45), bb_width (35)
Interpretation: 60-min-window intrabar volatility replaces daily-scale volatility percentile and directional momentum.

## FILES (v2)
- cell_base_rates_multihorizon.csv
- indicator_screening_multihorizon.csv
- drift_analysis_multihorizon.csv
- top5_per_cell_per_horizon.csv
- wire_ready_range_table_multihorizon.csv
- cross_horizon_comparison.csv
- base_rate_shrink_by_horizon.csv
- top10_rh_rate_by_horizon.csv
- sequential_sanity_v2_validated.csv
- reconciliation_crude_vs_validated.csv
- v1 files retained; v1 sequential_sanity.csv EV column SUPERSEDED by reconciliation table above.