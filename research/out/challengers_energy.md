# Challenger books on recent history (IN-SAMPLE, not proof)

Written by `research/challengers.py` on 2026-11-11 08:59 UTC. Every book starts flat with $10,000 per asset at the window's start and trades the same odds the live step would have formed (voices walked forward from 240 days back; trained on the last 700 days of bars, not all history as live does). Fees as live. Paper only.

**Read this plainly:** one 120-day window that the rules' authors had already lived through; the H3 limit was chosen from a grid on this kind of history; six assets that move together. A history read can reject an idea, never prove one. Promotion is decided on forward results (docs/CHARTER.md).

## All six assets together ($60,000 start)

| Book | P&L | Return | vs main | Max drawdown | First half | Second half | Trades | Win rate | Avg R | Fees |
|---|---|---|---|---|---|---|---|---|---|---|
| Main rule (v5), fresh copy (`main`) | $-3400 | -17.00% | $+0 | -34.40% | -4.23% | -13.34% | 15 | 6.7% | -0.895 | $106 |
| v4: no higher-timeframe bias (H4) (`v4`) | $-2936 | -14.68% | $+465 | -34.40% | -1.52% | -13.36% | 13 | 0.0% | -0.968 | $93 |
| H3: limit on flip exits (`h3_flip_limit`) | $-3341 | -16.70% | $+60 | -34.36% | -3.69% | -13.51% | 15 | 6.7% | -0.889 | $106 |
| B: half at Target 1, rest at Target 2 (`b_targets`) | $-2124 | -10.62% | $+1277 | -27.34% | -3.54% | -7.34% | 70 | 42.9% | -0.037 | $506 |
| B: trailing swing / 2 ATR stop after 1R (`b_trail`) | $-2273 | -11.36% | $+1128 | -32.14% | -3.73% | -7.93% | 137 | 51.8% | +0.025 | $1019 |
| A: wait up to 8 bars for a pullback fill (`a_pullback`) | $-2074 | -10.37% | $+1326 | -29.32% | +3.53% | -13.42% | 12 | 8.3% | -0.849 | $87 |
| Y: same engine, decides at 4h closes only (`y_4h`) | $-2084 | -10.42% | $+1317 | -26.04% | +3.31% | -13.29% | 11 | 0.0% | -0.987 | $82 |
| Y: same engine, decides at each market's daily close only (`y_1d`) | $-3949 | -19.74% | $-548 | -28.29% | -5.15% | -15.39% | 16 | 6.2% | -0.945 | $117 |
| H5: damp slow daily voices when 1h/4h structure turns (`h5_damp`) | $-3400 | -17.00% | $+0 | -34.40% | -4.23% | -13.34% | 15 | 6.7% | -0.895 | $106 |
| M: 1h swing mind (EV filter, stop/target/1h clock) (`m_swing_1h`) | $+0 | +0.00% | $+3400 | 0.00% | +0.00% | +0.00% | 0 | - | - | $0 |
| M: 4h swing mind (EV filter, stop/target/4h clock) (`m_swing_4h`) | $+0 | +0.00% | $+3400 | 0.00% | +0.00% | +0.00% | 0 | - | - | $0 |
| Buy and hold (one round trip) (`buy_hold`) | $+1345 | +6.73% | $+4746 | -21.80% | +23.12% | -13.31% | - | - | - | - |

Max drawdown: of the six books summed and marked every session. Halves split the window by sessions.

## energy: 2026-07-14 08:15 to 2026-11-11 08:15 UTC (halves split at 2026-09-11 19:30)

### WTI (buy and hold +6.99%, its max drawdown -20.91%)

| Book | Return | Max DD | Trades | Win rate | Avg R | Profit factor | Fees | 1st half | 2nd half | At end |
|---|---|---|---|---|---|---|---|---|---|---|
| `main` | -14.91% | -31.86% | 7 | 14.30% | -0.78 | 0.02 | $50 | -0.78% | -14.23% | LONG |
| `v4` | -10.26% | -30.96% | 5 | 0.00% | -0.92 | 0.00 | $37 | +4.63% | -14.23% | LONG |
| `h3_flip_limit` | -14.68% | -31.68% | 7 | 14.30% | -0.77 | 0.03 | $50 | -0.52% | -14.23% | LONG |
| `b_targets` | -22.97% | -35.24% | 39 | 38.50% | -0.14 | 0.64 | $273 | -6.47% | -17.65% | SHORT |
| `b_trail` | -10.92% | -27.77% | 66 | 53.00% | +0.03 | 0.89 | $501 | +2.69% | -13.26% | SHORT |
| `a_pullback` | -0.39% | -20.91% | 4 | 25.00% | -0.53 | 0.08 | $31 | +16.15% | -14.23% | LONG |
| `y_4h` | -12.76% | -24.83% | 6 | 0.00% | -1.02 | 0.00 | $44 | +1.72% | -14.23% | LONG |
| `y_1d` | -20.30% | -29.26% | 9 | 11.10% | -0.88 | 0.04 | $66 | -0.33% | -20.04% | LONG |
| `h5_damp` | -14.91% | -31.86% | 7 | 14.30% | -0.78 | 0.02 | $50 | -0.78% | -14.23% | LONG |
| `m_swing_1h` | +0.00% | +0.00% | 0 | - | - | - | $0 | +0.00% | +0.00% | FLAT |
| `m_swing_4h` | +0.00% | +0.00% | 0 | - | - | - | $0 | +0.00% | +0.00% | FLAT |

### BRENT (buy and hold +6.46%, its max drawdown -23.24%)

| Book | Return | Max DD | Trades | Win rate | Avg R | Profit factor | Fees | 1st half | 2nd half | At end |
|---|---|---|---|---|---|---|---|---|---|---|
| `main` | -19.10% | -37.86% | 8 | 0.00% | -1.00 | 0.00 | $56 | -7.70% | -12.35% | LONG |
| `v4` | -19.10% | -37.86% | 8 | 0.00% | -1.00 | 0.00 | $56 | -7.70% | -12.35% | LONG |
| `h3_flip_limit` | -18.73% | -37.85% | 8 | 0.00% | -1.00 | 0.00 | $56 | -6.88% | -12.72% | LONG |
| `b_targets` | +1.74% | -28.03% | 31 | 48.40% | +0.09 | 0.91 | $234 | -0.63% | +2.38% | SHORT |
| `b_trail` | -11.80% | -38.09% | 71 | 50.70% | +0.02 | 0.90 | $518 | -10.18% | -1.81% | SHORT |
| `a_pullback` | -20.35% | -39.05% | 8 | 0.00% | -1.01 | 0.00 | $56 | -9.13% | -12.35% | LONG |
| `y_4h` | -8.08% | -27.17% | 5 | 0.00% | -0.94 | 0.00 | $38 | +4.87% | -12.35% | LONG |
| `y_1d` | -19.19% | -27.86% | 7 | 0.00% | -1.03 | 0.00 | $51 | -10.04% | -10.17% | SHORT |
| `h5_damp` | -19.10% | -37.86% | 8 | 0.00% | -1.00 | 0.00 | $56 | -7.70% | -12.35% | LONG |
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
