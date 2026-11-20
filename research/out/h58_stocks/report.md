# H58: the stocks' own model on history

Registered in research/HYPOTHESES.md (H58, 20 Nov 2026 02:50 UTC) before any H58 code or number. Engine think15-v5.2.5. PAPER ONLY. Development data only (rows before 2025-11-11).

**Verdict: NO PASS.**

| condition | required | result | met |
|---|---|---|---|
| pooled nov hit, first half | > 50% and 95% lower bound > 50% | 40.2% (31.6% .. 49.4%, n 112) | no |
| pooled nov hit, second half | > 50% and 95% lower bound > 50% | 57.2% (49.8% .. 64.4%, n 173) | no |
| tickers with full-period nov hit > 50% | >= 6 of 13 | 6 (MSFT, GOOGL, AVGO, META, BRK.B, JPM) | yes |
| **verdict** | both | | **NO PASS** |

How often a stance is taken: of 325705 closes: 1759 LONG (0.54%), 778 SHORT (0.24%), 323168 FLAT (99.22%).

## Side by side with H57

| measure | H58 primary (2022-01-03 .. seal) | H58 leave-one-ticker-out | H57 same dates | H57 as reported (2021-01-12 .. seal) |
|---|---|---|---|---|
| calls (LONG/SHORT) | 2537 (all hit 47.0%) | 2439 (all hit 49.8%) | 711 (all hit 52.8%) | 1942 (all hit 57.7%) |
| pooled non-overlapping hit | 50.5% (44.8% .. 56.3%, n 285) | 52.8% (47.2% .. 58.3%, n 307) | 49.6% (41.3% .. 58.0%, n 133) | 53.1% (47.6% .. 58.5%, n 324) |
| first half | 40.2% (lower 31.6%, n 112) | 50.4% (lower 41.4%, n 115) | 50.8% (lower 38.4%, n 59) | 55.4% (lower 47.6%, n 157) |
| second half | 57.2% (lower 49.8%, n 173) | 54.2% (lower 47.1%, n 192) | 48.6% (lower 37.6%, n 74) | 50.9% (lower 43.4%, n 167) |
| day-block bootstrap 95% | 40.9% .. 60.0% | 44.5% .. 60.8% | 38.0% .. 59.3% | 46.7% .. 58.8% |
| tickers above 50% | 6 of 13 | 7 of 13 | 5 of 13 | 7 of 13 |
| Brier skill vs base | -0.0021 | -0.0017 | -0.0023 | -0.0029 |
| log-loss skill vs base | -0.0015 | -0.0012 | -0.0017 | -0.0021 |
| share of closes with a stance | 0.78% | 0.75% | 0.22% | 0.48% |

Halves: H58 split at 2023-03-14 15:45 UTC; H57-same-dates split at 2022-02-25 20:22 UTC (each at its own median graded call).

## H58 primary: hit rate of LONG / SHORT calls (NEITHER not counted)

