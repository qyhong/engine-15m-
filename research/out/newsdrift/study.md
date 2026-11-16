# H50: post-news drift

PAPER RESEARCH ONLY. Registered 2026-11-16 09:48 UTC (`research/hypotheses_pending/H50.md`) before any code or number. Development data only (rows before 2025-11-11 00:00 UTC; the holdout was not read). Releases with entry from 2020-01-01; first half before 2023-06-07. Written 2026-11-16 09:52 UTC.

Releases: CPI, NFP, FOMC, PCE, advance GDP from `engine15/calhistory.py` (official dates, agency release times; same-minute rows = one release, typed FOMC > CPI > NFP > PCE > GDP). Impulse I = (close of the k-th 15m bar from the release - the last close before it) / daily ATR. Hit = +0.5 daily ATR in the trade's favour before -0.5 against, from the next 15m open, within the release's UTC day (a bar touching both = miss; neither = unresolved, excluded). p = exact two-sided binomial against 50%. Tests: 8 variants x 2 outcomes = **16** per half; Bonferroni p < 3.13e-03. Rows = release x market pairs; one release moves all markets together, so the pooled p overstates the evidence (see the release-level check).

## Verdict: NO PASS

## Releases used

| type | in calendar 1st / 2nd | k=1: releases with a row 1st / 2nd | rows 1st / 2nd | k=4: releases 1st / 2nd | rows 1st / 2nd |
|---|---|---|---|---|---|
| FOMC | 28 / 20 | 28 / 20 | 217 / 160 | 28 / 20 | 215 / 159 |
| CPI | 41 / 29 | 41 / 29 | 283 / 202 | 41 / 29 | 281 / 203 |
| NFP | 42 / 27 | 42 / 27 | 286 / 188 | 42 / 27 | 286 / 189 |
| PCE | 41 / 28 | 41 / 28 | 284 / 192 | 41 / 28 | 286 / 192 |
| GDP | 14 / 8 | 14 / 8 | 98 / 56 | 14 / 8 | 98 / 56 |

## The variants

| id | rule |
|---|---|
| N1 | impulse over the first 15 min, abs >= 0.25 daily ATR, trade WITH it at the next 15m open |
| N2 | impulse over the first 15 min, abs >= 0.50 daily ATR, trade WITH it at the next 15m open |
| N3 | impulse over the first 60 min, abs >= 0.50 daily ATR, trade WITH it at the next 15m open |
| N4 | impulse over the first 60 min, abs >= 1.00 daily ATR, trade WITH it at the next 15m open |
| F1 | impulse over the first 15 min, abs >= 0.25 daily ATR, trade AGAINST (fade) it at the next 15m open |
| F2 | impulse over the first 15 min, abs >= 0.50 daily ATR, trade AGAINST (fade) it at the next 15m open |
| F3 | impulse over the first 60 min, abs >= 0.50 daily ATR, trade AGAINST (fade) it at the next 15m open |
| F4 | impulse over the first 60 min, abs >= 1.00 daily ATR, trade AGAINST (fade) it at the next 15m open |

## Pooled hit rates (primary: rest of the UTC day; secondary: 24 h)

| id | first: hit | resolved | p | second: hit | resolved | p | 24 h first | p | 24 h second | p | both barriers in one bar |
|---|---|---|---|---|---|---|---|---|---|---|---|
| N1 | 46.8% | 203 (61 unres.) | 0.400 | 55.6% | 133 (35 unres.) | 0.225 | 49.5% (222) | 0.947 | 54.7% (150) | 0.288 | 0.2% |
| N2 | 50.0% | 96 (19 unres.) | 1.000 | 57.1% | 49 (14 unres.) | 0.392 | 51.5% (103) | 0.844 | 56.4% (55) | 0.419 | 0.6% |
| N3 | 52.4% | 105 (54 unres.) | 0.696 | 59.4% | 64 (42 unres.) | 0.169 | 55.5% (137) | 0.232 | 55.1% (89) | 0.397 | 0.4% |
| N4 | 61.5% | 26 (5 unres.) | 0.327 | 79.0% | 19 (8 unres.) | 0.019 | 62.1% (29) | 0.265 | 77.3% (22) | 0.017 | 1.7% |
| F1 | 53.2% | 203 (61 unres.) | 0.400 | 43.6% | 133 (35 unres.) | 0.165 | 50.5% (222) | 0.947 | 44.7% (150) | 0.221 | 0.2% |
| F2 | 50.0% | 96 (19 unres.) | 1.000 | 40.8% | 49 (14 unres.) | 0.253 | 48.5% (103) | 0.844 | 41.8% (55) | 0.281 | 0.6% |
| F3 | 47.6% | 105 (54 unres.) | 0.696 | 39.1% | 64 (42 unres.) | 0.103 | 44.5% (137) | 0.232 | 43.8% (89) | 0.289 | 0.4% |
| F4 | 38.5% | 26 (5 unres.) | 0.327 | 15.8% | 19 (8 unres.) | 0.004 | 37.9% (29) | 0.265 | 18.2% (22) | 0.004 | 1.7% |

