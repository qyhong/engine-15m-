# Harness study (loop round 1): can a harness turn an over-trading 15m strategy into one that beats buy-and-hold?

Generated 2026-11-11 13:54 UTC by `py -3 research/harness/run.py`. Paper research only; nothing here places orders. Hypotheses H20-H24 were registered in `research/HYPOTHESES.md` at 13:45 UTC on 11 Nov 2026, before any harness result existed. **Development data only:** the last 12 months (2025-11-11 to 2026-11-11) are a sealed holdout that no number in this report has touched. No holdout look was used in round 1 (see `research/harness/LOOP.md`).

## Summary (round 1)

**Thesis:** a 15m strategy that trades too often can be turned, by a filter or harness, into one that trades far
less AND beats buy-and-hold out of sample after 0.10% fees. **Verdict: not supported.** Filtering cuts trades and
costs, as expected, but filtering a no-edge 15m signal ends between flat and a loss; it never beats buy-and-hold. The
two harnesses built on something that already has an edge (the daily 30-day momentum rule, or a buy-and-hold core)
make 27-42% a year net, but they do not beat buy-and-hold risk-adjusted on BTC, beat it on ETH by a statistically
meaningless margin, and lose to it in most folds. No candidate is a development pass, so no holdout look was taken.

**What the numbers say (BTC, development out of sample Oct 2020 - Nov 2025, 0.10% a side):**

- **Trade count vs net return.** On every base, the first cuts in trading do almost all the work: the 16-bar momentum
  base goes from ~4,500 trades a year (-100%, cost drag ~1,200% a year) to ~350 (-60%) with a 24-hour minimum hold and
  to about -17% a year once a daily-trend filter is added. Below ~300 trades a year the costs stop being the story and
  the lack of edge is: gross Sharpe of the frequent bases is about -0.3 to +0.5, i.e. a coin. The only filter ladder
  that ended positive is the EMA20/50 base with the daily-trend filter and a confidence threshold (~70 trades a year,
  +5% a year on BTC, +20% on ETH, Sharpe 0.32 / 0.71): that is the daily momentum rule's edge leaking through the
  filter, not an edge of the 15m signal. On training data the same picture: median Sharpe -0.06 at 30-100 trades a
  year, -0.68 at 100-300, -2.1 at 300-1,000, -5.6 above 1,000; no bucket's median beats zero by much.
- **Family 1 (H20, walk-forward selected from 864 filter stacks):** 141 trades a year, -12% a year, Sharpe -0.18,
  break-even fee 0.015% a side. Walk-forward selection jumps between bases and filters from fold to fold: there is
  nothing stable to select.
- **Family 2 (H22, meta-labeling on daily momentum):** +26.8% a year, Sharpe 0.81 vs buy-and-hold 0.83, max DD 58%
  vs 79%, 46 trades a year, break-even fee 0.63%. It beats momentum (+25.4%, Sharpe 0.67) and matches buy-and-hold's
  Sharpe with a much smaller drawdown, but does not beat buy-and-hold's Sharpe or Calmar at 0.10% (it does at 0.05%:
  flagged, not crowned). On ETH under the same rules: +35.8% a year, Sharpe 0.88 vs 0.79, Calmar 0.53 vs 0.44, max DD
  68% vs 82%. Sharpe beat buy-and-hold in only 38% (BTC) / 43% (ETH) of folds, and the bootstrap p-values (0.37 /
  0.30) are nowhere near the Bonferroni level. The walk-forward chose long-only (short size 0) in most BTC folds and
  vol-regime sizing (R1) in most folds on both coins; the 15m pullback entry (E1/E2) was chosen often on ETH.
- **Family 3 (H23, core-satellite, 1x core tilted within a band):** +29.9% a year on BTC, +41.6% on ETH, but more
  drawdown than buy-and-hold on ETH (85% vs 82%) and a lower Sharpe on BTC; the tilt the walk-forward picked was
  mostly the daily momentum signal (the 4h trend in most of the rest), never the 15m one.
