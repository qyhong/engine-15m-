# Paid / free data survey for sell-off tests (BTC, ETH)

All pages read on 2026-11-14 (public pages only; no accounts, trials, API calls or file downloads).
"Unverified" means I could not confirm it from a public page. Prices are USD unless marked.
Requirement used throughout: BTC and ETH, history back to 2021 (ideally 2020), daily acceptable, hourly or finer better, and a one-month test possible.

Key general finding: most vendors tie history depth to billing length. Several "monthly" plans give only 3-4 months of history (Tardis, Velo), or full history only at daily resolution (Coinglass). That rules them out for a one-month back-test, even when the monthly price looks low.

---

## 1. Liquidation history (long / short, USD)

| Provider / route | What it offers | History start | Finest resolution on cheapest plan with history | Cheapest plan (monthly billing?) | Free tier / trial | Access | Limits / licence | Source |
|---|---|---|---|---|---|---|---|---|
| CryptoQuant `market-data/liquidations` | Long/short liquidations (coin and USD) per exchange and `all_exchange`, BTC and ETH | BTC per docs: BitMEX 2019-04-02, Deribit 2019-05-25, Binance all_symbol 2019-11-20 (btc_usdt 2021-01-15), Bybit 2020-12-18/20, OKX 2020-12-17. ETH has a matching endpoint (example query from 2019-10-01) | Advanced: hourly ("High metric resolution (Hourly, Block-level)", "Full historic data"). Endpoint also lists `min` window; which plan unlocks it is unverified | Advanced $39/mo monthly ($29/mo on annual) | Basic free: daily, 3 years history only (about Nov 2023 onward), 10K credits/mo. 7-day Advanced trial, card on file, auto-converts | REST API, JSON or CSV | Pricing FAQ: Basic and Advanced include "API access: market data". Conflict: the endpoint doc page says an access token needs Professional or Premium. Treat Advanced API access to liquidations as likely but unverified. Docs warn Binance changed liquidation collection on 2021-04-27 (distribution changes). Downloads are under a "personal-use licence" | cryptoquant.com/pricing ; docs.cryptoquant.com/api-reference/btc-market-data/liquidations |
| Coinglass API `/api/futures/liquidation/aggregated-history` | Aggregated long/short liquidation USD across chosen exchanges; also per-pair history | Unverified (docs state no earliest date) | Daily only for full history. Hobbyist: 4h minimum interval and 4h history capped at 180 days. Startup ($79): 30m min, 1h capped 180 days. Standard ($299): 15m capped 90 days, 1h 360 days. Only `1d` is "Full history" on every plan | Hobbyist $29/mo (monthly price from a search snippet of the official page; my direct read showed only Black-Friday annual prices: $273/yr Hobbyist, $741/yr Startup) | No free tier or trial mentioned | REST API | Hobbyist/Startup "Personal use"; Standard+ commercial. Rate limit 30/min (Hobbyist). Paid as one-time crypto payment, no auto-renew, non-refundable | coinglass.com/pricing ; docs.coinglass.com/reference/intervals ; docs.coinglass.com/reference/aggregated-liquidation-history |
| Coinalyze API | Liquidation history per market | Unverified | Daily retained permanently; intraday (1m to 12h) keeps only the last 1500-2000 points, deleted daily | Free | Free; needs an API key from a (free) account | REST API | Asks for attribution on public use. Rate limit not confirmed | api.coinalyze.net/v1/doc |
| data.binance.vision `liquidationSnapshot` | Daily zip files of liquidation snapshots | USD-M (`futures/um`): folder does not exist. COIN-M (`futures/cm`) BTCUSD_PERP: 2023-06-25 to 2024-10-14 (listing ends there) | Event-level | Free | Free | CSV zips (S3) | COIN-M only and too short for this test | s3-ap-northeast-1.amazonaws.com/data.binance.vision listings |
| Tardis.dev `liquidations` | Raw liquidation events | Binance USD-M 2020-01-07, OKX 2020-12-17/18, Bybit 2020-11-03, BitMEX 2019-03-30, Deribit 2019-03-30 to 2023-10-03 | Event-level | Perpetuals plan, Solo $700/mo; monthly billing gives only 4 months of history (yearly gives 4 years). Academic $350/mo is quarterly/yearly only | First day of every month free as CSV, no key. Trial: days 1-10 of the previous month only | CSV + replay API | Binance forceOrder pushes at most one snapshot per second per symbol since April 2021, so not every liquidation is captured (affects every vendor using that feed) | tardis.dev ; docs.tardis.dev/faq/data ; docs.tardis.dev/faq/billing-and-subscriptions |
| Deribit history API | Trades carry a `liquidation` flag (M/T/MT) | Platform start (unverified exact date) | Event-level | Free | Free, public | REST | Deribit only; small share of liquidations | docs.deribit.com (get_last_trades_by_currency_and_time) |
| OKX / Bybit / BitMEX own archives | Bybit public.bybit.com has only trading, spot, kline, premium_index, spot_index folders (no liquidations). No official OKX or BitMEX bulk liquidation archive found | n/a | n/a | n/a | n/a | n/a | OKX/BitMEX not fully verified | public.bybit.com |

