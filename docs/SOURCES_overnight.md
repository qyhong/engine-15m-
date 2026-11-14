# S&P futures overnight: what `engine15/sources/overnight.py` reads

Written 2026-11-11 with the module. One decision card, for the S&P 500 cash index (`SPX`) only. It is a data
point for the engine's decisions and for post-mortems. Nothing here is claimed to predict anything, and none
of it has been tested for that.

## What the card says

The cash index trades 09:30 to 16:00 New York. S&P futures trade almost all the time in between. When the cash
market opens, a trader looks at what happened overnight. The card reads that at every SPX 15-minute close:

- **Opening gap.** Today's cash open against yesterday's cash close, in % and in hourly ATRs (ATR(14) of the
  1-hour chart, the yardstick the engine uses everywhere else).
- **Overnight move.** How far the futures went from yesterday's cash close to 09:30, set against the average
  size of that move over the previous 20 sessions ("1.5x the typical 0.44%").
- **Overnight range.** The futures high and low between the two cash sessions, put on the index's scale. The
  card says where the futures sat in that range at 09:30, where price is in it now, and how far the overnight
  high and low are from price in hourly ATRs. Traders often treat these two prices as levels for the day.
- **Gap fill.** How much of the gap price has taken back so far today (the furthest it got), and whether it
  has reached yesterday's close ("filled"), and after how many bars.
- **Trend strength.** The net overnight move divided by the distance the 15-minute closes travelled. 1 = a
  straight line, near 0 = back and forth. A random walk scores about 0.1.
- **By session.** The move split three ways: late US (from the cash close to 18:00 New York, which includes
  the weekend for a Monday), Asia (18:00 New York to 08:00 London), Europe (08:00 London to 09:30 New York).

Example, Tuesday 10 Nov 2026, the newest bar on disk at the time of writing (late morning New York), as the
engine would journal it:

