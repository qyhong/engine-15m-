# Challenger books on recent history (IN-SAMPLE, not proof)

Written by `research/challengers.py` on 2026-11-11 08:53 UTC. Every book starts flat with $10,000 per asset at the window's start and trades the same odds the live step would have formed (voices walked forward from 240 days back; trained on the last 700 days of bars, not all history as live does). Fees as live. Paper only.

**Read this plainly:** one 120-day window that the rules' authors had already lived through; the H3 limit was chosen from a grid on this kind of history; six assets that move together. A history read can reject an idea, never prove one. Promotion is decided on forward results (docs/CHARTER.md).

## All six assets together ($60,000 start)

| Book | P&L | Return | vs main | Max drawdown | First half | Second half | Trades | Win rate | Avg R | Fees |
|---|---|---|---|---|---|---|---|---|---|---|
| Main rule (v5), fresh copy (`main`) | $+3031 | +15.15% | $+0 | -15.22% | +13.85% | +1.14% | 15 | 13.3% | +0.093 | $295 |
| v4: no higher-timeframe bias (H4) (`v4`) | $+2534 | +12.67% | $-497 | -15.22% | +13.85% | -1.04% | 14 | 7.1% | -0.245 | $277 |
| H3: limit on flip exits (`h3_flip_limit`) | $+3086 | +15.43% | $+55 | -14.92% | +13.85% | +1.39% | 15 | 13.3% | +0.093 | $290 |
| B: half at Target 1, rest at Target 2 (`b_targets`) | $+2563 | +12.81% | $-468 | -13.87% | -2.84% | +16.11% | 84 | 46.5% | +0.022 | $1596 |
| B: trailing swing / 2 ATR stop after 1R (`b_trail`) | $-2541 | -12.70% | $-5572 | -22.24% | -6.20% | -6.94% | 189 | 49.2% | -0.085 | $3430 |
| A: wait up to 8 bars for a pullback fill (`a_pullback`) | $+3271 | +16.36% | $+241 | -15.12% | +14.97% | +1.20% | 14 | 14.3% | +0.185 | $279 |
| Y: same engine, decides at 4h closes only (`y_4h`) | $+2003 | +10.01% | $-1028 | -20.20% | +16.73% | -5.75% | 17 | 11.8% | +0.911 | $326 |
| Y: same engine, decides at daily closes only (`y_1d`) | $+269 | +1.34% | $-2762 | -18.30% | +5.19% | -3.66% | 12 | 8.3% | -0.682 | $233 |
| H5: damp slow daily voices when 1h/4h structure turns (`h5_damp`) | $+3031 | +15.15% | $+0 | -15.22% | +13.85% | +1.14% | 15 | 13.3% | +0.093 | $295 |
| M: 1h swing mind (EV filter, stop/target/1h clock) (`m_swing_1h`) | $+0 | +0.00% | $-3031 | 0.00% | +0.00% | +0.00% | 0 | - | - | $0 |
| M: 4h swing mind (EV filter, stop/target/4h clock) (`m_swing_4h`) | $+0 | +0.00% | $-3031 | 0.00% | +0.00% | +0.00% | 0 | - | - | $0 |
| Buy and hold (one round trip) (`buy_hold`) | $+3263 | +16.31% | $+232 | -22.65% | +32.34% | -12.11% | - | - | - | - |

Max drawdown: of the six books summed and marked every session. Halves split the window by sessions.

## crypto: 2026-07-14 08:30 to 2026-11-11 08:30 UTC (halves split at 2026-09-12 08:30)

### BTCUSDT (buy and hold +17.53%, its max drawdown -16.50%)

