# V5 broker validation — fresh OANDA candles + 1H forward truth

**Date:** 2026-06-21  
**Methodology change:** STOP using realized P/L for entry-indicator decisions. Exit logic (ratchet/SL/manual) changes constantly and contaminates the signal. Use **1H forward pip move** computed from fresh OANDA M5 candles as the ground truth for "did the entry indicator predict direction."

## Method

For each of 118 OANDA closed trades since 2026-06-12:
1. Fetched fresh M5/H1/D candles from OANDA spanning [entry-36h, entry+90min] (89,251 total candles)
2. Computed 30+ indicators (V5 baseline + qtl candidates) at the entry bar
3. Measured `forward_1h_pip_signed = (close[t+12] - close[t]) / pip * dir_sign`
4. Per cell: correlated each indicator with the forward 1H pip move

This is **broker truth** — indicator values come from OANDA candles, outcome comes from OANDA price action, no bot involvement.

## Key finding: realized P/L vs 1H forward direction MATCH only 68%

In 32% of trades, the bot's realized win/loss is OPPOSITE direction from what the market did over 1H after entry:
- **Bot wins where market went against**: ratchet captured a small reversal then market reversed back (good)
- **Bot loses where market went with**: SL hit during a wiggle before continuation (bad)

This is why we can't use realized P/L to evaluate ENTRY signals — exit logic distorts the picture.

## Per-cell broker validation (n≥3 trades, sorted by 1H forward pip)

### CELLS THE BROKER VALIDATES AS POSITIVE (real entry edge)

| Cell | n | broker fwd 1H mean | realized $ avg | top broker feature | Matrix Δ_2026 | Agreement |
|---|---:|---:|---:|---|---:|---|
| **USD_CAD/ny/long** | 7 | **+6.61p** ⭐ | +$30 | atr_5m +0.951 | -0.009 | ⚠ matrix says negative but broker confirms cell wins |
| **EUR_USD/london/short** | 7 | **+6.31p** ⭐ | +$20 | q_efi -0.762 | -0.003 | matrix understates; broker confirms winner |
| AUD_JPY/london/long | 3 | +2.83p | -$39 | — | -0.003 | broker positive, realized lost (exit logic) |
| **AUD_JPY/asia/short** | 6 | **+1.80p** | -$1 | h1_ret_1bar -0.747 | -0.001 | matrix understates; broker confirms winner |

### CELLS THE BROKER VALIDATES AS NEGATIVE (no entry edge)

| Cell | n | broker fwd 1H mean | realized $ avg | Matrix Δ_2026 | Agreement |
|---|---:|---:|---:|---:|---|
| **GBP_USD/ny/long** | 4 | **-10.53p** | -$61 | **+0.0014** | ⚠ matrix DISAGREES (positive); NOT disabled |
| **EUR_JPY/ny/long** | 3 | -6.27p | -$82 | -0.005 | matrix agrees; flag for disable |
| **EUR_JPY/london/short** | 4 | -5.73p | -$104 | -0.0003 | matrix agrees; **DISABLED** ✓ |
| **AUD_USD/asia/short** | 4 | -3.38p | -$39 | +0.003 | partial disagreement |
| **USD_CHF/ny/long** | 5 | -2.42p | -$122 | -0.001 | matrix agrees; flag for disable |
| USD_JPY/asia/short | 6 | -1.78p | +$42 | +0.013 | matrix says positive; realized actually positive |
| AUD_JPY/london/short | 3 | -1.23p | -$92 | -0.003 | matrix agrees; flag for disable |
| GBP_USD/ny/short | 5 | -0.40p | -$62 | +0.001 | partial conflict |
| USD_CHF/london/long | 6 | -0.48p (flat) | +$29 | -0.008 | matrix neg, broker flat; realized positive (exit logic captures) |

## Application of Brock's instructions

### EUR_JPY/london/short — DISABLED ✓
- Broker: n=4, mean fwd 1H **-5.73p**, q_hurst_m5 correlation -0.969
- Matrix: delta_auc_2026 = -0.0003, recent_3yr = -0.0004 (both negative)
- Both agree → **added to disabled_cells**

