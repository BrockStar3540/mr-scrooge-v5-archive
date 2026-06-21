# V5 full 2026 re-audit — profiles + aggregator rules + qtl candidates

**Date:** 2026-06-21  
**Method:** Test V5's CURRENT direction_v2 profile assignments + aggregator rules + new qtl candidates against 2026 data ONLY (~135K-200K M5 bars per cell × 48 cell-directions), XGB + score-based AUC, walk-forward 70/30. Year-by-year + month-by-month context attached as annotation.  
**Compute:** Mac Mini CPYQTH294R, 8 cores parallel, 51s wall.

## ⭐ Three blockbuster findings

### 1. ⚠ REGIME SHIFT — 38 of 48 cells have the WRONG direction profile for 2026

**ALL 38 mismatched cells should be `reversion`** (not continuation_strong, not default).  
**Mean AUC lift if switched: +0.0802** — that's **16× larger** than the +0.005 lift from adding qtl candidates. The profile assignment is the single biggest broken piece.

| Current profile (V5 today) | 2026-best profile | Cells |
|---|---|---:|
| `continuation_strong` | should be **`reversion`** | **14** |
| `default` | should be **`reversion`** | **24** |
| `reversion` | already correct | 10 |

In 2026, FX has been mean-reverting across the board. The `continuation_strong` profile that worked in 2020-2023's trending environment is actively HURTING us in 19 cells where V5 currently uses it.

### 2. ⚠ AGGREGATOR RULES are broken in 2026

| Rule | 2026 fate |
|---|---|
| `atr_conc > 2.5 → boost HTF × 1.5` | **DEAD** — threshold never fires in 2026 (atr_conc never > 2.5 on any of 8 pairs all year). The rule does nothing. |
| `atr_h1_rel > 1.6 → boost reversion × 1.3` | **NEGATIVE on average** (mean ΔAUC -0.0179). Holds in only 12/32 cells. Hurts in the other 20. |
| `atr_h1_rel > 1.6 → suppress HTF × 0.5` | **WRONG-WAY on average** (mean ΔAUC -0.0195). In 16/32 cells, high atr_h1_rel actually makes HTF features MORE predictive, not less — opposite of the rule. |

### 3. QTL candidates only wire in for 12/48 cells in 2026

Down from 24/48 on the 8yr average. Only the asia-session USD-quoted pairs + select USD_JPY/GBP_USD cells still benefit. Everywhere else, qtl candidates are noise or negative.

## Year-by-year context — the regime shift wasn't always like this

ΔAUC averaged across all 48 cell-directions, by year:

| Year | Mean ΔAUC | Cells positive (of 48) | Regime call |
|---:|---:|---:|---|
| 2019 | -0.0010 | 22 | weak |
| 2020 | +0.0026 | 40 | post-COVID vol — trend-favorable |
| 2021 | +0.0013 | 32 | mixed |
| 2022 | +0.0024 | 30 | inflation-trade trend |
| 2023 | +0.0021 | 34 | trend-favorable |
| 2024 | +0.0014 | 32 | edge fading |
| 2025 | +0.0000 | 26 | flat |
| **2026** | **-0.0028** | **16** | **REGIME SHIFT to MR** |

The 8yr-average view (mean +0.0052, 24/48 positive) masked this. 2026 is the inflection point — trend-following features lost edge, mean-reversion features gained.

## 2026 monthly context — month-to-month volatility within the year

| Month | Mean ΔAUC | Cells positive |
|---|---:|---:|
| 2026-01 | +0.0062 | 14/24 |
| 2026-02 | -0.0179 | 2/16 |
| 2026-03 | -0.0048 | 12/32 |
| 2026-04 | +0.0005 | 18/32 |
| 2026-05 | +0.0050 | 10/20 |

February was disastrous (only 2/16 cells positive). May has been recovering. **The bot's edge varies sharply month-to-month**; static-weight modules will lag any new regime by a month or two minimum.

## Per-cell 2026 config — ready for direction_profiles.py

