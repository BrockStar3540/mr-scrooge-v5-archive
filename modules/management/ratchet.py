from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional
from .base import Position, ExitSignal, TradeManager


ENGAGE_MINUTES   = 60
TRAIL_PIPS       = 2.5
RELOCK_MINUTES   = 60
MAX_HOLD_MINUTES = 240


class RatchetManager(TradeManager):
    """Ratchet exit: engage after 60min, trail 2.5p, re-lock every 60min, max 4h.

    Source: V4 live system. Validated in dm_05/dm_09.
    """

    def __init__(self, position: Position):
        self.position     = position
        self.pip          = position.pip_size
        self.trail        = TRAIL_PIPS * self.pip
        self.direction    = position.ticket.direction  # "long" | "short"
        self.floor        = None    # None = ratchet not yet engaged
        self.peak_price   = position.entry_price
        self.last_relock  = position.entry_time
        self.engaged      = False

    def name(self) -> str:
        return "ratchet"

    def update(self, current_price: float, current_time: datetime) -> Optional[ExitSignal]:
        elapsed = (current_time - self.position.entry_time).total_seconds() / 60

        # Time exit
        if elapsed >= MAX_HOLD_MINUTES:
            return self._exit(current_price, current_time, "time_exit")

        if self.direction == "long":
            return self._update_long(current_price, current_time, elapsed)
        else:
            return self._update_short(current_price, current_time, elapsed)

    def _update_long(self, price: float, ts: datetime, elapsed: float) -> Optional[ExitSignal]:
        if price > self.peak_price:
            self.peak_price = price

        relock_due = (ts - self.last_relock).total_seconds() / 60 >= RELOCK_MINUTES

        if elapsed >= ENGAGE_MINUTES and (not self.engaged or relock_due):
            new_floor = self.peak_price - self.trail
            self.floor = new_floor if self.floor is None else max(self.floor, new_floor)
            self.last_relock = ts
            self.engaged = True

        if self.engaged and price <= self.floor:
            return self._exit(self.floor, ts, "ratchet_stop")

        return None

    def _update_short(self, price: float, ts: datetime, elapsed: float) -> Optional[ExitSignal]:
        if price < self.peak_price:
            self.peak_price = price

        relock_due = (ts - self.last_relock).total_seconds() / 60 >= RELOCK_MINUTES

        if elapsed >= ENGAGE_MINUTES and (not self.engaged or relock_due):
            new_ceil = self.peak_price + self.trail
            self.floor = new_ceil if self.floor is None else min(self.floor, new_ceil)
            self.last_relock = ts
            self.engaged = True

        if self.engaged and price >= self.floor:
            return self._exit(self.floor, ts, "ratchet_stop")

        return None

    def _exit(self, price: float, ts: datetime, reason: str) -> ExitSignal:
        entry = self.position.entry_price
        if self.direction == "long":
            net_pips = (price - entry) / self.pip
        else:
            net_pips = (entry - price) / self.pip

        return ExitSignal(
            position=self.position, exit_price=price, exit_time=ts,
            reason=reason, net_pips=round(net_pips, 2),
        )
