# H61: a wide profit floor for the main book's big winners

Written by `research/h61_profit_floor.py` on 2026-11-21 01:40 UTC. Paper only. A replay of history this project has already read five times for exits. Nothing here is a proven edge, and nothing here changes a book.

Each rule takes every main-book trade at the main book's own fill, adds one wide stop that arms only on a big winner, and after an exit at that stop stays flat until the main book's next entry. R = the distance from entry to the entry stop.

## Gates

- The overlay with a rule that never arms reproduced `main` on 8 of 8 markets (every trade and the marked equity at every bar).
- `main` here against H60's run: reproduced exactly on all 8 markets.

## (a) Whole books: is any rule better than holding?

H36's test: pooled net P&L above the main book's in BOTH halves, above it in at least 5 of 8 markets, pooled max drawdown no worse.

| Book | Net P&L | vs main | First half vs main | Second half vs main | Markets beating main | Max DD | Sharpe | Trades | Better than holding |
|---|---|---|---|---|---|---|---|---|---|
| `main` | +339325 |  | +152355 | +186970 |  | -32.8% | 0.92 | 1080 | n/a |
| `floor_50pct_5r` | +457871 | +118545 | -1442 | +119987 | 5 of 8 | -23.8% | 1.24 | 1080 | no |
| `floor_50pct_3r` | +300397 | -38928 | -39165 | +237 | 4 of 8 | -15.2% | 1.27 | 1082 | no |
| `floor_33pct_5r` | +340166 | +841 | -871 | +1712 | 5 of 8 | -29.6% | 1.01 | 1080 | no |
| `floor_33pct_3r` | +393294 | +53968 | +4875 | +49093 | 5 of 8 | -27.0% | 1.09 | 1081 | YES |
| `chandelier_4h_3atr_3r` | +125289 | -214037 | -89319 | -124718 | 2 of 8 | -14.2% | 0.94 | 1085 | no |
| `swing_4h_5r` | +177559 | -161767 | -45457 | -116309 | 2 of 8 | -20.6% | 0.94 | 1083 | no |

(For `main` the two half columns show its own P&L in each half.)

### Per market, whole window: net P&L (max drawdown)

| Market | `main` | `floor_50pct_5r` | `floor_50pct_3r` | `floor_33pct_5r` | `floor_33pct_3r` | `chandelier_4h_3atr_3r` | `swing_4h_5r` |
|---|---|---|---|---|---|---|---|
| SPX | +6320 (-31%) | +9469 (-26%) | +8615 (-22%) | +8337 (-28%) | +6841 (-28%) | +3810 (-18%) | +3001 (-17%) |
| USDJPY | +6965 (-58%) | -2447 (-41%) | -1917 (-36%) | -3412 (-44%) | -3121 (-42%) | -1250 (-34%) | +211 (-33%) |
| BTCUSDT | +25155 (-81%) | +51337 (-79%) | +20442 (-73%) | +41539 (-75%) | +7356 (-78%) | +226 (-77%) | +2943 (-82%) |
| ETHUSDT | +240638 (-53%) | +238245 (-45%) | +182575 (-39%) | +209097 (-52%) | +318320 (-43%) | +83966 (-36%) | +85660 (-49%) |
| XAUUSD | +26565 (-59%) | +2492 (-30%) | +809 (-24%) | +1085 (-40%) | -249 (-32%) | +4089 (-21%) | +2608 (-22%) |
| XAGUSD | +3104 (-79%) | +4844 (-69%) | +6012 (-56%) | +6212 (-72%) | +9058 (-67%) | -2824 (-53%) | -4621 (-63%) |
| WTI | +24898 (-55%) | +115323 (-40%) | +67327 (-37%) | +62031 (-46%) | +41939 (-43%) | +27954 (-37%) | +70021 (-45%) |
| BRENT | +5682 (-67%) | +38607 (-52%) | +16535 (-38%) | +15278 (-63%) | +13150 (-60%) | +9318 (-32%) | +17736 (-41%) |

### Per market, each half: net P&L

