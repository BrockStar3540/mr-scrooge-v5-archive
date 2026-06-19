"""V5 per-(pair × session × direction) momentum profile assignment.

48 cells (8 pairs × 3 sessions × 2 directions). Mirrors direction_profiles
architecture.

Cells where we have evidence in one direction but not the other use the
session-shaped profile only for the evidenced direction; the other direction
falls through to "default" (V5 v1 unchanged).
"""
from __future__ import annotations

PAIR_TUNING: dict[str, dict] = {
    "AUD_JPY": dict(
        atr_d_typical_pips=75, rvol_floor=1.0, rvol_ceiling=1.5,
        h1_ret_floor_pips=2.0, atr_conc_floor=4.5,
        expected_pips_scaler=0.25, adr_consumed_ceiling=1.30,
    ),
    "AUD_USD": dict(
        atr_d_typical_pips=55, rvol_floor=1.0, rvol_ceiling=1.5,
        h1_ret_floor_pips=2.0, atr_conc_floor=4.0,
        expected_pips_scaler=0.30, adr_consumed_ceiling=1.30,
    ),
    "EUR_JPY": dict(
        atr_d_typical_pips=91, rvol_floor=1.0, rvol_ceiling=1.5,
        h1_ret_floor_pips=3.0, atr_conc_floor=5.0,
        expected_pips_scaler=0.30, adr_consumed_ceiling=1.20,
    ),
    "EUR_USD": dict(
        atr_d_typical_pips=64, rvol_floor=1.2, rvol_ceiling=1.5,
        h1_ret_floor_pips=2.5, atr_conc_floor=4.5,
        expected_pips_scaler=0.30, adr_consumed_ceiling=1.20,
    ),
    "GBP_USD": dict(
        atr_d_typical_pips=81, rvol_floor=1.0, rvol_ceiling=1.5,
        h1_ret_floor_pips=3.0, atr_conc_floor=5.0,
        expected_pips_scaler=0.35, adr_consumed_ceiling=1.20,
    ),
    "USD_CAD": dict(
        atr_d_typical_pips=60, rvol_floor=1.0, rvol_ceiling=1.5,
        h1_ret_floor_pips=2.0, atr_conc_floor=4.5,
        expected_pips_scaler=0.30, adr_consumed_ceiling=1.20,
    ),
    "USD_CHF": dict(
        atr_d_typical_pips=59, rvol_floor=1.0, rvol_ceiling=1.5,
        h1_ret_floor_pips=2.5, atr_conc_floor=4.5,
        expected_pips_scaler=0.35, adr_consumed_ceiling=1.20,
    ),
    "USD_JPY": dict(
        atr_d_typical_pips=62, rvol_floor=1.2, rvol_ceiling=1.5,
        h1_ret_floor_pips=3.0, atr_conc_floor=5.0,
        expected_pips_scaler=0.30, adr_consumed_ceiling=1.20,
    ),
}

