# RL Phase 2 report: PPO agent, walk-forward, out of sample after costs

Run `phase2_20261111T130110Z_8bc5b963`, generated 2026-11-11 13:30 UTC. BTCUSDT perpetual (Binance USD-M), 15-minute bars. Paper only: no orders, no keys. Out of sample = 25 stitched 3-month test windows, 2020-10-01 to 2026-11-11. Seeds [0, 1, 2, 3, 4], 100000 PPO steps per fold and seed, run time 29 min.

## Verdict

NO. Out of sample, after 0.10% fees, the PPO agent does not beat buy-and-hold on a risk-adjusted basis across seeds: its seed-mean Sharpe -1.92 is not above buy-and-hold's 0.64; only 0 of 5 seeds beat buy-and-hold's Sharpe; its Calmar -0.60 is not above buy-and-hold's 0.29. Net return: agent -100% on average over 5 seeds vs buy-and-hold +249% (max drawdown 100% vs 79%). Against the daily 30-day momentum rule (Sharpe 0.63, Calmar 0.34) the agent is not better on both.

## Headline: stitched out of sample, 0.10% a side (the owner's rule)

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Avg hold (h) | Cost drag/yr |
|---|---|---|---|---|---|---|---|---|
| **PPO agent, mean of 5 seeds** | **-99.6%** | **-1.92** | **-2.70** | **100%** | **-0.60** | **601** | **17** | **79.3%** |
| agent sd across seeds | 0.1% | 0.13 | 0.18 | 0% | 0.02 | 26 | 1 | 3.3% |
| agent seed 0 | -99.6% | -1.78 | -2.53 | 100% | -0.60 | 594 | 18 | 78.8% |
| agent seed 1 | -99.5% | -1.81 | -2.56 | 100% | -0.58 | 600 | 17 | 77.6% |
| agent seed 2 | -99.7% | -2.01 | -2.77 | 100% | -0.62 | 563 | 18 | 75.1% |
| agent seed 3 | -99.7% | -2.10 | -2.97 | 100% | -0.61 | 629 | 16 | 83.1% |
| agent seed 4 | -99.6% | -1.90 | -2.66 | 100% | -0.60 | 620 | 18 | 82.1% |
| Buy-and-hold | +249.3% | 0.64 | 0.91 | 79% | 0.29 | 0 | 53579 | 11.0% |
| Momentum (daily, 30-day sign, long/short) | +237.7% | 0.63 | 0.89 | 64% | 0.34 | 62 | 281 | 14.3% |
| Random agent (mean of 10) | -95.3% | -0.93 | -1.30 | 97% | -0.44 | 323 | 36 | 42.6% |
| *reference: buy-and-hold through the risk manager* | -20.4% | 0.18 | 0.25 | 82% | -0.04 | 59 | 322 | 19.2% |

## Same, 0.05% a side (Binance USDT-M taker)

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Avg hold (h) | Cost drag/yr |
|---|---|---|---|---|---|---|---|---|
| **PPO agent, mean of 5 seeds** | **-97.5%** | **-1.20** | **-1.69** | **98%** | **-0.47** | **608** | **17** | **49.8%** |
| agent sd across seeds | 0.9% | 0.19 | 0.25 | 1% | 0.03 | 26 | 1 | 2.0% |
| agent seed 0 | -96.6% | -1.00 | -1.42 | 97% | -0.44 | 604 | 19 | 49.7% |
| agent seed 1 | -97.1% | -1.13 | -1.61 | 98% | -0.45 | 609 | 17 | 48.5% |
| agent seed 2 | -98.6% | -1.37 | -1.90 | 99% | -0.51 | 565 | 18 | 47.3% |
| agent seed 3 | -98.3% | -1.43 | -2.00 | 98% | -0.50 | 630 | 16 | 51.5% |
| agent seed 4 | -96.7% | -1.06 | -1.50 | 98% | -0.44 | 630 | 18 | 51.9% |
| Buy-and-hold | +249.5% | 0.64 | 0.91 | 79% | 0.29 | 0 | 53579 | 11.0% |
| Momentum (daily, 30-day sign, long/short) | +308.7% | 0.68 | 0.97 | 61% | 0.42 | 62 | 281 | 11.2% |
| Random agent (mean of 10) | -87.3% | -0.59 | -0.84 | 93% | -0.35 | 323 | 36 | 26.5% |
| *reference: buy-and-hold through the risk manager* | -19.8% | 0.18 | 0.25 | 80% | -0.04 | 60 | 320 | 16.3% |

