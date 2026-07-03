# RATCHET-EV FIRST-PASSAGE STUDY — v2 (UNCONDITIONAL, look-ahead corrected)
Generated: 2026-07-03T10:05:01.540893+00:00
Device: Mac Mini (CPYQTH294R)

## ⚠️ CORRECTION vs v1
v1 filtered bars to `direction == label` where `label = sign(fwd_ret_pips)` =
sign of the FORWARD 1H return (v5_qtl_8yr_features.py L299-300). That conditioned
entries on the future outcome — v1's per-cell EVs were circular and are RETRACTED.
v1 table preserved in ratchet_ev_cells_CONDITIONED_lookahead.csv for reference only.

This version: EVERY bar, BOTH directions simulated, no label filter.
Exit mechanics unchanged: SL -20p, trigger 7.5p, trail/step 2.5p, no TP,
48-bar horizon, ADVERSE-FIRST intrabar ordering (pessimistic; bias vs optimistic
= -0.719p/bar on AUD_JPY 2026).

## Unconditional Classification Counts (net-of-spread, +0.5p threshold)

- **DEAD_CELL**: 22 pair x session slots

## Unconditional 44-Cell Table (2026, net-of-spread)

| Cell | EV_L uncond | EV_S uncond | Class uncond | EV_L cond(v1) | EV_S cond(v1) | P(Eng_L) | P(InitStop_L) | %PIERCE_DEAD_L |
|------|---:|---:|---|---:|---:|:---:|:---:|:---:|
| AUD_JPY/asia | -4.54 | -4.07 | DEAD_CELL | +2.26 | +3.58 | 0.683 | 0.243 | 15.9% |
| AUD_JPY/london | -3.84 | -4.64 | DEAD_CELL | +2.83 | +3.48 | 0.710 | 0.224 | 15.5% |
| AUD_USD/asia | -6.33 | -6.13 | DEAD_CELL | +0.38 | +0.71 | 0.568 | 0.162 | 5.8% |
| AUD_USD/london | -4.16 | -5.56 | DEAD_CELL | +2.32 | +1.55 | 0.640 | 0.175 | 8.2% |
| AUD_USD/ny | -8.57 | -6.14 | DEAD_CELL | -1.94 | +0.24 | 0.473 | 0.142 | 8.2% |
| EUR_JPY/asia | -4.28 | -4.00 | DEAD_CELL | +2.19 | +3.32 | 0.680 | 0.221 | 13.8% |
| EUR_JPY/london | -3.25 | -2.94 | DEAD_CELL | +3.55 | +4.85 | 0.710 | 0.247 | 18.9% |
| EUR_JPY/ny | -5.13 | -4.42 | DEAD_CELL | +1.33 | +2.85 | 0.650 | 0.178 | 11.9% |
| EUR_USD/asia | -7.89 | -6.91 | DEAD_CELL | -1.31 | -1.27 | 0.514 | 0.127 | 3.3% |
| EUR_USD/london | -3.77 | -3.54 | DEAD_CELL | +3.82 | +3.87 | 0.649 | 0.218 | 10.8% |
| EUR_USD/ny | -7.60 | -5.59 | DEAD_CELL | -0.56 | +0.78 | 0.505 | 0.144 | 9.6% |
| GBP_USD/asia | -5.78 | -4.80 | DEAD_CELL | +1.20 | +1.23 | 0.606 | 0.184 | 6.4% |
| GBP_USD/london | -2.60 | -3.04 | DEAD_CELL | +4.62 | +4.83 | 0.702 | 0.261 | 18.0% |
| GBP_USD/ny | -5.79 | -3.57 | DEAD_CELL | +2.09 | +3.17 | 0.588 | 0.196 | 14.1% |
| USD_CAD/asia | -8.47 | -10.48 | DEAD_CELL | -2.94 | -4.48 | 0.520 | 0.080 | 2.1% |
| USD_CAD/london | -4.46 | -5.08 | DEAD_CELL | +2.11 | +1.94 | 0.660 | 0.194 | 8.1% |
| USD_CAD/ny | -6.60 | -8.21 | DEAD_CELL | -0.02 | -0.81 | 0.583 | 0.124 | 9.4% |
| USD_CHF/london | -5.05 | -5.38 | DEAD_CELL | +1.89 | +1.63 | 0.632 | 0.174 | 7.5% |
| USD_CHF/ny | -8.07 | -9.69 | DEAD_CELL | -1.64 | -2.78 | 0.528 | 0.106 | 7.1% |
| USD_JPY/asia | -3.35 | -3.20 | DEAD_CELL | +2.92 | +3.88 | 0.650 | 0.199 | 13.3% |
| USD_JPY/london | -2.84 | -2.30 | DEAD_CELL | +3.74 | +4.91 | 0.663 | 0.216 | 16.3% |
| USD_JPY/ny | -2.89 | -4.58 | DEAD_CELL | +3.00 | +3.65 | 0.656 | 0.176 | 12.1% |

