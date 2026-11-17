# RL loop round 4: the committee at 1.25, and a four-vote committee

Generated 2026-11-17 03:40 UTC. Paper only. Rules: `research/rl_loop/LOOP_RL.md` (frozen 13 Nov 2026 04:10 UTC; round 4 registered 17 Nov 2026 03:21 UTC, before any round-4 code was written). Seeds 0, 1, 2; 25 walk-forward folds, out of sample 2020-10-01 .. 2026-11-11. Both variants are execution-only: R4-a uses Phase 6's trained `m_trend` models with round 2's `r_missed_spot`; R4-b uses those and round 3's `r_missed_longflat`; nothing was retrained. **RL variants tried, cumulative: 25** (Phase 6's 8 + round 1's 5 + round 2's 6 + round 3's 4 + round 4's 2). Evaluation compute: 2.1 min (host `research server (Linux)`).

**Honesty.** No historical span is unseen for RL (Phase 4-6 scored every window; this loop was designed after Phase 6's and rounds 1-3's per-fold results; the trend fallback was chosen with hindsight). A pass would not be proof of an edge, only a proposal for a forward paper book, confirmed at 30 forward trades. Spot longs = long part up to 1x as spot (no funding); exposure above 1x and shorts are perp. Leverage (R4-a and R3-b* request 1.25) raises return and drawdown together and leaves Sharpe unchanged only before costs; after fees, slippage and funding on the part above 1x it lowers Sharpe unless the extra exposure sits where the edge is larger.

**Where it ran, and the inputs.** Rounds 1-3 ran on the laptop; its RL input cache and evidence store were deleted in the owner-approved cleanup. Round 4 ran on the research server: input cache `research/out/rl_loop/r4_work/cache` rebuilt by the unchanged `engine15.rl.pool4.prepare` from the server's bar and funding files (cut at 2026-11-11 11:30) and the server's evidence store (read only); trained fold models `research/out/rl_loop/r4_work/inputs/models6/b6a25c5d`, `research/out/rl_loop/r4_work/inputs/models_r2`, `research/out/rl_loop/r4_work/inputs/models_r3` and Phase 6's saved run `research/out/rl_loop/r4_work/inputs/phase6_full.json` copied from the laptop.
- Readings snapshot BTCUSDT: 275935 rows, 2019-01-01 00:00:00+00:00 .. 2026-11-17 03:00:00+00:00, evidence store created 2026-11-16T09:49:23Z, read 2026-11-17 03:34:02 UTC.
- Readings snapshot ETHUSDT: 275935 rows, 2019-01-01 00:00:00+00:00 .. 2026-11-17 03:00:00+00:00, evidence store created 2026-11-16T09:49:25Z, read 2026-11-17 03:34:04 UTC.

**Gate, stage 1 (run 2026-11-17 03:35 UTC, before any round-4 variant was computed): PASSED.**
- Phase 6 primary BTCUSDT: return +458.6076% (saved +458.6076%), Sharpe 0.8655 (saved 0.8655); max per-seed difference: return 0.00e+00, Sharpe 0.00e+00
- Phase 6 primary ETHUSDT: return +709.1418% (saved +709.1418%), Sharpe 0.9619 (saved 0.9619); max per-seed difference: return 2.66e-15, Sharpe 7.77e-16
- R3-b* BTCUSDT: return +1427.8552% (round 3 saved +1427.8552%, relative difference 0.00e+00), Sharpe 1.1385 (saved 1.1385, difference 0.00e+00); max per-seed difference: return 0.00e+00, Sharpe 0.00e+00 -> ok
- R3-b* ETHUSDT: return +1644.3249% (round 3 saved +1644.3249%, relative difference 0.00e+00), Sharpe 1.1292 (saved 1.1292, difference 4.44e-16); max per-seed difference: return 0.00e+00, Sharpe 6.66e-16 -> ok
- R3-c* BTCUSDT: return +710.0125% (round 3 saved +710.0125%, relative difference 0.00e+00), Sharpe 1.0863 (saved 1.0863, difference 0.00e+00); max per-seed difference: return 0.00e+00, Sharpe 0.00e+00 -> ok
- R3-c* ETHUSDT: return +773.4421% (round 3 saved +773.4421%, relative difference 1.03e-15), Sharpe 1.0341 (saved 1.0341, difference 2.22e-16); max per-seed difference: return 2.66e-14, Sharpe 4.44e-16 -> ok
- R3-d* BTCUSDT: return +850.7985% (round 3 saved +850.7985%, relative difference 0.00e+00), Sharpe 1.1111 (saved 1.1111, difference 0.00e+00); max per-seed difference: return 0.00e+00, Sharpe 0.00e+00 -> ok
- R3-d* ETHUSDT: return +669.8857% (round 3 saved +669.8857%, relative difference 0.00e+00), Sharpe 0.9294 (saved 0.9294, difference 4.44e-16); max per-seed difference: return 0.00e+00, Sharpe 5.55e-16 -> ok

**Reproduction check (rule 3), this run.** Phase 6 primary through this harness: BTC +458.6%, Sharpe 0.866 (Phase 6: +458.6%, 0.87); ETH +709.1%, Sharpe 0.962 (+709.1%, 0.96); differences vs Phase 6's saved run (BTC seed mean): return 0.00e+00, Sharpe 0.00e+00 -> OK. Round 3's R3-b / R3-c / R3-d against round 3's saved results in this run: OK (largest relative return difference 1.03e-15, largest Sharpe difference 4.44e-16). risk_run vs risk3.apply max |difference|: BTCUSDT_fee_0.10% 0.0e+00, BTCUSDT_fee_0.05% 0.0e+00, ETHUSDT_fee_0.10% 0.0e+00, ETHUSDT_fee_0.05% 0.0e+00.

Floors applied (max of the quoted value and the unrounded Phase 6 seed mean): BTC full 0.8700, BTC to 2025-11-11 1.0505, ETH full 0.9619.

## Verdict

**No pass in round 4.**
- R4-a committee_riskoff_125: R3-c's committee (flat on 2 of 3 bearish) at 1.25: 20 of 21 rules; fails `S4_significant`.
- R4-b committee4_riskoff: flat on 3 of 4 bearish votes (3 agents + trend), 1x: 16 of 21 rules; fails `T_mean_cagr_gt_bh`, `T4_dev_return_gt_bh`, `T4_dev_mean_cagr_gt_bh`, `S1_fold_share_ge_half`, `S4_significant`.

## Headline: BTC and ETH, full span, 0.10% a side, seed means, against spot buy-and-hold

| Variant | BTC return | BTC mean CAGR | BTC Sharpe (seeds) | BTC max DD (worst seed) | BTC trades/yr (max seed) | BTC to 2025-11-11: return / Sharpe | ETH return | ETH Sharpe | ETH max DD (worst) | Rules met |
|---|---|---|---|---|---|---|---|---|---|---|
| Phase 6 primary m_trend, reproduced (perp, as Phase 6) | +458.6% | +31.3% | 0.87 (1.04, 0.73, 0.82) | 47% (52%) | 178 (210) | +543.3% / 1.05 | +709.1% | 0.96 | 62% (67%) | 10 / 21 |
| R3-b core_riskoff_125 (round 3, comparison) | +1427.9% | +55.3% | 1.14 (1.23, 1.19, 1.00) | 57% (60%) | 44 (49) | +1622.2% / 1.33 | +1644.3% | 1.13 | 55% (60%) | 19 / 21 |
| R3-c committee_riskoff (round 3, comparison) | +710.0% | +40.3% | 1.09 (1.15, 1.17, 0.94) | 52% (56%) | 54 (61) | +745.6% / 1.26 | +773.4% | 1.03 | 47% (52%) | 18 / 21 |
| R3-d retrain_longflat_riskoff (round 3, comparison) | +850.8% | +44.1% | 1.11 (1.01, 1.16, 1.16) | 47% (47%) | 47 (48) | +968.9% / 1.31 | +669.9% | 0.93 | 56% (61%) | 18 / 21 |
| R4-a committee_riskoff_125: R3-c's committee (flat on 2 of 3 bearish) at 1.25 | +1474.2% | +56.0% | 1.17 (1.21, 1.28, 1.03) | 60% (61%) | 57 (64) | +1551.6% / 1.35 | +1263.2% | 1.07 | 53% (59%) | 20 / 21 |
| R4-b committee4_riskoff: flat on 3 of 4 bearish votes (3 agents + trend), 1x | +592.6% | +36.7% | 1.01 (1.10, 1.06, 0.86) | 52% (55%) | 61 (72) | +651.8% / 1.19 | +995.7% | 1.09 | 51% (55%) | 16 / 21 |
| BTC spot buy-and-hold | +583.9% | +36.9% | 0.82 | 77% | 0 | +879.7% / 1.03 | | | | |
| ETH spot buy-and-hold | +470.6% | +33.0% | 0.76 | 81% | 0 | +889.1% / 0.96 | | | | |