## Release-level check (each release counted once; descriptive, not a test)

| id | first: releases | decided | hit % | p | second: releases | decided | hit % | p |
|---|---|---|---|---|---|---|---|---|
| N1 | 75 | 70 | 55.7 | 0.403 | 58 | 51 | 52.9 | 0.780 |
| N2 | 42 | 39 | 53.9 | 0.749 | 28 | 27 | 40.7 | 0.442 |
| N3 | 58 | 55 | 56.4 | 0.419 | 35 | 29 | 65.5 | 0.136 |
| N4 | 16 | 14 | 57.1 | 0.791 | 12 | 10 | 80.0 | 0.109 |
| F1 | 75 | 70 | 44.3 | 0.403 | 58 | 50 | 46.0 | 0.672 |
| F2 | 42 | 39 | 46.1 | 0.749 | 28 | 27 | 55.6 | 0.701 |
| F3 | 58 | 55 | 43.6 | 0.419 | 35 | 30 | 33.3 | 0.099 |
| F4 | 16 | 14 | 42.9 | 0.791 | 12 | 11 | 18.2 | 0.065 |

## The registered trade, pooled (the +/- 0.5 dATR bracket, out at the day's last close; own fee a side)

| id | half | trades | won | R before | R after | PF | per trade (% stake) | net $ |
|---|---|---|---|---|---|---|---|---|
| N1 | first | 264 | 47.3% | -0.031 | -0.095 | 0.70 | -0.1949% | -5,146 |
|  | second | 165 | 53.3% | +0.087 | +0.018 | 1.02 | +0.0069% | +113 |
| N2 | first | 115 | 49.6% | +0.006 | -0.057 | 0.84 | -0.0924% | -1,062 |
|  | second | 63 | 58.7% | +0.144 | +0.075 | 1.19 | +0.0469% | +296 |
| N3 | first | 159 | 51.6% | +0.055 | -0.011 | 0.68 | -0.1823% | -2,899 |
|  | second | 105 | 56.2% | +0.140 | +0.073 | 1.42 | +0.1157% | +1,215 |
| N4 | first | 31 | 64.5% | +0.235 | +0.174 | 0.91 | -0.0459% | -142 |
|  | second | 27 | 70.4% | +0.395 | +0.324 | 2.37 | +0.1931% | +521 |
| F1 | first | 264 | 50.4% | +0.031 | -0.033 | 1.07 | +0.0359% | +947 |
|  | second | 165 | 43.6% | -0.099 | -0.168 | 0.71 | -0.1377% | -2,272 |
| F2 | first | 115 | 50.4% | -0.006 | -0.069 | 0.92 | -0.0457% | -526 |
|  | second | 63 | 34.9% | -0.176 | -0.244 | 0.59 | -0.1419% | -894 |
| F3 | first | 159 | 44.7% | -0.055 | -0.121 | 1.06 | +0.0276% | +440 |
|  | second | 105 | 40.0% | -0.159 | -0.227 | 0.49 | -0.2337% | -2,453 |
| F4 | first | 31 | 32.3% | -0.235 | -0.296 | 0.82 | -0.1020% | -316 |
|  | second | 27 | 22.2% | -0.469 | -0.541 | 0.28 | -0.2887% | -780 |

## Pass bar, every variant

| id | hit >= 55% both | >= 100 resolved both | p < alpha both | trade 2nd half pooled net > 0 | markets net > 0 (2nd half) | PASS |
|---|---|---|---|---|---|---|
| N1 | no | yes | no | yes | 5 (BTCUSDT, ETHUSDT, XAGUSD, SPX, BRENT) | **no** |
| N2 | no | no | no | yes | 3 (XAUUSD, XAGUSD, SPX) | **no** |
| N3 | no | no | no | yes | 6 (BTCUSDT, ETHUSDT, XAUUSD, USDJPY, WTI, BRENT) | **no** |
| N4 | yes | no | no | yes | 3 (XAUUSD, XAGUSD, USDJPY) | **no** |
| F1 | no | yes | no | no | 1 (WTI) | **no** |
| F2 | no | no | no | no | 1 (BTCUSDT) | **no** |
| F3 | no | no | no | no | 1 (SPX) | **no** |
| F4 | no | no | no | no | 0 (-) | **no** |

Outcome cells whose pooled p passes Bonferroni in BOTH halves (either side of 50%): 0 of 16.

## Impulse size vs drift, k = 1 (15 min), every release-market row, no threshold

