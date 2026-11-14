# Workstream M: the intraday mind on history (IN-SAMPLE, not proof)

Written by `research/intraday_study.py` on 2026-11-11 08:46 UTC. Groups: crypto, metals, fx, index, energy. Paper only. A history read can reject an idea, never prove one; forward results decide (docs/CHARTER.md). See docs/INTRADAY.md for the plain-English summary.

- crypto: 2020-01-01 00:00 to 2026-11-11 08:15 UTC, halves split at 2023-06-07 04:07 (348.8s, peak 1294 MB)
- metals: 2020-01-01 23:00 to 2026-11-11 08:00 UTC, halves split at 2023-06-07 04:00 (134.9s, peak 909 MB)
- fx: 2020-01-01 22:00 to 2026-11-11 08:00 UTC, halves split at 2023-06-07 04:00 (159.9s, peak 670 MB)
- index: 2020-01-02 14:30 to 2026-11-10 20:45 UTC, halves split at 2023-06-06 22:22 (254.7s, peak 273 MB)
- energy: 2020-01-02 01:00 to 2026-11-11 08:00 UTC, halves split at 2023-06-07 04:00 (95.6s, peak 782 MB)

## M1: skill per horizon, per market, both halves

Hit = direction right on calls graded up or down; edge hit = the same on calls with a 5-point claimed edge; skill = log-loss gain over the base rate (%). 24h = the main engine's question asked of the same voting voices.

| Market | Horizon | Neither % | Skill 1st / 2nd | Hit 1st / 2nd | Edge hit 1st / 2nd | Edge calls 1st / 2nd | |edge| p95, pts |
|---|---|---|---|---|---|---|---|
| BTCUSDT | 1h | 61.4 | 0.40 / 0.25 | 55.3 / 54.2 | 57.2 / 54.4 | 5499 / 3929 | 5.1 |
| BTCUSDT | 4h | 32.0 | 0.09 / 0.09 | 51.9 / 51.2 | 52.5 / 53.5 | 11780 / 7590 | 6.0 |
| BTCUSDT | 24h | 6.4 | 0.02 / 0.06 | 51.0 / 50.6 | 51.8 / 51.1 | 31562 / 24483 | 9.6 |
| ETHUSDT | 1h | 61.6 | 0.44 / 0.33 | 55.4 / 55.2 | 58.3 / 56.4 | 5920 / 3856 | 5.1 |
| ETHUSDT | 4h | 30.7 | 0.07 / 0.16 | 51.3 / 52.0 | 53.4 / 55.2 | 12156 / 7531 | 6.1 |
| ETHUSDT | 24h | 5.0 | -0.12 / 0.11 | 50.5 / 50.9 | 50.9 / 52.4 | 31150 / 25572 | 9.9 |
| XAUUSD | 1h | 60.2 | 0.05 / 0.08 | 51.3 / 50.8 | - / - | 0 / 0 | 1.9 |
| XAUUSD | 4h | 29.2 | -0.01 / 0.04 | 50.8 / 50.8 | 48.3 / 50.0 | 1111 / 780 | 3.6 |
| XAUUSD | 24h | 2.0 | -0.18 / -0.02 | 49.5 / 50.3 | 47.7 / 45.1 | 12280 / 780 | 3.6 |
| XAGUSD | 1h | 61.2 | 0.05 / 0.12 | 50.9 / 52.9 | - / - | 0 / 0 | 1.9 |
| XAGUSD | 4h | 30.6 | 0.03 / 0.10 | 50.3 / 51.0 | 47.9 / 58.3 | 1219 / 1122 | 4.0 |
| XAGUSD | 24h | 2.5 | -0.21 / -0.02 | 48.2 / 49.8 | 47.6 / 52.0 | 13938 / 1672 | 4.2 |
| USDJPY | 1h | 59.8 | 0.04 / 0.24 | 51.8 / 50.5 | 37.9 / - | 29 / 0 | 2.0 |
| USDJPY | 4h | 28.1 | -0.02 / 0.16 | 50.7 / 50.0 | 55.3 / 0.0 | 901 / 2 | 2.4 |
| USDJPY | 24h | 3.0 | -0.10 / -0.05 | 49.8 / 49.7 | 48.1 / 40.7 | 7182 / 1775 | 4.3 |
| SPX | 1h | 59.0 | 0.81 / 1.12 | 51.9 / 52.7 | 44.4 / 48.3 | 18 / 58 | 3.4 |
| SPX | 4h | 22.5 | 0.47 / 0.75 | 50.2 / 49.8 | 47.9 / 43.5 | 192 / 23 | 2.5 |
| SPX | 24h | 0.6 | -0.20 / 0.02 | 49.0 / 51.2 | 43.2 / 52.1 | 2317 / 3465 | 7.8 |
| WTI | 1h | 57.8 | 0.07 / 0.03 | 49.1 / 49.1 | 55.6 / - | 54 / 0 | 1.3 |
| WTI | 4h | 29.5 | 0.01 / -0.05 | 50.2 / 49.4 | 48.3 / 46.7 | 6913 / 1128 | 3.7 |
| WTI | 24h | 1.2 | -0.30 / -0.34 | 50.0 / 50.1 | 50.2 / 49.5 | 32973 / 15479 | 16.0 |
| BRENT | 1h | 57.6 | 0.08 / 0.05 | 49.1 / 49.1 | 56.9 / - | 51 / 0 | 1.4 |
| BRENT | 4h | 28.8 | -0.01 / -0.04 | 50.1 / 49.4 | 49.7 / 47.4 | 6094 / 1132 | 3.7 |
| BRENT | 24h | 1.1 | -0.36 / -0.49 | 50.2 / 49.8 | 50.4 / 47.4 | 32433 / 15726 | 16.0 |