REF = Phase 6 as it is (perp accounting); R3-b*, R3-c* and R3-d* (round 3) recomputed in this run: the gate's rows, shown for comparison, graded here with N = 25 for information, not round-4 variants and not counted again.

## Every rule, every variant (PASS / fail)

| Rule | REF | R3-b* | R3-c* | R3-d* | R4-a | R4-b |
|---|---|---|---|---|---|---|
| `T_return_gt_bh` | fail | PASS | PASS | PASS | PASS | PASS |
| `T_mean_cagr_gt_bh` | fail | PASS | PASS | PASS | PASS | fail |
| `T_sharpe_ge_floor` | fail | PASS | PASS | PASS | PASS | PASS |
| `T_sharpe_gt_bh` | PASS | PASS | PASS | PASS | PASS | PASS |
| `T_every_seed_sharpe_gt_bh` | fail | PASS | PASS | PASS | PASS | PASS |
| `T_every_seed_dd_le_bh` | PASS | PASS | PASS | PASS | PASS | PASS |
| `T4_dev_return_gt_bh` | fail | PASS | fail | PASS | PASS | fail |
| `T4_dev_mean_cagr_gt_bh` | fail | PASS | fail | PASS | PASS | fail |
| `T4_dev_sharpe_ge_floor` | PASS | PASS | PASS | PASS | PASS | PASS |
| `T4_dev_sharpe_gt_bh` | PASS | PASS | PASS | PASS | PASS | PASS |
| `T4_dev_every_seed_sharpe_gt_bh` | fail | PASS | PASS | PASS | PASS | PASS |
| `T4_dev_every_seed_dd_le_bh` | PASS | PASS | PASS | PASS | PASS | PASS |
| `S1_fold_share_ge_half` | fail | fail | PASS | fail | PASS | fail |
| `S2_no_fee_only_at_0.05` | PASS | PASS | PASS | PASS | PASS | PASS |
| `S3_trades_le_100_every_seed` | fail | PASS | PASS | PASS | PASS | PASS |
| `S3_turnover_le_100_every_seed` | PASS | PASS | PASS | PASS | PASS | PASS |
| `S4_significant` | fail | fail | fail | fail | fail | fail |
| `E1_eth_sharpe_ge_floor` | fail | PASS | PASS | fail | PASS | PASS |
| `E2_eth_return_gt_bh` | PASS | PASS | PASS | PASS | PASS | PASS |
| `E2_eth_mean_cagr_gt_bh` | PASS | PASS | PASS | PASS | PASS | PASS |
| `E3_eth_every_seed_dd_le_bh` | PASS | PASS | PASS | PASS | PASS | PASS |
| rules met | 10 / 21 | 19 / 21 | 18 / 21 | 18 / 21 | 20 / 21 | 16 / 21 |
| fold share (seed-mean per fold), full / to 2025-11-11 | 40% / 38% | 40% / 33% | 52% / 43% | 40% / 33% | 56% / 48% | 44% / 33% |
| fold share by seed 0 / 1 / 2 | 48% / 44% / 40% | 44% / 44% / 36% | 48% / 48% / 44% | 48% / 52% / 48% | 48% / 60% / 52% | 40% / 48% / 36% |
| seed-mean book Sharpe - B&H (p; threshold 0.00200) | +0.23 (p 0.2972) | +0.40 (p 0.0438) | +0.43 (p 0.0427) | +0.44 (p 0.0437) | +0.46 (p 0.0358) | +0.33 (p 0.0930) |
| bootstrap standard error of that gap | 0.43 | 0.23 | 0.25 | 0.26 | 0.25 | 0.25 |
| Sharpe edge needed at that threshold / with the strategy loop's 1,910 added | 1.25 / 1.76 | 0.67 / 0.95 | 0.71 / 1.00 | 0.74 / 1.04 | 0.73 / 1.02 | 0.71 / 1.00 |
| daily correlation with B&H / tracking error a year (seed-mean book) | 0.42 / 53% | 0.84 / 31% | 0.81 / 35% | 0.82 / 34% | 0.80 / 34% | 0.82 / 34% |
| deflated-Sharpe probability (N = 25) | 0.632 | 0.811 | 0.787 | 0.791 | 0.843 | 0.715 |
| reported, not a rule: book Sharpe - B&H, first half, to 2023-06-07 (p; book return vs B&H) | +0.40 (p 0.292; +185% vs +152%) | +0.60 (p 0.057; +349% vs +152%) | +0.66 (p 0.063; +232% vs +152%) | +0.73 (p 0.043; +290% vs +152%) | +0.52 (p 0.113; +266% vs +152%) | +0.60 (p 0.078; +227% vs +152%) |
| reported, not a rule: book Sharpe - B&H, second half, from 2023-06-07 (p; book return vs B&H) | +0.04 (p 0.470; +98% vs +172%) | +0.18 (p 0.244; +237% vs +172%) | +0.18 (p 0.249; +146% vs +172%) | +0.14 (p 0.302; +144% vs +172%) | +0.36 (p 0.088; +329% vs +172%) | +0.04 (p 0.445; +111% vs +172%) |

Bootstrap on daily returns of the seed-mean book (per-bar mean of the three seeds' net returns) against spot buy-and-hold, BTC full span; Bonferroni over 25 RL variants (p <= 0.00200; with the strategy loop's 1,910 added: 2.6e-05). REF and the comparison rows are graded here with N = 25 for information only.

## Fold by fold, BTC, 0.10%: seed-mean Sharpe of each fold vs spot buy-and-hold's (* = above: counts for S1)