Drift = move from the entry open (next 15m open after the window) to the day's last close / the 24 h close, in the impulse's direction, daily-ATR units. WITH hit = the primary bracket traded with the impulse.

| abs(I) in daily ATR | half | rows | mean drift day | median drift day | mean drift 24 h | drift > 0 | WITH hit | resolved | p |
|---|---|---|---|---|---|---|---|---|---|
| 0.00-0.10 | first | 565 | -0.001 | -0.013 | +0.011 | 48.3% | 49.6% | 266 | 0.951 |
|  | second | 344 | +0.056 | +0.055 | -0.018 | 54.1% | 58.5% | 193 | 0.021 |
| 0.10-0.25 | first | 339 | -0.053 | -0.048 | -0.087 | 43.1% | 41.2% | 194 | 0.018 |
|  | second | 286 | -0.037 | -0.003 | -0.063 | 50.0% | 52.4% | 189 | 0.561 |
| 0.25-0.50 | first | 149 | -0.017 | -0.036 | +0.083 | 46.3% | 43.9% | 107 | 0.246 |
|  | second | 105 | +0.040 | +0.026 | -0.026 | 51.4% | 54.8% | 84 | 0.445 |
| 0.50-1.00 | first | 99 | -0.015 | -0.039 | +0.107 | 47.5% | 44.4% | 81 | 0.374 |
|  | second | 53 | +0.190 | +0.133 | +0.197 | 62.3% | 56.1% | 41 | 0.533 |
| 1.00-up | first | 16 | +0.413 | +0.427 | +0.606 | 68.8% | 80.0% | 15 | 0.035 |
|  | second | 10 | +0.686 | +0.524 | +0.226 | 80.0% | 62.5% | 8 | 0.727 |

Same rows by abs(I) in ATR15 units (ATR15 of the bar before the release):

| abs(I) in ATR15 | half | rows | mean drift day (dATR) | mean drift 24 h | drift > 0 | WITH hit | resolved |
|---|---|---|---|---|---|---|---|
| 0-2 | first | 818 | -0.016 | -0.012 | 46.5% | 45.7% | 420 |
|  | second | 556 | +0.022 | -0.028 | 52.5% | 56.1% | 330 |
| 2-4 | first | 186 | -0.040 | -0.024 | 45.2% | 44.0% | 116 |
|  | second | 142 | +0.040 | -0.027 | 52.8% | 56.5% | 108 |
| 4-8 | first | 123 | +0.021 | +0.121 | 52.0% | 47.9% | 94 |
|  | second | 66 | +0.017 | -0.079 | 48.5% | 46.0% | 50 |
| 8-up | first | 41 | +0.040 | +0.212 | 43.9% | 57.6% | 33 |
|  | second | 34 | +0.318 | +0.309 | 73.5% | 63.0% | 27 |

By release type (k = 1, every row, no threshold):

| type | half | releases | rows | median abs(I) dATR | mean drift day | WITH hit | resolved |
|---|---|---|---|---|---|---|---|
| FOMC | first | 28 | 217 | 0.117 | -0.011 | 47.9% | 117 |
|  | second | 20 | 160 | 0.126 | +0.151 | 65.5% | 87 |
| CPI | first | 41 | 283 | 0.149 | -0.004 | 44.8% | 183 |
|  | second | 29 | 202 | 0.140 | +0.107 | 57.3% | 143 |
| NFP | first | 42 | 286 | 0.151 | -0.010 | 43.8% | 153 |
|  | second | 27 | 188 | 0.145 | -0.105 | 42.7% | 143 |
| PCE | first | 41 | 284 | 0.070 | -0.039 | 47.3% | 148 |
|  | second | 28 | 192 | 0.077 | -0.006 | 56.2% | 112 |
| GDP | first | 14 | 98 | 0.086 | +0.015 | 51.6% | 62 |
|  | second | 8 | 56 | 0.101 | +0.090 | 76.7% | 30 |

## Impulse size vs drift, k = 4 (60 min), every release-market row, no threshold

Drift = move from the entry open (next 15m open after the window) to the day's last close / the 24 h close, in the impulse's direction, daily-ATR units. WITH hit = the primary bracket traded with the impulse.

