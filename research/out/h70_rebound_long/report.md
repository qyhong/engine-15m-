# H70: a long on a sharp rebound out of an oversold state (BTC and ETH, three sealed stages)

Registered in research/HYPOTHESES.md before any number. R after fees (0.10% a side). Excess = R minus the mean R
of the same trade entered at every eligible bar of the same coin and calendar month. Intervals and p-values:
month-clustered bootstrap, 5000 draws, seed 20261122. No result here is a proven edge.

## Stage 1 (first decided session to 2023-06-07 23:45)

- BTCUSDT: deciding bars 2020-02-05 00:15 to 2023-06-06 23:45, 103659 eligible bars, all-bar baseline mean R -0.256; readings: atr15 store, atr1h store, bias_ema50_1h_px store, sw_hi_15m store.
- ETHUSDT: deciding bars 2020-02-05 00:15 to 2023-06-06 23:45, 108461 eligible bars, all-bar baseline mean R -0.182; readings: atr15 store, atr1h store, bias_ema50_1h_px store, sw_hi_15m store.

| Candidate | Trades | Won | Mean R [95%] | Sum R | Excess over baseline [95%] | p (excess>0) | BTC excess (n) | ETH excess (n) |
|---|---|---|---|---|---|---|---|---|
| O1-R1-C0 | 780 | 49% | -0.124 [-0.196, -0.046] | -97.1 | +0.130 [+0.054, +0.206] | 0.0012 | +0.120 (387) | +0.139 (393) |
| O1-R1-C1 | 569 | 48% | -0.162 [-0.241, -0.076] | -92.1 | +0.092 [+0.011, +0.177] | 0.0162 | +0.046 (286) | +0.140 (283) |
| O1-R2-C0 | 1273 | 46% | -0.221 [-0.276, -0.159] | -281.9 | +0.035 [-0.020, +0.093] | 0.1196 | +0.029 (650) | +0.040 (623) |
| O1-R2-C1 | 601 | 46% | -0.247 [-0.327, -0.158] | -148.7 | +0.010 [-0.076, +0.098] | 0.3957 | -0.011 (301) | +0.031 (300) |
| O1-R3-C0 | 378 | 46% | -0.171 [-0.265, -0.064] | -64.5 | +0.088 [-0.012, +0.201] | 0.0604 | +0.123 (189) | +0.053 (189) |
| O1-R3-C1 | 292 | 46% | -0.167 [-0.278, -0.042] | -48.7 | +0.091 [-0.026, +0.222] | 0.0862 | +0.102 (146) | +0.080 (146) |
| O2-R1-C0 | 531 | 51% | -0.053 [-0.147, +0.055] | -27.9 | +0.160 [+0.081, +0.252] | 0.0006 | +0.162 (204) | +0.160 (327) |
| O2-R1-C1 | 369 | 52% | -0.051 [-0.146, +0.046] | -18.7 | +0.144 [+0.063, +0.227] | 0.0008 | +0.134 (140) | +0.149 (229) |
| O2-R2-C0 | 801 | 48% | -0.122 [-0.188, -0.048] | -97.9 | +0.091 [+0.029, +0.160] | 0.0048 | +0.098 (305) | +0.088 (496) |
| O2-R2-C1 | 390 | 50% | -0.086 [-0.178, +0.019] | -33.4 | +0.106 [+0.013, +0.213] | 0.0266 | +0.142 (141) | +0.085 (249) |
| O2-R3-C0 | 309 | 48% | -0.090 [-0.194, +0.024] | -28.0 | +0.116 [+0.015, +0.224] | 0.0192 | +0.127 (118) | +0.108 (191) |
| O2-R3-C1 | 240 | 50% | -0.056 [-0.174, +0.076] | -13.4 | +0.138 [+0.023, +0.268] | 0.0196 | +0.076 (91) | +0.176 (149) |
| O3-R1-C0 | 774 | 50% | -0.113 [-0.175, -0.050] | -87.2 | +0.139 [+0.067, +0.209] | 0.0002 | +0.081 (385) | +0.196 (389) |
| O3-R1-C1 | 593 | 49% | -0.151 [-0.218, -0.087] | -89.3 | +0.100 [+0.023, +0.175] | 0.0032 | +0.032 (291) | +0.166 (302) |
| O3-R2-C0 | 1253 | 47% | -0.208 [-0.259, -0.151] | -260.5 | +0.049 [-0.005, +0.104] | 0.0430 | +0.024 (625) | +0.073 (628) |
| O3-R2-C1 | 723 | 47% | -0.248 [-0.319, -0.171] | -179.2 | +0.008 [-0.071, +0.085] | 0.4129 | -0.034 (360) | +0.050 (363) |
| O3-R3-C0 | 510 | 46% | -0.175 [-0.259, -0.085] | -89.3 | +0.079 [-0.014, +0.179] | 0.0576 | +0.028 (256) | +0.132 (254) |
| O3-R3-C1 | 424 | 46% | -0.181 [-0.285, -0.074] | -76.8 | +0.074 [-0.042, +0.192] | 0.1076 | +0.006 (215) | +0.144 (209) |

