# Research

Every substantive research session that informed a V5 change. Cross-referenced so future sessions can be **circumspect of existing findings** and **rigorously cross-check** new ones against the corpus already in here.

## Methodology — before starting new research

Read this section before running a new sweep, smoke test, or backtest. The same rules apply to humans and to agents.

### 1. Cross-check the corpus first

The cells under `sessions/` are not isolated. Many questions have been asked before. Before launching anything substantive:

- Search `sessions/*/README.md` for the question you're investigating.
- Check `matrices/` for relevant per-trade data already captured.
- Check `reference/` for Brock-curated reports from earlier V5 testing.
- Read the most-recent matrix vault note (mirrored in vault `wiki/systems/note_scrooge_v5_findings_matrix_*.md`).

If the question is already answered: link the prior session in your new session's README and update the matrix vault note with whatever incremental signal you found.

### 2. Document what + why + outcome

Every session folder has a `README.md` with three sections at minimum:

- **What** — what you ran, with concrete file paths and commit hashes.
- **Why** — the question you were trying to answer.
- **Findings + outcome** — what you concluded, what you did with it (config change? new module? noted for later?), and what the next question is.

If a session changes the live trader, link to the relevant [CHANGELOG.md](../CHANGELOG.md) entry.

### 3. Sample size honesty

Most sessions have small N (10-50 trades). For any per-cell finding, state the cell sample size next to the claim. Don't extrapolate single-cell wins to global rules — that's the trap we hit multiple times in early 2026-06 work (see [feedback_no_defer_when_asked](../research/sessions/2026-06-19_per_direction_extension/README.md) for the lessons).

### 4. Scope claims to method + data

Findings that hold in one cell at one sample size may not generalize. Note the corpus (live vs corpus vs broker-cross-validated), the time window, and the pair-session breakdown. Don't claim "universal" unless 8+ cells across 2+ sessions concur.

### 5. Cross-broker / multi-source confirmation

For Tier 1 findings (universal claims):
- Confirm on the 7.5yr OANDA corpus.
- Spot-check on a second broker (forexsb.com H1 data is in [research/reference/](reference/) — or fresh fetch if older).
- Confirm in live smoke (at least 10 trades).

If only one of three confirms, the finding is Tier 2 (cell-conditional) and the cell range must be stated.

## Folder layout

```
research/
├── README.md            this file
├── reference/           Brock-curated reports (dm05-dm09 + factor_sweep)
├── sessions/            chronological — one folder per research session
├── matrices/            live-trade matrices that drove decisions
└── live-smoke/          nightly cron output (./data/v5-smoke-history/ mirror)
```

## Index of sessions

