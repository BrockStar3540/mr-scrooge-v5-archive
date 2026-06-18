"""ops/server.py — V5 control panel HTTP server.

Routes:
  GET /            → ops/panel.html
  GET /api/state   → live engine state JSON  (positions, tickets, events, account)
  GET /api/sysinfo → system metrics JSON     (CPU, RAM, services, logs)

Start via start_dashboard(engine, port=8095) from main.py — runs in daemon thread.
"""
from __future__ import annotations
import http.server
import json as _j
import logging
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.engine import Engine

log = logging.getLogger("v5.dashboard")

_PANEL = Path(__file__).resolve().parent / "panel.html"


def _state(engine: "Engine") -> dict:
    now = datetime.now(timezone.utc)

    # ── Account ──────────────────────────────────────────────────────────────
    account: dict = {}
    try:
        account = engine.broker.account_summary()
    except Exception as exc:
        account = {"error": str(exc)}

    # ── Open positions + ratchet state ───────────────────────────────────────
    open_positions = []
    try:
        oanda_trades = {t["id"]: t for t in engine.broker.open_positions()}
    except Exception:
        oanda_trades = {}

    for pair, mgr in engine.managers.items():
        mid = mgr.position.entry_price  # fallback
        for t in oanda_trades.values():
            if t.get("instrument") == pair:
                mid = (float(t.get("currentUnits", 0)) and
                       float(t.get("unrealizedPL", 0)) / abs(float(t.get("currentUnits", 1)))
                       / (0.0001 if "JPY" not in pair else 0.01))
                break

        elapsed = (now - mgr.position.entry_time).total_seconds() / 60
        # current mid from last views
        for v in (engine.last_views or []):
            if v.pair == pair:
                mid = (v.bid + v.ask) / 2
                break

        oanda_t = oanda_trades.get(mgr.position.oanda_trade_id, {})
        upl = float(oanda_t.get("unrealizedPL", 0)) if oanda_t else None

        open_positions.append({
            "pair":          pair,
            "direction":     mgr.direction,
            "entry":         round(mgr.position.entry_price, 5),
            "entry_time":    mgr.position.entry_time.isoformat(),
            "elapsed_min":   round(elapsed, 1),
            "oanda_trade_id": mgr.position.oanda_trade_id,
            "sl_locked_pips": mgr.sl_locked_pips,
            "peak_price":    round(mgr.peak_price, 5),
            "peak_pips":     round(mgr._peak_pips(), 2),
            "sl_price":      round(mgr._sl_pips_to_price(mgr.sl_locked_pips), 5)
                             if mgr.sl_locked_pips is not None else None,
            "net_pips_now":  round(mgr.net_pips(mid), 2),
            "unrealized_pl": round(upl, 2) if upl is not None else None,
        })

    # ── Last tickets (from last engine cycle) ─────────────────────────────────
    last_tickets = []
    for t in (engine.last_tickets or []):
        last_tickets.append({
            "pair":          t.pair,
            "session":       t.session,
            "timestamp":     t.timestamp.isoformat() if hasattr(t.timestamp, "isoformat") else str(t.timestamp),
            "dir_bias":      t.direction.bias,
            "dir_score":     round(t.direction.score, 3),
            "dir_certainty": round(t.direction.certainty, 3),
            "vol_regime":    t.momentum.vol_regime,
            "expected_pips": round(t.momentum.expected_pips, 1),
            "mom_certainty": round(t.momentum.certainty, 3),
            "spread_pips":   round(t.spread_pips, 2),
            "composite":     round(t.composite_score, 3),
            "actionable":    t.is_actionable,
        })

    # ── Last market views (for market-feature chips) ─────────────────────────
    last_views = []
    for v in (engine.last_views or []):
        last_views.append({
            "pair":        v.pair,
            "session":     v.session,
            "bid":         round(v.bid, 5) if hasattr(v, "bid") else None,
            "ask":         round(v.ask, 5) if hasattr(v, "ask") else None,
            "spread_pips": round(v.spread_pips, 2) if hasattr(v, "spread_pips") else None,
            "rsi14":       round(v.rsi14, 1) if hasattr(v, "rsi14") else None,
            "rsi_slope":   round(v.rsi_slope, 2) if hasattr(v, "rsi_slope") else None,
            "h1_ret_1bar": round(v.h1_ret_1bar, 1) if hasattr(v, "h1_ret_1bar") else None,
            "h1_ret_4bar": round(v.h1_ret_4bar, 1) if hasattr(v, "h1_ret_4bar") else None,
            "adr_consumed":round(v.adr_consumed, 2) if hasattr(v, "adr_consumed") else None,
            "htf_pct_20":  round(v.htf_pct_20, 3) if hasattr(v, "htf_pct_20") else None,
            "htf_pct_60":  round(v.htf_pct_60, 3) if hasattr(v, "htf_pct_60") else None,
            "pdh_dist":    round(v.pdh_dist, 1) if hasattr(v, "pdh_dist") else None,
            "pdl_dist":    round(v.pdl_dist, 1) if hasattr(v, "pdl_dist") else None,
        })

    return {
        "account":         account,
        "open_positions":  open_positions,
        "last_tickets":    last_tickets,
        "last_views":      last_views,
        "recent_events":   list(engine.recent_events),
        "cycle_count":     engine.cycle_count,
        "last_cycle_time": engine.last_cycle_time.isoformat() if engine.last_cycle_time else None,
        "dry_run":         engine.dry_run,
        "server_time":     now.isoformat(),
    }