| Fold | B&H Sharpe | B&H return | REF | R3-b* | R3-c* | R3-d* | R4-a | R4-b |
|---|---|---|---|---|---|---|---|---|
| 0 | 6.33 | +168% | 5.94 | 6.47* | 6.92* | 6.73* | 6.81* | 6.69* |
| 1 | 3.08 | +103% | 1.09 | 2.84 | 4.09* | 2.96 | 3.98* | 3.53* |
| 2 | -1.42 | -40% | -0.93* | -1.94 | -1.79 | -1.83 | -1.83 | -1.98 |
| 3 | 1.66 | +25% | 1.27 | 1.57 | 1.92* | 1.54 | 1.59 | 2.07* |
| 4 | 0.65 | +6% | -0.05 | 0.45 | 0.13 | 0.96* | 0.22 | -0.07 |
| 5 | 0.24 | -2% | -0.33 | 0.52* | 0.05 | -1.17 | 0.46* | -0.01 |
| 6 | -3.95 | -56% | 1.38* | -2.86* | -2.85* | -3.26* | -2.88* | -2.85* |
| 7 | 0.15 | -3% | 0.32* | 0.36* | 0.31* | 0.43* | 0.36* | 0.38* |
| 8 | -1.10 | -15% | -2.48 | -3.15 | -2.99 | -2.99 | -3.42 | -2.99 |
| 9 | 4.46 | +72% | 2.79 | 4.13 | 4.23 | 4.23 | 4.10 | 4.23 |
| 10 | 0.87 | +7% | 0.89* | 1.32* | 1.14* | 0.75 | 1.11* | 1.03* |
| 11 | -1.11 | -12% | -0.50* | -1.00* | -1.56 | -1.42 | -1.08* | -1.49 |
| 12 | 4.24 | +57% | 4.02 | 4.19 | 4.24 | 4.24 | 4.19 | 4.24 |
| 13 | 3.91 | +69% | 2.73 | 3.54 | 3.65 | 3.70 | 3.66 | 3.91 |
| 14 | -0.82 | -12% | -1.53 | -1.66 | -1.38 | -0.89 | -1.72 | -0.88 |
| 15 | 0.34 | +1% | -1.11 | -0.24 | -0.40 | 0.57* | 0.21 | -0.86 |
| 16 | 3.31 | +48% | 3.24 | 3.26 | 3.57* | 3.30 | 3.58* | 3.24 |
| 17 | -0.64 | -12% | -0.06* | -1.15 | -0.45* | -1.88 | -0.38* | -0.99 |
| 18 | 2.72 | +30% | 1.30 | 2.01 | 2.17 | 3.57* | 2.30 | 2.02 |
| 19 | 0.97 | +6% | 1.60* | 1.19* | 1.26* | 1.17* | 1.07* | 1.56* |
| 20 | -1.97 | -23% | 0.31* | -0.68* | -0.57* | -0.65* | -0.61* | -0.64* |
| 21 | -1.58 | -22% | -1.93 | -1.71 | -1.24* | -2.49 | -1.23* | -1.45* |
| 22 | -1.26 | -14% | 1.93* | 0.49* | 0.53* | 0.50* | 0.55* | 0.47* |
| 23 | 4.23 | +43% | -2.44 | 1.65 | 1.69 | 1.69 | 1.65 | 1.69 |
| 24 | -2.96 | -11% | -0.65* | -1.88* | -1.86* | -2.41* | -1.88* | -2.00* |
| folds above | | | 10 / 25 | 10 / 25 | 13 / 25 | 10 / 25 | 14 / 25 | 11 / 25 |
| of which bull folds, B&H fold Sharpe > 1 (9) | | | 0 | 1 | 4 | 2 | 3 | 3 |
| of which flat-ish folds, 0 to 1 (6) | | | 3 | 4 | 3 | 4 | 4 | 3 |
| of which bear folds, below 0 (10) | | | 7 | 5 | 6 | 4 | 7 | 5 |

## BTCUSDT, 2020-10-01 .. 2026-11-11, 0.10% a side

| Strategy | Net return | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Funding/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Phase 6 primary m_trend, reproduced (perp, as Phase 6), mean of 3 seeds** | +458.6% | +31.3% | 0.87 | 1.23 | 47% | 0.68 | 84 | 178 | 167 | 15.4% | 3.1% | 1.24 | 0.428% |
| &nbsp;&nbsp;seed 0 | +748.7% | +41.9% | 1.04 | 1.49 | 43% | 0.98 | 77 | 152 | 181 | 14.6% | 3.5% | 1.39 | 0.555% |
| &nbsp;&nbsp;seed 1 | +262.3% | +23.4% | 0.73 | 1.04 | 52% | 0.45 | 89 | 210 | 157 | 16.1% | 2.8% | 1.14 | 0.336% |
| &nbsp;&nbsp;seed 2 | +364.9% | +28.6% | 0.82 | 1.17 | 46% | 0.62 | 85 | 173 | 164 | 15.4% | 3.0% | 1.20 | 0.395% |
| **R3-b core_riskoff_125 (round 3, comparison), mean of 3 seeds** | +1427.9% | +55.3% | 1.14 | 1.61 | 57% | 0.97 | 36 | 44 | 349 | 6.0% | 1.0% | 1.26 | 1.326% |
| &nbsp;&nbsp;seed 0 | +1812.0% | +62.0% | 1.23 | 1.74 | 55% | 1.13 | 35 | 41 | 366 | 6.0% | 1.0% | 1.35 | 1.462% |
| &nbsp;&nbsp;seed 1 | +1609.8% | +59.1% | 1.19 | 1.69 | 57% | 1.04 | 37 | 49 | 312 | 6.2% | 0.9% | 1.32 | 1.344% |
| &nbsp;&nbsp;seed 2 | +861.7% | +44.8% | 1.00 | 1.41 | 60% | 0.74 | 34 | 43 | 368 | 5.9% | 1.1% | 1.12 | 1.172% |
| **R3-c committee_riskoff (round 3, comparison), mean of 3 seeds** | +710.0% | +40.3% | 1.09 | 1.54 | 52% | 0.78 | 37 | 54 | 239 | 5.4% | 0.0% | 1.23 | 1.012% |
| &nbsp;&nbsp;seed 0 | +800.8% | +43.2% | 1.15 | 1.62 | 47% | 0.92 | 35 | 50 | 257 | 5.2% | 0.0% | 1.28 | 1.111% |
| &nbsp;&nbsp;seed 1 | +865.7% | +44.9% | 1.17 | 1.66 | 56% | 0.80 | 40 | 61 | 216 | 6.0% | 0.0% | 1.33 | 1.017% |
| &nbsp;&nbsp;seed 2 | +463.6% | +32.7% | 0.94 | 1.33 | 53% | 0.62 | 35 | 52 | 244 | 5.1% | 0.0% | 1.08 | 0.908% |
| **R3-d retrain_longflat_riskoff (round 3, comparison), mean of 3 seeds** | +850.8% | +44.1% | 1.11 | 1.57 | 47% | 0.95 | 34 | 47 | 289 | 4.8% | 0.0% | 1.23 | 1.157% |
| &nbsp;&nbsp;seed 0 | +595.7% | +37.3% | 1.01 | 1.43 | 47% | 0.79 | 33 | 46 | 290 | 4.6% | 0.0% | 1.13 | 1.055% |
| &nbsp;&nbsp;seed 1 | +1040.8% | +48.9% | 1.16 | 1.63 | 46% | 1.07 | 35 | 48 | 295 | 5.0% | 0.0% | 1.28 | 1.229% |
| &nbsp;&nbsp;seed 2 | +915.8% | +46.1% | 1.16 | 1.65 | 47% | 0.98 | 35 | 47 | 281 | 4.8% | 0.0% | 1.29 | 1.187% |
| **R4-a committee_riskoff_125: R3-c's committee (flat on 2 of 3 bearish) at 1.25, mean of 3 seeds** | +1474.2% | +56.0% | 1.17 | 1.67 | 60% | 0.93 | 45 | 57 | 239 | 7.6% | 1.0% | 1.34 | 1.081% |
| &nbsp;&nbsp;seed 0 | +1599.9% | +58.9% | 1.21 | 1.72 | 61% | 0.96 | 43 | 53 | 257 | 7.4% | 1.1% | 1.37 | 1.169% |
| &nbsp;&nbsp;seed 1 | +1947.4% | +63.8% | 1.28 | 1.82 | 59% | 1.08 | 49 | 64 | 216 | 8.2% | 1.0% | 1.46 | 1.108% |
| &nbsp;&nbsp;seed 2 | +875.3% | +45.1% | 1.03 | 1.45 | 60% | 0.76 | 43 | 54 | 244 | 7.4% | 1.0% | 1.19 | 0.964% |
| **R4-b committee4_riskoff: flat on 3 of 4 bearish votes (3 agents + trend), 1x, mean of 3 seeds** | +592.6% | +36.7% | 1.01 | 1.42 | 52% | 0.71 | 40 | 61 | 226 | 6.0% | 0.0% | 1.16 | 0.870% |
| &nbsp;&nbsp;seed 0 | +706.2% | +40.7% | 1.10 | 1.55 | 49% | 0.83 | 39 | 56 | 237 | 5.7% | 0.0% | 1.25 | 0.971% |
| &nbsp;&nbsp;seed 1 | +702.4% | +40.6% | 1.06 | 1.50 | 55% | 0.73 | 46 | 72 | 198 | 6.9% | 0.0% | 1.24 | 0.842% |
| &nbsp;&nbsp;seed 2 | +369.1% | +28.8% | 0.86 | 1.21 | 51% | 0.57 | 36 | 56 | 242 | 5.3% | 0.0% | 1.00 | 0.799% |
| Buy-and-hold (spot) | +583.9% | +36.9% | 0.82 | 1.17 | 77% | 0.48 | 0 | 0 | 53579 | 0.0% | 0.0% | 0.83 | > 5% |
| Buy-and-hold (perp) | +249.3% | +22.7% | 0.64 | 0.91 | 79% | 0.29 | 0 | 0 | 53579 | 11.0% | 11.0% | 0.83 | > 5% |
| Momentum (daily 30-day, long/short, perp) | +237.7% | +22.0% | 0.63 | 0.89 | 64% | 0.34 | 62 | 31 | 281 | 14.3% | 6.1% | 0.87 | 0.418% |

