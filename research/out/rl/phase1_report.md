# RL Phase 1 report: benchmarks after costs, walk-forward out of sample

Run `phase1_20261111T124954Z_53591f6b`, generated 2026-11-11 12:50 UTC. BTCUSDT perpetual (Binance USD-M), 15-minute bars. Paper only.

## Summary

- At 0.10% a side, out of sample (2020-10-01 to 2026-11-11): buy-and-hold +249% (Sharpe 0.64, max drawdown 79%); daily 30-day momentum +238% (Sharpe 0.63, 31 trades a year, turnover 62x a year, cost drag 14% a year); random agent -95% on average over 10 seeds (Sharpe -0.93 +- 0.32).
- At 0.05% a side, out of sample (2020-10-01 to 2026-11-11): buy-and-hold +249% (Sharpe 0.64, max drawdown 79%); daily 30-day momentum +309% (Sharpe 0.68, 31 trades a year, turnover 62x a year, cost drag 11% a year); random agent -87% on average over 10 seeds (Sharpe -0.59 +- 0.32).
- Buy-and-hold before costs: +585%; holding the perpetual long paid 11.0% of equity a year in funding, which is most of the gap between its gross and net results (spot would not pay it).
- Momentum before costs: +710% (gross Sharpe 0.87). The gap to its net result is the cost of its turnover.
- Buy-and-hold's number is BTC's drift over these years, not skill; the random agent shows what costs and luck alone do to a strategy that trades once a day. No benchmark was trained or tuned; the rules were written in the config before the first run.

## Flags

- buy_hold at fee_0.10%: positive overall but only 48% of windows were positive.
- buy_hold at fee_0.10%: Sharpe 0.64 is above every random seed (max -0.39).
- momentum at fee_0.10%: Sharpe 0.63 is above every random seed (max -0.39).
- buy_hold at fee_0.05%: positive overall but only 48% of windows were positive.
- buy_hold at fee_0.05%: Sharpe 0.64 is above every random seed (max -0.07).
- momentum at fee_0.05%: Sharpe 0.68 is above every random seed (max -0.07).

## Data

- Bars: 251586, first 2019-09-08 19:00:00+00:00, last 2026-11-11 11:15:00+00:00 (open times, UTC).
- Gaps: 0 events, 0 missing bars (reported, not filled). Largest: none.
- Cleaning: 0 duplicates, 0 pre-listing placeholder bars, 0 OHLC-invalid bars dropped. 17 zero-volume bars kept: Binance serves exchange downtime as flat no-trade bars rather than missing ones, so these are the series' real outages (e.g. 2019-09-09 00:00:00+00:00, 2019-09-09 00:15:00+00:00, 2019-09-09 00:30:00+00:00, 2019-09-09 00:45:00+00:00).
- Funding: 7858 rows. Open interest: live only, OFF in backtests (free history ~30 days).

## Method

- Decision at each bar's close, fill at the open of the next bar (delay 1 bar). Returns open to open; equity compounds.
- Costs (one model, `engine15/rl/costs.py`): taker fee 0.10% a side (also shown at 0.05%), half-spread 0.5 bps, slippage 0.10 x per-bar realised vol (96 bars) x |trade|, funding on the position held at each settlement.
- Walk-forward: 12-month train, 3-month test, step 3 months, 25 test windows (2020-10-01 .. 2026-11-11). Benchmarks do not train; their target series is stitched over the test windows and backtested once, so positions carry across windows.
- Sharpe and Sortino are annualised for 15m bars: 365 x 96 = 35,040 bars a year, risk-free 0.
- Rules: buy-and-hold = +1 always; random = uniform draw from {-1, 0, +1} once a day at 00:00 UTC, seeds [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] (both fixed before the first run). Momentum (frozen 11 Nov 2026, Phase 2 task 1, before any agent result): decide once a day at the 00:00 UTC bar close, fill at the next open, sign of the 30-day return, long/short. It replaces Phase 1's sign-of-96-bar-return-at-every-close rule, which traded ~1,800 times a year (a straw man).

## Stitched out of sample, 0.10% a side

