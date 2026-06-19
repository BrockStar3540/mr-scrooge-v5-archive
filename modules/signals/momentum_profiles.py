"""V5 per-(pair × session) momentum profile assignment.

Mirrors direction_profiles.py. Each pair has its own configuration with
session-specific profile slots. Profiles encode WHICH momentum signals
gate entries in that cell — built from the 44-trade live evidence
(2026-06-18 to 2026-06-19, journalctl + OANDA M1/M5/H1/D).

Architecture (parallel to direction_v2):
    PAIR_TUNING[pair]        → per-pair constants (atr_d_typical, rvol_floor, etc.)
    PROFILE_ASSIGNMENT[(pair, session)] → (profile_name, evidence_tag)
    PROFILE_TEMPLATES[name]  → callable that returns gate-pass + cert + expected

Each pair × session cell picks a profile. Default = V5 v1 behavior
unchanged. STRONG/MEDIUM cells get a session-shaped profile with
gates that block setups the live evidence showed were no-momentum entries.

Cell-level data driving the choices (sum_out per cell, 44-trade window):
    POSITIVE (use session profile):
        AUD_JPY/asia  (5/5, 80% WR, +8.15p, avg_h1=+9.1)
        GBP_USD/london (3/3, 67% WR, +2.85p, avg_h1=+16.4)
        USD_CHF/london (3/3, 67% WR, +5.20p, avg_h1=+10.1)
        EUR_JPY/ny (1/1, +10.40p — n=1 caveat)
    HIGH-WR BUT-NEGATIVE (use profile + stricter):
        USD_JPY/asia (5/5, 60% WR but -25.0p — wins too small)
        AUD_USD/asia (4/4, 75% WR but -5.9p — same problem)
    BAD-EVIDENCE (default OR session profile + extra-tight):
        AUD_JPY/london (3/3, 33% WR, -27.6p)
        EUR_JPY/london (3/3, 33% WR, -16.5p)
        GBP_USD/ny (4/4, 25% WR, -14.6p)
        EUR_USD/ny (2/2, 0% WR, -12.9p)
        USD_CHF/ny (3/3, 33% WR, -11.2p)
    NO DATA (default = V5 v1 unchanged):
        12 cells
"""
from __future__ import annotations

# === Per-pair tuning constants ===
# Different pairs have different typical ATR-D, baseline volume, and
# what counts as "h1 momentum" in pips. These get plugged into the
# profile templates so the SAME profile (e.g., asia_volume_rev) is
# calibrated DIFFERENTLY for AUD_JPY vs USD_JPY.
PAIR_TUNING: dict[str, dict] = {
    "AUD_JPY": dict(
        atr_d_typical_pips=75,
        rvol_floor=1.0, rvol_ceiling=1.5,
        h1_ret_floor_pips=2.0,
        atr_conc_floor=4.5,
        expected_pips_scaler=0.25,  # asia peaks small
        adr_consumed_ceiling=1.30,
    ),
    "AUD_USD": dict(
        atr_d_typical_pips=55,
        rvol_floor=1.0, rvol_ceiling=1.5,
        h1_ret_floor_pips=2.0,
        atr_conc_floor=4.0,
        expected_pips_scaler=0.30,
        adr_consumed_ceiling=1.30,
    ),
    "EUR_JPY": dict(
        atr_d_typical_pips=91,
        rvol_floor=1.0, rvol_ceiling=1.5,
        h1_ret_floor_pips=3.0,
        atr_conc_floor=5.0,
        expected_pips_scaler=0.30,
        adr_consumed_ceiling=1.20,
    ),
    "EUR_USD": dict(
        atr_d_typical_pips=64,
        rvol_floor=1.2, rvol_ceiling=1.5,
        h1_ret_floor_pips=2.5,
        atr_conc_floor=4.5,
        expected_pips_scaler=0.30,
        adr_consumed_ceiling=1.20,
    ),
    "GBP_USD": dict(
        atr_d_typical_pips=81,
        rvol_floor=1.0, rvol_ceiling=1.5,
        h1_ret_floor_pips=3.0,
        atr_conc_floor=5.0,
        expected_pips_scaler=0.35,
        adr_consumed_ceiling=1.20,
    ),
    "USD_CAD": dict(
        atr_d_typical_pips=60,
        rvol_floor=1.0, rvol_ceiling=1.5,
        h1_ret_floor_pips=2.0,
        atr_conc_floor=4.5,
        expected_pips_scaler=0.30,
        adr_consumed_ceiling=1.20,
    ),
    "USD_CHF": dict(
        atr_d_typical_pips=59,
        rvol_floor=1.0, rvol_ceiling=1.5,
        h1_ret_floor_pips=2.5,
        atr_conc_floor=4.5,
        expected_pips_scaler=0.35,
        adr_consumed_ceiling=1.20,
    ),
    "USD_JPY": dict(
        atr_d_typical_pips=62,
        rvol_floor=1.2, rvol_ceiling=1.5,
        h1_ret_floor_pips=3.0,
        atr_conc_floor=5.0,
        expected_pips_scaler=0.30,
        adr_consumed_ceiling=1.20,
    ),
}

