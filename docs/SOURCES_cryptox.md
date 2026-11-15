# Batch 3 (crypto): what `engine15/sources/cryptox.py` reads

Written 15 Nov 2026 with the module, on the owner's approval of batch 3 (crypto): six reading-only decision cards for
BTCUSDT and ETHUSDT. **Built, not wired**: `cryptox` is not in `sources.MODULES`
(`tests/test_sources_cryptox.py::test_not_wired_yet`); the parent session wires it as think15-v5.2.2 after review.
Nothing here is claimed to predict anything; it does not vote until the card rating and the owner promote a card
(`research/CARD_PIPELINE.md`).

**Voices and features.** `optflow`, `kprem`, `cmegap`, `dom`, `spotlead`, `xfund` (none collides with an existing voice;
feature prefixes `of_ kp_ cg_ dm_ sl_ xf_`). Every feature is a float in [-1, 1], 0.0 = no read, never NaN; the RAW
columns carry the readable values (NaN = no read). `APPLIES` restricts every voice to BTCUSDT and ETHUSDT.

**Storage.** CSV under `data/sources/cx_<kind>[_<asset>].csv` (the Deribit card extends
`options_hourly_<asset>.csv`, the H40 file), written to a `.tmp` file and swapped in, **only ever extended**: a stored row
is never changed. No raw dumps are kept (Deribit trades are folded per hour as they arrive; klines and candles are kept
as the few columns used). `update()` fetches politely (a pause per host, back-off on 429 / 418 / 5xx with at least 30 s
after a rate-limit answer, a generic browser user agent, no keys, no accounts, nothing personal) and never raises;
`features()` reads files only (plus the project's own spot bars).

**The live loop.** It calls `update()` every 15 minutes. With the default folder each source is asked at most every
`MIN_GAP_S` (state in `data/sources/cryptox_state.json`) and each call is capped (`LIVE_MAX_REQ`: Deribit 6 hours, Upbit 10
requests, Binance perpetual 4, Bybit 12, OKX 20 per coin), so a long outage is caught up over several calls instead of
holding the loop. An explicit folder or `force=True` fetches everything without a cap (the backfill).

**When a value is known.** Every stored row has `known_ms`, publication lag included. A row first fetched within its
source's live window of its nominal time (a live fetch) is known at the later of the nominal time and the fetch time, so
a replay never knows more than a live run did. Readings are computed on each source's own gapless grid with backward
windows only, then joined to a 15m close as of `known_ms` (`flows._asof`), with a maximum age after which the reading is
"no read". A 15m candle from another venue is known one minute after its close, so the Korea premium and the spot vs perp
readings describe the bar BEFORE the decision's own bar, in the replay and live alike (the live loop fetches them a few
seconds after the close, too late for that close).

