# H112: an entry bar set per market, for the six non-crypto markets

A replay on history. It is post-mortem material, not validation. Nothing live was changed.
Registered in `research/HYPOTHESES.md` (H112) before any number on history was computed.
The prior expectation was low: earlier studies (H65, H80, H82b, H92, H93) found that the book's entry word, its
odds and its entry bar made little or no measurable difference on history.

## Words

- **Lead**: the engine's P(up first) minus P(down first), in points. |Lead| is its size, whichever way it points.
- **Step**: one 15-minute session for which the engine had odds.
- **Entry bar**: the Lead a side needs before the book enters by itself. Today it is 5 points on every market.
- **Real call**: an entry made because the Lead cleared the entry bar (entry word ENTER).
- **Forced entry**: after four flat sessions with no real call the book must enter, on the trend's side (FORCED).
- **Flip**: leaving a held side for the other side (FLIP).
- **R**: a trade's result after fees, divided by what it risked at its entry stop. +1R wins what was risked.
- **Worst fall**: the deepest drop of the paper book from an earlier high, in percent.
- **Segments**: h1 = up to 2023-06-07 (the bars are fitted here). h2 = 2023-06-08 to 2025-11-10.
  Holdout = 2025-11-11 to 2026-11-10. Forward = 2026-11-11 to the end of the data (2026-11-24 04:30 UTC).

## Verdict by the registered condition

**The PRIMARY rule (all bars scaled) DOES NOT PASS.**

| Leg (pooled over the six markets) | Current rule | All bars scaled | Met |
|---|---|---|---|
| 1. Sum of R higher in h2 | +18.3R | +2.1R | NO |
| 2. Sum of R higher in the holdout | +3.2R | +4.5R | yes |
| 3. In the new book in h2, real calls have a higher mean R than forced entries | | real calls -0.049R (142 trades), forced -0.000R (1271 trades) | NO |

A pass would lead only to a proposal for a forward paper shadow book. It would never change a live book or the vault.

## Step 1. Is the 5-point bar out of reach on history too?

Share of steps with |Lead| at or above 5 points, per segment. Then the |Lead| reached in half of all steps (p50),
and the levels passed in only 25%, 10%, 5% and 1% of steps (p75, p90, p95, p99), and the largest reading.

