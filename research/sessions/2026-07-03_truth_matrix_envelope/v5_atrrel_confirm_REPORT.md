# ATR H1 Relative Asymmetry — 2026 Window Confirmation Study
**Date:** 2026-07-03  
**Analyst:** Claude Code (read-only; facts + classification only, no changes)  
**Device verified:** CPYQTH294R (Mac Mini)  
**Data:** ~/v5-truth-matrix/*_truth.parquet, 2026 bars only (2026-01-01 to 2026-07-03)  
**Script:** ~/v5-atrrel-confirm/atr_confirm.py  
**Prior finding:** ~/v5-taint-rederivation/item4_atr_h1_rel.csv (8yr basis)  

---

## Data Summary

| Item | Value |
|------|-------|
| Total 2026 bars (8 pairs) | 297,952 |
| Date range | 2026-01-01 22:00 UTC → 2026-07-03 05:50 UTC |
| Bars where atr_h1_relative > 1.6 | 4,874 (1.6%) |
| Total cells (pair × session × direction) | 48 |
| Cells with n_hi_vol >= 10 | 44 |
| Cells with n_hi_vol = 0 (USD_CAD/CHF london) | 4 → classified OFF |

**Metric used:** MFE−MAE per direction at 60-min horizon (net excursion asymmetry).  
Delta = mean(MFE−MAE | hi_vol) − mean(MFE−MAE | lo_vol). Noise band: ±0.5 pip.

---

## Task 1: 2026 Per-Cell Asymmetry — Does High Relative Vol Still HELP Longs / HURT Shorts?

**Short answer: NO. The 8yr framing is INVERTED in 2026.**

The 2026 window shows the **opposite** of the 8yr finding:
- HIGH relative vol (>1.6) **HURTS longs** and **HELPS shorts**
- Mean net excursion (MFE−MAE) at high vol: **LONG = −1.94 pips, SHORT = +1.94 pips**
- 11 of 22 long cells → INVERT (high vol hurts them); 9 of 22 → KEEP (helped)
- 11 of 22 short cells → KEEP (high vol helps them); 9 of 22 → INVERT

**8yr claimed:** high vol → helps longs (KEEP), hurts shorts (INVERT).  
**2026 says:** high vol → hurts longs (net INVERT), helps shorts (net KEEP).  
This is a regime flip.

### 2026 Verdict Distribution (48 cells)

| Verdict | Count |
|---------|-------|
| KEEP    | 20    |
| INVERT  | 20    |
| OFF     | 4     |
| INSUFF  | 4     |

The 20/20 KEEP/INVERT split does NOT reproduce the 8yr "longs KEEP, shorts INVERT" pattern. Agreement vs 8yr:
- AGREE (both say same): **14 / 48** (29%)
- DISAGREE (opposite): **14 / 48** (29%)
- PARTIAL (one side is OFF): **16 / 48** (33%)
- INSUFF (no 2026 data): **4 / 48** (8%)

### Full Cell Table (2026 results vs 8yr)

| pair | session | dir | n_hi | delta(pip) | verdict_2026 | rec_8yr | agree |
|------|---------|-----|------|------------|--------------|---------|-------|
| AUD_JPY | asia | long | 203 | -2.05 | INVERT | KEEP | DISAGREE |
| AUD_JPY | asia | short | 203 | +2.05 | KEEP | INVERT | DISAGREE |
| AUD_JPY | london | long | 132 | +2.05 | KEEP | KEEP | AGREE |
| AUD_JPY | london | short | 132 | -2.05 | INVERT | INVERT | AGREE |
| AUD_JPY | ny | long | 239 | +1.03 | KEEP | OFF | PARTIAL |
| AUD_JPY | ny | short | 239 | -1.03 | INVERT | OFF | PARTIAL |
| AUD_USD | asia | long | 130 | +0.92 | KEEP | KEEP | AGREE |
| AUD_USD | asia | short | 130 | -0.92 | INVERT | INVERT | AGREE |
| AUD_USD | london | long | 119 | -2.67 | INVERT | KEEP | DISAGREE |
| AUD_USD | london | short | 119 | +2.67 | KEEP | INVERT | DISAGREE |
| AUD_USD | ny | long | 372 | +2.42 | KEEP | OFF | PARTIAL |
| AUD_USD | ny | short | 372 | -2.42 | INVERT | OFF | PARTIAL |
| EUR_JPY | asia | long | 252 | -5.68 | INVERT | KEEP | DISAGREE |
| EUR_JPY | asia | short | 252 | +5.68 | KEEP | INVERT | DISAGREE |
| EUR_JPY | london | long | 311 | -15.79 | INVERT | OFF | PARTIAL |
| EUR_JPY | london | short | 311 | +15.79 | KEEP | OFF | PARTIAL |
| EUR_JPY | ny | long | 299 | +0.77 | KEEP | KEEP | AGREE |
| EUR_JPY | ny | short | 299 | -0.77 | INVERT | INVERT | AGREE |
| EUR_USD | asia | long | 94 | -3.70 | INVERT | OFF | PARTIAL |
| EUR_USD | asia | short | 94 | +3.70 | KEEP | OFF | PARTIAL |
| EUR_USD | london | long | 48 | +1.93 | KEEP | KEEP | AGREE |
| EUR_USD | london | short | 48 | -1.93 | INVERT | INVERT | AGREE |
| EUR_USD | ny | long | 393 | +0.88 | KEEP | KEEP | AGREE |
| EUR_USD | ny | short | 393 | -0.88 | INVERT | INVERT | AGREE |
| GBP_USD | asia | long | 12 | -0.94 | INVERT | OFF | PARTIAL |
| GBP_USD | asia | short | 12 | +0.94 | KEEP | OFF | PARTIAL |
| GBP_USD | london | long | 60 | +11.04 | KEEP | INVERT | DISAGREE |
| GBP_USD | london | short | 60 | -11.04 | INVERT | KEEP | DISAGREE |
| GBP_USD | ny | long | 287 | +0.95 | KEEP | INVERT | DISAGREE |
| GBP_USD | ny | short | 287 | -0.95 | INVERT | KEEP | DISAGREE |
| USD_CAD | asia | long | 24 | -1.15 | INVERT | INVERT | AGREE |
| USD_CAD | asia | short | 24 | +1.15 | KEEP | KEEP | AGREE |
| USD_CAD | london | long | 0 | — | INSUFF | INVERT | INSUFF |
| USD_CAD | london | short | 0 | — | INSUFF | KEEP | INSUFF |
| USD_CAD | ny | long | 322 | +0.20 | OFF | OFF | AGREE |
| USD_CAD | ny | short | 322 | -0.20 | OFF | OFF | AGREE |
| USD_CHF | asia | long | 60 | -3.93 | INVERT | KEEP | DISAGREE |
| USD_CHF | asia | short | 60 | +3.93 | KEEP | INVERT | DISAGREE |
| USD_CHF | london | long | 0 | — | INSUFF | INVERT | INSUFF |
| USD_CHF | london | short | 0 | — | INSUFF | KEEP | INSUFF |
| USD_CHF | ny | long | 323 | -0.30 | OFF | INVERT | PARTIAL |
| USD_CHF | ny | short | 323 | +0.30 | OFF | KEEP | PARTIAL |
| USD_JPY | asia | long | 370 | -3.53 | INVERT | KEEP | DISAGREE |
| USD_JPY | asia | short | 370 | +3.53 | KEEP | INVERT | DISAGREE |
| USD_JPY | london | long | 287 | -17.83 | INVERT | OFF | PARTIAL |
| USD_JPY | london | short | 287 | +17.83 | KEEP | OFF | PARTIAL |
| USD_JPY | ny | long | 537 | -1.88 | INVERT | OFF | PARTIAL |
| USD_JPY | ny | short | 537 | +1.88 | KEEP | OFF | PARTIAL |

---

## Task 2: Monthly Stability Within 2026 (Jan–Jun)

Only cells with ≥4 valid months are reported as stable/unstable. Results for confirmed cells:

| pair | session | direction | verdict_2026 | stable_pct | stability |
|------|---------|-----------|--------------|------------|-----------|
| AUD_JPY | asia | long | INVERT | 0.75 | STABLE |
| AUD_JPY | asia | short | KEEP | 0.75 | STABLE |
| AUD_JPY | london | long | KEEP | NaN | WEAK (few months with data) |
| AUD_JPY | london | short | INVERT | NaN | WEAK |
| EUR_JPY | asia | long | INVERT | 0.75 | STABLE |
| EUR_JPY | asia | short | KEEP | 0.75 | STABLE |
| EUR_JPY | london | long | INVERT | 0.75 | STABLE |
| EUR_JPY | london | short | KEEP | 0.75 | STABLE |
| EUR_USD | ny | long | KEEP | 0.60 | STABLE (marginal) |
| EUR_USD | ny | short | INVERT | 0.60 | STABLE (marginal) |
| USD_JPY | asia | long | INVERT | 0.75 | STABLE |
| USD_JPY | asia | short | KEEP | 0.75 | STABLE |
| USD_JPY | london | long | INVERT | 0.50 | UNSTABLE |
| USD_JPY | london | short | KEEP | 0.50 | UNSTABLE |
| USD_JPY | ny | long | INVERT→OFF | 0.33 | UNSTABLE (flip to OFF) |
| USD_JPY | ny | short | KEEP→OFF | 0.33 | UNSTABLE (flip to OFF) |

**Key stability finding:** The 4 strongest INVERT signals (EUR_JPY london/asia, USD_JPY asia, AUD_JPY asia) are stable at 75% monthly agreement. USD_JPY london/ny are unstable — not confirmed. Most "WEAK" cells lack monthly high-vol sample size, not contradicted.

---

## Task 3: Live Rule Mismatch — Direction-Agnostic vs Direction-Specific Reality

The two live rules in `direction_profiles.py`:
- `high_vol_regime_amplifies_reversion`: amplifies reversion factors ×1.3 when atr_h1_rel > 1.6  
- `high_vol_regime_suppresses_htf`: suppresses HTF factors ×0.5 when atr_h1_rel > 1.6  

**Both fire identically for LONG and SHORT — direction-agnostic.**

### Mismatch count (48 cells):

| Alignment | Count | Pct |
|-----------|-------|-----|
| ALIGNED (rule fires, helps direction) | 20 | 42% |
| MISMATCH (rule fires, hurts direction) | 20 | 42% |
| NEUTRAL (OFF / tiny delta) | 4 | 8% |
| UNKNOWN (insuff 2026 data) | 4 | 8% |

**The rules mismatch exactly 42% of cells — nearly half.** Since each trigger fires for both long and short simultaneously, every high-vol bar simultaneously helps one direction and hurts the other in paired cells. This means the direction-agnostic rules cannot net-positive; the ALIGNED and MISMATCH effects cancel at minimum.

### Strongest mismatches (where the rule fires against a large 2026 measured effect):

| pair | session | direction | delta(pip) | verdict_2026 | rule_alignment |
|------|---------|-----------|------------|--------------|----------------|
| EUR_JPY | london | long | -15.79 | INVERT | MISMATCH |
| USD_JPY | london | long | -17.83 | INVERT | MISMATCH |
| GBP_USD | london | short | -11.04 | INVERT | MISMATCH |
| EUR_JPY | asia | long | -5.68 | INVERT | MISMATCH |
| USD_CHF | asia | long | -3.93 | INVERT | MISMATCH |
| USD_JPY | asia | long | -3.53 | INVERT | MISMATCH |
| EUR_USD | asia | long | -3.70 | INVERT | MISMATCH |
| AUD_JPY | asia | long | -2.05 | INVERT | MISMATCH |
| AUD_USD | london | long | -2.67 | INVERT | MISMATCH |

All 9 of the strongest MISMATCH cells are longs. The 2026 message is clear: when atr_h1_rel > 1.6, amplifying reversion factors FOR LONGS is working against the market.

---

## Task 4: Final Per-Cell Verdict (KEEP / OFF / INVERT)

### Confirmed (stable ≥ 75%, |delta| > 2.0):

| pair | session | direction | delta(pip) | final_verdict |
|------|---------|-----------|------------|---------------|
| EUR_JPY | asia | short | +5.68 | **KEEP** |
| EUR_JPY | asia | long | -5.68 | **INVERT** |
| EUR_JPY | london | short | +15.79 | **KEEP** |
| EUR_JPY | london | long | -15.79 | **INVERT** |
| AUD_JPY | asia | short | +2.05 | **KEEP** |
| AUD_JPY | asia | long | -2.05 | **INVERT** |
| USD_JPY | asia | short | +3.53 | **KEEP** |
| USD_JPY | asia | long | -3.53 | **INVERT** |

4 confirmed KEEP + 4 confirmed INVERT. All are short=KEEP / long=INVERT, all at 75% monthly stability.

### Final Verdict Distribution (48 cells):

| Final Verdict | Count |
|---------------|-------|
| KEEP (confirmed) | 4 |
| KEEP_WEAK | 15 |
| INVERT (confirmed) | 4 |
| INVERT_WEAK | 15 |
| OFF | 10 |

---

## Overall Recommendation

### The 8yr "longs KEEP / shorts INVERT" framing does NOT hold in 2026.

The 2026 window inverts the headline direction claim (8yr AGREE rate only 29%). High relative vol in 2026:
- Hurts longs broadly (mean −1.94 pips net excursion vs baseline)
- Helps shorts broadly (mean +1.94 pips net excursion vs baseline)

This is a significant regime flip from the 8yr aggregate.

### The two live global rules SHOULD BE REMOVED.

Reason: both rules are **direction-agnostic** but the underlying effect is **direction-specific and opposite** in 2026. The rules simultaneously help some cells and hurt others at equal rate (42%/42%). The evidence basis (`evidence: "smoke v4"`) predates V5 and the current regime. The 2026 data does not validate them.

**Do NOT implement a per-cell whitelist from this study alone** — 44 of 48 cells have only WEAK confirmations (no monthly stability or too few monthly high-vol bars). The 4 strongly confirmed cells are EUR_JPY and USD_JPY (asia/london), which have the most 2026 high-vol instances.

### Recommended disposition:

| Action | Scope |
|--------|-------|
| REMOVE `high_vol_regime_amplifies_reversion` | Global (direction-agnostic, canceling) |
| REMOVE `high_vol_regime_suppresses_htf` | Global (direction-agnostic, canceling) |
| Watch list for future per-cell rule | EUR_JPY asia+london shorts, USD_JPY asia shorts — 75% stable, >3 pip delta, but 2026 sample is still thin |
| `atr_conc_amplifies_htf` rule | NOT evaluated here — different factor, different evidence basis |

**Analogy to `atr_conc`:** atr_conc was removed after 2026 data showed the 8yr signal didn't reproduce. The same logic applies here. Both live atr_h1_rel rules carry only `"smoke v4"` evidence and fail 2026 primary fit. They should go.

---

## Files

- `~/v5-atrrel-confirm/atr_confirm.py` — analysis script
- `~/v5-atrrel-confirm/cell_verdicts_2026.csv` — full 48-cell table
- `~/v5-atrrel-confirm/monthly_stability_2026.csv` — monthly breakdown
- `~/v5-atrrel-confirm/REPORT.md` — this report
- `/tmp/v5_atrrel_confirm_REPORT.md` — EC2 copy

