#!/usr/bin/env python3
"""Test mcert vs abs(MAE) correlation across ALL trades since 2026-06-22 04:14.
Brock observed -0.875 correlation on 6 AUD_JPY trades. Validate on broader sample."""
from __future__ import annotations
import os, re, subprocess, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests
import statistics as stats

SINCE = "2026-06-22 04:14:00"
PIP = {"USD_JPY":0.01,"EUR_JPY":0.01,"AUD_JPY":0.01,
       "EUR_USD":0.0001,"GBP_USD":0.0001,"AUD_USD":0.0001,
       "USD_CAD":0.0001,"USD_CHF":0.0001}

env = Path.home() / ".openclaw" / "secrets.env"
for ln in env.read_text().splitlines():
    if "=" in ln and not ln.startswith("#"):
        k,v = ln.split("=",1); os.environ[k.strip()] = v.strip().strip('"').strip("'")
TOKEN = os.environ["OANDA_API_TOKEN"]
OANDA = os.environ.get("OANDA_API_URL","https://api-fxpractice.oanda.com").rstrip("/")
HDR = {"Authorization": f"Bearer {TOKEN}"}

ENTERED = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ INFO v5\.engine\s+ENTERED (\w+) (long|short) @ ([\d.]+) \| \d+ units \| SL [+-]?[\d.]+p \| trade_id=(\d+)")
EXIT = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ INFO v5\.engine\s+EXIT.*?(\w+) \| trade_id=(\d+) \| approx_net=([+-]?[\d.]+)p")
SIGNAL = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ INFO v5\.engine\s+SIGNAL (\w+) (long|short) \| score=([+-]?[\d.]+) d_cert=([+-]?[\d.]+) m_cert=([+-]?[\d.]+) expected=([+-]?[\d.]+)p vol=\w+ rivals=\d+ \| active_side=\S+ long_prof=\S+ short_prof=\S+ mom_prof=\S+ gates=\w+ cert_boost=[+-]?[\d.]+ \| shadow_vortex_diff=([+-]?[\d.]+) shadow_close_pos=([+-]?[\d.]+)")

raw = subprocess.check_output(["journalctl","--user","-u","mr-scrooge-v5","--since",SINCE,"--no-pager","-o","cat"], text=True)
ents, exts, sigs = {}, {}, []
for ln in raw.splitlines():
    if m := ENTERED.search(ln):
        ts,pair,dr,ep,tid = m.groups(); ents[tid] = {"ts":ts,"pair":pair,"dir":dr,"entry":float(ep)}
    elif m := EXIT.search(ln):
        ts,pair,tid,net = m.groups(); exts[tid] = {"ts":ts,"net":float(net)}
    elif m := SIGNAL.search(ln):
        sigs.append({"ts":m.group(1),"pair":m.group(2),"dir":m.group(3),
                     "dir_score":float(m.group(4)),"d_cert":float(m.group(5)),"m_cert":float(m.group(6)),
                     "expected":float(m.group(7)),"vortex":float(m.group(8)),"cpos":float(m.group(9))})

# Match SIGNAL → ENTRY within 10s same pair
for tid,e in ents.items():
    edt = datetime.strptime(e["ts"],"%Y-%m-%d %H:%M:%S"); best = None
    for s in sigs:
        if s["pair"]!=e["pair"]: continue
        sdt = datetime.strptime(s["ts"],"%Y-%m-%d %H:%M:%S"); dt=(edt-sdt).total_seconds()
        if 0<=dt<=10:
            if best is None or sdt > datetime.strptime(best["ts"],"%Y-%m-%d %H:%M:%S"): best = s
    e["sig"] = best

def fetch_m1(pair, ts_from, ts_to):
    url = f"{OANDA}/v3/instruments/{pair}/candles"
    r = requests.get(url, headers=HDR, params={"from":ts_from,"to":ts_to,"granularity":"M1","price":"M"}, timeout=30)
    r.raise_for_status(); return r.json().get("candles",[])

def iso(dt): return dt.isoformat().replace("+00:00","Z")

