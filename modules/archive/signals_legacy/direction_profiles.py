"""modules/signals/direction_profiles.py — per-(pair × session × direction) weights.

Per-cell weighting where each (pair × session × direction) gets its own profile.
48 cells total (8 pairs × 3 sessions × 2 directions). Cells with no live or
matrix evidence fall through to "default" (V5 v1 _FACTOR_DEFS unchanged).

Profile templates:
  CONTINUATION_STRONG — h1_ret_1bar/trend boosted; PDL halved; reversion small
  REVERSION           — mean-reversion family 2-4×; trend/HTF/PDH/PDL reduced
  DEFAULT             — V5 v1 unchanged

Direction matters because:
  1. Live evidence shows direction-asymmetric WRs in many cells (USD_CHF/ny/long
     0/3 vs USD_CHF/ny/short no_data; AUD_JPY/asia/short 5/5 vs long no_data)
  2. Matrix per-direction permutation importance differs (yesterday's work
     showed different feature rankings for long vs short in 17 of 48 cells)
  3. Brock said indicator accuracy differs between longs and shorts in our data

Two-pass evaluation in DirectionModule.stamp():
  Pass 1: compute raw direction with V5 v1 weights → tentative direction
  Pass 2: load (pair, session, tentative_dir) profile → recompute final score
  Direction = sign of final score (may flip from tentative if profile suggests)
"""
from __future__ import annotations

# ── V5's original _FACTOR_DEFS for reference + default profile ──
V5_DEFAULT_FACTOR_DEFS: list[tuple[str, float]] = [
    ("h1_ret_1bar",       +17.61),
    ("rsi_slope",         +10.41),
    ("zscore_1h",          +8.73),
    ("h1_ret_4bar",        +7.35),
    ("d_ret",              +7.09),
    ("ema20_1h_dist_pct",  +6.37),
    ("pdh_dist_pips",      +5.95),
    ("pdl_dist_pips",      +5.88),
    ("pdl_dist_atr_pct",   +5.69),
    ("pdh_dist_atr_pct",   +5.62),
    ("rsi14",              +4.79),
    ("htf_pct_20",         +1.91),
    ("htf_pct_60",         +1.01),
    ("ema20_dist_pct",     -0.57),
    ("bb_pos",             -0.55),
    ("zscore_5m",          -0.55),
    ("ema5_dist_pips",     -0.53),
    ("ret_5m",             -0.50),
    ("ret_15m",            -0.45),
    ("ret_1h",             -0.44),
    ("ret_30m",            -0.41),
    ("ema50_dist_pct",     -0.39),
    ("close_pos_daily",    -0.30),
    ("ema_cross_pips",     -0.27),
    # 2026-06-23: q_willr_m5 SOFT WIRE — matrix top-3 in 24/24 cells (gain 0.052).
    # Negative weight = reversion form: willr extreme oversold (norm -1) → +score
    # contribution toward long; willr extreme overbought (norm +1) → score toward short.
    # Per-cell sign actually varies (matrix); 3 profiles handle it by amplification.
    ("willr_m5",           -1.0),
]


# ── profile templates ──
def _profile_continuation_strong() -> list[tuple[str, float]]:
    """Bias toward h1_ret_1bar + trend_4h + HTF; halve PDL; keep reversion small."""
    return [
        ("h1_ret_1bar",       +26.0),
        ("rsi_slope",         +10.41),
        ("zscore_1h",          +8.73),
        ("h1_ret_4bar",        +9.0),
        ("d_ret",              +7.09),
        ("ema20_1h_dist_pct",  +7.5),
        ("pdh_dist_pips",      +4.0),
        ("pdl_dist_pips",      +2.5),
        ("pdl_dist_atr_pct",   +2.5),
        ("pdh_dist_atr_pct",   +4.0),
        ("rsi14",              +4.79),
        ("htf_pct_20",         +3.5),
        ("htf_pct_60",         +2.0),
        ("ema20_dist_pct",     -0.57),
        ("bb_pos",             -0.55),
        ("zscore_5m",          -0.55),
        ("ema5_dist_pips",     -0.53),
        ("ret_5m",             -0.50),
        ("ret_15m",            -0.45),
        ("ret_1h",             -0.44),
        ("ret_30m",            -0.41),
        ("ema50_dist_pct",     -0.39),
        ("close_pos_daily",    -1.5),
        ("ema_cross_pips",     -0.27),
        ("willr_m5",           -3.0),
    ]


