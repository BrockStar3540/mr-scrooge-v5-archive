"""modules/signals/momentum_v3.py — Per-(pair × session × direction) momentum module v3.

Drop-in alongside V5's existing momentum.py and momentum_v2.py.

stamp() now takes a `direction` argument from the caller (engine.py). The
profile lookup is on the (pair, session, direction) tuple — 48 cells total.
Cells with no live evidence fall through to "default" (V5 v1 behavior).

When activated in engine.py, the order of operations is:
  1. direction_stamp = direction_v2.stamp(view)
  2. momentum_stamp  = momentum_v3.stamp(view, direction_stamp.bias)
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

try:
    from modules.signals.base import MarketView, MomentumStamp
except ImportError:
    from base import MarketView, MomentumStamp  # type: ignore

try:
    from modules.archive.signals_legacy.momentum_profiles import (
        PROFILE_ASSIGNMENT, PAIR_TUNING, EVIDENCE_STRICTNESS,
        PROFILE_TEMPLATES, evaluate_cell, get_profile_info,
    )
except ImportError:
    from momentum_profiles import (  # type: ignore
        PROFILE_ASSIGNMENT, PAIR_TUNING, EVIDENCE_STRICTNESS,
        PROFILE_TEMPLATES, evaluate_cell, get_profile_info,
    )

_CAL_PATH = Path(__file__).parent / "factor_sweep.json"
_CAL: dict = {}

_FALLBACK_LOW  = 3.0
_FALLBACK_HIGH = 6.0
_FALLBACK_EXT  = 10.0

ATR_CONC_CHAOS_CEILING = 15.0  # INERT (2026-07-03): atr_conc = atr_5m/atr_1h ∈ (0, ~1.0) in production; ceiling 15.0 can never fire. Code path kept (harmless); re-derive threshold on clean data before re-activating.
WALL_FRAC_AMP_THRESHOLD = 5.0
WALL_FRAC_AMP_MULT      = 1.3


def _load_cal() -> dict:
    global _CAL
    if not _CAL and _CAL_PATH.exists():
        _CAL = json.loads(_CAL_PATH.read_text())
    return _CAL


class MomentumModule:
    def __init__(self, pair: str, session: str):
        self.pair = pair
        self.session = session
        self.tuning = PAIR_TUNING.get(pair, PAIR_TUNING["EUR_USD"]).copy()
        # Per-pair v5 v1 calibration for atr_5m vol regime
        self._thr_low:  float = _FALLBACK_LOW
        self._thr_high: float = _FALLBACK_HIGH
        self._thr_ext:  float = _FALLBACK_EXT
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

    def _vol_regime(self, atr_5m: float) -> str:
        if atr_5m >= self._thr_ext:  return "extreme"
        if atr_5m >= self._thr_high: return "high"
        if atr_5m >= self._thr_low:  return "normal"
        return "low"

    def _wall_frac(self, view: MarketView) -> float:
        pdh = abs(getattr(view, "pdh_dist_pips", 0.0))
        pdl = abs(getattr(view, "pdl_dist_pips", 0.0))
        atr = max(getattr(view, "atr_5m", 1.0), 0.001)
        return min(pdh, pdl) / atr

    def stamp(self, view: MarketView, direction: str = "long") -> MomentumStamp:
        """Stamp now requires `direction` from caller — determines cell profile.

        For backward compatibility, defaults to "long" if not provided. When
        engine activates v3, it should pass direction_stamp.bias.
        """
        # Validate direction (handle "block" or unknown)
        if direction not in ("long", "short"):
            direction = "long"  # safe default

        # === Per-cell profile lookup ===
        profile_name, evidence = get_profile_info(self.pair, self.session, direction)

        # === Base V5 v1 calculations ===
        regime        = self._vol_regime(view.atr_5m)
        rvol_combined = (view.rvol_5bar + view.rvol_12bar) / 2
        rvol_factor   = float(np.clip(rvol_combined, 0.6, 1.6))
        raw_expected = view.atr_1h * rvol_factor

        # === Per-pair × direction profile evaluation ===
        evaluation = evaluate_cell(self.pair, self.session, direction, view)
        gates_passed = evaluation["gates_passed"]
        cert_boost   = evaluation["cert_boost"]
        scaler_mult  = evaluation["scaler_mult"]

        # === atr_conc chaos veto (hard, applies regardless of profile) ===
        atr_conc = getattr(view, "atr_conc", 0.0) or 0.0
        chaos_veto = atr_conc >= ATR_CONC_CHAOS_CEILING

        # === Final expected_pips ===
        base_scaler = self.tuning["expected_pips_scaler"]
        scaler = base_scaler * scaler_mult
        scaled_expected = raw_expected * scaler
        wall_frac = self._wall_frac(view)
        if wall_frac > WALL_FRAC_AMP_THRESHOLD and gates_passed:
            scaled_expected *= WALL_FRAC_AMP_MULT
        expected_pips = round(float(scaled_expected), 2)

        # === Certainty ===
        if regime == "extreme":
            raw_cert = min((view.atr_5m - self._thr_ext) / max(self._thr_ext, 0.001) + 0.5, 1.0)
        elif regime == "high":
            span = max(self._thr_ext - self._thr_high, 0.001)
            raw_cert = (view.atr_5m - self._thr_high) / span
        elif regime == "low":
            raw_cert = 1.0 - (view.atr_5m / max(self._thr_low, 0.001))
        else:
            dist = (view.atr_5m - self._thr_low) / max(self._thr_high - self._thr_low, 0.001)
            raw_cert = abs(dist - 0.5) * 2
        base_cert = float(np.clip(raw_cert, 0.0, 1.0))

        final_cert = 0.0 if chaos_veto else float(np.clip(base_cert * cert_boost, 0.0, 1.0))

        reads = {
            "atr_5m":          regime,
            "atr_1h":          f"{view.atr_1h:.1f}p",
            "direction":       direction,
            "atr_conc":        f"{atr_conc:.2f}{' [CHAOS VETO]' if chaos_veto else ''}",
            "wall_frac":       f"{wall_frac:.2f}{' [amp]' if wall_frac > WALL_FRAC_AMP_THRESHOLD and gates_passed else ''}",
            "raw_expected":    f"{raw_expected:.1f}p (scaler={scaler:.3f})",
            "expected_pips":   f"{expected_pips:.1f}p",
            "profile":         f"{profile_name} [{evidence}, strictness={EVIDENCE_STRICTNESS[evidence]:.2f}]",
            "gates_passed":    gates_passed,
            "cert_boost":      f"{cert_boost:.2f}",
            "profile_reasons": " | ".join(evaluation["reasons"]),
            "pair_tuning":     f"atr_d_typ={self.tuning['atr_d_typical_pips']}p, "
                                f"h1_floor={self.tuning['h1_ret_floor_pips']*EVIDENCE_STRICTNESS[evidence]:.1f}p, "
                                f"rvol_floor={self.tuning['rvol_floor']*EVIDENCE_STRICTNESS[evidence]:.2f}",
        }
        return MomentumStamp(
            pair=self.pair, session=self.session, timestamp=view.timestamp,
            vol_regime=regime, expected_pips=expected_pips,
            certainty=round(final_cert, 4), reads=reads,
        )


def build_momentum_modules(pairs: list[str], sessions: list[str]) -> dict[tuple[str, str], "MomentumModule"]:
    return {(p, s): MomentumModule(p, s) for p in pairs for s in sessions}
