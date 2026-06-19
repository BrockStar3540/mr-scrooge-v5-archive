"""Smoke test for per-(pair × session × direction) modules.

Validates:
  1. direction_profiles: all 48 cells assigned
  2. momentum_profiles: all 48 cells assigned
  3. DirectionModule.stamp() dual-computes long+short and picks stronger
  4. MomentumModule.stamp(view, direction) uses per-direction profile
  5. Same view + different direction → different momentum gate decision
  6. Chaos veto still applies
"""
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


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
    atr_conc: float = 5.0; atr_h1_relative: float = 1.0
    h1_ret_1bar: float = 0.0; h1_ret_4bar: float = 0.0
    trend_4h: float = 0.0
    rsi_slope: float = 0.0; zscore_1h: float = 0.0
    d_ret: float = 0.0; ema20_1h_dist_pct: float = 0.0
    rsi14: float = 50.0; htf_pct_20: float = 0.0; htf_pct_60: float = 0.0
    ema20_dist_pct: float = 0.0; bb_pos: float = 0.5
    zscore_5m: float = 0.0; ema5_dist_pips: float = 0.0
    ret_5m: float = 0.0; ret_15m: float = 0.0; ret_30m: float = 0.0
    ret_1h: float = 0.0; ema50_dist_pct: float = 0.0
    close_pos_daily: float = 0.5; ema_cross_pips: float = 0.0


@dataclass
class DirectionStamp:
    pair: str; session: str; timestamp: str
    bias: str; score: float; certainty: float
    reads: dict = field(default_factory=dict)


@dataclass
class MomentumStamp:
    pair: str; session: str; timestamp: str
    vol_regime: str; expected_pips: float
    certainty: float; reads: dict = field(default_factory=dict)


_base_mod = type(sys)("base")
_base_mod.MarketView = MarketView
_base_mod.DirectionStamp = DirectionStamp
_base_mod.MomentumStamp = MomentumStamp
sys.modules["modules"] = type(sys)("modules")
sys.modules["modules.signals"] = type(sys)("signals")
sys.modules["modules.signals.base"] = _base_mod
sys.modules["base"] = _base_mod


def test_direction_profile_coverage_48():
    print("\n[1] direction_profiles — 48 (pair × session × direction) cells covered")
    from direction_profiles import PROFILE_ASSIGNMENT
    pairs = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
    sessions = ["asia","london","ny"]
    directions = ["long","short"]
    missing = []
    for p in pairs:
        for s in sessions:
            for d in directions:
                if PROFILE_ASSIGNMENT.get(p, {}).get(s, {}).get(d) is None:
                    missing.append((p, s, d))
    assert not missing, f"missing: {missing}"
    from collections import Counter
    flat = [PROFILE_ASSIGNMENT[p][s][d]
            for p in pairs for s in sessions for d in directions]
    pc = Counter(v[0] for v in flat)
    ec = Counter(v[1] for v in flat)
    print(f"    PASS — 48 cells assigned")
    print(f"    profile dist:  {dict(pc)}")
    print(f"    evidence dist: {dict(ec)}")


def test_momentum_profile_coverage_48():
    print("\n[2] momentum_profiles — 48 cells covered")
    from momentum_profiles import PROFILE_ASSIGNMENT
    pairs = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
    sessions = ["asia","london","ny"]
    directions = ["long","short"]
    missing = []
    for p in pairs:
        for s in sessions:
            for d in directions:
                if (p, s, d) not in PROFILE_ASSIGNMENT:
                    missing.append((p, s, d))
    assert not missing, f"missing: {missing}"
    from collections import Counter
    pc = Counter(v[0] for v in PROFILE_ASSIGNMENT.values())
    ec = Counter(v[1] for v in PROFILE_ASSIGNMENT.values())
    print(f"    PASS — 48 cells assigned")
    print(f"    profile dist:  {dict(pc)}")
    print(f"    evidence dist: {dict(ec)}")


def test_direction_dual_compute():
    print("\n[3] DirectionModule dual-computes long+short and picks stronger")
    from direction_v2 import DirectionModule
    # AUD_JPY/asia: long=default NO_DATA, short=continuation_strong STRONG
    # With h1_ret_1bar = -5 (bearish), short profile should win
    view = MarketView(
        h1_ret_1bar=-5.0, h1_ret_4bar=-12.0, trend_4h=-12.0,
        ema20_1h_dist_pct=-0.05, htf_pct_20=-2.0, close_pos_daily=0.85,
        atr_conc=3.0,
    )
    m = DirectionModule("AUD_JPY", "asia")
    s = m.stamp(view)
    print(f"    AUD_JPY/asia bearish view:")
    print(f"      long_profile  = {s.reads['long_profile']}")
    print(f"      short_profile = {s.reads['short_profile']}")
    print(f"      long_score    = {s.reads['long_score']}")
    print(f"      short_score   = {s.reads['short_score']}")
    print(f"      active_side   = {s.reads['active_side']}")
    print(f"      final bias    = {s.bias}  score={s.score:+.3f}")
    assert s.bias == "short", f"bearish view should pick short, got {s.bias}"
    print(f"    PASS — short-profile (continuation_strong STRONG) won")


