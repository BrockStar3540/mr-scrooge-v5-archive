<img width="900" height="900" alt="Scrooge Money" src="https://github.com/user-attachments/assets/df689e08-0799-414d-b7f6-7dec7a645813" />

# Mr. Scrooge V5

> **STRATEGY-FREE BOT.** V5 has no named strategies, plays, or setup libraries (that was V4). The entire strategy is **direction** (factor-scored, per-cell profiles) + **momentum/distance** (expected-pips gate), resolved per (pair × session × direction) cell and ranked by the playmaker. Analyses must be scoped to same-engine trades (v2/v3 modules, live 2026-06-20+); V4 and v1-module history is inadmissible for cell decisions.

Automated forex trading bot for OANDA. Modular signal pipeline: direction → momentum → playmaker → step-trail ratchet exit. Live on 8 currency pairs.

## Status

Live since 2026-06-18 on EC2 (Tailscale `[REDACTED-IP]`). 8 pairs: AUD/JPY, AUD/USD, EUR/JPY, EUR/USD, GBP/USD, USD/CAD, USD/CHF, USD/JPY. Dashboard: `https://[REDACTED-HOST]:8084/` — 8 tabs (LIVE / PAIRS / CELLS / INDICATORS / HEALTH / SYSTEM / TUNE / PLAYMAKER) with `?stream=1` and `?mode=overlay` modes for live broadcasting.

Pipeline at a glance:

```
OANDA M5/H1/D feed (5s manage, 300s scan)
   → MarketView (28 dir features incl willr_m5/aroonosc_h1/kc_up_dist/efi/vortex_diff_h1)
   → DirectionModule (per pair × session × direction, 48 cells)  → bias + score + cert
   → MomentumModule  (per pair × session × direction, 48 cells)  → expected_pips + cert
   → Playmaker (cert/score floors + spread gate + per-cell governance + random pick)
        ├── disabled_cells              — cell off entirely (14 cells currently)
        ├── inverted_live_cells         — flip trade direction at execution (9 cells)
        ├── inverted_shadow_cells       — log inversion signal only (2 cells)
        ├── per_cell_mom_cert_min/max   — m_cert floor/ceiling per cell (2 + 2)
        ├── per_cell_dir_cert_min/max   — d_cert floor/ceiling per cell (2 + 1)
        ├── per_cell_willr_range        — willr_m5 [min, max] per cell (1)
        ├── per_cell_kc_up_range        — kc_up_dist_pips [min, max] per cell (1)
        └── random_pick                  — random.choice among actionable (active)
   → Broker (OANDA market order, server-side SL = -20p)
   → RatchetManager (poll 5s, step-trail SL at MFE +7.5/10/12.5/15/17.5/20)
```

All per-cell governance mechanisms are hot-reloadable via config — no restart needed for tuning thresholds. New mechanism types (a new gate kind) require code + restart.

## Where to read more

