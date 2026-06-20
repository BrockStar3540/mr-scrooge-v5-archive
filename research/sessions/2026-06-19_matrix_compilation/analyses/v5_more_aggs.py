#!/usr/bin/env python3
"""Augment the 44-trade matrix with MORE aggregators Brock wants to test:

Volume / liquidity:
  - rvol_5bar    : last M5 vol / mean(last 20 M5 vols)
  - rvol_12bar   : last M5 vol / mean(last 50 M5 vols)
  - m5_volume    : raw last M5 tick count (already had)

Mean-reversion / overbought:
  - rsi14_m5     : RSI-14 on M5 closes
  - rsi14_h1     : RSI-14 on H1 closes
  - bb_pos_h1    : (close - bb_mid) / bb_width on 20-bar H1 (-1..+1)
  - close_pos_daily : (entry - PDL) / (PDH - PDL)
  - ema20_dist_pct_h1 : (entry - ema20_h1) / entry × 100
  - ema50_dist_pct_h1 : (entry - ema50_h1) / entry × 100

Trend / momentum (signed, aligned to trade direction):
  - ret_5m_aligned, ret_15m_aligned, ret_30m_aligned  : short-term return
  - adx14_h1     : trend strength (magnitude only)

Range:
  - adr_consumed : (today's range so far) / atr_d

Compute per trade, write to v5_full_matrix_v2.csv.
"""
import os, json, csv, urllib.request
from pathlib import Path
from datetime import datetime, timedelta
from statistics import mean, stdev

API = os.environ["OANDA_API_URL"]
TOKEN = os.environ["OANDA_API_TOKEN"]

PIP_SIZE = {
    "AUD_USD": 0.0001, "EUR_USD": 0.0001, "GBP_USD": 0.0001, "USD_CAD": 0.0001,
    "USD_JPY": 0.01, "USD_CHF": 0.0001, "AUD_JPY": 0.01, "EUR_JPY": 0.01,
}


