# H116: buying when BTC or ETH comes back to a capitulation low

**Verdict by the registered condition: no pass. Rule C1 ("the low holds") and rule C2 ("sweep and reclaim") both have
TOO FEW TRADES TO JUDGE, and on the trades there are, both lost a little after fees.** Nothing is proposed for a
forward paper book on the registered condition. Nothing in the engine, the books or the vault was changed.

Registered in `research/HYPOTHESES.md` (H116, commit `90ecef2`, 24 Nov 2026 12:54 UTC) before any number on history
was computed. History 2019-10-01 to 2025-11-10 23:45 UTC; the holdout from 2025-11-11 was not read (only the bars
around 21 Nov 2026 for the live case in section 5). Code `research/h116_retest_capitulation_low.py`, numbers in
`results.json`, the live case in `event.json`. A replay on history is post-mortem material, not validation.
(The registration's Part 1 is section 1 here, Part 2 is sections 2 and 3, Part 3 is section 4, Part 4 is section 5.)

## The question

The owner, 24 Nov 2026: if BTC comes back to 55k or 56k (the low of 21 Nov was 55,130), how can the engine take a
setup there, "earn the short and then turn long"? The rules being built in H115 buy the rebound from a NEW low. They
do not fire when price comes BACK to an old low and stays above it. This study looks at that case in history.

## Words used

- **Capitulation low:** the low that a panic sell-off bounced off. Exactly: the low behind H107's rule A trigger (a
  fresh 30-day low, at least 10% under the price a week earlier, then a rebound of twice the usual hourly range).
- **L, the level:** that low's price. It stays "live" for 30 days.
- **Retest:** price first bounces at least 5% above L, then comes back down to within 1.5% of L.
- **Holds / breaks:** the retest holds if price turns up again before any 15-minute bar closes below L. It breaks if a
  15-minute bar closes below L first.
- **Sweep:** price trades below L, even for a moment.
- **ATR(1h):** the average size of an hourly bar's range over the last 14 hours; the engine's unit for stops.
- **R:** a trade's result divided by what it risked (the distance from entry to stop), after fees. -1R is a full stop-out.
- **First half / second half:** before / from 8 June 2023.

## 1. What history says about a return to a capitulation low (base rates; descriptive)

BTC and ETH together: 187 triggers gave 130 separate levels (57 triggers repeated a low already counted). The 126 that
could be watched for their full 30 days before the cut:

| Of 126 capitulation lows | Count | Share |
|---|---|---|
| Undercut before price ever bounced 5% (the low was not the low) | 24 | 19% |
| Bounced 5% and never came back within 1.5% in 30 days | 25 | 20% |
| Bounced 5% and came back to within 1.5% (a retest) | 77 | 61% |

First half: 88 levels, 14 undercut, 16 never came back, 58 retested. Second half: 38 levels, 10 undercut, 9 never came
back, 19 retested.

| Of the 77 retests | All | First half | Second half |
|---|---|---|---|
| Held (turned up by one ATR before any 15-minute close below L) | 47 (61%) | 33 of 58 | 14 of 19 |
| ... of those, with a wick below L on the way | 13 | 8 | 5 |
| Broke (a 15-minute close below L came first) | 30 (39%) | 25 of 58 | 5 of 19 |
| ... of those, back above L within 24 hours | 26 | 23 | 3 |

"Held" is a weak word here. Counted with hindsight from the first touch of the zone:

| Within ... of the first touch | 24 hours | 48 hours | 96 hours |
|---|---|---|---|
| A 15-minute close below L, all 77 retests | 70% | 78% | 81% |
| The same, first half (58) | 72% | 83% | 86% |
| The same, second half (19) | 63% | 63% | 63% |
| The same, among the 47 that first "held" | 51% | 64% | 68% |

