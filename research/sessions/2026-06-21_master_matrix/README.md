# 2026-06-21 — V5 Master Matrix (per cell × all evidence)

**Author:** claude-code/MBP, session 2026-06-21  
**Builds on:** [2026-06-21_v5_2026_audit](../2026-06-21_v5_2026_audit/) + all prior sessions  
**Trigger:** Brock asked for a Master Matrix — every finding consolidated per (pair × session × direction), 2026 monthly stability check, indicator role categorization, live trade replay corroboration, and per-cell config/disable recommendations.

## What's in this folder

| File | Purpose |
|---|---|
| `reports/V5_MASTER_MATRIX_REPORT.md` | Comprehensive report with all findings, per-cell status, action plan |
| `analyses/v5_master_matrix.py` | Builds the per-cell matrix (40s on Mini, 48 cells × 55 columns) |
| `analyses/v5_indicator_roles.py` | Classifies 54 features by role (direction/oscillator/distance/regime/vol/volume/cycle) |
| `analyses/v5_live_replay_enriched.py` | Enriches the 44 live trades with qtl features from 8yr parquets + replays top-3 rules per cell |
| `data/master_matrix.csv` | The Master Matrix — 48 rows × 55 cols |
| `data/master_matrix.json` | Same data + nested rules + replay |
| `data/indicator_roles.csv` | 54 features × {role, dir_corr, mag_corr, vol_corr} |
| `data/live_replay_v2.csv` | Per (cell × rule) replay outcomes |
| `data/live_trades_enriched.csv` | 44 live trades + their qtl feature values at entry |

## Headlines

1. **ZERO cells are CONFIRMED** under strict criteria (ΔAUC_2026 > 0 AND recent_3yr_mean > 0 AND monthly_pos ≥ 4 of 5). FX is too noisy at the per-cell-per-month level for that bar.

2. **Cell status distribution**: 12 DEVIATING, 24 NEEDS_DATA (live N<3), 5 DISABLE_NEEDS_DATA, 5 WEAK_NEGATIVE, 2 MIXED.

3. **Live replay killed the qtl-as-binary-aggregator-rule plan.** Rules calibrated on every-bar distribution would have BLOCKED winning trades in V5's two best cells (AUD_JPY/asia/short, AUD_USD/asia/short). Or they'd take all entries (no filter effect). The ML thresholds don't translate to entry-bar filtering.

4. **2 cells are working as-is** — AUD_JPY/asia/short (80% WR, 5 trades) and AUD_USD/asia/short (75% WR, 4 trades). Both currently `continuation_strong`. Don't touch.

5. **5 cells flagged for DISABLE** — strongest case: AUD_USD/ny long+short (V5: reversion WEAK; ML: -0.032 ΔAUC, the WORST in matrix). No live data to corroborate, but 8yr ML is conclusive.

6. **3 cells are losing live but ML doesn't see a fix**: GBP_USD/ny/short (4 trades 25% WR), EUR_USD/ny/short (2 trades 0% WR), USD_CHF/ny/long (3 trades 33% WR). Profile is correct (reversion), but entries shouldn't be taken at all.

7. **Best NEW directional features found** (worth wiring as SOFT weights in direction_v2, not as binary rules):
   - `q_vortex_diff_h1` (+0.159 dir corr) — Vortex VI+ minus VI−
   - `q_super_dist_h1` (+0.146 dir corr) — SuperTrend distance
   - `q_aroonosc_h1` (+0.067 dir corr) — Aroon Oscillator
   - `close_pos_daily` (-0.240 dir corr) — V5 already has but UNDERWEIGHTED at -0.30 (could be -0.60 based on signal strength)

8. **Aggregator-rule decisions corroborated** with prior 2026 audit:
   - DROP `atr_conc > 2.5` rule (dead — never fires)
   - Convert `atr_h1_relative > 1.6` from global to per-cell whitelist

## What I'd actually do

In priority order:

1. **Don't touch V5's current 10 reversion-profile cells** — cross-validated 5 ways now.
2. **Disable AUD_USD ny long+short** — V5 currently allows these (reversion WEAK), but ML says strongly negative AND no live trades to defend the current assignment.
3. **Don't wire qtl candidates as binary rules** — the replay shows they don't filter properly on entry-bar distribution.
4. **Consider wiring qtl candidates as continuous-weight features** in direction_profiles.py (HMA-style) — q_vortex_diff_h1, q_super_dist_h1, q_aroonosc_h1, close_pos_daily-DOUBLED. This is the right implementation given the bar-vs-entry distribution gap.
5. **Set up monthly Mini cron** for the Master Matrix. Cell status drift is real (per the time-slice work); refresh monthly.

## Sample size honesty

- 2026 monthly bars per cell × month: ranges 7K-40K bars. Statistical power per month is decent but variance is high.
- Live trades: 44 across all cells. Per-cell N is 0-5. Most cells are NEEDS_DATA.
- 8yr bar-by-bar ML uses ~100K per cell-month — high statistical power but doesn't directly correspond to V5 entry distribution.

The gap between "bar-by-bar what predicts direction" and "entry-bar what predicts trade outcome" is now quantified by the live replay. **The cells where they AGREE are gold; where they conflict, live evidence wins.**

## Reproduction

```bash
# All on Mini, requires ~/.venvs/quantalib/ + ~/qtl-discovery-8yr/features/ from prior session
~/.venvs/quantalib/bin/python ~/qtl-discovery-8yr/v5_master_matrix.py         # 40s
~/.venvs/quantalib/bin/python ~/qtl-discovery-8yr/v5_indicator_roles.py      # 5s
~/.venvs/quantalib/bin/python ~/qtl-discovery-8yr/v5_live_replay_enriched.py # 25s
```

## Open follow-ups (NOT done in this session — flagged in main report)

- Per-cell live-distribution feature thresholds (re-derive rules using ONLY entry-bars, not all-bars)
- Soft-feature wiring (continuous weights in direction_profiles.py, not binary rules)
- Per-cell-direction `enabled` flag in playmaker_config (currently only per-pair)
- Monthly Mini cron for Master Matrix re-build
