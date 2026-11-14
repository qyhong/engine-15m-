# H36: moving-average trails and break-even on the main book's own entries (IN-SAMPLE, not proof)

Written by `research/exit_study.py` on 2026-11-13 04:30 UTC. Every book takes the main book's entries (v5.1 odds as the live step forms them, voices walked forward weekly from 2020-01-01), sizing, fees, protective stop, flips and mandate; only the exit differs. $10,000 per market, 8 markets. Halves split at 2023-06-08. Paper only.

**Read this plainly:** history the engine's authors have lived through, 15 exit variants tried (plus b_targets and b_trail), eight markets that partly move together. A history read can reject an idea, never prove one. Nothing here changes the main book; only the owner can.

## All markets together

| Book | Net P&L | Return | vs main | vs b_targets | vs b_trail | Sharpe | Max DD | 1st half vs main | 2nd half vs main | Markets beating main | Median market gap (return pts) | Without ETH: vs main / Sharpe / DD | Trades | Fees | Top-6 trades $ | Better than hold? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+329439 | +411.80% | $+0 | $+358301 | $+378247 | 0.92 | -29.63% | $+0 | $+0 | 0/8 | +0.0 | $+0 / 0.51 / -37.6% | 1322 | $60391 | $+557653 | - |
| `b_targets` | $-28862 | -36.08% | $-358301 | $+0 | $+19947 | -0.18 | -65.83% | $-132392 | $-225909 | 0/8 | -134.9 | $-85114 / -0.14 / -67.5% | 6121 | $63185 | $+102129 | - |
| `b_trail` | $-48808 | -61.01% | $-378247 | $-19947 | $+0 | -0.43 | -78.39% | $-133234 | $-245013 | 0/8 | -169.8 | $-101639 / -0.36 / -78.2% | 11663 | $112575 | $+85376 | - |
| `be_t1` | $+107673 | +134.59% | $-221766 | $+136535 | $+156482 | 0.62 | -37.05% | $-23231 | $-198534 | 2/8 | -21.8 | $-8554 / 0.46 / -45.1% | 1764 | $45062 | $+367616 | no |
| `ema20_15m_1r` | $-45226 | -56.53% | $-374665 | $-16364 | $+3582 | -0.38 | -72.95% | $-139954 | $-234711 | 0/8 | -164.4 | $-98037 / -0.31 / -72.8% | 11085 | $92072 | $+82890 | no |
| `ema50_15m_1r` | $-38049 | -47.56% | $-367488 | $-9187 | $+10759 | -0.24 | -70.65% | $-133138 | $-234350 | 0/8 | -146.9 | $-90898 / -0.17 / -70.6% | 10144 | $97074 | $+100005 | no |
| `ema20_1h_1r` | $-37098 | -46.37% | $-366537 | $-8236 | $+11711 | -0.22 | -69.26% | $-136756 | $-229781 | 0/8 | -130.3 | $-90204 / -0.15 / -69.0% | 9573 | $95073 | $+100989 | no |
| `sma20_15m_1r` | $-44610 | -55.76% | $-374049 | $-15748 | $+4198 | -0.36 | -72.70% | $-127827 | $-246222 | 0/8 | -158.1 | $-97440 / -0.29 / -72.4% | 11244 | $103143 | $+83151 | no |
| `sma50_15m_1r` | $-36998 | -46.25% | $-366437 | $-8137 | $+11810 | -0.21 | -70.47% | $-128478 | $-237960 | 0/8 | -132.9 | $-89880 / -0.14 / -70.4% | 10361 | $103127 | $+103994 | no |
| `sma20_1h_1r` | $-33431 | -41.79% | $-362870 | $-4569 | $+15378 | -0.17 | -67.41% | $-131865 | $-231005 | 0/8 | -124.5 | $-86565 / -0.10 / -67.4% | 9707 | $99353 | $+108191 | no |
| `ema20_1h_entry` | $-78817 | -98.52% | $-408256 | $-49955 | $-30008 | -2.95 | -98.60% | $-199165 | $-209090 | 0/8 | -211.7 | $-131449 / -2.87 / -98.5% | 95482 | $104107 | $+63080 | no |
| `sma20_1h_entry` | $-78781 | -98.48% | $-408220 | $-49919 | $-29972 | -2.88 | -98.61% | $-199480 | $-208739 | 0/8 | -211.7 | $-131413 / -2.80 / -98.5% | 98949 | $112291 | $+64901 | no |
| `ema20_1h_t1` | $-25732 | -32.16% | $-355171 | $+3130 | $+23077 | -0.08 | -68.87% | $-117928 | $-237243 | 0/8 | -110.7 | $-81522 / -0.04 / -69.6% | 6688 | $83509 | $+120540 | no |
| `sma20_1h_t1` | $-24645 | -30.81% | $-354084 | $+4217 | $+24164 | -0.08 | -66.28% | $-118149 | $-235935 | 0/8 | -126.4 | $-82312 / -0.06 / -68.1% | 6773 | $84101 | $+125382 | no |
| `be_ema20_1h_1r` | $-36788 | -45.99% | $-366228 | $-7927 | $+12020 | -0.21 | -68.80% | $-136197 | $-230031 | 0/8 | -128.1 | $-89964 / -0.14 / -68.5% | 9688 | $94210 | $+99102 | no |
| `be_sma20_1h_1r` | $-35006 | -43.76% | $-364445 | $-6145 | $+13802 | -0.19 | -68.22% | $-134687 | $-229758 | 0/8 | -126.9 | $-88256 / -0.12 / -68.2% | 9805 | $97625 | $+106436 | no |
| `half_ema20_1h_t1` | $-31220 | -39.03% | $-360660 | $-2359 | $+17588 | -0.17 | -68.84% | $-124617 | $-236043 | 0/8 | -109.3 | $-85223 / -0.11 / -68.8% | 6688 | $74183 | $+93363 | no |
| `half_sma20_1h_t1` | $-32758 | -40.95% | $-362197 | $-3896 | $+16050 | -0.20 | -70.51% | $-122973 | $-239224 | 0/8 | -124.0 | $-88211 / -0.15 / -71.4% | 6773 | $75870 | $+98908 | no |

Pooled curves: the markets' daily marked equity summed (a market not yet trading counts at $10,000). Sharpe on daily returns, sqrt(365). Top-6 trades $: the six largest closed trades of each market, summed. 'Better than hold' (registered): above main in both halves, in at least 5 of 8 markets, and drawdown no worse.

Dollar halves compound: ETHUSDT's main book alone made $+266807 of the pooled $+329439, so pooled dollar gaps are mostly ETH; the 'Without ETH' and 'Median market gap' columns show the rest.

Forward shadow books. The registered rule (best worse-half dollar gap to main) picks be = `be_t1`, ema = `ema20_1h_entry`, sma = `sma20_1h_entry`: it is degenerate under compounding (the from-entry trails lost ~99% by the midpoint, so they had no dollars left to lose in the second half and 'won' the worse half while being the worst variants). Amended after the results, disclosed in research/HYPOTHESES.md: whole-window pooled net P&L within each family, which picks be = `be_t1`, ema = `ema20_1h_t1`, sma = `sma20_1h_t1`.

