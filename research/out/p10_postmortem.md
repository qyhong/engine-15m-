# P10 round numbers: post-mortem of the first 120 live trades (19 Nov 2026)

Owner, 19 Nov 2026: "Post-mortem, then retire" for `p10_round` (H15), whose scoreboard verdict was "behind: even the high
end of the range is negative".

Source: a read-only replay of `engine15/playbook3.py` (the book holds no state; the same bars give the same rows) on
the server's own 15m bars (`/data/mind15/data`, copied read-only), 11 Nov 2026 to the 19 Nov 03:30 UTC bar, six
markets. The replay matches the server's `out/live/playbook.json` exactly: 120 closed trades, -$2,018.29, fees
$1,188.19 (the server's module files are byte-identical to this repo's). One more ETH trade was WAITING for the
03:45 open; whatever fills before the retirement stamp stays in the record.

## 1. The rule, and is the code doing it?

The registered rule (H15, `RULES["p10_round"]` = magnet, base grid, within 1 hourly ATR, full stop):

- Round numbers: BTC 1,000s, ETH 100s, gold 50s, silver 1s, USDJPY 0.50s, S&P 500 50s.
- When a 15m close first comes within 1 hourly ATR of the nearest round number (the previous close was farther away,
  and price has not touched it in the last 4 hours), trade toward it at the next open.
- Target = the number. Stop = the same distance behind the entry (a 1R / 1R bracket; at least 4 one-side fees away).
  Exit after 16 bars (4 hours). $10,000 a trade, each market's own fee.

The code does this. Every one of the 61 stopped trades lost exactly 1.00R before costs, and every one of the 45 trades
that reached the number made exactly 1.00R before costs: no gaps through stops, no fill or level errors. The losses
come from the rule, not the plumbing.

**Pass bar (fixed 11 Nov):** after 200 trades or 30 days, keep it only if the average is above **+0.05R after costs**
and **at least 4 of 6 markets** are positive. Live: -0.355R after costs, 1 of 6 markets positive by average R (gold),
2 of 6 by dollars (gold, and S&P on 3 trades). The 200 trades / 30 days were not reached; retired early on the owner's word.

## 2. The numbers

| | |
|---|---|
| Closed trades (8 days) | 120 |
| Net / before costs / fees | -$2,018 / -$830 / $1,188 |
| Won (net > 0) | 41.7% (50) |
| Mean result before costs | -0.14R (90% range -0.28R to -0.00R) |
| Mean result after costs | -0.36R (90% range -0.50R to -0.21R) |
| Average win / average loss | +$34 (+0.72R) / -$53 (-1.12R) |
| Win rate needed to break even | 61% (50% even before costs) |
| Median cost per trade | 0.20R (BTC 0.32R) |
| Median stop distance | 0.46% of price (USDJPY 0.09%) |

**Costs' share:** fees were $1,188 of the $2,018 lost (59%). Without any fee it would still have lost $830.

### Per market

| Market | Trades | Won | Net $ | Avg R before / after costs | Cost R/trade |
|---|---|---|---|---|---|
| BTC | 26 | 42% | -729 | -0.12 / -0.46 | 0.34 |
| ETH | 18 | 50% | -372 | -0.00 / -0.22 | 0.22 |
| Gold | 21 | 62% | +66 | +0.24 / +0.11 | 0.13 |
| Silver | 27 | 30% | -873 | -0.40 / -0.53 | 0.13 |
| USDJPY | 25 | 28% | -114 | -0.33 / -0.58 | 0.25 |
| S&P 500 | 3 | 67% | +5 | +0.06 / -0.13 | 0.18 |

### Per side

| Side | Trades | Won | Net $ | Avg R before / after costs |
|---|---|---|---|---|
| Long (number above) | 39 | 31% | -713 | -0.32 / -0.51 |
| Short (number below) | 81 | 47% | -1,305 | -0.06 / -0.28 |

Shorts were twice as common (prices mostly fell over these days, so the nearest number was more often below) and lost
less per trade; longs lost more. Gold shorts were the only sizeable positive cell (15 trades, +$171). With 3 to 27 trades a
cell, none of these splits is a pattern.

### How trades ended (why_out)

| Exit | Trades | Net $ | Avg R after costs | Median bars held |
|---|---|---|---|---|
| STOP (stop hit first) | 61 | -3,402 | -1.21 | 2 |
| T2 (the round number reached) | 45 | +1,694 | +0.79 | 1 |
| TIME (16 bars, neither) | 14 | -310 | -0.30 | 16 |

