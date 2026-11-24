# H111: pairs as one bet (BTC+ETH, gold+silver, WTI+Brent) on the Setups book

A replay on history, registered before any number was computed (research/HYPOTHESES.md, H111). It is post-mortem
material, not validation. Nothing live was changed. The books are the engine's own Setups rule (`b_targets`),
one $10,000 paper book per market, 2020-02-05 to 2026-11-24.

## Verdict by the registered condition

**V1 (pair-half) DOES NOT PASS.**

| Leg | Needed | Met |
|---|---|---|
| h1 | V1's ratio above V0's (+0.54 against +0.65) and V1's total above zero (+88.4) | NO |
| h2 | V1's ratio above V0's (-0.38 against -0.65) and V1's total above zero (-54.2) | NO |
| Holdout | V1's ratio above V0's (-0.66 against -0.43) and V1's total above zero (-98.6) | NO |
| Total kept | V1's total over all history at least 85% of V0's (-26.9 against +18.1) | NO |

By the brief's wording alone (the ratio higher in the three legs and the total kept, with no need for V1's total
to be above zero): does not pass (h1 no, h2 yes, holdout no, total_kept no).
The registered condition is the one that decides.

## Words used

- **Point**: one percent of one book's own money. A trade that makes 2% of its book adds 2 points. Points of the
  eight books are added up by the day a trade closed. Eight books each losing 1% on one day is a day of -8 points.
- **V0**: the books as they are. **V1**: a trade that opens while its pair partner already holds a trade on the same
  side counts at half; two partner trades opened at the same moment both count at half. **V1s**: as V1, but trades
  opened at the same moment stay full. **V2**: a trade is left out when four other markets already hold that side.
- **Worst day**: the worst single day of portfolio points. **Worst fall**: the largest drop of the running total from
  its highest point so far. **Ratio**: total divided by worst fall. Higher is better. Making every trade smaller by
  the same amount does not change it.
- **h1**: 2020-02-05 to 2023-06-07. **h2**: 2023-06-08 to 2025-11-10. **Holdout**: 2025-11-11 to 2026-11-10. **Forward**: 2026-11-11 to 2026-11-24, the days that prompted this
  study, shown apart and part of no leg.

## Reading

1. **The books are one bet. History agrees with the live audit.** Five or more of the eight books held the same side
   77% of the time. BTC and ETH held the same side 81% of the time, gold and silver 76%, WTI and Brent 91%. On 17 of
   the 20 worst days both members of a pair lost. On an ordinary day that happens 16% of the time.
2. **Halving the second trade of a pair made the falls smaller, but only as much as betting less would.** V1 halves 3,667
   of 5,971 trades. That takes 31% off the total size. The worst fall shrank by 34% (467 to 309 points). The worst day
   went from -40 to -27 points. The 20 worst days together went from -534 to -325 points.
3. **It did not make the result better for the risk taken.** The ratio went down in h1 (+0.65 to +0.54) and in the
   holdout (-0.43 to -0.66). It went up only in h2, where both totals are losses. Over all history the total went from
   +18 points to -27.
4. **Which trades were halved did not matter.** Halving the same number of trades picked at random did as well or
   better than V1 in 71% of tries over all history (52% in h1, 36% in h2, 97% in the holdout).
5. **Why.** The trade that opens second, when the partner is already in, is not the worse trade. It made +0.03 points a
   trade against -0.08 for the trades left at full size. In the holdout: +0.05 against -0.63. So V1 cut the slightly
   better trades and kept the slightly worse ones whole.
6. **The Setups book itself is flat on history.** +18 points in almost seven years, with a worst fall of 467 points. It
   lost in h2 (-137) and in the holdout (-86). This matches H65 and H68. A sizing rule cannot turn a flat book into a
   good one, and the registered condition could not be met in a period where the book loses unless the rule turned
   that loss into a gain.
7. **V2 (leave out the 5th trade on one side), descriptive only.** It left out 1,391 trades. The worst fall went from
   467 to 255 points and the total from +18 to +10. The ratio stayed at +0.04. The trades it left out were no worse
   than the ones it kept (+0.006 against +0.002 points a trade). They were better in h1 and worse in h2 and the
   holdout. This says nothing firm: a real book that skips a trade would trade differently afterwards.
