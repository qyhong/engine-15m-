# USDJPY post-mortem: a trade that reached both targets and closed at its entry (20 Nov 2026)

Asked for by the owner on 20 Nov 2026: "do a thorough post mortem so in future usdjpy trade can manage well.
Currently the engine guide the trade to profitability but you never follow through well. The engineering substrate
issue."

Everything here is read from the engine's own records: the journal (710 USDJPY decisions, 10 to 20 Nov), the trade
files, the shadow books' state, and the two history studies of exit rules (H36, H59). The history studies are
in-sample replays: they describe, they prove nothing. Ten days of live trading is one move up and one move down; it
cannot rank exit rules either. Paper only.

## 1. What happened

| When (UTC) | Event | Price | Open profit |
|---|---|---|---|
| 10 Nov 17:00 | Long opened, 378.19 units (6x). Entry by mandate, not by a lean: flat 4 sessions, the odds led by 0.3 points against a 5-point bar, so the side came from the 4h and daily trend. Stop 158.235. Target 1 159.395 (+$238). Target 2 159.822 (+$400). | 158.764 | |
| 11 Nov 13:30 | **Target 1 traded.** Nothing happened: the main book does not sell at targets. | 159.395 | +$232 |
| 11 Nov 15:30 | **Target 2 traded.** Nothing happened. | 159.822 | about +$400 |
| 13 Nov 06:15 | The high of the trade. | 160.188 | **+$512** (peak) |
| 13 Nov | Owner: "follow their own planned target profit", "trail profit with ema or sma". Answered with a history study (H36). It said every exit rule earned less than holding, the owner then chose "Let the winner run", and the main book was left as it was. Three shadow books were started. | | |
| 16 to 19 Nov | The trade sat between +$240 and +$455 at each day's end. | 159.4 to 159.9 | |
| 19 Nov evening | Owner: "usdjpy cannot breach above 160. Not feeling good", then "Follow the target". Two readings were offered: move the stop to the entry, or take profit at the targets. Claude recommended the first and the owner took the recommendation (think15-v5.2.5, live between 21:00 and 22:00). | 159.67 | **+$342** |
| 20 Nov 09:45 | Price fell one yen in ten hours. Stopped at the entry. | 158.764 | **-$12** (fees) |
| 20 Nov 11:00 | Forced back in after 4 flat sessions: a new long, 326.18 units. | 158.868 | |

The engine held for almost 700 decisions in a row. Its odds never told it to do anything else: see section 3.

## 2. The same trade under each exit rule

One trade, the real bars, the trade's own targets. Descriptive only.

