# Market sources: five decision cards

Module `engine15/sources/market.py`, files under `data/sources/`, built 10 Nov 2026. Data points
for the engine's decisions and post-mortems; nothing here says a reading predicts anything.

## The one rule: known at the 15-minute close
A 15m row may use only what was known when its bar closed (open + 15 min).

| Kind of value | Stamp | Used from |
|---|---|---|
| Hourly bar | the hour's open, H | H + 1 hour (the hour's end) |
| Daily value | UTC day D | 00:00 UTC of D + 1 |
| ETF flow | US trading date D | 12:00 UTC of D + 1 |

Every reading is computed on its source's own grid with backward-looking windows, then joined
to the 15m rows on the time it became known. A value that is too old becomes "no read" (0.0):
6 hours for hourly readings, 3 days for daily ones, 6 days for ETF flows (a long weekend is 4).
`tests/test_sources_market.py` checks it three ways: cutting the index, changing every source
row that ends after a cut, and planting one value per source to find the exact first row.
Features are dimensionless and clipped; the raw columns (for the journal) may be NaN. A source
that fails in `update()` keeps its old file and reports `failed: <reason>`.

## 1. Spot ETF flows (`etf`)
- **Endpoint:** Farside Investors' tables, `farside.co.uk/bitcoin-etf-flow-all-data/` and
  `/ethereum-etf-flow-all-data/` (fallback: `/btc/`, `/eth/`). HTML, parsed with a regex.
- **History:** Bitcoin from 11 Jan 2024, Ether from 23 Jul 2024, one row per US trading day, net
  flow of all funds in US$ million. `etf_btc.csv`, `etf_eth.csv`: `date, net_musd, n_funds`.
- **Readings** (the coin's own ETFs: BTC flows for BTCUSDT, Ether flows for ETHUSDT):
  `etf_1d` = last day's net flow / standard deviation of the last 30 trading days' flows;
  `etf_5d` = five-day sum / (that deviation x sqrt 5). Both clipped to +/-3. Needs 10 days to start.
- **Known:** 12:00 UTC the day after the trading date. Issuers report through the US evening, so
  00:00 UTC could show history a total live did not have yet. The 12 hours are chosen, not measured.
- **Weaknesses:** a web page, not an API: a layout change or a block stops it (the card goes silent
  after 6 days). Farside revises recent rows: the last 7 days on disk are refreshed on each fetch,
  older rows are frozen. A day where no fund has a number (holiday, not yet published) is not
  stored; `n_funds` counts the funds that had a number. No read before 2024.

## 2. Stablecoin supply (`stable`)
- **Endpoint:** DefiLlama `https://stablecoins.llama.fi/stablecoincharts/all`.
- **History:** daily from 29 Nov 2017. `stablecoins.csv`: `date, total_usd, usd_pegged`
  (`total_usd` = US$ value of all pegs; `usd_pegged` = the USD-pegged part, kept for reading).
- **Readings:** `stb_7d`, `stb_30d` = the % change in total supply over 7 / 30 days, divided by
  the root mean square of that same change over the past 365 days (90 to start), clipped to
  +/-3. Scaled by itself so that no hand-picked "big move" number is needed.
- **Known:** 00:00 UTC of the day after the stamp. Today's point is never stored (it still moves).
- **Weaknesses:** DefiLlama rewrites history when it adds or corrects a coin, so everything
  fetched on the first day (10 Nov 2026) is today's view of the past, not what was published
  then; from then on a stored date is never changed. The early series has one-day steps (+47% on
  5 Jan 2019, +26% on 3 Jan 2020, +37% on 3 Apr 2020) that look like coins entering the data.

## 3. Coinbase premium (`cbprem`)
- **Endpoint:** Coinbase Exchange public candles, `api.exchange.coinbase.com/products/BTC-USD/candles`
  (and `ETH-USD`), hourly, 300 per request, 0.35 s between requests.
- **History:** from 1 Jan 2019. `coinbase_btcusd_1h.csv`, `coinbase_ethusd_1h.csv`: `ts_ms, close`.
- **Premium:** Coinbase hourly close / Binance hourly close - 1. The Binance close is the close of
  this project's 15m bar that opens at H + 45 min; if that bar is missing the hour has no premium.
- **Readings:** `cbp_z` = premium against the mean and deviation of its last 30 days (720 hours,
  168 to start); `cbp_24h` = 24-hour mean premium in units of 0.1% (10 basis points, a round
  number); `cbp_d4h` = premium now minus 4 hours ago, divided by the 30-day deviation of that
  4-hour change. All clipped to +/-3. **Known:** at the end of the hour.
- **Weaknesses:** it compares BTC-USD with BTC-USDT, so it contains the USDT/USD rate: a tether
  wobble looks like a premium (2019: the hourly gap's deviation was 57 basis points, 5-10 since
  2021). Coinbase has no BTC candle for 19 hours since 2019. The two closes are last trades
  within the same hour, not the same instant.

## 4. Market breadth and ETH/BTC (`breadth`)
- **Endpoint:** Binance spot hourly klines, `data-api.binance.vision/api/v3/klines`, 1000 per
  request, for SOL, BNB, XRP, ADA, DOGE, LINK, AVAX, LTC, DOT, TRX against USDT.
- **History:** from 1 Jan 2019 or the coin's listing. `binance_<coin>usdt_1h.csv`: `ts_ms, close`.
  ETH/BTC comes from this project's own 15m bars, not from a file here.
- **Readings:** `brd_above_24h`, `_7d`, `_30d` = share of the coins whose close is above their own
  24h / 7d / 30d simple average, as 2 x share - 1 (-1..+1). A coin counts once 90% of its window
  exists, so a coin not yet listed does not count; fewer than 3 coins = no read. `brd_rel_24h` =
  the coins' mean 24h log return minus BTC's, divided by BTC's daily volatility (std of hourly log
  returns over 30 days x sqrt 24). `brd_ethbtc_1d`, `_7d` = log change of ETH/BTC over 24 / 168
  hours, divided by the ratio's hourly volatility over 30 days x sqrt of the hours. The last three
  are clipped to +/-3. The same values for both coins. **Known:** at the end of the hour.
