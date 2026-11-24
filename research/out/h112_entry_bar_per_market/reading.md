## Reading (written by hand after the run)

**1. Is the 5-point bar out of reach on history too? On four markets yes, but only since about 2023. On oil, no.**

- Gold, silver, USDJPY and the S&P 500: in 2020 and 2021 the Lead reached 5 points quite often (gold in 21% and 11%
  of steps). It has shrunk every year since. From mid-2023 it reached 5 points in under 1% of steps, and in the last
  year almost never. Gold last reached it on 22 Apr 2025, silver on 25 Sep 2025, the S&P on 27 Sep 2023.
- So on these four markets the Setups book already entered by force nearly every time on history: from mid-2023 on,
  real calls were 0% to 2% of its entries. The live finding matches the history.
- Oil is different. On WTI and Brent the Lead reached 5 points in 29% of steps up to mid-2023. That is more often
  than on BTC and ETH (21%). It still did in 14% of steps in h2 and in 23% of steps in the holdout year. It comes in
  bursts: 63% of steps in Feb 2026, none in Jun 2026, 32% in Oct 2026. The last time was 2 to 3 Nov 2026. The 14 live
  days fell in a quiet spell. For oil the bar is not out of reach.

**2. The fitted bars.** Gold 3.25 points, silver 3.20, USDJPY 3.63, S&P 2.43. For oil the same rule RAISED the bar:
WTI 6.74, Brent 6.96. So the study tested a lower bar on four markets and a higher one on two.

**3. The fitted bars did not do what they were meant to do after 2023.** The bar was set so that it is cleared in 21%
of steps, as on crypto. That held only where it was fitted. Because the Lead keeps shrinking on the four markets, the
new bars were cleared in about 5% to 6% of steps in h2 and 1% to 3% in the holdout. Real calls rose only from 7% to
10% of entries in h2. About nine trades in ten were still forced entries. A bar fitted once does not keep up with a
Lead that drifts.

**4. The result.** The primary rule does not pass. It fails two of the three legs.

- h2: the six books made +2.1R with the scaled bars against +18.3R with the current rule (16.1R less). The noise check
  gives a range of -54.6R to +19.4R for that gap, so it cannot be told from chance, in either direction.
- Holdout: +4.5R against +3.2R (1.3R more; range -8.8R to +9.8R). Nominally higher, and not distinguishable from zero.
- Real calls against forced entries in the new book in h2: real calls lost a little (-0.049R a trade over 142 trades),
  forced entries were flat (-0.000R over 1,271). Real calls were not the better trades.
- The secondary rule (only the entry bar scaled) reads the same: -2.7R in h2, +5.9R in the holdout.

**5. By market (h2).** USDJPY carries most of the gap: +21.3R with the current rule, -5.6R with the lower bar. Silver
was 5R worse. Gold and Brent hardly moved. The S&P was better (+29.5R against +18.5R, on 100 trades). WTI with its
higher bar was 7R better in h2 and 5R worse in the holdout. No market shows the same sign in a convincing way across
both segments, and with one market up and another down by chance this is what noise looks like.

**6. What this says and does not say.** It agrees with the earlier studies: more entries on the Lead's own call did
not pay better than forced entries on this history (H65), and the book's odds and entry bar could not be told from
placebos (H80, H82b). Nothing here supports lowering the bar on the six markets. It also does not show that a lower
bar is harmful: the gaps are inside the noise. It is a replay, so it proves nothing about the future either way.

**7. Dollars and R can disagree.** In the holdout the six books are up a few R and down about $11,600. R counts
every trade the same. Dollars weigh a trade by how much it risked, and a position is never smaller than 1x, so trades
with a far stop cost more than the planned 2% (the audit's finding 5). Silver's holdout book shows it most: +8.0R,
-$3,783, with a worst fall of 73%. The reason given here is the likely one; it was not checked trade by trade.

**8. If the owner still wants real calls on these markets.** A bar fitted once is the wrong tool, because the Lead's
size drifts. A bar that follows the recent Lead (for example the level cleared in 21% of the last 90 days' steps)
would be a different rule and would need its own registration. The prior expectation for it is also low, for the same
reasons. A more useful question may be why the Lead on gold, silver, USDJPY and the S&P has shrunk towards zero since
2022: the odds there are now close to even at almost every step. That was not studied here.

**Not verified.**
- The fits for the last year of BTC, ETH and USDJPY were not in the cache (54 and 38 weekly refits). They were refitted
  on the laptop by the engine's own code. They were not compared with the fits the live box holds.
- The replay's largest forward readings sit close to the live audit's on five of six markets (gold 4.53 against 4.6,
  silver 4.70 against 4.7, S&P 3.62 against 3.5, WTI 4.30 against 4.2, Brent 4.61 against 4.5). USDJPY differs (4.11
  against 5.0). The audit's window starts a day earlier (10 Nov); whether that explains it was not checked.
- The current rule's h2 numbers per market equal the earlier H92 study's table exactly (trades and sum of R, all six
  markets). That is an independent check of the loader and the book for h2. There is no such check for the holdout.
- Only this study's own tests were run (10 tests). The full test suite was not run; no engine file was changed.