# === Per-cell profile assignment ===
# (pair, session) → (profile_name, evidence_tag)
# evidence_tag: STRONG (n>=3, WR>=60%, net+), MEDIUM (n>=3, mixed), BAD
# (n>=3, WR<40%), NO_DATA (n<3) — drives the strictness multiplier in templates.
PROFILE_ASSIGNMENT: dict[tuple[str, str], tuple[str, str]] = {
    # ASIA — h1_ret +0.887 + rvol +0.68 + reversion (trend_4h −0.621)
    ("AUD_JPY", "asia"):    ("asia_volume_rev",     "STRONG"),       # 5 trades, 80% WR, +8.15p
    ("USD_JPY", "asia"):    ("asia_volume_rev",     "MEDIUM_STRICT"),# 5 trades, 60% WR, -25p (size problem)
    ("AUD_USD", "asia"):    ("asia_volume_rev",     "MEDIUM"),       # 4 trades, 75% WR, -5.9p
    ("EUR_JPY", "asia"):    ("default",             "NO_DATA"),      # 0 trades — V5 v1
    ("EUR_USD", "asia"):    ("default",             "NO_DATA"),
    ("GBP_USD", "asia"):    ("default",             "NO_DATA"),
    ("USD_CAD", "asia"):    ("default",             "NO_DATA"),
    ("USD_CHF", "asia"):    ("default",             "NO_DATA"),

    # LONDON — adr_consumed +0.637 + atr_conc +0.396
    ("AUD_JPY", "london"):  ("london_exhaustion",   "BAD"),          # 3 trades, 33% WR, -27p
    ("USD_JPY", "london"):  ("default",             "NO_DATA"),
    ("EUR_JPY", "london"):  ("london_exhaustion",   "BAD"),          # 3 trades, 33% WR, -16p
    ("EUR_USD", "london"):  ("london_exhaustion",   "MEDIUM"),       # 2 trades, 50% WR, -3.4p
    ("GBP_USD", "london"):  ("london_exhaustion",   "STRONG"),       # 3 trades, 67% WR, +2.9p
    ("AUD_USD", "london"):  ("default",             "NO_DATA"),
    ("USD_CAD", "london"):  ("default",             "NO_DATA"),
    ("USD_CHF", "london"):  ("london_exhaustion",   "STRONG"),       # 3 trades, 67% WR, +5.2p

    # NY — atr_conc +0.731 + atr_5m +0.725 + continuation (trend_4h +0.687)
    ("AUD_JPY", "ny"):      ("default",             "NO_DATA"),
    ("USD_JPY", "ny"):      ("ny_volatility",       "MEDIUM"),       # 2 trades, 50% WR, -0.3p
    ("EUR_JPY", "ny"):      ("ny_volatility",       "WEAK"),         # 1 trade, +10.4p (caveat n=1)
    ("EUR_USD", "ny"):      ("ny_volatility_strict","BAD"),          # 2 trades, 0% WR, -12.9p
    ("GBP_USD", "ny"):      ("ny_volatility_strict","BAD"),          # 4 trades, 25% WR, -14.6p
    ("AUD_USD", "ny"):      ("default",             "NO_DATA"),
    ("USD_CAD", "ny"):      ("ny_volatility",       "MEDIUM"),       # 4 trades, 50% WR, -7.9p
    ("USD_CHF", "ny"):      ("ny_volatility_strict","BAD"),          # 3 trades, 33% WR, -11p
}


