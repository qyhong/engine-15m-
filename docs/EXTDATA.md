# Gold, silver, USDJPY and the S&P 500: 15-minute bars (`engine15/extdata.py`)

Data layer only; nothing here trades. `data/xauusd_15m.csv`, `xagusd_15m.csv`, `usdjpy_15m.csv` and `spx_15m.csv`
have the crypto files' shape (`ts_ms` = bar OPEN time, UTC ms; closed bars only; `taker_buy` empty).

```python
data.load("XAUUSD")                    # the project's own loader reads them unchanged
extdata.build_history("XAUUSD")        # make the file from scratch (one Yahoo request); returns a report
df, n_new = extdata.update("XAUUSD")   # append bars closed since the last stored one; never raises on a network failure
extdata.is_open("XAUUSD", when_utc)    # is the market trading at that moment
extdata.report("XAUUSD")               # rows, first/last, bars per weekday, splice ratio, join date, gaps
```

## Sources

| Asset | Older history, 2019-01-01 on | Recent 60 days and live |
|---|---|---|
| XAUUSD | Dukascopy spot gold, BID | Yahoo `GC=F`, the front gold future |
| XAGUSD | Dukascopy spot silver, BID | Yahoo `SI=F`, the front silver future |
| USDJPY | Dukascopy USDJPY, BID | Yahoo `JPY=X` |
| SPX | Dukascopy `USA500` index CFD, BID | Yahoo `^GSPC`, the cash index |

Dukascopy: the Kronos store (`C:\tmp\kronos\data\markets`, read-only; ended 5 Nov 2026 at build time). Yahoo: its free chart API.

## The join

Yahoo is used from its first bar on; everything older is Dukascopy. The two sit at slightly different price
levels, so every older Dukascopy price (open, high, low, close) is multiplied by one ratio: the median of
`yahoo_close / dukascopy_close` over the first 96 bars both sources have (one day, at the join).

| Built 10 Nov 2026 | Join (UTC) | Ratio used | Bars in both | Median difference after adjustment: at the join / all common bars |
|---|---|---|---|---|
| XAUUSD | 2026-09-01 04:00 | 1.011042 | 4,280 | 0.010% / **0.42%** |
| XAGUSD | 2026-09-01 04:00 | 1.009477 | 4,280 | 0.020% / **0.39%** |
| USDJPY | 2026-08-18 23:00 | 0.999972 | 5,380 | 0.0016% / 0.0016% |
| SPX | 2026-08-18 13:30 | 1.000034 | 1,481 | 0.0033% / 0.0036% |

Why the first day and not the whole overlap: a future costs more than spot and sinks toward it as the contract
ages. Gold's ratio fell from 1.0110 on 1 Sep to about 1.0024 by 5 Nov (silver alike): 0.86% in ten weeks. The
whole-overlap median (gold 1.006771, silver 1.005553) would leave a step of about 0.4% at the join; the ratio at
the join leaves none. For USDJPY and the S&P the two agree to five decimals. `JOIN_BARS = None` gives the other rule.

Volume is each source's own number and is NOT comparable across the join: Dukascopy's quoted size before it;
after it futures contracts (gold, silver), index share volume (S&P), and always 0 for USDJPY.

## Sessions (all follow New York time, so they move an hour in UTC with US daylight saving)

- Gold, silver: Sunday 18:00 to Friday 17:00 New York, shut 17:00-18:00 every day. In winter UTC that is
  Sunday 23:00 to Friday 22:00 with the break at 22:00-23:00; in summer one hour earlier. 92 bars a full day.
- USDJPY: Sunday 17:00 to Friday 17:00 New York (winter: Sunday 22:00 to Friday 22:00 UTC). 96 bars a day.
- S&P 500: Monday-Friday 09:30-16:00 New York, 26 bars a day. Only the Dukascopy CFD bars that open inside
  that session are kept, with NYSE holidays removed and the half days cut at 13:00 (725 bars dropped for
  those). The holiday rule matches every day Yahoo's daily `^GSPC` file traded from 2013 to 2026.
- `zoneinfo` works here. Without time-zone data the module uses its own US daylight-saving rule; a test checks they agree.

## The live feed and how late it is

Only closed bars are stored. Yahoo's last element is always live and is dropped; a bar counts once the feed's
own last trade time has passed its end (or the market has been silent 20 minutes), and never before the clock
has. Empty rows, rows off the 15-minute grid and single prints inside the daily break or after the close are dropped.
Measured 10 Nov 2026: `GC=F` and `SI=F` ran 602-608 seconds behind the clock, `JPY=X` and `^GSPC` 1-2 seconds. A gold
or silver bar is available about 10 minutes after it closes: an engine stepping on the quarter hour will not have it yet.

## Weaknesses

- Gold and silver are a spot price below the join and a futures price above it. The future keeps sliding toward
  spot and will jump when Yahoo rolls to the next contract (none seen in these ten weeks; from the measured slide
  expect roughly +0.5% to +1%). That jump is not a market move, and nothing here removes it.
- Yahoo skips US holidays for the futures: no `GC=F`/`SI=F` bar from Friday 4 Sep 20:45 to Tuesday 8 Sep
  04:00 UTC (Labor Day), 29 hours the market did trade. It is the largest gap in both metal files.
- Yahoo's USDJPY week starts at London midnight on Monday, two hours after the market opens, so from the
  join on the first 8 bars of each week are missing. `is_open(asset, t, feed=True)` answers for the feed.
- For gold, silver and USDJPY, `is_open` knows the weekly hours only. Christmas, New Year, Good Friday and
  the short US-holiday halts read as open; in the history they are the 14-26 hour and 2.5-4 hour gaps.
- The cash index's 09:30 bar opens on stale prices (median 0.07% from the CFD's open; 0.004% for other bars).
- `update` only appends (a late Yahoo bar is never filled in); a store over 60 days old needs `build_history`.
- `data.gates(df)["pass"]` is False for all four: it counts nights and weekends as missing bars. Its other
  fields are clean (monotone, no duplicates, no OHLC violations). Use `extdata.report` for gaps.
- Yahoo's chart API is free and unofficial: no guarantee it stays up or keeps this shape.
