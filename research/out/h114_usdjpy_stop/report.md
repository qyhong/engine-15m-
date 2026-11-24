# H114: USDJPY in the Setups book. A wider stop, or leave it out?

Run 2026-11-24 12:24 UTC on the laptop. History replay, paper only. Registered before any number
(`research/HYPOTHESES.md`, section H114). Nothing live was changed by this study.

A replay on history is a look back. It is not proof that a rule works. The only test is forward paper trading.

## The answer in short

- **The wider stop (3.0): DOES NOT PASS** by the condition fixed in advance.
  First half yes, second half NO, holdout NO, total result higher than today's rule NO.
  (First half: yes by the registered check, NO by the plain ratio)
- **Leave USDJPY out: the record does not make that case by the rule written down in advance.**
  Today's rule, sum of R: first half -5.5, second half +14.6, holdout -9.5. The rule asked for all three at or below zero.

## What it means

Written by hand after the run, from the tables below.

**1. A wider stop did not help.** With the stop at 3.0 barriers the book ended at -$2,910. Today's rule ended at -$688.
The 3.0 stop lost in the second half (-14.0%) where today's rule gained (+16.2%). It lost a little more in the holdout
too (-18.4% against -17.4%). It only did better in the first half, and there it still lost (-17.5% against -19.9%).

**2. The three stops give no pattern.** 2.0 loses a little, 3.0 loses more, 4.0 gains a little (+$896). If a wider stop
truly helped, 3.0 would sit between 2.0 and 4.0. It does not. The sums of R are +9.0, -10.7 and +8.0, and each chance
band is 35R or wider. None of the three can be told from zero on this history. The 4.0 stop was not graded and would not
have passed either: it made nothing in the second half (+$3) and lost in the holdout (-14.6%).

**3. Why the wider stop does not pay here.** A loss is a full stop at any width: about -1R. But Target 1 hardly moves
out with the stop (0.68%, 0.77% and 0.73% of price). It comes from a chart level or from a typical day's travel. So with a wider stop a win is worth less
against the risk: the usual Target 1 is 1.31R away today, 0.89R with the 3.0 stop and 0.66R with the 4.0 stop. More
trades win (42%, 47%, 54%), but each win is smaller. The two roughly cancel.

**4. The stops were not hit by noise more than chance would do.** After a stop-out at today's distance, price was back
at the entry within a day 36% of the time. It ran a further full stop distance the other way 39% of the time. About
equal. A 3.0 stop would have sat through 110 of those 146 returns, and the 3.0 book still did worse, for the reason in 3.

**5. Leave it out?** The rule written down in advance is not met: the second half was positive (+14.6R). But the
record is thin. In 723 trades over six and a half years the book made +9.0R (chance band 72R) and ended at -$688, with
a worst fall of 53%. All of the gain came from one stretch, June 2023 to November 2025 (+24.1R). The first half lost
(-5.5R), the last twelve months lost (-9.5R) and the live days so far lost. This history gives no reason to expect the
Setups rule to earn on USDJPY, and no proof that it loses. Leaving it out would be the owner's judgement, not a result
of this study. The Setups book on USDJPY is paper only; the vault copies BTC and ETH.

**6. What follows.** No proposal for a forward paper book with a wider stop: the tested stop did not pass. The choice
left is the owner's: keep USDJPY in the Setups book as it is, or leave it out. Nothing was changed.

**7. Not verified.** The first run had to refit 38 weekly fits that the copied cache did not hold (about the last 38
weeks). Whether they equal the live box's own fits was not checked. The 2.0 book does match what H62 and H65
published (the same first half to the dollar, the same trade count). The replay's forward trades are not the live
book's six trades: the replay arrives at 11 Nov in a position of its own.

## Words used

- **Setups book**: the paper book `b_targets`. It sells half at Target 1, the rest at Target 2, and moves the stop to the entry after Target 1.
- **Barrier**: 1.5 times the average hourly range of the last 14 hours. The engine measures distances in barriers.
- **Stop**: the price where a losing trade is closed. Today it is 2.0 barriers from the entry. Tested here: 3.0 and 4.0.
- **Size**: the engine sizes each trade so that a stop costs about 2% of the book. A wider stop means a smaller position.
- **R**: a trade's result divided by what it risked at its stop. -1R is a full stop. +2R is twice the risk, won.
- **Net**: the change in the book's value, fees included, open trades marked at the last price.
- **Worst fall**: the largest drop of the book from a high to a later low inside the period, in percent.
- **Net / worst fall**: net in percent divided by the worst fall in percent. Higher is better. It asks what the gain cost in pain.
- **Stop-out**: a trade closed at its first stop, before Target 1.
- **Periods**: first half = 2020-04-08 to 2023-06-08. Second half = 2023-06-08 to 2026-11-24 (it contains the holdout).
  Holdout = from 2025-11-11. Forward = from 2026-11-11 (the days the engine has run live).

