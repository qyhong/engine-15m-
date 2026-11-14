# RL Phase 5 report: trade-less variants and which readings carry the edge

Run `phase5_20261112T100635Z_b8c8f31f`, generated 2026-11-12 10:10 UTC. Paper only. Parts 2 and 3 of Phase 5 (part 1, the forward paper run, is `engine15/playbook5.py`; its checks are summarised below). Seeds [0, 1, 2]; 15-minute bars and clock; Phase 4's data, folds, inputs, risk manager, backtester, fees and benchmarks.

**Holdout honesty.** Phase 4 already scored every test window through 2026-11-11, so no historical span is unseen for RL any more: every number below is in-sample in the sense that matters (the setup was chosen after looking at these windows). Both spans are shown: 2020-10-01 .. 2026-11-11 and up to 2025-11-11. The strategy loop's rules A and B (and every comparison with them) stop at 2025-11-11, the start of the loop's sealed year. The forward paper run is the only real test left.

## Part 1: the forward paper run (checks)

- Phase 4's fold-24 models rebuilt with the export hook: max |W - Phase 4's stored W| = 0.0, 0.0, 0.0 per seed and coin; exact: True.
- Forward step vs Phase 4's batch walk-forward on 2026-10-20 00:00 .. 2026-11-11 11:30 (4316 bars, 5 incremental steps, same model and bars): decisions identical True; executed positions max difference 0.00e+00; book equity max difference 1.82e-16; values max |W forward - W stored| 0.00e+00.

## Part 2: trade-less variants (frozen before any result; no retraining)

Each variant uses the Phase 4 primary's trained fold models unchanged; only the step from values to positions differs (configs/rl/phase5.yaml `trade_less`).

| Variant | Asset | Gross Sharpe (primary) | Net Sharpe 0.10% (primary) | Turnover/yr (primary) | Trades/yr (primary) | Keeps edge | Trades less | Beats B&H* | Beats momentum | Edge every seed |
|---|---|---|---|---|---|---|---|---|---|---|
| t1: wider no-trade band (2 round trips) | BTCUSDT | 0.42 (0.78) | 0.30 (0.48) | 11 (47) | 34 (110) | no | yes | no | no | yes |
| t1: wider no-trade band (2 round trips) | ETHUSDT | 0.79 (1.11) | 0.66 (0.77) | 15 (63) | 49 (158) | no | yes | no | no | yes |
| t2: minimum hold 2 days | BTCUSDT | 0.43 (0.78) | 0.24 (0.48) | 25 (47) | 60 (110) | no | yes | no | no | yes |
| t2: minimum hold 2 days | ETHUSDT | 0.92 (1.11) | 0.71 (0.77) | 30 (63) | 76 (158) | yes | yes | no | no | yes |
| t3: 1x spot core +- 0.5x agent tilt | BTCUSDT | 0.91 (0.78) | 0.83 (0.48) | 24 (47) | 110 (110) | yes | yes | no | yes | yes |
| t3: 1x spot core +- 0.5x agent tilt | ETHUSDT | 0.90 (1.11) | 0.82 (0.77) | 32 (63) | 159 (158) | yes | yes | yes | no | yes |

Full span 2020-10-01 .. 2026-11-11, seed means, after 0.10% fees. *B&H = perp buy-and-hold; for t3 (a spot core) spot buy-and-hold. Beats = Phase 4's rule (seed-mean Sharpe and Calmar above, every seed's Sharpe above).

### BTCUSDT, 2020-10-01 .. 2026-11-11, 0.10% a side

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Phase 4 primary (Q, BTC+ETH pooled, expanding, readings) [primary], mean of 3 seeds** | **+78.8%** | **0.48** | **0.67** | **41%** | **0.24** | **47** | **110** | **162** | **8.4%** | **0.78** | **0.298%** |
| &nbsp;&nbsp;seed 0 | +94.2% | 0.52 | 0.72 | 40% | 0.28 | 54 | 126 | 130 | 9.5% | 0.84 | 0.302% |
| &nbsp;&nbsp;seed 1 | +57.8% | 0.40 | 0.56 | 45% | 0.17 | 39 | 95 | 234 | 7.2% | 0.65 | 0.290% |
| &nbsp;&nbsp;seed 2 | +84.4% | 0.51 | 0.72 | 38% | 0.27 | 49 | 109 | 123 | 8.6% | 0.84 | 0.302% |
| t1: wider no-trade band (2 round trips), mean of 3 seeds | +31.4% | 0.30 | 0.42 | 48% | 0.10 | 11 | 34 | 1000 | 3.5% | 0.42 | 0.565% |
| t2: minimum hold 2 days, mean of 3 seeds | +22.2% | 0.24 | 0.34 | 47% | 0.07 | 25 | 60 | 453 | 5.0% | 0.43 | 0.217% |
| t3: 1x spot core +- 0.5x agent tilt, mean of 3 seeds | +662.5% | 0.83 | 1.18 | 80% | 0.49 | 24 | 110 | 53579 | 4.9% | 0.91 | 1.505% |
| Buy-and-hold (perp) | +249.3% | 0.64 | 0.91 | 79% | 0.29 | 0 | 0 | 53579 | 11.0% | 0.83 | > 5% |
| Buy-and-hold (spot) | +583.9% | 0.82 | 1.17 | 77% | 0.48 | 0 | 0 | 53579 | 0.0% | 0.83 | > 5% |
| Momentum (daily 30-day, long/short) | +237.7% | 0.63 | 0.89 | 64% | 0.34 | 62 | 31 | 281 | 14.3% | 0.87 | 0.418% |
| Random agent (mean of 10) | -95.3% | -0.93 | -1.30 | 97% | -0.44 | 323 | 243 | 36 | 42.6% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +248.5% | 0.68 | 0.96 | 68% | 0.33 | 22 | 88 | 53579 | 11.9% | 0.95 | 1.036% |
| *reference: momentum through the Phase 3 risk manager* | +212.0% | 0.64 | 0.90 | 57% | 0.36 | 72 | 123 | 281 | 14.2% | 0.95 | 0.356% |

