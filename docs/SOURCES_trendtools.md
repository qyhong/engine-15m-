# Ichimoku, Hull and KAMA (`engine15/sources/trendtools.py`)

Owner, 11 Nov 2026: add Ichimoku, the Hull moving average and KAMA "as reading and studies, unless it
is helpful on direction prediction". Three cards, built only from the asset's own 15-minute bars, on
all six assets. They are ordinary voices: they are read, journaled and shown; whether they vote is
set in config, and they start as readings only. **Nothing here is claimed to predict anything.**

## The one rule

A row uses only what was known at that 15-minute close. 1h and 4h readings come from bars that have
**closed** (the `data.htf_on_15` lookup). `tests/test_trendtools.py` cuts the future off at several
points (on BTC, on the S&P 500 with its overnight gaps, and on planted data) and checks that no column
changes. ATR is Wilder's ATR(14) of the same timeframe.

## Ichimoku cloud (voice `ichimoku`), 1h and 4h, standard 9 / 26 / 52

- **Tenkan** = middle of the last 9 bars' range; **Kijun** = middle of the last 26.
- **The cloud is drawn 26 bars ahead of the bar that computes it.** So the cloud under the current
  bar, the one a chart shows behind today's candle, was computed 26 bars ago: span A = (Tenkan +
  Kijun) / 2 of 26 bars ago, span B = middle of the 52-bar range of 26 bars ago. Nothing here peeks
  at the future. The cloud computed at this close is the **cloud ahead** (drawn 26 bars to the right).
- **Lagging line** (Chikou): today's close drawn 26 bars back, read as this close against the close
  26 bars ago.

Readings: price above, inside or below the cloud and how far from its edge (ATR); cloud colour
(green = span A over B) and thickness (ATR); Tenkan above or below Kijun and the age and price of
their last cross; distance to the Kijun (a classic dynamic support/resistance); the lagging line; the
colour of the cloud ahead. Prices: `ich_{tf}_tenkan_px`, `_kijun_px`, `_span_a_px`, `_span_b_px`,
`_ahead_a_px`, `_ahead_b_px`, `_lag_ref_px`.

Features: `ich_pos_*` (+1 above the cloud, -1 below, inside -0.5 to +0.5 by where in the cloud),
`ich_tk_*` (Tenkan minus Kijun, tanh(ATRs)), `ich_kijun_*` (close minus Kijun, tanh(ATRs / 2)),
`ich_cloud_*` (span A minus B: colour times thickness, tanh(ATRs / 2)), `ich_lag_*` (close minus the
close 26 bars back, tanh(ATRs / 3)).

## Hull moving average (voice `hull`), 15m and 1h, lengths 9, 21, 55

HMA(n) = WMA(2 x WMA(close, n/2) - WMA(close, n), sqrt(n)), with n/2 and sqrt(n) rounded down; WMA is
the linearly weighted average. The Hull line follows price closely and turns quickly; its turns are
what traders watch.

Readings per line: price, rising or falling (and its one-bar slope in ATR), price above or below it,
bars since it last turned; the HMA 9 / 21 cross with its age and price.

Features: `hull_dir_*` (mean slope sign of the three lines), `hull_pos_*` (mean side of price),
`hull_turn_*` (a fresh turn of the HMA 21, signed, fading over 8 bars), `hull_x_*` (a fresh 9/21
cross, signed, fading over 8 bars).

## Kaufman adaptive average (voice `kama`), 15m, 1h and 4h, ER 10, fast 2, slow 30

- **Efficiency ratio** (ER): net move over the last 10 bars divided by the sum of the 10 bar-to-bar
  moves. 0 = pure chop, 1 = a straight line. Shown as choppy (below 0.3), mixed, or efficient (0.6+).
- **KAMA** moves fast when ER is high and almost stops when it is low:
  sc = (ER x (2/3 - 2/31) + 2/31)^2, KAMA = previous KAMA + sc x (close - previous KAMA).
- **Label**: flat (no trend) when KAMA moved less than 0.15 ATR over its last 3 bars, else trending
  up or down. This is the card to look at when the mandate forces a position into a market with no
  trend.

Features: `kama_er_*` (ER signed by the direction of the 10-bar move), `kama_pos_*` (close minus
KAMA, tanh(ATRs / 2)), `kama_slope_*` (KAMA's 3-bar change, tanh(ATRs / 0.5)).

## Limits, stated plainly

- All three are trend tools built on past prices; they lag and they disagree in ranges.
- Ichimoku's periods (9 / 26 / 52) come from a six-day trading week; they are used as is on every
  timeframe and market, as charting packages do.
- Constants (fade 8 bars, squash scales, the 0.15 ATR flat line, ER bands) are conventional values
  declared once and not tuned against outcomes.
- The readable columns are float32 (about seven significant digits). 83 columns; full history for one
  asset takes about one second.