| abs(I) in daily ATR | half | rows | mean drift day | median drift day | mean drift 24 h | drift > 0 | WITH hit | resolved | p |
|---|---|---|---|---|---|---|---|---|---|
| 0.00-0.10 | first | 383 | -0.093 | -0.040 | -0.114 | 45.2% | 33.8% | 157 | 5.74e-05 |
|  | second | 250 | +0.002 | -0.002 | -0.043 | 50.0% | 50.4% | 119 | 1.000 |
| 0.10-0.25 | first | 389 | -0.007 | -0.017 | +0.003 | 48.1% | 45.8% | 168 | 0.316 |
|  | second | 257 | -0.010 | +0.012 | +0.009 | 52.1% | 51.5% | 136 | 0.797 |
| 0.25-0.50 | first | 235 | +0.009 | +0.025 | +0.070 | 53.2% | 45.8% | 118 | 0.407 |
|  | second | 186 | +0.036 | +0.040 | -0.010 | 53.8% | 56.7% | 120 | 0.171 |
| 0.50-1.00 | first | 128 | -0.032 | +0.014 | +0.048 | 50.8% | 49.4% | 79 | 1.000 |
|  | second | 79 | +0.035 | +0.052 | +0.027 | 54.4% | 51.1% | 45 | 1.000 |
| 1.00-up | first | 31 | +0.142 | +0.139 | +0.292 | 61.3% | 61.5% | 26 | 0.327 |
|  | second | 27 | +0.315 | +0.364 | +0.269 | 77.8% | 79.0% | 19 | 0.019 |

Same rows by abs(I) in ATR15 units (ATR15 of the bar before the release):

| abs(I) in ATR15 | half | rows | mean drift day (dATR) | mean drift 24 h | drift > 0 | WITH hit | resolved |
|---|---|---|---|---|---|---|---|
| 0-2 | first | 666 | -0.046 | -0.067 | 46.8% | 41.9% | 284 |
|  | second | 410 | +0.011 | -0.006 | 51.2% | 52.8% | 197 |
| 2-4 | first | 263 | -0.012 | +0.057 | 49.0% | 39.8% | 128 |
|  | second | 226 | +0.023 | -0.010 | 54.4% | 55.4% | 148 |
| 4-8 | first | 171 | +0.001 | +0.068 | 56.7% | 50.5% | 91 |
|  | second | 114 | -0.028 | -0.037 | 50.0% | 46.8% | 62 |
| 8-up | first | 66 | -0.033 | +0.113 | 47.0% | 51.1% | 45 |
|  | second | 49 | +0.192 | +0.163 | 67.3% | 65.6% | 32 |

By release type (k = 4, every row, no threshold):

| type | half | releases | rows | median abs(I) dATR | mean drift day | WITH hit | resolved |
|---|---|---|---|---|---|---|---|
| FOMC | first | 28 | 215 | 0.198 | +0.023 | 56.1% | 66 |
|  | second | 20 | 159 | 0.218 | +0.105 | 60.7% | 56 |
| CPI | first | 41 | 281 | 0.197 | -0.017 | 35.6% | 146 |
|  | second | 29 | 203 | 0.215 | +0.050 | 57.4% | 129 |
| NFP | first | 42 | 286 | 0.183 | -0.019 | 49.3% | 140 |
|  | second | 27 | 189 | 0.185 | -0.047 | 47.1% | 119 |
| PCE | first | 41 | 286 | 0.125 | -0.086 | 41.3% | 138 |
|  | second | 28 | 192 | 0.136 | -0.014 | 53.3% | 107 |
| GDP | first | 14 | 98 | 0.151 | -0.062 | 41.4% | 58 |
|  | second | 8 | 56 | 0.186 | +0.006 | 53.6% | 28 |

## By release type, every variant (descriptive)