- **System architecture** → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Signal modules** (direction + momentum, per-(pair × session × direction)) → [docs/MODULES.md](docs/MODULES.md) — supersedes the historical [docs/signal-module-spec.md](docs/signal-module-spec.md)
- **Ratchet exit logic** → [docs/RATCHET.md](docs/RATCHET.md)
- **Playmaker entry gates** → [docs/PLAYMAKER.md](docs/PLAYMAKER.md)
- **Configuration files** → [docs/CONFIGURATION.md](docs/CONFIGURATION.md)
- **Deployment + rollback** → [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **Setup from scratch** → [docs/SETUP.md](docs/SETUP.md)
- **What's next** → [docs/ROADMAP.md](docs/ROADMAP.md)

## Research

All research data, analyses, and per-session findings live under [research/](research/README.md). Master index there describes the methodology of cross-checking new research against prior findings.

Key research artifacts:
- [docs/EDGE_REPORT.md](docs/EDGE_REPORT.md) — V5 edge analysis through 2026-06-18 (direction signal + ratchet amplification + system expectation)
- [research/reference/](research/reference/) — curated Brock-archived V5 test reports (dm05-dm09 + factor_sweep)
- [research/sessions/](research/sessions/) — chronological per-session research with what, why, findings, links to data
- [research/matrices/](research/matrices/) — live-trade matrices that drove module decisions
- [research/live-smoke/](research/live-smoke/) — nightly cron output

## Change history

See [CHANGELOG.md](CHANGELOG.md) — every substantive change with what + why + outcome.

## Repo layout

```
mr-scrooge-v5/
├── README.md                navigation hub (this file)
├── CHANGELOG.md             every change with what/why/outcome
├── docs/                    architecture, modules, config, deployment
│   ├── ARCHITECTURE.md
│   ├── MODULES.md           current state — per-(pair × session × direction)
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
│   ├── README.md            master index + methodology
│   ├── sessions/<yyyy-mm-dd_topic>/
│   ├── matrices/
│   ├── reference/           Brock-curated reports
│   └── live-smoke/          nightly cron output
├── core/                    engine, broker, feed, session map
├── modules/
│   ├── signals/             direction + momentum + their profiles
│   ├── management/          ratchet
│   └── playmaker/           entry gating
├── config/                  exit_config.json, playmaker_config.json, sessions.py
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
edit config/exit_config.json       # SL + ratchet + TP1/TP2
edit config/playmaker_config.json  # account + per-pair gates
```

Or use the TUNE / PLAYMAKER tabs on the dashboard at `:8084` for guarded edits.

## Dashboard

Modern dark UI (rebuilt 2026-06-24). 8 tabs, glass-blur nav, semantic colors (long=cyan, short=magenta, inverted=purple, shadow=slate), JetBrains Mono numerics.

- **LIVE** — giga P/L ticker, equity curve, cell mosaic, account bar, open positions, today's trades, recent events
- **PAIRS** — per-pair signal cards with 15 indicator chips + per-cell rule pass/fail footers
- **CELLS** — 38-cell governance grid with filter/sort/fire counts
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
| `disabled_cells`            | list of [pair, session, dir] | cell has structural negative edge with corroboration (ML + broker + walk-forward) |
| `inverted_live_cells`       | list of [pair, session]     | cell's signal direction is consistently wrong — flip the firing pin |
| `inverted_shadow_cells`     | list of [pair, session]     | shadow-log opposite direction signals to evaluate inversion before commit |
| `per_cell_mom_cert_min`     | dict pair/session → float   | cell's edge IS the high-conviction setup (cert correlates with MFE) |
| `per_cell_mom_cert_max`     | dict pair/session → float   | cell's edge IS the big-move setup (low cert predicts magnitude) |
| `per_cell_dir_cert_min/max` | dict pair/session → float   | direction certainty floor/ceiling — same logic on the direction module |
| `per_cell_willr_range`      | dict pair/session/dir → [lo, hi] | cell only profitable in a specific willr_m5 window |
| `per_cell_kc_up_range`      | dict pair/session/dir → [lo, hi] | cell only profitable when distance to upper Keltner is in a window |
| `per_cell_aroon_range`      | dict pair/session/dir → [lo, hi] | cell only profitable in a specific aroonosc_h1 window (MAE-flip doctrine separator) |
| `inverted_live_directions`  | list of [pair, session, native_dir] | ONE native direction's signal is wired backwards (MAE >> MFE) — flip just that side; XOR with cell-level inversion |
| `random_pick`               | bool                        | spread fire rate across all actionable cells instead of max-composite (for evaluating alternative rankings) |

### 🔒 LOCKED cells — security lock (2026-07-01)

Brock-designated dialed-in cells are **frozen**: they keep trading exactly as validated,
and global / per-pair / per-cell config changes do NOT apply to them unless explicitly
overridden. Registry: `config/locked_cells.json` (baselines + `snapshot` + `overrides`).

- **Enforcement**: `modules/playmaker/lock_guard.py`, wired into `pick_best()`. For a
  locked (pair, session), every gate (session eligibility, disables, inversion, cert
  floors/bounds, willr/kc ranges, cooldown, initial SL) resolves from the lock-time
  `snapshot.governance`, not live config. Divergence is logged as
  `LOCK_GUARD drift ... (using locked)` (rate-limited 1/h per field) and shown in
  `/api/state.lock_guard`.
- **Throttle**: locked traded directions cap at `snapshot.throttle.max_opens_per_session`
  (default 2) per session-instance — engine-level changes (e.g. multi-open) cannot
  multiply a locked cell's exposure. A capped cell falls through to the next candidate.
- **Code-level drift**: restart-required inputs (direction/momentum profiles, factor
  anchors, session hours, exit step params) are fingerprinted at lock time;
  `startup_check()` logs CRITICAL `LOCK_GUARD CODE-DRIFT` on mismatch (alert-only,
  keeps trading).
- **Changing a locked cell**: add an entry to `overrides` in `locked_cells.json`
  ({pair, session, field, value, approved_by, date, note}) — nothing applies silently.
  Re-dialing a cell = update config, then re-run
  `python3 research/tools/lock_snapshot.py --write` to take a fresh snapshot.
- **Audit**: `research/tools/cell_audit.py` tags 🔒 + raises DEGRADING post-lock
  (warning for Brock, not authorization to edit).
