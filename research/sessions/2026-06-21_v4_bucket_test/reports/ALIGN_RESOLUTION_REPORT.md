# Is ALIGN 0-4 too narrow across the 48 cells?

**Date:** 2026-06-21
**Question (Brock):** Is the 0-4 ALIGN bucket too narrow for HTF across all our cells (pair × session × direction)?
**Method:** Per-(pair × session × direction) = 64 cell-sessions, reference = cell's fixed direction. Compared three ALIGN forms by Spearman correlation with 1H forward pip: **0-4 count** (4 HTF factors), **0-8 count** (8 HTF factors: daily 5/10/20/60/120-day returns + trend 1h/4h/24h), and **continuous** (z-scored signed sum). Plus population at each level. 8yr, 8 pairs, 2.1s.

## Short answer: not too narrow in population or resolution — but a UNIFORM align score is wrong, because align's SIGN flips by session.

## 1. Population — 0-4 is fully populated in every cell

| | result |
|---|---|
| Cells where align=4 has <200 bars | **0 / 64** |
| Cells where align=0 has <200 bars | **0 / 64** |
| Mean % of bars at align=4 | 11.3% |
| Mean % of bars at align=0 | 12.0% |

Every cell has all five align levels well-populated (~11-12% at each extreme). **0-4 is not too narrow in the sparsity sense** — there's no cell where the strong-aligned or strong-unaligned bucket lacks sample.

## 2. Resolution — finer barely helps, more factors doesn't

| Form | mean \|corr\| with forward | beats 0-4 |
|---|---:|---:|
| 0-4 count | 0.0092 | — |
| 0-8 count (more factors) | 0.0086 | 30/64 (worse) |
| continuous (z-sum) | 0.0100 | 36/64 (barely) |

- **More LEVELS (continuous):** +0.0008 corr gain — negligible, and only above-half of cells.
- **More FACTORS (0-8):** slightly *worse* (−0.0001). Adding daily 5/10/120-day + trend-1h/24h does NOT improve on the original 4-factor basis. The 4 factors {ret20d, ret60d, trend4h, trend24h} are sufficient.

So neither axis of "narrow" is the limiting factor. **The 0-4 count is fine.**

## 3. The real finding — ALIGN's sign FLIPS by session (this is what matters)

Once you fix the direction (as a per-cell V5 trade does), ALIGN's correlation with forward is small (~0.01-0.03) **but its SIGN is overwhelmingly session-determined:**

| session | cells where align predicts TREND (+) | cells where align predicts FADE (−) | mean corr |
|---|---:|---:|---:|
| **overlap** | **16 / 16** | 0 | **+0.0128** |
| ny | 2 / 16 | **14 / 16** | −0.0077 |
| london | 2 / 16 | 14 / 16 | −0.0073 |
| asia | 6 / 16 | 10 / 16 | −0.0024 (mixed) |

**In the overlap session, HTF alignment confirms (more aligned → better forward) in all 16 cells. In NY and London, alignment FADES (more aligned → WORSE forward) in 14 of 16 cells.** The continuous form captures this slightly better than the 5-bucket count precisely in the sessions where the relationship is non-monotonic (NY gain +0.0043, overlap +0.0046).

## This reconciles the strong C1 effect from the prior test

Yesterday's SESSION × ALIGN test showed align climbing strongly (a0 1.6 → a4 7.9 in ny_open). That used d = sign(h1_ret_1bar) as the direction — so it measured *"when HTF agrees with recent momentum, does momentum continue."* That's largely **momentum-direction selection**, not pure alignment. When the direction is FIXED per cell (no momentum selection), alignment's marginal predictive power drops to ~0.01-0.03 corr and **its sign is session-dependent** — confirmation in overlap, fade in NY/london.

## Corrected recommendation for V5

Yesterday I recommended "build an ALIGN score (0-4) as a direction_v2 confidence multiplier." **That was too simple — a uniform align multiplier would help overlap cells but HURT NY/london cells** (where align fades). The corrected form:

1. **Use ALIGN continuous + PER-CELL-SIGNED**, not a uniform 0-4 multiplier. The sign comes from the cell's session: positive (confirm) in overlap, negative (fade) in NY/london, ~neutral in asia.
2. **0-4 buckets are fine for resolution** — don't bother with 0-8 or finer; the gain is negligible. If anything, continuous is marginally cleaner in the fade sessions.
3. This is the same NY-fade we keep finding, now seen through the alignment lens: HTF-aligned momentum in NY does NOT continue — it reverses. Align is a fade signal there, a trend signal in overlap.

## The throughline (now 4 independent views of the same fact)
1. Broker P/L: NY cells lost money.
2. Broker forward pip: NY cells negative forward.
3. 8yr walk-forward momentum: NY momentum fades, 8/8 pairs.
4. **ALIGN resolution: HTF alignment FADES in NY/london (14/16 cells), confirms in overlap (16/16).**
Every method says the same thing: **NY is a fade session; overlap is a trend session; alignment must be session-signed.**

## Answer to the literal question
**No, 0-4 is not too narrow** — it's fully populated in every one of the 64 cell-sessions, and finer/wider resolution adds essentially nothing (+0.0008 corr). The limiting factor isn't the bucket count; it's that **alignment's predictive sign is session-dependent**, so the fix is per-cell-signed continuous align, not more buckets.

## Reproduction
```bash
~/.venvs/quantalib/bin/python ~/qtl-discovery-8yr/v5_align_resolution.py   # ~2.1s
# outputs: align_resolution/align_resolution.csv
```
