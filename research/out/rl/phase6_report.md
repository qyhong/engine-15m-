# RL Phase 6 report: flat scores weakly, long and short both ways

Run `phase6_20261112T141341Z_30a4dd4f`, generated 2026-11-12 14:15 UTC. Paper only. Seeds [0, 1, 2]; 15-minute bars and clock; Phase 4's data, folds, inputs, risk manager, backtester, fees and benchmarks. Owner's direction: "the RL need to learn to profit from downtrend also. stay flat should have a weak scoring so the RL will have more motivation to take long or short".

**Holdout honesty.** Phase 4 already scored every test window through 2026-11-11, so no historical span is unseen for RL: everything below was designed after those windows were seen. Both spans are shown; the loop's rules A and B only up to 2025-11-11. The forward paper run is the real test.

## Verdict

YES. The Phase 6 primary (missed-opportunity reward, fallback = trend reference), BTC full span after 0.10% fees: net Sharpe 0.87 (seeds 1.04, 0.73, 0.82) vs the Phase 4 primary's 0.48; ETH 0.96 vs 0.77. Time long / short / flat (BTC): 70% / 22% / 8% (Phase 4 primary 42% / 8% / 50%). Variants that clearly beat the Phase 4 primary by the frozen rule: missed-opportunity reward, fallback = trend reference (of 8 tried).

## What changed (frozen in configs/rl/phase6.yaml before any result)

