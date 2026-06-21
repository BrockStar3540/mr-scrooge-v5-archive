"""Per-cell momentum-separation test, walk-forward validated.

Symmetry note: the exhaustion separation E[fwd|RSI bull] - E[fwd|RSI bear] is
IDENTICAL for the long and short cell of a given (pair x session) — it's a
direction-agnostic property of the indicator-vs-forward relationship. So this
is a 24-cell (pair x session) test. Sign:
  separation < 0  -> momentum FADES in this cell (fast indicator agreement = exhaustion -> penalize)
  separation > 0  -> momentum TRENDS in this cell (agreement = confirmation -> reward)

Fast->slow ladder per cell tells you whether to penalize fast-confirmation
and/or reward slow-confirmation.

Walk-forward: TRAIN = bars < 2024-01-01, TEST = bars >= 2024-01-01.
A cell's effect is trustworthy only if train and test agree on SIGN with
similar magnitude.
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
OUT = ROOT / "percell_exhaustion"
OUT.mkdir(exist_ok=True)

PAIRS = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
PIP = {"AUD_JPY":0.01,"EUR_JPY":0.01,"USD_JPY":0.01,"AUD_USD":0.0001,
       "EUR_USD":0.0001,"GBP_USD":0.0001,"USD_CAD":0.0001,"USD_CHF":0.0001}
N_JOBS = 8
FWD_BARS = 12
SPLIT = pd.Timestamp('2024-01-01', tz='UTC')

def wilder_rsi(close, period):
    d = close.astype(float).diff()
    g = d.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    l = (-d.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    return 100 - 100/(1 + g/l.replace(0,np.nan))

def ema(close, span): return close.astype(float).ewm(span=span, adjust=False).mean()
def resample(m5, rule):
    return m5.resample(rule, label='right', closed='right').agg(
        {'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna()
def session_from_hour(h):
    if 22<=h or h<=5: return 'asia'
    if 6<=h<=12: return 'london'
    if 13<=h<=14: return 'overlap'
    return 'ny'

# Fast->slow ladder of momentum indicators (signed, >0 bullish)
LADDER = [
    ('RSI7_M5','RSI',7,'M5'), ('RSI14_M5','RSI',14,'M5'),
    ('RSI7_M15','RSI',7,'M15'), ('RSI14_M30','RSI',14,'M30'), ('RSI7_H1','RSI',7,'H1'),
    ('EMA5_20_M5','EMA',(5,20),'M5'), ('EMA8_21_M15','EMA',(8,21),'M15'),
    ('EMA10_30_M30','EMA',(10,30),'M30'),
]
TF_RULES = {'M15':'15min','M30':'30min','H1':'1h'}

def build_signed(m5, kind, param, tf):
    src = m5 if tf=='M5' else resample(m5, TF_RULES[tf])
    if kind=='RSI':
        s = wilder_rsi(src['close'], param) - 50
    else:
        f,sl = param
        s = ema(src['close'], f) - ema(src['close'], sl)
    return s.reindex(m5.index, method='ffill')

def sep_stats(sig, fwd):
    """E[fwd|bull] - E[fwd|bear] + counts."""
    d = pd.DataFrame({'s':sig,'f':fwd}).dropna()
    bull = d['s']>0; bear = d['s']<0
    if bull.sum()<500 or bear.sum()<500: return None, 0, 0
    return d.loc[bull,'f'].mean() - d.loc[bear,'f'].mean(), int(bull.sum()), int(bear.sum())

def process_pair(pair):
    t0 = time.time()
    pip = PIP[pair]
    m5 = pd.read_parquet(RAW / f"{pair}_M5.parquet")
    close = m5['close'].astype(float)
    fwd = (close.shift(-FWD_BARS) - close) / pip
    sess = pd.Series([session_from_hour(h) for h in m5.index.hour], index=m5.index)
    is_train = m5.index < SPLIT

    rows = []
    for name, kind, param, tf in LADDER:
        sig = build_signed(m5, kind, param, tf)
        for s in ['asia','london','ny','overlap']:
            cell_mask = (sess==s)
            for win, wm in [('train', is_train), ('test', ~is_train)]:
                mask = cell_mask & wm
                sep, nb, nbr = sep_stats(sig[mask], fwd[mask])
                if sep is None: continue
                rows.append({'pair':pair,'session':s,'indicator':name,'window':win,
                             'separation':round(sep,3),'n_bull':nb,'n_bear':nbr})
    print(f"  {pair}: {len(rows)} rows, {time.time()-t0:.1f}s")
    return rows

if __name__ == '__main__':
    print(f"Per-cell exhaustion ladder, walk-forward (train<2024, test>=2024), {N_JOBS} cores")
    t0 = time.time()
    res = Parallel(n_jobs=N_JOBS, verbose=5)(delayed(process_pair)(p) for p in PAIRS)
    df = pd.DataFrame([r for sub in res for r in sub])
    print(f"Total: {time.time()-t0:.1f}s")
    df.to_csv(OUT/'percell_ladder_walkforward.csv', index=False)

    # Pivot to train/test side by side
    piv = df.pivot_table(index=['pair','session','indicator'], columns='window', values='separation').reset_index()
    piv = piv.dropna(subset=['train','test'])
    piv['sign_agree'] = (np.sign(piv['train'])==np.sign(piv['test']))
    piv['mag_test'] = piv['test'].abs()

    # ── The headline: fast-RSI exhaustion per (pair x session), walk-forward stable ──
    print(f"\n=== FAST-RSI (RSI7_M5) momentum separation per cell — TRAIN vs TEST ===")
    print(f"   (negative = momentum fades/exhaustion; positive = momentum trends)")
    fast = piv[piv['indicator']=='RSI7_M5'].copy().sort_values('test')
    print(fast[['pair','session','train','test','sign_agree']].to_string(index=False))

    # ── Session-level pattern (mean across pairs), per ladder rung ──
    print(f"\n=== LADDER × SESSION: mean TEST separation across pairs (fast->slow) ===")
    lad = piv.groupby(['indicator','session'])['test'].mean().unstack().round(3)
    # order ladder
    order = [l[0] for l in LADDER]
    lad = lad.reindex(order)
    print(lad.to_string())

    # ── Walk-forward stability: which (cell × indicator) hold sign train->test ──
    print(f"\n=== WALK-FORWARD STABLE CELLS (sign agrees train/test, |test|>=0.3) ===")
    stable = piv[(piv['sign_agree']) & (piv['mag_test']>=0.3)].sort_values('mag_test', ascending=False)
    print(f"{len(stable)} (pair×session×indicator) combos stable + material out-of-time")
    print(stable[['pair','session','indicator','train','test']].head(30).to_string(index=False))

    # ── Aggregate the exhaustion signal: per cell, average the FAST rungs (M5) vs SLOW rungs ──
    fast_rungs = ['RSI7_M5','RSI14_M5','EMA5_20_M5']
    slow_rungs = ['RSI14_M30','RSI7_H1','EMA10_30_M30']
    fast_sep = piv[piv['indicator'].isin(fast_rungs)].groupby(['pair','session'])['test'].mean().rename('fast_test')
    slow_sep = piv[piv['indicator'].isin(slow_rungs)].groupby(['pair','session'])['test'].mean().rename('slow_test')
    fast_tr  = piv[piv['indicator'].isin(fast_rungs)].groupby(['pair','session'])['train'].mean().rename('fast_train')
    slow_tr  = piv[piv['indicator'].isin(slow_rungs)].groupby(['pair','session'])['train'].mean().rename('slow_train')
    cell = pd.concat([fast_tr,fast_sep,slow_tr,slow_sep], axis=1).round(3).reset_index()
    cell['fast_stable'] = np.sign(cell['fast_train'])==np.sign(cell['fast_test'])
    cell['slow_stable'] = np.sign(cell['slow_train'])==np.sign(cell['slow_test'])
    cell = cell.sort_values('fast_test')
    cell.to_csv(OUT/'percell_fast_slow_summary.csv', index=False)
    print(f"\n=== PER-CELL FAST vs SLOW momentum separation (test window, walk-forward stable flags) ===")
    print(f"   fast<0 = penalize fast-momentum-confirmation (exhaustion); slow>0 = reward slow-confirmation")
    print(cell.to_string(index=False))

    print(f"\n→ {OUT}/percell_ladder_walkforward.csv, percell_fast_slow_summary.csv")
