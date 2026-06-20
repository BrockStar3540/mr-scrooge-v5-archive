# 2026-06-19 — 44-trade live matrix compilation

## What

Built three nested per-trade matrices from V5's last 24h of live trades:

1. **`v5_trade_matrix_44trades_base.csv`** — 14 columns: pair, dir, raw_dir, composite, d_cert, m_cert, expected, vol_regime, m5_volume, spread_pips, h1_ret_aligned, peak_pips, exit_net
2. **`v5_full_matrix_44trades.csv`** — 24 columns: above + session label + matrix aggregators (atr_5m, atr_1h, atr_d, atr_conc, atr_h1_relative, wall_frac, trend_4h_pips, htf_pct_20, htf_pct_60)
3. **`v5_full_matrix_v2_36cols.csv`** — 36 columns: above + new aggregators (rvol_5bar, rvol_12bar, rsi14_m5, rsi14_h1, bb_pos_h1, ema20_dist_pct, ema50_dist_pct, ret_5m_aligned, ret_15m_aligned, ret_30m_aligned, adx14_h1, adr_consumed)

These CSVs are in `../../matrices/`. The Python scripts that built them are in `analyses/`.

## Why

The 2026-06-18 aggregator sweep used 7.5yr corpus data. To answer "does this hold for V5's CURRENT live trader," we needed a 1-day live matrix at the (pair × session × direction × per-feature) granularity.

Specifically:
- Which aggregators actually predict pip_high MFE on the LIVE trader?
- Per-session, does the predictor ranking differ?
- Is volume / liquidity useful at this granularity?
- Which (pair × session) cells are systematically winning vs losing?

## How

1. Parse 53 SIGNAL + 53 ENTERED + 49 EXIT events from journalctl.
2. Reverse-solve `raw_dir = composite_score / (d_cert × m_cert)` per trade.
3. Pull OANDA M1 candles entry→exit per trade → compute peak MFE.
4. Pull OANDA M5 + H1 + D candles preceding entry per trade → compute aggregators.
5. Compute h1_ret_1bar aligned to trade direction.
6. Write CSVs + run per-session and per-(pair × session) correlations.

The expansion to 36 columns added the aggregators that earlier smoke tests hinted might matter but weren't in the matrix yet (rvol, RSI, BB, EMA distances, ADX, ADR-consumed, short-term aligned returns).

## Findings

### Per-session correlations (Pearson vs peak_pips, N=14-16 per session)

**ASIA (n=14)** — momentum + volume + reversion bot:
- `h1_ret_aligned` +0.887 (runaway #1)
- `rvol_12bar` +0.681 / `rvol_5bar` +0.670 — volume IS useful in asia only
- `trend_4h_pips` -0.621 (reversion — trade against 4h trend)
- `ret_30m_aligned` +0.547

**LONDON (n=14)** — exhaustion + volatility, weakest single signal:
- `adr_consumed` +0.637 — already-extended day predicts more travel
- `atr_conc` +0.396
- `trend_4h_pips` -0.370 (mild reversion)
- `m_cert` -0.353 (still wrong-way)
- `h1_ret_aligned` +0.486 vs exit_net

**NY (n=16)** — continuation + volatility breakouts:
- `atr_conc` +0.731 / `atr_5m` +0.725 — magnitude predictors
- `trend_4h_pips` +0.687 (continuation — trade WITH 4h trend)
- `bb_pos_h1` +0.547 (stretched BB still moves)
- `h1_ret_aligned` +0.529
- `rvol_5bar` -0.491 vs exit_net (vol spikes ARE BAD in NY)

### Per-(pair × session) cell breakdown

Best cells:
- AUD_JPY/asia 5 trades 80% WR +8.15p
- GBP_USD/london 3 trades 67% WR +2.85p
- USD_CHF/london 3 trades 67% WR +5.20p
- EUR_JPY/ny 1 trade +10.40p (n=1)

Worst cells:
- AUD_JPY/london 3 trades 33% WR -27.60p (BAD)
- EUR_JPY/london 3 trades 33% WR -16.50p
- GBP_USD/ny 4 trades 25% WR -14.60p
- EUR_USD/ny 2 trades 0% WR -12.90p
- USD_CHF/ny 3 trades 33% WR -11.15p

### Cohort patterns

| Cohort | n | WR | avg_out | avg_peak |
|---|---:|---:|---:|---:|
| BB_h1 stretched (\|x\|>0.7) | 13 | 69% | +1.74p | +10.58p |
| ADX ≤ 20 (no trend) | 14 | 71% | -0.99p | +6.78p |
| ADR_used > 1.2 (exhausted) | 19 | 37% | -2.22p | +8.71p |
| ADR_used < 0.7 (room left) | 4 | 75% | -1.47p | +4.80p |
| rvol_5bar > 1.5 (spike) | 7 | 43% | -5.40p | +7.26p |

## Outcome

These findings drove the per-(pair × session × direction) cell assignments in [2026-06-19 per_direction_extension](../2026-06-19_per_direction_extension/):

- ASIA cells with rvol + h1_ret strong → `asia_volume_rev` profile.
- LONDON cells with adr_consumed signal → `london_exhaustion` profile.
- NY cells with atr_conc + atr_5m signal → `ny_volatility` profile.
- BAD-evidence cells got `ny_volatility_strict` (1.5× tighter floors) or `default` to filter out the no-momentum entries.

Universal claims demoted to cell-conditional (matrix Tier 1 → Tier 2):
- `trend_4h` is bipolar (asia=reversion, ny=continuation)
- `raw_dir` (V5's direction.score) actively misleads in asia (-0.336 vs peak)
- `m_cert` is uniformly wrong-way as a positive gate

New universal finding:
- `h1_ret_1bar` aligned to trade direction is the strongest single signal in the matrix corpus (+0.501 vs peak, +0.572 vs exit_net, 77.3% sign accuracy).

## Files

- `analyses/v5_trade_matrix.py` — base 14-col matrix
- `analyses/v5_full_matrix.py` — 24-col matrix with aggregators
- `analyses/v5_more_aggs.py` — 36-col matrix with extended aggregators
- `analyses/v5_per_cell.py` — per-(pair × session) correlation analysis
- `analyses/v5_per_cell_v2.py` — per-session cohort patterns
- `analyses/v5_render_tables.py` — readable table rendering
- `analyses/parse_v5_trades.py` — journalctl trade extraction
- `data/` — copies of the CSVs (live in `../../matrices/`)

## Sample-size honesty

44 trades. Per-session N=14-16 — meaningful for session-level correlations. Per-cell N=1-5 — only useful for direction-of-effect, not magnitude.

Reassess profile assignments after the nightly smoke cron accumulates 200+ more trades.