| id | type | first: hit | resolved | p | second: hit | resolved | p | trade 2nd half: trades | net $ |
|---|---|---|---|---|---|---|---|---|---|
| N1 | FOMC | 34.0% | 47 (12 unres.) | 0.040 | 75.0% | 24 (10 unres.) | 0.023 | 31 | +872 |
|  | CPI | 44.7% | 85 (14 unres.) | 0.386 | 53.9% | 52 (11 unres.) | 0.678 | 63 | -1,151 |
|  | NFP | 57.7% | 52 (24 unres.) | 0.332 | 41.9% | 43 (12 unres.) | 0.360 | 55 | -147 |
|  | PCE | 45.5% | 11 (6 unres.) | 1.000 | 70.0% | 10 (2 unres.) | 0.344 | 12 | +504 |
|  | GDP | 75.0% | 8 (5 unres.) | 0.289 | 75.0% | 4 (0 unres.) | 0.625 | 4 | +36 |
| N2 | FOMC | 42.1% | 19 (2 unres.) | 0.648 | 76.9% | 13 (3 unres.) | 0.092 | 16 | +466 |
|  | CPI | 45.6% | 46 (6 unres.) | 0.659 | 57.9% | 19 (1 unres.) | 0.648 | 20 | -54 |
|  | NFP | 61.5% | 26 (7 unres.) | 0.327 | 37.5% | 16 (8 unres.) | 0.454 | 24 | -172 |
|  | PCE | 0.0% | 2 (1 unres.) | 0.500 | - | 0 |  | 2 | +19 |
|  | GDP | 100.0% | 3 (3 unres.) | 0.250 | 100.0% | 1 (0 unres.) | 1.000 | 1 | +36 |
| N3 | FOMC | 60.9% | 23 (22 unres.) | 0.405 | 58.8% | 17 (15 unres.) | 0.629 | 31 | +441 |
|  | CPI | 37.2% | 43 (14 unres.) | 0.126 | 56.0% | 25 (8 unres.) | 0.690 | 33 | +158 |
|  | NFP | 74.1% | 27 (12 unres.) | 0.019 | 57.1% | 14 (14 unres.) | 0.791 | 28 | +73 |
|  | PCE | 33.3% | 6 (1 unres.) | 0.688 | 75.0% | 4 (4 unres.) | 0.625 | 8 | +401 |
|  | GDP | 50.0% | 6 (5 unres.) | 1.000 | 75.0% | 4 (1 unres.) | 0.625 | 5 | +142 |
| N4 | FOMC | 75.0% | 4 (0 unres.) | 0.625 | 83.3% | 6 (2 unres.) | 0.219 | 8 | +307 |
|  | CPI | 38.5% | 13 (4 unres.) | 0.581 | 75.0% | 8 (0 unres.) | 0.289 | 8 | +250 |
|  | NFP | 87.5% | 8 (1 unres.) | 0.070 | 66.7% | 3 (5 unres.) | 1.000 | 8 | -132 |
|  | PCE | - | 0 |  | - | 0 |  | 1 | -22 |
|  | GDP | 100.0% | 1 (0 unres.) | 1.000 | 100.0% | 2 (0 unres.) | 0.500 | 2 | +118 |
| F1 | FOMC | 66.0% | 47 (12 unres.) | 0.040 | 25.0% | 24 (10 unres.) | 0.023 | 31 | -1,160 |
|  | CPI | 55.3% | 85 (14 unres.) | 0.386 | 44.2% | 52 (11 unres.) | 0.488 | 63 | +90 |
|  | NFP | 42.3% | 52 (24 unres.) | 0.332 | 58.1% | 43 (12 unres.) | 0.360 | 55 | -466 |
|  | PCE | 54.5% | 11 (6 unres.) | 1.000 | 30.0% | 10 (2 unres.) | 0.344 | 12 | -661 |
|  | GDP | 25.0% | 8 (5 unres.) | 0.289 | 25.0% | 4 (0 unres.) | 0.625 | 4 | -75 |
| F2 | FOMC | 57.9% | 19 (2 unres.) | 0.648 | 23.1% | 13 (3 unres.) | 0.092 | 16 | -582 |
|  | CPI | 54.4% | 46 (6 unres.) | 0.659 | 36.8% | 19 (1 unres.) | 0.359 | 20 | -244 |
|  | NFP | 38.5% | 26 (7 unres.) | 0.327 | 62.5% | 16 (8 unres.) | 0.454 | 24 | +16 |
|  | PCE | 100.0% | 2 (1 unres.) | 0.500 | - | 0 |  | 2 | -39 |
|  | GDP | 0.0% | 3 (3 unres.) | 0.250 | 0.0% | 1 (0 unres.) | 1.000 | 1 | -44 |
| F3 | FOMC | 39.1% | 23 (22 unres.) | 0.405 | 41.2% | 17 (15 unres.) | 0.629 | 31 | -756 |
|  | CPI | 62.8% | 43 (14 unres.) | 0.126 | 40.0% | 25 (8 unres.) | 0.424 | 33 | -653 |
|  | NFP | 25.9% | 27 (12 unres.) | 0.019 | 42.9% | 14 (14 unres.) | 0.791 | 28 | -353 |
|  | PCE | 66.7% | 6 (1 unres.) | 0.688 | 25.0% | 4 (4 unres.) | 0.625 | 8 | -514 |
|  | GDP | 50.0% | 6 (5 unres.) | 1.000 | 25.0% | 4 (1 unres.) | 0.625 | 5 | -178 |
| F4 | FOMC | 25.0% | 4 (0 unres.) | 0.625 | 16.7% | 6 (2 unres.) | 0.219 | 8 | -376 |
|  | CPI | 61.5% | 13 (4 unres.) | 0.581 | 12.5% | 8 (0 unres.) | 0.070 | 8 | -356 |
|  | NFP | 12.5% | 8 (1 unres.) | 0.070 | 33.3% | 3 (5 unres.) | 1.000 | 8 | +76 |
|  | PCE | - | 0 |  | - | 0 |  | 1 | +14 |
|  | GDP | 0.0% | 1 (0 unres.) | 1.000 | 0.0% | 2 (0 unres.) | 0.500 | 2 | -138 |

## Per market (descriptive)

