# H55: the Setups quality filter on history (NOT proof)

Written by `research/setups_filter.py` on 2026-11-17 14:50 UTC. Registered in `research/HYPOTHESES.md` (H55, 17 Nov 2026 12:03 UTC) before any H55 code or number existed. Paper only; history the engine's authors have lived through; the sealed holdout (from 2025-11-11) was never read.

**Plainly:** a history read can reject an idea, never prove one. A pass would only be a reason to propose a forward paper filter book (S1-F) to the owner.

## Verdict

- **F1: NO PASS.** AUC first half 0.760 (in-sample), second half 0.520.
- **F2: NO PASS.** AUC first half 0.917 (in-sample), second half 0.566.

Judged with scikit-learn 1.9.1.

## Pass table (second half, 2023-06-07 to the seal)

| Rule | F1 | F1 pass | F2 | F2 pass |
|---|---|---|---|---|
| (1) mean R per sent signal, kept > all, block bootstrap p <= 0.025 | kept -0.0355 vs all -0.0274 (diff -0.0082), p = 0.6490 | no | kept -0.0202 vs all -0.0274 (diff +0.0072), p = 0.3706 | no |
| (2) kept total R > 0 | -39.1 R | no | -21.7 R | no |
| (3) kept mean > all mean in >= 5 markets with >= 20 signals | 4 of 8 (BTCUSDT, XAGUSD, USDJPY, BRENT) | no | 4 of 8 (BTCUSDT, ETHUSDT, WTI, BRENT) | no |
| (4) kept >= 100 second-half signals | 1101 | yes | 1077 | yes |

## Population

5034 signals: 2858 first half (entries before 2023-06-07), 2176 second half. Label base rate (followable > 0 R after costs; a no fill = 0): 25.0% all, 25.3% first half, 24.7% second half. Markets present: BTCUSDT, ETHUSDT, XAUUSD, XAGUSD, USDJPY, SPX, WTI, BRENT.

| Market | Book trades | Signals | Opened and closed in the fill bar (never a signal) | Not a signal | Unresolved at the seal | Open at the seal | Replay window |
|---|---|---|---|---|---|---|---|
| BTCUSDT | 867 | 861 | 6 | 0 | 0 | 1 | 2020-02-05 00:00 .. 2025-11-10 23:45 |
| ETHUSDT | 873 | 867 | 6 | 0 | 0 | 1 | 2020-02-05 00:00 .. 2025-11-10 23:45 |
| XAUUSD | 638 | 637 | 1 | 0 | 0 | 1 | 2020-02-21 19:00 .. 2025-11-10 23:45 |
| XAGUSD | 582 | 582 | 0 | 0 | 0 | 1 | 2020-02-21 19:00 .. 2025-11-10 23:45 |
| USDJPY | 636 | 633 | 3 | 0 | 0 | 1 | 2020-04-08 21:00 .. 2025-11-10 23:45 |
| WTI | 634 | 634 | 0 | 0 | 0 | 1 | 2020-02-27 19:00 .. 2025-11-10 21:45 |
| BRENT | 623 | 621 | 2 | 0 | 0 | 1 | 2020-02-27 19:00 .. 2025-11-10 21:45 |
| SPX | 199 | 199 | 0 | 0 | 0 | 1 | 2021-01-12 17:30 .. 2025-11-10 20:45 |

### All signals, first half (followable R per sent signal; book R beside)

| Market | Signals | Fill rate | Mean R | Total R | Win rate (filled) | Book mean R | Book total R | Book win rate |
|---|---|---|---|---|---|---|---|---|
| all | 2858 | 59.2% | -0.0010 | -3.0 | 42.7% | +0.0021 | +6.0 | 42.5% |
| BTCUSDT | 451 | 61.4% | -0.0063 | -2.8 | 44.0% | +0.0325 | +14.6 | 45.7% |
| ETHUSDT | 515 | 65.2% | +0.0378 | +19.5 | 46.1% | +0.0571 | +29.4 | 46.0% |
| XAUUSD | 396 | 59.3% | -0.0471 | -18.6 | 40.0% | -0.1011 | -40.0 | 37.9% |
| XAGUSD | 337 | 59.3% | +0.0130 | +4.4 | 44.5% | -0.0583 | -19.6 | 41.8% |
| USDJPY | 336 | 56.8% | -0.0343 | -11.5 | 39.3% | -0.0102 | -3.4 | 40.8% |
| SPX | 95 | 53.7% | -0.0744 | -7.1 | 33.3% | +0.0524 | +5.0 | 41.1% |
| WTI | 381 | 55.6% | +0.0355 | +13.5 | 43.9% | +0.0293 | +11.2 | 42.0% |
| BRENT | 347 | 55.0% | -0.0009 | -0.3 | 40.8% | +0.0257 | +8.9 | 41.5% |

