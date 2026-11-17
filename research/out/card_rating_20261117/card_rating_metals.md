# Card rating: metals (XAUUSD, XAGUSD)

Method of research/exp_memory.py: per card its steadiest raw reading (the sign of the reading in its most extreme fifth as a call of direction, on calls the triple barrier graded up or down), first half vs second half. Combined score = the worse half in the reading's own direction (50 + steady). In-sample history; a rating ranks cards, it proves no edge.

- window 2020-01-01 23:00 .. 2025-11-10 23:45 UTC, halves split at 2022-12-07 12:30; horizon 96 sessions; 269799 graded rows (XAUUSD 135214, XAGUSD 134585); up 50.5%
- voting (worse half > 50.5%, top 10, at least 3): Mass Index (1h to daily), Ultimate Oscillator (15m, 1h, daily), Regime, Volatility gauges, Elder-Ray (1h to daily), CCI (15m to daily), Pivot points (daily and weekly), Moving averages as support and resistance, Ichimoku cloud, Aroon and Vortex (1h to daily)
- voting voices: mass, ultosc, regime, volx, elder, cci, pivots, mavg_sr, ichimoku, aroon, owner
- built in 815.6s, peak None MB

| # | card | steadiest reading | 1st half | 2nd half | worse half | direction | XAUUSD (1st / 2nd) | XAGUSD (1st / 2nd) |
|---|---|---|---|---|---|---|---|---|
| 1 | Mass Index (1h to daily) (votes) | massb_1d | 36.9 | 43.5 | 56.5 | against | 51.6 / 41.7 | 6.9 / 46.7 |
| 2 | Ultimate Oscillator (15m, 1h, daily) (votes) | uoz_1d | 57.7 | 53.2 | 53.2 | with | 56.8 / 55.1 | 59.2 / 50.9 |
| 3 | Regime (votes) | regime TREND_DOWN | 52.7 | 53.9 | 52.7 | with | 53.0 / 53.0 | 52.3 / 54.2 |
| 4 | Volatility gauges (votes) | vx_gold | 52.5 | 52.5 | 52.5 | with | 52.8 / 51.9 | 52.3 / 53.1 |
| 5 | Elder-Ray (1h to daily) (votes) | eld_bull_1d | 52.3 | 52.5 | 52.3 | with | 53.1 / 54.2 | 51.6 / 50.2 |
| 6 | CCI (15m to daily) (votes) | cci_4h | 52.1 | 52.3 | 52.1 | with | 53.1 / 54.4 | 51.1 / 50.2 |
| 7 | Pivot points (daily and weekly) (votes) | pvt_cam_day | 52.8 | 52.0 | 52.0 | with | 53.2 / 53.8 | 52.5 / 50.0 |
| 8 | Moving averages as support and resistance (votes) | mas_room_4h | 52.2 | 52.0 | 52.0 | with | 52.2 / 54.3 | 52.2 / 50.1 |
| 9 | Ichimoku cloud (votes) | ich_lag_1h | 53.5 | 51.9 | 51.9 | with | 53.4 / 52.6 | 53.7 / 51.0 |
| 10 | Aroon and Vortex (1h to daily) (votes) | vtx_1h | 53.5 | 51.8 | 51.8 | with | 54.1 / 51.8 | 52.9 / 51.8 |
| 11 | News and economic events | a US release is near | 47.6 | 48.2 | 51.8 | against | 46.2 / 48.8 | 49.1 / 47.6 |
| 12 | Momentum and stretch | last 24 hours' move | 53.0 | 51.7 | 51.7 | with | 53.4 / 52.3 | 52.5 / 50.9 |
| 13 | Futures positioning (CFTC) | cot_level | 51.6 | 54.5 | 51.6 | with | 56.3 / 55.9 | 46.5 / 45.2 |
| 14 | Gold and silver ETF holdings | ge_gld_dvol | 48.0 | 48.4 | 51.6 | against | 47.2 / 48.2 | 48.7 / 48.6 |
| 15 | Fisher Transform (15m to 4h) | fishext_1h | 52.0 | 51.6 | 51.6 | with | 53.2 / 53.8 | 50.6 / 49.1 |
| 16 | Metals ratios | mt_lead_24h | 51.4 | 52.5 | 51.4 | with | 51.9 / 52.3 | 51.0 / 52.8 |
| 17 | Kaufman adaptive average (KAMA) | kama_slope_1h | 52.3 | 51.3 | 51.3 | with | 52.4 / 52.6 | 52.2 / 49.9 |
| 18 | Linear-regression channel (1h to daily) | lrc_r2_1d | 51.3 | 52.0 | 51.3 | with | 49.7 / 54.4 | 52.9 / 48.8 |
| 19 | Time and session | ck_us_open_in | 51.8 | 51.3 | 51.3 | with | 51.3 / 54.2 | 52.3 / 48.3 |
| 20 | Daily range budget and range breaks | adr_room_up | 51.3 | 51.7 | 51.3 | with | 51.5 / 54.2 | 51.0 / 49.2 |
| 21 | Moving-average ribbon | rb_width_1h | 52.0 | 51.2 | 51.2 | with | 52.2 / 51.7 | 51.8 / 50.6 |
| 22 | RSI divergence (15m to 4h) | rdiv_4h | 48.2 | 48.8 | 51.2 | against | 50.3 / 53.2 | 45.6 / 45.2 |
| 23 | Trend quality and squeeze | tq_rsi_1h | 51.7 | 51.2 | 51.2 | with | 52.6 / 53.0 | 50.6 / 49.1 |
| 24 | Trade setups | su_pullback | 48.2 | 48.9 | 51.1 | against | 48.5 / 48.8 | 48.0 / 49.0 |
| 25 | Fibonacci retracement | fib_depth_1h | 48.5 | 48.9 | 51.1 | against | 47.2 / 49.2 | 49.8 / 48.6 |
| 26 | StochRSI (15m to daily) | os_k_15m | 48.9 | 48.8 | 51.1 | against | 49.1 / 49.6 | 48.7 / 47.9 |
| 27 | Market structure | ms_pos_1h | 52.0 | 51.0 | 51.0 | with | 52.1 / 52.4 | 52.0 / 49.6 |
| 28 | Working strategies | weekly regime (EMA20/50) | 49.0 | 48.7 | 51.0 | against | 49.9 / 52.7 | 48.1 / 44.6 |
| 29 | Chaikin money flow and OBV (1h to daily) | obvdiv_1d | 46.0 | 49.1 | 50.9 | against | 50.4 / 45.1 | 41.4 / 52.1 |
| 30 | Money Flow Index (15m to daily) | mfi_1d | 51.9 | 50.9 | 50.9 | with | 52.4 / 52.7 | 51.4 / 49.0 |
| 31 | Moving averages (SMA and EMA 5-200) | ma_stack_1d | 50.9 | 51.0 | 50.9 | with | 52.1 / 54.7 | 49.5 / 46.4 |
| 32 | Williams %R (15m to daily) | wr_15m | 48.9 | 49.2 | 50.8 | against | 49.3 / 50.6 | 48.6 / 47.8 |
| 33 | Volume profile (session and 7 days) | vpf_poc_7d | 53.7 | 50.7 | 50.7 | with | 52.2 / 51.8 | 55.4 / 49.5 |
| 34 | Support and resistance | strength of the resistance above | 52.1 | 50.7 | 50.7 | with | 52.7 / 56.2 | 51.5 / 45.9 |
| 35 | Intraday levels (VWAP and opening range) | id_band | 49.3 | 49.2 | 50.7 | against | 50.4 / 49.2 | 48.1 / 49.3 |
| 36 | TRIX (1h to daily) | trix_1h | 53.2 | 50.6 | 50.6 | with | 52.9 / 49.9 | 53.6 / 51.5 |
| 37 | Timeframe strength | 1h trend | 52.1 | 50.6 | 50.6 | with | 52.9 / 54.1 | 51.4 / 46.8 |
| 38 | Candle size and realistic targets | cs_used | 48.4 | 49.4 | 50.6 | against | 48.9 / 46.8 | 47.8 / 52.3 |
| 39 | Heikin-Ashi trend (15m to 4h) | ha_run_4h | 48.6 | 49.4 | 50.6 | against | 48.6 / 50.0 | 48.7 / 48.9 |
| 40 | Hull moving average | hull_pos_1h | 50.6 | 50.8 | 50.6 | with | 50.9 / 52.3 | 50.2 / 49.3 |
| 41 | Parabolic SAR (15m to daily) | psar_1d | 51.5 | 50.5 | 50.5 | with | 51.8 / 51.7 | 51.2 / 49.2 |
| 42 | Supertrend (15m to daily) | os_st_15m | 49.6 | 48.8 | 50.4 | against | 51.2 / 49.7 | 48.0 / 47.8 |
| 43 | Rates and the dollar | rt_y10_5d | 50.1 | 51.4 | 50.1 | with | 49.5 / 52.0 | 50.8 / 50.9 |
| 44 | Kronos forecast | - | - | - | - | no history yet | - | - |
