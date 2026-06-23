#!/usr/bin/env python3
"""V5 ratchet + exit assessment — pull OANDA M1 candles per trade,
compute MFE (max favorable excursion) and MAE (max adverse excursion).

For each trade: how high did the pip-pnl go during hold (MFE),
how low (MAE), vs the realized net at exit and the initial SL.

This tells us:
  - "Left on table" = MFE − realized (ratchet too tight?)
  - "SL margin" = MAE / −SL (how close to getting stopped)
  - Pattern: are we exiting near peak (good ratchet) or way below (bad)?
"""
from __future__ import annotations
import os, re, subprocess, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
import requests

PIP = {
    "USD_JPY": 0.01, "EUR_JPY": 0.01, "AUD_JPY": 0.01, "GBP_JPY": 0.01,
    "EUR_USD": 0.0001, "GBP_USD": 0.0001, "AUD_USD": 0.0001, "USD_CHF": 0.0001,
    "USD_CAD": 0.0001, "NZD_USD": 0.0001,
}
INITIAL_SL_PIPS = 20.0   # per V5 — confirm by reading initial_sl_pips_for() if needed
SINCE = "2026-06-22 04:14:00"

# Load OANDA creds
env_path = Path.home() / ".openclaw" / "secrets.env"
for line in env_path.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")
TOKEN = os.environ.get("OANDA_API_TOKEN") or os.environ.get("OANDA_API_KEY")
ACCOUNT_ID = os.environ.get("OANDA_ACCOUNT_ID")
OANDA_URL = os.environ.get("OANDA_API_URL", "https://api-fxpractice.oanda.com").rstrip("/")
if not TOKEN:
    print("ERROR: no OANDA_API_TOKEN in env", file=sys.stderr)
    sys.exit(1)
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
BASE = f"{OANDA_URL}/v3"

ENTERED = re.compile(
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ INFO v5\.engine\s+ENTERED "
    r"(\w+) (long|short) @ ([\d.]+) \| (\d+) units \| SL ([+-]?[\d.]+)p \| trade_id=(\d+)"
)
EXIT = re.compile(
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ INFO v5\.engine\s+EXIT.*?"
    r"(\w+) \| trade_id=(\d+) \| approx_net=([+-]?[\d.]+)p"
)


def parse_journal():
    raw = subprocess.check_output(
        ["journalctl", "--user", "-u", "mr-scrooge-v5",
         "--since", SINCE, "--no-pager", "-o", "cat"],
        text=True,
    )
    entries, exits = {}, {}
    for line in raw.splitlines():
        if m := ENTERED.search(line):
            ts, pair, dr, ep, units, sl, tid = m.groups()
            entries[tid] = {"ts": ts, "pair": pair, "dir": dr,
                            "entry": float(ep), "units": int(units),
                            "sl_pips": float(sl)}
        elif m := EXIT.search(line):
            ts, pair, tid, net = m.groups()
            exits[tid] = {"ts": ts, "pair": pair, "net": float(net)}
    return entries, exits


def iso_z(s: str, pad_seconds: int = 0) -> str:
    dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    if pad_seconds:
        dt += timedelta(seconds=pad_seconds)
    return dt.isoformat().replace("+00:00", "Z")


def fetch_candles(pair: str, ts_from: str, ts_to: str, granularity: str = "M1"):
    url = f"{BASE}/instruments/{pair}/candles"
    params = {"from": ts_from, "to": ts_to,
              "granularity": granularity, "price": "M"}
    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("candles", [])


def mfe_mae(pair: str, direction: str, entry: float, candles: list) -> tuple[float, float]:
    pip = PIP[pair]
    if not candles:
        return 0.0, 0.0
    highs = [float(c["mid"]["h"]) for c in candles if c.get("complete") or "mid" in c]
    lows  = [float(c["mid"]["l"]) for c in candles if c.get("complete") or "mid" in c]
    if not highs or not lows:
        return 0.0, 0.0
    if direction == "long":
        mfe = (max(highs) - entry) / pip
        mae = (min(lows)  - entry) / pip
    else:
        mfe = (entry - min(lows))  / pip
        mae = (entry - max(highs)) / pip
    return round(mfe, 2), round(mae, 2)


