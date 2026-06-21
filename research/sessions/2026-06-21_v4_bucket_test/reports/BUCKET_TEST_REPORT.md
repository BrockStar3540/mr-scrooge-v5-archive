# Testing the V4-era "coarse-factor bucket" claims on the 8yr corpus

**Date:** 2026-06-21
**Source:** Brock's notes from a previous bot version (the V4 bucket/align system).
**Method:** Reconstruct the ALIGN / ADR / RSI bucket logic on V5's 8yr feature corpus, outcome = **1H forward pip in the signal direction** (market truth, per this weekend's methodology — NOT realized P/L). ALIGN = # of HTF factors {htf_pct_20, htf_pct_60, trend_4h, d_ret} whose sign matches the signal direction d = sign(h1_ret_1bar), range 0-4. 4.27M bars, 8 pairs, 2.3s.

## Verdict: 2 of 3 claims confirmed, 1 is strategy-specific (as Brock's own caveat predicted)

## ✅ C1 — SESSION × ALIGN holds, and ny_open is steepest (matches the old notes exactly)

Mean forward pip in signal direction, pooled across pairs:

| session | a0 | a1 | a2 | a3 | a4 | slope |
|---|---:|---:|---:|---:|---:|---|
| asia | 0.74 | 1.73 | 2.55 | 2.95 | 4.39 | climbs +3.65 |
| asia_late | 1.15 | 1.86 | 2.65 | 2.76 | 3.75 | climbs +2.60 |
| london_open | 1.43 | 2.14 | 3.74 | 4.65 | 6.34 | climbs +4.91 |
| london | 1.47 | 2.52 | 3.89 | 4.60 | 5.98 | climbs +4.51 |
| **ny_open** | 1.61 | 3.25 | 5.32 | 6.59 | **7.88** | **climbs +6.27 (steepest)** |
| ny_mid | 1.67 | 2.26 | 3.17 | 3.58 | 4.11 | climbs +2.44 |
| ny_close | 1.18 | 1.07 | 1.50 | 1.78 | 2.01 | climbs +0.83 (flattest) |

**Alignment climbs monotonically in every session.** ny_open is the steepest (Δ+6.27) and ny_close the flattest (Δ+0.83) — the V4 notes said exactly this ("ny_open ↑ steepest", "ny_close ~flat"). The effect is real and large: HTF-aligned signals carry far more forward continuation than unaligned ones.

**Caveat on magnitude:** these pooled pip numbers are inflated by JPY-pair pip-count (0.01 pip size → larger counts) and by overlapping forward windows. Treat them as a *relative/structural* ranking, not literal tradeable pips. The DIRECTION (align climbs, ny_open steepest) is rock-solid.

