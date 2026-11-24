# Audit of Mind 15's live trades, 10 to 24 Nov 2026

Owner, 24 Nov 2026: "audit all assets and the past open and close trade so far for minds15. See anything we can
studies or do better". Data read from the live box at 11:55 UTC on 24 Nov (engine think15-v5.2.10). Nothing on the box
was changed. Tables: `trade_tables.txt` (every trade of the main, Setups and B trail books) and `checks.txt`.
The `.py` files here are the scripts as run from a scratch folder beside a copy of the box's files; they are kept for
the method, and their paths need changing before they run again.

This is a description of 14 days in one falling market. It is not a test of any rule.

## 1. Are the records right

207 trade rows (main books and 16 shadow books) were checked against the 15-minute bars.

- Every entry price lies inside its bar.
- Every result equals size x move less fees. Equity adds up from each trade to the next.
- No duplicate rows, no trade that opens before the last one closed, none that closes before it opens.
- 18 exit prices lie outside their exit bar. All 18 are two-part exits (Target 1 then Target 2, or Target 1 then the
  stop at entry) written as one row with the average of the two exit prices. Not an error.
- BTC and ETH: no 15-minute close without a journal line since 10 Nov 13:15 UTC.

## 2. Results on closed trades

| Book | Trades | Won | Net | Fees |
|---|---|---|---|---|
| Main books | 19 | 10 | +$7,327 | $262 |
| Setups book (`b_targets`) | 35 | 23 | +$5,204 | $452 |
| B trail | 60 | 47 | +$10,251 | $795 |

With open positions marked at 11:30 UTC the eight main books stand at $87,813 on $80,000 (+9.8%).

Net by market, with the number of trades:

| Market | Main | Setups | B trail | Price change over the span |
|---|---|---|---|---|
| BTC | +$1,419 (5) | +$1,530 (7) | +$2,468 (12) | -19.4% |
| ETH | +$1,634 (4) | +$597 (6) | +$2,154 (9) | -19.2% |
| Gold | +$1,557 (1) | +$1,150 (7) | +$1,708 (7) | -11.2% |
| Silver | +$1,678 (2) | +$1,801 (4) | +$1,827 (10) | -19.8% |
| USDJPY | +$307 (1) | -$196 (6) | +$268 (7) | +0.6% |
| S&P 500 | +$160 (2) | +$304 (2) | +$463 (2) | -3.7% |
| WTI | +$302 (2) | -$288 (1) | +$587 (6) | -5.5% |
| Brent | +$269 (2) | +$305 (2) | +$775 (7) | -3.2% |

## 3. Findings

1. **One bet.** Seven markets fell and the books were short on them. Shorts: 18 of 19 main trades, 29 of 35 Setups
   trades, 53 of 60 B trail trades. The main books were short on five or more markets at once 89% of the time.
   Trades opened after the 21 Nov low lost in all three books: main 2 of 6 won, -$1,455; Setups 0 of 3, -$1,555;
   B trail 2 of 6, -$1,549. On 23 Nov the Setups book took five stops in one day, -$2,086.
2. **The Lead never cleared 5 points outside crypto.** Largest reading in 14 days: gold 4.6, silver 4.7, USDJPY 5.0,
   S&P 3.5, WTI 4.2, Brent 4.5. So every trade on those six markets was a forced entry on the trend's side. The main
   books made 7 entries on a real call in 14 days, all on BTC and ETH.
3. **On crypto the Lead pointed down in 98% of steps**, including through the rebound from 55,130. ETH readings above
   10 points had price on their side 24 hours later 51% of the time.
4. **On oil the Lead pointed up** in 85% to 90% of steps while price fell. The oil books made their money short, by
   the forced entry, against their own reading. Readings of 2 to 5 points were on the right side 24 hours later 26%
   (WTI) and 38% (Brent) of the time.
5. **A loss is not 2% of the book.** A position is never smaller than 1x, so when the stop is further than 2% away the
   loss is larger. Setups book: 17 of 35 trades risked more than 2.5%. Losing crypto trades cost 5.6% of the book on
   average, the other markets 2.6%.
6. **Exits were early in a trend.** The Setups book kept 1.37% of an average best point of 3.97%. After a winning
   exit the price went a further 3.3% the same way within 24 hours, on average. The main books' seven trades held
   over three days made +$9,806; the other twelve lost $2,480 between them. The shadow books that trail after Target 1
   (`b_ema20_1h_t1`, `b_sma20_1h_t1`) average $223 and $219 a trade against $149, on 18 and 21 trades.
7. **After Target 1 the rest is protected only at entry.** WTI now: entry 88.93, price 80.12, stop 88.93.
8. **The quick re-entry after a stop has paid.** The next trade after a losing stop opened 1.2 hours later on the same
   side every time. Main: 7 of 9 won, +$5,615. Setups: 4 of 7, +$844. B trail: 8 of 11, +$1,256. The book that waits
   after a stop (`b_wait_stop`) is at -$1,318 on 6 trades.
9. **USDJPY is the weakest market.** Setups book: 6 trades, -$196. The stop sits 0.26% to 0.41% from entry. The Lead
   was on the right side 24 hours later in 34% to 38% of steps.
10. **The scoreboard's range is too narrow.** It treats trades as independent. BTC and ETH open and close in the same
    hours, as do gold and silver, and WTI and Brent. The two "ahead" verdicts rest on fewer separate bets than 35 and 60.
11. **Two strategy books are judged "behind"**: `p10_round` (121 trades, -$1,934) and `p1_liqhunt` (66 trades, -$1,368).

The check of the Lead against later prices uses every 15-minute reading, so neighbouring readings overlap heavily.

## 4. What could be studied or done

| # | What | Kind |
|---|---|---|
| A | Judge the scoreboard by day or by pair of markets, not by trade | report change, no trading rule |
| B | Count BTC+ETH, gold+silver and WTI+Brent as one bet each, or cap the total risk in one direction | study on history |
| C | An entry bar set per market, for the six where 5 points is never reached | study on history |
| D | Size below 1x so each stop costs 2% | study; the paper books' money path, owner's word |
| E | How fast the Lead turns after a capitulation low | study on history |
| F | USDJPY: a wider stop, or leave it out of the Setups book | study |
| G | Stop running the two books judged "behind" | owner's decision |

Exits (finding 6 and 7) need no new study: the exit learner (H109) and the two trail-after-Target-1 shadows are already
measuring them forward.