No-fill reasons: window 1093, target 35, stop 33, model 4.

### All signals, second half (followable R per sent signal; book R beside)

| Market | Signals | Fill rate | Mean R | Total R | Win rate (filled) | Book mean R | Book total R | Book win rate |
|---|---|---|---|---|---|---|---|---|
| all | 2176 | 60.2% | -0.0274 | -59.6 | 41.0% | -0.0280 | -61.0 | 41.5% |
| BTCUSDT | 410 | 57.6% | -0.1064 | -43.6 | 36.4% | -0.1706 | -69.9 | 38.3% |
| ETHUSDT | 352 | 59.7% | +0.0002 | +0.1 | 43.3% | +0.0131 | +4.6 | 44.9% |
| XAUUSD | 241 | 60.2% | +0.0073 | +1.8 | 44.1% | +0.1085 | +26.1 | 44.8% |
| XAGUSD | 245 | 61.6% | -0.0089 | -2.2 | 42.4% | +0.0115 | +2.8 | 42.9% |
| USDJPY | 297 | 61.6% | +0.0424 | +12.6 | 44.3% | +0.0791 | +23.5 | 44.1% |
| SPX | 104 | 62.5% | +0.1750 | +18.2 | 53.8% | +0.1567 | +16.3 | 46.2% |
| WTI | 253 | 63.6% | -0.1154 | -29.2 | 34.2% | -0.1069 | -27.0 | 36.4% |
| BRENT | 274 | 58.0% | -0.0628 | -17.2 | 38.4% | -0.1363 | -37.3 | 37.6% |

No-fill reasons: window 819, stop 30, target 16, model 1.

## F1: kept and skipped

Cut = median of first-half predictions = 0.44957; kept 50.0% of first-half and 50.6% of second-half signals. AUC first half 0.760 (in-sample), second half 0.520.
Fitted with scikit-learn LogisticRegression (lbfgs): 116 iterations; warnings: 'penalty' was deprecated in version 1.8 and will be removed in 1.10. To avoid this warning, leave 'penalty' set to its default value and use 'l1_ratio' or 'C' instead. Use l1_ratio=0 instead of penalt.

**followable R, first half**

| Set | Signals | Fill rate | Mean R | Total R | Win rate |
|---|---|---|---|---|---|
| all | 2858 | 59.2% | -0.0010 | -3.0 | 42.7% |
| kept | 1429 | 66.2% | +0.2325 | +332.2 | 60.3% |
| skipped | 1429 | 52.3% | -0.2346 | -335.2 | 20.5% |
| BTCUSDT kept | 256 | 66.0% | +0.1848 | +47.3 | 59.8% |
| BTCUSDT skipped | 195 | 55.4% | -0.2571 | -50.1 | 19.4% |
| ETHUSDT kept | 318 | 70.4% | +0.2362 | +75.1 | 59.4% |
| ETHUSDT skipped | 197 | 56.9% | -0.2824 | -55.6 | 19.6% |
| XAUUSD kept | 177 | 67.8% | +0.1929 | +34.1 | 60.0% |
| XAUUSD skipped | 219 | 52.5% | -0.2410 | -52.8 | 19.1% |
| XAGUSD kept | 173 | 69.4% | +0.2648 | +45.8 | 60.8% |
| XAGUSD skipped | 164 | 48.8% | -0.2526 | -41.4 | 20.0% |
| USDJPY kept | 149 | 63.1% | +0.1580 | +23.5 | 54.3% |
| USDJPY skipped | 187 | 51.9% | -0.1875 | -35.1 | 24.7% |
| SPX kept | 30 | 63.3% | +0.3780 | +11.3 | 63.2% |
| SPX skipped | 65 | 49.2% | -0.2832 | -18.4 | 15.6% |
| WTI kept | 180 | 64.4% | +0.2416 | +43.5 | 61.2% |
| WTI skipped | 201 | 47.8% | -0.1490 | -30.0 | 22.9% |
| BRENT kept | 146 | 57.5% | +0.3524 | +51.5 | 67.9% |
| BRENT skipped | 201 | 53.2% | -0.2576 | -51.8 | 19.6% |

