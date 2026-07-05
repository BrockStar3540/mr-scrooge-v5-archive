# Cell-Level Transaction Costs (measured from broker fills)

**Session 2026-07-04 · source: OANDA transaction export (practice-account-id-redacted), 2026-05-31 → 2026-07-03, 963 ORDER_FILL rows (~477 round trips), V4+V5 eras pooled (spread is market microstructure, not bot config).**

Method: OANDA's `ESTIMATED SPREAD COST` per fill = half-spread × size (charged each side). Converted to pips via `cost_usd / (units × pipsize × quote→USD)`; quote→USD from the CSV `CONVERSION RATE` column when present, else derived from same-file fill prices. Round trip (RT) = entry median + exit median. Cross-check: RT medians match OANDA's published typical spreads (EUR/USD 1.6, GBP/USD 1.9, EUR/JPY 2.7) — method validated.

## Headline

- **Total spread tax over the 5 weeks: $18,630. Net realized P/L same window: −$22,473.** At mid prices the book was ≈ −$3.9k: **~83% of the realized loss was transaction cost.** ($/trade figures are inflated by V4-era position sizes; the pip figures below are the invariant.)
- **Financing is a rounding error:** 63 DAILY_FINANCING rows net **+$33.86** (mean +$0.54/day, worst −$55). Charged only on positions held past 21:00 UTC. Irrelevant for intraday cells; only matters for multi-day holds (worst pair/side ≈ 0.5–1.0p equivalent per night at 20%-margin sizing).
- **Pair dominates, session barely matters.** Within a pair, session medians differ by ≤0.2p; across pairs the RT cost ranges 1.35p → 2.8p (2×). The cost dimension of a "cell" is effectively the PAIR row, not the session column.

## RT cost per cell (median entry + median exit, pips)

| pair | asia | london | ny | p90 blowout seen (exits) |
|---|---|---|---|---|
| AUD/USD | 1.35 | 1.35 | 1.35 | 0.75 |
| USD/JPY | 1.62 | 1.56 | 1.59 | 1.19 |
| EUR/USD | 1.60 | 1.63 | 1.60 | 2.60 (london) |
| USD/CHF | 1.64 | 1.56 | 1.64 | 6.93 (ny = hour 21) |
| USD/CAD | 1.81 | 1.86 | 1.79 | 4.60 (ny = hour 21) |
| GBP/USD | 2.00 | 1.87 | 1.95 | 1.10 |
| AUD/JPY | 2.36 | 2.24 | 2.40 | 6.35 (ny = hour 21) |
| EUR/JPY | 2.78 | 2.57 | 2.76 | 7.22 (ny = hour 21) |

Full per-fill stats (n/med/p75/p90 × entry/exit): `cell_costs.json`. Reproduce: `python3 analyze_transaction_costs.py <oanda_export.csv>`.

## Rollover hour (21:00 UTC, inside the "ny" session label)

Half-spreads blow out 4–10× (GBP/USD 10p, USD/CHF 7.2, EUR/JPY 7.35, AUD/JPY 6.1, USD/CAD 4.95, AUD/USD 4.05 median per-fill). Stops were NOT swept more often at hour 21 in this sample (12/377 = 3.2% vs 4.2% uniform) — but each hour-21 stop fill paid ~8× normal cost (mean $158 vs ~$19). Implication: avoid bot-initiated entries/closes 20:55–22:05; a ratchet stop resting within ~half-spread-blowout distance of price can be triggered by the widening itself (stop triggers on bid/ask, not mid).

## Margin model (rates measured from the account's instrument endpoint, not memory)

marginRate: EUR/USD, USD/CAD **2%** · AUD/USD, USD/CHF **3%** · GBP/USD, USD/JPY, EUR/JPY, AUD/JPY **5%**. Current sizing confirmed = ~20% of balance as margin per trade (open AUD/USD trade: $3,409 / $16,784 NAV = 20.3%).

Per-trade size at balance $16.8k:

| pair | $/pip @20% | $/pip @40% | RT tax $ @20% |
|---|---|---|---|
| AUD/USD | 16.12 | 32.25 | 21.77 |
| EUR/USD | 14.41 | 28.81 | 23.05 |
| USD/CHF | 14.29 | 28.58 | 22.86 |
| USD/CAD | 12.14 | 24.29 | 21.86 |
| AUD/JPY | 6.63 | 13.25 | 15.57 |
| GBP/USD | 4.98 | 9.97 | 9.72 |
| USD/JPY | 4.60 | 9.20 | 7.36 |
| EUR/JPY | 3.95 | 7.89 | 10.66 |

**Structural consequence of equal-margin sizing:** identical "20% of balance" buys a 4.1× spread in $/pip (AUD/USD $16.1 vs EUR/JPY $3.9). The book's $ P/L is silently dominated by the 2–3%-margin pairs regardless of cell quality. If cell-era wants each cell's edge weighted equally, sizing should normalize $/pip (units = target_$per_pip / (pipsize × quote→USD)), not margin fraction. 40%×2 doubles every row, same asymmetry.

