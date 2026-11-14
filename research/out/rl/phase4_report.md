# RL Phase 4 report: more data per model

Run `phase4_20261111T205810Z_d214cadd`, generated 2026-11-11 21:55 UTC. 15-minute bars and a 15-minute decision clock throughout. Paper only: no orders, no keys. Seeds [0, 1, 2], run time 57.4 min. BTCUSDT perpetual is the headline; ETHUSDT is reported the same way. Out of sample = 25 stitched 3-month test windows, 2020-10-01 to 2026-11-11; every decision comes from a model trained only on data before its window. The strategy loop's rules A and B (and every comparison with them) are scored only up to 2025-11-11, the start of the loop's sealed holdout.

## Verdict

NO. Out of sample (Oct 2020 - Nov 2026, BTC, the headline), the Phase 4 primary agent (Q agent, BTC+ETH pooled, expanding, readings) shows an edge before costs on every seed (gross Sharpe 0.84, 0.65, 0.84, mean 0.78, t about 1.9; break-even fee 0.302%, 0.290%, 0.302%). After 0.10% fees it does not beat buy-and-hold and momentum risk-adjusted across seeds: seed-mean Sharpe 0.48 (seeds above buy-and-hold's 0.64: 0 of 3; above momentum's 0.63: 0 of 3), Calmar 0.24 vs 0.29 and 0.34, net return +79%. None of the 8 Phase 4 variants beats both on every seed.

- BTCUSDT, full span 2020-10-01 .. 2026-11-11: primary Sharpe 0.48 (seeds 0.52, 0.40, 0.51) vs buy-and-hold 0.64 and momentum 0.63; gross Sharpe 0.78; break-even fee 0.298%.
- BTCUSDT, span up to 2025-11-11: primary Sharpe 0.67 (seeds 0.69, 0.53, 0.79) vs buy-and-hold 0.83 and momentum 0.67; gross Sharpe 0.99; break-even fee 0.393%; loop rules A 1.19, B 1.32.
- ETHUSDT, full span 2020-10-01 .. 2026-11-11: primary Sharpe 0.77 (seeds 0.94, 0.75, 0.61) vs buy-and-hold 0.60 and momentum 0.83; gross Sharpe 1.11; break-even fee 0.419%.
- ETHUSDT, span up to 2025-11-11: primary Sharpe 0.86 (seeds 1.17, 0.76, 0.65) vs buy-and-hold 0.79 and momentum 0.82; gross Sharpe 1.23; break-even fee 0.447%.

## BTC headline: stitched out of sample 2020-10-01 .. 2026-11-11, 0.10% a side (the owner's rule)

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Q agent, BTC+ETH pooled, expanding, readings [primary], mean of 3 seeds** | **+78.8%** | **0.48** | **0.67** | **41%** | **0.24** | **47** | **110** | **162** | **8.4%** | **0.78** | **0.298%** |
| &nbsp;&nbsp;seed 0 | +94.2% | 0.52 | 0.72 | 40% | 0.28 | 54 | 126 | 130 | 9.5% | 0.84 | 0.302% |
| &nbsp;&nbsp;seed 1 | +57.8% | 0.40 | 0.56 | 45% | 0.17 | 39 | 95 | 234 | 7.2% | 0.65 | 0.290% |
| &nbsp;&nbsp;seed 2 | +84.4% | 0.51 | 0.72 | 38% | 0.27 | 49 | 109 | 123 | 8.6% | 0.84 | 0.302% |
| SP agent, BTC+ETH pooled, expanding, readings, mean of 3 seeds | +106.9% | 0.58 | 0.85 | 35% | 0.37 | 83 | 169 | 80 | 11.5% | 1.02 | 0.242% |
| SP agent, 8 markets pooled, expanding, readings, mean of 3 seeds | +127.2% | 0.65 | 0.97 | 36% | 0.41 | 80 | 156 | 81 | 11.1% | 1.09 | 0.270% |
| SP agent, BTC+ETH pooled, expanding, Phase 3 inputs, mean of 3 seeds | +8.8% | 0.14 | 0.21 | 49% | 0.04 | 41 | 97 | 168 | 5.2% | 0.33 | 0.103% |
| SP agent, one asset, expanding, readings, mean of 3 seeds | +374.2% | 0.85 | 1.24 | 36% | 0.69 | 90 | 182 | 80 | 12.5% | 1.29 | 0.324% |
| SP agent, one asset, expanding, Phase 3 inputs, mean of 3 seeds | +238.9% | 0.54 | 0.78 | 45% | 0.43 | 50 | 114 | 121 | 6.9% | 0.79 | 0.332% |
| SP agent, one asset, 12-month window, readings, mean of 3 seeds | -55.5% | -0.72 | -0.99 | 69% | -0.19 | 33 | 83 | 143 | 4.0% | -0.52 | -0.641% (loses before fees) |
| SP agent, one asset, 12-month window, Phase 3 inputs, mean of 3 seeds | -24.0% | -0.18 | -0.24 | 44% | -0.10 | 20 | 44 | 144 | 1.4% | -0.10 | -0.258% (loses before fees) |
| Phase 3 agent (c), continual + retrain [Phase 3 primary], mean of 3 seeds | -53.4% | -0.37 | -0.51 | 79% | -0.15 | 46 | 103 | 84 | 8.1% | -0.05 | -0.174% (loses before fees) |
| Phase 3 agent (a), static per fold, mean of 3 seeds | -51.8% | -0.42 | -0.58 | 75% | -0.16 | 40 | 101 | 108 | 5.6% | -0.19 | -0.220% (loses before fees) |
| Buy-and-hold (perp) | +249.3% | 0.64 | 0.91 | 79% | 0.29 | 0 | 0 | 53579 | 11.0% | 0.83 | > 5% |
| Buy-and-hold (spot) | +583.9% | 0.82 | 1.17 | 77% | 0.48 | 0 | 0 | 53579 | 0.0% | 0.83 | > 5% |
| Momentum (daily 30-day, long/short) | +237.7% | 0.63 | 0.89 | 64% | 0.34 | 62 | 31 | 281 | 14.3% | 0.87 | 0.418% |
| Random agent (mean of 10) | -95.3% | -0.93 | -1.30 | 97% | -0.44 | 323 | 243 | 36 | 42.6% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +248.5% | 0.68 | 0.96 | 68% | 0.33 | 22 | 88 | 53579 | 11.9% | 0.95 | 1.036% |
| *reference: momentum through the Phase 3 risk manager* | +212.0% | 0.64 | 0.90 | 57% | 0.36 | 72 | 123 | 281 | 14.2% | 0.95 | 0.356% |

## BTC: stitched out of sample 2020-10-01 .. 2026-11-11, 0.05% a side (Binance USDT-M taker)

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Q agent, BTC+ETH pooled, expanding, readings [primary], mean of 3 seeds** | **+105.9%** | **0.56** | **0.78** | **41%** | **0.31** | **47** | **107** | **162** | **6.0%** | **0.77** | **0.302%** |
| &nbsp;&nbsp;seed 0 | +120.5% | 0.59 | 0.82 | 39% | 0.35 | 52 | 121 | 130 | 6.7% | 0.82 | 0.297% |
| &nbsp;&nbsp;seed 1 | +86.8% | 0.50 | 0.69 | 44% | 0.24 | 39 | 93 | 234 | 5.2% | 0.68 | 0.311% |
| &nbsp;&nbsp;seed 2 | +110.4% | 0.59 | 0.83 | 38% | 0.34 | 49 | 107 | 123 | 6.1% | 0.82 | 0.297% |
| SP agent, BTC+ETH pooled, expanding, readings, mean of 3 seeds | +176.2% | 0.76 | 1.11 | 31% | 0.60 | 81 | 159 | 80 | 7.2% | 1.03 | 0.253% |
| SP agent, 8 markets pooled, expanding, readings, mean of 3 seeds | +196.4% | 0.82 | 1.22 | 32% | 0.63 | 80 | 153 | 81 | 7.2% | 1.10 | 0.273% |
| SP agent, BTC+ETH pooled, expanding, Phase 3 inputs, mean of 3 seeds | +22.9% | 0.22 | 0.31 | 48% | 0.09 | 41 | 98 | 168 | 3.2% | 0.33 | 0.100% |
| SP agent, one asset, expanding, readings, mean of 3 seeds | +525.0% | 1.01 | 1.48 | 33% | 0.94 | 90 | 178 | 80 | 8.0% | 1.30 | 0.327% |
| SP agent, one asset, expanding, Phase 3 inputs, mean of 3 seeds | +285.1% | 0.63 | 0.91 | 43% | 0.51 | 50 | 115 | 121 | 4.5% | 0.79 | 0.324% |
| SP agent, one asset, 12-month window, readings, mean of 3 seeds | -50.5% | -0.64 | -0.89 | 66% | -0.17 | 34 | 86 | 143 | 2.4% | -0.53 | -0.604% (loses before fees) |
| SP agent, one asset, 12-month window, Phase 3 inputs, mean of 3 seeds | -18.9% | -0.12 | -0.17 | 44% | -0.08 | 20 | 45 | 144 | 0.4% | -0.10 | -0.254% (loses before fees) |
| Phase 3 agent (c), continual + retrain [Phase 3 primary], mean of 3 seeds | -46.5% | -0.27 | -0.38 | 77% | -0.13 | 46 | 104 | 84 | 5.8% | -0.05 | -0.172% (loses before fees) |
| Phase 3 agent (a), static per fold, mean of 3 seeds | -45.4% | -0.33 | -0.46 | 72% | -0.14 | 41 | 100 | 108 | 3.6% | -0.19 | -0.219% (loses before fees) |
| Buy-and-hold (perp) | +249.5% | 0.64 | 0.91 | 79% | 0.29 | 0 | 0 | 53579 | 11.0% | 0.83 | > 5% |
| Buy-and-hold (spot) | +584.3% | 0.83 | 1.17 | 77% | 0.48 | 0 | 0 | 53579 | 0.0% | 0.83 | > 5% |
| Momentum (daily 30-day, long/short) | +308.7% | 0.68 | 0.97 | 61% | 0.42 | 62 | 31 | 281 | 11.2% | 0.87 | 0.418% |
| Random agent (mean of 10) | -87.3% | -0.59 | -0.84 | 93% | -0.35 | 323 | 243 | 36 | 26.5% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +261.7% | 0.70 | 0.98 | 69% | 0.34 | 23 | 95 | 53579 | 11.0% | 0.94 | 0.951% |
| *reference: momentum through the Phase 3 risk manager* | +295.7% | 0.72 | 1.02 | 50% | 0.51 | 74 | 128 | 281 | 10.7% | 0.96 | 0.354% |