# === (pair, session, direction) → (profile_name, evidence) — 48 cells ===
PROFILE_ASSIGNMENT: dict[tuple[str, str, str], tuple[str, str]] = {
    # AUD_JPY
    ("AUD_JPY","asia","long"):    ("default",             "NO_DATA"),
    ("AUD_JPY","asia","short"):   ("asia_volume_rev",     "STRONG"),
    ("AUD_JPY","london","long"):  ("london_exhaustion",   "BAD"),
    ("AUD_JPY","london","short"): ("default",             "WEAK"),
    ("AUD_JPY","ny","long"):      ("default",             "NO_DATA"),
    ("AUD_JPY","ny","short"):     ("default",             "NO_DATA"),
    # AUD_USD
    ("AUD_USD","asia","long"):    ("default",             "NO_DATA"),
    ("AUD_USD","asia","short"):   ("asia_volume_rev",     "MEDIUM"),
    ("AUD_USD","london","long"):  ("default",             "NO_DATA"),
    ("AUD_USD","london","short"): ("default",             "NO_DATA"),
    ("AUD_USD","ny","long"):      ("default",             "NO_DATA"),
    ("AUD_USD","ny","short"):     ("default",             "NO_DATA"),
    # EUR_JPY
    ("EUR_JPY","asia","long"):    ("default",             "NO_DATA"),
    ("EUR_JPY","asia","short"):   ("default",             "NO_DATA"),
    ("EUR_JPY","london","long"):  ("london_exhaustion",   "WEAK"),
    ("EUR_JPY","london","short"): ("london_exhaustion",   "BAD"),
    ("EUR_JPY","ny","long"):      ("ny_volatility",       "WEAK"),
    ("EUR_JPY","ny","short"):     ("default",             "NO_DATA"),
    # EUR_USD
    ("EUR_USD","asia","long"):    ("default",             "NO_DATA"),
    ("EUR_USD","asia","short"):   ("default",             "NO_DATA"),
    ("EUR_USD","london","long"):  ("default",             "NO_DATA"),
    ("EUR_USD","london","short"): ("london_exhaustion",   "MEDIUM"),
    ("EUR_USD","ny","long"):      ("default",             "NO_DATA"),
    ("EUR_USD","ny","short"):     ("ny_volatility_strict","BAD"),
    # GBP_USD
    ("GBP_USD","asia","long"):    ("default",             "NO_DATA"),
    ("GBP_USD","asia","short"):   ("default",             "NO_DATA"),
    ("GBP_USD","london","long"):  ("london_exhaustion",   "MEDIUM"),
    ("GBP_USD","london","short"): ("london_exhaustion",   "STRONG"),
    ("GBP_USD","ny","long"):      ("default",             "NO_DATA"),
    ("GBP_USD","ny","short"):     ("ny_volatility_strict","BAD"),
    # USD_CAD
    ("USD_CAD","asia","long"):    ("default",             "NO_DATA"),
    ("USD_CAD","asia","short"):   ("default",             "NO_DATA"),
    ("USD_CAD","london","long"):  ("default",             "NO_DATA"),
    ("USD_CAD","london","short"): ("default",             "NO_DATA"),
    ("USD_CAD","ny","long"):      ("ny_volatility",       "MEDIUM"),
    ("USD_CAD","ny","short"):     ("default",             "NO_DATA"),
    # USD_CHF
    ("USD_CHF","asia","long"):    ("default",             "NO_DATA"),
    ("USD_CHF","asia","short"):   ("default",             "NO_DATA"),
    ("USD_CHF","london","long"):  ("london_exhaustion",   "STRONG"),
    ("USD_CHF","london","short"): ("default",             "NO_DATA"),
    ("USD_CHF","ny","long"):      ("ny_volatility_strict","BAD"),
    ("USD_CHF","ny","short"):     ("default",             "NO_DATA"),
    # USD_JPY
    ("USD_JPY","asia","long"):    ("asia_volume_rev",     "WEAK"),
    ("USD_JPY","asia","short"):   ("asia_volume_rev",     "MEDIUM_STRICT"),
    ("USD_JPY","london","long"):  ("default",             "NO_DATA"),
    ("USD_JPY","london","short"): ("default",             "NO_DATA"),
    ("USD_JPY","ny","long"):      ("ny_volatility",       "WEAK"),
    ("USD_JPY","ny","short"):     ("ny_volatility",       "WEAK"),
}


EVIDENCE_STRICTNESS = {
    "STRONG":         1.00,
    "MEDIUM":         1.10,
    "MEDIUM_STRICT":  1.20,
    "WEAK":           1.20,
    "BAD":            1.40,
    "NO_DATA":        1.00,
}


def _safe(view, name, default=None):
    return getattr(view, name, default)


def profile_asia_volume_rev(view, tuning, strictness):
    reasons = []
    rvol5 = _safe(view, "rvol_5bar", 1.0) or 1.0
    h1_ret = _safe(view, "h1_ret_1bar", 0.0) or 0.0
    trend4 = _safe(view, "trend_4h", _safe(view, "h1_ret_4bar", 0.0)) or 0.0
    adr_used = _safe(view, "adr_consumed", 0.5) or 0.5

    rvol_floor = tuning["rvol_floor"] * strictness
    h1_floor = tuning["h1_ret_floor_pips"] * strictness
    adr_ceil = tuning["adr_consumed_ceiling"]

    gate1 = rvol5 >= rvol_floor
    reasons.append(f"rvol5={rvol5:.2f} {'>=' if gate1 else '<'} {rvol_floor:.2f}")
    gate2 = abs(h1_ret) >= h1_floor
    reasons.append(f"|h1_ret|={abs(h1_ret):.2f} {'>=' if gate2 else '<'} {h1_floor:.2f}")
    gate3 = adr_used <= adr_ceil
    reasons.append(f"adr={adr_used:.2f} {'<=' if gate3 else '>'} {adr_ceil:.2f}")
    rev_confirm = (h1_ret * trend4) < 0
    gates_passed = gate1 and gate2 and gate3
    cert_boost = 1.2 if (gates_passed and rev_confirm) else (1.0 if gates_passed else 0.0)
    return dict(gates_passed=gates_passed, cert_boost=cert_boost,
                scaler_mult=0.85, reasons=reasons, profile="asia_volume_rev")