| Market | Segment | Steps | Share at 5+ | p50 | p75 | p90 | p95 | p99 | Largest |
|---|---|---|---|---|---|---|---|---|---|
| BTC | h1 | 116871 | 20.91% | 2.40 | 4.45 | 7.47 | 10.16 | 17.32 | 27.42 |
| BTC | h2 | 85152 | 13.37% | 1.90 | 3.53 | 5.68 | 7.27 | 11.14 | 22.64 |
| BTC | holdout | 35040 | 14.91% | 2.13 | 3.76 | 6.01 | 8.03 | 12.51 | 20.79 |
| BTC | forward | 1267 | 71.35% | 7.15 | 9.27 | 12.00 | 13.69 | 18.25 | 21.45 |
| ETH | h1 | 116871 | 21.08% | 2.41 | 4.47 | 7.54 | 10.33 | 18.28 | 29.08 |
| ETH | h2 | 85152 | 12.95% | 1.95 | 3.51 | 5.58 | 7.17 | 11.12 | 22.48 |
| ETH | holdout | 35040 | 15.05% | 2.14 | 3.77 | 6.28 | 8.42 | 13.35 | 20.97 |
| ETH | forward | 1267 | 76.40% | 7.43 | 9.13 | 11.52 | 13.59 | 17.61 | 19.95 |
| Gold | h1 | 77795 | 9.26% | 1.61 | 2.93 | 4.81 | 6.58 | 13.12 | 35.48 |
| Gold | h2 | 57458 | 0.98% | 0.94 | 1.61 | 2.42 | 3.17 | 4.98 | 9.70 |
| Gold | holdout | 23523 | 0.00% | 0.89 | 1.52 | 2.13 | 2.51 | 3.31 | 4.34 |
| Gold | forward | 805 | 0.00% | 0.93 | 2.51 | 3.23 | 3.60 | 4.34 | 4.53 |
| Silver | h1 | 77795 | 8.65% | 1.56 | 2.89 | 4.67 | 6.50 | 11.93 | 35.14 |
| Silver | h2 | 57458 | 0.95% | 0.93 | 1.60 | 2.42 | 3.10 | 4.94 | 9.61 |
| Silver | holdout | 23523 | 0.00% | 0.92 | 1.54 | 2.12 | 2.50 | 3.35 | 4.95 |
| Silver | forward | 805 | 0.00% | 1.23 | 2.65 | 3.48 | 3.97 | 4.40 | 4.70 |
| USDJPY | h1 | 79058 | 8.72% | 2.03 | 3.34 | 4.77 | 5.94 | 12.70 | 20.14 |
| USDJPY | h2 | 60452 | 0.74% | 1.51 | 2.43 | 3.27 | 3.80 | 4.82 | 7.93 |
| USDJPY | holdout | 24804 | 0.23% | 1.14 | 1.90 | 2.62 | 3.05 | 4.00 | 6.67 |
| USDJPY | forward | 833 | 0.00% | 1.09 | 1.97 | 2.85 | 3.36 | 3.83 | 4.11 |
| S&P 500 | h1 | 15693 | 1.91% | 1.31 | 2.21 | 3.36 | 4.06 | 5.42 | 7.51 |
| S&P 500 | h2 | 15758 | 0.01% | 0.86 | 1.48 | 2.13 | 2.57 | 3.36 | 5.71 |
| S&P 500 | holdout | 6502 | 0.00% | 0.66 | 1.17 | 1.73 | 2.14 | 3.11 | 3.52 |
| S&P 500 | forward | 234 | 0.00% | 0.66 | 1.12 | 1.73 | 2.02 | 2.29 | 3.62 |
| WTI | h1 | 70531 | 28.83% | 2.72 | 5.74 | 12.55 | 17.10 | 26.15 | 39.22 |
| WTI | h2 | 52311 | 13.72% | 1.66 | 2.98 | 7.33 | 13.55 | 18.85 | 27.50 |
| WTI | holdout | 21383 | 22.71% | 2.13 | 4.08 | 11.84 | 13.73 | 16.09 | 18.92 |
| WTI | forward | 719 | 0.00% | 1.29 | 2.14 | 3.05 | 3.52 | 3.86 | 4.30 |
| Brent | h1 | 70531 | 29.26% | 2.77 | 5.87 | 12.28 | 16.85 | 27.48 | 39.81 |
| Brent | h2 | 52311 | 14.33% | 1.71 | 3.17 | 7.57 | 13.47 | 18.25 | 24.71 |
| Brent | holdout | 21383 | 22.59% | 2.11 | 4.17 | 11.86 | 13.78 | 16.21 | 20.36 |
| Brent | forward | 719 | 0.00% | 1.22 | 2.01 | 2.77 | 3.08 | 4.03 | 4.61 |

Live, 10 to 24 Nov 2026 (from the audit, already known): the largest reading was gold 4.6, silver 4.7, USDJPY 5.0,
S&P 3.5, WTI 4.2, Brent 4.5. The replay's forward rows above cover nearly the same days.

### The current Setups book's entries, by how they were made

One continuous book per market, as the engine runs it. Each cell: real calls / forced / flips (share that are real calls).

