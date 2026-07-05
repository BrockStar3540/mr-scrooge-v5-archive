# Ratchet Profile Study — per-cell excursion geometry (2026 corpus, walk-forward)

24 cells, 2026 bars, train Jan-Apr / test May-Jul, 30m-thinned sign guard. Balanced bar = |L60|<1/3 where L=(up-dn)/(up+dn).

## Q1 — signed direction from features (lopsidedness -> direction?)
Robust signed-L relationships: 0 of 144 tested.
**NONE cleared the bar — confirms 07-04 direction-horizon verdict (WHEN not WHICH WAY).**

## Q1b — one-sidedness |L| scaling (trendiness magnitude, unsigned)
none robust

## Q2 — total travel R60 scaling on balanced bars (ratchet distance knob)
| pair    | sess   | feature           | target   |   rho_train |   rho_test |   rho_thin | robust   |
|:--------|:-------|:------------------|:---------|------------:|-----------:|-----------:|:---------|
| AUD_JPY | asia   | atr_5m            | travel   |       0.634 |      0.396 |      0.594 | True     |
| AUD_JPY | asia   | q_kc_up_dist_pips | travel   |      -0.359 |     -0.243 |     -0.347 | True     |
| AUD_JPY | asia   | atr_conc          | travel   |       0.318 |      0.268 |      0.292 | True     |
| AUD_JPY | asia   | rvol_5bar         | travel   |       0.26  |      0.469 |      0.316 | True     |
| AUD_JPY | asia   | q_willr_m5        | travel   |      -0.133 |     -0.084 |     -0.147 | True     |
| AUD_JPY | asia   | atr_h1_relative   | travel   |       0.242 |      0.179 |      0.266 | True     |
| AUD_JPY | london | atr_5m            | travel   |       0.596 |      0.541 |      0.59  | True     |
| AUD_JPY | london | q_kc_up_dist_pips | travel   |      -0.213 |     -0.299 |     -0.229 | True     |
| AUD_JPY | london | atr_conc          | travel   |       0.137 |      0.217 |      0.214 | True     |
| AUD_JPY | london | rvol_5bar         | travel   |       0.162 |      0.254 |      0.216 | True     |
| AUD_JPY | london | atr_h1_relative   | travel   |       0.183 |      0.306 |      0.15  | True     |
| AUD_JPY | ny     | atr_5m            | travel   |       0.648 |      0.622 |      0.704 | True     |
| AUD_JPY | ny     | q_kc_up_dist_pips | travel   |      -0.35  |     -0.253 |     -0.401 | True     |
| AUD_JPY | ny     | atr_conc          | travel   |       0.451 |      0.515 |      0.522 | True     |
| AUD_JPY | ny     | rvol_5bar         | travel   |       0.338 |      0.366 |      0.356 | True     |
| AUD_JPY | ny     | atr_h1_relative   | travel   |       0.189 |      0.197 |      0.186 | True     |
| AUD_USD | asia   | atr_5m            | travel   |       0.635 |      0.368 |      0.58  | True     |
| AUD_USD | asia   | q_kc_up_dist_pips | travel   |      -0.308 |     -0.219 |     -0.27  | True     |
| AUD_USD | asia   | atr_conc          | travel   |       0.321 |      0.298 |      0.281 | True     |
| AUD_USD | asia   | rvol_5bar         | travel   |       0.336 |      0.424 |      0.358 | True     |
| AUD_USD | asia   | atr_h1_relative   | travel   |       0.243 |      0.096 |      0.221 | True     |
| AUD_USD | london | atr_5m            | travel   |       0.707 |      0.542 |      0.716 | True     |
| AUD_USD | london | q_kc_up_dist_pips | travel   |      -0.303 |     -0.152 |     -0.224 | True     |
| AUD_USD | london | atr_conc          | travel   |       0.13  |      0.263 |      0.112 | True     |
| AUD_USD | london | rvol_5bar         | travel   |       0.173 |      0.234 |      0.202 | True     |
| AUD_USD | london | atr_h1_relative   | travel   |       0.232 |      0.373 |      0.226 | True     |
| AUD_USD | ny     | atr_5m            | travel   |       0.72  |      0.699 |      0.736 | True     |
| AUD_USD | ny     | q_kc_up_dist_pips | travel   |      -0.391 |     -0.335 |     -0.371 | True     |
| AUD_USD | ny     | atr_conc          | travel   |       0.631 |      0.668 |      0.634 | True     |
| AUD_USD | ny     | rvol_5bar         | travel   |       0.488 |      0.451 |      0.457 | True     |
| AUD_USD | ny     | atr_h1_relative   | travel   |       0.102 |      0.23  |      0.128 | True     |
| EUR_JPY | asia   | atr_5m            | travel   |       0.609 |      0.454 |      0.629 | True     |
| EUR_JPY | asia   | q_kc_up_dist_pips | travel   |      -0.321 |     -0.128 |     -0.312 | True     |
| EUR_JPY | asia   | atr_conc          | travel   |       0.335 |      0.2   |      0.315 | True     |
| EUR_JPY | asia   | rvol_5bar         | travel   |       0.297 |      0.406 |      0.293 | True     |
| EUR_JPY | asia   | atr_h1_relative   | travel   |       0.234 |      0.118 |      0.206 | True     |
| EUR_JPY | london | atr_5m            | travel   |       0.539 |      0.601 |      0.616 | True     |
| EUR_JPY | london | q_kc_up_dist_pips | travel   |      -0.304 |     -0.394 |     -0.319 | True     |
| EUR_JPY | london | atr_conc          | travel   |       0.185 |      0.135 |      0.204 | True     |
| EUR_JPY | london | rvol_5bar         | travel   |       0.268 |      0.144 |      0.269 | True     |
| EUR_JPY | london | atr_h1_relative   | travel   |       0.284 |      0.279 |      0.281 | True     |
| EUR_JPY | ny     | atr_5m            | travel   |       0.632 |      0.582 |      0.65  | True     |
| EUR_JPY | ny     | q_kc_up_dist_pips | travel   |      -0.307 |     -0.278 |     -0.279 | True     |
| EUR_JPY | ny     | atr_conc          | travel   |       0.408 |      0.424 |      0.428 | True     |
| EUR_JPY | ny     | rvol_5bar         | travel   |       0.301 |      0.351 |      0.297 | True     |
| EUR_JPY | ny     | atr_h1_relative   | travel   |       0.204 |      0.154 |      0.171 | True     |
| EUR_USD | asia   | atr_5m            | travel   |       0.535 |      0.42  |      0.485 | True     |
| EUR_USD | asia   | q_kc_up_dist_pips | travel   |      -0.17  |     -0.103 |     -0.131 | True     |
| EUR_USD | asia   | atr_conc          | travel   |       0.237 |      0.317 |      0.199 | True     |
| EUR_USD | asia   | rvol_5bar         | travel   |       0.364 |      0.409 |      0.331 | True     |
| EUR_USD | asia   | atr_h1_relative   | travel   |       0.255 |      0.137 |      0.226 | True     |
| EUR_USD | london | atr_5m            | travel   |       0.594 |      0.429 |      0.547 | True     |
| EUR_USD | london | q_kc_up_dist_pips | travel   |      -0.196 |     -0.128 |     -0.21  | True     |
| EUR_USD | london | rvol_5bar         | travel   |       0.225 |      0.263 |      0.203 | True     |
| EUR_USD | london | atr_h1_relative   | travel   |       0.314 |      0.235 |      0.273 | True     |
| EUR_USD | ny     | atr_5m            | travel   |       0.715 |      0.704 |      0.74  | True     |
| EUR_USD | ny     | q_kc_up_dist_pips | travel   |      -0.284 |     -0.35  |     -0.288 | True     |
| EUR_USD | ny     | atr_conc          | travel   |       0.627 |      0.689 |      0.677 | True     |
| EUR_USD | ny     | rvol_5bar         | travel   |       0.466 |      0.508 |      0.461 | True     |
| EUR_USD | ny     | atr_h1_relative   | travel   |       0.111 |      0.204 |      0.138 | True     |
| GBP_USD | asia   | atr_5m            | travel   |       0.51  |      0.278 |      0.42  | True     |
| GBP_USD | asia   | q_kc_up_dist_pips | travel   |      -0.197 |     -0.079 |     -0.161 | True     |
| GBP_USD | asia   | atr_conc          | travel   |       0.315 |      0.232 |      0.231 | True     |
| GBP_USD | asia   | rvol_5bar         | travel   |       0.304 |      0.441 |      0.332 | True     |
| GBP_USD | london | atr_5m            | travel   |       0.55  |      0.524 |      0.536 | True     |
| GBP_USD | london | q_kc_up_dist_pips | travel   |      -0.188 |     -0.253 |     -0.185 | True     |
| GBP_USD | london | rvol_5bar         | travel   |       0.186 |      0.274 |      0.258 | True     |
| GBP_USD | london | atr_h1_relative   | travel   |       0.291 |      0.337 |      0.252 | True     |
| GBP_USD | ny     | atr_5m            | travel   |       0.724 |      0.644 |      0.714 | True     |
| GBP_USD | ny     | q_kc_up_dist_pips | travel   |      -0.298 |     -0.292 |     -0.322 | True     |
| GBP_USD | ny     | atr_conc          | travel   |       0.668 |      0.614 |      0.655 | True     |
| GBP_USD | ny     | rvol_5bar         | travel   |       0.474 |      0.396 |      0.468 | True     |
| GBP_USD | ny     | atr_h1_relative   | travel   |       0.149 |      0.153 |      0.138 | True     |
| USD_CAD | asia   | atr_5m            | travel   |       0.496 |      0.267 |      0.455 | True     |
| USD_CAD | asia   | atr_conc          | travel   |       0.245 |      0.187 |      0.205 | True     |
| USD_CAD | asia   | rvol_5bar         | travel   |       0.311 |      0.384 |      0.328 | True     |
| USD_CAD | asia   | atr_h1_relative   | travel   |       0.224 |      0.102 |      0.209 | True     |
| USD_CAD | london | atr_5m            | travel   |       0.537 |      0.416 |      0.533 | True     |
| USD_CAD | london | q_kc_up_dist_pips | travel   |      -0.161 |     -0.083 |     -0.238 | True     |
| USD_CAD | london | atr_conc          | travel   |       0.141 |      0.28  |      0.176 | True     |
| USD_CAD | london | rvol_5bar         | travel   |       0.136 |      0.172 |      0.233 | True     |
| USD_CAD | london | atr_h1_relative   | travel   |       0.253 |      0.277 |      0.249 | True     |
| USD_CAD | ny     | atr_5m            | travel   |       0.627 |      0.571 |      0.642 | True     |
| USD_CAD | ny     | q_kc_up_dist_pips | travel   |      -0.233 |     -0.175 |     -0.228 | True     |
| USD_CAD | ny     | atr_conc          | travel   |       0.55  |      0.59  |      0.561 | True     |
| USD_CAD | ny     | rvol_5bar         | travel   |       0.496 |      0.465 |      0.495 | True     |
| USD_CHF | asia   | atr_5m            | travel   |       0.472 |      0.211 |      0.428 | True     |
| USD_CHF | asia   | atr_conc          | travel   |       0.224 |      0.176 |      0.213 | True     |
| USD_CHF | asia   | rvol_5bar         | travel   |       0.208 |      0.329 |      0.233 | True     |
| USD_CHF | london | atr_5m            | travel   |       0.498 |      0.377 |      0.462 | True     |
| USD_CHF | london | atr_conc          | travel   |       0.116 |      0.184 |      0.175 | True     |
| USD_CHF | london | rvol_5bar         | travel   |       0.187 |      0.247 |      0.208 | True     |
| USD_CHF | london | atr_h1_relative   | travel   |       0.302 |      0.246 |      0.283 | True     |
| USD_CHF | ny     | atr_5m            | travel   |       0.596 |      0.561 |      0.632 | True     |
| USD_CHF | ny     | q_kc_up_dist_pips | travel   |      -0.253 |     -0.221 |     -0.275 | True     |
| USD_CHF | ny     | atr_conc          | travel   |       0.532 |      0.537 |      0.553 | True     |
| USD_CHF | ny     | rvol_5bar         | travel   |       0.36  |      0.325 |      0.372 | True     |
| USD_CHF | ny     | atr_h1_relative   | travel   |       0.112 |      0.101 |      0.11  | True     |
| USD_JPY | asia   | atr_5m            | travel   |       0.583 |      0.549 |      0.721 | True     |
| USD_JPY | asia   | q_kc_up_dist_pips | travel   |      -0.238 |     -0.25  |     -0.342 | True     |
| USD_JPY | asia   | atr_conc          | travel   |       0.351 |      0.125 |      0.302 | True     |
| USD_JPY | asia   | rvol_5bar         | travel   |       0.349 |      0.302 |      0.264 | True     |
| USD_JPY | asia   | atr_h1_relative   | travel   |       0.23  |      0.251 |      0.205 | True     |
| USD_JPY | london | atr_5m            | travel   |       0.588 |      0.729 |      0.761 | True     |
| USD_JPY | london | q_kc_up_dist_pips | travel   |      -0.308 |     -0.473 |     -0.479 | True     |
| USD_JPY | london | atr_conc          | travel   |       0.237 |      0.274 |      0.282 | True     |
| USD_JPY | london | rvol_5bar         | travel   |       0.209 |      0.139 |      0.152 | True     |
| USD_JPY | london | atr_h1_relative   | travel   |       0.355 |      0.287 |      0.308 | True     |
| USD_JPY | ny     | atr_5m            | travel   |       0.655 |      0.7   |      0.739 | True     |
| USD_JPY | ny     | q_kc_up_dist_pips | travel   |      -0.393 |     -0.377 |     -0.464 | True     |
| USD_JPY | ny     | atr_conc          | travel   |       0.525 |      0.318 |      0.458 | True     |
| USD_JPY | ny     | rvol_5bar         | travel   |       0.438 |      0.24  |      0.34  | True     |
| USD_JPY | ny     | atr_h1_relative   | travel   |       0.209 |      0.202 |      0.206 | True     |

