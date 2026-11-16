# Hypothesis register

Every idea the engine or the owner wants tested is written here BEFORE it is graded: what it
says, the evidence that prompted it, the exact rule, and how it will be graded forward. A
hypothesis is graded on what happens after its date, never on the history that suggested it.
Rows are added, not rewritten; a verdict is a new line.

Count of ideas tried so far in this project: 5 hypotheses (H1 to H5) plus H6-H10, with 29 (H6/H7, docs/PLAYBOOK.md) 130 (H8-H10, docs/PLAYBOOK2.md) 83 (H11-H17, docs/PLAYBOOK3.md) 48 (H18-H19, docs/INTRADAY.md) variants tried before registering, plus 1,838 (H20-H24, research/harness: 919 per coin, BTC and ETH) registered first and then run walk-forward, plus 64 (H25-H31, round 2) and 8 (H32-H35, round 3) the same way. Plus 15 exit variants (H36, moving-average trails and break-even, registered before any result). The fills study behind H3 tried
about 40 fill settings on history before H3 was chosen; count those too when judging it. Keep this count honest: the more
ideas tried, the more likely one looks good by luck.

---

## H1. CPI follow-through (registered 10 Nov 2026, 14:10 UTC)

**Prompted by:** the US CPI print of 10 Nov 2026, 13:30 UTC. In that one 15-minute bar BTC
ranged from 74,770 to 73,525 and closed down 0.7%; ETH ranged from 2,109 to 2,028 and closed
down 1.4%. The engine had gone long BTC 15 minutes earlier and lost 0.86% on it. Owner:
"Formulate a potential strategy so next time this can be a potential profitable trade setup."

**What the history on file says** (`research/event_study.py`; the calendar on disk starts
May 2026, so this is 6 CPI releases, 12 coin-rows, and BTC and ETH move together, so about 6
independent cases):

| After the release bar closes | Mean move in the direction of the release bar | Still ahead |
|---|---|---|
| 1 hour | +0.65% | 10 of 12 |
| 4 hours | +1.15% | 11 of 12 |
| 24 hours | +1.54% | 10 of 12 |

The release bar itself moved 0.81% on average and ranged about 5 times a normal 15-minute bar.
Jobs reports (12 rows) and Fed decisions (8 rows) did not show the same thing at 1 hour
(58% and 38% still ahead) and are NOT part of this hypothesis.

**The rule (shadow only, paper):**
1. At a US CPI release, do nothing during the release bar.
2. When the release bar closes, take the side of its close (down bar: short; up bar: long)
   at the next 15-minute open, but only if the bar moved at least 0.3% open to close.
3. Stop: beyond the release bar's far extreme (its high for a short, its low for a long).
4. Exit at the open 4 hours (16 sessions) after entry, or at the stop.
5. One fee of 0.10% a side is charged.

**Graded forward on:** every CPI release from 10 Nov 2026 on, both coins. The first case is
already running and its outcome was not known when this was written: short BTC from the
13:45 UTC open (about 73,898) and short ETH (about 2,069.40), to be read at 17:45 UTC.

**Verdict rule, fixed now:** after 6 forward releases (about six months), the setup stays
only if at least 8 of the 12 coin-rows are profitable after fees AND the mean result is above
+0.4% per trade. Fewer, or a mean under +0.4%: retire it and write why.

**Why it may be nothing:** 6 cases from one half-year; three release kinds and three horizons
were looked at before choosing this one; a stop beyond a 5x-normal bar is far away, so one
loss costs several wins.

---

## H2. Stand down before a scheduled release (registered 10 Nov 2026, 14:10 UTC)

**Prompted by:** the same print. The engine opened a new long 15 minutes before a release
whose bar then ranged 5 times normal.

**The rule (shadow only):** in the 4 sessions (1 hour) before a US High-impact release on the
calendar, open no NEW position and do not flip; use the mandate's idle allowance if flat. A
position already open is kept. Re-enter by the normal rules after the release bar closes.

**Graded forward on:** every High-impact USD release from 10 Nov 2026 on. For each, compare
the paper result of the engine as it traded with what it would have been under this rule,
over the window from 1 hour before to 1 hour after the release.

**Verdict rule, fixed now:** after 12 forward releases, adopt it if the rule's version is
ahead in total by more than the fees it saves or costs, and not behind in more than 7 of the
12. Otherwise drop it.

**Why it may be nothing:** one anecdote. Standing down also forfeits the cases where the
engine was already on the right side.

---

## H3. Limit order on flip exits (charter task E; registered 11 Nov 2026)

**Prompted by:** `research/fills.py` (`docs/FILLS.md`), which re-filled the v3 replay's 517 trades
under about 40 fill policies, 2020 to Nov 2026. Dropping trades whose limit order does not fill
lost money (the book lives on a few big winners, and limits miss some of them). Chasing with a
market order after a limit entry helped only in the first half. The one policy positive in both
halves on both coins: a limit order on flip exits, with a market order as the fallback.

| Flip exit, limit at next open + 0.25 x ATR(15m), 4 bars, then market | BTC | ETH |
|---|---|---|
| Change in P&L vs market exit, 2020 to Jun 2023 | +$528 | +$799 |
| Change in P&L vs market exit, Jun 2023 to Nov 2026 | +$87 | +$212 |
| Coin-years better | 10 of 14 together | |

**The rule (shadow only):** on a flip or decision exit (never a stop), place a limit to close
at the next open plus 0.25 x ATR(14, 15m) in the position's favour, ATR taken at the decision
bar. It rests 4 bars with the protective stop still live, then closes at market at the next open.
Entries and stops stay at market.

**Graded forward on:** every flip from 11 Nov 2026 on, all assets.

**Verdict rule, fixed now:** after at least 50 forward flips, adopt it if the total is ahead of
market exits after fees and no worse in more than 60% of flips. Otherwise drop it.

**Why it may be nothing:** chosen after seeing the grid (in-sample); 148 flips in all;
"traded through" stands in for queue position; no partial fills; the second-half gain is small.
Separately, the study found the fee schedule matters more than the order type: 0.075% (spot
with the BNB discount) instead of 0.10% added about $1,400 (BTC) and $1,200 (ETH) over the replay.

---

## H4. Higher-timeframe bias (engine v5; registered 11 Nov 2026)

**Prompted by:** the owner's post-mortem of BTC on 10 Nov 2026. ETH was short and right. BTC
went long twice: at 13:15 UTC (a 6.1-pt edge, mostly the economic-calendar voice, 15 minutes
before the CPI print; -$85.81) and at 14:45 (forced by the mandate on a 0.3-pt edge; stopped
at 16:30, -$213.88). At both, BTC was below its 1h, 4h and daily EMA20/50/200 and every
timeframe from 1h to daily scored down (1h -1.00, 4h -0.93, 1d -0.64). Owner: "The engine
should have higher timeframe understanding and realise price is all fall below the moving
average and it act as resistance. The bias should go for short rather than long." Both trades
were placed by v3 code; v4's trend tie-break (live from 15:30 UTC) would already have made the
14:45 forced entry a short.

**The rule (live in the main books from v5):** bias = SHORT when the 1h, 4h and daily trend
scores are all at or below -0.5 AND price is below the 1h EMA50, the 4h EMA20 and the 4h EMA50
(LONG: the mirror). With a bias: a forced entry takes the bias side; an entry against it needs
a 15-pt edge instead of 5; a position against it with less than a 5-pt edge for it is flipped
to the bias side. H2 (no new position or flip in the hour before a high-impact US release) went
live at the same time.

**History before adoption (BTC and ETH, 2019 to Nov 2026, 24h triple barrier):** in the short-
bias state the next 1.5-ATR move went down first 53.4% / 49.2% (BTC, first / second half) and
52.8% / 49.0% (ETH); in the long-bias state up first 51.9% / 52.0% and 51.6% / 50.1%. So the
state alone is about a coin flip at this horizon: adopted on the owner's call as a risk rule
(do not fight every timeframe at once), not as a proven edge.

**Graded forward on:** every session from 11 Nov 2026 with a bias, all six markets: hit rate of
the bias side, and the P&L of trades opened or flipped by the bias rule against what v4 would
have done (a v4 shadow book to be built).

**Verdict rule, fixed now:** after 30 days, keep it if the bias side was right in more than 52%
of graded bias sessions AND bias-rule trades are not behind v4's in total after fees. Otherwise
loosen it (bias only as the forced-entry tie-break) and write why.

**Why it may be nothing:** the history above; trends end, and a rule that flips into the trend
late can sell the low.

---

## H5. Damp the slow daily voices when the 1h and 4h structure turns (registered 11 Nov 2026)

**Prompted by:** the metals engine's week. Over the 30 days to 11 Nov it called UP only 5-10%
of the time and was right 59-60% (gold -4%, silver -14%). In the last 7 days gold rose 2.4% and
silver 6.0%; it stayed bearish (UP calls 5-23%) and was right 38%. The heaviest voice was "The
library's working strategies" (daily Donchian, 30-day momentum, 120-day SMA ...: 27% of the
trust, leaning short) - slow by design, and still trusted from the decline. Over 120 days the
engine was right 51-53%: a slow trend-follower that misses the turns, which is the opposite of
what a 15-minute engine is for (charter).

**The rule (shadow only, not yet built):** when the 1h AND 4h market structure (`ms_1h`,
`ms_4h` of the Market structure card: higher high and higher low, or the mirror) both point
against the "strategies" voice's lean, halve that voice's trust share for the session (the
freed share goes to the other voting voices pro rata).

**Graded forward on:** every session from registration, all six markets, as an odds variant:
hit rate and claimed-edge hit rate against the main odds, and the P&L of a book trading it.

**Verdict rule, fixed now:** after 30 days, adopt it if its hit rate on claimed-edge calls is
at least 2 points above the main odds' over the same sessions in at least 4 of the 6 markets.

**Why it may be nothing:** structure flips on 1h/4h are frequent; in a strong trend each
pullback flips them and the rule would weaken the voice that was right.

---

## H6. Liquidation hunt: fade a stop-run through a liquidity pool (registered 11 Nov 2026)

**Prompted by:** the owner, 11 Nov 2026: "include strategy to profit from liquidation hunt."

**What the history on file says** (`research/playbook_study.py`, 2020 to Nov 2026, six markets, split
at 7 Jun 2023; 11 P1 variants tried, 29 across H6 and H7): no variant cleared costs in the first
half. The chosen one lost in both halves on every market: -0.17% to -0.22% a trade on crypto,
-0.02% to -0.08% elsewhere, profit factor 0.40 to 0.73. Before costs it is about zero.

**The rule (shadow only, paper):** a bar trades through a pool (last confirmed 15m swing, 24h or 7-day
high/low, prior-day high/low, round number) that was beyond the prior close. Price reaches at least
0.25 x ATR(14, 15m) past it and closes back inside on the same bar or within 2 bars. The
sweep-to-reclaim candle's wick on the swept side is at least 50% of its range. On BTC/ETH, funding
must also be in the extreme fifth of its last 90 settlements against the swept side. Fade it at the next
open. Stop: the extreme + 0.1 ATR. Half at 1R, rest at 2R, stop to entry after 1R. Exit at the
next open after 16 bars. $10,000 a trade at the asset's own fee.

**Graded forward on:** every trade from 11 Nov 2026, all six markets (`engine15/playbook.py`, book `p1_liqhunt`).

**Verdict rule, fixed now:** after 200 forward trades or 30 days, whichever is later, keep it only if
the total is positive after fees AND at least 4 of 6 markets are positive; otherwise retire it and
write why. Separately, once 90 days of open-interest history exist, test whether an open-interest
drop in the sweep bar (the `lq_*` proxy) separates winners from losers, as a new hypothesis.

**Why it may be nothing:** it lost money on history in both halves. Stops of 0.2% to 0.4% make costs
0.5R to 0.7R a trade on crypto. The pools are everywhere (37 to 131 trades a month).

#

---

## H7. Breakout trap: trade a failed prior-day breakout with the higher-timeframe bias (registered 11 Nov 2026)

**Prompted by:** the owner, 11 Nov 2026: "Also, breakout trap"; the failed-breakout setup graded best
of six in `research/setup_stats.py` (BTC 53.1% / 52.2%).

**What the history on file says:** 18 P2 variants tried. The best unfiltered base (prior-day level,
back inside within 2 bars, 1R/2R) lost in the first half (-0.06% a trade, mean over markets). The
bias filter turned the score positive (+0.09%) on only 115 first-half trades. In the second half
(about 110 trades) it won on silver (+0.10%, PF 1.79) and lost on gold, USDJPY and the S&P. BTC/ETH
had 9 trades in 7 years.

**The rule (shadow only, paper):** a first close beyond the prior UTC day's high (low) is followed within
2 bars by a close back inside. Trade only when the engine's v5 higher-timeframe bias is on the
trade's side. Enter at the next open, against the breakout. Stop: the breakout extreme + 0.1 ATR. Half
at 1R, rest at 2R, stop to entry after 1R. Exit at the next open after 24 bars.

**Graded forward on:** every trade from 11 Nov 2026, all six markets (book `p2_trap`).

**Verdict rule, fixed now:** after 40 forward trades (expect about 3 a month across markets, so about a
year), keep it only if the total is positive after fees and the win rate is at least 50%;
otherwise retire it.

**Why it may be nothing:** chosen on 115 trades out of 18 variants; the unfiltered rule loses after
costs everywhere; almost no crypto trades.

---

## H8. Opening range breakout (registered 11 Nov 2026)

**Prompted by:** the owner's request for 15m strategy books (charter task K, batch 2). A classic
intraday rule, tried on every market's session open.

**What the history on file says** (`research/playbook2_study.py`, 2019 to Nov 2026, split 6 Dec
2022; 19 variants): no variant was positive after costs on average in either half. The registered
variant (below) had a mean avg R across markets of -0.074R in the first half and -0.151R in the
second, negative on all six markets in the second half. Before costs it was positive in the second
half on BTC, USDJPY and the S&P.

**The rule (shadow only, paper):**
1. Session opens: S&P cash 09:30 New York; London 08:00 for gold, silver, USDJPY; Tokyo 09:00 for
   USDJPY; the US equity open (NYSE days) and 00:00 UTC for BTC and ETH.
2. Opening range = the first 30 minutes' high and low.
3. The first 15m close outside the range, if it is in the direction of the engine's higher-timeframe
   bias (v5), is traded at the next open. No bias, or bias the other way: no trade that session.
4. Stop at the opposite side of the range; the stop must be at least 4 one-side fees away.
5. Target 2R. Exit by the session end (S&P 16:00 New York, else 8 hours after the open).
6. One trade at a time per market; $10,000; each market's own fee a side.

**Graded forward on:** every session from 11 Nov 2026, all six markets (about 35 trades a month).

**Verdict rule, fixed now:** after 100 forward trades (about three months), keep it only if the
average result is above +0.05R after costs, the profit factor is above 1.1, and at least 3 of the 6
markets are positive. Otherwise retire it and write why.

**Why it may be nothing:** history already says it does not pay its costs; 19 variants were tried;
the bias filter keeps only about one breakout in six and was chosen because it lost least.

---

---

## H9. S&P 500 overnight gap fill (registered 11 Nov 2026)

**Prompted by:** charter task K, batch 2; the overnight-futures card (`sources/overnight.py`) shows
the gap and its fill every morning.

**What the history on file says** (44 variants): the registered variant was the only one positive in
the first half (+0.020R after costs, 66 trades, 64% won) and lost -0.097R in the second (90 trades,
60% won). Before costs it was +0.21R and +0.14R: the edge, if any, is smaller than the 0.04% round
trip on a tight stop.

**The rule (shadow only, paper):**
1. At the S&P cash open, gap = today's open against yesterday's 16:00 close, in hourly ATRs (ATR(14)
   of the 1-hour chart known at the open). Only gaps of 0.25 to 1.00 ATRs.
2. At 10:00 New York, if the gap has not filled and the 10:00 close is back toward yesterday's close
   (below the open after a gap up, above it after a gap down), trade toward the fill at the next open.
3. Stop beyond the first 30 minutes' extreme (their high after a gap up, their low after a gap down).
4. Target yesterday's close. Exit at 16:00 (13:00 on half days) at the latest.
5. $10,000; 0.02% a side.

**Graded forward on:** every S&P session from 11 Nov 2026 (about 1.5 to 2 trades a month).

**Verdict rule, fixed now:** after 30 forward trades, keep it only if the average result is above
+0.05R after costs and at least 55% of trades won. Otherwise retire it. An interim look at the 10
Feb 2027 review decides nothing.

**Why it may be nothing:** best of 44 variants on 66 first-half trades; the second half lost; costs
take about 0.2R a trade.

---

---

## H10. Squeeze breakout (registered 11 Nov 2026)

**Prompted by:** charter task K, batch 2; the "Trend quality and squeeze" card (`sources/ltf.py`)
already reads the squeeze.

**What the history on file says** (67 variants): the registered variant's mean avg R across markets
was +0.001R in the first half and -0.040R in the second; only the S&P was positive in both halves
(about 40 trades each). 15-minute squeezes lost 0.09R to 0.15R in every variant.

