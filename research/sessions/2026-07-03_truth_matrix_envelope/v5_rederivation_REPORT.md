# V5 TAINT RE-DERIVATION REPORT

**Date:** 2026-07-03
**Device:** Mini CPYQTH294R
**Data source:** ~/qtl-discovery-8yr/features/ (rebuilt 2026-07-03, mtime >= Jul 2)
**Elapsed:** 12.6s

---

## EXECUTIVE VERDICT SUMMARY

| # | Item | Tainted Claim | Clean Result | Verdict |
|---|------|---------------|--------------|---------|
| 1 | Per-cell profile audit | 38/48 → reversion; mean lift +0.0802 | mean lift +0.0107; best AUC 0.4984 | **PROFILES MARGINALLY MATTER** |
| 2 | aroonosc_h1 ±3.57 aggregator | 16/6 sign table survives | 2/48 cells directional | **DEAD** |
| 3a | EUR_JPY/ny/short willr [-85,-7] | n=1360 +8.48p 70.2% WR | KEEP n=10055 +0.07p 47.8% WR | **DEFENSIBLE** |
| 3b | AUD_USD/london/short kc_up [-15,0] | +4.22p 69% WR | KEEP n=8391 -0.05p 49.2% WR | **DEFENSIBLE** |
| 4 | atr_h1_rel>1.6 — wrong-way 16/32 cells | 16/32 wrong-way → invert | KEEP=16, OFF=16, INVERT=16 per cell | **SEE PER-CELL TABLE** |
| 5 | AUD_USD/ny long+short disable (ΔAUC=-0.032) | Both negative | long ΔAUC=-0.0022 short ΔAUC=-0.0022 | **long: EVIDENCE-GONE / short: EVIDENCE-GONE** |
| 6 | QTL 12-cell candidates (willr/cci/efi) | Tainted thresholds never wired | PERSISTENT=4 FLICKER=8 | **FRESH TABLE BELOW** |

---

## ITEM 1: PER-CELL DIRECTION PROFILE AUDIT (2026 bars only)

### BEFORE (tainted)
- 38/48 cells → reversion assignment
- Claimed mean AUC lift if switched: **+0.0802**

### AFTER (clean)
- Cells with sufficient 2026 data: **48/48**
- Mean BEST AUC across all cells: **0.4984** (0.50 = coin flip)
- Mean CURRENT assignment AUC: **0.4877**
- Mean profile spread (max-min AUC within cell): **0.0149**
- Cells where best AUC < 0.52 (near coin-flip): **40**
- Mismatches (current ≠ best_2026 profile): **36**
- Mean lift if switched to best 2026 profile: **+0.0107**

### Interpretation
Some profile differentiation survives on clean data. See per-cell table.

### Top 20 cells by profile spread
```
   pair session direction     current_profile best_profile  current_auc  best_auc  profile_spread  lift_if_switched  mismatch
USD_JPY  london     short             default    reversion       0.4659    0.5013          0.0369            0.0355      True
USD_JPY  london      long             default    reversion       0.4659    0.5013          0.0369            0.0355      True
EUR_JPY      ny     short             default    reversion       0.4757    0.5039          0.0289            0.0282      True
EUR_JPY      ny      long continuation_strong    reversion       0.4750    0.5039          0.0289            0.0289      True
USD_CAD      ny      long           reversion    reversion       0.5296    0.5296          0.0272            0.0000     False
USD_CAD      ny     short             default    reversion       0.5045    0.5296          0.0272            0.0251      True
EUR_USD      ny     short           reversion    reversion       0.5284    0.5284          0.0251            0.0000     False
EUR_USD      ny      long             default    reversion       0.5033    0.5284          0.0251            0.0251      True
GBP_USD      ny      long             default    reversion       0.5159    0.5405          0.0245            0.0245      True
GBP_USD      ny     short           reversion    reversion       0.5405    0.5405          0.0245            0.0000     False
EUR_JPY    asia      long continuation_strong    reversion       0.5005    0.5182          0.0243            0.0177      True
EUR_JPY    asia     short continuation_strong    reversion       0.5005    0.5182          0.0243            0.0177      True
USD_JPY      ny     short continuation_strong    reversion       0.4777    0.5012          0.0234            0.0234      True
USD_JPY      ny      long continuation_strong    reversion       0.4777    0.5012          0.0234            0.0234      True
USD_CHF      ny      long           reversion    reversion       0.5211    0.5211          0.0231            0.0000     False
USD_CHF      ny     short             default    reversion       0.4985    0.5211          0.0231            0.0226      True
AUD_USD  london     short             default    reversion       0.4702    0.4890          0.0188            0.0188      True
AUD_USD  london      long             default    reversion       0.4702    0.4890          0.0188            0.0188      True
AUD_USD      ny     short           reversion    reversion       0.5174    0.5174          0.0176            0.0000     False
AUD_USD      ny      long           reversion    reversion       0.5174    0.5174          0.0176            0.0000     False
```

