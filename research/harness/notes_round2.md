## Summary (round 2)

**No development pass.** None of the 31 rules per coin (or the 2 two-coin books) meets all of the owner's strict rules
on both BTC and ETH, so no holdout look was taken (0 used, ledger empty).

**What did work, on development data:** the daily momentum direction combined with a buy-and-hold-style core,
leverage in uptrends and spot for the long legs beats spot buy-and-hold on CAGR, Sharpe and drawdown on both coins.
- **H29 H30 1.5x/0x spot longs** ("1.5x in uptrends, flat in downtrends"; ~30 trades a year): BTC +78% a year,
  Sharpe 1.19, max DD 65% (spot buy-and-hold +56%, 1.03, 77%). ETH +106%, Sharpe 1.25, max DD 67% (spot buy-and-hold
  +57%, 0.96, 81%).
- **H29 H31 trail 4 ATR spot longs** (vol-targeted to 60% a year, up to 2x, trailing exit on the 15m clock; ~50 trades
  a year): BTC +68%, Sharpe 1.32, DD 53%; ETH +72%, Sharpe 1.38, DD 43%. These are the best Sharpe ratios of the round.
- **H29 H28 spot longs** (the most-chosen round-1 variant, fixed): ETH meets 7 of 8 rules (p = 0.044, needed 2.6e-5);
  BTC +41%, below spot buy-and-hold's +56%.
- Spot execution for the long legs (H29) improved every rule it was applied to, by about 12-25 points of CAGR a year:
  funding on a perp long cost roughly 12% a year over the development span.

**Why nothing passes. Two rules bind every candidate:**
1. **Fold share (Sharpe above buy-and-hold's in at least half the folds).** Leverage does not raise Sharpe. In the up
   folds, where these rules are fully long or levered, their Sharpe equals buy-and-hold's minus costs and funding, so
   they lose those folds by a hair. They win the CAGR and the drawdown by being out of the down folds, which is only
   about a third of the folds. Best fold shares: ETH H29 H25 and H29 H28 52%; BTC at most 43%.
2. **Significance at Bonferroni 0.05 / 1,902.** That requires z >= 4.04. The paired bootstrap's standard error of the
   daily Sharpe gap over these 5.1 years is 0.20-0.41, so a pass needs a Sharpe edge over spot buy-and-hold of about
   +0.8 to +1.6. The best observed edges are +0.15 to +0.58. Each new round adds variants to the count and raises the
   bar. With five years of data, no simple daily-trend rule is likely to clear it. This is a property of the rules plus
   the data length, not a bug; it is stated so the owner can see it before round 3.

**Calendar years:** the strongest rules beat spot buy-and-hold in 3-4 of the 6 (partial) years. They win mostly by
losing less in 2022 and by leverage in 2020 and 2023. All of them lose 2024 on both coins (out of, or only partly in,
that rally), BTC 2025, and ETH 2023 for the H30 family. 2021 depends on the rule.

**Caution:** these are development numbers from a period with two very large crypto bull runs. Leveraged long rules
look best exactly when the sample is a bull market. The deflated-Sharpe probabilities (0.13-0.41) and the bootstrap
p-values say the edge over buy-and-hold is not distinguishable from luck at the rigour the owner set.

## Proposed round 3 (development data only; register before running; few variants, because each one raises the bar)

1. **H32 Vol-managed buy-and-hold core.** Always long; exposure = min(2, 60% / 7-day vol), spot up to 1x, re-sized on
   the 15m clock at drift >= 0.25; no direction filter. This targets the fold-share rule directly: vol-managed exposure
   is the one known way to raise Sharpe inside uptrends, not only by sitting out downtrends. 1 variant.
2. **H33 H31 with spot and the ensemble direction.** H29 H31 trail 4 ATR (the best Sharpe so far), with direction from
   the 10-90 day ensemble (long when the ensemble > 0) instead of the 30-day sign. 1 variant.
3. **H34 Funding-aware leverage.** H29 H30 1.5x/0x, but exposure above 1x only while the last funding rate is at or
   below its trailing 90-day median (crowded longs pay more and unwind harder). 1 variant.
4. **H35 15m hour-of-day exposure.** H32's exposure only in the UTC hours whose trailing-365-day mean 15m return was
   positive (re-estimated each quarter on train data); flat otherwise. Prior: weak, and it trades more. 1 variant.
5. **Owner's call, before round 3 runs:** with Bonferroni over the cumulative count and five years of data, a pass
   needs a Sharpe edge of roughly +0.8 to +1.6 over spot buy-and-hold. Keeping that rule is legitimate; it means the
   loop will very probably end without a development pass, and adding variants makes it harder. Changing the rule is
   the owner's decision only, made before round 3 runs.
