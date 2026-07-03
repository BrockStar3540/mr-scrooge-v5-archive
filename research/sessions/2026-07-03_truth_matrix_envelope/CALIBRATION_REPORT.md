# V5 Per-Cell Calibration Report
**Generated:** 2026-07-03  
**Artifact:** `~/v5-cell-calibration/cell_calibration_2026-07.json`  
**Fit window:** 2026-01-01 – 2026-07-03 (Jan–Jul inclusive; July drift label excluded — 2-day sample)  
**Lineage:** truth-matrix-2026-07-03-anchored  
**Script:** `~/v5-cell-calibration/gen_calibration.py`

---

## What Was Built

One JSON artifact keyed `"PAIR/session/direction"` for all 48 V5 cells.  
Each cell contains 4 calibration blocks + metadata:

1. **distance_calibration** — MFE-60 quantiles (p25/p50/p75/p90 pips, bars where MFE>0) + MFE-240 p50 for runner context + ATR regression (`slope`, `intercept`) so live code can do `projected_mfe = clip(slope×atr_1h + intercept, p25, p90)`.

2. **adverse_calibration** — Winner-conditioned MAE (bars where MFE-60 ≥ 10p): p50/p75/p90 of |MAE|. Anchor bias note: MAE understated ~+2.7p (anchor-validation finding 2026-07-03) — **documented, NOT baked in**, so downstream callers can choose conservative or nominal.

3. **dead_entry** — `base_rate_dead` = P(MFE-60 < 5p) for that cell. Up to 2 dead-entry separator features (PERSISTENT or REGIME drift only; FLICKER excluded). Each separator includes: feature name, dead_auc, drift label, median-split threshold, `live_feed_range` (actual 2026-session min/max — dimension-check anchor), P(dead | above threshold), P(dead | below threshold).

4. **direction_lean** — Top PERSISTENT-only direction-sync feature if `|corr| ≥ 0.06` on 2026 bars. Includes: feature, sign, corr, auc, drift, live_feed_range. Null if no qualifying feature.

5. **metadata** — `n_2026_bars`, `months_fit`, `drift_flags`, `killed_pair`, `killed_note` (USD_CHF), `lineage`.

---

## Validation Results

### A. Sanity Print — 5 Diverse Cells

| Cell | MFE-60 p25/p50/p90 | Dead Rate | Direction Lean | Killed |
|------|--------------------|-----------|---------------|--------|
| AUD_JPY/asia/long | 3.3 / 6.8 / 19.5p | 0.389 | ema5 neg corr=-0.084 | No |
| USD_JPY/ny/short | 2.5 / 5.8 / 22.2p | 0.457 | null | No |
| USD_CHF/london/short | 2.3 / 5.0 / 14.0p | **0.514** | pdh pos | **YES (killed)** |
| GBP_USD/ny/short | 3.2 / 6.6 / 21.5p | 0.398 | null | No |
| EUR_USD/london/long | 2.8 / 5.9 / 16.8p | 0.450 | null | No |

**JPY plausibility check:** AUD/JPY p50=6.8p, p90=19.5p — sane for pip-scale (non-JPY GBP p50=6.6p, p90=21.5p — comparable, as expected since parquet already in pips). USD/JPY p90=22.2p — consistent with JPY pair vol.

**USD_CHF:** dead rate 0.514 (worst quintile), correctly flagged `killed_pair=True`.

### B. Broker Cross-Check — GBP_USD/ny/short

- Artifact band: p25=3.2p, p50=6.6p, p90=21.5p  
- Broker GBP_USD SHORT trades: n=19, winners (MFE-60≥10p): n=6  
- Broker winner MFEs: [11.4, 11.5, 13.5, 13.7, 13.7, 13.8]  
- Broker winner median: 13.6p → sits inside artifact band at ~p75 (artifact p75=12.6p) — slightly above median, plausible since broker winners are a selected population  
- **Winners inside band [3.2–21.5]: 6/6 (100%) → PASS**  
- Caveat: n=6 broker winners is small; cross-check is directional, not statistically definitive.

### C. Dimension Check — live_feed_range vs expected scales

4 feature-cell combinations audited against expected scale rules:
- `atr_conc` range [0.08, 1.06] → dimensionless ratio, confirmed in [0, 2] — **OK**
- `atr_1h` in pips (GBP NY: [9.3, 45.7]) — **OK**
- No out-of-scale features found.
- **Result: PASS — no atr_conc-bug-class dimension violations detected.**

---

## Distribution Summary

| Metric | Value |
|--------|-------|
| Total cells | 48 |
| USD_CHF cells (killed, flagged) | 6 |
| Cells with direction lean | 28 / 48 (58%) |
| Cells with dead-entry separators | 37 / 48 (77%) |
| Dead rate > 50% | 23 cells |
| Dead rate 35–50% | 22 cells |
| Dead rate < 35% | 3 cells |
| Dead rate range | 0.320 – 0.742 |
| Dead rate median | 0.481 |

**Highest dead-rate cells (worst entries):**
1. USD_CHF/asia/short: 0.742 (killed)
2. USD_CHF/asia/long: 0.726 (killed)
3. USD_CAD/asia/short: 0.708
4. USD_CAD/asia/long: 0.685
5. EUR_USD/asia/long: 0.673

**Lowest dead-rate cells (best entry quality):**
1. EUR_JPY/london/long: 0.320
2. EUR_JPY/london/short: 0.327
3. GBP_USD/london/long: 0.337
4. GBP_USD/london/short: 0.356
5. AUD_JPY/london/long: 0.373

**28 cells with direction lean** (all symmetric: each pair/session has LONG+SHORT both tagged or neither). Notable strong leans:
- AUD_USD/london: `q_vwap_dist_pips_m5` corr=±0.118 — strongest
- USD_JPY/london: `atr_h1_relative` corr=±0.126
- EUR_USD/ny: `q_stochrsi_m5` corr=±0.094

---

## Key Design Notes

- **MAE sign convention:** parquet `mae_*_60` columns are negative; artifact stores them as **positive** via `abs()`. Field `mae_sign_convention` documents this in each cell.
- **Anchor bias:** +2.7p documented in `anchor_bias_note` field; NOT baked in. Live wiring should decide whether to add it to stop thresholds.
- **Dead separators threshold basis:** median of that cell's 2026-session bars. The `live_feed_range` field gives the actual data range for dimension checking when wiring.
- **No FLICKER features:** direction lean and dead separators both exclude FLICKER-drift features per house rules.
- **USD_CHF included but flagged:** 6 cells present with `killed_pair=True` and `killed_note`. They are calibration-only validation data.
- **July 2026 in fit window for quantiles/regression** (2 days of live bars), but excluded from drift labels per house rules.

---

## Files

```
~/v5-cell-calibration/
  cell_calibration_2026-07.json   ← primary artifact (48 cells)
  gen_calibration.py              ← generator script
  validate_calibration.py         ← validation script
  CALIBRATION_REPORT.md           ← this report
```

EC2 copies in `/tmp/` for review.

---

*No live bot changes made. Data-only task.*
