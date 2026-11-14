# Market-state map (charter L2)

Generated 2026-11-10 16:27. Coins: BTCUSDT, ETHUSDT. History 2020-01-01 to 2026-11-10, split in two halves: **2020-01 to 2023-06** and **2023-06 to 2026-11**. Cut points were fixed on the first half only, so the second half is out of sample.

**These are leads, not proven edges.** History can reject an idea, never prove one; anything worth keeping goes into `research/HYPOTHESES.md` and is graded forward.

## How to read this

Every closed 15-minute bar is put in a state from six readings known at its close:

- **vol** (quiet / normal / wild): volatility: the last hour's average 15m range against its 30-day average (terciles)
- **trend** (down / mixed / up): trend: 4h AND daily trend scores both DOWN (<= -0.5) / both UP (>= +0.5) / anything else
- **session** (Asia / London / London+NY overlap / New York / weekend): session by the UTC hour of the bar's close: Asia 22-07, London 07-12, overlap 12-16, New York 16-22; Saturday and Sunday = weekend
- **flow** (selling / balanced / buying): order flow: net taker buying over the last 4 hours as a share of volume (terciles)
- **place** (near 24h low / middle of 24h range / near 24h high): place: where the close sits in the last 24 hours' high-low range (terciles)
- **move** (fell / flat / rose): recent move: the last hour's return in units of the 1-hour ATR14 (terciles)

Cut points (first half): BTC vol 0.67/1.04, flow -0.032/+0.004, place 0.38/0.70, move -0.19/+0.21 ATR; ETH vol 0.68/1.05, flow -0.026/+0.020, place 0.39/0.71, move -0.20/+0.22 ATR.

For each state (and each pair of states) we look at what happened next if you entered at the next 15-minute open: the % move over 15 minutes, 1 hour and 4 hours, and the triple-barrier trade (one unit = 1.5 x the 1-hour ATR above and below; whichever is touched first, within 4 hours or 24 hours). 'Independent' counts overlapping holding periods once. A cell is listed only if it leans the same way in all four tests: BTC first half, BTC second half, ETH first half, ETH second half.

Average bar, for comparison (no state at all): BTC first half: next 4h +0.029% (up 51.2% of the time); BTC second half: next 4h +0.018% (up 51.2% of the time); ETH first half: next 4h +0.054% (up 51.9% of the time); ETH second half: next 4h +0.010% (up 50.9% of the time).

## The luck count (charter L4)

- Cells examined: **185** (states and pairs of states with at least 30 independent cases in every test).
- Tests made: **1480** (cells with >= 30 independent cases in all four tests x 4 outcome measures (f4, f16, tb16, tb96) x 2 sides).
- Passed 'consistent' (same side in all four tests, t >= 2 in each): **1**. Pass after fees (worst test still clears 0.20%, t >= 1 in each): **0**.
- Placebo: the same scan with the states slid in time against the outcomes (30 runs), i.e. states that cannot know anything: 'consistent' passed 0.5 on average (95th percentile 2.5, max 5.0); 'pays the fee' passed 0.0 on average (max 0.0). 8 of 30 placebo runs matched or beat the real 'consistent' count.
- Simple binomial: with no real effect, 92 tests would lean the same way in all four tests by chance if the four were independent (1 in 16); if BTC and ETH were the same coin, about 0.77 tests would pass 'consistent' by luck.
- Cells overlap (a pair contains its singles) and BTC and ETH move together, so the binomial numbers are rough bounds; the placebo (states slid in time, both coins by the same amount) keeps all of that structure and is the number to trust.

## Cells that lean the same way everywhere AND clear the fee

**None.** No state or pair of states leaned the same way in all four tests by enough to pay a 0.20% round trip in its worst test. On its own, no coarse state is a trade.

## Consistent cells that do not clear the fee on their own

These lean the same way, strongly, in all four tests, but the move is too small to pay the fee as a stand-alone trade. They are candidates for a filter (when to sit out, which side the mandate should force) or for timing inside a bigger-picture trade.

### 1. session=New York -> LONG, judged over the next 4 hours

**In plain words:** when it is the New York afternoon (16:00-22:00 UTC, weekdays), a LONG entered at the next 15m open and judged over the next 4 hours made at least +0.047% a trade in every one of the four tests (two coins x two halves) before fees; after the 0.20% round-trip fee the worst test is at -0.153%. The weakest test has t = 2.0.

