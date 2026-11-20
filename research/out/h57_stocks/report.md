# H57: stock stances on history

Registered in research/HYPOTHESES.md (H57, 19 Nov 2026 09:58 UTC) before any H57 code or number. Engine think15-v5.2.5. PAPER ONLY. Development data only (rows before 2025-11-11).

**Verdict: NO PASS.** Pooled non-overlapping hit rate above 50% with the 95% interval above 50% in both halves: no. Tickers above 50% (full period, non-overlapping): 7 of 13 (needed 6).

How often a stance is taken at all: of 408523 replayed closes, 1872 LONG (0.46%), 70 SHORT (0.02%), 406581 FLAT (99.52%). The combined S&P odds on a single stock rarely clear the policy's 5-point bar.

## Population and data

- Five tested: NVDA, MU, T; not testable (no Dukascopy CFD): ARGX, DDOG.
- Ten (largest S&P 500 companies, NVDA counted in the five): AAPL, MSFT, AMZN, GOOGL, AVGO, META, TSLA, BRK.B, JPM, LLY.
- Index model: 47 refits (one every 672 index sessions, about five weeks of cash sessions, as the live S&P call refits) walked forward from the engine's birth, first in force 2021-01-12 17:30 (index store 947c9eb316.., last written 2026-11-19T07:17:22Z; copied 19 Nov 2026 10:07 UTC).

| ticker | Dukascopy from | 15m bars | stance closes | first .. last | splits |
|---|---|---|---|---|---|
| NVDA | 2017-01 | 33252 | 31423 | 2021-01-12 17:30 .. 2025-11-10 16:45 | 2021-07-20 x4 (adjusted here); 2024-06-10 x10 (adjusted here) |
| MU | 2017-11 | 33244 | 31408 | 2021-01-12 17:30 .. 2025-11-07 20:45 | - |
| T | 2017-01 | 33108 | 31272 | 2021-01-12 17:30 .. 2025-11-07 20:45 | 2022-04-11 x1.324 (adjusted here) |
| AAPL | 2017-01 | 33247 | 31416 | 2021-01-12 17:30 .. 2025-11-10 15:30 | 2020-08-31 x4 (adjusted here) |
| MSFT | 2017-01 | 33245 | 31413 | 2021-01-12 17:30 .. 2025-11-10 17:15 | - |
| AMZN | 2017-01 | 33284 | 31402 | 2021-01-12 17:30 .. 2025-11-10 14:45 | 2022-06-06 x20 (adjusted here) |
| GOOGL | 2017-01 | 33244 | 31409 | 2021-01-12 17:30 .. 2025-11-10 16:45 | 2022-07-18 x20 (adjusted here) |
| AVGO | 2017-01 | 33239 | 31404 | 2021-01-12 17:30 .. 2025-11-07 20:45 | 2024-07-15 x10 (adjusted here) |
| META | 2017-01 | 33243 | 31407 | 2021-01-12 17:30 .. 2025-11-07 20:45 | - |
| TSLA | 2017-01 | 33253 | 31417 | 2021-01-12 17:30 .. 2025-11-07 20:45 | 2020-08-31 x5 (adjusted here); 2022-08-25 x3 (adjusted here) |
| BRK.B | 2017-11 | 33246 | 31413 | 2021-01-12 17:30 .. 2025-11-10 15:00 | - |
| JPM | 2017-01 | 33247 | 31411 | 2021-01-12 17:30 .. 2025-11-07 20:45 | - |
| LLY | 2017-05 | 33248 | 31412 | 2021-01-12 17:30 .. 2025-11-07 20:45 | - |

## Hit rate of LONG / SHORT calls (NEITHER not counted)

Halves split at 2021-10-01 19:30 UTC (median date of the pooled graded calls). nov = non-overlapping calls; interval = Wilson 95% on them. 'all' = every call, overlapping, no interval.

