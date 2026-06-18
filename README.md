# Mr. Scrooge V5

Automated forex trading bot for OANDA. Modular ML pipeline: direction signal → momentum filter → playmaker decision → step-trail ratchet exit management. Live on 8 currency pairs, 5-minute cycle.

---

## Expected Performance

Full analysis in [docs/EDGE_REPORT.md](docs/EDGE_REPORT.md).

| Metric | Value |
|--------|-------|
| Direction accuracy (module level) | 70-73% London / 70-72% Asia / 69-73% NY |
| Estimated trade win rate | 65-70% |
| E[pip/trade] gross of spread | +3.3-4.9p |
| E[pip/trade] net of spread | +2.5-4.0p |
| Initial stop-loss | -15p from entry |
| Edge classification | **HIGH** |
| Research basis | 8-year OOS walk-forward, all 8 pairs |
| Live confirmation | Pending — V5 launched 2026-06-18 |

**The ratchet is essential.** Without the 6-pip step-trail exit, the same signal produces +0.75p/trade (LOW edge). The ratchet converts the 70%+ of trades that run 20+ pips MFE into locked profits, lifting expectation to the +3-5p range.

**London is strongest.** EUR/JPY, USD/JPY, and GBP/USD London are the widest cells (28-30p D1-D10 span). Asia and NY are real but smaller.

**These are backtested numbers.** 8-year walk-forward, year-by-year stability verified. Allow 50-100 live trades before drawing conclusions about live vs backtest alignment.

---
## Architecture

```
 ┌─────────────────────────────────────────────────────────────────────────┐
 │  main.py  →  Engine  (core/engine.py)  ──  5-min cycle loop           │
 └─────────────────────────────────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
 ┌──────────────┐          ┌────────────────┐
 │  OandaFeed   │          │  OandaBroker   │
 │(core/feed/   │          │(core/broker/   │
 │  oanda.py)   │          │  oanda.py)     │
 │              │          │                │
 │ • M5/H1/D    │          │ • place_market │
 │   candles    │          │ • close_pos    │
 │ • 22+ field  │          │ • move_stop    │
 │   MarketView │          │ • account_nav  │
 └──────┬───────┘          └────────┬───────┘
        │                           │
        │  list[MarketView]         │  broker calls
        ▼                           │
 ┌────────────────────────────────┐ │
 │  Signal Modules                │ │
 │  (modules/signals/)            │ │
 │                                │ │
 │  DirectionModule × 24          │ │  PairTicket per pair
 │  ┌──────────────────────────┐  │  ─────────────────────────────────────
 │  │ dm_04 calibration (24    │  │
 │  │ features, 8 pairs ×      │  │
 │  │ 3 sessions)              │  │
 │  │ → DirectionStamp         │  │
 │  │   bias: long/short/block │  │
 │  │   score:  −1.0 .. +1.0   │  │
 │  │   certainty: 0..1        │  │
 │  └──────────────────────────┘  │
 │                                │
 │  MomentumModule × 24           │
 │  ┌──────────────────────────┐  │
 │  │ vol_regime: low/norm/    │  │
 │  │   high/extreme           │  │
 │  │ expected_pips: ~pips/hr  │  │
 │  │ certainty: 0..1          │  │
 │  └──────────────────────────┘  │
 └────────────────┬───────────────┘
                  │  list[PairTicket]
                  ▼
 ┌────────────────────────────────┐
 │  Playmaker  (modules/playmaker)│
 │                                │
 │  pick_best(tickets):           │
 │  • dir certainty ≥ 0.30        │
 │  • mom certainty ≥ 0.25        │
 │  • dir score ≥ 0.25            │
 │  • spread gate                 │
 │  • no duplicate pair           │
 │  • ranked by composite_score   │
 │    = score × dir_cert × mom_cert│
 │                                │
 │  → TradeTicket (or None)       │
 └────────────────┬───────────────┘
                  │
                  │  OandaBroker.place_market()
                  │  → SL at −15p server-side
                  ▼
 ┌────────────────────────────────┐
 │  RatchetManager                │
 │  (modules/management/ratchet)  │
 │                                │
 │  6-pip step-trail exit         │
 │  config: exit_config.json      │
 │  (live-editable, no restart)   │
 │                                │
 │  Ladder (trigger=10p, step=5p, │
 │  trail=6p):                    │
 │    peak <10p  → SL at −15p     │
 │    peak ≥10p  → SL at +4p      │
 │    peak ≥15p  → SL at +9p      │
 │    peak ≥20p  → SL at +14p     │
 │    peak ≥25p  → SL at +19p     │
 │    (uncapped, every 5p step)   │
 │                                │
 │  update() every 5 min:         │
 │  1. peak tracking              │
 │  2. cadence check (20 min)     │
 │  3. broker.move_stop() if SL   │
 │     advances                   │
 │  4. server-side exit detection │
 └────────────────────────────────┘

 Dashboard  ──  ops/panel.html  served on :8095
 ┌────────────────────────────────────────────┐
 │  LIVE   │  PAIRS  │  HEALTH  │  SYSTEM    │
 │  acct   │  signal │  engine  │  cpu/ram   │
 │  pos +  │  cards  │  health  │  services  │
 │  ratchet│  per    │  per     │  journal   │
 │  state  │  pair   │  pair    │  log       │
 └────────────────────────────────────────────┘
```

