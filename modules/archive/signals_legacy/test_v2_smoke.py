"""Smoke test for the new V5 v2 modules — import + instantiate + sample stamp.

Run from /tmp/v5_new_modules/ to verify:
  1. direction_profiles.py parses + per-cell profile assignment loads
  2. direction_v2.py instantiates a DirectionModule and produces a DirectionStamp
  3. momentum_v2.py instantiates a MomentumModule and produces a MomentumStamp
  4. aggregator rules fire when conditions are met

Doesn't depend on V5's `base.py` — we mock the MarketView / *Stamp here so
this is self-contained.
"""
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Stub modules.signals.base since this test runs standalone
sys.path.insert(0, str(Path(__file__).parent))


# Mock the V5 base types so we don't need the real V5 repo to run this
class _BaseFakeModule:
    pass

_signals_mod = type(sys)("signals")
_base_mod = type(sys)("base")


@dataclass
class MarketView:
    timestamp: str = "2026-06-19T00:00:00Z"
    # direction features
    h1_ret_1bar: float = 0.0
    rsi_slope: float = 0.0
    zscore_1h: float = 0.0
    h1_ret_4bar: float = 0.0
    d_ret: float = 0.0
    ema20_1h_dist_pct: float = 0.0
    pdh_dist_pips: float = 0.0
    pdl_dist_pips: float = 0.0
    pdh_dist_atr_pct: float = 0.0
    pdl_dist_atr_pct: float = 0.0
    rsi14: float = 50.0
    htf_pct_20: float = 0.0
    htf_pct_60: float = 0.0
    ema20_dist_pct: float = 0.0
    bb_pos: float = 0.5
    zscore_5m: float = 0.0
    ema5_dist_pips: float = 0.0
    ret_5m: float = 0.0
    ret_15m: float = 0.0
    ret_30m: float = 0.0
    ret_1h: float = 0.0
    ema50_dist_pct: float = 0.0
    close_pos_daily: float = 0.5
    ema_cross_pips: float = 0.0
    # momentum features
    atr_5m: float = 4.0
    rvol_5bar: float = 1.0
    atr_1h: float = 15.0
    rvol_12bar: float = 1.0
    bb_width: float = 8.0
    range_5bar: float = 5.0
    range_12bar: float = 10.0
    atr_d_pips: float = 80.0
    d_range_pips: float = 60.0
    adr_consumed: float = 0.5
    # aggregators (added to view for v2)
    atr_conc: float = 1.0
    atr_h1_relative: float = 1.0


@dataclass
class DirectionStamp:
    pair: str
    session: str
    timestamp: str
    bias: str
    score: float
    certainty: float
    reads: dict = field(default_factory=dict)


@dataclass
class MomentumStamp:
    pair: str
    session: str
    timestamp: str
    vol_regime: str
    expected_pips: float
    certainty: float
    reads: dict = field(default_factory=dict)


_base_mod.MarketView = MarketView
_base_mod.DirectionStamp = DirectionStamp
_base_mod.MomentumStamp = MomentumStamp
_signals_mod.base = _base_mod
sys.modules["modules"] = type(sys)("modules")
sys.modules["modules.signals"] = _signals_mod
sys.modules["modules.signals.base"] = _base_mod
sys.modules["base"] = _base_mod  # for standalone fallback in v2 modules


# Now we can import the v2 modules
from direction_profiles import (
    PROFILE_ASSIGNMENT, AGGREGATOR_RULES,
    get_factor_defs, get_profile_info, apply_aggregator_rules,
)


def test_profile_assignment_coverage():
    print("\n[1] profile assignment coverage:")
    pairs = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
    sessions = ["asia","london","ny"]
    for p in pairs:
        for s in sessions:
            name, evidence = get_profile_info(p, s)
            print(f"    {p}/{s:<7} → {name:<22} [{evidence}]")


def test_factor_defs_weights_normalize():
    print("\n[2] factor_defs total |weight| consistency:")
    for pname, (p, s) in [("AUD_JPY/asia (continuation_strong)", ("AUD_JPY","asia")),
                            ("EUR_USD/ny (reversion)",           ("EUR_USD","ny")),
                            ("USD_CHF/london (default)",          ("USD_CHF","london"))]:
        defs = get_factor_defs(p, s)
        tot = sum(abs(w) for _, w in defs)
        top5 = sorted(defs, key=lambda x: -abs(x[1]))[:5]
        print(f"    {pname}:  total |w|={tot:.2f}   top5={top5}")


