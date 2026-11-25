# H118: H107's rebound rules on ten more coins and BTC/ETH before Oct 2019

Registered in research/HYPOTHESES.md (H118) before any number. Fee 0.10% a side on every coin (generous to alts). Data to the bar opening 2025-11-10 23:45 UTC; the holdout was not downloaded. Run 70 s.

## Test 1 (the decision): ten alts pooled

### Rule A: **FAIL**

- p 0.2454, Holm 0.4908; checks: n_all>=100 ok, n_h1>=30 ok, n_h2>=30 ok, mean_r_h1>0 FAILED, mean_r_h2>0 ok, coins_with_mean_r>0_of_coins_with_5+_trades>=7 FAILED, holm_p<0.05 FAILED, excess_pooled>0 ok
- coins with 5+ trades: 10; with mean R > 0: 5 (AVAXUSDT, DOTUSDT, LINKUSDT, TRXUSDT, XRPUSDT)
- pooled: 891, 54% won, mean +0.041 [-0.067, +0.152], p 0.245, sum +36.8R
- first half: 610, 50% won, mean -0.017 [-0.150, +0.125], p 0.615, sum -10.5R
- second half: 281, 62% won, mean +0.168 [+0.038, +0.320], p 0.015, sum +47.3R
- excess over the drift baseline: +0.236 [+0.120, +0.351]
- exits {'stop': 337, 'T1_then_entry': 98, 'T1_T2': 121, 'T1_then_time': 160, 'time': 175}; longest losing run 19; deepest fall of cumulative R -40.1R; median +0.202

| coin | trades | won | mean R [95%] | sum R | h1 mean (n) | h2 mean (n) | skipped |
|---|---|---|---|---|---|---|---|
| ADAUSDT | 125 | 51% | -0.021 [-0.169, +0.144] | -2.6 | -0.072 (95) | +0.141 (30) | 78 |
| AVAXUSDT | 80 | 59% | +0.094 [-0.087, +0.321] | +7.5 | +0.084 (41) | +0.104 (39) | 49 |
| BNBUSDT | 81 | 46% | -0.108 [-0.260, +0.094] | -8.8 | -0.154 (65) | +0.075 (16) | 58 |
| DOGEUSDT | 82 | 56% | -0.001 [-0.160, +0.175] | -0.1 | -0.020 (48) | +0.026 (34) | 54 |
| DOTUSDT | 85 | 59% | +0.087 [-0.106, +0.312] | +7.4 | +0.061 (45) | +0.116 (40) | 44 |
| LINKUSDT | 82 | 66% | +0.248 [+0.045, +0.464] | +20.3 | +0.196 (49) | +0.325 (33) | 37 |
| LTCUSDT | 114 | 50% | -0.041 [-0.190, +0.151] | -4.7 | -0.102 (91) | +0.199 (23) | 72 |
| SOLUSDT | 90 | 48% | -0.029 [-0.211, +0.177] | -2.6 | -0.094 (57) | +0.083 (33) | 54 |
| TRXUSDT | 64 | 52% | +0.123 [-0.098, +0.423] | +7.9 | +0.106 (50) | +0.184 (14) | 39 |
| XRPUSDT | 88 | 57% | +0.143 [-0.016, +0.335] | +12.6 | +0.013 (69) | +0.613 (19) | 59 |

By year: 2018 101 tr -0.211 (sum -21.3); 2019 91 tr +0.158 (sum +14.4); 2020 76 tr -0.100 (sum -7.6); 2021 86 tr +0.301 (sum +25.9); 2022 205 tr -0.087 (sum -17.7); 2023 103 tr -0.028 (sum -2.9); 2024 124 tr +0.239 (sum +29.7); 2025 105 tr +0.156 (sum +16.4)

### Rule B: **FAIL**

- p 0.4294, Holm 0.4908; checks: n_all>=100 ok, n_h1>=30 ok, n_h2>=30 ok, mean_r_h1>0 FAILED, mean_r_h2>0 ok, coins_with_mean_r>0_of_coins_with_5+_trades>=7 FAILED, holm_p<0.05 FAILED, excess_pooled>0 ok
- coins with 5+ trades: 10; with mean R > 0: 6 (BNBUSDT, DOTUSDT, LINKUSDT, LTCUSDT, TRXUSDT, XRPUSDT)
- pooled: 284, 53% won, mean +0.022 [-0.137, +0.208], p 0.429, sum +6.3R
- first half: 184, 51% won, mean -0.007 [-0.207, +0.285], p 0.562, sum -1.3R
- second half: 100, 57% won, mean +0.076 [-0.120, +0.299], p 0.241, sum +7.6R
- excess over the drift baseline: +0.209 [+0.035, +0.408]
- exits {'stop': 116, 'T1_then_entry': 28, 'T1_T2': 31, 'T1_then_time': 66, 'time': 43}; longest losing run 11; deepest fall of cumulative R -33.4R; median +0.131

