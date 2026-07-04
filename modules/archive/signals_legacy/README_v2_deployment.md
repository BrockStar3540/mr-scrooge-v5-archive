# V5 Direction + Momentum Module v2 — Deployment Guide

Three drop-in files alongside V5's existing modules:

```
modules/signals/direction_profiles.py   (NEW — profile definitions + rules)
modules/signals/direction_v2.py         (NEW — drop-in DirectionModule)
modules/signals/momentum_v2.py          (NEW — drop-in MomentumModule)
```

## What's different from V5 v1

### Direction v2

1. **Per-(pair × session) weight profiles** — three types:
   - `continuation_strong`: boost h1_ret_1bar, trend_4h, HTF; halve PDL; for asia/JPY cells
   - `reversion`: boost mean-reversion family 2-3×, reduce trend/HTF; for NY non-JPY
   - `default`: V5's current weights unchanged; for cells without clear evidence

2. **Universal weight adjustments applied to ALL profiles**:
   - PDL distance features halved (live evidence: 31% accuracy)
   - close_pos_daily boosted (matrix #3 by permutation; 62% live accuracy)
   - h1_ret_1bar boosted in continuation cells (lives at 76% accuracy)

3. **Aggregator amplifier rules** (3 conditional multipliers):
   - `atr_conc > 2.5` → HTF + structural features × 1.5
   - `atr_h1_relative > 1.6` → reversion family × 1.3
   - `atr_h1_relative > 1.6` → HTF/continuation × 0.5

### Momentum v2

1. **`EXPECTED_PIPS_SCALER = 0.30`** — caps expected_pips at 30% of raw atr_1h × rvol calculation. Live evidence: V5's current expected_pips overshoots realized pip_high by 70-80%.

2. **wall_frac amplifier** — when min(PDH, PDL)/atr > 5.0, boost expected_pips by 1.3×. Live evidence: correlation +0.95 with pip_high in 3 of 5 cells.

3. **atr_conc gate UNCHANGED** — V5's existing Q4 block (atr_conc > 0.55) is preserved. Live smoke v3 confirmed -0.93 to -1.0 correlation with pip_high.

## Deployment steps

### Step 1 — copy files to V5 repo

```bash
# On EC2 (after pulling these files from /tmp/v5_new_modules):
cp /tmp/v5_new_modules/direction_profiles.py ~/mr-scrooge-v5/modules/signals/
cp /tmp/v5_new_modules/direction_v2.py        ~/mr-scrooge-v5/modules/signals/
cp /tmp/v5_new_modules/momentum_v2.py         ~/mr-scrooge-v5/modules/signals/
```

### Step 2 — SHADOW MODE first (recommended)

In `core/engine.py`, modify the engine to instantiate BOTH the v1 and v2
modules. Log both scores; route trades through v1 only. This lets you compare
v1 vs v2 scores on live signals for several days before switching execution.

```python
# pseudocode in engine.py
from modules.signals.direction    import DirectionModule
from modules.signals.direction_v2 import DirectionModule as DirectionModuleV2
from modules.signals.momentum     import MomentumModule
from modules.signals.momentum_v2  import MomentumModule as MomentumModuleV2

# in _cycle:
dir_v1 = self.dir_modules[(pair, session)].stamp(view)
dir_v2 = self.dir_modules_v2[(pair, session)].stamp(view)
log.info(f"SHADOW {pair}/{session}: v1.score={dir_v1.score:.3f} v2.score={dir_v2.score:.3f}")
# … existing logic uses dir_v1 only
```

Run shadow for **5-10 trading days**. Compare every signal's v1 vs v2 scores
to today's actual outcome (use smoke_v2.py against the new shadow logs).

### Step 3 — promote v2 to primary

After shadow validation, switch the imports in `engine.py`:

```python
from modules.signals.direction_v2 import DirectionModule
from modules.signals.momentum_v2  import MomentumModule
```

Restart `mr-scrooge-v5.service`. The MarketView shape is unchanged, so no
upstream changes needed.

### Step 4 — rollback plan

If v2 underperforms during shadow OR live, revert:
- Edit `engine.py` imports back to v1
- `systemctl --user restart mr-scrooge-v5`

The v2 files can stay in the repo (they're not loaded unless imported).
factor_sweep.json is shared between v1 and v2 — no risk to the calibration data.

## Profile assignments (current matrix evidence)

| Pair    | asia                       | london                | ny                         |
|---------|----------------------------|------------------------|----------------------------|
| AUD_JPY | continuation_strong [STRONG]| default [WEAK]         | continuation_strong [MOD]   |
| AUD_USD | continuation_strong [MOD]  | default [WEAK]         | reversion [WEAK]            |
| EUR_JPY | continuation_strong [MOD]  | reversion [MOD]        | default [WEAK]              |
| EUR_USD | default [WEAK]             | default [WEAK]         | reversion [STRONG]          |
| GBP_USD | default [WEAK]             | continuation_strong[WK]| reversion [STRONG]          |
| USD_CAD | default [WEAK]             | default [WEAK]         | reversion [MOD]             |
| USD_CHF | default [WEAK]             | default [WEAK]         | continuation_strong [WEAK]  |
| USD_JPY | continuation_strong [MOD]  | default [WEAK]         | continuation_strong [WEAK]  |

Evidence levels:
- STRONG = corpus + cross-broker + live concur
- MOD    = two of three sources concur
- WEAK   = single source or n≤2 trades; using "default" (V5 unchanged)

Cells marked WEAK use V5's existing weights as a conservative fallback —
no regression risk vs v1.

## Future iteration

After 5-10 trading days of shadow data, rebuild profile assignments using
the smoke_history.csv evidence (smoke_v2 daily output). Replace WEAK
assignments where new evidence has accumulated.

## Files in this drop

1. `direction_profiles.py` — profile templates + per-cell assignments + rules
2. `direction_v2.py`        — drop-in DirectionModule
3. `momentum_v2.py`         — drop-in MomentumModule
4. `README_deployment.md`   — this file

All files are reviewable Python — no binaries, no pickles, no external
dependencies beyond what V5 v1 already uses.
