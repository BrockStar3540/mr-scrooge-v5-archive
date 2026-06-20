#!/usr/bin/env python3
"""V5 per-trade analysis matrix.

For every trade in V5's journalctl:
  1. Parse the SIGNAL line: composite_score, d_cert, m_cert, expected_pips, vol_regime
  2. Reverse-solve raw direction.score = composite_score / (d_cert × m_cert)
  3. Pull OANDA M5 candles around entry → tick volume + spread at entry
  4. Pull OANDA M1 candles entry→exit → peak MFE
  5. Optional: pull H1 candle preceding entry → h1_ret_1bar (signed momentum check)

Then compute Pearson + Spearman correlations of each signal vs peak_pips
and vs exit_net_pips. Brock wants to know which signal predicts pip travel best.
"""
import os, json, re, sys
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta
from statistics import correlation as pearson  # 3.10+

API = os.environ["OANDA_API_URL"]
TOKEN = os.environ["OANDA_API_TOKEN"]
JOURNAL = Path("/tmp/v5_journal_full.log")

PIP_SIZE = {
    "AUD_USD": 0.0001, "EUR_USD": 0.0001, "GBP_USD": 0.0001, "USD_CAD": 0.0001,
    "USD_JPY": 0.01, "USD_CHF": 0.0001, "AUD_JPY": 0.01, "EUR_JPY": 0.01,
}


