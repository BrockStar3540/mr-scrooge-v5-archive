"""modules/signals/base.py — Data structures for the V5 signal pipeline."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MarketView:
    """Snapshot of one pair at one M5 bar — raw feed values."""
    pair:          str
    session:       str
    timestamp:     datetime
    # H1 momentum and structure
    h1_ret_1bar:   float   # last completed H1 bar return, pips
    h1_ret_4bar:   float   # cumulative return over last 4 H1 bars, pips
    rsi14:         float   # H1 RSI-14 level (0..100)
    rsi_slope:     float   # H1 RSI 2-bar delta
    zscore_1h:     float   # H1 Z-score vs 20-bar SMA
    ema20_1h_dist: float   # distance from H1 EMA20 as fraction of price (pct)
    # Vol / magnitude
    atr_5m:        float   # 5-min ATR, pips
    atr_1h:        float   # 1H ATR, pips
    rvol_5bar:     float   # relative volume vs 5-bar rolling mean (1.0 = normal)
    adr_consumed:  float   # fraction of today's average daily range used (0..1)
    # Daily context
    d_ret:         float   # today's running daily return, pips
    pdh_dist:      float   # distance from prev-day high, pips
    pdl_dist:      float   # distance from prev-day low, pips
    # Execution
    bid:           float   = 0.0
    ask:           float   = 0.0
    spread_pips:   float   = 0.0


@dataclass
class DirectionStamp:
    """Translation of raw direction indicators for one pair/session bar.

    Produced by DirectionModule.stamp(). Each factor is read against its own
    per-(pair × session) historical distribution so the reads are calibrated
    to that bucket, not global placeholders.
    """
    pair:      str
    session:   str
    timestamp: datetime
    bias:      str     # "long" | "short" | "block"
    score:     float   # -1.0 (strong short) .. +1.0 (strong long), weighted composite
    certainty: float   # 0.0 .. 1.0 — factor agreement × factor extremity
    reads:     dict    # per-factor translation + agreement summary


@dataclass
class MomentumStamp:
    """Translation of raw volatility / magnitude indicators for one pair/session bar.

    Produced by MomentumModule.stamp(). Vol-regime thresholds are loaded from the
    per-(pair × session) ATR distribution (dm_04 decile boundaries), so 'high' means
    genuinely high for this pair/session — not a global absolute.
    """
    pair:          str
    session:       str
    timestamp:     datetime
    vol_regime:    str     # "low" | "normal" | "high" | "extreme"
    expected_pips: float   # calibrated 1-hour expected move estimate in pips
    certainty:     float   # 0.0 .. 1.0 — how definitively in a regime
    reads:         dict    # per-factor translation


@dataclass
class PairTicket:
    """Direction + momentum stamps combined — what the playmaker consumes.

    Produced by stamping a MarketView through both modules for this pair/session.
    Neither stamp knows anything about exit management; they describe raw market state.
    """
    pair:      str
    session:   str
    timestamp: datetime
    direction: DirectionStamp
    momentum:  MomentumStamp

    @property
    def composite_score(self) -> float:
        """Direction strength weighted by both modules' certainty ratings."""
        return self.direction.score * self.direction.certainty * self.momentum.certainty

    @property
    def is_actionable(self) -> bool:
        return (
            self.direction.bias != "block"
            and self.direction.certainty > 0.25
            and self.momentum.vol_regime != "extreme"
        )