### BTCUSDT, 2020-10-01 .. 2026-11-11, 0.05% a side

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Phase 4 primary (Q, BTC+ETH pooled, expanding, readings) [primary], mean of 3 seeds** | **+105.9%** | **0.56** | **0.78** | **41%** | **0.31** | **47** | **107** | **162** | **6.0%** | **0.77** | **0.302%** |
| &nbsp;&nbsp;seed 0 | +120.5% | 0.59 | 0.82 | 39% | 0.35 | 52 | 121 | 130 | 6.7% | 0.82 | 0.297% |
| &nbsp;&nbsp;seed 1 | +86.8% | 0.50 | 0.69 | 44% | 0.24 | 39 | 93 | 234 | 5.2% | 0.68 | 0.311% |
| &nbsp;&nbsp;seed 2 | +110.4% | 0.59 | 0.83 | 38% | 0.34 | 49 | 107 | 123 | 6.1% | 0.82 | 0.297% |
| t1: wider no-trade band (2 round trips), mean of 3 seeds | +38.4% | 0.33 | 0.46 | 47% | 0.12 | 11 | 33 | 1000 | 2.9% | 0.43 | 0.583% |
| t2: minimum hold 2 days, mean of 3 seeds | +33.5% | 0.30 | 0.42 | 45% | 0.11 | 24 | 56 | 453 | 3.7% | 0.43 | 0.235% |
| t3: 1x spot core +- 0.5x agent tilt, mean of 3 seeds | +718.8% | 0.85 | 1.20 | 80% | 0.51 | 24 | 108 | 53579 | 3.7% | 0.91 | 1.522% |
| Buy-and-hold (perp) | +249.5% | 0.64 | 0.91 | 79% | 0.29 | 0 | 0 | 53579 | 11.0% | 0.83 | > 5% |
| Buy-and-hold (spot) | +584.3% | 0.83 | 1.17 | 77% | 0.48 | 0 | 0 | 53579 | 0.0% | 0.83 | > 5% |
| Momentum (daily 30-day, long/short) | +308.7% | 0.68 | 0.97 | 61% | 0.42 | 62 | 31 | 281 | 11.2% | 0.87 | 0.418% |
| Random agent (mean of 10) | -87.3% | -0.59 | -0.84 | 93% | -0.35 | 323 | 243 | 36 | 26.5% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +261.7% | 0.70 | 0.98 | 69% | 0.34 | 23 | 95 | 53579 | 11.0% | 0.94 | 0.951% |
| *reference: momentum through the Phase 3 risk manager* | +295.7% | 0.72 | 1.02 | 50% | 0.51 | 74 | 128 | 281 | 10.7% | 0.96 | 0.354% |

### BTCUSDT, up to 2025-11-11, 0.10% a side (with the loop's rules A and B)

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Phase 4 primary (Q, BTC+ETH pooled, expanding, readings) [primary], mean of 3 seeds** | **+122.1%** | **0.67** | **0.94** | **41%** | **0.41** | **52** | **118** | **149** | **9.4%** | **0.99** | **0.393%** |
| &nbsp;&nbsp;seed 0 | +134.2% | 0.69 | 0.97 | 40% | 0.45 | 59 | 133 | 120 | 10.5% | 1.04 | 0.384% |
| &nbsp;&nbsp;seed 1 | +79.8% | 0.53 | 0.74 | 45% | 0.27 | 43 | 101 | 215 | 8.0% | 0.80 | 0.366% |
| &nbsp;&nbsp;seed 2 | +152.3% | 0.79 | 1.12 | 38% | 0.52 | 55 | 119 | 112 | 9.7% | 1.14 | 0.429% |
| t1: wider no-trade band (2 round trips), mean of 3 seeds | +87.2% | 0.56 | 0.79 | 39% | 0.33 | 10 | 30 | 886 | 3.6% | 0.69 | 1.434% |
| t2: minimum hold 2 days, mean of 3 seeds | +49.2% | 0.41 | 0.58 | 45% | 0.18 | 26 | 58 | 430 | 5.4% | 0.60 | 0.399% |
| t3: 1x spot core +- 0.5x agent tilt, mean of 3 seeds | +1140.0% | 1.06 | 1.50 | 80% | 0.79 | 26 | 118 | 44808 | 5.5% | 1.14 | 1.989% |
| Buy-and-hold (perp) | +418.4% | 0.83 | 1.18 | 79% | 0.48 | 0 | 0 | 44808 | 12.5% | 1.03 | > 5% |
| Buy-and-hold (spot) | +879.7% | 1.03 | 1.46 | 77% | 0.73 | 0 | 0 | 44808 | 0.0% | 1.03 | > 5% |
| Momentum (daily 30-day, long/short) | +218.6% | 0.67 | 0.95 | 63% | 0.41 | 60 | 30 | 293 | 15.2% | 0.92 | 0.477% |
| Random agent (mean of 10) | -92.0% | -0.91 | -1.28 | 95% | -0.45 | 323 | 243 | 36 | 42.9% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +398.4% | 0.91 | 1.28 | 68% | 0.54 | 20 | 80 | 44808 | 12.8% | 1.19 | 1.697% |
| *reference: momentum through the Phase 3 risk manager* | +250.2% | 0.76 | 1.07 | 49% | 0.56 | 64 | 101 | 293 | 14.2% | 1.06 | 0.480% |
| A: loop H29 H30 1.5x/0x spot | +1809.3% | 1.19 | 1.69 | 65% | 1.20 | 45 | 30 | 328 | 10.8% | 1.35 | 1.379% |
| B: loop H29 H31 trail 4 ATR spot | +1301.3% | 1.32 | 1.88 | 53% | 1.28 | 46 | 53 | 315 | 7.6% | 1.48 | 1.223% |