| Market | Half | `main` | `floor_50pct_5r` | `floor_50pct_3r` | `floor_33pct_5r` | `floor_33pct_3r` | `chandelier_4h_3atr_3r` | `swing_4h_5r` |
|---|---|---|---|---|---|---|---|---|
| SPX | 1st | -688 | -110 | -985 | -326 | -1405 | -734 | +451 |
| SPX | 2nd | +7007 | +9579 | +9600 | +8663 | +8246 | +4544 | +2550 |
| USDJPY | 1st | +14462 | -516 | -565 | -1232 | -1429 | -747 | +254 |
| USDJPY | 2nd | -7497 | -1931 | -1351 | -2181 | -1691 | -503 | -43 |
| BTCUSDT | 1st | +1020 | +5750 | +7693 | +5803 | +1989 | -4649 | -3541 |
| BTCUSDT | 2nd | +24135 | +45588 | +12749 | +35736 | +5367 | +4876 | +6484 |
| ETHUSDT | 1st | +99542 | +68697 | +29601 | +84083 | +91766 | +37912 | +78180 |
| ETHUSDT | 2nd | +141096 | +169549 | +152974 | +125015 | +226553 | +46054 | +7481 |
| XAUUSD | 1st | -3012 | -260 | +698 | -507 | +546 | +3457 | +1944 |
| XAUUSD | 2nd | +29576 | +2751 | +111 | +1592 | -795 | +632 | +665 |
| XAGUSD | 1st | +4137 | +281 | +2726 | +6052 | +6953 | +1989 | -228 |
| XAGUSD | 2nd | -1033 | +4564 | +3286 | +160 | +2106 | -4814 | -4394 |
| WTI | 1st | +29593 | +58478 | +58411 | +45441 | +41850 | +19892 | +26114 |
| WTI | 2nd | -4696 | +56845 | +8917 | +16590 | +88 | +8062 | +43907 |
| BRENT | 1st | +7300 | +18594 | +15612 | +12170 | +16960 | +5916 | +3724 |
| BRENT | 2nd | -1619 | +20013 | +923 | +3107 | -3810 | +3402 | +14011 |

## (b) The same question at equal size: R kept per armed trade

Per main-book trade that armed the rule and that the main book has closed: the R the rule ended with minus the R the main book ended with, on the same entry and the same risk. No compounding, so one market cannot decide it. "Helps per trade" needs a mean above zero in BOTH halves and in at least 5 markets.

| Rule | Armed trades | Closed by the rule | Mean peak | Main ended | Rule ended | Mean gain, all | 1st half (n) | 2nd half (n) | Better / worse | Markets helped | Helps per trade |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `floor_50pct_5r` | 189 | 150 | 12.1R | +7.8R | +7.1R | -0.71R | -0.42R (100) | -1.03R (89) | 111 / 39 | 6 of 8 | no |
| `floor_50pct_3r` | 267 | 234 | 7.8R | +5.5R | +4.4R | -1.04R | -0.49R (146) | -1.70R (121) | 165 / 69 | 4 of 8 | no |
| `floor_33pct_5r` | 189 | 125 | 13.1R | +7.8R | +6.6R | -1.19R | -0.26R (100) | -2.24R (89) | 92 / 33 | 5 of 8 | no |
| `floor_33pct_3r` | 267 | 209 | 8.8R | +5.5R | +4.2R | -1.26R | -0.29R (146) | -2.43R (121) | 150 / 59 | 4 of 8 | no |
| `chandelier_4h_3atr_3r` | 267 | 260 | 5.5R | +5.5R | +3.5R | -1.94R | -1.20R (146) | -2.82R (121) | 167 / 93 | 2 of 8 | no |
| `swing_4h_5r` | 189 | 184 | 7.9R | +7.8R | +5.3R | -2.53R | -1.49R (100) | -3.70R (89) | 118 / 66 | 2 of 8 | no |

| Rule | Largest give-back the main book took from a peak | Most the rule left on the table in one trade |
|---|---|---|
| `floor_50pct_5r` | 103.2R | 223.6R |
| `floor_50pct_3r` | 103.2R | 225.2R |
| `floor_33pct_5r` | 103.2R | 224.4R |
| `floor_33pct_3r` | 103.2R | 224.4R |
| `chandelier_4h_3atr_3r` | 14.5R | 222.9R |
| `swing_4h_5r` | 21.2R | 223.1R |

### Per market: armed trades and mean gain in R