| coin | trades | won | mean R [95%] | sum R | h1 mean (n) | h2 mean (n) | skipped |
|---|---|---|---|---|---|---|---|
| ADAUSDT | 25 | 44% | -0.173 [-0.488, +0.216] | -4.3 | -0.148 (18) | -0.238 (7) | 14 |
| AVAXUSDT | 43 | 53% | -0.003 [-0.251, +0.320] | -0.1 | +0.021 (26) | -0.041 (17) | 30 |
| BNBUSDT | 25 | 48% | +0.006 [-0.230, +0.471] | +0.1 | +0.093 (19) | -0.270 (6) | 13 |
| DOGEUSDT | 33 | 52% | -0.062 [-0.318, +0.238] | -2.0 | -0.018 (21) | -0.138 (12) | 18 |
| DOTUSDT | 48 | 58% | +0.085 [-0.185, +0.410] | +4.1 | +0.044 (30) | +0.153 (18) | 24 |
| LINKUSDT | 20 | 65% | +0.154 [-0.223, +0.641] | +3.1 | -0.090 (11) | +0.452 (9) | 5 |
| LTCUSDT | 16 | 56% | +0.053 [-0.426, +0.661] | +0.8 | +0.005 (11) | +0.158 (5) | 11 |
| SOLUSDT | 34 | 44% | -0.140 [-0.411, +0.191] | -4.8 | -0.155 (23) | -0.110 (11) | 21 |
| TRXUSDT | 23 | 52% | +0.145 [-0.288, +0.670] | +3.3 | +0.033 (11) | +0.247 (12) | 14 |
| XRPUSDT | 17 | 59% | +0.360 [-0.049, +0.914] | +6.1 | +0.164 (14) | +1.275 (3) | 9 |

By year: 2020 13 tr +0.175 (sum +2.3); 2021 14 tr +0.636 (sum +8.9); 2022 145 tr -0.077 (sum -11.1); 2023 31 tr -0.079 (sum -2.4); 2024 32 tr +0.193 (sum +6.2); 2025 49 tr +0.051 (sum +2.5)

## Test 2 (descriptive): BTC and ETH before Oct 2019

descriptive only; about two years on two coins is too short to decide; rule B cannot fire (no funding before 2019-09/11)

- Rule A pooled: 65, 34% won, mean -0.265 [-0.411, -0.038], p 1.000, sum -17.3R
  - BTCUSDT: 24, 38% won, mean -0.233 [-0.465, +0.190], p 0.976, sum -5.6R
  - ETHUSDT: 41, 32% won, mean -0.284 [-0.421, -0.082], p 1.000, sum -11.7R
- Rule B pooled: 0 trades
  - BTCUSDT: 0 trades
  - ETHUSDT: 0 trades

## All 12 coins x all years (descriptive; H107's trades from its results.json + tests 1 and 2)

- Rule A: 1079 trades, 52% won, mean +0.017, sum +18.8R
  - by year: 2017 1 +0.462; 2018 157 -0.245; 2019 105 +0.139; 2020 86 -0.166; 2021 104 +0.323; 2022 249 -0.128; 2023 111 -0.015; 2024 139 +0.254; 2025 127 +0.165
  - by coin: ADAUSDT 125 -0.021; AVAXUSDT 80 +0.094; BNBUSDT 81 -0.108; BTCUSDT 78 -0.100; DOGEUSDT 82 -0.001; DOTUSDT 85 +0.087; ETHUSDT 110 -0.093; LINKUSDT 82 +0.248; LTCUSDT 114 -0.041; SOLUSDT 90 -0.029; TRXUSDT 64 +0.123; XRPUSDT 88 +0.143
- Rule B: 316 trades, 53% won, mean +0.040, sum +12.5R
  - by year: 2019 1 +1.427; 2020 14 +0.162; 2021 14 +0.636; 2022 161 -0.071; 2023 32 -0.063; 2024 35 +0.247; 2025 59 +0.080
  - by coin: ADAUSDT 25 -0.173; AVAXUSDT 43 -0.003; BNBUSDT 25 +0.006; BTCUSDT 8 +0.277; DOGEUSDT 33 -0.062; DOTUSDT 48 +0.085; ETHUSDT 24 +0.166; LINKUSDT 20 +0.154; LTCUSDT 16 +0.053; SOLUSDT 34 -0.140; TRXUSDT 23 +0.145; XRPUSDT 17 +0.360

