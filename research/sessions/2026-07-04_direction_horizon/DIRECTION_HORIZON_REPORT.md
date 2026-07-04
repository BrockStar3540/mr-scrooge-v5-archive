# DIRECTION HORIZON REPORT — short-horizon direction test

Run: 2026-07-04 01:58 | Train 2026-01-01..2026-04-30 | Validate 2026-05-01..2026-07-03 | 78 features | N_PERMS=10

Target: dir_h = 1[(mfe_long_h - mae_long_h) > 0], h in {20,30,60}m. One model per pair x session (24 cells).


60m recompute vs stored sign_asym_60 match rates: {"AUD_JPY": 0.9986, "AUD_USD": 0.9981, "EUR_JPY": 0.9987, "EUR_USD": 0.9981, "GBP_USD": 0.9985, "USD_CAD": 0.9984, "USD_CHF": 0.9979, "USD_JPY": 0.9986}


## Excluded columns (30)

`asym_240, asym_60, best_mfe_240, best_mfe_60, close, dead_long_60, dead_short_60, dn_excursion_240, dn_excursion_60, fwd_ret_pips, high, label, low, mae_long_240, mae_long_60, mae_short_240, mae_short_60, mfe_long_240, mfe_long_60, mfe_short_240, mfe_short_60, open, q_super_dist_h1, session, session_upper, sign_asym_240, sign_asym_60, up_excursion_240, up_excursion_60, volume`


## 1. Horizon win counts (the headline)

- 20m > 60m: **8/24** (median AUC edge -0.0083)
- 30m > 60m: **8/24** (median AUC edge -0.0088)
- 20m > 30m: **9/24** (median AUC edge -0.0043)

- h20: median val AUC 0.5069, validated (floor+baseline) 8/24, median floor_p95 0.5193
- h30: median val AUC 0.5158, validated (floor+baseline) 7/24, median floor_p95 0.5200
- h60: median val AUC 0.5212, validated (floor+baseline) 7/24, median floor_p95 0.5252

## 2. Per-cell AUC table

| cell | AUC 20m | AUC 30m | AUC 60m | 20-60 | val20 | val30 | val60 |
|---|---|---|---|---|---|---|---|
| AUD_JPY_london | 0.5050 | 0.4874 | 0.4854 | +0.0196 | n | n | n |
| EUR_USD_asia | 0.4953 | 0.4796 | 0.4782 | +0.0171 | n | n | n |
| USD_JPY_asia | 0.5146 | 0.5207 | 0.5022 | +0.0124 | n | n | n |
| EUR_JPY_ny | 0.5305 | 0.5420 | 0.5218 | +0.0087 | n | Y | n |
| USD_CAD_ny | 0.5373 | 0.5223 | 0.5318 | +0.0055 | Y | n | n |
| AUD_USD_ny | 0.5288 | 0.5157 | 0.5262 | +0.0026 | Y | n | n |
| AUD_JPY_ny | 0.5460 | 0.5517 | 0.5446 | +0.0014 | Y | Y | Y |
| GBP_USD_ny | 0.5375 | 0.5343 | 0.5368 | +0.0007 | Y | Y | Y |
| GBP_USD_london | 0.5008 | 0.5102 | 0.5015 | -0.0007 | n | n | n |
| USD_CHF_asia | 0.4981 | 0.4947 | 0.5027 | -0.0046 | n | n | n |
| EUR_JPY_asia | 0.5047 | 0.5178 | 0.5095 | -0.0048 | n | n | n |
| AUD_JPY_asia | 0.4944 | 0.4835 | 0.5018 | -0.0074 | n | n | n |
| USD_CAD_london | 0.4938 | 0.4815 | 0.5030 | -0.0092 | n | n | n |
| AUD_USD_london | 0.4994 | 0.5066 | 0.5119 | -0.0125 | n | n | n |
| EUR_JPY_london | 0.4928 | 0.4956 | 0.5064 | -0.0136 | n | n | n |
| GBP_USD_asia | 0.5088 | 0.5274 | 0.5234 | -0.0146 | n | Y | n |
| EUR_USD_ny | 0.5204 | 0.5234 | 0.5355 | -0.0151 | Y | n | Y |
| USD_JPY_ny | 0.5460 | 0.5495 | 0.5616 | -0.0156 | Y | Y | Y |
| EUR_USD_london | 0.4910 | 0.4962 | 0.5106 | -0.0196 | n | n | n |
| USD_CHF_london | 0.5009 | 0.5158 | 0.5207 | -0.0198 | n | n | n |
| USD_CHF_ny | 0.5316 | 0.5430 | 0.5580 | -0.0264 | Y | Y | Y |
| AUD_USD_asia | 0.5018 | 0.5142 | 0.5310 | -0.0292 | n | n | Y |
| USD_CAD_asia | 0.5094 | 0.5087 | 0.5422 | -0.0328 | n | n | n |
| USD_JPY_london | 0.5282 | 0.5504 | 0.5718 | -0.0436 | Y | Y | Y |

