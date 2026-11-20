# H59: half at Target 1 + stop to entry on the rest, on the main book's own entries (IN-SAMPLE, not proof)

Written by `research/h59_half_be.py` on 2026-11-20 04:13 UTC. H36's frame in every respect (v5.1 odds as the live step formed them before the v5.2 trust cap, voices walked weekly from 2020-01-01, the main book's entries, sizing, fees, protective stop, flips and mandate; $10,000 per market; halves split at 2023-06-08). Only the exit differs. Paper only.

**Read this plainly:** descriptive and in-sample, on history the project has already read (H36, 13 Nov). `half_be_t1` = `{"half_t1": true, "be_t1": true}` is the 16th exit variant counted on these entries, chosen after H36's results and after the owner had adopted the rule for the S&P 500 main book. It gates nothing. 'Better than hold' (registered, H36's): pooled net above main in both halves, ahead of main in at least 5 of 8 markets, pooled max drawdown no worse.

## H36's window (each market's start to H36's last stored session, 12/13 Nov 2026)

**Reconciliation with H36** (`main`, `be_t1`, `b_targets` per market, net P&L and trades): **NOT exact**; differences below.

| Market | Book | H36 net | Here | Diff $ | H36 trades | Here | Diff |
|---|---|---|---|---|---|---|---|
| SPX | `main` | $+6816 | $+6816 | -0.15 | 36 | 36 | +0 |
| SPX | `be_t1` | $+6334 | $+6334 | -0.44 | 42 | 42 | +0 |
| SPX | `b_targets` | $+1018 | $+724 | -294.37 | 237 | 239 | +2 |
| BTCUSDT | `main` | $-2649 | $+22778 | +25427.39 | 317 | 228 | -89 |
| BTCUSDT | `be_t1` | $-1750 | $+21683 | +23432.65 | 398 | 295 | -103 |
| BTCUSDT | `b_targets` | $-9583 | $-9257 | +326.34 | 1128 | 1056 | -72 |
| ETHUSDT | `main` | $+266807 | $+223486 | -43320.68 | 237 | 208 | -29 |
| ETHUSDT | `be_t1` | $+53596 | $+72923 | +19327.29 | 344 | 299 | -45 |
| ETHUSDT | `b_targets` | $-6380 | $+2947 | +9326.88 | 1043 | 1009 | -34 |
| XAUUSD | `main` | $+17712 | $+22717 | +5004.54 | 134 | 115 | -19 |
| XAUUSD | `be_t1` | $+13945 | $+19611 | +5665.85 | 170 | 147 | -23 |
| XAUUSD | `b_targets` | $-4105 | $-3244 | +860.61 | 749 | 747 | -2 |
| XAGUSD | `main` | $-796 | $+1769 | +2565.09 | 161 | 144 | -17 |
| XAGUSD | `be_t1` | $-1387 | $+18 | +1405.09 | 212 | 197 | -15 |
| XAGUSD | `b_targets` | $-7871 | $-7016 | +854.76 | 737 | 721 | -16 |
| USDJPY | `main` | $+19209 | $+7288 | -11920.71 | 120 | 98 | -22 |
| USDJPY | `be_t1` | $+27238 | $+9424 | -17814.39 | 145 | 122 | -23 |
| USDJPY | `b_targets` | $+2939 | $-394 | -3333.46 | 744 | 719 | -25 |
| WTI | `main` | $+13328 | $+25550 | +12221.88 | 156 | 116 | -40 |
| WTI | `be_t1` | $+9346 | $+16343 | +6996.56 | 215 | 178 | -37 |
| WTI | `b_targets` | $-3184 | $-3599 | -414.70 | 752 | 731 | -21 |
| BRENT | `main` | $+9012 | $+5987 | -3025.29 | 161 | 131 | -30 |
| BRENT | `be_t1` | $+354 | $-1687 | -2040.63 | 238 | 205 | -33 |
| BRENT | `b_targets` | $-1695 | $-5005 | -3310.29 | 731 | 721 | -10 |