## Movement-After-Filter Check
Question: does any cell + at-entry indicator-state deliver > +0.5p net BOTH directions
on the unconditional population (no future knowledge)?

**NONE FOUND.** No cell/indicator-state combination was profitable both directions net-of-spread.

## Unconditional Filter Candidates (per direction, in-sample optimized)

| Cell | Feature | Keep Range | EV Before | EV After | Uplift | n_kept | AUC | Drift | On View |
|---|---|---|---:|---:|---:|---:|---|---|---|
| USD_JPY/london/short | htf_pct_60 | [0.018, 9999.0] | -2.30 | +0.41 | +2.71 | 4425 | 0.598 | PERSISTENT | True |
| USD_JPY/ny/long | q_kc_up_dist_pips | [-9999.0, -8.5502] | -2.89 | +0.06 | +2.95 | 6275 | 0.640 | REGIME | True |
| USD_JPY/asia/short | atr_d_pips | [111.6407, 9999.0] | -3.20 | -0.35 | +2.85 | 5627 | 0.679 | REGIME | True |
| USD_JPY/london/long | q_kc_up_dist_pips | [-9999.0, -8.904] | -2.84 | -0.58 | +2.26 | 4891 | 0.595 | PERSISTENT | True |
| USD_JPY/asia/long | q_obv | [-9999.0, 1455684.5] | -3.35 | -0.95 | +2.40 | 6235 | 0.692 | PERSISTENT | False |
| GBP_USD/london/long | atr_d_pips | [91.4859, 9999.0] | -2.60 | -1.18 | +1.42 | 4933 | 0.565 | PERSISTENT | True |
| AUD_JPY/asia/short | q_obv | [1984426.2, 9999.0] | -4.07 | -1.56 | +2.51 | 5001 | 0.632 | PERSISTENT | False |
| EUR_JPY/london/short | q_yzv_m5 | [0.0002, 9999.0] | -2.94 | -1.79 | +1.15 | 4898 | 0.635 | PERSISTENT | False |
| EUR_USD/london/long | atr_1h | [9.8706, 9999.0] | -3.77 | -1.80 | +1.97 | 7614 | 0.680 | PERSISTENT | True |
| EUR_JPY/london/long | atr_1h | [19.107, 9999.0] | -3.25 | -1.96 | +1.29 | 4902 | 0.616 | PERSISTENT | True |
| USD_JPY/ny/short | atr_d_pips | [105.8, 9999.0] | -4.58 | -2.09 | +2.50 | 6979 | 0.634 | PERSISTENT | True |
| GBP_USD/london/short | pdh_dist_atr_pct | [-0.3389, 9999.0] | -3.04 | -2.14 | +0.90 | 4355 | 0.549 | PERSISTENT | True |
| GBP_USD/ny/short | atr_d_pips | [90.026, 9999.0] | -3.57 | -2.16 | +1.41 | 7719 | 0.557 | PERSISTENT | True |
| EUR_JPY/asia/short | adr_consumed | [0.8578, 9999.0] | -4.00 | -2.19 | +1.81 | 6294 | 0.606 | PERSISTENT | True |
| AUD_JPY/london/long | adr_consumed | [0.9496, 9999.0] | -3.84 | -2.26 | +1.58 | 4951 | 0.550 | PERSISTENT | True |
| EUR_USD/london/short | q_kurtosis_m5 | [-9999.0, -0.5198] | -3.54 | -2.27 | +1.27 | 4889 | 0.516 | PERSISTENT | False |
| AUD_USD/london/long | atr_d_pips | [66.1416, 9999.0] | -4.16 | -2.36 | +1.80 | 4930 | 0.642 | REGIME | True |
| AUD_JPY/asia/long | q_obv | [-9999.0, 1923331.0] | -4.54 | -2.50 | +2.04 | 6251 | 0.559 | PERSISTENT | False |
| USD_CAD/london/long | adr_consumed | [-9999.0, 0.8449] | -4.46 | -2.70 | +1.76 | 4410 | 0.605 | PERSISTENT | True |
| EUR_JPY/ny/long | q_dc_up_dist_pips | [-9999.0, -9.2] | -5.13 | -2.72 | +2.41 | 6304 | 0.601 | PERSISTENT | False |
| USD_CHF/london/short | atr_1h | [9.5586, 9999.0] | -5.38 | -2.73 | +2.65 | 4892 | 0.671 | REGIME | True |
| GBP_USD/ny/long | q_yzv_m5 | [0.0003, 9999.0] | -5.79 | -2.89 | +2.90 | 6975 | 0.700 | PERSISTENT | False |
| EUR_JPY/asia/long | q_adl | [-9999.0, 3019854.4061] | -4.28 | -2.98 | +1.30 | 6240 | 0.658 | PERSISTENT | False |
| GBP_USD/asia/short | adr_consumed | [0.9849, 9999.0] | -4.80 | -3.01 | +1.79 | 5052 | 0.538 | PERSISTENT | True |
| EUR_JPY/ny/short | atr_1h | [19.575, 9999.0] | -4.42 | -3.09 | +1.34 | 6290 | 0.632 | PERSISTENT | True |
| USD_CAD/london/short | q_adosc | [79.3357, 9999.0] | -5.08 | -3.11 | +1.97 | 4340 | 0.567 | PERSISTENT | False |
| AUD_JPY/london/short | q_yzv_m5 | [0.0003, 9999.0] | -4.64 | -3.13 | +1.51 | 5439 | 0.694 | PERSISTENT | False |
| AUD_USD/london/short | atr_1h | [11.1824, 9999.0] | -5.56 | -3.25 | +2.31 | 4886 | 0.734 | PERSISTENT | True |
| EUR_USD/ny/long | atr_5m | [4.2552, 9999.0] | -7.60 | -3.44 | +4.16 | 6265 | 0.735 | PERSISTENT | True |
| EUR_USD/ny/short | q_atrn_m5 | [0.6146, 9999.0] | -5.59 | -3.53 | +2.07 | 6265 | 0.692 | PERSISTENT | False |

## Broker Anchor (unchanged from v1 — actual trades, not conditioned)
- n=110, Pearson r=0.724, MAD=5.25p — simulation tracks the live ratchet exit well.

## Methodology Notes
- All EV net of 2x typical one-way spread per pair.
- Filter thresholds optimized in-sample on 2026 (percentile grid, EV-uplift objective,
  good-sacrifice cap 60%) — figures are optimistic upper bounds pending walk-forward.
- Feature syncs and geometry rates computed on the unconditional population.
- v1 conditioned numbers: ratchet_ev_cells_CONDITIONED_lookahead.csv (RETRACTED for decisions).
