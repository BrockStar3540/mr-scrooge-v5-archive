#!/usr/bin/env python3
"""Test Brock's USD_JPY/london INVERT + m_cert floor 0.50 hypothesis on the
3,220-bar 2026 V5-actionable dataset.

Inverted = negate forward pip (mathematically equivalent to flipping trade direction).
"""
import pandas as pd
from pathlib import Path

OUT = Path.home() / "v5_backtest" / "usdjpy_2026_actionable.csv"
df = pd.read_csv(OUT)
print(f"Loaded {len(df)} V5-actionable bars\n")

def summarize(seg, label):
    if len(seg)==0: return f"{label:<30} n=0"
    n = len(seg); m = seg["fwd_pip"].mean()
    wr = 100 * (seg["fwd_pip"] > 0).mean()
    sm = seg["fwd_pip"].sum()
    return f"{label:<30} n={n:>4}  mean={m:>+6.3f}p  WR={wr:>4.1f}%  sum={sm:>+8.1f}p"

# === LONDON: current vs inverted, at floor 0.25 (current) and 0.50 (proposed) ===
print("="*85)
print("USD_JPY/LONDON — inverted + m_cert floor 0.50 sim")
print("="*85)
ldn = df[df.session=="london"].copy()
ldn["fwd_inv"] = -ldn["fwd_pip"]
print(f"\nTotal london actionable bars: {len(ldn)}")

print("\n--- CURRENT (natural direction, floor 0.25) ---")
print(summarize(ldn, "  ALL london natural"))
print(summarize(ldn[ldn.dir=="long"], "    long"))
print(summarize(ldn[ldn.dir=="short"], "    short"))

print("\n--- INVERTED (flip direction, floor 0.25) ---")
inv_natural = ldn.copy(); inv_natural["fwd_pip"] = inv_natural["fwd_inv"]
print(summarize(inv_natural, "  ALL london INVERTED"))
print(summarize(inv_natural[inv_natural.dir=="long"], "    bot-long → traded short"))
print(summarize(inv_natural[inv_natural.dir=="short"], "    bot-short → traded long"))

print("\n--- INVERTED + FLOOR 0.50 (BROCK'S PROPOSAL) ---")
hi = ldn[ldn.m_cert >= 0.50].copy()
lo = ldn[ldn.m_cert <  0.50].copy()
hi["fwd_pip"] = -hi["fwd_pip"]   # invert
print(summarize(hi, "  KEPT-INVERTED (m_cert>=0.50)"))
print(summarize(hi[hi.dir=="long"], "    bot-long → short"))
print(summarize(hi[hi.dir=="short"], "    bot-short → long"))
print(summarize(lo, "  BLOCKED (m_cert<0.50, no trade)"))

# Side-by-side comparison
print("\n--- COMPARISON: net expected per-bar ---")
print(f"  Current (natural, floor 0.25):     {ldn['fwd_pip'].mean():+.3f}p  WR={100*(ldn['fwd_pip']>0).mean():.1f}%  n={len(ldn)}")
print(f"  Inverted (no floor):               {ldn['fwd_inv'].mean():+.3f}p  WR={100*(ldn['fwd_inv']>0).mean():.1f}%  n={len(ldn)}")
print(f"  Inverted + floor 0.50:             {hi['fwd_pip'].mean():+.3f}p  WR={100*(hi['fwd_pip']>0).mean():.1f}%  n={len(hi)}")

# Also do ASIA same way for completeness
print("\n" + "="*85)
print("USD_JPY/ASIA — same sim (already inverted_live currently)")
print("="*85)
asia = df[df.session=="asia"].copy()
print(f"\nTotal asia actionable bars: {len(asia)}")
print("Note: USD_JPY/asia is CURRENTLY inverted_live — so the bot's natural-direction")
print("fwd_pip here represents the OPPOSITE of what's being traded live.\n")

print("--- Natural direction (what the BACKTEST captures, signal=trade) ---")
print(summarize(asia, "  ALL asia natural (signal-dir)"))
print(summarize(asia[asia.dir=="long"], "    long"))
print(summarize(asia[asia.dir=="short"], "    short"))

print("\n--- INVERTED (= what the LIVE BOT actually does) ---")
asia_inv = asia.copy(); asia_inv["fwd_pip"] = -asia_inv["fwd_pip"]
print(summarize(asia_inv, "  ALL asia INVERTED"))

print("\n--- INVERTED + FLOOR 0.50 ---")
asia_hi = asia[asia.m_cert >= 0.50].copy()
asia_hi["fwd_pip"] = -asia_hi["fwd_pip"]
print(summarize(asia_hi, "  KEPT-INVERTED (m_cert>=0.50)"))

# Last 30 days of 2026 (most recent regime)
print("\n" + "="*85)
print("RECENT REGIME ONLY (last 30 days of 2026, may be more representative)")
print("="*85)
df["ts"] = pd.to_datetime(df["ts"])
recent = df[df.ts >= df.ts.max() - pd.Timedelta(days=30)].copy()
recent["fwd_inv"] = -recent["fwd_pip"]
print(f"  last-30d total bars: {len(recent)}\n")
for sess in ["asia","london"]:
    s = recent[recent.session==sess]
    if len(s)==0:
        print(f"  {sess}: 0 bars")
        continue
    inv = s.copy(); inv["fwd_pip"] = inv["fwd_inv"]
    inv_floor = s[s.m_cert >= 0.50].copy(); inv_floor["fwd_pip"] = -inv_floor["fwd_pip"]
    print(f"  {sess.upper()} natural:                 {s['fwd_pip'].mean():+.3f}p WR={100*(s['fwd_pip']>0).mean():.1f}% n={len(s)}")
    print(f"  {sess.upper()} inverted:                {s['fwd_inv'].mean():+.3f}p WR={100*(s['fwd_inv']>0).mean():.1f}% n={len(s)}")
    print(f"  {sess.upper()} inverted + floor 0.50:   {inv_floor['fwd_pip'].mean():+.3f}p WR={100*(inv_floor['fwd_pip']>0).mean():.1f}% n={len(inv_floor)}")
    print()
