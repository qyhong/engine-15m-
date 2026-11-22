# H105: a daily close back above the EMA200 after at least 30 days below it

**Conclusion: too few cases to tell.** (3 readings; each is judged at alpha 0.0028 = 0.05 / 18 Part B tests)

| event, reading | conclusion | events / episodes | win rate (all) | per episode [95% Wilson] | p vs threshold | cluster interval | baseline | difference [95%] | first half / second half |
|---|---|---|---|---|---|---|---|---|---|
| ema200_reclaim_after_30d_long / W5 (threshold 55.0%) | too few cases to tell | 12 / 9 | 75.0% | 77.8% [45.3%, 93.7%] | 0.1495 | 50.0%-94.3% | 53.8% | 21.2% [-5.2%, 42.9%] | 77.8% (9) / 66.7% (3) |
| ema200_reclaim_after_30d_long / W10 (threshold 55.0%) | too few cases to tell | 12 / 9 | 75.0% | 88.9% [56.5%, 98.0%] | 0.0385 | 53.8%-100.0% | 54.5% | 20.5% [-0.8%, 42.5%] | 77.8% (9) / 66.7% (3) |
| ema200_reclaim_after_30d_long / WEMA10 (threshold 55.0%) | too few cases to tell | 12 / 9 | 58.3% | 66.7% [35.4%, 87.9%] | 0.3614 | 30.8%-83.3% | 39.8% | 18.5% [-8.3%, 43.3%] | 55.6% (9) / 66.7% (3) |

Data: BTCUSDT 2019-01-01 to 2025-11-10 (2506 days); ETHUSDT 2019-01-01 to 2025-11-10 (2506 days)
The holdout (2025-11-11 onward) was not read. A history check is not proof of anything; a 'supported' reading
leads at most to a proposal for a forward paper shadow book, on the owner's word.
