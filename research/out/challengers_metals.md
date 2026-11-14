# Challenger books on recent history (IN-SAMPLE, not proof)

Written by `research/challengers.py` on 2026-11-11 08:59 UTC. Every book starts flat with $10,000 per asset at the window's start and trades the same odds the live step would have formed (voices walked forward from 240 days back; trained on the last 700 days of bars, not all history as live does). Fees as live. Paper only.

**Read this plainly:** one 120-day window that the rules' authors had already lived through; the H3 limit was chosen from a grid on this kind of history; six assets that move together. A history read can reject an idea, never prove one. Promotion is decided on forward results (docs/CHARTER.md).

## All six assets together ($60,000 start)

| Book | P&L | Return | vs main | Max drawdown | First half | Second half | Trades | Win rate | Avg R | Fees |
|---|---|---|---|---|---|---|---|---|---|---|
| Main rule (v5), fresh copy (`main`) | $+1101 | +5.51% | $+0 | -15.15% | -2.15% | +7.83% | 13 | 15.4% | -0.589 | $78 |
| v4: no higher-timeframe bias (H4) (`v4`) | $+912 | +4.56% | $-189 | -13.61% | -1.57% | +6.23% | 10 | 10.0% | -0.766 | $62 |
| H3: limit on flip exits (`h3_flip_limit`) | $+1134 | +5.67% | $+32 | -15.02% | -2.08% | +7.91% | 13 | 15.4% | -0.585 | $78 |
| B: half at Target 1, rest at Target 2 (`b_targets`) | $+810 | +4.05% | $-291 | -15.16% | -5.19% | +9.75% | 74 | 43.2% | +0.071 | $435 |
| B: trailing swing / 2 ATR stop after 1R (`b_trail`) | $-611 | -3.06% | $-1713 | -18.75% | -7.25% | +4.53% | 152 | 50.7% | +0.014 | $925 |
| A: wait up to 8 bars for a pullback fill (`a_pullback`) | $+991 | +4.96% | $-110 | -16.05% | -1.92% | +7.01% | 13 | 15.4% | -0.533 | $79 |
| Y: same engine, decides at 4h closes only (`y_4h`) | $+558 | +2.79% | $-543 | -14.81% | -6.13% | +9.50% | 12 | 8.3% | -0.822 | $70 |
| Y: same engine, decides at each market's daily close only (`y_1d`) | $-1325 | -6.62% | $-2426 | -23.32% | -16.07% | +11.26% | 19 | 0.0% | -1.030 | $108 |
| H5: damp slow daily voices when 1h/4h structure turns (`h5_damp`) | $+1101 | +5.51% | $+0 | -15.15% | -2.15% | +7.83% | 13 | 15.4% | -0.589 | $78 |
| M: 1h swing mind (EV filter, stop/target/1h clock) (`m_swing_1h`) | $+0 | +0.00% | $-1101 | 0.00% | +0.00% | +0.00% | 0 | - | - | $0 |
| M: 4h swing mind (EV filter, stop/target/4h clock) (`m_swing_4h`) | $+0 | +0.00% | $-1101 | 0.00% | +0.00% | +0.00% | 0 | - | - | $0 |
| Buy and hold (one round trip) (`buy_hold`) | $-947 | -4.74% | $-2049 | -24.29% | +8.85% | -12.48% | - | - | - | - |

Max drawdown: of the six books summed and marked every session. Halves split the window by sessions.

## metals: 2026-07-14 08:30 to 2026-11-11 08:30 UTC (halves split at 2026-09-13 23:30)

### XAUUSD (buy and hold +0.01%, its max drawdown -18.24%)

| Book | Return | Max DD | Trades | Win rate | Avg R | Profit factor | Fees | 1st half | 2nd half | At end |
|---|---|---|---|---|---|---|---|---|---|---|
| `main` | +5.80% | -13.54% | 5 | 20.00% | -0.40 | 0.49 | $31 | -2.43% | +8.44% | SHORT |
| `v4` | +3.80% | -18.68% | 7 | 14.30% | -0.66 | 0.25 | $44 | -1.23% | +5.10% | SHORT |
| `h3_flip_limit` | +5.96% | -13.41% | 5 | 20.00% | -0.40 | 0.50 | $31 | -2.29% | +8.44% | SHORT |
| `b_targets` | +9.71% | -14.94% | 29 | 41.40% | +0.14 | 1.20 | $177 | -0.51% | +10.28% | SHORT |
| `b_trail` | +2.31% | -14.87% | 74 | 51.40% | +0.04 | 1.05 | $470 | -5.25% | +7.97% | SHORT |
| `a_pullback` | +6.17% | -14.80% | 5 | 20.00% | -0.26 | 0.66 | $32 | -2.02% | +8.35% | SHORT |
| `y_4h` | +3.37% | -14.78% | 4 | 25.00% | -0.66 | 0.15 | $25 | -5.18% | +9.03% | SHORT |
| `y_1d` | -9.84% | -22.21% | 10 | 0.00% | -1.03 | 0.00 | $58 | -17.12% | +8.78% | SHORT |
| `h5_damp` | +5.80% | -13.54% | 5 | 20.00% | -0.40 | 0.49 | $31 | -2.43% | +8.44% | SHORT |
| `m_swing_1h` | +0.00% | +0.00% | 0 | - | - | - | $0 | +0.00% | +0.00% | FLAT |
| `m_swing_4h` | +0.00% | +0.00% | 0 | - | - | - | $0 | +0.00% | +0.00% | FLAT |

### XAGUSD (buy and hold -9.48%, its max drawdown -31.82%)

| Book | Return | Max DD | Trades | Win rate | Avg R | Profit factor | Fees | 1st half | 2nd half | At end |
|---|---|---|---|---|---|---|---|---|---|---|
| `main` | +5.22% | -20.48% | 8 | 12.50% | -0.71 | 0.19 | $47 | -1.69% | +7.03% | SHORT |
| `v4` | +5.32% | -16.15% | 3 | 0.00% | -1.03 | 0.00 | $18 | -1.69% | +7.13% | SHORT |
| `h3_flip_limit` | +5.38% | -20.36% | 8 | 12.50% | -0.70 | 0.20 | $47 | -1.69% | +7.20% | SHORT |
| `b_targets` | -1.61% | -20.51% | 45 | 44.40% | +0.02 | 0.94 | $258 | -10.06% | +9.39% | SHORT |
| `b_trail` | -8.42% | -26.64% | 78 | 50.00% | -0.01 | 0.92 | $456 | -9.44% | +1.13% | SHORT |
| `a_pullback` | +3.75% | -20.83% | 8 | 12.50% | -0.71 | 0.19 | $47 | -1.65% | +5.49% | SHORT |
| `y_4h` | +2.21% | -21.47% | 8 | 0.00% | -0.91 | 0.00 | $46 | -6.90% | +9.78% | SHORT |
| `y_1d` | -3.40% | -24.59% | 9 | 0.00% | -1.03 | 0.00 | $50 | -15.03% | +13.68% | SHORT |
| `h5_damp` | +5.22% | -20.48% | 8 | 12.50% | -0.71 | 0.19 | $47 | -1.69% | +7.03% | SHORT |
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
