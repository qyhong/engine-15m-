# Card pipeline batch 3 (`engine15/sources/osc4.py`)

The owner gave the go on 16 Nov 2026 (see `research/CARD_PIPELINE.md`). Five cards, built only from the asset's own
15-minute bars, on all eight markets. They are **reading-only and not wired in**: `osc4` is not in `sources.MODULES`,
the engine does not read them and they do not vote (a test checks this). **Nothing here is claimed to predict
anything.** Tests: `tests/test_sources_osc4.py`.

## The timing rule

A row is keyed by its 15m bar's OPEN time and uses only what was known at that bar's close. 1h, 4h and daily values
are computed on resampled OHLCV bars (UTC grid, left-labelled) and reach a 15m row only once that higher bar has closed
(`data.htf_on_15`). Weekly pivots are computed on weekly bars (weeks start Monday 00:00 UTC) and handed through
`data.htf_on_15` as a bar that closes at the next Monday 00:00 UTC. The tests cut the history at several points, on
synthetic bars and on the last 90 days of real BTCUSDT and XAUUSD bars, and check that no column changes; and that
daily values change only on the row whose close is midnight UTC, weekly ones only at Monday 00:00 UTC, 4h / 1h ones
only at their closes. `update()` fetches nothing.

## The cards

| Voice | Card | What it reads | Parameters |
|---|---|---|---|
| `willr` | Williams %R (15m to daily) | %R = -100 x (highest high - close) / (highest high - lowest low) on 15m, 1h, 4h, 1d. Feature `wr_*` = (%R + 50) / 50 (+1 at the top of the range, -1 at the bottom); raw `wr_raw_*` in -100..0. Sentence flags above -20 overbought, below -80 oversold | 14 bars; a flat window is no read |
| `cmf` | Chaikin money flow and OBV (1h to daily) | CMF on 1h, 4h, 1d: feature `cmf_*` = CMF / 0.25 clipped, raw `cmf_raw_*`. OBV divergence `obvdiv_*`: the close makes a new 20-bar closing high (above each of the previous 19 closes) while OBV does not make its own new 20-bar high (bearish), or the mirror for lows (bullish); feature +1 bullish / -1 bearish on the event bar fading to 0 over 5 bars; raw `obvdiv_bull_age_*`, `obvdiv_bear_age_*` (bars of that timeframe since the event, NaN after 5) | CMF(20) = sum(((C-L) - (H-C)) / (H-L) x V) / sum(V); a bar with H = L adds volume but no flow. Needs volume |
| `elder` | Elder-Ray (1h to daily) | Bull power = high - EMA13 and bear power = low - EMA13, in ATR(14) of that timeframe; features `eld_bull_*`, `eld_bear_*` = power / 2 clipped; `eld_slope_*` = sign of the EMA13 change on the last bar. Raw `eld_bull_raw_*`, `eld_bear_raw_*`, `eld_ema_*` | EMA13 seeded with the SMA of the first 13 closes, read after 26 bars (`indicators.ema_seeded`); Wilder ATR(14) |
| `pivots` | Pivot points (daily and weekly) | From the prior completed UTC day and prior completed week: classic P = (H+L+C)/3, R1 = 2P-L, S1 = 2P-H, R2 = P+(H-L), S2 = P-(H-L), R3 = H+2(P-L), S3 = L-2(H-P); Camarilla H4/L4 = C +/- 1.1(H-L)/2, H3/L3 = C +/- 1.1(H-L)/4. Features (per `day` / `wk`): `pvt_pos_*` = (close - P) / daily ATR / 2 clipped; `pvt_zone_*` = which classic zone (below S3 = -1 ... above R3 = +1, in 8 steps); `pvt_cam_*` = (close - prior close) / (1.1(H-L)/2) clipped (H4 = +1, H3 = +0.5, L3 = -0.5, L4 = -1). Raw: all eleven levels `pvt_<level>_<day|wk>`, nearest level above / below among all eleven (`pvt_above_px_*`, `pvt_below_px_*`) and their distance in daily ATR(14) (`pvt_above_atr_*`, `pvt_below_atr_*`), `pvt_atr_d` | A UTC day with fewer than 16 15m bars (e.g. the two-hour Sunday session of metals, oil and FX) or a week with fewer than 64 is skipped: the previous day's / week's levels stay in use, so Monday's daily pivots come from Friday |
| `rsidiv` | RSI divergence (15m to 4h) | On 15m, 1h, 4h: regular bearish divergence = the last two confirmed swing highs have a higher price high and a lower RSI(14) at those bars; regular bullish = the last two confirmed swing lows have a lower price low and a higher RSI. Feature `rdiv_*` = +1 bullish / -1 bearish on the confirming bar, fading to 0 over 20 bars of that timeframe; raw `rdiv_bull_age_*`, `rdiv_bear_age_*` (bars since confirmation, NaN when none is active), `rdiv_rsi_*` (current RSI) | Swing high = high above each of the 3 bars before and at least each of the 3 bars after (lows mirrored); **k = 3: a swing is confirmed 3 bars after it, and the signal appears only on that bar, never earlier**. The two swings at most 60 bars apart. Wilder RSI(14), first 14 bars not read |

Features are in [-1, 1] with 0.0 = no read (never NaN); raw columns are NaN when there is no read. `describe(row,
asset)` gives one sentence per card that says what is read and forecasts nothing.

## Volume

- **USDJPY: no read** on the CMF / OBV card on every row (`NO_VOLUME`); its live feed carries no volume. The sentence
  says so. The other four cards read USDJPY normally.
- Any asset: a CMF / OBV window is read only if at least half its bars carry volume > 0.
- Gold, silver, the S&P, WTI and Brent carry each source's own volume number, and gold, silver and the S&P change
  source at the data join (Aug / Sep 2026); see `docs/SOURCES_osc2.md`. Volume is not comparable across markets.

## Notes

- Pivots use the close of the row's own 15m bar; the nearest level is chosen among all eleven (classic and Camarilla),
  a level equal to the close counts as below.
- The S&P trades cash hours only, so its "day" is the cash session and its weekly pivots come from five sessions.
- Elder-Ray and Williams %R on the daily bar of a market with a thin Sunday session see that session as its own small
  daily bar (as every other daily reading in the engine does).

## Cost

BTCUSDT full history (about 276,000 15m rows, 2019 to Nov 2026): about 1.5-3 s for all five cards on the owner's laptop.