def test_aggregator_rules():
    print("\n[3] aggregator rules fire when conditions met:")
    base_weights = {"htf_pct_20": 0.1, "htf_pct_60": 0.1, "h1_ret_4bar": 0.1,
                    "d_ret": 0.1, "bb_pos": -0.05, "ema20_dist_pct": -0.05,
                    "trend_4h": 0.1, "ret_5m": -0.05, "ret_15m": -0.05}
    # case A: low atr_conc, low regime — no rules fire
    view_a = MarketView(atr_conc=1.0, atr_h1_relative=1.0)
    out_a = apply_aggregator_rules(base_weights, view_a)
    print(f"    LOW regime  : htf_pct_20={out_a['htf_pct_20']:.3f}  bb_pos={out_a['bb_pos']:.3f}")
    assert abs(out_a["htf_pct_20"] - 0.1) < 0.001, "no rules should fire for low regime"
    # case B: high atr_conc only
    view_b = MarketView(atr_conc=3.5, atr_h1_relative=1.0)
    out_b = apply_aggregator_rules(base_weights, view_b)
    print(f"    HIGH atr_conc only: htf_pct_20={out_b['htf_pct_20']:.3f} (should be ~0.15)")
    assert abs(out_b["htf_pct_20"] - 0.15) < 0.001, f"atr_conc rule should 1.5x HTF: {out_b['htf_pct_20']}"
    # case C: high atr_h1_relative — both regime rules fire
    view_c = MarketView(atr_conc=1.0, atr_h1_relative=2.0)
    out_c = apply_aggregator_rules(base_weights, view_c)
    # htf_pct_20 should go 0.1 → 0.05 (suppress rule)
    # bb_pos should go -0.05 → -0.065 (reversion rule)
    print(f"    HIGH atr_h1_relative: htf_pct_20={out_c['htf_pct_20']:.3f}  bb_pos={out_c['bb_pos']:.3f}")
    assert abs(out_c["htf_pct_20"] - 0.05) < 0.001
    assert abs(out_c["bb_pos"] - (-0.065)) < 0.001


def test_direction_module():
    print("\n[4] DirectionModule instantiates + stamps:")
    from direction_v2 import DirectionModule
    # AUD_JPY/asia continuation_strong cell — bullish view
    view = MarketView(
        h1_ret_1bar=6.0, h1_ret_4bar=12.0, zscore_1h=1.0,
        ema20_1h_dist_pct=0.05, pdh_dist_pips=15.0, htf_pct_20=2.0,
        atr_conc=3.0,  # high — should trigger HTF amplifier
    )
    mod = DirectionModule("AUD_JPY", "asia")
    stamp = mod.stamp(view)
    print(f"    AUD_JPY/asia  bias={stamp.bias}  score={stamp.score:+.3f}  cert={stamp.certainty:.3f}")
    print(f"      reads.cal      = {stamp.reads['cal']}")
    print(f"      reads.evidence = {stamp.reads['profile_evidence']}")
    print(f"      h1_ret_1bar    = {stamp.reads['h1_ret_1bar']}")
    print(f"      htf_pct_20     = {stamp.reads['htf_pct_20']}")
    # EUR_USD/ny reversion cell — bearish reversion view
    view2 = MarketView(
        ema20_dist_pct=0.06, bb_pos=0.9, zscore_5m=1.5,
        ret_5m=2.0, ret_15m=3.0, close_pos_daily=0.85,
    )
    mod2 = DirectionModule("EUR_USD", "ny")
    stamp2 = mod2.stamp(view2)
    print(f"    EUR_USD/ny    bias={stamp2.bias}  score={stamp2.score:+.3f}  cert={stamp2.certainty:.3f}")
    print(f"      reads.cal      = {stamp2.reads['cal']}")


def test_momentum_module():
    print("\n[5] MomentumModule v2 — expected_pips scaling:")
    from momentum_v2 import MomentumModule, EXPECTED_PIPS_SCALER
    view = MarketView(atr_5m=4.0, atr_1h=15.0, rvol_5bar=1.2, rvol_12bar=1.1,
                       bb_width=8.0, range_5bar=5.0, range_12bar=10.0,
                       pdh_dist_pips=8.0, pdl_dist_pips=12.0)
    mod = MomentumModule("EUR_USD", "ny")
    stamp = mod.stamp(view)
    raw_expected = 15.0 * (1.2 + 1.1) / 2  # what v1 would have computed
    print(f"    raw atr_1h × rvol_factor = {raw_expected:.2f}p")
    print(f"    v2 expected_pips         = {stamp.expected_pips:.2f}p  (scaler={EXPECTED_PIPS_SCALER})")
    print(f"    vol_regime               = {stamp.vol_regime}")
    print(f"    raw_expected read        = {stamp.reads['raw_expected']}")
    print(f"    wall_frac read           = {stamp.reads['wall_frac']}")
    expected_scaled = raw_expected * EXPECTED_PIPS_SCALER
    print(f"    sanity: v2 ≈ raw × {EXPECTED_PIPS_SCALER}? {abs(stamp.expected_pips - expected_scaled) < 1.0}")


if __name__ == "__main__":
    test_profile_assignment_coverage()
    test_factor_defs_weights_normalize()
    test_aggregator_rules()
    test_direction_module()
    test_momentum_module()
    print("\nAll smoke checks completed.")
