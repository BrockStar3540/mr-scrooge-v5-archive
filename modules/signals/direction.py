"""modules/signals/direction.py — Per-pair direction scoring from raw dm_04 factor sweep.

Weights are proportional to dm_04 raw net_60m decile spans (median across 24 pair×session
buckets): h1_ret_1bar +17.6p, rsi_slope +10.4p, zscore_1h +8.7p → weights 0.48/0.28/0.24.

Normalization anchors are D1.hi_val (D1/D2 boundary) and D10.lo_val (D9/D10 boundary)
from the dm_04 factor_sweep.json curves. This maps "entered D1" to -1.0 and "entered D10"
to +1.0 using each pair/session's own historical distribution — no outlier contamination
from the D1 lower tail or D10 upper tail.

No exit-management assumptions — this module describes raw market direction only.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from .base import MarketView, DirectionOutput

_CAL_PATH = Path(__file__).parent / "factor_sweep.json"
_CAL: dict = {}

_WEIGHTS = {
    "h1_ret_1bar": 0.48,
    "rsi_slope":   0.28,
    "zscore_1h":   0.24,
}

# Conservative defaults used when calibration for a bucket is missing
_FALLBACK_RANGES = {
    "h1_ret_1bar": (-12.0, 12.0),
    "rsi_slope":   (-9.0,  9.0),
    "zscore_1h":   (-2.0,  2.0),
}


def _cal() -> dict:
    global _CAL
    if not _CAL and _CAL_PATH.exists():
        _CAL = json.loads(_CAL_PATH.read_text())
    return _CAL


def _norm_range(pair: str, session: str, feat: str) -> tuple[float, float]:
    """D1/D2 boundary and D9/D10 boundary for feature in this pair/session bucket.

    D1.hi_val is the upper edge of the lowest decile; D10.lo_val is the lower edge
    of the highest decile. A feature value below lo is fully short (-1), above hi
    is fully long (+1), with linear interpolation between.
    """
    try:
        curve = _cal()[pair][session]["curves"][feat]
        lo = float(curve["D1"]["hi_val"])   # D1/D2 boundary
        hi = float(curve["D10"]["lo_val"])  # D9/D10 boundary
        if lo < hi:
            return lo, hi
    except (KeyError, TypeError, ValueError):
        pass
    return _FALLBACK_RANGES.get(feat, (-10.0, 10.0))


def _norm(v: float, lo: float, hi: float) -> float:
    if hi == lo:
        return 0.0
    return float(np.clip((v - lo) / (hi - lo) * 2 - 1, -1, 1))


def score_direction(view: MarketView) -> DirectionOutput:
    """Score market direction from dm_04 raw momentum factors.

    Normalization is per (pair × session) so a strong reading is calibrated
    to that bucket's D1/D10 boundaries rather than global placeholders.
    """
    lo_h1, hi_h1 = _norm_range(view.pair, view.session, "h1_ret_1bar")
    lo_rs, hi_rs = _norm_range(view.pair, view.session, "rsi_slope")
    lo_z,  hi_z  = _norm_range(view.pair, view.session, "zscore_1h")

    h1_norm    = _norm(view.h1_ret_1bar, lo_h1, hi_h1)
    rsi_s_norm = _norm(view.rsi_slope,   lo_rs, hi_rs)
    z_norm     = _norm(view.zscore_1h,   lo_z,  hi_z)

    score = (_WEIGHTS["h1_ret_1bar"] * h1_norm
           + _WEIGHTS["rsi_slope"]   * rsi_s_norm
           + _WEIGHTS["zscore_1h"]   * z_norm)
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