**What reproduces and what does not (20 Nov 2026 run).** The main book reproduces H36 exactly only on SPX (main and be_t1 to the cent and trade; b_targets there differs by a few hundred dollars and 2 trades, so Target 2 has moved while Target 1 has not). On the other seven markets the MAIN book itself differs (different trade counts), so the entries differ, not the exit code. Checked: the 15m bars over H36's window are byte-identical to the local copy H36 read (USDJPY, SPX, XAUUSD hashed); exit_study.py, shadows.py, leanprep.py and evcache.py are identical on the server and in the repo; the trust cap (v5.2) is not applied by this frame. The daily equity first departs from H36's on XAUUSD 2020-02-24 and USDJPY 2020-10-30 (SPX: never). Inferred, not proven: the evidence store H36 read on 13 Nov (local, layout 1) is not the store on the server now (rebuilt at version changes since, layout 2), and some readings the voting cards learn from differ, which changes the odds and so the entries. The comparison between the four books below is one consistent run on today's store; the absolute numbers of the seven non-SPX markets are NOT H36's.

### S&P 500 (SPX) first: 2021-01-12 17:30 to 2026-11-12 20:45 UTC, buy and hold +100.35%, fee 0.020% a side

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | 1st half | 2nd half | Exits | Open at end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+6816 | $+0 | +68.2% | 0.55 | -31.0% | 36 | 22% | $+1332 | $-225 | $-688 | $+7503 | STOP 23, FLIP 13 | LONG |
| `b_targets` | $+724 | $-6092 | +7.2% | 0.16 | -26.1% | 239 | 43% | $+334 | $-244 | $-280 | $+1004 | STOP 130, T1+T2 67, T1+STOP_BE 36, FLIP 6 | SHORT |
| `be_t1` | $+6334 | $-482 | +63.3% | 0.53 | -31.6% | 42 | 19% | $+1207 | $-168 | $-1012 | $+7346 | STOP 21, STOP_BE 11, FLIP 10 | LONG (T1 hit) |
| `half_be_t1` | $+4528 | $-2288 | +45.3% | 0.57 | -21.7% | 42 | 43% | $+456 | $-204 | $-463 | $+4991 | STOP 21, T1+STOP_BE 11, T1+FLIP 8, FLIP 2 | LONG (T1 hit) |

### All eight markets together

| Book | Net P&L | Return | vs main | Sharpe | Max DD | 1st half | 2nd half | 1st half vs main | 2nd half vs main | Markets beating main | Trades | Better than hold? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+316391 | +395.49% | $+0 | 0.90 | -32.83% | $+152355 | $+164036 | $+0 | $+0 | 0/8 | 1076 | - |
| `b_targets` | $-24845 | -31.06% | $-341236 | -0.13 | -60.64% | $-4982 | $-19863 | $-157337 | $-183899 | 0/8 | 5943 | no |
| `be_t1` | $+144648 | +180.81% | $-171743 | 0.71 | -23.70% | $+107179 | $+37469 | $-45177 | $-126567 | 1/8 | 1485 | no |
| `half_be_t1` | $+101170 | +126.46% | $-215221 | 0.81 | -15.58% | $+73795 | $+27375 | $-78560 | $-136661 | 0/8 | 1485 | no |

`half_be_t1` against the registered test: 1st half vs main $-78560 (fail), 2nd half vs main $-136661 (fail), ahead of main in 0 of 8 markets (none; needs 5), pooled max DD -15.58% vs main -32.83% (pass). **Better than holding: NO.**

### Net P&L by market (whole window)

