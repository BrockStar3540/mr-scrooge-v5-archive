# Changelog

Every substantive change to V5: what changed, why, and the outcome (where known). Commits before V5 cutover are in V4's repo history.

Format:
- `[date]` `commit` — Title
  - **What** — concrete change
  - **Why** — motivation
  - **Outcome** — measured result if known, or status if not yet validated

## 2026-06-20

### `[06-20 PM]` `a8f3889` — Close v2/v3 observability + aggregator-input gaps
- **What**: After audit of the 5a29000 activation found three silent issues. **Gap 3 (feed):** `atr_h1_relative` + `trend_4h` now populated on `MarketView` ([core/feed/oanda.py](core/feed/oanda.py), [modules/signals/base.py](modules/signals/base.py)). `atr_h1_relative` = current Wilder ATR14 ÷ 100-bar rolling-mean ATR; `trend_4h` = sign(h1_ret_4bar). `_H1_COUNT` 100→200 to give the rolling-mean a real baseline. **Gap 2 (smoke cron):** `SIGNAL` log line in [core/engine.py](core/engine.py) extended with `active_side / long_prof / short_prof / mom_prof / gates / cert_boost`. `/home/ubuntu/v5_smoke_nightly.py` regex + CSV gain 6 columns + daily report gains per-mom-profile WR + per-active-side WR sections. **Gap 1 (dashboard):** [ops/server.py](ops/server.py) `/api/state` ticket payload exposes the v2/v3 `reads` fields and `last_views` adds `atr_h1_relative + trend_4h + atr_conc`. [ops/panel.html](ops/panel.html) PAIRS card gains "Dir prof" + "Mom prof" rows.
- **Why**: 5a29000 wired v2/v3 INTO the engine but left aggregator rules 2+3 silently dead (rule field `atr_h1_relative` not on MarketView, getattr→0, threshold `>1.6` never reached) and the `trend_4h` weight in continuation_strong profiles re-normalized to zero contribution. The dashboard couldn't show which profile fired; the smoke cron couldn't measure per-profile WR. Math audit confirmed the modules calculated *accurately* (live EUR_JPY/ny ticket matched recompute to ±0.0004 / ±0.03p) but with incomplete inputs.
- **Outcome**: Restart cycle 1 clean. All 8 `last_views` show populated `atr_h1_relative` (0.87-1.07 quiet-Saturday range, no rule fires; will fire during real news vol spikes), `trend_4h` (+1/-1 per pair), and `atr_conc` (0.17-0.35). Ticket payload includes 10 new v2/v3 reads fields. SIGNAL log dry-test parsed by new regex matched 13/13 fields. Tonight's 23:30 UTC nightly = first to capture per-profile WR.

### `[06-20 PM]` `<commit>` — direction_v2 + momentum_v3 activated LIVE
- **What**: Swapped `modules/signals/__init__.py` to import `DirectionModule` from `direction_v2` and `MomentumModule` from `momentum_v3`. `stamp_pair()` now computes the direction stamp first and passes `direction_stamp.bias` into `momentum.stamp(view, direction)` — the v3 signature requires the caller's direction so it can pick the per-(pair × session × direction) profile. `core/engine.py` untouched. Added three alias properties (`pdh_dist_pips`, `pdl_dist_pips`, `ema20_1h_dist_pct`) to `MarketView` so v2/v3 field-name reads resolve to the existing live fields. Deleted obsolete `test_momentum_v3.py` (asserted 24-cell coverage; superseded by `test_per_direction.py` 48-cell coverage after the 06-19 PM extension).
- **Why**: v2/v3 modules have been staged since 06-19 with passing per-direction smoke tests. Saturday market-closed window is the safe restart slot — verifies behavior before London open Sun 22:00 UTC. Per-direction profiles encode the live evidence that direction_v1 / momentum_v1 was averaging across mixed-WR sides.
- **Outcome**: Live since 2026-06-20 19:44 UTC (cycle 1). First-cycle diff vs v1 baseline (cycle 577): `expected_pips` ~3× lower across the board (matches v3 `EXPECTED_PIPS_SCALER=0.30` cap; v1 was overshooting); EUR_JPY/ny bias `block → short` (dual-compute picked stronger short side); AUD_USD/ny + GBP_USD/ny score signs flipped (same reason); USD_JPY/ny + USD_CHF/ny `mom_certainty` 0.64/0.12 → 0.00 (profile gate kills). USD_CAD/ny short remains the strongest signal at composite -0.092 in both v1 and v2/v3. No process errors. Journal clean.

## 2026-06-19

### `[06-19 PM]` `2b084e7` — Per-(pair × session × direction) extension
- **What**: Both `direction_v2` and `momentum_v3` extended from per-(pair × session) = 24 cells to per-(pair × session × direction) = 48 cells. `DirectionModule.stamp()` dual-computes long and short scores using respective profile weights and picks stronger. `MomentumModule.stamp(view, direction)` now requires direction arg.
- **Why**: Live evidence showed direction-asymmetric WRs being averaged out — AUD_JPY/asia had 5/5 short winners + 0 long trades; USD_CHF/ny had 0/3 long losers + 0 short trades. Per-(pair × session) profiles were one-size-fits-both and missed this.
- **Outcome**: Staged. Six smoke tests pass. Direction: 24 default / 14 continuation_strong / 10 reversion. Momentum: 30 default / 7 london_exhaustion / 4 asia_volume_rev / 4 ny_volatility / 3 ny_volatility_strict. Cells without per-direction evidence default to V5 v1 unchanged. Activation pending shadow-mode.

