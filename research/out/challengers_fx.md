# Challenger books on recent history (IN-SAMPLE, not proof)

Written by `research/challengers.py` on 2026-11-11 09:00 UTC. Every book starts flat with $10,000 per asset at the window's start and trades the same odds the live step would have formed (voices walked forward from 240 days back; trained on the last 700 days of bars, not all history as live does). Fees as live. Paper only.

**Read this plainly:** one 120-day window that the rules' authors had already lived through; the H3 limit was chosen from a grid on this kind of history; six assets that move together. A history read can reject an idea, never prove one. Promotion is decided on forward results (docs/CHARTER.md).

## All six assets together ($60,000 start)

| Book | P&L | Return | vs main | Max drawdown | First half | Second half | Trades | Win rate | Avg R | Fees |
|---|---|---|---|---|---|---|---|---|---|---|
| Main rule (v5), fresh copy (`main`) | $+4975 | +49.75% | $+0 | -13.42% | +50.41% | -0.44% | 23 | 43.5% | +1.079 | $362 |
| v4: no higher-timeframe bias (H4) (`v4`) | $+4209 | +42.09% | $-765 | -13.10% | +30.29% | +9.06% | 17 | 29.4% | +1.314 | $251 |
| H3: limit on flip exits (`h3_flip_limit`) | $+4771 | +47.71% | $-204 | -13.61% | +48.61% | -0.61% | 23 | 39.1% | +1.084 | $355 |
| B: half at Target 1, rest at Target 2 (`b_targets`) | $-1259 | -12.59% | $-6234 | -23.26% | -2.64% | -10.22% | 52 | 44.2% | -0.112 | $610 |
| B: trailing swing / 2 ATR stop after 1R (`b_trail`) | $-2019 | -20.19% | $-6994 | -24.26% | -11.59% | -9.73% | 88 | 50.0% | -0.116 | $926 |
| A: wait up to 8 bars for a pullback fill (`a_pullback`) | $+5292 | +52.92% | $+317 | -11.45% | +50.19% | +1.82% | 21 | 42.9% | +1.231 | $338 |
| Y: same engine, decides at 4h closes only (`y_4h`) | $+5057 | +50.57% | $+83 | -9.95% | +52.69% | -1.39% | 17 | 29.4% | +1.464 | $274 |
| Y: same engine, decides at each market's daily close only (`y_1d`) | $+6403 | +64.03% | $+1428 | -9.63% | +56.57% | +4.76% | 11 | 45.5% | +2.342 | $171 |
| H5: damp slow daily voices when 1h/4h structure turns (`h5_damp`) | $+5892 | +58.92% | $+917 | -13.42% | +59.62% | -0.44% | 21 | 42.9% | +1.371 | $321 |
| M: 1h swing mind (EV filter, stop/target/1h clock) (`m_swing_1h`) | $+0 | +0.00% | $-4975 | 0.00% | +0.00% | +0.00% | 0 | - | - | $0 |
| M: 4h swing mind (EV filter, stop/target/4h clock) (`m_swing_4h`) | $+0 | +0.00% | $-4975 | 0.00% | +0.00% | +0.00% | 0 | - | - | $0 |
| Buy and hold (one round trip) (`buy_hold`) | $-215 | -2.15% | $-5190 | -6.67% | -4.96% | +2.96% | - | - | - | - |

Max drawdown: of the six books summed and marked every session. Halves split the window by sessions.

## fx: 2026-07-14 08:30 to 2026-11-11 08:30 UTC (halves split at 2026-09-11 01:30)

### USDJPY (buy and hold -2.15%, its max drawdown -6.67%)

| Book | Return | Max DD | Trades | Win rate | Avg R | Profit factor | Fees | 1st half | 2nd half | At end |
|---|---|---|---|---|---|---|---|---|---|---|
| `main` | +49.75% | -13.42% | 23 | 43.50% | +1.08 | 2.38 | $362 | +50.45% | -0.47% | SHORT |
| `v4` | +42.09% | -13.10% | 17 | 29.40% | +1.31 | 2.43 | $251 | +30.34% | +9.02% | SHORT |
| `h3_flip_limit` | +47.71% | -13.61% | 23 | 39.10% | +1.08 | 2.34 | $355 | +48.66% | -0.64% | SHORT |
| `b_targets` | -12.59% | -23.26% | 52 | 44.20% | -0.11 | 0.77 | $610 | -2.61% | -10.24% | SHORT |
| `b_trail` | -20.19% | -24.26% | 88 | 50.00% | -0.12 | 0.75 | $926 | -11.56% | -9.76% | SHORT |
| `a_pullback` | +52.92% | -11.45% | 21 | 42.90% | +1.23 | 2.60 | $338 | +50.24% | +1.79% | SHORT |
| `y_4h` | +50.57% | -9.95% | 17 | 29.40% | +1.46 | 2.62 | $274 | +52.73% | -1.42% | FLAT |
| `y_1d` | +64.03% | -9.63% | 11 | 45.50% | +2.34 | 4.57 | $171 | +56.62% | +4.73% | LONG |
| `h5_damp` | +58.92% | -13.42% | 21 | 42.90% | +1.37 | 2.64 | $321 | +59.66% | -0.47% | SHORT |
| `m_swing_1h` | +0.00% | +0.00% | 0 | - | - | - | $0 | +0.00% | +0.00% | FLAT |
| `m_swing_4h` | +0.00% | +0.00% | 0 | - | - | - | $0 | +0.00% | +0.00% | FLAT |

## The rules (engine15/shadows.py)

- `main`: Main rule (v5), fresh copy
- `v4`: v4: no higher-timeframe bias (H4)
- `h3_flip_limit`: H3: limit on flip exits
- `b_targets`: B: half at Target 1, rest at Target 2
- `b_trail`: B: trailing swing / 2 ATR stop after 1R
- `a_pullback`: A: wait up to 8 bars for a pullback fill
- `y_4h`: Y: same engine, decides at 4h closes only
- `y_1d`: Y: same engine, decides at each market's daily close only
- `h5_damp`: H5: damp slow daily voices when 1h/4h structure turns
- `m_swing_1h`: M: 1h swing mind (EV filter, stop/target/1h clock)
- `m_swing_4h`: M: 4h swing mind (EV filter, stop/target/4h clock)

Intrabar conventions: limits fill only when a bar trades strictly through them, at the limit; a stop live at a bar's start comes before any target or limit in that bar; Target 1 and 2 may fill in one bar, the break-even stop is live from the next bar. Trade counts are closed trades; a b_targets trade with a partial exit counts once.
