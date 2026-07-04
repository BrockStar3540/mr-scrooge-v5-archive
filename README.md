<img width="900" height="900" alt="Scrooge Money" src="https://github.com/user-attachments/assets/df689e08-0799-414d-b7f6-7dec7a645813" />

# Mr. Scrooge V5

> **STRATEGY-FREE BOT.** V5 has no named strategies, plays, or setup libraries (that was V4). The entire strategy is **direction** (factor-scored, per-cell profiles) + **momentum/distance** (expected-pips gate), resolved per (pair × session × direction) cell and ranked by the playmaker. Analyses must be scoped to same-engine trades (v2/v3 modules, live 2026-06-20+); V4 and v1-module history is inadmissible for cell decisions.

Automated forex trading bot for OANDA. Modular signal pipeline: direction → momentum → playmaker → step-trail ratchet exit. Live on 7 currency pairs (USD_CHF killed 2026-07-01).

## Status

Live since 2026-06-18 on EC2 (Tailscale `[REDACTED-IP]`). 7 active pairs: AUD/JPY, AUD/USD, EUR/JPY, EUR/USD, GBP/USD, USD/CAD, USD/JPY. Dashboard: `https://[REDACTED-HOST]:8084/` — 8 tabs (LIVE / PAIRS / CELLS / INDICATORS / HEALTH / SYSTEM / TUNE / PLAYMAKER) with `?stream=1` and `?mode=overlay` modes for live broadcasting.

Pipeline at a glance:

```
OANDA M5/H1/D feed (5s manage, 300s scan)
   → MarketView (28 dir features incl willr_m5/aroonosc_h1/kc_up_dist_pips/efi/vortex_diff_h1)
   → direction_v2  (per pair × session × direction, 48 cells)  → bias + score + cert
   → momentum_v3   (per pair × session × direction, 48 cells)  → expected_pips + cert
   → Playmaker     (cert/score floors + spread gate + per-cell governance + lock guard)
        ├── disabled_cells              — cell off entirely
        ├── inverted_live_cells         — flip trade direction at execution (both dirs)
        ├── inverted_live_directions    — flip one native direction (MAE-flip doctrine)
        ├── inverted_shadow_cells       — log inversion signal only
        ├── per_cell_mom_cert_min/max   — m_cert floor/ceiling per cell
        ├── per_cell_dir_cert_min/max   — d_cert floor/ceiling per cell
        ├── per_cell_willr_range        — willr_m5 [min, max] per cell+dir
        ├── per_cell_kc_up_range        — kc_up_dist_pips [min, max] per cell+dir
        ├── per_cell_aroon_range        — aroonosc_h1 [min, max] per cell+dir (MAE-flip sep.)
        ├── max_per_currency_direction  — exposure cap: max 1 open per (currency, direction)
        └── random_pick                 — random.choice among actionable (vs max-composite)
   → Broker (OANDA market order, server-side SL = −20p)
   → RatchetManager (poll 5s, step-trail SL at MFE +7.5/10/12.5/15/17.5/20)
```

All per-cell governance mechanisms are hot-reloadable via config — no restart needed for tuning thresholds. New mechanism types (a new gate kind) require code + restart.

---

## Cell architecture (LIVE — Phase D cutover 2026-07-04)

The cell is becoming the first-class unit: `config/cells/<PAIR>.json` (evidence-generated, lineage on every threshold) + `modules/cells/` (CellModule/PairModule). **LIVE since 2026-07-04 (Phase D cutover)**: `CELL_EXECUTION_ENABLED=True` — cells are the sole strategy source; direction_v2/momentum_v3 archived at `modules/archive/signals_legacy/` (rollback tag `pre-cell-cutover-2026-07-04`). Book: 10 ACTIVE / 3 SHADOW (controls) / 11 NO-SIDE / 3 DISABLED. Portfolio caps in `modules/cells/portfolio.py`; per-setup exits ride `Position.exit_params`. Scorer: `research/tools/cell_setup_score.py --json`.

## Current Architecture (2026-07-03)

### Aggregator rules

**AGGREGATOR_RULES is intentionally empty.** The two previously wired rules were retired on 2026-07-03:
- `atr_conc > 2.5` — had a dead scale bug (live ratio lives in (0,1), never fired); retired with the atr_conc fix that revived 14 cells (the 4.0-5.0 floors were the separate momentum-profile bug).
- `atr_h1_rel > 1.6` — sign INVERTED in 2026 vs 8yr average (confirmed 297k-bar study). No new aggregator rules until clean-corpus derivation on post-07-03 parquets.

### Calibration instrumentation (LOG-ONLY, 2026-07-03)

`config/cell_calibration.json` — 48 cells: MFE quantiles (p25/p50/p75/p90 at 60m/240m), ATR regression (`projected_mfe = clip(slope × atr_1h + intercept, p25, p90)`), winner-MAE, dead-entry rates + separators, direction leans. Per cycle the engine logs `CAL` lines comparing `expected_pips` vs artifact projection. Monthly re-fit: Mini cron `0 5 1 * *` (`v5_monthly_refit.sh`) → bars → leak-test → truth rebuild → calibration → anchor check → ship. First run: 2026-08-01.