| Market | h1 | h2 | holdout | forward |
|---|---|---|---|---|
| BTC | 200 / 230 / 39 (43%) | 137 / 255 / 19 (33%) | 48 / 127 / 1 (27%) | 5 / 2 / 0 (71%) |
| ETH | 189 / 289 / 44 (36%) | 124 / 231 / 12 (34%) | 39 / 78 / 3 (32%) | 4 / 0 / 0 (100%) |
| Gold | 36 / 343 / 33 (9%) | 5 / 236 / 3 (2%) | 0 / 90 / 0 (0%) | 0 / 6 / 0 (0%) |
| Silver | 24 / 319 / 21 (7%) | 2 / 238 / 6 (1%) | 0 / 110 / 1 (0%) | 0 / 4 / 0 (0%) |
| USDJPY | 58 / 268 / 12 (17%) | 6 / 282 / 11 (2%) | 1 / 81 / 0 (1%) | 0 / 4 / 0 (0%) |
| S&P 500 | 5 / 88 / 2 (5%) | 0 / 102 / 3 (0%) | 0 / 38 / 1 (0%) | 0 / 2 / 0 (0%) |
| WTI | 109 / 257 / 27 (28%) | 50 / 199 / 12 (19%) | 17 / 59 / 2 (22%) | - |
| Brent | 92 / 237 / 31 (26%) | 45 / 231 / 8 (16%) | 16 / 61 / 1 (21%) | - |
| **BTC + ETH** | 389 / 519 / 83 (39%) | 261 / 486 / 31 (34%) | 87 / 205 / 4 (29%) | 9 / 2 / 0 (82%) |
| **The six** | 324 / 1512 / 126 (17%) | 108 / 1288 / 43 (8%) | 34 / 439 / 5 (7%) | 0 / 16 / 0 (0%) |

The same book's result by entry word, pooled (trades, mean R, sum of R). Descriptive.

| Markets | Segment | Real calls | Forced | Flips |
|---|---|---|---|---|
| BTC + ETH | h1 | 389, +0.028R, +10.8R | 519, +0.044R, +22.9R | 83, +0.134R, +11.1R |
| BTC + ETH | h2 | 261, -0.064R, -16.7R | 486, -0.099R, -47.9R | 31, -0.004R, -0.1R |
| BTC + ETH | holdout | 87, -0.115R, -10.0R | 205, +0.060R, +12.3R | 4, +1.143R, +4.6R |
| BTC + ETH | forward | 9, -0.077R, -0.7R | 2, +2.001R, +4.0R | 0, -, +0.0R |
| The six | h1 | 324, +0.026R, +8.6R | 1512, -0.025R, -38.1R | 126, +0.114R, +14.4R |
| The six | h2 | 108, +0.018R, +2.0R | 1288, +0.029R, +37.7R | 43, -0.070R, -3.0R |
| The six | holdout | 34, -0.017R, -0.6R | 439, -0.000R, -0.1R | 5, +0.379R, +1.9R |
| The six | forward | 0, -, +0.0R | 16, +0.653R, +10.4R | 0, -, +0.0R |

## Step 2. The fitted bars (h1 only)

On BTC and ETH together, |Lead| was at or above 5 points in **21.00%** of h1 steps (233742 steps).
Each market's bar is the |Lead| it reached in that same share of its own h1 steps (never below 1.00 point).
The other bars move by the same factor: the high-risk entry bar (10 points today), the flip bar (10) and the bar
for an entry against the higher-timeframe trend (15).

| Market | Fitted entry bar | Factor | High-risk bar | Flip bar | Counter-trend bar | Share of steps at or above the fitted bar: h1 / h2 / holdout / forward |
|---|---|---|---|---|---|---|
| Gold | 3.25 | 0.650 | 6.50 | 6.50 | 9.75 | 21.0% / 4.6% / 1.1% / 9.6% |
| Silver | 3.20 | 0.640 | 6.40 | 6.40 | 9.60 | 21.0% / 4.5% / 1.3% / 15.4% |
| USDJPY | 3.63 | 0.726 | 7.26 | 7.26 | 10.89 | 21.0% / 6.3% / 1.9% / 2.6% |
| S&P 500 | 2.43 | 0.486 | 4.86 | 4.86 | 7.29 | 21.0% / 6.3% / 3.4% / 0.9% |
| WTI | 6.74 | 1.348 | 13.48 | 13.48 | 20.22 | 21.0% / 10.4% / 19.9% / 0.0% |
| Brent | 6.96 | 1.392 | 13.92 | 13.92 | 20.88 | 21.0% / 10.6% / 19.2% / 0.0% |

For comparison, the share of steps at 5+ points on crypto: BTC 20.9% / 13.4% / 14.9% / 71.3%; ETH 21.1% / 13.0% / 15.1% / 76.4% (h1 / h2 / holdout / forward).

## Step 2. The replay, pooled over the six markets

