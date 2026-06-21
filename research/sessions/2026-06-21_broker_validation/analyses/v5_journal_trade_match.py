"""Parse V5 journal SIGNAL + ENTERED + EXIT lines, match to OANDA closed trades by
trade_id. For each trade, capture what V5 ACTUALLY decided at signal time
(score, d_cert, m_cert, expected_pips, vol_regime, profile fields if present).

Tag each trade by V5 era:
  - V5_v1: 2026-06-18 19:04 → 2026-06-20 19:44  (direction.py + momentum.py)
  - V5_v2v3: 2026-06-20 19:44 → present         (direction_v2.py + momentum_v3.py)
  - V5_v2v3_enriched: 2026-06-20 onwards with shadow logging  (post a8f3889)

Output:
  /tmp/v5_trades_with_signal.csv
  /tmp/v5_trades_summary.txt
"""
import os, re, subprocess, csv
from datetime import datetime, timezone

V5_CUTOVER     = datetime(2026, 6, 18, 19, 4,  tzinfo=timezone.utc)
V5_V2V3_ON     = datetime(2026, 6, 20, 19, 44, tzinfo=timezone.utc)   # commit 5a29000 deploy
V5_V2V3_ENRICHED = datetime(2026, 6, 20, 19, 48, tzinfo=timezone.utc) # commit a8f3889

def era(ts):
    if ts < V5_CUTOVER: return "V4"
    if ts < V5_V2V3_ON: return "V5_v1"
    if ts < V5_V2V3_ENRICHED: return "V5_v2v3_unenriched"
    return "V5_v2v3"

# Pull full journal since V5 cutover (need sudo? journalctl --user works for ubuntu)
out = subprocess.check_output(
    ["journalctl", "--user", "-u", "mr-scrooge-v5",
     "--since", V5_CUTOVER.isoformat(), "--no-pager", "-o", "cat"],
    env={**os.environ, "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}", "SYSTEMD_PAGER": ""},
    text=True,
)
lines = out.splitlines()
print(f"Journal lines since V5 cutover: {len(lines)}")

# Old SIGNAL: "SIGNAL <pair> <dir> | score=N d_cert=N m_cert=N expected=Np vol=W rivals=N"
# New SIGNAL: ... + "| active_side=X long_prof=X short_prof=X mom_prof=X gates=X cert_boost=X [| shadow_vortex_diff=N shadow_close_pos=N]"
sig_re_new = re.compile(
    r"(\S+ \S+) INFO v5\.engine\s+SIGNAL (\w+) (\w+) \| "
    r"score=([\-\d.]+) d_cert=([\d.]+) m_cert=([\d.]+) expected=([\d.]+)p vol=(\w+) rivals=(\d+)"
    r"(?:\s*\|\s*active_side=(\S+)\s+long_prof=(\S+)\s+short_prof=(\S+)\s+mom_prof=(\S+)\s+gates=(\S+)\s+cert_boost=(\S+))?"
    r"(?:\s*\|\s*shadow_vortex_diff=([\-\d.]+)\s+shadow_close_pos=([\-\d.]+))?"
)
ent_re = re.compile(r"(\S+ \S+) INFO v5\.engine\s+ENTERED (\w+) (\w+) @ ([\d.]+) \| (\d+) units .* trade_id=(\d+)")
exit_re = re.compile(r"(\S+ \S+) INFO v5\.engine\s+EXIT.*? trade_id=(\d+) \| (?:approx_net|net)=([\-\d.]+)p")

