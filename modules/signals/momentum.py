from __future__ import annotations
import numpy as np
from .base import MarketView, MomentumOutput


def score_momentum(view: MarketView) -> MomentumOutput:
    """Compute magnitude score from ATR/vol/ADR factors.

    Key finding (dm_09): ATR/vol have ~0 raw span but +11-12p ratchet span.
    These factors predict the SIZE of the upcoming move, not the direction.
    Direction module handles direction; this module handles magnitude.

    magnitude = weighted composite; higher = bigger expected ratchet capture.
    """
    atr_score  = np.log1p(view.atr_5m)          # log-scale: 0->0, 10->2.4, 30->3.4
    rvol_score = np.clip(view.rvol_5bar, 0, 3)  # relative vol capped at 3x
    adr_score  = np.clip(view.adr_consumed, 0, 1)

    # Composite: ATR dominates (dm_09 span +11.9p), rvol secondary (+9.7p)
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
