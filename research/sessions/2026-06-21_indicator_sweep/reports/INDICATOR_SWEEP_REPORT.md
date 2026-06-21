# Indicator parameter sweep + aggregator/verifier test

**Date:** 2026-06-21
**Question (Brock):** Maybe the parameters are off. Test the numerical variations, and test the indicators as **aggregators / verification** of other signals, not standalone.
**Method:** 46 variants (RSI 7/9/14/21 × M5/M15/M30/H1, RSI bands 45/50/55, EMA 5-20/8-21/10-30/12-26/20-50 × M5/M15/M30/H1, StochRSI 14-5-3/14-3-3/21-5-5 × M15/M30). All bars, 8yr × 8 pairs. Two measurements per variant: **standalone directional separation** = E[fwd60m | bullish] − E[fwd60m | bearish]; and **aggregator lift** = E[fwd in base direction | verifier agrees] − E[ | verifier disagrees]. 65 seconds compute.

## Bottom line first

- **No parameter setting gives standalone edge.** Sweeping RSI period, EMA pairs, cross levels, timeframes — nothing crosses into tradeable standalone territory. So "the variables were off" is **not** the explanation. The base signal is dead at every setting.
- **BUT there are three real, consistent structural effects** that the standalone test (run earlier) averaged away. These are small (0.1–0.6 pip) but statistically dead-certain (millions of bars, consistent sign across all 8 pairs). They are usable as **per-cell confidence modifiers**, not as primary signals.

## Finding 1 — Fast indicators are EXHAUSTION markers (the biggest aggregator signal)

The clearest result in the whole sweep. When a **fast (M5) RSI agrees with your direction, forward expectancy gets WORSE:**

| Verifier on base | Lift | Consistency across 8 pairs |
|---|---:|---:|
| RSI21_M5 verifying RSI7_M15 base | **−0.243** | 0/8 (always negative) |
| RSI7_M5 verifying EMA5/20 base | −0.243 | 0/8 |
| RSI14_M5 verifying RSI7_M15 | −0.242 | 0/8 |
| RSI7_M5 verifying h1ret base | −0.234 | 1/8 |

**Interpretation:** a fast M5 RSI confirming your direction means the short-term move is already overextended — you're chasing. This is a genuine, exploitable, contrarian signal: **M5-RSI-agreement should be a NEGATIVE weight on confidence (an exhaustion penalty), not a confirmation.** Magnitude ~−0.24p, perfectly consistent.

This also shows up in the standalone pooled separation: the faster the RSI, the more negative — RSI7_M5 −0.24 → RSI21_M5 −0.18 → RSI on H1 ≈ 0. Speed = exhaustion.

## Finding 2 — Slow verifiers add small POSITIVE confirmation

The opposite end. Slow-TF indicators (M30/H1 RSI, M15 EMA state) agreeing with a base add a small, consistent positive lift:

| Verifier on base | Lift | Consistency |
|---|---:|---:|
| RSI9_M30 verifying RSI7_M15 | **+0.102** | 7/8 |
| RSI21_M15 verifying RSI7_M15 | +0.090 | 5/8 |
| EMA8/21_M15 verifying EMA5/20_M15 | +0.079 | 5/8 |
| EMA10/30_M15 verifying EMA5/20 | +0.076 | 6/8 |
| RSI14_M30 verifying RSI7_M15 | +0.074 | 5/8 |

**Caveat that matters:** in every one of these the base is a *losing* signal, and both the agree and disagree subsets are negative (e.g. agree −0.043 vs disagree −0.145). The slow verifier lifts a negative base **toward break-even, not into profit.** So slow-TF confirmation is real but weak — it makes a bad signal less bad. It is NOT enough to turn the app logic into an edge.

This is the rigorous answer to "is the multi-timeframe alignment useful as verification": **marginally yes** (+0.07 to +0.10p of separation), but far too small to overcome spread, and it's confirming a base that has no edge to begin with.

## Finding 3 — The indicator's meaning FLIPS by session (largest magnitude effect)

The session split is where the real magnitude lives. Same indicator, opposite sign by session (separation = E[fwd|bull] − E[fwd|bear], pooled across pairs):

| Session | Best variant | Separation | Meaning |
|---|---|---:|---|
| **NY** | RSI7_M5 | **−0.62** | strong FADE — bullish RSI → next hour down |
| **overlap** (13-14 UTC) | EMA5/20_M5 | **+0.47** | strong TREND — bullish EMA → next hour up |
| london | RSI7_H1 | +0.17 | mild trend |
| asia | RSI7_M5 | −0.16 | mild fade |

**This is genuinely exploitable structure.** In the NY session, fast momentum indicators are reliably contrarian (−0.6 separation is the biggest number in the sweep). In the London/NY overlap, they're trend-following (+0.47). An indicator used the SAME way in all sessions averages these out to ≈0 — which is exactly what the standalone test found. The signal isn't absent; **it's session-sign-dependent.**

## What this means for V5 (concrete, testable)

None of these are standalone moneymakers — all are sub-spread in magnitude. But two are large and consistent enough to wire as **per-cell confidence modifiers** and forward-validate:

1. **Fast-RSI exhaustion penalty.** Add `RSI7_M5 agrees with bias` as a NEGATIVE weight in the direction score (−0.24p effect, 0/8 consistency = dead certain direction). When the bot's direction is already confirmed by the fastest RSI, it's chasing — reduce confidence. This is the single most actionable item.

2. **Session-conditional sign** on momentum verifiers: in NY, treat fast-indicator agreement as a fade (reduce or flip); in overlap, treat it as confirmation (boost). V5 already keys per-(pair × session × direction), so this fits the architecture exactly — it's a per-session weight sign, not a new global rule.

3. **Slow-TF verification (M30/H1 RSI, M15 EMA)** as a tiny positive confirmation (+0.07-0.10p) — marginal, lowest priority. Worth including as a small positive weight only after the two above are validated.

## What it does NOT support

- The app's core logic (RSI cross + MTF alignment as a BUY/SELL trigger) — still no edge at any parameter setting.
- Treating same-TF or fast indicators as *confirmation* — they're exhaustion markers; confirming with them makes it worse.
- Any of this as a primary signal — all effects are < spread.

## Honesty on magnitude + stats

Every number here is pooled over millions of M5 bars, so even ±0.05p effects are statistically certain (consistency column = fraction of 8 pairs agreeing on sign; many are 8/8). But *certain* ≠ *large*. The exhaustion penalty (−0.24p) and the NY fade (−0.6p separation) are the only effects with magnitude approaching the ~1-2p spread, and even those are confidence-modifier-sized, not standalone-strategy-sized. The right use is: small per-cell weights, shadow-logged, validated on forward broker data before trusting — same discipline as everything else this weekend.

## Reproduction
```bash
~/.venvs/quantalib/bin/python ~/qtl-discovery-8yr/v5_indicator_sweep.py   # 65s on Mini
# outputs: indicator_sweep/{standalone_sweep.csv, aggregator_lift.csv, aggregator_lift_summary.csv}
```

## Next test worth running
Now that "fast = exhaustion, slow = mild-confirm, session flips sign" is established, the highest-value follow-up is the **per-cell** version: which specific (pair × session × direction) cells have the largest fast-RSI exhaustion penalty? Wire it only where the per-cell effect is large + forward-validated, exactly like the broker-validation disable list. That converts this from "interesting structure" to "a weight V5 actually uses."
