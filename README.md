<img width="900" height="900" alt="Scrooge Money" src="https://github.com/user-attachments/assets/df689e08-0799-414d-b7f6-7dec7a645813" />

# Mr. Scrooge V5

Automated forex trading bot for OANDA. Modular signal pipeline: direction → momentum → playmaker → step-trail ratchet exit. Live on 8 currency pairs.

## Status

Live since 2026-06-18 on EC2 (Tailscale `[REDACTED-IP]`). 8 pairs: AUD/JPY, AUD/USD, EUR/JPY, EUR/USD, GBP/USD, USD/CAD, USD/CHF, USD/JPY. Dashboard: `https://[REDACTED-HOST]:8084/`.

Pipeline at a glance:

```
OANDA M5/H1/D feed
   → MarketView (24 dir features + 10 mom features + aggregators)
   → DirectionModule (per pair × session × direction, 48 cells)  → bias + score + cert
   → MomentumModule  (per pair × session × direction, 48 cells)  → expected_pips + cert
   → Playmaker (cert/score floors + spread gate + tournament)    → winning ticket
   → Broker (OANDA market order, server-side SL = -20p)
   → RatchetManager (poll 30s, trail SL up as price runs)
```

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
