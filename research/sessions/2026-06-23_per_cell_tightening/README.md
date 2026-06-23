# Per-cell tightening — Mon night 2026-06-23

After the earlier Mon work (inverted_live + ratchet+exit + entry-indicators + random_pick + CYCLE log + 4 shadow features + willr soft-wire), Brock drove a series of per-cell tightening decisions based on per-trade deep-dive analysis and 2026 backtests on Mini.

## What landed

### 1. Per-cell `inverted_live_cells` adjustments
- **AUD_JPY/asia: REVERTED** (was inverted, observed -46p over 5 closed trades + 9241 open at -16p drawdown). Backtest confirmed natural direction is profitable (+6.32p/72.3% WR on 710 bars).
- **USD_JPY/london: INVERTED** (Brock override of backtest data which strongly favored natural direction +7.06p/65.8% WR). Brock based call on 3 live trades (1 win, 1 -19p loss, 1 -14p open drawdown). Watching.

### 2. NEW MECHANISM: `per_cell_mom_cert_max` (ceiling)
Block trades where m_cert > ceiling. Per Brock's reframe: low m_cert predicts BIG directional move; high m_cert predicts small contained move. For cells whose edge is in the big-move tail, block high-cert.

- **AUD_JPY/asia: ceiling 0.50** — 5 of 6 live trades there had m_cert ≤ 0.50; the one 0.91 outlier produced only +5.10p (smallest win)

### 3. NEW MECHANISM: `per_cell_mom_cert_min` (floor)
Mirror of the ceiling. Block trades where m_cert < floor. For cells where the OPPOSITE pattern holds (high m_cert → big MFE, low m_cert → small/failed).

- **GBP_USD/ny: floor 0.40** — 5 live trades, m_cert 0.39-0.84 → MFE 8.4-13.8p; only the lowest (0.39) produced smallest MFE
- **USD_JPY/london: floor 0.50** — paired with the new inversion. Brock's call.

### 4. NEW MECHANISM: `per_cell_willr_range` (gate)
Block trades where willr_m5 is outside [min, max] for the (pair, session, direction). Per-direction granularity (willr behavior is direction-asymmetric).

PIPING: PairTicket gained `willr_m5`, `close_pos_daily`, `vortex_diff_h1` fields piped from view through `stamp_pair`. Playmaker reads from PairTicket directly. (No view passing needed.)

- **EUR_JPY/ny/short: willr in [-85, -7]** — per 2026 backtest, this rule alone improves baseline +6.95p/64.8% WR → +8.48p/70.2% WR on n=1,360 of 1,999 bars (best single rule found).

## Backtests run on Mini

| Script | Pair | Finding |
|---|---|---|
| `v5_usdjpy_mcert_backtest.py` | USD_JPY | m_cert floor 0.75 marginal: asia +9% mean, london mixed (WR -1.9pp). NY has 0 actionable bars all of 2026. |
| `v5_usdjpy_london_invert_sim.py` | USD_JPY/london | Inverting destroys the cell: natural +7.06p/65.8% → inverted -7.06p/34.2%. Floor 0.50 makes inversion worse (−8.03p/35.2%). Brock overrode this. |
| `v5_eurjpy_ny_short_filter_backtest.py` | EUR_JPY/ny/short | willr [-85, -7] alone is best (+8.48p/70.2% WR). cpos [0.06, 0.60] alone HURT (+6.33p/63.2% — small-sample artifact from 7 live trades). Combined cpos+willr only marginal. m_cert sweet spot inside KEEP: 0.55-0.70 = +11.82p/78% on n=229. |

## Per-trade deep-dives (filed in `2026-06-23_aud_jpy_deep_dive/analyses/v5_pair_deep_dive.py`)

Parameterized script — `python3 v5_pair_deep_dive.py PAIR` works for any pair.

Pulls per-trade journal SIGNAL fields + recomputes willr/aroon/kc_up/efi/rsi_h1 at entry from OANDA + MFE/MAE per trade.

| Pair | Trades | WR | Mean realized | Notes |
|---|:--:|---:|---:|---|
| AUD_JPY | 6 | 33% | -7.7p | All asia-inverted era. Reverted after this analysis. |
| USD_JPY | 4 (1 open) | 67% | +6.22p | Big win 9237 asia/short (+29.4p). 1 open london drawdown. |
| EUR_JPY | 7 (1 open) | 83% | +4.89p | All ny/short, no other cells fired. Best per-cell WR observed. |

## Watch list for next session

### Per-cell rules to evaluate on next ~10 trades each
- **AUD_JPY/asia un-inverted**: confirm low-m_cert trades produce big MFE wins (the reframe hypothesis)
- **USD_JPY/london inverted + floor 0.50**: backtest predicts catastrophic loss; if Brock's read was right, live should show recoveries from natural-direction losses
- **EUR_JPY/ny/short willr filter**: expect WR climb 65% → 70% on next 5-10 fires
- **GBP_USD/ny inverted + floor 0.40**: continue tracking (5/5 wins pre-floor — does floor maintain edge?)

### Still untested cells (need data)
- USD_CAD/ny/long inverted (the canary — historical STAR +6.61p inverted to short, no live trades yet)
- USD_CHF/london+ny inverted (no live trades)
- EUR_USD/london+ny inverted (no live trades)
- USD_JPY/asia inverted (1 live trade +29.4p, backtest says revert — too thin to decide)
- EUR_JPY london + asia (zero live trades all cells)

### Future narrowing candidates (NOT shipped, kept as research)
- EUR_JPY/ny/short: add m_cert [0.55, 0.70] window inside the willr KEEP bucket → +11.82p/78% WR on n=229
- USD_JPY backtest framework reusable for any pair — apply to GBP_USD or EUR_USD when those cells fire

## Reproduction

```bash
# All run on Mini (CPYQTH294R), feature parquets at ~/qtl-discovery-8yr/features/
ssh ec2 'ssh mini ". ~/.venvs/quantalib/bin/activate && python3 /tmp/v5_usdjpy_mcert_backtest.py"'
ssh ec2 'ssh mini ". ~/.venvs/quantalib/bin/activate && python3 /tmp/v5_usdjpy_london_invert_sim.py"'
ssh ec2 'ssh mini ". ~/.venvs/quantalib/bin/activate && python3 /tmp/v5_eurjpy_ny_short_filter_backtest.py"'

# Or copy any analyses/ script from this folder to Mini /tmp and run.
```

## V5 live state at session close (2026-06-23 ~21:15 UTC)
- 14 disabled, 9 inverted_live, 2 inverted_shadow
- `per_cell_mom_cert_max`: AUD_JPY/asia=0.50
- `per_cell_mom_cert_min`: GBP_USD/ny=0.40, USD_JPY/london=0.50
- `per_cell_willr_range`: EUR_JPY/ny/short=[-85, -7]
- 4 shadow features (willr/aroon/kc_up/efi) in CYCLE log per pair per cycle
- willr_m5 wired as soft direction feature (default -1.0, continuation_strong -3.0, reversion -5.0)
- random_pick=true, manage=5s
- NAV ~$21,100