def test_momentum_per_direction():
    print("\n[4] MomentumModule.stamp(view, direction) uses per-direction profile")
    from momentum_v3 import MomentumModule
    # AUD_JPY/asia: long=default NO_DATA, short=asia_volume_rev STRONG
    view = MarketView(
        atr_5m=4.0, atr_1h=15.0, atr_conc=5.0,
        rvol_5bar=1.2, rvol_12bar=1.1,
        h1_ret_1bar=-3.5, trend_4h=4.0, adr_consumed=0.8,
        pdh_dist_pips=12.0, pdl_dist_pips=18.0,
    )
    m = MomentumModule("AUD_JPY", "asia")
    long_stamp  = m.stamp(view, "long")
    short_stamp = m.stamp(view, "short")
    print(f"    AUD_JPY/asia, same view:")
    print(f"      LONG:")
    print(f"        profile     = {long_stamp.reads['profile']}")
    print(f"        gates       = {long_stamp.reads['gates_passed']}")
    print(f"        certainty   = {long_stamp.certainty}")
    print(f"        reasons     = {long_stamp.reads['profile_reasons']}")
    print(f"      SHORT:")
    print(f"        profile     = {short_stamp.reads['profile']}")
    print(f"        gates       = {short_stamp.reads['gates_passed']}")
    print(f"        certainty   = {short_stamp.certainty}")
    print(f"        reasons     = {short_stamp.reads['profile_reasons']}")
    # Both should differ — long is default (cert based on regime), short uses asia_volume_rev profile
    assert long_stamp.reads['profile'].startswith("default"), "long should be default"
    assert short_stamp.reads['profile'].startswith("asia_volume_rev"), "short should be asia_volume_rev"
    print(f"    PASS — same view, different direction → different profile")


def test_chaos_veto_still_works():
    print("\n[5] atr_conc >= 15 vetoes regardless of direction")
    from momentum_v3 import MomentumModule
    view = MarketView(
        atr_5m=20.0, atr_1h=80.0, atr_conc=18.0,
        rvol_5bar=1.5, rvol_12bar=1.3,
        h1_ret_1bar=8.0, trend_4h=10.0, adr_consumed=0.5,
    )
    m = MomentumModule("AUD_JPY", "asia")
    for d in ("long", "short"):
        s = m.stamp(view, d)
        assert s.certainty == 0.0, f"{d} should be 0.0, got {s.certainty}"
    print(f"    PASS — chaos veto applies in both directions")


def test_bad_evidence_tightens():
    print("\n[6] BAD evidence in one direction → tighter floors than other direction")
    from momentum_v3 import MomentumModule
    # EUR_USD/ny: long=default NO_DATA, short=ny_volatility_strict BAD
    # short side will have 1.5x ny_volatility floors * 1.4 BAD strictness = 2.1x baseline
    view = MarketView(
        atr_5m=4.5, atr_1h=18.0, atr_conc=6.0,
        rvol_5bar=1.0, rvol_12bar=1.0,
        h1_ret_1bar=3.0, trend_4h=3.0, adr_consumed=0.7,
    )
    m = MomentumModule("EUR_USD", "ny")
    long_stamp  = m.stamp(view, "long")
    short_stamp = m.stamp(view, "short")
    print(f"    EUR_USD/ny same view:")
    print(f"      LONG  (default NO_DATA): gates={long_stamp.reads['gates_passed']}")
    print(f"      SHORT (ny_strict BAD):   gates={short_stamp.reads['gates_passed']}  reasons={short_stamp.reads['profile_reasons']}")
    # Short should fail because atr_conc_floor = 4.5*1.5*1.4 = 9.45 > 6.0
    assert not short_stamp.reads['gates_passed'], "BAD short should fail strict floors"
    print(f"    PASS — BAD evidence yields stricter rejection")


if __name__ == "__main__":
    test_direction_profile_coverage_48()
    test_momentum_profile_coverage_48()
    test_direction_dual_compute()
    test_momentum_per_direction()
    test_chaos_veto_still_works()
    test_bad_evidence_tightens()
    print("\nAll per-direction smoke tests pass.")
