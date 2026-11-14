# RL Phase 3 report: a continuously learning 15m agent that learns when not to trade

Run `phase3_20261111T144229Z_6e297970`, generated 2026-11-11 16:57 UTC. 15-minute bars and a 15-minute decision clock throughout. Paper only: no orders, no keys. Seeds [0, 1, 2], run time 135.5 min. BTCUSDT perpetual is the headline; ETHUSDT (the engine's 15m file) is the robustness check. Out of sample = 25 stitched 3-month test windows, 2020-10-01 to 2026-11-11; every prediction comes from a model trained only on data before it.

## Verdict

NO. Out of sample (Oct 2020 - Nov 2026), after 0.10% fees, the continuously learning 15m agent (c) does not beat buy-and-hold and momentum on a risk-adjusted basis across seeds: seed-mean Sharpe -0.37 (seeds above buy-and-hold's 0.64: 0 of 3; above momentum's 0.63: 0 of 3), Calmar -0.15 vs 0.29 and 0.34, net return -53% vs buy-and-hold +249%. Its break-even fee is -0.174% (loses before fees) a side. None of the 9 agent variants or filters beats both on every seed.

Break-even fees (0.10% decisions held fixed; seed mean): (a) static, fresh model per fold -0.220% (loses before fees); (b) continual fine-tuning, never reset -0.030% (loses before fees); (c) continual + full retrain each fold -0.174% (loses before fees); v3 higher-timeframe alignment 0.323%; v2 confidence gate -0.037% (loses before fees); v4 volatility / cost gate -0.130% (loses before fees); v5 meta-labeling on momentum 0.220%; v6 core-satellite (0..1.5x) 0.229%; v1 seed consensus (all 3 seeds agree) -0.022% (loses before fees).

Against their own baselines (dev span only, to 2025-11-11, the loop's spot backtester, 0.10%): residual RL on A (+-0.5x): Sharpe 1.09 vs 1.19, net +1458% vs +1809%, Sharpe higher in 5 of 21 folds (return in 4); residual RL on B (+-0.5x): Sharpe 1.06 vs 1.32, net +806% vs +1301%, Sharpe higher in 4 of 21 folds (return in 3); imitation warm start on A, then RL: Sharpe 0.18 vs 1.19, net -42% vs +1809%, Sharpe higher in 10 of 21 folds (return in 8); imitation warm start on B, then RL: Sharpe 0.12 vs 1.32, net -44% vs +1301%, Sharpe higher in 8 of 21 folds (return in 8); same agent from scratch (A's inputs): Sharpe 0.00 vs 1.19, net -68% vs +1809%, Sharpe higher in 7 of 21 folds (return in 6); same agent from scratch (B's inputs): Sharpe -0.02 vs 1.32, net -70% vs +1301%, Sharpe higher in 7 of 21 folds (return in 7).

## BTC headline: stitched out of sample, 0.10% a side (the owner's rule)

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|
| (a) static, fresh model per fold, mean of 3 seeds | -51.8% | -0.42 | -0.58 | 75% | -0.16 | 40 | 101 | 108 | 5.6% | -0.220% (loses before fees) |
| &nbsp;&nbsp;seed 0 | -24.7% | -0.07 | -0.10 | 62% | -0.07 | 37 | 94 | 109 | 5.1% | -0.025% (loses before fees) |
| &nbsp;&nbsp;seed 1 | -64.7% | -0.60 | -0.83 | 82% | -0.19 | 37 | 95 | 120 | 5.0% | -0.356% (loses before fees) |
| &nbsp;&nbsp;seed 2 | -66.1% | -0.58 | -0.81 | 80% | -0.20 | 47 | 113 | 96 | 6.7% | -0.280% (loses before fees) |
| (b) continual fine-tuning, never reset, mean of 3 seeds | -45.9% | -0.14 | -0.19 | 76% | -0.13 | 80 | 180 | 130 | 13.6% | -0.030% (loses before fees) |
| &nbsp;&nbsp;seed 0 | -30.8% | -0.01 | -0.01 | 69% | -0.09 | 79 | 171 | 128 | 13.4% | 0.024% |
| &nbsp;&nbsp;seed 1 | -59.3% | -0.25 | -0.35 | 82% | -0.17 | 84 | 193 | 129 | 14.4% | -0.074% (loses before fees) |
| &nbsp;&nbsp;seed 2 | -47.7% | -0.15 | -0.21 | 78% | -0.13 | 76 | 174 | 134 | 13.0% | -0.040% (loses before fees) |
| **(c) continual + full retrain each fold [primary], mean of 3 seeds** | **-53.4%** | **-0.37** | **-0.51** | **79%** | **-0.15** | **46** | **103** | **84** | **8.1%** | **-0.174% (loses before fees)** |
| &nbsp;&nbsp;seed 0 | -51.6% | -0.34 | -0.47 | 80% | -0.14 | 46 | 107 | 82 | 8.3% | -0.155% (loses before fees) |
| &nbsp;&nbsp;seed 1 | -48.5% | -0.31 | -0.43 | 77% | -0.13 | 45 | 96 | 81 | 7.8% | -0.141% (loses before fees) |
| &nbsp;&nbsp;seed 2 | -60.2% | -0.45 | -0.63 | 79% | -0.18 | 46 | 107 | 88 | 8.1% | -0.227% (loses before fees) |
| v1 seed consensus (all 3 seeds agree) | -21.3% | -0.05 | -0.07 | 66% | -0.06 | 32 | 68 | 90 | 6.2% | -0.022% (loses before fees) |
| v2 confidence gate, mean of 3 seeds | -12.5% | 0.01 | 0.01 | 70% | -0.03 | 19 | 45 | 157 | 3.9% | -0.037% (loses before fees) |
| &nbsp;&nbsp;seed 0 | +12.0% | 0.20 | 0.28 | 72% | 0.03 | 18 | 45 | 180 | 4.0% | 0.201% |
| &nbsp;&nbsp;seed 1 | -10.7% | 0.03 | 0.04 | 62% | -0.03 | 18 | 41 | 131 | 3.9% | -0.000% (loses before fees) |
| &nbsp;&nbsp;seed 2 | -38.8% | -0.21 | -0.30 | 78% | -0.10 | 20 | 50 | 160 | 3.8% | -0.310% (loses before fees) |
| v3 higher-timeframe alignment, mean of 3 seeds | +48.2% | 0.50 | 0.71 | 37% | 0.19 | 29 | 64 | 40 | 5.8% | 0.323% |
| &nbsp;&nbsp;seed 0 | +60.4% | 0.59 | 0.83 | 31% | 0.26 | 29 | 64 | 43 | 5.8% | 0.365% |
| &nbsp;&nbsp;seed 1 | +45.0% | 0.49 | 0.69 | 40% | 0.16 | 27 | 60 | 39 | 5.5% | 0.326% |
| &nbsp;&nbsp;seed 2 | +39.2% | 0.43 | 0.60 | 39% | 0.14 | 30 | 69 | 39 | 6.1% | 0.277% |
| v4 volatility / cost gate, mean of 3 seeds | -31.2% | -0.15 | -0.20 | 70% | -0.08 | 27 | 70 | 107 | 5.7% | -0.130% (loses before fees) |
| &nbsp;&nbsp;seed 0 | -25.8% | -0.11 | -0.15 | 69% | -0.07 | 26 | 65 | 96 | 5.3% | -0.091% (loses before fees) |
| &nbsp;&nbsp;seed 1 | -33.9% | -0.15 | -0.22 | 70% | -0.09 | 29 | 77 | 112 | 6.1% | -0.130% (loses before fees) |
| &nbsp;&nbsp;seed 2 | -33.8% | -0.17 | -0.24 | 71% | -0.09 | 25 | 69 | 113 | 5.8% | -0.170% (loses before fees) |
| v5 meta-labeling on momentum, mean of 3 seeds | +38.4% | 0.35 | 0.48 | 55% | 0.10 | 44 | 97 | 68 | 8.6% | 0.220% |
| &nbsp;&nbsp;seed 0 | +28.8% | 0.30 | 0.41 | 60% | 0.07 | 45 | 96 | 69 | 8.9% | 0.192% |
| &nbsp;&nbsp;seed 1 | +26.5% | 0.28 | 0.40 | 57% | 0.07 | 43 | 96 | 69 | 8.6% | 0.189% |
| &nbsp;&nbsp;seed 2 | +60.0% | 0.45 | 0.63 | 48% | 0.17 | 43 | 98 | 66 | 8.4% | 0.279% |
| v6 core-satellite (0..1.5x), mean of 3 seeds | +106.0% | 0.48 | 0.68 | 67% | 0.18 | 90 | 225 | 327 | 21.0% | 0.229% |
| &nbsp;&nbsp;seed 0 | +72.8% | 0.43 | 0.60 | 68% | 0.14 | 93 | 229 | 309 | 21.5% | 0.196% |
| &nbsp;&nbsp;seed 1 | +148.2% | 0.55 | 0.77 | 68% | 0.23 | 91 | 221 | 309 | 21.0% | 0.263% |
| &nbsp;&nbsp;seed 2 | +97.1% | 0.47 | 0.67 | 66% | 0.18 | 86 | 225 | 362 | 20.5% | 0.228% |
| Buy-and-hold (perp) | +249.3% | 0.64 | 0.91 | 79% | 0.29 | 0 | 0 | 53579 | 11.0% | > 5% |
| Momentum (daily 30-day, long/short) | +237.7% | 0.63 | 0.89 | 64% | 0.34 | 62 | 31 | 281 | 14.3% | 0.418% |
| Random agent (mean of 10) | -95.3% | -0.93 | -1.30 | 97% | -0.44 | 323 | 243 | 36 | 42.6% | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +248.5% | 0.68 | 0.96 | 68% | 0.33 | 22 | 88 | 53579 | 11.9% | 1.036% |
| *reference: momentum through the Phase 3 risk manager* | +212.0% | 0.64 | 0.90 | 57% | 0.36 | 72 | 123 | 281 | 14.2% | 0.356% |
| *Phase 2 PPO, mean of 5 seeds (Phase 2 risk limits; from phase2_summary.json)* | -99.6% | -1.92 | -2.70 | 100% | -0.60 | 601 | ~500 | 17 | 79.3% | < 0 (gross Sharpe ~0) |

## BTC headline: stitched out of sample, 0.05% a side (Binance USDT-M taker)

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|
| (a) static, fresh model per fold, mean of 3 seeds | -45.4% | -0.33 | -0.46 | 72% | -0.14 | 41 | 100 | 108 | 3.6% | -0.219% (loses before fees) |
| &nbsp;&nbsp;seed 0 | -14.4% | 0.02 | 0.02 | 57% | -0.04 | 38 | 95 | 109 | 3.4% | -0.016% (loses before fees) |
| &nbsp;&nbsp;seed 1 | -60.4% | -0.52 | -0.72 | 80% | -0.18 | 38 | 98 | 120 | 3.2% | -0.346% (loses before fees) |
| &nbsp;&nbsp;seed 2 | -61.5% | -0.50 | -0.69 | 78% | -0.19 | 45 | 107 | 96 | 4.2% | -0.295% (loses before fees) |
| (b) continual fine-tuning, never reset, mean of 3 seeds | -30.1% | -0.01 | -0.02 | 71% | -0.08 | 81 | 180 | 130 | 9.7% | -0.027% (loses before fees) |
| &nbsp;&nbsp;seed 0 | -13.2% | 0.10 | 0.15 | 63% | -0.04 | 81 | 177 | 128 | 9.6% | 0.021% |
| &nbsp;&nbsp;seed 1 | -50.4% | -0.16 | -0.22 | 80% | -0.14 | 86 | 198 | 129 | 10.3% | -0.084% (loses before fees) |
| &nbsp;&nbsp;seed 2 | -26.7% | 0.02 | 0.02 | 70% | -0.07 | 75 | 167 | 134 | 9.2% | -0.018% (loses before fees) |
| **(c) continual + full retrain each fold [primary], mean of 3 seeds** | **-46.5%** | **-0.27** | **-0.38** | **77%** | **-0.13** | **46** | **104** | **84** | **5.8%** | **-0.172% (loses before fees)** |
| &nbsp;&nbsp;seed 0 | -44.7% | -0.25 | -0.35 | 78% | -0.12 | 47 | 106 | 82 | 6.0% | -0.158% (loses before fees) |
| &nbsp;&nbsp;seed 1 | -41.3% | -0.22 | -0.31 | 75% | -0.11 | 46 | 99 | 81 | 5.6% | -0.140% (loses before fees) |
| &nbsp;&nbsp;seed 2 | -53.4% | -0.35 | -0.49 | 78% | -0.15 | 46 | 107 | 88 | 5.8% | -0.219% (loses before fees) |
| v1 seed consensus (all 3 seeds agree) | -14.9% | 0.00 | 0.00 | 65% | -0.04 | 33 | 70 | 90 | 4.7% | -0.031% (loses before fees) |
| v2 confidence gate, mean of 3 seeds | -8.2% | 0.04 | 0.05 | 70% | -0.02 | 19 | 47 | 157 | 3.0% | -0.039% (loses before fees) |
| v3 higher-timeframe alignment, mean of 3 seeds | +60.9% | 0.59 | 0.83 | 34% | 0.25 | 29 | 64 | 40 | 4.4% | 0.318% |
| v4 volatility / cost gate, mean of 3 seeds | -25.8% | -0.09 | -0.13 | 69% | -0.07 | 27 | 70 | 107 | 4.4% | -0.131% (loses before fees) |
| v5 meta-labeling on momentum, mean of 3 seeds | +57.5% | 0.44 | 0.61 | 53% | 0.15 | 44 | 98 | 68 | 6.5% | 0.217% |
| v6 core-satellite (0..1.5x), mean of 3 seeds | +190.7% | 0.59 | 0.84 | 65% | 0.29 | 88 | 217 | 327 | 16.2% | 0.247% |
| Buy-and-hold (perp) | +249.5% | 0.64 | 0.91 | 79% | 0.29 | 0 | 0 | 53579 | 11.0% | > 5% |
| Momentum (daily 30-day, long/short) | +308.7% | 0.68 | 0.97 | 61% | 0.42 | 62 | 31 | 281 | 11.2% | 0.418% |
| Random agent (mean of 10) | -87.3% | -0.59 | -0.84 | 93% | -0.35 | 323 | 243 | 36 | 26.5% | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +261.7% | 0.70 | 0.98 | 69% | 0.34 | 23 | 95 | 53579 | 11.0% | 0.951% |
| *reference: momentum through the Phase 3 risk manager* | +295.7% | 0.72 | 1.02 | 50% | 0.51 | 74 | 128 | 281 | 10.7% | 0.354% |
| *Phase 2 PPO, mean of 5 seeds (Phase 2 risk limits; from phase2_summary.json)* | -97.5% | -1.20 | -1.69 | 98% | -0.47 | 608 | ~500 | 17 | 49.8% | < 0 (gross Sharpe ~0) |

Every agent row runs through the Phase 3 risk manager (vol-targeted sizing + soft drawdown brake); benchmarks run without it, and the two reference rows show what the risk manager alone does to buy-and-hold and momentum. Break-even fee = the fee a side at which the stitched net return would be zero with the same positions.

## Reading the numbers (BTC, 0.10%)

- **No edge before costs.** The primary agent's gross (pre-cost) Sharpe is -0.05; it loses before any fee (break-even fee below zero). It fits its training slices (train-slice Sharpe 2.68) but not the next three months (validation 0.03), so the 'do no harm' rule sends 59% of fold models to neutral: it is flat 65% of the time.
- **It did learn when not to trade.** Turnover 46 a year and 103 trades a year (Phase 2: ~600 and ~500), average hold 84 h, cost drag 8.1% a year (Phase 2: ~80%). Costs are no longer what sinks it; the lack of an edge is.
- **Continual learning.** Seed-mean Sharpe: static (a) -0.42, continual (b) -0.14, continual + retrain (c) -0.37. All negative after costs on BTC.
- **The variants that make money lean on momentum or on a buy-and-hold core:** v3 higher-timeframe alignment Sharpe 0.50, Calmar 0.19, max DD 37%, net +48%; v5 meta-labeling on momentum Sharpe 0.35, Calmar 0.10, max DD 55%, net +38%; v6 core-satellite (0..1.5x) Sharpe 0.48, Calmar 0.18, max DD 67%, net +106%. Buy-and-hold: Sharpe 0.64, Calmar 0.29; momentum: 0.63, 0.34. None beats them on Sharpe.
- **On the loop's rules (dev span):** the residual agents trade the baseline more (turnover ~80 a year vs ~45) and lower its Sharpe and return; imitation warm starts beat the same agent from scratch but end far below the rules they imitated: RL fine-tuning on 9 months of 15m data unlearns the rule.
- **Diagnostic (Phase 2's seen trades):** filters cut Phase 2's losses mostly by trading less; only seed consensus turned positive (Sharpe 0.56, 13 trades a year), i.e. by almost never trading. Filtering a no-edge agent removes cost, not the missing edge.

## By seed, both fees (BTC, Sharpe / net return / break-even fee)

| Variant | seed 0 | seed 1 | seed 2 | mean, 0.10% | mean, 0.05% |
|---|---|---|---|---|---|
| (a) static, fresh model per fold | -0.07 / -25% / -0.025% (loses before fees) (0.05%: 0.02) | -0.60 / -65% / -0.356% (loses before fees) (0.05%: -0.52) | -0.58 / -66% / -0.280% (loses before fees) (0.05%: -0.50) | -0.42 / -52% | -0.33 / -45% |
| (b) continual fine-tuning, never reset | -0.01 / -31% / 0.024% (0.05%: 0.10) | -0.25 / -59% / -0.074% (loses before fees) (0.05%: -0.16) | -0.15 / -48% / -0.040% (loses before fees) (0.05%: 0.02) | -0.14 / -46% | -0.01 / -30% |
| (c) continual + full retrain each fold [primary] | -0.34 / -52% / -0.155% (loses before fees) (0.05%: -0.25) | -0.31 / -48% / -0.141% (loses before fees) (0.05%: -0.22) | -0.45 / -60% / -0.227% (loses before fees) (0.05%: -0.35) | -0.37 / -53% | -0.27 / -46% |
| v1 seed consensus (all 3 seeds agree) | - | - | - | -0.05 / -21% | 0.00 / -15% |
| v2 confidence gate | 0.20 / +12% / 0.201% (0.05%: 0.23) | 0.03 / -11% / -0.000% (loses before fees) (0.05%: 0.06) | -0.21 / -39% / -0.310% (loses before fees) (0.05%: -0.17) | 0.01 / -12% | 0.04 / -8% |
| v3 higher-timeframe alignment | 0.59 / +60% / 0.365% (0.05%: 0.68) | 0.49 / +45% / 0.326% (0.05%: 0.57) | 0.43 / +39% / 0.277% (0.05%: 0.52) | 0.50 / +48% | 0.59 / +61% |
| v4 volatility / cost gate | -0.11 / -26% / -0.091% (loses before fees) (0.05%: -0.06) | -0.15 / -34% / -0.130% (loses before fees) (0.05%: -0.11) | -0.17 / -34% / -0.170% (loses before fees) (0.05%: -0.11) | -0.15 / -31% | -0.09 / -26% |
| v5 meta-labeling on momentum | 0.30 / +29% / 0.192% (0.05%: 0.40) | 0.28 / +27% / 0.189% (0.05%: 0.37) | 0.45 / +60% / 0.279% (0.05%: 0.55) | 0.35 / +38% | 0.44 / +58% |
| v6 core-satellite (0..1.5x) | 0.43 / +73% / 0.196% (0.05%: 0.53) | 0.55 / +148% / 0.263% (0.05%: 0.69) | 0.47 / +97% / 0.228% (0.05%: 0.57) | 0.48 / +106% | 0.59 / +191% |

## BTC on the development span only (2020-10-01 to 2025-11-11): against the loop's rules A and B

The loop chose rules A and B on data before 2025-11-11 and keeps 2025-11-11 to 2026-11-11 sealed. So everything built on A or B (residual RL, imitation warm starts, the matching scratch agents) is scored on the 21 folds that end by 2025-11-11 and nowhere else; the last year is excluded from these numbers. The full-span agents are shown on the same span for comparison (their full-span numbers are above). A, B and the agents built on them use the loop's spot backtester (long legs up to 1x pay no funding) and no Phase 3 risk manager.

### 0.10% a side

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|
| Buy-and-hold (perp) | +418.4% | 0.83 | 1.18 | 79% | 0.48 | 0 | 0 | 44808 | 12.5% | > 5% |
| Buy-and-hold (spot) | +879.7% | 1.03 | 1.46 | 77% | 0.73 | 0 | 0 | 44808 | 0.0% | > 5% |
| Momentum (daily 30-day, perp) | +218.6% | 0.67 | 0.95 | 63% | 0.41 | 60 | 30 | 293 | 15.2% | 0.477% |
| A: loop H29 H30 1.5x/0x spot | +1809.3% | 1.19 | 1.69 | 65% | 1.20 | 45 | 30 | 328 | 10.8% | 1.379% |
| B: loop H29 H31 trail 4 ATR spot | +1301.3% | 1.32 | 1.88 | 53% | 1.28 | 46 | 53 | 315 | 7.6% | 1.223% |
| Random agent (mean of 10) | -92.0% | -0.91 | -1.28 | 95% | -0.45 | 323 | 243 | 36 | 42.9% | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +398.4% | 0.91 | 1.28 | 68% | 0.54 | 20 | 80 | 44808 | 12.8% | 1.697% |
| *reference: momentum through the Phase 3 risk manager* | +250.2% | 0.76 | 1.07 | 49% | 0.56 | 64 | 101 | 293 | 14.2% | 0.480% |
| residual RL on A (+-0.5x), mean of 3 seeds | +1457.9% | 1.09 | 1.55 | 75% | 0.94 | 80 | 88 | 265 | 17.3% | 0.765% |
| &nbsp;&nbsp;seed 0 | +1352.8% | 1.08 | 1.53 | 75% | 0.91 | 79 | 86 | 262 | 17.0% | 0.757% |
| &nbsp;&nbsp;seed 1 | +1504.9% | 1.10 | 1.56 | 74% | 0.98 | 82 | 92 | 259 | 17.9% | 0.756% |
| &nbsp;&nbsp;seed 2 | +1516.0% | 1.11 | 1.57 | 76% | 0.95 | 79 | 87 | 272 | 17.0% | 0.782% |
| residual RL on B (+-0.5x), mean of 3 seeds | +806.1% | 1.06 | 1.50 | 68% | 0.79 | 80 | 111 | 255 | 14.4% | 0.629% |
| &nbsp;&nbsp;seed 0 | +629.6% | 0.99 | 1.41 | 66% | 0.72 | 77 | 107 | 251 | 13.7% | 0.602% |
| &nbsp;&nbsp;seed 1 | +969.1% | 1.10 | 1.57 | 66% | 0.89 | 84 | 117 | 260 | 15.2% | 0.651% |
| &nbsp;&nbsp;seed 2 | +819.6% | 1.07 | 1.52 | 73% | 0.74 | 81 | 110 | 255 | 14.3% | 0.636% |
| imitation warm start on A, then RL, mean of 3 seeds | -42.3% | 0.18 | 0.25 | 79% | -0.13 | 102 | 113 | 122 | 18.5% | -0.008% (loses before fees) |
| &nbsp;&nbsp;seed 0 | -50.3% | 0.14 | 0.20 | 81% | -0.16 | 99 | 110 | 125 | 18.3% | -0.037% (loses before fees) |
| &nbsp;&nbsp;seed 1 | -23.7% | 0.25 | 0.35 | 74% | -0.07 | 90 | 101 | 134 | 16.7% | 0.041% |
| &nbsp;&nbsp;seed 2 | -52.7% | 0.15 | 0.21 | 84% | -0.16 | 116 | 128 | 106 | 20.5% | -0.027% (loses before fees) |
| imitation warm start on B, then RL, mean of 3 seeds | -44.1% | 0.12 | 0.17 | 87% | -0.16 | 107 | 127 | 121 | 19.0% | -0.059% (loses before fees) |
| &nbsp;&nbsp;seed 0 | -83.3% | -0.14 | -0.20 | 91% | -0.32 | 103 | 121 | 126 | 18.5% | -0.239% (loses before fees) |
| &nbsp;&nbsp;seed 1 | +7.1% | 0.37 | 0.52 | 88% | 0.02 | 110 | 135 | 122 | 19.2% | 0.112% |
| &nbsp;&nbsp;seed 2 | -56.0% | 0.12 | 0.17 | 82% | -0.18 | 107 | 125 | 114 | 19.1% | -0.050% (loses before fees) |
| same agent from scratch (A's inputs), mean of 3 seeds | -68.4% | 0.00 | 0.00 | 88% | -0.24 | 99 | 120 | 123 | 18.5% | -0.147% (loses before fees) |
| &nbsp;&nbsp;seed 0 | -81.7% | -0.13 | -0.18 | 92% | -0.31 | 97 | 121 | 128 | 18.3% | -0.241% (loses before fees) |
| &nbsp;&nbsp;seed 1 | -71.7% | -0.02 | -0.03 | 88% | -0.25 | 95 | 109 | 113 | 17.7% | -0.161% (loses before fees) |
| &nbsp;&nbsp;seed 2 | -51.9% | 0.15 | 0.21 | 83% | -0.16 | 104 | 129 | 129 | 19.5% | -0.037% (loses before fees) |
| same agent from scratch (B's inputs), mean of 3 seeds | -70.1% | -0.02 | -0.03 | 89% | -0.25 | 99 | 120 | 124 | 18.2% | -0.156% (loses before fees) |
| &nbsp;&nbsp;seed 0 | -82.8% | -0.18 | -0.25 | 93% | -0.31 | 94 | 117 | 119 | 17.2% | -0.265% (loses before fees) |
| &nbsp;&nbsp;seed 1 | -74.3% | -0.02 | -0.03 | 90% | -0.26 | 106 | 124 | 121 | 19.2% | -0.151% (loses before fees) |
| &nbsp;&nbsp;seed 2 | -53.2% | 0.14 | 0.20 | 84% | -0.17 | 99 | 119 | 132 | 18.3% | -0.050% (loses before fees) |
| (a) static, fresh model per fold, mean of 3 seeds | -46.0% | -0.36 | -0.50 | 72% | -0.16 | 47 | 116 | 104 | 6.6% | -0.170% (loses before fees) |
| (b) continual fine-tuning, never reset, mean of 3 seeds | -30.7% | -0.03 | -0.05 | 72% | -0.10 | 87 | 198 | 123 | 15.2% | 0.012% |
| **(c) continual + full retrain each fold [primary], mean of 3 seeds** | **-45.0%** | **-0.29** | **-0.41** | **76%** | **-0.15** | **54** | **121** | **79** | **9.6%** | **-0.119% (loses before fees)** |
| v1 seed consensus (all 3 seeds agree) | -21.3% | -0.06 | -0.08 | 66% | -0.07 | 38 | 81 | 90 | 7.4% | -0.022% (loses before fees) |
| v2 confidence gate, mean of 3 seeds | -12.5% | 0.01 | 0.01 | 70% | -0.04 | 22 | 54 | 157 | 4.7% | -0.037% (loses before fees) |
| v3 higher-timeframe alignment, mean of 3 seeds | +49.4% | 0.56 | 0.79 | 37% | 0.23 | 34 | 76 | 41 | 6.9% | 0.329% |
| v4 volatility / cost gate, mean of 3 seeds | -31.2% | -0.16 | -0.22 | 70% | -0.10 | 32 | 84 | 107 | 6.8% | -0.130% (loses before fees) |
| v5 meta-labeling on momentum, mean of 3 seeds | +46.7% | 0.43 | 0.60 | 51% | 0.15 | 51 | 114 | 67 | 10.1% | 0.246% |
| v6 core-satellite (0..1.5x), mean of 3 seeds | +253.4% | 0.74 | 1.04 | 67% | 0.42 | 94 | 229 | 265 | 22.6% | 0.359% |

### 0.05% a side

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|
| Buy-and-hold (perp) | +418.6% | 0.83 | 1.18 | 79% | 0.48 | 0 | 0 | 44808 | 12.5% | > 5% |
| Buy-and-hold (spot) | +880.2% | 1.03 | 1.46 | 77% | 0.73 | 0 | 0 | 44808 | 0.0% | > 5% |
| Momentum (daily 30-day, perp) | +271.2% | 0.72 | 1.02 | 61% | 0.48 | 60 | 30 | 293 | 12.3% | 0.477% |
| A: loop H29 H30 1.5x/0x spot | +2040.2% | 1.22 | 1.74 | 64% | 1.28 | 45 | 30 | 328 | 8.6% | 1.379% |
| B: loop H29 H31 trail 4 ATR spot | +1474.7% | 1.37 | 1.95 | 51% | 1.39 | 46 | 53 | 315 | 5.3% | 1.223% |
| Random agent (mean of 10) | -81.7% | -0.59 | -0.83 | 91% | -0.36 | 323 | 243 | 36 | 26.8% | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +413.1% | 0.92 | 1.30 | 69% | 0.55 | 21 | 86 | 44808 | 12.1% | 1.566% |
| *reference: momentum through the Phase 3 risk manager* | +290.7% | 0.81 | 1.14 | 48% | 0.63 | 67 | 113 | 293 | 11.2% | 0.445% |
| residual RL on A (+-0.5x), mean of 3 seeds | +1813.6% | 1.15 | 1.63 | 73% | 1.06 | 80 | 88 | 265 | 13.3% | 0.765% |
| residual RL on B (+-0.5x), mean of 3 seeds | +1014.7% | 1.13 | 1.60 | 66% | 0.91 | 80 | 111 | 255 | 10.4% | 0.629% |
| imitation warm start on A, then RL, mean of 3 seeds | -25.4% | 0.25 | 0.36 | 76% | -0.07 | 102 | 113 | 122 | 13.4% | -0.008% (loses before fees) |
| imitation warm start on B, then RL, mean of 3 seeds | -26.2% | 0.19 | 0.27 | 86% | -0.11 | 107 | 127 | 121 | 13.6% | -0.059% (loses before fees) |
| same agent from scratch (A's inputs), mean of 3 seeds | -59.2% | 0.07 | 0.10 | 86% | -0.20 | 99 | 120 | 123 | 13.6% | -0.147% (loses before fees) |
| same agent from scratch (B's inputs), mean of 3 seeds | -61.4% | 0.05 | 0.07 | 87% | -0.20 | 99 | 120 | 124 | 13.3% | -0.156% (loses before fees) |
| (a) static, fresh model per fold, mean of 3 seeds | -39.3% | -0.27 | -0.38 | 69% | -0.14 | 48 | 118 | 104 | 4.4% | -0.167% (loses before fees) |
| (b) continual fine-tuning, never reset, mean of 3 seeds | -12.1% | 0.09 | 0.13 | 69% | -0.04 | 87 | 198 | 123 | 11.0% | 0.015% |
| **(c) continual + full retrain each fold [primary], mean of 3 seeds** | **-36.8%** | **-0.19** | **-0.27** | **74%** | **-0.12** | **54** | **121** | **79** | **7.0%** | **-0.118% (loses before fees)** |
| v1 seed consensus (all 3 seeds agree) | -14.9% | 0.00 | 0.00 | 65% | -0.05 | 39 | 84 | 90 | 5.6% | -0.031% (loses before fees) |
| v2 confidence gate, mean of 3 seeds | -8.2% | 0.04 | 0.06 | 70% | -0.03 | 23 | 56 | 157 | 3.6% | -0.039% (loses before fees) |
| v3 higher-timeframe alignment, mean of 3 seeds | +62.2% | 0.66 | 0.93 | 34% | 0.30 | 34 | 77 | 41 | 5.2% | 0.324% |
| v4 volatility / cost gate, mean of 3 seeds | -25.8% | -0.10 | -0.14 | 69% | -0.08 | 32 | 84 | 107 | 5.3% | -0.131% (loses before fees) |
| v5 meta-labeling on momentum, mean of 3 seeds | +66.3% | 0.53 | 0.74 | 49% | 0.22 | 51 | 115 | 67 | 7.6% | 0.242% |
| v6 core-satellite (0..1.5x), mean of 3 seeds | +370.8% | 0.85 | 1.20 | 62% | 0.56 | 93 | 226 | 265 | 17.7% | 0.372% |


## ETH robustness check (same frozen settings, base family only)

### 0.10% a side

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|
| (a) static, fresh model per fold, mean of 3 seeds | -43.6% | -0.25 | -0.35 | 76% | -0.13 | 46 | 131 | 132 | 8.9% | -0.192% (loses before fees) |
| &nbsp;&nbsp;seed 0 | -39.0% | -0.10 | -0.13 | 72% | -0.11 | 58 | 162 | 104 | 11.2% | -0.039% (loses before fees) |
| &nbsp;&nbsp;seed 1 | -76.1% | -0.72 | -0.99 | 86% | -0.24 | 35 | 107 | 148 | 7.0% | -0.574% (loses before fees) |
| &nbsp;&nbsp;seed 2 | -15.6% | 0.05 | 0.07 | 70% | -0.04 | 44 | 124 | 146 | 8.3% | 0.037% |
| (b) continual fine-tuning, never reset, mean of 3 seeds | -67.1% | -0.26 | -0.36 | 93% | -0.18 | 104 | 264 | 97 | 19.0% | -0.077% (loses before fees) |
| &nbsp;&nbsp;seed 0 | -68.3% | -0.27 | -0.37 | 93% | -0.18 | 100 | 254 | 97 | 18.3% | -0.088% (loses before fees) |
| &nbsp;&nbsp;seed 1 | -73.0% | -0.35 | -0.48 | 94% | -0.20 | 105 | 269 | 94 | 19.2% | -0.104% (loses before fees) |
| &nbsp;&nbsp;seed 2 | -59.9% | -0.17 | -0.23 | 90% | -0.15 | 109 | 270 | 98 | 19.6% | -0.038% (loses before fees) |
| **(c) continual + full retrain each fold [primary], mean of 3 seeds** | **-4.9%** | **0.13** | **0.18** | **75%** | **-0.01** | **52** | **130** | **89** | **11.2%** | **0.081%** |
| &nbsp;&nbsp;seed 0 | -3.8% | 0.15 | 0.21 | 77% | -0.01 | 63 | 156 | 79 | 13.7% | 0.090% |
| &nbsp;&nbsp;seed 1 | -12.0% | 0.07 | 0.10 | 77% | -0.03 | 42 | 110 | 91 | 9.4% | 0.051% |
| &nbsp;&nbsp;seed 2 | +1.0% | 0.16 | 0.22 | 73% | 0.00 | 51 | 124 | 97 | 10.5% | 0.103% |
| v1 seed consensus (all 3 seeds agree) | +44.2% | 0.35 | 0.49 | 66% | 0.09 | 33 | 80 | 123 | 8.2% | 0.283% |
| v2 confidence gate, mean of 3 seeds | -25.0% | -0.08 | -0.11 | 70% | -0.07 | 15 | 44 | 187 | 5.1% | -0.306% (loses before fees) |
| v3 higher-timeframe alignment, mean of 3 seeds | +46.6% | 0.42 | 0.59 | 30% | 0.21 | 39 | 88 | 45 | 8.4% | 0.262% |
| v4 volatility / cost gate, mean of 3 seeds | +60.9% | 0.41 | 0.57 | 63% | 0.13 | 26 | 71 | 137 | 7.8% | 0.401% |
| Buy-and-hold (perp) | +172.2% | 0.60 | 0.85 | 82% | 0.22 | 0 | 0 | 53556 | 12.1% | > 5% |
| Momentum (daily 30-day, long/short) | +727.8% | 0.83 | 1.18 | 80% | 0.51 | 55 | 28 | 317 | 15.9% | 0.722% |
| Random agent (mean of 10) | -96.6% | -0.73 | -1.02 | 98% | -0.48 | 323 | 243 | 36 | 45.3% | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +170.5% | 0.58 | 0.81 | 64% | 0.28 | 21 | 88 | 53556 | 11.7% | 0.867% |
| *reference: momentum through the Phase 3 risk manager* | +688.0% | 0.91 | 1.30 | 70% | 0.57 | 65 | 132 | 317 | 14.3% | 0.616% |

### 0.05% a side

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|
| (a) static, fresh model per fold, mean of 3 seeds | -34.6% | -0.18 | -0.25 | 75% | -0.10 | 47 | 136 | 132 | 6.8% | -0.182% (loses before fees) |
| (b) continual fine-tuning, never reset, mean of 3 seeds | -55.5% | -0.14 | -0.19 | 91% | -0.14 | 106 | 267 | 97 | 13.9% | -0.079% (loses before fees) |
| **(c) continual + full retrain each fold [primary], mean of 3 seeds** | **+6.6%** | **0.19** | **0.26** | **74%** | **0.01** | **53** | **132** | **89** | **8.6%** | **0.068%** |
| v1 seed consensus (all 3 seeds agree) | +62.4% | 0.42 | 0.59 | 63% | 0.13 | 33 | 80 | 123 | 6.6% | 0.289% |
| v2 confidence gate, mean of 3 seeds | -22.6% | -0.06 | -0.08 | 69% | -0.06 | 15 | 43 | 187 | 4.3% | -0.311% (loses before fees) |
| v3 higher-timeframe alignment, mean of 3 seeds | +66.2% | 0.53 | 0.73 | 28% | 0.31 | 39 | 87 | 45 | 6.4% | 0.264% |
| v4 volatility / cost gate, mean of 3 seeds | +83.9% | 0.47 | 0.66 | 62% | 0.17 | 25 | 69 | 137 | 6.5% | 0.432% |
| Buy-and-hold (perp) | +172.4% | 0.60 | 0.85 | 82% | 0.22 | 0 | 0 | 53556 | 12.1% | > 5% |
| Momentum (daily 30-day, long/short) | +880.0% | 0.87 | 1.23 | 79% | 0.57 | 55 | 28 | 317 | 13.2% | 0.722% |
| Random agent (mean of 10) | -90.9% | -0.47 | -0.66 | 97% | -0.39 | 323 | 243 | 36 | 29.1% | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +176.6% | 0.58 | 0.82 | 63% | 0.29 | 24 | 98 | 53556 | 10.9% | 0.748% |
| *reference: momentum through the Phase 3 risk manager* | +879.8% | 0.98 | 1.40 | 68% | 0.67 | 71 | 155 | 317 | 11.5% | 0.573% |


## Behaviour out of sample (BTC, 0.10%): turnover, holding, what the gates did

| Variant | Turnover/yr | Trades/yr | Avg hold (h) | Long / flat / short | Mean abs size | Gross Sharpe | Fee drag/yr | Decision stats (per seed, summed) |
|---|---|---|---|---|---|---|---|---|
| (a) static, fresh model per fold | 40 | 101 | 108 | 19 / 65 / 17% | 0.20 | -0.19 | 4.0% | changes 1591, forced 0, min_hold_refusals 194, gate_refusals 0, band_holds 0 |
| (b) continual fine-tuning, never reset | 80 | 180 | 130 | 48 / 20 / 32% | 0.49 | 0.26 | 8.0% | changes 2737, forced 0, min_hold_refusals 410, gate_refusals 0, band_holds 0 |
| (c) continual + full retrain each fold [primary] | 46 | 103 | 84 | 20 / 65 / 15% | 0.21 | -0.05 | 4.6% | changes 1743, forced 0, min_hold_refusals 213, gate_refusals 0, band_holds 0 |
| v1 seed consensus (all 3 seeds agree) | 32 | 68 | 90 | 18 / 73 / 10% | 0.16 | 0.22 | 3.2% | changes 386, forced 0, min_hold_refusals 31, disagree_holds 141 |
| v2 confidence gate | 19 | 45 | 157 | 18 / 73 / 9% | 0.17 | 0.17 | 1.9% | changes 563, forced 0, min_hold_refusals 83, gate_refusals 0, band_holds 35724 |
| v3 higher-timeframe alignment | 29 | 64 | 40 | 8 / 89 / 3% | 0.07 | 0.89 | 2.9% | changes 1161, forced 228, min_hold_refusals 48, gate_refusals 0, band_holds 0 |
| v4 volatility / cost gate | 27 | 70 | 107 | 20 / 71 / 9% | 0.17 | 0.10 | 2.7% | changes 952, forced 0, min_hold_refusals 148, gate_refusals 59115, band_holds 0 |
| v5 meta-labeling on momentum | 44 | 97 | 68 | 14 / 75 / 10% | 0.16 | 0.73 | 4.4% | changes 1694, forced 112, min_hold_refusals 135, gate_refusals 0, band_holds 0 |
| v6 core-satellite (0..1.5x) | 90 | 225 | 327 | 81 / 19 / 0% | 0.81 | 0.91 | 9.0% | changes 1820, forced 0, min_hold_refusals 247, gate_refusals 0, band_holds 0 |

Phase 2 for comparison: ~600 turnover a year, ~500 trades, 17 h average hold, ~80% of equity a year in costs.

Thresholds chosen per fold (from the 3 months before each fold; counts over folds and seeds): v2 confidence gate: 0 x1, 0.5 x10, 1 x4, 2 x10, 4 x50; v4 volatility / cost gate: 2 x4, 4 x6, 6 x7, 8 x58.

Risk manager on buy-and-hold (full span): vol_resize 241, brake_resize 299, brake_on_bars 72456.

## Overfitting flags (BTC)

| Variant | train_test_sharpe_gap | seed_dispersion | beats_benchmarks_in_under_half_the_folds | fee_sign_flip | edge_only_at_0.05 | high_turnover | degenerate_policy |
|---|---|---|---|---|---|---|---|
| (a) static, fresh model per fold | FIRED | - | FIRED | - | - | - | - |
| (b) continual fine-tuning, never reset | FIRED | - | FIRED | - | - | - | - |
| (c) continual + full retrain each fold [primary] | FIRED | - | FIRED | - | - | - | - |
| v1 seed consensus (all 3 seeds agree) | n/a | n/a | FIRED | - | - | - | - |
| v2 confidence gate | n/a | FIRED | FIRED | - | - | - | - |
| v3 higher-timeframe alignment | n/a | - | FIRED | - | - | - | - |
| v4 volatility / cost gate | n/a | - | FIRED | - | - | - | - |
| v5 meta-labeling on momentum | FIRED | - | FIRED | - | - | - | - |
| v6 core-satellite (0..1.5x) | FIRED | - | FIRED | - | - | - | - |
| residual RL on A (+-0.5x) | FIRED | - | FIRED | - | - | - | - |
| residual RL on B (+-0.5x) | FIRED | - | FIRED | - | - | - | - |
| imitation warm start on A, then RL | FIRED | - | FIRED | - | - | FIRED | - |
| imitation warm start on B, then RL | FIRED | FIRED | FIRED | - | - | FIRED | - |
| same agent from scratch (A's inputs) | FIRED | - | FIRED | - | - | FIRED | - |
| same agent from scratch (B's inputs) | FIRED | - | FIRED | - | - | FIRED | - |

- **train_test_sharpe_gap: FIRED.** mean over folds and seeds: train-slice Sharpe 2.68, validation 0.03, test -0.89; gap 3.57 (threshold 1.0); neutral fallback in 59% of fold models
- **seed_dispersion: not fired.** stitched Sharpe by seed -0.34, -0.31, -0.45 (sd 0.07, threshold 0.50)
- **beats_benchmarks_in_under_half_the_folds: FIRED.** folds with a higher seed-mean Sharpe: buy_hold 7/25, momentum 5/25
- **fee_sign_flip: not fired.** no seed changes sign
- **edge_only_at_0.05: not fired.** seed mean: net -53.4% / Sharpe -0.37 at 0.10% (buy-and-hold 0.64); net -46.5% / Sharpe -0.27 at 0.05% (buy-and-hold 0.64)
- **high_turnover: not fired.** turnover per year by seed 46, 45, 46 (threshold 100)
- **degenerate_policy: not fired.** long / flat / short share of bars by seed: 0 22/65/13%; 1 18/66/15%; 2 21/63/17%

ETH flags:

| Variant | train_test_sharpe_gap | seed_dispersion | beats_benchmarks_in_under_half_the_folds | fee_sign_flip | edge_only_at_0.05 | high_turnover | degenerate_policy |
|---|---|---|---|---|---|---|---|
| (a) static, fresh model per fold | FIRED | - | FIRED | - | - | - | - |
| (b) continual fine-tuning, never reset | FIRED | - | FIRED | - | - | FIRED | - |
| (c) continual + full retrain each fold [primary] | FIRED | FIRED | FIRED | FIRED | FIRED | - | - |
| v1 seed consensus (all 3 seeds agree) | n/a | n/a | FIRED | - | - | - | - |
| v2 confidence gate | n/a | - | FIRED | - | - | - | - |
| v3 higher-timeframe alignment | n/a | - | FIRED | - | - | - | - |
| v4 volatility / cost gate | n/a | - | FIRED | - | - | - | - |

## Learnability check (synthetic data, before the freeze)

Synthetic 15m-like series (fat tails, vol regimes, funding), 2 years each: 9 months train, 3 months validation, 12 months held-out synthetic test. Planted edge: a visible AR(1) signal (one-day half-life) predicting the next bar's return with a per-bar information coefficient of kappa. A cost-aware oracle that KNOWS the signal shows what is attainable. Fresh series (seed base 2000), 5 seeds.

| Agent | Scenario | kappa | Test Sharpe (mean) | by seed | Oracle Sharpe | Train-slice Sharpe | Turnover/yr | Exposure |
|---|---|---|---|---|---|---|---|---|
| Phase 3 Q agent | edge | 0.020 | -0.00 | 0.45, 0.00, 0.06, -1.67, 1.15 | 0.90 | 3.02 | 82 | 74% |
| Phase 3 Q agent | edge_small | 0.010 | -0.04 | -0.13, 0.00, 0.00, 0.00, -0.08 | -0.01 | 1.00 | 19 | 38% |
| Phase 3 Q agent | none | 0.000 | -0.06 | -0.28, 0.00, 0.00, 0.00, 0.00 | -0.65 | 0.63 | 4 | 19% |
| PPO (Phase 2 algorithm), same reward | edge | 0.020 | -1.84 | -1.56, -0.49, -3.48 | 0.62 | -0.20 | 449 | 49% |
| PPO (Phase 2 algorithm), same reward | none | 0.000 | -1.04 | -0.80, -1.66, -0.67 | -0.89 | -0.19 | 276 | 47% |

Criteria (frozen before this run): edge_scenario edge, none_scenario none, edge_min_test_sharpe 0.5, edge_min_oracle_share 0.25, min_train_sharpe 0.5, none_min_test_sharpe -0.5, none_max_turnover 50, none_max_exposure 0.6. Result: **FAIL**.

**Supplementary power check** (added AFTER the frozen check failed; no agent setting changed): the same frozen agent on 10 new synthetic series with a 24-month test.

| Scenario | kappa | Test Sharpe (mean) | by seed | Oracle | Abstained (neutral fallback) | Corr. of position with the planted signal |
|---|---|---|---|---|---|---|
| edge | 0.020 | 0.56 | 1.15, 0.97, 0.86, 1.77, 0.00, 0.10, 0.78, 0.00, 0.00, 0.00 | 1.96 | 40% | 0.22 |
| none | 0.000 | -0.20 | 0.00, -0.09, -0.93, 0.00, 0.00, 0.00, -0.14, 0.00, -0.81, 0.00 | -0.32 | 60% | -0.03 |

How the setup was fixed (synthetic data only): Phase 2's PPO-style setup and a first Q-learner both took a position ~95% of the time even with no edge and fitted noise (train Sharpe 4-13 with nothing to find). Fixes, each tested only on synthetic series: (1) afterstate form (position enters only through the cost, which is hard-wired, not learned); (2) a zero-initialised output layer (random initial weights had been giving actions made-up preferences larger than the signal); (3) 16-step targets so value propagates over the holding horizon; (4) a linear value function (an MLP memorised the training path); (5) weight decay; (6) a 'do no harm' fallback to the neutral position when the validation Sharpe is below 0.5. A realistic edge is barely detectable in 9 months of 15m data (t-stat ~1.6 for an oracle-Sharpe-1 edge), which caps what any learner can recover.

## Update cadence (chosen before the freeze)

Rule: score = mean of (BTC pre-OOS validation Sharpe, synthetic drifting-edge test Sharpe); highest wins; ties -> the longer cadence. Scores: 7 day(s): BTC val Sharpe 0.57, synthetic drifting-edge test Sharpe -0.36; 1 day(s): BTC val Sharpe 0.32, synthetic drifting-edge test Sharpe -0.34. **Chosen: every 7 day(s).** BTC data used: before 2020-10-01 only.

## Risk manager check (on buy-and-hold and momentum, no agent; before any agent result)

| Asset | Strategy (0.10%, out of sample) | Sharpe raw | Sharpe with risk3 | Max DD raw | Max DD with risk3 | Pass |
|---|---|---|---|---|---|---|
| BTCUSDT | buy_hold | 0.64 | 0.68 | 79% | 68% | yes |
| BTCUSDT | momentum | 0.63 | 0.64 | 64% | 57% | yes |
| ETHUSDT | buy_hold | 0.60 | 0.58 | 82% | 64% | yes |
| ETHUSDT | momentum | 0.83 | 0.91 | 80% | 70% | yes |

Phase 2's limits on BTC buy-and-hold for comparison: Sharpe 0.18, net -20%, max DD 82%.

Rule: out of sample at 0.10%: Sharpe through the risk manager >= 0.9 x the raw Sharpe AND a smaller max drawdown, for buy-and-hold AND momentum. One revision allowed if it fails, reported as such. Result: **pass**.

## Forward paper mode: dry run on historical bars (not wired live)

Dry run BTCUSDT, 2026-10-28 00:00:00+00:00 to 2026-11-10 23:45:00+00:00 (1344 bars as if live, data cut at each bar, 2 scheduled update(s), 38 s): 1344 of 1344 decisions equal the batch walk-forward simulation from the same start model; executed targets after the risk manager differ by at most 0.0e+00. 0 target change(s). Log: C:\Ai Dataset\engine-15m\research/out/rl\paper_dryrun\BTCUSDT/decisions.jsonl. Nothing is wired into the live engine or the page.

## DIAGNOSTIC ONLY: the Phase 3 filters applied to the Phase 2 agent's trades

Not a result: it replays Phase 2's saved models on Phase 2's test windows, which have been seen. It only asks whether filtering a no-edge agent can help at all. Phase 2 targets replayed without Phase 2's risk manager; BTC; mean over the 5 Phase 2 seeds (consensus is one series).

| Filter | Net return 0.10% | Sharpe 0.10% | Max DD | Trades/yr | Avg hold (h) | Break-even fee | Net 0.05% | Sharpe 0.05% |
|---|---|---|---|---|---|---|---|---|
| unfiltered | -99.7% | -1.73 | 100% | 515 | 18 | -0.050% (loses before fees) | -97.9% | -1.07 |
| confidence | -63.3% | -0.19 | 87% | 111 | 95 | -0.047% (loses before fees) | -45.9% | -0.04 |
| htf | -87.0% | -1.01 | 93% | 279 | 15 | -0.026% (loses before fees) | -69.6% | -0.55 |
| vol_gate | -95.1% | -0.80 | 97% | 248 | 38 | -0.064% (loses before fees) | -87.2% | -0.48 |
| meta_label | -89.7% | -0.95 | 95% | 349 | 17 | -0.013% (loses before fees) | -70.0% | -0.45 |
| core_sat | -78.2% | -0.06 | 95% | 515 | 53579 | 0.021% | -42.2% | 0.19 |
| consensus | +164.0% | 0.56 | 86% | 13 | 694 | 1.016% | +178.3% | 0.58 |

Unfiltered = the Phase 2 PPO's own targets without Phase 2's risk manager. Thresholds fixed in phase3.yaml (diag2), not tuned here.

## What was frozen, and when

- 11 Nov 2026, ~13:45-14:20 UTC (synthetic data only): agent setup chosen on synthetic series (exploration seeds 1000+; no real data): afterstate Q-learning, linear W, zero-initialised output, 16-step targets, weight decay 0.3, risk aversion 1.0, vol-scaled reward, round-trip cost charge, validation-loss early stopping, neutral fallback at a validation Sharpe of 0.5
- 11 Nov 2026, ~14:20 UTC: this file drafted with every value (features, actions, min hold, agent, families incl. the owner's two addenda: the six filter / harness variants and the loop-rule baselines A / B with residual RL and imitation warm starts on the dev span only), the risk manager draft and the learnability / risk-check / cadence rules, before those checks ran
- 11 Nov 2026, 14:24 UTC: risk check of the draft risk manager on buy-and-hold and momentum (no agent): failed on buy-and-hold; revision 1 (slow vol rv_672, 60 pct target) chosen after looking at five versions on benchmark numbers; the revised check passed at 14:31 UTC
- 11 Nov 2026, 14:28 UTC: learnability check on fresh synthetic series: FAIL on the frozen criteria (planted edge not found reliably; near-flat without an edge: yes; fits its training slice: yes). No agent setting was changed afterwards. One design change was made after it: the neutral fallback became a per-fold flag instead of overwriting the weights, because continual fine-tuning was seen to erode an overwritten neutral model (cadence run, synthetic); static decisions are identical either way
- 11 Nov 2026, 14:38 UTC: update cadence: weekly (score 0.10 vs daily -0.01; BTC data before 2020-10-01 only)
- 11 Nov 2026, 14:39 UTC: everything frozen; then the walk-forward runs (BTC, then ETH), once
- No test-window number fed back into any setting; nothing was re-run after the test results were seen.

## Design (fixed before testing)

- **Clock and timing.** Every 15m bar: decide at the close, fill at the next open (the shared cost model's delay), hold to the next bar. Holding is free; minimum hold 4 bars between changes.
- **Observation.** Phase 2's 18 point-in-time features + higher-timeframe context on closed bars (1h / 4h / 1d trend and price vs the higher-timeframe mean, the frozen momentum signal, 30-day daily vol, a vol regime) + time of day / week; funding already in. z-scored on the trailing 12 months, clipped at +-5. The real-data truncation check runs on every column.
- **Agent.** Afterstate Q-learning: W(x, a) learned (linear), Q(x, p, a) = W(x, a) - cost(p -> a) with the cost hard-wired; reward = vol-scaled net return of the target - 2 x the real one-side cost on every change (a full round trip) - a risk charge 1.0 x a^2 x vol^2; gamma 0.99, 16-step targets, AdamW lr 0.0005, weight decay 0.3, batch 256; early stopping on the validation Bellman loss; neutral fallback when the kept model's validation Sharpe < 0.5.
- **Actions.** Base: target size in {-1, -0.5, 0, 0.5, 1}. Meta-labeling: {0, 0.5, 1} x the momentum direction. Core-satellite: {0, 0.5, 1, 1.5} with 1x as the default. Residual: baseline + {-0.5, 0, +0.5}. Warm start / scratch (on A / B): {0, 0.5, 1, 1.5, 2}, spot long legs.
- **Continual learning.** Updates every 7 day(s) at the 00:00 UTC bar close: 200 gradient steps on a replay buffer of the trailing 365 days (half uniform, half with a 60-day recency half-life), warm-started from the previous weights and optimiser; an update at bar U trains only on decisions whose n-step targets close by bar U.
- **Risk manager (Phase 3).** size = min(1, 60% / rv_672 annualised) x drawdown brake (1.0, then 0.75/0.5 at 20%/30% below the rolling 90-day peak); re-sized only when the size moves by more than 0.20; every resize logged with its reason.
- **Walk-forward.** Phase 1's folds (12-month train: 9 train + 3 validation, 3-month test, roll 3 months). One decision loop runs across all test windows (position carries over); the executed series is replayed through the shared backtester and scored like the benchmarks.

## Per fold, primary agent (c), BTC, 0.10%

| # | Test window | Agent net, mean (min..max) | Agent Sharpe | B&H net | B&H Sharpe | Mom net | Mom Sharpe |
|---|---|---|---|---|---|---|---|
| 0 | 2020-10-01 .. 2021-01-01 | +74.5% (+72% .. +78%) | 4.93 | +155.6% | 6.04 | +168.0% | 6.33 |
| 1 | 2021-01-01 .. 2021-04-01 | +11.3% (-1% .. +19%) | 1.03 | +72.4% | 2.49 | +34.9% | 1.63 |
| 2 | 2021-04-01 .. 2021-07-01 | -32.6% (-34% .. -31%) | -3.66 | -44.4% | -1.68 | -21.2% | -0.36 |
| 3 | 2021-07-01 .. 2021-10-01 | -0.2% (-0% .. -0%) | -2.42 | +22.4% | 1.54 | +13.6% | 1.09 |
| 4 | 2021-10-01 .. 2022-01-01 | -8.4% (-11% .. -5%) | -0.61 | +0.3% | 0.35 | +1.7% | 0.43 |
| 5 | 2022-01-01 .. 2022-04-01 | -10.5% (-17% .. -2%) | -0.95 | -2.8% | 0.16 | -31.9% | -2.03 |
| 6 | 2022-04-01 .. 2022-07-01 | -4.2% (-9% .. -0%) | -1.17 | -56.6% | -4.00 | +40.9% | 2.18 |
| 7 | 2022-07-01 .. 2022-10-01 | -0.6% (-1% .. +0%) | -0.84 | -3.7% | 0.07 | +2.4% | 0.46 |
| 8 | 2022-10-01 .. 2023-01-01 | +0.0% (+0% .. +0%) | 0.00 | -15.5% | -1.16 | -27.6% | -2.45 |
| 9 | 2023-01-01 .. 2023-04-01 | -14.4% (-22% .. +0%) | -2.22 | +68.6% | 4.31 | +52.3% | 3.52 |
| 10 | 2023-04-01 .. 2023-07-01 | -0.1% (-0% .. +0%) | -1.89 | +5.4% | 0.72 | -3.5% | -0.14 |
| 11 | 2023-07-01 .. 2023-10-01 | -12.4% (-14% .. -9%) | -3.25 | -12.6% | -1.24 | +9.5% | 1.15 |
| 12 | 2023-10-01 .. 2024-01-01 | -0.0% (-0% .. -0%) | -0.95 | +52.2% | 3.97 | +51.8% | 3.95 |
| 13 | 2024-01-01 .. 2024-04-01 | -19.3% (-30% .. -13%) | -2.18 | +59.5% | 3.52 | +1.6% | 0.40 |
| 14 | 2024-04-01 .. 2024-07-01 | -0.3% (-0% .. -0%) | -2.76 | -14.0% | -1.01 | +3.3% | 0.51 |
| 15 | 2024-07-01 .. 2024-10-01 | +0.0% (+0% .. +0%) | 0.00 | -0.0% | 0.27 | -51.4% | -4.94 |
| 16 | 2024-10-01 .. 2025-01-01 | +0.0% (+0% .. +0%) | 0.00 | +43.1% | 3.06 | +40.1% | 2.89 |
| 17 | 2025-01-01 .. 2025-04-01 | -6.8% (-8% .. -5%) | -0.53 | -12.9% | -0.74 | -22.9% | -1.63 |
| 18 | 2025-04-01 .. 2025-07-01 | -3.0% (-9% .. -0%) | -0.71 | +28.6% | 2.64 | -1.2% | 0.09 |
| 19 | 2025-07-01 .. 2025-10-01 | -0.0% (-0% .. +0%) | -0.92 | +4.6% | 0.74 | +2.6% | 0.48 |
| 20 | 2025-10-01 .. 2026-01-01 | +0.0% (+0% .. +0%) | 0.00 | -24.0% | -2.07 | +15.1% | 1.42 |
| 21 | 2026-01-01 .. 2026-04-01 | +0.0% (+0% .. +0%) | 0.00 | -22.3% | -1.60 | -22.7% | -1.63 |
| 22 | 2026-04-01 .. 2026-07-01 | +0.0% (+0% .. +0%) | 0.00 | -14.3% | -1.29 | +19.1% | 1.89 |
| 23 | 2026-07-01 .. 2026-10-01 | -14.4% (-22% .. +0%) | -3.21 | +40.3% | 4.05 | -12.0% | -1.29 |
| 24 | 2026-10-01 .. 2026-11-11 | +0.0% (+0% .. +0%) | 0.11 | -12.1% | -3.12 | +13.4% | 3.39 |

## Training

- (a) static, fresh model per fold: train-slice Sharpe 2.68 (positive in 100% of fold models), validation 0.03, test -0.61; neutral fallback in 59% of fold models.
- (b) continual fine-tuning, never reset: train-slice Sharpe 2.03 (positive in 96% of fold models), validation 2.86, test -0.30; neutral fallback in 8% of fold models.
- (c) continual + full retrain each fold [primary]: train-slice Sharpe 2.68 (positive in 100% of fold models), validation 0.03, test -0.89; neutral fallback in 59% of fold models.
- v5 meta-labeling on momentum: train-slice Sharpe 2.73 (positive in 100% of fold models), validation 0.19, test -0.17; neutral fallback in 56% of fold models.
- v6 core-satellite (0..1.5x): train-slice Sharpe 1.97 (positive in 100% of fold models), validation 0.52, test 0.20; neutral fallback in 52% of fold models.
- residual RL on A (+-0.5x): train-slice Sharpe 2.69 (positive in 98% of fold models), validation 0.38, test 0.55; neutral fallback in 57% of fold models.
- residual RL on B (+-0.5x): train-slice Sharpe 2.65 (positive in 100% of fold models), validation 0.43, test 0.55; neutral fallback in 57% of fold models.
- imitation warm start on A, then RL: train-slice Sharpe 2.09 (positive in 98% of fold models), validation 1.01, test -0.10; neutral fallback in 52% of fold models.
- imitation warm start on B, then RL: train-slice Sharpe 2.02 (positive in 100% of fold models), validation 0.90, test -0.08; neutral fallback in 52% of fold models.
- same agent from scratch (A's inputs): train-slice Sharpe 2.04 (positive in 100% of fold models), validation 0.74, test -0.43; neutral fallback in 52% of fold models.
- same agent from scratch (B's inputs): train-slice Sharpe 2.06 (positive in 100% of fold models), validation 0.76, test -0.37; neutral fallback in 51% of fold models.
- Real-data look-ahead check of the Phase 3 feature set (3 random cuts per asset): BTCUSDT {'59009': [], '126356': [], '248128': []}; ETHUSDT {'58972': [], '126272': [], '247961': []}.
- Memory: work started only with >= 700 MB free and paused (never failed) under 350 MB. Pauses: 2026-11-11 14:47:59 BTCUSDT base s0 fold 14 (b) (under the 350 MB floor while running, waited 20s); 2026-11-11 15:02:51 BTCUSDT meta s0 fold 14 (under the 350 MB floor while running, waited 20s); 2026-11-11 15:17:42 BTCUSDT core s1 fold 2 (under the 350 MB floor while running, waited 20s); 2026-11-11 16:22:01 BTCUSDT scr_A s0 fold 14 (under the 350 MB floor while running, waited 20s).
- Models: C:\Ai Dataset\engine-15m\research/out/rl/models3\1bd0b404\BTCUSDT (one small .pt per fold model and per continual end-state; W values per fold as .npy).

## Not done here (Phase 4, not started)

- Wiring the forward paper mode into the live engine loop or the web page: the owner decides after review.

Machine-readable: `phase3_summary.json`. Risk manager log: `phase3_risk_log_btcusdt.csv` (and `_ethusdt`).

