# Moving averages, the ribbon, and averages as support and resistance (`engine15/sources/mavg.py`)

Owner, 11 Nov 2026: "Adding moving average reading also. Using simple and exponential on 5, 10,
20, 50 and 200", a moving-average ribbon "to assist engine directional trade", and "sometimes
support and resistance can be in moving average structure rather than just a horizontal line."

Three cards, built only from the asset's own 15-minute bars. Nothing is downloaded. They work the
same on BTC, ETH, gold, silver, USDJPY and the S&P 500 (cash hours only).
**Nothing here is claimed to predict anything.** Moving averages are a charting convention; these
cards turn them into readings the engine learns from and the owner reads. Whether any of them helps
is for graded calls and forward results to say.

## What is new compared with "Timeframe strength"

The Timeframe strength card (`indicators.trend_score`) already folds EMA/SMA 5-200 position, stack
and slope into one number between -1 and +1 per timeframe. That number hides what a trader looks at:
where the averages actually are, how far price is from them, when they crossed, the shape of the
ribbon, and whether an average is acting as a floor or a ceiling. These cards show exactly that.

## The one rule

A row uses only what was known at that 15-minute close. The 15m readings look backwards only. The
1h, 4h and 1d readings are computed on hourly, four-hour and daily bars and reach a 15m row only once
that bar has **closed** (the same lookup as `data.htf_on_15`). So "1d" always means the last
completed day, never today's unfinished one. `tests/test_mavg.py` cuts the future off at several
points (some in the middle of an hour or a day, on BTC, the S&P 500 with its gaps, and planted data)
and checks that no column changes.

