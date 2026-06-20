#!/usr/bin/env python3
"""Pull OANDA M1 candles for each post-retune loser to compute peak MFE."""
import os, json, urllib.request
from datetime import datetime

API = os.environ["OANDA_API_URL"]
TOKEN = os.environ["OANDA_API_TOKEN"]

LOSERS = [
    # (trade_id, pair, dir, entry_price, entry_utc, exit_utc)
    ("9029", "AUD_USD", "short", 0.69905, "2026-06-19T05:17:26Z", "2026-06-19T06:22:16Z"),
    ("9032", "USD_JPY", "long",  161.444, "2026-06-19T05:22:29Z", "2026-06-19T07:05:17Z"),
    ("9040", "AUD_JPY", "long",  113.193, "2026-06-19T08:19:36Z", "2026-06-19T14:55:31Z"),
    ("9052", "GBP_USD", "long",  1.32398, "2026-06-19T09:40:55Z", "2026-06-19T13:34:27Z"),
]

PIP_SIZE = {"AUD_USD": 0.0001, "USD_JPY": 0.01, "AUD_JPY": 0.01, "GBP_USD": 0.0001}


def fetch_m1(pair, from_iso, to_iso):
    url = (f"{API}/v3/instruments/{pair}/candles?"
           f"granularity=M1&from={from_iso}&to={to_iso}&price=M")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    return json.loads(urllib.request.urlopen(req).read())["candles"]


print(f"{'tid':<6}{'pair':<10}{'dir':<7}{'entry':<10}{'exit':<10}{'peak_pips':<11}{'OLD?(+4.5)':<13}{'NEW?(+7.5)':<13}")
print("-" * 90)

for tid, pair, dir_, entry_price, entry_utc, exit_utc in LOSERS:
    candles = fetch_m1(pair, entry_utc, exit_utc)
    pip = PIP_SIZE[pair]
    peak_pips = 0.0
    for c in candles:
        if not c.get("complete"):
            continue
        hi = float(c["mid"]["h"])
        lo = float(c["mid"]["l"])
        if dir_ == "long":
            move = (hi - entry_price) / pip
        else:
            move = (entry_price - lo) / pip
        if move > peak_pips:
            peak_pips = move
    old_armed = "YES" if peak_pips >= 4.5 else "no"
    new_armed = "YES" if peak_pips >= 7.5 else "no"
    print(f"{tid:<6}{pair:<10}{dir_:<7}{entry_utc[11:16]:<10}{exit_utc[11:16]:<10}+{peak_pips:>4.1f}p     {old_armed:<13}{new_armed:<13}")
