"""Measure the shadow-inverted cells: parse SHADOW_INVERT journal lines,
pull the 1H forward from OANDA, report whether the INVERTED direction would
have profited net of spread.

Run on EC2 (has OANDA token + journalctl). Run periodically as signals
accumulate (e.g. every few days). When ~30 NY signals exist with a settled
1H forward AND inverted clears spread, promote the cell from disabled to
inverted-active.

  SHADOW_INVERT GBP_USD ny | v5_dir=short inverted_dir=long score=-0.180 \\
    d_cert=0.400 m_cert=0.500 mid=1.32050 ts=2026-06-22T13:05:00+00:00
"""
import os, re, json, subprocess, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

for ln in open(os.path.expanduser("~/.openclaw/secrets.env")):
    if "=" in ln and not ln.strip().startswith("#"):
        k, v = ln.strip().split("=", 1); os.environ[k.strip()] = v.strip().strip('"').strip("'")
TOKEN = os.environ["OANDA_API_TOKEN"]
BASE  = os.environ.get("OANDA_API_URL", "https://api-fxtrade.oanda.com")
PIP = {"GBP_USD":0.0001, "EUR_JPY":0.01}
SPREAD = {"GBP_USD":1.5, "EUR_JPY":1.8}

# 1. Pull SHADOW_INVERT lines from the journal (V5-era)
res = subprocess.run(
    ["journalctl","--user","-u","mr-scrooge-v5","--since","2026-06-21","--no-pager","-o","cat"],
    env={**os.environ, "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}", "SYSTEMD_PAGER":""},
    capture_output=True, text=True)
rx = re.compile(r"SHADOW_INVERT (\w+) (\w+) \| v5_dir=(\w+) inverted_dir=(\w+) score=([\-\d.]+) "
                r"d_cert=([\d.]+) m_cert=([\d.]+) mid=([\d.]+) ts=(\S+)")
sigs = []
for line in res.stdout.splitlines():
    m = rx.search(line)
    if m:
        pair, sess, v5dir, invdir, score, dc, mc, mid, ts = m.groups()
        sigs.append({"pair":pair,"session":sess,"v5_dir":v5dir,"inverted_dir":invdir,
                     "score":float(score),"d_cert":float(dc),"m_cert":float(mc),
                     "mid":float(mid),"ts":datetime.fromisoformat(ts)})
print(f"SHADOW_INVERT signals parsed: {len(sigs)}")
if not sigs:
    print("No shadow-invert signals yet. They appear when GBP_USD/ny or EUR_JPY/ny produce a")
    print("fresh actionable signal during the NY session (13:00-15:00 UTC). Re-run after a few NY sessions.")
    raise SystemExit(0)

# 2. For each signal with a settled 1H forward, pull OANDA M5 and compute forward pip
def fetch_m5(pair, start, end):
    url = f"{BASE}/v3/instruments/{pair}/candles?" + urllib.parse.urlencode({
        "from": start.isoformat().replace("+00:00","Z"), "to": end.isoformat().replace("+00:00","Z"),
        "granularity":"M5","price":"M"})
    req = urllib.request.Request(url, headers={"Authorization":f"Bearer {TOKEN}"})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())
    return [(c["time"], float(c["mid"]["c"])) for c in data.get("candles",[]) if c.get("complete")]

now = datetime.now(timezone.utc)
rows = []
for s in sigs:
    if (now - s["ts"]).total_seconds() < 3900:   # need 60min + buffer settled
        continue
    pip = PIP[s["pair"]]
    cs = fetch_m5(s["pair"], s["ts"] - timedelta(minutes=10), s["ts"] + timedelta(minutes=75))
    if len(cs) < 13: continue
    times = [datetime.fromisoformat(t.replace("Z","+00:00")) for t,_ in cs]
    closes = [c for _,c in cs]
    # entry = last close at/before ts; +12 bars = 60min
    entry_i = max(i for i,t in enumerate(times) if t <= s["ts"]) if any(t<=s["ts"] for t in times) else 0
    if entry_i + 12 >= len(closes): continue
    fwd = (closes[entry_i+12] - closes[entry_i]) / pip
    # follow = V5's direction; inverted = opposite
    follow_signed = fwd if s["v5_dir"]=="long" else -fwd
    inverted_signed = -follow_signed
    rows.append({**s, "fwd_60m": round(fwd,2),
                 "follow_pip": round(follow_signed,2),
                 "invert_pip": round(inverted_signed,2),
                 "invert_net_spread": round(inverted_signed - SPREAD[s["pair"]],2)})

print(f"Signals with settled 1H forward: {len(rows)}")
if not rows:
    print("Signals exist but none settled yet (need 60min+ elapsed). Re-run later.")
    raise SystemExit(0)

# 3. Report per cell
import statistics as st
print(f"\n=== SHADOW-INVERT RESULTS per cell ===")
by = {}
for r in rows:
    by.setdefault(r["pair"], []).append(r)
for pair, rs in sorted(by.items()):
    inv = [r["invert_pip"] for r in rs]
    net = [r["invert_net_spread"] for r in rs]
    follow = [r["follow_pip"] for r in rs]
    inv_wr = sum(1 for x in inv if x>0)/len(inv)
    print(f"\n  {pair}/ny  (n={len(rs)})")
    print(f"    V5 follow mean:        {st.mean(follow):+.2f}p  (what V5 would have earned trading WITH signal)")
    print(f"    inverted mean:         {st.mean(inv):+.2f}p")
    print(f"    inverted net of spread:{st.mean(net):+.2f}p  (spread={SPREAD[pair]})")
    print(f"    inverted win rate:     {inv_wr:.0%}")
    promote = st.mean(net) > 0 and len(rs) >= 30
    print(f"    → PROMOTE to inverted-active? {'YES' if promote else 'not yet'} "
          f"(need net>0 AND n>=30; have net={st.mean(net):+.2f} n={len(rs)})")

# save
out = "/tmp/invert_shadow_results.json"
json.dump([{**r, "ts": r["ts"].isoformat()} for r in rows], open(out,"w"), indent=2, default=str)
print(f"\n→ {out}")