def fetch(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def parse_journal():
    """Build {tid: {pair, dir, entry_iso, exit_iso, composite, d_cert, m_cert, expected, vol_regime, raw_dir, exit_net}}"""
    trades = {}
    pending_signal = None  # the most recent SIGNAL line (matched to next ENTERED)

    for line in JOURNAL.read_text().splitlines():
        m_dt = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
        if not m_dt:
            continue
        ts_iso = m_dt.group(1).replace(" ", "T") + "Z"

        m_sig = re.search(
            r"SIGNAL (\S+) (\S+) \| score=([\-0-9.]+) d_cert=([\-0-9.]+) m_cert=([\-0-9.]+) "
            r"expected=([\-0-9.]+)p vol=(\S+) rivals=(\d+)", line)
        if m_sig:
            pending_signal = {
                "pair": m_sig.group(1), "dir": m_sig.group(2),
                "composite": float(m_sig.group(3)),
                "d_cert": float(m_sig.group(4)), "m_cert": float(m_sig.group(5)),
                "expected": float(m_sig.group(6)), "vol_regime": m_sig.group(7),
                "rivals": int(m_sig.group(8)), "ts": ts_iso,
            }
            continue

        m_en = re.search(r"ENTERED (\S+) (\S+) @ ([\d.]+).*trade_id=(\d+)", line)
        if m_en:
            tid = m_en.group(4)
            if pending_signal and pending_signal["pair"] == m_en.group(1) and pending_signal["dir"] == m_en.group(2):
                trades[tid] = dict(pending_signal)
                trades[tid]["entry_iso"] = ts_iso
                trades[tid]["entry_price"] = float(m_en.group(3))
                trades[tid]["exit_iso"] = None
                trades[tid]["exit_net"] = None
                # Reverse-solve raw direction.score
                denom = trades[tid]["d_cert"] * trades[tid]["m_cert"]
                trades[tid]["raw_dir"] = (trades[tid]["composite"] / denom) if denom > 0 else 0.0
                pending_signal = None
            continue

        m_ex = re.search(r"EXIT.*?(\w+_\w+) \| trade_id=(\d+) \| approx_net=([\-0-9.]+)p", line)
        if m_ex:
            tid = m_ex.group(2)
            if tid in trades:
                trades[tid]["exit_iso"] = ts_iso
                trades[tid]["exit_net"] = float(m_ex.group(3))
    return trades


def fetch_m5_at_entry(pair, entry_iso):
    """Fetch M5 mid + bid + ask candle preceding entry. Returns (volume, spread_pips)."""
    # Use a 30-min window ending at entry — find the M5 bar that contains/precedes entry
    entry_dt = datetime.strptime(entry_iso, "%Y-%m-%dT%H:%M:%SZ")
    from_dt = entry_dt - timedelta(minutes=10)
    to_dt = entry_dt + timedelta(minutes=5)
    f = from_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    t = to_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"{API}/v3/instruments/{pair}/candles?granularity=M5&from={f}&to={t}&price=MBA"
    data = fetch(url)
    candles = data.get("candles", [])
    if not candles:
        return None, None
    # find the M5 bar that contains entry_dt
    best = None
    for c in candles:
        ct = datetime.strptime(c["time"][:19], "%Y-%m-%dT%H:%M:%S")
        if ct <= entry_dt:
            best = c
    if best is None:
        best = candles[0]
    vol = int(best["volume"])
    pip = PIP_SIZE[pair]
    bid_c = float(best["bid"]["c"])
    ask_c = float(best["ask"]["c"])
    spread_pips = (ask_c - bid_c) / pip
    return vol, spread_pips


def fetch_m1_peak(pair, dir_, entry_price, entry_iso, exit_iso):
    """Peak MFE in pips between entry and exit."""
    url = f"{API}/v3/instruments/{pair}/candles?granularity=M1&from={entry_iso}&to={exit_iso}&price=M"
    data = fetch(url)
    pip = PIP_SIZE[pair]
    peak = 0.0
    for c in data.get("candles", []):
        if not c.get("complete"):
            continue
        hi = float(c["mid"]["h"])
        lo = float(c["mid"]["l"])
        move = (hi - entry_price) / pip if dir_ == "long" else (entry_price - lo) / pip
        if move > peak:
            peak = move
    return peak


def fetch_h1_ret_1bar(pair, entry_iso):
    """Signed pip return of the H1 bar most recently closed before entry.

    Per yesterday's matrix work this was 100% accurate for direction on the
    morning's trades — Brock's hypothesized momentum-direction gate.
    """
    entry_dt = datetime.strptime(entry_iso, "%Y-%m-%dT%H:%M:%SZ")
    from_dt = entry_dt - timedelta(hours=3)
    f = from_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    t = entry_iso
    url = f"{API}/v3/instruments/{pair}/candles?granularity=H1&from={f}&to={t}&price=M"
    data = fetch(url)
    candles = [c for c in data.get("candles", []) if c.get("complete")]
    if not candles:
        return None
    last = candles[-1]
    pip = PIP_SIZE[pair]
    o = float(last["mid"]["o"])
    c = float(last["mid"]["c"])
    return (c - o) / pip


def spearman(xs, ys):
    """Simple Spearman rank correlation."""
    def rank(arr):
        sorted_pairs = sorted(enumerate(arr), key=lambda p: p[1])
        ranks = [0] * len(arr)
        for new_rank, (orig_idx, _) in enumerate(sorted_pairs):
            ranks[orig_idx] = new_rank + 1
        return ranks
    if len(xs) < 3:
        return None
    return pearson(rank(xs), rank(ys))


def main():
    trades = parse_journal()
    print(f"parsed {len(trades)} trade events from journal", file=sys.stderr)

    rows = []
    for tid in sorted(trades.keys(), key=int):
        t = trades[tid]
        if t["exit_iso"] is None or t["exit_net"] is None:
            continue
        try:
            vol, spread = fetch_m5_at_entry(t["pair"], t["entry_iso"])
            peak = fetch_m1_peak(t["pair"], t["dir"], t["entry_price"], t["entry_iso"], t["exit_iso"])
            h1ret = fetch_h1_ret_1bar(t["pair"], t["entry_iso"])
        except Exception as e:
            print(f"  skip {tid}: {e}", file=sys.stderr)
            continue
        # Signed h1_ret aligned with trade direction → positive = momentum agrees
        h1_aligned = (h1ret if t["dir"] == "long" else -h1ret) if h1ret is not None else None
        rows.append({
            "tid": tid, "pair": t["pair"], "dir": t["dir"],
            "raw_dir": t["raw_dir"], "composite": t["composite"],
            "d_cert": t["d_cert"], "m_cert": t["m_cert"],
            "expected": t["expected"], "vol_regime": t["vol_regime"],
            "m5_volume": vol, "spread_pips": spread,
            "h1_ret_aligned": h1_aligned,
            "peak_pips": peak, "exit_net": t["exit_net"],
        })
        print(f"  {tid} {t['pair']:<8} {t['dir']:<5}  raw_dir={t['raw_dir']:+.3f}  m_cert={t['m_cert']:.3f}  vol5m={vol}  h1_aligned={h1_aligned:+.2f}p  peak={peak:+.2f}p  exit={t['exit_net']:+.2f}p")

    print(f"\nfinal trade count with full features: {len(rows)}", file=sys.stderr)
    # Write CSV
    out = Path("/tmp/v5_trade_matrix.csv")
    cols = list(rows[0].keys())
    with out.open("w") as f:
        f.write(",".join(cols) + "\n")
        for r in rows:
            f.write(",".join(f"{r[c]:.4f}" if isinstance(r[c], float) and r[c] is not None
                             else ("" if r[c] is None else str(r[c]))
                             for c in cols) + "\n")
    print(f"\nwrote {out}")

    # === correlations ===
    def corr_block(label, target_key):
        print(f"\n=== correlations vs {label} ({target_key}) ===")
        targets = [r[target_key] for r in rows]
        for feat in ("raw_dir", "composite", "d_cert", "m_cert", "expected",
                     "m5_volume", "spread_pips", "h1_ret_aligned"):
            xs = [r[feat] for r in rows if r[feat] is not None]
            ys = [r[target_key] for r in rows if r[feat] is not None]
            if len(xs) < 3:
                continue
            try:
                p = pearson(xs, ys)
                s = spearman(xs, ys)
                # Sign-correlation (does the SIGN of feature predict the SIGN of target)
                pos_target = sum(1 for x, y in zip(xs, ys) if (x > 0) == (y > 0))
                acc = pos_target / len(xs)
                print(f"  {feat:<18}  pearson={p:+.3f}  spearman={s:+.3f}  sign_acc={acc:.2%}  n={len(xs)}")
            except Exception as e:
                print(f"  {feat}: err {e}")

    if rows:
        # For raw_dir we want to test against the ABSOLUTE pip travel (peak)
        # since raw_dir is signed but peak is always >= 0 (MFE).
        # Use |raw_dir| for fairness.
        for r in rows:
            r["abs_raw_dir"] = abs(r["raw_dir"])
            r["abs_composite"] = abs(r["composite"])
            r["abs_h1_aligned"] = abs(r["h1_ret_aligned"]) if r["h1_ret_aligned"] is not None else None

        print("\n=== |signal_magnitude| → peak_pips (MFE) — does the SIZE of the signal predict the SIZE of travel? ===")
        for feat in ("abs_raw_dir", "abs_composite", "d_cert", "m_cert", "expected",
                     "m5_volume", "spread_pips", "abs_h1_aligned"):
            xs = [r[feat] for r in rows if r[feat] is not None]
            ys = [r["peak_pips"] for r in rows if r[feat] is not None]
            if len(xs) < 3:
                continue
            try:
                p = pearson(xs, ys)
                s = spearman(xs, ys)
                print(f"  {feat:<18}  pearson={p:+.3f}  spearman={s:+.3f}  n={len(xs)}")
            except Exception as e:
                print(f"  {feat}: err {e}")

        print("\n=== signal_aligned → exit_net (signed) — does signal direction match outcome direction? ===")
        for feat in ("raw_dir", "composite", "h1_ret_aligned"):
            xs = [r[feat] for r in rows if r[feat] is not None]
            ys = [r["exit_net"] for r in rows if r[feat] is not None]
            if len(xs) < 3:
                continue
            try:
                p = pearson(xs, ys)
                s = spearman(xs, ys)
                pos = sum(1 for x, y in zip(xs, ys) if (x > 0) == (y > 0))
                acc = pos / len(xs)
                print(f"  {feat:<18}  pearson={p:+.3f}  spearman={s:+.3f}  dir_match_acc={acc:.2%}  n={len(xs)}")
            except Exception as e:
                print(f"  {feat}: err {e}")


if __name__ == "__main__":
    main()