### ETHUSDT, 2020-10-01 .. 2026-11-11, 0.10% a side

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Phase 4 primary (Q, BTC+ETH pooled, expanding, readings) [primary], mean of 3 seeds** | **+263.1%** | **0.77** | **1.07** | **50%** | **0.49** | **63** | **158** | **104** | **11.6%** | **1.11** | **0.419%** |
| &nbsp;&nbsp;seed 0 | +416.0% | 0.94 | 1.32 | 39% | 0.79 | 65 | 168 | 109 | 12.5% | 1.30 | 0.510% |
| &nbsp;&nbsp;seed 1 | +233.5% | 0.75 | 1.04 | 58% | 0.38 | 64 | 161 | 107 | 12.0% | 1.10 | 0.408% |
| &nbsp;&nbsp;seed 2 | +139.8% | 0.61 | 0.85 | 52% | 0.30 | 60 | 147 | 97 | 10.4% | 0.95 | 0.339% |
| t1: wider no-trade band (2 round trips), mean of 3 seeds | +189.4% | 0.66 | 0.92 | 54% | 0.36 | 15 | 49 | 499 | 4.2% | 0.79 | 1.217% |
| t2: minimum hold 2 days, mean of 3 seeds | +198.7% | 0.71 | 0.99 | 51% | 0.40 | 30 | 76 | 270 | 6.4% | 0.92 | 0.677% |
| t3: 1x spot core +- 0.5x agent tilt, mean of 3 seeds | +696.7% | 0.82 | 1.16 | 85% | 0.47 | 32 | 159 | 53556 | 6.6% | 0.90 | 1.167% |
| Buy-and-hold (perp) | +172.2% | 0.60 | 0.85 | 82% | 0.22 | 0 | 0 | 53556 | 12.1% | 0.76 | > 5% |
| Buy-and-hold (spot) | +470.6% | 0.76 | 1.07 | 81% | 0.40 | 0 | 0 | 53556 | 0.0% | 0.76 | > 5% |
| Momentum (daily 30-day, long/short) | +727.8% | 0.83 | 1.18 | 80% | 0.51 | 55 | 28 | 317 | 15.9% | 1.04 | 0.722% |
| Random agent (mean of 10) | -95.8% | -0.63 | -0.89 | 97% | -0.45 | 323 | 243 | 36 | 45.4% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +170.5% | 0.58 | 0.81 | 64% | 0.28 | 21 | 88 | 53556 | 11.7% | 0.82 | 0.867% |
| *reference: momentum through the Phase 3 risk manager* | +688.0% | 0.91 | 1.30 | 70% | 0.57 | 65 | 132 | 317 | 14.3% | 1.19 | 0.616% |

### ETHUSDT, 2020-10-01 .. 2026-11-11, 0.05% a side

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Phase 4 primary (Q, BTC+ETH pooled, expanding, readings) [primary], mean of 3 seeds** | **+341.1%** | **0.86** | **1.19** | **49%** | **0.56** | **63** | **157** | **104** | **8.5%** | **1.11** | **0.418%** |
| &nbsp;&nbsp;seed 0 | +542.3% | 1.04 | 1.46 | 41% | 0.88 | 63 | 158 | 109 | 9.1% | 1.30 | 0.529% |
| &nbsp;&nbsp;seed 1 | +302.5% | 0.84 | 1.16 | 57% | 0.45 | 64 | 161 | 107 | 8.8% | 1.09 | 0.403% |
| &nbsp;&nbsp;seed 2 | +178.3% | 0.69 | 0.96 | 51% | 0.36 | 61 | 153 | 97 | 7.6% | 0.93 | 0.322% |
| t1: wider no-trade band (2 round trips), mean of 3 seeds | +208.3% | 0.69 | 0.97 | 52% | 0.39 | 14 | 43 | 499 | 3.3% | 0.79 | 1.320% |
| t2: minimum hold 2 days, mean of 3 seeds | +232.8% | 0.77 | 1.07 | 50% | 0.45 | 30 | 74 | 270 | 4.9% | 0.92 | 0.695% |
| t3: 1x spot core +- 0.5x agent tilt, mean of 3 seeds | +775.7% | 0.84 | 1.19 | 85% | 0.50 | 32 | 157 | 53556 | 5.0% | 0.90 | 1.163% |
| Buy-and-hold (perp) | +172.4% | 0.60 | 0.85 | 82% | 0.22 | 0 | 0 | 53556 | 12.1% | 0.76 | > 5% |
| Buy-and-hold (spot) | +470.9% | 0.76 | 1.07 | 81% | 0.40 | 0 | 0 | 53556 | 0.0% | 0.76 | > 5% |
| Momentum (daily 30-day, long/short) | +880.0% | 0.87 | 1.23 | 79% | 0.57 | 55 | 28 | 317 | 13.2% | 1.04 | 0.722% |
| Random agent (mean of 10) | -88.7% | -0.38 | -0.53 | 93% | -0.36 | 323 | 243 | 36 | 29.3% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +176.6% | 0.58 | 0.82 | 63% | 0.29 | 24 | 98 | 53556 | 10.9% | 0.81 | 0.748% |
| *reference: momentum through the Phase 3 risk manager* | +879.8% | 0.98 | 1.40 | 68% | 0.67 | 71 | 155 | 317 | 11.5% | 1.20 | 0.573% |

