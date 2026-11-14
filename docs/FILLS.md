# Cheaper fills (charter item E)

Study of 11 Nov 2026. Code: `research/fills.py`. Tests: `tests/test_fills.py`.
Output: `out/fills/fills_grid.csv` (every policy, both coins, three fee schedules) and
`out/fills/summary.json`.

```
py -3 research/fills.py                 about 10 s, under 150 MB
py -3 -m pytest tests/test_fills.py -q
```

## The question

The paper book buys and sells at the next 15-minute bar's open with market orders and pays
0.10% a side, about $20 for a round trip at $10,000. Would limit (maker) orders make the
**same trades** pay more, once fees saved, better prices and missed trades are all counted?

## Short answer

1. **The fee schedule matters more than the order type.** Paying spot fees in BNB (0.075%)
   adds about $1,400 (BTC) and $1,200 (ETH) over the 6.9 years at $10,000 a trade. It
   changes nothing in how the engine trades. Perp taker fees (0.05%) halve the fees, but
   this book paid more in funding ($3,000 BTC, $4,900 ETH) than it saved in fees.
2. **A limit at the open price saves nothing on spot**, because spot maker and taker fees
   are the same. It only adds the cost of chasing when price runs away. On perps it saves the
   maker discount, about $2 to $3 a round trip.
3. **Dropping a trade when the limit is not filled ("skip") is a lottery, not a saving.**
   The book wins only 18% (BTC) to 24% (ETH) of its trades and lives on a few big winners.
   Missing one of them costs more than the fees saved on dozens of trades. The same rule
   added $10,000 on BTC and lost $14,500 on ETH.
4. **Limits placed a little better than the open, followed by a market order if not filled
   ("chase"), helped a little.** The trades are the same; only the prices change. For
   entries all of the help came in the first half of history, so that is not reliable. For
   flip exits it held in both halves on both coins, but the amounts are small: about $8 to
   $13 a flip. This is the one rule worth registering. It is a hypothesis, not an edge.

## Method

