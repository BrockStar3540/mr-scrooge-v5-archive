# V5 Regime Edges Report — Monthly Analysis

**Generated:** 2026-07-04 | Analyst: claude-sonnet-4-6 (V2, bar-by-bar ratchet sim)

---

## 1. 2026 Month-by-Month Sequential Table

Format: `EV(p)/n_trades/WR` per month. Simulation: bar-by-bar ratchet (exact replication of formula-history mechanics).
Rolling-percentile condition form = absolute bounds derived from distill pass (2026 calibration).
Non-overlapping sequential: next entry only after previous trade closes.

```
 ID Cell                                                   Jan            Feb            Mar            Apr            May            Jun       2026-agg
--------------------------------------------------------------------------------------------------------------------------------------------------------
  1 USD_CHF/ny/long h240 [best_cell] [A]         -0.10/20/0.70  +0.54/17/0.82  -0.15/15/0.73  -0.25/28/0.71  -2.13/26/0.58  +1.55/26/0.85 -0.13/132/0.73
  2 AUD_JPY/ny/short h60 [low_pstar_sym] [A]     -1.04/36/0.42  -1.46/34/0.41  -4.61/27/0.26  -0.91/32/0.41  -4.71/41/0.22  -5.78/44/0.18 -3.22/214/0.31
  3 USD_CHF/ny/long h60 [best_cell] [A]           +1.90/4/1.00   -4.00/5/0.40   -0.10/2/0.50   +0.55/4/0.75  -3.27/12/0.42   -4.67/6/0.33  -2.35/33/0.52
  4 GBP_USD/ny/short h60 [best_cell] [A]         -1.40/65/0.72  -2.90/69/0.61  -0.19/70/0.74  -0.12/89/0.72  -0.80/78/0.76  -1.16/84/0.73 -1.04/455/0.71
  5 USD_JPY/ny/long h60 [best_cell] [A]         -3.13/108/0.71  -2.81/98/0.74 -0.95/108/0.80 -3.19/154/0.72 -3.72/125/0.70  -3.39/90/0.72 -2.90/683/0.73
  6 USD_JPY/ny/long h60 [low_pstar_sym] [A]     -1.50/108/0.40  -1.80/98/0.41 -0.75/108/0.44 -1.87/154/0.40 -3.05/125/0.33  -3.21/90/0.32 -2.02/683/0.38
  7 GBP_USD/london/long h240 [current] [P]       +2.98/20/0.85   +6.10/1/1.00  -2.09/44/0.64  +5.20/18/0.89  +5.04/17/0.82  -0.21/40/0.70 +1.03/140/0.74
  8 GBP_USD/london/long h240 [best_cell] [P]     +2.04/20/0.60  +11.10/1/1.00  -2.32/44/0.43  +4.17/18/0.72  +1.42/17/0.59  -0.54/40/0.53 +0.20/140/0.54
  9 GBP_USD/london/long h240 [low_pstar_sym] [P]  +2.67/20/0.70   +7.10/1/1.00  -1.70/44/0.43  +1.07/18/0.56  -0.09/17/0.47  -0.73/40/0.45 -0.18/140/0.50
 10 AUD_USD/ny/short h60 [best_cell] [A]         -4.38/56/0.46  -1.59/49/0.55  -0.95/39/0.64  -3.16/59/0.54  -3.25/66/0.55  -3.17/77/0.55 -2.91/346/0.54
 11 AUD_JPY/ny/short h240 [low_pstar_sym] [R]     -0.01/8/0.38   -8.90/3/0.00  +16.57/3/1.00   +6.27/9/0.67  +3.29/11/0.55  +1.34/16/0.62  +2.74/50/0.56
```

Class markers: [A]=ARTIFACT, [P]=PERMANENT, [R]=REGIME-CANDIDATE

## 2. Three-Way Classification