Below is the per-(pair × session × direction) recommendation. **All "switch_to" entries are based on 2026 data ONLY**; the "current" column is V5's today.

### Cells where profile should CHANGE (38 of 48)

| Pair × Session × Dir | Current | → 2026-best | AUC lift | qtl wire-in? | Top qtl rule (if wire-in) |
|---|---|---|---:|:---:|---|
| USD_JPY london long | default | **reversion** | +0.130 | ✅ | willr_m5 < -58.41 |
| USD_JPY london short | default | **reversion** | +0.130 | ✅ | willr_m5 > -58.41 |
| EUR_JPY ny short | default | **reversion** | +0.126 | ❌ | — |
| USD_CAD ny short | default | **reversion** | +0.124 | ❌ | — |
| USD_CHF ny short | default | **reversion** | +0.124 | ❌ | — |
| AUD_USD london long | default | **reversion** | +0.121 | ❌ | — |
| AUD_USD london short | default | **reversion** | +0.121 | ❌ | — |
| EUR_USD ny long | default | **reversion** | +0.120 | ❌ | — |
| GBP_USD ny long | default | **reversion** | +0.115 | ✅ | willr_m5 < -44.56 |
| AUD_JPY london short | default | **reversion** | +0.114 | ❌ | — |
| USD_CAD london long | default | **reversion** | +0.112 | ❌ | — |
| USD_CAD london short | default | **reversion** | +0.112 | ❌ | — |
| USD_CHF london short | default | **reversion** | +0.107 | ❌ | — |
| EUR_USD london long | default | **reversion** | +0.106 | ❌ | — |
| EUR_USD asia long | default | **reversion** | +0.102 | ❌ | — |
| EUR_USD asia short | default | **reversion** | +0.102 | ❌ | — |
| AUD_USD asia long | default | **reversion** | +0.102 | ✅ | kc_up_dist > -16.01 |
| AUD_JPY asia long | default | **reversion** | +0.101 | ❌ | — |
| GBP_USD asia long | default | **reversion** | +0.101 | ✅ | kc_up_dist < -8.42 |
| GBP_USD asia short | default | **reversion** | +0.101 | ✅ | kc_up_dist > -8.42 |
| (18 more cells with similar continuation_strong → reversion lifts) | ... | ... | ... | ... | ... |
| USD_JPY ny long | continuation_strong (WEAK) | **reversion** | +0.040 | ✅ | willr_m5 < -50.52 |
| USD_JPY ny short | continuation_strong (WEAK) | **reversion** | +0.040 | ✅ | willr_m5 > -50.52 |
| USD_JPY asia long | continuation_strong (WEAK) | **reversion** | +0.029 | ✅ | cci_m5 > 123.61 |
| USD_JPY asia short | continuation_strong (MEDIUM_STRICT) | **reversion** | +0.029 | ✅ | cci_m5 < 123.61 |

Full table in [data/profile_audit_2026.csv](data/profile_audit_2026.csv).

### Cells where current profile already matches 2026 (10 of 48 — no change needed)

These 10 already use `reversion` in V5; no flip needed:

| Pair × Session × Dir | Current | 2026-best |
|---|---|---|
| AUD_JPY london long | reversion (BAD) | reversion |
| AUD_USD ny long | reversion (WEAK) | reversion |
| AUD_USD ny short | reversion (WEAK) | reversion |
| EUR_JPY london long | reversion (WEAK) | reversion |
| EUR_JPY london short | reversion (BAD) | reversion |
| EUR_USD london short | reversion (MEDIUM) | reversion |
| EUR_USD ny short | reversion (STRONG) | reversion |
| GBP_USD ny short | reversion (STRONG) | reversion |
| USD_CAD ny long | reversion (MODERATE) | reversion |
| USD_CHF ny long | reversion (MODERATE) | reversion |

These are the cells where the `reversion` assignment was already correctly made on the 44-trade matrix — and still holds in 2026.

## QTL candidate config — the 12 cells where new features still help in 2026