Price traded below L at some point in the 96 hours after the first touch in 88% of the retests (first half 91%,
second half 79%). The lowest point of those 96 hours was, at the median, 6.6% BELOW L (first half 8.7% below, second
half 1.8% below); the highest point was, at the median, 9.7% above L. So a return to the low was usually followed by
a move through the low AND a wide swing both ways.

**When the retest came:** a median of 21 hours after the low (a quarter within 7.5 hours, a quarter later than 4 days,
the longest 30 days). In the first half the median was 14 hours: many "retests" were the next leg of the same fall. In
the second half the median was 5 days. The bounce before the retest reached a median of 9% above L.

**What price did after the first touch** (from the close of the 15-minute bar that first touched the zone; median, and
the share of cases that were higher):

| | After 24 hours | After 48 hours | After 96 hours |
|---|---|---|---|
| All 77 retests | +1.9%, 58% | +1.3%, 56% | +0.9%, 53% |
| First half (58) | +1.4%, 57% | +0.2%, 52% | -0.5%, 47% |
| Second half (19) | +2.9%, 63% | +4.1%, 68% | +4.6%, 74% |
| Those that held (47; known only afterwards) | +2.4%, 68% | +1.7%, 62% | +2.0%, 55% |
| Those that broke (30; known only afterwards) | -4.3%, 43% | -1.8%, 47% | -0.2%, 50% |

The middle half of the 24-hour outcomes runs from -4.6% to +4.8%: close to a coin flip with a wide spread. By year,
2022 holds 47 of the 126 levels and 33 of the 77 retests (17 held, 16 broke).

## 2. The two rules, exactly as tested

Both use the same level and the same retest. All bars are 15-minute bars, UTC; every step uses closed bars only.

**The level.** When H107's rule A fires at the close of bar k, L = the lowest low of the 16 bars ending at k (bars
k-15 to k); b = the first of those bars with that low. If the coin already has a level at the same price made in the
last 30 days, no new level is made. The level can be touched and can give a signal only at bars that open at most 30
days after bar k opened.
1. Dead: if any bar after b has a low below L before, or in the same bar as, step 2.
2. Armed: the first bar after b whose high is at least 1.05 x L (it may be before k).
3. First touch: the first bar after both the arming bar and bar k whose low is at or below 1.015 x L.
4. From the first-touch bar f on, bar by bar: m = the lowest low of bars f to the current bar; s = the first bar from
   f on whose low is below L.

**C1, "holds the low".** If a bar from f on closes below L before C1 has signalled, C1 is off for this level.
Otherwise C1 signals at the close of the first bar j whose close is at least m + 1.0 x ATR(1h) at j. Stop = the lower
of L and m, minus 0.5 x ATR(1h) at j.

**C2, "sweep and reclaim".** If C1 signalled in a bar before s (before any low under L), C2 is off for this level.
Otherwise C2 signals at the close of the first bar j, from bar s to bar s+95 (24 hours, the sweep's first bar
included), whose close is above L. Stop = the lowest low of bars s to j, minus 0.5 x ATR(1h) at j.

**Both.** ATR(1h) = Wilder ATR(14) of 1-hour bars, the last 1-hour bar closed by the 15-minute bar's close; a signal
needs it finite and above zero. One signal per level per rule. The two rules are separate books and may both trade
the same retest.

**The trade (both).** Buy at the open of bar j+1 (not taken if that open is at or below the stop). R = entry minus
stop. Target 1 = entry + 1R: half is sold there and the stop on the rest moves to the entry from the next bar. Target
2 = entry + 2R: the rest is sold there (also possible in the Target 1 bar). Whatever is left is sold at the close of
bar j+192 (48 hours). Inside a bar the stop is checked first (a low at or below the stop fills at the stop, or at the
open if the bar opens below it). Fees 0.10% of notional a side. One open trade at a time per rule and coin: a signal
whose bar is before the previous trade's exit bar is skipped, and its level is used up for that rule.