### Edge hit rate by session (1st / 2nd half)

| Market | Horizon | asia | london | overlap | ny |
|---|---|---|---|---|---|
| BTCUSDT | 1h | 58.1 / 55.9 | 60.0 / 52.6 | 53.3 / 54.8 | 57.3 / 53.4 |
| BTCUSDT | 4h | 53.0 / 55.1 | 47.8 / 51.4 | 53.1 / 52.6 | 55.2 / 53.3 |
| ETHUSDT | 1h | 59.5 / 56.4 | 62.4 / 56.4 | 55.4 / 55.5 | 56.1 / 56.9 |
| ETHUSDT | 4h | 54.5 / 55.9 | 51.9 / 51.5 | 54.3 / 55.9 | 52.3 / 56.3 |
| XAUUSD | 1h | - / - | - / - | - / - | - / - |
| XAUUSD | 4h | 43.4 / 45.0 | 55.3 / 63.9 | 52.1 / 42.0 | 45.1 / 50.0 |
| XAGUSD | 1h | - / - | - / - | - / - | - / - |
| XAGUSD | 4h | 44.7 / 59.2 | 59.7 / 65.2 | 50.2 / 44.4 | 38.1 / 61.7 |
| USDJPY | 1h | 25.0 / - | 20.0 / - | 41.7 / - | 100.0 / - |
| USDJPY | 4h | 61.5 / 0.0 | 62.7 / - | 40.5 / - | 40.0 / - |
| SPX | 1h | - / - | - / - | 57.1 / 66.7 | 36.4 / 41.9 |
| SPX | 4h | 100.0 / - | - / - | 33.3 / 50.0 | 52.9 / 41.2 |
| WTI | 1h | 0.0 / - | 92.3 / - | 46.7 / - | 57.1 / - |
| WTI | 4h | 52.0 / 46.7 | 43.3 / 42.1 | 46.9 / 50.4 | 52.7 / 48.6 |
| BRENT | 1h | 20.0 / - | 50.0 / - | 65.0 / - | 64.3 / - |
| BRENT | 4h | 53.9 / 42.1 | 45.0 / 41.4 | 48.4 / 51.4 | 52.0 / 55.8 |

### Edge hit rate by regime, 1h and 4h minds (1st / 2nd half, calls in 2nd)