| Market | main | be_t1 | b_targets | half_be_t1 | half_be_t1 vs main | half_be_t1 vs be_t1 | half_be_t1 1st / 2nd half | main 1st / 2nd half | DD main / half_be_t1 | Trades main / half_be_t1 | Win main / half_be_t1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SPX | $+6816 | $+6334 | $+724 | $+4528 | $-2288 | $-1805 | $-463 / $+4991 | $-688 / $+7503 | -31.0% / -21.7% | 36 / 42 | 22% / 43% |
| BTCUSDT | $+22778 | $+21683 | $-9257 | $+9614 | $-13164 | $-12068 | $+411 / $+9204 | $+1020 / $+21759 | -81.1% / -76.0% | 228 / 295 | 20% / 45% |
| ETHUSDT | $+223486 | $+72923 | $+2947 | $+55382 | $-168105 | $-17541 | $+22124 / $+33258 | $+99542 / $+123944 | -52.8% / -40.2% | 208 / 299 | 23% / 46% |
| XAUUSD | $+22717 | $+19611 | $-3244 | $+15187 | $-7529 | $-4424 | $-594 / $+15781 | $-3012 / $+25728 | -58.8% / -33.6% | 115 / 147 | 24% / 44% |
| XAGUSD | $+1769 | $+18 | $-7016 | $-1689 | $-3458 | $-1707 | $-874 / $-815 | $+4137 / $-2368 | -78.6% / -70.5% | 144 / 197 | 15% / 40% |
| USDJPY | $+7288 | $+9424 | $-394 | $+4148 | $-3140 | $-5275 | $+8980 / $-4832 | $+14462 / $-7174 | -58.2% / -50.2% | 98 / 122 | 13% / 39% |
| WTI | $+25550 | $+16343 | $-3599 | $+15299 | $-10251 | $-1044 | $+35250 / $-19951 | $+29593 / $-4044 | -55.4% / -51.6% | 116 / 178 | 22% / 42% |
| BRENT | $+5987 | $-1687 | $-5005 | $-1300 | $-7286 | $+387 | $+8961 / $-10260 | $+7300 / $-1314 | -67.2% / -65.1% | 131 / 205 | 18% / 40% |

### Per market, every book

#### BTCUSDT: 2020-02-05 00:00 to 2026-11-13 04:00 UTC, buy and hold +647.05%

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | 1st half | 2nd half | Exits | Open at end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+22778 | $+0 | +227.8% | 0.59 | -81.1% | 228 | 20% | $+2113 | $-418 | $+1020 | $+21759 | STOP 149, FLIP 79 | SHORT |
| `b_targets` | $-9257 | $-32035 | -92.6% | -0.47 | -98.0% | 1056 | 42% | $+250 | $-197 | $-4583 | $-4674 | STOP 567, T1+T2 275, T1+STOP_BE 155, FLIP 54, T1+FLIP 5 | SHORT (T1 hit) |
| `be_t1` | $+21683 | $-1096 | +216.8% | 0.59 | -82.2% | 295 | 16% | $+2181 | $-342 | $+1588 | $+20094 | STOP 141, STOP_BE 87, FLIP 67 | SHORT (T1 hit) |
| `half_be_t1` | $+9614 | $-13164 | +96.1% | 0.46 | -76.0% | 295 | 45% | $+581 | $-435 | $+411 | $+9204 | STOP 141, T1+STOP_BE 87, T1+FLIP 40, FLIP 27 | SHORT (T1 hit) |

#### ETHUSDT: 2020-02-05 00:00 to 2026-11-13 04:00 UTC, buy and hold +922.24%

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | 1st half | 2nd half | Exits | Open at end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+223486 | $+0 | +2234.9% | 1.05 | -52.8% | 208 | 23% | $+16591 | $-3634 | $+99542 | $+123944 | STOP 135, FLIP 73 | SHORT |
| `b_targets` | $+2947 | $-220539 | +29.5% | 0.41 | -76.2% | 1009 | 46% | $+469 | $-391 | $+1600 | $+1347 | STOP 502, T1+T2 273, T1+STOP_BE 175, FLIP 53, T1+FLIP 6 | SHORT (T1 hit) |
| `be_t1` | $+72923 | $-150563 | +729.2% | 0.80 | -56.3% | 299 | 14% | $+6041 | $-784 | $+30457 | $+42467 | STOP 137, STOP_BE 95, FLIP 67 | SHORT (T1 hit) |
| `half_be_t1` | $+55382 | $-168105 | +553.8% | 0.86 | -40.2% | 299 | 46% | $+1477 | $-979 | $+22124 | $+33258 | STOP 137, T1+STOP_BE 95, T1+FLIP 39, FLIP 28 | SHORT (T1 hit) |