## Per market (whole window)

### BTCUSDT: 2020-02-05 00:00 to 2026-11-13 04:00 UTC, buy and hold +647.05%, fee 0.100% a side

Main book: top 6 trades $+17576 of $-2649 net (-%).

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | Avg hold (bars) | Top-6 share | 1st half | 2nd half | Exits |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $-2649 | $+0 | -26.5% | 0.18 | -82.4% | 317 | 18% | $+678 | $-166 | 741 | - | $-6448 | $+3798 | STOP 217, FLIP 100 |
| `b_targets` | $-9583 | $-6934 | -95.8% | -0.61 | -98.3% | 1128 | 42% | $+162 | $-132 | 207 | - | $-6916 | $-2667 | STOP 601, T1+T2 287, T1+STOP_BE 170, FLIP 63 |
| `b_trail` | $-8889 | $-6239 | -88.9% | -0.26 | -93.2% | 1848 | 50% | $+135 | $-146 | 125 | - | $-5524 | $-3364 | TRAIL 926, STOP 848, FLIP 74 |
| `be_t1` | $-1750 | $+899 | -17.5% | 0.22 | -83.7% | 398 | 15% | $+731 | $-138 | 591 | - | $-5841 | $+4091 | STOP 203, STOP_BE 107, FLIP 88 |
| `ema20_15m_1r` | $-9619 | $-6970 | -96.2% | -0.52 | -97.4% | 1749 | 48% | $+94 | $-98 | 132 | - | $-7155 | $-2464 | TRAIL_MA 850, STOP 822, FLIP 77 |
| `ema50_15m_1r` | $-9164 | $-6515 | -91.6% | -0.32 | -94.4% | 1587 | 47% | $+96 | $-96 | 145 | - | $-6913 | $-2251 | TRAIL_MA 773, STOP 743, FLIP 71 |
| `ema20_1h_1r` | $-8440 | $-5791 | -84.4% | -0.18 | -90.5% | 1513 | 46% | $+143 | $-133 | 153 | - | $-5601 | $-2839 | TRAIL_MA 736, STOP 701, FLIP 76 |
| `sma20_15m_1r` | $-9599 | $-6949 | -96.0% | -0.49 | -97.5% | 1774 | 48% | $+115 | $-117 | 130 | - | $-6561 | $-3037 | TRAIL_MA 861, STOP 837, FLIP 76 |
| `sma50_15m_1r` | $-9683 | $-7034 | -96.8% | -0.56 | -97.9% | 1668 | 46% | $+77 | $-77 | 138 | - | $-8143 | $-1540 | TRAIL_MA 805, STOP 792, FLIP 71 |
| `sma20_1h_1r` | $-8660 | $-6011 | -86.6% | -0.22 | -91.1% | 1570 | 46% | $+123 | $-116 | 147 | - | $-6326 | $-2335 | TRAIL_MA 773, STOP 719, FLIP 78 |
| `ema20_1h_entry` | $-10000 | $-7351 | -100.0% | -8.25 | -100.0% | 18677 | 14% | $+3 | $-1 | 8 | - | $-10000 | $-0 | TRAIL_MA 18591, STOP 60, FLIP 26 |
| `sma20_1h_entry` | $-10000 | $-7351 | -100.0% | -8.62 | -100.0% | 19640 | 14% | $+3 | $-1 | 8 | - | $-10000 | $-0 | TRAIL_MA 19546, STOP 58, FLIP 36 |
| `ema20_1h_t1` | $-8732 | $-6083 | -87.3% | -0.23 | -93.1% | 1109 | 38% | $+174 | $-122 | 210 | - | $-6654 | $-2078 | STOP 600, TRAIL_MA 433, FLIP 76 |
| `sma20_1h_t1` | $-8176 | $-5527 | -81.8% | -0.14 | -88.8% | 1130 | 39% | $+161 | $-117 | 206 | - | $-6578 | $-1598 | STOP 598, TRAIL_MA 454, FLIP 78 |
| `be_ema20_1h_1r` | $-8888 | $-6238 | -88.9% | -0.24 | -93.5% | 1529 | 45% | $+115 | $-105 | 151 | - | $-6793 | $-2095 | TRAIL_MA 716, STOP 699, FLIP 76, STOP_BE 38 |
| `be_sma20_1h_1r` | $-9059 | $-6409 | -90.6% | -0.28 | -93.6% | 1578 | 45% | $+100 | $-93 | 146 | - | $-7199 | $-1860 | TRAIL_MA 744, STOP 719, FLIP 77, STOP_BE 38 |
| `half_ema20_1h_t1` | $-9206 | $-6557 | -92.1% | -0.46 | -94.4% | 1109 | 40% | $+147 | $-113 | 210 | - | $-7157 | $-2049 | STOP 599, T1+TRAIL_MA 433, FLIP 74, T1+FLIP 2 |
| `half_sma20_1h_t1` | $-8758 | $-6108 | -87.6% | -0.33 | -90.6% | 1130 | 41% | $+135 | $-108 | 206 | - | $-6957 | $-1801 | STOP 596, T1+TRAIL_MA 454, FLIP 77, T1+STOP 2 |

### ETHUSDT: 2020-02-05 00:00 to 2026-11-13 04:00 UTC, buy and hold +922.24%, fee 0.100% a side

Main book: top 6 trades $+296672 of $+266807 net (111%).

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | Avg hold (bars) | Top-6 share | 1st half | 2nd half | Exits |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+266807 | $+0 | +2668.1% | 1.06 | -55.3% | 237 | 24% | $+13605 | $-2924 | 996 | 111% | $+72862 | $+193945 | STOP 147, FLIP 90 |
| `b_targets` | $-6380 | $-273187 | -63.8% | 0.15 | -90.5% | 1043 | 44% | $+190 | $-164 | 224 | - | $-6308 | $-72 | STOP 519, T1+T2 278, T1+STOP_BE 171, FLIP 69 |
| `b_trail` | $-9801 | $-276608 | -98.0% | -0.37 | -99.0% | 1997 | 50% | $+106 | $-117 | 115 | - | $-9098 | $-703 | TRAIL 997, STOP 919, FLIP 81 |
| `be_t1` | $+53596 | $-213211 | +536.0% | 0.74 | -66.0% | 344 | 14% | $+4909 | $-689 | 684 | 162% | $+20027 | $+33568 | STOP 155, STOP_BE 101, FLIP 88 |
| `ema20_15m_1r` | $-9821 | $-276628 | -98.2% | -0.35 | -99.2% | 1869 | 49% | $+78 | $-84 | 123 | - | $-9146 | $-675 | TRAIL_MA 914, STOP 881, FLIP 74 |
| `ema50_15m_1r` | $-9783 | $-276590 | -97.8% | -0.35 | -99.2% | 1674 | 46% | $+66 | $-68 | 138 | - | $-9446 | $-337 | TRAIL_MA 803, STOP 798, FLIP 73 |
| `ema20_1h_1r` | $-9525 | $-276332 | -95.2% | -0.21 | -98.2% | 1587 | 45% | $+114 | $-105 | 145 | - | $-8989 | $-537 | TRAIL_MA 752, STOP 750, FLIP 85 |
| `sma20_15m_1r` | $-9802 | $-276609 | -98.0% | -0.33 | -99.4% | 1887 | 49% | $+70 | $-77 | 122 | - | $-9315 | $-487 | TRAIL_MA 927, STOP 889, FLIP 71 |
| `sma50_15m_1r` | $-9751 | $-276558 | -97.5% | -0.32 | -98.8% | 1733 | 46% | $+82 | $-81 | 133 | - | $-9351 | $-400 | TRAIL_MA 836, STOP 822, FLIP 75 |
| `sma20_1h_1r` | $-9498 | $-276305 | -95.0% | -0.19 | -98.3% | 1603 | 45% | $+108 | $-100 | 144 | - | $-9239 | $-259 | TRAIL_MA 761, STOP 751, FLIP 91 |
| `ema20_1h_entry` | $-10000 | $-276807 | -100.0% | -6.00 | -100.0% | 18833 | 19% | $+6 | $-2 | 8 | - | $-10000 | $-0 | TRAIL_MA 18750, STOP 52, FLIP 31 |
| `sma20_1h_entry` | $-10000 | $-276807 | -100.0% | -6.20 | -100.0% | 19664 | 19% | $+6 | $-2 | 8 | - | $-10000 | $-0 | TRAIL_MA 19559, STOP 60, FLIP 45 |
| `ema20_1h_t1` | $-6842 | $-273649 | -68.4% | 0.15 | -91.1% | 1128 | 39% | $+340 | $-228 | 206 | - | $-5516 | $-1326 | STOP 596, TRAIL_MA 448, FLIP 84 |
| `sma20_1h_t1` | $-4965 | $-271772 | -49.6% | 0.25 | -90.0% | 1133 | 41% | $+362 | $-256 | 205 | - | $-4417 | $-548 | STOP 583, TRAIL_MA 460, FLIP 90 |
| `be_ema20_1h_1r` | $-9457 | $-276264 | -94.6% | -0.19 | -98.0% | 1598 | 45% | $+120 | $-108 | 144 | - | $-8869 | $-587 | STOP 747, TRAIL_MA 738, FLIP 82, STOP_BE 31 |
| `be_sma20_1h_1r` | $-9383 | $-276190 | -93.8% | -0.16 | -98.0% | 1615 | 44% | $+120 | $-107 | 143 | - | $-9050 | $-333 | STOP 748, TRAIL_MA 746, FLIP 89, STOP_BE 32 |
| `half_ema20_1h_t1` | $-8630 | $-275437 | -86.3% | -0.09 | -93.8% | 1128 | 41% | $+229 | $-171 | 206 | - | $-7081 | $-1548 | STOP 594, T1+TRAIL_MA 448, FLIP 83, T1+STOP 2 |
| `half_sma20_1h_t1` | $-7179 | $-273986 | -71.8% | 0.07 | -91.1% | 1133 | 42% | $+245 | $-188 | 205 | - | $-6352 | $-827 | STOP 581, T1+TRAIL_MA 460, FLIP 88, T1+STOP 2 |

### XAUUSD: 2020-02-21 19:00 to 2026-11-13 03:30 UTC, buy and hold +135.42%, fee 0.020% a side

Main book: top 6 trades $+30414 of $+17712 net (172%).

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | Avg hold (bars) | Top-6 share | 1st half | 2nd half | Exits |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+17712 | $+0 | +177.1% | 0.61 | -69.9% | 134 | 22% | $+1163 | $-198 | 1151 | 172% | $-4081 | $+21793 | STOP 90, FLIP 44 |
| `b_targets` | $-4105 | $-21817 | -41.0% | -0.13 | -77.2% | 749 | 41% | $+151 | $-114 | 207 | - | $-6213 | $+2108 | STOP 414, T1+T2 188, T1+STOP_BE 107, FLIP 38 |
| `b_trail` | $-2211 | $-19923 | -22.1% | 0.06 | -75.0% | 1445 | 51% | $+126 | $-133 | 104 | - | $-5674 | $+3463 | TRAIL 725, STOP 677, FLIP 43 |
| `be_t1` | $+13945 | $-3767 | +139.4% | 0.56 | -69.0% | 170 | 14% | $+1164 | $-124 | 906 | 179% | $-3960 | $+17904 | STOP 83, STOP_BE 46, FLIP 41 |
| `ema20_15m_1r` | $-3701 | $-21413 | -37.0% | -0.04 | -84.4% | 1368 | 50% | $+97 | $-101 | 111 | - | $-7165 | $+3464 | TRAIL_MA 681, STOP 644, FLIP 43 |
| `ema50_15m_1r` | $+1279 | $-16433 | +12.8% | 0.22 | -80.2% | 1264 | 49% | $+126 | $-121 | 120 | 359% | $-6504 | $+7783 | TRAIL_MA 635, STOP 588, FLIP 41 |
| `ema20_1h_1r` | $-1078 | $-18790 | -10.8% | 0.12 | -83.3% | 1197 | 48% | $+119 | $-111 | 128 | - | $-7024 | $+5946 | TRAIL_MA 589, STOP 564, FLIP 44 |
| `sma20_15m_1r` | $-3909 | $-21621 | -39.1% | -0.06 | -83.1% | 1381 | 50% | $+100 | $-105 | 110 | - | $-6856 | $+2947 | TRAIL_MA 690, STOP 650, FLIP 41 |
| `sma50_15m_1r` | $-2959 | $-20671 | -29.6% | 0.02 | -84.1% | 1307 | 49% | $+103 | $-103 | 116 | - | $-7327 | $+4368 | TRAIL_MA 654, STOP 611, FLIP 42 |
| `sma20_1h_1r` | $-1596 | $-19308 | -16.0% | 0.10 | -85.8% | 1224 | 47% | $+111 | $-102 | 125 | - | $-7284 | $+5689 | TRAIL_MA 596, STOP 585, FLIP 43 |
| `ema20_1h_entry` | $-9999 | $-27711 | -100.0% | -3.73 | -100.0% | 10783 | 31% | $+6 | $-4 | 10 | - | $-9966 | $-33 | TRAIL_MA 10685, STOP 67, FLIP 31 |
| `sma20_1h_entry` | $-9999 | $-27711 | -100.0% | -3.60 | -100.0% | 11064 | 32% | $+6 | $-4 | 10 | - | $-9961 | $-38 | TRAIL_MA 10959, STOP 67, FLIP 38 |
| `ema20_1h_t1` | $-704 | $-18416 | -7.0% | 0.14 | -73.6% | 824 | 40% | $+212 | $-141 | 188 | - | $-5513 | $+4809 | STOP 458, TRAIL_MA 325, FLIP 41 |
| `sma20_1h_t1` | $-2825 | $-20537 | -28.2% | 0.02 | -78.7% | 847 | 39% | $+186 | $-125 | 182 | - | $-6344 | $+3518 | STOP 479, TRAIL_MA 328, FLIP 40 |
| `be_ema20_1h_1r` | $-616 | $-18328 | -6.2% | 0.14 | -82.3% | 1208 | 47% | $+120 | $-109 | 126 | - | $-7055 | $+6439 | TRAIL_MA 578, STOP 561, FLIP 44, STOP_BE 25 |
| `be_sma20_1h_1r` | $-1550 | $-19261 | -15.5% | 0.10 | -85.9% | 1233 | 47% | $+111 | $-100 | 124 | - | $-7433 | $+5883 | STOP 583, TRAIL_MA 583, FLIP 43, STOP_BE 24 |
| `half_ema20_1h_t1` | $-1197 | $-18909 | -12.0% | 0.09 | -70.0% | 824 | 41% | $+203 | $-143 | 188 | - | $-5090 | $+3894 | STOP 458, T1+TRAIL_MA 325, FLIP 40, T1+FLIP 1 |
| `half_sma20_1h_t1` | $-3619 | $-21331 | -36.2% | -0.06 | -76.9% | 847 | 40% | $+174 | $-124 | 182 | - | $-6095 | $+2476 | STOP 479, T1+TRAIL_MA 328, FLIP 38, T1+FLIP 2 |