def _sysinfo() -> dict:
    import multiprocessing as _mp, os as _os
    try:
        with open("/proc/loadavg") as f:
            parts = f.read().split()
            load_1, load_5 = parts[0], parts[1]
        with open("/proc/meminfo") as f:
            mem: dict = {}
            for line in f:
                k, v = line.split(":", 1)
                mem[k.strip()] = int(v.split()[0])
        ram_total = mem["MemTotal"]; ram_avail = mem["MemAvailable"]
        ram_used = ram_total - ram_avail; ram_pct = round(ram_used / ram_total * 100)
        cpu_count = _mp.cpu_count()
        cpu_pct = min(round(float(load_1) / cpu_count * 100), 100)
        st = _os.statvfs("/home")
        disk_total = st.f_frsize * st.f_blocks; disk_free = st.f_frsize * st.f_bavail
        disk_pct = round((disk_total - disk_free) / disk_total * 100)
        with open("/proc/uptime") as f:
            secs = int(float(f.read().split()[0]))
        days, rem = divmod(secs, 86400); hrs, rem2 = divmod(rem, 3600); mins = rem2 // 60
        uptime = (f"{days}d " if days else "") + f"{hrs}h {mins}m"
        hostname = _os.uname().nodename
    except Exception as exc:
        return {"error": str(exc)}

    _SHOW = {"mr-scrooge-v5", "openclaw-gateway", "claim-donkey", "mantis-crm"}
    services = []
    try:
        out = subprocess.check_output(
            ["systemctl", "--user", "list-units", "--type=service",
             "--all", "--no-pager", "--no-legend", "--plain"],
            text=True, timeout=5,
        )
        for line in out.strip().splitlines():
            cols = line.split(None, 4)
            if len(cols) < 4:
                continue
            name = cols[0].removesuffix(".service")
            if name not in _SHOW:
                continue
            pid = ""
            try:
                p = subprocess.check_output(
                    ["systemctl", "--user", "show", cols[0], "--property=MainPID"],
                    text=True, timeout=2,
                ).strip()
                pv = p.split("=", 1)[1] if "=" in p else ""
                pid = "" if pv in ("", "0") else pv
            except Exception:
                pass
            services.append({"name": name, "active": cols[2], "sub": cols[3],
                              "desc": cols[4] if len(cols) > 4 else "", "pid": pid})
    except Exception as exc:
        services = [{"name": "error", "active": "unknown", "desc": str(exc), "pid": ""}]

    logs: list[str] = []
    try:
        logs = subprocess.check_output(
            ["journalctl", "--user", "-u", "mr-scrooge-v5", "-o", "cat",
             "-n", "40", "--no-pager"],
            text=True, timeout=5, stderr=subprocess.DEVNULL,
        ).splitlines()
    except Exception:
        logs = ["(journal unavailable)"]

    return {
        "system": {
            "cpu_pct": cpu_pct, "cpu_count": cpu_count,
            "load_1": load_1, "load_5": load_5,
            "ram_pct": ram_pct,
            "ram_used_gb": round(ram_used / 1024 ** 3, 1),
            "ram_total_gb": round(ram_total / 1024 ** 3, 1),
            "disk_pct": disk_pct,
            "uptime": uptime, "hostname": hostname,
        },
        "services": services,
        "logs":     logs,
    }


def start_dashboard(engine: "Engine", port: int = 8095) -> None:
    """Start the dashboard HTTP server in a background daemon thread."""

    def handler_factory(*args, **kwargs):
        return _Handler(engine, *args, **kwargs)

    srv = http.server.HTTPServer(("0.0.0.0", port), handler_factory)
    t = threading.Thread(target=srv.serve_forever, daemon=True, name="v5-dashboard")
    t.start()
    log.info("Dashboard started on port %d — http://[REDACTED-IP]:%d/", port, port)


class _Handler(http.server.BaseHTTPRequestHandler):
    def __init__(self, engine: "Engine", *args, **kwargs):
        self._engine = engine
        super().__init__(*args, **kwargs)

    def do_GET(self):
        try:
            if self.path in ("/", ""):
                if _PANEL.exists():
                    body = _PANEL.read_bytes()
                    ctype = "text/html; charset=utf-8"
                else:
                    body = b"<h1>Panel not found</h1>"
                    ctype = "text/html"
                code = 200
            elif self.path.startswith("/api/state"):
                body = _j.dumps(_state(self._engine), default=str).encode()
                ctype = "application/json"
                code = 200
            elif self.path.startswith("/api/sysinfo"):
                body = _j.dumps(_sysinfo(), default=str).encode()
                ctype = "application/json"
                code = 200
            else:
                body, ctype, code = b"not found", "text/plain", 404
        except Exception as exc:
            log.exception("dashboard handler error: %s", exc)
            body = _j.dumps({"error": str(exc)}).encode()
            ctype, code = "application/json", 500

        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass
