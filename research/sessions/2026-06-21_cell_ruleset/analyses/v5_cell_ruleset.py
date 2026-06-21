"""Consolidate every weekend finding into ONE per-cell ruleset.

Each (pair x session x direction) = 48 cells gets its validated rules:
  - direction_profile   (8yr ML: reversion/continuation_strong/default)
  - momentum_sign       (NY=fade, overlap=trend, london=mostly fade, asia=mixed) — walk-forward
  - align_sign          (per-session: confirm vs fade) — from align_resolution
  - broker_fwd_pip      (actual 1H forward in cell direction, real trades)
  - broker_n            (real trade count)
  - enabled             (not in disabled_cells)
  - evidence_tier       (STRONG = walk-forward + broker agree; MODERATE = one source; WEAK = ML only)
  - recommended_rule    (one-line action)

Joins the CSVs already produced this weekend. V5's 3-session scheme
(asia 22-5, london 6-12, ny 13-21). Note: the finer tests show ny(13-21)
LUMPS a trend-y overlap (13-14) with a fade-y late-ny (15-21) — flagged.
"""
import json, subprocess
from pathlib import Path
import numpy as np
import pandas as pd

def assert_on_mini():
    s = subprocess.run(["system_profiler","SPHardwareDataType"], capture_output=True, text=True).stdout
    if "CPYQTH294R" not in s: raise RuntimeError("NOT ON MINI")
    print("✓ device verified: Mini CPYQTH294R")
assert_on_mini()

ROOT = Path.home() / "qtl-discovery-8yr"
OUT = ROOT / "cell_ruleset"; OUT.mkdir(exist_ok=True)
PAIRS = ["AUD_JPY","AUD_USD","EUR_JPY","EUR_USD","GBP_USD","USD_CAD","USD_CHF","USD_JPY"]
SESS = ["asia","london","ny"]; DIRS = ["long","short"]

# ── Load all artifacts ──
mm = pd.read_csv(ROOT/"master_matrix"/"master_matrix_with_broker.csv")   # per cell-direction
fs = pd.read_csv(ROOT/"percell_exhaustion"/"percell_fast_slow_summary.csv")  # per pair-session momentum
ar = pd.read_csv(ROOT/"align_resolution"/"align_resolution.csv")          # per pair-session-direction align (4-session)

# disabled cells (from the live config on EC2 — hardcode the known 10)
DISABLED = {("AUD_USD","ny","long"),("AUD_USD","ny","short"),("USD_CHF","london","short"),
            ("USD_CAD","ny","short"),("EUR_USD","ny","long"),("EUR_JPY","london","short"),
            ("EUR_JPY","ny","long"),("USD_CHF","ny","long"),("AUD_JPY","london","short"),
            ("AUD_JPY","ny","long")}
INVERT_SHADOW = {("GBP_USD","ny"),("EUR_JPY","ny")}

# momentum sign per (pair, session): fade if fast_test<0, trend if >0 (use V5 ny = the fade-dominant ny)
mom = {}
for _,r in fs.iterrows():
    mom[(r['pair'], r['session'])] = {'fast': r['fast_test'], 'slow': r['slow_test'],
                                       'stable': bool(r['fast_stable'])}

# align sign per (pair, session, direction): corr_cont sign (use V5's 3 sessions; map overlap->ny)
# align_resolution sessions are asia/london/ny/overlap. V5 ny = ny+overlap merged.
align = {}
for _,r in ar.iterrows():
    s = 'ny' if r['session']=='overlap' else r['session']
    key = (r['pair'], s, r['direction'])
    align.setdefault(key, []).append(r['corr_cont'])
align_sign = {k: np.mean(v) for k,v in align.items()}

