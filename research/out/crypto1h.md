# Crypto 1h study: can the 1h mind's next-hour call pay its costs? (IN-SAMPLE, not proof)

Written by `research/crypto1h_study.py` on 2026-11-11 10:01 UTC. BTCUSDT and ETHUSDT, 2020-01-01 00:00 to 2026-11-11 09:00 UTC, halves split at 2023-06-07 04:30. Costs 0.10% a side (0.20% round trip). Paper only: history can reject an idea, never prove one.

Every call is a trade entered at the next 15m open, one at a time per coin, none in the hour before a high-impact US release. R = the stop distance at entry. Hit = direction right on calls whose 1h triple-barrier grade was up or down (the 1h mind's own yardstick); win = trade positive after costs.

## Verdict

The first-half choice `m0_mix|top2|sqrel|wide 3.0R 16b` cleared costs in the first half (worse coin +0.066 R after costs) and in the untouched second half made -0.229 R (BTC, 254 trades) and -0.137 R (ETH, 280 trades) after costs. **It does not clear costs in both halves.** Luck: 5760 variants tried; 0 clear costs in both halves on both coins after the fact, against 0.0 on average (max 0) when the signals are slid in time.

Read plainly:

- **Selectivity does lift the hit rate, a little, in both halves.** The 1h mind on every call: 55.4 / 53.9 % (BTC) and 55.5 / 55.0 % (ETH). `m1_pooled|top10|none|bar 1.0R 4b`: 61.3 / 57.6 % and 60.1 / 59.4 % on 2,900-5,600 trades a half per coin. That is close to the 60% asked for on ETH. But it does not turn into money: R before costs on those trades is +0.064 / +0.029 (BTC) and +0.041 / +0.024 (ETH), because the read is about which way SMALL moves go; a large share of calls never reach a barrier inside the hour.
- **The cost wall.** On the 1-barrier stop (0.75 x ATR 1h) the round trip costs 0.34 / 0.51 R on BTC and 0.26 / 0.37 R on ETH (first / second half: BTC's hourly range shrank after 2023, so the same 0.20% is a bigger share of it). A 2-barrier stop halves that (0.17 / 0.25 and 0.13 / 0.19 R), but the edge does not grow with the stop, so R before costs shrinks as fast. Bigger targets (2-3R) and longer clocks (8-16 bars) raise R before costs to at most about +0.1-0.35 R on the selected calls, still short of costs in the second half.
- **The first-half pick was not luck in the first half, and still failed.** Its first-half worse-coin +0.066 R beat every one of 30 slid-signal placebos (best -0.022 R), so the selection found something real in 2020-2023; in the untouched second half it lost (-0.229 R BTC, -0.137 R ETH after costs).
- **High hit rates on a few hundred trades are not evidence.** The best first-half worse-coin hit rate among the 5760 variants is 65.6 %; with the signals slid in time the best is 58.5 % on average (max 65.82 %).
- **Better inputs and other models did not help on direction overall:** on every graded call the pooled logistic, the selected fast readings (order flow, trend quality, VWAP, ribbon, Hull, KAMA, the other coin, interactions) and the blend are within about 1 point of the 1h mind in both halves; the extra first-half points of the selected model (m2) are gone in the second.

So no hypothesis entry and no shadow challenger are drafted from this study (the rule set before it: only something that clears costs in both halves with >= 200 trades per half per coin).

## The models on every graded call (no selection): direction hit %, 1st / 2nd half

| Model | BTC | ETH |
|---|---|---|
| m0_mix | 55.33 / 54.18 | 55.43 / 55.24 |
| m1_pooled | 55.11 / 54.19 | 55.30 / 55.26 |
| m2_select | 55.94 / 54.14 | 56.21 / 55.23 |
| m3_blend | 55.99 / 54.30 | 56.36 / 55.44 |

m1 ridge 1000.0; m2: K = 32 readings of 172 candidates, ridge 1000.0 (chosen by first-half inner validation; 28 model settings tried).

m2's readings at its last refit (2026-10-26): rb_pos_15m, id_day_pos, tr_15m, tq_di_15m, tq_rsi_15m, kama_pos_15m, id_band, hull_dir_15m, rb_order_15m, rb_gmma_15m, kama_er_15m, rangepos, x_tr_15m, id_vwap_d, kama_slope_15m, ms_pos_1h, rb_width_15m, stretch_1h, id_or, hull_dir_1h, rb_pos_1h, mom_4h, hull_pos_1h, ma_share_1h, ma_cross_1h, brd_above_24h, tq_st_15m, kama_pos_1h, tq_rsi_1h, sr_break, sr_pd_pos, kama_er_1h.

## Selectivity: does picking the surest calls lift the hit rate? (1-barrier stop and target, 4 bars, no filter)

| Variant | BTC 1st: trades / hit % / R gross / R net | BTC 2nd | ETH 1st | ETH 2nd |
|---|---|---|---|---|
| `m0_mix|all|none|bar 1.0R 4b` | 34252 / 55.4 / +0.008 / -0.330 | 36767 / 53.9 / +0.001 / -0.509 | 34263 / 55.5 / +0.008 / -0.252 | 36354 / 55.0 / +0.006 / -0.365 |
| `m0_mix|top10|none|bar 1.0R 4b` | 5389 / 56.9 / +0.024 / -0.290 | 5578 / 54.0 / -0.006 / -0.443 | 5386 / 58.0 / +0.035 / -0.203 | 5642 / 56.2 / +0.018 / -0.302 |
| `m0_mix|top5|none|bar 1.0R 4b` | 3054 / 57.8 / +0.045 / -0.259 | 3109 / 53.8 / -0.008 / -0.425 | 3005 / 57.2 / +0.033 / -0.200 | 3180 / 55.3 / +0.016 / -0.287 |
| `m0_mix|top2|none|bar 1.0R 4b` | 1445 / 56.8 / +0.051 / -0.247 | 1505 / 52.8 / -0.014 / -0.413 | 1494 / 55.9 / +0.024 / -0.198 | 1512 / 54.1 / +0.009 / -0.276 |
| `m1_pooled|all|none|bar 1.0R 4b` | 35050 / 55.0 / +0.010 / -0.329 | 36767 / 53.8 / +0.004 / -0.506 | 35074 / 55.2 / +0.010 / -0.248 | 36354 / 55.1 / +0.011 / -0.360 |
| `m1_pooled|top10|none|bar 1.0R 4b` | 5353 / 61.3 / +0.064 / -0.271 | 5414 / 57.6 / +0.029 / -0.462 | 5323 / 60.1 / +0.041 / -0.212 | 5394 / 59.4 / +0.024 / -0.337 |
| `m1_pooled|top5|none|bar 1.0R 4b` | 3037 / 59.9 / +0.055 / -0.281 | 2885 / 58.0 / +0.033 / -0.448 | 2975 / 60.1 / +0.041 / -0.209 | 2965 / 58.4 / +0.018 / -0.338 |
| `m1_pooled|top2|none|bar 1.0R 4b` | 1431 / 59.5 / +0.060 / -0.273 | 1321 / 56.2 / +0.019 / -0.453 | 1363 / 59.6 / +0.035 / -0.213 | 1360 / 59.5 / +0.028 / -0.316 |
| `m2_select|all|none|bar 1.0R 4b` | 35050 / 56.4 / +0.014 / -0.325 | 36767 / 54.0 / +0.004 / -0.507 | 35074 / 56.3 / +0.016 / -0.242 | 36354 / 54.8 / +0.006 / -0.365 |
| `m2_select|top10|none|bar 1.0R 4b` | 5394 / 57.6 / +0.005 / -0.346 | 5520 / 57.2 / +0.012 / -0.522 | 5380 / 61.2 / +0.041 / -0.221 | 5553 / 59.6 / +0.021 / -0.360 |
| `m2_select|top5|none|bar 1.0R 4b` | 2939 / 58.4 / +0.015 / -0.337 | 2990 / 57.6 / +0.013 / -0.533 | 2981 / 61.3 / +0.037 / -0.228 | 3009 / 60.1 / +0.020 / -0.365 |
| `m2_select|top2|none|bar 1.0R 4b` | 1361 / 56.7 / -0.005 / -0.361 | 1345 / 54.8 / -0.018 / -0.578 | 1366 / 61.0 / +0.040 / -0.225 | 1329 / 60.4 / +0.008 / -0.384 |
| `m3_blend|all|none|bar 1.0R 4b` | 33966 / 56.4 / +0.011 / -0.327 | 36767 / 54.1 / +0.003 / -0.508 | 33980 / 56.3 / +0.012 / -0.248 | 36354 / 55.0 / +0.007 / -0.364 |
| `m3_blend|top10|none|bar 1.0R 4b` | 5231 / 58.8 / +0.033 / -0.300 | 5691 / 55.0 / -0.002 / -0.483 | 5226 / 59.8 / +0.045 / -0.206 | 5690 / 56.4 / +0.009 / -0.336 |
| `m3_blend|top5|none|bar 1.0R 4b` | 2954 / 57.4 / +0.031 / -0.297 | 3105 / 54.7 / -0.003 / -0.471 | 2924 / 58.8 / +0.043 / -0.203 | 3168 / 56.2 / +0.016 / -0.318 |
| `m3_blend|top2|none|bar 1.0R 4b` | 1369 / 55.7 / +0.015 / -0.301 | 1461 / 53.2 / -0.021 / -0.475 | 1316 / 58.6 / +0.044 / -0.194 | 1516 / 55.2 / +0.015 / -0.309 |

## Filters on the top 10% of the 1h mind (m0), same payoff

| Variant | BTC 1st: trades / hit % / R gross / R net | BTC 2nd | ETH 1st | ETH 2nd |
|---|---|---|---|---|
| `m0_mix|top10|none|bar 1.0R 4b` | 5389 / 56.9 / +0.024 / -0.290 | 5578 / 54.0 / -0.006 / -0.443 | 5386 / 58.0 / +0.035 / -0.203 | 5642 / 56.2 / +0.018 / -0.302 |
| `m0_mix|top10|agree|bar 1.0R 4b` | 5124 / 57.0 / +0.026 / -0.290 | 5241 / 53.7 / -0.009 / -0.439 | 5162 / 58.1 / +0.035 / -0.203 | 5224 / 56.1 / +0.017 / -0.294 |
| `m0_mix|top10|volband|bar 1.0R 4b` | 2798 / 57.4 / +0.013 / -0.290 | 3069 / 54.1 / -0.029 / -0.461 | 2839 / 58.8 / +0.027 / -0.203 | 3111 / 57.8 / +0.025 / -0.295 |
| `m0_mix|top10|overlap|bar 1.0R 4b` | 1109 / 57.0 / +0.058 / -0.261 | 1229 / 53.4 / +0.022 / -0.434 | 1100 / 56.8 / +0.054 / -0.190 | 1159 / 57.4 / +0.065 / -0.271 |
| `m0_mix|top10|active|bar 1.0R 4b` | 3396 / 56.2 / +0.027 / -0.290 | 3700 / 54.1 / +0.003 / -0.431 | 3405 / 57.7 / +0.041 / -0.199 | 3699 / 56.4 / +0.030 / -0.293 |
| `m0_mix|top10|htf|bar 1.0R 4b` | 1089 / 51.6 / -0.022 / -0.316 | 1354 / 53.2 / +0.015 / -0.363 | 956 / 54.5 / +0.014 / -0.206 | 1487 / 55.0 / +0.028 / -0.263 |
| `m0_mix|top10|tide4h|bar 1.0R 4b` | 2968 / 56.0 / +0.023 / -0.299 | 3409 / 52.5 / -0.015 / -0.434 | 2812 / 57.2 / +0.044 / -0.194 | 3641 / 56.4 / +0.033 / -0.279 |
| `m0_mix|top10|surge|bar 1.0R 4b` | 2091 / 54.9 / +0.026 / -0.258 | 2351 / 53.1 / -0.004 / -0.396 | 2220 / 57.4 / +0.049 / -0.174 | 2449 / 54.5 / +0.013 / -0.280 |
| `m0_mix|top10|sqrel|bar 1.0R 4b` | 2018 / 56.4 / +0.024 / -0.316 | 1558 / 53.5 / -0.016 / -0.457 | 1821 / 57.8 / +0.030 / -0.224 | 1775 / 57.4 / +0.034 / -0.301 |
| `m0_mix|top10|flow|bar 1.0R 4b` | 4782 / 57.0 / +0.027 / -0.287 | 4876 / 53.4 / -0.011 / -0.449 | 4664 / 58.4 / +0.043 / -0.196 | 4892 / 55.5 / +0.011 / -0.312 |

## Payoff: the 1h mind's top 10%, no filter, every stop / target / clock

| Variant | BTC 1st: trades / hit % / R gross / R net | BTC 2nd | ETH 1st | ETH 2nd |
|---|---|---|---|---|
| `m0_mix|top10|none|bar 1.0R 4b` | 5389 / 56.9 / +0.024 / -0.290 | 5578 / 54.0 / -0.006 / -0.443 | 5386 / 58.0 / +0.035 / -0.203 | 5642 / 56.2 / +0.018 / -0.302 |
| `m0_mix|top10|none|bar 1.0R 8b` | 4633 / 56.3 / +0.027 / -0.291 | 4821 / 53.5 / -0.005 / -0.445 | 4616 / 58.3 / +0.045 / -0.194 | 4840 / 56.2 / +0.031 / -0.294 |
| `m0_mix|top10|none|bar 1.0R 16b` | 4400 / 56.3 / +0.034 / -0.287 | 4599 / 53.3 / -0.006 / -0.449 | 4382 / 58.0 / +0.049 / -0.191 | 4592 / 55.8 / +0.033 / -0.294 |
| `m0_mix|top10|none|bar 1.5R 4b` | 4830 / 56.6 / +0.023 / -0.291 | 5012 / 53.8 / -0.004 / -0.440 | 4799 / 58.6 / +0.030 / -0.207 | 5052 / 56.4 / +0.024 / -0.296 |
| `m0_mix|top10|none|bar 1.5R 8b` | 3858 / 56.3 / +0.029 / -0.290 | 4019 / 53.7 / -0.006 / -0.450 | 3798 / 58.6 / +0.036 / -0.206 | 4067 / 55.8 / +0.038 / -0.288 |
| `m0_mix|top10|none|bar 1.5R 16b` | 3504 / 56.2 / +0.033 / -0.290 | 3668 / 53.5 / -0.008 / -0.456 | 3454 / 58.7 / +0.048 / -0.195 | 3686 / 55.3 / +0.044 / -0.287 |
| `m0_mix|top10|none|bar 2.0R 4b` | 4603 / 56.8 / +0.025 / -0.288 | 4770 / 54.1 / -0.001 / -0.437 | 4558 / 58.4 / +0.033 / -0.204 | 4777 / 56.8 / +0.022 / -0.298 |
| `m0_mix|top10|none|bar 2.0R 8b` | 3482 / 56.5 / +0.035 / -0.284 | 3658 / 54.2 / -0.003 / -0.447 | 3477 / 58.1 / +0.043 / -0.198 | 3659 / 55.7 / +0.037 / -0.292 |
| `m0_mix|top10|none|bar 2.0R 16b` | 3038 / 56.0 / +0.041 / -0.285 | 3197 / 53.7 / +0.005 / -0.445 | 2995 / 58.0 / +0.057 / -0.189 | 3169 / 55.4 / +0.044 / -0.291 |
| `m0_mix|top10|none|bar 3.0R 4b` | 4392 / 56.7 / +0.025 / -0.285 | 4544 / 54.1 / -0.007 / -0.442 | 4373 / 58.2 / +0.037 / -0.200 | 4586 / 56.4 / +0.027 / -0.292 |
| `m0_mix|top10|none|bar 3.0R 8b` | 3157 / 56.3 / +0.037 / -0.281 | 3294 / 54.0 / -0.020 / -0.465 | 3138 / 58.9 / +0.052 / -0.191 | 3290 / 56.6 / +0.049 / -0.281 |
| `m0_mix|top10|none|bar 3.0R 16b` | 2582 / 56.0 / +0.056 / -0.270 | 2705 / 53.6 / -0.015 / -0.468 | 2532 / 58.8 / +0.090 / -0.158 | 2674 / 56.4 / +0.067 / -0.273 |
| `m0_mix|top10|none|struct 1.0R 4b` | 5387 / 56.9 / +0.024 / -0.288 | 5572 / 54.0 / -0.006 / -0.440 | 5373 / 58.0 / +0.034 / -0.203 | 5630 / 56.2 / +0.018 / -0.300 |
| `m0_mix|top10|none|struct 1.0R 8b` | 4626 / 56.4 / +0.028 / -0.289 | 4808 / 53.4 / -0.006 / -0.444 | 4600 / 58.4 / +0.044 / -0.194 | 4817 / 56.2 / +0.032 / -0.292 |
| `m0_mix|top10|none|struct 1.0R 16b` | 4385 / 56.3 / +0.033 / -0.286 | 4583 / 53.1 / -0.007 / -0.447 | 4363 / 58.0 / +0.048 / -0.192 | 4561 / 55.8 / +0.035 / -0.290 |
| `m0_mix|top10|none|struct 1.5R 4b` | 4832 / 56.7 / +0.022 / -0.290 | 5001 / 54.0 / -0.005 / -0.439 | 4792 / 58.5 / +0.028 / -0.208 | 5049 / 56.4 / +0.025 / -0.293 |
| `m0_mix|top10|none|struct 1.5R 8b` | 3852 / 56.4 / +0.029 / -0.289 | 4008 / 53.8 / -0.006 / -0.447 | 3786 / 58.5 / +0.032 / -0.208 | 4060 / 55.9 / +0.041 / -0.284 |
| `m0_mix|top10|none|struct 1.5R 16b` | 3488 / 56.2 / +0.034 / -0.288 | 3642 / 53.5 / -0.009 / -0.456 | 3434 / 58.7 / +0.043 / -0.199 | 3669 / 55.3 / +0.046 / -0.283 |
| `m0_mix|top10|none|struct 2.0R 4b` | 4602 / 56.7 / +0.026 / -0.285 | 4767 / 54.2 / -0.002 / -0.435 | 4550 / 58.4 / +0.032 / -0.203 | 4777 / 56.6 / +0.022 / -0.296 |
| `m0_mix|top10|none|struct 2.0R 8b` | 3479 / 56.6 / +0.035 / -0.283 | 3653 / 54.4 / -0.005 / -0.447 | 3465 / 58.4 / +0.041 / -0.200 | 3654 / 55.6 / +0.038 / -0.288 |
| `m0_mix|top10|none|struct 2.0R 16b` | 3030 / 56.1 / +0.041 / -0.283 | 3184 / 53.9 / +0.002 / -0.447 | 2990 / 57.9 / +0.052 / -0.192 | 3143 / 55.5 / +0.042 / -0.292 |
| `m0_mix|top10|none|struct 3.0R 4b` | 4390 / 56.7 / +0.026 / -0.283 | 4544 / 54.1 / -0.008 / -0.440 | 4372 / 58.1 / +0.036 / -0.199 | 4583 / 56.4 / +0.027 / -0.290 |
| `m0_mix|top10|none|struct 3.0R 8b` | 3156 / 56.3 / +0.039 / -0.278 | 3287 / 54.2 / -0.019 / -0.462 | 3137 / 58.9 / +0.049 / -0.192 | 3286 / 56.6 / +0.051 / -0.276 |
| `m0_mix|top10|none|struct 3.0R 16b` | 2581 / 56.0 / +0.055 / -0.270 | 2689 / 53.5 / -0.013 / -0.463 | 2529 / 58.7 / +0.083 / -0.163 | 2654 / 56.6 / +0.068 / -0.270 |
| `m0_mix|top10|none|wide 1.0R 4b` | 4356 / 57.4 / +0.015 / -0.141 | 4505 / 54.1 / +0.002 / -0.216 | 4336 / 58.6 / +0.017 / -0.102 | 4511 / 57.2 / +0.015 / -0.145 |
| `m0_mix|top10|none|wide 1.0R 8b` | 3151 / 56.9 / +0.020 / -0.140 | 3252 / 54.2 / -0.001 / -0.224 | 3143 / 58.7 / +0.024 / -0.098 | 3271 / 56.1 / +0.025 / -0.141 |
| `m0_mix|top10|none|wide 1.0R 16b` | 2596 / 56.0 / +0.025 / -0.139 | 2675 / 53.4 / +0.001 / -0.227 | 2541 / 58.1 / +0.035 / -0.089 | 2643 / 55.3 / +0.032 / -0.138 |
| `m0_mix|top10|none|wide 1.5R 4b` | 4188 / 57.1 / +0.015 / -0.141 | 4316 / 54.4 / -0.004 / -0.221 | 4179 / 58.5 / +0.016 / -0.102 | 4355 / 57.0 / +0.017 / -0.143 |
| `m0_mix|top10|none|wide 1.5R 8b` | 2906 / 56.3 / +0.020 / -0.139 | 2975 / 54.0 / -0.012 / -0.235 | 2886 / 59.2 / +0.021 / -0.101 | 2997 / 57.3 / +0.031 / -0.134 |
| `m0_mix|top10|none|wide 1.5R 16b` | 2244 / 56.0 / +0.026 / -0.139 | 2285 / 53.7 / -0.010 / -0.239 | 2207 / 58.4 / +0.032 / -0.093 | 2279 / 57.2 / +0.057 / -0.115 |
| `m0_mix|top10|none|wide 2.0R 4b` | 4123 / 57.7 / +0.018 / -0.138 | 4277 / 54.2 / -0.004 / -0.220 | 4123 / 58.6 / +0.015 / -0.103 | 4307 / 57.1 / +0.018 / -0.141 |
| `m0_mix|top10|none|wide 2.0R 8b` | 2795 / 57.2 / +0.024 / -0.135 | 2879 / 54.1 / -0.011 / -0.233 | 2796 / 58.7 / +0.022 / -0.099 | 2907 / 56.9 / +0.034 / -0.131 |
| `m0_mix|top10|none|wide 2.0R 16b` | 2103 / 55.5 / +0.027 / -0.137 | 2130 / 53.6 / -0.006 / -0.234 | 2058 / 58.1 / +0.038 / -0.087 | 2127 / 57.0 / +0.063 / -0.109 |
| `m0_mix|top10|none|wide 3.0R 4b` | 4084 / 57.9 / +0.015 / -0.140 | 4246 / 54.3 / -0.007 / -0.223 | 4100 / 58.9 / +0.014 / -0.104 | 4276 / 56.8 / +0.020 / -0.140 |
| `m0_mix|top10|none|wide 3.0R 8b` | 2725 / 57.2 / +0.021 / -0.138 | 2813 / 54.1 / -0.018 / -0.239 | 2740 / 59.1 / +0.022 / -0.099 | 2844 / 56.7 / +0.035 / -0.129 |
| `m0_mix|top10|none|wide 3.0R 16b` | 1994 / 56.0 / +0.025 / -0.138 | 2015 / 53.1 / -0.004 / -0.232 | 1958 / 58.4 / +0.039 / -0.087 | 2009 / 57.1 / +0.072 / -0.100 |

## The first-half choice (rule declared before the read)

Best worse-coin average R after costs in the first half, among variants with >= 200 trades per coin: `m0_mix|top2|sqrel|wide 3.0R 16b` (first half, worse coin: +0.066 R).

| Variant | BTC 1st: trades / hit % / R gross / R net | BTC 2nd | ETH 1st | ETH 2nd |
|---|---|---|---|---|
| `m0_mix|top2|sqrel|wide 3.0R 16b` | 267 / 57.2 / +0.256 / +0.091 | 254 / 52.4 / -0.023 / -0.229 | 291 / 57.9 / +0.191 / +0.066 | 280 / 59.5 / +0.020 / -0.137 |

- BTC 1st half: 267 trades, hit 57.2%, win 44.2%, +0.256 R before costs, +0.091 R after, PF after costs 1.21, +0.0507% a trade after costs
- BTC 2nd half: 254 trades, hit 52.4%, win 35.0%, -0.023 R before costs, -0.229 R after, PF after costs 0.59, -0.2927% a trade after costs
- ETH 1st half: 291 trades, hit 57.9%, win 42.6%, +0.191 R before costs, +0.066 R after, PF after costs 1.15, -0.0346% a trade after costs
- ETH 2nd half: 280 trades, hit 59.5%, win 33.2%, +0.020 R before costs, -0.137 R after, PF after costs 0.72, -0.2075% a trade after costs

Best worse-coin first-half HIT RATE (same eligibility): `m1_pooled|top2|tide4h|wide 3.0R 16b` (65.6%).

| Variant | BTC 1st: trades / hit % / R gross / R net | BTC 2nd | ETH 1st | ETH 2nd |
|---|---|---|---|---|
| `m1_pooled|top2|tide4h|wide 3.0R 16b` | 320 / 65.7 / +0.114 / -0.068 | 294 / 52.2 / +0.062 / -0.174 | 262 / 65.6 / +0.143 / +0.012 | 251 / 65.1 / +0.259 / +0.062 |

## Top 20 variants by first-half worse-coin R after costs (>= 200 trades per coin), with their second half

| Variant | BTC 1st: trades / hit % / R gross / R net | BTC 2nd | ETH 1st | ETH 2nd |
|---|---|---|---|---|
| `m0_mix|top2|sqrel|wide 3.0R 16b` | 267 / 57.2 / +0.256 / +0.091 | 254 / 52.4 / -0.023 / -0.229 | 291 / 57.9 / +0.191 / +0.066 | 280 / 59.5 / +0.020 / -0.137 |
| `m0_mix|top2|sqrel|wide 2.0R 16b` | 277 / 57.1 / +0.222 / +0.058 | 263 / 52.3 / -0.010 / -0.218 | 303 / 57.1 / +0.158 / +0.031 | 292 / 58.6 / +0.008 / -0.149 |
| `m1_pooled|top5|overlap|wide 2.0R 16b` | 356 / 59.3 / +0.214 / +0.042 | 370 / 55.5 / +0.142 / -0.114 | 335 / 61.9 / +0.150 / +0.017 | 367 / 59.8 / +0.187 / +0.000 |
| `m1_pooled|top5|overlap|wide 3.0R 16b` | 339 / 60.2 / +0.182 / +0.011 | 353 / 55.6 / +0.179 / -0.079 | 326 / 62.4 / +0.171 / +0.037 | 356 / 61.0 / +0.206 / +0.018 |
| `m1_pooled|top5|overlap|wide 1.5R 16b` | 379 / 60.1 / +0.207 / +0.033 | 390 / 55.5 / +0.144 / -0.112 | 354 / 61.8 / +0.140 / +0.006 | 392 / 58.7 / +0.179 / -0.009 |
| `m1_pooled|top5|overlap|struct 3.0R 16b` | 423 / 59.9 / +0.353 / +0.013 | 430 / 55.6 / +0.191 / -0.307 | 390 / 61.1 / +0.272 / +0.002 | 426 / 57.8 / +0.229 / -0.136 |
| `m1_pooled|top5|overlap|bar 3.0R 16b` | 422 / 60.0 / +0.351 / +0.006 | 433 / 55.9 / +0.203 / -0.303 | 387 / 61.6 / +0.267 / -0.002 | 435 / 57.8 / +0.220 / -0.153 |
| `m0_mix|top2|surge|wide 3.0R 16b` | 415 / 52.9 / +0.170 / +0.017 | 415 / 56.0 / -0.009 / -0.209 | 439 / 58.4 / +0.116 / -0.002 | 469 / 52.8 / +0.050 / -0.100 |
| `m0_mix|top2|sqrel|wide 1.5R 16b` | 295 / 57.9 / +0.204 / +0.040 | 283 / 51.9 / -0.034 / -0.240 | 315 / 57.1 / +0.117 / -0.009 | 308 / 58.0 / +0.001 / -0.157 |
| `m0_mix|top2|tide4h|wide 3.0R 16b` | 335 / 56.6 / +0.165 / +0.005 | 395 / 53.2 / -0.013 / -0.210 | 330 / 56.3 / +0.104 / -0.011 | 429 / 55.2 / +0.099 / -0.050 |
| `m0_mix|top2|sqrel|wide 3.0R 8b` | 270 / 57.8 / +0.154 / -0.010 | 255 / 52.7 / -0.022 / -0.229 | 295 / 58.8 / +0.106 / -0.019 | 284 / 59.7 / -0.015 / -0.172 |
| `m0_mix|top2|flow|wide 3.0R 16b` | 573 / 57.2 / +0.152 / -0.003 | 637 / 52.2 / -0.038 / -0.246 | 608 / 56.3 / +0.099 / -0.020 | 636 / 55.0 / +0.022 / -0.132 |
| `m0_mix|top5|surge|wide 3.0R 16b` | 680 / 58.5 / +0.144 / -0.008 | 685 / 54.6 / +0.012 / -0.195 | 695 / 59.1 / +0.098 / -0.024 | 745 / 54.4 / +0.039 / -0.117 |
| `m1_pooled|top5|tide4h|wide 3.0R 16b` | 623 / 62.1 / +0.157 / -0.025 | 600 / 60.5 / +0.132 / -0.116 | 538 / 64.0 / +0.122 / -0.010 | 559 / 59.7 / +0.188 / -0.002 |
| `m0_mix|top2|none|wide 3.0R 16b` | 586 / 57.0 / +0.161 / +0.006 | 649 / 53.6 / -0.034 / -0.242 | 630 / 57.5 / +0.093 / -0.026 | 657 / 55.0 / +0.034 / -0.120 |
| `m0_mix|top2|agree|wide 3.0R 16b` | 574 / 57.4 / +0.167 / +0.013 | 627 / 53.1 / -0.041 / -0.247 | 620 / 57.7 / +0.092 / -0.027 | 627 / 54.6 / +0.029 / -0.119 |
| `m1_pooled|top5|tide4h|wide 2.0R 16b` | 650 / 62.8 / +0.154 / -0.028 | 627 / 60.0 / +0.106 / -0.140 | 552 / 63.8 / +0.110 / -0.023 | 577 / 58.1 / +0.155 / -0.034 |
| `m0_mix|top2|sqrel|wide 1.0R 16b` | 331 / 56.9 / +0.147 / -0.017 | 306 / 52.0 / -0.015 / -0.219 | 350 / 57.0 / +0.097 / -0.029 | 336 / 57.9 / +0.013 / -0.144 |
| `m0_mix|top2|sqrel|wide 2.0R 8b` | 278 / 58.2 / +0.144 / -0.020 | 264 / 52.6 / -0.005 / -0.213 | 307 / 57.9 / +0.092 / -0.034 | 297 / 59.0 / -0.017 / -0.173 |
| `m1_pooled|top5|overlap|wide 1.0R 16b` | 411 / 59.4 / +0.137 / -0.037 | 430 / 57.1 / +0.125 / -0.133 | 395 / 61.2 / +0.103 / -0.030 | 426 / 59.0 / +0.127 / -0.059 |

## Luck count

Variants tried: **5760** (4 models x 4 edge levels x 10 filters x 36 payoffs: 3 stops x 4 targets x 3 clocks), plus 28 model settings in the inner validation. Variants with average R after costs > 0 on both coins in the first half (>= 200 trades each): 6. Variants that clear costs on both coins in BOTH halves (>= 200 trades each): 0.

Placebo: the whole grid re-run 30 times with every signal slid by a random number of whole days (prices, outcomes and the release guard left in place). Best first-half worse-coin R after costs: real +0.066, placebo mean -0.095, max -0.022 (share of placebo runs at least as good: 0.0). Variants clearing both halves: placebo mean 0.0, max 0. First-half positive on both coins: placebo mean 0.0. Best first-half worse-coin hit rate: placebo mean 58.5%, max 65.82%.

## Limits

In-sample history; the engine's constants and voting cards were chosen on this history already. Refits every 4 weeks (live: weekly). Evidence built one coin at a time in 3-month pieces with 300 days of warm-up (the other coin's readings filled in afterwards). Fills at the next open, no slippage, no funding; a target is filled at its price even when the bar opens beyond it (cautious), a stop at the worse of the stop and the open. Full per-variant tables: `research/out/crypto1h.json`.