8. **The 14 forward days.** V1 would have halved the gain (+72 to +37 points), because the trades it halves were the
   winners of a falling market. On 23 Nov the replay closed seven trades, five of them stops, for +1.2 points. V1 makes
   that day -3.1 points: it halves the two winning oil trades and only two of the five stops.

**What this means.** The risk the audit found is real: the eight books rise and fall together. But on this history the
pair rule is a way to bet less, not a way to bet better. If smaller falls are wanted, a smaller size on every trade
does the same and is simpler. By the registered condition there is no case for a forward paper shadow of the pair
rule. Nothing was changed.

## Limits

- This is a replay on history. It is post-mortem material, not validation. No part of this history was unseen for the
  Setups book (H65, H67 and H68 read all of it).
- Results are booked when a trade closes. A loss that is still open is not counted until then. A book marked every 15
  minutes would show larger worst days and larger falls. For scale: H68 measured a worst fall of 61.6% on the eight
  books' marked money.
- Points are added across books and are not compounded. Each book counts the same, whatever money it has left. In the
  replay the BTC book fell as low as $610.
- "Half size" here is counting. The engine never sizes below 1x, so a real half-size trade is not always possible
  under today's sizing rule.
- V1 is one way to count a pair as one bet. Others were not tested (for example capping the pair's risk by the stop
  distances, or resizing the trade that is already open).
- The three periods are parts of one history of eight markets that moved together. They are not three separate tests.
- The placebo and all tables are descriptive. Only V1 was tested against a condition.
- The 5+ table starts on 2021-01-12, when the last of the eight books (S&P 500) has its first decided session.

## Not verified

- The replay's forward days were not matched trade for trade with the live record. The live Setups book took
  -$2,086 on five stops on 23 Nov. The replay has the five stops and two winning closes that day (-$480 in all). The
  live books started fresh on 10-11 Nov and the engine changed version twice in those days.
- The last year of fits was recomputed on this laptop. The trades closed by H68's cut (21 Nov 13:45 UTC) match H68
  exactly (5,963 trades, +22.5R, and the same split), so the replay is the same book. The days after that cut have
  nothing to be compared with.

## The numbers

Each cell: total points | worst day | worst fall | ratio.

| Variant | All history | h1 | h2 | Holdout | Forward (14 days) |
|---|---|---|---|---|---|
| V0 current | +18.1 | -40.3 | 466.6 | +0.04 | +168.2 | -40.3 | 259.3 | +0.65 | -136.9 | -22.2 | 209.3 | -0.65 | -85.7 | -27.1 | 200.5 | -0.43 | +72.5 | -3.0 | 3.0 | +24.24 |
| V1 pair-half (primary) | -26.9 | -27.0 | 308.5 | -0.09 | +88.4 | -27.0 | 163.3 | +0.54 | -54.2 | -16.7 | 141.6 | -0.38 | -98.6 | -19.1 | 148.7 | -0.66 | +37.5 | -3.1 | 4.6 | +8.19 |
| V1s (descriptive) | -53.1 | -33.8 | 369.4 | -0.14 | +101.8 | -33.8 | 179.0 | +0.57 | -90.9 | -16.7 | 143.1 | -0.64 | -113.7 | -24.5 | 155.9 | -0.73 | +49.7 | -2.1 | 2.1 | +23.48 |
| V2 direction cap (descriptive) | +10.1 | -36.3 | 254.5 | +0.04 | +39.7 | -36.3 | 167.4 | +0.24 | -23.2 | -19.4 | 169.9 | -0.14 | -50.1 | -27.0 | 151.9 | -0.33 | +43.8 | -5.5 | 10.9 | +4.01 |

