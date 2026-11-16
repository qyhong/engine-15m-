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
