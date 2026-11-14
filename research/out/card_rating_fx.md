# Card rating: fx (USDJPY)

Method of research/exp_memory.py: per card its steadiest raw reading (the sign of the reading in its most extreme fifth as a call of direction, on calls the triple barrier graded up or down), first half vs second half. Combined score = the worse half in the reading's own direction (50 + steady). In-sample history; a rating ranks cards, it proves no edge.

- window 2020-01-01 22:00 .. 2026-11-11 11:30 UTC, halves split at 2023-06-01 00:00; horizon 96 sessions; 166396 graded rows (USDJPY 166396); up 50.9%
- voting (worse half > 50.5%, top 10, at least 3): Trade setups, Regime, Working strategies, Time and session, Moving averages (SMA and EMA 5-200), Rates and the dollar, Trend quality and squeeze, Momentum and stretch, Support and resistance, Timeframe strength
- voting voices: setups, regime, strategies, clock, mavg, rates, trendq, momentum, meanrev, pullback, levels, trend, owner
- built in 85.4s, peak 532 MB

| # | card | steadiest reading | 1st half | 2nd half | worse half | direction | USDJPY (1st / 2nd) |
|---|---|---|---|---|---|---|---|
| 1 | Trade setups (votes) | su_rangefade | 42.6 | 37.7 | 57.4 | against | 42.6 / 37.7 |
| 2 | Regime (votes) | regime TREND_DOWN | 55.0 | 53.8 | 53.8 | with | 55.0 / 53.8 |
| 3 | Working strategies (votes) | StochRSI core zone | 53.8 | 53.3 | 53.3 | with | 53.8 / 53.3 |
| 4 | Time and session (votes) | ck_dow_cos | 53.9 | 52.7 | 52.7 | with | 53.9 / 52.7 |
| 5 | Moving averages (SMA and EMA 5-200) (votes) | ma_cross_1d | 46.7 | 47.5 | 52.5 | against | 46.7 / 47.5 |
| 6 | Rates and the dollar (votes) | rt_gap_5d | 53.6 | 52.3 | 52.3 | with | 53.6 / 52.3 |
| 7 | Trend quality and squeeze (votes) | tq_adx_1h | 48.0 | 44.9 | 52.0 | against | 48.0 / 44.9 |
| 8 | Momentum and stretch (votes) | 1h StochRSI | 52.6 | 52.0 | 52.0 | with | 52.6 / 52.0 |
| 9 | Support and resistance (votes) | resistance is close | 51.8 | 52.5 | 51.8 | with | 51.8 / 52.5 |
| 10 | Timeframe strength (votes) | weekly trend | 51.7 | 55.7 | 51.7 | with | 51.7 / 55.7 |
| 11 | Futures positioning (CFTC) | cot_pctile | 53.9 | 51.7 | 51.7 | with | 53.9 / 51.7 |
| 12 | Intraday levels (VWAP and opening range) | id_band | 53.2 | 51.7 | 51.7 | with | 53.2 / 51.7 |
| 13 | Japan watch | jp_boj_next | 53.0 | 51.7 | 51.7 | with | 53.0 / 51.7 |
| 14 | Candle size and realistic targets | cs_reach_rel | 48.6 | 48.6 | 51.4 | against | 48.6 / 48.6 |
| 15 | Volatility gauges | vx_front | 47.6 | 49.0 | 51.0 | against | 47.6 / 49.0 |
| 16 | Market structure | ms_pos_1h | 53.8 | 50.9 | 50.9 | with | 53.8 / 50.9 |
| 17 | News and economic events | a US release just printed | 50.9 | 51.4 | 50.9 | with | 50.9 / 51.4 |
| 18 | Kaufman adaptive average (KAMA) | kama_slope_4h | 47.8 | 49.2 | 50.8 | against | 47.8 / 49.2 |
| 19 | Fibonacci retracement | fib_depth_1h | 48.2 | 49.4 | 50.6 | against | 48.2 / 49.4 |
| 20 | Hull moving average | hull_pos_1h | 51.5 | 50.6 | 50.6 | with | 51.5 / 50.6 |
| 21 | Ichimoku cloud | ich_cloud_4h | 50.5 | 52.7 | 50.5 | with | 50.5 / 52.7 |
| 22 | Moving averages as support and resistance | mas_test_1h | 49.4 | 49.5 | 50.5 | against | 49.4 / 49.5 |
| 23 | Moving-average ribbon | rb_order_15m | 51.3 | 50.3 | 50.3 | with | 51.3 / 50.3 |
| 24 | Kronos forecast | - | - | - | - | no history yet | - |