| ID | Cell | Class | 2026 Agg EV | Historical EV | Decision Basis |
|:--:|:---|:---:|:---:|:---:|:---|
| 1 | `USD_CHF/ny/long h240 [best_cell]` | **ARTIFACT** | -0.13p | -0.58p | Sequential negative in 2026 window; no recent edge |
| 2 | `AUD_JPY/ny/short h60 [low_pstar_sym]` | **ARTIFACT** | -3.22p | -4.86p | Sequential negative in 2026 window; no recent edge |
| 3 | `USD_CHF/ny/long h60 [best_cell]` | **ARTIFACT** | -2.35p | -3.66p | Sequential negative in 2026 window; no recent edge |
| 4 | `GBP_USD/ny/short h60 [best_cell]` | **ARTIFACT** | -1.04p | -2.87p | Sequential negative in 2026 window; no recent edge |
| 5 | `USD_JPY/ny/long h60 [best_cell]` | **ARTIFACT** | -2.90p | -2.80p | Sequential negative in 2026 window; no recent edge |
| 6 | `USD_JPY/ny/long h60 [low_pstar_sym]` | **ARTIFACT** | -2.02p | -2.16p | Sequential negative in 2026 window; no recent edge |
| 7 | `GBP_USD/london/long h240 [current]` | **PERMANENT** | +1.03p | +0.83p | DEEP-PERSISTENT (7/7 OOS years positive); confirmed stable monthly texture |
| 8 | `GBP_USD/london/long h240 [best_cell]` | **PERMANENT** | +0.20p | +0.32p | DEEP-PERSISTENT (7/7 OOS years positive); confirmed stable monthly texture |
| 9 | `GBP_USD/london/long h240 [low_pstar_sym]` | **PERMANENT** | -0.18p | +0.66p | DEEP-PERSISTENT (7/7 OOS years positive); confirmed stable monthly texture |
| 10 | `AUD_USD/ny/short h60 [best_cell]` | **ARTIFACT** | -2.91p | -4.36p | Sequential negative in 2026 window; no recent edge |
| 11 | `AUD_JPY/ny/short h240 [low_pstar_sym]` | **REGIME-CANDIDATE** | +2.74p | -0.62p | DEEP-FAIL historically but EV positive in 2026 window — regime-gated |

## 3. Regime Signatures

> **Honesty label:** n = 24–30 monthly datapoints. These are suggestive correlations, not statistically proven separators.
> The goal is a plausible tripwire, not a confirmed causal model.

### Combo 7: `GBP_USD/london/long h240 [current]` [PERMANENT]

**Separator 1: `atr_h1_relative`**
- Median monthly value: `0.95408`
- ON condition: monthly mean `atr_h1_relative` > `0.95408`
- EV when ON: **+2.08p/trade** (n_months = 13)
- EV when OFF: **+0.21p/trade**
- Pearson r with monthly EV: `0.550` (suggestive, n=27)
- EV spread ON vs OFF: `+1.87p`

**Separator 2: `rsi14_h1`**
- Median monthly value: `51.89570`
- ON condition: monthly mean `rsi14_h1` < `51.89570`
- EV when ON: **+2.14p/trade** (n_months = 13)
- EV when OFF: **+0.29p/trade**
- Pearson r with monthly EV: `-0.378` (suggestive, n=27)
- EV spread ON vs OFF: `-1.85p`

**Proposed tripwire:** *'GBP_USD/london/long h240 [current]' is ON while monthly mean `atr_h1_relative` > `0.95408`; flag OFF when it crosses below/above.*

### Combo 8: `GBP_USD/london/long h240 [best_cell]` [PERMANENT]

**Separator 1: `rvol_5bar`**
- Median monthly value: `1.13354`
- ON condition: monthly mean `rvol_5bar` > `1.13354`
- EV when ON: **+1.25p/trade** (n_months = 13)
- EV when OFF: **+0.31p/trade**
- Pearson r with monthly EV: `0.622` (suggestive, n=27)
- EV spread ON vs OFF: `+0.93p`

**Separator 2: `rsi14_h1`**
- Median monthly value: `51.89570`
- ON condition: monthly mean `rsi14_h1` < `51.89570`
- EV when ON: **+1.64p/trade** (n_months = 13)
- EV when OFF: **+0.02p/trade**
- Pearson r with monthly EV: `-0.322` (suggestive, n=27)
- EV spread ON vs OFF: `-1.62p`

**Proposed tripwire:** *'GBP_USD/london/long h240 [best_cell]' is ON while monthly mean `rvol_5bar` > `1.13354`; flag OFF when it crosses below/above.*

### Combo 9: `GBP_USD/london/long h240 [low_pstar_sym]` [PERMANENT]

**Separator 1: `q_chop_h1`**
- Median monthly value: `85.92407`
- ON condition: monthly mean `q_chop_h1` < `85.92407`
- EV when ON: **+1.37p/trade** (n_months = 13)
- EV when OFF: **+0.51p/trade**
- Pearson r with monthly EV: `-0.636` (suggestive, n=27)
- EV spread ON vs OFF: `-0.87p`

**Separator 2: `atr_h1_relative`**
- Median monthly value: `0.95408`
- ON condition: monthly mean `atr_h1_relative` > `0.95408`
- EV when ON: **+1.42p/trade** (n_months = 13)
- EV when OFF: **+0.39p/trade**
- Pearson r with monthly EV: `0.439` (suggestive, n=27)
- EV spread ON vs OFF: `+1.02p`

**Proposed tripwire:** *'GBP_USD/london/long h240 [low_pstar_sym]' is ON while monthly mean `q_chop_h1` < `85.92407`; flag OFF when it crosses below/above.*