signals, entries, exits = [], {}, {}
for line in lines:
    m = sig_re_new.search(line)
    if m:
        g = m.groups()
        try: ts = datetime.strptime(g[0].split(",")[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except Exception: ts = None
        signals.append({
            "ts": ts, "pair": g[1], "direction": g[2],
            "score": float(g[3]), "d_cert": float(g[4]), "m_cert": float(g[5]),
            "expected_pips": float(g[6]), "vol_regime": g[7], "rivals": int(g[8]),
            "active_side": g[9], "long_prof": g[10], "short_prof": g[11], "mom_prof": g[12],
            "gates_passed": g[13], "cert_boost": g[14],
            "shadow_vortex": float(g[15]) if g[15] else None,
            "shadow_close_pos": float(g[16]) if g[16] else None,
        })
        continue
    m = ent_re.search(line)
    if m:
        ts_str, pair, direction, price, units, tid = m.groups()
        try: ts = datetime.strptime(ts_str.split(",")[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except Exception: ts = None
        entries[tid] = {
            "ts": ts, "pair": pair, "direction": direction,
            "fill_price": float(price), "units": int(units), "trade_id": tid,
        }
        continue
    m = exit_re.search(line)
    if m:
        ts_str, tid, net = m.groups()
        try: ts = datetime.strptime(ts_str.split(",")[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except Exception: ts = None
        exits[tid] = {"ts": ts, "net_pips": float(net)}

print(f"\nParsed: {len(signals)} SIGNAL, {len(entries)} ENTERED, {len(exits)} EXIT")
print(f"SIGNAL with v2/v3 fields populated: {sum(1 for s in signals if s['active_side'])}")
print(f"SIGNAL with shadow fields populated: {sum(1 for s in signals if s['shadow_vortex'] is not None)}")

# Match SIGNAL → ENTERED by timestamp ± 2 seconds
matched = []
for tid, ent in entries.items():
    if ent["ts"] is None: continue
    candidates = [s for s in signals
                  if s["ts"] is not None
                  and s["pair"]==ent["pair"]
                  and s["direction"]==ent["direction"]
                  and abs((s["ts"] - ent["ts"]).total_seconds()) < 3]
    sig = candidates[0] if candidates else None
    matched.append({
        "trade_id": tid,
        "pair": ent["pair"], "direction": ent["direction"],
        "entered_ts": ent["ts"].isoformat(),
        "fill_price": ent["fill_price"], "units": ent["units"],
        "era": era(ent["ts"]),
        "signal_matched": sig is not None,
        "score": sig["score"] if sig else None,
        "d_cert": sig["d_cert"] if sig else None,
        "m_cert": sig["m_cert"] if sig else None,
        "expected_pips": sig["expected_pips"] if sig else None,
        "vol_regime": sig["vol_regime"] if sig else None,
        "active_side": sig["active_side"] if sig else None,
        "long_prof": sig["long_prof"] if sig else None,
        "short_prof": sig["short_prof"] if sig else None,
        "mom_prof": sig["mom_prof"] if sig else None,
        "gates_passed": sig["gates_passed"] if sig else None,
        "cert_boost": sig["cert_boost"] if sig else None,
        "shadow_vortex": sig["shadow_vortex"] if sig else None,
        "shadow_close_pos": sig["shadow_close_pos"] if sig else None,
        "exit_pips_journal": exits.get(tid, {}).get("net_pips"),
    })

# Save
out_csv = "/tmp/v5_trades_with_signal.csv"
with open(out_csv, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(matched[0].keys()) if matched else [])
    w.writeheader()
    w.writerows(matched)
print(f"\n→ {out_csv} ({len(matched)} trades)")

# Summary by era
from collections import Counter
era_counts = Counter(r["era"] for r in matched)
print(f"\nTrades by V5 era: {dict(era_counts)}")
sig_match_rate = sum(1 for r in matched if r["signal_matched"]) / max(len(matched), 1) * 100
print(f"SIGNAL match rate: {sig_match_rate:.0f}%")

print(f"\nSummary written to /tmp/v5_trades_summary.txt")
with open("/tmp/v5_trades_summary.txt", "w") as f:
    f.write(f"V5 journal trade-matching summary\n")
    f.write(f"Window: {V5_CUTOVER.isoformat()} → present\n")
    f.write(f"SIGNAL: {len(signals)}, ENTERED: {len(entries)}, EXIT: {len(exits)}\n")
    f.write(f"Matched trades: {len(matched)}\n")
    f.write(f"SIGNAL match rate: {sig_match_rate:.0f}%\n")
    f.write(f"By era: {dict(era_counts)}\n")