### XAGUSD: 2020-02-21 19:00 to 2026-11-13 03:30 UTC, buy and hold +168.56%, fee 0.030% a side

Main book: top 6 trades $+26428 of $-796 net (-%).

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | Avg hold (bars) | Top-6 share | 1st half | 2nd half | Exits |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $-796 | $+0 | -8.0% | 0.19 | -85.0% | 161 | 14% | $+1406 | $-253 | 962 | - | $+1056 | $-1852 | STOP 125, FLIP 36 |
| `b_targets` | $-7871 | $-7075 | -78.7% | -0.43 | -88.8% | 737 | 42% | $+168 | $-143 | 210 | - | $-5858 | $-2013 | STOP 405, T1+T2 197, T1+STOP_BE 104, FLIP 29 |
| `b_trail` | $-6853 | $-6057 | -68.5% | -0.20 | -87.0% | 1297 | 49% | $+171 | $-177 | 117 | - | $-1954 | $-4900 | TRAIL 641, STOP 621, FLIP 35 |
| `be_t1` | $-1387 | $-591 | -13.9% | 0.17 | -85.6% | 212 | 11% | $+1214 | $-164 | 730 | - | $-446 | $-941 | STOP 119, STOP_BE 60, FLIP 33 |
| `ema20_15m_1r` | $-7324 | $-6528 | -73.2% | -0.27 | -88.6% | 1267 | 48% | $+142 | $-145 | 120 | - | $-4257 | $-3067 | STOP 619, TRAIL_MA 616, FLIP 32 |
| `ema50_15m_1r` | $-8214 | $-7418 | -82.1% | -0.41 | -92.7% | 1195 | 46% | $+140 | $-133 | 128 | - | $-5334 | $-2880 | STOP 594, TRAIL_MA 567, FLIP 34 |
| `ema20_1h_1r` | $-5816 | $-5020 | -58.2% | -0.10 | -82.3% | 1119 | 47% | $+178 | $-170 | 137 | - | $-3780 | $-2036 | TRAIL_MA 547, STOP 539, FLIP 33 |
| `sma20_15m_1r` | $-8546 | $-7750 | -85.5% | -0.48 | -93.0% | 1274 | 47% | $+128 | $-127 | 120 | - | $-5269 | $-3277 | STOP 637, TRAIL_MA 606, FLIP 31 |
| `sma50_15m_1r` | $-7516 | $-6720 | -75.2% | -0.29 | -90.4% | 1207 | 47% | $+158 | $-150 | 126 | - | $-4319 | $-3198 | STOP 594, TRAIL_MA 580, FLIP 33 |
| `sma20_1h_1r` | $-8203 | $-7407 | -82.0% | -0.41 | -92.0% | 1147 | 46% | $+127 | $-119 | 133 | - | $-6304 | $-1899 | STOP 572, TRAIL_MA 542, FLIP 33 |
| `ema20_1h_entry` | $-9998 | $-9201 | -100.0% | -2.95 | -100.0% | 11157 | 34% | $+10 | $-7 | 9 | - | $-9840 | $-158 | TRAIL_MA 11075, STOP 68, FLIP 14 |
| `sma20_1h_entry` | $-9998 | $-9202 | -100.0% | -3.11 | -100.0% | 11482 | 34% | $+10 | $-7 | 9 | - | $-9899 | $-99 | TRAIL_MA 11390, STOP 75, FLIP 17 |
| `ema20_1h_t1` | $-7632 | $-6836 | -76.3% | -0.31 | -90.0% | 794 | 39% | $+201 | $-145 | 195 | - | $-5013 | $-2619 | STOP 444, TRAIL_MA 318, FLIP 32 |
| `sma20_1h_t1` | $-8316 | $-7520 | -83.2% | -0.43 | -93.3% | 806 | 38% | $+175 | $-125 | 192 | - | $-5855 | $-2461 | STOP 460, TRAIL_MA 317, FLIP 29 |
| `be_ema20_1h_1r` | $-5807 | $-5011 | -58.1% | -0.10 | -81.0% | 1133 | 46% | $+175 | $-158 | 135 | - | $-4097 | $-1710 | STOP 530, TRAIL_MA 524, STOP_BE 46, FLIP 33 |
| `be_sma20_1h_1r` | $-8212 | $-7416 | -82.1% | -0.41 | -91.6% | 1159 | 44% | $+126 | $-112 | 132 | - | $-6399 | $-1813 | STOP 561, TRAIL_MA 519, STOP_BE 46, FLIP 33 |
| `half_ema20_1h_t1` | $-7893 | $-7097 | -78.9% | -0.41 | -88.5% | 794 | 42% | $+158 | $-129 | 195 | - | $-5442 | $-2451 | STOP 441, T1+TRAIL_MA 318, FLIP 31, T1+STOP 3 |
| `half_sma20_1h_t1` | $-8509 | $-7713 | -85.1% | -0.55 | -92.2% | 806 | 41% | $+134 | $-109 | 192 | - | $-6323 | $-2186 | STOP 457, T1+TRAIL_MA 317, FLIP 28, T1+STOP 3 |

### USDJPY: 2020-04-08 21:00 to 2026-11-13 03:45 UTC, buy and hold +46.91%, fee 0.010% a side