Each book starts flat with $10,000 per market at the start of its segment. h1 is not compared: the bars were fitted there.
Each cell: trades, share that are real calls, share won, sum of R, mean R, net dollars (six books), worst fall (six books summed).

| Rule | h2 | holdout | forward |
|---|---|---|---|
| current rule | 1446, 7%, 42%, +18.3R, +0.013R, +332, -21.1% | 486, 7%, 42%, +3.2R, +0.007R, -11579, -34.4% | 23, 0%, 61%, +12.6R, +0.546R, +4176, -2.1% |
| all bars scaled (PRIMARY) | 1463, 10%, 42%, +2.1R, +0.001R, -2693, -25.4% | 483, 8%, 42%, +4.5R, +0.009R, -11834, -33.9% | 23, 9%, 61%, +12.7R, +0.553R, +4181, -2.2% |
| entry bar only (secondary) | 1468, 10%, 42%, -2.7R, -0.002R, -4087, -25.4% | 482, 8%, 42%, +5.9R, +0.012R, -10740, -32.4% | 23, 9%, 61%, +12.7R, +0.553R, +4181, -2.2% |

By entry word (trades, mean R, sum of R):

| Rule | Segment | Real calls | Forced | Flips |
|---|---|---|---|---|
| current rule | h2 | 108, +0.018R, +2.0R | 1295, +0.015R, +19.3R | 43, -0.070R, -3.0R |
| current rule | holdout | 34, -0.017R, -0.6R | 447, +0.004R, +1.9R | 5, +0.379R, +1.9R |
| current rule | forward | 0, -, +0.0R | 23, +0.546R, +12.6R | 0, -, +0.0R |
| all bars scaled (PRIMARY) | h2 | 142, -0.049R, -7.0R | 1271, -0.000R, -0.3R | 50, +0.188R, +9.4R |
| all bars scaled (PRIMARY) | holdout | 40, -0.083R, -3.3R | 438, +0.014R, +5.9R | 5, +0.379R, +1.9R |
| all bars scaled (PRIMARY) | forward | 2, +1.678R, +3.4R | 21, +0.446R, +9.4R | 0, -, +0.0R |
| entry bar only (secondary) | h2 | 148, -0.079R, -11.7R | 1271, +0.001R, +1.9R | 49, +0.144R, +7.1R |
| entry bar only (secondary) | holdout | 38, -0.040R, -1.5R | 439, +0.012R, +5.5R | 5, +0.379R, +1.9R |
| entry bar only (secondary) | forward | 2, +1.678R, +3.4R | 21, +0.446R, +9.4R | 0, -, +0.0R |

### How much of the difference could be noise (descriptive, not part of the verdict)

Difference in sum of R against the current rule. The range comes from redrawing the calendar months 10,000 times.
A range that spans zero means the difference cannot be told from chance on this history.

| Rule | Segment | Months | Difference | 95% range | Share of redraws above zero |
|---|---|---|---|---|---|
| all bars scaled (PRIMARY) | h2 | 30 | -16.1R | -54.6 to +19.4 | 19% |
| all bars scaled (PRIMARY) | holdout | 13 | +1.3R | -8.8 to +9.8 | 64% |
| entry bar only (secondary) | h2 | 30 | -21.0R | -61.2 to +16.5 | 14% |
| entry bar only (secondary) | holdout | 13 | +2.7R | -8.3 to +12.1 | 73% |

## Per market

Each cell: trades, share that are real calls, share won, sum of R, mean R, net dollars, worst fall.

