# H49: the exhaustion fade

PAPER RESEARCH ONLY. Registered 2026-11-16 06:25 UTC (`research/HYPOTHESES.md` H49) before any code or outcome. Development data only (rows before 2025-11-11 00:00 UTC; the holdout was not read). Events with entry from 2020-01-01; first half before 2023-06-07. Written 2026-11-16 06:28 UTC.

Event = the first qualifying 15m bar per UTC day per direction: a close beyond today's running high/low (or a fresh close beyond the prior day's high/low) on a day that has already used >= U x its daily ATR (14, last closed day), on a bar whose true range < K x ATR15 (the weak push). Fade hit = -0.5 daily ATR in the fade's favour before +0.5 daily ATR against, from the next open, within the UTC day (a bar touching both = miss; neither = unresolved, excluded). Chance ~50%. p = exact two-sided binomial against 50%. Tests: 8 variants x 6 scopes = **48** per half; Bonferroni p < 1.04e-03.

## Verdict: NO PASS

Best by the lower of the two halves' pooled hit rate (reported, not passed) variant: **X1** (close beyond today's running high/low, day used >= 100% of daily ATR, push bar TR < 1.0 x ATR15; fade: stop day extreme + 0.25 ATR15, target 0.5 daily ATR, out at the day's end).

Bar for X1: hit >= 55% both halves **NO** (55.2% / 45.0%); >= 200 resolved both halves **YES** (337 / 269); p < 1.04e-03 both halves **NO** (0.064 / 0.113); second-half trade pooled net > 0 and PF >= 1.1 **NO** (net -4,249, PF 0.697); >= 5 of 8 markets net > 0 with PF >= 1.1 **NO** (0: none).

Cells (variant x scope) whose p passes Bonferroni in BOTH halves (either side of 50%): 0 of 48.

## The variants

| id | rule |
|---|---|
| X1 | close beyond today's running high/low, day used >= 100% of daily ATR, push bar TR < 1.0 x ATR15; fade: stop day extreme + 0.25 ATR15, target 0.5 daily ATR, out at the day's end |
| X2 | close beyond today's running high/low, day used >= 130% of daily ATR, push bar TR < 1.0 x ATR15; fade: stop day extreme + 0.25 ATR15, target 0.5 daily ATR, out at the day's end |
| X3 | close beyond today's running high/low, day used >= 100% of daily ATR, push bar TR < 0.7 x ATR15; fade: stop day extreme + 0.25 ATR15, target 0.5 daily ATR, out at the day's end |
| X4 | close beyond today's running high/low, day used >= 100% of daily ATR, push bar TR < 1.0 x ATR15, next bar closes back (below / above the push close); fade: stop day extreme + 0.25 ATR15, target 0.5 daily ATR, out at the day's end |
| X5 | fresh close beyond the prior UTC day's high/low, day used >= 100% of daily ATR, push bar TR < 1.0 x ATR15; fade: stop day extreme + 0.25 ATR15, target 0.5 daily ATR, out at the day's end |
| X6 | fresh close beyond the prior UTC day's high/low, day used >= 100% of daily ATR, push bar TR < 1.0 x ATR15, next bar closes back (inside the level); fade: stop day extreme + 0.25 ATR15, target 0.5 daily ATR, out at the day's end |
| X7 | close beyond today's running high/low, day used >= 100% of daily ATR, push bar TR < 1.0 x ATR15; fade: stop day extreme + 0.25 daily ATR, target the day's midpoint (floor 0.25 dATR), out at the day's end |
| X8 | close beyond today's running high/low, day used >= 130% of daily ATR, push bar TR < 1.0 x ATR15, next bar closes back (below / above the push close); fade: stop day extreme + 0.25 daily ATR, target the day's midpoint (floor 0.25 dATR), out at the day's end |

## Pooled fade hit rates (primary: within the day; secondary: 72 h)

| id | first: hit | resolved | p | second: hit | resolved | p | 72 h first | 72 h second | events / month 1st / 2nd | dropped (no same-day entry) |
|---|---|---|---|---|---|---|---|---|---|---|
| X1 | 55.2% | 337 (715 unres.) | 0.064 | 45.0% | 269 (620 unres.) | 0.113 | 51.6% (993) / 50.8% (839) | 25.6 / 30.5 | 17 |
| X2 | 59.0% | 183 (344 unres.) | 0.018 | 48.2% | 137 (311 unres.) | 0.733 | 54.6% (507) / 52.2% (429) | 12.8 / 15.4 | 18 |
| X3 | 56.6% | 83 (357 unres.) | 0.272 | 48.9% | 90 (345 unres.) | 0.916 | 48.8% (414) / 52.3% (407) | 10.7 / 14.9 | 7 |
| X4 | 56.9% | 209 (596 unres.) | 0.053 | 50.6% | 174 (511 unres.) | 0.940 | 50.3% (754) / 52.8% (640) | 19.6 / 23.5 | 20 |
| X5 | 47.0% | 181 (408 unres.) | 0.457 | 47.1% | 104 (270 unres.) | 0.624 | 51.5% (559) / 52.5% (345) | 14.3 / 12.8 | 13 |
| X6 | 46.1% | 65 (163 unres.) | 0.620 | 60.0% | 40 (118 unres.) | 0.268 | 54.0% (215) / 58.2% (141) | 5.5 / 5.4 | 10 |
| X7 | 55.2% | 337 (715 unres.) | 0.064 | 45.0% | 269 (620 unres.) | 0.113 | 51.6% (993) / 50.8% (839) | 25.6 / 30.5 | 17 |
| X8 | 61.0% | 105 (292 unres.) | 0.031 | 46.5% | 99 (251 unres.) | 0.547 | 51.8% (382) / 50.9% (334) | 9.6 / 12.0 | 10 |

## The registered trade, pooled (after each market's own fee a side)