- BTCUSDT 1h: MOMENTUM_DOWN 47.1 / 44.3 (158); MOMENTUM_UP 54.2 / 44.3 (88); RANGE 57.1 / 54.0 (1740); TRANSITION 58.8 / 57.0 (1204); TREND_DOWN 56.5 / 62.3 (239); TREND_UP 58.7 / 50.6 (500)
- ETHUSDT 1h: MOMENTUM_DOWN 55.4 / 50.5 (188); MOMENTUM_UP 57.8 / 50.7 (144); RANGE 57.9 / 57.5 (1845); TRANSITION 58.5 / 57.1 (1227); TREND_DOWN 61.3 / 59.8 (261); TREND_UP 59.2 / 46.6 (191)
- BTCUSDT 4h: MOMENTUM_DOWN 51.2 / 49.9 (795); MOMENTUM_UP 46.3 / 47.2 (320); RANGE 52.6 / 53.7 (3171); TRANSITION 52.7 / 52.8 (1741); TREND_DOWN 55.1 / 59.4 (1034); TREND_UP 51.7 / 51.4 (529)
- ETHUSDT 4h: MOMENTUM_DOWN 51.8 / 55.1 (902); MOMENTUM_UP 49.1 / 46.9 (333); RANGE 50.9 / 56.7 (2959); TRANSITION 57.7 / 53.9 (2161); TREND_DOWN 54.1 / 59.5 (922); TREND_UP 56.8 / 46.1 (254)
- XAUUSD 1h: MOMENTUM_DOWN - / - (0); MOMENTUM_UP - / - (0); RANGE - / - (0); TRANSITION - / - (0); TREND_DOWN - / - (0); TREND_UP - / - (0)
- XAGUSD 1h: MOMENTUM_DOWN - / - (0); MOMENTUM_UP - / - (0); RANGE - / - (0); TRANSITION - / - (0); TREND_DOWN - / - (0); TREND_UP - / - (0)
- XAUUSD 4h: MOMENTUM_DOWN 51.7 / - (0); MOMENTUM_UP 0.0 / - (0); RANGE 44.4 / 50.1 (419); TRANSITION 51.1 / 48.4 (333); TREND_DOWN - / 69.2 (26); TREND_UP 48.9 / 50.0 (2)
- XAGUSD 4h: MOMENTUM_DOWN 54.6 / 0.0 (1); MOMENTUM_UP 41.7 / - (0); RANGE 53.4 / 53.2 (421); TRANSITION 40.9 / 63.5 (476); TREND_DOWN 2.4 / 54.8 (104); TREND_UP 60.3 / 59.2 (120)
- USDJPY 1h: RANGE 30.8 / - (0); TRANSITION 45.5 / - (0); TREND_DOWN - / - (0); TREND_UP 40.0 / - (0)
- USDJPY 4h: RANGE 54.2 / - (0); TRANSITION 52.4 / - (0); TREND_DOWN 50.0 / 0.0 (2); TREND_UP 60.2 / - (0)
- SPX 1h: MOMENTUM_DOWN - / 100.0 (1); MOMENTUM_UP - / - (0); RANGE 100.0 / 44.4 (9); TRANSITION 41.2 / 47.8 (46); TREND_DOWN - / - (0); TREND_UP - / 50.0 (2)
- SPX 4h: MOMENTUM_DOWN - / - (0); MOMENTUM_UP - / - (0); RANGE 45.7 / 0.0 (4); TRANSITION 50.4 / 52.9 (17); TREND_DOWN 0.0 / - (0); TREND_UP - / 50.0 (2)
- WTI 1h: MOMENTUM_DOWN - / - (0); MOMENTUM_UP - / - (0); RANGE - / - (0); TRANSITION 56.6 / - (0); TREND_DOWN 0.0 / - (0); TREND_UP - / - (0)
- BRENT 1h: MOMENTUM_DOWN - / - (0); MOMENTUM_UP - / - (0); RANGE 50.0 / - (0); TRANSITION 58.7 / - (0); TREND_DOWN 0.0 / - (0); TREND_UP - / - (0)
- WTI 4h: MOMENTUM_DOWN 36.2 / - (0); MOMENTUM_UP 45.4 / 39.1 (69); RANGE 45.8 / 55.6 (115); TRANSITION 50.5 / 47.6 (489); TREND_DOWN 59.9 / - (0); TREND_UP 45.3 / 44.6 (455)
- BRENT 4h: MOMENTUM_DOWN 37.2 / - (0); MOMENTUM_UP 44.0 / 27.0 (37); RANGE 49.7 / 51.2 (129); TRANSITION 54.5 / 47.6 (617); TREND_DOWN 51.6 / - (0); TREND_UP 42.4 / 47.9 (349)

### Which voices know the next hours (each fitted alone on the 1st half, scored on the 2nd)

Log-loss skill % (mostly knowing WHETHER price will move: the 'neither' class) and the direction hit % on calls graded up or down (knowing WHICH WAY). Top 6 of each.

