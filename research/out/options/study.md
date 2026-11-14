# H40: Deribit options flow (put/call and skew), each input tested alone (exploration, not a loop round)

Registered 2026-11-14 09:00 UTC in `research/HYPOTHESES.md` before any H40 history was downloaded or any number computed; computed 2026-11-14 13:13 UTC. Code `research/options_study.py` (H39's statistics imported from `research/flows_study.py` unchanged); data `engine15/sources/options_hist.py` (docs `docs/SOURCES_options_hist.md`; not wired into the live engine); machine-readable `research/out/options/study.json`.

Development data only: bars before 2025-11-11; option trades fetched only up to 2025-11-11 00:00 UTC and every row known at or after it dropped; forward windows end before the seal. Decisions: each daily close (00:00 UTC). Risk IC = -Spearman(oriented input, outcome): **positive = the registered risk-off side (HIGH for every input) was right**. Partial IC = the same after removing the 30-day momentum sign m and the 200-day downtrend rule D; 'Partial +DVOL' also removes DVOL z90. Moving-block bootstrap (block max(10, 2h) days, 2000 draws).

**Multiple testing:** 120 tests run (120 registered: 6 inputs x 2 coins x 10); Bonferroni level 4.17e-04; BH q in the JSON.

**Bar (registered, H39's, not lowered):** partial IC at 7 days >= 0.12, positive, Bonferroni-significant, on both coins, same sign in both halves. RL loop S4 needs an IC of about 0.12-0.17 (0.160 for an information ratio of 1.15 at 7 days, one independent bet a week).

## Data

| Coin | First option trade served | Hours stored (dev) | Gapless | Trades | Block trades | Days without trades | Trades a day by year |
|---|---|---|---|---|---|---|---|
| BTCUSDT | 2016-11-29 | 60143 (2019-01-01 00:00 .. 2025-11-10 22:00) | yes | 20,872,001 | 276,102 | 0 | 2019: 1,185, 2020: 3,619, 2021: 8,036, 2022: 8,119, 2023: 9,764, 2024: 13,819, 2025: 14,640 |
| ETHUSDT | 2019-03-21 | 58247 (2019-03-21 00:00 .. 2025-11-10 22:00) | yes | 14,790,877 | 161,398 | 0 | 2019: 266, 2020: 1,214, 2021: 5,378, 2022: 9,280, 2023: 7,959, 2024: 8,444, 2025: 9,316 |

## BTCUSDT

| Input | Span (decision days) | n | Risk IC r1 | Risk IC r7 [95%] | Risk IC r30 | Risk IC dd1 | Risk IC dd7 | **Partial IC r7** [95%] (p) | Partial +DVOL r7 (p) | Partial r1 | Partial r30 | Halves r7 | corr m | corr DVOL z |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| O1 put/call notional, ln ratio, 7 days | 2019-09-09 .. 2025-11-10 | 2248 | -0.032 | -0.061 [-0.15, +0.03] | +0.002 | +0.129 | +0.083 | -0.122 [-0.22, -0.03] (0.0106) | -0.085 (0.105) | -0.062 | -0.064 | -0.03 / -0.14 | -0.20 | +0.05 |
| O2 put/call notional 24h, ln ratio, z 90d | 2019-09-09 .. 2025-11-10 | 2248 | -0.004 | -0.029 [-0.09, +0.03] | +0.016 | +0.015 | +0.015 | -0.058 [-0.12, +0.00] (0.0655) | -0.079 (0.022) | -0.011 | -0.003 | +0.01 / -0.08 | -0.11 | +0.03 |
| O3 taker bearish flow (put buys - sells minus call buys - sells) / notional, 7d | 2019-09-09 .. 2025-11-10 | 2248 | -0.005 | -0.014 [-0.10, +0.07] | +0.081 | +0.029 | +0.040 | -0.071 [-0.17, +0.02] (0.123) | -0.078 (0.109) | -0.015 | +0.042 | +0.02 / -0.06 | -0.27 | +0.04 |
| O4 25-delta put IV minus call IV (trades, 7-60d expiries, 72h), vol pts | 2019-09-09 .. 2025-11-10 | 2248 | +0.011 | +0.015 [-0.08, +0.11] | +0.033 | +0.051 | +0.054 | -0.019 [-0.11, +0.07] (0.688) | -0.036 (0.474) | -0.003 | +0.029 | +0.03 / -0.07 | -0.48 | -0.02 |
| O5 25-delta skew, 7-day change | 2019-09-09 .. 2025-11-10 | 2248 | -0.026 | -0.077 [-0.15, +0.00] | +0.006 | +0.026 | -0.010 | -0.090 [-0.17, -0.01] (0.0268) | -0.064 (0.158) | -0.032 | +0.018 | -0.11 / -0.04 | -0.11 | +0.03 |
| O6 block-trade bearish flow / block notional, 7d | 2019-09-09 .. 2025-11-10 | 2241 | -0.010 | -0.057 [-0.14, +0.03] | -0.037 | +0.062 | +0.067 | -0.086 [-0.17, +0.01] (0.0628) | -0.049 (0.311) | -0.032 | +0.005 | -0.09 / -0.01 | -0.12 | +0.04 |

Risk-off calls (input at or above the 80th percentile of its trailing 365 days), 7-day horizon; momentum's own risk-off (m = -1) over the same days for reference:

| Input | Days | Calls (share) | Hit rate (r7 < 0) | Base rate | Mean r7 calls / rest | Mean dd7 calls / rest | Calls already m = -1 | Momentum-off hit rate / mean r7 |
|---|---|---|---|---|---|---|---|---|
| O1 put/call notional, ln ratio, 7 days | 2069 | 473 (23%) | +41% | +46% | +1.3% / +1.2% | -6.4% / -6.0% | +59% | +49% / +0.3% |
| O2 put/call notional 24h, ln ratio, z 90d | 2069 | 422 (20%) | +40% | +46% | +1.7% / +1.1% | -6.9% / -5.9% | +53% | +49% / +0.3% |
| O3 taker bearish flow (put buys - sells minus call buys - sells) / notional, 7d | 2069 | 428 (21%) | +36% | +46% | +2.2% / +1.0% | -6.4% / -6.0% | +59% | +49% / +0.3% |
| O4 25-delta put IV minus call IV (trades, 7-60d expiries, 72h), vol pts | 2069 | 484 (23%) | +43% | +46% | +1.7% / +1.1% | -6.6% / -5.9% | +75% | +49% / +0.3% |
| O5 25-delta skew, 7-day change | 2069 | 398 (19%) | +36% | +46% | +3.6% / +0.7% | -5.9% / -6.1% | +51% | +49% / +0.3% |
| O6 block-trade bearish flow / block notional, 7d | 2062 | 358 (17%) | +40% | +46% | +2.1% / +1.2% | -5.9% / -5.9% | +51% | +49% / +0.5% |

## ETHUSDT

| Input | Span (decision days) | n | Risk IC r1 | Risk IC r7 [95%] | Risk IC r30 | Risk IC dd1 | Risk IC dd7 | **Partial IC r7** [95%] (p) | Partial +DVOL r7 (p) | Partial r1 | Partial r30 | Halves r7 | corr m | corr DVOL z |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| O1 put/call notional, ln ratio, 7 days | 2019-09-09 .. 2025-11-10 | 2163 | -0.015 | -0.027 [-0.13, +0.06] | -0.005 | +0.151 | +0.118 | -0.039 [-0.14, +0.05] (0.41) | +0.010 (0.857) | -0.023 | -0.015 | -0.00 / -0.02 | -0.09 | +0.12 |
| O2 put/call notional 24h, ln ratio, z 90d | 2019-09-09 .. 2025-11-10 | 2163 | +0.021 | +0.012 [-0.05, +0.07] | +0.045 | +0.031 | +0.021 | +0.005 [-0.06, +0.07] (0.887) | +0.035 (0.336) | +0.018 | +0.046 | -0.02 / +0.05 | -0.09 | +0.08 |
| O3 taker bearish flow (put buys - sells minus call buys - sells) / notional, 7d | 2019-09-09 .. 2025-11-10 | 2163 | +0.005 | -0.021 [-0.10, +0.07] | +0.084 | +0.032 | +0.026 | -0.052 [-0.14, +0.03] (0.236) | -0.033 (0.519) | -0.002 | +0.065 | -0.03 / -0.01 | -0.24 | +0.11 |
| O4 25-delta put IV minus call IV (trades, 7-60d expiries, 72h), vol pts | 2019-09-09 .. 2025-11-10 | 2162 | +0.030 | +0.067 [-0.02, +0.16] | +0.062 | +0.030 | +0.074 | +0.026 [-0.06, +0.11] (0.554) | +0.011 (0.819) | +0.011 | +0.033 | +0.13 / -0.03 | -0.48 | -0.04 |
| O5 25-delta skew, 7-day change | 2019-09-09 .. 2025-11-10 | 2161 | -0.015 | +0.010 [-0.06, +0.09] | +0.067 | +0.043 | +0.047 | -0.001 [-0.08, +0.08] (0.969) | +0.005 (0.907) | -0.024 | +0.069 | +0.02 / -0.01 | -0.05 | +0.08 |
| O6 block-trade bearish flow / block notional, 7d | 2019-10-18 .. 2025-11-10 | 1937 | +0.003 | +0.002 [-0.08, +0.09] | +0.139 | +0.074 | +0.080 | -0.020 [-0.11, +0.07] (0.655) | +0.011 (0.83) | +0.002 | +0.124 | -0.02 / +0.04 | -0.09 | +0.18 |

Risk-off calls (input at or above the 80th percentile of its trailing 365 days), 7-day horizon; momentum's own risk-off (m = -1) over the same days for reference:

| Input | Days | Calls (share) | Hit rate (r7 < 0) | Base rate | Mean r7 calls / rest | Mean dd7 calls / rest | Calls already m = -1 | Momentum-off hit rate / mean r7 |
|---|---|---|---|---|---|---|---|---|
| O1 put/call notional, ln ratio, 7 days | 2012 | 430 (21%) | +45% | +47% | +2.4% / +1.4% | -7.9% / -7.8% | +61% | +50% / -0.1% |
| O2 put/call notional 24h, ln ratio, z 90d | 2012 | 419 (21%) | +48% | +47% | +1.1% / +1.7% | -8.5% / -7.7% | +54% | +50% / -0.1% |
| O3 taker bearish flow (put buys - sells minus call buys - sells) / notional, 7d | 2012 | 420 (21%) | +40% | +47% | +2.7% / +1.3% | -6.8% / -8.1% | +68% | +50% / -0.1% |
| O4 25-delta put IV minus call IV (trades, 7-60d expiries, 72h), vol pts | 2010 | 410 (20%) | +46% | +47% | +1.3% / +1.7% | -9.1% / -7.4% | +79% | +50% / -0.0% |
| O5 25-delta skew, 7-day change | 2008 | 390 (19%) | +39% | +47% | +2.6% / +1.4% | -8.1% / -7.7% | +51% | +50% / -0.0% |
| O6 block-trade bearish flow / block notional, 7d | 1755 | 350 (20%) | +46% | +48% | +0.7% / +1.3% | -7.2% / -8.1% | +65% | +51% / -0.4% |

## Bonferroni survivors

| Coin | Input | Test | Risk IC | p | BH q |
|---|---|---|---|---|---|
| ETH | O1 put/call notional, ln ratio, 7 days | ic_dd1 | +0.151 | 7.3e-08 | 8.7e-06 |
| BTC | O1 put/call notional, ln ratio, 7 days | ic_dd1 | +0.129 | 1.3e-05 | 0.00076 |

## Verdict against the registered bar

| Input | Qualifies | Why not |
|---|---|---|
| O1 put/call notional, ln ratio, 7 days | no | BTC partial IC7 -0.122 (p 0.0106); ETH partial IC7 -0.039 (p 0.41) |
| O2 put/call notional 24h, ln ratio, z 90d | no | BTC partial IC7 -0.058 (p 0.0655); BTC halves +0.014 / -0.080; ETH partial IC7 +0.005 (p 0.887); ETH halves -0.022 / +0.052 |
| O3 taker bearish flow (put buys - sells minus call buys - sells) / notional, 7d | no | BTC partial IC7 -0.071 (p 0.123); BTC halves +0.018 / -0.058; ETH partial IC7 -0.052 (p 0.236) |
| O4 25-delta put IV minus call IV (trades, 7-60d expiries, 72h), vol pts | no | BTC partial IC7 -0.019 (p 0.688); BTC halves +0.034 / -0.066; ETH partial IC7 +0.026 (p 0.554); ETH halves +0.130 / -0.028 |
| O5 25-delta skew, 7-day change | no | BTC partial IC7 -0.090 (p 0.0268); ETH partial IC7 -0.001 (p 0.969); ETH halves +0.022 / -0.012 |
| O6 block-trade bearish flow / block notional, 7d | no | BTC partial IC7 -0.086 (p 0.0628); ETH partial IC7 -0.020 (p 0.655); ETH halves -0.021 / +0.042 |

## Reading (written after the run; changes no rule)

- **No input meets the registered bar.** On the registered (risk-off = HIGH) side the largest partial IC at 7 days is
  ETH 25-delta skew +0.026 (p 0.55); on BTC every partial IC at 7 days is negative. The bar is >= 0.12 on both coins at
  p <= 4.17e-04; S4 needs about 0.12-0.17.
- **The largest effect has the wrong sign.** BTC 7-day put/call notional: partial IC at 7 days -0.122 (95% -0.22 to
  -0.03, p 0.011): after heavy put trading BTC tended to do BETTER over the next week (a contrarian pattern). It is not
  Bonferroni-significant (p 0.011 vs 4.17e-04), weakens to -0.085 (p 0.11) once DVOL is controlled for, is BTC only
  (ETH -0.039, p 0.41), and the contrarian reading was not registered as a test, so it is reported, not claimed.
  BTC skew change (-0.090, p 0.027) and block flow (-0.086, p 0.063) lean the same, contrarian, way, also not significant.
- **Two Bonferroni survivors, both next-day DRAWDOWN tests of the 7-day put/call ratio** (ETH dd1 +0.151, p 7e-08; BTC
  dd1 +0.129, p 1.3e-05): high put trading comes with deeper next-day drawdowns but not lower 7-day returns. Like DVOL
  and stablecoin growth in H39, this is information about the size of moves, not their direction.
- **Risk-off calls do not work as exits.** Days in an input's top-20% tail were followed by r7 < 0 on 36-48% of days
  against base rates of 46-48% (momentum's own risk-off: 49-51%); mean 7-day returns after calls were mostly HIGHER than
  on other days (BTC skew change: +3.6% vs +0.7%).
- **Overlap with the trend.** The skew level correlates -0.48 with the 30-day momentum sign on both coins (puts are dear
  after falls), so what it says the trend mostly says already; correlations with DVOL z are small (-0.04 to +0.18).
- **Data caveats.** One venue; volume ratios, not open interest; trade-IV skew is an approximation (index price as the
  underlying, fixed delta and expiry buckets, the mix changes with what traded); 2019-2020 volume is thin (BTC about
  1,200 and ETH about 270 trades a day in 2019), so early readings are noisier; block trades rare before 2021 (ETH's
  block input starts Oct 2019 and speaks on 1,937 of 2,163 days). Taker side for block and combo legs is Deribit's
  reported aggressor, not always the economic direction. No look-ahead from the source itself (trades are final when
  printed and the fetch stopped at the seal), unlike H39's revised on-chain flows.
