"""Is ALIGN 0-4 too narrow across the 48 cells?

Tests two axes of "narrow":
  (A) too few LEVELS — compare 0-4 count vs 0-8 count vs continuous weighted score
  (B) too few FACTORS — 4 HTF factors vs an 8-factor basis (more timeframes)

Per (pair x session x direction) = 48 cells, reference direction = cell direction
(long=+1, short=-1). fwd_dir = dir * fwd_60m. ALIGN measured relative to dir.

Metric per cell: Spearman corr of each align variant with fwd_dir + monotonic
mean-fwd ladder + population at each level (are the extremes even populated?).

8-factor HTF basis (signed, >0 bullish):
  daily returns: 5d, 10d, 20d, 60d, 120d   (5)
  trend:         1h, 4h, 24h                (3)
align4  = {ret20d, ret60d, trend4h, trend24h}  (the original ~4)
align8  = all 8
align_c = z-scored signed sum of all 8 (continuous)
"""
import os, subprocess, time
from pathlib import Path
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import spearmanr

def assert_on_mini():
    s = subprocess.run(["system_profiler","SPHardwareDataType"], capture_output=True, text=True).stdout
    if "CPYQTH294R" not in s: raise RuntimeError("NOT ON MINI")
    print("✓ device verified: Mini CPYQTH294R")
assert_on_mini()

ROOT = Path.home() / "qtl-discovery-8yr"
RAW = Path("/Volumes/Alien Device/direction_ml/raw_bars")
OUT = ROOT / "align_resolution"; OUT.mkdir(exist_ok=True)
PAIRS = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
PIP = {"AUD_JPY":0.01,"EUR_JPY":0.01,"USD_JPY":0.01,"AUD_USD":0.0001,
       "EUR_USD":0.0001,"GBP_USD":0.0001,"USD_CAD":0.0001,"USD_CHF":0.0001}