- crypto, 1h: skill risk +3.76, candles +3.75, clock +2.46, trendq +1.26, trend +0.30, levels +0.29; direction trend 54.5%, meanrev 54.3%, momentum 54.2%, flow 54.1%, trendq 54.0%, mavg 53.7%
- crypto, 4h: skill clock +3.02, risk +1.95, candles +1.88, trendq +0.55, breadth +0.14, trend +0.09; direction meanrev 52.1%, trendq 52.0%, intraday 52.0%, structure 51.8%, mavg 51.7%, trend 51.6%
- crypto, 24h: skill clock +2.17, candles +0.71, risk +0.66, basis +0.13, mavg +0.12, flow +0.11; direction mavg 51.6%, trendq 51.4%, intraday 51.4%, structure 51.3%, cbprem 51.2%, fib 51.0%
- metals, 1h: skill risk +4.86, candles +4.02, clock +2.55, trendq +0.27, trend +0.11, mavg +0.08; direction regime 52.3%, owner 52.3%, cross 52.0%, levels 51.9%, trend 51.8%, trendq 51.8%
- metals, 4h: skill clock +3.11, risk +1.80, candles +1.18, trendq +0.26, macro +0.09, momentum +0.06; direction trendq 51.4%, regime 51.3%, owner 51.3%, intraday 51.0%, pullback 51.0%, mavg 51.0%
- metals, 24h: skill risk +0.23, candles +0.21, meanrev +0.06, trendq +0.05, pullback +0.03, mavg +0.03; direction rates 51.6%, risk 51.0%, trendq 51.0%, mavg 50.9%, meanrev 50.8%, levels 50.7%
- fx, 1h: skill risk +3.49, candles +3.12, clock +0.57, trendq +0.36, intraday +0.23, levels +0.19; direction intraday 51.5%, rates 51.2%, cot 51.2%, cross 51.1%, owner 51.1%, mavg 50.9%
- fx, 4h: skill clock +3.31, risk +1.00, candles +0.90, trend +0.15, trendq +0.12, intraday +0.10; direction candles 50.8%, volx 50.8%, intraday 50.6%, setups 50.6%, pullback 50.5%, rates 50.5%
- fx, 24h: skill risk +0.04, intraday +0.04, strategies +0.03, pullback +0.00, cross -0.00, owner -0.00; direction trend 51.1%, clock 51.0%, structure 50.9%, volx 50.8%, levels 50.7%, intraday 50.7%
- index, 1h: skill trendq +1.63, candles +1.53, risk +1.37, meanrev +1.07, structure +0.99, levels +0.92; direction levels 53.6%, pullback 52.7%, macro 52.0%, cross 51.7%, trendq 51.7%, owner 51.7%
- index, 4h: skill clock +1.45, meanrev +1.30, trendq +1.28, structure +1.13, momentum +1.02, mavg +0.89; direction fib 51.8%, strategies 51.8%, overnight 51.1%, rates 51.1%, pullback 50.6%, setups 50.6%
- index, 24h: skill rates +0.27, pullback +0.18, strategies +0.17, regime +0.12, fib +0.07, intraday +0.06; direction pullback 52.6%, strategies 52.6%, rates 51.4%, cot 51.0%, risk 50.9%, intraday 50.8%
- energy, 1h: skill clock +11.62, risk +7.04, candles +6.82, trendq +0.53, macro +0.08, owner -0.00; direction risk 51.7%, structure 51.0%, candles 50.7%, meanrev 50.6%, levels 50.4%, clock 50.4%
- energy, 4h: skill clock +12.24, risk +3.42, candles +2.65, macro +0.07, owner +0.00, pullback -0.07; direction risk 51.8%, levels 50.8%, candles 50.4%, trendq 50.3%, meanrev 50.2%, setups 50.2%
- energy, 24h: skill risk +0.12, candles +0.11, owner -0.00, setups -0.01, intraday -0.05, cross -0.06; direction levels 50.7%, intraday 50.4%, trendq 50.2%, structure 50.1%, meanrev 50.0%, fib 49.9%

## M2: how often the expected value after costs clears the margin

EV = P(win) - P(loss) - round trip / risk, in R, with a 1-barrier stop and target. Share of sessions (%).

