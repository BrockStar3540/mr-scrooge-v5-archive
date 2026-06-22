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
import collections
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from config.pairs import PAIRS, PIP
from core.broker.oanda import DEFAULT_INITIAL_SL_PIPS
from modules.signals import build_modules, stamp_pair
from modules.playmaker.playmaker import pick_best, TradeTicket, pm_margin_pct, pm_inverted_shadow_cells
from modules.management.base import Position
from modules.management.ratchet import RatchetManager, initial_sl_pips_for

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
        # pair -> datetime of last losing exit (in-memory; playmaker cooldown)
        self._sl_history: dict[str, datetime] = {}
        # (pair, session, dir) -> bool actionable last cycle; rising edge => SHADOW_INVERT log
        self._invert_shadow_actionable: dict[tuple, bool] = {}

        # Dashboard state — updated each cycle
        self.last_views:        list = []
        self.last_tickets:      list = []
        self.last_trade_ticket: Optional[TradeTicket] = None
        self.recent_events:     collections.deque = collections.deque(maxlen=40)
        self.cycle_count:       int = 0
        self.last_cycle_time:   Optional[datetime] = None

        log.info("V5 engine ready | dry_run=%s | %d pairs | %d dir_mods | %d mom_mods",
                 dry_run, len(PAIRS), len(self.dir_mods), len(self.mom_mods))

        if not dry_run:
            self._recover_open_positions()

    def _recover_open_positions(self) -> None:
        """Adopt any existing OANDA open trades at startup.

        Allows clean V4→V5 handoff without closing positions, and survives
        process restarts without orphaning trades.
        """
        try:
            trades = self.broker.open_positions()
        except Exception as exc:
            log.error("recovery: cannot fetch open positions: %s", exc)
            return

        if not trades:
            log.info("recovery: no open trades to adopt")
            return

        now = datetime.now(timezone.utc)
        for t in trades:
            pair = t["instrument"]
            if pair in self.managers:
                continue
            if pair not in PIP:
                log.warning("recovery: unknown pair %s — skipping", pair)
                continue

            units_signed = int(t["currentUnits"])
            direction    = "long" if units_signed > 0 else "short"
            entry_price  = float(t["price"])
            entry_time   = datetime.fromisoformat(t["openTime"].replace("Z", "+00:00"))
            trade_id     = str(t["id"])

            # Stub ticket — just enough for RatchetManager to know pair + direction
            ticket = TradeTicket(
                pair=pair, session="recovery", direction=direction,
                score=0.0, dir_certainty=0.0, mom_certainty=0.0,
                vol_regime="unknown", expected_pips=0.0,
                timestamp=entry_time, reads={},
            )
            oanda_sl = t.get("stopLossOrder", {}).get("price")
            initial_sl_price = float(oanda_sl) if oanda_sl else 0.0
            pos = Position(
                ticket=ticket,
                entry_price=entry_price,
                entry_time=entry_time,
                units=abs(units_signed),
                oanda_trade_id=trade_id,
                pip_size=PIP[pair],
                initial_sl_price=initial_sl_price,
            )
            self.managers[pair] = RatchetManager(
                position=pos,
                broker=self.broker,
                dry_run=self.dry_run,
                initial_units=abs(int(float(t.get("initialUnits", t.get("currentUnits", 0))))),
                tp1_done=(abs(float(t.get("currentUnits", 0))) < abs(float(t.get("initialUnits", t.get("currentUnits", 0))))),
                tp2_done=False,
            )
            elapsed_min = (now - entry_time).total_seconds() / 60
            log.info("RECOVERED %s %s | entry=%.5f | trade_id=%s | elapsed=%.1fm",
                     pair, direction, entry_price, trade_id, elapsed_min)
            self.recent_events.append(
                f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} RECOVERED {pair} {direction} @ {entry_price:.5f}"
            )

    def run_forever(self, scan_interval_seconds: int = 300, manage_interval_seconds: int = 30):
        log.info("V5 engine starting (dry_run=%s, scan=%ds, manage=%ds)",
                 self.dry_run, scan_interval_seconds, manage_interval_seconds)
        ticks_per_scan = max(1, round(scan_interval_seconds / manage_interval_seconds))
        i = 0
        while True:
            try:
                if i % ticks_per_scan == 0:
                    self._cycle()                              # full: manage + scan + enter
                else:
                    self._manage(datetime.now(timezone.utc))   # fast: exit-detect + ratchet only
            except Exception as exc:
                log.exception("loop error: %s", exc)
            time.sleep(manage_interval_seconds)
            i += 1

    def _manage(self, now: datetime) -> None:
        """Fast path -- runs every manage_interval. Detect server-side stop hits and
        tick the ratchet for each open position using a cheap pricing() poll (no
        candle fetch). The ratchet re-locks at step_cadence_min granularity, so this
        is what lets the trailing stop follow the peak between 5-min scan cycles."""
        if self.dry_run or not self.managers:
            return

        try:
            oanda_open = {t["id"] for t in self.broker.open_positions()}
        except Exception as exc:
            log.warning("open_positions failed: %s -- skip exit detection", exc)
            oanda_open = None

        for pair in list(self.managers.keys()):
            mgr = self.managers[pair]
            try:
                bid, ask = self.feed.pricing(pair)
                mid = (bid + ask) / 2.0
            except Exception as exc:
                log.warning("pricing %s failed: %s -- using entry price", pair, exc)
                mid = mgr.position.entry_price

            # Server-side stop already hit on OANDA
            if oanda_open is not None and mgr.position.oanda_trade_id not in oanda_open:
                _net = mgr.net_pips(mid)
                log.info("EXIT (server stop hit) %s | trade_id=%s | approx_net=%.2fp",
                         pair, mgr.position.oanda_trade_id, _net)
                self.recent_events.append(
                    f"{now.strftime('%H:%M:%S')} EXIT {pair} server-stop approx {'+' if _net >= 0 else ''}{_net:.1f}p"
                )
                if _net < 0:
                    self._sl_history[pair] = now
                del self.managers[pair]
                continue

            # Tick ratchet -- may call broker.move_stop() if the floor tightens
            signal = mgr.update(mid, now)
            if signal:
                log.info("EXIT (local detect) %s | %s | net=%.2fp",
                         pair, signal.reason, signal.net_pips)
                self.recent_events.append(
                    f"{now.strftime('%H:%M:%S')} EXIT {pair} {signal.reason} {'+' if signal.net_pips >= 0 else ''}{signal.net_pips:.1f}p"
                )
                if not self.dry_run:
                    try:
                        self.broker.close_position(mgr.position.oanda_trade_id)
                    except Exception as exc:
                        log.warning("close_position %s: %s (OANDA may have beaten us)", pair, exc)
                if signal.net_pips < 0:
                    self._sl_history[pair] = now
                del self.managers[pair]

    def _cycle(self):
        now = datetime.now(timezone.utc)

        # Steps 1+2: manage open positions (exit detection + ratchet)
        self._manage(now)

        # Step 3: full candles for signal stamping
        views = self.feed.get_views(PAIRS)

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
            now=now,
            sl_history=self._sl_history,
        )

        # ── Update dashboard state ────────────────────────────────────────────
        self.last_views        = views
        self.last_tickets      = tickets
        self.last_trade_ticket = trade_ticket
        self.cycle_count      += 1
        self.last_cycle_time   = now

        # ── Shadow-inverted cells: log signal stream on rising edge (NOT traded) ──
        # research/sessions/2026-06-21_percell_exhaustion/: GBP_USD/ny + EUR_JPY/ny
        # are NY momentum-fade cells; inverting them looks +2.5-3.0p net of spread.
        # Log each fresh actionable signal so a later job measures the 1H forward.
        _shadow_cells = pm_inverted_shadow_cells()
        if _shadow_cells:
            for t in tickets:
                if (t.pair, t.session) not in _shadow_cells:
                    continue
                key = (t.pair, t.session, t.direction.bias)
                was = self._invert_shadow_actionable.get(key, False)
                is_now = t.is_actionable
                self._invert_shadow_actionable[key] = is_now
                if is_now and not was:   # rising edge = fresh signal
                    _v = next((v for v in views if v.pair == t.pair), None)
                    _mid = ((_v.bid + _v.ask) / 2.0) if _v and _v.bid and _v.ask else 0.0
                    _inv = "short" if t.direction.bias == "long" else "long"
                    log.info("SHADOW_INVERT %s %s | v5_dir=%s inverted_dir=%s score=%.3f "
                             "d_cert=%.3f m_cert=%.3f mid=%.5f ts=%s",
                             t.pair, t.session, t.direction.bias, _inv,
                             t.direction.score, t.direction.certainty, t.momentum.certainty,
                             _mid, now.isoformat())

        if trade_ticket is None:
            return

        dr = trade_ticket.reads.get("direction", {})
        mr = trade_ticket.reads.get("momentum", {})
        # First word of each profile label so log stays single-token-per-field (parseable)
        _lp = (dr.get("long_profile",  "?") or "?").split()[0]
        _sp = (dr.get("short_profile", "?") or "?").split()[0]
        _mp = (mr.get("profile",       "?") or "?").split()[0]
        # Shadow features (logged but NOT used in scoring until 2026-07-04 evaluation)
        _view = next((v for v in views if v.pair == trade_ticket.pair), None)
        _vortex = getattr(_view, "vortex_diff_h1", 0.0) if _view else 0.0
        _cpd    = getattr(_view, "close_pos_daily", 0.0) if _view else 0.0
        _inv_live = getattr(trade_ticket, "inverted_live", False)
        _sig_dir  = dr.get("signal_direction", trade_ticket.direction)
        log.info("SIGNAL %s %s | score=%.3f d_cert=%.3f m_cert=%.3f expected=%.1fp vol=%s rivals=%d "
                 "| active_side=%s long_prof=%s short_prof=%s mom_prof=%s gates=%s cert_boost=%s "
                 "| shadow_vortex_diff=%.4f shadow_close_pos=%.4f"
                 "%s",
                 trade_ticket.pair, trade_ticket.direction,
                 trade_ticket.score, trade_ticket.dir_certainty, trade_ticket.mom_certainty,
                 trade_ticket.expected_pips, trade_ticket.vol_regime, trade_ticket.rivals,
                 dr.get("active_side", "?"), _lp, _sp, _mp,
                 mr.get("gates_passed", "?"), mr.get("cert_boost", "?"),
                 _vortex, _cpd,
                 (f" | INVERTED_LIVE signal_dir={_sig_dir} trade_dir={trade_ticket.direction}"
                  if _inv_live else ""))

        if not self.dry_run:
            self._open_trade(trade_ticket, views, now)

    def _open_trade(self, ticket: TradeTicket, views: list, now: datetime):
        view = next(v for v in views if v.pair == ticket.pair)
        pip  = PIP[ticket.pair]

        entry_price = view.ask if ticket.direction == "long" else view.bid
        initial_sl = initial_sl_pips_for(ticket.pair)
        units = self.broker.size_units(ticket.pair, ticket.direction,
                                       margin_pct=pm_margin_pct())
        trade = self.broker.place_market(
            ticket.pair, ticket.direction, units=units,
            entry_price=entry_price, sl_pips=initial_sl,
        )

        initial_sl_price = (entry_price - initial_sl * pip
                            if ticket.direction == "long"
                            else entry_price + initial_sl * pip)
        pos = Position(
            ticket=ticket,
            entry_price=entry_price,
            entry_time=now,
            units=units,
            oanda_trade_id=str(trade["id"]),
            pip_size=pip,
            initial_sl_price=initial_sl_price,
        )
        self.managers[ticket.pair] = RatchetManager(
            position=pos,
            broker=self.broker,
            dry_run=self.dry_run,
            initial_units=units,
        )
        log.info("ENTERED %s %s @ %.5f | %d units | SL -%.1fp | trade_id=%s",
                 ticket.pair, ticket.direction, entry_price, units,
                 initial_sl, trade["id"])
        self.recent_events.append(
            f"{now.strftime('%H:%M:%S')} ENTER {ticket.pair} {ticket.direction} @ {entry_price:.5f}"
        )