---

## ITEM 2: AROONOSC_H1 AGGREGATOR (±3.57 threshold)

### BEFORE (tainted)
- Threshold ±3.57 with 16/6 sign table (16 cells direction-aligned, 6 opposed)

### AFTER (clean — all 8yr data)
- Threshold ±3.57 directionally survives: **2/48 cells**
- Mean |WR delta| (extremes vs. neutral): **0.0138**
- Long cells where aroon>thresh helps: **1/24**
- Short cells where aroon>thresh hurts: **1/24**

### Verdict: **DEAD**

### Per-cell detail
```
   pair session direction  wr_aroon_gt_thresh  wr_aroon_lt_neg_thresh  wr_delta_abs  threshold_survives_for_direction  fresh_2026_thresh fresh_2026_side
AUD_JPY    asia      long              0.5073                  0.5251        0.0178                             False            60.7143              gt
AUD_JPY    asia     short              0.4927                  0.4749        0.0178                             False            60.7143             lte
AUD_JPY  london      long              0.5101                  0.5191        0.0090                             False             3.5714             lte
AUD_JPY  london     short              0.4899                  0.4809        0.0090                             False             3.5714              gt
AUD_JPY      ny      long              0.5081                  0.5249        0.0169                             False            39.2857             lte
AUD_JPY      ny     short              0.4919                  0.4751        0.0169                             False            39.2857              gt
AUD_USD    asia      long              0.5068                  0.5234        0.0165                             False           -17.8571             lte
AUD_USD    asia     short              0.4932                  0.4766        0.0165                             False           -17.8571              gt
AUD_USD  london      long              0.4966                  0.5113        0.0147                             False            -3.5714             lte
AUD_USD  london     short              0.5034                  0.4887        0.0147                             False            -3.5714              gt
AUD_USD      ny      long              0.4980                  0.5172        0.0192                             False             3.5714             lte
AUD_USD      ny     short              0.5020                  0.4828        0.0192                             False             3.5714              gt
EUR_JPY    asia      long              0.5028                  0.5294        0.0266                             False           -10.7143              gt
EUR_JPY    asia     short              0.4972                  0.4706        0.0266                             False           -10.7143             lte
EUR_JPY  london      long              0.5169                  0.5160        0.0009                              True            -3.5714             lte
EUR_JPY  london     short              0.4831                  0.4840        0.0009                              True            -3.5714              gt
EUR_JPY      ny      long              0.5091                  0.5279        0.0188                             False             3.5714             lte
EUR_JPY      ny     short              0.4909                  0.4721        0.0188                             False             3.5714              gt
EUR_USD    asia      long              0.4982                  0.5080        0.0098                             False           -17.8571             lte
EUR_USD    asia     short              0.5018                  0.4920        0.0098                             False           -17.8571              gt
EUR_USD  london      long              0.4908                  0.5040        0.0133                             False            17.8571             lte
EUR_USD  london     short              0.5092                  0.4960        0.0133                             False            17.8571              gt
EUR_USD      ny      long              0.5011                  0.5173        0.0162                             False             3.5714             lte
EUR_USD      ny     short              0.4989                  0.4827        0.0162                             False             3.5714              gt
GBP_USD    asia      long              0.4930                  0.5079        0.0149                             False            17.8571             lte
GBP_USD    asia     short              0.5070                  0.4921        0.0149                             False            17.8571              gt
GBP_USD  london      long              0.4998                  0.5058        0.0060                             False            25.0000             lte
GBP_USD  london     short              0.5002                  0.4942        0.0060                             False            25.0000              gt
GBP_USD      ny      long              0.5054                  0.5103        0.0049                             False            10.7143              gt
GBP_USD      ny     short              0.4946                  0.4897        0.0049                             False            10.7143             lte
USD_CAD    asia      long              0.4908                  0.5030        0.0123                             False           -75.0000             lte
USD_CAD    asia     short              0.5092                  0.4970        0.0123                             False           -75.0000              gt
USD_CAD  london      long              0.4970                  0.5136        0.0166                             False           -46.4286             lte
USD_CAD  london     short              0.5030                  0.4864        0.0166                             False           -46.4286              gt
USD_CAD      ny      long              0.4845                  0.4960        0.0115                             False            -3.5714             lte
USD_CAD      ny     short              0.5155                  0.5040        0.0115                             False            -3.5714              gt
USD_CHF    asia      long              0.5050                  0.5131        0.0081                             False           -32.1429             lte
USD_CHF    asia     short              0.4950                  0.4869        0.0081                             False           -32.1429              gt
USD_CHF  london      long              0.4971                  0.5028        0.0058                             False             3.5714             lte
USD_CHF  london     short              0.5029                  0.4972        0.0058                             False             3.5714              gt
USD_CHF      ny      long              0.4878                  0.5010        0.0132                             False           -82.1429             lte
USD_CHF      ny     short              0.5122                  0.4990        0.0132                             False           -82.1429              gt
USD_JPY    asia      long              0.5049                  0.5245        0.0196                             False           -10.7143             lte
USD_JPY    asia     short              0.4951                  0.4755        0.0196                             False           -10.7143              gt
USD_JPY  london      long              0.5155                  0.5258        0.0103                             False             3.5714             lte
USD_JPY  london     short              0.4845                  0.4742        0.0103                             False             3.5714              gt
USD_JPY      ny      long              0.5013                  0.5286        0.0273                             False            10.7143             lte
USD_JPY      ny     short              0.4987                  0.4714        0.0273                             False            10.7143              gt
```

