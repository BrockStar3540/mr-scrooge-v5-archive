"""modules/signals/momentum.py — Raw market condition magnitude scoring.

ATR, rvol, and adr_consumed are intrinsic market-condition metrics — they describe
how much the market is currently moving (ATR), how active participation is relative
to recent norms (rvol), and how much of today's expected range has already been
consumed (adr_consumed). These are properties of the market itself; the magnitude
score captures expected per-bar movement potential independent of any exit strategy.

Calibration of pair-specific vol regimes will be loaded from dm_04 ATR decile edges
once the per-pair module build is complete. Current regime thresholds are global
placeholder values from the all-pair median ATR distribution.
"""
from __future__ import annotations
import numpy as np
from .base import MarketView, MomentumOutput


def score_momentum(view: MarketView) -> MomentumOutput:
    """Composite market-condition magnitude from ATR, rvol, and ADR context.

    atr_5m:       expected pip movement per M5 bar under current conditions
    rvol_5bar:    current volume relative to 5-bar rolling mean (1.0 = normal)
    adr_consumed: fraction of today's average daily range already used (0=fresh, 1=exhausted)
    """
    atr_score  = np.log1p(view.atr_5m)          # log-scale: 0→0, 10→2.4, 30→3.4
    rvol_score = np.clip(view.rvol_5bar, 0, 3)  # relative vol capped at 3x
    adr_score  = np.clip(view.adr_consumed, 0, 1)

    magnitude = 0.45 * atr_score + 0.35 * rvol_score + 0.20 * adr_score
    magnitude = float(max(magnitude, 0.0))

    if view.atr_5m < 2.0:
        vol_regime = "low"
    elif view.atr_5m < 6.0:
        vol_regime = "normal"
    elif view.atr_5m < 12.0:
        vol_regime = "high"
    else:
        vol_regime = "extreme"

    return MomentumOutput(
        pair=view.pair, session=view.session, timestamp=view.timestamp,
        magnitude=round(magnitude, 4), vol_regime=vol_regime,
        factors={
            "atr_5m":       view.atr_5m,
            "rvol_5bar":    view.rvol_5bar,
            "adr_consumed": view.adr_consumed,
        },
    )