N_JOBS = 8; FWD_BARS = 12
def resample(m5, rule):
    return m5.resample(rule, label='right', closed='right').agg(
        {'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna()
def session(h):
    if 22<=h or h<=5: return 'asia'
    if 6<=h<=12: return 'london'
    if 13<=h<=14: return 'overlap'
    return 'ny'

def process_pair(pair):
    pip = PIP[pair]
    m5 = pd.read_parquet(RAW / f"{pair}_M5.parquet")
    close = m5['close'].astype(float)
    fwd = (close.shift(-FWD_BARS) - close) / pip
    d1 = resample(m5, '1D'); h1 = resample(m5, '1h')
    dc = d1['close']
    htf = {
        'ret5d':  (dc/dc.shift(5)-1),  'ret10d': (dc/dc.shift(10)-1),
        'ret20d': (dc/dc.shift(20)-1), 'ret60d': (dc/dc.shift(60)-1),
        'ret120d':(dc/dc.shift(120)-1),
    }
    hc = h1['close']
    htf['trend1h']  = (hc - hc.shift(1))
    htf['trend4h']  = (hc - hc.shift(4))
    htf['trend24h'] = (hc - hc.shift(24))
    # align to m5 timeline
    H = pd.DataFrame({k: v.reindex(m5.index, method='ffill') for k,v in htf.items()})
    sess = pd.Series([session(h) for h in m5.index.hour], index=m5.index)

    F4 = ['ret20d','ret60d','trend4h','trend24h']
    F8 = list(htf.keys())
    # z-score each factor (for continuous)
    Hz = (H - H.mean()) / H.replace(0,np.nan).std()

    rows = []
    for direction in ['long','short']:
        dsign = 1 if direction=='long' else -1
        fwd_dir = dsign * fwd
        # alignment = count of HTF factors whose sign matches dsign
        sgn = np.sign(H)
        align4 = (sgn[F4]==dsign).sum(axis=1)
        align8 = (sgn[F8]==dsign).sum(axis=1)
        align_c = (Hz * dsign).sum(axis=1)   # continuous: signed z-sum in cell direction
        base = pd.DataFrame({'fwd_dir':fwd_dir,'a4':align4,'a8':align8,'ac':align_c,'sess':sess}).dropna()
        for s, g in base.groupby('sess'):
            if len(g) < 5000: continue
            # spearman corr of each align variant with forward
            c4 = spearmanr(g['a4'], g['fwd_dir']).correlation
            c8 = spearmanr(g['a8'], g['fwd_dir']).correlation
            cc = spearmanr(g['ac'], g['fwd_dir']).correlation
            # population at each align4 level + extreme sparsity
            pop = g['a4'].value_counts().to_dict()
            n_a0 = pop.get(0,0); n_a4 = pop.get(4,0)
            # mean fwd at a4-extremes
            rows.append({'pair':pair,'session':s,'direction':direction,'n':len(g),
                         'corr_a4':round(c4,4),'corr_a8':round(c8,4),'corr_cont':round(cc,4),
                         'gain_a8_vs_a4':round(c8-c4,4),'gain_cont_vs_a4':round(cc-c4,4),
                         'n_align0':int(n_a0),'n_align4':int(n_a4),
                         'pct_align0':round(n_a0/len(g),3),'pct_align4':round(n_a4/len(g),3)})
    return rows

if __name__ == '__main__':
    print("ALIGN resolution test — 0-4 vs 0-8 vs continuous, per cell")
    t0=time.time()
    res = Parallel(n_jobs=N_JOBS, verbose=5)(delayed(process_pair)(p) for p in PAIRS)
    df = pd.DataFrame([r for sub in res for r in sub])
    print(f"compute {time.time()-t0:.1f}s, {len(df)} cells")
    df.to_csv(OUT/'align_resolution.csv', index=False)

    print(f"\n=== Does finer/wider ALIGN beat 0-4? (per-cell spearman corr with forward) ===")
    print(f"  mean |corr| a4={df['corr_a4'].abs().mean():.4f}  a8={df['corr_a8'].abs().mean():.4f}  cont={df['corr_cont'].abs().mean():.4f}")
    print(f"  a8 beats a4 (|corr|) in {(df['corr_a8'].abs()>df['corr_a4'].abs()).sum()}/{len(df)} cells")
    print(f"  continuous beats a4 in {(df['corr_cont'].abs()>df['corr_a4'].abs()).sum()}/{len(df)} cells")
    print(f"  mean gain a8 vs a4:   {df['gain_a8_vs_a4'].mean():+.4f}")
    print(f"  mean gain cont vs a4: {df['gain_cont_vs_a4'].mean():+.4f}")

    print(f"\n=== Are the ALIGN-4 EXTREMES populated in every cell? (n at align=0 and align=4) ===")
    sparse4 = df[df['n_align4']<200]; sparse0 = df[df['n_align0']<200]
    print(f"  cells where align=4 has <200 bars: {len(sparse4)}/{len(df)}")
    print(f"  cells where align=0 has <200 bars: {len(sparse0)}/{len(df)}")
    print(f"  mean pct of bars at align=4: {df['pct_align4'].mean():.1%}  at align=0: {df['pct_align0'].mean():.1%}")
    if len(sparse4):
        print(f"\n  Cells with sparse align=4 (the strong-aligned extreme is rare):")
        print(sparse4[['pair','session','direction','n','n_align4','pct_align4']].head(15).to_string(index=False))

    print(f"\n=== Per-cell corr table (sorted by |corr_cont|, top 16) ===")
    df['abs_cont'] = df['corr_cont'].abs()
    print(df.sort_values('abs_cont', ascending=False).head(16)[
        ['pair','session','direction','n','corr_a4','corr_a8','corr_cont','pct_align4']].to_string(index=False))

    # Session-level summary: is the resolution gain bigger in some sessions?
    print(f"\n=== Resolution gain by session (cont vs a4) ===")
    print(df.groupby('session')[['corr_a4','corr_a8','corr_cont','gain_cont_vs_a4']].mean().round(4).to_string())
    print(f"\n→ {OUT}/align_resolution.csv")