---

## ITEM 3: LIVE GATE THRESHOLDS

### 3a: EUR_JPY/ny/short — willr_m5 in [-85, -7] (DISABLED CELL — for the record)

#### BEFORE (tainted)
- KEEP n=1360 mean=+8.48p WR=70.2%

#### AFTER (clean 2026 data)
| Segment | n | mean pip | WR% |
|---------|---|----------|-----|
| ALL | 12790 | -0.044 | 47.4 |
| KEEP (willr in [-85,-7]) | 10055 | +0.065 | 47.8 |
| BLOCKED | 2735 | -0.442 | 45.9 |

Fresh decision-stump threshold: **-75.019 (gt)** — fires WR=49.0% (n=9927), doesnt WR=41.9%

willr_m5 percentiles in EUR_JPY/ny 2026: {'p10': -88.688, 'p25': -72.129, 'p50': -45.147, 'p75': -21.462, 'p90': -8.824}

**Verdict:** DEFENSIBLE — filter still improves outcomes on clean data

(Note: EUR_JPY/ny/short is currently DISABLED for live trading. This threshold is for the record only.)

---

### 3b: AUD_USD/london/short — kc_up_dist_pips in [-15, 0] (LIVE LOCKED CELL — 6W1L broker support)

#### BEFORE (tainted)
- KEEP mean=+4.22p WR=69% vs deep-below (<-20) LOSING -4.02p/54%

#### AFTER (clean 2026 data)
| Segment | n | mean pip | WR% |
|---------|---|----------|-----|
| ALL | 9922 | -0.217 | 49.0 |
| KEEP (kc_up in [-15,0]) | 8391 | -0.054 | 49.2 |
| BLOCKED | 1531 | -1.110 | 47.9 |

Fresh decision-stump threshold: **-13.6459 (gt)** — fires WR=49.6% (n=8913), doesnt WR=43.8%