| Market | `floor_50pct_5r` | `floor_50pct_3r` | `floor_33pct_5r` | `floor_33pct_3r` | `chandelier_4h_3atr_3r` | `swing_4h_5r` |
|---|---|---|---|---|---|---|
| SPX | 9: +1.02R | 11: +0.60R | 9: +0.67R | 11: +0.13R | 11: -1.30R | 9: -1.95R |
| USDJPY | 16: -5.51R | 21: -4.04R | 16: -5.95R | 21: -4.43R | 21: -3.83R | 16: -4.48R |
| BTCUSDT | 39: +0.49R | 53: -1.46R | 39: +0.39R | 53: -1.89R | 53: -2.63R | 39: -3.31R |
| ETHUSDT | 39: +0.02R | 58: -0.25R | 39: -0.21R | 58: -0.03R | 58: -1.33R | 39: -2.05R |
| XAUUSD | 18: -10.87R | 27: -7.02R | 18: -11.17R | 27: -7.17R | 27: -6.47R | 18: -10.20R |
| XAGUSD | 19: +0.04R | 29: +0.63R | 19: +0.13R | 29: +0.34R | 29: -2.07R | 19: -3.93R |
| WTI | 24: +2.69R | 33: +1.23R | 24: +1.48R | 33: +0.67R | 33: +0.40R | 24: +1.94R |
| BRENT | 25: +2.21R | 35: +0.65R | 25: +0.81R | 35: +0.52R | 35: +0.46R | 25: +1.26R |

## (c) Today's open main-book trades under each rule (description, not a test)

Live book as of the page of 2026-11-21T01:32:48Z UTC (engine think15-v5.2.7). "Locks" = net dollars if the level were hit, at the live size.

| Market | Trade | Open now | `floor_50pct_5r` | `floor_50pct_3r` | `floor_33pct_5r` | `floor_33pct_3r` | `chandelier_4h_3atr_3r` | `swing_4h_5r` |
|---|---|---|---|---|---|---|---|---|
| SPX | SHORT | this market has its own exit rule on the live book (half at Target 1) | | | | | | |
| USDJPY | LONG | this market has its own exit rule on the live book (half at Target 1) | | | | | | |
| BTCUSDT | SHORT from 74466.4, 11-11 18:30 | +10.5R, $+2003 | level 66301.4 = +5.5R, locks $+1048, 12.4% away | level 66301.4 = +5.5R, locks $+1048, 12.4% away | level 69023.1 = +3.7R, locks $+692, 17.0% away | level 69023.1 = +3.7R, locks $+692, 17.0% away | CLOSED 11-15 09:00 at +5.7R, banked $+1080 (-923 vs open now) | level 64080.8 = +7.0R, locks $+1338, 8.6% away |
| ETHUSDT | SHORT from 2097.55, 11-10 13:15 | +9.7R, $+2254 | level 1845.79 = +5.1R, locks $+1181, 13.9% away | level 1845.79 = +5.1R, locks $+1181, 13.9% away | level 1929.71 = +3.4R, locks $+781, 19.1% away | level 1929.71 = +3.4R, locks $+781, 19.1% away | CLOSED 11-16 14:30 at +4.9R, banked $+1142 (-1112 vs open now) | CLOSED 11-16 14:30 at +5.1R, banked $+1184 (-1070 vs open now) |
| XAUUSD | SHORT from 4029.2, 11-10 16:45 | +8.7R, $+1731 | level 3768 = +4.6R, locks $+920, 6.5% away | level 3768 = +4.6R, locks $+920, 6.5% away | level 3855.07 = +3.1R, locks $+611, 8.9% away | level 3855.07 = +3.1R, locks $+611, 8.9% away | level 3640.1 = +6.9R, locks $+1373, 2.9% away | level 3894 = +2.4R, locks $+473, 10.0% away |
| XAGUSD | SHORT from 52.95, 11-11 06:15 | +10.4R, $+2177 | level 46.8125 = +5.4R, locks $+1123, 13.9% away | level 46.8125 = +5.4R, locks $+1123, 13.9% away | level 48.8583 = +3.6R, locks $+747, 18.9% away | level 48.8583 = +3.6R, locks $+747, 18.9% away | level 43.6246 = +8.2R, locks $+1709, 6.2% away | level 47.92 = +4.4R, locks $+919, 16.6% away |
| WTI | SHORT from 88.93, 11-12 21:00 | +2.2R, $+572 | not armed (peak 3.3R) | level 84.945 = +1.6R, locks $+428, 1.6% away | not armed (peak 3.3R) | level 86.2733 = +1.1R, locks $+282, 3.2% away | level 84.5971 = +1.8R, locks $+466, 1.2% away | not armed (peak 3.3R) |
| BRENT | SHORT from 95.62, 11-12 19:15 | +2.1R, $+576 | not armed (peak 2.9R) | not armed (peak 2.9R) | not armed (peak 2.9R) | not armed (peak 2.9R) | not armed (peak 2.9R) | not armed (peak 2.9R) |

