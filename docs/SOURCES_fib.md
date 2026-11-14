# Fibonacci retracement and extension (`engine15/sources/fib.py`)

Owner, 11 Nov 2026: "include fibonacci retracement skill into the AI engine to help it plan
entry and exit". This card serves charter tasks **A** (timing an entry on a pullback inside a
larger move) and **B** (exits: a target that is realistic, and a price that says the idea is wrong).

It is one voice, **Fibonacci retracement** (`fib`), built only from the asset's own 15-minute
bars. Nothing is downloaded. It works the same on BTC, ETH, gold, silver, USDJPY and the S&P 500.
**Nothing here is claimed to predict anything.** Fibonacci ratios are a charting convention; this
card turns them into readings the engine learns from and the owner reads. Whether any of them
helps is for graded calls and forward results to say.

## The one rule

A row uses only what was known at that 15m close. Swings are **confirmed** swings (structure.py's
definition: a swing high is the highest high of the K bars either side, K = 3 on 1h and 4h, 2 on
1d), so a swing is known only K bars after it formed. Each timeframe reaches the 15m rows through
`data.htf_on_15`: an hour, four hours or a day counts only once it has closed. The deepest
retracement is a running maximum. `tests/test_fib.py::test_no_lookahead` cuts the future off at
several bars (some in the middle of an hour) and checks that no column changes.

## The leg

On each of 1h, 4h and 1d the card keeps one **impulse leg**: origin to end.

- **Up-leg** (swing low to swing high). A higher swing high extends it; if a pullback low was
  confirmed since the old high, the leg is redrawn from that low (the newest impulse). A lower
  swing high is ignored (it is part of the pullback). A swing low above the origin is the pullback
  low that held. A swing low **below the origin** breaks the leg: a new down-leg starts from the
  old high.
- **Down-leg**: the mirror.

So a pullback that holds keeps the leg; only a confirmed break of the origin flips it. Between
the moment price crosses the origin and the moment the new swing confirms (3 hours on 1h, 12 on
4h, 2 days on 1d), the card says the leg is broken but still shows the old one.

When the 4h (or 1d) leg is the very same leg as the 1h (same origin and end, common when one big
move dominates), the card says so and does not count it twice for confluence.

## The levels

For a leg from origin O to end E, every level is `E - r x (E - O)`:

| Level | r | Use |
|---|---|---|
| 0.236, 0.382 | shallow retracements | a strong trend often pauses here |
| 0.5 to 0.618 | the **golden zone** | the classic pullback entry |
| 0.618 | `fib_<tf>_entry_px` | the pullback entry price |
| 0.786 | `fib_<tf>_inval_px` | invalidation: a close beyond it says the leg has failed |
| 1.272 | `fib_<tf>_t1_px` = O + 1.272 (E - O) | first target, beyond the leg end |
| 1.618 | `fib_<tf>_t2_px` = O + 1.618 (E - O) | second target |

**Depth** = (E - close) / (E - O): 0 at the leg end, 0.5 half way back, 1 back at the origin;
below 0 means price is beyond the leg end (extending), above 1 beyond the origin.

## Readable columns (prices, ratios, percentages; NaN = no read)

Per timeframe `<tf>` in 1h, 4h, 1d:

| Column | Meaning |
|---|---|
| `fib_<tf>_dir` | +1 up-leg, -1 down-leg, 0 none |
| `fib_<tf>_origin_px`, `fib_<tf>_end_px` | the leg's two swing prices |
| `fib_<tf>_end_age_h` | hours from the leg end's bar to this close |
| `fib_<tf>_depth`, `fib_<tf>_maxdepth` | retracement now, and the deepest close since the leg was known |
| `fib_<tf>_gz` | 1 when price is in the golden zone and the 0.786 has not been broken |
| `fib_<tf>_broken` | 1 once a close went beyond the 0.786 of this leg (sticky until the leg changes) |
| `fib_<tf>_r236_px`, `_r382_px`, `_r500_px`, `_entry_px`, `_inval_px`, `_t1_px`, `_t2_px` | the level prices |
| `fib_<tf>_near_lvl`, `fib_<tf>_near_atr` | the nearest level (0.236 ... 1.618) and its distance in ATR(1h) |
| `fib_<tf>_rr` | reward / risk if entered **now** in the leg's direction: distance to the 1.272 over distance to the 0.786 (NaN beyond the 0.786; 0 past the target) |
| `fib_<tf>_t1_pct` | distance to the 1.272 in % of price, + = still ahead |
| `fib_<tf>_t1_reach_x` | that distance over the realistic 24h reach (1.0 = one typical day's travel) |

Shared: `fib_close_px`, `fib_atr1h_px` (Wilder ATR(14) of the 1h chart), `fib_reach24_pct` and
`fib_reach24_p80_pct` (ltf.py's realistic reach: the median and 80th-percentile move in either
direction within 24 hours over the last 90 days, scaled to today's ATR; identical to ltf's
`reach_24h_*_pct`), `fib_conf_n` (fib levels of all three legs within 0.25 ATR of price),
`fib_cluster_px` and `fib_cluster_atr` (the nearest price where levels of two different legs lie
within 0.25 ATR of each other, and its distance from price in ATR, + = above).

**Is the target realistic?** The card compares the 1.272's distance with the realistic reach:
at most a typical day's travel = "realistic within a day"; up to a large day's (80th percentile)
= "a stretch for one day"; more = "not realistic within a day".

## Model features (one voice; 0.0 = no read; all within [-1, 1])

| Feature | Reading |
|---|---|
| `fib_gz_1h`, `fib_gz_4h` | signed golden-zone pullback: leg direction x 1 in the golden zone, x 0.5 in the bands either side (0.382-0.5, 0.618-0.786), 0 elsewhere or once the 0.786 broke |
| `fib_depth_1h`, `fib_depth_4h` | leg direction x depth (clipped to -1 ... 1.5) / 1.5 |
| `fib_conf` | signed confluence at price: each level within 0.25 ATR adds the leg direction if it is a retracement (support under an up-leg) and subtracts it if it is an extension (a target, where a move may stall); sum / 3, clipped |
| `fib_room_1h` | 1h leg direction x (distance to the 1.272 / realistic 24h reach), clipped to -1 ... 2, / 2 |
| `fib_rr_1h` | 1h leg direction x log2(reward/risk now), clipped at +/-2, / 2 (R/R 1 = 0, 4 = full; target already passed = -1) |

The signs follow the leg: + leans with an up-leg, - with a down-leg. The model decides from graded
calls what, if anything, each is worth.

## How a trader would read the card

"1h up-leg 73,100 -> 75,400; price 74,300 is at the 0.48 retracement, a shallow pullback above the
golden zone 73,979-74,250; invalid below 73,592 (0.786); targets 76,026 (1.272) and 76,821 (1.618)."
Plan in that reading: a pullback entry near 73,979 (0.618), a stop beyond 73,592, a first target
at 76,026, and the card says whether that target is within a normal day's travel.

## Limits, stated plainly

- **Which swings make "the" leg is a choice.** Different swing sizes give different legs and
  different levels; a trader drawing by eye may pick another pair of points. K is structure.py's.
- **Confirmation lag.** A swing is known 3 bars (1h, 4h) or 2 days (1d) after it formed, so a
  fresh leg end appears late, and a broken origin flips the leg late.
- **Big legs.** The leg flips only on a break of its origin, so in a long range the 1h leg can
  stay the same for days (a median 1h leg spans about 9 ATR(1h) on BTC).
- **Levels are not walls.** Price trades through fib levels all the time; 0.25 ATR "at a level"
  and the golden zone are conventions, not tuned values. No constant here was fitted to outcomes.
- **Reward/risk** uses the 0.786 as the stop and the 1.272 as the target; it ignores fees,
  slippage and whether either is ever reached.
- **Markets with sessions** (gold, silver, USDJPY, the S&P 500): hours and days are UTC clock
  buckets of the bars that exist; a weekend or a closed session is simply absent, and a 4h or
  daily bar may hold only part of a session.
- Realistic reach needs 30 days of history before it reads; until then `fib_room_1h` is 0.
