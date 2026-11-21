# H62: the Setups book with the main book's stop where it is wider

History replay to 2026-11-21 13:45 UTC, paper. Registered before any number (research/HYPOTHESES.md).

Gate: the reduced copy reproduced `b_targets` on 8 of 8 markets.

## Pooled, eight markets

| Book | Net | First half | Second half | Holdout | Forward | Trades | Won | Worst fall | Worst trade | Sum of R (all / 1st / 2nd / forward) | Worst R | Wide at entry | Largest stop ratio | Moves out / in |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| current rule | -21575 | -4982 | -16593 | -1273 | +4134 | 5964 | 42.6% | -60.6% | -5655 | +21.7 / +24.3 / -2.6 / +28.1 | -1.9 | - | - | - |
| A wide_entry | -20357 | +1546 | -21903 | -2103 | +3612 | 5699 | 43.8% | -64.4% | -6460 | +20.0 / +32.1 / -12.0 / +26.9 | -1.9 | 8.5% | 47.5x | - |
| B wide_follow | -13272 | -1718 | -11555 | +1846 | +4622 | 5683 | 44.2% | -61.7% | -6298 | +29.7 / +27.7 / +2.0 / +28.3 | -2.3 | 7.8% | 47.5x | 540 / 458 |
| C wide_entry_tighten | -18203 | +2617 | -20820 | -459 | +3885 | 5733 | 43.6% | -64.3% | -6645 | +39.4 / +38.6 / +0.7 / +26.9 | -1.9 | 8.6% | 47.5x | 0 / 254 |

R = a trade's result divided by its own risk at the stop it carried at the fill. The paper book trades BTC and
ETH at full size whatever the stop, so its dollars grow with a wider stop; a member is sized to lose a fixed share
of the wallet at the stop, so the sum of R is the member's view.

## BTC and ETH only (what the vault copies)

| Book | Net | First half | Second half | Holdout | Forward | Trades | Won | Worst fall | Worst trade | Sum of R (all / 1st / 2nd / forward) | Worst R | Wide at entry | Largest stop ratio | Moves out / in |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| current rule | -5136 | -2983 | -2153 | +6058 | +1829 | 2075 | 44.0% | -77.5% | -5655 | -8.6 / +46.1 / -54.7 / +10.7 | -1.4 | - | - | - |
| A wide_entry | -7244 | -1873 | -5371 | +4049 | +1566 | 1968 | 45.0% | -75.5% | -5655 | -12.6 / +36.9 / -49.5 / +10.1 | -1.4 | 13.6% | 3.9x | - |
| B wide_follow | +375 | -7531 | +7906 | +8400 | +2527 | 1996 | 45.5% | -76.9% | -5570 | -6.9 / +23.6 / -30.4 / +11.5 | -2.3 | 11.9% | 3.9x | 306 / 270 |
| C wide_entry_tighten | -4778 | -288 | -4490 | +5788 | +1870 | 1990 | 44.8% | -74.5% | -5655 | +0.8 / +46.6 / -45.8 / +10.1 | -1.4 | 13.1% | 3.9x | 0 / 158 |

## Verdict for A (PRIMARY)

A is NOT SHOWN TO BE BETTER than the current rule by the registered bar. Checks: pooled_first_half yes, pooled_second_half NO, worst_fall_not_deeper NO, btc_eth_first_half yes, btc_eth_second_half NO.

## Per market (net, trades, worst fall)

| Market | current rule | A wide_entry | B wide_follow | C wide_entry_tighten | Main (live rules) | Main flat |
|---|---|---|---|---|---|---|
| SPX | +1565 (240, -26.1%) | +1844 (119, -32.8%) | +1844 (119, -32.8%) | +1844 (119, -32.8%) | +4730 (65) | 0% |
| USDJPY | -882 (722, -53.1%) | -882 (722, -53.1%) | -882 (722, -53.1%) | -882 (722, -53.1%) | -882 (1022) | 2% |
| BTCUSDT | -9196 (1062, -98.0%) | -8855 (996, -96.9%) | -9448 (1019, -98.4%) | -8777 (995, -96.8%) | -9199 (1487) | 24% |
| ETHUSDT | +4059 (1013, -76.2%) | +1611 (972, -81.3%) | +9823 (977, -81.4%) | +3999 (995, -78.7%) | -9464 (1569) | 26% |
| XAUUSD | -2466 (750, -74.6%) | -543 (742, -67.9%) | -26 (737, -66.2%) | -1141 (744, -69.9%) | -744 (258) | 85% |
| XAGUSD | -6526 (725, -83.7%) | -7005 (729, -85.8%) | -6769 (726, -85.9%) | -6547 (725, -83.7%) | -771 (228) | 84% |
| WTI | -3256 (731, -90.2%) | -828 (701, -89.1%) | -3008 (700, -91.5%) | -1766 (718, -90.5%) | +8943 (825) | 48% |
| BRENT | -4874 (721, -84.5%) | -5700 (718, -87.5%) | -4806 (683, -87.9%) | -4933 (715, -85.4%) | +12231 (861) | 47% |

## The ETH trade of 20 Nov 2026 in the replay

- current rule: in 2026-11-20 19:00 at 1616.66, own stop 1700.43, carried 1700.43 (1.0x), out 2026-11-21 13:30 STOP, -800
- A wide_entry: in 2026-11-20 19:00 at 1616.66, own stop 1700.43, carried 1700.43 (1.0x), out 2026-11-21 13:30 STOP, -661
- B wide_follow: in 2026-11-20 19:00 at 1616.66, own stop 1700.43, carried 1700.43 (1.0x), out 2026-11-21 13:30 STOP, -1129
- C wide_entry_tighten: in 2026-11-20 19:00 at 1616.66, own stop 1700.43, carried 1700.43 (1.0x), out 2026-11-21 13:30 STOP, -797

Not in the replay: the main book's total-risk cap across books. A replay is not a forward result.
