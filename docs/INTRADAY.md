# Workstream M: the intraday mind

Owner, 11 Nov 2026: "explore to improve the engine's analysis and intelligence on trading the lower
timeframe, where trading more brings more profitability also - rather than just better timing but doing
almost the same as on the 4h or daily chart."

Paper only. Nothing here is a claimed edge: history can reject an idea, never prove one; forward
results decide (docs/CHARTER.md).

## What was wrong with "15m timing"

The main engine asks one question at every 15-minute close: "over the next 24 hours, will price first
move 1.5 x ATR(1h) up or down?" It then holds until the other side leads by 10 points, often for days,
and takes no profit. That is a slow trend-follower that happens to look every 15 minutes. Its replay
money came from a few long holds. Earlier tries to make it trade more (profit targets and trailing
stops on the same 24-hour signal; twelve stand-alone 15m rule books) lost money: more trades, more
fees, and the signal was never about the next hour.

## What the intraday mind does differently

**It asks shorter questions (M1).** The same readings and the same ten voting cards (plus the owner's
view) are trained again, from scratch, on two new questions:

| Mind | Question | Barrier each side | Graded within |
|---|---|---|---|
| 1h mind | will price first move one barrier up or down within the next hour? | 0.75 x ATR(1h) | 4 bars |
| 4h mind | the same, within the next four hours | 1 x ATR(1h) | 16 bars |
| main engine (for comparison) | the same, within 24 hours | 1.5 x ATR(1h) | 96 bars (S&P: 26) |

