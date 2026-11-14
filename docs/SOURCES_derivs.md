# Derivatives and clock sources: what `engine15/sources/derivs.py` reads

Written 2026-11-10 with the module. Five decision cards: data points for the engine's decisions and
for post-mortems. Nothing here is claimed to predict anything, and none of it was tested for that.

**Storage.** CSV under `data/sources/`, `ts_ms` first, written to a `.tmp` file and swapped in, only
ever extended: `update()` asks each endpoint for rows newer than its file (0.35 s between requests,
30 s timeout); a failed source keeps its file and returns `failed: <reason>`. `features()` reads the
files and the project's 15m bars, never the network. A feature is 0.0 on no read; raw columns are NaN.

**When a value is known.** Row i may use only what was known at the close of 15m bar i. Every
stored row has a known-at time; it goes to the first 15m close at or after it and becomes "no read"
once older than the source's maximum age. Rolling figures look backward on the source's own gapless
grid. `tests/test_sources_derivs.py` checks it by cutting the index and by rewriting what was not yet known.

## 1. `basis`: Perp basis and premium
- **Endpoint.** Binance `fapi/v1/premiumIndexKlines`, 15m. The premium index is how far the USDT
  perpetual trades from its spot index; funding is set from it. File `basis_<asset>.csv`.
- **History.** From 24 Dec 2019 03:15 UTC: 241,282 bars a coin at the first fetch, 3 gaps.
- **Readings.** `pb_level`: the last hour's average of the bar-close premium, divided by 0.05% (the
  yardstick `evidence.py` already uses for funding), clipped to 3. `pb_z`: that level against its own
  mean and deviation over the last 30 days (silent until 7 days exist), clipped to 3. `pb_chg_4h`:
  the level now minus the level 4 hours ago, in the 0.05% unit. Raw: `pb_premium_pct`.
- **Known.** At the premium bar's close, the same instant as the price bar's. Maximum age 1 hour.
- **Weaknesses.** One venue. A bar's close is one sample, hence the hourly average. Overlaps the funding card.

## 2. `lsratio`: Long/short positioning
- **Endpoints.** Binance `futures/data/globalLongShortAccountRatio` (all accounts, by head count),
  `topLongShortPositionRatio` (the largest accounts, by position size), `takerlongshortRatio` (taker
  buy volume over sell volume), `period=15m`. File `lsratio_<asset>.csv`.
- **History.** Binance serves only the last 30 days: on disk from 11 Oct 2026 14:45 UTC (2,877
  rows a coin). `update()` extends it forever; a gap of over 30 days between updates cannot be refilled.
- **Readings.** `ls_global`, `ls_top`: natural log of the long/short ratio (0 = balanced, positive =
  more long), clipped to 3. `ls_global_24h`, `ls_top_24h`: the change in that log over 24 hours,
  divided by 0.25 (about a 28% change in the ratio). `ls_taker`: log of the last hour's taker buy
  over sell volume, divided by 0.20; `ls_taker_24h`: its change over 24 hours, same unit.
  Raw: `ls_global_ratio`, `ls_top_ratio`, `ls_taker_ratio`.
- **Known.** Binance publishes these late. Measured once, 10 Nov 2026: the taker bar appeared 57 s
  after its period ended, the snapshots 156 to 164 s after their stamp; the live loop steps 75 s
  after a close and would not have them. So `STATS_LAG_MS` (5 minutes; any value up to 15 has the
  same effect) is added to every stamp: **the statistics of bar i reach row i+1**, in replay and
  live alike. Maximum age 1 hour.
- **Weaknesses.** One venue. Account ratios count heads, not money. One bar late. One delay measurement.

## 3. `liq`: Liquidation pressure (proxy)
- **Not a liquidation feed.** No free REST history of liquidations exists and this project may not
  install a websocket library, so the card infers them from Binance `futures/data/openInterestHist`
  (`period=15m`; open interest in coins, so price alone does not move it). File `liq_oi_<asset>.csv`.