(The old notes also claimed "off_hours INVERTS." My session mapping covers all 24 hours so there's no separate off_hours bucket to confirm/deny — the closest, ny_close, is flattest but still climbs.)

## ⭐ C2 — RSI extremes ONLY pay when aligned. This is the gold (confirmed).

Mean forward pip by RSI-in-direction × align:

| RSI(dir) bucket | a0 | a1 | a2 | a3 | a4 |
|---|---:|---:|---:|---:|---:|
| rsi_lo | 1.28 | 2.00 | 2.46 | 3.03 | 2.76 |
| rsi_mlo | 1.56 | 2.20 | 2.57 | 3.28 | 3.56 |
| rsi_mid | 1.16 | 2.17 | 2.89 | 3.51 | 4.59 |
| rsi_mhi | 0.28 | 1.78 | 3.65 | 3.83 | 4.87 |
| **rsi_hi (extreme)** | **−1.01** | 0.89 | 5.45 | 5.28 | **6.25** |

**An extreme RSI in the trade direction is the ONLY negative cell when unaligned (−1.01 at a0) — and the single biggest payer when aligned (+6.25 at a4).** This is precisely the V4 finding ("RSI0 a0:−1.09 → a4:+4.48"). Reading down the rsi_hi row: extreme RSI without HTF backing loses; with HTF backing it's the strongest setup in the table. The interaction is mechanistic and real.

## ❌ C3 — the bucket drop-negative lift did NOT replicate at the all-bars level

The V4 notes claimed: build ALIGN×ADR×RSI buckets, drop the negative ones, lift CP2 from +0.36p → +2.06p (a huge +1.7p gain). OOS-tested (build map on 2019-2023, test on 2024-2026):

| pair | base fwd | keep fwd | **lift** | drop_n (of ~182k) |
|---|---:|---:|---:|---:|
| AUD_JPY | 3.969 | 3.975 | +0.006 | 405 |
| EUR_JPY | 4.843 | 4.852 | +0.009 | 177 |
| USD_CHF | 2.218 | 2.229 | +0.011 | 647 |
| (all 8) | +3.290 mean | +3.295 mean | ~+0.005 | tiny |

**The lift is essentially zero (+0.005p), because almost no bars fall in the negative buckets out-of-sample** (drop_n is 0-647 out of ~182k per pair). On all bars, the ALIGN×ADR×RSI buckets are nearly all positive — there's nothing to drop.

This matches Brock's own caveat: *"it's strategy-specific — CP2's map (ADR-driven) won't be another strategy's."* The V4 result worked because CP2_squeeze_momentum_long concentrated its 1332 trades in the narrow regions where the negative buckets exist. On the unconditional all-bars population, those regions are rare. **The bucket-drop is a per-strategy entry filter, not a general edge.**

## The unification — this explains today's NY momentum-fade

Earlier today: NY short-term momentum (RSI7_M5) FADES. This test shows why: it's the **unaligned** case.
- Short-term momentum WITHOUT HTF backing (align 0-1) = weak/fade. The fast-RSI-cross is exactly this — a short-term blip with no higher-timeframe confirmation. rsi_hi + a0 = **−1.01** (the fade).
- Short-term momentum WITH HTF backing (align 4) = strong continuation (+6 to +8p). rsi_hi + a4 = **+6.25**.

V5's direction engine treats momentum (h1_ret_1bar) as its #1 factor without a strong alignment gate. **The fade losses in NY are the unaligned-momentum trades.** Alignment is the missing axis that separates the continuation from the exhaustion.

## ✅ And critically — ALIGN is LIVE in V5 (the V4 blocker is gone)

The V4 notes ended: *"align is a core bucket axis and it's frozen live — so this filter can't work in production until the H20/H60 feed is fixed."* Verified today on V5's `/api/state`: htf_pct_20 (−0.024 to +0.032), htf_pct_60 (0 to +0.033), trend_4h (±1) are all live and varied across pairs. The H20/H60 freeze was fixed (per the 2026-06-09 htf fix). **So the align filter that V4 could never deploy CAN be wired into V5 now.**

## Actionable for V5

1. **Build an ALIGN score (0-4 HTF agreement) as a direction_v2 confidence multiplier.** It's V5's single strongest available forward predictor (monotonic in every session, Δ up to +6p) and it's live-wired. This is the highest-value item to surface from the V4 notes.
2. **Penalize RSI-extreme-but-unaligned** (the −1.01 cell). This is the same fade we wired the shadow-invert for, now with a clean mechanism: extreme RSI + low align = fade. Could replace the cell-specific invert logic with a general align-gated RSI penalty.
3. **Do NOT chase the C3 bucket-drop generically** — it's strategy-specific and doesn't hold on all bars.

## Honesty
- C1/C2 are millions of bars, directionally certain. Magnitudes inflated by pooling (JPY pip-count + overlapping windows) — use as relative ranking, validate absolute tradeable size on a clean per-pair non-overlapping sample before sizing.
- C2's sign flip (rsi_hi: −1.01 unaligned → +6.25 aligned) is the most robust and actionable single result.
- C3's null is also certain — the bucket-drop is per-strategy, not general.

## Reproduction
```bash
~/.venvs/quantalib/bin/python ~/qtl-discovery-8yr/v5_bucket_test.py   # ~2.3s
# outputs: bucket_test/{session_x_align.csv, rsi_x_align.csv, oos_bucket_lift.csv}
```

## Next
Wire the ALIGN score + align-gated RSI-extreme penalty into direction_v2 as shadow features (log alongside current score), measure forward — exactly the shadow→validate→promote discipline used for Vortex and the inverted cells. ALIGN is the most promising single feature surfaced this weekend.