Qualified by the Stage 1 rule: none. Selected: none.
- skipped events O1-R1-C0: BTCUSDT {'events': 960, 'while_open': 553, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 1, 'stop_over_8pct': 19, 'no_reading': 0}; ETHUSDT {'events': 941, 'while_open': 517, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 31, 'no_reading': 0}
- skipped events O1-R1-C1: BTCUSDT {'events': 645, 'while_open': 350, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 1, 'stop_over_8pct': 8, 'no_reading': 0}; ETHUSDT {'events': 623, 'while_open': 332, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 8, 'no_reading': 0}
- skipped events O1-R2-C0: BTCUSDT {'events': 1323, 'while_open': 664, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 1, 'stop_over_8pct': 8, 'no_reading': 0}; ETHUSDT {'events': 1228, 'while_open': 586, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 1, 'stop_over_8pct': 18, 'no_reading': 0}
- skipped events O1-R2-C1: BTCUSDT {'events': 531, 'while_open': 229, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 1, 'stop_over_8pct': 0, 'no_reading': 0}; ETHUSDT {'events': 501, 'while_open': 199, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 1, 'stop_over_8pct': 1, 'no_reading': 0}
- skipped events O1-R3-C0: BTCUSDT {'events': 291, 'while_open': 94, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 8, 'no_reading': 0}; ETHUSDT {'events': 312, 'while_open': 105, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 18, 'no_reading': 0}
- skipped events O1-R3-C1: BTCUSDT {'events': 215, 'while_open': 67, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 2, 'no_reading': 0}; ETHUSDT {'events': 229, 'while_open': 74, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 9, 'no_reading': 0}
- skipped events O2-R1-C0: BTCUSDT {'events': 552, 'while_open': 326, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 22, 'no_reading': 0}; ETHUSDT {'events': 887, 'while_open': 517, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 43, 'no_reading': 0}
- skipped events O2-R1-C1: BTCUSDT {'events': 337, 'while_open': 189, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 8, 'no_reading': 0}; ETHUSDT {'events': 564, 'while_open': 321, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 14, 'no_reading': 0}
- skipped events O2-R2-C0: BTCUSDT {'events': 695, 'while_open': 379, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 11, 'no_reading': 0}; ETHUSDT {'events': 1071, 'while_open': 554, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 21, 'no_reading': 0}
- skipped events O2-R2-C1: BTCUSDT {'events': 270, 'while_open': 129, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 0, 'no_reading': 0}; ETHUSDT {'events': 467, 'while_open': 217, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 1, 'no_reading': 0}
- skipped events O2-R3-C0: BTCUSDT {'events': 222, 'while_open': 88, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 16, 'no_reading': 0}; ETHUSDT {'events': 354, 'while_open': 132, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 31, 'no_reading': 0}
- skipped events O2-R3-C1: BTCUSDT {'events': 156, 'while_open': 63, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 2, 'no_reading': 0}; ETHUSDT {'events': 251, 'while_open': 92, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 10, 'no_reading': 0}
- skipped events O3-R1-C0: BTCUSDT {'events': 1280, 'while_open': 873, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 2, 'stop_over_8pct': 20, 'no_reading': 0}; ETHUSDT {'events': 1274, 'while_open': 853, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 32, 'no_reading': 0}
- skipped events O3-R1-C1: BTCUSDT {'events': 916, 'while_open': 615, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 2, 'stop_over_8pct': 8, 'no_reading': 0}; ETHUSDT {'events': 909, 'while_open': 600, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 7, 'no_reading': 0}
- skipped events O3-R2-C0: BTCUSDT {'events': 1568, 'while_open': 931, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 3, 'stop_over_8pct': 9, 'no_reading': 0}; ETHUSDT {'events': 1480, 'while_open': 833, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 19, 'no_reading': 0}
- skipped events O3-R2-C1: BTCUSDT {'events': 773, 'while_open': 408, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 5, 'stop_over_8pct': 0, 'no_reading': 0}; ETHUSDT {'events': 749, 'while_open': 385, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 1, 'no_reading': 0}
- skipped events O3-R3-C0: BTCUSDT {'events': 470, 'while_open': 203, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 11, 'no_reading': 0}; ETHUSDT {'events': 517, 'while_open': 235, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 28, 'no_reading': 0}
- skipped events O3-R3-C1: BTCUSDT {'events': 376, 'while_open': 158, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 3, 'no_reading': 0}; ETHUSDT {'events': 397, 'while_open': 177, 'entry_at_or_below_stop': 0, 'stop_under_0.3pct': 0, 'stop_over_8pct': 11, 'no_reading': 0}

## Stage 2 (first decided session to )

Not run: nothing to confirm (Stage 1 selected none).

