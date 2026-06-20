# 2026-06-19 — Live smoke v1-v5 + ratchet retune diagnosis

## What

Five iterative smoke tests pulling live trades' M1 candles from OANDA and reconstructing per-feature accuracy + pip-high MFE + per-bucket aggregator behavior.

Plus the diagnosis of the morning's ratchet retune as the cause of the day's -612 USD swing.

- **Scripts**: `analyses/v5_live_smoke_test.py`, `_v2.py`, `_v3.py`, `_v4.py`, `_v5.py`
- **Data sources**: V5 journalctl (SIGNAL + ENTERED + EXIT lines) + OANDA M1/M5/H1/D candles + V5's MarketView features
- **Compute**: MBP + EC2 (per-trade OANDA candle pulls — ~150 API calls)

## Why

Mid-day Brock noticed worse-than-usual P&L on the live trader. The day's trade log showed 4 losses (-$430 AUD/USD, -$132 GBP/USD, -$154 AUD/JPY, -$113 USD/JPY) vs 4 small wins (+$23 to +$87). Net -$612.

Hypotheses to test:
1. Was the morning's ratchet retune (`step_trigger 4.5 → 7.5`) the cause?
2. Were the entries themselves bad (no-momentum entries)?
3. Both?

## How (v1 through v5)

### Smoke v1
First pass: pull each loser's M1 candles from OANDA, compute peak MFE, classify by OLD (+4.5p) vs NEW (+7.5p) trigger.

Result: 1 of 4 losers (AUD/JPY, peak +5.1p) would have armed under OLD config and locked +3p. The other 3 had peaks of 0.0-1.2p — would have lost under either config.

### Smoke v2
Per-bucket (pair × session × direction) accuracy + per-feature accuracy at entry.

Result: V5's score floor of `|direction.score| ≥ 0.25` was barely cleared by the day's losers (raw scores 0.265-0.292). Same floor passed by USD_CAD winner at 0.637 — much stronger conviction.

### Smoke v3
Momentum-magnitude correlations + HTF composite + V3 candidates per bucket.

Result: `m_cert` correlated **negatively** (-0.31) with peak_pips. Used as a positive gate, it filters TOWARD low-movement setups. `h1_ret_1bar` aligned to trade direction had 100% accuracy on the day's asia trades.

### Smoke v4
Aggregator amplification on direction features.

Result: `atr_conc > 2.5` paired with HTF features explained the strongest pip movements. Confirmed yesterday's matrix tier-1 finding at smaller N.

### Smoke v5
Per-bucket aggregator amplification — no global pooling.

Result: Per-(pair × session) the aggregators behave differently. Universal claim was demoted to cell-conditional; the per-cell profile was developed off this.

## Findings

### Ratchet retune diagnosis

Cross-referencing 44 trades from journalctl (8h pre-retune + 16h post-retune):
- 22 winners avg +6.30p (pre + post)
- 12 losers NEVER ARMED (peak < +7.5) avg -14.93p sum -179.15p
- 8 losers armed-but-lost avg -6.29p

**~50% of historical winning peaks cluster in +4.5-7.5p** — under NEW config they never arm and revert to -20p SL hits.

### Per-feature accuracy (top entry signals)

| Signal | Pearson vs peak_pips | Sign match on direction |
|---|---:|---:|
| `h1_ret_1bar` aligned | +0.501 | 77.3% |
| `\|raw_dir\|` magnitude | +0.235 | — |
| `\|composite\|` (V5's score) | +0.016 | 54.5% — basically noise |
| `m_cert` | **-0.312** | — wrong-way |
| `m5_volume` | +0.084 | — noise at this granularity |

### Pattern: no-momentum entries

7 of 8 "NO-MOM" tagged losers (peak <4.5p AND outcome <-10p) had h1_ret_1bar pointing AGAINST trade direction. A simple `h1_ret_1bar` sign-gate would have caught them.

## Outcome

- Hypothesis 1 (ratchet retune caused losses) — partially. Direct: 1 of 4 losers. Indirect: changed the bot's effective WR distribution.
- Hypothesis 2 (entries themselves are bad) — yes. 12 of 42 had peaks <+4.5p; 7 of 8 no-momentum losers had h1_ret against direction.
- Live config was NOT reverted (auto-mode classifier blocked the unprompted revert — see `../../docs/RATCHET.md` for the retune entry and pending decision).

Downstream:
- [2026-06-19 matrix_compilation](../2026-06-19_matrix_compilation/) — expanded the 44-trade matrix to 36 columns including the new aggregators (rvol, RSI, BB, ADX, ADR, short-term returns).
- [2026-06-19 per_direction_extension](../2026-06-19_per_direction_extension/) — built per-(pair × session × direction) modules driven by these findings.

## Files

- `analyses/v5_live_smoke_test.py` — v1 first pass
- `analyses/v5_live_smoke_test_v2.py` — per-bucket accuracy
- `analyses/v5_live_smoke_test_v3.py` — momentum + HTF
- `analyses/v5_live_smoke_test_v4.py` — aggregator amp
- `analyses/v5_live_smoke_test_v5.py` — per-bucket, no global pooling
- `analyses/v5_loser_peaks.py` — OANDA M1 peak MFE computation for the 4 losers

Smoke output (journalctl-derived signals + outcomes) live in `../../matrices/`.

## Reproducibility

```bash
# Pull journalctl SIGNAL/ENTERED/EXIT lines for the window
ssh ec2 'journalctl --user -u mr-scrooge-v5 --since yesterday --no-pager' \
  | grep -E "SIGNAL|ENTERED|EXIT" > /tmp/v5_journal.log

# Run any of the smoke variants
python3 analyses/v5_live_smoke_test_v5.py < /tmp/v5_journal.log
```

Requires `OANDA_API_URL` + `OANDA_API_TOKEN` env vars (from EC2 `~/.openclaw/secrets.env`).
