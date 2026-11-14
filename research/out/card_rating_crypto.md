# Card rating: crypto (BTCUSDT, ETHUSDT)

Method of research/exp_memory.py: per card its steadiest raw reading (the sign of the reading in its most extreme fifth as a call of direction, on calls the triple barrier graded up or down), first half vs second half. Combined score = the worse half in the reading's own direction (50 + steady). In-sample history; a rating ranks cards, it proves no edge.

- window 2020-01-01 00:00 .. 2026-11-11 11:15 UTC, halves split at 2023-05-31 01:45; horizon 96 sessions; 456473 graded rows (BTCUSDT 226533, ETHUSDT 229940); up 50.3%
- voting (worse half > 50.5%, top 10, at least 3): Regime, Moving-average ribbon, Trend quality and squeeze, Momentum and stretch, Support and resistance, Coinbase premium, Kaufman adaptive average (KAMA), Intraday levels (VWAP and opening range), Moving averages (SMA and EMA 5-200), Ichimoku cloud
- voting voices: regime, ribbon, trendq, momentum, meanrev, pullback, levels, cbprem, kama, intraday, mavg, ichimoku, owner
- built in 385.6s, peak 884 MB

| # | card | steadiest reading | 1st half | 2nd half | worse half | direction | BTCUSDT (1st / 2nd) | ETHUSDT (1st / 2nd) |
|---|---|---|---|---|---|---|---|---|
| 1 | Regime (votes) | regime MOMENTUM_DOWN | 44.9 | 45.4 | 54.6 | against | 40.8 / 44.6 | 48.4 / 45.9 |
| 2 | Moving-average ribbon (votes) | rb_gmma_1h | 54.6 | 53.9 | 53.9 | with | 55.3 / 53.9 | 54.0 / 53.9 |
| 3 | Trend quality and squeeze (votes) | tq_rsi_1h | 55.2 | 53.6 | 53.6 | with | 55.6 / 52.5 | 54.9 / 54.5 |
| 4 | Momentum and stretch (votes) | stretch from the 1h average | 55.7 | 53.2 | 53.2 | with | 55.7 / 52.4 | 55.6 / 54.0 |
| 5 | Support and resistance (votes) | place in yesterday's range | 55.3 | 52.8 | 52.8 | with | 54.6 / 53.0 | 56.0 / 52.7 |
| 6 | Coinbase premium (votes) | cbp_z | 55.4 | 52.7 | 52.7 | with | 56.1 / 52.1 | 54.8 / 53.4 |
| 7 | Kaufman adaptive average (KAMA) (votes) | kama_er_1h | 54.4 | 52.7 | 52.7 | with | 54.8 / 52.4 | 54.0 / 53.0 |
| 8 | Intraday levels (VWAP and opening range) (votes) | id_vwap_w | 52.7 | 53.4 | 52.7 | with | 53.0 / 53.7 | 52.3 / 53.0 |
| 9 | Moving averages (SMA and EMA 5-200) (votes) | ma_cross_4h | 55.1 | 52.6 | 52.6 | with | 53.2 / 53.5 | 57.2 / 51.7 |
| 10 | Ichimoku cloud (votes) | ich_lag_1h | 54.8 | 52.6 | 52.6 | with | 55.6 / 51.7 | 54.1 / 53.5 |
| 11 | News and economic events | a US release is near | 54.2 | 52.6 | 52.6 | with | 52.3 / 54.4 | 56.0 / 50.8 |
| 12 | Market structure | ms_pos_4h | 54.5 | 52.4 | 52.4 | with | 53.4 / 52.7 | 55.6 / 52.1 |
| 13 | Order flow (CVD) | 4h order flow (CVD) | 52.6 | 52.4 | 52.4 | with | 52.3 / 52.3 | 52.9 / 52.4 |
| 14 | Market breadth and ETH/BTC | brd_ethbtc_7d | 47.4 | 47.8 | 52.2 | against | 46.0 / 46.5 | 48.7 / 49.0 |
| 15 | Timeframe strength | 15m trend | 52.2 | 52.3 | 52.2 | with | 51.8 / 51.9 | 52.7 / 52.7 |
| 16 | Working strategies | StochRSI core zone | 48.1 | 47.2 | 51.9 | against | 49.2 / 46.8 | 47.0 / 47.6 |
| 17 | Stablecoin supply | stb_7d | 51.8 | 51.7 | 51.7 | with | 50.6 / 52.5 | 53.0 / 50.8 |
| 18 | Trade setups | su_trap | 52.4 | 51.2 | 51.2 | with | 51.8 / 52.5 | 52.9 / 49.9 |
| 19 | Fibonacci retracement | fib_gz_4h | 51.2 | 51.5 | 51.2 | with | 51.2 / 52.8 | 51.2 / 50.7 |
| 20 | Perp basis and premium | pb_level | 48.6 | 49.0 | 51.0 | against | 46.6 / 50.0 | 50.2 / 48.2 |
| 21 | Moving averages as support and resistance | mas_hold_1h | 48.1 | 49.1 | 50.9 | against | 48.2 / 47.7 | 48.1 / 50.2 |
| 22 | Hull moving average | hull_dir_1h | 50.8 | 50.9 | 50.8 | with | 50.3 / 50.6 | 51.2 / 51.3 |
| 23 | Time and session | ck_dow_cos | 50.6 | 51.6 | 50.6 | with | 51.3 / 51.1 | 49.9 / 52.1 |
| 24 | Options: implied volatility and skew | op_dvol_rank | 51.8 | 50.4 | 50.4 | with | 53.3 / 49.9 | 50.8 / 51.1 |
| 25 | Funding and positioning | funding rate | 50.2 | 50.2 | 50.2 | with | 48.7 / 50.5 | 51.5 / 49.9 |
| 26 | Candle size and realistic targets | cs_expand | 49.9 | 49.2 | 50.1 | against | 50.8 / 48.4 | 49.0 / 50.2 |
| 27 | Fear and Greed | fng_level | 50.6 | 48.5 | 50.0 | with | 50.4 / 49.4 | 50.8 / 47.6 |
| 28 | Liquidity (order book) | - | - | - | - | no history yet | - | - |
| 29 | Kronos forecast | - | - | - | - | no history yet | - | - |
| 30 | Long/short positioning | ls_global | - | - | - | too little history | - | - |
| 31 | Liquidation pressure (proxy) | - | - | - | - | no history yet | - | - |
| 32 | Spot ETF flows | etf_1d | - | - | - | too little history | - | - |
