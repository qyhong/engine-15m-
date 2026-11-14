# Playbook: liquidation hunt (P1) and breakout trap (P2)

Owner, 11 Nov 2026: "include strategy to profit from liquidation hunt. Also, breakout trap."
Two standalone, rule-based paper books on 15-minute bars, on all six markets (BTC, ETH, gold,
silver, USDJPY, S&P 500). Paper only. Code: `engine15/playbook.py` (interface:
`docs/PLAYBOOK_INTERFACE.md`). History: `research/playbook_study.py` ->
`research/out/playbook.md` / `.json`. Tests: `tests/test_playbook.py`.

**The short version: neither book cleared costs on history, in either half, on any market,
except the P2 version that was finally picked, which made money on silver in both halves and
traded too rarely to say anything (about 115 trades a half across all six markets).** Before costs,
P1 averages about zero per trade and P2 about +0.01% to +0.05%. A 15-minute stop costs only
0.2% to 0.4% of price, so the 0.20% crypto round trip eats 0.5R to 0.7R of every trade. They run
forward because the charter says forward results decide, not because history supports them.

---

## P1. Liquidation hunt (stop-run fade)

**What it looks for.** Stops and liquidation levels collect around prices that everyone can see:
the last swing high or low, yesterday's high and low, the 24-hour and 7-day extremes, and round
numbers. A fast push through such a level sets those orders off. The resting orders turn into
market orders in the direction of the push. If nobody follows through, price snaps back once
they are filled. What is left is a long wick through the level and a close back on the near side.

**Why it might work.** The push is fuelled by forced orders, not by new opinion. Once the stops
are used up there is nothing left to buy (or sell), so the move fades. The traders who were
stopped out, or who chased the break, then add to the move back.

**Exact rule (registered variant `k0.25 m2 fixed +funding`).** All on closed 15m bars:
1. Pools, each known at the close of the bar before (swings only once confirmed, 5 bars later):
   the last confirmed 15m swing high/low (5 bars each side), the 24h high/low and the 7-day
   high/low (bars before this one), the prior UTC day's high/low, and the next round number
   above/below the prior close (largest 1 / 2.5 / 5 x 10^n step not above 2% of price, as in levels.py).
2. Sweep above (mirror for below): price was below the pool at the prior close; a bar trades
   above the pool; the highest high reaches at least the pool + 0.25 x ATR(14, 15m), with ATR
   taken at the prior close; and the sweep bar, or one of the next 2 bars, CLOSES back below the
   pool. Every bar in between must still close at or above it.
3. Wick: read the bars from the sweep bar to the reclaim bar as one candle. Its upper wick (high
   minus the larger of the sweep bar's open and the reclaim close) must be at least 50% of its range.
4. Confirmation, BTC and ETH only: the newest funding rate is in the top fifth of its last 90
   settlements (30 days) for a short, or the bottom fifth for a long. In other words, the crowd on
   the side that was swept is paying to be there. Gold, silver, USDJPY and the S&P have no funding,
   so they trade without this filter.
5. Trade: SHORT at the next open. The stop goes at the sweep's high + 0.1 x ATR(15m), with ATR taken
   at the reclaim bar. Half comes off at 1R and the rest at 2R. Once 1R is taken, the stop moves to
   the entry from the next bar. Whatever is still open after 16 bars (4 hours) closes at the next open.
6. If several pools are swept at once, the furthest one names the setup. One open trade per asset.

**History (2020 to 10 Nov 2026, after each asset's cost; first half before 7 Jun 2023):**

| Asset | Half | Trades | Win % | Avg R | PF | Exp. % / trade | Before costs % |
|---|---|---|---|---|---|---|---|
| BTC | 1st / 2nd | 2,291 / 2,166 | 43.3 / 33.6 | -0.39 / -0.69 | 0.59 / 0.40 | -0.183 / -0.191 | +0.017 / +0.010 |
| ETH | 1st / 2nd | 2,383 / 2,429 | 46.4 / 37.9 | -0.31 / -0.53 | 0.68 / 0.46 | -0.171 / -0.220 | +0.029 / -0.020 |
| Gold | 1st / 2nd | 4,753 / 4,803 | 43.5 / 45.3 | -0.36 / -0.31 | 0.58 / 0.66 | -0.046 / -0.042 | -0.006 / -0.002 |
| Silver | 1st / 2nd | 5,380 / 5,358 | 46.2 / 47.4 | -0.27 / -0.23 | 0.66 / 0.73 | -0.076 / -0.066 | -0.016 / -0.006 |
| USDJPY | 1st / 2nd | 4,487 / 4,419 | 45.0 / 45.6 | -0.34 / -0.31 | 0.63 / 0.65 | -0.019 / -0.020 | +0.001 / +0.001 |
| S&P 500 | 1st / 2nd | 1,666 / 1,518 | 47.2 / 43.5 | -0.24 / -0.38 | 0.73 / 0.66 | -0.058 / -0.049 | -0.018 / -0.009 |

It fires very often: 37 to 131 trades a month per market. Every session (Asia, London, New York,
late) and every pool type is negative after costs in both halves. Round numbers are the worst
(about -0.11% a trade). Prior-day highs and lows are the least bad (-0.03% to -0.07%).

## P2. Breakout trap (failed breakout)

**What it looks for.** Price closes beyond a level everyone watches, so breakout traders buy the
close and put their stops just under the level. Within a bar or two it closes back inside. Those
traders are now trapped: the trade has failed, and their stops sit right where price is heading.

**Why it might work.** A failed break shows there was no follow-through beyond the level. When the
trapped traders exit, they push price back toward the middle of the range. It is the setup that
graded best in `research/setup_stats.py` (failed breakout, BTC 53.1% long / 52.2% short).

**Exact rule (registered variant `pday j2 fixed +with_bias`).**
1. Level: the prior UTC day's high (mirror: low), known from the first bar of the new day.
2. Breakout: a bar closes above the level after the bar before closed at or below it.
3. Trap: within the next 2 bars, a bar closes back below the level (bars in between still above).
4. Filter: the trade must be on the side of the engine's v5 higher-timeframe bias (SHORT bias =
   1h, 4h and 1d trend scores all <= -0.5 and price below the 1h EMA50, 4h EMA20 and 4h EMA50; LONG
   is the mirror). So the breakout went against the bias and failed.
5. Trade: SHORT at the next open. The stop goes at the highest high from the breakout bar to the reclaim
   bar + 0.1 x ATR(15m). Half comes off at 1R and the rest at 2R, with the stop moved to the entry
   after 1R. The trade closes at the next open after 24 bars (6 hours).

**History (same frame):**

| Asset | Half | Trades | Win % | Avg R | PF | Exp. % / trade |
|---|---|---|---|---|---|---|
| BTC | 1st / 2nd | 1 / 5 | - | - | - | -1.71 / -0.01 |
| ETH | 1st / 2nd | 2 / 1 | - | - | - | -0.86 / -1.62 |
| Gold | 1st / 2nd | 32 / 28 | 34.4 / 39.3 | -0.51 / -0.38 | 0.68 / 0.48 | -0.037 / -0.054 |
| Silver | 1st / 2nd | 28 / 28 | 57.1 / 64.3 | +0.01 / +0.15 | 1.90 / 1.79 | +0.121 / +0.095 |
| USDJPY | 1st / 2nd | 22 / 20 | 40.9 / 40.0 | -0.44 / -0.47 | 0.59 / 0.57 | -0.033 / -0.030 |
| S&P 500 | 1st / 2nd | 30 / 29 | 70.0 / 31.0 | +0.58 / -0.59 | 4.24 / 0.35 | +0.313 / -0.171 |

The filter was picked because the first half scored +0.09% against -0.06% for the unfiltered
rule. That score rests on 115 trades, and the S&P's first-half run did not repeat (+0.31% then
-0.17%). On crypto it almost never fires: a prior-day high close above while every timeframe
trends down is rare. Disclosed second look, not used to choose: the unfiltered base `pday j2
fixed` is negative after costs on all six markets in the second half (-0.01% to -0.18% a
trade, 330 to 848 trades), though positive before costs on five of them.