### ETHUSDT, up to 2025-11-11, 0.10% a side

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Phase 4 primary (Q, BTC+ETH pooled, expanding, readings) [primary], mean of 3 seeds** | **+290.5%** | **0.86** | **1.20** | **50%** | **0.63** | **71** | **179** | **105** | **13.2%** | **1.23** | **0.447%** |
| &nbsp;&nbsp;seed 0 | +546.0% | 1.17 | 1.64 | 39% | 1.13 | 71 | 182 | 108 | 13.9% | 1.54 | 0.614% |
| &nbsp;&nbsp;seed 1 | +195.5% | 0.76 | 1.05 | 58% | 0.41 | 74 | 187 | 107 | 13.9% | 1.13 | 0.387% |
| &nbsp;&nbsp;seed 2 | +130.0% | 0.65 | 0.91 | 52% | 0.34 | 67 | 168 | 99 | 11.9% | 1.01 | 0.341% |
| t1: wider no-trade band (2 round trips), mean of 3 seeds | +162.6% | 0.68 | 0.96 | 54% | 0.40 | 18 | 57 | 483 | 4.9% | 0.83 | 1.174% |
| t2: minimum hold 2 days, mean of 3 seeds | +218.3% | 0.79 | 1.11 | 51% | 0.51 | 33 | 84 | 280 | 7.2% | 1.01 | 0.748% |
| t3: 1x spot core +- 0.5x agent tilt, mean of 3 seeds | +1329.1% | 1.02 | 1.44 | 85% | 0.80 | 36 | 179 | 44784 | 7.5% | 1.11 | 1.551% |
| Buy-and-hold (perp) | +383.7% | 0.79 | 1.11 | 82% | 0.44 | 0 | 0 | 44784 | 14.0% | 0.96 | > 5% |
| Buy-and-hold (spot) | +889.1% | 0.96 | 1.35 | 81% | 0.69 | 0 | 0 | 44784 | 0.0% | 0.96 | > 5% |
| Momentum (daily 30-day, long/short) | +447.8% | 0.82 | 1.15 | 80% | 0.49 | 53 | 27 | 327 | 17.4% | 1.03 | 0.718% |
| Random agent (mean of 10) | -93.7% | -0.62 | -0.88 | 96% | -0.47 | 322 | 242 | 36 | 45.8% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +347.2% | 0.83 | 1.17 | 63% | 0.54 | 16 | 69 | 44784 | 12.4% | 1.08 | 1.876% |
| *reference: momentum through the Phase 3 risk manager* | +505.7% | 0.93 | 1.33 | 70% | 0.60 | 62 | 126 | 327 | 14.9% | 1.22 | 0.669% |

### By seed (full span): Sharpe / net return / break-even fee

**BTCUSDT**

| Variant | seed 0 | seed 1 | seed 2 | mean, 0.10% | mean, 0.05% |
|---|---|---|---|---|---|
| Phase 4 primary (Q, BTC+ETH pooled, expanding, readings) | 0.52 / +94% / 0.302% (0.05%: 0.59) | 0.40 / +58% / 0.290% (0.05%: 0.50) | 0.51 / +84% / 0.302% (0.05%: 0.59) | 0.48 / +79% | 0.56 / +106% |
| t1: wider no-trade band (2 round trips) | 0.20 / +10% / 0.215% (0.05%: 0.26) | 0.36 / +46% / 0.898% (0.05%: 0.37) | 0.33 / +38% / 0.583% (0.05%: 0.36) | 0.30 / +31% | 0.33 / +38% |
| t2: minimum hold 2 days | 0.32 / +35% / 0.282% (0.05%: 0.37) | 0.33 / +37% / 0.310% (0.05%: 0.38) | 0.09 / -6% / 0.057% (0.05%: 0.14) | 0.24 / +22% | 0.30 / +33% |
| t3: 1x spot core +- 0.5x agent tilt | 0.84 / +692% / 1.350% (0.05%: 0.86) | 0.81 / +601% / 1.705% (0.05%: 0.83) | 0.84 / +694% / 1.459% (0.05%: 0.86) | 0.83 / +663% | 0.85 / +719% |

**ETHUSDT**

| Variant | seed 0 | seed 1 | seed 2 | mean, 0.10% | mean, 0.05% |
|---|---|---|---|---|---|
| Phase 4 primary (Q, BTC+ETH pooled, expanding, readings) | 0.94 / +416% / 0.510% (0.05%: 1.04) | 0.75 / +234% / 0.408% (0.05%: 0.84) | 0.61 / +140% / 0.339% (0.05%: 0.69) | 0.77 / +263% | 0.86 / +341% |
| t1: wider no-trade band (2 round trips) | 0.86 / +338% / 1.949% (0.05%: 0.88) | 0.49 / +93% / 0.734% (0.05%: 0.53) | 0.62 / +137% / 0.969% (0.05%: 0.66) | 0.66 / +189% | 0.69 / +208% |
| t2: minimum hold 2 days | 0.83 / +272% / 0.831% (0.05%: 0.89) | 0.76 / +219% / 0.717% (0.05%: 0.80) | 0.55 / +105% / 0.483% (0.05%: 0.61) | 0.71 / +199% | 0.77 / +233% |
| t3: 1x spot core +- 0.5x agent tilt | 0.85 / +828% / 1.208% (0.05%: 0.87) | 0.82 / +662% / 1.134% (0.05%: 0.83) | 0.80 / +601% / 1.159% (0.05%: 0.81) | 0.82 / +697% | 0.84 / +776% |

### Edge before costs

