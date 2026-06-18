"""modules/signals/momentum.py — Per-(pair × session) momentum module.

10 vol/magnitude features — all have near-zero direction span in the dm_04 raw
sweep, meaning they do not predict which way price moves, but DO describe current
market conditions relevant to expected move magnitude.

  atr_5m        +0.05p dir span    rvol_5bar    +0.07p    atr_1h      +0.10p
  rvol_12bar    +0.00p             bb_width     +0.12p    range_5bar  -0.11p
  range_12bar   -0.14p             atr_d_pips   +0.17p    d_range_pips -0.12p
  adr_consumed  -0.52p (direction-conditional; carried as context, not direction signal)

Vol regime thresholds from per-(pair × session) ATR_5m D2.hi (low boundary) and
D8.hi (high boundary) from factor_sweep.json.

expected_pips = atr_1h × rvol_factor
  (atr_1h is the actual 1H ATR; rvol_factor scales by current volume activity)

Certainty = how definitively ATR is in one regime, boosted when rvol agrees.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from .base import MarketView, MomentumStamp

_CAL_PATH = Path(__file__).parent / "factor_sweep.json"
_CAL: dict = {}

_FALLBACK_LOW  = 3.0
_FALLBACK_HIGH = 6.0
_FALLBACK_EXT  = 10.0


def _load_cal() -> dict:
    global _CAL
    if not _CAL and _CAL_PATH.exists():
        _CAL = json.loads(_CAL_PATH.read_text())
    return _CAL


class MomentumModule:
    """Translates raw vol/activity indicators into a magnitude stamp."""

    def __init__(self, pair: str, session: str):
        self.pair    = pair
        self.session = session
        self._thr_low:  float = _FALLBACK_LOW
        self._thr_high: float = _FALLBACK_HIGH
        self._thr_ext:  float = _FALLBACK_EXT
        self._d5_mid:   float = 0.0
        self._load_thresholds()

    def _load_thresholds(self) -> None:
        c = (_load_cal()
             .get(self.pair, {})
             .get(self.session, {})
             .get("curves", {})
             .get("atr_5m", {}))
        if c and all(k in c for k in ("D2", "D5", "D8", "D9")):
            self._thr_low  = float(c["D2"]["hi_val"])
            self._thr_high = float(c["D8"]["hi_val"])
            self._thr_ext  = float(c["D9"]["hi_val"])
            self._d5_mid   = (float(c["D5"]["lo_val"]) + float(c["D5"]["hi_val"])) / 2

    def _vol_regime(self, atr_5m: float) -> str:
        if atr_5m >= self._thr_ext:  return "extreme"
        if atr_5m >= self._thr_high: return "high"
        if atr_5m >= self._thr_low:  return "normal"
        return "low"

    def _regime_certainty(self, atr_5m: float, regime: str, rvol: float) -> float:
        if regime == "extreme":
            raw = min((atr_5m - self._thr_ext) / max(self._thr_ext, 0.001) + 0.5, 1.0)
        elif regime == "high":
            span = max(self._thr_ext - self._thr_high, 0.001)
            raw  = (atr_5m - self._thr_high) / span
        elif regime == "low":
            raw  = 1.0 - (atr_5m / max(self._thr_low, 0.001))
        else:
            dist = (atr_5m - self._thr_low) / max(self._thr_high - self._thr_low, 0.001)
            raw  = abs(dist - 0.5) * 2
        c = float(np.clip(raw, 0.0, 1.0))
        if regime in ("high", "extreme") and rvol > 1.25: c = min(c * 1.2, 1.0)
        elif regime == "low" and rvol < 0.75:              c = min(c * 1.2, 1.0)
        return round(c, 4)

    def _rvol_read(self, rvol: float) -> str:
        if rvol > 1.8:  return "very_elevated"
        if rvol > 1.2:  return "elevated"
        if rvol > 0.8:  return "normal"
        if rvol > 0.4:  return "subdued"
        return "very_subdued"

    def _adr_context(self, adr: float) -> str:
        if adr < 0.25: return "fresh"
        if adr < 0.55: return "midfield"
        if adr < 0.80: return "extended"
        return "exhausted"

    def _range_read(self, r5: float, r12: float) -> str:
        """Relative range expansion: r12/r5 — is range growing or contracting?"""
        if r5 <= 0 or r12 <= 0: return "—"
        ratio = r12 / r5
        if ratio > 2.0:  return "expanding"
        if ratio > 1.2:  return "slightly_expanding"
        if ratio > 0.8:  return "stable"
        return "contracting"

    def stamp(self, view: MarketView) -> MomentumStamp:
        regime        = self._vol_regime(view.atr_5m)
        rvol_combined = (view.rvol_5bar + view.rvol_12bar) / 2
        rvol_factor   = float(np.clip(rvol_combined, 0.6, 1.6))
        expected_pips = round(view.atr_1h * rvol_factor, 2)
        certainty     = self._regime_certainty(view.atr_5m, regime, rvol_combined)

        reads = {
            "atr_5m":       regime,
            "atr_1h":       f"{view.atr_1h:.1f}p",
            "rvol_5bar":    self._rvol_read(view.rvol_5bar),
            "rvol_12bar":   self._rvol_read(view.rvol_12bar),
            "bb_width":     f"{view.bb_width:.1f}p" if view.bb_width > 0 else "—",
            "range_trend":  self._range_read(view.range_5bar, view.range_12bar),
            "adr_context":  self._adr_context(view.adr_consumed),
            "expected_1h":  f"{expected_pips:.1f}p",
            "cal":          f"{self.pair}/{self.session} low<{self._thr_low:.1f}p high>{self._thr_high:.1f}p",
        }

        return MomentumStamp(
            pair=self.pair, session=self.session, timestamp=view.timestamp,
            vol_regime=regime, expected_pips=expected_pips,
            certainty=certainty, reads=reads,
        )


def build_momentum_modules(pairs: list[str], sessions: list[str]) -> dict[tuple[str,str], "MomentumModule"]:
    return {(p, s): MomentumModule(p, s) for p in pairs for s in sessions}