- **Reward (training only).** The literal "net return - beta x reference return" cannot change any decision with this agent: the reference's return does not depend on the action, so it lowers every action's value equally (flat scores negative in a trend, but long scores lower by the same amount). It was replaced before any run by forms that charge the IDLE part of the book: *missed opportunity* (the idle part pays beta x the daily momentum rule's return, long or short; beta in {0.25, 0.5, 1} chosen on validation) and *flat-time charge* (the idle part pays lam x one round trip per day; lam in {0.25, 0.5, 1} on validation). Decisions and results use the real net P&L.
- **Symmetry.** Actions -1, -0.5, 0, +0.5, +1 with the same costs each way; perp funding on the whole position both ways (shorts receive positive funding); signed features.
- **'Do no harm'.** Three modes on the same trained models: flat (Phase 4's rule), none, the trend reference.

- Chosen per fold (BTC records, 3 seeds): missed-opportunity reward: {'0.25': 33, '0.5': 19, '1.0': 23}; validation net Sharpe under 0.5 (the 'do no harm' trigger) in 27% of fold models.
- Chosen per fold (BTC records, 3 seeds): flat-time charge: {'0.25': 27, '0.5': 12, '1.0': 36}; validation net Sharpe under 0.5 (the 'do no harm' trigger) in 36% of fold models.
- Phase 4 primary: 'do no harm' trigger in 39% of fold models.

## BTCUSDT, 2020-10-01 .. 2026-11-11, 0.10% a side

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **missed-opportunity reward, fallback = trend reference [primary], mean of 3 seeds** | **+458.6%** | **0.87** | **1.23** | **47%** | **0.68** | **84** | **178** | **167** | **15.4%** | **1.24** | **0.428%** |
| &nbsp;&nbsp;seed 0 | +748.7% | 1.04 | 1.49 | 43% | 0.98 | 77 | 152 | 181 | 14.6% | 1.39 | 0.555% |
| &nbsp;&nbsp;seed 1 | +262.3% | 0.73 | 1.04 | 52% | 0.45 | 89 | 210 | 157 | 16.1% | 1.14 | 0.336% |
| &nbsp;&nbsp;seed 2 | +364.9% | 0.82 | 1.17 | 46% | 0.62 | 85 | 173 | 164 | 15.4% | 1.20 | 0.395% |
| Phase 4 primary, 'do no harm' = flat (as it is), mean of 3 seeds | +78.8% | 0.48 | 0.67 | 41% | 0.24 | 47 | 110 | 162 | 8.4% | 0.78 | 0.298% |
| Phase 4 primary, no fallback, mean of 3 seeds | +140.1% | 0.54 | 0.76 | 62% | 0.23 | 73 | 173 | 152 | 13.4% | 0.92 | 0.271% |
| Phase 4 primary, fallback = trend reference, mean of 3 seeds | +624.6% | 0.98 | 1.39 | 43% | 0.89 | 74 | 157 | 208 | 13.5% | 1.31 | 0.536% |
| missed-opportunity reward, fallback flat, mean of 3 seeds | +188.9% | 0.68 | 0.97 | 45% | 0.43 | 63 | 139 | 139 | 12.0% | 1.04 | 0.375% |
| missed-opportunity reward, no fallback, mean of 3 seeds | +195.1% | 0.66 | 0.93 | 58% | 0.33 | 77 | 174 | 157 | 14.5% | 1.05 | 0.328% |
| flat-time charge, fallback flat, mean of 3 seeds | +167.3% | 0.62 | 0.87 | 49% | 0.33 | 61 | 131 | 156 | 10.9% | 0.94 | 0.350% |
| flat-time charge, no fallback, mean of 3 seeds | +98.2% | 0.47 | 0.66 | 67% | 0.18 | 81 | 187 | 190 | 14.9% | 0.83 | 0.232% |
| flat-time charge, fallback = trend reference, mean of 3 seeds | +645.9% | 0.91 | 1.29 | 51% | 0.75 | 87 | 181 | 191 | 15.4% | 1.27 | 0.449% |
| Buy-and-hold (perp) | +249.3% | 0.64 | 0.91 | 79% | 0.29 | 0 | 0 | 53579 | 11.0% | 0.83 | > 5% |
| Buy-and-hold (spot) | +583.9% | 0.82 | 1.17 | 77% | 0.48 | 0 | 0 | 53579 | 0.0% | 0.83 | > 5% |
| Momentum (daily 30-day, long/short) | +237.7% | 0.63 | 0.89 | 64% | 0.34 | 62 | 31 | 281 | 14.3% | 0.87 | 0.418% |
| Random agent (mean of 10) | -95.3% | -0.93 | -1.30 | 97% | -0.44 | 323 | 243 | 36 | 42.6% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +248.5% | 0.68 | 0.96 | 68% | 0.33 | 22 | 88 | 53579 | 11.9% | 0.95 | 1.036% |
| *reference: momentum through the Phase 3 risk manager* | +212.0% | 0.64 | 0.90 | 57% | 0.36 | 72 | 123 | 281 | 14.2% | 0.95 | 0.356% |

### BTCUSDT, 0.05% a side

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **missed-opportunity reward, fallback = trend reference [primary], mean of 3 seeds** | **+638.5%** | **0.98** | **1.39** | **44%** | **0.87** | **84** | **177** | **167** | **11.2%** | **1.25** | **0.433%** |
| &nbsp;&nbsp;seed 0 | +1020.9% | 1.15 | 1.64 | 41% | 1.17 | 76 | 148 | 181 | 10.7% | 1.41 | 0.568% |
| &nbsp;&nbsp;seed 1 | +416.1% | 0.87 | 1.24 | 44% | 0.69 | 88 | 198 | 157 | 11.5% | 1.16 | 0.356% |
| &nbsp;&nbsp;seed 2 | +478.4% | 0.91 | 1.29 | 45% | 0.74 | 88 | 184 | 164 | 11.4% | 1.19 | 0.375% |
| Phase 4 primary, 'do no harm' = flat (as it is), mean of 3 seeds | +105.9% | 0.56 | 0.78 | 41% | 0.31 | 47 | 107 | 162 | 6.0% | 0.77 | 0.302% |
| Phase 4 primary, no fallback, mean of 3 seeds | +196.2% | 0.64 | 0.90 | 61% | 0.30 | 73 | 171 | 152 | 9.7% | 0.92 | 0.270% |
| Phase 4 primary, fallback = trend reference, mean of 3 seeds | +746.2% | 1.05 | 1.48 | 42% | 1.00 | 75 | 164 | 208 | 9.9% | 1.29 | 0.511% |
| missed-opportunity reward, fallback flat, mean of 3 seeds | +251.2% | 0.78 | 1.10 | 43% | 0.53 | 64 | 143 | 139 | 9.0% | 1.04 | 0.369% |
| missed-opportunity reward, no fallback, mean of 3 seeds | +281.7% | 0.77 | 1.09 | 56% | 0.44 | 78 | 174 | 157 | 10.7% | 1.06 | 0.330% |
| flat-time charge, fallback flat, mean of 3 seeds | +212.4% | 0.70 | 0.98 | 47% | 0.41 | 62 | 135 | 156 | 8.0% | 0.93 | 0.337% |
| flat-time charge, no fallback, mean of 3 seeds | +157.0% | 0.56 | 0.80 | 66% | 0.25 | 83 | 195 | 190 | 11.1% | 0.83 | 0.226% |
| flat-time charge, fallback = trend reference, mean of 3 seeds | +819.9% | 1.00 | 1.42 | 48% | 0.89 | 89 | 187 | 191 | 11.2% | 1.26 | 0.434% |
| Buy-and-hold (perp) | +249.5% | 0.64 | 0.91 | 79% | 0.29 | 0 | 0 | 53579 | 11.0% | 0.83 | > 5% |
| Buy-and-hold (spot) | +584.3% | 0.83 | 1.17 | 77% | 0.48 | 0 | 0 | 53579 | 0.0% | 0.83 | > 5% |
| Momentum (daily 30-day, long/short) | +308.7% | 0.68 | 0.97 | 61% | 0.42 | 62 | 31 | 281 | 11.2% | 0.87 | 0.418% |
| Random agent (mean of 10) | -87.3% | -0.59 | -0.84 | 93% | -0.35 | 323 | 243 | 36 | 26.5% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +261.7% | 0.70 | 0.98 | 69% | 0.34 | 23 | 95 | 53579 | 11.0% | 0.94 | 0.951% |
| *reference: momentum through the Phase 3 risk manager* | +295.7% | 0.72 | 1.02 | 50% | 0.51 | 74 | 128 | 281 | 10.7% | 0.96 | 0.354% |

### BTCUSDT, up to 2025-11-11, 0.10% (with the loop's rules A and B)

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **missed-opportunity reward, fallback = trend reference [primary], mean of 3 seeds** | **+543.3%** | **1.05** | **1.50** | **47%** | **0.93** | **84** | **178** | **155** | **16.1%** | **1.44** | **0.529%** |
| &nbsp;&nbsp;seed 0 | +814.6% | 1.22 | 1.73 | 43% | 1.27 | 76 | 153 | 171 | 15.2% | 1.57 | 0.666% |
| &nbsp;&nbsp;seed 1 | +319.8% | 0.89 | 1.27 | 52% | 0.62 | 92 | 216 | 142 | 17.3% | 1.32 | 0.403% |
| &nbsp;&nbsp;seed 2 | +495.5% | 1.04 | 1.48 | 46% | 0.91 | 83 | 166 | 153 | 15.9% | 1.42 | 0.517% |
| Phase 4 primary, 'do no harm' = flat (as it is), mean of 3 seeds | +122.1% | 0.67 | 0.94 | 41% | 0.41 | 52 | 118 | 149 | 9.4% | 0.99 | 0.393% |
| Phase 4 primary, no fallback, mean of 3 seeds | +247.2% | 0.80 | 1.13 | 62% | 0.41 | 80 | 185 | 133 | 14.9% | 1.21 | 0.380% |
| Phase 4 primary, fallback = trend reference, mean of 3 seeds | +745.6% | 1.20 | 1.70 | 43% | 1.22 | 73 | 153 | 193 | 14.1% | 1.53 | 0.672% |
| missed-opportunity reward, fallback flat, mean of 3 seeds | +246.9% | 0.85 | 1.20 | 45% | 0.61 | 70 | 156 | 133 | 13.5% | 1.23 | 0.439% |
| missed-opportunity reward, no fallback, mean of 3 seeds | +334.9% | 0.92 | 1.31 | 58% | 0.57 | 85 | 189 | 140 | 16.2% | 1.34 | 0.437% |
| flat-time charge, fallback flat, mean of 3 seeds | +219.4% | 0.78 | 1.11 | 49% | 0.49 | 67 | 142 | 146 | 12.3% | 1.13 | 0.423% |
| flat-time charge, no fallback, mean of 3 seeds | +283.6% | 0.81 | 1.15 | 64% | 0.47 | 84 | 184 | 166 | 16.0% | 1.19 | 0.404% |
| flat-time charge, fallback = trend reference, mean of 3 seeds | +885.8% | 1.14 | 1.63 | 45% | 1.16 | 84 | 167 | 178 | 15.8% | 1.50 | 0.592% |
| Buy-and-hold (perp) | +418.4% | 0.83 | 1.18 | 79% | 0.48 | 0 | 0 | 44808 | 12.5% | 1.03 | > 5% |
| Buy-and-hold (spot) | +879.7% | 1.03 | 1.46 | 77% | 0.73 | 0 | 0 | 44808 | 0.0% | 1.03 | > 5% |
| Momentum (daily 30-day, long/short) | +218.6% | 0.67 | 0.95 | 63% | 0.41 | 60 | 30 | 293 | 15.2% | 0.92 | 0.477% |
| Random agent (mean of 10) | -92.0% | -0.91 | -1.28 | 95% | -0.45 | 323 | 243 | 36 | 42.9% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +398.4% | 0.91 | 1.28 | 68% | 0.54 | 20 | 80 | 44808 | 12.8% | 1.19 | 1.697% |
| *reference: momentum through the Phase 3 risk manager* | +250.2% | 0.76 | 1.07 | 49% | 0.56 | 64 | 101 | 293 | 14.2% | 1.06 | 0.480% |
| A: loop H29 H30 1.5x/0x spot | +1809.3% | 1.19 | 1.69 | 65% | 1.20 | 45 | 30 | 328 | 10.8% | 1.35 | 1.379% |
| B: loop H29 H31 trail 4 ATR spot | +1301.3% | 1.32 | 1.88 | 53% | 1.28 | 46 | 53 | 315 | 7.6% | 1.48 | 1.223% |

## ETHUSDT, 2020-10-01 .. 2026-11-11, 0.10% a side

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **missed-opportunity reward, fallback = trend reference [primary], mean of 3 seeds** | **+709.1%** | **0.96** | **1.36** | **62%** | **0.66** | **86** | **205** | **143** | **17.1%** | **1.33** | **0.494%** |
| &nbsp;&nbsp;seed 0 | +860.9% | 1.03 | 1.45 | 57% | 0.78 | 84 | 201 | 151 | 16.4% | 1.39 | 0.540% |
| &nbsp;&nbsp;seed 1 | +581.5% | 0.90 | 1.27 | 67% | 0.55 | 86 | 202 | 152 | 17.1% | 1.26 | 0.465% |
| &nbsp;&nbsp;seed 2 | +685.0% | 0.95 | 1.35 | 62% | 0.65 | 89 | 213 | 126 | 17.7% | 1.33 | 0.477% |
| Phase 4 primary, 'do no harm' = flat (as it is), mean of 3 seeds | +263.1% | 0.77 | 1.07 | 50% | 0.49 | 63 | 158 | 104 | 11.6% | 1.11 | 0.419% |
| Phase 4 primary, no fallback, mean of 3 seeds | +379.1% | 0.81 | 1.14 | 55% | 0.53 | 92 | 238 | 116 | 16.7% | 1.22 | 0.372% |
| Phase 4 primary, fallback = trend reference, mean of 3 seeds | +607.0% | 0.82 | 1.15 | 66% | 0.59 | 89 | 214 | 151 | 16.9% | 1.19 | 0.406% |
| missed-opportunity reward, fallback flat, mean of 3 seeds | +264.4% | 0.74 | 1.03 | 52% | 0.45 | 69 | 167 | 108 | 13.7% | 1.10 | 0.403% |
| missed-opportunity reward, no fallback, mean of 3 seeds | +379.0% | 0.76 | 1.07 | 55% | 0.52 | 94 | 234 | 113 | 17.6% | 1.17 | 0.354% |
| flat-time charge, fallback flat, mean of 3 seeds | +314.9% | 0.76 | 1.06 | 46% | 0.56 | 67 | 156 | 125 | 13.3% | 1.09 | 0.436% |
| flat-time charge, no fallback, mean of 3 seeds | +221.8% | 0.64 | 0.89 | 62% | 0.33 | 94 | 222 | 139 | 17.6% | 1.01 | 0.302% |
| flat-time charge, fallback = trend reference, mean of 3 seeds | +421.4% | 0.76 | 1.07 | 63% | 0.49 | 91 | 208 | 159 | 17.6% | 1.13 | 0.383% |
| Buy-and-hold (perp) | +172.2% | 0.60 | 0.85 | 82% | 0.22 | 0 | 0 | 53556 | 12.1% | 0.76 | > 5% |
| Buy-and-hold (spot) | +470.6% | 0.76 | 1.07 | 81% | 0.40 | 0 | 0 | 53556 | 0.0% | 0.76 | > 5% |
| Momentum (daily 30-day, long/short) | +727.8% | 0.83 | 1.18 | 80% | 0.51 | 55 | 28 | 317 | 15.9% | 1.04 | 0.722% |
| Random agent (mean of 10) | -95.8% | -0.63 | -0.89 | 97% | -0.45 | 323 | 243 | 36 | 45.4% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +170.5% | 0.58 | 0.81 | 64% | 0.28 | 21 | 88 | 53556 | 11.7% | 0.82 | 0.867% |
| *reference: momentum through the Phase 3 risk manager* | +688.0% | 0.91 | 1.30 | 70% | 0.57 | 65 | 132 | 317 | 14.3% | 1.19 | 0.616% |

### ETHUSDT, 0.05% a side

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **missed-opportunity reward, fallback = trend reference [primary], mean of 3 seeds** | **+909.0%** | **1.04** | **1.46** | **61%** | **0.76** | **88** | **213** | **143** | **13.0%** | **1.31** | **0.476%** |
| &nbsp;&nbsp;seed 0 | +1111.0% | 1.11 | 1.56 | 55% | 0.92 | 85 | 205 | 151 | 12.4% | 1.38 | 0.528% |
| &nbsp;&nbsp;seed 1 | +687.1% | 0.95 | 1.34 | 67% | 0.60 | 90 | 219 | 152 | 13.2% | 1.23 | 0.424% |
| &nbsp;&nbsp;seed 2 | +928.8% | 1.05 | 1.48 | 60% | 0.77 | 90 | 214 | 126 | 13.4% | 1.33 | 0.474% |
| Phase 4 primary, 'do no harm' = flat (as it is), mean of 3 seeds | +341.1% | 0.86 | 1.19 | 49% | 0.56 | 63 | 157 | 104 | 8.5% | 1.11 | 0.418% |
| Phase 4 primary, no fallback, mean of 3 seeds | +510.6% | 0.91 | 1.28 | 54% | 0.64 | 93 | 240 | 116 | 12.2% | 1.21 | 0.361% |
| Phase 4 primary, fallback = trend reference, mean of 3 seeds | +748.1% | 0.89 | 1.25 | 65% | 0.67 | 91 | 221 | 151 | 12.6% | 1.16 | 0.384% |
| missed-opportunity reward, fallback flat, mean of 3 seeds | +340.7% | 0.82 | 1.15 | 50% | 0.54 | 70 | 171 | 108 | 10.4% | 1.10 | 0.394% |
| missed-opportunity reward, no fallback, mean of 3 seeds | +512.4% | 0.85 | 1.20 | 53% | 0.63 | 95 | 237 | 113 | 13.0% | 1.15 | 0.344% |
| flat-time charge, fallback flat, mean of 3 seeds | +394.3% | 0.83 | 1.16 | 44% | 0.67 | 66 | 152 | 125 | 9.9% | 1.08 | 0.437% |
| flat-time charge, no fallback, mean of 3 seeds | +302.8% | 0.71 | 0.99 | 61% | 0.41 | 94 | 224 | 139 | 13.0% | 0.99 | 0.288% |
| flat-time charge, fallback = trend reference, mean of 3 seeds | +535.3% | 0.84 | 1.17 | 61% | 0.58 | 93 | 215 | 159 | 13.2% | 1.11 | 0.365% |
| Buy-and-hold (perp) | +172.4% | 0.60 | 0.85 | 82% | 0.22 | 0 | 0 | 53556 | 12.1% | 0.76 | > 5% |
| Buy-and-hold (spot) | +470.9% | 0.76 | 1.07 | 81% | 0.40 | 0 | 0 | 53556 | 0.0% | 0.76 | > 5% |
| Momentum (daily 30-day, long/short) | +880.0% | 0.87 | 1.23 | 79% | 0.57 | 55 | 28 | 317 | 13.2% | 1.04 | 0.722% |
| Random agent (mean of 10) | -88.7% | -0.38 | -0.53 | 93% | -0.36 | 323 | 243 | 36 | 29.3% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +176.6% | 0.58 | 0.82 | 63% | 0.29 | 24 | 98 | 53556 | 10.9% | 0.81 | 0.748% |
| *reference: momentum through the Phase 3 risk manager* | +879.8% | 0.98 | 1.40 | 68% | 0.67 | 71 | 155 | 317 | 11.5% | 1.20 | 0.573% |

### ETHUSDT, up to 2025-11-11, 0.10%

| Strategy | Net return | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | Cost drag/yr | Gross Sharpe | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **missed-opportunity reward, fallback = trend reference [primary], mean of 3 seeds** | **+577.5%** | **0.99** | **1.40** | **62%** | **0.72** | **89** | **217** | **133** | **18.3%** | **1.38** | **0.503%** |
| &nbsp;&nbsp;seed 0 | +971.0% | 1.21 | 1.70 | 57% | 1.03 | 88 | 211 | 139 | 17.8% | 1.59 | 0.628% |
| &nbsp;&nbsp;seed 1 | +326.1% | 0.83 | 1.17 | 67% | 0.49 | 88 | 208 | 142 | 18.3% | 1.22 | 0.423% |
| &nbsp;&nbsp;seed 2 | +435.3% | 0.93 | 1.31 | 62% | 0.63 | 91 | 231 | 116 | 18.9% | 1.34 | 0.460% |
| Phase 4 primary, 'do no harm' = flat (as it is), mean of 3 seeds | +290.5% | 0.86 | 1.20 | 50% | 0.63 | 71 | 179 | 105 | 13.2% | 1.23 | 0.447% |
| Phase 4 primary, no fallback, mean of 3 seeds | +451.4% | 0.97 | 1.36 | 55% | 0.71 | 98 | 255 | 110 | 18.2% | 1.40 | 0.431% |
| Phase 4 primary, fallback = trend reference, mean of 3 seeds | +432.4% | 0.79 | 1.11 | 65% | 0.60 | 92 | 229 | 142 | 18.0% | 1.18 | 0.388% |
| missed-opportunity reward, fallback flat, mean of 3 seeds | +319.8% | 0.89 | 1.24 | 50% | 0.65 | 74 | 183 | 104 | 15.2% | 1.27 | 0.470% |
| missed-opportunity reward, no fallback, mean of 3 seeds | +423.6% | 0.93 | 1.31 | 54% | 0.70 | 99 | 249 | 106 | 19.0% | 1.36 | 0.422% |
| flat-time charge, fallback flat, mean of 3 seeds | +364.0% | 0.90 | 1.26 | 45% | 0.77 | 75 | 175 | 126 | 15.2% | 1.26 | 0.494% |
| flat-time charge, no fallback, mean of 3 seeds | +406.1% | 0.89 | 1.25 | 62% | 0.60 | 98 | 229 | 129 | 18.9% | 1.28 | 0.422% |
| flat-time charge, fallback = trend reference, mean of 3 seeds | +314.9% | 0.78 | 1.09 | 61% | 0.52 | 93 | 219 | 151 | 18.7% | 1.16 | 0.386% |
| Buy-and-hold (perp) | +383.7% | 0.79 | 1.11 | 82% | 0.44 | 0 | 0 | 44784 | 14.0% | 0.96 | > 5% |
| Buy-and-hold (spot) | +889.1% | 0.96 | 1.35 | 81% | 0.69 | 0 | 0 | 44784 | 0.0% | 0.96 | > 5% |
| Momentum (daily 30-day, long/short) | +447.8% | 0.82 | 1.15 | 80% | 0.49 | 53 | 27 | 327 | 17.4% | 1.03 | 0.718% |
| Random agent (mean of 10) | -93.7% | -0.62 | -0.88 | 96% | -0.47 | 322 | 242 | 36 | 45.8% | - | - |
| *reference: buy-and-hold through the Phase 3 risk manager* | +347.2% | 0.83 | 1.17 | 63% | 0.54 | 16 | 69 | 44784 | 12.4% | 1.08 | 1.876% |
| *reference: momentum through the Phase 3 risk manager* | +505.7% | 0.93 | 1.33 | 70% | 0.60 | 62 | 126 | 327 | 14.9% | 1.22 | 0.669% |

### Phase 5's trade-less variants (reference, full span)

| Phase 5 variant (reference) | Asset | Net Sharpe 0.10% | Gross Sharpe | Max DD | Calmar | Turnover/yr |
|---|---|---|---|---|---|---|
| Phase 5 t1_band2x | BTCUSDT | 0.30 | 0.42 | 48% | 0.10 | 11 |
| Phase 5 t2_hold2d | BTCUSDT | 0.24 | 0.43 | 47% | 0.07 | 25 |
| Phase 5 t3_tilt | BTCUSDT | 0.83 | 0.91 | 80% | 0.49 | 24 |
| Phase 5 t1_band2x | ETHUSDT | 0.66 | 0.79 | 54% | 0.36 | 15 |
| Phase 5 t2_hold2d | ETHUSDT | 0.71 | 0.92 | 51% | 0.40 | 30 |
| Phase 5 t3_tilt | ETHUSDT | 0.82 | 0.90 | 85% | 0.47 | 32 |

## Where the gain comes from: the agent's folds vs the 'do no harm' folds

The 'trend' fallback hands the folds whose validation net Sharpe is under 0.5 to the daily momentum rule; those folds are flat under 'rule' and the model's own under 'none'. A large share of the 'trend' variants' gain is momentum's return in those folds, and the pattern behind it (the Phase 4 agent sat flat in folds where momentum made large gains: folds 6, 9, 12, 22 in Phase 4's per-fold table) was visible before Phase 6 was designed: hindsight risk.

| Variant | Asset | 'Do no harm' folds by seed (of 25) | Return in the agent's folds, by seed | Return in the 'do no harm' folds, by seed |
|---|---|---|---|---|
| Phase 4 primary, 'do no harm' = flat (as it is) | BTCUSDT | 9, 10, 10 | +94%, +58%, +86% | -0%, -0%, -1% |
| Phase 4 primary, 'do no harm' = flat (as it is) | ETHUSDT | 10, 10, 11 | +417%, +233%, +140% | -0%, +0%, -0% |
| Phase 4 primary, no fallback | BTCUSDT | 9, 10, 10 | +78%, +56%, +82% | +12%, -17%, +115% |
| Phase 4 primary, no fallback | ETHUSDT | 10, 10, 11 | +495%, +238%, +106% | +0%, -5%, +152% |
| Phase 4 primary, fallback = trend reference | BTCUSDT | 9, 10, 10 | +92%, +73%, +90% | +227%, +486%, +178% |
| Phase 4 primary, fallback = trend reference | ETHUSDT | 10, 10, 11 | +465%, +207%, +125% | +163%, +18%, +20% |
| missed-opportunity reward, fallback flat | BTCUSDT | 8, 4, 8 | +139%, +228%, +203% | +0%, -1%, +0% |
| missed-opportunity reward, fallback flat | ETHUSDT | 7, 8, 8 | +260%, +367%, +166% | -0%, +0%, -0% |
| missed-opportunity reward, no fallback | BTCUSDT | 8, 4, 8 | +172%, +248%, +189% | +8%, -31%, +21% |
| missed-opportunity reward, no fallback | ETHUSDT | 7, 8, 8 | +315%, +331%, +166% | +13%, +73%, -16% |
| missed-opportunity reward, fallback = trend reference | BTCUSDT | 8, 4, 8 | +159%, +238%, +212% | +228%, +7%, +49% |
| missed-opportunity reward, fallback = trend reference | ETHUSDT | 7, 8, 8 | +250%, +346%, +167% | +175%, +53%, +194% |
| flat-time charge, fallback flat | BTCUSDT | 11, 7, 9 | +70%, +147%, +286% | -0%, -0%, -0% |
| flat-time charge, fallback flat | ETHUSDT | 9, 9, 8 | +147%, +486%, +311% | +0%, +0%, -0% |
| flat-time charge, no fallback | BTCUSDT | 11, 7, 9 | +64%, +142%, +175% | +16%, -40%, -6% |
| flat-time charge, no fallback | ETHUSDT | 9, 9, 8 | +117%, +608%, +386% | +81%, -60%, -41% |
| flat-time charge, fallback = trend reference | BTCUSDT | 11, 7, 9 | +79%, +125%, +251% | +267%, +33%, +266% |
| flat-time charge, fallback = trend reference | ETHUSDT | 9, 9, 8 | +91%, +459%, +269% | +40%, +44%, +33% |

## Long vs short

| Variant | Asset | Long / short / flat (time) | Net from long bars /yr | Net from short bars /yr | Gross long /yr | Gross short /yr |
|---|---|---|---|---|---|---|
| Phase 4 primary, 'do no harm' = flat (as it is) | BTCUSDT | 42% / 8% / 50% | +13.2% | +1.1% | +19.9% | +2.0% |
| Phase 4 primary, 'do no harm' = flat (as it is) | ETHUSDT | 41% / 10% / 49% | +24.8% | +2.5% | +33.5% | +4.0% |
| Phase 4 primary, no fallback | BTCUSDT | 66% / 18% / 16% | +22.9% | -2.9% | +33.3% | -1.3% |
| Phase 4 primary, no fallback | ETHUSDT | 65% / 21% / 14% | +30.6% | +4.9% | +43.2% | +7.1% |
| Phase 4 primary, fallback = trend reference | BTCUSDT | 67% / 24% / 10% | +33.0% | +7.8% | +44.0% | +9.5% |
| Phase 4 primary, fallback = trend reference | ETHUSDT | 65% / 27% / 7% | +32.5% | +6.4% | +45.2% | +9.4% |
| missed-opportunity reward, fallback flat | BTCUSDT | 54% / 11% / 35% | +23.3% | +1.0% | +33.1% | +1.6% |
| missed-opportunity reward, fallback flat | ETHUSDT | 49% / 12% / 39% | +26.1% | +3.4% | +37.1% | +4.4% |
| missed-opportunity reward, no fallback | BTCUSDT | 70% / 20% / 10% | +29.7% | -3.5% | +41.4% | -2.6% |
| missed-opportunity reward, no fallback | ETHUSDT | 67% / 21% / 11% | +31.3% | +4.1% | +45.0% | +5.6% |
| missed-opportunity reward, fallback = trend reference | BTCUSDT | 70% / 22% / 8% | +31.9% | +4.8% | +44.4% | +6.2% |
| missed-opportunity reward, fallback = trend reference | ETHUSDT | 67% / 25% / 8% | +36.2% | +10.5% | +49.6% | +12.5% |
| flat-time charge, fallback flat | BTCUSDT | 50% / 14% / 36% | +21.7% | -0.7% | +30.5% | +1.3% |
| flat-time charge, fallback flat | ETHUSDT | 50% / 15% / 35% | +27.9% | +2.6% | +38.4% | +5.1% |
| flat-time charge, no fallback | BTCUSDT | 76% / 24% / 0% | +23.7% | -4.5% | +35.6% | -1.6% |
| flat-time charge, no fallback | ETHUSDT | 74% / 25% / 1% | +26.1% | +4.2% | +39.7% | +7.9% |
| flat-time charge, fallback = trend reference | BTCUSDT | 71% / 29% / 0% | +32.7% | +6.9% | +45.2% | +9.6% |
| flat-time charge, fallback = trend reference | ETHUSDT | 70% / 30% / 0% | +29.4% | +8.1% | +42.8% | +12.1% |
| Buy-and-hold (perp) | BTCUSDT | 100% / 0% / 0% | +38.3% | +0.0% | +49.3% | +0.0% |
| Buy-and-hold (perp) | ETHUSDT | 100% / 0% / 0% | +46.4% | +0.0% | +58.6% | +0.0% |
| Momentum (daily, L/S) | BTCUSDT | 55% / 45% / 0% | +38.1% | -0.3% | +50.7% | +1.4% |
| Momentum (daily, L/S) | ETHUSDT | 53% / 47% / 0% | +55.6% | +9.0% | +69.6% | +11.0% |

Full span, 0.10% a side, seed means; per-bar returns summed by the side held (a simple, additive split).

## Downtrends

| Variant | Asset | 2022 (2022-01-01 .. 2023-01-01) | current_decline (2025-10-06 .. 2026-11-11) | Down months: mean / profitable | Up months: mean |
|---|---|---|---|---|---|
| Phase 4 primary, 'do no harm' = flat (as it is) | BTCUSDT | -7.4% | -27.0% | -2.9% / 22% of 33 | +4.4% |
| Phase 4 primary, 'do no harm' = flat (as it is) | ETHUSDT | -7.7% | -8.1% | -1.9% / 19% of 36 | +6.1% |
| Phase 4 primary, no fallback | BTCUSDT | -43.9% | -37.6% | -4.7% / 29% of 33 | +6.8% |
| Phase 4 primary, no fallback | ETHUSDT | -38.5% | -17.2% | -3.1% / 31% of 36 | +8.5% |
| Phase 4 primary, fallback = trend reference | BTCUSDT | +6.9% | -24.5% | -1.5% / 43% of 33 | +7.4% |
| Phase 4 primary, fallback = trend reference | ETHUSDT | +1.5% | +30.9% | -1.7% / 33% of 36 | +8.1% |
| missed-opportunity reward, fallback flat | BTCUSDT | -11.6% | -23.2% | -3.6% / 20% of 33 | +6.4% |
| missed-opportunity reward, fallback flat | ETHUSDT | -13.1% | -14.6% | -2.3% / 22% of 36 | +6.8% |
| missed-opportunity reward, no fallback | BTCUSDT | -35.0% | -38.3% | -4.4% / 25% of 33 | +7.4% |
| missed-opportunity reward, no fallback | ETHUSDT | -36.5% | -14.7% | -2.7% / 32% of 36 | +8.0% |
| missed-opportunity reward, fallback = trend reference | BTCUSDT | -7.6% | -23.0% | -2.7% / 35% of 33 | +7.6% |
| missed-opportunity reward, fallback = trend reference | ETHUSDT | +4.8% | +26.8% | -1.0% / 34% of 36 | +8.5% |
| flat-time charge, fallback flat | BTCUSDT | -12.2% | -28.1% | -3.7% / 21% of 33 | +6.2% |
| flat-time charge, fallback flat | ETHUSDT | -7.4% | -18.7% | -3.1% / 19% of 36 | +8.0% |
| flat-time charge, no fallback | BTCUSDT | -42.1% | -55.8% | -5.9% / 25% of 33 | +7.9% |
| flat-time charge, no fallback | ETHUSDT | -40.9% | -40.6% | -4.6% / 31% of 36 | +9.4% |
| flat-time charge, fallback = trend reference | BTCUSDT | +2.9% | -34.9% | -1.7% / 41% of 33 | +7.5% |
| flat-time charge, fallback = trend reference | ETHUSDT | +2.1% | +15.9% | -2.3% / 34% of 36 | +8.7% |
| Buy-and-hold (perp) | BTCUSDT | -65.7% | -42.4% | -11.7% / 0% of 33 | +15.1% |
| Buy-and-hold (perp) | ETHUSDT | -67.7% | -55.7% | -13.8% / 0% of 36 | +20.3% |
| Momentum (daily, L/S) | BTCUSDT | -28.9% | -2.2% | +2.0% / 58% of 33 | +3.7% |
| Momentum (daily, L/S) | ETHUSDT | -0.2% | +32.7% | +0.0% / 44% of 36 | +9.9% |

Net of 0.10% fees, seed means. The current decline overlaps the strategy loop's sealed year; it is shown for RL only (nothing here is compared with the loop's rules there).