Main book: top 6 trades $+68176 of $+19209 net (355%).

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | Avg hold (bars) | Top-6 share | 1st half | 2nd half | Exits |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+19209 | $+0 | +192.1% | 0.63 | -58.2% | 120 | 18% | $+3881 | $-648 | 1362 | 355% | $+32607 | $-13398 | STOP 87, FLIP 33 |
| `b_targets` | $+2939 | $-16271 | +29.4% | 0.28 | -49.5% | 744 | 43% | $+348 | $-256 | 216 | 223% | $+795 | $+2144 | STOP 403, T1+T2 203, T1+STOP_BE 105, FLIP 29 |
| `b_trail` | $-5585 | $-24794 | -55.9% | -0.20 | -74.7% | 1537 | 50% | $+182 | $-188 | 102 | - | $-99 | $-5486 | TRAIL 767, STOP 735, FLIP 35 |
| `be_t1` | $+27238 | $+8028 | +272.4% | 0.73 | -57.5% | 145 | 14% | $+4756 | $-562 | 1126 | 299% | $+40322 | $-13084 | STOP 77, STOP_BE 39, FLIP 29 |
| `ema20_15m_1r` | $-5518 | $-24727 | -55.2% | -0.19 | -70.7% | 1469 | 49% | $+177 | $-174 | 107 | - | $-1102 | $-4416 | TRAIL_MA 723, STOP 714, FLIP 32 |
| `ema50_15m_1r` | $-4522 | $-23731 | -45.2% | -0.08 | -71.7% | 1372 | 48% | $+207 | $-197 | 115 | - | $+74 | $-4596 | TRAIL_MA 671, STOP 669, FLIP 32 |
| `ema20_1h_1r` | $-5543 | $-24752 | -55.4% | -0.16 | -73.6% | 1308 | 47% | $+168 | $-155 | 121 | - | $-2221 | $-3322 | TRAIL_MA 632, STOP 625, FLIP 51 |
| `sma20_15m_1r` | $-4524 | $-23733 | -45.2% | -0.10 | -70.9% | 1510 | 49% | $+216 | $-215 | 104 | - | $+2343 | $-6867 | TRAIL_MA 750, STOP 724, FLIP 36 |
| `sma50_15m_1r` | $-1781 | $-20991 | -17.8% | 0.09 | -68.4% | 1381 | 49% | $+237 | $-226 | 114 | - | $+265 | $-2046 | TRAIL_MA 688, STOP 665, FLIP 28 |
| `sma20_1h_1r` | $-227 | $-19436 | -2.3% | 0.17 | -71.7% | 1293 | 47% | $+299 | $-270 | 122 | - | $+4432 | $-4658 | TRAIL_MA 632, STOP 615, FLIP 46 |
| `ema20_1h_entry` | $-10000 | $-29209 | -100.0% | -4.30 | -100.0% | 11990 | 24% | $+3 | $-2 | 9 | - | $-9954 | $-46 | TRAIL_MA 11915, STOP 57, FLIP 18 |
| `sma20_1h_entry` | $-10000 | $-29209 | -100.0% | -4.34 | -100.0% | 12316 | 25% | $+3 | $-2 | 8 | - | $-9963 | $-37 | TRAIL_MA 12217, STOP 52, FLIP 47 |
| `ema20_1h_t1` | $-107 | $-19316 | -1.1% | 0.17 | -64.3% | 886 | 40% | $+385 | $-252 | 181 | - | $+3820 | $-3927 | STOP 497, TRAIL_MA 348, FLIP 41 |
| `sma20_1h_t1` | $+3960 | $-15250 | +39.6% | 0.32 | -65.1% | 881 | 39% | $+560 | $-355 | 182 | 423% | $+9788 | $-5829 | STOP 494, TRAIL_MA 348, FLIP 39 |
| `be_ema20_1h_1r` | $-5976 | $-25186 | -59.8% | -0.20 | -74.3% | 1324 | 46% | $+163 | $-144 | 120 | - | $-2162 | $-3815 | STOP 624, TRAIL_MA 618, FLIP 52, STOP_BE 30 |
| `be_sma20_1h_1r` | $-931 | $-20141 | -9.3% | 0.14 | -72.7% | 1310 | 46% | $+286 | $-250 | 121 | - | $+3749 | $-4680 | TRAIL_MA 618, STOP 613, FLIP 46, STOP_BE 33 |
| `half_ema20_1h_t1` | $-2977 | $-22187 | -29.8% | -0.01 | -61.9% | 886 | 40% | $+265 | $-187 | 181 | - | $-791 | $-2186 | STOP 491, T1+TRAIL_MA 348, FLIP 40, T1+STOP 6 |
| `half_sma20_1h_t1` | $-1089 | $-20298 | -10.9% | 0.10 | -62.8% | 881 | 41% | $+352 | $-246 | 182 | - | $+2774 | $-3863 | STOP 490, T1+TRAIL_MA 348, FLIP 38, T1+STOP 4 |

### SPX: 2021-01-12 17:30 to 2026-11-12 20:45 UTC, buy and hold +100.35%, fee 0.020% a side

Main book: top 6 trades $+10195 of $+6816 net (150%).

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | Avg hold (bars) | Top-6 share | 1st half | 2nd half | Exits |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+6816 | $+0 | +68.2% | 0.55 | -31.0% | 36 | 22% | $+1332 | $-225 | 944 | 150% | $-688 | $+7503 | STOP 23, FLIP 13 |
| `b_targets` | $+1018 | $-5798 | +10.2% | 0.18 | -26.9% | 237 | 43% | $+339 | $-249 | 155 | 485% | $-14 | $+1031 | STOP 126, T1+T2 64, T1+STOP_BE 39, FLIP 8 |
| `b_trail` | $-3848 | $-10664 | -38.5% | -0.26 | -50.5% | 494 | 50% | $+186 | $-201 | 72 | - | $-2114 | $-1735 | TRAIL 247, STOP 239, FLIP 8 |
| `be_t1` | $+6334 | $-482 | +63.3% | 0.53 | -31.6% | 42 | 19% | $+1207 | $-168 | 808 | 147% | $-1012 | $+7346 | STOP 21, STOP_BE 11, FLIP 10 |
| `ema20_15m_1r` | $+1307 | $-5509 | +13.1% | 0.21 | -33.8% | 473 | 52% | $+284 | $-299 | 75 | 403% | $+2039 | $-732 | TRAIL_MA 247, STOP 219, FLIP 7 |
| `ema50_15m_1r` | $-608 | $-7424 | -6.1% | 0.06 | -38.5% | 422 | 52% | $+242 | $-264 | 85 | - | $+558 | $-1167 | TRAIL_MA 219, STOP 197, FLIP 6 |
| `ema20_1h_1r` | $-2966 | $-9781 | -29.7% | -0.16 | -38.4% | 400 | 48% | $+200 | $-202 | 90 | - | $-2060 | $-906 | STOP 196, TRAIL_MA 196, FLIP 8 |
| `sma20_15m_1r` | $+1051 | $-5764 | +10.5% | 0.19 | -35.6% | 482 | 52% | $+268 | $-282 | 74 | 436% | $+414 | $+637 | TRAIL_MA 250, STOP 226, FLIP 6 |
| `sma50_15m_1r` | $-1075 | $-7891 | -10.8% | 0.03 | -35.1% | 431 | 52% | $+228 | $-251 | 83 | - | $+895 | $-1970 | TRAIL_MA 225, STOP 200, FLIP 6 |
| `sma20_1h_1r` | $-2683 | $-9499 | -26.8% | -0.12 | -41.1% | 409 | 49% | $+212 | $-218 | 88 | - | $-953 | $-1730 | TRAIL_MA 205, STOP 196, FLIP 8 |
| `ema20_1h_entry` | $-8820 | $-15636 | -88.2% | -1.92 | -88.3% | 2664 | 31% | $+24 | $-16 | 9 | - | $-5727 | $-3094 | TRAIL_MA 2645, STOP 19 |
| `sma20_1h_entry` | $-8784 | $-15600 | -87.8% | -1.87 | -88.0% | 2780 | 33% | $+22 | $-15 | 9 | - | $-6003 | $-2781 | TRAIL_MA 2755, STOP 25 |
| `ema20_1h_t1` | $-1921 | $-8737 | -19.2% | -0.06 | -37.0% | 264 | 38% | $+311 | $-202 | 139 | - | $-2090 | $+169 | STOP 152, TRAIL_MA 103, FLIP 9 |
| `sma20_1h_t1` | $-1386 | $-8202 | -13.9% | -0.01 | -35.3% | 270 | 40% | $+323 | $-221 | 136 | - | $-1461 | $+75 | STOP 151, TRAIL_MA 110, FLIP 9 |
| `be_ema20_1h_1r` | $-2771 | $-9587 | -27.7% | -0.14 | -40.7% | 405 | 48% | $+215 | $-211 | 89 | - | $-1451 | $-1320 | STOP 195, TRAIL_MA 194, STOP_BE 9, FLIP 7 |
| `be_sma20_1h_1r` | $-2830 | $-9646 | -28.3% | -0.14 | -41.8% | 411 | 48% | $+215 | $-215 | 87 | - | $-626 | $-2204 | TRAIL_MA 200, STOP 193, STOP_BE 10, FLIP 8 |
| `half_ema20_1h_t1` | $-1804 | $-8620 | -18.0% | -0.06 | -28.7% | 264 | 39% | $+311 | $-214 | 139 | - | $-1178 | $-626 | STOP 152, T1+TRAIL_MA 103, FLIP 9 |
| `half_sma20_1h_t1` | $-1141 | $-7957 | -11.4% | 0.00 | -33.2% | 270 | 41% | $+324 | $-233 | 136 | - | $-558 | $-583 | STOP 151, T1+TRAIL_MA 110, FLIP 9 |

