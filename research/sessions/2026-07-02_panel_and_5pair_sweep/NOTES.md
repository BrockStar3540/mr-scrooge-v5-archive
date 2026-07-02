# 2026-07-02 — 3-model panel (Opus/Sonnet/Haiku) + 5-pair MAE-flip sweep + fixes shipped

## Trigger
Brock: "spin up Sonnet, Opus, Haiku, debate the indicators and data, figure this shit out.
we are clearly overlooking something." Preceded by broker-truth sweeps of USD_CAD, EUR_JPY,
USD_JPY, AUD_USD, EUR_USD, GBP_USD, AUD_JPY (V5-era-only, per-trade MFE/MAE + entry stamps).

## Panel verdict (2 rounds, cross-examined)
TWO-LAYER FAILURE:
1. SIGNAL LAYER (root, Opus+Sonnet, survived attack): 2026 is mean-reverting; live
   PROFILE_ASSIGNMENT ran 15 continuation_strong + 26 default vs audit's all-reversion answer
   (+0.0802 AUC, 38/38 same-sign, monotone year drift 2020->2026). The 06-22 inversion wave =
   lagging per-cell hand-patch of this bug (muted both broker stars; 07-02 knife-catch -61.8p).
2. GOVERNANCE LAYER (co-root, Haiku, upgraded by all): winner's-curse — locks/gates/inversions
   fit to n<10 luck. Locked cells post-lock 3W/7L -127p; P(3W/7L | lock's claimed 88% WR) = 2.8e-5
   -> baselines were never real. 71% of cells (34/48) assigned on NO_DATA/WEAK/BAD evidence.
   Haiku: "a constant can't explain a variable" — bleed timing tracks TUNING events, not market.
KILLED ON DATA: -10p loss cap (06-23 sim decomposition: cap variant worst, -36.9p; converts 27%
of winners to losers); delete-all-disables; hard static profile flip (Feb 2026 -0.0179).
UNITS CAVEAT (Haiku): +0.0802 is AUC not pips; converted recovery ~= quarter of the -2.58p/trade
structural deficit at 67% WR — profile fix is necessary, not sufficient.
SEQUENCING TRAP (Sonnet): de-invert BEFORE shipping reversion weights, or corrected fade signals
pass through stale flips back into momentum-chasing.
CONSTITUTION (adopted): no per-cell action below n>=20 same-engine trades; inversion deprecated
for new cells (flips only via MAE-flip doctrine >=3x asymmetry n>=6); chop veto (MAE/MFE ~1.5-2.5x
both directions = disable, never invert); 8yr corpus promotes features, live only vetoes;
locks = provisional attribution, not validated-winner badges (re-lock at n>=25, CI over breakeven).

## Replay gate (Mini, ~272K bars)
Corrected profiles won 6/6 months of 2026, +2.3-3.2p mean fwd/call, all 8 pairs; biggest movers =
the live bleeders (USD_JPY/london +4.6, GBP_USD/london +4.5, EUR_JPY/ny +3.7). Trade-level test
structurally undecidable (parquet cutoff = V5 go-live) -> live shadow is the trade-level evidence
collector. Report: Mini ~/v5-replay-gate/REPORT.md.

## Shipped this session (chronological)
- 5c9ac55 de-inversion non-locked: EUR_USD london+ny (star restored), GBP_USD london, EUR_JPY ny;
  chop-disables EUR_JPY/ny/short + AUD_JPY/asia/long. HOT-RELOADED LIVE.
- 5ddd0d2 per-currency exposure cap max_per_currency_direction=1 (pick_best Step 6, fallthrough;
  /api/state exposure map). Inert until restart.
- (this commit) SHADOW_PROFILE dual-stamp: corrected-profile stack stamps same views, logs
  disagreements; kill-switch defaults.profile_shadow_enabled; scorer
  research/tools/profile_shadow_score.py. Logging only. Inert until restart.
- Earlier same day: b8422e8 strategy-free README banner; d6d9f81 EUR_JPY willr exhaustion window;
  cc939ae USD_CAD MAE-flip (per-dir inversion + aroon gate mechanisms) + floor 0.25.

## Pending Brock
- Restart (activates exposure cap + profile shadow).
- USD_JPY/london un-invert = locked-cell override (live inverted -24.4p/5 vs natural +7.06 backtest;
  biggest replay mover +4.57p under reversion).
- After ~1-2wk shadow: profile flip decision via profile_shadow_score.py forward-pip readout.

## Kept per Brock call / n-too-small (explicitly NOT changed)
USD_CAD/ny + USD_JPY/asia inversions; GBP_USD/ny lock; AUD_JPY/asia/short lock (DEGRADING watch).