**followable R, second half**

| Set | Signals | Fill rate | Mean R | Total R | Win rate |
|---|---|---|---|---|---|
| all | 2176 | 60.2% | -0.0274 | -59.6 | 41.0% |
| kept | 1101 | 61.1% | -0.0355 | -39.1 | 42.3% |
| skipped | 1075 | 59.3% | -0.0190 | -20.4 | 39.6% |
| BTCUSDT kept | 269 | 59.5% | -0.0755 | -20.3 | 38.8% |
| BTCUSDT skipped | 141 | 53.9% | -0.1654 | -23.3 | 31.6% |
| ETHUSDT kept | 224 | 58.0% | -0.0398 | -8.9 | 42.3% |
| ETHUSDT skipped | 128 | 62.5% | +0.0702 | +9.0 | 45.0% |
| XAUUSD kept | 128 | 62.5% | +0.0041 | +0.5 | 48.8% |
| XAUUSD skipped | 113 | 57.5% | +0.0110 | +1.2 | 38.5% |
| XAGUSD kept | 136 | 59.6% | +0.0158 | +2.1 | 45.7% |
| XAGUSD skipped | 109 | 64.2% | -0.0397 | -4.3 | 38.6% |
| USDJPY kept | 79 | 60.8% | +0.1290 | +10.2 | 54.2% |
| USDJPY skipped | 218 | 61.9% | +0.0111 | +2.4 | 40.7% |
| SPX kept | 34 | 64.7% | +0.0790 | +2.7 | 50.0% |
| SPX skipped | 70 | 61.4% | +0.2216 | +15.5 | 55.8% |
| WTI kept | 139 | 66.9% | -0.1648 | -22.9 | 32.3% |
| WTI skipped | 114 | 59.6% | -0.0552 | -6.3 | 36.8% |
| BRENT kept | 92 | 64.1% | -0.0278 | -2.5 | 42.4% |
| BRENT skipped | 182 | 54.9% | -0.0806 | -14.7 | 36.0% |

**BOOK R (as b_targets booked it), first half**

| Set | Signals | Fill rate | Mean R | Total R | Win rate |
|---|---|---|---|---|---|
| all | 2858 | - | +0.0021 | +6.0 | 42.5% |
| kept | 1429 | - | +0.2592 | +370.5 | 56.0% |
| skipped | 1429 | - | -0.2550 | -364.5 | 29.0% |
| BTCUSDT kept | 256 | - | +0.2543 | +65.1 | 58.6% |
| BTCUSDT skipped | 195 | - | -0.2587 | -50.5 | 28.7% |
| ETHUSDT kept | 318 | - | +0.2469 | +78.5 | 55.3% |
| ETHUSDT skipped | 197 | - | -0.2492 | -49.1 | 31.0% |
| XAUUSD kept | 177 | - | +0.1662 | +29.4 | 52.5% |
| XAUUSD skipped | 219 | - | -0.3171 | -69.4 | 26.0% |
| XAGUSD kept | 173 | - | +0.2975 | +51.5 | 57.2% |
| XAGUSD skipped | 164 | - | -0.4336 | -71.1 | 25.6% |
| USDJPY kept | 149 | - | +0.2068 | +30.8 | 53.0% |
| USDJPY skipped | 187 | - | -0.1831 | -34.2 | 31.0% |
| SPX kept | 30 | - | +0.6201 | +18.6 | 63.3% |
| SPX skipped | 65 | - | -0.2097 | -13.6 | 30.8% |
| WTI kept | 180 | - | +0.2513 | +45.2 | 55.0% |
| WTI skipped | 201 | - | -0.1694 | -34.0 | 30.3% |
| BRENT kept | 146 | - | +0.3516 | +51.3 | 58.2% |
| BRENT skipped | 201 | - | -0.2111 | -42.4 | 29.4% |

