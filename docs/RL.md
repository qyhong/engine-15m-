# RL module (engine15/rl): Phases 1, 2, 3 and 4

Paper only. Public market data, no API keys, no orders. Market: BTCUSDT perpetual (Binance
USD-M), 15-minute bars, Sept 2019 to now. Phase 1 builds the ground an agent will stand on:
data, point-in-time features, one cost model, a backtester, benchmarks, metrics and a
walk-forward splitter. Phase 2 (below) adds a Gymnasium trading environment, a risk manager and a PPO
agent trained per walk-forward fold, judged out of sample against the benchmarks.

## How to run

    py -3 -m engine15.rl phase1              data update -> features -> benchmarks -> walk-forward report
    py -3 -m engine15.rl phase1 --offline    stored data only (no network)
    py -3 -m engine15.rl data                data update only
    py -3 -m engine15.rl phase2 [--offline] [--seeds N] [--timesteps N] [--fresh]
                                             PPO per fold, seeds one after another -> phase2_report.md
    py -3 -m engine15.rl phase3 [--offline] [--seeds N] [--assets BTCUSDT,ETHUSDT] [--fresh]
                                             Phase 3 (below): continual 15m agent, every frozen variant -> phase3_report.md
    py -3 -m engine15.rl phase3-learn | phase3-power | phase3-cadence | phase3-risk | phase3-diag2
                                             Phase 3's pre-freeze steps and the Phase 2 filter diagnostic
    py -3 -m engine15.rl phase4-learn        Phase 4 learnability at the new data sizes (synthetic; before the freeze)
    py -3 -m engine15.rl phase4-check [--offline]   Phase 4 input caches + no-look-ahead truncation test of every input
    py -3 -m engine15.rl phase4 [--offline] [--fresh]
                                             Phase 4 (below): more data per model, the frozen walk-forward -> phase4_report.md
    py -3 -m engine15.rl phase4-report       rebuild the Phase 4 report from the latest run (formatting only)
    py -3 -m engine15.rl paper [--asset BTCUSDT] [--dry-run-from DATE --dry-run-to DATE]
                                             forward paper mode (design + dry run; not wired into the live engine)
    py -3 -m pytest tests/rl -q              the module's tests (planted data, no network)

Config: `configs/rl/phase1.yaml`. Output: `research/out/rl/phase1_report.md` and `.json`; each
run also writes `research/out/rl/runs/<run_id>/` with the resolved `config.yaml`, a
`manifest.json` (run id, UTC start time, config hash, seed, Python, platform) and the report.
The run id is git-free: `phase1_<UTC timestamp>_<config hash>`.

## Files

| File | What |
|---|---|
| `engine15/rl/store.py` | the only module that knows the disk format (`.csv.gz`) |
| `engine15/rl/data.py` | perp klines (`fapi/v1/klines`), funding (`fapi/v1/fundingRate`), open interest (`futures/data/openInterestHist`, live only); cleaning and gap report |
| `engine15/rl/features.py` | point-in-time features + `lookahead_report` (the truncation check) |
| `engine15/rl/costs.py` | THE cost model (fee, half-spread, vol-scaled slippage, funding, execution delay) |
| `engine15/rl/backtest.py` | vectorised backtester for a target series in [-1, 1] |
| `engine15/rl/metrics.py` | Sharpe, Sortino, max drawdown, CAGR, Calmar, turnover, holding time, cost drag |
| `engine15/rl/benchmarks.py` | buy-and-hold, daily 30-day momentum (frozen 11 Nov 2026), random agent (10 seeds) |
| `engine15/rl/walkforward.py` | rolling train / unseen test windows, stitching, per-window and stitched evaluation |
| `engine15/rl/phase1.py`, `report.py`, `__main__.py`, `config.py` | runner, report, CLI, YAML + run folders |
| `tests/rl/` | look-ahead, data/store, costs/backtest, metrics/benchmarks/walk-forward, end-to-end smoke |

## Design decisions

- **Storage is `.csv.gz` behind one module.** pyarrow/parquet cannot be installed on this laptop
  (Windows on ARM64). Every table has an integer `ts_ms` (UTC epoch ms) column; floats are read
  back with `float_precision="round_trip"`, so a write and a read give back the same bits (tested).
  Moving to parquet later means editing `store.py` only.
- **Data: honest and resumable.** One request at a time, a pause between pages, timeouts, retries
  with back-off; a network blip never raises, it returns what it got and the next run resumes from
  the last stored bar (progress is saved every 20 pages). Duplicates are dropped (the later copy
  wins), the pre-listing no-trade head is dropped, OHLC-invalid bars are dropped and listed, and
  gaps are reported, never filled with made-up bars. Funding is seeded (read only) from the
  engine's own `data/btcusdt_funding.csv` and extended into `data/rl/`; the live engine's files are
  never written.
- **Open interest is live only.** The free endpoint keeps about 30 days, so OI is fetched and
  stored for the live phase but is OFF in every backtest (`data.open_interest.enabled_in_backtest: false`).
