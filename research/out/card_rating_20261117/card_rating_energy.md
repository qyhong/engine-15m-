# Card rating: energy (WTI, BRENT)

Method of research/exp_memory.py: per card its steadiest raw reading (the sign of the reading in its most extreme fifth as a call of direction, on calls the triple barrier graded up or down), first half vs second half. Combined score = the worse half in the reading's own direction (50 + steady). In-sample history; a rating ranks cards, it proves no edge.

- window 2020-01-02 01:00 .. 2025-11-10 21:45 UTC, halves split at 2022-12-07 21:45; horizon 96 sessions; 249569 graded rows (WTI 124767, BRENT 124802); up 50.7%
- voting (worse half > 50.5%, top 10, at least 3): Mass Index (1h to daily), Trade setups, Chaikin money flow and OBV (1h to daily), Oil volatility, Pivot points (daily and weekly), Linear-regression channel (1h to daily), Elder-Ray (1h to daily), Aroon and Vortex (1h to daily), Moving averages (SMA and EMA 5-200), Fibonacci retracement
- voting voices: mass, setups, cmf, oilvol, pivots, linreg, elder, aroon, mavg, fib, owner
- built in 748.1s, peak None MB

| # | card | steadiest reading | 1st half | 2nd half | worse half | direction | WTI (1st / 2nd) | BRENT (1st / 2nd) |
|---|---|---|---|---|---|---|---|---|
| 1 | Mass Index (1h to daily) (votes) | massb_4h | 43.9 | 25.8 | 56.1 | against | - | - |
| 2 | Trade setups (votes) | su_pullback | 45.3 | 45.4 | 54.6 | against | 45.0 / 43.7 | 45.7 / 47.0 |
| 3 | Chaikin money flow and OBV (1h to daily) (votes) | cmf_4h | 46.5 | 45.2 | 53.5 | against | 47.3 / 46.2 | 45.8 / 44.2 |
| 4 | Oil volatility (votes) | ovol_chg5 | 47.3 | 44.9 | 52.7 | against | 47.5 / 45.3 | 47.1 / 44.4 |
| 5 | Pivot points (daily and weekly) (votes) | pvt_cam_day | 53.6 | 52.7 | 52.7 | with | 53.8 / 51.7 | 53.5 / 53.6 |
| 6 | Linear-regression channel (1h to daily) (votes) | lrc_pos_1d | 47.6 | 47.9 | 52.1 | against | 47.6 / 48.4 | 47.6 / 47.5 |
| 7 | Elder-Ray (1h to daily) (votes) | eld_bull_1h | 52.7 | 52.0 | 52.0 | with | 52.9 / 52.4 | 52.4 / 51.7 |
| 8 | Aroon and Vortex (1h to daily) (votes) | vtx_1h | 52.3 | 52.0 | 52.0 | with | 52.9 / 51.7 | 51.7 / 52.2 |
| 9 | Moving averages (SMA and EMA 5-200) (votes) | ma_cross_1d | 51.8 | 52.0 | 51.8 | with | 52.0 / 50.1 | 51.7 / 53.8 |
| 10 | Fibonacci retracement (votes) | fib_gz_1h | 46.6 | 48.3 | 51.7 | against | 46.9 / 47.6 | 46.3 / 49.0 |
| 11 | Candle size and realistic targets | cs_reach_rel | 48.6 | 46.5 | 51.4 | against | 49.1 / 46.0 | 48.1 / 47.0 |
| 12 | Regime | regime MOMENTUM_DOWN | 52.3 | 51.4 | 51.4 | with | 55.2 / 51.6 | 49.5 / 51.2 |
| 13 | Momentum and stretch | last 24 hours' move | 51.3 | 51.5 | 51.3 | with | 50.6 / 51.0 | 51.9 / 52.0 |
| 14 | WTI-Brent and curve | ospr_curve | 48.8 | 42.6 | 51.2 | against | 48.8 / 42.6 | - |
| 15 | RSI divergence (15m to 4h) | rdiv_4h | 53.6 | 51.2 | 51.2 | with | 54.7 / 50.1 | 52.4 / 52.5 |
| 16 | Ultimate Oscillator (15m, 1h, daily) | uoz_1h | 48.8 | 48.5 | 51.2 | against | 50.6 / 48.0 | 47.4 / 49.0 |
| 17 | Moving-average ribbon | rb_width_15m | 52.3 | 51.1 | 51.1 | with | 52.9 / 51.4 | 51.7 / 50.8 |
| 18 | Support and resistance | support is close | 51.6 | 51.1 | 51.1 | with | 51.2 / 52.7 | 52.0 / 49.6 |
| 19 | Daily range budget and range breaks | adr_room_dn | 51.1 | 51.2 | 51.1 | with | 51.4 / 51.8 | 50.8 / 50.6 |
| 20 | Williams %R (15m to daily) | wr_4h | 49.0 | 47.6 | 51.0 | against | 50.1 / 47.6 | 47.9 / 47.7 |
| 21 | TRIX (1h to daily) | trixx_1h | 51.3 | 51.0 | 51.0 | with | 51.3 / 50.8 | 51.4 / 51.3 |
| 22 | CCI (15m to daily) | cci_4h | 51.0 | 51.1 | 51.0 | with | 51.1 / 50.1 | 51.0 / 52.1 |
| 23 | Money Flow Index (15m to daily) | mfi_1d | 49.1 | 46.4 | 50.9 | against | 47.6 / 47.2 | 50.4 / 45.7 |
| 24 | Kaufman adaptive average (KAMA) | kama_er_1h | 52.5 | 50.9 | 50.9 | with | 52.8 / 51.0 | 52.2 / 50.9 |
| 25 | EIA crude inventories | eia_cushing | 52.3 | 50.9 | 50.9 | with | 52.2 / 51.6 | 52.4 / 50.1 |
| 26 | Market structure | ms_pos_4h | 50.9 | 51.1 | 50.9 | with | 51.7 / 50.1 | 50.2 / 52.0 |
| 27 | Fisher Transform (15m to 4h) | fish_4h | 49.2 | 48.1 | 50.8 | against | 50.8 / 49.1 | 47.5 / 47.1 |
| 28 | Crude futures positioning (CFTC) | opos_chg | 49.0 | 49.2 | 50.8 | against | 47.5 / 50.5 | 50.3 / 47.7 |
| 29 | Trend quality and squeeze | tq_rsi_1h | 51.1 | 50.7 | 50.7 | with | 51.8 / 50.8 | 50.3 / 50.6 |
| 30 | Moving averages as support and resistance | mas_room_4h | 51.1 | 50.7 | 50.7 | with | 51.1 / 51.8 | 51.1 / 49.6 |
| 31 | Ichimoku cloud | ich_lag_1h | 51.1 | 50.7 | 50.7 | with | 51.2 / 50.8 | 51.0 / 50.5 |
| 32 | StochRSI (15m to daily) | os_k_1d | 49.4 | 47.8 | 50.6 | against | 48.6 / 49.2 | 50.2 / 46.4 |
| 33 | Intraday levels (VWAP and opening range) | id_or | 50.6 | 50.9 | 50.6 | with | 50.8 / 50.5 | 50.2 / 51.6 |
| 34 | News and economic events | dollar index, 5-day move | 49.5 | 48.6 | 50.5 | against | 49.4 / 48.8 | 49.6 / 48.3 |
| 35 | Hull moving average | hull_pos_15m | 49.5 | 49.2 | 50.5 | against | 50.0 / 49.4 | 49.1 / 49.1 |
| 36 | Time and session | ck_dow_cos | 49.5 | 49.6 | 50.4 | against | 49.4 / 49.2 | 49.5 / 50.0 |
| 37 | Volume profile (session and 7 days) | vpf_pos_day | 51.7 | 50.1 | 50.1 | with | 52.1 / 50.4 | 51.2 / 49.8 |
| 38 | Heikin-Ashi trend (15m to 4h) | ha_run_4h | 49.0 | 49.9 | 50.1 | against | 49.7 / 50.9 | 48.2 / 48.8 |
| 39 | Supertrend (15m to daily) | os_st_15m | 50.1 | 50.3 | 50.1 | with | 50.2 / 50.9 | 50.0 / 49.7 |
| 40 | OPEC+ calendar | opec_week | 59.7 | 47.7 | 50.0 | with | 60.1 / 48.0 | 59.3 / 47.5 |
| 41 | Working strategies | StochRSI core zone | 49.0 | 52.2 | 50.0 | against | 48.1 / 51.4 | 50.0 / 53.0 |
| 42 | Timeframe strength | 15m trend | 50.5 | 48.9 | 50.0 | with | 51.2 / 49.0 | 49.8 / 48.9 |
| 43 | Parabolic SAR (15m to daily) | psar_15m | 50.0 | 49.6 | 50.0 | against | 50.1 / 49.6 | 49.8 / 49.6 |
| 44 | Kronos forecast | - | - | - | - | no history yet | - | - |
