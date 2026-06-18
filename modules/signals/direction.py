from __future__ import annotations
import numpy as np
from .base import MarketView, DirectionOutput

# Per-pair/session zero-crossing thresholds for h1_ret_1bar (pips).
# Source: dm_09 ratchet sweep decile boundaries.
# Placeholder -- will be populated from dm_09 data.
DIRECTION_BLOCK_THRESHOLD: dict[tuple[str,str], float] = {}


def score_direction(view: MarketView) -> DirectionOutput:
    """Compute direction score from H1 momentum factors.

    Signal stack (weights from dm_09 ratchet sweep):
      h1_ret_1bar  -- primary (span ~17p raw, ~9.5p ratchet)
      rsi_slope    -- secondary (span ~10p raw, ~6p ratchet)
      zscore_1h    -- tertiary (span ~8.7p raw, ~4.6p ratchet)

    Returns score in [-1, +1] and bias in {long, short, block}.
    """
    def _norm(v: float, lo: float, hi: float) -> float:
        if hi == lo:
            return 0.0
        return float(np.clip((v - lo) / (hi - lo) * 2 - 1, -1, 1))

    # Placeholder normalisation ranges (will be loaded per-bucket from dm_09 edges)
    h1_norm     = _norm(view.h1_ret_1bar, -15.0, 15.0)
    rsi_s_norm  = _norm(view.rsi_slope,    -5.0,  5.0)
    z_norm      = _norm(view.zscore_1h,    -2.0,  2.0)

    # Weighted sum -- weights reflect dm_09 ratchet span ratios
    score = 0.55 * h1_norm + 0.28 * rsi_s_norm + 0.17 * z_norm
    score = float(np.clip(score, -1.0, 1.0))

    confidence = abs(score)
    bias = "block"
    if score > 0.15:
        bias = "long"
    elif score < -0.15:
        bias = "short"

    return DirectionOutput(
        pair=view.pair, session=view.session, timestamp=view.timestamp,
        score=score, confidence=confidence, bias=bias,
        factors={
            "h1_ret_1bar": view.h1_ret_1bar,
            "rsi_slope":   view.rsi_slope,
            "zscore_1h":   view.zscore_1h,
            "h1_norm":     round(h1_norm, 3),
        },
    )
