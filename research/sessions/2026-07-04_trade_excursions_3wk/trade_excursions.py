#!/usr/bin/env python3
"""Broker-truth MAE/MFE excursion table — trades since 2026-06-13, cell-lens.

Session 2026-07-04. Lineage: reuses fetch pattern of ~/v5-mfe-study/mfe_study.py;
feature formulas match ~/qtl-discovery-8yr/v5_qtl_8yr_features.py (corpus-exact).
Output: ~/v5-trade-excursions/{excursions.csv, REPORT.md}
"""
import os, json, time, subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd
import requests
import quantalib as qtl

s = subprocess.run(["system_profiler","SPHardwareDataType"], capture_output=True, text=True).stdout
if "CPYQTH294R" not in s: raise RuntimeError("NOT ON MINI")
print("device OK: Mini")

OUT = Path.home() / "v5-trade-excursions"
OUT.mkdir(exist_ok=True)
CELL_BOOK = json.loads((OUT / "cell_book.json").read_text())

creds = {}
for line in open(Path.home() / "mr-scrooge-v4-replay" / ".env"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); creds[k.strip()] = v.strip().strip('"').strip("'")
BASE  = creds.get("OANDA_API_URL", "https://api-fxpractice.oanda.com").rstrip("/")
TOKEN = creds["OANDA_API_TOKEN"]; ACCT = creds["OANDA_ACCOUNT_ID"]
H = {"Authorization": f"Bearer {TOKEN}", "Accept-Datetime-Format": "RFC3339"}

FROM_DT   = datetime(2026, 6, 13, 0, 0, tzinfo=timezone.utc)
CUT_V5    = datetime(2026, 6, 18, 0, 0, tzinfo=timezone.utc)
CUT_CELL  = datetime(2026, 7, 4, 7, 50, tzinfo=timezone.utc)
PAIRS = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
JPY = {"AUD_JPY","EUR_JPY","USD_JPY"}
pip_of = lambda p: 0.01 if p in JPY else 0.0001
def sess_of(h):
    return "london" if 7 <= h < 13 else ("ny" if 13 <= h < 22 else "asia")
def era_of(t):
    return "v4" if t < CUT_V5 else ("v5leg" if t < CUT_CELL else "cell_v1")

def get(url, **params):
    for i in range(3):
        r = requests.get(url, headers=H, params=params, timeout=30)
        if r.status_code == 200: return r.json()
        time.sleep(1 + i)
    r.raise_for_status()

def candles_df(raw):
    rows = [{"time": datetime.fromisoformat(c["time"].replace("Z","+00:00")),
             "o": float(c["mid"]["o"]), "h": float(c["mid"]["h"]),
             "l": float(c["mid"]["l"]), "c": float(c["mid"]["c"]),
             "v": int(c.get("volume",0))} for c in raw.get("candles", []) if c.get("mid")]
    df = pd.DataFrame(rows)
    return df.set_index("time") if len(df) else df

def fetch_between(pair, f, t, gran):
    return candles_df(get(f"{BASE}/v3/instruments/{pair}/candles", granularity=gran,
        price="M", **{"from": f.strftime("%Y-%m-%dT%H:%M:%SZ"), "to": t.strftime("%Y-%m-%dT%H:%M:%SZ")}))

def fetch_count(pair, to, n, gran):
    return candles_df(get(f"{BASE}/v3/instruments/{pair}/candles", granularity=gran,
        price="M", count=n, to=to.strftime("%Y-%m-%dT%H:%M:%SZ")))

