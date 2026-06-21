# V5 corrected analysis — REAL OANDA trade data (not journal-derived)

**Date:** 2026-06-21  
**Period:** 2026-06-12 → 2026-06-21 (~9 days)  
**Source:** OANDA `/v3/accounts/{id}/transactions/idrange` API (not bot journal logs)  
**Total transactions:** 749 (every event: fills, SL changes, manual closes, cancels)  
**Closed trades:** 120 (118 with identifiable side)

## ⚠ My prior conclusions were on bad data

I was reading V5's JOURNAL log, which captures what V5 *thought* happened — not what actually filled at OANDA. The 44-trade matrix CSV missed ~70 trades and didn't distinguish ratchet exits from manual closes. The Master Matrix recommendations from yesterday were derived from this incomplete dataset.

## What the REAL data shows

| Metric | All trades | BOT_EXIT only | MANUAL closes |
|---|---:|---:|---:|
| Count | 118 | 101 | 17 |
| Win rate | 49% | 51% | 29% |
| Total P/L (USD) | **-$6,114** | **-$5,409** | -$705 |
| Mean P/L | -$52 | -$54 | -$41 |

**The bot has been losing $54/trade on average over the last 9 days.** Manual closes were 17 trades (14% of the total) — these were *your* exits during V4→V5 cutover, not bot decisions.

### V4 vs V5 era split

V5 cutover was 2026-06-18 19:04 UTC.

| Era | Trades | BOT_EXIT | Manual | P/L (all) | P/L (BOT_EXIT) | WR |
|---|---:|---:|---:|---:|---:|---:|
| V4 (06-12 → 06-18 19:04) | 82 | 77 | 5 | -$3,881 | -$4,184 | 53% |
| **V5 (06-18 19:04 → present)** | **36** | **24** | **12** | **-$2,234** | **-$1,225** | **44%** |

V5 has been live ~50 hours and has 24 bot-exit trades. **33% of V5-era trades got manually closed** — much higher than V4. That's the V5 cutover effect (you closing V4 positions to bring V5 online).

## Per-cell stats — REAL trades (BOT_EXIT only, all era, n≥3)

| Pair | Sess | Side | n | WR | Mean P/L | Total P/L | V5 current profile |
|---|---|---|---:|---:|---:|---:|---|
| **USD_CAD ny long** | 8 | **75%** | +$63 | **+$503** | reversion MODERATE |
| **USD_CHF london long** | 6 | **83%** | +$29 | **+$174** | continuation_strong MODERATE |
| **EUR_USD london short** | 7 | 71% | +$20 | +$138 | reversion MEDIUM |
| **AUD_JPY asia short** | 6 | 83% | +$7 | +$43 | continuation_strong STRONG |
| USD_JPY asia short | 7 | 71% | -$9 | -$61 | continuation_strong MEDIUM_STRICT |
| AUD_JPY london long | 3 | 67% | -$39 | -$116 | reversion BAD |
| AUD_USD asia short | 4 | 50% | -$54 | -$215 | continuation_strong MEDIUM |
| GBP_USD ny long | 4 | 50% | -$61 | -$243 | default NO_DATA |
| AUD_JPY london short | 3 | 33% | -$92 | -$277 | default WEAK |
| EUR_JPY ny long | 3 | 33% | -$99 | -$297 | continuation_strong WEAK |
| **GBP_USD ny short** | 5 | 40% | -$69 | **-$344** | reversion STRONG |
| **USD_CHF ny long** | 5 | 40% | -$90 | **-$448** | reversion MODERATE |
| **EUR_JPY london short** | 5 | 20% | -$147 | **-$737** ⚠ | reversion BAD |

## Per-cell × feature correlation findings

For cells with **n≥5** REAL trades, features that correlate with win/loss (|corr| > 0.5):

### USD_CAD ny long (8 trades, 75% WR, +$503) — V5's STAR cell
- `q_willr_m5` +0.573 (high Williams %R = win)
- `bb_pos` +0.568 (high BB pos = win)
- `q_cci_m5` +0.557 (high CCI = win)
- `q_mfi` +0.549 (high MFI = win)
- `zscore_1h` +0.554 (high zscore = win)
- `q_vortex_diff_h1` +0.544 (high Vortex = win)

**This cell wins on CONTINUATION/MOMENTUM signals, not reversion.** V5 has it as `reversion MODERATE` — that's WRONG per the live data. Should be `continuation_strong`.

### USD_CHF london long (6 trades, 83% WR, +$174)
- Few strong feature correlations at this sample size
- V5 has `continuation_strong MODERATE` — live confirms (83% WR)

### EUR_USD london short (7 trades, 71% WR, +$138)
- `q_willr_m5` -0.573 (LOW willr = win)
- `rvol_5bar` -0.517 (LOW vol = win)
- `q_kc_up_dist_pips` -0.513
- `q_cmf` -0.508 (LOW money flow = win)

**This cell wins on REVERSION/QUIET-MARKET signals.** V5 has it as `reversion MEDIUM` — CORRECT per the live data.

### AUD_JPY asia short (6 trades, 83% WR, +$43)
- `q_mfi` -0.565 (LOW MFI = win)
- `atr_conc` -0.565 (LOW vol concentration = win)
- `atr_5m` -0.508 (LOW vol = win)

**Wins in quiet, low-volatility conditions.** V5 has it as `continuation_strong STRONG` — debatable; the live data suggests reversion-style would be more accurate.

### GBP_USD ny short (5 trades, 40% WR, -$344) — LOSER cell
- `h1_ret_1bar` -0.570 (LOW h1_ret = win short)
- `q_chop_h1` -0.554 (LOW chop = trending down = win short)