| Variant | Asset | Span | Gross Sharpe by seed | Mean | t (approx.) | Break-even fee by seed | Net Sharpe 0.10% (mean) |
|---|---|---|---|---|---|---|---|
| Phase 4 primary (Q, BTC+ETH pooled, expanding, readings) | BTCUSDT | 2020-10 .. 2026-11 | 0.84, 0.65, 0.84 | 0.78 | 1.9 | 0.302%, 0.290%, 0.302% | 0.48 |
| Phase 4 primary (Q, BTC+ETH pooled, expanding, readings) | BTCUSDT | to 2025-11-11 | 1.04, 0.80, 1.14 | 0.99 | 2.2 | 0.384%, 0.366%, 0.429% | 0.67 |
| Phase 4 primary (Q, BTC+ETH pooled, expanding, readings) | ETHUSDT | 2020-10 .. 2026-11 | 1.30, 1.10, 0.95 | 1.11 | 2.8 | 0.510%, 0.408%, 0.339% | 0.77 |
| Phase 4 primary (Q, BTC+ETH pooled, expanding, readings) | ETHUSDT | to 2025-11-11 | 1.54, 1.13, 1.01 | 1.23 | 2.8 | 0.614%, 0.387%, 0.341% | 0.86 |
| t1: wider no-trade band (2 round trips) | BTCUSDT | 2020-10 .. 2026-11 | 0.33, 0.48, 0.46 | 0.42 | 1.0 | 0.215%, 0.898%, 0.583% | 0.30 |
| t1: wider no-trade band (2 round trips) | BTCUSDT | to 2025-11-11 | 0.58, 0.73, 0.76 | 0.69 | 1.6 | 0.807%, 2.199%, 1.298% | 0.56 |
| t1: wider no-trade band (2 round trips) | ETHUSDT | 2020-10 .. 2026-11 | 0.99, 0.63, 0.74 | 0.79 | 1.9 | 1.949%, 0.734%, 0.969% | 0.66 |
| t1: wider no-trade band (2 round trips) | ETHUSDT | to 2025-11-11 | 1.04, 0.66, 0.77 | 0.83 | 1.9 | 1.910%, 0.683%, 0.930% | 0.68 |
| t2: minimum hold 2 days | BTCUSDT | 2020-10 .. 2026-11 | 0.51, 0.51, 0.27 | 0.43 | 1.1 | 0.282%, 0.310%, 0.057% | 0.24 |
| t2: minimum hold 2 days | BTCUSDT | to 2025-11-11 | 0.66, 0.64, 0.49 | 0.60 | 1.4 | 0.451%, 0.456%, 0.288% | 0.41 |
| t2: minimum hold 2 days | ETHUSDT | 2020-10 .. 2026-11 | 1.04, 0.97, 0.74 | 0.92 | 2.3 | 0.831%, 0.717%, 0.483% | 0.71 |
| t2: minimum hold 2 days | ETHUSDT | to 2025-11-11 | 1.29, 1.02, 0.72 | 1.01 | 2.3 | 1.106%, 0.705%, 0.431% | 0.79 |
| t3: 1x spot core +- 0.5x agent tilt | BTCUSDT | 2020-10 .. 2026-11 | 0.92, 0.87, 0.92 | 0.91 | 2.2 | 1.350%, 1.705%, 1.459% | 0.83 |
| t3: 1x spot core +- 0.5x agent tilt | BTCUSDT | to 2025-11-11 | 1.15, 1.09, 1.17 | 1.14 | 2.6 | 1.780%, 2.244%, 1.943% | 1.06 |
| t3: 1x spot core +- 0.5x agent tilt | ETHUSDT | 2020-10 .. 2026-11 | 0.94, 0.89, 0.87 | 0.90 | 2.2 | 1.208%, 1.134%, 1.159% | 0.82 |
| t3: 1x spot core +- 0.5x agent tilt | ETHUSDT | to 2025-11-11 | 1.17, 1.09, 1.07 | 1.11 | 2.5 | 1.699%, 1.428%, 1.528% | 1.02 |

t (approx.) = gross Sharpe x sqrt(years). For t3 the gross Sharpe includes the 1x spot core.

### Overfitting flags (Phase 4's)

**BTCUSDT**

| Variant | train_test_sharpe_gap | seed_dispersion | beats_benchmarks_in_under_half_the_folds | fee_sign_flip | edge_only_at_0.05 | high_turnover | degenerate_policy |
|---|---|---|---|---|---|---|---|
| Phase 4 primary (Q, BTC+ETH pooled, expanding, readings) | FIRED | - | FIRED | - | - | - | - |
| t1: wider no-trade band (2 round trips) | FIRED | - | FIRED | - | - | - | - |
| t2: minimum hold 2 days | FIRED | FIRED | FIRED | FIRED | - | - | - |
| t3: 1x spot core +- 0.5x agent tilt | FIRED | - | - | - | - | - | FIRED |

**ETHUSDT**

| Variant | train_test_sharpe_gap | seed_dispersion | beats_benchmarks_in_under_half_the_folds | fee_sign_flip | edge_only_at_0.05 | high_turnover | degenerate_policy |
|---|---|---|---|---|---|---|---|
| Phase 4 primary (Q, BTC+ETH pooled, expanding, readings) | FIRED | - | FIRED | - | - | - | - |
| t1: wider no-trade band (2 round trips) | FIRED | - | FIRED | - | - | - | - |
| t2: minimum hold 2 days | FIRED | - | FIRED | - | - | - | - |
| t3: 1x spot core +- 0.5x agent tilt | - | - | - | - | - | - | FIRED |

### Plain answer (part 2)

