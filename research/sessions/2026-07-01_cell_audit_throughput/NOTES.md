# Cell audit + per-cell tightening + throughput session — 2026-07-01

Big session. Per-cell deep-dives (USD_JPY, AUD_JPY, USD_CHF), two throughput fixes, a full
broker-truth cell audit, and a session-map widening. All changes live, both remotes.

## Commits (all pushed origin + alien)
1. af0afa7 — USD_JPY/asia += per_cell_dir_cert_min=0.49 (block low-conviction inverted losers; n=5, both losers d_cert 0.37/0.46, winners >=0.49)
2. 1e7b24a — AUD_JPY/asia UN-INVERT + drop d_cert ceiling (cell wants short; long side -95.75p/3W6L vs native shorts +20.1p/2W0L; m_cert confirmed big-movers 0.25-0.40)
3. 5f36685 — session note + README gov counts
4. acdefe7 — USD_CHF/ny UN-INVERT (trade short) + drop d_cert ceiling. BROCK OVERRIDE: n=9 both-dir M1 ratchet sim said all-long +1.60p vs all-short -12.30p; Brock chose short. Watch.
5. c6479e1 — USD_JPY/london LONG-ONLY: kept inverted (short sig->winning long) + disabled native long (blocks long-sig->losing short 9554). london long 3W0L +20.55p vs short 0W2L -37.60p.
6. 0312522 — ENGINE multi-open per cycle (throughput fix)
7. e6b0b30 — widen PAIR_SESSIONS (asia for EUR_USD/EUR_JPY/GBP_USD, USD_CAD all-3) + re-enable AUD_USD asia

## Diagnostic 1 — why only 1-2 concurrent positions
Root cause: `_cycle` opened ONE ticket per 300s scan (pick_best returns single), so open-rate
capped at 1/5min while ratchet exits close in minutes -> steady state 1-2. Fix: `_cycle` loops
pick_best excluding opened pairs, fires all actionable up to max_concurrent(4); SIGNAL log
extracted to `_signal_and_open` helper. Restart 06:08 clean.

## Diagnostic 2 — why some pairs never trade / went silent
Root cause: config/pairs.py PAIR_SESSIONS restricts each pair to specific sessions (line 285
in playmaker: `if t.session not in PAIR_SESSIONS.get(t.pair, [])`). Recent signal regime is
asia-heavy, but EUR_USD/EUR_JPY/GBP_USD were london/ny-only and USD_CAD was ny-only -> their
qualifying asia signals were filtered before any gate. AUD_USD had all asia cells in
disabled_cells. Only USD_JPY/AUD_JPY were asia-enabled -> they dominated recent trading.
Fix = commit e6b0b30. NOTE: newly-opened cells are UNVALIDATED (no history/tuning) — exploratory.

## OANDA BROKER AUDIT (from Brock's CSV export, since 2026-06-22 UTC)
72 trades vs journal's 56 — **journal missed 16 (28%)**, confirming "use broker not logs".
Ranked by net pips (with real $):
  GBP_USD/ny/short   14  12W2L  86%  +42.4p  +$262   [best volume winner]
  AUD_USD/london/sht  7   6W1L  86%  +30.2p  +$599   [best $ winner]
  USD_JPY/london/lng  4   4W0L 100%  +24.9p  +$128
  AUD_USD/london/lng  2   2W0L 100%  +12.6p  +$258
  USD_JPY/asia/long   2   2W0L 100%   +9.7p   +$51
  AUD_JPY/asia/short  5   4W1L  80%   +8.0p   +$63
  USD_JPY/asia/short  6   4W2L  67%   +6.3p   +$31
  EUR_JPY/ny/long     1   0W1L   0%   -1.4p    -$6
  EUR_JPY/ny/short    9   6W3L  67%  -17.5p   -$94
  USD_CHF/ny/long     7   4W3L  57%  -20.7p  -$375
  USD_CHF/ny/short    2   0W2L   0%  -40.0p  -$696
  USD_JPY/london/sht  2   0W2L   0%  -40.2p  -$209
  AUD_JPY/asia/long  11   4W7L  36% -108.3p  -$824   [worst cell]
  TOTAL              72  48W24L 67%  -94.0p  -$813
Money bleeders: AUD_JPY/asia/long -$824 (fixed: un-inverted), USD_CHF/ny both dirs -$1071 (bad
cell BOTH ways — Brock kept it short, the -$696 side; flagged as disable candidate).
Money winners: AUD_USD both dirs +$857, GBP_USD/ny/short +$262.

## Live governance state (end of session)
- inverted_live_cells (9): USD_JPY/asia, USD_JPY/london, EUR_USD/london, EUR_USD/ny,
  GBP_USD/london, GBP_USD/ny, USD_CAD/ny, EUR_JPY/ny, USD_CHF/london
- disabled_cells (13): AUD_USD/ny L+S, USD_CHF/london/short, EUR_JPY/london/short, USD_CHF/ny/long,
  AUD_JPY/london/short, AUD_JPY/ny/long, USD_JPY/ny/short, USD_CAD/ny/short, EUR_JPY/ny/long,
  EUR_USD/london/long, EUR_USD/ny/long, USD_JPY/london/long
- per_cell_dir_cert_min: GBP_USD/ny=0.52, USD_JPY/asia=0.49
- per_cell_dir_cert_max: USD_CHF/london=0.55
- per_cell_mom_cert_min: GBP_USD/ny=0.40, USD_JPY/london=0.50
- per_cell_mom_cert_max: AUD_JPY/asia=0.50, AUD_USD/london=0.50
- per_cell_willr_range: EUR_JPY/ny/short=[-85,-7] · per_cell_kc_up_range: AUD_USD/london/short=[-15,0]
- PAIR_SESSIONS: all pairs asia-enabled EXCEPT USD_CHF (london/ny only — left off deliberately, worst pair)
- engine: multi-open per cycle (up to max_concurrent=4)

## Watch list
- AUD_JPY/asia: confirm trades come through SHORT (un-invert working).
- USD_CHF/ny: SHORT per Brock override, but sim + broker say it loses both ways (-$1071). Disable candidate.
- All newly-enabled asia cells (EUR_USD/EUR_JPY/GBP_USD/USD_CAD/AUD_USD): UNVALIDATED — re-audit via broker after they accumulate trades.
- AUD_USD/asia: re-enabled despite weak-negative disable evidence; watch it doesn't dilute the london winner.
- Combined throughput: multi-open + widened sessions = materially more concurrency/risk. Watch position counts.