| id | half | trades | won | R before | R after | PF | per trade (% stake) | net $ | trades / month | median stop (dATR) |
|---|---|---|---|---|---|---|---|---|---|---|
| X1 | first | 1051 | 21.1% | +0.232 | -0.309 | 0.93 | -0.0145% | -1,520 | 25.5 | 0.06 |
|  | second | 889 | 19.5% | +0.169 | -0.477 | 0.70 | -0.0478% | -4,249 | 30.5 |  |
| X2 | first | 526 | 25.7% | +0.376 | -0.117 | 1.17 | +0.0315% | +1,655 | 12.8 | 0.067 |
|  | second | 448 | 23.7% | +0.285 | -0.302 | 0.79 | -0.0336% | -1,507 | 15.4 |  |
| X3 | first | 439 | 22.3% | +0.163 | -0.442 | 0.85 | -0.0221% | -969 | 10.7 | 0.053 |
|  | second | 435 | 19.8% | +0.132 | -0.567 | 0.72 | -0.0354% | -1,540 | 14.9 |  |
| X4 | first | 805 | 35.5% | +0.061 | -0.188 | 1.00 | +0.0008% | +64 | 19.6 | 0.136 |
|  | second | 685 | 33.7% | +0.052 | -0.249 | 0.76 | -0.0472% | -3,232 | 23.5 |  |
| X5 | first | 582 | 41.1% | +0.046 | -0.106 | 0.92 | -0.0298% | -1,733 | 14.1 | 0.397 |
|  | second | 374 | 38.0% | -0.034 | -0.206 | 0.66 | -0.1021% | -3,819 | 12.8 |  |
| X6 | first | 225 | 40.9% | +0.034 | -0.054 | 0.89 | -0.0473% | -1,065 | 5.5 | 0.502 |
|  | second | 158 | 50.6% | +0.037 | -0.059 | 1.02 | +0.0044% | +69 | 5.4 |  |
| X7 | first | 1052 | 43.0% | +0.070 | -0.039 | 1.07 | +0.0217% | +2,279 | 25.6 | 0.272 |
|  | second | 888 | 38.2% | -0.029 | -0.157 | 0.71 | -0.0767% | -6,814 | 30.4 |  |
| X8 | first | 397 | 48.1% | +0.084 | +0.003 | 1.38 | +0.1137% | +4,512 | 9.6 | 0.362 |
|  | second | 349 | 39.8% | -0.014 | -0.110 | 0.69 | -0.0836% | -2,917 | 12.0 |  |

## Pass bar, every variant

| id | hit >= 55% both | >= 200 resolved both | p < alpha both | trade 2nd half pooled net > 0 & PF >= 1.1 | markets net > 0 & PF >= 1.1 (2nd half) | PASS |
|---|---|---|---|---|---|---|
| X1 | no | yes | no | no | 0 (-) | **no** |
| X2 | no | no | no | no | 1 (SPX) | **no** |
| X3 | no | no | no | no | 0 (-) | **no** |
| X4 | no | no | no | no | 1 (BRENT) | **no** |
| X5 | no | no | no | no | 0 (-) | **no** |
| X6 | no | no | no | no | 3 (BTCUSDT, XAUUSD, SPX) | **no** |
| X7 | no | yes | no | no | 0 (-) | **no** |
| X8 | no | no | no | no | 1 (BTCUSDT) | **no** |

## Fade hit rate within the day, per market group (tests) and per market (descriptive)