**This cell could be SAVED** by filtering: only take when h1_ret_1bar < 0 AND q_chop_h1 is low.

### EUR_JPY london short (5 trades, 20% WR, -$737) — DISASTER cell
- `q_bbwp_m5` +0.572
- `q_chop_h1` +0.559
- `q_adx_h1` +0.509

The 1 winning trade fired at HIGH BBWP + HIGH ADX. **The other 4 (losers) fired at low ADX.** Could filter: only short when ADX > X.

### USD_CHF ny long (5 trades, 40% WR, -$448) — LOSER cell
- `bb_pos` -0.555 (LOW bb_pos = win long; reversion!)
- `q_cci_m5` -0.515 (LOW CCI = win)
- `q_efi` -0.508
- `htf_pct_20` -0.511

**V5 has reversion MODERATE here — correct intent but the bot isn't filtering tight enough.** Should only fire when bb_pos is genuinely low (oversold).

## What this changes about yesterday's Master Matrix conclusions

| Yesterday's claim | What real data shows |
|---|---|
| "AUD_JPY/asia/short 80% WR 5 trades" | 83% WR 6 trades ✓ holds (slightly better) |
| "AUD_USD/asia/short 75% WR 4 trades" | 50% WR 4 BOT_EXIT trades (60% all) — was inflated |
| "USD_CAD/ny/long 50% WR 4 trades" | **75% WR 8 trades, +$503** — STAR cell I missed |
| "USD_CHF/london/long 67% WR 3 trades" | 83% WR 6 trades — better than I said |
| "GBP_USD/ny/short 25% WR 4 trades" | 40% WR 5 trades (still bad) |
| "AUD_USD/ny long+short: 0 live trades → DISABLE" | 1 V4-era trade lost -$293 (V5-era: 0); disable still defensible |
| "USD_CHF/ny/long 33% WR 3 trades" | 40% WR 5 trades, -$448 (worse than I said) |
| "EUR_USD/ny/short 0% WR 2 trades" | 0% WR 1 BOT_EXIT trade (-$8); 0% WR 3 all-class (-$324) |

**The 5 cells I just DISABLED still look defensible**: AUD_USD/ny long had 1 V4 trade that lost big, AUD_USD/ny short 0 trades, USD_CHF/london/short 0, USD_CAD/ny/short 0 (USD_CAD/ny LONG is the winner, the short side never fired), EUR_USD/ny/long 0. **None of the disabled cells are V5 STAR cells.** The disable was right.

## What I'd actually change now (corrected recommendations)

1. **USD_CAD/ny/long: switch from `reversion` to `continuation_strong`** — REAL trade data (8 trades, 75% WR, +$503) shows momentum-style continuation wins, not reversion. V5's current assignment is FIGHTING the cell's natural edge.

2. **Investigate EUR_JPY/london/short** — 5 trades, 20% WR, -$737 single-cell loss. Either tighten filter (only when ADX > X) or DISABLE. V5 has it as reversion BAD already, but the bot keeps firing into it.

3. **Investigate USD_CHF/ny/long** — 5 trades, 40% WR, -$448. V5 has reversion MODERATE which is right INTENT, but filter is too loose. The cell wins only when bb_pos is genuinely low.

4. **Don't wire `q_willr_m5` globally** — it correlates POSITIVELY with win in USD_CAD/ny/long (+0.573) and NEGATIVELY in EUR_USD/london/short (-0.573). Per-cell logic only.

5. **My shadow Vortex wiring is still useful** — gathers more data going forward. Don't roll back.

6. **My 5-cell disable list is still defensible** — confirmed against real data.

## Sample-size honesty

- 24 V5-era BOT_EXIT trades is too small for stable per-cell stats
- 101 BOT_EXIT trades across V4+V5 give better per-cell n but mix two different bot versions
- 95% CI on correlation at n=5 is roughly ±0.7 — most "n=5 correlation" findings could be noise
- Even at n=8 (USD_CAD/ny/long, V5's best cell), CI is ±0.6 — the +0.57 correlations are SUGGESTIVE not CONCLUSIVE

**The honest read:** V5 is losing money. The current profile assignments are partially correct (some cells like EUR_USD/london/short work) and partially wrong (USD_CAD/ny/long should be continuation, not reversion). The bot needs either a per-cell config tune-up OR more selective entry filters to stop the bleeding in the losing cells.

## Reproduction

```bash
# EC2 — pull OANDA trade history (needs OANDA_API_TOKEN in ~/.openclaw/secrets.env)
/home/ubuntu/mr_burns_env/bin/python /tmp/v5_pull_oanda_trades.py
# Outputs: /tmp/oanda_all_classified.csv

# Ship to Mini, then enrich with indicators at entry time
~/.venvs/quantalib/bin/python ~/qtl-discovery-8yr/v5_enrich_real_trades.py
# Outputs: ~/qtl-discovery-8yr/real_trade_analysis/{real_trades_enriched.csv, per_cell_*.csv}
```

## Open follow-ups (NOT done in this session)

- **Flip USD_CAD/ny/long from `reversion` to `continuation_strong`** in direction_profiles.py — biggest WR-impact change with real evidence behind it
- **Add per-cell ENTRY filters** for the losing cells (e.g., USD_CHF/ny/long only fires when bb_pos < X)
- **Live trade replay** — for each candidate filter rule, simulate "would this have blocked the bot's losing trades while letting winners through" using the enriched real-trade dataset
- **Monthly cron should pull OANDA trades** not just journal — update `master_matrix_monthly.sh` to call `v5_pull_oanda_trades.py` then `v5_enrich_real_trades.py`