### SHADOW_PROFILE (LOG-ONLY, 2026-07-03)

Corrected 2026-reversion profiles stamp same views each cycle alongside live profiles (`SHADOW_PROFILE` log lines). Inert until promoted via restart. Promotion gate: shadow beats live on n>=20 same-engine per cell. Scorer: `research/tools/profile_shadow_score.py`.

### Research taint dividing line

H1 look-ahead leak fixed 2026-07-03. Pre-fix H1-feature parquet numbers are **upper bounds**. Broker-trade measurements, M5 features, and post-fix corpus are the clean anchors. See `research/README.md` §(c) for the full tainted-session list and `note_parquet_h1_leak_2026-07-03.md` in vault.

---

## Where to read more

- **Signal theory + evidence** → [docs/DIRECTION_DETECTOR_SPEC_v2.md](docs/DIRECTION_DETECTOR_SPEC_v2.md) (evidence-revised, 2026-07-03)
- **Research index + truth/tainted labeling** → [research/README.md](research/README.md)
- **System architecture** → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Signal modules** (direction + momentum, per-(pair × session × direction)) → [docs/MODULES.md](docs/MODULES.md)
- **Ratchet exit logic** → [docs/RATCHET.md](docs/RATCHET.md)
- **Playmaker entry gates** → [docs/PLAYMAKER.md](docs/PLAYMAKER.md)
- **Configuration files** → [docs/CONFIGURATION.md](docs/CONFIGURATION.md)
- **Deployment + rollback** → [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **Setup from scratch** → [docs/SETUP.md](docs/SETUP.md)
- **What's next** → [docs/ROADMAP.md](docs/ROADMAP.md)

## Research

All research data, analyses, and per-session findings live under [research/](research/README.md). The research index labels each session as CURRENT TRUTH, VALID LEGACY, or TAINTED (H1 leak) and lists the Mini compute directories.

Key research artifacts:
- [docs/EDGE_REPORT.md](docs/EDGE_REPORT.md) — V5 edge analysis through 2026-06-18 (direction signal + ratchet amplification + system expectation)
- [docs/DIRECTION_DETECTOR_SPEC_v2.md](docs/DIRECTION_DETECTOR_SPEC_v2.md) — evidence-revised theory spec (2026-07-03)
- [research/reference/](research/reference/) — curated Brock-archived V5 test reports (dm05-dm09 + factor_sweep)
- [research/sessions/](research/sessions/) — chronological per-session research with what, why, findings, links to data
- [research/matrices/](research/matrices/) — live-trade matrices that drove module decisions
- [research/live-smoke/](research/live-smoke/) — nightly cron output

## Change history

See [CHANGELOG.md](CHANGELOG.md) — every substantive change grouped by era with what + why + outcome.

## Repo layout

```
mr-scrooge-v5/
├── README.md                navigation hub (this file)
├── CHANGELOG.md             every change by era with what/why/outcome
├── docs/                    architecture, modules, config, deployment
│   ├── ARCHITECTURE.md
│   ├── MODULES.md           current state — per-(pair × session × direction)
│   ├── DIRECTION_DETECTOR_SPEC_v2.md  evidence-revised theory (2026-07-03)
│   ├── signal-module-spec.md  historical dm_04 spec
│   ├── EDGE_REPORT.md       2026-06-13 → 06-18 edge analysis
│   ├── SETUP.md
│   ├── DEPLOYMENT.md
│   ├── RATCHET.md
│   ├── PLAYMAKER.md
│   ├── CONFIGURATION.md
│   ├── ROADMAP.md
│   └── images/
├── research/
│   ├── README.md            master index: truth/tainted labels + methodology + Mini dirs
│   ├── sessions/<yyyy-mm-dd_topic>/
│   ├── matrices/
│   ├── reference/           Brock-curated reports
│   ├── tools/               cell_audit.py, lock_snapshot.py, calibration_score.py, profile_shadow_score.py
│   └── live-smoke/          nightly cron output
├── config/
│   ├── exit_config.json         SL + ratchet + TP1/TP2
│   ├── playmaker_config.json    account + per-pair gates
│   ├── locked_cells.json        lock registry + snapshots + overrides
│   └── cell_calibration.json    48-cell MFE/MAE calibration artifact (LOG-ONLY)
├── core/                    engine, broker, feed, session map
├── modules/
│   ├── signals/             direction_v2 + momentum_v3 + their profiles
│   ├── management/          ratchet
│   └── playmaker/           entry gating + lock_guard
├── ops/                     panel + server
└── tests/
```

## Quick commands

Service control on EC2:
```bash
systemctl --user status mr-scrooge-v5
systemctl --user restart mr-scrooge-v5
journalctl --user -u mr-scrooge-v5 -f
```

Live config edits (no restart):
```bash
# Both configs are hot-reloaded by the engine
nano config/exit_config.json       # SL + ratchet + TP1/TP2
nano config/playmaker_config.json  # account + per-pair gates
```

Or use the TUNE / PLAYMAKER tabs on the dashboard at `:8084` for guarded edits.

## Dashboard

Modern dark UI (rebuilt 2026-06-24). 8 tabs, glass-blur nav, semantic colors (long=cyan, short=magenta, inverted=purple, shadow=slate), JetBrains Mono numerics.

- **LIVE** — giga P/L ticker, equity curve, cell mosaic, account bar, open positions, today's trades, recent events
- **PAIRS** — per-pair signal cards with 15 indicator chips + per-cell rule pass/fail footers
- **CELLS** — governance grid with filter/sort/fire counts
- **INDICATORS** — per-pair feature cards + sparklines (dir_sc / m_cert / willr / vortex / kc_up / cpos)
- **HEALTH** — scan/manage intervals, pick method, last fired
- **SYSTEM** — CPU / RAM / services / Mini / logs
- **TUNE** — live SL + ratchet + TP edits
- **PLAYMAKER** — account knobs + per-pair gates + per-cell governance view

URL modes for streaming:
- `?stream=1` — large hero, hides non-LIVE tabs, enables decision ticker
- `?mode=overlay` — transparent body for OBS chromakey (just trade overlays + corner P/L pill)

## Per-cell governance — when to use what

| mechanism | shape | when to ship |
|-----------|-------|--------------|
| `disabled_cells`              | list of [pair, session, dir]       | cell has structural negative edge with corroboration (broker + walk-forward), n>=5 consistent |
| `inverted_live_cells`         | list of [pair, session]            | BOTH directions consistently wrong — flip the firing pin for both. Deprecated for new cells (use MAE-flip doctrine instead) |
| `inverted_live_directions`    | list of [pair, session, native_dir]| ONE native direction's signal is wired backwards (MAE >> MFE, >=3× asymmetry, n>=6) — flip just that side |
| `inverted_shadow_cells`       | list of [pair, session]            | shadow-log opposite direction signals to evaluate inversion before commit |
| `per_cell_mom_cert_min`       | dict pair/session → float          | cell's edge IS the high-conviction setup (cert correlates with MFE) |
| `per_cell_mom_cert_max`       | dict pair/session → float          | cell's edge IS the big-move setup (low cert predicts magnitude) |
| `per_cell_dir_cert_min/max`   | dict pair/session → float          | direction certainty floor/ceiling — same logic on the direction module |
| `per_cell_willr_range`        | dict pair/session/dir → [lo, hi]   | cell only profitable in a specific willr_m5 window |
| `per_cell_kc_up_range`        | dict pair/session/dir → [lo, hi]   | cell only profitable when distance to upper Keltner is in a window |
| `per_cell_aroon_range`        | dict pair/session/dir → [lo, hi]   | cell only profitable in a specific aroonosc_h1 window (MAE-flip doctrine separator) |
| `max_per_currency_direction`  | int (default 1)                    | exposure cap — no stacking the same (currency, direction) bet |
| `random_pick`                 | bool                               | spread fire rate across all actionable cells instead of max-composite |

**Governance constitution (2026-07-02):** no per-cell action on fewer than n>=20 same-engine (v2/v3 module) trades from that cell. Inversion deprecated for new cells (require MAE-flip doctrine: >=3× MAE:MFE asymmetry, n>=6). Locks are provisional attribution, not validated-winner badges — re-lock at n>=25 with CI over breakeven.

### 🔒 LOCKED cells — security lock (2026-07-01)

Brock-designated dialed-in cells are **frozen**: they keep trading exactly as validated, and global / per-pair / per-cell config changes do NOT apply to them unless explicitly overridden. Registry: `config/locked_cells.json` (baselines + `snapshot` + `overrides`).

- **Enforcement**: `modules/playmaker/lock_guard.py`, wired into `pick_best()`. For a locked (pair, session), every gate resolves from the lock-time `snapshot.governance`, not live config. Divergence logged as `LOCK_GUARD drift ... (using locked)` (rate-limited 1/h per field) and shown in `/api/state.lock_guard`.
- **Throttle**: locked traded directions cap at `snapshot.throttle.max_opens_per_session` (default 2) per session-instance.
- **Code-level drift**: restart-required inputs fingerprinted at lock time; `startup_check()` logs CRITICAL `LOCK_GUARD CODE-DRIFT` on mismatch (alert-only, keeps trading).
- **Changing a locked cell**: add an entry to `overrides` in `locked_cells.json` ({pair, session, field, value, approved_by, date, note}). Re-dialing = edit config + rerun `python3 research/tools/lock_snapshot.py --write`.
- **Audit**: `research/tools/cell_audit.py` tags 🔒 + raises DEGRADING post-lock (warning for Brock, not authorization to edit). Vault page: [[locked-cells-status]] (run `~/.local/bin/locked_cell_monitor.sh` on EC2 to refresh).