# Compute MFE/MAE per closed trade
rows = []
for tid in sorted(ents.keys(), key=lambda t: ents[t]["ts"]):
    e = ents[tid]
    x = exts.get(tid)
    if not x: continue   # only closed
    sig = e.get("sig", {})
    edt = datetime.strptime(e["ts"],"%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    xdt = datetime.strptime(x["ts"],"%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    pip = PIP[e["pair"]]
    try:
        c = fetch_m1(e["pair"], iso(edt), iso(xdt+timedelta(seconds=1)))
        h = [float(b["mid"]["h"]) for b in c if "mid" in b]
        l = [float(b["mid"]["l"]) for b in c if "mid" in b]
        if e["dir"]=="long":
            mfe = (max(h)-e["entry"])/pip; mae = (min(l)-e["entry"])/pip
        else:
            mfe = (e["entry"]-min(l))/pip; mae = (e["entry"]-max(h))/pip
    except Exception: mfe=mae=0.0
    rows.append({"tid":tid,"pair":e["pair"],"dir":e["dir"],
                 "m_cert":sig.get("m_cert"),"d_cert":sig.get("d_cert"),
                 "dir_score":sig.get("dir_score"),"vortex":sig.get("vortex"),
                 "cpos":sig.get("cpos"),"realized":x["net"],
                 "mfe":round(mfe,2),"mae":round(mae,2),"abs_mae":round(abs(mae),2)})

print(f"Closed trades since {SINCE}: {len(rows)}\n")
print(f"{'tid':<5} {'pair':<8} {'dir':<5} {'m_cert':>7} {'d_cert':>7} {'dir_sc':>7} {'vortex':>7} {'cpos':>5} {'realized':>9} {'MFE':>6} {'MAE':>6} {'|MAE|':>5}")
for r in rows:
    def f(v,w,p=2): return f"{v:>{w}.{p}f}" if v is not None else f"{'':>{w}}"
    print(f"{r['tid']:<5} {r['pair']:<8} {r['dir']:<5} {f(r['m_cert'],7,3)} {f(r['d_cert'],7,3)} {f(r['dir_score'],7,3)} {f(r['vortex'],7,3)} {f(r['cpos'],5,2)} {r['realized']:>+8.2f}p {r['mfe']:>+5.1f}p {r['mae']:>+5.1f}p {r['abs_mae']:>5.1f}")

# Pearson correlation of each indicator with abs(MAE)
def corr(xs, ys):
    n = len(xs)
    if n < 3: return None
    mx, my = sum(xs)/n, sum(ys)/n
    num = sum((x-mx)*(y-my) for x,y in zip(xs,ys))
    dx = (sum((x-mx)**2 for x in xs))**0.5
    dy = (sum((y-my)**2 for y in ys))**0.5
    return num/(dx*dy) if dx>0 and dy>0 else None

abs_mae = [r["abs_mae"] for r in rows]
print(f"\n=== Correlation with abs(MAE) — n={len(rows)} ===")
for ind_name in ["m_cert","d_cert","dir_score","vortex","cpos","realized","mfe"]:
    vals = [r[ind_name] for r in rows]
    vals_filt = [(v,m) for v,m in zip(vals,abs_mae) if v is not None]
    if vals_filt:
        xs = [v for v,_ in vals_filt]; ys = [m for _,m in vals_filt]
        c = corr(xs, ys)
        print(f"  {ind_name:<12} corr={c:+.3f} (n={len(xs)})") if c is not None else None

# Per-pair correlations to see if mcert→MAE is universal or AUD_JPY-only
print(f"\n=== Per-pair mcert→abs(MAE) correlation ===")
from collections import defaultdict
by_pair = defaultdict(list)
for r in rows: by_pair[r["pair"]].append(r)
for pair, prs in sorted(by_pair.items()):
    if len(prs) >= 3:
        mc = [p["m_cert"] for p in prs if p["m_cert"] is not None]
        am = [p["abs_mae"] for p in prs if p["m_cert"] is not None]
        c = corr(mc, am)
        if c is not None:
            print(f"  {pair}: n={len(mc)}, corr={c:+.3f}, mean_mcert={sum(mc)/len(mc):.2f}, mean_|MAE|={sum(am)/len(am):.1f}p")

# Threshold test: if m_cert < 0.40, what's the avg |MAE| vs avg |MAE| when m_cert >= 0.40?
print(f"\n=== Threshold split: m_cert < 0.40 vs >= 0.40 (across all pairs) ===")
low = [r["abs_mae"] for r in rows if r["m_cert"] is not None and r["m_cert"] < 0.40]
hi  = [r["abs_mae"] for r in rows if r["m_cert"] is not None and r["m_cert"] >= 0.40]
if low: print(f"  m_cert <  0.40: n={len(low)}, mean |MAE|={sum(low)/len(low):.1f}p, max={max(low):.1f}p")
if hi:  print(f"  m_cert >= 0.40: n={len(hi)}, mean |MAE|={sum(hi)/len(hi):.1f}p, max={max(hi):.1f}p")

# Also check realized P/L by m_cert bucket
print(f"\n=== Realized P/L by m_cert bucket ===")
low_r = [r["realized"] for r in rows if r["m_cert"] is not None and r["m_cert"] < 0.40]
hi_r  = [r["realized"] for r in rows if r["m_cert"] is not None and r["m_cert"] >= 0.40]
if low_r: print(f"  m_cert <  0.40: n={len(low_r)}, mean={sum(low_r)/len(low_r):+.2f}p, wins={sum(1 for x in low_r if x>0)}/{len(low_r)} = {100*sum(1 for x in low_r if x>0)/len(low_r):.0f}%")
if hi_r:  print(f"  m_cert >= 0.40: n={len(hi_r)}, mean={sum(hi_r)/len(hi_r):+.2f}p, wins={sum(1 for x in hi_r if x>0)}/{len(hi_r)} = {100*sum(1 for x in hi_r if x>0)/len(hi_r):.0f}%")
