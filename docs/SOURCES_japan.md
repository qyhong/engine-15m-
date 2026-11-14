# Japan watch: the `japan` card

Module: `engine15/sources/japan.py`. Market: USDJPY only. Tests: `tests/test_japan.py`.

Three things a USDJPY trader keeps an eye on: the Bank of Japan's next decision, Japan's next
important data release, and how close the yen is to where Japan's Ministry of Finance (MoF)
stepped in before, and how fast it got there.

## The numbers on the card

- **Next BoJ decision**: date and days away. The BoJ publishes its meeting dates about a year
  ahead. The decision is taken as out at 12:00 Tokyo (03:00 UTC) on the meeting's last day. The
  BoJ has no fixed time; it is usually between 11:30 and 13:00 Tokyo.
- **Next JPY high-impact release**: title and hours away, from the ForexFactory weekly calendar
  feed. The engine already reads that feed for US releases; this card keeps Japan's events in
  its own file. "None in this week's calendar" means nothing High-impact is listed for the rest
  of the feed's week.
- **Reference intervention level**: the nearest past intervention level at or above today's
  price. If price is above every past level, it is the highest one. The card shows its date and
  amount, the **distance to it** in %, and the **distance to the highest level** ever defended.
- **Last confirmed intervention**: days since.
- **Change over 1 week / 1 month**: the % move of USDJPY, and that move in standard deviations
  of a usual 1-week (1-month) move over the past year. Officials talk about the *speed* of a move
  ("rapid, one-sided"), not only its level.

## The intervention table (data, with sources)

Kept in `data/sources/jpy_interventions.csv`. The owner may add a row; the file wins over the
built-in table. Amounts are the MoF's published daily figures ("Foreign Exchange Intervention
Operations"; the 2024 and 2026 quarterly pages were checked on 10 Nov 2026). The level is the
USDJPY high that day in this project's own bars.

| Date | Level (day high) | Yen bought, JPY bn | Confirmed by the MoF (UTC) |
|---|---|---|---|
| 22 Sep 2022 | 145.90 | 2,838.2 | 22 Sep 2022 (announced the same day) |
| 21 Oct 2022 | 151.94 | 5,620.2 | 31 Oct 2022 (monthly total) |
| 24 Oct 2022 | 149.45 | 729.6 | 31 Oct 2022 |
| 29 Apr 2024 | 160.20 | 5,918.5 | 31 May 2024 |
| 1 May 2024 | 157.98 | 3,870.0 | 31 May 2024 |
| 11 Jul 2024 | 161.75 (cycle high 161.94 on 3 Jul) | 3,167.8 | 31 Jul 2024 |
| 12 Jul 2024 | 159.38 | 2,367.0 | 31 Jul 2024 |
| 30 Apr 2026 | 160.72 | 6,278.7 (record day) | 29 May 2026 |
| 4 May 2026 | 157.30 | 780.2 | 29 May 2026 |
| 6 May 2026 | 157.89 | 4,675.9 | 29 May 2026 |

Other feeds print slightly different highs (for example 160.245 on 29 Apr 2024). The 2022 daily
amounts are as widely reported; the MoF's 2022 quarterly pages were not reachable when this was built.

## Model features (scaled; 0.0 = no read)

| Feature | Meaning |
|---|---|
| `jp_boj_next` | 1 at the BoJ decision, falling to 0 a week (168 h) before it |
| `jp_event_next` | 1 at a JPY High-impact release, falling to 0 a day before it |
| `jp_mof_zone` | 1 at (or above) the reference intervention level, 0 when 5% or more below it |
| `jp_speed_1w`, `jp_speed_1m` | the 1-week / 1-month move in standard deviations, / 3, clipped to ±1 (+ = USDJPY up, yen weaker) |
| `jp_risk` | the zone times how fast USDJPY has been rising (the larger of the two speeds, from 0 at no rise to 1 at 2 standard deviations). It is high only when price is near a defended level and climbing fast |

Readable columns (NaN = no read): `jp_px`, `jp_boj_hours`, `jp_event_hours`, `jp_mof_level`,
`jp_mof_dist_pct`, `jp_mof_top_dist_pct`, `jp_days_since_mof`, `jp_chg_1w_pct`, `jp_chg_1m_pct`,
`jp_speed_1w_z`, `jp_speed_1m_z`.

## When something counts (no look-ahead)

- A BoJ meeting counts from 180 days before it. The 2020 emergency changes count only from when
  they were made: the meeting brought forward to 16 Mar 2020 (announced Friday 13 Mar), April's
  meeting cut to one day, and the extra meeting of 22 May 2020.
- A feed event counts from the moment `update()` first saw it.
- An intervention counts from the MoF's confirmation, not from the day it happened. For most of
  them that is the monthly total published at 19:00 Tokyo on the month's last business day.
  Traders often guessed sooner from the price action.
- Price speed uses the project's own closed USDJPY 15m bars up to the row's own close. Its
  yardstick is the past year of the same measure, looking backward only.

## Source, history, cost

- BoJ dates: boj.or.jp (2018 to 2027, built in).
- JPY releases: `nfs.faireconomy.media/ff_calendar_thisweek.json`, asked **at most every 3
  hours** (the engine's econ module already asks it every step). The feed shows only the
  current week, so **this history starts on 10 Nov 2026** and grows from there. Before that,
  `jp_event_*` is "no read". Files: `data/sources/jpy_events.csv`, `data/sources/japan_state.json`.
- Interventions: from 22 Sep 2022. Before that, the zone and risk readings are "no read".
- Price speed: from the project's USDJPY bars (2019 on; it needs about 60 trading days of bars
  to set its yardstick).

## Limits

- The calendar feed is a third-party aggregator. Its impact labels are its own, and a week's
  events appear only when that week's file is published.
- Intervention levels are where the MoF acted in the past, not a promise. Japan has also acted
  well below the previous high (Sep 2022 at 145.9).
- Stealth interventions are confirmed weeks later. Until the confirmation, the card does not
  know about them.
- It is a data point. Nothing here is claimed to predict price.
