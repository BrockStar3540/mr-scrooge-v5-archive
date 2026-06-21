"""Replace journal-derived live trade columns in master_matrix with REAL broker
data + 1H forward pip outcomes. Outcome truth = forward 1H pip move, NOT realized
P/L (exit logic changes constantly).

New columns:
  broker_n_trades       — count of OANDA-confirmed trades for this cell
  broker_n_bot_exit     — count of bot-exit (non-manual-close) trades
  broker_fwd_1h_mean_pip — mean 1H forward pip move (signed in trade direction)
  broker_fwd_1h_wr      — % of trades where 1H forward was in trade direction
  broker_realized_pl_mean — mean realized USD P/L (reference only)
  broker_top_fwd_corr_feature — feature with strongest |corr| vs 1H fwd
  broker_top_fwd_corr   — that correlation value
  broker_disagrees_matrix — True if broker says cell is losing but matrix says positive
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
MM = ROOT / "master_matrix" / "master_matrix.csv"

# Load
broker = pd.read_csv(BV / "trades_broker_validated.csv")
corrs = pd.read_csv(BV / "per_cell_feature_vs_forward1h.csv")
mm = pd.read_csv(MM)

print(f"broker trades: {len(broker)}; per-cell corrs: {len(corrs)}; matrix rows: {len(mm)}")

# Filter broker to bot_exit + valid fwd window for the fwd_1h analysis
bot_valid = broker[(broker['exit_class']=='BOT_EXIT') & broker['forward_1h_pip_signed'].notna()].copy()
print(f"  bot-exit + valid fwd: {len(bot_valid)}")

# Per-cell broker stats — KEY METRIC: 1H forward pip (broker truth)
per_cell_broker = broker.groupby(['pair','session','side']).agg(
    broker_n_trades=('trade_id','count'),
    broker_realized_wr=('realized_pl_usd', lambda x: (x>0).mean()),
    broker_realized_mean_pl=('realized_pl_usd','mean'),
).round(3)
# Bot-exit-only subset (clean signal evaluation)
per_cell_botexit = bot_valid.groupby(['pair','session','side']).agg(
    broker_n_bot_exit=('trade_id','count'),
    broker_fwd_1h_mean_pip=('forward_1h_pip_signed','mean'),
    broker_fwd_1h_wr=('forward_1h_pip_signed', lambda x: (x>0).mean()),
).round(3)

per_cell_broker = per_cell_broker.join(per_cell_botexit, how='outer')
per_cell_broker = per_cell_broker.reset_index().rename(columns={'side':'direction'})

# Top broker correlation feature per cell (where n>=4)
top_corr = (corrs.assign(abs_corr=corrs['corr_fwd_pip'].abs())
                  .sort_values('abs_corr', ascending=False)
                  .groupby(['pair','session','side']).head(1)
                  .rename(columns={'side':'direction',
                                   'feature':'broker_top_fwd_corr_feature',
                                   'corr_fwd_pip':'broker_top_fwd_corr'})
                  [['pair','session','direction','broker_top_fwd_corr_feature','broker_top_fwd_corr']])

per_cell_broker = per_cell_broker.merge(top_corr, on=['pair','session','direction'], how='left')

# Merge into master matrix
mm_new = mm.merge(per_cell_broker, on=['pair','session','direction'], how='left')

# Flag broker/matrix disagreement
def disagrees(row):
    if pd.isna(row.get('broker_fwd_1h_mean_pip')) or pd.isna(row.get('delta_auc_2026')):
        return False
    if row['broker_fwd_1h_mean_pip'] < -2 and row['delta_auc_2026'] > 0:
        return True  # broker says cell is losing, matrix says positive
    return False
mm_new['broker_disagrees_matrix'] = mm_new.apply(disagrees, axis=1)

# Disable recommendation per cell:
#   matrix_negative = (delta_auc_2026 <= 0 OR recent_3yr_mean <= 0)
#   broker_negative = (broker_fwd_1h_mean_pip < -2 AND broker_n_bot_exit >= 3) OR (broker_realized_mean_pl < -50 AND broker_n_trades >= 3)
#   recommend_disable = matrix_negative AND broker_negative
def recommend_disable(row):
    delta = row.get('delta_auc_2026')
    recent = row.get('recent_3yr_mean')
    fwd = row.get('broker_fwd_1h_mean_pip')
    n_bot = row.get('broker_n_bot_exit')
    realized = row.get('broker_realized_mean_pl')
    n = row.get('broker_n_trades')
    matrix_neg = (pd.notna(delta) and delta <= 0) or (pd.notna(recent) and recent <= 0)
    broker_neg = ((pd.notna(fwd) and fwd < -2 and pd.notna(n_bot) and n_bot >= 3) or
                  (pd.notna(realized) and realized < -50 and pd.notna(n) and n >= 3))
    return matrix_neg and broker_neg
mm_new['recommend_disable_v2'] = mm_new.apply(recommend_disable, axis=1)

out = ROOT / "master_matrix" / "master_matrix_with_broker.csv"
mm_new.to_csv(out, index=False)
print(f"\n→ {out}")

# Print disable recommendation table
print(f"\n=== DISABLE RECOMMENDATIONS (matrix-confirmed broker-losing cells) ===")
dis = mm_new[mm_new['recommend_disable_v2']==True].copy()
print(f"{len(dis)} cells flagged")
cols = ['pair','session','direction','current_profile','delta_auc_2026','recent_3yr_mean',
        'broker_n_trades','broker_n_bot_exit','broker_fwd_1h_mean_pip','broker_realized_mean_pl',
        'broker_top_fwd_corr_feature','broker_top_fwd_corr']
print(dis[cols].to_string(index=False))

print(f"\n=== BROKER-MATRIX DISAGREEMENTS (matrix positive, broker says losing) ===")
disagree = mm_new[mm_new['broker_disagrees_matrix']==True].copy()
print(f"{len(disagree)} cells")
print(disagree[cols + ['broker_disagrees_matrix']].to_string(index=False))

print(f"\n=== TOP CELLS BY broker_fwd_1h_mean_pip (cells with n_bot_exit>=3) ===")
strong = mm_new[mm_new['broker_n_bot_exit'].fillna(0) >= 3].copy()
top = strong.sort_values('broker_fwd_1h_mean_pip', ascending=False).head(10)
print(top[cols].to_string(index=False))

print(f"\n=== BOTTOM CELLS BY broker_fwd_1h_mean_pip (cells with n_bot_exit>=3) ===")
bot10 = strong.sort_values('broker_fwd_1h_mean_pip').head(10)
print(bot10[cols].to_string(index=False))