| id | scope | first: hit | resolved | p | second: hit | resolved | p |
|---|---|---|---|---|---|---|---|
| X1 | crypto | 55.2% | 67 (60 unres.) | 0.464 | 53.2% | 47 (68 unres.) | 0.771 |
|  | metals | 57.0% | 79 (224 unres.) | 0.260 | 36.4% | 77 (184 unres.) | 0.022 |
|  | fx | 49.0% | 49 (143 unres.) | 1.000 | 40.0% | 50 (99 unres.) | 0.203 |
|  | index | 57.7% | 52 (76 unres.) | 0.332 | 57.9% | 38 (52 unres.) | 0.418 |
|  | energy | 55.6% | 90 (212 unres.) | 0.343 | 45.6% | 57 (217 unres.) | 0.597 |
| | BTCUSDT | 50.0% | 30 (22 unres.) | 1.000 | 51.9% | 27 (42 unres.) | 1.000 |
| | ETHUSDT | 59.5% | 37 (38 unres.) | 0.324 | 55.0% | 20 (26 unres.) | 0.824 |
| | XAUUSD | 61.3% | 31 (118 unres.) | 0.281 | 36.8% | 38 (104 unres.) | 0.143 |
| | XAGUSD | 54.2% | 48 (106 unres.) | 0.665 | 35.9% | 39 (80 unres.) | 0.108 |
| | USDJPY | 49.0% | 49 (143 unres.) | 1.000 | 40.0% | 50 (99 unres.) | 0.203 |
| | SPX | 57.7% | 52 (76 unres.) | 0.332 | 57.9% | 38 (52 unres.) | 0.418 |
| | WTI | 53.6% | 56 (109 unres.) | 0.689 | 48.6% | 37 (123 unres.) | 1.000 |
| | BRENT | 58.8% | 34 (103 unres.) | 0.392 | 40.0% | 20 (94 unres.) | 0.503 |
| X2 | crypto | 59.5% | 37 (30 unres.) | 0.324 | 45.5% | 22 (38 unres.) | 0.832 |
|  | metals | 58.3% | 48 (121 unres.) | 0.312 | 40.8% | 49 (100 unres.) | 0.253 |
|  | fx | 50.0% | 30 (75 unres.) | 1.000 | 50.0% | 24 (62 unres.) | 1.000 |
|  | index | 63.0% | 27 (22 unres.) | 0.248 | 66.7% | 18 (18 unres.) | 0.238 |
|  | energy | 63.4% | 41 (96 unres.) | 0.117 | 50.0% | 24 (93 unres.) | 1.000 |
| | BTCUSDT | 50.0% | 20 (8 unres.) | 1.000 | 50.0% | 12 (22 unres.) | 1.000 |
| | ETHUSDT | 70.6% | 17 (22 unres.) | 0.143 | 40.0% | 10 (16 unres.) | 0.754 |
| | XAUUSD | 66.7% | 18 (63 unres.) | 0.238 | 42.3% | 26 (51 unres.) | 0.557 |
| | XAGUSD | 53.3% | 30 (58 unres.) | 0.856 | 39.1% | 23 (49 unres.) | 0.405 |
| | USDJPY | 50.0% | 30 (75 unres.) | 1.000 | 50.0% | 24 (62 unres.) | 1.000 |
| | SPX | 63.0% | 27 (22 unres.) | 0.248 | 66.7% | 18 (18 unres.) | 0.238 |
| | WTI | 57.7% | 26 (54 unres.) | 0.557 | 50.0% | 16 (61 unres.) | 1.000 |
| | BRENT | 73.3% | 15 (42 unres.) | 0.118 | 50.0% | 8 (32 unres.) | 1.000 |
| X3 | crypto | 58.3% | 12 (14 unres.) | 0.774 | 46.1% | 13 (16 unres.) | 1.000 |
|  | metals | 53.9% | 13 (119 unres.) | 1.000 | 29.6% | 27 (111 unres.) | 0.052 |
|  | fx | 50.0% | 18 (77 unres.) | 1.000 | 33.3% | 18 (62 unres.) | 0.238 |
|  | index | 62.5% | 16 (46 unres.) | 0.454 | 81.2% | 16 (28 unres.) | 0.021 |
|  | energy | 58.3% | 24 (101 unres.) | 0.541 | 68.8% | 16 (128 unres.) | 0.210 |
| | BTCUSDT | 50.0% | 6 (6 unres.) | 1.000 | 50.0% | 10 (12 unres.) | 1.000 |
| | ETHUSDT | 66.7% | 6 (8 unres.) | 0.688 | 33.3% | 3 (4 unres.) | 1.000 |
| | XAUUSD | 66.7% | 6 (63 unres.) | 0.688 | 22.2% | 9 (63 unres.) | 0.180 |
| | XAGUSD | 42.9% | 7 (56 unres.) | 1.000 | 33.3% | 18 (48 unres.) | 0.238 |
| | USDJPY | 50.0% | 18 (77 unres.) | 1.000 | 33.3% | 18 (62 unres.) | 0.238 |
| | SPX | 62.5% | 16 (46 unres.) | 0.454 | 81.2% | 16 (28 unres.) | 0.021 |
| | WTI | 60.0% | 15 (53 unres.) | 0.607 | 58.3% | 12 (74 unres.) | 0.774 |
| | BRENT | 55.6% | 9 (48 unres.) | 1.000 | 100.0% | 4 (54 unres.) | 0.125 |
| X4 | crypto | 55.6% | 45 (42 unres.) | 0.551 | 62.1% | 29 (50 unres.) | 0.265 |
|  | metals | 54.0% | 50 (192 unres.) | 0.672 | 40.0% | 50 (156 unres.) | 0.203 |
|  | fx | 45.5% | 33 (121 unres.) | 0.728 | 37.5% | 32 (89 unres.) | 0.215 |
|  | index | 69.0% | 42 (59 unres.) | 0.020 | 61.3% | 31 (44 unres.) | 0.281 |
|  | energy | 59.0% | 39 (182 unres.) | 0.337 | 59.4% | 32 (172 unres.) | 0.377 |
| | BTCUSDT | 50.0% | 22 (18 unres.) | 1.000 | 64.7% | 17 (30 unres.) | 0.332 |
| | ETHUSDT | 60.9% | 23 (24 unres.) | 0.405 | 58.3% | 12 (20 unres.) | 0.774 |
| | XAUUSD | 45.0% | 20 (98 unres.) | 0.824 | 34.8% | 23 (87 unres.) | 0.210 |
| | XAGUSD | 60.0% | 30 (94 unres.) | 0.362 | 44.4% | 27 (69 unres.) | 0.701 |
| | USDJPY | 45.5% | 33 (121 unres.) | 0.728 | 37.5% | 32 (89 unres.) | 0.215 |
| | SPX | 69.0% | 42 (59 unres.) | 0.020 | 61.3% | 31 (44 unres.) | 0.281 |
| | WTI | 55.6% | 27 (98 unres.) | 0.701 | 56.5% | 23 (99 unres.) | 0.678 |
| | BRENT | 66.7% | 12 (84 unres.) | 0.388 | 66.7% | 9 (73 unres.) | 0.508 |
| X5 | crypto | 42.6% | 61 (96 unres.) | 0.306 | 43.9% | 41 (71 unres.) | 0.533 |
|  | metals | 46.0% | 50 (138 unres.) | 0.672 | 51.7% | 29 (85 unres.) | 1.000 |
|  | fx | 42.1% | 19 (68 unres.) | 0.648 | 53.9% | 13 (50 unres.) | 1.000 |
|  | index | 62.5% | 16 (22 unres.) | 0.454 | 66.7% | 6 (13 unres.) | 0.688 |
|  | energy | 51.4% | 35 (84 unres.) | 1.000 | 33.3% | 15 (51 unres.) | 0.302 |
| | BTCUSDT | 48.4% | 31 (53 unres.) | 1.000 | 45.5% | 22 (33 unres.) | 0.832 |
| | ETHUSDT | 36.7% | 30 (43 unres.) | 0.200 | 42.1% | 19 (38 unres.) | 0.648 |
| | XAUUSD | 44.0% | 25 (70 unres.) | 0.690 | 54.2% | 24 (46 unres.) | 0.839 |
| | XAGUSD | 48.0% | 25 (68 unres.) | 1.000 | 40.0% | 5 (39 unres.) | 1.000 |
| | USDJPY | 42.1% | 19 (68 unres.) | 0.648 | 53.9% | 13 (50 unres.) | 1.000 |
| | SPX | 62.5% | 16 (22 unres.) | 0.454 | 66.7% | 6 (13 unres.) | 0.688 |
| | WTI | 52.4% | 21 (55 unres.) | 1.000 | 27.3% | 11 (34 unres.) | 0.227 |
| | BRENT | 50.0% | 14 (29 unres.) | 1.000 | 50.0% | 4 (17 unres.) | 1.000 |
| X6 | crypto | 52.0% | 25 (43 unres.) | 1.000 | 62.5% | 16 (30 unres.) | 0.454 |
|  | metals | 43.8% | 16 (57 unres.) | 0.804 | 66.7% | 12 (42 unres.) | 0.388 |
|  | fx | 28.6% | 7 (29 unres.) | 0.453 | 50.0% | 6 (26 unres.) | 1.000 |
|  | index | 50.0% | 8 (8 unres.) | 1.000 | 100.0% | 1 (3 unres.) | 1.000 |
|  | energy | 44.4% | 9 (26 unres.) | 1.000 | 40.0% | 5 (17 unres.) | 1.000 |
| | BTCUSDT | 53.3% | 15 (23 unres.) | 1.000 | 85.7% | 7 (15 unres.) | 0.125 |
| | ETHUSDT | 50.0% | 10 (20 unres.) | 1.000 | 44.4% | 9 (15 unres.) | 1.000 |
| | XAUUSD | 30.0% | 10 (22 unres.) | 0.344 | 72.7% | 11 (23 unres.) | 0.227 |
| | XAGUSD | 66.7% | 6 (35 unres.) | 0.688 | 0.0% | 1 (19 unres.) | 1.000 |
| | USDJPY | 28.6% | 7 (29 unres.) | 0.453 | 50.0% | 6 (26 unres.) | 1.000 |
| | SPX | 50.0% | 8 (8 unres.) | 1.000 | 100.0% | 1 (3 unres.) | 1.000 |
| | WTI | 40.0% | 5 (17 unres.) | 1.000 | 50.0% | 4 (14 unres.) | 1.000 |
| | BRENT | 50.0% | 4 (9 unres.) | 1.000 | 0.0% | 1 (3 unres.) | 1.000 |
| X7 | crypto | 55.2% | 67 (60 unres.) | 0.464 | 53.2% | 47 (68 unres.) | 0.771 |
|  | metals | 57.0% | 79 (224 unres.) | 0.260 | 36.4% | 77 (184 unres.) | 0.022 |
|  | fx | 49.0% | 49 (143 unres.) | 1.000 | 40.0% | 50 (99 unres.) | 0.203 |
|  | index | 57.7% | 52 (76 unres.) | 0.332 | 57.9% | 38 (52 unres.) | 0.418 |
|  | energy | 55.6% | 90 (212 unres.) | 0.343 | 45.6% | 57 (217 unres.) | 0.597 |
| | BTCUSDT | 50.0% | 30 (22 unres.) | 1.000 | 51.9% | 27 (42 unres.) | 1.000 |
| | ETHUSDT | 59.5% | 37 (38 unres.) | 0.324 | 55.0% | 20 (26 unres.) | 0.824 |
| | XAUUSD | 61.3% | 31 (118 unres.) | 0.281 | 36.8% | 38 (104 unres.) | 0.143 |
| | XAGUSD | 54.2% | 48 (106 unres.) | 0.665 | 35.9% | 39 (80 unres.) | 0.108 |
| | USDJPY | 49.0% | 49 (143 unres.) | 1.000 | 40.0% | 50 (99 unres.) | 0.203 |
| | SPX | 57.7% | 52 (76 unres.) | 0.332 | 57.9% | 38 (52 unres.) | 0.418 |
| | WTI | 53.6% | 56 (109 unres.) | 0.689 | 48.6% | 37 (123 unres.) | 1.000 |
| | BRENT | 58.8% | 34 (103 unres.) | 0.392 | 40.0% | 20 (94 unres.) | 0.503 |
| X8 | crypto | 66.7% | 27 (21 unres.) | 0.122 | 53.3% | 15 (28 unres.) | 1.000 |
|  | metals | 54.2% | 24 (109 unres.) | 0.839 | 44.8% | 29 (89 unres.) | 0.711 |
|  | fx | 38.9% | 18 (64 unres.) | 0.481 | 40.0% | 20 (51 unres.) | 0.503 |
|  | index | 68.4% | 19 (17 unres.) | 0.167 | 47.1% | 17 (15 unres.) | 1.000 |
|  | energy | 76.5% | 17 (81 unres.) | 0.049 | 50.0% | 18 (68 unres.) | 1.000 |
| | BTCUSDT | 57.1% | 14 (9 unres.) | 0.791 | 66.7% | 9 (16 unres.) | 0.508 |
| | ETHUSDT | 76.9% | 13 (12 unres.) | 0.092 | 33.3% | 6 (12 unres.) | 0.688 |
| | XAUUSD | 55.6% | 9 (54 unres.) | 1.000 | 40.0% | 15 (44 unres.) | 0.607 |
| | XAGUSD | 53.3% | 15 (55 unres.) | 1.000 | 50.0% | 14 (45 unres.) | 1.000 |
| | USDJPY | 38.9% | 18 (64 unres.) | 0.481 | 40.0% | 20 (51 unres.) | 0.503 |
| | SPX | 68.4% | 19 (17 unres.) | 0.167 | 47.1% | 17 (15 unres.) | 1.000 |
| | WTI | 75.0% | 12 (43 unres.) | 0.146 | 46.1% | 13 (43 unres.) | 1.000 |
| | BRENT | 80.0% | 5 (38 unres.) | 0.375 | 60.0% | 5 (25 unres.) | 1.000 |