| Market | Mind | Round trip | Median barrier | Median cost in R | >=0 1st / 2nd | >=0.05 1st / 2nd | >=0.10 1st / 2nd |
|---|---|---|---|---|---|---|---|
| BTCUSDT | 1h | 0.200% | 0.544% | 0.368 | 0.09 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| ETHUSDT | 1h | 0.200% | 0.722% | 0.277 | 0.28 / 0.01 | 0.00 / 0.00 | 0.00 / 0.00 |
| BTCUSDT | 4h | 0.200% | 0.725% | 0.276 | 1.42 / 0.11 | 0.28 / 0.04 | 0.02 / 0.00 |
| ETHUSDT | 4h | 0.200% | 0.962% | 0.208 | 2.58 / 0.45 | 0.70 / 0.13 | 0.08 / 0.02 |
| XAUUSD | 1h | 0.040% | 0.198% | 0.202 | 0.00 / 0.03 | 0.00 / 0.00 | 0.00 / 0.00 |
| XAGUSD | 1h | 0.060% | 0.405% | 0.148 | 0.00 / 0.11 | 0.00 / 0.00 | 0.00 / 0.00 |
| XAUUSD | 4h | 0.040% | 0.265% | 0.151 | 0.83 / 0.52 | 0.16 / 0.00 | 0.00 / 0.00 |
| XAGUSD | 4h | 0.060% | 0.540% | 0.111 | 1.54 / 1.20 | 0.27 / 0.00 | 0.00 / 0.00 |
| USDJPY | 1h | 0.020% | 0.098% | 0.204 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| USDJPY | 4h | 0.020% | 0.131% | 0.153 | 0.13 / 0.01 | 0.00 / 0.00 | 0.00 / 0.00 |
| SPX | 1h | 0.040% | 0.300% | 0.133 | 0.00 / 0.23 | 0.00 / 0.00 | 0.00 / 0.00 |
| SPX | 4h | 0.040% | 0.400% | 0.100 | 1.24 / 0.11 | 0.00 / 0.00 | 0.00 / 0.00 |
| WTI | 1h | 0.080% | 0.476% | 0.168 | 0.49 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| BRENT | 1h | 0.080% | 0.442% | 0.181 | 0.20 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| WTI | 4h | 0.080% | 0.635% | 0.126 | 4.99 / 0.30 | 0.27 / 0.00 | 0.00 / 0.00 |
| BRENT | 4h | 0.080% | 0.590% | 0.136 | 3.12 / 0.20 | 0.01 / 0.00 | 0.00 / 0.00 |

## M3/M4: the swing book (48 variants tried: 24 per mind)

Variant = stop | target | target R | EV margin. Pooled over every market; R per trade before and after costs.

### 1h mind: every variant

| Variant | Trades 1st | Avg R gross 1st | Avg R net 1st | PF net 1st | Trades 2nd | Avg R gross 2nd | Avg R net 2nd | PF net 2nd |
|---|---|---|---|---|---|---|---|---|
| barrier|r|1.0|0.00 | 266 | -0.074 | -0.124 | 0.75 | 77 | +0.044 | +0.011 | 1.03 |
| barrier|r|1.0|0.05 | 1 | -1.000 | -1.032 | 0.00 | 0 | - | - | - |
| barrier|r|1.0|0.10 | 0 | - | - | - | 0 | - | - | - |
| barrier|r|1.5|0.00 | 221 | -0.116 | -0.167 | 0.71 | 63 | +0.086 | +0.053 | 1.11 |
| barrier|r|1.5|0.05 | 1 | -1.000 | -1.032 | 0.00 | 0 | - | - | - |
| barrier|r|1.5|0.10 | 0 | - | - | - | 0 | - | - | - |
| barrier|r|2.0|0.00 | 205 | -0.048 | -0.098 | 0.83 | 50 | +0.050 | +0.016 | 1.03 |
| barrier|r|2.0|0.05 | 1 | -1.000 | -1.032 | 0.00 | 0 | - | - | - |
| barrier|r|2.0|0.10 | 0 | - | - | - | 0 | - | - | - |
| barrier|reach|1.5|0.00 | 221 | -0.116 | -0.167 | 0.71 | 63 | +0.086 | +0.053 | 1.11 |
| barrier|reach|1.5|0.05 | 1 | -1.000 | -1.032 | 0.00 | 0 | - | - | - |
| barrier|reach|1.5|0.10 | 0 | - | - | - | 0 | - | - | - |
| structure|r|1.0|0.00 | 296 | -0.080 | -0.128 | 0.73 | 91 | +0.095 | +0.064 | 1.17 |
| structure|r|1.0|0.05 | 1 | -1.000 | -1.032 | 0.00 | 0 | - | - | - |
| structure|r|1.0|0.10 | 0 | - | - | - | 0 | - | - | - |
| structure|r|1.5|0.00 | 252 | -0.121 | -0.169 | 0.69 | 74 | +0.086 | +0.054 | 1.12 |
| structure|r|1.5|0.05 | 1 | -1.000 | -1.032 | 0.00 | 0 | - | - | - |
| structure|r|1.5|0.10 | 0 | - | - | - | 0 | - | - | - |
| structure|r|2.0|0.00 | 234 | -0.062 | -0.109 | 0.80 | 64 | +0.093 | +0.061 | 1.12 |
| structure|r|2.0|0.05 | 1 | -1.000 | -1.032 | 0.00 | 0 | - | - | - |
| structure|r|2.0|0.10 | 0 | - | - | - | 0 | - | - | - |
| structure|reach|1.5|0.00 | 252 | -0.121 | -0.169 | 0.69 | 74 | +0.086 | +0.054 | 1.12 |
| structure|reach|1.5|0.05 | 1 | -1.000 | -1.032 | 0.00 | 0 | - | - | - |
| structure|reach|1.5|0.10 | 0 | - | - | - | 0 | - | - | - |

