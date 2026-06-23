#!/usr/bin/env python3
"""Pull raw entry-time indicators per trade + cross with MFE/MAE/realized.

Goal: find which entry conditions predict big winners vs failed winners,
so we can tighten per-cell entry gates.

For each of the 14 trades (since 2026-06-22 04:14 UTC):
  - Journal SIGNAL fields: dir_score, d_cert, m_cert, expected, vol_regime,
    profiles, vortex_diff, close_pos, inverted_live flag
  - Recomputed at entry from OANDA M5+H1:
    rsi14_h1, rsi14_m5, atr_5m, atr_1h, bb_pos_m5, h1_ret_1bar, h1_ret_4bar
  - MFE, MAE, realized (from prior script)

Outputs:
  - Per-trade table (CSV + stdout)
  - Group means: BIG_WIN (MFE>=10p), SMALL_WIN, FAILED_WIN (MFE>0 realized<0), LOSS
  - Notable patterns flagged
"""
from __future__ import annotations
import os, re, subprocess, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
import requests
import pandas as pd
import numpy as np

PIP = {
    "USD_JPY": 0.01, "EUR_JPY": 0.01, "AUD_JPY": 0.01, "GBP_JPY": 0.01,
    "EUR_USD": 0.0001, "GBP_USD": 0.0001, "AUD_USD": 0.0001, "USD_CHF": 0.0001,
    "USD_CAD": 0.0001, "NZD_USD": 0.0001,
}
SINCE = "2026-06-22 04:14:00"