kc_up percentiles in AUD_USD/london 2026: {'p10': -13.736, 'p25': -9.496, 'p50': -5.971, 'p75': -3.175, 'p90': -0.667}

**Verdict:** DEFENSIBLE — filter still improves outcomes on clean data. Live range [-15,0] appears structurally sound.

---

## ITEM 4: ATR_H1_RELATIVE > 1.6 GLOBAL RULES

### BEFORE (tainted)
- Claimed wrong-way in 16/32 cells (50%)

### AFTER (clean data — all years)
- **KEEP:** 16 cells (triggered → higher WR, rule adds value)
- **OFF:** 16 cells (neutral, WR delta < ±1pp)
- **INVERT:** 16 cells (triggered → lower WR, rule is wrong-way)

### Per-cell recommendation table
```
   pair session direction  n_triggered  trigger_rate  wr_when_triggered  wr_when_not_triggered  wr_delta recommendation
AUD_JPY    asia     short         2213        0.0120             0.4487                 0.4819   -0.0332         INVERT
AUD_JPY  london     short         2284        0.0141             0.4750                 0.4868   -0.0117         INVERT
AUD_USD    asia     short         1514        0.0083             0.4379                 0.4877   -0.0498         INVERT
AUD_USD  london     short         1303        0.0081             0.4006                 0.4987   -0.0981         INVERT
EUR_JPY    asia     short         2568        0.0139             0.4533                 0.4866   -0.0333         INVERT
EUR_JPY      ny     short         4887        0.0236             0.4391                 0.4809   -0.0418         INVERT
EUR_USD  london     short          792        0.0049             0.4457                 0.5030   -0.0573         INVERT
EUR_USD      ny     short         4533        0.0220             0.4589                 0.4911   -0.0323         INVERT
GBP_USD  london      long          840        0.0052             0.4881                 0.5007   -0.0126         INVERT
GBP_USD      ny      long         4161        0.0201             0.4850                 0.5094   -0.0244         INVERT
USD_CAD    asia      long         1286        0.0070             0.4829                 0.4993   -0.0164         INVERT
USD_CAD  london      long          802        0.0050             0.3778                 0.5051   -0.1273         INVERT
USD_CHF    asia     short         1160        0.0065             0.4655                 0.4901   -0.0246         INVERT
USD_CHF  london      long          977        0.0061             0.4698                 0.5017   -0.0319         INVERT
USD_CHF      ny      long         3997        0.0196             0.4633                 0.4949   -0.0315         INVERT
USD_JPY    asia     short         3169        0.0172             0.4632                 0.4884   -0.0252         INVERT
AUD_JPY    asia      long         2213        0.0120             0.5513                 0.5181    0.0332           KEEP
AUD_JPY  london      long         2284        0.0141             0.5250                 0.5132    0.0117           KEEP
AUD_USD    asia      long         1514        0.0083             0.5621                 0.5123    0.0498           KEEP
AUD_USD  london      long         1303        0.0081             0.5994                 0.5013    0.0981           KEEP
EUR_JPY    asia      long         2568        0.0139             0.5467                 0.5134    0.0333           KEEP
EUR_JPY      ny      long         4887        0.0236             0.5609                 0.5191    0.0418           KEEP
EUR_USD  london      long          792        0.0049             0.5543                 0.4970    0.0573           KEEP
EUR_USD      ny      long         4533        0.0220             0.5411                 0.5089    0.0323           KEEP
GBP_USD  london     short          840        0.0052             0.5119                 0.4993    0.0126           KEEP
GBP_USD      ny     short         4161        0.0201             0.5150                 0.4906    0.0244           KEEP
USD_CAD    asia     short         1286        0.0070             0.5171                 0.5007    0.0164           KEEP
USD_CAD  london     short          802        0.0050             0.6222                 0.4949    0.1273           KEEP
USD_CHF    asia      long         1160        0.0065             0.5345                 0.5099    0.0246           KEEP
USD_CHF  london     short          977        0.0061             0.5302                 0.4983    0.0319           KEEP
USD_CHF      ny     short         3997        0.0196             0.5367                 0.5051    0.0315           KEEP
USD_JPY    asia      long         3169        0.0172             0.5368                 0.5116    0.0252           KEEP
AUD_JPY      ny      long         3369        0.0163             0.5233                 0.5174    0.0059            OFF
AUD_JPY      ny     short         3369        0.0163             0.4767                 0.4826   -0.0059            OFF
AUD_USD      ny      long         2595        0.0127             0.5037                 0.5069   -0.0032            OFF
AUD_USD      ny     short         2595        0.0127             0.4963                 0.4931    0.0032            OFF
EUR_JPY  london      long         2766        0.0171             0.5163                 0.5159    0.0004            OFF
EUR_JPY  london     short         2766        0.0171             0.4837                 0.4841   -0.0004            OFF
EUR_USD    asia      long         1450        0.0079             0.5103                 0.5020    0.0083            OFF
EUR_USD    asia     short         1450        0.0079             0.4897                 0.4980   -0.0083            OFF
GBP_USD    asia      long          995        0.0054             0.5075                 0.5003    0.0072            OFF
GBP_USD    asia     short          995        0.0054             0.4925                 0.4997   -0.0072            OFF
USD_CAD      ny      long         3618        0.0175             0.4804                 0.4887   -0.0083            OFF
USD_CAD      ny     short         3618        0.0175             0.5196                 0.5113    0.0083            OFF
USD_JPY  london      long         3072        0.0190             0.5127                 0.5196   -0.0069            OFF
USD_JPY  london     short         3072        0.0190             0.4873                 0.4804    0.0069            OFF
USD_JPY      ny      long         6121        0.0296             0.5105                 0.5132   -0.0027            OFF
USD_JPY      ny     short         6121        0.0296             0.4895                 0.4868    0.0027            OFF
```