### 4h mind: every variant

| Variant | Trades 1st | Avg R gross 1st | Avg R net 1st | PF net 1st | Trades 2nd | Avg R gross 2nd | Avg R net 2nd | PF net 2nd |
|---|---|---|---|---|---|---|---|---|
| barrier|r|1.0|0.00 | 1862 | -0.002 | -0.062 | 0.88 | 506 | -0.011 | -0.065 | 0.87 |
| barrier|r|1.0|0.05 | 366 | -0.044 | -0.100 | 0.81 | 45 | -0.158 | -0.236 | 0.61 |
| barrier|r|1.0|0.10 | 51 | -0.180 | -0.227 | 0.62 | 9 | -0.270 | -0.332 | 0.49 |
| barrier|r|1.5|0.00 | 1421 | -0.003 | -0.063 | 0.89 | 402 | -0.015 | -0.071 | 0.87 |
| barrier|r|1.5|0.05 | 293 | -0.068 | -0.125 | 0.79 | 40 | -0.204 | -0.283 | 0.59 |
| barrier|r|1.5|0.10 | 42 | -0.154 | -0.201 | 0.70 | 7 | -0.366 | -0.429 | 0.37 |
| barrier|r|2.0|0.00 | 1199 | -0.005 | -0.065 | 0.89 | 350 | -0.007 | -0.064 | 0.89 |
| barrier|r|2.0|0.05 | 258 | -0.131 | -0.188 | 0.70 | 39 | -0.139 | -0.218 | 0.69 |
| barrier|r|2.0|0.10 | 43 | -0.160 | -0.207 | 0.70 | 7 | -0.295 | -0.357 | 0.47 |
| barrier|reach|1.5|0.00 | 1502 | +0.001 | -0.059 | 0.89 | 420 | -0.025 | -0.081 | 0.85 |
| barrier|reach|1.5|0.05 | 309 | -0.023 | -0.081 | 0.85 | 42 | -0.176 | -0.255 | 0.61 |
| barrier|reach|1.5|0.10 | 45 | -0.135 | -0.181 | 0.71 | 7 | -0.389 | -0.451 | 0.34 |
| structure|r|1.0|0.00 | 1969 | +0.004 | -0.054 | 0.89 | 566 | -0.011 | -0.064 | 0.87 |
| structure|r|1.0|0.05 | 385 | -0.024 | -0.079 | 0.84 | 47 | -0.164 | -0.242 | 0.60 |
| structure|r|1.0|0.10 | 53 | -0.165 | -0.211 | 0.64 | 9 | -0.270 | -0.332 | 0.49 |
| structure|r|1.5|0.00 | 1519 | +0.002 | -0.056 | 0.90 | 464 | -0.001 | -0.055 | 0.90 |
| structure|r|1.5|0.05 | 305 | -0.041 | -0.096 | 0.83 | 42 | -0.209 | -0.287 | 0.57 |
| structure|r|1.5|0.10 | 44 | -0.126 | -0.172 | 0.73 | 7 | -0.366 | -0.429 | 0.37 |
| structure|r|2.0|0.00 | 1298 | +0.004 | -0.055 | 0.90 | 403 | -0.010 | -0.065 | 0.88 |
| structure|r|2.0|0.05 | 271 | -0.100 | -0.156 | 0.74 | 41 | -0.147 | -0.225 | 0.67 |
| structure|r|2.0|0.10 | 45 | -0.121 | -0.167 | 0.75 | 7 | -0.295 | -0.357 | 0.47 |
| structure|reach|1.5|0.00 | 1606 | +0.002 | -0.057 | 0.89 | 478 | -0.019 | -0.074 | 0.86 |
| structure|reach|1.5|0.05 | 327 | -0.005 | -0.061 | 0.88 | 44 | -0.182 | -0.260 | 0.59 |
| structure|reach|1.5|0.10 | 47 | -0.116 | -0.162 | 0.73 | 7 | -0.389 | -0.451 | 0.34 |

