# Card rating: index (SPX)

Method of research/exp_memory.py: per card its steadiest raw reading (the sign of the reading in its most extreme fifth as a call of direction, on calls the triple barrier graded up or down), first half vs second half. Combined score = the worse half in the reading's own direction (50 + steady). In-sample history; a rating ranks cards, it proves no edge.

- window 2020-01-02 14:30 .. 2025-11-10 20:45 UTC, halves split at 2022-11-29 17:15; horizon 26 sessions; 26732 graded rows (SPX 26732); up 52.5%
- voting (worse half > 50.5%, top 10, at least 3): Mass Index (1h to daily), Trade setups, RSI divergence (15m to 4h), Ultimate Oscillator (15m, 1h, daily), Moving averages (SMA and EMA 5-200), Linear-regression channel (1h to daily), Momentum and stretch, Daily range budget and range breaks, Stock-market breadth, Regime
- voting voices: mass, setups, rsidiv, ultosc, mavg, linreg, momentum, meanrev, pullback, adr, eqbreadth, regime, owner
- built in 122.0s, peak None MB

| # | card | steadiest reading | 1st half | 2nd half | worse half | direction | SPX (1st / 2nd) |
|---|---|---|---|---|---|---|---|
| 1 | Mass Index (1h to daily) (votes) | massb_4h | 33.1 | 29.6 | 66.9 | against | 33.1 / 29.6 |
| 2 | Trade setups (votes) | su_pullback | 61.8 | 56.9 | 56.9 | with | 61.8 / 56.9 |
| 3 | RSI divergence (15m to 4h) (votes) | rdiv_4h | 55.9 | 59.5 | 55.9 | with | 55.9 / 59.5 |
| 4 | Ultimate Oscillator (15m, 1h, daily) (votes) | uoz_1h | 59.6 | 55.7 | 55.7 | with | 59.6 / 55.7 |
| 5 | Moving averages (SMA and EMA 5-200) (votes) | ma_cross_1h | 57.9 | 55.3 | 55.3 | with | 57.9 / 55.3 |
| 6 | Linear-regression channel (1h to daily) (votes) | lrc_r2_1d | 56.9 | 55.1 | 55.1 | with | 56.9 / 55.1 |
| 7 | Momentum and stretch (votes) | pullback inside the trend | 58.0 | 54.6 | 54.6 | with | 58.0 / 54.6 |
| 8 | Daily range budget and range breaks (votes) | adr_room_dn | 54.4 | 54.6 | 54.4 | with | 54.4 / 54.6 |
| 9 | Stock-market breadth (votes) | eb_iwm_20d | 45.7 | 45.9 | 54.1 | against | 45.7 / 45.9 |
| 10 | Regime (votes) | regime TREND_UP | 55.5 | 53.8 | 53.8 | with | 55.5 / 53.8 |
| 11 | Trend quality and squeeze | tq_adx_15m | 53.8 | 54.9 | 53.8 | with | 53.8 / 54.9 |
| 12 | Chaikin money flow and OBV (1h to daily) | obvdiv_1d | 46.3 | 43.4 | 53.7 | against | 46.3 / 43.4 |
| 13 | Time and session | ck_us_open_in | 53.5 | 56.7 | 53.5 | with | 53.5 / 56.7 |
| 14 | Support and resistance | near yesterday's low | 53.5 | 56.3 | 53.5 | with | 53.5 / 56.3 |
| 15 | Moving averages as support and resistance | mas_test_4h | 53.3 | 57.0 | 53.3 | with | 53.3 / 57.0 |
| 16 | Kaufman adaptive average (KAMA) | kama_er_15m | 53.8 | 53.3 | 53.3 | with | 53.8 / 53.3 |
| 17 | Fibonacci retracement | fib_room_1h | 46.9 | 42.3 | 53.1 | against | 46.9 / 42.3 |
| 18 | Volume profile (session and 7 days) | vpf_poc_day | 53.8 | 53.0 | 53.0 | with | 53.8 / 53.0 |
| 19 | Williams %R (15m to daily) | wr_1h | 53.9 | 52.9 | 52.9 | with | 53.9 / 52.9 |
| 20 | Rates and the dollar | rt_dxy_5d | 53.8 | 52.8 | 52.8 | with | 53.8 / 52.8 |
| 21 | Fisher Transform (15m to 4h) | fishext_15m | 53.4 | 52.8 | 52.8 | with | 53.4 / 52.8 |
| 22 | Candle size and realistic targets | cs_body | 46.9 | 47.2 | 52.8 | against | 46.9 / 47.2 |
| 23 | Futures positioning (CFTC) | cot_level | 47.3 | 44.4 | 52.7 | against | 47.3 / 44.4 |
| 24 | S&P futures overnight | on_pos | 54.1 | 52.5 | 52.5 | with | 54.1 / 52.5 |
| 25 | News and economic events | a US release is near | 52.4 | 55.7 | 52.4 | with | 52.4 / 55.7 |
| 26 | Intraday levels (VWAP and opening range) | id_vwap_w | 52.3 | 55.4 | 52.3 | with | 52.3 / 55.4 |
| 27 | Pivot points (daily and weekly) | pvt_pos_day | 52.4 | 52.3 | 52.3 | with | 52.4 / 52.3 |
| 28 | Ichimoku cloud | ich_lag_4h | 48.2 | 46.5 | 51.8 | against | 48.2 / 46.5 |
| 29 | TRIX (1h to daily) | trix_4h | 46.7 | 48.2 | 51.8 | against | 46.7 / 48.2 |
| 30 | Working strategies | Donchian trend strategy | 51.8 | 52.0 | 51.8 | with | 51.8 / 52.0 |
| 31 | Elder-Ray (1h to daily) | eld_bear_4h | 44.7 | 48.3 | 51.7 | against | 44.7 / 48.3 |
| 32 | Timeframe strength | 4h trend | 51.7 | 53.0 | 51.7 | with | 51.7 / 53.0 |
| 33 | Megacap earnings | ern_last | 54.5 | 51.6 | 51.6 | with | 54.5 / 51.6 |
| 34 | Heikin-Ashi trend (15m to 4h) | ha_run_4h | 45.5 | 48.4 | 51.6 | against | 45.5 / 48.4 |
| 35 | StochRSI (15m to daily) | os_k_1h | 51.6 | 52.4 | 51.6 | with | 51.6 / 52.4 |
| 36 | Aroon and Vortex (1h to daily) | aro_osc_1h | 46.0 | 48.6 | 51.4 | against | 46.0 / 48.6 |
| 37 | Market structure | ms_1d | 51.7 | 51.3 | 51.3 | with | 51.7 / 51.3 |
| 38 | Supertrend (15m to daily) | os_st_4h | 48.6 | 48.8 | 51.2 | against | 48.6 / 48.8 |
| 39 | Moving-average ribbon | rb_pos_1h | 55.3 | 51.0 | 51.0 | with | 55.3 / 51.0 |
| 40 | Money Flow Index (15m to daily) | mfi_1d | 49.6 | 46.9 | 50.4 | against | 49.6 / 46.9 |
| 41 | Hull moving average | hull_x_1h | 50.4 | 51.4 | 50.4 | with | 50.4 / 51.4 |
| 42 | Parabolic SAR (15m to daily) | psar_1h | 49.2 | 49.9 | 50.1 | against | 49.2 / 49.9 |
| 43 | Volatility gauges | vx_level | 43.2 | 50.8 | 50.0 | against | 43.2 / 50.8 |
| 44 | CCI (15m to daily) | cci_15m | 50.3 | 49.1 | 50.0 | with | 50.3 / 49.1 |
| 45 | Kronos forecast | - | - | - | - | no history yet | - |
| 46 | Options mood (put/call) | pc_total | - | - | - | too little history | - |