| Market | Rule | h2 | holdout | forward |
|---|---|---|---|---|
| Gold | current rule | 247, 2%, 45%, +27.5R, +0.111R, +5368, -31.3% | 86, 0%, 43%, +9.5R, +0.110R, -247, -37.8% | 7, 0%, 71%, +5.6R, +0.802R, +1194, -5.5% |
| Gold | all bars scaled (PRIMARY) | 250, 5%, 46%, +26.5R, +0.106R, +5011, -35.1% | 86, 1%, 43%, +9.5R, +0.110R, -247, -37.8% | 7, 14%, 71%, +5.6R, +0.802R, +1196, -6.1% |
| Gold | entry bar only (secondary) | 252, 5%, 45%, +21.9R, +0.087R, +3702, -35.1% | 86, 1%, 43%, +9.5R, +0.110R, -247, -37.8% | 7, 14%, 71%, +5.6R, +0.802R, +1196, -6.1% |
| Silver | current rule | 248, 1%, 42%, -1.7R, -0.007R, -2000, -35.3% | 110, 0%, 45%, +8.0R, +0.073R, -3783, -72.7% | 5, 0%, 80%, +6.1R, +1.217R, +1601, -7.7% |
| Silver | all bars scaled (PRIMARY) | 262, 6%, 42%, -7.0R, -0.027R, -2849, -46.6% | 110, 4%, 45%, +7.8R, +0.071R, -3829, -72.8% | 5, 20%, 80%, +6.2R, +1.246R, +1604, -7.7% |
| Silver | entry bar only (secondary) | 262, 6%, 41%, -8.4R, -0.032R, -3047, -46.6% | 110, 4%, 45%, +7.8R, +0.071R, -3829, -72.8% | 5, 20%, 80%, +6.2R, +1.246R, +1604, -7.7% |
| USDJPY | current rule | 299, 2%, 44%, +21.3R, +0.071R, +3917, -42.4% | 84, 1%, 40%, -8.8R, -0.105R, -1553, -28.1% | 6, 0%, 50%, -1.0R, -0.169R, -194, -7.4% |
| USDJPY | all bars scaled (PRIMARY) | 319, 15%, 40%, -5.6R, -0.017R, -1866, -45.1% | 79, 4%, 42%, -6.5R, -0.082R, -1133, -24.5% | 6, 0%, 50%, -1.0R, -0.169R, -194, -7.4% |
| USDJPY | entry bar only (secondary) | 319, 15%, 40%, -5.6R, -0.017R, -1866, -45.1% | 79, 4%, 42%, -6.5R, -0.082R, -1133, -24.5% | 6, 0%, 50%, -1.0R, -0.169R, -194, -7.4% |
| S&P 500 | current rule | 106, 0%, 47%, +18.5R, +0.175R, +2809, -22.1% | 37, 0%, 38%, -4.4R, -0.118R, -1036, -13.4% | 2, 0%, 50%, +1.8R, +0.900R, +346, -4.6% |
| S&P 500 | all bars scaled (PRIMARY) | 100, 8%, 50%, +29.5R, +0.295R, +5952, -22.1% | 37, 3%, 41%, -0.8R, -0.022R, -373, -12.8% | 2, 0%, 50%, +1.8R, +0.900R, +346, -4.6% |
| S&P 500 | entry bar only (secondary) | 100, 9%, 50%, +29.7R, +0.297R, +6023, -22.1% | 37, 3%, 41%, -0.8R, -0.022R, -373, -12.8% | 2, 0%, 50%, +1.8R, +0.900R, +346, -4.6% |
| WTI | current rule | 262, 19%, 38%, -21.4R, -0.082R, -4802, -55.2% | 87, 20%, 39%, -4.4R, -0.051R, -3355, -59.2% | 1, 0%, 0%, -1.0R, -1.028R, +602, -4.8% |
| WTI | all bars scaled (PRIMARY) | 254, 11%, 39%, -14.3R, -0.056R, -3967, -52.6% | 89, 18%, 37%, -9.2R, -0.103R, -4699, -64.7% | 1, 0%, 0%, -1.0R, -1.028R, +602, -4.8% |
| WTI | entry bar only (secondary) | 252, 12%, 39%, -13.6R, -0.054R, -3852, -51.7% | 88, 16%, 38%, -7.8R, -0.089R, -3602, -59.2% | 1, 0%, 0%, -1.0R, -1.028R, +602, -4.8% |
| Brent | current rule | 284, 16%, 40%, -26.1R, -0.092R, -4960, -61.8% | 82, 20%, 43%, +3.3R, +0.040R, -1604, -52.6% | 2, 0%, 50%, +1.1R, +0.558R, +628, -5.3% |
| Brent | all bars scaled (PRIMARY) | 278, 10%, 39%, -27.0R, -0.097R, -4975, -61.7% | 82, 18%, 43%, +3.6R, +0.044R, -1552, -52.3% | 2, 0%, 50%, +1.1R, +0.558R, +628, -5.3% |
| Brent | entry bar only (secondary) | 283, 11%, 40%, -26.8R, -0.095R, -5049, -61.1% | 82, 18%, 43%, +3.6R, +0.044R, -1554, -52.3% | 2, 0%, 50%, +1.1R, +0.558R, +628, -5.3% |