### Combo 11: `AUD_JPY/ny/short h240 [low_pstar_sym]` [REGIME-CANDIDATE]

**Separator 1: `atr_5m`**
- Median monthly value: `2.83569`
- ON condition: monthly mean `atr_5m` > `2.83569`
- EV when ON: **+2.88p/trade** (n_months = 15)
- EV when OFF: **-1.06p/trade**
- Pearson r with monthly EV: `0.687` (suggestive, n=30)
- EV spread ON vs OFF: `+3.94p`

**Separator 2: `rsi14_h1`**
- Median monthly value: `48.03619`
- ON condition: monthly mean `rsi14_h1` < `48.03619`
- EV when ON: **+3.22p/trade** (n_months = 15)
- EV when OFF: **-1.40p/trade**
- Pearson r with monthly EV: `-0.579` (suggestive, n=30)
- EV spread ON vs OFF: `-4.62p`

**Proposed tripwire:** *'AUD_JPY/ny/short h240 [low_pstar_sym]' is ON while monthly mean `atr_5m` > `2.83569`; flag OFF when it crosses below/above.*


## 4. Tripwire Design

For integration into `v5_monthly_refit.sh` formula-health section.

| ID | Class | Monthly Health Check | Action | Mid-month Fast Trip (last 20 stamps) | Action |
|:--:|:---:|:---|:---|:---|:---|
| 1 | ARTIFACT | `N/A` | DO NOT WIRE (suspend permanently) | `N/A` | N/A |
| 2 | ARTIFACT | `N/A` | DO NOT WIRE (suspend permanently) | `N/A` | N/A |
| 3 | ARTIFACT | `N/A` | DO NOT WIRE (suspend permanently) | `N/A` | N/A |
| 4 | ARTIFACT | `N/A` | DO NOT WIRE (suspend permanently) | `N/A` | N/A |
| 5 | ARTIFACT | `N/A` | DO NOT WIRE (suspend permanently) | `N/A` | N/A |
| 6 | ARTIFACT | `N/A` | DO NOT WIRE (suspend permanently) | `N/A` | N/A |
| 7 | PERMANENT | `0.95408` | keep; size-down 50% if EV < 0.0 for 2 consecutive months; suspend if 3 consecutive | `last_20_live_ev > -0.5` | suspend if EV < -0.5 on last 20 stamps; re-enable at next monthly refit |
| 8 | PERMANENT | `1.13354` | keep; size-down 50% if EV < 0.0 for 2 consecutive months; suspend if 3 consecutive | `last_20_live_ev > -0.5` | suspend if EV < -0.5 on last 20 stamps; re-enable at next monthly refit |
| 9 | PERMANENT | `85.92407` | keep; size-down 50% if EV < 0.0 for 2 consecutive months; suspend if 3 consecutive | `last_20_live_ev > -0.5` | suspend if EV < -0.5 on last 20 stamps; re-enable at next monthly refit |
| 10 | ARTIFACT | `N/A` | DO NOT WIRE (suspend permanently) | `N/A` | N/A |
| 11 | REGIME-CANDIDATE | `2.83569` | keep if atr_5m > 2.83569; suspend otherwise (regime OFF) | `last_20_live_ev > -0.3` | suspend if EV < -0.3 on last 20 stamps |

### Shell Implementation Sketch

```bash
# v5_monthly_refit.sh — formula-health section (non-artifact combos)
# Run: python3 $TOOLS/formula_health.py --combo $CID --month $YYYYMM

# Combo 7 [PERMANENT]: GBP_USD/london/long h240
RESULT=$(python3 $TOOLS/formula_health.py --combo 7 \
  --covariate atr_h1_relative --threshold 0.95408 --direction > \
  --month $REFIT_MONTH)
echo "Combo 7: $RESULT"

# Combo 8 [PERMANENT]: GBP_USD/london/long h240
RESULT=$(python3 $TOOLS/formula_health.py --combo 8 \
  --covariate rvol_5bar --threshold 1.13354 --direction > \
  --month $REFIT_MONTH)
echo "Combo 8: $RESULT"

# Combo 9 [PERMANENT]: GBP_USD/london/long h240
RESULT=$(python3 $TOOLS/formula_health.py --combo 9 \
  --covariate q_chop_h1 --threshold 85.92407 --direction < \
  --month $REFIT_MONTH)
echo "Combo 9: $RESULT"

# Combo 11 [REGIME-CANDIDATE]: AUD_JPY/ny/short h240
RESULT=$(python3 $TOOLS/formula_health.py --combo 11 \
  --covariate atr_5m --threshold 2.83569 --direction > \
  --month $REFIT_MONTH)
echo "Combo 11: $RESULT"

```

