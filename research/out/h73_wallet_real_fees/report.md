# H73: one member wallet on the BTC and ETH trades of three engine books, three sizings, three fees

History replay 2020-02-05 00:00 to 2026-11-21 13:45 UTC, paper, registered before any number (research/HYPOTHESES.md, H73). A description of history under stated assumptions, not a forecast and not advice. The two variants (b_trend30, b_wait_stop) were FOUND on this same history: their numbers cannot show an advantage.

Trades (closed + open at the cut): b_targets 2075, b_trend30 1816, b_wait_stop 1763. Closed per coin: b_targets BTCUSDT 1062, b_trend30 BTCUSDT 895, b_wait_stop BTCUSDT 880, b_targets ETHUSDT 1012, b_trend30 ETHUSDT 920, b_wait_stop ETHUSDT 881. Entries booked at the last close and dropped: b_targets ETHUSDT 1, b_trend30 ETHUSDT 1.

Funding from the stored Binance series (BTCUSDT 7884, ETHUSDT 7650 rows used; 8 funding times had no bar). The paper book's own fee: 0.10% per side.

Gate: b_targets BTCUSDT passed (largest relative gap 2.98e-15 over 238079 bars, 1063 trades); b_trend30 BTCUSDT passed (largest relative gap 2.71e-15 over 238079 bars, 896 trades); b_wait_stop BTCUSDT passed (largest relative gap 5.15e-15 over 238079 bars, 881 trades); b_targets ETHUSDT passed (largest relative gap 3.51e-15 over 238079 bars, 1012 trades); b_trend30 ETHUSDT passed (largest relative gap 3.09e-15 over 238079 bars, 920 trades); b_wait_stop ETHUSDT passed (largest relative gap 5.72e-15 over 238079 bars, 882 trades)

Not modelled: the member's actual fee rate (not available), slippage against the book's prices, the vault's join window, refusals, exchange limits, rounding. The brake is H63's model of the vault's, not its code.

## 1. The primary cells: 100% per coin (S2), fee 0.05% per side

`*` = a variant found on this same history (found on this same history: cannot show an advantage).

| Cell | Final | Worst fall | Lowest equity | Worst UTC day | Longest losing run | Joined / trimmed / capped / not joined | Fees | Funding paid | Final without funding | Wiped out |
|---|---|---|---|---|---|---|---|---|---|---|
| current rule | 6,198 | -94.6% | 2,832 (2025-10-29) | -19.4% (2026-02-06) | 13 | 2044 / 168 / 0 / 31 | 26,920 | 14,156 | 12,278 | no |
| 30-day trend filter * | 245,417 | -74.8% | 8,910 (2020-03-05) | -19.4% (2026-02-06) | 15 | 1780 / 145 / 0 / 36 | 197,760 | 66,658 | 555,892 | no |
| wait after a stop-out * | 65,262 | -80.2% | 6,508 (2020-04-17) | -19.4% (2026-02-06) | 13 | 1748 / 107 / 0 / 15 | 71,139 | 13,203 | 106,557 | no |

Month-start table (a fresh 10,000 from every month-start, 365 days):

| Cell | Starts | +100% first | -50% or wipe-out first (of which wiped) | Neither (median end) | Unfinished | Median days to either | to +100% | to -50% |
|---|---|---|---|---|---|---|---|---|
| current rule | 81 | 21 | 25 (0) | 26 (8,474) | 9 | 172 | 135 | 248 |
| 30-day trend filter * | 81 | 37 | 6 (0) | 30 (11,134) | 8 | 184 | 164 | 246 |
| wait after a stop-out * | 81 | 30 | 5 (0) | 36 (9,498) | 10 | 174 | 157 | 243 |

Monthly returns (complete calendar months of the whole-run wallet; months resampled with replacement, 10000 draws, seed 73; this treats months as exchangeable, which they are not exactly):

| Cell | Complete months | Mean month (90% bootstrap interval) | Median month | Months up | Worst / best month | 12-month paths ending above start | 12-month paths below half at a month-end | Median 12-month path end |
|---|---|---|---|---|---|---|---|---|
| current rule | 80 | +1.64% (-2.57% to +6.10%) | -1.92% | 49% | -39.5% / +71.0% | 43.6% | 33.9% | 0.89x |
| 30-day trend filter * | 80 | +5.84% (+1.76% to +10.08%) | +0.27% | 51% | -29.0% / +77.2% | 72.6% | 10.0% | 1.53x |
| wait after a stop-out * | 80 | +4.25% (+0.59% to +8.01%) | +1.66% | 55% | -36.4% / +67.6% | 66.6% | 11.1% | 1.32x |

Fresh 10,000 wallets by period (primary cells):

first half (to 2023-06-07):

| Cell | Final | Worst fall | Lowest equity | Worst UTC day | Longest losing run | Joined / trimmed / capped / not joined | Fees | Funding paid | Final without funding | Wiped out |
|---|---|---|---|---|---|---|---|---|---|---|
| current rule | 17,860 | -75.8% | 6,897 (2020-03-08) | -19.1% (2021-02-22) | 10 | 966 / 133 / 0 / 25 | 18,715 | 12,248 | 30,854 | no |
| 30-day trend filter * | 155,562 | -58.5% | 8,910 (2020-03-05) | -16.8% (2021-01-21) | 15 | 832 / 111 / 0 / 31 | 59,288 | 33,814 | 297,377 | no |
| wait after a stop-out * | 58,860 | -63.8% | 6,508 (2020-04-17) | -16.1% (2021-02-15) | 10 | 894 / 96 / 0 / 14 | 33,883 | 9,579 | 90,017 | no |

second half (2023-06-08 on):

| Cell | Final | Worst fall | Lowest equity | Worst UTC day | Longest losing run | Joined / trimmed / capped / not joined | Fees | Funding paid | Final without funding | Wiped out |
|---|---|---|---|---|---|---|---|---|---|---|
| current rule | 3,657 | -89.0% | 1,671 (2025-10-29) | -19.4% (2026-02-06) | 13 | 1078 / 35 / 0 / 6 | 4,820 | 1,142 | 4,200 | no |
| 30-day trend filter * | 16,689 | -74.8% | 5,880 (2025-07-08) | -19.4% (2026-02-06) | 9 | 948 / 34 / 0 / 5 | 9,394 | 2,255 | 19,815 | no |
| wait after a stop-out * | 11,516 | -64.4% | 4,795 (2026-01-28) | -19.4% (2026-02-06) | 13 | 854 / 11 / 0 / 1 | 6,552 | 660 | 12,322 | no |

holdout (2025-11-11 on):

| Cell | Final | Worst fall | Lowest equity | Worst UTC day | Longest losing run | Joined / trimmed / capped / not joined | Fees | Funding paid | Final without funding | Wiped out |
|---|---|---|---|---|---|---|---|---|---|---|
| current rule | 18,876 | -52.3% | 8,977 (2026-08-19) | -19.4% (2026-02-06) | 7 | 306 / 3 / 0 / 0 | 3,623 | -100 | 18,700 | no |
| 30-day trend filter * | 19,966 | -42.7% | 8,481 (2026-01-28) | -19.4% (2026-02-06) | 8 | 285 / 5 / 0 / 0 | 3,418 | -30 | 19,906 | no |
| wait after a stop-out * | 17,086 | -50.4% | 7,114 (2026-01-28) | -19.4% (2026-02-06) | 11 | 210 / 3 / 0 / 0 | 2,348 | -75 | 16,948 | no |

## current rule (b_targets): all sizings and fees

Whole replay:

