# Challenger books on recent history (IN-SAMPLE, not proof)

Written by `research/challengers.py` on 2026-11-11 08:59 UTC. Every book starts flat with $10,000 per asset at the window's start and trades the same odds the live step would have formed (voices walked forward from 240 days back; trained on the last 700 days of bars, not all history as live does). Fees as live. Paper only.

**Read this plainly:** one 120-day window that the rules' authors had already lived through; the H3 limit was chosen from a grid on this kind of history; six assets that move together. A history read can reject an idea, never prove one. Promotion is decided on forward results (docs/CHARTER.md).

## All six assets together ($60,000 start)

| Book | P&L | Return | vs main | Max drawdown | First half | Second half | Trades | Win rate | Avg R | Fees |
|---|---|---|---|---|---|---|---|---|---|---|
| Main rule (v5), fresh copy (`main`) | $+408 | +4.08% | $+0 | -4.72% | +0.00% | +4.08% | 0 | - | - | $0 |
| v4: no higher-timeframe bias (H4) (`v4`) | $+408 | +4.08% | $+0 | -4.72% | +0.00% | +4.08% | 0 | - | - | $0 |
| H3: limit on flip exits (`h3_flip_limit`) | $+408 | +4.08% | $+0 | -4.72% | +0.00% | +4.08% | 0 | - | - | $0 |
| B: half at Target 1, rest at Target 2 (`b_targets`) | $+484 | +4.84% | $+76 | -2.73% | +0.00% | +4.84% | 3 | 66.7% | +0.739 | $17 |
| B: trailing swing / 2 ATR stop after 1R (`b_trail`) | $+614 | +6.14% | $+206 | -3.25% | +0.00% | +6.14% | 4 | 75.0% | +0.938 | $26 |
| A: wait up to 8 bars for a pullback fill (`a_pullback`) | $+408 | +4.08% | $+1 | -4.72% | +0.00% | +4.08% | 0 | - | - | $0 |
| Y: same engine, decides at 4h closes only (`y_4h`) | $-670 | -6.70% | $-1078 | -7.64% | +0.00% | -6.70% | 2 | 0.0% | -1.374 | $16 |
| Y: same engine, decides at each market's daily close only (`y_1d`) | $-207 | -2.07% | $-614 | -4.15% | +0.00% | -2.07% | 1 | 0.0% | -1.033 | $7 |
| H5: damp slow daily voices when 1h/4h structure turns (`h5_damp`) | $+408 | +4.08% | $+0 | -4.72% | +0.00% | +4.08% | 0 | - | - | $0 |
| M: 1h swing mind (EV filter, stop/target/1h clock) (`m_swing_1h`) | $+0 | +0.00% | $-408 | 0.00% | +0.00% | +0.00% | 0 | - | - | $0 |
| M: 4h swing mind (EV filter, stop/target/4h clock) (`m_swing_4h`) | $+0 | +0.00% | $-408 | 0.00% | +0.00% | +0.00% | 0 | - | - | $0 |
| Buy and hold (one round trip) (`buy_hold`) | $-22 | -0.22% | $-429 | -6.19% | +1.74% | -1.92% | - | - | - | - |

Max drawdown: of the six books summed and marked every session. Halves split the window by sessions.

## index: 2026-07-14 13:30 to 2026-11-10 20:45 UTC (halves split at 2026-09-11 16:45)

### SPX (buy and hold -0.22%, its max drawdown -6.19%)

| Book | Return | Max DD | Trades | Win rate | Avg R | Profit factor | Fees | 1st half | 2nd half | At end |
|---|---|---|---|---|---|---|---|---|---|---|
| `main` | +4.08% | -4.72% | 0 | - | - | - | $0 | +0.00% | +4.08% | SHORT |
| `v4` | +4.08% | -4.72% | 0 | - | - | - | $0 | +0.00% | +4.08% | SHORT |
| `h3_flip_limit` | +4.08% | -4.72% | 0 | - | - | - | $0 | +0.00% | +4.08% | SHORT |
| `b_targets` | +4.84% | -2.73% | 3 | 66.70% | +0.74 | 2.88 | $17 | +0.00% | +4.84% | SHORT |
| `b_trail` | +6.14% | -3.25% | 4 | 75.00% | +0.94 | 4.51 | $26 | +0.00% | +6.14% | SHORT |
| `a_pullback` | +4.08% | -4.72% | 0 | - | - | - | $0 | +0.00% | +4.08% | SHORT |
| `y_4h` | -6.70% | -7.64% | 2 | 0.00% | -1.37 | 0.00 | $16 | +0.00% | -6.70% | SHORT |
| `y_1d` | -2.07% | -4.15% | 1 | 0.00% | -1.03 | 0.00 | $7 | +0.00% | -2.07% | FLAT |
| `h5_damp` | +4.08% | -4.72% | 0 | - | - | - | $0 | +0.00% | +4.08% | SHORT |
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