Why 0.75 x ATR(1h) and not 1 x ATR(15m) for the hour: they are about the same size (an hour's range
is roughly twice a 15-minute bar's), but the 1h ATR is the yardstick the rest of the engine uses and
does not jump on one wide bar, so the stop it sets is steadier, and it stays a little further above
the round-trip cost (one ATR of a 15m bar on BTC is often no wider than the 0.20% crypto round trip).

Each card's voice is refitted once a week (UTC Monday 00:00) on every call already graded, trust follows
recent error exactly as in the main engine, and the mix of the voices is the mind's odds.
Code: `engine15/intraday.py` (`mind_odds`, `walk`, `fit_voices`, `mix_odds`).

**It prices every trade before taking it (M2).** For each side:

    EV (in R) = P(target side first) x 1  -  P(stop side first) x 1  -  round-trip cost / stop distance

A call that runs out of time ("neither") counts as 0 R before costs. A trade is allowed only when EV
clears a margin. This is where the cost of each market enters: crypto pays 0.20% a round trip, gold
0.04%, silver 0.06%, USDJPY 0.02%, the S&P 0.04%, oil 0.08%. On a 0.4% stop, crypto's round trip
alone is half a stop (0.5 R); USDJPY's is 0.05 R.

**It manages each trade as a swing (M3)** (`intraday.run_swing`):

- Entry: at the next 15-minute open, only when EV clears the margin (1h mind 0.05 R, 4h mind 0 R); never
  in the hour before a
  high-impact US release (the engine's release guard).
- Stop: the last confirmed swing beyond the entry (15m swings for the 1h mind, 1h swings for the 4h
  mind), 0.1 barrier beyond it, when it lies 0.5 to 1.5 barriers away; otherwise 1 barrier.
- Target: 1.5 x the stop distance for the 1h mind, 1 x for the 4h mind (the 4h choice was made on the
  first half of history; the realistic reach of the candle card was one of the variants tried); a stop and a target touched inside one bar count as the stop (the cautious reading).
- Clock: out at the open after the horizon (4 bars / 16 bars). If at that moment the same side still
  clears the margin, the trade is kept and the clock restarts (no fees for a pointless exit and re-entry).
- Re-entry: allowed at any later close.
- No mandate: the swing books may stay flat for as long as nothing clears the margin. The owner's
  always-positioned rule stays with the main book; forcing entries into a book whose whole point is
  to pay costs only for priced trades would defeat it.
- Size: `backtest.leverage` on the stop distance (about 2% of equity at risk, 1x to the asset's cap).

**It runs forward on all eight markets (M5)** as two shadow books, `m_swing_1h` and `m_swing_4h`, beside
the main book and the `y_4h` / `y_1d` yardsticks (`engine15/shadows.py`). Their closed trades go to
`out/live/shadow_trades_m_swing_*` and therefore onto the forward scoreboard. The odds are computed
inside the live step from the step's own evidence; fitted weeks are cached in
`data/intraday_minds_<group>.json`, so a normal step only predicts and re-weighs trust.

**It reports which clock it reads best (M6).** Every step keeps the hit rate and the claimed-edge
hit rate of the 1h, 4h and 24h calls per market over the last 7 and 30 days
(`data/horizon_skill_live.json`); once a week `research/out/horizon_skill.md/.json` is written and
page.json carries a small `horizon_skill` block.

## Results on history (M4)

Full tables: `research/out/intraday.md` / `.json` (`research/intraday_study.py`, run 11 Nov 2026 on all
eight markets, 2020-01-01 to 10/11 Nov 2026; halves split on 7 Jun 2023, the same date for every market).
In-sample history: it can reject an idea, never prove one.

**Which clock the voices read (M1).** Direction hit rate on calls graded up or down, first / second half:

| Market | 1h mind | 4h mind | 24h question (same voices) |
|---|---|---|---|
| BTC | 55.3 / 54.2 | 51.9 / 51.2 | 51.0 / 50.6 |
| ETH | 55.4 / 55.2 | 51.3 / 52.0 | 50.5 / 50.9 |
| Gold | 51.3 / 50.8 | 50.8 / 50.8 | 49.5 / 50.3 |
| Silver | 50.9 / 52.9 | 50.3 / 51.0 | 48.2 / 49.8 |
| USDJPY | 51.8 / 50.5 | 50.7 / 50.0 | 49.8 / 49.7 |
| S&P 500 | 51.9 / 52.7 | 50.2 / 49.8 | 49.0 / 51.2 |
| WTI | 49.1 / 49.1 | 50.2 / 49.4 | 50.0 / 50.1 |
| Brent | 49.1 / 49.1 | 50.1 / 49.4 | 50.2 / 49.8 |

Read plainly:

- **Crypto's next hour is the one steady read** found here: about 55% right in both halves for BTC and ETH,
  in every session and most regimes. The voices that carry it are trend, stretch (mean reversion),
  momentum and order flow (each about 54% alone).
- Everywhere else the short-horizon minds are close to a coin flip on direction. What the voices do
  know at short horizons is **whether** price will move at all (volatility, candle size, time of day:
  the risk, candles and clock cards), not **which way**.
- The odds are timid: outside crypto, 95% of calls claim an edge under 2 to 4 points; a "claimed edge"
  of 5 points is rare (often none at all in a half), so the claimed-edge hit rates are mostly noise.

**Does any of it pay its costs? (M2)** EV after costs cleared 0.05 R on **0% of sessions for every 1h
mind, in both halves, on all eight markets**. The 4h mind cleared it on 0 to 0.7% of sessions in the
first half and 0 to 0.13% in the second. Crypto's 55% is real enough to show in both halves but far too
small for taker fees: a rough sum, (1 - 61% "neither") x (2 x 0.55 - 1), is about +0.04 R a call before
costs, against a round trip of about 0.37 R (BTC's 1h barrier is a median 0.54%; the round trip 0.20%).
Even maker-like fees (0.02% a side, about 0.07 R) would eat it. This is the same wall the twelve 15m strategy
books hit.

**The swing book (M3/M4).** 48 variants tried (stop at structure or 1 barrier x target 1R, 1.5R, 2R or
the realistic reach x margin 0, 0.05, 0.10 R, for each mind), one chosen per mind on the first half,
pooled over all markets:

- 1h mind: no variant reached the 300 first-half trades needed to choose one (most: 296 in 3.4 years,
  because so few trades pass the cost filter). The rule declared before the read stands.
- 4h mind: chosen `structure stop, 1R target, margin 0`: 1,969 trades, **+0.004 R before costs, -0.054 R
  after** in the first half; 566 trades, -0.011 R before, **-0.064 R after** in the second. Profit factor
  after costs 0.89 / 0.87. **It does not clear costs.**
- Market x session: no cell is positive after costs in both halves with at least 30 trades in each.
  Small leads only (fewer than 30 trades in a half, picked after looking): gold in the London/New York
  overlap (+0.22 / +0.12 R), silver in London (+0.29 / +0.09 R), WTI in the New York session
  (+0.10 / +0.20 R).

**What this means for the owner's goal.** On this evidence, "trading more" with these readings does not
bring more profit at any market's cost: the readings do not tell the next one to four hours' direction
well enough, except crypto's next hour, where the edge is about a tenth of the fee. The intraday mind
is therefore registered and run forward as an honest test, not as an improvement. What might change the
picture (not done here): a cheaper way to trade crypto's 1h read (maker fills, charter E); readings
built for direction at short horizons (order flow and liquidations at finer grain); or using the
short-horizon volatility read (which the voices DO have) to size or time the main book's trades.

**Limits.** In-sample history; the main engine's constants and the voting cards were chosen on this
history already. The study refits every 4 weeks (live: weekly) and builds the evidence in 6-month pieces
(3 months for crypto) with 300 days of warm-up, so the slowest readings (the weekly trend's 100/200-week
averages) are read with fewer parts than live. Fills at the next open, no slippage, no funding. Bars are
counted, not hours, so on the S&P the 4h clock can cross the overnight gap. 48 swing variants, 3 margins
in the EV table and 3 minds were tried: count them.

**Live cost (M5).** Measured on USDJPY with all history loaded as the live step does: 7.3 s for the
first step after a restart (13 to 14 weekly fits for each mind, then cached in `data/`), then 0.3 s a step
per market group; the two swing books add about 0.002 s per market. Expect about 35 s once after the loop
is restarted, then 1 to 3 s a step across the five groups.

## Draft hypothesis entries (for research/HYPOTHESES.md; not entered there by this workstream)

Counting: this workstream tried 3 minds x 8 markets for skill, 3 EV margins, and 48 swing-book
variants (24 per mind) on history before registering the two rules below.

### H18. The 1h swing mind (registered 11 Nov 2026; FORWARD)

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