#### XAUUSD: 2020-02-21 19:00 to 2026-11-13 03:30 UTC, buy and hold +135.42%

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | 1st half | 2nd half | Exits | Open at end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+22717 | $+0 | +227.2% | 0.68 | -58.8% | 115 | 24% | $+1320 | $-228 | $-3012 | $+25728 | STOP 77, FLIP 38 | SHORT |
| `b_targets` | $-3244 | $-25961 | -32.4% | -0.06 | -74.6% | 747 | 42% | $+167 | $-126 | $-5993 | $+2749 | STOP 414, T1+T2 191, T1+STOP_BE 106, FLIP 35, T1+FLIP 1 | SHORT |
| `be_t1` | $+19611 | $-3106 | +196.1% | 0.66 | -55.7% | 147 | 18% | $+1223 | $-142 | $-2530 | $+22141 | STOP 70, STOP_BE 39, FLIP 38 | SHORT (T1 hit) |
| `half_be_t1` | $+15187 | $-7529 | +151.9% | 0.73 | -33.6% | 147 | 44% | $+468 | $-218 | $-594 | $+15781 | STOP 70, T1+STOP_BE 39, FLIP 21, T1+FLIP 17 | SHORT (T1 hit) |

#### XAGUSD: 2020-02-21 19:00 to 2026-11-13 03:30 UTC, buy and hold +168.56%

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | 1st half | 2nd half | Exits | Open at end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+1769 | $+0 | +17.7% | 0.28 | -78.6% | 144 | 15% | $+1584 | $-274 | $+4137 | $-2368 | STOP 113, FLIP 31 | SHORT |
| `b_targets` | $-7016 | $-8785 | -70.2% | -0.30 | -83.7% | 721 | 44% | $+207 | $-178 | $-4353 | $-2663 | STOP 390, T1+T2 195, T1+STOP_BE 109, FLIP 26, T1+FLIP 1 | SHORT (T1 hit) |
| `be_t1` | $+18 | $-1751 | +0.2% | 0.22 | -82.2% | 197 | 11% | $+1380 | $-175 | $+1112 | $-1094 | STOP 112, STOP_BE 57, FLIP 28 | SHORT (T1 hit) |
| `half_be_t1` | $-1689 | $-3458 | -16.9% | 0.06 | -70.5% | 197 | 40% | $+289 | $-212 | $-874 | $-815 | STOP 112, T1+STOP_BE 57, T1+FLIP 15, FLIP 13 | SHORT (T1 hit) |

#### USDJPY: 2020-04-08 21:00 to 2026-11-13 03:45 UTC, buy and hold +46.91%

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | 1st half | 2nd half | Exits | Open at end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+7288 | $+0 | +72.9% | 0.42 | -58.2% | 98 | 13% | $+3238 | $-423 | $+14462 | $-7174 | STOP 76, FLIP 22 | LONG |
| `b_targets` | $-394 | $-7683 | -3.9% | 0.13 | -53.1% | 719 | 42% | $+266 | $-194 | $-1986 | $+1592 | STOP 399, T1+T2 195, T1+STOP_BE 102, FLIP 22, T1+FLIP 1 | LONG |
| `be_t1` | $+9424 | $+2135 | +94.2% | 0.47 | -56.7% | 122 | 11% | $+3443 | $-336 | $+16804 | $-7380 | STOP 69, STOP_BE 35, FLIP 18 | LONG (T1 hit) |
| `half_be_t1` | $+4148 | $-3140 | +41.5% | 0.36 | -50.2% | 122 | 39% | $+591 | $-337 | $+8980 | $-4832 | STOP 69, T1+STOP_BE 35, T1+FLIP 11, FLIP 7 | LONG (T1 hit) |

