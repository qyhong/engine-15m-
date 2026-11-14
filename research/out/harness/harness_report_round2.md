# Harness loop, round 2: strict outperformance of buy-and-hold at >= 25% CAGR

Generated 2026-11-11 14:10 UTC by `py -3 research/harness/round2.py`. Paper research only. H25-H31 registered in `research/HYPOTHESES.md` at 14:05 UTC on 11 Nov 2026, before any round-2 result. Development data only (out of sample 2020-10-01 to 2025-11-11, 21 walk-forward folds); the sealed holdout (2025-11-11 to 2026-11-11) is untouched.

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

## Rules (owner, set before round 2; per coin)

1 CAGR >= 25% net of 0.10% a side and funding; 2 CAGR > buy-and-hold's; 3 Sharpe > buy-and-hold's and max DD <= buy-and-hold's; 4 Sharpe > buy-and-hold's in >= half the folds; 5 bootstrap p <= 0.05 / 1902 (all variants tried in the loop: 1,838 in round 1 + 64 in round 2) = 2.6e-05, deflated-Sharpe probability reported; 6 no fee_only_at_0.05, no high turnover (> 100 changes a year); 7 (kept from round 1) more than half the folds net positive. Benchmark for the pass: **spot buy-and-hold** (no funding); perp buy-and-hold shown too.

## BTCUSDT

### CAGR against the target and the benchmarks, 0.10% a side (spot buy-and-hold +56.2%, perp buy-and-hold +37.9%, momentum +25.4%)

| Strategy | CAGR | vs 25% | vs spot B&H | vs momentum | Sharpe (spot B&H 1.03) | Max DD (spot B&H 77%) | Calmar | Trades/yr | Avg exposure | Break-even fee | Rules met vs spot (of 8) | vs perp (of 8) | Boot p | DSR | Pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H25 vol-targeted momentum (perp) | +45.8% | +20.8% | -10.5% | +20.3% | 1.06 | 53% | 0.87 | 54 | 0.70 | 0.948% | 4 | 5 | 0.403 | 0.15 | no |
| H26 ensemble long/short (perp) | +14.0% | -11.0% | -42.2% | -11.4% | 0.51 | 57% | 0.25 | 145 | 0.65 | 0.331% | 1 | 1 | 0.828 | 0.01 | no |
| H26 ensemble long-only (perp) | +39.1% | +14.1% | -17.1% | +13.7% | 1.08 | 36% | 1.09 | 73 | 0.40 | 1.263% | 4 | 5 | 0.249 | 0.16 | no |
| H26 ensemble long-only 1.5x (perp) | +55.9% | +30.9% | -0.3% | +30.5% | 1.08 | 52% | 1.08 | 73 | 0.60 | 1.141% | 4 | 5 | 0.356 | 0.16 | no |
| H28 fixed H22 variant (perp) | +31.7% | +6.7% | -24.5% | +6.3% | 1.02 | 49% | 0.65 | 41 | 0.43 | 1.029% | 4 | 5 | 0.329 | 0.13 | no |
| H29 H25 spot longs | +57.0% | +32.0% | +0.7% | +31.5% | 1.23 | 49% | 1.17 | 55 | 0.70 | 1.103% | 5 | 5 | 0.256 | 0.26 | no |
| H29 H28 spot longs | +40.9% | +15.9% | -15.3% | +15.5% | 1.23 | 48% | 0.86 | 41 | 0.43 | 1.256% | 5 | 6 | 0.136 | 0.26 | no |
| H30 trend core 1.5x/0.5x (perp) | +61.3% | +36.3% | +5.0% | +35.8% | 1.03 | 77% | 0.80 | 30 | 1.06 | 1.688% | 6 | 6 | 0.535 | 0.13 | no |
| H29 H30 1.5x/0.5x spot longs | +80.2% | +55.2% | +24.0% | +54.8% | 1.18 | 75% | 1.07 | 30 | 1.06 | 2.054% | 6 | 7 | 0.232 | 0.23 | no |
| H30 trend core 2x/0x (perp) | +71.0% | +46.0% | +14.8% | +45.6% | 1.05 | 80% | 0.89 | 30 | 1.11 | 0.993% | 5 | 5 | 0.616 | 0.14 | no |
| H29 H30 2x/0x spot longs | +88.6% | +63.6% | +32.4% | +63.2% | 1.15 | 78% | 1.14 | 30 | 1.11 | 1.154% | 5 | 6 | 0.478 | 0.21 | no |
| H30 trend core 1.5x/0x (perp) | +61.4% | +36.4% | +5.2% | +36.0% | 1.05 | 67% | 0.91 | 30 | 0.83 | 1.163% | 6 | 6 | 0.470 | 0.14 | no |
| H29 H30 1.5x/0x spot longs | +78.0% | +53.0% | +21.8% | +52.6% | 1.19 | 65% | 1.20 | 30 | 0.83 | 1.379% | 6 | 7 | 0.292 | 0.23 | no |
| H31 vol-target + trail 2.5 ATR (perp) | +46.3% | +21.3% | -9.9% | +20.9% | 1.05 | 54% | 0.86 | 62 | 0.69 | 0.753% | 5 | 6 | 0.462 | 0.15 | no |
| H29 H31 trail 2.5 ATR spot longs | +58.7% | +33.7% | +2.5% | +33.3% | 1.23 | 52% | 1.13 | 62 | 0.69 | 0.892% | 6 | 6 | 0.293 | 0.26 | no |
| H31 vol-target + trail 4 ATR (perp) | +54.2% | +29.2% | -2.1% | +28.7% | 1.14 | 56% | 0.96 | 53 | 0.71 | 1.043% | 5 | 6 | 0.339 | 0.20 | no |
| H29 H31 trail 4 ATR spot longs | +67.6% | +42.6% | +11.3% | +42.1% | 1.32 | 53% | 1.28 | 53 | 0.71 | 1.223% | 6 | 7 | 0.183 | 0.33 | no |
| Buy-and-hold, spot | +56.2% | +31.2% | | | 1.03 | 77% | 0.73 | 0 | | | | | | | |
| Buy-and-hold, perp | +37.9% | +12.9% | | | 0.83 | 79% | 0.48 | 0 | | | | | | | |
| Momentum (daily, 30-day, perp) | +25.4% | +0.4% | | | 0.67 | 63% | 0.41 | 30 | | | | | | | |

