"""BROKER validation: for each trade, compute indicators at entry from FRESH
OANDA candles, then measure actual 1H forward pip move. Test: do the matrix's
per-cell relationships hold up against real broker data?

Runs on Mini. Uses qtl for all indicator computation.
"""
import json, os, subprocess, time
from pathlib import Path
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd
import quantalib as qtl

def assert_on_mini():
    s = subprocess.run(["system_profiler","SPHardwareDataType"], capture_output=True, text=True).stdout
    if "CPYQTH294R" not in s: raise RuntimeError("NOT ON MINI")
    print("✓ device verified: Mini CPYQTH294R")
assert_on_mini()

ROOT = Path.home() / "qtl-discovery-8yr"
BUNDLE = Path("/Users/brock-mini-mac/qtl-discovery-8yr/v5_trade_candles_bundle.json")
OUT = ROOT / "broker_validation"
OUT.mkdir(exist_ok=True)

PIP = {"AUD_JPY":0.01,"EUR_JPY":0.01,"USD_JPY":0.01,
       "AUD_USD":0.0001,"EUR_USD":0.0001,"GBP_USD":0.0001,
       "USD_CAD":0.0001,"USD_CHF":0.0001}

bundle = json.loads(BUNDLE.read_text())
print(f"loaded bundle: {len(bundle['trades'])} trades")

def candles_to_df(rows):
    if not rows: return None
    df = pd.DataFrame(rows, columns=["time","open","high","low","close","volume"])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.set_index("time").sort_index()
    for c in ["open","high","low","close","volume"]:
        df[c] = df[c].astype(float)
    return df