def wilder_atr(df, n=14):
    pc = df["c"].shift(1)
    tr = pd.concat([df["h"]-df["l"], (df["h"]-pc).abs(), (df["l"]-pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean()

# ── trades ──────────────────────────────────────────────────────────────────
trades = []
for pair in PAIRS:
    for t in get(f"{BASE}/v3/accounts/{ACCT}/trades", instrument=pair, state="CLOSED", count=500).get("trades", []):
        ot = datetime.fromisoformat(t["openTime"].replace("Z","+00:00"))
        if ot < FROM_DT: continue
        ct = datetime.fromisoformat(t["closeTime"].replace("Z","+00:00"))
        units = int(float(t["initialUnits"])); pm = pip_of(pair)
        pe, px = float(t["price"]), float(t.get("averageClosePrice", 0))
        d = "long" if units > 0 else "short"
        real = (px-pe)/pm if d == "long" else (pe-px)/pm
        trades.append(dict(id=t["id"], pair=pair, open=ot, close=ct, dir=d,
            units=abs(units), real_pips=round(real,2), real_usd=float(t.get("realizedPL",0)),
            entry=pe, sess=sess_of(ot.hour), era=era_of(ot),
            dur_min=round((ct-ot).total_seconds()/60)))
print(f"trades since {FROM_DT.date()}: {len(trades)}")

# ── excursions + features ───────────────────────────────────────────────────
recs = []
for i, tr in enumerate(sorted(trades, key=lambda x: x["open"])):
    pair, pm = tr["pair"], pip_of(tr["pair"])
    try:
        gran = "M1" if tr["dur_min"] <= 2880 else "M5"
        pad = timedelta(minutes=2 if gran == "M1" else 6)
        path = fetch_between(pair, tr["open"]-pad, tr["close"]+pad, gran)
        if len(path):
            path = path[path.index >= tr["open"] - pad]
            seg = path[(path.index >= tr["open"] - pad) & (path.index <= tr["close"] + pad)]
            if tr["dir"] == "long":
                mfe = (seg["h"].max() - tr["entry"]) / pm; mae = (tr["entry"] - seg["l"].min()) / pm
            else:
                mfe = (tr["entry"] - seg["l"].min()) / pm; mae = (seg["h"].max() - tr["entry"]) / pm
            tr["mfe"], tr["mae"] = round(max(mfe,0),1), round(max(mae,0),1)
        else:
            tr["mfe"] = tr["mae"] = None
        m5 = fetch_count(pair, tr["open"], 400, "M5")
        h1 = fetch_count(pair, tr["open"], 120, "H1")
        f = {}
        if len(m5) >= 50:
            m5 = m5[m5.index <= tr["open"]]
            f["atr_5m"]    = float(wilder_atr(m5).iloc[-1]) / pm
            f["rvol_5bar"] = float((m5["v"].rolling(5).mean() / m5["v"].rolling(32).mean()).iloc[-1])
            try:    f["willr_m5"] = float(qtl.willr(m5["h"], m5["l"], m5["c"], period=14).iloc[-1])
            except Exception:
                hh, ll = m5["h"].rolling(14).max(), m5["l"].rolling(14).min()
                f["willr_m5"] = float((-100*(hh-m5["c"])/(hh-ll+1e-10)).iloc[-1])
            try:
                kc = qtl.kchannel(m5["h"], m5["l"], m5["c"], period=20, multiplier=2.0)
                f["kc_up_dist_pips"] = float((m5["c"].iloc[-1] - kc["upper"].iloc[-1]) / pm)
            except Exception: f["kc_up_dist_pips"] = None
        if len(h1) >= 100:
            h1 = h1[h1.index <= tr["open"]]
            a14 = wilder_atr(h1, 14); a100 = wilder_atr(h1, 100)
            f["atr_h1_relative"] = float(a14.iloc[-1] / (a100.iloc[-1] + 1e-12))
            if f.get("atr_5m"): f["atr_conc"] = f["atr_5m"] / (float(a14.iloc[-1])/pm + 1e-12)
        tr.update({k: (round(v,3) if isinstance(v,float) else v) for k,v in f.items()})
        recs.append(tr)
        if (i+1) % 25 == 0: print(f"  {i+1}/{len(trades)}", flush=True)
        time.sleep(0.05)
    except Exception as e:
        tr["err"] = str(e)[:80]; recs.append(tr)

df = pd.DataFrame(recs)
df.to_csv(OUT / "excursions.csv", index=False)

# ── report ──────────────────────────────────────────────────────────────────
FEATS = ["atr_5m","kc_up_dist_pips","atr_conc","rvol_5bar","willr_m5","atr_h1_relative"]
def fmt_dur(m):
    if m is None or pd.isna(m): return "?"
    m = int(m); return f"{m//1440}d{(m%1440)//60:02d}h" if m >= 1440 else (f"{m//60}h{m%60:02d}" if m >= 60 else f"{m}m")
L = ["# Broker-Truth MAE/MFE — trades since 2026-06-13 (cell lens)\n",
     f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%MZ')} · {len(df)} trades · MAE/MFE from "
     "M1 path (M5 if >2d) vs entry fill · features at entry bar, corpus-exact formulas · "
     "eras: v4 (<06-18), v5leg (<07-04 07:50Z), cell_v1\n"]
for pair in PAIRS:
    for sess in ("asia","london","ny"):
        g = df[(df["pair"]==pair) & (df["sess"]==sess)]
        if not len(g): continue
        cb = CELL_BOOK.get(f"{pair}|{sess}", {})
        setups = cb.get("setups", [])
        active_sides = {st["side"] for st in setups if st.get("status")=="ACTIVE"}
        shead = "; ".join(f"{st['id']}({st['side']},{st['status']}: {','.join(x for x in st['features'] if x)})" for st in setups) or cb.get("note","no setups")
        L.append(f"\n## {pair} / {sess} — n={len(g)}, WR {100*(g['real_pips']>0).mean():.0f}%, "
                 f"med MAE {g['mae'].median():.1f} / MFE {g['mfe'].median():.1f} / real {g['real_pips'].median():+.1f}p")
        L.append(f"**Cell now:** {shead}\n")
        L.append("| MAE | MFE | real | out | dur | dir✓ | era | date | " + " | ".join(FEATS) + " |")
        L.append("|" + "---|"*(8+len(FEATS)))
        for _, r in g.sort_values("mae", ascending=False).iterrows():
            match = "—" if not active_sides else ("✓" if r["dir"] in active_sides else "✗")
            fv = " | ".join("" if k not in r or pd.isna(r[k]) else f"{r[k]:.2f}" for k in FEATS)
            L.append(f"| {r['mae']:.1f} | {r['mfe']:.1f} | {r['real_pips']:+.1f} | {'W' if r['real_pips']>0 else 'L'} "
                     f"| {fmt_dur(r['dur_min'])} | {r['dir'][0].upper()}{match} | {r['era']} "
                     f"| {r['open'].strftime('%m-%d %H:%M')} | {fv} |")
(OUT / "REPORT.md").write_text("\n".join(L))
print(f"done: {len(df)} trades -> {OUT}/excursions.csv + REPORT.md")
