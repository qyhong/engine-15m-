# H101: the kitchen sink: every chosen setting of H90-H100 stacked, tested once

**Conclusion: does not.**

Chosen on the choice period: `stacked` (the current setting is `current`). On the test period 2023-06-08 to 2025-11-10, paired by calendar
month over the eight markets, the chosen setting made +2.15 R a month more than the current one on average
(95% month-clustered interval -0.73 to +5.07, 30 months, 20000 draws), one-sided p = 0.0740 against the pass level 0.00417;
BTC and ETH together: +69.7 R over the test period (the rule needs this not negative).

| | current | chosen |
|---|---|---|
| trades | 2212 | 1496 |
| mean R per trade [95%] | -0.015 [-0.066, +0.036] | +0.020 [-0.039, +0.080] |
| worst fall, eight books summed | -22.8% | -15.3% |
| share of bars flat (markets' mean) | 2.0% | 21.6% |
| paper net, eight books ($) | -10309 | -727 |

## Per market, test period (sum of R)

| market | current | chosen | difference |
|---|---|---|---|
| BTCUSDT | -57.1 (398) | -0.6 (257) | +56.6 |
| ETHUSDT | +4.8 (368) | +17.9 (241) | +13.2 |
| XAUUSD | +27.5 (247) | +6.5 (202) | -21.1 |
| XAGUSD | -1.7 (248) | -0.7 (195) | +0.9 |
| USDJPY | +21.3 (299) | +9.0 (204) | -12.3 |
| SPX | +18.5 (106) | +5.5 (64) | -13.0 |
| WTI | -21.4 (262) | +1.6 (168) | +23.0 |
| BRENT | -26.1 (284) | -8.9 (165) | +17.2 |

## Every value on the test period: DESCRIPTIVE, NOT USED FOR ANY CHOICE (computed last)

| value | pooled sum R | BTC+ETH sum R | trades |
|---|---|---|---|
| current | -34.1 | -52.3 | 2212 |
| stacked | +30.4 | +17.4 | 1496 |

Stacked from: H90 `stop_units=2`, H91 `idle_max=16`, H92 `theta_enter=0.1`, H93 `theta_flip=0.1`, H94 `theta_counter=0.15`, H95 `bias=on,tiebreak=on`, H96 `tight_q=0.5`, H97 `block_12-18`, H98 `none`, H99 `none`, H100 `shock=0.05,step_aside=off`

A pass here is a proposal for a forward PAPER shadow book only, and needs the owner's word. Nothing in the engine,
the Setups book or the vault changes. The holdout (2025-11-11 onward) was not loaded.
