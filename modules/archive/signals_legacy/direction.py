"""modules/signals/direction.py — Per-(pair × session) direction module.

All 24 features with meaningful direction signal from the dm_04 raw net_60m sweep
(|span| ≥ 0.27p median across 24 pair×session buckets). Weights are derived directly
from those spans so each indicator's score share equals its empirical predictive power.

Continuation signals (positive spans → positive signed weights):
  h1_ret_1bar       +17.61p   rsi_slope         +10.41p   zscore_1h          +8.73p
  h1_ret_4bar        +7.35p   d_ret              +7.09p   ema20_1h_dist_pct  +6.37p
  pdh_dist_pips      +5.95p   pdl_dist_pips      +5.88p   pdl_dist_atr_pct   +5.69p
  pdh_dist_atr_pct   +5.62p   rsi14              +4.79p   htf_pct_20         +1.91p
  htf_pct_60         +1.01p

Mean-reversion signals (negative spans → negative signed weights):
  ema20_dist_pct     -0.57p   bb_pos             -0.55p   zscore_5m          -0.55p
  ema5_dist_pips     -0.53p   ret_5m             -0.50p   ret_15m            -0.45p
  ret_1h             -0.44p   ret_30m            -0.41p   ema50_dist_pct     -0.39p
  close_pos_daily    -0.30p   ema_cross_pips     -0.27p

Normalization per (pair × session): D1.hi_val (D1/D2 boundary) → D10.lo_val (D9/D10
boundary) from factor_sweep.json. Value below lo clips to -1 (D1 territory),
above hi clips to +1 (D10 territory).

Certainty = factor extremity × (0.4 + 0.6 × agreement_fraction).
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from modules.signals.base import MarketView, DirectionStamp

_CAL_PATH = Path(__file__).parent / "factor_sweep.json"
_CAL: dict = {}

# (MarketView_field, sweep_key, raw_span_pips)
# Positive span → continuation signal (high feature value = bullish)
# Negative span → mean-reversion signal (high feature value = bearish)
_FACTOR_DEFS: list[tuple[str, str, float]] = [
    # ── Continuation ──────────────────────────────────────────────────────
    ("h1_ret_1bar",       "h1_ret_1bar",       +17.61),
    ("rsi_slope",         "rsi_slope",          +10.41),
    ("zscore_1h",         "zscore_1h",           +8.73),
    ("h1_ret_4bar",       "h1_ret_4bar",          +7.35),
    ("d_ret",             "d_ret",                +7.09),
    ("ema20_1h_dist",     "ema20_1h_dist_pct",    +6.37),
    ("pdh_dist",          "pdh_dist_pips",         +5.95),
    ("pdl_dist",          "pdl_dist_pips",         +5.88),
    ("pdl_dist_atr_pct",  "pdl_dist_atr_pct",     +5.69),
    ("pdh_dist_atr_pct",  "pdh_dist_atr_pct",     +5.62),
    ("rsi14",             "rsi14",                +4.79),
    ("htf_pct_20",        "htf_pct_20",            +1.91),
    ("htf_pct_60",        "htf_pct_60",            +1.01),
    # ── Mean-reversion ────────────────────────────────────────────────────
    ("ema20_dist_pct",    "ema20_dist_pct",        -0.57),
    ("bb_pos",            "bb_pos",                -0.55),
    ("zscore_5m",         "zscore_5m",             -0.55),
    ("ema5_dist_pips",    "ema5_dist_pips",         -0.53),
    ("ret_5m",            "ret_5m",                -0.50),
    ("ret_15m",           "ret_15m",               -0.45),
    ("ret_1h",            "ret_1h",                -0.44),
    ("ret_30m",           "ret_30m",               -0.41),
    ("ema50_dist_pct",    "ema50_dist_pct",         -0.39),
    ("close_pos_daily",   "close_pos_daily",        -0.30),
    ("ema_cross_pips",    "ema_cross_pips",         -0.27),
]

# Signed weights: span / total_abs_span → each factor's share = |span| / total
_TOTAL_ABS = sum(abs(s) for _, _, s in _FACTOR_DEFS)
_FACTORS: list[tuple[str, str, float]] = [
    (field, key, span / _TOTAL_ABS)
    for field, key, span in _FACTOR_DEFS
]

# Conservative fallback D1/D10 anchors when calibration is missing
_FALLBACK: dict[str, tuple[float, float]] = {
    "h1_ret_1bar":      (-12.0,  12.0),
    "rsi_slope":        ( -9.0,   9.0),
    "zscore_1h":        ( -2.0,   2.0),
    "h1_ret_4bar":      (-20.0,  20.0),
    "d_ret":            (-40.0,  40.0),
    "ema20_1h_dist":    ( -0.15,  0.15),
    "pdh_dist":         (-20.0,  20.0),
    "pdl_dist":         (-20.0,  20.0),
    "pdh_dist_atr_pct": ( -3.0,   3.0),
    "pdl_dist_atr_pct": ( -3.0,   3.0),
    "rsi14":            ( 35.0,  65.0),
    "htf_pct_20":       ( -3.0,   3.0),
    "htf_pct_60":       ( -3.0,   3.0),
    "ema20_dist_pct":   ( -0.10,  0.10),
    "bb_pos":           (  0.1,   0.9),
    "zscore_5m":        ( -2.0,   2.0),
    "ema5_dist_pips":   ( -5.0,   5.0),
    "ret_5m":           ( -3.0,   3.0),
    "ret_15m":          ( -5.0,   5.0),
    "ret_30m":          ( -8.0,   8.0),
    "ret_1h":           (-12.0,  12.0),
    "ema50_dist_pct":   ( -0.20,  0.20),
    "close_pos_daily":  (  0.1,   0.9),
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
    """Translates all 24 direction indicators into a stamped directional read."""

    def __init__(self, pair: str, session: str):
        self.pair    = pair
        self.session = session
        self._anchors: dict[str, tuple[float, float]] = {}
        self._load_anchors()

    def _load_anchors(self) -> None:
        cal    = _load_cal()
        curves = cal.get(self.pair, {}).get(self.session, {}).get("curves", {})
        for field_name, sweep_key, _ in _FACTOR_DEFS:
            c = curves.get(sweep_key)
            if c and "D1" in c and "D10" in c:
                try:
                    lo = float(c["D1"]["hi_val"])
                    hi = float(c["D10"]["lo_val"])
                    if lo < hi:
                        self._anchors[field_name] = (lo, hi)
                        continue
                except (KeyError, TypeError, ValueError):
                    pass
            self._anchors[field_name] = _FALLBACK[field_name]

    def _norm(self, v: float, field: str) -> float:
        lo, hi = self._anchors[field]
        if hi == lo:
            return 0.0
        return float(np.clip((v - lo) / (hi - lo) * 2 - 1, -1, 1))

    def stamp(self, view: MarketView) -> DirectionStamp:
        """Translate all 24 direction factors; return a stamped DirectionStamp."""
        norms: list[tuple[str, float, float]] = []  # (field, norm, signed_weight)
        for field_name, _, signed_w in _FACTORS:
            v    = float(getattr(view, field_name, 0.0))
            n    = self._norm(v, field_name)
            norms.append((field_name, n, signed_w))

        # Composite: sum(signed_weight × norm)
        # Max = +1 when all continuation at D10 AND all reversion at D1 (not extended)
        score = float(np.clip(sum(n * w for _, n, w in norms), -1.0, 1.0))

        # Extremity: weighted average of |contribution| per factor
        extremity = sum(abs(n * w) for _, n, w in norms)

        # Agreement: fraction of (abs) weight where the factor's contribution
        # aligns with the composite direction
        sig = np.sign(score)
        if abs(score) > 0.05 and sig != 0:
            active = [(field, n * w) for field, n, w in norms if abs(n * w) > 0.002]
            if active:
                agree  = sum(abs(c) for _, c in active if np.sign(c) == sig)
                total  = sum(abs(c) for _, c in active)
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

        # Per-factor reads (use norm for continuation; for reversion, flip the label)
        reads = {}
        for field_name, n, signed_w in norms:
            if signed_w < 0:
                # Reversion feature: positive norm = bearish signal → flip label
                reads[field_name] = _read_label(-n)
            else:
                reads[field_name] = _read_label(n)

        aligned_w   = sum(abs(n * w) for _, n, w in norms if abs(n * w) > 0.002 and np.sign(n * w) == sig)
        total_act_w = sum(abs(n * w) for _, n, w in norms if abs(n * w) > 0.002)
        reads["agreement"] = f"{aligned_w / total_act_w * 100:.0f}% weight aligned" if total_act_w > 0 else "—"
        reads["cal"] = (f"{self.pair}/{self.session} "
                        f"h1:{self._anchors['h1_ret_1bar'][0]:.1f}..{self._anchors['h1_ret_1bar'][1]:.1f}p")

        return DirectionStamp(
            pair=self.pair, session=self.session, timestamp=view.timestamp,
            bias=bias, score=round(score, 4), certainty=round(certainty, 4),
            reads=reads,
        )


def build_direction_modules(pairs: list[str], sessions: list[str]) -> dict[tuple[str,str], "DirectionModule"]:
    return {(p, s): DirectionModule(p, s) for p in pairs for s in sessions}
