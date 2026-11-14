# Lower-timeframe toolkit (`engine15/sources/ltf.py`)

Three decision cards built only from the coin's own 15-minute bars. Nothing is downloaded.
They describe where price is and how far it normally moves. **Nothing here is claimed to
predict anything**; no reading was tested against what price did next.

**The one rule.** A row uses only bars that had closed by that row's 15m close. 1h / 4h / 1d
readings arrive through `data.htf_on_15`, so an hour (or day) is used only after it has ended.
`tests/test_sources_ltf.py::test_no_lookahead` cuts the future off and checks every column.

**Units.** "ATR" always means ATR(14) of the 1-hour chart. Features are plain numbers, clipped,
and 0.0 means "no read". Ratios are read in doublings (log2): +1 = twice, -1 = half, clipped at 3.
A dollar figure shown to the owner is always a percentage applied to the bar's close.

## Card 1. Intraday levels (VWAP and opening range)

What it tells a swing trader: whether price is above or below the average price everyone paid
today and this week, and whether it has left the range the first hour set.

| Reading | What it is | Feature and scale | Known |
|---|---|---|---|
| Daily VWAP | average of (high+low+close)/3 weighted by volume, since 00:00 UTC | `id_vwap_d`: close minus VWAP in ATRs, clipped at 3 | every bar |
| Weekly VWAP | the same since Monday 00:00 UTC | `id_vwap_w`: in units of 2.65 ATR (sqrt 7), clipped at 3 | every bar |
| VWAP bands | VWAP plus and minus 1 and 2 volume-weighted standard deviations | `id_band`: -1, -0.5, 0, +0.5, +1 = below -2 sd ... above +2 sd | once the day is 1 hour old |
| Opening range | high and low of 00:00 to 01:00 UTC | `id_or`: +1 close above it, -1 below, 0 inside or unknown | from the 00:45 bar's close |
| Today's range | high and low so far today | `id_day_pos`: -1 at the low, +1 at the high | every bar |

Weaknesses: crypto has no real "open", so 00:00 UTC is a convention, not an auction. Early in a
session a VWAP is built from few bars and moves a lot. The weekly unit (2.65 ATR) is a choice.

## Card 2. Trend quality and squeeze

What it tells a swing trader: is there a trend worth following or only chop, is volatility
coiled or released, and do the 15m and 1h pictures agree.

| Reading | What it is | Feature and scale | Known |
|---|---|---|---|
| ADX(14), 15m and 1h | trend strength 0 to 100 (direction-free) | `tq_adx_15m`, `tq_adx_1h`: (ADX - 25) / 25, so 0 = the textbook trend line | bar close / hour close |
| +DI / -DI | which side leads | `tq_di_15m`, `tq_di_1h`: (+DI - -DI) / (+DI + -DI), -1 to +1 | same |
| Bollinger(20, 2) width | band width as % of price, ranked in its last 30 days | `tq_bbw`: -1 = tightest of 30 days, +1 = widest | after 7 days |
| Squeeze | Bollinger bands inside Keltner channels (20-bar average, 1.5 mean true range) | `tq_squeeze`: 1 on, 0 off | bar close |
| Squeeze release | the bar a squeeze ended; direction = side of the 20-bar average | `tq_sq_release`: +1 / -1 fading to 0 over 8 bars | bar close |
| Supertrend(10, 3) | trailing-stop line; above = up, below = down | `tq_st_15m`, `tq_st_1h`: +1 / -1; `tq_st_flip`: a fresh 15m flip fading over 8 bars | bar close / hour close |
| Structure | last two confirmed swing highs and lows (5 bars each side) | `tq_struct`: +1 higher highs and higher lows, -1 lower highs and lower lows, 0 mixed | 5 bars after each swing |
| Break of structure | first close beyond the last confirmed swing high or low | `tq_bos`: +1 / -1 fading to 0 over 8 bars | bar close |
| MACD(12, 26, 9) histogram | 15m and 1h | `tq_macd_*`: +1 above zero, -1 below; `tq_macd_rise_*`: +1 rising, -1 falling | bar close / hour close |
| RSI(14) | 15m and 1h | `tq_rsi_*`: (RSI - 50) / 50 | same |
| Relative volume | last hour's volume against the same clock hour of the previous 20 days | `tq_rvol`: log2, +1 = twice usual | after 10 days |

Weaknesses: every tool here lags; ADX and Supertrend turn after the move has started. A swing
is only confirmed 75 minutes late, and two swing highs in a row with no low between them both
count. The squeeze flag compares two volatility measures and can flicker on and off. MACD sign
is nearly meaningless when the histogram is close to zero. These readings overlap heavily: they
are several views of the same price path, not independent witnesses.

## Card 3. Candle size and realistic targets

What it tells a swing trader: how big a normal candle and a normal day are right now, how much
of a normal day is already spent, and how far price has usually travelled in 1, 4 and 24 hours.

- **Average body and range**: body = |close - open|, range = high - low, each as a % of that
  candle's open, averaged over the last 96 candles of 15m, 48 of 1h, 30 of 4h, 14 of 1d. The 1d
  range average is the average daily range (ADR). Higher timeframes use closed candles only.
- **Range used** (`cs_used_x`): today's high minus low so far, divided by the ADR. 0.85 = 85%
  of a normal day already travelled. Feature `cs_used` = that minus 1, clipped to -1..+2.
- **Last candle**: body as a multiple of the average body (`cs_body`, log2); body divided by
  range (`cs_body_share`: +1 all body, -1 all wick); average body of the last 8 candles over
  the last 96 (`cs_expand`, log2: above 0 expanding, below 0 contracting).
- **Realistic reach**. For each past bar that closed on the hour, take the largest move in
  either direction over the next 4, 16 or 96 bars and divide it by the ATR at that bar. That
  ratio exists only once those bars have closed, so it joins the record 1, 4 or 24 hours late.
  At each bar the module keeps the median and the 80th percentile of the last 90 days of such
  ratios (it needs 30 days to start). Reach now = ratio x today's ATR, as a % of price:
  `reach_1h_med_pct`, `reach_1h_p80_pct`, `reach_4h_*`, `reach_24h_*`.
  Feature `cs_reach_rel`: the 24h median reach against its own 90-day median (log2).

How to read "Typical travel: 1h 0.4%, 4h 0.9%, 24h 2.7% (large moves reach ...)": in the last
90 days, at this level of volatility, half of all 24-hour windows moved less than 2.7% from
their starting price at their furthest point, and four in five moved less than the "large" figure.

Weaknesses: reach has no direction; it is the furthest point touched, not where price ended,
and it says nothing about which side. It assumes the next hours resemble the last 90 days
scaled by the current ATR; after a volatility shock the ATR lags and so does the reach. The
24-hour windows overlap, so 90 days hold far fewer independent examples than 2,160. ADR over
14 days moves slowly. A target inside the typical reach is not thereby likely to be hit.

## Parameters

All conventional and declared once at the top of the module with a one-line reason each. None
was tuned against outcomes. Windows count bars; sessions and hours come from the UTC clock.