Trades: All history 5971 (in pairs 5007, V1 halves 3667, V1s halves 3161, V2 drops 1391); h1 2945 (in pairs 2514, V1 halves 1846, V1s halves 1582, V2 drops 729); h2 2217 (in pairs 1813, V1 halves 1280, V1s halves 1106, V2 drops 498); Holdout 774 (in pairs 653, V1 halves 517, V1s halves 452, V2 drops 154); Forward (14 days) 35 (in pairs 27, V1 halves 24, V1s halves 21, V2 drops 10).

V2 is descriptive only. A real book that skips a trade is flat afterwards and would enter differently later.
Here the trade is only removed from the record. The replay cannot show what the book would then have done.

## Does it matter WHICH trades are halved

Placebo: the same number of trades halved in each market and period, picked at random, 2000 times.

| | All history | h1 | h2 | Holdout | Forward (14 days) |
|---|---|---|---|---|---|
| V0 ratio | +0.04 | +0.65 | -0.65 | -0.43 | +24.24 |
| V1 ratio | -0.09 | +0.54 | -0.38 | -0.66 | +8.19 |
| Random halving, median ratio | +0.03 | +0.56 | -0.45 | -0.48 | +12.49 |
| Share of random draws at least as good as V1 | 71% | 52% | 36% | 97% | 97% |

## The trades V1 halves against the ones it leaves full

Pair markets only, at full size. Each cell: trades, mean points a trade, share won.

| | All history | h1 | h2 | Holdout | Forward (14 days) |
|---|---|---|---|---|---|
| Halved by V1 (partner already on that side) | 3667, +0.025, 44% | 1846, +0.087, 44% | 1280, -0.129, 42% | 517, +0.050, 44% | 24, +2.918, 79% |
| Left full | 1340, -0.083, 40% | 668, +0.028, 40% | 533, -0.081, 41% | 136, -0.629, 41% | 3, -0.345, 33% |
| Dropped by V2 (all markets) | 1391, +0.006, 44% | 729, +0.176, 46% | 498, -0.228, 40% | 154, -0.231, 44% | 10, +2.878, 80% |
| Kept by V2 (all markets) | 4580, +0.002, 42% | 2216, +0.018, 42% | 1719, -0.014, 43% | 620, -0.081, 42% | 25, +1.750, 64% |

## How often five or more markets hold the same side

Share of time, 2021-01-12 17:30 to 2026-11-23 20:45, positions carried over closed hours.

| | All history | h1 | h2 | Holdout | Forward (14 days) |
|---|---|---|---|---|---|
| 5+ on one side (long or short) | 77% | 83% | 75% | 69% | 100% |
| 5+ long | 51% | 46% | 55% | 52% | 0% |
| 5+ short | 27% | 36% | 20% | 17% | 100% |

Largest number of markets on one side, share of time (all history): 4: 22%, 5: 34%, 6: 25%, 7: 15%, 8: 3%.

## The pairs

| Pair | Daily results move together (correlation, all days) | Only days both closed a trade | Both hold the same side, share of time | Opposite sides | Trades V1 halves |
|---|---|---|---|---|---|
| BTC + ETH | +0.25 | +0.47 (391 days) | 81% | 17% | BTC 69%, ETH 73% |
| Gold + Silver | +0.16 | +0.33 (271 days) | 76% | 21% | Gold 70%, Silver 73% |
| WTI + Brent | +0.51 | +0.73 (355 days) | 91% | 7% | WTI 78%, Brent 79% |

Correlation runs from -1 to +1. 0 means the two books' days have nothing to do with each other. +1 means they
win and lose together every day.

Correlation by period: BTC + ETH: h1 +0.25, h2 +0.24, holdout +0.21, forward +0.55; Gold + Silver: h1 +0.19, h2 +0.09, holdout +0.21, forward +0.58; WTI + Brent: h1 +0.51, h2 +0.38, holdout +0.63, forward +1.00.

## The 20 worst days of the books as they are (V0)

On 17 of the 20, both members of at least one pair lost that day (BTC + ETH: 9, Gold + Silver: 6, WTI + Brent: 11).
Over all days that happens on 15.8% of days, and on 34% of losing days.
The 20 days together: V0 -533.6 points, V1 -325.0, V2 -413.7.

