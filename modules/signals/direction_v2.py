"""modules/signals/direction_v2.py — Per-(pair × session) direction module v2.

This is a drop-in alongside V5's existing modules/signals/direction.py. It:
  1. Loads per-(pair × session) weight profiles from direction_profiles.py
  2. Keeps V5's per-(pair × session) D1/D10 anchors from factor_sweep.json
     for normalization (unchanged from v1)
  3. Applies aggregator-amplifier rules conditionally (atr_conc HIGH → boost
     HTF; atr_h1_relative HIGH → boost reversion, suppress HTF)
  4. Stamps DirectionStamp with same shape as v1 so the playmaker doesn't
     need to change

USAGE:
    from modules.signals.direction_v2 import DirectionModule as DirectionModuleV2
  Then in engine.py, swap:
    DirectionModule(pair, session) → DirectionModuleV2(pair, session)
  Or run BOTH in parallel and log both scores for shadow-mode A/B comparison.

The MarketView shape is unchanged. This module only needs:
  - the V5 direction features (24 of them, as before)
  - aggregator features (atr_conc, atr_h1_relative) for rule conditions —
    add these to MarketView if not present, see expand_view() helper
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

try:
    from .base import MarketView, DirectionStamp
    from .direction_profiles import (
        get_factor_defs, get_profile_info, apply_aggregator_rules,
    )
except ImportError:
    # standalone-test fallback
    from base import MarketView, DirectionStamp  # type: ignore
    from direction_profiles import (              # type: ignore
        get_factor_defs, get_profile_info, apply_aggregator_rules,
    )

_CAL_PATH = Path(__file__).parent / "factor_sweep.json"
_CAL: dict = {}

# Fallback D1/D10 anchors per feature (matches v1)
_FALLBACK: dict[str, tuple[float, float]] = {
    "h1_ret_1bar":      (-12.0,  12.0),  "rsi_slope":         ( -9.0,  9.0),
    "zscore_1h":        ( -2.0,   2.0),  "h1_ret_4bar":       (-20.0, 20.0),
    "d_ret":            (-40.0,  40.0),  "ema20_1h_dist_pct": ( -0.15, 0.15),
    "pdh_dist_pips":    (-20.0,  20.0),  "pdl_dist_pips":     (-20.0, 20.0),
    "pdh_dist_atr_pct": ( -3.0,   3.0),  "pdl_dist_atr_pct":  ( -3.0,  3.0),
    "rsi14":            ( 35.0,  65.0),  "htf_pct_20":        ( -3.0,  3.0),
    "htf_pct_60":       ( -3.0,   3.0),
    "ema20_dist_pct":   ( -0.10,  0.10), "bb_pos":            (  0.1,  0.9),
    "zscore_5m":        ( -2.0,   2.0),  "ema5_dist_pips":    ( -5.0,  5.0),
    "ret_5m":           ( -3.0,   3.0),  "ret_15m":           ( -5.0,  5.0),
    "ret_30m":          ( -8.0,   8.0),  "ret_1h":            (-12.0, 12.0),
    "ema50_dist_pct":   ( -0.20,  0.20), "close_pos_daily":   (  0.1,  0.9),
    "ema_cross_pips":   ( -3.0,   3.0),
}


def _load_cal() -> dict:
    global _CAL
    if not _CAL and _CAL_PATH.exists():
        _CAL = json.loads(_CAL_PATH.read_text())
    return _CAL


def _read_label(norm: float) -> str:
    if norm >  0.70: return "strong_long"
    if norm >  0.30: return "mild_long"
    if norm > -0.30: return "neutral"
    if norm > -0.70: return "mild_short"
    return "strong_short"


class DirectionModule:
    """Per-(pair × session) direction module v2 — profile-driven weights."""

    def __init__(self, pair: str, session: str):
        self.pair = pair
        self.session = session
        # Load profile assignment + factor defs
        self._factor_defs = get_factor_defs(pair, session)
        self.profile_name, self.evidence_level = get_profile_info(pair, session)
        # Normalize signed weights
        total_abs = sum(abs(s) for _, s in self._factor_defs) or 1.0
        self._base_weights: dict[str, float] = {
            f: s / total_abs for f, s in self._factor_defs
        }
        # Per-cell D1/D10 anchors
        self._anchors: dict[str, tuple[float, float]] = {}
        self._load_anchors()

    def _load_anchors(self) -> None:
        cal = _load_cal()
        curves = cal.get(self.pair, {}).get(self.session, {}).get("curves", {})
        for fname, _ in self._factor_defs:
            c = curves.get(fname)
            if c and "D1" in c and "D10" in c:
                try:
                    lo = float(c["D1"]["hi_val"])
                    hi = float(c["D10"]["lo_val"])
                    if lo < hi:
                        self._anchors[fname] = (lo, hi)
                        continue
                except (KeyError, TypeError, ValueError):
                    pass
            self._anchors[fname] = _FALLBACK.get(fname, (-1.0, 1.0))

    def _norm(self, v: float, fname: str) -> float:
        lo, hi = self._anchors[fname]
        if hi == lo:
            return 0.0
        return float(np.clip((v - lo) / (hi - lo) * 2 - 1, -1, 1))

    def stamp(self, view: MarketView) -> DirectionStamp:
        # Apply aggregator amplifier rules — produces a new weights dict
        weights = apply_aggregator_rules(self._base_weights, view)
        # Re-normalize after rules so |total| sums to 1 again
        total_abs = sum(abs(w) for w in weights.values()) or 1.0
        weights = {f: w / total_abs for f, w in weights.items()}

        norms: list[tuple[str, float, float]] = []
        for fname, _ in self._factor_defs:
            v = float(getattr(view, fname, 0.0))
            n = self._norm(v, fname)
            w = weights[fname]
            norms.append((fname, n, w))

        score = float(np.clip(sum(n * w for _, n, w in norms), -1.0, 1.0))
        extremity = sum(abs(n * w) for _, n, w in norms)
        sig = np.sign(score)
        if abs(score) > 0.05 and sig != 0:
            active = [(f, n * w) for f, n, w in norms if abs(n * w) > 0.002]
            if active:
                agree = sum(abs(c) for _, c in active if np.sign(c) == sig)
                total = sum(abs(c) for _, c in active)
                agreement = agree / total if total > 0 else 0.5
            else:
                agreement = 0.5
        else:
            agreement = 0.5
        certainty = float(np.clip(extremity * (0.4 + 0.6 * agreement), 0.0, 1.0))

        bias = "block"
        if score > 0.15:
            bias = "long"
        elif score < -0.15:
            bias = "short"

        reads = {}
        for fname, n, w in norms:
            reads[fname] = _read_label(-n) if w < 0 else _read_label(n)
        aligned_w   = sum(abs(n * w) for _, n, w in norms if abs(n * w) > 0.002 and np.sign(n * w) == sig)
        total_act_w = sum(abs(n * w) for _, n, w in norms if abs(n * w) > 0.002)
        reads["agreement"] = f"{aligned_w / total_act_w * 100:.0f}% weight aligned" if total_act_w > 0 else "—"
        reads["cal"] = f"{self.pair}/{self.session} profile={self.profile_name} (v2)"
        reads["profile_evidence"] = self.evidence_level

        return DirectionStamp(
            pair=self.pair, session=self.session,
            timestamp=view.timestamp,
            bias=bias, score=score, certainty=certainty, reads=reads,
        )


def build_direction_modules(pairs: list[str], sessions: list[str]) -> dict[tuple[str, str], "DirectionModule"]:
    return {(p, s): DirectionModule(p, s) for p in pairs for s in sessions}
