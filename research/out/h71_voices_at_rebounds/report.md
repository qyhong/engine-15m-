# H71 report: the engine's own odds, voices and readings in BTC/ETH oversold states

Written by `research/h71_report.py` from the stage files computed by `research/h71_voices_at_rebounds.py` (registered in `research/HYPOTHESES.md`, H71). IC = Spearman rank correlation with the forward log return; partial = after removing trailing 1h/4h/24h/7d returns and 24h volatility; intervals are month-clustered bootstrap 95% (4,000 draws, seed 20261122).

## Discovery (2023-06-07 23:45)

Walk: 0 refits, 174 from the cache; EMA gap source {'BTCUSDT': 'stored', 'ETHUSDT': 'stored'}.

- BTC: 116871 bars 2020-02-05 00:00 to 2023-06-07 23:45; states {'calm': 94848, 'overbought': 12588, 'oversold': 9435}; oversold months 41; sharp-rebound base rate oversold 10.0%, calm 6.5%
- ETH: 116871 bars 2020-02-05 00:00 to 2023-06-07 23:45; states {'calm': 88421, 'overbought': 16781, 'oversold': 11669}; oversold months 41; sharp-rebound base rate oversold 17.8%, calm 11.4%

### Oversold state

| Reading | 24h partial BTC | 24h partial ETH | 24h partial pooled [95%] | 24h raw pooled | 4h partial pooled | 4h raw pooled |
|---|---|---|---|---|---|---|
| `lead` | +0.143 | +0.108 | +0.120 [+0.059, +0.174] | +0.041 [-0.024, +0.101] | +0.064 [+0.024, +0.097] | +0.007 [-0.037, +0.050] |
| `v_meanrev` | +0.076 | +0.037 | +0.051 [-0.025, +0.131] | +0.042 [-0.029, +0.113] | +0.071 [+0.036, +0.110] | +0.030 [-0.018, +0.082] |
| `v_pullback` | -0.001 | -0.004 | -0.003 [-0.071, +0.071] | +0.007 [-0.058, +0.074] | +0.032 [-0.007, +0.068] | +0.013 [-0.024, +0.053] |
| `v_momentum` | +0.055 | -0.006 | +0.016 [-0.076, +0.092] | -0.035 [-0.110, +0.034] | +0.028 [-0.016, +0.074] | -0.031 [-0.084, +0.026] |
| `v_structure` | +0.066 | +0.006 | +0.026 [-0.042, +0.103] | +0.035 [-0.028, +0.100] | +0.078 [+0.027, +0.130] | +0.061 [+0.011, +0.116] |
| `v_regime` | -0.124 | -0.048 | -0.074 [-0.146, +0.004] | -0.117 [-0.189, -0.035] | -0.063 [-0.114, -0.013] | -0.084 [-0.135, -0.033] |
| `v_levels` | +0.034 | +0.009 | +0.017 [-0.045, +0.083] | +0.002 [-0.053, +0.060] | +0.016 [-0.027, +0.059] | -0.011 [-0.050, +0.030] |
| `v_flow` | +0.070 | -0.019 | +0.013 [-0.039, +0.058] | -0.024 [-0.069, +0.017] | -0.007 [-0.039, +0.029] | -0.056 [-0.103, -0.005] |
| `k_1h` | +0.056 | +0.026 | +0.036 [-0.025, +0.099] | +0.035 [-0.023, +0.098] | +0.047 [+0.006, +0.088] | +0.019 [-0.021, +0.061] |
| `stretch_4h` | +0.125 | +0.048 | +0.075 [-0.047, +0.172] | -0.038 [-0.153, +0.047] | +0.042 [-0.034, +0.108] | -0.003 [-0.064, +0.047] |
| `cvd_div` | +0.005 | -0.053 | -0.034 [-0.081, +0.022] | -0.022 [-0.066, +0.031] | -0.031 [-0.075, +0.020] | -0.012 [-0.051, +0.034] |
| `fund_z` | -0.145 | -0.060 | -0.088 [-0.169, -0.018] | -0.125 [-0.200, -0.061] | -0.026 [-0.064, +0.011] | -0.040 [-0.082, -0.001] |

