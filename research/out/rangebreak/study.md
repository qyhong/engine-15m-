# H44: range breaks with momentum against the daily ATR budget

PAPER RESEARCH ONLY. Registered 2026-11-16 04:40 UTC (`research/HYPOTHESES.md` H44) before any number. Development data only (rows before 2025-11-11 00:00 UTC; the holdout was not read). Trades from 2020-01-01; first half before 2023-06-07. Written 2026-11-16 04:44 UTC.

Readings from `engine15/sources/adr.py` (`readings`, `breaks`); trades through `playbook.simulate` unchanged (next open, stop 1 x ATR15 from the break close, break-even after 1R, hold 16 bars, each market's own fee a side).

## Verdict: NO PASS

Chosen on the first half: **V4** (prior UTC day, k 1.5, room-left (used < 0.65), half 1R / rest 2R), score -0.0735% a trade.

Pass bar (second half): pooled net > 0 with >= 100 trades: **NO**; net > 0 in >= 5 of 8 markets: **NO** (0: none); PF >= 1.1: **NO**; per trade better than its no-eagle twin (V4_twin): **YES**.

## Variants, pooled over the eight markets

Score = mean over markets (>= 20 first-half trades) of the first-half expectancy after costs.

| id | rule | score | half | trades | won | R before costs | R after costs | PF | per trade (% stake) | net $ |
|---|---|---|---|---|---|---|---|---|---|---|
| V1 | last 24 bars, k 1.5, room-left (used < 0.65), half 1R / rest 2R | -0.0892% | first | 15108 | 43.2% | -0.008 | -0.408 | 0.51 | -0.1028% | -155,345 |
|  |  |  | second | 10969 | 36.8% | -0.043 | -0.624 | 0.32 | -0.1220% | -133,864 |
| V2 | last 24 bars, k 2.0, room-left (used < 0.65), half 1R / rest 2R | -0.0862% | first | 9228 | 43.2% | +0.005 | -0.399 | 0.53 | -0.0984% | -90,787 |
|  |  |  | second | 6592 | 36.5% | -0.045 | -0.634 | 0.33 | -0.1243% | -81,914 |
| V3 | last 12 bars, k 1.5, room-left (used < 0.65), half 1R / rest 2R | -0.0909% | first | 20826 | 42.9% | -0.008 | -0.411 | 0.51 | -0.1047% | -218,101 |
|  |  |  | second | 14785 | 36.9% | -0.034 | -0.620 | 0.33 | -0.1189% | -175,835 |
| V4 | prior UTC day, k 1.5, room-left (used < 0.65), half 1R / rest 2R | -0.0735% | first | 4946 | 47.0% | +0.044 | -0.305 | 0.61 | -0.0769% | -38,018 |
|  |  |  | second | 3504 | 40.0% | -0.042 | -0.512 | 0.38 | -0.1059% | -37,093 |
| V5 | opening range (first 4 bars), k 1.5, room-left (used < 0.65), half 1R / rest 2R | -0.0791% | first | 9986 | 44.9% | +0.018 | -0.372 | 0.55 | -0.0875% | -87,370 |
|  |  |  | second | 7348 | 38.6% | -0.025 | -0.556 | 0.37 | -0.1071% | -78,680 |
| V6 | last 24 bars, k 1.5, room-left (used < 0.65), half 1R / rest at the day's room level | -0.0862% | first | 13388 | 39.9% | +0.006 | -0.393 | 0.54 | -0.0983% | -131,641 |
|  |  |  | second | 9757 | 31.9% | -0.029 | -0.603 | 0.35 | -0.1181% | -115,249 |
| V7 | last 24 bars, k 1.5, exhausted (used >= 1.0), half 1R / rest 2R |  | first | 5169 | 48.9% | +0.024 | -0.204 | 0.66 | -0.1179% | -60,943 |
|  |  |  | second | 3541 | 45.9% | -0.006 | -0.288 | 0.56 | -0.1181% | -41,818 |
| V8 | last 24 bars, k 1.5, no daily filter, half 1R / rest 2R |  | first | 26812 | 45.1% | +0.001 | -0.343 | 0.57 | -0.1063% | -285,109 |
|  |  |  | second | 19074 | 40.0% | -0.031 | -0.506 | 0.42 | -0.1190% | -226,952 |
| V2_twin | last 24 bars, k 2.0, no daily filter, half 1R / rest 2R |  | first | 17004 | 45.5% | +0.019 | -0.326 | 0.60 | -0.1007% | -171,229 |
|  |  |  | second | 12030 | 40.0% | -0.030 | -0.503 | 0.43 | -0.1211% | -145,630 |
| V3_twin | last 12 bars, k 1.5, no daily filter, half 1R / rest 2R |  | first | 35177 | 44.5% | -0.006 | -0.359 | 0.56 | -0.1089% | -383,212 |
|  |  |  | second | 24638 | 39.7% | -0.031 | -0.517 | 0.41 | -0.1179% | -290,532 |
| V4_twin | prior UTC day, k 1.5, no daily filter, half 1R / rest 2R |  | first | 7844 | 47.8% | +0.046 | -0.268 | 0.66 | -0.0762% | -59,733 |
|  |  |  | second | 5575 | 41.9% | -0.029 | -0.440 | 0.45 | -0.1075% | -59,909 |
| V5_twin | opening range (first 4 bars), k 1.5, no daily filter, half 1R / rest 2R |  | first | 12795 | 45.4% | +0.007 | -0.349 | 0.56 | -0.0943% | -120,693 |
|  |  |  | second | 9183 | 39.7% | -0.030 | -0.511 | 0.41 | -0.1100% | -101,007 |
| V6_twin | last 24 bars, k 1.5, no daily filter, half 1R / rest at the day's room level |  | first | 23457 | 43.1% | +0.008 | -0.332 | 0.59 | -0.1038% | -243,395 |
|  |  |  | second | 16692 | 36.9% | -0.022 | -0.490 | 0.44 | -0.1159% | -193,379 |

## Chosen variant V4 vs its no-eagle twin V4_twin and the exhausted contrast V7, per market

| market | half | V4 net $ | V4 per trade | V4 trades | V4_twin net $ | V4_twin per trade | V4_twin trades | V7 net $ | V7 per trade | V7 trades |
|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | first | -12,503 | -0.1817% | 688 | -19,392 | -0.1695% | 1144 | -24,432 | -0.2594% | 942 |
|  | second | -10,352 | -0.2075% | 499 | -17,179 | -0.2103% | 817 | -14,375 | -0.2191% | 656 |
| ETHUSDT | first | -7,934 | -0.1199% | 662 | -14,177 | -0.1269% | 1117 | -23,696 | -0.2463% | 962 |
|  | second | -9,458 | -0.1975% | 479 | -16,476 | -0.1999% | 824 | -17,740 | -0.2541% | 698 |
| XAUUSD | first | -2,039 | -0.0343% | 595 | -3,465 | -0.0349% | 994 | -1,791 | -0.0273% | 655 |
|  | second | -1,302 | -0.0315% | 413 | -2,526 | -0.0355% | 712 | -2,041 | -0.0406% | 502 |
| XAGUSD | first | -4,032 | -0.0693% | 582 | -7,696 | -0.0753% | 1022 | -996 | -0.0154% | 645 |
|  | second | -3,497 | -0.1002% | 349 | -6,593 | -0.1011% | 652 | -3,057 | -0.0623% | 491 |
| USDJPY | first | -999 | -0.0163% | 614 | -1,605 | -0.0162% | 988 | -1,818 | -0.0234% | 776 |
|  | second | -1,054 | -0.0228% | 463 | -1,420 | -0.0201% | 707 | -812 | -0.0161% | 504 |
| SPX | first | -1,440 | -0.0306% | 471 | -2,006 | -0.0347% | 579 | -428 | -0.0360% | 119 |
|  | second | -1,630 | -0.0523% | 312 | -1,905 | -0.0476% | 400 | -476 | -0.0580% | 82 |
| WTI | first | -4,737 | -0.0678% | 699 | -6,177 | -0.0566% | 1092 | -3,395 | -0.0518% | 655 |
|  | second | -5,487 | -0.1045% | 525 | -8,559 | -0.1050% | 815 | -1,919 | -0.0508% | 378 |
| BRENT | first | -4,335 | -0.0683% | 635 | -5,215 | -0.0574% | 908 | -4,388 | -0.1057% | 415 |
|  | second | -4,313 | -0.0930% | 464 | -5,251 | -0.0810% | 648 | -1,399 | -0.0608% | 230 |

## Descriptive: what happens after a break with momentum (pre-cost, events, overlaps allowed)

Forward return in the break direction from the next open, in 15m ATRs (and %); MFE / MAE over the next 16 bars in 15m ATRs; hit = reached +1 ATR15 before -1 ATR15 (same bar = miss; 'neither' left out of the hit rate). Buckets: share of the daily ATR used at the break (room left < 0.65, middle 0.65-1.0, exhausted >= 1.0).

| events | half | bucket | n | fwd 4 (ATR) | fwd 8 | fwd 16 | fwd 16 % | up at 16 | MFE | MAE | hit +1 before -1 | neither |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| box24 k1.5 | first | room left | 16910 | +0.014 | +0.026 | +0.041 | +0.010% | 47.1% | 2.72 | 2.53 | 49.5% | 0.5% |
|  | first | middle | 7971 | +0.002 | +0.018 | +0.023 | -0.039% | 47.8% | 2.64 | 2.44 | 49.2% | 0.5% |
|  | first | exhausted | 5871 | +0.040 | +0.036 | +0.096 | -0.088% | 46.9% | 2.58 | 2.25 | 50.0% | 1.1% |
|  | first | all | 30752 | +0.016 | +0.026 | +0.047 | -0.021% | 47.2% | 2.67 | 2.46 | 49.5% | 0.6% |
|  | second | room left | 12270 | -0.024 | -0.042 | +0.012 | -0.009% | 47.7% | 2.87 | 2.77 | 47.6% | 0.5% |
|  | second | middle | 5520 | -0.004 | -0.005 | -0.021 | +0.001% | 47.8% | 2.62 | 2.53 | 47.6% | 0.8% |
|  | second | exhausted | 3981 | +0.010 | +0.022 | +0.097 | +0.023% | 48.7% | 2.53 | 2.26 | 49.0% | 0.9% |
|  | second | all | 21771 | -0.013 | -0.021 | +0.020 | -0.001% | 47.9% | 2.74 | 2.62 | 47.9% | 0.6% |
|  | all | room left | 29180 | -0.002 | -0.003 | +0.029 | +0.002% | 47.4% | 2.78 | 2.63 | 48.7% | 0.5% |
|  | all | middle | 13491 | -0.001 | +0.009 | +0.005 | -0.023% | 47.8% | 2.63 | 2.48 | 48.6% | 0.7% |
|  | all | exhausted | 9852 | +0.028 | +0.030 | +0.097 | -0.043% | 47.6% | 2.56 | 2.25 | 49.6% | 1.0% |
|  | all | all | 52523 | +0.004 | +0.007 | +0.036 | -0.013% | 47.5% | 2.70 | 2.52 | 48.8% | 0.6% |
| box24 k2.0 | first | room left | 9482 | +0.020 | +0.025 | +0.017 | +0.010% | 47.1% | 2.75 | 2.53 | 49.9% | 0.5% |
|  | first | middle | 4695 | +0.042 | +0.051 | +0.091 | -0.022% | 49.1% | 2.77 | 2.45 | 50.9% | 0.3% |
|  | first | exhausted | 3541 | +0.070 | +0.065 | +0.142 | -0.077% | 48.1% | 2.72 | 2.28 | 50.6% | 0.7% |
|  | first | all | 17718 | +0.036 | +0.040 | +0.062 | -0.016% | 47.8% | 2.75 | 2.46 | 50.3% | 0.5% |
|  | second | room left | 6783 | -0.003 | -0.047 | -0.051 | -0.013% | 47.1% | 2.92 | 2.84 | 47.1% | 0.4% |
|  | second | middle | 3254 | -0.015 | -0.007 | -0.017 | -0.007% | 47.9% | 2.71 | 2.60 | 47.9% | 0.4% |
|  | second | exhausted | 2482 | +0.032 | +0.004 | +0.097 | +0.044% | 48.9% | 2.66 | 2.37 | 48.9% | 0.7% |
|  | second | all | 12519 | +0.001 | -0.026 | -0.013 | -0.000% | 47.6% | 2.82 | 2.69 | 47.7% | 0.5% |
|  | all | room left | 16265 | +0.010 | -0.005 | -0.011 | +0.001% | 47.1% | 2.82 | 2.66 | 48.7% | 0.5% |
|  | all | middle | 7949 | +0.019 | +0.027 | +0.046 | -0.016% | 48.6% | 2.74 | 2.51 | 49.7% | 0.3% |
|  | all | exhausted | 6023 | +0.055 | +0.040 | +0.124 | -0.028% | 48.4% | 2.70 | 2.32 | 49.9% | 0.7% |
|  | all | all | 30237 | +0.021 | +0.013 | +0.031 | -0.009% | 47.7% | 2.77 | 2.55 | 49.2% | 0.5% |
| box12 k1.5 | first | room left | 23453 | +0.007 | +0.026 | +0.031 | +0.006% | 47.2% | 2.70 | 2.53 | 49.5% | 0.6% |
|  | first | middle | 9964 | +0.006 | +0.027 | +0.035 | -0.028% | 47.8% | 2.63 | 2.42 | 49.1% | 0.7% |
|  | first | exhausted | 6995 | +0.013 | +0.006 | +0.050 | -0.095% | 46.0% | 2.52 | 2.25 | 49.3% | 1.2% |
|  | first | all | 40412 | +0.008 | +0.023 | +0.035 | -0.019% | 47.1% | 2.65 | 2.46 | 49.3% | 0.7% |
|  | second | room left | 16590 | -0.015 | -0.043 | +0.029 | -0.003% | 48.2% | 2.87 | 2.75 | 47.9% | 0.6% |
|  | second | middle | 6821 | -0.006 | +0.018 | -0.001 | +0.004% | 47.8% | 2.62 | 2.51 | 47.2% | 0.9% |
|  | second | exhausted | 4716 | +0.011 | +0.014 | +0.069 | +0.019% | 48.5% | 2.51 | 2.26 | 48.8% | 1.1% |
|  | second | all | 28127 | -0.009 | -0.018 | +0.028 | +0.003% | 48.1% | 2.75 | 2.61 | 47.9% | 0.7% |
|  | all | room left | 40043 | -0.002 | -0.003 | +0.030 | +0.003% | 47.6% | 2.77 | 2.62 | 48.8% | 0.6% |
|  | all | middle | 16785 | +0.001 | +0.024 | +0.020 | -0.015% | 47.8% | 2.62 | 2.45 | 48.4% | 0.8% |
|  | all | exhausted | 11711 | +0.012 | +0.009 | +0.057 | -0.049% | 47.0% | 2.52 | 2.25 | 49.1% | 1.1% |
|  | all | all | 68539 | +0.001 | +0.006 | +0.032 | -0.010% | 47.6% | 2.69 | 2.52 | 48.7% | 0.7% |
| prior day k1.5 | first | room left | 4992 | +0.039 | +0.030 | +0.059 | -0.000% | 48.3% | 2.54 | 2.35 | 51.3% | 0.9% |
|  | first | middle | 1937 | +0.076 | +0.108 | +0.119 | +0.013% | 48.6% | 2.67 | 2.31 | 52.3% | 0.8% |
|  | first | exhausted | 1008 | +0.030 | +0.083 | +0.094 | -0.011% | 49.8% | 2.45 | 2.09 | 50.7% | 1.3% |
|  | first | all | 7937 | +0.047 | +0.056 | +0.078 | +0.001% | 48.5% | 2.56 | 2.31 | 51.5% | 0.9% |
|  | second | room left | 3537 | +0.027 | -0.034 | -0.088 | -0.029% | 46.4% | 2.63 | 2.59 | 47.7% | 0.7% |
|  | second | middle | 1385 | +0.089 | +0.050 | -0.016 | -0.006% | 48.9% | 2.53 | 2.41 | 48.4% | 0.9% |
|  | second | exhausted | 717 | +0.139 | +0.063 | +0.162 | +0.043% | 52.0% | 2.56 | 2.29 | 48.4% | 1.3% |
|  | second | all | 5639 | +0.057 | -0.001 | -0.039 | -0.014% | 47.7% | 2.60 | 2.51 | 48.0% | 0.9% |
|  | all | room left | 8529 | +0.034 | +0.004 | -0.002 | -0.012% | 47.5% | 2.58 | 2.45 | 49.8% | 0.8% |
|  | all | middle | 3322 | +0.081 | +0.084 | +0.063 | +0.005% | 48.7% | 2.61 | 2.35 | 50.7% | 0.9% |
|  | all | exhausted | 1725 | +0.075 | +0.075 | +0.122 | +0.011% | 50.7% | 2.50 | 2.18 | 49.7% | 1.3% |
|  | all | all | 13576 | +0.051 | +0.032 | +0.030 | -0.005% | 48.2% | 2.58 | 2.39 | 50.0% | 0.9% |
| opening range k1.5 | first | room left | 10110 | +0.001 | +0.000 | -0.028 | +0.002% | 47.3% | 2.56 | 2.46 | 50.7% | 0.8% |
|  | first | middle | 2140 | -0.042 | -0.084 | -0.138 | -0.096% | 46.8% | 2.25 | 2.25 | 48.7% | 1.2% |
|  | first | exhausted | 723 | -0.025 | -0.081 | -0.041 | -0.137% | 48.5% | 2.19 | 2.10 | 49.5% | 1.7% |
|  | first | all | 12973 | -0.007 | -0.018 | -0.047 | -0.022% | 47.3% | 2.49 | 2.41 | 50.3% | 0.9% |
|  | second | room left | 7427 | +0.017 | +0.007 | +0.036 | +0.011% | 48.5% | 2.76 | 2.63 | 48.2% | 0.6% |
|  | second | middle | 1402 | +0.004 | +0.041 | +0.135 | +0.024% | 50.6% | 2.47 | 2.31 | 47.6% | 1.4% |
|  | second | exhausted | 462 | +0.150 | +0.159 | +0.170 | +0.036% | 49.8% | 2.45 | 2.14 | 47.2% | 1.9% |
|  | second | all | 9291 | +0.022 | +0.020 | +0.058 | +0.014% | 48.9% | 2.70 | 2.56 | 48.0% | 0.8% |
|  | all | room left | 17537 | +0.008 | +0.003 | -0.001 | +0.006% | 47.8% | 2.64 | 2.53 | 49.6% | 0.7% |
|  | all | middle | 3542 | -0.024 | -0.035 | -0.030 | -0.049% | 48.3% | 2.34 | 2.27 | 48.3% | 1.3% |
|  | all | exhausted | 1185 | +0.043 | +0.012 | +0.041 | -0.069% | 49.0% | 2.29 | 2.11 | 48.6% | 1.8% |
|  | all | all | 22264 | +0.005 | -0.002 | -0.003 | -0.007% | 48.0% | 2.58 | 2.47 | 49.3% | 0.9% |
| box24 NO momentum (TR < 1.0 ATR15) | first | room left | 6217 | -0.043 | -0.034 | +0.067 | +0.011% | 49.3% | 2.41 | 2.38 | 47.2% | 2.2% |
|  | first | middle | 2817 | -0.064 | -0.038 | +0.030 | -0.002% | 47.9% | 2.08 | 2.09 | 45.8% | 4.1% |
|  | first | exhausted | 2672 | -0.141 | -0.194 | -0.216 | -0.142% | 43.6% | 1.67 | 2.00 | 41.1% | 7.8% |
|  | first | all | 11706 | -0.070 | -0.072 | -0.007 | -0.027% | 47.7% | 2.16 | 2.22 | 45.5% | 3.9% |
|  | second | room left | 6127 | -0.011 | -0.031 | +0.067 | +0.007% | 49.7% | 2.41 | 2.42 | 47.6% | 1.6% |
|  | second | middle | 2581 | -0.046 | -0.052 | -0.026 | -0.014% | 47.1% | 2.09 | 2.14 | 45.7% | 4.3% |
|  | second | exhausted | 2418 | -0.038 | -0.016 | -0.058 | -0.031% | 46.5% | 1.76 | 1.78 | 46.8% | 6.5% |
|  | second | all | 11126 | -0.025 | -0.033 | +0.018 | -0.006% | 48.4% | 2.19 | 2.22 | 47.0% | 3.3% |
|  | all | room left | 12344 | -0.027 | -0.033 | +0.067 | +0.009% | 49.5% | 2.41 | 2.40 | 47.4% | 1.9% |
|  | all | middle | 5398 | -0.055 | -0.045 | +0.003 | -0.008% | 47.5% | 2.08 | 2.11 | 45.8% | 4.2% |
|  | all | exhausted | 5090 | -0.092 | -0.109 | -0.141 | -0.089% | 45.0% | 1.71 | 1.90 | 43.8% | 7.2% |
|  | all | all | 22832 | -0.048 | -0.053 | +0.005 | -0.017% | 48.0% | 2.17 | 2.22 | 46.2% | 3.6% |

## Per market, every variant (second half)

| market | V1 | V2 | V3 | V4 | V5 | V6 | V7 | V8 | V2_twin | V3_twin | V4_twin | V5_twin | V6_twin |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | -0.205% (2108) | -0.206% (1309) | -0.201% (2831) | -0.207% (499) | -0.197% (1190) | -0.196% (1822) | -0.219% (656) | -0.203% (3546) | -0.201% (2331) | -0.205% (4582) | -0.210% (817) | -0.207% (1446) | -0.199% (3026) |
| ETHUSDT | -0.215% (2065) | -0.206% (1344) | -0.206% (2772) | -0.198% (479) | -0.188% (1128) | -0.214% (1778) | -0.254% (698) | -0.222% (3641) | -0.212% (2470) | -0.211% (4690) | -0.200% (824) | -0.197% (1404) | -0.217% (3107) |
| XAUUSD | -0.039% (1186) | -0.038% (638) | -0.036% (1618) | -0.032% (413) | -0.038% (913) | -0.038% (1066) | -0.041% (502) | -0.041% (2289) | -0.045% (1371) | -0.041% (2924) | -0.035% (712) | -0.039% (1156) | -0.040% (2021) |
| XAGUSD | -0.083% (978) | -0.091% (558) | -0.082% (1408) | -0.100% (349) | -0.073% (1003) | -0.082% (898) | -0.062% (491) | -0.076% (2048) | -0.078% (1285) | -0.079% (2693) | -0.101% (652) | -0.074% (1283) | -0.077% (1864) |
| USDJPY | -0.021% (1241) | -0.022% (720) | -0.022% (1641) | -0.023% (463) | -0.022% (748) | -0.020% (1137) | -0.016% (504) | -0.019% (2297) | -0.021% (1383) | -0.020% (2971) | -0.020% (707) | -0.020% (976) | -0.018% (2044) |
| SPX | -0.051% (359) | -0.057% (268) | -0.039% (498) | -0.052% (312) | -0.056% (120) | -0.056% (350) | -0.058% (82) | -0.049% (533) | -0.050% (376) | -0.040% (734) | -0.048% (400) | -0.045% (223) | -0.053% (505) |
| WTI | -0.097% (1491) | -0.090% (859) | -0.100% (2007) | -0.104% (525) | -0.093% (1187) | -0.093% (1329) | -0.051% (378) | -0.087% (2467) | -0.087% (1478) | -0.092% (3165) | -0.105% (815) | -0.097% (1472) | -0.087% (2169) |
| BRENT | -0.096% (1541) | -0.099% (896) | -0.093% (2010) | -0.093% (464) | -0.093% (1059) | -0.098% (1377) | -0.061% (230) | -0.091% (2253) | -0.093% (1336) | -0.091% (2879) | -0.081% (648) | -0.099% (1223) | -0.092% (1956) |

## Checks

- BTCUSDT: 240306 bars (2019-01-01 00:00 to 2025-11-10 23:45), fee 0.10% a side; truncation check 2 cuts, 122189 signals compared, 0 mismatched runs.
- ETHUSDT: 240306 bars (2019-01-01 00:00 to 2025-11-10 23:45), fee 0.10% a side; truncation check 2 cuts, 127649 signals compared, 0 mismatched runs.
- XAUUSD: 162247 bars (2019-01-01 23:00 to 2025-11-10 23:45), fee 0.02% a side; truncation check 2 cuts, 87484 signals compared, 0 mismatched runs.
- XAGUSD: 162216 bars (2019-01-01 23:00 to 2025-11-10 23:45), fee 0.03% a side; truncation check 2 cuts, 82090 signals compared, 0 mismatched runs.
- USDJPY: 171130 bars (2019-01-01 22:00 to 2025-11-10 23:45), fee 0.01% a side; truncation check 2 cuts, 91121 signals compared, 0 mismatched runs.
- SPX: 44687 bars (2019-01-02 14:30 to 2025-11-10 20:45), fee 0.02% a side; truncation check 2 cuts, 25659 signals compared, 0 mismatched runs.
- WTI: 161931 bars (2019-01-01 23:00 to 2025-11-10 23:45), fee 0.04% a side; truncation check 2 cuts, 99497 signals compared, 0 mismatched runs.
- BRENT: 147959 bars (2019-01-02 01:00 to 2025-11-10 21:45), fee 0.04% a side; truncation check 2 cuts, 90847 signals compared, 0 mismatched runs.

## Overlap with what the engine already reads

- `cs_used_x` (card 'Candle size and realistic targets', `sources/ltf.py`): today's high-low / the 14-day AVERAGE high-low range (simple mean, % of open). H44's `used` is the same idea against the Wilder daily ATR(14) (true range, so gaps count) and is held fixed for the day; the two agree closely. NEW in H44: room left in each direction, and the break flag conditioned on it.
- `tq_bos` (card 'Trend quality and squeeze'): a CLOSE beyond the last confirmed 5-bar swing, no size condition. H44's break is beyond a fixed 24-bar box AND needs a bar >= 1.5 x ATR15; many H44 breaks are also BOS events, but the momentum condition and the daily budget are not read there.
- `tq_sq_release` (same card): a Bollinger-inside-Keltner squeeze ending; a volatility-regime event, not a range break. Related (a release often coincides with a large bar) but different.
- `id_or` (card 'Intraday levels'): position vs the first UTC hour's range (above / inside / below), no momentum condition, no first-break event. V5 uses the same range (first 4 bars of the UTC day on file).
- H7 (breakout trap, `playbook.py` p2) FADES failed first closes beyond the 48-bar / prior-day / swing levels; H44 trades WITH the break.
