# Release follow-through, 2019 onward (informational)

Built 2026-11-11 06:57 UTC by `research/release_history.py` from `data/sources/calendar_history.csv` (engine15/calhistory.py) and the 15m Binance bars on file.

**This grades nothing.** H1 (CPI) and H16 (release days beyond CPI) keep their forward-only verdict rules in `research/HYPOTHESES.md`; history is warm-up and post-mortem material, not validation. Many ways of slicing these numbers exist; treat any one cell as a description, not an edge.

Measure (same as `research/event_study.py`): the release bar is the 15m bar opening at the release time. Follow-through = the move from the release bar's close to the close 1h (4 bars) / 4h (16 bars) later, signed by the release bar's direction. *Continued* = share of releases where that is positive. *p* = two-sided exact sign test against 50%. No costs.

Releases 2019-01-03 to 2026-11-10; halves split at 2022-12-07. CPI/NFP/FOMC as listed; OTHER = PPI, retail sales, advance GDP, PCE, ISM manufacturing (release times shared with CPI/NFP count once, under the first kind listed at that time).

## By half

| kind | coin | half | n | mean abs release bar | continued 1h | mean 1h | p 1h | continued 4h | mean 4h | p 4h |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CPI | BTC | 1st | 47 | 0.98% | 49% | -0.00% | 1.00 | 40% | -0.40% | 0.24 |
| CPI | BTC | 2nd | 47 | 0.68% | 43% | -0.03% | 0.38 | 55% | +0.05% | 0.56 |
| CPI | ETH | 1st | 46 | 1.21% | 41% | +0.06% | 0.30 | 43% | -0.21% | 0.46 |
| CPI | ETH | 2nd | 47 | 0.96% | 49% | +0.14% | 1.00 | 57% | +0.38% | 0.38 |
| NFP | BTC | 1st | 48 | 0.52% | 44% | -0.17% | 0.47 | 42% | -0.29% | 0.31 |
| NFP | BTC | 2nd | 46 | 0.48% | 48% | -0.16% | 0.88 | 41% | -0.18% | 0.30 |
| NFP | ETH | 1st | 48 | 0.59% | 54% | -0.03% | 0.67 | 40% | -0.36% | 0.19 |
| NFP | ETH | 2nd | 46 | 0.57% | 41% | -0.32% | 0.30 | 46% | -0.13% | 0.66 |
| FOMC | BTC | 1st | 32 | 1.04% | 53% | +0.07% | 0.86 | 50% | +0.02% | 1.00 |
| FOMC | BTC | 2nd | 32 | 0.45% | 50% | +0.35% | 1.00 | 72% | +0.89% | 0.02 |
| FOMC | ETH | 1st | 31 | 1.27% | 58% | -0.40% | 0.47 | 55% | -0.55% | 0.72 |
| FOMC | ETH | 2nd | 32 | 0.57% | 59% | +0.29% | 0.38 | 62% | +0.75% | 0.22 |
| OTHER | BTC | 1st | 198 | 0.31% | 47% | -0.07% | 0.52 | 45% | -0.17% | 0.23 |
| OTHER | BTC | 2nd | 185 | 0.30% | 49% | +0.03% | 0.88 | 49% | +0.00% | 0.88 |
| OTHER | ETH | 1st | 198 | 0.42% | 46% | -0.08% | 0.29 | 43% | -0.16% | 0.08 |
| OTHER | ETH | 2nd | 185 | 0.39% | 45% | -0.04% | 0.24 | 48% | -0.05% | 0.56 |

## Whole period

| kind | coin | half | n | mean abs release bar | continued 1h | mean 1h | p 1h | continued 4h | mean 4h | p 4h |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CPI | BTC | all | 94 | 0.83% | 46% | -0.01% | 0.47 | 48% | -0.17% | 0.76 |
| CPI | ETH | all | 93 | 1.08% | 45% | +0.10% | 0.41 | 51% | +0.09% | 1.00 |
| NFP | BTC | all | 94 | 0.50% | 46% | -0.17% | 0.47 | 41% | -0.24% | 0.12 |
| NFP | ETH | all | 94 | 0.58% | 48% | -0.17% | 0.76 | 43% | -0.25% | 0.18 |
| FOMC | BTC | all | 64 | 0.75% | 52% | +0.21% | 0.90 | 61% | +0.46% | 0.10 |
| FOMC | ETH | all | 63 | 0.92% | 59% | -0.05% | 0.21 | 59% | +0.11% | 0.21 |
| OTHER | BTC | all | 383 | 0.31% | 48% | -0.02% | 0.54 | 47% | -0.08% | 0.31 |
| OTHER | ETH | all | 383 | 0.41% | 46% | -0.06% | 0.10 | 45% | -0.11% | 0.08 |

## Only release bars that moved at least 0.3% (H1's size filter), whole period

| kind | coin | half | n | mean abs release bar | continued 1h | mean 1h | p 1h | continued 4h | mean 4h | p 4h |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CPI | BTC | all | 58 | 1.27% | 47% | +0.03% | 0.69 | 45% | -0.23% | 0.51 |
| CPI | ETH | all | 66 | 1.47% | 45% | +0.18% | 0.54 | 52% | +0.01% | 0.90 |
| NFP | BTC | all | 51 | 0.82% | 41% | -0.21% | 0.26 | 41% | -0.38% | 0.26 |
| NFP | ETH | all | 57 | 0.87% | 49% | -0.15% | 1.00 | 44% | -0.23% | 0.43 |
| FOMC | BTC | all | 34 | 1.30% | 56% | +0.26% | 0.61 | 53% | +0.42% | 0.86 |
| FOMC | ETH | all | 41 | 1.34% | 54% | -0.07% | 0.76 | 63% | +0.17% | 0.12 |
| OTHER | BTC | all | 138 | 0.61% | 43% | -0.07% | 0.15 | 50% | -0.11% | 1.00 |
| OTHER | ETH | all | 180 | 0.71% | 46% | -0.05% | 0.33 | 49% | -0.07% | 0.82 |

## Read

- CPI BTC: continued after 1h 49% / 43% (1st / 2nd half), after 4h 40% / 55%; mean 4h follow-through -0.40% / +0.05%.
- CPI ETH: continued after 1h 41% / 49% (1st / 2nd half), after 4h 43% / 57%; mean 4h follow-through -0.21% / +0.38%.
- NFP BTC: continued after 1h 44% / 48% (1st / 2nd half), after 4h 42% / 41%; mean 4h follow-through -0.29% / -0.18%.
- NFP ETH: continued after 1h 54% / 41% (1st / 2nd half), after 4h 40% / 46%; mean 4h follow-through -0.36% / -0.13%.
- FOMC BTC: continued after 1h 53% / 50% (1st / 2nd half), after 4h 50% / 72%; mean 4h follow-through +0.02% / +0.89%.
- FOMC ETH: continued after 1h 58% / 59% (1st / 2nd half), after 4h 55% / 62%; mean 4h follow-through -0.55% / +0.75%.
- 1 of 64 p-values in the tables are below 0.05 (FOMC BTC 2nd 4h); about 3.2 would be by chance alone.

With roughly 45 releases per kind, coin and half, a continued-share between about 35% and 65% is within what a coin flip produces (the p column says so case by case). BTC and ETH react to the same release, so their rows are not independent evidence.