| ticker | calls | all hit | nov graded | nov hit | 95% interval | first half nov hit (n) | second half nov hit (n) | LONG / SHORT / FLAT closes |
|---|---|---|---|---|---|---|---|---|
| NVDA | 255 | 44.5% | 31 | 48.4% | 32.0% .. 65.2% | 20.0% (10) | 61.9% (21) | 167 / 88 / 24797 |
| MU | 149 | 50.8% | 21 | 47.6% | 28.3% .. 67.6% | 33.3% (12) | 66.7% (9) | 84 / 65 / 24888 |
| T | 133 | 34.0% | 14 | 42.9% | 21.4% .. 67.4% | 60.0% (5) | 33.3% (9) | 122 / 11 / 24772 |
| AAPL | 149 | 23.3% | 16 | 37.5% | 18.5% .. 61.4% | 16.7% (6) | 50.0% (10) | 110 / 39 / 24896 |
| MSFT | 234 | 60.1% | 26 | 61.5% | 42.5% .. 77.6% | 54.5% (11) | 66.7% (15) | 152 / 82 / 24808 |
| AMZN | 173 | 55.4% | 25 | 36.0% | 20.2% .. 55.5% | 22.2% (9) | 43.8% (16) | 125 / 48 / 24858 |
| GOOGL | 134 | 51.9% | 17 | 52.9% | 31.0% .. 73.8% | 28.6% (7) | 70.0% (10) | 89 / 45 / 24904 |
| AVGO | 242 | 57.7% | 33 | 60.6% | 43.7% .. 75.3% | 61.5% (13) | 60.0% (20) | 151 / 91 / 24792 |
| META | 213 | 70.7% | 23 | 52.2% | 33.0% .. 70.8% | 50.0% (8) | 53.3% (15) | 168 / 45 / 24823 |
| TSLA | 211 | 23.7% | 22 | 40.9% | 23.3% .. 61.3% | 33.3% (9) | 46.2% (13) | 127 / 84 / 24835 |
| BRK.B | 226 | 21.1% | 21 | 52.4% | 32.4% .. 71.7% | 50.0% (8) | 53.8% (13) | 180 / 46 / 24816 |
| JPM | 151 | 57.1% | 18 | 72.2% | 49.1% .. 87.5% | 66.7% (6) | 75.0% (12) | 126 / 25 / 24889 |
| LLY | 267 | 46.3% | 18 | 44.4% | 24.6% .. 66.3% | 25.0% (8) | 60.0% (10) | 158 / 109 / 24774 |
| **five** | 537 | 44.1% | 66 | 47.0% | 35.4% .. 58.8% | 33.3% (27) | 56.4% (39) | - |
| **ten** | 2000 | 47.9% | 219 | 51.6% | 45.0% .. 58.1% | 42.4% (85) | 57.5% (134) | - |
| **pooled** | 2537 | 47.0% | 285 | 50.5% | 44.8% .. 56.3% | 40.2% (112) | 57.2% (173) | - |

Day-block bootstrap of the pooled non-overlapping hit rate: full 40.9% .. 60.0%, first 20.8% .. 59.1%, second 46.5% .. 66.7%.

## H58 primary: probabilities against each ticker's own UP share

| ticker | rows | UP share | Brier | base | skill | log-loss | base | skill | skill first | skill second |
|---|---|---|---|---|---|---|---|---|---|---|
| NVDA | 19312 | 52.7% | 0.2500 | 0.2493 | -0.0031 | 0.6932 | 0.6917 | -0.0022 | -0.0033 | -0.0067 |
| MU | 18999 | 51.3% | 0.2497 | 0.2498 | 0.0005 | 0.6925 | 0.6928 | 0.0004 | -0.0086 | -0.0023 |
| T | 18890 | 52.4% | 0.2500 | 0.2494 | -0.0021 | 0.6931 | 0.6920 | -0.0015 | -0.0013 | -0.0058 |
| AAPL | 18668 | 52.2% | 0.2503 | 0.2495 | -0.0031 | 0.6937 | 0.6922 | -0.0022 | -0.0046 | -0.0052 |
| MSFT | 18715 | 51.4% | 0.2501 | 0.2498 | -0.0013 | 0.6934 | 0.6927 | -0.0009 | -0.0053 | -0.0053 |
| AMZN | 19255 | 51.2% | 0.2503 | 0.2499 | -0.0018 | 0.6937 | 0.6929 | -0.0013 | -0.0060 | -0.0041 |
| GOOGL | 19143 | 52.5% | 0.2498 | 0.2494 | -0.0018 | 0.6928 | 0.6919 | -0.0013 | -0.0108 | -0.0104 |
| AVGO | 19100 | 52.2% | 0.2497 | 0.2495 | -0.0006 | 0.6925 | 0.6922 | -0.0004 | 0.0007 | -0.0039 |
| META | 18683 | 52.4% | 0.2499 | 0.2494 | -0.0020 | 0.6930 | 0.6920 | -0.0014 | -0.0048 | -0.0057 |
| TSLA | 19530 | 50.0% | 0.2502 | 0.2500 | -0.0006 | 0.6935 | 0.6931 | -0.0004 | -0.0063 | -0.0006 |
| BRK.B | 18764 | 52.9% | 0.2500 | 0.2492 | -0.0035 | 0.6932 | 0.6915 | -0.0025 | -0.0005 | -0.0069 |
| JPM | 19165 | 53.6% | 0.2501 | 0.2487 | -0.0057 | 0.6934 | 0.6905 | -0.0041 | -0.0033 | -0.0094 |
| LLY | 18020 | 52.3% | 0.2499 | 0.2495 | -0.0017 | 0.6930 | 0.6921 | -0.0012 | -0.0035 | -0.0073 |
| **five** | 57201 | 52.1% | 0.2499 | 0.2495 | -0.0016 | 0.6929 | 0.6922 | -0.0011 | -0.0045 | -0.0050 |
| **ten** | 189043 | 52.1% | 0.2500 | 0.2495 | -0.0022 | 0.6932 | 0.6921 | -0.0016 | -0.0045 | -0.0059 |
| **pooled** | 246244 | 52.1% | 0.2500 | 0.2495 | -0.0021 | 0.6932 | 0.6921 | -0.0015 | -0.0045 | -0.0056 |

