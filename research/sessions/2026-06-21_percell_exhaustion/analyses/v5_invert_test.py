"""Can the NY momentum-fade cells be run INVERTED?

Two questions:
  Q1 (raw inversion): on ALL NY bars, if you fade momentum (trade opposite the
     indicator), what's the expectancy net of spread? And does the fade
     STRENGTHEN with momentum extremity (because V5 only fires on strong signals)?
  Q2 (real trades): invert the actual broker NY trades (flip the 1H forward) —
     net of spread, would the opposite direction have profited?

follow_exp  = E[fwd * sign(momentum)]              (trade WITH momentum)
invert_exp  = -follow_exp                            (trade AGAINST = fade)
invert_net  = invert_exp - spread                    (after cost)

Walk-forward train(<2024)/test(>=2024). All bars, 8 pairs, NY session.
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
RAW = Path("/Volumes/Alien Device/direction_ml/raw_bars")
OUT = ROOT / "invert_test"; OUT.mkdir(exist_ok=True)

PAIRS = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
PIP = {"AUD_JPY":0.01,"EUR_JPY":0.01,"USD_JPY":0.01,"AUD_USD":0.0001,
       "EUR_USD":0.0001,"GBP_USD":0.0001,"USD_CAD":0.0001,"USD_CHF":0.0001}
# Typical OANDA spreads (pips) — conservative
SPREAD = {"EUR_USD":1.0,"GBP_USD":1.5,"USD_JPY":1.0,"USD_CAD":1.8,"AUD_USD":1.2,
          "USD_CHF":1.8,"EUR_JPY":1.8,"AUD_JPY":2.0}
N_JOBS = 8; FWD_BARS = 12
SPLIT = pd.Timestamp('2024-01-01', tz='UTC')

def wilder_rsi(close, period):
    d = close.astype(float).diff()
    g = d.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    l = (-d.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    return 100 - 100/(1 + g/l.replace(0,np.nan))
def resample(m5, rule):
    return m5.resample(rule, label='right', closed='right').agg(
        {'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna()
def session_from_hour(h):
    if 22<=h or h<=5: return 'asia'
    if 6<=h<=12: return 'london'
    if 13<=h<=14: return 'overlap'
    return 'ny'

def process_pair(pair):
    pip = PIP[pair]; spread = SPREAD[pair]
    m5 = pd.read_parquet(RAW / f"{pair}_M5.parquet")
    close = m5['close'].astype(float)
    fwd = (close.shift(-FWD_BARS) - close) / pip
    sess = pd.Series([session_from_hour(h) for h in m5.index.hour], index=m5.index)
    # momentum: RSI7 M5 (fastest, strongest fade) + h1_ret (V5's #1 factor)
    rsi = wilder_rsi(close, 7)
    rsi_dist = (rsi - 50)
    h1 = resample(m5, '1h'); h1ret = (h1['close']-h1['close'].shift(1)).reindex(m5.index, method='ffill') / pip

    rows = []
    for momname, mom in [('rsi7_m5', rsi_dist), ('h1ret', h1ret)]:
        d = pd.DataFrame({'mom':mom,'fwd':fwd,'sess':sess}).dropna()
        d = d[d['sess']=='ny']
        d = d[d['mom']!=0]
        d['follow'] = d['fwd'] * np.sign(d['mom'])    # trade WITH momentum
        d['is_test'] = d.index >= SPLIT
        d['mom_abs'] = d['mom'].abs()
        # Quintile by momentum strength
        for win, mask in [('train', ~d['is_test']), ('test', d['is_test'])]:
            sub = d[mask].copy()
            if len(sub) < 5000: continue
            sub['bucket'] = pd.qcut(sub['mom_abs'], 5, labels=['q1_weak','q2','q3','q4','q5_strong'], duplicates='drop')
            for b, g in sub.groupby('bucket', observed=True):
                follow = g['follow'].mean()
                invert = -follow
                rows.append({'pair':pair,'mom':momname,'window':win,'bucket':str(b),'n':len(g),
                             'follow_exp':round(follow,3),'invert_exp':round(invert,3),
                             'invert_net_spread':round(invert - spread,3),
                             'invert_wr':round((( -g['follow'])>0).mean(),3),
                             'spread':spread})
    return rows

if __name__ == '__main__':
    print(f"Invert test — NY momentum fade, strength-bucketed, net of spread, walk-forward")
    res = Parallel(n_jobs=N_JOBS, verbose=5)(delayed(process_pair)(p) for p in PAIRS)
    df = pd.DataFrame([r for sub in res for r in sub])
    df.to_csv(OUT/'invert_buckets.csv', index=False)

    print(f"\n=== Q1: does the FADE strengthen with momentum extremity? (RSI7_M5, TEST window, mean across pairs) ===")
    t = df[(df['mom']=='rsi7_m5')&(df['window']=='test')].groupby('bucket').agg(
        follow=('follow_exp','mean'), invert=('invert_exp','mean'),
        invert_net=('invert_net_spread','mean'), invert_wr=('invert_wr','mean'), n=('n','sum')).round(3)
    t = t.reindex(['q1_weak','q2','q3','q4','q5_strong'])
    print(t.to_string())
    print(f"\n  (h1ret momentum, TEST):")
    t2 = df[(df['mom']=='h1ret')&(df['window']=='test')].groupby('bucket').agg(
        follow=('follow_exp','mean'), invert=('invert_exp','mean'),
        invert_net=('invert_net_spread','mean'), n=('n','sum')).round(3)
    print(t2.reindex(['q1_weak','q2','q3','q4','q5_strong']).to_string())

    print(f"\n=== Q1: STRONGEST bucket (q5) invert-net-of-spread per pair, RSI7_M5 TEST ===")
    q5 = df[(df['mom']=='rsi7_m5')&(df['window']=='test')&(df['bucket']=='q5_strong')].sort_values('invert_net_spread', ascending=False)
    print(q5[['pair','n','follow_exp','invert_exp','invert_net_spread','invert_wr','spread']].to_string(index=False))

    # walk-forward stability of q5 invert sign
    q5tr = df[(df['mom']=='rsi7_m5')&(df['window']=='train')&(df['bucket']=='q5_strong')][['pair','invert_exp']].rename(columns={'invert_exp':'invert_train'})
    q5te = df[(df['mom']=='rsi7_m5')&(df['window']=='test')&(df['bucket']=='q5_strong')][['pair','invert_exp','invert_net_spread']].rename(columns={'invert_exp':'invert_test'})
    wf = q5tr.merge(q5te, on='pair')
    wf['stable'] = np.sign(wf['invert_train'])==np.sign(wf['invert_test'])
    print(f"\n=== Walk-forward: q5-strong invert expectancy, train vs test ===")
    print(wf.to_string(index=False))
    print(f"  pairs with positive invert in BOTH train+test: {((wf.invert_train>0)&(wf.invert_test>0)).sum()}/8")
    print(f"  pairs with invert_net_spread > 0 (test): {(wf.invert_net_spread>0).sum()}/8")
    df.to_csv(OUT/'invert_buckets.csv', index=False)
    print(f"\n→ {OUT}/invert_buckets.csv")
