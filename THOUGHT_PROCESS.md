# Mind 15: how the engine thinks

A 15-minute thinking engine. Paper only. First written for BTC and ETH (`think15-v1`); now version
`think15-v5` on eight markets. The sections after "Now" describe the original design, which still holds.

## Now (11 Nov 2026; updated 16 Nov 2026 at think15-v5.2.2; the live version is `CFG["version"]`, v5.2.6 on 20 Nov 2026,
and every later change is in `VERSION_NOTE` in engine15/config.py)

- **Markets:** crypto (BTC, ETH), metals (gold, silver), USDJPY, S&P 500 (cash hours), oil (WTI, Brent).
  Each group is thought about separately (its own voices, trust and odds); each market has its own
  $10,000 book. Fees a side: crypto 0.10%, gold 0.02%, silver 0.03%, USDJPY 0.01%, S&P 0.02%, oil 0.04%.
- **Sizing:** crypto 1x; the others sized so a stop-out costs ~2% of equity, between 1x and the cap
  (USDJPY 100x, the others 5x). A total-risk cap: all open stops together at most 10% of total equity.
- **Exits (think15-v5.2.5, 19 Nov 2026):** every main book still leaves a trade only at its stop or on a flip.
  One market differs: on USDJPY the stop moves to the entry price once Target 1 has traded, live from the next
  bar (`CFG["be_t1"]`, `backtest.run_book`; a stop-out there is `STOP_BE`). The owner's call ("Follow the
  target", then "Stop to entry after T1"), not a passed test: on 2020-2026 history it was the only one of 15
  exit variants ahead of holding on USDJPY (+$27,238 against +$19,209, H36), and behind holding on the eight
  markets pooled. No profit is taken at the targets; the other seven markets are unchanged.
- **Exits (think15-v5.2.6, 20 Nov 2026):** the S&P 500's main book closes half the position at Target 1, moves
  the stop of the rest to the entry, and lets the rest run to that stop or a flip (`CFG["half_t1"]`; the half
  is a closed trade at once, `T1`, the rest a second row). The owner's call ("close half ... as TP1 already achieve", then "Rest runs, stop at entry").
  Not in H36's grid; its history read is H59, descriptive. Six markets still hold to the stop or a flip.
- **Exits (think15-v5.2.7, 20 Nov 2026):** USDJPY's main book sells half at Target 1 and the rest at Target 2
  (`CFG["t2_exit"]`; the owner: "Sell at target").
- **The opening Lead in the vault's book (think15-v5.2.10, 24 Nov 2026):** each BTC and ETH setup sent to the VIP
  vault carries `lead_pts`, the Lead of the step that opened it. The owner's order (23 Nov, in the AI Trading session):
  VIP accounts take a setup only when that Lead is above 5.0 points in its direction; the vault applies the cut. The
  engine's own decisions and every book are unchanged: the forced entries still open and are still judged on paper.
  Not a tested rule: on history (H65) setups opened on a real call and forced ones are both about flat per trade.
- **The Setups book's entry (think15-v5.2.9, 22 Nov 2026):** on BTC and ETH the Setups book books a new entry from flat
  at the close that decides it, at that close's price, where it used to fill at the next bar's open one step later
  (owner: "Cut the 15-minute delay"). The same moment, closed bars only; the setup is on the page, in the signal and in
  the book the vault reads about 15 minutes sooner. H64 found the delay cost nothing on average, so this makes a
  member's fill match the book's and is not expected to change results. Flips and exits keep their timing; the main
  books and every other market are untouched. Beside it runs the paper desk (`engine15/paper_desk.py`): three forward
  paper wallets on the same trades at three sizes (2% rule, 100% per coin, 3x book).
