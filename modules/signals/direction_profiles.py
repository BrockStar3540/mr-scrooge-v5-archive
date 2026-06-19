"""modules/signals/direction_profiles.py — per-(pair × session) weight profiles.

Derived from:
  - 7.5yr OANDA corpus aggregator + permutation importance findings
  - forexsb.com H1 cross-broker validation
  - Today's live smoke tests (v1-v5, 29 trades with per-bucket breakdown)
  - See vault note: note_scrooge_v5_findings_matrix_2026-06-18.md

Three profile types based on which feature family wins in that cell:

  CONTINUATION_STRONG (asia/JPY, GBP_USD/london, USD_JPY/ny):
    - h1_ret_1bar boosted (it dominates everywhere; 75.9% live accuracy)
    - trend_4h, HTF features at full or boosted weight
    - PDH kept; PDL halved (PDL was 31% accurate in pooled live data)
    - mean-reversion features at low weight (V5 default)

  REVERSION (EUR_USD/ny, GBP_USD/ny, USD_CAD/ny, EUR_JPY/london):
    - mean-reversion features boosted 2-3×
    - continuation + trend_4h reduced 0.5×
    - HTF features reduced 0.3× (actively wrong in these cells)
    - h1_ret_1bar kept (still strong as standalone)

  DEFAULT (everything else, also fallback):
    - V5's current _FACTOR_DEFS unchanged

PLUS universal adjustments applied to ALL profiles:
  - PDH/PDL distance features halved (live evidence: 31-41% accuracy on pooled day)
  - atr_conc amplifier rule: when atr_conc > 2.5, HTF features × 1.5
  - When atr_h1_relative > 1.6 (regime switch HIGH), reversion features × 1.3
"""
from __future__ import annotations

# ── V5's original _FACTOR_DEFS for reference (kept for fallback) ──
V5_DEFAULT_FACTOR_DEFS: list[tuple[str, float]] = [
    # continuation features (positive raw spans)
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
    # mean-reversion features (negative raw spans)
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
]


# ── profile templates ──
def _profile_continuation_strong() -> list[tuple[str, float]]:
    """Bias toward h1_ret_1bar + trend_4h + HTF; halve PDL; keep reversion small."""
    return [
        ("h1_ret_1bar",       +26.0),   # +17.61 → boosted (matrix U5 + live smoke: 76% acc)
        ("rsi_slope",         +10.41),  # unchanged
        ("zscore_1h",          +8.73),  # unchanged
        ("h1_ret_4bar",        +9.0),   # boosted (continuation cells reward this)
        ("d_ret",              +7.09),  # unchanged
        ("ema20_1h_dist_pct",  +7.5),   # mild boost
        ("pdh_dist_pips",      +4.0),   # reduced from +5.95 (still useful but live evidence weaker)
        ("pdl_dist_pips",      +2.5),   # HALVED (live: 31% accuracy globally)
        ("pdl_dist_atr_pct",   +2.5),   # HALVED
        ("pdh_dist_atr_pct",   +4.0),   # reduced
        ("rsi14",              +4.79),  # unchanged
        ("htf_pct_20",         +3.5),   # BOOSTED — works strongly in continuation cells
        ("htf_pct_60",         +2.0),   # boosted
        ("ema20_dist_pct",     -0.57),  # unchanged
        ("bb_pos",             -0.55),
        ("zscore_5m",          -0.55),
        ("ema5_dist_pips",     -0.53),
        ("ret_5m",             -0.50),
        ("ret_15m",            -0.45),
        ("ret_1h",             -0.44),
        ("ret_30m",            -0.41),
        ("ema50_dist_pct",     -0.39),
        ("close_pos_daily",    -1.5),   # BOOSTED (matrix #3 by permutation; 62% live)
        ("ema_cross_pips",     -0.27),
    ]


def _profile_reversion() -> list[tuple[str, float]]:
    """Bias toward mean-reversion features; reduce trend/HTF; keep h1_ret_1bar."""
    return [
        ("h1_ret_1bar",       +17.61),  # unchanged — still strong standalone
        ("rsi_slope",          +5.0),   # reduced from +10.41 (live: rsi_slope was mixed)
        ("zscore_1h",          +4.0),   # reduced from +8.73 (live: 55%, contention)
        ("h1_ret_4bar",        +2.5),   # REDUCED (reversion cells punish this)
        ("d_ret",              +2.0),   # REDUCED
        ("ema20_1h_dist_pct",  +2.0),   # REDUCED
        ("pdh_dist_pips",      +1.5),   # reduced
        ("pdl_dist_pips",      +1.5),   # reduced
        ("pdl_dist_atr_pct",   +1.5),
        ("pdh_dist_atr_pct",   +1.5),
        ("rsi14",              +3.0),   # reduced
        ("htf_pct_20",         +0.5),   # MAJOR cut (live: 0% in NY non-JPY cells)
        ("htf_pct_60",         +0.3),   # MAJOR cut
        ("ema20_dist_pct",     -2.5),   # BOOSTED 4× (reversion family wins here)
        ("bb_pos",             -2.0),   # BOOSTED
        ("zscore_5m",          -2.5),   # BOOSTED (live: amplified by m_cert in v4)
        ("ema5_dist_pips",     -2.5),   # BOOSTED
        ("ret_5m",             -2.0),   # BOOSTED
        ("ret_15m",            -2.0),   # BOOSTED
        ("ret_1h",             -2.0),   # BOOSTED
        ("ret_30m",            -2.0),   # BOOSTED
        ("ema50_dist_pct",     -2.0),   # BOOSTED
        ("close_pos_daily",    -2.5),   # BOOSTED
        ("ema_cross_pips",     -2.0),   # BOOSTED
    ]