| Book | Return | Max DD | Trades | Win rate | Avg R | Profit factor | Fees | 1st half | 2nd half | At end |
|---|---|---|---|---|---|---|---|---|---|---|
| `main` | -3.18% | -15.36% | 10 | 10.00% | -0.54 | 0.61 | $186 | -3.78% | +0.63% | SHORT |
| `v4` | -8.15% | -16.50% | 9 | 0.00% | -1.14 | 0.00 | $168 | -3.78% | -4.54% | LONG |
| `h3_flip_limit` | -3.51% | -15.36% | 10 | 10.00% | -0.55 | 0.60 | $186 | -3.78% | +0.29% | SHORT |
| `b_targets` | +2.51% | -13.98% | 52 | 46.20% | -0.06 | 1.01 | $979 | -3.93% | +6.71% | SHORT |
| `b_trail` | -16.28% | -23.05% | 92 | 46.70% | -0.17 | 0.78 | $1598 | -11.70% | -5.19% | SHORT |
| `a_pullback` | -1.22% | -13.66% | 9 | 11.10% | -0.48 | 0.70 | $169 | -1.84% | +0.63% | SHORT |
| `y_4h` | -0.07% | -18.33% | 13 | 7.70% | +0.62 | 0.84 | $237 | -0.70% | +0.64% | SHORT |
| `y_1d` | +3.83% | -13.66% | 7 | 14.30% | -0.52 | 1.14 | $136 | +3.18% | +0.63% | SHORT |
| `h5_damp` | -3.18% | -15.36% | 10 | 10.00% | -0.54 | 0.61 | $186 | -3.78% | +0.63% | SHORT |
| `m_swing_1h` | +0.00% | +0.00% | 0 | - | - | - | $0 | +0.00% | +0.00% | FLAT |
| `m_swing_4h` | +0.00% | +0.00% | 0 | - | - | - | $0 | +0.00% | +0.00% | FLAT |

### ETHUSDT (buy and hold +15.10%, its max drawdown -28.24%)

| Book | Return | Max DD | Trades | Win rate | Avg R | Profit factor | Fees | 1st half | 2nd half | At end |
|---|---|---|---|---|---|---|---|---|---|---|
| `main` | +33.48% | -20.73% | 5 | 20.00% | +1.36 | 2.52 | $109 | +31.24% | +1.71% | SHORT |
| `v4` | +33.48% | -20.73% | 5 | 20.00% | +1.36 | 2.52 | $109 | +31.24% | +1.71% | SHORT |
| `h3_flip_limit` | +34.36% | -20.21% | 5 | 20.00% | +1.37 | 2.70 | $104 | +31.24% | +2.38% | SHORT |
| `b_targets` | +23.12% | -15.83% | 32 | 46.90% | +0.15 | 1.54 | $617 | -1.83% | +25.40% | SHORT |
| `b_trail` | -9.13% | -25.43% | 97 | 51.50% | -0.01 | 0.93 | $1832 | -0.90% | -8.30% | SHORT |
| `a_pullback` | +33.94% | -20.65% | 5 | 20.00% | +1.38 | 2.58 | $109 | +31.53% | +1.83% | SHORT |
| `y_4h` | +20.10% | -25.49% | 4 | 25.00% | +1.84 | 2.10 | $88 | +33.90% | -10.31% | SHORT |
| `y_1d` | -1.14% | -23.23% | 5 | 0.00% | -0.91 | 0.00 | $97 | +6.99% | -7.60% | SHORT |
| `h5_damp` | +33.48% | -20.73% | 5 | 20.00% | +1.36 | 2.52 | $109 | +31.24% | +1.71% | SHORT |
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
- `y_1d`: Y: same engine, decides at daily closes only
- `h5_damp`: H5: damp slow daily voices when 1h/4h structure turns
- `m_swing_1h`: M: 1h swing mind (EV filter, stop/target/1h clock)
- `m_swing_4h`: M: 4h swing mind (EV filter, stop/target/4h clock)

Intrabar conventions: limits fill only when a bar trades strictly through them, at the limit; a stop live at a bar's start comes before any target or limit in that bar; Target 1 and 2 may fill in one bar, the break-even stop is live from the next bar. Trade counts are closed trades; a b_targets trade with a partial exit counts once.
