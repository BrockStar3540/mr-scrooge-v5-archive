# 2026-07-03 — Truth-matrix era: leak repair, envelope strategy, falsifications, discovery v2

The day the research foundation was rebuilt and every mechanical lever quantified.
Reports for each study are in this directory; raw artifacts on the Mini (~/v5-truth-matrix/,
~/v5-ratchet-ev/, ~/v5-exit-sweep/, ~/v5-taint-rederivation/, ~/v5-cell-calibration/,
~/v5-discovery-v2/, ~/v5-atrrel-confirm/, ~/v5-mfe-study/).

## Infrastructure shipped (all live)
- atr_conc scale bug FIXED (2c7367a): 14 cells structurally unable to fire since v3
  activation, revived (impossible profiles -> default). First revived-cell trade same day
  (USD_JPY/ny/long 9855). Also: spread gate fail-closed, is_actionable 0.10 bootstrap,
  dead rules/constants cleaned, docstring fiction fixed.
- H1 look-ahead LEAK repaired: builder joins moved to bar-close; parquets rebuilt (100%
  safe-match); all H1-feature research pre-fix = upper bounds (memory: note_parquet_h1_leak).
- TRUTH MATRIX: per-bar dual-direction fwd MFE/MAE 60m/240m, 8 pairs x 8yr, extended to
  current, broker-anchored (60m-capped r=0.84/0.84; convention-adjusted 0.86-0.90).
  Brock doctrine: verified MAE/MFE = the ultimate configuration truth.
- CELL CALIBRATION artifact (config/cell_calibration.json, 48 cells): MFE quantiles + ATR
  regression, winner-MAE, dead rates + separators, direction leans. CAL log-lines live per
  cycle vs live expected_pips (first cycles: artifact ~2x the global 0.30 multiplier).
- MONTHLY RE-FIT PIPELINE armed (Mini cron 0 5 1 * *): bars->leak-test->truth->sync->
  calibration->anchor(155/155 trades r=0.86/0.84)->ship. First autonomous run Aug 1.
- ALL aggregator rules retired (atr_conc dead-scale; atr_h1_rel 2026-INVERTED, 297k-bar
  confirm study). AUD_USD/ny re-enabled (disable evidence was leak-fabricated).
- Panel-consensus de-inversions + USD_JPY/london natural (Brock lock override) + exposure
  cap active (121 skips day one) + SHADOW_PROFILE dual-stamp. Conformance sweep: 10/10.
- Theory spec v2: docs/DIRECTION_DETECTOR_SPEC_v2.md (10-item evidence change log).

## Strategy findings (the week's ledger, all broker/clean-corpus)
1. UNCONDITIONAL trading loses ~2.5-3p/trade at EVERY exit geometry (90-config sweep,
   0/44 cells positive in holdout; spread = most of the loss; best global SL8/tr3/trail1.5
   still -2.86 validate). Tighter exits +3.3p vs current BUT population-mismatch with the
   06-23 fired-trade sim (tighter = -36.9p on real entries) -> NO exit changes.
2. Envelope-first STRONG form falsified: no MOVEMENT cells (both-direction profit) exist
   unconditionally; the celebrated v1 table was outcome-conditioned (label = fwd sign) and
   retracted — the verification reflex caught it. Envelope control relocated: (a) entry
   filters (+1-4p uplift, only USD_JPY/london/short+htf_pct_60 crosses zero in-sample),
   (b) exit-geometry fitting (symmetric geometries engineer p* down to ~0.50-0.55).
3. Direction knowledge worth ~+6p/trade; current geometry requires ~70% accuracy;
   single-feature clean direction signal r~0.1 (28/48 cells PERSISTENT leans, each cell a
   DIFFERENT feature: atr_h1_relative USD_JPY/london ±0.126, vwap_dist AUD_USD/london,
   daily levels USD_CHF/london, stochrsi EUR_USD/ny). 20 cells: no lean.
4. Structural tiering (unconditional table): london JPY/GBP cells ~breakeven GROSS (any
   real skill converts); bottom tier (EUR_USD/asia, USD_CAD/asia+ny, AUD_USD/ny, GBP_USD/
   asia, USD_CHF) loses even gross — proposed trim pending Brock.
5. DISCOVERY v2 (clean, multivariate, excursion+ratchet-EV targets, permutation noise
   floors): **130/288 validated signals above floor AND single-feature baseline** —
   Brock's "formulas" vindicated. Breakdown: DEAD 41, RATCHET_EV 24, DISTANCE 33,
   **DIRECTION 32 (18@60m, 14@240m) with best AUC 0.58-0.61** (USD_JPY/ny 0.600@60m,
   USD_CHF/ny 0.610@240m, AUD_JPY/ny 0.580) vs single-feature <=0.53 and floor ~0.52.
   KEY CONVERGENCE: formula direction accuracy (~57-58%) meets engineered-geometry
   p* (~0.51-0.55) — first time both sides of the ledger reach each other.

## Trades today (broker)
9837 GBP_USD asia long -19.3 (asia-long streak now 3W1L); 9847 AUD_JPY asia short -18.1
(LOCKED cell post-lock now 0W3L -57.5p — starkest lock-vs-tape conflict, corpus still
supports the short side); 9851 AUD_USD london long (LOCKED, open, dead-entry shape);
9855 USD_JPY ny long (FIRST REVIVED-CELL TRADE, open +6p, peak 7.05 just under trigger).
NAV ~16.8k.

## Next session agenda (in order)
1. Discovery v2 distillation: RANGE formulas + plateau tests (Brock: ranges not exact
   thresholds; amendment arrived after sweep completed — NOT yet executed) for the 130,
   priority DIRECTION 32 + RATCHET_EV 24; then EV-simulate top direction formulas AT the
   engineered symmetric exit geometries (the convergence test).
2. Feed extension: q_yzv_m5, q_dc_*, q_bbwp_m5, q_vwap_dist, q_stochrsi/fisher, q_obv/adl
   onto MarketView (strongest validated detectors currently unreadable live).
3. Brock decision: structural trim of lose-even-gross tier.
4. Scoreboards: profile_shadow_score.py + calibration_score.py readouts (~1wk).
5. cellular_knowledge pattern-loop lineage audit (pre-leak-fix corpus?).
6. AUD_JPY/asia/short locked cell: monitor; corpus-vs-tape conflict.
