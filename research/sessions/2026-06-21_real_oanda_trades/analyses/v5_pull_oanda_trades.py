"""Pull ACTUAL trade history from OANDA — every Buy/Sell Market Filled with
open/close times + realized P/L. Replaces journal-derived matrix.

Outputs:
  /tmp/oanda_trades_raw.json        — every transaction (with type + tradeID)
  /tmp/oanda_closed_trades.csv      — one row per closed trade with open + close
  /tmp/oanda_trades_summary.txt     — counts + first/last + by-pair distribution
"""
import os, json, csv, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

# Load secrets
for ln in open(os.path.expanduser("~/.openclaw/secrets.env")):
    if "=" in ln and not ln.strip().startswith("#"):
        k, v = ln.strip().split("=", 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")
TOKEN = os.environ["OANDA_API_TOKEN"]
ACCT  = os.environ["OANDA_ACCOUNT_ID"]
BASE  = os.environ.get("OANDA_API_URL", "https://api-fxtrade.oanda.com")

def api(path, params=None):
    url = f"{BASE}{path}"
    if params: url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

# Get all transactions in a time window — use /accounts/{id}/transactions/idrange
# We want every transaction since 2026-06-12 (covers V4 tail + all V5)
since = datetime(2026, 6, 12, tzinfo=timezone.utc)

print(f"Fetching OANDA transactions since {since.isoformat()}...")
# Step 1: get the latest transaction ID to know range
acct = api(f"/v3/accounts/{ACCT}")
last_tid = int(acct["account"]["lastTransactionID"])
print(f"  last transaction ID: {last_tid}")

# Step 2: page back through transactions until we cross `since`
all_txns = []
to_id = last_tid
batch_size = 500
while to_id > 0:
    from_id = max(1, to_id - batch_size + 1)
    try:
        page = api(f"/v3/accounts/{ACCT}/transactions/idrange",
                   {"from": from_id, "to": to_id})
    except Exception as e:
        print(f"  fetch failed {from_id}..{to_id}: {e}")
        break
    txns = page.get("transactions", [])
    if not txns:
        break
    all_txns.extend(txns)
    earliest = txns[0]
    earliest_t = datetime.fromisoformat(earliest["time"].replace("Z", "+00:00"))
    if earliest_t <= since:
        # filter to since
        all_txns = [t for t in all_txns
                    if datetime.fromisoformat(t["time"].replace("Z","+00:00")) >= since]
        break
    to_id = from_id - 1
    print(f"  fetched {len(all_txns)} txns; earliest {earliest_t.isoformat()}")

all_txns.sort(key=lambda t: int(t["id"]))
print(f"\nTotal transactions since {since.isoformat()}: {len(all_txns)}")

# Save raw
open("/tmp/oanda_trades_raw.json", "w").write(json.dumps(all_txns, indent=2))
print(f"→ /tmp/oanda_trades_raw.json ({os.path.getsize('/tmp/oanda_trades_raw.json')/1024:.0f} KB)")

# Step 3: build closed-trade records from ORDER_FILL transactions
# ORDER_FILL with tradeOpened = trade opened with this fill
# ORDER_FILL with tradesClosed = trade(s) closed with this fill
# Each tradeClosed has tradeID, realizedPL, units (signed: pos = was long), price
opened = {}  # tradeID → {pair, side, openTime, openPrice, units, openTxn_id}
closed_records = []
for t in all_txns:
    if t.get("type") != "ORDER_FILL":
        continue
    instr = t.get("instrument")
    ts = t.get("time")
    fill_price = float(t.get("price", 0))
    txn_id = t["id"]
    # Opening
    if t.get("tradeOpened"):
        to = t["tradeOpened"]
        trade_id = to["tradeID"]
        units = float(to["units"])
        opened[trade_id] = {
            "pair": instr,
            "side": "long" if units > 0 else "short",
            "units": abs(units),
            "open_time": ts,
            "open_price": fill_price,
            "open_txn_id": txn_id,
        }
    # Closing
    for tc in t.get("tradesClosed", []) or []:
        trade_id = tc["tradeID"]
        rec = opened.pop(trade_id, None)
        if rec is None:
            # opened before our window
            rec = {"pair": instr, "side": "?", "units": abs(float(tc.get("units", 0))),
                   "open_time": None, "open_price": None, "open_txn_id": None}
        closed_records.append({
            **rec,
            "trade_id": trade_id,
            "close_time": ts,
            "close_price": fill_price,
            "close_units": float(tc.get("units", 0)),
            "realized_pl_usd": float(tc.get("realizedPL", 0)),
            "close_txn_id": txn_id,
            "close_reason": t.get("reason", ""),
        })

# Also note trades still open
print(f"\nClosed trades: {len(closed_records)}")
print(f"Still open: {len(opened)} → trade IDs: {list(opened.keys())[:10]}")

# Save CSV
with open("/tmp/oanda_closed_trades.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["trade_id","pair","side","units","open_time","open_price",
                                       "close_time","close_price","close_units","realized_pl_usd",
                                       "open_txn_id","close_txn_id","close_reason"])
    w.writeheader()
    w.writerows(closed_records)
print(f"→ /tmp/oanda_closed_trades.csv")

# Summary
from collections import Counter
by_pair = Counter(r["pair"] for r in closed_records)
by_side = Counter(r["side"] for r in closed_records)
by_reason = Counter(r["close_reason"] for r in closed_records)

print(f"\n=== SUMMARY ===")
print(f"Period: {since.isoformat()} → present")
print(f"Closed trades: {len(closed_records)}")
print(f"Open positions still: {len(opened)}")
print(f"\nBy pair: {dict(by_pair.most_common())}")
print(f"By side: {dict(by_side)}")
print(f"By close reason: {dict(by_reason.most_common())}")
total_pl = sum(r["realized_pl_usd"] for r in closed_records)
print(f"Total realized P/L: ${total_pl:+.2f}")
print(f"Winners: {sum(1 for r in closed_records if r['realized_pl_usd'] > 0)}")
print(f"Losers:  {sum(1 for r in closed_records if r['realized_pl_usd'] < 0)}")

# Save summary
open("/tmp/oanda_trades_summary.txt", "w").write(f"""OANDA trade pull summary
Period: {since.isoformat()} → present
Closed trades: {len(closed_records)}
Still open: {len(opened)}
By pair: {dict(by_pair.most_common())}
By side: {dict(by_side)}
By close reason: {dict(by_reason.most_common())}
Total realized P/L: ${total_pl:+.2f}
Winners: {sum(1 for r in closed_records if r['realized_pl_usd'] > 0)}
Losers: {sum(1 for r in closed_records if r['realized_pl_usd'] < 0)}
""")