### Which rules fail (vs spot buy-and-hold, BTCUSDT)

| Strategy | CAGR >= 25% | CAGR > B&H | Sharpe > B&H & DD <= B&H | fold share (%) | significant | no fee-only-0.05 | turnover <= 100 | folds positive (%) | at 0.05%: CAGR / Sharpe |
|---|---|---|---|---|---|---|---|---|---|
| H25 vol-targeted momentum (perp) | yes | no | yes | no (24) | no | yes | yes | no (48) | +49.0% / 1.11 |
| H26 ensemble long/short (perp) | no | no | no | no (19) | no | yes | no | no (38) | +17.3% / 0.57 |
| H26 ensemble long-only (perp) | yes | no | yes | no (5) | no | yes | yes | no (48) | +41.1% / 1.11 |
| H26 ensemble long-only 1.5x (perp) | yes | no | yes | no (5) | no | yes | yes | no (43) | +59.2% / 1.11 |
| H28 fixed H22 variant (perp) | yes | no | no | no (29) | no | yes | yes | yes (52) | +33.7% / 1.07 |
| H29 H25 spot longs | yes | yes | yes | no (33) | no | yes | yes | no (48) | +60.5% / 1.28 |
| H29 H28 spot longs | yes | no | yes | no (33) | no | yes | yes | yes (52) | +43.0% / 1.28 |
| H30 trend core 1.5x/0.5x (perp) | yes | yes | yes | no (10) | no | yes | yes | yes (52) | +63.7% / 1.05 |
| H29 H30 1.5x/0.5x spot longs | yes | yes | yes | no (29) | no | yes | yes | yes (57) | +82.9% / 1.21 |
| H30 trend core 2x/0x (perp) | yes | yes | no | no (29) | no | yes | yes | yes (52) | +76.2% / 1.08 |
| H29 H30 2x/0x spot longs | yes | yes | no | no (33) | no | yes | yes | yes (52) | +94.3% / 1.19 |
| H30 trend core 1.5x/0x (perp) | yes | yes | yes | no (29) | no | yes | yes | yes (52) | +65.0% / 1.08 |
| H29 H30 1.5x/0x spot longs | yes | yes | yes | no (33) | no | yes | yes | yes (57) | +82.0% / 1.22 |
| H31 vol-target + trail 2.5 ATR (perp) | yes | no | yes | no (38) | no | yes | yes | yes (57) | +50.6% / 1.11 |
| H29 H31 trail 2.5 ATR spot longs | yes | yes | yes | no (43) | no | yes | yes | yes (57) | +63.4% / 1.29 |
| H31 vol-target + trail 4 ATR (perp) | yes | no | yes | no (29) | no | yes | yes | yes (57) | +57.7% / 1.19 |
| H29 H31 trail 4 ATR spot longs | yes | yes | yes | no (43) | no | yes | yes | yes (57) | +71.4% / 1.37 |

