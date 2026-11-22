# H103: daily RSI(14) at or below 30, entry on the first close back above 30

**Conclusion: mixed: see the cells.** (3 readings; each is judged at alpha 0.0028 = 0.05 / 18 Part B tests)

| event, reading | conclusion | events / episodes | win rate (all) | per episode [95% Wilson] | p vs threshold | cluster interval | baseline | difference [95%] | first half / second half |
|---|---|---|---|---|---|---|---|---|---|
| rsi30_reclaim_long / W5 (threshold 55.0%) | too few cases to tell | 45 / 24 | 57.8% | 58.3% [38.8%, 75.5%] | 0.4539 | 42.1%-73.7% | 53.8% | 4.0% [-11.9%, 20.2%] | 58.1% (31) / 57.1% (14) |
| rsi30_reclaim_long / W10 (threshold 55.0%) | too few cases to tell | 44 / 23 | 43.2% | 47.8% [29.2%, 67.0%] | 0.8164 | 25.0%-61.4% | 54.6% | -11.4% [-30.2%, 7.1%] | 45.2% (31) / 38.5% (13) |
| rsi30_reclaim_long / WEMA10 (threshold 55.0%) | not supported | 45 / 24 | 35.6% | 33.3% [18.0%, 53.3%] | 0.9905 | 22.2%-50.0% | 39.9% | -4.4% [-18.0%, 10.6%] | 41.9% (31) / 21.4% (14) |

Data: BTCUSDT 2019-01-01 to 2025-11-10 (2506 days); ETHUSDT 2019-01-01 to 2025-11-10 (2506 days)
The holdout (2025-11-11 onward) was not read. A history check is not proof of anything; a 'supported' reading
leads at most to a proposal for a forward paper shadow book, on the owner's word.
