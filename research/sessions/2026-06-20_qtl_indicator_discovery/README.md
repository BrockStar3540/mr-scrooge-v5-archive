# 2026-06-20 — QuanTAlib indicator discovery sweep

**Author:** claude-code/MBP, session 2026-06-20  
**Builds on:** [2026-06-20_quantalib_eval](../2026-06-20_quantalib_eval/) (library validation + survey) and [2026-06-19_matrix_compilation](../2026-06-19_matrix_compilation/) (44-trade matrix)  
**Trigger:** Brock asked to check mihakralj's three companion repos (pinescript, pandas-ta, Trady) for indicator gaps V5 should be testing — surfaced 7 gap categories; this sweep tested ~25 candidates against the 44-trade matrix to find which ones actually move the needle.

## What's in this folder

| File | Purpose |
|---|---|
| `reports/QTL_DISCOVERY_REPORT.md` | Full findings with per-indicator accuracy + WR bucket tables + interpretation |
| `analyses/v5_qtl_prefetch.py` | Phase 1 (runs on EC2) — parses journal for entry times, fetches OANDA candles per trade, bundles into JSON |
| `analyses/v5_qtl_discovery.py` | Phase 2 (runs on Mini via `~/.venvs/quantalib/`) — computes 31 qtl indicators per trade, scores accuracy + orthogonality |
| `data/v5_qtl_prefetch_bundle.json` | Pre-fetched OANDA candles for all 44 trades (M5×500 + H1×300 + D×100 each, ~40K candles total) |
| `data/discovery_features.csv` | Per-trade feature matrix (44 rows × ~50 cols: 31 new qtl features + V5 reference features + outcome) |
| `data/discovery_signed_rank.csv` | Signed-indicator ranking by orthogonal lift |
| `data/discovery_magnitude_rank.csv` | Magnitude-indicator ranking by WR delta |

## Headlines

1. **`kurtosis_m5` HIGH-bucket WR 72.7% vs LOW-bucket 31.8% (Δ +40.9pp).** Strongest finding of the sweep. High kurtosis = fat-tailed recent returns = persistent moves. V5 has no distribution-shape feature; this fills a clear gap.

2. **`bbwp_m5` (BB Width Percentile) HIGH 69.6% vs LOW 33.3% (Δ +36.2pp).** Vol regime percentile rank; high BBWP = elevated structured vol. Effectively doubles V5's WR in its HIGH bucket.

3. **Volume oscillators DO carry signal in FX despite tick-volume noise.** `adosc` (Chaikin Oscillator) 61.4% direction accuracy + `efi` (Elder's Force Index) 59.1% — top of the signed-indicator list. Updates the memory rule "FX volume is unreliable" → "absolute FX volume is unreliable; oscillator forms ARE signal."

4. **Cycle-phase shows up:** `ht_dcphase_m5` 59.1% direction accuracy + `ht_dcperiod_m5` Δ+22.7pp magnitude bucket. V5 has zero cycle features; worth adding.

5. **`aroonosc_h1` (40.9%) and `super_dist_h1` (38.6%) are REVERSE signals** — either V5 already fades them correctly (= they ARE signal, just inverted) or noise; investigate with more trades.

## Sample size honesty

n=44 trades. 95% confidence band on a 60% accuracy estimate is ±14pp. The 40pp WR deltas for kurtosis + BBWP survive even at the conservative edge of that band, but secondary findings (vhf, ht_dcperiod, entropy) need a 100+ sample to settle. V5 takes ~10 trades/day, so we'll have a 200+ sample within 3 weeks.

## Recommended next actions

- **Wire `kurtosis_m5` + `bbwp_m5` into the Mini's nightly discovery cron** as evidence-gathering features. If the +40pp / +36pp WR deltas hold at n=100+, promote to direction_v2/momentum_v3 profile gates.
- **Update memory rule on FX volume.**
- **Investigate aroonosc / super_dist reverse signals.**

## Reproduction

```bash
# Phase 1: prefetch on EC2 (has OANDA token)
ssh -i ~/.ssh/openclaw-key.pem ubuntu@[REDACTED-IP] \
  '/home/ubuntu/mr_burns_env/bin/python /home/ubuntu/mr-scrooge-v5/research/sessions/2026-06-20_qtl_indicator_discovery/analyses/v5_qtl_prefetch.py'
# Ship bundle + matrix + script to Mini → ~/qtl-discovery/

# Phase 2: discovery on Mini
ssh -i ~/.ssh/mac_mini_austin brock-mini-mac@[REDACTED-IP] \
  '~/.venvs/quantalib/bin/python ~/qtl-discovery/v5_qtl_discovery.py'
```