def compute_indicators_at_bar(m5, h1, pair):
    """Compute the indicators at the LAST bar of m5 (which is the entry bar).
       h1 is aligned via ffill to m5 resolution. Returns a dict of features."""
    pip = PIP[pair]
    o, h, l, c, v = m5["open"], m5["high"], m5["low"], m5["close"], m5["volume"]
    f = {}

    # V5 baseline subset
    def safe_last(x):
        try:
            arr = np.asarray(x); v = float(arr[-1])
            return v if not np.isnan(v) else None
        except Exception: return None

    f["atr_5m"]   = safe_last(qtl.atr(o, h, l, c, v, period=14)) / pip if pip else None
    f["rsi14"]    = safe_last(qtl.rsi(c, period=14))
    f["bb_pos"]   = None
    bb = qtl.bbands(c, period=20, std=2.0)
    if isinstance(bb, pd.DataFrame):
        cols = list(bb.columns)
        u = next((cc for cc in cols if "u" in cc.lower()), cols[0])
        lo = next((cc for cc in cols if "l" in cc.lower() and cc != u), cols[-1])
        u_v = bb[u].iloc[-1]; l_v = bb[lo].iloc[-1]
        if u_v != l_v: f["bb_pos"] = float((c.iloc[-1] - l_v) / (u_v - l_v))

    # qtl candidate indicators
    f["q_willr_m5"]  = safe_last(qtl.willr(h, l, c, period=14))
    f["q_cci_m5"]    = safe_last(qtl.cci(o, h, l, c, v, period=20))
    f["q_fisher_m5"] = safe_last(qtl.fisher(c, period=10))
    f["q_tsi_m5"]    = safe_last(qtl.tsi(c, longPeriod=25, shortPeriod=13))
    f["q_macd_m5"]   = safe_last(qtl.macd(c, fastPeriod=12, slowPeriod=26, signalPeriod=9))
    f["q_stochrsi_m5"] = safe_last(qtl.stochrsi(c, period=14))
    f["q_obv"]       = safe_last(qtl.obv(c, v))
    f["q_cmf"]       = safe_last(qtl.cmf(h, l, c, v, period=20))
    f["q_mfi"]       = safe_last(qtl.mfi(h, l, c, v, period=14))
    f["q_efi"]       = safe_last(qtl.efi(c, v, period=13))
    f["q_adosc"]     = safe_last(qtl.adosc(h, l, c, v))
    f["q_bbwp_m5"]   = safe_last(qtl.bbwp(c, period=20, lookback=100))
    f["q_atrn_m5"]   = safe_last(qtl.atrn(o, h, l, c, v, period=14))
    f["q_hurst_m5"]  = safe_last(qtl.hurst(c, period=100))
    f["q_kurtosis_m5"] = safe_last(qtl.kurtosis(c, period=100))
    f["q_skew_m5"]   = safe_last(qtl.skew(c, period=100))
    f["q_ht_dcphase_m5"] = safe_last(qtl.ht_dcphase(c))
    f["q_ebsw_m5"]   = safe_last(qtl.ebsw(c))

    # Channels
    dc = qtl.dchannel(h, l, period=20)
    if isinstance(dc, pd.DataFrame) and "upper" in dc.columns:
        f["q_dc_up_dist_pips"] = float((c.iloc[-1] - dc["upper"].iloc[-1]) / pip)
        f["q_dc_lo_dist_pips"] = float((c.iloc[-1] - dc["lower"].iloc[-1]) / pip)
    kc = qtl.kchannel(h, l, c, period=20, multiplier=2.0)
    if isinstance(kc, pd.DataFrame) and "upper" in kc.columns:
        f["q_kc_up_dist_pips"] = float((c.iloc[-1] - kc["upper"].iloc[-1]) / pip)

    # H1 features
    if h1 is not None and len(h1) >= 50:
        h1o, h1h, h1l, h1c, h1v = h1["open"], h1["high"], h1["low"], h1["close"], h1["volume"]
        f["q_chop_h1"]      = safe_last(qtl.chop(h1o, h1h, h1l, h1c, h1v, period=14))
        f["q_aroonosc_h1"]  = safe_last(qtl.aroonosc(h1h, h1l, period=14))
        f["q_vhf_h1"]       = safe_last(qtl.vhf(h1c, period=28))
        f["q_adx_h1"]       = safe_last(qtl.adx(h1h, h1l, h1c, period=14))
        vrtx = qtl.vortex(h1h, h1l, h1c, period=14)
        if isinstance(vrtx, pd.DataFrame) and "viPlus" in vrtx.columns:
            f["q_vortex_diff_h1"] = float(vrtx["viPlus"].iloc[-1] - vrtx["viMinus"].iloc[-1])
        st = qtl.supertrend(h1o, h1h, h1l, h1c, h1v, period=10, multiplier=3.0)
        if st is not None:
            f["q_super_dist_h1"] = float((h1c.iloc[-1] - st.iloc[-1]) / pip)
        # rsi14 H1
        f["rsi14_h1"] = safe_last(qtl.rsi(h1c, period=14))
        f["h1_ret_1bar"] = float((h1c.iloc[-1] - h1c.iloc[-2]) / pip) if len(h1c) >= 2 else None
        f["h1_ret_4bar"] = float((h1c.iloc[-1] - h1c.iloc[-5]) / pip) if len(h1c) >= 5 else None
    return f

