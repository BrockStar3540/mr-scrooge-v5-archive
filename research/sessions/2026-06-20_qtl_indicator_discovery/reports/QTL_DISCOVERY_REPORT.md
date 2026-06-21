# QuanTAlib indicator discovery — 44-trade V5 matrix

**Date:** 2026-06-20  
**Trades analyzed:** 44 V5 live trades 2026-06-18 → 2026-06-19 (52% baseline WR)  
**Indicators tested:** 31 across 7 gap categories (volume, dynamics, oscillators, channels, volatility, cycles, statistics)  
**Analysis script:** [analyses/v5_qtl_discovery.py](analyses/v5_qtl_discovery.py)  
**Per-trade feature matrix:** [data/discovery_features.csv](data/discovery_features.csv)

## Headline findings — TWO strong candidates emerge

| Indicator | Type | Effect | Max V5 corr |
|---|---|---|---|
| **`kurtosis_m5` (Shannon)** | Magnitude bucket | **HIGH bucket WR 72.7% vs LOW bucket 31.8% — Δ +41pp** | 0.58 |
| **`bbwp_m5` (BB Width Percentile)** | Magnitude bucket | **HIGH bucket WR 69.6% vs LOW bucket 33.3% — Δ +36pp** | 0.44 |

These two are unlike anything V5 currently measures, and the effect size is striking. **With 22 trades per bucket, the WR delta is far larger than the per-bucket noise floor.** Worth wiring in.

## Full results

### Signed-direction indicators (predict price direction at entry)

44 trades; baseline WR 52%; accuracy = % where indicator sign matched actual price direction.

