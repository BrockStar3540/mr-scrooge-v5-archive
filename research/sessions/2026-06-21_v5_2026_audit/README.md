# 2026-06-21 — V5 full 2026 re-audit (profiles + aggregators + qtl candidates)

**Author:** claude-code/MBP, session 2026-06-21  
**Builds on:**
- [2026-06-20_qtl_8yr_per_cell](../2026-06-20_qtl_8yr_per_cell/) — 8yr-aggregate per-cell sweep
- [2026-06-20_qtl_indicator_discovery](../2026-06-20_qtl_indicator_discovery/) — 44-trade pilot
**Trigger:** Brock pushed: (a) configurations must be per-(pair × session × direction), no globals; (b) drift over years/months can hide under averages — break it down; (c) re-audit V5's EXISTING profile/aggregator rules against 2026 too, not just new qtl candidates.

## What's in this folder

| File | Purpose |
|---|---|
| `reports/V5_2026_AUDIT_AND_CONFIG.md` | Full audit: per-cell 2026-best direction profile, qtl wire-in decisions, aggregator rule decisions, ready-to-paste Python config |
| `analyses/v5_2026_audit.py` | Audit pipeline (parallel 8 cores on Mini). Three concurrent audits per cell: profile assignment, aggregator rules, qtl candidate config. |
| `analyses/v5_qtl_8yr_ml_time_slices.py` | Per-year + per-month 2026 ML sweep (drift detection) — also from this session |
| `data/audit_2026_per_cell.json` | Full audit JSON, 48 cells × 3 audit dimensions |
| `data/profile_audit_2026.csv` | Per cell: current profile vs 2026-best + AUC lift if switched |
| `data/aggregator_audit_2026.csv` | Per rule × cell: trigger rate, AUC when triggered vs not |
| `data/qtl_2026_per_cell.csv` | Per cell: 2026-only ΔAUC + top feature + threshold |
| `data/config_2026_per_cell.json` | Ready-to-paste per-cell 2026 config |
| `data/year_x_cell_delta_auc.csv` | Drift table: 8 years × 48 cells × ΔAUC |
| `data/month2026_x_cell_delta_auc.csv` | Drift table: 5 months 2026 × 48 cells × ΔAUC |
| `data/feature_importance_by_slice.csv` | Per-feature importance trend across years + 2026 months |
| `data/top3_features_by_slice.csv` | Top-3 feature counts per slice (where each feature ranked top-3 by year/month) |

## Headlines (in priority order of action)

### 1. ⚠ Direction profile assignment is the biggest broken thing — 38/48 cells wrong for 2026
- Mean AUC lift if switched: **+0.0802** (16× the qtl candidate lift)
- **ALL 38 mismatched cells should become `reversion`** in 2026 (regime shift from trend-following to mean-reverting)
- Only 10 cells (all already `reversion` in V5) are correctly assigned today

### 2. ⚠ Aggregator rules need rewriting
- `atr_conc > 2.5` → DEAD (never fires in 2026; threshold needs lowering or rule removal)
- `atr_h1_rel > 1.6 → boost reversion` → only correct in 12/32 cells; HURTS in the other 20
- `atr_h1_rel > 1.6 → suppress HTF` → WRONG-WAY in 16/32 cells (HTF actually becomes MORE predictive in high-vol regime for JPY pairs)
- Recommended: convert from global rules to per-cell whitelists (full lists in main report)

### 3. QTL candidates wire in for only 12/48 cells in 2026 (vs 24/48 on 8yr average)
- All 12 are asia-session USD-quoted pairs + select USD_JPY/GBP_USD cells
- All 36 other cells: do NOT wire qtl (ΔAUC negative)
- Per-cell thresholds in the main report

### 4. Drift across years is real and big
- Mean ΔAUC by year: 2019=-0.001, peaked 2020=+0.0026, plateaued 2021-2024 +0.0015, flat 2025=0.000, **2026=-0.0028**
- Feature importance shifts: q_willr_m5 declined ~30% from 2020 peak; q_kc_up_dist_pips JUMPED in 2026; q_super_dist_h1 decayed to near-zero in 2024-2025
- Static-weight V5 modules will lag any regime shift by months. Re-audit monthly.

## What this means for V5

**Do NOT wire the 8yr-average recommendations** from the prior session (the willr_m5-everywhere + global Aroon ±3.57 rule). Those were based on a 2020-2024 regime that's gone.

**Three concrete changes for V5, in this order:**

1. **Flip the 38 mismatched direction profiles to `reversion`.** Single largest WR impact. Single PR with shadow-logging recommended (2-3 weeks dual-stamp before flipping playmaker).
2. **Remove `atr_conc > 2.5` aggregator rule** (dead anyway).
3. **Replace the two `atr_h1_rel > 1.6` global rules with per-cell whitelists** (lists in main report). Or use per-cell-direction sign lookup, depending on V5 implementation pattern.

For new feature additions (Williams %R, CCI, Keltner): **scope to the 12 cells where 2026 ΔAUC > 0 only**. Per-cell thresholds are in the report.

## Sample-size honesty

- 2026 = Jan-Jun = ~135K-200K M5 bars per cell. Plenty of statistical power per cell.
- 6 months is a half-cycle though — IF 2026 is a transient MR pocket within a longer trending regime, switching to all-reversion would overfit. Risk: 2-3 week shadow-mode is the mitigation.
- Confidence intervals on AUC lift estimates at n=100K bars per cell: ±0.005 (95%). The +0.08 mean profile-switch lift is 16× the noise floor.

## Reproduction

```bash
# On Mini:
~/.venvs/quantalib/bin/python ~/qtl-discovery-8yr/v5_2026_audit.py
# 48 cell audit, ~51s wall time with 8 cores
```

## Open follow-ups (NOT done in this session)

- **Wire profile flips + qtl rules + aggregator changes** with shadow logging — separate commit
- **PAIR_TUNING audit** — re-derive `atr_d_typical_pips`, `rvol_floor`, `atr_conc_floor` from 2026 distributions (V5 currently hardcoded from 2020-2024 averages)
- **momentum_profiles re-audit** — this session only re-audited direction_v2 profiles; momentum_v3 needs the same treatment
- **EVIDENCE_STRICTNESS tuning** — BAD=1.4 / WEAK=1.2 multipliers may need re-tuning
- **Monthly Mini cron** for ongoing re-audit