**Engine bars are spot.** `engine15.data.load` is Binance SPOT (`data-api.binance.vision` `/api/v3/klines`; checked 15 Nov
2026: the stored bar equals the spot kline exactly, the perpetual's volume is about 5 times larger). The spot vs perp
card therefore fetches the PERPETUAL and compares it with the project's own bars.

| Card (voice) | Source (file kind) | Endpoint | History start BTC / ETH | Grid | Known at | Max age | Throttle (live) |
|---|---|---|---|---|---|---|---|
| Options flow, Deribit (`optflow`) | every option trade (`options_hourly`) | `history.deribit.com/api/v2/public/get_last_trades_by_currency_and_time` | 1 Jan 2019 / 21 Mar 2019 (file; Deribit serves from 2016 / 2019) | 1 hour | hour end (live: fetch time) | 3 hours | 50 min, 6 hours a call |
| Korea premium (`kprem`) | Upbit 15m candles (`upbit`) | `api.upbit.com/v1/candles/minutes/15?market=KRW-BTC` | 1 Sep 2019 / 1 Sep 2019 | 15 min | close + 1 min | 1 hour | 10 min |
| | USD/KRW (`fx`) | `api.frankfurter.dev/v1/<from>..<to>?base=USD&symbols=KRW` (ECB reference rates, EUR crosses) | 31 May 2019 | ECB business day | D 17:00 Frankfurt | 5 days | 6 hours |
| CME gap, spot proxy (`cmegap`) | the project's own spot bars | none (CME session clock, `America/Chicago`) | CME launch weeks: 15 Dec 2017 / 5 Feb 2021 (bars from 2019) | 15 min | the bar close | n/a | n/a |
| BTC dominance (`dom`) | market caps (`caps`) | `community-api.coinmetrics.io/v4/timeseries/asset-metrics`, `CapMrktCurUSD`, 1d | 1 Jan 2019 (served from 2010 / 2015) | 1 day | D+1 06:00 UTC | 3 days | 6 hours |
| | stablecoins (`stables`) | `stablecoins.llama.fi/stablecoincharts/all` | 1 Jan 2019 (served from 29 Nov 2017) | 1 day | D+1 06:00 UTC | 3 days | 6 hours |
| Spot vs perp (`spotlead`) | Binance USDT-M perpetual (`perp`) | `fapi.binance.com/fapi/v1/klines?interval=15m` | 8 Sep 2019 17:45 / 27 Nov 2019 07:45 UTC | 15 min | close + 1 min | 1 hour | 10 min |
| Cross-exchange funding and OI (`xfund`) | Bybit funding (`bybit_fund`) | `api.bybit.com/v5/market/funding/history?category=linear` | 25 Mar 2020 / 21 Oct 2020 | settlement (8 h) | settlement + 1 min | 10 hours | 30 min |
| | Bybit open interest (`bybit_oi`) | `api.bybit.com/v5/market/open-interest?intervalTime=1h` | 20 Jul 2020 / 21 Oct 2020 | 1 hour | stamp + 1 h 5 min | 3 hours | 30 min |
| | OKX funding (`okx_fund`) | `www.okx.com/api/v5/public/funding-rate-history` | about 3 months back only (10 Aug 2026), then live | settlement (8 h) | settlement + 1 min | 10 hours | 30 min |
| | OKX open interest (`okx_oi`) | `www.okx.com/api/v5/rubik/stat/contracts/open-interest-history?period=1H` | about 60 days back only (16 Sep 2026), then live | 1 hour | stamp + 1 h 5 min | 3 hours | 30 min |
| | Binance funding | `data.load_funding` (the project's file, `fapi.binance.com/fapi/v1/fundingRate`) | Sep 2019 / Nov 2019 | settlement | settlement + 1 min | 10 hours | (the live loop's own) |

## 1. `optflow`: Options flow (Deribit)
- **What.** The H40 hourly aggregates (`sources/options_hist.py`, `docs/SOURCES_options_hist.md`): put / call notional,
  taker buys, block-trade flow, and amount-weighted trade IV in 25-delta put / call buckets (expiries 7-60 days).
- **Made live.** `options_hist.update(live=True)` resumes at the hour after the file's last row (not the next whole day)
  and stops at the last whole hour that ended 5 minutes ago; an hour first fetched within 6 hours of its end is known at
  the fetch time. The H40 seal (2025-11-11) applied to the H40 study only: `research/options_study.py` still drops every
  row known at or after it (`cutoff_ms`), so extending the file does not open the holdout to the study.
- **Features** (the registered H40 inputs, their H40 units, +-3 mapped to +-1): `of_pcr_7d` ln(put / call notional, 7
  days), `of_pcr_1d_z` (24 h ratio, z against the same hour over 90 days), `of_taker_bear_7d`, `of_rr25` (25-delta put
  minus call trade IV, 3 days), `of_rr25_chg7`, `of_block_bear_7d`. Raw: 24 h put / call notional, trade count, ATM IV,
  skew in vol points.
- **Weakness.** Trade IV, not a quoted surface; the skew is approximate (Black-Scholes delta from the trade's own IV).

## 2. `kprem`: Korea premium
- **What.** premium = Upbit close in KRW / (USD/KRW x Binance spot close) - 1, on each 15m bar both have; USD/KRW is the
  newest ECB reference rate known at the bar's close (via Frankfurter, an open, keyless service republishing the ECB's
  daily rates; the ECB's own data portal answered 503 on 15 Nov 2026 and FRED's H.10 rates are published weekly, too late
  for a live card). Binance prices are in USDT, treated as USD.
- **Features.** `kp_prem` (premium / 5%), `kp_z30` (z against the last 30 days of 15m premia, 10 days to speak, / 3),
  `kp_chg24` (change over 96 bars / 2 points). Raw: premium %, z, 24 h change, USD/KRW, Upbit price.
- **Weaknesses.** The ECB rate is fixed once a day at 14:10 CET, so intraday won moves (typically under 0.5%) show up as
  premium; weekends use Friday's rate. Upbit omits candles without trades (a missing bar is no read).

## 3. `cmegap`: CME gap (spot proxy)
- **Why a proxy.** No free, keyless, terms-compatible history of CME Bitcoin / Ether futures prices was found (checked 15
  Nov 2026): CME's own delayed quotes and settlements are behind terms that forbid automated access, Yahoo Finance and
  Barchart/Investing forbid scraping, Stooq now needs a key, Nasdaq Data Link needs an account. The CFTC publishes
  positions, not prices. **So the card as specified (CME futures prices) is dropped**, and what is built instead reads the
  same weekly event from the project's own spot bars: the CME close is spot at Friday 16:00 Chicago (Thursday when Friday
  is Good Friday) and the reopen is spot at Sunday 17:00 Chicago. The futures basis (front month, usually well under 1%)
  is ignored. Mid-week holiday halts are not modelled. The parent session can leave this voice out by deleting one
  GROUPS entry.
