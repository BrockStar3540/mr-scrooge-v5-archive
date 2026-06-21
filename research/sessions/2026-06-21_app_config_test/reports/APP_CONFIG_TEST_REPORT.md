# App-style config test — do RSI/EMA/StochRSI MTF configs predict 1H direction?

**Date:** 2026-06-21
**Question (Brock):** Do these app-style configurations actually improve one-hour forecast accuracy, or are they just visually persuasive?
**Answer: Visually persuasive only. Zero forecast edge at any horizon. The multi-timeframe alignment that looks authoritative in the app adds NOTHING — it just thins the signal count.**

## Method (exactly as specified)

- **8yr corpus, 8 pairs, every M5 bar scanned mechanically** — not app alerts (avoided "the mistake" in §9)
- RSI(7) / EMA(5,20) / StochRSI(14,5,3) computed on M5→M15→M30→H1→H4 resampled OHLC
- Signal = M15 RSI(7) crosses 50 (+ each config's filters)
- **910,406 total signals** across 8 configs (260,517 raw RSI crosses alone)
- For each signal: signed forward pip at 15 / 30 / 60 / 90 / 120 min. Buy = +move, Sell = −move. Positive = signal was right.
- Mid-price (no spread) — so every number below is **before** the 1-2 pip spread cost
- Compute: 2.5 seconds on Mini, 8 cores

## THE TABLE (Brock's format) — ranked by expectancy

| Config | Signals | Win % | Avg 60m Pips | Median | PF | Expectancy |
|---|---:|---:|---:|---:|---:|---:|
| 5 · RSI cross + EMA M15 state | 111,205 | 47.9% | **−0.12** | −0.3 | 0.97 | **−0.18** |
| 6 · RSI cross + EMA M30 state | 113,474 | 47.8% | −0.12 | −0.3 | 0.97 | −0.19 |
| 1 · RSI(7) M15 cross only | 260,517 | 48.0% | −0.15 | −0.2 | 0.96 | −0.21 |
| 4 · RSI + M30/H1/H4 align | 68,943 | 47.6% | −0.15 | −0.3 | 0.96 | −0.21 |
| 2 · RSI + M30 align | 118,801 | 47.7% | −0.16 | −0.3 | 0.96 | −0.22 |
| 3 · RSI + M30/H1 align | 90,054 | 47.5% | −0.16 | −0.3 | 0.96 | −0.22 |
| 7 · RSI align + EMA state | 74,657 | 47.6% | −0.16 | −0.3 | 0.96 | −0.22 |
| 8 · Full + StochRSI filter | 72,755 | 47.6% | −0.16 | −0.3 | 0.96 | −0.22 |

**Every single config: win rate < 48%, negative expectancy, profit factor < 1.0. Before spread.**

## The three findings that matter

### 1. The filters are decorative — they don't select better signals
Config 1 (raw RSI cross) = −0.21 expectancy on 260k signals. Config 8 (the full stack: RSI cross + M30/H1 RSI agree + EMA M15 state + StochRSI not extreme) = **−0.22 expectancy on 73k signals.** Adding 4 confirmation layers reduced sample by 72% and made expectancy *very slightly worse*. The multi-timeframe alignment removes signals **at random** with respect to outcome — it is not informative. This directly refutes the §12 prediction that "RSI + M30/H1 alignment is the best improvement-to-complexity ratio." It isn't an improvement at all.

### 2. The signal slightly ANTI-predicts at EVERY horizon
Mean signed pip by horizon (config 1):

| 15m | 30m | 60m | 90m | 120m |
|---:|---:|---:|---:|---:|
| −0.118 | −0.144 | −0.151 | −0.148 | −0.162 |

It's negative at 15 min and stays negative through 120 min. **RSI(7) M15 crossing 50 is a lagging exhaustion marker** — by the time the cross prints, the move is done and price mean-reverts slightly. It is not early, not timely, not late-but-right. It's just slightly wrong, consistently.

### 3. It's symmetric noise with huge variance
avg_win +8.1p, avg_loss −7.9p, WR 48%, **std 12.7p** on a −0.15p mean. Tail symmetry: 32.2% reach +3p / 34.5% reach −3p; 24.3% reach +5p / 25.7% reach −5p. The distribution is a coin flip nudged slightly toward losing.

## Session split — the only texture in the data

Expectancy by session (60m), all configs roughly agree:

| | asia | london | ny | overlap |
|---|---:|---:|---:|---:|
| RSI cross only | −0.16 | **−0.09** | −0.43 | −0.13 |
| RSI + EMA M15 state | −0.13 | **+0.05** | −0.50 | −0.19 |

- **London is the only non-terrible session** (roughly flat, occasionally barely positive).
- **NY session is actively destructive** (−0.4 to −0.5). RSI-cross signals in NY are the worst.
- This matches §8's intuition that crosses behave differently by session — but even London's "best" case is break-even, not an edge.

## Is there ANY cell where it works?

Scanned all 256 (config × pair × session) cells with n≥200:
- **7 cells** have expectancy > +0.5p (all EUR_JPY or USD_CAD in the *overlap* session — tiny n=660-1230)
- **35 cells** have expectancy < −0.5p (signal anti-predicts; EUR_JPY/ny and EUR_USD/overlap most reliably)

**5× more cells where the signal is reliably WRONG than reliably right.** The 7 "positive" cells are almost certainly overfitting noise — there's no structural reason EUR_JPY-overlap-only would carry edge while every other slice doesn't. If anything, the cleaner signal is the *fade*: EUR_JPY/ny RSI crosses anti-predict at −1.0p across configs (n=2,500-4,000), which is more sample and more consistent than any "winning" cell.

## Bottom line for V5

**Do not wire any of these app configs into V5's direction engine.** They have no forecast edge — they are alert-generators that look authoritative because the multi-timeframe RSI panel is visually convincing, not because the timeframes agreeing means anything for the next 60 minutes.

This is the same lesson as the broker-validation session: **a signal that looks right on a chart (or in an app's confluence panel) is not the same as a signal that predicts forward price.** The only honest test is "scan every occurrence, measure the forward move" — which is what this did, and the answer is no edge.

What V5 already has (the per-cell direction_v2 profiles tuned on 8yr ML + broker-validated forward pip) is a *better* foundation than this app logic, despite V5 currently losing money — because V5's framework at least selects on measured forward edge per cell, whereas RSI-cross-confluence selects on nothing.

### One thing worth a follow-up
The **fade** direction shows more consistency than the long direction. If there's anything here, it's that RSI(7) M15 50-crosses are slightly contrarian — but at −0.15p pre-spread it's not tradeable as a standalone fade either. Not worth pursuing as a primary signal; possibly worth testing RSI-cross *exhaustion* as a small negative weight in a cell that's otherwise mean-reverting.

## Reproduction

```bash
# On Mini:
~/.venvs/quantalib/bin/python ~/qtl-discovery-8yr/v5_app_config_tester.py   # 2.5s, writes all_signals_raw.csv (145MB)
~/.venvs/quantalib/bin/python ~/qtl-discovery-8yr/v5_app_horizons.py        # multi-horizon + per-cell breakdown
```

## Not tested (deferred — would not change the conclusion)
- RSI divergence (Config D / 8 in §6) — requires pivot detection; given the primary RSI signal has zero edge, divergence as a *modifier on it* can't rescue a dead base signal. Worth a separate test only if a base signal with real edge is found first.
- Per-pair-group (majors vs JPY vs crosses) beyond the per-pair view — the per-pair best cells were all still negative (−0.08 to −0.14 expectancy), so grouping won't surface a hidden winner.
- StochRSI/EMA as *standalone* direction (§5 Phase 1) — config 5/6 already show EMA-state adds nothing on top of RSI; standalone would be weaker.