# Evidence-tag → strictness multiplier on gate floors.
# Tighter gates for cells with bad live evidence even within same profile.
EVIDENCE_STRICTNESS = {
    "STRONG":         1.00,  # default profile floors
    "MEDIUM":         1.10,  # 10% tighter floors
    "MEDIUM_STRICT":  1.20,  # 20% tighter
    "WEAK":           1.20,  # n<3 — be cautious
    "BAD":            1.40,  # actively losing — 40% tighter
    "NO_DATA":        1.00,  # no signal either way → run base profile cleanly
}


# === Profile templates ===
# Each profile is a callable: profile(view, tuning, strictness) -> dict
# Returns:
#   gates_passed: bool      — whether this entry passes momentum-side gates
#   cert_boost:   float     — multiplier on baseline m_cert (0..1.5)
#   scaler_mult:  float     — multiplier on tuning['expected_pips_scaler']
#   reasons:      list[str] — human-readable gate breakdown for logging

def _safe(view, name, default=None):
    return getattr(view, name, default)


def profile_asia_volume_rev(view, tuning, strictness):
    """Asia session — rvol spike + h1_ret + reversion (trade against 4h)."""
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
    reasons.append(f"adr_used={adr_used:.2f} {'<=' if gate3 else '>'} {adr_ceil:.2f}")
    # reversion confirm — soft (not a hard gate, just a cert booster)
    rev_confirm = (h1_ret * trend4) < 0   # h1 opposite of 4h = reversion setup

    gates_passed = gate1 and gate2 and gate3
    cert_boost = 1.2 if (gates_passed and rev_confirm) else (1.0 if gates_passed else 0.0)
    scaler_mult = 0.85   # asia peaks tend to be smaller, scale expected down
    return dict(gates_passed=gates_passed, cert_boost=cert_boost,
                scaler_mult=scaler_mult, reasons=reasons,
                profile="asia_volume_rev")


def profile_london_exhaustion(view, tuning, strictness):
    """London — adr-consumed ceiling + atr_conc floor."""
    reasons = []
    adr_used = _safe(view, "adr_consumed", 0.5) or 0.5
    atr_conc = _safe(view, "atr_conc", 0.0) or 0.0
    h1_ret = _safe(view, "h1_ret_1bar", 0.0) or 0.0

    adr_ceil = tuning["adr_consumed_ceiling"]
    atr_floor = tuning["atr_conc_floor"] * strictness
    h1_floor = tuning["h1_ret_floor_pips"] * strictness

    gate1 = adr_used <= adr_ceil
    reasons.append(f"adr_used={adr_used:.2f} {'<=' if gate1 else '>'} {adr_ceil:.2f}")
    gate2 = atr_conc >= atr_floor
    reasons.append(f"atr_conc={atr_conc:.2f} {'>=' if gate2 else '<'} {atr_floor:.2f}")
    gate3 = abs(h1_ret) >= h1_floor
    reasons.append(f"|h1_ret|={abs(h1_ret):.2f} {'>=' if gate3 else '<'} {h1_floor:.2f}")

    gates_passed = gate1 and gate2 and gate3
    cert_boost = 1.1 if gates_passed else 0.0
    scaler_mult = 1.0
    return dict(gates_passed=gates_passed, cert_boost=cert_boost,
                scaler_mult=scaler_mult, reasons=reasons,
                profile="london_exhaustion")