**BOOK R (as b_targets booked it), second half**

| Set | Signals | Fill rate | Mean R | Total R | Win rate |
|---|---|---|---|---|---|
| all | 2176 | - | -0.0280 | -61.0 | 41.5% |
| kept | 1101 | - | -0.0270 | -29.8 | 43.5% |
| skipped | 1075 | - | -0.0290 | -31.2 | 39.3% |
| BTCUSDT kept | 269 | - | -0.1356 | -36.5 | 40.1% |
| BTCUSDT skipped | 141 | - | -0.2374 | -33.5 | 34.8% |
| ETHUSDT kept | 224 | - | +0.0105 | +2.4 | 46.4% |
| ETHUSDT skipped | 128 | - | +0.0175 | +2.2 | 42.2% |
| XAUUSD kept | 128 | - | +0.1420 | +18.2 | 50.8% |
| XAUUSD skipped | 113 | - | +0.0704 | +8.0 | 38.1% |
| XAGUSD kept | 136 | - | +0.0263 | +3.6 | 44.1% |
| XAGUSD skipped | 109 | - | -0.0071 | -0.8 | 41.3% |
| USDJPY kept | 79 | - | +0.2010 | +15.9 | 51.9% |
| USDJPY skipped | 218 | - | +0.0349 | +7.6 | 41.3% |
| SPX kept | 34 | - | +0.0276 | +0.9 | 41.2% |
| SPX skipped | 70 | - | +0.2194 | +15.4 | 48.6% |
| WTI kept | 139 | - | -0.1914 | -26.6 | 34.5% |
| WTI skipped | 114 | - | -0.0038 | -0.4 | 38.6% |
| BRENT kept | 92 | - | -0.0831 | -7.6 | 42.4% |
| BRENT skipped | 182 | - | -0.1631 | -29.7 | 35.2% |

Top ten inputs (coefficient on the standardised input):

1. `eld_bear_1h` -0.49452
2. `ich_tk_1h` -0.44426
3. `market_SPX` -0.37855
4. `id_vwap_d` -0.35731
5. `ha_strong_1h` 0.35523
6. `vx_level` 0.34782
7. `t1_stop_ratio` -0.34641
8. `trixz_1h` -0.34525
9. `tr_1w` 0.33622
10. `hull_pos_1h` -0.33506

## F2: kept and skipped

Cut = median of first-half predictions = 0.23908; kept 50.0% of first-half and 49.5% of second-half signals. AUC first half 0.917 (in-sample), second half 0.566.
Fitted with scikit-learn HistGradientBoostingClassifier: 200 iterations.

**followable R, first half**

| Set | Signals | Fill rate | Mean R | Total R | Win rate |
|---|---|---|---|---|---|
| all | 2858 | 59.2% | -0.0010 | -3.0 | 42.7% |
| kept | 1429 | 71.5% | +0.3535 | +505.2 | 65.9% |
| skipped | 1429 | 47.0% | -0.3556 | -508.2 | 7.3% |
| BTCUSDT kept | 282 | 67.4% | +0.2419 | +68.2 | 62.1% |
| BTCUSDT skipped | 169 | 51.5% | -0.4204 | -71.0 | 4.6% |
| ETHUSDT kept | 327 | 74.6% | +0.3101 | +101.4 | 62.7% |
| ETHUSDT skipped | 188 | 48.9% | -0.4356 | -81.9 | 2.2% |
| XAUUSD kept | 187 | 71.7% | +0.3080 | +57.6 | 65.7% |
| XAUUSD skipped | 209 | 48.3% | -0.3647 | -76.2 | 5.9% |
| XAGUSD kept | 166 | 72.9% | +0.3803 | +63.1 | 67.8% |
| XAGUSD skipped | 171 | 46.2% | -0.3435 | -58.7 | 8.9% |
| USDJPY kept | 129 | 72.9% | +0.4271 | +55.1 | 69.1% |
| USDJPY skipped | 207 | 46.9% | -0.3219 | -66.6 | 10.3% |
| SPX kept | 26 | 69.2% | +0.5523 | +14.4 | 72.2% |
| SPX skipped | 69 | 47.8% | -0.3105 | -21.4 | 12.1% |
| WTI kept | 163 | 73.0% | +0.4531 | +73.9 | 68.9% |
| WTI skipped | 218 | 42.7% | -0.2768 | -60.3 | 11.8% |
| BRENT kept | 149 | 68.5% | +0.4802 | +71.5 | 71.6% |
| BRENT skipped | 198 | 44.9% | -0.3630 | -71.9 | 5.6% |