### 1h mind: no variant chosen

No variant reached 300 first-half trades over all markets (most: 296); the pre-declared rule (intraday.SWING_RULES) stands.

### 4h mind: chosen on the 1st half: `structure|r|1.0|0.00`

Pooled: 1st half 1969 trades, -0.054 R net (+0.004 gross); 2nd half 566 trades, -0.064 R net (-0.011 gross).

| Market | Session | Trades 1st / 2nd | Win % 1st / 2nd | Avg R gross 1st / 2nd | Avg R net 1st / 2nd | PF net 1st / 2nd | Net % per trade 1st / 2nd |
|---|---|---|---|---|---|---|---|
| BTCUSDT | all | 301 / 40 | 49.2 / 47.5 | +0.024 / -0.045 | -0.059 / -0.150 | 0.88 / 0.73 | -0.2998 / -0.3834 |
| BTCUSDT | asia | 127 / 17 | 48.0 / 52.9 | +0.014 / +0.059 | -0.072 / -0.048 | 0.85 / 0.90 | -0.4473 / -0.2191 |
| BTCUSDT | london | 63 / 6 | 52.4 / 33.3 | +0.072 / -0.303 | -0.011 / -0.402 | 0.98 / 0.43 | -0.0678 / -0.6050 |
| BTCUSDT | overlap | 55 / 12 | 50.9 / 50.0 | +0.033 / +0.000 | -0.046 / -0.105 | 0.90 / 0.81 | -0.1546 / -0.2848 |
| BTCUSDT | ny | 56 / 5 | 46.4 / 40.0 | -0.014 / -0.200 | -0.095 / -0.298 | 0.80 / 0.54 | -0.3691 / -0.9133 |
| ETHUSDT | all | 534 / 137 | 48.7 / 48.2 | +0.015 / -0.027 | -0.055 / -0.119 | 0.88 / 0.76 | -0.2613 / -0.3546 |
| ETHUSDT | asia | 219 / 59 | 48.4 / 47.5 | -0.009 / -0.072 | -0.080 / -0.162 | 0.83 / 0.69 | -0.3233 / -0.4320 |
| ETHUSDT | london | 104 / 21 | 56.7 / 47.6 | +0.149 / -0.006 | +0.077 / -0.096 | 1.18 / 0.80 | +0.1018 / -0.1961 |
| ETHUSDT | overlap | 101 / 21 | 43.6 / 42.9 | -0.074 / -0.120 | -0.140 / -0.211 | 0.74 / 0.63 | -0.6220 / -0.7516 |
| ETHUSDT | ny | 110 / 36 | 46.4 / 52.8 | +0.018 / +0.089 | -0.053 / -0.009 | 0.89 / 0.98 | -0.1502 / -0.0885 |
| XAUUSD | all | 101 / 93 | 45.5 / 48.4 | -0.038 / +0.004 | -0.085 / -0.030 | 0.83 / 0.93 | -0.0726 / -0.0252 |
| XAUUSD | asia | 32 / 32 | 31.2 / 43.8 | -0.292 / -0.090 | -0.344 / -0.125 | 0.43 / 0.76 | -0.2507 / -0.0265 |
| XAUUSD | london | 25 / 22 | 48.0 / 50.0 | +0.082 / +0.023 | +0.036 / -0.010 | 1.09 / 0.98 | +0.0144 / -0.1046 |
| XAUUSD | overlap | 24 / 19 | 62.5 / 57.9 | +0.259 / +0.154 | +0.217 / +0.116 | 1.60 / 1.30 | +0.1414 / +0.0927 |
| XAUUSD | ny | 20 / 20 | 45.0 / 45.0 | -0.138 / -0.008 | -0.183 / -0.041 | 0.70 / 0.91 | -0.1531 / -0.0481 |
| XAGUSD | all | 189 / 199 | 45.0 / 51.8 | -0.058 / +0.055 | -0.098 / +0.021 | 0.80 / 1.05 | -0.1127 / +0.0593 |
| XAGUSD | asia | 78 / 71 | 46.2 / 49.3 | -0.081 / -0.020 | -0.122 / -0.051 | 0.76 / 0.90 | -0.1186 / -0.1437 |
| XAGUSD | london | 27 / 38 | 63.0 / 52.6 | +0.324 / +0.123 | +0.289 / +0.090 | 1.93 / 1.21 | +0.4750 / +0.1155 |
| XAGUSD | overlap | 48 / 42 | 43.8 / 52.4 | -0.026 / +0.057 | -0.068 / +0.021 | 0.86 / 1.05 | -0.0190 / +0.1010 |
| XAGUSD | ny | 36 / 48 | 30.6 / 54.2 | -0.334 / +0.110 | -0.377 / +0.075 | 0.40 / 1.20 | -0.6656 / +0.2786 |
| USDJPY | all | 27 / 4 | 55.6 / 25.0 | +0.125 / -0.341 | +0.072 / -0.376 | 1.20 / 0.39 | +0.0300 / -0.1800 |
| USDJPY | asia | 8 / 1 | 62.5 / 0.0 | +0.147 / -0.363 | +0.085 / -0.399 | 1.28 / 0.00 | +0.0121 / -0.2186 |
| USDJPY | london | 6 / 1 | 66.7 / 0.0 | +0.231 / -1.000 | +0.180 / -1.032 | 1.51 / 0.00 | +0.0785 / -0.6405 |
| USDJPY | overlap | 6 / 1 | 33.3 / 0.0 | -0.228 / -1.000 | -0.280 / -1.043 | 0.53 / 0.00 | -0.0950 / -0.4854 |
| USDJPY | ny | 7 / 1 | 57.1 / 100.0 | +0.314 / +1.000 | +0.267 / +0.969 | 2.21 / - | +0.1160 / +0.6245 |
| SPX | all | 68 / 6 | 47.1 / 33.3 | -0.074 / -0.278 | -0.120 / -0.298 | 0.77 / 0.52 | -0.0913 / -0.5540 |
| SPX | asia | 0 / 0 | - / - | - / - | - / - | - / - | - / - |
| SPX | london | 0 / 0 | - / - | - / - | - / - | - / - | - / - |
| SPX | overlap | 34 / 3 | 47.1 / 66.7 | -0.029 / +0.333 | -0.075 / +0.314 | 0.83 / 1.92 | -0.0466 / +0.6414 |
| SPX | ny | 34 / 3 | 47.1 / 0.0 | -0.120 / -0.890 | -0.164 / -0.911 | 0.73 / 0.00 | -0.1360 / -1.7494 |
| WTI | all | 436 / 49 | 51.4 / 46.9 | +0.032 / -0.097 | -0.012 / -0.131 | 0.97 / 0.74 | +0.0895 / -0.5621 |
| WTI | asia | 96 / 14 | 52.1 / 28.6 | +0.056 / -0.423 | +0.014 / -0.460 | 1.03 / 0.26 | -0.0306 / -1.4201 |
| WTI | london | 79 / 10 | 53.2 / 40.0 | +0.083 / -0.191 | +0.039 / -0.226 | 1.08 / 0.63 | +0.1995 / -0.5407 |
| WTI | overlap | 140 / 11 | 44.3 / 54.5 | -0.115 / -0.022 | -0.160 / -0.054 | 0.73 / 0.88 | +0.0226 / -0.7550 |
| WTI | ny | 121 / 14 | 57.9 / 64.3 | +0.148 / +0.238 | +0.104 / +0.204 | 1.25 / 1.55 | +0.1902 / +0.4323 |
| BRENT | all | 313 / 38 | 48.2 / 44.7 | -0.015 / -0.108 | -0.068 / -0.143 | 0.86 / 0.74 | -0.0633 / -0.5403 |
| BRENT | asia | 72 / 14 | 43.1 / 50.0 | -0.084 / -0.059 | -0.138 / -0.093 | 0.70 / 0.82 | -0.3481 / -0.4721 |
| BRENT | london | 80 / 4 | 53.8 / 50.0 | +0.085 / +0.000 | +0.033 / -0.042 | 1.07 / 0.92 | +0.4651 / +0.0440 |
| BRENT | overlap | 86 / 7 | 43.0 / 28.6 | -0.124 / -0.429 | -0.177 / -0.454 | 0.69 / 0.38 | -0.2414 / -1.4360 |
| BRENT | ny | 75 / 13 | 53.3 / 46.2 | +0.070 / -0.021 | +0.019 / -0.060 | 1.04 / 0.87 | -0.1494 / -0.3113 |

By regime (pooled, avg R net 1st / 2nd): MOMENTUM_DOWN -0.022 / -0.091; MOMENTUM_UP -0.073 / -0.052; RANGE -0.078 / -0.131; TRANSITION -0.053 / -0.058; TREND_DOWN -0.064 / +0.138; TREND_UP -0.028 / -0.122

Market x session cells positive after costs in BOTH halves (>= 30 trades each): none. Picked after looking, out of 40 cells: leads for forward grading, not findings.