def profile_london_exhaustion(view, tuning, strictness):
    reasons = []
    adr_used = _safe(view, "adr_consumed", 0.5) or 0.5
    atr_conc = _safe(view, "atr_conc", 0.0) or 0.0
    h1_ret = _safe(view, "h1_ret_1bar", 0.0) or 0.0

    adr_ceil = tuning["adr_consumed_ceiling"]
    atr_floor = tuning["atr_conc_floor"] * strictness
    h1_floor = tuning["h1_ret_floor_pips"] * strictness

    gate1 = adr_used <= adr_ceil
    reasons.append(f"adr={adr_used:.2f} {'<=' if gate1 else '>'} {adr_ceil:.2f}")
    gate2 = atr_conc >= atr_floor
    reasons.append(f"atr_conc={atr_conc:.2f} {'>=' if gate2 else '<'} {atr_floor:.2f}")
    gate3 = abs(h1_ret) >= h1_floor
    reasons.append(f"|h1_ret|={abs(h1_ret):.2f} {'>=' if gate3 else '<'} {h1_floor:.2f}")
    gates_passed = gate1 and gate2 and gate3
    cert_boost = 1.1 if gates_passed else 0.0
    return dict(gates_passed=gates_passed, cert_boost=cert_boost,
                scaler_mult=1.0, reasons=reasons, profile="london_exhaustion")


def profile_ny_volatility(view, tuning, strictness):
    reasons = []
    atr_conc = _safe(view, "atr_conc", 0.0) or 0.0
    atr_5m = _safe(view, "atr_5m", 0.0) or 0.0
    h1_ret = _safe(view, "h1_ret_1bar", 0.0) or 0.0
    trend4 = _safe(view, "trend_4h", _safe(view, "h1_ret_4bar", 0.0)) or 0.0
    rvol5 = _safe(view, "rvol_5bar", 1.0) or 1.0

    atr_conc_floor = tuning["atr_conc_floor"] * strictness
    atr_5m_floor = 2.5 * strictness
    h1_floor = tuning["h1_ret_floor_pips"] * strictness
    rvol_ceiling = tuning["rvol_ceiling"]

    gate1 = atr_conc >= atr_conc_floor
    reasons.append(f"atr_conc={atr_conc:.2f} {'>=' if gate1 else '<'} {atr_conc_floor:.2f}")
    gate2 = atr_5m >= atr_5m_floor
    reasons.append(f"atr_5m={atr_5m:.2f} {'>=' if gate2 else '<'} {atr_5m_floor:.2f}")
    gate3 = abs(h1_ret) >= h1_floor
    reasons.append(f"|h1_ret|={abs(h1_ret):.2f} {'>=' if gate3 else '<'} {h1_floor:.2f}")
    gate4 = rvol5 <= rvol_ceiling
    reasons.append(f"rvol5={rvol5:.2f} {'<=' if gate4 else '>'} {rvol_ceiling:.2f}")
    cont_confirm = (h1_ret * trend4) > 0
    gates_passed = gate1 and gate2 and gate3 and gate4
    cert_boost = 1.2 if (gates_passed and cont_confirm) else (1.0 if gates_passed else 0.0)
    return dict(gates_passed=gates_passed, cert_boost=cert_boost,
                scaler_mult=1.15, reasons=reasons, profile="ny_volatility")


def profile_ny_volatility_strict(view, tuning, strictness):
    return profile_ny_volatility(view, tuning, strictness * 1.5)


def profile_default(view, tuning, strictness):
    return dict(gates_passed=True, cert_boost=1.0, scaler_mult=1.0,
                reasons=["default profile — no gates added"], profile="default")


PROFILE_TEMPLATES = {
    "asia_volume_rev":      profile_asia_volume_rev,
    "london_exhaustion":    profile_london_exhaustion,
    "ny_volatility":        profile_ny_volatility,
    "ny_volatility_strict": profile_ny_volatility_strict,
    "default":              profile_default,
}


def get_profile_info(pair: str, session: str, direction: str) -> tuple[str, str]:
    return PROFILE_ASSIGNMENT.get((pair, session, direction), ("default", "NO_DATA"))


def get_pair_tuning(pair: str) -> dict:
    return PAIR_TUNING.get(pair, PAIR_TUNING["EUR_USD"]).copy()


def evaluate_cell(pair: str, session: str, direction: str, view) -> dict:
    """Evaluate the profile for this (pair, session, direction) cell."""
    profile_name, evidence = get_profile_info(pair, session, direction)
    template = PROFILE_TEMPLATES[profile_name]
    tuning = get_pair_tuning(pair)
    strictness = EVIDENCE_STRICTNESS[evidence]
    result = template(view, tuning, strictness)
    result["evidence"] = evidence
    result["pair_tuning"] = tuning
    return result