| id | market | first: hit | resolved | p | second: hit | resolved | p | trade first: net $ | trade second: trades | won | R after | net $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| N1 | BTCUSDT | 41.7% | 24 (9 unres.) | 0.541 | 63.6% | 11 (0 unres.) | 0.549 | -1,487 | 10 | 60.0% | +0.097 | +208 |
|  | ETHUSDT | 50.0% | 22 (4 unres.) | 1.000 | 61.5% | 13 (2 unres.) | 0.581 | -818 | 15 | 53.3% | +0.071 | +78 |
|  | XAUUSD | 45.8% | 48 (14 unres.) | 0.665 | 56.2% | 32 (9 unres.) | 0.597 | -311 | 40 | 55.0% | +0.037 | -29 |
|  | XAGUSD | 52.1% | 48 (12 unres.) | 0.885 | 57.7% | 26 (6 unres.) | 0.557 | -382 | 31 | 61.3% | +0.121 | +225 |
|  | USDJPY | 60.0% | 35 (17 unres.) | 0.311 | 48.7% | 39 (14 unres.) | 1.000 | +133 | 53 | 49.1% | -0.069 | -219 |
|  | SPX | 20.0% | 10 (1 unres.) | 0.109 | 57.1% | 7 (0 unres.) | 1.000 | -609 | 7 | 57.1% | +0.046 | +18 |
|  | WTI | 30.0% | 10 (2 unres.) | 0.344 | 50.0% | 4 (3 unres.) | 1.000 | -788 | 7 | 28.6% | -0.213 | -218 |
|  | BRENT | 16.7% | 6 (2 unres.) | 0.219 | 100.0% | 1 (1 unres.) | 1.000 | -884 | 2 | 50.0% | +0.278 | +51 |
| N2 | BTCUSDT | 50.0% | 10 (1 unres.) | 1.000 | 0.0% | 1 (0 unres.) | 1.000 | -112 | 1 | 0.0% | -1.132 | -170 |
|  | ETHUSDT | 40.0% | 10 (0 unres.) | 0.754 | 50.0% | 2 (0 unres.) | 1.000 | -688 | 2 | 50.0% | -0.097 | -14 |
|  | XAUUSD | 50.0% | 26 (6 unres.) | 1.000 | 62.5% | 16 (2 unres.) | 0.454 | -98 | 18 | 61.1% | +0.151 | +126 |
|  | XAGUSD | 50.0% | 24 (3 unres.) | 1.000 | 70.0% | 10 (3 unres.) | 0.344 | -281 | 13 | 76.9% | +0.344 | +445 |
|  | USDJPY | 54.5% | 22 (9 unres.) | 0.832 | 47.1% | 17 (9 unres.) | 1.000 | -11 | 26 | 50.0% | -0.071 | -108 |
|  | SPX | 33.3% | 3 (0 unres.) | 1.000 | 66.7% | 3 (0 unres.) | 1.000 | -63 | 3 | 66.7% | +0.236 | +17 |
|  | WTI | 100.0% | 1 (0 unres.) | 1.000 | - | 0 |  | +191 | 0 |  |  | +0 |
|  | BRENT | - | 0 |  | - | 0 |  | +0 | 0 |  |  | +0 |
| N3 | BTCUSDT | 21.4% | 14 (4 unres.) | 0.057 | 60.0% | 5 (0 unres.) | 1.000 | -2,493 | 5 | 60.0% | +0.092 | +249 |
|  | ETHUSDT | 41.7% | 12 (5 unres.) | 0.774 | 100.0% | 3 (1 unres.) | 0.250 | -747 | 4 | 75.0% | +0.566 | +663 |
|  | XAUUSD | 61.5% | 26 (13 unres.) | 0.327 | 69.2% | 13 (12 unres.) | 0.267 | +130 | 25 | 64.0% | +0.129 | +134 |
|  | XAGUSD | 58.3% | 24 (12 unres.) | 0.541 | 47.6% | 21 (7 unres.) | 1.000 | +492 | 28 | 46.4% | -0.072 | -323 |
|  | USDJPY | 66.7% | 18 (16 unres.) | 0.238 | 60.0% | 15 (15 unres.) | 0.607 | +57 | 29 | 51.7% | +0.077 | +106 |
|  | SPX | 66.7% | 6 (2 unres.) | 0.688 | 50.0% | 2 (4 unres.) | 1.000 | +115 | 6 | 50.0% | -0.088 | -52 |
|  | WTI | 25.0% | 4 (2 unres.) | 0.625 | 75.0% | 4 (0 unres.) | 0.625 | -293 | 4 | 75.0% | +0.436 | +330 |
|  | BRENT | 0.0% | 1 (0 unres.) | 1.000 | 0.0% | 1 (3 unres.) | 1.000 | -160 | 4 | 75.0% | +0.065 | +109 |
| N4 | BTCUSDT | 25.0% | 4 (0 unres.) | 0.625 | - | 0 |  | -569 | 0 |  |  | +0 |
|  | ETHUSDT | 0.0% | 1 (2 unres.) | 1.000 | - | 0 |  | -142 | 0 |  |  | +0 |
|  | XAUUSD | 75.0% | 8 (1 unres.) | 0.289 | 100.0% | 5 (3 unres.) | 0.062 | +200 | 8 | 75.0% | +0.437 | +188 |
|  | XAGUSD | 66.7% | 6 (0 unres.) | 0.688 | 80.0% | 5 (2 unres.) | 0.375 | +244 | 7 | 71.4% | +0.373 | +244 |
|  | USDJPY | 71.4% | 7 (2 unres.) | 0.453 | 71.4% | 7 (2 unres.) | 0.453 | +126 | 9 | 66.7% | +0.284 | +110 |
|  | SPX | - | 0 |  | 50.0% | 2 (1 unres.) | 1.000 | +0 | 3 | 66.7% | +0.031 | -20 |
|  | WTI | - | 0 |  | - | 0 |  | +0 | 0 |  |  | +0 |
|  | BRENT | - | 0 |  | - | 0 |  | +0 | 0 |  |  | +0 |
| F1 | BTCUSDT | 58.3% | 24 (9 unres.) | 0.541 | 36.4% | 11 (0 unres.) | 0.549 | +165 | 10 | 40.0% | -0.303 | -611 |
|  | ETHUSDT | 50.0% | 22 (4 unres.) | 1.000 | 38.5% | 13 (2 unres.) | 0.581 | -227 | 15 | 46.7% | -0.238 | -680 |
|  | XAUUSD | 54.2% | 48 (14 unres.) | 0.665 | 43.8% | 32 (9 unres.) | 0.597 | -185 | 40 | 40.0% | -0.189 | -290 |
|  | XAGUSD | 47.9% | 48 (12 unres.) | 0.885 | 42.3% | 26 (6 unres.) | 0.557 | -338 | 31 | 38.7% | -0.235 | -597 |
|  | USDJPY | 40.0% | 35 (17 unres.) | 0.311 | 48.7% | 39 (14 unres.) | 1.000 | -341 | 53 | 45.3% | -0.082 | -43 |
|  | SPX | 80.0% | 10 (1 unres.) | 0.109 | 42.9% | 7 (0 unres.) | 1.000 | +521 | 7 | 42.9% | -0.240 | -74 |
|  | WTI | 70.0% | 10 (2 unres.) | 0.344 | 50.0% | 4 (3 unres.) | 1.000 | +596 | 7 | 71.4% | +0.077 | +107 |
|  | BRENT | 83.3% | 6 (2 unres.) | 0.219 | 0.0% | 1 (1 unres.) | 1.000 | +757 | 2 | 50.0% | -0.396 | -83 |
| F2 | BTCUSDT | 50.0% | 10 (1 unres.) | 1.000 | 100.0% | 1 (0 unres.) | 1.000 | -330 | 1 | 100.0% | +0.868 | +130 |
|  | ETHUSDT | 60.0% | 10 (0 unres.) | 0.754 | 50.0% | 2 (0 unres.) | 1.000 | +286 | 2 | 50.0% | -0.097 | -66 |
|  | XAUUSD | 50.0% | 26 (6 unres.) | 1.000 | 37.5% | 16 (2 unres.) | 0.454 | -158 | 18 | 33.3% | -0.308 | -270 |
|  | XAGUSD | 50.0% | 24 (3 unres.) | 1.000 | 30.0% | 10 (3 unres.) | 0.344 | -43 | 13 | 23.1% | -0.463 | -602 |
|  | USDJPY | 45.5% | 22 (9 unres.) | 0.832 | 47.1% | 17 (9 unres.) | 1.000 | -113 | 26 | 38.5% | -0.123 | -46 |
|  | SPX | 66.7% | 3 (0 unres.) | 1.000 | 33.3% | 3 (0 unres.) | 1.000 | +39 | 3 | 33.3% | -0.430 | -41 |
|  | WTI | 0.0% | 1 (0 unres.) | 1.000 | - | 0 |  | -207 | 0 |  |  | +0 |
|  | BRENT | - | 0 |  | - | 0 |  | +0 | 0 |  |  | +0 |
| F3 | BTCUSDT | 78.6% | 14 (4 unres.) | 0.057 | 40.0% | 5 (0 unres.) | 1.000 | +1,773 | 5 | 40.0% | -0.308 | -449 |
|  | ETHUSDT | 58.3% | 12 (5 unres.) | 0.774 | 0.0% | 3 (1 unres.) | 0.250 | +63 | 4 | 25.0% | -0.741 | -824 |
|  | XAUUSD | 38.5% | 26 (13 unres.) | 0.327 | 30.8% | 13 (12 unres.) | 0.267 | -442 | 25 | 36.0% | -0.275 | -334 |
|  | XAGUSD | 41.7% | 24 (12 unres.) | 0.541 | 52.4% | 21 (7 unres.) | 1.000 | -924 | 28 | 50.0% | -0.045 | -13 |
|  | USDJPY | 33.3% | 18 (16 unres.) | 0.238 | 33.3% | 15 (15 unres.) | 0.302 | -193 | 29 | 37.9% | -0.263 | -272 |
|  | SPX | 33.3% | 6 (2 unres.) | 0.688 | 50.0% | 2 (4 unres.) | 1.000 | -179 | 6 | 50.0% | -0.085 | +4 |
|  | WTI | 75.0% | 4 (2 unres.) | 0.625 | 25.0% | 4 (0 unres.) | 0.625 | +197 | 4 | 25.0% | -0.564 | -393 |
|  | BRENT | 100.0% | 1 (0 unres.) | 1.000 | 100.0% | 1 (3 unres.) | 1.000 | +144 | 4 | 25.0% | -0.187 | -172 |
| F4 | BTCUSDT | 75.0% | 4 (0 unres.) | 0.625 | - | 0 |  | +411 | 0 |  |  | +0 |
|  | ETHUSDT | 100.0% | 1 (2 unres.) | 1.000 | - | 0 |  | +22 | 0 |  |  | +0 |
|  | XAUUSD | 25.0% | 8 (1 unres.) | 0.289 | 0.0% | 5 (3 unres.) | 0.062 | -272 | 8 | 25.0% | -0.603 | -252 |
|  | XAGUSD | 33.3% | 6 (0 unres.) | 0.688 | 20.0% | 5 (2 unres.) | 0.375 | -316 | 7 | 28.6% | -0.499 | -328 |
|  | USDJPY | 28.6% | 7 (2 unres.) | 0.453 | 14.3% | 7 (2 unres.) | 0.125 | -162 | 9 | 11.1% | -0.626 | -196 |
|  | SPX | - | 0 |  | 50.0% | 2 (1 unres.) | 1.000 | +0 | 3 | 33.3% | -0.214 | -4 |
|  | WTI | - | 0 |  | - | 0 |  | +0 | 0 |  |  | +0 |
|  | BRENT | - | 0 |  | - | 0 |  | +0 | 0 |  |  | +0 |

