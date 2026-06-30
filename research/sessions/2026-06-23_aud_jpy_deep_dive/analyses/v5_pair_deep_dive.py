#!/usr/bin/env python3
"""Per-pair deep-dive — per-trade everything we know + the 4 new matrix
indicators recomputed from OANDA at entry time.

Usage:
  python3 v5_pair_deep_dive.py PAIR [--since YYYY-MM-DD HH:MM:SS]

Default since: 2026-06-22 04:14:00 (inverted_live wiring landed)
"""
from __future__ import annotations
import argparse, os, re, subprocess, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests
import pandas as pd

PIP = {"USD_JPY":0.01,"EUR_JPY":0.01,"AUD_JPY":0.01,"GBP_JPY":0.01,
       "EUR_USD":0.0001,"GBP_USD":0.0001,"AUD_USD":0.0001,"USD_CHF":0.0001,
       "USD_CAD":0.0001}

env = Path.home() / ".openclaw" / "secrets.env"
for line in env.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")
TOKEN = os.environ["OANDA_API_TOKEN"]
OANDA_URL = os.environ.get("OANDA_API_URL", "https://api-fxpractice.oanda.com").rstrip("/")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def coarse_session(h):
    if 7 <= h < 13: return "london"
    if 13 <= h < 22: return "ny"
    return "asia"


def iso_z(dt): return dt.isoformat().replace("+00:00", "Z")


def fetch(pair, granularity, ts_from, ts_to):
    url = f"{OANDA_URL}/v3/instruments/{pair}/candles"
    r = requests.get(url, headers=HEADERS,
                     params={"from": ts_from, "to": ts_to, "granularity": granularity, "price": "M"},
                     timeout=30)
    r.raise_for_status()
    return r.json().get("candles", [])


def df_from(candles):
    if not candles: return pd.DataFrame()
    df = pd.DataFrame([{
        "time": c["time"], "open": float(c["mid"]["o"]), "high": float(c["mid"]["h"]),
        "low": float(c["mid"]["l"]), "close": float(c["mid"]["c"]), "volume": int(c["volume"])
    } for c in candles if "mid" in c])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.set_index("time").sort_index()


def willr(df, period=14):
    if df is None or len(df) < period + 1: return 0.0
    seg = df.iloc[-period:]
    hh, ll, c = float(seg["high"].max()), float(seg["low"].min()), float(df["close"].iloc[-1])
    if hh == ll: return -50.0
    return -100.0 * (hh - c) / (hh - ll)

def aroon_osc(df, period=14):
    if df is None or len(df) < period + 1: return 0.0
    seg = df.iloc[-(period + 1):]
    h = seg["high"].astype(float).reset_index(drop=True)
    l = seg["low"].astype(float).reset_index(drop=True)
    return 100.0 * (int(h.idxmax()) - int(l.idxmin())) / period

def kc_up_dist(df, pip, period=20, mult=2.0):
    if df is None or len(df) < period + 1: return 0.0
    c, h, l = df["close"].astype(float), df["high"].astype(float), df["low"].astype(float)
    pc = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1.0 / period, adjust=False).mean()
    ema = c.ewm(span=period, adjust=False).mean()
    upper = ema + mult * atr
    return float((c.iloc[-1] - upper.iloc[-1]) / pip)

def efi(df, period=13):
    if df is None or len(df) < period + 2: return 0.0
    c, v = df["close"].astype(float), df["volume"].astype(float)
    return float(((c - c.shift(1)) * v).ewm(span=period, adjust=False).mean().iloc[-1])

def rsi14_h1(df, period=14):
    if df is None or len(df) < period + 1: return 0.0
    d = df["close"].astype(float).diff()
    g = d.clip(lower=0).ewm(alpha=1.0 / period, adjust=False).mean()
    l = (-d.clip(upper=0)).ewm(alpha=1.0 / period, adjust=False).mean()
    rs = g / l
    return float((100 - 100 / (1 + rs)).iloc[-1])