## By seed (full span): Sharpe / net return / break-even fee

**BTCUSDT**

| Variant | seed 0 | seed 1 | seed 2 | mean, 0.10% | mean, 0.05% |
|---|---|---|---|---|---|
| missed-opportunity reward, fallback = trend reference | 1.04 / +749% / 0.555% (0.05%: 1.15) | 0.73 / +262% / 0.336% (0.05%: 0.87) | 0.82 / +365% / 0.395% (0.05%: 0.91) | 0.87 / +459% | 0.98 / +638% |
| Phase 4 primary, 'do no harm' = flat (as it is) | 0.52 / +94% / 0.302% (0.05%: 0.59) | 0.40 / +58% / 0.290% (0.05%: 0.50) | 0.51 / +84% / 0.302% (0.05%: 0.59) | 0.48 / +79% | 0.56 / +106% |
| Phase 4 primary, no fallback | 0.49 / +99% / 0.258% (0.05%: 0.56) | 0.30 / +29% / 0.156% (0.05%: 0.42) | 0.83 / +292% / 0.400% (0.05%: 0.93) | 0.54 / +140% | 0.64 / +196% |
| Phase 4 primary, fallback = trend reference | 0.95 / +528% / 0.489% (0.05%: 1.01) | 1.12 / +917% / 0.674% (0.05%: 1.17) | 0.88 / +430% / 0.445% (0.05%: 0.96) | 0.98 / +625% | 1.05 / +746% |
| missed-opportunity reward, fallback flat | 0.61 / +139% / 0.363% (0.05%: 0.70) | 0.71 / +225% / 0.354% (0.05%: 0.82) | 0.73 / +203% / 0.408% (0.05%: 0.81) | 0.68 / +189% | 0.78 / +251% |
| missed-opportunity reward, no fallback | 0.66 / +194% / 0.346% (0.05%: 0.78) | 0.57 / +140% / 0.274% (0.05%: 0.69) | 0.74 / +251% / 0.366% (0.05%: 0.85) | 0.66 / +195% | 0.77 / +282% |
| flat-time charge, fallback flat | 0.43 / +70% / 0.246% (0.05%: 0.52) | 0.58 / +147% / 0.336% (0.05%: 0.66) | 0.84 / +285% / 0.468% (0.05%: 0.92) | 0.62 / +167% | 0.70 / +212% |
| flat-time charge, no fallback | 0.46 / +90% / 0.226% (0.05%: 0.55) | 0.36 / +46% / 0.178% (0.05%: 0.42) | 0.58 / +159% / 0.293% (0.05%: 0.71) | 0.47 / +98% | 0.56 / +157% |
| flat-time charge, fallback = trend reference | 0.93 / +556% / 0.449% (0.05%: 1.03) | 0.63 / +198% / 0.297% (0.05%: 0.73) | 1.17 / +1184% / 0.601% (0.05%: 1.23) | 0.91 / +646% | 1.00 / +820% |

