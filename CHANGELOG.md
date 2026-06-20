# Changelog

Every substantive change to V5: what changed, why, and the outcome (where known). Commits before V5 cutover are in V4's repo history.

Format:
- `[date]` `commit` — Title
  - **What** — concrete change
  - **Why** — motivation
  - **Outcome** — measured result if known, or status if not yet validated

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
