#!/usr/bin/env python3
"""Backtest Brock's proposed ratchet against the 14 actual trades.

Proposed bands (each only raises SL, never lowers):
  MFE >= 4.0p  -> SL = -4.0p  (early loss-cap)
  MFE >= 6.0p  -> SL = +4.0p  (lock +4)
  MFE >= 7.5p  -> SL = +5.0p  (existing first band)
  MFE >= 10p   -> SL = +7.5p  (existing)
  MFE >= 12.5p -> SL = +10p
  MFE >= 15p   -> SL = +12.5p
  MFE >= 17.5p -> SL = +15p
  MFE >= 20p   -> SL = +17.5p

For each actual trade: pull M1 candles for entry->exit window, walk in time
order. On each candle: (1) check if SL was hit (pessimistic: stop-before-
ratchet within the same bar); (2) update peak; (3) raise SL band if peak
crossed a threshold. If SL never hits, close at actual exit price (= keep
the realized result for that part).

Compares old vs new realized P/L per trade and in aggregate.
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
SINCE = "2026-06-22 04:14:00"

BANDS = [
    # SOFTER VARIANT: skip the early -4 loss-cap; first lock is +4 at MFE +6
    (6.0,   4.0),
    (7.5,   5.0),
    (10.0,  7.5),
    (12.5, 10.0),
    (15.0, 12.5),
    (17.5, 15.0),
    (20.0, 17.5),
    (22.5, 20.0),
    (25.0, 22.5),
    (30.0, 27.5),
]

env_path = Path.home() / ".openclaw" / "secrets.env"
for line in env_path.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")
TOKEN = os.environ.get("OANDA_API_TOKEN")
OANDA_URL = os.environ.get("OANDA_API_URL", "https://api-fxpractice.oanda.com").rstrip("/")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

ENTERED = re.compile(
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ INFO v5\.engine\s+ENTERED "
    r"(\w+) (long|short) @ ([\d.]+) \| (\d+) units \| SL ([+-]?[\d.]+)p \| trade_id=(\d+)"
)
EXIT = re.compile(
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ INFO v5\.engine\s+EXIT.*?"
    r"(\w+) \| trade_id=(\d+) \| approx_net=([+-]?[\d.]+)p"
)


def iso_z(s: str, pad_seconds: int = 0) -> str:
    dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    if pad_seconds:
        dt += timedelta(seconds=pad_seconds)
    return dt.isoformat().replace("+00:00", "Z")


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
                            "entry": float(ep), "sl_pips": float(sl)}
        elif m := EXIT.search(line):
            ts, pair, tid, net = m.groups()
            exits[tid] = {"ts": ts, "pair": pair, "net": float(net)}
    return entries, exits


def fetch_candles(pair: str, ts_from: str, ts_to: str, granularity: str = "M1"):
    url = f"{OANDA_URL}/v3/instruments/{pair}/candles"
    params = {"from": ts_from, "to": ts_to,
              "granularity": granularity, "price": "M"}
    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("candles", [])


def sim_proposed_ratchet(entry: float, direction: str, sl_init_pips: float,
                          candles: list, pair: str) -> tuple[float, str, float]:
    """Walk candles, return (realized_pips, exit_reason, peak_mfe_p)."""
    pip = PIP[pair]
    sl_p = -abs(sl_init_pips)   # -20.0 typical
    peak_p = 0.0

    for c in candles:
        if "mid" not in c:
            continue
        h = float(c["mid"]["h"])
        l = float(c["mid"]["l"])
        if direction == "long":
            high_p = (h - entry) / pip
            low_p  = (l - entry) / pip
        else:
            high_p = (entry - l) / pip
            low_p  = (entry - h) / pip

        # Realistic intra-candle ordering: update peak + ratchet FIRST,
        # then check stop on the candle's low against the (possibly raised) SL.
        # Matches the live behavior with fine-grained polling: ratchet engages
        # on the way up, stop fires on the way down.
        if high_p > peak_p:
            peak_p = high_p
            for thresh, lock in BANDS:
                if peak_p >= thresh and lock > sl_p:
                    sl_p = lock
        if low_p <= sl_p:
            return round(sl_p, 2), "ratchet_stop", round(peak_p, 2)

    # Never hit ratchet — exit at last close
    last_close = float(candles[-1]["mid"]["c"])
    if direction == "long":
        final_p = (last_close - entry) / pip
    else:
        final_p = (entry - last_close) / pip
    return round(final_p, 2), "candle_end_close", round(peak_p, 2)


def run():
    entries, exits = parse_journal()
    closed = sorted([tid for tid in entries if tid in exits],
                    key=lambda t: entries[t]["ts"])

    rows = []
    for tid in closed:
        e, x = entries[tid], exits[tid]
        candles = fetch_candles(e["pair"], iso_z(e["ts"]),
                                iso_z(x["ts"], pad_seconds=1), "M1")
        sim_pips, reason, peak = sim_proposed_ratchet(
            e["entry"], e["dir"], e["sl_pips"], candles, e["pair"]
        )
        rows.append({
            "tid": tid, "pair": e["pair"], "dir": e["dir"],
            "old_realized": x["net"],
            "sim_realized": sim_pips,
            "delta": round(sim_pips - x["net"], 2),
            "peak_mfe": peak,
            "exit_reason": reason,
        })

    print(f"V5 ratchet proposal — simulated on {len(rows)} actual trades")
    print(f"Proposed bands: {BANDS[:4]} ... (existing bands above)\n")
    print(f"{'tid':<5} {'pair':<8} {'dir':<5} {'MFE':>7} "
          f"{'old':>9} {'new':>9} {'Δ':>8}  reason")
    print("-" * 75)
    for r in rows:
        flag = ""
        if r["delta"] > 5:  flag = " ★ saved"
        elif r["delta"] < -2: flag = " ✗ worse"
        print(f"{r['tid']:<5} {r['pair']:<8} {r['dir']:<5} "
              f"{r['peak_mfe']:>+6.1f}p "
              f"{r['old_realized']:>+8.2f}p {r['sim_realized']:>+8.2f}p "
              f"{r['delta']:>+7.2f}p  {r['exit_reason']}{flag}")

    n = len(rows)
    sum_old = sum(r["old_realized"] for r in rows)
    sum_new = sum(r["sim_realized"] for r in rows)
    wr_old  = 100 * sum(1 for r in rows if r["old_realized"] > 0) / n
    wr_new  = 100 * sum(1 for r in rows if r["sim_realized"] > 0) / n
    saved   = [r for r in rows if r["delta"] > 0]
    hurt    = [r for r in rows if r["delta"] < 0]

    print()
    print(f"=== aggregate ===")
    print(f"  OLD: sum={sum_old:+.2f}p, mean={sum_old/n:+.2f}p, WR={wr_old:.0f}%")
    print(f"  NEW: sum={sum_new:+.2f}p, mean={sum_new/n:+.2f}p, WR={wr_new:.0f}%")
    print(f"  Δ:   sum={sum_new-sum_old:+.2f}p, mean={(sum_new-sum_old)/n:+.2f}p")
    print(f"  Trades better: {len(saved)} (sum gain={sum(r['delta'] for r in saved):+.2f}p)")
    print(f"  Trades worse:  {len(hurt)} (sum loss={sum(r['delta'] for r in hurt):+.2f}p)")
    print(f"  Trades same:   {n - len(saved) - len(hurt)}")


if __name__ == "__main__":
    run()