- t1: wider no-trade band (2 round trips): BTCUSDT gross 0.42 (primary 0.78), net 0.30 (primary 0.48), turnover 11 (47): keeps the edge no, trades less yes, beats B&H no, beats momentum no; ETHUSDT gross 0.79 (primary 1.11), net 0.66 (primary 0.77), turnover 15 (63): keeps the edge no, trades less yes, beats B&H no, beats momentum no
- t2: minimum hold 2 days: BTCUSDT gross 0.43 (primary 0.78), net 0.24 (primary 0.48), turnover 25 (47): keeps the edge no, trades less yes, beats B&H no, beats momentum no; ETHUSDT gross 0.92 (primary 1.11), net 0.71 (primary 0.77), turnover 30 (63): keeps the edge yes, trades less yes, beats B&H no, beats momentum no
- t3: 1x spot core +- 0.5x agent tilt: BTCUSDT gross 0.91 (primary 0.78), net 0.83 (primary 0.48), turnover 24 (47): keeps the edge yes, trades less yes, beats spot B&H no, beats momentum yes; ETHUSDT gross 0.90 (primary 1.11), net 0.82 (primary 0.77), turnover 32 (63): keeps the edge yes, trades less yes, beats spot B&H yes, beats momentum no

## Part 3: which readings carry the edge (registered; retrained per variant)

The Phase 4 primary setup retrained with one input set changed at a time (same folds, seeds, data, selection, refit, 'do no harm', risk manager). Gross = before every cost. Frozen rule: a group carries independent value if dropping it costs >= 0.20 gross Sharpe on BTC and on ETH.

| Variant | BTC gross Sharpe (vs primary) | BTC net 0.10% | ETH gross Sharpe (vs primary) | ETH net 0.10% | BTC turnover/yr | BTC gross to 2025-11-11 | ETH gross to 2025-11-11 |
|---|---|---|---|---|---|---|---|
| **Phase 4 primary (Q, BTC+ETH pooled, expanding, readings)** | **0.78** | **0.48** | **1.11** | **0.77** | **47** | **0.99** | **1.23** |
| ablation: Phase 3 inputs only | 0.42 (-0.36) | 0.13 | 0.56 (-0.55) | 0.24 | 37 | 0.52 | 0.64 |
| ablation: readings only | 0.62 (-0.15) | 0.39 | 0.88 (-0.24) | 0.63 | 19 | 0.86 | 1.14 |
| ablation: without trend readings | 0.79 (+0.01) | 0.49 | 0.98 (-0.13) | 0.65 | 47 | 1.01 | 1.09 |
| ablation: without funding readings | 0.83 (+0.05) | 0.50 | 0.92 (-0.19) | 0.54 | 49 | 0.88 | 1.01 |
| ablation: without basis readings | 0.82 (+0.04) | 0.54 | 0.99 (-0.13) | 0.67 | 41 | 0.93 | 1.24 |
| ablation: without flow / CVD / Coinbase readings | 0.78 (+0.01) | 0.48 | 0.61 (-0.50) | 0.29 | 43 | 0.95 | 0.75 |
| ablation: without volatility-regime readings | 0.91 (+0.14) | 0.57 | 0.99 (-0.13) | 0.63 | 54 | 0.99 | 1.09 |
| ablation: without levels readings | 0.85 (+0.08) | 0.58 | 1.07 (-0.05) | 0.72 | 41 | 0.93 | 1.25 |

### BTCUSDT, 2020-10-01 .. 2026-11-11, 0.10% a side

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Phase 4 primary (Q, BTC+ETH pooled, expanding, readings) [primary], mean of 3 seeds** | **+78.8%** | **0.48** | **0.67** | **41%** | **0.24** | **47** | **110** | **162** | **8.4%** | **0.78** | **0.298%** |
| &nbsp;&nbsp;seed 0 | +94.2% | 0.52 | 0.72 | 40% | 0.28 | 54 | 126 | 130 | 9.5% | 0.84 | 0.302% |
| &nbsp;&nbsp;seed 1 | +57.8% | 0.40 | 0.56 | 45% | 0.17 | 39 | 95 | 234 | 7.2% | 0.65 | 0.290% |
| &nbsp;&nbsp;seed 2 | +84.4% | 0.51 | 0.72 | 38% | 0.27 | 49 | 109 | 123 | 8.6% | 0.84 | 0.302% |
| ablation: Phase 3 inputs only, mean of 3 seeds | -1.3% | 0.13 | 0.18 | 50% | -0.00 | 37 | 94 | 193 | 8.0% | 0.42 | 0.094% |
| ablation: readings only, mean of 3 seeds | +60.9% | 0.39 | 0.56 | 40% | 0.20 | 19 | 56 | 746 | 6.7% | 0.62 | 0.468% |
| ablation: without trend readings, mean of 3 seeds | +89.9% | 0.49 | 0.69 | 46% | 0.25 | 47 | 109 | 156 | 8.5% | 0.79 | 0.311% |
| ablation: without funding readings, mean of 3 seeds | +89.8% | 0.50 | 0.70 | 44% | 0.25 | 49 | 116 | 123 | 8.9% | 0.83 | 0.306% |
| ablation: without basis readings, mean of 3 seeds | +92.7% | 0.54 | 0.75 | 37% | 0.31 | 41 | 99 | 155 | 7.3% | 0.82 | 0.356% |
| ablation: without flow / CVD / Coinbase readings, mean of 3 seeds | +79.6% | 0.48 | 0.67 | 43% | 0.23 | 43 | 108 | 153 | 8.3% | 0.78 | 0.315% |
| ablation: without volatility-regime readings, mean of 3 seeds | +149.6% | 0.57 | 0.81 | 42% | 0.39 | 54 | 126 | 123 | 9.6% | 0.91 | 0.334% |
| ablation: without levels readings, mean of 3 seeds | +119.7% | 0.58 | 0.81 | 42% | 0.32 | 41 | 99 | 167 | 7.5% | 0.85 | 0.401% |
| Buy-and-hold (perp) | +249.3% | 0.64 | 0.91 | 79% | 0.29 | 0 | 0 | 53579 | 11.0% | 0.83 | > 5% |
| Buy-and-hold (spot) | +583.9% | 0.82 | 1.17 | 77% | 0.48 | 0 | 0 | 53579 | 0.0% | 0.83 | > 5% |
| Momentum (daily 30-day, long/short) | +237.7% | 0.63 | 0.89 | 64% | 0.34 | 62 | 31 | 281 | 14.3% | 0.87 | 0.418% |
| Random agent (mean of 10) | -95.3% | -0.93 | -1.30 | 97% | -0.44 | 323 | 243 | 36 | 42.6% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +248.5% | 0.68 | 0.96 | 68% | 0.33 | 22 | 88 | 53579 | 11.9% | 0.95 | 1.036% |
| *reference: momentum through the Phase 3 risk manager* | +212.0% | 0.64 | 0.90 | 57% | 0.36 | 72 | 123 | 281 | 14.2% | 0.95 | 0.356% |

