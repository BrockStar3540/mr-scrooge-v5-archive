#!/usr/bin/env python3
"""Parse V5 journalctl trade log into a per-trade table."""
import sys, re
from pathlib import Path

src = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/v5_trades_today.log")
trades = {}
for line in src.read_text().splitlines():
    m_ts = re.search(r"(\d{2}:\d{2}:\d{2})", line)
    ts = m_ts.group(1) if m_ts else "?"
    m_en = re.search(r"ENTERED (\S+) (\S+) @ ([\d.]+).*trade_id=(\d+)", line)
    m_rt = re.search(r"RATCHET (\S+) \| peak=([\d.]+)p sl=([\d.\-]+)p.*trade_id=(\d+)", line)
    m_ex = re.search(r"EXIT.*?(\w+_\w+) \| trade_id=(\d+) \| approx_net=([\d.\-]+)p", line)
    if m_en:
        tid = m_en.group(4)
        trades[tid] = {"pair": m_en.group(1), "dir": m_en.group(2),
                       "entry_ts": ts, "ratchets": [],
                       "exit_net": None, "exit_ts": None}
    elif m_rt:
        tid = m_rt.group(4)
        if tid in trades:
            trades[tid]["ratchets"].append((ts, float(m_rt.group(2)), float(m_rt.group(3))))
    elif m_ex:
        tid = m_ex.group(2)
        if tid in trades:
            trades[tid]["exit_net"] = float(m_ex.group(3))
            trades[tid]["exit_ts"] = ts

print(f"{'tid':<6}{'pair':<10}{'dir':<7}{'in':<10}{'out':<10}{'arm@peak':<11}{'lock@sl':<10}{'net_pips':<11}note")
print("-" * 105)
losers_no_arm, losers_armed, winners = [], [], []
for tid in sorted(trades.keys(), key=int):
    t = trades[tid]
    if t["exit_net"] is None:
        continue
    armpeak = t["ratchets"][0][1] if t["ratchets"] else None
    armlock = t["ratchets"][0][2] if t["ratchets"] else None
    arm_str = f"+{armpeak:.1f}p" if armpeak else "—"
    lock_str = f"+{armlock:.1f}p" if armlock else "—"
    net = t["exit_net"]
    note = ""
    if not t["ratchets"] and net < -10:
        note = "NEVER ARMED (peak<+7.5)"
        losers_no_arm.append((tid, t, net))
    elif net > 0:
        winners.append((tid, t, net))
    else:
        losers_armed.append((tid, t, net))
    print(f"{tid:<6}{t['pair']:<10}{t['dir']:<7}{t['entry_ts']:<10}{t['exit_ts']:<10}{arm_str:<11}{lock_str:<10}{net:>+8.2f}p  {note}")

w_sum = sum(n for _, _, n in winners)
nl_sum = sum(n for _, _, n in losers_no_arm)
al_sum = sum(n for _, _, n in losers_armed)
total = w_sum + nl_sum + al_sum
print(f"\n=== summary ===")
print(f"  Winners (armed→locked):     {len(winners):>2}  avg=+{w_sum/max(len(winners),1):.2f}p  pips_sum={w_sum:+.2f}p")
print(f"  Losers (NEVER ARMED, -SL):  {len(losers_no_arm):>2}  avg={nl_sum/max(len(losers_no_arm),1):+.2f}p  pips_sum={nl_sum:+.2f}p")
print(f"  Losers (armed but lost):    {len(losers_armed):>2}  avg={al_sum/max(len(losers_armed),1):+.2f}p  pips_sum={al_sum:+.2f}p")
print(f"  TOTAL closed: {len(winners)+len(losers_no_arm)+len(losers_armed)}  net_pips={total:+.2f}p")