## One setting at a time on test 1 (descriptive, decides nothing)

| variant | trades | mean R | h1 mean (n) | h2 mean (n) | coins 5+ / mean > 0 |
|---|---|---|---|---|---|
| A, bounce 1.5 ATR | 1146 | +0.028 | -0.000 (805) | +0.093 (341) | 10 / 6 |
| B, bounce 1.5 ATR | 379 | +0.027 | +0.054 (247) | -0.022 (132) | 10 / 8 |
| A, bounce 2.5 ATR | 602 | +0.051 | -0.057 (401) | +0.265 (201) | 10 / 6 |
| B, bounce 2.5 ATR | 185 | +0.024 | -0.069 (117) | +0.183 (68) | 10 / 5 |
| A, drop 8% | 971 | +0.038 | -0.009 (662) | +0.138 (309) | 10 / 6 |
| B, drop 8% | 320 | +0.019 | -0.001 (205) | +0.055 (115) | 10 / 5 |
| A, drop 12% | 796 | +0.051 | -0.020 (553) | +0.212 (243) | 10 / 7 |
| B, drop 12% | 261 | +0.009 | -0.023 (175) | +0.074 (86) | 10 / 6 |
| A, hold 24h | 903 | +0.110 | +0.084 (621) | +0.167 (282) | 10 / 8 |
| B, hold 24h | 286 | +0.056 | +0.057 (186) | +0.056 (100) | 10 / 7 |
| A, hold 96h | 885 | +0.027 | -0.049 (604) | +0.190 (281) | 10 / 6 |
| B, hold 96h | 283 | +0.044 | +0.000 (183) | +0.124 (100) | 10 / 7 |

## Look-ahead guards

- (i) bars recomputed on data cut at the bar: 3492, mismatches 0
- (ii) vectorised walk against the bar-by-bar walk, largest difference over every trade: 4.44e-16 R

## Data

Total 233.2 MB in data/sources/h118/. Gates per file:

- ADAUSDT: 265035 rows 2018-04-17 04:00 .. 2025-11-10 23:45, missing bars 389 in 26 gaps (largest 10.2 h), OHLC violations 0; funding from 2020-01-19 16:00
- AVAXUSDT: 179976 rows 2020-09-22 06:30 .. 2025-11-10 23:45, missing bars 94 in 10 gaps (largest 4.8 h), OHLC violations 0; funding from 2020-09-22 16:00
- BNBUSDT: 280439 rows 2017-11-06 03:45 .. 2025-11-10 23:45, missing bars 538 in 32 gaps (largest 33.8 h), OHLC violations 0; funding from 2020-02-10 08:00
- DOGEUSDT: 222566 rows 2019-07-05 12:00 .. 2025-11-10 23:45, missing bars 202 in 18 gaps (largest 8.2 h), OHLC violations 0; funding from 2020-07-10 08:00
- DOTUSDT: 183270 rows 2020-08-18 23:00 .. 2025-11-10 23:45, missing bars 94 in 10 gaps (largest 4.8 h), OHLC violations 0; funding from 2020-08-20 08:00
- LINKUSDT: 238826 rows 2019-01-16 10:00 .. 2025-11-10 23:45, missing bars 270 in 21 gaps (largest 10.2 h), OHLC violations 0; funding from 2020-01-17 08:00
- LTCUSDT: 276890 rows 2017-12-13 03:30 .. 2025-11-10 23:45, missing bars 536 in 31 gaps (largest 33.8 h), OHLC violations 0; funding from 2020-01-09 08:00
- SOLUSDT: 184010 rows 2020-08-11 06:00 .. 2025-11-10 23:45, missing bars 94 in 10 gaps (largest 4.8 h), OHLC violations 0; funding from 2020-09-13 16:00
- TRXUSDT: 259725 rows 2018-06-11 11:30 .. 2025-11-10 23:45, missing bars 389 in 26 gaps (largest 10.2 h), OHLC violations 0; funding from 2020-01-15 08:00
- XRPUSDT: 263387 rows 2018-05-04 08:00 .. 2025-11-10 23:45, missing bars 389 in 26 gaps (largest 10.2 h), OHLC violations 0; funding from 2020-01-06 08:00
- BTCUSDT: 74469 rows 2017-08-17 04:00 .. 2019-10-05 23:45, missing bars 395 in 16 gaps (largest 33.8 h), OHLC violations 0; funding from None
- ETHUSDT: 74469 rows 2017-08-17 04:00 .. 2019-10-05 23:45, missing bars 395 in 16 gaps (largest 33.8 h), OHLC violations 0; funding from None