- **Point-in-time rules.** A bar is keyed by its open time and known at its close. Features are
  trailing windows ending at the bar. A funding rate counts from its settlement on: Binance stamps
  settlements 1-47 ms after the hour, so a stamp within 60 s of the 15m grid is treated as that grid
  time (never moved more than that earlier; anything else rounds up). Time to the next funding is
  projected from past settlements only. The one higher-timeframe feature (last closed UTC day)
  goes through `engine15.data.htf_on_15`, the engine's no-look-ahead join. The test: features on data
  cut at random points t equal the full-data features up to t, bit for bit; a deliberately leaky
  feature (next bar's return, a centred window) and funding read one bar early are both caught.
- **One cost model, shared.** `costs.CostModel` is used by the backtester now and will be used by the
  Phase 2 simulator (its `step()` is the per-bar formula; a test checks the vectorised backtester
  gives the same numbers bar by bar), so an agent is trained against exactly the costs it is judged by.
  Fee 0.10% a side by default (the owner's paper rule); every report also shows 0.05% (Binance
  USDT-M taker). Half-spread 0.5 bps a side; slippage 0.10 x per-bar realised vol (96 bars, known at the
  decision) x |trade|, about 0.03% a side at typical BTC 15m vol, far more than a $10k order really moves
  the perp; funding paid by longs and received by shorts when the rate is positive, on the position held
  over the bar that ends at the settlement.
- **The delay.** A target decided at the close of bar t fills at the open of bar t+1 (configurable,
  never 0: the model refuses a fill inside the decision bar). Returns are open to open, equity compounds.
- **Walk-forward.** 12-month train, next 3 months test, roll 3 months. Benchmarks have no training,
  but they are stitched and evaluated exactly the way Phase 2's agents will be: one target series made of
  each test window's decisions, one backtest over it (positions and costs carry across window edges),
  metrics per window and for the stitched out-of-sample span.
- **Annualisation.** 15m bars, 24/7: one year = 365 x 96 = 35,040 bars. Sharpe and Sortino use it, risk-free 0.

## What Phases 2-4 will add (not started)

- Phase 2: done (see below). The owner later allowed gymnasium, torch and stable-baselines3, so the
  environment is a Gymnasium env rather than numpy-only.
- Phase 3: done (see below): a continuously learning, cost-aware 15m agent, the owner's filters and harnesses, ETH.
- Phase 4: done (see below). The owner chose "more data per model" after the Phase 3 review.

## Phase 1 results (headline)

Re-run `phase1_20261111T124954Z_53591f6b` (11 Nov 2026, with the frozen daily momentum rule; first run
`phase1_20261111T113950Z_03678408`). Data: 251,586 bars, 2019-09-08 19:00 to 2026-11-11 11:15 UTC, no missing
bars (Binance serves its 17 downtime bars as flat no-trade bars), 7,858 funding settlements. Out of sample = 25
stitched 3-month test windows, 2020-10-01 to 2026-11-11.

| Stitched OOS | Fee/side | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Avg hold | Cost drag/yr |
|---|---|---|---|---|---|---|---|---|---|
| Buy-and-hold | 0.10% | +249.3% | 0.64 | 0.91 | 79% | 0.29 | ~0 | whole span | 11.0% (almost all funding) |
| Buy-and-hold | 0.05% | +249.5% | 0.64 | 0.91 | 79% | 0.29 | ~0 | whole span | 11.0% |
| Momentum (daily, 30-day sign, long/short) | 0.10% | +237.7% | 0.63 | 0.89 | 64.5% | 0.34 | 62 | 281 h | 14.3% |
| Momentum (daily, 30-day sign, long/short) | 0.05% | +308.7% | 0.68 | 0.97 | 61.3% | 0.42 | 62 | 281 h | 11.2% |
| Random, mean of 10 seeds | 0.10% | -95% (sd 4) | -0.93 (sd 0.32) | -1.30 | 97% | -0.44 | 323 | 36 h | 43% |
| Random, mean of 10 seeds | 0.05% | -87% (sd 12) | -0.59 (sd 0.32) | -0.84 | 93% | -0.35 | 323 | 36 h | 27% |
| *retired: momentum, sign of 96-bar return every bar* | 0.10% | -100% | -7.53 | -10.57 | 100% | -0.99 | 3,564 | 4.9 h | 464% |

What it says: on 15m bars the costs are the opponent. A random agent that trades once a day loses 87-95% from
costs alone. Buy-and-hold is BTC's drift (gross +585%), less ~11% a year of funding a perpetual long pays; it was
positive in only 12 of 25 windows. The daily 30-day momentum rule trades ~31 times a year, makes about the same
return as buy-and-hold at 0.10% (Sharpe 0.63 vs 0.64) with a smaller drawdown (65% vs 79%, Calmar 0.34 vs 0.29),
and was positive in 16 of 25 windows. Full tables: `research/out/rl/phase1_report.md`.

### The momentum benchmark fix (frozen 11 Nov 2026, Phase 2 task 1)

Phase 1's momentum rule (sign of the 96-bar return at every bar close) traded ~1,800 times a year and lost
everything to costs: a straw man. Before any RL code was run or any agent result existed, it was replaced and
frozen: **decide once a day at the close of the bar ending 00:00 UTC, fill at the next bar's open, target = sign of
the 30-day (2,880-bar) return, long/short** (+1 / -1; 0 with too little history). Long/short because Phase 1's
design (and the agent's action set) is long/short; `benchmarks.momentum(..., long_short=False)` gives long/flat
but is not used. Costs come from the shared `costs.py` through the same backtester. The old rule stays in
`benchmarks.momentum_every_bar` for the record only.

# Phase 2: environment, risk manager, PPO agent, walk-forward training

Paper only, out-of-sample results only. Config: `configs/rl/phase2.yaml` (loaded on top of
`phase1.yaml`). Output: `research/out/rl/phase2_report.md`, `phase2_summary.json` (for a future web "Lab"
tab), `phase2_risk_log.csv` (every order the risk manager blocked or resized, out of sample),
`phase2_progress.json`; small model files under `research/out/rl/models/<config hash>/` (gitignored style).

    py -3 -m engine15.rl phase2 --offline                 stored data, seeds and budget from the config
    py -3 -m engine15.rl phase2 --seeds 3 --timesteps 50000
    py -3 -m engine15.rl phase2 --offline --fresh         retrain everything (ignore finished folds)

An interrupted run resumes: every finished fold (seed x window) is saved at once and reused by a later run
with the same config hash (`--fresh` overrides).

## Files (Phase 2)

| File | What |
|---|---|
| `engine15/rl/env.py` | `Market` (read-only arrays shared by all envs) and `TradingEnv` (Gymnasium) |
| `engine15/rl/risk.py` | `RiskManager`: max position, daily loss, drawdown kill switch, volatility breaker; logs every block/resize |
| `engine15/rl/agent.py` | SB3 PPO builder, `NumpyPolicy` (the actor in numpy: fast evaluation, ~20 KB .npz), memory guard callback |
| `engine15/rl/train.py` | per-fold training with validation model choice; one continuous out-of-sample simulation |
| `engine15/rl/phase2.py`, `report2.py` | runner (memory-gated, resumable), flags, verdict, report, summary JSON |
| `engine15/rl/resources.py` | below-normal priority, free-memory reading (no psutil), torch on 2 threads |
| `tests/rl/test_env.py`, `test_risk.py`, `test_phase2_smoke.py` | no look-ahead in observations, env P&L == backtest P&L, each risk rule, end-to-end + resume, numpy policy == SB3 |

## Design (frozen 11 Nov 2026 about 12:55 UTC, before any agent was trained or evaluated)

- **Timing.** Decide at the close of the bar ending on each UTC hour (every 4th 15m bar), fill at the next bar's
  open (the cost model's delay), hold to the next decision. Returns open to open, as in the backtester.
- **Observation.** The decision bar's point-in-time features (Phase 1's 15 + the 30-day return and 30-day
  momentum: 18), z-scored with the mean/sd of the fold's **training slice only**, clipped at +-5, NaN -> 0; plus
  the current target, time in position and a "risk manager is restricting" flag. Test: an observation built on
  data cut right after its bar equals the one built on all data, for every decision, with and without the risk
  manager; a deliberate one-bar peek (features or the risk manager's mark) makes it fail.
- **Action.** Target position in {-1, 0, +1} (short / flat / long, 1x equity).
- **Costs.** The env calls the same `CostModel.step()` on the same arrays as `backtest.run`; a test replays the
  env's executed targets through the backtester and gets the same per-bar net return, fee, spread, slippage and
  funding (and the real run checks it again: max difference is printed in the report).
- **Reward.** 100 x (sum over the hour's bars of log(1 + net return) - 0.0005 x |target change|): the real costs
  are already in the net return; the penalty adds half a fee per unit of turnover to discourage churn.
- **Minimum hold.** A new target is refused until 48 bars (12 h) after the last change; risk exits are never held back.
- **Risk manager** (between agent and execution, in training and in evaluation): |position| <= 1.0; 5% loss on the
  UTC day -> flat for the rest of the day; 30% below the equity peak -> flat for 7 days, then the peak is reset
  (a stand-in for "stop and review"); rv_16 > 3 x rv_672 -> |position| <= 0.5. Equity rules are checked at every
  bar close on equity marked at that close (no later price) and can flatten between decisions. Every blocked or
  resized order is logged with the rule and the reason.
- **PPO** (Stable-Baselines3 2.9): MLP 64-64 tanh for policy and value, lr 3e-4, 4 envs x 512 steps, batch 256,
  5 epochs, gamma 0.99, GAE 0.95, clip 0.2, entropy 0.01; CPU, 2 torch threads, below-normal priority.
  Training episodes are 30 days of hourly decisions from a random start (random starting position).
- **Walk-forward.** Phase 1's folds (12-month train, 3-month test, roll 3 months; 25 folds). Inside each train
  window the first 9 months train and the last 3 months validate: 100,000 PPO steps in 5 chunks, the policy is
  run on the validation slice after each chunk, the best validation Sharpe (net of 0.10% costs) is kept, early
  stop after 2 checks without improvement. The kept policy is then used once on the next 3 months. Out of
  sample, one simulation runs across all 25 test windows, each decision taken by the policy of the fold whose
  test window holds it; position, holding clock and risk state carry across windows as they would live. The
  executed target series is replayed through the Phase 1 backtester and scored exactly like the benchmarks.
- **Seeds.** 5 (0-4), trained one after another. **Fees.** 0.10% a side headline (the agent trains at 0.10%);
  the same trained policies are re-run at 0.05% for the comparison line.
- **Overfitting flags** (thresholds frozen with the rest): train-slice vs test Sharpe gap > 1.0; seed dispersion
  (stitched Sharpe sd > 0.5 or seeds disagree on the sign); agent (seed mean) beats a benchmark's Sharpe in fewer
  than half the folds; a sign flip between 0.10% and 0.05% (or the comparison with buy-and-hold flips); turnover >
  100 a year; and a degenerate policy (long > 90% of the time, a buy-and-hold clone, or flat > 95%).
- **Memory.** A fold starts only with >= 700 MB free (otherwise it waits and retries); training stops cleanly under
  350 MB and the fold restarts after a wait; one process, seeds in sequence. Peak working set ~370 MB.

## Phase 2 results (headline)

Run `phase2_20261111T130110Z_8bc5b963` (11 Nov 2026, 29 min on CPU, 5 seeds x 25 folds, 100,000 PPO steps per
fold). Out of sample, 2020-10-01 to 2026-11-11, stitched, after costs:

| Stitched OOS, 0.10% a side | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Avg hold | Cost drag/yr |
|---|---|---|---|---|---|---|---|---|
| PPO agent, mean of 5 seeds | -99.6% | -1.92 (sd 0.13) | -2.70 | 100% | -0.60 | 601 | 17 h | 79% |
| seeds 0 / 1 / 2 / 3 / 4 (Sharpe) | -99.5% .. -99.7% | -1.78 / -1.81 / -2.01 / -2.10 / -1.90 | | 100% | | 563-629 | 16-18 h | 75-83% |
| Buy-and-hold | +249.3% | 0.64 | 0.91 | 79% | 0.29 | 0 | whole span | 11% |
| Momentum (daily, 30-day, long/short) | +237.7% | 0.63 | 0.89 | 64% | 0.34 | 62 | 281 h | 14% |
| Random (mean of 10) | -95.3% | -0.93 | -1.30 | 97% | -0.44 | 323 | 36 h | 43% |
| PPO agent at 0.05% a side | -97.5% | -1.20 | -1.69 | 98% | -0.47 | 608 | 17 h | 50% |

**Verdict: no.** The agent does not beat buy-and-hold (or momentum, or even the random agent) out of sample after
0.10% fees, on return or risk, for any seed. Gross of costs its Sharpe is about 0 (-0.28 to +0.01): no edge; it then
trades ~500 times a year and pays ~80% of equity a year in costs. PPO did not fit its own training slices either
(mean train Sharpe -1.27). Flags fired: train/test Sharpe gap (1.05), beats benchmarks in under half the folds
(Sharpe higher than buy-and-hold in 3 of 25), high turnover. Not fired: seed dispersion (the seeds agree: all
lose), fee sign flip, degenerate policy. Also found: the frozen risk limits alone take buy-and-hold from Sharpe
0.64 to 0.18 (-20%), so they are too tight for 1x BTC. Memory: the guard stopped training 3 times while the
owner's history replay ran (folds restarted after short waits; finished folds kept). Full report:
`research/out/rl/phase2_report.md`.

## Suggestions for Phase 3 (not started; each a new, pre-registered experiment)

- Make the decision problem match the cost structure: decide once a day (or every 4-8 h) instead of hourly, and
  let the agent see the momentum benchmark's signal; the only rule that survives costs here trades ~31 times a year.
- Prove learnability first: a check that PPO can beat a planted, known edge in synthetic data, and fit its own
  training slice, before any walk-forward.
- Revisit the risk limits on their own merits (they cost buy-and-hold most of its Sharpe): e.g. vol-targeted size
  instead of a 30% kill switch and a 5% daily stop, judged on buy-and-hold first.
- Then robustness as planned: cost stress, regime splits, ETH, more seeds, all frozen before testing.

# Phase 3: a continuously learning 15m agent that learns when not to trade

Paper only, out-of-sample results only. The timeframe stays 15 minutes: 15m bars and a 15m decision clock. Config:
`configs/rl/phase3.yaml` (frozen 11 Nov 2026 14:39 UTC, before any walk-forward test; its `freeze` block records what was
decided when). Output: `research/out/rl/phase3_report.md`, `phase3_summary.json` (for a future Lab tab),
`phase3_learnability.json`, `phase3_riskcheck.json`, `phase3_cadence.json`, `phase3_diag2.json` (diagnostic only),
`phase3_paper_dryrun.json`, `phase3_risk_log_<asset>.csv`; models under `research/out/rl/models3/<work hash>/<asset>/`.
A rerun with the same frozen config resumes from every saved fold (`--fresh` overrides).

## Files (Phase 3)

| File | What |
|---|---|
| `engine15/rl/features3.py` | Phase 2 features + 1h/4h/1d trend and price vs higher-timeframe mean (closed bars, `htf_on_15`), the frozen momentum signal, vol regime, 30-day daily vol, time of day/week |
| `engine15/rl/qagent.py` | the agent: afterstate Q-learning with a hard-wired round-trip cost, linear W, n-step double-Q targets, behaviour cloning for warm starts |
| `engine15/rl/policy3.py` | Q values -> decisions: hold by default, minimum hold, gates, confidence band, masks, seed consensus; fast P&L == backtester |
| `engine15/rl/continual.py` | full trains with validation early stopping and the neutral fallback; weekly fine-tunes on a recency-weighted replay buffer |
| `engine15/rl/risk3.py` | the Phase 3 risk manager (vol-targeted size + soft drawdown brake), one `Stepper` shared by the backtest and paper mode |
| `engine15/rl/baselines3.py` | the strategy loop's rules A (H29 H30 1.5x/0x spot) and B (H29 H31 trail 4 ATR spot), imported read-only from `research/harness` |
| `engine15/rl/synth.py`, `learncheck.py`, `env3.py` | synthetic series with a planted edge, the learnability check, a Gym env so PPO gets the same check |
| `engine15/rl/phase3.py`, `phase3pre.py`, `report3.py` | runner (resumable, memory-paused), pre-freeze steps, report / flags / verdict / summary |
| `engine15/rl/paper.py` | forward paper mode: decide the next bar with the newest model, log it, fine-tune when due; dry run == batch path |
| `engine15/rl/diag2.py` | DIAGNOSTIC: the Phase 3 filters applied to Phase 2's (seen) trades |
| `tests/rl/test_phase3_units.py`, `test_phase3_smoke.py` | no look-ahead (features, risk manager, updates), reward == backtester, decision rules, end to end + resume, baselines, paper == batch |

## Design (frozen before testing)

- **Agent.** The market does not react to a paper book, so for every bar, held position p and target a the one-bar reward
  is known exactly. The agent learns W(x, a) (the value of holding a after this bar) from the features only;
  Q(x, p, a) = W(x, a) - cost(p -> a) with the cost hard-wired at 2x the real one-side cost (a full round trip charged on
  every change). Holding is free, so inaction is the default and the no-trade band is exact. Reward: vol-scaled net return
  minus a log-utility variance charge (so flat beats a no-edge position). Linear W, 16-step double-Q targets, gamma 0.99,
  zero-initialised output (no made-up action preferences at the start), weight decay, early stopping on the validation
  Bellman loss, and a "do no harm" rule: a fold whose model has a validation Sharpe under 0.5 acts neutral.
- **Why not PPO.** On synthetic data with a planted edge, Phase 2's PPO on the same reward and features did not fit its
  training slice and lost after costs (turnover 200-950 a year); see the learnability table in the report.
- **Actions.** Base: size in {-1, -0.5, 0, 0.5, 1}; decided every 15m bar; minimum hold 4 bars.
- **Continual learning.** (a) static model per fold (Phase 2 style); (b) one model fine-tuned weekly forever; (c) a fresh
  model each fold, fine-tuned weekly inside it (primary). Weekly = Monday 00:00 UTC; 200 gradient steps on the trailing
  12 months (half uniform, half with a 60-day recency half-life), warm-started with the optimiser state. An update at bar U
  trains only on targets that close by bar U. Cadence chosen before the freeze (weekly beat daily).
- **Risk manager.** size = min(1, 60% / one-week realised vol) x a soft drawdown brake (0.75 at 20%, 0.5 at 30% below the
  rolling 90-day peak); re-sized only when the size moves by more than 0.2; every resize logged with its reason. Judged on
  buy-and-hold and momentum first (one documented revision), frozen before any agent result.
- **Owner's variants.** v1 seed consensus, v2 confidence gate, v3 higher-timeframe alignment, v4 volatility/cost gate
  (thresholds re-chosen each fold from the 3 months before it), v5 meta-labeling on the momentum direction, v6
  core-satellite (0..1.5x around a 1x core); and on the loop's rules A / B: the rules as benchmarks, residual RL
  (baseline + an adjustment in +-0.5x), imitation warm start (behaviour cloning, then RL) vs the same agent from scratch.
  Everything built on A or B is scored only on folds ending by 2025-11-11 (the loop's sealed holdout is not touched).
- **Forward paper mode.** `py -3 -m engine15.rl paper` decides the next bar from the latest closed bars with the newest
  model, logs it (`research/out/rl/paper/<asset>/decisions.jsonl`), runs the weekly fine-tune when due and saves a new model
  version; it re-checks the do-no-harm rule quarterly. Not wired into the live engine or the page.

## Phase 3 results (headline)

Run `phase3_20261111T144229Z_6e297970` (11 Nov 2026, 136 min on CPU, 3 seeds, BTC 9 agent families + ETH base family).
BTC out of sample 2020-10-01 to 2026-11-11 (25 folds), stitched, after costs, 0.10% a side; agents through the Phase 3
risk manager:

| BTC, 0.10% a side | Net return | Sharpe | Max DD | Calmar | Turnover/yr | Avg hold | Cost drag/yr | Break-even fee |
|---|---|---|---|---|---|---|---|---|
| (a) static, mean of 3 seeds | -52% | -0.42 | 75% | -0.16 | 40 | 108 h | 5.6% | < 0 (loses before fees) |
| (b) continual, never reset | -46% | -0.14 | 76% | -0.13 | 80 | 130 h | 13.6% | < 0 |
| **(c) continual + retrain each fold (primary)** | **-53%** | **-0.37** | **79%** | **-0.15** | **46** | **84 h** | **8.1%** | **< 0** |
| v3 higher-timeframe alignment | +48% | 0.50 | 37% | 0.19 | 29 | 40 h | 5.8% | 0.32% |
| v5 meta-labeling on momentum | +38% | 0.35 | 55% | 0.10 | 44 | 68 h | 8.6% | 0.22% |
| v6 core-satellite (0..1.5x) | +106% | 0.48 | 67% | 0.18 | 90 | 327 h | 21.0% | 0.23% |
| Buy-and-hold (perp) | +249% | 0.64 | 79% | 0.29 | 0 | - | 11.0% | > 5% |
| Momentum (daily 30-day) | +238% | 0.63 | 64% | 0.34 | 62 | 281 h | 14.3% | 0.42% |
| Phase 2 PPO (reference) | -100% | -1.92 | 100% | -0.60 | 601 | 17 h | 79.3% | < 0 |

**Verdict: no.** The continuously learning 15m agent does not beat buy-and-hold or momentum out of sample after 0.10% fees,
for any seed; it loses before fees (gross Sharpe about 0). It did learn when not to trade: turnover fell from ~600 to
~46 a year and costs from ~80% to ~8% of equity a year. No variant or filter beats both benchmarks on every seed; the
ones that make money (v3, v5, v6) lean on the momentum signal or a buy-and-hold core and still have a lower Sharpe than
buy-and-hold. On the loop's rules (dev span to 2025-11-11 only), residual RL lowered both baselines' Sharpe (A 1.19 ->
1.09, B 1.32 -> 1.06; better in 5 and 4 of 21 folds), and imitation warm starts beat training from scratch but ended
far below the rules they imitated. ETH: the primary agent is about flat (Sharpe 0.13 vs buy-and-hold 0.60). The
learnability check failed on its frozen criteria (the planted edge is found unreliably; with no edge the agent stays
near flat); PPO failed it worse. The new risk manager passed its check on buy-and-hold and momentum (BTC buy-and-hold
Sharpe 0.64 -> 0.68, max DD 79% -> 68%). Full report: `research/out/rl/phase3_report.md`.

# Phase 4: more data per model

Paper only, out-of-sample results only, 15-minute bars and a 15-minute decision clock. The owner chose "more data per model"
after the Phase 3 review: Phase 3's agent fitted its 9-month training slices (train Sharpe ~2.7) but had ~0 validation and
negative test Sharpe, and a realistic edge has a t-stat of only ~1.6 on 9 months of 15m data. Phase 4 asks whether longer,
pooled training data and inputs with an economic reason give a 15m agent a real out-of-sample edge. Config:
`configs/rl/phase4.yaml` (its `freeze` block records what was decided when, including every change made before the freeze).
Output: `research/out/rl/phase4_report.md`, `phase4_summary.json`, `phase4_learnability.json`, `phase4_lookahead.json`,
`phase4_exploration_sp*.json` (synthetic exploration, before the freeze); models under `research/out/rl/models4/<work hash>/`,
input caches under `research/out/rl/phase4_cache/` (memory-mapped float32; reproducible, not for version control).

## Files (Phase 4)

| File | What |
|---|---|
| `engine15/rl/features4.py` | the 18 Mind 15 readings used (trend, funding, basis, flow, vol regime, levels) read from the evidence store snapshot, availability flags, and the real-data truncation test of every input |
| `engine15/rl/pool4.py` | one asset at a time into memory-mapped caches (inputs, reward arrays, times), per-asset z-scoring on training rows, recency and block-bootstrap weights |
| `engine15/rl/models4.py` | the two families: SP (weighted ridge on the next day's vol-scaled return -> Phase 3's cost-aware policy) and Q (the Phase 3 learner on pooled rows); selection, refit, 'do no harm' |
| `engine15/rl/learn4.py` | the learnability check at the new data sizes (same test span, three training sizes) and its power check |
| `engine15/rl/phase4.py`, `report4.py` | runner (frozen-config guard, resumable, memory-paused), evaluation against every benchmark, flags, verdict, report, summary |
| `tests/rl/test_phase4.py` | unavailable readings never a signal, assembled inputs and engine readings point in time, no training row past its fold (SP and Q, pooled), pooled rows never cross assets, reward-array P&L == backtester, SP finds a planted edge, end to end + resume, unfrozen config refused |

## Design (frozen before testing)

- **More data per model.** One model per walk-forward fold (Phase 1's 25 folds, test windows unchanged) trained on every bar
  from 2019 up to the fold (each market's first bar + 35 days; BTC perp from Sept 2019), pooled across BTC and ETH; one
  variant pools all 8 engine markets (their own `asset_cost`, no funding). Inputs are z-scored per asset on that asset's own
  training rows. The recency half-life (none / 2 years / 1 year) is chosen per fold on the last 6 months before it; then the
  model is refit on everything up to the fold. Ablations keep Phase 3's 12-month single-asset window.
- **Inputs.** Phase 3's features plus 18 Mind 15 readings read only from the compact evidence store (`engine15/evcache.py`,
  snapshot): `tr_1h/4h/1d/1w`, `fund_z`, `fund_3d`, `pb_z`, `pb_chg_4h`, `cvd_4h`, `cvd_24h`, `cvd_div`, `cbp_z`, `vol_rank`,
  `shock_ratio`, `rg_er`, `sr_room`, `sr_lean`, `sr_pd_pos`, each with an economic reason (`features4.py` docstring), and 7
  availability flags. Live-only readings are not used; a missing reading is NaN (never a zero signal) with its group's flag at 0.
- **No look-ahead.** `phase4-check` recomputes every reading with the engine's own code on data cut at random bars
  (`evidence.build_one`; the basis and Coinbase source modules on source files cut to what was known) and compares with the
  full-data rows, checks the store holds exactly what the code computes, and runs the truncation test on the assembled matrix.
  Nothing in the live engine is called beyond these read-only functions; `backtest.prepare` is never called.
- **Families.** SP: weighted ridge (penalty and half-life chosen by validation R2, no intercept, block-bootstrap seeds) on the
  next 96 bars' vol-scaled net return, turned into decisions by Phase 3's cost-aware policy (round-trip cost band, risk
  charge, minimum hold 4 bars). Q: the Phase 3 afterstate Q-learner unchanged, fed pooled rows. 'Do no harm' as in Phase 3:
  a fold whose validation-stage model nets a Sharpe under 0.5 on an asset acts flat on it.
- **Primary.** Chosen by a rule written before the learnability check: the pooled-2 family that passes it (or, failing both,
  the better planted-edge test Sharpe at the 6-year pooled size).
- **Scoring.** Agents through the Phase 3 risk manager into the shared backtester, 0.10% headline and 0.05%, break-even fee,
  gross (pre-cost) Sharpe; benchmarks buy-and-hold perp and spot, daily momentum, random, the Phase 3 agents (from the saved
  Phase 3 run), the loop's rules A and B. Everything compared with A/B is scored only up to 2025-11-11 (the loop's sealed
  holdout starts there); the agents are shown on both spans, labelled. Phase 3's flags and thresholds.
- **Memory.** Heavy steps start only with >= 1,000 MB free and pause under 400 MB; one process; below-normal priority; torch on
  2 threads; assets loaded one at a time; caches memory-mapped.

## Phase 4 learnability at the new data sizes (synthetic, before the freeze)

The same 12-month test span of a synthetic series (planted AR(1) edge, kappa 0.02; Phase 3's criteria) traded by models
trained on three data sizes, fresh series (seed base 7000), 5 seeds; power check 10 seeds, 24-month test:

| Family / size | Edge: test Sharpe (oracle) | Edge found | No edge: test Sharpe / turnover / exposure | Phase 3 criteria | Power check: edge test Sharpe (sd), found |
|---|---|---|---|---|---|
| SP, 9 months (Phase 3's size) | 0.40 (2.36) | 2 of 5 | 0.29 / 47 / 53% | FAIL | -0.01 (0.67), 1 of 10 |
| SP, 3 years, one series | 0.31 (2.02) | 2 of 5 | -0.09 / 9 / 16% | FAIL | - |
| SP, 6 years x 2 series pooled | 1.72 (1.90) | 5 of 5 | -0.25 / 18 / 16% | PASS | 1.10 (0.90), 7 of 10 |
| Q, 9 months (Phase 3's size) | -0.23 (2.36) | 0 of 5 | -0.46 / 50 / 37% | FAIL | 0.59 (1.08), 5 of 10 |
| Q, 3 years, one series | 0.97 (2.02) | 3 of 5 | -0.08 / 38 / 71% | FAIL | - |
| Q, 6 years x 2 series pooled | 2.13 (1.90) | 5 of 5 | 0.19 / 7 / 29% | PASS | 1.66 (1.23), 7 of 10 |

More data per model fixes "finds the planted edge unreliably" on synthetic data: at Phase 3's size both families fail; with
6 years x 2 pooled series both pass and find the edge in every seed of the main check (7 of 10 in the harder power check).
Primary by the pre-registered rule: Q (higher planted-edge test Sharpe at the pooled size). Before this check, run 1 (seed base
5000) was stopped and the SP selection rule changed on synthetic exploration seeds; see the freeze block in phase4.yaml.

## Phase 4 results (headline)

Run `phase4_20261111T205810Z_d214cadd` (11 Nov 2026, 57 min on CPU, 3 seeds, 8 frozen variants, no memory pauses). Primary:
the Q agent pooled on BTC+ETH, expanding window, Phase 3 features + readings. BTC out of sample 2020-10-01 to 2026-11-11 (25
folds), stitched, through the Phase 3 risk manager, 0.10% a side:

| BTC, 0.10% a side | Net return | Sharpe | Max DD | Calmar | Turnover/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|
| **Phase 4 primary (Q, BTC+ETH pooled), mean of 3 seeds** | **+79%** | **0.48** (0.52 / 0.40 / 0.51) | **41%** | **0.24** | **47** | **0.78** (t ~1.9) | **0.30%** |
| SP, BTC+ETH pooled | +107% | 0.58 | 35% | 0.37 | 83 | 1.02 | 0.24% |
| SP, 8 markets pooled | +127% | 0.65 | 36% | 0.41 | 80 | 1.09 | 0.27% |
| SP, one asset, expanding, readings | +374% | 0.85 (0.66 / 0.45 / 1.43) | 36% | 0.69 | 90 | 1.29 | 0.32% |
| SP, one asset, 12-month window, Phase 3 inputs (Phase 3's data budget) | -24% | -0.18 | 44% | -0.10 | 20 | -0.10 | < 0 |
| Phase 3 agent (c) (reference) | -53% | -0.37 | 79% | -0.15 | 46 | -0.05 | < 0 |
| Buy-and-hold (perp) / (spot) | +249% / +584% | 0.64 / 0.82 | 79% / 77% | 0.29 / 0.48 | 0 | 0.83 | > 5% |
| Momentum (daily 30-day) | +238% | 0.63 | 64% | 0.34 | 62 | 0.87 | 0.42% |

**Verdict: no, but the picture changed.** More data per model gives the 15m agent an edge BEFORE costs on every seed (BTC gross
Sharpe 0.65-0.84, t ~1.9 on the full span and ~2.2 up to 2025-11-11; ETH 0.95-1.30, t ~2.8; break-even fee ~0.30% BTC, ~0.42%
ETH), where Phase 3 lost before fees. After 0.10% fees it does not beat buy-and-hold or momentum risk-adjusted on BTC for any seed
(Sharpe 0.48 vs 0.64 and 0.63; Calmar 0.24 vs 0.29 and 0.34), although its drawdown is about half buy-and-hold's (41% vs 79%). On
ETH it beats buy-and-hold on every seed (0.77 vs 0.60, Calmar 0.49 vs 0.22) but not momentum (0.83). Up to 2025-11-11 the loop's
rules A and B (Sharpe 1.19, 1.32) stay far ahead of every agent (primary 0.67). No variant beats both benchmarks on every seed.
The ablation grid says where the improvement comes from: Phase 3's data budget (12-month window, one asset) loses before fees
with either input set; the expanding window turns it positive; the Mind 15 readings add the most (BTC+ETH pooled SP: Sharpe 0.14
without them, 0.58 with them; one-asset SP 0.54 -> 0.85; ETH -0.16 -> 0.67); pooling BTC with ETH did not add on its own, pooling 8
markets helped a little. Flags on the primary: train/validation/test gap (1.90 / 0.95 / 0.25) and fewer than half the folds beating
buy-and-hold (10/25) and momentum (9/25); no seed dispersion, fee sign flip, high turnover or degenerate policy. With 8 variants
tried, the best-looking one (one-asset SP with readings, BTC Sharpe 0.85, seed spread 0.45-1.43) is a lead, not a result. Full
report: `research/out/rl/phase4_report.md`.

# Phase 5: trade-less variants + forward paper

Paper only. The owner chose "Trade-less variant + paper" after the Phase 4 review (12 Nov 2026). Config:
`configs/rl/phase5.yaml` (frozen before any Phase 5 number; its `freeze` block records what happened when). Three parts:

1. **Forward paper run of the Phase 4 primary inside Mind 15** (`engine15/playbook5.py`, `engine15/rl/forward5.py`): the
   only unseen evidence left. Book `p5_rlq`, BTC and ETH, each $10,000, 0.10% a side, Phase 4's perp accounting; go-live
   `REGISTERED = 2026-11-12 04:30 UTC`; flagged NOT passed everywhere ("after fees it trailed buy-and-hold in history").
2. **At most 3 pre-registered trade-less variants** of the same agent (Phase 4's trained fold models, no retraining).
3. **A small registered ablation**: which reading groups carry the pre-cost edge (retrained), plus correlations with the
   daily momentum rule and the loop's rule A.

Holdout honesty: Phase 4 already scored every test window through 2026-11-11, so no historical span is unseen for RL any
more; parts 2 and 3 show the full span and the span up to 2025-11-11, and anything compared with the loop's rules A/B stops
at 2025-11-11. Report: `research/out/rl/phase5_report.md`, `phase5_summary.json`.

## Files (Phase 5)

| File | What |
|---|---|
| `engine15/rl/forward5.py` | training of the forward model (Phase 4's `q_fold` with an export hook, engine files, weekly), the update launcher and subprocess (lock, >= 1,500 MB free, retry every 30 min), the light live decision step (bar-file tail, evidence-store tail rows, recorded decisions), the book (risk manager per seed, mean of seeds, shared backtester), and the forward == batch check |
| `engine15/playbook5.py` | the strategy-book module (docs/PLAYBOOK_INTERFACE.md): `BOOKS`, `REGISTERED`, `step`, `page_block` with playbook4's block fields (`not_passed`, `note`, per-coin `books` with position, equity and spot buy-and-hold since go-live) |
| `engine15/rl/models4.py` | `q_fold(..., export=dict)` hands back the refit model (weights, bias, per-asset z-score stats, 'do no harm' flags); Phase 4's computation is unchanged |
| `engine15/rl/phase5.py`, `report5.py` | part 2 evaluation (trade-less variants), part 3 ablation training and evaluation (+ occlusion), correlations, report |
| `tests/rl/test_phase5.py` | forward == Phase 4 batch on real data for the same model and bars; truncation (no look-ahead) on real data; the live readings source == Phase 4's snapshot; planted-data forward == batch, incremental == one shot, resume; model data-end rule; 'do no harm'; update guards |
| `tests/test_playbook5.py` | the interface and page-block fields, forward only, trade accounting adds up, a repeated step records nothing new, step time |

## Part 1: how the forward run works

- **Model.** Exactly the Phase 4 primary procedure (Q agent, BTC+ETH pooled, expanding from 2019, Phase 3 features + 18
  readings + 7 flags, half-life and 'do no harm' on the last 6 months, refit to the data end), seeds 0, 1, 2. Rebuilding
  Phase 4's fold-24 models through the export hook gives Phase 4's stored test values bit for bit (all seeds, both coins),
  so a model the forward run trains is the Phase 4 primary's model. Data: the engine's own 15m files (what Mind 15 sees);
  BTC from the perp's first bar (2019-09-08) so the span equals Phase 4's. Disclosed difference: Phase 4 trained BTC on the
  USD-M perp bars; the forward run trains and decides BTC on the engine's Binance spot bars (perp funding, perp costs).
- **Live step (in the live loop, light).** Per coin: the bar file's tail, the funding file and the evidence store's tail
  rows (read only), Phase 4's inputs for the closed bars not yet decided (a 4,300-bar window gives exactly the
  full-history rows), the newest model whose data end is at or before each bar's close, Phase 3's policy per seed from the
  recorded state, decisions appended to `research/out/rl/forward5/decisions_<asset>.jsonl`. The book is rebuilt from that
  record each step: each seed through the Phase 3 risk manager, the book holds the mean of the three executed positions.
  Measured: about 0.2 s and about 20 MB working set (40 MB private) added per step.
- **Weekly update.** When the newest model's data end is before the latest Monday 00:00 UTC, the step starts
  `py -3 -m engine15.rl phase5-update` (below-normal priority, no window) if no update holds the lock, the last attempt is
  30+ minutes old and at least 1,500 MB are free; the subprocess pauses under 400 MB, refits on data up to then (about 3-4
  minutes), writes `research/out/rl/models5/live/model_<UTC>.json` atomically, and the next decision uses it. Never two at
  once; nothing is trained inside the step.
- **Timing.** Decision at a 15m close, fill at the next open (Phase 4's frame). The step runs a few minutes after a close
  and records each decision's lag; a catch-up after downtime decides each missed bar with only the information up to it.
- **Page.** The block renders on the Books tab as a not-passed book. One limitation without a page change: the page's coin
  line knows only long books, so a short book position shows as "flat" there (the open-trade line shows SHORT correctly).

## Phase 5 results (parts 2 and 3)

Run `phase5_20261112T100635Z_b8c8f31f` (the Phase 4 primary's rows reproduce Phase 4 exactly). Full report:
`research/out/rl/phase5_report.md`. Every historical span was already seen by Phase 4.

- **Trade-less variants (BTC full span, 0.10%).** Wider band (2 round trips): turnover 47 -> 11 a year, but gross Sharpe 0.78 ->
  0.42, net 0.30. Minimum hold 2 days: turnover 25, gross 0.43, net 0.24. Neither keeps the edge on BTC (ETH: the 2-day hold
  keeps most of it, gross 0.92, net 0.71 vs 0.77). The tilt (1x spot core +- 0.5x agent): net Sharpe 0.83 vs spot buy-and-hold
  0.82 (Calmar 0.49 vs 0.48, max DD 80%), beats momentum on BTC; ETH 0.82 vs spot buy-and-hold 0.76 (beats it on every seed),
  momentum 0.83. Up to 2025-11-11 the loop's rules A and B (1.19, 1.32) stay ahead of the tilt (1.06).
- **Which readings carry the edge.** Not trend-following: the agent's position correlates +0.02 (BTC) / +0.09 (ETH) with the
  daily momentum rule and +0.04 / +0.10 with rule A; its daily returns correlate +0.47 with buy-and-hold (it is a long-biased
  timer: about 57% long, 10% short, 33% flat). The readings together carry most of the edge (Phase 3 inputs only: gross BTC
  0.42, ETH 0.56; readings only: 0.62, 0.88; both: 0.78, 1.11), but no single group clears the frozen bar (-0.20 gross on BTC
  AND ETH): flow / CVD / Coinbase matters a lot on ETH (-0.50) and not on BTC; dropping the trend readings changes nothing on
  BTC (+0.01). Occlusion of the trained primary agrees: it leans on flow, volatility regime, basis and levels, not on trend.

# Phase 6: flat scores weakly, long and short both ways

Owner, 12 Nov 2026: "the RL need to learn to profit from downtrend also. stay flat should have a weak scoring so the RL will
have more motivation to take long or short" (Mind 15's mandate: long or short almost all the time). Config
`configs/rl/phase6.yaml` (frozen before any Phase 6 number); code `engine15/rl/learn6.py` (shaped learner, `q_fold6`),
`phase6.py`, `report6.py`; tests `tests/rl/test_phase6.py`; report `research/out/rl/phase6_report.md`. Paper only; no
historical span is unseen for RL.

- **Reward (training only).** The literal "net return - beta x reference return" cannot change a decision with this agent (the
  reference's return does not depend on the action: every action's value moves by the same amount; tested). Registered
  instead: *missed opportunity* (the idle part of the book, 1 - |a|, pays beta x the daily momentum rule's return, long or
  short) and *flat-time charge* (the idle part pays lam x one round trip a day); beta / lam in {0.25, 0.5, 1} chosen per fold
  on the validation slice's real net Sharpe. Decisions and every result use the real net P&L and the full round-trip cost.
- **Symmetry.** Actions -1 .. +1 with equal costs; perp funding both ways (shorts receive positive funding); signed inputs.
- **'Do no harm'.** Three modes on the same trained models: flat (Phase 4), none, the trend reference (daily momentum).
- **Result (run `phase6_20261112T141341Z_30a4dd4f`, 0.10%, full span).** The pre-registered Phase 6 primary (missed
  opportunity + trend fallback) clears the frozen "clearly beats the Phase 4 primary" bar: BTC net Sharpe 0.87 (seeds 1.04,
  0.73, 0.82) vs 0.48, ETH 0.96 vs 0.77; vs buy-and-hold perp 0.64 / spot 0.82 and momentum 0.63 (ETH: 0.60 / 0.76 / 0.83).
  Time long / short / flat BTC 70 / 22 / 8% (Phase 4 primary 42 / 8 / 50%); short bars net +4.8% a year BTC, +10.5% ETH.
  Turnover 84 a year (Phase 4: 47), not "exploded" by the frozen check. Up to 2025-11-11 BTC 1.05 vs the loop's rules A 1.19
  and B 1.32. Downtrends: 2022 BTC -7.6% (buy-and-hold -65.7%, momentum -28.9%), ETH +4.8%; the current decline (from BTC's
  2025 high on 2025-10-06) BTC -23.0% (buy-and-hold -42.4%, momentum -2.2%), ETH +26.8%: it loses far less than holding but
  did not make money on BTC in either decline.
- **Caveat that matters.** Much of the gain is the trend fallback, i.e. the momentum rule in the 4-11 folds per seed whose
  validation Sharpe was under 0.5 (Phase 4 primary + trend fallback alone: BTC 0.98, ETH 0.82). That pattern (Phase 4 flat
  while momentum made large gains) was visible in Phase 4's per-fold table before Phase 6 was designed: hindsight risk. The
  shaped reward on its own helps on BTC (fallback flat: 0.68 vs 0.48; agent-fold returns about twice Phase 4's) and not on
  ETH (0.74 vs 0.77). 8 variants were tried. A second forward paper book is proposed, not wired in.

## Phase 6 forward paper books (wired 13 Nov 2026, owner's approval; NOT passed)

`engine15/playbook6.py` (books), `engine15/rl/forward6.py` (training, refit launcher; everything else is forward5's), tests
`tests/test_playbook6.py`. Both books run exactly like `p5_rlq` (record `research/out/rl/forward6/decisions_<book>_<asset>.jsonl`,
mean of seeds 0/1/2 through the Phase 3 risk manager, decided at a 15m close, filled at the next open, 0.10% a side, perp
funding both sides), BTC and ETH each $10,000 per book, go-live `REGISTERED` in `playbook6.py`.

- **`p6_mtrend`, the Phase 6 primary (m_trend).** `learn6.q_fold6` with r_missed (beta on validation, the frozen rule) on
  forward5's data and geometry; model files `research/out/rl/models6/live/model_<UTC>.json`; weekly refit
  `py -3 -m engine15.rl phase6-update` (below-normal, >= 1,500 MB free, shares phase5-update's lock and waits while Phase 5's
  refit is due). History 0.87 / 0.96 (BTC / ETH net Sharpe); 1 of 8 variants tried.
- **`p6_p4trend`, the control (p4_trend).** Phase 5's weekly Phase 4 primary models (no second copy) with the trend fallback.
  History 0.98 / 0.82. If p6_mtrend does no better than this, Phase 6's gain came from the fallback, not the reward.
- **'Do no harm' live = history's rule.** Per seed and coin, fixed when the model is trained: its own validation net Sharpe
  (last 6 months) under 0.5 -> the seed holds the trend reference (W = -10 x |a - mom_signal|, the formula of
  `phase5.oos_w(fallback="trend")`, through the same policy and risk manager). Each record carries `mode` per seed
  ("model" / "trend"). The trend fallback was chosen with hindsight (the pattern was visible in Phase 4's results).

## Health readings (21 Nov 2026; they decide nothing)

After the audit of 21 Nov 2026 (docs/CHARTER.md) the forward books carry two readings on the page, and the Telegram
bot reports them. No decision of any book uses them.

- **Who earned it** (`forward5.agent_split`, page field `split`). The book is the mean of three seeds, so its position
  is exactly the sum of the seeds on their own model and the seeds a 'do no harm' model keeps on the fallback (flat in
  Phase 5, the daily 30-day momentum position in Phase 6). The gross result is split along that line bar by bar;
  fees, spread, slippage and funding are the whole book's and are not split. agent + fallback - costs = the book's
  net result (checked in `tests/test_rl_health.py`).
- **Input drift** (`forward5.input_drift`, journal field `dz`, page field `input_drift`). For each new decision: the
  share of the model's inputs more than 3 training standard deviations from their training mean (seed 0's own mean
  and deviation for the coin). The page shows the last week's mean and the week before. Records written before
  21 Nov 2026 have no `dz`.
- **Telegram** (`telegram_notify.rl_fallback_update`, `rl_weekly_update`, `/rl`): one card when every seed of a book
  on a coin is on the fallback and one line when an agent is back; one weekly card when a new model is in use. The
  weekly card says "drifting" when the reading is above 5% and more than twice the week before: a flag to look,
  not a tested threshold.

## Momentum yardstick, interim read and the Lab block (22 Nov 2026; owner: "Run all above")

Three items from the RL audit of 21 Nov 2026. None changes a decision of any RL book; every RL book stays NOT passed.

- **Momentum yardstick `p8_mom`** (`engine15/playbook8.py`, tests `tests/test_playbook8.py`; registered in
  research/HYPOTHESES.md as a yardstick, not a hypothesis). BTC and ETH, $10,000 each from 2026-11-23 00:00 UTC, flat at
  the start. It calls `forward5.advance(fallback="trend")` with a stand-in model whose every seed carries the 'do no harm'
  flag (no weights), so every decision is `forward5.trend_w` on features3's `mom_signal` (`benchmarks.momentum(close,
  30, True)`: sign of the 30-day return, decided at the 00:00 UTC close, long or short), then the cost band,
  `policy3.decide`, the Phase 3 risk manager and the cost model through `forward5.risk_and_book`, with the Phase 6
  configuration. Same closes as the Phase 6 books (those the readings cover). Record:
  `research/out/rl/forward8/decisions_p8_mom_<asset>.jsonl`. Each coin's page state has `same_days`: each Phase 6 book's
  return from its equity marked at the yardstick's start to the last common close, beside the yardstick's and spot
  buy-and-hold's. Scoreboard row `p8_mom`; module `playbook8` in `reports.PLAYBOOK_MODULES` (after `playbook6`).
- **Interim read at 8 weeks** (`research/rl_interim_read.py`, test `tests/test_rl_interim_read.py`): `p5_rlq` on
  2027-01-07 04:30 UTC, `p6_mtrend` and `p6_p4trend` on 2027-01-08 03:00 UTC. It refuses to show anything before the
  date; on or after it prints the registered sentences only ("ahead of", "behind" or "level with", 1.0-point band).
- **The page's `rl_lab` block** (`engine15/rl_lab.py`, called by `export.merge` inside its own try/except; tests
  `tests/test_rl_lab.py`). Read only: built from the playbook page blocks, the decision records and the model files.

### The page's rl_lab block, schema 1 (for the site session)

`page.json` key `rl_lab` (null if it could not be built). Times are UTC strings "YYYY-MM-DD HH:MM"; money in USD on
$10,000 per coin; percentages are percent. A field may be null when the engine has not written it yet.

- `schema` (1), `generated_utc`, `not_passed` (always true), `note` (plain words: none of these books has passed; show it),
  `verdict_rule` (the 30-per-coin rule in words).
- `interim_read`: `books` {book: {`start_utc`, `read_utc`}}, `words`, `changes_nothing`, `registered`.
- `books` {`p5_rlq`, `p6_mtrend`, `p6_p4trend`}: each
  - `title`, `kind` ("agent" / "control"), `not_passed` (true), `started_utc`, `interim_read_utc`,
    `fallback_kind` ("flat" for p5_rlq, "momentum" for the Phase 6 books), `split` (the book over both coins:
    `agent_gross_usd`, `fallback_gross_usd`, `costs_usd`, `net_usd`, `coins`), `totals` (closed trades: `trades`, `won`,
    `win_rate_pct`, `net_usd`, `fees_usd`, `costs_usd`, ...),
  - `refits`: oldest first, [{`model_id`, `data_end_utc`, `created_utc`, `first_decision_utc`, `last_decision_utc`
    (decisions this book took with it; null if never used), `seeds_passed_validation` {coin: [seed numbers on their
    model: own validation net Sharpe at least 0.5]}, `val_net_sharpe` {coin: [per seed]}}],
  - `coins` {`BTCUSDT`, `ETHUSDT`}: each `status` ("running", or "stale" when no decision for 2 hours), `position`
    (e.g. "short 1.00x since 2026-11-15 23:45 UTC" or "flat"), `exposure`, `equity_usd`, `return_pct`,
    `bh_spot_equity_usd`, `bh_spot_return_pct` (spot buy-and-hold over the same days), `max_dd_pct`, `bh_max_dd_pct`,
    `closed_trades`, `trades_needed` (30), `progress_pct`, `seeds` (3), `seeds_on_model`, `seeds_on_fallback`,
    `fallback_kind`, `seed_modes` [{`seed`, `mode` ("model" / "fallback"), `since_utc` (first decision of the current
    run in that mode)}], `split` (`agent_gross_usd`, `fallback_gross_usd`, `costs_usd`, `net_usd`,
    `agent_seed_bars_pct`, `all_fallback_bars_pct`, `last_7d` {...}, `note`), `input_drift` (`z`, `last_7d_pct`,
    `decisions_7d`, `week_before_pct`, `note`), `model_id`, `model_data_end_utc`, `last_decision_utc`, `decisions`,
    `late_decisions` (recorded more than 30 minutes after the close), `late_share_pct`; the Phase 6 books also
    `momentum_yardstick` (`from_utc`, `to_utc`, `book_return_pct`, `yardstick_return_pct`, `bh_spot_return_pct`,
    `difference_pts`: the same days only; null before the yardstick has a close).
- `momentum_yardstick`: `book` ("p8_mom"), `for` (the two Phase 6 books), `started_utc`, `not_a_hypothesis` (true),
  `note`, `totals`, `coins` {coin: `status`, `position`, `equity_usd`, `return_pct`, `bh_spot_return_pct`, `max_dd_pct`,
  `closed_trades`, `daily_direction` (+1 / -1 now), `momentum_30d_pct`, `last_decision_utc`, `late_decisions`,
  `decisions`, `same_days` {Phase 6 book: as above}}.

Wording for the tab: these are forward paper books that have NOT passed; never present a number here as a proven result.
