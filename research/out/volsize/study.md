# H52: size by expected move (volatility-forecast sizing), entries and exits unchanged

Registered 2026-11-16 09:50 UTC (research/hypotheses_pending/H52.md) before any code or number. PAPER RESEARCH ONLY. Development rows before 2025-11-11 00:00 UTC; results from 2020-01-01; first half before 2023-06-07, second half from it. Capital $10,000 a market, not compounded; each market's own fee a side. Sharpe on daily marked P&L over calendar days, sqrt(365). Return and max drawdown are exposure-matched to S0 per (market, half); Sharpe and return/DD are scale-free.

## Verdict

**NO PASS** on the primary stream (the main book's replayed trades). Chosen on the first half: **S3** (half-strength inverse volatility, w = clip(sqrt(m / sigma), 0.25, 4)). Variants passing the full bar in both halves: none.

## 1. Forecast quality

sigma = sqrt(B x mean of (v1, v5, v22)), equal-weight HAR of 15m squared log returns; vs the next valid day's (high - low) / close. Pooled = mean of the 8 per-market Spearman correlations: first half 0.561, second half 0.435.

| market | B | fee a side | Spearman 1st | Spearman 2nd | Pearson(log) 1st | Pearson(log) 2nd | days 1st / 2nd |
|---|---|---|---|---|---|---|---|
| BTCUSDT | 96 | 0.00100 | 0.551 | 0.389 | 0.596 | 0.398 | 1253 / 888 |
| ETHUSDT | 96 | 0.00100 | 0.567 | 0.449 | 0.607 | 0.486 | 1253 / 888 |
| XAUUSD | 92 | 0.00020 | 0.351 | 0.487 | 0.437 | 0.551 | 885 / 628 |
| XAGUSD | 92 | 0.00030 | 0.450 | 0.344 | 0.521 | 0.379 | 885 / 628 |
| USDJPY | 96 | 0.00010 | 0.643 | 0.487 | 0.652 | 0.500 | 892 / 630 |
| SPX | 26 | 0.00020 | 0.669 | 0.467 | 0.698 | 0.550 | 863 / 609 |
| WTI | 92 | 0.00040 | 0.624 | 0.425 | 0.726 | 0.441 | 885 / 628 |
| BRENT | 84 | 0.00040 | 0.632 | 0.434 | 0.707 | 0.453 | 886 / 628 |

## 2. Primary stream: the main book's own replayed trades

Replay: {"engine_version": "think15-v5.2.3", "cut": "rows before 2025-11-11 00:00 UTC", "written_utc": "2026-11-16 10:10:32", "rule": "main (hold to stop or flip)"}

Trades per market (closed / open at the seal): BTCUSDT 235 +1, ETHUSDT 202 +1, XAUUSD 110 +1, XAGUSD 150 +1, USDJPY 70 +1, SPX 33 +1, WTI 113 +1, BRENT 121 +1

### first half, pooled (8 markets, $80,000)

| variant | Sharpe | return % | max DD % | return/DD | avg exposure | trades | JK z | JK p |
|---|---|---|---|---|---|---|---|---|
| S0 | 1.121 | 99.31 | 20.46 | 4.85 | 0.920 | 699 | - | - |
| S1 | 0.793 | 62.81 | 20.66 | 3.04 | 0.876 | 699 | -1.60 | 0.1090 |
| S2 | 0.600 | 48.20 | 21.46 | 2.25 | 0.936 | 699 | -1.64 | 0.1004 |
| S3 | 0.931 | 75.98 | 19.80 | 3.84 | 0.881 | 699 | -1.54 | 0.1223 |
| S4 | 0.833 | 67.23 | 20.52 | 3.28 | 0.775 | 699 | -1.81 | 0.0709 |
| S5 | 0.800 | 63.43 | 20.23 | 3.13 | 0.727 | 699 | -2.16 | 0.0310 |
| S6 | 0.725 | 55.92 | 22.98 | 2.43 | 0.886 | 699 | -1.89 | 0.0586 |

Per-market Sharpe (first half):

| variant | BTCUSDT | ETHUSDT | XAUUSD | XAGUSD | USDJPY | SPX | WTI | BRENT |
|---|---|---|---|---|---|---|---|---|
| S0 | 0.45 | 1.18 | -0.06 | 0.05 | 0.71 | 0.06 | 0.88 | 0.51 |
| S1 | 0.68 | 1.01 | -0.35 | -0.10 | 0.85 | -0.04 | 0.33 | 0.07 |
| S2 | 0.79 | 0.81 | -0.46 | -0.34 | 0.92 | -0.22 | 0.13 | -0.18 |
| S3 | 0.57 | 1.10 | -0.22 | -0.01 | 0.79 | 0.02 | 0.53 | 0.28 |
| S4 | 0.58 | 1.05 | -0.32 | -0.03 | 0.79 | 0.09 | 0.37 | 0.14 |
| S5 | 0.66 | 0.90 | -0.30 | -0.37 | 0.82 | 0.11 | 0.52 | 0.17 |
| S6 | 0.67 | 0.86 | -0.23 | -0.48 | 0.89 | -0.05 | 0.39 | 0.09 |

Per-market return % / max DD % (exposure-matched, first half):

| variant | BTCUSDT | ETHUSDT | XAUUSD | XAGUSD | USDJPY | SPX | WTI | BRENT |
|---|---|---|---|---|---|---|---|---|
| S0 | 107.8 / 104.6 | 359.8 / 68.2 | -3.1 / 43.2 | 6.2 / 101.6 | 24.0 / 19.8 | 3.0 / 30.3 | 199.9 / 66.2 | 96.9 / 91.0 |
| S1 | 167.7 / 85.5 | 270.7 / 60.4 | -18.9 / 46.1 | -12.2 / 102.0 | 29.4 / 21.3 | -2.1 / 33.6 | 56.8 / 77.4 | 11.2 / 108.6 |
| S2 | 225.1 / 77.0 | 212.0 / 59.3 | -25.9 / 50.0 | -37.2 / 102.8 | 33.1 / 22.0 | -13.0 / 39.6 | 22.1 / 91.1 | -30.5 / 115.2 |
| S3 | 136.9 / 93.4 | 310.8 / 62.8 | -12.0 / 44.4 | -1.9 / 101.7 | 26.9 / 20.7 | 1.2 / 31.6 | 96.9 / 73.9 | 49.1 / 101.2 |
| S4 | 136.6 / 90.7 | 301.1 / 65.9 | -17.1 / 44.9 | -3.6 / 100.5 | 27.2 / 21.2 | 4.6 / 30.7 | 65.8 / 76.3 | 23.4 / 105.5 |
| S5 | 161.8 / 86.3 | 245.4 / 67.3 | -16.5 / 49.1 | -44.0 / 114.4 | 28.8 / 22.2 | 5.6 / 32.7 | 98.3 / 77.6 | 28.1 / 94.2 |
| S6 | 171.8 / 84.0 | 228.5 / 72.5 | -13.4 / 46.2 | -55.0 / 116.8 | 32.2 / 22.6 | -2.5 / 36.8 | 71.0 / 93.1 | 14.6 / 103.9 |

### second half, pooled (8 markets, $80,000)

| variant | Sharpe | return % | max DD % | return/DD | avg exposure | trades | JK z | JK p |
|---|---|---|---|---|---|---|---|---|
| S0 | 1.034 | 41.75 | 9.96 | 4.19 | 0.997 | 343 | - | - |
| S1 | 1.182 | 46.67 | 8.48 | 5.50 | 1.058 | 343 | 0.90 | 0.3684 |
| S2 | 1.183 | 47.90 | 9.01 | 5.32 | 1.175 | 343 | 0.50 | 0.6177 |
| S3 | 1.125 | 44.69 | 8.90 | 5.02 | 1.019 | 343 | 1.12 | 0.2628 |
| S4 | 1.176 | 47.45 | 9.32 | 5.09 | 0.927 | 343 | 1.50 | 0.1334 |
| S5 | 1.229 | 50.38 | 9.08 | 5.55 | 0.891 | 343 | 1.16 | 0.2448 |
| S6 | 1.230 | 51.00 | 8.35 | 6.11 | 1.115 | 343 | 0.86 | 0.3921 |

Per-market Sharpe (second half):

| variant | BTCUSDT | ETHUSDT | XAUUSD | XAGUSD | USDJPY | SPX | WTI | BRENT |
|---|---|---|---|---|---|---|---|---|
| S0 | 0.68 | 0.79 | 1.77 | -0.23 | 0.27 | 0.87 | -0.07 | -0.07 |
| S1 | 0.80 | 0.96 | 1.75 | -0.11 | 0.32 | 0.89 | -0.12 | -0.10 |
| S2 | 0.79 | 0.99 | 1.72 | -0.01 | 0.37 | 0.87 | -0.17 | -0.15 |
| S3 | 0.76 | 0.89 | 1.76 | -0.17 | 0.30 | 0.89 | -0.10 | -0.08 |
| S4 | 0.80 | 0.92 | 1.77 | -0.15 | 0.28 | 0.88 | -0.08 | -0.06 |
| S5 | 0.86 | 0.96 | 1.77 | -0.06 | 0.34 | 0.86 | -0.06 | -0.15 |
| S6 | 0.87 | 0.87 | 1.77 | 0.15 | 0.35 | 0.86 | -0.09 | -0.14 |

Per-market return % / max DD % (exposure-matched, second half):

| variant | BTCUSDT | ETHUSDT | XAUUSD | XAGUSD | USDJPY | SPX | WTI | BRENT |
|---|---|---|---|---|---|---|---|---|
| S0 | 85.2 / 69.1 | 125.8 / 72.8 | 109.7 / 22.4 | -18.5 / 75.0 | 6.6 / 11.0 | 35.1 / 17.5 | -5.3 / 41.9 | -4.7 / 36.2 |
| S1 | 97.5 / 59.6 | 149.9 / 61.7 | 106.9 / 22.0 | -8.6 / 71.4 | 8.0 / 11.1 | 35.5 / 17.8 | -9.1 / 49.8 | -6.8 / 39.3 |
| S2 | 100.0 / 50.4 | 158.3 / 58.6 | 103.0 / 21.4 | -1.1 / 69.7 | 9.7 / 14.5 | 36.3 / 18.2 | -13.0 / 57.1 | -10.0 / 42.7 |
| S3 | 92.7 / 64.4 | 139.9 / 64.6 | 108.4 / 22.2 | -13.2 / 73.0 | 7.2 / 10.7 | 35.2 / 17.6 | -7.2 / 45.9 | -5.5 / 37.7 |
| S4 | 99.4 / 64.9 | 151.6 / 66.0 | 109.7 / 22.4 | -12.2 / 71.5 | 6.8 / 11.2 | 34.6 / 17.6 | -6.4 / 45.0 | -4.0 / 36.3 |
| S5 | 107.9 / 61.8 | 163.5 / 75.6 | 109.7 / 22.4 | -5.3 / 70.0 | 8.4 / 10.8 | 33.7 / 17.2 | -5.0 / 44.8 | -9.9 / 40.3 |
| S6 | 108.9 / 63.0 | 149.4 / 77.1 | 109.7 / 22.4 | 13.5 / 61.9 | 8.9 / 11.2 | 33.7 / 17.2 | -6.9 / 48.2 | -9.2 / 40.7 |

Pass-bar conditions (REGISTERED): c1 pooled Sharpe > S0, c2 >= 5 of 8 markets beat S0 on Sharpe, c3 pooled matched max DD <= S0, c4 forecast correlation > 0.

| variant | 1st: gain / c1 c2 c3 c4 (markets) | 2nd: gain / c1 c2 c3 c4 (markets) | full bar |
|---|---|---|---|
| S1 | -0.328 / nnnY (2) | +0.148 / YYYY (5) | no |
| S2 | -0.521 / nnnY (2) | +0.149 / YnYY (4) | no |
| S3 | -0.190 / nnYY (2) | +0.091 / YYYY (5) | no |
| S4 | -0.288 / nnnY (3) | +0.142 / YYYY (6) | no |
| S5 | -0.321 / nnYY (3) | +0.195 / YYYY (5) | no |
| S6 | -0.396 / nnnY (2) | +0.196 / YnYY (4) | no |

Chosen on the first half: S3; verdict on it: NO PASS.

## 3. Secondary stream (descriptive): daily 30-day momentum sign, re-sized daily

### first half, pooled (8 markets, $80,000)

| variant | Sharpe | return % | max DD % | return/DD | avg exposure | trades | JK z | JK p |
|---|---|---|---|---|---|---|---|---|
| S0 | 1.208 | 107.44 | 21.17 | 5.08 | 1.000 | - | - | - |
| S1 | 1.407 | 99.96 | 21.34 | 4.68 | 1.003 | - | 0.79 | 0.4301 |
| S2 | 1.266 | 89.67 | 22.58 | 3.97 | 1.127 | - | 0.17 | 0.8681 |
| S3 | 1.413 | 106.87 | 19.35 | 5.52 | 0.983 | - | 1.30 | 0.1932 |
| S4 | 1.494 | 110.89 | 18.34 | 6.05 | 0.864 | - | 1.36 | 0.1745 |
| S5 | 1.400 | 107.16 | 18.07 | 5.93 | 0.827 | - | 1.13 | 0.2592 |
| S6 | 1.353 | 100.04 | 19.89 | 5.03 | 0.998 | - | 0.62 | 0.5342 |

Per-market Sharpe (first half):

| variant | BTCUSDT | ETHUSDT | XAUUSD | XAGUSD | USDJPY | SPX | WTI | BRENT |
|---|---|---|---|---|---|---|---|---|
| S0 | 1.07 | 1.16 | -0.40 | 0.28 | -0.30 | 0.22 | 0.60 | 0.44 |
| S1 | 1.05 | 1.24 | -0.20 | 0.29 | -0.15 | 0.33 | 0.85 | 0.59 |
| S2 | 0.85 | 0.98 | -0.09 | 0.27 | -0.07 | 0.45 | 0.94 | 0.62 |
| S3 | 1.11 | 1.27 | -0.29 | 0.29 | -0.21 | 0.28 | 0.83 | 0.57 |
| S4 | 1.15 | 1.44 | -0.27 | 0.28 | -0.21 | 0.18 | 0.78 | 0.55 |
| S5 | 0.99 | 1.45 | -0.35 | 0.27 | -0.15 | 0.14 | 0.74 | 0.53 |
| S6 | 0.93 | 1.25 | -0.16 | 0.22 | -0.01 | 0.30 | 0.81 | 0.57 |

Per-market return % / max DD % (exposure-matched, first half):

| variant | BTCUSDT | ETHUSDT | XAUUSD | XAGUSD | USDJPY | SPX | WTI | BRENT |
|---|---|---|---|---|---|---|---|---|
| S0 | 262.6 / 76.5 | 373.6 / 96.2 | -22.3 / 40.1 | 32.8 / 54.2 | -9.5 / 23.9 | 18.3 / 37.2 | 127.3 / 82.3 | 76.8 / 64.1 |
| S1 | 230.9 / 78.1 | 341.5 / 91.9 | -10.1 / 32.8 | 29.0 / 44.9 | -4.1 / 18.3 | 19.6 / 24.8 | 117.4 / 53.4 | 75.5 / 47.8 |
| S2 | 193.5 / 97.7 | 270.3 / 96.2 | -4.7 / 33.7 | 27.8 / 39.9 | -1.9 / 16.6 | 26.1 / 17.4 | 128.2 / 51.5 | 78.0 / 48.6 |
| S3 | 253.2 / 78.4 | 369.6 / 82.7 | -15.2 / 33.2 | 30.7 / 49.7 | -6.2 / 20.4 | 17.5 / 31.0 | 125.3 / 52.9 | 80.0 / 55.0 |
| S4 | 262.6 / 83.1 | 420.8 / 71.4 | -13.9 / 34.3 | 29.2 / 50.7 | -5.9 / 19.9 | 11.5 / 33.6 | 110.8 / 55.0 | 72.0 / 53.0 |
| S5 | 221.9 / 80.4 | 421.0 / 73.8 | -18.1 / 37.8 | 28.6 / 51.0 | -4.3 / 18.5 | 9.6 / 38.3 | 122.8 / 52.5 | 76.0 / 53.9 |
| S6 | 208.1 / 81.4 | 356.9 / 89.5 | -8.2 / 32.6 | 22.9 / 46.0 | -0.4 / 16.7 | 19.1 / 30.9 | 124.3 / 54.1 | 77.7 / 44.9 |

### second half, pooled (8 markets, $80,000)

| variant | Sharpe | return % | max DD % | return/DD | avg exposure | trades | JK z | JK p |
|---|---|---|---|---|---|---|---|---|
| S0 | 0.453 | 17.72 | 24.57 | 0.72 | 1.000 | - | - | - |
| S1 | 0.720 | 25.66 | 20.82 | 1.23 | 1.055 | - | 1.25 | 0.2106 |
| S2 | 0.886 | 32.29 | 18.51 | 1.74 | 1.202 | - | 1.17 | 0.2404 |
| S3 | 0.598 | 21.94 | 22.50 | 0.97 | 1.016 | - | 1.29 | 0.1985 |
| S4 | 0.604 | 22.02 | 23.06 | 0.95 | 0.907 | - | 1.01 | 0.3146 |
| S5 | 0.575 | 21.24 | 24.76 | 0.86 | 0.846 | - | 0.61 | 0.5386 |
| S6 | 0.643 | 23.64 | 21.82 | 1.08 | 1.052 | - | 0.69 | 0.4893 |

Per-market Sharpe (second half):

| variant | BTCUSDT | ETHUSDT | XAUUSD | XAGUSD | USDJPY | SPX | WTI | BRENT |
|---|---|---|---|---|---|---|---|---|
| S0 | 0.31 | 0.79 | -0.05 | -0.43 | -0.29 | 0.63 | 0.08 | -0.14 |
| S1 | 0.61 | 0.85 | 0.17 | -0.49 | -0.23 | 0.83 | 0.24 | -0.01 |
| S2 | 0.86 | 0.88 | 0.34 | -0.58 | -0.21 | 0.66 | 0.36 | 0.12 |
| S3 | 0.47 | 0.82 | 0.06 | -0.46 | -0.26 | 0.81 | 0.17 | -0.07 |
| S4 | 0.41 | 0.77 | 0.12 | -0.39 | -0.21 | 0.93 | 0.18 | -0.06 |
| S5 | 0.37 | 0.70 | 0.27 | -0.52 | -0.30 | 0.67 | 0.31 | 0.05 |
| S6 | 0.52 | 0.74 | 0.36 | -0.58 | -0.35 | 0.64 | 0.27 | 0.08 |

Per-market return % / max DD % (exposure-matched, second half):

| variant | BTCUSDT | ETHUSDT | XAUUSD | XAGUSD | USDJPY | SPX | WTI | BRENT |
|---|---|---|---|---|---|---|---|---|
| S0 | 35.4 / 84.2 | 125.0 / 64.5 | -2.1 / 29.0 | -29.8 / 50.6 | -7.2 / 20.8 | 23.4 / 17.6 | 6.3 / 37.7 | -9.2 / 29.9 |
| S1 | 64.4 / 65.3 | 130.7 / 60.7 | 5.9 / 26.0 | -32.1 / 56.9 | -5.2 / 19.9 | 25.2 / 16.1 | 16.8 / 33.5 | -0.3 / 22.2 |
| S2 | 93.6 / 51.9 | 141.7 / 62.0 | 11.8 / 25.2 | -37.2 / 65.5 | -4.9 / 19.1 | 20.8 / 19.4 | 25.1 / 29.9 | 7.3 / 23.8 |
| S3 | 50.0 / 74.0 | 127.0 / 61.3 | 2.2 / 26.4 | -30.5 / 53.3 | -6.0 / 20.4 | 25.5 / 14.9 | 11.9 / 35.5 | -4.5 / 26.1 |
| S4 | 43.8 / 73.8 | 121.5 / 66.9 | 4.3 / 27.4 | -26.1 / 49.5 | -5.0 / 20.6 | 28.4 / 14.4 | 13.0 / 35.2 | -3.7 / 27.1 |
| S5 | 39.9 / 77.4 | 113.3 / 82.2 | 9.8 / 26.1 | -33.3 / 58.7 | -7.2 / 21.8 | 21.3 / 16.1 | 22.6 / 30.4 | 3.4 / 24.1 |
| S6 | 55.0 / 66.1 | 122.9 / 78.2 | 13.2 / 24.3 | -38.0 / 67.9 | -8.2 / 21.8 | 19.8 / 16.1 | 19.4 / 29.6 | 5.2 / 23.2 |

Pass-bar conditions (descriptive only): c1 pooled Sharpe > S0, c2 >= 5 of 8 markets beat S0 on Sharpe, c3 pooled matched max DD <= S0, c4 forecast correlation > 0.

| variant | 1st: gain / c1 c2 c3 c4 (markets) | 2nd: gain / c1 c2 c3 c4 (markets) | full bar |
|---|---|---|---|
| S1 | +0.199 / YYnY (7) | +0.267 / YYYY (7) | no |
| S2 | +0.058 / YYnY (5) | +0.433 / YYYY (7) | no |
| S3 | +0.205 / YYYY (8) | +0.145 / YYYY (7) | PASS |
| S4 | +0.286 / YYYY (7) | +0.151 / YYYY (7) | PASS |
| S5 | +0.192 / YYYY (5) | +0.122 / YYnY (5) | no |
| S6 | +0.145 / YYYY (6) | +0.190 / YYYY (5) | PASS |

Chosen on the first half: S4; verdict on it: PASS.

## 4. Checks

Truncation (sigma, reference, weights, proxy sides on bars cut at 50% / 80% vs the full run): BTCUSDT 0/320977, ETHUSDT 0/320977, XAUUSD 0/219500, XAGUSD 0/219460, USDJPY 0/231049, SPX 0/66672, WTI 0/219089, BRENT 0/200926 (mismatches / values compared).

- BTCUSDT main trades: {"mapped": 236, "unmapped": 0, "entry_at_bar_open": 236, "trades_used": 236, "no_reference": 0}; S1 / S5 weights at entry: {"S1": {"mean": 1.004, "p10": 0.605, "p90": 1.398}, "S5": {"mean": 0.85, "p10": 0.5, "p90": 1.0}}; proxy: {"decisions": 2142, "no_reference": 0, "long_share": 0.568}
- ETHUSDT main trades: {"mapped": 203, "unmapped": 0, "entry_at_bar_open": 203, "trades_used": 203, "no_reference": 0}; S1 / S5 weights at entry: {"S1": {"mean": 1.016, "p10": 0.616, "p90": 1.457}, "S5": {"mean": 0.815, "p10": 0.5, "p90": 1.0}}; proxy: {"decisions": 2142, "no_reference": 0, "long_share": 0.554}
- XAUUSD main trades: {"mapped": 111, "unmapped": 0, "entry_at_bar_open": 111, "trades_used": 111, "no_reference": 0}; S1 / S5 weights at entry: {"S1": {"mean": 0.988, "p10": 0.499, "p90": 1.316}, "S5": {"mean": 0.847, "p10": 0.5, "p90": 1.0}}; proxy: {"decisions": 1514, "no_reference": 0, "long_share": 0.616}
- XAGUSD main trades: {"mapped": 151, "unmapped": 0, "entry_at_bar_open": 151, "trades_used": 151, "no_reference": 0}; S1 / S5 weights at entry: {"S1": {"mean": 0.986, "p10": 0.672, "p90": 1.307}, "S5": {"mean": 0.834, "p10": 0.5, "p90": 1.0}}; proxy: {"decisions": 1514, "no_reference": 0, "long_share": 0.572}
- USDJPY main trades: {"mapped": 71, "unmapped": 0, "entry_at_bar_open": 71, "trades_used": 71, "no_reference": 0}; S1 / S5 weights at entry: {"S1": {"mean": 1.016, "p10": 0.643, "p90": 1.355}, "S5": {"mean": 0.838, "p10": 0.5, "p90": 1.0}}; proxy: {"decisions": 1523, "no_reference": 0, "long_share": 0.584}
- SPX main trades: {"mapped": 34, "unmapped": 0, "entry_at_bar_open": 34, "trades_used": 34, "no_reference": 0}; S1 / S5 weights at entry: {"S1": {"mean": 1.06, "p10": 0.569, "p90": 1.5}, "S5": {"mean": 0.868, "p10": 0.5, "p90": 1.0}}; proxy: {"decisions": 1473, "no_reference": 0, "long_share": 0.692}
- WTI main trades: {"mapped": 114, "unmapped": 0, "entry_at_bar_open": 114, "trades_used": 114, "no_reference": 0}; S1 / S5 weights at entry: {"S1": {"mean": 0.862, "p10": 0.25, "p90": 1.248}, "S5": {"mean": 0.811, "p10": 0.5, "p90": 1.0}}; proxy: {"decisions": 1514, "no_reference": 0, "long_share": 0.501}
- BRENT main trades: {"mapped": 122, "unmapped": 0, "entry_at_bar_open": 122, "trades_used": 122, "no_reference": 0}; S1 / S5 weights at entry: {"S1": {"mean": 0.891, "p10": 0.25, "p90": 1.368}, "S5": {"mean": 0.811, "p10": 0.5, "p90": 1.0}}; proxy: {"decisions": 1515, "no_reference": 0, "long_share": 0.512}

Variants: S0 constant notional, w = 1 (baseline); S1 inverse volatility, w = clip(m / sigma, 0.25, 4); S2 inverse variance, w = clip((m / sigma)^2, 0.25, 4); S3 half-strength inverse volatility, w = clip(sqrt(m / sigma), 0.25, 4); S4 cut only, w = min(1, m / sigma), floor 0.25; S5 top-tercile cut, w = 0.5 above the trailing 67th percentile, else 1; S6 three regimes, w = 1.5 / 1 / 0.5 by trailing terciles.
Sharpe-difference test vs S0 (Jobson-Korkie, Memmel correction) on pooled matched daily P&L; Bonferroni threshold 0.0083 over 6 variants (reported, not a pass condition).