| ticker | calls | all hit | nov graded | nov hit | 95% interval | first half nov hit (n) | second half nov hit (n) | LONG / SHORT / FLAT closes |
|---|---|---|---|---|---|---|---|---|
| NVDA | 181 | 49.1% | 28 | 46.4% | 29.5% .. 64.2% | 40.0% (15) | 53.8% (13) | 177 / 4 / 31242 |
| MU | 150 | 47.0% | 29 | 44.8% | 28.4% .. 62.5% | 50.0% (14) | 40.0% (15) | 146 / 4 / 31258 |
| T | 96 | 57.3% | 14 | 42.9% | 21.4% .. 67.4% | 66.7% (3) | 36.4% (11) | 78 / 18 / 31176 |
| AAPL | 241 | 59.2% | 36 | 47.2% | 32.0% .. 63.0% | 57.1% (21) | 33.3% (15) | 240 / 1 / 31175 |
| MSFT | 70 | 69.2% | 18 | 55.6% | 33.7% .. 75.4% | 75.0% (8) | 40.0% (10) | 70 / 0 / 31343 |
| AMZN | 158 | 57.0% | 27 | 48.1% | 30.7% .. 66.0% | 52.9% (17) | 40.0% (10) | 148 / 10 / 31244 |
| GOOGL | 123 | 69.1% | 18 | 61.1% | 38.6% .. 79.7% | 75.0% (4) | 57.1% (14) | 121 / 2 / 31286 |
| AVGO | 170 | 52.6% | 33 | 57.6% | 40.8% .. 72.8% | 53.8% (13) | 60.0% (20) | 166 / 4 / 31234 |
| META | 85 | 80.6% | 13 | 53.8% | 29.1% .. 76.8% | 62.5% (8) | 40.0% (5) | 83 / 2 / 31322 |
| TSLA | 177 | 54.1% | 33 | 57.6% | 40.8% .. 72.8% | 47.4% (19) | 71.4% (14) | 168 / 9 / 31240 |
| BRK.B | 195 | 61.9% | 32 | 53.1% | 36.4% .. 69.1% | 58.3% (12) | 50.0% (20) | 194 / 1 / 31218 |
| JPM | 140 | 42.9% | 15 | 46.7% | 24.8% .. 69.9% | 50.0% (8) | 42.9% (7) | 138 / 2 / 31271 |
| LLY | 156 | 72.0% | 28 | 71.4% | 52.9% .. 84.7% | 66.7% (15) | 76.9% (13) | 143 / 13 / 31256 |
| **five** | 427 | 50.3% | 71 | 45.1% | 34.0% .. 56.6% | 46.9% (32) | 43.6% (39) | - |
| **ten** | 1515 | 60.0% | 253 | 55.3% | 49.2% .. 61.3% | 57.6% (125) | 53.1% (128) | - |
| **pooled** | 1942 | 57.7% | 324 | 53.1% | 47.6% .. 58.5% | 55.4% (157) | 50.9% (167) | - |

Day-block bootstrap of the pooled non-overlapping hit rate (descriptive; calls of different stocks at the same time are correlated): full 46.7% .. 58.8%, first 46.4% .. 64.2%, second 41.3% .. 59.5%.

## Probabilities: Brier and log-loss of P(up) / (P(up) + P(down)) against the ticker's own UP share

Every stance row (LONG, SHORT, FLAT) graded UP or DOWN, overlapping; base rate = the ticker's UP share in the same half (in-sample, favours the base). Skill > 0 = better than the base rate.