The numbers in these rules (1.5%, 5%, 30 days, 1 ATR, 0.5 ATR, 24 hours) were chosen after looking at ONE event
(21-24 Nov 2026), before any count on history. They are not fitted and not known to be good.

## 3. The test (R after fees; 95% range from resampling whole calendar months; p = the chance of a mean this high if the true mean were zero)

Pass needs: 60 trades and 20 in each half; mean R above zero in each half; pooled mean R above zero with p below 0.05
after correcting for two rules.

| Rule | Part | Trades | Won | Mean R | Sum R | 95% range | p |
|---|---|---|---|---|---|---|---|
| C1 | all, BTC + ETH | 48 | 40% | -0.178 | -8.5 | -0.513 to +0.203 | 0.84 (corrected 1.0) |
| C1 | first half | 31 | 29% | -0.431 | -13.4 | -0.756 to -0.053 | 0.995 |
| C1 | second half | 17 | 59% | +0.285 | +4.8 | -0.411 to +0.902 | 0.18 |
| C1 | BTC, all | 26 | 46% | -0.108 | -2.8 | -0.523 to +0.336 | 0.70 |
| C1 | ETH, all | 22 | 32% | -0.260 | -5.7 | -0.835 to +0.315 | 0.78 |
| C2 | all, BTC + ETH | 37 | 49% | -0.113 | -4.2 | -0.520 to +0.331 | 0.71 (corrected 1.0) |
| C2 | first half | 29 | 48% | -0.112 | -3.2 | -0.576 to +0.430 | 0.68 |
| C2 | second half | 8 | 50% | -0.116 | -0.9 | -1.106 to +0.874 | 0.59 |
| C2 | BTC, all | 17 | 41% | -0.222 | -3.8 | -0.741 to +0.379 | 0.80 |
| C2 | ETH, all | 20 | 55% | -0.020 | -0.4 | -0.517 to +0.499 | 0.53 |

- **C1:** 48 trades against 60 needed, 17 in the second half against 20: too few to judge. Beyond that, the mean is
  below zero overall and in the first half (where the whole range is below zero); only the second half is above zero.
  27 of 48 trades hit the stop. Longest losing run 13; deepest fall of the running total -16.6R. By year (trades, sum
  of R): 2019 3, -3.2; 2020 4, -3.8; 2021 6, +3.3; 2022 16, -11.5; 2023 4, +2.1; 2024 7, +2.5; 2025 8, +2.1.
- **C2:** 37 trades, 8 in the second half: too few to judge. The mean is below zero overall and in both halves. 18 of
  37 hit the stop. By year: 2020 3, -2.4; 2021 9, +3.2; 2022 17, -4.0; 2024 4, -0.4; 2025 4, -0.5.
- **Fees are not the problem here.** The median stop is 3.7% of price (C1) and 3.5% (C2), so the 0.20% round trip costs
  about 0.05R to 0.06R a trade. The trades lose because the low gives way, not because of costs. (This is where H116
  differs from the retired liquidation-hunt book, whose stops were about 0.2% of price.)
- Against a plain 48-hour buy at every bar of the same coin and month, C1's trades were +0.4 percentage points better
  and C2's +1.5: these were falling months in which most longs lost. Better than random is not the same as profitable.
- Signals not taken: one per coin per rule, because that rule's earlier trade was still open.
- **Checks:** the levels and signals recomputed on data cut off at each signal bar and at 80 random bars (164 bars):
  0 differences. The trade walk equals a bar-by-bar walk on every trade, and equals H107's own walk when given H107's
  stop. H107's rule A re-run on this copy of the data gives H107's result (123 trades, -0.7R).