### WTI: 2020-02-27 19:00 to 2026-11-13 03:30 UTC, buy and hold +89.13%, fee 0.040% a side

Main book: top 6 trades $+58672 of $+13328 net (440%).

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | Avg hold (bars) | Top-6 share | 1st half | 2nd half | Exits |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+13328 | $+0 | +133.3% | 0.50 | -67.3% | 156 | 22% | $+3148 | $-784 | 886 | 440% | $+15196 | $-1868 | STOP 96, FLIP 60 |
| `b_targets` | $-3184 | $-16513 | -31.8% | 0.12 | -89.7% | 752 | 41% | $+975 | $-673 | 187 | - | $+8607 | $-11792 | STOP 407, T1+T2 189, T1+STOP_BE 94, FLIP 52 |
| `b_trail` | $-5894 | $-19222 | -58.9% | 0.03 | -92.9% | 1528 | 49% | $+613 | $-605 | 90 | - | $+12475 | $-18370 | TRAIL 744, STOP 729, FLIP 55 |
| `be_t1` | $+9346 | $-3983 | +93.5% | 0.45 | -72.8% | 215 | 15% | $+3801 | $-639 | 668 | 724% | $+27684 | $-18339 | STOP 100, FLIP 60, STOP_BE 55 |
| `ema20_15m_1r` | $-4541 | $-17870 | -45.4% | 0.09 | -89.6% | 1448 | 49% | $+532 | $-523 | 95 | - | $+7742 | $-12283 | TRAIL_MA 707, STOP 682, FLIP 59 |
| `ema50_15m_1r` | $-2465 | $-15793 | -24.6% | 0.19 | -88.3% | 1330 | 49% | $+727 | $-690 | 104 | - | $+15831 | $-18296 | TRAIL_MA 650, STOP 629, FLIP 51 |
| `ema20_1h_1r` | $-759 | $-14087 | -7.6% | 0.25 | -82.4% | 1252 | 48% | $+661 | $-615 | 110 | - | $+12679 | $-13438 | TRAIL_MA 615, STOP 584, FLIP 53 |
| `sma20_15m_1r` | $-3869 | $-17197 | -38.7% | 0.13 | -89.2% | 1464 | 50% | $+653 | $-651 | 94 | - | $+17598 | $-21468 | TRAIL_MA 723, STOP 685, FLIP 56 |
| `sma50_15m_1r` | $-2930 | $-16258 | -29.3% | 0.17 | -89.5% | 1342 | 48% | $+779 | $-721 | 103 | - | $+17257 | $-20187 | TRAIL_MA 658, STOP 633, FLIP 51 |
| `sma20_1h_1r` | $+1348 | $-11980 | +13.5% | 0.30 | -83.3% | 1260 | 49% | $+752 | $-708 | 110 | 2767% | $+14701 | $-13352 | TRAIL_MA 624, STOP 583, FLIP 53 |
| `ema20_1h_entry` | $-10000 | $-23328 | -100.0% | -2.60 | -100.0% | 10817 | 32% | $+27 | $-14 | 9 | - | $-9813 | $-187 | TRAIL_MA 10734, STOP 58, FLIP 25 |
| `sma20_1h_entry` | $-10000 | $-23328 | -100.0% | -2.71 | -100.0% | 11178 | 33% | $+29 | $-16 | 9 | - | $-9821 | $-179 | TRAIL_MA 11077, STOP 63, FLIP 38 |
| `ema20_1h_t1` | $+761 | $-12567 | +7.6% | 0.29 | -84.2% | 836 | 39% | $+1091 | $-689 | 167 | 4483% | $+13574 | $-12813 | STOP 457, TRAIL_MA 323, FLIP 56 |
| `sma20_1h_t1` | $+356 | $-12972 | +3.6% | 0.28 | -85.4% | 847 | 39% | $+1080 | $-689 | 165 | 10090% | $+14510 | $-14154 | STOP 463, TRAIL_MA 326, FLIP 58 |
| `be_ema20_1h_1r` | $-1572 | $-14900 | -15.7% | 0.22 | -83.2% | 1274 | 47% | $+636 | $-565 | 108 | - | $+10834 | $-12406 | TRAIL_MA 603, STOP 585, FLIP 53, STOP_BE 33 |
| `be_sma20_1h_1r` | $+419 | $-12909 | +4.2% | 0.28 | -84.2% | 1280 | 47% | $+730 | $-656 | 108 | 8754% | $+12797 | $-12378 | TRAIL_MA 611, STOP 584, FLIP 53, STOP_BE 32 |
| `half_ema20_1h_t1` | $+1604 | $-11724 | +16.0% | 0.29 | -82.7% | 836 | 40% | $+1095 | $-740 | 167 | 2021% | $+15618 | $-14014 | STOP 456, T1+TRAIL_MA 323, FLIP 53, T1+FLIP 3 |
| `half_sma20_1h_t1` | $+1789 | $-11539 | +17.9% | 0.29 | -86.0% | 847 | 40% | $+1228 | $-824 | 165 | 2100% | $+19977 | $-18188 | STOP 462, T1+TRAIL_MA 326, FLIP 55, T1+FLIP 3 |

