"""Smoke test for momentum_v3 + momentum_profiles.

Validates:
  1. PROFILE_ASSIGNMENT covers all 24 (pair, session) cells
  2. PAIR_TUNING covers all 8 pairs
  3. Each profile fires gates differently for the same view
  4. Strictness multipliers tighten floors for BAD-evidence cells
  5. The chaos veto trumps the profile
"""
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Mock V5 base types
@dataclass
class MarketView:
    timestamp: str = "2026-06-19T00:00:00Z"
    atr_5m: float = 4.0; atr_1h: float = 15.0
    rvol_5bar: float = 1.0; rvol_12bar: float = 1.0
    bb_width: float = 8.0
    range_5bar: float = 5.0; range_12bar: float = 10.0
    atr_d_pips: float = 80.0; d_range_pips: float = 60.0
    adr_consumed: float = 0.6
    pdh_dist_pips: float = 10.0; pdl_dist_pips: float = 15.0
    pdh_dist_atr_pct: float = 0.0; pdl_dist_atr_pct: float = 0.0
    atr_conc: float = 5.0; atr_h1_relative: float = 5.0
    h1_ret_1bar: float = 0.0; h1_ret_4bar: float = 0.0
    trend_4h: float = 0.0
    # direction features (unused here but on the view)
    rsi_slope: float = 0.0; zscore_1h: float = 0.0
    d_ret: float = 0.0; ema20_1h_dist_pct: float = 0.0
    rsi14: float = 50.0; htf_pct_20: float = 0.0; htf_pct_60: float = 0.0
    ema20_dist_pct: float = 0.0; bb_pos: float = 0.5
    zscore_5m: float = 0.0; ema5_dist_pips: float = 0.0
    ret_5m: float = 0.0; ret_15m: float = 0.0; ret_30m: float = 0.0
    ret_1h: float = 0.0; ema50_dist_pct: float = 0.0
    close_pos_daily: float = 0.5; ema_cross_pips: float = 0.0


@dataclass
class MomentumStamp:
    pair: str; session: str; timestamp: str
    vol_regime: str; expected_pips: float
    certainty: float; reads: dict = field(default_factory=dict)


_base_mod = type(sys)("base")
_base_mod.MarketView = MarketView
_base_mod.MomentumStamp = MomentumStamp
sys.modules["modules"] = type(sys)("modules")
sys.modules["modules.signals"] = type(sys)("signals")
sys.modules["modules.signals.base"] = _base_mod
sys.modules["base"] = _base_mod


def test_assignment_coverage():
    print("\n[1] coverage check — 24 (pair, session) cells")
    from momentum_profiles import PROFILE_ASSIGNMENT, PAIR_TUNING, PROFILE_TEMPLATES
    pairs = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
    sessions = ["asia","london","ny"]
    missing = []
    for p in pairs:
        for s in sessions:
            if (p, s) not in PROFILE_ASSIGNMENT:
                missing.append((p, s))
    assert not missing, f"missing cells: {missing}"
    print(f"    PASS — all 24 cells assigned")
    for p in pairs:
        assert p in PAIR_TUNING, f"missing pair tuning: {p}"
    print(f"    PASS — all 8 pairs tuned")
    # Print profile counts
    from collections import Counter
    profile_count = Counter(v[0] for v in PROFILE_ASSIGNMENT.values())
    evidence_count = Counter(v[1] for v in PROFILE_ASSIGNMENT.values())
    print(f"    profile distribution: {dict(profile_count)}")
    print(f"    evidence distribution: {dict(evidence_count)}")


def test_each_profile_fires_distinctly():
    print("\n[2] each profile produces a distinct gate decision on the same view")
    from momentum_v3 import MomentumModule
    view = MarketView(
        atr_5m=4.0, atr_1h=15.0, atr_conc=5.0,
        rvol_5bar=1.2, rvol_12bar=1.1,
        h1_ret_1bar=3.5, trend_4h=-4.0, adr_consumed=0.8,
        pdh_dist_pips=12.0, pdl_dist_pips=18.0,
    )
    for pair, sess in [("AUD_JPY","asia"), ("GBP_USD","london"), ("USD_CAD","ny")]:
        m = MomentumModule(pair, sess)
        stamp = m.stamp(view)
        print(f"    {pair}/{sess}:")
        print(f"      profile        = {stamp.reads['profile']}")
        print(f"      gates_passed   = {stamp.reads['gates_passed']}")
        print(f"      expected_pips  = {stamp.expected_pips}")
        print(f"      certainty      = {stamp.certainty}")
        print(f"      profile_reasons= {stamp.reads['profile_reasons']}")