## The registered trade per market group and per market

| id | scope | half | trades | won | R before | R after | PF | per trade (% stake) | net $ |
|---|---|---|---|---|---|---|---|---|---|
| X1 | crypto | first | 127 | 16.5% | +0.130 | -0.566 | 0.61 | -0.1947% | -2,473 |
|  |  | second | 115 | 15.7% | +0.136 | -1.010 | 0.66 | -0.1219% | -1,401 |
|  | metals | first | 303 | 22.4% | +0.163 | -0.325 | 0.92 | -0.0110% | -333 |
|  |  | second | 261 | 21.1% | +0.188 | -0.364 | 0.73 | -0.0341% | -891 |
|  | fx | first | 192 | 20.8% | +0.627 | -0.132 | 0.81 | -0.0088% | -169 |
|  |  | second | 149 | 16.1% | -0.077 | -0.591 | 0.60 | -0.0228% | -340 |
|  | index | first | 128 | 18.8% | -0.100 | -0.450 | 0.91 | -0.0141% | -180 |
|  |  | second | 90 | 22.2% | +0.081 | -0.434 | 0.79 | -0.0223% | -201 |
|  | energy | first | 301 | 22.9% | +0.234 | -0.240 | 1.23 | +0.0543% | +1,635 |
|  |  | second | 274 | 20.4% | +0.328 | -0.314 | 0.70 | -0.0517% | -1,416 |
|  | BTCUSDT | first | 52 | 17.3% | +0.171 | -0.553 | 0.79 | -0.0987% | -513 |
|  |  | second | 69 | 17.4% | +0.247 | -1.141 | 0.82 | -0.0552% | -381 |
|  | ETHUSDT | first | 75 | 16.0% | +0.101 | -0.574 | 0.49 | -0.2612% | -1,959 |
|  |  | second | 46 | 13.0% | -0.031 | -0.813 | 0.50 | -0.2218% | -1,020 |
|  | XAUUSD | first | 149 | 22.1% | +0.177 | -0.384 | 0.65 | -0.0343% | -510 |
|  |  | second | 142 | 19.0% | +0.162 | -0.466 | 0.60 | -0.0378% | -537 |
|  | XAGUSD | first | 154 | 22.7% | +0.149 | -0.268 | 1.07 | +0.0115% | +178 |
|  |  | second | 119 | 23.5% | +0.218 | -0.241 | 0.82 | -0.0297% | -354 |
|  | USDJPY | first | 192 | 20.8% | +0.627 | -0.132 | 0.81 | -0.0088% | -169 |
|  |  | second | 149 | 16.1% | -0.077 | -0.591 | 0.60 | -0.0228% | -340 |
|  | SPX | first | 128 | 18.8% | -0.100 | -0.450 | 0.91 | -0.0141% | -180 |
|  |  | second | 90 | 22.2% | +0.081 | -0.434 | 0.79 | -0.0223% | -201 |
|  | WTI | first | 164 | 22.6% | +0.171 | -0.294 | 1.13 | +0.0317% | +520 |
|  |  | second | 160 | 21.2% | +0.315 | -0.310 | 0.72 | -0.0497% | -795 |
|  | BRENT | first | 137 | 23.4% | +0.310 | -0.174 | 1.36 | +0.0814% | +1,115 |
|  |  | second | 114 | 19.3% | +0.346 | -0.320 | 0.69 | -0.0545% | -621 |
| X2 | crypto | first | 67 | 20.9% | +0.327 | -0.251 | 0.73 | -0.1374% | -920 |
|  |  | second | 60 | 21.7% | +0.515 | -0.495 | 0.83 | -0.0604% | -363 |
|  | metals | first | 169 | 26.0% | +0.240 | -0.208 | 1.09 | +0.0130% | +219 |
|  |  | second | 149 | 21.5% | +0.084 | -0.428 | 0.64 | -0.0503% | -750 |
|  | fx | first | 105 | 17.1% | +0.274 | -0.402 | 0.62 | -0.0191% | -200 |
|  |  | second | 86 | 20.9% | +0.199 | -0.306 | 0.91 | -0.0051% | -44 |
|  | index | first | 49 | 32.7% | +0.548 | +0.233 | 1.08 | +0.0129% | +63 |
|  |  | second | 36 | 41.7% | +1.077 | +0.665 | 2.02 | +0.1000% | +360 |
|  | energy | first | 136 | 31.6% | +0.585 | +0.155 | 1.86 | +0.1833% | +2,493 |
|  |  | second | 117 | 23.9% | +0.244 | -0.337 | 0.67 | -0.0608% | -711 |
|  | BTCUSDT | first | 28 | 25.0% | +0.686 | +0.128 | 1.13 | +0.0634% | +177 |
|  |  | second | 34 | 20.6% | +0.451 | -0.755 | 0.91 | -0.0280% | -95 |
|  | ETHUSDT | first | 39 | 17.9% | +0.070 | -0.523 | 0.47 | -0.2815% | -1,098 |
|  |  | second | 26 | 23.1% | +0.598 | -0.155 | 0.74 | -0.1028% | -267 |
|  | XAUUSD | first | 81 | 22.2% | +0.039 | -0.486 | 0.52 | -0.0523% | -423 |
|  |  | second | 77 | 20.8% | +0.265 | -0.313 | 0.65 | -0.0343% | -264 |
|  | XAGUSD | first | 88 | 29.5% | +0.425 | +0.047 | 1.42 | +0.0731% | +643 |
|  |  | second | 72 | 22.2% | -0.110 | -0.551 | 0.63 | -0.0674% | -485 |
|  | USDJPY | first | 105 | 17.1% | +0.274 | -0.402 | 0.62 | -0.0191% | -200 |
|  |  | second | 86 | 20.9% | +0.199 | -0.306 | 0.91 | -0.0051% | -44 |
|  | SPX | first | 49 | 32.7% | +0.548 | +0.233 | 1.08 | +0.0129% | +63 |
|  |  | second | 36 | 41.7% | +1.077 | +0.665 | 2.02 | +0.1000% | +360 |
|  | WTI | first | 79 | 29.1% | +0.389 | -0.055 | 1.81 | +0.1876% | +1,482 |
|  |  | second | 77 | 24.7% | +0.140 | -0.458 | 0.62 | -0.0680% | -524 |
|  | BRENT | first | 57 | 35.1% | +0.857 | +0.447 | 1.95 | +0.1774% | +1,011 |
|  |  | second | 40 | 22.5% | +0.444 | -0.105 | 0.75 | -0.0468% | -187 |
| X3 | crypto | first | 26 | 19.2% | +0.569 | -0.153 | 0.79 | -0.0967% | -251 |
|  |  | second | 29 | 17.2% | +0.846 | -0.752 | 0.95 | -0.0154% | -45 |
|  | metals | first | 132 | 22.7% | +0.001 | -0.560 | 0.49 | -0.0611% | -807 |
|  |  | second | 138 | 20.3% | +0.027 | -0.618 | 0.60 | -0.0451% | -623 |
|  | fx | first | 95 | 15.8% | +0.270 | -0.569 | 0.60 | -0.0172% | -163 |
|  |  | second | 80 | 15.0% | -0.143 | -0.734 | 0.53 | -0.0244% | -195 |
|  | index | first | 62 | 17.7% | -0.039 | -0.424 | 1.03 | +0.0046% | +29 |
|  |  | second | 44 | 22.7% | +0.195 | -0.336 | 0.83 | -0.0181% | -79 |
|  | energy | first | 124 | 29.8% | +0.269 | -0.289 | 1.10 | +0.0180% | +224 |
|  |  | second | 144 | 21.5% | +0.223 | -0.459 | 0.73 | -0.0415% | -598 |
|  | BTCUSDT | first | 12 | 25.0% | +0.630 | -0.183 | 1.12 | +0.0456% | +55 |
|  |  | second | 22 | 13.6% | +0.807 | -0.997 | 0.91 | -0.0267% | -59 |
|  | ETHUSDT | first | 14 | 14.3% | +0.517 | -0.128 | 0.58 | -0.2186% | -306 |
|  |  | second | 7 | 28.6% | +0.967 | +0.019 | 1.07 | +0.0202% | +14 |
|  | XAUUSD | first | 69 | 23.2% | +0.119 | -0.543 | 0.61 | -0.0319% | -220 |
|  |  | second | 72 | 18.1% | +0.039 | -0.710 | 0.51 | -0.0401% | -288 |
|  | XAGUSD | first | 63 | 22.2% | -0.128 | -0.579 | 0.43 | -0.0931% | -586 |
|  |  | second | 66 | 22.7% | +0.015 | -0.518 | 0.66 | -0.0507% | -335 |
|  | USDJPY | first | 95 | 15.8% | +0.270 | -0.569 | 0.60 | -0.0172% | -163 |
|  |  | second | 80 | 15.0% | -0.143 | -0.734 | 0.53 | -0.0244% | -195 |
|  | SPX | first | 62 | 17.7% | -0.039 | -0.424 | 1.03 | +0.0046% | +29 |
|  |  | second | 44 | 22.7% | +0.195 | -0.336 | 0.83 | -0.0181% | -79 |
|  | WTI | first | 67 | 35.8% | +0.664 | +0.123 | 1.89 | +0.1433% | +960 |
|  |  | second | 86 | 18.6% | +0.016 | -0.645 | 0.54 | -0.0759% | -653 |
|  | BRENT | first | 57 | 22.8% | -0.195 | -0.775 | 0.35 | -0.1291% | -736 |
|  |  | second | 58 | 25.9% | +0.529 | -0.183 | 1.07 | +0.0094% | +55 |
| X4 | crypto | first | 87 | 29.9% | +0.071 | -0.196 | 0.79 | -0.1586% | -1,380 |
|  |  | second | 79 | 27.8% | +0.018 | -0.469 | 0.67 | -0.1602% | -1,266 |
|  | metals | first | 242 | 34.7% | -0.017 | -0.251 | 0.98 | -0.0034% | -82 |
|  |  | second | 206 | 31.6% | -0.075 | -0.353 | 0.66 | -0.0578% | -1,191 |
|  | fx | first | 154 | 33.8% | +0.093 | -0.253 | 0.63 | -0.0270% | -416 |
|  |  | second | 121 | 26.4% | -0.173 | -0.436 | 0.55 | -0.0358% | -434 |
|  | index | first | 101 | 39.6% | +0.162 | -0.020 | 1.84 | +0.1334% | +1,348 |
|  |  | second | 75 | 41.3% | +0.241 | -0.002 | 1.05 | +0.0072% | +54 |
|  | energy | first | 221 | 38.0% | +0.073 | -0.148 | 1.08 | +0.0268% | +593 |
|  |  | second | 204 | 39.7% | +0.258 | -0.040 | 0.91 | -0.0194% | -396 |
|  | BTCUSDT | first | 40 | 35.0% | +0.304 | +0.004 | 1.37 | +0.2235% | +894 |
|  |  | second | 47 | 34.0% | +0.210 | -0.366 | 0.96 | -0.0141% | -66 |
|  | ETHUSDT | first | 47 | 25.5% | -0.127 | -0.367 | 0.47 | -0.4837% | -2,274 |
|  |  | second | 32 | 18.8% | -0.265 | -0.620 | 0.41 | -0.3747% | -1,199 |
|  | XAUUSD | first | 118 | 28.8% | -0.208 | -0.484 | 0.53 | -0.0671% | -792 |
|  |  | second | 110 | 30.9% | -0.120 | -0.417 | 0.57 | -0.0522% | -574 |
|  | XAGUSD | first | 124 | 40.3% | +0.164 | -0.029 | 1.28 | +0.0573% | +710 |
|  |  | second | 96 | 32.3% | -0.024 | -0.279 | 0.71 | -0.0643% | -617 |
|  | USDJPY | first | 154 | 33.8% | +0.093 | -0.253 | 0.63 | -0.0270% | -416 |
|  |  | second | 121 | 26.4% | -0.173 | -0.436 | 0.55 | -0.0358% | -434 |
|  | SPX | first | 101 | 39.6% | +0.162 | -0.020 | 1.84 | +0.1334% | +1,348 |
|  |  | second | 75 | 41.3% | +0.241 | -0.002 | 1.05 | +0.0072% | +54 |
|  | WTI | first | 125 | 40.8% | +0.090 | -0.126 | 1.10 | +0.0327% | +408 |
|  |  | second | 122 | 33.6% | +0.176 | -0.118 | 0.77 | -0.0545% | -665 |
|  | BRENT | first | 96 | 34.4% | +0.050 | -0.177 | 1.05 | +0.0193% | +185 |
|  |  | second | 82 | 48.8% | +0.380 | +0.077 | 1.19 | +0.0328% | +269 |
| X5 | crypto | first | 157 | 42.0% | -0.070 | -0.216 | 0.80 | -0.1652% | -2,593 |
|  |  | second | 112 | 40.2% | -0.050 | -0.265 | 0.66 | -0.1964% | -2,200 |
|  | metals | first | 183 | 44.8% | +0.192 | +0.049 | 0.93 | -0.0144% | -263 |
|  |  | second | 114 | 43.0% | +0.084 | -0.051 | 0.77 | -0.0452% | -515 |
|  | fx | first | 86 | 39.5% | -0.014 | -0.200 | 0.91 | -0.0078% | -67 |
|  |  | second | 63 | 39.7% | -0.090 | -0.233 | 0.96 | -0.0034% | -21 |
|  | index | first | 38 | 36.8% | +0.151 | -0.016 | 0.56 | -0.1329% | -505 |
|  |  | second | 19 | 36.8% | +0.007 | -0.181 | 0.73 | -0.0362% | -69 |
|  | energy | first | 118 | 36.4% | -0.015 | -0.159 | 1.45 | +0.1437% | +1,696 |
|  |  | second | 66 | 24.2% | -0.169 | -0.354 | 0.48 | -0.1537% | -1,015 |
|  | BTCUSDT | first | 84 | 42.9% | -0.018 | -0.172 | 0.95 | -0.0315% | -264 |
|  |  | second | 55 | 38.2% | -0.081 | -0.333 | 0.67 | -0.1663% | -914 |
|  | ETHUSDT | first | 73 | 41.1% | -0.130 | -0.265 | 0.69 | -0.3191% | -2,329 |
|  |  | second | 57 | 42.1% | -0.020 | -0.199 | 0.65 | -0.2255% | -1,285 |
|  | XAUUSD | first | 92 | 39.1% | +0.156 | +0.001 | 0.57 | -0.0725% | -667 |
|  |  | second | 70 | 41.4% | +0.108 | -0.053 | 0.87 | -0.0197% | -138 |
|  | XAGUSD | first | 91 | 50.5% | +0.228 | +0.098 | 1.18 | +0.0444% | +404 |
|  |  | second | 44 | 45.5% | +0.045 | -0.048 | 0.67 | -0.0857% | -377 |
|  | USDJPY | first | 86 | 39.5% | -0.014 | -0.200 | 0.91 | -0.0078% | -67 |
|  |  | second | 63 | 39.7% | -0.090 | -0.233 | 0.96 | -0.0034% | -21 |
|  | SPX | first | 38 | 36.8% | +0.151 | -0.016 | 0.56 | -0.1329% | -505 |
|  |  | second | 19 | 36.8% | +0.007 | -0.181 | 0.73 | -0.0362% | -69 |
|  | WTI | first | 75 | 34.7% | -0.097 | -0.228 | 0.94 | -0.0212% | -159 |
|  |  | second | 45 | 22.2% | -0.129 | -0.320 | 0.35 | -0.2006% | -903 |
|  | BRENT | first | 43 | 39.5% | +0.129 | -0.040 | 2.48 | +0.4314% | +1,855 |
|  |  | second | 21 | 28.6% | -0.254 | -0.426 | 0.79 | -0.0533% | -112 |
| X6 | crypto | first | 68 | 35.3% | +0.007 | -0.081 | 0.84 | -0.1506% | -1,024 |
|  |  | second | 46 | 47.8% | +0.051 | -0.087 | 1.04 | +0.0188% | +86 |
|  | metals | first | 70 | 37.1% | +0.034 | -0.052 | 0.81 | -0.0365% | -256 |
|  |  | second | 54 | 57.4% | +0.105 | +0.026 | 1.31 | +0.0458% | +247 |
|  | fx | first | 36 | 52.8% | +0.070 | -0.037 | 0.90 | -0.0090% | -32 |
|  |  | second | 32 | 56.2% | -0.050 | -0.123 | 1.00 | +0.0002% | +1 |
|  | index | first | 16 | 50.0% | +0.167 | +0.092 | 0.45 | -0.2751% | -440 |
|  |  | second | 4 | 50.0% | +0.182 | +0.106 | 10.01 | +0.1103% | +44 |
|  | energy | first | 35 | 42.9% | -0.013 | -0.088 | 1.62 | +0.1964% | +687 |
|  |  | second | 22 | 31.8% | -0.060 | -0.148 | 0.58 | -0.1408% | -310 |
|  | BTCUSDT | first | 38 | 34.2% | -0.029 | -0.120 | 1.02 | +0.0132% | +50 |
|  |  | second | 22 | 50.0% | +0.093 | -0.067 | 1.41 | +0.1285% | +283 |
|  | ETHUSDT | first | 30 | 36.7% | +0.053 | -0.031 | 0.71 | -0.3581% | -1,074 |
|  |  | second | 24 | 45.8% | +0.012 | -0.106 | 0.85 | -0.0817% | -196 |
|  | XAUUSD | first | 31 | 25.8% | -0.126 | -0.234 | 0.26 | -0.1758% | -545 |
|  |  | second | 34 | 58.8% | +0.119 | +0.032 | 1.75 | +0.0908% | +309 |
|  | XAGUSD | first | 39 | 46.2% | +0.161 | +0.092 | 1.45 | +0.0742% | +289 |
|  |  | second | 20 | 55.0% | +0.079 | +0.016 | 0.84 | -0.0305% | -61 |
|  | USDJPY | first | 36 | 52.8% | +0.070 | -0.037 | 0.90 | -0.0090% | -32 |
|  |  | second | 32 | 56.2% | -0.050 | -0.123 | 1.00 | +0.0002% | +1 |
|  | SPX | first | 16 | 50.0% | +0.167 | +0.092 | 0.45 | -0.2751% | -440 |
|  |  | second | 4 | 50.0% | +0.182 | +0.106 | 10.01 | +0.1103% | +44 |
|  | WTI | first | 22 | 31.8% | -0.025 | -0.116 | 0.93 | -0.0212% | -47 |
|  |  | second | 18 | 33.3% | +0.009 | -0.083 | 0.61 | -0.1156% | -208 |
|  | BRENT | first | 13 | 61.5% | +0.007 | -0.040 | 2.62 | +0.5647% | +734 |
|  |  | second | 4 | 25.0% | -0.368 | -0.439 | 0.49 | -0.2542% | -102 |
| X7 | crypto | first | 127 | 40.9% | +0.082 | -0.044 | 0.97 | -0.0303% | -385 |
|  |  | second | 115 | 36.5% | +0.056 | -0.143 | 0.82 | -0.1072% | -1,233 |
|  | metals | first | 303 | 42.6% | +0.065 | -0.040 | 0.99 | -0.0015% | -45 |
|  |  | second | 260 | 40.0% | -0.043 | -0.160 | 0.66 | -0.0762% | -1,982 |
|  | fx | first | 192 | 44.3% | +0.038 | -0.095 | 0.82 | -0.0147% | -282 |
|  |  | second | 149 | 36.2% | -0.134 | -0.231 | 0.55 | -0.0505% | -753 |
|  | index | first | 128 | 42.2% | +0.114 | +0.009 | 1.35 | +0.0765% | +979 |
|  |  | second | 90 | 37.8% | +0.004 | -0.134 | 0.72 | -0.0472% | -425 |
|  | energy | first | 302 | 43.7% | +0.071 | -0.020 | 1.17 | +0.0666% | +2,012 |
|  |  | second | 274 | 38.3% | -0.004 | -0.128 | 0.68 | -0.0884% | -2,421 |
|  | BTCUSDT | first | 52 | 44.2% | +0.084 | -0.051 | 0.97 | -0.0237% | -123 |
|  |  | second | 69 | 37.7% | +0.111 | -0.119 | 0.89 | -0.0545% | -376 |
|  | ETHUSDT | first | 75 | 38.7% | +0.081 | -0.038 | 0.96 | -0.0350% | -262 |
|  |  | second | 46 | 34.8% | -0.027 | -0.180 | 0.74 | -0.1864% | -857 |
|  | XAUUSD | first | 149 | 40.9% | +0.090 | -0.030 | 1.08 | +0.0107% | +159 |
|  |  | second | 141 | 41.1% | -0.053 | -0.183 | 0.55 | -0.0731% | -1,031 |
|  | XAGUSD | first | 154 | 44.2% | +0.041 | -0.050 | 0.95 | -0.0132% | -204 |
|  |  | second | 119 | 38.7% | -0.031 | -0.132 | 0.73 | -0.0799% | -951 |
|  | USDJPY | first | 192 | 44.3% | +0.038 | -0.095 | 0.82 | -0.0147% | -282 |
|  |  | second | 149 | 36.2% | -0.134 | -0.231 | 0.55 | -0.0505% | -753 |
|  | SPX | first | 128 | 42.2% | +0.114 | +0.009 | 1.35 | +0.0765% | +979 |
|  |  | second | 90 | 37.8% | +0.004 | -0.134 | 0.72 | -0.0472% | -425 |
|  | WTI | first | 165 | 44.8% | +0.043 | -0.050 | 1.02 | +0.0107% | +177 |
|  |  | second | 160 | 36.2% | -0.025 | -0.151 | 0.64 | -0.1041% | -1,666 |
|  | BRENT | first | 137 | 42.3% | +0.105 | +0.017 | 1.36 | +0.1339% | +1,835 |
|  |  | second | 114 | 41.2% | +0.025 | -0.097 | 0.74 | -0.0662% | -755 |
| X8 | crypto | first | 48 | 45.8% | +0.279 | +0.189 | 1.88 | +0.7177% | +3,445 |
|  |  | second | 43 | 46.5% | +0.105 | -0.037 | 0.96 | -0.0205% | -88 |
|  | metals | first | 133 | 46.6% | +0.029 | -0.051 | 1.01 | +0.0015% | +20 |
|  |  | second | 117 | 39.3% | -0.027 | -0.117 | 0.64 | -0.0829% | -970 |
|  | fx | first | 82 | 46.3% | -0.006 | -0.108 | 0.62 | -0.0373% | -306 |
|  |  | second | 71 | 38.0% | -0.022 | -0.103 | 0.74 | -0.0254% | -180 |
|  | index | first | 36 | 61.1% | +0.268 | +0.200 | 2.95 | +0.2327% | +838 |
|  |  | second | 32 | 46.9% | -0.038 | -0.132 | 0.50 | -0.1475% | -472 |
|  | energy | first | 98 | 48.0% | +0.073 | +0.004 | 1.13 | +0.0526% | +516 |
|  |  | second | 86 | 36.0% | -0.040 | -0.135 | 0.56 | -0.1403% | -1,207 |
|  | BTCUSDT | first | 23 | 47.8% | +0.314 | +0.226 | 2.42 | +1.1457% | +2,635 |
|  |  | second | 25 | 56.0% | +0.286 | +0.128 | 1.75 | +0.2598% | +649 |
|  | ETHUSDT | first | 25 | 44.0% | +0.246 | +0.156 | 1.40 | +0.3239% | +810 |
|  |  | second | 18 | 33.3% | -0.146 | -0.266 | 0.51 | -0.4098% | -738 |
|  | XAUUSD | first | 63 | 46.0% | +0.035 | -0.058 | 1.10 | +0.0122% | +77 |
|  |  | second | 59 | 40.7% | -0.038 | -0.137 | 0.59 | -0.0746% | -440 |
|  | XAGUSD | first | 70 | 47.1% | +0.024 | -0.044 | 0.97 | -0.0082% | -57 |
|  |  | second | 58 | 37.9% | -0.016 | -0.097 | 0.67 | -0.0914% | -530 |
|  | USDJPY | first | 82 | 46.3% | -0.006 | -0.108 | 0.62 | -0.0373% | -306 |
|  |  | second | 71 | 38.0% | -0.022 | -0.103 | 0.74 | -0.0254% | -180 |
|  | SPX | first | 36 | 61.1% | +0.268 | +0.200 | 2.95 | +0.2327% | +838 |
|  |  | second | 32 | 46.9% | -0.038 | -0.132 | 0.50 | -0.1475% | -472 |
|  | WTI | first | 55 | 52.7% | +0.124 | +0.052 | 1.02 | +0.0111% | +61 |
|  |  | second | 56 | 33.9% | -0.052 | -0.148 | 0.50 | -0.1713% | -959 |
|  | BRENT | first | 43 | 41.9% | +0.008 | -0.058 | 1.33 | +0.1058% | +455 |
|  |  | second | 30 | 40.0% | -0.018 | -0.111 | 0.69 | -0.0825% | -247 |

