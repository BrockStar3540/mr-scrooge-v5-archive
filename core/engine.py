"""core/engine.py — V5 main loop.

Flow per M5 bar:
  1. Feed: get_views() → list[MarketView] for all pairs
  2. Signals: stamp each view through direction + momentum modules → PairTicket
  3. Playmaker: pick_best() across all tickets → TradeTicket or None
  4. Entry: size units + place market order via broker
  5. Management: update all open positions; close on ratchet exit signal
"""
from __future__ import annotations
import logging, time
from datetime import datetime, timezone

from config.pairs import PAIRS
from modules.signals import build_modules, stamp_pair
from modules.playmaker.playmaker import pick_best, TradeTicket
from modules.management.base import Position
from modules.management.ratchet import RatchetManager

log = logging.getLogger("v5.engine")

# Sessions that each module was calibrated against
_SESSIONS = ["asia", "london", "ny"]


class Engine:
    def __init__(self, feed, broker, dry_run: bool = True):
        self.feed     = feed
        self.broker   = broker
        self.dry_run  = dry_run

        # Build all 24 (pair × session) signal modules once at startup
        self.dir_mods, self.mom_mods = build_modules(PAIRS, _SESSIONS)
        self.managers: dict[str, RatchetManager] = {}   # pair → manager

        log.info("V5 engine ready | dry_run=%s | %d pairs | %d dir_mods | %d mom_mods",
                 dry_run, len(PAIRS), len(self.dir_mods), len(self.mom_mods))

    def run_forever(self, interval_seconds: int = 300):
        log.info("V5 engine starting (dry_run=%s, interval=%ds)", self.dry_run, interval_seconds)
        while True:
            try:
                self._cycle()
            except Exception as exc:
                log.exception("cycle error: %s", exc)
            time.sleep(interval_seconds)

    def _cycle(self):
        now   = datetime.now(timezone.utc)
        views = self.feed.get_views(PAIRS)

        # 1. Update open positions first; close on exit signal
        for pair, mgr in list(self.managers.items()):
            view = next((v for v in views if v.pair == pair), None)
            if view is None:
                continue
            mid    = (view.bid + view.ask) / 2.0
            signal = mgr.update(mid, now)
            if signal:
                log.info("EXIT %s | %s | net=%.2fp", pair, signal.reason, signal.net_pips)
                if not self.dry_run:
                    self.broker.close_position(signal.position.oanda_trade_id)
                del self.managers[pair]

        # 2. Stamp all views through signal modules
        tickets = []
        for view in views:
            try:
                ticket = stamp_pair(view, self.dir_mods, self.mom_mods)
                tickets.append(ticket)
            except KeyError:
                pass   # pair/session not in calibration — skip silently

        # 3. Playmaker: pick best setup
        trade_ticket = pick_best(
            tickets,
            hour_utc=now.hour,
            open_pairs=set(self.managers.keys()),
        )

        if trade_ticket is None:
            return

        log.info("SIGNAL %s %s | score=%.3f d_cert=%.3f m_cert=%.3f expected=%.1fp vol=%s rivals=%d",
                 trade_ticket.pair, trade_ticket.direction,
                 trade_ticket.score, trade_ticket.dir_certainty, trade_ticket.mom_certainty,
                 trade_ticket.expected_pips, trade_ticket.vol_regime, trade_ticket.rivals)

        if not self.dry_run:
            self._open_trade(trade_ticket, views)

    def _open_trade(self, ticket: TradeTicket, views: list):
        from config.pairs import PIP
        view = next(v for v in views if v.pair == ticket.pair)

        # Size units: 0.5% risk at DEFAULT_INITIAL_SL_PIPS (20p) stop
        units = self.broker.size_units(ticket.pair, ticket.direction)
        trade = self.broker.place_market(
            ticket.pair, ticket.direction, units=units,
            entry_price=view.ask if ticket.direction == "long" else view.bid,
        )

        entry_price = view.ask if ticket.direction == "long" else view.bid
        pos = Position(
            ticket=ticket,
            entry_price=entry_price,
            entry_time=ticket.timestamp,
            units=units,
            oanda_trade_id=str(trade["id"]),
            pip_size=PIP[ticket.pair],
        )
        self.managers[ticket.pair] = RatchetManager(pos)
        log.info("ENTERED %s %s @ %.5f | %d units | trade_id=%s",
                 ticket.pair, ticket.direction, entry_price, units, trade["id"])