- **Gap.** reopen minus close, kept when at least 0.2% of price. It is unfilled until a later bar trades back to the
  CME close (low at or below it after a gap up, high at or above it after a gap down); partial fills are not tracked.
- **Features.** `cg_open` = while CME is shut, (close - CME close) / daily ATR(14), clipped; `cg_above` = proximity of the
  nearest unfilled gap level above (1 at the level, 0 at 3 daily ATRs or more); `cg_below` = the same below, negative.
  Raw: CME close, open move in ATRs, nearest levels above / below, distance in ATRs, age in days, number open.

## 4. `dom`: BTC dominance (tracked-market proxy)
- **What.** BTC share and stablecoin share of a tracked total = BTC + ETH + 12 long-listed coins on CoinMetrics' free tier
  (XRP, ADA, DOGE, LTC, BCH, LINK, XLM, ETC, XMR, ZEC, DASH, ALGO) + every stablecoin on DefiLlama. 7-day and 30-day
  changes compare like with like: an alt missing on either day is left out of both totals.
- **Why a proxy.** No free keyless source serves total-market-cap history: CoinGecko's `global/market_cap_chart` is
  paid-only and its free coin history stops at 365 days; CoinMarketCap needs a key; CoinPaprika / CoinCap history need
  keys. CoinMetrics' community tier does not serve SOL, BNB (after 2019), TRX, TON and others, so the tracked total is
  smaller than the whole market and the BTC share reads higher than CoinGecko's dominance (see the calibration below);
  its changes move with it.
- **Features.** `dm_btc_7d` (/ 2.5 points), `dm_btc_30d` (/ 5), `dm_stable_7d` (/ 1.5), `dm_stable_30d` (/ 3). Raw:
  BTC, ETH and stablecoin shares, the four changes in points. The same reading for both coins.