**ETHUSDT**

| Variant | seed 0 | seed 1 | seed 2 | mean, 0.10% | mean, 0.05% |
|---|---|---|---|---|---|
| missed-opportunity reward, fallback = trend reference | 1.03 / +861% / 0.540% (0.05%: 1.11) | 0.90 / +582% / 0.465% (0.05%: 0.95) | 0.95 / +685% / 0.477% (0.05%: 1.05) | 0.96 / +709% | 1.04 / +909% |
| Phase 4 primary, 'do no harm' = flat (as it is) | 0.94 / +416% / 0.510% (0.05%: 1.04) | 0.75 / +234% / 0.408% (0.05%: 0.84) | 0.61 / +140% / 0.339% (0.05%: 0.69) | 0.77 / +263% | 0.86 / +341% |
| Phase 4 primary, no fallback | 0.91 / +496% / 0.423% (0.05%: 0.98) | 0.67 / +222% / 0.304% (0.05%: 0.77) | 0.86 / +419% / 0.388% (0.05%: 0.98) | 0.81 / +379% | 0.91 / +511% |
| Phase 4 primary, fallback = trend reference | 1.18 / +1388% / 0.609% (0.05%: 1.24) | 0.69 / +263% / 0.329% (0.05%: 0.77) | 0.59 / +171% / 0.281% (0.05%: 0.66) | 0.82 / +607% | 0.89 / +748% |
| missed-opportunity reward, fallback flat | 0.75 / +259% / 0.410% (0.05%: 0.83) | 0.84 / +368% / 0.475% (0.05%: 0.92) | 0.62 / +166% / 0.324% (0.05%: 0.71) | 0.74 / +264% | 0.82 / +341% |
| missed-opportunity reward, no fallback | 0.80 / +368% / 0.383% (0.05%: 0.89) | 0.96 / +645% / 0.443% (0.05%: 1.06) | 0.52 / +123% / 0.237% (0.05%: 0.61) | 0.76 / +379% | 0.85 / +512% |
| flat-time charge, fallback flat | 0.57 / +148% / 0.325% (0.05%: 0.67) | 0.92 / +486% / 0.572% (0.05%: 0.99) | 0.78 / +311% / 0.413% (0.05%: 0.84) | 0.76 / +315% | 0.83 / +394% |
| flat-time charge, no fallback | 0.71 / +294% / 0.343% (0.05%: 0.81) | 0.60 / +186% / 0.293% (0.05%: 0.67) | 0.60 / +185% / 0.270% (0.05%: 0.65) | 0.64 / +222% | 0.71 / +303% |
| flat-time charge, fallback = trend reference | 0.57 / +167% / 0.270% (0.05%: 0.67) | 0.94 / +707% / 0.504% (0.05%: 1.00) | 0.78 / +390% / 0.376% (0.05%: 0.83) | 0.76 / +421% | 0.84 / +535% |

