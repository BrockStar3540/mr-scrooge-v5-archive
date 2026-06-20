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
