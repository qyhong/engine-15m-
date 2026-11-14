# Card rating: index (SPX)

Method of research/exp_memory.py: per card its steadiest raw reading (the sign of the reading in its most extreme fifth as a call of direction, on calls the triple barrier graded up or down), first half vs second half. Combined score = the worse half in the reading's own direction (50 + steady). In-sample history; a rating ranks cards, it proves no edge.

- window 2020-01-02 14:30 .. 2026-11-10 20:45 UTC, halves split at 2023-05-23 19:15; horizon 26 sessions; 31352 graded rows (SPX 31352); up 51.7%
- voting (worse half > 50.5%, top 10, at least 3): Trade setups, News and economic events, Moving averages (SMA and EMA 5-200), S&P futures overnight, Trend quality and squeeze, Support and resistance, Regime, Intraday levels (VWAP and opening range), Fibonacci retracement, Rates and the dollar
- voting voices: setups, news, macro, mavg, overnight, trendq, levels, regime, intraday, fib, rates, owner
- built in 30.6s, peak 242 MB

| # | card | steadiest reading | 1st half | 2nd half | worse half | direction | SPX (1st / 2nd) |
|---|---|---|---|---|---|---|---|
| 1 | Trade setups (votes) | su_pullback | 58.6 | 59.4 | 58.6 | with | 58.6 / 59.4 |
| 2 | News and economic events (votes) | US 10-year yield, 5-day change | 44.2 | 44.6 | 55.4 | against | 44.2 / 44.6 |
| 3 | Moving averages (SMA and EMA 5-200) (votes) | ma_cross_1h | 56.2 | 55.3 | 55.3 | with | 56.2 / 55.3 |
| 4 | S&P futures overnight (votes) | on_pos | 54.1 | 53.4 | 53.4 | with | 54.1 / 53.4 |
| 5 | Trend quality and squeeze (votes) | tq_rsi_15m | 53.7 | 53.4 | 53.4 | with | 53.7 / 53.4 |
| 6 | Support and resistance (votes) | place in yesterday's range | 53.1 | 55.7 | 53.1 | with | 53.1 / 55.7 |
| 7 | Regime (votes) | regime TREND_UP | 52.8 | 55.1 | 52.8 | with | 52.8 / 55.1 |
| 8 | Intraday levels (VWAP and opening range) (votes) | id_vwap_w | 52.7 | 53.3 | 52.7 | with | 52.7 / 53.3 |
| 9 | Fibonacci retracement (votes) | fib_room_1h | 45.0 | 47.4 | 52.6 | against | 45.0 / 47.4 |
| 10 | Rates and the dollar (votes) | rt_y2_5d | 46.1 | 47.4 | 52.6 | against | 46.1 / 47.4 |
| 11 | Stock-market breadth | eb_rsp_20d | 45.3 | 47.8 | 52.2 | against | 45.3 / 47.8 |
| 12 | Kaufman adaptive average (KAMA) | kama_er_15m | 54.4 | 52.1 | 52.1 | with | 54.4 / 52.1 |
| 13 | Time and session | ck_hour_sin | 48.1 | 47.2 | 51.9 | against | 48.1 / 47.2 |
| 14 | Moving-average ribbon | rb_expand_15m | 51.7 | 52.8 | 51.7 | with | 51.7 / 52.8 |
| 15 | Moving averages as support and resistance | mas_hold_1h | 48.6 | 47.1 | 51.4 | against | 48.6 / 47.1 |
| 16 | Momentum and stretch | 1h StochRSI | 51.3 | 53.2 | 51.3 | with | 51.3 / 53.2 |
| 17 | Working strategies | BTC 120-day trend | 51.2 | 51.8 | 51.2 | with | 51.2 / 51.8 |
| 18 | Candle size and realistic targets | cs_reach_rel | 51.2 | 51.4 | 51.2 | with | 51.2 / 51.4 |
| 19 | Ichimoku cloud | ich_lag_4h | 48.9 | 48.1 | 51.1 | against | 48.9 / 48.1 |
| 20 | Market structure | ms_1d | 51.6 | 51.1 | 51.1 | with | 51.6 / 51.1 |
| 21 | Futures positioning (CFTC) | cot_pctile | 49.1 | 45.4 | 50.9 | against | 49.1 / 45.4 |
| 22 | Timeframe strength | 4h trend | 50.7 | 51.8 | 50.7 | with | 50.7 / 51.8 |
| 23 | Megacap earnings | ern_next | 49.6 | 48.8 | 50.4 | against | 49.6 / 48.8 |
| 24 | Hull moving average | hull_x_15m | 50.3 | 51.2 | 50.3 | with | 50.3 / 51.2 |
| 25 | Volatility gauges | vx_level | 45.6 | 55.0 | 50.0 | against | 45.6 / 55.0 |
| 26 | Kronos forecast | - | - | - | - | no history yet | - |
| 27 | Options mood (put/call) | pc_total | - | - | - | too little history | - |