Every number is out of sample and after costs (fee, half-spread, vol-scaled slippage, funding). The agent's test windows were each touched once, by a model trained only on the 12 months before. The risk manager is part of the agent's execution; the benchmarks run without it, and the reference row shows what the risk manager alone does to buy-and-hold.

## Overfitting flags

- **train_test_sharpe_gap: FIRED.** mean over folds and seeds: train-slice Sharpe -1.27, validation -0.39, test -2.32; train - test = 1.05 (threshold 1.0); validation - test = 1.93.
- **seed_dispersion: not fired.** stitched Sharpe by seed -1.78, -1.81, -2.01, -2.10, -1.90 (sd 0.13, threshold 0.50); stitched return by seed -100%, -99%, -100%, -100%, -100%; seeds disagree on the sign of a fold's return in 48% of folds.
- **beats_benchmarks_in_under_half_the_folds: FIRED.** agent seed mean per fold vs buy-and-hold: Sharpe higher in 3 of 25 folds (12%), return higher in 6 (24%); momentum: Sharpe higher in 2 of 25 folds (8%), return higher in 6 (24%); random (mean): Sharpe higher in 3 of 25 folds (12%), return higher in 4 (16%) (flag if any Sharpe share < 50%).
- **fee_sign_flip: not fired.** no seed (nor the mean) changes sign between fee_0.10% and fee_0.05%, and the comparison with buy-and-hold does not flip.
- **high_turnover: FIRED.** turnover per year by seed 594, 600, 563, 629, 620 (threshold 100); trading costs excluding funding 78.4%, 78.9%, 74.4%, 82.7%, 81.7% a year.
- **degenerate_policy: not fired.** share of out-of-sample bars long / flat / short by seed: s0 30/38/32%; s1 26/42/32%; s2 30/43/28%; s3 25/45/31%; s4 35/38/28% (flag if a seed is long > 90% of the time, a buy-and-hold clone, or flat > 95%).

## Reading the numbers (0.10%)

- **No edge before costs.** The agent's gross (pre-cost) return averages -52% over the span; gross Sharpe by seed -0.03, 0.01, -0.28, -0.08, 0.00. Before any fee it is about as good as a coin.
- **Costs then finish it.** About 503 trades a year: fees 60% and spread + slippage 19% of equity a year. The turnover penalty and the 12-hour minimum hold did not stop the churn: the policy asked for a change the minimum hold refused 16530 times per seed out of sample.
- **PPO did not even fit its own training data.** Mean Sharpe on the training slice (the data it learned on) -1.27, positive in 18% of the 125 fold-seed trainings; validation kept the very first checkpoint in 44% of them. With hourly decisions on 9 months of 15m data, the reward is mostly noise and costs.
- **The frozen risk limits are costly on their own.** Buy-and-hold through the same risk manager makes -20% (Sharpe 0.18 vs 0.64 without it): the 30% kill switch fired 14 times and the 5% daily-loss stop 142 times, each time selling into a fall and missing the rebound. That handicap applies to the agent too. It is a finding about the limits, not the main reason: the agent has no edge before costs, and even buy-and-hold under these limits (Sharpe 0.18) is far ahead of it.

## What was frozen, and when

- 11 Nov 2026, before any RL code was run: the momentum benchmark (daily at the 00:00 UTC bar close, fill next open, sign of the 30-day return, long/short), recorded in `configs/rl/phase1.yaml` and `docs/RL.md`; Phase 1 benchmarks were re-run with it.
- 11 Nov 2026 about 12:55 UTC, before any agent was trained or evaluated on any window: every value in `configs/rl/phase2.yaml` (features, action set, decision schedule, minimum hold, reward and turnover penalty, risk limits, PPO hyperparameters, training budget, validation rule, seeds, overfitting-flag thresholds). Only speed and memory were measured first (an 8,192-step smoke run) to size the budget.
- Model choice inside each fold used only the validation slice (last 3 months of the train window). No test number fed back into any choice; nothing was re-run after the test results were seen.

## Design (fixed before testing)

