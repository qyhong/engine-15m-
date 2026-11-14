# Oil cards: the `oil` module

Module: `engine15/sources/oil.py`. Markets: WTI and Brent crude (`WTI`, `BRENT`). Tests: `tests/test_oil.py`.
Files: `data/sources/oil_*.csv` and `data/sources/oil_state.json`.

Five cards, written for oil only. The engine's other cards read every market alike. These read what oil
traders watch: the weekly US inventory report, OPEC+ meetings, oil's own volatility index, how hedge
funds are positioned in crude futures, and the spreads (Brent against WTI, this month against next).

Nothing here is claimed to predict anything. Each card gives the engine data points to learn from and
gives you a sentence to read. The history replay is warm-up and post-mortem material, not proof.

## The one rule: only what was public at that 15-minute close

Every reading is placed on a bar only from the moment it was published:

| Data | Counts from |
|---|---|
| EIA weekly report (week ending Friday) | the actual release time in the EIA's archive (Wednesday 10:30 ET; 11:00 ET when a holiday moves it). When the EIA delayed a report (June 2022, November 2023, Christmas 2025), it counts from the delayed release. |
| EIA 5-year norms | built only from earlier years' weeks, all long public |
| OVX close for a day | 16:30 New York that day |
| CFTC report (positions as of Tuesday) | Friday 15:30 ET, with the CFTC's holiday and shutdown dates (the same rule as the `cot` card) |
| ICE Brent report (as of Tuesday) | Friday 15:30 ET; the next business day when that Friday is a UK holiday |
| EIA contract 1 / 2 prices (to April 2024) | the Thursday after the EIA's weekly post (always at or after the real post) |
| Yahoo contract closes | 17:15 New York that day |
| 15m bars | the close of the bar |

Live, a weekly report that was due but not yet on the website counts from the minute the engine first
saw it. Release *schedules* (when the next EIA report is due) are public in advance and are read as such.
`tests/test_oil.py::test_no_lookahead_truncation` cuts every file and both bar series at a set of times
and checks that no earlier row changes.

## Sign convention for the model features

Each card has a few model features between -1 and +1 (0 = no read). **Plus** always means the side
usually read as supportive for *this* market's price: a stock draw bigger than the seasonal norm, money
managers net long, this market gaining on the other one, backwardation. This is a convention so the
engine can compare cards. It is not a forecast. The readable numbers on the page keep their natural sign.

## 1. EIA crude inventories (`eia`)

Every week the US Energy Information Administration (EIA) publishes the Weekly Petroleum Status Report:
how much crude and fuel is held in US tanks. The card reads it from the EIA's own published history
pages (no key needed), from 2012, so the 5-year norms work from 2019 on.

- **Hours to / since the report.** Release times come from `engine15/calhistory.py` (the EIA's archive,
  2019 on). After its last row the EIA's rule is used (Wednesday 10:30 ET, Thursday 11:00 ET in a holiday
  week). `eia_next` rises from 0 to 1 over the 24 hours before the report; `eia_since` falls from 1 to 0
  over the 24 hours after. These carry no direction: they say "the report is near".
- **US commercial crude stocks** (excluding the Strategic Petroleum Reserve), in million barrels, and the
  week's change.
- **5-year norm.** For each week, the average change in the same week of the five years before (at least
  three years needed). Crude stocks are seasonal (refineries run hard in summer), so a 2 million barrel
  draw can be normal in one month and unusual in another. The card compares the week with its norm.
- **Against the 5-year average level.** This week's stocks against the average of the same week over the
  five years before, in %.
- **Cushing, Oklahoma**: the delivery point of the WTI contract. Its stocks and weekly change against its
  own norm.
- **Gasoline and distillate** (diesel, heating oil): weekly changes, and their combined norm.

Features: `eia_next`, `eia_since` (timing); `eia_crude` (crude change against its norm, 5 million barrels
= 1); `eia_cushing` (1.5 million barrels = 1); `eia_products` (gasoline + distillate against the norm,
5 million barrels = 1); `eia_level` (stocks 10% below the 5-year average = +1). The same report applies to
Brent: it is a US report, but the world prices crude off it too.

## 2. OPEC+ calendar (`opec`)

Days to the next and since the last OPEC or OPEC+ ministerial meeting (and the eight-country monthly
calls from 2025), from `calhistory.OPEC_MEETINGS` (public record, date only, nominal 13:00 UTC).