### ETHUSDT, 2020-10-01 .. 2026-11-11, 0.10% a side

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Phase 4 primary (Q, BTC+ETH pooled, expanding, readings) [primary], mean of 3 seeds** | **+263.1%** | **0.77** | **1.07** | **50%** | **0.49** | **63** | **158** | **104** | **11.6%** | **1.11** | **0.419%** |
| &nbsp;&nbsp;seed 0 | +416.0% | 0.94 | 1.32 | 39% | 0.79 | 65 | 168 | 109 | 12.5% | 1.30 | 0.510% |
| &nbsp;&nbsp;seed 1 | +233.5% | 0.75 | 1.04 | 58% | 0.38 | 64 | 161 | 107 | 12.0% | 1.10 | 0.408% |
| &nbsp;&nbsp;seed 2 | +139.8% | 0.61 | 0.85 | 52% | 0.30 | 60 | 147 | 97 | 10.4% | 0.95 | 0.339% |
| ablation: Phase 3 inputs only, mean of 3 seeds | +22.4% | 0.24 | 0.33 | 75% | 0.04 | 46 | 137 | 123 | 10.1% | 0.56 | 0.160% |
| ablation: readings only, mean of 3 seeds | +170.8% | 0.63 | 0.88 | 52% | 0.35 | 24 | 69 | 685 | 8.9% | 0.88 | 0.797% |
| ablation: without trend readings, mean of 3 seeds | +204.0% | 0.65 | 0.91 | 51% | 0.38 | 58 | 152 | 113 | 11.3% | 0.98 | 0.386% |
| ablation: without funding readings, mean of 3 seeds | +123.9% | 0.54 | 0.75 | 61% | 0.23 | 67 | 172 | 86 | 12.9% | 0.92 | 0.290% |
| ablation: without basis readings, mean of 3 seeds | +198.7% | 0.67 | 0.93 | 50% | 0.37 | 56 | 150 | 136 | 10.7% | 0.99 | 0.401% |
| ablation: without flow / CVD / Coinbase readings, mean of 3 seeds | +37.1% | 0.29 | 0.40 | 73% | 0.06 | 53 | 150 | 110 | 10.5% | 0.61 | 0.170% |
| ablation: without volatility-regime readings, mean of 3 seeds | +183.0% | 0.63 | 0.88 | 50% | 0.38 | 61 | 157 | 102 | 11.6% | 0.99 | 0.350% |
| ablation: without levels readings, mean of 3 seeds | +221.2% | 0.72 | 1.00 | 50% | 0.42 | 64 | 165 | 113 | 12.1% | 1.07 | 0.391% |
| Buy-and-hold (perp) | +172.2% | 0.60 | 0.85 | 82% | 0.22 | 0 | 0 | 53556 | 12.1% | 0.76 | > 5% |
| Buy-and-hold (spot) | +470.6% | 0.76 | 1.07 | 81% | 0.40 | 0 | 0 | 53556 | 0.0% | 0.76 | > 5% |
| Momentum (daily 30-day, long/short) | +727.8% | 0.83 | 1.18 | 80% | 0.51 | 55 | 28 | 317 | 15.9% | 1.04 | 0.722% |
| Random agent (mean of 10) | -95.8% | -0.63 | -0.89 | 97% | -0.45 | 323 | 243 | 36 | 45.4% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +170.5% | 0.58 | 0.81 | 64% | 0.28 | 21 | 88 | 53556 | 11.7% | 0.82 | 0.867% |
| *reference: momentum through the Phase 3 risk manager* | +688.0% | 0.91 | 1.30 | 70% | 0.57 | 65 | 132 | 317 | 14.3% | 1.19 | 0.616% |

### Flags (ablations)

**BTCUSDT**

| Variant | train_test_sharpe_gap | seed_dispersion | beats_benchmarks_in_under_half_the_folds | fee_sign_flip | edge_only_at_0.05 | high_turnover | degenerate_policy |
|---|---|---|---|---|---|---|---|
| Phase 4 primary (Q, BTC+ETH pooled, expanding, readings) | FIRED | - | FIRED | - | - | - | - |
| ablation: Phase 3 inputs only | FIRED | FIRED | FIRED | FIRED | FIRED | - | - |
| ablation: readings only | - | - | FIRED | - | - | - | - |
| ablation: without trend readings | FIRED | - | FIRED | - | - | - | - |
| ablation: without funding readings | FIRED | - | FIRED | - | - | - | - |
| ablation: without basis readings | FIRED | - | FIRED | - | - | - | - |
| ablation: without flow / CVD / Coinbase readings | FIRED | - | FIRED | - | - | - | - |
| ablation: without volatility-regime readings | FIRED | FIRED | FIRED | - | FIRED | - | - |
| ablation: without levels readings | FIRED | - | FIRED | - | FIRED | - | - |