**The rule (shadow only, paper):**
1. Squeeze = Bollinger(20, 2) inside Keltner(20, 1.5 x mean true range) on the 1-hour chart for at
   least 6 consecutive hourly bars.
2. When it releases (the hourly bar closes with the bands outside the channels), watch the next 8
   15m bars: the first close above the squeeze's high is a long, below its low a short, traded at the
   next open, if the decision bar opened between 08:00 London and 16:00 New York.
3. Stop at the squeeze range's opposite side (at least 4 one-side fees away).
4. Target 2R. Exit after 32 bars (8 hours), or at the close of the last bar before a market break.
5. One trade at a time per market; $10,000; each market's own fee a side.

**Graded forward on:** every release from 11 Nov 2026, all six markets (about 20 trades a month).

**Verdict rule, fixed now:** after 100 forward trades, keep it only if the average result is above
+0.05R after costs, the profit factor is above 1.1, and at least 3 of the 6 markets are positive.
Otherwise retire it.

**Why it may be nothing:** about zero in the first half and negative in the second; 67 variants; the
session filter was kept on a +0.002R difference.

---

## H11. VWAP reclaim with the higher-timeframe bias (registered 11 Nov 2026)

**Prompted by:** charter task K, batch 3 (VWAP reversion / reclaim); the intraday-levels card
(`sources/ltf.py`) already reads the daily VWAP and its bands.

**What the history on file says** (`research/playbook3_study.py`, 2019 to Nov 2026, split 6 Dec 2022; 20
variants): no variant positive after costs in either half. All 16 band-fade variants lost 0.25R to 0.50R
after costs and were negative before costs too. The registered reclaim lost -0.120R / -0.114R after costs
(first / second half, mean across markets), +0.023R / +0.042R before; negative after costs on every market
in both halves.

**The rule (shadow only, paper):**
1. Daily VWAP from 00:00 UTC (typical price, volume-weighted; equal weights for USDJPY).
2. With the engine's v5 bias LONG: the day's first 15m bar whose low reaches VWAP and whose close is back
   above it (the bar before also closed above), traded LONG at the next open. Mirror for SHORT.
3. Stop 1 hourly ATR beyond VWAP (at least 4 one-side fees away). Target 2R. Exit after 32 bars.
4. One trade at a time per market; $10,000; each market's own fee a side. All six markets.

**Graded forward on:** every trade from 11 Nov 2026 (about 55 a month).

**Verdict rule, fixed now:** after 100 forward trades, keep it only if the average result is above +0.05R
after costs, the profit factor is above 1.1, and at least 3 of the 6 markets are positive. Otherwise retire it.

**Why it may be nothing:** it lost after costs on every market in both halves; it lost least of 20.

---

---

## H12. Asian-range breakout at the London open, gold and USDJPY (registered 11 Nov 2026)

**Prompted by:** charter task K, batch 3 (session plays) and task D (trading sessions).

**What the history on file says** (12 variants over three plays): no play had a positive first half after
costs. The London false move lost about -0.33R after costs (negative before costs too); the New York
afternoon drift was +0.00R to +0.02R before costs and -0.05R to -0.16R after. The registered breakout:
-0.029R / -0.030R after costs (mean of gold and USDJPY), +0.049R / +0.034R before; USDJPY -0.000R / +0.006R.

**The rule (shadow only, paper):**
1. Asian range = the high and low of the bars from 00:00 UTC to the London open (08:00 London time).
2. The first 15m close above (below) it in the first 4 hours after the London open: LONG (SHORT) at the next open.
3. Stop at the opposite side of the Asian range (at least 4 one-side fees away). Target 3R.
4. Flat 8 hours after the London open. Gold and USDJPY; $10,000; each market's own fee.

**Graded forward on:** every London session from 11 Nov 2026 (about 26 trades a month).

**Verdict rule, fixed now:** after 100 forward trades, keep it only if the average result is above +0.05R
after costs and the profit factor is above 1.1, with both markets positive. Otherwise retire it.

**Why it may be nothing:** negative after costs overall in both halves; chosen as the least bad of three plays.

---

---

## H13. Fair value gap retest (registered 11 Nov 2026)

**Prompted by:** charter task K, batch 3 (fair value gap / order block).

**What the history on file says** (16 variants): none positive after costs in either half. Registered:
-0.166R / -0.199R after costs, +0.012R / -0.010R before. The order block was worse than the gap in every pairing.

**The rule (shadow only, paper):**
1. Bullish gap: candle 1's high below candle 3's low, candle 2 up, gap at least 1.0 x ATR(14, 15m) taken
   before the three candles (mirror for bearish).
2. The first bar within 12 hours that trades back into the gap, if its close is not beyond the gap's far
   edge: trade in the impulse direction at the next open.
3. Stop beyond the far edge + 0.25 hourly ATR. Half at the impulse extreme (1R if nearer than 0.5R), the
   rest at 2R or 1R past the extreme; stop to entry after the first half. Exit after 32 bars.
4. All six markets; $10,000; each market's own fee.

**Graded forward on:** every trade from 11 Nov 2026 (about 140 a month).

**Verdict rule, fixed now:** after 200 forward trades or 30 days, whichever is later, keep it only if the
average result is above +0.05R after costs, the profit factor is above 1.1, and at least 4 of 6 markets
are positive. Otherwise retire it.

**Why it may be nothing:** about zero before costs, -0.2R after, on thousands of trades.

---

---

## H14. Crypto liquidation cascade continuation (registered 11 Nov 2026)

**Prompted by:** charter task K, batch 3; the liquidation proxy of `sources/derivs.py` (whose open-interest
part has only 30 days of history).

**What the history on file says** (18 variants): continuation was positive after costs in the first half
in 8 of 9 variants and negative in the second half in all 9; positive before costs in both halves in all
9. Registered (with the funding filter): +0.061R / -0.061R after costs, +0.132R / +0.041R before. The
bounce lost in every variant.

**The rule (shadow only, paper):**
1. BTC and ETH. At a bar's close: price is at least 3 hourly ATRs (the ATR before the move) from the
   4-bar high (low), the 4 bars' volume is at least 1.5x the previous 24 hours' average, taker buying is
   at most 45% (at least 55%) of it, and the newest funding rate is at or below (above) its 30-day median.
   First bar of the cascade only.
2. Trade WITH the move at the next open; stop at the 4-bar extreme where the move began (at least 0.40% away).
3. Target 3R. Exit after 16 bars (4 hours). $10,000; 0.10% a side.

**Graded forward on:** every cascade from 11 Nov 2026 (about 8 a month).

**Verdict rule, fixed now:** after 40 forward trades (about five months), keep it only if the average
result is above +0.05R after costs and the profit factor is above 1.1. Otherwise retire it. Separately,
once 90 days of open-interest history exist, test whether a falling OI in the cascade separates winners
from losers, as a new hypothesis.

**Why it may be nothing:** the second half lost after costs; 18 variants; fills in a cascade would slip.

---

---

## H15. Round-number magnet (registered 11 Nov 2026)

**Prompted by:** charter task K, batch 3; the round-number pools of P1 (`playbook.py`).

**What the history on file says** (12 variants): no variant was positive even before costs on average.
Registered: -0.210R / -0.246R after costs, -0.016R / -0.026R before.

**The rule (shadow only, paper):**
1. Round numbers: BTC 1,000s, ETH 100s, gold 50s, silver 1s, USDJPY 0.50s, S&P 500 50s.
2. When the close first comes within 1 hourly ATR of the nearest one (not touched in the last 4 hours),
   trade toward it at the next open. Target the number; stop the same distance behind the entry (1R; at
   least 4 one-side fees away). Exit after 16 bars.
3. All six markets; $10,000; each market's own fee.

**Graded forward on:** every trade from 11 Nov 2026 (about 260 a month).

**Verdict rule, fixed now:** after 200 forward trades or 30 days, whichever is later, keep it only if the
average result is above +0.05R after costs and at least 4 of 6 markets are positive. Otherwise retire it.

**Why it may be nothing:** no edge even before costs on history; runs mainly as the control it already is.

---

---

## H16. Release-day follow-through beyond CPI (registered 11 Nov 2026)

**Prompted by:** charter task C (release days: FOMC, payrolls) and H1.

**What the history on file says** (4 variants): the calendar on file starts in May 2026, so about 28
release-rows in all (2 to 10 per market), all in-sample. Follow (1-ATR bar) +0.50R after costs a row,
fade -0.53R. FOMC rows won 11 of 12; payrolls 2 of 16. `research/event_study.py`
earlier found jobs and Fed releases did not follow through at 1 hour on BTC/ETH (58% / 38%): the two
views differ on the same few cases.

**The rule (shadow only, paper):**
1. Releases: every US high-impact release on `data/econ_events.csv` except CPI (H1): FOMC, payrolls, PPI, ...
2. Do nothing during the release bar. If it moved at least 1 hourly ATR open to close, take the side of its
   close at the next open.
3. Stop beyond its far extreme (at least 4 one-side fees away). Exit after 16 bars (4 hours).
4. Every market whose release bar exists (the S&P cash market sees FOMC only); $10,000; each market's own fee.

**Graded forward on:** every release from 11 Nov 2026 (about 3 releases a month).

**Verdict rule, fixed now:** after 12 forward releases (about four months), keep it only if at least half
of the release-rows are profitable after fees AND the mean result is above +0.2R. Otherwise retire it.

**Why it may be nothing:** about 28 in-sample rows from six months; markets move together on a release,
so the independent cases are about 10; chosen after seeing them.

---

---

## H17. Crypto opening range at the US equity open (registered 11 Nov 2026; FORWARD ONLY)

**Prompted by:** the playbook2 study's session breakdown of H8 (`research/out/playbook2.md`): at the US
equity open the rule was positive after costs on BTC (+0.03R then +0.12R) and ETH (+0.03R then +0.07R).

**What the history on file says:** nothing usable as evidence: the lead was FOUND in this history, by
splitting H8's results by session (one of many breakdowns of 130 variants). Reproduced in
`research/playbook3_study.py` as "where it was found": BTC +0.032R / +0.115R, ETH +0.034R / +0.072R
after costs (first / second half).

**The rule (shadow only, paper):**
1. BTC and ETH, NYSE trading days. Opening range = the first 30 minutes from 09:30 New York (13:30 UTC in
   US summer time, 14:30 in winter).
2. The first 15m close outside the range, if in the direction of the engine's v5 higher-timeframe bias,
   is traded at the next open. No bias, or bias the other way: no trade that day.
3. Stop at the range's opposite side (at least 0.40% away). Target 2R. Flat 8 hours after the open.
4. $10,000; 0.10% a side. (Identical to H8 at this one session.)

**Graded forward on:** every US session from 11 Nov 2026 (about 5 to 6 trades a month). History is not counted.

**Verdict rule, fixed now (purely forward):** after 60 forward trades (about ten months), keep it only if
the forward average result is above +0.05R after costs, the forward profit factor is above 1.1, and both
coins are positive. Otherwise retire it.

**Why it may be nothing:** a subset picked out of a losing rule after the fact; ~140 trades a half per
coin; the same trades also run inside H8.

---

## H18. The 1h swing mind (registered 11 Nov 2026; FORWARD)

**Prompted by:** the owner's request to trade the lower timeframe as its own game, not as timing for the
4h/daily trend (workstream M).

**What the history on file says** (`research/out/intraday.md`): the 1h mind's direction is about 55% right
on BTC and ETH in both halves and about 50-53% elsewhere; its expected value after costs cleared 0.05 R on
0% of sessions on every market in both halves; no 1h variant traded often enough to choose one. Nothing
in history supports it after costs.

**The rule (shadow book `m_swing_1h`, paper, all eight markets):** the 1h mind (the voting cards trained on
4-bar, 0.75 x ATR(1h) grades, refitted weekly) prices both sides at every 15m close; enter at the next open
when EV = P(win) - P(loss) - round trip / risk >= 0.05 R; no entry in the hour before a high-impact US
release; stop at the last confirmed 15m swing (+0.1 barrier) when 0.5-1.5 barriers away, else 1 barrier;
target 1.5R; out at the open after 4 bars unless the same side still clears (then the clock restarts);
re-entry allowed; flat allowed (no mandate); size by `backtest.leverage`; the market's own fees.

**Graded forward on:** every trade from the first live step after the loop restarts. Expect very few.

**Verdict rule, fixed now:** after 60 forward trades (or on 10 Feb 2027 if fewer), keep it only if the
forward average after costs is above +0.05 R with a profit factor above 1.1. Too few trades by 10 Feb 2027
is itself the verdict: the 1h read does not clear costs often enough to trade.

**Why it may be nothing:** a 55% read worth about 0.04 R a call before costs, against 0.2-0.4 R of costs.

### H19. The 4h swing mind (registered 11 Nov 2026; FORWARD)

**Prompted by:** the same request.

**What the history on file says:** the 4h mind is about 50-52% right on direction everywhere; the variant
chosen on the first half (structure stop, 1R target, margin 0) made about 0 R a trade before costs and
lost 0.054 R / 0.064 R a trade after costs in the two halves (about 2,500 trades). History says it loses.

**The rule (shadow book `m_swing_4h`, paper, all eight markets):** as H18 with the 4h mind (16-bar,
1 x ATR(1h) grades), EV margin 0 R, stop at the last confirmed 1h swing (+0.1 barrier) when 0.5-1.5
barriers away, else 1 barrier; target 1R; out after 16 bars unless renewed.

**Graded forward on:** every trade from the restart (history suggests about one a day over all markets).

**Verdict rule, fixed now:** after 100 forward trades, keep it only if the forward average after costs is
above +0.05 R, the profit factor above 1.1, and it is positive on at least two market groups. Otherwise retire.

**Why it may be nothing:** it is the best of 24 on the history read and still lost; it runs to check that
the forward record agrees, and to give the owner a live, priced swing book next to the main book and the
4h/daily yardsticks.

---

## H19. The 4h swing mind (registered 11 Nov 2026; FORWARD)

**Prompted by:** the same request.

**What the history on file says:** the 4h mind is about 50-52% right on direction everywhere; the variant
chosen on the first half (structure stop, 1R target, margin 0) made about 0 R a trade before costs and
lost 0.054 R / 0.064 R a trade after costs in the two halves (about 2,500 trades). History says it loses.

**The rule (shadow book `m_swing_4h`, paper, all eight markets):** as H18 with the 4h mind (16-bar,
1 x ATR(1h) grades), EV margin 0 R, stop at the last confirmed 1h swing (+0.1 barrier) when 0.5-1.5
barriers away, else 1 barrier; target 1R; out after 16 bars unless renewed.

**Graded forward on:** every trade from the restart (history suggests about one a day over all markets).

**Verdict rule, fixed now:** after 100 forward trades, keep it only if the forward average after costs is
above +0.05 R, the profit factor above 1.1, and it is positive on at least two market groups. Otherwise retire.

**Why it may be nothing:** it is the best of 24 on the history read and still lost; it runs to check that
the forward record agrees, and to give the owner a live, priced swing book next to the main book and the
4h/daily yardsticks.

---

# Harness study, loop round 1 (registered 11 Nov 2026, 13:45 UTC, before any harness result was computed)

Code: `research/harness/` (`py -3 research/harness/run.py`). Paper research only. Owner's question: can a 15m
strategy that trades too often (RL Phase 2: ~600 trades a year, ~80% of equity a year in costs, no edge before costs)
be turned, by a filter or "harness", into one that trades far less AND beats buy-and-hold out of sample after costs?
Owner's loop target (see `research/harness/LOOP.md`): CAGR of the stitched out-of-sample equity >= 25% a year net of
0.10%-a-side fees and funding (10% CAGR kept as a milestone), 15m decision clock, max drawdown no worse than
buy-and-hold's over the same span, net return positive in more than half of the test folds, flags clear.

**Common frame for H20-H24 (fixed now).** BTCUSDT perpetual first (the RL Phase 2 bars and funding,
`data/rl/`), then ETHUSDT (engine spot 15m bars `data/ethusdt_15m.csv` + perp funding `data/ethusdt_funding.csv`)
under identical rules. Costs = `engine15.rl.costs` (fee 0.10% a side headline, 0.05% comparison, half-spread 0.5 bp,
slippage 0.10 x 96-bar per-bar vol at the decision, funding), decide at a bar's close, fill at the next open.
**Sealed holdout: 2025-11-11 00:00 UTC to 2026-11-11.** Nothing below looks at it. Development data end
2025-11-10 23:45 UTC. Walk-forward = RL Phase 1/2 folds cut at the seal: 12-month train, next 3 months test, roll 3
months, first train 2019-10-01; development out of sample = stitched test windows 2020-10-01 to 2025-11-11 (21 folds,
the last one 41 days). In each fold the variant with the highest net Sharpe (0.10%) on that fold's train window is
used on its test window; one backtest runs over the stitched series. The 0.05% line re-runs the same selections.
Benchmarks over the same span, same costs: buy-and-hold 1x, the frozen daily 30-day momentum rule (long/short),
random strategy with matched trade count (10 seeds: position changes at random bars, drawn from the strategy's own
position levels), RL Phase 2 agent for reference (its numbers are over the full span, holdout included).