## Descriptive: by the push's direction (pooled, within the day)

| id | push | first: hit | resolved | p | second: hit | resolved | p |
|---|---|---|---|---|---|---|---|
| X1 | up push (fade short) | 55.4% | 195 (472 unres.) | 0.152 | 41.0% | 173 (373 unres.) | 0.022 |
| X1 | down push (fade long) | 54.9% | 142 (243 unres.) | 0.275 | 52.1% | 96 (247 unres.) | 0.760 |
| X2 | up push (fade short) | 60.8% | 107 (212 unres.) | 0.033 | 43.5% | 85 (195 unres.) | 0.278 |
| X2 | down push (fade long) | 56.6% | 76 (132 unres.) | 0.302 | 55.8% | 52 (116 unres.) | 0.488 |
| X3 | up push (fade short) | 63.2% | 57 (242 unres.) | 0.063 | 47.0% | 66 (231 unres.) | 0.712 |
| X3 | down push (fade long) | 42.3% | 26 (115 unres.) | 0.557 | 54.2% | 24 (114 unres.) | 0.839 |
| X4 | up push (fade short) | 53.1% | 128 (387 unres.) | 0.536 | 47.4% | 116 (310 unres.) | 0.643 |
| X4 | down push (fade long) | 63.0% | 81 (209 unres.) | 0.026 | 56.9% | 58 (201 unres.) | 0.358 |
| X5 | up push (fade short) | 52.5% | 80 (184 unres.) | 0.738 | 57.5% | 47 (115 unres.) | 0.382 |
| X5 | down push (fade long) | 42.6% | 101 (224 unres.) | 0.163 | 38.6% | 57 (155 unres.) | 0.111 |
| X6 | up push (fade short) | 50.0% | 28 (70 unres.) | 1.000 | 60.0% | 20 (53 unres.) | 0.503 |
| X6 | down push (fade long) | 43.2% | 37 (93 unres.) | 0.511 | 60.0% | 20 (65 unres.) | 0.503 |
| X7 | up push (fade short) | 55.4% | 195 (472 unres.) | 0.152 | 41.0% | 173 (373 unres.) | 0.022 |
| X7 | down push (fade long) | 54.9% | 142 (243 unres.) | 0.275 | 52.1% | 96 (247 unres.) | 0.760 |
| X8 | up push (fade short) | 58.0% | 69 (174 unres.) | 0.228 | 46.1% | 65 (153 unres.) | 0.620 |
| X8 | down push (fade long) | 66.7% | 36 (118 unres.) | 0.065 | 47.1% | 34 (98 unres.) | 0.864 |

