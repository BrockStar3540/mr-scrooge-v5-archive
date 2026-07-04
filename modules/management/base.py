from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from ..playmaker.playmaker import TradeTicket


@dataclass
class Position:
    ticket:         TradeTicket
    entry_price:    float
    entry_time:     datetime
    units:          int
    oanda_trade_id: str
    pip_size:       float
    initial_sl_price: float = 0.0  # OANDA SL at open; ratchet inits from this
    # Per-trade exit params from cell setup (Phase C: prepared, unused until cutover)
    # When present, RatchetManager reads these instead of exit_config.json.
    # When absent (None), current exit_config behaviour is byte-identical.
    exit_params: Optional[object] = None  # ExitParams from modules.cells (avoid circular import)


@dataclass
class ExitSignal:
    position:   Position
    exit_price: float
    exit_time:  datetime
    reason:     str    # "ratchet_stop" | "time_exit" | "manual"
    net_pips:   float


class TradeManager(ABC):
    """Abstract base -- one instance per open position."""

    @abstractmethod
    def update(self, current_price: float, current_time: datetime) -> Optional[ExitSignal]:
        """Called on each M5 bar. Returns ExitSignal when position should close."""
        ...

    @abstractmethod
    def name(self) -> str:
        ...