Agent rows run through the Phase 3 risk manager; benchmarks run without it (the two reference rows show what it does to buy-and-hold and momentum). Gross Sharpe = before every cost (fees, spread, slippage, funding) with the same positions. Break-even fee = the fee a side at which the stitched net return would be zero.

## By seed (BTC, full span): Sharpe / net return / break-even fee

| Variant | seed 0 | seed 1 | seed 2 | mean, 0.10% | mean, 0.05% |
|---|---|---|---|---|---|
| Q agent, BTC+ETH pooled, expanding, readings | 0.52 / +94% / 0.302% (0.05%: 0.59) | 0.40 / +58% / 0.290% (0.05%: 0.50) | 0.51 / +84% / 0.302% (0.05%: 0.59) | 0.48 / +79% | 0.56 / +106% |
| SP agent, BTC+ETH pooled, expanding, readings | 0.58 / +109% / 0.233% (0.05%: 0.75) | 0.64 / +134% / 0.270% (0.05%: 0.82) | 0.52 / +78% / 0.222% (0.05%: 0.71) | 0.58 / +107% | 0.76 / +176% |
| SP agent, 8 markets pooled, expanding, readings | 0.68 / +138% / 0.251% (0.05%: 0.89) | 0.65 / +122% / 0.289% (0.05%: 0.80) | 0.63 / +121% / 0.270% (0.05%: 0.77) | 0.65 / +127% | 0.82 / +196% |
| SP agent, BTC+ETH pooled, expanding, Phase 3 inputs | 0.08 / -11% / 0.048% (0.05%: 0.15) | -0.11 / -34% / -0.046% (loses before fees) (0.05%: -0.04) | 0.46 / +71% / 0.306% (0.05%: 0.53) | 0.14 / +9% | 0.22 / +23% |
| SP agent, one asset, expanding, readings | 0.66 / +145% / 0.242% (0.05%: 0.84) | 0.45 / +71% / 0.216% (0.05%: 0.62) | 1.43 / +907% / 0.516% (0.05%: 1.58) | 0.85 / +374% | 1.01 / +525% |
| SP agent, one asset, expanding, Phase 3 inputs | 0.32 / +34% / 0.186% (0.05%: 0.44) | 0.06 / -10% / 0.060% (0.05%: 0.15) | 1.23 / +693% / 0.748% (0.05%: 1.29) | 0.54 / +239% | 0.63 / +285% |
| SP agent, one asset, 12-month window, readings | -0.91 / -63% / -1.000% (loses before fees) (0.05%: -0.87) | -0.21 / -33% / -0.002% (loses before fees) (0.05%: -0.07) | -1.04 / -70% / -0.920% (loses before fees) (0.05%: -0.99) | -0.72 / -55% | -0.64 / -50% |
| SP agent, one asset, 12-month window, Phase 3 inputs | -0.45 / -45% / -0.430% (loses before fees) (0.05%: -0.40) | -0.22 / -33% / -0.477% (loses before fees) (0.05%: -0.20) | 0.15 / +6% / 0.132% (0.05%: 0.22) | -0.18 / -24% | -0.12 / -19% |

## BTC up to 2025-11-11 (the loop's development span): against the loop's rules A and B

The loop chose A and B on data before 2025-11-11 and keeps 2025-11-11 .. 2026-11-11 sealed, so this table stops there (21 folds). A and B use the loop's spot backtester (long legs up to 1x pay no funding), no risk manager.

### 0.10% a side

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Q agent, BTC+ETH pooled, expanding, readings [primary], mean of 3 seeds** | **+122.1%** | **0.67** | **0.94** | **41%** | **0.41** | **52** | **118** | **149** | **9.4%** | **0.99** | **0.393%** |
| &nbsp;&nbsp;seed 0 | +134.2% | 0.69 | 0.97 | 40% | 0.45 | 59 | 133 | 120 | 10.5% | 1.04 | 0.384% |
| &nbsp;&nbsp;seed 1 | +79.8% | 0.53 | 0.74 | 45% | 0.27 | 43 | 101 | 215 | 8.0% | 0.80 | 0.366% |
| &nbsp;&nbsp;seed 2 | +152.3% | 0.79 | 1.12 | 38% | 0.52 | 55 | 119 | 112 | 9.7% | 1.14 | 0.429% |
| SP agent, BTC+ETH pooled, expanding, readings, mean of 3 seeds | +100.6% | 0.62 | 0.90 | 35% | 0.44 | 97 | 196 | 78 | 13.4% | 1.09 | 0.238% |
| SP agent, 8 markets pooled, expanding, readings, mean of 3 seeds | +118.5% | 0.71 | 1.05 | 34% | 0.52 | 93 | 182 | 71 | 13.0% | 1.20 | 0.267% |
| SP agent, BTC+ETH pooled, expanding, Phase 3 inputs, mean of 3 seeds | +10.0% | 0.15 | 0.22 | 49% | 0.06 | 45 | 108 | 167 | 5.7% | 0.35 | 0.113% |
| SP agent, one asset, expanding, readings, mean of 3 seeds | +261.2% | 0.77 | 1.12 | 36% | 0.67 | 105 | 213 | 76 | 14.7% | 1.26 | 0.278% |
| SP agent, one asset, expanding, Phase 3 inputs, mean of 3 seeds | +228.0% | 0.51 | 0.74 | 45% | 0.50 | 57 | 132 | 118 | 8.0% | 0.79 | 0.302% |
| SP agent, one asset, 12-month window, readings, mean of 3 seeds | -56.0% | -0.79 | -1.09 | 68% | -0.22 | 39 | 100 | 138 | 4.8% | -0.57 | -0.635% (loses before fees) |
| SP agent, one asset, 12-month window, Phase 3 inputs, mean of 3 seeds | -22.6% | -0.18 | -0.25 | 44% | -0.11 | 23 | 51 | 144 | 1.5% | -0.10 | -0.258% (loses before fees) |
| Phase 3 agent (c), continual + retrain [Phase 3 primary], mean of 3 seeds | -45.0% | -0.29 | -0.41 | 76% | -0.15 | 54 | 121 | 79 | 9.6% | 0.06 | -0.119% (loses before fees) |
| Phase 3 agent (a), static per fold, mean of 3 seeds | -46.0% | -0.36 | -0.50 | 72% | -0.16 | 47 | 116 | 104 | 6.6% | -0.11 | -0.170% (loses before fees) |
| Buy-and-hold (perp) | +418.4% | 0.83 | 1.18 | 79% | 0.48 | 0 | 0 | 44808 | 12.5% | 1.03 | > 5% |
| Buy-and-hold (spot) | +879.7% | 1.03 | 1.46 | 77% | 0.73 | 0 | 0 | 44808 | 0.0% | 1.03 | > 5% |
| Momentum (daily 30-day, long/short) | +218.6% | 0.67 | 0.95 | 63% | 0.41 | 60 | 30 | 293 | 15.2% | 0.92 | 0.477% |
| Random agent (mean of 10) | -92.0% | -0.91 | -1.28 | 95% | -0.45 | 323 | 243 | 36 | 42.9% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +398.4% | 0.91 | 1.28 | 68% | 0.54 | 20 | 80 | 44808 | 12.8% | 1.19 | 1.697% |
| *reference: momentum through the Phase 3 risk manager* | +250.2% | 0.76 | 1.07 | 49% | 0.56 | 64 | 101 | 293 | 14.2% | 1.06 | 0.480% |
| A: loop H29 H30 1.5x/0x spot | +1809.3% | 1.19 | 1.69 | 65% | 1.20 | 45 | 30 | 328 | 10.8% | 1.35 | 1.379% |
| B: loop H29 H31 trail 4 ATR spot | +1301.3% | 1.32 | 1.88 | 53% | 1.28 | 46 | 53 | 315 | 7.6% | 1.48 | 1.223% |