- Observation at a decision bar: the 18 point-in-time features of that bar (z-scored with the fold's training-slice mean/sd, clipped at +-5) + current target, time in position, risk-restriction flag.
- Action: target position in [-1.0, 0.0, 1.0], decided at the close of each 4-th bar (each UTC hour), filled at the next open. Minimum hold 48 bars (12 h) between changes; risk exits are never held back.
- Reward: 100 x (sum of per-bar log(1 + net return) - 0.0005 x |target change|); net return uses the shared cost model (`costs.py`), the same arrays as the backtester (env and backtest P&L agree to 0.0e+00 per bar on the real run).
- Risk manager (training and evaluation): max position 1.0; daily loss 5% -> flat for the rest of the UTC day; drawdown kill switch 30% from peak -> flat 672 bars, then peak reset; vol breaker rv_16 > 3.0 x rv_672 -> |position| <= 0.5. Every block/resize is logged (`phase2_risk_log.csv`).
- PPO (Stable-Baselines3): MLP [64, 64] (tanh) for policy and value, lr 0.0003, 4 envs x 512 steps, batch 256, 5 epochs, gamma 0.99, GAE 0.95, clip 0.2, entropy 0.010; CPU, 2 torch threads, below-normal priority. Training episodes: 720 hourly decisions from a random start in the training slice.
- Per fold: train on the first 9 months of the 12-month window, check the policy on the last 3 months 5 times during training, keep the best validation Sharpe (early stop after 2 checks without improvement), then run it once on the next 3 months. Out of sample, one simulation runs across all test windows (position and risk state carry over) and the executed target series is replayed through the Phase 1 backtester.

## Per fold, 0.10% a side

| # | Test window | Agent net, mean (min..max of seeds) | Agent Sharpe | Train Sharpe | Val Sharpe | B&H net | B&H Sharpe | Mom net | Mom Sharpe |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 2020-10-01 .. 2021-01-01 | -5.4% (-47% .. +37%) | -0.67 | -0.96 | -0.27 | +155.6% | 6.04 | +168.0% | 6.33 |
| 1 | 2021-01-01 .. 2021-04-01 | -34.7% (-56% .. -19%) | -2.06 | -0.56 | 1.10 | +72.4% | 2.49 | +34.9% | 1.63 |
| 2 | 2021-04-01 .. 2021-07-01 | -14.0% (-45% .. +11%) | -0.80 | 0.43 | -0.65 | -44.4% | -1.68 | -21.2% | -0.36 |
| 3 | 2021-07-01 .. 2021-10-01 | -35.5% (-49% .. -25%) | -3.39 | -0.29 | 1.15 | +22.4% | 1.54 | +13.6% | 1.09 |
| 4 | 2021-10-01 .. 2022-01-01 | +3.3% (-25% .. +31%) | 0.14 | -0.20 | 1.51 | +0.3% | 0.35 | +1.7% | 0.43 |
| 5 | 2022-01-01 .. 2022-04-01 | -20.1% (-46% .. -4%) | -1.90 | -1.53 | 0.29 | -2.8% | 0.16 | -31.9% | -2.03 |
| 6 | 2022-04-01 .. 2022-07-01 | -15.3% (-30% .. +4%) | -1.14 | -1.20 | 1.15 | -56.6% | -4.00 | +40.9% | 2.18 |
| 7 | 2022-07-01 .. 2022-10-01 | -15.3% (-29% .. +14%) | -1.37 | -0.58 | 1.08 | -3.7% | 0.07 | +2.4% | 0.46 |
| 8 | 2022-10-01 .. 2023-01-01 | -20.3% (-31% .. -13%) | -2.59 | -0.42 | 0.27 | -15.5% | -1.16 | -27.6% | -2.45 |
| 9 | 2023-01-01 .. 2023-04-01 | -15.9% (-39% .. +18%) | -2.17 | -0.42 | -1.13 | +68.6% | 4.31 | +52.3% | 3.52 |
| 10 | 2023-04-01 .. 2023-07-01 | -24.9% (-37% .. -10%) | -3.55 | -2.21 | 0.23 | +5.4% | 0.72 | -3.5% | -0.14 |
| 11 | 2023-07-01 .. 2023-10-01 | -18.5% (-26% .. -13%) | -3.84 | -2.30 | -0.49 | -12.6% | -1.24 | +9.5% | 1.15 |
| 12 | 2023-10-01 .. 2024-01-01 | -16.9% (-44% .. -8%) | -2.47 | -1.18 | -3.15 | +52.2% | 3.97 | +51.8% | 3.95 |
| 13 | 2024-01-01 .. 2024-04-01 | -20.2% (-35% .. -6%) | -2.24 | -1.28 | -0.13 | +59.5% | 3.52 | +1.6% | 0.40 |
| 14 | 2024-04-01 .. 2024-07-01 | -15.5% (-35% .. -3%) | -1.74 | -2.71 | -0.31 | -14.0% | -1.01 | +3.3% | 0.51 |
| 15 | 2024-07-01 .. 2024-10-01 | -26.9% (-41% .. +3%) | -3.32 | -1.37 | -0.90 | -0.0% | 0.27 | -51.4% | -4.94 |
| 16 | 2024-10-01 .. 2025-01-01 | -17.0% (-34% .. +6%) | -2.09 | -1.37 | 0.02 | +43.1% | 3.06 | +40.1% | 2.89 |
| 17 | 2025-01-01 .. 2025-04-01 | -23.2% (-37% .. -11%) | -2.65 | -1.17 | -2.45 | -12.9% | -0.74 | -22.9% | -1.63 |
| 18 | 2025-04-01 .. 2025-07-01 | -6.9% (-38% .. +9%) | -0.96 | -1.03 | 0.01 | +28.6% | 2.64 | -1.2% | 0.09 |
| 19 | 2025-07-01 .. 2025-10-01 | -23.8% (-30% .. -13%) | -4.51 | -1.95 | -1.38 | +4.6% | 0.74 | +2.6% | 0.48 |
| 20 | 2025-10-01 .. 2026-01-01 | -21.4% (-37% .. +1%) | -2.53 | -1.40 | -1.66 | -24.0% | -2.07 | +15.1% | 1.42 |
| 21 | 2026-01-01 .. 2026-04-01 | -16.4% (-26% .. -6%) | -1.66 | -1.87 | -0.92 | -22.3% | -1.60 | -22.7% | -1.63 |
| 22 | 2026-04-01 .. 2026-07-01 | -24.6% (-50% .. +1%) | -3.79 | -2.55 | -0.73 | -14.3% | -1.29 | +19.1% | 1.89 |
| 23 | 2026-07-01 .. 2026-10-01 | -25.4% (-38% .. -12%) | -4.69 | -2.20 | -0.17 | +40.3% | 4.05 | -12.0% | -1.29 |
| 24 | 2026-10-01 .. 2026-11-11 | -7.4% (-18% .. +1%) | -2.02 | -1.43 | -2.33 | -12.1% | -3.12 | +13.4% | 3.39 |

## Behaviour out of sample (0.10%)

| Seed | Long / flat / short (share of bars) | Trades/yr | Min-hold refusals | Risk: vol breaker | daily-loss blocks (triggers) | kill-switch blocks (triggers) | forced flats |
|---|---|---|---|---|---|---|---|
| 0 | 30% / 38% / 32% | 497 | 16225 | 50 | 133 (102) | 2311 (22) | 94 |
| 1 | 26% / 42% / 32% | 513 | 17031 | 47 | 117 (88) | 1619 (19) | 79 |
| 2 | 30% / 43% / 28% | 474 | 15731 | 50 | 180 (85) | 2261 (21) | 86 |
| 3 | 25% / 45% / 31% | 521 | 17231 | 45 | 89 (89) | 1640 (20) | 81 |
| 4 | 35% / 38% / 28% | 510 | 16431 | 39 | 132 (91) | 2457 (21) | 81 |
| B&H + risk manager | - | 70 | - | 63 | 281 (142) | 2189 (14) | 119 |

## Training

- 125 fold-seed trainings; PPO steps run 61440..102400 (early stopping), mean 13 s each; kept checkpoint: check 1 x55, check 2 x17, check 3 x24, check 4 x17, check 5 x12.
- Models: `C:\Ai Dataset\engine-15m\research/out/rl/models\9ae64989` (one ~20 KB .npz per fold and seed: actor weights + the fold's normaliser).
- Real-data look-ahead check of the Phase 2 feature set at 3 random cuts: {'59009': [], '126356': [], '248128': []}.
- Memory: every fold started with >= 700 MB free; the guard stops training under 350 MB. Waits and stops in this run (the owner's history replay ran alongside): seed 0 fold 10 at 13:07:38 UTC: training stopped (free memory 332 MB < floor during training); fold restarts after a wait; seed 0 fold 10 at 13:07:58 UTC: waited 20 s for 700 MB free before starting; seed 2 fold 10 at 13:16:33 UTC: training stopped (free memory 117 MB < floor during training); fold restarts after a wait; seed 2 fold 10 at 13:17:13 UTC: waited 40 s for 700 MB free before starting; seed 2 fold 10 at 13:17:54 UTC: training stopped (free memory 291 MB < floor during training); fold restarts after a wait; seed 2 fold 10 at 13:18:15 UTC: waited 20 s for 700 MB free before starting.

## Not done here (Phase 3, not started)

- Robustness: more seeds, cost stress, regime splits, ETH, decision-interval and penalty sensitivity reported as such (new experiments, never re-tuning on these test windows).

Machine-readable: `phase2_summary.json` (per fold and overall, every strategy, both fees, flags, verdict).