| Date | Session | What it produced | Outcome |
|---|---|---|---|
| 2026-06-13 → 06-18 | Direction signal + ratchet amplification analysis (`docs/EDGE_REPORT.md`) | dm04 calibration, edge map | V5 v1 modules + ratchet shipped |
| 2026-06-18 | [aggregator_sweep](sessions/2026-06-18_aggregator_sweep/) | 24 per-cell XGB models, matrix of which V3 aggregators contribute edge | h1_ret_1bar #1 universal; atr_conc Q4 magnitude penalty universal; wall_frac amplifier; matrix vault note |
| 2026-06-19 | [matrix_compilation](sessions/2026-06-19_matrix_compilation/) | 44-trade live matrix with 24 → 36 features per trade | Per-session correlations driving v2/v3 cell assignments |
| 2026-06-19 | [live_smoke_v1-v5](sessions/2026-06-19_live_smoke_v1-v5/) | Per-bucket aggregator amplification on live trades | Per-session predictor rankings; ratchet retune diagnosis |
| 2026-06-19 | [per_direction_extension](sessions/2026-06-19_per_direction_extension/) | direction_v2 + momentum_v3 promoted to (pair × session × direction) | 48-cell modules staged |
| 2026-06-20 | [quantalib_eval](sessions/2026-06-20_quantalib_eval/) | QuanTAlib lib validated vs V5 hand-codes + 53 candidate indicators + speed bench | EMA/SMA/BB bit-exact; qtl ~3x faster; reference for new research |
| 2026-06-20 | [qtl_indicator_discovery](sessions/2026-06-20_qtl_indicator_discovery/) | 31 qtl indicators on 44-trade matrix | kurtosis_m5/bbwp_m5 looked strong (later refuted at 8yr scale) |
| 2026-06-20 | [qtl_8yr_per_cell](sessions/2026-06-20_qtl_8yr_per_cell/) | 8yr per-(pair x session) XGB, 4.4M bars, willr/Aroon candidates | willr top-3 in 24/24 cells (8yr avg - later shown regime-specific) |
| 2026-06-21 | [v5_2026_audit](sessions/2026-06-21_v5_2026_audit/) | Profiles + aggregators + qtl re-audited on 2026 only; year/month drift | 38/48 cells profile-mismatched on 2026; atr_conc rule DEAD; drift is real |
| 2026-06-21 | [master_matrix](sessions/2026-06-21_master_matrix/) | 48-cell x all-evidence matrix + live replay + indicator roles | Live replay killed qtl-as-binary-rules; 5 cells disabled |
| 2026-06-21 | [real_oanda_trades](sessions/2026-06-21_real_oanda_trades/) | **Pulled ACTUAL 120 trades from OANDA API (journal missed 70)** | Journal-derived matrix was wrong; broker is ground truth |
| 2026-06-21 | [broker_validation](sessions/2026-06-21_broker_validation/) | Fresh OANDA candles per trade then 1H forward pip; matrix+broker disable | Realized P/L matches fwd dir only 68%; 6 then 10 cells disabled |
| 2026-06-21 | [app_config_test](sessions/2026-06-21_app_config_test/) | 8 RSI/EMA/StochRSI MTF configs, 910k signals, 8yr | ZERO 1H edge; MTF alignment is decorative; RSI cross slightly anti-predicts |
| 2026-06-21 | [indicator_sweep](sessions/2026-06-21_indicator_sweep/) | 46 RSI/EMA/StochRSI variants x TF as standalone + aggregator/verifier | No param rescues standalone; fast=exhaustion, slow=confirm; session-signed |
| 2026-06-21 | [percell_exhaustion](sessions/2026-06-21_percell_exhaustion/) | Per-cell momentum fade/trend, walk-forward + inversion test | **NY = momentum FADE, 8/8 pairs walk-forward**; explains broker losses |
| 2026-06-21 | [v4_bucket_test](sessions/2026-06-21_v4_bucket_test/) | V4-era ALIGN/bucket claims tested on 8yr; align resolution | ALIGN climbs (ny_open steepest); RSI-extreme-only-aligned confirmed; align sign flips by session |
| 2026-06-21 | [cell_ruleset](sessions/2026-06-21_cell_ruleset/) | **Consolidated 48-cell module spec** from 6 validated tests | ~5 confirmed winners; conflicts prove per-cell modules needed |

## Methodology learnings - the 2026-06-20/21 weekend (read before any trade analysis)

This weekend overhauled how we measure Scrooge. The hard-won rules:

1. **Pull from OANDA API, not the bot journal.** The journal captures V5's INTENT (SIGNAL/ENTERED markers); only the broker has actual fills, manual closes, spread costs, realized P/L. The 44-trade journal matrix missed 70 of the actual 120 trades. Use the transactions/idrange endpoint. (`sessions/2026-06-21_real_oanda_trades/`)

2. **Use 1H FORWARD PIP for entry-indicator decisions, NOT realized P/L.** Exit logic (ratchet/SL/manual) is tuned constantly and flips 32% of trades from the actual market direction. Realized P/L confounds entry quality with exit choices. Compute forward pip from fresh OANDA candles: (close[t+12]-close[t])/pip * dir_sign. (`sessions/2026-06-21_broker_validation/`)

3. **Include manual-closed trades in forward analysis.** A manual close affects realized P/L only - NEVER the entry-bar indicators or the 1H forward market direction. Filtering them out discards real data. (caught + fixed in broker_validation)

4. **Walk-forward everything.** Train < 2024, test >= 2024. The "overlap trends" claim was strongly positive in-sample but FLIPPED negative out-of-sample. Only walk-forward-stable findings (e.g. NY fade, 8/8 pairs) are trustworthy. (`sessions/2026-06-21_percell_exhaustion/`)

5. **Per-(pair x session x direction), never global.** The same indicator/momentum/alignment has OPPOSITE sign in different cells: momentum fades in NY but trends in overlap; willr +0.57 corr in USD_CAD/ny but -0.57 in EUR_USD/london. Validated four independent ways (broker P/L + broker forward + 8yr walk-forward + align resolution). The cells genuinely disagree, so each needs its own rules. (`sessions/2026-06-21_cell_ruleset/`)

6. **App-confluence visual != forward-price edge.** Multi-timeframe RSI/EMA/StochRSI confluence has ZERO 1H edge at any parameter setting (910k signals). The MTF alignment that looks authoritative is decorative. Only "scan every occurrence, measure the forward move" tells the truth. (`sessions/2026-06-21_app_config_test/`)