| Coin | Half | Cases | Independent | Mean (long) % | Median % | Share up | Share down | t | 24h barrier: up first / down first |
|---|---|---|---|---|---|---|---|---|---|
| BTC | 2020-01 to 2023-06 | 21457 | 2284 | +0.074 | +0.079 | 54.3% | 45.7% | 2.2 | 47.8% / 45.5% |
| BTC | 2023-06 to 2026-11 | 21463 | 1789 | +0.047 | +0.041 | 52.7% | 47.3% | 2.0 | 46.0% / 44.5% |
| ETH | 2020-01 to 2023-06 | 21457 | 2284 | +0.093 | +0.116 | 54.5% | 45.4% | 2.3 | 49.1% / 46.1% |
| ETH | 2023-06 to 2026-11 | 21463 | 1789 | +0.075 | +0.059 | 53.3% | 46.7% | 2.3 | 47.1% / 45.2% |

## Near misses (same side in all four tests, but weaker)

These lean the same way in all four tests but at least one test has t below 2. Weaker leads; listed so they can be watched, not traded.

### 2. trend=up & move=fell -> LONG, judged over the next hour

**In plain words:** when the 4h and daily trends are both UP and the last hour FELL (bottom third, in 1h-ATR units), a LONG entered at the next 15m open and judged over the next hour made at least +0.019% a trade in every one of the four tests (two coins x two halves) before fees; after the 0.20% round-trip fee the worst test is at -0.181%. The weakest test has t = 1.8.

| Coin | Half | Cases | Independent | Mean (long) % | Median % | Share up | Share down | t | 24h barrier: up first / down first |
|---|---|---|---|---|---|---|---|---|---|
| BTC | 2020-01 to 2023-06 | 10498 | 4891 | +0.019 | +0.052 | 55.1% | 44.9% | 1.8 | 47.1% / 48.5% |
| BTC | 2023-06 to 2026-11 | 11210 | 5115 | +0.023 | +0.028 | 54.0% | 46.0% | 3.5 | 49.5% / 45.2% |
| ETH | 2020-01 to 2023-06 | 11706 | 5447 | +0.040 | +0.073 | 55.3% | 44.6% | 3.1 | 48.6% / 48.7% |
| ETH | 2023-06 to 2026-11 | 7789 | 3557 | +0.022 | +0.042 | 54.0% | 45.9% | 2.1 | 48.4% / 47.5% |

### 3. session=New York & flow=balanced -> LONG, judged over the next 4 hours

**In plain words:** when it is the New York afternoon (16:00-22:00 UTC, weekdays) and taker flow over the last 4 hours is balanced (middle third), a LONG entered at the next 15m open and judged over the next 4 hours made at least +0.068% a trade in every one of the four tests (two coins x two halves) before fees; after the 0.20% round-trip fee the worst test is at -0.132%. The weakest test has t = 1.8.

| Coin | Half | Cases | Independent | Mean (long) % | Median % | Share up | Share down | t | 24h barrier: up first / down first |
|---|---|---|---|---|---|---|---|---|---|
| BTC | 2020-01 to 2023-06 | 7531 | 1465 | +0.080 | +0.097 | 55.3% | 44.7% | 1.9 | 47.8% / 44.3% |
| BTC | 2023-06 to 2026-11 | 4013 | 1057 | +0.068 | +0.047 | 53.1% | 46.9% | 2.1 | 48.8% / 41.9% |
| ETH | 2020-01 to 2023-06 | 7927 | 1531 | +0.097 | +0.165 | 55.8% | 44.1% | 1.8 | 49.3% / 45.3% |
| ETH | 2023-06 to 2026-11 | 5472 | 1163 | +0.100 | +0.083 | 54.3% | 45.7% | 2.4 | 48.7% / 43.1% |

### 4. session=New York & move=rose -> LONG, judged over the next 4 hours

**In plain words:** when it is the New York afternoon (16:00-22:00 UTC, weekdays) and the last hour ROSE (top third, in 1h-ATR units), a LONG entered at the next 15m open and judged over the next 4 hours made at least +0.044% a trade in every one of the four tests (two coins x two halves) before fees; after the 0.20% round-trip fee the worst test is at -0.156%. The weakest test has t = 1.8.

