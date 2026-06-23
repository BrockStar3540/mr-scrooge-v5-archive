"""modules/signals/direction_v2.py — Per-(pair × session × direction) direction module v2.

Drop-in alongside V5's existing modules/signals/direction.py. Architecture:
  1. Each (pair × session) cell has TWO profiles loaded at __init__ — one for
     long-side evaluation and one for short-side. They may be the same.
  2. stamp(view) computes BOTH scores using their respective profile weights,
     picks whichever has stronger |score| as the final direction.
  3. Aggregator rules (atr_conc HIGH → boost HTF; atr_h1_relative HIGH →
     boost reversion) apply to both profiles symmetrically.
  4. The DirectionStamp shape is unchanged so the playmaker doesn't change.

Why dual-compute instead of "pick profile then evaluate":
  The dual-compute path doesn't bias toward one direction. If short_profile
  yields a more confident signal than long_profile, the short setup wins —
  even if V5's v1 raw signal would have nominally pointed long. This makes
  per-direction profile assignments genuinely two-sided.
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
    from base import MarketView, DirectionStamp  # type: ignore
    from direction_profiles import (              # type: ignore
        get_factor_defs, get_profile_info, apply_aggregator_rules,
    )

_CAL_PATH = Path(__file__).parent / "factor_sweep.json"
_CAL: dict = {}

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
    # 2026-06-23 soft wire: willr_m5 range -85..-15 maps to norm -1..+1.
    # willr -85 (extreme oversold) → norm -1; willr -15 (extreme overbought) → norm +1.
    "willr_m5":         (-85.0, -15.0),
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


def _normalize_weights(factor_defs: list[tuple[str, float]]) -> dict[str, float]:
    total_abs = sum(abs(s) for _, s in factor_defs) or 1.0
    return {f: s / total_abs for f, s in factor_defs}


class DirectionModule:
    """Per-(pair × session × direction) direction module v2."""

    def __init__(self, pair: str, session: str):
        self.pair = pair
        self.session = session
        # === Load TWO profiles — one per direction ===
        self._long_defs   = get_factor_defs(pair, session, "long")
        self._short_defs  = get_factor_defs(pair, session, "short")
        self.long_profile,  self.long_evidence  = get_profile_info(pair, session, "long")
        self.short_profile, self.short_evidence = get_profile_info(pair, session, "short")
        # Normalize each
        self._long_base   = _normalize_weights(self._long_defs)
        self._short_base  = _normalize_weights(self._short_defs)
        # Union of features for anchor lookup
        feat_union = set(f for f, _ in self._long_defs) | set(f for f, _ in self._short_defs)
        self._feature_list = sorted(feat_union)
        # Load D1/D10 anchors (one per feature, per cell — same for both directions)
        self._anchors: dict[str, tuple[float, float]] = {}
        self._load_anchors()

    def _load_anchors(self) -> None:
        cal = _load_cal()
        curves = cal.get(self.pair, {}).get(self.session, {}).get("curves", {})
        for fname in self._feature_list:
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

    def _compute_pass(self, view: MarketView, base_weights: dict[str, float],
                       factor_defs: list[tuple[str, float]]) -> tuple[float, float, list[tuple[str, float, float]]]:
        """Compute (score, extremity, norms_breakdown) using one profile's weights."""
        weights = apply_aggregator_rules(base_weights, view)
        total_abs = sum(abs(w) for w in weights.values()) or 1.0
        weights = {f: w / total_abs for f, w in weights.items()}
        norms: list[tuple[str, float, float]] = []
        for fname, _ in factor_defs:
            v = float(getattr(view, fname, 0.0))
            n = self._norm(v, fname)
            w = weights[fname]
            norms.append((fname, n, w))
        score = float(np.clip(sum(n * w for _, n, w in norms), -1.0, 1.0))
        extremity = sum(abs(n * w) for _, n, w in norms)
        return score, extremity, norms

    def stamp(self, view: MarketView) -> DirectionStamp:
        # === Dual-compute: long perspective + short perspective ===
        long_score, long_extr, long_norms = self._compute_pass(view, self._long_base, self._long_defs)
        short_score, short_extr, short_norms = self._compute_pass(view, self._short_base, self._short_defs)

        # Pick the more confident perspective by |score|
        if abs(long_score) >= abs(short_score):
            final_score = long_score
            final_extr  = long_extr
            final_norms = long_norms
            active_profile  = self.long_profile
            active_evidence = self.long_evidence
            active_side     = "long_profile"
        else:
            final_score = short_score
            final_extr  = short_extr
            final_norms = short_norms
            active_profile  = self.short_profile
            active_evidence = self.short_evidence
            active_side     = "short_profile"

        # Compute certainty (agreement-weighted extremity, V5 v1 style)
        sig = np.sign(final_score)
        if abs(final_score) > 0.05 and sig != 0:
            active = [(f, n * w) for f, n, w in final_norms if abs(n * w) > 0.002]
            if active:
                agree = sum(abs(c) for _, c in active if np.sign(c) == sig)
                total = sum(abs(c) for _, c in active)
                agreement = agree / total if total > 0 else 0.5
            else:
                agreement = 0.5
        else:
            agreement = 0.5
        certainty = float(np.clip(final_extr * (0.4 + 0.6 * agreement), 0.0, 1.0))

        # Determine bias from final sign
        bias = "block"
        if final_score > 0.15:
            bias = "long"
        elif final_score < -0.15:
            bias = "short"

        reads: dict = {}
        for fname, n, w in final_norms:
            reads[fname] = _read_label(-n) if w < 0 else _read_label(n)
        aligned_w = sum(abs(n * w) for _, n, w in final_norms
                       if abs(n * w) > 0.002 and np.sign(n * w) == sig)
        total_act_w = sum(abs(n * w) for _, n, w in final_norms if abs(n * w) > 0.002)
        reads["agreement"] = (f"{aligned_w / total_act_w * 100:.0f}% weight aligned"
                              if total_act_w > 0 else "—")
        reads["cal"] = f"{self.pair}/{self.session}/{bias} profile={active_profile} (v2 dual)"
        reads["profile_evidence"] = active_evidence
        reads["active_side"]      = active_side
        reads["long_score"]       = round(long_score, 4)
        reads["short_score"]      = round(short_score, 4)
        reads["long_profile"]     = f"{self.long_profile} [{self.long_evidence}]"
        reads["short_profile"]    = f"{self.short_profile} [{self.short_evidence}]"

        return DirectionStamp(
            pair=self.pair, session=self.session,
            timestamp=view.timestamp,
            bias=bias, score=final_score, certainty=certainty, reads=reads,
        )


def build_direction_modules(pairs: list[str], sessions: list[str]) -> dict[tuple[str, str], "DirectionModule"]:
    return {(p, s): DirectionModule(p, s) for p in pairs for s in sessions}