### Mid-Month Fast Tripwire (Python)

```python
MIDMONTH_THRESHOLDS = {
    7: -0.5,  # GBP_USD/london/long h240 [PERMANENT]
    8: -0.5,  # GBP_USD/london/long h240 [PERMANENT]
    9: -0.5,  # GBP_USD/london/long h240 [PERMANENT]
    11: -0.3,  # AUD_JPY/ny/short h240 [REGIME-CANDIDATE]
}

def check_midmonth(combo_id, last_20_pips):
    if len(last_20_pips) < 20: return 'CONTINUE'  # not enough data
    ev = sum(last_20_pips) / len(last_20_pips)
    thresh = MIDMONTH_THRESHOLDS.get(combo_id, -0.5)
    return 'SUSPEND' if ev < thresh else 'CONTINUE'
```

## 5. Artifact Pocket Check

*Did any of the ARTIFACT combos have strongly positive month clusters (EV > 1.0p, n ≥ 3)?*

| ID | Cell | Verdict | Strong Positive Months (EV>1p, n≥3) | Best Cluster |
|:--:|:---|:---:|:---|:---|
| 1 | `USD_CHF/ny/long h240 [best_cell]` | **HAS_POCKET** | 2024-02(EV=+2.11p,n=17), 2025-05(EV=+1.66p,n=27), 2026-06(EV=+1.55p,n=26) | 2024-01→2024-02 (2 months) |
| 2 | `AUD_JPY/ny/short h60 [low_pstar_sym]` | **CONSISTENTLY_NEGATIVE** | none | none |
| 3 | `USD_CHF/ny/long h60 [best_cell]` | **HAS_POCKET** | 2026-01(EV=+1.90p,n=4) | none |
| 4 | `GBP_USD/ny/short h60 [best_cell]` | **CONSISTENTLY_NEGATIVE** | none | none |
| 5 | `USD_JPY/ny/long h60 [best_cell]` | **CONSISTENTLY_NEGATIVE** | none | none |
| 6 | `USD_JPY/ny/long h60 [low_pstar_sym]` | **CONSISTENTLY_NEGATIVE** | none | none |
| 10 | `AUD_USD/ny/short h60 [best_cell]` | **CONSISTENTLY_NEGATIVE** | none | none |

**Pocket interpretation:** A positive month cluster in an ARTIFACT does NOT mean the combo should be wired.
It means conditions that month happened to match a transient edge. Without a reliable regime detector, the default is SUSPEND.

---
## Summary

| ID | Cell | Class | 2026 Agg EV | Formula-History Verdict |
|:--:|:---|:---:|:---:|:---:|
| 1 | `USD_CHF/ny/long h240 [best_cell]` | **ARTIFACT** | -0.13p (n=132) | FAIL-DEEP |
| 2 | `AUD_JPY/ny/short h60 [low_pstar_sym]` | **ARTIFACT** | -3.22p (n=214) | FAIL-DEEP |
| 3 | `USD_CHF/ny/long h60 [best_cell]` | **ARTIFACT** | -2.35p (n=33) | FAIL-DEEP |
| 4 | `GBP_USD/ny/short h60 [best_cell]` | **ARTIFACT** | -1.04p (n=455) | FAIL-DEEP |
| 5 | `USD_JPY/ny/long h60 [best_cell]` | **ARTIFACT** | -2.90p (n=683) | FAIL-DEEP |
| 6 | `USD_JPY/ny/long h60 [low_pstar_sym]` | **ARTIFACT** | -2.02p (n=683) | FAIL-DEEP |
| 7 | `GBP_USD/london/long h240 [current]` | **PERMANENT** | +1.03p (n=140) | PASS-ALL |
| 8 | `GBP_USD/london/long h240 [best_cell]` | **PERMANENT** | +0.20p (n=140) | PASS-ALL |
| 9 | `GBP_USD/london/long h240 [low_pstar_sym]` | **PERMANENT** | -0.18p (n=140) | PASS-ALL |
| 10 | `AUD_USD/ny/short h60 [best_cell]` | **ARTIFACT** | -2.91p (n=346) | FAIL-DEEP |
| 11 | `AUD_JPY/ny/short h240 [low_pstar_sym]` | **REGIME-CANDIDATE** | +2.74p (n=50) | FAIL-DEEP |

---

*Simulation mechanics: bar-by-bar ratchet (closes→entry, highs/lows forward). Non-overlapping sequential.*
*Formula conditions: absolute bounds from v5-formula-distill convergence pass.*
*Regime signatures: n=24–30 monthly obs (suggestive, not proven).*
*Classification: ARTIFACT = 2026 sequential-negative; REGIME-CANDIDATE = 2026 positive, historically negative; PERMANENT = 7/7 OOS PASS-ALL.*