- **Family 4 (H24, Mind 15's replay trades):** keeping only trades on the side of daily momentum roughly halves the
  trade count and raises the mean per trade on BTC's first half and on ETH, but not on BTC's second half, so the
  registered test is not met. In-sample in any case.

**Against the loop target (CAGR >= 25%, max DD <= buy-and-hold, > half the folds positive, flags clear):** H22 meets
the three numeric criteria on both BTC and ETH (CAGR 26.8% / 35.8%) but fails the flags (fold share, significance,
and on BTC "beats buy-and-hold only at 0.05%"). H23 meets the CAGR level on both but fails drawdown on ETH. So: the
10% milestone and the 25% level are reached on CAGR by H22 and H23, but nothing is a development pass. Note that over
the development span buy-and-hold itself made 38% a year on BTC and 36% on ETH, so 25% is below buy-and-hold here;
the 25% target is above buy-and-hold only over spans that include weaker years.

**Multiple testing:** 919 variants per asset (1,838 in all) were run in round 1; 27 strategies per asset were
graded. Walk-forward selection keeps each test window unseen by its own choice, so the headline numbers already pay
for the selection inside each family; the deflated Sharpe probabilities (0.06-0.11 for H22/H23 with 919 trials) say
that none of these Sharpe ratios is distinguishable from the best of many null strategies.

**Candidate for forward paper running:** none qualifies under the loop rules (a forward run follows a historical pass
only). If the owner wants a paper yardstick anyway, the closest is H22, frozen as registered: direction = sign of the
30-day return at the 00:00 UTC close; walk-forward re-selection each quarter on the trailing 12 months over the 36-variant
grid; the variant the procedure picks at the seal (trained 2024-11-11 to 2025-11-11, development data only) is, on BTC,
**long-only (short size 0), vol-regime size (1x when the 672-bar realised vol is at or below its trailing 365-day median
of daily readings, else 0.5x, set at each 00:00 UTC close), and a 15m pullback entry after each new daily direction
(wait up to 48 bars for a 15m close at or below EMA20 - 1.0 x ATR14, enter at the next open, or enter at bar 48)**; on
ETH: short size 0.5, the same vol-regime size, entry at the next open. It would be a yardstick, not evidence.

## Proposed round 2 (informed by development data only; register before running)

1. **H25 Vol-targeted daily momentum, 15m rebalancing.** Direction = daily 30-day momentum (long-only and 0.5x-short
   variants); size = min(1.5, 40% annual vol target / 7-day realised vol), re-sized on the 15m clock only when the
   target exposure drifts more than 25% from the held one. Why: vol-regime sizing (R1) was chosen in 14 of 21 folds on
   both coins in H22; leverage up to 1.5x in calm trends is the plausible route to more CAGR with less drawdown.
2. **H26 Momentum ensemble.** Exposure = mean of the signs of the 10, 20, 30, 60 and 90-day returns (long-only and
   long/short), decided daily, 15m pullback entry fixed as E2. Why: H22's single 30-day lookback wins in only ~40% of
   folds; an ensemble is less fold-dependent. No walk-forward selection (one fixed rule per variant, few variants).
3. **H27 Two-coin book.** H22 and H25 run 50/50 on BTC and ETH in one book. Why: the two coins' fold results differ
   (e.g. 2022-Q2, 2023-Q1), so a joint book may clear the drawdown and fold criteria that each misses alone.
4. **H28 Fixed H22 variant, no selection.** Long-only, vol-regime size, E2 pullback entry (the variant chosen most
   often on both coins) as one frozen rule, to measure how much the per-fold selection costs or adds.
5. **H29 Funding-aware execution.** The long legs of H22/H25 held as spot (no funding), shorts on the perp; the
   benchmark likewise as spot buy-and-hold. Why: funding cost longs about 12% a year on BTC over the development span.
6. **Owner decision before round 2 (not after its results):** whether the `fold_share` flag (Sharpe above
   buy-and-hold's in at least half the folds) and the Bonferroni significance flag stay as they are. As set, a
   strategy that sits out falling markets will rarely beat buy-and-hold's Sharpe in half the folds, and p <= 0.002
   needs a very large edge. Changing them is legitimate only before round 2 is run.

Not worth a round 2 slot, on development evidence: more filters on frequent 15m bases (H20/H21: no edge before
costs), and 15m tilts of a buy-and-hold core (the walk-forward never chose the 15m signal).

## Method

- Markets: BTCUSDT perpetual (the RL Phase 2 bars and funding, `data/rl/`), then ETHUSDT (engine spot 15m bars + perp funding) under identical rules. Bars 2019-09-08 19:00 to 2025-11-10 23:45 (BTC).

- Walk-forward: the RL Phase 1/2 folds cut at the seal: 12-month train, next 3 months test, roll 3 months; 21 folds; development out of sample = stitched test windows 2020-10-01 to 2025-11-11. In each fold the variant with the best train-window net Sharpe at 0.10% is used on the test window; one backtest runs over the stitched series (positions and costs carry across fold edges). The 0.05% line re-runs the same selections.

- Costs: `engine15.rl.costs` exactly (a test checks the lean backtester equals `engine15.rl.backtest` to 1e-15 per bar): fee 0.10% a side (headline) or 0.05%, half-spread 0.5 bp, slippage 0.10 x 96-bar vol, funding on the position held at each settlement. Decide at a bar's close, fill at the next open. Above 1x (family 3) every cost term scales linearly.

- Metrics: `engine15.rl.metrics` (15m bars, 35,040 a year). CAGR = (final / initial)^(1 / years) - 1 of the stitched out-of-sample equity, net of fees and funding. Trades/yr = position changes a year (a tilt counts). Break-even fee = the fee a side at which the stitched net return is zero.

- Benchmarks over the same span and costs: buy-and-hold 1x; the frozen daily 30-day momentum rule (long/short); a random strategy with the same number of position changes (10 seeds, levels drawn from the strategy's own); Phase 1's daily random agent; the RL Phase 2 agent for reference (its numbers cover Oct 2020 to Nov 2026, holdout included, so they are not on the same span).

- Multiple testing: 919 variants per asset this round (27 graded strategies per asset: 3 walk-forward headlines + 24 ladder levels). Each graded strategy gets a paired block-bootstrap p-value for Sharpe minus buy-and-hold Sharpe (daily returns, 20-day blocks, 2,000 draws), judged at the Bonferroni level 0.05 / 27 = 0.0019, and a deflated Sharpe probability with 919 trials (crude, assumes independent trials: a caution, not a test).

## BTCUSDT: development out of sample 2020-10-01 to 2025-11-11

### Annual return (CAGR) against the target, 0.10%% a side

| Strategy | CAGR | vs 25% target | vs buy-and-hold (+38.1%) | vs momentum (+25.4%) | 10% milestone | Max DD (B&H 79%) | Positive folds | Development pass |
|---|---|---|---|---|---|---|---|---|
| H20 Family 1 | -12.4% | -37.4% | -50.4% | -37.8% | no | 70% | 43% | no |
| H22 Family 2 | +26.8% | +1.8% | -11.3% | +1.4% | CAGR only | 58% | 52% | no |
| H23 Family 3 | +29.9% | +4.9% | -8.1% | +4.6% | CAGR only | 77% | 48% | no |
| H21 mom L0 base | -100.0% | -125.0% | -138.1% | -125.4% | no | 100% | 0% | no |
| H21 mom L1 +hold16 | -99.5% | -124.5% | -137.5% | -124.8% | no | 100% | 0% | no |
| H21 mom L2 hold96 | -59.7% | -84.7% | -97.7% | -85.1% | no | 99% | 29% | no |
| H21 mom L3 +trend1d | -16.7% | -41.7% | -54.8% | -42.1% | no | 81% | 33% | no |
| H21 mom L4 +confidence | -21.6% | -46.6% | -59.7% | -47.0% | no | 81% | 38% | no |
| H21 mom L5 +costgate | -26.2% | -51.2% | -64.2% | -51.5% | no | 87% | 48% | no |
| H21 mom L6 +session | -16.8% | -41.8% | -54.9% | -42.2% | no | 81% | 29% | no |
| H21 mom L7 +cooldown | -19.3% | -44.3% | -57.4% | -44.7% | no | 84% | 24% | no |
| H21 ema L0 base | -85.8% | -110.8% | -123.8% | -111.2% | no | 100% | 5% | no |
| H21 ema L1 +hold16 | -86.7% | -111.7% | -124.7% | -112.1% | no | 100% | 0% | no |
| H21 ema L2 hold96 | -72.9% | -97.9% | -111.0% | -98.3% | no | 100% | 5% | no |
| H21 ema L3 +trend1d | -28.6% | -53.6% | -66.7% | -54.0% | no | 92% | 29% | no |
| H21 ema L4 +confidence | +5.1% | -19.9% | -33.0% | -20.3% | no | 53% | 48% | no |
| H21 ema L5 +costgate | +3.7% | -21.3% | -34.4% | -21.7% | no | 52% | 38% | no |
| H21 ema L6 +session | -1.8% | -26.8% | -39.9% | -27.2% | no | 53% | 38% | no |
| H21 ema L7 +cooldown | -1.8% | -26.8% | -39.9% | -27.2% | no | 53% | 38% | no |
| H21 mr L0 base | -86.4% | -111.4% | -124.5% | -111.8% | no | 100% | 0% | no |
| H21 mr L1 +hold16 | -82.5% | -107.5% | -120.5% | -107.9% | no | 100% | 0% | no |
| H21 mr L2 hold96 | -46.4% | -71.4% | -84.5% | -71.8% | no | 96% | 14% | no |
| H21 mr L3 +trend1d | -28.6% | -53.6% | -66.6% | -54.0% | no | 92% | 33% | no |
| H21 mr L4 +confidence | -21.3% | -46.3% | -59.3% | -46.6% | no | 82% | 29% | no |
| H21 mr L5 +costgate | -21.7% | -46.7% | -59.8% | -47.1% | no | 83% | 24% | no |
| H21 mr L6 +session | -21.8% | -46.8% | -59.8% | -47.2% | no | 82% | 38% | no |
| H21 mr L7 +cooldown | -24.0% | -49.0% | -62.0% | -49.4% | no | 83% | 33% | no |
| Buy-and-hold | +38.1% | +13.1% | 0 | +12.7% | | 79% | | |
| Momentum (daily, 30-day) | +25.4% | +0.4% | -12.7% | 0 | | 63% | | |

### Headline table, 0.10% a side

| Strategy | CAGR | Net return | Sharpe | Gross Sharpe | Sortino | Max DD | Calmar | Trades/yr | Avg hold (h) | Cost drag/yr | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **H20 Family 1: filter stack on 15m bases (walk-forward selected)** | -12.4% | -49% | -0.18 | 0.49 | -0.26 | 70% | -0.18 | 141 | 24 | 24.6% | 0.015% |
| **H22 Family 2: meta-labeling on daily momentum (walk-forward selected)** | +26.8% | +236% | 0.81 | 1.15 | 1.15 | 58% | 0.46 | 46 | 240 | 13.1% | 0.627% |
| **H23 Family 3: core-satellite overlay (walk-forward selected)** | +29.9% | +282% | 0.74 | 1.12 | 1.04 | 77% | 0.39 | 66 | 434 | 22.5% | 0.455% |
| Buy-and-hold | +38.1% | +420% | 0.83 | 1.03 | 1.18 | 79% | 0.48 | 0 | whole span | 12.4% | > 4% |
| Momentum (daily, 30-day, long/short) | +25.4% | +218% | 0.67 | 0.92 | 0.95 | 63% | 0.41 | 30 | 293 | 15.2% | 0.478% |
| Random agent, daily (Phase 1), mean of 10 | -43.4% | -92% | -0.91 | -0.06 | -1.28 | 95% | -0.45 | 243 | 36 | 43.0% | - |
| Random, matched to H20 (mean of 10) | -31.4% | -81% | -0.50 | | | 89% | | (same) | | | |
| Random, matched to H22 (mean of 10) | -3.7% | +81% | 0.04 | | | 69% | | (same) | | | |
| Random, matched to H23 (mean of 10) | +10.1% | +86% | 0.45 | | | 84% | | (same) | | | |
| *RL Phase 2 agent, mean of 5 seeds (Oct 2020 - Nov 2026, not the same span)* | - | -100% | -1.92 | | -2.70 | 100% | -0.60 | ~600 turnover | 17 | 79% | |

### Headline table, 0.05% a side

| Strategy | CAGR | Net return | Sharpe | Gross Sharpe | Sortino | Max DD | Calmar | Trades/yr | Avg hold (h) | Cost drag/yr | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **H20 Family 1: filter stack on 15m bases (walk-forward selected)** | -5.3% | -24% | 0.03 | 0.49 | 0.04 | 66% | -0.08 | 141 | 24 | 16.8% | - |
| **H22 Family 2: meta-labeling on daily momentum (walk-forward selected)** | +29.6% | +277% | 0.87 | 1.15 | 1.23 | 57% | 0.52 | 46 | 240 | 10.8% | - |
| **H23 Family 3: core-satellite overlay (walk-forward selected)** | +34.8% | +361% | 0.80 | 1.12 | 1.13 | 76% | 0.46 | 66 | 434 | 18.8% | - |
| Buy-and-hold | +38.1% | +420% | 0.83 | 1.03 | 1.18 | 79% | 0.48 | 0 | whole span | 12.4% | - |
| Momentum (daily, 30-day, long/short) | +29.2% | +270% | 0.72 | 0.92 | 1.02 | 61% | 0.48 | 30 | 293 | 12.3% | - |

### Graded strategies: registered criteria and flags (BTCUSDT)

| Strategy | T: <=100 trades/yr | beats B&H Sharpe+Calmar | Sharpe > B&H in >= half folds | > matched random | Thesis pass | Flags fired | Boot p (Sharpe - B&H) | DSR prob |
|---|---|---|---|---|---|---|---|---|
| H20 Family 1 | no | no | no (38%) | yes | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |
| H22 Family 2 | yes | no | no (38%) | yes | no | fold_share, fee_only_at_0.05, not_significant | 0.367 | 0.08 |
| H23 Family 3 | yes | no | no (33%) | yes | no | fold_share, not_significant, eth_fails | 1.000 | 0.06 |
| H21 mom L0 base | no | no | no (0%) | no | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |
| H21 mom L1 +hold16 | no | no | no (0%) | no | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |
| H21 mom L2 hold96 | no | no | no (24%) | no | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |
| H21 mom L3 +trend1d | no | no | no (19%) | yes | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |
| H21 mom L4 +confidence | no | no | no (29%) | yes | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |
| H21 mom L5 +costgate | no | no | no (29%) | yes | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |
| H21 mom L6 +session | no | no | no (24%) | yes | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |
| H21 mom L7 +cooldown | no | no | no (24%) | yes | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |
| H21 ema L0 base | no | no | no (10%) | yes | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |
| H21 ema L1 +hold16 | no | no | no (10%) | no | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |
| H21 ema L2 hold96 | no | no | no (19%) | no | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |
| H21 ema L3 +trend1d | no | no | no (24%) | yes | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |
| H21 ema L4 +confidence | yes | no | no (33%) | yes | no | fold_share, not_significant | 1.000 | 0.01 |
| H21 ema L5 +costgate | yes | no | no (29%) | yes | no | fold_share, not_significant | 1.000 | 0.00 |
| H21 ema L6 +session | yes | no | no (29%) | yes | no | fold_share, not_significant | 1.000 | 0.00 |
| H21 ema L7 +cooldown | yes | no | no (29%) | yes | no | fold_share, not_significant | 1.000 | 0.00 |
| H21 mr L0 base | no | no | no (0%) | yes | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |
| H21 mr L1 +hold16 | no | no | no (5%) | yes | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |
| H21 mr L2 hold96 | no | no | no (24%) | yes | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |
| H21 mr L3 +trend1d | no | no | no (33%) | yes | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |
| H21 mr L4 +confidence | no | no | no (24%) | yes | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |
| H21 mr L5 +costgate | no | no | no (19%) | yes | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |
| H21 mr L6 +session | no | no | no (10%) | yes | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |
| H21 mr L7 +cooldown | no | no | no (10%) | no | no | fold_share, high_turnover, not_significant, eth_fails | 1.000 | 0.00 |

### Per fold, 0.10% (BTCUSDT): net return (Sharpe)

| # | Test window | H20 | H22 | H23 | Buy-and-hold | Momentum | H20 / H22 / H23 variant chosen on the train window |
|---|---|---|---|---|---|---|---|
| 0 | 2020-10-01 .. 2021-01-01 | -1% (0.07) | +145% (6.18) | +308% (6.23) | +157% (6.07) | +168% (6.32) | mr e=2 trend=4h gate=2.5 session=all hold=96 cool=0 / short=0 size=R3 entry=E0 / core 1x, signal=mom1d band=[0, 1.5] hold=16 |
| 1 | 2021-01-01 .. 2021-04-01 | +39% (2.20) | +29% (2.13) | +53% (2.11) | +72% (2.49) | +35% (1.63) | ema e=0 trend=1d gate=0 session=active hold=96 cool=0 / short=0 size=R1 entry=E2 / core 1x, signal=mom1d band=[0, 1] hold=16 |
| 2 | 2021-04-01 .. 2021-07-01 | -27% (-1.27) | -22% (-3.31) | -43% (-2.81) | -44% (-1.68) | -21% (-0.36) | ema e=0 trend=1d gate=0 session=active hold=96 cool=0 / short=0 size=R1 entry=E2 / core 1x, signal=mom1d band=[0.5, 1.5] hold=16 |
| 3 | 2021-07-01 .. 2021-10-01 | -30% (-2.60) | +12% (1.18) | +20% (1.71) | +22% (1.54) | +14% (1.09) | mom e=0 trend=none gate=2.5 session=all hold=96 cool=0 / short=0 size=R0 entry=E1 / core 1x, signal=mom1d band=[0, 1] hold=16 |
| 4 | 2021-10-01 .. 2022-01-01 | -22% (-2.03) | +5% (0.63) | +5% (0.63) | +0% (0.35) | +2% (0.43) | mom e=0 trend=none gate=2.5 session=all hold=96 cool=0 / short=0 size=R1 entry=E0 / core 1x, signal=mom1d band=[0, 1] hold=16 |
| 5 | 2022-01-01 .. 2022-04-01 | -0% (0.25) | -16% (-1.57) | -16% (-1.57) | -3% (0.16) | -32% (-2.03) | mom e=0 trend=none gate=2.5 session=all hold=96 cool=0 / short=0 size=R0 entry=E0 / core 1x, signal=mom1d band=[0, 1] hold=16 |
| 6 | 2022-04-01 .. 2022-07-01 | +6% (1.04) | -16% (-3.16) | -44% (-4.53) | -57% (-4.00) | +41% (2.18) | mr e=2 trend=1d gate=2.5 session=active hold=16 cool=96 / short=0 size=R1 entry=E0 / core 1x, signal=mom1d band=[0.5, 1.5] hold=16 |
| 7 | 2022-07-01 .. 2022-10-01 | +3% (0.81) | +2% (0.42) | +2% (0.38) | -4% (0.07) | +2% (0.46) | mr e=2.5 trend=both gate=2.5 session=all hold=1 cool=96 / short=1 size=R1 entry=E0 / core 1x, signal=mom1d band=[0, 1] hold=16 |
| 8 | 2022-10-01 .. 2023-01-01 | -1% (-0.27) | -30% (-3.38) | -29% (-3.11) | -15% (-1.16) | -28% (-2.45) | mr e=2.5 trend=both gate=2.5 session=all hold=1 cool=96 / short=1 size=R1 entry=E0 / core 1x, signal=mom1d band=[0, 1.5] hold=16 |
| 9 | 2023-01-01 .. 2023-04-01 | +10% (2.13) | +34% (3.10) | +114% (4.83) | +69% (4.31) | +52% (3.52) | mr e=2.5 trend=both gate=2.5 session=all hold=96 cool=0 / short=1 size=R1 entry=E0 / core 1x, signal=trend4h band=[0, 1.5] hold=96 |
| 10 | 2023-04-01 .. 2023-07-01 | +8% (2.47) | -4% (-0.14) | -17% (-1.36) | +5% (0.72) | -4% (-0.14) | mr e=2.5 trend=1d gate=2.5 session=all hold=96 cool=0 / short=1 size=R0 entry=E0 / core 1x, signal=trend4h band=[0, 1.5] hold=96 |
| 11 | 2023-07-01 .. 2023-10-01 | -7% (-3.67) | -3% (-0.69) | -19% (-4.45) | -13% (-1.24) | +10% (1.15) | ema e=1 trend=both gate=0 session=all hold=1 cool=0 / short=0 size=R0 entry=E2 / core 1x, signal=trend4h band=[0, 1] hold=96 |
| 12 | 2023-10-01 .. 2024-01-01 | +1% (0.32) | +31% (2.84) | +84% (3.96) | +52% (3.97) | +52% (3.95) | mr e=2.5 trend=4h gate=2.5 session=all hold=96 cool=0 / short=0 size=R3 entry=E0 / core 1x, signal=mom1d band=[0.5, 1.5] hold=16 |
| 13 | 2024-01-01 .. 2024-04-01 | +20% (1.86) | +27% (2.05) | +41% (2.10) | +59% (3.52) | +2% (0.40) | ema e=0 trend=none gate=1.5 session=active hold=96 cool=96 / short=0 size=R0 entry=E0 / core 1x, signal=mom1d band=[0, 1.5] hold=16 |
| 14 | 2024-04-01 .. 2024-07-01 | -4% (-0.76) | -4% (-0.69) | -11% (-0.73) | -14% (-1.01) | +3% (0.51) | mr e=2.5 trend=none gate=2.5 session=all hold=16 cool=0 / short=0 size=R1 entry=E0 / core 1x, signal=mom1d band=[0.5, 1.5] hold=16 |
| 15 | 2024-07-01 .. 2024-10-01 | -9% (-1.42) | -14% (-2.47) | -29% (-3.44) | -0% (0.27) | -51% (-4.94) | mr e=2.5 trend=both gate=0 session=all hold=96 cool=0 / short=0 size=R1 entry=E1 / core 1x, signal=mom1d band=[0, 1] hold=16 |
| 16 | 2024-10-01 .. 2025-01-01 | -6% (-0.56) | +27% (2.77) | +50% (2.88) | +43% (3.06) | +40% (2.89) | mr e=2 trend=4h gate=1.5 session=all hold=96 cool=0 / short=0 size=R1 entry=E1 / core 1x, signal=trend4h band=[0.5, 1.5] hold=16 |
| 17 | 2025-01-01 .. 2025-04-01 | -27% (-3.27) | -10% (-2.13) | -30% (-2.31) | -13% (-0.74) | -23% (-1.63) | mom e=1 trend=4h gate=1.5 session=all hold=96 cool=0 / short=0 size=R1 entry=E1 / core 1x, signal=trend4h band=[0.5, 1.5] hold=16 |
| 18 | 2025-04-01 .. 2025-07-01 | +5% (1.45) | +18% (2.43) | +13% (1.28) | +29% (2.64) | -1% (0.09) | mr e=2 trend=none gate=2.5 session=active hold=96 cool=0 / short=0 size=R1 entry=E2 / core 1x, signal=trend4h band=[0.5, 1.5] hold=96 |
| 19 | 2025-07-01 .. 2025-10-01 | +0% (0.00) | +4% (0.75) | -2% (-0.06) | +5% (0.74) | +3% (0.48) | mr e=2.5 trend=none gate=2.5 session=all hold=96 cool=0 / short=0 size=R1 entry=E2 / core 1x, signal=trend4h band=[0.5, 1.5] hold=96 |
| 20 | 2025-10-01 .. 2025-11-11 | +4% (1.81) | -4% (-1.18) | -7% (-1.26) | -7% (-1.31) | -0% (0.18) | mr e=2.5 trend=none gate=2.5 session=all hold=96 cool=0 / short=0 size=R1 entry=E2 / core 1x, signal=mom1d band=[0.5, 1.5] hold=16 |

### Trade count vs net return (BTCUSDT)

**Out of sample, the fixed ladder (H21; nothing fitted), 0.10% a side:**

| Base | Level | Trades/yr | CAGR | Net return | Sharpe | Gross Sharpe | Max DD | Cost drag/yr | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|
| mom | L0 base | 4503 | -100.0% | -100% | -18.77 | -0.28 | 100% | 1195.0% | none (loses at 0 fee) |
| mom | L1 +hold16 | 1673 | -99.5% | -100% | -7.92 | -0.89 | 100% | 445.8% | none (loses at 0 fee) |
| mom | L2 hold96 | 345 | -59.7% | -99% | -1.14 | 0.34 | 99% | 92.3% | none (loses at 0 fee) |
| mom | L3 +trend1d | 347 | -16.7% | -61% | -0.18 | 0.96 | 81% | 51.0% | 0.049% |
| mom | L4 +confidence | 300 | -21.6% | -71% | -0.35 | 0.66 | 81% | 43.5% | 0.020% |
| mom | L5 +costgate | 250 | -26.2% | -79% | -0.51 | 0.38 | 87% | 37.5% | none (loses at 0 fee) |
| mom | L6 +session | 212 | -16.8% | -61% | -0.27 | 0.55 | 81% | 32.1% | 0.014% |
| mom | L7 +cooldown | 212 | -19.3% | -67% | -0.35 | 0.46 | 84% | 31.7% | none (loses at 0 fee) |
| ema | L0 base | 703 | -85.8% | -100% | -2.79 | 0.20 | 100% | 187.8% | none (loses at 0 fee) |
| ema | L1 +hold16 | 624 | -86.7% | -100% | -2.90 | -0.23 | 100% | 167.3% | none (loses at 0 fee) |
| ema | L2 hold96 | 291 | -72.9% | -100% | -1.77 | -0.52 | 100% | 78.8% | none (loses at 0 fee) |
| ema | L3 +trend1d | 294 | -28.6% | -82% | -0.50 | 0.47 | 92% | 44.5% | none (loses at 0 fee) |
| ema | L4 +confidence | 74 | +5.1% | +29% | 0.32 | 0.73 | 53% | 11.3% | 0.166% |
| ema | L5 +costgate | 70 | +3.7% | +20% | 0.27 | 0.67 | 52% | 10.8% | 0.151% |
| ema | L6 +session | 63 | -1.8% | -9% | 0.06 | 0.44 | 53% | 9.8% | 0.071% |
| ema | L7 +cooldown | 63 | -1.8% | -9% | 0.06 | 0.44 | 53% | 9.8% | 0.071% |
| mr | L0 base | 1328 | -86.4% | -100% | -3.62 | -0.18 | 100% | 176.8% | none (loses at 0 fee) |
| mr | L1 +hold16 | 1153 | -82.5% | -100% | -3.21 | -0.06 | 100% | 158.4% | none (loses at 0 fee) |
| mr | L2 hold96 | 340 | -46.4% | -96% | -1.02 | 0.07 | 96% | 53.4% | none (loses at 0 fee) |
| mr | L3 +trend1d | 283 | -28.6% | -82% | -0.64 | 0.39 | 92% | 41.1% | none (loses at 0 fee) |
| mr | L4 +confidence | 252 | -21.3% | -71% | -0.45 | 0.52 | 82% | 36.4% | 0.006% |
| mr | L5 +costgate | 203 | -21.7% | -71% | -0.49 | 0.34 | 83% | 30.3% | none (loses at 0 fee) |
| mr | L6 +session | 181 | -21.8% | -72% | -0.54 | 0.25 | 82% | 27.1% | none (loses at 0 fee) |
| mr | L7 +cooldown | 181 | -24.0% | -75% | -0.62 | 0.16 | 83% | 26.9% | none (loses at 0 fee) |

**Training data only (exploration, not evidence): H20's 864 variants, mean over the folds' train windows, 0.10% a side:**

| Trades/yr | Variants | Median Sharpe | Best Sharpe | Median CAGR | Share with CAGR > 0 |
|---|---|---|---|---|---|
| 30-100 | 184 | -0.06 | 0.67 | +0.5% | 53% |
| 100-300 | 345 | -0.68 | 0.49 | -19.9% | 15% |
| 300-1000 | 298 | -2.08 | -0.11 | -48.6% | 0% |
| 1000- | 37 | -5.61 | -2.82 | -88.7% | 0% |

## ETHUSDT: development out of sample 2020-10-01 to 2025-11-11

### Annual return (CAGR) against the target, 0.10%% a side

| Strategy | CAGR | vs 25% target | vs buy-and-hold (+36.2%) | vs momentum (+39.5%) | 10% milestone | Max DD (B&H 82%) | Positive folds | Development pass |
|---|---|---|---|---|---|---|---|---|
| H20 Family 1 | -11.8% | -36.8% | -48.0% | -51.3% | no | 82% | 38% | no |
| H22 Family 2 | +35.8% | +10.8% | -0.4% | -3.6% | CAGR only | 68% | 52% | no |
| H23 Family 3 | +41.6% | +16.6% | +5.4% | +2.2% | CAGR only | 85% | 52% | no |
| H21 mom L0 base | -100.0% | -125.0% | -136.2% | -139.5% | no | 100% | 0% | no |
| H21 mom L1 +hold16 | -99.5% | -124.5% | -135.6% | -138.9% | no | 100% | 0% | no |
| H21 mom L2 hold96 | -62.0% | -87.0% | -98.2% | -101.4% | no | 100% | 19% | no |
| H21 mom L3 +trend1d | -14.9% | -39.9% | -51.1% | -54.4% | no | 91% | 43% | no |
| H21 mom L4 +confidence | -28.6% | -53.6% | -64.8% | -68.0% | no | 92% | 29% | no |
| H21 mom L5 +costgate | -23.2% | -48.2% | -59.4% | -62.7% | no | 89% | 33% | no |
| H21 mom L6 +session | -22.9% | -47.9% | -59.1% | -62.4% | no | 84% | 43% | no |
| H21 mom L7 +cooldown | -21.2% | -46.2% | -57.3% | -60.6% | no | 83% | 43% | no |
| H21 ema L0 base | -81.2% | -106.2% | -117.4% | -120.7% | no | 100% | 0% | no |
| H21 ema L1 +hold16 | -81.7% | -106.7% | -117.9% | -121.2% | no | 100% | 0% | no |
| H21 ema L2 hold96 | -59.5% | -84.5% | -95.6% | -98.9% | no | 100% | 29% | no |
| H21 ema L3 +trend1d | -11.4% | -36.4% | -47.5% | -50.8% | no | 89% | 43% | no |
| H21 ema L4 +confidence | +20.2% | -4.8% | -16.0% | -19.3% | CAGR only | 46% | 62% | no |
| H21 ema L5 +costgate | +19.4% | -5.6% | -16.8% | -20.0% | CAGR only | 46% | 67% | no |
| H21 ema L6 +session | +7.6% | -17.4% | -28.6% | -31.9% | no | 52% | 71% | no |
| H21 ema L7 +cooldown | +7.6% | -17.4% | -28.6% | -31.9% | no | 52% | 71% | no |
| H21 mr L0 base | -91.1% | -116.1% | -127.2% | -130.5% | no | 100% | 0% | no |
| H21 mr L1 +hold16 | -85.1% | -110.1% | -121.3% | -124.6% | no | 100% | 0% | no |
| H21 mr L2 hold96 | -58.1% | -83.1% | -94.3% | -97.6% | no | 100% | 29% | no |
| H21 mr L3 +trend1d | -18.8% | -43.8% | -55.0% | -58.3% | no | 92% | 38% | no |
| H21 mr L4 +confidence | -13.1% | -38.1% | -49.3% | -52.6% | no | 89% | 43% | no |
| H21 mr L5 +costgate | -18.9% | -43.9% | -55.1% | -58.4% | no | 91% | 38% | no |
| H21 mr L6 +session | -8.9% | -33.9% | -45.1% | -48.3% | no | 86% | 38% | no |
| H21 mr L7 +cooldown | -11.3% | -36.3% | -47.5% | -50.8% | no | 87% | 38% | no |
| Buy-and-hold | +36.2% | +11.2% | 0 | -3.3% | | 82% | | |
| Momentum (daily, 30-day) | +39.5% | +14.5% | +3.3% | 0 | | 80% | | |

### Headline table, 0.10% a side

| Strategy | CAGR | Net return | Sharpe | Gross Sharpe | Sortino | Max DD | Calmar | Trades/yr | Avg hold (h) | Cost drag/yr | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **H20 Family 1: filter stack on 15m bases (walk-forward selected)** | -11.8% | -47% | -0.01 | 0.64 | -0.01 | 82% | -0.14 | 186 | 25 | 31.7% | 0.033% |
| **H22 Family 2: meta-labeling on daily momentum (walk-forward selected)** | +35.8% | +378% | 0.88 | 1.19 | 1.24 | 68% | 0.53 | 63 | 240 | 14.9% | 0.708% |
| **H23 Family 3: core-satellite overlay (walk-forward selected)** | +41.6% | +492% | 0.84 | 1.13 | 1.18 | 85% | 0.49 | 57 | 478 | 26.8% | 0.637% |
| Buy-and-hold | +36.2% | +385% | 0.79 | 0.96 | 1.11 | 82% | 0.44 | 0 | whole span | 14.0% | > 4% |
| Momentum (daily, 30-day, long/short) | +39.5% | +448% | 0.82 | 1.03 | 1.15 | 80% | 0.49 | 27 | 327 | 17.4% | 0.720% |
| Random agent, daily (Phase 1), mean of 10 | -48.8% | -95% | -0.74 | -0.04 | -1.05 | 98% | -0.50 | 243 | 36 | 45.6% | - |
| Random, matched to H20 (mean of 10) | -31.1% | -69% | -0.29 | | | 92% | | (same) | | | |
| Random, matched to H22 (mean of 10) | -23.1% | -62% | -0.30 | | | 86% | | (same) | | | |
| Random, matched to H23 (mean of 10) | +12.6% | +124% | 0.53 | | | 85% | | (same) | | | |

### Headline table, 0.05% a side

| Strategy | CAGR | Net return | Sharpe | Gross Sharpe | Sortino | Max DD | Calmar | Trades/yr | Avg hold (h) | Cost drag/yr | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **H20 Family 1: filter stack on 15m bases (walk-forward selected)** | -3.1% | -15% | 0.18 | 0.64 | 0.26 | 77% | -0.04 | 186 | 25 | 22.3% | - |
| **H22 Family 2: meta-labeling on daily momentum (walk-forward selected)** | +39.3% | +444% | 0.93 | 1.19 | 1.31 | 65% | 0.60 | 63 | 240 | 12.4% | - |
| **H23 Family 3: core-satellite overlay (walk-forward selected)** | +46.3% | +599% | 0.87 | 1.13 | 1.23 | 83% | 0.56 | 57 | 478 | 23.6% | - |
| Buy-and-hold | +36.2% | +385% | 0.79 | 0.96 | 1.11 | 82% | 0.44 | 0 | whole span | 14.0% | - |
| Momentum (daily, 30-day, long/short) | +43.2% | +528% | 0.85 | 1.03 | 1.20 | 79% | 0.55 | 27 | 327 | 14.7% | - |

### Graded strategies: registered criteria and flags (ETHUSDT)

| Strategy | T: <=100 trades/yr | beats B&H Sharpe+Calmar | Sharpe > B&H in >= half folds | > matched random | Thesis pass | Flags fired | Boot p (Sharpe - B&H) | DSR prob |
|---|---|---|---|---|---|---|---|---|
| H20 Family 1 | no | no | no (33%) | yes | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |
| H22 Family 2 | yes | yes | no (43%) | yes | no | fold_share, not_significant | 0.301 | 0.11 |
| H23 Family 3 | yes | yes | no (43%) | yes | no | fold_share, not_significant | 0.485 | 0.09 |
| H21 mom L0 base | no | no | no (0%) | no | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |
| H21 mom L1 +hold16 | no | no | no (5%) | no | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |
| H21 mom L2 hold96 | no | no | no (19%) | yes | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |
| H21 mom L3 +trend1d | no | no | no (33%) | yes | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |
| H21 mom L4 +confidence | no | no | no (33%) | yes | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |
| H21 mom L5 +costgate | no | no | no (24%) | yes | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |
| H21 mom L6 +session | no | no | no (29%) | yes | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |
| H21 mom L7 +cooldown | no | no | no (29%) | yes | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |
| H21 ema L0 base | no | no | no (14%) | yes | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |
| H21 ema L1 +hold16 | no | no | no (10%) | yes | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |
| H21 ema L2 hold96 | no | no | no (24%) | yes | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |
| H21 ema L3 +trend1d | no | no | no (29%) | yes | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |
| H21 ema L4 +confidence | yes | no | no (38%) | yes | no | fold_share, fee_only_at_0.05, not_significant | 0.355 | 0.05 |
| H21 ema L5 +costgate | yes | no | no (38%) | yes | no | fold_share, fee_only_at_0.05, not_significant | 0.363 | 0.05 |
| H21 ema L6 +session | yes | no | no (38%) | yes | no | fold_share, not_significant, btc_fails | 1.000 | 0.01 |
| H21 ema L7 +cooldown | yes | no | no (38%) | yes | no | fold_share, not_significant, btc_fails | 1.000 | 0.01 |
| H21 mr L0 base | no | no | no (5%) | yes | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |
| H21 mr L1 +hold16 | no | no | no (0%) | yes | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |
| H21 mr L2 hold96 | no | no | no (33%) | no | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |
| H21 mr L3 +trend1d | no | no | no (29%) | yes | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |
| H21 mr L4 +confidence | no | no | no (38%) | yes | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |
| H21 mr L5 +costgate | no | no | no (33%) | yes | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |
| H21 mr L6 +session | no | no | no (29%) | yes | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |
| H21 mr L7 +cooldown | no | no | no (29%) | yes | no | fold_share, high_turnover, not_significant, btc_fails | 1.000 | 0.00 |

### Per fold, 0.10% (ETHUSDT): net return (Sharpe)

| # | Test window | H20 | H22 | H23 | Buy-and-hold | Momentum | H20 / H22 / H23 variant chosen on the train window |
|---|---|---|---|---|---|---|---|
| 0 | 2020-10-01 .. 2021-01-01 | -16% (-1.23) | +68% (4.04) | +110% (3.19) | +90% (3.66) | +51% (2.49) | mr e=2 trend=4h gate=0 session=all hold=96 cool=96 / short=0 size=R1 entry=E0 / core 1x, signal=mom1d band=[0, 1.5] hold=16 |
| 1 | 2021-01-01 .. 2021-04-01 | +42% (2.02) | +62% (3.15) | +157% (2.91) | +111% (2.89) | +105% (2.82) | mom e=0 trend=1d gate=1.5 session=active hold=96 cool=96 / short=0 size=R1 entry=E1 / core 1x, signal=mom1d band=[0, 1.5] hold=16 |
| 2 | 2021-04-01 .. 2021-07-01 | -10% (0.05) | +20% (1.44) | -1% (0.92) | +9% (0.99) | -14% (0.34) | ema e=0 trend=1d gate=2.5 session=all hold=96 cool=96 / short=0 size=R1 entry=E2 / core 1x, signal=mom1d band=[0.5, 1.5] hold=16 |
| 3 | 2021-07-01 .. 2021-10-01 | -7% (-0.16) | +34% (2.32) | +54% (2.13) | +27% (1.52) | +45% (2.11) | ema e=0 trend=1d gate=0 session=active hold=96 cool=96 / short=0 size=R1 entry=E2 / core 1x, signal=mom1d band=[0.5, 1.5] hold=16 |
| 4 | 2021-10-01 .. 2022-01-01 | +13% (1.22) | -1% (0.23) | +10% (0.86) | +17% (1.21) | -15% (-0.45) | mr e=2 trend=1d gate=1.5 session=active hold=96 cool=0 / short=0.5 size=R1 entry=E2 / core 1x, signal=mom1d band=[0.5, 1.5] hold=16 |
| 5 | 2022-01-01 .. 2022-04-01 | -27% (-2.37) | +9% (0.98) | -4% (0.18) | -12% (-0.21) | +7% (0.75) | mr e=2.5 trend=4h gate=0 session=all hold=96 cool=0 / short=0.5 size=R1 entry=E2 / core 1x, signal=mom1d band=[0.5, 1.5] hold=16 |
| 6 | 2022-04-01 .. 2022-07-01 | +8% (0.79) | +22% (2.12) | -47% (-3.78) | -67% (-4.00) | +98% (3.24) | ema e=0 trend=1d gate=2.5 session=active hold=96 cool=0 / short=0.5 size=R1 entry=E2 / core 1x, signal=mom1d band=[0.5, 1.5] hold=16 |
| 7 | 2022-07-01 .. 2022-10-01 | -42% (-3.19) | -14% (-0.76) | +9% (0.89) | +25% (1.44) | -14% (-0.19) | mom e=1 trend=1d gate=2.5 session=all hold=96 cool=96 / short=1 size=R1 entry=E2 / core 1x, signal=mom1d band=[0, 1] hold=16 |
| 8 | 2022-10-01 .. 2023-01-01 | -28% (-3.20) | -39% (-2.59) | -40% (-2.45) | -10% (-0.31) | -45% (-3.22) | mr e=2 trend=1d gate=2.5 session=active hold=96 cool=0 / short=1 size=R0 entry=E2 / core 1x, signal=mom1d band=[0, 1.5] hold=16 |
| 9 | 2023-01-01 .. 2023-04-01 | -12% (-2.30) | -6% (-0.26) | +34% (1.92) | +49% (3.15) | +1% (0.35) | mr e=2.5 trend=4h gate=2.5 session=active hold=96 cool=96 / short=0.5 size=R3 entry=E2 / core 1x, signal=mom1d band=[0, 1.5] hold=16 |
| 10 | 2023-04-01 .. 2023-07-01 | -3% (-0.92) | -17% (-2.46) | -14% (-1.12) | +5% (0.64) | -19% (-1.73) | mr e=2 trend=4h gate=2.5 session=active hold=96 cool=96 / short=0 size=R3 entry=E2 / core 1x, signal=trend4h band=[0, 1.5] hold=96 |
| 11 | 2023-07-01 .. 2023-10-01 | +3% (0.61) | -6% (-1.55) | -20% (-2.66) | -15% (-1.50) | -2% (-0.05) | mom e=1 trend=none gate=1.5 session=active hold=96 cool=96 / short=0 size=R0 entry=E2 / core 1x, signal=trend4h band=[0.5, 1.5] hold=96 |
| 12 | 2023-10-01 .. 2024-01-01 | -1% (-0.14) | +31% (3.64) | +29% (1.91) | +32% (2.54) | +21% (1.81) | mr e=2 trend=none gate=2.5 session=active hold=16 cool=96 / short=0 size=R1 entry=E2 / core 1x, signal=trend4h band=[0.5, 1.5] hold=96 |
| 13 | 2024-01-01 .. 2024-04-01 | +20% (1.83) | +6% (0.87) | +34% (1.79) | +51% (2.95) | -17% (-0.84) | mom e=1 trend=none gate=1.5 session=active hold=96 cool=96 / short=0 size=R1 entry=E2 / core 1x, signal=mom1d band=[0.5, 1.5] hold=16 |
| 14 | 2024-04-01 .. 2024-07-01 | +28% (2.60) | +5% (0.86) | -5% (-0.03) | -8% (-0.26) | +7% (0.74) | mom e=1 trend=none gate=1.5 session=active hold=96 cool=96 / short=0 size=R1 entry=E2 / core 1x, signal=trend4h band=[0.5, 1.5] hold=96 |
| 15 | 2024-07-01 .. 2024-10-01 | -8% (-1.23) | -9% (-3.11) | -19% (-1.19) | -25% (-1.39) | -6% (-0.03) | mr e=2.5 trend=4h gate=2.5 session=active hold=96 cool=0 / short=0 size=R1 entry=E1 / core 1x, signal=trend4h band=[0.5, 1.5] hold=96 |
| 16 | 2024-10-01 .. 2025-01-01 | -0% (0.08) | -9% (-0.92) | +20% (1.72) | +24% (1.63) | -27% (-1.62) | ema e=1 trend=1d gate=0 session=all hold=96 cool=0 / short=0 size=R1 entry=E1 / core 1x, signal=trend4h band=[0, 1] hold=96 |
| 17 | 2025-01-01 .. 2025-04-01 | +24% (2.74) | -3% (-3.06) | -43% (-5.74) | -46% (-2.67) | +49% (2.39) | mr e=2.5 trend=both gate=2.5 session=active hold=96 cool=0 / short=0 size=R3 entry=E0 / core 1x, signal=trend4h band=[0, 1] hold=96 |
| 18 | 2025-04-01 .. 2025-07-01 | -6% (-0.69) | +32% (1.88) | +39% (2.98) | +35% (2.00) | +33% (1.92) | mr e=2.5 trend=both gate=2.5 session=active hold=96 cool=0 / short=1 size=R0 entry=E2 / core 1x, signal=mom1d band=[0, 1] hold=16 |
| 19 | 2025-07-01 .. 2025-10-01 | -8% (-1.07) | +61% (3.58) | +107% (3.82) | +64% (3.56) | +65% (3.60) | mr e=2.5 trend=both gate=0 session=all hold=96 cool=0 / short=0.5 size=R0 entry=E2 / core 1x, signal=mom1d band=[0, 1.5] hold=16 |
| 20 | 2025-10-01 .. 2025-11-11 | +7% (1.84) | -12% (-2.62) | -18% (-2.55) | -14% (-1.49) | -13% (-1.37) | mr e=2.5 trend=both gate=0 session=all hold=96 cool=0 / short=0 size=R1 entry=E2 / core 1x, signal=mom1d band=[0, 1.5] hold=16 |

### Trade count vs net return (ETHUSDT)

**Out of sample, the fixed ladder (H21; nothing fitted), 0.10% a side:**

| Base | Level | Trades/yr | CAGR | Net return | Sharpe | Gross Sharpe | Max DD | Cost drag/yr | Break-even fee |
|---|---|---|---|---|---|---|---|---|---|
| mom | L0 base | 4388 | -100.0% | -100% | -14.59 | 0.42 | 100% | 1237.1% | none (loses at 0 fee) |
| mom | L1 +hold16 | 1650 | -99.5% | -100% | -6.00 | -0.25 | 100% | 467.6% | none (loses at 0 fee) |
| mom | L2 hold96 | 346 | -62.0% | -99% | -0.79 | 0.42 | 100% | 98.2% | none (loses at 0 fee) |
| mom | L3 +trend1d | 346 | -14.9% | -56% | -0.00 | 0.97 | 91% | 54.8% | 0.054% |
| mom | L4 +confidence | 308 | -28.6% | -82% | -0.36 | 0.55 | 92% | 48.8% | none (loses at 0 fee) |
| mom | L5 +costgate | 285 | -23.2% | -74% | -0.23 | 0.63 | 89% | 46.0% | 0.008% |
| mom | L6 +session | 243 | -22.9% | -74% | -0.26 | 0.52 | 84% | 39.6% | none (loses at 0 fee) |
| mom | L7 +cooldown | 243 | -21.2% | -70% | -0.22 | 0.56 | 83% | 39.5% | 0.002% |
| ema | L0 base | 696 | -81.2% | -100% | -1.66 | 0.81 | 100% | 199.7% | none (loses at 0 fee) |
| ema | L1 +hold16 | 614 | -81.7% | -100% | -1.70 | 0.50 | 100% | 177.1% | none (loses at 0 fee) |
| ema | L2 hold96 | 284 | -59.5% | -99% | -0.71 | 0.31 | 100% | 82.7% | none (loses at 0 fee) |
| ema | L3 +trend1d | 290 | -11.4% | -46% | 0.09 | 0.91 | 89% | 48.1% | 0.059% |
| ema | L4 +confidence | 69 | +20.2% | +156% | 0.71 | 1.06 | 46% | 11.7% | 0.366% |
| ema | L5 +costgate | 69 | +19.4% | +148% | 0.69 | 1.04 | 46% | 11.7% | 0.357% |
| ema | L6 +session | 65 | +7.6% | +45% | 0.39 | 0.72 | 52% | 10.9% | 0.213% |
| ema | L7 +cooldown | 65 | +7.6% | +45% | 0.39 | 0.72 | 52% | 10.9% | 0.213% |
| mr | L0 base | 1313 | -91.1% | -100% | -3.31 | -0.55 | 100% | 183.1% | none (loses at 0 fee) |
| mr | L1 +hold16 | 1144 | -85.1% | -100% | -2.61 | -0.07 | 100% | 165.0% | none (loses at 0 fee) |
| mr | L2 hold96 | 340 | -58.1% | -99% | -1.07 | -0.19 | 100% | 55.2% | none (loses at 0 fee) |
| mr | L3 +trend1d | 280 | -18.8% | -66% | -0.16 | 0.70 | 92% | 43.1% | 0.026% |
| mr | L4 +confidence | 253 | -13.1% | -51% | -0.06 | 0.76 | 89% | 38.8% | 0.045% |
| mr | L5 +costgate | 231 | -18.9% | -66% | -0.21 | 0.56 | 91% | 36.1% | 0.010% |
| mr | L6 +session | 205 | -8.9% | -38% | 0.02 | 0.73 | 86% | 32.1% | 0.055% |
| mr | L7 +cooldown | 204 | -11.3% | -46% | -0.05 | 0.67 | 87% | 31.8% | 0.042% |

**Training data only (exploration, not evidence): H20's 864 variants, mean over the folds' train windows, 0.10% a side:**

| Trades/yr | Variants | Median Sharpe | Best Sharpe | Median CAGR | Share with CAGR > 0 |
|---|---|---|---|---|---|
| 30-100 | 141 | 0.19 | 0.50 | +0.6% | 55% |
| 100-300 | 307 | -0.38 | 0.66 | -15.0% | 18% |
| 300-1000 | 372 | -1.65 | -0.04 | -51.1% | 0% |
| 1000- | 44 | -4.87 | -2.61 | -90.9% | 0% |

## Family 4: Mind 15's own replay trades (H24; in-sample, descriptive)

The 10 Nov 2026 replay (`out/replay/trades_*.csv`, 0.10% fees, trades entered before the seal) already trades about 35-40 times a year. H24 keeps a trade only when its side agrees with the frozen daily momentum at entry. The replay is warm-up material for an engine designed on this history, so H24 can neither pass nor go to the holdout. Forward data (`out/live/`, since 10-11 Nov 2026) holds no closed BTC/ETH main-book trades yet: too short to say anything.

| Coin | Half | Trades | Mean net/trade, all | Compounded, all | Kept | Mean net/trade, kept | Compounded, kept | Win rate all / kept |
|---|---|---|---|---|---|---|---|---|
| BTCUSDT | first | 186 | +0.02% | -53% | 96 | +0.84% | +32% | 17% / 20% |
| BTCUSDT | second | 89 | +0.89% | +53% | 46 | +0.79% | +23% | 21% / 26% |
| BTCUSDT | all | 275 | +0.30% | -29% | 142 | +0.82% | +62% | 18% / 22% |
| ETHUSDT | first | 164 | +1.35% | +141% | 74 | +2.38% | +185% | 23% / 28% |
| ETHUSDT | second | 65 | +3.45% | +453% | 29 | +4.17% | +151% | 29% / 24% |
| ETHUSDT | all | 229 | +1.95% | +1230% | 103 | +2.88% | +613% | 24% / 27% |

H24 registered test (kept mean above all-trades mean and kept compounded result positive, both halves, both coins): **not met** (in-sample; no pass can come of it).

## Verdict per family (BTCUSDT headline, 0.10% a side, development out of sample)

- **Filters on frequent 15m bases (H20): NO. 141 trades/yr; CAGR -12.4% (buy-and-hold +38.1%); Sharpe -0.18 vs 0.83; Calmar -0.18 vs 0.48; max DD 70% vs 79%; break-even fee 0.015%; flags: fold_share, high_turnover, not_significant, eth_fails. Development pass (25% target): no.**

- **The fixed filter ladder (H21): NO. Best ladder level by Sharpe: ema L4 +confidence (74 trades/yr, CAGR +5.1%, Sharpe 0.32 vs buy-and-hold 0.83, break-even fee 0.166%). No level cuts trades AND beats buy-and-hold risk-adjusted.**

- **Meta-labeling on daily momentum (H22): NO. 46 trades/yr; CAGR +26.8% (buy-and-hold +38.1%); Sharpe 0.81 vs 0.83; Calmar 0.46 vs 0.48; max DD 58% vs 79%; break-even fee 0.627%; flags: fold_share, fee_only_at_0.05, not_significant. Development pass (25% target): no.**

- **Core-satellite overlay (H23): NO. 66 trades/yr; CAGR +29.9% (buy-and-hold +38.1%); Sharpe 0.74 vs 0.83; Calmar 0.39 vs 0.48; max DD 77% vs 79%; break-even fee 0.455%; flags: fold_share, not_significant, eth_fails. Development pass (25% target): no.**

## Loop status after round 1

- Development passes (CAGR >= 25%, max DD <= buy-and-hold, > half the folds positive, flags clear): **none**.
- Holdout looks used: 0 (ledger in `research/out/harness/loop_state.json` and `research/harness/LOOP.md`).
- Best so far by development CAGR (BTC, 0.10%): Family 3: core-satellite overlay (walk-forward selected), CAGR +29.9%, Sharpe 0.74, max DD 77%, 66 trades/yr; flags: fold_share, not_significant, eth_fails.
- Closest to a development pass: R1-BTCUSDT-H22 (meets 6 of 6 loop-target criteria over BTC and ETH; flags BTC: fold_share, fee_only_at_0.05, not_significant; ETH: fold_share, not_significant).

Machine-readable: `harness_summary.json`; loop state: `loop_state.json`; per-asset caches `cache_<asset>.json`.