---

## 2. Options skew and put/call history (Deribit)

| Provider / route | What it offers | History start | Finest resolution on cheapest plan with history | Cheapest plan (monthly billing?) | Free tier / trial | Access | Limits / licence | Source |
|---|---|---|---|---|---|---|---|---|
| Deribit history API (`history.deribit.com`, `public/get_last_trades_by_currency_and_time`, `kind=option`) | Every option trade with `iv`, `index_price`, `mark_price`, `direction`, `amount`, instrument (strike, expiry, put/call). Enough to build put/call volume ratios and an approximate 25-delta skew (compute delta from iv) | A third-party repo states all derivatives trades "since the start of the platform" are public there. Exact start not verified | Trade level (aggregate to 15m/1h/1d yourself) | Free | Free, public, no key | REST, max 1000 trades per call | No open-interest history from trades. Rate limits not checked. Pull will take many calls | docs.deribit.com/api-reference/market-data/public-get_last_trades_by_currency_and_time.md ; github.com/BarendPotijk/deribit_historical_trades |
| Glassnode `options_25delta_skew_*` (1w/1m/3m/6m, exchanges incl. Deribit) | Ready-made 25-delta skew series; put/call metrics not seen in the visible part of the docs | Unverified | 10m / 1h / 24h listed for the endpoint; tier unverified | Professional "from $584/mo billed annually"; API is a separate add-on with no listed price. No monthly price shown | Advanced ($49/mo annual) has no API | API | API credits sold as add-on | studio.glassnode.com/pricing ; docs.glassnode.com/basic-api/api ; docs.glassnode.com/basic-api/endpoints/derivatives |
| Tardis.dev `options_chain` | Daily files of Deribit option ticker data (mark IV, greeks, OI via ticker channel) | Deribit data since 2019-03-30; ticker/markprice channels since 2019-10-01; sample file 2020-03-01 | Tick level | Options plan Solo $700/mo; monthly gives 4 months of history only | First day of each month free (very large files) | CSV + API | Same billing-history rule as above | tardis.dev ; docs.tardis.dev/historical-data-details/deribit |
| Laevitas | Options analytics | n/a | Premium $50/mo gives 1 year history (web, CSV exports; API not stated). Enterprise $500/mo per seat includes API historical data (depth not stated) | Premium $50/mo (too short), Enterprise $500/mo | Free plan: 1 week history | Web/CSV; API on Enterprise | Skew/put-call history depth not stated | laevitas.ch/pricing |
| Block Scholes | IV surfaces, IV indices, greeks; BTC and ETH | 3 years history only with annual billing on Core; 1 year with quarterly on Prime | Hourly (Core) | Core £499/mo (no monthly-billing history stated) | 14-day trial with 2 weeks rolling history | REST | Own-application licence only, no redistribution | console.blockscholes.com/products/data-plans |
| Velo | Futures/options/spot data API | Monthly subscription includes only 3 months history; yearly gives full | Unverified | API key $199/mo | Trial on request | REST/CSV | Options columns not confirmed | docs.velo.xyz/api |
| Amberdata | Options analytics (historically) | n/a | n/a | No public pricing: amberdata.io/pricing now redirects to a Kaiko acquisition notice; offerings moved onto the Kaiko platform (contact sales) | n/a | n/a | Unverified | kaiko.com news page |
| Coinglass options endpoints | Max pain, options info, exchange OI history, exchange volume history | Unverified | Unverified | Hobbyist $29/mo | none | API | No skew or put/call history endpoint listed | docs.coinglass.com/reference/endpoint-overview |

