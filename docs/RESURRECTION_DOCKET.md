# Resurrection Docket — V1–V5 buried ideas, re-adjudicated under clean method
**Opened 2026-07-09 (Brock order). Premise: verdicts rendered during bug eras are void until retested. Cross-reference: [BOOK_OF_BUGS.md](BOOK_OF_BUGS.md) contamination windows × the burial records (dead-ends-graveyard, FACTOR_RESEARCH_VERDICT, STRATEGY_ENCYCLOPEDIA — all in `/SCROOGE ARCHIVE/docs-harvest/`).**

Retest standard: the dial-in method (60d clean corpus, exact windows, multi-slice + dual-horizon robustness bar, live tripwires on anything promoted).

## Adjudicated 2026-07-09 (fresh tests run)

| item | buried when/why | contaminating bug | fresh verdict |
|---|---|---|---|
| **Trend-pullback factor trio** (ema20/ema50 dist, adr_consumed) — factor verdict said HELD (+31/+27/+21) but never entered cell era | retired with the factor stack at cell cutover | B-085 (factors dead live), B-078 (leaked corpus), pre-ratchet exits | **STAYS BURIED**: 0 passes across 5 active windows under the multi-slice bar. June's lift was regime + leak-era artifact |
| **USD_CHF pair** (killed 07-01) | live losses during the inversion era | inversions active 06-22→07-02 (execution sign-scrambled) | **KILL RE-CONFIRMED on clean corpus**: drift ~0 with monthly sign flips, all sessions. Right verdict, dirty trial, same sentence |
| **HTF/MTF directional family** (align lever, htf_pct, close_pos_daily…) | retired 07-03 (aggregator inversion) | B-075 (freeze+definition), B-078 | **One seat earned**: htf_pct_60 ≤ +1.3% on AU/lon (monthly-consistent, +163% drift). Rest stays buried (monthly sign flips) |
| **Reactive TP exits** (removed Mar 12 over B-033 infinite-retry) | dead-ends §3.4 — fix may have over-reached | B-033 | **ALREADY RESURRECTED** as the FAST bracket class (server-side TP) — and it's earning. The Mar-12 removal was indeed an over-fix |
| **TP1=5p / hold-time ping-pong** (Category 4) | parameter churn, V1–V3 | exit-bottleneck era (B-076) | **RESOLVED BY DESIGN**: cost-floor TPs + per-class timeouts are the principled versions |

## Open docket (queued, in priority order)

1. **The 14 atr_conc-dead cells (B-077)** — setups gated on atr_conc ≥4.0 could NEVER fire from V3 activation to 2026-07-03; every "no signal" verdict on them is void. Retest: identify the 14 from fix `2c7367a`, run their windows through the quintile grinder. *Weekend.*
2. **OTR/spread-economics hard gate** (dead-ends §3.1/3.2, demoted to advisory Mar 11) — the cost study vindicated the concern ($18.6k spread tax, ~83% of a losing window). Modern form: per-cell gate `spread_now / expected_travel > threshold → block`. We have both inputs live. *Strong candidate — design next session.*
3. **V1 box theory / PDH-PDL breakout** — buried in the B-001→B-074 swarm; note the current book star (kc_breakout) IS box-breakout-shaped. Retest: pdh/pdl-relative conditions through the grinder. *Weekend.*
4. **ml-lab miner-map + ranker** (+3.1p/trade OOS, promotion-gated, never wired) — not bug-buried; was awaiting 2020/2022 regime backfill. Status of backfill unknown. *Check + revive the gate process.*
5. **Discovery-engine trend-pullback roster** (06-14; 12× reach expansion claim) — partially contradicted by today's factor screen in current regime; re-run the roster's specific combos (not the generic factors) on clean corpus. *Weekend.*
6. **Value-band grain (K=1 dialed plugins)** — the per-band insight is methodologically alive (it IS the quintile grinder); the specific June bands need clean-corpus re-derivation before any use. *As cells demand.*
7. **Profit-anchored sizing / NAV-vs-balance compounding** (dead-ends §2.5/3.6) — bundle into the parked equal-$/pip sizing decision. *With Brock, pre-V6-live.*
8. **max_reentries + reactive re-entry logic** (§3.3, B-007) — cell era has no explicit re-entry policy beyond cooldown; UJ asia's winning re-entries suggest value in studying it deliberately. *Low.*

## Universe expansion (opened 2026-07-09, Brock order)

The original 20-pair universe returns for evaluation. 2026 corpus built for the 12 non-book pairs
(`research/tools/build_ext_corpus.py`, ~39k bars each); all 72 cells screened both directions
(`research/tools/universe_screen.py`). **Survivors:** EUR_AUD/asia LONG, GBP_AUD/asia LONG
(+5–9p/mo consistently since May), GBP_JPY/asia SHORT (+2.7 YTD). **Watch:** CHF_JPY asia+london
shorts, GBP_JPY/ny short. Next: weekend engine expansion (PAIRS list, feed, _MAX_SPREAD entries,
cell configs) to wire survivor pairs as SHADOW-only cells → stamp-forward scoreboard earns ACTIVE.

**Periodic flip protocol (standing):** the weekly review re-runs the universe screen over all cells
(book + shadows + expansion). Both directions are always scored — a strongly negative long IS the
short candidate. A shadow side flips when two consecutive weekly screens agree on the opposite sign;
an ACTIVE side flips only via the full dial-in treatment. Screens exclude fwd_*/mfe_*/mae_* columns.

## Standing rule
Nothing promotes from this docket without: clean-corpus pass (multi-slice bar) → live tripwire. Burials re-confirmed here get a headstone note in the graveyard doc so they aren't re-litigated a third time.
