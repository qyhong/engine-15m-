# H107: a long after a capitulation low that rebounds (BTC and ETH)

**Verdict by the registered rule: no pass.** Rule A FAILS. Rule B has too few trades to judge (no pass).
Registered in `research/HYPOTHESES.md` (H107, commit 9d271ea) before any history number was computed.
Data 2019-10-01 to 2025-11-10 23:45 UTC (the holdout from 2025-11-11 was not read, except the bars of 19-23 Nov 2026
for the event read below). Fees 0.10% a side. Stop = the engine's stop, 3 x ATR(1h). Code
`research/h107_capitulation_rebound.py`; numbers in `results.json`, the event in `event.json`.

## The rules (shaped by the 20-23 Nov 2026 event; see the registration)

- **Rule A.** At a 15m close: the lowest low of the last 4 hours is a fresh 30-day low, that low is at least 10% under
  the price a week earlier, and the close is at least 2 x ATR(1h) above that low (first bar only). Buy at the next
  open. Stop 3 x ATR(1h) under the entry. Half out at +1R (then the stop on the rest goes to the entry), the rest at
  +2R, else out after 48 hours.
- **Rule B.** Rule A, only when the last funding rate is negative (shorts paying).

## Results (R net of fees; 95% month-clustered interval; one-sided p for mean R > 0)

| Rule | Part | Trades | Won | Mean R | Sum R | 95% interval | p |
|---|---|---|---|---|---|---|---|
| A | all, BTC + ETH | 123 | 47% | -0.006 | -0.7 | -0.220 to +0.273 | 0.545 (Holm 0.545) |
| A | first half (to 2023-06-07) | 83 | 37% | -0.127 | -10.6 | -0.377 to +0.255 | 0.83 |
| A | second half | 40 | 68% | +0.246 | +9.8 | -0.029 to +0.556 | 0.057 |
| A | BTC, all | 54 | 41% | -0.041 | -2.2 | -0.313 to +0.307 | 0.63 |
| A | ETH, all | 69 | 52% | +0.021 | +1.5 | -0.191 to +0.316 | 0.44 |
| B | all, BTC + ETH | 32 | 59% | +0.194 | +6.2 | -0.110 to +0.622 | 0.182 (Holm 0.364) |
| B | first half | 19 | 47% | +0.079 | +1.5 | -0.286 to +0.829 | 0.40 |
| B | second half | 13 | 77% | +0.362 | +4.7 | -0.119 to +0.828 | 0.059 |
| B | BTC, all | 8 | 50% | +0.277 | +2.2 | wide | 0.26 |
| B | ETH, all | 24 | 63% | +0.166 | +4.0 | -0.142 to +0.538 | 0.18 |

Checks for rule A: enough trades yes; first half above zero NO; second half yes; BTC above zero NO; ETH yes;
Holm p below 0.05 NO; above the random-entry baseline yes (+0.19R, interval -0.03 to +0.46).
Rule B: 32 trades against 60 needed, 19 and 13 per half against 20 needed; Holm p 0.36.

Other facts. Rule A: 51 of 123 trades hit the stop; longest losing run 11; deepest fall of cumulative R -19.3R (in
2022). By year (trades, sum R): 2019 6, +0.7; 2020 10, -6.7; 2021 18, +7.7; 2022 44, -14.1; 2023 8, +1.3; 2024 15,
+5.7; 2025 22, +4.7. Rule B: 16 of its 32 trades are in 2022 (sum -0.4R); its gain is 2024-2025 (13 trades, +4.7R).
Random long entries in the same coin-months lost: the rules' excess over them is positive (A +0.19R, B +0.37R), but
those are crash months, where most longs lost.

Descriptive only (decides nothing): moving one setting (rebound 1.5 / 2.5 ATR, drop 8% / 12%, hold 24 / 96 hours)
never makes rule A's first half positive (-0.05R to -0.21R a trade) and never makes its second half negative
(+0.23R to +0.41R). Rule B stays between +0.07R and +0.30R a trade on 12 to 44 trades.

Look-ahead guards: the readings recomputed on data cut at each signal bar (and random bars), 561 bars, 0 mismatches;
the vectorised trade walk equals a bar-by-bar walk on every trade.

## The event itself (21 Nov 2026; inside the holdout, not part of the test)

Both rules fire once per coin at the 06:45 UTC close on 21 Nov: BTC long 57,194 (stop 54,664, T1 59,724, T2 62,254),
ETH long 1,613.70 (stop 1,534, T1 1,693, T2 1,773). Both took Target 1 on 21 Nov and closed the rest at the 48-hour
mark (23 Nov 06:30 bar): BTC +1.31R, ETH +1.16R. They were flat for today's +4% candle. The main book SOLD ETH short
at the same 1,613.70 at the same close.

## Reading

The rule made money on this one event, and in the two and a half years before the holdout, but lost over 2019-2023
(above all in 2022, when bounces off new lows kept failing). Over the whole period it is flat after fees. That fails
the test. With negative funding the result is better but rests on 32 trades, half of them in 2022, and is not
significant. Both rules were built after seeing this event, so even the good second half is a weak sign. Nothing here
supports a paper shadow book on the registered bar. No engine code, book or vault was changed.

## Deviations

1. ETH's funding file starts 2019-11-27 (the registration said funding exists from 2019-09-10, true for BTC only), so
   rule B could not fire on ETH in Oct-Nov 2019.
2. The first history run crashed in the look-ahead test (an empty funding slice before ETH's first rate) before
   anything was printed or written. The fix (an empty slice reads as "no funding yet") changes no rule; the run was
   repeated.