---

## 3. Order-book depth history (bid/ask within 1-2% of mid)

| Provider / route | What it offers | History start | Finest resolution on cheapest plan with history | Cheapest plan (monthly billing?) | Free tier / trial | Access | Limits / licence | Source |
|---|---|---|---|---|---|---|---|---|
| data.binance.vision `bookDepth` (USD-M futures) | Daily files of book depth by percentage band around price, BTCUSDT and ETHUSDT (also COIN-M folder) | BTCUSDT and ETHUSDT: 2023-01-01 | Sub-minute snapshots by reputation; exact columns and cadence not verified because I did not download a file | Free | Free | CSV zips | Starts 2023, not 2021. Futures book, not spot | S3 listing of data/futures/um/daily/bookDepth/ |
| Coinglass `orderbook/ask-bids-history` (futures and spot, pair and aggregated) | `bids_usd`, `asks_usd` within ±1% (also ±2, ±5 for Binance BTCUSDT) | Unverified | Full history at 1d only; 4h on Hobbyist capped at 180 days; 30m/1h on Startup capped 90/180 days | Hobbyist $29/mo | none | API | Snapshot values, not interval averages. Personal-use licence on low tiers | docs.coinglass.com/reference/futures-orderbook-history ; /reference/intervals |
| Tardis.dev `book_snapshot_25` / L2 | Full L2 to compute any depth band | Binance USD-M since 2019-11-17; Deribit since 2019-03-30 | Tick level | Spot or Perpetuals Solo $900 / $700 per month; monthly gives 4 months history only | First day of each month free | CSV + API | Large data volumes | tardis.dev ; docs.tardis.dev |
| CoinAPI | Historical order books; REST L2 snapshots (top 20 levels), Flat Files full depth | Binance spot BTC/USDT order books "since December 18, 2017" per CoinAPI tutorial | Unverified for REST history | Startup $79/mo (1,000 REST credits/day; 1 credit per 100 data points with `limit`) | Pay-as-you-go with $25 free credits | REST, Flat Files (S3) | Flat-file inclusion per plan unclear; REST said to fall back to daily for older records. Whether a 5-year 15m pull fits the credit budget is unverified | coinapi.io/market-data-api/pricing ; coinapi.io tutorial page |
| Kaiko (now incl. Amberdata) | Market depth / order book aggregations | Unverified | n/a | No public pricing (contact sales). A free "Research Account" is advertised; contents not stated | Trial on request | API | Unverified | kaiko.com |
| Binance `histDataLink` (T_DEPTH / S_DEPTH) | Tick-level order book archives | 2020 (dates conflict in Binance help pages) | Tick | Free but VIP-only | n/a | API | Requires VIP 1+ futures account; not usable here | developers.binance.com (search snippet) |

---

## 4. Entity / whale on-chain flows