#### WTI: 2020-02-27 19:00 to 2026-11-13 03:30 UTC, buy and hold +89.13%

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | 1st half | 2nd half | Exits | Open at end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+25550 | $+0 | +255.5% | 0.63 | -55.4% | 116 | 22% | $+4426 | $-1025 | $+29593 | $-4044 | STOP 82, FLIP 34 | LONG |
| `b_targets` | $-3599 | $-29149 | -36.0% | 0.09 | -90.2% | 731 | 41% | $+922 | $-639 | $+8511 | $-12110 | STOP 405, T1+T2 189, T1+STOP_BE 96, FLIP 36, T1+FLIP 5 | SHORT |
| `be_t1` | $+16343 | $-9207 | +163.4% | 0.54 | -69.3% | 178 | 14% | $+5382 | $-774 | $+45884 | $-29542 | STOP 93, STOP_BE 51, FLIP 34 | SHORT |
| `half_be_t1` | $+15299 | $-10251 | +153.0% | 0.57 | -51.6% | 178 | 42% | $+1484 | $-934 | $+35250 | $-19951 | STOP 93, T1+STOP_BE 51, T1+FLIP 22, FLIP 12 | SHORT |

#### BRENT: 2020-02-27 19:00 to 2026-11-13 03:30 UTC, buy and hold +86.56%

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | 1st half | 2nd half | Exits | Open at end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+5987 | $+0 | +59.9% | 0.38 | -67.2% | 131 | 18% | $+2253 | $-464 | $+7300 | $-1314 | STOP 90, FLIP 41 | LONG |
| `b_targets` | $-5005 | $-10992 | -50.0% | -0.05 | -84.5% | 721 | 41% | $+467 | $-338 | $+2103 | $-7108 | STOP 395, T1+T2 174, T1+STOP_BE 112, FLIP 38, T1+FLIP 2 | SHORT (T1 hit) |
| `be_t1` | $-1687 | $-7673 | -16.9% | 0.17 | -82.9% | 205 | 10% | $+2714 | $-319 | $+14875 | $-16562 | STOP 107, STOP_BE 61, FLIP 37 | SHORT |
| `half_be_t1` | $-1300 | $-7286 | -13.0% | 0.09 | -65.1% | 205 | 40% | $+550 | $-378 | $+8961 | $-10260 | STOP 107, T1+STOP_BE 61, T1+FLIP 19, FLIP 18 | SHORT |

## To the store's last session (H36's frame, longer window)

### S&P 500 (SPX) first: 2021-01-12 17:30 to 2026-11-19 20:45 UTC, buy and hold +89.42%, fee 0.020% a side

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | 1st half | 2nd half | Exits | Open at end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+6320 | $+0 | +63.2% | 0.52 | -31.0% | 37 | 24% | $+1362 | $-225 | $-688 | $+7007 | STOP 23, FLIP 14 | SHORT |
| `b_targets` | $+1283 | $-5036 | +12.8% | 0.20 | -26.1% | 239 | 43% | $+334 | $-244 | $-280 | $+1563 | STOP 130, T1+T2 67, T1+STOP_BE 36, FLIP 6 | SHORT (T1 hit) |
| `be_t1` | $+5851 | $-468 | +58.5% | 0.50 | -31.6% | 43 | 21% | $+1245 | $-168 | $-1012 | $+6863 | STOP 21, FLIP 11, STOP_BE 11 | SHORT (T1 hit) |
| `half_be_t1` | $+4438 | $-1882 | +44.4% | 0.55 | -21.7% | 43 | 44% | $+475 | $-204 | $-463 | $+4900 | STOP 21, T1+STOP_BE 11, T1+FLIP 9, FLIP 2 | SHORT (T1 hit) |

### All eight markets together

| Book | Net P&L | Return | vs main | Sharpe | Max DD | 1st half | 2nd half | 1st half vs main | 2nd half vs main | Markets beating main | Trades | Better than hold? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+339325 | +424.16% | $+0 | 0.92 | -32.83% | $+152355 | $+186970 | $+0 | $+0 | 0/8 | 1080 | - |
| `b_targets` | $-21574 | -26.97% | $-360900 | -0.09 | -60.64% | $-4982 | $-16592 | $-157337 | $-203562 | 0/8 | 5958 | no |
| `be_t1` | $+158137 | +197.67% | $-181188 | 0.74 | -23.70% | $+107179 | $+50959 | $-45177 | $-136012 | 1/8 | 1486 | no |
| `half_be_t1` | $+107974 | +134.97% | $-231352 | 0.85 | -15.58% | $+73795 | $+34179 | $-78560 | $-152791 | 0/8 | 1486 | no |

