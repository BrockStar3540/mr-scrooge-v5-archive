"""modules/signals/momentum_v3.py — Per-(pair × session) momentum module v3.

Drop-in alongside V5's existing momentum.py and momentum_v2.py. Loads
pair-specific profile assignment + per-pair tuning from momentum_profiles.

Architecture mirrors direction_v2 — each pair × session cell gets a profile
that encodes which momentum signals to gate on, and a strictness multiplier
based on live trade evidence. 12 cells stay on "default" (V5 v1 behavior
unchanged → zero regression risk in unseen cells).

Behavioral differences from v2:
  1. expected_pips scaler is PER-PAIR (was global 0.30 in v2)
  2. Profile-specific gate stack — m_cert is set to 0.0 when profile gates
     fail, so the existing playmaker min_mom_certainty floor REJECTS the
     entry without needing playmaker changes
  3. Reads include the profile name + reason list for live debugging
  4. V5's atr_5m vol_regime classification is KEPT (works fine)
  5. V5's atr_conc as chaos-block STILL applies as a hard veto
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

try:
    from .base import MarketView, MomentumStamp
except ImportError:
    from base import MarketView, MomentumStamp  # type: ignore

try:
    from .momentum_profiles import (
        PROFILE_ASSIGNMENT, PAIR_TUNING, EVIDENCE_STRICTNESS,
        PROFILE_TEMPLATES, evaluate_cell,
    )
except ImportError:
    from momentum_profiles import (  # type: ignore
        PROFILE_ASSIGNMENT, PAIR_TUNING, EVIDENCE_STRICTNESS,
        PROFILE_TEMPLATES, evaluate_cell,
    )

_CAL_PATH = Path(__file__).parent / "factor_sweep.json"
_CAL: dict = {}

_FALLBACK_LOW  = 3.0
_FALLBACK_HIGH = 6.0
_FALLBACK_EXT  = 10.0

# atr_conc hard chaos veto — applies REGARDLESS of profile. Inherited from v1.
ATR_CONC_CHAOS_CEILING = 15.0
# wall_frac gentle amplifier on expected_pips (kept from v2)
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
        # Lookup per-cell profile + per-pair tuning at construction
        self.profile_name, self.evidence = PROFILE_ASSIGNMENT.get(
            (pair, session), ("default", "NO_DATA"))
        self.tuning = PAIR_TUNING.get(pair, PAIR_TUNING["EUR_USD"]).copy()
        self.strictness = EVIDENCE_STRICTNESS[self.evidence]
        self.profile_fn = PROFILE_TEMPLATES[self.profile_name]
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

    def stamp(self, view: MarketView) -> MomentumStamp:
        # === Base V5 v1 calculations ===
        regime        = self._vol_regime(view.atr_5m)
        rvol_combined = (view.rvol_5bar + view.rvol_12bar) / 2
        rvol_factor   = float(np.clip(rvol_combined, 0.6, 1.6))
        raw_expected = view.atr_1h * rvol_factor

        # === Per-pair expected_pips scaler ===
        base_scaler = self.tuning["expected_pips_scaler"]

        # === Profile evaluation ===
        evaluation = evaluate_cell(self.pair, self.session, view)
        gates_passed = evaluation["gates_passed"]
        cert_boost   = evaluation["cert_boost"]
        scaler_mult  = evaluation["scaler_mult"]

        # === atr_conc chaos veto (hard, applies regardless of profile) ===
        atr_conc = getattr(view, "atr_conc", 0.0) or 0.0
        chaos_veto = atr_conc >= ATR_CONC_CHAOS_CEILING

        # === Final expected_pips ===
        scaler = base_scaler * scaler_mult
        scaled_expected = raw_expected * scaler
        wall_frac = self._wall_frac(view)
        if wall_frac > WALL_FRAC_AMP_THRESHOLD and gates_passed:
            scaled_expected *= WALL_FRAC_AMP_MULT
        expected_pips = round(float(scaled_expected), 2)

        # === Certainty ===
        # V5 v1 baseline regime certainty
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

        # Apply profile cert_boost (0.0 if gates fail = playmaker rejects entry)
        # Veto trumps boost.
        final_cert = 0.0 if chaos_veto else float(np.clip(base_cert * cert_boost, 0.0, 1.0))

        # === Reads (rich debug payload) ===
        reads = {
            "atr_5m":          regime,
            "atr_1h":          f"{view.atr_1h:.1f}p",
            "atr_conc":        f"{atr_conc:.2f}{' [CHAOS VETO]' if chaos_veto else ''}",
            "wall_frac":       f"{wall_frac:.2f}{' [amp-active]' if wall_frac > WALL_FRAC_AMP_THRESHOLD and gates_passed else ''}",
            "raw_expected":    f"{raw_expected:.1f}p (scaler={scaler:.3f})",
            "expected_pips":   f"{expected_pips:.1f}p",
            "profile":         f"{self.profile_name} [{self.evidence}, strictness={self.strictness:.2f}]",
            "gates_passed":    gates_passed,
            "cert_boost":      f"{cert_boost:.2f}",
            "profile_reasons": " | ".join(evaluation["reasons"]),
            "pair_tuning":     f"atr_d_typ={self.tuning['atr_d_typical_pips']}p, "
                                f"h1_floor={self.tuning['h1_ret_floor_pips']*self.strictness:.1f}p, "
                                f"rvol_floor={self.tuning['rvol_floor']*self.strictness:.2f}",
        }
        return MomentumStamp(
            pair=self.pair, session=self.session, timestamp=view.timestamp,
            vol_regime=regime, expected_pips=expected_pips,
            certainty=round(final_cert, 4), reads=reads,
        )


def build_momentum_modules(pairs: list[str], sessions: list[str]) -> dict[tuple[str, str], "MomentumModule"]:
    """Factory — instantiate one MomentumModule per (pair, session) cell."""
    return {(p, s): MomentumModule(p, s) for p in pairs for s in sessions}
