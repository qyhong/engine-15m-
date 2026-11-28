# Feed plan for the six non-crypto markets (28 Nov 2026)

Why: on 26-27 Nov 2026 Yahoo's futures charts (GC=F, SI=F, CL=F, BZ=F) served no bars for most of a day while the
markets traded. `engine15/bridge.py` carried gold, silver, WTI and Brent from exchange contracts meanwhile (101 bridged
bars each for gold, silver and WTI, 120 for Brent, per `data/bridge_bars.csv`). This note says what a second or
permanent feed could be. Every number below was measured from the Singapore box on 28 Nov 2026.

## What the outage did and did not hit

- Hit: the four futures charts. Not hit: USDJPY (JPY=X: 95 bars stored on 26 Nov, a full day) and the S&P 500
  (^GSPC: 14 bars on the 27 Nov half day, a full session; 26 Nov was a holiday).
- So Yahoo is not one feed that fails as one. USDJPY and SPX had no backup; both have one now (SPX below; USDJPY the
  rough xyz:JPY bridge, on the owner's word "Add rough bridge", 28 Nov 2026).

## What was tested

Each candidate's 15-minute bars for 19-27 Nov were fetched from the box (no key, no account) and compared with the
stored bars at the same times. Bars the bridge itself wrote were left out. "corr" is the correlation of 15-minute
returns; "bar gap" is the median / 95th percentile difference between the two returns of one bar, in basis points
(1 bp = 0.01%); "4h drift" is how far a series scaled to the stored close has moved off it four hours later (95th pct).

| Market | Source | corr | bar gap | 4h drift | Level vs stored |
|---|---|---|---|---|---|
| SPX (138 pairs) | Hyperliquid xyz:SP500 | 0.998 | 1.0 / 3.3 | 5.4 | 0.03% under |
| | OKX SPY-USDT-SWAP | 0.998 | 1.1 / 3.7 | 10.4 | fund, about index / 10 |
| | Binance SPYUSDT | 0.997 | 1.2 / 3.9 | 8.9 | fund, about index / 10 |
| | Bybit SPYUSDT, MEXC SPX500_USDT | 0.997, 0.996 | 1.2 / 4.4, 1.5 / 4.6 | 11.3, 9.2 | |
| | Gate SPX500, Kraken PF_SPYX, OKX US500, Bitget SP500 | 0.95, 0.91, 0.91, 0.91 | 7-9 / 18-27 | 22-52 | too loose |
| USDJPY (635 pairs) | Hyperliquid xyz:JPY | 0.79 | 1.3 / 5.1 | 5.3 | 0.04% over |
| | Bitget USDJPYUSDT, Bybit USDJPYUSDT | 0.48, 0.28 | 2.0 / 7.9, 2.3 / 11.4 | 9.8, 17.5 | too loose |
| XAUUSD (461 pairs) | Binance, OKX, Bybit XAU; Hyperliquid xyz:GOLD | 0.987, 0.986, 0.986, 0.983 | 0.8-1.9 / 2.6-6.1 | 7-10 | 0.02-0.17% under |
| XAGUSD (461) | Binance, OKX, Bybit XAG; Hyperliquid xyz:SILVER | 0.989, 0.989, 0.989, 0.988 | 2.3 / 7-8 | 16-18 | 0.4-0.5% under |
| WTI (461) | Binance, OKX, Bybit CL; Hyperliquid xyz:CL | 0.996, 0.996, 0.996, 0.993 | 1.2-1.7 / 4.8-6.8 | 6-8 | 0.01-0.13% under |
| BRENT (420) | Hyperliquid xyz:BRENTOIL; OKX, Bybit, Binance BZ | 0.983, 0.983, 0.983, 0.981 | 2.3-2.8 / 10 | 12-13 | 0.00-0.13% under |

- All of these traded round the clock in the window (about 96 bars a day, weekend included) and had a bar at every
  stored bar's time. Hours are therefore wider than the engine's; the bridge keeps the engine's own hours.
- USDJPY: xyz:JPY follows the LEVEL well (scaled once, it stayed within 5.4 bp at the 95th percentile and 11 bp at
  worst a whole day later), but a 15-minute USDJPY bar only moves about 3.6 bp, so a 1.3 bp gap is a third of the bar.
  The correlation is 0.79 on 15 minutes, 0.93 on one hour, 0.97 on four hours. It was NOT added to the bridge: the bar
  asked for was 0.9 on 15 minutes. Adding it is one line in `bridge.SOURCES` if the owner prefers a rough bar to none.
- Names to avoid: `SPXUSDT` / `SPX-USDT-SWAP` / Hyperliquid `SPX` are a crypto coin, not the index. MEXC `JPY_USDT`
  is not the dollar/yen rate either (correlation 0).
- Reached but no bars: Swissquote's public quote (a live bid/ask only). Refused or timed out from the box: Stooq
  (wants a browser), Cboe's delayed chart (403), Dukascopy's tick files (timeout).

## Risks

- Contract against future. These are perpetual contracts that follow spot or an index, not the front-month future the
  stored series is built on. Silver sat 0.5% under, gold up to 0.17% under. Scaling at the join removes the level; the
  drift column is what remains. Over a futures roll the two would part by the roll spread (not tested: no roll in the
  comparison that was examined; gold's ratio ranged about 1% across the window and the cause was not looked into).
- The SPY contracts follow the fund, which drops by its dividend four times a year; the index does not. Not tested.
  That is why xyz:SP500, which follows the index, is first.
- Weekends and holidays: the contracts trade when the real market is shut. Thin weekend prints are never stored (the
  calendar cuts them), but the first bar after a weekend carries the contract's weekend move as its opening gap.
- One venue each for the best SPX and Brent source (Hyperliquid's xyz market, run by a third party on that chain). It
  could be delisted or halted; the bridge then falls to the next source in the list.
- Rate limits were not tested. Use is one request per market per 15 minutes and only during an outage.
- Volume: bridged bars carry volume 0. Any reading that uses SPX or futures volume sees a hole for those hours.
- Window: nine days, one quiet holiday week. Not a proof for a fast market.
- Found while reading, not changed: the 45-minute test counts hours when the market was shut, so at the first bar
  after a daily break or overnight the bridge can step in if Yahoo is a minute late. Cost: one bar from the contract.

## Paid options (not tested; costs from memory, check before deciding)

- A broker's data API (OANDA, Interactive Brokers): real spot FX and metals, index and oil as CFDs or CME futures.
  Needs an account and a key on the box; roughly free to about $15 a month.
- A data vendor (Twelve Data, Polygon/Massive, Databento for CME): roughly $30 to $200 a month for intraday bars.

## Recommendation

1. Keep Yahoo as the main feed. The stored history sits on its level, and it was the futures charts that failed, once.
2. Make the exchange contracts the standing second feed through the bridge. Done in the working tree for SPX
   (`bridge.SOURCES`: xyz:SP500, then OKX SPY, then Binance SPY; tests added). Needs review and a normal deploy.
3. Give Brent the second and third source it lacks: Binance `BZUSDT` and OKX `BZ-USDT-SWAP` (0.981 / 0.983). Two
   entries in `bridge.SOURCES`, no new code.
4. USDJPY: the owner decides between xyz:JPY as a rough bridge (level good, single bars noisy) and a real FX feed
   from a broker key. Until then USDJPY has no backup.
5. Before calling any of this a replacement: record the contracts' bars beside Yahoo's every step for a month (a
   read-only CSV, no trading effect) so the gap is known across a roll, a dividend date and a fast day. Do not swap
   the main feed to a contract on nine days of data.
