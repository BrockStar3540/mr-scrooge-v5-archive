"""Enrich the 44 live trades with qtl features looked up from the 8yr feature parquets,
then replay each cell's top-3 rules against the actual trade outcomes."""
import json, time, subprocess
from pathlib import Path
import numpy as np
import pandas as pd

def assert_on_mini():
    s = subprocess.run(["system_profiler","SPHardwareDataType"], capture_output=True, text=True).stdout
    if "CPYQTH294R" not in s: raise RuntimeError("NOT ON MINI")
    print("✓ device verified: Mini CPYQTH294R")
assert_on_mini()

ROOT      = Path.home() / "qtl-discovery-8yr"
FEATURES  = ROOT / "features"
OUT       = ROOT / "master_matrix"
LIVE_CSV  = ROOT / "v5_full_matrix_v2_36cols.csv"

# Live trades have a tid but no entry_time column directly.
# Need to parse from journal OR use the prefetch bundle from earlier session.
# Reuse v5_qtl_prefetch_bundle.json if present (has tid → entry_time_iso).
BUNDLE_PATH = Path.home() / "qtl-discovery" / "v5_qtl_prefetch_bundle.json"
if not BUNDLE_PATH.exists():
    raise FileNotFoundError(f"Bundle not found at {BUNDLE_PATH}")
bundle = json.loads(BUNDLE_PATH.read_text())
trade_meta = {t["tid"]: t for t in bundle["trades"]}
print(f"Loaded {len(trade_meta)} trade-meta records from prefetch bundle")

live = pd.read_csv(LIVE_CSV)
live["tid"] = live["tid"].astype(str)
live["dir"] = live["dir"].str.lower()
print(f"Loaded {len(live)} live trades")

# For each live trade, look up qtl features at entry-time bar from per-pair parquet
def enrich_trade(row):
    tid = row["tid"]
    meta = trade_meta.get(tid)
    if meta is None: return None
    entry_iso = meta["entry_time_iso"]
    entry_ts = pd.Timestamp(entry_iso)
    pair = row["pair"]
    fp = FEATURES / f"{pair}_features.parquet"
    df = pd.read_parquet(fp)
    # Find the bar at or just before entry
    idx = df.index.get_indexer([entry_ts], method="ffill")
    if len(idx) == 0 or idx[0] < 0: return None
    bar = df.iloc[idx[0]]
    out = {"tid": tid, "entry_time_iso": entry_iso, "matched_bar": str(bar.name)}
    # Pull all q_* features
    for c in bar.index:
        if c.startswith("q_"): out[c] = bar[c]
    return out

enriched_rows = []
for _, row in live.iterrows():
    e = enrich_trade(row)
    if e is not None: enriched_rows.append(e)
enriched_df = pd.DataFrame(enriched_rows)
print(f"Enriched {len(enriched_df)} trades with qtl features")

# Merge enriched with live
live = live.merge(enriched_df, on="tid", how="left")
print(f"Merged: {len(live)} rows, q_ columns: {[c for c in live.columns if c.startswith('q_')][:6]}...")

# Save enriched
live.to_csv(OUT / "live_trades_enriched.csv", index=False)
print(f"→ {OUT / 'live_trades_enriched.csv'}")

# Now do the replay per cell using the master matrix rules
mm = json.load(open(OUT / "master_matrix.json"))
replay_rows = []
for cell in mm:
    pair = cell["pair"]; session = cell["session"]; direction = cell["direction"]
    cell_trades = live[(live["pair"]==pair) & (live["session"]==session) & (live["dir"]==direction)]
    if len(cell_trades) < 1: continue
    rules = json.loads(cell["best_rules"]) if isinstance(cell.get("best_rules"), str) else cell.get("best_rules", [])
    for rule in rules[:3]:
        f = rule["feature"]
        if f not in cell_trades.columns: continue
        thr = rule["threshold"]; side = rule["side"]
        if side == "gt":
            fires_mask = cell_trades[f] > thr
        else:
            fires_mask = cell_trades[f] < thr
        n_takes = int(fires_mask.sum())
        n_blocks = int((~fires_mask).sum())
        wr_taken   = float((cell_trades[fires_mask]["exit_net"] > 0).mean()) if n_takes >= 1 else None
        wr_blocked = float((cell_trades[~fires_mask]["exit_net"] > 0).mean()) if n_blocks >= 1 else None
        wr_baseline = float((cell_trades["exit_net"] > 0).mean()) if len(cell_trades) >= 1 else None
        mean_pips_taken = float(cell_trades[fires_mask]["exit_net"].mean()) if n_takes >= 1 else None
        mean_pips_blocked = float(cell_trades[~fires_mask]["exit_net"].mean()) if n_blocks >= 1 else None
        replay_rows.append({
            "pair": pair, "session": session, "direction": direction,
            "n_live_trades": len(cell_trades), "wr_baseline": wr_baseline,
            "rule_feature": f, "rule_threshold": round(thr, 4), "rule_side": side,
            "ml_rule_wr_delta": rule["wr_delta"],
            "live_n_taken_with_rule": n_takes, "live_wr_when_taken": round(wr_taken, 3) if wr_taken is not None else None,
            "live_mean_pips_taken": round(mean_pips_taken, 2) if mean_pips_taken is not None else None,
            "live_n_blocked": n_blocks, "live_wr_when_blocked": round(wr_blocked, 3) if wr_blocked is not None else None,
            "live_mean_pips_blocked": round(mean_pips_blocked, 2) if mean_pips_blocked is not None else None,
        })

replay_df = pd.DataFrame(replay_rows)
replay_df.to_csv(OUT / "live_replay_v2.csv", index=False)
print(f"\n→ {OUT / 'live_replay_v2.csv'}")
print(f"\n=== LIVE REPLAY — cells with N>=3 trades ===")
sig = replay_df[replay_df["n_live_trades"] >= 3].copy()
sig = sig.sort_values(["pair","session","direction"])
print(sig.to_string(index=False))