## Checks

| market | bars | first bar | last bar | fee a side | truncation cuts | events compared | mismatched runs | entries skipped (gap beyond stop, all variants) |
|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 240306 | 2019-01-01 00:00 | 2025-11-10 23:45 | 0.100% | 2 | 1138 | 0 | 0 |
| ETHUSDT | 240306 | 2019-01-01 00:00 | 2025-11-10 23:45 | 0.100% | 2 | 1156 | 0 | 0 |
| XAUUSD | 162247 | 2019-01-01 23:00 | 2025-11-10 23:45 | 0.020% | 2 | 2450 | 0 | 0 |
| XAGUSD | 162216 | 2019-01-01 23:00 | 2025-11-10 23:45 | 0.030% | 2 | 2437 | 0 | 0 |
| USDJPY | 171130 | 2019-01-01 22:00 | 2025-11-10 23:45 | 0.010% | 2 | 2915 | 0 | 0 |
| SPX | 44687 | 2019-01-02 14:30 | 2025-11-10 20:45 | 0.020% | 2 | 1724 | 0 | 0 |
| WTI | 161931 | 2019-01-01 23:00 | 2025-11-10 23:45 | 0.040% | 2 | 2372 | 0 | 3 |
| BRENT | 147959 | 2019-01-02 01:00 | 2025-11-10 21:45 | 0.040% | 2 | 1760 | 0 | 0 |