## Leave-one-ticker-out (a check, not the verdict)

Each ticker judged by a model whose card rating, voices and trust never saw it. Stances: of 325705 closes: 1602 LONG (0.49%), 837 SHORT (0.26%), 323266 FLAT (99.25%).

| condition | required | result | met |
|---|---|---|---|
| pooled nov hit, first half | > 50% and 95% lower bound > 50% | 50.4% (41.4% .. 59.4%, n 115) | no |
| pooled nov hit, second half | > 50% and 95% lower bound > 50% | 54.2% (47.1% .. 61.1%, n 192) | no |
| tickers with full-period nov hit > 50% | >= 6 of 13 | 7 (NVDA, MSFT, GOOGL, AVGO, TSLA, BRK.B, JPM) | yes |
| **verdict** | both | | **NO PASS** |

| ticker | calls | all hit | nov graded | nov hit | 95% interval | first half nov hit (n) | second half nov hit (n) | LONG / SHORT / FLAT closes |
|---|---|---|---|---|---|---|---|---|
| NVDA | 197 | 50.7% | 28 | 53.6% | 35.8% .. 70.5% | 50.0% (12) | 56.2% (16) | 112 / 85 / 24855 |
| MU | 121 | 54.4% | 18 | 38.9% | 20.3% .. 61.4% | 28.6% (7) | 45.5% (11) | 78 / 43 / 24916 |
| T | 202 | 53.0% | 26 | 50.0% | 32.1% .. 67.9% | 60.0% (10) | 43.8% (16) | 122 / 80 / 24703 |
| AAPL | 131 | 24.7% | 22 | 18.2% | 7.3% .. 38.5% | 14.3% (7) | 20.0% (15) | 102 / 29 / 24914 |
| MSFT | 232 | 61.8% | 23 | 65.2% | 44.9% .. 81.2% | 50.0% (12) | 81.8% (11) | 108 / 124 / 24810 |
| AMZN | 186 | 44.6% | 19 | 36.8% | 19.1% .. 59.0% | 0.0% (1) | 38.9% (18) | 163 / 23 / 24845 |
| GOOGL | 189 | 60.0% | 29 | 75.9% | 57.9% .. 87.8% | 75.0% (16) | 76.9% (13) | 89 / 100 / 24849 |
| AVGO | 224 | 54.3% | 31 | 58.1% | 40.8% .. 73.6% | 54.5% (11) | 60.0% (20) | 168 / 56 / 24810 |
| META | 237 | 70.8% | 32 | 50.0% | 33.6% .. 66.4% | 50.0% (8) | 50.0% (24) | 174 / 63 / 24799 |
| TSLA | 214 | 34.8% | 20 | 60.0% | 38.7% .. 78.1% | 62.5% (8) | 58.3% (12) | 192 / 22 / 24832 |
| BRK.B | 242 | 38.0% | 25 | 56.0% | 37.1% .. 73.3% | 55.6% (9) | 56.2% (16) | 112 / 130 / 24800 |
| JPM | 144 | 33.1% | 25 | 60.0% | 40.7% .. 76.6% | 40.0% (10) | 73.3% (15) | 100 / 44 / 24896 |
| LLY | 120 | 42.4% | 9 | 44.4% | 18.9% .. 73.3% | 25.0% (4) | 60.0% (5) | 82 / 38 / 24921 |
| **five** | 520 | 52.5% | 72 | 48.6% | 37.4% .. 59.9% | 48.3% (29) | 48.8% (43) | - |
| **ten** | 1919 | 49.0% | 235 | 54.0% | 47.7% .. 60.3% | 51.2% (86) | 55.7% (149) | - |
| **pooled** | 2439 | 49.8% | 307 | 52.8% | 47.2% .. 58.3% | 50.4% (115) | 54.2% (192) | - |

