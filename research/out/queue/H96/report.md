# H96: no new entry when the stop would be unusually tight

**Conclusion: does not.**

Chosen on the choice period: `tight_q=0.5` (the current setting is `none`). On the test period 2023-06-08 to 2025-11-10, paired by calendar
month over the eight markets, the chosen setting made +0.44 R a month more than the current one on average
(95% month-clustered interval -2.66 to +3.46, 30 months, 20000 draws), one-sided p = 0.3834 against the pass level 0.00417;
BTC and ETH together: +32.6 R over the test period (the rule needs this not negative).

| | current | chosen |
|---|---|---|
| trades | 2212 | 1728 |
| mean R per trade [95%] | -0.015 [-0.066, +0.036] | -0.012 [-0.070, +0.047] |
| worst fall, eight books summed | -22.8% | -18.1% |
| share of bars flat (markets' mean) | 2.0% | 15.3% |
| paper net, eight books ($) | -10309 | -9736 |

## Per market, test period (sum of R)

| market | current | chosen | difference |
|---|---|---|---|
| BTCUSDT | -57.1 (398) | -19.2 (296) | +37.9 |
| ETHUSDT | +4.8 (368) | -0.5 (295) | -5.3 |
| XAUUSD | +27.5 (247) | +32.3 (202) | +4.7 |
| XAGUSD | -1.7 (248) | -9.2 (221) | -7.6 |
| USDJPY | +21.3 (299) | +22.4 (220) | +1.0 |
| SPX | +18.5 (106) | +5.5 (75) | -13.1 |
| WTI | -21.4 (262) | -29.5 (210) | -8.2 |
| BRENT | -26.1 (284) | -22.4 (209) | +3.7 |

## The choice period (the only numbers the choice used)

| value | pooled sum R | BTC+ETH sum R | trades |
|---|---|---|---|
| none (current) | +25.2 | +46.9 | 2945 |
| tight_q=0.2 | +42.0 | +41.6 | 2714 |
| tight_q=0.33 | +46.6 | +46.5 | 2558 |
| tight_q=0.5 (chosen) | +65.4 | +64.5 | 2221 |

## Every value on the test period: DESCRIPTIVE, NOT USED FOR ANY CHOICE (computed last)

| value | pooled sum R | BTC+ETH sum R | trades |
|---|---|---|---|
| none | -34.1 | -52.3 | 2212 |
| tight_q=0.2 | -38.7 | -41.2 | 2066 |
| tight_q=0.33 | -23.2 | -32.7 | 1937 |
| tight_q=0.5 | -20.8 | -19.7 | 1728 |

A pass here is a proposal for a forward PAPER shadow book only, and needs the owner's word. Nothing in the engine,
the Setups book or the vault changes. The holdout (2025-11-11 onward) was not loaded.