**Trades.** The replay's closed trades, `out/replay/trades_BTCUSDT.csv` (280) and
`trades_ETHUSDT.csv` (235), 2020-02 to 2026-11. Each row has `time_in`/`time_out` (written
by `backtest.save_run` from the replay's common index), so each trade is found on the coin's
own 15m bars by its timestamp. Checks, all passed: `p_in` equals that bar's open for every
trade, and re-filling every trade at market at 0.10% reproduces the replay's `pnl_pct` to
1e-14. Live closed trades: none yet (one open position per coin in `data/live_state.json`).

**What stays fixed.** Side, decision bar, exit reason and stop level are the engine's. The
stop is rebuilt from the bars (fill − side × 2 × 1.5 × ATR(14) of 1h at the decision bar) and
matches all 367 stop exits that filled at their level. The stop stays at that price whatever
the new entry is, so each trade lives as long as it did in the replay.

**Fill policies.** An order goes in at the open of the bar where the replay filled (the
decision was made at the close before).

| Policy | Rule |
|---|---|
| market | fill at that open, taker fee |
| limit k, N | buy at open − k × ATR15 (sell at open + k × ATR15). ATR15 is Wilder ATR(14) of 15m bars at the decision bar, so it is known when the order goes in. k = 0, 0.1, 0.25, 0.5 |
| fill test | a bar in the window must trade **strictly through** the limit (low < limit to buy, high > limit to sell). Touching is not enough: this stands in for not being first in the queue. The fill is at the limit price, never better |
| window | the order bar plus the next N − 1 bars, N = 1, 2, 4 (15 min to 1 h) |
| skip | not filled → the trade is not taken |
| chase | not filled → market at the next open, taker fee |
| exits | stop exits stay market at the replay's price. Flip exits can rest a limit; an exit cannot be skipped, so an unfilled exit always chases. While it waits the stop is still live, and if one bar reaches both the stop and the limit, the stop is assumed to come first |
| cancel | an entry still waiting when the engine decides its exit is cancelled, and the trade is missed |

**Fees, Binance regular tier, a side.** Spot: 0.10% taker and maker, the replay's figure.
Spot with BNB: 0.075% taker and maker. Perp (USD-M): 0.05% taker, 0.02% maker, with the real
funding charged or received for each 8h settlement the position is held through
(`data/*_funding.csv`). The engine shorts, so "spot" really means a margin account.

**Money.** Dollar P&L and fees assume a fixed $10,000 on every trade. Return % and max
drawdown come from the compounding $10,000 book at full size, as in the replay. Drawdown is
measured on closed-trade equity, so it is smaller than the replay's mark-to-market drawdown.
Halves: before and after 6 Jun 2023, the middle of the span. No look-ahead: limit prices use
the order bar's open and the previous bar's ATR. Fills use only bars from the order bar
onward. A test checks that changing later bars changes nothing.

## Results

### 1. Fee schedule only (market in and out)

| Fees | BTC $ P&L | BTC fees | BTC return / maxDD | ETH $ P&L | ETH fees | ETH return / maxDD |
|---|---|---|---|---|---|---|
| spot 0.10% (incumbent) | 8,369 | 5,634 | −28% / −70% | 42,707 | 4,745 | +1,001% / −63% |
| spot+BNB 0.075% | 9,778 | 4,226 | −17% / −69% | 43,893 | 3,559 | +1,139% / −63% |
| perp 0.05%, no funding | 11,186 | 2,817 | −4% / −69% | 45,079 | 2,373 | +1,294% / −63% |
| perp 0.05% + funding | 8,217 | 2,817 (+2,969 funding) | −25% / −72% | 40,168 | 2,373 (+4,911 funding) | +850% / −65% |

### 2. Entry limits with chase: same trades, price effect only (spot fees, exits market)

Change in $ P&L against the incumbent, whole span (first half / second half):

| Entry | BTC | ETH |
|---|---|---|
| limit at open, N1 | −225 (−137 / −87) | −405 (−235 / −170) |
| k0.10, N4 | +616 (+559 / +57) | +153 (+469 / −316) |
| k0.25, N4 | +563 (+522 / +41) | +1,613 (+1,709 / −97) |
| k0.50, N4 | +431 (+871 / −440) | +1,607 (+1,835 / −228) |

Of the 12 chase entries, ETH did worse than market in the second half for **every** one.
BTC's second half ranged from −440 to +57. The gain is a first-half effect. On perps the
maker fee adds about $2.5 to $3 a round trip on top: limit at open N1 on perp is +$590 BTC and
+$283 ETH against perp market.

### 3. Entry limits with skip: adverse selection (spot fees)

| Entry | BTC missed (won / lost) | BTC Δ$ | ETH missed (won / lost) | ETH Δ$ |
|---|---|---|---|---|
| limit at open, N4 | 2 (0 / 2) | +480 | 3 (1 / 2) | +563 |
| k0.10, N1 | 44 (5 / 39) | +10,199 | 37 (12 / 25) | −14,514 |
| k0.10, N4 | 16 (2 / 14) | +5,016 | 17 (3 / 14) | +4,357 |
| k0.25, N2 | 65 (13 / 52) | +6,748 | 49 (16 / 33) | −14,693 |
| k0.50, N2 | 118 (26 / 92) | +1,582 | 97 (31 / 66) | −33,090 |

"Won / lost" says whether the market version of the missed trade made money. Across all 12
skip rules and both coins, 24% of missed trades were winners, against 21% for the book
overall: mild adverse selection by count. In money it is lopsided: at k0.5 a limit filled 45% of ETH's winners against 63% of its losers, the classic
adverse-selection pattern, and one missed ETH trend trade can be worth $10,000. The sign
flips between coins and between neighbouring settings. The grid's top 15 rows are all skip
rules (best: +$14,400 both coins), which is what picking the luckiest of 975 combinations
looks like. None of them is a finding.

### 4. Flip-exit limits with chase (spot fees, entries market)

Only flips can use a limit: 72 BTC and 76 ETH exits. Change in $ P&L (first half / second half):

| Exit | BTC | ETH |
|---|---|---|
| limit at open, N2 | 0 (0 / 0) | −130 (−126 / −4) |
| k0.10, N4 | +440 (+342 / +99) | +212 (+128 / +84) |
| **k0.25, N4** | **+615 (+528 / +87)** | **+1,011 (+799 / +212)** |
| k0.50, N4 | +1,124 (+1,069 / +54) | +1,434 (+1,215 / +219) |

All three improved N4 rules are positive in both halves on both coins. Within the hour,
93% (BTC) and 87% (ETH) of flips filled as maker. By year (k0.25 N4 against the incumbent, $), the rule
was better in 10 of 14 coin-years, worse in 3 and level in 1:

| Year | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| BTC | +9 | +403 | +74 | +3 | +165 | +57 | −94 |
| ETH | +380 | +485 | −37 | −26 | +77 | +133 | 0 |

### Combined, for scale

Entry k0.25 N4 chase plus exit k0.25 N4 chase: spot +$1,179 BTC and +$2,625 ETH against the
incumbent. On perps with the maker fee, +$2,084 BTC and +$3,446 ETH against perp market. That
is roughly $4 to $15 a round trip, against $20 of fees. It does not turn BTC's book positive
(−19% compounding return on spot).

## Hypothesis to register (not registered here; `research/HYPOTHESES.md` belongs to the engine owner)

**H-E1, patient flip exits.** When the engine flips or exits on a decision (not a stop),
close the old position with a limit at the decision bar's next open + 0.25 × ATR(14, 15m) in
the position's favour: sell above for a long, buy below for a short. ATR is taken at the
decision bar. The order rests for 4 bars (1 hour), with the protective stop still live. If it
is not filled, close at market at the next open. Entries and stop exits are unchanged (market).
The new side of a flip is still entered at market.
Replay (chosen after looking at a grid, so in-sample): +$615 BTC and +$1,011 ETH over 6.9
years at $10,000 a trade on spot fees, positive in both halves. **Forward test:** a shadow
book on the live calls, graded on $ per flip against the market exit over at least 50 flips.
Kill it if the mean saving is not above zero.

A second idea is to change the fee schedule (BNB on spot, or perp with maker entries). That
is an operational choice for a real account, not an engine hypothesis. The perp funding this
book paid must be counted against it.

Rejected: skipping trades whose limit does not fill (a lottery that depends on a handful of
big winners). Also rejected: limits at the plain open on spot (no fee to save, chase cost only).

## Limits, stated plainly

- **No order-book replay.** Fills come from 15m high and low only. "Strictly through" is a
  rough stand-in for queue position. A real maker order at the touch can still be skipped
  when price only ticks through it, which would make every limit result here too kind.
  Fill at the limit price ignores gap improvement, which is too harsh.
- **No partial fills.** At $10,000 on BTC and ETH this hardly matters. At size it would.
- **Same trades, same stops.** The engine's later decisions would differ if its position
  differed (a later entry, a missed trade). Only a full re-run of `run_book` with the odds
  can show that, and that needs `out/replay/store.pkl` (1.9 GB, not loaded here).
- **Small samples.** 515 trades and 148 flips in all. The exit gain is about $600 to $1,000
  per coin in 6.9 years, well inside what luck can do. Choosing k and N after seeing the grid
  is a selection effect, so the forward test decides.
- **Overlapping legs.** When an exit limit waits and the new side was taken at market, the
  book is briefly long and short at once (net flat). The model counts the legs separately.
- Intrabar order is unknown. When a fill and a stop fall in the same bar, the worse outcome is
  assumed.
