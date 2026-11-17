# Card rating: fx (USDJPY)

Method of research/exp_memory.py: per card its steadiest raw reading (the sign of the reading in its most extreme fifth as a call of direction, on calls the triple barrier graded up or down), first half vs second half. Combined score = the worse half in the reading's own direction (50 + steady). In-sample history; a rating ranks cards, it proves no edge.

- window 2020-01-01 22:00 .. 2025-11-10 23:45 UTC, halves split at 2022-12-02 20:00; horizon 96 sessions; 142250 graded rows (USDJPY 142250); up 50.7%
- voting (worse half > 50.5%, top 10, at least 3): Trade setups, Regime, Time and session, Momentum and stretch, StochRSI (15m to daily), Volatility gauges, Intraday levels (VWAP and opening range), Daily range budget and range breaks, Linear-regression channel (1h to daily), Working strategies
- voting voices: setups, regime, clock, momentum, meanrev, pullback, stochrsi, volx, intraday, adr, linreg, strategies, owner
- built in 338.3s, peak None MB

| # | card | steadiest reading | 1st half | 2nd half | worse half | direction | USDJPY (1st / 2nd) |
|---|---|---|---|---|---|---|---|
| 1 | Trade setups (votes) | su_rangefade | 44.6 | 38.5 | 55.4 | against | 44.6 / 38.5 |
| 2 | Regime (votes) | regime TREND_DOWN | 56.4 | 55.3 | 55.3 | with | 56.4 / 55.3 |
| 3 | Time and session (votes) | ck_weekend | 53.7 | 53.5 | 53.5 | with | 53.7 / 53.5 |
| 4 | Momentum and stretch (votes) | 1h StochRSI | 52.7 | 52.5 | 52.5 | with | 52.7 / 52.5 |
| 5 | StochRSI (15m to daily) (votes) | os_k_1h | 52.7 | 52.5 | 52.5 | with | 52.7 / 52.5 |
| 6 | Volatility gauges (votes) | vx_front | 47.8 | 46.0 | 52.2 | against | 47.8 / 46.0 |
| 7 | Intraday levels (VWAP and opening range) (votes) | id_band | 54.2 | 52.1 | 52.1 | with | 54.2 / 52.1 |
| 8 | Daily range budget and range breaks (votes) | adr_room_dn | 53.3 | 52.1 | 52.1 | with | 53.3 / 52.1 |
| 9 | Linear-regression channel (1h to daily) (votes) | lrc_r2_4h | 52.1 | 52.9 | 52.1 | with | 52.1 / 52.9 |
| 10 | Working strategies (votes) | StochRSI core zone | 52.1 | 52.5 | 52.1 | with | 52.1 / 52.5 |
| 11 | Futures positioning (CFTC) | cot_pctile | 56.7 | 52.0 | 52.0 | with | 56.7 / 52.0 |
| 12 | Support and resistance | near yesterday's high | 56.2 | 52.0 | 52.0 | with | 56.2 / 52.0 |
| 13 | Aroon and Vortex (1h to daily) | aro_osc_1d | 48.0 | 47.5 | 52.0 | against | 48.0 / 47.5 |
| 14 | Fibonacci retracement | fib_gz_4h | 55.1 | 51.8 | 51.8 | with | 55.1 / 51.8 |
| 15 | Japan watch | jp_boj_next | 52.3 | 51.8 | 51.8 | with | 52.3 / 51.8 |
| 16 | Timeframe strength | weekly trend | 51.7 | 56.1 | 51.7 | with | 51.7 / 56.1 |
| 17 | Moving averages (SMA and EMA 5-200) | ma_cross_1d | 48.3 | 48.1 | 51.7 | against | 48.3 / 48.1 |
| 18 | Market structure | ms_pos_1h | 54.2 | 51.6 | 51.6 | with | 54.2 / 51.6 |
| 19 | Trend quality and squeeze | tq_adx_1h | 48.8 | 44.7 | 51.2 | against | 48.8 / 44.7 |
| 20 | Ichimoku cloud | ich_cloud_4h | 51.2 | 52.5 | 51.2 | with | 51.2 / 52.5 |
| 21 | Mass Index (1h to daily) | mass_1d | 48.9 | 48.4 | 51.1 | against | 48.9 / 48.4 |
| 22 | Ultimate Oscillator (15m, 1h, daily) | uoz_1h | 51.1 | 51.3 | 51.1 | with | 51.1 / 51.3 |
| 23 | Moving-average ribbon | rb_pos_1h | 51.5 | 51.0 | 51.0 | with | 51.5 / 51.0 |
| 24 | Elder-Ray (1h to daily) | eld_bear_4h | 48.8 | 49.0 | 51.0 | against | 48.8 / 49.0 |
| 25 | Kaufman adaptive average (KAMA) | kama_slope_4h | 49.2 | 48.1 | 50.8 | against | 49.2 / 48.1 |
| 26 | Hull moving average | hull_pos_1h | 51.8 | 50.8 | 50.8 | with | 51.8 / 50.8 |
| 27 | Candle size and realistic targets | cs_expand | 51.0 | 50.8 | 50.8 | with | 51.0 / 50.8 |
| 28 | Heikin-Ashi trend (15m to 4h) | ha_col_4h | 51.1 | 50.7 | 50.7 | with | 51.1 / 50.7 |
| 29 | Moving averages as support and resistance | mas_test_4h | 50.8 | 50.7 | 50.7 | with | 50.8 / 50.7 |
| 30 | Rates and the dollar | rt_gap_5d | 55.6 | 50.5 | 50.5 | with | 55.6 / 50.5 |
| 31 | CCI (15m to daily) | cci_1h | 52.9 | 50.5 | 50.5 | with | 52.9 / 50.5 |
| 32 | Pivot points (daily and weekly) | pvt_cam_wk | 49.5 | 48.3 | 50.5 | against | 49.5 / 48.3 |
| 33 | Parabolic SAR (15m to daily) | psar_1d | 51.0 | 50.5 | 50.5 | with | 51.0 / 50.5 |
| 34 | TRIX (1h to daily) | trixx_1h | 50.8 | 50.5 | 50.5 | with | 50.8 / 50.5 |
| 35 | Fisher Transform (15m to 4h) | fishx_1h | 50.5 | 50.6 | 50.5 | with | 50.5 / 50.6 |
| 36 | Supertrend (15m to daily) | os_st_4h | 49.6 | 49.6 | 50.4 | against | 49.6 / 49.6 |
| 37 | RSI divergence (15m to 4h) | rdiv_15m | 49.7 | 49.1 | 50.3 | against | 49.7 / 49.1 |
| 38 | News and economic events | S&P 500, 5-day move | 45.2 | 49.8 | 50.2 | against | 45.2 / 49.8 |
| 39 | Williams %R (15m to daily) | wr_1d | 55.4 | 50.1 | 50.1 | with | 55.4 / 50.1 |
| 40 | Kronos forecast | - | - | - | - | no history yet | - |
| 41 | Money Flow Index (15m to daily) | - | - | - | - | no history yet | - |
| 42 | Volume profile (session and 7 days) | - | - | - | - | no history yet | - |
| 43 | Chaikin money flow and OBV (1h to daily) | - | - | - | - | no history yet | - |
