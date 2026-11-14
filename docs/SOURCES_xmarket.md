# Five cards for gold, silver, USDJPY and the S&P 500 (`engine15/sources/xmarket.py`)

Built 11 Nov 2026 at the owner's request: new cards for the four non-crypto markets. Each card is
a set of readings the engine learns from and the owner reads. None of them is claimed to predict
anything; the replay can reject a reading, never prove one.

| Card | Shown for | Sources |
|---|---|---|
| Volatility gauges | S&P 500, gold, silver, USDJPY | Cboe VIX, VIX9D, VIX3M, GVZ (Yahoo daily closes) |
| Rates and the dollar | gold, silver, USDJPY, S&P 500 | FRED (US Treasury yields), Yahoo (dollar index), Japan Ministry of Finance (JGB yields) |
| Metals ratios | gold, silver | this project's own 15m gold and silver bars; Yahoo copper and gold futures |
| Stock-market breadth | S&P 500 | Yahoo daily closes of SPY, RSP, IWM, XLK, XLU, SMH |
| Gold and silver ETF holdings | gold, silver | SPDR's GLD archive, the iShares SLV page, Yahoo GLD/SLV volume |

## When a number counts (no look-ahead)

A 15-minute row uses only what was public at that bar's close:

- **Yahoo daily closes** (VIX family, ETFs, futures, dollar index): from the close in New York plus
  15 minutes. Stock ETFs 16:15, Cboe volatility indices 16:30, copper / gold futures and the dollar
  index 17:15. So a gold bar at 10:00 New York on Tuesday sees Monday's VIX, not Tuesday's.
- **US Treasury yields (FRED)**: FRED posts the Federal Reserve's daily yields the next business day,
  so a yield for date D counts from 17:00 New York on the next federal business day (weekends,
  federal holidays including Columbus Day and Veterans Day skipped). Monday's bars see Thursday's yield.
- **Japan bond yields (Ministry of Finance)**: a Tokyo date D counts from 00:00 UTC of D + 1.
- **GLD holdings**: trading date D counts from 12:00 UTC of D + 1 (the same rule as the crypto ETF flows).
- **SLV holdings**: a snapshot "as of D" counts from 12:00 UTC of D + 1, and never before it was fetched.
- **Gold/silver ratio and lead**: closed 15m bars only. The ratio's one-year percentile compares the
  live ratio with each past day's last bar, and a day's last bar counts only once the day is over.

Files keep only values whose time has come: a Yahoo bar for "today" is never stored while the
session is still trading. A value goes silent ("no read") 6 days after it became known (10 days for
Japan, whose Golden Week can close the bond market for a week), so a source that stops updating
falls quiet instead of repeating itself. `tests/test_xmarket.py` cuts every file and the bars at
several moments and checks that no earlier row changes.

## Volatility gauges (`volx`)

| Number | Meaning |
|---|---|
| VIX | the S&P 500's expected volatility over 30 days, in % a year. Shown with its percentile among the last 252 trading days and its 5-day change in points |
| VIX9D, VIX3M | the same over 9 days and 3 months |
| VIX9D / VIX | above 1: the next nine days are priced as riskier than the month, fear is near-term |
| VIX / VIX3M | below 1 (usual, "contango"): calm. Above 1 ("backwardation"): fear now is priced above the next three months, typical of selloffs |
| GVZ (gold and silver only) | Cboe's gold volatility index (options on GLD), level, percentile, 5-day change |

