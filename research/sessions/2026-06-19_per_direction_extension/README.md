# 2026-06-19 — Per-(pair × session × direction) extension

## What

Both `direction_v2` and `momentum_v3` extended from per-(pair × session) = 24 cells to per-(pair × session × direction) = 48 cells.

- **Commits**: `c1925d3` (momentum_v3 deploy as per-(pair × session)), `2b084e7` (per-direction extension of both)
- **Files**: `modules/signals/direction_v2.py`, `direction_profiles.py`, `momentum_v3.py`, `momentum_profiles.py`, `test_per_direction.py`
- **Status**: Staged in `modules/signals/`, engine.py still imports v1.

## Why

Live evidence from the 44-trade matrix (`../2026-06-19_matrix_compilation/`) showed direction-asymmetric WRs in many cells that were being averaged out by the (pair × session) profile assignment.

Examples:
- AUD_JPY/asia: 5 shorts at 80% WR +8.15p · 0 long trades
- USD_CHF/ny: 0/3 longs lost · 0 short trades
- GBP_USD/ny: 4 shorts at 25% WR -14.60p · 0 long trades
- EUR_USD/ny: 0/2 shorts lost · 0 long trades
- AUD_JPY/london: 2 longs both lost · 1 short lost (BAD on long, default on short)

These asymmetries argue for separate long-side and short-side profiles per cell.

## How

### Architecture changes

**direction_profiles.py**:
- `PROFILE_ASSIGNMENT` becomes nested `{pair: {session: {long: ..., short: ...}}}`.
- `get_factor_defs(pair, session, direction)` — adds direction arg.

**direction_v2.py**:
- `DirectionModule.stamp(view)` dual-computes: long-profile score AND short-profile score, picks whichever has stronger `|score|`.
- DirectionStamp shape unchanged — Playmaker doesn't change.
- New reads payload exposes both scores and `active_side` for shadow-mode debugging.

**momentum_profiles.py**:
- `PROFILE_ASSIGNMENT` keys are now `(pair, session, direction)` tuples.

**momentum_v3.py**:
- `MomentumModule.stamp(view, direction)` requires direction arg from caller. When engine activates, order is: `direction_stamp = direction.stamp(view)`, then `momentum_stamp = momentum.stamp(view, direction_stamp.bias)`.

### Cell assignment (48 cells each)

Direction module — 24 default / 14 continuation_strong / 10 reversion.

Momentum module — 30 default / 7 london_exhaustion / 4 asia_volume_rev / 4 ny_volatility / 3 ny_volatility_strict.

Cells without per-direction evidence default to V5 v1 unchanged (zero regression risk).

### Per-pair tuning + evidence-strictness

The same profile is configured differently per pair via `PAIR_TUNING` constants (e.g., USD_JPY's h1_ret floor is 3.0p vs AUD_JPY's 2.0p, because USD_JPY ATR is larger).

Evidence-strictness multiplier layered on top:
- STRONG = 1.00× (default floors)
- MEDIUM = 1.10×
- MEDIUM_STRICT / WEAK = 1.20×
- BAD = 1.40× (tightest floors — for cells actively losing)
- NO_DATA = 1.00× (paired with `default` profile, V5 v1 behavior)

## Findings

The session's main "findings" are the cell assignments themselves — see `direction_profiles.py` and `momentum_profiles.py` for the full 48-cell breakdown.

### Test coverage

`test_per_direction.py` — 6 tests, all pass on EC2 + local:
1. direction_profiles 48 cells covered
2. momentum_profiles 48 cells covered
3. DirectionModule dual-computes and picks stronger
4. MomentumModule emits different stamps for same view, different direction
5. Chaos veto (atr_conc ≥ 15) trumps profile in both directions
6. BAD evidence yields stricter rejection than NO_DATA in opposite direction

## Outcome

Staged, not yet imported by engine.py. V5 still runs v1.

Activation pathway (recorded in `docs/DEPLOYMENT.md`):
1. Shadow-mode wiring: import both v1 and v2/v3 in engine.py, log both stamps.
2. After 3-5 days of shadow comparison, swap imports.
3. Rollback = single-line revert + service restart.

This session is the third of three on 2026-06-19:
- [matrix_compilation](../2026-06-19_matrix_compilation/) — built the data
- [live_smoke_v1-v5](../2026-06-19_live_smoke_v1-v5/) — confirmed the per-session patterns
- per_direction_extension (this session) — packaged into deployable modules

## Files

- Module files live in `/modules/signals/` (committed; not in this session folder to avoid duplication).
- This folder's README is the human-readable summary.

## What's next (also in `../../docs/ROADMAP.md`)

- Wire shadow-mode logging.
- Activate after 3-5 day shadow window.
- After 200+ more trades, re-evaluate cell assignments — many NO_DATA cells may upgrade.
- Add per-(pair × session × direction) calibration anchors (currently anchors are per-(pair × session) only). Requires a fresh aggregator sweep with the long/short split.

## Sample-size honesty

Per-cell sample sizes are 0-5 trades. Cells with 0 evidence default to V5 v1. The cell-assignment table is based on a mix of direct cell observation (N=3-5), session-level patterns (N=14-16), and matrix-level inference (continuation_strong for asia/JPY, reversion for NY non-JPY, all from 2026-06-18 corpus work).

The 24 default cells are by design conservative — we don't shrink the entry universe without evidence.