| Indicator | Accuracy | Max V5 corr | Orth lift | Note |
|---|---:|---:|---:|---|
| **`adosc`** (Chaikin Oscillator) | **61.4%** | 0.632 | 0.084 | volume — best signed |
| **`efi`** (Elder's Force Index) | 59.1% | 0.598 | 0.073 | volume |
| **`ht_dcphase_m5`** (HT Dominant Cycle Phase) | 59.1% | 0.649 | 0.064 | cycle |
| `cmf` (Chaikin Money Flow) | 56.8% | 0.731 | 0.037 | volume — but corr high |
| `stochrsi_m5` | 54.5% | 0.642 | 0.033 | oscillator |
| `dc_lo_dist_pips` (Donchian-20 low dist) | 54.5% | 0.658 | 0.031 | channel |
| `ebsw_m5` (Even Better Sinewave) | 56.8% | 0.866 | 0.018 | cycle — high corr |
| `mfi` (Money Flow Index) | 56.8% | 0.904 | 0.013 | volume — high corr |
| `macd_hist_m5` | 52.3% | 0.724 | 0.013 | oscillator — at baseline |
| `fisher_m5` | 56.8% | 0.928 | 0.010 | oscillator — high corr |
| `vwap_dist_pips_m5` (96-bar) | 52.3% | 0.826 | 0.008 | VWAP — at baseline |
| `cci_m5` | 52.3% | 0.874 | 0.006 | — |
| `kc_up_dist_pips` (Keltner upper) | 52.3% | 0.890 | 0.005 | — |
| `tsi_m5` (True Strength) | 52.3% | 0.892 | 0.005 | — |
| ⚠ `vortex_diff_h1` | 40.9% | 0.966 | -0.006 | high corr, weak alone |
| ⚠ `aroonosc_h1` | 40.9% | 0.884 | -0.021 | reverse signal! |
| ⚠ `super_dist_h1` (SuperTrend dist) | 38.6% | 0.860 | -0.032 | reverse signal! |

**Interpretation:**
- **Volume oscillators take the top of the list.** This is significant: my memory had a rule "FX tick volume is unreliable for absolute comparisons". The data here says **oscillator/divergence forms of tick-volume DO carry signal** (adosc + efi at 59-61% accuracy). Recommend updating the rule.
- **`adosc` (Chaikin Oscillator) at 61.4%** is the standout. n=44 so confidence band is wide (~±14pp), but it's the best of the lot and only moderately correlated with V5 features.
- **`aroonosc_h1` and `super_dist_h1` at 38-41% accuracy = REVERSE signal.** Either V5 trades systematically fade these (which means they ARE signal, just inverted) or it's noise. Worth investigating with more trades.

### Magnitude indicators (regime detection — does HIGH bucket win more?)

For unsigned features, bucket at median; report WR difference.

| Indicator | WR high | WR low | Δ WR | Max V5 corr | Verdict |
|---|---:|---:|---:|---:|---|
| **`kurtosis_m5`** (100-bar) | **72.7% (16/22)** | **31.8% (7/22)** | **+40.9 pp** | 0.58 | 🟢 STRONG — wire in |
| **`bbwp_m5`** (BB Width Percentile) | **69.6% (16/23)** | **33.3% (7/21)** | **+36.2 pp** | 0.44 | 🟢 STRONG — wire in |
| `vhf_h1` (Vert-Horiz Filter) | 40.9% | 63.6% | -22.7 pp | 0.66 | 🟡 REVERSE — low VHF = better |
| `ht_dcperiod_m5` (cycle wavelength) | 63.6% | 40.9% | +22.7 pp | 0.37 | 🟡 longer cycles = better trades |
| `entropy_m5` (Shannon, 100-bar) | 40.9% | 63.6% | -22.7 pp | 0.67 | 🟡 LOW entropy (more structure) = better |
| `chop_h1` (Choppiness) | 59.1% | 45.5% | +13.6 pp | 0.68 | weak |
| `atrn_m5` (ATR normalized) | 59.1% | 45.5% | +13.6 pp | 0.60 | weak |
| `yzv_m5` (Yang-Zhang vol) | 59.1% | 45.5% | +13.6 pp | 0.59 | weak |
| `hurst_m5` | 59.1% | 45.5% | +13.6 pp | 0.42 | weak |

## What stands out — kurtosis + BBWP

`kurtosis_m5` (high kurtosis = fat-tailed recent returns = unusual moves persist) and `bbwp_m5` (high BB width percentile = vol regime high relative to recent baseline) **both effectively double the V5 win rate when in their HIGH bucket** (72-70% vs 32-33%). They're moderately correlated with V5 features (0.44-0.58) but distinct enough to add new information.

**The most defensible interpretation:** V5's entry pipeline currently doesn't distinguish "noisy normal vol" from "elevated structured vol". When recent price has been in an elevated/persistent regime (high kurtosis OR high BBWP), V5's entries are 2x more likely to win. When the regime is quiet/random, V5's entries lose more than they win.

This is a **playmaker filter candidate**: add `kurtosis_m5 > median(last_N)` or `bbwp_m5 > 50` as a soft gate; downweight tickets that fail.

## Sample-size caveats

- **n=44 is small.** WR differences of 20-40pp on n=22 per bucket have 95% confidence intervals of ~±20pp. The kurtosis + BBWP findings are robust to that uncertainty (40pp delta with 20pp band = still strongly positive), but the secondary findings (`vhf_h1`, `ht_dcperiod`, `entropy`) need more data to settle.
- **Selection bias.** V5 only took these 44 trades because they passed V5's existing gates. We're measuring "given V5 picked it, what new info improves it" — NOT "what's universally predictive of FX direction". Both kurtosis and BBWP findings should re-confirm in a larger live sample (~200+ trades) before becoming hard gates.
- **All-NaN indicators** (when first run) were due to QuanTAlib's OHLCV-normalized signature; fixed and re-run. No silent drops.

## What QuanTAlib's library actually changed in our priors

Before this sweep, my memory had:
- "FX volume is tick-volume, unreliable" → **partially wrong**: oscillator forms (adosc, efi) DO carry signal at 59-61% accuracy
- V5 has no trend-strength filter → ADX-14 H1 was actually already in matrix; this sweep confirmed ADX alone isn't the missing piece (`chop_h1` only Δ+14pp)
- V5 has no cycle measure → `ht_dcphase` 59% acc + `ht_dcperiod` +23pp bucket Δ suggest cycle position matters; not as strong as kurtosis/BBWP but worth tracking
- V5 has no distribution-shape measure → **kurtosis_m5 was the single strongest finding of the entire sweep**

## Recommended next steps

1. **Wire `kurtosis_m5` + `bbwp_m5` into the discovery engine's nightly corpus on the Mini.** Both compute in microseconds via qtl; the daily cron will accumulate live per-trade evidence over the next 30+ days. If the Δ+40pp / Δ+36pp effect holds at n=100+, promote to direction_v2/momentum_v3 profile gates.
2. **Cross-check `adosc` (Chaikin Osc) over 100+ trades** — best signed candidate but n=44 confidence band is wide.
3. **Investigate `aroonosc_h1` and `super_dist_h1` REVERSE signals** — if V5 systematically fades these correctly, they ARE signal (just inverted). Worth understanding why.
4. **Update memory:** "FX tick volume is unreliable for absolute comparisons but oscillator forms (Chaikin, EFI) DO carry signal."

## Open items NOT addressed in this session

- Per-direction accuracy split (long vs short subsets had ~22 trades each, too small)
- Per-session split (asia/london/ny each ~15 trades)
- Combinatorial features (e.g., kurtosis × BBWP — both HIGH together)
- Live-bake-in of kurtosis/BBWP as soft playmaker gates with shadow logging