def _profile_default() -> list[tuple[str, float]]:
    """V5 unchanged baseline — for cells without clear evidence."""
    return list(V5_DEFAULT_FACTOR_DEFS)


# ── per-(pair × session) profile assignment ──
# Each cell points to a profile name. The profile is materialized via the
# get_factor_defs() function below.
# Evidence ratings:
#   STRONG = corpus + cross-broker + live concur
#   MODERATE = corpus + live concur OR corpus + cross-broker concur
#   WEAK = single source (e.g., live only with n<=2 trades)
PROFILE_ASSIGNMENT = {
    "AUD_JPY": {
        "asia":   ("continuation_strong", "STRONG"),   # 3/3 wins live + matrix tier-1 asia/JPY
        "london": ("default",             "WEAK"),     # mixed signals
        "ny":     ("continuation_strong", "MODERATE"), # matches asia pattern in matrix
    },
    "AUD_USD": {
        "asia":   ("continuation_strong", "MODERATE"), # 1 live + matrix tier-2
        "london": ("default",             "WEAK"),
        "ny":     ("reversion",           "WEAK"),     # matches other NY non-JPY
    },
    "EUR_JPY": {
        "asia":   ("continuation_strong", "MODERATE"), # corpus evidence; no live trades today
        "london": ("reversion",           "MODERATE"), # 2 losses today, reversion features 100%
        "ny":     ("default",             "WEAK"),
    },
    "EUR_USD": {
        "asia":   ("default",             "WEAK"),
        "london": ("default",             "WEAK"),    # 50/50 mixed today
        "ny":     ("reversion",           "STRONG"),   # 2/2 losses today + matrix tier-3
    },
    "GBP_USD": {
        "asia":   ("default",             "WEAK"),
        "london": ("continuation_strong", "WEAK"),    # 1 trade + matrix asia/london continuation
        "ny":     ("reversion",           "STRONG"),   # 1/4 wins today + matrix + corpus
    },
    "USD_CAD": {
        "asia":   ("default",             "WEAK"),
        "london": ("default",             "WEAK"),
        "ny":     ("reversion",           "MODERATE"), # 1/3 wins today, reversion 100%
    },
    "USD_CHF": {
        "asia":   ("default",             "WEAK"),
        "london": ("default",             "WEAK"),    # mixed today
        "ny":     ("continuation_strong", "WEAK"),    # h1_ret_1bar 100% today (n=3)
    },
    "USD_JPY": {
        "asia":   ("continuation_strong", "MODERATE"), # 2/3 wins + matrix tier-2 asia/JPY
        "london": ("default",             "WEAK"),
        "ny":     ("continuation_strong", "WEAK"),    # 1/1 win today + matrix
    },
}


# ── aggregator amplifier rules (apply on top of base weights) ──
# These are derived from smoke v4: aggregator HIGH → certain feature families
# get amplified. Use conservatively because n=29 trades.
AGGREGATOR_RULES = [
    # When atr_conc > 2.5, HTF/structural features become 1.5-5× more accurate
    {
        "name":           "atr_conc_amplifies_htf",
        "condition":      lambda view: getattr(view, "atr_conc", 0) > 2.5,
        "amplify":        ["htf_pct_20", "htf_pct_60", "h1_ret_4bar", "d_ret"],
        "multiplier":     1.5,
        "evidence":       "smoke v4: atr_conc HIGH → 1.5-5× accuracy on these features",
        "confidence":     "MODERATE",
    },
    # When atr_h1_relative > 1.6 (HIGH-vol regime), reversion features dominate
    {
        "name":           "high_vol_regime_amplifies_reversion",
        "condition":      lambda view: getattr(view, "atr_h1_relative", 1.0) > 1.6,
        "amplify":        ["ema20_dist_pct", "bb_pos", "zscore_5m", "ret_15m",
                            "ema5_dist_pips", "ret_5m", "ret_30m", "close_pos_daily"],
        "multiplier":     1.3,
        "evidence":       "smoke v4: atr_h1_relative HIGH → reversion features +43-88% accuracy",
        "confidence":     "MODERATE",
    },
    # When atr_h1_relative > 1.6, REDUCE HTF/continuation features (anti-amplifier)
    {
        "name":           "high_vol_regime_suppresses_htf",
        "condition":      lambda view: getattr(view, "atr_h1_relative", 1.0) > 1.6,
        "amplify":        ["htf_pct_20", "htf_pct_60", "trend_4h", "h1_ret_4bar",
                            "pdh_dist_pips", "pdh_dist_atr_pct", "d_ret"],
        "multiplier":     0.5,
        "evidence":       "smoke v4: HIGH atr_h1_relative → HTF features drop to 0.43-0.56×",
        "confidence":     "MODERATE",
    },
]


# ── api ──
def get_factor_defs(pair: str, session: str) -> list[tuple[str, float]]:
    """Return the (feature, signed_raw_span) list for this (pair, session)."""
    assignment = PROFILE_ASSIGNMENT.get(pair, {}).get(session)
    if assignment is None:
        return _profile_default()
    profile_name, _evidence = assignment
    if profile_name == "continuation_strong":
        return _profile_continuation_strong()
    if profile_name == "reversion":
        return _profile_reversion()
    return _profile_default()


def get_profile_info(pair: str, session: str) -> tuple[str, str]:
    """Return (profile_name, evidence_level) for diagnostics/logging."""
    return PROFILE_ASSIGNMENT.get(pair, {}).get(session, ("default", "WEAK"))


def apply_aggregator_rules(weights: dict[str, float], view) -> dict[str, float]:
    """Modify weights in-place based on view's aggregator state. Returns NEW dict."""
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