## Edge before costs

| Variant | Asset | Span | Gross Sharpe by seed | Mean | t (approx.) | Break-even fee by seed | Net Sharpe 0.10% (mean) |
|---|---|---|---|---|---|---|---|
| missed-opportunity reward, fallback = trend reference | BTCUSDT | 2020-10 .. 2026-11 | 1.39, 1.14, 1.20 | 1.24 | 3.1 | 0.555%, 0.336%, 0.395% | 0.87 |
| missed-opportunity reward, fallback = trend reference | BTCUSDT | to 2025-11-11 | 1.57, 1.32, 1.42 | 1.44 | 3.2 | 0.666%, 0.403%, 0.517% | 1.05 |
| missed-opportunity reward, fallback = trend reference | ETHUSDT | 2020-10 .. 2026-11 | 1.39, 1.26, 1.33 | 1.33 | 3.3 | 0.540%, 0.465%, 0.477% | 0.96 |
| missed-opportunity reward, fallback = trend reference | ETHUSDT | to 2025-11-11 | 1.59, 1.22, 1.34 | 1.38 | 3.1 | 0.628%, 0.423%, 0.460% | 0.99 |
| Phase 4 primary, 'do no harm' = flat (as it is) | BTCUSDT | 2020-10 .. 2026-11 | 0.84, 0.65, 0.84 | 0.78 | 1.9 | 0.302%, 0.290%, 0.302% | 0.48 |
| Phase 4 primary, 'do no harm' = flat (as it is) | BTCUSDT | to 2025-11-11 | 1.04, 0.80, 1.14 | 0.99 | 2.2 | 0.384%, 0.366%, 0.429% | 0.67 |
| Phase 4 primary, 'do no harm' = flat (as it is) | ETHUSDT | 2020-10 .. 2026-11 | 1.30, 1.10, 0.95 | 1.11 | 2.8 | 0.510%, 0.408%, 0.339% | 0.77 |
| Phase 4 primary, 'do no harm' = flat (as it is) | ETHUSDT | to 2025-11-11 | 1.54, 1.13, 1.01 | 1.23 | 2.8 | 0.614%, 0.387%, 0.341% | 0.86 |
| Phase 4 primary, no fallback | BTCUSDT | 2020-10 .. 2026-11 | 0.87, 0.68, 1.23 | 0.92 | 2.3 | 0.258%, 0.156%, 0.400% | 0.54 |
| Phase 4 primary, no fallback | BTCUSDT | to 2025-11-11 | 1.18, 0.90, 1.55 | 1.21 | 2.7 | 0.391%, 0.234%, 0.515% | 0.80 |
| Phase 4 primary, no fallback | ETHUSDT | 2020-10 .. 2026-11 | 1.30, 1.08, 1.28 | 1.22 | 3.0 | 0.423%, 0.304%, 0.388% | 0.81 |
| Phase 4 primary, no fallback | ETHUSDT | to 2025-11-11 | 1.55, 1.24, 1.40 | 1.40 | 3.2 | 0.517%, 0.360%, 0.415% | 0.97 |
| Phase 4 primary, fallback = trend reference | BTCUSDT | 2020-10 .. 2026-11 | 1.29, 1.42, 1.23 | 1.31 | 3.3 | 0.489%, 0.674%, 0.445% | 0.98 |
| Phase 4 primary, fallback = trend reference | BTCUSDT | to 2025-11-11 | 1.52, 1.58, 1.50 | 1.53 | 3.5 | 0.626%, 0.802%, 0.588% | 1.20 |
| Phase 4 primary, fallback = trend reference | ETHUSDT | 2020-10 .. 2026-11 | 1.53, 1.07, 0.96 | 1.19 | 2.9 | 0.609%, 0.329%, 0.281% | 0.82 |
| Phase 4 primary, fallback = trend reference | ETHUSDT | to 2025-11-11 | 1.61, 1.03, 0.91 | 1.18 | 2.7 | 0.643%, 0.290%, 0.232% | 0.79 |
| missed-opportunity reward, fallback flat | BTCUSDT | 2020-10 .. 2026-11 | 0.93, 1.11, 1.08 | 1.04 | 2.6 | 0.363%, 0.354%, 0.408% | 0.68 |
| missed-opportunity reward, fallback flat | BTCUSDT | to 2025-11-11 | 1.03, 1.34, 1.32 | 1.23 | 2.8 | 0.389%, 0.421%, 0.508% | 0.85 |
| missed-opportunity reward, fallback flat | ETHUSDT | 2020-10 .. 2026-11 | 1.10, 1.20, 1.00 | 1.10 | 2.7 | 0.410%, 0.475%, 0.324% | 0.74 |
| missed-opportunity reward, fallback flat | ETHUSDT | to 2025-11-11 | 1.42, 1.31, 1.08 | 1.27 | 2.9 | 0.564%, 0.507%, 0.338% | 0.89 |
| missed-opportunity reward, no fallback | BTCUSDT | 2020-10 .. 2026-11 | 1.03, 0.98, 1.14 | 1.05 | 2.6 | 0.346%, 0.274%, 0.366% | 0.66 |
| missed-opportunity reward, no fallback | BTCUSDT | to 2025-11-11 | 1.24, 1.30, 1.48 | 1.34 | 3.0 | 0.426%, 0.383%, 0.502% | 0.92 |
| missed-opportunity reward, no fallback | ETHUSDT | 2020-10 .. 2026-11 | 1.19, 1.37, 0.95 | 1.17 | 2.9 | 0.383%, 0.443%, 0.237% | 0.76 |
| missed-opportunity reward, no fallback | ETHUSDT | to 2025-11-11 | 1.44, 1.41, 1.21 | 1.36 | 3.1 | 0.490%, 0.438%, 0.338% | 0.93 |
| flat-time charge, fallback flat | BTCUSDT | 2020-10 .. 2026-11 | 0.75, 0.91, 1.17 | 0.94 | 2.3 | 0.246%, 0.336%, 0.468% | 0.62 |
| flat-time charge, fallback flat | BTCUSDT | to 2025-11-11 | 0.92, 1.06, 1.40 | 1.13 | 2.5 | 0.317%, 0.375%, 0.575% | 0.78 |
| flat-time charge, fallback flat | ETHUSDT | 2020-10 .. 2026-11 | 0.89, 1.24, 1.16 | 1.09 | 2.7 | 0.325%, 0.572%, 0.413% | 0.76 |
| flat-time charge, fallback flat | ETHUSDT | to 2025-11-11 | 1.10, 1.38, 1.29 | 1.26 | 2.8 | 0.424%, 0.611%, 0.448% | 0.90 |
| flat-time charge, no fallback | BTCUSDT | 2020-10 .. 2026-11 | 0.83, 0.72, 0.95 | 0.83 | 2.1 | 0.226%, 0.178%, 0.293% | 0.47 |
| flat-time charge, no fallback | BTCUSDT | to 2025-11-11 | 1.12, 1.10, 1.34 | 1.19 | 2.7 | 0.357%, 0.362%, 0.494% | 0.81 |
| flat-time charge, no fallback | ETHUSDT | 2020-10 .. 2026-11 | 1.07, 0.96, 1.00 | 1.01 | 2.5 | 0.343%, 0.293%, 0.270% | 0.64 |
| flat-time charge, no fallback | ETHUSDT | to 2025-11-11 | 1.33, 1.29, 1.22 | 1.28 | 2.9 | 0.458%, 0.455%, 0.354% | 0.89 |
| flat-time charge, fallback = trend reference | BTCUSDT | 2020-10 .. 2026-11 | 1.29, 1.00, 1.52 | 1.27 | 3.1 | 0.449%, 0.297%, 0.601% | 0.91 |
| flat-time charge, fallback = trend reference | BTCUSDT | to 2025-11-11 | 1.46, 1.23, 1.80 | 1.50 | 3.4 | 0.551%, 0.425%, 0.801% | 1.14 |
| flat-time charge, fallback = trend reference | ETHUSDT | 2020-10 .. 2026-11 | 0.94, 1.28, 1.16 | 1.13 | 2.8 | 0.270%, 0.504%, 0.376% | 0.76 |
| flat-time charge, fallback = trend reference | ETHUSDT | to 2025-11-11 | 0.96, 1.34, 1.17 | 1.16 | 2.6 | 0.268%, 0.533%, 0.358% | 0.78 |

