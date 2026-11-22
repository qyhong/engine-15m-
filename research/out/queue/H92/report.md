# H92: the entry bar (theta_enter)

**Conclusion: does not.**

Chosen on the choice period: `theta_enter=0.1` (the current setting is `theta_enter=0.05`). On the test period 2023-06-08 to 2025-11-10, paired by calendar
month over the eight markets, the chosen setting made +1.79 R a month more than the current one on average
(95% month-clustered interval -0.09 to +3.67, 30 months, 20000 draws), one-sided p = 0.0307 against the pass level 0.00417;
BTC and ETH together: +40.7 R over the test period (the rule needs this not negative).

| | current | chosen |
|---|---|---|
| trades | 2212 | 2146 |
| mean R per trade [95%] | -0.015 [-0.066, +0.036] | +0.009 [-0.038, +0.058] |
| worst fall, eight books summed | -22.8% | -19.9% |
| share of bars flat (markets' mean) | 2.0% | 2.1% |
| paper net, eight books ($) | -10309 | -3934 |

## Per market, test period (sum of R)

| market | current | chosen | difference |
|---|---|---|---|
| BTCUSDT | -57.1 (398) | -24.7 (355) | +32.4 |
| ETHUSDT | +4.8 (368) | +13.1 (353) | +8.3 |
| XAUUSD | +27.5 (247) | +24.8 (247) | -2.7 |
| XAGUSD | -1.7 (248) | -1.1 (247) | +0.5 |
| USDJPY | +21.3 (299) | +30.9 (298) | +9.6 |
| SPX | +18.5 (106) | +18.5 (106) | +0.0 |
| WTI | -21.4 (262) | -13.4 (253) | +8.0 |
| BRENT | -26.1 (284) | -28.7 (287) | -2.6 |

## The choice period (the only numbers the choice used)

| value | pooled sum R | BTC+ETH sum R | trades |
|---|---|---|---|
| theta_enter=0.02 | -17.4 | +8.5 | 3210 |
| theta_enter=0.03 | -10.0 | +1.4 | 3076 |
| theta_enter=0.05 (current) | +25.2 | +46.9 | 2945 |
| theta_enter=0.08 | +32.1 | +54.3 | 2871 |
| theta_enter=0.1 (chosen) | +33.4 | +54.1 | 2904 |

## Every value on the test period: DESCRIPTIVE, NOT USED FOR ANY CHOICE (computed last)

| value | pooled sum R | BTC+ETH sum R | trades |
|---|---|---|---|
| theta_enter=0.02 | +14.1 | +7.7 | 2393 |
| theta_enter=0.03 | -49.9 | -21.8 | 2300 |
| theta_enter=0.05 | -34.1 | -52.3 | 2212 |
| theta_enter=0.08 | +18.7 | -12.5 | 2149 |
| theta_enter=0.1 | +19.5 | -11.7 | 2146 |

A pass here is a proposal for a forward PAPER shadow book only, and needs the owner's word. Nothing in the engine,
the Setups book or the vault changes. The holdout (2025-11-11 onward) was not loaded.