## How the check was run

- USDJPY only, 2020-04-08 21:00 to 2026-11-24 04:30 UTC. Three books, each from $10,000, run by the engine's own code.
- The only setting changed is the stop distance. No engine file was edited.
- Gate: the 2.0 book equals the engine's own Setups book on every trade and every bar (723 trades). Passed.
- The targets move with the stop. That is the engine's own behaviour and it was kept. See the last table.

## Results per period

| Period | Book | Trades | Won | Sum of R | Chance band | Mean R | Net $ | Net % | Fees $ | Worst fall | Net / worst fall |
|---|---|---|---|---|---|---|---|---|---|---|---|
| All history | Stop 2.0 (current) | 723 | 42% | +9.0 | +/- 72 | +0.013 | -688 | -6.9% | 6236 | -53.1% | -0.13 |
| All history | Stop 3.0 (tested) | 453 | 47% | -10.7 | +/- 50 | -0.024 | -2910 | -29.1% | 2468 | -46.2% | -0.63 |
| All history | Stop 4.0 (for comparison) | 296 | 54% | +8.0 | +/- 35 | +0.027 | +896 | +9.0% | 1467 | -31.4% | +0.28 |
| First half | Stop 2.0 (current) | 338 | 41% | -5.5 | +/- 50 | -0.016 | -1986 | -19.9% | 2563 | -53.1% | -0.37 |
| First half | Stop 3.0 (tested) | 215 | 44% | -7.1 | +/- 36 | -0.033 | -1754 | -17.5% | 1203 | -46.2% | -0.38 |
| First half | Stop 4.0 (for comparison) | 155 | 52% | +6.4 | +/- 27 | +0.041 | +893 | +8.9% | 740 | -31.4% | +0.28 |
| Second half | Stop 2.0 (current) | 385 | 43% | +14.6 | +/- 52 | +0.038 | +1298 | +16.2% | 3672 | -49.5% | +0.33 |
| Second half | Stop 3.0 (tested) | 238 | 49% | -3.6 | +/- 34 | -0.015 | -1156 | -14.0% | 1266 | -43.8% | -0.32 |
| Second half | Stop 4.0 (for comparison) | 141 | 56% | +1.5 | +/- 23 | +0.011 | +3 | +0.0% | 726 | -28.2% | +0.00 |
| Second half before the holdout | Stop 2.0 (current) | 299 | 44% | +24.1 | +/- 46 | +0.081 | +3266 | +40.8% | 2713 | -42.4% | +0.96 |
| Second half before the holdout | Stop 3.0 (tested) | 189 | 52% | +7.0 | +/- 31 | +0.037 | +442 | +5.4% | 993 | -33.4% | +0.16 |
| Second half before the holdout | Stop 4.0 (for comparison) | 106 | 59% | +10.3 | +/- 20 | +0.097 | +1869 | +17.2% | 535 | -17.5% | +0.98 |
| Holdout | Stop 2.0 (current) | 86 | 41% | -9.5 | +/- 23 | -0.111 | -1968 | -17.4% | 959 | -28.1% | -0.62 |
| Holdout | Stop 3.0 (tested) | 49 | 39% | -10.7 | +/- 15 | -0.217 | -1598 | -18.4% | 272 | -25.4% | -0.72 |
| Holdout | Stop 4.0 (for comparison) | 35 | 46% | -8.7 | +/- 10 | -0.249 | -1866 | -14.6% | 191 | -20.0% | -0.73 |
| Forward | Stop 2.0 (current) | 4 | 50% | -1.1 | +/- 4 | -0.264 | -80 | -0.9% | 46 | -6.3% | -0.14 |
| Forward | Stop 3.0 (tested) | 2 | 50% | -0.7 | +/- 3 | -0.343 | -57 | -0.8% | 12 | -4.2% | -0.19 |
| Forward | Stop 4.0 (for comparison) | 3 | 67% | -0.5 | +/- 3 | -0.166 | -38 | -0.3% | 20 | -3.1% | -0.11 |

Trades are counted in the period they were entered. Net % is against the book's value at the period's start.
The forward rows are about two weeks: a description, not a result.
Chance band: how far the sum of R can drift by luck alone over that many trades (two standard errors, as if the
trades were independent). A sum of R inside its band cannot be told from zero. This column was added after the
first run. It is a yardstick and is not part of the registered condition.

## The condition fixed in advance, leg by leg

A period counts for the wider stop if its net / worst fall is higher than today's rule.
Where the wider stop lost money in a period, the ratio misleads. There the period counts only if it lost less
and its worst fall is not deeper. This guard was registered before the run.
The plain ratio, with no guard, is shown beside it. Where the two disagree, both are given.

