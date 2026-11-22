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
