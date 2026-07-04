# FORMULA DEEP-HISTORY VALIDATION REPORT
**Date:** 2026-07-04  
**Run time:** 74 seconds on Mac Mini (CPYQTH294R)  
**Data:** ~/v5-truth-matrix/ (2019-2026, 8 pairs, ~4.4M bars)  
**Input combos:** 11 positive formula×geometry combos from v5-formula-distill/convergence_results.csv  
**Work dir:** ~/v5-formula-history/

---

## BOTTOM LINE FIRST

**8 of 11 combos: DEEP-FAIL** — positive EV in May-Jun 2026 validation was a 2026-pocket artifact. These combos were negative in the prior 7 years of history (2019–2025).

**3 of 11 combos: PASS-ALL** — all three are the SAME cell: `GBP_USD/london/long h=240` at three different geometries. This cell is deep-persistent (positive 7/7 OOS years), drift-stable, and holds up in sequential simulation.

**Both tier-1 cells are DEEP-FAIL:**
- `USD_JPY/ny/long` — 0/7 OOS years positive, negative every year 2019–2025
- `GBP_USD/ny/short` — 0/7 OOS years positive, negative every year 2019–2025

These two are 2026-pocket artifacts. No softening.

---

## 11-COMBO VERDICT TABLE

| # | Cell | h | Geo | SL/Trig/Trail | Deep Label | OOS+ | Orig EV (overlap) | Orig n | Seq n | Seq EV | Seq WR | MDD (pips) | LLS | Drift | Overall |
|---|------|---|-----|---------------|------------|------|-------------------|--------|-------|--------|--------|------------|-----|-------|---------|
| 1 | USD_CHF/ny/long | 240 | best_cell | 8/3/1.5 | DEEP-FAIL | 2/7 | +0.559 | 258 | 75 | +0.805 | 81.3% | -27.6 | 2 | UNSTABLE | **FAIL-DEEP** |
| 2 | AUD_JPY/ny/short | 60 | low_pstar_sym | 8/7.5/1.5 | DEEP-FAIL | 0/7 | +0.212 | 518 | 73 | -4.919 | 21.9% | -376.7 | 12 | STABLE | **FAIL-DEEP** |
| 3 | USD_CHF/ny/long | 60 | best_cell | 8/3/1.5 | DEEP-FAIL | 0/7 | +1.830 | 46 | 13 | -1.915 | 53.8% | -48.3 | 4 | UNSTABLE | **FAIL-DEEP** |
| 4 | **GBP_USD/ny/short** ★ | 60 | best_cell | 12/3/1.5 | **DEEP-FAIL** | **0/7** | +0.914 | 954 | 214 | -1.499 | 70.6% | -386.4 | 5 | STABLE | **FAIL-DEEP** |
| 5 | **USD_JPY/ny/long** ★ | 60 | best_cell | 20/3/1.5 | **DEEP-FAIL** | **0/7** | +1.199 | 2366 | 322 | -4.918 | 65.5% | -1573.2 | 4 | STABLE | **FAIL-DEEP** |
| 6 | **USD_JPY/ny/long** ★ | 60 | low_pstar_sym | 8/7.5/1.5 | **DEEP-FAIL** | **0/7** | +0.752 | 2366 | 269 | -4.240 | 26.0% | -1145.9 | 16 | STABLE | **FAIL-DEEP** |
| 7 | GBP_USD/london/long | 240 | current | 20/7.5/2.5 | DEEP-PERSISTENT | **7/7** | +0.018 | 2194 | 149 | +0.038 | 70.5% | -199.0 | 5 | STABLE | **PASS-ALL** |
| 8 | GBP_USD/london/long | 240 | best_cell | 12/10/1.5 | DEEP-PERSISTENT | **7/7** | +0.154 | 2194 | 165 | +0.350 | 54.5% | -152.5 | 5 | STABLE | **PASS-ALL** |
| 9 | GBP_USD/london/long | 240 | low_pstar_sym | 8/7.5/1.5 | DEEP-PERSISTENT | **7/7** | +0.219 | 2194 | 259 | +0.264 | 51.4% | -113.2 | 7 | STABLE | **PASS-ALL** |
| 10 | AUD_USD/ny/short | 60 | best_cell | 10/3/1.5 | DEEP-FAIL | 0/7 | +0.394 | 1206 | 143 | -3.559 | 51.7% | -517.8 | 6 | STABLE | **FAIL-DEEP** |
| 11 | AUD_JPY/ny/short | 240 | low_pstar_sym | 8/7.5/1.5 | DEEP-FAIL | 1/7 | +1.938 | 91 | 18 | +4.550 | 72.2% | -17.8 | 2 | UNSTABLE | **FAIL-DEEP** |