`half_be_t1` against the registered test: 1st half vs main $-78560 (fail), 2nd half vs main $-152791 (fail), ahead of main in 0 of 8 markets (none; needs 5), pooled max DD -15.58% vs main -32.83% (pass). **Better than holding: NO.**

### Net P&L by market (whole window)

| Market | main | be_t1 | b_targets | half_be_t1 | half_be_t1 vs main | half_be_t1 vs be_t1 | half_be_t1 1st / 2nd half | main 1st / 2nd half | DD main / half_be_t1 | Trades main / half_be_t1 | Win main / half_be_t1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SPX | $+6320 | $+5851 | $+1283 | $+4438 | $-1882 | $-1414 | $-463 / $+4900 | $-688 / $+7007 | -31.0% / -21.7% | 37 / 43 | 24% / 44% |
| BTCUSDT | $+25155 | $+23993 | $-9224 | $+10355 | $-14800 | $-13639 | $+411 / $+9944 | $+1020 / $+24135 | -81.1% / -76.0% | 228 / 295 | 20% / 45% |
| ETHUSDT | $+240638 | $+78291 | $+4139 | $+57567 | $-183071 | $-20724 | $+22124 / $+35443 | $+99542 / $+141096 | -52.8% / -40.2% | 208 / 299 | 23% / 46% |
| XAUUSD | $+26565 | $+23094 | $-2500 | $+16787 | $-9778 | $-6307 | $-594 / $+17381 | $-3012 / $+29576 | -58.8% / -33.6% | 115 / 147 | 24% / 44% |
| XAGUSD | $+3104 | $+1136 | $-6588 | $-1183 | $-4287 | $-2319 | $-874 / $-309 | $+4137 / $-1033 | -78.6% / -70.5% | 144 / 197 | 15% / 40% |
| USDJPY | $+6965 | $+9061 | $-579 | $+4014 | $-2951 | $-5046 | $+8980 / $-4966 | $+14462 / $-7497 | -58.2% / -50.2% | 98 / 122 | 13% / 39% |
| WTI | $+24898 | $+17918 | $-3230 | $+16812 | $-8085 | $-1106 | $+35250 / $-18438 | $+29593 / $-4696 | -55.4% / -51.6% | 118 / 178 | 23% / 42% |
| BRENT | $+5682 | $-1206 | $-4876 | $-816 | $-6498 | $+390 | $+8961 / $-9777 | $+7300 / $-1619 | -67.2% / -65.4% | 132 / 205 | 19% / 40% |

### Per market, every book

#### BTCUSDT: 2020-02-05 00:00 to 2026-11-20 03:45 UTC, buy and hold +574.48%

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | 1st half | 2nd half | Exits | Open at end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+25155 | $+0 | +251.6% | 0.61 | -81.1% | 228 | 20% | $+2113 | $-418 | $+1020 | $+24135 | STOP 149, FLIP 79 | SHORT |
| `b_targets` | $-9224 | $-34379 | -92.2% | -0.45 | -98.0% | 1060 | 42% | $+249 | $-196 | $-4583 | $-4641 | STOP 569, T1+T2 277, T1+STOP_BE 155, FLIP 54, T1+FLIP 5 | SHORT |
| `be_t1` | $+23993 | $-1162 | +239.9% | 0.61 | -82.2% | 295 | 16% | $+2181 | $-342 | $+1588 | $+22405 | STOP 141, STOP_BE 87, FLIP 67 | SHORT (T1 hit) |
| `half_be_t1` | $+10355 | $-14800 | +103.5% | 0.47 | -76.0% | 295 | 45% | $+581 | $-435 | $+411 | $+9944 | STOP 141, T1+STOP_BE 87, T1+FLIP 40, FLIP 27 | SHORT (T1 hit) |