## Checks

| market | bars | first bar | last bar | fee a side | truncation cuts | events compared | mismatched runs | k=1 release status (ok / closed / other) |
|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 240306 | 2019-01-01 00:00 | 2025-11-10 23:45 | 0.100% | 2 | 858 | 0 | 278 / 0 / 0 |
| ETHUSDT | 240306 | 2019-01-01 00:00 | 2025-11-10 23:45 | 0.100% | 2 | 858 | 0 | 278 / 0 / 0 |
| XAUUSD | 162247 | 2019-01-01 23:00 | 2025-11-10 23:45 | 0.020% | 2 | 842 | 0 | 273 / 5 / 0 |
| XAGUSD | 162216 | 2019-01-01 23:00 | 2025-11-10 23:45 | 0.030% | 2 | 842 | 0 | 271 / 5 / 2 |
| USDJPY | 171130 | 2019-01-01 22:00 | 2025-11-10 23:45 | 0.010% | 2 | 854 | 0 | 277 / 1 / 0 |
| SPX | 44687 | 2019-01-02 14:30 | 2025-11-10 20:45 | 0.020% | 2 | 144 | 0 | 47 / 231 / 0 |
| WTI | 161931 | 2019-01-01 23:00 | 2025-11-10 23:45 | 0.040% | 2 | 844 | 0 | 272 / 5 / 1 |
| BRENT | 147959 | 2019-01-02 01:00 | 2025-11-10 21:45 | 0.040% | 2 | 840 | 0 | 270 / 5 / 3 |

## Notes

- Release times are each agency's standard release time on the official release date (ALFRED vintage dates for BLS/BEA, federalreserve.gov for the FOMC); they were not checked row by row against the tape here.
- The S&P 500 file is cash hours only: it sees the FOMC statement (14:00 ET) but not the 8:30 ET releases.
- F1-F4 use N1-N4's rows with the opposite side; with a symmetric bracket their hit rates are close to the complement of N1-N4's (a bar touching both barriers is a miss for both).
- Related forward-only shadows: H1 (CPI follow-through, BTC/ETH) and H16 (release-day follow-through) were set on the 2026 live calendar; H50 is the first look at 2020-2025 and does not change them.
