"""Phase 1: parse journal for trade entry times + pre-fetch OANDA candles
   for all 44 matrix trades. Ship the bundle to Mini for qtl-side analysis."""
import os, re, json, csv, urllib.parse, urllib.request, sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

for ln in open(os.path.expanduser("~/.openclaw/secrets.env")):
    if "=" in ln and not ln.strip().startswith("#"):
        k, v = ln.strip().split("=", 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")
TOKEN = os.environ["OANDA_API_TOKEN"]
BASE  = os.environ.get("OANDA_API_URL", "https://api-fxtrade.oanda.com")

ROOT = Path("/home/ubuntu/mr-scrooge-v5/research/sessions/2026-06-19_matrix_compilation/data")
MATRIX = ROOT / "v5_full_matrix_v2.csv"
JOURNAL = ROOT / "v5_journal_full.log"

# ── Parse matrix ─────────────────────────────────────────────────────────────
trades = []
with open(MATRIX) as f:
    for r in csv.DictReader(f):
        r["tid"] = str(r["tid"])
        trades.append(r)
print(f"loaded {len(trades)} trades from matrix")

# ── Extract entry times from journal ──────────────────────────────────────────
# ENTERED format: "Jun 18 09:00:30 ip-... INFO v5.engine  ENTERED EUR_JPY short @ 162.453 | 12345 units | SL -12.0p | trade_id=8802"
entered_re = re.compile(r"(\S+ \d+ \S+) \S+ python3\[\d+\]: \S+ \S+ INFO v5\.engine\s+ENTERED (\w+) (\w+) @ ([\d.]+) \| (\d+) units .* trade_id=(\d+)")
year_now = 2026  # journal lacks year; matrix is from Jun 2026
entry_times = {}
with open(JOURNAL) as f:
    for line in f:
        m = entered_re.search(line)
        if m:
            ts_str, pair, direction, price, units, tid = m.groups()
            # "Jun 18 09:00:30" → datetime
            try:
                ts = datetime.strptime(f"{year_now} {ts_str}", "%Y %b %d %H:%M:%S")
                entry_times[tid] = ts.replace(tzinfo=timezone.utc)
            except ValueError as e:
                print(f"  parse fail: {ts_str}: {e}")
print(f"parsed {len(entry_times)} entry times from journal")

# Match
matched = 0
for t in trades:
    et = entry_times.get(t["tid"])
    t["entry_time_iso"] = et.isoformat() if et else None
    if et: matched += 1
print(f"matched {matched}/{len(trades)} trades to entry times")
unmatched = [t["tid"] for t in trades if not t["entry_time_iso"]]
if unmatched:
    print(f"unmatched tids: {unmatched[:10]}")

# ── Fetch OANDA candles for each matched trade ──────────────────────────────
# For each trade, fetch:
#   M5 — last 500 bars ending at entry_time (covers ~41h; plenty for most indicators)
#   H1 — last 300 bars (~12.5 days)
#   D  — last 100 bars (~3.3 months — needed for HTF/cycle)
def fetch_candles(pair, granularity, count, end_time):
    """Fetch `count` candles of `granularity` ending at end_time."""
    url = f"{BASE}/v3/instruments/{pair}/candles?" + urllib.parse.urlencode({
        "count": count, "granularity": granularity, "price": "M",
        "to": end_time.isoformat().replace("+00:00", "Z"),
    })
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    rows = []
    for c in data.get("candles", []):
        if not c.get("complete"): continue
        m = c["mid"]
        rows.append([c["time"], float(m["o"]), float(m["h"]), float(m["l"]),
                     float(m["c"]), int(c.get("volume", 0))])
    return rows

bundle = {"trades": [], "candles": {}}
import time as _time
for i, t in enumerate(trades):
    if not t["entry_time_iso"]: continue
    et = datetime.fromisoformat(t["entry_time_iso"])
    pair = t["pair"]; tid = t["tid"]
    try:
        m5  = fetch_candles(pair, "M5",  500, et)
        h1  = fetch_candles(pair, "H1",  300, et)
        d1  = fetch_candles(pair, "D",   100, et)
        bundle["candles"][tid] = {"m5": m5, "h1": h1, "d1": d1}
        bundle["trades"].append({
            "tid": tid, "pair": pair, "session": t["session"], "dir": t["dir"],
            "entry_time_iso": t["entry_time_iso"],
            "exit_net": float(t["exit_net"]),
            "peak_pips": float(t["peak_pips"]),
            "composite": float(t["composite"]),
        })
    except Exception as exc:
        print(f"  fetch fail tid={tid} pair={pair}: {exc}")
    if (i+1) % 10 == 0:
        print(f"  fetched {i+1}/{len(trades)}")
    _time.sleep(0.1)  # be polite to OANDA

out = Path("/tmp/v5_qtl_prefetch_bundle.json")
out.write_text(json.dumps(bundle))
print(f"\nbundle: {len(bundle['trades'])} trades, {sum(len(c['m5'])+len(c['h1'])+len(c['d1']) for c in bundle['candles'].values())} candles total")
print(f"→ {out}  ({out.stat().st_size/1024:.0f} KB)")