## Limits

- This is a replay on history. It cannot prove that any rule has an edge.
- The six markets share days and trends. Their trades are not independent, so the totals rest on fewer separate bets than the counts suggest.
- The holdout was already read by earlier studies of this book (H65, H67, H68, H72). It is not a sealed test.
- The forward segment is about two weeks. Its numbers are too few to mean anything.
- The bar is fitted from how often the Lead is large, not from whether large Leads were right.
- The replay's odds come from the engine's own walk of weekly refits. Most were read from the cache. The last year's fits for BTC, ETH
  and USDJPY were not in it and were refitted on the laptop by the same code. The odds can differ a little from what
  the live engine printed.
- Each compared book starts fresh at its segment. A book carried over from 2020 would differ slightly at the joins.
- Fees are the engine's paper fees. Funding and slippage are not charged.

## Extra look, NOT registered, made after the results: the 5-point bar year by year

Share of steps with |Lead| at or above 5 points in each calendar year, and the last step that reached it.
Descriptive only. It changes no verdict.

| Market | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Last step at 5+ (UTC) |
|---|---|---|---|---|---|---|---|---|
| Gold | 20.6% | 10.5% | 2.2% | 1.1% | 0.4% | 0.8% | 0.0% | 2025-04-22 07:00 |
| Silver | 18.2% | 10.4% | 2.4% | 1.1% | 0.5% | 0.7% | 0.0% | 2025-09-25 22:15 |
| USDJPY | 7.3% | 14.7% | 4.4% | 3.7% | 0.5% | 0.8% | 0.2% | 2026-11-05 07:15 |
| S&P 500 | - | 3.8% | 0.9% | 0.0% | 0.0% | 0.0% | 0.0% | 2023-09-27 15:45 |
| WTI | 50.7% | 30.3% | 17.5% | 17.9% | 10.5% | 8.8% | 25.3% | 2026-11-03 11:15 |
| Brent | 51.3% | 32.0% | 16.9% | 19.3% | 10.3% | 9.0% | 25.2% | 2026-11-02 13:15 |

Oil in 2026, month by month:

| Market | 2026-01 | 2026-02 | 2026-03 | 2026-04 | 2026-05 | 2026-06 | 2026-07 | 2026-08 | 2026-09 | 2026-10 | 2026-11 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| WTI | 30.7% | 63.1% | 53.5% | 49.4% | 14.3% | 0.0% | 0.1% | 26.8% | 2.2% | 32.3% | 3.6% |
| Brent | 32.8% | 63.2% | 55.2% | 49.3% | 13.1% | 0.3% | 0.0% | 22.5% | 1.8% | 32.3% | 3.8% |

## Reading (written by hand after the run)

**1. Is the 5-point bar out of reach on history too? On four markets yes, but only since about 2023. On oil, no.**

- Gold, silver, USDJPY and the S&P 500: in 2020 and 2021 the Lead reached 5 points quite often (gold in 21% and 11%
  of steps). It has shrunk every year since. From mid-2023 it reached 5 points in under 1% of steps, and in the last
  year almost never. Gold last reached it on 22 Apr 2025, silver on 25 Sep 2025, the S&P on 27 Sep 2023.
- So on these four markets the Setups book already entered by force nearly every time on history: from mid-2023 on,
  real calls were 0% to 2% of its entries. The live finding matches the history.
- Oil is different. On WTI and Brent the Lead reached 5 points in 29% of steps up to mid-2023. That is more often
  than on BTC and ETH (21%). It still did in 14% of steps in h2 and in 23% of steps in the holdout year. It comes in
  bursts: 63% of steps in Feb 2026, none in Jun 2026, 32% in Oct 2026. The last time was 2 to 3 Nov 2026. The 14 live
  days fell in a quiet spell. For oil the bar is not out of reach.

