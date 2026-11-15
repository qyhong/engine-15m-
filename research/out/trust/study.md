# H42: a more balanced trust blend for the voices (IN-SAMPLE, development data only)

Written by `research/trust_study.py` on 2026-11-15 09:56 UTC. Rows before 2025-11-11 00:00 UTC only; halves split at 2022-12-06 00:00 UTC (first = selection, second = confirmation). Odds formed as the live step forms them (voices walked forward weekly from 2020-01-01, the group's voting cards, the silent-voice mask); only `trust_eta` and `trust_floor` change. Main book per market from $10,000 at the start of each half (flat), the asset's fee, leverage cap and fill delay as live; the live-only total-risk cap across books is not applied. 6 variants (1 baseline + 5 challengers). Paper only.

## Verdict

Chosen on the first half (registered rule: most groups with log-loss below base, ties by mean gap): **`f08`** ({"trust_eta": 0.2, "trust_floor": 0.08}).

Second-half pass bar: log-loss below base in >= 4 of 5 groups: **yes** (5: crypto, metals, fx, index, energy); pooled 8-market book Sharpe not lower than base: **no** (0.95 vs 1.06); pooled max drawdown no worse by more than 2 points: **yes** (-17.21% vs -16.86%).

**NO PASS.**

## Plain-English conclusions (written after the results)

- **Prediction: every balanced variant is a little better, and only a little.** In the second half all 5 challengers have lower log-loss than the live setting in all 5 groups (first half: 4 of 5; fx was the exception for every challenger). The gains are tiny: 0.00004 to 0.0011 nats, i.e. 0.005% to 0.15% of the log-loss. Direction hit rate on all up/down calls stays within about half a point of 50% everywhere (crypto 51.3-51.7% for every variant). Spreading the say is a mild smoothing, not a new skill.
- **Calls with a 5-point edge:** a flatter blend makes far fewer of them (crypto second half 30,701 -> 18,289 for `f08`) and those it makes are right a bit more often in crypto (51.3% -> 53.6%; `e05` 55.3% on 16,646). In metals and the S&P the counts fall to a few dozen or one, so those hit rates mean nothing.
- **Trading: no improvement.** The main book barely depends on the blend: gold, silver and the S&P trade identically under all 6 variants, and USDJPY identically under all 5 challengers, because most of their positions come from the higher-timeframe bias, forced entries and long holds, not from the size of the edge. Where the book does move (crypto, oil) it moves a lot and in no steady direction: ETH's second half is +124% under the live setting and -6% to -17% under every challenger, while BTC is better under every challenger. Pooled over 8 markets in the second half the chosen `f08` has Sharpe 0.95 vs 1.06, so it fails the bar; `e10` is the only challenger slightly above the live setting (1.10), and it was not chosen. First half the order was different again (`e05`/`e10f05` best). The book differences look like path noise from a few large holds.
- **How concentrated trust has been in history (live setting):** crypto's voting trust had one voice above 50% for 17% (first half) and 19% (second half) of the time; mean effective number of voices 8.4 of 13. Energy 32% then 23% (mean 6.6-6.9 voices of 11), metals 21% then 4%, fx 7% then 0%, the S&P 0%. The live picture (levels ~79%, the rest at the floor) is more concentrated than the development history's average, and it falls after the development cut, so this study does not cover it.
- **Why the floor variants look 'flat':** the Hedge leader is picked among all 59 voices before the voting cards are picked out, and in most groups the lowest-loss voice is a NON-voting voice 45-72% of the time (e.g. `all` and `ichimoku` in crypto). Then the voters often all sit at the floor and the vote is equal-weighted ('No single leader' column). A floor of 0.08 makes this the usual state in the second half (50-94% of the time).
- **Bottom line:** no pass. A more balanced blend gives a consistent but very small log-loss gain and no trading gain on this history; nothing here argues for changing `trust_eta` or `trust_floor`.

## Selection table

| Variant | eta | floor | Groups below base, 1st half | Mean log-loss gap, 1st half | Groups below base, 2nd half |
|---|---|---|---|---|---|
| `f05` | 0.2 | 0.05 | 4/5 | -0.00034 | 5/5 |
| `f08` | 0.2 | 0.08 | 4/5 | -0.00043 | 5/5 |
| `e10` | 0.1 | 0.02 | 4/5 | -0.00022 | 5/5 |
| `e05` | 0.05 | 0.02 | 4/5 | -0.00034 | 5/5 |
| `e10f05` | 0.1 | 0.05 | 4/5 | -0.00039 | 5/5 |

## First half (selection)

### Odds and trust per group

| Group | Variant | Log-loss | vs base | Hit % (all up/down) | Hit % (edge >= 5) | Calls (edge >= 5) | ENV mean | ENV p10-p90 | Leader share | Time one voice > 50% | No single leader | Most often leading |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| crypto | `base` | 0.84096 | +0.00000 | 50.10 | 52.02 | 44817 | 8.43 | 2.45-13.00 | 0.29 | 16.9% | 13.1% | breadth 15%, cbprem 14% |
| crypto | `f05` | 0.84049 | -0.00047 | 50.29 | 52.25 | 37474 | 10.61 | 4.50-13.00 | 0.19 | 7.5% | 34.5% | breadth 13%, meanrev 11% |
| crypto | `f08` | 0.84029 | -0.00067 | 50.47 | 52.58 | 33774 | 11.47 | 6.55-13.00 | 0.15 | 2.6% | 49.8% | breadth 11%, levels 10% |
| crypto | `e10` | 0.84071 | -0.00025 | 50.30 | 52.11 | 38272 | 10.32 | 5.64-12.92 | 0.20 | 4.5% | 2.9% | breadth 16%, meanrev 16% |
| crypto | `e05` | 0.84029 | -0.00067 | 50.49 | 53.51 | 31349 | 12.03 | 10.37-12.98 | 0.13 | 1.0% | 1.4% | breadth 17%, meanrev 16% |
| crypto | `e10f05` | 0.84031 | -0.00065 | 50.56 | 53.02 | 30579 | 12.13 | 10.04-13.00 | 0.12 | 1.9% | 51.8% | breadth 12%, levels 10% |
| metals | `base` | 0.80736 | +0.00000 | 49.35 | 48.80 | 16039 | 8.51 | 2.19-13.93 | 0.31 | 21.2% | 7.7% | regime 18%, ichimoku 16% |
| metals | `f05` | 0.80720 | -0.00016 | 49.02 | 45.97 | 9628 | 10.99 | 4.23-14.00 | 0.20 | 7.9% | 30.7% | regime 15%, ichimoku 13% |
| metals | `f08` | 0.80711 | -0.00025 | 49.10 | 43.87 | 7002 | 12.05 | 6.38-14.00 | 0.15 | 0.0% | 43.8% | regime 12%, ichimoku 12% |
| metals | `e10` | 0.80726 | -0.00010 | 49.14 | 45.62 | 8451 | 11.13 | 5.97-13.93 | 0.19 | 4.3% | 3.7% | regime 18%, ichimoku 16% |
| metals | `e05` | 0.80720 | -0.00016 | 48.70 | 44.99 | 4263 | 13.14 | 11.69-13.99 | 0.12 | 0.4% | 5.3% | regime 18%, ichimoku 16% |
| metals | `e10f05` | 0.80715 | -0.00021 | 48.70 | 44.41 | 4808 | 13.14 | 11.13-14.00 | 0.11 | 0.9% | 50.8% | ichimoku 11%, regime 11% |
| fx | `base` | 0.79087 | +0.00000 | 50.65 | 55.08 | 6632 | 9.69 | 4.59-12.90 | 0.23 | 7.4% | 2.5% | strategies 14%, meanrev 13% |
| fx | `f05` | 0.79097 | +0.00010 | 50.29 | 56.05 | 4583 | 11.81 | 8.92-13.00 | 0.14 | 4.8% | 38.8% | strategies 10%, meanrev 9% |
| fx | `f08` | 0.79107 | +0.00020 | 50.21 | 56.44 | 3949 | 12.30 | 11.33-13.00 | 0.11 | 2.8% | 63.4% | strategies 9%, regime 5% |
| fx | `e10` | 0.79097 | +0.00010 | 50.18 | 56.61 | 4506 | 11.75 | 10.20-12.98 | 0.15 | 3.8% | 2.8% | strategies 14%, meanrev 13% |
| fx | `e05` | 0.79133 | +0.00046 | 49.96 | 52.36 | 3134 | 12.61 | 12.54-13.00 | 0.11 | 0.0% | 9.8% | strategies 13%, meanrev 13% |
| fx | `e10f05` | 0.79116 | +0.00029 | 50.07 | 54.66 | 3520 | 12.61 | 12.89-13.00 | 0.10 | 1.3% | 79.8% | strategies 8%, trendq 3% |
| index | `base` | 1.07717 | +0.00000 | 48.25 | 47.84 | 255 | 11.29 | 9.92-12.00 | 0.13 | 0.0% | 12.6% | regime 23%, rates 14% |
| index | `f05` | 1.07648 | -0.00069 | 48.29 | 54.27 | 234 | 11.98 | 11.96-12.00 | 0.09 | 0.0% | 79.6% | levels 7%, rates 6% |
| index | `f08` | 1.07638 | -0.00079 | 48.40 | 53.33 | 240 | 12.00 | 12.00-12.00 | 0.08 | 0.0% | 98.0% | levels 1%, macro 1% |
| index | `e10` | 1.07668 | -0.00049 | 48.26 | 52.61 | 230 | 11.88 | 11.62-12.00 | 0.10 | 0.0% | 20.9% | regime 20%, rates 14% |
| index | `e05` | 1.07646 | -0.00071 | 48.29 | 54.74 | 232 | 11.99 | 11.96-12.00 | 0.09 | 0.0% | 44.2% | regime 14%, rates 13% |
| index | `e10f05` | 1.07637 | -0.00080 | 48.41 | 52.89 | 242 | 12.00 | 12.00-12.00 | 0.08 | 0.0% | 100.0% | - |
| energy | `base` | 0.75830 | +0.00000 | 51.83 | 53.12 | 40841 | 6.58 | 1.56-11.00 | 0.37 | 32.0% | 12.0% | levels 24%, regime 16% |
| energy | `f05` | 0.75784 | -0.00046 | 51.78 | 52.95 | 34664 | 8.23 | 2.49-11.00 | 0.26 | 18.4% | 34.7% | levels 21%, regime 14% |
| energy | `f08` | 0.75766 | -0.00064 | 51.82 | 52.70 | 31422 | 9.00 | 3.54-11.00 | 0.21 | 10.5% | 47.3% | levels 20%, regime 11% |
| energy | `e10` | 0.75794 | -0.00036 | 51.98 | 52.84 | 37834 | 7.85 | 2.57-10.91 | 0.29 | 16.4% | 2.8% | levels 27%, regime 17% |
| energy | `e05` | 0.75770 | -0.00060 | 51.91 | 51.94 | 31253 | 9.37 | 5.59-10.97 | 0.19 | 3.6% | 1.1% | levels 27%, regime 17% |
| energy | `e10f05` | 0.75773 | -0.00057 | 51.89 | 52.19 | 30057 | 9.46 | 4.82-11.00 | 0.18 | 6.1% | 46.3% | levels 24%, regime 10% |

### Main book per group (markets pooled) and all 8 markets

| Group | Variant | Return | Sharpe | Max DD | Trades | Per market (return / Sharpe / DD / trades) |
|---|---|---|---|---|---|---|
| crypto | `base` | +275.36% | 0.99 | -51.78% | 282 | BTCUSDT -69.2% / -0.28 / -83.1% / 164; ETHUSDT +619.9% / 1.25 / -55.3% / 118 |
| crypto | `f05` | +222.74% | 0.94 | -48.72% | 198 | BTCUSDT +51.5% / 0.55 / -73.6% / 94; ETHUSDT +394.0% / 1.09 / -54.5% / 104 |
| crypto | `f08` | +325.64% | 1.09 | -44.64% | 181 | BTCUSDT +54.1% / 0.55 / -72.3% / 89; ETHUSDT +597.2% / 1.25 / -52.0% / 92 |
| crypto | `e10` | +335.94% | 1.09 | -44.45% | 209 | BTCUSDT +54.7% / 0.56 / -77.3% / 104; ETHUSDT +617.2% / 1.26 / -52.1% / 105 |
| crypto | `e05` | +404.81% | 1.20 | -38.27% | 178 | BTCUSDT +83.4% / 0.65 / -74.0% / 89; ETHUSDT +726.2% / 1.35 / -49.4% / 89 |
| crypto | `e10f05` | +402.58% | 1.19 | -42.70% | 163 | BTCUSDT +84.4% / 0.66 / -74.0% / 82; ETHUSDT +720.7% / 1.34 / -46.4% / 81 |
| metals | `base` | -9.12% | 0.05 | -64.92% | 185 | XAUUSD -49.6% / -0.57 / -68.3% / 108; XAGUSD +31.3% / 0.45 / -64.8% / 77 |
| metals | `f05` | -3.45% | 0.11 | -58.18% | 152 | XAUUSD -46.7% / -0.56 / -61.3% / 87; XAGUSD +39.8% / 0.50 / -58.4% / 65 |
| metals | `f08` | -18.10% | -0.10 | -56.87% | 120 | XAUUSD -41.2% / -0.47 / -56.9% / 69; XAGUSD +5.0% / 0.24 / -59.2% / 51 |
| metals | `e10` | +0.81% | 0.16 | -56.57% | 138 | XAUUSD -48.6% / -0.62 / -62.9% / 86; XAGUSD +50.2% / 0.57 / -55.1% / 52 |
| metals | `e05` | -14.65% | -0.04 | -55.46% | 111 | XAUUSD -42.1% / -0.49 / -57.9% / 73; XAGUSD +12.8% / 0.30 / -56.2% / 38 |
| metals | `e10f05` | -15.29% | -0.05 | -55.46% | 111 | XAUUSD -43.4% / -0.51 / -57.9% / 73; XAGUSD +12.8% / 0.30 / -56.2% / 38 |
| fx | `base` | +306.41% | 1.50 | -29.93% | 48 | USDJPY +306.4% / 1.50 / -32.3% / 48 |
| fx | `f05` | +143.50% | 1.19 | -26.70% | 25 | USDJPY +143.5% / 1.19 / -28.9% / 25 |
| fx | `f08` | +143.70% | 1.19 | -26.70% | 17 | USDJPY +143.7% / 1.19 / -28.9% / 17 |
| fx | `e10` | +154.39% | 1.24 | -26.70% | 15 | USDJPY +154.4% / 1.24 / -28.9% / 15 |
| fx | `e05` | +133.30% | 1.13 | -26.70% | 19 | USDJPY +133.3% / 1.13 / -28.9% / 19 |
| fx | `e10f05` | +133.30% | 1.13 | -26.70% | 19 | USDJPY +133.3% / 1.13 / -28.9% / 19 |
| index | `base` | +2.03% | 0.15 | -19.05% | 15 | SPX +2.0% / 0.15 / -19.5% / 15 |
| index | `f05` | +0.17% | 0.11 | -19.47% | 15 | SPX +0.2% / 0.11 / -19.8% / 15 |
| index | `f08` | +0.17% | 0.11 | -19.47% | 15 | SPX +0.2% / 0.11 / -19.8% / 15 |
| index | `e10` | +2.03% | 0.15 | -19.05% | 15 | SPX +2.0% / 0.15 / -19.5% / 15 |
| index | `e05` | +2.03% | 0.15 | -19.05% | 15 | SPX +2.0% / 0.15 / -19.5% / 15 |
| index | `e10f05` | +0.17% | 0.11 | -19.47% | 15 | SPX +0.2% / 0.11 / -19.8% / 15 |
| energy | `base` | +273.57% | 1.17 | -38.73% | 157 | WTI +289.7% / 1.10 / -46.0% / 82; BRENT +257.5% / 1.14 / -48.2% / 75 |
| energy | `f05` | +289.93% | 1.20 | -42.64% | 131 | WTI +263.9% / 1.07 / -47.0% / 69; BRENT +316.0% / 1.25 / -51.2% / 62 |
| energy | `f08` | +359.93% | 1.29 | -41.61% | 128 | WTI +442.2% / 1.31 / -42.1% / 66; BRENT +277.7% / 1.17 / -51.3% / 62 |
| energy | `e10` | +255.68% | 1.12 | -39.28% | 148 | WTI +307.3% / 1.12 / -43.2% / 73; BRENT +204.1% / 1.03 / -50.1% / 75 |
| energy | `e05` | +367.53% | 1.32 | -43.97% | 120 | WTI +405.1% / 1.27 / -42.1% / 64; BRENT +329.9% / 1.27 / -53.7% / 56 |
| energy | `e10f05` | +388.49% | 1.34 | -41.97% | 124 | WTI +449.1% / 1.31 / -42.1% / 66; BRENT +327.8% / 1.26 / -51.3% / 58 |
| **all 8** | `base` | +173.50% | 1.26 | -27.97% | 687 | |
| **all 8** | `f05` | +145.26% | 1.20 | -20.79% | 521 | |
| **all 8** | `f08` | +184.85% | 1.32 | -27.05% | 461 | |
| **all 8** | `e10` | +167.66% | 1.27 | -25.23% | 525 | |
| **all 8** | `e05` | +206.34% | 1.43 | -24.51% | 443 | |
| **all 8** | `e10f05` | +210.63% | 1.42 | -28.19% | 432 | |

## Second half (confirmation)

### Odds and trust per group

| Group | Variant | Log-loss | vs base | Hit % (all up/down) | Hit % (edge >= 5) | Calls (edge >= 5) | ENV mean | ENV p10-p90 | Leader share | Time one voice > 50% | No single leader | Most often leading |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| crypto | `base` | 0.86688 | +0.00000 | 51.74 | 51.32 | 30701 | 8.43 | 2.36-13.00 | 0.29 | 19.4% | 10.9% | cbprem 24%, pullback 13% |
| crypto | `f05` | 0.86666 | -0.00022 | 51.62 | 52.68 | 21990 | 10.65 | 4.56-13.00 | 0.19 | 6.1% | 34.7% | cbprem 21%, pullback 9% |
| crypto | `f08` | 0.86660 | -0.00028 | 51.51 | 53.62 | 18289 | 11.53 | 6.75-13.00 | 0.15 | 0.2% | 50.0% | cbprem 18%, strategies 8% |
| crypto | `e10` | 0.86678 | -0.00010 | 51.53 | 52.24 | 22587 | 10.57 | 6.10-12.97 | 0.19 | 2.8% | 3.4% | cbprem 26%, pullback 14% |
| crypto | `e05` | 0.86663 | -0.00025 | 51.33 | 55.27 | 16646 | 12.27 | 10.97-13.00 | 0.12 | 0.0% | 3.6% | cbprem 27%, pullback 13% |
| crypto | `e10f05` | 0.86658 | -0.00030 | 51.42 | 54.99 | 15512 | 12.34 | 10.77-13.00 | 0.11 | 0.2% | 53.1% | cbprem 18%, levels 7% |
| metals | `base` | 0.79080 | +0.00000 | 50.35 | 44.05 | 1512 | 11.08 | 5.65-13.99 | 0.19 | 3.9% | 8.8% | goldetf 18%, macro 15% |
| metals | `f05` | 0.79074 | -0.00006 | 50.17 | 62.99 | 354 | 13.07 | 10.50-14.00 | 0.11 | 0.1% | 50.0% | goldetf 13%, macro 11% |
| metals | `f08` | 0.79073 | -0.00007 | 49.93 | 81.48 | 108 | 13.58 | 12.76-14.00 | 0.09 | 0.0% | 70.0% | goldetf 10%, macro 8% |
| metals | `e10` | 0.79076 | -0.00004 | 50.14 | 68.88 | 286 | 12.95 | 10.91-13.98 | 0.13 | 0.0% | 2.7% | goldetf 20%, macro 16% |
| metals | `e05` | 0.79072 | -0.00008 | 50.02 | 92.31 | 52 | 13.80 | 13.40-14.00 | 0.09 | 0.0% | 9.0% | goldetf 20%, macro 16% |
| metals | `e10f05` | 0.79072 | -0.00008 | 49.89 | 94.12 | 34 | 13.92 | 13.88-14.00 | 0.08 | 0.0% | 78.3% | goldetf 8%, macro 7% |
| fx | `base` | 0.80199 | +0.00000 | 49.74 | 42.22 | 1485 | 11.63 | 9.37-12.98 | 0.15 | 0.2% | 2.0% | clock 26%, meanrev 12% |
| fx | `f05` | 0.80170 | -0.00029 | 50.06 | 44.11 | 959 | 12.85 | 12.66-13.00 | 0.09 | 0.0% | 68.4% | clock 14%, trendq 5% |
| fx | `f08` | 0.80166 | -0.00033 | 50.11 | 45.70 | 895 | 12.97 | 13.00-13.00 | 0.08 | 0.0% | 89.3% | clock 7%, trendq 2% |
| fx | `e10` | 0.80171 | -0.00028 | 50.04 | 43.57 | 1026 | 12.68 | 12.13-13.00 | 0.11 | 0.0% | 6.2% | clock 27%, meanrev 12% |
| fx | `e05` | 0.80164 | -0.00035 | 50.13 | 45.16 | 919 | 12.95 | 12.88-13.00 | 0.09 | 0.0% | 26.8% | clock 25%, meanrev 10% |
| fx | `e10f05` | 0.80162 | -0.00037 | 50.11 | 45.86 | 881 | 13.00 | 13.00-13.00 | 0.08 | 0.0% | 95.8% | clock 4%, meanrev 0% |
| index | `base` | 1.07610 | +0.00000 | 50.28 | 29.41 | 17 | 11.01 | 9.40-11.97 | 0.15 | 0.0% | 3.2% | rates 31%, regime 16% |
| index | `f05` | 1.07598 | -0.00012 | 50.13 | 0.00 | 1 | 11.93 | 11.90-12.00 | 0.09 | 0.0% | 78.6% | rates 13%, fib 5% |
| index | `f08` | 1.07598 | -0.00012 | 50.19 | 0.00 | 1 | 11.99 | 12.00-12.00 | 0.09 | 0.0% | 93.8% | rates 5%, fib 1% |
| index | `e10` | 1.07601 | -0.00009 | 49.97 | 0.00 | 1 | 11.82 | 11.52-12.00 | 0.11 | 0.0% | 5.9% | rates 31%, regime 16% |
| index | `e05` | 1.07598 | -0.00012 | 50.03 | 0.00 | 1 | 11.98 | 11.94-12.00 | 0.09 | 0.0% | 32.0% | rates 27%, fib 16% |
| index | `e10f05` | 1.07597 | -0.00013 | 50.30 | 0.00 | 1 | 12.00 | 12.00-12.00 | 0.08 | 0.0% | 99.2% | rates 1% |
| energy | `base` | 0.73646 | +0.00000 | 49.40 | 47.81 | 18703 | 6.90 | 1.88-10.83 | 0.34 | 22.7% | 2.3% | kama 19%, regime 19% |
| energy | `f05` | 0.73582 | -0.00064 | 49.73 | 49.69 | 13405 | 8.78 | 3.30-11.00 | 0.22 | 11.7% | 31.6% | kama 17%, regime 16% |
| energy | `f08` | 0.73548 | -0.00098 | 49.93 | 49.66 | 12039 | 9.52 | 4.82-11.00 | 0.18 | 5.8% | 49.7% | kama 14%, regime 13% |
| energy | `e10` | 0.73605 | -0.00041 | 49.73 | 48.78 | 12878 | 8.96 | 4.92-10.96 | 0.22 | 6.5% | 1.1% | kama 19%, regime 19% |
| energy | `e05` | 0.73536 | -0.00110 | 49.92 | 45.54 | 7951 | 10.35 | 9.33-11.00 | 0.14 | 0.8% | 5.2% | kama 19%, regime 19% |
| energy | `e10f05` | 0.73552 | -0.00094 | 49.98 | 46.65 | 9199 | 10.32 | 8.88-11.00 | 0.14 | 2.6% | 59.0% | kama 12%, regime 11% |

### Main book per group (markets pooled) and all 8 markets

| Group | Variant | Return | Sharpe | Max DD | Trades | Per market (return / Sharpe / DD / trades) |
|---|---|---|---|---|---|---|
| crypto | `base` | +102.14% | 0.77 | -41.54% | 231 | BTCUSDT +80.2% / 0.67 / -45.5% / 128; ETHUSDT +124.1% / 0.77 / -49.3% / 103 |
| crypto | `f05` | +54.74% | 0.57 | -57.59% | 184 | BTCUSDT +115.2% / 0.81 / -60.8% / 89; ETHUSDT -5.7% / 0.23 / -72.6% / 95 |
| crypto | `f08` | +57.40% | 0.58 | -54.10% | 153 | BTCUSDT +129.4% / 0.85 / -51.5% / 73; ETHUSDT -14.6% / 0.17 / -73.0% / 80 |
| crypto | `e10` | +104.82% | 0.80 | -52.24% | 159 | BTCUSDT +226.6% / 1.12 / -49.5% / 67; ETHUSDT -16.9% / 0.15 / -72.9% / 92 |
| crypto | `e05` | +47.40% | 0.52 | -45.61% | 135 | BTCUSDT +110.7% / 0.79 / -48.6% / 63; ETHUSDT -15.9% / 0.17 / -71.9% / 72 |
| crypto | `e10f05` | +44.47% | 0.51 | -50.52% | 128 | BTCUSDT +102.0% / 0.75 / -50.5% / 60; ETHUSDT -13.1% / 0.18 / -76.0% / 68 |
| metals | `base` | +187.55% | 1.32 | -34.50% | 78 | XAUUSD +419.7% / 1.78 / -25.6% / 8; XAGUSD -44.6% / -0.43 / -71.0% / 70 |
| metals | `f05` | +187.55% | 1.32 | -34.50% | 78 | XAUUSD +419.7% / 1.78 / -25.6% / 8; XAGUSD -44.6% / -0.43 / -71.0% / 70 |
| metals | `f08` | +187.55% | 1.32 | -34.50% | 78 | XAUUSD +419.7% / 1.78 / -25.6% / 8; XAGUSD -44.6% / -0.43 / -71.0% / 70 |
| metals | `e10` | +187.55% | 1.32 | -34.50% | 78 | XAUUSD +419.7% / 1.78 / -25.6% / 8; XAGUSD -44.6% / -0.43 / -71.0% / 70 |
| metals | `e05` | +187.55% | 1.32 | -34.50% | 78 | XAUUSD +419.7% / 1.78 / -25.6% / 8; XAGUSD -44.6% / -0.43 / -71.0% / 70 |
| metals | `e10f05` | +187.55% | 1.32 | -34.50% | 78 | XAUUSD +419.7% / 1.78 / -25.6% / 8; XAGUSD -44.6% / -0.43 / -71.0% / 70 |
| fx | `base` | +13.60% | 0.30 | -35.60% | 48 | USDJPY +13.6% / 0.30 / -37.1% / 48 |
| fx | `f05` | +20.87% | 0.36 | -36.03% | 45 | USDJPY +20.9% / 0.36 / -37.5% / 45 |
| fx | `f08` | +20.87% | 0.36 | -36.03% | 45 | USDJPY +20.9% / 0.36 / -37.5% / 45 |
| fx | `e10` | +20.87% | 0.36 | -36.03% | 45 | USDJPY +20.9% / 0.36 / -37.5% / 45 |
| fx | `e05` | +20.87% | 0.36 | -36.03% | 45 | USDJPY +20.9% / 0.36 / -37.5% / 45 |
| fx | `e10f05` | +20.87% | 0.36 | -36.03% | 45 | USDJPY +20.9% / 0.36 / -37.5% / 45 |
| index | `base` | +59.56% | 0.89 | -18.69% | 17 | SPX +59.6% / 0.89 / -19.1% / 17 |
| index | `f05` | +59.56% | 0.89 | -18.69% | 17 | SPX +59.6% / 0.89 / -19.1% / 17 |
| index | `f08` | +59.56% | 0.89 | -18.69% | 17 | SPX +59.6% / 0.89 / -19.1% / 17 |
| index | `e10` | +59.56% | 0.89 | -18.69% | 17 | SPX +59.6% / 0.89 / -19.1% / 17 |
| index | `e05` | +59.56% | 0.89 | -18.69% | 17 | SPX +59.6% / 0.89 / -19.1% / 17 |
| index | `e10f05` | +59.56% | 0.89 | -18.69% | 17 | SPX +59.6% / 0.89 / -19.1% / 17 |
| energy | `base` | -51.49% | -0.57 | -58.64% | 145 | WTI -50.3% / -0.52 / -59.2% / 69; BRENT -52.6% / -0.57 / -62.5% / 76 |
| energy | `f05` | -43.58% | -0.41 | -51.99% | 116 | WTI -36.1% / -0.26 / -47.4% / 48; BRENT -51.1% / -0.53 / -59.2% / 68 |
| energy | `f08` | -46.39% | -0.43 | -54.37% | 112 | WTI -46.6% / -0.42 / -56.1% / 55; BRENT -46.1% / -0.41 / -55.0% / 57 |
| energy | `e10` | -42.70% | -0.39 | -51.23% | 111 | WTI -39.1% / -0.30 / -49.9% / 50; BRENT -46.3% / -0.44 / -55.2% / 61 |
| energy | `e05` | -54.66% | -0.65 | -61.41% | 113 | WTI -55.3% / -0.64 / -63.2% / 56; BRENT -54.0% / -0.61 / -61.6% / 57 |
| energy | `e10f05` | -52.63% | -0.60 | -59.68% | 112 | WTI -53.9% / -0.59 / -62.0% / 56; BRENT -51.4% / -0.55 / -59.4% / 56 |
| **all 8** | `base` | +68.69% | 1.06 | -16.86% | 519 | |
| **all 8** | `f05` | +59.73% | 0.97 | -18.99% | 440 | |
| **all 8** | `f08` | +59.70% | 0.95 | -17.21% | 405 | |
| **all 8** | `e10` | +72.47% | 1.10 | -16.94% | 410 | |
| **all 8** | `e05` | +55.13% | 0.91 | -15.39% | 388 | |
| **all 8** | `e10f05` | +54.90% | 0.89 | -17.05% | 380 | |

## Data notes

- crypto: 240306 rows to 2025-11-10 23:45 UTC; first odds {'BTCUSDT': '2020-02-05 00:00', 'ETHUSDT': '2020-02-05 00:00'}; split row 2022-12-06 00:00; voters trend, regime, levels, momentum, meanrev, pullback, flow, strategies, basis, stable, cbprem, breadth, owner; refits {'refits': 0, 'reused': 301}; baseline trust equals `leanprep.trust_tail` (max gap 0.0e+00).
- metals: 162215 rows to 2025-11-10 23:45 UTC; first odds {'XAUUSD': '2020-02-21 19:00', 'XAGUSD': '2020-02-21 19:00'}; split row 2022-12-06 00:00; voters trend, regime, momentum, meanrev, pullback, news, macro, structure, volx, goldetf, mavg, ichimoku, kama, owner; refits {'refits': 0, 'reused': 202}; baseline trust equals `leanprep.trust_tail` (max gap 0.0e+00).
- fx: 171130 rows to 2025-11-10 23:45 UTC; first odds {'USDJPY': '2020-04-08 21:00'}; split row 2022-12-06 00:00; voters trend, regime, levels, momentum, meanrev, pullback, strategies, clock, setups, trendq, rates, mavg, owner; refits {'refits': 0, 'reused': 208}; baseline trust equals `leanprep.trust_tail` (max gap 0.0e+00).
- index: 44687 rows to 2025-11-10 20:45 UTC; first odds {'SPX': '2021-01-12 17:30'}; split row 2022-12-06 14:30; voters regime, levels, news, macro, setups, intraday, trendq, fib, overnight, rates, mavg, owner; refits {'refits': 0, 'reused': 47}; baseline trust equals `leanprep.trust_tail` (max gap 0.0e+00).
- energy: 147360 rows to 2025-11-10 21:45 UTC; first odds {'WTI': '2020-02-27 19:00', 'BRENT': '2020-02-27 19:00'}; split row 2022-12-06 01:00; voters regime, levels, setups, trendq, candles, fib, mavg, kama, oilvol, oilspread, owner; refits {'refits': 0, 'reused': 183}; baseline trust equals `leanprep.trust_tail` (max gap 0.0e+00).

Which of ALL 59 voices has the lowest decayed loss (the Hedge leader before the voting cards are picked out; the same for every variant, since only eta and the floor change):

- crypto: first half: a voting card 36% of the time, most often ichimoku 12%, levels 8%, breadth 7%; second half: a voting card 37% of the time, most often all 15%, cbprem 14%, ichimoku 9%
- metals: first half: a voting card 50% of the time, most often regime 12%, ichimoku 11%, strategies 10%; second half: a voting card 28% of the time, most often clock 16%, all 14%, strategies 11%
- fx: first half: a voting card 54% of the time, most often strategies 11%, fib 9%, volx 9%; second half: a voting card 36% of the time, most often clock 15%, intraday 10%, volx 10%
- index: first half: a voting card 44% of the time, most often regime 14%, rates 13%, levels 9%; second half: a voting card 38% of the time, most often rates 22%, earnings 15%, all 14%
- energy: first half: a voting card 51% of the time, most often levels 12%, clock 12%, regime 11%; second half: a voting card 55% of the time, most often kama 14%, regime 14%, levels 10%

ENV = effective number of voices, 1 / sum(w^2) of the voting trust (before the per-asset silent-voice mask). Sharpe on daily marked equity, sqrt(365). Pooled curves sum the markets' daily equity.
