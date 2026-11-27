# H120: Setups on BTC and ETH without forced entries (A), and with no card above 20% of the say (B)

Replay to 2026-11-26 23:45; halves split at 2023-06-08; holdout from 2025-11-11 and forward from 2026-11-11 shown apart. The engine's own shadows.run under the Setups rule; odds built as the live engine builds them (trust cap included). Research only.

## The registered bar (BTC and ETH together)

- **A_no_forced: does not survive as a rule** (sum of R above current in both halves: False; mean R above zero in both halves: True; worst fall not deeper: False)
- **B_cap20: does not survive as a rule** (sum of R above current in both halves: False; mean R above zero in both halves: False; worst fall not deeper: True)

## BTC and ETH

| Book | all: trades, won, mean R, sum R, net | first half | second half | holdout | forward | worst fall |
|---|---|---|---|---|---|---|
| current | 2029, 44%, -0.006, -11.6, -10983 | 974, 46%, +0.041, +40.3, -4560 | 1055, 42%, -0.049, -51.9, -6423 | 288, 45%, +0.056, +16.1, +3051 | 15, 53%, +0.293, +4.4, +887 | -84.9% |
| A_no_forced | 1689, 45%, +0.016, +27.0, -14438 | 890, 44%, +0.022, +19.8, -10357 | 799, 46%, +0.009, +7.1, -4081 | 210, 48%, +0.053, +11.0, +217 | 11, 64%, +0.399, +4.4, +713 | -88.0% |
| B_cap20 | 1990, 44%, -0.009, -18.2, -6383 | 928, 45%, +0.015, +14.3, -8003 | 1062, 43%, -0.031, -32.6, +1620 | 304, 45%, +0.055, +16.7, +6100 | 14, 57%, +0.388, +5.4, +1362 | -84.6% |
| AB_both | 1572, 45%, +0.028, +43.4, -12803 | 827, 44%, +0.026, +21.6, -11599 | 745, 47%, +0.029, +21.8, -1204 | 194, 49%, +0.069, +13.4, +607 | 11, 64%, +0.586, +6.5, +726 | -83.4% |
| equal | 1958, 43%, -0.012, -24.0, -14032 | 897, 43%, -0.003, -2.3, -13526 | 1061, 43%, -0.020, -21.7, -506 | 298, 44%, +0.047, +14.0, +2246 | 14, 57%, +0.389, +5.4, +629 | -89.5% |

## The other six (descriptive)

| Book | all: trades, won, mean R, sum R, net | first half | second half | holdout | forward | worst fall |
|---|---|---|---|---|---|---|
| current | 3803, 41%, -0.004, -15.1, -22010 | 1898, 41%, -0.021, -40.0, -8683 | 1905, 42%, +0.013, +24.9, -13327 | 485, 43%, +0.021, +10.3, -5853 | 20, 60%, +0.451, +9.0, +1286 | -64.8% |
| A_no_forced | 1246, 44%, +0.044, +54.6, +15019 | 922, 43%, +0.043, +39.6, +20682 | 324, 46%, +0.046, +14.9, -5664 | 64, 50%, +0.138, +8.8, -4121 | 0, -%, -, +0.0, +0 | -21.3% |
| B_cap20 | 3798, 41%, -0.004, -14.1, -20408 | 1886, 41%, -0.019, -36.3, -6259 | 1912, 42%, +0.012, +22.2, -14149 | 493, 43%, +0.011, +5.6, -7087 | 20, 60%, +0.451, +9.0, +1445 | -65.6% |
| AB_both | 1047, 43%, +0.024, +24.7, +32106 | 814, 42%, +0.022, +18.1, +25156 | 233, 46%, +0.028, +6.6, +6950 | 30, 57%, +0.253, +7.6, +5401 | 0, -%, -, +0.0, +0 | -20.3% |
| equal | 3805, 41%, -0.008, -30.6, -20977 | 1879, 41%, -0.022, -40.8, -3003 | 1926, 42%, +0.005, +10.3, -17974 | 493, 43%, +0.011, +5.3, -7725 | 20, 60%, +0.451, +9.0, +1183 | -68.7% |

## All eight (descriptive)

| Book | all: trades, won, mean R, sum R, net | first half | second half | holdout | forward | worst fall |
|---|---|---|---|---|---|---|
| current | 5832, 42%, -0.005, -26.7, -32992 | 2872, 42%, +0.000, +0.3, -13243 | 2960, 42%, -0.009, -27.0, -19750 | 773, 44%, +0.034, +26.3, -2801 | 35, 57%, +0.383, +13.4, +2173 | -64.3% |
| A_no_forced | 2935, 44%, +0.028, +81.5, +581 | 1812, 44%, +0.033, +59.5, +10326 | 1123, 46%, +0.020, +22.1, -9745 | 274, 49%, +0.072, +19.8, -3904 | 11, 64%, +0.399, +4.4, +713 | -24.7% |
| B_cap20 | 5788, 42%, -0.006, -32.3, -26791 | 2814, 42%, -0.008, -21.9, -14262 | 2974, 42%, -0.003, -10.3, -12529 | 797, 44%, +0.028, +22.3, -987 | 34, 59%, +0.425, +14.5, +2807 | -60.7% |
| AB_both | 2619, 44%, +0.026, +68.1, +19304 | 1641, 43%, +0.024, +39.7, +13557 | 978, 47%, +0.029, +28.4, +5746 | 224, 50%, +0.094, +21.0, +6008 | 11, 64%, +0.586, +6.5, +726 | -23.1% |
| equal | 5763, 42%, -0.009, -54.5, -35009 | 2776, 42%, -0.016, -43.2, -16529 | 2987, 42%, -0.004, -11.4, -18480 | 791, 43%, +0.024, +19.3, -5479 | 34, 59%, +0.425, +14.5, +1812 | -66.6% |