### BTCUSDT, 0.05% a side

| Strategy | Net return | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Funding/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Phase 6 primary m_trend, reproduced (perp, as Phase 6), mean of 3 seeds** | +638.5% | +37.5% | 0.98 | 1.39 | 44% | 0.87 | 84 | 177 | 167 | 11.2% | 3.1% | 1.25 | 0.433% |
| &nbsp;&nbsp;seed 0 | +1020.9% | +48.5% | 1.15 | 1.64 | 41% | 1.17 | 76 | 148 | 181 | 10.7% | 3.5% | 1.41 | 0.568% |
| &nbsp;&nbsp;seed 1 | +416.1% | +30.8% | 0.87 | 1.24 | 44% | 0.69 | 88 | 198 | 157 | 11.5% | 2.8% | 1.16 | 0.356% |
| &nbsp;&nbsp;seed 2 | +478.4% | +33.2% | 0.91 | 1.29 | 45% | 0.74 | 88 | 184 | 164 | 11.4% | 3.0% | 1.19 | 0.375% |
| **R3-b core_riskoff_125 (round 3, comparison), mean of 3 seeds** | +1601.0% | +57.9% | 1.17 | 1.66 | 57% | 1.03 | 36 | 44 | 349 | 4.3% | 1.0% | 1.26 | 1.312% |
| &nbsp;&nbsp;seed 0 | +2083.5% | +65.6% | 1.27 | 1.80 | 54% | 1.22 | 36 | 41 | 366 | 4.2% | 1.0% | 1.36 | 1.457% |
| &nbsp;&nbsp;seed 1 | +1785.5% | +61.6% | 1.22 | 1.73 | 56% | 1.10 | 37 | 49 | 312 | 4.4% | 0.9% | 1.31 | 1.329% |
| &nbsp;&nbsp;seed 2 | +934.0% | +46.5% | 1.02 | 1.44 | 60% | 0.78 | 35 | 42 | 368 | 4.2% | 1.1% | 1.10 | 1.149% |
| **R3-c committee_riskoff (round 3, comparison), mean of 3 seeds** | +807.5% | +42.8% | 1.13 | 1.60 | 51% | 0.84 | 37 | 54 | 239 | 3.6% | 0.0% | 1.23 | 1.004% |
| &nbsp;&nbsp;seed 0 | +904.6% | +45.8% | 1.19 | 1.69 | 47% | 0.98 | 36 | 50 | 257 | 3.4% | 0.0% | 1.29 | 1.107% |
| &nbsp;&nbsp;seed 1 | +1009.5% | +48.2% | 1.23 | 1.74 | 55% | 0.88 | 41 | 61 | 216 | 4.0% | 0.0% | 1.33 | 1.016% |
| &nbsp;&nbsp;seed 2 | +508.5% | +34.3% | 0.98 | 1.37 | 52% | 0.66 | 35 | 52 | 244 | 3.4% | 0.0% | 1.07 | 0.888% |
| **R3-d retrain_longflat_riskoff (round 3, comparison), mean of 3 seeds** | +960.2% | +46.6% | 1.15 | 1.63 | 45% | 1.03 | 35 | 47 | 289 | 3.1% | 0.0% | 1.23 | 1.146% |
| &nbsp;&nbsp;seed 0 | +661.9% | +39.4% | 1.05 | 1.48 | 46% | 0.85 | 33 | 46 | 290 | 3.0% | 0.0% | 1.12 | 1.044% |
| &nbsp;&nbsp;seed 1 | +1168.0% | +51.5% | 1.19 | 1.69 | 45% | 1.14 | 36 | 48 | 295 | 3.3% | 0.0% | 1.27 | 1.212% |
| &nbsp;&nbsp;seed 2 | +1050.6% | +49.1% | 1.21 | 1.71 | 44% | 1.10 | 35 | 47 | 281 | 3.1% | 0.0% | 1.29 | 1.181% |
| **R4-a committee_riskoff_125: R3-c's committee (flat on 2 of 3 bearish) at 1.25, mean of 3 seeds** | +1683.6% | +59.2% | 1.22 | 1.73 | 59% | 1.01 | 45 | 57 | 239 | 5.4% | 1.0% | 1.33 | 1.073% |
| &nbsp;&nbsp;seed 0 | +1866.5% | +62.7% | 1.26 | 1.79 | 60% | 1.05 | 43 | 52 | 257 | 5.2% | 1.1% | 1.37 | 1.170% |
| &nbsp;&nbsp;seed 1 | +2175.9% | +66.7% | 1.32 | 1.87 | 58% | 1.16 | 49 | 64 | 216 | 5.8% | 1.0% | 1.44 | 1.088% |
| &nbsp;&nbsp;seed 2 | +1008.4% | +48.2% | 1.07 | 1.52 | 59% | 0.82 | 43 | 54 | 244 | 5.2% | 1.0% | 1.18 | 0.961% |
| **R4-b committee4_riskoff: flat on 3 of 4 bearish votes (3 agents + trend), 1x, mean of 3 seeds** | +697.3% | +39.9% | 1.07 | 1.51 | 51% | 0.78 | 40 | 61 | 226 | 4.0% | 0.0% | 1.17 | 0.875% |
| &nbsp;&nbsp;seed 0 | +816.3% | +43.6% | 1.15 | 1.63 | 48% | 0.90 | 39 | 56 | 237 | 3.8% | 0.0% | 1.25 | 0.970% |
| &nbsp;&nbsp;seed 1 | +830.5% | +44.0% | 1.13 | 1.59 | 55% | 0.81 | 46 | 72 | 198 | 4.6% | 0.0% | 1.24 | 0.841% |
| &nbsp;&nbsp;seed 2 | +445.1% | +31.9% | 0.92 | 1.30 | 51% | 0.62 | 36 | 55 | 242 | 3.5% | 0.0% | 1.02 | 0.816% |
| Buy-and-hold (spot) | +584.3% | +36.9% | 0.83 | 1.17 | 77% | 0.48 | 0 | 0 | 53579 | 0.0% | 0.0% | 0.83 | > 5% |
| Buy-and-hold (perp) | +249.5% | +22.7% | 0.64 | 0.91 | 79% | 0.29 | 0 | 0 | 53579 | 11.0% | 11.0% | 0.83 | > 5% |
| Momentum (daily 30-day, long/short, perp) | +308.7% | +25.9% | 0.68 | 0.97 | 61% | 0.42 | 62 | 31 | 281 | 11.2% | 6.1% | 0.87 | 0.418% |

### BTCUSDT, up to 2025-11-11, 0.10%

