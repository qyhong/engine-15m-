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
