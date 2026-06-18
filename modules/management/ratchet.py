"""modules/management/ratchet.py — Ratchet exit manager for V5.

Spec (from dm_05/dm_09 bake-off):
  - Engage after 60 min if trade is in profit
  - Trail 2.5 pips behind peak price
  - Re-lock every 60 min (tighten the floor if peak moved)
  - No cap — rides the full position; OANDA server closes on stop hit

How stops work:
  1. Entry: broker places a hard initial SL at -20p (server-side backstop)
  2. 60-min mark (if profitable): ratchet engages → broker.move_stop() to peak - 2.5p
  3. Every 60 min after: if peak improved, broker.move_stop() tightens further
  4. OANDA executes the stop the moment price crosses it — no 5-min delay
  5. Engine detects the trade closed via broker.open_positions() polling
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Optional

from .base import Position, ExitSignal, TradeManager

log = logging.getLogger("v5.ratchet")

ENGAGE_MINUTES = 60     # minutes before ratchet can engage
TRAIL_PIPS     = 2.5    # trailing distance in pips
RELOCK_MINUTES = 60     # minutes between SL re-locks (floor tightening)


class RatchetManager(TradeManager):
    """One instance per open trade. Calls broker.move_stop() when floor shifts.

    In dry_run mode the stop calculations run (for logging) but no API call is made.
    """

    def __init__(self, position: Position, broker=None, dry_run: bool = False):
        self.position    = position
        self.broker      = broker
        self.dry_run     = dry_run
        self.pip         = position.pip_size
        self.trail       = TRAIL_PIPS * self.pip
        self.direction   = position.ticket.direction   # "long" | "short"
        self.floor: Optional[float] = None             # current SL price (None = not engaged)
        self.peak_price  = position.entry_price
        self.last_relock = position.entry_time
        self.engaged     = False

    def name(self) -> str:
        return "ratchet"

    def net_pips(self, current_price: float) -> float:
        """Current unrealised P&L in pips."""
        if self.direction == "long":
            return (current_price - self.position.entry_price) / self.pip
        return (self.position.entry_price - current_price) / self.pip

    def update(self, current_price: float, current_time: datetime) -> Optional[ExitSignal]:
        """Called each engine cycle.

        Updates peak and floor; calls broker.move_stop when floor tightens.
        Returns ExitSignal only for belt-and-suspenders local stop detection
        (OANDA's server-side stop is the primary exit mechanism).
        """
        if self.direction == "long":
            return self._update_long(current_price, current_time)
        return self._update_short(current_price, current_time)

    # ── Long ─────────────────────────────────────────────────────────────────

    def _update_long(self, price: float, ts: datetime) -> Optional[ExitSignal]:
        # Update peak
        if price > self.peak_price:
            self.peak_price = price

        elapsed_min   = (ts - self.position.entry_time).total_seconds() / 60
        relock_due    = (ts - self.last_relock).total_seconds() / 60 >= RELOCK_MINUTES
        in_profit     = price > self.position.entry_price

        if elapsed_min >= ENGAGE_MINUTES and in_profit and (not self.engaged or relock_due):
            new_floor = self.peak_price - self.trail
            old_floor = self.floor
            self.floor = new_floor if self.floor is None else max(self.floor, new_floor)
            self.last_relock = ts
            self.engaged = True

            if self.floor != old_floor:
                self._push_stop(ts)

        # Local stop detection (belt-and-suspenders; OANDA server is primary)
        if self.engaged and self.floor is not None and price <= self.floor:
            return self._make_exit(self.floor, ts, "ratchet_stop")

        return None

    # ── Short ────────────────────────────────────────────────────────────────

    def _update_short(self, price: float, ts: datetime) -> Optional[ExitSignal]:
        if price < self.peak_price:
            self.peak_price = price

        elapsed_min  = (ts - self.position.entry_time).total_seconds() / 60
        relock_due   = (ts - self.last_relock).total_seconds() / 60 >= RELOCK_MINUTES
        in_profit    = price < self.position.entry_price

        if elapsed_min >= ENGAGE_MINUTES and in_profit and (not self.engaged or relock_due):
            new_floor = self.peak_price + self.trail
            old_floor = self.floor
            self.floor = new_floor if self.floor is None else min(self.floor, new_floor)
            self.last_relock = ts
            self.engaged = True

            if self.floor != old_floor:
                self._push_stop(ts)

        if self.engaged and self.floor is not None and price >= self.floor:
            return self._make_exit(self.floor, ts, "ratchet_stop")

        return None

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _push_stop(self, ts: datetime) -> None:
        """Move the server-side SL to self.floor."""
        pair = self.position.ticket.pair
        log.info("RATCHET %s %s | engaged=%s floor=%.5f peak=%.5f net_pips=%.1f",
                 pair, "LOCK" if self.engaged else "ENGAGE",
                 self.engaged, self.floor, self.peak_price,
                 self.net_pips(self.peak_price))

        if self.dry_run or self.broker is None:
            return
        try:
            self.broker.move_stop(self.position.oanda_trade_id, self.floor, pair)
        except Exception as exc:
            log.error("move_stop failed %s: %s", pair, exc)

    def _make_exit(self, price: float, ts: datetime, reason: str) -> ExitSignal:
        return ExitSignal(
            position=self.position,
            exit_price=price,
            exit_time=ts,
            reason=reason,
            net_pips=round(self.net_pips(price), 2),
        )