### GBP_USD/ny/long — NOT disabled (matrix conflict)
- Broker: n=4, mean fwd 1H **-10.53p**, q_adosc/q_chop_h1/q_mfi correlations +0.98 (n=4 — high but small sample)
- Matrix: delta_auc_2026 = +0.0014, recent_3yr_mean = +0.0052 (POSITIVE), 2024+2025+2026 all positive
- Matrix says winning regime → respecting matrix per Brock's instruction
- **Flagged for monitoring** — if next 5 trades confirm losing, re-evaluate

## Disabled cells after this update (6 total)

```python
disabled_cells = [
    ("AUD_USD","ny","long"),     # 8yr ML -0.032, 1 trade lost -$293
    ("AUD_USD","ny","short"),    # 8yr ML -0.032, 0 trades
    ("USD_CHF","london","short"),# 8yr ML -0.008, 0 trades
    ("USD_CAD","ny","short"),    # 8yr ML -0.009, 0 trades
    ("EUR_USD","ny","long"),     # 8yr ML -0.013, 0 trades
    ("EUR_JPY","london","short"),# 8yr ML -0.0003, broker -5.73p fwd (n=4)  ← NEW
]
```

## Other matrix-broker-confirmed-negative cells (NOT auto-disabled)

These would qualify under the same criteria as EUR_JPY/london/short. Brock only specified the two cells; surfacing here for decision:

| Cell | Matrix Δ_2026 | Broker fwd 1H | Realized | Worth considering |
|---|---:|---:|---:|---|
| EUR_JPY/ny/long | -0.005 | -6.27p (n=3) | -$82/trade | matrix + broker both negative |
| USD_CHF/ny/long | -0.001 | -2.42p (n=5) | -$122/trade | matrix flat, broker mildly neg, realized strong neg |
| AUD_JPY/london/short | -0.003 | -1.23p (n=3) | -$92/trade | matrix neg, broker mildly neg |
| AUD_JPY/ny/long | -0.0004 | NaN (n=3 manual closes) | -$136/trade | matrix neg, no broker fwd data |

## Methodology change effective this commit

**Going forward, entry-indicator config decisions use BROKER 1H FORWARD PIP, not realized P/L.**

Why:
1. Exit logic (ratchet/SL/TP/manual) is constantly being tuned
2. Realized P/L confounds entry quality with exit choices
3. The bot's 32% realized-vs-forward mismatch shows exit logic CHANGES outcomes
4. Indicator/profile decisions should be testable independent of exit logic

The MATRIX (8yr ML) and BROKER 1H FWD agree on direction in most cells. When they disagree, broker wins for cells with n≥4 trades; matrix wins for cells with n<4.

## Master matrix updated with broker columns

`master_matrix_with_broker.csv` adds these columns to the prior matrix:
- `broker_n_trades` — count of OANDA trades for this cell
- `broker_n_bot_exit` — count of clean (non-manual) trades
- `broker_fwd_1h_mean_pip` — actual 1H forward pip move (signed in trade direction)
- `broker_fwd_1h_wr` — % of trades where 1H forward went in trade direction
- `broker_realized_mean_pl` — reference: actual USD P/L
- `broker_top_fwd_corr_feature` — strongest |corr| feature per cell
- `broker_top_fwd_corr` — that correlation value
- `broker_disagrees_matrix` — True if matrix positive but broker n≥3 negative
- `recommend_disable_v2` — True if matrix negative AND broker negative

## Sample size honesty

- n=3-7 per cell is too small for stable correlations. The 0.95+ correlations in some cells are likely spurious at this scale.
- 32% realized-vs-forward mismatch suggests exit logic is dominant in single-trade outcomes
- Need 50+ trades per cell for high-confidence per-cell stats — currently only ~4 cells have n≥6
- Per Brock's instruction to update monthly cron with broker data, this will accumulate properly going forward

## What changed in live V5

- `config/playmaker_config.json`: disabled_cells now has 6 entries (was 5)
- V5 restarted 2026-06-21 06:16 UTC, healthy
- No new SIGNAL since restart (market closed Sun)

## Open follow-ups

- **Update monthly cron** to call `v5_pull_oanda_trades.py` + `v5_fetch_trade_candles.py` + `v5_broker_validation.py` instead of journal-based matrix
- **GBP_USD/ny/long**: monitor next 5 trades. If broker fwd 1H stays negative, the matrix's positive ΔAUC is wrong for current regime.
- **The 4 other matrix+broker-agree-negative cells** (EUR_JPY/ny/long, USD_CHF/ny/long, AUD_JPY/london/short, AUD_JPY/ny/long) — Brock decision pending.
