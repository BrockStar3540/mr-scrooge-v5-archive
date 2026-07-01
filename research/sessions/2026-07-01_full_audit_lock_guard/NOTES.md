# 2026-07-01 (evening) — Full V5 audit + LOCKED-cell security lock + USD_CHF kill

## Audit (3-agent: broker pull / wiring verify / tooling)
- All 6 morning changes CONFIRMED live (multi-open proven: 06:39Z double-open); 0 errors, 0 restarts.
- Broker truth post-06:08Z restart: n=11 closed, 4W/7L (36% WR), -109.1p / -$993 realized (+2 open ~-$205).
  - Newly-widened cells: 4 trades, -$623 (worst: AUD_USD/asia -$391, USD_CAD/london -$284 fwd -29.9p).
  - Locked cells: 5 trades, -$329 — but forward-pip says entries were fine
    (GBP_USD/ny/short mean fwd +0.7p; AUD_JPY/asia/short 9592 fwd +3.1p): chop + cadence, not edge decay.
- 2/6 locked cells flagged DEGRADING by monitor (realized-based); held as-is per forward-pip read.
- Key finding: multi-open engine change tripled GBP_USD/ny/short cadence (4 opens/3h vs ~1.75/day
  baseline) — a GLOBAL change silently altered a locked cell's exposure. Motivated the security lock.
- Monthly Mini master_matrix cron: FAILED first run (system_profiler not in cron PATH + `2>\&1`
  crontab typo + EC2_KEY wrong path). All three fixed; July run completed
  (archive ~/qtl-discovery-8yr/master_matrix_archive_2026-07 on Mini).

## LOCKED-cell security lock (Brock: "keep trading the way they are; global/pair changes
## must be overruled explicitly")
- config/locked_cells.json: + `snapshot` per cell (full (pair,session) governance at lock time,
  throttle, code_fingerprint) + `overrides` list. Generator: research/tools/lock_snapshot.py.
- modules/playmaker/lock_guard.py: frozen-governance resolution, drift logging (1/h/field),
  session-instance keys, fingerprint startup check. Fail-open (lock file error => lock inert, never crash).
- pick_best(): locked (pair,session) resolves ALL gates from snapshot; throttle-aware winner
  selection (capped locked cell falls through to next candidate — reviewed fix, tested 4/4).
- engine: _cell_opens tracking, locked initial-SL override, startup fingerprint check.
- server: /api/state.lock_guard block.
- Semantics: DEGRADING = early warning for Brock, NOT authorization to edit. Override entries
  are the only way changes reach a locked cell.

## USD_CHF killed (Brock: "a real turd")
- Broker-confirmed loser both directions (-$1,071). per_pair.USD_CHF.enabled=false (hot-reload).
- Open trade 9633 left to exit manager (stop -20p) per default; not flattened.

## Decisions declined by Brock
- Exploration budget + half-size exploratory cells + daily circuit breaker: not needed (practice account).
