# Dial-In Breakdown — AUD/JPY · AUD/USD · EUR/JPY (2026-07-08)

Per-indicator **quintile tables**: each row = one fifth of the setup's firing window (last 60 days, truth-matrix corpus, side-signed).
Columns: drift (expected pips/4h in trade direction) · median MFE · median MAE · **cw** = clean-win rate P(MFE≥10 & MAE≤8) · **dead** = P(MFE<4).
The dial: keep the rows where drift/cw are fat, cut the rows where MAE/dead dominate. Everything marked SHIPPED is live + in the generator.

---

## AUD/JPY ny · `regime_short_240` (SHORT) — window after Monday's dual filter

Baseline: n=1091 · drift **+7.42p** · medMFE 10.6 / medMAE 5.1 · cw 43% · dead 12%

**atr_5m — monotone dial (quiet = better):**
| range | drift | medMFE | medMAE | cw | dead |
|---|---|---|---|---|---|
| 1.05–2.16 | +6.71 | 11.7 | 3.8 | **53%** | **3%** |
| 2.16–2.47 | +8.13 | 10.6 | 4.5 | 49% | 12% |
| 2.47–2.81 | +10.61 | 11.1 | 5.7 | 43% | 14% |
| 2.81–3.17 | +6.05 | 9.9 | 6.3 | 36% | 13% |
| 3.17–3.60 | +5.62 | 9.0 | 5.8 | 34% | **19%** |

**kc_up_dist — closer to the band = better short:** top quintile [−2.25, +4.44] → cw 57%, dead 9%; bottom [−6.74, −5.41] → cw 35%.

**➤ SHIPPED: atr_5m cap 3.60→2.81, kc floor −6.75→−4.54.**
**Combined verified: drift +7.42 → +10.38p · cw 43→53% · dead 12→8%** (n=460/60d ≈ 7–8 qualifying fires/day retained).

---

## AUD/USD london · `kc_up_long_lean` (LONG)

Baseline: n=2844 · drift **+1.59p** · medMFE 11.1 / medMAE 8.2 · cw 38% · dead 20%

**kc_up_dist — the story reversed vs AUD/JPY: deep below the band = better long (pullback, not band-kiss):**
| range | drift | medMFE | medMAE | cw | dead |
|---|---|---|---|---|---|
| −14.9 … −8.6 | **+4.08** | 12.9 | 9.3 | 37% | 16% |
| −8.6 … −6.4 | +3.24 | 12.0 | 7.8 | 41% | 19% |
| −6.4 … −4.6 | +1.03 | 11.6 | 7.8 | 42% | 23% |
| −4.6 … −3.0 | ±0.00 | 10.5 | 7.6 | 39% | 21% |
| −3.0 … 0.0 | **−0.38** | 9.4 | 8.1 | 31% | 23% |

**rvol_5bar — dead zone at the bottom:** [0.39–0.80] drift **−2.06p**, cw 23%; every quintile above 0.80 positive.

**➤ SHIPPED: window [−15, 0] → [−15, −4.62] + rvol ≥ 0.80.**
**Combined verified: drift +1.59 → +2.93p (+84%) · cw 38→43%** (n=1410/60d).

---

## EUR/JPY ny · `timing_lean_30` (SHORT, FAST bracket) — first full audit

- **Side CONFIRMED:** drift **+5.17p** short. No flip.
- **Bracket geometry healthy:** P(MFE₆₀ ≥ 5) = 72% — the +5p TP has honest fill odds; SL −6 fits the 60-minute frame.
- **Dial found:** `atr_h1_relative` floor — high H1-relative vol favors the fade here (opposite sign to USD/JPY asia, which is why per-cell beats global rules).

**➤ SHIPPED: atr_h1_relative ≥ 1.09.**
**Verified: drift +5.17 → +8.32p (+61%) · cw 30→37% · dead 16→12% · fill-odds unchanged (73%).**

---

## GBP stop-losses (winners-MAE check)

- **asia `timing_lean_30_long`:** winners' MAE p50/p75/p90 = 6.5/13.8/19.5 → **SHIPPED SL 20→14.**
- **london `rvol_low_240` (the 7/7-year formula):** winners' MAE p75 = **22.5** — this one genuinely uses the room. **SL 20 kept, deliberately.**

---

## The doctrine these tables keep proving
1. Winners' MAE p75 is the SL dial — the default −20 only ever measured losers (except london rvol, which earns its depth).
2. The same indicator flips meaning across cells (atr_h1_rel: floor on EUR/JPY, cap on USD/JPY) — global rules are dead, the cell is the unit.
3. Every range above is a 60-day read with tripwires armed — n≥20 live fires per setup is the confirmation clock, cemetery if the dial doesn't hold.