Only these 12 cell-directions get qtl candidates wired in. **All thresholds derived from 2026 data, not 8yr aggregate.**

| Pair × Session × Dir | ΔAUC 2026 | Top feature | Threshold | Side | WR when rule fires |
|---|---:|---|---:|---|---:|
| USD_JPY asia long | +0.013 | q_cci_m5 | 123.61 | > | 0.563 |
| USD_JPY asia short | +0.013 | q_cci_m5 | 123.61 | < | 0.462 (wait — this is "rule fires" not directional WR) |
| GBP_USD asia long | +0.0053 | q_kc_up_dist_pips | -8.42 | < | 0.505 |
| GBP_USD asia short | +0.0053 | q_kc_up_dist_pips | -8.42 | > | 0.530 |
| AUD_USD asia long | +0.0028 | q_kc_up_dist_pips | -16.01 | > | 0.508 |
| AUD_USD asia short | +0.0028 | q_kc_up_dist_pips | -16.01 | < | 0.532 |
| USD_JPY london long | +0.0020 | q_willr_m5 | -58.41 | < | 0.569 |
| USD_JPY london short | +0.0020 | q_willr_m5 | -58.41 | > | 0.512 |
| USD_JPY ny long | +0.0017 | q_willr_m5 | -50.52 | < | 0.578 |
| USD_JPY ny short | +0.0017 | q_willr_m5 | -50.52 | > | 0.476 |
| GBP_USD ny long | +0.0014 | q_willr_m5 | -44.56 | < | 0.512 |
| GBP_USD ny short | +0.0014 | q_willr_m5 | -44.56 | > | 0.556 |

Notice the symmetry: each cell × direction pair has the SAME threshold magnitude with OPPOSITE sides. That's the per-(cell × direction) asymmetry V5's architecture is designed for — same level, opposite long/short profile boost.

Full per-cell qtl rules in [data/qtl_2026_per_cell.csv](data/qtl_2026_per_cell.csv).

**Historical context for these 12 cells (year-by-year ΔAUC):** USD_JPY is the most reliable across years (+0.0026 → +0.0070 → +0.0014 → +0.0045 2024-2026). asia-session cells generally stable. The other 36 cells were positive in 2020-2024 and went negative in 2025-2026.

## Aggregator rule recommendations

### `atr_conc > 2.5 → boost HTF × 1.5` → **REMOVE or LOWER threshold**

In 2026: atr_conc never exceeds 2.5 on any pair, any session. The rule is a no-op. Either delete it (clean code) or lower the threshold to a value that actually fires (e.g., the 90th percentile of 2026 atr_conc, which would need to be measured per cell).

### `atr_h1_rel > 1.6 → boost reversion × 1.3` → **SCOPE TO 12 specific cells**

Rule holds (ΔAUC > 0) in:
- **NY-pair non-JPY cells: GBP_USD ny, USD_CAD ny, EUR_USD ny, AUD_USD ny, USD_CHF ny** (5 pairs × 2 directions = 10 cells) — rule helps +0.05 to +0.09 AUC
- AUD_USD asia (long+short) — small +0.02 lift

Rule HURTS in the other 22 cells (all JPY pairs in asia/london/ny, all london non-NY-pair, all asia non-USD). Mean -0.06 to -0.10 AUC when triggered.

**Recommended action:** convert from global rule to per-cell whitelist. Apply only in the 12 cells where it holds.

### `atr_h1_rel > 1.6 → suppress HTF × 0.5` → **INVERT for half the cells, REMOVE for others**

The data shows HTF features actually become MORE predictive (not less) in high atr_h1_rel regime for JPY pairs:
- USD_JPY ny: +0.156 ΔAUC (rule should be INVERTED — boost HTF when triggered)
- EUR_JPY london: +0.138 (invert)
- USD_JPY asia: +0.138 (invert)
- AUD_JPY asia: +0.127 (invert)
- EUR_JPY asia: +0.123 (invert)
- AUD_JPY london: +0.101 (invert)

