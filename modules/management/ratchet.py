"""modules/management/ratchet.py — Step-trail ratchet exit manager for V5.

Matches the V4 "6-pip step trail" configuration (2026-06-17 era).

Lock ladder (default config):
  Peak < 10p  →  SL stays at initial (-15p from entry)
  Peak = 10p  →  SL → +4p   (breakeven + 4p guaranteed)
  Peak = 15p  →  SL → +9p
  Peak = 20p  →  SL → +14p
  Peak = 25p  →  SL → +19p
  ...         →  SL → peak_level - 6p  (always 6p behind nearest 5p step)

Config is live-editable — reads config/exit_config.json each cadence check.
Defaults (used if JSON missing/corrupt) match the JSON values.

How stops work:
  1. Entry: broker places hard SL at DEFAULT_INITIAL_SL_PIPS (-15p) server-side
  2. Every 20 min: if peak ≥ trigger (10p), compute step level and lock SL
  3. SL only ever moves in the profitable direction (never backwards)
  4. OANDA executes the stop server-side — engine polls open_positions() for exits
"""
from __future__ import annotations
import json
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Optional

from .base import Position, ExitSignal, TradeManager

log = logging.getLogger("v5.ratchet")

# Defaults — match exit_config.json; used when JSON is missing or corrupt
_DEFAULTS: dict = {
    "step_engage_min":   0.0,    # minutes before first cadence check (0 = immediate)
    "step_cadence_min":  20.0,   # minutes between SL evaluation checks
    "step_size_pips":    5.0,    # ratchet step size (SL level every N pips above trigger)
    "step_trigger_pips": 10.0,   # peak MFE required before first SL movement
    "step_trail_pips":   6.0,    # SL parks this many pips behind the step level
}

_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "exit_config.json"


def _load_config() -> dict:
    try:
        raw = json.loads(_CONFIG_PATH.read_text())
        return {**_DEFAULTS, **{k: float(v) for k, v in raw.items() if not k.startswith("_")}}
    except Exception:
        return _DEFAULTS.copy()


class RatchetManager(TradeManager):
    """One instance per open trade. Calls broker.move_stop() when step level advances.

    In dry_run mode: full logic runs for logging, API call is skipped.
    """

    def __init__(self, position: Position, broker=None, dry_run: bool = False):
        self.position       = position
        self.broker         = broker
        self.dry_run        = dry_run
        self.pip            = position.pip_size
        self.direction      = position.ticket.direction   # "long" | "short"

        # Peak tracks best price seen; initialise to entry
        self.peak_price     = position.entry_price

        # sl_locked_pips: current locked SL expressed as pips from entry in the
        # profit direction (positive = in profit, negative = still below entry).
        # Initialised from the OANDA server SL so we never move it backwards.
        if position.initial_sl_price != 0.0:
            self.sl_locked_pips: Optional[float] = self._price_to_sl_pips(position.initial_sl_price)
        else:
            self.sl_locked_pips = None

        self.last_check_time = position.entry_time

    # ── Public interface ─────────────────────────────────────────────────────

    def name(self) -> str:
        return "ratchet"

    def net_pips(self, current_price: float) -> float:
        """Unrealised P&L in pips at the given price."""
        if self.direction == "long":
            return (current_price - self.position.entry_price) / self.pip
        return (self.position.entry_price - current_price) / self.pip

    def update(self, current_price: float, current_time: datetime) -> Optional[ExitSignal]:
        """Called each engine cycle (every 5 min).

        1. Updates peak.
        2. On cadence: reads config, computes new SL level, calls broker.move_stop
           if the level improves.
        3. Belt-and-suspenders: returns ExitSignal if price crosses the locked SL
           (OANDA server-side stop is the primary exit mechanism).
        """
        self._update_peak(current_price)

        cfg             = _load_config()
        elapsed_total   = (current_time - self.position.entry_time).total_seconds() / 60
        elapsed_check   = (current_time - self.last_check_time).total_seconds() / 60
        engage_ok       = elapsed_total >= cfg["step_engage_min"]
        cadence_ok      = elapsed_check >= cfg["step_cadence_min"]

        if engage_ok and cadence_ok:
            self.last_check_time = current_time
            self._evaluate_and_lock(cfg, current_time)

        # Local belt-and-suspenders stop detection
        return self._check_stop_hit(current_price, current_time)

    # ── Core step logic ───────────────────────────────────────────────────────

    def _evaluate_and_lock(self, cfg: dict, ts: datetime) -> None:
        peak_pips = self._peak_pips()
        new_sl    = self._compute_step_sl(peak_pips, cfg)

        if new_sl is None:
            return   # peak hasn't reached trigger yet

        # Only tighten — never move SL backwards
        if self.sl_locked_pips is not None and new_sl <= self.sl_locked_pips:
            return

        self.sl_locked_pips = new_sl
        self._push_stop(new_sl, peak_pips, ts)

    @staticmethod
    def _compute_step_sl(peak_pips: float, cfg: dict) -> Optional[float]:
        """Return new SL in profit-direction pips from entry, or None if trigger not reached."""
        trigger = cfg["step_trigger_pips"]
        step    = cfg["step_size_pips"]
        trail   = cfg["step_trail_pips"]

        if peak_pips < trigger:
            return None

        level = math.floor((peak_pips - trigger) / step) * step + trigger
        return level - trail

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _update_peak(self, price: float) -> None:
        if self.direction == "long":
            if price > self.peak_price:
                self.peak_price = price
        else:
            if price < self.peak_price:
                self.peak_price = price

    def _peak_pips(self) -> float:
        """MFE in pips (always positive = favorable)."""
        if self.direction == "long":
            return round((self.peak_price - self.position.entry_price) / self.pip, 4)
        return round((self.position.entry_price - self.peak_price) / self.pip, 4)

    def _sl_pips_to_price(self, sl_pips: float) -> float:
        """Convert SL expressed as profit-direction pips from entry → absolute price."""
        if self.direction == "long":
            return self.position.entry_price + sl_pips * self.pip
        return self.position.entry_price - sl_pips * self.pip

    def _price_to_sl_pips(self, price: float) -> float:
        """Inverse: absolute price → profit-direction pips from entry."""
        if self.direction == "long":
            return round((price - self.position.entry_price) / self.pip, 4)
        return round((self.position.entry_price - price) / self.pip, 4)

    def _check_stop_hit(self, price: float, ts: datetime) -> Optional[ExitSignal]:
        if self.sl_locked_pips is None:
            return None
        sl_price = self._sl_pips_to_price(self.sl_locked_pips)
        if self.direction == "long" and price <= sl_price:
            return self._make_exit(sl_price, ts, "ratchet_stop")
        if self.direction == "short" and price >= sl_price:
            return self._make_exit(sl_price, ts, "ratchet_stop")
        return None

    def _push_stop(self, sl_pips: float, peak_pips: float, ts: datetime) -> None:
        pair     = self.position.ticket.pair
        sl_price = self._sl_pips_to_price(sl_pips)
        log.info("RATCHET %s | peak=%.1fp sl=%.1fp → %.5f | trade_id=%s",
                 pair, peak_pips, sl_pips, sl_price, self.position.oanda_trade_id)

        if self.dry_run or self.broker is None:
            return
        try:
            self.broker.move_stop(self.position.oanda_trade_id, sl_price, pair)
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