def _profile_reversion() -> list[tuple[str, float]]:
    """Bias toward mean-reversion features; reduce trend/HTF; keep h1_ret_1bar."""
    return [
        ("h1_ret_1bar",       +17.61),
        ("rsi_slope",          +5.0),
        ("zscore_1h",          +4.0),
        ("h1_ret_4bar",        +2.5),
        ("d_ret",              +2.0),
        ("ema20_1h_dist_pct",  +2.0),
        ("pdh_dist_pips",      +1.5),
        ("pdl_dist_pips",      +1.5),
        ("pdl_dist_atr_pct",   +1.5),
        ("pdh_dist_atr_pct",   +1.5),
        ("rsi14",              +3.0),
        ("htf_pct_20",         +0.5),
        ("htf_pct_60",         +0.3),
        ("ema20_dist_pct",     -2.5),
        ("bb_pos",             -2.0),
        ("zscore_5m",          -2.5),
        ("ema5_dist_pips",     -2.5),
        ("ret_5m",             -2.0),
        ("ret_15m",            -2.0),
        ("ret_1h",             -2.0),
        ("ret_30m",            -2.0),
        ("ema50_dist_pct",     -2.0),
        ("close_pos_daily",    -2.5),
        ("ema_cross_pips",     -2.0),
        ("willr_m5",           -5.0),
    ]


def _profile_default() -> list[tuple[str, float]]:
    return list(V5_DEFAULT_FACTOR_DEFS)


# ── per-(pair × session × direction) profile assignment (48 cells) ──
# Cell tag = (profile_name, evidence) where evidence ∈ STRONG, MODERATE, WEAK, BAD, NO_DATA
# Evidence drives strictness via direction_v2's gate-fail-on-low-cert path.
PROFILE_ASSIGNMENT: dict[str, dict[str, dict[str, tuple[str, str]]]] = {
    "AUD_JPY": {
        "asia": {
            "long":  ("default",             "NO_DATA"),   # 0 live trades
            "short": ("continuation_strong", "STRONG"),    # 5/5 80% WR +8.15p
        },
        "london": {
            "long":  ("reversion",           "BAD"),       # 2/2 lost
            "short": ("default",             "WEAK"),      # 1 lost
        },
        "ny": {
            "long":  ("continuation_strong", "MODERATE"),  # matrix
            "short": ("continuation_strong", "MODERATE"),  # matrix
        },
    },
    "AUD_USD": {
        "asia": {
            "long":  ("default",             "NO_DATA"),
            "short": ("continuation_strong", "MEDIUM"),    # 4/4 75% WR
        },
        "london": {
            "long":  ("default",             "NO_DATA"),
            "short": ("default",             "NO_DATA"),
        },
        "ny": {
            "long":  ("reversion",           "WEAK"),      # matrix
            "short": ("reversion",           "WEAK"),      # matrix
        },
    },
    "EUR_JPY": {
        "asia": {
            "long":  ("continuation_strong", "MODERATE"),  # matrix asia/JPY tier-2
            "short": ("continuation_strong", "MODERATE"),
        },
        "london": {
            "long":  ("reversion",           "WEAK"),      # 1 win +6.4
            "short": ("reversion",           "BAD"),       # 2/2 lost
        },
        "ny": {
            "long":  ("continuation_strong", "WEAK"),      # 1 win +10.4 (n=1)
            "short": ("default",             "NO_DATA"),
        },
    },
    "EUR_USD": {
        "asia": {
            "long":  ("default",             "NO_DATA"),
            "short": ("default",             "NO_DATA"),
        },
        "london": {
            "long":  ("default",             "NO_DATA"),
            "short": ("reversion",           "MEDIUM"),    # 2 mixed (+9.65/-13)
        },
        "ny": {
            "long":  ("default",             "NO_DATA"),
            "short": ("reversion",           "STRONG"),    # 2/2 lost + matrix tier-3
        },
    },
    "GBP_USD": {
        "asia": {
            "long":  ("default",             "NO_DATA"),
            "short": ("default",             "NO_DATA"),
        },
        "london": {
            "long":  ("continuation_strong", "MEDIUM"),    # 1W/1L mixed
            "short": ("continuation_strong", "STRONG"),    # 1 win +15.55 + matrix
        },
        "ny": {
            "long":  ("default",             "NO_DATA"),
            "short": ("reversion",           "STRONG"),    # 4 trades 25% WR + matrix
        },
    },
    "USD_CAD": {
        "asia": {
            "long":  ("default",             "NO_DATA"),
            "short": ("default",             "NO_DATA"),
        },
        "london": {
            "long":  ("default",             "NO_DATA"),
            "short": ("default",             "NO_DATA"),
        },
        "ny": {
            "long":  ("reversion",           "MODERATE"),  # 4 trades 50% WR — try reversion
            "short": ("default",             "NO_DATA"),
        },
    },
    "USD_CHF": {
        "asia": {
            "long":  ("default",             "NO_DATA"),
            "short": ("default",             "NO_DATA"),
        },
        "london": {
            "long":  ("continuation_strong", "MODERATE"),  # 3 trades 67% WR
            "short": ("default",             "NO_DATA"),
        },
        "ny": {
            "long":  ("reversion",           "MODERATE"),  # 3 trades all lost — flip to reversion
            "short": ("default",             "NO_DATA"),
        },
    },
    "USD_JPY": {
        "asia": {
            "long":  ("continuation_strong", "WEAK"),      # 1 trade +2.6
            "short": ("continuation_strong", "MEDIUM_STRICT"),  # 4 mixed but high WR
        },
        "london": {
            "long":  ("default",             "NO_DATA"),
            "short": ("default",             "NO_DATA"),
        },
        "ny": {
            "long":  ("continuation_strong", "WEAK"),      # 1 win +17.85
            "short": ("continuation_strong", "WEAK"),      # 1 loss -18.15
        },
    },
}