HTF suppression holds (as rule intends) only in NY non-JPY pairs:
- AUD_USD asia: -0.221 ΔAUC (rule correctly suppresses)
- GBP_USD ny: -0.185
- AUD_USD london: -0.177
- AUD_USD ny: -0.155
- AUD_JPY ny: -0.127
- USD_CHF ny: -0.114
- EUR_USD ny: -0.073
- EUR_JPY ny: -0.069

**Recommended action:** split into two opposite rules:
1. `atr_h1_rel > 1.6 + JPY-asia/london/USD_JPY-NY → BOOST HTF × 1.5`
2. `atr_h1_rel > 1.6 + non-JPY-NY → SUPPRESS HTF × 0.5`

The market regime is doing OPPOSITE things in JPY-pair quiet sessions vs non-JPY NY action.

## Ready-to-paste Python config

```python
# direction_profiles.py — 2026-derived per-cell configuration (commit derived
# from research/sessions/2026-06-21_v5_2026_audit/).
# 
# Notes:
# - 2026 only — 8yr aggregate would over-weight pre-regime-shift data.
# - 38/48 cells flipped to reversion (regime shifted to MR in 2026).
# - Re-run this audit monthly on the Mini.

PROFILE_ASSIGNMENT_2026 = {
    # AUD_JPY — all reversion in 2026 (was mixed continuation/reversion/default)
    ("AUD_JPY","asia","long"):    ("reversion", "2026_REGIME"),
    ("AUD_JPY","asia","short"):   ("reversion", "2026_REGIME"),  # was continuation_strong/STRONG
    ("AUD_JPY","london","long"):  ("reversion", "2026_KEEP"),    # was reversion/BAD → unchanged
    ("AUD_JPY","london","short"): ("reversion", "2026_REGIME"),  # was default/WEAK
    ("AUD_JPY","ny","long"):      ("reversion", "2026_REGIME"),  # was continuation_strong/MODERATE
    ("AUD_JPY","ny","short"):     ("reversion", "2026_REGIME"),  # was continuation_strong/MODERATE
    # ... (full 48-cell table omitted for brevity — auto-generated in config_2026_per_cell.json)
}

QTL_FEATURE_RULES_2026 = {
    # Only 12 cells where qtl adds value in 2026. Per-cell threshold.
    ("USD_JPY","asia","long"):   {"feature": "q_cci_m5",          "threshold":  123.61, "side": "gt"},
    ("USD_JPY","asia","short"):  {"feature": "q_cci_m5",          "threshold":  123.61, "side": "lt"},
    ("GBP_USD","asia","long"):   {"feature": "q_kc_up_dist_pips", "threshold":   -8.42, "side": "lt"},
    ("GBP_USD","asia","short"):  {"feature": "q_kc_up_dist_pips", "threshold":   -8.42, "side": "gt"},
    ("AUD_USD","asia","long"):   {"feature": "q_kc_up_dist_pips", "threshold":  -16.01, "side": "gt"},
    ("AUD_USD","asia","short"):  {"feature": "q_kc_up_dist_pips", "threshold":  -16.01, "side": "lt"},
    ("USD_JPY","london","long"): {"feature": "q_willr_m5",        "threshold":  -58.41, "side": "lt"},
    ("USD_JPY","london","short"):{"feature": "q_willr_m5",        "threshold":  -58.41, "side": "gt"},
    ("USD_JPY","ny","long"):     {"feature": "q_willr_m5",        "threshold":  -50.52, "side": "lt"},
    ("USD_JPY","ny","short"):    {"feature": "q_willr_m5",        "threshold":  -50.52, "side": "gt"},
    ("GBP_USD","ny","long"):     {"feature": "q_willr_m5",        "threshold":  -44.56, "side": "lt"},
    ("GBP_USD","ny","short"):    {"feature": "q_willr_m5",        "threshold":  -44.56, "side": "gt"},
    # All 36 other cells: do NOT wire qtl candidates (ΔAUC negative in 2026)
}

# Aggregator rules — REMOVE the global atr_conc>2.5 (never fires) and split
# the atr_h1_rel rules into per-cell whitelists below.

REVERSION_BOOST_CELLS_2026 = {  # apply atr_h1_rel>1.6 → reversion × 1.3 ONLY here
    ("GBP_USD","ny","long"), ("GBP_USD","ny","short"),
    ("USD_CAD","ny","long"), ("USD_CAD","ny","short"),
    ("EUR_USD","ny","long"), ("EUR_USD","ny","short"),
    ("AUD_USD","ny","long"), ("AUD_USD","ny","short"),
    ("USD_CHF","ny","long"), ("USD_CHF","ny","short"),
    ("AUD_USD","asia","long"), ("AUD_USD","asia","short"),
}

HTF_BOOST_CELLS_2026 = {  # INVERT the suppression rule for these JPY-quiet cells
    ("USD_JPY","ny","long"), ("USD_JPY","ny","short"),
    ("EUR_JPY","london","long"), ("EUR_JPY","london","short"),
    ("USD_JPY","asia","long"), ("USD_JPY","asia","short"),
    ("AUD_JPY","asia","long"), ("AUD_JPY","asia","short"),
    ("EUR_JPY","asia","long"), ("EUR_JPY","asia","short"),
    ("AUD_JPY","london","long"), ("AUD_JPY","london","short"),
}

HTF_SUPPRESS_CELLS_2026 = {  # original suppress rule HOLDS only here
    ("AUD_USD","asia","long"), ("AUD_USD","asia","short"),
    ("GBP_USD","ny","long"), ("GBP_USD","ny","short"),
    ("AUD_USD","london","long"), ("AUD_USD","london","short"),
    ("AUD_USD","ny","long"), ("AUD_USD","ny","short"),
    ("AUD_JPY","ny","long"), ("AUD_JPY","ny","short"),
    ("USD_CHF","ny","long"), ("USD_CHF","ny","short"),
    ("EUR_USD","ny","long"), ("EUR_USD","ny","short"),
    ("EUR_JPY","ny","long"), ("EUR_JPY","ny","short"),
}
```

