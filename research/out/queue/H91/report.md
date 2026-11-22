# H91: the forced-entry clock (idle_max)

**Conclusion: does not.**

Chosen on the choice period: `idle_max=16` (the current setting is `idle_max=4`). On the test period 2023-06-08 to 2025-11-10, paired by calendar
month over the eight markets, the chosen setting made -1.05 R a month more than the current one on average
(95% month-clustered interval -3.57 to +1.50, 30 months, 20000 draws), one-sided p = 0.7892 against the pass level 0.00417;
BTC and ETH together: +68.2 R over the test period (the rule needs this not negative).

| | current | chosen |
|---|---|---|
| trades | 2212 | 2119 |
| mean R per trade [95%] | -0.015 [-0.066, +0.036] | -0.031 [-0.085, +0.023] |
| worst fall, eight books summed | -22.8% | -26.8% |
| share of bars flat (markets' mean) | 2.0% | 6.7% |
| paper net, eight books ($) | -10309 | -18249 |

## Per market, test period (sum of R)

| market | current | chosen | difference |
|---|---|---|---|
| BTCUSDT | -57.1 (398) | -16.0 (364) | +41.1 |
| ETHUSDT | +4.8 (368) | +31.8 (336) | +27.0 |
| XAUUSD | +27.5 (247) | -5.3 (266) | -32.9 |
| XAGUSD | -1.7 (248) | -25.8 (253) | -24.1 |
| USDJPY | +21.3 (299) | -0.9 (279) | -22.2 |
| SPX | +18.5 (106) | +6.6 (106) | -12.0 |
| WTI | -21.4 (262) | -14.5 (239) | +6.9 |
| BRENT | -26.1 (284) | -41.4 (276) | -15.3 |

## The choice period (the only numbers the choice used)

| value | pooled sum R | BTC+ETH sum R | trades |
|---|---|---|---|
| idle_max=2 | +14.2 | +13.9 | 3113 |
| idle_max=4 (current) | +25.2 | +46.9 | 2945 |
| idle_max=8 | +53.1 | +46.4 | 2885 |
| idle_max=16 (chosen) | +48.6 | +57.5 | 2826 |
| idle_max=48 | +48.1 | +62.7 | 2791 |
| idle_max=never | +83.8 | +19.1 | 1917 |

## Every value on the test period: DESCRIPTIVE, NOT USED FOR ANY CHOICE (computed last)

| value | pooled sum R | BTC+ETH sum R | trades |
|---|---|---|---|
| idle_max=2 | -98.4 | -44.2 | 2326 |
| idle_max=4 | -34.1 | -52.3 | 2212 |
| idle_max=8 | -60.0 | -7.5 | 2123 |
| idle_max=16 | -65.6 | +15.8 | 2119 |
| idle_max=48 | -86.9 | -29.5 | 2071 |
| idle_max=never | +14.2 | +2.4 | 899 |

A pass here is a proposal for a forward PAPER shadow book only, and needs the owner's word. Nothing in the engine,
the Setups book or the vault changes. The holdout (2025-11-11 onward) was not loaded.