| Strategy | Net return | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Funding/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Phase 6 primary m_trend, reproduced (perp, as Phase 6), mean of 3 seeds** | +543.3% | +42.8% | 1.05 | 1.50 | 47% | 0.93 | 84 | 178 | 155 | 16.1% | 3.5% | 1.44 | 0.529% |
| &nbsp;&nbsp;seed 0 | +814.6% | +54.1% | 1.22 | 1.73 | 43% | 1.27 | 76 | 153 | 171 | 15.2% | 3.9% | 1.57 | 0.666% |
| &nbsp;&nbsp;seed 1 | +319.8% | +32.4% | 0.89 | 1.27 | 52% | 0.62 | 92 | 216 | 142 | 17.3% | 3.2% | 1.32 | 0.403% |
| &nbsp;&nbsp;seed 2 | +495.5% | +41.7% | 1.04 | 1.48 | 46% | 0.91 | 83 | 166 | 153 | 15.9% | 3.4% | 1.42 | 0.517% |
| **R3-b core_riskoff_125 (round 3, comparison), mean of 3 seeds** | +1622.2% | +73.4% | 1.33 | 1.88 | 57% | 1.29 | 34 | 45 | 359 | 6.0% | 1.1% | 1.45 | 1.707% |
| &nbsp;&nbsp;seed 0 | +2042.5% | +82.1% | 1.44 | 2.03 | 55% | 1.50 | 33 | 40 | 384 | 5.8% | 1.1% | 1.55 | 1.915% |
| &nbsp;&nbsp;seed 1 | +1802.7% | +77.9% | 1.38 | 1.95 | 57% | 1.37 | 38 | 52 | 304 | 6.6% | 1.0% | 1.51 | 1.604% |
| &nbsp;&nbsp;seed 2 | +1021.4% | +60.4% | 1.18 | 1.66 | 60% | 1.00 | 31 | 42 | 390 | 5.7% | 1.2% | 1.29 | 1.603% |
| **R3-c committee_riskoff (round 3, comparison), mean of 3 seeds** | +745.6% | +51.2% | 1.26 | 1.78 | 52% | 0.99 | 38 | 58 | 229 | 5.6% | 0.0% | 1.41 | 1.194% |
| &nbsp;&nbsp;seed 0 | +845.1% | +55.1% | 1.34 | 1.89 | 47% | 1.17 | 36 | 53 | 248 | 5.3% | 0.0% | 1.48 | 1.326% |
| &nbsp;&nbsp;seed 1 | +893.6% | +56.7% | 1.34 | 1.90 | 56% | 1.01 | 43 | 67 | 202 | 6.5% | 0.0% | 1.51 | 1.146% |
| &nbsp;&nbsp;seed 2 | +498.0% | +41.9% | 1.10 | 1.55 | 53% | 0.80 | 34 | 55 | 237 | 5.2% | 0.0% | 1.24 | 1.110% |
| **R3-d retrain_longflat_riskoff (round 3, comparison), mean of 3 seeds** | +968.9% | +58.6% | 1.31 | 1.86 | 47% | 1.26 | 32 | 46 | 302 | 4.6% | 0.0% | 1.42 | 1.515% |
| &nbsp;&nbsp;seed 0 | +767.6% | +52.6% | 1.25 | 1.76 | 47% | 1.12 | 31 | 45 | 302 | 4.4% | 0.0% | 1.36 | 1.444% |
| &nbsp;&nbsp;seed 1 | +1146.5% | +63.8% | 1.35 | 1.90 | 46% | 1.39 | 34 | 48 | 302 | 4.9% | 0.0% | 1.46 | 1.539% |
| &nbsp;&nbsp;seed 2 | +992.5% | +59.6% | 1.34 | 1.90 | 47% | 1.27 | 32 | 46 | 303 | 4.5% | 0.0% | 1.45 | 1.563% |
| **R4-a committee_riskoff_125: R3-c's committee (flat on 2 of 3 bearish) at 1.25, mean of 3 seeds** | +1551.6% | +72.1% | 1.35 | 1.92 | 60% | 1.20 | 46 | 61 | 229 | 8.0% | 1.1% | 1.52 | 1.276% |
| &nbsp;&nbsp;seed 0 | +1705.9% | +76.1% | 1.40 | 1.99 | 61% | 1.24 | 43 | 55 | 248 | 7.6% | 1.2% | 1.56 | 1.395% |
| &nbsp;&nbsp;seed 1 | +1944.0% | +80.4% | 1.45 | 2.06 | 59% | 1.37 | 51 | 70 | 202 | 8.9% | 1.1% | 1.63 | 1.241% |
| &nbsp;&nbsp;seed 2 | +1005.0% | +59.9% | 1.21 | 1.71 | 60% | 1.01 | 43 | 57 | 237 | 7.5% | 1.1% | 1.37 | 1.193% |
| **R4-b committee4_riskoff: flat on 3 of 4 bearish votes (3 agents + trend), 1x, mean of 3 seeds** | +651.8% | +47.7% | 1.19 | 1.67 | 52% | 0.93 | 41 | 65 | 218 | 6.2% | 0.0% | 1.34 | 1.054% |
| &nbsp;&nbsp;seed 0 | +760.7% | +52.3% | 1.29 | 1.82 | 49% | 1.07 | 39 | 59 | 230 | 5.8% | 0.0% | 1.44 | 1.179% |
| &nbsp;&nbsp;seed 1 | +770.5% | +52.7% | 1.24 | 1.75 | 55% | 0.95 | 49 | 79 | 186 | 7.5% | 0.0% | 1.43 | 0.963% |
| &nbsp;&nbsp;seed 2 | +424.1% | +38.2% | 1.03 | 1.44 | 51% | 0.76 | 35 | 57 | 238 | 5.3% | 0.0% | 1.17 | 1.019% |
| Buy-and-hold (spot) | +879.7% | +56.2% | 1.03 | 1.46 | 77% | 0.73 | 0 | 0 | 44808 | 0.0% | 0.0% | 1.03 | > 5% |
| Buy-and-hold (perp) | +418.4% | +37.9% | 0.83 | 1.18 | 79% | 0.48 | 0 | 0 | 44808 | 12.5% | 12.4% | 1.03 | > 5% |
| Momentum (daily 30-day, long/short, perp) | +218.6% | +25.4% | 0.67 | 0.95 | 63% | 0.41 | 60 | 30 | 293 | 15.2% | 7.3% | 0.92 | 0.477% |

## ETHUSDT, 2020-10-01 .. 2026-11-11, 0.10% a side

| Strategy | Net return | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Funding/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Phase 6 primary m_trend, reproduced (perp, as Phase 6), mean of 3 seeds** | +709.1% | +40.6% | 0.96 | 1.36 | 62% | 0.66 | 86 | 205 | 143 | 17.1% | 3.9% | 1.33 | 0.494% |
| &nbsp;&nbsp;seed 0 | +860.9% | +44.8% | 1.03 | 1.45 | 57% | 0.78 | 84 | 201 | 151 | 16.4% | 3.7% | 1.39 | 0.540% |
| &nbsp;&nbsp;seed 1 | +581.5% | +36.9% | 0.90 | 1.27 | 67% | 0.55 | 86 | 202 | 152 | 17.1% | 4.0% | 1.26 | 0.465% |
| &nbsp;&nbsp;seed 2 | +685.0% | +40.1% | 0.95 | 1.35 | 62% | 0.65 | 89 | 213 | 126 | 17.7% | 4.0% | 1.33 | 0.477% |
| **R3-b core_riskoff_125 (round 3, comparison), mean of 3 seeds** | +1644.3% | +59.1% | 1.13 | 1.59 | 55% | 1.09 | 35 | 51 | 286 | 5.9% | 0.8% | 1.24 | 1.431% |
| &nbsp;&nbsp;seed 0 | +1367.9% | +55.2% | 1.08 | 1.52 | 55% | 1.01 | 34 | 51 | 289 | 5.8% | 0.8% | 1.19 | 1.371% |
| &nbsp;&nbsp;seed 1 | +1347.7% | +54.8% | 1.07 | 1.51 | 60% | 0.91 | 33 | 49 | 307 | 5.7% | 0.9% | 1.18 | 1.432% |
| &nbsp;&nbsp;seed 2 | +2217.4% | +67.2% | 1.23 | 1.73 | 50% | 1.35 | 37 | 53 | 260 | 6.2% | 0.9% | 1.35 | 1.489% |
| **R3-c committee_riskoff (round 3, comparison), mean of 3 seeds** | +773.4% | +42.2% | 1.03 | 1.45 | 47% | 0.91 | 39 | 66 | 191 | 5.9% | 0.0% | 1.17 | 1.014% |
| &nbsp;&nbsp;seed 0 | +1011.9% | +48.3% | 1.13 | 1.59 | 42% | 1.14 | 36 | 61 | 206 | 5.5% | 0.0% | 1.26 | 1.203% |
| &nbsp;&nbsp;seed 1 | +606.7% | +37.7% | 0.96 | 1.34 | 52% | 0.72 | 39 | 64 | 200 | 6.0% | 0.0% | 1.10 | 0.919% |
| &nbsp;&nbsp;seed 2 | +701.7% | +40.6% | 1.01 | 1.42 | 47% | 0.86 | 41 | 73 | 165 | 6.4% | 0.0% | 1.16 | 0.921% |
| **R3-d retrain_longflat_riskoff (round 3, comparison), mean of 3 seeds** | +669.9% | +38.6% | 0.93 | 1.30 | 56% | 0.70 | 38 | 65 | 215 | 5.6% | 0.0% | 1.05 | 0.959% |
| &nbsp;&nbsp;seed 0 | +578.8% | +36.8% | 0.90 | 1.26 | 61% | 0.60 | 37 | 65 | 218 | 5.4% | 0.0% | 1.01 | 0.943% |
| &nbsp;&nbsp;seed 1 | +402.8% | +30.2% | 0.81 | 1.13 | 58% | 0.52 | 40 | 70 | 203 | 6.1% | 0.0% | 0.94 | 0.756% |
| &nbsp;&nbsp;seed 2 | +1028.0% | +48.6% | 1.08 | 1.51 | 50% | 0.97 | 37 | 61 | 224 | 5.3% | 0.0% | 1.19 | 1.179% |
| **R4-a committee_riskoff_125: R3-c's committee (flat on 2 of 3 bearish) at 1.25, mean of 3 seeds** | +1263.2% | +52.8% | 1.07 | 1.51 | 53% | 1.01 | 47 | 67 | 191 | 8.0% | 0.9% | 1.23 | 1.009% |
| &nbsp;&nbsp;seed 0 | +1492.5% | +57.3% | 1.12 | 1.57 | 49% | 1.17 | 43 | 62 | 206 | 7.5% | 0.9% | 1.26 | 1.154% |
| &nbsp;&nbsp;seed 1 | +881.2% | +45.3% | 0.98 | 1.37 | 59% | 0.76 | 47 | 65 | 200 | 8.0% | 0.9% | 1.13 | 0.899% |
| &nbsp;&nbsp;seed 2 | +1415.8% | +56.0% | 1.12 | 1.57 | 51% | 1.09 | 51 | 74 | 165 | 8.6% | 0.8% | 1.28 | 0.976% |
| **R4-b committee4_riskoff: flat on 3 of 4 bearish votes (3 agents + trend), 1x, mean of 3 seeds** | +995.7% | +47.1% | 1.09 | 1.53 | 51% | 0.92 | 42 | 75 | 176 | 6.6% | 0.0% | 1.24 | 1.014% |
| &nbsp;&nbsp;seed 0 | +1236.7% | +52.8% | 1.18 | 1.66 | 48% | 1.10 | 38 | 66 | 196 | 6.0% | 0.0% | 1.32 | 1.200% |
| &nbsp;&nbsp;seed 1 | +578.6% | +36.8% | 0.93 | 1.30 | 55% | 0.67 | 46 | 82 | 165 | 7.3% | 0.0% | 1.09 | 0.779% |
| &nbsp;&nbsp;seed 2 | +1171.8% | +51.6% | 1.17 | 1.64 | 51% | 1.01 | 43 | 77 | 167 | 6.7% | 0.0% | 1.32 | 1.065% |
| Buy-and-hold (spot) | +470.6% | +33.0% | 0.76 | 1.07 | 81% | 0.40 | 0 | 0 | 53556 | 0.0% | 0.0% | 0.76 | > 5% |
| Buy-and-hold (perp) | +172.2% | +17.8% | 0.60 | 0.85 | 82% | 0.22 | 0 | 0 | 53556 | 12.1% | 12.1% | 0.76 | > 5% |
| Momentum (daily 30-day, long/short, perp) | +727.8% | +41.3% | 0.83 | 1.18 | 80% | 0.51 | 55 | 28 | 317 | 15.9% | 8.4% | 1.04 | 0.722% |

### ETHUSDT, 0.05% a side

| Strategy | Net return | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Funding/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Phase 6 primary m_trend, reproduced (perp, as Phase 6), mean of 3 seeds** | +909.0% | +45.6% | 1.04 | 1.46 | 61% | 0.76 | 88 | 213 | 143 | 13.0% | 3.9% | 1.31 | 0.476% |
| &nbsp;&nbsp;seed 0 | +1111.0% | +50.4% | 1.11 | 1.56 | 55% | 0.92 | 85 | 205 | 151 | 12.4% | 3.7% | 1.38 | 0.528% |
| &nbsp;&nbsp;seed 1 | +687.1% | +40.1% | 0.95 | 1.34 | 67% | 0.60 | 90 | 219 | 152 | 13.2% | 4.0% | 1.23 | 0.424% |
| &nbsp;&nbsp;seed 2 | +928.8% | +46.4% | 1.05 | 1.48 | 60% | 0.77 | 90 | 214 | 126 | 13.4% | 4.1% | 1.33 | 0.474% |
| **R3-b core_riskoff_125 (round 3, comparison), mean of 3 seeds** | +1813.5% | +61.5% | 1.16 | 1.62 | 54% | 1.15 | 35 | 51 | 286 | 4.2% | 0.9% | 1.23 | 1.417% |
| &nbsp;&nbsp;seed 0 | +1552.7% | +58.2% | 1.12 | 1.57 | 53% | 1.09 | 35 | 51 | 289 | 4.1% | 0.8% | 1.20 | 1.366% |
| &nbsp;&nbsp;seed 1 | +1432.7% | +56.3% | 1.09 | 1.53 | 60% | 0.94 | 32 | 49 | 307 | 4.0% | 0.9% | 1.16 | 1.416% |
| &nbsp;&nbsp;seed 2 | +2455.0% | +69.9% | 1.26 | 1.77 | 49% | 1.41 | 37 | 53 | 260 | 4.4% | 0.9% | 1.34 | 1.469% |
| **R3-c committee_riskoff (round 3, comparison), mean of 3 seeds** | +939.7% | +46.0% | 1.09 | 1.53 | 46% | 1.01 | 39 | 66 | 191 | 4.0% | 0.0% | 1.19 | 1.028% |
| &nbsp;&nbsp;seed 0 | +1339.7% | +54.7% | 1.23 | 1.72 | 42% | 1.29 | 36 | 61 | 206 | 3.7% | 0.0% | 1.31 | 1.265% |
| &nbsp;&nbsp;seed 1 | +701.5% | +40.6% | 1.00 | 1.41 | 51% | 0.80 | 39 | 64 | 200 | 4.0% | 0.0% | 1.10 | 0.922% |
| &nbsp;&nbsp;seed 2 | +777.8% | +42.7% | 1.05 | 1.47 | 46% | 0.94 | 42 | 73 | 165 | 4.3% | 0.0% | 1.15 | 0.898% |
| **R3-d retrain_longflat_riskoff (round 3, comparison), mean of 3 seeds** | +737.0% | +40.3% | 0.96 | 1.34 | 55% | 0.75 | 38 | 65 | 215 | 3.7% | 0.0% | 1.04 | 0.935% |
| &nbsp;&nbsp;seed 0 | +574.8% | +36.7% | 0.89 | 1.26 | 61% | 0.60 | 38 | 65 | 218 | 3.6% | 0.0% | 0.97 | 0.878% |
| &nbsp;&nbsp;seed 1 | +468.6% | +32.9% | 0.85 | 1.19 | 55% | 0.59 | 40 | 70 | 203 | 4.1% | 0.0% | 0.94 | 0.753% |
| &nbsp;&nbsp;seed 2 | +1167.7% | +51.5% | 1.12 | 1.57 | 49% | 1.05 | 37 | 61 | 224 | 3.5% | 0.0% | 1.19 | 1.173% |
| **R4-a committee_riskoff_125: R3-c's committee (flat on 2 of 3 bearish) at 1.25, mean of 3 seeds** | +1429.8% | +55.7% | 1.11 | 1.56 | 52% | 1.08 | 47 | 67 | 191 | 5.7% | 0.9% | 1.22 | 0.997% |
| &nbsp;&nbsp;seed 0 | +1720.9% | +60.7% | 1.16 | 1.63 | 48% | 1.25 | 43 | 62 | 206 | 5.3% | 0.9% | 1.26 | 1.152% |
| &nbsp;&nbsp;seed 1 | +998.1% | +48.0% | 1.01 | 1.42 | 58% | 0.83 | 47 | 65 | 200 | 5.7% | 0.9% | 1.12 | 0.884% |
| &nbsp;&nbsp;seed 2 | +1570.4% | +58.5% | 1.15 | 1.61 | 51% | 1.15 | 51 | 74 | 165 | 6.1% | 0.8% | 1.26 | 0.956% |
| **R4-b committee4_riskoff: flat on 3 of 4 bearish votes (3 agents + trend), 1x, mean of 3 seeds** | +1167.6% | +50.5% | 1.14 | 1.61 | 49% | 1.03 | 43 | 75 | 176 | 4.5% | 0.0% | 1.25 | 1.013% |
| &nbsp;&nbsp;seed 0 | +1443.8% | +56.5% | 1.24 | 1.74 | 48% | 1.18 | 38 | 65 | 196 | 4.0% | 0.0% | 1.33 | 1.213% |
| &nbsp;&nbsp;seed 1 | +657.8% | +39.3% | 0.97 | 1.35 | 53% | 0.73 | 46 | 82 | 165 | 5.0% | 0.0% | 1.08 | 0.764% |
| &nbsp;&nbsp;seed 2 | +1401.2% | +55.7% | 1.22 | 1.73 | 47% | 1.19 | 44 | 77 | 167 | 4.6% | 0.0% | 1.33 | 1.063% |
| Buy-and-hold (spot) | +470.9% | +33.0% | 0.76 | 1.07 | 81% | 0.40 | 0 | 0 | 53556 | 0.0% | 0.0% | 0.76 | > 5% |
| Buy-and-hold (perp) | +172.4% | +17.8% | 0.60 | 0.85 | 82% | 0.22 | 0 | 0 | 53556 | 12.1% | 12.1% | 0.76 | > 5% |
| Momentum (daily 30-day, long/short, perp) | +880.0% | +45.3% | 0.87 | 1.23 | 79% | 0.57 | 55 | 28 | 317 | 13.2% | 8.4% | 1.04 | 0.722% |

### ETHUSDT, up to 2025-11-11, 0.10%

| Strategy | Net return | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Funding/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Phase 6 primary m_trend, reproduced (perp, as Phase 6), mean of 3 seeds** | +577.5% | +43.5% | 0.99 | 1.40 | 62% | 0.72 | 89 | 217 | 133 | 18.3% | 4.6% | 1.38 | 0.503% |
| &nbsp;&nbsp;seed 0 | +971.0% | +59.0% | 1.21 | 1.70 | 57% | 1.03 | 88 | 211 | 139 | 17.8% | 4.4% | 1.59 | 0.628% |
| &nbsp;&nbsp;seed 1 | +326.1% | +32.8% | 0.83 | 1.17 | 67% | 0.49 | 88 | 208 | 142 | 18.3% | 4.7% | 1.22 | 0.423% |
| &nbsp;&nbsp;seed 2 | +435.3% | +38.8% | 0.93 | 1.31 | 62% | 0.63 | 91 | 231 | 116 | 18.9% | 4.6% | 1.34 | 0.460% |
| **R3-b core_riskoff_125 (round 3, comparison), mean of 3 seeds** | +1559.6% | +72.8% | 1.26 | 1.76 | 55% | 1.34 | 35 | 53 | 282 | 6.1% | 0.9% | 1.37 | 1.653% |
| &nbsp;&nbsp;seed 0 | +1474.7% | +71.5% | 1.25 | 1.75 | 55% | 1.31 | 36 | 53 | 278 | 6.1% | 0.9% | 1.36 | 1.604% |
| &nbsp;&nbsp;seed 1 | +1225.6% | +65.8% | 1.18 | 1.65 | 60% | 1.10 | 33 | 52 | 300 | 6.0% | 1.0% | 1.28 | 1.598% |
| &nbsp;&nbsp;seed 2 | +1978.4% | +81.0% | 1.35 | 1.89 | 50% | 1.63 | 36 | 54 | 270 | 6.3% | 1.0% | 1.46 | 1.755% |
| **R3-c committee_riskoff (round 3, comparison), mean of 3 seeds** | +730.6% | +50.6% | 1.14 | 1.60 | 47% | 1.09 | 40 | 70 | 182 | 6.3% | 0.0% | 1.28 | 1.120% |
| &nbsp;&nbsp;seed 0 | +1032.2% | +60.8% | 1.29 | 1.81 | 42% | 1.43 | 37 | 65 | 198 | 5.8% | 0.0% | 1.42 | 1.376% |
| &nbsp;&nbsp;seed 1 | +560.2% | +44.7% | 1.05 | 1.47 | 52% | 0.86 | 41 | 68 | 189 | 6.4% | 0.0% | 1.20 | 0.998% |
| &nbsp;&nbsp;seed 2 | +599.3% | +46.3% | 1.08 | 1.52 | 47% | 0.99 | 43 | 78 | 160 | 6.7% | 0.0% | 1.24 | 0.986% |
| **R3-d retrain_longflat_riskoff (round 3, comparison), mean of 3 seeds** | +639.3% | +46.5% | 1.03 | 1.44 | 56% | 0.84 | 38 | 67 | 213 | 5.7% | 0.0% | 1.15 | 1.105% |
| &nbsp;&nbsp;seed 0 | +584.2% | +45.7% | 1.01 | 1.42 | 61% | 0.75 | 38 | 68 | 209 | 5.6% | 0.0% | 1.12 | 1.084% |
| &nbsp;&nbsp;seed 1 | +354.2% | +34.4% | 0.87 | 1.21 | 58% | 0.60 | 40 | 72 | 202 | 6.2% | 0.0% | 1.00 | 0.830% |
| &nbsp;&nbsp;seed 2 | +979.6% | +59.3% | 1.20 | 1.68 | 50% | 1.18 | 36 | 61 | 227 | 5.2% | 0.0% | 1.31 | 1.403% |
| **R4-a committee_riskoff_125: R3-c's committee (flat on 2 of 3 bearish) at 1.25, mean of 3 seeds** | +1220.9% | +64.7% | 1.19 | 1.67 | 53% | 1.24 | 49 | 72 | 182 | 8.5% | 1.0% | 1.35 | 1.127% |
| &nbsp;&nbsp;seed 0 | +1629.5% | +74.6% | 1.30 | 1.82 | 49% | 1.53 | 44 | 66 | 198 | 7.9% | 1.0% | 1.44 | 1.349% |
| &nbsp;&nbsp;seed 1 | +782.7% | +53.1% | 1.06 | 1.49 | 59% | 0.89 | 49 | 70 | 189 | 8.6% | 0.9% | 1.22 | 0.966% |
| &nbsp;&nbsp;seed 2 | +1250.6% | +66.4% | 1.22 | 1.71 | 51% | 1.30 | 52 | 79 | 160 | 9.1% | 0.9% | 1.38 | 1.066% |
| **R4-b committee4_riskoff: flat on 3 of 4 bearish votes (3 agents + trend), 1x, mean of 3 seeds** | +939.7% | +57.0% | 1.22 | 1.71 | 48% | 1.22 | 45 | 81 | 163 | 7.2% | 0.0% | 1.38 | 1.105% |
| &nbsp;&nbsp;seed 0 | +1159.6% | +64.1% | 1.33 | 1.86 | 48% | 1.33 | 40 | 70 | 182 | 6.3% | 0.0% | 1.47 | 1.318% |
| &nbsp;&nbsp;seed 1 | +535.6% | +43.6% | 1.02 | 1.42 | 55% | 0.79 | 50 | 90 | 151 | 8.0% | 0.0% | 1.19 | 0.820% |
| &nbsp;&nbsp;seed 2 | +1123.9% | +63.2% | 1.31 | 1.84 | 41% | 1.53 | 45 | 82 | 157 | 7.1% | 0.0% | 1.47 | 1.177% |
| Buy-and-hold (spot) | +889.1% | +56.6% | 0.96 | 1.35 | 81% | 0.69 | 0 | 0 | 44784 | 0.0% | 0.0% | 0.96 | > 5% |
| Buy-and-hold (perp) | +383.7% | +36.1% | 0.79 | 1.11 | 82% | 0.44 | 0 | 0 | 44784 | 14.0% | 14.0% | 0.96 | > 5% |
| Momentum (daily 30-day, long/short, perp) | +447.8% | +39.5% | 0.82 | 1.15 | 80% | 0.49 | 53 | 27 | 327 | 17.4% | 10.0% | 1.03 | 0.718% |

## Calendar-year net returns, BTCUSDT, 0.10% (seed means; 2020 from 1 Oct, 2026 to 11 Nov)

