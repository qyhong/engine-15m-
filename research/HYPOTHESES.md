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

## H46. Momentum / speed / participation CONFLUENCE at a daily-level break (registered 16 Nov 2026, 05:11 UTC, before any H46 code existed or any H46 outcome was computed)

**Prompted by:** H44 and H45 (a daily-level break on its own is a coin flip: +0.5 before -0.5 daily ATR in ~49.5% of
resolved events) and the owner, 16 Nov 2026: "Check on any indicators that can measure speed or momentum. I think need
confluence. Not just price exceed previous day high or low." and "the momentum or how it exceed it and there are higher
than 70% probability setup that it will continue to trend".

**Question:** does a CONFLUENCE of momentum / speed / participation conditions at the moment of a daily-level break pick
out setups that continue (+0.5 before -0.5 daily ATR) with >= 70% probability?

**Events (H45's code, `dailybreak_study.daily_breaks`, momentum condition OFF):** every FIRST 15m close beyond the
level in its UTC day, per direction (s = +1 up, -1 down), at most one up and one down event per level per day, eight
markets (BTCUSDT, ETHUSDT, XAUUSD, XAGUSD, USDJPY, SPX, WTI, BRENT). Two levels, analysed separately: **pday** = the
prior UTC day's high / low; **roll24** = the high / low of the previous 96 15m bars. Daily ATR D = Wilder ATR(14) of
the last CLOSED UTC day, held for the day (`engine15/sources/adr.py` `readings`, as H44/H45). The event bar i is the
break bar; an event needs D > 0 and its entry bar i+1 in the same UTC day (else excluded, counted).

**Outcome (the primary metric, pre-cost):** entry = open of bar i+1. Hit = price reaches entry + s x 0.5 D (high for up,
low for down) BEFORE it reaches entry - s x 0.5 D, using bars from i+1 to the last bar opening before entry + 72 h (by
clock). A bar touching both = a miss (H45's convention, slightly below 50% for a driftless walk). Neither within 72 h =
unresolved: excluded from hit rates and counted. Hit rate = hits / resolved. Chance ~50%.

**Confluence groups (each a yes/no at the break bar's CLOSE, closed bars only; 1h / 4h / 1d values through
`data.htf_on_15`, so a 1h bar is used only once it has closed, which can include the break bar itself; "no read" =
does not confirm):**
1. **SPEED:** r1h = ln(close_i / close_{i-4}) (the last 4 bars on file); sd1h = the standard deviation of r1h over
   the last 2,880 bars on file ending at i (min 672). Confirms if s x r1h >= 1.0 x sd1h, OR the break bar's true range
   >= 1.5 x ATR(14, 15m) of the bar before (H44/H45's momentum bar).
2. **TREND STRENGTH (1h):** on closed 1h bars, Wilder ADX(14) / +DI / -DI (`engine15/sources/ltf.py` `adx`) and the
   MACD(12, 26, 9) histogram (`ltf.macd_hist`). Confirms if (ADX >= 20 AND ADX > the previous 1h bar's ADX AND
   s x (+DI - -DI) > 0) OR (s x hist > 0 AND s x (hist - previous 1h hist) > 0).
3. **OSCILLATOR:** RSI(14) (`indicators.rsi`, first 14 bars masked) on closed 1h and closed 4h bars. Confirms if
   s x (RSI1h - 50) > 10 (RSI1h > 60 up, < 40 down) AND NOT s x (RSI4h - 50) > 30 (RSI4h not > 80 up, not < 20 down;
   a missing 4h RSI = no read).
4. **PARTICIPATION:** vol_x = the break bar's volume / the median volume of the same 15m clock slot (UTC) over the
   previous 20 days on file that have that slot (min 10; today excluded). Confirms if vol_x >= 2.0; on crypto also the
   taker-buy share taker_buy / volume of the break bar > 0.5 for up (< 0.5 for down). A zero / missing median or
   volume = no read (USDJPY's volume is 0 after its source join; the other non-crypto volumes change source at their
   join, VOLUME_NOTE, so vol_x is distorted for ~20 days there).
5. **SQUEEZE RELEASE (15m, ltf.py trendq's definition):** Bollinger(20, 2, population sd) both bands inside Keltner
   (same 20-bar mean +/- 1.5 x the 20-bar mean true range) = squeeze ON; release = a bar with the squeeze OFF after a
   bar with it ON. Confirms if the squeeze is OFF at bar i and the last release is at most 8 bars before i (0-8,
   i.e. ltf's tq_sq_bars_since <= 8). Direction is not required.
6. **HTF ALIGNMENT:** the engine's trend-map score (`indicators.trend_score`, -1..+1) on closed 4h bars and on closed
   UTC daily bars. Confirms if s x score4h > 0 AND s x score1d > 0 (both lean the break's way).
7. **LEVERAGE (crypto only, BTCUSDT from Sep 2020, ETHUSDT from Dec 2021):** Binance archive open interest
   (`data/sources/flows_metrics_<coin>.csv`, column oi, 15m snapshots read as data, the file is not modified).
   oi_now = the snapshot stamped at the break bar's OPEN time (15 minutes before its close: conservative), oi_4h = the
   snapshot 4 h earlier. Confirms if ln(oi_now / oi_4h) > 0 (open interest rising into the break, whichever side).
   CAVEAT stated now: the archive file of day D is published ~12 h after D ends (flows.py known_ms), so the LIVE engine
   could NOT read this in real time; it describes what a live open-interest feed (which the engine does not have)
   would have shown. Non-crypto events and crypto events before the archive = no read.

**COUNT** = the number of confirming groups (0-6; 0-7 on crypto with an OI read).

**The search (fixed now):** per level and per scope, 32 buckets: COUNT >= 3, >= 4, >= 5, = all (every group that has a
read for that event confirms: 6 of 6, or 7 of 7 on crypto with OI); each of the 7 groups alone; each of the 21 pairs of
groups (both confirm). Scopes: pooled over the 8 markets + each of the 5 market groups (crypto, metals, fx, index,
energy) = 6. **Multiple-testing count: 32 x 2 levels x 6 scopes = 384 buckets** (buckets that are empty in a scope,
e.g. group 7 outside crypto, are still counted: conservative). Bonferroni threshold per half: p < 0.05 / 384 = 1.30e-4.
Reference row (not a test): every event of the level.

**Data and split (H44/H45's):** rows before the sealed holdout 2025-11-11 00:00 UTC only (dropped right after loading,
never read); events with entry from 2020-01-01; first half = entry before 2023-06-07, second half = from it to the seal.

**"70% setup" (declared only if ALL hold for a bucket in a scope and level):** in BOTH halves the hit rate >= 70% with
>= 100 resolved events, AND the two-sided exact binomial p-value against 50% < 1.30e-4 in BOTH halves. Every bucket's
hit rate, n (resolved), unresolved count and p per half is reported anyway, sorted, with the lift over the level's
reference row. A pass would be described precisely so it could be registered as a forward PAPER book after asking the
owner; no live book is built here.

**After costs (descriptive, for the top buckets):** the top buckets = the 10 pooled buckets (either level) with the
highest LOWER-of-two-halves hit rate among those with >= 100 resolved events in each half, plus any 70% setup. Each is
traded: entry at the next 15m open (same UTC day only; a fill gapping beyond the stop is not taken), stop entry - s x
0.5 D, target entry + s x 0.5 D, out at the first open at or after entry + 72 h, stop first inside a bar, gaps fill at
the open, one position per market at a time, $10,000 a trade, each market's own fee a side (`playbook.fee_side`):
trades, win %, R before / after costs, % of stake a trade, net $, per half and per market; and events per month.

**Look-ahead guard:** `tests/test_confluence.py` truncates synthetic 24h and cash-hours bars (with volume, taker-buy and
an OI frame) and checks the event + confluence function gives the same rows and the same group flags on every row
before the cut; the same truncation check runs on the real bars of every market; the squeeze flag is cross-checked
against `ltf.features`' tq_sq_bars_since. No feature may use a bar after the break bar.

**Prior, stated now:** every momentum reading here has been near-useless as a single predictor in this project (H44,
H45, the card ratings). Conditioning on strong momentum usually raises continuation by a few points at most, and
crowded breaks often mean-revert. The honest expectation is that no bucket reaches 70% in either half, let alone both;
the best buckets may sit at 52-56%. Code `research/confluence_study.py`, report `research/out/confluence/study.md` +
`.json`, test `tests/test_confluence.py`.

## H47. REGIME SPLIT: do daily-level breaks continue in trending regimes and fail in ranging ones? (registered 16 Nov 2026, 05:40 UTC, before any H47 code existed or any H47 outcome was computed)

**Prompted by:** H44-H46 (the first 15m close beyond the prior-day or rolling-24h level reaches +0.5 daily ATR before
-0.5 daily ATR in ~50% of resolved events, and no momentum / participation confluence lifts it above ~51-54%). The
owner approved this test on 16 Nov 2026: breaks may CONTINUE in trending regimes and FAIL in ranging ones, so the two
cancel to ~50% when pooled.

**Events and outcome: identical to H46.** Every first 15m close beyond the level in its UTC day per direction
(s = +1 up, -1 down; `dailybreak_study.daily_breaks`, momentum OFF), levels **pday** (prior UTC day's high / low) and
**roll24** (previous 96 bars' high / low), daily ATR D from `engine15/sources/adr.py` `readings` (last closed day),
D > 0 and entry bar in the same UTC day. **Follow hit** = +0.5 D in the break direction before -0.5 D from the next 15m
open within 72 h (`confluence_study.outcome(R, i, s, D)` unchanged; a bar touching both = miss; neither = unresolved,
excluded, counted). **Fade hit** = the same event traded against the break: -0.5 D (in the break direction) before
+0.5 D, computed as `confluence_study.outcome(R, i, -s, D)` (so a bar touching both is a miss for the fade too, and
follow hits + fade hits <= resolved). Eight markets, rows before 2025-11-11 only (dropped right after loading), entries
from 2020-01-01, first half before 2023-06-07, second half from it to the seal.

**Regime measures (all on closed UTC daily bars from `data.resample(df15, "1D")`, joined with `data.htf_on_15`, so a
15m row sees only days that had closed by its own close; recomputed here, no live output read):**
- **R1, the engine's own regime label** (`indicators.regime_daily`, exactly as evidence.py's `regime` column). 7
  buckets: R1a TREND aligned (TREND_UP on an up break or TREND_DOWN on a down break); R1b TREND counter; R1c MOMENTUM
  aligned; R1d MOMENTUM counter; R1e TRENDING any (any TREND_* or MOMENTUM_* label, either direction); R1f RANGE;
  R1g TRANSITION. No label (first 209 daily bars) = no read, counted.
- **R2, daily ADX(14)** (Wilder, `engine15/sources/ltf.py` `adx` on the daily bars), DI alignment = s x (+DI - -DI) > 0.
  5 buckets: R2a ADX >= 25; R2b ADX >= 25 and DI aligned; R2c ADX >= 25 and DI counter; R2d 20 <= ADX < 25; R2e ADX < 20.
- **R3, Kaufman efficiency ratio over the last 20 daily closes**: ER = |C_t - C_t-20| / sum of |C_k - C_k-1| over the
  20 steps (regime_daily's er); direction = sign(C_t - C_t-20). Tercile cutoffs = the 33.3 / 66.7 percentiles of ER
  over FIRST-HALF events only (both levels, all markets pooled; values only, no outcomes), then fixed. 5 buckets:
  R3a high tercile; R3b high and aligned with the break; R3c high and counter; R3d middle; R3e low.
- **R4, realised-volatility percentile**: rv20 = standard deviation of the last 20 daily log returns; pct = rank of
  today's rv20 among the last 250 daily rv20 values (incl. today's; pandas rolling(250).rank(pct=True)). Terciles on
  first-half events as R3. 3 buckets: R4a high, R4b middle, R4c low.
- **R5, variance ratio (persistence)**: VR(5) = variance of the overlapping 5-day log-return sums / (5 x variance of the
  1-day log returns), over the last 250 daily returns (246 sums); VR > 1 = trending / persistent, < 1 = mean
  reverting. Terciles on first-half events as R3. 3 buckets: R5a high, R5b middle, R5c low.

**Count.** 23 buckets (7 + 5 + 5 + 3 + 3), each tested on 2 sides (follow, fade) x 2 levels x 6 scopes (pooled + the 5
market groups crypto, metals, fx, index, energy) = **552 tests per half**; Bonferroni threshold per half
p < 0.05 / 552 = 9.06e-5 (exact two-sided binomial against 50%, `confluence_study.binom_p`). Empty cells still count.

**Pass bar (fixed now; evaluated on the POOLED scope of each level, both sides):** a bucket passes if ALL hold: (1) hit
rate >= 55% in BOTH halves; (2) >= 200 resolved events in each half; (3) binomial p < 9.06e-5 in BOTH halves; (4)
traded (entry next 15m open, same UTC day only; the follow trade's stop entry - s x 0.5 D, target entry + s x 0.5 D;
the fade trade the mirror image (side -s); 72 h max, out at the first open at or after entry + 72 h; stop first inside
a bar, gaps fill at the open; one position per market at a time within the bucket; $10,000 a trade; each market's own
fee a side, `playbook.fee_side`; H46's `trades_of`) net $ after costs > 0 in the SECOND half pooled AND net > 0 in at
least 5 of the 8 markets in the second half (a market with no trades is not positive). A pass would be described so it
could be registered as a forward paper book after asking the owner; nothing is built or wired here.

**The core question: does regime explain the 50%?** Per measure the primary contrast is the trend bucket vs the range
bucket on the FOLLOW side: R1e vs R1f, R2a vs R2e, R3a vs R3e, R4a vs R4c (high vs low volatility), R5a vs R5c; per
level, pooled: 10 contrasts per half. Test: two-proportion z test (pooled variance), two-sided. "Regime explains" a
measure's split only if the difference has the same sign in both halves and p < 0.05 / 10 = 0.005 in BOTH halves; the
size of the difference (points) is reported either way, and also per market group (descriptive). Secondary,
descriptive: aligned vs counter within the trend buckets (R1a vs R1b, R2b vs R2c, R3b vs R3c).

**Reported whatever the result:** every bucket's follow and fade hit rate, resolved n, unresolved count and p per half,
pooled and per market group, per level; every pooled bucket traded both sides (trades, win %, R before / after costs,
% of stake a trade, net $ per half, per market in the second half, events per month); event counts without a regime
read. Sanity check: the reference (all events) must reproduce H46's reference hit rates.

**Look-ahead guard:** `tests/test_regime_split.py` truncates synthetic 24h and cash-hours bars and checks every regime
array (label, ADX, DI, ER, direction, rv percentile, VR) is identical on every row before the cut; the same check runs
on the real bars of every market in the study; the R1 label is cross-checked against evidence.py's join recipe.

**Prior, stated now:** H44-H46 found no lift from any momentum-type condition, and the daily trend-map alignment (H46
group 6, a cousin of these measures) moved the hit rate by under 1 point. Regime filters often look better in theory
than in 15m-to-3-day data. I expect trend-vs-range differences of 0-3 points, not significant in both halves, and no
bucket at 55%. Code `research/regime_split_study.py`, report `research/out/regime_split/study.md` + `.json`.

### H47 results (16 Nov 2026, ~05:45 UTC; development data to 2025-11-11; `research/out/regime_split/study.md`)

**NO PASS, and regime does not explain the 50%.** Code `research/regime_split_study.py` (events, outcome, binomial test
and trade bookkeeping reused from H45/H46); `tests/test_regime_split.py` (truncation of every regime array on 24h and
cash-hours synthetic bars, ER and VR recomputed by hand from closed days only, R1 equal to evidence.py's recipe, fade =
mirror of follow, bucket logic). Real bars: 0 mismatched regime arrays (8 markets x 2 cuts), 0 R1 mismatches against
the evidence.py recipe. 25,196 events (the reference reproduces H46's table exactly: pday pooled follow 49.1% of 6,916
/ 50.0% of 4,919). No-read events: only the volatility percentile on SPX (18 / 12) and Brent (10 / 10). Tests: 552
per half (23 buckets x 2 sides x 2 levels x 6 scopes), Bonferroni 9.06e-5. Holdout not touched. Tercile cutoffs
(first half): ER 0.137 / 0.305; volatility percentile 0.320 / 0.664; VR(5) 0.884 / 0.983.

**Core question (follow side, pooled, trend bucket minus range bucket, first / second half):** R1 engine label
(TRENDING any vs RANGE) pday +0.0 / -1.9 points, roll24 -0.3 / -2.3; R2 daily ADX >= 25 vs < 20 pday -2.7 (p 0.048) /
-0.8, roll24 -2.3 / -1.2; R3 ER high vs low tercile pday -0.1 / -3.0, roll24 -0.4 / -1.3; R4 high vs low volatility
pday -1.4 / -4.0 (p 0.019), roll24 -1.9 / -2.9; R5 VR high vs low pday -0.5 / -2.5, roll24 -0.9 / -2.1. **0 of 10
contrasts significant in both halves** (none even nominally p < 0.05 in both). Where there is a lean, it is the
REVERSE of the hypothesis: breaks in trending / high-ADX / high-volatility regimes continued slightly LESS often (about
48-49.5%) than breaks in quiet / ranging regimes (about 50-52%). Hit rates (follow, first / second half, pday): R1e
trending 49.4% / 48.7%, R1f RANGE 49.4% / 50.6%; R2a ADX >= 25 48.4% / 49.7%, R2e ADX < 20 51.1% / 50.5%; R4a high vol
48.5% / 47.5%, R4c low vol 49.9% / 51.5%. So "fade in range" is not there either: fade in RANGE 50.6% / 49.3%, fade
at ADX < 20 48.9% / 49.4%.

Direction within trend (descriptive): breaks aligned with the trend did a little better than counter-trend breaks in
the first half (R1a vs R1b +2.5 / +4.5 points, R3b vs R3c +4.8 / +4.3), not in the second (+4.0 / +1.6, -0.7 / +0.1),
nothing significant. Per market group a few single cells reach p < 0.01 (crypto R4 second half -9.9; fx R3 roll24
second half -14.8, R5 roll24 -11.9 / -14.0), all from small samples among 50 group contrasts (100 half-cells), none significant in both halves.

Best pooled bucket by the lower half: roll24 R1b (TREND label counter to the break) FADED, 52.2% of 523 / 52.7% of
355, far below 55% and the n bar. Buckets passing Bonferroni in both halves: 0 of 552. After costs (stop and target
0.5 daily ATR, 72 h, own fee, one position per market) no bucket on either side is positive in >= 5 of 8 markets in
the second half; the best pooled second-half results are pday R1d fade +0.030% a trade (55 trades), roll24 R1a fade
+0.007% (442), pday R1b fade +0.002% (345), i.e. zero. Every other bucket loses (follow -0.02% to -0.33%, fade
-0.004% to -0.23% a trade).

Reading: in this history a daily-level break is ~50/50 in every regime these five measures can name; the pooled 50% is
not two opposite halves cancelling. Nothing goes forward as a book. The live scan (`py -3
research/regime_split_study.py --scan`) prints each market's regime readings and today's breaks with their buckets,
labelled paper / untested.

## H48. FX AND SESSION TIMING: FX daily-break continuation out of family, and session-range breakouts (registered 16 Nov 2026, 05:55 UTC, before any H48 code existed or any H48 outcome was computed)

**Prompted by:** H46/H47. Daily-level breaks continued ~50% in every market group except FX (USDJPY): prior-day
breaks 53.3% / 53.3% (p 0.058 / 0.115) and rolling-24h 54.9% / 54.2% (p 0.004 / 0.039) on the symmetric +0.5 vs -0.5
daily ATR outcome, first / second half. That lean was found among 384 + 552 tests, so it may be noise. The owner
approved H48 (16 Nov 2026): (A) is the FX lean real out of family, steady, and tradeable after costs; (B) do
SESSION-range breakouts (Asia range into London, pre-New York ranges into New York, the index opening range)
continue where whole-day breaks do not?

**Related earlier tests (disclosed, same family):** H12 (Asian range broken in the first 4 h after the London open,
gold and USDJPY, stop at the far side of the range, 3R; history ~+0.03-0.05R before costs, negative after; a forward
shadow book) and H8 (30-minute opening range breakout, 130 variants in playbook2; nothing positive after costs).
H48 re-asks those questions on the symmetric daily-ATR outcome, not their trade designs. Range-break family so far:
H44-H47 (10 selectable rules, 384 + 552 bucket tests) plus H8/H12's variants.

**Data.** Engine files (`data.load`, the H45 loader `rangebreak_study.load_dev`): USDJPY, XAUUSD, XAGUSD, SPX, WTI,
BRENT. Extra out-of-family markets read READ-ONLY from the Kronos store (`C:\tmp\kronos\data\markets\<ID>\15m.csv.gz`,
Dukascopy BID 15m built from 1m, UTC open times; read with pandas, nothing written there): **USDSGD** (24h FX) and
**NDX** (Nasdaq-100 CFD, restricted to the NYSE cash session with `extdata.open_mask("SPX", ...)`, the engine's own
SPX filter). Pre-check (structure only, no outcome): both files monotonic, no duplicates, all stamps on the 15m grid,
no OHLC violations, a median 96 (USDSGD) / 89 (NDX CFD) bars per weekday 2020-2025. Rows at or after the seal
2025-11-11 00:00 UTC are dropped right after loading. Events with entry from 2020-01-01; first half = entry before
2023-06-07, second half = from it to the seal (H44-H47's split). Fees a side: config's (`playbook.fee_side`; USDJPY
0.01%, XAU 0.02%, XAG 0.03%, SPX 0.02%, oil 0.04%); USDSGD 0.015% (my choice: wider spread than USDJPY); NDX 0.02%
(as SPX). No new data is fetched from the internet.

**Daily ATR D** = Wilder ATR(14) of the last CLOSED UTC day, held for the day (`engine15/sources/adr.py` `readings`,
as H44-H47). An event needs D > 0 and its entry bar (the next bar) in the same UTC day.

**The variants (7 in all, every one counted):**

| id | event | markets | outcome window / trade time exit |
|---|---|---|---|
| A1 | H46 pday event: first 15m close beyond the prior UTC day's high/low, per direction per day (`dailybreak_study.daily_breaks`, momentum off) | USDJPY, USDSGD | 72 h |
| A2 | H46 roll24 event: same with the previous 96 bars' high/low | USDJPY, USDSGD | 72 h |
| B1 | Asia range = high/low of bars opening 00:00-06:45 UTC that day (needs >= 14 of 28 bars); event = first 15m close above / below it among bars opening 07:00-09:45 UTC (closes 07:15-10:00), per direction | USDJPY, USDSGD, XAUUSD, XAGUSD, WTI, BRENT | rest of the UTC day |
| B2 | pre-NY range = bars opening 00:00-13:15 UTC (>= 27 of 54); event window bars opening 13:30-15:45 UTC | same 6 | rest of the UTC day |
| B3 | London range = bars opening 07:00-13:15 UTC (>= 13 of 26); event window bars opening 13:30-15:45 UTC | same 6 | rest of the UTC day |
| B4 | index opening range, 30 min = the cash session's first 2 bars (the day counts only if its first bar opens at 09:30 New York); event window = session bars 3-10 (closes up to open + 2 h 30) | SPX, NDX | rest of the UTC day (= the session) |
| B5 | index opening range, 60 min = the first 4 bars; event window = session bars 5-10 | SPX, NDX | rest of the UTC day |

B4/B5 anchor on the real cash open (14:30 UTC in US winter, 13:30 UTC in US summer time), not a fixed 14:30 UTC, which
would sit an hour into the session for eight months a year; the event window is then 2.5 h from the open, the same
length as B2/B3's 13:30-16:00 UTC window. Every range is complete (its last bar closed) before the first bar of its
event window closes; an event is decided at its bar's close.

**Outcome (primary, pre-cost).** Entry = open of the next bar (same UTC day, else no event). Hit = price reaches
entry + s x X before entry - s x X (s = +1 up, -1 down), X = 0.5 x D; a bar touching both = miss; neither within the
window = unresolved, excluded and counted. A: bars from entry to the last bar opening before entry + 72 h
(`confluence_study.outcome`, H46's exactly). B: bars from entry to the last bar of the break's UTC day. Secondary,
descriptive only, not counted: the same with X = 0.25 x D.

**The trade (after costs).** Entry at the next open, stop entry - s x 0.5 D, target entry + s x 0.5 D, stop first
inside a bar, an open beyond either fills at that open; time exit A: the first open at or after entry + 72 h
(H46's `trades_of`); B: the close of the last bar of the break's UTC day. One position per market at a time per
variant, $10,000 a trade, the market's own fee a side.

**Count and test.** Per half, each variant's pooled cell plus one cell per market is a test: A1 3, A2 3, B1 7, B2 7,
B3 7, B4 3, B5 3 = **33 tests per half**; Bonferroni threshold p < 0.05 / 33 = 1.52e-3 (exact two-sided binomial
against 50%, `confluence_study.binom_p`).

**Fixed pass bar (each variant, on its POOLED cell):** (1) hit rate >= 55% in BOTH halves; (2) >= 200 resolved events
in each half; (3) p < 1.52e-3 in BOTH halves; (4) the trade's net $ after costs > 0 in the second half pooled AND
net > 0 in a majority (more than half) of its markets in the second half (A, B4, B5: both markets; B1-B3: >= 4 of 6).
USDJPY is where the FX lean was found, so A's pooled cell is not independent of H46: USDSGD alone is the genuine
out-of-family check and is reported apart (condition 4 already requires it to be positive after costs). A pass
would be described precisely enough to register as a forward paper book after asking the owner; nothing is built.

**Descriptive (reported whatever the result, not counted):** A: hit rate by calendar year and by direction (up vs down
breaks), per market and pooled, per half; B: the X = 0.25 D hit rates; for the passing variant (or, if none passes,
the best = highest lower-of-two-halves pooled hit rate with >= 200 resolved per half): hit rate by weekday and by
month of the year, trades a month; DST: B1-B3 recomputed with the same clock windows read in London local time
(Europe/London), and the UTC results split by London winter (GMT) / summer (BST); B4/B5 split by US winter / summer.

**Look-ahead guard:** `tests/test_session_break.py` truncates synthetic 24h and cash-hours bars and checks the event
function gives the same events and range values on every row before the cut, checks by hand that each range uses only
bars of its own window and that the event bar opens inside the event window after the range is complete, and that
the generic outcome equals `confluence_study.outcome` for the 72 h case. The same truncation check runs on every real
market. Live scan for today, labelled paper / untested.

**Prior, stated now:** H12's history put Asian-range breakouts at a few hundredths of an R before costs; the USDJPY
lean in H46 was the best of hundreds of cells. I expect A pooled at 51-54% with USDSGD nearer 50-52%, no B variant
at 55% in both halves, and no pass. Code `research/session_break_study.py`, report `research/out/session_break/study.md`
+ `.json`.

### H48 results (16 Nov 2026, ~06:00 UTC; development data to 2025-11-11; `research/out/session_break/study.md`)

**NO PASS, and the FX lean did not survive out of family.** Code `research/session_break_study.py` (H45's event code,
H46's outcome and trade bookkeeping reused; a generic same-day outcome for B); `tests/test_session_break.py`
(truncation on 24h and DST-spanning cash-hours synthetic bars incl. the London-local windows; the events recomputed
by hand bar by bar with an assert that every range closed before its event bar opened; the opening range anchored on
14:30 UTC before and 13:30 UTC after US DST; the 72 h outcome identical to `confluence_study.outcome`; the same-day
frame). Real bars: 0 mismatched truncation runs on all 8 markets (98,824 events compared). USDSGD and NDX from the
read-only Kronos store were clean and usable (USDSGD 2016-2025 24h; NDX CFD cut to NYSE cash hours, ~26 bars a
session). No data fetched. Holdout not touched. 7 variants, 33 tests per half, Bonferroni 1.52e-3. Sanity: USDJPY
reproduces H46 exactly (pday 53.3% of 875 / 53.3% of 612; roll24 54.9% / 54.2%).

**Pooled hit rates (first / second half, resolved n):** A1 FX prior-day 49.7% (1,803) / 51.6% (1,218); A2 FX
rolling-24h 50.4% (1,858) / 51.6% (1,272); B1 Asia range into London 49.5% (2,719) / 50.1% (1,944); B2 00:00-13:30
range into New York 53.5% (1,177, p 0.017) / 52.1% (964, p 0.21); B3 London range into New York 53.2% (1,423,
p 0.017) / 51.6% (1,138); B4 index 30-min opening range 49.4% (806) / 48.4% (616); B5 60-min 48.7% (495) / 49.6%
(377). No variant reached 55% in either half; 0 of 33 cells pass Bonferroni in both halves. B2/B3 resolve only
~40% of events within the day.

**(A) FX steadiness.** USDSGD, the out-of-family check, went the OTHER way: prior-day 46.3% (928) / 50.0% (606),
rolling-24h 46.4% (983) / 49.0% (637); below 50% in 2021-2024 on both levels (44.5-48.6%), 47.9-50.6% in 2020, 52% in 2025. USDJPY stays
steady at 50.6-59.2% in every year 2020-2025 on both levels, but its lean is mostly UP breaks on the prior-day level
(up 56.4% / 55.1%, down 49.4% / 51.1%); on rolling-24h both directions ~54-55%. So the H46 lean is a USDJPY feature
in this window (a strong-trend dollar-yen period), not an FX one. After costs (stop/target 0.5 daily ATR, 72 h):
A1 second half pooled -0.011% a trade (977 trades), USDJPY +0.009% (485, +$426), USDSGD -0.031% (-$1,518); A2
pooled -0.016%, USDJPY +0.011% (+$575), USDSGD -0.042%. USDJPY alone is about break-even after its 0.01% fee.

**(B) Session breaks.** USDJPY again leads (B2 61.1% / 55.5%, B3 60.9% / 55.1%, small n 110-190 a half), silver
57.8-58.0% / 54.8-56.4%; USDSGD 41-49% (B2/B3), oil 48-55%. After costs every B variant loses in the second half pooled (B1 -0.086%,
B2 -0.025%, B3 -0.036%, B4 -0.034%, B5 -0.024% a trade); markets positive: B1 USDJPY only, B2 silver only, B3 none,
B4/B5 none. Gross R is +0.01 to +0.03 at best (B2/B3/B4/B5), eaten by costs. X = 0.25 daily ATR (descriptive):
48.6-52.1% everywhere pooled.

**Descriptive extras.** Best variant (not passing) B2: weekday 50.2-54.8%, months 44.6-72.0% (May 72% of 132, noise
level). DST: London-local windows give B1 49.3% / 50.2%, B2 51.1% / 51.5%, B3 51.3% / 51.5% (slightly lower than UTC),
BST vs GMT within 1-2 points. Index opening range in US winter time continued less (B4 45.9% / 38.5%, B5 46.3% /
35.2%, p 0.003 in the second half on 108-174 events) than in summer (51.6% / 52.3%): one of ~20 descriptive splits,
not counted, not significant after any correction; worth noting, not acting on.

Reading: a session-range break, like a daily one, is a coin flip pooled; the only persistent lean in the whole
H44-H48 family is USDJPY's, and it does not carry to USDSGD, so it should be read as one market's history, not an
FX rule, and it does not pay its costs. Nothing goes forward as a book. Live scan `py -3
research/session_break_study.py --scan` (paper / untested; USDSGD and NDX scans are stale because the Kronos store
ends 5-6 Nov 2026).

## H49. The EXHAUSTION FADE: weak new extremes on a day that has already used its daily ATR (registered 16 Nov 2026, 06:25 UTC, before any H49 code existed or any H49 outcome was computed)

**Prompted by:** H44's descriptive reference row (NOT registered there, not claimed): 24-bar breaks WITHOUT momentum
(true range < 1.0 x ATR15) on a day that had already used >= 100% of its daily ATR drifted back (-0.22 ATR15 at 16
bars, +1 before -1 ATR15 in 41% of events, first half; -0.06 and 47% in the second half). The owner approved H49 on
16 Nov 2026: FADE the weak, late push on an exhausted day. The idea came from looking at H44's table (both halves), so
H49 is a follow-up test of a pattern already seen in this development data, not a fresh out-of-sample test; I state
that now.

**Definitions (fixed now; readings from `engine15/sources/adr.py` `readings`, as H44-H48).** Daily ATR D = Wilder
ATR(14) on UTC daily bars, the value of the last CLOSED day (through `data.htf_on_15`), held for the whole UTC day.
**used** at bar i = (today's high - today's low over today's bars up to and including bar i) / D (adr's `used`; only
bars up to the event bar). ATR15 = Wilder ATR(14) on 15m; **bar_x** = bar i's true range / ATR15 as of bar i-1. Side
s = +1 for an up push (the fade is SHORT), -1 for a down push (the fade is LONG).
- **Level "run" (running day extreme):** bar i's close > the highest high of today's bars BEFORE bar i (up), or < the
  lowest low of today's earlier bars (down). Needs at least one earlier bar today.
- **Level "pday":** a fresh close beyond the prior UTC day's high / low (close_i > pdh and close_{i-1} <= pdh; mirror
  for down), as adr's `breaks('pday')` without the momentum condition.
- **Qualifying bar:** level condition AND used >= U AND bar_x < K (the weak push) AND D > 0 AND ATR15 > 0.
- **Event:** the FIRST qualifying bar of the UTC day per direction (at most one up and one down event per day per
  variant). With **confirmation**, the event is the first qualifying bar of the day per direction whose NEXT bar (same
  UTC day) closes back: for "run" below the push bar's close (up; above for down), for "pday" back inside the level
  (close < pdh up; > pdl down); the decision is then at the confirmation bar's close. The decision bar is called i_dec.
  An event needs its entry bar (i_dec + 1) in the same UTC day; else it is dropped and counted.

**The variants (8, every one counted; there is no selection step: the pass bar applies to each):**

| id | level | exhaustion U | momentum ceiling K | confirmation | stop | target |
|---|---|---|---|---|---|---|
| X1 | run | 1.0 | 1.0 | no | day extreme + 0.25 ATR15 | 0.5 D |
| X2 | run | 1.3 | 1.0 | no | day extreme + 0.25 ATR15 | 0.5 D |
| X3 | run | 1.0 | 0.7 | no | day extreme + 0.25 ATR15 | 0.5 D |
| X4 | run | 1.0 | 1.0 | yes | day extreme + 0.25 ATR15 | 0.5 D |
| X5 | pday | 1.0 | 1.0 | no | day extreme + 0.25 ATR15 | 0.5 D |
| X6 | pday | 1.0 | 1.0 | yes | day extreme + 0.25 ATR15 | 0.5 D |
| X7 | run | 1.0 | 1.0 | no | day extreme + 0.25 D | the day's midpoint |
| X8 | run | 1.3 | 1.0 | yes | day extreme + 0.25 D | the day's midpoint |

X7 has the same events as X1 (only the trade differs), so its hit rate equals X1's; it is still counted as a test.

**The trade (registered, per variant).** Decision at i_dec's close; entry at the next 15m open AGAINST the push (side
-s), only if that bar is in the same UTC day. Day extreme = today's high (up push) / low (down push) up to and
including i_dec. Stop = day extreme + s x 0.25 x ATR15 (ATR15 at i_dec) or + s x 0.25 x D, as the table says.
Target = entry - s x 0.5 x D, or the day's midpoint (today's high + low) / 2 at i_dec; a midpoint nearer than 0.25 D
to the entry is replaced by entry - s x 0.25 D (H45's floor). VWAP is NOT used: USDJPY has no volume after its source
join and the other non-crypto volumes change source (extdata VOLUME_NOTE). A fill that opens beyond the stop is not
taken. Inside a bar the stop is checked first; an open beyond the stop or the target fills at that open. Time exit:
the close of the last bar of the event's UTC day (H48 B's rule; for SPX the cash session's last bar). One position per
market at a time per variant, $10,000 a trade, each market's own fee a side (`playbook.fee_side`).

**Primary statistic (H46's symmetric outcome, mirrored for the fade).** From the entry (next open), fade hit = price
reaches entry - s x 0.5 D before entry + s x 0.5 D, using bars from the entry bar to the last bar of the event's UTC
day (`session_break_study.outcome_window` with side -s). A bar touching both = miss; neither = unresolved, excluded
from the hit rate and counted. Chance ~50% (slightly below for a driftless walk). **Secondary (descriptive, not a
test):** the same over 72 h (`confluence_study.outcome(R, i_dec, -s, D)`, unchanged).

**Data and split (H44-H48's, exactly):** BTCUSDT, ETHUSDT, XAUUSD, XAGUSD, USDJPY, SPX, WTI, BRENT from `data.load`
(`rangebreak_study.load_dev`), rows before the sealed holdout 2025-11-11 00:00 UTC only (dropped right after loading,
never read); events with entry from 2020-01-01; first half = entry before 2023-06-07, second half = from it to the seal.

**Count and test.** Scopes: pooled + the 5 market groups (crypto, metals, fx, index, energy) = 6. Tests per half:
8 variants x 6 scopes = **48**; Bonferroni threshold p < 0.05 / 48 = 1.04e-3 (exact two-sided binomial against 50%,
`confluence_study.binom_p`). Per-market cells and the 72 h outcome are reported with nominal p and are NOT tests (no
condition below reads them). Family so far: H44 (6 selectable + 1 contrast + 6 controls), H45 (4 + 4 controls), H46
(384 bucket tests), H47 (552), H48 (7 variants, 33 tests), H49 (8 variants, 48 tests); earlier related fade: H7
(breakout trap, faded first closes beyond 48-bar / prior-day / swing levels; lost about its costs).

**Fixed pass bar (each variant):** ALL of (1) pooled fade hit rate >= 55% in BOTH halves; (2) >= 200 resolved events
pooled in EACH half; (3) pooled binomial p < 1.04e-3 in BOTH halves; (4) the registered trade, second half: pooled net $
after costs > 0 AND pooled profit factor >= 1.1; (5) in the second half at least 5 of the 8 markets have net $ > 0 AND
profit factor >= 1.1 (a market with no trades does not count). A pass is a reason to ask the owner about a forward
PAPER book, not proof of an edge; nothing is built or wired here. **Reported variant ("chosen"):** among passing
variants the highest lower-of-two-halves pooled hit rate; if none passes, the variant with the highest lower-of-two-
halves pooled hit rate among those with >= 200 resolved per half (for the write-up only).

**Reported whatever the result:** every variant's fade hit rate (day and 72 h), resolved / unresolved counts and p, per
half, pooled, per market group and per market; every variant's trade (trades, win %, R before / after costs, % of stake
a trade, PF, net $) per half pooled, per group and per market; events and trades per month; dropped events.

**Look-ahead guard:** `tests/test_exhaustion.py` truncates synthetic 24h and cash-hours bars and checks the event
function returns the same events (i_dec, side, used, day extreme, stop/target inputs) on every row before the cut;
recomputes the running extreme and `used` by hand from bars up to the event bar only; checks the confirmation event is
decided at the confirmation bar; checks the day-end outcome and the trade frame. The same truncation check runs on the
real bars of every market in the study.

**Prior, stated now:** the H44 drift was small (0.06-0.22 ATR15, i.e. a few hundredths of a daily ATR) and weaker in the
second half; at a +/- 0.5 daily ATR scale within the remaining day I expect fade hit rates of 50-54%, many unresolved
events, and no pass. The tight stops (0.25 ATR15 beyond the extreme) make costs a large share of 1R, worst in crypto
(0.10% a side). Code `research/exhaustion_study.py`, report `research/out/exhaustion/study.md` + `.json`.

### H49 results (16 Nov 2026, ~06:30 UTC; development data to 2025-11-11; `research/out/exhaustion/study.md`)

**NO PASS. No variant reached 55% in both halves, and none made money after costs in the second half.** Code
`research/exhaustion_study.py` (readings from `adr.readings`, the day-end outcome from `session_break_study.outcome_window`,
the 72 h outcome from `confluence_study.outcome`, both unchanged); `tests/test_exhaustion.py` (truncation on 24h and
cash-hours synthetic bars; the running extreme, `used` and the event checked by hand bar by bar from bars up to the
event bar only; confirmation decided at the confirmation bar; trade frame, day-end outcome, one position per market).
Real bars: 0 mismatched truncation runs on all 8 markets (15,952 events compared). 8 variants, 48 tests per half,
Bonferroni 1.04e-3. Holdout not touched. Sanity: on BTC, 838 of 2,141 days reach >= 100% of the daily ATR, but only
126 of them have a WEAK bar (TR < 1 x ATR15) closing at a new extreme after that: late new extremes are mostly made by
big bars, so the events are rare (pooled 10-30 a month across 8 markets).

**Pooled fade hit rate within the day (first / second half, resolved n; most events do not resolve by the day's end,
68% unresolved for X1):** X1 (running extreme, used >= 100%, TR < 1.0 ATR15) 55.2% (337) / 45.0% (269); X2 (used >=
130%) 59.0% (183) / 48.2% (137); X3 (TR < 0.7) 56.6% (83) / 48.9% (90); X4 (X1 + next bar closes back) 56.9% (209) /
50.6% (174); X5 (prior-day level) 47.0% (181) / 47.1% (104); X6 (X5 + back inside) 46.1% (65) / 60.0% (40); X7 = X1's
events; X8 (used >= 130% + confirmation) 61.0% (105) / 46.5% (99). The first half leans the fade's way (55-61% on the
running-extreme variants, p 0.02-0.06, none past Bonferroni); the second half is at or below 50% everywhere except
X6 (40 resolved). 0 of 48 cells pass Bonferroni in both halves. 72 h (secondary): 49-55% first, 51-58% second. The
H44 drift is therefore a first-half pattern that did not hold: the second-half failure is mostly UP pushes (fade
short) in a period of strong uptrends (X1 up pushes 55.4% / 41.0%, down pushes 54.9% / 52.1%; metals 36% in the second
half).

**After costs (registered trade, second half pooled):** X1 889 trades, -0.048% a trade, PF 0.70, net -$4,249, all 8
markets negative; X2 -0.034%, -$1,507 (SPX the only market net > 0 with PF >= 1.1); X3 -$1,540; X4 -$3,232 (Brent);
X5 -$3,819; X6 158 trades, +0.004% a trade, PF 1.02, +$69 (3 markets); X7 -$6,814; X8 -$2,917 (BTC). First half:
X2 +$1,655 (PF 1.17), X7 +$2,279 (1.07), X8 +$4,512 (1.38) were positive, and all three turned negative in the second
half. The tight-stop variants (X1-X4, median stop 0.05-0.14 daily ATR) had small positive gross results (+0.02% to
+0.10% a trade, R before costs +0.05 to +0.38) but costs took 0.2-0.6 R a trade; of the wider-stop variants (X5-X8)
X5, X7 and X8 were slightly negative before costs in the second half, X6 +0.10% a trade gross on 158 trades.

Reading: fading a weak new extreme on a day that has used its daily ATR looked useful in 2020-mid 2023 and did not in
mid 2023-2025; the H44 hint does not survive as a rule. Nothing goes forward as a book. Live scan `py -3
research/exhaustion_study.py --scan` (paper / untested).

## H50. POST-NEWS DRIFT: does the first 15-60 minutes after a high-impact US release keep going for the rest of the day? (registered 16 Nov 2026, 09:48 UTC, before any H50 code existed or any H50 number was computed)

**Prompted by:** the owner (approved 16 Nov 2026). Question: after CPI, the jobs report (NFP), an FOMC rate decision
(and PCE / advance GDP), does the move in the first 15 or 60 minutes keep drifting the same way over the next hours /
day? Related earlier work, all on the six months of live calendar only (May-Nov 2026, a few dozen rows): H1 (CPI
follow-through on BTC/ETH, forward shadow), H16 (release-day follow-through beyond CPI, forward shadow),
`research/event_study.py`. H50 is the first test on the 2019+ release history (`engine15/calhistory.py`). I have not
looked at any post-release returns in the 2020-2025 history before writing this.

**Events (fixed now).** `calhistory.load_history()` (data/sources/calendar_history.csv, the rows `econ.load_events()`
merges in), rows with country USD, impact High, kind in {CPI, NFP, FOMC, PCE, GDP} and an `official:` source (the
agency's release date with its standard release time: 8:30 ET for CPI/NFP/PCE/GDP, 14:00 ET for the FOMC statement,
the 2020 emergency cuts at their own times; derived / nominal-time rows such as ISM and OPEC are not used). Rows at the
same UTC minute are one release; its type is the first of FOMC > CPI > NFP > PCE > GDP present (the others, and any
PPI / Retail / ISM row at the same minute, are listed as co-released). Rows flagged ";irregular" (shutdown-shifted
dates) are kept and counted. Release time T in UTC.

**Bars and readings (15m bars indexed by their open; closed bars only).** C0 = close of the bar that opens at T - 15 min
(the last close before the release). Bar k = the k-th bar from T (opens at T + 15(k-1) min); Ck = its close (k = 1: 15
min, k = 4: 60 min). Daily ATR D = `adr.readings` datr (Wilder 14 on UTC daily bars, the last CLOSED day through
`data.htf_on_15`, held for the day) at bar k; ATR15 = adr's atr15 at the pre-release bar (descriptive only).
**Impulse** I = (Ck - C0) / D (signed); side s = sign(I). A release counts in a market only if the bars at T - 15, T,
..., T + 15k min (bar k and the entry bar) are all on file (no gap), the entry bar is in the same UTC day as bar k, and
D > 0; otherwise it is counted as "not traded there" (the S&P cash market sees the FOMC statement only; the 8:30 ET
releases are before its open). I = 0 is dropped.

**The variants (8, every one counted; no selection step: the pass bar applies to each):**

| id | k (impulse window) | condition | trade |
|---|---|---|---|
| N1 | 1 (15 min) | abs(I) >= 0.25 D | WITH the impulse (side s) |
| N2 | 1 (15 min) | abs(I) >= 0.5 D | WITH |
| N3 | 4 (60 min) | abs(I) >= 0.5 D | WITH |
| N4 | 4 (60 min) | abs(I) >= 1.0 D | WITH |
| F1 | 1 | abs(I) >= 0.25 D | FADE (side -s) |
| F2 | 1 | abs(I) >= 0.5 D | FADE |
| F3 | 4 | abs(I) >= 0.5 D | FADE |
| F4 | 4 | abs(I) >= 1.0 D | FADE |

F1-F4 have N1-N4's events with the opposite side; with a symmetric bracket their hit rate is close to 100% minus the
WITH rate (a bar touching both barriers is a miss for both). They are still counted as tests.

**Entry, outcome and the trade (registered).** Decision at bar k's close; entry at the next 15m open (bar k + 1).
**Primary outcome:** +0.5 D in the trade's favour before -0.5 D against, from the entry open, over the bars from the
entry bar to the last bar of the release's UTC day (`session_break_study.outcome_window`, unchanged: a bar touching both
= miss; an open beyond a barrier fills at the open; neither = unresolved, excluded from the hit rate and counted).
**Secondary (counted in the test total, not in the pass bar):** the same over 24 h (bars from the entry bar up to the
first bar at or after entry + 24 h). **The trade** = the primary bracket itself: stop entry - side x 0.5 D, target entry
+ side x 0.5 D, out at the barrier or at the close of the UTC day's last bar (SPX: the cash session's last bar), $10,000
a trade, each market's own fee a side (`playbook.fee_side`), one position per market per variant (a release whose entry
falls while that variant's earlier trade in the market is still open is skipped for the trade, still counted for the
hit rate).

**Data and split (H44-H49's, exactly):** BTCUSDT, ETHUSDT, XAUUSD, XAGUSD, USDJPY, SPX, WTI, BRENT from `data.load`
(`rangebreak_study.load_dev`), rows before the sealed holdout 2025-11-11 00:00 UTC only (dropped right after loading,
never read); releases with entry from 2020-01-01; first half = entry before 2023-06-07, second half = from it to the
seal.

**Count and test.** One scope (pooled over the eight markets, each release-market pair one row). Tests per half: 8
variants x 2 outcomes (day, 24 h) = **16**; Bonferroni threshold p < 0.05 / 16 = 3.13e-3 (exact two-sided binomial
against 50%, `confluence_study.binom_p`). Per-type (CPI / NFP / FOMC / PCE / GDP), per-market and impulse-size cells are
descriptive, reported with nominal p, and NOT tests. Caveat stated now: one release moves all eight markets at once, so
the pooled rows are not independent and the binomial p overstates the evidence; I also report a release-level count
(each release counted once: a hit if most of its resolved market rows hit, ties dropped) as a descriptive check, not a
test. Family so far: H44-H49 (see HYPOTHESES.md), H1, H16 (forward only).

**Fixed pass bar (each variant):** ALL of (1) pooled primary hit rate >= 55% in BOTH halves; (2) >= 100 resolved
release-market rows pooled in EACH half; (3) pooled binomial p < 3.13e-3 in BOTH halves; (4) the registered trade,
second half, pooled net $ after costs > 0; (5) in the second half at least 5 of the 8 markets have net $ > 0 (a market
with no trades does not count). A pass is a reason to ask the owner about a forward PAPER book, not proof of an edge;
nothing is built or wired here.

**Reported whatever the result:** every variant's hit rate (day and 24 h), resolved / unresolved and p, per half, pooled,
per release type and per market; the trade (trades, win %, R before / after costs, % of stake a trade, PF, net $) per
half pooled, per type and per market; the release-level check; releases used per type and per half, releases not traded
per market; **the impulse-size / drift table**: every release-market row (no threshold) bucketed by abs(I) in daily-ATR
units (< 0.1, 0.1-0.25, 0.25-0.5, 0.5-1.0, >= 1.0) for k = 1 and k = 4, per half: rows, mean drift from the entry open
to the day's last close and to the 24 h close in the impulse's direction (daily-ATR units), % of rows whose drift is > 0,
and the WITH hit rate; the same by abs(I) in ATR15 units (< 2, 2-4, 4-8, >= 8).

**Look-ahead guard:** `tests/test_newsdrift.py` builds synthetic bars and a synthetic release list, truncates the bars
at every point and checks every event decided before the cut (bar indices, C0, Ck, I, D, side) is identical; changes
bars after bar k and checks the event is unchanged; checks a market gap or a closed session drops the release; checks
the outcome / trade on hand-made paths. The same truncation check runs on the real bars of every market.

**Prior, stated now:** the release bar's move is usually large but much of it is priced within minutes; the literature
on intraday post-announcement drift in liquid futures is mixed (small continuation in some studies, reversal in others).
At a +/- 0.5 daily ATR bracket over the rest of the day I expect WITH hit rates of 48-55%, FOMC rows noisy (few, and
the press conference 30 min after the statement often reverses the first move), and no pass. Code
`research/newsdrift_study.py`, report `research/out/newsdrift/study.md` + `.json`.

### H50 results (16 Nov 2026, ~09:53 UTC; development data to 2025-11-11; `research/out/newsdrift/study.md`)

**NO PASS. No variant reached 55% in both halves with >= 100 resolved rows and p < 3.13e-3; 0 of 16 outcome cells pass
Bonferroni in both halves.** Code `research/newsdrift_study.py` (readings from `adr.readings`, the bracket outcome from
`session_break_study.outcome_window`, unchanged); `tests/test_newsdrift.py` (6 tests: truncation at 100+ consecutive
cuts on 24h and cash-hours synthetic bars, bars after bar k scaled by 1.37 change nothing, C0 / Ck / I / D / side checked
by hand, a closed session or a missing bar drops the release, hand-made outcome / trade path, one position per market,
same-minute grouping) green on the laptop and on the server. Run on the Singapore server (11 s). Real bars: 0
mismatched truncation runs on all 8 markets (6,082 events compared). Holdout not touched. A 2-market smoke run (XAUUSD,
SPX) on the laptop preceded the full run; nothing in the design was changed after it.

**Releases used (with at least one market row; first / second half):** FOMC 28 / 20, CPI 41 / 29, NFP 42 / 27, PCE 41 /
28, GDP 14 / 8 = 166 / 112 releases; 1,168 / 798 release-market rows (k = 1). SPX sees the FOMC statement only (47 rows).

**Pooled hit rate within the day (first / second half, resolved n, p):** N1 (15 min, >= 0.25 dATR, WITH) 46.8% (203) p
0.40 / 55.6% (133) p 0.23; N2 (15 min, >= 0.5) 50.0% (96) p 1.00 / 57.1% (49) p 0.39; N3 (60 min, >= 0.5) 52.4% (105) p
0.70 / 59.4% (64) p 0.17; N4 (60 min, >= 1.0) 61.5% (26) p 0.33 / 79.0% (19) p 0.019; F1-F4 are the mirror (53.2 / 43.6,
50.0 / 40.8, 47.6 / 39.1, 38.5 / 15.8). 24 h: N1 49.5 / 54.7, N3 55.5 / 55.1, N4 62.1 / 77.3. Release-level check (each
release once): N1 55.7% / 52.9%, N3 56.4% / 65.5% (29 decided), N4 57.1% / 80.0% (10 decided), none p < 0.1.

**After costs (bracket trade, out at the day's last close):** WITH: first half all negative (N1 -$5,146, N2 -$1,062,
N3 -$2,899, N4 -$142), second half all positive (N1 +$113 PF 1.02, N2 +$296 PF 1.19, N3 +$1,215 PF 1.42 with 6 of 8
markets > 0, N4 +$521 PF 2.37 on 27 trades). FADE: first half F1 +$947, F3 +$440; second half all negative (-$780 to
-$2,453). So the sign flips between the halves: the fade was (slightly) the better side in 2020-mid 2023, following the
impulse in mid 2023-2025.

**Impulse size vs drift (k = 1, every row):** below 1 dATR there is no first-half drift (mean -0.05 to 0.00 dATR to the
day's close, WITH hit 41-50%); in the second half small positive drift (+0.04 to +0.19, 52-59%). Only abs(I) >= 1 dATR
drifts in both halves (+0.41 / +0.69 dATR, 80% / 62% WITH hit) but on 15 / 8 resolved rows. k = 4 the same picture
(>= 1 dATR: +0.14 / +0.32, 61.5% / 79.0% on 26 / 19). By type (k = 1, no threshold): FOMC 47.9% / 65.5%, CPI 44.8% /
57.3%, NFP 43.8% / 42.7% (payrolls do not drift in either half), PCE 47.3% / 56.2%, GDP 51.6% / 76.7% (30 rows).

Reading: there is no stable post-release drift at the 15-60 minute horizon in 2020-2025; the second half (2023-2025)
leans toward continuation, mostly after FOMC and CPI and the largest impulses, but the first half does not, the counts
for the big-impulse cells are small (tens), and the market rows of one release are not independent. Nothing goes
forward as a book. Unverified: release clock times are the agencies' standard times, not checked row by row against the
tape; the FOMC press conference (30 min after the statement) is inside the k = 4 window and not separated.

## H51. CROSS-MARKET CONFIRMATION: does a daily-level break confirmed by a related market continue more often, and does one the related market refuses fail more often? (registered 16 Nov 2026, 09:50 UTC, before any H51 code existed or any H51 outcome was computed)

**Prompted by:** H44-H49 (the first 15m close beyond the prior-day or rolling-24h level reaches +0.5 daily ATR before
-0.5 daily ATR in ~50% of resolved events; no single-market confluence, regime, session or exhaustion condition lifts
it above ~54% in both halves). The owner approved this test on 16 Nov 2026: a break CONFIRMED by a related market (a
break the same way at about the same time) may continue more often, and a break the related market REFUSES
(diverges from) may fail more often.

**Events and outcome: identical to H46/H47.** Every first 15m close beyond the level in its UTC day per direction
(s = +1 up, -1 down; `dailybreak_study.daily_breaks`, momentum OFF), levels **pday** (prior UTC day's high / low) and
**roll24** (previous 96 bars' high / low), daily ATR D from `engine15/sources/adr.py` `readings` (last closed day),
D > 0 and entry bar i+1 in the same UTC day. **Follow hit** = +0.5 D in the break direction before -0.5 D from the
next 15m open within 72 h (`confluence_study.outcome(R, i, s, D)` unchanged; a bar touching both = miss; neither =
unresolved, excluded, counted). **Fade hit** = `confluence_study.outcome(R, i, -s, D)` (the mirror; follow + fade hits
<= resolved). Eight markets, rows before 2025-11-11 00:00 UTC only (dropped right after loading; the sealed holdout is
never read), entries from 2020-01-01, first half before 2023-06-07, second half from it to the seal.

**Pairs (partner relation r = +1 same direction, -1 inverse), each used BOTH ways (A's events read against B, and B's
events against A):** P1 BTCUSDT <-> ETHUSDT (r +1); P2 XAUUSD <-> XAGUSD (r +1); P3 WTI <-> BRENT (r +1); P4 XAUUSD vs
USDJPY (r -1: a gold up-break is confirmed by a USDJPY DOWN-break, i.e. dollar weakness, and vice versa); P5 SPX vs
BTCUSDT (r +1, risk-on); P6 WTI vs SPX (r +1, oil as risk / growth; BRENT left out so no SPX event is counted twice in P6).

**Partner reading for an event of market A at bar i (open ms_i, close T = ms_i + 15 min), partner B, relation r,
same level type as the event, N = 4 bars (1 h), X = 1.0:**
- **Window** = B's bars whose open is in (ms_i - 4 x 15 min, ms_i], i.e. B's bars that CLOSE in (T - 60 min, T]: only
  bars closed by the event bar's close (no look-ahead; B's bar closing at exactly T is included). Partner frame = B's
  own development bars and its own `adr.readings` (its own pdh / pdl, box_hi / box_lo, ATR15).
- **No read** = B has no bar in the window (market shut: e.g. SPX outside cash hours, metals / oil / fx at the weekly
  or daily break). Excluded from the buckets, counted.
- **Confirmed** = at least one B bar in the window CLOSES beyond B's own level of the same type in direction r x s
  (above B's high for r x s = +1, below B's low for -1). This includes B's first break of the day and B already being
  through its level (closing beyond it) during the window.
- **Divergent** = NOT confirmed, and B's move over the window, m = close of B's last bar in the window - open of B's
  first bar in the window, satisfies r x s x m <= -1.0 x ATR15_B (B's Wilder ATR(14) on 15m at its last bar in the
  window, `readings` atr15). I.e. B moved the opposite way by >= 1 of its own 15m ATRs over the hour.
- **Unconfirmed** = read, neither confirmed nor divergent.
(Confirmed and divergent together are counted for the report: confirmed takes precedence.)

**Variants (8), each a pooled set of (event market, partner) readings:**
- V1 = P1 pday; V2 = P2 pday; V3 = P3 pday; V4 = P4 pday; V5 = P5 pday; V6 = P6 pday (each event of the pair's two
  markets, read against the other market of the pair);
- V7 = ALL pairs, pday, "any partner": every event of all 8 markets once, read against all its partners (BTC: ETH, SPX;
  ETH: BTC; XAU: XAG, USDJPY inverse; XAG: XAU; USDJPY: XAU inverse; SPX: BTC, WTI; WTI: BRENT, SPX; BRENT: WTI).
  Confirmed = confirmed by >= 1 partner and divergent from none; divergent = divergent from >= 1 and confirmed by none;
  "mixed" (confirmed by one, divergent from another) excluded and counted; unconfirmed = read by >= 1 partner, neither;
  no read = no partner read.
- V8 = V7 on the **roll24** level.

**Tests:** 8 variants x 3 buckets (confirmed, unconfirmed, divergent) x 2 sides (follow, fade) = **48 tests per half**;
exact two-sided binomial against 50% (`confluence_study.binom_p`); Bonferroni threshold per half p < 0.05 / 48 =
1.04e-3. Empty cells still count. The PRIMARY cells are "confirmed, follow" and "divergent, fade", but all 48 count.

**Pass bar (fixed now, per variant and bucket and side):** ALL of (1) hit rate >= 55% in BOTH halves; (2) >= 200
resolved events in each half (pooled over the variant's pairs); (3) p < 1.04e-3 in BOTH halves; (4) traded (entry at
the next 15m open, same UTC day only; stop entry -/+ 0.5 D, target entry +/- 0.5 D on the bucket's side; out at the
first open at or after entry + 72 h; stop first inside a bar, gaps fill at the open; one position per market at a time
within the bucket and side; $10,000 a trade; each market's own fee a side, `playbook.fee_side`; H46's `trades_of`)
net $ after costs > 0 in the SECOND half pooled AND net > 0 in a MAJORITY (more than half) of the variant's markets in
the second half (V1-V6: both markets of the pair; V7/V8: >= 5 of 8; a market with no trades is not
positive). A pass would be described so it could be registered as a forward paper book after asking the owner; nothing
is built or wired here.

**Secondary (descriptive, its own count):** per variant, confirmed-follow minus divergent-follow hit rate, two-proportion
z test (pooled variance), two-sided; "the partner matters" for a variant only if the sign is the same in both halves and
p < 0.05 / 8 = 0.00625 in BOTH halves. Also reported: each variant's reference (all read events) per half; per event
market inside each variant; bucket shares; no-read counts; confirmed-and-divergent overlap counts; every bucket traded on
both sides (trades, win %, R before / after costs, % of stake a trade, net $ per half, per market in the second half).
Sanity: the union of all events per level must reproduce H46's reference hit rates (pday pooled follow 49.1% of 6,916
/ 50.0% of 4,919).

**Look-ahead guard:** `tests/test_crossmarket.py`: on synthetic 24h and cash-hours bar pairs, the partner reading of
every event is identical when the partner frame is truncated to bars opening at or before the event bar's open (so only
bars closed by the event's close exist), and when both frames are truncated at several cuts; the confirmed / divergent
logic is checked by hand; the inverse relation flips the side; the window excludes partner bars closing after T. The
same truncation check runs on the real bars of every pair in the study.

**Prior, stated now:** related markets break together most of the time (BTC/ETH, XAU/XAG, WTI/BRENT are highly
correlated at 1 h), so "confirmed" will be the large bucket and look like the reference (~50%); "divergent" will be
small. A divergent break may fade slightly more often, but I expect differences of 0-3 points, no bucket at 55% in both
halves with 200+ resolved, and nothing positive after costs in the majority of markets. Code
`research/crossmarket_study.py`, report `research/out/crossmarket/study.md` + `.json`.

### H51 results (16 Nov 2026, ~09:55 UTC; development data to 2025-11-11; `research/out/crossmarket/study.md`)

**NO PASS. A related market's confirmation does not lift a daily-level break, and its refusal does not make the
break fail.** Code `research/crossmarket_study.py` (events, outcome and trade bookkeeping reused unchanged from
H45/H46: `dailybreak_study.daily_breaks`, `confluence_study.outcome` / `trades_of` / `binom_p`); `tests/test_crossmarket.py`
(6 tests: partner reading checked by hand on 24h and cash-hours synthetic pairs; partner truncated to bars opening at or
before the event bar's open gives identical readings; changing every partner bar after the event's close changes
nothing; both frames truncated at two cuts; inverse relation; any-partner rule; fade = mirror). Run on the Singapore
server. Real bars: partner-reading truncation 0 mismatched of 2,438-3,075 compared per market and level (all 8 markets,
both levels). 25,196 events; the union reproduces H46's reference exactly (pday follow 49.1% of 6,916 / 50.0% of
4,919). Tests: 48 per half, Bonferroni 1.04e-3. Holdout not touched.

**Primary cells (follow on confirmed; fade on divergent), hit rate first / second half (resolved):** confirmed-follow
V1 BTC<->ETH 46.8% (1,030) / 50.0% (630); V2 XAU<->XAG 46.1% (862) / 48.5% (549); V3 WTI<->BRENT 49.0% (955) /
47.6% (745); V4 XAU vs USDJPY inverse 49.3% (608) / 50.2% (408); V5 SPX vs BTC 49.2% (303) / 48.1% (214); V6 WTI vs SPX
48.2% (313) / 45.3% (192); V7 any partner pday 47.9% (3,640) / 48.9% (2,464); V8 roll24 49.0% (3,132) / 49.6% (2,127).
Confirmed breaks if anything continue slightly LESS often than the reference. Divergent-fade: V1-V3 almost never
diverge (2/6, 9/23, 6/1 resolved: the tight pairs move together within the hour); V4 52.5% (120) / 52.0% (123); V5
52.9% (68) / 56.8% (74); V6 53.5% (114) / 52.8% (108); V7 55.9% (204) / 50.2% (231); V8 54.8% (250) / 49.1% (216).
0 of 48 cells pass Bonferroni in both halves; 0 reach 55% in both halves with >= 200 resolved. Secondary contrast
(confirmed-follow minus divergent-follow): 0 of 8 significant; V7 +3.8 / -0.5 points.

Best non-primary cell: V4 unconfirmed-follow (gold break while USDJPY neither confirms nor diverges) 52.5% (998) /
54.5% (695, p 0.019), not past Bonferroni and below 55% in the first half.

**After costs (stop / target 0.5 daily ATR, 72 h, own fee, one position per market):** only two cells are net > 0 in
the second half pooled and in a majority of their markets: V1 divergent-follow (6 trades, +$793; meaningless) and V4
unconfirmed-follow (607 trades, +0.005% a trade, +$320, XAU and USDJPY both positive; first half 867 trades, -$1,650).
Neither meets the hit-rate / Bonferroni parts. V7 confirmed-follow loses -0.13% a trade (2,274 trades, -$29,820, 1 of 8
markets positive); V7 divergent-fade +$1,012 first half, -$2,343 second.

Reading: in this history a daily-level break is ~50/50 whether or not its related market breaks with it in the same
hour; tight pairs (BTC/ETH, XAU/XAG, WTI/BRENT) almost never diverge, and where divergence is common (XAU vs USDJPY,
SPX vs BTC, WTI vs SPX) it moves the fade by 2-7 points at most, not consistently across halves. Nothing goes forward as
a book.

## H52. SIZE BY EXPECTED MOVE: scale position size by a volatility forecast, entries and exits unchanged (owner-approved 16 Nov 2026; registered 16 Nov 2026, 09:50 UTC, before any H52 code existed or any H52 number was computed)

**Prompted by:** H39 / H40 / H46: direction is close to unpredictable at 15m, but the SIZE of the next move is
predictable (DVOL, put/call and stablecoin flows passed Bonferroni only on next-day drawdown tests; ATR clusters).
Question: with every entry and exit decision held fixed, does scaling the position by the predicted move size earn
more per unit of risk than constant notional? This is a sizing study only; no decision rule changes.

**The volatility forecast (one, fixed now; no fitted coefficient).** From 15m bars of each market, closed bars only.
r_j = log(close_j / close_{j-1}) for consecutive bars of the market (a session gap is inside the first bar's return).
B = the market's bars per trading day, a structural constant: the median count of 15m bars per UTC calendar day with
any bar, over the development data (96 crypto, about 92 for 23h markets, 26 for SPX cash hours; printed). At the close
of bar i: v1 = mean r^2 over the last B bars, v5 over the last 5B, v22 over the last 22B (bars <= i only). Per-bar
variance forecast f_i = (v1 + v5 + v22) / 3 (equal-weight HAR, Corsi 2009, no fitting), daily vol forecast
sigma_i = sqrt(B * f_i). Reference level m_i = the median of sigma at each UTC-day-end bar over the trailing 365
calendar days up to bar i (at least 60 day-ends, else no reference and the trade is sized 1). Tercile cut points =
the 33rd / 67th percentiles of the same trailing set. DVOL is NOT used (crypto only; one forecast for all 8 markets).

**Forecast quality (reported, condition (4) below).** For each UTC day d with >= B/2 bars ("valid day"): forecast =
sigma at the last bar of day d; realised = next valid day's (high - low) / close of the last bar of day d. Spearman
and Pearson-of-logs correlation per market per half; pooled = the mean of the 8 per-market Spearman correlations.

**Decision streams (both FIXED; sizing never changes an entry, an exit or a side).**
- **Primary: the main book's own replayed trades.** `shadows.run` with the main rule (hold to stop or flip; the
  engine's entries, stops, flips, fill delays and fees), odds formed read-only from `data/evcache` exactly as
  `research/exit_study.py` `prep_readonly` does (voices walked forward weekly from the engine birth 2020-01-01 with a
  PRIVATE fits directory, trust and mix as the live step), but with every array CUT at the seal (rows before
  2025-11-11 00:00 UTC; the walk-forward only uses labels resolved before each refit, so the cut changes no earlier
  decision). Run on the LAPTOP under research/out/heavy_job.lock (below-normal priority, >= 1,500 MB free), which
  writes only the trade list (entry time, exit time, side, entry price, exit price, exit reason) per market; a
  position still open at the seal is closed at the last close before the seal (flagged). The sizing study itself runs
  on the server from that trade list and the market bars.
- **Secondary (descriptive, NOT part of the pass bar): a transparent proxy.** Daily 30-day momentum sign: at the last
  bar of each valid UTC day d, side = sign(close_d / close at the last bar at or before d - 30 calendar days - 1),
  long or short, held from the next 15m open to the next day's decision, re-sized every day.

**Sizing variants (7 rows: a baseline and 6 sizing rules, every one counted; w set from sigma and m at the decision
bar, i.e. the close before the entry open).** Capital $10,000 per market, NOT compounded; notional at entry =
w x $10,000; in the primary stream the quantity is fixed for the life of the trade (size set once at entry); in the
proxy stream every row (the baseline too) is re-set daily and pays fees on the change.

| id | rule |
|---|---|
| S0 | constant notional, w = 1 (baseline) |
| S1 | inverse volatility, w = clip(m / sigma, 0.25, 4) |
| S2 | inverse variance, w = clip((m / sigma)^2, 0.25, 4) |
| S3 | half-strength inverse volatility, w = clip(sqrt(m / sigma), 0.25, 4) |
| S4 | cut only: w = min(1, m / sigma), floor 0.25 |
| S5 | top-tercile cut: w = 0.5 when sigma > trailing 67th percentile, else 1 |
| S6 | three regimes: w = 1.5 below the trailing 33rd percentile, 1 between, 0.5 above the 67th |

**Comparable exposure.** Sharpe and return / max drawdown are scale-free for an uncompounded book. Return and max
drawdown are reported EXPOSURE-MATCHED: each variant's daily P&L in a (market, half) is multiplied by the constant
(S0's time-average |notional| / the variant's time-average |notional|) in that cell; the pooled book = the sum of the 8
exposure-matched market books. The raw average exposure of every variant is printed beside it.

**Costs, fills, data.** Each market's own fee a side (`engine15/playbook.fee_side`) on every unit of notional traded
(entry, exit, daily re-size in the proxy). Primary fills at the replay's own prices (next 15m open; stop fills at the
stop or the open beyond it). Markets BTCUSDT, ETHUSDT, XAUUSD, XAGUSD, USDJPY, SPX, WTI, BRENT; development rows
before 2025-11-11 00:00 UTC only (the sealed holdout is never read); results from 2020-01-01; first half before
2023-06-07, second half from it to the seal (daily mark-to-market P&L split by date). Daily P&L = change of marked
equity at each UTC day's last bar.

**Metrics per half, pooled and per market:** return (% of capital, exposure-matched), Sharpe (daily P&L, sqrt(365)),
max drawdown (% of capital, exposure-matched), return / max drawdown, average exposure, trades, fees; and the paired
Sharpe-difference test vs S0 on pooled daily P&L (Jobson-Korkie with the Memmel correction), reported with nominal p.

**Count and test.** 6 sizing variants vs S0 on the primary stream: 6 comparisons per half; Bonferroni threshold for
the reported Sharpe-difference p = 0.05 / 6 = 8.3e-3 (reported, not a pass condition: the owner's bar below decides).
The proxy stream repeats the 6 rows descriptively (no test). Family: H25/H31/H32 (vol-targeted momentum books in the
harness) and HRL1 sizing are related earlier work.

**Fixed pass bar (owner's, as written):** a sizing variant passes if ALL hold: (1) its pooled Sharpe > S0's pooled
Sharpe in BOTH halves; (2) its Sharpe > S0's in a majority of markets (>= 5 of 8) in EACH half; (3) its pooled
exposure-matched max drawdown is not worse (<=) than S0's in BOTH halves; (4) the forecast's pooled correlation with
realised next-day range is > 0 in BOTH halves. Choose on the first half, confirm on the second: the CHOSEN variant is
the one with the largest first-half pooled Sharpe gain over S0 among variants meeting (1)-(3) on the first half
(else the largest first-half gain, for the write-up); **H52 passes if the chosen variant meets (1)-(4) in the second
half too.** Every variant's pass/fail on the full bar is also reported. A pass is a reason to ask the owner about
sizing a forward PAPER book this way, not proof; nothing is built or wired here.

**Look-ahead guard:** `tests/test_volsize.py` truncates synthetic bars and checks sigma, m, the tercile cuts and every
variant's w at each decision bar equal the values computed on the full series; checks the HAR value by hand; checks
the proxy side uses closes <= the decision bar only and the next open fills; checks the trade P&L / fee accounting
and the exposure-matching constant on a hand-made example. The same truncation check runs on real bars of every
market.

**Prior, stated now:** volatility clustering makes the forecast correlation clearly positive (0.3-0.6 per market).
For the proxy momentum stream I expect inverse-vol sizing to raise Sharpe modestly (the vol-managed literature,
Moreira-Muir 2017, is strongest for trend books). For the main book's trades I expect a smaller or no gain: its stops
are already 3 x ATR(1h) and the engine already sizes non-crypto trades by stop distance, so the trade P&L in % is
already vol-scaled in part, and the main book's results are concentrated in few large trades (H36), which a size
rule can as easily shrink as grow. My guess: no pass on the primary stream, S1/S3 the closest. Code
`research/volsize_study.py`, test `tests/test_volsize.py`, report `research/out/volsize/study.md` + `.json`.

**Implementation note (16 Nov 2026, ~10:15 UTC, written with the code, before any number was computed):** the
reference set for m and the tercile cuts uses day-end bars strictly BEFORE the decision bar (not "up to and including"
it): whether a bar is the last of its UTC day is known only once a later bar exists, so including the decision bar
itself could peek. The proxy side reads closes up to its decision bar (the day's last bar) and fills at the next bar's
open, the moment that bar shows the day has ended.

### H52 results (16 Nov 2026, ~10:20 UTC; development data to 2025-11-11; `research/out/volsize/study.md` + `.json`)

**NO PASS on the registered primary stream (the main book's own trades).** Code `research/volsize_study.py`, test
`tests/test_volsize.py` (10 tests: HAR by hand, truncation on 24h and cash-hours synthetic bars, reference strictly
before the decision bar, weights, trade / proxy accounting, next-open fill, exposure matching; green on laptop and
server). Real bars: 0 mismatches in the truncation check on all 8 markets (1.8 million values). 6 variants vs S0,
Bonferroni 8.3e-3 for the reported Sharpe-difference p. Holdout not read for any result.

**Decision stream.** The main book (rule "main", hold to stop or flip) replayed on the LAPTOP from data/evcache
read-only under research/out/heavy_job.lock with every array cut at the seal (engine config think15-v5.2.3; voices
walked weekly from 2020-01-01 in a private fits dir, ~16 min): 1,034 closed trades + 8 positions open at the seal
(closed at the last pre-seal close). The per-trade accounting reproduces the engine's own per-trade % exactly (BTC
193.0% vs 192.98%, ETH 485.5 / 485.55, XAU 106.6 / 106.59, WTI 194.7 / 194.66, sums of uncompounded 1x trades). Every
entry maps to a bar open (1,042 / 1,042). Disclosure: the SPX evidence store is older than the newest cards (294 of
398 feature columns); the 104 missing columns were fed as zeros (those cards silent) for the SPX replay only. The
sizing study ran on the Singapore server from that trade list.

**Forecast quality (condition 4 met).** Equal-weight HAR sigma vs the next valid day's range: pooled mean Spearman
0.561 (first half) / 0.435 (second); every market positive in both halves (0.34-0.67).

**Primary, pooled Sharpe first / second half (S0 = constant notional):** S0 1.121 / 1.034; S1 inverse vol 0.793 /
1.182; S2 inverse variance 0.600 / 1.183; S3 half-strength 0.931 / 1.125; S4 cut-only 0.833 / 1.176; S5 top-tercile
cut 0.800 / 1.229; S6 three regimes 0.725 / 1.230. Every variant is WORSE than S0 in the first half (beats S0 in only
2-3 of 8 markets; the main book earned much of 2020-2022 in high-volatility oil and crypto spells that vol sizing
shrinks: WTI 200% -> 57% under S1) and better in the second half (5-6 of 8 markets for S1/S3/S4/S5, lower matched max
DD). Chosen on the first half: S3 (smallest loss, -0.19); it fails condition (1)-(2) in the first half, so NO PASS;
no variant passes the full bar. No Sharpe difference is Bonferroni-significant (best nominal p 0.031, S5 first half,
in the wrong direction; second-half p 0.13-0.62).

**Secondary proxy (descriptive, not a test): daily 30-day momentum sign.** Vol sizing helped in both halves: S0
1.208 / 0.453; S3 1.413 / 0.598; S4 1.494 / 0.604; S6 1.353 / 0.643; S1 1.407 / 0.720; S2 1.266 / 0.886. S3, S4 and
S6 would meet the full bar on this stream (S4 chosen on the first half), but no JK p is below 0.17, so even there the
gain is not statistically established. This matches the vol-managed-momentum literature and my prior.

Reading: the forecast works (size of move is predictable), and on a simple trend book it raises Sharpe in both
halves, but on the main engine's own trades it cut Sharpe by 0.19-0.52 in 2020-mid 2023 and raised it by 0.09-0.20
afterwards: not a stable improvement. Unverified: the main-book replay uses today's engine config over history (as
H36), the SPX store gap above, and uncompounded 1x accounting (drawdowns can exceed 100% of $10,000 in a market over
a half). Nothing is built or wired.

## RL loop round 4 (HRL4): the committee at 1.25, and a four-vote committee (registered 17 Nov 2026, 03:21 UTC, in `research/rl_loop/LOOP_RL.md`, before any round-4 code was written or any result)
Run at the owner's request of 17 Nov 2026 ("Concurrently do the RL tasks too") after the 14 Nov advice not to. Rules, frame and yardstick unchanged; two execution-only variants, no retrain: R4-a `committee_riskoff_125` (R3-c's two-of-three committee, long request 1.25) and R4-b `committee4_riskoff` (Phase 6, round-2 and round-3 agents plus the daily trend; flat on three of four bearish votes, 1x). Cumulative RL variants 25, threshold 0.00200. New inputs from `flows.py` / `cryptox.py` not used (too short, or already short of the bar alone in H39/H40, or never tested alone). Run on the research server on a rebuilt input cache after a gate that reproduced the Phase 6 primary and R3-b/c/d exactly. The loop's frame has no sealed holdout (full span to 2026-11-11, as frozen in LOOP_RL.md).
### Verdicts, RL loop round 4 (17 Nov 2026, 03:40 UTC; `research/out/rl_loop/round4_report.md`)
**No pass.** Yardstick BTC spot buy-and-hold +583.9%, Sharpe 0.82, DD 77% (sub-span +879.7%, 1.03).
- **R4-a: FAIL** (20/21). +1,474%, Sharpe 1.17 (1.21 / 1.28 / 1.03), DD 59-61%, 57 trades/yr; sub-span +1,552%, 1.35; fold share 56% (14/25); ETH +1,263%, 1.07. Fails only S4: gap +0.46, SE 0.25, p 0.036 vs 0.00200 (needs ~0.73).
- **R4-b: FAIL** (16/21). +593%, 1.01, DD 49-55%; mean CAGR 36.7% vs 36.9%; sub-span +652% vs +880%; fold share 44%; p 0.093.
- The 1.25x bought the return rules, not information: the Sharpe gap is R3-c's (+0.43) within an eighth of a standard error. No round 5 proposed. Not proof of anything either way.

## H53. The signal book S1: `b_targets` as a signal a person can follow (registered 17 Nov 2026, 04:18 UTC, before any S1 code existed or any S1 result was computed)

**Prompted by:** the owner, 17 Nov 2026: subscribers "only want to know trade opportunity"; "Yes, build preview". The main
books close about five trades a week and hold for days; the shadow book `b_targets` (half off at Target 1, the rest at
Target 2, stop to break-even after Target 1; `engine15/shadows.py`) trades two to three times a day and every trade has an
entry, a stop and two targets. Disclosed before registering: on the live scoreboard today `b_targets` shows 16 trades,
75% won, +$2,954; on 2020-2026 history it lost $28,862 against the main book (H36). One good week is not evidence.

**What S1 is.** Not a new trading rule: S1 is `b_targets` unchanged, in all eight markets, re-scored the way a subscriber
could really trade it. The book fills at the open of the bar after its decision; an alert reaches a person minutes later
(about four today), so the book's own fills cannot be had. S1 keeps two records per signal: the BOOK result (as
`b_targets` booked it) and the FOLLOWABLE result under the fixed rules below. Only the followable record is judged.

**A signal** is issued when `b_targets` shows a new open position in a market (a new `opened_utc`). It carries: side, the
book's entry price E, the stop S, Target 1 and Target 2, as the page shows them at that moment. 1R = |E - S|.

**Followable rules (fixed now).** Bars are the engine's own 15-minute bars. Let bar A be the bar during which the alert was
sent (the bar whose open is the book's fill).
1. Entry: a limit order at E. It counts as filled at E on the first of the FOUR bars after bar A whose range holds E
   (low <= E <= high). Bar A itself never counts (the alert arrives part-way through it).
2. No fill: if S or Target 1 trades in bar A or in any later bar before the fill (a bar that holds E and S or Target 1
   together counts as no fill), or the four bars pass, or the book closes its own trade first, the signal ends as
   "no fill": no result, counted as a signal sent but not as a trade.
3. After the fill: half is closed at Target 1, the rest at Target 2; after Target 1 the stop is at E. A bar that holds the
   stop and a target together counts as the stop. A gap through the stop fills at that bar's open.
4. If the book closes its own trade for any other reason (a flip, a decision exit) while the followable trade is open, the
   followable trade closes at the OPEN of the bar after the bar in which that exit alert was sent (one bar later than the
   book).
5. Costs: the market's own fee a side (`playbook.fee_side`) on each fill; $10,000 a signal; results in $, % and R.
6. Nothing is tuned on live results: the four-bar window, the limit at E and the half/half exit are fixed here.

**Judged on live signals only** (from the first signal sent by the deployed preview; nothing before it, no history replay):
the followable record through the scoreboard's own rule (mean result per filled trade, 90% range; "ahead" = the low end
above zero). Interim reading at 30 filled trades. **Commercial gate (fixed now): S1 is not sold before it has at least 100
signals over at least 60 days and its followable record is "ahead".** Reported with it, always: the fill rate (filled /
sent), the book result of the SAME signals (so the cost of followability is visible), and the results of signals that
did not fill, had they been taken at the book's price (to show what the limit rule misses). A pass is a reason to
propose the next step to the owner, not proof of an edge. Counted as one variant.

**Preview only:** signal cards and follow-ups go to the owner's own Telegram chat, labelled as a subscriber preview.
No subscriber channel exists; nothing is sold; paper only.

### H53 amendment (17 Nov 2026, 04:55 UTC; before the preview was deployed and before any live S1 signal existed)
Forced by how the page works, not chosen from a result. Disclosed: before writing this I had seen a mechanics-only replay
of 11-17 Nov records through the finished code (24 signals, 11 filled, 9 of them won); those numbers are not the
registered record and nothing below was picked because of them.
- **Bar A.** The registration said bar A is "the bar whose open is the book's fill". That cannot happen: the page shows a
  `b_targets` position only after its fill bar F has closed (`shadows.advance` works on closed bars), so the alert goes
  out in bar F+1 at the earliest. **Bar A is the bar in which the alert is actually sent.** Bars F to A never fill, and a
  stop or Target 1 trading in bars F to A also voids the signal. A subscriber therefore hears of a signal at least one
  full bar (15 minutes) after the book entered, not about four minutes.
- **Rule 4** in practice: the followable exit is at the open of the first bar after the exit alert's bar, which is two bars
  after the book's own exit, not one.
- **Conservative readings fixed with it:** in the bar that takes Target 1 the stop at E is live at once (if that bar also
  holds E, the rest closes at E); a bar wholly on the favourable side of E without touching it is not a fill; the four
  bars are the four 15-minute slots after A (a later bar after a session gap does not fill); a position already showing
  Target 1 taken when first seen is sent as "do not enter" and counts as no fill; "$10,000 a signal" is $10,000 notional
  without leverage (% and R are what subscribers see; the verdict is on $ at equal size, the same as on %); a position
  that opens and closes inside its own fill bar never shows as open and is never a signal, so the "book result of the same
  signals" leaves such instant stop-outs out (said wherever that comparison is shown); a signal counts only once its card
  was delivered.
- **Not changed:** the limit at E, the four-bar window, the half/half exit, the costs, the judgement on live followable
  results only, and the commercial gate (100 signals, 60 days, "ahead").
- **Follows from it (not part of S1):** the engine knows a `b_targets` entry one bar before the page shows the position;
  publishing the signal at decision time would be a different, earlier signal and would be registered as its own book.

### H53 note: the Setups page launches before the gate; the gate stays for charging (17 Nov 2026, 05:01 UTC)
The site coordination session relayed that the owner, asked "Should Setups launch as an owner-only preview until the
signal book passes its 100-signal gate?", answered **"no, launch now"**. Confirmed with the owner in this session the
same hour; of three options the owner chose **"Launch now, gate for charging"**: the Setups page on
aitrading.alphaprediction.ai goes live now, fed by `b_targets` / S1, labelled experimental and paper-only, showing the
live record with its trade count; **the gate (100 signals over 60 days and "ahead" on the followable record) remains the
condition for charging money for it.** H53's grading is unchanged: live followable signals only, from 2026-11-17 04:58 UTC.
The page is the site sessions' work; this project supplies `out/live/setups.json` (a pure function of the page and the S1
log; no new rule, no change to any book).

### H53 note 2: the owner drops the charging gate for the Setups page (17 Nov 2026, 05:05 UTC)
The website serves its data behind a paywall (members with a plan). Asked in this session whether Setups should be free
while experimental ("Free for now", my recommendation), "Included for paying members", or members-only labelled beta, the
owner chose **"Included for paying members"**: Setups sits behind the existing paywall from day one, as part of the plan
members already pay for. This replaces the earlier "Launch now, gate for charging" for the Setups page: **the commercial
gate of H53 (100 signals over 60 days and "ahead") no longer conditions selling the Setups page.** It is the owner's
decision against my recommendation; recorded as such. Unchanged: S1's rules and its grading on live followable signals
only (from 2026-11-17 04:58 UTC); the record and its trade count are shown on the page; nothing is described as a proven
edge; the question whether selling trade signals is a regulated activity is the owner's to settle with a lawyer. The
gate's numbers remain the bar for any claim that S1 "works", and for the Telegram signal product, which is still a
preview to the owner's chat only.

## H54. DUPLICATE CARDS: which cards say the same thing, and does one idea vote several times? (owner-approved 17 Nov 2026, "6 to 10 also ok", task 9; registered 17 Nov 2026, 06:15 UTC, before any H54 code existed or any H54 number was computed)

**Prompted by:** the engine now reads 82 cards (think15-v5.2.4) and many indicator families measure the same thing
(Williams %R, Stochastic, StochRSI and CCI all place the close in its recent range; Supertrend, Parabolic SAR,
Heikin-Ashi, the moving-average cards, KAMA, Hull and Ichimoku all follow trend). The owner approved a study of duplicate
cards. Known before any number: three voices share readings by construction (`pullback` reads `tr_1d` and `k_1h`, which
`trend` and `meanrev` also read).

**What this is.** A DESCRIPTIVE study. No trading rule, no selection, no pass bar, no variant search; counted as one
descriptive study with no variants. **Nothing is removed, merged or re-weighted on the strength of it: removing or
merging a card is a new engine version, registered on its own, and the owner's decision.** A high overlap says two cards
lean together; it does not say either of them is right.

**Data.** The engine's evidence stores `data/evcache/<group>/<asset>` on the research server, opened READ-ONLY (memory
maps; nothing under `data/` is written and no rebuild is triggered), for crypto, metals, fx and energy. The index group
is included only if its store is on the engine's current version when the study runs; at registration it is known NOT
to be (last built 16 Nov 21:04 UTC on the previous signature; it rebuilds when the S&P opens at 14:30 UTC), so it is
expected to be skipped and that will be said. Rows before the sealed holdout 2025-11-11 00:00 UTC only (later rows are
cut off before anything is computed; the holdout is never read). Sessions from 2020-01-01 where the engine's required
readings exist (`ready`). First half = sessions before 2023-06-07 00:00 UTC, second half = from it to the seal (the
H6/H41/H44 split). Every measure is computed on each half separately.

**The unit is the voice** (what votes: `config.voting_by_group` lists voices), shown under its card title. The two cards
with several voices (Momentum and stretch: `momentum`, `meanrev`, `pullback`; News and economic events: `news`, `macro`)
are kept as separate voices. Left out: `all`, `base`, `owner`; in each group the voices that do not apply there, and
voices with no history (live-only readings). The voices are those of the engine as it stands today (v5.2.4), walked
through history as if it had run then.

**The overlap measures, fixed now** (`research/card_overlap.py`; report `research/out/card_overlap_20261117.md` + `.json`):
- **A voice's pull** at a session = P(up) - P(down) of that voice's own odds (before trust), formed as the engine forms
  them: weekly refits walked forward from 2020-01-01 by `leanprep.walk_forward_cached` on the stored readings, with the
  refits kept in a PRIVATE directory under `research/out/card_overlap/` (never the engine's fits directory). A voice
  **speaks** at a session when at least one of its readings is non-zero there (the engine's silent-voice rule).
- **M1, pull overlap (primary):** Spearman rank correlation of the two voices' pulls over the sessions of the half where
  both speak and both have odds. Per asset; a pair is measured for an asset and half only with at least 2,000 such
  sessions and a pull that varies for both; the group's value for the half is the mean over its measured assets.
- **M2, agreement:** on the same sessions, how often the two pulls have the same sign (both non-zero). Reported, not
  used in any definition.
- **M3, reading overlap (secondary):** Spearman rank correlation between every pair of readings as the voices see them
  (the feature matrix: a missing reading is 0), over the ready sessions of the half, per asset. For two voices A and B:
  R(A in B) = the mean, over A's readings that vary in the sample, of the largest |rho| with any reading of B;
  R(A, B) = the smaller of R(A in B) and R(B in A); the group's value is the mean over its assets. Also listed: "A is
  contained in B" when R(A in B) >= 0.85 in both halves.
- **A pair's similarity in a group:** s = the smaller |M1| of the two halves, and 0 when the sign of M1 differs between
  the halves. (r, for readings: the smaller R of the two halves.)
- **Across groups:** with G = the number of groups in which the pair is measured in both halves, S = the k-th largest
  of its group similarities, k = ceil(0.75 x G) (3 of 4, 3 of 3, 2 of 2, 1 of 1). Pairs never measured together: S = 0.

**Definitions, fixed now.** Two voices are **duplicates** when S >= 0.85 (|rho| of their pulls at least 0.85 in BOTH
halves in at least three quarters of the groups where both apply) and **near-duplicates** when 0.70 <= S < 0.85. The same
two thresholds applied to the reading overlap give the secondary labels "reads alike" (>= 0.85) and "reads nearly alike"
(>= 0.70); they are reported beside the primary ones and never replace them.

**Clusters, by a fixed rule.** Average linkage: start with every voice alone; repeatedly join the two clusters whose
average pairwise similarity is highest, while that average is at or above the threshold (ties: the pair that comes
first in the engine's voice order). Run at 0.70 (near-duplicate clusters) and at 0.85 (duplicate clusters), (a) across
groups on S and (b) inside each group on s, and the same on the reading overlap. Clusters of two or more are reported.

**What will be reported.** (1) Every pair at or above 0.70 with its M1, M2 and reading overlap in each half and group.
(2) The clusters. (3) For each cluster and group, its best-rated member in Task 8's rating of 17 Nov 2026
(`research/out/card_rating_summary_20261117.md`: the card's worse half). (4) Per group, how much of the vote each
cluster holds among the current voters: the number of its voting voices out of the group's voters (the owner aside), and
its share of the say = the voting trust as the engine forms it on the same history (`leanprep.trust_tail` over all
voices, the group's voters only, renormalised, the 40% cap, then per asset the silent-voice mask and the cap again, as
`leanprep.prepare_live`), mean over the sessions of each half and over the group's assets, summed over the cluster's
voting members. (5) The count of pairs measured, and a plain-English summary with clean-up OPTIONS for the owner.

**Why it may mislead.** The voices' pulls are small (heavy ridge, even prior), so a rank correlation can be high between
two voices that both barely move the odds. Higher-timeframe readings are step functions, so the number of independent
observations is far below the session count; no significance test is run and none is claimed. 0.85 and 0.70 are
conventions chosen before looking, not measured boundaries. Two cards that overlap on history can still differ in the
rare sessions that matter. In-sample history: this describes how the cards behaved together, it proves no edge and no
redundancy going forward.

**If the registered design proves infeasible** (a store that cannot be read, memory, time), the run stops, the reason is
recorded here as a disclosed deviation, and no definition above is changed after a number has been seen.

### H54 note on the time (17 Nov 2026, 06:14 UTC; still before any H54 code existed)
The heading above says 06:15 UTC; by the research server's clock the section was appended at about 06:12 UTC (the time
was written a few minutes ahead). No H54 code existed and no H54 number had been computed at either time. Running at
that moment, and unrelated to H54's definitions: Task 8's card rating (`research/rate_cards_snapshot.py`, started
06:12 UTC on the server), whose results H54 only uses to name each cluster's best-rated member.

### H54 results (17 Nov 2026, ~07:00 UTC; development data to 2025-11-10; `research/out/card_overlap_20261117.md` + `.json`)

**Descriptive; nothing changes in the engine.** Code: `research/card_overlap.py` (group stage on the research server,
06:38-06:57 UTC, two workers; report on the laptop from `research/out/card_overlap/group_<g>.json`). Groups run: crypto,
metals, fx, energy. **Index not run**, as expected at registration: its store was still on the previous signature. 71
voices measured in at least one group, 2,251 distinct pairs (4,793 pair-by-group measurements). Never measured: `book`,
`kronos`, `news`, `lsratio`, `liq`, `etf` (no or too little history before the seal) and the index-only voices
`overnight`, `eqbreadth`, `putcall`, `earnings`. Holdout not touched. One descriptive study, no variants.

- **Duplicates (pull overlap S >= 0.85): none**, in no group (within-group maxima: crypto 0.80, fx 0.81, energy 0.78,
  metals 0.75).
- **Near-duplicates (0.70 <= S < 0.85): two pairs.** `meanrev` (Stretch and exhaustion) with `stochrsi`: S 0.75, measured
  in all four groups (crypto 0.66 / 0.74, metals 0.75 / 0.78, fx 0.80 / 0.85, energy 0.81 / 0.78). `momentum` with `flow`
  (Order flow, CVD): 0.73 / 0.75, crypto only. Within single groups more pairs pass 0.70 (crypto 19, fx 8, metals 2,
  energy 1), e.g. `cci`-`willr` 0.80 in crypto and 0.81 in fx, but 0.69 and 0.65 in metals and energy, so S = 0.69.
- **Reading overlap (secondary):** one pair "reads alike": `cci`-`willr` (0.87-0.90 in every group). 29 further pairs
  "read nearly alike". Clusters at 0.70: {`meanrev`, `ribbon`, `kama`, `stochrsi`, `cci`, `willr`, `elder`},
  {`trend`, `mavg`}, {`intraday`, `vprofile`}. Contained (R(A in B) >= 0.85): `stochrsi` in `meanrev` 0.91, `trend` in
  `mavg` 0.90, `cci` and `willr` in each other 0.88, `elder` in `cci` 0.88, `kama` in `cci` 0.87 and in `ribbon` 0.85.
  Not near-copies on either measure: `supertrend`, `psar`, `heikin` among themselves (0.4-0.5), `cmf`-`mfi` (0.45).
- **Does one idea vote several times?** By the vote: only in crypto, where `momentum` and `flow` are both voters (2 of
  12; 15% / 14% of the say). Separate voting ideas at the near-duplicate threshold: crypto 11 of 12, metals 13 of 13, fx
  12 of 12, energy 10 of 10. By the readings: metals has 3 voters in the range/average family (`momentum`, `meanrev`,
  `kama`: 23% / 23% of the say) and 2 in {`trend`, `mavg`} (15% / 16%); fx has {`trend`, `mavg`} (17% / 18%) and
  {`momentum`, `meanrev`} (18% / 18%); crypto and energy have no reading family with two voters. On this history the
  say is spread evenly (no voter above 15.3% on average in any group and half).
- **Best-rated members** (17 Nov rating): of {`cci`, `willr`}: CCI in crypto (#12), metals (#6) and fx (#31), Williams %R
  in energy (#20); of the family of seven: the ribbon in crypto (#2), Elder-Ray in metals (#5) and energy (#7), Momentum
  and stretch in fx (#4).

**Disclosed.** (1) The heading's time is three minutes ahead of the append (note above). (2) After the first group's
numbers existed, the REPORT code was changed twice, presentation only: a cluster's best-rated member is now listed only
for groups where at least two of its members are measured, and a voter without a card title prints its voice name. No
measure, threshold or clustering rule was changed, and no group was re-run. (3) Added beyond the registered list, as
context only: each card's mean |pull| in points and how often it speaks (section 6 of the report). (4) The registration's
"82 cards" are the engine's 82 voices including the owner's; 81 were candidates here. (5) The group stage copied the
rows before the seal out of the stores (read-only memory maps) into memory and worked from the copy; the engine's
steps at 06:45 and 07:00 UTC ran normally meanwhile.

**Reading.** By how they vote, the cards are less repetitive than their names suggest; by what they read, the newer
oscillator cards mostly repeat an idea the engine already had. Options for the owner are in the report; none is
proposed here. In-sample, descriptive, no edge claimed.

## H55. SETUPS QUALITY FILTER: can the engine's own readings at a setup's start tell which Setups signals are worth sending? (registered 17 Nov 2026, 12:03 UTC, before any H55 code existed or any H55 number was computed)

**Prompted by:** the owner, 17 Nov 2026, choosing the first of four ways RL could help ("Setups quality filter ... Yes").
Not an RL agent: a supervised "take it or skip it" classifier on top of an existing book (meta-labelling). The four RL
rounds showed learning direction from scratch fails; this asks a narrower question about trades that already exist.

**Population.** Every `b_targets` trade (the Setups / S1 source book, `engine15/shadows.py`, rule unchanged) in the eight
markets, replayed on history with the engine's own machinery, entries from 2020-01-01 to the sealed holdout 2025-11-11
00:00 UTC (later rows dropped right after loading; never read). Each trade is scored by H53's FOLLOWABLE rules as amended
on 17 Nov (bar A = the bar after the book's fill bar; limit at the book's entry for four bars; half at Target 1, rest at
Target 2, stop to entry after T1; same-bar = stop; costs = the market's fee a side): result in R, or "no fill".

**Label.** y = 1 if the followable result is > 0 R after costs, else 0; a "no fill" counts as y = 0 for training (a signal
that cannot be traded is not worth sending) and as 0 R in the results.

**Inputs (at the book's decision bar only, nothing later):** every feature the engine reads at that close
(`evidence.FEATURES` as stored for the bar, i.e. what the engine saw), the main call's odds and edge points signed to the
setup's side, the market (one-hot), the UTC hour and weekday, the stop distance and the Target-1 distance in ATR(14, 15m)
and their ratio. A test proves the inputs at bar t are identical with and without the bars after t.

**Variants (2, both counted):**
- F1: logistic regression, L2, C = 0.1, inputs standardised on the training rows, class weights balanced.
- F2: gradient-boosted trees (scikit-learn HistGradientBoostingClassifier if installed, else a stated stand-in fixed before
  running): max_depth 3, learning_rate 0.05, 200 iterations, min_samples_leaf 50, l2_regularization 1.0, early stopping off.
Each is trained ONCE on first-half signals (entries before 2023-06-07). **The filter keeps a signal when its predicted
probability is at or above the median of the first-half predictions** (so it keeps about half; the cut is fixed on the
first half). Nothing from the second half is used to train, scale, choose a cut or choose between F1 and F2.

**Fixed pass bar (second half, 2023-06-07 to the seal; each variant on its own; Bonferroni over 2 variants):**
(1) mean followable R per SENT signal of the kept set is higher than that of all signals, with a one-sided block
bootstrap p <= 0.025 (blocks = calendar weeks, 10,000 resamples, fixed seed 55); (2) the kept set's total followable R
after costs is > 0; (3) the kept set's mean R is higher than all signals' in at least 5 of the markets that have >= 20
second-half signals; (4) the kept set has >= 100 second-half signals. A pass would be a reason to propose a forward paper
filter book ("S1-F": the same live signals, sent only when the filter keeps them, graded on live followable results beside
S1) to the owner, not proof of an edge and not a change to Setups.

**Reported whatever the result:** counts, fill rates, mean and total R, win rates, per market and per half, for all
signals and for kept/skipped; the AUC of each variant on each half; the ten inputs that move each variant most; the same
table with the BOOK result instead of the followable one. **Disclosed already:** `b_targets` lost $28,862 against the main
book on 2020-2026 history (H36); its live record is 17 trades; the followable record has 1 live signal.

### H55 note: library decision (17 Nov 2026, 12:36 UTC; before any H55 result on real data was computed or seen)
scikit-learn was not installed when H55 was registered; the study agent prepared numpy stand-ins (a Newton-method L2
logistic regression for F1, a numpy histogram GBM for F2). The owner then approved installing scikit-learn 1.9.1 and
scipy 1.18.1 in a SEPARATE research Python setup on the server (`/data/venv-research`; the live engine's `/data/venv` is
byte-for-byte unchanged, numpy 2.4.5 shared). Decided now, before any real-data number: **F1 and F2 are judged with
scikit-learn exactly as registered** (F1: `LogisticRegression(penalty="l2", C=0.1, class_weight="balanced",
solver="lbfgs", max_iter=5000)` on standardised inputs; F2: `HistGradientBoostingClassifier(max_depth=3,
learning_rate=0.05, max_iter=200, min_samples_leaf=50, l2_regularization=1.0, early_stopping=False, random_state=55)`,
class weights none, as registered). The numpy stand-ins are reported beside them as a cross-check only, never judged.

### Verdicts, H55 (17 Nov 2026, ~14:50 UTC; development data 2020-02-05 .. 2025-11-10, seal never read; `research/out/setups_filter/report.md` + `results.json`)
**No pass. Neither filter passes; the Setups signals are not filtered and no S1-F forward book is proposed on this read.**
Judged with scikit-learn 1.9.1 (the library note above); the numpy stand-ins agree (cross-check, not judged: same
keep/skip on 99.7% (F1) and 92.4% (F2) of second-half signals, and neither would pass).
- Population: 5,034 `b_targets` signals in all eight markets (2,858 first half, entries before 2023-06-07; 2,176 second
  half). Second half: BTC 410, ETH 352, XAU 241, XAG 245, USDJPY 297, SPX 104, WTI 253, BRENT 274. Followable fill rate
  59.2% / 60.2%; most no-fills are the four-bar window passing (819 of 866 in the second half). Label base rate (> 0 R
  after costs, no fill = 0): 25.3% first half, 24.7% second half. All second-half signals: mean -0.027 R per sent signal,
  -59.6 R in total (the book's own result of the same trades: -0.028 R, -61.0 R).
- AUC, first half (in-sample) / second half: F1 0.760 / 0.520; F2 0.917 / 0.566. The in-sample separation does not carry
  over: the kept sets made +0.23 R (F1) and +0.35 R (F2) per signal in the first half and lost in the second.
- Pass bar, second half (F1 | F2):
  (1) kept mean R > all, block bootstrap p <= 0.025: F1 -0.0355 vs -0.0274, p = 0.649, FAIL | F2 -0.0202 vs -0.0274,
      p = 0.371, FAIL.
  (2) kept total R > 0: F1 -39.1 R, FAIL | F2 -21.7 R, FAIL.
  (3) kept better in >= 5 of the 8 eligible markets: F1 4 (BTC, XAG, USDJPY, BRENT), FAIL | F2 4 (BTC, ETH, WTI, BRENT), FAIL.
  (4) kept >= 100 signals: F1 1,101, pass | F2 1,077, pass.
- With the BOOK result instead: F2's kept set -0.001 R vs all -0.028 R (skipped -0.055 R); F1's kept set -0.027 R vs
  -0.028 R. Neither is a profit on the book's own fills either.
- Deviations / disclosures: inputs at the decision bar k = fill bar - 1 - fill delay; the stop and Target-1 distances are
  the book's plan at that close (entry = the close, since the fill is the next open); 18 trades that opened and closed
  inside their own fill bar are never signals (H53 amendment) and 8 trades open at the seal are left out; odds walked from
  2020-01-01 as H36 replayed the books (the live step walks 240 days); SPX was read after the engine rebuilt its store on
  the current code (14:47 UTC). Scoring is `engine15/signals.py`'s own state machine (tested against `signals.run` on
  synthetic bars).
- Plainly: this is history the engine's authors have lived through, one registered try with two variants. It rejects
  this filter on this data; it proves nothing about the signals going forward.

## H56. EARLY SIGNALS (S2): the same Setups signals, published at the engine's decision instead of one bar after the fill (registered 19 Nov 2026, 03:48 UTC, before any S2 code existed or any S2 result was computed)

**Prompted by:** the owner, 19 Nov 2026, choosing "Earlier signals" as the next build. S1 (H53, amended) can only announce a
`b_targets` entry after its fill bar has closed, so a subscriber hears of it at least one full bar (15 minutes) after the
book entered. The engine already knows the entry one bar earlier: at the close where `b_targets` decides it, the book holds
a PENDING order for the next open (`shadows` state `pending`, shown on the page as `next_open`).

**What S2 is.** Not a new trading rule: the same `b_targets` entries, announced at the decision close. A signal is issued
when the `b_targets` view of a market shows a NEW pending entry (`next_open` -> LONG/SHORT, not an exit or a flip-to-flat).
Levels: S2 uses the levels the engine would set for that entry at the decision close (`live.plan_targets` / the book's own
stop rule, computed from the decision bar exactly as the book will when it fills), with the planned entry price E0 = that
decision close. If those levels cannot be known before the fill without duplicating the book's logic, S2 announces the side
and E0 only, and the stop/targets follow in the S1 card one bar later: say which in the implementation, decided before any
live result.

**Followable rules (fixed now), the same as S1 except the timing:** bar A = the bar in which the S2 alert is sent (the bar
the book will fill at its open, or later). Entry: a limit at E0 for the four 15-minute bars after A's open (bar A INCLUDED,
because the alert now arrives before or near A's open; a bar counts only from the alert time on: the first 15-minute bar
that opens after the alert is the first that counts). After the fill: half at Target 1, the rest at Target 2, stop to entry
after T1, same-bar = stop, gap through the stop at the open, the book's own exits followed one bar later as in S1. Costs:
the market's fee a side. Every rule not restated here is S1's (H53 with its 17 Nov amendment).

**Judged on live S2 signals only,** from the first signal sent by the deployed preview, beside S1 on the SAME entries:
(1) S2's followable record through the scoreboard's rule (mean per filled trade, 90% range); (2) the paired comparison per
signal: S2's result minus S1's result for the same `b_targets` entry, mean and 90% range; (3) fill rates of both. Interim
reading at 30 filled S2 trades. S2 replaces S1 as the subscriber signal only if, at 100 paired signals over at least 60 days,
S2's mean result per signal is higher than S1's with the paired 90% range above zero; the owner decides then. Counted as one
variant. A pass is a reason to propose, not proof of an edge.

**Preview only** until the owner says otherwise: S2 cards go to the owner's own Telegram chat beside the S1 preview,
labelled as an early-signal preview; the vault feed and the website keep using S1/`b_targets` as today.

### H15 / P10: retired (owner, 19 Nov 2026)

Owner: "Post-mortem, then retire", after the scoreboard verdict "behind: even the high end of the range is negative".
Live record at the post-mortem (`research/out/p10_postmortem.md`, a replay on the server's bars that matched its page):
120 trades, 41.7% won, -$2,018 (fees $1,188, 59% of it), -0.14R a trade before costs and -0.36R after; 1 of 6 markets
positive (gold); the pass bar was above +0.05R after costs with 4 of 6 markets positive. Conclusion: there is no magnet.
Price reached the round number before the equally distant stop only 42% of the time (a coin flip would give 50%), so
the rule lost even before costs, as it did on 2019-2026 history (-0.02R before costs, every market negative after); the
1R / 1R bracket then needs about 61% wins to cover a median 0.20R round trip, and the trigger fires about 15 times a day.
No code bug was found. No improved variant is proposed; any change would be a new registered hypothesis, only on the
owner's word. `engine15/playbook3.py` RETIRED: no trade entered from **2026-11-19 04:00 UTC** counts; the live record
before it is kept as is. The verdict rule (200 trades or 30 days) was not reached; retired early on the owner's word.
### H56 note: implementation choice: side and E0 at the decision, stop and targets one bar later (19 Nov 2026, 03:56 UTC; decided from the code only, before any S2 code ran on live data and before any live S2 signal existed)
- **S2 announces the side and E0 only; the stop and the two targets follow one bar later**, as a reply to the S2 card (the
  same levels the S1 card shows). Why: the book sets them AT THE FILL, from the fill price. `shadows.run` -> `open_pos`
  takes entry = the next bar's OPEN, stop = entry - side x stop_units x unit (unit at the decision bar), and
  `live.plan_targets(side, entry, stop, readings of the decision bar)`; the day's-travel and 1.5R/2R targets and the
  Fibonacci 0.5R-4R test all move with that open, which is unknown at the decision close. The bot reads only the page,
  whose `b_targets` view carries `next_open` but neither the barrier unit nor the readings row; computing them would
  duplicate the book's logic (or change `shadows.py`), which H56 excludes.
- **The followable record uses the book's own levels**, from the page when the position appears, or from the book's
  closed-trade file (stop0, target_1, target_2) when the trade closed inside its fill bar (S1 never signals those) or the
  page first shows it with Target 1 already taken (the original stop is then no longer on the page). 1R = |E0 - S|.
  Bars are run through the S1 state machine only once the levels are known, from bar A on.
- **The window, as H56's text reads (nothing changed):** bar A = the 15-minute slot holding the send time; the limit lives
  in the four slots A..A+3 (valid until A's open + 60 minutes); a bar may fill only if it opens at or after the send time.
  The page is written after the decision close, so a page-driven alert always arrives after A's open: in practice bar A
  never fills and A+1..A+3 can. A stop or Target 1 trading in bar A or any later bar before the fill voids, as in S1.
- E0 = the close of the bar the page's shadow books have reached when the pending entry is first seen (the decision bar),
  read from the engine's own bar file. A late-feed market (gold, silver, WTI, Brent fill one bar later) shows the same
  pending on two pages: one signal.
- Pairing with S1 on the entry's `opened_utc`; a no fill counts 0 for either side; an entry S1 never signalled counts S1 as
  0 once the book's trade is closed. If the book's levels never become known (no position on the page and no closed-trade
  row 30 minutes after the pending is gone), the S2 signal ends "no fill" (sent, not a trade).

## H57. STOCK STANCES ON HISTORY: do the Setups page's single-stock stances (`engine15/stocks.py`) carry any information on pre-seal history? (registered 19 Nov 2026, 09:58 UTC, before any H57 code existed or any H57 number was computed)

**Prompted by:** the owner, 19 Nov 2026: "Test the stock stances on history". `engine15/stocks.py` publishes, for the Setups
page's top five US stocks, a LONG / SHORT / FLAT stance: the S&P 500 call's cards read on each stock's own bars plus the
market-wide cards as the S&P call has them, mixed with the index group's learned trust and refit voices, side by
`policy.decide` for a flat book with an idle clock of 0. It is live for paying members, labelled "not validated on single
stocks". One variant, fixed here; nothing below is tuned after seeing a number.

**Population (fixed now, in this order).** (a) The five: NVDA, ARGX, MU, T, DDOG. (b) The larger, less hand-picked sample:
the ten largest S&P 500 companies by index weight around the seal (Nov 2025, from memory of the weights, not looked up),
one ticker per company, NVDA not counted again (it is in the five): AAPL, MSFT, AMZN, GOOGL, AVGO, META, TSLA, BRK.B, JPM,
LLY. A ticker of (b) that has no Dukascopy CFD with 15-minute history starting on or before 2024-11-11 (at least a year
before the seal) is replaced by the next of WMT, ORCL, V, MA, XOM, NFLX, COST, in that order, until (b) has ten. The five
are never replaced: one without such history is reported as NOT TESTABLE (Yahoo's free 15-minute bars cover only the last
60 days, all after the seal; the card code reads 15-minute bars only, so Yahoo's 1-hour bars are not a clean substitute
and are not used). Availability is decided by probing Dukascopy's public files only (no outcome is looked at).

**Data.** Dukascopy's free BID minute candles of the stock CFD (`datafeed.dukascopy.com`, the format `extdata.read_dukascopy`
reads: flat zero-volume minutes dropped), aggregated to 15-minute bars keyed by open time, kept to US cash hours with
`extdata.open_mask("SPX", ..., calendar=False)` as `stocks.fetch_15m` keeps Yahoo's bars; a 15-minute slot with no traded
minute is absent. Splits: the series is checked against Yahoo's split-adjusted daily closes and any step at a split date is
removed by the split ratio (said per ticker in the report). Every row whose bar opens at or after 2025-11-11 00:00 UTC is
dropped at load. Downloads on the research server, paced at least 1 s apart, one connection, raw files under
`research/out/h57_stocks/raw/` (deleted after the 15-minute files are built).

**The stance, replayed as `stocks.py` makes it, at every US-hours 15-minute close where the S&P 500 also has a close:**
- Readings: `stocks.readings(bars15, daily, ticker)` (the engine's own card code, both placeholder shapes, the agreement
  rule). To reproduce the live situation (a 15-minute store that starts 60 days back, daily bars before it), the closes of
  each calendar month M are read from a window of the stock's 15-minute bars that starts 60 days before M's first day, with
  daily bars for every NY trading day before the window (built from the same Dukascopy 15-minute bars: the cash session's
  open, high, low, close, volume; Yahoo's daily bars are not mixed in). Only M's rows are kept. `stocks.REQUIRED` missing:
  no stance at that close.
- Market-wide cards (`stocks.MARKET_VOICES`), the release guard (`ec_next`) and nothing else from the S&P 500 call's
  readings at the same close, read from the index group's evidence store (`data/evcache/index`, read only, copied as
  `research/card_overlap.py` / `research/b_trail_history.py` copy it).
- The S&P model AS IT STOOD AT THAT CLOSE: the index group's voices walked forward weekly from the engine's birth by
  `leanprep.walk_forward_cached` on the copied rows (refits in a private folder `research/out/h57_stocks/fits/`, deleted
  after), the refit in force at that close (the week's refit, even prior applied, as the live call uses it); trust =
  `leanprep.trust_tail` with the index group's voting cards and the trust cap, exactly as `leanprep.prepare_live` forms it,
  at that close (what the S&P call's journal entry records), renormalised as `stocks.entry_trust` does. Never a model
  fitted on later data. Closes before the index model's first refit have no stance.
- Mix and side: `stocks.feature_vector`, `stocks.stance_odds`, `stocks.decide` (shock, tide, htf_bias from the stock's own
  row; guard from the S&P call's `ec_next`), unchanged.

**Grading (the engine's own):** `labels.triple_barrier` on the stock's 15-minute bars (consecutive cash-session bars, as
`stocks.grade_one` grades on the stored bars), unit = 1.5 x the stock's `atr1h` at the close, 26 bars. NEITHER is not
counted in hit rates.

**Measures.**
- Hit rate of LONG / SHORT calls (LONG right on UP, SHORT right on DOWN) against 50%, per ticker and pooled. The interval
  (Wilson 95%) is on NON-OVERLAPPING calls: per ticker, in time order, a call is taken only if the previous taken call's
  grade was known (its first touch or its 26th bar) before it; graded NEITHER calls still block. All calls (overlapping)
  are reported beside, without an interval. Pooling adds the tickers' non-overlapping calls (calls of different stocks at
  the same time are correlated through the market; a block bootstrap by trading day is reported beside, descriptive only).
- Brier score and log-loss of the two-way probability p = P(up) / (P(up) + P(down)) on every stance row (LONG, SHORT and
  FLAT) graded UP or DOWN, against the base rate = that ticker's own UP share over the same half (an in-sample constant:
  the yardstick is given an advantage); skill = 1 - model / base. Per ticker and pooled; descriptive, not in the pass bar.
- First half / second half split at the median date of the pooled graded LONG / SHORT calls; the same split date for
  every ticker.

**Pass bar (fixed now):** PASS only if (1) the pooled non-overlapping hit rate is above 50% with the Wilson 95% lower
bound above 50% in BOTH halves, AND (2) at least 40% of the tested tickers (6 of 15 when all 15 are tested; rounded up)
have a full-period non-overlapping hit rate above 50%. The five and the ten are also reported separately; the bar is on
all tested tickers together. A pass would only allow the page's label to say "tested on history" (no edge is claimed); a
fail means the page should say the stance showed no edge on history (the wording is the owner's call). The live record
the page already builds is unaffected either way.
### H57 note: data availability (19 Nov 2026, 10:12 UTC; from Dukascopy's file listing only, before any H57 number was computed)
- Dukascopy names its US stock CFDs `<TICKER>USUSD`; Meta Platforms' CFD still carries its old name `FBUSUSD` (live to
  2025). It is META's CFD, so META stays in the ten (the rule replaces a ticker only when it has no CFD); WMT is not used.
- ARGX and DDOG have no Dukascopy CFD: NOT TESTABLE, as registered. Tested: NVDA, MU, T (of the five) and the ten (AAPL,
  MSFT, AMZN, GOOGL, AVGO, META, TSLA, BRK.B, JPM, LLY): 13 tickers, so condition (2) of the pass bar needs 6 of 13.
- Daily bars for days before the minute downloads (which start 2020-10-01, 60 days before the index model's first odds
  in 2021) are built from Dukascopy's hourly candles of the cash-session hours (09:00-16:00 New York hour buckets), not
  from 15-minute bars; from 2020-10-01 on they are built from the 15-minute bars as registered.

### Verdicts, H57 (20 Nov 2026, 01:52 UTC): NO PASS

Run on the research server (`research/h57_data.py`, `research/h57_stocks.py`; report `research/out/h57_stocks/report.md`,
numbers `results.json`). 13 tickers tested (NVDA, MU, T of the five; ARGX and DDOG NOT TESTABLE: no Dukascopy CFD; the ten
AAPL, MSFT, AMZN, GOOGL, AVGO, META, TSLA, BRK.B, JPM, LLY), Dukascopy 15-minute cash-hours bars 2020-10-01 .. 2025-11-10
(1,284 days each, none missing; closes within 0.1% of Yahoo's daily closes after the split adjustments), stances from
2021-01-12 (the index model's first refit in force) to the seal: 408,523 replayed closes.

| condition (fixed at registration) | required | result | met |
|---|---|---|---|
| pooled non-overlapping hit, first half (before 2021-10-01 19:30 UTC) | > 50% and Wilson 95% lower bound > 50% | 55.4% (47.6% .. 63.0%, n 157) | no |
| pooled non-overlapping hit, second half | > 50% and Wilson 95% lower bound > 50% | 50.9% (43.4% .. 58.4%, n 167) | no |
| tickers with full-period non-overlapping hit > 50% | >= 6 of 13 | 7 (MSFT, GOOGL, AVGO, META, TSLA, BRK.B, LLY) | yes |
| **H57** | both | | **NO PASS** |

- Full period, pooled: 1,942 LONG/SHORT calls, 324 non-overlapping graded, 53.1% right (47.6% .. 58.5%; day-block
  bootstrap 46.7% .. 58.8%). The five: 45.1% (n 71); the ten: 55.3% (n 253, 49.2% .. 61.3%). The overlapping hit rate
  (57.7%) is inflated by clustered calls and carries no interval.
- The stance is almost never taken: 99.52% of closes FLAT, 0.46% LONG, 0.02% SHORT (the combined S&P odds on a stock
  rarely reach the 5-point bar; live since 17 Nov every logged stance has been FLAT too). Half of all graded calls fall
  before Oct 2021, so the "second half" covers four years with 167 non-overlapping calls.
- Probabilities: the two-way P(up) / (P(up) + P(down)) is WORSE than each ticker's own constant UP share on every one of
  the 13 tickers (Brier skill -0.0001 to -0.0058; pooled -0.0029; log-loss skill pooled -0.0021), in both halves pooled.
- Reading: no evidence that the stances carry information on these stocks. A pass would only have allowed "tested on
  history"; per the registration the page should say the stance showed no edge on history (wording: the owner's call).
  Nothing in the engine is changed by this verdict; the page's live record keeps building.

## Adoption note, think15-v5.2.5 (19 Nov 2026, ~21:30 UTC): H36's `be_t1` on USDJPY's main book. NOT a pass.

The owner switched USDJPY's main book to break-even after Target 1 (docs/CHARTER.md, same date). This is a rule
change on the owner's word, as v5.2's trust cap was; it is not a verdict on H36 and no H36 line is moved. What the
record says, unchanged: H36's history read is in-sample and seen; `be_t1` was 1 of 15 variants; it was ahead of
holding in 2 of 8 markets (BTC, USDJPY) and failed "better than hold" pooled; on USDJPY both it and holding lost
about $13,000 in the second half. Picking the one market where one variant won is a selection made after the
result. Forward, the comparison stays readable: the shadow `main` copy keeps hold-to-stop-or-flip on USDJPY, and
`b_be_t1` keeps running; their USDJPY lines and the main book's own are read at 30 closed forward trades, as
research/VERDICT_RULES.md says, and the owner decides then whether USDJPY keeps the rule.

## H59. HALF AT TARGET 1 + STOP TO ENTRY ON THE REST, on the main book's own entries: the history read of the rule the owner adopted for the S&P 500 (registered 20 Nov 2026, 03:23 UTC, before any H59 code existed or any H59 number was computed)

**Prompted by:** the owner, 20 Nov 2026, with the S&P 500 main book short from 7,626 and past its Target 1: "The snp 500
should close half of the profit now under mind 15 as TP1 already achieve"; of three ways to treat the other half he
chose: close half at Target 1, move the stop on the rest to the entry price, let the rest run until that stop or a flip.
**The owner adopted this rule for the S&P 500 main book before this read.** This read gates nothing, changes no rule and
moves no H36 line; it is shown to the owner beside the build.

**The one variant:** `half_be_t1` = `{"half_t1": True, "be_t1": True}` in `engine15/shadows.run`: half the position off
at Target 1 (`live.plan_targets` at entry; a limit at the target, filled when a bar reaches it, after the stop check),
the stop on the rest to the entry price from the next bar (only ever tighter), the rest out at that stop, the original
stop or a flip. It is the **16th exit variant counted on these entries** (H36's 15, plus b_targets and b_trail already
counted). H36 ran `be_t1` (full size) and half-at-Target-1 only with moving-average trails, never this combination.

**Frame: H36's in every respect.** Same entries (v5.1 odds as the live step forms them: evidence store read-only,
voices walked forward weekly from the 2020-01-01 birth by `leanprep.walk_forward_cached` with a private fits directory),
sizing, fees per side, protective stop, flips, mandate, $10,000 per market from the first session with odds, the same
eight markets in five groups, the same halves split date 2023-06-08, the same statistics per market and pooled (net
P&L, return, Sharpe on daily marked equity sqrt(365), max drawdown, trades, win rate, average win / loss, each half,
the exit mix, the gap to main). Window, primary: each market's start to the same last stored session H36 used
(13 Nov 2026; SPX 12 Nov 20:45 UTC) if the stored bars allow it. Secondary, reported beside it if it can be run:
to today's last stored session. Compared on the same run against `main` (hold to stop or flip), H36's `be_t1` and
`b_targets`. Code `research/h59_half_be.py` (imports `research/exit_study.py`'s machinery; H36's frozen outputs in
`research/out/exits/` are not touched), output `research/out/h59_half_be/` (`report.md`, `results.json`).

**Sanity check that decides whether the numbers can be trusted:** the re-run of `main` and `be_t1` over H36's window
must reproduce H36's per-market numbers (e.g. SPX main +$6,816 / 36 trades, be_t1 +$6,334; USDJPY main +$19,209,
be_t1 +$27,238). Any difference is reported with its size and cause; numbers that cannot be reconciled are not
presented as clean.

**What counts as better than holding** (exactly H36's): pooled net P&L above the main book's in BOTH halves, above it
in at least 5 of the 8 markets over the whole window, and pooled max drawdown no worse than the main book's.

**Read this plainly:** descriptive, in-sample, on history the project has already seen (H36 read these same entries
on 13 Nov), one variant chosen after H36's results were known and after the owner had chosen the rule. A pass would
not be proof and a fail does not reverse the owner's decision; the S&P 500 line is read first because that is the
market switched, and picking one market's line after the fact is a selection.

### H59 results (20 Nov 2026, ~04:15 UTC; `research/out/h59_half_be/report.md` + `results.json`): NOT better than holding

- **Reconciliation: H36 is reproduced exactly only on SPX** (main +$6,816 / 36 trades, be_t1 +$6,334 / 42, to the cent). On
  the other seven markets the main book itself differs from H36 (e.g. USDJPY main +$7,288 / 98 trades vs H36 +$19,209 / 120;
  XAUUSD +$22,717 / 115 vs +$17,712 / 134), so the entries differ, not the exit. Bars over H36's window are byte-identical and
  the code is identical; the inferred cause is that the evidence store on the server (rebuilt since, layout 2) is not the one
  H36 read on 13 Nov. The non-SPX absolute numbers here are not H36's; the four books are one consistent run on today's store.
- **SPX, H36's window:** main +$6,816 (36 trades, win 22%, DD -31.0%, halves -$688 / +$7,503); be_t1 +$6,334; b_targets +$724;
  **half_be_t1 +$4,528** (42 trades, win 43%, DD -21.7%, Sharpe 0.57 vs 0.55, halves -$463 / +$4,991): $2,288 less than holding.
  To the store's last session (19 Nov): main +$6,320, be_t1 +$5,851, half_be_t1 +$4,438.
- **Pooled, H36's window:** main +$316,391 (DD -32.8%); half_be_t1 +$101,170 (DD -15.6%, Sharpe 0.81 vs 0.90), behind main in
  both halves (-$78,560 / -$136,661) and in 8 of 8 markets. be_t1 +$144,648. To 20 Nov: main +$339,325, half_be_t1 +$107,974.
  Fails "better than hold" (drawdown passes; halves and markets fail). The owner's S&P 500 rule stands on his word; this
  read does not move it.

## H58. STOCKS' OWN MODEL ON HISTORY: do cards rated on stock history and voices trained on stock history call single-stock direction better than chance? (registered 20 Nov 2026, 02:50 UTC, before any H58 code existed or any H58 number was computed)

**Prompted by:** H57's NO PASS (the S&P model borrowed for single stocks). The owner, 20 Nov 2026: "I think need to make
sure the result proven. Rather change description or remove. If snp500 cannot apply a single stock. Recommend me a better
option"; offered "give stocks a model of their own, as each market group got on 11 Nov (v5.1)", the owner: "Yes, build it".
PAPER ONLY; research only; nothing in engine15/ is changed by this test.

**What was already seen (disclosure).** H57's results (report and verdict above): the 13 tickers' bars, the borrowed
model's hit rates per ticker and half, its Brier skill. No reading's direction accuracy on stocks, no card rating on stocks
and no stock-trained voice has been looked at. The design below is written from the engine's own methods, not from H57's
numbers.

**Population and data (fixed now).** The 13 tickers H57 tested: NVDA, MU, T, AAPL, MSFT, AMZN, GOOGL, AVGO, META, TSLA,
BRK.B, JPM, LLY. ARGX and DDOG (on the live page) have no 15-minute history: NOT TESTABLE, reported as such. Bars: H57's
files on the research server (`research/out/h57_stocks/bars/`, Dukascopy CFD 15-minute cash-hours bars 2020-10-01 ..
2025-11-10, daily bars before), not downloaded again. The S&P 500's 15-minute bars: the engine's `data/spx_15m.csv`,
copied read-only into the H58 folder, rows before the seal. Every row whose bar opens at or after 2025-11-11 00:00 UTC
(the sealed holdout) is dropped at load and never computed on.

**Readings (per stock, per 15-minute close).**
- The engine's own cards on the stock's bars exactly as `engine15/stocks.py` makes them live: `stocks.readings` on a
  window of the stock's 15-minute bars starting 60 days before the close's calendar month, daily bars before the window
  (H57's `month_readings`), only that month's rows kept. Rows from 2020-12-01 on (the first month with a full 60-day
  window). The market-wide cards (`stocks.MARKET_VOICES`: macro, volx, rates, eqbreadth) and the release guard (`ec_next`)
  from the S&P call's readings at the same close (H57's `spx_model.npz`, copied from the index store); a close with no
  S&P row has no stance. Index-only and live-only cards (`stocks.SKIP_VOICES`) read nothing, as live.
- Two stock-only readings, each its own new card and voice:
  - **Strength against the S&P 500** (voice `stk_rs`): d = the stock's 15-minute log return minus the S&P 500's over the
    same bar (bars joined on open time; a bar without an S&P bar is no read); rs_k = clip((sum of the last k d) /
    (std of d over the last 672 bars x sqrt(k)), -3, 3) for k = 4 (an hour), 26 (a session), 130 (five sessions), the
    scaling the engine's momentum readings use.
  - **Own earnings date** (voice `stk_ern`), from the engine's existing megacap earnings file only
    (`data/sources/earnings_megacap.csv`, copied read-only; 2018-2026, four reports a year for NVDA, AAPL, MSFT, AMZN,
    GOOGL, META, AVGO, TSLA, BRK.B, JPM), with `equity_events`' own release times and KNOWN-AT rule (a backfilled date is
    known 7 days before the report): ern_next = clip(1 - days to the next known report / 7, 0, 1); ern_last = clip(1 -
    days since the last report / 5, 0, 1). MU, T and LLY are not in that file and no other clean free history of their
    dates is used: for them this card reads nothing (0), stated, not filled in.

**Grading (the engine's own, as H57):** `labels.triple_barrier` on the stock's consecutive 15-minute bars, unit = 1.5 x
the stock's `atr1h` at the close, 26 bars; NEITHER not counted in hit rates.

**The model (primary specification; one variant decides the verdict).** The engine's own model code and constants,
the 13 stocks pooled as the engine pools a group's assets, WALKED FORWARD:
- Timeline: the union of the 13 tickers' bar open times. Refits every 672 sessions of that timeline (`refit_every`, about
  26 trading days, the cadence the live S&P call refits at); the first refit at the first session on or after 2022-01-03
  00:00 UTC; each refit's model answers the sessions up to the next refit.
- At each refit, ONLY rows whose grade was known by that refit's close (the ticker's 26th bar after the row has closed by
  then, i.e. the engine's t <= s - horizon rule, per ticker), from 2020-12-01 on, with the required readings
  (`stocks.REQUIRED`), are used, for both:
  1. **Card rating and selection** (research/rate_cards.py's method, its own functions): every card that reads on a
     stock (the 41 engine cards with an own or market voice, plus the two new cards) rated on those rows pooled: per
     reading, the most extreme fifth, direction accuracy of its sign in the first and second half (split at the median
     training row), steadiest reading per card, worse half; the top ten cards with a worse half above 50.5% vote (at
     least the three best) (`rate_cards.choose_voting`). The owner's voice is not used (it never reads on a stock).
  2. **Voice training**: one voice per engine voice that reads on a stock (40 own + 4 market) plus `stk_rs`, `stk_ern`,
     "all" (every stock feature) and "base", each `model.fit_softmax` on the training rows subsampled every 16th row per
     ticker (`train_step`), ridge `l2` 100, warm-started from the previous refit, `even_prior`, at least `min_train_rows`.
- Trust: `model.trust_path`'s Hedge (eta 0.2, half-life 960 sessions, floor 0.02) on the walked-forward voices' graded
  direction losses of all 13 tickers on the common timeline, a loss arriving at its grade's close; masked to the refit's
  voting voices, renormalised, capped at 40% (`trust_cap`), then per row over the voices that speak, capped again
  (`stocks.stance_odds`). Odds = the mix.
- Stance: `stocks.decide` (policy.decide for a flat book, idle clock 0: 5 points, 10 in high risk, 15 against the
  higher-timeframe bias, none in the hour before a high-impact US release), shock / tide / htf_bias from the stock's own
  readings, the guard from the S&P call's `ec_next`.
- Judged: every close from the first refit (2022-01-03) to the seal. No call is ever made by a model, a card choice or a
  trust that saw the row's own outcome or any later row. (A clean single cut was considered; the walk-forward is chosen
  because it is how the live engine itself learns, it judges almost four years instead of two, and card selection and
  training are redone inside every training window, so selection never sees the judged rows.)

**Measures (as H57, so the two sit side by side):** pooled and per-ticker hit rate of LONG / SHORT calls on
NON-OVERLAPPING calls (per ticker, a call taken only once the previous taken call's grade is known; NEITHER blocks but is
not counted), Wilson 95%; all calls beside without an interval; halves split at the median date of the pooled graded
LONG / SHORT calls; day-block bootstrap (descriptive); Brier and log-loss skill of p = P(up) / (P(up) + P(down)) on every
stance row graded up or down against the ticker's own UP share in the same half; the share of closes with a stance;
H57's own rows restricted to the same judged dates (2022-01-03 on) beside, for a like-for-like comparison. Also: which
cards voted at each refit, the two new cards' ratings at each refit, the voting voices' trust.

**Pass bar (fixed now, H57's):** PASS only if (1) the pooled non-overlapping hit rate is above 50% with the Wilson 95%
lower bound above 50% in BOTH halves, AND (2) at least 6 of the 13 tickers have a full-period non-overlapping hit rate
above 50%.

**Leave-tickers-out check (registered now; a check, not the verdict):** the same walk-forward 13 times, each time
with one ticker left out of everything (card rating, voices, trust) and judged by that model. The 13 held-out sets are
pooled and measured as above. Reading: if the primary passes but this check does not meet the same bar, the model is
not shown to carry over to stocks it did not learn from, and the live page (whose list includes stocks with no history
at all) may not say "tested on history" for an untrained ticker.

**Variants (counted):** the primary decides. Exploratory, reported and labelled so, never the verdict: E1 = the primary
without the two stock-only cards (to show what they add). Nothing else is planned; anything more tried is added to this
count in the report. No tuning and re-grading after seeing a number: a fail is reported as a fail.

**What a result changes.** PASS: a historical pass is not proof (research/VERDICT_RULES.md); it allows a PROPOSAL to the
owner to run this model forward on paper on the page, labelled "tested on history, being checked live", confirmed only by
forward graded calls; wiring it into `engine15/stocks.py` needs the owner's word and is described, not done. NO PASS: the
stocks' own model is not supported on history either; the page's wording and whether to keep the section is the owner's
call ("not confirmed on history").

**Where it runs:** the research server, `research/h58_stocks.py`, outputs under `research/out/h58_stocks/`, under
`nice -n 10`, the heavy-job lock, never touching the live engine's files.

### Verdicts, H58 (20 Nov 2026, 03:40 UTC): NO PASS

Run on the research server (`research/h58_stocks.py`; report `research/out/h58_stocks/report.md`, numbers `results.json`,
the primary's per-refit card choices and trust `refits_primary.json`). 13 tickers, 325,705 judged closes 2022-01-03 ..
2025-11-10 (38 refits), nothing on or after the seal.

| condition (fixed at registration) | required | result | met |
|---|---|---|---|
| pooled non-overlapping hit, first half (before 2023-03-14 15:45 UTC) | > 50% and Wilson 95% lower bound > 50% | 40.2% (31.6% .. 49.4%, n 112) | no |
| pooled non-overlapping hit, second half | > 50% and Wilson 95% lower bound > 50% | 57.2% (49.8% .. 64.4%, n 173) | no |
| tickers with full-period non-overlapping hit > 50% | >= 6 of 13 | 6 (MSFT, GOOGL, AVGO, META, BRK.B, JPM) | yes |
| **H58** | both | | **NO PASS** |

- Full period, pooled: 2,537 LONG/SHORT calls, 285 non-overlapping graded, 50.5% right (44.8% .. 56.3%; day-block
  bootstrap 40.9% .. 60.0%). The halves point opposite ways (40% then 57%). Overlapping hit rate 47.0%.
- Stance taken on 0.78% of closes (0.54% LONG, 0.24% SHORT); H57: 0.48%.
- Probabilities: Brier skill against each ticker's own UP share negative on 12 of 13 tickers (MU +0.0005), pooled -0.0021;
  log-loss skill pooled -0.0015; negative in both halves pooled.
- Leave-one-ticker-out (check): 52.8% (47.2% .. 58.3%, n 307); halves 50.4% (lower 41.4%) and 54.2% (lower 47.1%); 7 of
  13 tickers above 50%: does not meet the bar either.
- E1 (exploratory, without the two stock-only cards): 50.7% (n 365), halves 39.8% and 55.6%: NO PASS; the two cards
  changed little.
- H57's own rows on the same dates (2022-01-03 on): 49.6% (n 133). The stocks' own model is not better than the borrowed
  one on these numbers.
- The two stock-only cards: strength against the S&P 500 rated at most 51.0% in its worse half and never made the top
  ten. Own earnings date (10 megacaps only) voted at 26 of 38 refits, always "against" (near or just after a report the
  next move was more often down in the training rows), but with 0.5% of the mean say it barely moved the odds.
- Card choice was unstable: consecutive refits shared 6 to 10 of their 10 cards (8 most often). Only the Ultimate
  Oscillator (37 of 38) and economic calendar (36) voted almost every time.
- Reading: no evidence that a model rated and trained on stock history calls single-stock direction better than chance
  on 2022-2025. Per the registration, the page's wording and whether to keep the section is the owner's call ("not
  confirmed on history"). Nothing in the engine is changed by this verdict.

Disclosed departures and details: the registration's heading says 02:50 UTC; its commit is 02:46 UTC. The prep stage (read-only copies of
`data/spx_15m.csv` and `data/sources/earnings_megacap.csv`) ran at 02:49, after the registration commit and before the
code commit (02:52). A smoke test of the walk on 2 tickers and 1-2 refits checked only that it ran (no hit rate printed).
The relative-strength volatility uses at least 600 of the last 672 bars (`min_periods`), a detail the registration did
not fix. OpenBLAS was limited to one thread (speed only; no effect on the numbers). The first report run failed on a
formatting bug after the numbers were computed and before any were printed; fixed and re-run. The "all" voice uses the
305 stock features only (the engine's other features are always zero on a stock). Variants: the primary, E1 and the
registered leave-one-ticker-out check; nothing else was run.

## Adoption note, think15-v5.2.6 (20 Nov 2026, ~04:00 UTC): half at Target 1 on the S&P 500's main book. NOT a pass.

The owner switched the S&P 500's main book to: half closed at Target 1, the stop of the rest to the entry, the rest
out at that stop or on a flip (docs/CHARTER.md, same date). A rule change on the owner's word. When it was made,
no history number existed for this exact rule: H36 had `be_t1` at full size (S&P +$6,334 against +$6,816 for
holding) and half-at-Target-1 only with moving-average trails or, in `b_targets`, with the rest out at Target 2
(+$1,018). H59 (registered separately, the same day, by the agent that runs it) reads this rule on history; it was
started after the decision and cannot have informed it. Forward: the shadow `main` copy keeps hold-to-stop-or-flip
on the S&P, `b_be_t1` and `b_targets` keep running, and the lines are read at 30 closed forward trades.

## H60. EXITS BY REGIME, PER MARKET: flip exits in directional regimes, target exits in the others; and one exit rule per market instead of one for all (registered 20 Nov 2026, 11:43 UTC, before any number is computed)

**Prompted by:** the owner, 20 Nov 2026, after the USDJPY post-mortem (`research/out/usdjpy_postmortem_20261120.md`):
"Also test the idea of regime. If is momentum up or momebtum down. Using edge flip scoring to take profit is better. But
other regime is better to follow TP level. Also treat all the assets at different condition and setup. Should not use
one setup for all assets."

**The regime** is the engine's own daily label, `ev["regime"]` (`indicators.regime_daily`, the last CLOSED daily bar
joined to the 15-minute rows by `data.htf_on_15`): TREND_UP, TREND_DOWN, MOMENTUM_UP, MOMENTUM_DOWN, RANGE, TRANSITION.
The owner's "momentum up or momentum down" is read two ways, both frozen here:

- **directional** (primary reading): TREND_UP, TREND_DOWN, MOMENTUM_UP, MOMENTUM_DOWN. The label MOMENTUM needs a 5-day
  move of 8% with expanding range, which USDJPY and the S&P 500 almost never make, so the literal reading alone would
  leave those markets with one rule.
- **momentum only** (literal reading): MOMENTUM_UP, MOMENTUM_DOWN.

**The two exit modes** are the two the engine already has, unchanged:

- **flip mode** = the main book's rule: out at the protective stop or when the odds flip (10 points), nothing else.
- **target mode** = the Setups book's rule (`b_targets`): half at Target 1, the stop of the rest to the entry from the
  next bar, the rest at Target 2 (targets from `live.plan_targets` at entry).

**The five variants** (frozen; exit variants 17 to 21 counted on these entries, after H36's 15, `b_targets`/`b_trail`
and H59's one):

1. `rg_dir_entry` (PRIMARY): the mode is fixed for each trade by the regime at its entry decision bar: directional ->
   flip mode, otherwise -> target mode.
2. `rg_dir_aligned`: as 1, but flip mode only when the regime points the trade's way (TREND_UP or MOMENTUM_UP for a
   long, TREND_DOWN or MOMENTUM_DOWN for a short); a directional regime against the trade is target mode.
3. `rg_dir_live`: the mode follows the regime bar by bar: a target is acted on only in a bar whose regime is not
   directional; a target reached while the regime is directional is passed by and is acted on later only if the bar
   that reaches it again is in a non-directional regime. Once half is off at Target 1 the stop stays at the entry.
4. `rg_mom_entry`: as 1 with "momentum only" in place of "directional".
5. `rg_dir_entry_inv` (the CONTROL, the owner's idea turned round): directional -> target mode, otherwise -> flip mode.
   If the idea holds, this must do worse than variant 1.

Nothing else is varied: the flip bar stays 10 points (a lower bar would also change entries and is another
hypothesis), no trail, no new target formula.

**Frame: H59's "today" frame in every respect.** The main book's own entries (odds as the live step forms them:
evidence store read-only, voices walked forward weekly by `leanprep.walk_forward_cached` with a private fits
directory), sizing, fees per side, protective stop, flips, mandate, $10,000 per market, eight markets in five groups,
halves split 2023-06-08, the same statistics (net P&L, return, Sharpe on daily marked equity, max drawdown, trades,
win rate, average win / loss, each half, exit mix, gap to main). Window: each market's start to the last session of
H59's "today" run (20 Nov 2026 03:45 UTC or the group's own), cut by H59's `prep_cut`, so that `main`, `be_t1`,
`b_targets` and `half_be_t1` here must reproduce `research/out/h59_half_be/today_<group>.json` exactly. **If they do
not, the difference is reported and no H60 number is presented as clean.**

**Code:** `research/h60_regime_exits.py`, output `research/out/h60_regime_exits/` (`report.md`, `results.json`). The
book runner is a copy of `engine15/shadows.run` kept inside the study with one added input, a per-trade / per-bar
"targets active" switch; `engine15/shadows.py` (the money path, pinned by `tests/test_money_path_golden.py`) is NOT
edited. The copy must reproduce `shadows.run` trade for trade with the switch always off (= `main`) and always on
(= `b_targets`) on every market before any variant is read.

**Three things are read, in this order.**

*(a) The idea itself, on the two existing books (no new variant needed).* Every closed trade of `main` and of
`b_targets` is put in the bucket of the regime at its entry decision bar. Per market and pooled, per bucket
(directional / other; and the six labels): trades, net P&L, mean per trade, win rate, for each half. The owner's
idea says: in the directional bucket `main` earns more per trade than `b_targets`, and in the other bucket
`b_targets` earns more than `main`. **It is called supported only if both hold pooled in BOTH halves and in at least
5 of 8 markets over the whole window.** (The two books do not hold the same trades after their first exit differs;
the table compares what each rule earned from the entries it took in that regime, which is what a rule switch would
get.)

*(b) The five variants as whole books.* "Better than holding" is H36's test, unchanged: pooled net P&L above the main
book's in BOTH halves, above it in at least 5 of the 8 markets over the whole window, and pooled max drawdown no worse.
Read for variant 1 first. Variant 1 against its control (5): the idea needs 1 above 5 pooled in both halves.

*(c) One rule per market.* Menu (frozen, 8 rules): `main`, `be_t1`, `half_be_t1`, `b_targets`, `rg_dir_entry`,
`rg_dir_aligned`, `rg_dir_live`, `rg_mom_entry`. For each market the rule with the highest net P&L in the FIRST half
(to 2023-06-08) is picked; ties go to the earlier name in the menu. Its SECOND-half result is then set beside the
main book's second half. **"A rule per market helps" only if the picks, pooled, beat the main book's pooled second
half AND do so in at least 5 of 8 markets.** Also reported, as description only: each market's best rule over the
whole window and how far that pick agrees with the first-half pick.

**Read this plainly.** In-sample history that this project has already read four times for exits (H36, H59): the
second half is not untouched for `main`, `be_t1`, `b_targets` and `half_be_t1`, and five more variants on the same
entries make 21 looked at. The numbers of these studies have moved by thousands of dollars between runs when the
readings store was rebuilt. A pass is not proof of anything and gates nothing by itself; a fail does not stop the
owner from choosing a rule. Whatever the owner adopts runs forward beside the `main` copy and is read at 30 closed
forward trades per market, as agreed for the other exit books. Paper only; the vault's book is not touched.

### H60 results (20 Nov 2026, 11:51-11:57 UTC on the research server; `research/out/h60_regime_exits/report.md` + `results.json`, per-group `today_<group>.json`)

- **Equivalence gate: passed on all 8 markets.** The study's copy of `shadows.run` with the switch always off gave
  `main`'s trades and always on gave `b_targets`' trades (same rows, words, prices, sizes, fees, P&L within $0.000001,
  same final equity and open position), e.g. USDJPY 98 / 721 trades, SPX 37 / 239.
- **Reconciliation with H59's "today" run: reproduced exactly.** `main`, `be_t1`, `b_targets`, `half_be_t1` on all 8
  markets to the cent and trade (pooled main +$339,325, 1,080 trades). The H60 numbers below are one clean run.
- **(a) The idea on the two existing books: NOT SUPPORTED.** Per trade, pooled: in directional regimes `main` earned
  more than `b_targets` in the first half (+$467 vs +$6) but not in the second (-$1,501 vs -$25, 36 main trades); in the
  other regimes `b_targets` earned less than `main` in both halves (first -$5 vs +$160, second -$1 vs +$466). Both parts
  held over the whole window in 1 of 8 markets (XAGUSD; 5 needed). 920 of main's 1,080 trades start on a RANGE or
  TRANSITION day, and RANGE alone carries +$221,532 of main's money.
- **(b) Variant 1 `rg_dir_entry`: NOT better than holding.** Pooled +$41,188 vs main +$339,325; halves vs main
  -$127,865 / -$170,273; ahead of main in 2 of 8 markets (SPX, XAGUSD); max DD -36.7% vs -32.8%. **Against its control
  (variant 5 `rg_dir_entry_inv`, +$232,932) variant 1 is behind in both halves (-$78,386 / -$113,359): the idea does
  not hold.** No variant passes (aligned +$37,315; live -$43,404; momentum-only -$6,942; control +$232,932, 4 of 8).
- **(c) One rule per market: does NOT help.** First-half picks: SPX `rg_dir_entry`, USDJPY `be_t1`, BTC `be_t1`, ETH
  `main`, XAU `half_be_t1`, XAG `main`, WTI `be_t1`, BRENT `be_t1`. Second half, picks together +$137,211 vs main
  +$186,970; ahead of main in 1 of 8 (SPX: +$9,153 vs +$7,007). The whole-window best rule agrees with the first-half
  pick in 3 of 8 markets.
- **USDJPY:** main +$6,965, `rg_dir_entry` +$1,403, control +$7,657, `be_t1` +$9,061 (best both on the first half and the
  whole window, but -$7,743 vs main -$7,497 in the second half). MOMENTUM: 0 days of 2,067. Directional 19.5% of sessions,
  2 of main's 98 trades. **S&P 500:** main +$6,320, `rg_dir_entry` +$9,268 (halves +$115 / +$9,153; 75 trades in target
  mode, 13 in flip mode), control +$6,486. MOMENTUM: 5 days of 1,472 (0.4% of sessions); directional 20.6% of sessions,
  1 of main's 37 trades. One market's line picked after the fact is a selection, and the pooled test fails.
- Regime shares (sessions; full table in the report): directional 18.6% (BRENT) to 26.2% (ETH); MOMENTUM 0.0% USDJPY,
  0.4% SPX, 0.6% XAU, 4.0% XAG, 7.3% WTI, 6.4% BRENT, 8.9% BTC, 12.5% ETH.

Disclosed departures and details: the runner copy keeps every code line of `shadows.run` (two comments shortened); the
switch replaces `use_targets` per trade, and per bar in `rg_dir_live`; with the switch on, a stop after Target 1 is
worded `STOP_BE` as in `b_targets`. In `rg_dir_live` the regime of bar i is the label on row i - 1 (known before the bar
trades; row i already holds the daily bar that bar i closes); the registration said "a bar whose regime", not which row.
Halves in (a) and (c) are split by each trade's exit bar, as H59's half statistics are; no row in these windows lacked a
label. Means in (a) are dollars per trade (ETH weighs most pooled); percent means are in results.json. (c)'s sums are
per-market half results added (main's equals the pooled-curve second half, +$186,970). H59's cached refits
(`fits_today`) were copied into H60's own folder on the server, so no refit was computed (all from the cache); the
reconciliation then held exactly. The heavy-job lock was taken per group. Code on the server: this branch's
`research/h60_regime_exits.py` as of commit 93c129c (the later edits change report wording only, no number) with the
server's deployed engine15 at think15-v5.2.6 (`shadows.py` there predates main's held_share/PART comment edit; `run()`
is identical). No smoke test was run; the five groups ran once each (fx first, then index, energy, metals, crypto, about
6 minutes in all); the report was written once on the server and once more locally from the same group files after the
wording edits. The live step stayed at 133-150 s during the runs.

## Adoption note, think15-v5.2.7 (20 Nov 2026, ~11:50 UTC): USDJPY's main book sells at both targets. NOT a pass.

The owner switched USDJPY's main book to the Setups book's exit rule: half closed at Target 1, the stop of the rest to
the entry, the rest closed at Target 2 (docs/CHARTER.md, same date; "Sell at target"). The 4-session mandate stays
("Still follow our rules"). A rule change on the owner's word after a post-mortem of one trade
(`research/out/usdjpy_postmortem_20261120.md`), not on a test: the history numbers that exist for this rule on USDJPY
are below holding (H36 `b_targets` +$2,939 against `main` +$19,209; H59's re-run -$394 against +$7,288), and the ten
live days cannot rank the rules. H60 above was registered at 11:43 UTC, before this change was built, and had computed
nothing when it was adopted, so it cannot have informed it. Forward: the shadow `main` copy keeps hold-to-stop-or-flip
on USDJPY, `b_be_t1`, `b_targets` and `b_trail` keep running, and the lines are read at 30 closed forward trades.


## H61. A WIDE PROFIT FLOOR FOR THE MAIN BOOK'S BIG WINNERS: a stop that leaves a winner room and bites only on a real reversal, with no re-entry of its own (registered 21 Nov 2026, 01:35 UTC, before any H61 code existed or any H61 number was computed)

**Prompted by:** the owner, in the site-coordination session, 21 Nov 2026 ~01:30 UTC, relayed by that session: "Lets
monitor all assets for minds15. As currently all are in profit. It is crucial to see what is the optimal way to capture
the profit." That session read `page.json` (01:17 UTC): six main-book shorts 2 to 10 R in open profit, nothing banked,
every stop still the entry stop. It asked for this study and named the three rule families below.

**The gap this fills.** H36, H59 and H60 tested only TIGHT exits on these entries (15m / 1h moving-average trails armed
at 1R or Target 1, the 1R ATR trail `b_trail`, break-even and targets), and every one of them lets the book re-enter on
its own clock after the exit, so a trail exit is followed by a forced entry four sessions later. No study has tested a
WIDE floor that arms only on a large winner, and none has held the book flat after such an exit.

**The six rules** (frozen; exit variants 22 to 27 counted on these entries). R = |entry - entry stop| of the trade.
"Open profit" is read at 15-minute CLOSES only; a level set at the close of bar i is a stop order from bar i + 1,
filled like the book's own stop (at the level, or at the bar's open if the bar opens through it); a level only ever
tightens and is never looser than the entry stop.

1. `floor_50pct_5r` (PRIMARY): once a close shows open profit of at least 5R, the stop sits at
   entry + 50% of the best close's open profit (it locks half of the peak, and moves up with every better close).
2. `floor_50pct_3r`: the same, armed at 3R.
3. `floor_33pct_5r`: armed at 5R, locks one third of the peak.
4. `floor_33pct_3r`: armed at 3R, locks one third of the peak.
5. `chandelier_4h_3atr_3r`: once a close shows 3R, the stop trails 3 x ATR(14, Wilder) of the 4-hour chart (last
   CLOSED 4h bar, joined by `data.htf_on_15`) behind the best close since entry.
6. `swing_4h_5r`: once a close shows 5R, the stop trails the last CONFIRMED 4-hour swing against the trade (swing low
   for a long, swing high for a short; the engine's own definition, `sources/structure.swings` with 3 bars either
   side, known only after the third later 4h bar closes). A swing on the wrong side of the close is not used.

In all six the main book's own exits stay: the entry stop until a rule arms, and the flip.

**No re-entry of its own.** Each rule is an OVERLAY on the main book's own trades: it takes every main trade at the
main book's fill, bar and price; it leaves either at its own level or, if that never fills, exactly where the main
book left; after an exit at its own level it stays FLAT until the main book's next entry. The size of each trade is
the main book's size scaled by (this book's equity / the main book's equity) at the entry, which is exact because the
main book's size is equity x a leverage that does not depend on equity. Fees per side as the main book's.

**Frame: H60's frame in every respect** (which is H59's "today" frame): the main book's entries with the odds as the
live step forms them (evidence store read-only, voices walked weekly with a private fits directory), $10,000 per
market, eight markets in five groups, the window cut at the last session of H59's "today" run per group (20 Nov 2026
03:45 UTC or the group's own), halves split 2023-06-08, the same statistics (`exit_study.seg_stats`). `main` is
`shadows.run` under the main rule, as in H36 / H59 / H60 (hold to the stop or the flip; it does NOT include the
half-at-Target-1 rules the live book has had for USDJPY and the S&P 500 since v5.2.6 / v5.2.7).

**Gates before any variant is read.** (i) The overlay with a rule that never arms must reproduce `main` on every
market: every trade's P&L and the marked equity at every bar within $0.000001. (ii) `main` here is set beside H60's
`today_<group>.json`; the readings store was rebuilt at the v5.2.7 deploy (20 Nov, after H60), so if the numbers
differ the difference is reported; the comparison inside H61 (rules against the `main` of the same run) stays like
for like either way.

**Three things are read, in this order.**

*(a) Whole books, H36's test unchanged.* A rule is "better than holding" only if its pooled net P&L is above the main
book's in BOTH halves, above it in at least 5 of the 8 markets over the whole window, and its pooled max drawdown is
no worse. Read for rule 1 first. Reported for each rule: whole window, each half, markets beating main, pooled and
per-market max drawdown, trades that armed and trades the rule closed.

*(b) The same question at equal size.* The pooled dollars are dominated by compounding in one market (ETH was
$240,638 of the main book's $339,325 in H60), so one long hold decides (a). So, per trade that ARMED the rule: the R
the rule ended with minus the R the main book ended with on the same entry (both on the entry risk; no compounding).
"The rule helps per trade" only if the mean difference is above zero pooled in BOTH halves and in at least 5 of the
markets that had an armed trade. Also reported: how many armed trades the rule improved, how many it cut short, and
the worst give-back of each side (the largest R the main book lost from the peak close; the largest R the rule left
on the table).

*(c) Today's open trades (description only, not a test).* For each open main-book trade on the live book at the time
of the run: whether each rule would be armed, the level it would have now, the dollars that level locks at the live
size against the open profit, and whether it would already have closed the trade (when, where, and what the trade
has done since).

**What follows from the result.** If rule 1 (or another of the six) passes (a), it is proposed to the owner as a
FORWARD shadow book beside the main book, read at 30 closed forward trades like the other exit books. If none passes
(a) but one passes (b), that is said plainly, with the same proposal as a shadow only. If none passes either, no
shadow is proposed. Nothing here changes the main book, the Setups book or the vault's feed: any change to a book is
the owner's decision in this project.

**Read this plainly.** In-sample history that this project has now read five times for exits; 27 exit variants on the
same entries. A floor armed at 5R acts on a handful of trades per market, so its whole-window number rests on very
few events and the second half is not untouched. A pass is not proof; a fail does not stop the owner from choosing a
rule. Paper only.

**Code:** `research/h61_profit_floor.py`, output `research/out/h61_profit_floor/` (`report.md`, `results.json`),
tests `tests/test_h61.py`. No engine file is edited.

### H61 note: implementation choices (21 Nov 2026, written with the code, before any number was read)

- Reading (b) counts only armed trades the main book has CLOSED; a trade still open at the window's end has no
  main-book result and is left out (it appears in (c) if it is a live trade).
- R in (b) is on prices before fees (the same fee per side applies to both books).
- The 4-hour bars are built from the 15-minute sessions the store holds (for the S&P 500, cash hours only), as
  the engine's own 4h readings are.

### H61 results (21 Nov 2026, 01:39-01:40 UTC on the research server; `research/out/h61_profit_floor/report.md` + `results.json`)

- **Gates: passed.** The overlay that never arms reproduced `main` on all 8 markets (every trade and the marked
  equity at every bar), and `main` reproduced H60's run exactly (pooled +339325, 1080 trades, max DD -32.8%).
- **(a) Whole books.**
  - `floor_50pct_5r`: +457871 (+118545 vs main; first half -1442, second half +119987; 5 of 8 markets; max DD -23.8%; better than holding: no). Per armed trade (189, 150 closed by the rule): -0.71R on average (first half -0.42R, second -1.03R; 111 better, 39 worse).
  - `floor_50pct_3r`: +300397 (-38928 vs main; first half -39165, second half +237; 4 of 8 markets; max DD -15.2%; better than holding: no). Per armed trade (267, 234 closed by the rule): -1.04R on average (first half -0.49R, second -1.70R; 165 better, 69 worse).
  - `floor_33pct_5r`: +340166 (+841 vs main; first half -871, second half +1712; 5 of 8 markets; max DD -29.6%; better than holding: no). Per armed trade (189, 125 closed by the rule): -1.19R on average (first half -0.26R, second -2.24R; 92 better, 33 worse).
  - `floor_33pct_3r`: +393294 (+53968 vs main; first half +4875, second half +49093; 5 of 8 markets; max DD -27.0%; better than holding: YES). Per armed trade (267, 209 closed by the rule): -1.26R on average (first half -0.29R, second -2.43R; 150 better, 59 worse).
  - `chandelier_4h_3atr_3r`: +125289 (-214037 vs main; first half -89319, second half -124718; 2 of 8 markets; max DD -14.2%; better than holding: no). Per armed trade (267, 260 closed by the rule): -1.94R on average (first half -1.20R, second -2.82R; 167 better, 93 worse).
  - `swing_4h_5r`: +177559 (-161767 vs main; first half -45457, second half -116309; 2 of 8 markets; max DD -20.6%; better than holding: no). Per armed trade (189, 184 closed by the rule): -2.53R on average (first half -1.49R, second -3.70R; 118 better, 66 worse).
  The PRIMARY rule, `floor_50pct_5r`, did NOT pass: it was $1442 behind the main book in the first half, although
  far ahead in the second, with a smaller drawdown. One rule passed, `floor_33pct_3r`. It is one of four floor
  variants, the pass was not predicted for it, and the four floors disagree market by market (gold: every floor
  ended near zero against the main book's +$26,565; WTI and Brent: every floor far ahead), so the pass is weak.
  The two 4-hour trails (chandelier, swing) were far behind holding.
- **(b) Equal size: NO rule helps per trade.** Every rule's mean R per armed trade is below the main book's in
  both halves. Each floor improved more trades than it hurt (`floor_50pct_5r`: 111 better, 39 worse), but the few
  it cut short were the very long holds (the most left on the table in one trade: 224R), which is where the main
  book's profit is. Per market the primary rule helped in 6 of 8 (not USDJPY, not gold).
- **Verdict.** A wide floor is NOT shown to be better than holding: the primary rule fails (a) narrowly and (b)
  clearly; the whole-book gains come from compounding in WTI, Brent and BTC and are offset by gold and USDJPY.
  By the registration, `floor_33pct_3r` may be proposed to the owner as a forward SHADOW book only; nothing else
  follows. The owner's separate decision of the same day (v5.2.8, a TIGHT trail on six main books) was made before
  these numbers and does not rest on them.

### H61 follow-up: `floor_33pct_3r` runs as a forward shadow book (21 Nov 2026)

- The owner, asked in the Mind 15 project: "Add shadow". The book is `f_floor_33_3r` (`engine15/floor_book.py`),
  this study's overlay one step at a time; `tests/test_floor_book.py` holds the two equal trade for trade on
  planted and random bars. The constants are the registered ones (arm at 3R, lock a third).
- One thing the study did not have: the book starts as a copy of the hold copy's book while that copy is in a
  trade. The floor is set from the closes since the entry; a fill can only happen from the first forward bar.
- Read it at 30 closed forward trades against the hold copy on the same trades, not before. Nothing follows from
  it for the main book without a new registration.

## Forward paper book from RL Phase 4: p5_rlq (go-live 2026-11-12 04:30 UTC; NOT passed) - block written after the fact, 21 Nov 2026

**This block was missing.** The book went live on 12 Nov 2026 with its rule fixed in `configs/rl/phase5.yaml`
(`forward.pass_rule`) and in `engine15/playbook5.py` (`REGISTERED`, `NOT_PASSED`), but nothing was written here. It
is added on 21 Nov 2026 by the RL audit, from those two files, and changes nothing.

**Status: NOT passed.** `p5_rlq` is the Phase 4 primary Q agent (pooled BTC+ETH, refit weekly), BTC and ETH, $10,000
each, decided at a 15m close, filled at the next open, 0.10% a side, perp funding, mean of seeds 0/1/2 through the
Phase 3 risk manager; a seed whose model fails its 'do no harm' check stays flat. History (seen): after fees it
trailed buy-and-hold (BTC Sharpe 0.48 against 0.64).

**Graded forward on:** no verdict before 30 closed forward trades per coin; then, after fees, against spot and perp
buy-and-hold since go-live. A forward pass would not make it a passed rule in history.

**State on 21 Nov 2026 (not a verdict):** 2 closed trades on BTC, 5 on ETH. Since the refit of 16 Nov all three
BTC seeds are on the fallback, so the BTC book has been flat.

## H62. The Setups book with the main book's stop where it is wider (registered 21 Nov 2026, 13:46 UTC, before any H62 code existed or any H62 number was computed)

**Prompted by:** the owner, in the site session, 21 Nov 2026 (relayed by that session, not yet confirmed in this
project): "Should follow the main book stop loss where is wider", then, from four options, "Setups trades, main-book
stop". That evening the member's ETH short, copied from the Setups book (`b_targets`), was stopped at the book's stop
1,680.76 (the bar's high was 1,681.99) while the main book's ETH stop, 1,693.44, held.

**Known before registering (the live journal, read today; these are facts, not results of this study):**
- The 1,693.44 stop belonged to a main-book trade opened 21 Nov 07:00 UTC, 11.5 hours after the Setups trade (20 Nov
  19:30 UTC, entry 1,596.99). At the Setups entry the main book held an older short with its stop at 2,146.83.
- The Setups book and the main book set their entry stop by the same formula (2 barriers from the entry). The main
  book's stop is "wider" only when its trade was entered elsewhere or earlier.
- The vault refuses a stop that moves away from price (`stop_not_tighter`), by design. It sizes a member's trade to lose
  2% of the wallet at the stop the book states at the join.

**What is tested.** `b_targets` unchanged in entries, Target 1, Target 2, the half at Target 1 and the stop to the entry
after Target 1. Only the stop before Target 1 changes. "The main book" is the main book under today's live rules
(think15-v5.2.8: the trailing stop and wait-for-a-signal on six markets, the target rules on USDJPY and the S&P 500),
run on the same bars; its position and the stop in force for a bar are those known at that bar's open. A main-book
stop counts only while the main book holds the SAME side and its stop is FURTHER from price than the Setups book's own.
- **A, `wide_entry` (PRIMARY: the owner's choice in the form the vault can follow).** At the Setups fill the book
  carries the main book's stop if it counts, else its own. Never moved afterwards except to the entry at Target 1.
- **B, `wide_follow`.** At every bar before Target 1 the stop is the main book's if it counts, else the book's own: it
  can move out mid-trade and back in. Not something the vault accepts today; replayed because it is the only form that
  would have changed the ETH trade above.
- **C, `wide_entry_tighten`.** As A at the fill; afterwards the stop moves IN to the book's own stop (or to a nearer
  main-book stop that still counts) when the main book leaves, turns or tightens. It never moves out.
- In all three the position is sized on the stop carried at the fill (`backtest.leverage`, as the vault sizes on the
  stated stop); the targets are planned from the book's OWN stop, as now.

**Data and method.** All eight markets, each from its first decided session to the last stored row at or before
2026-11-21 13:45 UTC, on the research server, reading the engine's evidence store and the cached weekly fits read-only.
The Setups book is run by a copy of `shadows.run` reduced to the targets rule. GATE (must pass or nothing is read):
with no wide stop that copy reproduces `shadows.run_challenger("b_targets")` on every market, every trade and the marked
equity at every bar. The main book is `backtest.run_book` with `live.asset_cfg` and the live step's own target and
trail wiring; the total-risk cap across books is left out (it needs the other books' live state), and that is said.
Halves split at 2023-06-08. The sealed holdout (2025-11-11 onward) is part of the second half: every rule here was
fixed before any number, and the holdout is reported separately as well.

**Read-outs, fixed now.** For the current rule, A, B and C, per market and pooled:
1. Net result, trades, share won, worst fall of the equity, worst single trade, in both halves and in the holdout.
2. How often the stop at the fill was the main book's, and how far the carried stop was from the entry against the
   book's own (median and largest ratio), since that ratio is how much smaller a member's position would be.
3. For B and C: stop moves per trade, out and in.
4. The forward period (from 2026-11-11) as its own slice, and the ETH trade of 20 Nov if the replay contains it.

**Pass bar for A (PRIMARY), fixed now.** A is "not worse than the current rule" only if, pooled over the eight markets,
its net result is at least the current rule's in BOTH halves, its worst fall is not deeper, AND it is at least the
current rule's on BTC and ETH taken together (the two markets the vault copies) in both halves. Anything else is "not
shown to be better". B and C are descriptive and can pass nothing. Whatever the result, the Setups book changes only on
the owner's word in this project, with a version and a new golden record; a history replay is not a forward result.

### H62 results (21 Nov 2026, 13:50 UTC runs, 14:52 UTC report, on the research server; `research/out/h62_setups_wide_stop/report.md` + `results.json`; per-group files stay on the server)

**Gate:** passed on 8 of 8 markets (the reduced copy reproduced `b_targets`, every trade and the marked equity).

**Verdict for A (PRIMARY): NOT SHOWN TO BE BETTER than the current rule.** Checks: pooled first half yes (+1,546 against
-4,982), pooled second half NO (-21,903 against -16,593), worst fall not deeper NO (-64.4% against -60.6%), BTC+ETH
first half yes (-1,873 against -2,983), BTC+ETH second half NO (-5,371 against -2,153).

| Book | Pooled net | 1st half | 2nd half | Holdout | Forward | Trades | Worst fall | BTC+ETH net | BTC+ETH 1st / 2nd | BTC+ETH sum of R (all / 1st / 2nd) |
|---|---|---|---|---|---|---|---|---|---|---|
| current rule | -21,575 | -4,982 | -16,593 | -1,273 | +4,134 | 5,964 | -60.6% | -5,136 | -2,983 / -2,153 | -8.6 / +46.1 / -54.7 |
| A wide_entry | -20,357 | +1,546 | -21,903 | -2,103 | +3,612 | 5,699 | -64.4% | -7,244 | -1,873 / -5,371 | -12.6 / +36.9 / -49.5 |
| B wide_follow | -13,272 | -1,718 | -11,555 | +1,846 | +4,622 | 5,683 | -61.7% | +375 | -7,531 / +7,906 | -6.9 / +23.6 / -30.4 |
| C wide_entry_tighten | -18,203 | +2,617 | -20,820 | -459 | +3,885 | 5,733 | -64.3% | -4,778 | -288 / -4,490 | +0.8 / +46.6 / -45.8 |

- **How often it applies.** The stop carried at the fill was the main book's on 8.5% of trades pooled and 13.6% on BTC
  and ETH (largest ratio to the book's own stop: 47.5x pooled, 3.9x on BTC and ETH). B moved a stop out 540 times and
  back in 458 times (306 / 270 on BTC and ETH); C moved in 254 times (158).
- **The member's view (sum of R, each trade over its own risk at the carried stop), BTC and ETH:** current -8.6, A -12.6,
  B -6.9, C +0.8 over about 2,000 trades. No variant separates from the current rule; B is better in one half and worse
  in the other; B's worst trade is -2.3R against -1.4R (a stop that moved out after the position was sized).
- **Per market** A is better on SPX, BTC, gold and WTI and worse on ETH (+1,611 against +4,059), silver and Brent;
  USDJPY is unchanged (its main book runs the same target rule from the same entries).
- **The ETH trade of 20 Nov in the replay** is not the live trade: the replay enters at 19:00 UTC at 1,616.66 (live:
  19:30 at 1,596.99) and its main book, run under today's rules over all history, carried no wider stop at that fill
  (1.0x in A, B and C), where the live main book, which got its trailing stop only this week, held a short with its
  stop at 2,146.83. All four books are stopped at 13:30 UTC on 21 Nov. The replay cannot speak to that one trade.
- **Not in the replay:** the main book's total-risk cap across books. A history replay is not a forward result.

**Reading.** The owner's rule in the form the vault can follow (A) fails the registered bar: worse in the second half
pooled and on BTC and ETH, with a deeper worst fall. Nothing here supports changing the Setups book's stop. No engine
code was changed by this study. The Setups book changes only on the owner's word in this project.

**Owner's decision (this project, 22 Nov 2026 local, after the results):** "Keep as is". The Setups book's stop is
unchanged. H62 is closed.

## H63. One member wallet on the Setups book's BTC and ETH trades under three sizings (registered 22 Nov 2026, before any H63 code existed or any H63 number was computed)

**Prompted by:** the site session, 22 Nov 2026, relaying an owner decision made there ("Study first, then paper desk";
not yet confirmed in this project): the owner wants VIP accounts to be able to run much larger than today's 2% rule,
and accepted evidence first. This is a description, not a hypothesis with a pass bar: nothing can "pass". No engine
code is changed. The "paper desk" (forward paper wallets) is a separate engine change that needs the owner's word here.

**Known before registering:** H62's replay of the current rule (BTC and ETH, each its own $10,000 paper book at full
size): net -5,136, worst fall -77.5%; BTC -9,196 (worst fall -98.0%), ETH +4,059 (-76.2%); forward slice +1,829.

**The trades.** The CURRENT Setups rule (`b_targets`) on BTCUSDT and ETHUSDT, from the replay H62 used (same store,
same cached fits, same end: the last stored session at or before 2026-11-21 13:45 UTC; first decided session 2020-02-05).
The book's entries, stops, targets and exits do not depend on its size, so each trade is taken as prices and bars: the
entry at an open, the stop it starts with, half closed at Target 1 if it was reached, the rest at its exit. GATE (must
pass or nothing is read): walked with the paper book's own sizing, one coin at a time, the walk reproduces the replay's
marked equity at every bar on both coins.

**The wallet.** ONE wallet, 10,000 at the start, both coins. Wallet = the realised balance; equity = the wallet plus the
open result at each 15-minute close. In a bar: funding first, then fills at the open (closes before entries, BTC before
ETH), then stops and targets inside the bar. A setup already open when a wallet starts is not joined.
- **Fees:** as the paper book counts them, 0.10% of the notional per side (`cost_side`; a member's real futures fee is lower).
- **Funding:** the stored Binance funding series (`data/<coin>_funding.csv`), paid or received on the open notional at
  each funding time at that bar's open price. The paper book counts no funding; the wallet does. The final wallet
  without funding is given beside it.
- **Daily loss brake** (my model of the vault's brake as the site session described it, not the vault's code): the day
  is the UTC day. Budget = brake% of the wallet at the day's start, less what the wallet has lost since the day's start
  (a gain adds nothing), less the other coin's open risk (its loss at its stop now; zero after Target 1). A new trade's
  loss at its stop may not exceed the budget: it is trimmed to fit, and not joined if the budget is zero or less. The
  brake closes nothing.
- **S1 "2% rule":** sized to lose 2% of the wallet at the stop; the notional capped at the wallet less the other coin's
  open notional (1x); brake 5%.
- **S2 "100% per coin":** notional = 1.0 x the wallet at the entry; brake 15%.
- **S3 "3x book":** notional = 1.5 x the wallet at the entry; brake 15%.
- **Wipe-out (all three):** in any bar, with each open position at its worst price of that bar (low for a long, high for
  a short; both coins at once, which is the cautious reading), if the equity is at or below 0.5% of the open notional
  (an assumed maintenance margin; the exchange's tiers at these sizes are near it), the wallet is wiped out and the run
  ends there. Positions closed inside that bar count at their exit price. Reported also with closes only, if it differs.

**Not modelled, and said:** the member's fill against the book's (slippage, the vault's join window), a trade the vault
would refuse, exchange limits, the vault's own rounding. So this is the book's trades at three sizes, not a simulation
of the vault.

**Read-outs, fixed now, for S1, S2, S3:**
- (a) The final wallet from 10,000 over the whole replay, the worst fall of the equity, the lowest equity, trades
  joined / trimmed / not joined, fees and funding paid, the final wallet without funding, and whether and when it was
  wiped out.
- (b) From EVERY month-start (the first bar of each calendar month, UTC) as a fresh 10,000 wallet, walked for 365 days:
  how often the equity reached +100% (20,000) at a close before -50% (5,000), how often -50% or a wipe-out came first,
  how often neither within 365 days, and the median days to either. Month-starts with less than 365 days of data and no
  line reached are counted apart as unfinished.
- (c) The worst single UTC day (equity at the day's last close against the day before) and the longest run of losing
  joined trades, from the run in (a).
- (d) The forward record alone: the LIVE Setups book's closed BTC and ETH trades since it started (11 Nov 2026, from
  `out/live/shadow_trades_b_targets_*.csv`) plus its open trades, one 10,000 wallet, marked at the last stored bar.
  About eleven days and a dozen trades: too short to judge, and the report says so.

A history replay is a warm-up, not a forward result; the first half and the second half of (b) are shown apart
(month-starts before and from 2023-06-08).

### H63 results (22 Nov 2026, 06:02-06:03 UTC on the research server; `research/out/h63_member_wallet/report.md` + `results.json`)

**Gate:** passed on both coins (the walk with the paper book's sizing reproduced the replay's marked equity at every one
of 238,079 bars; largest relative gap 6e-15). Replay 2020-02-05 to 2026-11-21 13:45 UTC, 2,076 trades. The report's
first rendering failed on a formatting slip in a table header; `results.json` was already written and the report was
rendered from it unchanged (`--report`, computes nothing).

**(a), (c) One 10,000 wallet over the whole replay:**

| Sizing | Final | Worst fall | Lowest | Wiped out | Joined / trimmed / capped / not joined | Fees | Funding paid | Final without funding | Worst day | Longest losing run |
|---|---|---|---|---|---|---|---|---|---|---|
| S1: 2% rule | 3,208 | -86.7% | 2,254 | no | 1,907 / 345 / 994 / 169 | 14,338 | 3,408 | 4,327 | -6.6% | 13 |
| S2: 100% per coin | 847 | -98.6% | 426 | no | 2,040 / 174 / 0 / 36 | 28,220 | 9,758 | 1,677 | -19.6% | 13 |
| S3: 3x book | 100 | -99.9% | 40 | no | 1,965 / 480 / 0 / 111 | 31,295 | 11,140 | 232 | -21.7% | 13 |

No sizing met the wipe-out rule (not with closes only either): the stops bound each loss. S3 still ends at 1% of its
start. All three lows are on 2026-08-19.

**(b) A fresh 10,000 wallet from each of 81 month-starts, 365 days each:**

| Sizing | +100% first | -50% first | Neither | Unfinished | Median days to +100% | Median days to -50% |
|---|---|---|---|---|---|---|
| S1: 2% rule | 0 | 4 | 65 (median end 7,984) | 12 | n/a | 313 |
| S2: 100% per coin | 16 | 37 | 16 (median end 6,930) | 12 | 123 | 222 |
| S3: 3x book | 24 | 54 | 1 | 2 | 83 | 166 |

By half (month-starts before / from 2023-06-08), +100% first against -50% first: S1 0-0 / 0-4; S2 15-17 / 1-20;
S3 16-24 / 8-30. No wipe-out in any start.

**(d) The forward record alone (the live book, 11 Nov 06:45 to 22 Nov 05:45 UTC, 13 trades, 2 still open): TOO SHORT TO
JUDGE.** Equity now from 10,000: S1 11,933 (worst fall -4.7%), S2 14,131 (-10.7%), S3 15,235 (-15.1%).

**Where the model differs from the vault (from the site session, which read the vault's code; stated, not changed):**
(1) the vault's daily room counts the account value as last read, open results included, where this model counts the
realised wallet; (2) at a 3x leverage setting two 1.5x positions need the whole wallet as margin, so the vault trims the
LATER order to the free margin: S3 here is an upper bound, a few percent high on the second coin; (3) the member's own
caps bind in none of the three.

**Reading.** On the replay every sizing loses, and a larger size loses faster: from a month-start, the 3x book halved
before it doubled 54 times against 24, the 100% book 37 against 16; the 2% rule never doubled within a year and halved 4
times. The fee is the paper book's 0.10% per side, about twice a member's real futures fee, and it is a large part of
the loss (S1 paid 14,338 in fees on a 10,000 wallet); no other fee was run. The forward eleven days are strongly
positive at every size and prove nothing yet. No engine code was changed by this study.

## H64. What the one-bar delay costs a member at the entry (registered 22 Nov 2026, before any H64 code existed or any H64 number was computed)

**Prompted by:** the site session, relaying an owner decision made there ("Cut the 15-minute delay": send a new setup to
the vault when its entry price is set, not one bar later; not yet confirmed in this project). One observation is known:
on 21 Nov the book's entries were 60,346.59 and 1,692.17 and the member's fills about 60,311 and 1,687.3, 17 minutes
later (0.06% and 0.29% worse for a short). This measures the same thing over the replay before anything is built.

**Measure.** For every `b_targets` trade on BTC and ETH in H63's replay: the book's entry is the open of bar i; the vault
first sees the position after that bar closes, so the member's price is taken as the open of bar i+1. Cost = side x
(open[i+1] - open[i]) / open[i], in percent of price: positive = the member's entry is worse than the book's. In R: the
cost divided by the book's stop distance in percent (the member keeps the book's stop and targets, so a worse entry
takes the same amount off every outcome).
**Read-outs, fixed now:** trades, mean, median, share worse, share better, the 5th and 95th percentile, the sum of the
cost in R; for all, per coin, per half (2023-06-08), per entry word (ENTER, FORCED, FLIP); the share of trades that were
already closed inside their entry bar (the member is told of a trade that is over) and that reached Target 1 inside it;
and the same cost on the live record's trades (too few to judge). Descriptive: nothing passes or fails. A positive mean
says the delay has cost members on average; a mean near zero says it adds noise, not a cost.

### H64 results (22 Nov 2026, about 06:20 UTC on the research server; `research/out/h64_entry_delay/results.json`)

Cost of entering at the next bar's open instead of the book's entry, in percent of price (positive = worse for the member):

| Slice | Trades | Mean | Median | Worse / better | 5th .. 95th percentile | Sum in R | t |
|---|---|---|---|---|---|---|---|
| All | 2,075 | +0.001% | -0.006% | 49.1% / 50.7% | -0.81% .. +0.87% | +0.7 | 0.06 |
| BTC | 1,062 | +0.019% | -0.003% | 49.3% / 50.5% | -0.64% .. +0.75% | +0.1 | 0.86 |
| ETH | 1,013 | -0.018% | -0.011% | 48.9% / 51.0% | -1.03% .. +0.96% | +0.6 | -0.63 |
| First half | 992 | +0.025% | -0.014% | 49.2% / 50.6% | -1.03% .. +1.10% | +10.8 | 0.74 |
| Second half | 1,083 | -0.021% | -0.004% | 49.0% / 50.9% | -0.65% .. +0.63% | -10.1 | -1.32 |
| ENTER | 745 | +0.005% | -0.029% | 48.3% / 51.7% | -1.22% .. +1.09% | -0.1 | 0.11 |
| FORCED | 1,212 | +0.003% | +0.004% | 50.3% / 49.6% | -0.62% .. +0.71% | +1.3 | 0.22 |
| FLIP | 118 | -0.044% | -0.061% | 41.5% / 56.8% | -1.03% .. +1.02% | -0.5 | -0.77 |
| Live record | 13 | +0.015% | +0.059% | 69% / 31% | -0.90% .. +0.45% | -0.0 | 0.11 |

0.5% of trades were already closed inside their entry bar (11 of 2,075) and 0.4% reached Target 1 inside it.

**Reading.** Over 2,075 entries the one-bar delay has cost a member nothing on average (+0.001% of price, under one R
in total); it is as often a better price as a worse one. What it adds is noise: in nine entries of ten the member's
price is within about 0.8% of the book's, either way. So sending the setup a bar earlier would make the member's entry
match the book's more closely, and would not have improved results. No engine code was changed by this measurement.

## H65. Post-mortem of the Setups book, from its first replay trade to now: where its results come from (registered 22 Nov 2026, before any H65 code existed or any H65 number was computed)

**Prompted by:** the owner, in this project, 22 Nov 2026: "Audit from beginning to now and see any post mortem. How can
we play the rules better". A description with fixed slices, not a rule change: nothing is adopted from it.

**Known before registering:** the live record (11 Nov to 20 Nov 2026 entries, 29 closed trades on eight markets: +27.25R,
22 wins; every trade short except USDJPY's five longs, which are the only losing market; 20 of 29 entered by the forced
rule). H62/H63: on the replay the current rule loses on BTC and ETH (sum of R -8.6 over 2,075 trades). H64: 1,212 of
those 2,075 entries are FORCED, 745 ENTER, 118 FLIP.

**Data.** `b_targets` as the server runs it today (the rule before v5.2.9; the early entry moves entry prices by a hair
and is not part of this), all eight markets, each from its first decided session to the last stored session at or before
2026-11-21 13:45 UTC, the evidence store and cached fits read only. Every closed trade, its result in R as the book
books it (`r_mult`: net of fees, over the risk at the entry stop). Halves split at 2023-06-08 by entry time.

**Slices, fixed now.** Readings are taken at the bar that decided the entry.
1. Entry word: ENTER, FORCED, FLIP.
2. Side: long, short.
3. Higher-timeframe bias: with the trade, against it, none.
4. Tide: with the trade, against it.
5. The market's own 30-day move (close against the close 30 days earlier): with the trade, against it.
6. The lead of the trade's side in the odds (P(side) - P(other side)): thirds, cut on the first half only.
7. Stop distance in percent of price: thirds per market, cut on that market's first half only.
8. Target 1's distance in R: thirds, cut on the first half only.
9. What came before on that market: the previous trade ended at its stop / at a target (Target 2, or the entry after
   Target 1) / otherwise; and whether this trade is on the same side as the previous one.
10. Facts about exits (not a slice to trade on): the exit words; of the trades stopped at the entry stop, the share that
    had been at least 0.5R and at least 1R in open profit first (best price of the bars before the exit bar); of the
    trades that took Target 1, the share that went on to Target 2; median bars held.

**Read-outs.** For every cell: trades, share won, mean R, sum of R; for all eight markets, for BTC and ETH, for the
other six; each in the first half and the second half. The live record's 29 trades are shown beside slices 1, 2 and 10.

**How a slice is called, fixed now.** A cell is "consistent" only if its mean R has the same sign in the first half and
the second half AND on BTC and ETH and on the other six markets, with at least 100 trades in each of those four parts.
Anything else is "not consistent". A consistent cell is a candidate for a registered forward shadow book and nothing
more: ten slices are looked at here, so some will look good by chance, and a history replay is a warm-up, not a
forward result. No engine code is changed by this.

### H65 results (22 Nov 2026, about 10:30 UTC on the research server; `research/out/h65_setups_postmortem/report.md` + `results.json`)

5,964 closed trades on eight markets, 2020-02-05 to 2026-11-20. Overall the book is flat in R: mean +0.004R a trade
(sum +21.7R; first half +28.7, second half -7.1); BTC and ETH -8.6R (BTC -66.9, ETH +58.3), the other six +30.3R.
Cells below: trades, mean R, sum of R.

**Consistent cells (same sign in both halves and on BTC+ETH and on the other six, 100+ trades in each part):**
- **Side.** Long 3,331, +0.055, +183.8R (positive); short 2,633, -0.062, -162.2R (negative). Most of these markets rose
  over the period, so part of this is the markets' own drift and not something the rule found.
- **The market's own 30-day move.** With it 4,493, +0.031, +139.3R (positive); against it 1,470, -0.079, -116.5R
  (negative). On BTC and ETH: with +89.6R over 1,508, against -98.2R over 567 (-0.173R a trade).
- **Higher-timeframe bias with the trade:** 1,451, +0.036, +52.6R (positive). With no bias (4,499 trades): -26.1R, not consistent.
- **Tide with the trade:** 5,388, +0.011, +60.0R (positive); against it 461, -0.051 (not consistent).
- **Stop distance.** The tightest third per market 2,623, -0.031, -81.9R (negative); the middle third +80.8R and the
  widest third +22.7R (both positive).
- **After a stop, the next trade on the other side:** 1,141, -0.030, -34.3R (negative).
- Target 1 distance, middle third: -0.014 (negative, small).

**Not consistent:** the entry word (ENTER -5.6R, FORCED -1.5R over 4,461 trades: the forced entry is neither the
problem nor a help; FLIP +28.9R but too few in a part), the lead in the odds (the top third +69.7R in all, but -3.7R in
the second half), Target 1 distance low and high, what the previous trade ended at.

**Exits (facts).** STOP 3,207 trades, -3,394.5R; T1+T2 1,572, +2,925.2R; T1 then the entry 894, +548.7R; FLIP 270,
-85.3R. Of the trades stopped at the entry stop, 43% had been at least 0.5R in open profit first and 16% at least 1R.
42% of trades took Target 1; of those 63% went on to Target 2 and 36% came back to the entry.

**The live record beside it (29 closed trades, 11 to 20 Nov 2026): +27.25R, 22 wins.** 24 of the 29 are shorts in
falling markets and the 5 USDJPY longs are with a rising market: every live trade so far is WITH its market's 30-day
move, the cell that is positive on history. The live record has not yet met the other cell.

**Reading.** On history the Setups rule makes its money with the market's own direction and gives it back against it;
the entries' own signal (the lead in the odds) does not hold up across halves. The one cell that is large, consistent
and simple is the 30-day move. Ten slices were looked at, so this is a candidate for a registered test and a forward
shadow book, not a finding to trade on. No engine code was changed.

## H66. BTC and ETH: how a Setups short has turned long, and what the book did in a sudden rally (registered 22 Nov 2026, before any H66 code existed or any H66 number was computed)

**Prompted by:** the owner, in this project, 22 Nov 2026: "under what circumstance for btc and eth will turn long. Can
simulate the possible. Also how can we manage if sudden rally long". The Setups book is short both coins. A description
of the replay under the current rule (the server's `b_targets`, to 2026-11-21 13:45 UTC), BTC and ETH; nothing passes.

**Known before registering:** the rule (`policy.decide`): a short flips to long when the up side leads by 10 points, or
when the higher-timeframe bias is up and the short's own lead is under 5 points; from flat a long needs a 5-point lead
(10 when risk is high, 15 against the bias), and after 4 flat sessions the forced entry goes with the bias, else the
tide, else the leading side. H65: after a stop the next trade on the other side has been slightly negative.

**A. How a short has turned long.** Every short followed by a long as the next trade, by path: (1) a flip; (2) the
short ended at its stop; (3) the short ended at a target or at the entry after Target 1. For each path: how many, the
median hours from the short's exit to the long's entry, the long's entry word, share won and mean R of that long. And,
of all shorts that ended at their stop, the share whose next trade was a short again, with that next short's mean R.
**B. Sudden rallies while short.** An episode starts at the first bar where the book holds a short and the close 96
bars (24 hours) later is at least 5% higher; the next episode is looked for after those 96 bars. Also at 8%. For each
episode: the market's move; the book's own marked equity change over the same 96 bars (paper, 1x) and the sum of R of
the trades closed inside them; how many stop-outs; how many NEW shorts were opened inside the episode; what the book
holds at the end (long, short, flat); hours to the first long (within the 96 bars, else "none"). Read-outs: episodes,
medians, the worst book result, the share that ended long; both halves. **C. The mirror** (sudden drops of 5% and 8%
while long) by the same rules, as a yardstick.

### H66 results (22 Nov 2026, about 10:45 UTC on the research server; `research/out/h66_turns_and_rallies/results.json`)

**A. How a short has turned long (next trade a long), BTC / ETH, 2020-02 to 2026-11:**

| Path | BTC: times, median hours, the long's mean R | ETH: times, median hours, the long's mean R |
|---|---|---|
| A flip (up side leads by 10 points, or the bias turns up) | 34, 0, +0.26 | 28, 0, +0.40 |
| The short was stopped, then a long | 137, 1.25, -0.08 (90 forced, 47 on a signal) | 112, 1.25, +0.09 (79 forced, 33 on a signal) |
| The short ended at a target, then a long | 22, 1.25, -0.22 | 25, 1.25, +0.64 |

About 28 turns a year on BTC and 24 on ETH; seven in ten came after a stop-out. After a stopped short the next trade was
a short AGAIN 51% of the time on BTC (145 of 282, mean -0.05R, 39% won) and 56% on ETH (140 of 252, -0.05R, 38% won).

**B. Sudden rallies while short (the close 24 hours later at least 5% higher), both coins: 505 episodes** (330 in the
first half, 175 in the second). Median rally +5.4%. The paper book (1x) lost in 93% of them: median -4.5%, mean -4.1%,
worst -41% (ETH, 12 Mar 2020), best +7.4%. Median stop-outs inside the 24 hours: 0 (the stop is usually further than
the move; the loss is the open short marked against the rally); at most 3. In 24% of the episodes the book opened a NEW
short inside the rally. It turned long within the 24 hours in 26% (median 15.5 hours when it did); at the end it was
still short in 349 of 505, long in 125, flat in 31. Second half alone: median -4.0%, a new short in 30%, long within 24
hours in 24%. **At 8%: 198 episodes**, median book -6.3%, a new short in 35%, long within 24 hours in 28%.

**C. The mirror, sudden drops while long:** 351 episodes at 5% (median book -4.1%, lost in 87%, turned short within 24
hours in 37%); 116 at 8% (median -4.3%, turned short within 24 hours in 61%). The book has turned short in a drop more
readily than it has turned long in a rally.

**Reading.** The book does not chase a rally: in three of four sudden rallies it did not turn long within a day, and in
one of four it sold again into the move. What bounds the loss is the stop, not a turn. Nothing here was changed.

## H67. The Setups rule with a 30-day trend filter (registered 22 Nov 2026, before any H67 number was computed)

**Prompted by:** H65 (trades against their market's own 30-day move lost 117R over 1,470 trades, with it +139R over
4,493, consistent across halves and market groups) and the owner, in this project, 22 Nov 2026, asked "Test the 30-day
trend filter on history and run it as a forward paper shadow book?": "Test it".

**What must be said first.** The filter was FOUND on this same history, all of it, the holdout included. So the replay
below cannot validate it: it only checks that the pattern survives when it is made a rule (a filtered book trades a
different sequence: it is flat where the old book was in a trade, and its later entries differ). The test is the
forward shadow book.

**The rule, `b_trend30`.** `b_targets` as it runs from think15-v5.2.9 (the early entry on BTC and ETH included), with
one change. At the close that decides, the market's 30-day move is the close against the close of the first bar at or
after 30 days earlier (unknown when there is no such bar: then nothing is filtered).
- A new entry from flat (ENTER or FORCED) on the side AGAINST the 30-day move is not taken: the book stays flat and its
  idle count goes on.
- A flip INTO the side against the 30-day move closes the position at the next open and opens nothing (flat).
- A position already open is never closed because the 30-day move changes; its stop, targets and exits are untouched.
So this book can sit flat for long: it has no 4-session mandate when the forced side is against the move. It is a
shadow book; the Setups book and the vault are not touched.

**Replay.** All eight markets, each from its first decided session to the last stored session at or before 2026-11-21
13:45 UTC, the engine's own `shadows.run` for both books (no copy), in a scratch copy of the code on the research
server, the evidence store and cached fits read only. Halves split at 2023-06-08; the holdout (2025-11-11 onward) and
the forward slice (2026-11-11 onward) shown apart. Descriptive beside it: the same rule with 20 and with 45 days.

**Read-outs, fixed now.** For the current rule and the filter, per market and pooled, BTC and ETH apart: trades, share
won, mean R and sum of R (the book's `r_mult`), paper net, worst fall of the marked equity, share of bars flat; first
half, second half, holdout, forward slice.

**Bar for the replay, fixed now.** "The pattern survives as a rule" only if ALL hold: (1) pooled over eight markets the
filter's sum of R is above the current rule's in BOTH halves; (2) the same on BTC and ETH together in BOTH halves;
(3) its pooled mean R per trade is above zero in BOTH halves; (4) its pooled worst fall (the eight books' equity summed)
is not deeper than the current rule's. Anything else is "does not survive as a rule". The 20-day and 45-day versions
are descriptive (do they agree in sign with the 30-day one).

**Forward.** `b_trend30` is added as a shadow book whatever the replay says (the owner asked for it), starting flat at
its first live bar. First read at 30 closed trades against `b_targets` over the same days; nothing reaches the Setups
book or the vault without the owner's word in this project.

### H67 results (22 Nov 2026, 10:50-10:51 UTC on the research server; `research/out/h67_trend_filter/report.md` + `results.json`)

**Verdict by the registered bar: the pattern SURVIVES as a rule** (all four checks hold). (1) Pooled sum of R above the
current rule's in both halves: first half +86.3R vs +29.6R, second half +41.0R vs -7.1R. (2) BTC and ETH together, both
halves: +106.1R vs +44.7R, +29.2R vs -52.5R. (3) Pooled mean R above zero in both halves: +0.032, +0.015. (4) Pooled worst
fall (the eight books' marked equity summed) -41.0% vs -61.6%: not deeper.

Each cell: trades, share won, mean R, sum of R, paper net ($), share of bars flat (pooled: the markets' mean).

| Pooled, 8 markets | All | First half | Second half | Holdout (2025-11-11 on) | Forward (2026-11-11 on) | Worst fall |
|---|---|---|---|---|---|---|
| current rule | 5963, 43%, +0.004, +22.5, -21233, 2% | 2953, +0.010, +29.6, -4701 | 3010, -0.002, -7.1, -16532 | 793, +0.027, +21.1, -1117 | 21, +0.874, +18.3, +4175 | -61.6% |
| 30-day filter | 5521, 43%, +0.023, +127.3, +278, 8% | 2721, +0.032, +86.3, +10861 | 2800, +0.015, +41.0, -10583 | 750, +0.060, +45.0, +11105 | 21, +0.765, +16.1, +7193 | -41.0% |
| BTC + ETH current | 2074, 44%, -0.004, -7.7, -4794, 1% | 991, +0.045, +44.7, -2702 | 1083, -0.048, -52.5, -2092 | 305, +0.040, +12.3, +6214 | 9, +0.599, +5.4, +1869 | -78.5% |
| BTC + ETH filter | 1815, 46%, +0.075, +135.3, +24847, 8% | 863, +0.123, +106.1, +22620 | 952, +0.031, +29.2, +2227 | 284, +0.051, +14.5, +14262 | 9, +0.599, +5.4, +5429 | -61.1% |
| Other six current | 3889, 42%, +0.008, +30.3, -16439, 2% | 1962, -0.008, -15.1, -1999 | 1927, +0.024, +45.4, -14440 | 488, +0.018, +8.8, -7331 | 12, +1.080, +13.0, +2305 | -65.9% |
| Other six filter | 3706, 41%, -0.002, -8.0, -24569, 8% | 1858, -0.011, -19.8, -11759 | 1848, +0.006, +11.8, -12809 | 466, +0.065, +30.5, -3156 | 12, +0.889, +10.7, +1764 | -57.0% |

Descriptive, sum of R (all / first half / second half): 20-day filter +55.1 / +66.2 / -11.1 (worst fall -67.2%, deeper
than the current rule); 45-day filter +144.9 / +22.3 / +122.7 (worst fall -46.1%). Both are above the current rule in
total (+22.5R), but neither in both halves: the 20-day one is below it in the second half (-11.1R vs -7.1R) and the
45-day one in the first half (+22.3R vs +29.6R). Neither would have cleared the bar.
Per market (30-day): BTC -66.9R -> +30.4R, ETH +59.2R -> +104.8R, WTI -5.7 -> +11.7; gold, silver, USDJPY, SPX and
Brent are a little worse (each within about 21R). The current rule's 5,963 trades and +22.5R match H65's record.

**Deviations:** none from the registered rule, replay or read-outs. Two choices made with the code, before the run: the
move at bar k uses the first bar whose open time is at or after open(k) minus 30 days (the registration says "30 days
earlier"), and a flip into the wrong side leaves the idle count at 0 (as any flip does today). The replay also checks
that the engine's own challenger `b_trend30` (via `run_challenger`) gives the very book the script ran (it did, on all
eight markets). Worst fall is also shown for BTC + ETH and the other six (the registration asked it pooled only).

**Reading.** On history the filter turns the Setups book's flat R into a positive one, and nearly all of the gain is on
BTC and ETH; on the other six markets it is roughly neutral (slightly worse in total, better in the holdout). The book
is flat about 8% of bars instead of 2%. The three lengths agree in sign on the total, but each of the other two loses
one half to the current rule (and 20 days has the deeper fall), so the result depends on the length chosen. This filter was FOUND on this same history
(H65), so the replay cannot validate it: it shows only that the pattern holds up when made a rule. The test is the
forward shadow book `b_trend30`, first read at 30 closed trades against `b_targets` over the same days. Nothing reaches
the Setups book or the vault without the owner's word.

## H68. The Setups rule that waits for a real signal after a stop-out (registered 22 Nov 2026, before any H68 code was run on history or any H68 number was computed)

**Prompted by:** H65 slice 9 and H66 (after a trade stopped at its entry stop, the next trade lost a little whichever way
it went: on BTC and ETH the next same-side trade after a stopped short averaged -0.05R, and "after a stop, the other
side" was negative in both halves and both market groups; on 21 Nov 2026 the live ETH short was stopped at 13:15 UTC and
the forced rule sold again an hour later) and the owner, in this project, 22 Nov 2026: "After a stop-out, wait for a
real signal instead of a forced re-entry."

**What must be said first.** Like H67, the idea was FOUND on this same history. The replay below cannot validate it; it
only checks that the pattern survives when it is made a rule. The test is the forward shadow book.

**The rule, `b_wait_stop`.** `b_targets` as it runs from think15-v5.2.9 (rule `{"targets": True, "early": True}`, the
early entry on BTC and ETH included) plus one key, `"wait_after_stop": True`. After a trade ends at its ENTRY STOP (the
exit word is exactly "STOP": a losing stop-out; not "STOP_BE" after Target 1, not a target, not a flip, not a step
aside), the forced entry is switched off: the book stays flat until one side clears the normal entry bar by itself
(`policy.decide` returns ENTER), however many sessions that takes; the idle count goes on. Once a trade is entered the
switch is cleared. After any other kind of exit the 4-session forced entry works as today. This mirrors the main
book's wait after a trailing-stop exit (v5.2.8, `wait_sig` in `engine15/backtest.py`). The switch lives in the book's
saved state under a key written only for a book whose rule asks for it, so every other book's state is unchanged, and
a bar-by-bar run equals the whole run. It is a shadow book; the Setups book and the vault are not touched.

**Replay.** As H67: all eight markets, each from its first decided session to the last stored session at or before
2026-11-21 13:45 UTC, the engine's own `shadows.run` for both books, in a scratch copy of the code on the research
server, the evidence store and cached fits read only. Halves split at 2023-06-08; the holdout (2025-11-11 onward) and
the forward slice (2026-11-11 onward) shown apart. Descriptive only (no bar, not a live book): one book with both the
H67 30-day trend filter and this wait.

**Read-outs, fixed now.** As H67 (for the current rule and the new rule, per market and pooled, BTC and ETH apart:
trades, share won, mean R, sum of R, paper net, worst fall of the marked equity, share of bars flat; first half, second
half, holdout, forward slice), plus: how many forced entries the new rule withheld (stop-outs after which at least one
forced entry was withheld, and sessions withheld); the median and the longest wait from a stop-out to the next entry;
and what the withheld forced entries would have made, read in the current rule's own record: the trades of the current
rule whose entry word is FORCED and whose previous trade on that market ended at "STOP" (count, mean R, sum of R).

**Bar for the replay, fixed now.** "Survives as a rule" only if ALL hold: (1) pooled over eight markets the new rule's
sum of R is above the current rule's in BOTH halves; (2) the same on BTC and ETH together in BOTH halves; (3) its pooled
mean R per trade is above zero in BOTH halves; (4) its pooled worst fall (the eight books' equity summed) is not deeper
than the current rule's. Anything else is "does not survive as a rule".

**Forward.** `b_wait_stop` is added as a shadow book whatever the replay says (the owner asked for it), starting flat at
its first live bar. First read at 30 closed trades against `b_targets` over the same days; nothing reaches the Setups
book or the vault without the owner's word in this project.

### H68 results (22 Nov 2026, 10:56-10:57 UTC on the research server; `research/out/h68_wait_after_stop/report.md` + `results.json`)

**Verdict by the registered bar: the pattern SURVIVES as a rule** (all four checks hold), with a large caveat below.
(1) Pooled sum of R above the current rule's in both halves: first half +113.3R vs +29.6R, second half +30.5R vs -7.1R.
(2) BTC and ETH together, both halves: +47.3R vs +44.7R (a narrow margin), +17.3R vs -52.5R. (3) Pooled mean R above
zero in both halves: +0.054, +0.024. (4) Pooled worst fall -32.4% vs -61.6%: not deeper.

Each cell: trades, share won, mean R, sum of R, paper net ($), share of bars flat (pooled: the markets' mean).

| Book | All | First half | Second half | Holdout (2025-11-11 on) | Forward (2026-11-11 on) | Worst fall |
|---|---|---|---|---|---|---|
| Pooled current | 5963, 43%, +0.004, +22.5, -21233, 2% | 2953, +0.010, +29.6, -4701 | 3010, -0.002, -7.1, -16532 | 793, +0.027, +21.1, -1117 | 21, +0.874, +18.3, +4175 | -61.6% |
| Pooled wait | 3389, 45%, +0.042, +143.9, +38537, 56% | 2090, +0.054, +113.3, +42343 | 1299, +0.024, +30.5, -3806 | 291, +0.105, +30.7, +8895 | 13, +0.516, +6.7, +1653 | -32.4% |
| BTC + ETH current | 2074, 44%, -0.004, -7.7, -4794, 1% | 991, +0.045, +44.7, -2702 | 1083, -0.048, -52.5, -2092 | 305, +0.040, +12.3, +6214 | 9, +0.599, +5.4, +1869 | -78.5% |
| BTC + ETH wait | 1761, 46%, +0.037, +64.5, +10032, 21% | 908, +0.052, +47.3, +8687 | 853, +0.020, +17.3, +1346 | 208, +0.064, +13.3, +9986 | 11, +0.658, +7.2, +1650 | -70.1% |
| Other six current | 3889, 42%, +0.008, +30.3, -16439, 2% | 1962, -0.008, -15.1, -1999 | 1927, +0.024, +45.4, -14440 | 488, +0.018, +8.8, -7331 | 12, +1.080, +13.0, +2305 | -65.9% |
| Other six wait | 1628, 44%, +0.049, +79.3, +28505, 67% | 1182, +0.056, +66.1, +33656 | 446, +0.030, +13.3, -5151 | 83, +0.210, +17.4, -1091 | 2, -0.264, -0.5, +2 | -24.7% |

**Withheld forced entries and waits.** Stop-outs after which at least one forced entry was withheld: 1,259 (BTC + ETH
651, the other six 608). Wait from a stop-out to the next entry (completed waits): BTC + ETH median 10.8 hours, longest
353 hours (about 15 days); the other six median 26.5 hours, longest 14,666 hours. At the cut, gold had been waiting
13,850 hours (about 19 months), silver 9,996 hours and SPX 27,389 hours (about 3 years): those three books were flat
96-99% of the second half (gold 179 trades in all instead of 750, silver 160 instead of 725, SPX 19 instead of 240).
The withheld entries in the current rule's own record (its FORCED entries right after a "STOP" exit): 2,675 trades,
40% won, mean -0.019R, sum -51.7R; BTC + ETH 762 trades, mean -0.070R, sum -53.1R (both halves negative); the other six
1,913 trades, mean +0.001R, sum +1.4R.

**Descriptive: both changes in one book** (wait + 30-day filter; no bar, not a live book): pooled 2,516 trades, mean
+0.067R, sum +169.5R (+110.1R / +59.4R by half), flat 67%, worst fall -27.6%; BTC + ETH 1,311 trades, +93.1R (+68.7R /
+24.4R), flat 40%, worst fall -63.9%. They overlap: on BTC + ETH the filter alone made +135.3R and the wait alone +64.5R,
together +93.1R, less than the filter alone.

**Deviations:** none from the registered rule, replay or read-outs. Choices made with the code: the switch is the state
key `wait_stop` = {"on": 0 off / 1 waiting / 2 waiting and a forced entry already withheld, "blocked": sessions withheld,
"episodes": stop-outs with a withheld entry}; "sessions withheld" counts every flat session past the mandate in which
the forced entry was refused; the waits are completed ones (a wait still open at the cut is reported apart). The replay
checks that the engine's own `b_wait_stop` (via `run_challenger`) gives the very book the script ran (it did).

**Reading.** By the bar it survives, but on two very different footings. On BTC and ETH the book still trades (flat
about 21% of bars, waits of hours to two weeks) and its gain over the current rule (+72R) is close to what the withheld
forced entries lost there (-53R). On the other six markets signals rarely clear the entry bar by themselves, so after a
stop-out the book often waits for months or years: most of its better R and its shallower fall there come from hardly
trading, not from better trades, and gold, silver and SPX were in effect switched off for the second half. The pooled
worst-fall check is therefore weak evidence. The idea was FOUND on this same history (H65, H66), so the replay cannot
validate it. The test is the forward shadow book `b_wait_stop` (starts flat at its first live bar, with no wait until
its first stop-out), first read at 30 closed trades against `b_targets` over the same days; on gold, silver and SPX it
may take a long time to reach any trades. Nothing reaches the Setups book or the vault without the owner's word.
## H69. RL ROUND 5 PRE-CHECK: do the four untested crypto inputs (Korea premium, BTC dominance, spot vs perp leadership, CME gap) carry anything on their own, one at a time? (registered 22 Nov 2026, about 11:00 UTC, before any H69 code existed or any H69 number was computed)

**Prompted by:** the owner, 22 Nov 2026: "Run all above", on the RL audit of 21 Nov, task 9: "Test the untested inputs one
at a time (Korea premium, dominance, spot-versus-perp leadership, CME gap). Any round 5 needs this first." H67 and H68 are
being registered on other branches today; this study takes H69. Research only: nothing in the engine, the books or the
vault changes, whatever the result.

**Known before registering (code and file metadata only, no outcome numbers).** The four inputs are the `kprem`, `dom`,
`spotlead` and `cmegap` cards of `engine15/sources/cryptox.py` (live since v5.2.2, reading-only, BTC and ETH only); they are
not among the RL Phase 4 readings (`engine15/rl/features4.py`). Source files on the server start: Upbit 15m 1 Sep 2019 (both
coins, about 252,800 rows each), Binance perpetual 15m 8 Sep 2019 (BTC) / 27 Nov 2019 (ETH), ECB USD/KRW 31 May 2019,
CoinMetrics caps and DefiLlama stablecoins 1 Jan 2019; the CME gap uses the project's own spot bars from the CME launch
week (BTC 15 Dec 2017, ETH 5 Feb 2021). So all four have history in both halves; whether any is too thin is decided by the
rule below, from the computed availability. These cards were rated by the card rating of 17 Nov 2026
(`research/CARD_PIPELINE.md`); its numbers for them were NOT read before this registration. Availability lags, from the
code: Korea premium and spot vs perp use another venue's 15m candle, known 1 minute after its close, so at a bar's close
they describe the PREVIOUS bar (max age 1 hour); USD/KRW is the ECB rate known at 17:00 Frankfurt (max age 5 days);
dominance uses day D known at D+1 06:00 UTC (max age 3 days); the CME gap uses the bar's own close (spot bars, known at
the close). Every reading is joined as of its `known_ms` (`flows._asof`); nothing is used before it was published.

**The inputs (13 features in 4 groups), exactly as `cryptox.features()` computes them, recomputed by the engine's own code
from the source files on spot bars cut at the end of the data (no new transform).** Korea premium: `kp_prem`, `kp_z30`,
`kp_chg24`. BTC dominance: `dm_btc_7d`, `dm_btc_30d`, `dm_stable_7d`, `dm_stable_30d` (the same values for both coins). Spot
vs perp: `sl_share_z`, `sl_taker_diff`, `sl_lead`. CME gap: `cg_open` (defined only while CME is shut: weekend rows),
`cg_above`, `cg_below` (from the CME launch week; "no unfilled gap within 3 daily ATRs" is the value 0, as the RL agent
would receive it). A row where a reading is "no read" (its raw companion NaN) is left out for that feature, never counted
as 0 (except the CME proximities above, where 0 is a real value).

**Data.** BTCUSDT and ETHUSDT 15m Binance spot bars, decisions at each bar close from 2020-01-01 00:00 UTC; prices only from
bars opening before 2025-11-10 23:45 UTC, so the last price used is that bar's close and nothing from the sealed holdout
(2025-11-11 onward) is read or computed. A row is used for horizon h only if its forward close is inside the same half.
Halves: first = decision and forward close before 2023-06-08 00:00 UTC; second = from 2023-06-08 00:00 UTC.

**The measure.** For each feature, coin, horizon h in {4 bars (1 hour), 16 bars (4 hours), 96 bars (24 hours)} and half:
1. **Raw IC**: the Spearman rank correlation between the feature at a bar's close and the forward log return
   ln(close[t+h] / close[t]).
2. **Partial IC (beyond past price)**: the same after taking out what past price already says: the ranks of the feature
   and of the forward return are each residualised (least squares, within the coin and half) on the ranks of the trailing
   log returns over 4, 16, 96 and 672 bars and of the trailing 96-bar realised volatility; the IC is the correlation of
   the residuals. Reason: the CME open move is a past return by construction, and a Korea premium change moves
   mechanically with price when one venue lags; a "signal" that is only past price is already in the RL agents' inputs.
3. **Interval**: 95% percentile interval from a month-clustered bootstrap (calendar months resampled with replacement,
   2,000 replicates, seed 20261122), computed from per-month sums with the ranks and residuals fixed. Bars are heavily
   autocorrelated and forward windows overlap, so no naive p-value is reported. A 24-hour window can spill one day into
   the next month; that small leak between clusters is accepted and said.
4. **Volatility thirds (descriptive only, passes nothing)**: the raw IC within thirds of trailing 96-bar realised
   volatility (cut points per coin over the whole 2020-01-01 to 2025-11-10 sample), per half.

**Rule, fixed now.** A feature-horizon PASSES ON A COIN when, in BOTH halves, its IC has the same sign, |IC| >= 0.01, and
the clustered interval excludes zero. It PASSES when it passes on BOTH coins with the same sign; the one exception is the
dominance group, which may pass with opposite signs on the two coins (a rising BTC share can be expected to act one way on
BTC and the other way on ETH, an alt); this exception is fixed now, before any number. Verdict per INPUT (group):
- **WORTH A REGISTERED PLACE IN ROUND 5**: at least one of its feature-horizons passes on the raw IC AND on the partial IC.
- **MOSTLY PAST PRICE**: some feature-horizon passes on the raw IC, none on the partial IC.
- **ONE COIN ONLY**: no feature-horizon passes on both coins (raw and partial), but one passes on one coin (raw and
  partial). Not a place in a pooled round.
- **NOTHING SHOWN**: none of the above.
- **CANNOT BE TESTED YET**: in either half on either coin, fewer than 12 calendar months with at least 1,000 usable rows for
  every feature of the group, or under 50% of the half's rows usable for every feature (for `cg_open`, of the weekend
  rows). Reported with the numbers.
The verdicts are checked in this order: cannot be tested, worth a place, mostly past price, one coin only, nothing shown.
"Worth a place" means only that a later round may include the input as a registered candidate, where it must still beat
costs out of sample under that round's own bar. It is not evidence of an advantage.

**Number of looks.** 13 features x 3 horizons = 39 feature-horizons, each judged on 2 coins x 2 halves x 2 measures (312
intervals), plus 234 descriptive volatility-third ICs. Some of these will look good by chance. The two-half, same-sign,
both-coin rule is the guard: if each cell were independent a null feature-horizon would pass with probability well under
1 in 10,000, but BTC and ETH move together (and dominance is the same series for both), so the honest figure is nearer the
one-coin rate, about 2 x 0.025^2 = 0.00125 per feature-horizon on each measure, or roughly a 5% chance that at least one
of the 39 passes the raw rule by luck. The features within a group are also correlated with each other.

**Read-outs.** For each feature: first row, rows usable per half and coin, share missing; the raw and partial IC with
intervals per coin, half and horizon; the pass flags; the volatility-third ICs; the verdict per input.
**Computed** by `research/h69_rl_untested_inputs.py` on the research server, in a scratch folder reading the engine's data
read-only; output `research/out/h69_rl_untested_inputs/results.json` and `report.md`.

### H69 results (22 Nov 2026, run 10:53 UTC on the research server, 34 s; `research/out/h69_rl_untested_inputs/report.md` + `results.json`)

**Gate (point in time):** the 13 features and their raw companions recomputed on bars and source files cut at
2022-09-14 13:00 (BTC) and 2024-03-20 07:00 UTC (ETH) equal the full-data values on every row up to the cut. The source
files were copied keeping only rows known before 2025-11-11 00:00 UTC; bars opening at or after 2025-11-10 23:45 were
dropped before anything was computed.

**All four inputs could be tested**, both coins, 2020-01-01 to 2025-11-10 (ETH's CME gap from 5 Feb 2021): every all-hours
feature has 99-100% of rows usable in both halves (about 120,000 rows in the first half, 85,000 in the second, 41 and 29
months). `cg_open` exists only while CME is shut (about 35,000 / 25,000 BTC rows); its months never reach 1,000 rows (a
weekend month holds about 850), so on its own it would have read "thin" under the registered threshold; the group is
testable through `cg_above` / `cg_below`, as the rule says.

**Verdicts by the registered rule. No input earns a registered place in round 5.**

| Input | Verdict | What passed (raw IC, half 1 / half 2, BTC; ETH) | Partial IC (beyond past price) |
|---|---|---|---|
| Korea premium | MOSTLY PAST PRICE | `kp_chg24` 1 h: +0.021 / +0.025; +0.020 / +0.023. 4 h: +0.023 / +0.035; +0.022 / +0.032 | 1 h: +0.004 / +0.002; +0.006 / -0.004. 4 h: -0.001 / +0.002; +0.002 / -0.002 (none excludes zero) |
| CME gap (spot proxy) | MOSTLY PAST PRICE | `cg_open` 1 h: -0.067 / -0.065; -0.056 / -0.057. 4 h: -0.101 / -0.055; -0.093 / -0.053 | 1 h: -0.021 / -0.003; -0.019 / +0.001. 4 h: -0.034 / +0.005; -0.041 / +0.002 (second half about zero) |
| BTC dominance | NOTHING SHOWN | none | `dm_stable_7d` 24 h passed on BTC only (+0.064 / +0.035) with its raw IC not passing; ETH second half +0.001 |
| Spot vs perp | NOTHING SHOWN | `sl_taker_diff` 4 h on BTC only (-0.020 / -0.021); ETH -0.015 / +0.009 | on BTC at 1 h only (-0.012 / -0.016), not the same horizon |

Of 39 feature-horizons, 4 passed the raw rule (both inside the two groups above) and 0 passed the partial rule on both
coins; about 2 raw passes would be unremarkable by luck with features this correlated. Reading: the weekend CME move has
tended to give back part of itself over the next hours, and a rising Korea premium has come with continued price, but in
both cases the trailing returns (1 h to 7 days) already carry it; once they are taken out nothing is left in the second
half. The volatility thirds (descriptive, 4 h) keep the raw `cg_open` and `kp_chg24` signs in most thirds (exceptions: BTC
`kp_chg24` in the low-volatility third of the first half, ETH `cg_open` in the high-volatility third of the second half);
no third stands out consistently. Nothing here is evidence of an advantage.

**Deviations:** none from the registration. Two notes: (1) the `cg_open` monthly-row quirk above was not foreseen when
the 1,000-row threshold was written; it changes no verdict. (2) `report.md` says errors from the cards not under test
were "expected"; in fact none were raised (with their files absent those cards return empty).
**For a round 5:** none of the four is registered as a candidate input by this rule. If a round 5 is ever run, these
four should not be added on the strength of this study; `kp_chg24` and `cg_open` duplicate the past-return inputs the
agents already have.

## H70. BTC and ETH: a long on a sharp rebound out of an oversold state, tested in three sealed stages (registered 22 Nov 2026, about 11:30 UTC, before any H70 code existed or any H70 number was computed)

**Prompted by:** the owner, 22 Nov 2026: "Deploy a study to find how this 15minds engine can confluence mean reversion
and turn long when sharp rebound happen. With stasticially proven edge." H66: in 505 sudden rallies while the Setups
book was short it lost in 93%, turned long within the day in 26% and sold again inside the rally in 24%. H65: the book
earns with a market's own 30-day move and loses against it, so a trend rule will not turn long early in a rebound.
Research only: nothing in the engine, the books or the vault changes, whatever the result. A study cannot show a
proven edge; it can only say whether a rule fixed in advance held up on data it was not chosen on.

**Known before registering:** H65 to H69 (above). No number about any of these oversold states, triggers or this long
trade has been computed on these markets for this study; none was looked at before this registration.

**Markets.** BTCUSDT and ETHUSDT decide everything (pooled, and each alone). XAUUSD, XAGUSD, USDJPY, SPX, WTI, BRENT
appear only in a descriptive table for a candidate that passes Stage 2; they pass or fail nothing.

**Three stages, three periods, in this order** (a period is the deciding bar's open time, UTC):
- Stage 1 DISCOVERY: the first decided session (2020-02) to 2023-06-07 23:45.
- Stage 2 CONFIRMATION: 2023-06-08 00:00 to 2025-11-10 23:45. Only the candidates Stage 1 selected (at most 3).
- Stage 3 FINAL: 2025-11-11 00:00 to the last stored session at or before 2026-11-21 13:45 (the sealed holdout).
  Only candidates that passed Stage 2. This uses the holdout once for this question.
Each stage is a separate run of `research/h70_rebound_long.py --stage N`. Stage N cuts every input (bars, readings,
odds) at its own period's end before anything is computed (`h59.prep_cut` with that end), so it cannot read later
prices. Stage 1 writes `selection_stage1.json`; Stage 2 refuses to run without it and evaluates only the candidates it
names, then writes `selection_stage2.json`; Stage 3 refuses to run without that and evaluates only its survivors. A
trade belongs to the period of its deciding bar and must END inside that period: an event whose 96-bar exit window would
run past the period's last bar is not taken (counted). So no stage's result uses a price from a later period.

**Readings (closed bars only, as known at the deciding close k).** From the evidence store where it holds them:
`atr1h` (ATR(14) of the 1h chart, joined by `data.htf_on_15`), `atr15` (ATR(14) of the 15m chart), `bias_ema50_1h_px`
(EMA50 of 1h closes, joined), `sw_hi_15m` (the last confirmed 15m swing high, `structure.swings`); if a column is
missing, it is computed from the bars by the same engine function (said in the output). Computed here: EMA20 of 15m
closes (`ewm(span=20, adjust=False)`); RSI(14) of 1h closes (`indicators.rsi` on `data.resample(.., "1h")`, joined by
`data.htf_on_15`); the 24-hour return (close k against the close of the last bar whose open is at or before open(k)
minus 24 hours; on BTC and ETH exactly 96 bars back).

**A candidate = OVERSOLD x REBOUND x CONFLUENCE, entered long.**
- OVERSOLD at a bar: (O1) close <= `bias_ema50_1h_px` - 3 x `atr1h`; (O2) 24-hour return <= -6%; (O3) RSI(14) of 1h
  closes <= 30 at some bar within the last 32 bars (8 hours) including this one.
- REBOUND trigger at the deciding close k, taken only if the oversold state was true at some bar in k-15..k, and only at
  its ONSET (the condition true at k and false at k-1): (R1) close > EMA20(15m); (R2) close >= the lowest low of bars
  k-15..k + 1.5 x `atr15`; (R3) close > `sw_hi_15m`.
- CONFLUENCE: (C0) none; (C1) the engine's own odds at k: P(up) - P(down) >= -0.05 (`prep["odds"]`, `labels.UP/DOWN`).
3 x 3 x 2 = 18 candidates, named e.g. O1-R2-C1. Every candidate only from the coin's first decided session (bars with
odds), so C0 and C1 share one population. One trade at a time per candidate and coin: an event at k is taken only if
k is at or after the exit bar of that candidate's previous trade on that coin.

**The trade (one rule for all, fixed now).** Entry at the open of bar k+1. Stop = lowest low of bars k-15..k minus
0.25 x `atr15`(k). R = entry - stop. Skipped and counted: entry <= stop, or stop distance under 0.3% or over 8% of
the entry. Bars k+1 .. k+96 are walked; in each bar the stop is looked at first (low <= stop: out at the stop, or at
the open if the open is already below it); then +1R (high >= entry + 1R: half out at +1R exactly, and the stop on the
rest moves to the entry from the NEXT bar); then +2.5R (high >= entry + 2.5R: the rest out at +2.5R exactly, also in
the same bar as +1R). Whatever is left goes out at the close of bar k+96 (24 hours). Targets fill at their price, never
better. Result per trade in R after fees: the fee is the book's, `cost_side` (0.10% of notional per side for BTC and
ETH) and `asset_cost` for the other six, on entry and on each part's exit, divided by R. Also kept: the trade's
percent return (same fees), bars held.

**The baseline (the drift problem).** For a trade on coin a decided in calendar month m, its baseline is the mean R of
the same trade rule entered at EVERY eligible bar of coin a in month m of the same stage (all bars with odds, the same
stop filter, the window inside the period), with no oversold or trigger condition. EXCESS of a trade = its R minus that
month's baseline; a candidate's excess = the mean over its trades. (All bars of those months instead of 20 random
draws: the exact expectation of a random entry, with no simulation noise.)

**Intervals and p-values.** Month-clustered bootstrap: calendar months (UTC, of the deciding bar) resampled with
replacement, both coins' trades of a month kept together when pooled; 5,000 draws, seed 20261122; the statistic is the
ratio of summed values to summed trades over the drawn months. 95% interval = 2.5th and 97.5th percentiles. One-sided
p-value for "excess > 0" = (1 + #{draw - observed >= observed}) / 5,001 (the bootstrap distribution shifted to zero).
Reported for mean R and for excess.

**Stage 1 selection rule (fixed now).** A candidate is selected only if, on BTC and ETH pooled in Stage 1: at least
150 trades; mean R > 0; excess > 0 with its 95% interval above zero; and the excess > 0 on BTC alone and on ETH alone
(point values). If more than 3 qualify, the 3 with the largest pooled excess. If none qualifies, the study stops and
reports "nothing to confirm"; Stages 2 and 3 are not run.

**Stage 2 pass rule (fixed now).** On BTC and ETH pooled in Stage 2: at least 80 trades; mean R > 0; excess > 0 with
one-sided p < 0.05 / (number selected in Stage 1) (Bonferroni); excess > 0 on each coin alone. 18 candidates are looked
at in Stage 1; the Stage 1 interval filter, Bonferroni over the selected and a fresh period are the guards.

**Stage 3 (holdout), for each Stage 2 survivor:** trades, share won, mean R, sum of R, excess with its interval and
p-value, the longest run of consecutive losing trades and the deepest fall of cumulative R. "Holds in the holdout" only
if mean R > 0 and excess > 0 with at least 30 trades. One year is short; that is said with the result.

**Descriptive, only for a candidate that passes Stage 2 (passes nothing; over the whole history to the cut, one
continuous run without stage boundaries):** (a) the H66 sudden-rally episodes recomputed the same way (a bar where the
current Setups book `b_targets` holds a short and the close 96 bars later is at least 5% higher, the next looked for
after those 96 bars, from the coin's first decided bar; the count should be 505): in how many the candidate decided an
entry inside the episode (bars t+1..t+96), the median hours from the episode start, and those trades' R; (b) entries a
year and median bars held; (c) what `b_targets` held at the deciding bar (short, long, flat) and its marked equity
change (paper, 1x) over the trade's 96 bars, beside the candidate's own percent return; (d) the same candidate on the
other six markets per stage (trades, mean R, excess), with their own fees.

**Read-outs.** `research/out/h70_rebound_long/`: `stage1.json`, `selection_stage1.json`, and as the stages are reached
`stage2.json`, `selection_stage2.json`, `stage3.json`, `results.json` (all merged) and `report.md`; skipped events
counted by reason. A study that finds nothing is a complete answer.

### H70 results (22 Nov 2026, Stage 1 run 11:28 UTC on the research server, 12 s; `research/out/h70_rebound_long/report.md` + `results.json`)

**Verdict by the registered rule: NOTHING TO CONFIRM.** No candidate met the Stage 1 selection rule, so Stage 2 was not
run, and the holdout (2025-11-11 onward) was not opened: it stays sealed for this question. Stage 3 refused to run, as it
was built to, without a Stage 2 selection.

**Why nothing qualified.** All 18 candidates lost money per trade after fees in Stage 1 (mean R from -0.05 to -0.25, every
one below zero; 5 of 18 have a 95% interval that reaches above zero, none has a point value above it). The rule needs mean
R above zero first. Most candidates did beat the matched baseline (random long entries in the same coin and month with the
same trade), which lost -0.256R a trade on BTC and -0.182R on ETH: 10 of 18 have an excess interval above zero, the best
O2-R1-C0 (24-hour return -6% or worse within the last 4 hours, then a 15m close back above its EMA20; no odds filter),
+0.160R [+0.081, +0.252], p 0.0006, positive on both coins.

Stage 1, BTC and ETH pooled, 2020-02-05 to 2023-06-06 (41 months). Each cell: trades, share won, mean R [95%], excess
over the baseline [95%].

| Candidate | No odds filter (C0) | With the odds filter (C1) |
|---|---|---|
| O1-R1 | 780, 49%, -0.124 [-0.196, -0.046], +0.130 [+0.054, +0.206] | 569, 48%, -0.162 [-0.241, -0.076], +0.092 [+0.011, +0.177] |
| O1-R2 | 1273, 46%, -0.221 [-0.276, -0.159], +0.035 [-0.020, +0.093] | 601, 46%, -0.247 [-0.327, -0.158], +0.010 [-0.076, +0.098] |
| O1-R3 | 378, 46%, -0.171 [-0.265, -0.064], +0.088 [-0.012, +0.201] | 292, 46%, -0.167 [-0.278, -0.042], +0.091 [-0.026, +0.222] |
| O2-R1 | 531, 51%, -0.053 [-0.147, +0.055], +0.160 [+0.081, +0.252] | 369, 52%, -0.051 [-0.146, +0.046], +0.144 [+0.063, +0.227] |
| O2-R2 | 801, 48%, -0.122 [-0.188, -0.048], +0.091 [+0.029, +0.160] | 390, 50%, -0.086 [-0.178, +0.019], +0.106 [+0.013, +0.213] |
| O2-R3 | 309, 48%, -0.090 [-0.194, +0.024], +0.116 [+0.015, +0.224] | 240, 50%, -0.056 [-0.174, +0.076], +0.138 [+0.023, +0.268] |
| O3-R1 | 774, 50%, -0.113 [-0.175, -0.050], +0.139 [+0.067, +0.209] | 593, 49%, -0.151 [-0.218, -0.087], +0.100 [+0.023, +0.175] |
| O3-R2 | 1253, 47%, -0.208 [-0.259, -0.151], +0.049 [-0.005, +0.104] | 723, 47%, -0.248 [-0.319, -0.171], +0.008 [-0.071, +0.085] |
| O3-R3 | 510, 46%, -0.175 [-0.259, -0.085], +0.079 [-0.014, +0.179] | 424, 46%, -0.181 [-0.285, -0.074], +0.074 [-0.042, +0.192] |

The engine's odds filter (C1) made the excess smaller in 6 of 9 pairs (larger in O1-R3, O2-R2 and O2-R3, by +0.003, +0.015 and
+0.022R).

**Post hoc, descriptive, not registered (Stage 1 data only; `research/h70_posthoc_fees.py`, `posthoc_fees_stage1.json`).**
The same trades WITHOUT fees: the baseline is about zero (BTC -0.014R, ETH +0.022R; median stop 0.97% / 1.22% of price, so
the 0.20% round trip costs about 0.21R / 0.16R a trade), and the candidates range from -0.073R to +0.038R (best O2-R1-C1
+0.038, O2-R1-C0 +0.026, O2-R2-C1 +0.026). So most of the "excess" is not a better direction: the oversold entries have
WIDER stops (median 1.15% to 3.4% of price against about 1% for a random bar), so the same fee is a smaller part of R. Before
fees the best rebound entry made about +0.03R a trade more than a random entry; after fees it still lost.

**Deviations:** none from the registered rule. Notes: (1) the registration's heading says "about 11:30 UTC"; it was
committed at 11:19 UTC (commit ecf42cd), before any H70 code existed. (2) The post-hoc fee read above was not registered;
it uses only Stage 1 data and changes no verdict. (3) Stages 2 and 3 and the descriptive read-outs (rallies, frequency, what
the book held, the other six markets) exist in the script but were not run, because their precondition (a Stage 1
selection) was not met.

**Reading.** Out of an oversold state, these rebound triggers picked better long entries than a random bar in the same
month, but not good enough to pay a 0.20% round trip with a stop at the rebound's low and a 24-hour exit, and adding the
engine's own odds mostly made them worse (6 of 9 pairs), not better. Nothing here supports adding a rebound long to the Setups book. A different
trade shape (wider stop, longer hold, a lower-cost venue) would be a NEW question with its own registration and a fresh
discovery period; it could not reuse this Stage 1 as if it had not been seen.
## H71. BTC and ETH in an oversold state: do the engine's own odds, voices and card readings carry information about a rebound, and does the way the engine combines them lose it? (registered 22 Nov 2026, about 11:40 UTC, before any H71 code was run or any H71 number was computed)

**Prompted by:** the owner, 22 Nov 2026: "how this 15minds engine can confluence mean reversion and turn long when sharp
rebound happen", with statistics behind it. H70 (another branch, running now) tests price-pattern entry rules; this study
asks about the engine's own evidence. Research only: nothing in the engine, the books or the vault changes, whatever the
result. A study cannot promise an edge; "nothing holds up" is a complete answer.

**Known before registering (no H71 outcome numbers).** H65: the lead in the odds did not hold up across halves as a
trade filter; the Setups book earns with a market's 30-day move and loses against it. H66: in 505 sudden rallies while
short the book turned long within 24 hours in 26%. The rule (`policy.decide`): from flat a long needs a 5-point lead in
the odds (10 when risk is high, 15 against the higher-timeframe bias); a short flips long at a 10-point up lead or when
the bias turns up.

**Data.** BTCUSDT and ETHUSDT, 15-minute closes, the evidence store and the cached weekly fits read only, through the
research helpers' path (`research/h59_half_be.py::prep_cut`, the frame H65 used): bars from `data.load`, readings from
`prep["ev"]`, the combined odds as `prep["odds"]`, each voice's probabilities from the same walk. The fits are COPIED into
the scratch folder before each stage (the walk deletes cached fits it does not use and writes any refit; copying keeps
`/data/mind15` untouched).
**Are the odds and voices out-of-sample when produced? Yes, by the code** (`engine15/leanprep.py::walk_forward_cached`):
the fit used for the week starting at session s is trained only on rows r <= s - 96 whose triple-barrier grade
(bars r+1 .. r+96) is complete by the close of bar s, and it is applied to sessions s .. s+671 only. Each voice's three
probabilities at a bar therefore come from a fit made before that bar. The combined odds mix the voices with trust
weights (`trust_tail`) built only from losses of calls whose grade had arrived by that bar. Known difference from the
live engine: this replay frame has no v5.2 trust cap (no card above 40%); it is the frame H36/H59/H65 used. The
readings themselves are fixed functions of closed bars (`data.htf_on_15`; the project's test
`test_evidence_never_reads_the_future`); I rely on that test and do not re-verify every reading.

**Stages, in order, each frozen before the next; the walk and every input are CUT at the stage's end before anything is
formed (`prep_cut(end=...)`), so a stage cannot see later prices.**
- DISCOVERY: from the first bar with odds at or after 2020-02-01 to 2023-06-07 23:45 UTC.
- CONFIRMATION: 2023-06-08 00:00 to 2025-11-10 23:45 UTC, only for what discovery selected (at most 3).
- HOLDOUT (sealed): 2025-11-11 00:00 to the last stored session at or before 2026-11-21 13:45 UTC, only for what
  confirmation passed; one year is short, and is said so.
A bar is used for horizon h only if its forward close is inside the same stage. The script takes `--stage`; the
confirmation stage refuses to run without `selection.json` from discovery and computes nothing for a reading not in it;
the holdout refuses to run without `confirmation.json` and computes only the readings that passed. The descriptive
read-out (below) is computed in discovery and confirmation only; the holdout is not opened for it.

**The oversold state (fixed).** 24-hour return (close against the close 96 bars earlier) of -6% or lower, OR the close at
least 3 x ATR(1h) below the 1-hour EMA50 (`(px - bias_ema50_1h_px) / atr1h <= -3`, the stored readings; computed from
bars the same way where a stored column is absent). **The overbought mirror**: +6% or more, or 3 x ATR(1h) above.
**Calm**: every other bar. The calm state is the contrast.

**The outcome.** Forward log return over 96 bars (24 hours) and 16 bars (4 hours) from the bar's close; a "sharp rebound"
flag: close 96 bars later at least 5% above the close.

**The readings tested (12, picked from the code before any outcome; "lead" = P(up) - P(down) of the 24-hour barrier
call; every lead is out-of-sample as above).**
1. `lead`: the engine's combined odds lead (what `policy.decide` acts on).
2. `v_meanrev`: the "Stretch and exhaustion" voice's own lead (stretch from the 1h/4h averages, range position, StochRSI).
3. `v_pullback`: the "Pullback inside the trend" voice's lead.
4. `v_momentum`: the "Momentum" voice's lead (moves over 1h, 4h, 24h, 7d against volatility).
5. `v_structure`: the "Market structure" voice's lead (swing structure 15m to 1d, position in the swing range).
6. `v_regime`: the "Market regime" voice's lead (daily regime labels and numbers).
7. `v_levels`: the "Support and resistance" voice's lead (nearest levels, strength, room).
8. `v_flow`: the "Order flow (CVD)" voice's lead (net taker buying 1h/4h/24h, flow without price progress).
9. `k_1h`: StochRSI on 1-hour bars, scaled -1..+1 (a raw card reading; low = oversold).
10. `stretch_4h`: (close - 4h EMA50) / ATR(4h), clipped (a raw reading; how deep the larger stretch is).
11. `cvd_div`: taker buying minus price progress over 4h (a raw reading; buying without price = absorption).
12. `fund_z`: the funding rate against its last 90 fundings (a raw reading; negative = shorts crowded and paying).
A voice that is not ready at a bar (NaN probabilities) or a reading that is NaN leaves that bar out for that reading.

**Measures, each on bars in the state only, within each stage.**
1. Raw IC: Spearman rank correlation of the reading with the forward return (24h and 4h).
2. Partial IC (beyond past price): ranks of the reading and of the forward return each residualised (least squares,
   within coin, state and stage) on the ranks of the trailing log returns over 4, 16, 96 and 672 bars and of the trailing
   96-bar realised volatility; the IC is the correlation of the residuals. Pooled = both coins' residuals together.
3. Month-clustered bootstrap: whole calendar months (of the bar's time) resampled with replacement, 4,000 draws, seed
   20261122, from per-month sums with ranks and residuals fixed; 95% percentile interval. One-sided p (confirmation,
   holdout): the share of centred draws, (b - estimate), at least as far as the estimate in the registered direction,
   (1 + count) / (1 + draws). A 24-hour window can spill into the next month; that small leak is accepted.
4. Hit rate (descriptive): share of sharp rebounds when the reading is in its top third and in its bottom third against
   the state's base rate; the third cut points are set per coin on the discovery oversold bars and reused unchanged later.
5. The same raw and partial ICs in the calm state, as contrast (selects nothing).

**Discovery selection (fixed).** A reading is selected only if, in the oversold state, its partial IC with the forward
24-hour return has the same sign on BTC and on ETH, the pooled month-clustered 95% interval excludes zero, and the pooled
|partial IC| >= 0.02. At most the 3 largest by pooled |partial IC|. None qualifies: stop and report "nothing to confirm".
**Confirmation pass (fixed).** Partial IC (oversold, 24h) of the same sign as in discovery on BTC and on ETH (point
estimates), and pooled one-sided p below 0.05 / (the number selected) (Bonferroni).
**Holdout read (fixed).** For each reading confirmed: pooled partial IC of the same sign with one-sided p below 0.05 /
(the number confirmed) "held in the holdout"; else "did not hold in the holdout". BTC and ETH shown alone.
**Number of looks.** 12 readings x 2 horizons x 2 measures x 2 states x 3 (BTC, ETH, pooled) in discovery = 288 ICs,
plus hit rates; only the 12 oversold 24h partial ICs can select. With 12 null readings and the both-coins-same-sign plus
interval rule, by luck about one might pass (BTC and ETH move together, and several voices share inputs), which is why
confirmation exists and is Bonferroni-corrected.

**Descriptive read-out (fixed, passes nothing).** In the oversold state, discovery and confirmation: the share of bars
where the combined odds lead UP by 5 points or more (the long bar from flat), by 15 or more (the bar against the bias),
lead DOWN by 5 or more, and in between; for each, bars, months, mean and median forward 24-hour return and the
sharp-rebound rate; and the same split by `htf_bias` = -1 (down) against not down.

**Computed** by `research/h71_voices_at_rebounds.py` on the research server in a scratch folder; output
`research/out/h71_voices_at_rebounds/` (`discovery.json`, `selection.json`, `confirmation.json`, `holdout.json` as
reached, `report.md`).

**Changes from the proposal given to me, made before registering:** (1) the fits are copied, not used in place (the walk
deletes unused fits and writes refits); (2) each stage cuts the walk at its own end rather than slicing after a full walk;
(3) "top third" is shown with the bottom third too, since several readings point to a rebound at the low end (StochRSI,
stretch, funding); (4) the calm state is "neither oversold nor the overbought mirror"; (5) the descriptive read-out adds
the 15-point bar and stays out of the holdout; (6) 4,000 bootstrap draws.

### H71 results (22 Nov 2026, 11:28 to 11:40 UTC on the research server; `research/out/h71_voices_at_rebounds/report.md` + `discovery.json`, `selection.json`, `confirmation.json`, `holdout.json`)

**Verdict by the registered rule: nothing confirmed. None of the engine's own readings carried information about the
next 24 hours after an oversold state that passed confirmation; the holdout was not opened.**

The walk reused every cached fit (discovery 174, confirmation 301, 0 refits), so the odds and voices are the same
out-of-sample weekly walk the other replay studies use. Oversold bars: discovery (2020-02-05 to 2023-06-07) BTC 9,435 and
ETH 11,669 in 41 months; confirmation (2023-06-08 to 2025-11-10) BTC 5,324 and ETH 6,429 in 30 months. Base rate of a
sharp rebound (+5% in 24 hours) in the oversold state: discovery BTC 10.0%, ETH 17.8% (calm 6.5%, 11.4%); confirmation
5.8%, 9.2% (calm 2.9%, 5.4%).

**Discovery (12 readings, oversold, partial IC with the 24-hour return).** Two qualified and were selected:
`lead` +0.120 [+0.059, +0.174] (BTC +0.143, ETH +0.108; raw IC only +0.041 [-0.024, +0.101]) and `fund_z` -0.088
[-0.169, -0.018] (BTC -0.145, ETH -0.060; raw -0.125). Nearest misses: `v_regime` -0.074 [-0.146, +0.004], `stretch_4h`
+0.075 [-0.047, +0.172], `v_meanrev` +0.051 [-0.025, +0.131]. The mean-reversion voices (`v_meanrev`, `v_pullback`)
and `k_1h` showed nothing that excluded zero at 24 hours.
**Confirmation (Bonferroni, p < 0.025 one-sided):**
- `lead`: BTC +0.064, ETH +0.071, pooled +0.068 [-0.120, +0.222], p = 0.21. FAILED.
- `fund_z`: BTC -0.085, ETH -0.071, pooled -0.076 [-0.154, +0.021], p = 0.026. FAILED, narrowly (threshold 0.025).
  Raw IC -0.155 [-0.237, -0.056]; much of it is what past price already says. In discovery the same negative sign was
  there in the calm state too (-0.059 [-0.101, -0.015]), so funding is not an oversold-specific rebound signal.
Hit rates (descriptive): the engine's lead in its top third did NOT raise the share of sharp rebounds (discovery BTC 9.3%
against 10.0% base; confirmation 3.8% against 5.8%); low funding (bottom third) did on ETH (22.2% against 17.8%;
16.7% against 9.2%) but much less or not on BTC (14.1% against 10.0%; 5.1% against 5.8%).

**Descriptive read-out: the engine's own odds in the oversold state.** The combined odds led UP by 5 points or more in
0.1% of oversold bars in discovery (28 bars in 3 months) and 0.2% in confirmation (27 bars in 2 months), and never by 15
points. They led DOWN by 5 points or more in 62% (discovery) and 53% (confirmation) of oversold bars, 73% and 56% when the
higher-timeframe bias was down. What followed did not differ much by the lead: discovery mean 24-hour return +0.17% when
the odds led down against +0.71% in between (rebound rate 14.3% in both); confirmation with the bias down, +1.08% and a
14.0% rebound rate when the odds led down, against +0.32% and 12.1% in between. So in an oversold state the engine's odds
almost never reach its own long bar (5 points from flat, 15 against a down bias); the 15-point bar against the bias was
never met in five and a half years of oversold bars. The odds point down in most oversold bars, and the bars where they
point down were followed by no worse 24 hours than the rest.

**Reading.** In this test the engine's evidence did not carry confirmed information about a rebound after an oversold
state, and so there is no confirmed information that the combining step throws away. The engine stays out of longs in
oversold states mainly because its odds lean down there and its long bar is rarely or never reached, not because a
reading that pointed to a rebound was overruled. Low funding came closest (p 0.026 against 0.025). It would need its own
registered forward test before anyone relies on it, and it is largely past price. Nothing here is evidence of an
advantage. No engine code was changed.

**Deviations and notes.** (1) A read-out-only mode for the confirmation period (`--stage readout-confirmation`) and the
report formatter `research/h71_report.py` were added after discovery's numbers. The mode was not used, because
confirmation ran with its two readings and computed the read-out as registered. (2) Discovery starts 2020-02-05 00:00,
the first bar with odds on or after 2020-02-01. (3) The run shared the box with two other research processes (H70, H72)
started minutes earlier; each H71 stage ran as one process, niced, for about 20 seconds. (4) The odds are the replay
frame without the v5.2 trust cap (as registered).
## H72. OUT-OF-SAMPLE TEST of the H67 trend filter and the H68 wait after a stop-out: parameters chosen on the first part only, paired monthly test on the later parts (registered 22 Nov 2026, 11:25 UTC, before any H72 code was run or any H72 number was computed)

**Prompted by:** H67 and H68 both "survived as a rule" on history, but both ideas were found by looking at that same
whole history (H65), so those replays validate nothing; and H67 showed that the 20-day and 45-day versions each lose one
half to the current rule. The owner asked for statistical backing. This study is the honest out-of-sample version that
is still possible: choose the parameter on the first part, freeze it, test on the later parts, with paired trade-level
statistics instead of totals.

**What cannot be undone, said first.**
- The IDEAS (filter entries by the market's own trend; wait after a stop-out) were chosen after seeing ALL the data, the
  test period and the holdout included, in pooled form (H65, H66). No split now can make the ideas themselves
  out-of-sample.
- Several later-period totals are ALREADY KNOWN. H67 and H68 published, for the 30-day filter, the wait, and both
  together, the sum of R in the second half (2023-06-08 on) and in the holdout (2025-11-11 on); the TEST-period totals
  follow from those by subtraction. On BTC + ETH: 30-day filter second half +29.2R vs current -52.5R, holdout +14.5R vs
  +12.3R; wait +17.3R vs -52.5R, holdout +13.3R vs +12.3R; both +24.4R in the second half. For the 20-day and 45-day
  filters H67's results file holds BTC + ETH second half -8.1R and +36.9R, holdout +17.9R and +18.5R. So for those books
  the direction of the TEST difference in totals is known before this study; what is new is (a) whether a length chosen
  by a fixed rule on the first part alone is the one that gets tested, (b) whether the difference is large against its
  own month-to-month noise (a paired, month-clustered test), and (c) mean R per trade and worst fall by period.
- The CHOICE-period sums of R for 20, 30 and 45 days are also known (H67 first half, pooled: +66.2R, +86.3R, +22.3R vs
  current +29.6R; BTC + ETH +79.6R, +106.1R, +59.4R vs +44.7R). Among those three the choice rule below would pick 30;
  10, 15, 60 and 90 days have never been computed on any period.

**Books.** The engine's own `shadows.run`, called exactly as `research/h67_trend_filter.py` and
`research/h68_wait_after_stop.py` call it: the current rule (`CHALLENGERS["b_targets"]["rule"]`, think15-v5.2.9, the
early entry on BTC and ETH included); the rule plus `trend_days`: N; the rule plus `wait_after_stop`: True; and the rule
plus both. All eight markets; BTC + ETH also apart (what members follow). Inputs as H67/H68: the evidence store and the
cached fits (`fits_today`, voices walked forward) read only, each market from its first decided session to the last
stored session at or before 2026-11-21 13:45 UTC.

**Periods (trades belong to the period of their ENTRY time).** CHOICE: first decided session (2020-02) to 2023-06-07;
TEST: 2023-06-08 to 2025-11-10; HOLDOUT: 2025-11-11 to the end above (about one year: short).

**Part A, the trend filter's length.** Grid fixed now: N in {10, 15, 20, 30, 45, 60, 90} days. Choice rule fixed now:
on CHOICE, the N with the largest pooled eight-market sum of R among those whose BTC + ETH sum of R on CHOICE is also
above the current rule's BTC + ETH sum of R on CHOICE; exact ties go to the longer N. An N qualifies only if it also
beats the current rule's pooled eight-market sum of R on CHOICE. If no N qualifies, Part A stops with "nothing to test".
For the choice the books are run ONLY on bars before 2023-06-08 (the code passes the TEST start as the end of the run,
so no later bar is read); a trade still open at that cut is not counted in the choice. The chosen N and every CHOICE
number behind it are written to `choice.json` before any later number is computed.

**Part B, wait after a stop-out.** No parameter: tested as it is on TEST and HOLDOUT (its CHOICE numbers shown beside).
Its primary comparison is BTC + ETH only (H68: on gold, silver and SPX it mostly stops trading); the eight-market figure
is shown beside it with the share of bars flat.

**Part C, both together:** the trend filter with Part A's chosen N plus the wait. If Part A stops, Part C is not run
(it would be Part B again).

**Statistics, fixed now.** The comparison is PAIRED in time. Both books are run over the whole history in one pass (the
state carries across period boundaries, as it would live). For each market and each calendar month (partial months at a
period's start and end count as their own month of that period; every calendar month of the period counts, a month
without trades as 0): d = (new book's sum of R over trades entered that month) - (current rule's). Pooled d for a set
of markets = sum over those markets. Test: mean monthly d above zero, one-sided, month-clustered bootstrap (resample
whole calendar months of the period with replacement, 10,000 draws, numpy default_rng seed 72); p = (1 + number of
draws with mean <= 0) / (1 + 10,000); 95% interval = 2.5th and 97.5th percentiles of the draws. Also, per book and
period: trades, share won, mean R per trade with a month-clustered 95% interval (same resampling, the ratio of sums),
sum of R, share of bars flat, and the worst fall of the marked equity (the set's books summed; peak reset at the
period's start; in percent of the peak).

**Pass rule on TEST, fixed now, for each frozen rule (A: filter N*; B: wait; C: both).** PASS only if BOTH: (1) on BTC +
ETH pooled the mean monthly d is above zero with a Holm-adjusted one-sided p below 0.05, the Holm correction taken over
the frozen rules actually tested in TEST (3, or 1 if Part A stops); (2) the pooled eight-market mean monthly d is not
negative (point estimate >= 0). The raw p and whether it is below 0.05/3 (the stricter all-at-once bar) are shown too.
**"Holds in the holdout":** BTC + ETH mean monthly d above zero in the holdout (point estimate), with its interval and
p shown; the holdout is one year, so this is a weak check and is not a pass/fail on its own.

**One registered descriptive table, not used for any choice:** all seven N against the current rule on CHOICE, TEST and
HOLDOUT (sum of R, mean monthly d with its interval, BTC + ETH and eight markets), so the owner can see how sensitive
the result is to the length. The script computes it only after `choice.json` and the frozen rules' results are written.

**Changes from the design as first written (before registering):** (1) the CHOICE runs stop at the TEST start, so the
choice cannot read later bars; (2) the pass threshold is stated as Holm-adjusted p < 0.05 over the rules actually tested
(the first draft said both "p below 0.05/3" and "Holm"; Holm equals 0.05/3 for the smallest p and is looser for the
others; both are reported); (3) the eight-market guard in the pass rule applies to Part B too, with B's eight-market
figure read beside its share of bars flat; (4) the already-known totals above are written down so a reader can see what
is and is not new; (5) the p-value and interval definitions, the seed and the month rule are fixed here.

**What a result can mean.** A pass says: a rule frozen on 2020-2023 beat the current rule month by month on 2023-2025
by more than month-to-month noise would explain. It does not say the idea was found out of sample (it was not), and it
does not promise the difference will continue. A fail is a complete answer. Nothing here changes the Setups book or the
vault; the forward shadow books `b_trend30` and `b_wait_stop` stay the live test.

### H72 results (22 Nov 2026, run 11:28-11:32 UTC on the research server after the live page showed think15-v5.2.9 at 11:27 UTC; `research/out/h72_trend_filter_oos/report.md`, `choice.json`, `results.json`, `sensitivity.json`, `run.log`)

**Choice (CHOICE period, books run only to 2023-06-08).** Sum of R, eight markets / BTC + ETH: current +25.2 / +46.9;
N=10 -0.9 / +43.6; 15 +19.7 / +62.2; 20 +61.3 / +81.8; 30 +77.9 / +108.3; 45 +15.9 / +61.6; 60 +21.8 / +43.7;
90 -22.2 / +15.5. Qualified: 20 and 30. **Chosen N = 30**, the length already known to win among 20/30/45; none of the
four lengths never computed before (10, 15, 60, 90) came close on CHOICE.

**Verdicts by the registered pass rule (TEST 2023-06-08 to 2025-11-10, 30 months; Holm over m = 3).**
Paired monthly difference against the current rule, BTC + ETH, mean R per month [95% month-clustered interval], one-sided p:
- **A, trend filter N=30: PASS.** +2.65 [+0.37, +5.05], p 0.0114 (Holm 0.034; below 0.05/3 too); 21 of 30 months up.
  Eight markets +0.80 [-2.46, +4.07] (guard >= 0 met by the point estimate only). Holdout (13 months): +0.17
  [-2.14, +2.48], p 0.44: above zero by a hair, i.e. no real difference in the holdout.
- **B, wait after a stop-out: PASS.** +2.29 [+0.34, +4.21], p 0.0116 (Holm 0.034; below 0.05/3 too); 21 of 30 up.
  Eight markets +0.93 [-2.33, +4.11], with the book flat 68% of bars in TEST (other six 82%). Holdout +0.08 [-3.50, +3.44],
  p 0.48: no real difference.
- **C, both: PASS** by the Holm rule (p 0.0177, Holm 0.034) but NOT below the stricter 0.05/3 bar first written.
  +2.63 [+0.17, +5.07]; eight markets +2.11 [-1.72, +5.89]; flat 76%. Holdout -0.16 [-3.32, +3.11]: does not hold.

**Per book (BTC + ETH; trades, mean R per trade [95% interval], sum of R, worst fall of the summed equity).**
TEST: current 778, -0.083 [-0.191, +0.036], -64.8R, -64.5%; A 668, +0.022 [-0.090, +0.137], +14.7R, -58.5%;
B 645, +0.006 [-0.098, +0.112], +4.0R, -45.6%; C 465, +0.031 [-0.098, +0.150], +14.2R, -54.5%.
HOLDOUT: current 305, +0.040 [-0.161, +0.280], +12.3R, -26.9%; A 284, +0.051, +14.5R, -25.9%; B 208, +0.064, +13.3R,
-30.4%; C 182, +0.056, +10.2R, -39.4%. No book's mean R per trade has an interval clear of zero in TEST or HOLDOUT.
Eight markets TEST: current -28.1R, fall -28.3%; A -4.0R, fall -39.8% (deeper); B -0.1R, -19.8%; C +35.3R, -19.1%.
The other six in TEST: A -1.84 R/month against the current rule [-3.83, +0.16] (worse), B -1.36, C -0.52.

**Descriptive only (not used for any choice): every length, BTC + ETH mean monthly difference in TEST.** N=10 +0.86
(p 0.15), 15 +0.23 (0.42), 20 +1.29 (0.16), 30 +2.65 (0.011), 45 +2.77 (0.011), 60 +2.78 (0.003), 90 +2.51 (0.040).
All seven are above the current rule on BTC + ETH in TEST, but on eight markets 10, 15 and 20 days are below it (-1.31,
-3.56, -1.69) and 30-90 above. In the HOLDOUT no length's BTC + ETH difference has an interval clear of zero (10 and
90 days are below zero). On CHOICE only 30 days was clearly above the current rule on BTC + ETH (+1.50, p 0.013).

**Deviations.** None from the registered design. Notes: (1) the choice stage's CHOICE sums differ from the full-run
CHOICE sums (eight markets, N=30: +77.9R vs +86.3R; current +25.2R vs +29.6R) because the choice runs stop at the TEST
start and leave out trades still open there, as registered; the choice would be the same on either set. (2) The run
checked that the engine's own `b_wait_stop` gives the very book the script ran (it did on all eight markets). (3)
pandas printed a future-deprecation warning on concatenation; no effect on numbers.

**Reading.** Both changes, with the filter's length frozen on 2020-2023, beat the current rule on BTC + ETH month by
month in 2023-2025 by more than month-to-month noise would usually give (each p about 0.011, Holm 0.034). Three things
limit this: (a) the ideas, and the direction of these TEST totals, were already seen on all the data (H65, H67, H68), so
this is a significance check on a known difference, not a blind test; (b) in TEST the current rule lost 64.8R on BTC +
ETH, and every filter length and the wait gain mainly by losing less in that stretch; no book's own mean R per trade is
clearly above zero; (c) in the one-year holdout none of the three differs from the current rule (intervals of about
plus or minus 2.5 to 3.5R a month around zero), and on the other six markets the filter was worse in TEST. A pass here
is a reason to keep the forward shadow books `b_trend30` and `b_wait_stop` running, not evidence of an edge. Nothing
reaches the Setups book or the vault without the owner's word.
## H73. One member wallet on the Setups book's BTC and ETH trades at realistic fees, at the member's new size, and on the two shadow rules (registered 22 Nov 2026, about 11:40 UTC, before any H73 code was run or any H73 number was computed)

**Prompted by:** H63 (today) walked ONE member wallet of $10,000 through every BTC and ETH trade of the Setups book
(`b_targets`) since 2020 at three sizes; every size lost on history, larger sizes faster. Two limits on what that says
about the owner's real member account: (1) H63 charged the paper book's fee, 0.10% of the notional per side, about twice
a standard futures taker fee, and fees were a large part of the loss (the 2% wallet paid 14,338 in fees on a 10,000
start); (2) since 11:18 UTC today the member account trades NEW setups at 100% of its balance per coin at 2x leverage with
a 15% daily loss limit (it was on the 2% rule). Also today two rule variants became paper shadow books: `b_trend30` (H67)
and `b_wait_stop` (H68). This is a description of history under stated assumptions, not a forecast and not advice. There
is no pass bar: nothing can pass. No engine code is changed.

**What must be said first.** The two variants were FOUND on this same history (H65, H66; tested as rules in H67, H68). Any
wallet result for them inherits that: it cannot show an advantage, and the report says so each time their numbers are
shown. A history replay is a warm-up, not a forward result. The member's actual fee rate was not available to this study.

**The trades.** BTCUSDT and ETHUSDT trades of three books, each run by the engine's own `shadows.run_challenger` (the
engine's code, no copy) over the replay H63 used (the crypto group prepared by `h59.prep_cut` with the cached fits, to the
last stored session at or before 2026-11-21 13:45 UTC, `h62.group_end`; first decided session as H63):
(a) `b_targets`, the current Setups rule as it runs from think15-v5.2.9 (early entry at the deciding close on BTC and ETH);
(b) `b_trend30` (H67); (c) `b_wait_stop` (H68). H63's reduced copy (`h62.run_setups`) is NOT used: since v5.2.9 it no
longer equals `b_targets` on BTC and ETH. Each book's closed trades and its open trade at the cut (from the book's own end
state: side, entry, initial stop, entry bar, Target 1 and whether it was taken) become setups with `h63.setup_of`; an
entry booked at the last close (held from a bar beyond the cut) is dropped. GATE (must pass or nothing is read, per book
and coin): walked with the paper book's own sizing and its own fee, one coin at a time, funding off, the walk reproduces
that engine book's marked equity at every bar (largest relative gap below 1e-7), as `h63.gate` does, adapted in the H73
script only to take the open trade from `shadows.run`'s end state.

**The wallet.** H63's rules unchanged (`h63.walk`, `h63.member_sizer`, imported, not edited): one wallet of 10,000, both
coins; in a bar funding first, then fills at the open (closes before entries, BTC before ETH), then stops and targets
inside the bar; funding from the stored Binance series (`data/<coin>_funding.csv`) on the open notional at each funding
time; the daily loss brake as H63 modelled it (UTC day, budget = brake% of the day-start wallet less the day's loss less
the other coin's open risk; a new trade is trimmed to fit or not joined; it closes nothing); the wipe-out rule (equity at
each open position's worst price of a bar at or below 0.5% of the open notional ends the run); a setup already open when a
wallet starts is not joined. Sizings:
- **S1 "2% rule":** loses 2% of the wallet at the stop, notional capped at the wallet less the other coin's open notional; brake 5%.
- **S2 "100% per coin":** notional = 1.0 x the wallet at the entry; brake 15%. Read here as the member's setting from
  today (100% of the balance per coin, 2x leverage: the two coins together need the whole wallet as margin). If the
  account instead means a notional of 2x the balance per coin, that is larger than S3 and is not run here.
- **S3 "3x book":** notional = 1.5 x the wallet at the entry; brake 15%.

**Fees, the point of the study:** three levels per side, charged as H63 charges them (fee x quantity x (entry price + exit
price)): **0.10%** (H63's, a reproduction check), **0.05%** (a standard futures taker fee, the PRIMARY level), **0.02%**
(a maker-like lower bound, shown as a bound; market orders do not pay it). Slippage of the member's fill against the
book's prices is not modelled (H64 measured the one-bar delay as zero on average with about 0.8% of noise either way).

**Read-outs, fixed now, for each of 3 books x 3 sizings x 3 fees (27 cells):**
- (a) One 10,000 wallet over the whole replay: final equity, worst fall of the equity, lowest equity (and when), worst UTC
  day (equity at the day's last close against the day before), longest run of losing joined trades, trades joined /
  trimmed / capped / not joined, fees paid, funding paid, the final equity without funding, wiped out or not (also with
  closes only, if it differs).
- (b) The same read-outs for three separate fresh 10,000 wallets: first half (first decided session to 2023-06-07, i.e.
  bars before 2023-06-08 00:00 UTC), second half (2023-06-08 to the cut), holdout (2025-11-11 to the cut).
- (c) H63's month-start table: a fresh 10,000 from every month-start for 365 days: how often +100% came first, how often
  -50% or a wipe-out came first, how often neither (median end equity), unfinished, median days to either, to +100%, to
  -50%; also by half (month-starts before / from 2023-06-08), as H63.
- (d) **The statistical statement, fixed now,** for the PRIMARY cell (book (a), S2, fee 0.05%) and the same cell of (b)
  and (c): from the whole-run wallet of (a), the equity at each calendar month's last close; monthly returns between
  consecutive month-ends, COMPLETE calendar months only (the partial first month from the start and the partial last
  month to the cut are left out); their mean, with a bootstrap 90% interval (resample the months with replacement, the
  same number of months, 10,000 draws, numpy seed 73, the 5th and 95th percentiles of the resampled means); and 10,000
  paths of 12 months drawn with replacement from the same months (seed 73), compounded: the share of paths that end above
  their start, and the share that fall below half their start at any month-end. This treats months as exchangeable
  (independent and alike), which they are not exactly: runs of good and bad months, and the wallet's size changing what a
  fixed-size month would do, are lost. If a wallet is wiped out, its wipe-out month counts as -100% and no month follows.
  The same numbers are written for all 27 cells in `results.json`, descriptive only.
- (e) **Reproduction check:** book (a) at 0.10% against H63's published S1/S2/S3 results (final, worst fall, lowest,
  fees, funding, joined/trimmed/not joined, month-start counts), side by side with the differences. No tolerance bar:
  the v5.2.9 entry at the deciding close instead of the next open moves the figures slightly, and how much is reported.
  Also shown: each book's trade count against H63 (2,076) and the BTC + ETH counts of H67 and H68.

**Not modelled, and said:** the member's actual fee rate, slippage and the vault's join window, refusals, exchange
limits, the vault's rounding, the vault's account-value reading of the daily room (H63's notes on where the model differs
from the vault stand). The forward record (H63's (d)) is not repeated here.

**Changes from the design as handed to me, made before registering:** (1) months for the statistic are complete calendar
months only (the partial first and last months are not months); (2) the bootstrap uses 10,000 draws, seed 73; (3) the
interpretation of "100% at 2x" is written down (S2 = 1.0x notional per coin); (4) the month-start table is also shown by
half, as in H63; (5) an entry booked at the last close (beyond the cut) is dropped rather than walked; (6) the trade
counts are cross-checked against H63, H67 and H68.

### H73 results (22 Nov 2026, 11:28-11:30 UTC on the research server; `research/out/h73_wallet_real_fees/report.md` + `results.json` + `run.log`)

**Gate:** passed for all three books on both coins (the paper-sizing walk reproduced each engine book's marked equity at
every one of 238,079 bars; largest relative gap 6e-15). Replay 2020-02-05 to 2026-11-21 13:45 UTC (run after the live
page showed think15-v5.2.9, generated 11:27 UTC). Trades (closed + open): `b_targets` 2,075, `b_trend30` 1,816,
`b_wait_stop` 1,763; one ETH entry booked at the last close was dropped in `b_targets` and in `b_trend30`.

**Primary cells: 100% per coin (S2), fee 0.05% per side.** `*` = found on this same history: cannot show an advantage.

| Book | Final from 10,000 | Worst fall | Lowest | Worst UTC day | Fees | Funding paid | Final without funding | Month-starts: +100% first / -50% first / neither / unfinished | Fresh wallet: 1st half / 2nd half / holdout |
|---|---|---|---|---|---|---|---|---|---|
| current rule | 6,198 | -94.6% | 2,832 | -19.4% | 26,920 | 14,156 | 12,278 | 21 / 25 / 26 / 9 (halves 17-8, 4-17) | 17,860 / 3,657 / 18,876 |
| 30-day filter * | 245,417 | -74.8% | 8,910 | -19.4% | 197,760 | 66,658 | 555,892 | 37 / 6 / 30 / 8 (halves 28-0, 9-6) | 155,562 / 16,689 / 19,966 |
| wait after stop * | 65,262 | -80.2% | 6,508 | -19.4% | 71,139 | 13,203 | 106,557 | 30 / 5 / 36 / 10 (halves 27-5, 3-0) | 58,860 / 11,516 / 17,086 |

No wallet in any of the 27 cells met the wipe-out rule. The worst day (-19.4%) is beyond the 15% brake: the modelled
brake only trims new entries, it closes nothing.

**Monthly statistic (80 complete months; 10,000 bootstrap draws, seed 73; treats months as exchangeable, which they are
not):** current rule mean month +1.64% (90% interval -2.57% to +6.10%), median month -1.92%, 12-month paths ending above
start 43.6%, falling below half at a month-end 33.9%. `b_trend30` * +5.84% (+1.76% to +10.08%), median +0.27%, 72.6% /
10.0%. `b_wait_stop` * +4.25% (+0.59% to +8.01%), median +1.66%, 66.6% / 11.1%.

**Fee levels, current rule (final from 10,000 at 0.10% / 0.05% / 0.02%; month-starts +100% first vs -50% first):**
S1 2% rule 3,251 / 8,561 / 15,327 (0-4, 1-1, 3-0); S2 100% per coin 861 / 6,198 / 20,287 (16-37, 21-25, 28-13); S3 3x
book 104 / 1,616 / 8,467 (24-54, 32-38, 42-25). Worst falls S1 -86.7 / -74.5 / -65.6%, S2 -98.6 / -94.6 / -90.0%, S3
-99.9 / -99.1 / -97.8%. Second-half fresh wallets lose at every size and fee on the current rule (S2: 1,267 / 3,657 /
6,908).

**Reproduction check (current rule, 0.10%, against H63):** close. Finals S1 3,251 vs 3,208, S2 861 vs 847, S3 104 vs
100; worst falls, worst days and the month-start counts identical; joined within 4, fees 1.5-4.6% higher. Trades 2,075 vs
2,076. The differences are consistent with the v5.2.9 entry at the deciding close (and the one entry at the cut that is
dropped); that attribution was not checked trade by trade.

**Deviations:** none from the registration.

**Reading.** At a standard taker fee the current rule at the member's size still lost on history (10,000 to 6,198) with
a 94.6% worst fall; halving the fee from H63's 0.10% to 0.05% lifts the final about sevenfold but does not turn it
positive, and funding (14,156) cost about as much again; only at the maker-like 0.02% bound does it end above its start,
still with a 90% fall. The second half loses at every size and fee. The two variants end far higher and halve far less
often from a month-start, but both were found on this same history, so these numbers cannot show an advantage; their
second halves are much weaker than their first, and their worst falls are still 75-80% at the member's size. Not
modelled: the member's actual fee rate (not available), slippage, the vault's join window and account-value reading.
## H74. The owner's daily pattern: after a fall below the daily EMA200 with a drop of more than 20%, does the first close back above the daily EMA10 win more than 60% of the time? BTC and ETH (registered 22 Nov 2026, about 11:40 UTC, before any H74 code was run and before any H74 outcome was computed)

**Prompted by:** the owner, 22 Nov 2026 (their words): "within 30 days after price drop below daily ema200 and the price
drop movement bigger than 20%. Then when price rally back and rise above ema10 has higher probability than 60% of winning
rate. Asset class btc and eth. Check is this statiscally correct". Research only: nothing in the engine, the books or the
vault changes, whatever the result.

**Known before registering (no outcome numbers).** The stored 15-minute bars (`data/btcusdt_15m.csv`, `data/ethusdt_15m.csv`
on the server) start 2019-01-01. BTCUSDT and ETHUSDT list on Binance spot in August 2017. Nothing about how often the
pattern occurs, or how it turned out, has been looked at.

**Data.** Daily UTC candles for BTCUSDT and ETHUSDT fetched from the engine's own public klines host
(`https://data-api.binance.vision/api/v3/klines`, interval `1d`, paged by `startTime`, limit 1000, a generic client),
from the listing day to the last complete UTC day (21 Nov 2026), into a scratch folder on the research server. Check: the
fetched daily closes are compared with daily closes built from the stored 15-minute bars (UTC days with all 96 bars) on
every overlapping day; the largest absolute and relative difference is reported. If the fetch fails, daily bars from the
stored 15-minute bars only (2019 onward) are used and this is said. Closes only, except the "largest fall" read-out (daily lows).

**Indicators.** EMA200 and EMA10 on daily closes, alpha = 2/(N+1), seeded with the simple average of the first N closes,
defined from the N-th close onward (no value before).

**Breakdown day B.** A daily close below the EMA200 when the previous close was at or above it (both EMA200 values defined).
Breakdowns are walked in time order; a breakdown is COUNTED only if it is more than 30 days after the previous counted
breakdown (so windows never overlap). The chain of counted breakdowns is the same for every reading.
**The window:** the 30 calendar days B+1 to B+30.

**"Drop bigger than 20%", two readings.** For a day d in [B, B+30], with L(d) = the lowest daily close from B to d:
- **D1 (PRIMARY):** L(d) <= 0.80 x P, where P = the highest daily close of the 60 days B-60 to B-1 (the fall from the recent peak).
- **D2:** some day k in [B, d] has close(k) <= 0.80 x EMA200(k) (a close at least 20% below its own day's EMA200).
The drop day d* is the first d in [B, B+30] where the condition holds. No d* in the window: no event.

**Entry.** The first day t in [max(B+1, d*), B+30] with close(t) > EMA10(t) and close(t-1) <= EMA10(t-1). Long at close(t).
One entry per counted breakdown. Price is NOT required to be below the EMA200 at entry (the claim does not ask it).
No such t: "window closed with no entry" (reported descriptively).

**"Winning", three readings** (all on closes; result = exit/entry - 1):
- **W1 (PRIMARY):** close(t+10) > close(t). **W2:** close(t+5) > close(t).
- **W3:** hold until the first day u > t with close(u) < EMA10(u); exit at close(u); win if the result minus a fee of
  0.05% per side (0.10% in all) is > 0. Days held = u - t. A trade not exited by the last complete day is left out of W3
  counts and listed as open.
- W1 and W2 also reported after the same 0.10% fee (descriptive; the tests use the no-fee W1/W2 above, as the claim does).
- An event whose horizon passes the last complete day is left out of that reading and listed.
**Readings:** 2 x 3 = 6 (D1W1, D1W2, D1W3, D2W1, D2W2, D2W3). The claim's primary reading is **D1W1**.

**Samples.** BTC alone, ETH alone, pooled. **Clusters (pooled):** events sorted by entry day; any two events (either coin)
whose entry days are within 10 calendar days of each other are in the same cluster (single linkage). The number of clusters
is the number of independent episodes reported. Per-coin events are treated as independent (their windows never overlap).

**The test, per reading and sample.**
- Wins / events, win rate, 95% Wilson interval, exact one-sided binomial p against "true win rate <= 60%".
- **Pooled:** because events in one cluster are not independent, the pooled Wilson interval and binomial p are computed on
  ONE event per cluster, the one with the earliest entry day (BTC first on a tie), a choice that does not look at outcomes.
  Also reported: the pooled win rate on all events with a 95% cluster-bootstrap percentile interval (clusters resampled,
  10,000 replicates, seed 20261122).
- **Baseline (the same trade at other times):** every day with an EMA10 up-cross (close(t) > EMA10(t), close(t-1) <=
  EMA10(t-1)), EMA200 defined, outcome horizon inside the data, EXCLUDING any cross that lies inside a qualifying window of
  that D reading on or after its drop day d* (so neither the event entries nor later crosses "preceded by such a drop" are in
  it). Same win definition. **Difference** = event win rate - baseline win rate, 95% bootstrap percentile interval: events
  resampled (individually per coin, by cluster pooled), baseline crosses resampled in calendar-month blocks (both coins'
  crosses of a month together when pooled), 10,000 replicates, seed 20261122. For the pooled difference the event side uses
  all events (cluster bootstrap).
- **Drift baseline (descriptive, W1/W2):** the share of all days (EMA200 defined, horizon inside the data) on which close(t+N)
  > close(t), N = 10 or 5.
- **Multiplicity:** 6 readings. Holm correction across the 6 readings, done separately within BTC, ETH and pooled. The answer
  to the owner is the POOLED verdict of D1W1; the other 17 cells are reported with the same rule.
- **Conclusion words, fixed now:**
  - **"supported"**: Holm-adjusted one-sided p against 60% < 0.05 AND the difference with the cross baseline > 0 with its 95%
    interval excluding zero;
  - **"not supported"**: the upper end of the 95% Wilson interval (pooled: one event per cluster) < 60%;
  - otherwise **"too few cases to tell"**, with the number of independent cases needed to tell a true 60% from 50% at 80%
    power (one-sided alpha 0.05, and alpha 0.05/6 for the Holm worst case) by the normal approximation:
    n = ((z_a x sqrt(0.5 x 0.5) + z_b x sqrt(0.6 x 0.4)) / 0.10)^2, z_b = 0.842.
  - Plain wording to the owner: "the data support the claim" / "the data do not support the claim" / "too few cases to tell".
    A sample win rate above 60% is not "above 60%" unless the rule above says so. "Proven" is never used.

**Descriptive read-outs (pass nothing).** Every event: coin, B, peak P and drop size (D1: 1 - L/P at entry; D2: deepest close
below its EMA200), d*, entry day, entry close, results under W1, W2, W3 (with and without fee), days held under W3, the largest
fall below the entry from t+1 to the W3 exit (daily lows). Average and median result per win definition, the worst case.
Results for the first and second half of events (by entry order; first half = the first ceil(n/2)) and for entries in
2017-2019 against 2020 onward. Windows that closed with no entry (drop met, no cross): count, and the change from close(B)
and from close(d*) to close(B+30).

**Addition, descriptive only (the 15-minute engine's version).** The same 6 readings with "rise above EMA10" replaced by:
the first 4-hour close above the 4-hour EMA10 (previous 4-hour close at or below it), 4-hour bars built from the stored
15-minute bars (2019 onward; EMA10 seeded the same way), among 4-hour bars closing after the close of day max(B, d*) - so
from 00:00 UTC of day max(B+1, d*+1) at the earliest -  and closing by the end of day B+30. Breakdowns and drops stay on the
daily chart. W1/W2: the close of the 4-hour bar 10 / 5 days (60 / 30 bars) later above the entry close; W3: hold to the first
4-hour close below the 4-hour EMA10, fee as above. Baseline: all 4-hour EMA10 up-crosses outside the qualifying windows (same
exclusion). Reported with the same columns, Wilson intervals and p-values, but marked descriptive: no conclusion word.

**Changes from the brief made before registering:** (1) D2 reads "some close from B to d at least 20% below its own day's
EMA200" (the brief's "that lowest close ... below the EMA200 of its own day" mixes the lowest close with its day; the deepest
close relative to its EMA200 is the reading that matches "20% below the EMA200"). (2) The pooled interval and p use one event
per cluster (an exact test needs independent cases; a bootstrap p with few clusters is unreliable); the cluster bootstrap is
reported beside it. (3) The "supported" rule uses the cross baseline (the same trade at other times); the all-days drift is
descriptive. (4) Clustering links any two events within 10 days, of either coin (conservative). (5) The counted-breakdown chain
is shared by all readings. (6) The 4-hour entry may not come before the close of day d*.
**Computed** by `research/h74_ema200_drop_ema10.py` on the research server in `/data/mind15_h74`; output
`research/out/h74_ema200_drop_ema10/` (results.json, report.md, events.csv, the fetched daily candles).

### H74 results (22 Nov 2026, run 11:27 UTC on the research server, 13 s; `research/out/h74_ema200_drop_ema10/report.md`, `results.json`, `events.csv`, fetched daily candles)

**Data.** Daily candles fetched for both coins, 2017-08-17 to 2026-11-21 (3,384 days each, no missing day). On the 2,861
overlapping days with all 96 stored 15-minute bars, the fetched daily close equals the close built from the stored bars
exactly (largest difference 0.0). 49 BTC and 35 ETH breakdowns below the EMA200; 25 and 19 counted (30-day spacing).

**Answer under the primary reading (D1W1, pooled): the data do not support the claim.** 28 entries (14 BTC, 14 ETH) in 22
independent episodes; 10 won (35.7%); one event per episode 8/22, 95% interval 19.7%-57.0% (cluster bootstrap on all events
17.9%-53.8%); the upper end is below 60%. The same trade at every other EMA10 cross won 51.4% (479 crosses); the difference
-15.6% [-34.7%, +4.2%]. All days: the close 10 days later was higher on 52.5%.

| reading | BTC (wins/events) | ETH | pooled events / episodes | pooled win rate [95%, 1 per episode] | p vs 60% (Holm) | cross baseline | verdict BTC / ETH / pooled |
|---|---|---|---|---|---|---|---|
| D1W1 (primary) | 4/14 | 6/14 | 28 / 22 | 35.7% [19.7, 57.0] | 0.993 (1.000) | 51.4% | not supported / too few / **not supported** |
| D1W2 | 6/14 | 7/14 | 28 / 22 | 46.4% [26.9, 65.3] | 0.945 (1.000) | 48.4% | too few / too few / too few |
| D1W3 | 3/14 | 5/14 | 28 / 22 | 28.6% [16.4, 52.7] | 0.998 (1.000) | 27.1% | not supported / too few / not supported |
| D2W1 | 1/2 | 5/5 | 7 / 6 | 85.7% [43.6, 97.0] | 0.233 (1.000) | 49.6% | too few / too few / too few |
| D2W2 | 1/2 | 2/5 | 7 / 6 | 42.9% [18.8, 81.2] | 0.821 (1.000) | 48.0% | too few (all) |
| D2W3 | 0/2 | 2/5 | 7 / 6 | 28.6% [9.7, 70.0] | 0.959 (1.000) | 26.4% | too few (all) |

No reading is "supported" (smallest Holm p 0.467, ETH D2W1). **Result per trade (D1, 28 trades):** W1 average -3.8%, median
-5.2%, worst -30.1% (ETH, May 2022), best +48.3% (ETH, April 2018); W3 after fees average +1.9%, median -2.8%, worst -11.6%,
won 28.6% (a few large winners, many small losers). 2017-2019 vs 2020 onward, W1 average -1.5% vs -4.9%. D2 (7 trades): W1
average +10.4%, median +4.9%, worst -4.6%; too few to mean anything. Windows with the drop met and no EMA10 cross: D1 5 (3
complete: -11%, -25%, -37% from B to B+30), D2 8; two are open now (BTC from 2026-11-05, ETH from 2026-10-29).
**Cases:** about 153 independent episodes would be needed to tell a true 60% from 50% (80% power, alpha 0.05), 259 at the
Holm worst case; the data hold 22 (D1) and 6 (D2).

**4-hour version (descriptive only).** D1 pooled: W1 13/25 (52.0%, cross baseline 53.2%), W2 17/25 (68.0%, interval
43.3%-81.9%, baseline 50.9%), W3 7/27 (25.9%); average W1 +0.3%, W2 +0.2% (worst -32.7%), W3 -0.2% after fees. D2 pooled:
W1 6/8, W2 6/8, W3 2/9. Nothing here is evidence either way.

**Deviations and notes.** (1) The registration's time reads "about 11:40 UTC"; the commit was at 11:25 UTC, before the first
run (11:27, which crashed on a date-parsing error before any outcome was computed; fixed and rerun). (2) The baseline
exclusion was applied to the windows of ALL breakdowns with the drop met (counted or not), the reading of "crosses not
preceded by such a drop"; the registration's text did not say counted or not. (3) 4-hour bars with fewer than 16 stored
15-minute bars were dropped and 4-hour entries need 3 days of 4-hour EMA history; not in the registration. (4) With 2
events (BTC D2) the bootstrap difference intervals are degenerate; the verdict there rests on the Wilson interval.
## Forward yardstick p8_mom: the Phase 6 books' momentum fallback rule alone (registered 22 Nov 2026, about 11:00 UTC, before any p8_mom code existed or any p8_mom number was computed). A YARDSTICK, NOT A HYPOTHESIS

**Prompted by:** the owner, 22 Nov 2026: "Run all above" (task 4 of the RL audit of 21 Nov 2026: "Add a momentum-only
paper book as the plain yardstick for the Phase 6 books").

**What it is for.** Since the refit of 16 Nov every BTC seed of both Phase 6 books (`p6_mtrend`, `p6_p4trend`) is on its
'do no harm' fallback, the daily 30-day momentum rule, so most of their BTC result is that rule's, not an agent's. This
book trades ONLY that fallback rule, with the same code, fees and decision times, so that the momentum rule's result is
never credited to an agent: a Phase 6 book is read beside it over the same days. It is not a hypothesis: it has no pass
rule, it is never called passed or failed, and nothing about it is graded. It has no proven advantage.

**The rule (the very same functions, called, not copied).** `engine15/playbook8.py`, book id `p8_mom`, BTC and ETH,
$10,000 each, from **2026-11-23 00:00 UTC** (`REGISTERED`); it starts flat and its first decision is at the first 15m
close after that. Each step calls `engine15/rl/forward5.advance` with `fallback="trend"` and one stand-in "model" (no
weights, no training) whose every seed (0, 1, 2) carries the 'do no harm' flag on both coins. So every decision goes
through `forward5.model_w` -> `forward5.trend_w`: W = -10 x |a - ref|, ref = features3's `mom_signal` =
`rl.benchmarks.momentum(close, 30, True)`: the sign of the trailing 30-day (2,880-bar) log return, decided once a day at
the close of the bar ending 00:00 UTC, long (+1) or short (-1), held until the next 00:00 UTC decision. Then exactly as
the Phase 6 books: `qagent.q_from_w` (the round-trip cost band), `policy3.decide` (minimum hold 4 bars), each seed through
the Phase 3 risk manager (`forward5.risk_and_book`: 60%-a-year vol target, the drawdown brake), the book holds the mean of
the three seeds (identical here), decided at a 15m close and filled at the next open, 0.10% a side, half spread 0.5 bp,
volatility slippage, perp funding both sides; spot buy-and-hold beside it. Decision times: every 15m close that the
evidence store's readings cover, the same closes the Phase 6 books decide (`advance` decides no bar the readings do not
cover). The configuration is the Phase 6 books' (`forward6.load_cfg()`). Record: `research/out/rl/forward8/
decisions_p8_mom_<asset>.jsonl` (append-only, its own state). A trade = one run of same-sign exposure, as the RL books.

**Known differences, stated now.** It starts later than the Phase 6 books (13 Nov 03:00 UTC), so it is compared with them
over the same days only: a Phase 6 book's return from its equity marked at 2026-11-23 00:00 UTC to the end of the window,
against this book's return over the same window (both net of costs; buy-and-hold over that window beside them). Its risk
manager starts fresh at its start; a Phase 6 seed carries its own policy state and drawdown brake from before, so even
when every Phase 6 seed is on the fallback the two books need not hold exactly the same size. If the book goes live after
2026-11-23 00:00 UTC, the closes in between are decided at its first live step from closed bars only (no fitted part, so
the same decisions a live step would have taken); they count in `late_decisions`.

**Shown:** on the scoreboard (strategy row `p8_mom`), in `playbook8`'s page block like the other strategy books, and in
the page's `rl_lab` block beside the Phase 6 books.

## Interim read of the RL forward books at 8 weeks: time-based, NOT a verdict (registered 22 Nov 2026, about 11:00 UTC, before any interim-read code existed or any interim number was computed)

**Prompted by:** the owner, 22 Nov 2026: "Run all above" (task 7 of the RL audit of 21 Nov 2026: "Register an interim,
time-based read (for example at 8 weeks), since 30 trades per coin is far off").

**When.** 8 weeks (56 days) after each book's own start, all UTC:

| Book | Start (go-live) | Interim read date (window end) |
|---|---|---|
| `p5_rlq` (Phase 4 primary) | 2026-11-12 04:30 | **2027-01-07 04:30** |
| `p6_mtrend` (Phase 6 primary) | 2026-11-13 03:00 | **2027-01-08 03:00** |
| `p6_p4trend` (Phase 6 control) | 2026-11-13 03:00 | **2027-01-08 03:00** |

`research/rl_interim_read.py` refuses to print any comparison for a book before its read date, and on or after it prints
the read-outs below for the window start -> read date only (closes at or before the read date; later bars never enter,
so a later run gives the same numbers). It reads the books' own records (`research/out/rl/forward5`, `forward6`,
`forward8`) and the engine's bar and funding files, read only, and rebuilds each book with `forward5.risk_and_book`.

**Read-outs, per book and coin (BTC, ETH), net of all costs:**
1. The book's return over its window against spot buy-and-hold over the same days (both from $10,000; as on the page).
2. For `p6_mtrend` and `p6_p4trend` also: against the momentum yardstick `p8_mom` over the SAME days only. The yardstick
   starts 2026-11-23 00:00 UTC, later than the RL books, so this comparison runs from 2026-11-23 00:00 UTC to the read
   date (2027-01-08 03:00 UTC): the Phase 6 book's return from its equity marked at 2026-11-23 00:00 UTC, the yardstick's
   return from its $10,000, and buy-and-hold over that window beside them.
3. The book's gross result over its window split into the agent-decided part and the fallback-decided part, with the
   costs (which are the whole book's and are not split), by `forward5.agent_split` (agent + fallback - costs = net), and
   the share of seed-bars on a model.
4. Closed trades per coin, against the 30 the verdict needs.

**The only words allowed for the outcome.** Each line says "interim" and, per comparison, exactly one of "ahead of",
"behind" or "level with" the yardstick (buy-and-hold, or the momentum yardstick), with both returns and the difference in
percentage points. "Level with" = the two returns differ by less than 1.0 percentage point; otherwise "ahead of" or
"behind". Template: `Interim read (8 weeks; not a verdict): <book> <coin> <+x.xx%> vs <yardstick> <+y.yy%> over <start>
to <end> UTC: <ahead of | behind | level with> <yardstick> by <d.dd> points.` No other verdict word (passed, failed,
works, beats, proven, significant, edge) is used.

**It changes no decision.** The 30-closed-trades-per-coin rule still decides every RL book's verdict. The interim read
does not stop, start, resize or relabel any book, does not change a model, a refit, a fallback flag or a pass rule, and
every RL book stays labelled NOT passed whatever it shows.

**What is NOT concluded from it.** Not that any agent has or lacks skill (8 weeks are a handful of trades per coin; no
range or significance is computed); not that a fallback-decided result is the agent's; not that a book is ahead in
history or will be ahead later; nothing pooled across coins or books as a single claim; no comparison outside the stated
windows; and nothing about the momentum rule itself beyond these same days.
## H80-H89, common part. QUEUE FAMILY: placebo, permutation and bootstrap tests of the Setups book and its two variants (registered 22 Nov 2026, about 12:00 UTC, before any H80-H89 number was computed; code `research/queue/placebo.py`, tests `tests/test_queue_placebo.py`)

**Prompted by:** the owner, 22 Nov 2026: "Queue at least 20 studies for SG box so it will have always have min 72 hours
queue tasks backlog to clear"; this family is the placebo half of that queue (another family holds walk-forward rule
variants and chart-pattern claims). The owner keeps asking for "statistically proven". What statistics can say first is
whether each PART of the Setups rule does anything at all, against the same rule with that part scrambled. Research
only: nothing in the engine, the books or the vault changes, whatever any study says.

**Known before registering (H65, H67, H68, to 2026-11-21, holdout included):** the Setups book (`b_targets`) is flat
per trade (+0.004R over 5,963 trades); its results line up with each market's own 30-day move; the lead in the odds did
not hold up across halves; the 30-day filter (H67) and the wait after a stop-out (H68) looked better on the very history
they were found on. No placebo of any of these has been computed. The smoke and timing runs for this registration
(server, 22 Nov 2026, 11:39-11:55 UTC) ran on a tiny slice (SPX, 2021-01 to 2022-12, labelled SMOKE) or printed seconds and
memory only. The smoke outputs were read only to test the code; one of them (H81) showed a flaw in the first design,
which was changed before this registration (see H81). None of their numbers is a result or will be reported.

**Common to every study of the family (H80 to H89):**

- **The book.** `b_targets` as the engine runs it from think15-v5.2.9 (rule `{"targets": True, "early": True}`), the
  30-day filter `b_trend30` and the wait `b_wait_stop`, each run by the engine's own `shadows.run` (asset fee, leverage
  cap, fill delay and early entry from `shadows.asset_cfg`), eight markets, cached fits and the evidence store read only.
  Every run checks that the real book it computed is the engine's own challenger (`run_challenger("b_targets")`, and
  `"b_trend30"` for H83), trade for trade; a failed check stops the run.
- **THE HOLDOUT IS NOT TOUCHED.** Every market group ends at its last stored session at or before **2025-11-10 23:45
  UTC**, set in one place (`CUT` in the script) and checked again on what was loaded. Nothing from 2025-11-11 onward is
  read.
- **Halves** split at 2023-06-08 by entry bar. Every read-out is given for all eight markets ("pooled"), BTC+ETH
  ("vault") and the other six ("others"), each for the whole window and both halves, plus per market (descriptive).
- **R** is the book's own `r_mult` (net of fees, over the risk at the entry stop), except in H81 and H82, where real and
  placebo trades alike are scored by the exits machinery alone (see H81); "mean R" is the pooled sum of R over the
  pooled number of closed trades.
- **Placebo p-value** (H80-H86): p = (1 + number of draws at least as good as the real book) / (1 + number of draws).
  "At least as good" = the draw's statistic is greater than or equal to the real one. A draw with no closed trade in a
  cell has no mean R and is never counted as at least as good. The lower-tail share (draws at most as good, same
  correction) is reported beside it, so a part that HURTS the book is seen too.
- **Primary statistic** (one per placebo study): the pooled mean R per trade over the whole window. Secondary, reported
  with their own p-values and NOT used for the conclusion: the sum of R and the mean R for pooled / vault / others in
  each half, and per market.
- **Conclusion wording, fixed now** (H80-H86): "the real book IS distinguishable from its placebo at p = x" when the
  primary p <= 0.05, else "the real book is NOT distinguishable from its placebo at p = x". Never "proven". A
  distinguishable result says that the scrambled part carries something on this history; it is not a forward result,
  and for H83 and H84 the rule under test was found on a history that contains this whole window.
- **Draws.** Fixed seeds: study seed 20261122xx (xx = the study number, e.g. 2026112280); draw k uses
  `numpy.random.default_rng([seed, k])` for anything common to all markets and `[seed, k, market index]` (or
  `[seed, k, 100 + group index]`) for anything per market or group, so draw k is reproducible on its own. Draw counts
  were set from timing runs on the research server so each heavy study takes roughly 8 to 16 hours of one processor.
- **Job contract.** `research/queue/placebo.py --study H8x --fits-dir <fits_today> --out <folder>`; resumable (finished
  draws are written as one line per batch, at least once a minute; a torn last line is dropped; draws written by another
  version of the script, seed or draw count are never counted, so an edited script starts afresh), `progress.json`, and
  on success `results.json`, `report.md` (conclusion first) and an empty `DONE`. `--estimate` prints the CPU hours;
  `--smoke` runs a few draws on SPX to the end of 2022 in seconds, into `<out>/smoke`.

## H80. Odds placebo: do the engine's odds matter to the Setups book? (registered 22 Nov 2026 with the family, before any H80 number was computed)

**Scrambled:** each market's odds (P(up first), P(flat), P(down first)) over its window are replaced by the same odds
shifted circularly in TIME: row t takes the odds in force at t - delta, wrapped round the window, delta = 30 days + u x
(window - 60 days - 7 days), u uniform on [0, 1) and COMMON to all eight markets in a draw (so the odds of BTC and ETH
stay as related to each other as they are, and the dependence between the markets' books is kept). Every row's source
is at least 30 days away both ways round the circle (the 7-day margin covers closed hours and weekends). The odds keep
their own behaviour (levels, persistence, their share of strong leads) and lose their link to the price at that moment.
Everything else is real: prices, the higher-timeframe bias, the tide, the shock flag, the release guard, the stop unit,
the targets. Note: the forced entry after four flat sessions goes with the bias, else the tide, so the odds act through
ENTER and FLIP decisions and the side of a forced entry when there is neither bias nor tide.
**Real:** `b_targets`. **Draws:** 10,000. **Conclusions:** "the Setups book IS / is NOT distinguishable from the same
book run on time-shifted odds at p = x". If it is not, the odds add nothing measurable to this book's mean R on this
history.

## H81. Side placebo: does the book pick the right side, given when it trades? (registered 22 Nov 2026 with the family, before any H81 number was computed)

**Scrambled:** the sides of the real book's closed trades are permuted within each market and calendar month (entry
month), so each market-month keeps exactly its number of longs and shorts. Every trade keeps its entry bar and entry
price and is scored under **the exits machinery alone**: the stop at 2 units from the entry (`stop_units` x `unit` of
the bar before the entry, as the book sets it), Target 1 and Target 2 from `live.plan_targets` at the decision row for
the trade's side, half off at Target 1 with the stop moved to the entry, in the engine's order inside a bar; else out
at the close of the last bar opening before entry + 30 days. R does not depend on size, so each trade is scored alone.
The REAL statistic is the same machinery on the real sides (the book's own R, which also has flips and steps aside, is
shown beside it).
**Changed from the brief, and why:** the brief kept "the real book's exits". A first version ended each placebo trade
at the real trade's last bar; a smoke run showed why that is wrong. A real stop-out is a move of at least 1R in the
OTHER side's favour, so a flipped trade closed at that bar is closed at a good moment chosen by the real trade's loss,
which flatters the flip. The machinery ends a trade only by what happens to that trade itself.
**Done** by the trade replay `replay_trade` / `machine_r` in the script. **Gates (checked in the run, every market):**
replayed with its own side AND the real trade's own window, every real trade gives its own R (to 1e-9), its own kind of
exit and its own exit bar (this ties the replay to the book); any mismatch stops the run. Tests: where a real trade
ended at its own stop or Target 2 within 30 days, the machinery gives its R exactly; on random-walk bars with
uninformative odds, flipping a side has no built-in advantage (mean difference within noise).
Each trade has only two possible sides, so both outcomes are computed once and a draw is a permutation: this study is
light by nature: **draws 100,000** (about 0.1 hour; more draws would buy only resolution). The number of trades is
fixed, so the mean R and the sum of R give the same p-value. **Conclusions:** "the book's choice of side IS / is NOT
distinguishable from a random side with the same monthly long/short share at p = x".

## H82. Entry-time placebo: what does the exit machinery earn by itself? (registered 22 Nov 2026 with the family, before any H82 number was computed)

**Scrambled:** each real closed trade is moved to a bar drawn uniformly from the bars of the same market and calendar
month (bars with a stop unit; with replacement, so placebo trades may overlap: it is a trade-level test, not a book).
It keeps its side. The entry is at the close of the bar before (BTC, ETH: the early entry) or at the bar's open (the
others); it is scored under the exits machinery alone, exactly as in H81 (same code, same gate, 30-day cap).
**Real:** the real trades (real bars and sides) under the same machinery, the book's own R beside it. **Draws:**
100,000. **Conclusions:** "the book's entry timing IS / is NOT distinguishable from random entry bars in the same month
with the same sides and exits at p = x". If not, what the book's entries earn is what its exits earn at any bar of the
month.

## H83. Trend-filter placebo (for H67): does the filter help because of WHICH entries it blocks? (registered 22 Nov 2026 with the family, before any H83 number was computed)

**Changed from the brief:** the brief asked for "a random filter that blocks the same share of entries per month".
A filter drawn afresh at each close would block a forced entry once and let it through at the next close, so it would
block far fewer entries than the real filter (which keeps blocking while the 30-day move stays against the side), and
matching the share of blocked DECISIONS per month would not match the share of blocked ENTRIES. **Scrambled instead:**
the 30-day move series itself (`shadows.trend_move`, 30 days, as the engine computes it) is shifted circularly in time
as in H80, with at least 60 days (two whole lookbacks) between a row and its source, u common to all markets. The
placebo filter then blocks entries as often, in spells as long, and with the same tilt towards blocking shorts as the
real one (most markets rose), but at the wrong moments. Passed to the engine's own `shadows.run` as `aux["trend_move"]`
under the `b_trend30` rule (no copy of the loop). The placebo books' trade counts and share of flat bars are reported
beside the real filter book's, so it is seen that both trade about as little.
**Real:** `b_trend30` (with the real move; gate: equal to the engine's challenger). **Draws:** 10,000.
**Conclusions:** "the 30-day filter book IS / is NOT distinguishable from the same book with a time-shifted filter at
p = x". If not, its better mean R on history is what any filter of that shape and tilt gives (trading less, leaning
long), not its timing. The filter was found on this history: a distinguishable result is still not a forward result.

## H84. Wait-after-stop placebo (for H68): does it matter that the wait follows a STOP? (registered 22 Nov 2026 with the family, before any H84 number was computed)

**Changed from the brief:** the brief asked for "waits of the same lengths placed after random exits". The real wait
has no length of its own: it lasts until a signal clears the entry bar. **Scrambled instead:** the TRIGGER. Exactly
the H68 rule (no forced entry until `policy.decide` returns ENTER), but switched on after each exit that leaves the book
flat (any exit but a flip) with probability p, independently, instead of after exactly the exits at the entry stop;
p for a market is the share of such exits that ended at "STOP" in that market's real `b_wait_stop` book over the window
(so the placebo switches the wait on about as often). The waits then end the same way (at a signal), so their lengths
come from the same mechanism. Reported beside: the real and placebo books' trade counts, share of flat bars, stop-outs
followed by a wait ("episodes") and sessions withheld.
**Done** by a research-side copy of the Setups loop (`run_setups_copy`, the `b_targets` path of `shadows.run` with one
hook: which exit switches the wait on). **Gate (checked in the run, every market, before any draw):** with no wait the
copy gives `b_targets`, and with the hook "the exit word is STOP" it gives `b_wait_stop` (and the same wait counters),
trade for trade and bar for bar, against the engine's own `shadows.run`; any mismatch stops the run.
**Real:** `b_wait_stop`. **Draws:** 11,000. **Conclusions:** "the wait-after-stop book IS / is NOT distinguishable from
the same wait switched on after random exits at p = x". If not, what the wait does on history comes from waiting for a
signal at all (and, on gold, silver and SPX, from hardly trading), not from what follows a stop-out.

## H85. Higher-timeframe placebo: do the bias and the trend tiebreak matter to the book? (registered 22 Nov 2026 with the family, before any H85 number was computed)

**Scrambled:** the higher-timeframe bias (`htf_bias`) and the tide (the 4h/daily trend used as the tiebreak) shifted
TOGETHER in time as in H80 (at least 30 days, u common to all markets; the two keep their relation to each other and
lose their link to the moment). Odds, prices and everything else real. The bias decides the side of forced entries (most
entries), raises the bar against it, and forces a flip when a position fights it without an edge, so this tests most of
what decides the side. **Real:** `b_targets`. **Draws:** 13,000. **Conclusions:** "the Setups book IS / is NOT
distinguishable from the same book run on time-shifted bias and tide at p = x".

## H86. Stop-size placebo: does volatility-scaled stop sizing matter? (registered 22 Nov 2026 with the family, before any H86 number was computed)

**Scrambled:** the stop unit (`unit` = 1.5 x ATR of the 1-hour chart, which sets the stop at 2 units and through it the
size of R, the targets' fallback distances and Target 1's eligibility band) shuffled across bars within each calendar
month, one permutation per market group and draw (BTC and ETH share their bars' clock, so they share it): each month
keeps its own stop sizes (their typical size and spread), but a stop no longer fits the volatility of its moment.
Entries, sides and the odds are real; only the stop and what follows from it change.
**Real:** `b_targets`. **Draws:** 10,000. **Conclusions:** "the Setups book IS / is NOT distinguishable from the same
book with stops of the month's typical sizes at random at p = x". Read with care either way: R is measured against the
stop, so a different stop changes the unit in which the result is counted; the sum of R and the per-half cells are
shown beside the primary.

## H87. Block bootstrap of the real books: what can a year look like? (registered 22 Nov 2026 with the family, before any H87 number was computed)

**Done:** the per-month sums of R (entry month) of each market under the current rule, `b_trend30` and `b_wait_stop`
(each the engine's own run), months kept together across markets (so their dependence is kept). A 12-month path is four
blocks of three consecutive months drawn with replacement from the window (circular moving blocks, so a month's
neighbours come along); **20,000 paths** per book and slice; seed 2026112287. Sensitivity: one-month blocks. Read-outs
for pooled / vault / others, whole window and each half: quantiles (5, 25, 50, 75, 95%) of the 12-month sum of R, of the
worst fall inside the year (largest drop of the cumulative R from its running peak, month resolution, in R), and the
chance of a losing 12 months (sum of R below 0). No p-value; a description of history as if the future were like it.
The two variants were found on this history, so their figures are flattered. Light (under 0.1 hour).

## H88. Costs surface: where does the Setups book break even? (registered 22 Nov 2026 with the family, before any H88 number was computed)

**Done:** every closed trade of the three books (one engine run each), with its fee replaced by f a side for all
markets alike, f in {0.02, 0.05, 0.10, 0.15}%, crossed with an entry slip s in {0, 0.02, 0.05, 0.10}% of the entry
price against the trade (16 cells). Both are exact on the book's own trades: fees enter R linearly and change nothing
else in the path (R does not depend on size, and no rule reads equity), so R(f) = R before fees - (f / the market's fee)
x the trade's fees in R; a member's slipped fill keeps the setup's stop and targets (as the vault places them) and costs
s x entry price / stop distance in R. (The slip's own tiny extra fee is left out.) **Gate (in the run, every market):**
the post-hoc fee at 0.15% equals a replay with `cost_side` 0.0015, trade for trade, to 1e-9 R. Read-outs per cell: mean R
and sum of R for pooled / vault / others, both halves, and a month-clustered 95% interval of the mean (calendar months
resampled, 5,000 replicates, seed 2026112288); the break-even fee at no slip and the break-even slip at each fee (mean R
is linear in both, so these are exact). Light (under 0.1 hour).

## H89. Year by year: is the result one or two years? (registered 22 Nov 2026 with the family, before any H89 number was computed)

**Done:** the three books' closed trades (one engine run each), mean R per trade with a month-clustered 95% interval
(10,000 replicates, seed 2026112289) for each calendar year alone (2020 to 2025; 2025 ends at the cut) and for the
window with each year left out, pooled / vault / others. **Fixed now:** a result "rests on one year" when leaving out
that one year turns the sign of the whole window's mean R; "on two years" when two different years each do so; else
"no single year turns it". Descriptive, no bar. Light (under 0.1 hour).

### Ledger of the family H80-H89 (the end of the registration)

- **Tests that can come out "distinguishable":** 7 primary placebo p-values (H80 to H86). If none of the parts did
  anything and the seven were independent, the chance that at least one would show p <= 0.05 is about 30%; one of the
  seven looking significant by chance would be unremarkable. They are not independent (the same trades and markets run
  through all of them).
- **Secondary p-values:** each placebo study also reports 17 secondary cells (two statistics in three slices and three
  periods, minus the primary) and 8 per-market ones, about 175 in all. At the 5% level some 9 of them will look
  significant by chance; none of them decides a conclusion.
- **Intervals:** H88 and H89 report about 260 month-clustered intervals (16 cost cells in three slices for three books;
  the whole window and six years alone and left out, in three slices for three books); some will exclude zero by
  chance. H87 gives no p-value.
- **So:** one or two "significant" results in this family are expected by chance. A single p near 0.05 is not news; a
  primary p well below 0.01 that agrees across halves and market groups would be worth a forward test, and only that.
  Nothing here can make a rule "proven": these are placebo comparisons on history, the variants were found on it, and
  the holdout (2025-11-11 onward) is kept for later.

**Queue commands** (run with the working directory at a code snapshot that has `engine15/`, `research/` and a `data`
link; xx = 80 .. 89): `/data/venv-research/bin/python research/queue/placebo.py --study H8x --fits-dir
/data/mind15/research/out/h60_regime_exits/fits_today --out /data/research_queue/out/H8x`. Estimated CPU hours from the
timing runs (seconds per draw over the eight markets, one processor, research server, 22 Nov 2026: H80 4.17, H82
0.41, H83 4.36, H84 3.79, H85 3.21, H86 4.26; loading the five groups about 66 s; peak memory 2.9 GB resident, of which
1.7 GB not file-backed, in the crypto load): H80 11.7 h (10,000 draws), H81 0.1 h (100,000), H82 11.4 h (100,000), H83
12.2 h (10,000), H84 11.7 h (11,000), H85 11.6 h (13,000), H86 11.9 h (10,000), H87, H88, H89 under 0.1 h each:
**about 70.6 CPU hours** in all. `--estimate` prints these figures.
## H90-H106. THE QUEUE FAMILY: walk-forward tests of one setting of the Setups rule (H90-H101) and chart-pattern claims on BTC and ETH (H102-H106) (registered 22 Nov 2026, about 11:40 UTC, before any H90-H106 number was computed; smoke runs on tiny slices only, their numbers not reported)

**Prompted by:** the owner, 22 Nov 2026: "Queue at least 20 studies for SG box so it will have always have min 72 hours
queue tasks backlog to clear". This family is one of three (another agent writes a placebo and bootstrap family; a third
builds the queue runner). Research only: nothing in the engine, the Setups book or the vault changes, whatever the result.
Code: `research/queue/walkforward.py` (H90-H101) and `research/queue/pattern.py` (H102-H106); tests
`tests/test_queue_walkforward.py`. Run by the job queue, one study per job:
`python research/queue/walkforward.py --study H9x --fits-dir <fits_today> --out <queue out>/H9x` (same form for pattern.py).

**The danger, and how this family is built against it.** Twenty studies on one history will throw up good-looking results
by chance. So: (1) every Part A setting is CHOSEN on one period and JUDGED on a later one, by a choice rule fixed now;
(2) the last year of data (2025-11-11 onward, the holdout) is never loaded: the code refuses any load past
2025-11-10 23:45 UTC (`wall()`, one function in each script); (3) the tests are counted in the ledger at the end and the
pass levels are Bonferroni-corrected for that count; (4) whatever passes leads ONLY to a proposal for a forward PAPER
shadow book, which needs the owner's word in this project. Nothing is ever called "proven".

**Known before registering (no outcome numbers of this family).** H65 (the Setups book's replay post-mortem; on all
history, the holdout included): the tightest third of stops lost (-81.9R over 2,623 trades), trades against the market's
30-day move lost, the forced entry neither helped nor hurt, the entries' lead in the odds did not hold across halves.
H67 and H68 (on the same history): a 30-day trend filter and a wait after a stop-out both "survive as a rule" on the
replay. H72 (tonight, another agent) tests those two out of sample; this family does not repeat them. H74 (tonight): the
owner's EMA200-drop / EMA10 long claim, "not supported" (8/22 episodes). The engine's constants are those of
think15-v5.2.9; the code refuses to run if any of the ten constants named below differs from the value stated here.
These grids were chosen from the engine's design and the brief, not from any replay of them: no grid value below has
been replayed by anyone, as far as the research log shows. One limitation stated now: the voices' card VOTING list
(`voting_for`, from the card rating of 17 Nov 2026) was chosen on full history; it is the same for every setting compared,
so it cannot favour one setting over another, but the odds themselves are not fully walk-forward in that one respect.

### PART A (H90-H101): walk-forward tests of one setting at a time

**The book.** The Setups rule `b_targets` exactly as it runs now (`shadows.CHALLENGERS["b_targets"]["rule"]` =
`{"targets": True, "early": True}`, cfg from `shadows.asset_cfg`, the early entry on BTC and ETH included), on all eight
markets, through the engine's own `shadows.run`, inputs from `shadows.book_inputs` of a market group prepared by
`research/h59_half_be.prep_cut` with the cached fits (as H62/H67/H68). Result per trade: the book's `r_mult` (net of
fees, over the risk at the entry stop). The script checks once per market on the choice period that its "current
setting" book equals the engine's own `run_challenger("b_targets")` book (trades and equity), and stops if not.

**How one setting is varied, without editing the engine.**
- A cfg override in the dict passed to `shadows.run` (stop_units, idle_max, theta_enter, theta_enter_shock, theta_flip,
  theta_counter, htf_bias, trend_tiebreak, step_aside).
- An ENTRY FILTER through the `guard` input: the study's mask is OR-ed into the market's real release-guard array (the
  real guard keeps working exactly as before; `release_guard` stays on). What `policy.decide` does where `guard[i]` is
  True, read from the code: FLAT -> IDLE, "release_guard": no new position at that close, and the idle count goes on,
  so when the mask ends the idle count may already be past `idle_max` and the FORCED entry can come at the first close
  after it. IN A POSITION -> HOLD, "release_guard_hold": no flip (neither the "other side clears the flip bar" flip nor
  the "against the higher-timeframe bias" flip) and no step-aside at that close; the open position keeps its stop and
  its targets, which `shadows.run` checks inside every bar before the decision, so a position can still end at its stop
  or targets while masked. An order decided at an earlier close still fills at the next open. Every mask uses only what
  is known at that bar's close (the close time, the close, the volatility unit at that close, and earlier bars).
- The rule flags `trend_days` and `wait_after_stop` exist but are not used here (H72 tests them).

**Periods, fixed for all of Part A.** CHOICE: each market's first decided session (from 2020-01/02) to the last stored
session at or before 2023-06-07 23:45 UTC. TEST: from the first session at or after 2023-06-08 00:00 UTC to the last stored
session at or before 2025-11-10 23:45 UTC. Each period's books start flat with $10,000 at the period's first session.
Trades are counted by entry time; a trade still open at a period's end is not counted.
HOLDOUT: nothing at or after 2025-11-11 is loaded (enforced in `wall()`).

**The order, enforced in code.** (1) CHOICE: every grid value is run on the choice period with the market groups loaded
ONLY up to the choice period's last session (the test period's bars are not in memory). The choice is computed and
written to `choice.json`. (2) TEST: the script runs on the test period only the current setting and the chosen one; any
other value is refused (`PeekError`) while `verdict.json` does not exist. The statistic below is computed and written to
`verdict.json`. (3) Only then: a table of every grid value on the test period, marked "descriptive, not used for any
choice". The tests check this order with a planted world (the test period cannot be loaded before `choice.json` exists).

**Choice rule, fixed for all.** On CHOICE, the grid value with the largest pooled sum of R (eight markets) among the values
whose BTC+ETH sum of R is at least the current setting's. Ties go to the current setting, then to grid order. If the
choice is the current setting, the study ends: "the current setting was already the choice" (no test-period number).

**Test statistic, fixed for all.** Per calendar month of the test period (2023-06 to 2025-11, 30 months, months with no
trade count as zero), D(month) = the sum over the eight markets of (chosen setting's sum of R minus the current setting's
sum of R) for trades entered that month (the pairing is by calendar month and market). The statistic is the mean of
D over months, with a month-clustered bootstrap (whole months resampled with replacement, 20,000 draws, seed 20261122):
95% percentile interval and one-sided p = (1 + number of bootstrap means <= 0) / (draws + 1). Also reported for both
settings: mean R per trade with a month-clustered 95% interval, the worst fall of the pooled paper equity (the eight books'
marked equity summed), the share of bars flat (markets' mean), the number of trades, paper net, and per market sums.

**Pass rule.** p below 0.05 / 12 = 0.00417 (twelve Part A studies, H90-H101), AND the BTC+ETH difference over the test
period not negative (and at least 12 months in the test period, which only a smoke run lacks). Conclusion words: "beats the current setting on later data", "does not", or "the current setting
was already the choice".

**A note on R across stop widths (H90).** R is in units of each trade's own entry-stop risk. On the markets sized by
`backtest.leverage` (risk about 2% a trade) a wider stop means the same money at risk; on BTC and ETH (cap 1x, full size)
a wider stop means more money per R. The choice and the test use R as registered; paper net in dollars is shown beside.

**The studies.** Current setting first; the grid is fixed; "never" values are implemented as idle_max = 10^9 and
theta_flip = 9.0 (an edge is at most 1.0).

## H90. Stop distance: `stop_units` in {1.0, 1.5, 2.0 (current), 2.5, 3.0, 4.0}
The protective stop is stop_units x the volatility unit (1.5 x ATR14 1h) from the fill; position size follows it.

## H91. Forced-entry clock: `idle_max` in {2, 4 (current), 8, 16, 48, never forced}
"Never forced" means the book enters only when a side clears the entry bar (it may stay flat a long time).

## H92. Entry bar: `theta_enter` in {0.02, 0.03, 0.05 (current), 0.08, 0.10}
Changed from the brief (which had 0.15 at the top, not 0.02): `theta_enter_shock` stays at 0.10 in this study, and with
theta_enter above 0.10 the high-risk bar would be LOWER than the normal bar, which turns the rule inside out; 0.15 is
replaced by 0.02 so the grid stays at five values on the same side. theta_enter is also the edge below which a position
against the higher-timeframe bias is flipped (policy.decide), so that moves with it.

## H93. Flip bar: `theta_flip` in {0.05, 0.10 (current), 0.15, 0.20, never flip}
"Never flip" switches off only the "other side clears the flip bar" flip; the flip to the higher-timeframe bias side
(a position against the bias with less than theta_enter for it) still works.

## H94. Counter-bias entry bar: `theta_counter` in {0.05, 0.10, 0.15 (current), 0.25}
Acts only when the higher-timeframe bias is set (htf_bias on, bias not 0); 0.05 equals theta_enter (no extra bar).

## H95. Higher-timeframe bias and trend tiebreak: (htf_bias, trend_tiebreak) in {(on, on) current, (on, off), (off, on), (off, off)}

## H96. Tight-stop entry filter: none (current), or no new entry when the stop would be in the lowest q, q in {0.2, 0.33, 0.5}
Reading at close i: ratio = unit[i] / close[i] (the stop distance per unit of price the entry at that close would get).
Threshold: the q-quantile of that ratio over the bars whose decision close falls in the 90 whole UTC days before bar i's
UTC day (so only earlier, closed bars); fewer than 30 days with bars in that window: no block. Blocked when ratio <= threshold.

## H97. Hours-of-day entry filter: none (current), or no new entry in one 6-hour UTC block: 00-06, 06-12, 12-18, 18-24
The hour is that of the deciding close (open time + 15 minutes); a close at 06:00 belongs to 06-12. On SPX (cash hours)
a block may cover most of its sessions; the rule is the same for all markets.

## H98. Weekend entry filter, BTC and ETH only: none (current), Saturday and Sunday UTC, or Friday 21:00 to Sunday 21:00 UTC
By the deciding close's UTC time. The other six markets run unchanged (their books are the current book, computed once).
The pooled statistic over eight markets is then the BTC+ETH difference.

## H99. Volatility entry filter: none (current), block the top third, block the bottom third of 24-hour realised volatility
Reading at close i: sqrt of the sum of squared 15m log returns of the bars that closed in the 24 hours up to and including
close i. Thirds: the 1/3 and 2/3 quantiles over the 90 whole UTC days before bar i's day (30 days minimum, as H96).
Top: blocked when the reading >= the 2/3 quantile; bottom: when <= the 1/3 quantile.

## H100. High-risk rules: `theta_enter_shock` in {0.05, 0.10 (current), 0.20} x `step_aside` in {off (current), on}: six values
0.05 equals theta_enter (no extra bar in high risk). step_aside on: in high risk with the held side's edge negative, go flat.

## H101. The kitchen sink: every chosen setting of H90-H100 stacked into one rule, tested once on the test period
Replaces the brief's H101 (the H67/H68 variants and their combination), which is H72 tonight. The rule: the current
setting with, for each of H90-H100, its chosen value where it is not the current one (cfg overrides merged; masks OR-ed).
It reads the other studies' `choice.json` from the queue's sibling output folders and runs LAST: if any is missing it
exits with code 75 and writes nothing final. There is no choice period of its own: the choice is the eleven choices.
If every study kept its current setting the study ends "the current setting was already the choice". Same statistic and
pass rule. Its point: to show what stacking choices made on one period really buys on a later one.

### PART B (H102-H106): chart-pattern claims on BTC and ETH daily bars

**Data.** Daily UTC bars (open first, high max, low min, close last) built from the stored 15-minute bars of BTCUSDT and
ETHUSDT from 2019-01-01, ending with the bar that opens at 2025-11-10 23:45 UTC (the last day is 2025-11-10). The holdout
is not read (`wall()`). Days with fewer than 96 bars are kept and counted in the report. EMA(N): alpha 2/(N+1), seeded
with the mean of the first N closes, defined from the N-th close on (as H74). RSI(14): Wilder's, seeded with the mean of
the first 14 changes.

**Entry at the event day's close. Three fixed "win" readings** (long; a short is the mirror): W5: close 5 days later above
the entry close; W10: 10 days later; WEMA10: held until the first later close below the daily EMA10 (short: above),
exit at that close, a win if the result after 0.05% a side (0.10% in all) is above zero. An event whose reading would
need a day past the data is left out of that reading.

**Statistics, per event kind and reading.** BTC and ETH pooled; events of either coin within 10 days of each other are one
episode (single linkage). Win rate on all events, with a cluster-bootstrap 95% interval (episodes resampled, 10,000 draws,
seed 20261122). As H74, the Wilson 95% interval and the exact one-sided binomial test against the stated threshold use ONE
event per episode (the earliest, BTC first on a tie: a choice that does not look at outcomes). Baseline: the same trade on
every other day (EMA200 defined, reading inside the data, event days left out), the difference (event rate minus baseline)
with a 95% bootstrap interval (episodes; baseline days in calendar-month blocks). Halves by entry day (before / from
2023-06-08). Per coin counts. **Conclusion words**: "supported" if the binomial p < 0.05 / 18 = 0.00278 AND the difference's
interval is above zero; "not supported" if the upper end of the Wilson interval is below the threshold; otherwise "too few
cases to tell". Threshold 55% unless the claim names one.

## H102. Golden cross (long) and death cross (short): daily EMA50 crossing EMA200; threshold 55%
Golden: EMA50 > EMA200 at the close and EMA50 <= EMA200 at the close before (both defined); long. Death: the mirror; short.
Two kinds x three readings = six tests. Descriptive beside it: nothing else.

## H103. Daily RSI(14) back above 30: RSI <= 30 at the previous close and > 30 at this close; long; threshold 55%

## H104. Three consecutive daily closes down totalling at least 10%: long at the third close; threshold 55%
close(d) < close(d-1) < close(d-2) < close(d-3) and close(d) / close(d-3) - 1 <= -10%. One event per down streak (no new
event until a close at or above the one before).

## H105. A daily close back above the EMA200 after at least 30 days below it: long; threshold 55%
close(d) > EMA200(d) and close(d-k) < EMA200(d-k) for each k = 1..30.

## H106. The mirror of H74 for the short side: threshold 50% (the claim: "is going short a winner more than 50% of the time")
Breakout day B: a close above the EMA200 with the previous close at or below it; counted only if more than 30 days after the
previous counted breakout. Rise: the first day d* in [B, B+30] where the highest close from B to d* is at least 1.20 x the
lowest close of the 60 days B-60 to B-1 (the mirror of H74's primary drop reading D1). Entry: the first day t in
[max(B+1, d*), B+30] with close(t) < EMA10(t) and close(t-1) >= EMA10(t-1); short at close(t). One entry per breakout.
Only D1 (H74's primary reading) is mirrored, to keep the count of tests down.

### Addendum before any study number (22 Nov 2026, about 12:00 UTC; code only, no study number computed)
- **Loader.** On the research server `h59_half_be.prep_cut` peaks at about 3.1 GB of memory on the crypto group, over the
  queue's 3 GB limit. `walkforward.py` therefore loads through `prep_cut_lean`, a line-for-line copy that keeps only the
  37 evidence columns the Setups book reads and computes the "which voices speak" mask in row chunks (peak about 1.7 GB).
  Checked on the server for all eight markets at the full cut (2025-11-10 23:45): the odds and the kept columns equal
  `prep_cut`'s exactly, and the current-setting book on the lean load equals `run_challenger("b_targets")` on `prep_cut`'s
  load (every trade and the equity). Only equality was printed; no study number was looked at.
- **Timing** (server, nice 19, one thread): a group load 1-17 s (crypto test period the longest), an unmasked book run
  about 0.4 s, a volatility- or tight-stop-masked run up to about 5 s. Estimated CPU time per Part A study 3-10 minutes
  (`--estimate`, with a 1.5x margin), Part B about a minute each. This family is far short of 72 queue hours on its own.

### Changes from the brief, made before registering
- H92's grid: 0.15 replaced by 0.02 (the reason is under H92).
- H101: the brief's own H101 was H72's work; it is the kitchen-sink control as the brief proposed instead.
- H98 moves only BTC and ETH, so its pooled statistic is the BTC+ETH difference (stated, not a separate rule).
- Part B: one event per episode for the exact test and the Wilson interval (as H74), the cluster bootstrap beside it.
- Bootstrap draws: 20,000 (Part A; the brief asked at least 5,000) so that p near 0.004 is resolved.
- Each period's books start flat and fresh (a walk-forward deploy of the chosen setting starts at the test period).

### The ledger
- Part A: 12 tests (H90-H101), each one-sided at 0.05 / 12. If no setting truly differed from the current one, the expected
  number of Part A passes by chance is at most 12 x 0.05/12 = 0.05 (the BTC+ETH condition only lowers it).
- Part B: 18 tests (H102: 6; H103, H104, H105, H106: 3 each), each "supported" only at 0.05 / 18; expected chance
  "supported" readings at most 18 x 0.05/18 = 0.05.
- Family: 30 tests; at most about 0.1 passes expected by chance alone (a family-wise chance of any false pass of at most
  about 10%). The descriptive tables (every grid value on the test period, halves, per coin, per market) are looks too,
  and pass nothing.
- Choice-period comparisons: 51 grid values in H90-H100 are compared on the choice period; they choose, they do not pass.
- **The standing rule:** a pass leads only to a PROPOSAL for a forward PAPER shadow book, registered on its own, and that
  needs the owner's word in this project. Nothing reaches the Setups book, the vault or real money from this family.

### Queue batch 1 results: H81, H87 to H100, H102 to H106 (22 Nov 2026, run by the research queue 13:04 to about 13:15 UTC; each study's `report.md` and `results.json` in `research/out/queue/<ID>/`)

All data end at 2025-11-10 23:45 UTC (the holdout was not read). Each conclusion below is the harness's own, by the rule
registered in that study's block; nothing was re-judged here.

**Part A, one setting at a time, chosen on 2020-02 to 2023-06-07, judged on 2023-06-08 to 2025-11-10 (pass level
p < 0.00417 per study): none passes.**
- The current setting was already the choice in 6 of 11: H90 stop distance, H93 flip bar, H94 counter-bias bar,
  H95 bias and trend tiebreak, H98 weekend filter, H99 volatility filter.
- Chosen something else, and it did not beat the current setting on later data: H91 idle_max 16 (p 0.79), H92
  theta_enter 0.10 (+1.79R a month, p 0.031: the closest, not a pass), H96 tight-stop filter q 0.5 (p 0.38), H97 no
  entries 12:00 to 18:00 UTC (p 0.32), H100 theta_enter_shock 0.05 (p 0.12).
- H101 (every chosen value stacked) was queued at 14:2x UTC, after its siblings' choice files existed.

**Part B, chart patterns on BTC and ETH daily bars (pass level p < 0.0028): none supported.**
- H102 golden and death cross: too few cases to tell (9 to 10 episodes each).
- H103 RSI(14) back above 30: too few to tell at 5 and 10 days; "not supported" for the hold-until-below-EMA10 reading.
- H104 three daily closes down totalling 10% or more: too few cases to tell by the rule (48 episodes; per episode 66.7%
  higher after 5 days, p 0.068 against 55%); it beat the all-days baseline (+12.2 points after 5 days, interval
  +0.2 to +23.7; +22.7 points for the hold-until-below-EMA10 reading, interval +9.8 to +34.5). Descriptive only.
- H105 a close back above the EMA200 after 30 days below: too few cases to tell (9 episodes; 8 of 9 higher after 10 days).
- H106 the short mirror of H74: not supported for the hold-until-above-EMA10 reading, too few to tell for the others.

**Placebo and bootstrap family, the quick studies:**
- H81 side placebo: the harness reports the real book NOT distinguishable from its placebo at the upper tail
  (p = 1.0000), with the lower tail at 0.0000: real -0.0030R a trade against a placebo median of +0.1083R. Read
  literally the book's side choice within a month is worse than a random assignment with the same monthly mix. A
  random assignment earning +0.11R a trade is implausible on its face; the result is UNDER AUDIT (22 Nov 2026) for an
  artefact in the trade scoring (`machine_r`, which H82 also uses) before it is read either way.
- H87 block bootstrap of 12-month paths (3-month blocks): current rule, chance of a losing 12 months 54% on eight
  markets and 56% on BTC and ETH, median 12-month sum -3.7R; the 30-day filter 37% and 18%; the wait after a stop-out
  26% and 33% (the two variants were found on this history, so their figures are flattered).
- H88 costs surface: the current rule breaks even at a fee of 0.032% a side with no slip on eight markets, and at
  0.086% a side on BTC and ETH (in R, before funding); the 30-day filter at 0.214% and the wait at 0.147% on BTC and ETH.
- H89 year by year: the current rule's sign turns when a single year is left out (on eight markets: 2022, 2023 or 2025;
  on BTC and ETH: 2024 or 2025): its result rests on single years. For the 30-day filter and the wait no single year
  turns the sign.

**Reading.** No single setting of the Setups rule, chosen on the first half, beat the current one on later data, and
none of five common daily patterns is supported on BTC and ETH. The current rule's own record is close to zero per trade
and rests on single years; its break-even fee on BTC and ETH (0.086% a side in R, before funding and slippage) is above
the member's 0.05%. Nothing here changes a book. The six heavy placebo studies (H80, H82 to H86) are still running or
queued.

**Audit of H81, and H82 withdrawn (22 Nov 2026, about 14:40 UTC; `research/out/queue/H81/audit.md`, script
`research/queue/h81_audit.py`).** H81 is VOID: its result is an artefact of the placebo's design, not of the trade
scoring and not a fact about the book. The scoring (`machine_r`, `replay_trade`) is sound: own-side and flipped
trades score symmetrically (own + opposite equals about minus two fees in R), no stop or target on the wrong side in
5,162 trades, no look-ahead, fees the same; a recomputation matched H81's saved outcomes exactly. The flaw: permuting
sides WITHIN a calendar month hands a trade the side of a trade entered LATER in that month. The book reacts to price
(stop-outs, flips, the higher-timeframe bias), so its later sides carry the month's direction (the month's long share
correlates 0.63 to 0.77 with the same month's move and 0.03 with the next month's). Sides taken only from later
trades of the month earn +0.223R a trade pooled, only from earlier trades -0.063R; on 12 driftless random walks the
same permutation makes a causal momentum rule "lose" and a reversal rule "win" by 0.045R. Against side choices that use
no future information the book is about as good as a coin (pooled -0.003R against -0.040R for a coin; ETH +0.060R
against -0.011R, BTC -0.082R against -0.071R); these comparisons are descriptive, not registered tests.
H82 has the same flaw (a trade moved to an earlier bar of its month keeps a side chosen later: in a sampled probe of
H82's own draw, placebo bars before the real entry earned +0.211R a trade, bars after -0.024R), so it was WITHDRAWN from
the queue before it started (moved to `/data/research_queue/held/`). H80, H83, H84 and H85 do not take sides from later
decisions and are not affected; H86 shuffles the stop unit within a month, which leaks future volatility (not
direction); its size was not measured and H86 will be read with that caveat. Corrected versions of H81 and H82 need a
fresh registration, with the disclosure that this audit saw the numbers above.

## H81b. Side placebo without look-ahead: does the book pick a better side than its own recent mix? (registered 22 Nov 2026, about 15:00 UTC, before any H81b number was computed; replaces the void H81; code `research/queue/placebo.py` study `H81b`, tests `tests/test_queue_placebo.py`)

**Prompted by:** the H81 audit (above): H81 permuted sides within a calendar month, so a trade could get the side of a
LATER trade, and the book's later sides follow the month's move. H81 is void. The owner asked for a causal version that
uses no information the book did not have at the moment of the trade.

**DISCLOSURE (read this first).** The H81 audit already computed, on this same data and window, descriptive numbers
that bear directly on this question: the book's own side earns -0.003R a trade pooled under the exits machinery,
against -0.040R for a fair coin; ETH +0.060R against -0.011R; BTC -0.082R against -0.071R; sides taken from earlier
trades of the same month -0.063R; sides at the share of the previous 10 trades -0.014R. The expected value of the coin
cell below and, closely, of the main cell are therefore already known. **H81b is partly a confirmation of a number
already seen, not a blind test**: what it adds is the registered p-value (how far the real side is from what chance
would give with the same mix), the halves and the market groups, under a design fixed before it runs. Its result must
be read with that in mind.

**Common part:** as the H80-H89 family (the book `b_targets` as the engine runs it, the engine-challenger check, THE
HOLDOUT IS NOT TOUCHED: every group ends at its last session at or before 2025-11-10 23:45 UTC, `CUT` in the script;
halves split at 2023-06-08, here by the REAL entry bar; pooled / vault (BTC+ETH) / others, each for the whole window and
both halves, plus per market, descriptive; the +1-corrected p-values; the job contract).

**Scored as H81 (unchanged and reused as it is):** every real closed trade keeps its real entry bar and entry price and
is scored under the exits machinery alone (`machine_r`: stop at 2 units from the entry, Target 1 and Target 2 from
`live.plan_targets` at the decision row for the trade's side, half off at Target 1 and the stop to the entry, else out
at the close of the last bar opening before entry + 30 days). The replay gate of H81 runs on every market (each real
trade replayed with its own side and window gives its own R, exit and exit bar, or the run stops). Both sides of every
trade are scored once; the run checks that the real side's outcome equals the real trade's machinery R.

**Scrambled (exactly):** on each market, take the book's real closed trades in entry order. The book holds one
position at a time, so every earlier trade is closed when trade j opens (the run checks this: entry bars strictly
increasing and each exit at or before the next entry, else it stops). For trade j, p_j = the long share of the book's
previous 20 trades on that market (all earlier trades while fewer than 20 exist; 0.5 for the first trade). The placebo
side of trade j is long when u_j < p_j, else short, u_j uniform on [0, 1), independent across trades. p_j reads only
the sides of trades entered before trade j (never its own side or a later one; asserted on planted data in the tests).
**Second cell, a fair coin:** long when u'_j < 0.5. Both cells come from the same draw: draw k uses
`numpy.random.default_rng([20261122812, k]).random((2, T))` over all T trades concatenated in the fixed market order
(row 0 the main cell, row 1 the coin).
**Real:** the same machinery on the real sides (identical to H81's real statistic).
**Primary statistic:** the pooled mean R per trade over the eight markets, whole window, main cell; p_upper = (1 +
draws at least as good as the real) / (1 + draws), p_lower beside it. The number of trades is fixed, so the mean R and
the sum of R give the same p-value. Secondary, with their own p-values, NOT used for the conclusion: every other cell
(pooled / vault / others x whole / first half / second half, per market), and the coin cell in the same cells.
The exact expectation of each placebo cell (closed form) is reported beside the draws, descriptive.
**Draws:** 200,000; seed 20261122812. **Conclusion wording, fixed now:** "the book's choice of side IS / is NOT
distinguishable from a side drawn from the long share of its own previous 20 trades at p = x" (IS when the primary
p_upper <= 0.05). Secondary line: "... from a fair coin at p = x". A low p_lower is reported as such ("the real side is
WORSE than the placebo at p = y"), never turned into a pass. Never "proven".
**What a "not distinguishable" says:** on this history the book's side adds nothing measurable, per trade, over a
side drawn at random with its own recent long/short mix. A "distinguishable" says the side carries something on this
history; it is not a forward result, and the disclosure above applies.

**Changed from the brief, and why:**
- The proposal is kept as it is (N = 20; fewer at the start; 0.5 for the first trade; plus a fair coin). Made precise:
  "previous trades" are the book's closed trades on the same market entered before trade j (all of them are closed at
  trade j's entry, checked in the run); the main cell is the primary test and the coin cell is a registered secondary
  line, so the family counts one primary test for H81b, not two.
- Draws: the brief asked for as many draws as fit in 1 to 2 CPU hours. Both outcomes of every trade are precomputed, so
  a draw is one vectorised pass (0.0005 s on the server for all 5,162 trades) and 1 to 2 hours would be millions of draws. The count
  is set at 200,000 by memory and need instead (two cells x 200,000 draws x 8 markets x 15 numbers is about 0.4 GB; p
  resolution 5e-6): the study takes about 0.05 CPU hours, nearly all of it loading the five groups.
- Halves by the real entry bar (the placebo moves no trade in time).

**Random-walk check (registration aid, synthetic data only; `placebo.py --rw-check 120`, unit test
`test_random_walk_check_causal_placebos_find_nothing_and_old_designs_tilt` on 16 walks).** 120 driftless random walks
(hourly bars, about 3% a day, two years each), a one-position toy book on each (entry by a causal rule at the close
before entry: 3-day momentum, 3-day reversal, or a coin; out by the same machinery, `replay_trade`, Target 1 1.5R and
Target 2 2R with no readings; the next entry 0-23 bars after the exit, so, as in the real book, when it enters next
depends on how the trade ended), about 400 trades a walk, 400 placebo draws a walk. Placebo minus real mean R a trade
(SE over walks), and the share of walks with p_upper <= 0.05 / >= 0.95 (5% each expected for a sound test):

| design | momentum | reversal | coin |
|---|---|---|---|
| H81 within-month permutation (void) | +0.054 (0.005); 0% / 24% | -0.084 (0.005); 48% / 0% | +0.007 (0.005); 1% / 9% |
| **H81b main: previous 20 trades' long share** | +0.002 (0.006); 7.5% / 5.0% | -0.006 (0.006); 10.0% / 8.3% | +0.006 (0.005); 2.5% / 6.7% |
| **H81b coin** | +0.005 (0.006); 6.7% / 3.3% | -0.009 (0.006); 8.3% / 6.7% | +0.007 (0.005); 1.7% / 9.2% |

The causal placebo finds no difference for any rule (every gap within 1.6 SE of zero) and does not reproduce the old
design's tilt (placebo "better" than a momentum rule, "worse" than a reversal rule). The tail shares are close to 5%
(the SE of a share over 120 walks is about 2 points); the reversal rule's are a little high in both tails. Why that can
happen: the main cell's spread is p(1 - p) per trade, and a real side that tends to go AGAINST its own recent majority
(as a reversal rule does) varies more than that, a side that goes WITH it (as a momentum rule, and the reactive real
book, do) varies less; so for a book like this one the main cell's p-value is, if anything, a little conservative. The
coin cell has no such effect (spread 1 per trade either way).

## H82b. Entry-time placebo without look-ahead: does the exact entry bar matter, given the side? (registered 22 Nov 2026, about 15:00 UTC, before any H82b number was computed; replaces H82, which was withdrawn before it ran; code `research/queue/placebo.py` study `H82b`)

**DISCLOSURE.** In the H81 audit's sampled probe of H82's own draw (each real trade moved to 4 random bars of its month,
same side, the machinery), placebo bars AFTER the real entry earned -0.024R a trade pooled (BTC -0.109R, ETH -0.039R,
BTC+ETH -0.074R), against -0.003R for the real trades (BTC -0.082R, ETH +0.060R). Those bars ran up to the end of the
month, not the window below, so they are not this study's number, but they are close to it in spirit: H82b too is
partly a confirmation of a number already seen, not a blind test.

**Common part and scoring:** as H81b (same book, gates, cut, halves by the real entry bar, cells, p-values, `machine_r`
with the 30-day cap, the replay gate).

**Scrambled (exactly):** each real closed trade keeps its SIDE (chosen at its real decision) and is moved to a bar
drawn uniformly from a window that starts AT its real entry bar. Drawable bars: the market's bars from its first
tradeable bar to the end of the window whose bar before has a finite, positive stop unit (as H82), plus every real
entry bar. With pos_j the position of trade j's real entry among the drawable bars, the window is the L_j drawable bars
pos_j, pos_j + 1, ..., pos_j + L_j - 1, where L_j = the median of the book's previous 20 entry gaps on that market (the
gap from trade m-1 to trade m, m <= j, counted in drawable bars; the gap that ends at trade j is known at its entry and
counts; fewer than 20 at the start), truncated to an integer, at least 1; L for the first trade is 1 (it stays at its
real bar); a window is cut at the data end. The offset is floor(u_j x L_j), u_j uniform on [0, 1); draw k uses
`numpy.random.default_rng([20261122822, k]).random(T)`. Entry price by the real trade's own convention: the close of the
bar before when the real trade was an early entry (BTC and ETH entries from flat, booked at the deciding close), else the
bar's open (flips, the other markets, the markets with a fill delay). Every placebo bar is at or after the real entry
bar (so the side was already decided; on the markets with a fill delay the decision was even earlier), and the window's
length reads only earlier entries (both asserted in the run and on planted data in the tests: scrambling every price
and stop unit before a trade's decision row leaves its whole window of outcomes unchanged). Offset 0 is the real trade
(checked in the run to 1e-12). A placebo trade may still be open at the next real entry: this is a trade-level test,
as H82 was, not a book; the share of windows that reach past the next real entry is reported per market.
Every outcome of every window is computed once with `machine_r`; a draw is then a table lookup.
**Real:** the real trades under the same machinery (the same real statistic as H81b). **Primary statistic, secondary
cells, p-values:** as H81b (one cell, no coin). The exact expectation (the mean over each window) is reported beside.
**Draws:** 200,000; seed 20261122822. **Conclusion wording, fixed now:** "the book's entry timing IS / is NOT
distinguishable from the same trades, same sides, entered at random bars at or after the real entry within the median
of its previous 20 entry gaps, at p = x". If not, the exact entry bar adds nothing measurable over entering the same
side at a random moment of the next typical gap. A low p_lower ("entering later would have done better") is reported as
such, not as a pass. Never "proven".

**Changed from the brief, and why:**
- **The window does NOT run to the next real entry.** The brief drew the bar from the real decision to the next real
  entry. The next real entry comes after the real trade has ended, and when it ends depends on where the price goes
  after the entry (a stop-out comes soon, a winner runs); a window that ends there makes every placebo bar a function of
  the trade's own future. The random-walk check below shows the size: on driftless walks that window makes the placebo
  lose about 0.08R a trade against the real toy book for every rule, the coin included, with p_upper <= 0.05 in 53% to
  60% of walks; the real book would have looked better than its placebo for nothing. The registered window keeps the
  brief's idea (about one typical gap between entries) but takes its length from the book's PREVIOUS entries.
- So placebo trades may overlap the next real decision (they keep a side the book may already have changed: stale but
  not future information).
- Draws: the brief asked for 8 to 12 CPU hours. Every window's outcomes are computed once (58 s on the
  server for the eight markets), after which a draw is a lookup (0.0003 s).
  200,000 draws resolve p to 5e-6; the study takes about 0.05 CPU hours in all.
- Halves by the real entry bar; entry price by the real trade's own convention (the brief's "close of the bar before
  for markets with the early entry" would price a BTC or ETH flip at a close the book did not use).

**Random-walk check** (as under H81b, same walks and toy books; placebo minus real mean R a trade (SE); share of walks
with p_upper <= 0.05 / >= 0.95):

| design | momentum | reversal | coin |
|---|---|---|---|
| H82 random bar of the month (withdrawn) | +0.066 (0.005); 0% / 27% | -0.087 (0.006); 43% / 0% | +0.008 (0.006); 1% / 8% |
| brief's window, to the next real entry | -0.081 (0.004); 53% / 0% | -0.078 (0.004); 54% / 0% | -0.077 (0.004); 60% / 1% |
| **H82b: previous 20 entry gaps' median** | +0.002 (0.004); 5.0% / 4.2% | +0.001 (0.004); 5.8% / 5.8% | +0.002 (0.005); 5.0% / 6.7% |

The registered window finds no difference for any rule and its tail shares are at 5%; it reproduces neither the old
design's tilt nor the brief window's.

**Queue commands** (as the family: the working directory at a code snapshot with `engine15/`, `research/` and a `data`
link): `/data/venv-research/bin/python research/queue/placebo.py --study H81b --fits-dir
/data/mind15/research/out/h60_regime_exits/fits_today --out /data/research_queue/out/H81b`, and the same with `H82b`.
`--estimate` prints 0.05 (H81b) and 0.05 (H82b) CPU hours; `--smoke` runs SPX to 2022 into
`<out>/smoke`. Peak memory 2.98 GB resident (the crypto load, the family loader; the draws need under 0.5 GB after it is freed). Smoke runs for this
registration (server, 22 Nov 2026, about 14:46 UTC, SPX to 2022, labelled SMOKE): only that the runs finish, the gates
pass and the files of the job contract are written was looked at; no statistic of H81b or H82b was read.

**The existing ids are unchanged.** The new code adds study ids and functions only; the one shared function touched,
`real_books_for`, now also runs the replay gate for H81b and H82b (the H81 and H82 path is as it was). Checked on the
server: `--smoke` of H80, H81, H83, H84, H85 and H86 with the code before this change (78d162d) and after it gives the
same `results.json` (all but the run time) and the same `report.md`, byte for byte. The script's fingerprint covers its
own text, so a job of an older id resumed with the NEW file would start its draws afresh (and reproduce the same draws,
each draw being seeded on its own); the running jobs use their own snapshot and are not affected.

### Ledger of the family H80-H89, updated with H81b and H82b (22 Nov 2026, about 15:00 UTC)

- H81 is void (design flaw) and H82 was withdrawn before it ran: neither counts as a test.
- **Tests that can come out "distinguishable":** 7 primary placebo p-values, as before: H80, H83, H84, H85, H86, and
  now H81b and H82b in place of H81 and H82. If none of the parts did anything and the seven were independent, the chance
  that at least one shows p <= 0.05 is about 30%; they are not independent (the same trades and markets run through all
  of them, and H81b and H82b share their real statistic).
- **Secondary p-values:** H81b and H82b report 17 secondary cells and 8 per-market ones each, and H81b the coin cell in
  all of them as well: about 75 more looks; some will look significant by chance and none decides a conclusion.
- **Not blind:** H81b and H82b were registered after the H81 audit had seen descriptive numbers on the same data (the
  disclosures above). A "distinguishable" from either is weaker evidence than one from a blind test; a primary p well
  below 0.01 that agrees across halves and market groups would be worth a forward test, and only that. Nothing here
  can make a rule "proven", and nothing in the engine, the books or the vault changes, whatever these studies say.

## H107. BTC and ETH: a long after a capitulation low that rebounds (rule A), and the same only when shorts are paying funding (rule B) (registered 23 Nov 2026, about 14:45 UTC, before any H107 number on history was computed)

**Prompted by:** the owner, 23 Nov 2026: "Deploy a study how we can take advantage of last fri where price huge drop to
55k and then rally back to now". Research only: nothing in the engine, the books or the vault changes, whatever the
result. A pass leads only to a proposal for a forward PAPER shadow book; it never changes a live book or the vault.

**The event (descriptive, from the box's bars, journal and trade files, read before this registration).** BTC fell from
75,442 (10 Nov) to 55,130 at 06:15 UTC on Sat 21 Nov (Fri 20 Nov 12:00 UTC to the low: 61,808 to 55,130); ETH from 2,137
to 1,538 at 04:00 UTC on 21 Nov. At the low the engine read: 24-hour return about -10%, 7-day about -17%, 3.7-3.8 ATR
below the 1h average, StochRSI 1h 0 / 4h 6 / daily 5, last funding negative (BTC -0.0061%, ETH -0.0188% per 8 hours,
both at the bottom of their 90-funding range), open interest down over 24 hours (BTC -2.4%, ETH -5.7%) with a
liquidation-proxy flag of longs closed out in a 7.6-sigma bar, net taker selling over 24 hours, Fear and Greed 12,
regime MOMENTUM_DOWN, higher-timeframe bias down; the odds led DOWN by 9 to 12 points at the low. BTC then rallied
+4% in 45 minutes and to 63,841 at 14:00 UTC today (one 15m bar +4.2%; ETH +4.9%). The main book's shorts left at the
low by their trailing stop (21 Nov 06:30, +$2,321 BTC, +$2,465 ETH) and then sold the bounce (ETH ENTER short at
1,613.70 at the 06:45 close, BTC ENTER short at 58,100 at 07:45); those and the next forced shorts were stopped (BTC
-$644, -$405; ETH -$641, -$670). The Setups book's BTC short took Target 1 then the entry (+0.60R); its ETH short was
stopped (-1.04R); both forced shorts of 21 Nov 14:30 were stopped today (-1.04R each); `b_trend30` and `b_wait_stop`
(live since 22 Nov) shorted on 22 Nov and were stopped today (about -1.06R each). A long from flat needs a 5-point up
lead (15 against a down bias); the odds' best up lead from the low until 13:45 today was -1.1 points.

**Known before registering (prior work, holdout untouched by H107):** H66: in 505 sudden rallies while short the Setups
book lost in 93%, turned long within a day in 26%, sold again inside the rally in 24%; what bounds the loss is the
stop. H70: 18 rebound-long rules out of an oversold state (24-hour -6%, 3 x ATR(1h) under the 1h EMA50, or 1h RSI
under 30; triggers: back above the 15m EMA20, 1.5 x ATR(15m) off the 4-hour low, above the 15m swing high; stop at the
4-hour low; 24-hour exit) ALL lost after fees in 2020-02 to 2023-06 (mean R -0.05 to -0.25): nothing to confirm. They
beat random longs, but mostly because their wider stops make the same fee a smaller part of R; before fees about
+0.03R better than a random entry. H71: none of the engine's own readings (odds lead, voices, StochRSI, stretch, flow,
funding) carried confirmed information about the next 24 hours in an oversold state; low funding came closest
(p 0.026 against 0.025) and largely repeats past price; in oversold bars the odds almost never reach the long bar.
H74 and H102-H106: the owner's daily EMA200/EMA10 pattern and five daily chart patterns are not supported (too few or
below the claim); H104 (three daily closes down 10%) was descriptively better than all days, too few to judge.
H65/H67/H72: the Setups book earns with the 30-day move and loses against it; H68: forced re-entries after a stop lose
on BTC and ETH. H80-H89, H81b, H82b: the book's odds are not distinguishable from shifted odds; its side choice is a
little better than its own recent mix (p 0.034); its exact entry bar is not distinguishable. So nothing already in the
engine catches a rebound; H107 asks a NEW trade shape (the engine's own stop of 3 x ATR(1h), a 48-hour hold) at a
capitulation low, not an oversold state in general.

**What must be said first.** Both rules were SHAPED BY THIS ONE EVENT: their numbers (a fresh 30-day low, 10% below a
week earlier, a 2 x ATR(1h) rebound, negative funding, a 48-hour hold) were chosen after looking at 20-23 Nov 2026,
where they fire once per coin at the 21 Nov 06:45 UTC close (BTC 57,194, ETH 1,613.70: the same close at which the main
book sold ETH short). That event is inside the sealed holdout (from 2025-11-11) and is NOT part of the test; it is
reported apart, descriptive only. H70's discovery period (2020-02 to 2023-06) overlaps this test's first half and was
seen, so the first half is not blind. Only the bar and funding files were read for the event (from 2026-08-01, for the
indicators' warm-up); nothing else from 2025-11-11 onward is computed.

**Data.** `btcusdt_15m.csv`, `ethusdt_15m.csv` (Binance spot 15m) and the two funding files, as copied from the box's
`/data/mind15/data` on 23 Nov 2026 (md5 in results.json). Deciding bars from 2019-10-01 00:00 UTC (funding exists from
2019-09-10; the 30-day low needs 30 days) to the cut. **Cut: every input is truncated at the bar opening 2025-11-10
23:45 UTC before anything is computed** (funding: rates set up to that bar's close); a trade must END by that bar, else
it is not taken. Halves split at 2023-06-08 by the deciding bar. No evidence store, fits, odds or engine book is used.

**Readings at the close of bar k (all from bars up to k).** ATR(1h) = Wilder ATR(14) of 1h bars (`data.resample`,
`indicators.atr_wilder`) joined by `data.htf_on_15` (only closed 1h bars), the engine's own stop unit (checked: it
gives the Setups book's live BTC stop of 21 Nov 14:30 exactly). low16 = lowest low of bars k-15..k (4 hours). low30d =
lowest low of the bars whose open is within 30 days up to k (needs 30 days of bars). c7 = close of the last bar whose
open is at or before open(k) - 7 days. Funding = the last rate SET at or before the close of bar k.

**Rule A (capitulation rebound long).** Signal at the close of bar k when, at k: (1) a fresh 30-day low within the last
4 hours: low16 <= low30d; (2) that low is at least 10% under the price a week earlier: low16 / c7 - 1 <= -10%;
(3) the rebound: close(k) >= low16 + 2.0 x ATR(1h); and (1)-(3) were NOT all true at k-1 (onset only).
**Rule B (A when shorts are crowded):** rule A's signal and the last funding rate < 0.
**The trade (both rules, fixed now).** Long at the open of bar k+1 = P. R = 3 x ATR(1h) at k (`stop_units` 2 x
`barrier_atr` 1.5, the engine's stop). Stop P - R. Bars k+1 .. k+192 (48 hours) are walked; in each bar the stop is
looked at first (low <= stop: out at the stop, or at the open if the open is below it); then Target 1 = P + 1R (half out
at T1 exactly, the stop on the rest moves to P from the NEXT bar); then Target 2 = P + 2R (the rest out at T2 exactly,
also in the T1 bar). What is left goes out at the close of bar k+192. Fees 0.10% of notional a side (`cost_side`) on
the entry and on each part's exit, in R. Funding is not charged or paid (as the books' R). One trade at a time per rule
and coin: a signal at k is taken only if k >= the previous trade's exit bar. Result per trade: R net of fees (and the
percent return).

**Statistics.** Pooled BTC + ETH, and each coin. Month-clustered bootstrap: every calendar month of the window (UTC, of
the deciding bar; months without a trade included) resampled with replacement, both coins' trades of a month together;
10,000 draws, seed 20261123; the statistic is summed R over summed trades of the drawn months; 95% interval = 2.5th and
97.5th percentiles; one-sided p for "mean R > 0" = (1 + #{draw - observed >= observed}) / (draws + 1) (the H70 method).
Holm correction over the two rules (m = 2) on the pooled whole-window p. **Baseline (drift):** for each coin-month with a
trade, the same trade entered at EVERY bar of that coin-month (window inside the period); excess = R minus that mean.

**Pass rule, per rule, fixed now. PASS only if all hold:** (a) at least 60 trades pooled and at least 20 in EACH half;
(b) pooled mean R > 0 in BOTH halves; (c) mean R > 0 on BTC alone and on ETH alone over the whole window; (d) the
Holm-adjusted one-sided p < 0.05; (e) pooled excess over the baseline > 0 (point estimate). Fewer trades than (a):
"too few trades to judge" (no pass). Anything else: FAIL.

**Read-outs.** For each rule: trades, share won, mean R, sum of R, median R, percent return, exits by kind, longest
losing run, deepest fall of cumulative R, months with a trade; pooled / BTC / ETH x whole / first half / second half,
each with the bootstrap interval and p for R and for the excess; signals skipped while a trade was open; the trade
list. **Look-ahead guards:** (i) for every signal bar (and up to 200 rule bars and 40 random bars per coin) the readings
are recomputed on data cut at that bar and must match the full run exactly; (ii) the vectorised trade walk is checked
bar by bar on every trade. **Descriptive only (decides nothing; one setting moved at a time):** rebound 1.5 and 2.5
ATR, drop 8% and 12%, hold 24 and 96 hours. **The event apart (descriptive):** the two rules on 19-23 Nov 2026.

**Code:** `research/h107_capitulation_rebound.py` (history run; `--event` for the event alone; the event mode was run
before this registration to check the code on the event it was shaped on: the numbers above). Output:
`research/out/h107_capitulation_rebound/` (`results.json`, `event.json`, `report.md`).

### H107 results (23 Nov 2026, about 14:50 UTC on the laptop, 22 s; `research/out/h107_capitulation_rebound/report.md` + `results.json` + `event.json`)

**Verdict by the registered rule: NO PASS. Rule A FAILS; rule B has TOO FEW TRADES TO JUDGE.** Data 2019-10-01 to
2025-11-10 23:45 UTC; the holdout was not read (only the bars of 19-23 Nov 2026 for the event apart).

Each cell: trades, share won, mean R [95% month-clustered interval], sum of R; one-sided p for mean R > 0.
- **Rule A, BTC + ETH:** 123, 47%, -0.006 [-0.220, +0.273], -0.7R; p 0.545, Holm 0.545. First half 83, 37%, -0.127,
  -10.6R; second half 40, 68%, +0.246 [-0.029, +0.556], +9.8R (p 0.057). BTC 54, -0.041, -2.2R; ETH 69, +0.021,
  +1.5R. Checks failed: first-half mean, BTC mean, Holm p. Excess over random longs in the same coin-months +0.19R
  [-0.03, +0.46]. By year (sum R): 2019 +0.7, 2020 -6.7, 2021 +7.7, 2022 -14.1 (44 trades), 2023 +1.3, 2024 +5.7,
  2025 +4.7. 51 of 123 stopped; longest losing run 11; deepest fall of cumulative R -19.3R.
- **Rule B (A with negative funding):** 32, 59%, +0.194 [-0.110, +0.622], +6.2R; p 0.182, Holm 0.364. First half 19,
  +0.079; second half 13, +0.362. BTC 8, ETH 24. Fewer than the 60 trades (and 20 a half) the rule needs; 16 of the 32
  are in 2022 (-0.4R together).
- **Descriptive, one setting moved at a time:** no variant makes rule A's first half positive (-0.05 to -0.21R a
  trade) or its second half negative (+0.23 to +0.41R); rule B +0.07 to +0.30R a trade on 12 to 44 trades.
- **Look-ahead guards:** 561 bars recomputed on data cut at the bar, 0 mismatches; the vectorised walk equals the
  bar-by-bar walk on every trade.
- **The event apart (inside the holdout, not a test):** both rules buy at the 21 Nov 06:45 UTC close (BTC 57,194, ETH
  1,613.70), take Target 1 the same day and close the rest at 48 hours on 23 Nov 06:30: BTC +1.31R, ETH +1.16R; flat
  for today's +4% candle.

**Deviations.** (1) ETH's funding file starts 2019-11-27, not 2019-09-10 as written (that is BTC's), so rule B could not
fire on ETH in Oct-Nov 2019. (2) The first run crashed in the look-ahead test on an empty funding slice before anything
was printed or written; the fix (empty = no funding yet) changes no rule, and the run was repeated.

**Reading.** A rule built on this event would have caught it, but over six years of history the same rule is flat after
fees: it lost in the first half (2022 above all, when bounces off new lows kept failing) and made money in the second.
Negative funding looks better but rests on 32 trades and is not significant. This agrees with H70 and H71: on BTC and
ETH no rebound-long rule tested so far has held up across both halves. Nothing here supports a paper shadow book on the
registered bar; nothing in the engine, the books or the vault was changed.

## H110. The book allocator `a_alloc`: does moving one paper wallet toward the books that are doing well forward beat holding them all equally? (registered 24 Nov 2026, about 05:25 UTC, before any H110 number was computed; RL idea R2 of `docs/RL_NEXT.md`; owner, 24 Nov 2026: "Ok lets do it")

**Paper only. NOT passed. It changes no book and no decision.** `a_alloc` is one paper wallet of $10,000 that is split
each UTC day between the forward books the scoreboard already judges. It reads the books' own trade records and writes
one block of `out/live/scoreboard.json`. It cannot create an edge that none of the books has: all it can do is hold more
of what has been working and less of what has not.

**What had been seen when this was written (disclosure).** The server's scoreboard of 24 Nov 2026 03:48 UTC (which
books exist and how many trades each has, for example `b_trail` 59, `p10_round` 121, `p1_liqhunt` 66) and the line in
`docs/RL_NEXT.md` that `b_trail` reads ahead and `p10_round` and `p1_liqhunt` behind. No allocator number, share or
equity had been computed. The settings below come from the textbook rule, not from the books' results.

**Start.** 2026-11-25 00:00 UTC (`book_alloc.START_UTC`). Nothing before it counts: only trades OPENED at or after the
start enter a daily result or a trade count (as the paper desk does not join a trade that was already open).

**The books (37, fixed now).** Each with the number of markets it trades; its capital base is $10,000 times that number.
- Main books, 8 markets: `main` (files `out/live/trades_<market>.csv`).
- Shadow books, 8 markets each (files `out/live/shadow_trades_<book>_<market>.csv`), 17 books: `main` (the hold copy),
  `v4`, `h3_flip_limit`, `b_targets`, `b_trend30`, `b_wait_stop`, `b_trail`, `a_pullback`, `y_4h`, `y_1d`, `h5_damp`,
  `m_swing_1h`, `m_swing_4h`, `b_be_t1`, `b_ema20_1h_t1`, `b_sma20_1h_t1`, `f_floor_33_3r`.
- Strategy books (the rows the strategy modules return each step), 19 books, markets in brackets: `p1_liqhunt` (6),
  `p2_trap` (6), `p3_orb` (6), `p4_gapfill` (1), `p5_squeeze` (6), `p6_vwap` (6), `p7_session` (2), `p8_fvg` (6),
  `p9_cascade` (2), `p10_round` (6), `p11_release` (6), `p12_orb_us` (2), the loop rules `p4_h30spot` (2) and
  `p4_h31trail` (2), the RL books `p5_rlq` (2), `p6_mtrend` (2), `p6_p4trend` (2), the pair book `p7_rvbear` (2) and
  the momentum yardstick `p8_mom` (2).

The CPI book (H1) and the paper desk are not on the scoreboard's rows and are not in. A book that joins the scoreboard
later is NOT added (it is listed as "not registered"). A registered book with no trade yet stays in with a zero result.

**A book's daily result (closed trades only; open trades are NOT marked).** The scoreboard's data holds closed trades,
not a marked value for every book, so: a book's result on UTC day D = the sum of `pnl_usd` (after fees) of its rows
whose close time is in D, divided by its capital base. Close time = `time_out` (main), `t_out_ms` (shadow),
`exit_utc` (strategy); entry time = `time_in`, `t_in_ms`, `entry_utc`. A trade closed in parts books each part on its
own day. A row written twice counts once. What this means: a trade held for days books its whole result on the day it
closes, an open loss is not seen until then, and a day without a closed trade is a zero. Dollars are taken as the book
booked them (a book's own compounding is not undone).

**Method: exponential weights (the "experts" rule), not Thompson sampling.** Why: (1) every book's daily result is seen
whatever the wallet held, because a paper share moves no book; that is the full-information case this rule is made
for, while Thompson sampling is for when only the chosen book is seen; (2) it has no random draw, so the same records
always give the same shares, it needs no stored state and the no-lookahead test is exact; (3) the engine already uses
it for card trust (`model.trust_path`). Settings, fixed now:
- Score of book b for day D = the sum of its daily results on the days before D since the start, each cut to the
  range -5% to +5% (`RET_CLIP` 0.05; the cut is for the score only, never for the equity). No forgetting.
- Raw weight = exp(`ETA` x score), `ETA` = 7.0: the textbook rate sqrt(8 ln N / T) / range with N = 37 books,
  T = 60 days and range 0.10, which is 6.94, rounded.
- **Cap:** no book above 25% (`CAP` 0.25). **Floor:** a book with fewer than 30 closed trades since the start (counted
  per entry, as the scoreboard counts) holds at least half the equal share (`FLOOR_X` 0.5: 0.5 / 37 = 1.35%); after
  30 trades it has no floor. Shares = the raw weights times one number, each held inside its floor and the cap, the
  number chosen so the shares add up to 1. If fewer than 4 books can be read the cap cannot be met fully invested:
  each holds 25% and the rest is cash at zero.
- **No lookahead:** the shares for day D use only rows that closed before D 00:00 UTC. On the first day every score
  is zero, so every book holds 1/37.

**The two wallets.** Both start at $10,000 and compound once a day. Allocator: wallet x (1 + sum over books of share x
the book's result that day). **Yardstick: the equal-weight mix of the same books over the same days**: wallet x
(1 + the plain average of the books' results that day). No cost of moving the wallet between books is counted (the
daily turnover is shown). `a_alloc` is "ahead" only against this yardstick.

**Verdict rule, forward only, fixed now.** d = the allocator's day result minus the yardstick's, on each completed UTC
day (a day is complete one hour after it ends). Two reads and no decision between them:
- **First read: the first 30 completed days** (25 Nov to 24 Dec 2026). **Second read: the first 60** (to 23 Jan 2027).
- The 90% range of the mean of d, the scoreboard's formula: mean +/- 1.645 x sd / sqrt(n). **"ahead"**: the low end is
  above zero. **"behind"**: the high end is below zero. **"level"**: the range includes zero. Before day 30: "too
  early to read (n of 30 days)". Both wallets' returns and their difference in points are shown beside the word.
- No other verdict word is used. A read changes nothing by itself: `a_alloc` stays NOT passed whatever it reads.
  "Ahead" at both reads means it is worth bringing to the owner; "level" or "behind" at the second read means the
  allocator added nothing over holding the books equally.

**Caveats, part of the rule.** The books are correlated and share market spells: 17 of the 37 are shadow books built
on the main engine's own calls, and most books trade the same eight markets, so 30 days hold far fewer than 30 separate facts
and may be one or two market moods; the range above understates the uncertainty. Closed-trade booking lumps a long
trade into one day. The equal-weight yardstick is itself mostly the main-rule family. The rule's own guarantee is only
that it ends close to the best single book in hindsight; that says nothing about beating equal weight.

**How it runs.** `engine15/book_alloc.py`, called by `reports.scoreboard` inside a try/except; block `a_alloc` of
`scoreboard.json`. It keeps no state: every step it reads the records again and recomputes every day from the start.
So a row that arrives late (gold, silver and oil step one bar behind) can still move the newest day's shares in the
first hour of that day; after that a day's shares do not change unless a record changes. A book whose records cannot
be read at a step is left out of that step for both wallets, and the block says so. Constants live in the module, not
in `CFG`. Tests: `tests/test_book_alloc.py`.
## H108. RL idea R3: card trust kept separately per regime bucket, as a paper shadow mind (registered 24 Nov 2026, about 05:25 UTC, before any H108 code existed or any H108 number, on history or live, was computed)

**Prompted by:** `docs/RL_NEXT.md` section R3 ("Trust that depends on the regime") and the owner, in this project, 24 Nov
2026, on the three RL-style ideas that "would run as a paper shadow first": "Ok lets do it".

**What must be said first.** There is NO evidence yet that this helps. Nothing was measured before this entry: no
replay, no forward number, no count of how often each bucket occurs. The known risk (RL_NEXT.md): each bucket sees
fewer graded calls than the one live table, so its weights are noisier. The forward shadow book is the only test.
Paper only. It decides nothing for any other book.

**The idea.** The live engine learns one set of card weights ("trust") per market group from every graded call
(`engine15/model.py` `trust_path`: exponential weights, 10-day half-life; then the 40% cap). The shadow mind keeps one
such set PER REGIME BUCKET: a card's errors made in one kind of market only move its weight for that kind of market.

**The buckets, fixed now (4).** Read per market at each 15-minute close, from two readings the engine already has at
that close (`engine15/evidence.py`; closed bars only):
- trend or range: the `regime` reading (the six-label daily regime of the last CLOSED daily bar). `TREND_UP`,
  `TREND_DOWN`, `MOMENTUM_UP`, `MOMENTUM_DOWN` = "trend". `RANGE`, `TRANSITION` = "range".
- high or low volatility: the `vol_rank` reading (where ATR(1h) / price stands among its last 2,880 15-minute bars).
  0.5 or more = "high". Below 0.5 = "low".
- The four buckets: `trend_hi`, `trend_lo`, `range_hi`, `range_lo`. A bar where either reading is missing has no bucket.

**The rule, fixed now.** For a market group (its markets pooled, as the live learner pools them) and a bucket b:
- A call made at bar t on market a belongs to bucket b when market a was in b at bar t.
- Bucket b's table is exactly `model.trust_path` fed only with the calls that belong to b. Same loss (direction only,
  calls graded up or down), same clock (a loss counts from the bar its grade arrives, never earlier, and halves every
  960 bars after that), same constants as the live learner, read from the live config, never copied: `trust_eta`,
  `trust_halflife`, `trust_floor`. Same learning window as the live step.
- At bar s, market a takes the table of the bucket it is in at bar s. Then the live mixing, unchanged: only the
  group's voting cards, the 40% cap (`trust_cap`), a card with no reading has no vote, the cap again, the weighted
  mix of the cards' calls. That gives the mind's own odds for bar s.
- A bar with no bucket uses the engine's own odds. A bucket with no graded call yet starts level (every card equal).
- The paper book `m_regime_trust` trades those odds with the main rule, unchanged: `shadows.run` with no rule
  switched on (the rule of the fresh main copy `main`: `policy.decide`, the same stop, the same sizing, hold to stop
  or flip, the 4-session mandate), $10,000 per market, the market's own fee. All eight markets. It starts FLAT on
  each market at its first live bar. The tables it starts with come from the graded calls of the live learning window
  (warm-up, as for the live learner; not proof of anything).
- No look-ahead: a table at bar s uses only calls whose grade had arrived by bar s. A truncation test holds this
  (the odds at bar t must not change when later bars are removed).

**What it is compared with.** The fresh main copy (`main` in `shadows.CHALLENGERS`): the same rule, the same bars,
the same sizing, the same markets, over the same days. The only difference is the odds (one table against four).
Each side is its change in marked paper equity since the bar the mind started on that market, summed over the
markets, in percent of the starting capital ($10,000 x markets).

**The verdict rule, fixed now. Forward only.**
1. Nothing is read before the book has 30 closed forward trades (all its markets pooled; a trade counts when it is
   fully closed). Until then the only words are "too few trades to judge (N of 30)" and "no read before 30 closed
   forward trades". A history replay, if one is ever run, is labelled warm-up and decides nothing.
2. The read at 30 is the first server scoreboard (`out/live/scoreboard.json`) whose `m_regime_trust` row shows 30 or
   more trades, copied as it stands: the row against zero by `research/VERDICT_RULES.md` section 2 ("ahead", "behind"
   or "undecided" from the 90% range), and the comparison line beside it. Later changes do not change the read.
3. The comparison line uses only these words: the mind is "ahead of" the main copy when its return is 1.0 percentage
   point or more above the main copy's over the same days, "behind" when it is 1.0 point or more below, otherwise
   "level with". Both returns and the difference are shown. BTC and ETH alone are shown beside it, not as the rule.
4. A second read follows at 60 closed trades, by the same rule.
5. What each outcome changes: "ahead of" at both reads, and the row against zero not "behind": the result goes to the
   owner with a proposal (a longer run or a registered follow-up); nothing else. "behind" at both reads: I propose to
   retire the book; the owner decides. Anything else: it keeps running and nothing changes.
6. No word such as passed, proven, works or edge is used for it. `research/VERDICT_RULES.md` section 3 applies: 30
   trades opened within a few weeks of one market spell show much less than 30 independent results would, and the
   two books trade the same bars, so most of their results move together.
7. Nothing here changes the live learner, the main books, the Setups book (`b_targets`) or what the vault is sent.
   Any such change needs the owner's word in this project and its own registration.

**Not tested, said now:** other bucket choices (six labels, three volatility bands, the 4h trend), a bucket clock
that only runs while the market is in the bucket, a different half-life per bucket. None is tried here. Trying them
later is a new hypothesis each.

**Code:** `engine15/regime_trust.py` (the buckets, the tables, the odds, the book's step, the comparison line),
hooked into `engine15/shadows.py` `advance` as a guarded shadow mind (`shadows.MINDS`; a failure is logged in one
line and skipped). Tests `tests/test_regime_trust.py`. Scoreboard label: "NOT passed, paper only".
## H109. An exit learner for BTC and ETH: a paper book `b_learn` that follows whichever exit rule has been earning most in the current market state (registered 24 Nov 2026, about 05:45 UTC, before any H109 code existed and before any number for the learner, on history or live, was computed)

**Prompted by:** `docs/RL_NEXT.md`, R1 ("Exit and join learner for setups"; only the EXIT part is built here, not the
join part). The owner on 21 Nov 2026: "Not now". The owner on 24 Nov 2026, on three RL-style ideas that "would run as
a paper shadow first": "Ok lets do it". The 24 Nov word replaces the earlier one. Paper only. Nothing here reaches the
Setups book, the vault feed or any main book.

**What must be said first.** H36 found that on history holding beat every trail and every target exit (2020 to Nov
2026, eight markets: hold +$329k, every variant less). A learner that shifts weight between exit rules ends close to the
best single rule; it can only do BETTER than the best single rule if the right exit depends on the market state at
the entry. That is not proven. It is the one thing this book tests. If one rule is best in every state, the learner
ends as a late copy of that rule and adds nothing.

**Disclosure: what had been seen when this was written.** H36's history numbers (above); `b_trail`'s history (-$47k)
and its forward lead ("ahead" at 33 trades, RL_NEXT.md); `b_targets`' read at 30 trades (ahead, +$6,915, eight markets;
BTC and ETH alone 11 trades, +10.77R; VERDICT_RULES.md section 10). While checking the file format, the header and the
first row of the laptop's stale copy of `shadow_trades_b_targets_BTCUSDT.csv` (one trade, 11 to 13 Nov, +1.40R). The
per-arm BTC and ETH records of the other five arms were not opened. No bucket, weight or choice was computed.

**The arms (six, fixed).** The exit rules the shadow books already run on BTCUSDT and ETHUSDT
(`engine15/shadows.py` `CHALLENGERS`), each with its own $10,000 per coin and its own live record:
`b_targets` (the Setups book: half at Target 1, the rest at Target 2, stop to the entry after Target 1), `main` (the
hold copy: out only at the entry stop or on a flip), `b_trail` (swing / 2 ATR trail after 1R), `b_be_t1` (stop to the
entry after Target 1), `b_ema20_1h_t1` and `b_sma20_1h_t1` (EMA20 / SMA20 of the 1h chart as a trail after Target 1).
Not arms: `b_trend30` and `b_wait_stop` (they change entries, not exits), the H61 floor follower, v4, H3, A, H5, the
yardsticks and the swing minds. The arms take the same entries only until their first different exit; after it each
re-enters on its own clock. So the arms' trades are NOT the same setups graded six ways (RL_NEXT.md's picture): each
arm is scored on its own closed trades. This is said because it is weaker than a same-setup comparison.

**The reward.** A closed trade's net R-multiple after fees: the `r_mult` column of the arm's own record
(`out/live/shadow_trades_<arm>_<coin>.csv`; net result over the risk at entry). Not clipped. A row without a finite
`r_mult` is left out.

**The buckets (four, fixed before any result).** Two readings at the entry, from the stored 15-minute bars of the
entry's own coin, using only bars that had CLOSED at or before the entry time (for these six arms the entry time is the
close that decided the entry):
- *Volatility*: x = a bar's true range over the previous close. The mean of x over the last 96 closed bars (24 hours)
  against the median of that same 96-bar mean over the last 2,880 closes (30 days, this close included). Above the
  median: `wild`. Otherwise: `calm`.
- *Trend agreement*: on 4h bars and on daily bars (built with `data.resample`, read through `data.htf_on_15`, so only
  a 4h or daily bar that has closed counts), the sign of the last closed bar's close against the simple average of the
  last 20 closed closes. Both above or both below: `agree`. Anything else: `mixed`.

Buckets: `calm_agree`, `calm_mixed`, `wild_agree`, `wild_mixed`. BTC and ETH share one weight table per bucket (the
coin is NOT a split: eight buckets would halve the trades in each, and the book already keeps the coins apart). An entry
with no reading (fewer bars than the look-backs need, or the last stored bar more than one hour before the entry) is
left out: it is neither followed nor used for weights, and it is counted in the block.

**The weights (exponential weights, full information).** For bucket b and arm a at time T:
score(a, b, T) = the sum, over a's closed trades of both coins whose ENTRY was in bucket b and whose exit time is
strictly before T, of r_mult x 0.5^((T - exit time) / 30 days). Weight = exp(0.5 x score), normalised over the six
arms. Half-life 30 days, learning rate 0.5 per R, both fixed here. Because the book follows the single best-weighted
arm, the learning rate changes the weights shown but never a trade: only the ORDER of the scores matters.
A bucket's own table is used once it holds at least 12 closed arm trades (all arms together, exits before T); until
then the choice uses the four buckets pooled into one table. Ties (and the start, when every score is zero): the order
`b_targets`, `main`, `b_trail`, `b_be_t1`, `b_ema20_1h_t1`, `b_sma20_1h_t1`. So with no information the book copies
the Setups book.

**Warm-up (not proof).** Weights start equal. Every closed trade in the arms' LIVE records counts for the weights,
including the ones closed before `b_learn` starts (the arms have run since 11 and 13 Nov 2026). Those earlier trades
are warm-up for the weights only; none of them is a trade of `b_learn`. No history replay is run for starting weights.
One may be added later only by a new note here, as warm-up, never as proof.

**The follower rule (how weights become a paper position).** One book per coin, $10,000 each, flat at
2026-11-25 00:00 UTC (`START_UTC`); only arm trades entered at or after that time can be followed.
- When `b_learn` is flat on a coin and an arm opens a trade on that coin at time T, in bucket b: if that arm is the
  best-weighted arm for b at T (weights from trades closed strictly before T), `b_learn` copies that trade from its
  entry to its exit, at the arm's own fills, sized so that it earns the arm's return on equity for that trade (its
  result = the arm's net result x `b_learn`'s equity over the arm's equity before the trade). Then it is flat and
  chooses again.
- It is flat for an entry at T if its last copied trade closed strictly before T, or closed at T and was the same
  arm's (an arm's flip is one moment). An entry of another arm in the bar in which its own trade closes is not taken.
- Entries of arms that are not the best-weighted one are ignored. While the best arm is inside a trade that began
  before `b_learn` was free, `b_learn` waits flat. The time it spends flat is reported.
- No lookahead: the choice at T uses the arms' closed-trade rows with exit time before T and bars closed by T, nothing
  else. A test removes later trades from the arms' records and checks that no earlier choice changes.

The book keeps no state: every step it is recomputed from the arms' closed-trade files, the shadow books' state (open
trades) and the bar files, so a restart or a late deploy gives exactly the trades a continuous run from `START_UTC`
gives. A row written twice counts once; a row or state that does not add up leaves that trade out.

**Baselines, over the same days** (arm trades entered at or after `START_UTC` and closed by the read): `b_targets`,
and the best single arm, which is the arm with the highest sum of net R on BTC and ETH together, picked at the read
with hindsight. That is a hard yardstick and it is meant to be.

**Verdict rule (forward only; wording as `research/VERDICT_RULES.md` sections 2, 3 and 10).**
1. The read at 30 is the first server scoreboard whose `b_learn` row shows 30 or more closed trades (BTC and ETH
   pooled), copied as it stands; the read at 60 the same at 60. Later changes of the text do not change either. No
   decision is taken between the two.
2. The scoreboard's own verdict (ahead, undecided or behind zero, from the 90% range per trade) is copied but is NOT
   the pass rule here: `b_learn` copies the arms, so being above zero says the arms made money, not that choosing
   helped.
3. At 30: nothing changes whatever it shows. A short note: its sum of R against each arm's over the same days, which
   arm it followed how often, by bucket, and the share of time flat. If the scoreboard reads "behind", a post-mortem
   first, then the owner decides whether it runs on.
4. At 60, "the learner adds something" only if ALL hold over the same days: (a) its sum of net R is above
   `b_targets`'; (b) it is above the best single arm's; (c) at least two different arms were each followed for at
   least 10 of its trades (otherwise it is one rule under another name); (d) the scoreboard does not read "behind".
   Then, and only then, a proposal goes to the owner for a NEXT TEST under a new registration. It is not a proposal
   to change the Setups book.
5. At 60, (a) holds but (b) does not: no worse than the Setups book, no better than one fixed rule. The contextual
   part has not shown itself. It runs on to 100 trades for the record; no proposal.
6. At 60, below `b_targets`: a post-mortem, then the owner decides: retire it or keep it as a labelled reference.
7. Whatever the read, nothing changes the Setups book, the vault feed or a main book without the owner's word in this
   project and a new registration. Sixty trades from two coins that move together, inside a few weeks, are far fewer
   than sixty independent results (VERDICT_RULES.md section 3); a pass here is "worth a second look", never proof.

**Label.** On the scoreboard the book is a shadow, paper only, NOT passed. It never calls itself passed.

**Code:** `engine15/learn_book.py` (the book; constants in the module, none in `CFG`), hooked into
`reports.scoreboard` inside a try/except, as the paper desk is. Tests: `tests/test_learn_book.py`. It writes
`out/live/shadow_trades_b_learn_<coin>.csv` (its closed trades, rewritten from the recomputation) and the
`exit_learner` block of `out/live/scoreboard.json`. It reads the arms' files and changes none of them.

### H109 note: implementation choices (24 Nov 2026, written with the code, after the registration was committed as d9002fd)

Nothing in the registered rule was changed. What the registration left open, and what was seen while building:
- **Readings.** The two means (96 bars of range, 20 higher-timeframe closes) are summed window by window, and the
  median is an order statistic, so a reading is the same whether the bar file is read from 40 days or from six years
  before the entry (`tests/test_learn_book.py` checks both that and the cut at the entry's bar). The bars are read from
  the tail of `data/<coin>_15m.csv` by the module's own reader, held equal to `signals.read_bars` by a test.
- **Decay base.** Rewards are stored against `START_UTC`, a constant, so a stored reward does not depend on which other
  rows the records hold.
- **Open trades.** An arm's open trade is read from `data/shadow_state.json`. If its closed row is already in the arm's
  file (the engine writes the file before the state), the file wins. An open trade the state cannot support is left out.
- **An input that cannot be read at a step** (a bar file, the state file): the block says so and the book's own record
  on file is left as it was, so a half-written file never shortens the record or changes the scoreboard row.
- **Not on the page's shadow table.** The book is hooked into `reports.scoreboard` (rows of `scoreboard.json`, as every
  shadow book, plus the `exit_learner` block), not into `shadows.FOLLOWERS`: `shadows.py` is on the money path and was
  not touched. So it has no row in `page["shadows"]["scoreboard"]` (the marked-equity table with `vs_main_usd`).
- **Seen after the registration, not a result:** one smoke run, writing nothing, on the laptop's stale copy of the
  arms' files (four of the six arms, up to 16 Nov 2026): the book reads "not started", 20 warm-up trades all fall in
  `wild_agree`. No forward number exists yet.
- **Step cost, measured on the laptop** with synthetic records and a 21 MB bar file: about 0.03 s with today's two
  weeks of arm records, 0.08 s after three months, 0.23 s after a year. It grows with the length of the arms' records.

## H111. Pairs as one bet: the Setups book's trades counted at half size when the pair partner already holds the same side, and a cap on trades open in one direction (registered 24 Nov 2026, about 12:20 UTC, before any H111 number on history was computed)

**Prompted by:** the live audit of 24 Nov 2026 (`research/out/live_audit_20261124/report.md`, findings 1 and 10, row B
of its table): BTC and ETH open and close in the same hours, as do gold and silver, and WTI and Brent; the main books
were short on five or more markets at once 89% of the time; on 23 Nov the Setups book took five stops in one day
(-$2,086). The owner: "count BTC+ETH, gold+silver and WTI+Brent as one bet each, or cap total risk in one direction".
Research only: nothing in the engine, the books or the vault changes, whatever the result.

**Known before registering.**
- H65: on history the Setups book (`b_targets`) is flat per trade (+0.004R over 5,963 trades to 21 Nov 2026; first half
  +29.6R, second half -7.1R; BTC+ETH -7.7R, the other six +30.3R); it earns with a market's own 30-day move and loses
  against it. H67/H68: pooled worst fall of the eight books' summed equity -61.6%; paper net -$21,233 on $80,000; the
  30-day filter and the wait after a stop looked better on the history they were found on. H87-H89: the current rule's
  chance of a losing 12 months is about 54%; its sign turns when one year is left out (2022, 2023 or 2025); it breaks
  even at a fee of 0.032% a side on eight markets. H80-H86, H81b, H82b: the odds are not distinguishable from shifted
  odds; the side choice is a little better than its own recent mix (p 0.034). H81 was VOID because its placebo handed
  a trade information from later in the month: a placebo must not borrow from the future.
- The live audit's 14 days (10 to 24 Nov 2026, one falling market; Setups book 35 trades, 29 short, +$5,204; five stops
  on 23 Nov). THE IDEA COMES FROM THOSE DAYS. They lie in the forward slice below, which is therefore not a test.
- Nothing about how the eight books' results move together on history has been computed in this project (no entry in
  this file on pairs, daily co-movement or trades open at once; H37 is a BTC/ETH relative-value book, another matter).
- Before this registration one loader-only run was made on USDJPY to learn whether the cached fits reach today's
  store (they stop at 2025-11-10; 38 weekly refits were recomputed in 44 s). It printed sessions, refits and seconds.
  No book was run and no trade or result was computed.

**What must be said first.** A replay on history is post-mortem material, not validation. The holdout (from 2025-11-11)
was already read for this book by H65, H67 and H68, so no part of this history is blind for the Setups book, though
no pair or direction measure was looked at. A pass below is a reason to propose a forward paper shadow and nothing more.

**Source.** The current Setups rule (`shadows.CHALLENGERS["b_targets"]`, rule `{"targets": True, "early": True}`, as in
think15-v5.2.10) replayed per market by the engine's own `shadows.run`, exactly as H68's "current" book, on all eight
markets, each from its first decided session to its group's last stored session in the shared copy of the box's data
(crypto and fx 24 Nov 2026 04:30 UTC, metals and energy 04:15, index 23 Nov 20:45). Loader:
`research/queue/walkforward.prep_cut_lean` (H90-H106's line-for-line copy of `h59_half_be.prep_cut` that uses less
memory); fits from this worktree's `fits_today`. Every book is checked to be the engine's own
`run_challenger("b_targets")`, trade for trade; a failed check stops the run. Closed trades only: a trade still open at
the end is left out. Reconciliation, reported whatever it shows: the trades closed by each group's last session at or
before 2026-11-21 13:45 against H68's 5,963 trades and +22.5R (H68 ran on the research server with its own fits; the
last year's fits are recomputed here on another machine, so small differences are possible and will be stated).

**Points.** A trade's result = 100 x `pnl_usd` / (the book's equity just before the trade opened), where that equity
is the trade row's `equity` (after the close) minus its `pnl_usd`. Position size is equity x leverage, and leverage
depends only on the stop distance, so this percentage does not depend on how much the book had won or lost before. A
trade is booked whole on the UTC day its exit bar opened (a Target 1 part taken earlier is booked with the rest).
"Portfolio points" of a day = the sum over the eight books. Days without a close count zero.

**"Open at moment T", fixed now.** A trade is open at T when it was entered before T (entry time < T) and its exit bar
opens at or after T; an exit by FLIP or STEP_ASIDE is a fill at the bar's open, so such a trade is already closed at
its exit bar's open. Times are `t_in_ms` and `t_out_ms`. Two trades with the same entry time opened "at once".

**Variants.**
- **V0 current:** every trade at full size.
- **V1 pair-half (PRIMARY):** pairs BTCUSDT-ETHUSDT, XAUUSD-XAGUSD, WTI-BRENT (USDJPY and SPX have no partner and are
  never changed). A trade that opens while its partner holds an open trade on the same side counts at half its points,
  for its whole life. The trade already open is not changed. Two partner trades opened at once on the same side BOTH
  count at half (together one bet). Because only the size changes, every entry, stop and exit is the book's own: V1 is
  exact in points, with no change to any book's path.
- **V1s (descriptive):** as V1, but two trades opened at once both stay at full size (the strict reading of "already
  open").
- **V2 direction cap (descriptive only):** trades taken in order of entry time (ties in the order BTCUSDT, ETHUSDT,
  XAUUSD, XAGUSD, USDJPY, SPX, WTI, BRENT). A trade is dropped when four or more trades that V2 itself kept are open on
  its side on other markets at its entry, counting kept trades entered at once and earlier in that order (it would be
  the 5th or later). Descriptive because a real book that skips a trade is flat afterwards and would enter differently
  later; here the trade is only removed from the record and every later trade of that book is kept as it was. This
  flatters or harms V2 in ways the replay cannot show.
- **Placebo for V1 (descriptive):** 2,000 draws (seed 2026112411); in each, the same NUMBER of trades as V1 halved is
  halved in each market and segment, chosen at random among that market's trades of that segment. The choice uses
  nothing about results or later bars. Reported: the share of draws whose ratio (below) is at least V1's, per segment.
  It answers whether WHICH trades are halved matters, or only that some are.

**Segments, by the day a trade is booked, not overlapping:** h1 = to 2023-06-07; h2 = 2023-06-08 to 2025-11-10;
holdout = 2025-11-11 to 2026-11-10; forward = 2026-11-11 on (the days the idea came from; descriptive); all = everything.

**Measures, per segment and variant.** Total points; worst day (the lowest daily portfolio points); worst fall = the
largest drop of the running sum of daily points from its highest point so far, the running sum starting at zero at
the segment's first day (a positive number); ratio = total / worst fall. The ratio does not change when every trade is
made smaller by the same factor, so "just bet less" cannot raise it: V1's ratio beats V0's only if the halved trades
are worse than the rest or sit inside the falls.

**Descriptive tables.** (1) On a 15-minute grid over the days when all eight books have started (positions carried
over closed hours): the share of time 5 or more markets hold the same side (long, short, either), by segment, and the
spread of the largest same-side count. (2) Per pair: the correlation of the two members' daily points (all days, and
only days on which both closed a trade), the share of time both hold the same side, and the share of each member's
trades that V1 halves. (3) Of the 20 worst V0 portfolio days: on how many did both members of a pair lose (each
member's daily points below zero), per pair and any pair, beside the same share over all days. (4) The mean points per
trade of the trades V1 halves against the trades it leaves full, by segment (V0 size). (5) Counts: trades halved by V1
and V1s, trades dropped by V2. (6) Per market: trades, total points.

**PASS condition for V1, fixed now.** PASS only if ALL hold:
1. in h1, V1's ratio is higher than V0's AND V1's total is above zero;
2. the same in h2;
3. the same in the holdout;
4. V1's total over all history is at least 85% of V0's (if V0's total is zero or negative: V1's total is not below V0's).

A worst fall of zero gives no ratio and that leg is not met. Anything else is "DOES NOT PASS". V1s, V2, the placebo and
every table are descriptive and pass nothing. One primary test, so no correction for multiple tests; the descriptive
looks (two variants, a placebo, six tables, five segments) are looks and nothing more.

**What a pass changes.** Only a proposal, to be registered on its own and needing the owner's word, for a forward PAPER
shadow of the pair rule. It never changes a live book, the Setups book, the vault or real money. A "does not pass"
changes nothing either.

**Limits known now.** Daily points come from closed trades, so a loss still open is not seen until it closes and the
worst day and worst fall understate what a marked book would show. Points add across books without compounding. A real
half-size trade may not be possible where the engine's size is already at its 1x floor; the halving here is counting.
The three legs are three stretches of one history of eight markets that largely moved together; they are not three
independent tests.

### Changes from the brief, made before registering
- Segments do not overlap: h2 ends at 2025-11-10 (H68's "second half" ran to the end), and the holdout leg ends at
  2026-11-10, so the 14 days that prompted the idea (the forward slice) are in no leg of the pass condition.
- The pass condition also needs V1's total above zero in each leg. With a negative total a "higher" ratio can come from
  a deeper fall, which is not better. The report will also say what the brief's wording alone (ratio higher in the three
  legs, 85% of the total) gives; the registered condition above is the one that decides.
- What happens when V0's total over all history is zero or negative is defined (leg 4).
- Two partner trades opened at once: both at half (the brief did not say); the strict reading is shown as V1s.
- "Open" is defined to the bar, and V2's order among trades entered at once is fixed.
- Added, descriptive only: the random-halving placebo, the halved-against-full table, the per-pair shares.
- Data run to the end of the shared store (24 Nov 2026), not H68's cut of 21 Nov, so the forward slice holds 23 Nov;
  the lean loader replaces `h59_half_be.prep_cut` for memory (the laptop has about 2 GB free); H68's numbers are
  reconciled on the trades closed by its cut.

**Code:** `research/h111_pair_bets.py`, tests `tests/test_h111_pair_bets.py`. Output: `research/out/h111_pair_bets/`
(`report.md`, `results.json`).

### H111 results (24 Nov 2026, books run 12:24-12:32 UTC on the laptop, analysis 12:33 UTC; `research/out/h111_pair_bets/report.md` + `results.json`; registered in commit 7c8e63e, its stated time corrected in 39b0f9c, both before any number)

**Verdict by the registered condition: V1 (pair-half) DOES NOT PASS.** None of the four legs is met. Ratio = total
points / worst fall; a point is one percent of one book's own money, added over the eight books by the day a trade closed.
- h1 (2020-02-05 to 2023-06-07): V1's ratio +0.54 against V0's +0.65: NO (V1's total +88.4, above zero).
- h2 (2023-06-08 to 2025-11-10): ratio -0.38 against -0.65, higher, but V1's total is -54.2: NO.
- Holdout (2025-11-11 to 2026-11-10): ratio -0.66 against -0.43, total -98.6: NO.
- Total kept: V1 -26.9 points over all history against V0 +18.1: NO.
By the brief's wording alone (no above-zero requirement) it does not pass either (h1 no, h2 yes, holdout no, total no).

Each cell: total points, worst day, worst fall, ratio.

| Variant | All | h1 | h2 | Holdout | Forward (2026-11-11 on) |
|---|---|---|---|---|---|
| V0 current | +18.1, -40.3, 466.6, +0.04 | +168.2, -40.3, 259.3, +0.65 | -136.9, -22.2, 209.3, -0.65 | -85.7, -27.1, 200.5, -0.43 | +72.5, -3.0, 3.0, +24.24 |
| V1 pair-half (primary) | -26.9, -27.0, 308.5, -0.09 | +88.4, -27.0, 163.3, +0.54 | -54.2, -16.7, 141.6, -0.38 | -98.6, -19.1, 148.7, -0.66 | +37.5, -3.1, 4.6, +8.19 |
| V1s, ties full (descriptive) | -53.1, -33.8, 369.4, -0.14 | +101.8, -33.8, 179.0, +0.57 | -90.9, -16.7, 143.1, -0.64 | -113.7, -24.5, 155.9, -0.73 | +49.7, -2.1, 2.1, +23.48 |
| V2 direction cap (descriptive) | +10.1, -36.3, 254.5, +0.04 | +39.7, -36.3, 167.4, +0.24 | -23.2, -19.4, 169.9, -0.14 | -50.1, -27.0, 151.9, -0.33 | +43.8, -5.5, 10.9, +4.01 |

5,971 closed trades (5,007 on the six pair markets). V1 halves 3,667 (506 of them by the tie rule), V1s 3,161; V2
drops 1,391. V1's mean size is 0.69 of V0's.

**Descriptive.**
- **Placebo (2,000 draws, the same number of trades halved at random per market and period):** share of draws with a
  ratio at least V1's: all 71%, h1 52%, h2 36%, holdout 97%, forward 97%. Which trades are halved does not matter.
- **Halved against full, pair markets, mean points a trade at full size:** halved +0.025 (3,667 trades, 44% won), left
  full -0.083 (1,340, 40%); h1 +0.087 / +0.028, h2 -0.129 / -0.081, holdout +0.050 / -0.629. The trade that opens second
  is not the worse trade.
- **Five or more markets on one side** (15-minute grid, 2021-01-12 on, when all eight books have started): 77% of the
  time (long 51%, short 27%); h1 83%, h2 75%, holdout 69%, forward 100% (all short). Largest same-side count: 4 22%,
  5 34%, 6 25%, 7 15%, 8 3% of the time.
- **Pairs, correlation of daily points (all days / only days both closed a trade), share of time on the same side:**
  BTC+ETH +0.25 / +0.47, 81%; gold+silver +0.16 / +0.33, 76%; WTI+Brent +0.51 / +0.73, 91%.
- **The 20 worst V0 days:** on 17 both members of at least one pair lost (BTC+ETH 9, gold+silver 6, WTI+Brent 11),
  against 15.8% of all days and 34% of losing days. The 20 days sum to -533.6 points in V0, -325.0 in V1, -413.7 in V2.
- **V2:** the trades it drops made +0.006 points a trade against +0.002 for the ones it keeps (h1 +0.176 / +0.018,
  h2 -0.228 / -0.014, holdout -0.231 / -0.081). A real book that skips a trade would trade differently afterwards.
- **Per market, V0 points over all history:** BTC -162.2, ETH +191.8, gold -5.1, silver -66.5, USDJPY +18.1, S&P 500
  +21.1, WTI +34.7, Brent -13.7.
- **Forward, 23 Nov:** the replay closed seven trades that day, five at the stop, for +1.2 points (-$480); V1 makes it
  -3.1 points (it halves the two winning oil trades and two of the five stops).

**Reconciliation with H68.** The trades closed by 2026-11-21 13:45 UTC: 5,963 trades, +22.5R (BTC+ETH 2,074, -7.7R; the
other six 3,889, +30.3R): H68's figures exactly. Every book equalled `run_challenger("b_targets")`.

**Checks.** `tests/test_h111_pair_bets.py` (11 tests on made-up trades). The V1, V1s and V2 choices on the real trades
were recomputed by a separate brute-force pass over every pair of trades and are identical.

**Deviations from the registration:** none in the rule, the segments, the measures or the pass condition. Choices
made with the code: the books are run one group per process and their trades cached, so the evidence store is held
for seconds (crypto 3 minutes, 54 refits); a trade stopped inside the bar that opens at T counts as open at T (the
registered definition), so a partner trade entered at that bar's open is halved; the 5+ table counts a 15-minute slot
when a trade is open during any part of it and includes the trades still open at the end; the correlation "all days"
runs from the day both members have started. Before the full run the USDJPY group was run alone as a smoke test
(`out/smoke`, numbers not reported).

**Reading.** History agrees with the audit that the eight books are largely one bet: five or more on one side three
quarters of the time, and the worst days are days on which both members of a pair lose. But counting the second trade
of a pair at half did not improve the result for the risk taken: it cut the worst fall by 34% while cutting size by
31%, which is what betting less on every trade does, and random halving did as well. The reason is that the second
trade of a pair is not a worse trade than the first. Under it all the Setups book is flat on this history (+18 points
in almost seven years, worst fall 467; negative in h2 and in the holdout), as H65 and H68 found, and no sizing rule
makes a flat book a good one. No forward shadow is proposed on this condition. If smaller falls are wanted, a smaller
size on every trade does the same more simply; that is a sizing decision for the owner, not a finding of this study.
A replay on history is post-mortem material, not validation. Nothing in the engine, the books or the vault was changed.

**Limits.** Closed trades booked on the closing day (a marked book would show larger worst days and falls); points
added across books without compounding; "half size" is counting (the engine never sizes below 1x); one definition of a
pair bet tested; the three legs are parts of one history and no part of it was unseen for this book; the replay's
forward days were not matched trade for trade with the live record (live 23 Nov: five stops, -$2,086).
## H112. An entry bar set per market, for the six markets where a 5-point Lead is out of reach (registered 24 Nov 2026, about 12:20 UTC, before any H112 code existed or any H112 number on history was computed)

**Prompted by:** the live audit of 24 Nov 2026 (`research/out/live_audit_20261124/report.md`, finding 2 and study C) and
the owner, 24 Nov 2026: a study on history of "an entry bar set per market, for the six where 5 points is never
reached". Research only: nothing in the engine, the books or the vault changes, whatever the result. A pass leads only
to a PROPOSAL for a forward PAPER shadow book, registered on its own and needing the owner's word; it never changes a
live book or the vault.

**Words.** The *Lead* is P(up first) minus P(down first) in points (`policy.decide`: `edge`, times 100). A *real call*
is an entry from flat because the better side's Lead cleared the entry bar (the book's entry word is `ENTER`). A
*forced entry* is the entry the mandate makes after `idle_max` (4) flat sessions when no side cleared the bar (entry
word `FORCED`); it goes with the higher-timeframe bias, else with the 4h/daily trend. A *flip* (`FLIP`) leaves a held
side for the other. *R* is the book's own `r_mult`: a trade's result net of fees over its risk at the entry stop.

**Known before registering (live; already seen, quoted as such).** In 14 live days (10 to 24 Nov 2026) the Lead never
cleared 5 points on the six non-crypto markets: largest reading gold 4.6, silver 4.7, USDJPY 5.0, S&P 3.5, WTI 4.2,
Brent 4.5. Every trade there was a forced entry. On BTC and ETH it was above 5 in about half of all steps. On oil the
Lead pointed up in 85% to 90% of steps while price fell; readings of 2 to 5 points were on the right side 24 hours
later 26% (WTI) and 38% (Brent) of the time; on USDJPY 34% to 38%.

**Known before registering (history; the prior expectation for this study is LOW, and the report must say so).**
- H65 (post-mortem of the Setups book, 5,964 trades to 21 Nov 2026): the entry word is "not consistent": real calls
  (ENTER) -5.6R, forced entries -1.5R over 4,461 trades; "the forced entry is neither the problem nor a help". The lead
  in the odds did not hold up across halves (top third +69.7R in all, -3.7R in the second half).
- H68: on the other six markets "signals rarely clear the entry bar by themselves": a book that waits for a real call
  after a stop-out sat flat for months or years (gold, silver and SPX flat 96-99% of the second half). So it is already
  half known that the bar is out of reach on history too, at least from 2023 on; step 1 measures it. H68 also printed
  the current rule on the other six: first half 1,962 trades, -15.1R; second half (2023-06-08 to 2026-11-21) 1,927,
  +45.4R; holdout (2025-11-11 on) 488, +8.8R; forward (2026-11-11 on) 12, +13.0R.
- H80: the Setups book is NOT distinguishable from the same book on time-shifted odds (p 0.1143). H81b: its side is a
  little better than its own recent mix (p 0.0338). H82b: its exact entry bar is NOT distinguishable from a random bar
  of the next typical gap (p 0.0802). So the odds, which the Lead is made of, add little that can be measured.
- H92 (walk-forward of `theta_enter`, eight markets): on 2020-02 to 2023-06 LOWER entry bars were worse (0.02: -17.4R,
  0.03: -10.0R, 0.05: +25.2R, 0.08: +32.1R, 0.10: +33.4R); the chosen 0.10 did not pass on 2023-06 to 2025-11 (p 0.031
  against 0.0042). On that test period the current rule made, per market: XAUUSD +27.5R (247 trades), XAGUSD -1.7
  (248), USDJPY +21.3 (299), SPX +18.5 (106), WTI -21.4 (262), BRENT -26.1 (284); doubling the entry bar left SPX
  exactly as it was and gold and silver nearly so (their entries there are already almost all forced).
- H93: a flip bar of 5 points instead of 10 was much worse on 2020-02 to 2023-06 (pooled -149.7R on 5,182 trades
  against +25.2R on 2,945): a low flip bar churns. H94: a counter-bias bar of 5 instead of 15: +13.6R against +25.2R.
  H100: a high-risk bar of 5 instead of 10 was the choice on the first period (+54.9R against +25.2R) and did not pass
  later (p 0.12).
- The holdout (2025-11-11 on) is NOT sealed for this book: H65, H67, H68 and H72 have read it. H90-H101 did not.
None of these studies set a bar per market, scaled the bars together, or looked at the six markets alone under a
lower bar. No H112 number exists.

**Data and loader.** The evidence store and the cached fits, read only. Each market group ends at its last stored
session at or before **2026-11-24 04:30 UTC** (the end of the laptop's copy of the live box's store). The loader is
`research/queue/walkforward.prep_cut_lean` (H90-H101's line-for-line, checked copy of `h59_half_be.prep_cut` that keeps
only the columns the Setups book reads). A market's *steps* are its stored sessions from its first decided session
(`lo` as in H68: the first session with odds, at or after the birth date) that have odds. **Segments, by session time,
disjoint:** h1 = up to 2023-06-07 23:45; h2 = 2023-06-08 to 2025-11-10 23:45; holdout = 2025-11-11 to 2026-11-10
23:45; forward = 2026-11-11 to the cut.

**Step 1, descriptive, all eight markets, per segment (no bar, decides nothing).** The share of steps with |Lead| at or
above 5.0 points; the 50th, 75th, 90th, 95th and 99th percentile and the largest value of |Lead|; and, in the current
Setups book (`shadows.run_challenger("b_targets")`, one continuous book per market from its first decided session, as
the engine runs it), the entries by entry word (ENTER / FORCED / FLIP: count and share), by the segment of the entry
bar. The forward segment is set beside the live audit's figures.

**Step 2, the fit, on h1 ONLY.** p* = the share of steps with |Lead| >= 5.0 points on BTC and ETH pooled in h1 (all h1
steps of both coins in one count). For each of XAUUSD, XAGUSD, USDJPY, SPX, WTI, BRENT: bar_m = the (1 - p*) quantile
of that market's |Lead| over its h1 steps (`numpy.quantile`, linear), so that the bar is cleared in h1 as often as 5
points is on crypto; rounded to 0.01 point; never below 1.00 point (the floor). No cap: if a market clears 5 points
MORE often than crypto in h1, its bar rises. Nothing after 2023-06-07 enters the fit, and no trade result enters it.

**Step 2, the test.** scale_m = bar_m / 5. Three rules per market, each the engine's own `b_targets` rule run by
`shadows.run_challenger("b_targets", ..., cfg=...)` with only the named numbers of the cfg changed (nothing under
`engine15/` is edited):
- **current:** the cfg as it is (`theta_enter` 0.05, `theta_enter_shock` 0.10, `theta_flip` 0.10, `theta_counter` 0.15;
  the run stops if the config holds other values).
- **PRIMARY, all bars scaled:** `theta_enter`, `theta_enter_shock`, `theta_flip` AND `theta_counter`, each times
  scale_m. How the code derives the counter-bias bar: it is a separate number, `cfg["theta_counter"]` (15 points); an
  entry against the higher-timeframe bias needs `max(the entry bar, theta_counter)`. Left at 15 it could never be met
  on these markets, so it is scaled with the others. `theta_enter` has a second role in `policy.decide`: a held
  position against the bias whose own Lead is below `theta_enter` is flipped to the bias side; that moves with it.
- **Secondary, descriptive, no bar:** only `theta_enter` times scale_m (its second role moves with it); the other
  three as they are.
BTC and ETH are unchanged and are not part of step 2. Each book is run on h2, on the holdout and on the forward
segment separately, **each starting flat with $10,000 at the segment's first session** and ending at its last (never
on h1). Read-outs per rule, per market and pooled over the six, per segment: closed trades (by entry bar; a trade
still open at the segment's end is in the marked equity, not in R), entries by word and the share of real calls, share
won, sum of R, mean R, net dollars (marked equity at the end less $10,000), worst fall of the marked equity (pooled:
of the six books' equity summed, as H68), share of sessions flat; mean R and sum of R by entry word. Also per segment:
the share of steps with |Lead| at or above bar_m (is the fitted bar still cleared about as often as on crypto after
h1?), beside the crypto share at 5 points in that segment.

**PASS condition for the PRIMARY, fixed now, before any number. PASS only if all three hold, pooled over the six
markets:** (1) its sum of R is higher than the current rule's in h2; (2) its sum of R is higher than the current
rule's in the holdout; (3) in the PRIMARY book in h2 its real-call entries (ENTER) have a higher mean R than its
forced entries (FORCED), with at least 30 closed trades in each of the two classes (fewer: the leg is not met).
Anything else is "does not pass". The forward segment (about 13 days) and every per-market number are descriptive.

**Descriptive only (does not enter the pass).** For h2 and for the holdout, pooled over the six: the difference in sum
of R (primary less current) with a month-clustered bootstrap interval (calendar months of the entry bar, UTC, months
with no trade count as zero, the six markets' trades of a month drawn together; 10,000 draws, seed 20261124112; 2.5th
to 97.5th percentile). It says how much of a "higher" could be noise; it changes no verdict.

**What a pass would and would not say.** The legs are point comparisons on history, on six markets that share days
and trends; a pass says the pattern is worth a forward paper shadow book and nothing more. A replay is post-mortem
material, not validation. If it does not pass, a lower bar on these markets is not supported on this history.

**Ledger.** One primary test (three legs, no p-value). The secondary rule, the forward segment, the per-market rows
and the bootstrap interval are looks that pass nothing. Three sibling studies (H111, H113, H114) run in parallel on
other questions; each keeps its own ledger.

**Smoke run.** Before the full run the script is run once on the `fx` group alone (`--smoke`, USDJPY, into
`research/out/h112_entry_bar_per_market/smoke/`, labelled SMOKE) with a made-up scale of 0.5 because p* needs crypto;
it is read only to see that the code runs and the files are written. None of its numbers is a result or is reported.

**Changes from the brief, made before registering.**
- Segments are disjoint (the brief, like H68, let h2 run to the end and the holdout include the forward days). The
  two legs of the pass on sum of R then rest on separate data: 2023-06-08 to 2025-11-10, and 2025-11-11 to 2026-11-10.
- Each compared book starts flat with $10,000 at its segment (as H90-H101 did), not as one book carried from 2020:
  net dollars and worst fall are then comparable between rules, and nothing a rule did in h1 carries into a judged
  segment. Step 1 keeps the continuous book, since it describes the book as the engine runs it.
- "Real call" is the entry word ENTER; FLIP entries are counted apart (a flip can be a call from the other side or
  the rule that turns a position back to the bias; the trade record does not say which). Leg (3) needs 30 trades in
  each class.
- The counter-bias bar is a separate number and is scaled in the PRIMARY (the brief left this open).
- No cap on bar_m above 5 points (the brief gave only the floor).
- The cut is the end of the laptop's store copy (2026-11-24 04:30 UTC), not H68's 2026-11-21 13:45, so the forward
  segment covers the audit's days. Sessions after the last cached fit are refitted by the engine's own cached walk.
- The loader is the lean copy (the laptop has about 2 GB of memory free).
- Added, descriptive: the largest |Lead| per segment, the share of steps clearing the fitted bar after h1, and the
  bootstrap interval.

**Code:** `research/h112_entry_bar_per_market.py`; tests `tests/test_h112_entry_bar.py`. Output:
`research/out/h112_entry_bar_per_market/report.md` + `results.json`.

### H112 results (24 Nov 2026, run 12:25-12:28 UTC on the laptop, 210 s; registration committed first as `972b24b`; `research/out/h112_entry_bar_per_market/report.md` + `results.json` + `reading.md` + `extra_lead_by_period.json`)

**Verdict by the registered condition: the PRIMARY rule (all bars scaled) DOES NOT PASS.** Pooled over the six
markets: (1) sum of R in h2 +2.1R against the current rule's +18.3R: NOT higher; (2) sum of R in the holdout +4.5R
against +3.2R: higher; (3) in the new book in h2 real calls -0.049R a trade (142 trades) against forced entries
-0.000R (1,271): NOT higher. Two of three legs fail. The prior expectation was low (H65, H80, H82b, H92, H93) and the
result agrees with it. A replay is post-mortem material, not validation; nothing live was changed.

**Step 1: is the 5-point bar out of reach on history too?** Share of steps with |Lead| >= 5 points, h1 / h2 / holdout
/ forward, then the largest reading in the forward days (live audit's in brackets):
- BTC 20.9% / 13.4% / 14.9% / 71.3%; ETH 21.1% / 13.0% / 15.1% / 76.4%.
- Gold 9.26% / 0.98% / 0.00% / 0.00%, 4.53 (4.6). Silver 8.65% / 0.95% / 0.00% / 0.00%, 4.70 (4.7).
- USDJPY 8.72% / 0.74% / 0.23% / 0.00%, 4.11 (5.0). S&P 500 1.91% / 0.01% / 0.00% / 0.00%, 3.62 (3.5).
- WTI 28.83% / 13.72% / 22.71% / 0.00%, 4.30 (4.2). Brent 29.26% / 14.33% / 22.59% / 0.00%, 4.61 (4.5).
So on gold, silver, USDJPY and the S&P the bar has been out of reach since about mid-2023 (under 1% of steps), though
not in 2020-21. On oil it is NOT out of reach: the Lead cleared 5 points more often than on crypto in h1 and in the
holdout year; the live 14 days were a quiet spell. The current Setups book's entries (continuous book; real calls /
forced / flips): the six pooled h1 324 / 1,512 / 126 (17% real calls), h2 108 / 1,288 / 43 (8%), holdout 34 / 439 / 5
(7%), forward 0 / 16 / 0; BTC + ETH 39%, 34%, 29%, 82% real calls. On gold, silver, USDJPY and the S&P real calls are
0% to 2% of entries from h2 on; on WTI and Brent 16% to 22%.

**Step 2, the fit (h1 only).** p* = 21.00% (BTC + ETH, 233,742 steps). Fitted entry bars in points (factor): gold 3.25
(0.650), silver 3.20 (0.640), USDJPY 3.63 (0.726), S&P 500 2.43 (0.486), WTI 6.74 (1.348), Brent 6.96 (1.392). For oil
the registered rule RAISED the bar. Share of steps at or above the fitted bar, h1 / h2 / holdout / forward: gold 21.0%
/ 4.6% / 1.1% / 9.6%; silver 21.0 / 4.5 / 1.3 / 15.4; USDJPY 21.0 / 6.3 / 1.9 / 2.6; S&P 21.0 / 6.3 / 3.4 / 0.9; WTI
21.0 / 10.4 / 19.9 / 0.0; Brent 21.0 / 10.6 / 19.2 / 0.0. The bars did not stay "cleared as often as on crypto" after
h1, because the Lead on the four markets keeps shrinking.

**Step 2, the replay, pooled over the six** (each book fresh and flat with $10,000 a market at its segment). Cells:
trades, share that are real calls, share won, sum of R, mean R, net dollars, worst fall of the six books summed.

| Rule | h2 (2023-06-08 to 2025-11-10) | holdout (2025-11-11 to 2026-11-10) | forward (2026-11-11 on) |
|---|---|---|---|
| current rule | 1,446, 7%, 42%, +18.3R, +0.013R, +$332, -21.1% | 486, 7%, 42%, +3.2R, +0.007R, -$11,579, -34.4% | 23, 0%, 61%, +12.6R, +0.546R, +$4,176, -2.1% |
| all bars scaled (PRIMARY) | 1,463, 10%, 42%, +2.1R, +0.001R, -$2,693, -25.4% | 483, 8%, 42%, +4.5R, +0.009R, -$11,834, -33.9% | 23, 9%, 61%, +12.7R, +0.553R, +$4,181, -2.2% |
| entry bar only (secondary) | 1,468, 10%, 42%, -2.7R, -0.002R, -$4,087, -25.4% | 482, 8%, 42%, +5.9R, +0.012R, -$10,740, -32.4% | 23, 9%, 61%, +12.7R, +0.553R, +$4,181, -2.2% |

By entry word in the PRIMARY book: h2 real calls 142, -0.049R, -7.0R; forced 1,271, -0.000R, -0.3R; flips 50,
+0.188R, +9.4R. Holdout: real calls 40, -0.083R; forced 438, +0.014R; flips 5.
Month-clustered bootstrap of the gap to the current rule (descriptive): PRIMARY h2 -16.1R (95% range -54.6 to
+19.4, 30 months), holdout +1.3R (-8.8 to +9.8, 13 months); secondary h2 -21.0R (-61.2 to +16.5), holdout +2.7R
(-8.3 to +12.1). No gap can be told from chance in either direction.

Per market, sum of R, current rule against PRIMARY (trades): h2 gold +27.5 (247) / +26.5 (250); silver -1.7 (248) /
-7.0 (262); USDJPY +21.3 (299) / -5.6 (319); S&P +18.5 (106) / +29.5 (100); WTI -21.4 (262) / -14.3 (254); Brent -26.1
(284) / -27.0 (278). Holdout: gold +9.5 / +9.5; silver +8.0 / +7.8; USDJPY -8.8 / -6.5; S&P -4.4 / -0.8; WTI -4.4 /
-9.2; Brent +3.3 / +3.6. USDJPY carries most of the h2 gap.

**Check.** The current rule's h2 numbers per market equal H92's test-period table exactly (trades and sum of R, all
six markets): an independent check of the loader and the book for h2. There is no such check for the holdout.

**Deviations and what was done after the registration.**
- None from the registered fit, rules, segments, read-outs or pass condition.
- The smoke run (fx only, made-up scale 0.5) came before the full run, as registered. It showed USDJPY's real step-1
  numbers and its books at the made-up scale. After it only the report's wording and layout were changed (a missing
  mean printed as "-R"; the loader's lines kept in results.json). No rule or read-out was changed.
- The cached fits did not hold the last year for crypto (54 weekly refits) and fx (38): those were refitted on the
  laptop by the engine's own cached walk, as the registration allowed. Metals, index and energy came wholly from cache.
- **Added after the results, NOT registered, descriptive** (`--by-year`, `extra_lead_by_period.json`): the share of
  steps at 5+ points per calendar year. Gold 20.6% (2020), 10.5%, 2.2%, 1.1%, 0.4%, 0.8%, 0.0% (2026), last reached
  22 Apr 2025; silver 18.2% to 0.0%, last 25 Sep 2025; USDJPY 7.3%, 14.7%, 4.4%, 3.7%, 0.5%, 0.8%, 0.2%, last 5 Nov
  2026; S&P 3.8% (2021), 0.9%, then 0.0%, last 27 Sep 2023; WTI 50.7%, 30.3%, 17.5%, 17.9%, 10.5%, 8.8%, 25.3% (2026),
  last 3 Nov 2026; Brent the same shape, last 2 Nov 2026. Oil in 2026 by month runs from about 0% (June, July) to 63% (February).
- The history lock was free at the smoke run and held by a sibling study for under two minutes before the full run
  and before the extra look (9 s and 54 s old on arrival; waited, not removed).

**Not verified.** The laptop's refits for the last year of BTC, ETH and USDJPY were not compared with the live box's
fits. The replay's largest forward reading on USDJPY (4.11) is below the live audit's 5.0; the audit's window starts a
day earlier and the reason was not checked. Why dollars and R disagree in the holdout (+3.2R, -$11,579; silver +8.0R,
-$3,783, worst fall -72.7%) was not checked trade by trade; the likely reason is that a position is never smaller
than 1x, so far stops cost more than 2% (the audit's finding 5). Only the study's own 10 tests were run, not the full
suite; no file under `engine15/` was changed.

**Reading.** On four of the six markets (gold, silver, USDJPY, the S&P) history agrees with the live audit: since
about mid-2023 the 5-point bar is almost never reached and nearly every entry is forced. On oil it is reached often
and the live fortnight was a quiet spell. A bar fitted per market on 2020 to mid-2023 does not fix this: the Lead on
the four markets kept shrinking, so the fitted bars were cleared in 5% to 6% of later steps, not 21%, and real calls
rose only from 7% to 10% of entries. Where the lower bar did add real calls they were not better than forced entries
(-0.049R against 0.000R a trade), and the book as a whole was 16R lower in h2 and 1R higher in the holdout, both
inside the noise. Nothing here supports a per-market entry bar, and no forward shadow book is proposed. It does not
show that a lower bar harms either. Limits: one replay; six markets that share days and trends; a holdout already
read by H65, H67, H68 and H72; a forward slice of two weeks; a bar fitted on how often the Lead is large, not on
whether it was right. A bar that follows the recent Lead would be a different rule needing its own registration, with
a low prior for the same reasons. Why the odds on these four markets have moved so close to even since 2022 was not
studied. Nothing in the engine, the books or the vault was changed.
## H113. BTC and ETH: how fast the Lead turns after a capitulation low, and whether Setups shorts opened in the 48 hours after a capitulation rebound do worse than the book's other shorts (registered 24 Nov 2026, about 12:25 UTC, before any H113 number on history was computed)

**Prompted by:** the live audit of 24 Nov 2026 (`research/out/live_audit_20261124/report.md`, study E): on BTC and ETH
the Lead pointed down in 98% of steps over 14 live days, including through the rebound from the 21 Nov low (BTC
55,130), and trades opened after that low lost in all three books (main 2 of 6 won, -$1,455; Setups 0 of 3, -$1,555;
B trail 2 of 6, -$1,549). The owner asked for a study on history of "how fast the Lead turns after a capitulation
low". Research only: nothing in the engine, the books or the vault changes, whatever the result. A pass leads only to
a PROPOSAL for a forward paper shadow book ("no new short for 48 hours after a capitulation rebound"); it never
changes a live book or the vault.

**Words.** The **Lead** is the engine's P(up first) minus P(down first), in points (`engine15/policy.py`: `edge`,
times 100). Above zero it favours up, below zero it favours down. From flat the engine goes long by itself only at
+5 points (+10 when risk is high, +15 against the higher-timeframe bias). **R** is a trade's result divided by what it
risked at its entry stop, after fees (the book's `r_mult`). The **Setups book** is the paper book `b_targets`.

**Known before registering (what earlier studies already answer).**
- H71 (the engine's readings in an oversold state): in oversold bars the odds led UP by 5 points or more in 0.1% to
  0.2% of bars and never by 15; they led DOWN by 5 or more in 53% to 62%. The Lead did not carry confirmed
  information about the next 24 hours there. So "the Lead mostly stays down while a market is oversold" is ALREADY
  KNOWN. H71 counted bars in a state; it did not measure time from a low.
- H66 (sudden rallies while short): in 505 rallies of +5% in 24 hours while the Setups book was short, it lost in 93%,
  opened a NEW short inside the rally in 24%, and turned long within the day in 26%. The rallies were picked with
  hindsight on price and were not tied to a capitulation; the shorts' own R was not compared with other shorts.
- H65 / H67 / H72: the book earns with its market's 30-day move and loses against it; shorts as a whole averaged
  -0.062R. A short just after a capitulation is WITH the 30-day move, the cell that was positive. So H113's claim is
  that the first 48 hours after a capitulation rebound are an exception inside a cell that earns on average.
- H68: forced entries right after a stop-out lost on BTC and ETH (762 trades, -0.070R); `b_wait_stop` runs forward.
- H70: 18 rebound-long rules out of an oversold state all lost after fees in 2020-02 to 2023-06.
- H107 (the event definition reused here): a long at rule A's trigger made -0.127R a trade in the first half (83
  trades) and +0.246R in the second (40 trades), flat over all (123, -0.006R). Two things follow before any H113
  number: (i) bounces off new lows kept failing in the first half (2022 above all), so shorts opened there may well
  have done fine: the claim is NOT expected to hold in the first half on that evidence; (ii) with about 40 triggers
  taken in the second half, the second half may hold fewer than 20 in-window shorts.
- The 21 Nov 2026 event itself (the audit and H107's event read): rule A fired on both coins at the 06:45 UTC close;
  the books' shorts after the low lost. That event shaped H107's rule and prompted this study. It is NOT part of the
  test and is reported apart.

**What H113 adds.** (a) Time measured from a capitulation low: how many hours until the Lead first favours up, the
Lead's path hour by hour, and how often it still favours down one, two and three days later. No earlier study measured
this. (b) A test, without look-ahead, of whether the Setups book's shorts opened in the 48 hours after H107's rule A
fires do worse than its other shorts. H66 and H68 are near it but answer different questions.
**What H113 does not repeat.** Whether a LONG at the trigger pays (H107: it does not hold up). Whether the Lead
predicts anything in an oversold state (H71: not confirmed).

**Data.** BTCUSDT and ETHUSDT. The laptop's copy of the live box's data (`data/`: 15-minute bars, funding, the
evidence store to 2026-11-24 04:30 UTC) and a private copy of the cached weekly fits, all read only. The Lead per
15-minute close is `prep["odds"]` from `research/h59_half_be.py::prep_cut` (the frame H65 to H68 and H71 used; each
fit is made only from rows graded before the week it serves). **Known difference from the live engine:** this replay
frame has no trust cap (live, since v5.2, no card holds more than 40% of the say), so the replay Lead is close to but
not the same as the live Lead. The Setups book is the engine's own `shadows.run` under the rule of
`shadows.CHALLENGERS["b_targets"]` (`{"targets": True, "early": True}`), as in `research/h68_wait_after_stop.py`,
from the first close with odds to the store's last session.

**Segments, by the time of the bar that decides (UTC).** First half: the first close with odds (2020-02) to 2023-06-07
23:45. Second half: 2023-06-08 00:00 to 2025-11-10 23:45. Holdout: 2025-11-11 00:00 to 2026-11-18 23:45. The event
apart: from 2026-11-19 00:00 (H107's event window). The halves are H107's.

**The capitulation trigger (part b), reused from H107 exactly.** `research/h107_capitulation_rebound.py::features`
with its registered settings (`REG`), column `"A"`: at the close of bar k, a fresh 30-day low within the last 4 hours,
that low at least 10% under the close a week earlier, the close at least 2 x ATR(1h) above that low, and not all true
one bar earlier. The script imports that function; it defines no trigger of its own. Each coin uses its own trigger.

**Part (a), descriptive, hindsight allowed, decides nothing.** A **confirmed capitulation low** is a 15-minute bar k
whose low (1) is the lowest of the 30 days up to it (H107's `lowN`, 30 days of bars needed), (2) is at least 10% under
the close a week earlier (H107's `cref`), and (3) is not undercut in the next 192 bars (48 hours). Events on one coin
are kept in time order, and one is dropped if it comes less than 7 days after the last one kept. The Lead must exist
at bar k. For each event, with the Lead read at each close from 24 hours before to 72 hours after:
- the median Lead by hour (and the quartiles);
- the hours from the low bar's close until the Lead is first at or above 0 (and first at or above +5), within 72
  hours; an event where that never happens is counted as "not within 72 hours", and the median is given only if at
  least half the events turned;
- the share of events in which the Lead is below 0 at +24h, +48h and +72h, and the share of the 72 hours spent below 0;
- the price at +24h, +48h and +72h against the low and against the low bar's close. By construction price cannot be
  under the low in the first 48 hours, so these moves flatter the low; they are a description, not a forecast.
Per segment, each coin and both together (BTC and ETH lows mostly fall on the same days, so "both" is not twice the
evidence). As a yardstick: the share of ALL closes in each segment with the Lead below 0. Without hindsight, the same
shares anchored at rule A's trigger instead of the low. The 21 Nov 2026 lows are shown apart.

**Part (b), the test, no look-ahead.** A trigger at the close of bar k opens a **post-capitulation window**: that close
and the next 191 closes (48 hours; the bars H107's long would hold). A later trigger extends it. A short of the
Setups book is **in-window** if the close that decided it (the bar before its entry bar `i_in`) lies inside a window
of its own coin; every other short of the book on BTC and ETH is an "other short". All shorts count, whatever the
entry word (ENTER, FORCED, FLIP). The measure is the mean of `r_mult`, BTC and ETH trades pooled.
**The claim:** shorts opened inside the window do worse than the book's other shorts.
**PASS condition, fixed now.** In the first half AND in the second half: at least 20 in-window shorts, their mean R
below zero, AND their mean R below the other shorts' mean R of that half. Fewer than 20 in either half: "too few to
judge" (no pass). Anything else: "does not pass".
**The holdout** is opened for part (b) only if both halves pass (as H70 and H71 did: nothing to confirm, nothing
opened). It then confirms only if it holds at least 10 in-window shorts with a mean R below zero and below the other
shorts' mean R there; otherwise the proposal does not stand. If the halves do not pass, the in-window split is not
computed on the holdout and it stays sealed for this question.
**The event apart.** Shorts decided from 2026-11-19 on, in the replay and (from the audit's copy of the live files,
if still on disk) in the live books, with the live Lead from the journal: descriptive only.

**Descriptive beside the test (decides nothing; first and second half only unless the holdout is opened):**
- a month-clustered bootstrap interval for (in-window mean R minus others' mean R): calendar months of the deciding
  bar, both coins together, 10,000 draws, seed 20261124, 95% percentile interval;
- the others restricted to the same coin-months as the in-window shorts (a like-for-like yardstick);
- each coin alone; by entry word; the first 24 hours of the window against the second;
- the mirror: the book's LONGS decided inside the window against its other longs (if they do worse too, the window is
  simply a costly time to trade, not a bad time to be short);
- the Lead at the entry of the in-window shorts; the number of triggers and the share of closes inside a window;
- windows of 24 and of 96 hours.
**Look-ahead guard.** For every trigger bar and 40 random bars per coin, `features` is recomputed on bars cut at that
bar and the flag must match the full run.

**Changes from the brief, made before registering.**
1. The second half ends at 2025-11-10 23:45, so it does not overlap the holdout (in H68 the second half ran to the end).
2. The holdout is opened for part (b) only if both halves pass, and needs at least 10 in-window shorts to confirm
   (the brief asked for "the same sign" with no count).
3. The holdout ends at 2026-11-18 23:45; everything from 19 Nov 2026 is the event apart.
4. Part (a)'s 10% test compares the LOW with the close a week earlier, not the close with the close, so that a
   confirmed low is H107's own first two conditions at the low bar, on H107's code.
5. The window is defined by the close that DECIDES the short (the trigger's close and the next 191), each coin by its
   own trigger, later triggers extending it; flips into a short count.
6. The replay runs to the store's last session (2026-11-24 04:30), not to 2026-11-21 13:45, so that the event can be
   shown. This changes nothing before 19 Nov 2026.
7. The descriptive read-outs listed above were added (the +5 bar, the yardsticks, the trigger-anchored path, the
   bootstrap interval, the mirror on longs, the 24- and 96-hour windows, the live journal for the event).

**Seen before this registration:** the audit report, the H107 code and results, the studies named above, the store's
time index (its first and last session) and file listings, and the first and last lines of the audit's journal copy.
No Lead path, no event list beyond H107's own results, and no split of the book's shorts has been computed.

**Code:** `research/h113_lead_after_capitulation.py`, tests `tests/test_h113_lead_after_capitulation.py`. Output:
`research/out/h113_lead_after_capitulation/` (`report.md`, `results.json`).

### H113 results (24 Nov 2026; build 12:21 to 12:24 UTC on the laptop, analysis about 20 s; `research/out/h113_lead_after_capitulation/report.md` + `results.json`; registration commit 5a2241c)

**Verdict by the registered condition: the two halves PASS; the holdout does NOT confirm; the proposal does not
stand.** Nothing in the engine, the books or the vault was changed.

**Part (b), the test.** Setups shorts decided inside the 48 hours after rule A's trigger against the book's other
shorts, BTC + ETH. Each cell: trades, share won, mean R, sum of R.
- First half: in-window 58, 43%, -0.085, -4.9R; others 428, 42%, -0.032, -13.9R. Difference -0.052R, month-clustered
  95% range [-0.502, +0.310]. Passes the three checks, by a margin that could be chance.
- Second half: in-window 37, 27%, -0.501, -18.5R; others 305, 41%, -0.093, -28.2R. Difference -0.409R [-0.744, -0.033].
- Both halves passed, so the holdout was opened. Holdout (2025-11-11 to 2026-11-18): in-window 28, 61%, +0.588,
  +16.5R; others 165, 45%, +0.079, +13.0R. Difference +0.509R [-0.234, +1.591]. The opposite sign: not confirmed.
- Like for like (other shorts in the same coin-months): +0.325R (162), +0.218R (124), +0.518R (42) in the three
  segments. In the halves the in-window shorts were far under the other shorts of the same months; in the holdout
  they were level with them.
- Beside the test: BTC in-window -0.158 / -0.822 / +0.370; ETH +0.000 / -0.282 / +0.805 (first half / second half /
  holdout). Forced entries in the window -0.549 (15) / -0.541 (20) / +1.247 (10); entries on a signal +0.077 (43) /
  -0.454 (17) / +0.222 (18). No flip into a short fell in a window. The mirror cannot be read: the book opened only 3
  longs inside a window in the two halves. Windows of 24 and 96 hours give the same signs in every segment. Triggers
  120 / 61 / 61; 4.8% / 3.8% / 7.5% of closes lie inside a window.
- Not registered, added after the run, by calendar year (in-window shorts): 2020 11, -0.024; 2021 12, -0.511; 2022
  28, +0.249; 2023 10, -0.700; 2024 15, -0.751; 2025 22, -0.284; 2026 25, +0.678. They won in the two years of long
  falls and lost or were flat in the other five.
- Look-ahead guard: `features` recomputed on bars cut at 348 bars (every trigger bar, 40 random bars a coin), 0
  mismatches.

**Part (a), descriptive (hindsight).** 76 confirmed capitulation lows (BTC 34, ETH 42; 97 candidates before the 7-day
rule): first half 37, second half 28, holdout 11.
- Lead at the low: median -10.4 points; below zero in 99% of events.
- Hours from the low until the Lead is first at or above 0: median 19.9 (first half 15.0, second half 18.4, holdout
  37.0). Within 24 / 48 / 72 hours in 54% / 79% / 84% of events; never within 72 hours in 12 of 76.
- Still below 0 at +24h / +48h / +72h: 79% / 74% / 75% of events (holdout 100% / 82% / 100%). Median Lead -3.1 at
  +24h, -2.3 at +48h, -2.0 at +72h. Median share of the 72 hours spent below 0: 87%. Yardstick, all closes: the Lead
  is below 0 at 67% (first half), 55% (second half), 64% (holdout) of BTC closes; ETH the same within 2 points.
- At or above +5 within 24 / 48 / 72 hours: 8% / 14% / 29% of events (holdout 0 of 11). Median highest Lead in the 72
  hours +2.5.
- Price against the low at +24h / +48h / +72h, median: +6.3% / +8.3% / +8.8% (by construction not under the low for
  48 hours).
- Without hindsight, from the trigger that opens a window (87 of them): median 27.5 hours to the first reading at
  or above 0; still below 0 at +24h / +48h / +72h in 87% / 79% / 77%; price against the trigger's close +0.6% / +1.3% /
  +1.6% at the median (holdout -1.2% / -0.7% / -3.7%).
- Not registered: all 95 candidates before the event, without the 7-day rule, give the same picture (19.2 hours;
  78% / 75% / 78%).

**The 21 Nov 2026 event, apart (descriptive).** Rule A fired on both coins at the 06:45 UTC close. Live Lead (the
audit's copy of the journal): -11.3 (BTC) and -10.9 (ETH) at the low; first at or above 0 after 55.5 and 57.75 hours;
highest +4.9 and +5.5; price +11.7% and +12.7% above the low at +48h. Replay Lead: BTC touched 0 after 2 hours and
was below 0 again at +24h and +48h; ETH 57.75 hours. Over the 14 live days the replay Lead had the live Lead's sign
at 99% of 1,311 closes a coin and differed by 2.2 points on average. Live shorts decided inside the window: Setups
2, both stopped, -$1,254; B trail 4, all stopped, -$2,516; main 4, all stopped, -$2,361. Replay Setups book: 2
in-window shorts, both stopped (-1.05R, -1.04R). The 21 Nov lows are left out of part (a)'s tables by the 7-day rule
(a confirmed low on 15 Nov 2026 was kept on each coin); the event's read-outs use them all the same.

**Deviations and choices made with the code.** (1) The heading says "about 12:25 UTC"; the registration was committed
at 12:17 UTC by the laptop's clock (5a2241c), before the script existed. (2) The private copy of the fits held 301 of
the walk's 355 weekly fits (those to 2025-11-10); the other 54 were refitted on the laptop by the engine's own walk.
Check: the book's record to 2026-11-21 13:45 is 2,074 trades, -7.7R (BTC -66.9R, ETH +59.2R), exactly H67's and
H68's. (3) The trigger-anchored yardstick uses the trigger that OPENS a window (no trigger in the 192 bars before
it), since triggers come in clusters. (4) The event's lows are taken before the 7-day rule (above). (5) Added after
the run and marked so: the by-year table, the candidates without the 7-day rule, the check against H67. (6) The
build (the one run that loads the evidence store) ran once; the analysis, which reads only the saved Lead and trades, was rerun several times for the
report's layout and the additions in (4) and (5); the registered numbers were identical in every run. (7) In the holdout's
bootstrap 9,989 of 10,000 draws held both groups.

**Reading.** On part (a) the answer to the owner's question is: slowly. After a capitulation low the Lead touches
zero within about a day in half the events, but it does not stay; three days later it still favours down in three
events out of four, and it reaches the +5 points a long needs within three days in fewer than one in three. That
agrees with H71: the Lead follows the recent fall and does not call the turn. On part (b) the pattern the audit saw
on 21 Nov (shorts sold into the rebound lose) is there in both halves, clearly in the second and barely in the
first, and it is reversed in the holdout year, where the same shorts were the book's best. By year these shorts won
in 2022 and 2026, the years in which bounces off new lows kept failing, and lost or were flat in the other five.
The trigger does not tell the two kinds of bounce apart. So a rule "no new short for 48 hours after a capitulation
rebound" is not supported: no forward shadow is proposed. The holdout has now been read for this question and
cannot be a fresh check for a variant of it. A replay is post-mortem material, not validation.
## H114. USDJPY in the Setups book: a wider stop (3 barriers instead of 2), or leave the market out (registered 24 Nov 2026, 12:17 UTC, before any H114 code existed or any H114 number on history was computed)

**Prompted by:** the live audit of 24 Nov 2026 (`research/out/live_audit_20261124/report.md`, finding 9 and row F) and
the owner, 24 Nov 2026: "USDJPY: a wider stop, or leave it out of the Setups book". Research only: nothing in the engine,
the Setups book, the main book or the vault changes, whatever the result. A pass leads only to a proposal for a forward
PAPER shadow book; leaving a market out is the owner's decision.

**Known before registering (prior work and the live record; none of it computed for H114).**
- **Live, 10 to 24 Nov (the audit):** the Setups book (`b_targets`) on USDJPY: 6 closed trades, -$196, three of them
  stopped. The stop sat 0.26% to 0.41% from the entry, with the position at about 6x so that a stop costs 2% of the book.
  The Lead was on the right side 24 hours later in 34% to 38% of steps. Fourteen days in one market: a description.
- **H62 (21 Nov) does NOT answer the wider-stop question for USDJPY.** Its "wider stop" was the main book's stop where
  that was further away. On USDJPY the main book runs the same target rule from the same entries, so the carried stop
  was the main book's on 0 of 722 trades and all three variants equal the current rule to the dollar ("USDJPY is
  unchanged"). What H62 does give is the current rule's own record on USDJPY (replay 2020-04-08 to 2026-11-20 21:45,
  trades by exit time): 722 trades, 42.0% won, net -$882, worst fall -53.1%, fees $6,226, sum of R +8.5; first half
  337 trades, -$1,986, -6.1R; second half 385, +$1,104, +14.6R; holdout 86, -$2,162, -8.4R; forward slice 4 trades,
  -$274, +0.7R. Exits: 401 at the entry stop, 195 at both targets, 103 at Target 1 then the entry, 22 flips.
- **H65 and H68 (22 Nov), same replay, trades by entry time:** USDJPY 722 trades, +8.5R; first half 338, -5.5R; second
  half 384, +14.0R. H65 pooled over eight markets: the tightest third of stops per market lost (-81.9R on 2,623 trades).
- **H90 (22 Nov, the queue) has replayed these very stop distances, but pooled.** `stop_units` in {1, 1.5, 2, 2.5, 3,
  4} on all eight markets together, 2020-02 to 2023-06-07 only, sum of R: -420.6, -35.9, +25.2 (current, 2,945 trades),
  +55.2, +99.9 (stop 3.0, 1,744 trades), +88.2 (stop 4.0, 1,226 trades). Its choice rule kept 2.0 (on BTC and ETH 3.0
  made +43.6R against +46.9R), so the study ended there: no number for another stop on later data exists, and no
  per-market number was published. So the FIRST-HALF leg of the condition below is not blind: pooled, a wider stop
  already looked better in R on that period. The second half and the holdout with a 3.0 stop are new. H91 and H96
  give the current rule on USDJPY for 2023-06-08 to 2025-11-10 (a fresh book): +21.3R on 299 trades; H96's filter
  that skips the tighter half of stops made +22.4R on 220 trades there (no difference to speak of).
- **USDJPY post-mortem (20 Nov, `research/out/usdjpy_postmortem_20261120.md`):** on USDJPY the odds almost never clear
  the entry bar (1 decision of 710), so entries are forced on the trend's side; a trade that banks its targets is
  forced back in within the hour and gives the money back (first trade +$304, the next three -$392). History tables for
  this market moved by thousands of dollars between two runs a week apart (the readings store was rebuilt), so dollar
  totals here are soft.
- **What this means for "leave it out":** on the published numbers the current rule's sum of R on USDJPY is negative
  in the first half (-5.5R / -6.1R), POSITIVE in the second half (+14.0R / +14.6R) and negative in the holdout (-8.4R).
  The condition below (at or below zero in all three) is therefore not met on what is already published. H114 only
  re-reads it on today's store (rebuilt 23 Nov, three more days of data); that part is a re-read, not a new study.
- **So H114 is reduced to what is new:** the Setups rule on USDJPY alone with its own stop at 3.0 (and 4.0) barriers,
  per period, in dollars and with the worst fall; and a count of stop-outs that price then reversed.

**What changes with the stop, read from the code (`engine15/shadows.py` `run`/`open_pos`, `engine15/backtest.py`
`leverage`, `engine15/live.py` `plan_targets`).** One barrier is 1.5 x the 14-hour average range of the 1-hour chart.
- The stop: `stop_units` barriers from the fill (2.0 now).
- The size: `leverage` = 2% / (stop distance as a share of price), between 1x and the market's cap (100x for USDJPY).
  A stop 1.5 times as far means a position two thirds the size; the loss at the stop stays about 2% of the book.
- The targets DO depend on the stop distance (call it R). Target 1 is the Fibonacci 1.272 level of the 1h (else 4h)
  leg only when that level lies between 0.5R and 4R from the entry; else a typical day's travel (the median 24-hour
  reach, which does not depend on the stop); else 1.5R. Target 2 is that leg's 1.618 level when Target 1 came from it,
  else the larger of 2R and 1.5 times Target 1's distance. With a wider stop the Fibonacci window moves out (a near
  level is refused, a far one accepted) and the 2R fallback for Target 2 moves out. The engine's own behaviour is kept:
  the targets are planned from the widened stop. Half is still closed at Target 1, the stop still goes to the entry.
- Nothing else reads `stop_units`: the odds, the entries, the forced entry and the flips are the same rule. The books
  differ in their trades only because a different exit leaves the book flat or in a trade at different times.

**The books.** USDJPY only. The engine's own `shadows.run` under the `b_targets` rule
(`shadows.CHALLENGERS["b_targets"]["rule"]`, cfg from `shadows.asset_cfg`), inputs from `shadows.book_inputs` of the fx
group prepared by `research/h59_half_be.prep_cut` with the cached fits (as H62/H68), from the first decided session to
the last stored session at or before 2026-11-24 04:30 UTC (the copy of the live box's store made today). Three books,
each one continuous from $10,000: `stop_units` 2.0 (current), 3.0 (PRIMARY), 4.0 (secondary, descriptive, can pass
nothing). The stop is passed in the cfg dict handed to `shadows.run`; no engine file is edited. GATE (must hold or
nothing is read): the 2.0 book equals the engine's own `shadows.run_challenger("b_targets")` book, every trade and the
marked equity at every bar.

**Periods.** all; h1 (first decided session to 2023-06-08); h2 (2023-06-08 to the end; as in H68 it CONTAINS the
holdout); holdout (2025-11-11 to the end); forward (2026-11-11 to the end, live days; about two weeks, a description).
Shown beside them, descriptive: "h2 before the holdout" (2023-06-08 to 2025-11-10), so the three parts that do not
overlap can be seen. Trades are counted by entry time.

**Read-outs per book and period, fixed now.**
1. Trades; share won; sum of R and mean R (R = a trade's result after fees over its own risk at its entry stop, the
   book's `r_mult`); net dollars (the marked equity's change over the period) and the same as a percentage of the
   equity at the period's start; fees paid by the period's trades.
2. Worst fall: the largest peak-to-trough fall of the marked equity INSIDE the period, in percent (the running peak
   starts at the equity the period starts with).
3. Net / worst fall: net percent divided by the size of the worst fall in percent. No value when there is no fall.
4. Stop-outs (exit word exactly "STOP": the entry stop, before Target 1) and, of those with 96 later sessions on file,
   the share after which price traded back at the ENTRY price within the next 96 fifteen-minute sessions (24 hours of
   trading; a weekend is skipped; the rest of the exit bar itself is not counted, since the order inside a bar is
   unknown). Yardstick beside it: the share after which price instead went a further full stop distance beyond the
   stop in the same 96 sessions. For price with no memory the two shares are about equal; the first being clearly
   larger is what "stops hit by noise" would look like. A count, not a test.
5. Descriptive: of the current rule's stop-outs that were back at the entry within 96 sessions, the share where price,
   from the entry to that return, never reached a stop 3.0 (4.0) barriers from the same entry (bars' lows and highs,
   the return bar included). Same entry, not the same book: after the first different exit the books part.
6. Checks: the share of trades whose size was held at the 1x floor or the 100x cap (there the stop does not cost 2%);
   the median stop distance in percent and the median leverage; where each Target 1 came from (Fibonacci, a day's
   travel, 1.5R) and the median distance of both targets in percent, by recomputing `plan_targets` for each trade.

**PASS condition for the 3.0 stop, fixed now.** ALL of:
- (a) net / worst fall is higher than the current rule's in h1, AND in h2, AND in the holdout;
- (b) net over all history is higher than the current rule's.
Anything else is "does not pass". A pass leads only to a proposal for a forward paper shadow book (USDJPY with a 3.0
stop beside `b_targets`), which needs the owner's word; it never changes a live book. A history replay is post-mortem
material, not validation, whatever it shows.

**The "leave it out" read, descriptive.** The current rule's own record on USDJPY per period, from the 2.0 book. If its
sum of R is at or below zero in h1 AND in h2 AND in the holdout, that is written down as a proposal for the owner to
decide. Otherwise the report says the record does not make that case by this rule, and shows the periods. Either way
nothing changes: the owner decides which markets a book trades.

**Changes from the brief, made before registering.**
1. "Net / worst fall" is defined in percent, with the fall measured inside each period, because the three books arrive
   at a period with different equity and the size compounds (2% of the equity at each entry).
2. A guard on leg (a): the ratio misleads when a book loses (with the same loss, a DEEPER fall gives a "higher" ratio).
   So in a period where the 3.0 book's net is at or below zero, the leg holds only if its net is higher than the
   current rule's AND its worst fall is not deeper. Where the 3.0 book's net is above zero the leg is the ratio as
   written. This can only make a pass harder.
3. h2 contains the holdout, as in H68 (the brief names H68's periods); the non-overlapping middle part is shown too.
4. "Back at the entry within 24 hours" is fixed as 96 sessions after the exit bar, with a yardstick (read-out 4) and
   read-out 5, since a good share of stops reverse that far in a random walk and the bare share would mislead.
5. Fees, leverage-limit checks and the targets' sources are added as read-outs (a wider stop means fewer and smaller
   trades, so part of any difference is fees; that part is to be shown, not left inside the total).
6. The replay ends at the last stored session of today's copy (24 Nov 04:30 UTC), not at H62's 21 Nov cut, so the
   forward slice holds the live days the audit covers.
7. The "leave it out" read is a re-read of numbers already published (see above), and is labelled so.
8. The gate against the engine's own `b_targets` book is added, as in H62 and H68.

**Limits, stated now.** One market and three stop values on one history that earlier studies have already looked at
(the first half pooled, by H90). One stop is graded (3.0) and one described (4.0); no correction is made, so a pass is
weak evidence and leads only to a forward paper shadow. Paper fees (0.01% a side on USDJPY), fills at the stop price or
the bar's open, no slippage, no swap or financing cost on a leveraged position held for days. The voices' voting list
was chosen on full history (as in H90). Dollar totals on this market have moved between store rebuilds.

### H114 results (24 Nov 2026, runs 12:20 and 12:24 UTC on the laptop, 41 s and 11 s; `research/out/h114_usdjpy_stop/report.md` + `results.json`; script `research/h114_usdjpy_stop.py`, tests `tests/test_h114.py`)

Registered in commit `e2758da` (12:17 UTC; `d70dc57` corrected only the time in the heading), both before the script
existed or any number was computed. USDJPY, 2020-04-08 21:00 to 2026-11-24 04:30 UTC. **Gate passed:** the 2.0 book is
the engine's own `b_targets` book, every trade and the marked equity at every bar (723 trades). The first run refitted
38 weekly fits that the copied cache did not hold (they are in the worktree's own `fits_today`); the second run read all
246 from the cache and gave the same numbers. The 2.0 book agrees with what H62 and H65 published (first half -$1,986
and -5.5R, the same to the dollar; 722 trades to 20 Nov, 723 with the one closed since).

**Verdict for the 3.0 stop: DOES NOT PASS.** First half holds (by the guard: -17.5% against -19.9%, worst fall -46.2%
against -53.1%), second half NO (-14.0% against +16.2%), holdout NO (-18.4% against -17.4%), net over all history NO
(-$2,910 against -$688). No proposal for a forward paper book follows.

Each cell: trades, share won, sum of R, net $, net % of the period's starting equity, worst fall inside the period,
net / worst fall.

| Stop | All | First half (to 2023-06-08) | Second half (holdout included) | Second half before the holdout | Holdout (2025-11-11 on) | Forward (2026-11-11 on) |
|---|---|---|---|---|---|---|
| 2.0 (current) | 723, 42%, +9.0R, -688, -6.9%, -53.1%, -0.13 | 338, 41%, -5.5R, -1,986, -19.9%, -53.1%, -0.37 | 385, 43%, +14.6R, +1,298, +16.2%, -49.5%, +0.33 | 299, 44%, +24.1R, +3,266, +40.8%, -42.4%, +0.96 | 86, 41%, -9.5R, -1,968, -17.4%, -28.1%, -0.62 | 4, 50%, -1.1R, -80, -0.9%, -6.3%, -0.14 |
| 3.0 (PRIMARY) | 453, 47%, -10.7R, -2,910, -29.1%, -46.2%, -0.63 | 215, 44%, -7.1R, -1,754, -17.5%, -46.2%, -0.38 | 238, 49%, -3.6R, -1,156, -14.0%, -43.8%, -0.32 | 189, 52%, +7.0R, +442, +5.4%, -33.4%, +0.16 | 49, 39%, -10.7R, -1,598, -18.4%, -25.4%, -0.72 | 2, 50%, -0.7R, -57, -0.8%, -4.2%, -0.19 |
| 4.0 (descriptive) | 296, 54%, +8.0R, +896, +9.0%, -31.4%, +0.28 | 155, 52%, +6.4R, +893, +8.9%, -31.4%, +0.28 | 141, 56%, +1.5R, +3, +0.0%, -28.2%, +0.00 | 106, 59%, +10.3R, +1,869, +17.2%, -17.5%, +0.98 | 35, 46%, -8.7R, -1,866, -14.6%, -20.0%, -0.73 | 3, 67%, -0.5R, -38, -0.3%, -3.1%, -0.11 |

- **No pattern across the three stops.** Net -688, -2,910, +896; sum of R +9.0, -10.7, +8.0; mean R +0.013, -0.024,
  +0.027. Two standard errors of the sum of R (trades taken as independent) are 72R, 50R and 35R: none of the three
  can be told from zero. The 4.0 stop, not graded, would not have passed either (second half +$3 against +$1,298).
  Fees: $6,236, $2,468, $1,467.
- **Why a wider stop does not pay here (from the checks).** The loss at a stop stays about -1R (mean stop-out -1.05R,
  -1.04R, -1.03R), but Target 1 hardly moves out with the stop: median 0.68%, 0.77%, 0.73% of price, which is 1.31R,
  0.89R and 0.66R. Half of the Target 1s come from a Fibonacci level and half from the median day's travel, never from
  1.5R. More trades win (42%, 47%, 54%) and each win is smaller. Every trade's targets were reproduced from
  `plan_targets` (0 not reproduced).
- **Stops and noise.** After a stop-out, price was back at the entry within 96 sessions in 36% of cases at 2.0 (146 of
  401), 20% at 3.0, 7% at 4.0; it ran a further full stop distance instead in 39%, 22%, 14%. At no width is the
  first share the larger one: no sign that the stops are hit by noise more than a price with no memory would hit them. Of the 146 returns at
  2.0, a 3.0 stop from the same entry holds through 110 (75%) and a 4.0 stop through 133 (91%).
- **Size.** Median stop distance 0.45%, 0.71%, 0.88%; median leverage 4.5x, 2.8x, 2.3x; no trade at the 100x cap;
  trades at the 1x floor (stop more than 2% away, so the loss exceeds 2%): 0%, 1.8%, 5.7%. Worst trade -1.52R, -2.58R,
  -1.94R (by the code a loss past -1R and fees needs a bar that opens beyond the stop; not checked trade by trade).
- **"Leave it out", a re-read: no proposal by the registered rule.** The current rule's sum of R: first half -5.5R,
  second half +14.6R, holdout -9.5R. Not all three at or below zero. As the registration said, the published numbers
  already showed this. What the three non-overlapping parts show: -5.5R, +24.1R (2023-06-08 to 2025-11-10), -9.5R; in
  all +9.0R on 723 trades with a chance band of 72R, net -$688, worst fall -53.1%. The record neither earns nor
  loses on this history by more than chance. Leaving the market out stays the owner's decision; the Setups book on
  USDJPY is paper only (the vault copies BTC and ETH).

**Deviations and things to know.**
- **The registration's sentence "This can only make a pass harder" (change 2, the guard) was wrong.** In the first half
  the 3.0 stop lost less with a shallower fall, so the guarded leg holds, while the plain ratio is not higher (-0.38
  against -0.37). With the plain ratio in every leg the verdict is the same: does not pass (no leg holds).
- **The guard's unit.** The registration did not say whether "its net is higher" means dollars or percent. The code,
  written before the run, uses percent of the period's starting equity. In the holdout the two differ: -18.4% against
  -17.4%, but -$1,598 against -$1,968 (the 3.0 book entered the holdout with $8,688 against $11,280). In dollars that
  leg would hold. The verdict does not turn on it: the second half and the total fail either way.
- **Added after the first run, descriptive:** the chance band on the sum of R (two standard errors), and the plain
  ratio beside each guarded leg. Neither enters the verdict. The second run was made only to add them.
- **Not verified:** that the 38 fits made on the laptop equal the live box's own (they cover about the last 38 weeks;
  the 2.0 book's trade count and first-half numbers match H62's, and the gate compares the script with the engine on
  the same odds, not with the box). The live Setups book's six trades of the audit are not the replay's forward
  trades: the replay arrives at 11 Nov in a position of its own (4 closed trades, -$80, against 6 and -$196 live).
- **Limits** as registered: one market, one history already looked at (H90, pooled first half), two stop values with
  no correction, paper fees of 0.01% a side, no slippage and no financing cost, compounding books.

**Reading.** On this history a wider stop does not improve the Setups rule on USDJPY: the registered stop (3.0) is
worse than today's in the second half, in the holdout and in total, and the three widths together show noise around
zero. So this study finds no evidence that the stop distance is what makes USDJPY weak. What the post-mortem pointed
at (entries forced on the trend's side) was not tested here. No engine code was changed. Nothing is proposed for a
forward shadow. Whether USDJPY stays in the Setups book is the owner's call.

## H116. BTC and ETH: when price comes back to a capitulation low, a long if the low holds (rule C1) and a long if the low is swept and reclaimed (rule C2) (registered 24 Nov 2026, about 13:00 UTC, before any H116 code existed or any H116 number on history was computed)

**Prompted by:** the owner, 24 Nov 2026: "You need to find the mechanism or way to able to take setup when market
like btc and eth reach its all time low and earn from the rebound. If there is a chance btc revisit 55k or 56k. What
can we do. So we can earn the short and then turn long." Research only: nothing in the engine, the books or the vault
changes, whatever the result. A pass leads only to a PROPOSAL for a forward PAPER book; it never changes a live book
or the vault. A replay on history is post-mortem material, not validation.

**The gap this study fills.** BTC fell to 55,130 on 21 Nov 2026 (ETH to 1,538), bounced to 64,603 (ETH 1,845) and
trades near 60,550. The engine cannot turn long by itself there (a long from flat needs a 5-point Lead, 15 against a
down trend; H71, H113). H107's rules A and B (being built as a paper book in H115) buy the rebound from a FRESH
30-day low; they do not fire when price comes BACK to an earlier capitulation low and stays above it, because that
makes no new low. H116 asks about that case: the RETEST of a capitulation low.

**Words.** A **capitulation low** here is the low that H107's rule A trigger fired off (a fresh 30-day low, at least
10% under the price a week earlier, followed by a rebound of 2 x ATR(1h)). The **level L** is that low's price. A
**retest** is price coming back down to within 1.5% of L after it has first been at least 5% above L. The level
**holds** when the retest turns up without a 15-minute close below L; it **breaks** when a 15-minute bar closes below
L. A **sweep** is a 15-minute low below L. **ATR(1h)** is the engine's stop unit (Wilder ATR(14) of 1h bars, closed
bars only). **R** is a trade's result divided by the distance from its entry to its stop, after fees.

**Known before registering.**
- H107 (the same triggers, the same window): a long AT rule A's trigger made -0.127R a trade in the first half (83
  trades), +0.246R in the second (40), -0.006R over all (123; p 0.545): FAIL. 2022 alone -14.1R on 44 trades: lows kept
  being undercut. So this window is NOT blind for these events: which years' capitulation lows failed is known.
- H113: 181 rule A triggers in the two halves (120 / 61); they come in clusters. After a confirmed capitulation low
  the Lead is still below zero three days later in three events of four, and Setups shorts opened in the 48 hours
  after a trigger did badly in both halves but well in the holdout year: the trigger does not tell a bounce that
  lasts from one that fails. With about 180 clustered triggers, **fewer than 60 trades a rule is likely**; then the
  verdict is "too few to judge" and Part 1's base rates are the study's main product.
- H70: 18 rebound-long rules out of an oversold state all lost after fees (2020-02 to 2023-06). H71: none of the
  engine's readings carried confirmed information about a rebound. H66: in 505 sudden rallies while short the Setups
  book lost in 93% and turned long within a day in 26%.
- The liquidation-hunt book `p1_liqhunt` (H6; `engine15/playbook.py`, `research/out/p1_postmortem.md`): a GENERIC fade
  of sweeps through ANY liquidity pool (15m swings, 24-hour, 7-day and prior-day highs and lows, round numbers) on six
  markets. It lost forward (65 trades at the post-mortem, 32% won, -0.68R a trade after costs; retired by the owner on
  15 Nov 2026) and on history, and its improvement study H41 (8 variants, about 23,000 trades each) found no edge
  before costs. Its three faults: fading the trend, a stop 0.1 x ATR(15m) beyond the sweep (re-swept), and costs of
  0.26R to 0.5R on tiny stops. **H116 differs in one thing only: the kind of level.** It looks at ONE kind of level,
  the low of a confirmed capitulation (a few a year), long side only, on BTC and ETH, with a stop 0.5 x ATR(1h) beyond
  the low. Rule C2 IS a sweep fade of that level; the generic version of that idea has failed, and nothing known
  says this special case is different. The fee share of R is reported for that reason.

**What must be said first.** The rules' numbers (within 1.5% of the low, a 5% bounce first, 30 days, 1 x ATR(1h) off
the retest's low, a stop 0.5 x ATR(1h) under, 24 hours to reclaim) were chosen by the brief AFTER looking at one
event (21-24 Nov 2026) and before any count on history. They are not fitted, and they are not known to be good.
That event is inside the sealed holdout and is not part of the test. Before this registration nothing of H116 was
computed; I read H107's script and results, H113, H70, H71, H66, the p1 post-mortem, and the first two and last two
rows of the two bar files (the last bar is 24 Nov 2026 04:30 UTC).

**Data.** As H107: `btcusdt_15m.csv`, `ethusdt_15m.csv` and the two funding files in `data/` (a read-only link to the
shared copy of the box's data; md5 in results.json). Deciding bars from 2019-10-01 00:00 UTC. **Cut: every input is
truncated at the bar opening 2025-11-10 23:45 UTC before anything is computed**; the holdout from 2025-11-11 is not
read; a trade must END by the cut, else it is not taken. Halves split at 2023-06-08 00:00 UTC (Part 1: by the trigger
bar; Part 2: by the bar that decides the trade). No evidence store, fits, odds or engine book is used. The event apart
reads bars from 2026-08-01 (indicator warm-up, as H107) and reports only levels created from 2026-11-19 on.

**The level (H107's trigger reused exactly: `h107_capitulation_rebound.features`, flag `A`).** When rule A's signal
(onset) fires at the close of 15m bar k: L = low16(k), the lowest 15m low of bars k-15..k; b = the first of those bars
with that low. No new level is made when the coin already has a level with the same L made in the last 30 days. The
level is LIVE for 30 days: it can be touched and can give a signal only at bars that open at most 30 days after the
open of bar k. States, each known at the close of the bar named, from bars up to it only:
1. **Undercut before the bounce (the level dies).** A 15m low below L at any bar after b, before or in the bar that
   arms the level. (The low was not the low; a new trigger at the lower low makes its own level.)
2. **Armed.** The first bar a after b with a 15m high >= 1.05 x L (it may lie before k).
3. **First touch (the retest starts).** The first bar f after both a and k with a 15m low <= 1.015 x L.
4. **In the retest** (bars j = f, f+1, ... while the level is live), with m(j) = the lowest low of bars f..j and
   s = the first bar from f on with a 15m low below L (the sweep's first bar), the two rules below.

**Rule C1, "holds the low".** If any bar from f on closes below L before C1 has signalled, C1 is off for this level
(the retest is a BREAK). Otherwise C1 signals at the close of the first bar j with close(j) >= m(j) + 1.0 x
ATR(1h)(j) (the retest is a HOLD; wicks below L are allowed, closes below L are not). Stop = the lower of L and m(j),
less 0.5 x ATR(1h)(j).
**Rule C2, "sweep and reclaim".** If C1 has signalled before any sweep began (s later than C1's bar), C2 is off for
this level (that sweep is not the first retest). Otherwise C2 signals at the close of the first bar j with
s <= j <= s+95 (within 24 hours of the sweep's first bar, that bar included) and close(j) > L. Stop = the lowest low
of bars s..j, less 0.5 x ATR(1h)(j). No such bar: no C2 trade on this level.
**Both.** One signal per level per rule (the first retest only). A signal needs a finite ATR(1h) > 0. The two rules
are judged apart, as two books; both may trade the same retest.

**The trade (H107's exit code with only the stop swapped).** Long at the open of bar j+1 = P (H107's convention; on
these 24-hour markets the next open is the deciding close within a tick). Not taken if P <= the stop. R = P - stop.
Bars j+1 .. j+192 (48 hours) are walked; in each bar the stop is looked at first (low <= stop: out at the stop, or at
the open if the open is below it); then Target 1 = P + 1R (half out at T1 exactly; the stop on the rest moves to P
from the NEXT bar); then Target 2 = P + 2R (the rest out at T2 exactly, also in the T1 bar). What is left goes out at
the close of bar j+192. Fees 0.10% of notional a side (`cost_side`) on the entry and on each part's exit. Funding is
not charged or paid. One trade at a time per rule and coin: a signal is taken only if its bar is at or after the
previous trade's exit bar; a skipped signal uses up its level for that rule. Result: R net of fees, and percent.

**Part 1, base rates (descriptive; decides nothing).** Levels whose trigger is at least 34 days (30 days + 96 hours)
before the cut, so each is seen in full; per half and overall, pooled and per coin. Counts: triggers, levels; of the
levels: undercut before a 5% bounce, never bounced 5% in 30 days, armed; of the armed: retested within 30 days (a first
touch) or not; of the retested: HOLD (C1's signal came with no close below L before it; with or without a wick under
L), BREAK (a 15m close below L came first; reclaimed within 24 hours, i.e. C2 signalled, or not), unresolved (neither
by the end of the 30 days). Also, with hindsight and labelled so: the share of retests with a 15m close below L within
24, 48 and 96 hours of the first touch. Timing: hours from the low (bar b) to the first touch (median, quartiles,
range). **What price did next:** from the CLOSE of the first-touch bar, the close 24, 48 and 96 hours later (bars
f+96, f+192, f+384), as a percent (median, quartiles, share above zero), and the lowest low and highest high of the 96
hours against L; all retests, and split by HOLD and BREAK (a split known only afterwards: hindsight).

**Part 2, the test.** Rules C1 and C2 as above, BTC + ETH pooled, and each coin. **Statistics as H107:** month-clustered
bootstrap (every calendar month of the window, of the deciding bar, months without a trade included, both coins'
trades of a month together; 10,000 draws; seed 20261124; statistic = summed R over summed trades of the drawn months;
95% interval = 2.5th and 97.5th percentiles; one-sided p for "mean R > 0" = (1 + #{draw - observed >= observed}) /
(draws + 1)). A half's bootstrap resamples that half's months (June 2023, which the split cuts, is in both lists with
each half's own trades). Holm correction over the two rules (m = 2) on the pooled whole-window p.
**Pass rule, per rule, fixed now. PASS only if all hold:** (a) at least 60 trades pooled and at least 20 in EACH half;
(b) pooled mean R > 0 in BOTH halves; (c) pooled mean R > 0 over the whole window with the Holm-adjusted one-sided
month-clustered p < 0.05. Fewer trades than (a): "TOO FEW TRADES TO JUDGE" (no pass). Anything else: FAIL.
**Read-outs (not conditions):** per rule, pooled / BTC / ETH x whole / first half / second half: trades, share won,
mean R, sum of R, median R, percent return, exits by kind, longest losing run, deepest fall of cumulative R, months
with a trade, the bootstrap interval and p; by calendar year; signals skipped; the median stop distance as a percent
of price and the round-trip fee in R; a drift yardstick in percent (the trade's net percent minus the mean net percent
of a plain 48-hour long, next open to the close 192 bars later less 0.20%, entered at every bar of the same
coin-month); the trade list.
**Look-ahead guards:** (i) for every signal bar of both rules and 40 random bars per coin, H107's readings AND the
whole level machine are recomputed on data cut at that bar; the set of signals up to that bar (rule, bar, L, stop)
must equal the full run's; (ii) the trade walk with a swapped stop is checked bar by bar on every trade, and against
H107's own `walk` when given H107's stop.
**Descriptive only (decides nothing; one setting moved at a time):** zone 1.0% and 2.5%; first bounce 3% and 8%; C1's
turn 0.5 and 2.0 x ATR(1h); stop pad 0.25 and 1.0 x ATR(1h); C2's reclaim window 6 and 48 hours; level life 14 and 60
days.

**Part 3, "earn the short and then turn long" (descriptive; ARITHMETIC ON PRICES, NOT A BOOK).** The evidence store is
not loaded, so what the Setups book held is not read. For each C1 and C2 trade: H = the highest 15m high from the bar
after the low to the bar before the first touch (the bounce high, known as the high only afterwards); Z = 1.015 x L
(the top of the retest zone). The fall into the zone = (H - Z) / H. A short sold at H and bought back at Z would have
made that less 0.20% fees; a short sold halfway, at (H + Z) / 2, makes ((H + Z) / 2 - Z) / ((H + Z) / 2) less 0.20%.
Nobody sells the exact high: the first is an upper bound. Next to them: the long's own net percent and R, and the
move from Z to the long's entry (what a short held past the zone until the long's signal would have added or given
back). Medians and ranges per rule, per half.

**Part 4, the live case (descriptive only; NO result is computed for it).** The level machine on the event: BTC L =
55,130 (low 21 Nov 2026 06:15 UTC), ETH L = 1,538 (low 21 Nov 04:00 UTC), rule A's trigger at the 06:45 UTC close on
both (H107's event read). Stated in prices: the state of each level at the last bar read (armed or not, touched or
not), the retest zone, what C1 and what C2 must see to signal, where the stop and Target 1 would sit for example fills
at the ATR(1h) of the last bar read (the ATR on the day will differ), and the date the levels stop being live. If a
C1 or C2 signal has already occurred it is named, without a result.

**Changes from the brief, made before registering.**
1. The entry is the OPEN of the bar after the deciding close (H107's code), not the close itself.
2. H107's exit code closes the rest at Target 2 = +2R when it is reached inside the 48 hours; the brief's summary
   named only Target 1 and the 48-hour close. Kept as H107's code, since the brief asks for H107's own exit.
3. A level DIES when its low is undercut before price has bounced 5% (state 1). The brief did not say; without it a
   level that price fell through would later be "retested" from below.
4. Triggers that repeat the same low within 30 days make ONE level (rule A can fire again off the same low).
5. The first touch must come after the trigger bar and after the arming bar (not in the bar that arms).
6. HOLD and BREAK are defined by which comes first in the retest, C1's turn or a 15m close below L; a retest with
   neither inside the 30 days is "unresolved". The brief's "no close below L during the retest" had no end.
7. C2 belongs to the first retest: if C1's turn came before any low below L, a later sweep gives no C2 trade. C2's
   24 hours run from the sweep's FIRST bar and include a reclaim in that same bar (a wick).
8. One trade at a time per rule and coin (H107's form), so two levels alive together cannot stack trades in a rule.
9. The pass rule is the brief's three conditions. H107's two further conditions (each coin above zero, above the
   random-entry baseline) are read-outs here, not conditions; the baseline is a drift yardstick in percent, because
   H70 showed an R baseline mostly measures how much of R the fee eats.
10. Part 1 uses only levels seen in full (trigger at least 34 days before the cut). Forward prices are measured from
    the close of the first-touch bar.
11. Added, descriptive only: the sensitivity list; the hindsight share of retests with a close below L in 24/48/96
    hours; the fee share of R.

**Code:** `research/h116_retest_capitulation_low.py` (history run; `--event` for Part 4 alone), tests
`tests/test_h116_retest.py`. Output: `research/out/h116_retest_capitulation_low/` (`results.json`, `event.json`,
`report.md`).

### H116 results (24 Nov 2026, run 12:58 UTC on the laptop, 7 s; registration commit `90ecef2`; `research/out/h116_retest_capitulation_low/report.md` + `results.json` + `event.json`; tests `tests/test_h116_retest.py`)

**Verdict by the registered condition: NO PASS. Rule C1 and rule C2 both have TOO FEW TRADES TO JUDGE; on the trades
there are, both lost after fees.** Data 2019-10-01 to 2025-11-10 23:45 UTC; the holdout was not read (only the bars
from 2026-08-01 for the two live levels, states and prices only). Nothing in the engine, the books or the vault was
changed; nothing is proposed for a forward book on the registered condition.

**Part 1, base rates.** 187 rule A triggers, 130 levels (57 triggers repeated a low); 126 seen in full.
- Of the 126: 24 (19%) undercut before a 5% bounce; 25 (20%) bounced and never came back within 1.5% in 30 days; 77
  (61%) retested. First half 88 levels / 58 retests; second half 38 / 19.
- Of the 77 retests: HOLD 47 (61%; 13 with a wick under L), BREAK 30 (39%; 26 back above L within 24 hours),
  unresolved 0. First half 33 / 25; second half 14 / 5.
- Hindsight from the first touch: a 15m close below L within 24 / 48 / 96 hours in 70% / 78% / 81% of the retests
  (first half 72 / 83 / 86; second half 63 / 63 / 63), and in 51% / 64% / 68% of those that "held". Price traded below
  L inside 96 hours in 88% (91%, 79%). Lowest low of the 96 hours against L, median -6.6% (-8.7%, -1.8%); highest
  high +9.7%.
- Hours from the low to the first touch: median 21.0, quartiles 7.5 and 95.5, range 2 to 716 (first half median 13.6,
  second half 119.5). The bounce high before the retest: median 9.1% above L.
- From the close of the first-touch bar, median return and share above zero at 24 / 48 / 96 hours: all +1.9% 58%,
  +1.3% 56%, +0.9% 53%; first half +1.4% 57%, +0.2% 52%, -0.5% 47%; second half +2.9% 63%, +4.1% 68%, +4.6% 74%;
  HOLD +2.4% 68%, +1.7% 62%, +2.0% 55%; BREAK -4.3% 43%, -1.8% 47%, -0.2% 50%. 2022 holds 47 levels and 33 retests.

**Part 2, the test.** Each cell: trades, share won, mean R [95% month-clustered interval], sum of R; one-sided p.
- **C1, BTC + ETH:** 48, 40%, -0.178 [-0.513, +0.203], -8.5R; p 0.844, Holm 1.0. First half 31, 29%, -0.431 [-0.756,
  -0.053], -13.4R; second half 17, 59%, +0.285 [-0.411, +0.902], +4.8R (p 0.18). BTC 26, -0.108; ETH 22, -0.260.
  Checks failed: 60 trades, 20 in the second half, first-half mean, whole-window mean, Holm p. 27 of 48 stopped;
  longest losing run 13; deepest fall of cumulative R -16.6R. By year (trades, sum R): 2019 3, -3.2; 2020 4, -3.8;
  2021 6, +3.3; 2022 16, -11.5; 2023 4, +2.1; 2024 7, +2.5; 2025 8, +2.1.
- **C2, BTC + ETH:** 37, 49%, -0.113 [-0.520, +0.331], -4.2R; p 0.712, Holm 1.0. First half 29, 48%, -0.112; second
  half 8, 50%, -0.116. BTC 17, -0.222; ETH 20, -0.020. Checks failed: 60 trades, 20 in the second half, both halves'
  means, whole-window mean, Holm p. 18 of 37 stopped. By year: 2020 3, -2.4; 2021 9, +3.2; 2022 17, -4.0; 2024 4,
  -0.4; 2025 4, -0.5.
- Median stop 3.7% of price (C1) and 3.5% (C2); the round-trip fee is 0.05R to 0.06R: costs are not what loses.
  Drift yardstick (net percent minus a plain 48-hour long at every bar of the same coin-month): C1 +0.45, C2 +1.51
  percentage points. Signals not taken: one per coin per rule (a trade was open).
- **Look-ahead guards:** H107's readings and the level machine recomputed on data cut at 164 bars (84 signal bars, 80
  random), 0 mismatches; the walk equals the bar-by-bar walk on every trade and H107's own walk when given H107's
  stop (84 bars). H107's rule A re-run on this data copy: 123 trades, -0.7R, as H107 reported.
- **Descriptive, one setting moved at a time:** C1's first half is below zero in all 10 variants that change it (-0.05
  to -0.50R a trade) and its second half above zero in all (+0.07 to +0.64R); overall -0.29R (first bounce 8%, 34
  trades) to +0.20R (a 2 x ATR turn, 29 trades); zone 2.5% gives 62 trades at +0.02R. C2 overall -0.19R to +0.07R.

**Part 3, arithmetic on prices, not a book.** At the median, C1's 48 trades / C2's 37: fall from the bounce high to
the zone top 7.1% / 7.9% (at least 3.3% by construction); a short from the exact high to the zone top +6.9% / +7.7%
after fees, from halfway +3.5% / +3.9%; a short kept from the zone top to the long's entry -1.3% / +0.9%; the long
from there -2.5% (mean -0.9%) / -1.3% (mean -0.3%). The bounce high is known only afterwards.

**Part 4, the live case (states and prices; no result).** At the bar opening 24 Nov 2026 04:30 UTC both levels are
armed and not touched; both live until the 15m close of 21 Dec 2026 06:45 UTC. BTC: L 55,130.00, zone a 15m low <=
55,956.95; ETH: L 1,538.00, zone <= 1,561.07. ATR(1h) then: BTC 713.08, ETH 22.89. Example fills at that ATR: BTC C1
with the retest low at the zone top needs a close >= 56,670.03, stop 54,773.46, T1 58,566.59; with the retest low at
L, close >= 55,843.08, stop 54,773.46, T1 56,912.69; BTC C2 after a sweep to 54,578.70, a close above 55,130, stop
54,222.16, T1 56,037.84. ETH C1: close >= 1,583.96 (stop 1,526.55, T1 1,641.37) or >= 1,560.89 (stop 1,526.55, T1
1,595.23); ETH C2 after a sweep to 1,522.62: close above 1,538, stop 1,511.17, T1 1,564.83.

**Not registered, added after the run (small cells).** By time from the low to the first touch: under 24 hours 41
retests, C1 23 trades -0.30R, C2 16 trades -0.29R; 24 hours to 7 days 21 retests, C1 14, +0.15R, C2 12, +0.27R; over
7 days 15 retests, C1 11, -0.35R, C2 9, -0.32R.

**Deviations.** (1) The heading says "about 13:00 UTC"; the registration was committed at 12:54 UTC (`90ecef2`),
before the script existed. (2) The split by time to the first touch was added after the first run and is marked so;
the run was repeated with it and every registered number was identical. (3) The bar files are a later copy than
H107's (other md5); inside the cut they give H107's rule A result exactly. (4) Only the H116 tests were run (10
pass), not the full suite; no engine file was touched.

**Reading.** A capitulation low was revisited within 30 days in six cases of ten, and when it was, price mostly did
not stop there: it traded under the low within four days in about nine revisits of ten and closed a 15-minute bar
under it in eight of ten. Buying the retest, either when the low first holds (C1) or after a sweep is reclaimed (C2),
lost a little after fees over 2019 to 2025, on too few trades to judge. As in H107 the halves disagree: the first half
(2022 above all) lost, C1's second half is positive on 17 trades. History gives no support for covering a short at
the old low and buying there because the low should hold. The rules are written out exactly in the report, so they
can be ported to a paper book if the owner wants the data points; that would be collecting evidence, not acting on
an edge. A replay is post-mortem material, not validation.
## H115. A forward paper book for H107's capitulation-rebound long on BTC and ETH: rule A and rule B side by side, with a Telegram alert when a rule fires (registered 24 Nov 2026, about 12:55 UTC, before any H115 code existed; no new number on history was computed for it)

**Prompted by:** the owner, 24 Nov 2026: "So how can we seize the opportunity when the capitulation occur. How can we
do the long setup?" and then, to the proposal of a paper book with an alert: "build the paper capitulation-long book
with the Telegram alert". **Paper only. NOT passed.** It places no order, it changes no book and no decision, and it
never reaches the VIP vault.

**What must be said first: history does not support this rule. The book is started because the owner asked for it,
not because a study passed.** What is already on record:
- **H107 (the two rules run here), 2019-10 to 2025-11, BTC + ETH, after fees.** Rule A: 123 trades, 47% won, -0.006R
  a trade (95% month-clustered range -0.220 to +0.273), -0.7R in all: FLAT. It lost in the first half (83 trades,
  -0.127R, -10.6R) and won in the second (40 trades, +0.246R, +9.8R); BTC alone -0.041R, ETH alone +0.021R; 51 of 123
  stopped; longest losing run 11; deepest fall of cumulative R -19.3R; 2022 alone 44 trades, -14.1R. Verdict by its
  registered rule: FAILS. Rule B (A with negative funding): 32 trades, 59% won, +0.194R a trade (-0.110 to +0.622;
  p 0.182), +6.2R in all; 16 of the 32 are in 2022. Verdict: TOO FEW TRADES TO JUDGE (no pass).
- **H70:** 18 other rebound-long rules out of an oversold state ALL lost after fees in 2020-02 to 2023-06 (mean R -0.05
  to -0.25 a trade). **H71:** none of the engine's own readings carried confirmed information about the next 24 hours
  in an oversold state.
- **H113:** counted from rule A's trigger without hindsight, the price was +0.6% / +1.3% / +1.6% above the trigger's
  close after 24 / 48 / 72 hours at the median, and -1.2% / -0.7% / -3.7% in the holdout year. The trigger "does not
  tell the two kinds of bounce apart": bounces off new lows kept failing in 2022 and in 2026.
- **The one event the rules were shaped on:** at the 21 Nov 2026 06:45 UTC close both rules bought on both coins (BTC
  57,194, ETH 1,613.70) and made +1.31R and +1.16R. That is one event, seen before the rules were written. It is not
  evidence.

So the honest expectation is a book that is about flat after fees, with long losing runs when the market keeps
falling. Nothing here may be described as having an edge.

**The rules: H107's, exactly as registered there (nothing is tuned).** Per coin (BTCUSDT, ETHUSDT), at the close of
each 15-minute bar k, from bars up to k only:
- ATR(1h) = Wilder ATR(14) of the 1h bars (`data.resample`, `indicators.atr_wilder`), read through
  `data.htf_on_15` (closed 1h bars only). low16 = the lowest low of bars k-15..k (4 hours). low30d = the lowest low of
  the bars whose open is within 30 days up to k (30 days of bars needed). c7 = the close of the last bar whose open is
  at or before open(k) - 7 days. Funding = the last rate SET at or before the close of bar k.
- **Rule A:** (1) low16 <= low30d (a fresh 30-day low in the last 4 hours); (2) low16 / c7 - 1 <= -10%; (3) close(k) >=
  low16 + 2.0 x ATR(1h); and (1)-(3) were NOT all true at k-1 (onset only).
- **Rule B:** rule A's signal AND the last funding rate < 0 (shorts are paying).
- **The trade (both rules):** long at the open of bar k+1 = P. R = 3 x ATR(1h) at k. Stop P - R. Bars k+1 .. k+192
  (48 hours) are walked; in each bar the stop is looked at first (low <= stop: out at the stop, or at the open if the
  open is below it); then Target 1 = P + 1R (half out at T1 exactly; the stop on the rest moves to P from the NEXT
  bar); then Target 2 = P + 2R (the rest out at T2 exactly, also in the T1 bar). What is left goes out at the close
  of bar k+192. One trade at a time per rule and coin: a signal at k is taken only if k >= the previous trade's exit
  bar; a signal while that rule's trade is open is counted and not taken.
- **A note on the owner's summary.** The accepted proposal said "half off at Target 1 and the rest closed after 48
  hours". H107's registered trade has two more parts: the stop on the rest moves to the entry after Target 1, and the
  rest goes out at Target 2 (+2R) if price gets there within the 48 hours. The book runs H107's trade exactly, because
  every history number quoted above is for that trade; a different exit would be a new, untested rule. The alert names
  both parts.

**Two books, side by side.** `p9_rebound_a` (rule A) and `p9_rebound_b` (rule B), module `engine15/playbook9.py`,
each on BTC and ETH. They are NOT two independent tests: every rule B trigger is a rule A trigger, and BTC and ETH
mostly fire at the same close.

**Forward only.** The record starts at the first live step after the deploy (kept in the book's state as
`started_utc`), and never before 2026-11-24 12:50 UTC (`REGISTERED`). Only a trigger whose deciding bar CLOSES after
the start counts. No trade from history is ever written into the record; the 21 Nov 2026 event is not in it.
- The book keeps its own state (`data/capit_long_state.json`, written atomically): the last bar it has seen per coin,
  an open or waiting trade per rule and coin with its fixed entry, stop and targets, the closed trades, and the alerts
  made. A decision is made once, at the step that first sees the bar, and is not recomputed later. A restart resumes
  from the file. A missing or unreadable file means the book starts flat again from that step (an unreadable one is
  kept beside it for a person to look at); that is logged, and it loses the record made so far, so the file belongs
  with the engine's other state when the box is backed up.
- If the engine was down over a deciding close, the step that comes back finds the trigger late. It is still taken at
  the rule's own fill (the open of bar k+1, already on file), walked bar by bar through what it missed, and marked
  late; the alert says how late. This keeps the record equal to the rule; it is said here because such a trade could
  not have been acted on by hand in time.

**Funding for rule B (the live source).** The engine's own funding file, `data/<coin>_funding.csv`
(`data.load_funding`), which `live._update_bars` refreshes from Binance at every crypto step and which the journal's
funding reading is built from. Binance sets BTC and ETH funding every 8 hours; in the file since 2019 no two rates are
more than 8 hours and 47 milliseconds apart. **Stale = the last rate set at or before the deciding close is more than
9 hours older than that close** (one 8-hour interval plus one hour: four engine steps of grace for a late fetch, and
far short of a second interval, so a file that missed a whole funding can never pass). When rule A fires and the
funding is missing or stale, rule B does NOT fire, one log line says so, and the alert says so. Rule B never fires on
a stale rate. Known limit: at the three closes a day where a new rate is set in the same second (00:00, 08:00, 16:00
UTC), the step may still hold the previous rate; each decision records the rate it used and when that rate was set.

**Sizing and fees (the strategy books' convention).** $10,000 per trade, per coin and per rule, 1x, not compounded
(`docs/PLAYBOOK_INTERFACE.md`: "at $10,000 per trade"; crypto is 1x in `backtest.leverage`). Fee 0.10% of notional a
side, on the entry and on each part's exit (the H107 figure; frozen in the module). Funding is not charged or paid, as
in H107's R. Each trade records its net R (H107's formula: result after fees over the entry-to-stop distance) and
its dollars (`pnl_usd` = the net percent return x $10,000). A stop-out loses the stop distance (typically 2% to 5% of
the price) on $10,000 plus about $20 of fees. Not chosen: sizing to a fixed 2% risk, which the engine uses only where
leverage is allowed.

**Forward verdict, fixed now.** Per rule, BTC and ETH pooled, by the scoreboard's own rule
(`reports._stats`, `research/VERDICT_RULES.md` section 2): the 90% range of the mean dollar result per closed trade.
1. First read: the first server scoreboard whose row for the book shows 30 or more closed forward trades, copied as
   it stands. Second read: the same at 60. No decision is taken between the two.
2. The by-day range the scoreboard shows beside it is read with it: BTC and ETH fire together, so 30 trades may be 15
   to 20 separate events. Mean R per trade (H107's measure) is shown on the book's block; it carries no verdict.
3. **How long this will take, honestly.** On history rule A made about 20 trades a year on the two coins together
   (123 in 6.1 years) and rule B about 5 (32). So rule A's first read is about a year and a half away and its second
   about three years; rule B's first read is about six years away. The triggers come in clusters (44 of rule A's 123
   trades were in 2022), so it can be much sooner or much later. In practice rule B is a record, not a test.
4. "ahead" at the first read changes nothing; "behind" at the first read: a post-mortem, then the owner decides
   whether it runs on. "undecided" at the second read: it stays a labelled record.

**What a pass would and would not change.** "ahead" at BOTH reads opens a discussion with the owner about a next test
under a new registration, and nothing else. It never by itself reaches the vault, the Setups book or a main book, and
it does not make H107 pass on history. Whatever it reads, the book stays labelled NOT passed.

**The Telegram alert (to the owner's own chat only).** `engine15/telegram_notify.py` reads the book's state file and
sends one card per coin when a rule opens a trade: the coin, which rule(s), the entry (the deciding close; the paper
fill is the next bar's open), the stop, Target 1 and Target 2, the time exit in UTC, the risk in percent, the funding
reading, and the line that this is paper only, NOT passed, flat on history. One card says both rules when both fire at
the same close. A second card when a trade closes, with its R. Each is sent once (the bot remembers what it delivered
in its own state). The bot is a separate process and only reads: a failed alert cannot touch the book. The alert is
information for the owner; it is not a signal for members and goes to no channel.

**Disclosure: what had been seen when this was written.** H107's results and its event read, H70, H71 and H113 (all
above). No forward trade of this book exists. No new history run was made for this registration.

**Code (to be written after this is committed):** `engine15/playbook9.py` (the rules ported into the engine, constants
in the module, none in `CFG`, no version bump), registered in `reports.PLAYBOOK_MODULES`; the alert in
`engine15/telegram_notify.py`; tests `tests/test_playbook9.py` (parity with `research/h107_capitulation_rebound.py`
trade for trade on the real bars, no look-ahead, forward only, stale funding, state and restart, the cards). Nothing on
the money path is edited (`tools/money_files.txt`).

### H115 note: implementation choices (24 Nov 2026, written with the code, after the registration was committed as 98a0954)

Nothing in the registered rule was changed. The registration was committed at 12:50 UTC by the laptop's clock (the
heading says "about 12:55"); `REGISTERED` is 12:50. What the registration left open, and what was seen while building:
- **The port and its proof.** `playbook9.features` and the bar-by-bar trade (`_walk_bar`) are H107's
  `features` and `walk_loop`, with the constants frozen in the module (stop 3.0 x ATR, fee 0.10%), so a later change
  of `CFG` does not silently change the book. `tests/test_playbook9.py` runs the book's own per-bar code over the
  whole of both bar files and holds it to the research script: the three flags on every bar, and every trade's
  deciding bar, entry, stop, targets, exit bar, kind of exit and R (BTC 68 rule A and 13 rule B trades, ETH 94 and
  37, on the laptop's copy to 24 Nov 2026 04:30 UTC). Those files include the holdout year. The test asserts equality
  and reports no result; the only results looked at were the two 21 Nov 2026 event trades H107 already published
  (+1.31R and +1.16R, reproduced). The counts were seen: about 39 rule A trades fall after 10 Nov 2025, against about
  20 a year before, so the first read may come sooner than the registration's estimate if new lows keep coming.
- **The two prices in the registration** ("BTC 57,194, ETH 1,613.70") are H107's words. On the files the deciding
  closes are 57,194.94 and 1,613.76 and the fills at the next open 57,193.99 and 1,613.70.
- **The start is the first step's clock**, not the last bar on file: the last 15-minute close before the clock of the
  step that finds no state (never before `REGISTERED`). A bar file that is behind at that step cannot bring an older
  bar into the record later.
- **The tail.** Each step reads the last 45 days of bars plus the bars it has not seen. A test recomputes the readings
  on such a tail cut at the bar, for every rule A bar and 40 random bars a coin: the flags are identical and the ATR
  agrees to 1e-9 (Wilder's average has forgotten its start after 45 days).
- **Stale funding never happened on history.** With the 9-hour limit no bar since 2019 has a stale rate, so the guard
  changes nothing in the parity check; it protects the live read only. Rates carry the exchange's own timestamps,
  which are up to 47 ms after the 8-hour mark: a rate stamped after a close is not read at that close, as in H107.
- **"Late".** A trigger is marked late when the step that finds it runs after the NEXT bar has closed (more than 15
  minutes after the deciding close). The Telegram card adds its own "Late" line when it is sent more than 30 minutes
  after the close, whatever the reason (the bot was down, the send failed).
- **The alert's numbers.** At the signal the fill (the next bar's open) is not on file yet, so the card gives the
  deciding close as "Entry near" and the stop and targets from it; one bar later the state holds the paper fill and
  a card sent after that shows the exact levels. Trades of one coin that close at the same close share one card. The
  bot shows paper dollars at its usual 15x display (`DISPLAY_X`); R is not scaled.
- **The generic close card.** The bot's own closed-trade card is silent for ids that start with `p9_` (its `QUIET`
  list, there for `p9_cascade`), so these books' closes are announced once, by their own card. The milestone at 30
  trades and a verdict change still alert. Seen while reading that code, not changed: for the other forward books
  the generic card cannot fire on a book's FIRST closed trade (the key changes from `<book>|forward` to the
  scoreboard title when the row first appears).
- **Signals while a rule's trade is open** are counted in the state and on the page and get no card.
- **The allocator** `a_alloc` lists both books as "not registered": H110 fixed its 37 books, and that is left as it is.
- **The web tab.** The block `playbook.playbook9` carries `not_passed: true`; the tab's generic strategy-book code
  (`web/mind15/index.html` in this repo) lists such a book in its NOT-passed group, with an open trade's entry, stop
  and targets. Whether the deployed page shows it is the page pipeline's matter; it was not checked.
- **The hourly state copies** (`tools/server/state_copies.py`) do not include `capit_long_state.json`; the daily
  laptop backup of `data/` does. Not changed here.
- **Step cost, measured on the laptop on the real files:** 12 ms with no new bar, 26 ms with a new bar on both
  coins, 34 ms to catch up five days.
- **Not verified:** nothing was run on the live box. That the box's funding file is refreshed at every crypto step
  is read from `live._update_bars`, not observed there. No card was sent to Telegram: the texts are held by tests.

### H115 note: the retest-level notice (24 Nov 2026; NOT a hypothesis, NOT a setup, nothing registered and nothing graded)

After H116 the owner chose "a plain Telegram notice when price enters the zone, stating these base rates". It is built
beside the H115 book and opens, closes and changes no trade:
- **What it is.** `playbook9.levels_of` is H116's level exactly as the report words it (the low behind a rule A
  trigger; the same-low rule; 30 days; dead, armed, first touch), plus one state that H116 did not name: broken, the
  first bar from the first touch on with a low under the level. The bot sends the owner one notice at the first touch
  and one at the break. The numbers on the first are H116's Part 1 base rates (77 retests, 2019 to 2025: under the
  old low within four days in 88%, median lowest point 6.6% below it; higher a day after the first touch in 58%,
  median +1.9%). They are descriptive counts, not a tested rule; the rules H116 did test (C1, C2) had too few trades
  to judge and lost a little, and the notice says so.
- **Stateless, from a 93-day tail.** The levels alive when the code is deployed were made before it, so nothing is
  kept from triggers seen live: every new bar the levels are recomputed from the last 93 days of closed bars (32 days a
  level is listed, 30 for the same-low rule before it, 30 of lows before those triggers, 1 spare).
  `tests/test_capit_zone.py` holds this to `research/h116_retest_capitulation_low.machine` run on the whole file: at
  338 test dates on BTC and 460 on ETH (every level's trigger bar, first-touch bar, break bar and last listed bar,
  plus 30 random bars) the levels, low bars, arming bars, first-touch bars and states are the script's (787 and 1,341
  level readings, no difference), and at the end of the data copy it finds the two levels of H116's `event.json`.
  Those files include the holdout year; the test asserts equality and reports no result.
- **What no tail can follow:** three or more triggers off exactly the same low price that chain across more than 30
  days. It did not happen in these files: all 86 repeats of a low came within 3.5 hours of the level's own trigger.
- **One message, not two,** when a level is first seen already broken (into the zone and under the low in one bar, or
  the bot was away): the break notice names the touch. This is the bot's choice, not H116's.
- **Not verified:** nothing was run on the live box and no notice was sent to Telegram; the texts are held by tests.
  The page block carries the levels; the web tab does not show them.
## H117. The Setups rule with a capitulation-rebound override, as a forward paper shadow book `b_rebound` on BTC and ETH (registered 24 Nov 2026, about 13:35 UTC, before any H117 code existed; no number on history was computed for it)

**Prompted by:** the owner, 24 Nov 2026, about BTC and ETH falling back to, or under, the 21 Nov capitulation lows:
"So we can earn the short and then turn long"; to the three-step proposal whose step 1 is "a paper copy of the Setups
book with the rebound override (`b_rebound`)": "1. Yes."; and then "I want minds15 engine able to take this
opportunity". **Paper only. NOT passed.** It places no order, it changes no other book and no decision, and it never
reaches the VIP vault: the vault copies `b_targets`, and `setups.BOOK` stays `b_targets`.

**What must be said first: history does not support this rule, and this override itself has never been run on
history. The book is started on the owner's word, not because a study passed.** On record:
- **H107 (the trigger and the long used here).** Rule A, 2019-10 to 2025-11, BTC + ETH, after fees: 123 trades, 47%
  won, -0.006R a trade (95% month-clustered range -0.220 to +0.273): FLAT; it lost in the first half (-0.127R on 83)
  and won in the second (+0.246R on 40); 2022 alone 44 trades, -14.1R; longest losing run 11. Verdict: FAILS. Rule B
  (A with negative funding): 32 trades, +0.194R, too few to judge.
- **H113 (what the override withholds).** Setups shorts opened inside the 48 hours after a rule A trigger, against
  the book's other shorts: first half -0.085R (58) against -0.032R, second half -0.501R (37) against -0.093R, but in
  the holdout year (2025-11 to 2026-11) they were the BETTER shorts: +0.588R (28) against +0.079R. The holdout did not
  confirm that those shorts are bad. From the trigger's close the price was +1.3% after 48 hours at the median and
  -0.7% in the holdout year. So in the most recent year, standing aside from shorts after a trigger would have cost.
- **H116.** A long on the RETEST of an old capitulation low lost a little (C1 48 trades, -0.18R; C2 37, -0.11R; too
  few to judge). This book does not buy a retest: it buys only a NEW rule A trigger (a fresh 30-day low that
  rebounds). If BTC or ETH falls back to the 21 Nov lows and holds above them, rule A does not fire and this book does
  what the Setups book does.
- **H70, H71:** no rebound-long rule or reading tested so far has held up across both halves.
- **Not known at all:** what closing a Setups short at a trigger and holding the rebound long instead would have made
  on history. No replay of this override exists and none was run for this registration.

So the honest expectation is a book that behaves as `b_targets` almost all the time and, about twenty times a year on
the two coins together, swaps the Setups position for a long whose record on history is flat after fees. "Earn the
short" means only this: a short the book holds at the trigger is closed at the next bar's open, at whatever result it
has then. Nothing here may be described as having an edge.

**The book.** `b_rebound` = the Setups rule `b_targets` exactly as it runs on the day (rule `{"targets": True,
"early": True}`, the same odds, readings, bars, sizing rule, fee and early entry) plus ONE rule key, `"rebound": True`.
BTCUSDT and ETHUSDT only; on the other six markets the book does not exist. With no trigger it is `b_targets`, bar
for bar.

**The trigger (H107's rule A, nothing tuned).** At the close of each 15-minute bar k, from bars up to k only,
`engine15/playbook9.py`'s `features` on the book's own 15-minute bars (the last 45 days of them, as `p9_rebound_a`
reads): the onset flag `A` (low16 <= low30d; low16 / c7 - 1 <= -10%; close(k) >= low16 + 2.0 x ATR(1h); not all three
true at k-1) and its ATR(1h) (Wilder ATR(14) of the 1h bars through `data.htf_on_15`, closed 1h bars only). A trigger
needs a finite ATR above zero. Rule B's flag (A with negative, fresh funding) is RECORDED with each trigger and
decides nothing: every rule B trigger is a rule A trigger.

**The override, at a trigger at the close of bar k.** The book's position is read at that close, after bar k's own
stop and target fills and before the Setups decision of that close.
1. **SHORT:** the Setups decision of that close is not taken. At the open of bar k+1 the short is closed (exit word
   `REBOUND`, or `T1+REBOUND` when its Target 1 was taken before) and the long is opened at the same price, the way the
   book books a flip.
2. **FLAT:** the Setups decision of that close is not taken (no entry at that close, early or forced). The long is
   opened at the open of bar k+1. (The Setups early entry books a trade at the deciding close; the rebound long keeps
   H107's fill, the next open, so it shows one step later.)
3. **Already LONG (a Setups long):** nothing changes; the trigger is counted (`while_long`) and the Setups rule decides
   that close as always, whatever it decides.
4. **A rebound long is open:** the trigger is counted (`in_trade`), not taken. A trigger at the close of the very bar
   in which a rebound long ended IS taken (the book is flat at that close; `playbook9` does the same).

**The long (H107's trade exactly).** P = the open of bar k+1. R = 3 x ATR(1h) at k (`playbook9.STOP_ATR`). Stop P - R.
In every bar from k+1 on the stop is looked at first (low <= stop: out at the stop, or at the open if the open is
below it); then Target 1 = P + R (half out at exactly T1, the book's `PART`; the stop on the rest moves to P from the
NEXT bar); then Target 2 = P + 2R (the rest out, also in the Target 1 bar). What is left is closed at the close of the
192nd bar (bar k+192, 48 hours; exit word `TIME`). The targets come from R, not from `live.plan_targets`. So for the
same trigger the entry, stop, targets, exit and R are those of `p9_rebound_a`'s trade (the two books can still differ
in WHICH triggers they take: each skips a trigger while its own long is open, and this one also while it holds a
Setups long).

**Size and fees: the Setups book's own, so its dollars compare with `b_targets`.** Quantity = the book's equity x
`backtest.leverage(cfg, P, R)` / P: the book's sizing rule with this trade's stop distance; on BTC and ETH the cap is
1.0, so the whole book at 1x, compounding as the book does (H115's books use a flat $10,000 a trade instead). Fee =
the book's `cost_side` (0.10% a side on BTC and ETH today, the figure H107 used), on the entry and on each part's
exit; funding is not charged, as in the book. R = the book's `r_mult` (net dollars over quantity x R), which with
that fee is H107's R. Each rebound long also records its R at H107's 0.10% fee (`r_h107`), so the two stay visible if
the book's fee is ever changed.

**While the rebound long is open** the Setups rule is not consulted: no flip to short, no step-aside, no forced
entry; the idle count stays at zero. **When it ends** (stop, Target 2 or the 48-hour exit) the book is flat with an
idle count of zero; the Setups rule makes no decision at the close of the bar in which it ended and decides again from
the close of the next bar. Everything else is `b_targets` unchanged.

**When something fails.** If the trigger cannot be computed at a step (the module does not import, the bars cannot be
read), that step runs as the plain Setups rule and one log line says so; a rebound long already open is still managed
by its own stop, targets and 48-hour exit, which need no trigger. A trigger at such a close is lost, not taken later.
If the book's own step fails, it is not advanced, one log line says so, no other book is touched, and the next step
walks the bars it missed one by one (a trigger found then is taken at the rule's own fill, already on file).

**Forward only.** The book starts FLAT with $10,000 a coin at the first live step after the deploy, as `b_trend30`
did; nothing from history is written into it. Its state lives in `data/shadow_state.json` under its own key, written
only for this book; a restart resumes an open rebound long exactly.

**The forward read, fixed now.**
1. **The scoreboard's verdict** (`reports._stats`: the 90% range of the mean dollar result per closed trade) on the
   row `b_rebound`, BTC and ETH together, at the first server scoreboard that shows 30 or more closed forward trades,
   copied as it stands, with its by-day range.
2. **The registered comparison with `b_targets` over the same days:** the change in marked equity of `b_rebound`
   against that of `b_targets` on the same two coins, both counted from the close of `b_rebound`'s first live step, in
   points of return on the two $10,000 books. "ahead of" at +1.0 point or more, "behind" at -1.0 or less, "level with"
   between (H108's band). No number and no word before 30 closed trades.
3. **What that read can and cannot say.** Most of those 30 trades will be ordinary Setups trades: the override acts
   about twenty times a year on the two coins (H107's pace; fewer here, because triggers while the book is long are
   skipped), so the first read mostly measures the Setups rule and the luck of a fresh start. The book starts flat
   while `b_targets` may be in a trade, so the two differ until they fall into step, and that difference is not the
   override. The override's own record is kept beside the read and carries no verdict: every trigger seen, how many
   were taken from SHORT and from FLAT, how many were skipped and why, and each rebound long's R. Thirty rebound longs
   are more than a year away at H107's pace.

**What a good read would and would not change.** "ahead" opens a discussion with the owner about a next test under a
new registration, and nothing else. It does not make H107 pass on history, and the book stays labelled NOT passed
whatever it reads. Following this book with real money would still need two separate decisions, both the owner's
(`docs/CHARTER.md`, the rebound plan): pointing the feed at `b_rebound` (that alone closes members' shorts earlier and
withholds shorts while the long lives) and the vault's own rebound switch. Neither is part of this registration.
"behind": a post-mortem, then the owner decides whether it runs on.

**Disclosure: what had been seen when this was written.** H107, H113, H115 and H116 with their results (above), H66,
and the live books of 21 to 24 Nov 2026. No `b_rebound` code and no `b_rebound` number, on history or live, existed.

**Code (to be written after this is committed):** the rule key in `engine15/shadows.py` `run()` (a money-path file:
with the key off every line of the old path is untouched, `tests/test_money_path_golden.py` stays green and its record
is not rewritten), the trigger computed from `playbook9.features` outside `run()` and handed in through `aux`, with
`playbook9` imported lazily and only for this book; tests in `tests/test_rebound_book.py`. No `CFG` change, no version
bump; `setups.py`, `signals.py`, `vault_feed.py`, `policy.py`, `backtest.py`, `exits.py`, `config.py` and `live.py`
are not edited.

### H117 note: implementation choices (24 Nov 2026, written with the code, after the registration was committed as 1dac3df)

Nothing in the registered rule was changed. The registration was committed at 13:28 UTC by the laptop's clock (the
heading says "about 13:35"). What the registration left open, and what was seen while building:
- **Where the book lives: not in `shadows.CHALLENGERS`.** The shadow framework cannot restrict a challenger to two
  markets (its loop runs every book on all eight), and that loop is not guarded: one exception in any book stops
  every book's step for the group, `b_targets` included, and then the vault's book is not advanced. So `b_rebound` is
  a module (`engine15/rebound_book.py`) registered in `shadows.MINDS`, the guarded registry H108 added: it is advanced
  after every challenger and follower, inside a try/except, on BTCUSDT and ETHUSDT only, and the summary and the
  scoreboard already show such a book on the markets it has. Its rule is read at every step as
  `dict(shadows.CHALLENGERS["b_targets"]["rule"], rebound=True)` with `b_targets`' own cfg, so it follows the Setups
  rule of the day. Consequences: the tests that run over `CHALLENGERS` do not cover it (its own file does);
  `research/challengers.py` does not list it; `a_alloc` lists it as "not registered" (H110 fixed its books).
- **`engine15/shadows.py` (a money-path file): 109 lines added, none changed or removed.** The doc entry; the guarded
  registration; `REBOUND_KEPT` and `_rebound_state`; and in `run()`: the state read (`rb`, `None` unless the rule key
  is on), two inner functions (`open_rebound`, `rebound_done`), the fill of the override at the open, the bar count,
  the 48-hour exit after the stop and the targets, the trigger and the override before the Setups decision, and the
  state key written for this book only. Every one of those sits behind `rb is not None` (or `rb_live`, which is then
  `False`). No other money file was edited; no `CFG` change; no version bump.
- **That `b_targets` and every other book are unchanged was checked three ways.** (1) `tests/test_money_path_golden.py`
  is green and its record was not rewritten. (2) `tests/fixtures/rebound_main_books.json` was written by the new test
  file run on main's code (commit 46df899, before the rule key existed): all sixteen challengers on the golden bars
  and on a 3,000-bar made-up run (trades, equity, held sides, final state), and a `shadow_state.json` written by
  main's forward step with where every book stood 280 bars later; the test compares the current code with it,
  including loading that file and stepping on. Floats are compared to 1e-9 because the made-up bars come from the
  machine's own `exp`; times, sides and exit words exactly. (3) Once, on the laptop, outside the suite: every
  challenger under BTC's and gold's cfg on the golden bars and three 4,000-bar runs, plus 120 single-bar resumed
  steps each and one forward `advance`, pickled from main's code and from this branch and compared bit for bit:
  129 entries, 88,601 trades, no difference. A fourth test hands every challenger a trigger object that fails when
  touched: with the key off nothing reads it.
- **The order at a trigger's close.** The trigger is read after that bar's own stop and target fills and before the
  Setups decision. When the override acts, or while a rebound long is open, or in the bar it ended, `policy.decide`
  is not called at all. From SHORT the short is closed by the book's own `close()` at the next open and the long
  opened at the same price in the same bar. A LONG book counts the trigger and the Setups rule then decides as
  always, a flip to short included (tested).
- **The trigger's frame.** The step's own bars (`prep["px"]`, the bars the book trades on, which the live step reads
  from the same files `playbook9` reads): `playbook9.TAIL_BARS + 8` bars before the first new bar plus the new bars,
  as that book's own step. Bars that are not numbers are left out. On planted bars the flags equal
  `playbook9.features` on the whole frame and the ATR agrees to 1e-9; a test halves every bar after the deciding one
  and nothing changes. The funding file is read only when a trigger is there; rule B's flag is recorded as true,
  false or unknown (no fresh funding reading), and a file that cannot be read leaves rule A's trigger as it is.
- **The long against `playbook9`.** Bar by bar against `playbook9._open_trade` / `_walk_bar` on planted bars: the
  entry, stop and targets to the last digit, the stop, Target 1 and the share held at every bar, the exit bar, kind
  and price, and R, over all five kinds of exit. The forward book (through `shadows.advance`, with no odds so that
  only the override trades) against `playbook9.replay` from the same start: the same trades one for one, and the
  same count of triggers skipped while a long was open. On the laptop's real bar files the book's own code gives
  H107's two published event trades of 21 Nov 2026 (fills 57,193.99 and 1,613.70; +1.31R and +1.16R): a check of the
  code on trades already published, not a result.
- **Size, fee and R.** On BTC and ETH today the book's fee is 0.10% a side and its leverage cap 1.0, so the long is the
  whole book at 1x, `r_mult` equals H107's R, and `r_h107` equals both (tested). A test with another fee and a cap
  of 5 shows the two R's apart and the quantity following `backtest.leverage` with the trade's own stop distance.
- **Words.** Entry word `REBOUND`. Exits `STOP`, `T1+STOP_BE`, `T1+T2`, `T1+TIME`, `TIME` (`playbook9`'s STOP, T1+BE,
  T1+T2, T1+TIME, TIME). A short the override replaced ends `REBOUND` or `T1+REBOUND`. A `TIME` exit is booked at the
  close of the 192nd bar with that bar's open time as `t_out_ms`, as every exit inside a bar.
- **The comparison's start.** `late_starts.b_rebound.<coin>` keeps `ref_utc` (the close of the book's first live
  step), `own_eq` and `setups_eq` (both books' marked equity at that close); `rebound_book.compare` counts both from
  there. The generic shadow table's "vs main" column for this book is against the fresh main copy since its start,
  as for every late book; the registered line is `vs_setups_book` on the scoreboard row.
- **Added beside the read, not registered:** each rebound long also records what `b_targets` made on its own book
  from the trigger's close to the close of the bar the long ended in (`setups_pct`; `setups_exact` only when both
  ends were single-bar steps). Descriptive, in `override.against_setups_same_bars`; it carries no verdict.
- **After the engine was down** the missed bars are walked one by one, and a trigger among them is taken at the
  rule's own fill; unlike `playbook9` it is not marked late. A trigger at a step whose trigger could not be computed
  is lost; `h117.no_trigger_steps` counts such steps.
- **Limits.** The state keeps the last 50 rebound longs a coin (the trade file keeps all). The rule key was built and
  tested only on top of the Setups rule: with a pullback entry, a flip limit or a delayed fill it is untested, and
  BTC and ETH have none of those.
- **Existing tests changed:** four assertions that list the books of a crypto group's view (`tests/test_shadows.py`
  two, `tests/test_floor_book.py` one, `tests/test_regime_trust.py` one) now include `b_rebound`. Nothing else.
- **Telegram.** The bot's generic closed-trade card will fire for this book as for `b_trend30` and `b_wait_stop`
  (a name was added: "Setups + rebound long (shadow, NOT passed)"); it was not added to `QUIET`. No card of its own.
- **Step cost, measured on the laptop on the real bar files (276,613 bars a coin):** 20 to 35 ms a step for both
  coins, of which the trigger is about 3 ms a coin and the rest is building the book's inputs from the evidence
  frame; 132 ms to catch up 403 bars.
- **Not verified:** nothing was run on the live box, and the live `shadow_state.json` was not seen (the test uses a
  file written by main's own code on planted bars; the laptop's stale copy has the same keys). The full suite was
  not run here. The web tab was not opened: the page block is the generic one. No Telegram card was sent.

### H86 results (24 Nov 2026; run on the LAPTOP, not on the box, 04:54 to 13:35 UTC, 31,287 s; 10,000 draws per group; `research/out/queue/H86/report.md` + `results.json`)

The owner said on 24 Nov 2026 "For those sg box research still pending. Utilise this laptop to start 1": H86 was run
from a worktree at 0a94526 with the box's `fits_today`, bars and evidence store copied over; the per-draw fits overlay
was pre-filled with copies because Windows cannot make the symlinks the script uses (no code changed). Every market's
run passed its gate (`run_is_engine_b_targets: true`). Data end at the last session at or before 2025-11-10 23:45 UTC;
the holdout is not read.

**Conclusion, in the registered words:** the Setups book IS distinguishable from the same book with stops of the
month's typical sizes at random, at p = 0.0025 (primary: pooled mean R per trade over the eight markets, one-sided).
Real -0.0021R a trade on 5,162 trades; placebo median -0.0278R (5%-95%: -0.0425 to -0.0131).
- Halves, pooled: h1 p 0.022 (real +0.010R against -0.014R), h2 p 0.021 (-0.018R against -0.046R).
- Market groups do NOT agree: vault (BTC, ETH) h1 p 0.0006 but h2 p 0.77 (real -0.081R against a placebo -0.061R);
  the other six h1 p 0.52, h2 p 0.0003. Per market (descriptive): ETH p 0.010, USDJPY p 0.049, the rest 0.10 to 0.44.

**Reading.** Stops fitted to the volatility of the moment do better than stops of the same month's sizes handed out at
random; the engine's stop sizing does what it is meant to. This is NOT an edge: the book itself is about flat
(-0.002R a trade). Two caveats registered beforehand apply: the in-month shuffle lets a placebo stop carry volatility
from later in its month (its size was not measured), and R is counted against the stop, so a different stop changes the
unit of the result. By the family's ledger a primary p well below 0.01 is worth a forward test only if it agrees across
halves AND market groups; the halves agree pooled, the market groups do not. No forward test is proposed; nothing in
the engine changes. H85 is still parked on the box at 17,436 of 65,000 draws with the research queue stopped (owner,
24 Nov: "Keep it stop now"); H82 and the void H81 stay in `held/`.

## H118. H107's capitulation-rebound rules A and B, unchanged, on ten more coins and on BTC and ETH's years before October 2019 (registered 25 Nov 2026, about 22:40 UTC (26 Nov, 06:40 on the laptop's clock), before any H118 number was computed)

**Prompted by:** the owner, 25-26 Nov 2026: "test the rebound rule on more coins and years", then "Yes, download".
Research only: nothing in `engine15/`, the books, the vault or the Singapore box changes, whatever the result. A pass
would lead only to a proposal; it changes no live or paper book by itself.

**The question.** H107 found rule A flat after fees on BTC and ETH, 2019-10-01 to 2025-11-10 (123 trades, -0.006R a
trade; lost in the first half, won in the second) and rule B too few (32 trades). Does the SAME rule, with not one
number changed, earn on coins it was never shaped on, and on BTC and ETH's earlier years?

**Seen before this registration (written honestly).** H107's code and its results (section above and
`research/out/h107_capitulation_rebound/results.json`), including its descriptive variants and the 21 Nov 2026 event the
rules were shaped on. H70 (18 rebound-long rules out of an oversold state all lost after fees on BTC/ETH 2020-02 to
2023-06), H71 (no engine reading carried confirmed information in an oversold state; low funding came closest), H113
(Setups shorts in the 48 hours after a rule A trigger: both halves passed, the holdout gave the opposite sign) and H116
(retest rules C1/C2 after a rule A low: too few trades, both lost after fees), as written in their sections. The file
LIST of `data/sources`: hourly close-only files for these ten alts (`binance_<coin>_1h.csv`) exist there; they were not
opened for H118 and no H118 number was computed from them. Nothing from any alt's 15m bars, any alt's funding, or BTC/ETH
before 2019-01-01 has been read or computed; none of those files existed on this laptop when this was written.

**What must be said first.** The rules were shaped on one BTC/ETH event (Nov 2026, holdout). Alt coins move together
with BTC: a BTC crash day is usually a crash day for all ten, so the coins' trades are not independent. The bootstrap
below resamples calendar months with all coins' trades of a month together for that reason, but the coins still count
as one market more than as ten. Fees: the same 0.10% a side on every coin. Alts' real trading costs and slippage, above
all after a crash, are usually higher than BTC's, so this fee is GENEROUS to the rule.

**Data (downloaded after this registration).** Binance SPOT 15m klines from the public host
`https://data-api.binance.vision/api/v3/klines` (the source `engine15/data.py` uses; its fetch pattern: 1000 bars a page,
a pause of about 0.2 s, retries on errors), columns as the engine's 15m files: `ts_ms,open,high,low,close,volume,
taker_buy`. Coins: ADAUSDT, AVAXUSDT, BNBUSDT, DOGEUSDT, DOTUSDT, LINKUSDT, LTCUSDT, SOLUSDT, TRXUSDT, XRPUSDT, each from
its first bar to the bar opening 2025-11-10 23:45 UTC; BTCUSDT and ETHUSDT from their first bar (Aug 2017) to the bar
opening 2019-10-05 23:45 UTC (separate files; the extra five days past 30 Sep only let a trade decided by 30 Sep finish,
also for the 96-hour variant; those bars lie inside H107's window and were already seen). Funding: Binance USDT-M futures
`https://fapi.binance.com/fapi/v1/fundingRate` (symbol, startTime, limit 1000), columns `ts_ms,rate`, for the ten alts,
from each perpetual's first rate. Before a coin's perpetual existed there is no funding and rule B cannot fire (as for
ETH in Oct-Nov 2019 in H107); BTC and ETH have no funding before 2019-09/11, so rule B cannot fire in test 2. If fapi is
refused from this laptop, rule B is "not tested" and only rule A is run. Saved under `data/sources/h118/`
(`<coin>_15m.csv`, `<coin>_funding.csv`, `btcusdt_15m_pre2019.csv`, `ethusdt_15m_pre2019.csv`); the H107 files in
`data/` are not touched. Nothing from 2025-11-11 on is downloaded (the sealed holdout); every input is also cut at the
bar opening 2025-11-10 23:45 UTC (funding: rates set up to that bar's close) before anything is computed. md5 of every
file goes into results.json. Bars are used as Binance gives them: gaps (exchange outages) are not filled, and the rule
counts bars, as H107 does. If the download heads well past 300 MB, it is stopped and reported.

**Rules, trade, fees: exactly H107's, imported from its script.** `REG = {look 16, low_days 30, drop_days 7, drop 10%,
bounce_atr 2.0, hold 192}`: a fresh 30-day low within the last 4 hours, that low at least 10% under the close a week
earlier, close at least 2 x ATR(1h) above it, onset only; rule B = rule A and the last funding rate < 0. Long at the next
open; stop 3 x ATR(14) of 1h bars (`data.resample`, `indicators.atr_wilder`, `data.htf_on_15`); Target 1 at +1R for
half, then the stop to entry from the next bar; Target 2 at +2R; out at the close of bar k+192 otherwise; the stop is
looked at first in a bar; fee 0.10% of notional a side on the entry and on each part's exit; funding not charged; one
trade at a time per rule and coin. The code calls H107's `features`, `walk`, `walk_loop`, `trades_of`, `baseline`,
`summary`, `boot`, `holm`; H107's script is not edited.

**Window.** Deciding bars from 30 days after each coin's first bar (H107's `features` already requires a full 30 days
behind a bar) to the cut 2025-11-10 23:45 UTC; a trade must END by the cut, else it is not taken. Test 2: deciding bars
from 30 days after BTC's / ETH's first bar to 2019-09-30 23:45 UTC; its trades must end by 2019-10-05 23:45. Halves
split at 2023-06-08 00:00 UTC by the deciding bar (H107's).

**Statistics.** Month-clustered bootstrap, H107's method: calendar months (UTC, of the deciding bar) from the first month
any coin of the test can decide to the cut's month, months without a trade included, resampled with replacement with all
coins' trades of a month together; 10,000 draws, seed 20261126; the statistic is summed R over summed trades of the
drawn months; 95% interval = 2.5th and 97.5th percentiles; one-sided p for mean R > 0 = (1 + #{draw - observed >=
observed}) / (draws + 1). Halves: first-half months up to and including June 2023, second-half months from June 2023
(June 2023 is in both lists; each half carries only its own trades). Holm over the two rules (m = 2) on the pooled
whole-window p of test 1. **Baseline (drift), H107's:** for each coin-month with a trade, the same trade entered at
EVERY bar of that coin-month (the trade inside the window); excess = R minus that mean.

**Test 1, the decision: the ten new coins pooled, rule A and rule B, each judged by itself. PASS only if all hold:**
(a) at least 100 trades pooled and at least 30 in EACH half; (b) pooled mean R > 0 in BOTH halves; (c) mean R > 0 on at
least 7 of the coins that have 5 or more trades (if fewer than 7 coins have 5 or more trades, (c) fails); (d) the
Holm-adjusted one-sided p < 0.05; (e) pooled excess over the drift baseline > 0 (point estimate). Fewer trades than (a):
"too few trades to judge" (no pass). Anything else: FAIL.

**Test 2, descriptive, decides nothing: BTC and ETH, Sep 2017 to 2019-09-30 (deciding bars).** Rule A (rule B cannot
fire: no funding): trades, share won, mean R with the month-clustered interval, sum of R, per coin. About two years on
two coins is too short to decide anything; it is reported as such.

**Read-outs.** Per rule, as H107: trades, share won, mean R with interval and p, sum of R, median R, percent return,
exits by kind, longest losing run, deepest fall of cumulative R, months with a trade; pooled / each coin x whole / first
half / second half; by year; signals skipped while a trade was open; the trade list. **Descriptive only:** (1) all 12
coins x all years together: H107's BTC/ETH trades (read from its results.json, not recomputed) plus tests 1 and 2, by
year and by coin; (2) H107's one-setting-at-a-time variants (rebound 1.5 and 2.5 ATR, drop 8% and 12%, hold 24 and 96
hours) on test 1's ten coins.

**Look-ahead guards (H107's two; any mismatch must be fixed before results count).** (i) For every signal bar, up to
200 trigger bars and 40 random bars per coin (tests 1 and 2), the readings (A, B, trigger, ATR) are recomputed on data
cut at that bar (funding at its close) and must equal the full run exactly; (ii) the vectorised trade walk must equal
the bar-by-bar walk on every trade. Mismatches are reported.

**Code:** `research/h118_rebound_more_coins.py` (`--download` fetches the data; the default run reads it). Output:
`research/out/h118_rebound_more_coins/` (`results.json`, `report.md`).

### H118 results (25 Nov 2026 UTC; download 22:42 to 23:20 UTC, 2,262 s, 233.2 MB; run 23:22 UTC on the laptop, 70 s; `research/out/h118_rebound_more_coins/report.md` + `results.json`; data `data/sources/h118/`)

**Verdict by the registered rule: NO PASS. Rule A FAILS and rule B FAILS on test 1 (the ten new coins pooled).** Both
have enough trades; both fail the same three checks: first-half mean R not above 0, fewer than 7 of the 10 coins with a
positive mean, Holm p not under 0.05. Funding was reachable, so rule B was tested. The holdout was not downloaded (last
bar opening 2025-11-10 23:45 UTC; last funding rate 2025-11-10 16:00). Nothing in the engine, the books, the vault or the
box was changed.

Each cell: trades, share won, mean R [95% month-clustered interval], one-sided p for mean R > 0, sum of R.
- **Rule A, ten coins pooled:** 891, 54%, +0.041 [-0.067, +0.152], p 0.245 (Holm 0.491), +36.8R. First half 610, 50%,
  -0.017 [-0.150, +0.125], p 0.615, -10.5R; second half 281, 62%, +0.168 [+0.038, +0.320], p 0.015, +47.3R. Positive on
  5 of 10 coins (AVAX, DOT, LINK, TRX, XRP); every coin has 64 or more trades. Excess over random longs in the same
  coin-months +0.236 [+0.120, +0.351]. Exits: 337 stopped, 98 T1 then entry, 121 T1 and T2, 160 T1 then time, 175 time;
  median +0.202; longest losing run 19; deepest fall of cumulative R -40.1R. By year (trades, mean): 2018 101 -0.211,
  2019 91 +0.158, 2020 76 -0.100, 2021 86 +0.301, 2022 205 -0.087, 2023 103 -0.028, 2024 124 +0.239, 2025 105 +0.156.
- **Rule A per coin (mean R, trades):** ADA -0.021 (125), AVAX +0.094 (80), BNB -0.108 (81), DOGE -0.001 (82), DOT
  +0.087 (85), LINK +0.248 (82; interval [+0.045, +0.464]), LTC -0.041 (114), SOL -0.029 (90), TRX +0.123 (64), XRP
  +0.143 (88). In the second half all ten are positive; in the first half 5 of 10 are negative (ADA, BNB, DOGE, LTC, SOL).
- **Rule B, ten coins pooled:** 284, 53%, +0.022 [-0.137, +0.208], p 0.429 (Holm 0.491), +6.3R. First half 184, 51%,
  -0.007, p 0.562; second half 100, 57%, +0.076 [-0.120, +0.299], p 0.241. Positive on 6 of 10 coins (BNB, DOT, LINK,
  LTC, TRX, XRP). 145 of the 284 trades are in 2022 (-0.077 a trade). Excess +0.209 [+0.035, +0.408].
- **Test 2, BTC and ETH from 16 Sep 2017 to 30 Sep 2019 (descriptive; too short to decide anything):** rule A 65 trades,
  34% won, -0.265 [-0.411, -0.038], -17.3R (BTC 24, -0.233; ETH 41, -0.284); 56 of the 65 trades in 2018 (-0.308 a
  trade). Rule B cannot fire (no funding), 0 trades, as registered.
- **All 12 coins x all years (descriptive; H107's 123 + 32 trades from its results.json plus tests 1 and 2):** rule A
  1,079 trades, 52% won, +0.017 a trade, +18.8R; by year 2018 -0.245 (157), 2019 +0.139, 2020 -0.166, 2021 +0.323,
  2022 -0.128 (249), 2023 -0.015, 2024 +0.254, 2025 +0.165. Rule B 316 trades, +0.040 a trade, +12.5R.
- **One setting at a time on test 1 (descriptive, decides nothing):** rule A's first half stays at or below zero in 5 of
  6 variants (-0.057 to -0.000); only the 24-hour hold is positive in both halves (+0.084 on 621, +0.167 on 282; 903
  trades, 8 of 10 coins positive). That variant was not registered and is one of twelve looked at; it decides nothing.
- **Look-ahead guards:** (i) 3,492 bars recomputed on data cut at the bar over the 12 coins, 0 mismatches; (ii) the
  vectorised walk equals the bar-by-bar walk on every trade (largest difference 4.4e-16 R).

**Deviations (stated honestly).** (1) The registration time is written in UTC as 25 Nov 2026 about 22:40 (26 Nov 06:40
on the laptop's clock), not "26 Nov ... UTC" as the title asked: the 26 Nov date was local time. (2) The brief said the
BTC/ETH pre-2019 files run "to 2019-10-01"; they run to the bar opening 2019-10-05 23:45 so that trades decided by 30 Sep
can finish. This was written into the registration before any download; deciding bars still end 2019-09-30 23:45.
(3) Funding was fetched strictly before 2025-11-11 00:00, so the rate set at exactly 00:00 (the cut bar's close), which
H107's cut would have allowed, is absent. It could only affect the last bar, which cannot open a trade that ends by the
cut. (4) Per-coin bootstrap cells use calendar months from that coin's first deciding month (the registration fixed the
pooled months only); the pooled cells, which decide, use months from the first month any coin could decide (Dec 2017).
(5) A smoke test of the loader on ADA, after the registration and before the download finished, printed the count of
rule A onsets on ADA's bars (203, before the one-at-a-time filter; no R). (6) The first full run crashed in the report
writer (a literal % in a format string) after results.json was written and before any verdict or R was printed; it was
fixed and the whole run repeated. A second fix only changed how variant names print in report.md's table (regenerated
from the same results.json). No rule, number or window was changed by either fix. (7) Data quality: Binance spot gaps are
used as they are (largest 33.8 hours, the Feb 2018 outage on BNB, LTC, BTC and ETH; at most 0.2% of bars missing on an
alt, 0.53% on the BTC/ETH pre-2019 files). The same 0.10% fee on every coin flatters the alts.

**Reading.** On ten coins it was never shaped on, the rebound long behaves as on BTC and ETH: it lost in the first half
and earned in the second, and it is not significant overall (+0.04R a trade on 891 trades). Half the coins lose money
on it over the whole period. On BTC and ETH's earlier years (mostly 2018) it lost clearly (-0.27R a trade on 65 trades).
The pattern is consistent across all twelve coins: the rule earns in years when crashes are bought back (2019, 2021,
2024, 2025) and loses in falling years (2018, 2020, 2022). It beats random longs in the same months, but
mostly because random longs in those crash months lose more. Rule B (negative funding) does not help on the alts. What
looked like H107's second half is a period effect, not an edge that holds across coins and years. Nothing here supports
a paper or live book on the registered bar; the forward books `p9_rebound_a/b` and `b_rebound` remain unsupported by
history, as before.


## H119. The Setups page, the signals and the vault on a trailing-stop book (`b_trail_setups`): the forward read after the switch, and the followable rules of a trail signal (registered 26 Nov 2026, about 04:40 UTC, before the book had run one step, before any trail signal existed and before any switch)

**Prompted by:** the owner, 26 Nov 2026: "Lets switch. But explain to me what is the changed.", "Ok. Lets plan for this
and apply for VIP", then "Page and VIP". The plan and the design: `docs/TRAIL_SWITCH_PLAN.md`.

**This is not a test that decides the switch.** The owner decided it. On 2020-2026 history every tight trail made less
than holding (H36: `b_trail` -$48,808 against the main book's +$329,439; `b_targets` -$28,862). This section fixes, before
any number exists, how the switch is read afterwards, so that the read cannot be shaped by what it shows.

**Seen before this registration (written honestly).** The forward paper record of `b_trail` and `b_targets`, 11-26 Nov
2026, one falling market (trade files on the box, 26 Nov 04:33 UTC): `b_trail` BTC 14 trades 11 won +$2,457, ETH 11 / 8
/ +$2,088, Gold 9 / 8 / +$2,167, Silver 13 / 12 / +$3,021, Brent 8 / 5 / +$475, WTI 7 / 4 / +$288, USDJPY 7 / 4 / +$268,
S&P 3 / 3 / +$764; `b_targets` BTC 9 / 7 / +$1,844, ETH 8 / 4 / +$935, Gold 7 / 5 / +$1,150, Silver 6 / 5 / +$1,980,
Brent 3 / 2 / +$486, WTI 1 / 0 / -$288, USDJPY 6 / 3 / -$196, S&P 2 / 1 / +$304. H36's history. Nothing of
`b_trail_setups` (it does not exist yet) and no trail signal.

**The book.** `b_trail_setups`: `shadows.run` under `{"trail": True, "early": True}`: the main rule's entries, on BTC and
ETH booked at the close that decides them (v5.2.9); no targets; once price has gone 1R in favour the stop becomes, at
each 15-minute close, the tighter of the last confirmed 15m swing and 2 x ATR(14, 15m) from the close, never looser. It
starts flat at its deploy. It differs from `b_trail` only by the early entry on BTC and ETH.

**Read 1: the trail book against the targets book, after the switch.** Markets: those the owner switches. Per market,
from its changeover time (`from_utc` in `data/setups_voice_state.json`): the closed trades of `b_trail_setups` opened at
or after it, against the closed trades of `b_targets` (which keeps running on paper) opened at or after it. Read at 30
and at 60 closed trail trades, all switched markets pooled, each read made once:
- each book's trades, wins, net $ after fees, total R, fees, median hold;
- the difference in total net $ (trail minus targets) over the same span, with a 90% range from a block bootstrap over
  UTC days (a day's trades of both books stay together; 5,000 draws, seed 119);
- the words: "trail ahead" when the range's low end is above zero, "trail behind" when its high end is below zero,
  else "undecided".
A "trail behind" at 60 trades is put to the owner as a proposal to switch back; nothing switches by itself. Before the
switch the same table is shown from the book's deploy as a description only.

**Read 2: the trail signal a person can follow.** H53's record is closed to trail signals: the two are never pooled. A
signal is issued when a market on the trail voice shows a new open setup. It carries the side, the entry E and the stop
S0; 1R = |E - S0|. Rules, fixed now:
1. Entry: a limit at E, filled on the first of the FOUR bars after the alert's bar whose range holds E (as H53).
2. No fill: S0 trades first; or price reaches E + side x 1R in any bar from the book's fill bar up to the fill (the trail
   has armed; a bar that holds both E and that level is a no fill); or the four bars pass; or the book closes first.
3. After the fill there are no targets. In each bar the stop is the one the book had published at the close before that
   bar; the stop is looked at first; a gap through it fills at the bar's open. (When a check is late and several bars
   are processed together, the older, looser stop is used for them.)
4. The book closes its own trade for another reason: the followable trade closes at the open of the bar after the bar
   in which that exit alert was sent (as H53 rule 4).
5. Costs as H53: the market's own fee a side, $10,000 a signal, results in $, % and R on S0.
Judged at 30 closed followable trail trades with the scoreboard's own verdict sentence; fill rate and the share of
"ran first" no fills reported beside it.

**Read 3: real fills (descriptive).** For each member trade the AI Trading session reports: the fill at the join against
the book's entry, and the fill at the stop against the book's exit. No bar is set; the question is how much a moving
stop-market order costs against the paper book.

**Constants declared here, not tuned later.** The trail's own (1R to arm, 2 x ATR(14, 15m), the 15m swing: H36's
`b_trail`). The cards a follower gets for a moving stop: when the trail arms, when the stop first passes the entry, then
whenever it has moved at least 0.5R since the last card.

**What this cannot show.** Thirty or sixty trades in one kind of market say little about the next kind; the history
(H36) is the larger sample and it is against the rule.


### H85 results (26 Nov 2026; run on the box 23 Nov 01:53 UTC to 26 Nov 13:25 UTC with the queue stopped from 24 Nov 04:48 to 26 Nov 05:05 UTC, resumed from its checkpoint; 13,000 draws per group, 65,000 in all; `research/out/queue/H85/report.md` + `results.json`)

Every market's run passed its gate (`run_is_engine_b_targets: true`). Data end at the last session at or before
2025-11-10 23:45 UTC; the holdout is not read.

**Conclusion, in the registered words:** the Setups book is NOT distinguishable from the same book run on time-shifted
bias and tide, at p = 0.1037 (primary: pooled mean R per trade over the eight markets, one-sided). Real -0.0021R a trade
on 5,162 trades; placebo median -0.0278R (5%-95%: -0.0564 to +0.0060). The real book sits on the better side of the
placebo, but inside what chance gives.
- Halves, pooled: h1 p 0.11 (real +0.010R against -0.020R), h2 p 0.25 (-0.018R against -0.038R).
- BTC and ETH: all p 0.13; h1 p 0.051 (+0.045R against -0.023R); h2 p 0.59 (-0.081R against -0.071R: no better than the
  shifted bias). The other six: all p 0.19; h1 p 0.39, h2 p 0.18.
- Per market (descriptive): ETH p 0.031, USDJPY 0.11, SPX 0.14, the rest 0.37 to 0.63; BTC 0.49.
- The placebo trades more (median 6,006 trades against 5,162): a bias that is wrong in time flips and forces more.

**Reading.** The higher-timeframe bias and the tide decide the side of most entries, yet shifting them in time by a
month or more leaves a book that cannot be told from the real one at the registered bar. That is the same picture as
the card post-mortem of 26 Nov (the Lead did no better than always leaning with the fall): on this history the
direction inputs carry little that their moment gives them. It is not proof that they carry nothing: the real book is
better than nine placebo draws in ten, and the first half comes close on BTC and ETH. One of seven placebo tests in
this family (ledger above); no change follows from it alone.