### Calendar-year returns, 0.10% a side (BTCUSDT; 2020 from 1 Oct, 2025 to 10 Nov)

| Strategy | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | Years beating spot B&H |
|---|---|---|---|---|---|---|---|
| Buy-and-hold, spot | +168% | +60% | -64% | +156% | +121% | +13% | 0 of 6 |
| Buy-and-hold, perp | +156% | +18% | -66% | +136% | +96% | +8% | 0 of 6 |
| Momentum (perp) | +168% | +23% | -29% | +144% | -29% | -22% | 2 of 6 |
| H25 vol-targeted momentum (perp) | +177% | +11% | -40% | +170% | +34% | +4% | 3 of 6 |
| H26 ensemble long/short (perp) | +124% | +25% | -35% | +37% | +2% | -22% | 1 of 6 |
| H26 ensemble long-only (perp) | +125% | +41% | -24% | +70% | +37% | -3% | 1 of 6 |
| H26 ensemble long-only 1.5x (perp) | +225% | +48% | -34% | +114% | +52% | -6% | 2 of 6 |
| H28 fixed H22 variant (perp) | +110% | +19% | -40% | +91% | +34% | +7% | 1 of 6 |
| H29 H25 spot longs | +187% | +29% | -39% | +187% | +46% | +7% | 3 of 6 |
| H29 H28 spot longs | +116% | +42% | -39% | +99% | +42% | +10% | 1 of 6 |
| H30 trend core 1.5x/0.5x (perp) | +303% | +35% | -66% | +249% | +74% | +2% | 2 of 6 |
| H29 H30 1.5x/0.5x spot longs | +322% | +78% | -65% | +275% | +94% | +6% | 3 of 6 |
| H30 trend core 2x/0x (perp) | +519% | +25% | -69% | +391% | +43% | -7% | 2 of 6 |
| H29 H30 2x/0x spot longs | +548% | +61% | -69% | +422% | +58% | -5% | 3 of 6 |
| H30 trend core 1.5x/0x (perp) | +308% | +39% | -57% | +248% | +41% | -3% | 3 of 6 |
| H29 H30 1.5x/0x spot longs | +327% | +79% | -56% | +270% | +55% | -0% | 4 of 6 |
| H31 vol-target + trail 2.5 ATR (perp) | +222% | +6% | -43% | +228% | +13% | -3% | 3 of 6 |
| H29 H31 trail 2.5 ATR spot longs | +236% | +27% | -42% | +248% | +24% | -1% | 3 of 6 |
| H31 vol-target + trail 4 ATR (perp) | +220% | +11% | -45% | +224% | +41% | +3% | 3 of 6 |
| H29 H31 trail 4 ATR spot longs | +234% | +33% | -44% | +244% | +55% | +5% | 3 of 6 |

- H25 vol-targeted momentum (perp), walk-forward choices (s, vt, Lmax) by count: (0.0, 0.5, 2.0) x8, (0.5, 0.5, 2.0) x3, (0.0, 0.8, 1.5) x3, (0.5, 0.8, 1.5) x2, (0.0, 0.8, 2.0) x2, (0.0, 0.5, 1.5) x2, (0.5, 0.5, 1.5) x1
- H29 H25 spot longs, walk-forward choices (s, vt, Lmax) by count: (0.0, 0.5, 2.0) x9, (0.5, 0.5, 2.0) x3, (0.0, 0.8, 1.5) x2, (0.5, 0.8, 1.5) x2, (0.0, 0.8, 2.0) x2, (0.0, 0.5, 1.5) x2, (0.5, 0.5, 1.5) x1

## ETHUSDT

### CAGR against the target and the benchmarks, 0.10% a side (spot buy-and-hold +56.6%, perp buy-and-hold +36.1%, momentum +39.5%)