| Day | V0 | V1 | V2 | Markets losing | Pairs with both losing |
|---|---|---|---|---|---|
| 2020-03-20 | -40.3 | -20.2 | -7.7 | 3 | WTI+Brent |
| 2020-04-02 | -39.6 | -23.3 | -36.3 | 3 | BTC+ETH |
| 2020-05-07 | -37.3 | -27.0 | -31.6 | 4 | WTI+Brent |
| 2020-03-11 | -34.0 | -17.5 | -33.0 | 3 | WTI+Brent |
| 2022-03-15 | -30.7 | -18.7 | -31.8 | 4 | Gold+Silver, WTI+Brent |
| 2020-05-11 | -28.2 | -15.2 | -23.3 | 4 | WTI+Brent |
| 2022-09-09 | -27.5 | -18.7 | -10.8 | 7 | BTC+ETH, Gold+Silver |
| 2026-07-27 | -27.1 | -17.4 | -10.5 | 6 | BTC+ETH, WTI+Brent |
| 2026-01-30 | -27.0 | -18.7 | -27.0 | 3 | Gold+Silver |
| 2026-03-09 | -24.8 | -15.7 | -24.8 | 4 | WTI+Brent |
| 2026-02-08 | -24.5 | -19.1 | -24.5 | 2 | - |
| 2022-03-09 | -23.9 | -13.0 | -23.9 | 6 | BTC+ETH, Gold+Silver, WTI+Brent |
| 2021-05-20 | -23.7 | -11.9 | -23.7 | 1 | - |
| 2024-08-08 | -22.2 | -11.1 | -19.4 | 3 | BTC+ETH |
| 2021-01-29 | -22.1 | -15.1 | -7.8 | 2 | - |
| 2020-03-24 | -21.3 | -13.7 | -16.1 | 3 | Gold+Silver |
| 2021-12-07 | -20.4 | -11.3 | -19.9 | 5 | BTC+ETH, WTI+Brent |
| 2024-05-03 | -19.7 | -15.6 | -11.5 | 5 | BTC+ETH |
| 2021-07-21 | -19.7 | -8.5 | -13.9 | 4 | BTC+ETH, WTI+Brent |
| 2024-11-06 | -19.5 | -13.4 | -16.4 | 6 | BTC+ETH, Gold+Silver, WTI+Brent |

## Per market

| Market | Trades | Short | Points V0 (all) | h1 | h2 | Holdout | Forward | Points V1 (all) | V1 halves | V2 drops | Sum of R |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BTC | 1063 | 49% | -162.2 | +1.0 | -137.4 | -37.4 | +11.6 | -125.2 | 738 | 259 | -68.0 |
| ETH | 1013 | 49% | +191.8 | +133.5 | -8.0 | +56.4 | +9.9 | +136.7 | 737 | 247 | +58.2 |
| Gold | 752 | 41% | -5.1 | -81.1 | +56.7 | +8.2 | +11.2 | +17.5 | 529 | 175 | +7.0 |
| Silver | 725 | 41% | -66.5 | -41.8 | -6.5 | -35.6 | +17.4 | -82.0 | 526 | 199 | +4.4 |
| USDJPY | 723 | 39% | +18.1 | -12.2 | +46.1 | -18.3 | +2.5 | +18.1 | 0 | 120 | +9.0 |
| S&P 500 | 241 | 29% | +21.1 | +2.3 | +25.3 | -7.7 | +1.1 | +21.1 | 0 | 58 | +18.2 |
| WTI | 732 | 46% | +34.7 | +114.2 | -52.0 | -35.1 | +7.5 | +15.6 | 568 | 155 | -4.1 |
| Brent | 722 | 45% | -13.7 | +52.3 | -61.3 | -16.3 | +11.5 | -28.8 | 569 | 178 | -1.4 |

## Check against H68

Trades closed by 2026-11-21 13:45 UTC: here 5963 trades, +22.5R (BTC+ETH 2074, -7.7R; the other six 3889, +30.3R). H68 reported 5963,
+22.5R (BTC+ETH 2074, -7.7R; the other six 3889, +30.3R).