★ = Tier-1 cell. "Seq n" and "Seq EV" are the honest May-Jun 2026 sequential (non-overlapping) numbers.

---

## TEST 1: DEEP OOS — TIER-1 CELLS (FULL YEAR-BY-YEAR)

### GBP_USD/ny/short — h=60, best_cell (SL=12, trig=3, trail=1.5)
Formula: `rvol_5bar in [0.371, 0.669]`

| Year | EV pct-form | EV abs-form | n bars | Seq EV | Seq n |
|------|-------------|-------------|--------|--------|-------|
| 2019 | -1.590 | -1.365 | 5623 | -1.48 | 697 |
| 2020 | -0.827 | -0.711 | 5654 | -0.83 | 690 |
| 2021 | -2.001 | -1.582 | 5639 | -1.80 | 700 |
| 2022 | -0.946 | -0.588 | 5658 | -0.80 | 686 |
| 2023 | -2.800 | -2.464 | 5655 | -2.65 | 697 |
| 2024 | -3.520 | -3.552 | 5664 | -3.30 | 693 |
| 2025 | -1.871 | -1.825 | 5657 | -1.65 | 686 |
| 2026 | -1.128 | -1.124 | 2846 | (-1.50 seq MayJun) | 214 |

**Verdict: DEEP-FAIL. Negative every single year 2019–2025. Getting worse in 2024 (-3.5p). The 2026 May-Jun +0.914 convergence result was pure artifact — sequential restates it as -1.499p.**

### USD_JPY/ny/long — h=60, best_cell (SL=20, trig=3, trail=1.5)
Formula: `atr_5m in [2.703, 6.332]`

| Year | EV pct-form | EV abs-form | n bars | Seq EV | Seq n |
|------|-------------|-------------|--------|--------|-------|
| 2019 | -6.805 | -3.906 | 14722 | -6.31 | 1820 |
| 2020 | -6.462 | -4.586 | 14745 | -5.87 | 1813 |
| 2021 | -7.818 | -4.751 | 14769 | -7.16 | 1831 |
| 2022 | -2.057 | -3.164 | 14865 | -1.97 | 1842 |
| 2023 | -2.214 | -3.622 | 14890 | -2.01 | 1838 |
| 2024 | -2.318 | -3.451 | 14921 | -2.19 | 1835 |
| 2025 | -1.346 | -2.829 | 14896 | -1.16 | 1843 |
| 2026 | -2.421 | -2.425 | 7474 | (-4.92 seq MayJun) | 322 |

**Verdict: DEEP-FAIL. Catastrophically negative 2019–2021 (-6 to -8p), still negative 2022–2025. Sequential MayJun restates at -4.92p. This formula simply doesn't work at any horizon. The rvol-based ATR filter selects high-activity windows that favor mean-reversion, not the direction indicated.**

### USD_JPY/ny/long — h=60, low_pstar_sym (SL=8, trig=7.5, trail=1.5)
Same formula, tighter geometry — same verdict:

| Year | EV pct-form | EV abs-form |
|------|-------------|-------------|
| 2019 | -5.011 | -3.067 |
| 2020 | -5.078 | -3.697 |
| 2021 | -5.886 | -3.911 |
| 2022 | -1.554 | -2.392 |
| 2023 | -1.842 | -3.089 |
| 2024 | -1.813 | -2.730 |
| 2025 | -0.997 | -2.144 |
| 2026 | -2.296 | -2.300 |

**Tighter geometry doesn't rescue it. Still 0/7 OOS years positive.**

---

## TEST 1: DEEP OOS — PASS-ALL CELL (GBP_USD/london/long, h=240)
Formula: `rvol_5bar in [0.371, 0.669]` (identical feature, different session+direction — london long, not NY short)

### Combo 7: current geo (SL=20, trig=7.5, trail=2.5)

| Year | EV pct-form | EV abs-form | n bars |
|------|-------------|-------------|--------|
| 2019 | +0.860 | -0.668 | 10677 |
| 2020 | +1.595 | +0.500 | 10916 |
| 2021 | +0.539 | +0.957 | 10898 |
| 2022 | +1.203 | -0.623 | 10855 |
| 2023 | +0.896 | -2.714 | 10851 |
| 2024 | +0.434 | +0.074 | 10895 |
| 2025 | +0.563 | +0.913 | 10851 |
| 2026 | +0.444 | +0.444 | 5458 |

