"""Indicator parameter sweep + aggregator/verifier test.

Two questions:
  Q1 (params off?): sweep numerical variants of RSI / EMA / StochRSI across
     periods, TF, cross-levels. For each variant measure per-cell + pooled
     DIRECTIONAL SEPARATION = mean(fwd_60m | indicator bullish) - mean(fwd_60m | bearish).
     A useful indicator has large, consistent separation (and sign matters:
     positive = trend-following carries info; negative = it fades).

  Q2 (verifier/aggregator?): for a base direction B and a verifier V, does
     requiring V to AGREE with B lift forward expectancy?
       lift = E[B*fwd | sign(V)==B] - E[B*fwd | sign(V)!=B]
     Positive lift = V is a useful confirmation layer on B (an aggregator).

All bars, 8yr, 8 pairs. Per (pair x session) cell + pooled + per session.
"""
import os, json, subprocess, time
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
OUT = ROOT / "indicator_sweep"
OUT.mkdir(exist_ok=True)

PAIRS = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
PIP = {"AUD_JPY":0.01,"EUR_JPY":0.01,"USD_JPY":0.01,"AUD_USD":0.0001,
       "EUR_USD":0.0001,"GBP_USD":0.0001,"USD_CAD":0.0001,"USD_CHF":0.0001}
N_JOBS = 8
FWD_BARS = 12  # 60 min on M5