Readings: `vx_level` (VIX percentile, -1 at the year's low to +1 at its high), `vx_front`
(VIX9D/VIX, 0.95 = 0, +-0.15 = +-1), `vx_curve` (VIX/VIX3M, 0.90 = 0, +-0.15 = +-1), `vx_chg5`
(5-day change, +35% = +1), `vx_gold` (GVZ percentile; gold and silver only).
History: all four from 2018 (fetched from 1 Jan 2018 so the percentile has a year of warm-up by 2019).

## Rates and the dollar (`rates`)

| Number | Meaning |
|---|---|
| US 2-year, 10-year | Treasury constant-maturity yields (FRED DGS2, DGS10), %, with daily and 5-day changes in basis points |
| 10-year real | the 10-year TIPS yield (FRED DFII10): the yield after inflation. Gold has often moved against it |
| 10y minus 2y | the curve, in basis points |
| Treasury data of | the date behind the yields (usually the previous business day: FRED's lag) |
| Dollar index | ICE DXY (Yahoo DX-Y.NYB), daily and 5-day change in % |
| Japan 2-year, 10-year (USDJPY only) | JGB benchmark yields from Japan's Ministry of Finance, **daily** (not the monthly FRED series) |
| US-Japan gap | US yield minus Japan's on the same date (Tokyo closes first), and its 5-day change in basis points |

Readings: 5-day changes clipped to [-1, 1]: `rt_y2_5d` and `rt_y10_5d` (25 bp = 1), `rt_real_5d`
(20 bp = 1), `rt_dxy_5d` (1.5% = 1), `rt_gap_5d` (US-Japan 2-year gap, 25 bp = 1; USDJPY only).
History: FRED from 2018, MOF daily from 1974 (kept from 2018), dollar index from 2018.

Limit: FRED refuses requests that carry a browser User-Agent from a script (tested 11 Nov 2026), so
FRED is asked with the requests library's own plain User-Agent; it names no person or address.
Every other source gets a generic browser User-Agent.

## Metals ratios (`metals`)

| Number | Meaning |
|---|---|
| Gold/silver ratio | ounces of silver one ounce of gold buys, from the last closed 15m bars of each. Percentile against the last 252 days' closing ratios; change over about five trading days (460 bars). A falling ratio = silver gaining on gold |
| Silver minus gold, 1h / 4h / 24h | silver's % change minus gold's over the last 4, 16 and 96 trading bars (percentage points): which metal led |
| Copper | COMEX copper futures (HG=F), $/lb, daily and 5-day change |
| Copper/gold ratio (x1000) | copper futures over gold futures (GC=F), x1000; percentile and 20-day change. Often read as a growth-versus-safety gauge |

Readings: `mt_gsr_level` (ratio percentile, -1 to +1), `mt_gsr_trend` (5% in five days = 1),
`mt_lead_1h`, `mt_lead_4h`, `mt_lead_24h` (silver minus gold in units of two standard deviations of
that spread over the window, from its last 30 trading days), `mt_cugold_20d` (10% in 20 days = 1).
History: gold and silver bars from 2019 (the percentile starts in late May 2019 once 126 days are on
file); copper and gold futures from 2018.

## Stock-market breadth (`eqbreadth`)

| Ratio | Rising means |
|---|---|
| RSP/SPY | the average S&P stock (equal weight) beating the cap-weighted index |
| IWM/SPY | small caps beating large caps |
| XLK/XLU | technology beating utilities (risk appetite) |
| SMH/SPY | semiconductors beating the index |

Each with 5- and 20-day changes in %. The card's label reads the last 20 trading days: **narrow
rally** (SPY up more than 1% while RSP/SPY falls more than 1%), **broad rally** (SPY up, RSP and IWM
keeping up), **risk-off rotation** (SPY down more than 1% and XLK/XLU down more than 2%), **selloff
led by the biggest names** (SPY down, RSP/SPY up more than 1%), **broad selloff**, or **mixed**.
Readings: `eb_rsp_5d` / `eb_rsp_20d` (1.5% / 3% = 1), `eb_iwm_5d` / `eb_iwm_20d` (2.5% / 5%),
`eb_tech_5d` / `eb_tech_20d` (5% / 10%), `eb_semis_20d` (10%). History: 2018 on.

## Gold and silver ETF holdings (`goldetf`)

| Number | Source and meaning |
|---|---|
| GLD tonnes | SPDR Gold Shares' own daily historical archive (xlsx, from Nov 2004; kept from 2018): gold held by the trust, daily and 5-day change in tonnes and % |
| GLD premium | GLD's bid/ask midpoint against its indicative value at 4:15pm New York, in % (same archive) |
| SLV ounces | the iShares Silver Trust page shows only today's "Ounces in Trust". The engine stores one snapshot a day from 11 Nov 2026 on; daily and 5-day changes appear once enough snapshots exist. **There is no free SLV history**: iShares' download link returns the web page, not a file |
| GLD / SLV dollar volume | Yahoo daily close x shares traded, against its 20-day median. A proxy for activity, not for the direction of flows |

Readings: `ge_gld_1d` (0.5% = 1), `ge_gld_5d` (1.5% = 1), `ge_gld_prem` (0.15% = 1), `ge_slv_5d`
(1.5% = 1; silent until five snapshots exist), `ge_gld_dvol` and `ge_slv_dvol` (log of the multiple
of the 20-day median; 3x = 1, a third = -1).

## Fetching (`update`, run by the live loop every 15 minutes)

Each source has its own job. A job asks the network only when a newer value should be public by
its publication rule (for example after 16:30 New York for the VIX), at least every 12 hours, or
when its file is missing; a failed job keeps its old file and waits 30 minutes before trying again.
On most 15-minute steps nothing is fetched (about 0.05 s). A full refresh is 15 Yahoo requests (at
least 1 s apart, sharing the project's Yahoo clock with `extdata.py`), 3 FRED, 1-2 MOF, 1 SPDR and
1 iShares request, about 30 seconds. Timeouts are 30 s. Files: `data/sources/xm_*.csv` and the
schedule in `data/sources/xm_state.json`.

## Limits, plainly

- Daily data reaches a 15m bar late by design: the VIX of a day reaches the next day's bars, a
  Treasury yield reaches bars one business day later still.
- Yahoo daily closes can be revised slightly in the days after; the last three weeks are re-read on
  each fetch and the newest copy kept.
- GLD's 12:00 UTC rule is a conservative guess at when the archive is updated; the issuer does not
  state a time.
- The gold/silver lead uses trading bars, so "24h" means 96 bars of trading (about a day), and the
  first bars after a weekend compare with Friday.
- Breadth thresholds (1%, 2%) and every scale above were declared once, before looking at results.
