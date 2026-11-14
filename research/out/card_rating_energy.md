# Card rating: energy (WTI, BRENT)

Method of research/exp_memory.py: per card its steadiest raw reading (the sign of the reading in its most extreme fifth as a call of direction, on calls the triple barrier graded up or down), first half vs second half. Combined score = the worse half in the reading's own direction (50 + steady). In-sample history; a rating ranks cards, it proves no edge.

- window 2020-01-02 01:00 .. 2026-11-11 11:00 UTC, halves split at 2023-06-07 10:00; horizon 96 sessions; 291622 graded rows (WTI 145763, BRENT 145859); up 50.8%
- voting (worse half > 50.5%, top 10, at least 3): Oil volatility, Regime, Trade setups, WTI-Brent and curve, Fibonacci retracement, Moving averages (SMA and EMA 5-200), Support and resistance, Kaufman adaptive average (KAMA), Candle size and realistic targets, Trend quality and squeeze
- voting voices: oilvol, regime, setups, oilspread, fib, mavg, levels, kama, candles, trendq, owner
- built in 154.2s, peak 622 MB

| # | card | steadiest reading | 1st half | 2nd half | worse half | direction | WTI (1st / 2nd) | BRENT (1st / 2nd) |
|---|---|---|---|---|---|---|---|---|
| 1 | Oil volatility (votes) | ovol_chg5 | 47.3 | 46.0 | 52.7 | against | 47.5 / 46.0 | 47.1 / 45.9 |
| 2 | Regime (votes) | regime MOMENTUM_DOWN | 52.3 | 55.4 | 52.3 | with | 54.6 / 53.6 | 50.0 / 57.6 |
| 3 | Trade setups (votes) | su_rangefade | 52.2 | 58.7 | 52.2 | with | 49.4 / 60.5 | 54.6 / 57.3 |
| 4 | WTI-Brent and curve (votes) | ospr_curve | 48.1 | 42.5 | 51.9 | against | 48.1 / 42.9 | - |
| 5 | Fibonacci retracement (votes) | fib_gz_1h | 48.4 | 47.3 | 51.6 | against | 48.5 / 46.8 | 48.3 / 47.8 |
| 6 | Moving averages (SMA and EMA 5-200) (votes) | ma_cross_1d | 51.5 | 51.6 | 51.5 | with | 52.4 / 50.2 | 50.5 / 52.8 |
| 7 | Support and resistance (votes) | support is close | 51.4 | 51.5 | 51.4 | with | 51.3 / 52.3 | 51.5 / 50.7 |
| 8 | Kaufman adaptive average (KAMA) (votes) | kama_er_4h | 48.8 | 48.2 | 51.2 | against | 50.3 / 48.3 | 47.2 / 48.1 |
| 9 | Candle size and realistic targets (votes) | cs_reach_rel | 48.9 | 48.3 | 51.1 | against | 49.5 / 48.5 | 48.3 / 48.1 |
| 10 | Trend quality and squeeze (votes) | tq_bbw | 49.0 | 47.4 | 51.0 | against | 49.4 / 47.2 | 48.7 / 47.6 |
| 11 | Crude futures positioning (CFTC) | opos_pctile | 48.0 | 49.0 | 51.0 | against | 51.1 / 49.7 | 45.5 / 48.2 |
| 12 | EIA crude inventories | eia_crude | 49.1 | 46.0 | 50.9 | against | 49.1 / 45.8 | 49.0 / 46.2 |
| 13 | Ichimoku cloud | ich_tk_4h | 49.1 | 47.0 | 50.9 | against | 50.1 / 47.4 | 48.1 / 46.6 |
| 14 | Moving-average ribbon | rb_pos_1h | 50.8 | 51.0 | 50.8 | with | 50.7 / 51.5 | 50.8 / 50.5 |
| 15 | Intraday levels (VWAP and opening range) | id_vwap_d | 52.2 | 50.7 | 50.7 | with | 52.2 / 51.2 | 52.2 / 50.2 |
| 16 | Time and session | ck_us_open_in | 51.6 | 50.7 | 50.7 | with | 51.3 / 50.7 | 51.8 / 50.6 |
| 17 | Momentum and stretch | 4h StochRSI | 48.6 | 49.3 | 50.7 | against | 49.1 / 49.7 | 48.1 / 49.0 |
| 18 | Market structure | ms_agree | 49.3 | 48.9 | 50.7 | against | 49.2 / 49.0 | 49.4 / 48.8 |
| 19 | Moving averages as support and resistance | mas_hold_1h | 50.6 | 51.0 | 50.6 | with | 49.7 / 50.0 | 51.7 / 52.1 |
| 20 | Hull moving average | hull_pos_15m | 49.5 | 49.6 | 50.4 | against | 49.9 / 49.6 | 49.0 / 49.5 |
| 21 | News and economic events | dollar index, 5-day move | 49.7 | 48.5 | 50.3 | against | 49.7 / 48.9 | 49.8 / 48.1 |
| 22 | Working strategies | 30-day momentum strategy | 51.4 | 50.3 | 50.3 | with | 51.2 / 51.2 | 51.6 / 49.5 |
| 23 | OPEC+ calendar | opec_week | 60.0 | 46.7 | 50.0 | with | 60.4 / 46.9 | 59.5 / 46.5 |
| 24 | Timeframe strength | 15m trend | 50.5 | 49.1 | 50.0 | with | 51.1 / 49.2 | 49.8 / 49.0 |
| 25 | Kronos forecast | - | - | - | - | no history yet | - | - |
