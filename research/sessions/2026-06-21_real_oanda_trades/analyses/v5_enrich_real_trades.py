"""Enrich the 118 OANDA-real trades with the 54 indicators at their actual fill time.

For each closed trade:
  - Look up its open_time in the per-pair 8yr feature parquet (Mini)
  - Extract all V5 baseline + qtl candidate features at that bar
  - Tag with side, session, exit_class, realized_pl, win/loss

Then re-do per-cell feature analysis using REAL trade outcomes.
"""
import os, sys, json, subprocess
from pathlib import Path
import numpy as np
import pandas as pd

def assert_on_mini():
    s = subprocess.run(["system_profiler","SPHardwareDataType"], capture_output=True, text=True).stdout
    if "CPYQTH294R" not in s: raise RuntimeError("NOT ON MINI")
    print("✓ device verified: Mini CPYQTH294R")
assert_on_mini()

ROOT = Path.home() / "qtl-discovery-8yr"
FEATURES = ROOT / "features"
OUT = ROOT / "real_trade_analysis"
OUT.mkdir(exist_ok=True)

trades = pd.read_csv(Path.home() / "qtl-discovery-8yr" / "oanda_all_classified.csv")
trades['open_time'] = pd.to_datetime(trades['open_time'], utc=True)
print(f"loaded {len(trades)} real trades")
print(f"  V5-era (>= 2026-06-18 19:04): {(trades['open_time'] >= pd.Timestamp('2026-06-18 19:04', tz='UTC')).sum()}")

# Cache pair parquets
print("loading 8 pair parquets...")
pair_dfs = {}
for p in trades['pair'].unique():
    fp = FEATURES / f"{p}_features.parquet"
    if fp.exists():
        pair_dfs[p] = pd.read_parquet(fp)

# Enrich each trade
enriched_rows = []
for _, t in trades.iterrows():
    pair = t['pair']
    if pair not in pair_dfs:
        continue
    df = pair_dfs[pair]
    # Find the M5 bar at or just before open_time
    open_ts = t['open_time']
    idx = df.index.get_indexer([open_ts], method='ffill')
    if len(idx) == 0 or idx[0] < 0: continue
    bar = df.iloc[idx[0]]
    row = {
        "trade_id": t['trade_id'],
        "pair": pair,
        "side": t['side'],
        "session": t.get('session'),
        "open_time": str(open_ts),
        "open_price": t['open_price'],
        "close_time": t['close_time'],
        "close_price": t['close_price'],
        "realized_pl_usd": t['realized_pl_usd'],
        "exit_class": t['exit_class'],
        "win": int(t['realized_pl_usd'] > 0),
        "bar_time": str(bar.name),
        "is_v5_era": int(open_ts >= pd.Timestamp('2026-06-18 19:04', tz='UTC')),
    }
    # All features at that bar
    for c in bar.index:
        if c in ("session","label","fwd_ret_pips"):
            continue
        row[c] = bar[c]
    enriched_rows.append(row)

en = pd.DataFrame(enriched_rows)
en.to_csv(OUT / "real_trades_enriched.csv", index=False)
print(f"\n→ {OUT / 'real_trades_enriched.csv'} ({len(en)} trades enriched)")

# ── Per-cell × side stats from REAL trades ─────────────────────────────────
print(f"\n=== ALL ERA (V4+V5) BOT_EXIT trades per cell ===")
bot = en[en['exit_class']=='BOT_EXIT'].copy()
per_cell = bot.groupby(['pair','session','side']).agg(
    n=('trade_id','count'),
    wr=('win','mean'),
    mean_pl=('realized_pl_usd','mean'),
    total_pl=('realized_pl_usd','sum'),
).round(3).sort_values('total_pl', ascending=False)
per_cell.to_csv(OUT / "per_cell_real_trades_bot_exit.csv")
print(per_cell.head(25).to_string())

# Per-feature correlation with WIN within each cell (where n>=3)
print(f"\n=== PER-CELL × FEATURE CORRELATIONS (cells with n>=3 bot-exit trades) ===")
feature_cols = [c for c in en.columns if c.startswith('q_') or c in
                 ('atr_5m','atr_1h','atr_conc','atr_h1_relative','wall_frac','rvol_5bar','rvol_12bar',
                  'rsi14','bb_pos','htf_pct_20','htf_pct_60','ema20_dist_pct','ema50_dist_pct',
                  'adr_consumed','close_pos_daily','h1_ret_1bar','h1_ret_4bar','trend_4h',
                  'zscore_1h','ema20_1h_dist','d_ret','pdh_dist','pdl_dist')]
print(f"Features tested: {len(feature_cols)}")

cell_corr_rows = []
for (pair, sess, side), g in bot.groupby(['pair','session','side']):
    if len(g) < 3: continue
    for f in feature_cols:
        if f not in g.columns: continue
        try:
            valid = g[[f, 'win']].dropna()
            if len(valid) < 3: continue
            corr = valid[f].corr(valid['win'])
            if pd.isna(corr): continue
            cell_corr_rows.append({
                "pair": pair, "session": sess, "side": side,
                "n_trades": len(g), "feature": f,
                "corr_with_win": round(corr, 3),
                "wr_baseline": round(g['win'].mean(), 3),
            })
        except Exception: pass

corr_df = pd.DataFrame(cell_corr_rows)
corr_df.to_csv(OUT / "per_cell_feature_correlations.csv", index=False)
# Top |corr| per cell
print(f"\n=== Top correlation per cell (|corr| > 0.5, n_trades >= 3) ===")
strong = corr_df[corr_df['corr_with_win'].abs() > 0.5].sort_values('corr_with_win', key=abs, ascending=False)
print(strong.to_string(index=False))

