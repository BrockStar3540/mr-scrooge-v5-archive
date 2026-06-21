# QuanTAlib candidates for V5 ML discovery / feature expansion

**Date:** 2026-06-20  
**Source:** [QuanTAlib v0.8.9 indicator index](https://github.com/mihakralj/QuanTAlib/blob/main/lib/_index.md) (411 indicators across 16 categories)  
**Scope:** Forex M5 short-term scalping. V5 currently has ~24 direction features + ~10 momentum/vol features. This list curates **53 candidates** the ML discovery engine could mine, organized by use-case and priority. Each entry = one-line rationale on what it adds beyond V5's current feature set.

**Validation status:** EMA, BB-mid, SMA-20 confirmed bit-exact vs V5 hand-codes; Wilder ATR + RSI bit-exact at the last-bar values V5 actually reads. See `V5_QTL_VALIDATION_REPORT.md`.

## Priority tiers
- **HIGH** — should immediately enter the discovery corpus; high probability of finding edge
- **MED** — worth testing once HIGH is processed; less obvious payoff
- **LOW** — interesting / specialized; only test if specific hypothesis arises

---

## 1. Advanced moving averages (replace / augment EMA, KAMA-style)

V5 uses plain EMA (span 5/20/50). Most of these are designed to have lower lag, lower noise, or both.

| Indicator | Why for V5 | Priority |
|---|---|---|
| **HMA** Hull MA | Industry-standard low-lag MA; ~1/2 the lag of EMA at same span; popular in scalping | HIGH |
| **ALMA** Arnaud Legoux | Gaussian-weighted; smoother than SMA, less lag than EMA | HIGH |
| **KAMA** Kaufman Adaptive | Auto-adjusts speed by noise (Efficiency Ratio); ideal for the regime-shifting FX market | HIGH |
| **JMA** Jurik MA | Premium MA, very low lag + very low noise; commonly cited as "best in class" | HIGH |
| **T3** Tillson | Smooth + responsive; popular alternative to EMA for noisy intraday | MED |
| **FRAMA** Fractal Adaptive | Adjusts span by Hurst-style fractal dim; faster in trending, slower in chop | MED |
| **VIDYA** Variable Index Dynamic | Adapts to CMO; similar adaptive logic to KAMA | MED |
| **ZLEMA / ZLDEMA / ZLTEMA** | Zero-lag variants — explicit lag-compensation | MED |
| **TEMA / DEMA** | Triple/Double exponential — less lag than single EMA | LOW |
| **TRIMA** Triangular MA | Smooths the smooth; very low noise, more lag | LOW |
| **MAMA** MESA Adaptive MA | Ehlers cycle-aware adaptive MA | LOW |

**Use idea:** swap V5's `ema20_1h_dist` calc to HMA-20 or KAMA-20 and compare WR per cell on the smoke nightly. If improvement → permanent replacement.

---

## 2. Alternative momentum oscillators (beyond RSI)

V5 uses RSI-14 + slope + Z-score-1h. These add finer-grained or differently-smoothed signals.

| Indicator | Why for V5 | Priority |
|---|---|---|
| **CRSI** Connors RSI | RSI + streak + ROC combo; sharper MR signals than plain RSI; favored by short-term traders | HIGH |
| **LRSI** Ehlers Laguerre RSI | Lower-noise RSI; less choppy than Wilder RSI in M5 | HIGH |
| **STOCHRSI** | Stoch applied to RSI; more sensitive OB/OS than either alone | HIGH |
| **TSI** True Strength Index | Double-smoothed momentum; cleaner signal than ROC | HIGH |
| **FISHER** Fisher Transform | Normalizes prices to Gaussian, exaggerates extremes; sharpens reversal detection | HIGH |
| **CCI** Commodity Channel Index | Classic 20-bar momentum vs typical price; well-understood; orthogonal to RSI | MED |
| **DPO** Detrended Price Oscillator | Removes trend, exposes cycle/mean-reversion; useful for asia/range cells | MED |
| **TRIX** Triple Exp Avg | Triple-smoothed ROC; very clean direction | MED |
| **WILLR** Williams %R | Different denominator than Stoch; OB/OS | MED |
| **ER** Efficiency Ratio | Direct trend/noise ratio (0-1); could replace `htf_align_signed`-style filters | MED |
| **CMO** Chande Momentum | RSI variant, less smoothing; faster MR | LOW |
| **RSX** | Smoothed RSI by Jurik | LOW |

---

## 3. Volatility (regime detection, vol filtering)

V5 uses raw `atr_5m`, `atr_1h`, and the new `atr_h1_relative`. These are better volatility estimators or different ways to measure regime.

| Indicator | Why for V5 | Priority |
|---|---|---|
| **ATRN / NATR** ATR Normalized | ATR as % of price; cleaner cross-pair regime signal (JPY ATR is different scale than EUR) | HIGH |
| **BBWP** BB Width Percentile | Vol percentile rank over rolling window; squeeze detection | HIGH |
| **YZV** Yang-Zhang Volatility | Superior OHLC-based vol estimator (uses overnight + intraday); much less bias than close-to-close | HIGH |
| **GKV** Garman-Klass Volatility | OHLC-based; better than close-to-close in non-stationary markets | HIGH |
| **JVOLTY** Jurik Volatility | Smoothed vol; lower noise than ATR | MED |
| **UI** Ulcer Index | Drawdown-aware vol; weights downside more heavily | MED |
| **CCV** Close-to-Close Vol | Different smoothing of vol vs ATR; orthogonal | MED |
| **RSV** Rogers-Satchell | OHLC-based; drift-independent | MED |
| **VR** Volatility Ratio | Short vol vs long vol; similar to atr_h1_relative | LOW |
| **MASSI** Mass Index | Vol-based reversal signal; specific to range-breakout patterns | LOW |

---

## 4. Trend strength / directional dynamics

V5 has nothing explicitly measuring "is this a trending market vs a chop market". This is a known gap (Brock's choppiness vs trend feature has been on the future-experiments list).

| Indicator | Why for V5 | Priority |
|---|---|---|
| **ADX** Average Directional Index | Classic trend-strength filter; ADX>25 = trending; orthogonal to V5's direction module | HIGH |
| **CHOP** Choppiness Index | Opposite of ADX; high = sideways. Could gate the `continuation_strong` profile | HIGH |
| **AROON / AROONOSC** | Bars-since-high vs bars-since-low; clean directional regime | HIGH |
| **VHF** Vertical Horizontal Filter | Trend vs range detector; different math from ADX | HIGH |
| **SUPER** SuperTrend | ATR-based trend follower with explicit flip; popular in algo systems | HIGH |
| **PFE** Polarized Fractal Efficiency | Trend efficiency by fractal path length; novel signal | MED |
| **VORTEX** Vortex Indicator | Directional movement via TR comparisons; correlates with ADX but different | MED |
| **ICHIMOKU** | 5-component cloud; specifically the cloud color / thickness as a regime signal | MED |
| **DMX** Jurik DMI | Smoother DI+/DI- | MED |
| **DX / ADXR** | DMI variants | LOW |
| **RAVI** Chande RAVI | Range action verification; similar to CHOP | LOW |

---

## 5. Statistical / regime indicators (orthogonal to TA)

These measure properties of the price *distribution* rather than the price itself.

| Indicator | Why for V5 | Priority |
|---|---|---|
| **HURST** Hurst Exponent | >0.5 = trending, <0.5 = mean-reverting; foundational regime measure | HIGH |
| **ENTROPY** Shannon Entropy | Information content of returns; high = noise, low = structure; could filter low-info bars | HIGH |
| **KURTOSIS** | Tail-heaviness; high kurtosis = fat tails → asymmetric risk | HIGH |
| **SKEW** | Distribution asymmetry; bias toward up- or down-moves | HIGH |
| **ZSCORE** | Standardized price; V5 already uses but qtl version may differ in window/scale | MED |
| **LINREG** Linear Regression | Slope + R² of last N bars; slope = trend direction, R² = trend reliability | MED |
| **ADF** Augmented Dickey-Fuller | Stationarity test; stationary series = mean-revertable | MED |
| **CORREL / SPEARMAN** | Cross-pair correlation; useful for risk-on/risk-off regime | LOW |
| **COINTEGRATION** | Pair-trading basis; only useful if V5 ever takes basket trades | LOW |

---

## 6. Cycle / phase indicators (Ehlers stack)

V5 doesn't measure cycle position at all. Asia/JPY cells especially are regime-cyclic and these could materially help.

| Indicator | Why for V5 | Priority |
|---|---|---|
| **HT_DCPERIOD** | Dominant cycle period of recent price; tells you current cycle wavelength | HIGH |
| **HT_DCPHASE** | Current phase in the dominant cycle (0-360°); mean-revert timing | HIGH |
| **EBSW** Even Better Sinewave | Ehlers' clean sine-wave indicator; OB/OS at cycle turns | HIGH |
| **HT_SINE** | Hilbert SineWave; reversal-timing signal at sine crossings | MED |
| **CCYC** Cyber Cycle | Smoothed cycle component; tradeable as MR | MED |
| **DSP / SSFDSP** | Detrended Synthetic Price; isolates cycle from trend | LOW |
| **HOMOD** Homodyne Discriminator | Alternative dominant-cycle calculator | LOW |

---

## 7. Filters (noise reduction for ML features)

These produce a smoother price/volume series; useful as inputs to other indicators or directly as features.

| Indicator | Why for V5 | Priority |
|---|---|---|
| **KALMAN** | Optimal recursive filter; widely used in quant; lower lag than EMA at same noise reduction | HIGH |
| **GAUSS** Gaussian Filter | Phase-preserving smoother | MED |
| **USF / SSF2** Ehlers Smoothers | Designed for trading; minimal lag, strong noise rejection | MED |
| **BUTTER2 / BUTTER3** Butterworth | Classical signal-processing filter; sharp roll-off | MED |
| **LOESS** | Local regression; smoother than EMA; lag depends on window | LOW |
| **ROOFING** Roofing Filter | Band-pass that isolates 10-48 bar cycles; perfect for M5 intraday cycles | MED |
| **WAVELET** Wavelet Denoising | Modern denoiser; multi-scale | LOW |

---

## 8. Reversal / stop / pivot

V5 has its own ratchet exit. These are alternative entry-trigger or stop-placement primitives.

| Indicator | Why for V5 | Priority |
|---|---|---|
| **SAR** Parabolic SAR | Classic trend-flip detector; could replace bias signal | MED |
| **FRACTALS** Williams Fractals | 5-bar swing high/low; useful as a pre-trade `support_above` / `resistance_below` distance | MED |
| **CHANDELIER** | ATR-based trailing stop; alternative to V5's ratchet | LOW |
| **PIVOTFIB** Fibonacci Pivots | Daily pivot levels; some traders use as MR targets | LOW |
| **PIVOTCAM** Camarilla Pivots | Different pivot formula; intraday levels | LOW |

---

## Total: 53 indicators across 8 use-cases

**HIGH priority:** 23 indicators — should enter the ML discovery corpus first  
**MED priority:** 22 indicators — second wave once HIGH is processed  
**LOW priority:** 8 indicators — only test on specific hypothesis

## Next-step suggestion
Pick a session's worth of trades (e.g. the recent 44-trade matrix Brock built) and compute HIGH-priority indicators on the matched bars. Then run the same per-feature accuracy + permutation test the smoke nightly does, against the realized direction sign. Indicators with accuracy ≥ 60% and orthogonal to V5's existing features (correlation < 0.5) become candidates for direction_v2/momentum_v3 profile inclusion.
