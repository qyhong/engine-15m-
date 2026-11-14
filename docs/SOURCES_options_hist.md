# Deribit option trade history: what `engine15/sources/options_hist.py` reads

Written 14 Nov 2026 with the module, for hypothesis H40 (`research/HYPOTHESES.md`). Data points for research.
Nothing here is claimed to predict anything; the H40 study (`research/out/options/study.md`) is the only test of that,
on development data.

**NOT wired into the live engine.** `options_hist` is not in `sources.MODULES`, and no other file under `engine15/`
names it (`tests/test_sources_options_hist.py::test_not_wired_into_the_live_engine`). Wiring it in would be a separate,
versioned, owner-approved step (see the end of this page). Not an RL input.

## Source

`https://history.deribit.com/api/v2/public/get_last_trades_by_currency_and_time`, `currency` = BTC or ETH,
`kind=option`, `sorting=asc`, `count=1000` (the documented maximum), `start_timestamp` / `end_timestamp` in ms. Public:
no key, no account. Each trade carries `trade_id`, `timestamp`, `instrument_name` (`BTC-25MAR22-50000-P`), `amount`
(coins: one Deribit inverse option is one coin), `price` (in coin), `index_price`, `mark_price`, `iv` (trade implied
volatility, %), `direction` (the taker's side), and, when it was a block trade, `block_trade_id`; newer trades also carry
`combo_id`, `contracts`, `liquidation`. Only inverse options under BTC and ETH; USDC-settled linear options are not in
these currencies and are not read.

**Earliest trade served (probed 14 Nov 2026):** BTC 2016-11-29 08:23 UTC (`BTC-31MAR17-700-P`), ETH 2019-03-21 13:10
UTC (`ETH-28JUN19-170-C`). The stored history starts 2019-01-01 (BTC) and 2019-03-21 (ETH), because the development bars
start 2019-09-08 and nothing earlier is needed. For H40 the fetch stopped at 2025-11-11 00:00 UTC (the holdout seal):
no holdout trade was downloaded.

**Volume (measured over the stored history):** mean trades a day, BTC 1,185 (2019), 3,619 (2020), 8,036 (2021), 8,119
(2022), 9,764 (2023), 13,819 (2024), 14,640 (2025 to the seal); ETH 266, 1,214, 5,378, 9,280, 7,959, 8,444, 9,316. In all
20.9 million BTC and 14.8 million ETH option trades (276,102 and 161,398 of them block-trade prints), none unreadable,
no day without trades, no page-boundary millisecond with more than 1,000 trades. About 22,000 BTC and 16,000 ETH requests.
Stored: 60,144 BTC and 58,248 ETH hourly rows, 15.0 MB and 12.7 MB.

## Storage

`data/sources/options_hourly_<asset>.csv`, one row per UTC hour (`ts_ms` = hour start), written to a `.tmp` file and
swapped in, **only ever extended** (a stored hour is never changed; CSVs are read with exact float round-trip so a
re-written stored row stays bit-identical). Raw trade pages are never kept: each day's trades are folded into 24 hourly
rows in memory, and an hour without trades is a row of zeros, so the file is a gapless grid. `update()` resumes from the
day after the file's last row; at most `FLUSH_DAYS` (7) unflushed days are repeated after an interruption.

| Column | Meaning |
|---|---|
| `n`, `n_put`, `n_call` | trades in the hour |
| `put_usd`, `call_usd` | notional, sum of amount x index price (US$) |
| `put_buy_usd`, `call_buy_usd` | notional where the taker bought (sells = total - buys) |
| `prem_put_usd`, `prem_call_usd` | premium, price x amount x index price (US$) |
| `blk_n`, `blk_{put,call}_{buy,sell}_usd` | block trades: count and notional by taker side |
| `rr_put_ivw`, `rr_put_w`, `rr_put_n` | puts with abs(delta) in [0.15, 0.35] and 7-60 days to expiry: sum of iv x amount, sum of amount, count |
| `rr_call_ivw`, `rr_call_w`, `rr_call_n` | the same for calls with delta in [0.15, 0.35] |
| `atm_ivw`, `atm_w` | abs(delta) in [0.40, 0.60], 7-60 days: sum of iv x amount, sum of amount |
| `skipped` | trades that could not be read (unknown instrument name, zero amount or index) |
| `known_ms` | hour end: trades are public the moment they print, so the hour is known when it ends |

**Delta** is Black-Scholes with the trade's own IV, the strike, the time to expiry (08:00 UTC on the expiry date) and the
index price as the underlying, zero rates. The forward is approximated by the index (the futures basis is ignored), so the
buckets are approximate; the 25-delta skew built from them is a trade-weighted approximation of a risk reversal, not a
fitted surface, and its mix of strikes and expiries changes with what traded.

**Polite fetching.** One process waits `PAUSE_S` (0.6 s) after each answer before the next request (so at most about
one request a second per process); back-off 2, 4, 8, 16, 32 s on 429 / 5xx / network errors, at least 30 s after a 429;
generic browser user agent with nothing personal. For the H40 backfill at most four processes ran at once on disjoint
date ranges (later ranges written to a scratch folder and appended afterwards, each checked contiguous and the stored rows
unchanged), about 3-4 requests a second in total; the backfill took about 4 hours (14 Nov 2026). The first minutes of an
earlier start were discarded and refetched after the CSV reader was switched to exact float round-trip.

## Readings (H40's registered transforms; `inputs(close_ms, asset, cutoff_ms=...)`)

Computed on the gapless hourly grid with backward windows, then joined as of `known_ms` (the same `_asof` as
`flows.py`), maximum age 3 hours. A window with a missing hour is NaN. `cutoff_ms` drops every row known at or after it
before anything is computed.

| Input | Definition | Risk-off side (H40) | Feature unit |
|---|---|---|---|
| `op_pcr_7d` | ln(put notional / call notional), 168 hours | HIGH | 0.25 |
| `op_pcr_1d_z90` | ln(put / call notional) over 24 hours, z against the same hour's trailing 90 daily values (30 to speak) | HIGH | 1 |
| `op_taker_bear_7d` | [(put buys - put sells) - (call buys - call sells)] / total notional, 168 hours | HIGH | 0.10 |
| `op_rr25` | amount-weighted IV of 25-delta puts minus 25-delta calls, 7-60 day expiries, 72 hours, vol points (10 trades a side to speak) | HIGH | 5 |
| `op_rr25_chg7` | `op_rr25` minus its value 168 hours earlier | HIGH | 3 |
| `op_block_bear_7d` | the taker measure on block trades only / block notional, 168 hours (5 block trades to speak) | HIGH | 0.20 |

Raw columns: `op_put_usd_24h`, `op_call_usd_24h`, `op_trades_24h`, `op_atm_iv` (24-hour amount-weighted at-the-money
trade IV). `features()` returns the inputs clipped to +-3 units (0.0 = no read) for the same interface as the other
source modules; `describe()` gives one plain sentence.

## Weaknesses

- One venue (Deribit), though it carried most crypto option volume over 2019-2025. No open interest (not in trade
  history), so put/call is a volume ratio, not a positioning ratio.
- Trade IVs are noisy, and the bucket mix changes with what traded; the 72-hour window and amount weights smooth it.
- Taker side (`direction`) is the aggressor of the print; for block trades and combo legs it is the side of the
  initiating party as Deribit reports it, which is not always the economic direction of a multi-leg structure.
- Block trades were rare before about 2021, so `op_block_bear_7d` speaks less in early years.
- If more than 1,000 trades shared one millisecond, the pager steps past it and those beyond 1,000 are lost; such events
  are counted (`hourly_<ASSET>_stuck_ms` in `update()`'s result) and reported.

## Running it

`py -3 -m engine15.sources.options_hist BTCUSDT [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--max-days N] [--src DIR]`,
or `options_hist.update(assets=[...], end_ms=...)`. Nothing schedules it: no live process calls it.

## Wiring it in (NOT done; needs the owner's approval)

1. Add `"options_hist"` to `MODULES` in `engine15/sources/__init__.py` and call `update()` at least hourly (the readings
   go silent after 3 hours without new rows); bump `version` in `engine15/config.py` and say so in the journal.
2. `tests/test_engine.py::test_evidence_never_reads_the_future` must stay green, and
   `test_not_wired_into_the_live_engine` must be changed in the same step.
