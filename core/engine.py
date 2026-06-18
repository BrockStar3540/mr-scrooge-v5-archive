"""core/engine.py -- V5 main loop.

Flow per M5 bar:
  1. Feed: build MarketView for each pair
  2. Signals: compute SignalStack per pair (direction + momentum)
  3. Playmaker: pick best trade ticket from all active stacks
  4. Entry: place order via broker if ticket fires
  5. Management: update all open positions; close on exit signal
"""
from __future__ import annotations
import time
import logging
from datetime import datetime, timezone
from config.pairs import PAIRS
from modules.signals import compute_signal_stack
from modules.playmaker import pick_best, TradeTicket
from modules.management import Position, RatchetManager

log = logging.getLogger("v5.engine")


class Engine:
    def __init__(self, feed, broker, dry_run: bool = True):
        self.feed       = feed
        self.broker     = broker
        self.dry_run    = dry_run
        self.managers: dict[str, RatchetManager] = {}   # pair -> manager

    def run_forever(self, interval_seconds: int = 300):
        log.info("V5 engine starting (dry_run=%s)", self.dry_run)
        while True:
            try:
                self._cycle()
            except Exception as e:
                log.exception("cycle error: %s", e)
            time.sleep(interval_seconds)

    def _cycle(self):
        now    = datetime.now(timezone.utc)
        views  = self.feed.get_views(PAIRS)
        stacks = [compute_signal_stack(v) for v in views]

        # Update open positions first
        for pair, mgr in list(self.managers.items()):
            mid_price = next((v.bid + v.ask) / 2 for v in views if v.pair == pair)
            signal    = mgr.update(mid_price, now)
            if signal:
                log.info("EXIT %s | %s | %.2fp", pair, signal.reason, signal.net_pips)
                if not self.dry_run:
                    self.broker.close_position(signal.position.oanda_trade_id)
                del self.managers[pair]

        # Playmaker: find best new trade
        ticket = pick_best(
            stacks,
            hour_utc=now.hour,
            open_pairs=set(self.managers.keys()),
        )
        if ticket:
            log.info("ENTRY %s %s | score=%.3f mag=%.3f vol=%s",
                     ticket.pair, ticket.direction, ticket.score,
                     ticket.magnitude, ticket.vol_regime)
            if not self.dry_run:
                self._open_trade(ticket, views)

    def _open_trade(self, ticket: TradeTicket, views):
        from config.pairs import PIP
        view  = next(v for v in views if v.pair == ticket.pair)
        trade = self.broker.place_market(ticket.pair, ticket.direction, units=1000)
        pos   = Position(
            ticket=ticket,
            entry_price=view.ask if ticket.direction == "long" else view.bid,
            entry_time=ticket.timestamp,
            units=1000,
            oanda_trade_id=trade["id"],
            pip_size=PIP[ticket.pair],
        )
        self.managers[ticket.pair] = RatchetManager(pos)