### Key live-trader facts established this weekend
- V5 has been LOSING: -$6,114 over 120 trades (V4+V5), -$2,234 V5-era 36 trades. Edge is concentrated in ~5 cells; the bot trades the whole 48-cell grid including fade cells.
- **NY is a momentum-FADE session** (8/8 pairs, walk-forward, broker-corroborated). V5 trend-follows h1_ret (its #1 factor) into a fade regime, producing the NY losses.
- **Confirmed winner cells:** USD_CAD/ny/long (+6.61p, n=7), EUR_USD/london/short (+6.31p, n=7), AUD_JPY/asia long+short (trend).
- **10 cells disabled** (config/playmaker_config.json disabled_cells); 2 cells (GBP_USD/ny, EUR_JPY/ny) shadow-logging inverted direction.
- **ALIGN (HTF agreement) is live** in V5 (htf_pct_20/60 + trend_4h non-zero) - the V4-era freeze is fixed; align CAN be wired now, but session-signed (confirm in overlap, fade in NY/london).
- Architectural refinement flagged: V5's ny session (13-21 UTC) lumps trend-y overlap (13-14) with fade-y late-ny (15-21) - split for coherent per-module regime.

### The 8yr corpus + Mini compute (all heavy work runs HERE)
- Per-pair M5/H1/D parquets: /Volumes/Alien Device/direction_ml/raw_bars/ (8 pairs, ~553k M5 bars each, 2019-2026)
- Computed feature parquets: ~/qtl-discovery-8yr/features/<PAIR>_features.parquet (84 features incl. fwd_ret_pips)
- Python venv with quantalib + xgboost + scipy: ~/.venvs/quantalib/ (Python 3.12)
- Monthly Master Matrix cron: ~/.local/bin/master_matrix_monthly.sh (1st of month, 04:00)
- All scripts reproducible - see each session's analyses/. Device serial check (CPYQTH294R) guards every heavy script.

## Index of matrices

| File | Trades | Columns | Built by |
|---|---:|---:|---|
| `matrices/v5_trade_matrix_44trades_base.csv` | 44 | 14 | `sessions/2026-06-19_matrix_compilation/analyses/v5_trade_matrix.py` |
| `matrices/v5_full_matrix_44trades.csv` | 44 | 24 | `sessions/2026-06-19_matrix_compilation/analyses/v5_full_matrix.py` |
| `matrices/v5_full_matrix_v2_36cols.csv` | 44 | 36 | `sessions/2026-06-19_matrix_compilation/analyses/v5_more_aggs.py` |

## Index of reference reports (Brock-curated, Dropbox `/SCROOGE V5/Test Data/`)

| File | Size | Topic |
|---|---:|---|
| `reference/factor_sweep.txt` | 87KB | Full factor × bucket sweep — per-cell aggregator behavior |
| `reference/direction_ml_report.txt` | 22KB | Direction + momentum matrix from earlier V5 ML build |
| `reference/dm05_ratchet_corr.txt` | 1.5KB | DM-05 ratchet label correlation |
| `reference/dm06_validation.txt` | 27KB | DM-06 validation suite |
| `reference/dm07_direction_split.txt` | 27KB | DM-07 direction-split factor sweep |
| `reference/dm08_combo_sweep.txt` | 40KB | DM-08 combo sweep (2-factor 5×5) |
| `reference/dm09_ratchet_sweep.txt` | 79KB | DM-09 indicator sweep — raw vs ratchet |

These are the source-of-truth reports from earlier dm04-dm09 work that informed the original V5 modules. Read first when asking "did we test X already?"

## Index of live data

| File | Notes |
|---|---|
| `live-smoke/all_trades_per_feature_seed.csv` | First night's cron output, 9 trades from 2026-06-19 |
| `live-smoke/2026-06-19_first_run.txt` | Per-day human-readable summary |

Live data accumulates in `/data/v5-smoke-history/` on EC2 via the 23:30 UTC cron. Periodically snapshot fresh copies into this folder (and update the matrix vault note).

## Vault cross-reference

The matrix vault note `wiki/systems/note_scrooge_v5_findings_matrix_2026-06-18.md` is the **rolling synthesis** of all research findings. It supersedes individual session READMEs for "what do we currently believe is true." Sessions add to it; the note is the consolidated view.

Other vault notes that cross-reference research:
- `wiki/systems/cockpit.md` — V5 banner has the most-recent state
- `wiki/systems/agent-activity-log.md` — chronological log of cross-agent activity (V5 entries chronicle research sessions)
- `wiki/systems/quick-status.md` — live alerts/positions (auto-updated)