## Overlap with earlier tests and what the engine reads

- H44 V7 (exhausted contrast) traded WITH 24-bar breaks on a momentum bar on exhausted days; H49 fades the weak (no momentum) pushes. H44's reference row (24-bar breaks without momentum on exhausted days drifted back) is where the idea came from, so H49 is not independent of H44's data.
- H7 (breakout trap, `playbook.py` p2) faded failed first closes beyond the 48-bar / prior-day / swing levels with no daily-budget condition; it lost about its costs.
- `cs_used_x` (card 'Candle size and realistic targets') and `adr_used` (reading-only, not wired) already read the share of the day's range used; `adr_bar` reads the bar's size in ATR15. H49's event is the combination of the two at a new extreme.

## Live scan at write time (PAPER / UNTESTED)

```
H49 live exhaustion-fade scan, 16 Nov 2026 06:28 UTC (PAPER; UNTESTED / no variant passed H49's history bar)
  BTCUSDT  last close Mon 16 Nov 06:15 UTC; daily ATR 2712.25; day used 40% of it (high 65392.01 / low 64294.11)
      no exhaustion-fade event today
  ETHUSDT  last close Mon 16 Nov 06:15 UTC; daily ATR 107.97; day used 33% of it (high 1838.77 / low 1803.63)
      no exhaustion-fade event today
  XAUUSD   last close Mon 16 Nov 06:00 UTC; daily ATR 76.4270; day used 89% of it (high 3903.50 / low 3835.20)
      no exhaustion-fade event today
  XAGUSD   last close Mon 16 Nov 06:00 UTC; daily ATR 1.8280; day used 103% of it (high 48.9550 / low 47.0650)
      no exhaustion-fade event today
  USDJPY   last close Mon 16 Nov 06:15 UTC; daily ATR 0.9019; day used 56% of it (high 159.86 / low 159.35)
      no exhaustion-fade event today
  SPX      last close Fri 13 Nov 21:00 UTC (57 h old: market shut; last session shown); daily ATR 106.19; day used 115% of it (high 7621.78 / low 7499.40)
      X5 DOWN push at 20:30 close (used 115%, bar 0.58 ATR15): fade LONG entry 7550.02, stop 7495.95, target 7603.11: open
  WTI      last close Mon 16 Nov 06:00 UTC; daily ATR 3.5337; day used 34% of it (high 88.8000 / low 87.5900)
      no exhaustion-fade event today
  BRENT    last close Mon 16 Nov 06:00 UTC; daily ATR 4.9953; day used 28% of it (high 95.8700 / low 94.4600)
      no exhaustion-fade event today
  (PAPER / UNTESTED unless marked passed; nothing is traded or wired)
```