| Exit rule | Result on this trade |
|---|---|
| As the engine ran it (hold; stop to entry from 19 Nov) | -$12 |
| Hold with the first stop, no change at all | still open on 20 Nov at about +$10, having been +$512 |
| Stop to entry and half at Target 1 (the S&P 500's rule) | +$107 |
| **Half at Target 1, half at Target 2 (the Setups book's rule; the record as the owner set it on 20 Nov)** | **+$307** |
| All out at Target 1 | about +$226 |
| All out at Target 2 | about +$388 |
| "Take profit at the targets" chosen on 19 Nov, when both had long traded: out at once near 159.67 | about +$330 |

The last row is the one that matters for the process: on 19 Nov the owner asked to follow the target, the trade was
+$342, and the option Claude recommended banked nothing. That recommendation was wrong for what the owner wanted, and
it cost the paper book about $340.

## 3. Why the engine could not manage this trade

**3a. The main book has no way to take profit.** It leaves a trade in two ways only: its stop, or a flip when the
odds lean 10 points the other way. The targets are computed at entry and shown on the page with dollar amounts, and the
code says of them: "PLANNED levels shown on the page ... the paper book does not yet take profit at them"
(`live.plan_targets`). What the owner sees as the plan is not what the book does.

**3b. The odds never moved enough to act on.** Over all 710 USDJPY decisions from 10 to 20 Nov:

- the lean ranged from -5.0 to +3.6 points; its typical size was 1.0 point;
- it reached the 5 points an ordinary entry needs in 1 decision of 710, and never the 10 points a flip needs;
- "the odds lean against it" was true in 54% of the bars the long was held, including the bar Target 1 traded.

So on USDJPY the odds decided neither the entry (forced by the mandate, side from the higher-timeframe trend) nor any
exit. The profit came from the trend the trade was pointed along, 158.76 to 160.19, and nothing in the engine was
watching for the trend to end. This is also why "close when the odds lean against it" (the owner's idea of 19 Nov) is
close to "close at Target 1" on this market: the odds lean against a long about half the time.

**3c. Taking profit is undone by the forced re-entry.** After any exit the book must be back in within 4 sessions (one
hour). The shadow books that did take profit on USDJPY show what follows. All entries below were forced.

| Shadow book (USDJPY, from 11 Nov) | First trade | Re-entries after it | Net realized |
|---|---|---|---|
| `main` copy: hold | none closed; still in its long of 11 Nov | | -$33 open |
| `b_targets`: half at Target 1, rest at Target 2 | **+$304** (both targets, 11 Nov) | -$219, +$41, -$214 | -$89 |
| `b_trail`: trailing stop after 1R | **+$428** | +$129, -$224, +$267, -$228, -$220 | +$153 |
| `b_be_t1`: stop to entry after Target 1 (from 13 Nov) | | -$214, -$207 | -$422 |

The Setups book did exactly what the owner wants: it banked $304 on both targets within eight hours. It was then
forced long again at 159.83, 159.75 and 159.77, near the top, and gave back $392: it ended these ten days at -$89, the main book without the rule at -$12. **Banking the profit and then not handing it back
are two separate fixes, and the second one is the mandate.**

**3d. Nothing tells the owner.** The Telegram bot reports a main-book trade when it closes. No alert was found for a
main-book trade reaching Target 1 or Target 2, or for a trade giving back most of its open profit. The owner
saw the stall under 160 before the system said anything.

**3e. Two exit engines.** The Setups book's exits live in `shadows.run`; the main book's in `backtest.run_book`. The
half at Target 1 was built a second time for the S&P 500 on 20 Nov. Each exit decision so far has been a one-market
switch added to one of the two.

## 4. What the history studies say, and what they do not

USDJPY, 2020 to Nov 2026, the main book's own entries (H36 table; H59 re-run on today's readings in brackets):

| Rule | Net | Trades | Wins | Largest drawdown | First half / second half |
|---|---|---|---|---|---|
| Hold (`main`) | +$19,209 (+$7,288) | 120 | 18% | -58% | +$32,607 / -$13,398 |
| Stop to entry after Target 1 | +$27,238 (+$9,424) | 145 | 14% | -57% | +$40,322 / -$13,084 |
| Half at Target 1, rest at Target 2 (`b_targets`) | +$2,939 (-$394) | 744 | 43% | -50% | +$795 / +$2,144 |
| Trailing stop (`b_trail`) | -$5,585 | 1,537 | 50% | -75% | -$99 / -$5,486 |

- Holding looks best in total, but its whole result is six trades (they sum to 355% of the net) and it lost money in
  the more recent half. It wins about one trade in six and waits two weeks per trade.
- Taking targets wins 43% of the time and earns little, because it trades six times as often and every exit is
  followed by a forced re-entry: the same thing section 3c shows live.
- These numbers moved by thousands of dollars between two runs of the same study a week apart (the likely cause: the readings
  store was rebuilt). They are not a basis for refusing an instruction. On 13 Nov and on 19 Nov they were used as one.

## 5. Where the follow-through failed

1. **13 Nov.** The owner said to follow the planned targets. The answer was a study and three shadow books; the open
   trade, already past both targets, was not touched.
2. **19 Nov.** The owner said "Follow the target" about a trade +$342 in profit that they judged was stalling. Claude
   offered a protective option and a profit-taking option and recommended the protective one, citing the history
   table. The owner's read of the market was right and the recommendation gave the profit back.
3. **The owner's standing preference**, said of data sources on 10 Nov, is to build and record first and not to gate
   on a backtest. Exits were gated on a backtest twice.

## 6. Fixes

**A. Rule, USDJPY main book: sell half at Target 1, the rest at Target 2, stop to the entry after Target 1.** The rule
the Setups book already runs and the page already shows. It applies to the open long of 20 Nov (Target 1 159.586,
Target 2 160.093). A new engine version; the hold copy and the other exit shadows keep running as the comparison.

**B. Rule, USDJPY main book: no forced re-entry after a trade that ended at a target.** After such an exit the book
waits for a real lean (the ordinary 5-point entry) before it trades again; the 4-session mandate applies again after
that trade. This is the fix section 3c points at, and it changes the owner's own mandate for one market, so it is the
owner's decision. On the last ten days it would have left the book flat with the $307 from 11 Nov on, except for the one decision
where the lean reached 5 points.

**C. Alerts, all main books:** a Telegram card when a trade reaches Target 1, when it reaches Target 2, and when it
has given back more than half of its best open profit. No trading in it: so the owner is told before, not after.

**D. The page says what the book will do.** `page.json` gets a field per trade saying whether its targets are traded.
Where they are not (BTC, ETH, gold, silver, oil main books today), the page should say "planned, not traded". The
page itself is the AI Trading Bot session's.

**E. One exit engine.** The main book calls the same exit code as the Setups book, so "follow the targets" is one
switch per market and one set of tests. The golden test of 20 Nov already pins that code for the vault's book; the
change must leave it green.

**F. Process.** When the owner gives an instruction about an open trade, it is applied to that trade the same day,
banking what the trade has already reached. The alternative runs as a shadow book. A history table is reported with
the change; it does not replace it.

## 7. What stays unknown

Whether A and B earn more than holding on USDJPY over many trades. The forward comparison answers it: the main book
under the new rules against the `main` copy that holds, read at 30 closed trades each, as already agreed for the other
exit shadows.
