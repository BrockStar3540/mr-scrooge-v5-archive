"""Test the V4-era 'coarse-factor bucket' claims against the 8yr corpus,
using 1H FORWARD PIP as the outcome (market truth, not realized P/L).

Claims under test:
  C1 SESSION x ALIGN: EV climbs a0->a4 in most sessions but INVERTS in off-hours
     (and is flat in ny_close). [old notes]
  C2 RSI x ALIGN: RSI extremes only pay when aligned (RSI0 a0:-1.09 -> a4:+4.48).
  C3 ALIGN x ADR x RSI coarse bucket separates hard; dropping negative buckets
     lifts the average. OOS: build map on 2019-2023, test on 2024-2026.

ALIGN = # of HTF factors {htf_pct_20, htf_pct_60, trend_4h, d_ret} whose sign
        matches the signal direction d = sign(h1_ret_1bar). Range 0..4.
Outcome = d * fwd_60m (forward pip in the signal direction).
"""
import os, subprocess, time
from pathlib import Path
import numpy as np
import pandas as pd
from joblib import Parallel, delayed

def assert_on_mini():
    s = subprocess.run(["system_profiler","SPHardwareDataType"], capture_output=True, text=True).stdout
    if "CPYQTH294R" not in s: raise RuntimeError("NOT ON MINI")
    print("✓ device verified: Mini CPYQTH294R")
assert_on_mini()

ROOT = Path.home() / "qtl-discovery-8yr"
FEAT = ROOT / "features"
OUT = ROOT / "bucket_test"; OUT.mkdir(exist_ok=True)
PAIRS = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
N_JOBS = 8
SPLIT = pd.Timestamp('2024-01-01', tz='UTC')

def fine_session(h):
    if h in (22,23,0,1): return 'asia'
    if h in (2,3,4,5):   return 'asia_late'
    if h in (6,7,8):     return 'london_open'
    if h in (9,10,11,12):return 'london'
    if h in (13,14,15):  return 'ny_open'
    if h in (16,17,18):  return 'ny_mid'
    if h in (19,20,21):  return 'ny_close'
    return 'off'

def process_pair(pair):
    df = pd.read_parquet(FEAT / f"{pair}_features.parquet")
    need = ['h1_ret_1bar','htf_pct_20','htf_pct_60','trend_4h','d_ret','adr_consumed','rsi14','fwd_ret_pips']
    df = df[[c for c in need if c in df.columns]].copy()
    df = df.replace([np.inf,-np.inf], np.nan).dropna()
    d = np.sign(df['h1_ret_1bar']); d = d.replace(0, 1)
    # ALIGN: HTF factor agreement with signal direction
    align = ((np.sign(df['htf_pct_20'])==d).astype(int)
             + (np.sign(df['htf_pct_60'])==d).astype(int)
             + (np.sign(df['trend_4h'])==d).astype(int)
             + (np.sign(df['d_ret'])==d).astype(int))
    df['align'] = align
    df['dir'] = d
    df['outcome'] = d * df['fwd_ret_pips']     # forward pip in signal direction
    df['session'] = [fine_session(h) for h in df.index.hour]
    # RSI relative to direction: for a long signal high rsi is "extreme aligned"
    df['rsi_dir'] = np.where(d>0, df['rsi14'], 100-df['rsi14'])
    df['is_test'] = df.index >= SPLIT
    # ADR group (lo/hi by 0.65 of typical ~ use median split per pair)
    adr_med = df['adr_consumed'].median()
    df['adr_grp'] = np.where(df['adr_consumed']>=adr_med, 'ADRhi', 'ADRlo')
    # RSI group: mid (40-60 on rsi_dir) vs extreme
    df['rsi_grp'] = np.where(df['rsi_dir'].between(40,60), 'RSImid',
                     np.where(df['rsi_dir']>60, 'RSIhi', 'RSIlo'))
    df['pair'] = pair
    return df[['pair','session','align','dir','outcome','rsi_dir','adr_grp','rsi_grp','is_test','adr_consumed','rsi14']]