## Flags

**BTCUSDT**

| Variant | train_test_sharpe_gap | seed_dispersion | beats_benchmarks_in_under_half_the_folds | fee_sign_flip | edge_only_at_0.05 | high_turnover | degenerate_policy | turnover exploded |
|---|---|---|---|---|---|---|---|---|
| missed-opportunity reward, fallback = trend reference | FIRED | - | FIRED | - | - | - | - | - (84 /yr, 178 trades) |
| Phase 4 primary, 'do no harm' = flat (as it is) | FIRED | - | FIRED | - | - | - | - | - (47 /yr, 110 trades) |
| Phase 4 primary, no fallback | FIRED | - | FIRED | - | - | - | - | - (73 /yr, 173 trades) |
| Phase 4 primary, fallback = trend reference | FIRED | - | FIRED | - | - | - | - | - (74 /yr, 157 trades) |
| missed-opportunity reward, fallback flat | FIRED | - | FIRED | - | - | - | - | - (63 /yr, 139 trades) |
| missed-opportunity reward, no fallback | FIRED | - | FIRED | - | - | - | - | - (77 /yr, 174 trades) |
| flat-time charge, fallback flat | FIRED | - | FIRED | - | FIRED | - | - | - (61 /yr, 131 trades) |
| flat-time charge, no fallback | FIRED | - | FIRED | - | - | - | - | - (81 /yr, 187 trades) |
| flat-time charge, fallback = trend reference | FIRED | - | FIRED | - | - | - | - | - (87 /yr, 181 trades) |