- `opec_week` rises from 0 to 1 over the 7 days before a meeting. `opec_after` falls from 1 to 0 over the
  7 days after. No direction: a meeting can raise or cut output.
- To avoid looking ahead, the card sees an upcoming meeting only 21 days before it (7 days for the
  eight-country calls), and only 1 day before for meetings that were called or moved at short notice
  (April 2020, June 2020, Dec 2020, Jan 2021, July 2021, Nov 2023, Dec 2024, May and July 2025).

**Known gap:** the meeting list in calhistory ends on 1 March 2026. Until newer dates are added there, the
card has no upcoming meeting to show, and "days since" keeps counting from March. The card says so.

## 3. Oil volatility (`oilvol`)

- **OVX**, the Cboe crude oil volatility index (Yahoo daily closes, from 2018): the market's price for
  WTI moves over the next 30 days, in annualised %. Shown with its percentile against the past year and
  its change over 5 trading days. OVX is computed from options on the USO fund (WTI). Brent has no free
  equivalent, so the Brent card shows OVX too.
- **Realised volatility** from this project's own 15m bars of that market: over 1, 5 and 20 trading days,
  annualised.
- **OVX / 20-day realised**: above 1, options price more movement than oil has shown lately.

Features: `ovol_level` (percentile: 0th = -1, 100th = +1), `ovol_chg5` (OVX up 35% in 5 days = +1),
`ovol_rv_trend` (5-day realised twice the 20-day = +1), `ovol_vrp` (OVX twice the realised = +1). These
measure how much oil moves, not which way.

## 4. Crude futures positioning (`oilpos`)

How hedge funds and CTAs ("managed money") are positioned, from the weekly Commitments of Traders reports.
Each market reads its own exchange:

| Market | Contract | Source |
|---|---|---|
| WTI | NYMEX light sweet crude (CFTC code 067651, "WTI-Physical" from Feb 2022) | CFTC public reporting API, disaggregated, futures only |
| BRENT | ICE Brent Crude Futures | ICE Futures Europe's own COT history files (same layout as the CFTC's), futures only |

Both from 2015, so the 3-year percentile works from 2018. The numbers: net position (long minus short
contracts), weekly change, open interest, net as % of open interest, and where that share sits in the
last 3 years (0 = most short, 100 = most long). One contract is 1,000 barrels.

Features: `opos_level` (net 30% of open interest = +1), `opos_pctile` (3-year percentile: 0th = -1,
100th = +1), `opos_chg` (a weekly change of 3 standard deviations = +1).

## 5. WTI-Brent and curve (`oilspread`)

- **Brent minus WTI** from this project's own 15m bars, at times both markets have a bar: the level in
  dollars, its z-score against the last 20 trading days and the last year, and its change over about one
  trading day. The bars are Dukascopy CFDs before the join and front-month futures after it, so the two
  legs can sit on different contract months near expiry; read it as a guide, not an exchange spread.
- **Front month minus second month** (the curve). Above zero is backwardation: prompt oil costs more than
  later oil, usually a sign of tight supply. Below zero is contango.
  - WTI, 2012 to 5 April 2024: the EIA's daily NYMEX contract 1 and 2 prices. The EIA stopped this series
    after 5 April 2024.
  - WTI and Brent, from late October 2026: Yahoo's daily closes of the two nearest listed contracts
    (CL for WTI, BZ for Brent). Yahoo drops a contract once it expires, so this history starts with the
    current front month and grows by one day each day.
  - **Missing:** April 2024 to October 2026 for WTI, and everything before October 2026 for Brent. There
    the curve is "no read".

Features: `ospr_z20`, `ospr_z250` (spread z-score, 2.5 = 1), `ospr_chg1d` ($1 = 1), signed so that +
means this market gained on the other (for WTI a narrowing Brent-WTI spread is +); `ospr_curve` (front
2% above second = +1).

## How often it asks the internet

`update()` runs in the live loop every 15 minutes and usually makes no request. A weekly report is asked
for only once its release time has passed, then every 30 minutes until it appears. Daily closes are asked
for once the close is final (and at least every 12 hours). The EIA contract history is fetched once.
Timeouts 30 s, 1.5 s between requests, a generic browser User-Agent, no keys. A failure keeps the old file
and never stops the engine. The first run (the full backfill) takes about a minute; it was run on
11 Nov 2026.