| Provider / route | What it offers | History start | Finest resolution on cheapest plan with history | Cheapest plan (monthly billing?) | Free tier / trial | Access | Limits / licence | Source |
|---|---|---|---|---|---|---|---|---|
| CryptoQuant Professional | Exchange flows (inflow/outflow/netflow per exchange), Flow Indicator incl. Exchange Whale Ratio (top-10 inflows / total inflow), Exchange Inflow Spent Output Value Bands (BTC, by size band), Inter-Entity Flows (BTC); ETH has Exchange Flows and Flow Indicator | Full history (BTC from chain start); exact per-metric starts not checked | API on-chain endpoints at daily resolution per FAQ ("Professional adds on-chain API endpoints at daily resolution"); hourly/block may be web-only on this tier (unverified) | $109/mo monthly ($99 annual) | No trial on Professional; Basic/Advanced API is market data only | REST API, JSON/CSV; CSV download limited | 500K credits/mo; downloads under personal-use licence | cryptoquant.com/pricing ; docs.cryptoquant.com |
| Glassnode Professional + API add-on | Entity-adjusted exchange flows, size-band metrics | Full | Up to 10m | From $584/mo billed annually, plus API add-on (price not listed). No monthly price | Advanced ($49/mo annual): no API (Light API is 14 days, daily) | API | Credits add-on | studio.glassnode.com/pricing ; docs.glassnode.com/basic-api/api |
| Santiment | Exchange flow and whale-transaction metrics (restricted metrics) | API history: Sanbase Pro 1 year with 30-day lag; Sanbase Max 2 years; Business Max full | Unverified | Full history needs Business Max $999/mo (API site figure); Sanbase Max $249/mo gives only 2 years | Free: 1 year, 30-day lag; Sanbase Pro 14-day trial | GraphQL API | Business plans may have been withdrawn per a third-party changelog | app.santiment.net/pricing ; academy.santiment.net/products-and-plans/sanapi-plans |
| IntoTheBlock | Large transactions, exchange flows (historically) | n/a | n/a | intotheblock.com/pricing now redirects to sentora.com, which no longer shows analytics plans | n/a | n/a | Unverified whether still sold | sentora.com |
| Nansen | Wallet labels, smart-money flows (EVM focus) | Unverified | Unverified | Pro $69/mo monthly ($49 annual) with 2,000 credits/mo; historical endpoints reportedly 5 credits per call (secondary source) | Unverified | API | No BTC exchange-flow endpoint confirmed; plan page behind login | docs.nansen.ai (search snippets) |

---

## Cheapest test route per kind

| Kind | Cheapest route with enough history (2021 or earlier) | One-month cost | Notes |
|---|---|---|---|
| 1. Liquidations | CryptoQuant Advanced, hourly, per exchange, back to 2019/2020 | $39 | Depends on Advanced API covering the liquidations endpoint (FAQ says yes for "market data"; one doc page says Professional). If it turns out to need Professional: $109. Free daily fallback: Coinalyze (start date unverified). Coinglass Hobbyist $29 gives full history at daily only |
| 2. Options skew, put/call | Deribit history API (free), build put/call volume ratio and trade-IV skew yourself | $0 | No OI history. Ready-made skew needs Glassnode Pro (~$584+/mo annual) or Laevitas Enterprise ($500/mo) |
| 3. Order-book depth | No cheap route back to 2021 at intraday resolution. Free Binance futures bookDepth from 2023-01-01. Coinglass $29 at daily for full history (start unverified) | $0 (from 2023) / $29 (daily) | Tardis monthly gives only 4 months; CoinAPI $79 might work but credit/coverage unverified |
| 4. Whale / entity flows | CryptoQuant Professional (exchange whale ratio, inflow value bands, netflow) | $109 | Daily via API on this tier. Glassnode and Santiment full-history API both cost several hundred to ~$1,000/mo |

## Recommendation (one source to test first)

Test **liquidation history from CryptoQuant Advanced, one month, $39** (monthly billing, cancel any time, refund only within 24 h). Reasons: it is the only route found that gives hourly long/short liquidations for BTC and ETH across Binance, OKX, Bybit, BitMEX and Deribit back to 2019-2020 for under $50; the API returns CSV; and the same subscription includes other market data. Before paying, confirm in their docs or with support that the Advanced API key can call `market-data/liquidations` at `window=hour` (the docs conflict). If it cannot, the same test costs $109 on Professional, which would also cover kind 4.

Run the free Deribit options pull (kind 2) in parallel at no cost.

Caveats for any test: Binance liquidation feeds were throttled from April 2021 (CryptoQuant flags a distribution change on 2021-04-27), so liquidation totals are lower bounds and not comparable across that date without care. Nothing here shows that any of these data predict prices; that is what the test is for.
