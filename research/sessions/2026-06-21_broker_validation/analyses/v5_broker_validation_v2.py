"""FIXED broker validation. Forward 1H pip = OANDA market data after entry —
COMPLETELY INDEPENDENT of whether V5 manually closed the trade. Use ALL 118
trades, not just BOT_EXIT subset. Manual close affects realized P/L only,
NOT the entry-bar indicators NOR the forward market direction.
"""
import json, subprocess
from pathlib import Path
import pandas as pd
import numpy as np

def assert_on_mini():
    s = subprocess.run(["system_profiler","SPHardwareDataType"], capture_output=True, text=True).stdout
    if "CPYQTH294R" not in s: raise RuntimeError("NOT ON MINI")
    print("✓ device verified: Mini CPYQTH294R")
assert_on_mini()

ROOT = Path.home() / "qtl-discovery-8yr"
BV = ROOT / "broker_validation"

df = pd.read_csv(BV / "trades_broker_validated.csv")
print(f"All trades: {len(df)}")
print(f"With valid forward_1h_pip_signed: {df['forward_1h_pip_signed'].notna().sum()}")
print(f"By exit_class:")
print(df.groupby('exit_class')['forward_1h_pip_signed'].agg(['count', 'mean']).round(2).to_string())

# ALL trades with valid forward data — don't filter by exit_class
valid = df[df['forward_1h_pip_signed'].notna()].copy()
print(f"\nUsing all {len(valid)} trades with valid forward windows")

# Per-cell stats with FULL dataset
per_cell = valid.groupby(['pair','session','side']).agg(
    n=('trade_id','count'),
    n_manual=('exit_class', lambda x: (x=='MANUAL').sum()),
    broker_fwd_1h_mean_pip=('forward_1h_pip_signed','mean'),
    broker_fwd_1h_wr=('forward_1h_pip_signed', lambda x: (x>0).mean()),
    realized_mean_pl=('realized_pl_usd','mean'),
).round(3).sort_values('broker_fwd_1h_mean_pip')
print(f"\n=== PER-CELL BROKER FORWARD 1H (ALL TRADES, n>=3) ===")
print(per_cell[per_cell['n']>=3].to_string())

# Per-cell × feature corrs (USING ALL trades)
print(f"\n=== PER-CELL TOP FEATURE CORRELATION WITH FORWARD 1H PIP (ALL trades, n>=4) ===")
feat_cols = [c for c in df.columns if c.startswith('q_') or c in
             ('atr_5m','rsi14','bb_pos','rsi14_h1','h1_ret_1bar','h1_ret_4bar')]
rows = []
for (pair, sess, side), g in valid.groupby(['pair','session','side']):
    if len(g) < 4: continue
    for f in feat_cols:
        if f not in g.columns: continue
        sub = g[[f,'forward_1h_pip_signed']].dropna()
        if len(sub) < 4: continue
        corr = sub[f].corr(sub['forward_1h_pip_signed'])
        if pd.isna(corr): continue
        rows.append({"pair":pair,"session":sess,"side":side,"n":len(g),
                     "feature":f,"corr":round(corr,3)})
cor = pd.DataFrame(rows)
top_per_cell = (cor.assign(absc=cor['corr'].abs())
                   .sort_values('absc',ascending=False)
                   .groupby(['pair','session','side']).head(3))
print(top_per_cell[['pair','session','side','n','feature','corr']].to_string(index=False))

# Save
per_cell.reset_index().to_csv(BV / "per_cell_v2_full_dataset.csv")
cor.to_csv(BV / "per_cell_feature_corrs_v2_full.csv", index=False)
print(f"\n→ {BV / 'per_cell_v2_full_dataset.csv'}")
print(f"→ {BV / 'per_cell_feature_corrs_v2_full.csv'}")

# Also: cells where my prior bot-exit-only analysis was wrong
print(f"\n=== Cells where INCLUDING manual closes CHANGES the broker fwd 1H direction ===")
prior = df[(df['exit_class']=='BOT_EXIT') & df['forward_1h_pip_signed'].notna()].copy()
prior_cell = prior.groupby(['pair','session','side'])['forward_1h_pip_signed'].mean().rename('prior_botexit_fwd')
new_cell = per_cell['broker_fwd_1h_mean_pip']
cmp = pd.concat([prior_cell, new_cell], axis=1)
cmp['diff'] = (cmp['broker_fwd_1h_mean_pip'] - cmp['prior_botexit_fwd']).abs()
cmp = cmp[per_cell['n']>=3].sort_values('diff', ascending=False)
print(cmp.head(15).to_string())
