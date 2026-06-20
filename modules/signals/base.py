"""modules/signals/base.py — Data structures for the V5 signal pipeline."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MarketView:
    """Snapshot of one pair at one M5 bar — raw feed values.

    Fields that have = 0.0 defaults are wired in the module design but not yet
    populated by the feed; they contribute zero until the feed is implemented.
    """
    pair:          str
    session:       str
    timestamp:     datetime

    # ── H1 timeframe: momentum & structure ──────────────────────────────────
    h1_ret_1bar:   float           # last completed H1 bar return, pips  [+17.6p dir span]
    h1_ret_4bar:   float           # sum of last 4 H1 bar returns, pips  [+7.4p]
    rsi14:         float           # H1 RSI-14 level (0..100)            [+4.8p]
    rsi_slope:     float           # H1 RSI 2-bar delta                  [+10.4p]
    zscore_1h:     float           # H1 Z-score vs 20-bar SMA            [+8.7p]
    ema20_1h_dist: float           # H1 EMA20 distance, frac of price    [+6.4p]
    htf_pct_20:    float = 0.0     # H20 higher-TF percent signal        [+1.9p]
    htf_pct_60:    float = 0.0     # H60 higher-TF percent signal        [+1.0p]

    # ── Distance-to-level signals ────────────────────────────────────────────
    pdh_dist:          float = 0.0  # current price - prev-day high, pips   [+6.0p]
    pdl_dist:          float = 0.0  # current price - prev-day low, pips    [+5.9p]
    pdh_dist_atr_pct:  float = 0.0  # pdh_dist normalized by ATR            [+5.6p]
    pdl_dist_atr_pct:  float = 0.0  # pdl_dist normalized by ATR            [+5.7p]

    # ── Daily context ─────────────────────────────────────────────────────────
    d_ret:          float = 0.0     # today's running daily return, pips     [+7.1p]
    close_pos_daily: float = 0.0    # close position in daily range (0..1)   [-0.3p]
    adr_consumed:   float = 0.0     # fraction of avg daily range used (0..1) [in momentum]

    # ── Mean-reversion signals (5m timeframe) ────────────────────────────────
    bb_pos:         float = 0.0     # Bollinger Band position (0=low, 1=high)  [-0.55p]
    bb_width:       float = 0.0     # Bollinger Band width, pips (in momentum) [+0.12p]
    zscore_5m:      float = 0.0     # 5m Z-score vs 20-bar SMA                [-0.55p]
    ema20_dist_pct: float = 0.0     # 5m EMA20 distance, frac of price        [-0.57p]
    ema5_dist_pips: float = 0.0     # 5m EMA5 distance, pips                  [-0.53p]
    ema50_dist_pct: float = 0.0     # 5m EMA50 distance, frac of price        [-0.39p]
    ema_cross_pips: float = 0.0     # EMA cross signal, pips                  [-0.27p]
    ret_5m:         float = 0.0     # last 5m bar return, pips                [-0.50p]
    ret_15m:        float = 0.0     # last 15m lagged return, pips            [-0.45p]
    ret_30m:        float = 0.0     # last 30m lagged return, pips            [-0.41p]
    ret_1h:         float = 0.0     # last 1h lagged return, pips             [-0.44p]

    # ── Volatility / magnitude ────────────────────────────────────────────────
    atr_5m:         float = 0.0     # 5-min ATR, pips
    atr_1h:         float = 0.0     # 1H ATR, pips
    atr_d_pips:     float = 0.0     # daily ATR, pips
    rvol_5bar:      float = 1.0     # relative volume vs 5-bar mean (1.0=normal)
    rvol_12bar:     float = 1.0     # relative volume vs 12-bar mean
    range_5bar:     float = 0.0     # high-low range over last 5 bars, pips
    range_12bar:    float = 0.0     # high-low range over last 12 bars, pips
    d_range_pips:   float = 0.0     # today's high-low range, pips
    atr_conc:       float = 0.0     # ATR concentration ratio
    atr_h1_relative: float = 1.0    # current 1H ATR / its rolling-mean (1.0=normal; v2/v3 aggregator: >1.6 = elevated)
    trend_4h:       float = 0.0     # sign of last-4 H1 bars net return (+1 up, 0 flat, -1 down)

    # ── Execution ────────────────────────────────────────────────────────────
    bid:            float = 0.0
    ask:            float = 0.0
    spread_pips:    float = 0.0

    # ── v2/v3 module field-name aliases (read-only) ─────────────────────
    @property
    def pdh_dist_pips(self) -> float: return self.pdh_dist
    @property
    def pdl_dist_pips(self) -> float: return self.pdl_dist
    @property
    def ema20_1h_dist_pct(self) -> float: return self.ema20_1h_dist


@dataclass
class DirectionStamp:
    """Translation of raw direction indicators for one pair/session bar."""
    pair:      str
    session:   str
    timestamp: datetime
    bias:      str     # "long" | "short" | "block"
    score:     float   # -1.0 (strong short) .. +1.0 (strong long), weighted composite
    certainty: float   # 0.0..1.0 — factor agreement × factor extremity
    reads:     dict    # per-factor translation + agreement summary


@dataclass
class MomentumStamp:
    """Translation of raw volatility / magnitude indicators for one pair/session bar."""
    pair:          str
    session:       str
    timestamp:     datetime
    vol_regime:    str     # "low" | "normal" | "high" | "extreme"
    expected_pips: float   # calibrated 1-hour expected move estimate in pips
    certainty:     float   # 0.0..1.0 — how definitively in a regime
    reads:         dict    # per-factor translation


@dataclass
class PairTicket:
    """Direction + momentum stamps combined — what the playmaker consumes."""
    pair:      str
    session:   str
    timestamp: datetime
    direction:   DirectionStamp
    momentum:    MomentumStamp
    spread_pips: float = 0.0      # live spread at stamp time — playmaker spread gate

    @property
    def composite_score(self) -> float:
        return self.direction.score * self.direction.certainty * self.momentum.certainty

    @property
    def is_actionable(self) -> bool:
        return (
            self.direction.bias != "block"
            and self.direction.certainty > 0.25
            and self.momentum.vol_regime != "extreme"
        )
