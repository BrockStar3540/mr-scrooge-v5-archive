"""core/engine.py — V5 main loop.

Flow per M5 bar:
  1. Feed: get_views() → list[MarketView] for all pairs
  2. Ratchet tick: for each open position, update peak/floor → move server SL
  3. Exit detection: poll broker.open_positions(); remove managers for closed trades
  4. Signals: stamp each view through direction + momentum modules → PairTicket
  5. Playmaker: pick_best() across all tickets → TradeTicket or None
  6. Entry: size units + place market order via broker; register RatchetManager
"""
from __future__ import annotations
import logging, time
from datetime import datetime, timezone

from config.pairs import PAIRS, PIP
from core.broker.oanda import DEFAULT_INITIAL_SL_PIPS
from modules.signals import build_modules, stamp_pair
from modules.playmaker.playmaker import pick_best
from modules.management.base import Position
from modules.management.ratchet import RatchetManager

log = logging.getLogger("v5.engine")

_SESSIONS = ["asia", "london", "ny"]


class Engine:
    def __init__(self, feed, broker, dry_run: bool = True):
        self.feed     = feed
        self.broker   = broker
        self.dry_run  = dry_run

        self.dir_mods, self.mom_mods = build_modules(PAIRS, _SESSIONS)
        # pair → RatchetManager; one entry per open trade
        self.managers: dict[str, RatchetManager] = {}

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

        # ── Step 1: poll OANDA to detect server-side stop hits ───────────────
        oanda_open: set | None = None
        if not self.dry_run and self.managers:
            try:
                oanda_open = {t["id"] for t in self.broker.open_positions()}
            except Exception as exc:
                log.warning("open_positions failed: %s — skip exit detection", exc)

        # ── Step 2: tick ratchet for each open position ───────────────────────
        for pair in list(self.managers.keys()):
            mgr  = self.managers[pair]
            view = next((v for v in views if v.pair == pair), None)
            mid  = (view.bid + view.ask) / 2.0 if view else mgr.position.entry_price

            # Server-side stop already hit on OANDA
            if oanda_open is not None and mgr.position.oanda_trade_id not in oanda_open:
                log.info("EXIT (server stop hit) %s | trade_id=%s | approx_net=%.2fp",
                         pair, mgr.position.oanda_trade_id, mgr.net_pips(mid))
                del self.managers[pair]
                continue

            # Tick ratchet — may call broker.move_stop() if floor tightens;
            # returns ExitSignal only if local price tracking detects stop crossed
            signal = mgr.update(mid, now)
            if signal:
                log.info("EXIT (local detect) %s | %s | net=%.2fp",
                         pair, signal.reason, signal.net_pips)
                if not self.dry_run:
                    try:
                        self.broker.close_position(mgr.position.oanda_trade_id)
                    except Exception as exc:
                        log.warning("close_position %s: %s (OANDA may have beaten us)", pair, exc)
                del self.managers[pair]

        # ── Step 3: stamp signals ─────────────────────────────────────────────
        tickets = []
        for view in views:
            try:
                ticket = stamp_pair(view, self.dir_mods, self.mom_mods)
                tickets.append(ticket)
            except KeyError:
                pass

        # ── Step 4: playmaker ─────────────────────────────────────────────────
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
            self._open_trade(trade_ticket, views, now)

    def _open_trade(self, ticket, views: list, now: datetime):
        view = next(v for v in views if v.pair == ticket.pair)
        pip  = PIP[ticket.pair]

        entry_price = view.ask if ticket.direction == "long" else view.bid
        units = self.broker.size_units(ticket.pair, ticket.direction)
        trade = self.broker.place_market(
            ticket.pair, ticket.direction, units=units,
            entry_price=entry_price,
        )

        pos = Position(
            ticket=ticket,
            entry_price=entry_price,
            entry_time=now,
            units=units,
            oanda_trade_id=str(trade["id"]),
            pip_size=pip,
        )
        self.managers[ticket.pair] = RatchetManager(
            position=pos,
            broker=self.broker,
            dry_run=self.dry_run,
        )
        log.info("ENTERED %s %s @ %.5f | %d units | SL -%dp | trade_id=%s",
                 ticket.pair, ticket.direction, entry_price, units,
                 DEFAULT_INITIAL_SL_PIPS, trade["id"])
