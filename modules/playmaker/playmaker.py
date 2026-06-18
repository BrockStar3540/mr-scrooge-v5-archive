from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from ..signals.base import SignalStack
from config.pairs import PAIR_SESSIONS
from config.sessions import current_session


MAX_OPEN_POSITIONS = 3   # maximum concurrent trades


@dataclass
class TradeTicket:
    """What the playmaker emits -- consumed by trade management."""
    pair:         str
    session:      str
    direction:    str    # "long" | "short"
    score:        float  # composite_score at fire time
    confidence:   float
    magnitude:    float
    vol_regime:   str
    timestamp:    datetime
    rationale:    dict   # which factors drove the decision


def pick_best(
    stacks: list[SignalStack],
    hour_utc: int,
    open_pairs: set[str],
    max_positions: int = MAX_OPEN_POSITIONS,
) -> Optional[TradeTicket]:
    """Given all current signal stacks, emit the highest-quality trade ticket.

    Rules:
      1. Only consider pairs active in the current session.
      2. Skip pairs that already have an open position.
      3. Skip stacks where direction.bias == 'block'.
      4. Rank by composite_score (direction.confidence x momentum.magnitude).
      5. Fire the top-ranked pair if composite_score exceeds the session minimum.
    """
    session = current_session(hour_utc)

    candidates = [
        s for s in stacks
        if s.is_actionable
        and s.pair not in open_pairs
        and session in PAIR_SESSIONS.get(s.pair, [])
    ]

    if not candidates:
        return None

    if len(open_pairs) >= max_positions:
        return None

    best = max(candidates, key=lambda s: s.composite_score)

    # Minimum threshold -- placeholder; will be calibrated per session from dm_09
    MIN_SCORE = 0.4
    if best.composite_score < MIN_SCORE:
        return None

    return TradeTicket(
        pair=best.pair,
        session=session,
        direction=best.direction.bias,
        score=round(best.composite_score, 4),
        confidence=round(best.direction.confidence, 4),
        magnitude=round(best.momentum.magnitude, 4),
        vol_regime=best.momentum.vol_regime,
        timestamp=best.timestamp,
        rationale={
            "direction_score":   best.direction.score,
            "direction_factors": best.direction.factors,
            "momentum_factors":  best.momentum.factors,
        },
    )