if __name__ == '__main__':
    print("Bucket test — V4-era claims on 8yr forward pip")
    t0=time.time()
    res = Parallel(n_jobs=N_JOBS, verbose=5)(delayed(process_pair)(p) for p in PAIRS)
    alld = pd.concat(res, ignore_index=True)
    print(f"compute {time.time()-t0:.1f}s, {len(alld):,} bars")

    # ── C1: SESSION x ALIGN (mean forward outcome) ──
    print(f"\n=== C1: SESSION × ALIGN — mean forward pip in signal direction (pooled all pairs) ===")
    sa = alld.pivot_table(index='session', columns='align', values='outcome', aggfunc='mean').round(2)
    order = ['asia','asia_late','london_open','london','ny_open','ny_mid','ny_close','off']
    sa = sa.reindex([s for s in order if s in sa.index])
    print(sa.to_string())
    # trend per session: does it climb a0->a4?
    print(f"\n  per-session a0->a4 slope (a4 - a0): + = align helps, - = align INVERTS")
    for s in sa.index:
        a0 = sa.loc[s].get(0, np.nan); a4 = sa.loc[s].get(4, np.nan)
        if not (np.isnan(a0) or np.isnan(a4)):
            tag = 'climbs' if a4>a0+0.3 else ('INVERTS' if a4<a0-0.3 else 'flat')
            print(f"    {s:<12} a0={a0:+.2f} a4={a4:+.2f}  Δ={a4-a0:+.2f}  {tag}")

    # ── C2: RSI × ALIGN interaction ──
    print(f"\n=== C2: RSI(dir) × ALIGN — do RSI extremes only pay when aligned? (mean fwd pip) ===")
    alld['rsi_bucket'] = pd.cut(alld['rsi_dir'], [0,30,45,55,70,100], labels=['rsi_lo','rsi_mlo','rsi_mid','rsi_mhi','rsi_hi'])
    ra = alld.pivot_table(index='rsi_bucket', columns='align', values='outcome', aggfunc='mean', observed=True).round(2)
    print(ra.to_string())

    # ── C3: coarse ALIGN×ADR×RSI bucket, OOS drop-negative ──
    print(f"\n=== C3: ALIGN × ADR × RSI coarse bucket — OOS drop-negative lift, per pair ===")
    alld['bucket'] = (alld['align'].astype(str) + '|' + alld['adr_grp'] + '|' + alld['rsi_grp'])
    results = []
    for pair, g in alld.groupby('pair'):
        tr = g[~g['is_test']]; te = g[g['is_test']]
        # build map on train: bucket mean outcome
        bmap = tr.groupby('bucket')['outcome'].agg(['mean','count'])
        keep = set(bmap[(bmap['mean']>0) & (bmap['count']>=200)].index)  # positive buckets, min sample
        # apply to test
        te_keep = te[te['bucket'].isin(keep)]
        te_drop = te[~te['bucket'].isin(keep)]
        base = te['outcome'].mean()
        kept = te_keep['outcome'].mean() if len(te_keep) else np.nan
        dropped = te_drop['outcome'].mean() if len(te_drop) else np.nan
        results.append({'pair':pair,'test_n':len(te),'base_fwd':round(base,3),
                        'keep_n':len(te_keep),'keep_fwd':round(kept,3),
                        'drop_n':len(te_drop),'drop_fwd':round(dropped,3),
                        'lift':round(kept-base,3) if not np.isnan(kept) else None,
                        'n_buckets_kept':len(keep)})
    rdf = pd.DataFrame(results)
    print(rdf.to_string(index=False))
    print(f"\n  OOS lift (keep-fwd minus base-fwd) > 0 in {(rdf['lift']>0).sum()}/8 pairs")
    print(f"  Mean OOS base fwd: {rdf['base_fwd'].mean():+.3f}p  |  Mean OOS keep fwd: {rdf['keep_fwd'].mean():+.3f}p")

    alld.drop(columns=['rsi14','adr_consumed']).to_parquet(OUT/'bucket_bars.parquet')
    sa.to_csv(OUT/'session_x_align.csv'); ra.to_csv(OUT/'rsi_x_align.csv'); rdf.to_csv(OUT/'oos_bucket_lift.csv', index=False)
    print(f"\n→ {OUT}/ : session_x_align.csv, rsi_x_align.csv, oos_bucket_lift.csv")
