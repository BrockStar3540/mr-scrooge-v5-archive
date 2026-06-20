#!/usr/bin/env python3
"""Build the full per-trade matrix Brock asked for.

For every trade in the existing /tmp/v5_trade_matrix.csv, augment with:
  - session (from entry UTC hour, V5's coarse_session)
  - atr_5m_pips, atr_1h_pips, atr_d_pips (ATR-14 at entry)
  - atr_conc      (atr_5m / (atr_d/96)) — V5's chaos gate
  - atr_h1_relative (atr_1h / atr_d_avg) — the matrix's regime switch
  - wall_frac     (min(PDH_dist, PDL_dist) / atr_5m) — V5 momentum amplifier
  - trend_4h      (sum of last 4 H1 returns, signed in pips)
  - htf_pct_20    (percentile rank of yesterday's return vs last 20 days)
  - htf_pct_60    (vs last 60 days)

Pull OANDA M5/H1/D candles for the window preceding each entry.
"""
import os, json, csv
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta
from statistics import mean

API = os.environ["OANDA_API_URL"]
TOKEN = os.environ["OANDA_API_TOKEN"]

PIP_SIZE = {
    "AUD_USD": 0.0001, "EUR_USD": 0.0001, "GBP_USD": 0.0001, "USD_CAD": 0.0001,
    "USD_JPY": 0.01, "USD_CHF": 0.0001, "AUD_JPY": 0.01, "EUR_JPY": 0.01,
}


def coarse_session(hour_utc):
    if 7 <= hour_utc < 13:  return "london"
    if 13 <= hour_utc < 22: return "ny"
    return "asia"


def fetch(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def atr_pips(candles, n, pip):
    """True-range ATR over the last n complete candles (in pips)."""
    closed = [c for c in candles if c.get("complete")][-n-1:]
    if len(closed) < 2:
        return None
    trs = []
    for i in range(1, len(closed)):
        h = float(closed[i]["mid"]["h"]); l = float(closed[i]["mid"]["l"])
        pc = float(closed[i-1]["mid"]["c"])
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr / pip)
    return mean(trs[-n:]) if trs else None


def pdh_pdl(d_candles, pip):
    """Prior-day H and L from daily candles."""
    closed = [c for c in d_candles if c.get("complete")]
    if len(closed) < 1:
        return None, None
    last = closed[-1]
    return float(last["mid"]["h"]), float(last["mid"]["l"])


def daily_returns_pips(d_candles, pip):
    """Per-bar daily returns (c-o)/pip, signed, last 60 days."""
    closed = [c for c in d_candles if c.get("complete")]
    return [(float(c["mid"]["c"]) - float(c["mid"]["o"])) / pip for c in closed[-60:]]


def htf_pct(d_ret, history, k):
    """Percentile rank of d_ret within the last k history values."""
    window = history[-k:]
    if not window:
        return None
    return sum(1 for h in window if h <= d_ret) / len(window)


def trend_4h_pips(h1_candles, pip):
    """Sum of last 4 complete H1 (c-o) returns in pips."""
    closed = [c for c in h1_candles if c.get("complete")][-4:]
    if not closed:
        return 0.0
    return sum((float(c["mid"]["c"]) - float(c["mid"]["o"])) / pip for c in closed)