## How the variants were chosen (the luck count)

29 variants were tried: 11 for P1 and 18 for P2, all listed in `research/out/playbook.md`.
- P1 base grid: sweep depth k in {0.10, 0.25} x ATR, reclaim within m in {0, 2} bars, exits
  {struct: half at the session VWAP or 24h mid, rest at the far side of the 24h range; fixed: 1R/2R}.
  The confirmations were then tried one at a time on the chosen base: volume >= 2x its 20-day median
  for that 15-minute slot, taker flip (the reclaim bar's takers lean against the sweep), and funding extreme.
- P2 base grid: level {48-bar range, prior day, last confirmed 15m swing} x j in {2, 4} x the same
  two exits. Then six filters, one at a time: breakout volume < 1x, breakout volume >= 1.5x, with the
  bias, against the bias, a London or New York open window, and shallow (<= 0.5 ATR beyond the level).
- The rule was fixed before the first run. Pick the base with the best mean (over assets with 20 or
  more trades) of first-half expectancy after costs, needing 100 or more first-half trades in all.
  Add a filter only if it lifts that score by at least 0.02 points with 100 or more trades kept.
  Then report the second half untouched.
- **Not testable on history:** the open-interest drop / liquidation proxy (`lq_*`). Binance serves
  only about 30 days of open-interest history; the file holds 2,939 bars from 11 Oct 2026. It is
  left for forward data.

Truncation test: the registered rules re-run on history cut 400, 120 and 9 days before the end
reproduced all 26,777 trades closed before each cut exactly.

## Limits

- Fills are at the next open with no slippage. Real stop-run fades happen in fast markets, so real
  fills would be worse.
- A stop and a target in the same bar count as the stop first. Pessimistic, but 15m bars hide the path.
- Metals, USDJPY and the S&P use their data source's volume (often tick volume), which changes over
  the years. Round numbers and "24h" mean less on the S&P's 6.5-hour session, and entries can come
  after an overnight gap.
- The live books start reading 450 days before registration (fixed anchor). On the S&P the daily
  EMA200 inside the bias is not ready that early, so the bias there leans on fewer averages.
- Funding paid while holding is ignored (16-24 bars at most).

## Live books

`playbook.step(bars, now_ms=None) -> rows` recomputes both books from the bars for every asset
since 11 Nov 2026. It is stateless: the same bars give the same rows. `playbook.page_block(rows)`
gives open setups, the last 5 trades and totals per book, ready for page.json. Each row carries a
sentence, for example: "Liquidation hunt, ETH: 14:00-14:30 bars dropped to 2,114.5 below the round
number 2,125.0 and closed back at 2,126.7 with a 72% lower wick and 1.1x volume, funding at the 7th
percentile of its last 30 days: LONG 2,126.7, stop 2,113.5, T1 (1R) 2,139.8, T2 (2R) 2,153.0."

---

## DRAFT register entries (for the main session to copy into research/HYPOTHESES.md)

### H6. Liquidation hunt: fade a stop-run through a liquidity pool (registered 11 Nov 2026)

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

### H7. Breakout trap: trade a failed prior-day breakout with the higher-timeframe bias (registered 11 Nov 2026)

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