| Strategy | CAGR | vs 25% | vs spot B&H | vs momentum | Sharpe (spot B&H 0.96) | Max DD (spot B&H 81%) | Calmar | Trades/yr | Avg exposure | Break-even fee | Rules met vs spot (of 8) | vs perp (of 8) | Boot p | DSR | Pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H25 vol-targeted momentum (perp) | +45.1% | +20.1% | -11.5% | +5.6% | 1.00 | 61% | 0.74 | 52 | 0.55 | 1.043% | 5 | 7 | 0.331 | 0.12 | no |
| H26 ensemble long/short (perp) | +21.3% | -3.7% | -35.3% | -18.2% | 0.62 | 77% | 0.28 | 143 | 0.64 | 0.462% | 2 | 2 | 0.678 | 0.02 | no |
| H26 ensemble long-only (perp) | +34.8% | +9.8% | -21.7% | -4.6% | 0.86 | 49% | 0.72 | 76 | 0.38 | 1.138% | 4 | 5 | 0.393 | 0.07 | no |
| H26 ensemble long-only 1.5x (perp) | +43.4% | +18.4% | -13.2% | +3.9% | 0.86 | 67% | 0.65 | 76 | 0.57 | 0.934% | 3 | 5 | 0.548 | 0.07 | no |
| H28 fixed H22 variant (perp) | +52.2% | +27.2% | -4.4% | +12.7% | 1.22 | 42% | 1.25 | 36 | 0.40 | 1.590% | 5 | 7 | 0.120 | 0.25 | no |
| H29 H25 spot longs | +60.3% | +35.3% | +3.7% | +20.8% | 1.20 | 58% | 1.04 | 51 | 0.55 | 1.323% | 7 | 7 | 0.162 | 0.23 | no |
| H29 H28 spot longs | +65.0% | +40.0% | +8.5% | +25.6% | 1.42 | 37% | 1.77 | 36 | 0.40 | 1.876% | 7 | 7 | 0.044 | 0.41 | no |
| H30 trend core 1.5x/0.5x (perp) | +72.4% | +47.4% | +15.8% | +32.9% | 1.05 | 74% | 0.98 | 27 | 1.03 | 2.118% | 6 | 6 | 0.468 | 0.14 | no |
| H29 H30 1.5x/0.5x spot longs | +96.3% | +71.3% | +39.8% | +56.8% | 1.19 | 71% | 1.35 | 27 | 1.03 | 2.593% | 6 | 6 | 0.225 | 0.23 | no |
| H30 trend core 2x/0x (perp) | +85.5% | +60.5% | +29.0% | +46.1% | 1.12 | 82% | 1.04 | 27 | 1.05 | 1.246% | 4 | 4 | 0.566 | 0.18 | no |
| H29 H30 2x/0x spot longs | +109.1% | +84.1% | +52.6% | +69.7% | 1.22 | 80% | 1.37 | 27 | 1.05 | 1.465% | 5 | 5 | 0.446 | 0.25 | no |
| H30 trend core 1.5x/0x (perp) | +82.6% | +57.6% | +26.0% | +43.1% | 1.12 | 68% | 1.22 | 27 | 0.79 | 1.590% | 6 | 6 | 0.373 | 0.18 | no |
| H29 H30 1.5x/0x spot longs | +105.8% | +80.8% | +49.3% | +66.4% | 1.25 | 67% | 1.57 | 27 | 0.79 | 1.882% | 6 | 7 | 0.232 | 0.27 | no |
| H31 vol-target + trail 2.5 ATR (perp) | +50.4% | +25.4% | -6.1% | +11.0% | 1.12 | 47% | 1.07 | 54 | 0.50 | 0.955% | 5 | 6 | 0.249 | 0.18 | no |
| H29 H31 trail 2.5 ATR spot longs | +64.2% | +39.2% | +7.6% | +24.7% | 1.31 | 45% | 1.42 | 54 | 0.50 | 1.137% | 6 | 7 | 0.121 | 0.32 | no |
| H31 vol-target + trail 4 ATR (perp) | +57.3% | +32.3% | +0.8% | +17.8% | 1.20 | 45% | 1.27 | 44 | 0.51 | 1.271% | 6 | 6 | 0.179 | 0.23 | no |
| H29 H31 trail 4 ATR spot longs | +71.9% | +46.9% | +15.4% | +32.5% | 1.38 | 43% | 1.67 | 44 | 0.51 | 1.498% | 6 | 7 | 0.079 | 0.38 | no |
| Buy-and-hold, spot | +56.6% | +31.6% | | | 0.96 | 81% | 0.69 | 0 | | | | | | | |
| Buy-and-hold, perp | +36.1% | +11.1% | | | 0.79 | 82% | 0.44 | 0 | | | | | | | |
| Momentum (daily, 30-day, perp) | +39.5% | +14.5% | | | 0.82 | 80% | 0.49 | 27 | | | | | | | |