**Note:** This is a per-cell whitelist RECOMMENDATION — no live changes. Cells marked INVERT on clean data were already identified as wrong-way in the tainted run; the question is how many survive that conclusion.

---

## ITEM 5: AUD_USD/NY DISABLE EVIDENCE

### BEFORE (tainted)
- Disable basis: ΔAUC = -0.032 for BOTH long and short (tainted XGB on contaminated parquets)
- Zero live trades in either direction (too new to have broker evidence)

### AFTER (clean data — chronological 70/30)

| Direction | AUC baseline | AUC full | ΔAUC clean | Tainted ΔAUC | Verdict |
|-----------|-------------|---------|------------|--------------|---------|
| long | 0.5419 | 0.5397 | -0.0022 | -0.032 | **EVIDENCE-GONE** |
| short | 0.5419 | 0.5397 | -0.0022 | -0.032 | **EVIDENCE-GONE** |

---

## ITEM 6: QTL 12-CELL CANDIDATE THRESHOLDS (willr_m5 / cci_m5 / efi)

### BEFORE (tainted)
- All thresholds were fits on tainted parquets. Never wired to live bot.

### AFTER (clean — 2026-fit primary, 8yr drift context)

**Drift classification:**
- REGIME: 48
- FLICKER: 8
- PERSISTENT: 4

**Rule:** PERSISTENT = same direction 2026 vs 8yr, <20% threshold shift → candidate for wiring.
FLICKER = direction flips → do NOT wire.
REGIME = same direction, >20% threshold shift → wire 2026 threshold, flag for re-check after 3-month rollover.