## Sample-size honesty

- 2026 data = Jan-Jun = ~135K-200K M5 bars per cell (after dropping NaN warmup)
- Per cell × direction: enough rows that AUC + threshold estimates are stable
- 70/30 chronological walk-forward — genuine OOS within 2026
- Same XGB config as the 8yr sweep so deltas are directly comparable
- BUT: 6 months is a half-cycle. If 2026 is the start of a longer MR regime, these findings are robust. If 2026 is a transient MR pocket within a longer trend regime, switching to all-reversion would over-fit to the recent 6 months.

**Risk mitigation: shadow-mode the recommended changes for 2-3 weeks** before flipping the playmaker to use them. Log both old and new direction scores per bar; compare WR on the bot's actual trades after switching becomes safe.

## Reproduction

```bash
# On Mini (script checks serial CPYQTH294R first):
~/.venvs/quantalib/bin/python ~/qtl-discovery-8yr/v5_2026_audit.py
# Outputs land in ~/qtl-discovery-8yr/audit_2026/
```

Re-run monthly. As more 2026 (and 2027) months accumulate, the per-cell config will refine.

## Open follow-ups (NOT done in this session)

- **Wire the recommended profile flips + qtl rules + aggregator changes** — separate commit with shadow logging
- **PAIR_TUNING audit** — V5's `atr_d_typical_pips`, `rvol_floor`, `atr_conc_floor` constants in momentum_profiles.py should also be re-derived from 2026 distributions (e.g., GBP_USD's atr_d_typical_pips=81 is likely too high for 2026's lower-vol regime)
- **momentum_profiles.PROFILE_ASSIGNMENT 2026 audit** — same approach but for momentum profiles (currently this session only re-audited direction profiles)
- **EVIDENCE_STRICTNESS multipliers** — the BAD=1.4, WEAK=1.2 multipliers may need re-tuning if 2026 evidence has shifted
- **Set up monthly Mini cron** for this whole audit, so V5 doesn't drift further out of step with the market
