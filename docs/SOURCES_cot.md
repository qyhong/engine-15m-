# Futures positioning (CFTC): the `cot` card

Module: `engine15/sources/cot.py`. Markets: gold, silver, USDJPY, S&P 500. Tests: `tests/test_cot.py`.

## What it reads

Every week the US Commodity Futures Trading Commission (CFTC) publishes the Commitments of
Traders report: who holds the open futures contracts on each US futures exchange, sorted into
trader groups. The card reads the speculative group for each market:

| Market | Futures contract | Report | Group read |
|---|---|---|---|
| XAUUSD | COMEX gold (code 088691) | Disaggregated | Managed money (hedge funds, CTAs) |
| XAGUSD | COMEX silver (084691) | Disaggregated | Managed money |
| USDJPY | CME Japanese yen (097741) | Traders in Financial Futures | Leveraged funds |
| SPX | CME E-mini S&P 500 (13874A) | Traders in Financial Futures | Leveraged funds (asset managers shown beside them) |

Futures-only figures (options not folded in).

## The numbers on the card

- **Net position**: long contracts minus short contracts held by that group, in contracts.
  One gold contract is 100 oz, one silver contract 5,000 oz, one yen contract 12.5 million yen,
  one E-mini $50 times the index.
- **Weekly change**: net now minus net in the previous report.
- **Open interest**: all open contracts in that future.
- **Net as % of open interest**: net divided by open interest. This makes years comparable when
  the market's size changes.
- **3-year percentile**: where this week's net share sits among the last 156 weekly reports
  (0 = the most short in three years, 100 = the most long). Needs at least 52 reports.
- **Asset managers, net** (yen and S&P only): pension funds, insurers and mutual funds, for context.
  In the E-mini, leveraged funds are usually net short. Much of that short is the hedge side of
  basis trades, not a bet against the index. So read the percentile and the change, not the sign alone.

**The yen sign.** The CME yen future is priced in US dollars per yen, the opposite way round to
USDJPY. Leveraged funds net **long** the yen future are positioned for USDJPY to **fall**. The
card says this in words. The readable numbers keep the CFTC's own sign (the future's terms).
The engine's model features (`cot_level`, `cot_pctile`, `cot_chg`) are multiplied by -1 for
USDJPY, so for the features "+" always means positioned for the traded market to rise.

Model features (scaled; 0.0 = no read): `cot_level` = net share of open interest / 30%, clipped
to ±1; `cot_pctile` = 3-year percentile mapped to -1..+1; `cot_chg` = weekly change in net share
in standard deviations of its own 3-year history / 3, clipped to ±1.
Readable columns (natural units; NaN = no read): `cot_net`, `cot_net_chg`, `cot_oi`, `cot_net_pct_oi`,
`cot_pctile_3y`, `cot_am_net`, `cot_report_age_d` (days from the positions date to the 15m close).

## When a report counts (no look-ahead)

Positions are counted on a **Tuesday**. The report is **published on the Friday at 15:30 New
York time**. A report is used from its release onward, never from the Tuesday. The release time
of every report is worked out from the CFTC's own rules:

1. The Friday of that week at 15:30 ET.
2. One business day later (normally the Monday) when a federal holiday falls on the Wednesday,
   Thursday or Friday after the positions date. This rule reproduces all 52 dates of the CFTC's
   published 2026 schedule (for example, Veterans Day on Wednesday 11 Nov 2026 moves that week's
   release to Monday 16 Nov). A test checks this.
3. The actual catch-up dates after the 2018-19 shutdown, the 2023 ION cyber incident and the
   2025 shutdown (table in `RELEASE_OVERRIDES`, from the CFTC's announcements). During the 2025
   shutdown no report came out from 26 Sep to 19 Nov 2025. The card goes silent after 15 days
   without a new report, so it said nothing for most of that gap.
4. Live: if the API still lacks a report after its release time, the report counts only from
   the moment `update()` first saw it (`known_ms` in the file).
5. Reports are used in order. A report never counts before every earlier report is out.

## Source, history, cost

- The CFTC public reporting API (`publicreporting.cftc.gov`, Socrata). No key, plain JSON.
  Datasets `72hh-3qpy` (disaggregated, futures only) and `gpe5-46if` (traders in financial
  futures, futures only).
- Kept from **January 2015**, so the 3-year percentile has a full window from 2018 on.
  618 weekly reports per market at the first run (to positions of 3 Nov 2026).
- `update()` asks the API only after a report's release time has passed, and then every 30
  minutes until the report appears. A normal week costs one request per market. All other calls
  make no request. Files: `data/sources/cot_<asset>.csv` and `data/sources/cot_state.json`.

## Limits

- Weekly and late: by the time a report is out, the positions are 3 days old, and up to 10 days
  old just before the next one.
- The E-mini alone is not the whole S&P futures complex. The big contract and the Micro E-mini
  are left out, as are options.
- The trader groups are the CFTC's classification. "Managed money" and "leveraged funds" are
  close relatives but not the same definition.
- A stored report is never revised, even when the CFTC later corrects a figure. The file keeps
  what the engine saw.
- It is a data point. Nothing here is claimed to predict price.
