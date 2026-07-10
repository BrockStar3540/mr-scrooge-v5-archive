#!/usr/bin/env python3
"""research/tools/center_probe_score.py — mine the center-probe log for a
which-way filter. For each matured observation, fetch the forward M5 path and
measure signed_travel = fwd_up − fwd_down (which wall the wave rode). Then rank
every logged indicator by how well it separates up-rides from down-rides.

Run on the Mini (or EC2 with broker creds). Prints the direction-separation
leaderboard; needs ~n>=100 matured observations to mean anything.
"""
import os, json, sys, time, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

LOG = Path(__file__).resolve().parents[2] / "data" / "center_probe_log.jsonl" \
      if (Path(__file__).resolve().parents[2] / "data" / "center_probe_log.jsonl").exists() \
      else Path(os.path.expanduser("~/mr-scrooge-v5/data/center_probe_log.jsonl"))

def creds():
    for line in open(os.path.expanduser("~/.openclaw/secrets.env")):
        line=line.strip()
        if line and not line.startswith("#") and "=" in line:
            k,v=line.split("=",1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return (os.environ.get("OANDA_API_URL","https://api-fxpractice.oanda.com").rstrip("/"),
            os.environ["OANDA_API_TOKEN"])

def fwd(url, tok, pair, t0):
    pm = 0.01 if "JPY" in pair else 0.0001
    u=f"{url}/v3/instruments/{pair}/candles?granularity=M5&from={t0.strftime('%Y-%m-%dT%H:%M:%SZ')}&count=49&price=M"
    cs=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={"Authorization":f"Bearer {tok}"}),timeout=20))["candles"]
    if len(cs)<13: return None
    e=float(cs[0]["mid"]["o"])
    up=(max(float(c["mid"]["h"]) for c in cs)-e)/pm
    dn=(e-min(float(c["mid"]["l"]) for c in cs))/pm
    return up-dn   # signed travel: + rode up, − rode down

def main():
    if not LOG.exists(): print("no probe log yet:", LOG); return
    obs=[json.loads(l) for l in open(LOG) if l.strip()]
    print(f"observations logged: {len(obs)}")
    url,tok=creds()
    now=datetime.now(timezone.utc)
    scored=[]
    for o in obs:
        t0=datetime.fromisoformat(o["ts"])
        if (now-t0).total_seconds() < 245*60: continue
        try:
            st=fwd(url,tok,o["pair"],t0)
            if st is not None: o["signed_travel"]=st; scored.append(o); time.sleep(0.04)
        except Exception: continue
    print(f"matured & scored: {len(scored)}")
    if len(scored) < 40:
        print("insufficient — let it accumulate (target n>=100)"); return
    import statistics as st
    try:
        from scipy.stats import spearmanr
    except Exception:
        spearmanr=None
    feats=[k for k in scored[0] if k not in ("ts","pair","session","mid","box","signed_travel") and scored[0][k] is not None]
    y=[o["signed_travel"] for o in scored]
    print(f"\nbase: {sum(1 for v in y if v>0)}/{len(y)} rode UP | median signed travel {st.median(y):+.1f}p")
    print("\nDIRECTION SEPARATORS (indicator vs signed_travel):")
    rows=[]
    for f in feats:
        xs=[(o[f],o["signed_travel"]) for o in scored if isinstance(o.get(f),(int,float))]
        if len(xs)<40: continue
        if spearmanr:
            r=spearmanr([a for a,_ in xs],[b for _,b in xs]).statistic
        else:
            r=0.0
        # top vs bottom tercile mean signed travel
        xs.sort(); k=len(xs)//3
        lo=st.mean(b for _,b in xs[:k]); hi=st.mean(b for _,b in xs[-k:])
        rows.append((abs(hi-lo), f, r, lo, hi, len(xs)))
    for sep,f,r,lo,hi,n in sorted(rows,reverse=True)[:15]:
        print(f"  {f:20} rho {r:+.3f} | low-third {lo:+6.1f}p  high-third {hi:+6.1f}p  spread {hi-lo:+6.1f}p (n={n})")
    print("\nA feature with rho>|0.15| and a monotone low→high spread is a which-way candidate.")

if __name__=="__main__": main()
