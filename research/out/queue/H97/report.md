# H97: no new entry in one 6-hour block of the day (UTC)

**Conclusion: does not.**

Chosen on the choice period: `block_12-18` (the current setting is `none`). On the test period 2023-06-08 to 2025-11-10, paired by calendar
month over the eight markets, the chosen setting made +0.53 R a month more than the current one on average
(95% month-clustered interval -1.53 to +2.72, 30 months, 20000 draws), one-sided p = 0.3193 against the pass level 0.00417;
BTC and ETH together: +34.6 R over the test period (the rule needs this not negative).

| | current | chosen |
|---|---|---|
| trades | 2212 | 2017 |
| mean R per trade [95%] | -0.015 [-0.066, +0.036] | -0.009 [-0.062, +0.044] |
| worst fall, eight books summed | -22.8% | -20.4% |
| share of bars flat (markets' mean) | 2.0% | 4.5% |
| paper net, eight books ($) | -10309 | -10931 |

## Per market, test period (sum of R)

| market | current | chosen | difference |
|---|---|---|---|
| BTCUSDT | -57.1 (398) | -32.7 (343) | +24.4 |
| ETHUSDT | +4.8 (368) | +15.0 (339) | +10.2 |
| XAUUSD | +27.5 (247) | +18.5 (245) | -9.0 |
| XAGUSD | -1.7 (248) | -8.3 (241) | -6.6 |
| USDJPY | +21.3 (299) | +19.6 (280) | -1.7 |
| SPX | +18.5 (106) | +16.1 (103) | -2.4 |
| WTI | -21.4 (262) | -28.5 (236) | -7.1 |
| BRENT | -26.1 (284) | -17.9 (230) | +8.2 |

## The choice period (the only numbers the choice used)

| value | pooled sum R | BTC+ETH sum R | trades |
|---|---|---|---|
| none (current) | +25.2 | +46.9 | 2945 |
| block_00-06 | +60.8 | +42.7 | 2868 |
| block_06-12 | -11.7 | +67.5 | 2903 |
| block_12-18 (chosen) | +71.6 | +54.8 | 2661 |
| block_18-24 | -6.3 | +22.0 | 2864 |

## Every value on the test period: DESCRIPTIVE, NOT USED FOR ANY CHOICE (computed last)

| value | pooled sum R | BTC+ETH sum R | trades |
|---|---|---|---|
| none | -34.1 | -52.3 | 2212 |
| block_00-06 | -50.2 | -23.4 | 2251 |
| block_06-12 | -48.3 | -46.8 | 2187 |
| block_12-18 | -18.2 | -17.7 | 2017 |
| block_18-24 | +10.1 | -1.1 | 2147 |

A pass here is a proposal for a forward PAPER shadow book only, and needs the owner's word. Nothing in the engine,
the Setups book or the vault changes. The holdout (2025-11-11 onward) was not loaded.
