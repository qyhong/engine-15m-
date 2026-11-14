# Positioning and on-chain flow sources: what `engine15/sources/flows.py` reads

Written 13 Nov 2026 with the module, for hypothesis H39 (`research/HYPOTHESES.md`). Data points for research and,
later, possibly for the engine. Nothing here is claimed to predict anything; the H39 study
(`research/out/flows/study.md`) is the only test of that, on development data.

**Wired into the live engine from think15-v5.1.1 (13 Nov 2026, owner's "Yes").** `flows` is in `sources.MODULES`, its
four cards apply to BTC and ETH only (`APPLIES`, and `evidence.CRYPTO_ONLY_SOURCES`), and the live step's call to
`update()` asks each source at most every `MIN_GAP_S` (metrics 1 h, Bitfinex 50 min, CFTC 6 h, CoinMetrics 2 h; last
attempts in `data/sources/flows_state.json`). `tests/test_sources_flows.py::test_wired_crypto_only_and_throttled`.
Not an RL input.

**Storage.** CSV under `data/sources/flows_<kind>_<asset>.csv`, written to a `.tmp` file and swapped in, **only ever
extended**: a stored row is never changed; a later fetch only adds rows with new stamps. (Unlike `derivs.py`, which lets a
re-fetched row replace an old one: here providers revise history, and the first value seen is the point-in-time one.)
The Binance archive zips are kept as downloaded under `data/raw/binance_metrics/<SYMBOL>/` (about 12 KB a day a coin) and
are only ever read as CSV text; days the archive answered 404 for are listed in `_not_in_archive.txt` there.
`update()` fetches (polite: a pause per host, back-off on 429 / 5xx, at least 65 s after a rate-limit answer, a generic
browser user agent with nothing personal, no keys, no accounts); `features()` and `inputs()` read files only.

**When a value is known.** Every stored row has an explicit `known_ms`, publication lag included (table below). A row
first fetched within 7 days of its nominal time (a live fetch, not the backfill) is known at the later of the nominal
time and the moment it was fetched, so a replay never knows more than a live run did. Readings are computed on each
source's own gapless grid with backward windows, then joined to a 15m row (or any decision instant) as of `known_ms`,
with a maximum age after which the reading is "no read" (0.0; raw columns NaN). `inputs(close_ms, asset, cutoff_ms=...)`
returns the unclipped transforms H39 tests; `cutoff_ms` drops every row known at or after it before anything is computed
(the study passes the holdout seal).

| Source (file kind) | Endpoint | History (BTC / ETH) | Grid stored | Known at | Max age |
|---|---|---|---|---|---|
| Binance archive positioning (`metrics`) | `data.binance.vision/data/futures/um/daily/metrics/<SYM>/<SYM>-metrics-<day>.zip` | 1 Sep 2020 / 1 Dec 2021 | 15 min | day D's rows: D+1 00:00 UTC + 12 h | 3 days |
| Bitfinex margin positions (`bitfinex`) | `api-pub.bitfinex.com/v2/stats1/pos.size:1h:t<COIN>USD:{long,short}/hist` | 22 Feb 2021 / 22 Feb 2021 | 1 hour | stamp + 1 h 5 min | 6 hours |
| CME futures positioning, CFTC (`cme`) | `publicreporting.cftc.gov/resource/gpe5-46if.json` (traders in financial futures, futures only), codes 133741 / 146021 | 10 Apr 2018 / 6 Apr 2021 | weekly report | release: Friday 15:30 New York, with `cot.py`'s holiday rule and catch-up overrides | 15 days |
| On-chain, CoinMetrics community (`onchain`) | `community-api.coinmetrics.io/v4/timeseries/asset-metrics`, `frequency=1d`, no key | 2015 (MVRV from 2010) / Jul 2015 | 1 day | day D: D+1 00:00 UTC + 6 h | 3 days |

Measured lags (11-13 Nov 2026): Binance archive files for 10, 11, 12 Nov appeared at 06:34, 08:19 and 06:42 UTC the
next day; CoinMetrics flash values for 7-12 Nov were computed 01:15-03:20 UTC the next day; the Bitfinex hourly value
equals its 1-minute value AT the stamp (so 1 h 5 min is conservative); CFTC as `docs/SOURCES_cot.md`.

## 1. `metrics`: Binance USDT-M positioning (archive)
- **What.** One CSV a day of 5-minute rows: `sum_open_interest` (coins), `sum_open_interest_value` (USDT),
  `count_toptrader_long_short_ratio` (top traders by accounts), `sum_toptrader_long_short_ratio` (top traders by
  position), `count_long_short_ratio` (all accounts), `sum_taker_long_short_vol_ratio` (taker buy / sell volume).
  Stored at 15 minutes: the snapshot AT :00/:15/:30/:45 for open interest and the ratios, the geometric mean of the three
  5-minute taker ratios in [stamp, stamp + 15 min) for the taker ratio. Columns `oi, oi_value, top_acct_ls, top_pos_ls,
  global_ls, taker_ls, known_ms`.
- **Same series as the live API.** Checked against `derivs.py`'s files from `futures/data/*` (15m, 11 Oct - 12 Nov
  2026): the archive row created at T is the API row stamped T + 5 min. BTC: account and top-trader position ratios
  identical (within 0.03%) in all 3,109 overlapping rows, open interest identical in 99%; on 8-12 Nov the taker ratio
  correlates 0.95 (its periods are cut differently). Top-trader ratios are missing for about 30,000 of BTC's early rows. So the archive
  extends `derivs.py`'s 30-day positioning back to 2020 / 2021 with the same meaning.
