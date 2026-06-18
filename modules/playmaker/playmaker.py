"""modules/playmaker/playmaker.py — Selects the best trade from active pair tickets.

The playmaker receives one PairTicket per active pair (already stamped by direction
and momentum modules) and picks the highest-quality setup to fire.

CERTAINTY FLOORS — derived from dm_04 raw factor sweep (not exit-management calibrated):

  MIN_DIRECTION_SCORE = 0.25
    The direction module emits "block" at |score| < 0.15.  Score 0.15–0.25 is
    technically non-block but directionally weak (D6-D7 territory on primary
    indicator with poor supporting signal).  0.25+ means the weighted factor
    composite is committed to a side with meaningful conviction.

  MIN_DIR_CERTAINTY = 0.30
    Certainty = factor_extremity × (0.4 + 0.6 × agreement).
    From dm_04: h1_ret_1bar at D9 (norm≈0.85) + 4 supporting factors at D7
    (norm≈0.45) → certainty ≈ 0.30.  Below that, the signal is not consistently
    above the noise floor established by the sweep.  The is_actionable property
    in PairTicket already gates on certainty > 0.25; this adds the stricter
    playmaker-level bar.

  MIN_MOM_CERTAINTY = 0.25
    Momentum certainty 0.25 = ATR is at least 25% of the way from the center of
    the normal regime toward a boundary (low/normal or normal/high).  Below 0.25
    the vol regime is ambiguous and expected_pips estimates are unreliable.

BEST-EDGE PRIORITY when multiple pairs pass all gates simultaneously:
  Primary rank:   abs(composite_score) = abs(direction.score) × dir_certainty × mom_certainty
  Secondary rank: expected_pips        — higher-magnitude setup wins on ties
  This means a moderately strong signal with high dual-certainty beats a raw
  signal with middling certainties, which is the correct preference.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..signals.base import PairTicket
from config.pairs import PAIR_SESSIONS


# ── Certainty floors (dm_04-derived, see module docstring) ──────────────────
MIN_DIRECTION_SCORE = 0.25   # |direction.score| minimum
MIN_DIR_CERTAINTY   = 0.30   # direction.certainty minimum
MIN_MOM_CERTAINTY   = 0.25   # momentum.certainty minimum

# ── Position and spread limits ───────────────────────────────────────────────
MAX_OPEN_POSITIONS = 3

# Maximum spread to accept a trade (pips).  Above these levels the spread
# consumes too much of the expected edge.  0.0 in the ticket = feed not yet
# wired → skip the spread gate (fail-open until feed is live).
_MAX_SPREAD: dict[str, float] = {
    "EUR_USD": 2.5,
    "GBP_USD": 3.0,
    "USD_JPY": 2.0,
    "AUD_USD": 2.5,
    "USD_CAD": 3.0,
    "USD_CHF": 3.0,
    "EUR_JPY": 3.5,
    "AUD_JPY": 4.0,
}
_DEFAULT_MAX_SPREAD = 3.0


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
    rivals:        int = 0 # how many other candidates passed all gates this cycle


def _passes_gates(t: PairTicket) -> bool:
    """All certainty + spread gates the playmaker requires (beyond is_actionable)."""
    d, m = t.direction, t.momentum

    # Gate 1: base checks from signals (bias, dir_certainty>0.25, vol_regime)
    if not t.is_actionable:
        return False

    # Gate 2: direction signal must be meaningfully committed to one side
    if abs(d.score) < MIN_DIRECTION_SCORE:
        return False

    # Gate 3: direction module certainty — D9+ on primary indicator with support
    if d.certainty < MIN_DIR_CERTAINTY:
        return False

    # Gate 4: momentum module certainty — clearly in a vol regime
    if m.certainty < MIN_MOM_CERTAINTY:
        return False

    # Gate 5: spread sanity (skip when spread_pips == 0.0, i.e., feed not live yet)
    if t.spread_pips > 0.0:
        max_spread = _MAX_SPREAD.get(t.pair, _DEFAULT_MAX_SPREAD)
        if t.spread_pips > max_spread:
            return False

    return True


def _edge_rank(t: PairTicket) -> tuple:
    """Higher is better.  Primary: composite magnitude.  Secondary: expected move."""
    return (abs(t.composite_score), t.momentum.expected_pips)


def pick_best(
    tickets:       list[PairTicket],
    hour_utc:      int,
    open_pairs:    set[str],
    max_positions: int = MAX_OPEN_POSITIONS,
) -> Optional[TradeTicket]:
    """Select the best-edge trade ticket from active pair tickets.

    Returns None when:
      - position limit is already reached, or
      - no ticket passes all certainty + spread gates.

    When multiple tickets pass (group arrival), picks the one with the highest
    abs(composite_score), breaking ties by expected_pips.
    """
    if len(open_pairs) >= max_positions:
        return None

    # Step 1: session + position eligibility.
    # Gate on each ticket's OWN session — the value the feed stamped via the
    # dm_04 coarse mapping (asia/london/ny) and that the direction/momentum
    # calibration used. This guarantees the eligibility gate and the
    # calculations can never disagree (the prior bug: a separate fine-grained
    # current_session() returned labels like "ny_mid" that PAIR_SESSIONS never
    # contained, silently disabling all NY-session trading).
    eligible = [
        t for t in tickets
        if t.pair not in open_pairs
        and t.session in PAIR_SESSIONS.get(t.pair, [])
    ]
    if not eligible:
        return None

    # Step 2: all certainty + spread gates
    candidates = [t for t in eligible if _passes_gates(t)]
    if not candidates:
        return None

    # Step 3: rank by edge quality; pick the best
    best = max(candidates, key=_edge_rank)

    return TradeTicket(
        pair=best.pair,
        session=best.session,
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
        rivals=len(candidates) - 1,
    )