### 0.05% a side

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Q agent, BTC+ETH pooled, expanding, readings [primary], mean of 3 seeds** | **+151.2%** | **0.76** | **1.06** | **40%** | **0.50** | **52** | **118** | **149** | **6.8%** | **0.99** | **0.392%** |
| &nbsp;&nbsp;seed 0 | +156.4% | 0.75 | 1.05 | 39% | 0.51 | 58 | 134 | 120 | 7.6% | 1.00 | 0.365% |
| &nbsp;&nbsp;seed 1 | +110.5% | 0.63 | 0.88 | 44% | 0.35 | 43 | 101 | 215 | 5.8% | 0.83 | 0.386% |
| &nbsp;&nbsp;seed 2 | +186.5% | 0.88 | 1.25 | 36% | 0.64 | 55 | 118 | 112 | 6.9% | 1.13 | 0.426% |
| SP agent, BTC+ETH pooled, expanding, readings, mean of 3 seeds | +163.9% | 0.80 | 1.18 | 31% | 0.70 | 95 | 186 | 78 | 8.4% | 1.10 | 0.247% |
| SP agent, 8 markets pooled, expanding, readings, mean of 3 seeds | +182.9% | 0.89 | 1.33 | 30% | 0.77 | 93 | 178 | 71 | 8.4% | 1.21 | 0.270% |
| SP agent, BTC+ETH pooled, expanding, Phase 3 inputs, mean of 3 seeds | +23.5% | 0.23 | 0.33 | 48% | 0.11 | 45 | 108 | 167 | 3.5% | 0.35 | 0.114% |
| SP agent, one asset, expanding, readings, mean of 3 seeds | +373.3% | 0.95 | 1.39 | 33% | 0.95 | 105 | 208 | 76 | 9.4% | 1.26 | 0.281% |
| SP agent, one asset, expanding, Phase 3 inputs, mean of 3 seeds | +271.3% | 0.61 | 0.89 | 43% | 0.59 | 58 | 133 | 118 | 5.1% | 0.79 | 0.294% |
| SP agent, one asset, 12-month window, readings, mean of 3 seeds | -51.2% | -0.71 | -0.98 | 66% | -0.21 | 40 | 102 | 138 | 2.9% | -0.58 | -0.599% (loses before fees) |
| SP agent, one asset, 12-month window, Phase 3 inputs, mean of 3 seeds | -17.6% | -0.12 | -0.17 | 44% | -0.09 | 23 | 52 | 144 | 0.4% | -0.10 | -0.254% (loses before fees) |
| Phase 3 agent (c), continual + retrain [Phase 3 primary], mean of 3 seeds | -36.8% | -0.19 | -0.27 | 74% | -0.12 | 54 | 121 | 79 | 7.0% | 0.06 | -0.118% (loses before fees) |
| Phase 3 agent (a), static per fold, mean of 3 seeds | -39.3% | -0.27 | -0.38 | 69% | -0.14 | 48 | 118 | 104 | 4.4% | -0.11 | -0.167% (loses before fees) |
| Buy-and-hold (perp) | +418.6% | 0.83 | 1.18 | 79% | 0.48 | 0 | 0 | 44808 | 12.5% | 1.03 | > 5% |
| Buy-and-hold (spot) | +880.2% | 1.03 | 1.46 | 77% | 0.73 | 0 | 0 | 44808 | 0.0% | 1.03 | > 5% |
| Momentum (daily 30-day, long/short) | +271.2% | 0.72 | 1.02 | 61% | 0.48 | 60 | 30 | 293 | 12.3% | 0.92 | 0.477% |
| Random agent (mean of 10) | -81.7% | -0.59 | -0.83 | 91% | -0.36 | 323 | 243 | 36 | 26.8% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +413.1% | 0.92 | 1.30 | 69% | 0.55 | 21 | 86 | 44808 | 12.1% | 1.18 | 1.566% |
| *reference: momentum through the Phase 3 risk manager* | +290.7% | 0.81 | 1.14 | 48% | 0.63 | 67 | 113 | 293 | 11.2% | 1.05 | 0.445% |
| A: loop H29 H30 1.5x/0x spot | +2040.2% | 1.22 | 1.74 | 64% | 1.28 | 45 | 30 | 328 | 8.6% | 1.35 | 1.379% |
| B: loop H29 H31 trail 4 ATR spot | +1474.7% | 1.37 | 1.95 | 51% | 1.39 | 46 | 53 | 315 | 5.3% | 1.48 | 1.223% |

## ETH: stitched out of sample 2020-10-01 .. 2026-11-11

### 0.10% a side

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Q agent, BTC+ETH pooled, expanding, readings [primary], mean of 3 seeds** | **+263.1%** | **0.77** | **1.07** | **50%** | **0.49** | **63** | **158** | **104** | **11.6%** | **1.11** | **0.419%** |
| &nbsp;&nbsp;seed 0 | +416.0% | 0.94 | 1.32 | 39% | 0.79 | 65 | 168 | 109 | 12.5% | 1.30 | 0.510% |
| &nbsp;&nbsp;seed 1 | +233.5% | 0.75 | 1.04 | 58% | 0.38 | 64 | 161 | 107 | 12.0% | 1.10 | 0.408% |
| &nbsp;&nbsp;seed 2 | +139.8% | 0.61 | 0.85 | 52% | 0.30 | 60 | 147 | 97 | 10.4% | 0.95 | 0.339% |
| SP agent, BTC+ETH pooled, expanding, readings, mean of 3 seeds | +37.6% | 0.26 | 0.37 | 55% | 0.10 | 89 | 218 | 63 | 13.3% | 0.70 | 0.136% |
| SP agent, 8 markets pooled, expanding, readings, mean of 3 seeds | +244.0% | 0.70 | 1.01 | 48% | 0.49 | 94 | 211 | 74 | 13.9% | 1.15 | 0.299% |
| SP agent, BTC+ETH pooled, expanding, Phase 3 inputs, mean of 3 seeds | +10.0% | 0.20 | 0.29 | 57% | 0.03 | 41 | 109 | 142 | 6.4% | 0.41 | 0.136% |
| SP agent, one asset, expanding, readings, mean of 3 seeds | +199.9% | 0.67 | 0.96 | 48% | 0.39 | 105 | 241 | 62 | 16.2% | 1.18 | 0.270% |
| SP agent, one asset, expanding, Phase 3 inputs, mean of 3 seeds | -33.3% | -0.16 | -0.22 | 53% | -0.12 | 31 | 91 | 138 | 4.6% | 0.02 | -0.139% (loses before fees) |
| SP agent, one asset, 12-month window, readings, mean of 3 seeds | -51.9% | -0.54 | -0.75 | 63% | -0.20 | 43 | 104 | 87 | 5.4% | -0.29 | -0.276% (loses before fees) |
| SP agent, one asset, 12-month window, Phase 3 inputs, mean of 3 seeds | -31.0% | -0.20 | -0.27 | 53% | -0.12 | 35 | 91 | 101 | 4.8% | 0.02 | -0.083% (loses before fees) |
| Phase 3 agent (c), continual + retrain [Phase 3 primary], mean of 3 seeds | -4.9% | 0.13 | 0.18 | 75% | -0.01 | 52 | 130 | 89 | 11.2% | 0.48 | 0.081% |
| Phase 3 agent (a), static per fold, mean of 3 seeds | -43.6% | -0.25 | -0.35 | 76% | -0.13 | 46 | 131 | 132 | 8.9% | 0.04 | -0.192% (loses before fees) |
| Buy-and-hold (perp) | +172.2% | 0.60 | 0.85 | 82% | 0.22 | 0 | 0 | 53556 | 12.1% | 0.76 | > 5% |
| Buy-and-hold (spot) | +470.6% | 0.76 | 1.07 | 81% | 0.40 | 0 | 0 | 53556 | 0.0% | 0.76 | > 5% |
| Momentum (daily 30-day, long/short) | +727.8% | 0.83 | 1.18 | 80% | 0.51 | 55 | 28 | 317 | 15.9% | 1.04 | 0.722% |
| Random agent (mean of 10) | -95.8% | -0.63 | -0.89 | 97% | -0.45 | 323 | 243 | 36 | 45.4% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +170.5% | 0.58 | 0.81 | 64% | 0.28 | 21 | 88 | 53556 | 11.7% | 0.82 | 0.867% |
| *reference: momentum through the Phase 3 risk manager* | +688.0% | 0.91 | 1.30 | 70% | 0.57 | 65 | 132 | 317 | 14.3% | 1.19 | 0.616% |