| Strategy | Net return | Gross return | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Avg hold (h) | Cost drag/yr | Funding paid/yr |
|---|---|---|---|---|---|---|---|---|---|---|---|
| buy_hold | +249.3% | +584.8% | +22.7% | 0.64 | 0.91 | 79.3% | 0.29 | 0 | 53579.2 | 11.0% | +11.0% |
| momentum | +237.7% | +710.1% | +22.0% | 0.63 | 0.89 | 64.5% | 0.34 | 62 | 280.5 | 14.3% | +6.1% |
| random (mean of 10) | -95.3% | -34.1% | -42.7% | -0.93 | -1.30 | 96.9% | -0.44 | 323 | 36.1 | 42.6% | -0.0% |
| random (sd) | 4.3% | 63.6% | 9.3% | 0.32 | 0.45 | 2.5% | 0.09 | 10 | 0.9 | 1.5% | 0.4% |
| random (min .. max) | -99.2% .. -86.2% | -88.6% .. +102.8% | -55.0% .. -27.6% | -1.33 .. -0.39 | -1.85 .. -0.56 | 93.3% .. 99.5% | -0.55 .. -0.30 | 303 .. 338 | 34.6 .. 37.8 | 39.9% .. 44.3% | -0.6% .. +0.7% |

## Stitched out of sample, 0.05% a side

| Strategy | Net return | Gross return | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Avg hold (h) | Cost drag/yr | Funding paid/yr |
|---|---|---|---|---|---|---|---|---|---|---|---|
| buy_hold | +249.5% | +584.8% | +22.7% | 0.64 | 0.91 | 79.3% | 0.29 | 0 | 53579.2 | 11.0% | +11.0% |
| momentum | +308.7% | +710.1% | +25.9% | 0.68 | 0.97 | 61.3% | 0.42 | 62 | 280.5 | 11.2% | +6.1% |
| random (mean of 10) | -87.3% | -34.1% | -32.6% | -0.59 | -0.84 | 92.9% | -0.35 | 323 | 36.1 | 26.5% | -0.0% |
| random (sd) | 11.8% | 63.6% | 11.0% | 0.32 | 0.46 | 5.5% | 0.10 | 10 | 0.9 | 1.0% | 0.4% |
| random (min .. max) | -97.9% .. -62.1% | -88.6% .. +102.8% | -46.7% .. -14.7% | -1.00 .. -0.07 | -1.39 .. -0.09 | 84.7% .. 98.9% | -0.47 .. -0.17 | 303 .. 338 | 34.6 .. 37.8 | 24.7% .. 27.7% | -0.6% .. +0.7% |

## Per test window, 0.10% a side