#### ETHUSDT: 2020-02-05 00:00 to 2026-11-20 03:45 UTC, buy and hold +822.49%

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | 1st half | 2nd half | Exits | Open at end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+240638 | $+0 | +2406.4% | 1.06 | -52.8% | 208 | 23% | $+16591 | $-3634 | $+99542 | $+141096 | STOP 135, FLIP 73 | SHORT |
| `b_targets` | $+4139 | $-236499 | +41.4% | 0.42 | -76.2% | 1011 | 46% | $+470 | $-391 | $+1600 | $+2539 | STOP 502, T1+T2 274, T1+STOP_BE 176, FLIP 53, T1+FLIP 6 | SHORT |
| `be_t1` | $+78291 | $-162347 | +782.9% | 0.82 | -56.3% | 299 | 14% | $+6041 | $-784 | $+30457 | $+47834 | STOP 137, STOP_BE 95, FLIP 67 | SHORT (T1 hit) |
| `half_be_t1` | $+57567 | $-183071 | +575.7% | 0.87 | -40.2% | 299 | 46% | $+1477 | $-979 | $+22124 | $+35443 | STOP 137, T1+STOP_BE 95, T1+FLIP 39, FLIP 28 | SHORT (T1 hit) |

#### XAUUSD: 2020-02-21 19:00 to 2026-11-20 03:30 UTC, buy and hold +113.32%

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | 1st half | 2nd half | Exits | Open at end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+26565 | $+0 | +265.6% | 0.73 | -58.8% | 115 | 24% | $+1320 | $-228 | $-3012 | $+29576 | STOP 77, FLIP 38 | SHORT |
| `b_targets` | $-2500 | $-29065 | -25.0% | -0.00 | -74.6% | 750 | 42% | $+168 | $-126 | $-5993 | $+3493 | STOP 414, T1+T2 194, T1+STOP_BE 106, FLIP 35, T1+FLIP 1 | SHORT |
| `be_t1` | $+23094 | $-3471 | +230.9% | 0.71 | -55.7% | 147 | 18% | $+1223 | $-142 | $-2530 | $+25624 | STOP 70, STOP_BE 39, FLIP 38 | SHORT (T1 hit) |
| `half_be_t1` | $+16787 | $-9778 | +167.9% | 0.77 | -33.6% | 147 | 44% | $+468 | $-218 | $-594 | $+17381 | STOP 70, T1+STOP_BE 39, FLIP 21, T1+FLIP 17 | SHORT (T1 hit) |

#### XAGUSD: 2020-02-21 19:00 to 2026-11-20 03:30 UTC, buy and hold +122.96%

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | 1st half | 2nd half | Exits | Open at end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+3104 | $+0 | +31.0% | 0.31 | -78.6% | 144 | 15% | $+1584 | $-274 | $+4137 | $-1033 | STOP 113, FLIP 31 | SHORT |
| `b_targets` | $-6588 | $-9692 | -65.9% | -0.24 | -83.7% | 725 | 44% | $+205 | $-178 | $-4353 | $-2235 | STOP 390, T1+T2 199, T1+STOP_BE 109, FLIP 26, T1+FLIP 1 | SHORT |
| `be_t1` | $+1136 | $-1968 | +11.4% | 0.26 | -82.2% | 197 | 11% | $+1380 | $-175 | $+1112 | $+23 | STOP 112, STOP_BE 57, FLIP 28 | SHORT (T1 hit) |
| `half_be_t1` | $-1183 | $-4287 | -11.8% | 0.09 | -70.5% | 197 | 40% | $+289 | $-212 | $-874 | $-309 | STOP 112, T1+STOP_BE 57, T1+FLIP 15, FLIP 13 | SHORT (T1 hit) |