**followable R, second half**

| Set | Signals | Fill rate | Mean R | Total R | Win rate |
|---|---|---|---|---|---|
| all | 2176 | 60.2% | -0.0274 | -59.6 | 41.0% |
| kept | 1077 | 60.3% | -0.0202 | -21.7 | 46.1% |
| skipped | 1099 | 60.1% | -0.0345 | -37.9 | 36.0% |
| BTCUSDT kept | 260 | 54.6% | -0.0416 | -10.8 | 42.3% |
| BTCUSDT skipped | 150 | 62.7% | -0.2186 | -32.8 | 27.7% |
| ETHUSDT kept | 228 | 59.6% | +0.0226 | +5.2 | 49.3% |
| ETHUSDT skipped | 124 | 59.7% | -0.0410 | -5.1 | 32.4% |
| XAUUSD kept | 120 | 60.0% | -0.0754 | -9.1 | 45.8% |
| XAUUSD skipped | 121 | 60.3% | +0.0894 | +10.8 | 42.5% |
| XAGUSD kept | 119 | 61.3% | -0.0243 | -2.9 | 46.6% |
| XAGUSD skipped | 126 | 61.9% | +0.0057 | +0.7 | 38.5% |
| USDJPY kept | 140 | 64.3% | -0.0186 | -2.6 | 46.7% |
| USDJPY skipped | 157 | 59.2% | +0.0968 | +15.2 | 41.9% |
| SPX kept | 30 | 70.0% | +0.0405 | +1.2 | 52.4% |
| SPX skipped | 74 | 59.5% | +0.2296 | +17.0 | 54.5% |
| WTI kept | 93 | 68.8% | -0.0016 | -0.1 | 43.8% |
| WTI skipped | 160 | 60.6% | -0.1816 | -29.1 | 27.8% |
| BRENT kept | 87 | 58.6% | -0.0295 | -2.6 | 47.1% |
| BRENT skipped | 187 | 57.8% | -0.0784 | -14.7 | 34.3% |

**BOOK R (as b_targets booked it), first half**

| Set | Signals | Fill rate | Mean R | Total R | Win rate |
|---|---|---|---|---|---|
| all | 2858 | - | +0.0021 | +6.0 | 42.5% |
| kept | 1429 | - | +0.3428 | +489.8 | 59.4% |
| skipped | 1429 | - | -0.3386 | -483.8 | 25.5% |
| BTCUSDT kept | 282 | - | +0.2777 | +78.3 | 58.5% |
| BTCUSDT skipped | 169 | - | -0.3768 | -63.7 | 24.3% |
| ETHUSDT kept | 327 | - | +0.3040 | +99.4 | 57.8% |
| ETHUSDT skipped | 188 | - | -0.3723 | -70.0 | 25.5% |
| XAUUSD kept | 187 | - | +0.2401 | +44.9 | 57.2% |
| XAUUSD skipped | 209 | - | -0.4064 | -84.9 | 20.6% |
| XAGUSD kept | 166 | - | +0.3795 | +63.0 | 62.0% |
| XAGUSD skipped | 171 | - | -0.4833 | -82.6 | 22.2% |
| USDJPY kept | 129 | - | +0.3968 | +51.2 | 61.2% |
| USDJPY skipped | 207 | - | -0.2638 | -54.6 | 28.0% |
| SPX kept | 26 | - | +0.5083 | +13.2 | 61.5% |
| SPX skipped | 69 | - | -0.1195 | -8.2 | 33.3% |
| WTI kept | 163 | - | +0.4105 | +66.9 | 59.5% |
| WTI skipped | 218 | - | -0.2557 | -55.7 | 28.9% |
| BRENT kept | 149 | - | +0.4893 | +72.9 | 62.4% |
| BRENT skipped | 198 | - | -0.3233 | -64.0 | 25.8% |