## 3. What carries short-horizon direction


**h20** (top-15 slots, 62% directional): `q_kc_up_dist_pips`(7*), `zscore_5m`(5*), `pdl`(5), `bb_std`(5), `ema20_dist_pct`(5*), `q_macd_m5`(5*), `htf_pct_60`(5*), `d_high`(5), `ema20`(4), `d_close`(4), `pdh_dist_atr_pct`(4*), `rsi14_h1`(4*), `q_obv`(4*), `close_pos_daily`(3*), `d_low`(3)

**h30** (top-15 slots, 50% directional): `d_low`(6), `ema20`(6), `ema20_dist_pct`(6*), `q_kc_up_dist_pips`(5*), `bb_mid`(5), `pdl`(5), `q_macd_m5`(4*), `q_dc_up_dist_pips`(4*), `bb_std`(3), `ret_1h`(3*), `pdh`(3), `ema20_1h_dist`(3*), `bb_pos`(3*), `q_bbwp_m5`(3), `q_adl`(3*)

**h60** (top-15 slots, 39% directional): `ema50`(7), `d_close`(6), `htf_pct_60`(6*), `q_macd_m5`(6*), `pdh`(5), `ema5`(4), `d_high`(4), `ema_cross_pips`(4*), `q_tsi_m5`(4*), `d_low`(4), `ema20`(4), `q_skew_m5`(3*), `bb_mid`(3), `q_willr_m5`(3*), `q_yzv_m5`(3)

(* = directional feature; unstarred = vol/regime)


## 4. Distilled formulas (validated short-horizon cells)

- **AUD_JPY_ny h20**: pdh_dist_atr_pct in [-1.105303,1.055576] (p14.5-p92.2)* -> formula AUC 0.5559 (retain20 1.078)
- **AUD_JPY_ny h30**: ema20 in [108.105253,114.017315] (p24.3-p93.6) -> formula AUC 0.5491 (retain20 0.881)
- **AUD_JPY_ny h30**: ema20 in [108.105253,114.017315] (p24.3-p93.6) AND ema20_1h_dist in [-0.000427,0.001551] (p34.3-p64.0)* -> formula AUC 0.5357 (retain20 1.418)
- **AUD_JPY_ny h30**: ema20 in [108.105253,114.017315] (p24.3-p93.6) AND ema20_1h_dist in [-0.000427,0.001551] (p34.3-p64.0)* AND ema20_dist_pct in [-0.000175,0.000674] (p30.4-p84.1)* -> formula AUC 0.5323 (retain20 0.851)
- **AUD_USD_ny h20**: atr_conc in [0.171771,0.238954] (p11.1-p30.6) -> formula AUC 0.5715 (retain20 0.705)
- **USD_CHF_ny h30**: q_dc_lo_dist_pips in [2.8,10.3] (p21.6-p67.8)* -> formula AUC 0.5358 (retain20 1.135)
- **USD_CHF_ny h30**: q_kc_up_dist_pips in [-8.511736,-2.607512] (p35.3-p80.9)* AND q_dc_lo_dist_pips in [2.8,10.3] (p21.6-p67.8)* -> formula AUC 0.5541 (retain20 0.805)
- **USD_JPY_london h20**: ema50_dist_pct in [-0.000918,0.000679] (p10.8-p79.9)* AND q_ht_dcphase_m5 in [30.467977,186.549942] (p26.6-p65.4)* -> formula AUC 0.5319 (retain20 0.929)
- **USD_JPY_london h30**: d_low in [159.291,159.304001] (p90.6-p92.9) AND pdh_dist_atr_pct in [-0.79667,0.510805] (p20.4-p85.6)* -> formula AUC 0.5834 (retain20 0.844)
- **USD_JPY_ny h20**: ema20 in [156.731945,158.715004] (p31.5-p62.6) -> formula AUC 0.5489 (retain20 0.784)
- **USD_JPY_ny h20**: q_tsi_m5 in [-12.808107,21.374987] (p21.4-p82.8)* AND pdl in [156.217499,157.748001] (p32.9-p56.5) -> formula AUC 0.5584 (retain20 0.88)
- **USD_JPY_ny h30**: range_5bar in [10.0,12.475] (p39.0-p55.0) -> formula AUC 0.6172 (retain20 0.708)