### 0.05% a side

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Q agent, BTC+ETH pooled, expanding, readings [primary], mean of 3 seeds** | **+341.1%** | **0.86** | **1.19** | **49%** | **0.56** | **63** | **157** | **104** | **8.5%** | **1.11** | **0.418%** |
| &nbsp;&nbsp;seed 0 | +542.3% | 1.04 | 1.46 | 41% | 0.88 | 63 | 158 | 109 | 9.1% | 1.30 | 0.529% |
| &nbsp;&nbsp;seed 1 | +302.5% | 0.84 | 1.16 | 57% | 0.45 | 64 | 161 | 107 | 8.8% | 1.09 | 0.403% |
| &nbsp;&nbsp;seed 2 | +178.3% | 0.69 | 0.96 | 51% | 0.36 | 61 | 153 | 97 | 7.6% | 0.93 | 0.322% |
| SP agent, BTC+ETH pooled, expanding, readings, mean of 3 seeds | +80.6% | 0.40 | 0.58 | 52% | 0.21 | 89 | 216 | 63 | 8.9% | 0.70 | 0.135% |
| SP agent, 8 markets pooled, expanding, readings, mean of 3 seeds | +335.1% | 0.83 | 1.20 | 46% | 0.62 | 95 | 214 | 74 | 9.3% | 1.13 | 0.290% |
| SP agent, BTC+ETH pooled, expanding, Phase 3 inputs, mean of 3 seeds | +23.7% | 0.27 | 0.38 | 56% | 0.06 | 42 | 109 | 142 | 4.3% | 0.41 | 0.132% |
| SP agent, one asset, expanding, readings, mean of 3 seeds | +314.9% | 0.84 | 1.21 | 45% | 0.56 | 107 | 238 | 62 | 11.0% | 1.18 | 0.271% |
| SP agent, one asset, expanding, Phase 3 inputs, mean of 3 seeds | -27.8% | -0.11 | -0.16 | 52% | -0.10 | 32 | 95 | 138 | 3.1% | 0.01 | -0.142% (loses before fees) |
| SP agent, one asset, 12-month window, readings, mean of 3 seeds | -46.8% | -0.46 | -0.64 | 61% | -0.18 | 43 | 102 | 87 | 3.3% | -0.30 | -0.286% (loses before fees) |
| SP agent, one asset, 12-month window, Phase 3 inputs, mean of 3 seeds | -21.8% | -0.10 | -0.14 | 48% | -0.09 | 35 | 86 | 101 | 3.0% | 0.03 | -0.072% (loses before fees) |
| Phase 3 agent (c), continual + retrain [Phase 3 primary], mean of 3 seeds | +6.6% | 0.19 | 0.26 | 74% | 0.01 | 53 | 132 | 89 | 8.6% | 0.46 | 0.068% |
| Phase 3 agent (a), static per fold, mean of 3 seeds | -34.6% | -0.18 | -0.25 | 75% | -0.10 | 47 | 136 | 132 | 6.8% | 0.05 | -0.182% (loses before fees) |
| Buy-and-hold (perp) | +172.4% | 0.60 | 0.85 | 82% | 0.22 | 0 | 0 | 53556 | 12.1% | 0.76 | > 5% |
| Buy-and-hold (spot) | +470.9% | 0.76 | 1.07 | 81% | 0.40 | 0 | 0 | 53556 | 0.0% | 0.76 | > 5% |
| Momentum (daily 30-day, long/short) | +880.0% | 0.87 | 1.23 | 79% | 0.57 | 55 | 28 | 317 | 13.2% | 1.04 | 0.722% |
| Random agent (mean of 10) | -88.7% | -0.38 | -0.53 | 93% | -0.36 | 323 | 243 | 36 | 29.3% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +176.6% | 0.58 | 0.82 | 63% | 0.29 | 24 | 98 | 53556 | 10.9% | 0.81 | 0.748% |
| *reference: momentum through the Phase 3 risk manager* | +879.8% | 0.98 | 1.40 | 68% | 0.67 | 71 | 155 | 317 | 11.5% | 1.20 | 0.573% |

### ETH up to 2025-11-11, 0.10%

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Q agent, BTC+ETH pooled, expanding, readings [primary], mean of 3 seeds** | **+290.5%** | **0.86** | **1.20** | **50%** | **0.63** | **71** | **179** | **105** | **13.2%** | **1.23** | **0.447%** |
| &nbsp;&nbsp;seed 0 | +546.0% | 1.17 | 1.64 | 39% | 1.13 | 71 | 182 | 108 | 13.9% | 1.54 | 0.614% |
| &nbsp;&nbsp;seed 1 | +195.5% | 0.76 | 1.05 | 58% | 0.41 | 74 | 187 | 107 | 13.9% | 1.13 | 0.387% |
| &nbsp;&nbsp;seed 2 | +130.0% | 0.65 | 0.91 | 52% | 0.34 | 67 | 168 | 99 | 11.9% | 1.01 | 0.341% |
| SP agent, BTC+ETH pooled, expanding, readings, mean of 3 seeds | +30.9% | 0.25 | 0.36 | 55% | 0.10 | 99 | 244 | 60 | 15.0% | 0.73 | 0.126% |
| SP agent, 8 markets pooled, expanding, readings, mean of 3 seeds | +184.8% | 0.70 | 1.01 | 48% | 0.51 | 107 | 240 | 67 | 15.8% | 1.19 | 0.280% |
| SP agent, BTC+ETH pooled, expanding, Phase 3 inputs, mean of 3 seeds | +23.2% | 0.27 | 0.39 | 57% | 0.07 | 44 | 117 | 129 | 6.9% | 0.49 | 0.181% |
| SP agent, one asset, expanding, readings, mean of 3 seeds | +166.6% | 0.72 | 1.03 | 48% | 0.43 | 117 | 270 | 55 | 18.1% | 1.28 | 0.265% |
| SP agent, one asset, expanding, Phase 3 inputs, mean of 3 seeds | -24.9% | -0.09 | -0.12 | 51% | -0.11 | 31 | 90 | 147 | 4.6% | 0.08 | -0.118% (loses before fees) |
| SP agent, one asset, 12-month window, readings, mean of 3 seeds | -48.8% | -0.58 | -0.80 | 63% | -0.22 | 51 | 122 | 83 | 6.4% | -0.30 | -0.272% (loses before fees) |
| SP agent, one asset, 12-month window, Phase 3 inputs, mean of 3 seeds | -30.5% | -0.21 | -0.30 | 53% | -0.14 | 41 | 105 | 101 | 5.6% | 0.02 | -0.084% (loses before fees) |
| Phase 3 agent (c), continual + retrain [Phase 3 primary], mean of 3 seeds | +1.3% | 0.17 | 0.23 | 72% | 0.00 | 57 | 143 | 85 | 12.6% | 0.55 | 0.099% |
| Phase 3 agent (a), static per fold, mean of 3 seeds | -48.2% | -0.32 | -0.45 | 76% | -0.17 | 48 | 142 | 136 | 9.6% | -0.02 | -0.242% (loses before fees) |
| Buy-and-hold (perp) | +383.7% | 0.79 | 1.11 | 82% | 0.44 | 0 | 0 | 44784 | 14.0% | 0.96 | > 5% |
| Buy-and-hold (spot) | +889.1% | 0.96 | 1.35 | 81% | 0.69 | 0 | 0 | 44784 | 0.0% | 0.96 | > 5% |
| Momentum (daily 30-day, long/short) | +447.8% | 0.82 | 1.15 | 80% | 0.49 | 53 | 27 | 327 | 17.4% | 1.03 | 0.718% |
| Random agent (mean of 10) | -93.7% | -0.62 | -0.88 | 96% | -0.47 | 322 | 242 | 36 | 45.8% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +347.2% | 0.83 | 1.17 | 63% | 0.54 | 16 | 69 | 44784 | 12.4% | 1.08 | 1.876% |
| *reference: momentum through the Phase 3 risk manager* | +505.7% | 0.93 | 1.33 | 70% | 0.60 | 62 | 126 | 327 | 14.9% | 1.22 | 0.669% |

### By seed (ETH, full span)

| Variant | seed 0 | seed 1 | seed 2 | mean, 0.10% | mean, 0.05% |
|---|---|---|---|---|---|
| Q agent, BTC+ETH pooled, expanding, readings | 0.94 / +416% / 0.510% (0.05%: 1.04) | 0.75 / +234% / 0.408% (0.05%: 0.84) | 0.61 / +140% / 0.339% (0.05%: 0.69) | 0.77 / +263% | 0.86 / +341% |
| SP agent, BTC+ETH pooled, expanding, readings | 0.46 / +79% / 0.205% (0.05%: 0.60) | -0.16 / -43% / -0.002% (loses before fees) (0.05%: -0.01) | 0.46 / +76% / 0.206% (0.05%: 0.62) | 0.26 / +38% | 0.40 / +81% |
| SP agent, 8 markets pooled, expanding, readings | 0.19 / +7% / 0.110% (0.05%: 0.34) | 0.82 / +257% / 0.332% (0.05%: 0.92) | 1.09 / +468% / 0.455% (0.05%: 1.22) | 0.70 / +244% | 0.83 / +335% |
| SP agent, BTC+ETH pooled, expanding, Phase 3 inputs | 0.24 / +17% / 0.157% (0.05%: 0.30) | 0.16 / +0% / 0.100% (0.05%: 0.23) | 0.22 / +13% / 0.152% (0.05%: 0.27) | 0.20 / +10% | 0.27 / +24% |
| SP agent, one asset, expanding, readings | 0.82 / +277% / 0.358% (0.05%: 0.96) | 0.38 / +52% / 0.155% (0.05%: 0.59) | 0.82 / +270% / 0.298% (0.05%: 0.98) | 0.67 / +200% | 0.84 / +315% |
| SP agent, one asset, expanding, Phase 3 inputs | 0.01 / -12% / 0.010% (0.05%: 0.06) | -0.45 / -57% / -0.384% (loses before fees) (0.05%: -0.42) | -0.05 / -30% / -0.042% (loses before fees) (0.05%: 0.02) | -0.16 / -33% | -0.11 / -28% |
| SP agent, one asset, 12-month window, readings | -0.44 / -43% / -0.169% (loses before fees) (0.05%: -0.36) | -0.10 / -24% / 0.007% (0.05%: -0.01) | -1.08 / -88% / -0.668% (loses before fees) (0.05%: -1.00) | -0.54 / -52% | -0.46 / -47% |
| SP agent, one asset, 12-month window, Phase 3 inputs | -0.43 / -41% / -0.215% (loses before fees) (0.05%: -0.37) | 0.07 / -4% / 0.073% (0.05%: 0.16) | -0.23 / -47% / -0.107% (loses before fees) (0.05%: -0.10) | -0.20 / -31% | -0.10 / -22% |