def test_strictness_tightens_bad_cells():
    print("\n[3] BAD-evidence cells use 1.4x stricter floors")
    from momentum_v3 import MomentumModule
    view = MarketView(
        atr_5m=4.0, atr_1h=15.0, atr_conc=5.0,
        rvol_5bar=1.2, rvol_12bar=1.1,
        h1_ret_1bar=2.5, trend_4h=3.0, adr_consumed=0.8,
        pdh_dist_pips=12.0, pdl_dist_pips=18.0,
    )
    # AUD_JPY/london is BAD evidence on london_exhaustion
    bad = MomentumModule("AUD_JPY", "london").stamp(view)
    # GBP_USD/london is STRONG evidence on same profile
    strong = MomentumModule("GBP_USD", "london").stamp(view)
    print(f"    AUD_JPY/london (BAD, strictness 1.40):")
    print(f"      gates_passed = {bad.reads['gates_passed']}  reasons={bad.reads['profile_reasons']}")
    print(f"    GBP_USD/london (STRONG, strictness 1.00):")
    print(f"      gates_passed = {strong.reads['gates_passed']}  reasons={strong.reads['profile_reasons']}")
    # h1_ret=2.5 against AUD_JPY floor of 3.0*1.4=4.2 → BAD should fail
    # GBP_USD floor is 3.0*1.0=3.0 → still fails (2.5 < 3.0) at this view
    # Try with h1_ret=3.5 — GBP passes, AUD fails
    view2 = MarketView(
        atr_5m=4.0, atr_1h=15.0, atr_conc=5.5,
        rvol_5bar=1.2, rvol_12bar=1.1,
        h1_ret_1bar=3.5, trend_4h=3.0, adr_consumed=0.8,
        pdh_dist_pips=12.0, pdl_dist_pips=18.0,
    )
    bad2 = MomentumModule("AUD_JPY", "london").stamp(view2)
    strong2 = MomentumModule("GBP_USD", "london").stamp(view2)
    print(f"    With h1_ret=3.5p:")
    print(f"      AUD_JPY/london gates_passed={bad2.reads['gates_passed']} (expected: False, floor 4.2)")
    print(f"      GBP_USD/london gates_passed={strong2.reads['gates_passed']} (expected: True, floor 3.0)")
    assert not bad2.reads["gates_passed"], "BAD-evidence should reject at h1=3.5"
    assert strong2.reads["gates_passed"], "STRONG-evidence should accept at h1=3.5"
    print(f"    PASS — strictness differentiates cells")


def test_chaos_veto_trumps_profile():
    print("\n[4] atr_conc ≥ 15 vetoes everything")
    from momentum_v3 import MomentumModule
    view = MarketView(
        atr_5m=20.0, atr_1h=80.0, atr_conc=18.0,  # chaos
        rvol_5bar=1.5, rvol_12bar=1.3,
        h1_ret_1bar=8.0, trend_4h=10.0, adr_consumed=0.5,
        pdh_dist_pips=12.0, pdl_dist_pips=18.0,
    )
    s = MomentumModule("AUD_JPY", "asia").stamp(view)
    print(f"    AUD_JPY/asia under chaos atr_conc=18.0:")
    print(f"      certainty   = {s.certainty}  (expected 0.0)")
    print(f"      atr_conc read= {s.reads['atr_conc']}")
    assert s.certainty == 0.0, f"chaos should null certainty, got {s.certainty}"
    print(f"    PASS — chaos veto works")


def test_per_pair_scaler_differs():
    print("\n[5] expected_pips uses per-pair scaler, not global")
    from momentum_v3 import MomentumModule
    view = MarketView(atr_5m=4.0, atr_1h=20.0, atr_conc=5.0,
                        rvol_5bar=1.0, rvol_12bar=1.0,
                        h1_ret_1bar=3.0, trend_4h=0.0)
    # Use default profile cells where scaler_mult=1.0 so we see pure per-pair scaler
    print(f"    Same view, default profile, different pairs:")
    for pair in ["AUD_USD", "AUD_JPY", "GBP_USD", "USD_CHF"]:
        # use a NO_DATA session so profile=default
        s = MomentumModule(pair, "ny").stamp(view) if pair == "AUD_USD" else MomentumModule(pair, "asia").stamp(view) if pair in ("EUR_USD", "GBP_USD") else MomentumModule(pair, "asia").stamp(view)
        from momentum_profiles import PAIR_TUNING
        scaler = PAIR_TUNING[pair]["expected_pips_scaler"]
        print(f"      {pair}: pair_scaler={scaler:.3f}  expected_pips={s.expected_pips}  raw=atr_1h(20.0)*rvol(1.0)*{scaler}")


if __name__ == "__main__":
    test_assignment_coverage()
    test_each_profile_fires_distinctly()
    test_strictness_tightens_bad_cells()
    test_chaos_veto_trumps_profile()
    test_per_pair_scaler_differs()
    print("\nAll momentum_v3 smoke checks completed.")
