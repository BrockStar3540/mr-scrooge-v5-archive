# 2026-07-02 — USD_CAD deep dive (broker statement) + MAE-flip doctrine + new governance mechanisms

## Method (Brock's MAE-flip doctrine, stated this session)
Losing cell + MAE >> MFE = correct signal wired backwards -> keep signal, flip entry (MAE becomes MFE).
Then separate low-MAE "never got off the ground" entries from movers using entry-indicator stamps;
gate only on indicators that split CLEANLY; track rival separators forward.

## Broker-truth findings (V5-era-only; V4 excluded as different engine)
- STRICT SCOPING RESULT: current signal stack (v2/v3, live 06-20) has NEVER traded USD_CAD ny.
  All 6 "V5 ny long" trades were v1-module entries (06-18/19): 2W4L -36.9p fwd -1.1p.
  The 06-21 "+6.61p n=7 STAR" claim was cross-era contaminated (V4 trades in sample) — see
  methodology lesson below. NY under v2/v3 = "never measured".
- ny inversion (06-22 canary): fired ZERO trades in 10 days (d_cert ~0.24-0.27 vs 0.30 floor).
  Brock affirms flip stays (v1 sample MAE/MFE 3.7x supports flip direction per doctrine).
- london long (v2/v3): 0W2L, MAE/MFE ~12x (MFE 2.8 vs MAE 32.1) -> textbook flip candidate.
  Flipped, 9609 -> MFE 20.6 and 9743 -> MFE 43.6.
- london short (v2/v3): 3W1L +1.9p -> keep native. Dead-vs-mover separation on n=4:
  aroon (-57 vs -86 clean), kc_up (-15 vs <=-32 clean), efi (-0.06 vs <=-0.9 clean);
  willr/d_cert/m_cert/vortex do NOT separate. Gate on aroon per Brock; kc_up+efi tracked as rivals.
- asia: n=3, no verdict.

## Changes shipped (this commit)
1. NEW MECHANISM inverted_live_directions [pair, session, native_dir]: per-direction inversion,
   XOR with cell-level. First use: USD_CAD/london/long -> executes short. reads.inversion_type
   annotates INVERTED_CELL / INVERTED_DIR.
2. NEW MECHANISM per_cell_aroon_range (mirrors willr gate). First use: USD_CAD/london/short
   [-100,-85] (native shorts only — flipped longs are a different population, both replay
   winners had aroon +100/-57 and would have been blocked).
3. per_pair USD_CAD min_dir_certainty 0.30 -> 0.25 (Brock) so the inverted ny cell can fire
   and finally generate forward data.
4. lock_guard/lock_snapshot schema extended (inverted_directions, aroon_range_*) — locked cells
   frozen at "off" for both new knobs; old snapshots backward-compatible.
Earlier this session (separate commits): LOCK GUARD enforcement f605d4c; USD_CHF killed 7998bce.

## Methodology lessons registered
- Cell validation must filter to SAME-ENGINE trades (V4 vs V5 v1 vs v2/v3). Second star-claim
  revision after era-scoping (GBP_USD/ny was first).
- Grunt-agent rollups must be recomputed from trade rows (4 subtotal errors found; rows tie to CSV).
- Memory: feedback_mae_flip_doctrine saved (MBP memory dir).

## Watch forward
- USD_CAD london: flipped longs + gated shorts — re-audit at n=6 per side (fwd pip truth).
- USD_CAD ny: first v2/v3 trades ever once floor 0.25 live — judge inverted cell by fwd pip, n>=6.
- Rival separators kc_up/efi vs aroon on london shorts.