> The S&P 500 opened 0.48% below yesterday's close (7,549.01 to 7,513.09, 0.7 hourly ATRs); S&P futures moved
> -0.65% from yesterday's cash close to 09:30 (1.5x the 20-session typical 0.44%), by session: late US +0.11%,
> Asia +0.05%, Europe -0.80% (largest: Europe); the overnight range was 7,485.95 to 7,575.43 (1.20%) and the open
> sat 16% of the way up it; at 7,496.22 price is 1.5 hourly ATRs below the overnight high and 0.2 above the low;
> so far today price has retraced at most 86% of the gap (yesterday's close 7,549.01 not reached).

## Features (what the card's voice sees; 0.0 = no read)

| Feature | Meaning | Scale |
|---|---|---|
| `on_gap` | the opening gap in hourly ATRs (the ATR known at the first close of the day) | 2 ATRs = 1.0, clipped at +/-1.5 |
| `on_fill` | how much of the gap has been taken back so far today, signed by the direction of that move | -1 = an up gap fully filled, +1 = a down gap fully filled; 0 when the gap is under 0.05% |
| `on_pos` | where price is in the overnight range | -1 = at the low, +1 = at the high, clipped at +/-1.5 (outside the range) |
| `on_move` | the overnight futures move against its 20-session typical size | twice the typical = 1.0, clipped at +/-1.5 |
| `on_trend` | the overnight path's efficiency, signed | 0.5 = 1.0, clipped at +/-1 |

Readable columns (`RAW`, NaN = no read): `on_close`, `on_atr1h`, `on_prev_close`, `on_open`, `on_gap_pct`,
`on_gap_atr`, `on_high_px`, `on_low_px`, `on_range_pct`, `on_open_pos_pct`, `on_move_pct`, `on_typical_pct`,
`on_move_x`, `on_er`, `on_late_pct`, `on_asia_pct`, `on_europe_pct`, `on_fill_pct`, `on_filled`, `on_fill_bars`,
`on_high_atr`, `on_low_atr`, `on_pos_pct`, `on_basis_pct`, `on_roll`, `on_bars`, `on_hours`, `on_src`.

## The data

One nearly-24-hour S&P series, kept in `data/sources/overnight_es_15m.csv` (bar open time in UTC ms, closed
bars only, a `src` column: 0 = Dukascopy, 1 = Yahoo).

| Part | Source | Hours | On disk at the first build (11 Nov 2026) |
|---|---|---|---|
| History | Dukascopy USA500 index CFD (the read-only Kronos store, `C:\tmp\kronos\data\markets\SPX\15m.csv.gz`) | Sunday 18:00 to Friday 16:15 New York, shut 16:15-18:00 | 1 Nov 2018 to 5 Nov 2026 23:45 UTC |
| Recent and live | Yahoo `ES=F`, the E-mini S&P 500 front future, 15m (Yahoo serves about 60 days) | Sunday 18:00 to Friday 17:00 New York, shut 17:00-18:00 | from 6 Nov 2026 on, extended by `update()` |

183,142 bars in all. The engine's own SPX file keeps only the cash-hours bars of the same CFD; this file keeps
every hour. The cash index itself (yesterday's close, today's open, today's bars) comes from the engine's SPX
file, `data/spx_15m.csv`.

**History depth.** Overnight readings exist from 3 Jan 2019, the second session of the engine's SPX history:
1,969 of 1,976 sessions to 10 Nov 2026 have a full read. The six without one are 2 Jan 2019 (no yesterday)
and five days of March 2020, when the futures were limit-locked and the CFD stopped quoting near the open.
The 20-session typical move needs 10 sessions before it speaks.

**Splice.** As `extdata.splice` does it: one ratio, the median of `ES=F close / CFD close` over the 96 common
bars nearest the join, multiplies every older CFD price (1.003822 at the first build, from 4,138 common bars).
The CFD is used wherever it exists, ES=F after its last bar, because the CFD follows the cash index and has
no contract rolls or stray prints. Later fetches are stitched on by the median of `stored / new` close over
the bars both have, so when Yahoo swaps all 60 days to the next contract (it does so for 15m data) no step
is left in the file.

**The file's price level means nothing on its own.** It is a futures level, or a CFD scaled to one. Every
reading is taken inside one overnight window and put on the index's scale by that window's own basis.

**Basis: futures to the cash index.** The brief asked for the futures/cash ratio at the open. Measured over
49 sessions (2 Sep to 10 Nov 2026, ES=F against `^GSPC`), that ratio jumped about 0.12% from day to day (up to
0.29%), because the cash index's first print at 09:30 is stale (many stocks have not traded yet). The ratio
at the previous cash close moved only 0.02% a day. So the overnight high and low are put on the index's scale
with **the ratio at yesterday's cash close** (cash close / the futures close of the bar ending then), known
before the window opens. The ratio at the open is still computed, and is used to spot a contract roll. It is
shown as `on_basis_pct`: the futures' premium over cash, in % (0.31% on 10 Nov 2026).

**Fetching.** `update()` builds the file once (Dukascopy plus 60 days of ES=F), then asks Yahoo only when the
newest stored bar closed more than 20 minutes ago, and at most once every 10 minutes (60 while the futures are
shut). It asks for 5 days of bars, or 60 when the file is more than 4 days old. One request, 30 s timeout, a
browser User-Agent, no key. It never raises: a failure keeps the old file and returns `failed: <reason>`.

## When a value is known (no look-ahead)

Row i uses only what had closed by the close of SPX bar i. The overnight window is the futures bars that
closed between yesterday's cash close and 09:30 today, so it is complete at the open and the first cash close
(09:45) already has all of it. No futures bar from today's cash session is ever read. The only one read from
yesterday's session is the bar that closed at yesterday's close, for the basis. Today's fill and position use
today's cash bars up to bar i. The typical move uses only earlier sessions. Live, ES=F runs about 10 minutes
behind on Yahoo, so the last overnight bar (09:15-09:30) arrives about 09:40, before the first close.
`tests/test_overnight.py` checks this four ways. It cuts both series at a bar's close. It cuts only the index.
It rewrites every futures bar traded during the cash session. It rewrites everything after a cut. No earlier
row may change in any of them.

## Limits

- **Contract rolls.** Yahoo's ES=F switches contract every quarter, and the new one costs about 0.5% to 1.1%
  more (2024-26). If such a step lands inside a window, the card catches it: the basis at the open differs
  from the basis at yesterday's close by over 0.40% (the most seen without a roll was 0.29%). The card then
  finds the trading break whose step matches and removes only that basis change (`on_roll` = 1). If no
  break matches, the day's futures readings are "no read" (`on_roll` = 2). A roll smaller than 0.40% (if
  rates fall) would get through and add itself to that day's overnight move.
- **Stray prints.** Yahoo has bars that open on a wild print (+2.6% on 30 Oct 2026). Within continuous
  trading a bar opens where the last one closed, so an open more than 0.25% away is set back to that close,
  and a high or low that was the stray print is cut back. 18 bars in the stored series are repaired this way.
  A stray print in the middle of a bar's high or low is not caught.
- **The gap uses the cash index's own open.** That first print is stale, about 0.07% off a tradable price on
  a typical day in the Yahoo part. The overnight move uses the futures and does not have this problem. The
  two agree to within 0.02% (std) in the CFD history.
- **Two sources.** The CFD has almost no trading 16:15-18:00 New York. ES=F trades until 17:00, so its
  "late US" segment has one more hour in it. Neither source has volume worth comparing. Volume is not read.
- **Holidays.** On a cash holiday the futures still trade (sometimes a short day). That trading counts as
  overnight: the window runs from the last cash close to the next cash open. Windows longer than 100 hours
  are treated as a data hole. So are windows with under six hours of futures bars, or with no futures price
  within 30 minutes of either end. All of these are "no read".
- **Yahoo's chart API is free and unofficial.** If it is down for over 60 days, the file cannot be refilled
  from it. Kronos' Dukascopy store would have to be refreshed and the file rebuilt (`overnight.build()`).
- **The Asia/Europe split** uses fixed clock boundaries: 18:00 New York and 08:00 London. These are not
  exchange session flags.
