"""modules/signals — Direction and momentum module registry.

At startup call build_modules() once to create all 24 (pair × session) instances.
Then call stamp_pair(view, dir_modules, mom_modules) to produce a PairTicket.
"""
from __future__ import annotations
from .base import MarketView, PairTicket
from .direction_v2 import DirectionModule, build_direction_modules
from .momentum_v3  import MomentumModule, build_momentum_modules

__all__ = [
    "MarketView",
    "PairTicket",
    "DirectionModule",
    "MomentumModule",
    "build_modules",
    "stamp_pair",
]


def build_modules(
    pairs: list[str],
    sessions: list[str],
) -> tuple[dict, dict]:
    """Create one DirectionModule + one MomentumModule per (pair × session) bucket.

    Returns (dir_modules, mom_modules) — keyed by (pair, session) tuples.
    Call once at startup; modules are stateless after construction.
    """
    return (
        build_direction_modules(pairs, sessions),
        build_momentum_modules(pairs, sessions),
    )


def stamp_pair(
    view: MarketView,
    dir_modules:  dict[tuple[str,str], DirectionModule],
    mom_modules:  dict[tuple[str,str], MomentumModule],
) -> PairTicket:
    """Stamp a MarketView through its pair/session modules and return a PairTicket."""
    key = (view.pair, view.session)
    d_mod = dir_modules.get(key)
    m_mod = mom_modules.get(key)

    if d_mod is None or m_mod is None:
        raise KeyError(f"No modules registered for {view.pair}/{view.session}")

    direction_stamp = d_mod.stamp(view)
    momentum_stamp  = m_mod.stamp(view, direction_stamp.bias)
    return PairTicket(
        pair=view.pair, session=view.session, timestamp=view.timestamp,
        direction=direction_stamp,
        momentum=momentum_stamp,
        spread_pips=view.spread_pips,
    )
