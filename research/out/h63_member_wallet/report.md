# H63: one member wallet on the Setups book's BTC and ETH trades, three sizings

History replay 2020-02-05 00:00 to 2026-11-21 13:45 UTC, 2076 trades, paper. Registered before any number (research/HYPOTHESES.md).
Fees 0.10% of the notional per side; funding from the stored Binance series (BTCUSDT 7884, ETHUSDT 7650 rows used, 8 funding times had no bar).

Gate: BTCUSDT passed (largest relative gap 2.11e-15 over 238079 bars, 1063 trades); ETHUSDT passed (largest relative gap 6.17e-15 over 238079 bars, 1013 trades)

## (a) and (c): one 10,000 wallet over the whole replay

| Sizing | Final | Worst fall | Lowest equity | Wiped out | Joined / trimmed / capped / not joined | Fees | Funding paid | Final without funding | Worst day | Longest losing run |
|---|---|---|---|---|---|---|---|---|---|---|
| S1: 2% rule | 3,208 | -86.7% | 2,254 (2026-08-19 06:00) | no | 1907 / 345 / 994 / 169 | 14,338 | 3,408 | 4,327 | -6.6% (2024-03-05) | 13 |
| S2: 100% per coin | 847 | -98.6% | 426 (2026-08-19 06:00) | no | 2040 / 174 / 0 / 36 | 28,220 | 9,758 | 1,677 | -19.6% (2026-02-06) | 13 |
| S3: 3x book | 100 | -99.9% | 40 (2026-08-19 06:00) | no | 1965 / 480 / 0 / 111 | 31,295 | 11,140 | 232 | -21.7% (2026-02-06) | 13 |

## (b): a fresh 10,000 wallet from every month-start, 365 days each

| Sizing | Month-starts | +100% first | -50% first | Wiped out | Neither in 365 days | Unfinished | Median days to either | Median days to +100% | Median days to -50% | Median end when neither |
|---|---|---|---|---|---|---|---|---|---|---|
| S1: 2% rule | 81 | 0 | 4 | 0 | 65 | 12 | 313 | n/a | 313 | 7,984 |
| S2: 100% per coin | 81 | 16 | 37 | 0 | 16 | 12 | 195 | 123 | 222 | 6,930 |
| S3: 3x book | 81 | 24 | 54 | 0 | 1 | 2 | 130 | 83 | 166 | 7,464 |

The same, month-starts before 2023-06-08 and from it:

| Sizing | Month-starts | +100% first | -50% first | Wiped out | Neither | Unfinished | Median days to either | to +100% | to -50% | Median end when neither |
|---|---|---|---|---|---|---|---|---|---|---|
| S1: 2% rule, first half | 40 | 0 | 0 | 0 | 40 | 0 | n/a | n/a | n/a | 8,566 |
| S1: 2% rule, second half | 41 | 0 | 4 | 0 | 25 | 12 | 313 | n/a | 313 | 6,825 |
| S2: 100% per coin, first half | 40 | 15 | 17 | 0 | 8 | 0 | 191 | 132 | 230 | 7,051 |
| S2: 100% per coin, second half | 41 | 1 | 20 | 0 | 8 | 12 | 215 | 64 | 215 | 6,928 |
| S3: 3x book, first half | 40 | 16 | 24 | 0 | 0 | 0 | 126 | 96 | 191 | n/a |
| S3: 3x book, second half | 41 | 8 | 30 | 0 | 1 | 2 | 143 | 55 | 157 | 7,464 |

## (d): the forward record alone (the live book's own trades)

2026-11-11 06:45 to 2026-11-22 05:45 UTC: 13 trades, 2 still open. TOO SHORT TO JUDGE.

| Sizing | Equity now | Worst fall | Joined / trimmed / capped / not joined | Funding paid | Wiped out |
|---|---|---|---|---|---|
| S1: 2% rule | 11,933 | -4.7% | 12 / 0 / 5 / 1 | -8 | no |
| S2: 100% per coin | 14,131 | -10.7% | 13 / 0 / 0 / 0 | -17 | no |
| S3: 3x book | 15,235 | -15.1% | 13 / 3 / 0 / 0 | -23 | no |

Not modelled: the member's fill against the book's (slippage, the vault's join window), refusals, exchange
limits, rounding. The brake is a model of the vault's, not its code. Wipe-out: equity at each position's worst
price of a bar at or below 0.5% of the open notional. A history replay is a warm-up, not a forward result.