Of the 106 trades that hit either side, the number came first only 45 times (42%). On a 1R / 1R bracket a coin flip
gives 50%; a real magnet would give more. 32 of the 61 stops hit within 2 bars.

### Time of day (UTC)

| Session | Trades | Won | Net $ | Avg R before / after |
|---|---|---|---|---|
| Asia 00-07 | 40 | 35% | -1,020 | -0.32 / -0.53 |
| London 07-13 | 24 | 46% | -187 | -0.03 / -0.23 |
| New York 13-20 | 38 | 39% | -525 | -0.14 / -0.35 |
| Late 20-24 | 18 | 56% | -286 | +0.10 / -0.15 |

Asia lost most live; on history Asia was no worse than the other sessions, so this is likely noise.

### Distance to the round number at the decision

| Distance (hourly ATRs) | Trades | Won | Net $ | Avg R before / after | Median stop % |
|---|---|---|---|---|---|
| 0 to 0.5 | 15 | 47% | -155 | -0.07 / -0.32 | 0.26% |
| 0.5 to 0.75 | 26 | 42% | -439 | -0.19 / -0.43 | 0.44% |
| 0.75 to 1.0 | 79 | 41% | -1,425 | -0.14 / -0.34 | 0.57% |

Most entries (79 of 120, median 0.80 ATR) came at the outer edge of the 1-ATR window, because the rule fires on the
first close inside it. The result per trade is about the same at every distance: no distance where the pull works.
In dollars the far trades lost most, because the stake is a fixed $10,000, so a wider stop risks more dollars.

### Holding time

Median 3 bars (45 minutes); 50 of 120 trades closed within the first bar. Winners median 2 bars, losers 3. The
16-bar limit was reached only 14 times, and those lost on average.

### Over the days

Roughly flat for the first five days (-$306 on 58 trades), then -$1,712 on 62 trades from 16 to 19 Nov. The pace was about
450 trades a month across the six markets, against about 260 a month on history.

## 3. History vs live

| | History, first half (2019-2022) | History, second half (2022-Nov 2026) | Live (11-19 Nov 2026) |
|---|---|---|---|
| Trades | ~9,200 | ~12,400 | 120 |
| Win rate (by market) | 44-51% | 44-47% | 42% |
| Avg R before costs (mean of markets) | -0.016 | -0.026 | -0.14 (all trades) |
| Avg R after costs (mean of markets) | -0.210 | -0.246 | -0.36 (all trades) |
| Markets positive after costs | 0 of 6 | 0 of 6 | 1 of 6 |

Source: `research/out/playbook3.md` (12 variants tried; this one lost least in the first half). H15's own note said
"no edge even before costs on history; runs mainly as the control it already is", and `docs/PLAYBOOK3.md` gave the
verdict "rejected" before it went live. Live did what history said, only worse: about zero before costs on history,
slightly negative live (eight days of mostly falling markets), and in both cases a fifth of 1R or more of costs on top.

## 4. Why it loses (as far as the data shows)

1. **There is no magnet.** Price reached the round number before an equally distant stop 42% of the time live, and
   history's trades won 44-51% (by market) over about 21,600 trades: a coin flip or worse. Before costs it lost -0.14R a trade live
   and about -0.02R on history. There is nothing for the costs to come out of.
2. **The bracket makes costs fatal.** With target and stop the same distance away, it needs 50% just to break even before
   costs; with a median 0.20R round trip (0.32R on BTC, where 1,000 is under 1% of price) it needs about 61%. Fees were 59%
   of the loss.
3. **It trades too often.** The trigger (first close within 1 hourly ATR of any grid number) fires about 15 times a
   day across six markets, so the cost drag piles up fast.
4. Silver and USDJPY were the worst live (28-30% won), and longs lost more than shorts; with 120 trades in one falling
   week these are not causes to fix, just where the losses landed.

No code bug was found. **No improved variant is proposed.** As with P1, any change (a different grid, a nearer trigger,
a wider target, a trend filter) would be a new hypothesis, registered before any test and only on the owner's word;
the history already shows that the 11 sibling variants (major grid, half stop, the rejection play) were no better.

## 5. Retirement

`engine15/playbook3.py` `RETIRED = {"p10_round": "2026-11-19 04:00"}` (the next quarter hour after the owner's word):
no trade entered from 19 Nov 2026 04:00 UTC counts, no new WAITING setups, and the live record before it stays on the
page, frozen, under the title "Round-number magnets (retired 19 Nov 2026)", as `playbook.RETIRED` does for P1.
