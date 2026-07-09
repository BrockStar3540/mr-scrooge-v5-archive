"""12-pair expansion corpus: 2026 M5/H1/D bars from OANDA -> features + forward
MFE/MAE targets (60/240m, both sides) -> ~/v5-truth-matrix-ext/{PAIR}_2026.parquet.
Formulas mirror v5_qtl_8yr_features.py (corpus-exact where features overlap)."""
import os, json, time, urllib.request
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import quantalib as qtl

env = {}
for line in open(os.path.expanduser("~/.openclaw/secrets.env")):
    line=line.strip()
    if line and not line.startswith("#") and "=" in line:
        k,v=line.split("=",1); env[k.strip()]=v.strip().strip('"').strip("'")
URL = env.get("OANDA_API_URL","https://api-fxpractice.oanda.com"); TOK = env["OANDA_API_TOKEN"]
H = {"Authorization": f"Bearer {TOK}"}
PAIRS = ["NZD_USD","EUR_GBP","GBP_JPY","CHF_JPY","EUR_CHF","GBP_CHF",
         "EUR_AUD","GBP_AUD","AUD_NZD","EUR_NZD","NZD_JPY","AUD_CHF"]
OUT = os.path.expanduser("~/v5-truth-matrix-ext"); os.makedirs(OUT, exist_ok=True)
pip_of = lambda p: 0.01 if p.endswith("JPY") else 0.0001

def fetch_all(pair, gran, start="2026-01-01T00:00:00Z"):
    rows = []; frm = start
    while True:
        u = f"{URL}/v3/instruments/{pair}/candles?granularity={gran}&from={frm}&count=5000&price=M"
        cs = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H))).get("candles", [])
        cs = [c for c in cs if c.get("complete")]
        if not cs: break
        for c in cs:
            m = c["mid"]
            rows.append((c["time"][:19], float(m["o"]), float(m["h"]), float(m["l"]), float(m["c"]), int(c["volume"])))
        nxt = cs[-1]["time"][:19] + "Z"
        if nxt == frm or len(cs) < 2: break
        frm = nxt
        if len(rows) > 90000: break
        time.sleep(0.1)
    df = pd.DataFrame(rows, columns=["time","open","high","low","close","volume"]).drop_duplicates("time")
    df["time"] = pd.to_datetime(df["time"])
    return df.set_index("time").sort_index()

def wilder_atr(h, l, c, n=14):
    pc = c.shift(1)
    tr = pd.concat([h-l, (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean()

for pair in PAIRS:
    try:
        t0 = time.time()
        m5 = fetch_all(pair, "M5"); h1 = fetch_all(pair, "H1"); d = fetch_all(pair, "D", "2025-09-01T00:00:00Z")
        pip = pip_of(pair)
        f = pd.DataFrame(index=m5.index)
        f["close"] = m5["close"]
        f["atr_5m"] = wilder_atr(m5["high"], m5["low"], m5["close"]) / pip
        f["rvol_5bar"] = m5["volume"].rolling(5).mean() / m5["volume"].rolling(32).mean()
        try:
            f["q_willr_m5"] = qtl.willr(m5["high"], m5["low"], m5["close"], period=14)
        except Exception:
            hh, ll = m5["high"].rolling(14).max(), m5["low"].rolling(14).min()
            f["q_willr_m5"] = -100*(hh-m5["close"])/(hh-ll+1e-10)
        try:
            kc = qtl.kchannel(m5["high"], m5["low"], m5["close"], period=20, multiplier=2.0)
            f["q_kc_up_dist_pips"] = (m5["close"] - kc["upper"]) / pip
        except Exception:
            e20 = m5["close"].ewm(span=20, adjust=False).mean()
            f["q_kc_up_dist_pips"] = (m5["close"] - (e20 + 2*wilder_atr(m5["high"],m5["low"],m5["close"],20))) / pip
        a1 = wilder_atr(h1["high"], h1["low"], h1["close"], 14) / pip
        a100 = wilder_atr(h1["high"], h1["low"], h1["close"], 100) / pip
        hh1 = pd.DataFrame({"atr_1h": a1, "atr_h1_relative": a1/(a100+1e-12)}, index=h1.index)
        f = pd.merge_asof(f.sort_index(), hh1.sort_index(), left_index=True, right_index=True)
        f["atr_conc"] = f["atr_5m"] / (f["atr_1h"] + 1e-12)
        dd = pd.DataFrame({"pdh": d["high"].shift(1), "pdl": d["low"].shift(1),
                           "htf_pct_20": d["close"].pct_change(20), "htf_pct_60": d["close"].pct_change(60)}, index=d.index)
        f = pd.merge_asof(f, dd.sort_index(), left_index=True, right_index=True)
        f["pdh_dist"] = (f["close"] - f["pdh"]) / pip
        f["pdl_dist"] = (f["close"] - f["pdl"]) / pip
        # forward excursions: next 12 (60m) and 48 (240m) bars
        for hz, k in (("60", 12), ("240", 48)):
            fmax = m5["high"].shift(-1).rolling(k, min_periods=k).max().shift(-(k-1))
            fmin = m5["low"].shift(-1).rolling(k, min_periods=k).min().shift(-(k-1))
            f[f"mfe_long_{hz}"]  = (fmax - m5["close"]) / pip
            f[f"mae_long_{hz}"]  = (m5["close"] - fmin) / pip
            f[f"mfe_short_{hz}"] = (m5["close"] - fmin) / pip
            f[f"mae_short_{hz}"] = (fmax - m5["close"]) / pip
        f.to_parquet(f"{OUT}/{pair}_2026.parquet")
        print(f"{pair}: {len(f)} bars, {time.time()-t0:.0f}s", flush=True)
    except Exception as e:
        print(f"{pair}: FAILED {e}", flush=True)
print("EXT CORPUS BUILD DONE", flush=True)