- **Weaknesses:** the ten coins were chosen in 2026: coins that died are absent (survivorship).
  5 or 6 coins in early 2019, all 10 from Oct 2020. Equal weight: TRX counts as much as SOL. A zero on
  `brd_above_*` can be a real 50% as well as "no read"; the raw `brd_n` tells them apart.

## 5. Fear and Greed (`sentiment`)
- **Endpoint:** `https://api.alternative.me/fng/?limit=0`.
- **History:** daily from 1 Feb 2018 (two gaps, of 1 and 3 days). `fear_greed.csv`: `date, value`.
- **Readings:** `fng_level` = (value - 50) / 50 (-1..+1); `fng_7d` = value minus the value 7 days
  earlier, in units of 25 points (a quarter of the scale), clipped to +/-3; `fng_extreme` = -1
  at 20 or under, +1 at 80 or over, else 0.
- **Known:** 00:00 UTC of the day after the stamp. That is probably a day later than needed: on
  10 Nov 2026 the site already showed the value stamped 10 Nov, next update due at 00:00 UTC. The
  rule for daily values was applied as written; `FNG_LAG_MS` is the constant to change.
- **Weaknesses:** one site's composite, partly built from BTC's own volatility and momentum.
  `fng_level` = 0.0 is a real reading at 50, not only "no read"; the raw `fng_value` tells them apart.

## Running it
`market.update()` fetches everything: hourly files only the hours since their last row, daily
sources at most once every 3 hours. The first run took 9 minutes (about 460 Coinbase and 700
Binance requests); a later one takes seconds. For the hourly cards to read live it must run at
least every few hours (6-hour limit). `features()` reads only files (about 1 s for the full
history). Constants sit at the top of the module; all were set before any data was seen.
