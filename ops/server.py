"""ops/server.py — V5 control panel HTTP server.

Routes:
  GET /            → ops/panel.html
  GET /api/state   → live engine state JSON  (positions, tickets, events, account)
  GET /api/sysinfo → system metrics JSON     (CPU, RAM, services, logs)

Start via start_dashboard(engine, port=8084) from main.py — runs in daemon thread.
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

# ── Exit-tuning config (TUNE tab) ───────────────────────────────────────────
from pathlib import Path as _Path
_EXIT_CONFIG_PATH = _Path("/home/ubuntu/mr-scrooge-v5/config/exit_config.json")

_EXIT_FIELDS = {
    "initial_sl_pips":   {"min": 1.0,  "max": 100.0, "label": "Initial SL (pips)"},
    "step_engage_min":   {"min": 0.0,  "max": 240.0, "label": "Engage delay (min)"},
    "step_cadence_min":  {"min": 0.1,  "max": 60.0,  "label": "Cadence (min)"},
    "step_trigger_pips": {"min": 0.5,  "max": 100.0, "label": "TP1 trigger (peak pips)"},
    "step_trail_pips":   {"min": 0.1,  "max": 100.0, "label": "Trail behind level (pips)"},
    "step_size_pips":    {"min": 0.5,  "max": 50.0,  "label": "Rung spacing (pips)"},
}
# TP1/TP2 fields. bools use kind=bool; percentages 0..1.
_EXIT_FIELDS_TP = {
    "tp1_enabled":   {"kind": "bool",                "label": "TP1 on"},
    "tp1_at_pips":   {"min": 0.5,  "max": 200.0,     "label": "TP1 peak (pips)"},
    "tp1_close_pct": {"min": 0.0,  "max": 0.95,      "label": "TP1 close %"},
    "tp1_lock_pips": {"min": 0.0,  "max": 100.0,     "label": "TP1 SL lock (pips)"},
    "tp2_enabled":   {"kind": "bool",                "label": "TP2 on"},
    "tp2_at_pips":   {"min": 0.5,  "max": 300.0,     "label": "TP2 peak (pips)"},
    "tp2_close_pct": {"min": 0.0,  "max": 0.95,      "label": "TP2 close %"},
}
_EXIT_FIELDS.update(_EXIT_FIELDS_TP)
_PAIRS_ALL = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]

def _read_exit_config() -> dict:
    try:
        return _j.loads(_EXIT_CONFIG_PATH.read_text())
    except Exception as exc:
        return {"schema": "v2", "defaults": {}, "per_pair": {}, "_error": str(exc)}

def _validate_exit_field(k: str, v):
    if k not in _EXIT_FIELDS:
        raise ValueError(f"unknown field: {k}")
    spec = _EXIT_FIELDS[k]
    if spec.get("kind") == "bool":
        if isinstance(v, bool): return v
        if isinstance(v, (int, float)): return bool(v)
        if isinstance(v, str): return v.strip().lower() in ("1","true","yes","on")
        raise ValueError(f"{k}: expected bool, got {type(v).__name__}")
    f = float(v)
    if not (spec["min"] <= f <= spec["max"]):
        raise ValueError(f"{k}={f} out of bounds [{spec['min']}, {spec['max']}]")
    return f

def _check_tp_cross_rules(merged: dict) -> None:
    """Cross-field validation for TP1/TP2 on the merged effective view."""
    t1e = bool(merged.get("tp1_enabled", False))
    t2e = bool(merged.get("tp2_enabled", False))
    if t2e and not t1e:
        raise ValueError("tp2_enabled requires tp1_enabled (TP2 only fires after TP1)")
    t1p = merged.get("tp1_close_pct"); t2p = merged.get("tp2_close_pct")
    if t1p is not None and t2p is not None and (t1p + t2p) >= 1.0:
        raise ValueError(f"tp1_close_pct + tp2_close_pct = {t1p+t2p:.2f} >= 1.0 (runner must remain)")
    t1at = merged.get("tp1_at_pips"); t2at = merged.get("tp2_at_pips")
    if t1at is not None and t2at is not None and t2at <= t1at:
        raise ValueError(f"tp2_at_pips ({t2at}) must be > tp1_at_pips ({t1at})")

def _validate_exit_cfg(cfg: dict) -> dict:
    out = {"schema": "v2", "defaults": {}, "per_pair": {}}
    defaults = cfg.get("defaults") or {}
    for k in _EXIT_FIELDS:
        if k in defaults:
            out["defaults"][k] = _validate_exit_field(k, defaults[k])
    if "step_trail_pips" in out["defaults"] and "step_trigger_pips" in out["defaults"]:
        if out["defaults"]["step_trail_pips"] >= out["defaults"]["step_trigger_pips"]:
            raise ValueError("defaults: step_trail_pips must be < step_trigger_pips (else first lock <= 0)")
    _check_tp_cross_rules(out["defaults"])
    per = cfg.get("per_pair") or {}
    for pair, ov in per.items():
        if pair not in _PAIRS_ALL:
            raise ValueError(f"unknown pair: {pair}")
        clean = {}
        for k, v in (ov or {}).items():
            clean[k] = _validate_exit_field(k, v)
        merged_trig  = clean.get("step_trigger_pips", out["defaults"].get("step_trigger_pips"))
        merged_trail = clean.get("step_trail_pips",   out["defaults"].get("step_trail_pips"))
        if merged_trig is not None and merged_trail is not None and merged_trail >= merged_trig:
            raise ValueError(f"{pair}: step_trail_pips must be < step_trigger_pips")
        merged_eff = {**out["defaults"], **clean}
        try:
            _check_tp_cross_rules(merged_eff)
        except ValueError as exc:
            raise ValueError(f"{pair}: {exc}") from None
        if clean:
            out["per_pair"][pair] = clean
    return out



# ── Playmaker config (PLAYMAKER tab) ────────────────────────────────────────
_PM_CONFIG_PATH = _Path("/home/ubuntu/mr-scrooge-v5/config/playmaker_config.json")

_PM_FIELDS = {
    "enabled":             {"kind": "bool",                 "label": "Enabled"},
    "min_direction_score": {"min": 0.0,  "max": 1.0,        "label": "Min |direction.score|"},
    "min_dir_certainty":   {"min": 0.0,  "max": 1.0,        "label": "Min direction.certainty"},
    "min_mom_certainty":   {"min": 0.0,  "max": 1.0,        "label": "Min momentum.certainty"},
    "cooldown_after_sl_min": {"min": 0.0, "max": 1440.0,    "label": "Cooldown after losing exit (min)"},
}
_PM_ACCT_FIELDS = {
    "margin_pct_per_trade":  {"min": 0.001, "max": 1.0,  "label": "Margin per trade (fraction of balance)"},
    "max_concurrent_trades": {"min": 1,     "max": 20,   "label": "Max concurrent trades", "int": True},
}
_PM_LEGACY_ACCT_KEYS = {"risk_pct_per_trade": "margin_pct_per_trade"}

def _read_playmaker_config() -> dict:
    try:
        return _j.loads(_PM_CONFIG_PATH.read_text())
    except Exception as exc:
        return {"schema": "v1", "account": {}, "defaults": {}, "per_pair": {}, "_error": str(exc)}

def _validate_pm_field(table: dict, k: str, v):
    if k not in table:
        raise ValueError(f"unknown field: {k}")
    spec = table[k]
    if spec.get("kind") == "bool":
        if isinstance(v, bool): return v
        if isinstance(v, (int, float)): return bool(v)
        if isinstance(v, str): return v.strip().lower() in ("1","true","yes","on")
        raise ValueError(f"{k}: expected bool")
    f = float(v)
    if not (spec["min"] <= f <= spec["max"]):
        raise ValueError(f"{k}={f} out of bounds [{spec['min']}, {spec['max']}]")
    return int(f) if spec.get("int") else f

def _validate_pm_cfg(cfg: dict) -> dict:
    out = {"schema": "v1", "account": {}, "defaults": {}, "per_pair": {}}
    for k, v in (cfg.get("account") or {}).items():
        k = _PM_LEGACY_ACCT_KEYS.get(k, k)   # back-compat rename
        out["account"][k] = _validate_pm_field(_PM_ACCT_FIELDS, k, v)
    for k, v in (cfg.get("defaults") or {}).items():
        out["defaults"][k] = _validate_pm_field(_PM_FIELDS, k, v)
    for pair, ov in (cfg.get("per_pair") or {}).items():
        if pair not in _PAIRS_ALL:
            raise ValueError(f"unknown pair: {pair}")
        clean = {}
        for k, v in (ov or {}).items():
            clean[k] = _validate_pm_field(_PM_FIELDS, k, v)
        if clean:
            out["per_pair"][pair] = clean
    return out

def _write_playmaker_config(cfg: dict) -> None:
    clean = _validate_pm_cfg(cfg)
    clean["_note"] = "Edited via dashboard PLAYMAKER tab."
    tmp = _PM_CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(_j.dumps(clean, indent=2))
    tmp.replace(_PM_CONFIG_PATH)

def _write_exit_config(cfg: dict) -> None:
    clean = _validate_exit_cfg(cfg)
    clean["_note"] = ("Nested schema v2. Edited via dashboard TUNE tab. "
                      "Per-pair fields override defaults for that pair only.")
    tmp = _EXIT_CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(_j.dumps(clean, indent=2))
    tmp.replace(_EXIT_CONFIG_PATH)



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
        # v2/v3 reads: first word of profile labels (drop the "[NO_DATA, strictness=...]" suffix)
        _dr = t.direction.reads or {}
        _mr = t.momentum.reads  or {}
        _firstword = lambda s: (s or "?").split()[0]
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
            # ── v2/v3 profile fields ─────────────────────────────────────
            "active_side":    _dr.get("active_side"),
            "long_profile":   _firstword(_dr.get("long_profile")),
            "short_profile":  _firstword(_dr.get("short_profile")),
            "long_score":     _dr.get("long_score"),
            "short_score":    _dr.get("short_score"),
            "agreement":      _dr.get("agreement"),
            "mom_profile":    _firstword(_mr.get("profile")),
            "gates_passed":   _mr.get("gates_passed"),
            "cert_boost":     _mr.get("cert_boost"),
            "profile_reasons":_mr.get("profile_reasons"),
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
            "atr_h1_relative": round(v.atr_h1_relative, 3) if hasattr(v, "atr_h1_relative") else None,
            "trend_4h":    int(v.trend_4h) if hasattr(v, "trend_4h") else None,
            "atr_conc":    round(v.atr_conc, 3) if hasattr(v, "atr_conc") else None,
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


def start_dashboard(engine: "Engine", port: int = 8084) -> None:
    """Start the dashboard HTTP server in a background daemon thread."""

    def handler_factory(*args, **kwargs):
        return _Handler(engine, *args, **kwargs)

    srv = http.server.HTTPServer(("127.0.0.1", port), handler_factory)
    t = threading.Thread(target=srv.serve_forever, daemon=True, name="v5-dashboard")
    t.start()
    log.info("Dashboard started on port %d — https://[REDACTED-HOST]:%d/", port, port)


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
            elif self.path.startswith("/api/config/exit"):
                body = _j.dumps({
                    "cfg": _read_exit_config(),
                    "fields": _EXIT_FIELDS,
                    "pairs": _PAIRS_ALL,
                }, default=str).encode()
                ctype = "application/json"
                code = 200
            elif self.path.startswith("/api/config/playmaker"):
                body = _j.dumps({
                    "cfg": _read_playmaker_config(),
                    "fields": _PM_FIELDS,
                    "acct_fields": _PM_ACCT_FIELDS,
                    "pairs": _PAIRS_ALL,
                }, default=str).encode()
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

    def do_POST(self):
        try:
            if self.path.startswith("/api/config/exit"):
                length = int(self.headers.get("Content-Length", "0") or 0)
                raw = self.rfile.read(length) if length else b""
                try:
                    payload = _j.loads(raw.decode() or "{}")
                    _write_exit_config(payload)
                    body = _j.dumps({"ok": True, "cfg": _read_exit_config()}).encode()
                    ctype, code = "application/json", 200
                    log.info("exit_config updated via dashboard (defaults=%s per_pair=%s)",
                             list(payload.get("defaults", {}).keys()),
                             list(payload.get("per_pair", {}).keys()))
                except Exception as exc:
                    body = _j.dumps({"ok": False, "error": str(exc)}).encode()
                    ctype, code = "application/json", 400
            elif self.path.startswith("/api/config/playmaker"):
                length = int(self.headers.get("Content-Length", "0") or 0)
                raw = self.rfile.read(length) if length else b""
                try:
                    payload = _j.loads(raw.decode() or "{}")
                    _write_playmaker_config(payload)
                    body = _j.dumps({"ok": True, "cfg": _read_playmaker_config()}).encode()
                    ctype, code = "application/json", 200
                    log.info("playmaker_config updated (account=%s defaults=%s per_pair=%s)",
                             list(payload.get("account", {}).keys()),
                             list(payload.get("defaults", {}).keys()),
                             list(payload.get("per_pair", {}).keys()))
                except Exception as exc:
                    body = _j.dumps({"ok": False, "error": str(exc)}).encode()
                    ctype, code = "application/json", 400
            else:
                body, ctype, code = b"not found", "text/plain", 404
        except Exception as exc:
            log.exception("dashboard POST handler error: %s", exc)
            body = _j.dumps({"ok": False, "error": str(exc)}).encode()
            ctype, code = "application/json", 500
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass
