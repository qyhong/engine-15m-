# RL loop round 1: execution, accounting and sizing of the Phase 6 primary

Generated 2026-11-13 04:25 UTC. Paper only. Rules: `research/rl_loop/LOOP_RL.md` (frozen 13 Nov 2026 04:10 UTC, before any result). Seeds 0, 1, 2; 25 walk-forward folds, out of sample 2020-10-01 .. 2026-11-11; Phase 6's trained `m_trend` models (r_missed, trend fallback) reused unchanged. **RL variants tried, cumulative: 13** (Phase 6's 8 + round 1's 5). Compute: 1.0 min.

**Honesty.** No historical span is unseen for RL (Phase 4-6 scored every window; this loop was designed after Phase 6's per-fold results; the trend fallback was chosen with hindsight). A pass here would not be proof of an edge, only a proposal for a forward paper book, confirmed at 30 forward trades. Spot longs = long part up to 1x held as spot (no funding); shorts and exposure above 1x are perp. Leverage (V3-V5 reach 1.5x) raises return and drawdown together and leaves Sharpe unchanged only before costs.

**Reproduction check (rule 3).** Phase 6 primary through this harness: BTC +458.6%, Sharpe 0.866 (Phase 6 report: +458.6%, 0.87); ETH +709.1%, Sharpe 0.962 (+709.1%, 0.96). The spot-aware risk manager with perp accounting and Phase 6's band equals `risk3.apply`: max |difference| in executed position BTCUSDT_fee_0.10% 0.0e+00, BTCUSDT_fee_0.05% 0.0e+00, ETHUSDT_fee_0.10% 0.0e+00, ETHUSDT_fee_0.05% 0.0e+00.

Floors applied (max of the quoted value and the unrounded Phase 6 seed mean): BTC full 0.8700, BTC to 2025-11-11 1.0505, ETH full 0.9619.

Reproduction differences vs Phase 6's saved run (BTC seed mean): return 0.00e+00, Sharpe 0.00e+00 -> OK.

## Verdict

**No pass in round 1.** Best by rules met: V5 spot_lean_blend: side + 0.5 x trend, 19 of 21 rules; fails `S1_fold_share_ge_half`, `S4_significant`.

## Headline: BTC and ETH, full span, 0.10% a side, seed means, against spot buy-and-hold

| Variant | BTC return | BTC mean CAGR | BTC Sharpe (seeds) | BTC max DD (worst seed) | BTC trades/yr (max seed) | ETH return | ETH Sharpe | ETH max DD (worst) | Rules met |
|---|---|---|---|---|---|---|---|---|---|
| Phase 6 primary m_trend, reproduced (perp, as Phase 6) | +458.6% | +31.3% | 0.87 (1.04, 0.73, 0.82) | 47% (52%) | 178 (210) | +709.1% | 0.96 | 62% (67%) | 11 / 21 |
| V1 spot: m_trend, spot longs | +664.1% | +38.0% | 0.99 (1.18, 0.86, 0.92) | 46% (51%) | 177 (206) | +1059.8% | 1.09 | 61% (65%) | 16 / 21 |
| V2 spot_lean: side only, hold 4 h, band 0.40 | +642.0% | +38.6% | 0.96 (1.02, 0.93, 0.93) | 44% (50%) | 61 (65) | +2213.9% | 1.24 | 55% (60%) | 18 / 21 |
| V3 spot_lean_agree: 1.5x when agent = trend | +993.2% | +47.0% | 0.96 (1.06, 0.89, 0.92) | 60% (70%) | 85 (89) | +5593.7% | 1.30 | 67% (73%) | 19 / 21 |
| V4 spot_lean_agree_veto: 1.5x with trend, flat against | +751.9% | +41.9% | 0.94 (0.96, 0.96, 0.89) | 56% (59%) | 62 (65) | +5369.4% | 1.34 | 74% (77%) | 19 / 21 |
| V5 spot_lean_blend: side + 0.5 x trend | +1127.0% | +50.5% | 1.03 (1.08, 0.99, 1.01) | 54% (59%) | 88 (93) | +6808.0% | 1.40 | 68% (74%) | 19 / 21 |
| BTC spot buy-and-hold | +583.9% | +36.9% | 0.82 | 77% | 0 | | | | |
| ETH spot buy-and-hold | +470.6% | +33.0% | 0.76 | 81% | 0 | | | | |

The reference row is Phase 6 as it is (perp accounting): graded for information, not a round-1 variant.

## Every rule, every variant (PASS / fail)

| Rule | REF | V1 | V2 | V3 | V4 | V5 |
|---|---|---|---|---|---|---|
| `T_return_gt_bh` | fail | PASS | PASS | PASS | PASS | PASS |
| `T_mean_cagr_gt_bh` | fail | PASS | PASS | PASS | PASS | PASS |
| `T_sharpe_ge_floor` | fail | PASS | PASS | PASS | PASS | PASS |
| `T_sharpe_gt_bh` | PASS | PASS | PASS | PASS | PASS | PASS |
| `T_every_seed_sharpe_gt_bh` | fail | PASS | PASS | PASS | PASS | PASS |
| `T_every_seed_dd_le_bh` | PASS | PASS | PASS | PASS | PASS | PASS |
| `T4_dev_return_gt_bh` | fail | fail | fail | PASS | PASS | PASS |
| `T4_dev_mean_cagr_gt_bh` | fail | fail | fail | PASS | PASS | PASS |
| `T4_dev_sharpe_ge_floor` | PASS | PASS | PASS | PASS | PASS | PASS |
| `T4_dev_sharpe_gt_bh` | PASS | PASS | PASS | PASS | PASS | PASS |
| `T4_dev_every_seed_sharpe_gt_bh` | fail | PASS | PASS | PASS | PASS | PASS |
| `T4_dev_every_seed_dd_le_bh` | PASS | PASS | PASS | PASS | PASS | PASS |
| `S1_fold_share_ge_half` | fail | fail | PASS | fail | fail | fail |
| `S2_no_fee_only_at_0.05` | PASS | PASS | PASS | PASS | PASS | PASS |
| `S3_trades_le_100_every_seed` | fail | fail | PASS | PASS | PASS | PASS |
| `S3_turnover_le_100_every_seed` | PASS | PASS | PASS | PASS | PASS | PASS |
| `S4_significant` | fail | fail | fail | fail | fail | fail |
| `E1_eth_sharpe_ge_floor` | PASS | PASS | PASS | PASS | PASS | PASS |
| `E2_eth_return_gt_bh` | PASS | PASS | PASS | PASS | PASS | PASS |
| `E2_eth_mean_cagr_gt_bh` | PASS | PASS | PASS | PASS | PASS | PASS |
| `E3_eth_every_seed_dd_le_bh` | PASS | PASS | PASS | PASS | PASS | PASS |
| fold share (seed-mean per fold), full / to 2025-11-11 | 40% / 38% | 44% / 43% | 52% / 48% | 36% / 33% | 40% / 38% | 36% / 33% |
| fold share by seed 0 / 1 / 2 | 48% / 44% / 40% | 48% / 48% / 48% | 48% / 52% / 56% | 36% / 40% / 44% | 32% / 48% / 36% | 32% / 44% / 36% |
| seed-mean book Sharpe - B&H (p; threshold 0.0038) | +0.23 (p 0.297) | +0.36 (p 0.201) | +0.34 (p 0.214) | +0.24 (p 0.291) | +0.18 (p 0.347) | +0.30 (p 0.260) |
| Sharpe edge needed at that threshold / with the strategy loop's 1,910 added | 1.16 / 1.76 | 1.16 / 1.76 | 1.13 / 1.72 | 1.17 / 1.77 | 1.25 / 1.90 | 1.22 / 1.86 |
| deflated-Sharpe probability (N = 13) | 0.736 | 0.830 | 0.816 | 0.804 | 0.761 | 0.835 |

Bootstrap on daily returns of the seed-mean book (per-bar mean of the three seeds' net returns) against spot buy-and-hold, BTC full span; Bonferroni over 13 RL variants.

## BTCUSDT, 2020-10-01 .. 2026-11-11, 0.10% a side

| Strategy | Net return | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Funding/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Phase 6 primary m_trend, reproduced (perp, as Phase 6), mean of 3 seeds** | +458.6% | +31.3% | 0.87 | 1.23 | 47% | 0.68 | 84 | 178 | 167 | 15.4% | 3.1% | 1.24 | 0.428% |
| &nbsp;&nbsp;seed 0 | +748.7% | +41.9% | 1.04 | 1.49 | 43% | 0.98 | 77 | 152 | 181 | 14.6% | 3.5% | 1.39 | 0.555% |
| &nbsp;&nbsp;seed 1 | +262.3% | +23.4% | 0.73 | 1.04 | 52% | 0.45 | 89 | 210 | 157 | 16.1% | 2.8% | 1.14 | 0.336% |
| &nbsp;&nbsp;seed 2 | +364.9% | +28.6% | 0.82 | 1.17 | 46% | 0.62 | 85 | 173 | 164 | 15.4% | 3.0% | 1.20 | 0.395% |
| **V1 spot: m_trend, spot longs, mean of 3 seeds** | +664.1% | +38.0% | 0.99 | 1.40 | 46% | 0.85 | 84 | 177 | 167 | 10.3% | -2.0% | 1.24 | 0.489% |
| &nbsp;&nbsp;seed 0 | +1094.1% | +50.0% | 1.18 | 1.67 | 41% | 1.22 | 75 | 145 | 181 | 8.9% | -2.0% | 1.39 | 0.638% |
| &nbsp;&nbsp;seed 1 | +402.6% | +30.2% | 0.86 | 1.22 | 51% | 0.59 | 89 | 206 | 157 | 11.1% | -2.2% | 1.14 | 0.395% |
| &nbsp;&nbsp;seed 2 | +495.7% | +33.9% | 0.92 | 1.31 | 45% | 0.75 | 87 | 181 | 164 | 10.8% | -1.9% | 1.18 | 0.435% |
| **V2 spot_lean: side only, hold 4 h, band 0.40, mean of 3 seeds** | +642.0% | +38.6% | 0.96 | 1.36 | 44% | 0.89 | 60 | 61 | 191 | 6.5% | -2.3% | 1.11 | 0.644% |
| &nbsp;&nbsp;seed 0 | +773.9% | +42.5% | 1.02 | 1.45 | 38% | 1.13 | 59 | 56 | 201 | 6.2% | -2.4% | 1.16 | 0.694% |
| &nbsp;&nbsp;seed 1 | +569.7% | +36.5% | 0.93 | 1.32 | 50% | 0.72 | 56 | 63 | 189 | 5.9% | -2.5% | 1.07 | 0.652% |
| &nbsp;&nbsp;seed 2 | +582.5% | +36.9% | 0.93 | 1.32 | 45% | 0.82 | 64 | 65 | 183 | 7.4% | -2.1% | 1.09 | 0.586% |
| **V3 spot_lean_agree: 1.5x when agent = trend, mean of 3 seeds** | +993.2% | +47.0% | 0.96 | 1.36 | 60% | 0.81 | 79 | 85 | 191 | 10.7% | -0.8% | 1.15 | 0.586% |
| &nbsp;&nbsp;seed 0 | +1450.3% | +56.5% | 1.06 | 1.51 | 51% | 1.10 | 79 | 81 | 201 | 10.5% | -0.8% | 1.24 | 0.664% |
| &nbsp;&nbsp;seed 1 | +701.1% | +40.5% | 0.89 | 1.27 | 70% | 0.58 | 73 | 89 | 189 | 9.9% | -1.0% | 1.07 | 0.561% |
| &nbsp;&nbsp;seed 2 | +828.3% | +44.0% | 0.92 | 1.31 | 59% | 0.75 | 84 | 86 | 183 | 11.6% | -0.5% | 1.12 | 0.533% |
| **V4 spot_lean_agree_veto: 1.5x with trend, flat against, mean of 3 seeds** | +751.9% | +41.9% | 0.94 | 1.33 | 56% | 0.76 | 71 | 62 | 166 | 10.5% | 0.7% | 1.14 | 0.595% |
| &nbsp;&nbsp;seed 0 | +849.7% | +44.5% | 0.96 | 1.36 | 50% | 0.90 | 72 | 63 | 170 | 10.7% | 0.8% | 1.17 | 0.609% |
| &nbsp;&nbsp;seed 1 | +749.9% | +41.9% | 0.96 | 1.36 | 59% | 0.71 | 64 | 58 | 167 | 9.4% | 0.4% | 1.15 | 0.644% |
| &nbsp;&nbsp;seed 2 | +656.2% | +39.2% | 0.89 | 1.27 | 59% | 0.66 | 76 | 65 | 162 | 11.4% | 0.7% | 1.11 | 0.531% |
| **V5 spot_lean_blend: side + 0.5 x trend, mean of 3 seeds** | +1127.0% | +50.5% | 1.03 | 1.46 | 54% | 0.95 | 81 | 88 | 175 | 11.3% | -0.2% | 1.24 | 0.603% |
| &nbsp;&nbsp;seed 0 | +1358.9% | +55.0% | 1.08 | 1.53 | 47% | 1.16 | 80 | 82 | 191 | 11.1% | -0.1% | 1.28 | 0.647% |
| &nbsp;&nbsp;seed 1 | +929.5% | +46.4% | 0.99 | 1.41 | 55% | 0.84 | 78 | 93 | 159 | 10.8% | -0.5% | 1.20 | 0.585% |
| &nbsp;&nbsp;seed 2 | +1092.6% | +50.0% | 1.01 | 1.44 | 59% | 0.85 | 84 | 89 | 174 | 11.9% | -0.1% | 1.23 | 0.578% |
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
| **V1 spot: m_trend, spot longs, mean of 3 seeds** | +933.1% | +45.1% | 1.11 | 1.57 | 43% | 1.06 | 82 | 167 | 167 | 5.9% | -2.0% | 1.25 | 0.510% |
| &nbsp;&nbsp;seed 0 | +1504.0% | +57.4% | 1.29 | 1.83 | 40% | 1.42 | 73 | 133 | 181 | 5.0% | -2.0% | 1.41 | 0.672% |
| &nbsp;&nbsp;seed 1 | +637.9% | +38.6% | 1.02 | 1.44 | 43% | 0.89 | 84 | 182 | 157 | 6.3% | -2.2% | 1.17 | 0.438% |
| &nbsp;&nbsp;seed 2 | +657.5% | +39.2% | 1.01 | 1.44 | 45% | 0.88 | 89 | 186 | 164 | 6.6% | -1.9% | 1.17 | 0.421% |
| **V2 spot_lean: side only, hold 4 h, band 0.40, mean of 3 seeds** | +774.4% | +42.4% | 1.02 | 1.45 | 44% | 0.98 | 60 | 61 | 191 | 3.5% | -2.3% | 1.10 | 0.638% |
| &nbsp;&nbsp;seed 0 | +913.7% | +46.0% | 1.07 | 1.52 | 38% | 1.22 | 60 | 56 | 201 | 3.3% | -2.4% | 1.15 | 0.682% |
| &nbsp;&nbsp;seed 1 | +700.1% | +40.5% | 1.00 | 1.42 | 50% | 0.81 | 56 | 63 | 189 | 3.1% | -2.5% | 1.07 | 0.654% |
| &nbsp;&nbsp;seed 2 | +709.6% | +40.8% | 0.99 | 1.41 | 45% | 0.91 | 64 | 65 | 183 | 4.1% | -2.1% | 1.09 | 0.579% |
| **V3 spot_lean_agree: 1.5x when agent = trend, mean of 3 seeds** | +1461.7% | +55.6% | 1.05 | 1.50 | 58% | 0.98 | 79 | 86 | 191 | 6.7% | -0.8% | 1.17 | 0.603% |
| &nbsp;&nbsp;seed 0 | +2194.6% | +66.9% | 1.17 | 1.66 | 50% | 1.33 | 79 | 80 | 201 | 6.5% | -0.8% | 1.28 | 0.694% |
| &nbsp;&nbsp;seed 1 | +969.6% | +47.3% | 0.97 | 1.38 | 67% | 0.71 | 74 | 90 | 189 | 6.3% | -0.9% | 1.08 | 0.570% |
| &nbsp;&nbsp;seed 2 | +1220.9% | +52.5% | 1.02 | 1.45 | 59% | 0.90 | 85 | 86 | 183 | 7.4% | -0.6% | 1.15 | 0.546% |
| **V4 spot_lean_agree_veto: 1.5x with trend, flat against, mean of 3 seeds** | +1123.5% | +50.5% | 1.05 | 1.49 | 54% | 0.95 | 71 | 62 | 166 | 7.0% | 0.6% | 1.18 | 0.623% |
| &nbsp;&nbsp;seed 0 | +1252.9% | +53.1% | 1.07 | 1.52 | 48% | 1.11 | 72 | 63 | 170 | 7.1% | 0.8% | 1.21 | 0.637% |
| &nbsp;&nbsp;seed 1 | +969.8% | +47.3% | 1.03 | 1.47 | 55% | 0.86 | 64 | 58 | 167 | 6.2% | 0.4% | 1.16 | 0.650% |
| &nbsp;&nbsp;seed 2 | +1148.0% | +51.1% | 1.04 | 1.48 | 59% | 0.87 | 77 | 65 | 162 | 7.6% | 0.6% | 1.19 | 0.582% |
| **V5 spot_lean_blend: side + 0.5 x trend, mean of 3 seeds** | +1673.7% | +59.8% | 1.14 | 1.61 | 52% | 1.15 | 81 | 88 | 175 | 7.3% | -0.3% | 1.27 | 0.622% |
| &nbsp;&nbsp;seed 0 | +1861.3% | +62.7% | 1.16 | 1.65 | 48% | 1.30 | 80 | 82 | 191 | 7.1% | -0.1% | 1.29 | 0.656% |
| &nbsp;&nbsp;seed 1 | +1300.4% | +54.0% | 1.08 | 1.54 | 50% | 1.08 | 79 | 93 | 159 | 7.0% | -0.5% | 1.22 | 0.593% |
| &nbsp;&nbsp;seed 2 | +1859.5% | +62.7% | 1.16 | 1.65 | 59% | 1.07 | 85 | 88 | 174 | 7.7% | -0.2% | 1.30 | 0.618% |
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
| **V1 spot: m_trend, spot longs, mean of 3 seeds** | +771.1% | +51.4% | 1.19 | 1.69 | 46% | 1.15 | 83 | 173 | 155 | 10.3% | -2.2% | 1.43 | 0.605% |
| &nbsp;&nbsp;seed 0 | +1171.6% | +64.4% | 1.37 | 1.94 | 41% | 1.57 | 74 | 141 | 171 | 8.7% | -2.2% | 1.57 | 0.773% |
| &nbsp;&nbsp;seed 1 | +476.2% | +40.8% | 1.04 | 1.48 | 51% | 0.80 | 92 | 208 | 142 | 11.6% | -2.4% | 1.32 | 0.472% |
| &nbsp;&nbsp;seed 2 | +665.4% | +48.9% | 1.16 | 1.65 | 45% | 1.08 | 84 | 170 | 153 | 10.5% | -2.1% | 1.41 | 0.570% |
| **V2 spot_lean: side only, hold 4 h, band 0.40, mean of 3 seeds** | +711.2% | +50.4% | 1.12 | 1.60 | 44% | 1.17 | 61 | 66 | 180 | 6.6% | -2.6% | 1.27 | 0.762% |
| &nbsp;&nbsp;seed 0 | +834.7% | +54.8% | 1.19 | 1.68 | 38% | 1.45 | 59 | 59 | 193 | 6.0% | -2.7% | 1.32 | 0.836% |
| &nbsp;&nbsp;seed 1 | +620.1% | +47.1% | 1.08 | 1.54 | 49% | 0.97 | 60 | 70 | 174 | 6.4% | -2.8% | 1.22 | 0.745% |
| &nbsp;&nbsp;seed 2 | +678.8% | +49.4% | 1.10 | 1.57 | 45% | 1.09 | 66 | 70 | 173 | 7.6% | -2.3% | 1.27 | 0.706% |
| **V3 spot_lean_agree: 1.5x when agent = trend, mean of 3 seeds** | +1261.6% | +65.4% | 1.14 | 1.62 | 60% | 1.13 | 81 | 92 | 180 | 11.3% | -0.7% | 1.33 | 0.715% |
| &nbsp;&nbsp;seed 0 | +1821.7% | +78.2% | 1.26 | 1.79 | 51% | 1.52 | 79 | 85 | 193 | 10.7% | -0.8% | 1.44 | 0.826% |
| &nbsp;&nbsp;seed 1 | +805.6% | +53.8% | 1.04 | 1.47 | 70% | 0.77 | 78 | 98 | 174 | 10.8% | -0.9% | 1.23 | 0.651% |
| &nbsp;&nbsp;seed 2 | +1157.3% | +64.0% | 1.12 | 1.60 | 59% | 1.09 | 87 | 92 | 173 | 12.3% | -0.5% | 1.33 | 0.669% |
| **V4 spot_lean_agree_veto: 1.5x with trend, flat against, mean of 3 seeds** | +1024.5% | +60.3% | 1.15 | 1.63 | 56% | 1.09 | 72 | 66 | 157 | 11.1% | 0.9% | 1.35 | 0.756% |
| &nbsp;&nbsp;seed 0 | +1216.6% | +65.5% | 1.19 | 1.68 | 50% | 1.32 | 72 | 67 | 163 | 11.1% | 1.1% | 1.39 | 0.798% |
| &nbsp;&nbsp;seed 1 | +854.3% | +55.4% | 1.12 | 1.60 | 59% | 0.94 | 65 | 63 | 154 | 10.0% | 0.8% | 1.32 | 0.777% |
| &nbsp;&nbsp;seed 2 | +1002.5% | +59.9% | 1.13 | 1.61 | 59% | 1.02 | 79 | 70 | 155 | 12.2% | 1.0% | 1.35 | 0.692% |
| **V5 spot_lean_blend: side + 0.5 x trend, mean of 3 seeds** | +1328.1% | +67.7% | 1.20 | 1.71 | 54% | 1.28 | 81 | 94 | 168 | 11.7% | -0.0% | 1.41 | 0.733% |
| &nbsp;&nbsp;seed 0 | +1674.4% | +75.5% | 1.27 | 1.81 | 47% | 1.60 | 78 | 85 | 189 | 11.2% | 0.1% | 1.47 | 0.817% |
| &nbsp;&nbsp;seed 1 | +997.1% | +59.7% | 1.14 | 1.62 | 55% | 1.08 | 81 | 102 | 147 | 11.6% | -0.3% | 1.35 | 0.675% |
| &nbsp;&nbsp;seed 2 | +1312.7% | +67.8% | 1.19 | 1.70 | 59% | 1.15 | 85 | 94 | 168 | 12.4% | 0.1% | 1.41 | 0.707% |
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
| **V1 spot: m_trend, spot longs, mean of 3 seeds** | +1059.8% | +49.1% | 1.09 | 1.53 | 61% | 0.82 | 86 | 204 | 143 | 11.4% | -1.7% | 1.33 | 0.563% |
| &nbsp;&nbsp;seed 0 | +1267.1% | +53.4% | 1.15 | 1.62 | 56% | 0.96 | 83 | 196 | 151 | 10.8% | -1.8% | 1.39 | 0.616% |
| &nbsp;&nbsp;seed 1 | +833.2% | +44.1% | 1.01 | 1.43 | 65% | 0.68 | 89 | 214 | 152 | 11.7% | -1.8% | 1.26 | 0.511% |
| &nbsp;&nbsp;seed 2 | +1079.0% | +49.7% | 1.09 | 1.54 | 61% | 0.82 | 87 | 202 | 126 | 11.9% | -1.6% | 1.35 | 0.563% |
| **V2 spot_lean: side only, hold 4 h, band 0.40, mean of 3 seeds** | +2213.9% | +65.2% | 1.24 | 1.75 | 55% | 1.18 | 63 | 75 | 162 | 7.6% | -2.0% | 1.39 | 0.892% |
| &nbsp;&nbsp;seed 0 | +3637.6% | +80.8% | 1.41 | 1.98 | 60% | 1.35 | 64 | 73 | 164 | 7.4% | -2.3% | 1.55 | 1.022% |
| &nbsp;&nbsp;seed 1 | +1392.8% | +55.6% | 1.13 | 1.60 | 59% | 0.94 | 59 | 68 | 178 | 7.2% | -1.8% | 1.28 | 0.846% |
| &nbsp;&nbsp;seed 2 | +1611.4% | +59.1% | 1.18 | 1.68 | 47% | 1.26 | 65 | 84 | 144 | 8.3% | -1.8% | 1.35 | 0.806% |
| **V3 spot_lean_agree: 1.5x when agent = trend, mean of 3 seeds** | +5593.7% | +88.6% | 1.30 | 1.84 | 67% | 1.33 | 83 | 99 | 162 | 11.8% | -0.7% | 1.48 | 0.853% |
| &nbsp;&nbsp;seed 0 | +10034.0% | +112.9% | 1.48 | 2.09 | 73% | 1.55 | 83 | 97 | 164 | 11.6% | -1.0% | 1.66 | 0.998% |
| &nbsp;&nbsp;seed 1 | +1979.2% | +64.3% | 1.10 | 1.56 | 67% | 0.96 | 77 | 93 | 178 | 10.9% | -0.7% | 1.27 | 0.742% |
| &nbsp;&nbsp;seed 2 | +4767.9% | +88.8% | 1.31 | 1.86 | 60% | 1.48 | 88 | 107 | 144 | 12.8% | -0.5% | 1.51 | 0.820% |
| **V4 spot_lean_agree_veto: 1.5x with trend, flat against, mean of 3 seeds** | +5369.4% | +88.0% | 1.34 | 1.91 | 74% | 1.19 | 71 | 71 | 163 | 10.9% | 0.6% | 1.53 | 0.982% |
| &nbsp;&nbsp;seed 0 | +10097.7% | +113.1% | 1.55 | 2.20 | 75% | 1.51 | 71 | 71 | 163 | 11.0% | 0.6% | 1.73 | 1.152% |
| &nbsp;&nbsp;seed 1 | +2904.4% | +74.5% | 1.24 | 1.76 | 70% | 1.06 | 66 | 64 | 178 | 10.0% | 0.5% | 1.41 | 0.940% |
| &nbsp;&nbsp;seed 2 | +3106.1% | +76.3% | 1.25 | 1.77 | 77% | 0.99 | 75 | 78 | 149 | 11.8% | 0.7% | 1.44 | 0.855% |
| **V5 spot_lean_blend: side + 0.5 x trend, mean of 3 seeds** | +6808.0% | +96.9% | 1.40 | 1.99 | 68% | 1.42 | 82 | 101 | 151 | 12.1% | -0.2% | 1.60 | 0.912% |
| &nbsp;&nbsp;seed 0 | +11612.0% | +118.0% | 1.56 | 2.21 | 74% | 1.59 | 84 | 99 | 151 | 12.3% | -0.2% | 1.75 | 1.018% |
| &nbsp;&nbsp;seed 1 | +3968.5% | +83.3% | 1.30 | 1.85 | 66% | 1.26 | 78 | 93 | 157 | 11.4% | -0.2% | 1.48 | 0.872% |
| &nbsp;&nbsp;seed 2 | +4843.5% | +89.3% | 1.34 | 1.90 | 63% | 1.42 | 85 | 110 | 145 | 12.6% | -0.1% | 1.55 | 0.845% |
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
| **V1 spot: m_trend, spot longs, mean of 3 seeds** | +1380.2% | +55.0% | 1.17 | 1.64 | 59% | 0.96 | 87 | 206 | 143 | 7.2% | -1.7% | 1.32 | 0.553% |
| &nbsp;&nbsp;seed 0 | +1655.7% | +59.8% | 1.24 | 1.74 | 53% | 1.13 | 82 | 191 | 151 | 6.5% | -1.8% | 1.38 | 0.623% |
| &nbsp;&nbsp;seed 1 | +994.9% | +47.9% | 1.06 | 1.50 | 66% | 0.72 | 92 | 227 | 152 | 7.5% | -1.8% | 1.22 | 0.475% |
| &nbsp;&nbsp;seed 2 | +1490.0% | +57.2% | 1.19 | 1.68 | 56% | 1.02 | 88 | 200 | 126 | 7.6% | -1.6% | 1.35 | 0.562% |
| **V2 spot_lean: side only, hold 4 h, band 0.40, mean of 3 seeds** | +2734.8% | +71.0% | 1.31 | 1.85 | 53% | 1.35 | 63 | 75 | 162 | 4.5% | -2.0% | 1.40 | 0.895% |
| &nbsp;&nbsp;seed 0 | +4371.4% | +86.2% | 1.46 | 2.06 | 58% | 1.48 | 64 | 73 | 164 | 4.2% | -2.3% | 1.55 | 1.016% |
| &nbsp;&nbsp;seed 1 | +1755.2% | +61.2% | 1.20 | 1.70 | 57% | 1.07 | 59 | 68 | 178 | 4.3% | -1.8% | 1.29 | 0.856% |
| &nbsp;&nbsp;seed 2 | +2077.8% | +65.5% | 1.26 | 1.79 | 44% | 1.50 | 66 | 83 | 144 | 5.1% | -1.8% | 1.36 | 0.812% |
| **V3 spot_lean_agree: 1.5x when agent = trend, mean of 3 seeds** | +7056.2% | +95.7% | 1.35 | 1.91 | 66% | 1.45 | 83 | 99 | 162 | 7.7% | -0.8% | 1.47 | 0.841% |
| &nbsp;&nbsp;seed 0 | +12863.8% | +121.6% | 1.54 | 2.18 | 71% | 1.71 | 84 | 97 | 164 | 7.5% | -1.0% | 1.65 | 0.988% |
| &nbsp;&nbsp;seed 1 | +2531.4% | +70.7% | 1.16 | 1.64 | 66% | 1.07 | 77 | 92 | 178 | 7.1% | -0.8% | 1.27 | 0.737% |
| &nbsp;&nbsp;seed 2 | +5773.3% | +94.7% | 1.35 | 1.92 | 60% | 1.59 | 89 | 107 | 144 | 8.5% | -0.5% | 1.49 | 0.798% |
| **V4 spot_lean_agree_veto: 1.5x with trend, flat against, mean of 3 seeds** | +6727.7% | +95.5% | 1.41 | 2.00 | 73% | 1.31 | 71 | 71 | 163 | 7.4% | 0.6% | 1.53 | 0.983% |
| &nbsp;&nbsp;seed 0 | +12194.7% | +119.7% | 1.60 | 2.27 | 75% | 1.61 | 72 | 72 | 163 | 7.5% | 0.6% | 1.72 | 1.137% |
| &nbsp;&nbsp;seed 1 | +3679.2% | +81.1% | 1.30 | 1.85 | 68% | 1.20 | 66 | 64 | 178 | 6.8% | 0.5% | 1.41 | 0.946% |
| &nbsp;&nbsp;seed 2 | +4309.2% | +85.8% | 1.33 | 1.88 | 75% | 1.14 | 75 | 78 | 149 | 8.1% | 0.7% | 1.46 | 0.866% |
| **V5 spot_lean_blend: side + 0.5 x trend, mean of 3 seeds** | +8667.4% | +104.4% | 1.46 | 2.07 | 67% | 1.55 | 83 | 101 | 151 | 8.0% | -0.2% | 1.59 | 0.904% |
| &nbsp;&nbsp;seed 0 | +15004.1% | +127.2% | 1.62 | 2.30 | 73% | 1.74 | 85 | 100 | 151 | 8.1% | -0.2% | 1.75 | 1.011% |
| &nbsp;&nbsp;seed 1 | +4922.0% | +89.8% | 1.35 | 1.93 | 66% | 1.36 | 78 | 93 | 157 | 7.5% | -0.2% | 1.48 | 0.866% |
| &nbsp;&nbsp;seed 2 | +6076.1% | +96.3% | 1.40 | 1.99 | 62% | 1.55 | 85 | 109 | 145 | 8.4% | -0.2% | 1.54 | 0.835% |
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
| **V1 spot: m_trend, spot longs, mean of 3 seeds** | +857.0% | +53.5% | 1.13 | 1.59 | 61% | 0.90 | 89 | 215 | 133 | 11.8% | -1.9% | 1.38 | 0.581% |
| &nbsp;&nbsp;seed 0 | +1404.9% | +70.0% | 1.35 | 1.90 | 56% | 1.26 | 86 | 205 | 139 | 11.2% | -2.0% | 1.59 | 0.713% |
| &nbsp;&nbsp;seed 1 | +476.2% | +40.9% | 0.96 | 1.35 | 65% | 0.63 | 91 | 223 | 142 | 12.1% | -2.0% | 1.21 | 0.475% |
| &nbsp;&nbsp;seed 2 | +690.0% | +49.8% | 1.09 | 1.54 | 61% | 0.82 | 88 | 218 | 116 | 12.2% | -1.8% | 1.35 | 0.557% |
| **V2 spot_lean: side only, hold 4 h, band 0.40, mean of 3 seeds** | +1875.8% | +72.2% | 1.29 | 1.82 | 55% | 1.30 | 65 | 81 | 152 | 7.9% | -2.2% | 1.45 | 0.916% |
| &nbsp;&nbsp;seed 0 | +3921.2% | +106.0% | 1.63 | 2.30 | 60% | 1.77 | 68 | 79 | 152 | 7.8% | -2.6% | 1.78 | 1.161% |
| &nbsp;&nbsp;seed 1 | +782.6% | +53.1% | 1.09 | 1.54 | 59% | 0.89 | 61 | 73 | 168 | 7.5% | -2.0% | 1.24 | 0.798% |
| &nbsp;&nbsp;seed 2 | +923.6% | +57.6% | 1.16 | 1.64 | 47% | 1.23 | 66 | 90 | 135 | 8.3% | -2.0% | 1.33 | 0.790% |
| **V3 spot_lean_agree: 1.5x when agent = trend, mean of 3 seeds** | +4080.8% | +94.8% | 1.32 | 1.86 | 67% | 1.41 | 85 | 105 | 152 | 12.3% | -0.8% | 1.51 | 0.858% |
| &nbsp;&nbsp;seed 0 | +9115.1% | +142.2% | 1.65 | 2.33 | 73% | 1.95 | 87 | 102 | 152 | 12.3% | -1.0% | 1.83 | 1.108% |
| &nbsp;&nbsp;seed 1 | +905.2% | +57.1% | 1.03 | 1.45 | 67% | 0.85 | 79 | 97 | 168 | 11.3% | -0.8% | 1.20 | 0.671% |
| &nbsp;&nbsp;seed 2 | +2222.2% | +85.0% | 1.28 | 1.80 | 60% | 1.41 | 88 | 115 | 135 | 13.2% | -0.5% | 1.48 | 0.795% |
| **V4 spot_lean_agree_veto: 1.5x with trend, flat against, mean of 3 seeds** | +3400.8% | +92.0% | 1.36 | 1.93 | 74% | 1.24 | 71 | 75 | 154 | 11.4% | 0.9% | 1.55 | 0.997% |
| &nbsp;&nbsp;seed 0 | +7164.9% | +131.2% | 1.66 | 2.36 | 75% | 1.75 | 73 | 75 | 157 | 11.6% | 0.8% | 1.85 | 1.241% |
| &nbsp;&nbsp;seed 1 | +1480.8% | +71.6% | 1.21 | 1.71 | 70% | 1.02 | 66 | 66 | 171 | 10.4% | 0.7% | 1.38 | 0.918% |
| &nbsp;&nbsp;seed 2 | +1556.7% | +73.2% | 1.22 | 1.72 | 77% | 0.95 | 75 | 84 | 135 | 12.3% | 1.0% | 1.43 | 0.833% |
| **V5 spot_lean_blend: side + 0.5 x trend, mean of 3 seeds** | +4554.7% | +103.3% | 1.43 | 2.02 | 68% | 1.51 | 84 | 107 | 143 | 12.6% | -0.1% | 1.63 | 0.927% |
| &nbsp;&nbsp;seed 0 | +9441.1% | +143.9% | 1.71 | 2.42 | 74% | 1.94 | 87 | 104 | 142 | 12.9% | -0.1% | 1.91 | 1.116% |
| &nbsp;&nbsp;seed 1 | +1819.4% | +78.2% | 1.25 | 1.77 | 66% | 1.18 | 79 | 98 | 149 | 11.9% | -0.1% | 1.44 | 0.825% |
| &nbsp;&nbsp;seed 2 | +2403.7% | +87.7% | 1.33 | 1.88 | 63% | 1.40 | 85 | 118 | 139 | 13.0% | -0.0% | 1.54 | 0.839% |
| Buy-and-hold (spot) | +889.1% | +56.6% | 0.96 | 1.35 | 81% | 0.69 | 0 | 0 | 44784 | 0.0% | 0.0% | 0.96 | > 5% |
| Buy-and-hold (perp) | +383.7% | +36.1% | 0.79 | 1.11 | 82% | 0.44 | 0 | 0 | 44784 | 14.0% | 14.0% | 0.96 | > 5% |
| Momentum (daily 30-day, long/short, perp) | +447.8% | +39.5% | 0.82 | 1.15 | 80% | 0.49 | 53 | 27 | 327 | 17.4% | 10.0% | 1.03 | 0.718% |

## Calendar-year net returns, BTCUSDT, 0.10% (seed means; 2020 from 1 Oct, 2026 to 11 Nov)

| Variant | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| Phase 6 primary m_trend, reproduced (perp, as Phase 6) | +106% | +8% | -8% | +105% | +44% | +15% | -19% |
| V1 spot: m_trend, spot longs | +112% | +17% | -4% | +116% | +56% | +18% | -19% |
| V2 spot_lean: side only, hold 4 h, band 0.40 | +129% | +8% | +1% | +86% | +73% | +14% | -13% |
| V3 spot_lean_agree: 1.5x when agent = trend | +246% | -6% | -14% | +170% | +80% | +10% | -24% |
| V4 spot_lean_agree_veto: 1.5x with trend, flat against | +253% | +16% | -22% | +186% | +24% | +8% | -26% |
| V5 spot_lean_blend: side + 0.5 x trend | +267% | +21% | -20% | +188% | +51% | +7% | -23% |
| Buy-and-hold (spot) | +168% | +60% | -64% | +156% | +121% | -6% | -16% |
| Buy-and-hold (perp) | +156% | +18% | -66% | +136% | +96% | -11% | -18% |
| Momentum | +168% | +23% | -29% | +144% | -29% | -10% | -8% |

## Calendar-year net returns, ETHUSDT, 0.10% (seed means; 2020 from 1 Oct, 2026 to 11 Nov)

| Variant | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| Phase 6 primary m_trend, reproduced (perp, as Phase 6) | +56% | +131% | +5% | +18% | +12% | +63% | +19% |
| V1 spot: m_trend, spot longs | +64% | +161% | +9% | +26% | +18% | +66% | +20% |
| V2 spot_lean: side only, hold 4 h, band 0.40 | +74% | +158% | +19% | +14% | +93% | +95% | +26% |
| V3 spot_lean_agree: 1.5x when agent = trend | +104% | +256% | +31% | +5% | +86% | +154% | +50% |
| V4 spot_lean_agree_veto: 1.5x with trend, flat against | +103% | +306% | +28% | -5% | +10% | +259% | +53% |
| V5 spot_lean_blend: side + 0.5 x trend | +101% | +315% | +27% | +3% | +50% | +214% | +51% |
| Buy-and-hold (spot) | +104% | +399% | -67% | +91% | +46% | -11% | -31% |
| Buy-and-hold (perp) | +89% | +243% | -68% | +76% | +28% | -15% | -32% |
| Momentum | +51% | +119% | -0% | -4% | -39% | +212% | +37% |

## Long vs short, and the agent's folds vs the fallback folds (0.10%, full span, seed means)

| Variant | Asset | Long / short / flat (time) | Time above 1x | Net from long bars /yr | Net from short bars /yr | Return in agent folds (by seed) | Return in fallback folds (by seed) |
|---|---|---|---|---|---|---|---|
| Phase 6 primary m_trend, reproduced (perp, as Phase 6) | BTCUSDT | 70% / 22% / 8% | 0% | +31.9% | +4.8% | +159%, +238%, +212% | +228%, +7%, +49% |
| Phase 6 primary m_trend, reproduced (perp, as Phase 6) | ETHUSDT | 67% / 25% / 8% | 0% | +36.2% | +10.5% | +250%, +346%, +167% | +175%, +53%, +194% |
| V1 spot: m_trend, spot longs | BTCUSDT | 70% / 22% / 8% | 0% | +36.8% | +5.0% | +221%, +364%, +279% | +272%, +8%, +57% |
| V1 spot: m_trend, spot longs | ETHUSDT | 67% / 25% / 8% | 0% | +42.0% | +10.7% | +360%, +493%, +260% | +197%, +57%, +227% |
| V2 spot_lean: side only, hold 4 h, band 0.40 | BTCUSDT | 70% / 22% / 8% | 0% | +40.1% | +4.2% | +218%, +485%, +419% | +175%, +14%, +31% |
| V2 spot_lean: side only, hold 4 h, band 0.40 | ETHUSDT | 67% / 25% / 8% | 0% | +53.5% | +11.3% | +1229%, +753%, +505% | +181%, +75%, +183% |
| V3 spot_lean_agree: 1.5x when agent = trend | BTCUSDT | 70% / 22% / 8% | 50% | +50.4% | +6.2% | +244%, +573%, +489% | +351%, +19%, +58% |
| V3 spot_lean_agree: 1.5x when agent = trend | ETHUSDT | 67% / 25% / 8% | 43% | +67.5% | +18.5% | +2435%, +924%, +893% | +300%, +103%, +390% |
| V4 spot_lean_agree_veto: 1.5x with trend, flat against | BTCUSDT | 47% / 15% / 38% | 50% | +45.5% | +6.4% | +144%, +612%, +408% | +290%, +19%, +49% |
| V4 spot_lean_agree_veto: 1.5x with trend, flat against | ETHUSDT | 46% / 19% / 35% | 44% | +60.0% | +24.5% | +2493%, +1429%, +577% | +293%, +96%, +373% |
| V5 spot_lean_blend: side + 0.5 x trend | BTCUSDT | 72% / 28% / 0% | 51% | +48.4% | +6.9% | +287%, +763%, +686% | +277%, +19%, +52% |
| V5 spot_lean_blend: side + 0.5 x trend | ETHUSDT | 68% / 32% / 0% | 43% | +63.7% | +22.8% | +2999%, +1841%, +965% | +278%, +110%, +364% |

Fallback folds (validation net Sharpe under 0.5: the daily momentum position is held instead of the agent's) cover 33%, 14%, 33% of the BTC span by seed. In V3-V5 they are held at a 1.5x request (agent = trend by construction).

## Decision counts (agent changes over the span, by seed; min hold refusals)

- BTCUSDT: hold 4 bars: 694 (53), 846 (123), 745 (94); hold 16 bars: 619 (368), 743 (774), 658 (571)
- ETHUSDT: hold 4 bars: 906 (115), 928 (136), 978 (123); hold 16 bars: 828 (813), 820 (943), 873 (893)

Machine-readable: `research/out/rl_loop/round1_results.json`; state: `research/out/rl_loop/loop_state.json`. Nothing here is wired into the live engine or the forward books.

## Reading the result (written after the run; nothing below changes a rule or a grade)

- **Spot accounting alone (V1) already beats spot buy-and-hold on return and Sharpe over the full span** (+664% vs +584%,
  0.99 vs 0.82, every seed above), because the Phase 6 agent's longs stop paying ~5%/yr of perp funding. It fails the
  sub-span return (+771% vs +880% to 2025-11-11), fold share (44%), trades (177/yr) and significance.
- **V2 (side only, 4 h hold, band 0.40)** cuts trades from 178 to 61 a year and cost drag from 15.4% to ~7%/yr, lifts the
  worst seed's Sharpe from 0.73 to 0.93, and is the only variant with fold share >= 1/2 (52%). It fails the sub-span return
  (+711% vs +880%) and significance.
- **V3-V5 (1.5x when agent and trend agree)** clear every return rule on both spans and keep Sharpe at 0.94-1.03 (V5
  1.03, every seed >= 0.99) with drawdown 54-60% (worst seed 59-70%) vs 77%, but the extra exposure costs fold share
  (36-40%): leverage raised return without raising the Sharpe of a fold, and in strong bull folds buy-and-hold's Sharpe
  stays higher. As stated in the rules, leverage leaves Sharpe unchanged only before costs.
- **Significance is out of reach at this sample size:** with 13 RL variants the rule needs a Sharpe edge of ~1.1-1.25 over
  spot buy-and-hold; the best seed-mean book shows +0.36 (V1), p 0.20. Counting the strategy loop's 1,910 would need ~1.8.
  This rule is reported as failing, not changed. Deflated-Sharpe probabilities 0.74-0.84 (N = 13).
- **ETH guard holds for every variant** (Sharpe 1.09-1.40 vs floor 0.962; returns far above ETH spot buy-and-hold).
  ETH seed returns are very dispersed (V5: +3,969% to +11,612%); the seed mean is dominated by seed 0.
- **Where the gain comes from (honesty):** fallback folds (the daily momentum position, chosen with hindsight in Phase 6)
  cover 33% / 14% / 33% of the BTC span by seed; V3-V5 hold momentum at 1.5x there. Calendar years: V5 lags buy-and-hold
  in 2021 (+21% vs +60%) and 2024 (+51% vs +121%) and wins by losing less in 2022 (-20% vs -64%) and 2026.
- Disclosure: the round-1 script's lock release failed on Windows after the results were written (the file was deleted
  while still open); the stale lock (dead PID) was removed and `release_lock` fixed. No result was affected. The report
  tables were regenerated once to fix a missing column separator (formatting only).

## Round 2 proposals (not registered, not run; see `loop_state.json`)

Aim: keep V3/V5's return and Sharpe while winning fold share (the agent's bull-fold Sharpe), and lift the Sharpe edge,
which only a better agent can do; execution tweaks cannot reach the ~1.2 edge the significance rule asks for.
1. **R2-a `blend_fundcap`**: V5, but the part above 1x only while the latest settled funding rate <= its trailing
   270-settlement median (else request capped at 1.0): leverage where it is cheap (the loop's H34 idea).
2. **R2-b `blend_125`**: V5 with clip(s + 0.25 m, -1.25, 1.25): less leverage, aiming for V2's fold share with a sub-span
   return above buy-and-hold's.
3. **R2-c `lean_longlever`**: V2, with 1.5x only when s = m = +1 (long leverage only; shorts at 1x): bull folds are where
   fold share is lost.
4. **R2-d `retrain_spot_lean`** (retrain, ~4 h): r_missed retrained with spot-long funding in the training reward
   (`qagent.funding_mode` = spot accounting), so the agent learns under the accounting it is scored by; V2 execution.
5. **R2-e `retrain_spot_blend`**: R2-d's models with V5 execution.
Cumulative after round 2 would be 18 (threshold 0.05 / 18). Round 2 must be registered in LOOP_RL.md and HYPOTHESES.md
before any of it runs.