**BOOK R (as b_targets booked it), second half**

| Set | Signals | Fill rate | Mean R | Total R | Win rate |
|---|---|---|---|---|---|
| all | 2176 | - | -0.0280 | -61.0 | 41.5% |
| kept | 1077 | - | -0.0009 | -0.9 | 46.9% |
| skipped | 1099 | - | -0.0546 | -60.0 | 36.1% |
| BTCUSDT kept | 260 | - | -0.0740 | -19.2 | 44.2% |
| BTCUSDT skipped | 150 | - | -0.3380 | -50.7 | 28.0% |
| ETHUSDT kept | 228 | - | +0.0924 | +21.1 | 52.2% |
| ETHUSDT skipped | 124 | - | -0.1328 | -16.5 | 31.5% |
| XAUUSD kept | 120 | - | -0.0622 | -7.5 | 45.0% |
| XAUUSD skipped | 121 | - | +0.2777 | +33.6 | 44.6% |
| XAGUSD kept | 119 | - | +0.0494 | +5.9 | 47.9% |
| XAGUSD skipped | 126 | - | -0.0244 | -3.1 | 38.1% |
| USDJPY kept | 140 | - | +0.0164 | +2.3 | 46.4% |
| USDJPY skipped | 157 | - | +0.1349 | +21.2 | 42.0% |
| SPX kept | 30 | - | -0.0765 | -2.3 | 43.3% |
| SPX skipped | 74 | - | +0.2512 | +18.6 | 47.3% |
| WTI kept | 93 | - | +0.0548 | +5.1 | 45.2% |
| WTI skipped | 160 | - | -0.2008 | -32.1 | 31.2% |
| BRENT kept | 87 | - | -0.0722 | -6.3 | 46.0% |
| BRENT skipped | 187 | - | -0.1661 | -31.1 | 33.7% |

Top ten inputs (total split gain):

1. `t1_stop_ratio` 598.20726
2. `ck_dow_cos` 192.79883
3. `mfi_15m` 116.58893
4. `brd_ethbtc_7d` 98.0109
5. `sr_break` 92.37904
6. `lrc_pos_1h` 91.91988
7. `ma_cross_1h` 88.63142
8. `mass_4h` 88.31725
9. `aro_up_4h` 85.89975
10. `sr_sup_near` 84.03317

## Cross-check only (not judged): the numpy stand-ins

| Stand-in | AUC first | AUC second | Kept (2nd half) | Kept mean R vs all | p | Total kept R | Markets | Would pass | Same keep/skip as the judged variant (1st / 2nd half) |
|---|---|---|---|---|---|---|---|---|---|
| F1_numpy | 0.760 | 0.520 | 1103 | -0.0364 vs -0.0274 | 0.6639 | -40.1 | 4 of 8 | no | 99.9% / 99.7% |
| F2_numpy | 0.915 | 0.565 | 1068 | -0.0167 vs -0.0274 | 0.3027 | -17.8 | 4 of 8 | no | 93.8% / 92.4% |

## Method notes and deviations

- Judged with scikit-learn 1.9.1 in the separate research Python setup (`/data/venv-research`; the engine's `/data/venv` unchanged), as decided in the H55 library note (17 Nov 2026 12:36 UTC, before any real-data number). The numpy stand-ins written while scikit-learn was missing are shown beside as a cross-check only.
- Missing input cells (replaced by the first-half mean): 0 (none).
- Bar A is the slot after the fill bar (the earliest the page shows a b_targets position, H53 amendment); a trade that opens and closes in its own fill bar is never a signal; a trade still open at the seal, or a followable trade unfinished at the seal, is left out (counts above).
- Stop and Target-1 distances are the book's plan at the decision close (entry = that close), because the fill price is the next bar's open. The decision bar is the fill bar minus 1 minus the market's fill delay.
- The odds are walked from the engine's birth (2020-01-01) as H36 replayed the books; the live step walks the last 240 days.
- Markets present: BTCUSDT, ETHUSDT, XAUUSD, XAGUSD, USDJPY, SPX, WTI, BRENT.