## E1 (exploratory): without the two stock-only cards

Stances: of 325705 closes: 1893 LONG (0.58%), 769 SHORT (0.24%), 323043 FLAT (99.18%).

| condition | required | result | met |
|---|---|---|---|
| pooled nov hit, first half | > 50% and 95% lower bound > 50% | 39.8% (31.3% .. 49.0%, n 113) | no |
| pooled nov hit, second half | > 50% and 95% lower bound > 50% | 55.6% (49.4% .. 61.6%, n 252) | no |
| tickers with full-period nov hit > 50% | >= 6 of 13 | 6 (T, MSFT, GOOGL, AVGO, BRK.B, JPM) | yes |
| **verdict** | both | | **NO PASS** |

| ticker | calls | all hit | nov graded | nov hit | 95% interval | first half nov hit (n) | second half nov hit (n) | LONG / SHORT / FLAT closes |
|---|---|---|---|---|---|---|---|---|
| NVDA | 265 | 48.2% | 36 | 41.7% | 27.1% .. 57.8% | 20.0% (10) | 50.0% (26) | 177 / 88 / 24787 |
| MU | 174 | 50.7% | 29 | 48.3% | 31.4% .. 65.6% | 30.8% (13) | 62.5% (16) | 109 / 65 / 24863 |
| T | 144 | 40.0% | 26 | 57.7% | 38.9% .. 74.5% | 60.0% (5) | 57.1% (21) | 133 / 11 / 24761 |
| AAPL | 154 | 24.7% | 18 | 38.9% | 20.3% .. 61.4% | 16.7% (6) | 50.0% (12) | 113 / 41 / 24891 |
| MSFT | 242 | 56.7% | 31 | 51.6% | 34.8% .. 68.0% | 54.5% (11) | 50.0% (20) | 165 / 77 / 24800 |
| AMZN | 185 | 55.9% | 29 | 34.5% | 19.9% .. 52.7% | 22.2% (9) | 40.0% (20) | 137 / 48 / 24846 |
| GOOGL | 144 | 50.9% | 21 | 52.4% | 32.4% .. 71.7% | 28.6% (7) | 64.3% (14) | 99 / 45 / 24894 |
| AVGO | 237 | 55.2% | 38 | 60.5% | 44.7% .. 74.4% | 61.5% (13) | 60.0% (25) | 157 / 80 / 24797 |
| META | 213 | 62.8% | 30 | 43.3% | 27.4% .. 60.8% | 50.0% (8) | 40.9% (22) | 168 / 45 / 24823 |
| TSLA | 205 | 24.0% | 24 | 45.8% | 27.9% .. 64.9% | 33.3% (9) | 53.3% (15) | 130 / 75 / 24841 |
| BRK.B | 266 | 28.7% | 32 | 62.5% | 45.3% .. 77.1% | 50.0% (8) | 66.7% (24) | 209 / 57 / 24776 |
| JPM | 154 | 54.0% | 27 | 70.4% | 51.5% .. 84.1% | 66.7% (6) | 71.4% (21) | 129 / 25 / 24886 |
| LLY | 279 | 46.2% | 24 | 45.8% | 27.9% .. 64.9% | 25.0% (8) | 56.2% (16) | 167 / 112 / 24762 |
| **five** | 583 | 47.1% | 91 | 48.4% | 38.4% .. 58.5% | 32.1% (28) | 55.6% (63) | - |
| **ten** | 2079 | 46.6% | 274 | 51.5% | 45.6% .. 57.3% | 42.4% (85) | 55.6% (189) | - |
| **pooled** | 2662 | 46.7% | 365 | 50.7% | 45.6% .. 55.8% | 39.8% (113) | 55.6% (252) | - |

## Which cards voted (primary, 38 refits)