### Which rules fail (vs spot buy-and-hold, ETHUSDT)

| Strategy | CAGR >= 25% | CAGR > B&H | Sharpe > B&H & DD <= B&H | fold share (%) | significant | no fee-only-0.05 | turnover <= 100 | folds positive (%) | at 0.05%: CAGR / Sharpe |
|---|---|---|---|---|---|---|---|---|---|
| H25 vol-targeted momentum (perp) | yes | no | yes | no (43) | no | yes | yes | yes (52) | +48.0% / 1.04 |
| H26 ensemble long/short (perp) | no | no | no | no (24) | no | yes | no | yes (52) | +24.5% / 0.66 |
| H26 ensemble long-only (perp) | yes | no | no | no (14) | no | yes | yes | yes (52) | +36.8% / 0.89 |
| H26 ensemble long-only 1.5x (perp) | yes | no | no | no (14) | no | yes | yes | no (48) | +46.5% / 0.89 |
| H28 fixed H22 variant (perp) | yes | no | yes | no (48) | no | yes | yes | yes (62) | +54.3% / 1.26 |
| H29 H25 spot longs | yes | yes | yes | yes (52) | no | yes | yes | yes (52) | +63.4% / 1.24 |
| H29 H28 spot longs | yes | yes | yes | yes (52) | no | yes | yes | yes (62) | +67.4% / 1.45 |
| H30 trend core 1.5x/0.5x (perp) | yes | yes | yes | no (29) | no | yes | yes | yes (57) | +74.7% / 1.06 |
| H29 H30 1.5x/0.5x spot longs | yes | yes | yes | no (29) | no | yes | yes | yes (57) | +99.0% / 1.20 |
| H30 trend core 2x/0x (perp) | yes | yes | no | no (33) | no | yes | yes | no (48) | +90.5% / 1.14 |
| H29 H30 2x/0x spot longs | yes | yes | yes | no (33) | no | yes | yes | no (48) | +114.8% / 1.24 |
| H30 trend core 1.5x/0x (perp) | yes | yes | yes | no (33) | no | yes | yes | yes (57) | +86.3% / 1.14 |
| H29 H30 1.5x/0x spot longs | yes | yes | yes | no (33) | no | yes | yes | yes (62) | +110.0% / 1.27 |
| H31 vol-target + trail 2.5 ATR (perp) | yes | no | yes | no (43) | no | yes | yes | yes (62) | +54.0% / 1.17 |
| H29 H31 trail 2.5 ATR spot longs | yes | yes | yes | no (48) | no | yes | yes | yes (62) | +68.1% / 1.36 |
| H31 vol-target + trail 4 ATR (perp) | yes | yes | yes | no (38) | no | yes | yes | yes (57) | +60.4% / 1.24 |
| H29 H31 trail 4 ATR spot longs | yes | yes | yes | no (48) | no | yes | yes | yes (57) | +75.3% / 1.43 |

### Calendar-year returns, 0.10% a side (ETHUSDT; 2020 from 1 Oct, 2025 to 10 Nov)