**ETHUSDT**

| Variant | train_test_sharpe_gap | seed_dispersion | beats_benchmarks_in_under_half_the_folds | fee_sign_flip | edge_only_at_0.05 | high_turnover | degenerate_policy | turnover exploded |
|---|---|---|---|---|---|---|---|---|
| missed-opportunity reward, fallback = trend reference | - | - | FIRED | - | - | - | - | - (86 /yr, 205 trades) |
| Phase 4 primary, 'do no harm' = flat (as it is) | FIRED | - | FIRED | - | - | - | - | - (63 /yr, 158 trades) |
| Phase 4 primary, no fallback | - | - | FIRED | - | - | - | - | - (92 /yr, 238 trades) |
| Phase 4 primary, fallback = trend reference | FIRED | - | FIRED | - | - | - | - | - (89 /yr, 214 trades) |
| missed-opportunity reward, fallback flat | FIRED | - | FIRED | - | - | - | - | - (69 /yr, 167 trades) |
| missed-opportunity reward, no fallback | FIRED | - | FIRED | - | - | - | - | - (94 /yr, 234 trades) |
| flat-time charge, fallback flat | FIRED | - | FIRED | - | - | - | - | - (67 /yr, 156 trades) |
| flat-time charge, no fallback | FIRED | - | - | - | - | FIRED | - | - (94 /yr, 222 trades) |
| flat-time charge, fallback = trend reference | - | - | FIRED | - | - | - | - | - (91 /yr, 208 trades) |