- **Exits (think15-v5.2.8, 21 Nov 2026):** on BTC, ETH, gold, silver, WTI and Brent the main book trails its stop
  (`CFG["trail_stop"]`, `exits.trail_step`, the B trail shadow book's rule): once a bar has gone one entry-stop
  distance in favour, the stop is the tighter of the last confirmed 15m swing and 2 x ATR(15m) behind the close,
  live from the next bar, never looser; a stop-out there is `TRAIL`. After a `TRAIL` exit the forced entry is off
  (`CFG["trail_wait_signal"]`): the book stays flat until one side clears the entry bar; an exit at the entry stop
  or on a flip keeps the 4-session mandate. The owner's call ("Update minds 15 with tight trailing stop"; "Six
  markets"; "Wait for a signal"), not a passed test: every tight trail lost against holding on history (H36), and
  the wait-for-a-signal re-entry has never run. The shadow `main` copy keeps holding as the forward comparison.
- **A profit-floor shadow book (21 Nov 2026, no version change):** `f_floor_33_3r` (`engine15/floor_book.py`)
  takes every trade of the shadow `main` copy (the hold rule) at that copy's fill and adds one exit: once a
  15-minute close has shown 3 entry-stop distances of open profit, a stop rests at the entry plus a third of the
  best profit a close has shown, live from the next bar, never looser. After its own exit it is flat until the
  hold copy's next entry. H61's `floor_33pct_3r`, the one variant that passed on history, weakly; forward data
  points only (the owner: "Add shadow"). It started as a copy of the hold copy's book, running trades included.
- **RL health readings (21 Nov 2026, no version change):** the three RL paper books now show how much of their
  result came from the agents and how much from the 'do no harm' fallback, and an input-drift reading; the
  Telegram bot says when no agent trades a coin (docs/RL.md, "Health readings"). No decision changed.
- **Fills:** decision at a bar's close, fill at the next open; gold, silver and oil one bar later (their
  live bars arrive ~10 minutes late). Futures rolls are smoothed (data/rolls.csv).
- **v5 decision rules:** a higher-timeframe bias (1h, 4h and daily trend one way and price on that side of
  the 1h EMA50 and 4h EMA20/50): forced entries take the bias side; an entry against it needs 15 pts; a
  position against it without a 5-pt edge is flipped. No new position or flip in the hour before a
  high-impact US release (the release calendar now covers 2019 to today).