rows = []
for pair in PAIRS:
    for sess in SESS:
        for dr in DIRS:
            cell = (pair, sess, dr)
            mmr = mm[(mm.pair==pair)&(mm.session==sess)&(mm.direction==dr)]
            profile = mmr['current_profile'].iloc[0] if len(mmr) else 'default'
            delta_auc = mmr['delta_auc_2026'].iloc[0] if len(mmr) else None
            recent3 = mmr['recent_3yr_mean'].iloc[0] if len(mmr) and 'recent_3yr_mean' in mmr else None
            bfwd = mmr['broker_fwd_1h_mean_pip'].iloc[0] if len(mmr) and 'broker_fwd_1h_mean_pip' in mmr else None
            bn = mmr['broker_n_bot_exit'].iloc[0] if len(mmr) and 'broker_n_bot_exit' in mmr else None
            m = mom.get((pair,sess), {})
            mom_fast = m.get('fast'); mom_stable = m.get('stable', False)
            mom_sign = 'FADE' if (mom_fast is not None and mom_fast<0) else ('TREND' if mom_fast is not None and mom_fast>0 else '?')
            al = align_sign.get(cell)
            al_sign = 'FADE' if (al is not None and al<0) else ('CONFIRM' if al is not None and al>0 else '?')
            enabled = cell not in DISABLED
            invert_shadow = (pair,sess) in INVERT_SHADOW

            # evidence tier: do momentum(walk-forward) + broker forward agree?
            broker_neg = (bfwd is not None and not pd.isna(bfwd) and bfwd < 0)
            broker_pos = (bfwd is not None and not pd.isna(bfwd) and bfwd > 0)
            mom_fade = (mom_fast is not None and mom_fast < 0 and mom_stable)
            if (broker_neg and mom_fade) or (broker_pos and mom_fast is not None and mom_fast>0):
                tier = 'STRONG'   # broker + walk-forward agree
            elif bn is not None and not pd.isna(bn) and bn >= 3:
                tier = 'MODERATE' # has real trades
            else:
                tier = 'WEAK'     # ML only

            # recommended rule
            if not enabled:
                rule = f"DISABLED (ML {delta_auc:+.3f}" + (f", broker {bfwd:+.1f}p" if broker_neg or broker_pos else "") + ")"
            elif invert_shadow:
                rule = f"SHADOW-INVERT (broker fade, testing inverted)"
            elif mom_sign=='FADE' and mom_stable:
                rule = f"profile={profile}; FADE momentum (NY/london fade, walk-forward stable)"
            elif mom_sign=='TREND':
                rule = f"profile={profile}; TREND momentum (overlap/asia confirm)"
            else:
                rule = f"profile={profile}; momentum neutral"

            rows.append({'pair':pair,'session':sess,'direction':dr,
                         'enabled':enabled,'invert_shadow':invert_shadow,
                         'direction_profile':profile,
                         'momentum_sign':mom_sign,'momentum_stable':mom_stable,
                         'align_sign':al_sign,
                         'ml_delta_auc_2026':round(delta_auc,4) if delta_auc is not None and not pd.isna(delta_auc) else None,
                         'broker_fwd_pip':round(bfwd,2) if bfwd is not None and not pd.isna(bfwd) else None,
                         'broker_n':int(bn) if bn is not None and not pd.isna(bn) else 0,
                         'evidence_tier':tier,
                         'recommended_rule':rule})

df = pd.DataFrame(rows)
df.to_csv(OUT/'cell_ruleset.csv', index=False)
print(f"\n=== V5 PER-CELL RULESET (48 cells) ===")
print(f"  enabled: {df['enabled'].sum()}/48  |  disabled: {(~df['enabled']).sum()}  |  invert-shadow: {df['invert_shadow'].sum()}")
print(f"  evidence: STRONG {len(df[df.evidence_tier=='STRONG'])}, MODERATE {len(df[df.evidence_tier=='MODERATE'])}, WEAK {len(df[df.evidence_tier=='WEAK'])}")

print(f"\n=== STRONG-evidence cells (broker + walk-forward agree) ===")
strong = df[df.evidence_tier=='STRONG']
print(strong[['pair','session','direction','enabled','direction_profile','momentum_sign','align_sign','broker_fwd_pip','broker_n','recommended_rule']].to_string(index=False))

print(f"\n=== Full ruleset (compact) ===")
print(df[['pair','session','direction','enabled','direction_profile','momentum_sign','align_sign','broker_fwd_pip','evidence_tier']].to_string(index=False))
print(f"\n→ {OUT}/cell_ruleset.csv")