| # | Test window | B&H net | B&H Sharpe | Mom net | Mom gross | Mom Sharpe | Random net (mean +- sd) | Random Sharpe |
|---|---|---|---|---|---|---|---|---|
| 0 | 2020-10-01 .. 2021-01-01 | +155.6% | 6.04 | +168.0% | +181.3% | 6.33 | -14.2% +- 20.4% | -1.05 |
| 1 | 2021-01-01 .. 2021-04-01 | +72.4% | 2.49 | +34.9% | +58.3% | 1.63 | -17.2% +- 35.7% | -0.66 |
| 2 | 2021-04-01 .. 2021-07-01 | -44.4% | -1.68 | -21.2% | -17.9% | -0.36 | +5.4% +- 22.4% | 0.54 |
| 3 | 2021-07-01 .. 2021-10-01 | +22.4% | 1.54 | +13.6% | +20.1% | 1.09 | -20.0% +- 26.0% | -1.65 |
| 4 | 2021-10-01 .. 2022-01-01 | +0.3% | 0.35 | +1.7% | +4.4% | 0.43 | -24.4% +- 21.0% | -2.02 |
| 5 | 2022-01-01 .. 2022-04-01 | -2.8% | 0.16 | -31.9% | -30.5% | -2.03 | -17.7% +- 18.6% | -1.39 |
| 6 | 2022-04-01 .. 2022-07-01 | -56.6% | -4.00 | +40.9% | +43.0% | 2.18 | -0.7% +- 52.1% | -0.41 |
| 7 | 2022-07-01 .. 2022-10-01 | -3.7% | 0.07 | +2.4% | +4.1% | 0.46 | -9.0% +- 14.5% | -0.58 |
| 8 | 2022-10-01 .. 2023-01-01 | -15.5% | -1.16 | -27.6% | -24.4% | -2.45 | -16.9% +- 11.1% | -1.95 |
| 9 | 2023-01-01 .. 2023-04-01 | +68.6% | 4.31 | +52.3% | +57.5% | 3.52 | -7.6% +- 22.2% | -0.84 |
| 10 | 2023-04-01 .. 2023-07-01 | +5.4% | 0.72 | -3.5% | -1.9% | -0.14 | -14.4% +- 12.4% | -1.79 |
| 11 | 2023-07-01 .. 2023-10-01 | -12.6% | -1.24 | +9.5% | +9.9% | 1.15 | -11.8% +- 10.8% | -1.80 |
| 12 | 2023-10-01 .. 2024-01-01 | +52.2% | 3.97 | +51.8% | +57.0% | 3.95 | -8.9% +- 18.8% | -1.03 |
| 13 | 2024-01-01 .. 2024-04-01 | +59.5% | 3.52 | +1.6% | +8.9% | 0.40 | -14.3% +- 20.5% | -1.32 |
| 14 | 2024-04-01 .. 2024-07-01 | -14.0% | -1.01 | +3.3% | +6.6% | 0.51 | -3.0% +- 22.5% | -0.31 |
| 15 | 2024-07-01 .. 2024-10-01 | -0.0% | 0.27 | -51.4% | -49.4% | -4.94 | -12.4% +- 18.0% | -1.17 |
| 16 | 2024-10-01 .. 2025-01-01 | +43.1% | 3.06 | +40.1% | +45.2% | 2.89 | +4.2% +- 28.1% | 0.35 |
| 17 | 2025-01-01 .. 2025-04-01 | -12.9% | -0.74 | -22.9% | -20.2% | -1.63 | -13.6% +- 16.1% | -1.21 |
| 18 | 2025-04-01 .. 2025-07-01 | +28.6% | 2.64 | -1.2% | +1.5% | 0.09 | -11.2% +- 14.9% | -1.32 |
| 19 | 2025-07-01 .. 2025-10-01 | +4.6% | 0.74 | +2.6% | +4.5% | 0.48 | -12.5% +- 8.4% | -2.10 |
| 20 | 2025-10-01 .. 2026-01-01 | -24.0% | -2.07 | +15.1% | +16.0% | 1.42 | -14.3% +- 12.4% | -1.46 |
| 21 | 2026-01-01 .. 2026-04-01 | -22.3% | -1.60 | -22.7% | -18.9% | -1.63 | -17.2% +- 17.0% | -1.63 |
| 22 | 2026-04-01 .. 2026-07-01 | -14.3% | -1.29 | +19.1% | +21.0% | 1.89 | -11.4% +- 15.0% | -1.51 |
| 23 | 2026-07-01 .. 2026-10-01 | +40.3% | 4.05 | -12.0% | -9.2% | -1.29 | +1.6% +- 12.7% | 0.23 |
| 24 | 2026-10-01 .. 2026-11-11 | -12.1% | -3.12 | +13.4% | +13.4% | 3.39 | -4.9% +- 8.5% | -1.61 |

## Per test window, 0.05% a side