**ATR** in these cards is Wilder's ATR(14) of the same timeframe: a 4h distance is measured in 4h
ATRs, a daily one in daily ATRs. The EMAs are seeded with the simple average of their first N closes
and shown after 2 x N bars (the trend map's rule), so the daily 200 EMA needs 400 days of history.

## Card 1: Moving averages (SMA and EMA 5-200), voice `mavg`

On 15m, 1h, 4h and 1d, the ten averages: SMA and EMA of 5, 10, 20, 50 and 200 closes.

- **Prices** of all ten (`ma_{tf}_{sma|ema}{n}_px`) and the close's distance from each, in % and in
  ATR (the card works these out from the price, the close `ma_close` and the ATR `ma_{tf}_atr`).
- **Above k of 10**: how many of the ten averages price is above.
- **Stack**: per family, fully bullish (5 > 10 > 20 > 50 > 200), fully bearish, or mixed, and which
  pair breaks the order ("EMA 20 under EMA 50").
- **Slope** of the 20, 50 and 200: change over that timeframe's last 3 bars, in ATR.
- **Crosses**, with their age in bars of their own timeframe and the price at the cross:
  EMA 5/10, EMA 10/20, EMA 20/50, SMA 50/200 (golden cross up, death cross down), price through the
  EMA 20 and price through the 200 SMA. The direction is today's order of the two lines.

Features (0 = no read):

| Feature | Meaning |
|---|---|
| `ma_share_1h/4h/1d` | (averages price is above minus averages it is below) / averages known: +1 = above all ten |
| `ma_stack_1h/4h/1d` | stack alignment: +1 both families fully bullish, -1 fully bearish |
| `ma_cross_1h/4h/1d` | recent crosses, signed, each fading to nothing over 12 bars; slow crosses weigh more (golden/death 3, EMA 20/50 and price/200 2, the rest 1) |
| `ma_d200_4h/1d` | distance from the 200 SMA in ATR, squashed: tanh(ATRs / 4) |
| `ma_slope50_4h/1d` | slope of the 50 (mean of SMA and EMA), tanh(ATRs per 3 bars / 0.5) |

## Card 2: Moving-average ribbon, voice `ribbon`

On 15m and 1h, five EMAs of Fibonacci lengths 8, 13, 21, 34 and 55, plus the Guppy multiple moving
average: a short group (EMA 3, 5, 8, 10, 12, 15) and a long group (EMA 30, 35, 40, 45, 50, 60).

- **Order**: in order up (8 above 13 above ... above 55), in order down, or tangled.
- **Width**: top line minus bottom line, in ATR; **widening or compressing** over the last 4 bars.
- **Price** above how many of the five lines.
- **Last full re-order**: bars since the five lines last snapped into full order, and which way.
- **Guppy**: short-group average minus long-group average, in ATR; whether the two groups are
  interwoven (crossing) or apart; bars since the group averages crossed.

Features: `rb_order_*` (+1 all in order up, -1 all down, in quarters between), `rb_width_*` (width,
signed by the ribbon's direction, tanh(ATRs / 3)), `rb_expand_*` (width change over 4 bars signed by
the ribbon's direction: + = an up ribbon widening or a down ribbon compressing), `rb_pos_*` (price
inside the ribbon: -0.5 at the bottom line, +0.5 at the top, +-1 one ribbon-width outside it),
`rb_gmma_*` (Guppy separation, tanh(ATRs / 2)).

## Card 3: Moving averages as support and resistance, voice `mavg_sr`

On 15m, 1h, 4h and 1d, the averages that act as levels: EMA and SMA 20, 50 and 200. (The 5 and 10
track price within a bar or two, so they are read on card 1, not treated as levels.)

- **Nearest average below price** (dynamic support) and **above** (dynamic resistance): which, its
  price, distance in ATR and %.
- **Tested on this bar**: the bar's low came within 0.25 ATR of an average with the previous close
  above it (a support test), or the high came within 0.25 ATR with the previous close below it (a
  resistance test). **Held** = the bar closed back on its side; **broke** = it closed through.
- **Counted tests**: a touch counts as a test only if price had closed at least 0.5 ATR away from
  the average since the previous touch, so price hugging the line is one test, not twenty.
- **Last test**: which average, held or broke, how many bars ago.
- **Respect record**: per average, held versus broke over its last 20 counted tests (12 on 4h, 10 on
  1d). It says whether the market has lately been respecting that average.
- **Confluence** (in the sentence and the readable rows): whether the tested average sits within
  0.25 of the 1-hour ATR of a horizontal level (support/resistance, prior day/week high, low and
  close, round numbers from `levels.py`), a Fibonacci level (`fib.py`), or another timeframe's
  average. Read from the evidence row when those cards are present. Stacked levels are counted.

Features: `mas_room_1h/4h` (room to the nearest average above minus room to the nearest below, each
capped at 3 ATR, / 3: + = support close below and open air above), `mas_test_15m/1h/4h` (+1 = testing
support that held in an uptrend, -1 = resistance that held in a downtrend; uptrend = EMA 20 above
EMA 50 with the EMA 50 rising), `mas_hold_15m/1h/4h` (the tested average's hold share minus 0.5,
signed + for support and - for resistance; 0 with no test or fewer than 3 on record).

## Reading the sentences

- "4h: price above 9 of 10 averages, both stacks fully bullish, EMA 20/50 crossed up 6 bars ago at
  74,120, 1.8 ATR (2.40%) above the 200 SMA (70,950)"
- "1h ribbon in order up for 34 bars, widening, 2.1 ATR wide; price above all five lines; Guppy short
  group 1.3 ATR above the long group, apart since they crossed 40 bars ago"
- "1h: testing the EMA 50 (74,020) from above; it held 7 of its last 9 tests; it sits with the 1h
  0.618 Fib (74,050) and a horizontal support (73,980)"

"4h (last closed bar)" and "1d (last closed bar)" mean the test happened on the last completed 4h
bar or day, which may be some hours old.

## Limits, stated plainly

- Averages lag by construction; a cross is old news by the time it prints, more so on 4h and 1d.
- Constants (fade 12 bars, squash scales, 0.25 / 0.5 ATR, record lengths) are conventional values
  declared once in the module's constant block and not tuned against outcomes.
- The S&P 500 trades 26 bars a day, so its daily 200 SMA covers 200 sessions and its 15m 200 covers
  about eight sessions; the averages there span calendar time differently from crypto.
- The readable columns are stored as float32 (about seven significant digits) to keep the frame
  small: about 35 MB for a year of 15m rows. The features go to the model as float64 as usual.
- About 250 columns; full history for one asset takes about one second.