## Q3 — per-cell ratchet class
growth = med R240 / med R60 (how much the move extends past the first hour); tercile cuts at 2.09/2.27. QUICK-SLICE requires med up60 >= RT cost + 2p. Broker anchor: winners' median duration/MFE from the 230-trade table (small n — anchor, not proof).

| pair    | sess   |   n2026 |   balanced_share |   med_up60 |   med_R60 |   med_R240 |   growth |   p75_up240 |   rt_cost | klass       |   n_w |   med_dur_w |   med_mfe_w |
|:--------|:-------|--------:|-----------------:|-----------:|----------:|-----------:|---------:|------------:|----------:|:------------|------:|------------:|------------:|
| USD_CAD | ny     |   13957 |            0.288 |        5.2 |      11.8 |       20.5 |     1.74 |       16.9  |      1.8  | QUICK-SLICE |     6 |        56.5 |        8.7  |
| USD_CHF | ny     |   13870 |            0.3   |        4.3 |       9.7 |       17.5 |     1.8  |       14.3  |      1.6  | QUICK-SLICE |     6 |        71   |        9.55 |
| EUR_USD | ny     |   13923 |            0.29  |        4.5 |      11.4 |       20.7 |     1.82 |       15.4  |      1.6  | QUICK-SLICE |   nan |       nan   |      nan    |
| GBP_USD | ny     |   13950 |            0.291 |        6.2 |      15.3 |       27.8 |     1.82 |       20.4  |      1.95 | QUICK-SLICE |    16 |        26.5 |       10.45 |
| EUR_JPY | ny     |   13969 |            0.311 |        6.7 |      15   |       29.1 |     1.94 |       22.8  |      2.7  | QUICK-SLICE |    10 |        61.5 |       10.8  |
| AUD_USD | ny     |   13913 |            0.286 |        4.1 |      10.3 |       20.1 |     1.95 |       15.3  |      1.35 | QUICK-SLICE |   nan |       nan   |      nan    |
| EUR_JPY | london |    9318 |            0.285 |        8.2 |      18.9 |       38.2 |     2.02 |       30    |      2.7  | QUICK-SLICE |     2 |       221   |        6.9  |
| AUD_JPY | ny     |   13949 |            0.289 |        6.2 |      14.4 |       29.6 |     2.06 |       23.2  |      2.35 | QUICK-SLICE |     1 |        61   |        5.3  |
| USD_JPY | london |    9304 |            0.283 |        6.6 |      16.3 |       37.1 |     2.28 |       26.3  |      1.6  | RUNNER      |     5 |       183   |        8.9  |
| USD_JPY | asia   |   14036 |            0.278 |        6   |      14.7 |       33.6 |     2.29 |       25.6  |      1.6  | RUNNER      |    15 |        40   |        9.1  |
| AUD_USD | london |    9289 |            0.264 |        5   |      11.4 |       26.2 |     2.3  |       21.7  |      1.35 | RUNNER      |     8 |       146   |       10.95 |
| EUR_JPY | asia   |   14047 |            0.285 |        6.6 |      15.4 |       35.7 |     2.32 |       28.2  |      2.7  | RUNNER      |     4 |        44.5 |       10.25 |
| EUR_USD | asia   |   14004 |            0.274 |        3.5 |       8.6 |       20   |     2.33 |       15.6  |      1.6  | RUNNER      |     2 |       148   |        8.35 |
| USD_CAD | london |    9291 |            0.275 |        5.1 |      11.6 |       27.4 |     2.36 |       21.1  |      1.8  | RUNNER      |     4 |         2.5 |       11.35 |
| GBP_USD | asia   |   14026 |            0.278 |        4.6 |      11.1 |       26.4 |     2.38 |       20.5  |      1.95 | RUNNER      |     4 |       210.5 |       11.55 |
| USD_CHF | asia   |   13987 |            0.27  |        3.1 |       6.9 |       16.5 |     2.39 |       13    |      1.6  | RUNNER      |     1 |        78   |        4.3  |
| USD_JPY | ny     |   13945 |            0.291 |        6.3 |      14.5 |       30.4 |     2.1  |       24.5  |      1.6  | STANDARD    |     2 |       144.5 |       18.05 |
| AUD_USD | asia   |   14019 |            0.266 |        4.1 |       9.9 |       21.5 |     2.17 |       16.8  |      1.35 | STANDARD    |     5 |        70   |        5.2  |
| AUD_JPY | asia   |   14068 |            0.283 |        6.8 |      15.8 |       34.4 |     2.18 |       26.5  |      2.35 | STANDARD    |    16 |        32.5 |        9    |
| USD_CAD | asia   |   13974 |            0.285 |        3.4 |       7.6 |       16.7 |     2.2  |       13.7  |      1.8  | STANDARD    |     4 |       279.5 |       10.9  |
| USD_CHF | london |    9291 |            0.268 |        4.7 |      11.1 |       24.4 |     2.2  |       18.35 |      1.6  | STANDARD    |     5 |        81   |        8.8  |
| AUD_JPY | london |    9313 |            0.283 |        6.9 |      16.2 |       35.8 |     2.21 |       28.8  |      2.35 | STANDARD    |     1 |       109   |       17.6  |
| GBP_USD | london |    9321 |            0.276 |        7.9 |      18.3 |       40.8 |     2.23 |       33.1  |      1.95 | STANDARD    |     2 |        53   |       17.6  |
| EUR_USD | london |    9300 |            0.284 |        5.6 |      13.2 |       29.8 |     2.26 |       23.4  |      1.6  | STANDARD    |     6 |        48   |        8.35 |