**Thesis criteria (T), per graded strategy, development OOS, 0.10%:** (a) at most 100 position changes a year;
(b) Sharpe above buy-and-hold's AND Calmar above buy-and-hold's; (c) Sharpe above buy-and-hold's in at least half the
folds (else flag `fold_share`); (d) holds at 0.10%, not only at 0.05% (else flag `fee_only_at_0.05`); (e) Sharpe above
the matched-random mean. **Loop target (L):** CAGR >= 25% at 0.10%, max DD <= buy-and-hold's, net return positive in
> 50% of folds, plus flags clear: `fold_share`, `fee_only_at_0.05`, `high_turnover` (> 100 changes/yr),
`eth_fails` (same procedure on ETH has CAGR <= 0 or max DD worse than ETH buy-and-hold), `not_significant` (paired
block-bootstrap p-value of Sharpe minus buy-and-hold Sharpe, 20-day blocks, 2,000 draws, above 0.05 / number of graded
strategies: Bonferroni). A strategy meeting L with flags clear is a development pass and may get ONE look at the
holdout, frozen as registered (the selection procedure continues quarterly into the holdout on trailing 12 months).

## H20. Filter stack on frequent 15m base signals (family 1, walk-forward selected)

Bases (score z at each 15m close): `mom` z = 16-bar log return / (96-bar per-bar vol x 4); `ema` z = (EMA20 - EMA50)
/ (close x 96-bar vol x 4); `mr` z = -(close - SMA48) / std48. Raw side: long when z > e, short when z < -e, back to
flat when z crosses 0 (mom/ema e in {0, 1}; mr e in {2, 2.5}: the confidence filter). Filters: trend T in {none, 4h,
1d, both} (4h: sign of last closed 4h close minus 4h EMA50, via `engine15.data.htf_on_15`; 1d: the frozen daily 30-day
momentum sign; a side against the trend is flat); cost gate k in {0, 1.5, 2.5}: a new entry only if expected 1-hour
move (96-bar vol x 2) >= k x round trip (2 x (0.10% + 0.5 bp + 0.10 x vol)); session S in {all, active}: entries only
on bars closing 12:00-21:00 UTC; minimum hold H in {1, 16, 96} bars for every change; cooldown CD in {0, 96} bars of no
entry after a trade closed at a loss (decision-close prices). 3 bases x 2 x 4 x 3 x 2 x 3 x 2 = 864 variants.
Graded on T and L. Prior: a no-edge base filtered at best saves fees and ends near flat; expected FAIL.

## H21. The filter ladder: trade count vs net return (family 1, fixed, no fitting)

For each base, fixed levels: L0 base alone (e = 0 / 0 / 2, H = 1); L1 + H = 16; L2 H = 96 instead; L3 + T = 1d;
L4 + confidence (e = 1 / 1 / 2.5); L5 + k = 1.5; L6 + S = active; L7 + CD = 96. 24 fixed strategies, run once on the
development OOS. Reported as a trade-count vs net-return curve. The thesis holds for "filters on a no-edge base"
only if some level meets T(a, b, c, e). Prior: net return rises as trades fall, no level beats buy-and-hold.

## H22. Meta-labeling harness on the frozen daily momentum (family 2, walk-forward selected)

Direction = the frozen daily 30-day momentum sign (decided at the 00:00 UTC close). Short size in {0, 0.5, 1}.
Size rule R: R0 size 1; R1 at each daily decision size 1 if the 672-bar realised vol is at or below its trailing
365-day median (daily decision bars) else 0.5; R2 size 1 if the last closed 4h trend (as H20) agrees with the
direction else 0.5; R3 as R2 but 0 when it disagrees. Entry timing E: E0 at the next open; E1 after a direction change
wait up to 24 bars for a 15m close beyond EMA20(15m) by 0.5 x ATR14 against the trend (below for a long), enter at the
next open, or at bar 24; E2 the same with 1.0 ATR and 48 bars (flat while waiting). 3 x 4 x 3 = 36 variants. Graded on
T and L. Prior: can match momentum with less drawdown; beating 25% CAGR is unlikely.

## H23. Core-satellite overlay (family 3, walk-forward selected)

Core 1x long; signal sig in {15m EMA20/50 sign, last closed 4h trend, daily 30-day momentum}; exposure = band high
when sig > 0, band low when sig < 0; bands {[0.5, 1.5], [0, 1.5], [0, 1]}; minimum hold H in {16, 96} bars between
exposure changes; fees on every tilt; above 1x the costs and returns scale linearly (backtest at exposure / 1.5,
then x 1.5). 3 x 3 x 2 = 18 variants. Graded on T and L.

## H24. Mind 15 replay trades filtered by daily momentum (family 4, descriptive, in-sample)

`out/replay/trades_*.csv` (10 Nov 2026 replay, 0.10% fees), trades entered before 2025-11-11 only. Keep a trade only
when its side equals the frozen daily momentum sign at entry. Pass if the kept subset's mean net result per trade is
above all trades' in both halves (split 2023-06-07) on both coins, and the kept subset's compounded result is positive
in both halves. The replay is warm-up material for an engine designed on this history: H24 cannot produce a
development pass or a holdout look, whatever it shows.

Variants in this round: 864 + 36 + 18 + 1 = 919 per asset (H21's 24 are inside H20's grid).

### Verdicts, loop round 1 (11 Nov 2026, ~13:55 UTC; development out of sample 2020-10-01 to 2025-11-11, 0.10% a side; `research/out/harness/harness_report.md`)

- **H20: FAIL.** BTC 141 trades/yr, CAGR -12.4%, Sharpe -0.18 (buy-and-hold +38.1%, 0.83); ETH -11.8%. Break-even fee 0.015% a side.
- **H21: FAIL.** Filtering cuts trades from ~4,500 to ~60-350 a year and costs with them, but no level beats buy-and-hold;
  best BTC level ema L4 (74 trades/yr, +5.1% CAGR, Sharpe 0.32). The frequent bases have gross Sharpe about 0.
- **H22: FAIL as a thesis test and not a development pass.** BTC +26.8% CAGR, Sharpe 0.81 vs 0.83, max DD 58% vs 79%, 46
  trades/yr; beats buy-and-hold risk-adjusted only at 0.05%. ETH +35.8%, Sharpe 0.88 vs 0.79. Meets the loop's CAGR,
  drawdown and positive-fold criteria on both coins; flags fired: fold_share (38% / 43%), not_significant (p 0.37 / 0.30),
  BTC fee_only_at_0.05.