| Strategy | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | Years beating spot B&H |
|---|---|---|---|---|---|---|---|
| Buy-and-hold, spot | +104% | +399% | -67% | +91% | +46% | +7% | 0 of 6 |
| Buy-and-hold, perp | +89% | +243% | -68% | +76% | +28% | +2% | 0 of 6 |
| Momentum (perp) | +51% | +119% | -0% | -4% | -39% | +183% | 2 of 6 |
| H25 vol-targeted momentum (perp) | +66% | +169% | -32% | +19% | -6% | +99% | 2 of 6 |
| H26 ensemble long/short (perp) | +33% | +104% | -22% | -17% | -2% | +57% | 2 of 6 |
| H26 ensemble long-only (perp) | +39% | +160% | -16% | +6% | +16% | +24% | 2 of 6 |
| H26 ensemble long-only 1.5x (perp) | +56% | +223% | -24% | +5% | +19% | +33% | 2 of 6 |
| H28 fixed H22 variant (perp) | +68% | +182% | -22% | +35% | -7% | +83% | 2 of 6 |
| H29 H25 spot longs | +88% | +232% | -32% | +26% | +2% | +103% | 2 of 6 |
| H29 H28 spot longs | +76% | +255% | -21% | +42% | -1% | +86% | 2 of 6 |
| H30 trend core 1.5x/0.5x (perp) | +120% | +372% | -57% | +75% | +3% | +100% | 3 of 6 |
| H29 H30 1.5x/0.5x spot longs | +137% | +576% | -56% | +88% | +15% | +107% | 4 of 6 |
| H30 trend core 2x/0x (perp) | +146% | +363% | -52% | +65% | -25% | +250% | 3 of 6 |
| H29 H30 2x/0x spot longs | +165% | +551% | -51% | +76% | -18% | +258% | 4 of 6 |
| H30 trend core 1.5x/0x (perp) | +107% | +360% | -37% | +54% | -13% | +171% | 3 of 6 |
| H29 H30 1.5x/0x spot longs | +123% | +548% | -37% | +64% | -4% | +178% | 4 of 6 |
| H31 vol-target + trail 2.5 ATR (perp) | +60% | +91% | -12% | +62% | -18% | +125% | 2 of 6 |
| H29 H31 trail 2.5 ATR spot longs | +70% | +135% | -11% | +73% | -11% | +130% | 2 of 6 |
| H31 vol-target + trail 4 ATR (perp) | +66% | +154% | -16% | +60% | -22% | +129% | 2 of 6 |
| H29 H31 trail 4 ATR spot longs | +76% | +214% | -15% | +70% | -15% | +134% | 2 of 6 |

- H25 vol-targeted momentum (perp), walk-forward choices (s, vt, Lmax) by count: (0.0, 0.5, 1.5) x5, (0.5, 0.5, 1.5) x5, (0.0, 0.5, 2.0) x4, (0.0, 0.8, 2.0) x3, (0.0, 0.8, 1.5) x2, (0.5, 0.8, 1.5) x1, (0.5, 0.8, 2.0) x1
- H29 H25 spot longs, walk-forward choices (s, vt, Lmax) by count: (0.0, 0.5, 1.5) x5, (0.5, 0.5, 1.5) x5, (0.0, 0.5, 2.0) x4, (0.0, 0.8, 1.5) x3, (0.0, 0.8, 2.0) x3, (0.5, 0.8, 2.0) x1

## H27: two-coin books (half BTC, half ETH, never rebalanced; vs the same spot buy-and-hold book)

| Book | CAGR | Sharpe | Max DD | Calmar | Trades/yr (both coins) | Fold share vs B&H | Folds positive | Boot p | DSR | Pass |
|---|---|---|---|---|---|---|---|---|---|---|
| H27 book: H28 on both coins | +43.4% | 1.20 | 41% | 1.05 | 77 | 33% | 57% | 0.141 | 0.24 | no |
| H27 book: H25 on both coins | +45.4% | 1.08 | 51% | 0.88 | 107 | 29% | 48% | 0.283 | 0.16 | no |
| Buy-and-hold book, spot | +56.4% | 0.99 | 79% | 0.71 | | | | | | |
| Buy-and-hold book, perp | +37.0% | 0.80 | 80% | 0.46 | | | | | | |

| Book | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| Buy-and-hold book, spot | +136% | +207% | -67% | +111% | +75% | +10% |
| H27 book: H28 on both coins | +89% | +92% | -28% | +51% | +8% | +49% |
| H27 book: H25 on both coins | +121% | +70% | -36% | +76% | +17% | +36% |

## Round 2 result

- Development passes (all rules, BTC and ETH, vs spot buy-and-hold): **none**.
- Closest: H29 H30 1.5x/0.5x spot longs (rules met 6/8 on BTC, 6/8 on ETH; failing on BTC: 4_fold_share_ge_half, 5_significant; on ETH: 4_fold_share_ge_half, 5_significant).
- Holdout looks used: 0.