## Edge before costs

| Variant | Asset | Span | Gross Sharpe by seed | Mean | t (approx.) | Break-even fee by seed | Net Sharpe 0.10% (mean) |
|---|---|---|---|---|---|---|---|
| Q agent, BTC+ETH pooled, expanding, readings | BTCUSDT | 2020-10 .. 2026-11 | 0.84, 0.65, 0.84 | 0.78 | 1.9 | 0.302%, 0.290%, 0.302% | 0.48 |
| Q agent, BTC+ETH pooled, expanding, readings | BTCUSDT | to 2025-11-11 | 1.04, 0.80, 1.14 | 0.99 | 2.2 | 0.384%, 0.366%, 0.429% | 0.67 |
| Q agent, BTC+ETH pooled, expanding, readings | ETHUSDT | 2020-10 .. 2026-11 | 1.30, 1.10, 0.95 | 1.11 | 2.8 | 0.510%, 0.408%, 0.339% | 0.77 |
| Q agent, BTC+ETH pooled, expanding, readings | ETHUSDT | to 2025-11-11 | 1.54, 1.13, 1.01 | 1.23 | 2.8 | 0.614%, 0.387%, 0.341% | 0.86 |
| SP agent, BTC+ETH pooled, expanding, readings | BTCUSDT | 2020-10 .. 2026-11 | 1.05, 1.06, 0.95 | 1.02 | 2.5 | 0.233%, 0.270%, 0.222% | 0.58 |
| SP agent, BTC+ETH pooled, expanding, readings | BTCUSDT | to 2025-11-11 | 1.08, 1.18, 1.02 | 1.09 | 2.5 | 0.224%, 0.275%, 0.217% | 0.62 |
| SP agent, BTC+ETH pooled, expanding, readings | ETHUSDT | 2020-10 .. 2026-11 | 0.91, 0.29, 0.91 | 0.70 | 1.7 | 0.205%, -0.002% (loses before fees), 0.206% | 0.26 |
| SP agent, BTC+ETH pooled, expanding, readings | ETHUSDT | to 2025-11-11 | 1.00, 0.25, 0.94 | 0.73 | 1.6 | 0.209%, -0.021% (loses before fees), 0.190% | 0.25 |
| SP agent, 8 markets pooled, expanding, readings | BTCUSDT | 2020-10 .. 2026-11 | 1.21, 1.03, 1.03 | 1.09 | 2.7 | 0.251%, 0.289%, 0.270% | 0.65 |
| SP agent, 8 markets pooled, expanding, readings | BTCUSDT | to 2025-11-11 | 1.27, 1.13, 1.19 | 1.20 | 2.7 | 0.234%, 0.281%, 0.285% | 0.71 |
| SP agent, 8 markets pooled, expanding, readings | ETHUSDT | 2020-10 .. 2026-11 | 0.73, 1.23, 1.47 | 1.15 | 2.8 | 0.110%, 0.332%, 0.455% | 0.70 |
| SP agent, 8 markets pooled, expanding, readings | ETHUSDT | to 2025-11-11 | 0.81, 1.22, 1.53 | 1.19 | 2.7 | 0.110%, 0.307%, 0.424% | 0.70 |
| SP agent, BTC+ETH pooled, expanding, Phase 3 inputs | BTCUSDT | 2020-10 .. 2026-11 | 0.21, 0.14, 0.64 | 0.33 | 0.8 | 0.048%, -0.046% (loses before fees), 0.306% | 0.14 |
| SP agent, BTC+ETH pooled, expanding, Phase 3 inputs | BTCUSDT | to 2025-11-11 | 0.33, 0.05, 0.68 | 0.35 | 0.8 | 0.145%, -0.097% (loses before fees), 0.291% | 0.15 |
| SP agent, BTC+ETH pooled, expanding, Phase 3 inputs | ETHUSDT | 2020-10 .. 2026-11 | 0.49, 0.38, 0.37 | 0.41 | 1.0 | 0.157%, 0.100%, 0.152% | 0.20 |
| SP agent, BTC+ETH pooled, expanding, Phase 3 inputs | ETHUSDT | to 2025-11-11 | 0.66, 0.31, 0.50 | 0.49 | 1.1 | 0.277%, 0.038%, 0.227% | 0.27 |
| SP agent, one asset, expanding, readings | BTCUSDT | 2020-10 .. 2026-11 | 1.16, 0.84, 1.88 | 1.29 | 3.2 | 0.242%, 0.216%, 0.516% | 0.85 |
| SP agent, one asset, expanding, readings | BTCUSDT | to 2025-11-11 | 1.14, 0.73, 1.91 | 1.26 | 2.9 | 0.211%, 0.152%, 0.473% | 0.77 |
| SP agent, one asset, expanding, readings | ETHUSDT | 2020-10 .. 2026-11 | 1.25, 0.99, 1.29 | 1.18 | 2.9 | 0.358%, 0.155%, 0.298% | 0.67 |
| SP agent, one asset, expanding, readings | ETHUSDT | to 2025-11-11 | 1.33, 1.12, 1.38 | 1.28 | 2.9 | 0.338%, 0.174%, 0.284% | 0.72 |
| SP agent, one asset, expanding, Phase 3 inputs | BTCUSDT | 2020-10 .. 2026-11 | 0.60, 0.32, 1.46 | 0.79 | 2.0 | 0.186%, 0.060%, 0.748% | 0.54 |
| SP agent, one asset, expanding, Phase 3 inputs | BTCUSDT | to 2025-11-11 | 0.47, 0.31, 1.60 | 0.79 | 1.8 | 0.108%, 0.049%, 0.748% | 0.51 |
| SP agent, one asset, expanding, Phase 3 inputs | ETHUSDT | 2020-10 .. 2026-11 | 0.21, -0.30, 0.14 | 0.02 | 0.0 | 0.010%, -0.384% (loses before fees), -0.042% (loses before fees) | -0.16 |
| SP agent, one asset, expanding, Phase 3 inputs | ETHUSDT | to 2025-11-11 | 0.19, -0.16, 0.21 | 0.08 | 0.2 | -0.025% (loses before fees), -0.333% (loses before fees), 0.005% | -0.09 |
| SP agent, one asset, 12-month window, readings | BTCUSDT | 2020-10 .. 2026-11 | -0.87, 0.21, -0.90 | -0.52 | -1.3 | -1.000% (loses before fees), -0.002% (loses before fees), -0.920% (loses before fees) | -0.72 |
| SP agent, one asset, 12-month window, readings | BTCUSDT | to 2025-11-11 | -0.93, 0.19, -0.98 | -0.57 | -1.3 | -0.972% (loses before fees), -0.014% (loses before fees), -0.920% (loses before fees) | -0.79 |
| SP agent, one asset, 12-month window, readings | ETHUSDT | 2020-10 .. 2026-11 | -0.18, 0.24, -0.93 | -0.29 | -0.7 | -0.169% (loses before fees), 0.007%, -0.668% (loses before fees) | -0.54 |
| SP agent, one asset, 12-month window, readings | ETHUSDT | to 2025-11-11 | -0.18, 0.34, -1.06 | -0.30 | -0.7 | -0.154% (loses before fees), 0.038%, -0.700% (loses before fees) | -0.58 |
| SP agent, one asset, 12-month window, Phase 3 inputs | BTCUSDT | 2020-10 .. 2026-11 | -0.39, -0.20, 0.30 | -0.10 | -0.2 | -0.430% (loses before fees), -0.477% (loses before fees), 0.132% | -0.18 |
| SP agent, one asset, 12-month window, Phase 3 inputs | BTCUSDT | to 2025-11-11 | -0.41, -0.22, 0.32 | -0.10 | -0.2 | -0.429% (loses before fees), -0.477% (loses before fees), 0.132% | -0.18 |
| SP agent, one asset, 12-month window, Phase 3 inputs | ETHUSDT | 2020-10 .. 2026-11 | -0.23, 0.26, 0.02 | 0.02 | 0.0 | -0.215% (loses before fees), 0.073%, -0.107% (loses before fees) | -0.20 |
| SP agent, one asset, 12-month window, Phase 3 inputs | ETHUSDT | to 2025-11-11 | -0.25, 0.28, 0.02 | 0.02 | 0.0 | -0.215% (loses before fees), 0.073%, -0.111% (loses before fees) | -0.21 |

t (approx.) = gross Sharpe x sqrt(years): about 2 is the usual bar for 'distinguishable from luck' (one test; with this many variants a higher bar is fair).

## Does more data help? (the ablation grid, all frozen before any result)

