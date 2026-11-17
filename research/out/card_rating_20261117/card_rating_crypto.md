# Card rating: crypto (BTCUSDT, ETHUSDT)

Method of research/exp_memory.py: per card its steadiest raw reading (the sign of the reading in its most extreme fifth as a call of direction, on calls the triple barrier graded up or down), first half vs second half. Combined score = the worse half in the reading's own direction (50 + steady). In-sample history; a rating ranks cards, it proves no edge.

- window 2020-01-01 00:00 .. 2025-11-10 23:45 UTC, halves split at 2022-11-30 20:30; horizon 96 sessions; 390670 graded rows (BTCUSDT 193571, ETHUSDT 197099); up 50.3%
- voting (worse half > 50.5%, top 10, at least 3): Pivot points (daily and weekly), Moving-average ribbon, Trend quality and squeeze, Momentum and stretch, News and economic events, Support and resistance, Market structure, Aroon and Vortex (1h to daily), Coinbase premium, Kaufman adaptive average (KAMA)
- voting voices: pivots, ribbon, trendq, momentum, meanrev, pullback, news, macro, levels, structure, aroon, cbprem, kama, owner
- built in 1393.4s, peak None MB

| # | card | steadiest reading | 1st half | 2nd half | worse half | direction | BTCUSDT (1st / 2nd) | ETHUSDT (1st / 2nd) |
|---|---|---|---|---|---|---|---|---|
| 1 | Pivot points (daily and weekly) (votes) | pvt_cam_day | 57.6 | 54.8 | 54.8 | with | 56.4 / 55.1 | 58.8 / 54.5 |
| 2 | Moving-average ribbon (votes) | rb_gmma_1h | 54.4 | 54.6 | 54.4 | with | 54.2 / 55.5 | 54.6 / 53.6 |
| 3 | Trend quality and squeeze (votes) | tq_rsi_1h | 55.2 | 54.1 | 54.1 | with | 54.7 / 53.7 | 55.6 / 54.5 |
| 4 | Momentum and stretch (votes) | stretch from the 1h average | 55.7 | 53.9 | 53.9 | with | 55.1 / 53.4 | 56.2 / 54.3 |
| 5 | News and economic events (votes) | a US release is near | 53.9 | 53.9 | 53.9 | with | 51.5 / 55.4 | 56.2 / 52.5 |
| 6 | Support and resistance (votes) | place in yesterday's range | 55.3 | 53.7 | 53.7 | with | 54.2 / 53.9 | 56.4 / 53.4 |
| 7 | Market structure (votes) | ms_pos_4h | 54.8 | 53.7 | 53.7 | with | 53.0 / 54.5 | 56.5 / 52.8 |
| 8 | Aroon and Vortex (1h to daily) (votes) | vtx_1h | 56.9 | 53.6 | 53.6 | with | 56.8 / 52.6 | 57.0 / 54.6 |
| 9 | Coinbase premium (votes) | cbp_z | 55.1 | 53.4 | 53.4 | with | 56.1 / 53.1 | 54.1 / 53.7 |
| 10 | Kaufman adaptive average (KAMA) (votes) | kama_er_1h | 54.5 | 53.4 | 53.4 | with | 54.7 / 53.0 | 54.4 / 53.7 |
| 11 | Linear-regression channel (1h to daily) | lrc_slope_1h | 53.3 | 53.4 | 53.3 | with | 53.2 / 54.3 | 53.5 / 52.5 |
| 12 | CCI (15m to daily) | cci_4h | 54.5 | 53.2 | 53.2 | with | 54.8 / 54.2 | 54.2 / 52.1 |
| 13 | Money Flow Index (15m to daily) | mfi_1h | 55.5 | 53.0 | 53.0 | with | 55.5 / 52.2 | 55.5 / 53.7 |
| 14 | Fisher Transform (15m to 4h) | fishext_1h | 54.4 | 53.0 | 53.0 | with | 54.9 / 51.9 | 53.9 / 54.1 |
| 15 | Ichimoku cloud | ich_lag_1h | 54.8 | 52.8 | 52.8 | with | 54.7 / 52.7 | 54.9 / 52.9 |
| 16 | Elder-Ray (1h to daily) | eld_bull_1h | 54.4 | 52.8 | 52.8 | with | 54.1 / 52.8 | 54.6 / 52.8 |
| 17 | Volume profile (session and 7 days) | vpf_poc_7d | 52.8 | 54.0 | 52.8 | with | 53.2 / 53.4 | 52.4 / 54.6 |
| 18 | StochRSI (15m to daily) | os_k_1h | 52.8 | 52.6 | 52.6 | with | 52.4 / 51.3 | 53.1 / 53.9 |
| 19 | Moving averages (SMA and EMA 5-200) | ma_cross_4h | 56.3 | 52.5 | 52.5 | with | 53.8 / 52.7 | 59.2 / 52.3 |
| 20 | Cross-exchange funding and OI | xf_avg | 47.5 | 46.9 | 52.5 | against | 45.3 / 51.5 | 49.6 / 42.6 |
| 21 | Order flow (CVD) | 4h order flow (CVD) | 52.5 | 52.8 | 52.5 | with | 52.1 / 52.4 | 52.8 / 53.2 |
| 22 | Intraday levels (VWAP and opening range) | id_vwap_w | 52.4 | 54.0 | 52.4 | with | 52.4 / 54.9 | 52.4 / 53.1 |
| 23 | Heikin-Ashi trend (15m to 4h) | ha_run_1h | 52.3 | 52.6 | 52.3 | with | 52.0 / 51.8 | 52.6 / 53.3 |
| 24 | BTC dominance | dm_btc_7d | 52.2 | 56.9 | 52.2 | with | 52.8 / 58.8 | 51.5 / 55.1 |
| 25 | Ultimate Oscillator (15m, 1h, daily) | uoz_1h | 54.4 | 52.2 | 52.2 | with | 56.6 / 50.1 | 52.3 / 55.1 |
| 26 | TRIX (1h to daily) | trix_1h | 53.5 | 52.2 | 52.2 | with | 53.8 / 53.9 | 53.3 / 50.6 |
| 27 | Supertrend (15m to daily) | os_st_agree | 53.3 | 52.2 | 52.2 | with | 51.8 / 52.3 | 54.7 / 52.0 |
| 28 | Timeframe strength | 15m trend | 52.2 | 52.6 | 52.2 | with | 51.3 / 51.9 | 52.9 / 53.3 |
| 29 | RSI divergence (15m to 4h) | rdiv_15m | 47.3 | 47.9 | 52.1 | against | 48.6 / 47.8 | 46.0 / 47.9 |
| 30 | Market breadth and ETH/BTC | brd_ethbtc_7d | 48.0 | 45.8 | 52.0 | against | 46.7 / 44.1 | 49.2 / 47.4 |
| 31 | Perp basis and premium | pb_level | 48.5 | 47.9 | 51.5 | against | 46.3 / 49.8 | 50.3 / 46.3 |
| 32 | Funding and positioning | funding rate | 48.5 | 48.3 | 51.5 | against | 45.9 / 50.2 | 50.7 / 46.6 |
| 33 | Moving averages as support and resistance | mas_hold_1h | 48.3 | 48.6 | 51.4 | against | 48.6 / 46.9 | 47.9 / 50.3 |
| 34 | Williams %R (15m to daily) | wr_1h | 51.6 | 51.4 | 51.4 | with | 50.6 / 50.7 | 52.6 / 52.2 |
| 35 | Korea premium | kp_z30 | 48.6 | 48.6 | 51.4 | against | 48.7 / 49.2 | 48.5 / 48.1 |
| 36 | Binance positioning (archive) | fl_ls_global_z | 45.6 | 48.7 | 51.3 | against | 45.9 / 47.3 | 44.6 / 50.0 |
| 37 | Working strategies | StochRSI core zone | 48.7 | 47.1 | 51.3 | against | 51.3 / 45.3 | 46.2 / 49.0 |
| 38 | Options flow (Deribit) | of_block_bear_7d | 51.1 | 51.4 | 51.1 | with | 51.7 / 51.1 | 50.4 / 51.5 |
| 39 | Trade setups | su_trap | 52.6 | 51.0 | 51.0 | with | 51.8 / 52.7 | 53.4 / 49.4 |
| 40 | Hull moving average | hull_pos_1h | 51.4 | 51.0 | 51.0 | with | 51.0 / 50.4 | 51.7 / 51.5 |
| 41 | On-chain activity and flows | fl_netflow_7d | 49.1 | 46.9 | 50.9 | against | 47.9 / 47.6 | 50.3 / 46.6 |
| 42 | Daily range budget and range breaks | adr_pos | 51.3 | 50.9 | 50.9 | with | 49.9 / 50.0 | 52.5 / 51.9 |
| 43 | Chaikin money flow and OBV (1h to daily) | obvdiv_1d | 50.8 | 52.3 | 50.8 | with | 50.8 / 50.9 | 50.8 / 54.1 |
| 44 | Regime | regime MOMENTUM_DOWN | 44.6 | 49.3 | 50.7 | against | 40.8 / 49.0 | 47.9 / 49.5 |
| 45 | Mass Index (1h to daily) | massb_1d | 49.3 | 47.5 | 50.7 | against | 61.7 / 57.8 | 38.4 / 37.1 |
| 46 | Stablecoin supply | stb_7d | 51.4 | 50.7 | 50.7 | with | 50.0 / 51.6 | 52.9 / 49.8 |
| 47 | Time and session | ck_dow_cos | 50.5 | 50.7 | 50.5 | with | 51.1 / 50.7 | 49.8 / 50.8 |
| 48 | Parabolic SAR (15m to daily) | psar_1h | 50.4 | 51.2 | 50.4 | with | 50.4 / 50.4 | 50.4 / 51.9 |
| 49 | Fibonacci retracement | fib_depth_4h | 47.0 | 49.7 | 50.3 | against | 47.4 / 49.4 | 46.4 / 50.0 |
| 50 | Options: implied volatility and skew | op_dvol_24h | 50.2 | 52.1 | 50.2 | with | 51.1 / 51.6 | 49.4 / 52.6 |
| 51 | CME gap (spot proxy) | cg_open | 49.3 | 52.6 | 50.0 | against | 50.3 / 50.5 | 47.8 / 54.2 |
| 52 | Candle size and realistic targets | cs_used | 52.5 | 49.2 | 50.0 | with | 53.0 / 47.8 | 52.1 / 50.8 |
| 53 | Spot vs perp leadership | sl_share_z | 48.6 | 51.9 | 50.0 | against | 48.5 / 50.7 | 48.6 / 53.0 |
| 54 | Bitfinex margin positions | fl_bfx_14d | 50.6 | 48.1 | 50.0 | with | 51.3 / 50.9 | 49.7 / 45.2 |
| 55 | Fear and Greed | fng_level | 51.0 | 48.6 | 50.0 | with | 51.0 / 49.6 | 51.0 / 47.6 |
| 56 | CME futures positioning (CFTC) | fl_cme_lev_z | 48.8 | 50.1 | 50.0 | against | 49.3 / 49.8 | 48.2 / 50.6 |
| 57 | Liquidity (order book) | - | - | - | - | no history yet | - | - |
| 58 | Kronos forecast | - | - | - | - | no history yet | - | - |
| 59 | Long/short positioning | - | - | - | - | no history yet | - | - |
| 60 | Liquidation pressure (proxy) | - | - | - | - | no history yet | - | - |
| 61 | Spot ETF flows | etf_1d | - | - | - | too little history | - | - |
