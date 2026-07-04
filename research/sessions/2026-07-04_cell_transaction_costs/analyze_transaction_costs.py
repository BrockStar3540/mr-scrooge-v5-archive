import csv, statistics, json, sys
from datetime import datetime, timedelta
from collections import defaultdict

CSV = sys.argv[1] if len(sys.argv) > 1 else "transactions.csv"
rows = list(csv.DictReader(open(CSV, encoding="utf-8-sig")))
fills = [r for r in rows if r["TRANSACTION TYPE"] == "ORDER_FILL"]

ENTRY = {"MARKET_ORDER", "LIMIT_ORDER"}
EXIT  = {"STOP_LOSS_ORDER", "TAKE_PROFIT_ORDER", "MARKET_ORDER_TRADE_CLOSE", "MARKET_ORDER_POSITION_CLOSEOUT"}

def session(h):
    if 7 <= h < 13: return "london"
    if 13 <= h < 22: return "ny"
    return "asia"

def parse_t(s):  # "2026-05-31 16:40:42 -12" -> UTC datetime
    return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S") + timedelta(hours=12)

# price series per pair (for quote->USD derivation)
series = defaultdict(list)
for r in fills:
    series[r["INSTRUMENT"]].append((parse_t(r["TRANSACTION DATE"]), float(r["PRICE"])))
for k in series: series[k].sort()

def nearest_price(pair, t):
    best, bd = None, None
    for tt, p in series.get(pair, []):
        d = abs((tt - t).total_seconds())
        if bd is None or d < bd: bd, best = d, p
    return best

def quote_to_usd(pair, price, t, conv_col):
    if conv_col:
        return float(conv_col)
    base, quote = pair.split("/")
    if quote == "USD": return 1.0
    if base == "USD": return 1.0 / price
    # cross: find USD/quote or quote/USD
    p = nearest_price(f"USD/{quote}", t)
    if p: return 1.0 / p
    p = nearest_price(f"{quote}/USD", t)
    if p: return p
    return None

recs = []
for r in fills:
    pair = r["INSTRUMENT"]
    t = parse_t(r["TRANSACTION DATE"])
    price = float(r["PRICE"])
    units = float(r["UNITS"])
    cost = float(r["ESTIMATED SPREAD COST"])
    conv = quote_to_usd(pair, price, t, r["CONVERSION RATE"])
    if conv is None: continue
    pipsize = 0.01 if pair.endswith("/JPY") else 0.0001
    pipval_usd = units * pipsize * conv
    cost_pips = cost / pipval_usd
    kind = "entry" if r["DETAILS"] in ENTRY else "exit"
    recs.append(dict(pair=pair, t=t, hour=t.hour, sess=session(t.hour),
                     kind=kind, cost_pips=cost_pips, pipval=pipval_usd,
                     units=units, notional_usd=units*price*(conv if pair.split("/")[1]!="USD" else 1)
                     if pair.split("/")[0]!="USD" else units))

MAIN = ["EUR/USD","GBP/USD","USD/JPY","USD/CAD","AUD/USD","EUR/JPY","AUD/JPY","USD/CHF"]

def stats(v):
    if not v: return None
    return dict(n=len(v), med=round(statistics.median(v),2),
                p75=round(sorted(v)[int(len(v)*0.75)],2),
                p90=round(sorted(v)[min(int(len(v)*0.90), len(v)-1)],2),
                mean=round(statistics.mean(v),2))

print("="*100)
print("PER-FILL HALF-SPREAD COST IN PIPS, pair x session x entry/exit  (all fills 05-31 .. 07-03)")
print("="*100)
table = {}
for pair in MAIN:
    for sess in ("asia","london","ny"):
        for kind in ("entry","exit"):
            v = [x["cost_pips"] for x in recs if x["pair"]==pair and x["sess"]==sess and x["kind"]==kind]
            table[(pair,sess,kind)] = stats(v)

hdr = f"{'pair':9}{'session':8} | {'ENTRY n':>7} {'med':>5} {'p75':>5} {'p90':>5} | {'EXIT n':>6} {'med':>5} {'p75':>5} {'p90':>5} | {'RT med':>6}"
print(hdr); print("-"*len(hdr))
rt_table = {}
for pair in MAIN:
    for sess in ("asia","london","ny"):
        e, x = table[(pair,sess,"entry")], table[(pair,sess,"exit")]
        rt = round(e["med"]+x["med"],2) if e and x else None
        rt_table[(pair,sess)] = dict(entry=e, exit=x, roundtrip_med=rt)
        es = f"{e['n']:>7} {e['med']:>5} {e['p75']:>5} {e['p90']:>5}" if e else f"{'—':>7}{'':>17}"
        xs = f"{x['n']:>6} {x['med']:>5} {x['p75']:>5} {x['p90']:>5}" if x else f"{'—':>6}{'':>17}"
        print(f"{pair:9}{sess:8} | {es} | {xs} | {str(rt) if rt else '—':>6}")
    print()

print("="*100)
print("HOURLY (UTC) round-trip-relevant cost: median per-fill cost in pips by hour, main pairs pooled")
print("="*100)
for pair in MAIN:
    line = f"{pair:9}"
    for h in range(24):
        v = [x["cost_pips"] for x in recs if x["pair"]==pair and x["hour"]==h]
        line += f"{statistics.median(v):5.2f}" if v else "    ·"
    print(line)
print("hour:     " + "".join(f"{h:5}" for h in range(24)))

# financing lumps
fin = [(parse_t(r["TRANSACTION DATE"]), float(r["FINANCING"])) for r in rows if r["TRANSACTION TYPE"]=="DAILY_FINANCING"]
tot = sum(f for _,f in fin)
print(f"\nDAILY_FINANCING: {len(fin)} days, total ${tot:+.2f}, mean ${tot/len(fin):+.2f}/day, "
      f"worst ${min(f for _,f in fin):+.2f}, best ${max(f for _,f in fin):+.2f}")

# observed sizing
bal_recs = [(parse_t(r["TRANSACTION DATE"]), float(r["BALANCE"])) for r in rows if r["BALANCE"]]
json.dump({f"{p}|{s}": rt_table[(p,s)] for p in MAIN for s in ("asia","london","ny")},
          open("cell_costs.json","w"), indent=1)
print("\nsaved cell_costs.json")