def augment_trade(pair, dir_, entry_price, entry_iso):
    """Pull OANDA candles for one trade entry and compute all aggregators."""
    pip = PIP_SIZE[pair]
    entry_dt = datetime.strptime(entry_iso, "%Y-%m-%dT%H:%M:%SZ")

    # M5: last 20 bars before entry → atr_5m
    m5_from = (entry_dt - timedelta(minutes=5 * 25)).strftime("%Y-%m-%dT%H:%M:%SZ")
    m5_to   = entry_iso
    m5 = fetch(f"{API}/v3/instruments/{pair}/candles?granularity=M5&from={m5_from}&to={m5_to}&price=M").get("candles", [])
    atr_5m = atr_pips(m5, 14, pip)

    # H1: last 6 bars before entry → atr_1h + trend_4h
    h1_from = (entry_dt - timedelta(hours=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
    h1_to   = entry_iso
    h1 = fetch(f"{API}/v3/instruments/{pair}/candles?granularity=H1&from={h1_from}&to={h1_to}&price=M").get("candles", [])
    atr_1h = atr_pips(h1, 14, pip)
    tr_4h  = trend_4h_pips(h1, pip)

    # D: last 65 days before entry → atr_d + PDH/PDL + htf_pct
    d_from = (entry_dt - timedelta(days=80)).strftime("%Y-%m-%dT%H:%M:%SZ")
    d_to   = entry_iso
    d = fetch(f"{API}/v3/instruments/{pair}/candles?granularity=D&from={d_from}&to={d_to}&price=M").get("candles", [])
    atr_d = atr_pips(d, 14, pip)
    pdh, pdl = pdh_pdl(d, pip)
    dret_hist = daily_returns_pips(d, pip)

    # Most recent completed daily return
    today_ret = dret_hist[-1] if dret_hist else 0.0
    hist_20 = dret_hist[-21:-1] if len(dret_hist) >= 2 else []
    hist_60 = dret_hist[-61:-1] if len(dret_hist) >= 2 else []
    h20 = htf_pct(today_ret, hist_20, 20)
    h60 = htf_pct(today_ret, hist_60, 60)

    # Derived
    pdh_dist_pips = (entry_price - pdh) / pip if pdh is not None else None  # signed: + above PDH
    pdl_dist_pips = (entry_price - pdl) / pip if pdl is not None else None
    wall_frac = None
    if atr_5m and pdh_dist_pips is not None and pdl_dist_pips is not None:
        nearest_wall = min(abs(pdh_dist_pips), abs(pdl_dist_pips))
        wall_frac = nearest_wall / atr_5m
    atr_conc = None
    if atr_5m and atr_d:
        atr_conc = atr_5m / (atr_d / 96)  # 24h × 60min / 5min = 288, V5 uses 96 for some normalization (~quarter-day)
    atr_h1_rel = None
    if atr_1h and atr_d:
        atr_h1_rel = atr_1h / (atr_d / 24)  # avg-hour ratio

    return {
        "atr_5m":          round(atr_5m, 2) if atr_5m else None,
        "atr_1h":          round(atr_1h, 2) if atr_1h else None,
        "atr_d":           round(atr_d,  2) if atr_d  else None,
        "atr_conc":        round(atr_conc, 3) if atr_conc is not None else None,
        "atr_h1_relative": round(atr_h1_rel, 3) if atr_h1_rel is not None else None,
        "wall_frac":       round(wall_frac, 2) if wall_frac is not None else None,
        "trend_4h_pips":   round(tr_4h, 2),
        "htf_pct_20":      round(h20, 2) if h20 is not None else None,
        "htf_pct_60":      round(h60, 2) if h60 is not None else None,
    }


def main():
    src = Path("/tmp/v5_trade_matrix.csv")
    rows = list(csv.DictReader(src.open()))
    print(f"loading {len(rows)} trades from {src}", flush=True)

    # We also need the entry_iso for each trade. Re-parse journal.
    journal = Path("/tmp/v5_journal_full.log")
    import re
    entry_iso_by_tid = {}
    entry_price_by_tid = {}
    for ln in journal.read_text().splitlines():
        m_dt = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", ln)
        m_en = re.search(r"ENTERED (\S+) (\S+) @ ([\d.]+).*trade_id=(\d+)", ln)
        if m_dt and m_en:
            tid = m_en.group(4)
            entry_iso_by_tid[tid] = m_dt.group(1).replace(" ", "T") + "Z"
            entry_price_by_tid[tid] = float(m_en.group(3))

    enriched = []
    for r in rows:
        tid = r["tid"]
        if tid not in entry_iso_by_tid:
            continue
        entry_iso = entry_iso_by_tid[tid]
        entry_price = entry_price_by_tid[tid]
        hour_utc = int(entry_iso[11:13])
        session = coarse_session(hour_utc)
        try:
            aug = augment_trade(r["pair"], r["dir"], entry_price, entry_iso)
        except Exception as e:
            print(f"  skip {tid}: {e}", flush=True)
            continue
        new = dict(r)
        new["session"] = session
        new.update(aug)
        enriched.append(new)
        print(f"  {tid} {r['pair']:<8} {r['dir']:<5} {session:<6}  atr_conc={aug['atr_conc']}  h1_rel={aug['atr_h1_relative']}  wall={aug['wall_frac']}  trend4h={aug['trend_4h_pips']}  htf20={aug['htf_pct_20']}  htf60={aug['htf_pct_60']}", flush=True)

    # Write the full CSV
    out = Path("/tmp/v5_full_matrix.csv")
    cols = list(enriched[0].keys())
    with out.open("w") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(enriched)
    print(f"\nwrote {out} ({len(enriched)} rows × {len(cols)} cols)")


if __name__ == "__main__":
    main()
