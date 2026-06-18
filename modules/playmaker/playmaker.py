"""modules/playmaker/playmaker.py — Selects the best trade from active pair tickets.

The playmaker receives one PairTicket per active pair (already stamped by direction
and momentum modules) and picks the highest-quality setup to fire.

Selection logic:
  1. Filter to pairs active in the current session (PAIR_SESSIONS config).
  2. Drop pairs that already have an open position.
  3. Drop tickets where direction.bias == 'block'.
  4. Drop extreme vol-regime (momentum.vol_regime == 'extreme').
  5. Rank by composite_score = direction.score × direction.certainty × momentum.certainty.
  6. Fire the top-ranked ticket if composite_score >= MIN_SCORE threshold.

TradeTicket is what flows downstream to trade management (RatchetManager or any other
exit strategy). It carries direction and magnitude readings but no exit instructions —
those are entirely the trade management module's concern.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..signals.base import PairTicket
from config.pairs import PAIR_SESSIONS
from config.sessions import current_session


MAX_OPEN_POSITIONS = 3
MIN_COMPOSITE_SCORE = 0.20   # placeholder; will be calibrated per session from dm_04 data


@dataclass
class TradeTicket:
    """What the playmaker emits — consumed by trade management, not signal modules."""
    pair:          str
    session:       str
    direction:     str     # "long" | "short"
    score:         float   # composite_score at fire time
    dir_certainty: float   # direction module certainty
    mom_certainty: float   # momentum module certainty
    vol_regime:    str     # from momentum stamp
    expected_pips: float   # from momentum stamp
    timestamp:     datetime
    reads:         dict    # direction.reads + momentum.reads for logging/debug


def pick_best(
    tickets:        list[PairTicket],
    hour_utc:       int,
    open_pairs:     set[str],
    max_positions:  int = MAX_OPEN_POSITIONS,
) -> Optional[TradeTicket]:
    """Select the best trade ticket from active pair tickets.

    Returns None when no actionable setup exists or position limit is reached.
    """
    if len(open_pairs) >= max_positions:
        return None

    session = current_session(hour_utc)

    candidates = [
        t for t in tickets
        if t.is_actionable
        and t.pair not in open_pairs
        and session in PAIR_SESSIONS.get(t.pair, [])
    ]

    if not candidates:
        return None

    best = max(candidates, key=lambda t: abs(t.composite_score))

    if abs(best.composite_score) < MIN_COMPOSITE_SCORE:
        return None

    return TradeTicket(
        pair=best.pair,
        session=session,
        direction=best.direction.bias,
        score=round(best.composite_score, 4),
        dir_certainty=round(best.direction.certainty, 4),
        mom_certainty=round(best.momentum.certainty, 4),
        vol_regime=best.momentum.vol_regime,
        expected_pips=best.momentum.expected_pips,
        timestamp=best.timestamp,
        reads={
            "direction": best.direction.reads,
            "momentum":  best.momentum.reads,
        },
    )