## 5. `spotlead`: Spot vs perp leadership
- **What.** Binance SPOT (the project's bars) against Binance USDT-M PERPETUAL 15m klines, on the bars both have.
- **Features.** `sl_share_z` = spot share of spot + perpetual base volume over 4 hours, z against 30 days (10 to speak),
  / 3; `sl_taker_diff` = (2 x taker buy / volume - 1) on spot minus the same on the perpetual, 4 hours, / 0.15;
  `sl_lead` = corr(spot return t-1, perp return t) minus corr(perp return t-1, spot return t) over the last 96 bars
  (positive: spot moved first), / 0.03. Raw: spot share %, z, both imbalances, lead, perpetual premium in basis points.
- **Weakness.** Real spot-perp lead/lag is sub-second; a 15-minute lag-one correlation is coarse and mostly small.

## 6. `xfund`: Cross-exchange funding and OI
- **What.** Binance (the project's file), Bybit and OKX USDT perpetual funding, each scaled to an 8-hour equivalent (an
  exchange that settles every 4 h or 1 h is scaled up); open interest from Bybit (hourly) and OKX (hourly).
- **Features.** `xf_avg` = (average across the venues with a read - 0.01%) / 0.04%; `xf_spread` = highest minus lowest
  (two venues or more) / 0.03%; `xf_bin_gap` = Binance minus the others' mean / 0.04%; `xf_oi_24h` = mean 24 h log change of
  open interest across Bybit and OKX / 0.10. Raw: each venue's rate, average, spread, gap, each venue's OI change, venues.
- **History.** Bybit funding from 25 Mar 2020 (BTC) / 21 Oct 2020 (ETH); Bybit hourly open interest from 20 Jul 2020
  (BTC) / 21 Oct 2020 (ETH); OKX's public API serves only about 3 months of funding and 60 days of hourly open interest, so before
  mid-Aug / mid-Sep 2026 the card reads two venues (funding) or one (open interest) and builds forward from here.

## History: does it reach 2021?
Every source reaches back before 1 Jan 2021 for both coins except OKX: its public API serves only about 3 months of
funding (from 10 Aug 2026) and 60 days of hourly open interest (from 16 Sep 2026), and no clean free archive was found
(the old `static.okx.com` trade-record paths answer 404). OKX is kept because it is still useful live: before those
dates the cross-exchange card simply reads Binance and Bybit (`xf_n_venues` says how many). Bybit funding starts 25 Mar
2020 (BTC) / 21 Oct 2020 (ETH), Bybit open interest 20 Jul 2020 / 21 Oct 2020; ETH's perpetual 27 Nov 2019; everything
else 2019 or earlier.

## Calibration and checks (15 Nov 2026)
- **Engine bars are spot**: the stored BTCUSDT bar for 11:15 UTC equals the spot kline (`data-api.binance.vision`) to
  the cent and volume (149.09 BTC); the perpetual's bar traded 742.3 BTC.
- **Dominance proxy vs CoinGecko**: on 13 Nov 2026 BTC was 66.1% of the tracked total ($2.07T) and stablecoins 14.0%
  ($290B); CoinGecko's live `/global` said BTC 59.4% of $2.21T (USDT 7.9%, USDC 3.1%). The proxy reads about 6-7 points
  higher on BTC; use its changes, not its level, against public dominance figures.
- **Units** were set from each reading's own spread on 2020-2026 BTC history (about its 95th percentile of |input|),
  a scale only, never fitted to an outcome. The spot-perp lag-one lead is small (median |lead| 0.006, 95th
  percentile 0.026), as expected at 15 minutes.
- **Speed**: `features()` over BTC's full history (275,782 bars, 2019 to now) takes about 4 s (2.5 s with the files
  cached by modification time).
- **Live windows** (a row first fetched within this long of its nominal time is known at the fetch time): 15m candles,
  funding and open interest 1 day; ECB rates 1 day (never revised); CoinMetrics and DefiLlama days 7 days (as
  `flows.py`: providers revise recent days); Deribit hours 6 hours. So right after a backfill the newest stretch of each
  reading is "no read" in the replay; live it reads from the next closes on.