def fetch(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def closed(candles):
    return [c for c in candles if c.get("complete")]


def closes(candles):
    return [float(c["mid"]["c"]) for c in candles]


def rsi(closes_, n=14):
    if len(closes_) < n + 1:
        return None
    deltas = [closes_[i] - closes_[i-1] for i in range(1, len(closes_))]
    gains = [max(d, 0) for d in deltas]
    losses = [-min(d, 0) for d in deltas]
    avg_gain = mean(gains[-n:])
    avg_loss = mean(losses[-n:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def ema(values, n):
    if not values:
        return None
    k = 2 / (n + 1)
    out = values[0]
    for v in values[1:]:
        out = v * k + out * (1 - k)
    return out


def bb_pos(closes_, n=20):
    if len(closes_) < n:
        return None
    window = closes_[-n:]
    mid = mean(window)
    sd = stdev(window)
    if sd == 0:
        return 0.0
    return (closes_[-1] - mid) / (2 * sd)


def adx(candles, n=14):
    closed_ = closed(candles)
    if len(closed_) < n + 2:
        return None
    plus_dm, minus_dm, trs = [], [], []
    for i in range(1, len(closed_)):
        h, l = float(closed_[i]["mid"]["h"]), float(closed_[i]["mid"]["l"])
        ph, pl = float(closed_[i-1]["mid"]["h"]), float(closed_[i-1]["mid"]["l"])
        pc = float(closed_[i-1]["mid"]["c"])
        up_move = h - ph
        down_move = pl - l
        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0)
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    atr_ = mean(trs[-n:])
    pdi = 100 * mean(plus_dm[-n:]) / atr_ if atr_ > 0 else 0
    ndi = 100 * mean(minus_dm[-n:]) / atr_ if atr_ > 0 else 0
    if pdi + ndi == 0:
        return 0
    dx = 100 * abs(pdi - ndi) / (pdi + ndi)
    return dx


def aligned_ret(o, c, dir_, pip):
    r = (c - o) / pip
    return r if dir_ == "long" else -r


def augment_trade(pair, dir_, entry_price, entry_iso):
    pip = PIP_SIZE[pair]
    entry_dt = datetime.strptime(entry_iso, "%Y-%m-%dT%H:%M:%SZ")

    # M5: pull 60 bars before entry
    m5_from = (entry_dt - timedelta(minutes=5 * 65)).strftime("%Y-%m-%dT%H:%M:%SZ")
    m5_to = entry_iso
    m5 = fetch(f"{API}/v3/instruments/{pair}/candles?granularity=M5&from={m5_from}&to={m5_to}&price=M").get("candles", [])
    m5_closed = closed(m5)

    # H1: pull 30 bars before entry
    h1_from = (entry_dt - timedelta(hours=35)).strftime("%Y-%m-%dT%H:%M:%SZ")
    h1_to = entry_iso
    h1 = fetch(f"{API}/v3/instruments/{pair}/candles?granularity=H1&from={h1_from}&to={h1_to}&price=M").get("candles", [])
    h1_closed = closed(h1)

    # D: pull 30 days for current-day range + ADR
    d_from = (entry_dt - timedelta(days=35)).strftime("%Y-%m-%dT%H:%M:%SZ")
    d = fetch(f"{API}/v3/instruments/{pair}/candles?granularity=D&from={d_from}&to={entry_iso}&price=M").get("candles", [])
    d_closed = closed(d)

    # rvol — M5 volume ratios
    m5_vols = [int(c["volume"]) for c in m5_closed]
    last_v = m5_vols[-1] if m5_vols else 0
    rvol_5bar = last_v / mean(m5_vols[-20:]) if len(m5_vols) >= 20 and mean(m5_vols[-20:]) > 0 else None
    rvol_12bar = last_v / mean(m5_vols[-50:]) if len(m5_vols) >= 50 and mean(m5_vols[-50:]) > 0 else None

    # RSI
    m5_c = closes(m5_closed)
    h1_c = closes(h1_closed)
    rsi_m5 = rsi(m5_c, 14)
    rsi_h1 = rsi(h1_c, 14)

    # BB position (h1 20-bar)
    bbp_h1 = bb_pos(h1_c, 20)

    # EMA distance pct (h1 20 + 50)
    ema20_h1 = ema(h1_c, 20) if len(h1_c) >= 20 else None
    ema50_h1 = ema(h1_c, 50) if len(h1_c) >= 50 else None
    ema20_dist = ((entry_price - ema20_h1) / entry_price * 100) if ema20_h1 else None
    ema50_dist = ((entry_price - ema50_h1) / entry_price * 100) if ema50_h1 else None

    # Aligned shorts (signed pip returns aligned to trade dir)
    # ret_5m  = last 1 M5 bar (c-o)
    # ret_15m = sum of last 3 M5 (c-o)
    # ret_30m = sum of last 6 M5 (c-o)
    def m5_ret(n):
        bars = m5_closed[-n:]
        if not bars:
            return None
        total = sum(float(b["mid"]["c"]) - float(b["mid"]["o"]) for b in bars)
        return aligned_ret(0, total, dir_, pip)
    ret_5m = m5_ret(1)
    ret_15m = m5_ret(3)
    ret_30m = m5_ret(6)

    # ADX H1
    adx14_h1 = adx(h1, 14)

    # ADR consumed: (current day high - low so far) / 14-day ADR
    if d_closed:
        adrs = []
        for c in d_closed[-15:-1]:
            adrs.append((float(c["mid"]["h"]) - float(c["mid"]["l"])) / pip)
        adr14 = mean(adrs) if adrs else None
        # current-day range — take "today" candle (last D candle, may be incomplete)
        today = d[-1] if d else None
        if today and adr14:
            tr_today = (float(today["mid"]["h"]) - float(today["mid"]["l"])) / pip
            adr_consumed = tr_today / adr14
        else:
            adr_consumed = None
    else:
        adr_consumed = None

    return {
        "rvol_5bar":        round(rvol_5bar, 2) if rvol_5bar else None,
        "rvol_12bar":       round(rvol_12bar, 2) if rvol_12bar else None,
        "rsi14_m5":         round(rsi_m5, 1) if rsi_m5 else None,
        "rsi14_h1":         round(rsi_h1, 1) if rsi_h1 else None,
        "bb_pos_h1":        round(bbp_h1, 2) if bbp_h1 is not None else None,
        "ema20_dist_pct":   round(ema20_dist, 3) if ema20_dist is not None else None,
        "ema50_dist_pct":   round(ema50_dist, 3) if ema50_dist is not None else None,
        "ret_5m_aligned":   round(ret_5m, 2) if ret_5m is not None else None,
        "ret_15m_aligned":  round(ret_15m, 2) if ret_15m is not None else None,
        "ret_30m_aligned":  round(ret_30m, 2) if ret_30m is not None else None,
        "adx14_h1":         round(adx14_h1, 1) if adx14_h1 is not None else None,
        "adr_consumed":     round(adr_consumed, 2) if adr_consumed is not None else None,
    }


def main():
    # Load existing matrix
    src = Path("/tmp/v5_full_matrix.csv")
    rows = list(csv.DictReader(src.open()))

    # Re-parse journal for entry_iso + entry_price (used by augmenter)
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
        try:
            aug = augment_trade(r["pair"], r["dir"], entry_price_by_tid[tid], entry_iso_by_tid[tid])
        except Exception as e:
            print(f"  skip {tid}: {e}", flush=True)
            continue
        new = dict(r)
        new.update(aug)
        enriched.append(new)
        print(f"  {tid} {r['pair']:<8} {r['session']:<6}  rvol5={aug['rvol_5bar']}  rsi_h1={aug['rsi14_h1']}  bb_h1={aug['bb_pos_h1']}  adx={aug['adx14_h1']}  adr={aug['adr_consumed']}  ret30m_aligned={aug['ret_30m_aligned']}", flush=True)

    out = Path("/tmp/v5_full_matrix_v2.csv")
    cols = list(enriched[0].keys())
    with out.open("w") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(enriched)
    print(f"\nwrote {out} ({len(enriched)} rows × {len(cols)} cols)")


if __name__ == "__main__":
    main()