| # | Test window | B&H net | B&H Sharpe | Mom net | Mom gross | Mom Sharpe | Random net (mean +- sd) | Random Sharpe |
|---|---|---|---|---|---|---|---|---|
| 0 | 2020-10-01 .. 2021-01-01 | +155.7% | 6.05 | +168.4% | +181.3% | 6.34 | -10.6% +- 21.5% | -0.76 |
| 1 | 2021-01-01 .. 2021-04-01 | +72.4% | 2.49 | +35.4% | +58.3% | 1.64 | -13.8% +- 37.1% | -0.49 |
| 2 | 2021-04-01 .. 2021-07-01 | -44.4% | -1.68 | -20.5% | -17.9% | -0.33 | +9.8% +- 23.5% | 0.73 |
| 3 | 2021-07-01 .. 2021-10-01 | +22.4% | 1.54 | +15.1% | +20.1% | 1.17 | -16.8% +- 27.1% | -1.36 |
| 4 | 2021-10-01 .. 2022-01-01 | +0.3% | 0.35 | +1.9% | +4.4% | 0.44 | -21.3% +- 21.9% | -1.74 |
| 5 | 2022-01-01 .. 2022-04-01 | -2.8% | 0.16 | -31.3% | -30.5% | -1.97 | -14.4% +- 19.2% | -1.09 |
| 6 | 2022-04-01 .. 2022-07-01 | -56.6% | -4.00 | +41.9% | +43.0% | 2.22 | +3.3% +- 54.0% | -0.15 |
| 7 | 2022-07-01 .. 2022-10-01 | -3.7% | 0.07 | +3.0% | +4.1% | 0.50 | -5.3% +- 14.9% | -0.26 |
| 8 | 2022-10-01 .. 2023-01-01 | -15.5% | -1.16 | -26.4% | -24.4% | -2.32 | -13.4% +- 11.5% | -1.50 |
| 9 | 2023-01-01 .. 2023-04-01 | +68.6% | 4.31 | +53.4% | +57.5% | 3.57 | -3.9% +- 23.0% | -0.46 |
| 10 | 2023-04-01 .. 2023-07-01 | +5.4% | 0.72 | -2.9% | -1.9% | -0.08 | -10.9% +- 12.9% | -1.31 |
| 11 | 2023-07-01 .. 2023-10-01 | -12.6% | -1.24 | +9.8% | +9.9% | 1.18 | -8.1% +- 11.3% | -1.25 |
| 12 | 2023-10-01 .. 2024-01-01 | +52.2% | 3.97 | +52.0% | +57.0% | 3.95 | -5.0% +- 19.6% | -0.56 |
| 13 | 2024-01-01 .. 2024-04-01 | +59.5% | 3.52 | +2.6% | +8.9% | 0.47 | -10.8% +- 21.3% | -0.98 |
| 14 | 2024-04-01 .. 2024-07-01 | -14.0% | -1.01 | +4.4% | +6.6% | 0.60 | +1.2% +- 23.4% | 0.12 |
| 15 | 2024-07-01 .. 2024-10-01 | -0.0% | 0.27 | -50.7% | -49.4% | -4.85 | -8.8% +- 18.8% | -0.81 |
| 16 | 2024-10-01 .. 2025-01-01 | +43.1% | 3.06 | +40.5% | +45.2% | 2.91 | +8.6% +- 29.4% | 0.74 |
| 17 | 2025-01-01 .. 2025-04-01 | -12.9% | -0.74 | -21.8% | -20.2% | -1.53 | -10.1% +- 16.6% | -0.85 |
| 18 | 2025-04-01 .. 2025-07-01 | +28.6% | 2.64 | -0.3% | +1.5% | 0.18 | -7.6% +- 15.4% | -0.86 |
| 19 | 2025-07-01 .. 2025-10-01 | +4.6% | 0.74 | +3.2% | +4.5% | 0.56 | -8.7% +- 8.7% | -1.44 |
| 20 | 2025-10-01 .. 2026-01-01 | -24.0% | -2.07 | +15.7% | +16.0% | 1.46 | -10.8% +- 12.9% | -1.06 |
| 21 | 2026-01-01 .. 2026-04-01 | -22.3% | -1.60 | -21.3% | -18.9% | -1.50 | -13.8% +- 17.7% | -1.27 |
| 22 | 2026-04-01 .. 2026-07-01 | -14.3% | -1.29 | +20.1% | +21.0% | 1.97 | -7.8% +- 15.6% | -1.03 |
| 23 | 2026-07-01 .. 2026-10-01 | +40.3% | 4.05 | -11.2% | -9.2% | -1.19 | +5.9% +- 13.3% | 0.82 |
| 24 | 2026-10-01 .. 2026-11-11 | -12.1% | -3.12 | +13.5% | +13.4% | 3.42 | -3.0% +- 8.6% | -0.99 |

Every metric for every window and seed is in `phase1_report.json`.