- **History.** 30 days served, then what `update()` accumulates: from 11 Oct 2026 15:00 UTC (2,876 rows).
- **Readings.** For each bar: the log change in open interest between the snapshots at its open and
  its close, and the bar's log return (the project's spot bars), each in standard deviations of the
  **prior** 7 days (silent until 1 day exists). An event needs an open-interest drop of at least
  2 sigma inside a bar of at least 2 sigma. `lq_bar` = sign of the bar x sqrt(drop x size) / 2,
  clipped to 3: 1.0 is an event exactly at both thresholds; negative = down bar (longs closed out),
  positive = up bar (shorts); otherwise 0. `lq_4h`: the sum of the last 16 bars' events (needs 8),
  clipped to 3. Raw: `lq_oi`, `lq_oi_chg_pct`, `lq_bar_sigma`.
- **Known.** As source 2: the snapshot at a bar's close is published about 160 s later, so
  **row i carries the proxy of bar i-1**. `lq_bar` uses only that bar; `lq_4h` may be 1 hour old.
- **Weaknesses.** Open interest also falls when traders close by choice, and new positions in the
  same bar can hide a liquidation: the proxy over- and under-counts. Spot price against perpetual
  open interest. 0.0 means both "no event" and "no read"; `lq_oi` (NaN on no read) tells them apart.

## 4. `options`: Options: implied volatility and skew
- **Endpoints.** Deribit `public/get_volatility_index_data` (`resolution=3600`): DVOL, the 30-day
  implied volatility index, annualised %, hourly; file `options_dvol_<asset>.csv`. Live only:
  `public/get_book_summary_by_currency?kind=option`, one row a run in `options_live_<asset>.csv`.
- **History.** DVOL from 24 Mar 2021 00:00 UTC, BTC and ETH: 49,381 hours each, no gaps. The live
  reads start 10 Nov 2026 13:53 UTC and have no past.
- **Readings.** `op_dvol_rank`: where the DVOL close sits between its lowest and highest hourly
  close of the last 90 days (silent until 30 days exist): -1 at the low, +1 at the high.
  `op_dvol_24h`: log change of DVOL over 24 hours, divided by 0.10. `op_iv_rv`: DVOL minus realised
  volatility, divided by 20 points; realised = root mean square of the project's 15m log returns
  over 30 days (needs 7) x sqrt(96 x 365) x 100, the 365-day annualisation DVOL uses. Live only:
  `op_pcr` = log(put / call open interest, all expiries) / 0.5; `op_skew` = (implied volatility 10%
  below the forward, from puts, minus 10% above it, from calls) / 10 points, on the expiry nearest
  30 days out (between 7 and 60). Raw: `op_dvol`, `op_rv`, `op_pc_ratio`, `op_skew_pts`.
- **Known.** A DVOL hour from the end of its hour (maximum age 3 hours). A live read from the PC
  clock time it was fetched, for at most 24 hours (it depends on how often `update()` runs).
- **Weaknesses.** One venue. Realised looks back 30 days while DVOL looks forward 30. The skew is at
  fixed 10% moneyness, not fixed delta, so it moves with the volatility level and jumps when the
  chosen expiry rolls. The put/call ratio sums coins of open interest over every strike and expiry.

## 5. `clock`: Time and session
- **Readings** (no network, no file; read at the bar's **close**, when the engine decides).
  `ck_hour_sin`, `ck_hour_cos`: the UTC hour as an angle. `ck_dow_sin`, `ck_dow_cos`: the position in
  the UTC week (Monday 00:00 = 0). `ck_weekend`: 1 on a UTC Saturday or Sunday. `ck_asia`,
  `ck_europe`, `ck_us`: +1 while that cash session is open, else -1: Tokyo 09:00 to 15:00, London
  08:00 to 16:30, New York 09:30 to 16:00, local time, Monday to Friday, daylight saving followed.
  `ck_us_open_in`: hours to the next New York 09:30 / 24, capped at 1. Raw: `ck_us_open_hours`.
- **Weaknesses.** Holidays and half days are not modelled; Tokyo's lunch break and its later close
  since November 2024 are ignored. A 0.0 here is a value, not "no read".

## Constants
All sit at the top of `derivs.py` with their reasons: the windows repeat the brief (30-day z-score,
90-day range, 4h and 24h changes); the units (0.05%, 0.25, 0.20, 10%, 20 points, 0.5, 10 points) are
round numbers meant to keep a typical reading inside its clip. They were declared before the history
was fetched and none was changed after. What the first fetch showed (BTC, share of non-zero
readings at the clip): `ls_taker_24h` 10%, `lq_4h` 22%, `lq_bar` 7%, every other one under 3%.