Selection checks (same sign BTC/ETH; pooled interval excludes 0; |pooled| >= 0.02):

- `lead`: {'same_sign_btc_eth': True, 'pooled_interval_excludes_zero': True, 'abs_pooled_at_least_0.02': True, 'qualifies': True}
- `v_meanrev`: {'same_sign_btc_eth': True, 'pooled_interval_excludes_zero': False, 'abs_pooled_at_least_0.02': True, 'qualifies': False}
- `v_pullback`: {'same_sign_btc_eth': True, 'pooled_interval_excludes_zero': False, 'abs_pooled_at_least_0.02': False, 'qualifies': False}
- `v_momentum`: {'same_sign_btc_eth': False, 'pooled_interval_excludes_zero': False, 'abs_pooled_at_least_0.02': False, 'qualifies': False}
- `v_structure`: {'same_sign_btc_eth': True, 'pooled_interval_excludes_zero': False, 'abs_pooled_at_least_0.02': True, 'qualifies': False}
- `v_regime`: {'same_sign_btc_eth': True, 'pooled_interval_excludes_zero': False, 'abs_pooled_at_least_0.02': True, 'qualifies': False}
- `v_levels`: {'same_sign_btc_eth': True, 'pooled_interval_excludes_zero': False, 'abs_pooled_at_least_0.02': False, 'qualifies': False}
- `v_flow`: {'same_sign_btc_eth': False, 'pooled_interval_excludes_zero': False, 'abs_pooled_at_least_0.02': False, 'qualifies': False}
- `k_1h`: {'same_sign_btc_eth': True, 'pooled_interval_excludes_zero': False, 'abs_pooled_at_least_0.02': True, 'qualifies': False}
- `stretch_4h`: {'same_sign_btc_eth': True, 'pooled_interval_excludes_zero': False, 'abs_pooled_at_least_0.02': True, 'qualifies': False}
- `cvd_div`: {'same_sign_btc_eth': False, 'pooled_interval_excludes_zero': False, 'abs_pooled_at_least_0.02': True, 'qualifies': False}
- `fund_z`: {'same_sign_btc_eth': True, 'pooled_interval_excludes_zero': True, 'abs_pooled_at_least_0.02': True, 'qualifies': True}

Qualified: ['lead', 'fund_z']

### Sharp-rebound hit rates (oversold, descriptive)

| Reading | BTC base / top third / bottom third (%) | ETH base / top / bottom (%) |
|---|---|---|
| `lead` | 10.0 / 9.3 / 12.8 | 17.8 / 18.5 / 20.5 |
| `v_meanrev` | 10.0 / 11.8 / 9.0 | 17.8 / 19.4 / 15.4 |
| `v_pullback` | 10.0 / 11.0 / 8.4 | 17.8 / 16.9 / 17.6 |
| `v_momentum` | 10.0 / 8.8 / 11.3 | 17.8 / 17.4 / 18.4 |
| `v_structure` | 10.0 / 9.9 / 8.4 | 17.8 / 19.8 / 18.8 |
| `v_regime` | 10.0 / 5.9 / 17.6 | 17.8 / 19.1 / 23.9 |
| `v_levels` | 10.0 / 8.6 / 13.5 | 17.8 / 16.7 / 20.2 |
| `v_flow` | 10.0 / 8.8 / 13.3 | 17.8 / 17.2 / 20.3 |
| `k_1h` | 10.0 / 11.2 / 7.9 | 17.8 / 19.2 / 17.3 |
| `stretch_4h` | 10.0 / 6.3 / 13.7 | 17.8 / 19.1 / 22.8 |
| `cvd_div` | 10.0 / 9.3 / 11.5 | 17.8 / 16.8 / 17.6 |
| `fund_z` | 10.0 / 5.9 / 14.1 | 17.8 / 9.3 / 22.2 |

### Calm state (contrast)

