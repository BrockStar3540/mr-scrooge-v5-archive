"""modules/signals/direction.py — Per-(pair × session) direction module.

DirectionModule is instantiated once per bucket at startup. It owns the calibration
data for its bucket and translates raw indicator values into directional reads.

7 direction factors, weighted by their dm_04 raw net_60m decile spans (median across
all 24 pair×session buckets):

  h1_ret_1bar       +17.6p  →  w=0.282   primary momentum: last H1 bar return
  rsi_slope         +10.4p  →  w=0.167   RSI velocity: momentum of the momentum
  zscore_1h          +8.7p  →  w=0.140   H1 Z-score: departure from recent mean
  h1_ret_4bar        +7.3p  →  w=0.117   4-bar H1 momentum: trend vs. noise
  d_ret              +7.1p  →  w=0.114   daily return: macro session context
  ema20_1h_dist      +6.4p  →  w=0.103   EMA20 dist: position in trend structure
  rsi14              +4.8p  →  w=0.077   RSI level: overbought / oversold context

Normalization anchors: D1.hi_val (D1/D2 boundary) and D10.lo_val (D9/D10 boundary)
from the dm_04 factor_sweep.json for this specific bucket. Values outside those
boundaries clip to ±1. Values near zero = D5 territory = no signal.

Certainty reflects both how extreme each reading is AND how much the factors agree.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
import numpy as np
from .base import MarketView, DirectionStamp

_CAL_PATH = Path(__file__).parent / "factor_sweep.json"
_CAL: dict = {}

# Weights proportional to dm_04 raw net_60m spans (7 factors, sum to 1.0)
_FACTORS = [
    ("h1_ret_1bar",    0.282),
    ("rsi_slope",      0.167),
    ("zscore_1h",      0.140),
    ("h1_ret_4bar",    0.117),
    ("d_ret",          0.114),
    ("ema20_1h_dist",  0.103),   # stored as ema20_1h_dist_pct in factor_sweep
    ("rsi14",          0.077),
]

# sweep key name differs from MarketView field name for one feature
_SWEEP_KEY = {
    "ema20_1h_dist": "ema20_1h_dist_pct",
}

# Fallback D1/D10 anchors when calibration is missing for a bucket
_FALLBACK = {
    "h1_ret_1bar":   (-12.0, 12.0),
    "rsi_slope":     (-9.0,  9.0),
    "zscore_1h":     (-2.0,  2.0),
    "h1_ret_4bar":   (-20.0, 20.0),
    "d_ret":         (-40.0, 40.0),
    "ema20_1h_dist": (-0.15, 0.15),
    "rsi14":         (35.0,  65.0),
}


def _load_cal() -> dict:
    global _CAL
    if not _CAL and _CAL_PATH.exists():
        _CAL = json.loads(_CAL_PATH.read_text())
    return _CAL


def _read_label(norm: float) -> str:
    """Translate a [-1,+1] normalized score into a human-readable direction label."""
    if norm >  0.70: return "strong_long"
    if norm >  0.30: return "mild_long"
    if norm > -0.30: return "neutral"
    if norm > -0.70: return "mild_short"
    return "strong_short"


class DirectionModule:
    """Translates raw market indicators into a directional read for this pair/session."""

    def __init__(self, pair: str, session: str):
        self.pair    = pair
        self.session = session
        self._anchors: dict[str, tuple[float, float]] = {}
        self._load_anchors()

    def _load_anchors(self) -> None:
        cal = _load_cal()
        curves = cal.get(self.pair, {}).get(self.session, {}).get("curves", {})
        for field_name, _ in _FACTORS:
            sweep_key = _SWEEP_KEY.get(field_name, field_name)
            c = curves.get(sweep_key)
            if c and "D1" in c and "D10" in c:
                lo = float(c["D1"]["hi_val"])    # D1/D2 boundary
                hi = float(c["D10"]["lo_val"])   # D9/D10 boundary
                if lo < hi:
                    self._anchors[field_name] = (lo, hi)
                    continue
            self._anchors[field_name] = _FALLBACK[field_name]

    def _norm(self, v: float, feat: str) -> float:
        lo, hi = self._anchors[feat]
        if hi == lo:
            return 0.0
        return float(np.clip((v - lo) / (hi - lo) * 2 - 1, -1, 1))

    def _get_value(self, view: MarketView, feat: str) -> float:
        return float(getattr(view, feat))

    def stamp(self, view: MarketView) -> DirectionStamp:
        """Translate all 7 direction factors and produce a stamped DirectionStamp."""
        norms: list[tuple[str, float, float]] = []  # (feat, norm, weight)
        for feat, weight in _FACTORS:
            v = self._get_value(view, feat)
            n = self._norm(v, feat)
            norms.append((feat, n, weight))

        # Weighted composite score
        score = float(np.clip(
            sum(n * w for _, n, w in norms),
            -1.0, 1.0
        ))

        # Factor extremity: how far each factor departs from neutral (0..1)
        extremity = sum(abs(n) * w for _, n, w in norms)  # weighted, 0..1

        # Factor agreement: fraction of weight aligned with composite direction
        sig = np.sign(score)
        if abs(score) > 0.05 and sig != 0:
            agree_w = sum(w for _, n, w in norms if abs(n) > 0.1 and np.sign(n) == sig)
            total_w = sum(w for _, n, w in norms if abs(n) > 0.1)
            agreement = agree_w / total_w if total_w > 0 else 0.5
        else:
            agreement = 0.5

        # Certainty combines extremity and agreement
        certainty = float(np.clip(extremity * (0.4 + 0.6 * agreement), 0.0, 1.0))

        bias = "block"
        if score > 0.15:
            bias = "long"
        elif score < -0.15:
            bias = "short"

        # Build per-factor reads
        reads = {feat: _read_label(n) for feat, n, _ in norms}
        aligned = sum(1 for _, n, _ in norms if abs(n) > 0.1 and np.sign(n) == sig)
        meaningful = sum(1 for _, n, _ in norms if abs(n) > 0.1)
        reads["agreement"] = f"{aligned}/{meaningful} factors aligned"
        reads["cal"] = f"{self.pair}/{self.session} D1/D2:{self._anchors['h1_ret_1bar'][0]:.1f}p D9/D10:{self._anchors['h1_ret_1bar'][1]:.1f}p"

        return DirectionStamp(
            pair=self.pair, session=self.session, timestamp=view.timestamp,
            bias=bias, score=round(score, 4), certainty=round(certainty, 4),
            reads=reads,
        )


def build_direction_modules(pairs: list[str], sessions: list[str]) -> dict[tuple[str,str], DirectionModule]:
    """Build one DirectionModule per (pair × session) bucket at startup."""
    return {(p, s): DirectionModule(p, s) for p in pairs for s in sessions}
