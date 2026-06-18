"""core/broker/oanda.py — OANDA REST v3 order execution for V5.

Credentials: OANDA_API_URL, OANDA_API_TOKEN, OANDA_ACCOUNT_ID
Loaded from ~/.openclaw/secrets.env — never stored in code.

Public API:
    broker = OandaBroker()
    trade  = broker.place_market("EUR_USD", "long", units=10000, sl_pips=20)
    broker.close_position(trade["id"])
    nav    = broker.account_nav()
    size   = broker.size_units("EUR_USD", direction, sl_pips=20, risk_pct=0.005)
"""
from __future__ import annotations
import json, logging, os, urllib.request
from typing import Optional

from config.pairs import PIP

log = logging.getLogger("v5.broker")

# Hard initial stop on OANDA server — ratchet engages at 60min but we still
# need a backstop for the first 60 minutes before the ratchet floor is set.
DEFAULT_INITIAL_SL_PIPS = 15
RISK_PCT = 0.005   # 0.5% of NAV per trade


def _secrets() -> dict:
    path = os.path.expanduser("~/.openclaw/secrets.env")
    out: dict = {}
    if os.path.exists(path):
        for raw in open(path):
            line = raw.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                k = k.replace("export ", "").strip()
                out[k] = v.strip()
    return out


class OandaBroker:
    """Thin wrapper over OANDA REST v3 — keeps no state beyond credentials."""

    def __init__(self):
        s = _secrets()
        self._base  = s.get("OANDA_API_URL",   "").rstrip("/")
        self._token = s.get("OANDA_API_TOKEN",  "")
        self._acct  = s.get("OANDA_ACCOUNT_ID", "")

    # ── Raw HTTP ─────────────────────────────────────────────────────────────

    def _req(self, method: str, path: str, body: Optional[dict] = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req  = urllib.request.Request(
            self._base + path,
            method=method,
            headers={"Authorization": f"Bearer {self._token}",
                     "Content-Type": "application/json"},
            data=data,
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())

    # ── Account ──────────────────────────────────────────────────────────────

    def account_nav(self) -> float:
        """Current account NAV in account currency (USD)."""
        summary = self._req("GET", f"/v3/accounts/{self._acct}/summary")
        return float(summary["account"]["NAV"])

    def open_positions(self) -> list[dict]:
        """List of currently open trades."""
        return self._req("GET", f"/v3/accounts/{self._acct}/openTrades").get("trades", [])

    # ── Position sizing ──────────────────────────────────────────────────────

    def size_units(
        self,
        pair:      str,
        direction: str,    # "long" | "short"
        sl_pips:   float  = DEFAULT_INITIAL_SL_PIPS,
        risk_pct:  float  = RISK_PCT,
    ) -> int:
        """Compute units so that sl_pips loss = risk_pct of current NAV.

        pip_value_per_unit:
          USD-quoted (EUR/USD, GBP/USD, AUD/USD):  pip_size USD per unit
          USD-based  (USD/JPY, USD/CAD, USD/CHF):  pip_size / current_price USD per unit
          Cross-yen  (AUD/JPY, EUR/JPY):            pip_size / current_price USD per unit
        """
        nav         = self.account_nav()
        risk_amount = nav * risk_pct                 # USD at risk
        pip         = PIP[pair]
        quote       = pair.split("_")[1]             # second currency
        base_       = pair.split("_")[0]

        if quote == "USD":
            # EUR_USD, GBP_USD, AUD_USD: 1 unit moves quote USD by pip_size
            pip_value_per_unit = pip
        else:
            # USD_JPY, USD_CAD, USD_CHF, AUD_JPY, EUR_JPY: need current price
            # Approximate: 1 unit of pair moves account by pip_size / mid_price USD
            # We fetch a quick pricing update; on error fall back to conservative estimate
            try:
                px = self._req(
                    "GET",
                    f"/v3/accounts/{self._acct}/pricing?instruments={pair}"
                )["prices"][0]
                mid = (float(px["bids"][0]["price"]) + float(px["asks"][0]["price"])) / 2
                pip_value_per_unit = pip / mid
            except Exception:
                pip_value_per_unit = pip / 100.0   # conservative fallback

        units = int(risk_amount / (sl_pips * pip_value_per_unit))
        units = max(units, 1000)     # minimum tradeable lot
        log.debug("size_units %s: nav=%.2f risk=%.2f sl=%dp → %d units",
                  pair, nav, risk_amount, sl_pips, units)
        return units

    # ── Trade execution ──────────────────────────────────────────────────────

    def place_market(
        self,
        pair:      str,
        direction: str,    # "long" | "short"
        units:     int,
        sl_pips:   float = DEFAULT_INITIAL_SL_PIPS,
        entry_price: Optional[float] = None,
    ) -> dict:
        """Place a market order with an initial server-side stop loss.

        sl_pips: pips from entry for the hard SL. This is the backstop before
                 the ratchet engages at 60min. Default = 20p.
        Returns the OANDA trade object (has 'id' key for later reference).
        """
        pip     = PIP[pair]
        signed  = units if direction == "long" else -units

        # Fetch live mid to compute SL price if not provided
        if entry_price is None:
            try:
                px = self._req(
                    "GET",
                    f"/v3/accounts/{self._acct}/pricing?instruments={pair}"
                )["prices"][0]
                bid = float(px["bids"][0]["price"])
                ask = float(px["asks"][0]["price"])
                entry_price = ask if direction == "long" else bid
            except Exception as exc:
                raise RuntimeError(f"Cannot fetch pricing for SL calc: {exc}") from exc

        sl_price = (entry_price - sl_pips * pip if direction == "long"
                    else entry_price + sl_pips * pip)

        # OANDA price precision: JPY pairs 3dp, others 5dp
        prec = 3 if "JPY" in pair else 5

        order: dict = {
            "type":       "MARKET",
            "instrument": pair,
            "units":      str(signed),
            "stopLossOnFill": {"price": f"{sl_price:.{prec}f}"},
        }

        result = self._req("POST", f"/v3/accounts/{self._acct}/orders", {"order": order})
        trade  = result.get("orderFillTransaction", {})
        log.info("PLACED %s %s %d units | SL %.{prec}fp | trade_id=%s".replace("{prec}", str(prec)),
                 pair, direction, units, sl_price, trade.get("tradeOpened", {}).get("tradeID", "?"))
        return {"id": trade.get("tradeOpened", {}).get("tradeID", ""),
                "price": trade.get("price", ""),
                "raw": result}

    def close_position(self, trade_id: str) -> dict:
        """Close a specific trade by OANDA trade ID (full close)."""
        result = self._req(
            "PUT",
            f"/v3/accounts/{self._acct}/trades/{trade_id}/close",
            {"units": "ALL"},
        )
        log.info("CLOSED trade %s", trade_id)
        return result

    def move_stop(self, trade_id: str, new_sl_price: float, pair: str) -> dict:
        """Update the server-side stop loss for a trade (ratchet trail updates)."""
        prec = 3 if "JPY" in pair else 5
        return self._req(
            "PUT",
            f"/v3/accounts/{self._acct}/trades/{trade_id}/orders",
            {"stopLoss": {"price": f"{new_sl_price:.{prec}f}"}},
        )