| Reading | 24h partial BTC | 24h partial ETH | 24h partial pooled [95%] | 24h raw pooled | 4h partial pooled | 4h raw pooled |
|---|---|---|---|---|---|---|
| `lead` | -0.032 | -0.054 | -0.042 [-0.080, -0.005] | -0.048 [-0.080, -0.019] | -0.004 [-0.022, +0.012] | -0.024 [-0.043, -0.008] |
| `v_meanrev` | -0.013 | -0.022 | -0.017 [-0.047, +0.009] | -0.019 [-0.046, +0.007] | -0.003 [-0.025, +0.017] | -0.019 [-0.041, +0.003] |
| `v_pullback` | -0.031 | -0.033 | -0.032 [-0.058, -0.005] | -0.038 [-0.062, -0.011] | -0.005 [-0.027, +0.016] | -0.023 [-0.044, -0.002] |
| `v_momentum` | -0.028 | -0.042 | -0.034 [-0.062, -0.004] | -0.030 [-0.063, +0.002] | -0.007 [-0.021, +0.009] | -0.030 [-0.048, -0.011] |
| `v_structure` | -0.022 | -0.020 | -0.021 [-0.051, +0.009] | -0.035 [-0.064, -0.007] | +0.015 [-0.008, +0.036] | -0.006 [-0.028, +0.013] |
| `v_regime` | -0.019 | +0.000 | -0.010 [-0.054, +0.037] | -0.009 [-0.054, +0.037] | +0.002 [-0.013, +0.019] | +0.003 [-0.013, +0.019] |
| `v_levels` | +0.024 | +0.015 | +0.020 [-0.025, +0.062] | -0.009 [-0.054, +0.032] | +0.015 [-0.004, +0.034] | -0.012 [-0.031, +0.006] |
| `v_flow` | -0.034 | -0.037 | -0.036 [-0.060, -0.010] | -0.044 [-0.068, -0.020] | -0.007 [-0.019, +0.007] | -0.040 [-0.057, -0.022] |
| `k_1h` | +0.009 | -0.007 | +0.002 [-0.023, +0.027] | -0.007 [-0.033, +0.019] | +0.005 [-0.017, +0.027] | -0.016 [-0.038, +0.005] |
| `stretch_4h` | +0.002 | -0.004 | -0.001 [-0.037, +0.037] | +0.001 [-0.043, +0.041] | +0.008 [-0.009, +0.024] | +0.004 [-0.015, +0.021] |
| `cvd_div` | -0.013 | -0.003 | -0.009 [-0.028, +0.011] | -0.012 [-0.032, +0.007] | -0.004 [-0.017, +0.010] | -0.001 [-0.013, +0.013] |
| `fund_z` | -0.059 | -0.058 | -0.059 [-0.101, -0.015] | -0.051 [-0.092, -0.012] | -0.024 [-0.042, -0.004] | -0.017 [-0.036, +0.002] |

### Descriptive read-out: the combined odds in the oversold state

| Bias | Lead bucket | bars | share of state | months | mean fwd 24h % | median fwd 24h % | rebound +5% rate |
|---|---|---|---|---|---|---|---|
| all | all | 21104 | 100.0% | 41 | +0.38 | +0.46 | 14.3% |
| all | up 5+ | 28 | 0.1% | 3 | +3.56 | +2.01 | 42.9% |
| all | up 15+ | 0 | | | | | |
| all | between | 8062 | 38.2% | 41 | +0.71 | +0.55 | 14.3% |
| all | down 5+ | 13014 | 61.7% | 41 | +0.17 | +0.37 | 14.3% |
| bias down | all | 7909 | 100.0% | 20 | +0.55 | +0.56 | 17.3% |
| bias down | up 5+ | 8 | 0.1% | 1 | +9.40 | +9.90 | 100.0% |
| bias down | up 15+ | 0 | | | | | |
| bias down | between | 2152 | 27.2% | 17 | +0.92 | +0.41 | 18.6% |
| bias down | down 5+ | 5749 | 72.7% | 20 | +0.40 | +0.62 | 16.7% |
| bias not down | all | 13195 | 100.0% | 41 | +0.28 | +0.41 | 12.5% |
| bias not down | up 5+ | 20 | 0.2% | 3 | +1.23 | -0.11 | 20.0% |
| bias not down | up 15+ | 0 | | | | | |
| bias not down | between | 5910 | 44.8% | 40 | +0.63 | +0.60 | 12.7% |
| bias not down | down 5+ | 7265 | 55.1% | 41 | -0.01 | +0.21 | 12.4% |

