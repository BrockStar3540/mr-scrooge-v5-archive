from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class MarketView:
    """Snapshot of one pair at one M5 bar."""
    pair:          str
    session:       str
    timestamp:     datetime
    # H1-timeframe signals
    h1_ret_1bar:   float   # last completed H1 bar return, pips
    h1_ret_4bar:   float   # last 4 H1 bars return, pips
    rsi14:         float   # H1 RSI-14
    rsi_slope:     float   # H1 RSI 2-bar delta
    zscore_1h:     float   # H1 Z-score vs 20-bar SMA
    ema20_1h_dist: float   # distance from H1 EMA20, pct
    # Magnitude signals
    atr_5m:        float   # 5-min ATR, pips
    atr_1h:        float   # 1H ATR, pips
    rvol_5bar:     float   # relative volume, 5-bar vs 20-bar
    adr_consumed:  float   # fraction of today's ADR already used (0..1)
    # Daily context
    d_ret:         float   # today's daily return, pips
    pdh_dist:      float   # distance from prev-day high, pips
    pdl_dist:      float   # distance from prev-day low, pips
    # Raw prices
    bid:           float   = 0.0
    ask:           float   = 0.0
    spread_pips:   float   = 0.0


@dataclass
class DirectionOutput:
    """Output of the direction module for one pair."""
    pair:          str
    session:       str
    timestamp:     datetime
    score:         float   # -1.0 (strong short) .. +1.0 (strong long)
    confidence:    float   # 0.0 .. 1.0
    bias:          str     # "long" | "short" | "block"
    factors:       dict    = field(default_factory=dict)  # contributing factor values


@dataclass
class MomentumOutput:
    """Output of the momentum module for one pair."""
    pair:          str
    session:       str
    timestamp:     datetime
    magnitude:     float   # expected move size in pips (0..inf)
    vol_regime:    str     # "low" | "normal" | "high" | "extreme"
    factors:       dict    = field(default_factory=dict)


@dataclass
class SignalStack:
    """Combined direction + momentum for one pair -- what the playmaker consumes."""
    pair:       str
    session:    str
    timestamp:  datetime
    direction:  DirectionOutput
    momentum:   MomentumOutput

    @property
    def composite_score(self) -> float:
        """Direction confidence x magnitude -- the playmaker's ranking key."""
        return self.direction.confidence * self.momentum.magnitude

    @property
    def is_actionable(self) -> bool:
        return self.direction.bias != "block" and self.direction.confidence > 0.3
