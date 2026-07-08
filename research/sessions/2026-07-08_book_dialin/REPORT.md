# Book Dial-In Week — 2026-07-06 → 07-08 (summary)

Full side-audit + quintile dial-in of every active setup, triggered by Brock's
wrong-direction suspicions. Method per setup: (1) side check = side-signed
drift240 in the EXACT condition window (60d truth corpus), (2) SL = winners'
MAE p75, (3) dials = quintile MAE/MFE tables, cut only clean worst-end blocks,
combined-verified (n>=250, gain >=+1.5p), (4) live flips not shadow-waiting
(Brock doctrine), cemetery for sideless setups.

Outcomes: 4 sides flipped live (AUD_USD/lon, GBP/asia, AJ/ny timing, UJ/lon),
1 cemetery (GBP/lon timing), 1 demotion (GBP/lon rvol_low — RESOLVED band
bleeds; fallback-band audit artifact documented), 1 broker-veto keep (UJ/asia
kc: corpus negative, live 6W/1L), 8 dial tightenings, SLs resized to winners'
MAE on 5 setups (default -20 was a loser-collection device; GBP/lon rvol
earns its 20). Key insight: the same indicator flips meaning across cells
(atr_h1_relative: cap on UJ/asia, floor on EUR_JPY/ny).

Every change: hot-reloaded live + committed + generator override (survives
monthly refit). Verification: tripwires (last-20 EV) + n>=20 clocks + the
weekly expectancy scoreboard (watch avg-loss shrink toward ~-50, not WR).
Tables: DIALIN_BREAKDOWN.md. Scoreboard at close: UJ 92% WR +175, GBP 50%
-98, AJ 80% -28, AU 33% -585 (pre-dial damage).