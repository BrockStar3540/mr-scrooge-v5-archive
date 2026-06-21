import pandas as pd, numpy as np
df = pd.read_csv('/Users/brock-mini-mac/qtl-discovery-8yr/app_config_test/all_signals_raw.csv')
print(f'loaded {len(df):,} signals')

hz = ['fwd_15m','fwd_30m','fwd_60m','fwd_90m','fwd_120m']
print('\n=== EXPECTANCY (mean signed pip) BY HORIZON, per config ===')
agg = df.groupby('config')[hz].mean().round(3)
agg.columns = ['15m','30m','60m','90m','120m']
print(agg.to_string())

print('\n=== WIN RATE BY HORIZON, per config (% signed-pip > 0) ===')
wr = df.groupby('config')[hz].apply(lambda g: (g>0).mean()).round(3)
wr.columns = ['15m','30m','60m','90m','120m']
print(wr.to_string())

print('\n=== Tail stats (config 1 RSI cross only, 60m) ===')
c1 = df[df.config=='1_rsi7_cross_only']['fwd_60m'].dropna()
print(f'  n={len(c1):,}  mean={c1.mean():.3f}  median={c1.median():.3f}  std={c1.std():.1f}')
print(f'  pct >=+3p: {(c1>=3).mean():.1%}  >=+5p: {(c1>=5).mean():.1%}  >=+8p: {(c1>=8).mean():.1%}  >=+10p: {(c1>=10).mean():.1%}')
print(f'  pct <=-3p: {(c1<=-3).mean():.1%}  <=-5p: {(c1<=-5).mean():.1%}')

print('\n=== ANY config x pair x session with positive expectancy >+0.5p AND n>=200? ===')
cell = df.groupby(['config','pair','session'])['fwd_60m'].agg(['count','mean']).reset_index()
ntotal = df.groupby(['config','pair','session']).ngroups
cell = cell[(cell['count']>=200) & (cell['mean']>0.5)].sort_values('mean', ascending=False)
print(f'{len(cell)} cells qualify out of {ntotal} total')
print(cell.head(20).to_string(index=False))

print('\n=== INVERTED (FADE) edge? Cells with expectancy < -0.5p AND n>=200 (fade these = positive) ===')
fade = df.groupby(['config','pair','session'])['fwd_60m'].agg(['count','mean']).reset_index()
fade = fade[(fade['count']>=200) & (fade['mean']<-0.5)].sort_values('mean')
print(f'{len(fade)} cells where the signal anti-predicts (fading them would profit)')
print(fade.head(15).to_string(index=False))