**Moving one number at a time (descriptive; decides nothing).** C1's first half stayed below zero in all 10 variants
that change it (-0.05R to -0.50R a trade) and its second half stayed above zero in all of them (+0.07R to +0.64R).
Overall C1 ranged from -0.29R (first bounce 8%, 34 trades) to +0.20R (waiting for a 2 x ATR turn, 29 trades); a zone
of 2.5% gave 62 trades at +0.02R. C2 ranged from -0.19R to +0.07R overall with mixed signs in both halves. Picking
the best of these afterwards would be fitting to the past. (Changing C1's turn also changes C2's trades, because the
first retest ends when C1 turns.)

**Not registered, added after the run (small cells; not a basis for a rule).** Split by how long after the low the
first touch came: under 24 hours, 41 retests, C1 23 trades -0.30R, C2 16 trades -0.29R; 24 hours to 7 days, 21
retests, C1 14 trades +0.15R, C2 12 trades +0.27R; over 7 days, 15 retests, C1 11 trades -0.35R, C2 9 trades -0.32R.
No steady pattern: the quick retests lost, the middle group gained, the late ones lost again.

## 4. "Earn the short and then turn long" (arithmetic on prices, NOT a book)

What the Setups book actually held at these moments was not read (that needs the evidence store, which this study
may not load). These are plain price facts around each C1 and C2 trade.

| At the median | C1's 48 trades | C2's 37 trades |
|---|---|---|
| Fall from the bounce high to the top of the retest zone | 7.1% | 7.9% |
| A short sold at the exact bounce high, bought back at the zone top, after 0.20% fees | +6.9% | +7.7% |
| A short sold halfway down, bought back at the zone top, after fees | +3.5% | +3.9% |
| A short kept past the zone top until the long's entry | gave back 1.3% | added 0.9% |
| The long from there (net) | -2.5% (mean -0.9%), 40% won | -1.3% (mean -0.3%), 49% won |

Read this with care. The fall into the zone is at least 3.3% BY DEFINITION (a retest only exists if price first rose
5% above L and then fell to 1.5% above it), and the bounce high is known only afterwards: nobody sells the exact high.
So the short's numbers say how big the move was, not that a rule could have earned it. What the table does show is
that in history the down leg into the zone was the larger part, and the long that followed lost on average. And
since price went below L in 88% of the retests, a short covered AT the zone was usually covered early.

## 5. The live case: what C1 and C2 would need to see now (no result computed)

Read from the bars up to the 15-minute bar opening 24 Nov 2026 04:30 UTC (BTC 60,537.51, ETH 1,703.85). Rule A fired
on both coins at the 06:45 UTC close on 21 Nov. Both levels are **armed and not yet touched**. Both are live until
the 15-minute close at **21 Dec 2026 06:45 UTC**.

| | BTC | ETH |
|---|---|---|
| L (the low) | 55,130.00 (21 Nov 06:15 UTC bar) | 1,538.00 (21 Nov 04:00 UTC bar) |
| Armed by a high at or above | 57,886.50 (reached; high so far 64,603.12) | 1,614.90 (reached; high so far 1,845.07) |
| Lowest price since the trigger | 57,093.77 | 1,612.91 |
| Retest zone: a 15-minute low at or below | **55,956.95** | **1,561.07** |
| ATR(1h) at the last bar read | 713.08 | 22.89 |

**C1 needs:** after the first touch of the zone, no 15-minute close below L, and a 15-minute close at least one ATR(1h)
above the lowest low made since the first touch. Stop = the lower of L and that lowest low, minus half an ATR(1h).
**C2 needs:** a 15-minute low below L, then within 24 hours (that bar and the next 95) a 15-minute close above L.
Stop = the lowest low of the sweep minus half an ATR(1h).

Example fills at the ATR of the last bar read (the ATR on the day will differ; in a sell-off it is usually larger,
and in history the median stop was about 3.7% of price):