## Per market (descriptive)

| Market | book | trades | mean R | sum R | flat % | entries by word | longest flat (h) |
|---|---|---|---|---|---|---|---|
| BTCUSDT | current | 1047 | -0.060 | -62.7 | 1 | {'FORCED': 627, 'ENTER': 372, 'FLIP': 48} | 2 |
| BTCUSDT | A_no_forced | 846 | +0.018 | +15.2 | 30 | {'ENTER': 782, 'FLIP': 64} | 375 |
| BTCUSDT | B_cap20 | 988 | -0.065 | -64.4 | 1 | {'FORCED': 639, 'ENTER': 318, 'FLIP': 31} | 2 |
| BTCUSDT | AB_both | 755 | +0.057 | +42.9 | 32 | {'ENTER': 704, 'FLIP': 51} | 375 |
| BTCUSDT | equal | 971 | -0.051 | -49.9 | 1 | {'FORCED': 657, 'ENTER': 287, 'FLIP': 27} | 2 |
| ETHUSDT | current | 982 | +0.052 | +51.0 | 1 | {'FORCED': 599, 'ENTER': 337, 'FLIP': 46} | 2 |
| ETHUSDT | A_no_forced | 843 | +0.014 | +11.8 | 31 | {'ENTER': 758, 'FLIP': 85} | 262 |
| ETHUSDT | B_cap20 | 1002 | +0.046 | +46.2 | 1 | {'FORCED': 644, 'ENTER': 320, 'FLIP': 38} | 2 |
| ETHUSDT | AB_both | 817 | +0.001 | +0.5 | 34 | {'ENTER': 736, 'FLIP': 81} | 262 |
| ETHUSDT | equal | 987 | +0.026 | +26.0 | 1 | {'FORCED': 658, 'ENTER': 296, 'FLIP': 33} | 2 |
| XAUUSD | current | 735 | +0.006 | +4.4 | 2 | {'FORCED': 685, 'FLIP': 26, 'ENTER': 24} | 2 |
| XAUUSD | A_no_forced | 95 | +0.035 | +3.4 | 91 | {'ENTER': 79, 'FLIP': 16} | 9452 |
| XAUUSD | B_cap20 | 727 | +0.014 | +9.9 | 2 | {'FORCED': 687, 'FLIP': 25, 'ENTER': 15} | 2 |
| XAUUSD | AB_both | 60 | -0.081 | -4.9 | 95 | {'ENTER': 45, 'FLIP': 15} | 9750 |
| XAUUSD | equal | 740 | -0.003 | -2.0 | 2 | {'FORCED': 710, 'FLIP': 20, 'ENTER': 10} | 2 |
| XAGUSD | current | 700 | -0.002 | -1.3 | 2 | {'FORCED': 664, 'ENTER': 20, 'FLIP': 16} | 2 |
| XAGUSD | A_no_forced | 89 | +0.220 | +19.6 | 90 | {'ENTER': 78, 'FLIP': 11} | 6886 |
| XAGUSD | B_cap20 | 704 | +0.003 | +2.2 | 2 | {'FORCED': 679, 'FLIP': 15, 'ENTER': 10} | 2 |
| XAGUSD | AB_both | 56 | +0.460 | +25.8 | 94 | {'ENTER': 45, 'FLIP': 11} | 15500 |
| XAGUSD | equal | 703 | -0.002 | -1.2 | 2 | {'FORCED': 682, 'FLIP': 16, 'ENTER': 5} | 2 |
| USDJPY | current | 723 | +0.013 | +9.1 | 2 | {'FORCED': 639, 'ENTER': 61, 'FLIP': 23} | 2 |
| USDJPY | A_no_forced | 323 | -0.033 | -10.6 | 68 | {'ENTER': 261, 'FLIP': 62} | 5377 |
| USDJPY | B_cap20 | 720 | +0.011 | +8.2 | 2 | {'FORCED': 648, 'ENTER': 53, 'FLIP': 19} | 2 |
| USDJPY | AB_both | 298 | -0.058 | -17.4 | 70 | {'ENTER': 233, 'FLIP': 65} | 5912 |
| USDJPY | equal | 712 | +0.022 | +15.7 | 2 | {'FORCED': 644, 'ENTER': 46, 'FLIP': 22} | 2 |
| SPX | current | 241 | +0.076 | +18.2 | 2 | {'FORCED': 230, 'FLIP': 6, 'ENTER': 5} | 1 |
| SPX | A_no_forced | 11 | +0.112 | +1.2 | 96 | {'ENTER': 10, 'FLIP': 1} | 5098 |
| SPX | B_cap20 | 239 | +0.081 | +19.4 | 2 | {'FORCED': 229, 'FLIP': 7, 'ENTER': 3} | 1 |
| SPX | AB_both | 10 | +0.369 | +3.7 | 96 | {'ENTER': 9, 'FLIP': 1} | 5098 |
| SPX | equal | 239 | +0.080 | +19.2 | 2 | {'FORCED': 229, 'FLIP': 7, 'ENTER': 3} | 1 |
| WTI | current | 708 | -0.025 | -18.0 | 2 | {'FORCED': 543, 'ENTER': 131, 'FLIP': 34} | 2 |
| WTI | A_no_forced | 369 | +0.076 | +28.0 | 52 | {'ENTER': 333, 'FLIP': 36} | 1740 |
| WTI | B_cap20 | 709 | -0.034 | -24.4 | 2 | {'FORCED': 620, 'ENTER': 59, 'FLIP': 30} | 2 |
| WTI | AB_both | 309 | +0.087 | +27.0 | 66 | {'ENTER': 283, 'FLIP': 26} | 1742 |
| WTI | equal | 715 | -0.035 | -25.2 | 2 | {'FORCED': 638, 'ENTER': 46, 'FLIP': 31} | 2 |
| BRENT | current | 696 | -0.039 | -27.4 | 2 | {'FORCED': 546, 'ENTER': 115, 'FLIP': 35} | 2 |
| BRENT | A_no_forced | 359 | +0.036 | +13.0 | 51 | {'ENTER': 327, 'FLIP': 32} | 1466 |
| BRENT | B_cap20 | 699 | -0.042 | -29.3 | 2 | {'FORCED': 610, 'ENTER': 58, 'FLIP': 31} | 2 |
| BRENT | AB_both | 314 | -0.030 | -9.4 | 63 | {'ENTER': 286, 'FLIP': 28} | 2534 |
| BRENT | equal | 696 | -0.053 | -37.1 | 2 | {'FORCED': 637, 'ENTER': 36, 'FLIP': 23} | 2 |