def parse_journal(pair, since):
    ENTERED = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ INFO v5\.engine\s+ENTERED " +
        pair + r" (long|short) @ ([\d.]+) \| \d+ units \| SL [+-]?[\d.]+p \| trade_id=(\d+)"
    )
    EXIT = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ INFO v5\.engine\s+EXIT.*?" +
        pair + r" \| trade_id=(\d+) \| approx_net=([+-]?[\d.]+)p"
    )
    SIGNAL = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ INFO v5\.engine\s+SIGNAL " +
        pair + r" (long|short) \| score=([+-]?[\d.]+) d_cert=([+-]?[\d.]+) "
        r"m_cert=([+-]?[\d.]+) expected=([+-]?[\d.]+)p vol=(\w+) rivals=\d+ "
        r"\| active_side=(\S+) long_prof=(\S+) short_prof=(\S+) mom_prof=(\S+) "
        r"gates=\w+ cert_boost=[+-]?[\d.]+ "
        r"\| shadow_vortex_diff=([+-]?[\d.]+) shadow_close_pos=([+-]?[\d.]+)"
        r"(\s*\| INVERTED_LIVE \S+ \S+)?"
    )
    raw = subprocess.check_output(
        ["journalctl", "--user", "-u", "mr-scrooge-v5", "--since", since, "--no-pager", "-o", "cat"],
        text=True,
    )
    ents, exts, sigs = {}, {}, []
    for line in raw.splitlines():
        if m := ENTERED.search(line):
            ts, dr, ep, tid = m.groups()
            ents[tid] = {"ts": ts, "dir": dr, "entry": float(ep)}
        elif m := EXIT.search(line):
            ts, tid, net = m.groups()
            exts[tid] = {"ts": ts, "net": float(net)}
        elif m := SIGNAL.search(line):
            sigs.append({
                "ts": m.group(1), "dir": m.group(2),
                "dir_score": float(m.group(3)), "d_cert": float(m.group(4)),
                "m_cert": float(m.group(5)), "expected": float(m.group(6)),
                "vol": m.group(7), "active_side": m.group(8),
                "long_prof": m.group(9), "short_prof": m.group(10),
                "mom_prof": m.group(11),
                "vortex_diff": float(m.group(12)), "close_pos": float(m.group(13)),
                "inverted_live": m.group(14) is not None,
            })
    for tid, e in ents.items():
        edt = datetime.strptime(e["ts"], "%Y-%m-%d %H:%M:%S")
        best = None
        for s in sigs:
            sdt = datetime.strptime(s["ts"], "%Y-%m-%d %H:%M:%S")
            dt = (edt - sdt).total_seconds()
            if 0 <= dt <= 10:
                if best is None or sdt > datetime.strptime(best["ts"], "%Y-%m-%d %H:%M:%S"):
                    best = s
        e["sig"] = best
    return ents, exts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pair", help="e.g. USD_JPY")
    ap.add_argument("--since", default="2026-06-22 04:14:00")
    args = ap.parse_args()
    pair = args.pair
    pip = PIP[pair]

    ents, exts = parse_journal(pair, args.since)
    tids = sorted(ents.keys(), key=lambda t: ents[t]["ts"])
    print(f"{pair} deep-dive — {len(tids)} trades since {args.since}\n")

    rows = []
    for tid in tids:
        e = ents[tid]
        x = exts.get(tid)
        sig = e.get("sig", {})
        edt = datetime.strptime(e["ts"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        session = coarse_session(edt.hour)

        m5_from = iso_z(edt - timedelta(hours=8)); m5_to = iso_z(edt + timedelta(minutes=5))
        h1_from = iso_z(edt - timedelta(days=5)); h1_to = iso_z(edt + timedelta(minutes=5))
        m5 = df_from(fetch(pair, "M5", m5_from, m5_to))
        h1 = df_from(fetch(pair, "H1", h1_from, h1_to))
        m5_at = m5[m5.index <= edt] if not m5.empty else m5
        h1_at = h1[h1.index <= edt] if not h1.empty else h1
        ind = {
            "willr": willr(m5_at) if len(m5_at) >= 15 else None,
            "aroon": aroon_osc(h1_at) if len(h1_at) >= 15 else None,
            "kc_up": kc_up_dist(m5_at, pip) if len(m5_at) >= 21 else None,
            "efi":   efi(m5_at) if len(m5_at) >= 15 else None,
            "rsi_h1": rsi14_h1(h1_at) if len(h1_at) >= 15 else None,
        }

        if x:
            xdt = datetime.strptime(x["ts"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            mfe = mae = hold_min = None
            try:
                m1 = fetch(pair, "M1", iso_z(edt), iso_z(xdt + timedelta(seconds=1)))
                if m1:
                    highs = [float(c["mid"]["h"]) for c in m1 if "mid" in c]
                    lows  = [float(c["mid"]["l"]) for c in m1 if "mid" in c]
                    if e["dir"] == "long":
                        mfe = (max(highs) - e["entry"]) / pip
                        mae = (min(lows)  - e["entry"]) / pip
                    else:
                        mfe = (e["entry"] - min(lows))  / pip
                        mae = (e["entry"] - max(highs)) / pip
                    hold_min = (xdt - edt).total_seconds() / 60.0
            except Exception:
                pass
            realized = x["net"]; status = "closed"
        else:
            now = datetime.now(timezone.utc)
            try:
                m1 = fetch(pair, "M1", iso_z(edt), iso_z(now))
                highs = [float(c["mid"]["h"]) for c in m1 if "mid" in c]
                lows  = [float(c["mid"]["l"]) for c in m1 if "mid" in c]
                if e["dir"] == "long":
                    mfe = (max(highs) - e["entry"]) / pip
                    mae = (min(lows)  - e["entry"]) / pip
                else:
                    mfe = (e["entry"] - min(lows))  / pip
                    mae = (e["entry"] - max(highs)) / pip
                hold_min = (now - edt).total_seconds() / 60.0
            except Exception:
                mfe = mae = hold_min = None
            realized = None; status = "OPEN"

        sig = sig or {}
        rows.append({
            "tid": tid, "ts": e["ts"], "session": session,
            "trade_dir": e["dir"], "inverted": sig.get("inverted_live", False),
            "signal_dir_real": ("long" if e["dir"]=="short" else "short") if sig.get("inverted_live") else e["dir"],
            "entry": e["entry"],
            "dir_score": sig.get("dir_score"), "d_cert": sig.get("d_cert"),
            "m_cert": sig.get("m_cert"), "expected": sig.get("expected"),
            "vol": sig.get("vol"),
            "active_side": sig.get("active_side",""),
            "long_prof": sig.get("long_prof","?"), "short_prof": sig.get("short_prof","?"),
            "mom_prof": sig.get("mom_prof","?"),
            "vortex_diff": sig.get("vortex_diff"), "close_pos": sig.get("close_pos"),
            **ind,
            "mfe": mfe, "mae": mae, "hold_m": hold_min,
            "realized": realized, "status": status,
        })

    if not rows:
        print(f"No {pair} trades found.")
        return

    print(f"{'tid':<5} {'session':<6} {'trade':<5} {'inv':<3} {'sig→':<5} "
          f"{'entry':>9} {'score':>6} {'d_c':>5} {'m_c':>5} {'expct':>6} "
          f"{'vortex':>7} {'cpos':>5} "
          f"{'willr':>6} {'aroon':>6} {'kc_up':>7} {'efi':>8} {'rsi_h1':>6} "
          f"{'MFE':>6} {'MAE':>7} {'hold':>5} {'real':>8}")
    print('-' * 200)
    for r in rows:
        def f(v, w, p=2):
            if v is None: return f"{'':<{w}}"
            if isinstance(v, float): return f"{v:>{w}.{p}f}"
            return f"{v:>{w}}"
        print(
            f"{r['tid']:<5} {r['session']:<6} {r['trade_dir']:<5} "
            f"{'Y' if r['inverted'] else 'N':<3} {r['signal_dir_real']:<5} "
            f"{r['entry']:>9.3f} {f(r['dir_score'],6,3)} {f(r['d_cert'],5,2)} {f(r['m_cert'],5,2)} {f(r['expected'],6,1)} "
            f"{f(r['vortex_diff'],7,3)} {f(r['close_pos'],5,2)} "
            f"{f(r['willr'],6,1)} {f(r['aroon'],6,1)} {f(r['kc_up'],7,2)} {f(r['efi'],8,3)} {f(r['rsi_h1'],6,1)} "
            f"{f(r['mfe'],6,1)} {f(r['mae'],7,1)} {f(r['hold_m'],5,0)} "
            f"{f(r['realized'],8,2) if r['realized'] is not None else '   OPEN':>8}"
        )

    print(f"\n=== Profile summary per trade ===")
    for r in rows:
        print(f"  {r['tid']} {r['session']}/{r['trade_dir']:<5}  "
              f"active={r['active_side']:<14} long_prof={r['long_prof']:<22} short_prof={r['short_prof']:<22} mom_prof={r['mom_prof']}")


if __name__ == "__main__":
    main()