| Variant | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| Phase 6 primary m_trend, reproduced (perp, as Phase 6) | +106% | +8% | -8% | +105% | +44% | +15% | -19% |
| R3-b core_riskoff_125 (round 3, comparison) | +211% | +41% | -36% | +185% | +119% | -0% | -12% |
| R3-c committee_riskoff (round 3, comparison) | +150% | +29% | -32% | +106% | +72% | +11% | -6% |
| R3-d retrain_longflat_riskoff (round 3, comparison) | +179% | +52% | -38% | +105% | +89% | +7% | -12% |
| R4-a committee_riskoff_125: R3-c's committee (flat on 2 of 3 bearish) at 1.25 | +196% | +26% | -38% | +178% | +140% | +8% | -7% |
| R4-b committee4_riskoff: flat on 3 of 4 bearish votes (3 agents + trend), 1x | +150% | +29% | -32% | +104% | +66% | +3% | -9% |
| Buy-and-hold (spot) | +168% | +60% | -64% | +156% | +121% | -6% | -16% |
| Buy-and-hold (perp) | +156% | +18% | -66% | +136% | +96% | -11% | -18% |
| Momentum | +168% | +23% | -29% | +144% | -29% | -10% | -8% |

## Calendar-year net returns, ETHUSDT, 0.10% (seed means; 2020 from 1 Oct, 2026 to 11 Nov)

| Variant | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| Phase 6 primary m_trend, reproduced (perp, as Phase 6) | +56% | +131% | +5% | +18% | +12% | +63% | +19% |
| R3-b core_riskoff_125 (round 3, comparison) | +108% | +193% | -31% | +61% | +30% | +93% | +2% |
| R3-c committee_riskoff (round 3, comparison) | +72% | +130% | -23% | +37% | +36% | +49% | +4% |
| R3-d retrain_longflat_riskoff (round 3, comparison) | +77% | +158% | -36% | +34% | +25% | +50% | +3% |
| R4-a committee_riskoff_125: R3-c's committee (flat on 2 of 3 bearish) at 1.25 | +100% | +193% | -33% | +45% | +41% | +64% | +3% |
| R4-b committee4_riskoff: flat on 3 of 4 bearish votes (3 agents + trend), 1x | +81% | +172% | -24% | +38% | +26% | +60% | +4% |
| Buy-and-hold (spot) | +104% | +399% | -67% | +91% | +46% | -11% | -31% |
| Buy-and-hold (perp) | +89% | +243% | -68% | +76% | +28% | -15% | -32% |
| Momentum | +51% | +119% | -0% | -4% | -39% | +212% | +37% |

## Long vs short vs flat, and the agent's folds vs the fallback folds (0.10%, full span, seed means)

| Variant | Asset | Long / short / flat (time) | Time above 1x | Net from long bars /yr | Net from short bars /yr | Return in agent folds (by seed) | Return in fallback folds (by seed) |
|---|---|---|---|---|---|---|---|
| Phase 6 primary m_trend, reproduced (perp, as Phase 6) | BTCUSDT | 70% / 22% / 8% | 0% | +31.9% | +4.8% | +159%, +238%, +212% | +228%, +7%, +49% |
| Phase 6 primary m_trend, reproduced (perp, as Phase 6) | ETHUSDT | 67% / 25% / 8% | 0% | +36.2% | +10.5% | +250%, +346%, +167% | +175%, +53%, +194% |
| R3-b core_riskoff_125 (round 3, comparison) | BTCUSDT | 79% / 0% / 21% | 43% | +58.3% | +0.0% | +480%, +1338%, +531% | +230%, +19%, +52% |
| R3-b core_riskoff_125 (round 3, comparison) | ETHUSDT | 74% / 0% / 26% | 31% | +63.3% | +0.0% | +580%, +990%, +691% | +116%, +33%, +193% |
| R3-c committee_riskoff (round 3, comparison) | BTCUSDT | 73% / 0% / 27% | 0% | +43.5% | +0.0% | +307%, +738%, +345% | +121%, +15%, +27% |
| R3-c committee_riskoff (round 3, comparison) | ETHUSDT | 68% / 0% / 32% | 0% | +47.2% | +0.0% | +435%, +433%, +215% | +108%, +33%, +155% |
| R3-d retrain_longflat_riskoff (round 3, comparison) | BTCUSDT | 75% / 0% / 25% | 0% | +46.8% | +0.0% | +371%, +470%, +344% | +48%, +100%, +129% |
| R3-d retrain_longflat_riskoff (round 3, comparison) | ETHUSDT | 77% / 0% / 23% | 0% | +46.0% | +0.0% | +147%, +83%, +162% | +174%, +175%, +330% |
| R4-a committee_riskoff_125: R3-c's committee (flat on 2 of 3 bearish) at 1.25 | BTCUSDT | 73% / 0% / 27% | 44% | +58.6% | +0.0% | +424%, +1606%, +520% | +225%, +20%, +57% |
| R4-a committee_riskoff_125: R3-c's committee (flat on 2 of 3 bearish) at 1.25 | ETHUSDT | 68% / 0% / 32% | 33% | +59.5% | +0.0% | +632%, +647%, +419% | +118%, +31%, +192% |
| R4-b committee4_riskoff: flat on 3 of 4 bearish votes (3 agents + trend), 1x | BTCUSDT | 77% / 0% / 23% | 0% | +41.4% | +0.0% | +265%, +588%, +273% | +121%, +17%, +26% |
| R4-b committee4_riskoff: flat on 3 of 4 bearish votes (3 agents + trend), 1x | ETHUSDT | 72% / 0% / 28% | 0% | +51.4% | +0.0% | +546%, +468%, +431% | +107%, +19%, +140% |

The fallback split of R3-c*, R4-a and R4-b uses the Phase 6 agent's fallback folds.

## The agents (unchanged; reused trained models)

| Asset | Models | Fallback share of the span (s0 / s1 / s2) | Fallback folds (s0; s1; s2) | Decided long / short / flat (hold 16) |
|---|---|---|---|---|
| BTCUSDT | Phase 6 r_missed (perp-trained, long/short) | 33% / 14% / 33% | 6,7,8,9,12,16,22,23; 7,22,23,24; 6,7,8,9,12,15,22,23 | 70% / 22% / 8% |
| BTCUSDT | r_missed_spot (spot-trained, long/short) | 33% / 26% / 41% | 6,7,8,9,12,16,22,23; 7,8,9,12,22,23,24; 0,3,6,7,8,9,12,15,22,23 | 75% / 21% / 4% |
| BTCUSDT | r_missed_longflat (spot, long/flat, long-only reference) | 41% / 33% / 45% | 4,6,7,8,9,16,19,21,22,23; 4,6,7,8,9,16,22,23; 4,6,7,8,9,12,16,19,21,22,23 | 70% / 0% / 30% |
| ETHUSDT | Phase 6 r_missed (perp-trained, long/short) | 29% / 31% / 33% | 6,7,8,9,12,19,22; 6,7,8,12,16,22,23,24; 6,7,12,16,19,21,22,23 | 67% / 25% / 8% |
| ETHUSDT | r_missed_spot (spot-trained, long/short) | 29% / 25% / 37% | 6,7,8,9,12,19,22; 7,8,9,12,22,23; 6,7,8,9,12,16,19,22,23 | 70% / 23% / 7% |
| ETHUSDT | r_missed_longflat (spot, long/flat, long-only reference) | 29% / 33% / 33% | 7,8,12,16,19,22,23; 7,8,9,12,16,19,22,23; 6,7,9,16,18,19,22,23 | 72% / 0% / 28% |

Requested-flat share of the out-of-sample span (seed mean), BTC: R3-b* 21%, R3-c* 27%, R3-d* 25%, R4-a 27%, R4-b 23%; ETH: R3-b* 26%, R3-c* 32%, R3-d* 23%, R4-a 32%, R4-b 28%. Daily trend down (m = -1): BTC 45%, ETH 47% of the span.

Machine-readable: `research/out/rl_loop/round4_results.json`, grades `round4_grades.json`, gate `round4_check.json`; state: `research/out/rl_loop/loop_state.json`. Nothing here is wired into the live engine or the forward books.
