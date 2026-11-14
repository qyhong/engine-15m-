# H39: new positioning and on-chain inputs, each tested alone (exploration, not a loop round)

Registered 2026-11-13 10:52 UTC in `research/HYPOTHESES.md` before any H39 history was downloaded or any number computed; computed 2026-11-13 11:45 UTC. Code `research/flows_study.py`; data `engine15/sources/flows.py` (docs `docs/SOURCES_flows.md`; not wired into the live engine); machine-readable `research/out/flows/study.json`.

Development data only: bars before 2025-11-11 (`core.load(dev_only=True)`); source rows known at or after 2025-11-11 00:00 UTC dropped first; forward windows end before the seal. The holdout was not touched. Decisions: each daily close (00:00 UTC). Risk IC = -Spearman(oriented input, outcome): **positive = the registered risk-off side was right** (high input, lower forward return / deeper forward drawdown). Partial IC = the same after removing the 30-day momentum sign m and the 200-day downtrend rule D (rank residuals on [1, m, D]). 95% intervals and p from a moving-block bootstrap (block max(10, 2h) days, 2000 draws).

**Multiple testing:** 216 tests run (216 registered: 12 inputs x 2 coins x 9); Bonferroni level 2.31e-04; BH q in the JSON.

**IC needed for an overlay information ratio of 1.15** (round 3's S4 estimate), one independent bet per horizon: 1 day 0.060, 7 days 0.160, 30 days 0.331. Round 3's 0.12-0.17 band corresponds to the 7-day horizon; the registered bar for an RL round 4 is a partial IC at 7 days >= 0.12, Bonferroni-significant, on both coins, with the same sign in both halves of the input's span.

## BTCUSDT

| Input | Span (decision days) | n | Risk IC r1 | Risk IC r7 [95%] | Risk IC r30 | Risk IC dd7 | Risk IC dd30 | **Partial IC r7** [95%] (p) | Partial r30 | Added R2 r7 | Halves r7 | corr with m |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| X1 Binance open interest, 7-day log change | 2020-09-09 .. 2025-11-10 | 1882 | +0.024 | +0.034 [-0.04, +0.11] | +0.040 | +0.020 | +0.061 | +0.029 [-0.04, +0.11] (0.434) | +0.034 | 0.0006 | +0.01 / +0.08 | -0.06 |
| X2 Binance global account long/short, z 90d | 2020-10-01 .. 2025-11-10 | 1843 | +0.005 | +0.032 [-0.07, +0.12] | +0.073 | +0.093 | +0.151 | +0.014 [-0.08, +0.10] (0.753) | +0.054 | 0.0000 | +0.02 / +0.05 | -0.25 |
| X3 Binance top-trader position L/S minus global account L/S, z 90d | 2020-10-01 .. 2025-11-10 | 1494 | -0.008 | +0.010 [-0.10, +0.10] | +0.038 | +0.104 | +0.169 | -0.027 [-0.13, +0.07] (0.607) | -0.004 | 0.0006 | -0.01 / +0.05 | -0.30 |
| X4 Bitfinex margin ln(longs/shorts), 14-day change | 2021-03-08 .. 2025-11-10 | 1702 | +0.018 | -0.022 [-0.12, +0.08] | +0.062 | +0.032 | +0.043 | -0.030 [-0.12, +0.07] (0.551) | +0.062 | 0.0011 | +0.01 / -0.05 | -0.17 |
| X5 CME leveraged funds net % OI, z 52 reports | 2019-09-09 .. 2025-10-10 | 2211 | -0.005 | +0.016 [-0.08, +0.11] | +0.010 | -0.075 | -0.155 | +0.047 [-0.06, +0.14] (0.358) | +0.034 | 0.0025 | +0.05 / -0.02 | +0.05 |
| X6 MVRV, ln z 365d | 2019-09-09 .. 2025-11-10 | 2248 | -0.022 | -0.050 [-0.14, +0.06] | -0.099 | -0.055 | -0.133 | -0.027 [-0.12, +0.08] (0.588) | -0.077 | 0.0018 | -0.10 / +0.05 | +0.44 |
| X7 exchange net inflow 7d / exchange supply | 2019-09-09 .. 2025-11-10 | 2248 | +0.038 | +0.064 [-0.02, +0.15] | +0.034 | +0.118 | +0.127 | +0.075 [-0.01, +0.16] (0.0817) | +0.017 | 0.0047 | +0.03 / +0.10 | -0.06 |
| X8 active addresses, ln(30d mean / 365d mean) | 2019-09-09 .. 2025-11-10 | 2248 | +0.011 | +0.018 [-0.08, +0.12] | +0.037 | -0.004 | +0.058 | +0.024 [-0.08, +0.12] (0.649) | +0.045 | 0.0006 | +0.05 / -0.01 | -0.16 |
| X9 BTC hash ribbon ln(SMA30/SMA60) | 2019-09-09 .. 2025-11-10 | 2248 | +0.025 | +0.064 [-0.03, +0.16] | +0.035 | +0.026 | +0.018 | +0.061 [-0.04, +0.18] (0.262) | +0.067 | 0.0048 | +0.03 / +0.11 | -0.13 |
| X10 stablecoin supply, 30-day log change | 2019-09-09 .. 2025-11-10 | 2248 | +0.010 | +0.030 [-0.07, +0.13] | +0.088 | -0.161 | -0.076 | +0.006 [-0.12, +0.10] (0.906) | -0.005 | 0.0002 | +0.10 / -0.08 | -0.10 |
| X11 Fear & Greed, 7-day mean | 2019-09-09 .. 2025-11-10 | 2248 | -0.019 | -0.034 [-0.13, +0.07] | -0.028 | -0.024 | -0.074 | +0.037 [-0.06, +0.13] (0.454) | +0.059 | 0.0003 | -0.07 / +0.07 | +0.54 |
| X12 Deribit DVOL, z 90d | 2021-04-22 .. 2025-11-10 | 1657 | -0.061 | -0.104 [-0.21, -0.01] | -0.118 | +0.046 | -0.126 | -0.099 [-0.20, -0.00] (0.0491) | -0.114 | 0.0060 | -0.11 / -0.08 | +0.08 |

Risk-off calls (input in its registered risk-off tail: at or above the 80th percentile of its trailing 365 days), 7-day horizon; momentum's own risk-off (m = -1) over the same days for reference:

| Input | Days | Calls (share) | Hit rate (r7 < 0) | Base rate | Mean r7 calls / rest | Mean dd7 calls / rest | Calls already m = -1 | Momentum-off hit rate / mean r7 |
|---|---|---|---|---|---|---|---|---|
| X1 Binance open interest, 7-day log change | 1703 | 311 (18%) | +54% | +48% | -0.4% / +0.8% | -6.8% / -5.8% | +48% | +50% / +0.1% |
| X2 Binance global account long/short, z 90d | 1664 | 321 (19%) | +50% | +48% | -0.2% / +0.8% | -5.9% / -5.9% | +69% | +50% / +0.2% |
| X3 Binance top-trader position L/S minus global account L/S, z 90d | 1136 | 227 (20%) | +45% | +46% | +0.4% / +1.0% | -5.4% / -6.0% | +70% | +50% / +0.2% |
| X4 Bitfinex margin ln(longs/shorts), 14-day change | 1523 | 286 (19%) | +47% | +48% | +1.2% / +0.5% | -5.5% / -5.5% | +57% | +50% / +0.3% |
| X5 CME leveraged funds net % OI, z 52 reports | 2032 | 572 (28%) | +45% | +45% | +1.1% / +1.3% | -5.8% / -6.2% | +42% | +49% / +0.3% |
| X6 MVRV, ln z 365d | 2069 | 541 (26%) | +41% | +46% | +2.9% / +0.7% | -5.1% / -6.4% | +14% | +49% / +0.3% |
| X7 exchange net inflow 7d / exchange supply | 2069 | 362 (17%) | +48% | +46% | +0.5% / +1.4% | -7.7% / -5.7% | +49% | +49% / +0.3% |
| X8 active addresses, ln(30d mean / 365d mean) | 2069 | 410 (20%) | +49% | +46% | +0.5% / +1.4% | -6.9% / -5.9% | +58% | +49% / +0.3% |
| X9 BTC hash ribbon ln(SMA30/SMA60) | 2069 | 429 (21%) | +43% | +46% | +0.9% / +1.3% | -6.6% / -5.9% | +51% | +49% / +0.3% |
| X10 stablecoin supply, 30-day log change | 2069 | 333 (16%) | +49% | +46% | +0.3% / +1.4% | -7.2% / -5.9% | +52% | +49% / +0.3% |
| X11 Fear & Greed, 7-day mean | 2069 | 544 (26%) | +42% | +46% | +2.7% / +0.7% | -5.4% / -6.3% | +8% | +49% / +0.3% |
| X12 Deribit DVOL, z 90d | 1478 | 298 (20%) | +43% | +48% | +1.8% / +0.2% | -5.2% / -5.5% | +39% | +50% / -0.0% |

## ETHUSDT

| Input | Span (decision days) | n | Risk IC r1 | Risk IC r7 [95%] | Risk IC r30 | Risk IC dd7 | Risk IC dd30 | **Partial IC r7** [95%] (p) | Partial r30 | Added R2 r7 | Halves r7 | corr with m |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| X1 Binance open interest, 7-day log change | 2021-12-09 .. 2025-11-10 | 1426 | +0.023 | +0.014 [-0.08, +0.11] | -0.028 | +0.035 | +0.003 | +0.017 [-0.08, +0.12] (0.728) | -0.025 | 0.0001 | -0.06 / +0.09 | -0.03 |
| X2 Binance global account long/short, z 90d | 2021-12-31 .. 2025-11-10 | 1387 | +0.019 | +0.065 [-0.05, +0.16] | +0.179 | +0.014 | +0.113 | +0.043 [-0.08, +0.14] (0.441) | +0.161 | 0.0045 | +0.09 / +0.04 | -0.29 |
| X3 Binance top-trader position L/S minus global account L/S, z 90d | 2021-12-31 .. 2025-11-10 | 1038 | -0.003 | +0.047 [-0.08, +0.14] | +0.189 | +0.018 | +0.147 | -0.008 [-0.13, +0.09] (0.892) | +0.104 | 0.0000 | +0.02 / +0.09 | -0.48 |
| X4 Bitfinex margin ln(longs/shorts), 14-day change | 2021-03-08 .. 2025-11-10 | 1673 | +0.003 | -0.013 [-0.12, +0.09] | +0.074 | -0.032 | +0.018 | -0.021 [-0.13, +0.08] (0.684) | +0.066 | 0.0015 | +0.01 / -0.04 | -0.04 |
| X5 CME leveraged funds net % OI, z 52 reports | 2021-10-01 .. 2025-10-10 | 1458 | +0.008 | +0.012 [-0.11, +0.13] | -0.019 | +0.096 | +0.054 | +0.020 [-0.10, +0.13] (0.728) | -0.007 | 0.0016 | -0.07 / +0.03 | -0.01 |
| X6 MVRV, ln z 365d | 2019-09-09 .. 2025-11-10 | 2163 | -0.024 | -0.043 [-0.15, +0.05] | -0.101 | -0.054 | -0.162 | -0.008 [-0.10, +0.09] (0.879) | -0.124 | 0.0001 | -0.11 / +0.04 | +0.51 |
| X7 exchange net inflow 7d / exchange supply | 2019-09-09 .. 2025-11-10 | 2163 | +0.009 | +0.015 [-0.06, +0.10] | -0.000 | +0.066 | +0.041 | +0.032 [-0.05, +0.12] (0.461) | +0.045 | 0.0003 | -0.05 / +0.10 | +0.00 |
| X8 active addresses, ln(30d mean / 365d mean) | 2019-09-09 .. 2025-11-10 | 2163 | +0.033 | +0.067 [-0.03, +0.17] | +0.048 | -0.060 | -0.078 | +0.053 [-0.03, +0.15] (0.256) | +0.040 | 0.0056 | +0.14 / -0.07 | -0.17 |
| X9 BTC hash ribbon ln(SMA30/SMA60) | 2019-09-09 .. 2025-11-10 | 2163 | +0.010 | +0.047 [-0.06, +0.15] | +0.092 | +0.021 | +0.118 | +0.020 [-0.09, +0.13] (0.715) | +0.091 | 0.0000 | +0.00 / +0.10 | -0.12 |
| X10 stablecoin supply, 30-day log change | 2019-09-09 .. 2025-11-10 | 2163 | +0.024 | +0.072 [-0.02, +0.16] | +0.072 | -0.130 | -0.111 | +0.033 [-0.05, +0.13] (0.466) | +0.021 | 0.0020 | +0.13 / -0.08 | -0.19 |
| X11 Fear & Greed, 7-day mean | 2019-09-09 .. 2025-11-10 | 2163 | -0.033 | -0.079 [-0.18, +0.02] | -0.110 | -0.059 | -0.160 | -0.040 [-0.14, +0.07] (0.438) | -0.102 | 0.0032 | -0.14 / -0.01 | +0.51 |
| X12 Deribit DVOL, z 90d | 2021-04-23 .. 2025-11-10 | 1637 | -0.032 | -0.060 [-0.16, +0.04] | -0.009 | +0.067 | +0.005 | -0.049 [-0.15, +0.05] (0.344) | +0.003 | 0.0003 | -0.03 / -0.09 | +0.11 |

Risk-off calls (input in its registered risk-off tail: at or above the 80th percentile of its trailing 365 days), 7-day horizon; momentum's own risk-off (m = -1) over the same days for reference:

| Input | Days | Calls (share) | Hit rate (r7 < 0) | Base rate | Mean r7 calls / rest | Mean dd7 calls / rest | Calls already m = -1 | Momentum-off hit rate / mean r7 |
|---|---|---|---|---|---|---|---|---|
| X1 Binance open interest, 7-day log change | 1247 | 246 (20%) | +48% | +48% | +1.4% / +0.7% | -6.9% / -7.0% | +41% | +48% / +0.2% |
| X2 Binance global account long/short, z 90d | 1208 | 255 (21%) | +42% | +48% | +1.8% / +0.7% | -6.2% / -6.8% | +65% | +47% / +0.2% |
| X3 Binance top-trader position L/S minus global account L/S, z 90d | 847 | 185 (22%) | +52% | +50% | -0.8% / +1.4% | -7.8% / -6.5% | +79% | +51% / -0.3% |
| X4 Bitfinex margin ln(longs/shorts), 14-day change | 1512 | 316 (21%) | +49% | +50% | +0.3% / +0.4% | -7.8% / -7.4% | +59% | +51% / -0.4% |
| X5 CME leveraged funds net % OI, z 52 reports | 1279 | 270 (21%) | +54% | +50% | -0.4% / +0.8% | -9.2% / -6.6% | +54% | +50% / -0.2% |
| X6 MVRV, ln z 365d | 2012 | 574 (29%) | +46% | +47% | +2.6% / +1.2% | -6.7% / -8.3% | +16% | +50% / -0.1% |
| X7 exchange net inflow 7d / exchange supply | 2012 | 393 (20%) | +49% | +47% | +2.1% / +1.5% | -8.9% / -7.6% | +47% | +50% / -0.1% |
| X8 active addresses, ln(30d mean / 365d mean) | 2012 | 437 (22%) | +45% | +47% | +1.6% / +1.6% | -8.4% / -7.7% | +56% | +50% / -0.1% |
| X9 BTC hash ribbon ln(SMA30/SMA60) | 2012 | 421 (21%) | +40% | +47% | +3.2% / +1.2% | -8.1% / -7.8% | +48% | +50% / -0.1% |
| X10 stablecoin supply, 30-day log change | 2012 | 323 (16%) | +46% | +47% | +1.8% / +1.5% | -8.8% / -7.7% | +59% | +50% / -0.1% |
| X11 Fear & Greed, 7-day mean | 2012 | 537 (27%) | +42% | +47% | +3.2% / +1.0% | -6.7% / -8.2% | +11% | +50% / -0.1% |
| X12 Deribit DVOL, z 90d | 1474 | 328 (22%) | +49% | +50% | +0.7% / +0.3% | -7.5% / -7.4% | +46% | +51% / -0.5% |

## Verdict against the registered bar

| Input | Qualifies for an RL round 4 | Why not |
|---|---|---|
| X1 Binance open interest, 7-day log change | no | BTC partial IC7 +0.029 (p 0.434); ETH partial IC7 +0.017 (p 0.728); ETH halves -0.055 / +0.090 |
| X2 Binance global account long/short, z 90d | no | BTC partial IC7 +0.014 (p 0.753); ETH partial IC7 +0.043 (p 0.441) |
| X3 Binance top-trader position L/S minus global account L/S, z 90d | no | BTC partial IC7 -0.027 (p 0.607); BTC halves -0.010 / +0.046; ETH partial IC7 -0.008 (p 0.892) |
| X4 Bitfinex margin ln(longs/shorts), 14-day change | no | BTC partial IC7 -0.030 (p 0.551); BTC halves +0.006 / -0.052; ETH partial IC7 -0.021 (p 0.684); ETH halves +0.008 / -0.037 |
| X5 CME leveraged funds net % OI, z 52 reports | no | BTC partial IC7 +0.047 (p 0.358); BTC halves +0.050 / -0.018; ETH partial IC7 +0.020 (p 0.728); ETH halves -0.068 / +0.027 |
| X6 MVRV, ln z 365d | no | BTC partial IC7 -0.027 (p 0.588); BTC halves -0.097 / +0.048; ETH partial IC7 -0.008 (p 0.879); ETH halves -0.113 / +0.044 |
| X7 exchange net inflow 7d / exchange supply | no | BTC partial IC7 +0.075 (p 0.0817); ETH partial IC7 +0.032 (p 0.461); ETH halves -0.053 / +0.101 |
| X8 active addresses, ln(30d mean / 365d mean) | no | BTC partial IC7 +0.024 (p 0.649); BTC halves +0.051 / -0.009; ETH partial IC7 +0.053 (p 0.256); ETH halves +0.136 / -0.071 |
| X9 BTC hash ribbon ln(SMA30/SMA60) | no | BTC partial IC7 +0.061 (p 0.262); ETH partial IC7 +0.020 (p 0.715) |
| X10 stablecoin supply, 30-day log change | no | BTC partial IC7 +0.006 (p 0.906); BTC halves +0.100 / -0.079; ETH partial IC7 +0.033 (p 0.466); ETH halves +0.127 / -0.084 |
| X11 Fear & Greed, 7-day mean | no | BTC partial IC7 +0.037 (p 0.454); BTC halves -0.070 / +0.073; ETH partial IC7 -0.040 (p 0.438) |
| X12 Deribit DVOL, z 90d | no | BTC partial IC7 -0.099 (p 0.0491); ETH partial IC7 -0.049 (p 0.344) |

## Bonferroni survivors and what they are (written after the run; changes no rule)

Of 216 tests, 17 have p < 0.05 (about 11 expected by chance). Five pass Bonferroni (p <= 2.31e-04), and **all five are
next-day DRAWDOWN tests, none a return or incremental test**:

| Coin | Input | Test | Risk IC | p | BH q |
|---|---|---|---|---|---|
| ETH | X10 stablecoin 30d change | dd1 | -0.176 | 1.4e-08 | 3.0e-06 |
| BTC | X10 stablecoin 30d change | dd1 | -0.163 | 1.8e-07 | 2.0e-05 |
| ETH | X12 DVOL z 90d | dd1 | +0.164 | 4.9e-06 | 3.5e-04 |
| BTC | X7 exchange net inflow 7d | dd1 | +0.114 | 3.7e-05 | 1.7e-03 |
| BTC | X12 DVOL z 90d | dd1 | +0.143 | 3.9e-05 | 1.7e-03 |

These say how BIG the next day's range is likely to be, not which way price goes: high DVOL comes with deeper next-day
drawdowns but, if anything, HIGHER returns (BTC risk IC r7 -0.104, partial -0.099: the wrong sign for a risk-off call);
fast stablecoin growth (the opposite of the registered risk-off side) comes with deeper next-day drawdowns. Forward
drawdown mixes direction with volatility, and the controls (m, D) do not include volatility, so these are most likely
volatility forecasts. BTC exchange net inflow is the only one on the registered side for both drawdown (dd1 +0.114,
dd7 +0.118) and return (partial r7 +0.075, p 0.08), but it is BTC only (ETH partial +0.032, halves of opposite sign),
and its history is CoinMetrics' revised view (exchange address tags are added backwards), so it is the input most exposed
to look-ahead.

## Reading

- **No input meets the registered bar.** The largest partial IC at 7 days on the registered side is +0.075 (BTC exchange
  net inflow, p 0.08) against the 0.12 bar and the ~0.16 that an information ratio of 1.15 needs at that horizon; on ETH
  the largest is +0.053 (active addresses, halves of opposite sign). Every 95% interval of a partial IC at 7 days
  includes zero except BTC DVOL, whose sign is the wrong one.
- **The risk-off calls do not beat momentum's.** Hit rates of the inputs' tail calls (r7 < 0) are 40-54% against base
  rates of 46-50%; momentum's own risk-off calls hit 48-51%. Several calls (MVRV, Fear & Greed, DVOL, hash ribbon) are
  followed by HIGHER 7-day returns than the rest: in 2020-2025 extremes of greed and of implied volatility were not
  good exits.
- **Overlap with the trend.** MVRV and Fear & Greed correlate +0.44 to +0.54 with the 30-day momentum sign; the account
  long/short ratios -0.25 to -0.48 (the crowd adds longs into falls). Whatever they carry, the trend mostly has already.
- **Longer horizons look better but are not testable with this span.** Some 30-day ICs are 0.15-0.19 (ETH account
  long/short and top-vs-global, BTC account long/short on dd30), but the 30-day horizon needs ~0.33, the 95% intervals
  are wide (about 12 independent 30-day bets a year over 4-5 years), and none is significant after correction.
- **Span.** Binance positioning: BTC from Sep 2020, ETH from Dec 2021 (about 4 development years: the 2021 top, the
  2022 bear and the 2023-25 recovery). Bitfinex from Mar 2021. CME Ether from Oct 2021. The 2025 government shutdown
  delayed the CFTC reports of Oct 2025 past the seal, so X5 stops on 10 Oct 2025.
- **Bug fixed and disclosed.** The first run computed nothing (decision times were built in the wrong unit, so every
  input was empty and no statistic existed); it was fixed (`as_unit("ms")`, plus an assertion) and run once more. No
  number was seen before the fix.
