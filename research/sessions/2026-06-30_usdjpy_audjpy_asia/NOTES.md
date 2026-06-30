# USD_JPY + AUD_JPY asia deep-dives — 2026-06-30

Two per-trade deep-dives (tool: `research/sessions/2026-06-23_aud_jpy_deep_dive/analyses/v5_pair_deep_dive.py`),
both since 2026-06-22 (full journal depth). Indicators recomputed from OANDA candles at entry; MFE/MAE from M1.
Two live config changes shipped (both hot-reloaded, no restart).

## 1) USD_JPY/asia — added per_cell_dir_cert_min = 0.49  (commit af0afa7)

n=5 asia inverted (sig long -> traded short):

| tid | date | d_cert | m_cert | MFE | MAE | real |
|-----|------|--------|--------|-----|-----|------|
| 9237 | 06-23 06:28 | 0.49 | 0.84 | 40.7 | -1.2 | +29.40 |
| 9528 | 06-30 01:06 | 0.57 | 0.84 | 10.1 | -10.8 | +6.05 |
| 9522 | 06-30 00:56 | 0.69 | 0.49 | 14.3 | -3.2 | +4.85 |
| 9539 | 06-30 01:32 | 0.46 | 0.72 | 3.3 | -20.3 | -19.30 |
| 9517 | 06-30 00:46 | 0.37 | 0.39 | -0.5 | -29.1 | -23.20 |

Both losers have the lowest d_cert (0.37/0.46); all 3 winners >= 0.49. Floor 0.49 (gate is strict `<`)
blocks 9517 + 9539, keeps 9237 exactly at boundary. Net swing +42.5p on this n. Keyed (pair,session) so it
also covers asia/long, but both asia-long winners (0.55/0.58) clear it.
Note: today's 4 asia shorts fired in one 46-min cluster (00:46-01:32) = the USD_JPY -$158 day.
London/short already inverted (loser 9260 predates the flip) -> no change.

## 2) AUD_JPY/asia — UN-INVERTED + dropped d_cert ceiling  (commit 1e7b24a)

n=11, ALL asia (london/ny cells disabled). Grouped by ACTUAL traded direction:
- ASIA/LONG (8 inverted + 1 native): -95.75p, 3W/6L
- ASIA/SHORT (2 native): +20.10p, 2W/0L

Per config era (the aggregate blends dead configs):
| era | dates | n | W/L | net pips |
|-----|-------|---|-----|----------|
| 1st inversion (reverted 06-23) | 06-22..23 | 5 | 1/4 | -72.80 |
| native | 06-24..26 | 3 | 2/1 | +1.15 |
| 2nd inversion (was live) | 06-27..30 | 3 | 2/1 | -4.00 |

MAE sort (worst->best) showed the 6 deepest drawdowns (MAE -19 to -21) are ALL longs that should have been
short; every one was a ~full SL. m_cert validated Brock's magnitude reframe directly:
- 6 deepest moves all m_cert 0.25-0.40 (low m_cert = big move expected)
- shallowest move (9223, MAE -4.4) had m_cert 0.91 (high m_cert = contained move)
d_cert noisy (losers 0.39-0.76, winners 0.39-0.72) -> no usable separation.

V5 signals AUD_JPY/asia SHORT ~10 of 11 bars; inversion was forcing those shorts into losing longs.
Action (Brock directional call): UN-INVERT -> short signals trade short.
- Dropped per_cell_dir_cert_max=0.65 (would block short winners 9429@0.69, 9241-as-short@0.76).
- KEPT per_cell_mom_cert_max=0.50 (selects the big-move setups -> correct for a short cell).
- inverted_live_cells 11 -> 10.
Residual: 9441 was a NATIVE long signal (1/11); un-invert leaves it long. Minor tail, no gate yet.

## Live governance state after this session
- inverted_live_cells (10): EUR_USD/london, EUR_USD/ny, GBP_USD/london, GBP_USD/ny, USD_CAD/ny,
  USD_JPY/asia, USD_JPY/london, EUR_JPY/ny, USD_CHF/ny, USD_CHF/london
- disabled_cells: 14 (unchanged)
- per_cell_dir_cert_min: GBP_USD/ny=0.52, USD_JPY/asia=0.49 (NEW)
- per_cell_dir_cert_max: USD_CHF/ny=0.55, USD_CHF/london=0.55 (AUD_JPY/asia removed)
- per_cell_mom_cert_min: GBP_USD/ny=0.40, USD_JPY/london=0.50
- per_cell_mom_cert_max: AUD_JPY/asia=0.50, AUD_USD/london=0.50
- per_cell_willr_range: EUR_JPY/ny/short=[-85,-7]
- per_cell_kc_up_range: AUD_USD/london/short=[-15,0]

## Watch list next session
- AUD_JPY/asia: confirm next trades come through as SHORTS; verify the short cell harvests big down-moves.
- USD_JPY/asia: confirm d_cert<0.49 signals are being blocked; re-check separation once n grows.
- Both fit on thin samples (n=5 / current-config n=3) — directional logic clean, magnitude unproven.