## 5. Stacking math (quality gate + direction call, best 3 cells)

          cell  h_star  dir_val_auc  dir_validated                              gate  n_val_bars  n_gated  gate_selectivity  joint_accuracy  n_seq_ratchet  ev_seq_ratchet_net  wr_seq_ratchet  n_seq_hold60  ev_seq_hold60_net  wr_seq_hold60 drift_label
    AUD_JPY_ny      30       0.5517           True atr_5m + 6.6180 (h20, qAUC 0.718)        4796      389             0.081          0.4961             60              -2.887           0.717            44             -2.441          0.477   PERMANENT
USD_JPY_london      30       0.5504           True atr_5m + 6.5219 (h20, qAUC 0.721)        3729      378             0.101          0.5317             55              -0.931           0.673            33             -4.215          0.394     FLICKER
    USD_JPY_ny      30       0.5495           True atr_5m + 6.7283 (h20, qAUC 0.725)        4782      341             0.071          0.5513             55               0.024           0.764            36              2.367          0.639   PERMANENT


## 6. Drift labels (deep OOS 2022-2025, per cell x horizon)

- AUD_JPY_ny h20: PERMANENT {"2022": 0.5303, "2023": 0.5289, "2024": 0.5247, "2025": 0.5338}
- AUD_JPY_ny h30: PERMANENT {"2022": 0.5285, "2023": 0.5278, "2024": 0.5147, "2025": 0.5364}
- AUD_JPY_ny h60: PERMANENT {"2022": 0.5242, "2023": 0.5353, "2024": 0.5145, "2025": 0.5352}
- AUD_USD_asia h60: FLICKER {"2022": 0.5117, "2023": 0.5153, "2024": 0.5022, "2025": 0.4987}
- AUD_USD_ny h20: PERMANENT {"2022": 0.5266, "2023": 0.5342, "2024": 0.5336, "2025": 0.5411}
- EUR_JPY_ny h30: PERMANENT {"2022": 0.5295, "2023": 0.5267, "2024": 0.5353, "2025": 0.5418}
- EUR_USD_ny h20: PERMANENT {"2022": 0.5358, "2023": 0.5384, "2024": 0.525, "2025": 0.53}
- EUR_USD_ny h60: PERMANENT {"2022": 0.5364, "2023": 0.5417, "2024": 0.5302, "2025": 0.5468}
- GBP_USD_asia h30: PERMANENT {"2022": 0.5231, "2023": 0.5274, "2024": 0.5303, "2025": 0.5181}
- GBP_USD_ny h20: PERMANENT {"2022": 0.5252, "2023": 0.5316, "2024": 0.5364, "2025": 0.539}
- GBP_USD_ny h30: PERMANENT {"2022": 0.5255, "2023": 0.5353, "2024": 0.5362, "2025": 0.5431}
- GBP_USD_ny h60: PERMANENT {"2022": 0.5189, "2023": 0.5337, "2024": 0.537, "2025": 0.5462}
- USD_CAD_ny h20: PERMANENT {"2022": 0.5329, "2023": 0.5268, "2024": 0.5287, "2025": 0.5282}
- USD_CHF_ny h20: PERMANENT {"2022": 0.5427, "2023": 0.5306, "2024": 0.5358, "2025": 0.5333}
- USD_CHF_ny h30: PERMANENT {"2022": 0.5407, "2023": 0.5369, "2024": 0.5429, "2025": 0.5319}
- USD_CHF_ny h60: PERMANENT {"2022": 0.5422, "2023": 0.5621, "2024": 0.5475, "2025": 0.5405}
- USD_JPY_london h20: PERMANENT {"2022": 0.5036, "2023": 0.509, "2024": 0.5144, "2025": 0.5059}
- USD_JPY_london h30: FLICKER {"2022": 0.4986, "2023": 0.5115, "2024": 0.5137, "2025": 0.5003}
- USD_JPY_london h60: FLICKER {"2022": 0.485, "2023": 0.5053, "2024": 0.5197, "2025": 0.4957}
- USD_JPY_ny h20: PERMANENT {"2022": 0.5291, "2023": 0.5163, "2024": 0.5295, "2025": 0.5226}
- USD_JPY_ny h30: PERMANENT {"2022": 0.521, "2023": 0.5189, "2024": 0.527, "2025": 0.5246}
- USD_JPY_ny h60: PERMANENT {"2022": 0.5367, "2023": 0.5249, "2024": 0.529, "2025": 0.5421}