- **Readings.** `fl_oi_7d` = 7-day log change of the day's last open interest / 0.10. `fl_ls_global_z` = ln(account
  long/short), day mean, z against 90 days (30 to speak). `fl_ls_topgap_z` = ln(top-trader position long/short) minus
  ln(account long/short), day mean, z against 90 days. A day needs 48 of its 96 rows. Raw `fl_oi`, `fl_global_ls`,
  `fl_top_pos_ls`.
- **Weaknesses.** One venue. ETH starts Dec 2021 (about 4 development years). The archive files were regenerated by
  Binance (Last-Modified March 2026 on 2020-21 files), so the history is Binance's current view of it. The 12-hour lag
  makes a daily reading about a day older than the live API's: the engine's live 15m positioning stays in `derivs.py`.

## 2. `bitfinex`: Bitfinex margin longs and shorts
- **What.** Total margin position size, long and short, in coins (tBTCUSD, tETHUSD), hourly snapshots; 1-minute data
  goes back to Nov 2016 but is not fetched (hours from Feb 2021 cost ~12 requests a coin; minutes would cost hundreds).
- **Reading.** `fl_bfx_14d` = 14-day change of ln(longs / shorts) / 0.25. Raw `fl_bfx_long`, `fl_bfx_short`.
- **Weaknesses.** One venue's margin book, dominated by a few large accounts; shorts are small and jumpy, so the ratio
  moves mostly with shorts. 5 gaps of up to 8 hours since 2021.

## 3. `cme`: CME Bitcoin and Ether futures positioning (CFTC)
- **What.** Weekly Commitments of Traders, traders in financial futures, futures only: open interest and the long and
  short positions of leveraged funds, asset managers and dealers. CME Bitcoin (5 BTC contract, code 133741) from Apr 2018,
  CME Ether (146021) from Apr 2021. Micro contracts are not included.
- **Reading.** `fl_cme_lev_z` = leveraged-funds net as % of open interest, z against the trailing 52 reports (26 to
  speak). Raw `fl_cme_lev_net_pct`, `fl_cme_am_net_pct` (asset managers).
- **Weaknesses.** Weekly, positions as of Tuesday published Friday: three days old when published. Leveraged funds'
  short side is largely the short leg of cash-and-carry (long spot or ETF, short CME), so "net short" is not a bearish
  bet; the direction of this reading is ambiguous.

## 4. `onchain`: CoinMetrics community, daily
- **What.** `CapMVRVCur` (market value / realised value), `AdrActCnt` (active addresses), `FlowInExNtv` /
  `FlowOutExNtv` (coins into / out of tagged exchange addresses), `SplyExNtv` (coins on exchanges), `HashRate`,
  `IssTotUSD` (new issuance in US$), `TxCnt`, `CapMrktCurUSD`. Several others (realised cap, fees, NVT, supply-age
  metrics) are refused to the community tier (HTTP 403).
- **Readings.** `fl_mvrv_z` = ln(MVRV) z against 365 days (180 to speak). `fl_netflow_7d` = 7-day sum of (inflow -
  outflow) / exchange supply / 0.005. `fl_addr` = ln(30-day mean / 365-day mean of active addresses) / 0.20.
  `fl_hash_ribbon` = ln(30-day / 60-day mean of BTC's hash rate) / 0.05, BTC's for both coins (ETH has had no
  proof-of-work since Sep 2022). Raw `fl_mvrv`, `fl_exch_supply`, `fl_addr_act`, `fl_hashrate_btc`.
- **Weaknesses.** **Exchange flows are revised backwards** as CoinMetrics tags more exchange addresses: the 2022 values
  carry a status time of April 2026. The stored history is therefore today's view of the past (a look-ahead that cannot
  be removed for the backfill; from the first fetch on, a stored row is never changed). Values are "flash" (first
  estimate) for recent days. MVRV, addresses, hash rate are computed from the chain and the price and are revised far less.
- **Terms.** CoinMetrics community data is free for non-commercial use with attribution (Creative Commons BY-NC, as
  stated by CoinMetrics; re-check before any commercial use). Rate limit 10 requests per 6 seconds per IP.

## Running it
`flows.update()` (or `update(sources=[...], assets=[...])`). The first run downloaded about 4,070 archive zips (about
50 MB, roughly 50 minutes at 0.3 s between requests) plus ~30 API requests; a later run fetches only the days and hours
since its files' last rows. Nothing schedules it: no live process calls it.

## Wiring it in (done 13 Nov 2026 as think15-v5.1.1; steps 1-3 below, step 4 not done)
1. Add `"flows"` to `MODULES` in `engine15/sources/__init__.py` (evidence.py then calls `features()` and `describe()`),
   and add `flows.update()` to whatever runs the other sources' updates, at least daily (the archive and CoinMetrics
   publish once a day; Bitfinex hourly readings go silent after 6 hours without an update).
2. That changes the evidence the engine reads: bump `version` in `engine15/config.py` and say so in the journal.
3. `tests/test_engine.py::test_evidence_never_reads_the_future` must stay green, and
   `test_not_wired_into_the_live_engine` in `tests/test_sources_flows.py` must be updated in the same change.
4. For the RL loop, an input would go through `engine15/rl/features4.py`'s availability flags (most of these start in
   2020-21, so earlier folds would see them as unavailable), and only in a registered round.
