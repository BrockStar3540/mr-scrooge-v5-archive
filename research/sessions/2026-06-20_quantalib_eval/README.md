# 2026-06-20 — QuanTAlib evaluation

**Author:** claude-code/MBP, session-end 2026-06-20  
**Library:** [QuanTAlib v0.8.9](https://github.com/mihakralj/QuanTAlib) (C# NativeAOT core, Python wrapper) — 411 indicators cross-validated against TA-Lib + Tulip + Skender + Pandas-TA  
**Host for testing:** Mac Mini (`carls-mac-mini`, arm64) via `~/.venvs/quantalib/` (Python 3.12.13)  
**Why this work:** Brock surfaced the repo as a "incorporate in our testing" reference. Three-step evaluation: validation pass → indicator survey → speed benchmark.

## What's in this folder

| File | Purpose |
|---|---|
| `V5_QTL_VALIDATION_REPORT.md` | **Step 1 results** — V5 hand-codes vs qtl reference, bit-by-bit, on 500 EUR_USD H1 bars |
| `QTL_CANDIDATES_FOR_V5.md` | **Step 2 results** — 53 indicators from qtl's 411-catalog curated for V5 forex M5 use, with priority tiers |
| `QTL_BENCHMARK_REPORT.md` | **Step 3 results** — V5 pandas vs qtl speed comparison at 10K / 100K / 500K bars |
| `v5_qtl_validation.py` | Reproducer for step 1 |
| `v5_qtl_benchmark.py` | Reproducer for step 3 |
| `EUR_USD_H1_500.csv` | Test data (500 H1 bars 2026-05-22 → 2026-06-19) |
| `benchmark_results.json` | Raw benchmark output |

## Headline findings

1. **V5's hand-coded indicators are mathematically equivalent to qtl reference.** EMA / SMA / BB-mid match bit-exact (0.00e+00 diff). Wilder ATR + RSI match bit-exact at the last-bar values V5 actually reads in live; warmup-region diff is a convention difference in initial seeding, invisible to production. One BB convention diff: V5 uses ddof=1 (sample stdev), qtl uses ddof=0 (population) — bands ~2.5% wider in V5; new research code should pick the qtl convention to match the TA library ecosystem.

2. **53 candidate indicators identified across 8 use-cases** for the ML discovery engine. 23 marked HIGH priority — HMA / ALMA / KAMA / JMA (lag-reducing MAs), CRSI / LRSI / STOCHRSI / TSI / FISHER (alt momentum), ATRN / BBWP / YZV / GKV (better vol), ADX / CHOP / AROON / SUPER / VHF (trend strength — known V5 gap), HURST / ENTROPY / KURTOSIS / SKEW (distribution), HT_DCPERIOD / HT_DCPHASE / EBSW (cycle), KALMAN (filter).

3. **QuanTAlib is ~3× faster than V5's pandas for the same indicators** at 500K-bar backtest scale. Not the 100-1000× the C# version advertises (Python marshalling eats the AOT win), but a real win for research/discovery passes. Live engine should NOT swap — per-cycle cost is already negligible.

## Recommendations to Brock

- **Adopt qtl as the reference implementation for new research code** (the discovery engine, smoke nightly cross-checks, future feature-engineering scripts on the Mini).
- **Do NOT touch V5 live feed** — it's validated equivalent and operationally safer.
- **Wire the HIGH-priority candidate indicators into the next discovery-engine pass** to see if any beats V5's existing 24 direction features on per-cell accuracy. The Mini's `scrooge-mllab` is the natural home.
- **Pip-install `quantalib[pandas]` on every Mini Python venv that does research work.** Already installed at `~/.venvs/quantalib/`; reuse or add to other envs.

## Open follow-ups (NOT done in this session)

- Run a real per-feature-accuracy test on the 44-trade matrix using HIGH-priority qtl indicators (the validation step that promotes a candidate from "interesting" to "evidence-backed").
- Decide whether to move `v5_smoke_nightly.py` (which lives at `/home/ubuntu/v5_smoke_nightly.py` on EC2, outside the repo) into the V5 repo + add a qtl-based feature-augmentation column.
- If the discovery engine finds new winners, fold them into `direction_v2 / momentum_v3` per-cell profiles.

## How to reproduce

```bash
# On the Mini
cd ~/quantalib-validation
~/.venvs/quantalib/bin/python v5_qtl_validation.py    # validation
~/.venvs/quantalib/bin/python v5_qtl_benchmark.py     # benchmark
```

`v5_qtl_validation.py` takes a CSV path arg (defaults to the bundled EUR_USD_H1_500.csv). To re-validate on fresh data, regenerate the CSV from any pair / granularity / count via OANDA candles API.