| Variant | Model | Data | Inputs | BTC net Sharpe | BTC gross | ETH net Sharpe | ETH gross | train / val / test Sharpe (BTC) | neutral folds (BTC) | rows per model, last fold |
|---|---|---|---|---|---|---|---|---|---|---|
| q_pool2_full | Q | BTC+ETH, expanding from 2019 | Phase 3 + readings | 0.48 | 0.78 | 0.77 | 1.11 | 1.90 / 0.95 / 0.25 | 39% | 512,260 |
| sp_pool2_full | SP | BTC+ETH, expanding from 2019 | Phase 3 + readings | 0.58 | 1.02 | 0.26 | 0.70 | 1.22 / 0.90 / 0.19 | 48% | 322,903 |
| sp_pool8_full | SP | 8 markets, expanding from 2019 | Phase 3 + readings | 0.65 | 1.09 | 0.70 | 1.15 | 1.08 / 0.89 / 0.21 | 48% | 922,547 |
| sp_pool2_p3 | SP | BTC+ETH, expanding from 2019 | Phase 3 | 0.14 | 0.33 | 0.20 | 0.41 | 0.85 / 0.65 / -0.25 | 45% | 322,903 |
| sp_single_full | SP | one asset, expanding from 2019 | Phase 3 + readings | 0.85 | 1.29 | 0.67 | 1.18 | 1.35 / 0.88 / 0.32 | 44% | 155,820 |
| sp_single_p3 | SP | one asset, expanding from 2019 | Phase 3 | 0.54 | 0.79 | -0.16 | 0.02 | 0.82 / 0.70 / 0.10 | 48% | 155,820 |
| sp_single12_full | SP | one asset, 12-month window | Phase 3 + readings | -0.72 | -0.52 | -0.54 | -0.29 | 1.20 / 0.24 / -0.55 | 59% | 21,727 |
| sp_single12_p3 | SP | one asset, 12-month window | Phase 3 | -0.18 | -0.10 | -0.20 | 0.02 | 0.54 / 0.18 / -0.49 | 67% | 21,727 |

Net Sharpe at 0.10%, seed means, full span; gross = before costs. Reading: compare a row with the one that differs in one respect only (12-month window vs expanding, one asset vs pooled, Phase 3 inputs vs + readings).

## Overfitting flags

**BTCUSDT**

| Variant | train_test_sharpe_gap | seed_dispersion | beats_benchmarks_in_under_half_the_folds | fee_sign_flip | edge_only_at_0.05 | high_turnover | degenerate_policy |
|---|---|---|---|---|---|---|---|
| Q agent, BTC+ETH pooled, expanding, readings | FIRED | - | FIRED | - | - | - | - |
| SP agent, BTC+ETH pooled, expanding, readings | FIRED | - | FIRED | - | FIRED | - | - |
| SP agent, 8 markets pooled, expanding, readings | - | - | FIRED | - | - | - | - |
| SP agent, BTC+ETH pooled, expanding, Phase 3 inputs | FIRED | FIRED | FIRED | FIRED | - | - | - |
| SP agent, one asset, expanding, readings | FIRED | FIRED | FIRED | - | - | FIRED | - |
| SP agent, one asset, expanding, Phase 3 inputs | - | FIRED | FIRED | FIRED | - | - | - |
| SP agent, one asset, 12-month window, readings | FIRED | - | FIRED | - | - | - | - |
| SP agent, one asset, 12-month window, Phase 3 inputs | FIRED | FIRED | FIRED | - | - | - | - |

- **train_test_sharpe_gap: FIRED.** mean over folds and seeds: train-slice Sharpe 1.90, validation 0.95, test 0.25; gap 1.65 (threshold 1.0); neutral fallback in 39% of fold models
- **seed_dispersion: not fired.** stitched Sharpe by seed 0.52, 0.40, 0.51 (sd 0.06, threshold 0.50)
- **beats_benchmarks_in_under_half_the_folds: FIRED.** folds with a higher seed-mean Sharpe: buy_hold 10/25, momentum 9/25
- **fee_sign_flip: not fired.** no seed changes sign
- **edge_only_at_0.05: not fired.** seed mean: net +78.8% / Sharpe 0.48 at 0.10% (buy-and-hold 0.64); net +105.9% / Sharpe 0.56 at 0.05% (buy-and-hold 0.64)
- **high_turnover: not fired.** turnover per year by seed 54, 39, 49 (threshold 100)
- **degenerate_policy: not fired.** long / flat / short share of bars by seed: 0 43/48/9%; 1 46/47/7%; 2 37/54/8%

**ETHUSDT**

| Variant | train_test_sharpe_gap | seed_dispersion | beats_benchmarks_in_under_half_the_folds | fee_sign_flip | edge_only_at_0.05 | high_turnover | degenerate_policy |
|---|---|---|---|---|---|---|---|
| Q agent, BTC+ETH pooled, expanding, readings | FIRED | - | FIRED | - | - | - | - |
| SP agent, BTC+ETH pooled, expanding, readings | - | FIRED | FIRED | - | - | - | - |
| SP agent, 8 markets pooled, expanding, readings | - | - | FIRED | - | - | FIRED | - |
| SP agent, BTC+ETH pooled, expanding, Phase 3 inputs | - | - | FIRED | - | - | - | - |
| SP agent, one asset, expanding, readings | - | - | FIRED | - | - | FIRED | - |
| SP agent, one asset, expanding, Phase 3 inputs | - | - | FIRED | - | - | - | - |
| SP agent, one asset, 12-month window, readings | FIRED | - | FIRED | - | - | - | - |
| SP agent, one asset, 12-month window, Phase 3 inputs | FIRED | - | FIRED | FIRED | - | - | - |

- **train_test_sharpe_gap: FIRED.** mean over folds and seeds: train-slice Sharpe 1.57, validation 0.76, test 0.43; gap 1.13 (threshold 1.0); neutral fallback in 41% of fold models
- **seed_dispersion: not fired.** stitched Sharpe by seed 0.94, 0.75, 0.61 (sd 0.16, threshold 0.50)
- **beats_benchmarks_in_under_half_the_folds: FIRED.** folds with a higher seed-mean Sharpe: buy_hold 11/25, momentum 14/25
- **fee_sign_flip: not fired.** no seed changes sign
- **edge_only_at_0.05: not fired.** seed mean: net +263.1% / Sharpe 0.77 at 0.10% (buy-and-hold 0.60); net +341.1% / Sharpe 0.86 at 0.05% (buy-and-hold 0.60)
- **high_turnover: not fired.** turnover per year by seed 65, 64, 60 (threshold 100)
- **degenerate_policy: not fired.** long / flat / short share of bars by seed: 0 44/45/10%; 1 43/46/11%; 2 36/55/9%


## Learnability check at the new data sizes (synthetic, before the freeze)

Same test span of synthetic series 1 traded by models trained on three data sizes (Phase 4 code, selection, refit and 'do no harm' included). Fresh synthetic series; criteria = Phase 3's frozen ones.

| Family / size | Scenario | kappa | Test Sharpe mean | by seed | Oracle | Train | Val | Turnover/yr | Exposure | Corr. with planted | Neutral | Found the edge |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sp/p3_9m | edge | 0.020 | 0.40 | 0.58, 0.00, -0.01, -0.49, 1.91 | 2.36 | 2.54 | 1.86 | 115 | 64% | 0.21 | 20% | 2 of 5 |
| sp/p3_9m | edge_small | 0.010 | 0.53 | 0.74, 0.00, 0.00, -0.10, 1.99 | 0.96 | 1.77 | 1.60 | 45 | 40% | 0.07 | 40% | 1 of 5 |
| sp/p3_9m | none | 0.000 | 0.29 | 0.14, 0.00, 0.33, -0.34, 1.30 | -0.10 | 1.77 | 2.15 | 47 | 53% | 0.06 | 20% | 1 of 5 |
| sp/single_3y | edge | 0.020 | 0.31 | -0.87, -0.38, 0.00, 1.70, 1.09 | 2.02 | 1.37 | 1.95 | 108 | 65% | 0.30 | 20% | 2 of 5 |
| sp/single_3y | edge_small | 0.010 | -0.58 | -1.71, -1.17, 0.00, 0.00, 0.00 | 0.88 | 0.48 | 0.49 | 28 | 32% | 0.04 | 60% | 0 of 5 |
| sp/single_3y | none | 0.000 | -0.09 | 0.00, -0.47, 0.00, 0.00, 0.00 | 0.17 | 0.28 | 0.21 | 9 | 16% | -0.05 | 80% | 0 of 5 |
| sp/pool2_6y | edge | 0.020 | 1.72 | 1.42, 0.84, 1.63, 2.77, 1.92 | 1.90 | 1.81 | 1.89 | 226 | 87% | 0.62 | 0% | 5 of 5 |
| sp/pool2_6y | edge_small | 0.010 | -0.01 | 0.00, -0.58, 0.10, 0.00, 0.41 | 0.75 | 0.78 | 0.68 | 103 | 50% | 0.26 | 40% | 2 of 5 |
| sp/pool2_6y | none | 0.000 | -0.25 | 0.00, -1.26, 0.00, 0.00, 0.00 | -0.21 | 0.46 | 0.23 | 18 | 16% | -0.05 | 80% | 0 of 5 |
| q/p3_9m | edge | 0.020 | -0.23 | 0.00, -1.15, 0.00, 0.00, 0.00 | 2.36 | 4.87 | -0.05 | 26 | 18% | 0.04 | 80% | 0 of 5 |
| q/p3_9m | edge_small | 0.010 | -0.27 | 0.00, -1.35, 0.00, 0.00, 0.00 | 0.96 | 4.37 | -0.19 | 24 | 19% | 0.00 | 80% | 0 of 5 |
| q/p3_9m | none | 0.000 | -0.46 | 0.00, -1.17, 0.00, -1.12, 0.00 | -0.10 | 4.17 | -0.23 | 50 | 37% | -0.05 | 60% | 0 of 5 |
| q/single_3y | edge | 0.020 | 0.97 | -0.55, -0.02, 0.92, 0.81, 3.68 | 2.02 | 2.65 | 2.22 | 129 | 90% | 0.49 | 0% | 3 of 5 |
| q/single_3y | edge_small | 0.010 | -0.81 | -1.71, -1.02, -1.02, -0.30, 0.00 | 0.88 | 1.83 | 1.29 | 42 | 70% | 0.17 | 20% | 0 of 5 |
| q/single_3y | none | 0.000 | -0.08 | 1.00, -1.16, -1.13, 0.00, 0.87 | 0.17 | 1.48 | 0.82 | 38 | 71% | -0.02 | 20% | 1 of 5 |
| q/pool2_6y | edge | 0.020 | 2.13 | 0.50, 2.68, 1.18, 3.32, 2.98 | 1.90 | 2.09 | 3.59 | 113 | 87% | 0.59 | 0% | 5 of 5 |
| q/pool2_6y | edge_small | 0.010 | 0.44 | -0.31, -0.93, 0.07, 2.33, 1.03 | 0.75 | 1.01 | 2.66 | 48 | 77% | 0.30 | 0% | 3 of 5 |
| q/pool2_6y | none | 0.000 | 0.19 | 0.00, -1.10, 0.38, 1.67, 0.00 | -0.21 | 0.67 | 0.74 | 7 | 29% | -0.04 | 40% | 0 of 5 |