- **H23: FAIL, not a development pass.** BTC +29.9% CAGR, Sharpe 0.74; ETH +41.6% with max DD 85% vs 82% (eth_fails).
- **H24: not met** (BTC second half: kept trades' mean +0.79% vs all +0.89%); in-sample only.
- No holdout look taken. Variants tried in round 1: 919 per asset, 1,838 in all.

---

# Harness loop, round 2 (registered 11 Nov 2026, 14:05 UTC, before any round-2 result was computed)

Code: `research/harness/round2.py` (`py -3 research/harness/round2.py`). Development data only (bars before
2025-11-11), same 21 walk-forward folds, costs and timing as round 1 (decide at a bar's close, fill at the next open).

**Development pass rules (owner, set before round 2; each per coin: BTC headline AND ETH under the same frozen rule):**
1. CAGR >= 25% net of 0.10%-a-side fees and funding.
2. CAGR strictly above buy-and-hold's over the same span.
3. Sharpe strictly above buy-and-hold's AND max drawdown no worse than buy-and-hold's.
4. Sharpe above buy-and-hold's in at least half the folds (`fold_share`).
5. Paired block-bootstrap test of Sharpe minus buy-and-hold Sharpe (daily returns, 20-day blocks, 2,000 draws; p from
   the bootstrap standard error, normal approximation, because resampling cannot resolve p < 1/2,000) at Bonferroni
   level 0.05 / (all variants tried in the loop so far, cumulative: 1,838 from round 1 + round 2's); deflated-Sharpe
   probability reported.
6. No `fee_only_at_0.05` (beats buy-and-hold risk-adjusted only at 0.05%), no `high_turnover` (> 100 changes a year).
Also kept from round 1: net return positive in more than half the folds; 15m decision clock.
**Which buy-and-hold (my choice, the stricter one):** rules 2-4 use **spot buy-and-hold** (1x long, one 0.10% fee, no
funding), which beats the perpetual buy-and-hold by the funding a long pays (~12% a year on BTC). The perpetual
buy-and-hold is shown beside it, with a column saying whether a candidate would pass against it; a pass counts only
against spot. Calendar-year returns of every candidate are shown next to buy-and-hold's.

Common pieces: d = the frozen daily 30-day momentum sign (decided at the 00:00 UTC close); rv = 672-bar per-bar
realised vol x sqrt(35,040) (annualised); "E2 pullback" = after a new direction (sign change of the wanted exposure)
wait up to 48 bars for a 15m close at or below EMA20 - 1.0 x ATR14 (long; mirror for short), flat while waiting, enter
at the next open, or at bar 48. Exposures above 1x pay costs and funding on the whole position (perp) unless stated.

## H25. Vol-targeted daily momentum, 15m re-sizing (walk-forward selected, 8 variants)
Wanted exposure = min(Lmax, vt / rv) when d > 0; -s x min(1, vt / rv) when d < 0. On the 15m clock the held exposure is
changed when the wanted sign differs from the held one (with the E2 pullback on a new direction) or when |wanted -
held| >= 0.25. Grid: s in {0, 0.5} x vt in {0.5, 0.8} x Lmax in {1.5, 2.0}; per fold the best train-window net Sharpe.

## H26. Momentum ensemble (3 fixed variants)
e = mean of sign(L-day return), L in {10, 20, 30, 60, 90} days, at the 00:00 UTC close. Variants: long/short e;
long-only max(e, 0); long-only 1.5 x max(e, 0). E2 pullback on a new direction; size changes otherwise at the next open.

## H27. Two-coin book (2 fixed books)
Half the equity in BTC, half in ETH, never rebalanced (two sub-books), each running (a) H28, (b) H25 as selected for
that coin. Graded as one book against the same half-and-half spot buy-and-hold book, by the rules above (no per-coin
requirement: the book holds both).

## H28. The most-chosen H22 variant as one fixed rule (1 variant)
Long-only; size 1x when the 672-bar vol is at or below its trailing 365-day median of daily readings, else 0.5x (set at
the 00:00 UTC close); E2 pullback entry after each new daily direction. No selection.

## H29. Spot execution of the long legs (14 variants)
The long part up to 1x held as spot (no funding); exposure above 1x and any short on the perp (funding charged on those
parts only). Applied to H25 (its own walk-forward selection over its 8 variants), H28, H30 (3) and H31 (2).

## H30. Leveraged trend core (3 fixed variants)
Exposure U when d > 0, D when d < 0: (U, D) in {(1.5, 0.5), (2.0, 0), (1.5, 0)}. On the 15m clock an increase in
exposure (or a new direction) waits for the E2 pullback (the lower exposure is kept while waiting); a decrease is done
at the next open.

## H31. Vol-targeted long-only momentum with a 15m trailing exit (2 fixed variants)
H25 with s = 0, vt = 0.6, Lmax = 2.0, plus: while long, if a 15m close falls below the highest close since entry minus
m x ATR14 of the last closed daily bars, go flat; re-enter only at a later 00:00 UTC decision with d > 0 (E2 pullback).
m in {2.5, 4.0}.

Variants in round 2: per coin 8 + 3 + 1 + 14 + 3 + 2 = 31 (62 over both coins) + 2 books = 64. Cumulative loop count
after round 2: 1,902; Bonferroni level 0.05 / 1,902 = 2.6e-5. Prior: some of these may clear 25% CAGR and buy-and-hold's
drawdown; beating spot buy-and-hold's CAGR AND Sharpe on both coins with this significance is unlikely.

### Verdicts, loop round 2 (11 Nov 2026, ~14:10 UTC; development out of sample 2020-10-01 to 2025-11-11; `research/out/harness/harness_report_round2.md`)

Rules as registered (strict; vs spot buy-and-hold: BTC +56.2% CAGR, Sharpe 1.03, DD 77%; ETH +56.6%, 0.96, 81%). No pass.
- **H25: FAIL.** BTC +45.8% / ETH +45.1% CAGR, below spot buy-and-hold; fold share 24% / 43%.
- **H26: FAIL.** Best: long-only 1.5x, BTC +55.9% (Sharpe 1.08, DD 52%) but fold share 5%; ETH +43.4%.
- **H27: FAIL.** Books +43.4% (H28) and +45.4% (H25) vs the spot buy-and-hold book +56.4%; fold share 33% / 29%.
- **H28: FAIL.** BTC +31.7%, ETH +52.2% (Sharpe 1.22 vs 0.96, DD 42%); below spot buy-and-hold's CAGR on both.
- **H29: FAIL (closest).** Spot long legs add about 12-25 points of CAGR to every rule. H30 1.5x/0x spot: BTC +78.0%,
  Sharpe 1.19, DD 65%; ETH +105.8%, 1.25, 67%: beats spot buy-and-hold on CAGR, Sharpe and DD on both coins, fails fold
  share (33% / 33%) and significance (p 0.29 / 0.23). H28 spot meets 7 of 8 rules on ETH (p 0.044 vs 2.6e-5 needed).
- **H30: FAIL.** Perp versions +61-71% (BTC), +72-86% (ETH); fold share 10-33%; 2x/0x has a deeper drawdown than buy-and-hold.
- **H31: FAIL.** Trail 4 ATR: BTC +54.2%, ETH +57.3%; spot version +67.6% / +71.9% with the best Sharpe (1.32 / 1.38);
  fold share 43% / 48%; not significant.
- No holdout look taken. Cumulative variants: 1,902.
- Forward note (12 Nov 2026): H29 H30 1.5x/0x spot and H29 H31 trail 4 ATR spot now run forward as paper books,
  NOT passed; see "Forward paper books from round 2" at the end of this file.

---

# Harness loop, round 3 (registered 11 Nov 2026, 14:13 UTC, before any round-3 result was computed)

Code: `research/harness/round3.py`. Development data only (bars before 2025-11-11), same folds, costs, timing and the
round-2 pass rules unchanged (per coin, BTC and ETH, against spot buy-and-hold; Bonferroni over the cumulative count).
One variant per hypothesis. Variants counted: 4 rules x 2 coins = 8, cumulative 1,910 (Bonferroni 0.05 / 1,910 = 2.6e-5).
Robustness, report only (cannot produce or block a pass, not counted as variants): the same frozen rules on XAUUSD,
XAGUSD, USDJPY, SPX, WTI and BRENT, fee a side from `engine15/config.py` asset_cost, no funding, the same spread and
slippage model, metrics annualised by each market's own bars a year. On those markets "daily decision" = the last bar
of each UTC day and the 30-day (10-90 day) returns are measured in calendar days, since they do not trade 24/7. Leverage
financing (swap/carry) on those markets is not modelled.

Common pieces as in round 2: d = frozen daily 30-day momentum sign; rv = 672-bar realised vol annualised; resize at
drift >= 0.25 on the 15m clock; E2 pullback; spot long legs (funding only on exposure above 1x and on shorts).

## H32. Vol-managed buy-and-hold core
Always long: exposure = min(2, 0.60 / rv), spot up to 1x, re-sized on the 15m clock when it drifts >= 0.25 from the
held exposure. No direction filter. Aim: raise Sharpe inside uptrends (fold share), not only sit out downtrends.

## H33. H29-H31 (trail 4 ATR, spot) with the momentum-ensemble direction
Exposure = min(2, 0.60 / rv) while the 10-90 day ensemble e > 0 (else 0), E2 pullback on a new direction, re-sized at
drift >= 0.25; while long, a 15m close below (highest close since entry - 4 x daily ATR14) goes flat until a later
00:00 UTC decision with e > 0 (E2 pullback). Spot long legs.

## H34. Funding-aware leverage on H29-H30 1.5x/0x
As H30 (U = 1.5, D = 0, E2 pullback on increases, spot long legs), but exposure above 1x only while the latest settled
funding rate is at or below the median of the last 270 settlements (~90 days); otherwise 1x. (No funding on other
markets: there it is H30 1.5x/0x.)

## H35. 15m hour-of-day exposure on H32
H32's exposure, held only over bars whose UTC opening hour had a positive mean 15m open-to-open return over the fold's
12-month train window (re-estimated each fold; flat in the other hours). Prior: weak; it will trade far more.

Verdict rule: the round-2 development pass rules, unchanged. Also reported: the Sharpe edge over spot buy-and-hold the
significance rule demands (z = 4.04 x the bootstrap standard error).

### Verdicts, loop round 3 (11 Nov 2026, ~14:15 UTC; development out of sample 2020-10-01 to 2025-11-11; `research/out/harness/harness_report_round3.md`)

Rules unchanged (strict; vs spot buy-and-hold: BTC +56.2% CAGR, Sharpe 1.03, DD 77%; ETH +56.6%, 0.96, 81%). No pass.
- **H32: FAIL.** BTC +55.2%, Sharpe 1.01, DD 82%; ETH +37.1%, 0.81. Vol management did not raise Sharpe on crypto.
- **H33: FAIL.** BTC +65.3%, Sharpe 1.30, DD 66%; ETH +38.0%, 0.91. Fold share 29% / 33%.
- **H34: FAIL.** BTC +64.6%, Sharpe 1.18, DD 56%; ETH +94.4%, 1.26, 61%. 118 / 110 trades a year (turnover rule), fold share 29% / 38%.
- **H35: FAIL.** About 4,000 trades a year, -99% on both coins.
- Other markets (report only): no rule beats buy-and-hold on both Sharpe and drawdown on any of the six.
- Significance demands a Sharpe edge of 0.69-1.47 over spot buy-and-hold; best seen in the loop +0.58. No holdout look.
  Cumulative variants: 1,910. Loop paused by the owner after round 3.

---

## Forward paper books from round 2: H29 H30 1.5x/0x spot (book A) and H29 H31 trail 4 ATR spot (book B) (registered 11 Nov 2026, 20:00 UTC = 12 Nov 2026, 04:00 local; NOT passed)

**Status: NOT passed.** From the strategy loop; NOT passed: both failed fold share and significance on development data
(round 2 above); they run forward on paper to collect unseen evidence. The owner approved this on 12 Nov 2026 ("Yes,
add both", to running them forward as paper shadow books in Mind 15). No new hypothesis ID and no new variant: these are
the two round-2 rules frozen exactly as registered under H29-H31 and counted there (the loop's cumulative count stays
1,910). The loop itself stays paused; no loop rule changes.

- Code: `engine15/playbook4.py` (books `p4_h30spot`, `p4_h31trail`), hooked into `engine15/reports.py`
  (`PLAYBOOK_MODULES`), so they appear in `out/live/playbook.json`, page.json's Books tab and `out/live/scoreboard.json`.
  `tests/test_playbook4.py` proves the module reproduces round 2's targets, positions and per-bar net returns exactly
  (max difference 0.0 on a 2021-06 to 2023-06 slice of each coin) and the frozen development CAGRs (BTC +78.0% / +67.6%,
  ETH +105.8% / +71.9%, difference 0.0); no look-ahead (truncation test).
- **Go-live (forward start): 2026-11-11 20:00 UTC.** Only trades whose entry decision (the close of the bar where the
  target turns on) comes after it count; earlier history is warm-up only. At go-live both rules were flat on both coins
  (daily 30-day momentum down: BTC -10.0%, ETH -17.4%), so no warm-up position was carried.
- Markets: BTCUSDT and ETHUSDT, each its own $10,000 paper book (compounding), long only. Rules, timing and costs as
  round 2: decision at a 15m close, fill at the next 15m open; 0.10% a side, half spread 0.5 bp, slippage 0.10 x
  per-bar vol; longs up to 1x as spot (no funding), perp funding only on exposure above 1x. Live Mind 15 trades perps
  (a long pays funding on all of it); these books keep the loop's spot accounting so the comparison with the loop is
  like for like, and the difference from the main books is stated on the page, not hidden.
- A trade = one run of non-zero exposure, flat to flat (book B's re-sizes inside a run belong to it). On development
  data each book made about 13-15 trades a year per coin, so 30 trades (both coins together) should take about a year.

**Forward pass criteria** (the loop's strict development-pass rules where they apply forward, plus a minimum of 30
trades). Read once, at the first daily close at which a book has 30 closed forward trades (BTC and ETH together). Per
coin, over the span from go-live to that close, net of all costs, against spot buy-and-hold over the same span (1x
long decided at the first close after go-live, one fee, no funding):
1. CAGR >= 25% ((final / initial)^(1 / years) - 1).
2. CAGR strictly above buy-and-hold's.
3. Sharpe strictly above buy-and-hold's, and max drawdown no worse than buy-and-hold's.
4. Fold share: Sharpe above buy-and-hold's in at least half of the forward quarters (3-month folds from go-live; a last
   partial fold counts if it has at least 30 days, as in the loop's walk-forward).
5. Significance: the paired block bootstrap of the daily Sharpe gap (`core.boot_sharpe_diff_z`: block 20, 2,000 draws,
   normal approximation) p <= 0.05 / 1,910 (the loop's cumulative count at go-live); deflated-Sharpe probability reported.
6. No `fee_only_at_0.05` and no `high_turnover` (> 100 position changes a year).
7. Net return positive in more than half of the forward quarters.
Both coins must pass for a book to pass. The scoreboard's own verdict (90% range of the mean result per trade, read at
30 trades) is shown beside it but is not the pass. Honest prior: with about a year of forward data the significance rule
needs a Sharpe edge over buy-and-hold of roughly 2 to 4 (round 2 needed 0.8-1.6 over 5.1 years; the
bootstrap error grows about 2.3x on one year), so a forward pass is very unlikely; the books mainly collect
unseen evidence. **Even a forward pass is not a loop pass**: under `research/harness/LOOP.md` rules 3-4 only a holdout
pass can be confirmed forward, and these books earned no holdout look. A forward pass would be reported to the owner
as unseen evidence and changes neither the loop's verdicts nor its count. The sealed holdout (2025-11-11 to 2026-11-11)
is untouched: the forward span starts after it.

## Forward paper books from RL Phase 6: p6_mtrend (Phase 6 primary) and p6_p4trend (its control) (registered 13 Nov 2026, go-live 2026-11-13 03:00 UTC, before any forward decision; NOT passed)

**Status: NOT passed.** Owner's approval after the Phase 6 review (13 Nov 2026). Code `engine15/playbook6.py` +
`engine15/rl/forward6.py`, in `engine15/reports.py`'s `PLAYBOOK_MODULES` (Books tab, scoreboard). Both run like the RL book
`p5_rlq` (docs/RL.md): BTC and ETH, $10,000 each per book, decided at a 15m close, filled at the next open, 0.10% a side,
perp funding both sides, mean of seeds 0/1/2 through the Phase 3 risk manager; only decisions at closes after go-live count.

- `p6_mtrend` = Phase 6's m_trend: Q agent with the missed-opportunity reward (beta on validation), refit weekly; a model
  whose own validation net Sharpe is under 0.5 holds the daily 30-day momentum position (long or short) instead of flat.
  History (seen): net Sharpe BTC 0.87, ETH 0.96 vs buy-and-hold perp 0.64 / 0.60. **1 of 8 variants tried.**
- `p6_p4trend` = Phase 6's p4_trend, the control: Phase 5's weekly Phase 4 primary models with the same trend fallback.
  History (seen): BTC 0.98, ETH 0.82.
- Both: **the trend fallback was chosen with hindsight** (Phase 4's per-fold results already showed it flat while momentum
  gained). Every historical span was seen; only the forward record is unseen.

**Graded forward on:** no verdict before 30 closed forward trades per coin; then, after fees, Sharpe and Calmar since go-live
against spot and perp buy-and-hold, `p5_rlq`, and each other. The question the pair answers: does p6_mtrend beat
p6_p4trend (the reward adds something) or only p5_rlq (the gain is the momentum fallback)? A forward pass would not make
either a passed rule in history.

## H36. Exits for the main book's own entries: moving-average trails and break-even after Target 1 (registered 13 Nov 2026, ~04:05 UTC, before any result; charter task B)

**Prompted by:** the owner, 13 Nov 2026: "The mind15 trade setup need check. It might not follow their own planned
target profit", then "Explore the trailing stop option like trail profit with ema or sma." The main books (v5.1) exit
only at the fixed entry stop or on a flip; `live.plan_targets` shows Target 1 / 2 but no profit is taken there and the
stop never moves. At registration BTC's short was past both targets with the stop still above entry. Earlier evidence
(seen): the 120-day in-sample read had b_targets -$2,710 and b_trail -$8,670 against the main rule; the replay found
most profit comes from a few long holds (THOUGHT_PROCESS.md), so a tight exit can cut the big winners.

**What changes:** ONLY the exit. Every variant takes exactly the main book's entries, sizing, fees, protective stop,
flips and mandate (`shadows.run`, the same frame as `backtest.run_book`). After any exit the book is flat and the
normal rules decide from the next close (re-entry on either side, the idle clock and the forced entry as after a stop).

**The rules.**
- *MA trail* (`ma_trail`, `ma_arm`): once armed, the trail level at the close of bar t is the moving average at t
  (15m: bars <= t; 1h: the last 1h bar CLOSED by t's close, mavg.py's htf join, the same as `data.htf_on_15`),
  ratcheted so it never loosens (long: the highest MA value since arming; short: the lowest). A 15m CLOSE beyond
  the level against the position (long: close < level) exits at the NEXT open, at market, fees as usual (late-feed
  markets: one bar later, the main book's fill-delay rule). It counts only while the level is tighter than the
  protective stop; the protective stop stays live inside every bar and comes first. A flip or step-aside decided at
  the same close takes precedence. Averages: EMA (seeded) and SMA from the mavg card (`ma_<tf>_<ema|sma><n>_px`).
  Arming: `entry` (from the entry bar's close), `1r` (once a bar's high / low has been 1 stop-distance in favour, as
  b_trail), `t1` (once Target 1 has traded).
- *Break-even after Target 1* (`be_t1`): once a bar trades through Target 1 (`live.plan_targets` at entry), the
  stop moves to the entry price, live from the next bar, only ever tighter. Nothing else changes.
- *Half at Target 1* (`half_t1`): half the position is closed at Target 1 (a limit, filled when a bar reaches it,
  after the stop check); the rest is managed by the variant's trail.

**The frozen grid: 15 variants, all counted.**

| # | Name | Rule |
|---|---|---|
| 1 | `be_t1` | break-even after Target 1, nothing else |
| 2 | `ema20_15m_1r` | EMA20 on 15m, armed after 1R |
| 3 | `ema50_15m_1r` | EMA50 on 15m, armed after 1R |
| 4 | `ema20_1h_1r` | EMA20 on 1h, armed after 1R |
| 5 | `sma20_15m_1r` | SMA20 on 15m, armed after 1R |
| 6 | `sma50_15m_1r` | SMA50 on 15m, armed after 1R |
| 7 | `sma20_1h_1r` | SMA20 on 1h, armed after 1R |
| 8 | `ema20_1h_entry` | EMA20 on 1h, armed from entry |
| 9 | `sma20_1h_entry` | SMA20 on 1h, armed from entry |
| 10 | `ema20_1h_t1` | EMA20 on 1h, armed after Target 1 |
| 11 | `sma20_1h_t1` | SMA20 on 1h, armed after Target 1 |
| 12 | `be_ema20_1h_1r` | break-even after Target 1 + EMA20 on 1h armed after 1R |
| 13 | `be_sma20_1h_1r` | break-even after Target 1 + SMA20 on 1h armed after 1R |
| 14 | `half_ema20_1h_t1` | half at Target 1 + EMA20 on 1h on the rest, armed after Target 1 |
| 15 | `half_sma20_1h_t1` | half at Target 1 + SMA20 on 1h on the rest, armed after Target 1 |

The combinations use the 1h 20-bar averages, chosen before any result as the slowest of the three (the least likely
to cut a long hold). Compared against, on the same entries and odds: the main book (hold to stop or flip), `b_targets`
and `b_trail` (existing shadow rules, already counted).

**The history read** (`research/exit_study.py`, `research/out/exits/trail_study.md` + `.json`): all eight markets,
odds formed as the live step forms them (readings from the evidence store `data/evcache`, read-only; voices walked
forward weekly by `leanprep.walk_forward_cached`, the replay's code), every book from $10,000 per market, from the
engine's birth (CFG birth, 2020-01-01; later where a market's data start later) to the last stored session.
Fallback if a group cannot be walked in memory: the live step's 240-day walk; the report says which window was used.
Halves split at the calendar midpoint of the window (one date for all markets). Per market and pooled: net P&L after
the asset's fee, return, Sharpe (daily marked equity, sqrt(365)), max drawdown, trades, win rate, average win / loss,
the top 6 trades' share of net profit, each half separately, and the gap to main, b_targets and b_trail.

**What counts as better than holding** (descriptive; it changes no main-book rule, only the owner can do that): pooled
net P&L above the main book's in BOTH halves, above it in at least 5 of the 8 markets over the whole window, and
pooled max drawdown no worse than the main book's. With 15 variants (plus the study count above) one passing variant
can be luck.

**Forward shadow books, chosen by this rule, fixed now:** (a) `be_t1`, regardless of its history result (owner,
13 Nov 2026: "Shadow test plus label"); (b) the EMA variant (any of 2-4, 8, 10, 12, 14) and (c) the SMA variant (any of
5-7, 9, 11, 13, 15) with the highest worse-half pooled gap to the main book (min over the two halves of variant P&L
minus main P&L; ties: whole-window pooled P&L). They run forward regardless of the history result, labelled with it
(the owner wants forward data points, not backtest gating). **Graded forward on:** the shadow scoreboard against the
fresh main copy, on forward trades only; no verdict before 30 closed forward trades per book (all markets together).

---

## RL loop round 1 (HRL1): execution, accounting and sizing of the Phase 6 primary (registered 13 Nov 2026, 04:10 UTC, before any result)

Loop rules, target and honesty notes: `research/rl_loop/LOOP_RL.md` (frozen 13 Nov 2026, 04:10 UTC). Target, in short: on
BTC, out of sample 2020-10-01 .. 2026-11-11 after 0.10% fees and funding, seed mean of seeds 0/1/2: net total return and
mean seed CAGR strictly above BTC SPOT buy-and-hold's; seed-mean Sharpe >= 0.87 and above buy-and-hold's, every seed's
Sharpe above buy-and-hold's; every seed's max DD no worse than buy-and-hold's; the same on the sub-span to 2025-11-11
(Sharpe floor 1.05); fold share >= 1/2, no fee_only_at_0.05, <= 100 trades and <= 100 turnover a year per seed,
Bonferroni p <= 0.05 / (all RL variants tried: Phase 6's 8 + this loop's); ETH guard: the same procedure keeps ETH
seed-mean Sharpe >= 0.96, return and mean CAGR above ETH spot buy-and-hold, DD no worse. A historical pass is NOT proof
(every RL window was seen); it becomes a forward paper-book proposal, confirmed only at 30 forward trades.

All five variants reuse the trained Phase 6 `m_trend` fold models (r_missed, trend fallback), unchanged. a = the agent's
decided action (fallback folds: the daily momentum position), s = sign(a), m = the daily 30-day momentum sign at the same
close; risk manager = Phase 4's Phase 3 manager (vol target 60%, size = min(1, 0.60 / 7-day vol), brake x0.75 / x0.50 at
20% / 30% drawdown), executed = request x size; its equity marks use spot-long accounting. Spot longs = long part up to
1x as spot (no funding), shorts and exposure above 1x on perp.
- **HRL1-V1 `spot`**: request a; min hold 4 bars; re-size band 0.20 (Phase 6's execution, spot accounting only).
- **HRL1-V2 `spot_lean`**: request s; min hold 16 bars; re-size band 0.40.
- **HRL1-V3 `spot_lean_agree`**: V2 with request 1.5 s when s = m, else s.
- **HRL1-V4 `spot_lean_agree_veto`**: V3 with request 0 when s != m.
- **HRL1-V5 `spot_lean_blend`**: V2 with request clip(s + 0.5 m, -1.5, 1.5).
Reference (not counted): the Phase 6 primary reproduced (perp accounting); the round stops unless it matches +458.6% /
0.87. Cumulative RL variants after round 1: 13; significance threshold 0.05 / 13.

### Verdicts, RL loop round 1 (13 Nov 2026, ~04:25 UTC; full span 2020-10-01 .. 2026-11-11 and sub-span to 2025-11-11; `research/out/rl_loop/round1_report.md`)

Harness reproduced the Phase 6 primary exactly (BTC +458.6%, Sharpe 0.866; difference 0). Yardstick BTC spot buy-and-hold
+583.9%, Sharpe 0.82, DD 77% (sub-span +879.7%, 1.03). **No pass.** Cumulative RL variants: 13.
- **V1 spot: FAIL** (16/21). BTC +664%, Sharpe 0.99, DD 46%; fails sub-span return, fold share 44%, 177 trades/yr, significance.
- **V2 spot_lean: FAIL** (18/21). BTC +642%, 0.96, DD 44%, 61 trades/yr, fold share 52%; fails sub-span return (+711% vs +880%) and significance.
- **V3 spot_lean_agree: FAIL** (19/21). BTC +993%, 0.96, DD 60%; fails fold share 36% and significance.
- **V4 spot_lean_agree_veto: FAIL** (19/21). BTC +752%, 0.94, DD 56%; fails fold share 40% and significance.
- **V5 spot_lean_blend: FAIL** (19/21). BTC +1,127%, 1.03 (seeds 1.08 / 0.99 / 1.01), DD 54%; fails fold share 36% and significance (p 0.26 vs 0.0038).
- ETH guard held for all five (Sharpe 1.09-1.40 vs 0.962). Significance needs a Sharpe edge of ~1.1-1.25 over spot
  buy-and-hold at N = 13; best seen +0.36. Not proof of anything in any case: every RL window was seen.

## RL loop round 2 (HRL2): leverage where it is cheap, smaller tilts, and the agent retrained on spot accounting (registered 13 Nov 2026, 04:31 UTC, before any result)

Rules and target unchanged from HRL1 (`research/rl_loop/LOOP_RL.md`, frozen 13 Nov 2026 04:10 UTC); exact variant text
in LOOP_RL.md "Round 2". V2 execution = request from s, min hold 16 bars, band 0.40, spot longs; V5 request =
clip(s + 0.5 m, -1.5, 1.5).
- **HRL2-a `blend_fundcap`**: V5, with the part beyond 1x only where funding is cheap (long > 1 while the latest settled
  rate <= its trailing 270-settlement median; short < -1 while it is >= the median; else capped at 1x).
- **HRL2-b `blend_125`**: request clip(s + 0.25 m, -1.25, 1.25), V2 execution.
- **HRL2-c `lean_longlever`**: request 1.5 when s = m = +1, else s, V2 execution.
- **HRL2-d `retrain_spot_lean`**: r_missed retrained exactly as Phase 6 but with spot-long accounting in the reward
  (incl. the reference term) and in the validation score that picks beta and sets the 0.5 fallback bar; V2 execution.
- **HRL2-e `retrain_spot_blend`**: HRL2-d's models, V5 execution.
- **HRL2-f `retrain_spot_longlever`**: HRL2-d's models, HRL2-c execution.
Cumulative RL variants after round 2: 19; significance threshold 0.05 / 19 = 0.00263. Reference (not counted): the
Phase 6 primary reproduced; the round stops unless it matches.

### Verdicts, RL loop round 2 (13 Nov 2026, ~07:52 UTC; full span 2020-10-01 .. 2026-11-11 and sub-span to 2025-11-11; `research/out/rl_loop/round2_report.md`)

Harness reproduced the Phase 6 primary exactly again (difference 0). Yardstick BTC spot buy-and-hold +583.9%, Sharpe 0.82,
DD 77% (sub-span +879.7%, 1.03). **No pass.** Cumulative RL variants: 19 (threshold 0.00263).
- **R2-a blend_fundcap: FAIL** (17/21). +844%, 1.00; 218 trades and 131 turnover a year (the cap flips the request at each
  funding settlement and every new request executes at once: a design flaw, disclosed); fold share 40%; not significant.
- **R2-b blend_125: FAIL** (19/21). +1,073%, 1.06 (seeds 1.13 / 1.00 / 1.05), DD 48%; fold share 44%; p 0.19.
- **R2-c lean_longlever: FAIL** (19/21). +1,114%, 1.01, DD 58% (worst seed 71%); fold share 40%; p 0.22.
- **R2-d retrain_spot_lean: FAIL** (15/21). +867%, 1.03 (seeds 1.03 / 1.23 / 0.82), DD 42%, 58 trades/yr; fold share 48%;
  fails every-seed Sharpe (seed 2 0.82 vs 0.825) on both spans, sub-span return (+831% vs +880%), fold share, significance (p 0.151).
- **R2-e retrain_spot_blend: FAIL** (19/21). +1,273%, 1.04, DD 55%; fold share 32%; p 0.25.
- **R2-f retrain_spot_longlever: FAIL** (19/21). +1,574%, 1.09 (1.10 / 1.21 / 0.97), DD 54% (worst 60%); fold share 36%; p 0.154.
- ETH guard held for all six (Sharpe 1.07-1.40). The spot-trained agent's BTC gain comes mostly from more fallback
  (momentum) folds; its ETH Sharpe fell. Significance needs a Sharpe edge of ~1.0-1.3 over buy-and-hold; best seen +0.41.

### H36 history read and one amendment (13 Nov 2026, ~04:30 UTC; `research/out/exits/trail_study.md`)

- Window 2020-02 to 2026-11-13 (voices walked weekly from the 2020-01-01 birth, readings from the evidence store read-only;
  no fallback was needed). Main v5.1 (hold to stop or flip), 8 markets pooled: **+$329,439**, Sharpe 0.92, max DD -29.6%
  (ETHUSDT alone +$266,807). **Every one of the 15 variants made less than holding**; none passed "better than hold".
  Best: `be_t1` +$107,673 (-$221,766 vs main; without ETH -$8,554; ahead of main only in BTC and USDJPY). Best MA trails:
  `sma20_1h_t1` -$24,645, `ema20_1h_t1` -$25,732; from-entry trails lost ~99%. b_targets -$28,862, b_trail -$48,808.
- **Amendment, disclosed:** the registered pick rule for the EMA / SMA forward books (best worse-half DOLLAR gap to main)
  is degenerate under compounding: the from-entry trails had lost ~99% by the midpoint, so they could not lose many
  dollars in the second half and "won" the worse half while being the two worst variants. The forward books use
  whole-window pooled net P&L within each family instead: `ema20_1h_t1` and `sma20_1h_t1` (shadow books `b_ema20_1h_t1`,
  `b_sma20_1h_t1`), with `be_t1` as `b_be_t1` (owner's decision). The rule was changed after seeing results; count it so.

## RL loop round 3 (HRL3): the agent as a risk-off switch on a long core (registered 13 Nov 2026, 08:02 UTC, before any round-3 code ran or any result)

Rules and target unchanged from HRL1 (`research/rl_loop/LOOP_RL.md`, frozen 13 Nov 2026 04:10 UTC); exact variant text
in LOOP_RL.md "Round 3". s = side of the agent's decision (min hold 16), m = daily 30-day momentum sign; V2 execution =
min hold 16, band 0.40, risk manager, spot longs, part above 1x on perp. Round 2's five proposals are replaced, not run
(disclosed in LOOP_RL.md: leverage and tilts lowered fold share, and none removed the short leg that loses the bull folds).
- **HRL3-a `core_riskoff`**: request 0 when s <= 0 and m = -1, else 1 (no shorts); Phase 6 models.
- **HRL3-b `core_riskoff_125`**: HRL3-a with 1.25 instead of 1 (guard for the return rules against the 60% vol target).
- **HRL3-c `committee_riskoff`**: request 0 when at least two of {Phase 6 agent s <= 0, round 2 spot-trained agent s <= 0,
  m = -1} (same seed), else 1.
- **HRL3-d `retrain_longflat_riskoff`**: r_missed retrained as R2-d (spot accounting) with actions {0, 0.5, 1} and the
  missed-opportunity reference max(ref, 0); execution: request 0 when this agent is flat and m = -1, else 1.
Prior: S1 may pass (a long core turns bull folds from certain losses into near-ties, and flat wins bear folds); S4 is not
expected to (it needs an information ratio of ~1.2 over buy-and-hold); T1 / T4 return may fail because the vol target
holds a 1x request below 1x in high-vol rallies (HRL3-b is the guard). Cumulative RL variants after round 3: 23;
significance threshold 0.05 / 23 = 0.00217. Reference (not counted): the Phase 6 primary reproduced; the round stops
unless it matches.

---

## H37. Hedged long-short structures for BTC and ETH downtrends (registered 13 Nov 2026, 09:33 UTC, before any H37 code existed or any H37 number was computed; EXPLORATION, not a loop round)

**Prompted by:** the owner, 13 Nov 2026: "Also explore long-short strategies. It does not need fully naked short." Naked
shorts here have earned little (the Phase 6 agent's short leg about +4-7% a year on BTC). Question: in a downtrend,
does reducing or hedging the long core beat both going flat and flipping to a naked short, after fees and real funding?

**Status and scope.** Exploration only: NOT a round of `research/harness/LOOP.md` or `research/rl_loop/LOOP_RL.md`; no
loop rule is changed or reinterpreted; it cannot produce a loop pass; it is not added to the loop's count (1,910). If a
variant is later registered formally it gets a fresh registration under the loop's rules, and this study's 11 variants
are disclosed as already tried. (Naming note: LOOP.md's unregistered round-4 proposal also used the label "H37", a
crash-only filter; that proposal was never registered and would need a new number if it is ever run.)
Code `research/longshort_study.py`, results `research/out/longshort/` (`study.md`, `study.json`), tests `tests/test_longshort.py`.

**Data and span.** Development data only: `research/harness/core.load(asset, dev_only=True)` (bars before 2025-11-11);
the sealed holdout 2025-11-11 .. 2026-11-11 is not loaded or run. Reported over the loop's walk-forward out-of-sample
span 2020-10-01 .. 2025-11-11 (the 21 three-month test folds). Every parameter is fixed here; nothing is fitted.

**Common pieces.**
- Daily bars = UTC days from the 15m bars (`engine15.data.resample(..., "1D")`), handed to 15m rows only through
  `engine15.data.htf_on_15` (closed daily bars only). Daily decisions at the close of the 15m bar ending 00:00 UTC,
  filled at the next 15m open; 15m decisions at a 15m close, filled at the next open.
- **Downtrend rule D** (pre-set): last daily close < SMA200 of daily closes AND SMA200 < its value 20 daily bars earlier.
  Not D = up regime U. No hysteresis (the whipsaw this causes is measured, not tuned away).
- **Two legs per coin**: spot s >= 0 (no funding) and perpetual p (pays p x rate at each settlement from
  `data.load_funding` / the RL perp store, as `core.load` returns it: a positive rate costs a long and pays a short).
  Net exposure s + p; gross |s| + |p| <= 1.5 at all times. Costs on every leg's trades (|ds| + |dp|): 0.10% fee a side,
  half spread 0.5 bp, slippage 0.10 x per-bar vol (the harness cost model). Both legs use the same 15m price series
  (spot-perp basis ignored; BTC bars are the perp store, ETH bars are spot). Positions are fractions of equity held
  constant between changes (the harness convention).
- **Yardstick**: spot buy-and-hold 1x (one fee, no funding) over the same span. **References** (computed for
  comparison, NOT candidates, never recommended): R-flat (U: spot 1; D: 0), R-naked (U: spot 1; D: perp -1, the naked
  short of the same signal), R-naked-FR (V5's signal with a flat base and a perp -1 short at the trigger, same exits).

**The variants (5 rules; per coin 5 x 2 = 10, plus the V4 two-coin book = 11).**
- **V1 `dial0`**: U spot 1. D: spot 0.75 + perp -0.75 (net 0, gross 1.5). Why: the owner's "dial" with gross capped at
  1.5 (a 1x core plus a full hedge would be gross 2, so the core is cut to 0.75). Entering D trades 1.0 (0.25 spot +
  0.75 perp), the same as selling to flat; it differs from R-flat only by the funding on the 0.75 short and the spot
  core kept, so it isolates the carry.
- **V2 `dialm05`**: U spot 1. D: spot 0.5 + perp -1.0 (net -0.5, gross 1.5). Why: a partial net short earns part of a
  downtrend with half the squeeze and funding exposure of the naked short.
- **V3 `dial0_fund`**: as V1, but in D the hedge is on only when the mean of the last 3 settled funding rates (known at
  the 00:00 UTC decision) is > 0; otherwise in D spot 0, perp 0 (flat). Checked only at the daily decision (no
  per-settlement churn, the flaw seen in R2-a). Why: the cash-and-carry overlay, honest about funding often turning
  negative in downtrends: collect it when positive, do not pay it when negative.
- **V4 `rv_bear`**: per coin X (its own sleeve): U (X's D off): spot X 1.0. D on X: long the stronger coin spot 0.75 +
  short the weaker coin perp 0.75 (dollar neutral, gross 1.5); stronger = higher 30-day log return at the 00:00 UTC
  decision (BTC vs ETH). The two-coin book = two never-rebalanced half sleeves (as H27), graded against the
  never-rebalanced half-and-half spot buy-and-hold book. Why: relative value removes most market direction in a bear
  while keeping a position; ETH has usually fallen harder than BTC in crypto bears.
- **V5 `fr_hedge`** (short failed rallies only): U spot 1. D base: spot 0.5 (net +0.5). At a 00:00 UTC decision in D with
  no hedge on, put on perp -1.0 (net -0.5, gross 1.5) when ALL of: (a) touch: one of the last 3 closed daily bars had a
  high >= min(SMA20, SMA50) - 0.25 x ATR14 (daily); (b) stall: the last daily close < SMA20 and < the previous daily
  close; (c) not a breakdown: the last daily close is above the lowest daily close of the previous 20 days. Hedge exits
  (15m clock): take profit when a 15m close <= the trigger day's close - 1.5 x ATR14 (daily, at the trigger); stop when
  a 15m close > max(SMA20, SMA50) + 0.5 x ATR14 (last closed daily values); time stop 10 days (960 bars); D off ends it
  (spot back to 1). Re-arming needs a new touch on a daily bar closing after the exit. Why: shorts bear rallies where
  they stall, not after breakdowns (late entry), and takes profit fast (squeeze, whipsaw).
- **V6 agent hedge ratio (net = 1 - h): NOT RUN.** The Phase 6 agent's per-bar decisions are not stored; making them
  means running fold-model inference through `engine15.rl.phase4.asset_ctx`, which builds features over the full span
  including the sealed holdout, and is a heavy job while RL round 3 holds `research/out/heavy_job.lock`. Skipped.

**Reported** (per coin and for the V4 book, against spot buy-and-hold, R-flat and R-naked): total return, CAGR, Sharpe,
max drawdown, Calmar, trades a year (position changes on any leg), fold share (Sharpe above spot buy-and-hold's in the
21 folds), share of folds net positive, calendar years; every D window (D episodes merged across gaps of <= 14 days,
windows >= 30 days kept) and pooled D bars vs U bars; attribution (spot leg, perp leg price, funding, costs); whipsaw
(D flips, result in D episodes shorter than 30 days), late entry (fall from the 180-day high close before each D turn-on),
squeeze (worst 7-day perp-leg result), worst single bars (gaps), funding paid / received in D. Paired block bootstrap
of the daily Sharpe gap vs spot buy-and-hold (`core.boot_sharpe_diff_z`) and the deflated-Sharpe probability are shown
for information; the study's own Bonferroni level is 0.05 / 11.

**Worth a formal registration later (descriptive, fixed now):** on BOTH coins, Sharpe above spot buy-and-hold's, max
drawdown at most 0.75 x buy-and-hold's, and pooled D-bar return above both R-flat's and R-naked's. Meeting it would
only justify registering the rule under the loop's full rules (which it would still have to pass); it is not a pass.
Prior: V1 and V3 will look like R-flat plus a little carry; V2 and V5 can beat R-flat in long bears and lose in
whipsaws; V4 depends on ETH/BTC trending in bears.

### H37 results (13 Nov 2026, ~09:40 UTC; development out of sample 2020-10-01 .. 2025-11-11; `research/out/longshort/study.md`)

Exploration, not a loop verdict. Spot buy-and-hold: BTC +56.2% CAGR, Sharpe 1.03, DD 77%; ETH +56.6%, 0.96, 81%.
**No variant meets the bar registered above.**
- **V1 dial0.** BTC +75.4% (Sharpe 1.28, DD 57%); ETH +66.8% (1.09, 60%). This is R-flat plus about +0.6% a year of
  funding carry (R-flat: +74.3% / +65.9%).
- **V2 dialm05.** BTC +80.7%, DD 60%: +34% in BTC's 2022 bear. ETH +61.2%: -14% over D bars, because of whipsaws.
- **V3 dial0_fund.** BTC +71.4%, ETH +59.4%: worse than V1 on both. Switching cost 2.6% / 5.4% a year. Funding in D
  was mostly positive for shorts (+4.3% / +2.5% annualised).
- **V4 rv_bear.** BTC +78.5% (1.29), ETH +80.8% (1.19); D bars +12% / +55%. The two-coin book made +79.7% (1.25, DD 57%)
  against +56.4% (0.99, 79%) for half-and-half buy-and-hold. It fails the bar only on BTC: its D-bar return is below
  R-naked's +27%. It mainly rides the 2021-2025 ETH/BTC downtrend.
- **V5 fr_hedge.** BTC +64.0%, ETH +58.1%. The failed-rally short alone lost 11% / 28% over D bars.
- **Common to all.** Fold share is 0-24%, because the rules equal buy-and-hold in 9-13 of the 21 folds. Best p is
  0.087, against 0.05 / 11. The biggest loss source is late entry: a median -33% fall before D turned on.
- **V6.** Not run.
- **Holdout.** Not touched.

### Verdicts, RL loop round 3 (13 Nov 2026, ~10:13 UTC; full span 2020-10-01 .. 2026-11-11 and sub-span to 2025-11-11; `research/out/rl_loop/round3_report.md`)

Harness reproduced the Phase 6 primary exactly again (difference 0). Yardstick BTC spot buy-and-hold +583.9%, Sharpe 0.82,
DD 77% (sub-span +879.7%, 1.03). **No pass.** Cumulative RL variants: 23 (threshold 0.00217).
- **R3-a core_riskoff: FAIL** (17/21). +772%, 1.08 (1.16 / 1.08 / 1.00), DD 49%, 41 trades/yr; fold share 44% (folds 12
  and 13 exact ties with buy-and-hold); sub-span return +857% vs +880%; p 0.033.
- **R3-b core_riskoff_125: FAIL** (19/21). +1,428%, 1.14 (1.23 / 1.19 / 1.00), DD 57% (worst 60%), 44 trades/yr; sub-span
  +1,622%, 1.33; fold share 40%; p 0.044.
- **R3-c committee_riskoff: FAIL** (18/21). +710%, 1.09 (1.15 / 1.17 / 0.94), DD 52%; fold share 52% (PASS; 4 of 9 bull
  folds); sub-span return +746% vs +880% (total and mean CAGR); p 0.043.
- **R3-d retrain_longflat_riskoff: FAIL** (18/21). +851%, 1.11, DD 47%; fold share 40%; ETH Sharpe 0.93 < 0.962 (E1); p 0.044.
- The long core cut the bootstrap standard error of the Sharpe gap to 0.22-0.26 (rounds 1-2: 0.37-0.44); the gap itself
  stayed +0.40 to +0.44, so the rule still needs ~1.6-1.7x more (edge needed 0.64-0.73). Bear-fold wins fell (no
  shorts), bull folds moved towards buy-and-hold (fold 23: -1.96 -> +1.69). Not proof of anything in any case.

## H39. New positioning and on-chain inputs, each tested ALONE for BTC and ETH risk information (registered 13 Nov 2026, 10:52 UTC, before any H39 history was downloaded or any H39 number was computed; EXPLORATION, not a loop round)

**Prompted by:** RL loop round 3 (`research/out/rl_loop/round3_report.md`): S4 needs an overlay on buy-and-hold with an
information ratio of ~1.15, i.e. a per-decision information coefficient (IC) of ~0.12-0.17 at 50-100 decisions a year;
the agent's own inputs (price, trend, funding, basis, taker flow, Coinbase premium) look exhausted. The owner chose
"New data first": find free derivatives-positioning and on-chain data, build it as a source, test each input on its own.

**Status and scope.** Exploration only: NOT a round of `research/harness/LOOP.md` or `research/rl_loop/LOOP_RL.md`; no
loop rule is changed or reinterpreted; it cannot produce a pass; nothing is added to either loop's variant count. If an
input is later used in an RL round, that round registers it under the loop's rules and discloses H39 as already seen.
Data module `engine15/sources/flows.py` (docs `docs/SOURCES_flows.md`; NOT wired into the live engine), study code
`research/flows_study.py`, results `research/out/flows/` (`study.md`, `study.json`).

**Data and span.** Development bars only: `research/harness/core.load(asset, dev_only=True)` (bars before 2025-11-11).
The sealed holdout 2025-11-11 .. 2026-11-11 is not loaded; source rows known at or after 2025-11-11 00:00 UTC are dropped
before anything is computed, and every forward window must end before the seal. Decision times: each daily close
(00:00 UTC, the close of the 15m bar ending then). Each input's span starts when its own history allows; BTC bars from
2019-09, so most inputs run from late 2020 or 2021 (ETH Binance positioning from Dec 2021 only).

**Known-at rules (fixed now).** Binance archive metrics (5-minute rows, day D file published ~06:30-08:20 UTC on D+1,
measured 11-13 Nov 2026): a row of UTC day D is known at D+1 12:00 UTC. CoinMetrics community daily value of day D:
known at D+1 06:00 UTC (flash values were computed 01:15-03:20 UTC on D+1 over 7 Nov - 13 Nov 2026). Bitfinex hourly
margin positions: known at stamp + 1 h 5 min. CFTC COT (CME Bitcoin 133741, CME Ether 146021, traders in financial
futures, futures only): at its release (the Friday 15:30 New York rule and the overrides of `engine15/sources/cot.py`).
Stablecoins, Fear & Greed, DVOL: as their existing modules (`market.py`, `derivs.py`) define. At a decision, an input
uses only values known at or before it.

**The inputs (12, fixed now; each with one transform and a risk-off side declared now; same rule for BTC and ETH).**
Windows are trailing, on the input's own daily series (a daily value = the last value known at the decision).
- X1 `oi_chg_7d`: 7-day log change of Binance USDT-M open interest (in coins). Risk-off side: HIGH (leverage building).
- X2 `ls_global_z90`: ln(global account long/short ratio), daily mean of the 5-minute rows, z-score vs the trailing 90
  days. Risk-off: HIGH (crowded long accounts).
- X3 `ls_top_vs_global_z90`: ln(top-trader POSITION long/short) minus ln(global ACCOUNT long/short), daily mean, z vs 90
  days. Risk-off: LOW (large traders less long than the crowd).
- X4 `bfx_net_chg_14d`: 14-day change of ln(Bitfinex margin longs / margin shorts) (tBTCUSD for BTC, tETHUSD for ETH).
  Risk-off: LOW (margin longs being cut relative to shorts).
- X5 `cme_lev_z52`: CFTC leveraged-funds net position as % of open interest, z vs the trailing 52 reports. Risk-off: HIGH.
- X6 `mvrv_z365`: ln(CoinMetrics CapMVRVCur), z vs the trailing 365 days. Risk-off: HIGH (price far above realised).
- X7 `exch_netflow_7d`: 7-day sum of (FlowInExNtv - FlowOutExNtv) / SplyExNtv. Risk-off: HIGH (coins moving onto exchanges).
- X8 `addr_30v365`: ln(mean AdrActCnt over 30 days / mean over 365 days). Risk-off: LOW (activity fading).
- X9 `hash_ribbon`: ln(SMA30 / SMA60) of BTC's daily hash rate (CoinMetrics HashRate; BTC's series for both coins).
  Risk-off: LOW (miner capitulation).
- X10 `stable_30d`: 30-day log change of total stablecoin supply (DefiLlama, existing file). Risk-off: LOW.
- X11 `fng_7d`: 7-day mean of the Fear & Greed index (existing file). Risk-off: HIGH (greed; contrarian).
- X12 `dvol_z90`: Deribit DVOL daily close, z vs 90 days (existing file). Risk-off: HIGH.
Not tested (already among the agent's inputs): funding, perp basis, taker flow (CVD; Binance's taker ratio is the same
quantity), the Coinbase premium. ETF flows: dev history under 2 years, not tested.

**Measures, per input and coin** (oriented: s = +x when the risk-off side is HIGH, -x when LOW; "risk IC" = -Spearman(s,
outcome), so a positive risk IC means the declared side was right).
- Forward return r_h = close(t+h)/close(t) - 1 and forward drawdown dd_h = min(daily low over t+1..t+h)/close(t) - 1,
  h = 1, 7, 30 days, on UTC daily bars from the 15m bars.
- Risk IC with r_h and with dd_h; 95% CI and p-value from a moving-block bootstrap over decision days (block max(10, 2h)
  days, 2,000 draws; p two-sided from the bootstrap standard error, normal approximation).
- Incremental value: partial rank correlation of s with r_h controlling for the 30-day momentum sign m (sign of the
  30-day return) and the 200-day downtrend rule D (H37's: close < SMA200 and SMA200 below its value 20 days earlier),
  i.e. the correlation of the residuals of rank(s) and rank(r_h) after OLS on [1, m, D]; same bootstrap. Also the
  nested regression r_h ~ m + D (+ standardized rank of s): added R^2.
- Risk-off calls (descriptive, not tested): s above its trailing 365-day 80th percentile (needs 180 days). Hit rate =
  share of calls with r_h < 0, against the base rate over the same days; mean r_h and dd_h in calls vs the rest; and
  the same for momentum's own risk-off calls (m = -1) for reference.
- Benchmark: IC needed for IR 1.15 at horizon h with independent bets every h days = 1.15 / sqrt(365 / h): 0.060 (1d),
  0.160 (7d), 0.331 (30d); round 3's 0.12-0.17 band corresponds to the 7-day horizon.
- Multiple testing: 12 inputs x 2 coins x (6 risk ICs + 3 partial ICs) = 216 tests; Bonferroni at 0.05 / 216 and
  Benjamini-Hochberg q reported. The number of tests actually run is reported.

**Worth an RL round 4 built on it (descriptive bar, fixed now):** an input qualifies only if, on BOTH coins, its partial
risk IC at h = 7 days is positive, Bonferroni-significant (p <= 0.05 / 216) and >= 0.12, AND its risk IC at 7 days has
the same sign in the first and second half of its own dev span. Meeting it justifies proposing the input for a
registered RL round; it is not a pass and proves no edge. Prior, stated now: most inputs will show |IC| under 0.05 and
nothing will meet the bar; positioning history (late 2020 / 2021 on) covers about 4-5 dev years, mostly one bull top,
one bear and one recovery, so even a large IC is fragile.

### H37 V4 forward paper book (owner-approved 13 Nov 2026; go-live 2026-11-13 11:30 UTC)

The owner answered "Yes" to running H37's V4 (`rv_bear`) forward as a paper shadow book. Module `engine15/playbook7.py`
(book `p7_rvbear`, BTC sleeve and ETH sleeve, each $10,000), wired into `engine15/reports.PLAYBOOK_MODULES`; it shows on
the mind15 Books tab through page.json. The rule is frozen exactly as registered above; `tests/test_playbook7.py` proves
it reproduces the study's V4 targets and per-bar net returns. Unlike playbook4, the book takes the rule's position at the
first close after go-live (as its buy-and-hold comparison does). NOT passed; exploration, no loop rule changed, no loop
variant added. Forward verdict only after 30 closed forward trades (both sleeves together), after fees and funding,
against each coin's spot buy-and-hold since go-live.

### H39 results (13 Nov 2026, ~11:45 UTC; development data to 2025-11-11; `research/out/flows/study.md`)

Exploration, not a loop verdict; no loop rule or count changed. 216 tests run (as registered), Bonferroni 2.31e-04.
**No input meets the registered bar** (partial risk IC at 7 days >= 0.12, Bonferroni-significant, both coins, same sign
in both halves). Largest partial IC at 7 days on the registered side: BTC exchange net inflow +0.075 (p 0.08), ETH
active addresses +0.053 (p 0.26); the IC an information ratio of 1.15 needs at 7 days is ~0.16. Five tests pass
Bonferroni, all next-day drawdown tests (stablecoin 30-day change on both coins with the opposite of the registered
sign, DVOL z on both coins, BTC exchange net inflow): volatility information, not direction (DVOL's return IC has the
wrong sign). Risk-off tail calls hit 40-54% (r7 < 0) vs base rates 46-50%, no better than momentum's own risk-off calls.
Binance positioning covers BTC from Sep 2020 and ETH from Dec 2021 only. A unit bug made the first run compute nothing;
fixed and rerun once, disclosed in the study. Holdout not touched. Prior confirmed: nothing here supports an RL round 4
built on these inputs.

## H40. Deribit options flow (put/call and skew), each input tested ALONE for BTC and ETH risk information (registered 14 Nov 2026, 09:00 UTC, before any H40 history was downloaded, any Deribit history endpoint was probed or any H40 number was computed; EXPLORATION, not a loop round)

**Prompted by:** the owner's "Yes. Test them" (14 Nov 2026) about new data sources, after the paid-data survey
(`research/out/paid_data/survey.md`) found Deribit's public history API to be the only free source with enough options
history (start date unverified there). Same question, method and bar as H39: does an input carry a risk-off signal for
BTC or ETH that is INDEPENDENT of the trend features, at the IC of ~0.12-0.17 that RL loop S4 needs (round 3: an overlay
information ratio of ~1.15 at 50-100 decisions a year)? The bar is not lowered for this hypothesis.

**Status and scope.** Exploration only: NOT a round of `research/harness/LOOP.md` or `research/rl_loop/LOOP_RL.md`; no
loop rule changed; it cannot produce a pass; nothing is added to either loop's variant count. If an input is later used
in an RL round, that round registers it and discloses H40 as already seen. Data module `engine15/sources/options_hist.py`
(docs `docs/SOURCES_options_hist.md`; NOT wired into the live engine, a test enforces it), study code
`research/options_study.py`, results `research/out/options/` (`study.md`, `study.json`).

**Data.** `history.deribit.com/api/v2/public/get_last_trades_by_currency_and_time`, `currency` BTC and ETH, `kind=option`,
`sorting=asc`, `count=1000`, no key, no account; every inverse option trade (instrument `<COIN>-<DDMMMYY>-<strike>-<P|C>`;
USDC-settled linear options are not under these currencies and are not used). Trades are aggregated as they arrive into
one row per UTC hour per coin (raw pages are not kept), stored in `data/sources/options_<kind>_<asset>.csv` with
`known_ms` = the end of the hour (trades are public when they print). Fetched only up to the seal (2025-11-11 00:00 UTC):
no holdout trade is downloaded. Stop rule (fixed now): if the history API does not serve BTC option trades back to at
least 2021-01-01, the test is not run and that is reported instead.
Per trade: notional = amount (coins; one Deribit inverse option = one coin) x index_price (US$); taker side = `direction`;
block trade = `block_trade_id` present; delta = Black-Scholes delta from the trade's `iv`, strike, time to expiry
(expiry 08:00 UTC of the instrument's date) and the index price as the underlying (the forward is approximated by the
index; zero rates); this delta is approximate (basis ignored), stated as a caveat.

**Development data only.** Bars from `research/harness/core.load(asset, dev_only=True)` (before 2025-11-11); every
options row known at or after 2025-11-11 00:00 UTC dropped before anything is computed (`options_hist.inputs(...,
cutoff_ms=seal)`); forward windows must end before the seal. Decision times: each daily close (00:00 UTC), as H39.

**The inputs (6, fixed now; one transform and one risk-off side each, same rule for BTC and ETH).** Windows end at the
decision and use only hours that have ended by it.
- O1 `pcr_7d`: ln(put notional / call notional), all option trades over the trailing 7 days. Risk-off: HIGH.
- O2 `pcr_1d_z90`: ln(put notional / call notional) over the trailing 24 hours, z-score against the trailing 90 daily
  values (30 to speak). Risk-off: HIGH.
- O3 `taker_bear_7d`: taker bearish flow over 7 days = [(put taker-buy - put taker-sell) - (call taker-buy - call
  taker-sell)] notional / total option notional. Risk-off: HIGH (takers buying puts / selling calls).
- O4 `rr25`: approximate 25-delta skew = amount-weighted mean trade IV of puts with |delta| in [0.15, 0.35] minus that of
  calls with delta in [0.15, 0.35], expiries 7-60 days away, over the trailing 72 hours, in vol points (needs >= 10
  trades in each side). Risk-off: HIGH (puts dearer than calls).
- O5 `rr25_chg7`: O4 minus O4 seven days earlier. Risk-off: HIGH (puts bid quickly).
- O6 `block_bear_7d`: the O3 measure on block trades only, over 7 days, divided by total block notional over 7 days
  (needs >= 5 block trades). Risk-off: HIGH (large-block put buying). Large-block flow before block trades were common
  may be thin; reported with its span.
The opposite (contrarian) reading of the put/call ratio is NOT given a second test; the sign of every IC is reported.
Not tested here: DVOL (H39 X12), open interest (not in trade history).

**Measures** (exactly H39's code and conventions: oriented s, risk IC = -Spearman(s, outcome), moving-block bootstrap,
block max(10, 2h) days, 2,000 draws; forward return r_h and forward drawdown dd_h, h = 1, 7, 30 days, daily bars from the
15m dev bars).
- Risk IC with r_h and dd_h (6 tests per input per coin).
- Incremental (partial) IC with r_h controlling for [1, m, D] (30-day momentum sign, 200-day downtrend rule), h = 1, 7,
  30 (3 tests); added R^2.
- Added for H40 (registered now, counted): partial IC with r_7 controlling for [1, m, D, DVOL z90] (H39 X12), to check
  that a skew or put/call reading is not just volatility (1 test).
- Risk-off calls (descriptive, not tested): s at or above its trailing 365-day 80th percentile (needs 180 days); hit
  rate (r_h < 0) vs base rate, mean r_h and dd_h in calls vs rest, momentum's own risk-off calls for reference.
- Halves: risk IC at 7 days in each half of the input's own span.
- Multiple testing: 6 inputs x 2 coins x (6 + 3 + 1) = **120 tests**; Bonferroni at 0.05 / 120 = 4.17e-04; BH q reported;
  the number of tests actually run is reported.

**Bar (fixed now, the same as H39's; not lowered):** an input is worth proposing for a registered RL round only if, on
BOTH coins, its partial risk IC at h = 7 days (controls m, D) is positive, Bonferroni-significant (p <= 0.05 / 120) and
>= 0.12, AND its risk IC at 7 days has the same sign in both halves of its span. 0.12 is the low end of the 0.12-0.17 band
S4 needs (~0.16 for IR 1.15 at 7 days). Meeting it proves no edge and is not a pass. Prior, stated now: the H39 inputs all
fell short (best +0.075); options flow is likely to carry volatility (size) information like DVOL did, and nothing is
expected to meet the bar.

### H40 results (14 Nov 2026, ~13:15 UTC; development data to 2025-11-11; `research/out/options/study.md`)

Exploration, not a loop verdict; no loop rule or count changed. Data: Deribit's public history API serves option trades
from 2016-11-29 (BTC) and 2019-03-21 (ETH), so the stop rule (BTC back to 2021) did not trigger; stored 2019-01-01 (BTC)
/ 2019-03-21 (ETH) to the seal, 20.9 million BTC and 14.8 million ETH trades folded into 60,144 / 58,248 gapless hourly
rows (28 MB; no raw pages kept; no holdout trade fetched). 120 tests run (as registered), Bonferroni 4.17e-04.
**No input meets the registered bar** (partial risk IC at 7 days >= 0.12, Bonferroni-significant, both coins, same sign
in both halves). On the registered side the largest partial IC at 7 days is ETH 25-delta skew +0.026 (p 0.55); every BTC
partial IC at 7 days is negative. The largest effect is the wrong way round: BTC 7-day put/call notional -0.122 (p 0.011,
not Bonferroni-significant; -0.085, p 0.11, with DVOL controlled; ETH -0.039): heavy put trading was followed by better,
not worse, BTC weeks. That contrarian reading was not registered and is not claimed. Two tests pass Bonferroni, both
next-day drawdown tests of the 7-day put/call ratio (ETH +0.151, BTC +0.129): size-of-move information, as with DVOL in
H39, not direction. Risk-off tail calls hit 36-48% (r7 < 0) against base rates of 46-48%, below momentum's own 49-51%.
The skew level correlates -0.48 with the 30-day momentum sign. Holdout not touched. Prior confirmed: options flow from
free Deribit trade history does not give the independent risk-off IC of ~0.12-0.17 that S4 needs.

---

## H41. Liquidity hunt v2: the P1 sweep fade with a trend filter, wider stops, confirmation entries and no round-number pools (registered 15 Nov 2026, 05:45 UTC, before any H41 code existed or any H41 number was computed)

**Prompted by:** the owner, 15 Nov 2026: "dissect do post morterm and improve rather test the same setup". The
post-mortem (`research/out/p1_postmortem.md`, 65 live P1 trades, 11-15 Nov 2026, small sample, one falling regime):
long fades lost badly (19% won) because the rule fades sweeps against the trend; the stop at the extreme + 0.1 ATR is
re-swept (20 of 53 stops within 2 bars; 22 of 53 stopped trades later reached 1R); costs 0.26R median (0.5R on BTC)
on 0.2-0.4% stops; round-number pools were the worst; mean -0.38R even before costs.

**Common to every variant (fixed now).** The P1 sweep detection exactly as registered for H6 (`playbook.p1_signals`,
k = 0.25 ATR, reclaim on the sweep bar or within m = 2 bars, swept-side wick >= 50% of the sweep candle, funding
confirmation on BTC/ETH), the same frame (closed bars, decision at a close, fill at the next open, a stop and a
target in one bar = stop first, a gap through the stop fills at the open, a fill that gaps beyond the stop is not
taken, one trade per asset at a time), $10,000 a trade at the asset's own fee a side (`playbook.fee_side`: crypto
0.10%, gold 0.02%, silver 0.03%, USDJPY 0.01%, S&P 0.02%). Hold limit 24 bars (6 hours) for every v2 variant, then
out at the next open. Levers:
- **T (trend filter):** fade a sweep of a HIGH (short) only when the v5 higher-timeframe bias (`playbook.htf_bias`)
  at the decision bar is down or neutral; a sweep of a LOW (long) only when it is up or neutral.
- **R (no round numbers):** the round-number pool is removed from the pool list (24h, 7-day, prior-day and confirmed
  15m swing pools stay).
- **Stop pad:** the stop sits at the sweep's extreme + pad x ATR(14, 15m) at the decision bar, pad 0.1 / 0.5 / 1.0.
- **Entry:** "open" = the next open after the reclaim (as P1); "confirm" = the bar after the reclaim must also CLOSE
  on the reclaimed side of the pool (below it after a sweep of a high), decision at that close, fill at the next
  open, the extreme (and so the stop) taken over the sweep bar through the confirmation bar; "retest" = a limit
  order at the reclaimed pool level, live for the 4 bars after the reclaim, filled only if a bar trades THROUGH the
  level (strictly beyond it; at the open if the bar opens beyond the level but not beyond the stop; a bar that opens
  beyond the stop cancels it); on the fill bar only the stop is checked (stop first), targets from the next bar.
- **Exit:** "E1" = half at 1R, the rest at 2R, the stop to entry from the bar after 1R fills (P1's "fixed");
  "E2" = everything at 1.5R.

**The variants (8, all counted):**

| id | T | R | pad | entry | exit |
|---|---|---|---|---|---|
| V1 | yes | yes | 0.1 | open | E1 |
| V2 | yes | yes | 0.5 | open | E1 |
| V3 | yes | yes | 1.0 | open | E1 |
| V4 | yes | yes | 0.5 | confirm | E1 |
| V5 | yes | yes | 0.5 | retest (4 bars) | E1 |
| V6 | yes | yes | 0.5 | open | E2 |
| V7 | yes | yes | 0.5 | confirm | E2 |
| V8 | no | yes | 0.5 | open | E1 (measures lever T against V2) |

The original P1 (H6 registered rule: round numbers in, pad 0.1, no trend filter, next open, E1, hold 16) is re-run
through the same code as the control; it is not a new variant.

**Data:** the six P1 markets (BTCUSDT, ETHUSDT, XAUUSD, XAGUSD, USDJPY, SPX), bars before the sealed holdout
2025-11-11 00:00 UTC only (later bars and funding rows are dropped right after loading; the holdout is not looked at).
Trades count from 2020-01-01 by entry time. First half: entries before 2023-06-07 (the H6 split). Second half:
2023-06-07 to the seal.

**Selection (first half only):** the variant with the highest score = the mean over the markets (each with at least
20 first-half trades) of the first-half expectancy after costs (% of stake per trade), among variants with at least
100 first-half trades in all (H6's rule). Ties: fewer levers. Nothing from the second half is used to choose.

**Confirmation (second half, the chosen variant only, untouched).** **Pass bar, fixed now:** all of
(1) pooled six-market second-half net result after costs > 0 (sum of net $; at least 100 second-half trades in all);
(2) net $ after costs > 0 in at least 4 of the 6 markets in the second half;
(3) pooled second-half expectancy after costs per trade (% of stake) higher than the original P1's re-run through the
same code on the same bars.
Pass -> a forward paper book (`engine15/playbook8.py`, book `p13_lh2`) is written for the owner to approve; no pass ->
reported as such, nothing goes forward. A pass is not proof of an edge: it is a history check before forward grading.

**Variants tried overall:** H6/H7's 29 + these 8 = 37. The other 7 variants' second halves are reported for
reference only and do not change the choice.

**Prior, stated now:** the H6 base was about zero before costs on 2020-2026 history in both halves; the levers cut
cost share (wider stops) and trade against weak sides (trend), but nothing is expected to clear the bar with ease.

### H41 results (15 Nov 2026, ~06:00 UTC; development data to 2025-11-11; `research/out/liqhunt2/study.md`)

**NO PASS.** Code: `engine15/liqhunt2.py` (reuses `playbook.prepare`, `p1_signals`, `htf_bias`, `_money` unchanged),
`research/liqhunt2_study.py`. The original P1 re-run through the new simulator equals `playbook.simulate` trade for trade
on every market; every variant passes a truncation (no look-ahead) test (0 mismatches in 72,021 closed trades checked).
Variants tried overall: 37 (H6/H7 29 + H41 8). Holdout not touched.

Chosen on the first half (registered score, mean over markets of expectancy after costs): **V8** (no trend filter, no
round numbers, stop 0.5 ATR, next open, half 1R / rest 2R, hold 24), score -0.095% a trade (the eight scores ran from
-0.115% to -0.095%; the original P1 scored -0.092%, so by the registered metric no v2 variant beat it even in the first
half). First half pooled: 13,531 trades, 47.8% won, -0.02R before / -0.22R after costs, net -$93,299. **Second half
pooled: 9,815 trades, 46.9% won, -0.02R before / -0.25R after costs, -0.066% a trade, net -$65,164, PF 0.67**; negative
on all six markets (BTC -0.136%, ETH -0.217%, gold -0.049%, silver -0.058%, USDJPY -0.019%, S&P -0.060% a trade). Original
P1 second half: 14,401 trades, -0.37R after costs, -0.076% a trade, net -$109,797. Bar: pooled positive NO; >= 4 of 6
markets positive NO (0); better per trade than P1 YES.

Why: every variant averages -0.03R to +0.01R BEFORE costs in both halves. The levers moved the cost share (wider stops
cut the median cost from ~0.25R to 0.13-0.19R) but no lever created a gross edge. The trend filter made no difference
on history (V2 vs V8 about equal; long and short fades lose alike on 2020-2025), so the live four-day long/short gap
looks like one regime. Confirmation entries (V4, V7) cut trades ~65% and raised the cost share to ~0.3R; the limit
retest (V5) was in between. No `engine15/playbook8.py` was written; nothing goes forward from H41. The original P1 keeps
running under its own H6 verdict rule.

### H6 retired (owner, 15 Nov 2026, 06:15 UTC)

Owner: "Retire it", after the post-mortem of its first 65 live trades (`research/out/p1_postmortem.md`: 32% won,
-$1,421, -0.38R a trade before costs; no code bug) and H41 (8 improved versions, none with an edge before costs on
2020-2025). `engine15/playbook.py` RETIRED: no trade entered from 2026-11-15 06:15 UTC counts; the live record before
it is kept as is. The verdict rule (200 trades or 30 days) was not reached; retired early on the owner's word.

## H42. A more balanced trust blend for the voices (registered 15 Nov 2026, 09:30 UTC, before any H42 code existed or any H42 number was computed)

**Prompted by:** the owner, 15 Nov 2026: "yes" to testing a more balanced trust blend. Live, the crypto group's trust
(`model.trust_path`: Hedge weights `exp(-trust_eta x (S - S.min()))` on a decayed sum S of graded directional log-losses,
half-life 960 sessions, floored at `trust_floor`, renormalised, then restricted to the group's voting cards) gives one
voice ("levels", support and resistance) about 79% of the say, and the other 12 voters sit at about 1.8% each.
Question: does a blend where 3-5 voices share the say predict and trade better?

**A mechanical fact, stated before any number:** the floor is applied across ALL 59 voices before the voting cards are
picked out (`backtest.prepare`, `leanprep.prepare_live`). With 59 x 0.02 = 1.18 > 1, the floor already binds for most
voices, and once a leader saturates its raw weight a floor f leaves it about 1 / (1 + 12 f) of a 13-card vote
(f 0.02: ~0.8; 0.05: ~0.63; 0.08: ~0.51). The floor variants therefore mostly shift say from the leader to ALL voters
equally; the eta variants change how fast the leader saturates. The engine's mechanics are kept exactly; only the two
constants change (a cfg copy; `engine15/config.py` is not edited).

**The frozen grid: 6 variants (1 baseline + 5 challengers), all counted; half-life unchanged at 960 sessions.**

| # | Name | trust_eta | trust_floor |
|---|---|---|---|
| 0 | `base` (live v5.1.1) | 0.2 | 0.02 |
| 1 | `f05` | 0.2 | 0.05 |
| 2 | `f08` | 0.2 | 0.08 |
| 3 | `e10` | 0.1 | 0.02 |
| 4 | `e05` | 0.05 | 0.02 |
| 5 | `e10f05` | 0.1 | 0.05 |

**Data and method** (`research/trust_study.py`; report `research/out/trust/study.md` + `.json`). Development data only:
every row before 2025-11-11 00:00 UTC; bars, readings and the feature matrix are truncated there BEFORE the grades are
computed, so no later row is touched. Readings and X from the evidence store `data/evcache/<group>` (read-only); the voices
walked forward weekly from the engine's birth (2020-01-01) by `leanprep.walk_forward_cached` (the replay's code), its
refits kept in `research/out/trust/fits/` (never the live fits directory). Per-voice odds and grades are computed once
per group; each variant then re-runs only the trust path, the voting restriction, the silent-voice mask and the mix (as
`leanprep.prepare_live`), and the main book (`backtest.run_book` with the asset's fee, leverage cap and fill delay, as
live; the live-only total-risk cap across books is not applied). Group voting cards and the index's 26-session grading
horizon as live. Halves split at the calendar midpoint of 2020-01-01 .. 2025-11-11: **2022-12-06 00:00 UTC** (first
half = selection, second half = confirmation). Each half's books start flat at $10,000 per market (trust carries on
continuously).

**Metrics, per variant x group x half:** (a) the mixed odds' 3-class log-loss on every graded session (assets pooled
in the group) and the direction hit rate (on calls graded up or down: all, and where |edge| >= 5 pts); (b) the
effective number of voices 1 / sum(w^2) of the voting trust over time (mean, median, 10th / 90th percentile), the
leader's mean share, the share of time one voice holds > 50%, and which voice leads; (c) the main book per market and
pooled per group and over all 8 markets: net return, Sharpe (daily marked equity, sqrt(365)), max drawdown, trades.

**Selection (first half only):** among the 5 challengers, the one with log-loss below `base` in the most groups;
ties broken by the lower mean over the 5 groups of (variant - base) log-loss.

**Fixed pass bar (second half only):** the chosen variant has lower log-loss than `base` in at least 4 of the 5 groups
(crypto, metals, fx, index, energy) AND its pooled (8-market) second-half book Sharpe is not lower than `base`'s AND its
pooled second-half max drawdown is no worse than `base`'s by more than 2 percentage points. Variants tried: 6 (5
challengers). In-sample history; a pass would be a reason to ask the owner, not proof. If no pass, nothing changes.

### H42 results (15 Nov 2026, ~09:58 UTC; development data to 2025-11-11; `research/out/trust/study.md`)

**NO PASS.** Code: `research/trust_study.py` (per-voice odds once per group via `leanprep.walk_forward_cached`, refits in
`research/out/trust/fits/`; the baseline trust equals `leanprep.trust_tail` exactly in every group; only `trust_eta` /
`trust_floor` change through a cfg copy). Variants tried: 6 (5 challengers). Holdout not touched.

Chosen on the first half: **`f08`** (eta 0.2, floor 0.08): log-loss below base in 4 of 5 groups (all challengers tied at
4/5, fx the exception; `f08` had the lowest mean gap, -0.00043). Second half: log-loss below base in **5 of 5** groups
(crypto 0.86660 vs 0.86688, metals 0.79073 vs 0.79080, fx 0.80166 vs 0.80199, S&P 1.07598 vs 1.07610, oil 0.73548 vs
0.73646): YES. Pooled 8-market main-book Sharpe **0.95 vs 1.06**: NO. Pooled max drawdown -17.2% vs -16.9%: YES (within
2 points). Effective number of voices (crypto, second half) 11.5 vs 8.4 of 13; one voice above 50% 0.2% vs 19% of the time.

Reading: every challenger beats the live setting on log-loss in all 5 groups in the second half, but by 0.005% to 0.15%;
hit rates stay at 50-52%. The main book is insensitive (gold, silver, S&P identical under all 6 variants) or noisy
(crypto: BTC better and ETH +124% -> -6% to -17% under every challenger; pooled Sharpe 0.89-1.10 across challengers, only
`e10` above base and not chosen). Historically crypto's trust had one voice > 50% for 17-19% of the time (oil 23-32%,
metals 21% then 4%, fx and S&P ~0%); the live ~79% "levels" concentration is later than the development cut. The floor acts
across all 59 voices before the voting cards are picked; the overall lowest-loss voice is a non-voting one 45-72% of the
time, so voters often sit at the floor together. Nothing changes in the live engine.

## H43. Trust cap 40% (owner's choice; engine think15-v5.2, 15 Nov 2026)

**Owner, 15 Nov 2026:** "Should we set max weightage for each card" ... "Ok lets set it as 40%". Live from the next
restart (15 Nov 2026): `config.trust_cap = 0.40`, `model.cap_shares` applied to the voting cards' shares and again after
silent voices drop out, in `backtest.prepare`, `leanprep.prepare_live` and `intraday.mix_odds`. Chosen by the owner,
not selected by a test: I advised testing 30/40/50% first (H42 had found more balanced blends predicted marginally
better but traded worse). The history comparison below is recorded for the review, not as a gate. Forward grading: the
main books' live record from v5.2 on, compared at the 10 Dec review with v5.1.2's record before it.

## H44. Range breaks with momentum, read against the daily ATR budget ("eagle view") (registered 16 Nov 2026, 04:40 UTC, before any H44 code existed or any H44 number was computed)

**Prompted by:** the owner, 16 Nov 2026: "Do a research to see any pattern or any technical indicator can identify if
the price range broke with momentum on the average range. There might be a trending/momentum up or down. With a
confluence of eagle view of daily ATR on 15 minutes. Then spot the potential setup at 15 minutes time frame".

**Interpretation (mine, stated before any number).**
(1) A 15m **range break with momentum** = a 15m bar that CLOSES beyond a recent range, and whose true range is at least
k x ATR(14, 15m) as it stood at the close of the bar BEFORE (so the break bar does not inflate its own yardstick).
Ranges tried: the last N bars' high/low (N = 24 = 6 hours, or N = 12 = 3 hours; the bars before the break bar), the
prior UTC day's high/low (first close beyond it), the UTC day's opening range (high/low of the day's first 4 bars on
file, i.e. 00:00-01:00 UTC for crypto and the first cash hour for the S&P; breaks counted from the 5th bar, first close
beyond it). A volume condition is NOT used: volume is not comparable across sources outside crypto (extdata
VOLUME_NOTE; USDJPY has none).
(2) The **eagle view** = the daily ATR(14) (Wilder, on UTC daily bars from `data.resample`, joined with
`data.htf_on_15`: the last CLOSED day's value). At the break bar's close: **used** = (today's high - today's low so
far, this bar included) / daily ATR; **room left** in the break direction = 1 - (close - today's low) / daily ATR for
an up break (1 - (today's high - close) / daily ATR down); **position** in today's range = (close - low) / (high - low).
(3) **Hypothesis:** breaks with momentum while the day has room left (used < 0.65) continue; breaks after the day has
already used >= 1.0 daily ATR are exhausted (continuation fails or fades). Buckets: room-left used < 0.65, middle
0.65-1.0, exhausted >= 1.0.

**The trade (fixed now, common to every variant).** Decision at the break bar's close, fill at the next open (a fill
that gaps beyond the stop is not taken). Stop = the break bar's close -/+ 1.0 x ATR(14, 15m) at that close (so 1R is
about one 15m ATR). Exit E1 (the engine's "fixed"): half at 1R, the rest at 2R, the stop to entry from the bar after
1R fills. Hold limit 16 bars (4 hours), then out at the next open. Same frame as every playbook: a stop and a target in
one bar = stop first, a gap through the stop fills at the open, one trade at a time per market, $10,000 a trade, the
market's own fee a side (`playbook.fee_side`: crypto 0.10%, gold 0.02%, silver 0.03%, USDJPY 0.01%, S&P 0.02%, WTI
and Brent 0.04%). The simulator is `playbook.simulate` unchanged.

**The variants (8, all counted):**

| id | range | k | daily-ATR filter | exit | role |
|---|---|---|---|---|---|
| V1 | last 24 bars | 1.5 | room-left (used < 0.65) | E1 | candidate |
| V2 | last 24 bars | 2.0 | room-left | E1 | candidate |
| V3 | last 12 bars | 1.5 | room-left | E1 | candidate |
| V4 | prior UTC day high/low | 1.5 | room-left | E1 | candidate |
| V5 | opening range (first 4 bars) | 1.5 | room-left | E1 | candidate |
| V6 | last 24 bars | 1.5 | room-left | half at 1R, rest at the day's room level (today's low + 1 daily ATR for a long, high - 1 daily ATR for a short; T1 + 1R if that is not 0.5R beyond T1) | candidate |
| V7 | last 24 bars | 1.5 | EXHAUSTED (used >= 1.0) | E1 | contrast, not selectable |
| V8 | last 24 bars | 1.5 | none | E1 | no-eagle-view control, not selectable |

The pass bar compares the chosen variant with its **no-eagle twin**: the same rule with the daily-ATR filter removed,
run through the same code (for V1 that is V8; for the others it is computed as a control, not counted as a variant).

**Data:** the eight markets (BTCUSDT, ETHUSDT, XAUUSD, XAGUSD, USDJPY, SPX, WTI, BRENT) from `data.load`, rows before
the sealed holdout 2025-11-11 00:00 UTC only (later rows dropped right after loading; never read). Trades count from
2020-01-01 by entry time (2019 is warm-up). First half: entries before 2023-06-07 (the H6/H41 split). Second half:
2023-06-07 to the seal.

**Selection (first half only):** among V1-V6, the highest mean over markets (each with >= 20 first-half trades) of the
first-half expectancy after costs (% of stake per trade), among variants with >= 100 first-half trades in all. Ties:
the lower id. Nothing from the second half is used to choose.

**Fixed pass bar (second half, the chosen variant):** all of (1) pooled 8-market net $ after costs > 0 with >= 100
trades; (2) net $ > 0 in at least 5 of the 8 markets; (3) pooled profit factor >= 1.1; (4) pooled expectancy per trade
after costs (% of stake) higher than its no-eagle twin's in the second half. A pass would be a reason to propose a
forward paper book to the owner, not proof of an edge; no pass -> reported as such, nothing trades.

**Descriptive table (reported whatever the result; pre-cost, events not trades, overlaps allowed):** for every break
with momentum (each range at k 1.5, and the 24-bar range at k 2.0), by bucket (room-left / middle / exhausted) and
half: count, forward return in the break direction from the next open to the close 4 / 8 / 16 bars later (in ATR15
units and %), MFE and MAE over the 16 bars after entry (ATR15 units), and the share reaching +1 ATR15 before -1 ATR15
from the entry within 16 bars (same bar = loss; neither = reported separately). Reference row: 24-bar breaks WITHOUT
momentum (true range < 1.0 x ATR15).

**Overlap to report:** the engine already reads `cs_used_x` (today's range / the 14-day average high-low range, card
"Candle size and realistic targets"), `tq_sq_release` and `tq_bos` (card "Trend quality and squeeze") and `id_or`
(opening-range position, card "Intraday levels"). H7 (breakout trap) faded first closes beyond the 48-bar / prior-day /
swing levels; H44 trades WITH the break and only with momentum.

**Prior, stated now:** 15m breakouts have been near zero before costs in this project's earlier tests (H7 faded them
and lost about the cost); with a stop of about one 15m ATR the crypto round-trip fee is a large share of 1R. I do not
expect a pass; the descriptive table is the main deliverable. Code: `research/rangebreak_study.py`, report
`research/out/rangebreak/study.md` + `.json`; reading-only card `engine15/sources/adr.py` (not wired).

### H44 results (16 Nov 2026, ~04:50 UTC; development data to 2025-11-11; `research/out/rangebreak/study.md`)

**NO PASS.** Code: `research/rangebreak_study.py` (readings and the break definition from `engine15/sources/adr.py`,
trades through `playbook.simulate` unchanged). Truncation check on real bars: 0 mismatched runs (726,536 signals compared
over 8 markets x 13 rules x 2 cuts); `tests/test_rangebreak.py` checks the signal function the same way on synthetic
24h and cash-hours bars. Variants tried: 8 (+5 no-eagle twins as controls). Holdout not touched.

Chosen on the first half: **V4** (first close beyond the prior UTC day's high/low on a bar >= 1.5 x ATR15, day used
< 65% of its daily ATR, half 1R / rest 2R), score -0.074% a trade (V1-V6 scores ran from -0.091% to -0.074%: all
negative after costs). First half pooled: 4,946 trades, 47.0% won, +0.04R before / -0.31R after costs, -0.077% a trade,
PF 0.61, net -$38,018. **Second half pooled: 3,504 trades, 40.0% won, -0.04R before / -0.51R after costs, -0.106% a
trade, PF 0.38, net -$37,093; negative in all 8 markets.** Its no-eagle twin (same rule, no daily filter): 5,575
trades, -0.108% a trade, net -$59,909. Bar: pooled positive NO; >= 5 of 8 markets NO (0); PF >= 1.1 NO; better per trade
than the twin YES (by 0.002 points, i.e. nothing).

What the daily ATR adds: nothing measurable. Room-left vs no filter, second half per trade: V1 -0.122% vs V8 -0.119%,
V2 -0.124% vs -0.121%, V3 -0.119% vs -0.118%, V4 -0.106% vs -0.108%, V5 -0.107% vs -0.110%, V6 -0.118% vs -0.116%.
The exhausted contrast V7 did NOT lose more before costs (-0.01R second half, +0.02R first) than room-left V1 (-0.04R,
-0.01R); its stops are wider (median 0.35% vs 0.20% of price), so costs take 0.24R instead of 0.45R.

Descriptive, pre-cost, all 2020-2025 dev events (24-bar box, k 1.5): room left (n 29,180) forward 16 bars +0.03 ATR15,
+1 ATR before -1 ATR 48.7%; middle (13,491) +0.01, 48.6%; exhausted (9,852) +0.10, 49.6%; MFE 2.6-2.8 vs MAE 2.3-2.6
ATR15 over 16 bars. Every range (12/24-bar, prior day, opening range) and k 2.0 looks the same: a coin flip, and if
anything the reverse of the hypothesis (exhausted breaks slightly better), small and not steady across halves. The one
visible pattern is in the reference row: 24-bar breaks WITHOUT momentum on an exhausted day drifted back (-0.22 ATR15
at 16 bars, 41% hit, first half; -0.06, 47% second half), not registered and not claimed.

Why it fails as a trade: no gross edge, and a stop of one 15m ATR is small (median 0.2% of price), so the fee is
0.3-0.45R a trade (crypto ~0.6R). Overlap: `cs_used_x` already reads the same "share of the day used" idea; H44's new
pieces (room left per direction, the momentum-break flag) carry no history edge either. Nothing goes forward as a book.
As the owner asked for data points, the reading-only card `engine15/sources/adr.py` ("Daily range budget and range
breaks", voice `adr`, all eight markets) is built and tested but NOT wired into `sources.MODULES`; a live scan
(`py -3 research/rangebreak_study.py --scan`) lists current breaks with their daily-ATR context, labelled untested.

## H45. Daily range breaks traded with a DAILY-sized trade (registered 16 Nov 2026, 04:58 UTC, before any H45 code existed or any H45 number was computed)

**Prompted by:** H44 (every H44 trade was 15m-sized: stop 1 x ATR15, targets 1R/2R, hold 4 h) and the owner's question
about breaks of the 24-hour / daily range; the owner agreed ("Yes", 16 Nov 2026) to test a DAILY breakout traded with a
DAILY-sized trade.

**Definitions (fixed now).** Daily ATR = Wilder ATR(14) on UTC daily bars, the value of the last CLOSED day (through
`data.htf_on_15`, held for the whole UTC day; `engine15/sources/adr.py` `readings`, the same code as H44). Levels:
(a) **pday** = the prior UTC day's high / low; (b) **roll24** = the high / low of the previous 96 15m bars, known at the
previous bar's close. **Daily break** = the FIRST 15m close beyond the level in that UTC day, per direction (a close
above the level for up, below for down; one up and one down event at most per level per day). **With momentum** = that
first close is on a bar whose true range is >= 1.5 x ATR(14, 15m) of the bar before (H44's condition); if the first
close is not a momentum bar there is no momentum event that day (a later close does not count). **used** = (today's
high - low so far, the break bar included) / daily ATR; buckets room left < 0.65, middle 0.65-1.0, exhausted >= 1.0.

**The trade (common frame).** Decision at the break bar's close; entry at the next 15m open, only if that bar is in the
same UTC day as the break (else no trade); a fill gapping beyond the stop is not taken. One position per market at a
time ($10,000 a trade), the market's own fee a side (`playbook.fee_side`). Inside a bar the stop is checked first; an
open beyond the stop or the target fills at that open. A minimal simulator in the study implements this (a single
stop, a single target, a per-trade exit bar) because `playbook.simulate` always splits half at T1 with a break-even
stop and has one hold length for all signals. Exits:
- **day end**: out at the open of the first bar of a later UTC day than the break (for markets that shut, the next
  session's first open; Friday -> Monday);
- **3 days**: out at the open of the first bar at or after entry + 72 hours (= 288 bars on 24h markets; by clock so the
  cash-hours S&P is not held 11 sessions).
Stops: **S1** = entry -/+ 0.5 x daily ATR; **S2** = the broken level -/+ 0.25 x daily ATR. Targets: **T1** = entry +/-
1.0 x daily ATR; **Troom** = the remaining daily room at the break bar (today's low + 1 daily ATR for a long, today's
high - 1 daily ATR for a short), set to entry +/- 0.25 x daily ATR if it is nearer than that to the entry.

**The variants (8 rule runs in all, every one counted):**

| id | level | momentum | stop | target | exit | daily filter | role |
|---|---|---|---|---|---|---|---|
| D1 | pday | yes | S1 | Troom | day end | room left (used < 0.65) | candidate |
| D2 | roll24 | yes | S1 | Troom | day end | room left | candidate |
| D3 | pday | NO (every first close) | S1 | Troom | day end | room left | candidate |
| D4 | pday | yes | S2 | T1 | 3 days | room left | candidate |
| D1n-D4n | as D1-D4 | | | | | none | the no-eagle twins (controls, not selectable) |

Count, honestly: H44 ran 6 selectable variants, 1 contrast and 6 no-eagle controls; H45 adds 4 selectable and 4
controls: 10 selectable range-break rules in the H44/H45 family so far.

**Data and split (H44's):** the eight markets, rows before the sealed holdout 2025-11-11 00:00 UTC only (dropped right
after loading). Trades from 2020-01-01 by entry time. First half: entries before 2023-06-07; second half from it to the
seal. **Selection (first half only):** among D1-D4, the highest mean over markets (each with >= 20 first-half trades) of
the first-half expectancy after costs (% of stake a trade), among variants with >= 100 first-half trades pooled; ties
the lower id. **Fixed pass bar (second half, the chosen variant; H44's):** (1) pooled net $ after costs > 0 with >= 100
trades; (2) net > 0 in >= 5 of 8 markets; (3) pooled profit factor >= 1.1; (4) pooled expectancy per trade higher than
its no-eagle twin's. A pass is a reason to ask the owner about a forward paper book, not proof; no live book is built.

**Descriptive (reported whatever the result; pre-cost, events not trades, overlaps allowed):** for every daily break
(both levels, all first closes and the momentum subset, no daily filter): forward move in the break direction from the
next open to the close of the break's UTC day, to 24 h and to 72 h after entry, in daily-ATR units; the share reaching
+0.5 and +1.0 daily ATR before -0.5 daily ATR within 72 h (same bar = loss; neither reported apart), and +0.5 before
-0.5 by the day's end; split by bucket (room left / middle / exhausted), by market group (crypto, metals, fx, index,
energy) and by half.

**Prior, stated now:** with a stop of half a daily ATR the fee is a small share of 1R (crypto ~0.1-0.15R), so costs
will not decide it; the gross edge will. H44 found no gross continuation over 4 hours; a day-end or 3-day horizon is a
different question. I expect a small or no gross edge and no pass. Code `research/dailybreak_study.py`, test
`tests/test_dailybreak.py`, report `research/out/dailybreak/study.md` + `.json`.

### H45 results (16 Nov 2026, ~05:10 UTC; development data to 2025-11-11; `research/out/dailybreak/study.md`)

**NO PASS.** Code: `research/dailybreak_study.py` (levels and the daily ATR from `engine15/sources/adr.py` `readings`;
a minimal single-stop / single-target simulator with the playbook frame); `tests/test_dailybreak.py` (truncation test of
the signal function on 24h and cash-hours synthetic bars, the event checked by hand, the simulator's frame). Truncation
check on real bars: 0 mismatched runs (119,151 signals compared, 8 markets x 8 rules x 2 cuts). Variants: 4 selectable +
4 no-eagle controls (family so far: 10 selectable, 1 contrast, 10 controls). Holdout not touched.

All four candidates lost after costs in both halves (first-half scores -0.074% to -0.112% a trade). Chosen on the first
half: **D4** (first close beyond the prior UTC day's high/low on a momentum bar, day used < 65%, stop at the level -/+
0.25 daily ATR (median 0.31 dATR), target 1 daily ATR, out after 72 h). First half pooled: 2,764 trades, 28.5% won,
+0.00R before / -0.10R after costs, -0.082% a trade, PF 0.91, net -$22,595. **Second half pooled: 1,874 trades, 25.7%
won, -0.08R before / -0.20R after costs, -0.210% a trade, PF 0.69, net -$39,333; net > 0 in 0 of 8 markets** (gold
-$3 and USDJPY -$37 closest). Its twin D4n (no daily filter): 2,756 trades, -0.173% a trade, net -$47,778. Bar: pooled
positive NO; >= 5 markets NO; PF NO; better than the twin NO.

The day-end variants did not do better: D1 (pday, momentum, stop 0.5 dATR, target the day's remaining room, out at the
next UTC day's open) second half -0.171% a trade, -0.04R before costs; D2 (rolling 24 h) -0.191%; D3 (no momentum)
-0.132%. The room-left filter made every candidate WORSE per trade than its twin in the second half (D1 -0.171% vs D1n
-0.130%, D2 -0.191% vs -0.129%, D3 -0.132% vs -0.108%, D4 -0.210% vs -0.173%). Costs are now small (crypto ~0.1R), so
the loss is the absence of gross edge (R before costs -0.08 to +0.05 everywhere).

Descriptive (pre-cost events, no filter, 2020-2025 dev, 12,430 prior-day breaks / 8,404 with momentum; rolling-24h
similar): forward move in the break direction to the day's close +0.01 dATR, at 24 h +0.00-0.02, at 72 h +0.04-0.05
(up/down events pooled; not separated from the period's drift); share positive at the day's close 49%, at 72 h 50%.
+0.5 before -0.5 dATR within 72 h: 47% of events (49.5% of resolved; a driftless walk gives 50%); +1.0 before -0.5:
26% (30% of resolved; walk 33%). Room left vs middle vs exhausted (momentum, prior day): to day close -0.00 / +0.02 /
+0.05, at 72 h +0.02 / +0.08 / +0.13, +0.5 before -0.5 46% / 49% / 52%: if anything the REVERSE of the eagle-view idea
(the same as H44), small, from 1,085 exhausted events, not steady across halves. By group no market group continues
at the day's close by more than 0.04 dATR (crypto +0.04, energy -0.02). A daily break, on its own, is a coin flip at
the day's close and over 1-3 days in this history. Nothing goes forward as a book; the live scan
(`py -3 research/dailybreak_study.py --scan`) is labelled paper / untested.