| Coin | Half | Cases | Independent | Mean (long) % | Median % | Share up | Share down | t | 24h barrier: up first / down first |
|---|---|---|---|---|---|---|---|---|---|
| BTC | 2020-01 to 2023-06 | 7444 | 1827 | +0.087 | +0.031 | 51.7% | 48.3% | 2.4 | 48.1% / 45.2% |
| BTC | 2023-06 to 2026-11 | 8062 | 1700 | +0.044 | -0.012 | 49.4% | 50.6% | 1.8 | 46.0% / 45.3% |
| ETH | 2020-01 to 2023-06 | 7497 | 1823 | +0.102 | +0.051 | 51.9% | 48.1% | 2.3 | 49.5% / 45.4% |
| ETH | 2023-06 to 2026-11 | 7523 | 1683 | +0.098 | +0.007 | 50.4% | 49.6% | 2.8 | 47.0% / 45.3% |

### 5. place=near 24h high & move=fell -> LONG, judged over the next 4 hours

**In plain words:** when price sits in the top third of its last-24h range and the last hour FELL (bottom third, in 1h-ATR units), a LONG entered at the next 15m open and judged over the next 4 hours made at least +0.039% a trade in every one of the four tests (two coins x two halves) before fees; after the 0.20% round-trip fee the worst test is at -0.161%. The weakest test has t = 1.7.

| Coin | Half | Cases | Independent | Mean (long) % | Median % | Share up | Share down | t | 24h barrier: up first / down first |
|---|---|---|---|---|---|---|---|---|---|
| BTC | 2020-01 to 2023-06 | 8604 | 2566 | +0.056 | +0.008 | 50.5% | 49.5% | 2.1 | 49.9% / 46.2% |
| BTC | 2023-06 to 2026-11 | 8349 | 2429 | +0.039 | -0.003 | 49.8% | 50.2% | 2.1 | 49.3% / 46.0% |
| ETH | 2020-01 to 2023-06 | 8482 | 2553 | +0.167 | +0.061 | 52.3% | 47.7% | 4.9 | 51.9% / 45.2% |
| ETH | 2023-06 to 2026-11 | 7238 | 2256 | +0.045 | -0.025 | 48.7% | 51.3% | 1.7 | 49.3% / 46.4% |

### 6. session=London & move=rose -> LONG, judged over the next hour

**In plain words:** when it is the London session (07:00-12:00 UTC, weekdays) and the last hour ROSE (top third, in 1h-ATR units), a LONG entered at the next 15m open and judged over the next hour made at least +0.013% a trade in every one of the four tests (two coins x two halves) before fees; after the 0.20% round-trip fee the worst test is at -0.187%. The weakest test has t = 1.6.

| Coin | Half | Cases | Independent | Mean (long) % | Median % | Share up | Share down | t | 24h barrier: up first / down first |
|---|---|---|---|---|---|---|---|---|---|
| BTC | 2020-01 to 2023-06 | 5976 | 2903 | +0.022 | -0.016 | 48.5% | 51.4% | 1.7 | 48.5% / 47.8% |
| BTC | 2023-06 to 2026-11 | 6193 | 2988 | +0.013 | -0.006 | 49.0% | 51.0% | 1.6 | 50.6% / 48.0% |
| ETH | 2020-01 to 2023-06 | 5992 | 2897 | +0.032 | -0.019 | 48.4% | 51.4% | 2.0 | 53.4% / 43.6% |
| ETH | 2023-06 to 2026-11 | 5801 | 2862 | +0.028 | -0.003 | 49.6% | 50.4% | 2.5 | 48.1% / 49.6% |

### 7. place=near 24h high -> LONG, judged over the next hour

**In plain words:** when price sits in the top third of its last-24h range, a LONG entered at the next 15m open and judged over the next hour made at least +0.007% a trade in every one of the four tests (two coins x two halves) before fees; after the 0.20% round-trip fee the worst test is at -0.193%. The weakest test has t = 1.6.