| Family / size | finds planted edge | fits training slice | near flat without edge | PASS |
|---|---|---|---|---|
| sp/p3_9m | False | True | True | **FAIL** |
| sp/single_3y | False | True | True | **FAIL** |
| sp/pool2_6y | True | True | True | **PASS** |
| q/p3_9m | False | True | True | **FAIL** |
| q/single_3y | True | True | False | **FAIL** |
| q/pool2_6y | True | True | True | **PASS** |

**Power check** (10 seeds, 24-month test):

| Family / size | Scenario | Test Sharpe mean | sd over seeds | by seed | Oracle | Corr. with planted | Neutral | Found the edge |
|---|---|---|---|---|---|---|---|---|
| sp/p3_9m | edge | -0.01 | 0.67 | 0.30, 0.00, -0.91, 0.00, -0.40, -0.60, 0.00, 1.62, 0.00, -0.12 | 2.29 | 0.08 | 40% | 1 of 10 |
| sp/p3_9m | none | -0.18 | 0.69 | 0.65, 0.00, -0.84, 0.00, -0.29, -1.68, 0.00, -0.29, 0.00, 0.67 | -0.22 | -0.04 | 40% | 0 of 10 |
| sp/pool2_6y | edge | 1.10 | 0.90 | 0.00, 1.35, 2.06, 0.90, 2.21, 1.10, -0.19, 1.93, 0.00, 1.66 | 2.33 | 0.48 | 20% | 7 of 10 |
| sp/pool2_6y | none | -0.30 | 0.50 | 0.00, 0.22, 0.00, 0.00, 0.00, -0.42, -1.40, -0.66, 0.00, -0.74 | -0.20 | -0.02 | 50% | 0 of 10 |
| q/p3_9m | edge | 0.59 | 1.08 | 1.72, 1.50, -0.47, 0.51, -0.32, 0.00, 0.00, 2.85, 0.00, 0.11 | 2.29 | 0.23 | 30% | 5 of 10 |
| q/p3_9m | none | 0.01 | 0.60 | 0.00, 0.16, -1.28, 0.00, 0.00, 0.00, 0.00, 1.23, 0.00, 0.00 | -0.22 | 0.03 | 70% | 1 of 10 |
| q/pool2_6y | edge | 1.66 | 1.23 | 0.00, 0.00, 3.01, 1.30, 2.67, 2.34, 2.72, 2.37, 0.00, 2.17 | 2.33 | 0.40 | 30% | 7 of 10 |
| q/pool2_6y | none | -0.29 | 0.55 | 0.00, 0.00, 0.00, -1.69, 0.00, -0.07, 0.00, -0.75, 0.00, -0.42 | -0.20 | 0.01 | 60% | 0 of 10 |

## No-look-ahead check of every input (real data)

| Asset | Cuts | build_one readings, data cut | basis / Coinbase, source files cut | store == code | Clean |
|---|---|---|---|---|---|
| BTCUSDT | 2022-12-11 19:45, 2025-12-30 21:00, 2026-10-01 07:15 | all equal | all equal | all equal | yes |
| ETHUSDT | 2020-09-07 05:45, 2022-05-12 07:00, 2026-10-21 17:45 | all equal | all equal | all equal | yes |
| XAUUSD | 2023-09-07 14:15 | all equal | n/a | all equal | yes |
| XAGUSD | 2026-01-27 01:45 | all equal | n/a | all equal | yes |
| USDJPY | 2020-09-28 07:30 | all equal | n/a | all equal | yes |
| SPX | 2020-10-28 19:00 | all equal | n/a | all equal | yes |
| WTI | 2020-08-17 04:45 | all equal | n/a | all equal | yes |
| BRENT | 2022-04-04 16:45 | all equal | n/a | all equal | yes |

Assembled inputs on BTCUSDT's bars (Phase 3 features + readings + flags), cut at 2021-02-14 12:00, 2025-10-09 16:45, 2026-05-25 04:45: offending columns none.

Assembled inputs on ETHUSDT's bars (Phase 3 features + readings + flags), cut at 2020-07-26 04:00, 2025-09-01 07:00, 2026-05-08 18:15: offending columns none.

## What was frozen, and when