## Clearly beats the Phase 4 primary? (frozen rule)

- Phase 4 primary, no fallback: **no**. BTCUSDT: Sharpe 0.54 vs 0.48 (+0.10 needed), seeds 0.49, 0.30, 0.83, Calmar 0.23 vs 0.24, to 2025-11-11 0.80 vs 0.67; ETHUSDT: Sharpe 0.81 vs 0.77 (+0.10 needed), seeds 0.91, 0.67, 0.86, Calmar 0.53 vs 0.49, to 2025-11-11 0.97 vs 0.86
- Phase 4 primary, fallback = trend reference: **no**. BTCUSDT: Sharpe 0.98 vs 0.48, seeds 0.95, 1.12, 0.88, Calmar 0.89 vs 0.24, to 2025-11-11 1.20 vs 0.67; ETHUSDT: Sharpe 0.82 vs 0.77 (+0.10 needed), seeds 1.18, 0.69, 0.59, Calmar 0.59 vs 0.49, to 2025-11-11 0.79 vs 0.86
- missed-opportunity reward, fallback flat: **no**. BTCUSDT: Sharpe 0.68 vs 0.48, seeds 0.61, 0.71, 0.73, Calmar 0.43 vs 0.24, to 2025-11-11 0.85 vs 0.67; ETHUSDT: Sharpe 0.74 vs 0.77 (+0.10 needed), seeds 0.75, 0.84, 0.62, Calmar 0.45 vs 0.49, to 2025-11-11 0.89 vs 0.86
- missed-opportunity reward, no fallback: **no**. BTCUSDT: Sharpe 0.66 vs 0.48, seeds 0.66, 0.57, 0.74, Calmar 0.33 vs 0.24, to 2025-11-11 0.92 vs 0.67; ETHUSDT: Sharpe 0.76 vs 0.77 (+0.10 needed), seeds 0.80, 0.96, 0.52, Calmar 0.52 vs 0.49, to 2025-11-11 0.93 vs 0.86
- missed-opportunity reward, fallback = trend reference: **yes**. BTCUSDT: Sharpe 0.87 vs 0.48, seeds 1.04, 0.73, 0.82, Calmar 0.68 vs 0.24, to 2025-11-11 1.05 vs 0.67; ETHUSDT: Sharpe 0.96 vs 0.77, seeds 1.03, 0.90, 0.95, Calmar 0.66 vs 0.49, to 2025-11-11 0.99 vs 0.86
- flat-time charge, fallback flat: **no**. BTCUSDT: Sharpe 0.62 vs 0.48, seeds 0.43, 0.58, 0.84, Calmar 0.33 vs 0.24, to 2025-11-11 0.78 vs 0.67; ETHUSDT: Sharpe 0.76 vs 0.77 (+0.10 needed), seeds 0.57, 0.92, 0.78, Calmar 0.56 vs 0.49, to 2025-11-11 0.90 vs 0.86
- flat-time charge, no fallback: **no**. BTCUSDT: Sharpe 0.47 vs 0.48 (+0.10 needed), seeds 0.46, 0.36, 0.58, Calmar 0.18 vs 0.24, to 2025-11-11 0.81 vs 0.67; ETHUSDT: Sharpe 0.64 vs 0.77 (+0.10 needed), seeds 0.71, 0.60, 0.60, Calmar 0.33 vs 0.49, to 2025-11-11 0.89 vs 0.86
- flat-time charge, fallback = trend reference: **no**. BTCUSDT: Sharpe 0.91 vs 0.48, seeds 0.93, 0.63, 1.17, Calmar 0.75 vs 0.24, to 2025-11-11 1.14 vs 0.67; ETHUSDT: Sharpe 0.76 vs 0.77 (+0.10 needed), seeds 0.57, 0.94, 0.78, Calmar 0.49 vs 0.49, to 2025-11-11 0.78 vs 0.86

**Proposal (not wired in):** a second forward paper book for missed-opportunity reward, fallback = trend reference, in playbook5's style (same live step, its own models, the chosen 'do no harm' mode), NOT passed, with 8 variants tried stated on the page.

## What was frozen, and when

- 12 Nov 2026, ~08:45 UTC: written and frozen while Phase 5's ablation was still training; no Phase 6 model or number existed. The literal 'net return - beta x reference return' was dropped before any run because it cannot change a decision (see the reward section); replaced by its action-dependent form (r_missed)
- Training: 243 min, memory pauses: none
- Evaluation: 2 min, memory pauses: none

Machine-readable: `phase6_summary.json`. Nothing here is wired into the live engine.