**40%×2 live plan margin math:** both slots full = 80% of balance as margin. OANDA margin closeout at NAV ≤ 50% of margin used → NAV ≤ 40% of balance → requires ~60% drawdown while both positions open. Not imminent, but news-gap-real at 20:1 effective leverage on the 2% pairs. Also: 2 slots + 10 ACTIVE cells = signal lockout when full — in tension with a higher-frequency cheese-slicer book.

## Cheese-slicer floors (min viable ratchet lock per cell)

A locked stop at +L pips realizes +L (spread already embedded in fill prices) — but the market must travel **L + RT** from mid for the lock to exist, and EV_net = EV_gross_mid − RT per trade. Slicing more often multiplies the RT tax count. Cost floors (RT median, round up):

| tier | pairs | RT | sensible lock floor |
|---|---|---|---|
| cheap | AUD/USD | 1.35 | ~2.0–2.5p |
| mid | USD/JPY, EUR/USD, USD/CHF | 1.6 | ~2.5p |
| upper | USD/CAD, GBP/USD | 1.8–2.0 | ~3.0p |
| expensive | AUD/JPY | 2.4 | ~3.5p |
| expensive | EUR/JPY | 2.8 | ~4.0–4.5p |

Current live: global `step_trail_pips: 2.5`, per-setup `exit_params` all `{}` (mechanism exists, unused). Note the trail giveback (2.5p) is BELOW the RT cost of EUR/JPY and AUD/JPY — those cells cut cheese thinner than the knife.

**⚠️ Constraint before deploying any tightening:** the 2026-07-03 exit-geometry sweep found tighter global exits = −36.9p on real fired entries (population mismatch vs unconditional bars). These cost floors say where tightening is AFFORDABLE, not that it is PROFITABLE. Any per-cell lock change must re-run the fired-trade sim for that cell first.

## Caveats

- Practice-account pricing; live spreads can differ (usually similar on OANDA, but re-measure after the live-money switch with the same script).
- 5-week sample, one export; hour-level cells have small n (the hour-21 pattern is consistent across all 8 pairs, so it is real).
- `ESTIMATED SPREAD COST` is OANDA's estimate of half-spread × size; it is a decomposition of cost already embedded in fill prices, not an extra fee.
## ADDENDUM 2026-07-05 — slicer sweet-spot: slippage, conversion, lock mechanics

**Mechanics (verified against fills):** OANDA charges nothing beyond the bid/ask cross —
COMMISSION is 0 on all 963 fills. Entry fills at ask (long); a ratchet lock / TP at
entry_fill + L that fills realizes **L − slippage** — the spread is NOT charged again at
exit. The spread's real bite on a tight slicer is **rarity**: the stop/limit triggers on
the far side of the book, so MID must travel **L + full_spread** for a +L exit to fill.
A +3 lock on EUR_JPY needs ~5.7p of mid travel; on AUD_USD ~4.35p.

**Stop-fill slippage (375 matched stop→fill pairs, normal hours = excl 21:00 UTC):**
med 0.00p · p75 0.20p · p90 0.80p · p97 3.2p. 46% of fills land ≤0.5p worse than the stop,
6% better. Hour-21: med 0.8p, p90 8.8p — rollover remains the one true wash/loss zone.
EUR/USD carries the fattest news tails (p90 6.8p incl. all hours).

**Conversion markup (the hidden fee Brock suspected):** non-USD-quote P/L is converted at
~**1% against the client both ways** (winners −1%, losses +1%; measured vs same-file spot;
equals the CONVERSION FEE column: −$402.74 over 5 weeks). Proportional to P/L, so ≈0.03p
on a +3p slice — real, cumulative, but never the difference between profit and wash.
Affects JPY/CHF/CAD-quote pairs only.

**Wash-zone verdict:** a +3 lock that fills nets ≈ +2.9p typically, ≥ +2.2p in 90% of
normal-hour fills — **not a wash**. True wash territory: locks ≤1p (slippage-sized),
anything filling at 21:00 UTC, and p97 slippage days. The +5-floor instinct is right for
EV reasons, not fee reasons: slippage is a fixed tax per exit, so larger L dilutes it
(net-if-filled: +3→2.2p, +5→4.2p at p90), and the per-attempt spread toll amortizes better.

**Fill probabilities** (P(fwd MFE ≥ L + spread), 2026 corpus, both dirs avg —
`../2026-07-05_ratchet_profiles/fill_probabilities.csv`): at L=3, 60m fill runs 0.33
(USD_CHF asia) to 0.66 (GBP_USD london); at L=5, 0.18–0.54. Gross EV-if-filled
(P × net) RISES with L in every cell through L=8 — tighter slicing is not free money;
the failure branch (what a non-fill costs) is cell EV territory, gated on fired-trade sim.

**Limit-TP vs stop-lock:** same trigger side, same required travel — but a limit exit
cannot slip negative (fills at price or better). For pure slice-and-exit setups, TP-limit
at +L strictly dominates a stop-lock at +L on fill quality (saves the full slippage
distribution, 0.2–0.8p at p75/p90).