| Coin | Half | Cases | Independent | Mean (long) % | Median % | Share up | Share down | t | 24h barrier: up first / down first |
|---|---|---|---|---|---|---|---|---|---|
| BTC | 2020-01 to 2023-06 | 40040 | 11931 | +0.016 | -0.020 | 47.9% | 52.1% | 2.4 | 49.5% / 47.0% |
| BTC | 2023-06 to 2026-11 | 38145 | 11480 | +0.007 | -0.019 | 47.3% | 52.7% | 1.6 | 49.4% / 46.2% |
| ETH | 2020-01 to 2023-06 | 40040 | 11907 | +0.029 | -0.027 | 47.8% | 52.1% | 3.5 | 50.8% / 46.2% |
| ETH | 2023-06 to 2026-11 | 35406 | 10711 | +0.013 | -0.024 | 47.1% | 52.8% | 2.1 | 49.8% / 46.5% |

## The map, one dimension at a time

Mean % move over the next 4 hours after each state (entry at the next open), and how often the engine's 24-hour barrier was touched up first minus down first, in points.

| State | BTC H1 4h % | BTC H2 4h % | ETH H1 4h % | ETH H2 4h % | BTC H1 up-down | BTC H2 up-down | ETH H1 up-down | ETH H2 up-down |
|---|---|---|---|---|---|---|---|---|
| vol=quiet | +0.030 | +0.006 | +0.035 | -0.010 | -0.5 | +4.4 | +0.5 | +1.5 |
| vol=normal | +0.034 | +0.003 | +0.038 | -0.005 | -1.1 | -0.8 | +1.5 | -2.3 |
| vol=wild | +0.024 | +0.042 | +0.090 | +0.044 | +0.1 | +0.9 | +2.2 | -0.5 |
| trend=down | +0.017 | +0.040 | +0.022 | +0.019 | -2.3 | +0.3 | -2.1 | +0.6 |
| trend=mixed | +0.023 | +0.005 | +0.035 | +0.005 | -0.1 | +0.8 | +2.4 | -0.9 |
| trend=up | +0.051 | +0.035 | +0.105 | +0.018 | -0.1 | +4.2 | +1.3 | +0.2 |
| session=Asia | +0.004 | +0.018 | -0.010 | +0.026 | -2.6 | +0.3 | -0.6 | -0.4 |
| session=London | +0.081 | +0.013 | +0.117 | -0.020 | +0.3 | +0.4 | +5.1 | -4.8 |
| session=London+NY overlap | +0.013 | -0.004 | +0.100 | -0.085 | -0.6 | -0.6 | +0.4 | -8.0 |
| session=New York | +0.074 | +0.047 | +0.093 | +0.075 | +2.3 | +1.5 | +3.0 | +1.9 |
| session=weekend | +0.004 | +0.011 | +0.039 | +0.009 | -0.6 | +4.7 | +0.9 | +3.9 |
| flow=selling | +0.046 | +0.019 | +0.064 | -0.018 | -0.5 | +0.5 | -0.9 | -1.9 |
| flow=balanced | +0.021 | +0.026 | +0.075 | +0.052 | -0.9 | +2.8 | +2.5 | +1.5 |
| flow=buying | +0.019 | +0.013 | +0.025 | +0.017 | -0.2 | +2.7 | +2.8 | +0.3 |
| place=near 24h low | +0.003 | +0.021 | +0.010 | +0.003 | -3.4 | -0.5 | -2.5 | -2.3 |
| place=middle of 24h range | +0.029 | +0.010 | +0.042 | -0.008 | -0.6 | +2.5 | +2.2 | -1.5 |
| place=near 24h high | +0.056 | +0.023 | +0.112 | +0.040 | +2.5 | +3.2 | +4.6 | +3.3 |
| move=fell | +0.033 | +0.024 | +0.062 | +0.004 | -0.4 | +1.3 | +0.4 | -1.9 |
| move=flat | +0.023 | +0.017 | +0.035 | +0.000 | -1.5 | +2.5 | +0.6 | +0.5 |
| move=rose | +0.031 | +0.013 | +0.066 | +0.027 | +0.5 | +1.3 | +3.3 | +0.4 |

## Limits

- Fills at the next open with a flat 0.10% a side; no slippage, no funding.
- The barrier P&L counts a 'neither' (and a bar that touches both barriers) at the horizon's close.
- States are coarse on purpose; 185 cells and 4 outcome measures make many tests, see the luck count.
- 'Independent' is the number of distinct holding-period blocks a cell touches; it is an approximation.
- Full tables for every cell are in `state_map.json` (key `cells`).