| ticker | rows | UP share | Brier | base | skill | log-loss | base | skill | skill first | skill second |
|---|---|---|---|---|---|---|---|---|---|---|
| NVDA | 24174 | 52.7% | 0.2502 | 0.2492 | -0.0040 | 0.6936 | 0.6916 | -0.0029 | -0.0029 | -0.0043 |
| MU | 23998 | 52.1% | 0.2498 | 0.2496 | -0.0007 | 0.6927 | 0.6923 | -0.0005 | -0.0058 | -0.0002 |
| T | 23598 | 51.6% | 0.2502 | 0.2498 | -0.0016 | 0.6934 | 0.6927 | -0.0012 | 0.0009 | -0.0020 |
| AAPL | 23369 | 52.9% | 0.2501 | 0.2492 | -0.0036 | 0.6933 | 0.6915 | -0.0026 | -0.0029 | -0.0037 |
| MSFT | 23515 | 52.8% | 0.2500 | 0.2492 | -0.0033 | 0.6932 | 0.6916 | -0.0023 | -0.0168 | -0.0019 |
| AMZN | 24153 | 51.3% | 0.2502 | 0.2498 | -0.0014 | 0.6935 | 0.6928 | -0.0010 | -0.0044 | -0.0008 |
| GOOGL | 23642 | 52.7% | 0.2493 | 0.2493 | -0.0001 | 0.6918 | 0.6917 | -0.0001 | -0.0043 | 0.0002 |
| AVGO | 23991 | 52.2% | 0.2500 | 0.2495 | -0.0018 | 0.6931 | 0.6921 | -0.0013 | 0.0036 | -0.0038 |
| META | 23533 | 52.5% | 0.2501 | 0.2494 | -0.0028 | 0.6934 | 0.6919 | -0.0020 | -0.0078 | -0.0022 |
| TSLA | 24350 | 50.4% | 0.2505 | 0.2500 | -0.0022 | 0.6942 | 0.6931 | -0.0016 | -0.0004 | -0.0026 |
| BRK.B | 23488 | 53.2% | 0.2501 | 0.2490 | -0.0046 | 0.6934 | 0.6911 | -0.0033 | -0.0001 | -0.0054 |
| JPM | 24308 | 53.9% | 0.2500 | 0.2485 | -0.0058 | 0.6930 | 0.6902 | -0.0042 | -0.0048 | -0.0061 |
| LLY | 22694 | 52.8% | 0.2506 | 0.2492 | -0.0054 | 0.6943 | 0.6916 | -0.0039 | -0.0151 | -0.0039 |
| **five** | 71770 | 52.1% | 0.2500 | 0.2495 | -0.0021 | 0.6932 | 0.6922 | -0.0015 | -0.0027 | -0.0022 |
| **ten** | 237043 | 52.4% | 0.2501 | 0.2493 | -0.0031 | 0.6933 | 0.6918 | -0.0022 | -0.0052 | -0.0030 |
| **pooled** | 308813 | 52.4% | 0.2501 | 0.2494 | -0.0029 | 0.6933 | 0.6919 | -0.0021 | -0.0046 | -0.0028 |

## Pass table (fixed in the registration)

| condition | required | result | met |
|---|---|---|---|
| pooled nov hit, first half | > 50% and 95% lower bound > 50% | 55.4% (47.6% .. 63.0%, n 157) | no |
| pooled nov hit, second half | > 50% and 95% lower bound > 50% | 50.9% (43.4% .. 58.4%, n 167) | no |
| tickers with full-period nov hit > 50% | >= 6 of 13 | 7 (MSFT, GOOGL, AVGO, META, TSLA, BRK.B, LLY) | yes |
| **H57** | both | | **NO PASS** |

## How it was made

- Bars: Dukascopy BID minute candles of each stock CFD -> 15-minute cash-hours bars (research/h57_data.py); daily bars from the same bars (hourly candles before the minute data). CFD prices are not the exchange's prints (a quote-driven feed; minute volume is the CFD's), checked against Yahoo's daily closes (data.json).
- Stance: engine15/stocks.py's own functions at every cash-hours close where the S&P 500 has one, with the S&P model as it stood then (refits every 672 index sessions walked forward on the index store's rows, trust and cap as leanprep.prepare_live forms them). Readings per calendar month from a window starting 60 days before it (the live store's situation), daily bars before the window.
- Grading: labels.triple_barrier on the stock's bars, 1.5 x atr1h, 26 bars; NEITHER not counted.
- Not a trading test: no costs, no positions; a stance's hit rate only.
