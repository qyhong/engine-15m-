# Card rating of 2026-11-17: every card, the new batches included

Card pipeline step 3 (research/CARD_PIPELINE.md), engine think15-v5.2.4. The existing method, unchanged (research/rate_cards.py, run through research/rate_cards_snapshot.py): per card its steadiest raw reading; the sign of that reading in its most extreme fifth as a call of direction, on the calls the engine's triple barrier graded up or down; accuracy in the first and in the second half of history. A card's rating is its WORSE half, in the reading's own direction.

**This is in-sample history and it ranks cards; it proves no edge.** All of this history has been looked at before. The halves are a few points from 50% at best; differences of a few tenths between neighbours are noise. **Nothing here is a proposal to change which cards vote.** Step 5 of the pipeline needs, besides this rating, a 30-day forward check and the owner's yes.

Differences from the rating of 11 Nov 2026 that the page shows (research/out/card_rating_<group>.json, left untouched): history stops before the sealed holdout (2025-11-11), where the 11 Nov rating ran to 11 Nov 2026, so the halves split earlier and the numbers are not directly comparable; and the engine now reads the cards of eight more batches.

## crypto (BTCUSDT, ETHUSDT)

- History 2020-01-01 00:00 .. 2025-11-10 23:45 UTC, halves split at 2022-11-30 20:30 (the method's own split: the median graded call); horizon 96 sessions; 390670 graded calls (BTCUSDT 193571, ETHUSDT 197099); 50.3% of them up.
- 61 cards rated. Current voting cards (10, config.voting_by_group; the owner's voice aside): Momentum and stretch (#4), Support and resistance (#6), Coinbase premium (#9), Order flow (CVD) (#21), Timeframe strength (#28), Market breadth and ETH/BTC (#30), Perp basis and premium (#31), Working strategies (#37), Regime (#44), Stablecoin supply (#46).

| # | card | votes now | new | steadiest reading | 1st half | 2nd half | worse half | direction | # on 11 Nov |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Pivot points (daily and weekly) |  | osc4 | pvt_cam_day | 57.6 | 54.8 | 54.8 | with | new |
| 2 | Moving-average ribbon |  |  | rb_gmma_1h | 54.4 | 54.6 | 54.4 | with | 2 |
| 3 | Trend quality and squeeze |  |  | tq_rsi_1h | 55.2 | 54.1 | 54.1 | with | 3 |
| 4 | Momentum and stretch | yes |  | stretch from the 1h average | 55.7 | 53.9 | 53.9 | with | 4 |
| 5 | News and economic events |  |  | a US release is near | 53.9 | 53.9 | 53.9 | with | 11 |
| 6 | Support and resistance | yes |  | place in yesterday's range | 55.3 | 53.7 | 53.7 | with | 5 |
| 7 | Market structure |  |  | ms_pos_4h | 54.8 | 53.7 | 53.7 | with | 12 |
| 8 | Aroon and Vortex (1h to daily) |  | osc2 | vtx_1h | 56.9 | 53.6 | 53.6 | with | new |
| 9 | Coinbase premium | yes |  | cbp_z | 55.1 | 53.4 | 53.4 | with | 6 |
| 10 | Kaufman adaptive average (KAMA) |  |  | kama_er_1h | 54.5 | 53.4 | 53.4 | with | 7 |
| 11 | Linear-regression channel (1h to daily) |  | osc5 | lrc_slope_1h | 53.3 | 53.4 | 53.3 | with | new |
| 12 | CCI (15m to daily) |  | osc3 | cci_4h | 54.5 | 53.2 | 53.2 | with | new |
| 13 | Money Flow Index (15m to daily) |  | osc2 | mfi_1h | 55.5 | 53.0 | 53.0 | with | new |
| 14 | Fisher Transform (15m to 4h) |  | osc5 | fishext_1h | 54.4 | 53.0 | 53.0 | with | new |
| 15 | Ichimoku cloud |  |  | ich_lag_1h | 54.8 | 52.8 | 52.8 | with | 10 |
| 16 | Elder-Ray (1h to daily) |  | osc4 | eld_bull_1h | 54.4 | 52.8 | 52.8 | with | new |
| 17 | Volume profile (session and 7 days) |  | osc2 | vpf_poc_7d | 52.8 | 54.0 | 52.8 | with | new |
| 18 | StochRSI (15m to daily) |  | osc | os_k_1h | 52.8 | 52.6 | 52.6 | with | new |
| 19 | Moving averages (SMA and EMA 5-200) |  |  | ma_cross_4h | 56.3 | 52.5 | 52.5 | with | 9 |
| 20 | Cross-exchange funding and OI |  | cryptox | xf_avg | 47.5 | 46.9 | 52.5 | against | new |
| 21 | Order flow (CVD) | yes |  | 4h order flow (CVD) | 52.5 | 52.8 | 52.5 | with | 13 |
| 22 | Intraday levels (VWAP and opening range) |  |  | id_vwap_w | 52.4 | 54.0 | 52.4 | with | 8 |
| 23 | Heikin-Ashi trend (15m to 4h) |  | osc2 | ha_run_1h | 52.3 | 52.6 | 52.3 | with | new |
| 24 | BTC dominance |  | cryptox | dm_btc_7d | 52.2 | 56.9 | 52.2 | with | new |
| 25 | Ultimate Oscillator (15m, 1h, daily) |  | osc5 | uoz_1h | 54.4 | 52.2 | 52.2 | with | new |
| 26 | TRIX (1h to daily) |  | osc5 | trix_1h | 53.5 | 52.2 | 52.2 | with | new |
| 27 | Supertrend (15m to daily) |  | osc | os_st_agree | 53.3 | 52.2 | 52.2 | with | new |
| 28 | Timeframe strength | yes |  | 15m trend | 52.2 | 52.6 | 52.2 | with | 15 |
| 29 | RSI divergence (15m to 4h) |  | osc4 | rdiv_15m | 47.3 | 47.9 | 52.1 | against | new |
| 30 | Market breadth and ETH/BTC | yes |  | brd_ethbtc_7d | 48.0 | 45.8 | 52.0 | against | 14 |
| 31 | Perp basis and premium | yes |  | pb_level | 48.5 | 47.9 | 51.5 | against | 20 |
| 32 | Funding and positioning |  |  | funding rate | 48.5 | 48.3 | 51.5 | against | 25 |
| 33 | Moving averages as support and resistance |  |  | mas_hold_1h | 48.3 | 48.6 | 51.4 | against | 21 |
| 34 | Williams %R (15m to daily) |  | osc4 | wr_1h | 51.6 | 51.4 | 51.4 | with | new |
| 35 | Korea premium |  | cryptox | kp_z30 | 48.6 | 48.6 | 51.4 | against | new |
| 36 | Binance positioning (archive) |  | flows | fl_ls_global_z | 45.6 | 48.7 | 51.3 | against | new |
| 37 | Working strategies | yes |  | StochRSI core zone | 48.7 | 47.1 | 51.3 | against | 16 |
| 38 | Options flow (Deribit) |  | cryptox | of_block_bear_7d | 51.1 | 51.4 | 51.1 | with | new |
| 39 | Trade setups |  |  | su_trap | 52.6 | 51.0 | 51.0 | with | 18 |
| 40 | Hull moving average |  |  | hull_pos_1h | 51.4 | 51.0 | 51.0 | with | 22 |
| 41 | On-chain activity and flows |  | flows | fl_netflow_7d | 49.1 | 46.9 | 50.9 | against | new |
| 42 | Daily range budget and range breaks |  | adr | adr_pos | 51.3 | 50.9 | 50.9 | with | new |
| 43 | Chaikin money flow and OBV (1h to daily) |  | osc4 | obvdiv_1d | 50.8 | 52.3 | 50.8 | with | new |
| 44 | Regime | yes |  | regime MOMENTUM_DOWN | 44.6 | 49.3 | 50.7 | against | 1 |
| 45 | Mass Index (1h to daily) |  | osc5 | massb_1d | 49.3 | 47.5 | 50.7 | against | new |
| 46 | Stablecoin supply | yes |  | stb_7d | 51.4 | 50.7 | 50.7 | with | 17 |
| 47 | Time and session |  |  | ck_dow_cos | 50.5 | 50.7 | 50.5 | with | 23 |
| 48 | Parabolic SAR (15m to daily) |  | osc2 | psar_1h | 50.4 | 51.2 | 50.4 | with | new |
| 49 | Fibonacci retracement |  |  | fib_depth_4h | 47.0 | 49.7 | 50.3 | against | 19 |
| 50 | Options: implied volatility and skew |  |  | op_dvol_24h | 50.2 | 52.1 | 50.2 | with | 24 |
| 51 | CME gap (spot proxy) |  | cryptox | cg_open | 49.3 | 52.6 | 50.0 | against | new |
| 52 | Candle size and realistic targets |  |  | cs_used | 52.5 | 49.2 | 50.0 | with | 26 |
| 53 | Spot vs perp leadership |  | cryptox | sl_share_z | 48.6 | 51.9 | 50.0 | against | new |
| 54 | Bitfinex margin positions |  | flows | fl_bfx_14d | 50.6 | 48.1 | 50.0 | with | new |
| 55 | Fear and Greed |  |  | fng_level | 51.0 | 48.6 | 50.0 | with | 27 |
| 56 | CME futures positioning (CFTC) |  | flows | fl_cme_lev_z | 48.8 | 50.1 | 50.0 | against | new |
| 57 | Liquidity (order book) |  |  | - | - | - | - | no history yet | 28 |
| 58 | Kronos forecast |  |  | - | - | - | - | no history yet | 29 |
| 59 | Long/short positioning |  |  | - | - | - | - | no history yet | 30 |
| 60 | Liquidation pressure (proxy) |  |  | - | - | - | - | no history yet | 31 |
| 61 | Spot ETF flows |  |  | etf_1d | - | - | - | too little history | 32 |

**Where the new batches landed (crypto, of 61 cards):**

| batch | card | # | 1st half | 2nd half | worse half | direction |
|---|---|---|---|---|---|---|
| flows: batch 0, crypto positioning and on-chain (v5.1.1) | Binance positioning (archive) | 36 | 45.6 | 48.7 | 51.3 | against |
| flows: batch 0, crypto positioning and on-chain (v5.1.1) | On-chain activity and flows | 41 | 49.1 | 46.9 | 50.9 | against |
| flows: batch 0, crypto positioning and on-chain (v5.1.1) | Bitfinex margin positions | 54 | 50.6 | 48.1 | 50.0 | with |
| flows: batch 0, crypto positioning and on-chain (v5.1.1) | CME futures positioning (CFTC) | 56 | 48.8 | 50.1 | 50.0 | against |
| osc: batch 1 (v5.1.2) | StochRSI (15m to daily) | 18 | 52.8 | 52.6 | 52.6 | with |
| osc: batch 1 (v5.1.2) | Supertrend (15m to daily) | 27 | 53.3 | 52.2 | 52.2 | with |
| osc2: batch 2 (v5.1.2) | Aroon and Vortex (1h to daily) | 8 | 56.9 | 53.6 | 53.6 | with |
| osc2: batch 2 (v5.1.2) | Money Flow Index (15m to daily) | 13 | 55.5 | 53.0 | 53.0 | with |
| osc2: batch 2 (v5.1.2) | Volume profile (session and 7 days) | 17 | 52.8 | 54.0 | 52.8 | with |
| osc2: batch 2 (v5.1.2) | Heikin-Ashi trend (15m to 4h) | 23 | 52.3 | 52.6 | 52.3 | with |
| osc2: batch 2 (v5.1.2) | Parabolic SAR (15m to daily) | 48 | 50.4 | 51.2 | 50.4 | with |
| osc3: batch 2b, CCI (v5.2.1) | CCI (15m to daily) | 12 | 54.5 | 53.2 | 53.2 | with |
| cryptox: batch 3c, crypto (v5.2.2) | Cross-exchange funding and OI | 20 | 47.5 | 46.9 | 52.5 | against |
| cryptox: batch 3c, crypto (v5.2.2) | BTC dominance | 24 | 52.2 | 56.9 | 52.2 | with |
| cryptox: batch 3c, crypto (v5.2.2) | Korea premium | 35 | 48.6 | 48.6 | 51.4 | against |
| cryptox: batch 3c, crypto (v5.2.2) | Options flow (Deribit) | 38 | 51.1 | 51.4 | 51.1 | with |
| cryptox: batch 3c, crypto (v5.2.2) | CME gap (spot proxy) | 51 | 49.3 | 52.6 | 50.0 | against |
| cryptox: batch 3c, crypto (v5.2.2) | Spot vs perp leadership | 53 | 48.6 | 51.9 | 50.0 | against |
| adr: daily range budget (v5.2.3) | Daily range budget and range breaks | 42 | 51.3 | 50.9 | 50.9 | with |
| osc4: batch 3 (v5.2.3) | Pivot points (daily and weekly) | 1 | 57.6 | 54.8 | 54.8 | with |
| osc4: batch 3 (v5.2.3) | Elder-Ray (1h to daily) | 16 | 54.4 | 52.8 | 52.8 | with |
| osc4: batch 3 (v5.2.3) | RSI divergence (15m to 4h) | 29 | 47.3 | 47.9 | 52.1 | against |
| osc4: batch 3 (v5.2.3) | Williams %R (15m to daily) | 34 | 51.6 | 51.4 | 51.4 | with |
| osc4: batch 3 (v5.2.3) | Chaikin money flow and OBV (1h to daily) | 43 | 50.8 | 52.3 | 50.8 | with |
| osc5: batch 4 (v5.2.4) | Linear-regression channel (1h to daily) | 11 | 53.3 | 53.4 | 53.3 | with |
| osc5: batch 4 (v5.2.4) | Fisher Transform (15m to 4h) | 14 | 54.4 | 53.0 | 53.0 | with |
| osc5: batch 4 (v5.2.4) | Ultimate Oscillator (15m, 1h, daily) | 25 | 54.4 | 52.2 | 52.2 | with |
| osc5: batch 4 (v5.2.4) | TRIX (1h to daily) | 26 | 53.5 | 52.2 | 52.2 | with |
| osc5: batch 4 (v5.2.4) | Mass Index (1h to daily) | 45 | 49.3 | 47.5 | 50.7 | against |

**Weakest current voter (crypto):** Stablecoin supply, #46 of 61 (halves 51.4 / 50.7, worse half 50.7, with).

Non-voting cards rated above it (36); those marked **both** also beat it in EACH half separately (in their own direction: 29). These are candidates for the pipeline's step 5 only; nothing is proposed.

| # | card | new | 1st half | 2nd half | worse half | direction | above it in both halves |
|---|---|---|---|---|---|---|---|
| 1 | Pivot points (daily and weekly) | osc4 | 57.6 | 54.8 | 54.8 | with | **both** |
| 2 | Moving-average ribbon |  | 54.4 | 54.6 | 54.4 | with | **both** |
| 3 | Trend quality and squeeze |  | 55.2 | 54.1 | 54.1 | with | **both** |
| 5 | News and economic events |  | 53.9 | 53.9 | 53.9 | with | **both** |
| 7 | Market structure |  | 54.8 | 53.7 | 53.7 | with | **both** |
| 8 | Aroon and Vortex (1h to daily) | osc2 | 56.9 | 53.6 | 53.6 | with | **both** |
| 10 | Kaufman adaptive average (KAMA) |  | 54.5 | 53.4 | 53.4 | with | **both** |
| 11 | Linear-regression channel (1h to daily) | osc5 | 53.3 | 53.4 | 53.3 | with | **both** |
| 12 | CCI (15m to daily) | osc3 | 54.5 | 53.2 | 53.2 | with | **both** |
| 13 | Money Flow Index (15m to daily) | osc2 | 55.5 | 53.0 | 53.0 | with | **both** |
| 14 | Fisher Transform (15m to 4h) | osc5 | 54.4 | 53.0 | 53.0 | with | **both** |
| 15 | Ichimoku cloud |  | 54.8 | 52.8 | 52.8 | with | **both** |
| 16 | Elder-Ray (1h to daily) | osc4 | 54.4 | 52.8 | 52.8 | with | **both** |
| 17 | Volume profile (session and 7 days) | osc2 | 52.8 | 54.0 | 52.8 | with | **both** |
| 18 | StochRSI (15m to daily) | osc | 52.8 | 52.6 | 52.6 | with | **both** |
| 19 | Moving averages (SMA and EMA 5-200) |  | 56.3 | 52.5 | 52.5 | with | **both** |
| 20 | Cross-exchange funding and OI | cryptox | 47.5 | 46.9 | 52.5 | against | **both** |
| 22 | Intraday levels (VWAP and opening range) |  | 52.4 | 54.0 | 52.4 | with | **both** |
| 23 | Heikin-Ashi trend (15m to 4h) | osc2 | 52.3 | 52.6 | 52.3 | with | **both** |
| 24 | BTC dominance | cryptox | 52.2 | 56.9 | 52.2 | with | **both** |
| 25 | Ultimate Oscillator (15m, 1h, daily) | osc5 | 54.4 | 52.2 | 52.2 | with | **both** |
| 26 | TRIX (1h to daily) | osc5 | 53.5 | 52.2 | 52.2 | with | **both** |
| 27 | Supertrend (15m to daily) | osc | 53.3 | 52.2 | 52.2 | with | **both** |
| 29 | RSI divergence (15m to 4h) | osc4 | 47.3 | 47.9 | 52.1 | against | **both** |
| 32 | Funding and positioning |  | 48.5 | 48.3 | 51.5 | against | **both** |
| 33 | Moving averages as support and resistance |  | 48.3 | 48.6 | 51.4 | against | **both** |
| 34 | Williams %R (15m to daily) | osc4 | 51.6 | 51.4 | 51.4 | with | **both** |
| 35 | Korea premium | cryptox | 48.6 | 48.6 | 51.4 | against |  |
| 36 | Binance positioning (archive) | flows | 45.6 | 48.7 | 51.3 | against | **both** |
| 38 | Options flow (Deribit) | cryptox | 51.1 | 51.4 | 51.1 | with |  |
| 39 | Trade setups |  | 52.6 | 51.0 | 51.0 | with | **both** |
| 40 | Hull moving average |  | 51.4 | 51.0 | 51.0 | with |  |
| 41 | On-chain activity and flows | flows | 49.1 | 46.9 | 50.9 | against |  |
| 42 | Daily range budget and range breaks | adr | 51.3 | 50.9 | 50.9 | with |  |
| 43 | Chaikin money flow and OBV (1h to daily) | osc4 | 50.8 | 52.3 | 50.8 | with |  |
| 45 | Mass Index (1h to daily) | osc5 | 49.3 | 47.5 | 50.7 | against |  |

## metals (XAUUSD, XAGUSD)

- History 2020-01-01 23:00 .. 2025-11-10 23:45 UTC, halves split at 2022-12-07 12:30 (the method's own split: the median graded call); horizon 96 sessions; 269799 graded calls (XAUUSD 135214, XAGUSD 134585); 50.5% of them up.
- 44 cards rated. Current voting cards (10, config.voting_by_group; the owner's voice aside): Regime (#3), Volatility gauges (#4), Ichimoku cloud (#9), News and economic events (#11), Momentum and stretch (#12), Gold and silver ETF holdings (#14), Kaufman adaptive average (KAMA) (#17), Market structure (#27), Moving averages (SMA and EMA 5-200) (#31), Timeframe strength (#37).

| # | card | votes now | new | steadiest reading | 1st half | 2nd half | worse half | direction | # on 11 Nov |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Mass Index (1h to daily) |  | osc5 | massb_1d | 36.9 | 43.5 | 56.5 | against | new |
| 2 | Ultimate Oscillator (15m, 1h, daily) |  | osc5 | uoz_1d | 57.7 | 53.2 | 53.2 | with | new |
| 3 | Regime | yes |  | regime TREND_DOWN | 52.7 | 53.9 | 52.7 | with | 7 |
| 4 | Volatility gauges | yes |  | vx_gold | 52.5 | 52.5 | 52.5 | with | 1 |
| 5 | Elder-Ray (1h to daily) |  | osc4 | eld_bull_1d | 52.3 | 52.5 | 52.3 | with | new |
| 6 | CCI (15m to daily) |  | osc3 | cci_4h | 52.1 | 52.3 | 52.1 | with | new |
| 7 | Pivot points (daily and weekly) |  | osc4 | pvt_cam_day | 52.8 | 52.0 | 52.0 | with | new |
| 8 | Moving averages as support and resistance |  |  | mas_room_4h | 52.2 | 52.0 | 52.0 | with | 12 |
| 9 | Ichimoku cloud | yes |  | ich_lag_1h | 53.5 | 51.9 | 51.9 | with | 2 |
| 10 | Aroon and Vortex (1h to daily) |  | osc2 | vtx_1h | 53.5 | 51.8 | 51.8 | with | new |
| 11 | News and economic events | yes |  | a US release is near | 47.6 | 48.2 | 51.8 | against | 9 |
| 12 | Momentum and stretch | yes |  | last 24 hours' move | 53.0 | 51.7 | 51.7 | with | 3 |
| 13 | Futures positioning (CFTC) |  |  | cot_level | 51.6 | 54.5 | 51.6 | with | 14 |
| 14 | Gold and silver ETF holdings | yes |  | ge_gld_dvol | 48.0 | 48.4 | 51.6 | against | 4 |
| 15 | Fisher Transform (15m to 4h) |  | osc5 | fishext_1h | 52.0 | 51.6 | 51.6 | with | new |
| 16 | Metals ratios |  |  | mt_lead_24h | 51.4 | 52.5 | 51.4 | with | 17 |
| 17 | Kaufman adaptive average (KAMA) | yes |  | kama_slope_1h | 52.3 | 51.3 | 51.3 | with | 8 |
| 18 | Linear-regression channel (1h to daily) |  | osc5 | lrc_r2_1d | 51.3 | 52.0 | 51.3 | with | new |
| 19 | Time and session |  |  | ck_us_open_in | 51.8 | 51.3 | 51.3 | with | 13 |
| 20 | Daily range budget and range breaks |  | adr | adr_room_up | 51.3 | 51.7 | 51.3 | with | new |
| 21 | Moving-average ribbon |  |  | rb_width_1h | 52.0 | 51.2 | 51.2 | with | 11 |
| 22 | RSI divergence (15m to 4h) |  | osc4 | rdiv_4h | 48.2 | 48.8 | 51.2 | against | new |
| 23 | Trend quality and squeeze |  |  | tq_rsi_1h | 51.7 | 51.2 | 51.2 | with | 23 |
| 24 | Trade setups |  |  | su_pullback | 48.2 | 48.9 | 51.1 | against | 15 |
| 25 | Fibonacci retracement |  |  | fib_depth_1h | 48.5 | 48.9 | 51.1 | against | 16 |
| 26 | StochRSI (15m to daily) |  | osc | os_k_15m | 48.9 | 48.8 | 51.1 | against | new |
| 27 | Market structure | yes |  | ms_pos_1h | 52.0 | 51.0 | 51.0 | with | 5 |
| 28 | Working strategies |  |  | weekly regime (EMA20/50) | 49.0 | 48.7 | 51.0 | against | 20 |
| 29 | Chaikin money flow and OBV (1h to daily) |  | osc4 | obvdiv_1d | 46.0 | 49.1 | 50.9 | against | new |
| 30 | Money Flow Index (15m to daily) |  | osc2 | mfi_1d | 51.9 | 50.9 | 50.9 | with | new |
| 31 | Moving averages (SMA and EMA 5-200) | yes |  | ma_stack_1d | 50.9 | 51.0 | 50.9 | with | 10 |
| 32 | Williams %R (15m to daily) |  | osc4 | wr_15m | 48.9 | 49.2 | 50.8 | against | new |
| 33 | Volume profile (session and 7 days) |  | osc2 | vpf_poc_7d | 53.7 | 50.7 | 50.7 | with | new |
| 34 | Support and resistance |  |  | strength of the resistance above | 52.1 | 50.7 | 50.7 | with | 18 |
| 35 | Intraday levels (VWAP and opening range) |  |  | id_band | 49.3 | 49.2 | 50.7 | against | 19 |
| 36 | TRIX (1h to daily) |  | osc5 | trix_1h | 53.2 | 50.6 | 50.6 | with | new |
| 37 | Timeframe strength | yes |  | 1h trend | 52.1 | 50.6 | 50.6 | with | 6 |
| 38 | Candle size and realistic targets |  |  | cs_used | 48.4 | 49.4 | 50.6 | against | 21 |
| 39 | Heikin-Ashi trend (15m to 4h) |  | osc2 | ha_run_4h | 48.6 | 49.4 | 50.6 | against | new |
| 40 | Hull moving average |  |  | hull_pos_1h | 50.6 | 50.8 | 50.6 | with | 22 |
| 41 | Parabolic SAR (15m to daily) |  | osc2 | psar_1d | 51.5 | 50.5 | 50.5 | with | new |
| 42 | Supertrend (15m to daily) |  | osc | os_st_15m | 49.6 | 48.8 | 50.4 | against | new |
| 43 | Rates and the dollar |  |  | rt_y10_5d | 50.1 | 51.4 | 50.1 | with | 24 |
| 44 | Kronos forecast |  |  | - | - | - | - | no history yet | 25 |

**Where the new batches landed (metals, of 44 cards):**

| batch | card | # | 1st half | 2nd half | worse half | direction |
|---|---|---|---|---|---|---|
| osc: batch 1 (v5.1.2) | StochRSI (15m to daily) | 26 | 48.9 | 48.8 | 51.1 | against |
| osc: batch 1 (v5.1.2) | Supertrend (15m to daily) | 42 | 49.6 | 48.8 | 50.4 | against |
| osc2: batch 2 (v5.1.2) | Aroon and Vortex (1h to daily) | 10 | 53.5 | 51.8 | 51.8 | with |
| osc2: batch 2 (v5.1.2) | Money Flow Index (15m to daily) | 30 | 51.9 | 50.9 | 50.9 | with |
| osc2: batch 2 (v5.1.2) | Volume profile (session and 7 days) | 33 | 53.7 | 50.7 | 50.7 | with |
| osc2: batch 2 (v5.1.2) | Heikin-Ashi trend (15m to 4h) | 39 | 48.6 | 49.4 | 50.6 | against |
| osc2: batch 2 (v5.1.2) | Parabolic SAR (15m to daily) | 41 | 51.5 | 50.5 | 50.5 | with |
| osc3: batch 2b, CCI (v5.2.1) | CCI (15m to daily) | 6 | 52.1 | 52.3 | 52.1 | with |
| adr: daily range budget (v5.2.3) | Daily range budget and range breaks | 20 | 51.3 | 51.7 | 51.3 | with |
| osc4: batch 3 (v5.2.3) | Elder-Ray (1h to daily) | 5 | 52.3 | 52.5 | 52.3 | with |
| osc4: batch 3 (v5.2.3) | Pivot points (daily and weekly) | 7 | 52.8 | 52.0 | 52.0 | with |
| osc4: batch 3 (v5.2.3) | RSI divergence (15m to 4h) | 22 | 48.2 | 48.8 | 51.2 | against |
| osc4: batch 3 (v5.2.3) | Chaikin money flow and OBV (1h to daily) | 29 | 46.0 | 49.1 | 50.9 | against |
| osc4: batch 3 (v5.2.3) | Williams %R (15m to daily) | 32 | 48.9 | 49.2 | 50.8 | against |
| osc5: batch 4 (v5.2.4) | Mass Index (1h to daily) | 1 | 36.9 | 43.5 | 56.5 | against |
| osc5: batch 4 (v5.2.4) | Ultimate Oscillator (15m, 1h, daily) | 2 | 57.7 | 53.2 | 53.2 | with |
| osc5: batch 4 (v5.2.4) | Fisher Transform (15m to 4h) | 15 | 52.0 | 51.6 | 51.6 | with |
| osc5: batch 4 (v5.2.4) | Linear-regression channel (1h to daily) | 18 | 51.3 | 52.0 | 51.3 | with |
| osc5: batch 4 (v5.2.4) | TRIX (1h to daily) | 36 | 53.2 | 50.6 | 50.6 | with |

**Weakest current voter (metals):** Timeframe strength, #37 of 44 (halves 52.1 / 50.6, worse half 50.6, with).

Non-voting cards rated above it (27); those marked **both** also beat it in EACH half separately (in their own direction: 8). These are candidates for the pipeline's step 5 only; nothing is proposed.

| # | card | new | 1st half | 2nd half | worse half | direction | above it in both halves |
|---|---|---|---|---|---|---|---|
| 1 | Mass Index (1h to daily) | osc5 | 36.9 | 43.5 | 56.5 | against | **both** |
| 2 | Ultimate Oscillator (15m, 1h, daily) | osc5 | 57.7 | 53.2 | 53.2 | with | **both** |
| 5 | Elder-Ray (1h to daily) | osc4 | 52.3 | 52.5 | 52.3 | with | **both** |
| 6 | CCI (15m to daily) | osc3 | 52.1 | 52.3 | 52.1 | with |  |
| 7 | Pivot points (daily and weekly) | osc4 | 52.8 | 52.0 | 52.0 | with | **both** |
| 8 | Moving averages as support and resistance |  | 52.2 | 52.0 | 52.0 | with | **both** |
| 10 | Aroon and Vortex (1h to daily) | osc2 | 53.5 | 51.8 | 51.8 | with | **both** |
| 13 | Futures positioning (CFTC) |  | 51.6 | 54.5 | 51.6 | with |  |
| 15 | Fisher Transform (15m to 4h) | osc5 | 52.0 | 51.6 | 51.6 | with |  |
| 16 | Metals ratios |  | 51.4 | 52.5 | 51.4 | with |  |
| 18 | Linear-regression channel (1h to daily) | osc5 | 51.3 | 52.0 | 51.3 | with |  |
| 19 | Time and session |  | 51.8 | 51.3 | 51.3 | with |  |
| 20 | Daily range budget and range breaks | adr | 51.3 | 51.7 | 51.3 | with |  |
| 21 | Moving-average ribbon |  | 52.0 | 51.2 | 51.2 | with |  |
| 22 | RSI divergence (15m to 4h) | osc4 | 48.2 | 48.8 | 51.2 | against |  |
| 23 | Trend quality and squeeze |  | 51.7 | 51.2 | 51.2 | with |  |
| 24 | Trade setups |  | 48.2 | 48.9 | 51.1 | against |  |
| 25 | Fibonacci retracement |  | 48.5 | 48.9 | 51.1 | against |  |
| 26 | StochRSI (15m to daily) | osc | 48.9 | 48.8 | 51.1 | against |  |
| 28 | Working strategies |  | 49.0 | 48.7 | 51.0 | against |  |
| 29 | Chaikin money flow and OBV (1h to daily) | osc4 | 46.0 | 49.1 | 50.9 | against | **both** |
| 30 | Money Flow Index (15m to daily) | osc2 | 51.9 | 50.9 | 50.9 | with |  |
| 32 | Williams %R (15m to daily) | osc4 | 48.9 | 49.2 | 50.8 | against |  |
| 33 | Volume profile (session and 7 days) | osc2 | 53.7 | 50.7 | 50.7 | with | **both** |
| 34 | Support and resistance |  | 52.1 | 50.7 | 50.7 | with |  |
| 35 | Intraday levels (VWAP and opening range) |  | 49.3 | 49.2 | 50.7 | against |  |
| 36 | TRIX (1h to daily) | osc5 | 53.2 | 50.6 | 50.6 | with |  |

## fx (USDJPY)

- History 2020-01-01 22:00 .. 2025-11-10 23:45 UTC, halves split at 2022-12-02 20:00 (the method's own split: the median graded call); horizon 96 sessions; 142250 graded calls (USDJPY 142250); 50.7% of them up.
- 43 cards rated. Current voting cards (10, config.voting_by_group; the owner's voice aside): Trade setups (#1), Regime (#2), Time and session (#3), Momentum and stretch (#4), Working strategies (#10), Support and resistance (#12), Timeframe strength (#16), Moving averages (SMA and EMA 5-200) (#17), Trend quality and squeeze (#19), Rates and the dollar (#30).

| # | card | votes now | new | steadiest reading | 1st half | 2nd half | worse half | direction | # on 11 Nov |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Trade setups | yes |  | su_rangefade | 44.6 | 38.5 | 55.4 | against | 1 |
| 2 | Regime | yes |  | regime TREND_DOWN | 56.4 | 55.3 | 55.3 | with | 2 |
| 3 | Time and session | yes |  | ck_weekend | 53.7 | 53.5 | 53.5 | with | 4 |
| 4 | Momentum and stretch | yes |  | 1h StochRSI | 52.7 | 52.5 | 52.5 | with | 8 |
| 5 | StochRSI (15m to daily) |  | osc | os_k_1h | 52.7 | 52.5 | 52.5 | with | new |
| 6 | Volatility gauges |  |  | vx_front | 47.8 | 46.0 | 52.2 | against | 15 |
| 7 | Intraday levels (VWAP and opening range) |  |  | id_band | 54.2 | 52.1 | 52.1 | with | 12 |
| 8 | Daily range budget and range breaks |  | adr | adr_room_dn | 53.3 | 52.1 | 52.1 | with | new |
| 9 | Linear-regression channel (1h to daily) |  | osc5 | lrc_r2_4h | 52.1 | 52.9 | 52.1 | with | new |
| 10 | Working strategies | yes |  | StochRSI core zone | 52.1 | 52.5 | 52.1 | with | 3 |
| 11 | Futures positioning (CFTC) |  |  | cot_pctile | 56.7 | 52.0 | 52.0 | with | 11 |
| 12 | Support and resistance | yes |  | near yesterday's high | 56.2 | 52.0 | 52.0 | with | 9 |
| 13 | Aroon and Vortex (1h to daily) |  | osc2 | aro_osc_1d | 48.0 | 47.5 | 52.0 | against | new |
| 14 | Fibonacci retracement |  |  | fib_gz_4h | 55.1 | 51.8 | 51.8 | with | 19 |
| 15 | Japan watch |  |  | jp_boj_next | 52.3 | 51.8 | 51.8 | with | 13 |
| 16 | Timeframe strength | yes |  | weekly trend | 51.7 | 56.1 | 51.7 | with | 10 |
| 17 | Moving averages (SMA and EMA 5-200) | yes |  | ma_cross_1d | 48.3 | 48.1 | 51.7 | against | 5 |
| 18 | Market structure |  |  | ms_pos_1h | 54.2 | 51.6 | 51.6 | with | 16 |
| 19 | Trend quality and squeeze | yes |  | tq_adx_1h | 48.8 | 44.7 | 51.2 | against | 7 |
| 20 | Ichimoku cloud |  |  | ich_cloud_4h | 51.2 | 52.5 | 51.2 | with | 21 |
| 21 | Mass Index (1h to daily) |  | osc5 | mass_1d | 48.9 | 48.4 | 51.1 | against | new |
| 22 | Ultimate Oscillator (15m, 1h, daily) |  | osc5 | uoz_1h | 51.1 | 51.3 | 51.1 | with | new |
| 23 | Moving-average ribbon |  |  | rb_pos_1h | 51.5 | 51.0 | 51.0 | with | 23 |
| 24 | Elder-Ray (1h to daily) |  | osc4 | eld_bear_4h | 48.8 | 49.0 | 51.0 | against | new |
| 25 | Kaufman adaptive average (KAMA) |  |  | kama_slope_4h | 49.2 | 48.1 | 50.8 | against | 18 |
| 26 | Hull moving average |  |  | hull_pos_1h | 51.8 | 50.8 | 50.8 | with | 20 |
| 27 | Candle size and realistic targets |  |  | cs_expand | 51.0 | 50.8 | 50.8 | with | 14 |
| 28 | Heikin-Ashi trend (15m to 4h) |  | osc2 | ha_col_4h | 51.1 | 50.7 | 50.7 | with | new |
| 29 | Moving averages as support and resistance |  |  | mas_test_4h | 50.8 | 50.7 | 50.7 | with | 22 |
| 30 | Rates and the dollar | yes |  | rt_gap_5d | 55.6 | 50.5 | 50.5 | with | 6 |
| 31 | CCI (15m to daily) |  | osc3 | cci_1h | 52.9 | 50.5 | 50.5 | with | new |
| 32 | Pivot points (daily and weekly) |  | osc4 | pvt_cam_wk | 49.5 | 48.3 | 50.5 | against | new |
| 33 | Parabolic SAR (15m to daily) |  | osc2 | psar_1d | 51.0 | 50.5 | 50.5 | with | new |
| 34 | TRIX (1h to daily) |  | osc5 | trixx_1h | 50.8 | 50.5 | 50.5 | with | new |
| 35 | Fisher Transform (15m to 4h) |  | osc5 | fishx_1h | 50.5 | 50.6 | 50.5 | with | new |
| 36 | Supertrend (15m to daily) |  | osc | os_st_4h | 49.6 | 49.6 | 50.4 | against | new |
| 37 | RSI divergence (15m to 4h) |  | osc4 | rdiv_15m | 49.7 | 49.1 | 50.3 | against | new |
| 38 | News and economic events |  |  | S&P 500, 5-day move | 45.2 | 49.8 | 50.2 | against | 17 |
| 39 | Williams %R (15m to daily) |  | osc4 | wr_1d | 55.4 | 50.1 | 50.1 | with | new |
| 40 | Kronos forecast |  |  | - | - | - | - | no history yet | 24 |
| 41 | Money Flow Index (15m to daily) |  | osc2 | - | - | - | - | no history yet | new |
| 42 | Volume profile (session and 7 days) |  | osc2 | - | - | - | - | no history yet | new |
| 43 | Chaikin money flow and OBV (1h to daily) |  | osc4 | - | - | - | - | no history yet | new |

**Where the new batches landed (fx, of 43 cards):**

| batch | card | # | 1st half | 2nd half | worse half | direction |
|---|---|---|---|---|---|---|
| osc: batch 1 (v5.1.2) | StochRSI (15m to daily) | 5 | 52.7 | 52.5 | 52.5 | with |
| osc: batch 1 (v5.1.2) | Supertrend (15m to daily) | 36 | 49.6 | 49.6 | 50.4 | against |
| osc2: batch 2 (v5.1.2) | Aroon and Vortex (1h to daily) | 13 | 48.0 | 47.5 | 52.0 | against |
| osc2: batch 2 (v5.1.2) | Heikin-Ashi trend (15m to 4h) | 28 | 51.1 | 50.7 | 50.7 | with |
| osc2: batch 2 (v5.1.2) | Parabolic SAR (15m to daily) | 33 | 51.0 | 50.5 | 50.5 | with |
| osc2: batch 2 (v5.1.2) | Money Flow Index (15m to daily) | 41 | - | - | - | no history yet |
| osc2: batch 2 (v5.1.2) | Volume profile (session and 7 days) | 42 | - | - | - | no history yet |
| osc3: batch 2b, CCI (v5.2.1) | CCI (15m to daily) | 31 | 52.9 | 50.5 | 50.5 | with |
| adr: daily range budget (v5.2.3) | Daily range budget and range breaks | 8 | 53.3 | 52.1 | 52.1 | with |
| osc4: batch 3 (v5.2.3) | Elder-Ray (1h to daily) | 24 | 48.8 | 49.0 | 51.0 | against |
| osc4: batch 3 (v5.2.3) | Pivot points (daily and weekly) | 32 | 49.5 | 48.3 | 50.5 | against |
| osc4: batch 3 (v5.2.3) | RSI divergence (15m to 4h) | 37 | 49.7 | 49.1 | 50.3 | against |
| osc4: batch 3 (v5.2.3) | Williams %R (15m to daily) | 39 | 55.4 | 50.1 | 50.1 | with |
| osc4: batch 3 (v5.2.3) | Chaikin money flow and OBV (1h to daily) | 43 | - | - | - | no history yet |
| osc5: batch 4 (v5.2.4) | Linear-regression channel (1h to daily) | 9 | 52.1 | 52.9 | 52.1 | with |
| osc5: batch 4 (v5.2.4) | Mass Index (1h to daily) | 21 | 48.9 | 48.4 | 51.1 | against |
| osc5: batch 4 (v5.2.4) | Ultimate Oscillator (15m, 1h, daily) | 22 | 51.1 | 51.3 | 51.1 | with |
| osc5: batch 4 (v5.2.4) | TRIX (1h to daily) | 34 | 50.8 | 50.5 | 50.5 | with |
| osc5: batch 4 (v5.2.4) | Fisher Transform (15m to 4h) | 35 | 50.5 | 50.6 | 50.5 | with |

**Weakest current voter (fx):** Rates and the dollar, #30 of 43 (halves 55.6 / 50.5, worse half 50.5, with).

Non-voting cards rated above it (20); those marked **both** also beat it in EACH half separately (in their own direction: 1). These are candidates for the pipeline's step 5 only; nothing is proposed.

| # | card | new | 1st half | 2nd half | worse half | direction | above it in both halves |
|---|---|---|---|---|---|---|---|
| 5 | StochRSI (15m to daily) | osc | 52.7 | 52.5 | 52.5 | with |  |
| 6 | Volatility gauges |  | 47.8 | 46.0 | 52.2 | against |  |
| 7 | Intraday levels (VWAP and opening range) |  | 54.2 | 52.1 | 52.1 | with |  |
| 8 | Daily range budget and range breaks | adr | 53.3 | 52.1 | 52.1 | with |  |
| 9 | Linear-regression channel (1h to daily) | osc5 | 52.1 | 52.9 | 52.1 | with |  |
| 11 | Futures positioning (CFTC) |  | 56.7 | 52.0 | 52.0 | with | **both** |
| 13 | Aroon and Vortex (1h to daily) | osc2 | 48.0 | 47.5 | 52.0 | against |  |
| 14 | Fibonacci retracement |  | 55.1 | 51.8 | 51.8 | with |  |
| 15 | Japan watch |  | 52.3 | 51.8 | 51.8 | with |  |
| 18 | Market structure |  | 54.2 | 51.6 | 51.6 | with |  |
| 20 | Ichimoku cloud |  | 51.2 | 52.5 | 51.2 | with |  |
| 21 | Mass Index (1h to daily) | osc5 | 48.9 | 48.4 | 51.1 | against |  |
| 22 | Ultimate Oscillator (15m, 1h, daily) | osc5 | 51.1 | 51.3 | 51.1 | with |  |
| 23 | Moving-average ribbon |  | 51.5 | 51.0 | 51.0 | with |  |
| 24 | Elder-Ray (1h to daily) | osc4 | 48.8 | 49.0 | 51.0 | against |  |
| 25 | Kaufman adaptive average (KAMA) |  | 49.2 | 48.1 | 50.8 | against |  |
| 26 | Hull moving average |  | 51.8 | 50.8 | 50.8 | with |  |
| 27 | Candle size and realistic targets |  | 51.0 | 50.8 | 50.8 | with |  |
| 28 | Heikin-Ashi trend (15m to 4h) | osc2 | 51.1 | 50.7 | 50.7 | with |  |
| 29 | Moving averages as support and resistance |  | 50.8 | 50.7 | 50.7 | with |  |

Current voters at or below the pipeline's floor in this rating (worse half <= 50.5%): Rates and the dollar (#30).

## index (SPX)

- History 2020-01-02 14:30 .. 2025-11-10 20:45 UTC, halves split at 2022-11-29 17:15 (the method's own split: the median graded call); horizon 26 sessions; 26732 graded calls (SPX 26732); 52.5% of them up.
- 46 cards rated. Current voting cards (10, config.voting_by_group; the owner's voice aside): Trade setups (#2), Moving averages (SMA and EMA 5-200) (#5), Regime (#10), Trend quality and squeeze (#11), Support and resistance (#14), Fibonacci retracement (#17), Rates and the dollar (#20), S&P futures overnight (#24), News and economic events (#25), Intraday levels (VWAP and opening range) (#26).

| # | card | votes now | new | steadiest reading | 1st half | 2nd half | worse half | direction | # on 11 Nov |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Mass Index (1h to daily) |  | osc5 | massb_4h | 33.1 | 29.6 | 66.9 | against | new |
| 2 | Trade setups | yes |  | su_pullback | 61.8 | 56.9 | 56.9 | with | 1 |
| 3 | RSI divergence (15m to 4h) |  | osc4 | rdiv_4h | 55.9 | 59.5 | 55.9 | with | new |
| 4 | Ultimate Oscillator (15m, 1h, daily) |  | osc5 | uoz_1h | 59.6 | 55.7 | 55.7 | with | new |
| 5 | Moving averages (SMA and EMA 5-200) | yes |  | ma_cross_1h | 57.9 | 55.3 | 55.3 | with | 3 |
| 6 | Linear-regression channel (1h to daily) |  | osc5 | lrc_r2_1d | 56.9 | 55.1 | 55.1 | with | new |
| 7 | Momentum and stretch |  |  | pullback inside the trend | 58.0 | 54.6 | 54.6 | with | 16 |
| 8 | Daily range budget and range breaks |  | adr | adr_room_dn | 54.4 | 54.6 | 54.4 | with | new |
| 9 | Stock-market breadth |  |  | eb_iwm_20d | 45.7 | 45.9 | 54.1 | against | 11 |
| 10 | Regime | yes |  | regime TREND_UP | 55.5 | 53.8 | 53.8 | with | 7 |
| 11 | Trend quality and squeeze | yes |  | tq_adx_15m | 53.8 | 54.9 | 53.8 | with | 5 |
| 12 | Chaikin money flow and OBV (1h to daily) |  | osc4 | obvdiv_1d | 46.3 | 43.4 | 53.7 | against | new |
| 13 | Time and session |  |  | ck_us_open_in | 53.5 | 56.7 | 53.5 | with | 13 |
| 14 | Support and resistance | yes |  | near yesterday's low | 53.5 | 56.3 | 53.5 | with | 6 |
| 15 | Moving averages as support and resistance |  |  | mas_test_4h | 53.3 | 57.0 | 53.3 | with | 15 |
| 16 | Kaufman adaptive average (KAMA) |  |  | kama_er_15m | 53.8 | 53.3 | 53.3 | with | 12 |
| 17 | Fibonacci retracement | yes |  | fib_room_1h | 46.9 | 42.3 | 53.1 | against | 9 |
| 18 | Volume profile (session and 7 days) |  | osc2 | vpf_poc_day | 53.8 | 53.0 | 53.0 | with | new |
| 19 | Williams %R (15m to daily) |  | osc4 | wr_1h | 53.9 | 52.9 | 52.9 | with | new |
| 20 | Rates and the dollar | yes |  | rt_dxy_5d | 53.8 | 52.8 | 52.8 | with | 10 |
| 21 | Fisher Transform (15m to 4h) |  | osc5 | fishext_15m | 53.4 | 52.8 | 52.8 | with | new |
| 22 | Candle size and realistic targets |  |  | cs_body | 46.9 | 47.2 | 52.8 | against | 18 |
| 23 | Futures positioning (CFTC) |  |  | cot_level | 47.3 | 44.4 | 52.7 | against | 21 |
| 24 | S&P futures overnight | yes |  | on_pos | 54.1 | 52.5 | 52.5 | with | 4 |
| 25 | News and economic events | yes |  | a US release is near | 52.4 | 55.7 | 52.4 | with | 2 |
| 26 | Intraday levels (VWAP and opening range) | yes |  | id_vwap_w | 52.3 | 55.4 | 52.3 | with | 8 |
| 27 | Pivot points (daily and weekly) |  | osc4 | pvt_pos_day | 52.4 | 52.3 | 52.3 | with | new |
| 28 | Ichimoku cloud |  |  | ich_lag_4h | 48.2 | 46.5 | 51.8 | against | 19 |
| 29 | TRIX (1h to daily) |  | osc5 | trix_4h | 46.7 | 48.2 | 51.8 | against | new |
| 30 | Working strategies |  |  | Donchian trend strategy | 51.8 | 52.0 | 51.8 | with | 17 |
| 31 | Elder-Ray (1h to daily) |  | osc4 | eld_bear_4h | 44.7 | 48.3 | 51.7 | against | new |
| 32 | Timeframe strength |  |  | 4h trend | 51.7 | 53.0 | 51.7 | with | 22 |
| 33 | Megacap earnings |  |  | ern_last | 54.5 | 51.6 | 51.6 | with | 23 |
| 34 | Heikin-Ashi trend (15m to 4h) |  | osc2 | ha_run_4h | 45.5 | 48.4 | 51.6 | against | new |
| 35 | StochRSI (15m to daily) |  | osc | os_k_1h | 51.6 | 52.4 | 51.6 | with | new |
| 36 | Aroon and Vortex (1h to daily) |  | osc2 | aro_osc_1h | 46.0 | 48.6 | 51.4 | against | new |
| 37 | Market structure |  |  | ms_1d | 51.7 | 51.3 | 51.3 | with | 20 |
| 38 | Supertrend (15m to daily) |  | osc | os_st_4h | 48.6 | 48.8 | 51.2 | against | new |
| 39 | Moving-average ribbon |  |  | rb_pos_1h | 55.3 | 51.0 | 51.0 | with | 14 |
| 40 | Money Flow Index (15m to daily) |  | osc2 | mfi_1d | 49.6 | 46.9 | 50.4 | against | new |
| 41 | Hull moving average |  |  | hull_x_1h | 50.4 | 51.4 | 50.4 | with | 24 |
| 42 | Parabolic SAR (15m to daily) |  | osc2 | psar_1h | 49.2 | 49.9 | 50.1 | against | new |
| 43 | Volatility gauges |  |  | vx_level | 43.2 | 50.8 | 50.0 | against | 25 |
| 44 | CCI (15m to daily) |  | osc3 | cci_15m | 50.3 | 49.1 | 50.0 | with | new |
| 45 | Kronos forecast |  |  | - | - | - | - | no history yet | 26 |
| 46 | Options mood (put/call) |  |  | pc_total | - | - | - | too little history | 27 |

**Where the new batches landed (index, of 46 cards):**

| batch | card | # | 1st half | 2nd half | worse half | direction |
|---|---|---|---|---|---|---|
| osc: batch 1 (v5.1.2) | StochRSI (15m to daily) | 35 | 51.6 | 52.4 | 51.6 | with |
| osc: batch 1 (v5.1.2) | Supertrend (15m to daily) | 38 | 48.6 | 48.8 | 51.2 | against |
| osc2: batch 2 (v5.1.2) | Volume profile (session and 7 days) | 18 | 53.8 | 53.0 | 53.0 | with |
| osc2: batch 2 (v5.1.2) | Heikin-Ashi trend (15m to 4h) | 34 | 45.5 | 48.4 | 51.6 | against |
| osc2: batch 2 (v5.1.2) | Aroon and Vortex (1h to daily) | 36 | 46.0 | 48.6 | 51.4 | against |
| osc2: batch 2 (v5.1.2) | Money Flow Index (15m to daily) | 40 | 49.6 | 46.9 | 50.4 | against |
| osc2: batch 2 (v5.1.2) | Parabolic SAR (15m to daily) | 42 | 49.2 | 49.9 | 50.1 | against |
| osc3: batch 2b, CCI (v5.2.1) | CCI (15m to daily) | 44 | 50.3 | 49.1 | 50.0 | with |
| adr: daily range budget (v5.2.3) | Daily range budget and range breaks | 8 | 54.4 | 54.6 | 54.4 | with |
| osc4: batch 3 (v5.2.3) | RSI divergence (15m to 4h) | 3 | 55.9 | 59.5 | 55.9 | with |
| osc4: batch 3 (v5.2.3) | Chaikin money flow and OBV (1h to daily) | 12 | 46.3 | 43.4 | 53.7 | against |
| osc4: batch 3 (v5.2.3) | Williams %R (15m to daily) | 19 | 53.9 | 52.9 | 52.9 | with |
| osc4: batch 3 (v5.2.3) | Pivot points (daily and weekly) | 27 | 52.4 | 52.3 | 52.3 | with |
| osc4: batch 3 (v5.2.3) | Elder-Ray (1h to daily) | 31 | 44.7 | 48.3 | 51.7 | against |
| osc5: batch 4 (v5.2.4) | Mass Index (1h to daily) | 1 | 33.1 | 29.6 | 66.9 | against |
| osc5: batch 4 (v5.2.4) | Ultimate Oscillator (15m, 1h, daily) | 4 | 59.6 | 55.7 | 55.7 | with |
| osc5: batch 4 (v5.2.4) | Linear-regression channel (1h to daily) | 6 | 56.9 | 55.1 | 55.1 | with |
| osc5: batch 4 (v5.2.4) | Fisher Transform (15m to 4h) | 21 | 53.4 | 52.8 | 52.8 | with |
| osc5: batch 4 (v5.2.4) | TRIX (1h to daily) | 29 | 46.7 | 48.2 | 51.8 | against |

**Weakest current voter (index):** Intraday levels (VWAP and opening range), #26 of 46 (halves 52.3 / 55.4, worse half 52.3, with).

Non-voting cards rated above it (16); those marked **both** also beat it in EACH half separately (in their own direction: 7). These are candidates for the pipeline's step 5 only; nothing is proposed.

| # | card | new | 1st half | 2nd half | worse half | direction | above it in both halves |
|---|---|---|---|---|---|---|---|
| 1 | Mass Index (1h to daily) | osc5 | 33.1 | 29.6 | 66.9 | against | **both** |
| 3 | RSI divergence (15m to 4h) | osc4 | 55.9 | 59.5 | 55.9 | with | **both** |
| 4 | Ultimate Oscillator (15m, 1h, daily) | osc5 | 59.6 | 55.7 | 55.7 | with | **both** |
| 6 | Linear-regression channel (1h to daily) | osc5 | 56.9 | 55.1 | 55.1 | with |  |
| 7 | Momentum and stretch |  | 58.0 | 54.6 | 54.6 | with |  |
| 8 | Daily range budget and range breaks | adr | 54.4 | 54.6 | 54.4 | with |  |
| 9 | Stock-market breadth |  | 45.7 | 45.9 | 54.1 | against |  |
| 12 | Chaikin money flow and OBV (1h to daily) | osc4 | 46.3 | 43.4 | 53.7 | against | **both** |
| 13 | Time and session |  | 53.5 | 56.7 | 53.5 | with | **both** |
| 15 | Moving averages as support and resistance |  | 53.3 | 57.0 | 53.3 | with | **both** |
| 16 | Kaufman adaptive average (KAMA) |  | 53.8 | 53.3 | 53.3 | with |  |
| 18 | Volume profile (session and 7 days) | osc2 | 53.8 | 53.0 | 53.0 | with |  |
| 19 | Williams %R (15m to daily) | osc4 | 53.9 | 52.9 | 52.9 | with |  |
| 21 | Fisher Transform (15m to 4h) | osc5 | 53.4 | 52.8 | 52.8 | with |  |
| 22 | Candle size and realistic targets |  | 46.9 | 47.2 | 52.8 | against |  |
| 23 | Futures positioning (CFTC) |  | 47.3 | 44.4 | 52.7 | against | **both** |

## energy (WTI, BRENT)

- History 2020-01-02 01:00 .. 2025-11-10 21:45 UTC, halves split at 2022-12-07 21:45 (the method's own split: the median graded call); horizon 96 sessions; 249569 graded calls (WTI 124767, BRENT 124802); 50.7% of them up.
- 44 cards rated. Current voting cards (10, config.voting_by_group; the owner's voice aside): Trade setups (#2), Oil volatility (#4), Moving averages (SMA and EMA 5-200) (#9), Fibonacci retracement (#10), Candle size and realistic targets (#11), Regime (#12), WTI-Brent and curve (#14), Support and resistance (#18), Kaufman adaptive average (KAMA) (#24), Trend quality and squeeze (#29).

| # | card | votes now | new | steadiest reading | 1st half | 2nd half | worse half | direction | # on 11 Nov |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Mass Index (1h to daily) |  | osc5 | massb_4h | 43.9 | 25.8 | 56.1 | against | new |
| 2 | Trade setups | yes |  | su_pullback | 45.3 | 45.4 | 54.6 | against | 3 |
| 3 | Chaikin money flow and OBV (1h to daily) |  | osc4 | cmf_4h | 46.5 | 45.2 | 53.5 | against | new |
| 4 | Oil volatility | yes |  | ovol_chg5 | 47.3 | 44.9 | 52.7 | against | 1 |
| 5 | Pivot points (daily and weekly) |  | osc4 | pvt_cam_day | 53.6 | 52.7 | 52.7 | with | new |
| 6 | Linear-regression channel (1h to daily) |  | osc5 | lrc_pos_1d | 47.6 | 47.9 | 52.1 | against | new |
| 7 | Elder-Ray (1h to daily) |  | osc4 | eld_bull_1h | 52.7 | 52.0 | 52.0 | with | new |
| 8 | Aroon and Vortex (1h to daily) |  | osc2 | vtx_1h | 52.3 | 52.0 | 52.0 | with | new |
| 9 | Moving averages (SMA and EMA 5-200) | yes |  | ma_cross_1d | 51.8 | 52.0 | 51.8 | with | 6 |
| 10 | Fibonacci retracement | yes |  | fib_gz_1h | 46.6 | 48.3 | 51.7 | against | 5 |
| 11 | Candle size and realistic targets | yes |  | cs_reach_rel | 48.6 | 46.5 | 51.4 | against | 9 |
| 12 | Regime | yes |  | regime MOMENTUM_DOWN | 52.3 | 51.4 | 51.4 | with | 2 |
| 13 | Momentum and stretch |  |  | last 24 hours' move | 51.3 | 51.5 | 51.3 | with | 17 |
| 14 | WTI-Brent and curve | yes |  | ospr_curve | 48.8 | 42.6 | 51.2 | against | 4 |
| 15 | RSI divergence (15m to 4h) |  | osc4 | rdiv_4h | 53.6 | 51.2 | 51.2 | with | new |
| 16 | Ultimate Oscillator (15m, 1h, daily) |  | osc5 | uoz_1h | 48.8 | 48.5 | 51.2 | against | new |
| 17 | Moving-average ribbon |  |  | rb_width_15m | 52.3 | 51.1 | 51.1 | with | 14 |
| 18 | Support and resistance | yes |  | support is close | 51.6 | 51.1 | 51.1 | with | 7 |
| 19 | Daily range budget and range breaks |  | adr | adr_room_dn | 51.1 | 51.2 | 51.1 | with | new |
| 20 | Williams %R (15m to daily) |  | osc4 | wr_4h | 49.0 | 47.6 | 51.0 | against | new |
| 21 | TRIX (1h to daily) |  | osc5 | trixx_1h | 51.3 | 51.0 | 51.0 | with | new |
| 22 | CCI (15m to daily) |  | osc3 | cci_4h | 51.0 | 51.1 | 51.0 | with | new |
| 23 | Money Flow Index (15m to daily) |  | osc2 | mfi_1d | 49.1 | 46.4 | 50.9 | against | new |
| 24 | Kaufman adaptive average (KAMA) | yes |  | kama_er_1h | 52.5 | 50.9 | 50.9 | with | 8 |
| 25 | EIA crude inventories |  |  | eia_cushing | 52.3 | 50.9 | 50.9 | with | 12 |
| 26 | Market structure |  |  | ms_pos_4h | 50.9 | 51.1 | 50.9 | with | 18 |
| 27 | Fisher Transform (15m to 4h) |  | osc5 | fish_4h | 49.2 | 48.1 | 50.8 | against | new |
| 28 | Crude futures positioning (CFTC) |  |  | opos_chg | 49.0 | 49.2 | 50.8 | against | 11 |
| 29 | Trend quality and squeeze | yes |  | tq_rsi_1h | 51.1 | 50.7 | 50.7 | with | 10 |
| 30 | Moving averages as support and resistance |  |  | mas_room_4h | 51.1 | 50.7 | 50.7 | with | 19 |
| 31 | Ichimoku cloud |  |  | ich_lag_1h | 51.1 | 50.7 | 50.7 | with | 13 |
| 32 | StochRSI (15m to daily) |  | osc | os_k_1d | 49.4 | 47.8 | 50.6 | against | new |
| 33 | Intraday levels (VWAP and opening range) |  |  | id_or | 50.6 | 50.9 | 50.6 | with | 15 |
| 34 | News and economic events |  |  | dollar index, 5-day move | 49.5 | 48.6 | 50.5 | against | 21 |
| 35 | Hull moving average |  |  | hull_pos_15m | 49.5 | 49.2 | 50.5 | against | 20 |
| 36 | Time and session |  |  | ck_dow_cos | 49.5 | 49.6 | 50.4 | against | 16 |
| 37 | Volume profile (session and 7 days) |  | osc2 | vpf_pos_day | 51.7 | 50.1 | 50.1 | with | new |
| 38 | Heikin-Ashi trend (15m to 4h) |  | osc2 | ha_run_4h | 49.0 | 49.9 | 50.1 | against | new |
| 39 | Supertrend (15m to daily) |  | osc | os_st_15m | 50.1 | 50.3 | 50.1 | with | new |
| 40 | OPEC+ calendar |  |  | opec_week | 59.7 | 47.7 | 50.0 | with | 23 |
| 41 | Working strategies |  |  | StochRSI core zone | 49.0 | 52.2 | 50.0 | against | 22 |
| 42 | Timeframe strength |  |  | 15m trend | 50.5 | 48.9 | 50.0 | with | 24 |
| 43 | Parabolic SAR (15m to daily) |  | osc2 | psar_15m | 50.0 | 49.6 | 50.0 | against | new |
| 44 | Kronos forecast |  |  | - | - | - | - | no history yet | 25 |

**Where the new batches landed (energy, of 44 cards):**

| batch | card | # | 1st half | 2nd half | worse half | direction |
|---|---|---|---|---|---|---|
| osc: batch 1 (v5.1.2) | StochRSI (15m to daily) | 32 | 49.4 | 47.8 | 50.6 | against |
| osc: batch 1 (v5.1.2) | Supertrend (15m to daily) | 39 | 50.1 | 50.3 | 50.1 | with |
| osc2: batch 2 (v5.1.2) | Aroon and Vortex (1h to daily) | 8 | 52.3 | 52.0 | 52.0 | with |
| osc2: batch 2 (v5.1.2) | Money Flow Index (15m to daily) | 23 | 49.1 | 46.4 | 50.9 | against |
| osc2: batch 2 (v5.1.2) | Volume profile (session and 7 days) | 37 | 51.7 | 50.1 | 50.1 | with |
| osc2: batch 2 (v5.1.2) | Heikin-Ashi trend (15m to 4h) | 38 | 49.0 | 49.9 | 50.1 | against |
| osc2: batch 2 (v5.1.2) | Parabolic SAR (15m to daily) | 43 | 50.0 | 49.6 | 50.0 | against |
| osc3: batch 2b, CCI (v5.2.1) | CCI (15m to daily) | 22 | 51.0 | 51.1 | 51.0 | with |
| adr: daily range budget (v5.2.3) | Daily range budget and range breaks | 19 | 51.1 | 51.2 | 51.1 | with |
| osc4: batch 3 (v5.2.3) | Chaikin money flow and OBV (1h to daily) | 3 | 46.5 | 45.2 | 53.5 | against |
| osc4: batch 3 (v5.2.3) | Pivot points (daily and weekly) | 5 | 53.6 | 52.7 | 52.7 | with |
| osc4: batch 3 (v5.2.3) | Elder-Ray (1h to daily) | 7 | 52.7 | 52.0 | 52.0 | with |
| osc4: batch 3 (v5.2.3) | RSI divergence (15m to 4h) | 15 | 53.6 | 51.2 | 51.2 | with |
| osc4: batch 3 (v5.2.3) | Williams %R (15m to daily) | 20 | 49.0 | 47.6 | 51.0 | against |
| osc5: batch 4 (v5.2.4) | Mass Index (1h to daily) | 1 | 43.9 | 25.8 | 56.1 | against |
| osc5: batch 4 (v5.2.4) | Linear-regression channel (1h to daily) | 6 | 47.6 | 47.9 | 52.1 | against |
| osc5: batch 4 (v5.2.4) | Ultimate Oscillator (15m, 1h, daily) | 16 | 48.8 | 48.5 | 51.2 | against |
| osc5: batch 4 (v5.2.4) | TRIX (1h to daily) | 21 | 51.3 | 51.0 | 51.0 | with |
| osc5: batch 4 (v5.2.4) | Fisher Transform (15m to 4h) | 27 | 49.2 | 48.1 | 50.8 | against |

**Weakest current voter (energy):** Trend quality and squeeze, #29 of 44 (halves 51.1 / 50.7, worse half 50.7, with).

Non-voting cards rated above it (19); those marked **both** also beat it in EACH half separately (in their own direction: 12). These are candidates for the pipeline's step 5 only; nothing is proposed.

| # | card | new | 1st half | 2nd half | worse half | direction | above it in both halves |
|---|---|---|---|---|---|---|---|
| 1 | Mass Index (1h to daily) | osc5 | 43.9 | 25.8 | 56.1 | against | **both** |
| 3 | Chaikin money flow and OBV (1h to daily) | osc4 | 46.5 | 45.2 | 53.5 | against | **both** |
| 5 | Pivot points (daily and weekly) | osc4 | 53.6 | 52.7 | 52.7 | with | **both** |
| 6 | Linear-regression channel (1h to daily) | osc5 | 47.6 | 47.9 | 52.1 | against | **both** |
| 7 | Elder-Ray (1h to daily) | osc4 | 52.7 | 52.0 | 52.0 | with | **both** |
| 8 | Aroon and Vortex (1h to daily) | osc2 | 52.3 | 52.0 | 52.0 | with | **both** |
| 13 | Momentum and stretch |  | 51.3 | 51.5 | 51.3 | with | **both** |
| 15 | RSI divergence (15m to 4h) | osc4 | 53.6 | 51.2 | 51.2 | with | **both** |
| 16 | Ultimate Oscillator (15m, 1h, daily) | osc5 | 48.8 | 48.5 | 51.2 | against | **both** |
| 17 | Moving-average ribbon |  | 52.3 | 51.1 | 51.1 | with | **both** |
| 19 | Daily range budget and range breaks | adr | 51.1 | 51.2 | 51.1 | with |  |
| 20 | Williams %R (15m to daily) | osc4 | 49.0 | 47.6 | 51.0 | against |  |
| 21 | TRIX (1h to daily) | osc5 | 51.3 | 51.0 | 51.0 | with | **both** |
| 22 | CCI (15m to daily) | osc3 | 51.0 | 51.1 | 51.0 | with |  |
| 23 | Money Flow Index (15m to daily) | osc2 | 49.1 | 46.4 | 50.9 | against |  |
| 25 | EIA crude inventories |  | 52.3 | 50.9 | 50.9 | with | **both** |
| 26 | Market structure |  | 50.9 | 51.1 | 50.9 | with |  |
| 27 | Fisher Transform (15m to 4h) | osc5 | 49.2 | 48.1 | 50.8 | against |  |
| 28 | Crude futures positioning (CFTC) |  | 49.0 | 49.2 | 50.8 | against |  |

## How this was run, and what to be careful with

- **Where.** On the research server (`/data/mind15`, code = the laptop's git HEAD, engine think15-v5.2.4), 17 Nov 2026
  06:12 to about 07:00 UTC, two workers at low priority, one group at a time per worker.
- **Nothing the engine reads was written.** `research/rate_cards.py` builds its readings from the bars itself
  (`evidence.build`); it never opens `data/evcache` and writes nothing under `data/`. Run as it stands it WOULD overwrite
  `research/out/card_rating_<group>.json` and `voting_by_group.json`, which the live page (`export.group_rating`) and
  `tests/test_rate_cards.py` read. So it was run through `research/rate_cards_snapshot.py` (new, same method, same code):
  results in `research/out/card_rating_20261117/`, temporary files under that folder (the server's `/tmp` is memory),
  removed when each group finished. The rating the page shows is still the one of 11 Nov 2026.
- **The sealed holdout was not read.** History stops at 2025-11-10 23:45 UTC (`rate_cards.run(end="2025-11-11")`). The
  halves are the method's own: split at the median graded call, which lands in early December 2022 (the 11 Nov rating
  ran to 11 Nov 2026 and split in mid 2023). A card's place here and its place on the page are therefore not the same
  measurement; the last column of each table gives the 11 Nov place for orientation only.
- **The index group (S&P 500).** The brief said to rate it only if its reading cache is on the current version. The
  cache is NOT (last built 16 Nov 21:04 UTC on the earlier version; it rebuilds at the 14:30 UTC open), but this rating
  does not use the cache at all, so the index was rated from the bars with the current code like the other groups. If
  the owner prefers to wait for the cache, ignore the index section; nothing depends on it.
- **A rating at the top of the list can be an artefact.** The method takes each card's single steadiest reading. A
  yes/no reading that fires rarely (a few hundred sessions a half, bunched into a handful of episodes) can show a
  lopsided score from a few events. **Mass Index is the clear case:** its "bulge" reading tops metals and energy with
  halves like 36.9 / 43.5 and 43.9 / 25.8, but gold and silver disagree with each other (XAU 51.6 / 41.7, XAG 6.9 /
  46.7), BTC and ETH point opposite ways (61.7 / 57.8 against 38.4 / 37.1), and in oil neither market has enough rows
  on its own to be scored. Read it as "too few independent events to rate", not as the best card. The same caution, to
  a lesser degree, applies to every daily reading (for example the Ultimate Oscillator's daily zone in metals, the
  OPEC+ week): a daily value is repeated on up to 96 sessions, so the session counts overstate the evidence.
- **Cards with no rating.** Live-only cards (Kronos, order book, liquidation proxy) have no history; "Long/short
  positioning" and "Spot ETF flows" have too little history before the holdout. Several crypto cards of batches 0 and 3c
  have short histories (OKX funding about three months, Deribit flow, Korea premium), so their halves rest on less data
  than the price-based cards.
- **What this is for.** Step 3 of the card pipeline. A card is proposed for a vote only after step 4 as well (30 days of
  forward grading) and the owner's yes. The lists of "non-voting cards above the weakest voter" are that and nothing
  more: lists.