def profile_ny_volatility(view, tuning, strictness):
    """NY — atr_conc + atr_5m + continuation (trend_4h sign-aligned)."""
    reasons = []
    atr_conc = _safe(view, "atr_conc", 0.0) or 0.0
    atr_5m = _safe(view, "atr_5m", 0.0) or 0.0
    h1_ret = _safe(view, "h1_ret_1bar", 0.0) or 0.0
    trend4 = _safe(view, "trend_4h", _safe(view, "h1_ret_4bar", 0.0)) or 0.0
    rvol5 = _safe(view, "rvol_5bar", 1.0) or 1.0

    atr_conc_floor = tuning["atr_conc_floor"] * strictness
    atr_5m_floor = 2.5 * strictness   # NY M5 ATR floor in pips
    h1_floor = tuning["h1_ret_floor_pips"] * strictness
    rvol_ceiling = tuning["rvol_ceiling"]

    gate1 = atr_conc >= atr_conc_floor
    reasons.append(f"atr_conc={atr_conc:.2f} {'>=' if gate1 else '<'} {atr_conc_floor:.2f}")
    gate2 = atr_5m >= atr_5m_floor
    reasons.append(f"atr_5m={atr_5m:.2f} {'>=' if gate2 else '<'} {atr_5m_floor:.2f}")
    gate3 = abs(h1_ret) >= h1_floor
    reasons.append(f"|h1_ret|={abs(h1_ret):.2f} {'>=' if gate3 else '<'} {h1_floor:.2f}")
    gate4 = rvol5 <= rvol_ceiling   # NY: NO vol-spike trades
    reasons.append(f"rvol5={rvol5:.2f} {'<=' if gate4 else '>'} {rvol_ceiling:.2f}")
    # continuation confirm — soft cert booster
    cont_confirm = (h1_ret * trend4) > 0   # h1 same dir as 4h = continuation

    gates_passed = gate1 and gate2 and gate3 and gate4
    cert_boost = 1.2 if (gates_passed and cont_confirm) else (1.0 if gates_passed else 0.0)
    scaler_mult = 1.15   # NY peaks bigger when they happen
    return dict(gates_passed=gates_passed, cert_boost=cert_boost,
                scaler_mult=scaler_mult, reasons=reasons,
                profile="ny_volatility")


def profile_ny_volatility_strict(view, tuning, strictness):
    """NY (BAD-evidence cells) — same as ny_volatility but with 1.5x floors."""
    return profile_ny_volatility(view, tuning, strictness * 1.5)


def profile_default(view, tuning, strictness):
    """V5 v1 behavior — no new gates. cert_boost=1.0, scaler=1.0."""
    return dict(gates_passed=True, cert_boost=1.0, scaler_mult=1.0,
                reasons=["default profile — no gates added"],
                profile="default")


PROFILE_TEMPLATES = {
    "asia_volume_rev":      profile_asia_volume_rev,
    "london_exhaustion":    profile_london_exhaustion,
    "ny_volatility":        profile_ny_volatility,
    "ny_volatility_strict": profile_ny_volatility_strict,
    "default":              profile_default,
}


# === Helpers ===
def get_profile_info(pair: str, session: str) -> tuple[str, str]:
    return PROFILE_ASSIGNMENT.get((pair, session), ("default", "NO_DATA"))


def get_pair_tuning(pair: str) -> dict:
    return PAIR_TUNING.get(pair, PAIR_TUNING["EUR_USD"]).copy()


def evaluate_cell(pair: str, session: str, view) -> dict:
    """Evaluate the profile for this (pair, session) against a MarketView."""
    profile_name, evidence = get_profile_info(pair, session)
    template = PROFILE_TEMPLATES[profile_name]
    tuning = get_pair_tuning(pair)
    strictness = EVIDENCE_STRICTNESS[evidence]
    result = template(view, tuning, strictness)
    result["evidence"] = evidence
    result["pair_tuning"] = tuning
    return result