---

## Directory Layout

```
mr-scrooge-v5/
├── main.py                   # Entry point: --live flag for live trading
├── config/
│   ├── pairs.py              # 8-pair PAIRS list + PIP sizes
│   └── exit_config.json      # Live-editable ratchet config
├── core/
│   ├── engine.py             # Main cycle loop + position management
│   ├── feed/
│   │   └── oanda.py          # OandaFeed: MarketView builder (22+ fields)
│   └── broker/
│       └── oanda.py          # OandaBroker: order + account REST wrapper
├── modules/
│   ├── signals/
│   │   ├── base.py           # MarketView, PairTicket, DirectionStamp, MomentumStamp
│   │   ├── direction.py      # DirectionModule (dm_04 calibration)
│   │   └── momentum.py       # MomentumModule
│   ├── playmaker/
│   │   └── playmaker.py      # pick_best() + gate floors
│   └── management/
│       ├── base.py           # Position, ExitSignal, TradeManager dataclasses
│       └── ratchet.py        # RatchetManager: 6-pip step-trail
├── ops/
│   ├── panel.html            # Dashboard HTML (4 tabs)
│   └── server.py             # HTTP server thread (port 8095)
├── docs/
│   └── research/             # ML research artifacts (dm05–dm09, factor_sweep)
└── tests/
```

---

## Pairs

```
EUR_USD  GBP_USD  AUD_USD  USD_JPY
USD_CAD  USD_CHF  AUD_JPY  EUR_JPY
```

All 8 pairs run the same management + entry + exit stack. PIP sizes: non-JPY = 0.0001, JPY pairs = 0.01.

---

## Ratchet Config (`config/exit_config.json`)

Live-editable — engine re-reads on each 20-min cadence check, no restart needed.

| Key | Default | Meaning |
|---|---|---|
| `step_engage_min` | 0.0 | Minutes before first check (0 = immediate) |
| `step_cadence_min` | 20.0 | Minutes between SL evaluation cycles |
| `step_trigger_pips` | 10.0 | Peak MFE required before first SL movement |
| `step_size_pips` | 5.0 | Ratchet step size |
| `step_trail_pips` | 6.0 | SL parks this many pips behind step level |

**Lock ladder** (defaults): 10p → +4p, 15p → +9p, 20p → +14p, 25p → +19p, ...

Initial SL: **−15p** from entry (placed server-side at order fill).

---

## Playmaker Gate Floors

Data-derived from dm_04 calibration:

| Gate | Floor |
|---|---|
| `MIN_DIRECTION_SCORE` | 0.25 |
| `MIN_DIR_CERTAINTY` | 0.30 |
| `MIN_MOM_CERTAINTY` | 0.25 |

Spread gate: candidate dropped if spread > 3p (non-JPY) / 5p (JPY).

---

## Feed Features (MarketView)

22+ fields computed from OANDA M5/H1/D candles each cycle:

| Field | Source | V5 Use |
|---|---|---|
| `h1_ret_1bar` | H1 bar return | Direction: trend strength |
| `h1_ret_4bar` | 4-bar H1 sum | Direction: multi-bar trend |
| `rsi14` | H1 Wilder RSI-14 | Direction: OB/OS |
| `rsi_slope` | 2-bar RSI delta | Direction: momentum |
| `zscore_1h` | H1 Z-score vs SMA20 | Direction |
| `ema20_1h_dist` | H1 EMA20 dist | Direction |
| `htf_pct_20` / `htf_pct_60` | H20/H60 signed pct | Direction: HTF alignment |
| `pdh_dist` / `pdl_dist` | Price vs prev-day high/low | Direction: level proximity |
| `adr_consumed` | Daily range consumed | Momentum: vol context |
| `d_ret` | Running daily return | Direction: daily bias |
| `spread_pips` | Live bid/ask spread | Playmaker gate |
| `atr14_h1` | H1 Wilder ATR-14 | Momentum: vol regime |

---

## Credentials

All in `~/.openclaw/secrets.env` on EC2 (chmod 600). Never stored in code.

```
OANDA_API_URL=
OANDA_API_TOKEN=
OANDA_ACCOUNT_ID=
GITHUB_TOKEN_SCROOGE_V5=
```

---

## Operations

```bash
# Live trading (EC2)
systemctl --user start mr-scrooge-v5

# Dry run (signals only, no orders)
python main.py

# Live run directly
python main.py --live

# Dashboard
open https://[REDACTED-HOST]:8084/

# Tail logs
journalctl --user -u mr-scrooge-v5 -f -o cat

# Edit ratchet config live (no restart)
nano config/exit_config.json

# Run tests
python -m pytest tests/ -v
```

---

## Git Remotes

```
origin  → github.com/BrockStar3540/mr-scrooge-v5   (GITHUB_TOKEN_SCROOGE_V5)
alien   → brock-mini-mac@[REDACTED-IP]:git-mirrors/mr-scrooge-v5.git
```

Deploy: push EC2 → origin, then `git push alien main`.

---

## Version History

| Version | Date | Notes |
|---|---|---|
| V5 (current) | 2026-06-18 | Modular ML pipeline, 6p step-trail ratchet, 8 pairs |
| V4 (retired) | 2026-06-18 | Brain-gated strategy pipeline, BUCKET21-v3 |
| V3 (archived) | 2026-06-16 | Original shadow-mode bot |