| Cell | Final | Worst fall | Lowest equity | Worst UTC day | Longest losing run | Joined / trimmed / capped / not joined | Fees | Funding paid | Final without funding | Wiped out |
|---|---|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check) | 3,251 | -86.7% | 2,285 (2026-08-19) | -6.6% (2024-03-05) | 13 | 1903 / 345 / 993 / 172 | 14,559 | 3,462 | 4,385 | no |
| S1: 2% rule, fee 0.05% (taker, PRIMARY) | 8,561 | -74.5% | 5,578 (2025-10-29) | -6.5% (2024-03-05) | 13 | 1910 / 323 / 1009 / 165 | 10,590 | 4,187 | 11,532 | no |
| S1: 2% rule, fee 0.02% (maker-like bound) | 15,327 | -65.6% | 8,667 (2020-03-08) | -6.5% (2024-03-05) | 13 | 1920 / 316 / 1013 / 155 | 5,487 | 4,764 | 20,668 | no |
| S2: 100% per coin, fee 0.10% (H63's, check) | 861 | -98.6% | 433 (2026-08-19) | -19.6% (2026-02-06) | 13 | 2040 / 174 / 0 / 35 | 28,741 | 9,945 | 1,704 | no |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY) | 6,198 | -94.6% | 2,832 (2025-10-29) | -19.4% (2026-02-06) | 13 | 2044 / 168 / 0 / 31 | 26,920 | 14,156 | 12,278 | no |
| S2: 100% per coin, fee 0.02% (maker-like bound) | 20,287 | -90.0% | 7,034 (2020-03-08) | -19.3% (2026-02-06) | 13 | 2045 / 165 / 0 / 30 | 17,266 | 18,387 | 40,089 | no |
| S3: 3x book, fee 0.10% (H63's, check) | 104 | -99.9% | 42 (2026-08-19) | -21.7% (2026-02-06) | 13 | 1963 / 477 / 0 / 112 | 32,736 | 11,654 | 241 | no |
| S3: 3x book, fee 0.05% (taker, PRIMARY) | 1,616 | -99.1% | 592 (2026-08-19) | -21.3% (2026-02-06) | 13 | 1969 / 463 / 0 / 106 | 31,056 | 17,649 | 3,764 | no |
| S3: 3x book, fee 0.02% (maker-like bound) | 8,467 | -97.8% | 2,475 (2025-10-29) | -21.2% (2026-02-06) | 13 | 1978 / 460 / 0 / 97 | 20,147 | 23,824 | 19,791 | no |

Month-starts:

| Cell | Starts | +100% first | -50% or wipe-out first (of which wiped) | Neither (median end) | Unfinished | Median days to either | to +100% | to -50% |
|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check) | 81 | 0 | 4 (0) | 65 (7,984) | 12 | 313 | n/a | 313 |
| S1: 2% rule, fee 0.05% (taker, PRIMARY) | 81 | 1 | 1 (0) | 67 (9,115) | 12 | 319 | 316 | 321 |
| S1: 2% rule, fee 0.02% (maker-like bound) | 81 | 3 | 0 (0) | 66 (9,454) | 12 | 313 | 313 | n/a |
| S2: 100% per coin, fee 0.10% (H63's, check) | 81 | 16 | 37 (0) | 16 (6,930) | 12 | 187 | 123 | 222 |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY) | 81 | 21 | 25 (0) | 26 (8,474) | 9 | 172 | 135 | 248 |
| S2: 100% per coin, fee 0.02% (maker-like bound) | 81 | 28 | 13 (0) | 33 (9,282) | 7 | 186 | 161 | 212 |
| S3: 3x book, fee 0.10% (H63's, check) | 81 | 24 | 54 (0) | 1 (7,463) | 2 | 129 | 83 | 166 |
| S3: 3x book, fee 0.05% (taker, PRIMARY) | 81 | 32 | 38 (0) | 10 (8,611) | 1 | 110 | 88 | 167 |
| S3: 3x book, fee 0.02% (maker-like bound) | 81 | 42 | 25 (0) | 12 (9,335) | 2 | 124 | 105 | 139 |

Month-starts before / from 2023-06-08:

| Cell | Starts | +100% first | -50% or wipe-out first (of which wiped) | Neither (median end) | Unfinished | Median days to either | to +100% | to -50% |
|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check), first half | 40 | 0 | 0 (0) | 40 (8,566) | 0 | n/a | n/a | n/a |
| S1: 2% rule, fee 0.05% (taker, PRIMARY), first half | 40 | 1 | 0 (0) | 39 (9,453) | 0 | 316 | 316 | n/a |
| S1: 2% rule, fee 0.02% (maker-like bound), first half | 40 | 3 | 0 (0) | 37 (10,108) | 0 | 313 | 313 | n/a |
| S2: 100% per coin, fee 0.10% (H63's, check), first half | 40 | 15 | 17 (0) | 8 (7,050) | 0 | 174 | 132 | 230 |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY), first half | 40 | 17 | 8 (0) | 15 (7,957) | 0 | 154 | 135 | 204 |
| S2: 100% per coin, fee 0.02% (maker-like bound), first half | 40 | 22 | 4 (0) | 14 (9,311) | 0 | 161 | 147 | 244 |
| S3: 3x book, fee 0.10% (H63's, check), first half | 40 | 16 | 24 (0) | 0 (n/a) | 0 | 125 | 96 | 191 |
| S3: 3x book, fee 0.05% (taker, PRIMARY), first half | 40 | 19 | 14 (0) | 7 (7,716) | 0 | 97 | 94 | 153 |
| S3: 3x book, fee 0.02% (maker-like bound), first half | 40 | 24 | 10 (0) | 6 (9,966) | 0 | 99 | 99 | 108 |
| S1: 2% rule, fee 0.10% (H63's, check), second half | 41 | 0 | 4 (0) | 25 (6,796) | 12 | 313 | n/a | 313 |
| S1: 2% rule, fee 0.05% (taker, PRIMARY), second half | 41 | 0 | 1 (0) | 28 (7,967) | 12 | 321 | n/a | 321 |
| S1: 2% rule, fee 0.02% (maker-like bound), second half | 41 | 0 | 0 (0) | 29 (8,574) | 12 | n/a | n/a | n/a |
| S2: 100% per coin, fee 0.10% (H63's, check), second half | 41 | 1 | 20 (0) | 8 (6,928) | 12 | 215 | 64 | 215 |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY), second half | 41 | 4 | 17 (0) | 11 (8,814) | 9 | 243 | 158 | 254 |
| S2: 100% per coin, fee 0.02% (maker-like bound), second half | 41 | 6 | 9 (0) | 19 (9,282) | 7 | 204 | 219 | 190 |
| S3: 3x book, fee 0.10% (H63's, check), second half | 41 | 8 | 30 (0) | 1 (7,463) | 2 | 143 | 55 | 157 |
| S3: 3x book, fee 0.05% (taker, PRIMARY), second half | 41 | 13 | 24 (0) | 3 (9,914) | 1 | 118 | 81 | 167 |
| S3: 3x book, fee 0.02% (maker-like bound), second half | 41 | 18 | 15 (0) | 6 (9,129) | 2 | 135 | 117 | 202 |

first half (to 2023-06-07), fresh 10,000:

| Cell | Final | Worst fall | Lowest equity | Worst UTC day | Longest losing run | Joined / trimmed / capped / not joined | Fees | Funding paid | Final without funding | Wiped out |
|---|---|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check) | 8,559 | -50.9% | 8,449 (2023-06-07) | -6.5% (2021-08-05) | 13 | 917 / 217 / 303 / 74 | 9,548 | 3,006 | 10,780 | no |
| S1: 2% rule, fee 0.05% (taker, PRIMARY) | 12,828 | -44.3% | 8,609 (2020-03-08) | -6.4% (2021-08-05) | 13 | 921 / 210 / 308 / 70 | 5,864 | 3,424 | 16,151 | no |
| S1: 2% rule, fee 0.02% (maker-like bound) | 16,423 | -42.0% | 8,667 (2020-03-08) | -6.3% (2021-08-05) | 13 | 924 / 207 / 309 / 67 | 2,674 | 3,720 | 20,702 | no |
| S2: 100% per coin, fee 0.10% (H63's, check) | 7,176 | -82.1% | 5,526 (2023-03-05) | -19.2% (2021-02-22) | 10 | 963 / 138 / 0 / 28 | 24,001 | 9,320 | 12,377 | no |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY) | 17,860 | -75.8% | 6,897 (2020-03-08) | -19.1% (2021-02-22) | 10 | 966 / 133 / 0 / 25 | 18,715 | 12,248 | 30,854 | no |
| S2: 100% per coin, fee 0.02% (maker-like bound) | 30,910 | -73.2% | 7,034 (2020-03-08) | -19.0% (2021-02-22) | 10 | 967 / 130 / 0 / 24 | 10,059 | 14,624 | 53,279 | no |
| S3: 3x book, fee 0.10% (H63's, check) | 3,445 | -93.0% | 2,813 (2023-03-05) | -19.9% (2021-10-01) | 13 | 914 / 336 / 0 / 77 | 30,741 | 11,356 | 6,548 | no |
| S3: 3x book, fee 0.05% (taker, PRIMARY) | 10,858 | -88.1% | 6,543 (2020-04-20) | -19.6% (2021-10-01) | 13 | 917 / 326 / 0 / 74 | 26,489 | 16,384 | 20,705 | no |
| S3: 3x book, fee 0.02% (maker-like bound) | 21,581 | -86.7% | 6,826 (2020-04-20) | -19.4% (2021-10-01) | 13 | 924 / 325 / 0 / 67 | 15,235 | 20,750 | 41,433 | no |

second half (2023-06-08 on), fresh 10,000:

| Cell | Final | Worst fall | Lowest equity | Worst UTC day | Longest losing run | Joined / trimmed / capped / not joined | Fees | Funding paid | Final without funding | Wiped out |
|---|---|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check) | 3,916 | -76.4% | 2,752 (2026-08-19) | -6.6% (2024-03-05) | 13 | 987 / 128 / 690 / 97 | 6,028 | 557 | 4,197 | no |
| S1: 2% rule, fee 0.05% (taker, PRIMARY) | 6,877 | -65.1% | 4,480 (2025-10-29) | -6.5% (2024-03-05) | 13 | 991 / 113 / 701 / 93 | 3,792 | 622 | 7,363 | no |
| S1: 2% rule, fee 0.02% (maker-like bound) | 9,614 | -58.5% | 5,643 (2025-10-29) | -6.5% (2024-03-05) | 13 | 998 / 109 / 704 / 86 | 1,763 | 663 | 10,293 | no |
| S2: 100% per coin, fee 0.10% (H63's, check) | 1,267 | -94.9% | 638 (2026-08-19) | -19.6% (2026-02-06) | 13 | 1077 / 36 / 0 / 7 | 6,933 | 936 | 1,457 | no |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY) | 3,657 | -89.0% | 1,671 (2025-10-29) | -19.4% (2026-02-06) | 13 | 1078 / 35 / 0 / 6 | 4,820 | 1,142 | 4,200 | no |
| S2: 100% per coin, fee 0.02% (maker-like bound) | 6,908 | -84.5% | 2,632 (2025-10-29) | -19.3% (2026-02-06) | 13 | 1078 / 35 / 0 / 6 | 2,446 | 1,297 | 7,932 | no |
| S3: 3x book, fee 0.10% (H63's, check) | 328 | -99.0% | 131 (2026-08-19) | -21.7% (2026-02-06) | 13 | 1049 / 141 / 0 / 35 | 6,224 | 965 | 400 | no |
| S3: 3x book, fee 0.05% (taker, PRIMARY) | 1,612 | -95.5% | 590 (2026-08-19) | -21.3% (2026-02-06) | 13 | 1052 / 137 / 0 / 32 | 4,521 | 1,286 | 1,973 | no |
| S3: 3x book, fee 0.02% (maker-like bound) | 4,240 | -92.3% | 1,240 (2025-10-29) | -21.2% (2026-02-06) | 13 | 1054 / 135 / 0 / 30 | 2,447 | 1,564 | 5,175 | no |

holdout (2025-11-11 on), fresh 10,000:

| Cell | Final | Worst fall | Lowest equity | Worst UTC day | Longest losing run | Joined / trimmed / capped / not joined | Fees | Funding paid | Final without funding | Wiped out |
|---|---|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check) | 12,197 | -36.0% | 8,571 (2026-08-19) | -5.9% (2026-02-06) | 7 | 283 / 18 / 212 / 23 | 3,528 | -81 | 12,093 | no |
| S1: 2% rule, fee 0.05% (taker, PRIMARY) | 14,410 | -29.8% | 9,818 (2026-08-19) | -5.8% (2026-02-06) | 8 | 284 / 16 / 214 / 22 | 1,918 | -88 | 14,289 | no |
| S1: 2% rule, fee 0.02% (maker-like bound) | 15,943 | -25.9% | 9,951 (2025-11-11) | -5.7% (2026-02-06) | 7 | 286 / 14 / 214 / 20 | 809 | -92 | 15,817 | no |
| S2: 100% per coin, fee 0.10% (H63's, check) | 14,023 | -59.8% | 7,055 (2026-08-19) | -19.6% (2026-02-06) | 7 | 305 / 3 / 0 / 1 | 6,269 | -92 | 13,895 | no |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY) | 18,876 | -52.3% | 8,977 (2026-08-19) | -19.4% (2026-02-06) | 7 | 306 / 3 / 0 / 0 | 3,623 | -100 | 18,700 | no |
| S2: 100% per coin, fee 0.02% (maker-like bound) | 22,551 | -47.2% | 9,552 (2026-01-21) | -19.3% (2026-02-06) | 7 | 306 / 3 / 0 / 0 | 1,586 | -106 | 22,342 | no |
| S3: 3x book, fee 0.10% (H63's, check) | 13,486 | -72.1% | 5,393 (2026-08-19) | -21.7% (2026-02-06) | 7 | 304 / 22 / 0 / 2 | 8,581 | -154 | 13,267 | no |
| S3: 3x book, fee 0.05% (taker, PRIMARY) | 21,280 | -63.8% | 7,791 (2026-08-19) | -21.3% (2026-02-06) | 7 | 304 / 21 / 0 / 2 | 5,337 | -181 | 20,930 | no |
| S3: 3x book, fee 0.02% (maker-like bound) | 27,933 | -57.7% | 9,000 (2026-01-21) | -21.2% (2026-02-06) | 7 | 305 / 20 / 0 / 1 | 2,450 | -201 | 27,478 | no |

Monthly statistic (descriptive for all but the S2 0.05% cell):

| Cell | Complete months | Mean month (90% bootstrap interval) | Median month | Months up | Worst / best month | 12-month paths ending above start | 12-month paths below half at a month-end | Median 12-month path end |
|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check) | 80 | -0.97% (-2.96% to +1.14%) | -2.49% | 44% | -22.4% / +29.1% | 31.3% | 12.0% | 0.83x |
| S1: 2% rule, fee 0.05% (taker, PRIMARY) | 80 | +0.20% (-1.78% to +2.31%) | -1.28% | 46% | -20.4% / +31.3% | 45.1% | 5.9% | 0.95x |
| S1: 2% rule, fee 0.02% (maker-like bound) | 80 | +0.91% (-1.08% to +3.02%) | -0.56% | 48% | -19.2% / +32.8% | 54.0% | 3.6% | 1.04x |
| S2: 100% per coin, fee 0.10% (H63's, check) | 80 | -0.71% (-4.85% to +3.70%) | -4.20% | 42% | -42.0% / +67.3% | 30.7% | 48.2% | 0.66x |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY) | 80 | +1.64% (-2.57% to +6.10%) | -1.92% | 49% | -39.5% / +71.0% | 43.6% | 33.9% | 0.89x |
| S2: 100% per coin, fee 0.02% (maker-like bound) | 80 | +3.08% (-1.15% to +7.57%) | -0.52% | 49% | -38.0% / +73.2% | 53.0% | 26.0% | 1.06x |
| S3: 3x book, fee 0.10% (H63's, check) | 80 | -1.20% (-6.98% to +4.93%) | -9.77% | 40% | -50.4% / +95.9% | 25.1% | 67.8% | 0.47x |
| S3: 3x book, fee 0.05% (taker, PRIMARY) | 80 | +2.01% (-3.86% to +8.28%) | -7.38% | 46% | -46.7% / +102.6% | 37.3% | 54.8% | 0.70x |
| S3: 3x book, fee 0.02% (maker-like bound) | 80 | +4.01% (-1.92% to +10.33%) | -5.66% | 46% | -44.4% / +106.7% | 45.8% | 46.3% | 0.89x |

## 30-day trend filter (b_trend30, H67; found on this history): all sizings and fees (found on this same history: cannot show an advantage)

Whole replay:

| Cell | Final | Worst fall | Lowest equity | Worst UTC day | Longest losing run | Joined / trimmed / capped / not joined | Fees | Funding paid | Final without funding | Wiped out |
|---|---|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check) | 21,496 | -59.9% | 9,149 (2020-03-05) | -7.4% (2021-09-07) | 14 | 1702 / 251 / 814 / 114 | 40,072 | 7,527 | 30,010 | no |
| S1: 2% rule, fee 0.05% (taker, PRIMARY) | 50,818 | -49.3% | 9,328 (2020-03-05) | -7.3% (2021-09-07) | 14 | 1703 / 246 / 821 / 113 | 31,543 | 9,810 | 71,917 | no |
| S1: 2% rule, fee 0.02% (maker-like bound) | 86,751 | -42.6% | 9,457 (2020-03-05) | -7.2% (2021-09-07) | 14 | 1705 / 240 / 830 / 111 | 17,233 | 11,824 | 122,874 | no |
| S2: 100% per coin, fee 0.10% (H63's, check) | 43,975 | -82.5% | 8,554 (2020-03-05) | -19.6% (2026-02-06) | 15 | 1779 / 149 / 0 / 37 | 154,384 | 36,410 | 99,424 | no |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY) | 245,417 | -74.8% | 8,910 (2020-03-05) | -19.4% (2026-02-06) | 15 | 1780 / 145 / 0 / 36 | 197,760 | 66,658 | 555,892 | no |
| S2: 100% per coin, fee 0.02% (maker-like bound) | 691,714 | -70.9% | 9,131 (2020-03-05) | -19.3% (2026-02-06) | 15 | 1785 / 142 / 0 / 31 | 150,915 | 102,373 | 1,569,335 | no |
| S3: 3x book, fee 0.10% (H63's, check) | 77,803 | -90.1% | 8,823 (2020-03-05) | -21.7% (2026-02-06) | 14 | 1716 / 385 / 0 / 100 | 480,611 | 95,236 | 211,279 | no |
| S3: 3x book, fee 0.05% (taker, PRIMARY) | 863,122 | -83.2% | 9,340 (2020-03-05) | -21.3% (2026-02-06) | 14 | 1721 / 380 / 0 / 95 | 883,090 | 245,326 | 2,339,794 | no |
| S3: 3x book, fee 0.02% (maker-like bound) | 3,624,458 | -79.0% | 9,664 (2020-03-05) | -21.2% (2026-02-06) | 14 | 1728 / 378 / 0 / 88 | 884,410 | 473,630 | 9,874,996 | no |

Month-starts:

| Cell | Starts | +100% first | -50% or wipe-out first (of which wiped) | Neither (median end) | Unfinished | Median days to either | to +100% | to -50% |
|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check) | 81 | 5 | 0 (0) | 64 (10,219) | 12 | 305 | 305 | n/a |
| S1: 2% rule, fee 0.05% (taker, PRIMARY) | 81 | 8 | 0 (0) | 61 (11,610) | 12 | 279 | 279 | n/a |
| S1: 2% rule, fee 0.02% (maker-like bound) | 81 | 14 | 0 (0) | 55 (12,395) | 12 | 272 | 272 | n/a |
| S2: 100% per coin, fee 0.10% (H63's, check) | 81 | 26 | 10 (0) | 33 (9,178) | 12 | 161 | 152 | 223 |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY) | 81 | 37 | 6 (0) | 30 (11,134) | 8 | 184 | 164 | 246 |
| S2: 100% per coin, fee 0.02% (maker-like bound) | 81 | 49 | 3 (0) | 23 (11,992) | 6 | 190 | 192 | 189 |
| S3: 3x book, fee 0.10% (H63's, check) | 81 | 36 | 20 (0) | 17 (7,933) | 8 | 113 | 103 | 128 |
| S3: 3x book, fee 0.05% (taker, PRIMARY) | 81 | 50 | 15 (0) | 12 (10,283) | 4 | 112 | 112 | 135 |
| S3: 3x book, fee 0.02% (maker-like bound) | 81 | 59 | 12 (0) | 8 (10,388) | 2 | 112 | 110 | 140 |

Month-starts before / from 2023-06-08:

| Cell | Starts | +100% first | -50% or wipe-out first (of which wiped) | Neither (median end) | Unfinished | Median days to either | to +100% | to -50% |
|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check), first half | 40 | 5 | 0 (0) | 35 (12,664) | 0 | 305 | 305 | n/a |
| S1: 2% rule, fee 0.05% (taker, PRIMARY), first half | 40 | 8 | 0 (0) | 32 (13,775) | 0 | 279 | 279 | n/a |
| S1: 2% rule, fee 0.02% (maker-like bound), first half | 40 | 14 | 0 (0) | 26 (14,416) | 0 | 272 | 272 | n/a |
| S2: 100% per coin, fee 0.10% (H63's, check), first half | 40 | 25 | 0 (0) | 15 (9,275) | 0 | 149 | 149 | n/a |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY), first half | 40 | 28 | 0 (0) | 12 (11,031) | 0 | 140 | 140 | n/a |
| S2: 100% per coin, fee 0.02% (maker-like bound), first half | 40 | 32 | 0 (0) | 8 (12,343) | 0 | 152 | 152 | n/a |
| S3: 3x book, fee 0.10% (H63's, check), first half | 40 | 23 | 8 (0) | 9 (7,559) | 0 | 84 | 71 | 108 |
| S3: 3x book, fee 0.05% (taker, PRIMARY), first half | 40 | 26 | 6 (0) | 8 (9,418) | 0 | 86 | 82 | 137 |
| S3: 3x book, fee 0.02% (maker-like bound), first half | 40 | 29 | 5 (0) | 6 (10,388) | 0 | 92 | 81 | 108 |
| S1: 2% rule, fee 0.10% (H63's, check), second half | 41 | 0 | 0 (0) | 29 (8,726) | 12 | n/a | n/a | n/a |
| S1: 2% rule, fee 0.05% (taker, PRIMARY), second half | 41 | 0 | 0 (0) | 29 (9,987) | 12 | n/a | n/a | n/a |
| S1: 2% rule, fee 0.02% (maker-like bound), second half | 41 | 0 | 0 (0) | 29 (10,855) | 12 | n/a | n/a | n/a |
| S2: 100% per coin, fee 0.10% (H63's, check), second half | 41 | 1 | 10 (0) | 18 (9,082) | 12 | 219 | 157 | 223 |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY), second half | 41 | 9 | 6 (0) | 18 (12,093) | 8 | 218 | 217 | 246 |
| S2: 100% per coin, fee 0.02% (maker-like bound), second half | 41 | 17 | 3 (0) | 15 (11,490) | 6 | 246 | 250 | 189 |
| S3: 3x book, fee 0.10% (H63's, check), second half | 41 | 13 | 12 (0) | 8 (7,936) | 8 | 142 | 143 | 134 |
| S3: 3x book, fee 0.05% (taker, PRIMARY), second half | 41 | 24 | 9 (0) | 4 (11,517) | 4 | 163 | 173 | 135 |
| S3: 3x book, fee 0.02% (maker-like bound), second half | 41 | 30 | 7 (0) | 2 (9,823) | 2 | 156 | 144 | 157 |

first half (to 2023-06-07), fresh 10,000:

| Cell | Final | Worst fall | Lowest equity | Worst UTC day | Longest losing run | Joined / trimmed / capped / not joined | Fees | Funding paid | Final without funding | Wiped out |
|---|---|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check) | 30,246 | -40.2% | 9,149 (2020-03-05) | -7.4% (2021-09-07) | 14 | 818 / 155 / 258 / 45 | 16,292 | 4,927 | 38,807 | no |
| S1: 2% rule, fee 0.05% (taker, PRIMARY) | 43,030 | -38.0% | 9,328 (2020-03-05) | -7.3% (2021-09-07) | 14 | 817 / 155 / 260 / 46 | 10,137 | 5,656 | 55,959 | no |
| S1: 2% rule, fee 0.02% (maker-like bound) | 54,040 | -36.6% | 9,457 (2020-03-05) | -7.2% (2021-09-07) | 14 | 818 / 154 / 265 / 45 | 4,692 | 6,204 | 70,342 | no |
| S2: 100% per coin, fee 0.10% (H63's, check) | 71,452 | -63.0% | 8,554 (2020-03-05) | -16.9% (2021-07-21) | 15 | 832 / 115 / 0 / 31 | 69,876 | 24,201 | 136,428 | no |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY) | 155,562 | -58.5% | 8,910 (2020-03-05) | -16.8% (2021-01-21) | 15 | 832 / 111 / 0 / 31 | 59,288 | 33,814 | 297,377 | no |
| S2: 100% per coin, fee 0.02% (maker-like bound) | 248,756 | -57.4% | 9,131 (2020-03-05) | -16.7% (2021-01-21) | 15 | 837 / 110 / 0 / 26 | 33,204 | 42,141 | 476,235 | no |
| S3: 3x book, fee 0.10% (H63's, check) | 160,826 | -75.3% | 8,823 (2020-03-05) | -18.7% (2023-04-19) | 14 | 792 / 284 / 0 / 71 | 225,961 | 55,709 | 353,054 | no |
| S3: 3x book, fee 0.05% (taker, PRIMARY) | 466,120 | -72.7% | 9,340 (2020-03-05) | -18.2% (2023-04-19) | 14 | 796 / 280 / 0 / 67 | 244,285 | 96,072 | 1,025,062 | no |
| S3: 3x book, fee 0.02% (maker-like bound) | 884,181 | -71.0% | 9,664 (2020-03-05) | -17.8% (2023-04-19) | 14 | 800 / 278 / 0 / 63 | 158,935 | 138,531 | 1,943,665 | no |

second half (2023-06-08 on), fresh 10,000:

| Cell | Final | Worst fall | Lowest equity | Worst UTC day | Longest losing run | Joined / trimmed / capped / not joined | Fees | Funding paid | Final without funding | Wiped out |
|---|---|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check) | 7,125 | -59.9% | 5,424 (2026-10-13) | -6.6% (2024-03-05) | 10 | 883 / 96 / 556 / 70 | 7,883 | 862 | 7,753 | no |
| S1: 2% rule, fee 0.05% (taker, PRIMARY) | 11,840 | -49.3% | 7,520 (2025-08-06) | -6.5% (2024-03-05) | 10 | 884 / 91 / 561 / 69 | 4,988 | 968 | 12,885 | no |
| S1: 2% rule, fee 0.02% (maker-like bound) | 16,095 | -42.6% | 9,004 (2025-08-06) | -6.5% (2024-03-05) | 10 | 884 / 86 / 565 / 69 | 2,327 | 1,043 | 17,514 | no |
| S2: 100% per coin, fee 0.10% (H63's, check) | 6,525 | -82.5% | 3,423 (2025-07-08) | -19.6% (2026-02-06) | 9 | 947 / 34 / 0 / 6 | 12,495 | 1,833 | 7,742 | no |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY) | 16,689 | -74.8% | 5,880 (2025-07-08) | -19.4% (2026-02-06) | 9 | 948 / 34 / 0 / 5 | 9,394 | 2,255 | 19,815 | no |
| S2: 100% per coin, fee 0.02% (maker-like bound) | 29,377 | -70.9% | 7,546 (2024-11-06) | -19.3% (2026-02-06) | 9 | 948 / 32 / 0 / 5 | 4,990 | 2,579 | 34,884 | no |
| S3: 3x book, fee 0.10% (H63's, check) | 5,287 | -90.1% | 2,411 (2026-01-28) | -21.7% (2026-02-06) | 9 | 924 / 101 / 0 / 29 | 17,236 | 2,720 | 6,561 | no |
| S3: 3x book, fee 0.05% (taker, PRIMARY) | 20,168 | -83.2% | 5,232 (2025-01-15) | -21.3% (2026-02-06) | 9 | 925 / 100 / 0 / 28 | 14,892 | 3,521 | 24,939 | no |
| S3: 3x book, fee 0.02% (maker-like bound) | 44,553 | -79.0% | 7,560 (2025-01-07) | -21.2% (2026-02-06) | 9 | 927 / 100 / 0 / 26 | 8,904 | 4,152 | 55,392 | no |

holdout (2025-11-11 on), fresh 10,000:

| Cell | Final | Worst fall | Lowest equity | Worst UTC day | Longest losing run | Joined / trimmed / capped / not joined | Fees | Funding paid | Final without funding | Wiped out |
|---|---|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check) | 11,612 | -30.6% | 8,841 (2026-10-13) | -5.9% (2026-02-06) | 8 | 266 / 23 / 172 / 19 | 3,306 | -28 | 11,578 | no |
| S1: 2% rule, fee 0.05% (taker, PRIMARY) | 13,564 | -24.1% | 9,760 (2026-01-28) | -5.8% (2026-02-06) | 8 | 267 / 21 / 174 / 18 | 1,783 | -26 | 13,528 | no |
| S1: 2% rule, fee 0.02% (maker-like bound) | 14,895 | -21.3% | 9,951 (2025-11-11) | -5.7% (2026-02-06) | 8 | 266 / 20 / 174 / 19 | 747 | -25 | 14,865 | no |
| S2: 100% per coin, fee 0.10% (H63's, check) | 15,100 | -46.2% | 7,945 (2026-01-28) | -19.6% (2026-02-06) | 8 | 284 / 5 / 0 / 1 | 5,956 | -45 | 15,054 | no |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY) | 19,966 | -42.7% | 8,481 (2026-01-28) | -19.4% (2026-02-06) | 8 | 285 / 5 / 0 / 0 | 3,418 | -30 | 19,906 | no |
| S2: 100% per coin, fee 0.02% (maker-like bound) | 23,630 | -40.6% | 8,819 (2026-01-28) | -19.3% (2026-02-06) | 8 | 285 / 4 / 0 / 0 | 1,490 | -19 | 23,563 | no |
| S3: 3x book, fee 0.10% (H63's, check) | 15,076 | -60.3% | 6,875 (2026-01-28) | -21.7% (2026-02-06) | 8 | 280 / 18 / 0 / 5 | 8,489 | -120 | 14,953 | no |
| S3: 3x book, fee 0.05% (taker, PRIMARY) | 22,701 | -56.7% | 7,565 (2026-01-28) | -21.3% (2026-02-06) | 8 | 280 / 17 / 0 / 5 | 5,205 | -107 | 22,484 | no |
| S3: 3x book, fee 0.02% (maker-like bound) | 28,785 | -54.3% | 8,011 (2026-01-28) | -21.2% (2026-02-06) | 8 | 282 / 17 / 0 / 3 | 2,355 | -97 | 28,508 | no |

Monthly statistic (descriptive for all but the S2 0.05% cell):

| Cell | Complete months | Mean month (90% bootstrap interval) | Median month | Months up | Worst / best month | 12-month paths ending above start | 12-month paths below half at a month-end | Median 12-month path end |
|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check) | 80 | +1.30% (-0.59% to +3.27%) | +0.03% | 50% | -17.5% / +34.9% | 60.6% | 1.2% | 1.10x |
| S1: 2% rule, fee 0.05% (taker, PRIMARY) | 80 | +2.36% (+0.46% to +4.35%) | +1.30% | 54% | -16.3% / +36.1% | 73.8% | 0.4% | 1.25x |
| S1: 2% rule, fee 0.02% (maker-like bound) | 80 | +3.02% (+1.11% to +5.01%) | +1.83% | 54% | -15.9% / +36.8% | 80.7% | 0.1% | 1.35x |
| S2: 100% per coin, fee 0.10% (H63's, check) | 80 | +3.70% (-0.35% to +7.85%) | -1.89% | 46% | -31.6% / +73.9% | 59.3% | 18.2% | 1.19x |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY) | 80 | +5.84% (+1.76% to +10.08%) | +0.27% | 51% | -29.0% / +77.2% | 72.6% | 10.0% | 1.53x |
| S2: 100% per coin, fee 0.02% (maker-like bound) | 80 | +7.16% (+3.04% to +11.45%) | +1.99% | 55% | -27.4% / +79.2% | 79.5% | 6.7% | 1.77x |
| S3: 3x book, fee 0.10% (H63's, check) | 80 | +6.26% (+0.52% to +12.31%) | -3.16% | 48% | -43.9% / +94.8% | 59.5% | 31.4% | 1.26x |
| S3: 3x book, fee 0.05% (taker, PRIMARY) | 80 | +9.33% (+3.47% to +15.51%) | -0.23% | 49% | -40.6% / +100.0% | 72.4% | 20.3% | 1.79x |
| S3: 3x book, fee 0.02% (maker-like bound) | 80 | +11.21% (+5.28% to +17.49%) | +1.33% | 55% | -38.6% / +103.2% | 79.1% | 15.3% | 2.20x |

## wait after a stop-out (b_wait_stop, H68; found on this history): all sizings and fees (found on this same history: cannot show an advantage)

Whole replay:

| Cell | Final | Worst fall | Lowest equity | Worst UTC day | Longest losing run | Joined / trimmed / capped / not joined | Fees | Funding paid | Final without funding | Wiped out |
|---|---|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check) | 8,282 | -70.4% | 7,077 (2026-10-22) | -7.3% (2021-02-15) | 13 | 1677 / 172 / 824 / 86 | 20,732 | 2,449 | 10,041 | no |
| S1: 2% rule, fee 0.05% (taker, PRIMARY) | 19,592 | -51.9% | 8,427 (2020-03-08) | -7.3% (2021-02-15) | 12 | 1675 / 163 / 831 / 88 | 15,819 | 3,029 | 23,744 | no |
| S1: 2% rule, fee 0.02% (maker-like bound) | 32,918 | -44.4% | 8,489 (2020-03-08) | -7.2% (2021-02-15) | 12 | 1679 / 160 / 832 / 84 | 8,372 | 3,485 | 39,962 | no |
| S2: 100% per coin, fee 0.10% (H63's, check) | 11,933 | -92.1% | 5,685 (2020-12-14) | -19.7% (2026-02-06) | 13 | 1742 / 110 / 0 / 21 | 60,167 | 7,799 | 19,636 | no |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY) | 65,262 | -80.2% | 6,508 (2020-04-17) | -19.4% (2026-02-06) | 13 | 1748 / 107 / 0 / 15 | 71,139 | 13,203 | 106,557 | no |
| S2: 100% per coin, fee 0.02% (maker-like bound) | 179,833 | -70.6% | 6,693 (2020-04-17) | -19.3% (2026-02-06) | 13 | 1749 / 105 / 0 / 14 | 51,381 | 19,134 | 292,924 | no |
| S3: 3x book, fee 0.10% (H63's, check) | 2,763 | -98.5% | 1,215 (2026-01-28) | -21.7% (2026-02-06) | 13 | 1715 / 298 / 0 / 48 | 56,257 | 8,295 | 5,121 | no |
| S3: 3x book, fee 0.05% (taker, PRIMARY) | 30,078 | -94.3% | 5,887 (2020-04-17) | -21.4% (2026-02-06) | 13 | 1717 / 296 / 0 / 46 | 75,659 | 15,386 | 55,363 | no |
| S3: 3x book, fee 0.02% (maker-like bound) | 126,685 | -88.6% | 6,105 (2020-04-17) | -21.3% (2026-02-06) | 13 | 1719 / 294 / 0 / 44 | 62,926 | 24,509 | 232,513 | no |

Month-starts:

| Cell | Starts | +100% first | -50% or wipe-out first (of which wiped) | Neither (median end) | Unfinished | Median days to either | to +100% | to -50% |
|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check) | 81 | 2 | 0 (0) | 67 (8,770) | 12 | 303 | 303 | n/a |
| S1: 2% rule, fee 0.05% (taker, PRIMARY) | 81 | 8 | 0 (0) | 61 (9,747) | 12 | 304 | 304 | n/a |
| S1: 2% rule, fee 0.02% (maker-like bound) | 81 | 11 | 0 (0) | 58 (10,448) | 12 | 297 | 297 | n/a |
| S2: 100% per coin, fee 0.10% (H63's, check) | 81 | 29 | 17 (0) | 24 (8,342) | 11 | 201 | 163 | 233 |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY) | 81 | 30 | 5 (0) | 36 (9,498) | 10 | 174 | 157 | 243 |
| S2: 100% per coin, fee 0.02% (maker-like bound) | 81 | 30 | 0 (0) | 41 (10,790) | 10 | 145 | 145 | n/a |
| S3: 3x book, fee 0.10% (H63's, check) | 81 | 27 | 35 (0) | 9 (7,793) | 10 | 134 | 113 | 141 |
| S3: 3x book, fee 0.05% (taker, PRIMARY) | 81 | 32 | 24 (0) | 16 (10,598) | 9 | 131 | 118 | 155 |
| S3: 3x book, fee 0.02% (maker-like bound) | 81 | 40 | 18 (0) | 16 (11,475) | 7 | 129 | 125 | 154 |

Month-starts before / from 2023-06-08:

| Cell | Starts | +100% first | -50% or wipe-out first (of which wiped) | Neither (median end) | Unfinished | Median days to either | to +100% | to -50% |
|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check), first half | 40 | 2 | 0 (0) | 38 (9,292) | 0 | 303 | 303 | n/a |
| S1: 2% rule, fee 0.05% (taker, PRIMARY), first half | 40 | 8 | 0 (0) | 32 (10,005) | 0 | 304 | 304 | n/a |
| S1: 2% rule, fee 0.02% (maker-like bound), first half | 40 | 11 | 0 (0) | 29 (9,974) | 0 | 297 | 297 | n/a |
| S2: 100% per coin, fee 0.10% (H63's, check), first half | 40 | 27 | 10 (0) | 3 (7,504) | 0 | 208 | 163 | 262 |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY), first half | 40 | 27 | 5 (0) | 8 (7,422) | 0 | 169 | 151 | 243 |
| S2: 100% per coin, fee 0.02% (maker-like bound), first half | 40 | 27 | 0 (0) | 13 (7,402) | 0 | 133 | 133 | n/a |
| S3: 3x book, fee 0.10% (H63's, check), first half | 40 | 25 | 13 (0) | 2 (8,717) | 0 | 132 | 116 | 141 |
| S3: 3x book, fee 0.05% (taker, PRIMARY), first half | 40 | 27 | 11 (0) | 2 (7,442) | 0 | 131 | 123 | 180 |
| S3: 3x book, fee 0.02% (maker-like bound), first half | 40 | 27 | 9 (0) | 4 (9,425) | 0 | 129 | 123 | 161 |
| S1: 2% rule, fee 0.10% (H63's, check), second half | 41 | 0 | 0 (0) | 29 (8,523) | 12 | n/a | n/a | n/a |
| S1: 2% rule, fee 0.05% (taker, PRIMARY), second half | 41 | 0 | 0 (0) | 29 (9,729) | 12 | n/a | n/a | n/a |
| S1: 2% rule, fee 0.02% (maker-like bound), second half | 41 | 0 | 0 (0) | 29 (10,453) | 12 | n/a | n/a | n/a |
| S2: 100% per coin, fee 0.10% (H63's, check), second half | 41 | 2 | 7 (0) | 21 (8,366) | 11 | 200 | 186 | 200 |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY), second half | 41 | 3 | 0 (0) | 28 (10,505) | 10 | 293 | 293 | n/a |
| S2: 100% per coin, fee 0.02% (maker-like bound), second half | 41 | 3 | 0 (0) | 28 (12,071) | 10 | 156 | 156 | n/a |
| S3: 3x book, fee 0.10% (H63's, check), second half | 41 | 2 | 22 (0) | 7 (7,793) | 10 | 137 | 40 | 149 |
| S3: 3x book, fee 0.05% (taker, PRIMARY), second half | 41 | 5 | 13 (0) | 14 (10,873) | 9 | 140 | 66 | 152 |
| S3: 3x book, fee 0.02% (maker-like bound), second half | 41 | 13 | 9 (0) | 12 (12,491) | 7 | 142 | 177 | 102 |

first half (to 2023-06-07), fresh 10,000:

| Cell | Final | Worst fall | Lowest equity | Worst UTC day | Longest losing run | Joined / trimmed / capped / not joined | Fees | Funding paid | Final without funding | Wiped out |
|---|---|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check) | 13,072 | -45.3% | 8,325 (2020-03-08) | -7.3% (2021-02-15) | 11 | 872 / 126 / 300 / 36 | 11,569 | 2,034 | 15,357 | no |
| S1: 2% rule, fee 0.05% (taker, PRIMARY) | 19,460 | -38.6% | 8,427 (2020-03-08) | -7.3% (2021-02-15) | 11 | 871 / 120 / 301 / 37 | 7,291 | 2,350 | 22,871 | no |
| S1: 2% rule, fee 0.02% (maker-like bound) | 24,738 | -35.0% | 8,489 (2020-03-08) | -7.2% (2021-02-15) | 11 | 876 / 119 / 302 / 32 | 3,371 | 2,571 | 29,114 | no |
| S2: 100% per coin, fee 0.10% (H63's, check) | 24,945 | -69.2% | 5,685 (2020-12-14) | -16.4% (2021-02-15) | 10 | 889 / 99 / 0 / 19 | 38,498 | 6,546 | 38,418 | no |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY) | 58,860 | -63.8% | 6,508 (2020-04-17) | -16.1% (2021-02-15) | 10 | 894 / 96 / 0 / 14 | 33,883 | 9,579 | 90,017 | no |
| S2: 100% per coin, fee 0.02% (maker-like bound) | 98,060 | -60.3% | 6,693 (2020-04-17) | -15.9% (2021-02-15) | 10 | 895 / 94 / 0 / 13 | 19,309 | 12,296 | 149,614 | no |
| S3: 3x book, fee 0.10% (H63's, check) | 13,159 | -85.4% | 5,497 (2020-11-09) | -19.6% (2021-02-15) | 10 | 865 / 238 / 0 / 43 | 44,895 | 7,521 | 22,178 | no |
| S3: 3x book, fee 0.05% (taker, PRIMARY) | 41,169 | -81.9% | 5,887 (2020-04-17) | -19.4% (2021-02-15) | 10 | 867 / 238 / 0 / 41 | 46,609 | 12,140 | 68,883 | no |
| S3: 3x book, fee 0.02% (maker-like bound) | 81,558 | -79.4% | 6,105 (2020-04-17) | -19.3% (2021-02-15) | 10 | 869 / 236 / 0 / 39 | 29,751 | 16,810 | 136,220 | no |

second half (2023-06-08 on), fresh 10,000:

| Cell | Final | Worst fall | Lowest equity | Worst UTC day | Longest losing run | Joined / trimmed / capped / not joined | Fees | Funding paid | Final without funding | Wiped out |
|---|---|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check) | 6,250 | -51.6% | 5,340 (2026-10-22) | -6.3% (2025-04-09) | 12 | 804 / 46 / 521 / 51 | 6,948 | 325 | 6,457 | no |
| S1: 2% rule, fee 0.05% (taker, PRIMARY) | 9,949 | -35.2% | 7,745 (2026-01-23) | -6.3% (2025-04-09) | 12 | 802 / 43 / 527 / 53 | 4,347 | 357 | 10,271 | no |
| S1: 2% rule, fee 0.02% (maker-like bound) | 13,163 | -31.8% | 8,357 (2024-02-07) | -6.3% (2025-04-09) | 12 | 804 / 41 / 527 / 51 | 2,006 | 377 | 13,594 | no |
| S2: 100% per coin, fee 0.10% (H63's, check) | 4,980 | -78.8% | 2,424 (2026-01-28) | -19.7% (2026-02-06) | 13 | 853 / 11 / 0 / 2 | 8,999 | 544 | 5,333 | no |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY) | 11,516 | -64.4% | 4,795 (2026-01-28) | -19.4% (2026-02-06) | 13 | 854 / 11 / 0 / 1 | 6,552 | 660 | 12,322 | no |
| S2: 100% per coin, fee 0.02% (maker-like bound) | 19,022 | -55.9% | 6,208 (2024-02-07) | -19.3% (2026-02-06) | 13 | 854 / 11 / 0 / 1 | 3,384 | 744 | 20,351 | no |
| S3: 3x book, fee 0.10% (H63's, check) | 2,236 | -91.9% | 983 (2026-01-28) | -21.7% (2026-02-06) | 13 | 850 / 60 / 0 / 5 | 9,123 | 659 | 2,467 | no |
| S3: 3x book, fee 0.05% (taker, PRIMARY) | 7,750 | -80.1% | 2,673 (2026-01-28) | -21.4% (2026-02-06) | 13 | 850 / 58 / 0 / 5 | 7,450 | 869 | 8,555 | no |
| S3: 3x book, fee 0.02% (maker-like bound) | 16,441 | -69.9% | 4,421 (2024-02-07) | -21.3% (2026-02-06) | 13 | 850 / 58 / 0 / 5 | 4,291 | 1,031 | 18,128 | no |

holdout (2025-11-11 on), fresh 10,000:

| Cell | Final | Worst fall | Lowest equity | Worst UTC day | Longest losing run | Joined / trimmed / capped / not joined | Fees | Funding paid | Final without funding | Wiped out |
|---|---|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check) | 9,385 | -33.6% | 8,019 (2026-10-22) | -5.9% (2026-02-06) | 10 | 198 / 13 / 118 / 12 | 2,199 | -54 | 9,328 | no |
| S1: 2% rule, fee 0.05% (taker, PRIMARY) | 10,579 | -31.9% | 8,236 (2026-01-23) | -5.8% (2026-02-06) | 10 | 199 / 13 / 118 / 11 | 1,165 | -57 | 10,514 | no |
| S1: 2% rule, fee 0.02% (maker-like bound) | 11,376 | -31.0% | 8,356 (2026-01-23) | -5.7% (2026-02-06) | 10 | 198 / 11 / 118 / 12 | 483 | -59 | 11,310 | no |
| S2: 100% per coin, fee 0.10% (H63's, check) | 13,982 | -52.3% | 6,805 (2026-01-28) | -19.7% (2026-02-06) | 11 | 209 / 3 / 0 / 1 | 4,229 | -71 | 13,877 | no |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY) | 17,086 | -50.4% | 7,114 (2026-01-28) | -19.4% (2026-02-06) | 11 | 210 / 3 / 0 / 0 | 2,348 | -75 | 16,948 | no |
| S2: 100% per coin, fee 0.02% (maker-like bound) | 19,261 | -49.1% | 7,306 (2026-01-28) | -19.3% (2026-02-06) | 11 | 210 / 3 / 0 / 0 | 1,002 | -78 | 19,106 | no |
| S3: 3x book, fee 0.10% (H63's, check) | 12,004 | -68.3% | 5,277 (2026-01-28) | -21.7% (2026-02-06) | 11 | 209 / 16 / 0 / 1 | 5,756 | -113 | 11,847 | no |
| S3: 3x book, fee 0.05% (taker, PRIMARY) | 16,394 | -66.2% | 5,655 (2026-01-28) | -21.4% (2026-02-06) | 11 | 209 / 15 / 0 / 1 | 3,380 | -126 | 16,186 | no |
| S3: 3x book, fee 0.02% (maker-like bound) | 19,758 | -64.8% | 5,894 (2026-01-28) | -21.3% (2026-02-06) | 11 | 209 / 15 / 0 / 1 | 1,494 | -135 | 19,513 | no |

Monthly statistic (descriptive for all but the S2 0.05% cell):

| Cell | Complete months | Mean month (90% bootstrap interval) | Median month | Months up | Worst / best month | 12-month paths ending above start | 12-month paths below half at a month-end | Median 12-month path end |
|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, fee 0.10% (H63's, check) | 80 | +0.27% (-1.53% to +2.09%) | +0.31% | 52% | -24.1% / +28.6% | 47.3% | 3.0% | 0.98x |
| S1: 2% rule, fee 0.05% (taker, PRIMARY) | 80 | +1.32% (-0.49% to +3.16%) | +1.19% | 57% | -23.2% / +30.5% | 62.4% | 1.0% | 1.11x |
| S1: 2% rule, fee 0.02% (maker-like bound) | 80 | +1.96% (+0.14% to +3.81%) | +1.70% | 59% | -22.7% / +31.6% | 70.4% | 0.5% | 1.20x |
| S2: 100% per coin, fee 0.10% (H63's, check) | 80 | +2.12% (-1.47% to +5.82%) | +0.04% | 50% | -37.8% / +63.0% | 51.9% | 20.4% | 1.03x |
| S2: 100% per coin, fee 0.05% (taker, PRIMARY) | 80 | +4.25% (+0.59% to +8.01%) | +1.66% | 55% | -36.4% / +67.6% | 66.6% | 11.1% | 1.32x |
| S2: 100% per coin, fee 0.02% (maker-like bound) | 80 | +5.54% (+1.86% to +9.35%) | +2.91% | 55% | -35.5% / +70.4% | 74.5% | 7.3% | 1.53x |
| S3: 3x book, fee 0.10% (H63's, check) | 80 | +2.33% (-2.78% to +7.56%) | -0.27% | 50% | -52.7% / +85.1% | 43.1% | 42.7% | 0.85x |
| S3: 3x book, fee 0.05% (taker, PRIMARY) | 80 | +5.31% (+0.08% to +10.67%) | +2.07% | 54% | -51.0% / +92.7% | 58.2% | 29.8% | 1.21x |
| S3: 3x book, fee 0.02% (maker-like bound) | 80 | +7.14% (+1.83% to +12.60%) | +3.83% | 55% | -49.9% / +97.4% | 66.7% | 22.6% | 1.49x |

## Reproduction check: current rule at 0.10% against H63's published results

| Sizing | Read-out | H63 | H73 | Difference |
|---|---|---|---|---|
| S1: 2% rule | final | 3208.3 | 3251.4 | +43.1 |
| S1: 2% rule | worst fall % | -86.7 | -86.7 | -0.1 |
| S1: 2% rule | lowest | 2254.4 | 2284.7 | +30.3 |
| S1: 2% rule | fees | 14338.4 | 14559.1 | +220.7 |
| S1: 2% rule | funding | 3408.5 | 3462.2 | +53.7 |
| S1: 2% rule | joined | 1907 | 1903 | -4.0 |
| S1: 2% rule | trimmed | 345 | 345 | +0.0 |
| S1: 2% rule | not joined | 169 | 172 | +3.0 |
| S1: 2% rule | worst day % | -6.6 | -6.6 | -0.0 |
| S1: 2% rule | month-starts +100% first | 0 | 0 | +0.0 |
| S1: 2% rule | month-starts -50% first | 4 | 4 | +0.0 |
| S1: 2% rule | month-starts neither | 65 | 65 | +0.0 |
| S2: 100% per coin | final | 847.3 | 861.2 | +13.9 |
| S2: 100% per coin | worst fall % | -98.6 | -98.6 | -0.0 |
| S2: 100% per coin | lowest | 426.3 | 433.3 | +7.0 |
| S2: 100% per coin | fees | 28220.2 | 28740.5 | +520.3 |
| S2: 100% per coin | funding | 9757.9 | 9944.7 | +186.8 |
| S2: 100% per coin | joined | 2040 | 2040 | +0.0 |
| S2: 100% per coin | trimmed | 174 | 174 | +0.0 |
| S2: 100% per coin | not joined | 36 | 35 | -1.0 |
| S2: 100% per coin | worst day % | -19.6 | -19.6 | -0.0 |
| S2: 100% per coin | month-starts +100% first | 16 | 16 | +0.0 |
| S2: 100% per coin | month-starts -50% first | 37 | 37 | +0.0 |
| S2: 100% per coin | month-starts neither | 16 | 16 | +0.0 |
| S3: 3x book | final | 100.2 | 104.0 | +3.8 |
| S3: 3x book | worst fall % | -99.9 | -99.9 | -0.0 |
| S3: 3x book | lowest | 40.1 | 41.6 | +1.5 |
| S3: 3x book | fees | 31294.5 | 32735.8 | +1441.3 |
| S3: 3x book | funding | 11139.9 | 11654.1 | +514.2 |
| S3: 3x book | joined | 1965 | 1963 | -2.0 |
| S3: 3x book | trimmed | 480 | 477 | -3.0 |
| S3: 3x book | not joined | 111 | 112 | +1.0 |
| S3: 3x book | worst day % | -21.7 | -21.7 | -0.0 |
| S3: 3x book | month-starts +100% first | 24 | 24 | +0.0 |
| S3: 3x book | month-starts -50% first | 54 | 54 | +0.0 |
| S3: 3x book | month-starts neither | 1 | 1 | +0.0 |

H63 trades: 2076; H73 current-rule trades: 2075.

