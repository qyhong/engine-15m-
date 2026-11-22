# H100: the high-risk rules (theta_enter_shock, step_aside)

**Conclusion: does not.**

Chosen on the choice period: `shock=0.05,step_aside=off` (the current setting is `shock=0.1,step_aside=off`). On the test period 2023-06-08 to 2025-11-10, paired by calendar
month over the eight markets, the chosen setting made +0.69 R a month more than the current one on average
(95% month-clustered interval -0.46 to +1.90, 30 months, 20000 draws), one-sided p = 0.1220 against the pass level 0.00417;
BTC and ETH together: +26.4 R over the test period (the rule needs this not negative).

| | current | chosen |
|---|---|---|
| trades | 2212 | 2214 |
| mean R per trade [95%] | -0.015 [-0.066, +0.036] | -0.006 [-0.056, +0.046] |
| worst fall, eight books summed | -22.8% | -24.4% |
| share of bars flat (markets' mean) | 2.0% | 1.9% |
| paper net, eight books ($) | -10309 | -10336 |

## Per market, test period (sum of R)

| market | current | chosen | difference |
|---|---|---|---|
| BTCUSDT | -57.1 (398) | -31.5 (397) | +25.6 |
| ETHUSDT | +4.8 (368) | +5.6 (379) | +0.8 |
| XAUUSD | +27.5 (247) | +28.9 (247) | +1.3 |
| XAGUSD | -1.7 (248) | -0.4 (248) | +1.3 |
| USDJPY | +21.3 (299) | +19.8 (300) | -1.5 |
| SPX | +18.5 (106) | +18.5 (106) | +0.0 |
| WTI | -21.4 (262) | -24.9 (255) | -3.5 |
| BRENT | -26.1 (284) | -29.3 (282) | -3.2 |

## The choice period (the only numbers the choice used)

| value | pooled sum R | BTC+ETH sum R | trades |
|---|---|---|---|
| shock=0.05,step_aside=off (chosen) | +54.9 | +63.7 | 3079 |
| shock=0.05,step_aside=on | -22.5 | -10.0 | 5411 |
| shock=0.1,step_aside=off (current) | +25.2 | +46.9 | 2945 |
| shock=0.1,step_aside=on | -46.8 | -28.3 | 5395 |
| shock=0.2,step_aside=off | +14.2 | +35.7 | 2919 |
| shock=0.2,step_aside=on | -34.4 | -15.8 | 5371 |

## Every value on the test period: DESCRIPTIVE, NOT USED FOR ANY CHOICE (computed last)

| value | pooled sum R | BTC+ETH sum R | trades |
|---|---|---|---|
| shock=0.05,step_aside=off | -13.3 | -25.9 | 2214 |
| shock=0.05,step_aside=on | -133.0 | -60.7 | 4405 |
| shock=0.1,step_aside=off | -34.1 | -52.3 | 2212 |
| shock=0.1,step_aside=on | -162.0 | -82.5 | 4423 |
| shock=0.2,step_aside=off | -41.8 | -50.5 | 2233 |
| shock=0.2,step_aside=on | -161.3 | -77.3 | 4402 |

A pass here is a proposal for a forward PAPER shadow book only, and needs the owner's word. Nothing in the engine,
the Setups book or the vault changes. The holdout (2025-11-11 onward) was not loaded.