env_path = Path.home() / ".openclaw" / "secrets.env"
for line in env_path.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")
TOKEN = os.environ["OANDA_API_TOKEN"]
OANDA_URL = os.environ.get("OANDA_API_URL", "https://api-fxpractice.oanda.com").rstrip("/")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# ── Journal regex ──
ENTERED = re.compile(
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ INFO v5\.engine\s+ENTERED "
    r"(\w+) (long|short) @ ([\d.]+) \| (\d+) units \| SL ([+-]?[\d.]+)p \| trade_id=(\d+)"
)
EXIT = re.compile(
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ INFO v5\.engine\s+EXIT.*?"
    r"(\w+) \| trade_id=(\d+) \| approx_net=([+-]?[\d.]+)p"
)
# SIGNAL line captures (single-pass parse, fields come in order)
SIGNAL = re.compile(
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ INFO v5\.engine\s+SIGNAL "
    r"(\w+) (long|short) \| score=([+-]?[\d.]+) d_cert=([+-]?[\d.]+) "
    r"m_cert=([+-]?[\d.]+) expected=([+-]?[\d.]+)p vol=(\w+) rivals=(\d+) "
    r"\| active_side=(\S+) long_prof=(\S+) short_prof=(\S+) mom_prof=(\S+) "
    r"gates=(\w+) cert_boost=([+-]?[\d.]+) "
    r"\| shadow_vortex_diff=([+-]?[\d.]+) shadow_close_pos=([+-]?[\d.]+)"
    r"(\s*\| INVERTED_LIVE \S+ \S+)?"
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
    entries, exits, signals_by_pair_time = {}, {}, []
    for line in raw.splitlines():
        if m := ENTERED.search(line):
            ts, pair, dr, ep, units, sl, tid = m.groups()
            entries[tid] = {"ts": ts, "pair": pair, "dir": dr,
                            "entry": float(ep), "sl_pips": float(sl)}
        elif m := EXIT.search(line):
            ts, pair, tid, net = m.groups()
            exits[tid] = {"ts": ts, "pair": pair, "net": float(net)}
        elif m := SIGNAL.search(line):
            ts = m.group(1)
            signals_by_pair_time.append({
                "ts": ts, "pair": m.group(2), "trade_dir": m.group(3),
                "dir_score": float(m.group(4)),
                "d_cert":    float(m.group(5)),
                "m_cert":    float(m.group(6)),
                "expected":  float(m.group(7)),
                "vol":       m.group(8),
                "rivals":    int(m.group(9)),
                "active_side": m.group(10),
                "long_prof":  m.group(11),
                "short_prof": m.group(12),
                "mom_prof":   m.group(13),
                "gates":      m.group(14) == "True",
                "cert_boost": float(m.group(15)),
                "vortex_diff": float(m.group(16)),
                "close_pos":  float(m.group(17)),
                "inverted_live": m.group(18) is not None,
            })
    # Match each trade to its SIGNAL by pair + nearest preceding ts within 10s
    for tid, e in entries.items():
        e_dt = datetime.strptime(e["ts"], "%Y-%m-%d %H:%M:%S")
        best = None
        for s in signals_by_pair_time:
            if s["pair"] != e["pair"]:
                continue
            s_dt = datetime.strptime(s["ts"], "%Y-%m-%d %H:%M:%S")
            if (e_dt - s_dt).total_seconds() < 0 or (e_dt - s_dt).total_seconds() > 10:
                continue
            if best is None or s_dt > datetime.strptime(best["ts"], "%Y-%m-%d %H:%M:%S"):
                best = s
        if best:
            e["sig"] = best
    return entries, exits


# ── Indicators ──
def rsi(s: pd.Series, period: int = 14) -> pd.Series:
    delta = s.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - 100 / (1 + rs)


def atr(h: pd.Series, l: pd.Series, c: pd.Series, period: int = 14) -> pd.Series:
    prev_c = c.shift()
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def bb_pos(c: pd.Series, period: int = 20, mult: float = 2.0) -> pd.Series:
    ma = c.rolling(period).mean()
    sd = c.rolling(period).std()
    upper = ma + mult * sd
    lower = ma - mult * sd
    rng = (upper - lower).replace(0, np.nan)
    return (c - lower) / rng


def fetch_candles(pair: str, ts_from: str, ts_to: str, granularity: str):
    url = f"{OANDA_URL}/v3/instruments/{pair}/candles"
    params = {"from": ts_from, "to": ts_to,
              "granularity": granularity, "price": "M"}
    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("candles", [])


def candles_df(rows):
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame([
        {"time": c["time"],
         "open": float(c["mid"]["o"]), "high": float(c["mid"]["h"]),
         "low": float(c["mid"]["l"]), "close": float(c["mid"]["c"]),
         "volume": int(c["volume"])}
        for c in rows if "mid" in c
    ])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.set_index("time").sort_index()


def compute_at_entry(pair: str, entry_ts: str) -> dict:
    """Compute indicators at the M5 bar that contains the entry time."""
    pip = PIP[pair]
    # Pull 4h of M5 (48 bars) + 6h of H1 (6 bars) preceding entry
    e_dt = datetime.strptime(entry_ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    m5 = candles_df(fetch_candles(pair,
                                  (e_dt - timedelta(hours=8)).isoformat().replace("+00:00", "Z"),
                                  (e_dt + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
                                  "M5"))
    h1 = candles_df(fetch_candles(pair,
                                  (e_dt - timedelta(hours=24)).isoformat().replace("+00:00", "Z"),
                                  (e_dt + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
                                  "H1"))
    if m5.empty or h1.empty:
        return {}
    # M5 indicators at the bar at-or-before entry
    m5_at = m5[m5.index <= e_dt]
    h1_at = h1[h1.index <= e_dt]
    if len(m5_at) < 20 or len(h1_at) < 14:
        return {}
    rsi14_m5 = rsi(m5_at["close"], 14).iloc[-1]
    atr14_m5_p = atr(m5_at["high"], m5_at["low"], m5_at["close"], 14).iloc[-1] / pip
    bb_pos_m5 = bb_pos(m5_at["close"], 20, 2.0).iloc[-1]
    rsi14_h1 = rsi(h1_at["close"], 14).iloc[-1]
    atr14_h1_p = atr(h1_at["high"], h1_at["low"], h1_at["close"], 14).iloc[-1] / pip
    # H1 returns
    h1_close = h1_at["close"]
    h1_ret_1bar_p = ((h1_close.iloc[-1] - h1_close.iloc[-2]) / pip) if len(h1_close) >= 2 else np.nan
    h1_ret_4bar_p = ((h1_close.iloc[-1] - h1_close.iloc[-5]) / pip) if len(h1_close) >= 5 else np.nan
    return {
        "rsi14_m5": round(rsi14_m5, 1),
        "rsi14_h1": round(rsi14_h1, 1),
        "atr_5m_p": round(atr14_m5_p, 2),
        "atr_1h_p": round(atr14_h1_p, 2),
        "bb_pos_m5": round(bb_pos_m5, 3),
        "h1_ret_1bar_p": round(h1_ret_1bar_p, 2),
        "h1_ret_4bar_p": round(h1_ret_4bar_p, 2),
    }


def compute_mfe_mae(pair: str, direction: str, entry: float,
                    entry_ts: str, exit_ts: str) -> tuple[float, float]:
    pip = PIP[pair]
    e_dt = datetime.strptime(entry_ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    x_dt = datetime.strptime(exit_ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    candles = fetch_candles(pair,
                            e_dt.isoformat().replace("+00:00", "Z"),
                            (x_dt + timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
                            "M1")
    if not candles:
        return 0.0, 0.0
    highs = [float(c["mid"]["h"]) for c in candles if "mid" in c]
    lows  = [float(c["mid"]["l"]) for c in candles if "mid" in c]
    if direction == "long":
        return round((max(highs) - entry) / pip, 2), round((min(lows) - entry) / pip, 2)
    return round((entry - min(lows)) / pip, 2), round((entry - max(highs)) / pip, 2)


def run():
    entries, exits = parse_journal()
    closed = sorted([tid for tid in entries if tid in exits],
                    key=lambda t: entries[t]["ts"])

    rows = []
    for tid in closed:
        e, x = entries[tid], exits[tid]
        mfe, mae = compute_mfe_mae(e["pair"], e["dir"], e["entry"], e["ts"], x["ts"])
        ind = compute_at_entry(e["pair"], e["ts"])
        sig = e.get("sig", {})

        row = {
            "tid": tid, "pair": e["pair"], "dir": e["dir"],
            "session": _session_of(e["ts"]),
            "inverted": sig.get("inverted_live", False),
            "realized": x["net"], "mfe": mfe, "mae": mae,
            "dir_score": sig.get("dir_score"),
            "d_cert":    sig.get("d_cert"),
            "m_cert":    sig.get("m_cert"),
            "expected":  sig.get("expected"),
            "vol":       sig.get("vol"),
            "cert_boost": sig.get("cert_boost"),
            "vortex_diff": sig.get("vortex_diff"),
            "close_pos":  sig.get("close_pos"),
            "long_prof":  sig.get("long_prof"),
            "short_prof": sig.get("short_prof"),
            "mom_prof":   sig.get("mom_prof"),
            **ind,
        }
        # Outcome class
        if mfe >= 10:
            row["class"] = "BIG_WIN" if x["net"] > 0 else "BIG_FAIL"
        elif x["net"] > 2:
            row["class"] = "SMALL_WIN"
        elif x["net"] > 0:
            row["class"] = "MARGINAL"
        elif mfe > 2:
            row["class"] = "FAILED_WIN"
        else:
            row["class"] = "LOSS"
        rows.append(row)

    df = pd.DataFrame(rows)
    out_csv = Path(__file__).resolve().parent.parent / "data" / "entry_indicators_vs_mfe.csv"
    out_csv.parent.mkdir(exist_ok=True)
    df.to_csv(out_csv, index=False)

    # === Print 1: per-trade table ===
    print(f"=== Entry indicators × MFE per trade (n={len(df)}) ===\n")
    cols_short = ["tid","pair","dir","session","inverted","class",
                  "realized","mfe","mae",
                  "dir_score","d_cert","m_cert","expected",
                  "vortex_diff","close_pos",
                  "rsi14_h1","rsi14_m5","bb_pos_m5",
                  "h1_ret_1bar_p","h1_ret_4bar_p","atr_5m_p","atr_1h_p",
                  "mom_prof"]
    with pd.option_context("display.max_columns", None,
                           "display.width", 220,
                           "display.float_format", "{:+.2f}".format):
        print(df[cols_short].to_string(index=False))

    # === Print 2: group means ===
    print(f"\n=== Mean indicators by outcome class ===\n")
    num_cols = ["realized","mfe","mae","dir_score","d_cert","m_cert","expected",
                "vortex_diff","close_pos","rsi14_h1","rsi14_m5","bb_pos_m5",
                "h1_ret_1bar_p","h1_ret_4bar_p","atr_5m_p","atr_1h_p"]
    grp = df.groupby("class")[num_cols].mean().round(2)
    print(grp.to_string())

    # === Print 3: counts ===
    print(f"\n=== Class counts ===")
    print(df["class"].value_counts().to_string())
    print(f"\n→ {out_csv}")


def _session_of(ts: str) -> str:
    h = int(ts.split(" ")[1].split(":")[0])
    if 22 <= h or h < 5:  return "asia"
    if 5 <= h < 13:       return "london"
    return "ny"


if __name__ == "__main__":
    run()
