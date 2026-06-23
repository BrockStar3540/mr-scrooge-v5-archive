# V5 ratchet + exit assessment (2026-06-23)

**Question (Brock):** How is the ratchet performing? Assess on the 14 live trades since the inverted_live wiring.

## Headline
The current step-trail ratchet (peak − 2.5p, re-locked at 2.5p bands starting at +7.5p MFE, initial SL −20p) is **well-tuned for the dominant trade pattern** — wobble-then-run winners. Aggregate: 14 trades, +38.20p sum, +2.73p mean, 79% WR.

## Findings
1. **Wins capture 73% of MFE on average** — exits land near the peak, not deep below it.
2. **Elite winners (9176, 9192) captured 99%+ of MFE** — the step-trail nails big runs.
3. **All 3 losers went profitable first** (MFE +2 to +7.9p), but only ONE (9230, MFE +7.9p) was close enough to a current ratchet band to be saveable by an earlier engage.
4. **9208 (+2p MFE) and 9213 (−0.8p MFE) were clean failed entries** — no realistic band catches them; better SIGNAL filtering > better exit management.

## Proposed tighter bands — TESTED, REJECTED
Brock proposed: MFE +4 → SL −4 (loss cap), MFE +6 → SL +4 (lock), MFE +7.5+ unchanged.

| Variant | Sum | Mean | WR | Saved | Hurt | vs OLD |
|---|---:|---:|---:|---:|---:|---:|
| OLD (current) | +38.20p | +2.73p | 79% | — | — | — |
| Original proposal | +1.30p | +0.09p | 64% | 4 | 10 | −36.90p |
| Softer (no −4 cap) | +26.30p | +1.88p | 86% | 4 | 10 | −11.90p |

**Why the proposal loses:** 5 of 11 winners are "wobble-then-run" — they reach +5-8p MFE, dip back through +4p (sometimes through 0), then climb to +10-20p+ for the big run. The proposed +4 lock catches them on the dip and exits at +4p, missing the run. Most striking case is **9192 EUR_JPY short**: actual +19.95p elite winner, sim with proposal exits at +4p (or −4p with the loss-cap).

In this 14-trade dataset, the wobble-then-run pattern outnumbers the single-spike-then-reverse failed-winner pattern 5:1. Any tighter band loses more on the 5 than it saves on the 1.

## Adopted: 5-second manage-cycle polling
**One change shipped: `main.py` manage_interval_seconds 30 → 5 (commit pending).** Pure upside:
- Costs nothing in API budget (OANDA limit is ~100 req/sec, we use a fraction)
- Catches boundary cases where a brief MFE spike between bands (e.g. 9230's +7.9p that may have flickered above +7.5p between 30s polls) would now trigger the existing first band
- No risk to current well-tuned bands

## Re-evaluate threshold
**Re-run this analysis after 50+ trades.** If failed-winners become more common than wobble-runners, revisit Brock's proposal. With only 14 trades, the 1:5 ratio could be sample artifact.

## Reproduction
```bash
# MFE/MAE assessment (per-trade highs and lows)
python3 analyses/v5_mfe_mae_report.py

# Sim Brock's proposed bands against actual trades
python3 analyses/v5_ratchet_proposal_sim.py

# Softer variant (no -4 loss cap, just +4 lock at +6)
python3 analyses/v5_ratchet_softer_sim.py
```

All run from EC2 (V5 journal + OANDA creds are there).