| Check | Stop 2.0 (current) | Stop 3.0 | Plain ratio higher for 3.0 | Registered check holds for 3.0 | Stop 4.0 (not graded) |
|---|---|---|---|---|---|
| First half: net / worst fall | -0.37 | -0.38 | NO | yes (by the guard: net -17.5% against -19.9%, worst fall -46.2% against -53.1%) | +0.28 (would hold; plain ratio higher) |
| Second half: net / worst fall | +0.33 | -0.32 | NO | NO (by the guard: net -14.0% against +16.2%, worst fall -43.8% against -49.5%) | +0.00 (would not hold; plain ratio not higher) |
| Holdout: net / worst fall | -0.62 | -0.72 | NO | NO (by the guard: net -18.4% against -17.4%, worst fall -25.4% against -28.1%) | -0.73 (would hold; plain ratio not higher) |
| All history: net $ | -688 | -2910 | NO | NO | +896 (higher) |

Holdout: the guard compares the net in percent of each book's value at the period's start (set in the code before
the run; the registration did not name the unit). In dollars the 3.0 book lost less there (-1598 against -1968),
because it entered the period with $8688 against $11280. In dollars this check would hold. The verdict does not turn on it.

**Verdict for the 3.0 stop: DOES NOT PASS.** With the plain ratio and no guard: does not pass. The 4.0 stop, had it been graded: would not pass (plain ratio: would not pass).
A pass would lead only to a proposal for a forward paper book. It would not change a live book.

## Were the stops hit by noise?

For each stop-out: did price trade back at the entry within the next 96 sessions (24 hours of trading)?
The yardstick: did price instead run a further full stop distance past the stop in the same time?
If price had no memory the two shares would be about equal. Stops hit by noise would show a clearly larger first share.

| Period | Book | Stop-outs | Judged | Back at the entry | Ran a further stop distance | Both | Neither |
|---|---|---|---|---|---|---|---|
| All history | Stop 2.0 (current) | 401 | 401 | 36% | 39% | 22 | 122 |
| All history | Stop 3.0 (tested) | 218 | 218 | 20% | 22% | 4 | 130 |
| All history | Stop 4.0 (for comparison) | 109 | 109 | 7% | 14% | 0 | 86 |
| First half | Stop 2.0 (current) | 192 | 192 | 35% | 40% | 10 | 58 |
| First half | Stop 3.0 (tested) | 106 | 106 | 13% | 23% | 1 | 69 |
| First half | Stop 4.0 (for comparison) | 59 | 59 | 3% | 8% | 0 | 52 |
| Second half | Stop 2.0 (current) | 209 | 209 | 37% | 38% | 12 | 64 |
| Second half | Stop 3.0 (tested) | 112 | 112 | 26% | 22% | 3 | 61 |
| Second half | Stop 4.0 (for comparison) | 50 | 50 | 12% | 20% | 0 | 34 |
| Second half before the holdout | Stop 2.0 (current) | 158 | 158 | 39% | 39% | 11 | 45 |
| Second half before the holdout | Stop 3.0 (tested) | 84 | 84 | 26% | 19% | 3 | 49 |
| Second half before the holdout | Stop 4.0 (for comparison) | 34 | 34 | 18% | 9% | 0 | 25 |
| Holdout | Stop 2.0 (current) | 51 | 51 | 31% | 33% | 1 | 19 |
| Holdout | Stop 3.0 (tested) | 28 | 28 | 25% | 32% | 0 | 12 |
| Holdout | Stop 4.0 (for comparison) | 16 | 16 | 0% | 44% | 0 | 9 |
| Forward | Stop 2.0 (current) | 2 | 2 | 50% | 0% | 0 | 1 |
| Forward | Stop 3.0 (tested) | 1 | 1 | 0% | 0% | 0 | 1 |
| Forward | Stop 4.0 (for comparison) | 1 | 1 | 0% | 0% | 0 | 1 |

"Judged" leaves out stop-outs with fewer than 96 later sessions on file. The rest of the bar that hit the stop is not counted.

Of today's rule's stop-outs that were back at the entry: how many would a wider stop from the same entry have sat through?

| Period | Back at the entry | A 3.0 stop holds | A 4.0 stop holds |
|---|---|---|---|
| All history | 146 | 110 (75%) | 133 (91%) |
| First half | 68 | 56 (82%) | 63 (93%) |
| Second half | 78 | 54 (69%) | 70 (90%) |
| Second half before the holdout | 62 | 42 (68%) | 54 (87%) |
| Holdout | 16 | 12 (75%) | 16 (100%) |
| Forward | 1 | 0 (0%) | 1 (100%) |

