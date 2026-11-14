# S&P 500 event cards: `putcall` and `earnings`

Module: `engine15/sources/equity_events.py`. Market: SPX only. Tests: `tests/test_equity_events.py`.

## Options mood (put/call): the `putcall` card

**What it is.** Each day, the number of put option contracts traded divided by the number of call
contracts. A high ratio means more puts (protection or bearish bets) than usual. A low ratio
means more calls.

**On the card**
- **Total put/call**: all options.
- **Index options put/call**: cash-settled index options (SPX, VIX, XSP, RUT, NDX ...). These are
  mostly institutional hedges, so this ratio usually sits above 1.
- **Equity options put/call**: everything that is not an index option.
- **SPX options put/call**: S&P 500 index options alone (OCC days only).
- **10-day average** of the total ratio.
- **Percentile of the last year**: where today's ratio sits among the last 252 days of the same
  source (0 = fewest puts, 100 = most). Needs at least 60 days.

**Two sources. They are never mixed inside one number.**

| Span | Source | Covers | "Equity" means |
|---|---|---|---|
| 1 Nov 2006 to 4 Oct 2019 | Cboe's historical CSVs (`cdn.cboe.com/resources/options/volume_and_call_put_ratios/`) | Cboe exchange volume only | single-stock options, ETFs excluded |
| about 2 years before the first run (10 Nov 2026), and on | OCC's public volume query (`marketdata.theocc.com/volume-query`) | every cleared option trade, all US exchanges | single stocks **and** ETFs (SPY, QQQ ...) |

Between October 2019 and November 2024 there is no free daily source, so there is no read.
Cboe's current daily statistics page sits behind a bot wall and is not used. Because the two
sources define "total" and "equity" differently, averages and percentiles are worked out only
over days of the same source. The OCC ratios run a little different from the Cboe ratios that are
often quoted (all exchanges, ETFs in "equity").

OCC reports each trade once per side (buyer and seller), so its sums are halved. The halved total
matches OCC's own published daily contract volume exactly (checked for 9 Nov 2026: 79.8 million),
and the index set matches OCC's "Index/Others" total to within 0.02%.

**When a day counts.** A day's figures are used from **12:00 New York time on the next NYSE
trading day**. OCC was seen serving Monday 9 Nov 2026 by 11:49 ET on Tuesday 10 Nov. Live, a day
the OCC still lacked after that time counts from the moment it was first fetched.

**Cost.** OCC's daily reply is about 5 MB. `update()` asks for the last finished trading day once
its session is over, then again each hour until it is out. It also fills in at most one older day
per call, so the 2-year history refills on its own over a few days if it is ever lost. Cboe's
frozen history is fetched once. File: `data/sources/putcall_daily.csv`.

Features (0.0 = no read): `pc_total`, `pc_total_10d`, `pc_index`, `pc_equity`, each a percentile
mapped to -1..+1 (+1 = the most puts in a year). Readable columns: `pc_total_ratio`,
`pc_index_ratio`, `pc_equity_ratio`, `pc_spx_ratio`, `pc_total_10d_avg`, `pc_total_pctile`,
`pc_equity_pctile`, `pc_source` (1 = Cboe, 2 = OCC), `pc_day_age_d`.

## Megacap earnings: the `earnings` card

**Watch list** (the ten largest S&P 500 weights in late 2026): NVDA, AAPL, MSFT, AMZN, GOOGL,
META, AVGO, TSLA, BRK.B, JPM. The same ten are used for all history. That is a survivor's list:
in 2018 some of the top ten were other companies.

**On the card**: which of the ten report this week and next week, with the day and whether it is
before the open or after the close. Also how many report in the next 5 trading days, and which
reported in the last 24 hours.

**Source.** Nasdaq's public earnings calendar, `api.nasdaq.com/api/calendar/earnings?date=YYYY-MM-DD`,
one request per day, with a normal browser User-Agent and nothing else. Release times: before the
open = 07:00 ET, after the close = 16:05 ET. When Nasdaq gives no time (common for older dates),
the company's habit is used: JPM before the open, Berkshire on a Saturday morning (08:00 ET), the
rest after the close. The card says when a time is a habit rather than confirmed.

**When a date counts.**
- A date first seen on the calendar live counts from that moment.
- A date filled in from history counts from 7 days before the report. Megacaps announce their
  dates 2 to 5 weeks ahead, so this errs on the late side, and "days to the next report" never
  looks more than 7 days ahead.
- A date that later disappears from the calendar (a moved report) stops counting from the moment
  it was seen gone.
- A row reads the card only if every weekday from the day before to 7 days after it has been
  asked of the calendar. Otherwise it is "no read" (`data/sources/earnings_days.csv` records which
  days were asked and when).

**History.** Back to **1 Jan 2018** (a one-off fill, newest first). After that, `update()` keeps
filling at most two older days per call.

**Cost.** `update()` reads the calendar 28 days ahead. Days within a week are asked again every
6 hours, later days once a day, and each past day once more after it is over (to catch the actual
time). At most 4 days, plus 2 history days, per call, 1 second apart. Files:
`data/sources/earnings_megacap.csv`, `data/sources/earnings_days.csv`.

Features (0.0 = no read): `ern_next` (1 at a report, 0 when the next is 7+ days away), `ern_week`
(reports in the next 5 trading days / 5, capped at 1), `ern_last` (1 just after a report, 0 a day
later). Readable columns: `ern_days_next`, `ern_n_next5`, `ern_hours_since`, `ern_n_last24`.

## Limits (both cards)

- The put/call history has a five-year hole (Oct 2019 to Nov 2024), and the two sources measure
  slightly different things.
- The OCC lookback is 2 years. A day that is never fetched within 2 years is lost.
- The earnings calendar is Nasdaq's. A date can move after it is listed. The module follows the
  move, but the listing that came before it was what the engine saw.
- These are data points. Nothing here is claimed to predict price.