# ── Process each trade ──────────────────────────────────────────────────────
print(f"\nProcessing {len(bundle['trades'])} trades...")
rows = []
for i, t in enumerate(bundle["trades"]):
    tid = t["trade_id"]; pair = t["pair"]
    cands = bundle["candles"].get(tid, {})
    m5 = candles_to_df(cands.get("m5"))
    h1 = candles_to_df(cands.get("h1"))
    if m5 is None or len(m5) < 200:
        continue
    # Locate entry bar
    entry_ts = pd.Timestamp(t["open_time_iso"])
    if entry_ts.tz is None: entry_ts = entry_ts.tz_localize("UTC")
    # Use bars up to (and including) entry
    m5_pre = m5[m5.index <= entry_ts]
    if len(m5_pre) < 200: continue
    feats = compute_indicators_at_bar(m5_pre, h1[h1.index <= entry_ts] if h1 is not None else None, pair)
    # Forward 1H pip move (next 12 M5 bars)
    m5_post = m5[m5.index > entry_ts]
    if len(m5_post) < 12:
        forward_pip = None
    else:
        bar0_close = m5_pre["close"].iloc[-1]
        bar12_close = m5_post["close"].iloc[11]   # 12th bar after entry
        pip = PIP[pair]
        forward_pip = (bar12_close - bar0_close) / pip
    side_sign = 1 if t["side"]=="long" else -1
    forward_pip_signed = forward_pip * side_sign if forward_pip is not None else None
    rows.append({
        "trade_id": tid, "pair": pair, "side": t["side"], "session": t["session"],
        "open_time_iso": t["open_time_iso"],
        "realized_pl_usd": t["realized_pl_usd"],
        "exit_class": t["exit_class"],
        "forward_1h_pip": forward_pip,
        "forward_1h_pip_signed": forward_pip_signed,
        "win_realized": int(t["realized_pl_usd"] > 0),
        "win_forward1h": int(forward_pip_signed > 0) if forward_pip_signed is not None else None,
        **feats,
    })
    if (i+1) % 25 == 0: print(f"  processed {i+1}/{len(bundle['trades'])}")

df = pd.DataFrame(rows)
df.to_csv(OUT / "trades_broker_validated.csv", index=False)
print(f"\n→ {OUT / 'trades_broker_validated.csv'} ({len(df)} trades, {len(df.columns)} cols)")

# ── Per-cell × feature × forward-1h-pip correlation ─────────────────────────
print(f"\n=== PER-CELL: does each indicator at entry predict the actual 1H forward pip move? ===")
bot = df[(df['exit_class']=='BOT_EXIT') & df['forward_1h_pip_signed'].notna()].copy()
print(f"bot-exit + valid forward window: {len(bot)} trades")
feature_cols = [c for c in df.columns if c.startswith('q_') or c in
                ('atr_5m','rsi14','bb_pos','rsi14_h1','h1_ret_1bar','h1_ret_4bar')]

print(f"\n=== Per-cell n>=4: top |corr(feature, forward_1h_pip_signed)| ===")
results = []
for (pair, sess, side), g in bot.groupby(['pair','session','side']):
    if len(g) < 4: continue
    for f in feature_cols:
        if f not in g.columns: continue
        valid = g[[f, 'forward_1h_pip_signed']].dropna()
        if len(valid) < 4: continue
        corr = valid[f].corr(valid['forward_1h_pip_signed'])
        if pd.isna(corr): continue
        results.append({
            "pair": pair, "session": sess, "side": side, "n": len(g),
            "feature": f, "corr_fwd_pip": round(corr, 3),
            "mean_fwd_pip": round(valid['forward_1h_pip_signed'].mean(), 2),
        })
res = pd.DataFrame(results)
res.to_csv(OUT / "per_cell_feature_vs_forward1h.csv", index=False)
# Show top |corr| per cell
print(f"\nTop |corr| per cell (cells with n>=4 trades):")
top_per_cell = res.loc[res.groupby(['pair','session','side'])['corr_fwd_pip'].transform(lambda x: x.abs().rank(ascending=False) <= 3).astype(bool)]
top_per_cell = top_per_cell.sort_values(['pair','session','side','corr_fwd_pip'], key=lambda s: s.abs() if s.name=='corr_fwd_pip' else s, ascending=[True,True,True,False])
print(top_per_cell.to_string(index=False))

# Also overall: does V5's REALIZED win match the 1H-forward direction?
print(f"\n=== Realized-P/L direction vs 1H-forward direction agreement ===")
match = (df['win_realized'] == df['win_forward1h']).sum()
print(f"Trades where realized win/loss matches 1H forward direction: {match}/{len(df)} ({match/len(df)*100:.0f}%)")
print(f"V5 ratchet+manual exits often differ from 1H forward (cuts trades short or holds losers)")
