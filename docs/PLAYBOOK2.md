# Strategy books, batch 2: opening range breakout, S&P gap fill, squeeze breakout

Status: built 11 Nov 2026, **paper only**, registered to run forward from 11 Nov 2026. Charter task K
(batch 2). Code: `engine15/playbook2.py` (interface: `docs/PLAYBOOK_INTERFACE.md`). History:
`research/playbook2_study.py` -> `research/out/playbook2.md` / `.json`. Tests: `tests/test_playbook2.py`.

**The short version.** None of the three books clears costs in the second half of history. The
registered version of each was chosen on the first half (2019 to 6 Dec 2022) and then lost money
after costs in the second half (6 Dec 2022 to 11 Nov 2026). Before costs, several were slightly
positive, so costs are what kill them. 130 variants were tried in all. They run forward as paper
books only so that the forward record, not the history, gives the verdict (charter: "forward results
decide; the history replay can reject an idea, never prove one").

## The frame every book shares

- **Bars and fills.** 15-minute bars, closed bars only. The decision is at the close of a bar; the
  fill is at the next bar's open. If that open is already beyond the stop, there is no trade.
- **Stop first.** If a bar touches both the stop and a target, the stop counts. A gap through the
  stop fills at the open (worse than the stop).
- **One trade at a time** per book per market. $10,000 a trade, full size.
- **Costs.** Each market's own fee a side: BTC and ETH 0.10%, gold 0.02%, silver 0.03%, USDJPY 0.01%,
  S&P 500 0.02%. All results below are after costs. "R" = the result in dollars divided by the
  dollar risk to the stop, so -1R is a full stop-out and fees push it a little below -1.
- **Minimum stop.** A trade needs its stop at least four one-side fees away (0.40% for crypto,
  0.08% for gold and the S&P, 0.12% silver, 0.04% USDJPY), so the round trip never costs more than
  half of 1R. Tighter setups are skipped. Declared once, not tuned.
- **No position through a market close.** A trade still open when the market shuts for more than 3
  hours (a weekend, the S&P overnight) is closed at the close of the last bar before it. A time
  exit fills at the close of the window's last bar.
- **Target schemes** (tested in the grids): everything at 1R; everything at 2R; "split" (half at 1R,
  the rest at 2R, the stop moved to the entry from the bar after 1R fills); "reach" (everything at
  the realistic-reach target: how far price has typically travelled in this window lately).
- **Higher-timeframe bias** (a filter): the engine's v5 bias. Long bias when the 1h, 4h and daily
  trend scores are all at least +0.5 and price is above the 1h EMA50 and the 4h EMA20 and EMA50;
  short bias the mirror. Higher bars count only once closed.

## P3: Opening range breakout (`p3_orb`, draft H8)

**What it looks for.** The first minutes after a market opens set a range. When price closes outside
that range, trade in that direction.

**Why it might work.** At an open, overnight orders and the local session's first flows arrive at
once. If one side wins the first half hour, the move can carry for hours, and the range gives a
natural, nearby stop.

**Session opens.** S&P 500: the cash open 09:30 New York. Gold, silver, USDJPY: London 08:00 London
time. USDJPY also: Tokyo 09:00 (00:00 UTC). BTC, ETH: the US equity open (13:30 UTC in US summer,
14:30 in winter, NYSE trading days) and 00:00 UTC. Daylight saving is handled for New York and
London separately (in March and late October they change on different weekends).

**The registered rule.** Opening range = the first **30 minutes**. Trade the first 15m close outside
it, at the next open, **only in the direction of the higher-timeframe bias**. Stop at the range's
**opposite side**. Target **2R** (all of it). Flat by the session end: 16:00 New York for the S&P
(13:00 on half days), 8 hours after the open elsewhere.

**History (registered rule, after costs):**

| Market | Half | Trades | Win % | Avg R | Profit factor | Expectancy $ |
|---|---|---|---|---|---|---|
| BTC | first / second | 388 / 292 | 40.5 / 41.8 | -0.071 / -0.097 | 0.91 / 0.94 | -6.26 / -3.28 |
| ETH | first / second | 367 / 283 | 39.8 / 35.7 | -0.088 / -0.225 | 0.89 / 0.77 | -8.67 / -16.83 |
| Gold | first / second | 165 / 198 | 41.2 / 35.9 | -0.018 / -0.200 | 1.04 / 0.77 | +0.68 / -4.29 |
| Silver | first / second | 153 / 215 | 38.6 / 34.4 | -0.061 / -0.185 | 0.78 / 0.78 | -8.02 / -8.76 |
| USDJPY | first / second | 354 / 372 | 43.2 / 39.0 | -0.066 / -0.166 | 1.06 / 0.76 | +0.46 / -2.27 |
| S&P 500 | first / second | 258 / 261 | 41.1 / 48.7 | -0.139 / -0.034 | 0.58 / 0.88 | -10.33 / -1.98 |

**Verdict: does not clear costs.** Negative after costs on every market in the second half. Not one
of the 19 variants had a positive average across markets in either half. The bias filter keeps
about one breakout in six (BTC: 388 of 2,165 in the first half). The 30-minute range beat
the 15-minute one, and the far stop beat the middle stop, in every pairing.

**A lead, not a result.** Split by session, the crypto trades at the US equity open were positive
after costs in both halves (BTC +0.03R then +0.12R; ETH +0.03R then +0.07R, about 120 to 160
trades each), while the 00:00 UTC session lost heavily. This was found by looking at the breakdown,
which is itself more variants, so it is not registered here. If wanted, it becomes its own
hypothesis and is graded forward only.

## P4: S&P 500 overnight gap fill (`p4_gapfill`, draft H9)

**What it looks for.** The S&P cash index opens away from yesterday's 16:00 close (a gap). The trade
bets that price goes back to yesterday's close (the gap "fills").

**Why it might work.** Overnight futures moves are made in thin trading. When the full cash market
opens, part of that move is often given back, especially moderate gaps with no news behind them.

**The registered rule.** When the cash open gaps between **0.25 and 1.00 hourly ATRs** (ATR(14) of
the 1-hour chart, as known at the open) from yesterday's close, wait **30 minutes**. If the 10:00
close is back toward yesterday's close (below the open after a gap up, above it after a gap down),
and the gap has not already filled, trade toward the fill at 10:00. Stop beyond the first 30
minutes' extreme (the high after a gap up). Target **yesterday's close** (the full fill). Flat by 16:00.

**History (registered rule, after costs):**

| Half | Trades | Win % | Avg R | Avg R before costs | Profit factor | Expectancy $ |
|---|---|---|---|---|---|---|
| first | 66 | 63.6 | +0.020 | +0.206 | 0.94 | -0.61 |
| second | 90 | 60.0 | -0.097 | +0.135 | 0.78 | -2.00 |

**Verdict: does not clear costs.** It wins often (60%+) and is positive before costs in both halves,
but its stops are tight, so the 0.04% round trip costs about 0.2R a trade. It was the only one of
44 variants with a positive first half, so its +0.02R is what you would expect from the best of 44
by luck. The "gap and go" side (trade with a gap that holds 30 minutes) was in the same grid and
was worse. About 1.5 to 2 trades a month, so a forward verdict will take more than a year.

## P5: Squeeze breakout (`p5_squeeze`, draft H10)

**What it looks for.** A quiet stretch when the Bollinger bands (20, 2 standard deviations) sit inside
the Keltner channels (20, 1.5 average true ranges): volatility is compressed. When the squeeze
releases, trade the breakout.

**Why it might work.** Volatility comes in clusters: quiet periods tend to end in larger moves, and the
squeeze's own high and low give a stop.

**The registered rule.** Squeeze on the **1-hour** chart for at least **6 hours**. After it releases,
trade the first 15m close beyond the squeeze's high or low (within 2 hours), at the next open, **only
between 08:00 London and 16:00 New York**. Stop at the squeeze range's opposite side. Target **2R**
(all of it). Time exit after **32 bars** (8 hours); never held through a market close.

**History (registered rule, after costs):**

| Market | Half | Trades | Win % | Avg R | Profit factor | Expectancy $ |
|---|---|---|---|---|---|---|
| BTC | first / second | 197 / 208 | 45.7 / 34.1 | +0.001 / -0.140 | 0.96 / 0.62 | -4.10 / -27.43 |
| ETH | first / second | 172 / 205 | 43.6 / 42.9 | +0.004 / -0.020 | 1.01 / 0.90 | +1.09 / -8.44 |
| Gold | first / second | 178 / 152 | 46.6 / 44.7 | -0.075 / -0.071 | 0.91 / 0.82 | -2.22 / -4.90 |
| Silver | first / second | 187 / 189 | 46.5 / 41.3 | +0.052 / -0.042 | 1.11 / 0.80 | +4.41 / -10.43 |
| USDJPY | first / second | 179 / 164 | 46.4 / 45.7 | -0.017 / -0.002 | 0.97 / 0.96 | -0.32 / -0.41 |
| S&P 500 | first / second | 41 / 42 | 51.2 / 52.4 | +0.038 / +0.036 | 1.96 / 1.57 | +12.90 / +7.70 |

**Verdict: does not clear costs overall.** The mean across markets was about zero in the first half
(+0.001R) and -0.040R in the second; only the S&P stayed positive, on about 40 trades a half, too few
to mean much. The 1-hour squeeze beat the 15-minute one in every pairing (15-minute squeezes lost
0.09R to 0.15R). The session filter was kept because it lifted the first-half score, but by
+0.002R, which is noise (it changes nothing on the S&P, whose bars are all inside that window).

## Variants tried (count all of them)

| Book | Stage 1 (base grid) | Stage 2 (filters on the stage-1 winner) | Total |
|---|---|---|---|
| P3 ORB | range 15/30 min x stop far/mid x target 1R/2R/split/reach = 16 | narrow range, HTF bias, S&P gap direction = 3 | 19 |
| P4 gap fill | 4 gap bands x (fill: now/15 min/30 min x half/full/split; go: 1R/2R) | none | 44 |
| P5 squeeze | 15m/1h x N 6/12 x break/MACD x 1R/2R/split/reach x hold 16/32 = 64 | volume surge, HTF bias, London-New York session = 3 | 67 |
| **All** | | | **130** |

How the choice was made, fixed before the run: highest mean over markets of first-half average R
after costs, with at least 30 first-half trades on every market (20 for the filters). A filter was
kept only if it lifted that score. Nothing was re-chosen after looking at the second half.

## Limits

- History can reject a rule, not prove one. The second half here already rejects all three as
  written; the forward run tests whether that holds.
- No slippage beyond the fee; fills at the next open exactly; S&P and metals fills assume the CFD /
  futures price is tradable at the cash-index level.
- Data: gold, silver, USDJPY and the S&P are Dukascopy prices except for the last ~60 days, which
  are Yahoo (`docs/EXTDATA.md`). The S&P history is the cash session only; its gap is measured from the cash
  bars, not the futures (the overnight futures card, `sources/overnight.py`, is not used here).
- Holidays for gold, silver and USDJPY are not modelled (a holiday reads as a normal session).
- The volume filter (P5) does not apply to USDJPY (its live feed has no volume). Volume for the
  other non-crypto markets changes source at the data join, so the filter means slightly different
  things before and after.
- The S&P 1-hour chart has only 7 bars a day, so P5 trades the S&P rarely (about 1 a month).
- The higher-timeframe bias needs about 200 days of bars to be fully formed; the live book reads
  450 days back from registration.
- In the live book a setup appears only once it is decided (status WAITING: filled at the next open).
  A range that is set but not yet broken is not listed.
- Funding paid or received on a crypto position is not charged.

## Hooking it in (for the main session)

```python
from engine15 import playbook2
rows = playbook2.step(bars, now_ms)          # bars = {asset: 15m frame}; rows since 11 Nov 2026
page["playbook2"] = playbook2.page_block(rows)
```

Rows carry the interface's fields plus `t1_name`, `t2_name`, `t1_hit`, `est_entry` (WAITING rows) and
`session`. `exit_utc` is the open of the bar in which a stop or target filled, or the close time for a
time exit. A live step over all six markets takes about 2 seconds.

## DRAFT hypothesis entries (for `research/HYPOTHESES.md`; not yet copied there)

Count note for the register: these add 3 ideas (H8 to H10) and **130 variants tried on history**
before registration (`research/out/playbook2.md`).

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