#### USDJPY: 2020-04-08 21:00 to 2026-11-20 03:45 UTC, buy and hold +46.31%

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | 1st half | 2nd half | Exits | Open at end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+6965 | $+0 | +69.7% | 0.41 | -58.2% | 98 | 13% | $+3238 | $-423 | $+14462 | $-7497 | STOP 76, FLIP 22 | LONG |
| `b_targets` | $-579 | $-7544 | -5.8% | 0.12 | -53.1% | 721 | 42% | $+265 | $-194 | $-1986 | $+1407 | STOP 400, T1+T2 195, T1+STOP_BE 103, FLIP 22, T1+FLIP 1 | LONG |
| `be_t1` | $+9061 | $+2095 | +90.6% | 0.46 | -56.7% | 122 | 11% | $+3443 | $-336 | $+16804 | $-7743 | STOP 69, STOP_BE 35, FLIP 18 | LONG (T1 hit) |
| `half_be_t1` | $+4014 | $-2951 | +40.1% | 0.35 | -50.2% | 122 | 39% | $+591 | $-337 | $+8980 | $-4966 | STOP 69, T1+STOP_BE 35, T1+FLIP 11, FLIP 7 | LONG (T1 hit) |

#### WTI: 2020-02-27 19:00 to 2026-11-20 03:30 UTC, buy and hold +77.64%

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | 1st half | 2nd half | Exits | Open at end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+24898 | $+0 | +249.0% | 0.62 | -55.4% | 118 | 23% | $+4316 | $-1022 | $+29593 | $-4696 | STOP 83, FLIP 35 | SHORT |
| `b_targets` | $-3230 | $-28127 | -32.3% | 0.11 | -90.2% | 731 | 41% | $+922 | $-639 | $+8511 | $-11741 | STOP 405, T1+T2 189, T1+STOP_BE 96, FLIP 36, T1+FLIP 5 | SHORT (T1 hit) |
| `be_t1` | $+17918 | $-6979 | +179.2% | 0.55 | -69.5% | 178 | 14% | $+5382 | $-774 | $+45884 | $-27966 | STOP 93, STOP_BE 51, FLIP 34 | SHORT |
| `half_be_t1` | $+16812 | $-8085 | +168.1% | 0.59 | -51.6% | 178 | 42% | $+1484 | $-934 | $+35250 | $-18438 | STOP 93, T1+STOP_BE 51, T1+FLIP 22, FLIP 12 | SHORT |

#### BRENT: 2020-02-27 19:00 to 2026-11-20 03:30 UTC, buy and hold +75.75%

| Book | Net P&L | vs main | Return | Sharpe | Max DD | Trades | Win | Avg win | Avg loss | 1st half | 2nd half | Exits | Open at end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+5682 | $+0 | +56.8% | 0.37 | -67.2% | 132 | 19% | $+2201 | $-464 | $+7300 | $-1619 | STOP 90, FLIP 42 | SHORT |
| `b_targets` | $-4876 | $-10557 | -48.8% | -0.04 | -84.5% | 721 | 41% | $+467 | $-338 | $+2103 | $-6979 | STOP 395, T1+T2 174, T1+STOP_BE 112, FLIP 38, T1+FLIP 2 | SHORT (T1 hit) |
| `be_t1` | $-1206 | $-6888 | -12.1% | 0.19 | -83.0% | 205 | 10% | $+2714 | $-319 | $+14875 | $-16082 | STOP 107, STOP_BE 61, FLIP 37 | SHORT (T1 hit) |
| `half_be_t1` | $-816 | $-6498 | -8.2% | 0.11 | -65.4% | 205 | 40% | $+550 | $-378 | $+8961 | $-9777 | STOP 107, T1+STOP_BE 61, T1+FLIP 19, FLIP 18 | SHORT (T1 hit) |

Conventions (shadows.run): half at Target 1 is a limit at the target, filled when a bar reaches it, after the stop check in that bar; the stop moves to the entry from the next bar, only ever tighter; a trade that took half at Target 1 is one trade (exit word `T1+...`). Target 1 is `live.plan_targets` at entry. Sharpe on daily marked equity, sqrt(365). Pooled: markets' daily equity summed, a market not yet trading at $10,000.