| Example | Signal needs a 15m close | Entry about | Stop | R (% of entry) | Target 1 | Target 2 |
|---|---|---|---|---|---|---|
| BTC C1, retest low exactly at the zone top (55,956.95) | at or above 56,670.03 | 56,670 | 54,773.46 | 1,896.56 (3.3%) | 58,566.59 | 60,463.15 |
| BTC C1, retest low exactly at L (55,130) | at or above 55,843.08 | 55,843 | 54,773.46 | 1,069.61 (1.9%) | 56,912.69 | 57,982.30 |
| BTC C2, sweep to 54,578.70 (1% under L), reclaim | above 55,130.00 | 55,130 | 54,222.16 | 907.84 (1.6%) | 56,037.84 | 56,945.68 |
| ETH C1, retest low exactly at the zone top (1,561.07) | at or above 1,583.96 | 1,583.96 | 1,526.55 | 57.41 (3.6%) | 1,641.37 | 1,698.78 |
| ETH C1, retest low exactly at L (1,538) | at or above 1,560.89 | 1,560.89 | 1,526.55 | 34.34 (2.2%) | 1,595.23 | 1,629.57 |
| ETH C2, sweep to 1,522.62 (1% under L), reclaim | above 1,538.00 | 1,538 | 1,511.17 | 26.83 (1.7%) | 1,564.83 | 1,591.65 |

If a new, lower capitulation low forms on the way (rule A fires again under 55,130 / 1,538), that low becomes its own
level; the old one stays in its own retest.

## Reading

- A capitulation low was revisited within 30 days in about 6 cases of 10. When it was, price usually did not stop at
  the low: within four days it had traded under the low in about 9 revisits of 10 and closed a 15-minute bar under it
  in 8 of 10, with a median deepest point 6.6% below. A first reaction up was common (58% higher a day later) but small
  and unreliable.
- Buying the retest, in either form tested, did not make money over 2019-2025: C1 -0.18R a trade (48 trades), C2
  -0.11R (37). There are too few trades to judge by the registered bar, and the result is not close to passing.
- The two halves disagree, as they did in H107: lows kept failing in 2019-2022 (2022 above all), and C1 was positive
  on 17 trades since mid-2023. Seventeen trades cannot carry a conclusion, and the last year (the holdout) was not
  read.
- For the owner's plan: history gives no support for covering a short AT 55-56k and buying there in the expectation
  that the low holds. On these numbers the level was more often a place price passed through than a floor. If BTC
  does revisit the zone, C1 and C2 above say exactly what a paper long would wait for, and it would be a data point,
  not a tested edge.
- By the registered condition nothing is proposed. Whether to run C1 and C2 forward on paper anyway, to collect data
  points beside rules A and B (H115), is the owner's call; the rules in section 2 are written so they can be ported
  as they stand.

## Limits and what was not verified

- Small samples: 48 and 37 trades, months of 2022 dominate; every interval is wide.
- The window is not blind: H107 already showed which years' capitulation lows failed, and the first half overlaps
  H70's discovery period.
- The holdout year (2025-11-11 to 2026-11-18) was not read, so how the rules did in the most recent year is unknown.
- Fills are at the next bar's open with no slippage; inside a bar the stop is assumed to come first; funding is not
  charged. In a capitulation real fills can be worse.
- Section 4 is the short's arithmetic, not what any book held; the Setups book's own trades at these moments were not
  read.
- The live example prices use the ATR of 24 Nov 04:30 UTC; the data copy ends there, about 8 hours before this run.
- Only the H116 tests were run (10 pass); the full test suite was not run, since no engine code was touched.

## Deviations from the registration

1. The heading says "about 13:00 UTC"; the registration was committed at 12:54 UTC (`90ecef2`), before the script
   existed.
2. Added after the first run and marked "not registered": the split by time from the low to the first touch. The run
   was repeated with it; every registered number was identical (the two result files were compared).
3. The bar files are a later copy than H107 used (different md5, more recent bars); inside the cut they reproduce
   H107's rule A result exactly.
4. No other change: the rules, the pass condition, the statistics and the guards ran as registered.