- 11 Nov 2026, ~19:45 UTC: this file drafted with every value (assets, pools, inputs, both families, all eight variants, the validation choices, the 'do no harm' bar, the verdict rules, the learnability sizes and criteria, the primary rule) before any Phase 4 code ran on any data
- 11 Nov 2026, ~19:50 UTC: look-ahead check on real data (inputs only, no model): the truncation tests were clean from the start; a first 'store == code' comparison for metals / energy recomputed the readings on each market's own bars instead of its group's common bars (as the store does) and was fixed in the checking code; rerun CLEAN for all 8 markets
- 11 Nov 2026, ~19:52 UTC: learnability run 1 (seed base 5000, draft SP design: penalty chosen by validation IC, with an intercept) STOPPED after 7 rows: IC is blind to prediction scale and picked the heaviest penalty (alpha 10), whose predictions never cleared the cost band (pool2_6y SP did not trade even in its training slice). Rows kept in phase4_learnability_run1_draft.partial.jsonl. Q results so far: neutral fallback in every fold (unchanged agent)
- 11 Nov 2026, ~20:00-20:10 UTC (synthetic seeds 9000+ only, never real data): SP exploration (phase4_exploration_sp*.json): selection by validation R2 vs IC, 'do no harm' bar 0.5 / 0 / none, intercept on / off, at p3_9m and pool2_6y, 3-5 seeds. Chosen: select_on val_r2 (scale-aware, fixes run 1's failure; IC vs R2 test Sharpe differences within noise), intercept off (a timing agent should not carry a constant drift bet; little difference on synthetic data), 'do no harm' bar kept at Phase 3's 0.5. Seen there and left as is: without an edge the pooled model still bets on spurious slow trends in some seeds (exposure ~50%, test Sharpe ~-1), a limit of what 6 years of 15m data can tell apart. No Q setting changed. The frozen learnability check then runs on fresh series (seed base 7000)
- 11 Nov 2026, ~20:05-20:30 UTC: learnability check (main, 5 seeds, seed base 7000): at Phase 3's size (p3_9m) both families FAIL (planted edge found in 2 of 5 seeds by SP, 0 of 5 by Q); at single_3y both FAIL; at pool2_6y both PASS (edge found in 5 of 5 seeds; test Sharpe SP 1.72, Q 2.13 vs oracle 1.90; near flat without an edge). Primary by the rule: q_pool2_full. The power check (10 seeds, 24-month test) was still running and is reported as found; it decides nothing
- 11 Nov 2026, 20:30 UTC: everything frozen (status: frozen, primary q_pool2_full); then the walk-forward runs once
- No test-window number fed back into any setting; nothing was rerun after the test results were seen.

## Design (fixed before testing)

- **Clock.** 15m bars, a decision at every 15m close, fill at the next open, minimum hold 4 bars; actions [-1.0, -0.5, 0.0, 0.5, 1.0].
- **More data per model.** Each fold model trains on every bar from 2019 (each market's first bar + 35 days of warm-up; BTC perp from Sept 2019) up to the fold, i.e. 1 year for the first fold growing to about 7 for the last, pooled across BTC and ETH (and, in one variant, all 8 engine markets with their own costs); recency half-life chosen per fold on the validation slice (last 6 months) from [None, 730, 365] days (None = no recency); then refit on everything up to the fold. Ablations keep Phase 3's 12-month single-asset window.
- **Inputs.** Phase 3's features (z-scored per asset on the fold's training rows, clipped at +-5) plus 18 Mind 15 readings from the evidence store and 7 availability flags (an unavailable reading is NaN -> 0 after z-scoring, with its group's flag at 0).
- **SP (supervised-then-policy).** Weighted ridge on the next 96 bars' vol-scaled net return, penalty from [0.01, 0.1, 1.0, 10.0] chosen with the half-life by the validation information coefficient; block-bootstrap seeds (1-week blocks); Phase 3's cost-aware policy on the prediction (round-trip cost band, risk charge 1.0).
- **Q.** The Phase 3 afterstate Q-learner unchanged (linear, 16-step double Q, weight decay 0.3, round-trip cost hard-wired), up to 8 x 1000 steps with early stopping on the validation Bellman loss (patience 2), half-life chosen by that loss; refit for the kept steps.
- **Do no harm.** A fold whose validation-stage model nets a Sharpe under 0.5 on an asset's validation slice acts flat on that asset for the fold.
- **Risk manager and costs.** Agents through the Phase 3 risk manager (vol-targeted size, soft drawdown brake) into the shared backtester; 0.10% a side headline, 0.05% comparison; funding on perp positions.

## Per fold, primary agent, BTC, 0.10%

| # | Test window | Agent net, mean (min..max) | Agent Sharpe | Neutral seeds | B&H net | B&H Sharpe | Mom net | Mom Sharpe |
|---|---|---|---|---|---|---|---|---|
| 0 | 2020-10-01 .. 2021-01-01 | +46.7% (+0% .. +83%) | 3.45 | 1 of 3 | +155.6% | 6.04 | +168.0% | 6.33 |
| 1 | 2021-01-01 .. 2021-04-01 | +10.6% (+7% .. +13%) | 1.08 | 0 of 3 | +72.4% | 2.49 | +34.9% | 1.63 |
| 2 | 2021-04-01 .. 2021-07-01 | -8.8% (-14% .. -0%) | -1.44 | 1 of 3 | -44.4% | -1.68 | -21.2% | -0.36 |
| 3 | 2021-07-01 .. 2021-10-01 | +12.4% (-0% .. +19%) | 0.31 | 1 of 3 | +22.4% | 1.54 | +13.6% | 1.09 |
| 4 | 2021-10-01 .. 2022-01-01 | +2.8% (+0% .. +8%) | 0.30 | 2 of 3 | +0.3% | 0.35 | +1.7% | 0.43 |
| 5 | 2022-01-01 .. 2022-04-01 | -10.3% (-15% .. -4%) | -0.83 | 0 of 3 | -2.8% | 0.16 | -31.9% | -2.03 |
| 6 | 2022-04-01 .. 2022-07-01 | +0.1% (+0% .. +0%) | 0.82 | 3 of 3 | -56.6% | -4.00 | +40.9% | 2.18 |
| 7 | 2022-07-01 .. 2022-10-01 | +0.0% (+0% .. +0%) | 0.00 | 3 of 3 | -3.7% | 0.07 | +2.4% | 0.46 |
| 8 | 2022-10-01 .. 2023-01-01 | +3.3% (+0% .. +10%) | 0.62 | 2 of 3 | -15.5% | -1.16 | -27.6% | -2.45 |
| 9 | 2023-01-01 .. 2023-04-01 | -0.0% (-0% .. +0%) | -0.95 | 3 of 3 | +68.6% | 4.31 | +52.3% | 3.52 |
| 10 | 2023-04-01 .. 2023-07-01 | +0.5% (-2% .. +3%) | 0.19 | 0 of 3 | +5.4% | 0.72 | -3.5% | -0.14 |
| 11 | 2023-07-01 .. 2023-10-01 | -4.9% (-20% .. +4%) | -0.48 | 0 of 3 | -12.6% | -1.24 | +9.5% | 1.15 |
| 12 | 2023-10-01 .. 2024-01-01 | -0.0% (-0% .. -0%) | -0.95 | 3 of 3 | +52.2% | 3.97 | +51.8% | 3.95 |
| 13 | 2024-01-01 .. 2024-04-01 | +27.8% (+25% .. +33%) | 2.57 | 0 of 3 | +59.5% | 3.52 | +1.6% | 0.40 |
| 14 | 2024-04-01 .. 2024-07-01 | -9.6% (-15% .. -4%) | -0.99 | 0 of 3 | -14.0% | -1.01 | +3.3% | 0.51 |
| 15 | 2024-07-01 .. 2024-10-01 | +3.9% (-0% .. +9%) | -0.34 | 1 of 3 | -0.0% | 0.27 | -51.4% | -4.94 |
| 16 | 2024-10-01 .. 2025-01-01 | +12.3% (-0% .. +37%) | 0.32 | 2 of 3 | +43.1% | 3.06 | +40.1% | 2.89 |
| 17 | 2025-01-01 .. 2025-04-01 | +1.2% (-8% .. +11%) | 0.33 | 0 of 3 | -12.9% | -0.74 | -22.9% | -1.63 |
| 18 | 2025-04-01 .. 2025-07-01 | +18.1% (+4% .. +37%) | 2.92 | 0 of 3 | +28.6% | 2.64 | -1.2% | 0.09 |
| 19 | 2025-07-01 .. 2025-10-01 | +1.9% (-0% .. +5%) | 0.49 | 0 of 3 | +4.6% | 0.74 | +2.6% | 0.48 |
| 20 | 2025-10-01 .. 2026-01-01 | -0.5% (-10% .. +8%) | 0.09 | 0 of 3 | -24.0% | -2.07 | +15.1% | 1.42 |
| 21 | 2026-01-01 .. 2026-04-01 | -23.4% (-24% .. -22%) | -3.20 | 0 of 3 | -22.3% | -1.60 | -22.7% | -1.63 |
| 22 | 2026-04-01 .. 2026-07-01 | +0.1% (+0% .. +0%) | 1.12 | 3 of 3 | -14.3% | -1.29 | +19.1% | 1.89 |
| 23 | 2026-07-01 .. 2026-10-01 | +0.0% (+0% .. +0%) | 0.00 | 3 of 3 | +40.3% | 4.05 | -12.0% | -1.29 |
| 24 | 2026-10-01 .. 2026-11-11 | +0.9% (+0% .. +2%) | 0.81 | 1 of 3 | -12.1% | -3.12 | +13.4% | 3.39 |

## Training

- Q agent, BTC+ETH pooled, expanding, readings: train-slice Sharpe 1.90, validation 0.95, test 0.25 (BTC, fold means); neutral in 39% of fold models; half-life chosen 365 d x34, 730 d x24, none x17.
- SP agent, BTC+ETH pooled, expanding, readings: train-slice Sharpe 1.22, validation 0.90, test 0.19 (BTC, fold means); neutral in 48% of fold models; half-life chosen 365 d x24, 730 d x7, none x44; ridge penalty chosen 0.01 x7, 0.1 x14, 1 x23, 10 x31.
- SP agent, 8 markets pooled, expanding, readings: train-slice Sharpe 1.08, validation 0.89, test 0.21 (BTC, fold means); neutral in 48% of fold models; half-life chosen 365 d x32, 730 d x10, none x33; ridge penalty chosen 0.01 x12, 0.1 x22, 1 x27, 10 x14.
- SP agent, BTC+ETH pooled, expanding, Phase 3 inputs: train-slice Sharpe 0.85, validation 0.65, test -0.25 (BTC, fold means); neutral in 45% of fold models; half-life chosen 365 d x18, 730 d x5, none x52; ridge penalty chosen 0.01 x18, 0.1 x15, 1 x19, 10 x23.
- SP agent, one asset, expanding, readings: train-slice Sharpe 1.35, validation 0.88, test 0.32 (BTC, fold means); neutral in 44% of fold models; half-life chosen 365 d x16, 730 d x12, none x47; ridge penalty chosen 0.01 x2, 0.1 x8, 1 x32, 10 x33.
- SP agent, one asset, expanding, Phase 3 inputs: train-slice Sharpe 0.82, validation 0.70, test 0.10 (BTC, fold means); neutral in 48% of fold models; half-life chosen 365 d x16, 730 d x10, none x49; ridge penalty chosen 0.01 x15, 0.1 x13, 1 x18, 10 x29.
- SP agent, one asset, 12-month window, readings: train-slice Sharpe 1.20, validation 0.24, test -0.55 (BTC, fold means); neutral in 59% of fold models; half-life chosen 365 d x29, 730 d x3, none x43; ridge penalty chosen 0.01 x1, 0.1 x1, 1 x9, 10 x64.
- SP agent, one asset, 12-month window, Phase 3 inputs: train-slice Sharpe 0.54, validation 0.18, test -0.49 (BTC, fold means); neutral in 67% of fold models; half-life chosen 365 d x27, 730 d x2, none x46; ridge penalty chosen 0.01 x1, 0.1 x6, 1 x4, 10 x64.

- Memory: heavy steps started only with >= 1000 MB free and paused under 400 MB. Pauses: none.
- Models: C:\Ai Dataset\engine-15m\research/out/rl/models4\397144c2 (one W file per fold, seed and asset; a JSON record per fold).
- Phase 3 benchmark rows: from run `phase3_20261111T144229Z_6e297970` (same data, folds, backtester and risk manager).

Machine-readable: `phase4_summary.json`. Nothing here is wired into the live engine or the page.