def wilder_rsi(close, period):
    d = close.astype(float).diff()
    g = d.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    l = (-d.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = g / l.replace(0, np.nan)
    return 100 - 100/(1+rs)

def ema(close, span): return close.astype(float).ewm(span=span, adjust=False).mean()

def stoch_rsi_k(close, rp=14, kp=5, dp=3):
    r = wilder_rsi(close, rp)
    rmin = r.rolling(rp).min(); rmax = r.rolling(rp).max()
    st = (r - rmin)/(rmax-rmin).replace(0,np.nan)*100
    return st.rolling(kp).mean()

def resample(m5, rule):
    return m5.resample(rule, label='right', closed='right').agg(
        {'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna()

def session_from_hour(h):
    if 22<=h or h<=5: return 'asia'
    if 6<=h<=12: return 'london'
    if 13<=h<=14: return 'overlap'
    return 'ny'

# ── Build the variant grid. Each variant returns a SIGNED series (>0 bullish) on the M5 timeline ──
TF_RULES = {'M15':'15min','M30':'30min','H1':'1h','H4':'4h'}

def build_variants(m5):
    """Return dict name -> signed pd.Series aligned to m5.index (ffill from higher TF)."""
    out = {}
    tfs = {tf: resample(m5, rule) for tf, rule in TF_RULES.items()}
    tfs['M5'] = m5
    # RSI variants: signed = RSI - level
    for period in [7, 9, 14, 21]:
        for tf in ['M5','M15','M30','H1']:
            r = wilder_rsi(tfs[tf]['close'], period)
            for level in [50]:
                s = (r - level)
                out[f"RSI{period}_{tf}_lvl{level}"] = s.reindex(m5.index, method='ffill')
    # RSI band variants (45/55) on a couple
    for period in [14]:
        for tf in ['M15','M30']:
            r = wilder_rsi(tfs[tf]['close'], period)
            for level in [45, 55]:
                out[f"RSI{period}_{tf}_lvl{level}"] = (r - level).reindex(m5.index, method='ffill')
    # EMA state variants: signed = ema_fast - ema_slow
    for (f,s) in [(5,20),(8,21),(10,30),(12,26),(20,50)]:
        for tf in ['M5','M15','M30','H1']:
            ef = ema(tfs[tf]['close'], f); es = ema(tfs[tf]['close'], s)
            out[f"EMA{f}_{s}_{tf}"] = (ef - es).reindex(m5.index, method='ffill')
    # StochRSI variants: signed = K - 50
    for (rp,kp,dp) in [(14,5,3),(14,3,3),(21,5,5)]:
        for tf in ['M15','M30']:
            k = stoch_rsi_k(tfs[tf]['close'], rp, kp, dp)
            out[f"StochK{rp}_{kp}_{dp}_{tf}"] = (k - 50).reindex(m5.index, method='ffill')
    return out

# ── Base direction signals for the aggregator test ──
def build_bases(m5, variants):
    """Bases = candidate primary direction signals (signed)."""
    bases = {}
    # B1: h1_ret_1bar sign (V5's #1 momentum factor)
    h1 = resample(m5, '1h')
    h1ret = (h1['close'] - h1['close'].shift(1))
    bases['BASE_h1ret'] = h1ret.reindex(m5.index, method='ffill')
    # B2: RSI(7) M15 - 50 (the app's primary)
    bases['BASE_rsi7_m15'] = variants['RSI7_M15_lvl50']
    # B3: EMA 5/20 M15 state
    bases['BASE_ema5_20_m15'] = variants['EMA5_20_M15']
    return bases

def process_pair(pair):
    t0 = time.time()
    pip = PIP[pair]
    m5 = pd.read_parquet(RAW / f"{pair}_M5.parquet")
    close = m5['close'].astype(float)
    fwd = (close.shift(-FWD_BARS) - close) / pip   # signed 60m forward pip (long convention)
    sess = pd.Series([session_from_hour(h) for h in m5.index.hour], index=m5.index)

    variants = build_variants(m5)
    bases = build_bases(m5, variants)

    rows_standalone = []
    rows_agg = []

    base_df = pd.DataFrame({'fwd': fwd, 'sess': sess})

    # ── Q1: standalone directional separation per variant ──
    for vname, vser in variants.items():
        d = pd.DataFrame({'sig': vser, 'fwd': fwd, 'sess': sess}).dropna()
        if len(d) < 5000: continue
        bull = d['sig'] > 0; bear = d['sig'] < 0
        # pooled
        sep = d.loc[bull,'fwd'].mean() - d.loc[bear,'fwd'].mean()
        corr = np.sign(d['sig']).corr(d['fwd'])
        rows_standalone.append({'pair':pair,'variant':vname,'scope':'pooled',
                                'n':len(d),'sep':round(sep,3),'sign_corr':round(corr,4),
                                'mean_fwd_bull':round(d.loc[bull,'fwd'].mean(),3),
                                'mean_fwd_bear':round(d.loc[bear,'fwd'].mean(),3)})
        # per session
        for s, g in d.groupby('sess'):
            if len(g) < 2000: continue
            b = g['sig']>0; r = g['sig']<0
            rows_standalone.append({'pair':pair,'variant':vname,'scope':s,
                                    'n':len(g),'sep':round(g.loc[b,'fwd'].mean()-g.loc[r,'fwd'].mean(),3),
                                    'sign_corr':round(np.sign(g['sig']).corr(g['fwd']),4),
                                    'mean_fwd_bull':round(g.loc[b,'fwd'].mean(),3),
                                    'mean_fwd_bear':round(g.loc[r,'fwd'].mean(),3)})

    # ── Q2: aggregator lift — does verifier V agreeing with base B lift forward? ──
    for bname, bser in bases.items():
        bdir = np.sign(bser)  # +1 long, -1 short
        for vname, vser in variants.items():
            if vname == bname.replace('BASE_',''): continue
            d = pd.DataFrame({'bdir':bdir,'vsig':vser,'fwd':fwd,'sess':sess}).dropna()
            d = d[d['bdir']!=0]
            if len(d) < 5000: continue
            d['signed_fwd'] = d['bdir'] * d['fwd']   # forward in the base's direction
            agree = np.sign(d['vsig']) == d['bdir']
            disagree = np.sign(d['vsig']) == -d['bdir']
            if agree.sum()<1000 or disagree.sum()<1000: continue
            e_agree = d.loc[agree,'signed_fwd'].mean()
            e_dis   = d.loc[disagree,'signed_fwd'].mean()
            rows_agg.append({'pair':pair,'base':bname,'verifier':vname,'scope':'pooled',
                             'n_agree':int(agree.sum()),'n_disagree':int(disagree.sum()),
                             'E_agree':round(e_agree,3),'E_disagree':round(e_dis,3),
                             'lift':round(e_agree - e_dis,3)})
    elapsed = time.time()-t0
    print(f"  {pair}: {len(variants)} variants, {len(rows_standalone)} standalone rows, {len(rows_agg)} agg rows, {elapsed:.1f}s")
    return rows_standalone, rows_agg

if __name__ == '__main__':
    print(f"Indicator sweep: variants x TF x levels, all bars, 8yr x 8 pairs, {N_JOBS} cores")
    t0 = time.time()
    res = Parallel(n_jobs=N_JOBS, verbose=10)(delayed(process_pair)(p) for p in PAIRS)
    print(f"\nTotal: {time.time()-t0:.1f}s")

    standalone = pd.DataFrame([r for sub,_ in res for r in sub])
    agg = pd.DataFrame([r for _,sub in res for r in sub])
    standalone.to_csv(OUT/'standalone_sweep.csv', index=False)
    agg.to_csv(OUT/'aggregator_lift.csv', index=False)

    # ── Q1 SUMMARY: which variants carry the most directional info (pooled across pairs) ──
    print(f"\n=== Q1: STANDALONE — variant directional separation, pooled across pairs (scope=pooled) ===")
    sp = standalone[standalone['scope']=='pooled'].groupby('variant').agg(
        mean_sep=('sep','mean'), mean_corr=('sign_corr','mean'),
        consistency=('sep', lambda x:(np.sign(x)==np.sign(x.mean())).mean()), n_pairs=('pair','count')).round(4)
    sp = sp.sort_values('mean_sep', key=lambda s:s.abs(), ascending=False)
    print(sp.to_string())

    print(f"\n=== Q1 by SESSION: best variant separation per session (mean across pairs) ===")
    for s in ['asia','london','ny','overlap']:
        sub = standalone[standalone['scope']==s].groupby('variant')['sep'].mean().sort_values(key=lambda x:x.abs(), ascending=False)
        print(f"\n  --- {s} --- top 6 by |sep|:")
        print(sub.head(6).round(3).to_string())

    # ── Q2 SUMMARY: best aggregator lifts (verifier on base), pooled across pairs ──
    print(f"\n=== Q2: AGGREGATOR LIFT — verifier agreeing with base lifts forward expectancy (mean across pairs) ===")
    al = agg.groupby(['base','verifier']).agg(
        mean_lift=('lift','mean'), mean_E_agree=('E_agree','mean'), mean_E_dis=('E_disagree','mean'),
        consistency=('lift', lambda x:(x>0).mean()), n_pairs=('pair','count')).round(3)
    al = al.sort_values('mean_lift', ascending=False)
    print(f"\n  TOP 25 verifier->base lifts:")
    print(al.head(25).to_string())
    print(f"\n  BOTTOM 10 (verifier HURTS the base):")
    print(al.tail(10).to_string())
    al.to_csv(OUT/'aggregator_lift_summary.csv')
    print(f"\n→ {OUT}/standalone_sweep.csv, aggregator_lift.csv, aggregator_lift_summary.csv")
