# Card rating: metals (XAUUSD, XAGUSD)

Method of research/exp_memory.py: per card its steadiest raw reading (the sign of the reading in its most extreme fifth as a call of direction, on calls the triple barrier graded up or down), first half vs second half. Combined score = the worse half in the reading's own direction (50 + steady). In-sample history; a rating ranks cards, it proves no edge.

- window 2020-01-01 23:00 .. 2026-11-11 10:30 UTC, halves split at 2023-06-11 22:45; horizon 96 sessions; 316096 graded rows (XAUUSD 158321, XAGUSD 157775); up 50.3%
- voting (worse half > 50.5%, top 10, at least 3): Volatility gauges, Ichimoku cloud, Momentum and stretch, Gold and silver ETF holdings, Market structure, Timeframe strength, Regime, Kaufman adaptive average (KAMA), News and economic events, Moving averages (SMA and EMA 5-200)
- voting voices: volx, ichimoku, momentum, meanrev, pullback, goldetf, structure, trend, regime, kama, news, macro, mavg, owner
- built in 195.4s, peak 658 MB

| # | card | steadiest reading | 1st half | 2nd half | worse half | direction | XAUUSD (1st / 2nd) | XAGUSD (1st / 2nd) |
|---|---|---|---|---|---|---|---|---|
| 1 | Volatility gauges (votes) | vx_gold | 52.2 | 53.0 | 52.2 | with | 51.5 / 53.4 | 52.9 / 52.6 |
| 2 | Ichimoku cloud (votes) | ich_lag_1h | 51.9 | 52.9 | 51.9 | with | 51.1 / 54.4 | 52.9 / 51.2 |
| 3 | Momentum and stretch (votes) | last 24 hours' move | 51.7 | 53.0 | 51.7 | with | 51.5 / 53.9 | 51.9 / 51.9 |
| 4 | Gold and silver ETF holdings (votes) | ge_gld_5d | 53.7 | 51.6 | 51.6 | with | 53.3 / 54.6 | 54.0 / 48.5 |
| 5 | Market structure (votes) | ms_pos_4h | 52.3 | 51.6 | 51.6 | with | 51.7 / 53.2 | 53.0 / 49.9 |
| 6 | Timeframe strength (votes) | 4h trend | 54.2 | 51.5 | 51.5 | with | 53.1 / 54.2 | 55.3 / 48.6 |
| 7 | Regime (votes) | regime MOMENTUM_DOWN | 53.6 | 51.3 | 51.3 | with | - | 54.7 / 53.6 |
| 8 | Kaufman adaptive average (KAMA) (votes) | kama_pos_4h | 51.3 | 53.2 | 51.3 | with | 51.0 / 55.2 | 51.7 / 51.0 |
| 9 | News and economic events (votes) | a US release just printed | 47.9 | 48.7 | 51.3 | against | 48.6 / 49.3 | 47.2 / 48.1 |
| 10 | Moving averages (SMA and EMA 5-200) (votes) | ma_share_4h | 51.8 | 51.3 | 51.3 | with | 51.3 / 52.8 | 52.4 / 49.7 |
| 11 | Moving-average ribbon | rb_gmma_1h | 51.2 | 52.4 | 51.2 | with | 50.9 / 53.3 | 51.6 / 51.3 |
| 12 | Moving averages as support and resistance | mas_room_4h | 52.4 | 51.1 | 51.1 | with | 52.8 / 53.1 | 52.1 / 49.1 |
| 13 | Time and session | ck_weekend | 48.9 | 48.6 | 51.1 | against | 47.5 / 45.0 | 50.2 / 52.4 |
| 14 | Futures positioning (CFTC) | cot_level | 51.0 | 53.5 | 51.0 | with | 56.3 / 54.3 | 43.7 / 45.7 |
| 15 | Trade setups | su_pullback | 48.0 | 49.1 | 50.9 | against | 47.7 / 49.8 | 48.3 / 48.2 |
| 16 | Fibonacci retracement | fib_gz_4h | 46.4 | 49.2 | 50.8 | against | 45.9 / 51.9 | 46.7 / 46.5 |
| 17 | Metals ratios | mt_lead_24h | 50.8 | 53.0 | 50.8 | with | 51.0 / 53.1 | 50.6 / 52.9 |
| 18 | Support and resistance | strength of the resistance above | 50.8 | 51.8 | 50.8 | with | 52.4 / 55.2 | 49.3 / 48.9 |
| 19 | Intraday levels (VWAP and opening range) | id_vwap_d | 50.8 | 51.1 | 50.8 | with | 51.2 / 50.8 | 50.4 / 51.3 |
| 20 | Working strategies | 30-day momentum strategy | 50.9 | 50.8 | 50.8 | with | 51.0 / 53.1 | 50.7 / 48.1 |
| 21 | Candle size and realistic targets | cs_reach_rel | 50.7 | 53.5 | 50.7 | with | 51.1 / 53.5 | 50.2 / 53.4 |
| 22 | Hull moving average | hull_pos_1h | 50.5 | 51.6 | 50.5 | with | 51.3 / 52.4 | 49.7 / 50.7 |
| 23 | Trend quality and squeeze | tq_macd_1h | 50.5 | 51.2 | 50.5 | with | 51.4 / 51.9 | 49.6 / 50.5 |
| 24 | Rates and the dollar | rt_y2_5d | 48.1 | 50.2 | 50.0 | against | 48.8 / 48.6 | 47.5 / 51.8 |
| 25 | Kronos forecast | - | - | - | - | no history yet | - | - |
