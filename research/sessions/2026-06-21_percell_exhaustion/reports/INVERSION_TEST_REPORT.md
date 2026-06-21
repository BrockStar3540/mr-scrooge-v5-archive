# Can the NY momentum-fade cells be run INVERTED?

**Date:** 2026-06-21
**Question (Brock):** If NY momentum fades, can those cells just be run inverted (trade the opposite)?
**Short answer:** Directionally yes — the fade is walk-forward robust (8/8 pairs) and concentrates in the strong-momentum signals where V5 fires. But economically it's **marginal net of spread, and cell-specific — NOT a blanket "flip all NY cells."** Two cells look genuinely worth inverting; one must NOT be inverted (it's the star).

## Q1 — All-bars: does the fade strengthen where V5 fires? YES.

Bucketing NY bars by momentum extremity (RSI7_M5 distance from 50), TEST window 2024-2026, mean across pairs:

| Momentum bucket | follow exp | invert exp | invert net spread | invert WR |
|---|---:|---:|---:|---:|
| q1 (weak) | −0.033 | +0.033 | −1.48 | 49.8% |
| q2 | −0.119 | +0.119 | −1.39 | 51.3% |
| q3 | −0.289 | +0.289 | −1.22 | 52.3% |
| q4 | −0.375 | +0.375 | −1.14 | 53.6% |
| **q5 (strong)** | **−0.728** | **+0.728** | **−0.79** | **54.6%** |

The fade is monotonic in momentum strength — the stronger the momentum signal, the harder it fades. Inverting the strong signals gives +0.73p gross and 54.6% win rate. **This is exactly where V5 fires** (it only trades strong composite signals), so V5's actual entries fade harder than a random NY bar.

**Walk-forward: 8/8 pairs have positive invert in BOTH train and test.** The fade DIRECTION is rock-solid out-of-time. But...

## Q1 net of spread — only 1 of 8 pairs clears at the all-bars level

q5-strong invert expectancy minus typical spread, per pair (TEST):

| Pair (NY) | invert gross | spread | **invert net** |
|---|---:|---:|---:|
| **USD_JPY** | +1.09 | 1.0 | **+0.09** ✓ |
| EUR_USD | +0.76 | 1.0 | −0.24 |
| EUR_JPY | +1.17 | 1.8 | −0.63 |
| AUD_USD | +0.45 | 1.2 | −0.75 |
| GBP_USD | +0.52 | 1.5 | −0.98 |
| USD_CHF | +0.73 | 1.8 | −1.07 |
| AUD_JPY | +0.80 | 2.0 | −1.20 |
| USD_CAD | +0.31 | 1.8 | −1.49 |

At all-bars selectivity, only USD_JPY/ny clears spread, and only barely. The wide-spread pairs (EUR_JPY, AUD_JPY, USD_CHF, USD_CAD at 1.8-2.0p) have large gross fade that spread eats entirely.

## Q2 — Inverting V5's ACTUAL NY broker trades (the real test)

V5's real entries are far more selective than the top-20% bucket. Inverting the 43 actual NY broker trades (flip the direction, measure forward 1H, net of spread):

| Pair (NY) | n | actual fwd | inverted fwd | **invert net spread** | invert WR |
|---|---:|---:|---:|---:|---:|
| **USD_JPY** | 3 | −11.37 | +11.37 | **+10.37** | 67% |
| **GBP_USD** | 10 | −4.46 | +4.46 | **+2.96** | 60% |
| **EUR_JPY** | 4 | −4.25 | +4.25 | **+2.45** | 50% |
| AUD_USD | 1 | −2.40 | +2.40 | +1.20 | 100% |
| EUR_USD | 5 | −1.32 | +1.32 | +0.32 | 60% |
| USD_CHF | 7 | −1.03 | +1.03 | −0.77 | 43% |
| AUD_JPY | 3 | +1.33 | −1.33 | −3.33 | 33% |
| **USD_CAD** | 10 | **+3.69** | −3.69 | **−5.49** | 40% |

**All 43 NY trades inverted: +0.07p net of spread (break-even). But the per-pair picture is the real story.**

## ⚠ The critical caveat — NOT all NY cells fade

**USD_CAD/ny actually TRENDS** (actual forward +3.69p, n=10) — inverting it would destroy V5's best NY cell. Recall from the broker-validation session: USD_CAD/ny/long is V5's STAR cell (+5.07p forward, driven by atr_5m + rsi14_h1, not generic momentum). The all-bars *generic-momentum* fade (−0.31) and the cell's *actual-signal* edge are different things — V5's USD_CAD/ny signal works WITH the move even though generic RSI momentum fades in NY.

So inversion is **cell-specific, not a session-wide flip.**

## The honest answer

**Can they be run inverted?**
- **Directionally yes**, and it's walk-forward robust (8/8 all-bars, both windows positive). The fade is strongest exactly where V5 fires.
- **Net of spread it's marginal** — break-even on average (43 real trades: +0.07p net). Spread eats most of the gross fade on wide-spread pairs.
- **It's cell-specific.** Two cells look genuinely positive inverted on real trades: **GBP_USD/ny (+2.96 net, n=10)** and **EUR_JPY/ny (+2.45 net, n=4)** — both currently disabled. **USD_JPY/ny** too (+10.4, but n=3). **USD_CAD/ny must NOT be inverted** — it's the star and it trends.

## Recommendation

Three tiers for the NY cells:
1. **Keep trading WITH signal:** USD_CAD/ny (star, trends +3.69p). Do not touch.
2. **Try INVERTED (shadow first):** GBP_USD/ny and EUR_JPY/ny — currently disabled, but real-trade inversion is +2.5 to +3.0p net of spread AND the all-bars fade is walk-forward stable. These are the strongest invert candidates. Better to run inverted than leave disabled IF the shadow confirms.
3. **Stay disabled:** USD_CHF/ny, AUD_JPY/ny, USD_CAD/ny/short, AUD_USD/ny, EUR_USD/ny — invert net-of-spread is negative or trends the wrong way; disabled is the safe call.

**The clean move:** rather than flip cells blind, shadow-log an inverted-direction score for GBP_USD/ny + EUR_JPY/ny alongside the current behavior, and measure forward on the next ~30 NY signals. If inverted clears spread live, flip those two from disabled to inverted-active. Everything else stays as-is.

## Sample-size honesty
- Q1 (all-bars) is millions of bars — the fade direction and its concentration in strong momentum are certain. The net-of-spread marginality is also certain.
- Q2 (real trades) is n=1-10 per cell, 43 total — directional but noisy. USD_JPY/ny +10.4 net rests on 3 trades; GBP_USD/ny +2.96 on 10 (the most trustworthy). Don't bank real money on any single cell without the shadow A/B.
- Spreads are typical OANDA estimates; live spread varies (wider in NY illiquid windows, which would hurt inversion further).

## Reproduction
```bash
~/.venvs/quantalib/bin/python ~/qtl-discovery-8yr/v5_invert_test.py   # ~1s, invert_test/invert_buckets.csv
```