# ── aggregator amplifier rules (apply on top of base weights, direction-agnostic) ──
# NOTE (2026-07-03 audit): "atr_conc_amplifies_htf" rule DELETED.
# It gated on atr_conc > 2.5 but atr_conc = atr_5m / atr_1h ∈ (0, ~1.0) in
# production (core/feed/oanda.py:396) — condition can never fire. Same root
# cause as the momentum_profiles.py floor mismatch. Removed rather than left
# as dead code since AGGREGATOR_RULES is fingerprinted by lock_snapshot.
AGGREGATOR_RULES = [
    # EMPTY as of 2026-07-03 — all three original amplifier rules retired:
    #   - "atr_conc_amplifies_htf": deleted earlier 2026-07-03 (condition mathematically
    #     impossible — atr_conc is a ratio < 1.0, threshold was 2.5).
    #   - "high_vol_regime_amplifies_reversion" (x1.3) and
    #     "high_vol_regime_suppresses_htf" (x0.5): REMOVED per the 2026 confirmation study
    #     (Mini ~/v5-atrrel-confirm/, 297,952 bars Jan-Jun 2026). Findings: the 8yr
    #     long-help/short-hurt asymmetry INVERTED in 2026 (regime flip; 8yr agreement
    #     only 29%); direction-agnostic application was ALIGNED in 42% of cells and
    #     MISMATCHED in 42% (self-canceling), with the 9 strongest mismatches all being
    #     the cells the rules hurt most (up to -17.8 pip conditional delta).
    #     Evidence basis was "smoke v4" (pre-V5, pre-regime). Per-cell whitelist NOT
    #     wired yet: only 8 cells show stable 2026 signal (all JPY, short=KEEP/long=INVERT)
    #     at a 1.6% trigger rate — flagged for a dedicated study on full-year 2026 data.
    # Mechanism retained: rules may be re-added ONLY per-cell, 2026-fit, drift-labeled.
]



# ── api ──
def get_factor_defs(pair: str, session: str, direction: str = "long") -> list[tuple[str, float]]:
    """Return the (feature, signed_raw_span) list for this (pair, session, direction)."""
    cell = PROFILE_ASSIGNMENT.get(pair, {}).get(session, {}).get(direction)
    if cell is None:
        return _profile_default()
    profile_name, _evidence = cell
    if profile_name == "continuation_strong":
        return _profile_continuation_strong()
    if profile_name == "reversion":
        return _profile_reversion()
    return _profile_default()


def get_profile_info(pair: str, session: str, direction: str = "long") -> tuple[str, str]:
    """Return (profile_name, evidence_level) for (pair, session, direction)."""
    return PROFILE_ASSIGNMENT.get(pair, {}).get(session, {}).get(direction, ("default", "NO_DATA"))


def apply_aggregator_rules(weights: dict[str, float], view) -> dict[str, float]:
    """Modify weights based on view's aggregator state. Returns NEW dict."""
    out = dict(weights)
    for rule in AGGREGATOR_RULES:
        try:
            if rule["condition"](view):
                mult = rule["multiplier"]
                for fname in rule["amplify"]:
                    if fname in out:
                        out[fname] = out[fname] * mult
        except (AttributeError, TypeError):
            continue
    return out