**ETHUSDT**

| Variant | train_test_sharpe_gap | seed_dispersion | beats_benchmarks_in_under_half_the_folds | fee_sign_flip | edge_only_at_0.05 | high_turnover | degenerate_policy |
|---|---|---|---|---|---|---|---|
| Phase 4 primary (Q, BTC+ETH pooled, expanding, readings) | FIRED | - | FIRED | - | - | - | - |
| ablation: Phase 3 inputs only | FIRED | FIRED | FIRED | FIRED | - | - | - |
| ablation: readings only | - | - | FIRED | - | - | - | - |
| ablation: without trend readings | FIRED | - | FIRED | - | - | - | - |
| ablation: without funding readings | FIRED | - | FIRED | - | FIRED | - | - |
| ablation: without basis readings | FIRED | - | FIRED | - | - | - | - |
| ablation: without flow / CVD / Coinbase readings | FIRED | FIRED | FIRED | FIRED | - | - | - |
| ablation: without volatility-regime readings | FIRED | - | FIRED | - | - | - | - |
| ablation: without levels readings | FIRED | - | FIRED | - | - | - | - |

### Occlusion (supplementary, no retraining)

What the TRAINED primary leans on: each group's inputs set to 0 ('nothing to add') in its stored values; a retrained agent may recover some of it from other inputs.

| Group set to 0 in the trained primary | BTC gross Sharpe (vs primary) | ETH gross Sharpe (vs primary) |
|---|---|---|
| trend | 1.05 (+0.27) | 1.20 (+0.08) |
| funding / positioning | 0.65 (-0.12) | 1.05 (-0.06) |
| basis | 0.54 (-0.24) | 1.01 (-0.11) |
| flow / CVD / Coinbase | 0.59 (-0.19) | 0.67 (-0.44) |
| volatility regime | 0.62 (-0.16) | 0.78 (-0.34) |
| levels | 0.74 (-0.03) | 0.65 (-0.47) |

### Correlation with the momentum rule and the loop's rule A

| Asset | Span | Position vs momentum | Same side as momentum (when in) | Daily return vs momentum | Daily return vs buy-and-hold | Position vs rule A | Daily return vs rule A | Long / short share |
|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 2020-10 .. 2026-11 | +0.02 | 54% | +0.01 | +0.47 | (not shown: sealed) | (not shown: sealed) | 57% / 10% |
| BTCUSDT | to 2025-11-11 | +0.04 | 56% | +0.05 | +0.45 | +0.04 | +0.36 | 62% / 11% |
| ETHUSDT | 2020-10 .. 2026-11 | +0.09 | 55% | +0.14 | +0.47 | (not shown: sealed) | (not shown: sealed) | 56% / 13% |
| ETHUSDT | to 2025-11-11 | +0.10 | 56% | +0.16 | +0.49 | +0.10 | +0.42 | 62% / 13% |

Position = the agent's executed position (mean of seeds, after the risk manager) vs the rule's target, per 15m bar; daily = correlation of daily net returns. Rule A only up to 2025-11-11.

### Plain answer

Correlation of the agent's position with the daily momentum rule's: BTC +0.02, ETH +0.09 (full span); daily net returns: BTC +0.01, ETH +0.14; with buy-and-hold's daily returns: BTC +0.47, ETH +0.47. With the loop's rule A (to 2025-11-11 only): position BTC +0.04, ETH +0.10; daily returns BTC +0.36, ETH +0.42. Together the readings carry most of the edge: Phase 3 inputs alone give gross Sharpe BTC 0.42, ETH 0.56 (primary 0.78, 1.11); the readings alone keep BTC 0.62, ETH 0.88. Mostly trend-following by the frozen rule: NO (the rule: position correlation with momentum >= 0.5, or the trend readings the only group that clears the 0.20 bar). No single reading group clears the frozen bar (dropping it, retrained, costs >= 0.20 gross Sharpe on BTC and on ETH).

## What was frozen, and when

- 12 Nov 2026, ~04:10 UTC (before this file): Phase 4's fold-24 model rebuilt with the Phase 5 export hook (models4.q_fold(export=...)): the stored test values match Phase 4's file bit for bit (max difference 0.0), so a model the forward run trains is the Phase 4 primary's model, exactly. No Phase 5 result existed.
- 12 Nov 2026, ~04:12 UTC: this file written with every value of parts 1-3 and frozen before any Phase 5 number
- 12 Nov 2026, 04:16-04:19 UTC: the fold-24 rebuild for seeds 1 and 2 (also exact) and the first live model (models5/live/model_20261112T041605Z.json, data end 2026-11-12 04:00 UTC; 'do no harm' keeps seed 0 flat on both coins, seeds 1 and 2 trade) trained by forward5.train_model; no Part 2 / Part 3 number existed
- 12 Nov 2026, ~04:20 UTC: part 3 ablation training started (phase5-ablate, frozen variants in the frozen order)
- 12 Nov 2026, ~04:25 UTC: forward == batch check on Phase 4's fold 24 (2026-10-20 .. 2026-11-11, BTC and ETH, 4,316 bars, 5 cut calls): decisions identical, executed positions and values identical (difference 0.0) (research/out/rl/phase5_forward_check.json); go-live set: engine15/playbook5.py REGISTERED = 2026-11-12 04:30 UTC (a first fix before go-live: the bar-file tail reader built its index from a Series; no decision was recorded before)
- Ablation training: 347 min, memory pauses: none
- Evaluation: 4 min, memory pauses: none

Machine-readable: `phase5_summary.json`. Nothing here changes the live engine except the forward paper book (engine15/playbook5.py), which the owner reviews before the loop is restarted.