### Full candidate table
```
   pair session direction           feature      drift  thresh_2026 side_2026  wr_delta_2026  n_fires_2026  thresh_8yr  wr_delta_8yr
AUD_JPY  london      long          q_cci_m5    FLICKER    -163.6374        gt         0.0383          9299     85.9498        0.0201
AUD_JPY  london     short          q_cci_m5    FLICKER    -163.6374       lte         0.0383           650     85.9498        0.0201
AUD_JPY      ny      long             q_efi    FLICKER       3.0878        gt         0.0440          3560     -0.3885        0.0296
AUD_JPY      ny     short             q_efi    FLICKER       3.0878       lte         0.0440          9215     -0.3885        0.0296
EUR_JPY  london      long          q_cci_m5    FLICKER     171.0185        gt         0.0609           567     43.8118        0.0155
EUR_JPY  london      long     q_aroonosc_h1    FLICKER      -3.5714       lte         0.0282          3387      3.5714        0.0017
EUR_JPY  london     short          q_cci_m5    FLICKER     171.0185       lte         0.0609          9384     43.8118        0.0155
EUR_JPY  london     short     q_aroonosc_h1    FLICKER      -3.5714        gt         0.0282          6564      3.5714        0.0017
EUR_JPY      ny      long     q_aroonosc_h1 PERSISTENT       3.5714       lte         0.0159          7503      3.5714        0.0185
EUR_JPY      ny     short     q_aroonosc_h1 PERSISTENT       3.5714        gt         0.0159          5287      3.5714        0.0185
USD_CAD      ny      long q_kc_up_dist_pips PERSISTENT      -4.7432       lte         0.0846          8876     -5.3391        0.0459
USD_CAD      ny     short q_kc_up_dist_pips PERSISTENT      -4.7432        gt         0.0846          3899     -5.3391        0.0459
AUD_JPY  london      long        q_willr_m5     REGIME      -5.2016       lte         0.0574          9287    -72.5832        0.0240
AUD_JPY  london      long             q_efi     REGIME      10.4613       lte         0.0478          9422      2.7511        0.0306
AUD_JPY  london      long q_kc_up_dist_pips     REGIME     -26.1715       lte         0.0654           554     -3.6226        0.0239
AUD_JPY  london      long     q_aroonosc_h1     REGIME       3.5714       lte         0.0480          5806     -3.5714        0.0091
AUD_JPY  london     short        q_willr_m5     REGIME      -5.2016        gt         0.0574           662    -72.5832        0.0240
AUD_JPY  london     short             q_efi     REGIME      10.4613        gt         0.0478           527      2.7511        0.0306
AUD_JPY  london     short q_kc_up_dist_pips     REGIME     -26.1715        gt         0.0654          9395     -3.6226        0.0239
AUD_JPY  london     short     q_aroonosc_h1     REGIME       3.5714        gt         0.0480          4143     -3.5714        0.0091
AUD_JPY      ny      long        q_willr_m5     REGIME     -89.8805       lte         0.0658          1135    -20.4432        0.0379
AUD_JPY      ny      long          q_cci_m5     REGIME    -161.2961       lte         0.0517           745     -7.5276        0.0334
AUD_JPY      ny      long q_kc_up_dist_pips     REGIME      -6.8398       lte         0.0767          7727     -5.6767        0.0511
AUD_JPY      ny      long     q_aroonosc_h1     REGIME      39.2857       lte         0.0483          8691     10.7143        0.0162
AUD_JPY      ny     short        q_willr_m5     REGIME     -89.8805        gt         0.0658         11640    -20.4432        0.0379
AUD_JPY      ny     short          q_cci_m5     REGIME    -161.2961        gt         0.0517         12030     -7.5276        0.0334
AUD_JPY      ny     short q_kc_up_dist_pips     REGIME      -6.8398        gt         0.0767          5048     -5.6767        0.0511
AUD_JPY      ny     short     q_aroonosc_h1     REGIME      39.2857        gt         0.0483          4084     10.7143        0.0162
EUR_JPY  london      long        q_willr_m5     REGIME     -66.4782       lte         0.0305          3012    -49.4269        0.0138
EUR_JPY  london      long             q_efi     REGIME     -13.5275       lte         0.0597           831     -0.2361        0.0148
EUR_JPY  london      long q_kc_up_dist_pips     REGIME     -17.4874       lte         0.0425          2185     -7.4513        0.0156
EUR_JPY  london     short        q_willr_m5     REGIME     -66.4782        gt         0.0305          6939    -49.4269        0.0138
EUR_JPY  london     short             q_efi     REGIME     -13.5275        gt         0.0597          9120     -0.2361        0.0148
EUR_JPY  london     short q_kc_up_dist_pips     REGIME     -17.4874        gt         0.0425          7766     -7.4513        0.0156
EUR_JPY      ny      long        q_willr_m5     REGIME     -75.0190       lte         0.0708          2863    -54.8272        0.0406
EUR_JPY      ny      long          q_cci_m5     REGIME      15.6874       lte         0.0492          6458     22.4762        0.0408
EUR_JPY      ny      long             q_efi     REGIME      -2.9017       lte         0.0644          3165      0.0054        0.0357
EUR_JPY      ny      long q_kc_up_dist_pips     REGIME      -7.7688       lte         0.0817          7748     -3.8334        0.0665
EUR_JPY      ny     short        q_willr_m5     REGIME     -75.0190        gt         0.0708          9927    -54.8272        0.0406
EUR_JPY      ny     short          q_cci_m5     REGIME      15.6874        gt         0.0492          6332     22.4762        0.0408
EUR_JPY      ny     short             q_efi     REGIME      -2.9017        gt         0.0644          9625      0.0054        0.0357
EUR_JPY      ny     short q_kc_up_dist_pips     REGIME      -7.7688        gt         0.0817          5042     -3.8334        0.0665
GBP_USD  london      long        q_willr_m5     REGIME      -7.2508       lte         0.0352          9077    -85.0169        0.0200
GBP_USD  london      long          q_cci_m5     REGIME     168.0204       lte         0.0695          9262    123.1365        0.0185
GBP_USD  london      long             q_efi     REGIME      -0.1833       lte         0.0691           518     -0.0060        0.0142
GBP_USD  london      long q_kc_up_dist_pips     REGIME       1.5972       lte         0.0976          9385     -3.1889        0.0222
GBP_USD  london      long     q_aroonosc_h1     REGIME      25.0000       lte         0.0512          6623     -3.5714        0.0084
GBP_USD  london     short        q_willr_m5     REGIME      -7.2508        gt         0.0352           877    -85.0169        0.0200
GBP_USD  london     short          q_cci_m5     REGIME     168.0204        gt         0.0695           692    123.1365        0.0185
GBP_USD  london     short             q_efi     REGIME      -0.1833        gt         0.0691          9436     -0.0060        0.0142
GBP_USD  london     short q_kc_up_dist_pips     REGIME       1.5972        gt         0.0976           569     -3.1889        0.0222
GBP_USD  london     short     q_aroonosc_h1     REGIME      25.0000        gt         0.0512          3331     -3.5714        0.0084
USD_CAD      ny      long        q_willr_m5     REGIME     -31.8428       lte         0.0784          8257    -69.4786        0.0439
USD_CAD      ny      long          q_cci_m5     REGIME      79.1612       lte         0.0708          9162    -38.2591        0.0401
USD_CAD      ny      long             q_efi     REGIME      -0.0035       lte         0.0351          5362     -0.0024        0.0277
USD_CAD      ny      long     q_aroonosc_h1     REGIME      -3.5714       lte         0.0311          4685    -17.8571        0.0134
USD_CAD      ny     short        q_willr_m5     REGIME     -31.8428        gt         0.0784          4518    -69.4786        0.0439
USD_CAD      ny     short          q_cci_m5     REGIME      79.1612        gt         0.0708          3613    -38.2591        0.0401
USD_CAD      ny     short             q_efi     REGIME      -0.0035        gt         0.0351          7413     -0.0024        0.0277
USD_CAD      ny     short     q_aroonosc_h1     REGIME      -3.5714        gt         0.0311          8090    -17.8571        0.0134
```

---

## FILES

| File | Contents |
|------|---------|
| item1_profile_audit.csv | Per-cell AUC by profile, 2026 only |
| item2_aroonosc_h1.csv | aroonosc ±3.57 per cell + fresh threshold |
| item3_gate_thresholds.json | EUR_JPY willr + AUD_USD kc_up detailed stats |
| item4_atr_h1_rel.csv | atr_h1_rel>1.6 per-cell recommendation |
| item5_audusd_ny_disable.json | AUD_USD/ny disable ΔAUC evidence |
| item6_qtl_candidates.csv | QTL 12-cell fresh threshold table |
| rederivation_summary.json | Machine-readable verdicts for all 6 items |

*Generated by generate_report.py — V5 Taint Re-Derivation 2026-07-03*