## Checks

- BTCUSDT: window 2020-02-05 00:00 to 2026-11-26 23:45; the largest card's share of the say (median): live 0.18, cap20 0.18, equal 0.08; sessions where the side differs from live: cap20 2.7%, equal 7.6%; live Setups trades since 11 Nov found in the replay: {'live': 10, 'found': 4}
- ETHUSDT: window 2020-02-05 00:00 to 2026-11-26 23:45; the largest card's share of the say (median): live 0.18, cap20 0.18, equal 0.08; sessions where the side differs from live: cap20 2.7%, equal 7.7%; live Setups trades since 11 Nov found in the replay: {'live': 8, 'found': 2}
- XAUUSD: window 2020-02-21 19:00 to 2026-11-26 23:45; the largest card's share of the say (median): live 0.14, cap20 0.14, equal 0.08; sessions where the side differs from live: cap20 2.7%, equal 8.1%; live Setups trades since 11 Nov found in the replay: {'live': 7, 'found': 0}
- XAGUSD: window 2020-02-21 19:00 to 2026-11-26 23:45; the largest card's share of the say (median): live 0.13, cap20 0.13, equal 0.08; sessions where the side differs from live: cap20 2.6%, equal 7.7%; live Setups trades since 11 Nov found in the replay: {'live': 7, 'found': 5}
- USDJPY: window 2020-04-08 21:00 to 2026-11-26 23:30; the largest card's share of the say (median): live 0.13, cap20 0.13, equal 0.09; sessions where the side differs from live: cap20 1.6%, equal 5.5%; live Setups trades since 11 Nov found in the replay: {'live': 6, 'found': 1}
- SPX: window 2021-01-12 17:30 to 2026-11-25 20:45; the largest card's share of the say (median): live 0.12, cap20 0.12, equal 0.11; sessions where the side differs from live: cap20 0.5%, equal 2.9%; live Setups trades since 11 Nov found in the replay: {'live': 2, 'found': 2}
- WTI: window 2020-02-27 19:00 to 2026-11-26 18:15; the largest card's share of the say (median): live 0.21, cap20 0.20, equal 0.11; sessions where the side differs from live: cap20 4.9%, equal 11.7%; live Setups trades since 11 Nov found in the replay: {'live': 1, 'found': 0}
- BRENT: window 2020-02-27 19:00 to 2026-11-26 18:15; the largest card's share of the say (median): live 0.21, cap20 0.20, equal 0.11; sessions where the side differs from live: cap20 5.1%, equal 11.4%; live Setups trades since 11 Nov found in the replay: {'live': 5, 'found': 0}

Run time 759 s.
