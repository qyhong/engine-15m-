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
