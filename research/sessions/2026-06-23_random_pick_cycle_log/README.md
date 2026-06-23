# V5 random pick_best + per-cycle CYCLE log (2026-06-23)

**Date:** 2026-06-23 ~05:52 UTC live cut-over
**Commits:** [c43c38c](https://github.com/BrockStar3540/mr-scrooge-v5/commit/c43c38c) (random + CYCLE log), bac4d69 (5s manage), 200629f (inverted_live infra)

## Why
After 24h of inverted_live testing we saw **5 of 14 trades were GBP_USD/ny alone** because pick_best ranks by `abs(composite_score)` and GBP_USD/ny consistently had the highest composite each NY cycle. Most enabled cells (11 of 13 inverted-live, 8 of 11 normal-enabled) got zero trades. The composite-magnitude ranker was gatekeeping cells with otherwise-actionable signals.

The matrix research [2026-06-21_master_matrix](../2026-06-21_master_matrix/) had warned about scoring confidence — close_pos_daily was the only feature with strong global direction correlation (-0.24) but per-cell it doesn't make the top-3 ML rules for any of our 6 live cells. Other indicators (q_willr_m5, q_kc_up_dist_pips, q_vortex_diff_h1) were stronger per-cell. The current composite formula doesn't use any of these.

Brock's call (verbatim): *"maybe the way they are scored is wrong. ... just randomize the trade that gets fired off then, this way they all fire, because right now, the current priority ranking score is unreliable and its gatekeeping other pairs with opportunities."*

## What changed

### 1. `playmaker.py` — `random_pick` config flag
- New `random_pick: bool` field in `playmaker_config.json` (default `false`)
- When `true`, pick_best uses `random.choice(candidates)` instead of `max(_edge_rank)`
- All actionable candidates get equal probability
- TradeTicket.reads now includes `pick_method: "random" | "edge_rank"` for traceability
- Hot-reloadable (no restart needed to flip on/off)
- Live now: `random_pick: true`

### 2. `engine.py` — per-cycle ticket dump
- After pick_best returns, log one pipe-delimited line dumping all 8 pairs' state:
  ```
  CYCLE <iso_ts> picked=<pair/sess/dir or NONE> method=<random|edge_rank|none>
    | <pair>/<sess>/<bias> act=<T|F> dscore=<x> dcert=<x> mcert=<x>
      comp=<x> vortex=<x> close_pos=<x>
    | ...
  ```
- ~288 cycles/day × 8 pairs = **~2300 ticket-observations/day**

## The analyzer — `analyses/v5_cycle_log_analyzer.py`

Parses CYCLE lines from the journal. For each cycle, applies the playmaker's session + disabled filter to identify the eligible candidate set, then re-applies four alternative rankers to that same set:

| Ranker | Score |
|---|---|
| **max-composite** | `abs(composite_score)` — current default |
| **random** | uniform pick (what's live now) |
| **vortex-aligned** | `vortex_diff × (+1 if long else -1)` |
| **comp×vortex** | `abs(composite) × (1 + max(0, vortex_aligned))` |

Outputs:
- Per-cell counts: eligible-cycles, actual picks, counterfactual picks under each ranker
- Diversity: distinct cells each ranker would fire across the window
- Top-1 cell share (lower = more spread)
- Optional `--csv` dump of all per-cycle candidates

```bash
# Run after 24-48h of CYCLE data:
python3 analyses/v5_cycle_log_analyzer.py
python3 analyses/v5_cycle_log_analyzer.py --csv
python3 analyses/v5_cycle_log_analyzer.py --since '2026-06-24 12:00:00'
```

## Reading the output

The headline question: **does max-composite's gatekeeping correlate with actually better outcomes, or is it noise?**

If we see:
- **max-composite would fire 1-2 cells out of N eligible** (top-1 share > 50%): confirms gatekeeping concern; random or vortex-aligned likely give better cell coverage
- **vortex-aligned spreads to many cells AND those cells later win**: ship vortex-aligned as new primary
- **random gets same cell distribution as max-composite**: there isn't much gatekeeping happening; the cells genuinely all rank similarly

To attribute OUTCOMES (win/loss per ranker-pick), join with the existing `v5_mfe_mae_report.py` per-trade table — match each picked cell to the resulting ENTERED/EXIT lines using trade_id.

## Easy revert
Config-only revert: edit `playmaker_config.json` → `random_pick: false` → save. Hot-reloads to max-composite behavior. CYCLE log keeps emitting regardless of pick_method.

## Status
- Live as of 2026-06-23 05:52 UTC
- First CYCLE log line confirmed: 05:52:17 (clean)
- Re-run analyzer at 24h (2026-06-24 ~06:00 UTC) and 48h marks
- If random-pick produces meaningfully different live results vs max-composite history, that's the data we need to design a better permanent ranker