| card | refits voting |
|---|---|
| Ultimate Oscillator (15m, 1h, daily) | 37 |
| News and economic events | 36 |
| Mass Index (1h to daily) | 31 |
| Linear-regression channel (1h to daily) | 29 |
| Intraday levels (VWAP and opening range) | 27 |
| Own earnings date | 26 |
| Elder-Ray (1h to daily) | 21 |
| Trade setups | 21 |
| Chaikin money flow and OBV (1h to daily) | 18 |
| Timeframe strength | 18 |
| Regime | 17 |
| Trend quality and squeeze | 15 |
| Time and session | 14 |
| Stock-market breadth | 14 |
| Moving averages (SMA and EMA 5-200) | 12 |
| Market structure | 9 |
| Aroon and Vortex (1h to daily) | 8 |
| Volatility gauges | 6 |
| Kaufman adaptive average (KAMA) | 6 |
| Daily range budget and range breaks | 4 |
| Support and resistance | 2 |
| Money Flow Index (15m to daily) | 2 |
| Fibonacci retracement | 2 |
| RSI divergence (15m to 4h) | 2 |
| StochRSI (15m to daily) | 1 |
| Rates and the dollar | 1 |
| Williams %R (15m to daily) | 1 |

Mean say per voice on judged closes (after voting mask, speaking mask and the 40% cap), largest first:

- macro: 13.1%
- ultosc: 11.5%
- intraday: 8.8%
- mass: 7.8%
- linreg: 7.6%
- trend: 6.7%
- clock: 6.7%
- cmf: 6.2%
- mavg: 5.9%
- elder: 4.8%
- trendq: 3.3%
- eqbreadth: 3.0%
- regime: 2.6%
- aroon: 1.9%
- structure: 1.9%

## The two stock-only cards at each refit (1st half, 2nd half, steady, direction)