- **Trust cap (v5.2, 15 Nov 2026, owner's choice):** no voting card may hold more than 40% of the say; the excess is
  handed to the other voting cards in proportion to their scores (`model.cap_shares`).
- **Readings:** about 70 cards since v5.2.2 (crypto ~60; every market also gets Supertrend, StochRSI, Parabolic SAR,
  Money Flow, volume profile, Heikin-Ashi, Aroon/Vortex and CCI; crypto adds Deribit options flow, Korea premium,
  CME gap, BTC dominance, spot vs perp and cross-exchange funding). Before v5.1.2: about 49 cards (36 for crypto, 20-27 for the others; crypto-only cards are not shown for
  the other markets). Only the top rated cards vote; the rest are read, journaled and shown.
  v5.1.1 (13 Nov 2026) added four crypto-only reading cards from `engine15/sources/flows.py`: Binance archive
  positioning, Bitfinex margin, CME positioning (CFTC) and on-chain activity (CoinMetrics). They do not vote; H39
  found no direction edge in them, only some volatility information.
- **Exits:** stop or flip. Profit targets (Fibonacci extensions or a typical day's travel) are planned and
  shown, not yet traded at (taking profit lost money in every history test so far). H36 (13 Nov 2026) tried 15
  moving-average trails and break-even-after-Target-1 variants on the main book's own entries, 2020-2026, eight
  markets: every one made less than holding (main +$329k pooled; break-even after Target 1 +$108k, the best MA trail
  -$25k). The main book earns from a few long holds (wins ~1 in 5, winners 4-6x losers); trails cut them. Three run
  forward as shadow books (b_be_t1, b_ema20_1h_t1, b_sma20_1h_t1); `research/out/exits/trail_study.md`. The owner
  chose "Let the winner run" (13 Nov 2026): no v5.2, profit is taken only by flipping.
- **Learning loops:** daily surprise mining and an idea queue; the owner's weekly review question; a
  question library that asks the owner about levels, stops, trend conflicts, squeezes and more; web
  answers (PIN-checked on the server) pulled before each step and graded like a card.
- **Beside the main books:** shadow challengers (v4, H3, A pullback entry, B exits, H5, the 4h and daily
  yardsticks, the 1h/4h swing minds), twelve strategy books (H6-H17) and the CPI book (H1). One
  forward scoreboard judges them all once each has 30 live trades.
- **RL forward paper books (12-13 Nov 2026, all NOT passed):** `p5_rlq` (Phase 4's RL agent) and, from 2026-11-13 03:00 UTC,
  `p6_mtrend` (Phase 6's agent: missed-opportunity reward, and the daily momentum position instead of flat when a
  model failed its own validation; 1 of 8 variants tried) with its control `p6_p4trend` (Phase 4's agent with the same
  momentum fallback). The momentum fallback was chosen with hindsight; the pair shows whether the new reward adds
  anything beyond it. They do not touch the main books' decisions.
- **BTC/ETH pair book (13 Nov 2026, NOT passed):** `p7_rvbear` (`engine15/playbook7.py`, H37 V4), forward from
  2026-11-13 11:30 UTC. Outside a daily downtrend each sleeve holds its own coin 1x spot; in a downtrend (daily close
  below a falling 200-day average) it holds the stronger coin 0.75x spot and shorts the weaker 0.75x perp.
- **Lean live step (11 Nov 2026, opt-in with `ENGINE15_LEAN=1`):** the live step no longer holds all history
  in memory. Every session's readings and feature matrix are kept on disk (`engine15/evcache.py`,
  `data/evcache/`, memory-mapped). Each step computes only the new sessions plus a 30-day refresh for late
  data, and checks every row the learning reads once a day. The weekly refits are cached and reused only when
  the training rows, grades and warm start are identical (`engine15/leanprep.py`). Readings are still
  computed over all history internally, because the weekly trend's seeded EMAs and the level list depend on
  the first bar of 2019 (a 1.7-year warm-up changed `tr_1w` by up to 0.56). Decisions and numbers are
  unchanged: proven bit for bit against the old code on frozen inputs for every group, in a fresh step and
  a 16-bar catch-up. Because nothing changed, there is no version bump. Peak memory per step: crypto
  about 1.3 GB (was about 5-6 GB), metals 1.1 GB (was 5.0). The replay (`backtest`) is unchanged.
- **What history says so far (in-sample, not proof):** 15m direction read alone is right ~51%; crypto's
  next hour ~55% (the one steady short-horizon skill, too small to pay crypto fees); over the last 120
  days the 15m main rule (+7.6%) beat the same engine on 4h (+6.1%) and daily (+1.5%) decisions.

## Why it exists

The AI Trading Bot's main engine trades 4-hour and daily bars. A hypothesis there takes
months to grade. This engine works on 15-minute bars so it makes and grades thousands of
calls a month: the purpose is to learn fast and to keep a full record of what it read,
what it decided and what happened, so that post-mortems can turn into new strategies.

It borrows from the AI Trading Bot (read-only; nothing in that project is changed):

| Borrowed | From | Used here as |
|---|---|---|
| Trend strength per timeframe (EMA and SMA 5 to 200: position, stack, slope) | `src/strategy/trend_map.py` | card 1 |
| Six market regimes | `scripts/regime.py` | card 2 |
| Working strategies: StochRSI core zone, Donchian trend, Burst momentum, 30-day momentum, BTC 120-day trend, weekly regime | `research/local/library/strategy_library.json` | card 9 |
| Kronos candle forecasts | the forecast job in `C:\tmp\kronos\forecast` | card 8 |
| Crypto headlines and the weekly economic calendar feed | the same job; `src/strategy/econ_calendar.py` | card 10 |
| Honest-frame rules: closed bars only, next-open fills, 0.10% a side | the estate's constitution | the paper book |

## The loop, every 15 minutes

1. **Read.** At each closed 15-minute bar the engine reads its sources (the ten cards
   below, plus risk and the other coin). Higher-timeframe bars count only once closed.
2. **Each voice gives odds.** Every card is one or more *voices*. A voice sees only its
   own readings and answers one question: over the next 24 hours, will price first move
   one unit up, first one unit down, or neither? A unit is 1.5 times the 1-hour ATR.
3. **Weigh by trust.** The engine mixes the voices' odds, weighted by how well each has
   called recently (see Learning). The mix is the engine's own odds.
4. **Decide under the mandate.** The edge is P(up first) minus P(down first).
   - Flat: enter the better side if its edge is at least 5 points (10 when risk is high).
     Otherwise sit out, for at most 4 sessions (1 hour) in a row; then the mandate forces
     the better side.
   - In a position: flip only when the other side leads by 10 points (a flip costs two
     fills). Otherwise hold. (Until v3 the engine also stepped aside when risk was high and
     its edge was gone; the owner switched that off on 10 Nov 2026 because it caused about
     770 exits and 1,000 forced re-entries a coin in the replay.)
   - A protective stop sits 3 times the 1-hour ATR from the fill.
   - Risk is "high" when the last hour's 15-minute range is at least twice its 24-hour norm.
5. **Journal.** One entry per coin per session: the readings, the odds, each voice's pull,
   the decision and its reason, the book, and which earlier calls were graded this session.
6. **Grade and learn.** A call is graded when price touches a barrier or 24 hours pass.

## The paper book

Each asset has its own $10,000 paper account and always trades at full size (1x, no
leverage). Owner's decision, 10 Nov 2026, taken over a proposed smaller, conviction-scaled
sizing. Fees are charged at 0.10% a side, so one round trip at full size costs about $20.

## The ten decision cards

| # | Card | Readings | History |
|---|---|---|---|
| 1 | Timeframe strength | trend score on 15m, 1h, 4h, 1d, 1w | 2019 on |
| 2 | Regime | TREND_UP/DOWN, MOMENTUM_UP/DOWN, RANGE, TRANSITION | 2019 on |
| 3 | Support and resistance | nearest levels, strength, room, breaks, rejections (`docs/SUPPORT_RESISTANCE.md`) | 2019 on |
| 4 | Momentum and stretch | moves over 1h to 7d against volatility; StochRSI 15m/1h/4h; stretch from the 1h and 4h averages; pullback inside the trend | 2019 on |
| 5 | Order flow (CVD) | net taker buying over 1h, 4h, 24h; flow without price progress | 2019 on |
| 6 | Funding and positioning | funding rate, against its month, 3-day sum; open-interest change | funding 2019 on; open interest live |
| 7 | Liquidity (order book) | resting size within 0.5% and 2%; nearest big wall; depth profile archived for a heatmap | live only |
| 8 | Kronos forecast | where the median path and the ten sample paths end, 15m and 1h | since 5 Nov 2026 |
| 9 | Working strategies | where each library strategy stands | 2019 on |
| 10 | News and economic events | headline tone and volume; time to and since US releases; S&P 500, dollar, VIX, 10-year yield | news live; calendar May 2026 on; macro 2018 on |

Behind the cards: **risk** (volatility level, shock) and **the other coin**.

**Cards 11 to 20** (added 10 Nov 2026; `docs/SOURCES_derivs.md`, `docs/SOURCES_market.md`):
perp basis and premium, long/short positioning, liquidation pressure (a proxy), options
implied volatility and skew, time and session, spot ETF flows, stablecoin supply, Coinbase
premium, market breadth and ETH/BTC, Fear and Greed. A further source is **the owner**: the
engine asks one question a session and a PIN-protected answer becomes a graded reading
(`engine15/owner.py`).

**Which cards vote (v3).** Every card is read, journaled and shown, but only the ten
best-rated ones vote on direction (`research/card_rating.json`): Regime, Momentum and
stretch, Support and resistance, Coinbase premium, Order flow, Market breadth, Timeframe
strength, Working strategies, Stablecoin supply, Perp basis. The owner's view always votes.
With all 20 voting, the replay's accuracy on claimed-edge calls fell from 51.7% to 50.0%.

**Shadow books.** Registered hypotheses trade on paper beside the main books
(`engine15/shadow.py`, `research/HYPOTHESES.md`). H1: CPI follow-through.

A live-only source has no past to learn from. It starts as "no read", says nothing, and
earns a say only as its own graded calls accumulate.

## Learning

Two loops, both fed only by calls whose grade is already known:

- **Daily refit.** Each voice is refitted every day on the last 180 days of graded calls.
- **Trust.** Every graded call costs each voice its error. Trust follows recent error with
  a 10-day half-life and never drops below 2% a voice.

The journal and `python -m engine15 postmortem` are the third loop, the owner's: what did
each reading say, and what happened next?

## Market structure and named setups (the foundation)

Owner, 10 Nov 2026: the foundation is "accuracy in reading market structure" leading to
"high probability trade setup and directional call". `engine15/sources/structure.py` does
two things at every 15-minute close:

- **Reads structure** on 15m, 1h, 4h and 1d from confirmed swing highs and lows (a swing is
  known only some bars after it forms): uptrend (higher high and higher low), downtrend, or
  range, with the last swing high and low as the prices that matter.
- **Names the setup**, if one is present, from a library of six exact rules: trend pullback,
  breakout, breakout retest, failed breakout, range fade, trend failure.

A setup's "probability" is its graded record (`research/setup_stats.py`): how often, in
history, price then travelled one unit its way before one unit against. First grading,
2020 to Nov 2026, both coins: no setup is high-probability as first written. The best are
failed breakout on BTC (53.1% long, 52.2% short, steady in both halves, about 2,270 cases
each) and breakout long on ETH (52.4%). Trend pullback, the textbook favourite, is 48 to 50%.
These two cards are read and journaled; they do not vote until a setup earns it.

Improving a setup follows the same rule as everything else: write the new version in
`research/HYPOTHESES.md` first, grade it in both halves, then forward.

## Scoring every trade (the improvement loop)

The experiment tests more than the long/short call: it also tests how the trade is set up,
entered and exited. `engine15/scorecard.py` grades every closed trade on five parts, each
0 to 100: **direction** (was the side right), **entry** (where the fill sat in the next two
hours' range), **speed** (how soon it was half a unit in profit), **exit** (how much of its
best open profit was kept) and **risk** (how much heat it took). The trade score weighs them
35 / 25 / 10 / 20 / 10.

Baseline, history replay with the v2 rule (2,556 trades): score 43; direction 51, entry 51,
speed 54, exit 16, risk 33. Read plainly: fills are no better than the middle of the range
that follows, and the exit keeps about a sixth of the best open profit, so the exit is the
weakest part.

The loop, weekly: (1) score every closed trade; (2) name the weakest part; (3) write one
challenger for that part in `research/HYPOTHESES.md` (for example a pullback entry, or a
trailing exit) and run it as a shadow on the same calls; (4) promote the challenger only if
it beats the incumbent on that part without lowering the total score over at least 50 trades.

## What the replay is, and is not

`python -m engine15 backtest` walks this loop through all history. It exists to warm the
voices up and to produce post-mortem material. It is not a claim that the engine makes
money. Known limits, stated plainly:

- The AI Trading Bot's own screens found no stand-alone 15-minute edge after costs on
  BTC and ETH (H1, 14 Aug 2026), and Kronos has failed every test run on it there.
- A must-be-positioned mandate pays fees whether or not there is an edge.
- The replay has no order-book, Kronos or news readings; funding paid or received on a
  held position is not charged; fills are at the next bar's open with no slippage model.
- Constants in `engine15/config.py` were declared once and not tuned.

## Commands

```
py -3 -m engine15 update            fetch new bars, funding, macro, calendar
py -3 -m engine15 backtest          replay all history (out/replay/)
py -3 -m engine15 step              one live step: read, think, decide, journal, page.json
py -3 -m engine15 live              step after every 15-minute close until stopped
py -3 -m engine15 ask now           what it thinks right now (also: why ETH, cards BTC, today, learning)
py -3 -m engine15 postmortem        what each reading said and what followed
py -3 -m pytest tests -q            the tests
```