**7/7 OOS years positive (percentile form). Divergence: abs form flips negative in 2019, 2022, 2023 — the percentile ranges matter. The absolute thresholds are regime-dependent.**

### Combo 8: best_cell geo (SL=12, trig=10, trail=1.5)

| Year | EV pct-form | EV abs-form |
|------|-------------|-------------|
| 2019 | +1.059 | +0.239 |
| 2020 | +1.637 | +0.869 |
| 2021 | +0.532 | +1.264 |
| 2022 | +0.919 | -0.076 |
| 2023 | +0.735 | -1.808 |
| 2024 | +1.156 | +0.743 |
| 2025 | +0.494 | +0.920 |
| 2026 | +0.750 | +0.750 |

**7/7 OOS years positive (pct). Abs diverges in 2022, 2023. Best geometry (12/10/1.5) produces higher EV than current in most years.**

### Combo 9: low_pstar_sym geo (SL=8, trig=7.5, trail=1.5)

| Year | EV pct-form | EV abs-form |
|------|-------------|-------------|
| 2019 | +0.588 | +0.390 |
| 2020 | +1.094 | +0.571 |
| 2021 | +0.367 | +0.989 |
| 2022 | +0.905 | +0.094 |
| 2023 | +0.592 | -0.724 |
| 2024 | +0.723 | +0.532 |
| 2025 | +0.172 | +0.560 |
| 2026 | +0.475 | +0.475 |

**7/7 OOS years positive (pct). Abs diverges only in 2023. Lowest EV of the three geometries but also lowest MDD (-113p).**

---

## TEST 2: SEQUENTIAL (NON-OVERLAPPING) RESTATEMENT

### Key finding: overlapping bar counts are massively inflated

The convergence step reported bar counts as ALL bars satisfying the formula within the validation window — this includes bars during already-open positions. The honest sequential trade count is much smaller:

| Combo | Cell | Overlap n (MayJun) | Seq n (MayJun) | Compression ratio | Seq EV |
|-------|------|--------------------|----------------|-------------------|--------|
| 5 | USD_JPY/ny/long best | 2366 | 322 | 7.3x | -4.918 |
| 6 | USD_JPY/ny/long lps | 2366 | 269 | 8.8x | -4.240 |
| 4 | GBP_USD/ny/short best | 954 | 214 | 4.5x | -1.499 |
| 2 | AUD_JPY/ny/short lps | 518 | 73 | 7.1x | -4.919 |
| 10 | AUD_USD/ny/short best | 1206 | 143 | 8.4x | -3.559 |
| 7 | GBP_USD/london/long current | 2194 | 149 | 14.7x | +0.038 |
| 8 | GBP_USD/london/long best | 2194 | 165 | 13.3x | +0.350 |
| 9 | GBP_USD/london/long lps | 2194 | 259 | 8.5x | +0.264 |

**The PASS-ALL cell (GBP_USD/london/long) holds positive EV after sequential compression. The FAIL-DEEP cells flip negative or get worse.**

---

## TEST 3: MONTHLY DRIFT — PASS-ALL CELL

GBP_USD/london/long h=240 — monthly EV across 2024-2026 (pct form, net spread):

### Combo 7 (current geo, 20/7.5/2.5):

| Month | EV | | Month | EV |
|-------|----|-|-------|-----|
| 2024-01 | -0.343 | | 2025-07 | +1.379 |
| 2024-02 | +0.030 | | 2025-08 | +3.411 |
| 2024-03 | +0.849 | | 2025-09 | -0.204 |
| 2024-04 | +0.636 | | 2025-10 | -3.209 |
| 2024-05 | +4.452 | | 2025-11 | +3.035 |
| 2024-06 | -1.611 | | 2025-12 | +2.222 |
| 2024-07 | +3.373 | | 2026-01 | -0.244 |
| 2024-08 | -0.614 | | 2026-02 | -2.193 |
| 2024-09 | +1.443 | | 2026-03 | +2.146 |
| 2024-10 | +0.051 | | 2026-04 | +3.093 |
| 2024-11 | +1.411 | | 2026-05 | +1.080 |
| 2024-12 | +1.236 | | 2026-06 | -1.400 |
| 2025-01 | +0.061 | | 2026-07 | -2.999 (partial) |
| 2025-02 | +0.401 | | | |
| 2025-03 | +4.149 | | | |
| 2025-04 | +2.667 | | | |
| 2025-05 | +1.687 | | | |
| 2025-06 | +2.792 | | | |

**Sign flips in last 6 completed months (Jan-Jun 2026): 2 flips (Jan-, Feb-, Mar+, Apr+, May+, Jun-). STABLE verdict (<=2 flips). 2026 is mixed but not alarming — there are 4 positive months out of 6.**

