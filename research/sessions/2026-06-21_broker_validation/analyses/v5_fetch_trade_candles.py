"""For each of the 120 OANDA trades, fetch FRESH M5 candles from OANDA spanning
[entry-24h, entry+90min]. Save as one bundle JSON for Mini-side compute.

Run on EC2 (has OANDA token in ~/.openclaw/secrets.env).
"""
import os, json, csv, time, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

for ln in open(os.path.expanduser("~/.openclaw/secrets.env")):
    if "=" in ln and not ln.strip().startswith("#"):
        k, v = ln.strip().split("=", 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")
TOKEN = os.environ["OANDA_API_TOKEN"]
BASE  = os.environ.get("OANDA_API_URL", "https://api-fxtrade.oanda.com")

def fetch(pair, granularity, start, end):
    """Fetch candles between start and end times (UTC datetimes)."""
    url = f"{BASE}/v3/instruments/{pair}/candles?" + urllib.parse.urlencode({
        "from": start.isoformat().replace("+00:00", "Z"),
        "to":   end.isoformat().replace("+00:00", "Z"),
        "granularity": granularity, "price": "M",
    })
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    rows = []
    for c in data.get("candles", []):
        if not c.get("complete"): continue
        m = c["mid"]
        rows.append([c["time"], float(m["o"]), float(m["h"]), float(m["l"]), float(m["c"]),
                     int(c.get("volume", 0))])
    return rows

# Load the OANDA trades
trades_csv = "/tmp/oanda_all_classified.csv"
trades = []
with open(trades_csv) as f:
    for row in csv.DictReader(f):
        if row["side"] not in ("long","short"): continue
        row["open_time_dt"] = datetime.fromisoformat(row["open_time"].replace(" ", "T").replace("Z","+00:00"))
        if "+" not in row["open_time"]:
            row["open_time_dt"] = row["open_time_dt"].replace(tzinfo=timezone.utc)
        trades.append(row)
print(f"Loaded {len(trades)} trades with valid side")

bundle = {"trades": [], "candles": {}}
for i, t in enumerate(trades):
    et = t["open_time_dt"]
    pair = t["pair"]
    tid = t["trade_id"]
    # Window: [entry - 36h, entry + 90min] to give enough trailing bars + forward window
    start = et - timedelta(hours=36)
    end   = et + timedelta(minutes=90)
    try:
        m5 = fetch(pair, "M5", start, end)
        h1 = fetch(pair, "H1", et - timedelta(days=14), et + timedelta(minutes=5))
        d  = fetch(pair, "D",  et - timedelta(days=120), et + timedelta(minutes=5))
    except Exception as exc:
        print(f"  fail tid={tid} pair={pair}: {exc}")
        continue
    bundle["candles"][tid] = {"m5": m5, "h1": h1, "d1": d}
    bundle["trades"].append({
        "trade_id": tid, "pair": pair, "side": t["side"],
        "session": t.get("session"),
        "open_time_iso": t["open_time"],
        "open_price": float(t.get("open_price") or 0),
        "close_time": t.get("close_time"),
        "close_price": float(t.get("close_price") or 0),
        "realized_pl_usd": float(t.get("realized_pl_usd") or 0),
        "exit_class": t.get("exit_class"),
    })
    if (i+1) % 20 == 0:
        print(f"  fetched {i+1}/{len(trades)}")
    time.sleep(0.1)

out = "/tmp/v5_trade_candles_bundle.json"
open(out, "w").write(json.dumps(bundle))
total_candles = sum(len(c["m5"]) + len(c["h1"]) + len(c["d1"]) for c in bundle["candles"].values())
print(f"\nBundle: {len(bundle['trades'])} trades, {total_candles} total candles, {os.path.getsize(out)/1024:.0f} KB")