### BRENT: 2020-02-27 19:00 to 2026-11-13 03:30 UTC, buy and hold +86.56%, fee 0.040% a side

Main book: top 6 trades $+49520 of $+9012 net (550%).

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | Avg hold (bars) | Top-6 share | 1st half | 2nd half | Exits |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+9012 | $+0 | +90.1% | 0.44 | -76.6% | 161 | 20% | $+2535 | $-598 | 858 | 550% | $+13470 | $-4458 | STOP 108, FLIP 53 |
| `b_targets` | $-1695 | $-10707 | -16.9% | 0.14 | -85.3% | 731 | 41% | $+765 | $-544 | 192 | - | $+7489 | $-9184 | STOP 395, T1+T2 175, T1+STOP_BE 108, FLIP 46 |
| `b_trail` | $-5727 | $-14739 | -57.3% | -0.04 | -92.9% | 1517 | 50% | $+440 | $-440 | 90 | - | $+2728 | $-8455 | TRAIL 749, STOP 719, FLIP 49 |
| `be_t1` | $+354 | $-8659 | +3.5% | 0.24 | -86.4% | 238 | 13% | $+2879 | $-446 | 602 | 15214% | $+23968 | $-23615 | STOP 126, STOP_BE 61, FLIP 51 |
| `ema20_15m_1r` | $-6008 | $-15020 | -60.1% | -0.06 | -92.6% | 1442 | 48% | $+463 | $-442 | 96 | - | $+3065 | $-9074 | TRAIL_MA 700, STOP 687, FLIP 55 |
| `ema50_15m_1r` | $-4571 | $-13583 | -45.7% | 0.04 | -91.4% | 1300 | 47% | $+501 | $-455 | 106 | - | $+2570 | $-7142 | STOP 628, TRAIL_MA 627, FLIP 45 |
| `ema20_1h_1r` | $-2971 | $-11984 | -29.7% | 0.12 | -90.2% | 1197 | 48% | $+552 | $-503 | 116 | - | $+4214 | $-7185 | TRAIL_MA 580, STOP 571, FLIP 46 |
| `sma20_15m_1r` | $-5414 | $-14426 | -54.1% | -0.02 | -89.3% | 1472 | 49% | $+426 | $-414 | 94 | - | $+3793 | $-9207 | TRAIL_MA 721, STOP 697, FLIP 54 |
| `sma50_15m_1r` | $-1303 | $-10315 | -13.0% | 0.18 | -87.1% | 1292 | 48% | $+552 | $-508 | 107 | - | $+6220 | $-7523 | TRAIL_MA 631, STOP 614, FLIP 47 |
| `sma20_1h_1r` | $-3911 | $-12923 | -39.1% | 0.08 | -90.3% | 1201 | 46% | $+505 | $-440 | 116 | - | $+3085 | $-6997 | STOP 579, TRAIL_MA 570, FLIP 52 |
| `ema20_1h_entry` | $-10000 | $-19012 | -100.0% | -3.59 | -100.0% | 10561 | 32% | $+14 | $-8 | 9 | - | $-9891 | $-109 | TRAIL_MA 10478, STOP 64, FLIP 19 |
| `sma20_1h_entry` | $-10000 | $-19012 | -100.0% | -3.42 | -100.0% | 10825 | 32% | $+17 | $-9 | 9 | - | $-9858 | $-141 | TRAIL_MA 10748, STOP 56, FLIP 21 |
| `ema20_1h_t1` | $-555 | $-9567 | -5.5% | 0.21 | -87.5% | 847 | 40% | $+1039 | $-688 | 166 | - | $+13439 | $-13994 | STOP 465, TRAIL_MA 331, FLIP 51 |
| `sma20_1h_t1` | $-3292 | $-12304 | -32.9% | 0.10 | -89.5% | 859 | 38% | $+869 | $-538 | 163 | - | $+6184 | $-9475 | STOP 482, TRAIL_MA 322, FLIP 55 |
| `be_ema20_1h_1r` | $-1702 | $-10714 | -17.0% | 0.17 | -88.4% | 1217 | 46% | $+596 | $-514 | 114 | - | $+7371 | $-9073 | STOP 570, TRAIL_MA 566, FLIP 46, STOP_BE 35 |
| `be_sma20_1h_1r` | $-3462 | $-12474 | -34.6% | 0.10 | -89.8% | 1219 | 45% | $+526 | $-436 | 114 | - | $+3449 | $-6910 | STOP 578, TRAIL_MA 555, FLIP 53, STOP_BE 33 |
| `half_ema20_1h_t1` | $-1118 | $-10130 | -11.2% | 0.17 | -86.0% | 847 | 41% | $+852 | $-594 | 166 | - | $+10480 | $-11598 | STOP 465, T1+TRAIL_MA 331, FLIP 48, T1+FLIP 3 |
| `half_sma20_1h_t1` | $-4252 | $-13264 | -42.5% | 0.02 | -89.9% | 859 | 40% | $+712 | $-473 | 163 | - | $+4537 | $-8789 | STOP 482, T1+TRAIL_MA 322, FLIP 52, T1+FLIP 3 |

## Recommendation for the main book (v5.2 question)