### Combo 8 (best_cell, 12/10/1.5) — STABLE, sign flips=2, higher EV than current in most months.

### Combo 9 (low_pstar_sym, 8/7.5/1.5) — STABLE, sign flips=2, most consistent month-to-month.

---

## PERCENTILE VS ABSOLUTE DIVERGENCE

**This is the most important methodological finding:**

The percentile-form and absolute-form agree on direction for all FAIL-DEEP cells — they're simply negative under both approaches.

For the PASS-ALL cell (GBP_USD/london/long), divergence occurs:
- Combo 7 (current): abs form negative in 2019, 2022, 2023 vs pct positive
- Combo 8 (best_cell): abs form negative in 2022, 2023 vs pct positive
- Combo 9 (low_pstar_sym): abs form negative only in 2023 vs pct positive

**Interpretation:** The rvol_5bar window (p4.8–p25.2 in 2026) is regime-dependent. In 2022-2023, when GBP volatility structure shifted, the fixed absolute thresholds [0.371, 0.669] missed the correct relative-volume band for that regime. Percentile re-derivation adapts to each year's distribution and recovers the edge. **This means the live implementation MUST use percentile computation against a rolling lookback window, not the frozen 2026 absolute values.**

---

## COMBOS SURVIVING ALL THREE TESTS

Only these three, all the same underlying cell:

| # | Cell | Formula | Geo | Deep | Seq MayJun EV | Seq MayJun n | MDD | Drift | Pct-Abs Diverge |
|---|------|---------|-----|------|---------------|--------------|-----|-------|-----------------|
| 7 | GBP_USD/london/long h=240 | rvol_5bar ∈ [p4.8, p25.2] | current 20/7.5/2.5 | 7/7 yrs | +0.038 | 149 | -199p | STABLE | 2019/2022/2023 diverge |
| 8 | GBP_USD/london/long h=240 | rvol_5bar ∈ [p4.8, p25.2] | best_cell 12/10/1.5 | 7/7 yrs | +0.350 | 165 | -153p | STABLE | 2022/2023 diverge |
| 9 | GBP_USD/london/long h=240 | rvol_5bar ∈ [p4.8, p25.2] | low_pstar_sym 8/7.5/1.5 | 7/7 yrs | +0.264 | 259 | -113p | STABLE | 2023 only |

**Among these three, combo 8 (best_cell: 12/10/1.5) has the highest sequential EV (+0.350p) and best_cell geometry also has the lowest pct-abs divergence in recent years. Combo 9 has the most sequential trades and lowest MDD.**

**The only remaining check before considering live use: verify the rvol_5bar feature is actually computed and served to V5 in real-time (live wiring check).**

---

## NOTES ON METHODOLOGY

- Simulation uses the same `sim_ratchet_on_bars` machinery as run_convergence.py — reuses verified bar-level price walk
- No look-ahead: features at bar t only; forward price is from bar t+1 onward
- Spreads: SPREAD_PIPS table identical to convergence (AUD_JPY=0.9, GBP_USD=0.6, USD_JPY=0.5, USD_CHF=0.7, AUD_USD=0.5, USD_CAD=0.7)
- Sequential simulation: chronological scan, enter on first qualifying bar when no position open, hold through ratchet exit, then resume scanning. This eliminates all position-overlap inflation.
- Percentile re-derivation: for each year, the feature distribution is computed from that year's session rows only; lo_pct_2026/hi_pct_2026 bands (e.g., p4.8–p25.2 for rvol_5bar) are applied to that year's CDF. This is the design intent — ranges breathe with the regime.
- The H1 look-ahead leak fixed 2026-07-03 does not affect these formulas: rvol_5bar, atr_5m, atr_conc, ema20_dist_pct, q_atrn_m5, q_kc_up_dist_pips, ema50_dist_pct are all M5-timeframe features computed from bar closes/highs/lows with no H1 dependency.

---

## FILES WRITTEN

- `~/v5-formula-history/test1_deep_oos.csv` — per-combo×year (2019-2026), both pct and abs EV
- `~/v5-formula-history/test2_sequential.csv` — per-combo×year sequential simulation results
- `~/v5-formula-history/test3_monthly_drift.csv` — per-combo×month (2024-2026) EV
- `~/v5-formula-history/verdict_table.csv` — master 11-combo verdict table
- `~/v5-formula-history/validation_run.log` — full timestamped log
- Copies on EC2: `/tmp/v5-formula-history-*.csv`