## Selection

```
{
 "written_utc": "2026-11-22 11:28:20",
 "selected": [
  {
   "reading": "lead",
   "sign": 1.0,
   "pooled_partial_ic": 0.12006286861379156
  },
  {
   "reading": "fund_z",
   "sign": -1.0,
   "pooled_partial_ic": -0.08832149497106935
  }
 ],
 "nothing_to_confirm": false
}
```

## Confirmation

Cut 2025-11-10 23:45.
- BTC: 85152 bars 2023-06-08 00:00 to 2025-11-10 23:45; states {'calm': 70709, 'overbought': 9119, 'oversold': 5324}; oversold months 30; sharp-rebound base rate oversold 5.8%, calm 2.9%
- ETH: 85152 bars 2023-06-08 00:00 to 2025-11-10 23:45; states {'calm': 69545, 'overbought': 9178, 'oversold': 6429}; oversold months 30; sharp-rebound base rate oversold 9.2%, calm 5.4%

| Reading | 24h partial BTC | 24h partial ETH | 24h partial pooled [95%] | 24h raw pooled | 4h partial pooled | 4h raw pooled |
|---|---|---|---|---|---|---|
| `lead` | +0.064 | +0.071 | +0.068 [-0.120, +0.222] | +0.024 [-0.157, +0.176] | +0.005 [-0.062, +0.084] | +0.024 [-0.036, +0.090] |
| `fund_z` | -0.085 | -0.071 | -0.076 [-0.154, +0.021] | -0.155 [-0.237, -0.056] | +0.016 [-0.037, +0.076] | -0.035 [-0.090, +0.030] |

- `lead`: {'sign': 1.0, 'one_sided_p': 0.20944763809047737, 'threshold': 0.025, 'passed': False}
- `fund_z`: {'sign': -1.0, 'one_sided_p': 0.02649337665583604, 'threshold': 0.025, 'passed': False}

| Reading | BTC base / top third / bottom third (%) | ETH base / top / bottom (%) |
|---|---|---|
| `lead` | 5.8 / 3.8 / 8.5 | 9.2 / 8.2 / 11.7 |
| `fund_z` | 5.8 / 6.3 / 5.1 | 9.2 / 4.5 / 16.7 |

### Descriptive read-out (confirmation period)

| Bias | Lead bucket | bars | share of state | months | mean fwd 24h % | median fwd 24h % | rebound +5% rate |
|---|---|---|---|---|---|---|---|
| all | all | 11753 | 100.0% | 30 | +0.11 | +0.31 | 7.7% |
| all | up 5+ | 27 | 0.2% | 2 | +1.37 | +1.46 | 3.7% |
| all | up 15+ | 0 | | | | | |
| all | between | 5535 | 47.1% | 30 | +0.17 | +0.29 | 7.0% |
| all | down 5+ | 6191 | 52.7% | 30 | +0.04 | +0.32 | 8.3% |
| bias down | all | 3256 | 100.0% | 14 | +0.75 | +0.81 | 13.1% |
| bias down | up 5+ | 0 | | | | | |
| bias down | up 15+ | 0 | | | | | |
| bias down | between | 1426 | 43.8% | 13 | +0.32 | +0.57 | 12.1% |
| bias down | down 5+ | 1830 | 56.2% | 13 | +1.08 | +1.12 | 14.0% |
| bias not down | all | 8497 | 100.0% | 30 | -0.14 | +0.16 | 5.6% |
| bias not down | up 5+ | 27 | 0.3% | 2 | +1.37 | +1.46 | 3.7% |
| bias not down | up 15+ | 0 | | | | | |
| bias not down | between | 4109 | 48.4% | 30 | +0.12 | +0.22 | 5.2% |
| bias not down | down 5+ | 4361 | 51.3% | 30 | -0.39 | +0.04 | 5.9% |

## Holdout

Not opened: nothing to carry from the previous stage.
