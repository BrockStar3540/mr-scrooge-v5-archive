"""Universe expansion screen: 12 new pairs x 3 sessions x 2 sides, unconditional
drift, multi-slice bar (>= +2p in >=4/5 slices). Both sides reported: a strong
negative long IS a strong short (the flip check is built in)."""
from pathlib import Path
import pandas as pd
EXT = Path.home()/"v5-truth-matrix-ext"
sess_hours = {"asia": set(list(range(22,24))+list(range(0,7))), "london": set(range(7,13)), "ny": set(range(13,22))}
SLICES = [("YTD","2026-01-01",None),("May","2026-05-01","2026-06-01"),
          ("Jun","2026-06-01","2026-07-01"),("Jul","2026-07-01",None),("14d","2026-06-25",None)]
survivors, watch = [], []
for f in sorted(EXT.glob("*_2026.parquet")):
    pair = f.name.replace("_2026.parquet","")
    df = pd.read_parquet(f)
    for sess in ("asia","london","ny"):
        g = df[[h in sess_hours[sess] for h in df.index.hour]]
        for side in ("long","short"):
            net = (g[f"mfe_{side}_240"] - g[f"mae_{side}_240"]).dropna()
            if len(net) < 1000: continue
            ok = 0; have = 0; ms = []
            for nm, lo, hi in SLICES:
                x = net[net.index >= lo]
                if hi: x = x[x.index < hi]
                if len(x) < 50: continue
                have += 1; ms.append(f"{nm}:{x.mean():+.1f}")
                if x.mean() >= 2.0: ok += 1
            ytd = net.mean()
            if have >= 4 and ok >= 4:
                survivors.append((pair, sess, side, round(ytd,2), " ".join(ms)))
            elif have >= 4 and ok == 3 and ytd >= 1.5:
                watch.append((pair, sess, side, round(ytd,2), " ".join(ms)))
print(f"SURVIVORS ({len(survivors)}):")
for p, s, d, y, m in survivors: print(f"  {p}/{s} {d}: YTD {y:+.2f} | {m}")
print(f"\nWATCH — 3/5 slices ({len(watch)}):")
for p, s, d, y, m in watch: print(f"  {p}/{s} {d}: YTD {y:+.2f} | {m}")
