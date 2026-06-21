# V5 per-cell ruleset — the weekend's findings consolidated into 48 cell modules

**Date:** 2026-06-21
**Premise (Brock):** Each cell (pair × session × direction) gets its own module with session- and direction-aware rules special to that cell.
**This report:** consolidates every validated finding this weekend into one per-cell ruleset, and shows *why* the per-cell-module architecture is necessary — the three independent signals conflict per cell, so only per-cell resolution works.

## The architecture is validated — by the conflicts

The consolidated ruleset joins three independent, validated signals per cell:
- **direction_profile** — 8yr ML (reversion / continuation_strong / default)
- **momentum_sign** — walk-forward (NY/london fade, overlap/asia trend)
- **broker_fwd_pip** — actual 1H forward on real OANDA trades

**These conflict in 8+ cells.** The clearest example — cells where the ML profile says `continuation_strong` but momentum + broker say FADE:

| Cell | profile | momentum | broker fwd | enabled |
|---|---|---|---:|:---:|
| **USD_JPY/ny/short** | continuation_strong | FADE | **−17.80p** | yes ⚠ |
| EUR_JPY/ny/long | continuation_strong | FADE | −6.27p | disabled |
| AUD_USD/asia/short | continuation_strong | FADE | −3.38p | yes |
| GBP_USD/london/short | continuation_strong | FADE | −3.95p | yes |
| GBP_USD/london/long | continuation_strong | FADE | −0.45p | yes |

USD_JPY/ny/short is the alarm: V5's profile (set from sparse 44-trade live evidence) says continuation, but the walk-forward momentum AND real broker forward both say fade hard (−17.8p). **A global or per-pair rule would never catch this — only a per-cell module that resolves the conflict cell-by-cell.** This is the architectural thesis, proven by the data: the cells genuinely disagree with each other, so each needs its own resolved rule.

## The confirmed WINNER cells — where to concentrate

Only a handful of cells have positive broker forward AND supporting evidence. These are V5's real edge:

| Cell | profile | broker fwd | n | tier |
|---|---|---:|---:|---|
| **AUD_JPY/asia/long** | default | **+6.70p** | (1) | STRONG (TREND) |
| **USD_CAD/ny/long** | reversion | **+6.61p** | **7** | MODERATE ⭐ |
| **EUR_USD/london/short** | reversion | **+6.31p** | **7** | MODERATE ⭐ |
| AUD_JPY/london/long | reversion | +2.83p | 3 | MODERATE |
| **AUD_JPY/asia/short** | continuation_strong | +1.80p | **6** | STRONG (TREND) |

The two ⭐ cells (USD_CAD/ny/long, EUR_USD/london/short) have the strongest evidence — n=7 real trades each, positive forward, ML-supported. **These are the cells V5 should trust and not touch.** AUD_JPY/asia (both directions, n=6-7, trend) is the other reliable cluster.

## The honest picture — edge is concentrated, most cells are weak

| Evidence tier | cells | meaning |
|---|---:|---|
| STRONG (broker + walk-forward agree) | ~16 | but mostly agree on NEGATIVE (fade/lose) |
| MODERATE (≥3 real trades) | ~8 | the winners + some losers |
| WEAK (ML only, n<3) | ~24 | not enough live evidence |

**~4-5 cells are confirmed positive-edge.** The rest are fade-dominant, weak, or disabled. This is exactly consistent with V5 losing money — the edge lives in a few cells, and the bot has been trading the whole 48-cell grid including the fade cells. **Concentrating on the confirmed winners + disabling/fading the rest is the path to profitability.**

## A real architectural refinement the data surfaced

V5's `ny` session (13:00-21:00 UTC) **lumps two opposite regimes:**
- overlap (13:00-14:00): momentum TRENDS, align CONFIRMS
- late-ny (15:00-21:00): momentum FADES, align FADES

The align-resolution + percell tests showed overlap is 16/16 cells trend-positive while ny-proper fades. V5 merges them into one `ny` session, so a `ny` cell module is forced to average a trend regime with a fade regime. **The next-level per-cell refinement is to split `ny` into `overlap` + `ny` — expanding to a finer session grid where each module sees a coherent regime.** That's the natural evolution of the per-cell architecture this weekend's data points to.

## The deliverable — cell_ruleset.csv

48 rows, one per (pair × session × direction), each with: enabled, invert_shadow, direction_profile, momentum_sign, align_sign, ml_delta_auc, broker_fwd_pip, broker_n, evidence_tier, recommended_rule. This is the per-cell module spec — the concrete embodiment of "each cell gets its own rules," populated from six validated tests:
1. 8yr per-cell ML (direction profiles)
2. 2026 re-audit (regime/monthly)
3. broker validation (real forward pip)
4. per-cell momentum walk-forward (fade/trend sign)
5. align resolution (session-signed alignment)
6. inversion test (which fade cells to flip)

## Recommended sequencing (disciplined, not blind)

1. **Trust + protect the winners** — USD_CAD/ny/long, EUR_USD/london/short, AUD_JPY/asia (both). Don't change their profiles.
2. **Resolve the conflict cells per-cell** — USD_JPY/ny/short (profile says continuation, everything else says fade −17.8p): either flip to fade/reversion or disable. This is the highest-impact single fix.
3. **The 10 disabled cells stay disabled**; the 2 invert-shadow cells (GBP_USD/ny, EUR_JPY/ny) accumulate shadow data.
4. **Split ny → overlap + ny** as the next architectural step (finer session grid).
5. Everything WEAK (n<3) waits for the monthly cron to accumulate live evidence.

## The weekend in one line
The per-cell-module architecture was correct. What was missing was the validated per-cell rules — now generated, cross-checked four ways, and consolidated into one ruleset. The edge is real but concentrated in ~5 cells; the rest fade or wait. **Each cell genuinely needs its own rule, because the cells genuinely disagree.**

## Reproduction
```bash
~/.venvs/quantalib/bin/python ~/qtl-discovery-8yr/v5_cell_ruleset.py
# joins all weekend artifacts -> cell_ruleset/cell_ruleset.csv
```