This is the same entry with a wider stop, not the wider book: once one exit differs, the books trade at different times.

## Size, stop distance and targets (checks)

| Book | Median stop distance | Range | Median size | Trades at the 1x floor | At the 100x cap | Mean result of a stop-out | Worst trade | Median hold |
|---|---|---|---|---|---|---|---|---|
| Stop 2.0 (current) | 0.45% | 0.14% to 1.97% | 4.5x | 0.0% | 0.0% | -1.05R | -1.52R | 123 sessions |
| Stop 3.0 (tested) | 0.71% | 0.25% to 2.78% | 2.8x | 1.8% | 0.0% | -1.04R | -2.58R | 195 sessions |
| Stop 4.0 (for comparison) | 0.88% | 0.37% to 3.27% | 2.3x | 5.7% | 0.0% | -1.03R | -1.94R | 311 sessions |

| Book | Target 1 from a Fibonacci level | from a day's travel | from 1.5R | Median Target 1 | Median Target 2 | Target 2 from a Fibonacci level | Not reproduced |
|---|---|---|---|---|---|---|---|
| Stop 2.0 (current) | 361 | 362 | 0 | 0.68% (1.31R) | 1.06% (2.00R) | 361 | 0 |
| Stop 3.0 (tested) | 232 | 221 | 0 | 0.77% (0.89R) | 1.51% (2.00R) | 232 | 0 |
| Stop 4.0 (for comparison) | 135 | 161 | 0 | 0.73% (0.66R) | 1.77% (2.00R) | 135 | 0 |

Target distances are from the entry, in percent of price and in R. "Not reproduced" counts trades whose targets
this script could not recompute exactly from the engine's own function; they are left out of this table only.

## Leave USDJPY out? Today's rule on its own record

| Period | Trades | Won | Sum of R | Mean R | Net $ | Worst fall | Sum of R at or below zero |
|---|---|---|---|---|---|---|---|
| All history | 723 | 42% | +9.0 | +0.013 | -688 | -53.1% | no |
| First half | 338 | 41% | -5.5 | -0.016 | -1986 | -53.1% | yes |
| Second half | 385 | 43% | +14.6 | +0.038 | +1298 | -49.5% | no |
| Second half before the holdout | 299 | 44% | +24.1 | +0.081 | +3266 | -42.4% | no |
| Holdout | 86 | 41% | -9.5 | -0.111 | -1968 | -28.1% | yes |
| Forward | 4 | 50% | -1.1 | -0.264 | -80 | -6.3% | yes |

Rule written down in advance: a proposal to leave the market out only if the sum of R is at or below zero in the
first half AND the second half AND the holdout. Result: not all three, so no proposal by this rule.
Leaving a market out is the owner's decision either way. This study changes nothing.

## The replay's trades in the forward days

- Stop 2.0 (current): 11-11 14:30 long at 159.620, stop 0.30% away, out 11-13 18:00 T1+STOP_BE, +0.53R, +101; 11-13 19:15 long at 159.723, stop 0.34% away, out 11-17 04:15 STOP, -1.06R, -203; 11-17 05:30 long at 159.161, stop 0.31% away, out 11-20 13:00 STOP, -1.06R, -200; 11-20 14:15 long at 158.770, stop 0.38% away, out 11-24 02:00 T1+STOP_BE, +0.54R, +99. Open at the end: LONG.
- Stop 3.0 (tested): 11-11 14:30 long at 159.620, stop 0.44% away, out 11-13 18:00 T1+STOP_BE, +0.35R, +51; 11-13 19:15 long at 159.723, stop 0.51% away, out 11-17 09:00 STOP, -1.04R, -151. Open at the end: LONG.
- Stop 4.0 (for comparison): 11-11 14:30 long at 159.620, stop 0.59% away, out 11-13 18:00 T1+STOP_BE, +0.26R, +58; 11-13 19:15 long at 159.723, stop 0.68% away, out 11-20 13:00 STOP, -1.03R, -228; 11-20 14:15 long at 158.770, stop 0.77% away, out 11-24 02:00 T1+STOP_BE, +0.27R, +58. Open at the end: LONG.

These are the replay's trades, not the live book's. The replay book arrives at 11 Nov with its own history.

## Limits

- One market, one history, three stop values. Earlier studies had already looked at this history (H90 looked at these stop distances on the first half, all markets pooled).
- No allowance was made for looking at two stop values. A pass would be weak evidence.
- Paper costs: 0.01% a side. No slippage. No financing cost on a leveraged position held for days.
- A stop is filled at its price, or at the bar's open if price gapped through it.
- Dollar totals on this market have moved by thousands between rebuilds of the readings store.
- The books compound: each trade risks 2% of what the book holds then. Dollar results late in the history depend on what came before; the percent columns do not.