def run():
    entries, exits = parse_journal()
    closed = sorted([tid for tid in entries if tid in exits],
                    key=lambda t: entries[t]["ts"])
    if not closed:
        print("No closed trades since", SINCE)
        return

    rows = []
    for tid in closed:
        e, x = entries[tid], exits[tid]
        candles = fetch_candles(e["pair"], iso_z(e["ts"]), iso_z(x["ts"], pad_seconds=1),
                                granularity="M1")
        mfe, mae = mfe_mae(e["pair"], e["dir"], e["entry"], candles)
        hold_min = (datetime.strptime(x["ts"], "%Y-%m-%d %H:%M:%S")
                    - datetime.strptime(e["ts"], "%Y-%m-%d %H:%M:%S")).total_seconds() / 60.0
        left_on_table = round(mfe - x["net"], 2)
        sl_margin_pct = round(100.0 * abs(mae) / e["sl_pips"], 1)
        rows.append({"tid": tid, "pair": e["pair"], "dir": e["dir"],
                     "hold_m": round(hold_min, 1), "n_candles": len(candles),
                     "entry": e["entry"], "realized": x["net"],
                     "MFE": mfe, "MAE": mae,
                     "left_on_table": left_on_table,
                     "sl_used_pct": sl_margin_pct})

    # Per-trade table
    print(f"V5 ratchet + exit assessment ({len(rows)} closed trades since {SINCE})\n")
    print(f"{'tid':<5} {'pair':<8} {'dir':<5} {'hold':>5} {'realized':>9} "
          f"{'MFE':>7} {'MAE':>7} {'left':>7} {'sl%':>5}")
    print("-" * 67)
    for r in rows:
        print(f"{r['tid']:<5} {r['pair']:<8} {r['dir']:<5} "
              f"{r['hold_m']:>4.0f}m {r['realized']:>+8.2f}p "
              f"{r['MFE']:>+6.1f}p {r['MAE']:>+6.1f}p "
              f"{r['left_on_table']:>+6.1f}p {r['sl_used_pct']:>4.0f}%")

    # Aggregates
    n = len(rows)
    wins = [r for r in rows if r["realized"] > 0]
    losses = [r for r in rows if r["realized"] <= 0]
    print(f"\n=== aggregates (n={n}) ===")
    print(f"  realized:  mean={mean(r['realized'] for r in rows):+.2f}p, "
          f"sum={sum(r['realized'] for r in rows):+.2f}p, wr={100*len(wins)/n:.0f}%")
    print(f"  MFE:       mean={mean(r['MFE'] for r in rows):+.2f}p, "
          f"max={max(r['MFE'] for r in rows):+.2f}p")
    print(f"  MAE:       mean={mean(r['MAE'] for r in rows):+.2f}p, "
          f"worst={min(r['MAE'] for r in rows):+.2f}p")
    print(f"  left_on_table: mean={mean(r['left_on_table'] for r in rows):+.2f}p"
          f" (positive = ratchet exited below the peak)")
    print(f"  sl_used:   mean={mean(r['sl_used_pct'] for r in rows):.0f}% of {INITIAL_SL_PIPS:.0f}p initial SL")

    if wins:
        print(f"\n  WINS  ({len(wins)}): mean_realized={mean(r['realized'] for r in wins):+.2f}p, "
              f"mean_MFE={mean(r['MFE'] for r in wins):+.2f}p, "
              f"mean_capture={100*mean(r['realized']/max(r['MFE'],0.01) for r in wins):.0f}% of MFE")
    if losses:
        print(f"  LOSSES ({len(losses)}): mean_realized={mean(r['realized'] for r in losses):+.2f}p, "
              f"mean_MFE={mean(r['MFE'] for r in losses):+.2f}p "
              f"(MFE>0 = trade went profitable before reversing)")


if __name__ == "__main__":
    run()