**2. The fitted bars.** Gold 3.25 points, silver 3.20, USDJPY 3.63, S&P 2.43. For oil the same rule RAISED the bar:
WTI 6.74, Brent 6.96. So the study tested a lower bar on four markets and a higher one on two.

**3. The fitted bars did not do what they were meant to do after 2023.** The bar was set so that it is cleared in 21%
of steps, as on crypto. That held only where it was fitted. Because the Lead keeps shrinking on the four markets, the
new bars were cleared in about 5% to 6% of steps in h2 and 1% to 3% in the holdout. Real calls rose only from 7% to
10% of entries in h2. About nine trades in ten were still forced entries. A bar fitted once does not keep up with a
Lead that drifts.

**4. The result.** The primary rule does not pass. It fails two of the three legs.

- h2: the six books made +2.1R with the scaled bars against +18.3R with the current rule (16.1R less). The noise check
  gives a range of -54.6R to +19.4R for that gap, so it cannot be told from chance, in either direction.
- Holdout: +4.5R against +3.2R (1.3R more; range -8.8R to +9.8R). Nominally higher, and not distinguishable from zero.
- Real calls against forced entries in the new book in h2: real calls lost a little (-0.049R a trade over 142 trades),
  forced entries were flat (-0.000R over 1,271). Real calls were not the better trades.
- The secondary rule (only the entry bar scaled) reads the same: -2.7R in h2, +5.9R in the holdout.

**5. By market (h2).** USDJPY carries most of the gap: +21.3R with the current rule, -5.6R with the lower bar. Silver
was 5R worse. Gold and Brent hardly moved. The S&P was better (+29.5R against +18.5R, on 100 trades). WTI with its
higher bar was 7R better in h2 and 5R worse in the holdout. No market shows the same sign in a convincing way across
both segments, and with one market up and another down by chance this is what noise looks like.

**6. What this says and does not say.** It agrees with the earlier studies: more entries on the Lead's own call did
not pay better than forced entries on this history (H65), and the book's odds and entry bar could not be told from
placebos (H80, H82b). Nothing here supports lowering the bar on the six markets. It also does not show that a lower
bar is harmful: the gaps are inside the noise. It is a replay, so it proves nothing about the future either way.

**7. Dollars and R can disagree.** In the holdout the six books are up a few R and down about $11,600. R counts
every trade the same. Dollars weigh a trade by how much it risked, and a position is never smaller than 1x, so trades
with a far stop cost more than the planned 2% (the audit's finding 5). Silver's holdout book shows it most: +8.0R,
-$3,783, with a worst fall of 73%. The reason given here is the likely one; it was not checked trade by trade.

**8. If the owner still wants real calls on these markets.** A bar fitted once is the wrong tool, because the Lead's
size drifts. A bar that follows the recent Lead (for example the level cleared in 21% of the last 90 days' steps)
would be a different rule and would need its own registration. The prior expectation for it is also low, for the same
reasons. A more useful question may be why the Lead on gold, silver, USDJPY and the S&P has shrunk towards zero since
2022: the odds there are now close to even at almost every step. That was not studied here.

**Not verified.**
- The fits for the last year of BTC, ETH and USDJPY were not in the cache (54 and 38 weekly refits). They were refitted
  on the laptop by the engine's own code. They were not compared with the fits the live box holds.
- The replay's largest forward readings sit close to the live audit's on five of six markets (gold 4.53 against 4.6,
  silver 4.70 against 4.7, S&P 3.62 against 3.5, WTI 4.30 against 4.2, Brent 4.61 against 4.5). USDJPY differs (4.11
  against 5.0). The audit's window starts a day earlier (10 Nov); whether that explains it was not checked.
- The current rule's h2 numbers per market equal the earlier H92 study's table exactly (trades and sum of R, all six
  markets). That is an independent check of the loader and the book for h2. There is no such check for the holdout.
- Only this study's own tests were run (10 tests). The full test suite was not run; no engine file was changed.
