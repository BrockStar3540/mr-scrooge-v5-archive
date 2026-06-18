"""modules/signals/momentum.py — Per-(pair × session) momentum module.

MomentumModule is instantiated once per bucket at startup. It translates raw
volatility and activity indicators into a magnitude/regime stamp calibrated to
this pair/session's historical ATR distribution.

Vol-regime thresholds:
  low      atr_5m < D2.hi  (bottom 20% of ATR for this bucket)
  normal   D2.hi ≤ atr_5m < D8.hi  (middle 60%)
  high     D8.hi ≤ atr_5m < D9.hi  (top ~20%)
  extreme  atr_5m ≥ D9.hi  (top 10%)

Thresholds are loaded from the dm_04 factor_sweep.json curves for each
(pair × session), so 'high' for GBP_USD/london is correctly calibrated to that
pair's wider range (D8.hi≈8.3p) vs USD_CHF/ny (D8.hi≈4.7p).

expected_pips = atr_1h × rvol_factor
  atr_1h gives the actual 1-hour ATR from recent history.
  rvol_factor = clip(rvol_5bar, 0.6, 1.6) scales up or down based on current
  volume activity vs the 5-bar rolling mean.

Certainty: how definitively the ATR is in one regime vs borderline between two.
Boosted when atr_1h and rvol_5bar agree on the regime direction.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from .base import MarketView, MomentumStamp

_CAL_PATH = Path(__file__).parent / "factor_sweep.json"
_CAL: dict = {}

_FALLBACK_THRESHOLDS = {
    "low":     3.0,
    "normal":  6.0,
    "high":    10.0,
}


def _load_cal() -> dict:
    global _CAL
    if not _CAL and _CAL_PATH.exists():
        _CAL = json.loads(_CAL_PATH.read_text())
    return _CAL


class MomentumModule:
    """Translates raw vol/activity indicators into a magnitude stamp for this pair/session."""

    def __init__(self, pair: str, session: str):
        self.pair    = pair
        self.session = session
        # ATR_5m regime thresholds loaded from dm_04 distribution
        self._thr_low:  float = 0.0   # D2.hi  (bottom 20%)
        self._thr_high: float = 0.0   # D8.hi  (top ~20%)
        self._thr_ext:  float = 0.0   # D9.hi  (top 10%)
        self._d5_mid:   float = 0.0   # median ATR reference
        self._load_thresholds()

    def _load_thresholds(self) -> None:
        cal = _load_cal()
        c = cal.get(self.pair, {}).get(self.session, {}).get("curves", {}).get("atr_5m", {})
        if c and "D2" in c and "D5" in c and "D8" in c and "D9" in c:
            self._thr_low  = float(c["D2"]["hi_val"])
            self._thr_high = float(c["D8"]["hi_val"])
            self._thr_ext  = float(c["D9"]["hi_val"])
            d5 = c["D5"]
            self._d5_mid   = (float(d5["lo_val"]) + float(d5["hi_val"])) / 2
        else:
            self._thr_low  = _FALLBACK_THRESHOLDS["low"]
            self._thr_high = _FALLBACK_THRESHOLDS["normal"]
            self._thr_ext  = _FALLBACK_THRESHOLDS["high"]
            self._d5_mid   = (self._thr_low + self._thr_high) / 2

    def _vol_regime(self, atr_5m: float) -> str:
        if atr_5m >= self._thr_ext:
            return "extreme"
        if atr_5m >= self._thr_high:
            return "high"
        if atr_5m >= self._thr_low:
            return "normal"
        return "low"

    def _regime_certainty(self, atr_5m: float, regime: str, rvol: float) -> float:
        """How definitively is ATR in this regime (vs borderline between two)."""
        if regime == "extreme":
            # Distance beyond the extreme threshold as fraction of the threshold
            dist = (atr_5m - self._thr_ext) / max(self._thr_ext, 0.001)
            raw = min(dist + 0.5, 1.0)
        elif regime == "high":
            span = max(self._thr_ext - self._thr_high, 0.001)
            raw = (atr_5m - self._thr_high) / span
        elif regime == "low":
            raw = 1.0 - (atr_5m / max(self._thr_low, 0.001))
        else:  # normal
            # Closer to the middle of normal = less certain (could tip either way)
            dist_low  = (atr_5m - self._thr_low)  / max(self._thr_high - self._thr_low, 0.001)
            raw = abs(dist_low - 0.5) * 2  # 0 at center, 1 at edges

        certainty = float(np.clip(raw, 0.0, 1.0))

        # Boost if rvol_5bar agrees with the ATR regime direction
        if regime in ("high", "extreme") and rvol > 1.25:
            certainty = min(certainty * 1.2, 1.0)
        elif regime == "low" and rvol < 0.75:
            certainty = min(certainty * 1.2, 1.0)

        return round(certainty, 4)

    def _rvol_read(self, rvol: float) -> str:
        if rvol > 1.8:   return "very_elevated"
        if rvol > 1.2:   return "elevated"
        if rvol > 0.8:   return "normal"
        if rvol > 0.4:   return "subdued"
        return "very_subdued"

    def _adr_context(self, adr_consumed: float) -> str:
        if adr_consumed < 0.25:  return "fresh"
        if adr_consumed < 0.55:  return "midfield"
        if adr_consumed < 0.80:  return "extended"
        return "exhausted"

    def stamp(self, view: MarketView) -> MomentumStamp:
        """Translate vol/activity indicators and produce a stamped MomentumStamp."""
        regime = self._vol_regime(view.atr_5m)

        # expected_pips: 1H ATR scaled by current relative volume
        rvol_factor   = float(np.clip(view.rvol_5bar, 0.6, 1.6))
        expected_pips = round(view.atr_1h * rvol_factor, 2)

        certainty = self._regime_certainty(view.atr_5m, regime, view.rvol_5bar)

        reads = {
            "atr_5m":      regime,     # same classification as vol_regime
            "rvol_5bar":   self._rvol_read(view.rvol_5bar),
            "adr_context": self._adr_context(view.adr_consumed),
            "expected_1h": f"{expected_pips:.1f}p",
            "cal":         f"{self.pair}/{self.session} low<{self._thr_low:.1f}p high>{self._thr_high:.1f}p",
        }

        return MomentumStamp(
            pair=self.pair, session=self.session, timestamp=view.timestamp,
            vol_regime=regime, expected_pips=expected_pips,
            certainty=certainty, reads=reads,
        )


def build_momentum_modules(pairs: list[str], sessions: list[str]) -> dict[tuple[str,str], MomentumModule]:
    """Build one MomentumModule per (pair × session) bucket at startup."""
    return {(p, s): MomentumModule(p, s) for p in pairs for s in sessions}
