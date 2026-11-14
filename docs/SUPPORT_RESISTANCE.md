# Support and resistance: what the research says and how `engine15/levels.py` reads it

Written 2026-11-10 with the module. A reading, not an edge: nothing here is validated as
profitable, and section 5 shows why that sentence has to stay.

## 1. What the research says (only what changed the build)

**Is there anything to it?** Some, and it is modest.
- Osler (2000, NY Fed) tested support/resistance levels that six FX firms sent to clients
  against one-minute quotes and found "strong evidence that the levels help to predict
  intraday trend interruptions", with power that varied by firm and currency. She compared
  against thousands of arbitrary levels, which is the right test. It shows trends pause at
  levels more often than chance; it does not show a profit after costs.
  [paper](https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf),
  [abstract](https://www.fedinprint.org/item/fednep/19790)
- Osler (2003, Journal of Finance) gives the mechanism: take-profit orders cluster AT round
  numbers (so trends stall there) and stop-loss orders cluster just BEYOND them (so trends
  speed up once a level is crossed). This is why the module reads a bounce and a break as
  two different events and why a break is a close beyond the level, not a touch.
  [abstract](https://econpapers.repec.org/RePEc:bla:jfinan:v:58:y:2003:i:5:p:1791-1819)
- Kavajecz and Odders-White (2004, Review of Financial Studies): support and resistance
  levels coincide with peaks of resting depth in the limit order book. Levels mark liquidity.
  [abstract](https://econpapers.repec.org/RePEc:oup:rfinst:v:17:y:2004:i:4:p:1043-1071)
- Chung and Bellotti (2021, arXiv preprint, not peer reviewed): on intraday series, a level
  that price has bounced off more often is more likely to hold again, and that likelihood
  decays with time. Hence touches and a recency half-life in the strength score.
  [abstract](https://arxiv.org/abs/2101.07410)
- Against: Zapranis and Tsinaslanidis (2012) found on 20 years of US stocks that support
  predicts trend interruptions better than resistance, but neither beats buy-and-hold.
  Urquhart (2017) found Bitcoin prices cluster at round numbers but found no significant
  return pattern after one.
  [stocks](https://econpapers.repec.org/RePEc:taf:apfiec:v:22:y:2012:i:19:p:1571-1585),
  [bitcoin](https://econpapers.repec.org/RePEc:eee:ecolet:v:159:y:2017:i:c:p:145-148)

**Where the evidence is weak or absent.** Osler's levels were chosen by human analysts, not
by an algorithm, in FX in the 1990s. I found no rigorous study of volume-profile levels
(point of control, high-volume nodes): only vendor and broker pages, one of which admits
old points of control often go untouched for months
([LuxAlgo](https://www.luxalgo.com/library/concept/volume-profile.md)). I found no rigorous
study of prior-day high/low either; the nearest academic work is on intraday reversals after
opening moves in index futures, mixed after costs
([Grant, Wolf, Yu 2005](https://researchwith.montclair.edu/en/publications/intraday-price-reversals-in-the-us-stock-index-futures-market-a-1/)),
and a 2026 preprint in which every opening-range breakout variant failed out of sample
([arXiv 2605.04004](https://arxiv.org/pdf/2605.04004)). "Higher-timeframe levels matter
more" and "volume at the level" are practitioner conventions with no test behind them that
I could find. I could not open the full text of either Osler PDF from here, so the
statements above rest on their abstracts and on secondary summaries.

**How practitioners compute it** (open-source chart scripts agree on the pattern): confirmed
swing pivots, merged into zones whose width is a multiple of ATR rather than a percent,
scored by touch count and recency, penalised when price trades through them, kept after a
break in the opposite role ([examples](https://in.tradingview.com/scripts/support-resistance/)).
A pivot needing k bars on each side is known only k bars later; that lag is the price of not
repainting ([TA-Lib](https://ta-lib.org/functions/fractal.html),
[Williams fractal](https://www.luxalgo.com/library/concept/williams-fractal/)).

## 2. The design

**A level is one of:**
1. **Pivot zone.** A swing high is a bar whose high is at least the k highs before it and
   above the k highs after it (low: mirrored). It enters the level set k bars after it
   formed, never earlier. Four sizes on the 15m bars: k = 10, 20, 48, 192, i.e. 2.5 hours,
   5 hours, 12 hours and 2 days each side. These are the windows of a 10/10 pivot on 15m, a
   5-bar pivot on 1h, a 3-bar pivot on 4h and a 2-bar (Williams) fractal on 1D, so they
   stand for the 15m / 1h / 4h / 1D charts while keeping the exact wick price and time and
   not depending on where an hourly or daily bar happens to start. A swing joins the nearest
   zone within 0.25 hourly ATR (the zone centre is the mean of its swings) or starts one.
2. **Prior-day high, low, close** and **prior-week high, low**, from the last CLOSED UTC day
   and week (through `data.htf_on_15`; the week uses the same shift-then-join as evidence.py).
3. **Round numbers.** The grid is the largest 1 / 2.5 / 5 x 10^n step not above 2% of price
   (BTC 74,000: every 1,000; 40,000: every 500; ETH 2,100: every 25).

**Strength, 0 to 1.** For a pivot zone:
`(0.40 x touches/4 + 0.30 x timeframe weight + 0.20 x rejection + 0.10 x volume) x recency x 0.8^breaks`.
Touches are swings in the zone at least 4 hours apart, capped at 4. Timeframe weight is
0.25 / 0.50 / 0.75 / 1.00. Rejection is how far price left the swing within its k bars
(3 ATR = full). Volume is the swing bar's volume against the prior 24 hours (3x = full).
Recency halves every 20 x k bars without a touch (2, 4, 10, 40 days). Fixed levels have
fixed strengths. Levels within one zone-width of each other are read as ONE level whose
strength is 1 - product(1 - each), so confluence counts but never exceeds 1.

**Reading.** Support = the nearest level (or confluence) below the close with strength
>= 0.30; resistance = the nearest at or above it. Role reversal therefore needs no special
rule: a support that price closes through is above the close and is read as resistance. Its
zone is labelled "flipped", keeps 80% of its strength per break, and is dropped at the third.

**Events.** BREAK: a close more than 0.25 ATR beyond a level (close through resistance = +,
through support = -), sized by the strength broken. REJECTION: within the last 3 bars price
touched or wicked through a level that held its role, and the close is back on the original
side (bounce off support = +, rejection at resistance = -), sized by strength x recovery
(0.5 ATR from the wick = full). Each fades with a 1-hour half-life; the strongest recent
event stands until it has faded.

**No look-ahead.** Every input is causal: swings appear at swing row + k; day and week levels
after their close; ATR is the hourly ATR14 of closed hours. `tests/test_levels.py::test_no_lookahead`
builds on the full frame and on cut frames and requires identical rows before every cut.

**Speed.** One pass over the bars, a sorted list of at most 64 zones plus 9 fixed levels, a
few binary searches per bar. Full BTC history (275,303 bars): about 1.8 seconds.

## 3. Outputs

FEATURES (in [-1, 1], 0.0 = no read): `sr_sup_near`, `sr_res_near` (1 = on the level, 0 = 4
ATR away or none), `sr_sup_str`, `sr_res_str`, `sr_room` ((up - down)/(up + down)), `sr_lean`
(support strength x nearness minus resistance's), `sr_break`, `sr_reject`, `sr_pdh_near`,
`sr_pdl_near`, `sr_round_near` (0 = 1.5 ATR away), `sr_pd_pos` (place in the prior day's
range: -0.5 = its low, +0.5 = its high). READS: `sup_px`, `sup_str`, `sup_kind`,
`sup_touches`, `sup_dist_atr`, the same five for `res_`, `pd_high`, `pd_low`, `pd_close`,
`pw_high`, `pw_low`, `round_px`, `sr_event`. Also `sr_atr1h`, the yardstick used.

## 4. Every constant (declared once at the top of levels.py; none tuned on outcomes)

| Constant | Value | Why |
|---|---|---|
| SWING_K | 10, 20, 48, 192 | windows of the common 15m 10/10, 1h 5-bar, 4h 3-bar, 1D 2-bar pivots; also the delay |
| DEGREE_WEIGHT | .25 .5 .75 1 | higher timeframe counts more; a plain linear ladder |
| HALFLIFE_PER_K | 20 | strength halves in 2, 4, 10, 40 days untouched (Chung-Bellotti decay) |
| ZONE_HALF_ATR | 0.25 | a zone is half an hourly ATR wide: ATR, not percent |
| BREAK_ATR | 0.25 | a break is a close past the zone's far edge, not a wick (Osler: stops sit beyond) |
| TOUCH_SEP_BARS | 16 | swings under 4 hours apart are one touch |
| TOUCH_FULL | 4 | four touches = fully proven |
| REACT_FULL_ATR | 3.0 | a swing price left by 3 ATR = full rejection score |
| VOL_WINDOW, VOL_FULL | 96, 3.0 | swing-bar volume vs the prior 24h; 3x = full |
| W_TOUCH/DEGREE/REACT/VOLUME | .40 .30 .20 .10 | touches have the best evidence, volume the least |
| BREAK_KEEP, MAX_BREAKS | 0.8, 3 | chopped-through zones fade, then go |
| MAX_ZONES | 64 | bounds time and memory; weakest dropped first |
| S_PD_HILO, S_PD_CLOSE, S_PW_HILO | .50 .30 .70 | weekly above daily; the close least |
| ROUND_STEP_PCT | 0.02 | keeps grid numbers about 1-2% of price apart |
| S_ROUND | .20 .40 .60 | a plain grid number only adds to a level; rounder numbers stand alone |
| MIN_STRENGTH, STRONG | 0.30, 0.60 | least strength to be read; the journal's "strong" and its bar for naming an event |
| SEARCH_ATR, DIST_CLIP_ATR | 10, 4 | not read beyond 10 ATR; features call 4 ATR "far" |
| NEAR_ATR | 1.5 | "near" a named level = within the engine's barrier |
| REJ_LOOKBACK, REJECT_FULL_ATR | 3, 0.5 | touch within 3 bars; 0.5 ATR recovery = full |
| EVENT_HALFLIFE | 4 | events fade in about an hour |

Two values were changed during the build after looking at how often things appeared (never
at what price did next): S_ROUND was lowered from .30/.50/.70 because plain grid numbers
were half of all reads on a random walk, and the journal's event bar was raised from 0.30 to
0.60 because 3 bars in 10 carried an event sentence.

## 5. One descriptive statistic (BTC, 2019-01 to 2026-11-10; a description, not an edge)

Event: the first bar in 16 whose close is within 0.25 ATR of a STRONG level (>= 0.60).
Over the next 16 bars: *broke* = a close more than 0.25 ATR beyond it; *reversed* = no break
and the close 16 bars later at least 1 ATR away on the original side; *stalled* = neither.
Placebo: the same rule 7 days earlier with a made-up level at the same distance.

| | n | reversed | stalled | broke |
|---|---|---|---|---|
| strong levels | 6,625 | 17.2% | 19.6% | 63.2% |
| placebo (arbitrary level) | 6,625 | 15.9% | 23.8% | 60.3% |

Strong levels were closed through slightly MORE often than arbitrary ones (+2.9 points,
standard error about 0.8) and reversed slightly more often (+1.3); price stalled less at
them. Ordinary levels (0.30 to 0.60, n = 8,118) look the same: 15.2 / 21.1 / 63.6% against
14.9 / 23.8 / 61.3%. On this definition the levels do not hold better than chance. Treat
every feature here as an unproven reading and let the voices' graded trust decide.

## 6. Known weaknesses

- No demonstrated holding power (section 5). The placebo is crude: it is not matched on how
  price approached the level.
- Levels are dense: after warm-up a support and a resistance exist 99% of the time, the
  nearest a median 0.6 ATR away. "Nearest meaningful level" is a permissive reading.
- The strength formula and its weights are a judgement. Nothing was fitted.
- Swings are known late by construction (2.5 hours to 2 days). Only the rejection event sees
  a fresh turn early, and only at a level already known.
- Memory is bounded: a zone untouched for several half-lives is forgotten, so last year's
  all-time high is not a level here unless price has swung there recently.
- No volume profile (15-minute bars cannot place volume at a price, and no rigorous evidence
  was found) and no order-book data, which is where Osler and Kavajecz locate the mechanism.
- The round grid changes when price crosses 12,500 / 25,000 / 50,000 / 125,000 (and their
  powers of ten); round levels are rebuilt there.
- The same extreme can count twice in a confluence (a day's high is usually also a swing).
- UTC day and week boundaries are a convention; crypto has no session close.