### `[06-19 PM]` `c1925d3` — momentum_v3 (per-pair × per-session)
- **What**: Added `modules/signals/momentum_v3.py` + `momentum_profiles.py`. Per-pair `PAIR_TUNING` constants (atr_d_typical, rvol_floor, h1_ret_floor, etc.). Per-(pair × session) profile slots: `asia_volume_rev`, `london_exhaustion`, `ny_volatility`, `ny_volatility_strict`, `default`. Evidence-strictness multiplier layers on top (STRONG=1.00, MEDIUM=1.10, BAD=1.40).
- **Why**: momentum_v2 was a single global `EXPECTED_PIPS_SCALER = 0.30` constant. Per-cell profiles let each cell gate differently on its own predictors (rvol in asia, adr_consumed in london, atr_conc in ny).
- **Outcome**: Staged alongside momentum.py v1. Five smoke tests pass.

### `[06-19 AM]` `249f970` — Ratchet retune (LIVE, see diagnosis)
- **What**: `step_trigger_pips` 4.5 → 7.5, `step_trail_pips` 1.5 → 2.5, `step_size_pips` 5.0 → 2.5. First lock now at peak +7.5p instead of peak +4.5p. Rungs every +2.5p with 2.5p trail.
- **Why**: Brock wanted a more conservative entry to the ratchet (engage at +7.5p, lock +5p) with finer rungs riding bigger winners.
- **Outcome**: Live since 06:15 UTC. Diagnosed later same day as the cause of -612 USD over 24h: 50% of winners peak in the +4.5p to +7.5p zone — under new config those never arm and revert to -20p SL hits. Brock asked for diagnosis ("why is the bot trading worse"); revert not yet executed pending decision. See [research/sessions/2026-06-19_live_smoke_v1-v5/](research/sessions/2026-06-19_live_smoke_v1-v5/) and ratchet doc.

### `[06-19 AM]` `87ffe08` — v2 modules + nightly Self-Eval cron
- **What**: Added `modules/signals/direction_v2.py` + `direction_profiles.py` + `momentum_v2.py` (per-(pair × session)). Cron at 23:30 UTC runs `v5_smoke_nightly.py` to capture per-trade per-feature accuracy → `/data/v5-smoke-history/all_trades_per_feature.csv`.
- **Why**: Compile per-(pair × session) profile assignments from yesterday's matrix work. Nightly cron accumulates per-trade per-feature accuracy so profile assignments can be refined live.
- **Outcome**: First nightly run captured 9 asia-session trades, 89% WR, h1_ret_1bar 100% accuracy.

## 2026-06-18

### `[06-18 EOD]` — Initial SL widened 12p → 20p
- **What**: `config/exit_config.json` `initial_sl_pips`: 12 → 20.
- **Why**: -12p was being hit on trades that would have run to profit if given room. The ratchet was supposed to tighten the SL post-engage; the initial was too aggressive.
- **Outcome**: Trades now have more breathing room before the ratchet arms.

### `[06-18]` — V5 aggregator test launched on Mini
- **What**: ~/scrooge-aggregator-test/ on Mini ran two XGBoost regressors per (pair × session) trained from scratch on 7.5yr corpus. Sweep: 8 pairs × 3 sessions × 7 V3-candidate ablations. Outputs at `/Volumes/Alien Device/scrooge-research/v5_aggregator_test_2026-06-18/`.
- **Why**: Validate which V3 aggregators (trend_1h, trend_4h, atr_conc, htf_bias_20/60, wall_frac, ema50_atr_frac) actually contribute edge versus being noise.
- **Outcome**: 24 cell-level XGB models. Key findings: `atr_conc` Q4 magnitude penalty universal; `h1_ret_1bar` strongest direction signal; `wall_frac` amplifies pip_high in 3 of 5 multi-trade cells. See [research/sessions/2026-06-18_aggregator_sweep/](research/sessions/2026-06-18_aggregator_sweep/) and `docs/EDGE_REPORT.md`.

### `[06-18 cutover]` — V4 retired, V5 promoted to live trader
- **What**: V4 stopped; V5 became sole live trader on 8 pairs. dm_04 direction + momentum modules + deterministic playmaker + step-trail ratchet.
- **Why**: V4 evolved as a research platform (ratchet runner exit, util brain, bucket-keyed strategies). V5 was the cleaner production rewrite with structured modules + clear separation of concerns.
- **Outcome**: V5 has been the live trader since the cutover.

## Pre-V5

V4 history lives in V4's repo. The cutover snapshot is in `~/v5-archives/v5-pre-cutover-backups-2026-06-19.tgz` on EC2 (mirrored to Dropbox: `/LLM Sessions/Claude Sessions/Scrooge/2026-06-19_v5_v2_modules_deployment/`).