Ranked by pooled net P&L over all eight markets (the registered robust ranking, by the worse half's gap to main, is shown beside it). Main v5.1 (hold to stop or flip): $+329439, Sharpe 0.92, max DD -29.63%.

| Rank | Variant | Net P&L | vs main | Sharpe (main 0.92) | Max DD (main -29.63%) | 1st half vs main | 2nd half vs main | Markets beating main | Rank by worse half |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `be_t1` | $+107673 | $-221766 | 0.62 | -37.05% | $-23231 | $-198534 | 2/8 | 1 |
| 2 | `sma20_1h_t1` | $-24645 | $-354084 | -0.08 | -66.28% | $-118149 | $-235935 | 0/8 | 10 |
| 3 | `ema20_1h_t1` | $-25732 | $-355171 | -0.08 | -68.87% | $-117928 | $-237243 | 0/8 | 12 |
| 4 | `half_ema20_1h_t1` | $-31220 | $-360660 | -0.17 | -68.84% | $-124617 | $-236043 | 0/8 | 11 |
| 5 | `half_sma20_1h_t1` | $-32758 | $-362197 | -0.20 | -70.51% | $-122973 | $-239224 | 0/8 | 14 |
| 6 | `sma20_1h_1r` | $-33431 | $-362870 | -0.17 | -67.41% | $-131865 | $-231005 | 0/8 | 7 |
| 7 | `be_sma20_1h_1r` | $-35006 | $-364445 | -0.19 | -68.22% | $-134687 | $-229758 | 0/8 | 4 |
| 8 | `be_ema20_1h_1r` | $-36788 | $-366228 | -0.21 | -68.80% | $-136197 | $-230031 | 0/8 | 6 |
| 9 | `sma50_15m_1r` | $-36998 | $-366437 | -0.21 | -70.47% | $-128478 | $-237960 | 0/8 | 13 |
| 10 | `ema20_1h_1r` | $-37098 | $-366537 | -0.22 | -69.26% | $-136756 | $-229781 | 0/8 | 5 |
| 11 | `ema50_15m_1r` | $-38049 | $-367488 | -0.24 | -70.65% | $-133138 | $-234350 | 0/8 | 8 |
| 12 | `sma20_15m_1r` | $-44610 | $-374049 | -0.36 | -72.70% | $-127827 | $-246222 | 0/8 | 15 |
| 13 | `ema20_15m_1r` | $-45226 | $-374665 | -0.38 | -72.95% | $-139954 | $-234711 | 0/8 | 9 |
| 14 | `sma20_1h_entry` | $-78781 | $-408220 | -2.88 | -98.61% | $-199480 | $-208739 | 0/8 | 2 |
| 15 | `ema20_1h_entry` | $-78817 | $-408256 | -2.95 | -98.60% | $-199165 | $-209090 | 0/8 | 3 |

**Every one of the 15 trail / break-even variants made less than holding.** The best, `be_t1`, trails main by $221766 (67% of main's net); the worst, `ema20_1h_entry`, by $408256.

- **Best for the main book: `be_t1`** ({"be_t1": true}): net $+107673 vs main $+329439, Sharpe 0.62 vs 0.92, max DD -37.05% vs -29.63%, halves vs main $-23231 / $-198534, ahead of main in 2 of 8 markets.
- **Runner-up: `sma20_1h_t1`** ({"ma_trail": "1h sma20", "ma_arm": "t1"}): net $-24645, Sharpe -0.08, max DD -66.28%, halves vs main $-118149 / $-235935.
- Robust ranking (worse half's gap to main) puts `be_t1` first and `sma20_1h_entry` second (dollar halves compound: see the note on the forward picks above).
- Without ETHUSDT (whose compounding dominates the dollars): `be_t1` vs main $-8554, Sharpe 0.46 vs 0.51, max DD -45.1% vs -37.6%; `sma20_1h_t1` vs main $-82312.

**Plainly:** on this history no exit tried here beats holding to the stop or the flip. The main book wins about one trade in five and its winners are four to six times its losers; its six largest trades per market add up to more than its whole net. Every MA trail cut those winners, re-entered (often by the mandate) and was stopped, turning the pooled profit into a loss. Break-even after Target 1 is the least harmful and the only candidate if the owner still wants a v5.2 profit plan; the cost on this history is real.

## If the owner switches the main book (v5.2): what it needs

Not done here; the main book is unchanged (v5.1). The rule lives once, in `engine15/exits.py` (pure per-bar functions: `ma_trail_step`, `be_stop`, `reached`, and `trail_from_history` for open trades); `shadows.run` calls it and `backtest.run_book` can call the same functions.

1. **Config** (`engine15/config.py`): one key, e.g. `"exit_rule": {"be_t1": True}` (or `{"ma_trail": "1h sma20", "ma_arm": "t1"}`, the same dicts as the H36 grid), and `version` -> `think15-v5.2`, said in the journal's next entry. An empty dict = v5.1.
2. **`backtest.run_book`**: know Target 1 at entry (today `live.py` computes `plan_targets` after the book runs, from the readings row of the decision bar; move it into the book via a `row_of(k)` or a precomputed target array, as `shadows.run` does); per bar after the stop check: `exits.reached` -> `t1_hit`, `exits.be_stop`; at the close `exits.ma_trail_step` on the MA column (`ev["ma_1h_sma20_px"]` etc.); a trail exit is a pending order (`TRAIL_MA`, target 0) through the same next-open fill and late-feed delay; idle as after a stop. New state keys: `stop0`, `t1`, `t1_hit`, `ma_on`, `trail_px` (restored on resume). The stop word after break-even: `STOP_BE` (journal.py line ~127 looks for `STOP` only: widen it).
3. **Open trades at the switch** (state migration, closed bars only): for each open main-book trade call `exits.trail_from_history(pos, entry, stop0=book["stop"] (v5.1 stops never move, so the live stop is the entry stop), t1=book["target_1"], arm, high, low, close, ma, i_in=times.searchsorted(t_in_ms), i_last=last closed row, be_t1=...)`. Set `stop`, `t1_hit`, `ma_on`, `trail_px` from it. If it returns an `exit_row`, the rule would already have closed the trade: close it at the next open and journal it as a switch exit; never back-date a fill.
4. **Shadows**: add `main_v51_hold` (rule `{}`, title "Main v5.1: hold to stop or flip") so the old rule keeps running forward; give `main` (the fresh copy of the main rule) the v5.2 rule (`run_challenger` passes the spec's rule to `shadows.run`). If v5.2 = `be_t1`, `b_be_t1` duplicates `main` and can be retired. New books join flat and the scoreboard compares them with main over their own time (`late_starts`).
5. **Tests to update**: `tests/test_shadows.py::test_run_book_is_unchanged_on_a_fixed_slice` (PINNED: pin v5.1 with an empty exit rule and add a v5.2 pin), `test_shadow_engine_without_rules_is_run_book_exactly` (compare `run_book` under the exit rule with `shadows.run(rule=exit_rule)`, both ways across a resume cut), `tests/test_engine.py` book tests, `tests/test_lean.py` (lean vs full prep through `run_book`), and keep `test_trail_from_history_matches_the_book` and `test_evidence_never_reads_the_future` green.

## The variants (frozen in research/HYPOTHESES.md, H36)

- `be_t1`: {"be_t1": true}
- `ema20_15m_1r`: {"ma_trail": "15m ema20", "ma_arm": "1r"}
- `ema50_15m_1r`: {"ma_trail": "15m ema50", "ma_arm": "1r"}
- `ema20_1h_1r`: {"ma_trail": "1h ema20", "ma_arm": "1r"}
- `sma20_15m_1r`: {"ma_trail": "15m sma20", "ma_arm": "1r"}
- `sma50_15m_1r`: {"ma_trail": "15m sma50", "ma_arm": "1r"}
- `sma20_1h_1r`: {"ma_trail": "1h sma20", "ma_arm": "1r"}
- `ema20_1h_entry`: {"ma_trail": "1h ema20", "ma_arm": "entry"}
- `sma20_1h_entry`: {"ma_trail": "1h sma20", "ma_arm": "entry"}
- `ema20_1h_t1`: {"ma_trail": "1h ema20", "ma_arm": "t1"}
- `sma20_1h_t1`: {"ma_trail": "1h sma20", "ma_arm": "t1"}
- `be_ema20_1h_1r`: {"ma_trail": "1h ema20", "ma_arm": "1r", "be_t1": true}
- `be_sma20_1h_1r`: {"ma_trail": "1h sma20", "ma_arm": "1r", "be_t1": true}
- `half_ema20_1h_t1`: {"ma_trail": "1h ema20", "ma_arm": "t1", "half_t1": true}
- `half_sma20_1h_t1`: {"ma_trail": "1h sma20", "ma_arm": "t1", "half_t1": true}

Conventions: MA trail levels are read at the 15m close from bars closed by then (1h averages: the last closed 1h bar), ratcheted so they never loosen; a close beyond the level exits at the next open; the protective stop stays live inside every bar and comes first; break-even moves the stop to entry from the bar after Target 1 trades; half at Target 1 fills at the target. Fees per side as live.
