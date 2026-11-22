# H68: the Setups rule that waits for a real signal after a stop-out

History replay, every book run by the engine's own code. Registered before any number. The idea was found on
this same history (H65, H66), so this replay cannot validate it; the forward shadow book `b_wait_stop` is the test.
Every cell: trades, share won, mean R, sum of R, paper net, share of bars flat (pooled: the markets' mean).

## Verdict by the registered bar

**The pattern SURVIVES as a rule.** Checks: pooled_sum_r_h1 yes, pooled_sum_r_h2 yes, vault_sum_r_h1 yes, vault_sum_r_h2 yes, mean_r_positive_h1 yes, mean_r_positive_h2 yes, worst_fall_not_deeper yes.

## All eight markets

| Book | All | First half | Second half | Holdout | Forward | Worst fall |
|---|---|---|---|---|---|---|
| current rule | 5963, 43%, +0.004, +22.5, -21233, flat 2% | 2953, 43%, +0.010, +29.6, -4701, flat 2% | 3010, 42%, -0.002, -7.1, -16532, flat 2% | 793, 43%, +0.027, +21.1, -1117, flat 2% | 21, 76%, +0.874, +18.3, +4175, flat 2% | -61.6% |
| wait after a stop | 3389, 45%, +0.042, +143.9, +38537, flat 56% | 2090, 45%, +0.054, +113.3, +42343, flat 42% | 1299, 45%, +0.024, +30.5, -3806, flat 68% | 291, 49%, +0.105, +30.7, +8895, flat 68% | 13, 62%, +0.516, +6.7, +1653, flat 70% | -32.4% |
| both (wait + 30-day filter; descriptive) | 2516, 46%, +0.067, +169.5, +5906, flat 67% | 1525, 45%, +0.072, +110.1, +15428, flat 58% | 991, 47%, +0.060, +59.4, -9521, flat 75% | 250, 48%, +0.097, +24.2, -712, flat 73% | 11, 64%, +0.658, +7.2, +1697, flat 76% | -27.6% |

## BTC and ETH

| Book | All | First half | Second half | Holdout | Forward | Worst fall |
|---|---|---|---|---|---|---|
| current rule | 2074, 44%, -0.004, -7.7, -4794, flat 1% | 991, 46%, +0.045, +44.7, -2702, flat 1% | 1083, 42%, -0.048, -52.5, -2092, flat 1% | 305, 45%, +0.040, +12.3, +6214, flat 1% | 9, 67%, +0.599, +5.4, +1869, flat 1% | -78.5% |
| wait after a stop | 1761, 46%, +0.037, +64.5, +10032, flat 21% | 908, 46%, +0.052, +47.3, +8687, flat 14% | 853, 46%, +0.020, +17.3, +1346, flat 27% | 208, 48%, +0.064, +13.3, +9986, flat 29% | 11, 64%, +0.658, +7.2, +1650, flat 5% | -70.1% |
| both (wait + 30-day filter; descriptive) | 1311, 47%, +0.071, +93.1, -1258, flat 40% | 664, 48%, +0.103, +68.7, +10710, flat 35% | 647, 46%, +0.038, +24.4, -11967, flat 45% | 182, 46%, +0.056, +10.2, -291, flat 44% | 11, 64%, +0.658, +7.2, +1697, flat 5% | -63.9% |

## The other six

| Book | All | First half | Second half | Holdout | Forward | Worst fall |
|---|---|---|---|---|---|---|
| current rule | 3889, 42%, +0.008, +30.3, -16439, flat 2% | 1962, 41%, -0.008, -15.1, -1999, flat 2% | 1927, 43%, +0.024, +45.4, -14440, flat 2% | 488, 43%, +0.018, +8.8, -7331, flat 2% | 12, 83%, +1.080, +13.0, +2305, flat 2% | -65.9% |
| wait after a stop | 1628, 44%, +0.049, +79.3, +28505, flat 67% | 1182, 44%, +0.056, +66.1, +33656, flat 52% | 446, 45%, +0.030, +13.3, -5151, flat 82% | 83, 52%, +0.210, +17.4, -1091, flat 81% | 2, 50%, -0.264, -0.5, +2, flat 91% | -24.7% |
| both (wait + 30-day filter; descriptive) | 1205, 44%, +0.063, +76.4, +7164, flat 76% | 861, 43%, +0.048, +41.4, +4718, flat 65% | 344, 48%, +0.102, +35.0, +2446, flat 85% | 68, 53%, +0.206, +14.0, -421, flat 83% | - | -22.0% |

## Withheld forced entries and waits

| Markets | Book | Stop-outs with a withheld forced entry | Sessions withheld | Waits after a stop: n, median h, longest h |
|---|---|---|---|---|
| All eight | wait after a stop | 1259 | 601021 | 1610, 17.0, 14665.5 |
| All eight | both (wait + 30-day filter; descriptive) | 1087 | 735348 | 1238, 37.4, 13193.5 |
| BTC + ETH | wait after a stop | 651 | 93189 | 845, 10.8, 352.8 |
| BTC + ETH | both (wait + 30-day filter; descriptive) | 596 | 166600 | 651, 33.2, 794.0 |
| Other six | wait after a stop | 608 | 507832 | 765, 26.5, 14665.5 |
| Other six | both (wait + 30-day filter; descriptive) | 491 | 568748 | 587, 46.2, 13193.5 |

## What the withheld entries made in the current rule's record

The current rule's trades entered by FORCE right after a trade ended at the entry stop: trades, share won, mean R, sum of R.

| Markets | All | First half | Second half | Holdout | Forward |
|---|---|---|---|---|---|
| All eight | 2675, 40%, -0.019, -51.7 | 1220, 40%, -0.012, -15.1 | 1455, 40%, -0.025, -36.6 | 396, 42%, +0.011, +4.3 | 3, 67%, +1.394, +4.2 |
| BTC + ETH | 762, 40%, -0.070, -53.1 | 311, 40%, -0.040, -12.5 | 451, 39%, -0.090, -40.6 | 139, 45%, +0.038, +5.3 | 1, 100%, +2.430, +2.4 |
| Other six | 1913, 40%, +0.001, +1.4 | 909, 40%, -0.003, -2.6 | 1004, 40%, +0.004, +3.9 | 257, 40%, -0.004, -1.0 | 2, 50%, +0.876, +1.8 |

## Per market (all: trades, won, mean R, sum R, net, flat; worst fall)

| Market | current rule | wait after a stop | both (descriptive) |
|---|---|---|---|
| BTCUSDT | 1062, 42%, -0.063, -66.9, -9202, flat 1%; -98.0% | 880, 45%, +0.005, +4.2, -6642, flat 21%; -78.2% | 656, 47%, +0.066, +43.2, +3163, flat 39%; -71.6% |
| ETHUSDT | 1012, 46%, +0.058, +59.2, +4407, flat 1%; -75.6% | 881, 47%, +0.069, +60.4, +16674, flat 21%; -75.0% | 655, 47%, +0.076, +49.9, -4420, flat 42%; -90.5% |
| XAUUSD | 750, 42%, +0.012, +9.0, -2466, flat 2%; -74.6% | 179, 43%, +0.034, +6.0, +619, flat 84%; -32.8% | 124, 38%, -0.059, -7.3, -1759, flat 90%; -34.2% |
| XAGUSD | 725, 44%, +0.006, +4.4, -6526, flat 2%; -83.7% | 160, 48%, +0.084, +13.4, +1236, flat 81%; -30.1% | 112, 41%, -0.069, -7.8, -2676, flat 89%; -44.8% |
| USDJPY | 722, 42%, +0.012, +8.5, -882, flat 2%; -53.1% | 395, 39%, -0.042, -16.7, -3697, flat 59%; -59.0% | 236, 43%, +0.071, +16.8, +2822, flat 72%; -36.7% |
| SPX | 240, 43%, +0.080, +19.2, +1565, flat 2%; -26.1% | 19, 37%, +0.034, +0.6, +105, flat 94%; -9.4% | 9, 44%, +0.235, +2.1, +371, flat 97%; -6.8% |
| WTI | 731, 41%, -0.008, -5.7, -3256, flat 2%; -90.2% | 440, 47%, +0.090, +39.6, +22382, flat 44%; -43.0% | 363, 48%, +0.111, +40.4, +4197, flat 54%; -62.0% |
| BRENT | 721, 41%, -0.007, -5.2, -4874, flat 2%; -84.5% | 435, 46%, +0.084, +36.4, +7860, flat 42%; -40.3% | 361, 45%, +0.089, +32.2, +4208, flat 53%; -46.7% |