| refit | strength vs S&P 500 | own earnings date |
|---|---|---|
| 2022-01-03 | 50.5 / 50.6 / 0.5 / with (rs_1d) | 48.1 / 45.3 / 1.9 / against (ern_next_s) |
| 2022-02-08 | 50.3 / 51.4 / 0.3 / with (rs_1d) | 31.6 / 47.8 / 2.2 / against (ern_last_s) |
| 2022-03-17 | 50.1 / 50.8 / 0.1 / with (rs_1h) | 33.8 / 43.7 / 6.3 / against (ern_last_s) |
| 2022-04-25 | 50.2 / 50.7 / 0.2 / with (rs_1h) | 33.8 / 41.8 / 8.2 / against (ern_last_s) |
| 2022-06-01 | 50.1 / 50.1 / 0.1 / with (rs_1h) | 34.4 / 43.7 / 6.3 / against (ern_last_s) |
| 2022-07-11 | 50.1 / 50.6 / 0.1 / with (rs_1h) | 33.1 / 45.6 / 4.4 / against (ern_last_s) |
| 2022-08-16 | 49.9 / 50.8 / 0.0 / against (rs_1h) | 43.3 / 60.7 / 0.0 / against (ern_next_s) |
| 2022-09-21 | 50.3 / 50.8 / 0.3 / with (rs_1d) | 38.0 / 49.0 / 1.0 / against (ern_last_s) |
| 2022-10-27 | 50.2 / 50.0 / 0.0 / with (rs_1h) | 41.2 / 46.8 / 3.2 / against (ern_last_s) |
| 2022-12-06 | 50.6 / 51.2 / 0.6 / with (rs_1d) | 41.4 / 45.8 / 4.2 / against (ern_last_s) |
| 2023-01-12 | 50.6 / 51.5 / 0.6 / with (rs_1d) | 41.0 / 45.7 / 4.3 / against (ern_last_s) |
| 2023-02-21 | 51.0 / 51.0 / 1.0 / with (rs_1d) | 41.0 / 46.1 / 3.9 / against (ern_last_s) |
| 2023-03-29 | 50.9 / 50.9 / 0.9 / with (rs_1d) | 46.3 / 56.3 / 0.0 / against (ern_next_s) |
| 2023-05-05 | 50.8 / 50.6 / 0.6 / with (rs_1d) | 40.2 / 49.5 / 0.5 / against (ern_last_s) |
| 2023-06-13 | 50.9 / 50.7 / 0.7 / with (rs_1d) | 48.7 / 55.7 / 0.0 / against (ern_next_s) |
| 2023-07-21 | 50.9 / 50.7 / 0.7 / with (rs_1d) | 48.5 / 54.8 / 0.0 / against (ern_next_s) |
| 2023-08-28 | 50.4 / 50.4 / 0.4 / with (rs_1h) | 38.8 / 49.2 / 0.8 / against (ern_last_s) |
| 2023-10-04 | 50.4 / 50.4 / 0.4 / with (rs_1h) | 48.9 / 56.1 / 0.0 / against (ern_next_s) |
| 2023-11-09 | 50.2 / 50.7 / 0.2 / with (rs_1d) | 48.8 / 53.6 / 0.0 / against (ern_next_s) |
| 2023-12-18 | 50.1 / 50.7 / 0.1 / with (rs_1h) | 39.0 / 49.5 / 0.5 / against (ern_last_s) |
| 2024-01-26 | 50.4 / 50.6 / 0.4 / with (rs_1d) | 39.4 / 47.6 / 2.4 / against (ern_last_s) |
| 2024-03-05 | 50.5 / 50.7 / 0.5 / with (rs_1d) | 41.4 / 44.7 / 5.3 / against (ern_last_s) |
| 2024-04-11 | 50.3 / 50.2 / 0.2 / with (rs_1h) | 45.1 / 41.0 / 4.9 / against (ern_last_s) |
| 2024-05-17 | 50.5 / 50.3 / 0.3 / with (rs_1d) | 45.1 / 41.9 / 4.9 / against (ern_last_s) |
| 2024-06-26 | 50.4 / 50.6 / 0.4 / with (rs_1d) | 44.0 / 42.8 / 6.0 / against (ern_last_s) |
| 2024-08-02 | 50.5 / 51.0 / 0.5 / with (rs_1d) | 44.0 / 44.0 / 6.0 / against (ern_last_s) |
| 2024-09-10 | 50.7 / 51.1 / 0.7 / with (rs_1d) | 45.8 / 40.5 / 4.2 / against (ern_last_s) |
| 2024-10-16 | 50.6 / 50.9 / 0.6 / with (rs_1d) | 45.0 / 39.8 / 5.0 / against (ern_last_s) |
| 2024-11-20 | 50.2 / 50.8 / 0.2 / with (rs_1h) | 43.6 / 39.9 / 6.4 / against (ern_last_s) |
| 2024-12-31 | 50.2 / 50.5 / 0.2 / with (rs_1h) | 44.0 / 41.5 / 6.0 / against (ern_last_s) |
| 2025-02-10 | 50.1 / 50.5 / 0.1 / with (rs_1h) | 44.0 / 43.7 / 6.0 / against (ern_last_s) |
| 2025-03-19 | 50.2 / 50.7 / 0.2 / with (rs_1h) | 43.2 / 43.6 / 6.4 / against (ern_last_s) |
| 2025-04-25 | 50.4 / 50.4 / 0.4 / with (rs_1h) | 43.9 / 43.1 / 6.1 / against (ern_last_s) |
| 2025-06-03 | 50.3 / 50.5 / 0.3 / with (rs_1h) | 43.8 / 42.6 / 6.2 / against (ern_last_s) |
| 2025-07-11 | 50.4 / 50.5 / 0.4 / with (rs_1h) | 44.5 / 41.1 / 5.5 / against (ern_last_s) |
| 2025-08-18 | 50.3 / 50.4 / 0.3 / with (rs_1h) | 44.5 / 42.0 / 5.5 / against (ern_last_s) |
| 2025-09-24 | 50.4 / 50.4 / 0.4 / with (rs_1h) | 45.1 / 42.5 / 4.9 / against (ern_last_s) |
| 2025-10-29 | 50.2 / 50.5 / 0.2 / with (rs_1h) | 45.5 / 44.2 / 4.5 / against (ern_last_s) |

## How it was made

- Bars: H57's Dukascopy CFD 15-minute cash-hours bars; S&P 500 bars from the engine's data/spx_15m.csv (copied read-only).
- Readings: engine15/stocks.py's readings per calendar month from a 60-day window (as live), market-wide cards from the S&P call's readings at the same close; strength against the S&P 500 and own earnings date (megacap earnings file; MU, T, LLY no read).
- Model: walk-forward, refit every 672 sessions of the 13 tickers' common timeline from 2022-01-03; at each refit the cards are rated (rate_cards.py's functions) and the voices fitted (model.fit_softmax) only on rows whose grade was known then; trust is the engine's Hedge on graded losses as they arrive; the stance is stocks.decide.
- Grading: labels.triple_barrier, 1.5 x atr1h, 26 bars; NEITHER not counted. Not a trading test: no costs.
