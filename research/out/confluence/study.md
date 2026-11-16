# H46: momentum / speed / participation confluence at a daily-level break

PAPER RESEARCH ONLY. Registered 2026-11-16 05:11 UTC (`research/HYPOTHESES.md` H46) before any outcome. Development data only (rows before 2025-11-11 00:00 UTC; the holdout was not read). Events with entry from 2020-01-01; first half before 2023-06-07. Written 2026-11-16 05:19 UTC.

Event = the first 15m close beyond the level in its UTC day per direction (H45's code, no momentum condition). Outcome = +0.5 daily ATR in the break direction before -0.5 daily ATR from the next 15m open within 72 h (a bar touching both = miss; neither = unresolved, excluded). Hit rate = hits / resolved; a coin flip is ~50%. p = exact two-sided binomial against 50%. Buckets tested: 32 per level and scope x 2 levels x 6 scopes = **384**; Bonferroni threshold per half p < 1.30e-04.

## Verdict: NO 70% setup

No bucket in any scope or level reached 70% in both halves with >= 100 resolved events per half. The best lower-of-two-halves hit rate among the pooled buckets is pday / trend+htf: 51.4% (first 51.4% of 2337, second 51.5% of 1567).

Buckets whose p-value passes Bonferroni in BOTH halves (any hit rate, either side of 50%): 0 of 384.

## Reference: every daily break (no confluence)

| level | scope | first: hit | n | p | second: hit | n | p |
|---|---|---|---|---|---|---|---|
| pday | pooled | 49.1% | 6916 (368 unres.) | 0.152 | 50.0% | 4919 (239 unres.) | 0.977 |
| pday | crypto | 47.9% | 1930 (52 unres.) | 0.072 | 51.1% | 1345 (40 unres.) | 0.413 |
| pday | metals | 47.8% | 1757 (73 unres.) | 0.070 | 49.0% | 1266 (49 unres.) | 0.482 |
| pday | fx | 53.3% | 875 (46 unres.) | 0.058 | 53.3% | 612 (40 unres.) | 0.115 |
| pday | index | 48.1% | 694 (84 unres.) | 0.343 | 49.1% | 495 (45 unres.) | 0.719 |
| pday | energy | 50.2% | 1660 (113 unres.) | 0.902 | 48.4% | 1201 (65 unres.) | 0.273 |
| roll24 | pooled | 49.2% | 7051 (401 unres.) | 0.190 | 50.2% | 5058 (244 unres.) | 0.746 |
| roll24 | crypto | 47.5% | 2356 (72 unres.) | 0.018 | 50.1% | 1652 (49 unres.) | 0.941 |
| roll24 | metals | 48.6% | 1674 (97 unres.) | 0.271 | 49.9% | 1205 (52 unres.) | 0.954 |
| roll24 | fx | 54.9% | 875 (52 unres.) | 0.004 | 54.2% | 635 (44 unres.) | 0.039 |
| roll24 | index | 46.5% | 426 (50 unres.) | 0.160 | 52.6% | 293 (36 unres.) | 0.413 |
| roll24 | energy | 49.9% | 1720 (130 unres.) | 0.942 | 48.2% | 1273 (63 unres.) | 0.217 |

## Top buckets (pooled, sorted by the lower of the two halves' hit rates, >= 100 resolved per half)

| # | level | bucket | first: hit | n | p | second: hit | n | p | events / month (pooled, 1st / 2nd) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | pday | trend+htf | 51.4% | 2337 (106 unres.) | 0.172 | 51.5% | 1567 (70 unres.) | 0.245 | 59.3 / 56.1 |
| 2 | roll24 | trend+htf | 51.0% | 2466 (117 unres.) | 0.324 | 53.1% | 1664 (72 unres.) | 0.013 | 62.8 / 59.5 |
| 3 | roll24 | count>=5 | 50.4% | 1890 (63 unres.) | 0.730 | 53.2% | 1251 (42 unres.) | 0.024 | 47.4 / 44.3 |
| 4 | roll24 | squeeze+htf | 50.2% | 1603 (74 unres.) | 0.920 | 53.9% | 991 (49 unres.) | 0.016 | 40.7 / 35.6 |
| 5 | roll24 | part+htf | 50.1% | 1318 (33 unres.) | 0.934 | 53.8% | 846 (23 unres.) | 0.030 | 32.8 / 29.8 |
| 6 | pday | osc+htf | 50.1% | 2223 (113 unres.) | 0.966 | 50.9% | 1452 (80 unres.) | 0.512 | 56.8 / 52.5 |
| 7 | roll24 | trend+part | 50.1% | 2229 (73 unres.) | 0.966 | 51.6% | 1511 (44 unres.) | 0.237 | 55.9 / 53.3 |
| 8 | roll24 | speed+trend | 50.1% | 4678 (253 unres.) | 0.942 | 50.0% | 3223 (130 unres.) | 0.972 | 119.8 / 114.9 |
| 9 | roll24 | trend | 50.1% | 5372 (303 unres.) | 0.902 | 50.0% | 3849 (179 unres.) | 1.000 | 137.9 / 138.1 |
| 10 | pday | htf | 50.0% | 3329 (170 unres.) | 1.000 | 50.6% | 2312 (111 unres.) | 0.574 | 85.0 / 83.0 |

## Which single groups help (pooled; lift = bucket hit rate minus the level's reference, percentage points)

| level | group | share of events 1st / 2nd | hit 1st | lift 1st | hit 2nd | lift 2nd |
|---|---|---|---|---|---|---|
| pday | 1 speed | 83.5 / 80.5% | 48.9% | -0.2 | 49.8% | -0.2 |
| pday | 2 trend strength | 70.7 / 69.8% | 50.0% | +0.8 | 49.8% | -0.2 |
| pday | 3 oscillator | 57.0 / 55.7% | 49.0% | -0.1 | 49.5% | -0.5 |
| pday | 4 participation | 36.8 / 36.5% | 49.2% | +0.1 | 49.8% | -0.2 |
| pday | 5 squeeze release | 45.6 / 41.6% | 48.8% | -0.3 | 50.0% | -0.0 |
| pday | 6 HTF alignment | 48.0 / 47.0% | 50.0% | +0.8 | 50.6% | +0.6 |
| pday | 7 leverage (OI) | 10.3 / 15.7% | 46.7% | -2.4 | 53.4% | +3.4 |
| roll24 | 1 speed | 88.3 / 85.0% | 49.2% | +0.0 | 50.4% | +0.2 |
| roll24 | 2 trend strength | 76.2 / 76.0% | 50.1% | +0.9 | 50.0% | -0.2 |
| roll24 | 3 oscillator | 56.4 / 55.8% | 48.9% | -0.3 | 50.4% | +0.1 |
| roll24 | 4 participation | 40.7 / 38.9% | 49.7% | +0.5 | 51.5% | +1.3 |
| roll24 | 5 squeeze release | 47.6 / 43.4% | 48.9% | -0.3 | 51.4% | +1.1 |
| roll24 | 6 HTF alignment | 47.2 / 44.9% | 49.8% | +0.5 | 52.0% | +1.8 |
| roll24 | 7 leverage (OI) | 11.8 / 18.0% | 48.0% | -1.2 | 51.1% | +0.8 |

Per market group, single-group lift (first / second half, points):

| level | group | crypto | metals | fx | index | energy |
|---|---|---|---|---|---|---|
| pday | 1 speed | -0.1 / -0.6 | +0.0 / +0.5 | -0.5 / +0.8 | -0.1 / -1.4 | -0.5 / -1.0 |
| pday | 2 trend strength | +0.6 / +0.1 | +1.5 / -0.1 | +1.0 / -4.5 | +0.9 / +1.4 | +0.4 / +0.4 |
| pday | 3 oscillator | -1.0 / -1.1 | +1.3 / +1.3 | +2.7 / -3.7 | -5.4 / +2.0 | -0.4 / -0.6 |
| pday | 4 participation | +0.5 / -0.8 | +2.4 / -0.4 | -4.0 / -1.2 | +9.4 / -3.2 | -1.2 / +0.9 |
| pday | 5 squeeze release | -0.4 / +1.4 | -1.0 / -1.4 | +0.0 / -0.0 | +3.4 / +0.9 | -1.2 / -0.3 |
| pday | 6 HTF alignment | -0.0 / -0.8 | +1.6 / +2.5 | +1.1 / +1.3 | -3.3 / +2.4 | +2.8 / -1.1 |
| pday | 7 leverage (OI) | -1.2 / +2.2 | - | - | - | - |
| roll24 | 1 speed | -0.1 / +0.2 | +0.8 / +0.1 | -0.8 / +1.2 | +1.2 / +1.0 | -0.4 / -0.6 |
| roll24 | 2 trend strength | +0.1 / -0.2 | +1.9 / -0.9 | +0.9 / -1.9 | +3.7 / +3.5 | +0.6 / +0.5 |
| roll24 | 3 oscillator | -0.6 / -0.1 | -0.4 / +0.6 | +1.7 / -1.2 | -3.0 / +0.7 | -0.2 / +0.7 |
| roll24 | 4 participation | +1.0 / +1.6 | +2.0 / +1.8 | -0.2 / -0.3 | +5.0 / +1.4 | +0.9 / +0.8 |
| roll24 | 5 squeeze release | -0.5 / +1.7 | -0.9 / +0.1 | -1.0 / +2.7 | +4.7 / -0.4 | -0.1 / +1.1 |
| roll24 | 6 HTF alignment | +0.9 / +1.5 | -0.9 / +2.8 | -0.2 / +3.2 | -1.7 / +0.6 | +2.7 / +0.0 |
| roll24 | 7 leverage (OI) | +0.4 / +1.0 | - | - | - | - |

## After costs: the top buckets traded (stop -0.5 dATR, target +0.5 dATR, 72 h max, own fee a side, one position per market)

| level | bucket | half | trades | won | R before costs | R after costs | per trade (% stake) | net $ |
|---|---|---|---|---|---|---|---|---|
| pday | trend+htf | first | 2148 | 51.4% | +0.026 | -0.037 | -0.1016% | -21,826 |
|  |  | second | 1448 | 51.9% | +0.038 | -0.041 | -0.0878% | -12,709 |
| roll24 | trend+htf | first | 2268 | 51.1% | +0.019 | -0.044 | -0.1261% | -28,589 |
|  |  | second | 1519 | 52.7% | +0.060 | -0.018 | -0.0643% | -9,771 |
| roll24 | count>=5 | first | 1773 | 50.4% | +0.008 | -0.061 | -0.1795% | -31,821 |
|  |  | second | 1188 | 52.6% | +0.059 | -0.029 | -0.0757% | -8,997 |
| roll24 | squeeze+htf | first | 1537 | 50.5% | +0.012 | -0.053 | -0.1366% | -20,993 |
|  |  | second | 965 | 53.8% | +0.080 | +0.003 | -0.0454% | -4,378 |
| roll24 | part+htf | first | 1228 | 50.4% | +0.006 | -0.064 | -0.1514% | -18,596 |
|  |  | second | 793 | 53.3% | +0.080 | -0.009 | -0.0515% | -4,085 |
| pday | osc+htf | first | 2014 | 50.4% | +0.012 | -0.052 | -0.1141% | -22,987 |
|  |  | second | 1348 | 51.5% | +0.034 | -0.043 | -0.1077% | -14,518 |
| roll24 | trend+part | first | 2025 | 49.8% | +0.004 | -0.065 | -0.2201% | -44,573 |
|  |  | second | 1396 | 51.5% | +0.042 | -0.046 | -0.0831% | -11,604 |
| roll24 | speed+trend | first | 4170 | 49.5% | -0.001 | -0.065 | -0.1819% | -75,861 |
|  |  | second | 2831 | 50.3% | +0.016 | -0.062 | -0.0985% | -27,889 |
| roll24 | trend | first | 4649 | 49.8% | +0.002 | -0.061 | -0.1680% | -78,097 |
|  |  | second | 3273 | 49.9% | +0.008 | -0.068 | -0.1054% | -34,494 |
| pday | htf | first | 2941 | 50.4% | +0.006 | -0.057 | -0.1043% | -30,681 |
|  |  | second | 2067 | 51.1% | +0.028 | -0.050 | -0.0968% | -20,000 |

Per market, second half (per trade after costs, trades; events per month in brackets):

| level | bucket | BTCUSDT | ETHUSDT | XAUUSD | XAGUSD | USDJPY | SPX | WTI | BRENT |
|---|---|---|---|---|---|---|---|---|---|
| pday | trend+htf | -0.335% (233) [9.2] | -0.135% (232) [9.0] | +0.035% (179) [6.8] | -0.126% (162) [6.1] | +0.014% (176) [6.9] | +0.015% (142) [5.6] | -0.008% (168) [6.4] | -0.043% (156) [6.1] |
| roll24 | trend+htf | -0.231% (239) [9.8] | -0.108% (247) [9.6] | +0.019% (196) [7.4] | -0.106% (170) [6.5] | +0.032% (191) [7.5] | +0.016% (129) [5.1] | +0.077% (177) [6.9] | -0.137% (170) [6.7] |
| roll24 | count>=5 | -0.161% (334) [13.2] | -0.095% (350) [13.2] | +0.070% (109) [3.9] | -0.032% (93) [3.3] | +0.053% (76) [2.8] | -0.029% (53) [1.8] | +0.040% (93) [3.4] | -0.172% (80) [2.8] |
| roll24 | squeeze+htf | -0.151% (135) [5.1] | -0.161% (136) [5.0] | +0.093% (143) [5.2] | -0.192% (122) [4.4] | +0.056% (124) [4.8] | +0.044% (83) [3.0] | +0.126% (118) [4.3] | -0.160% (104) [3.8] |
| roll24 | part+htf | -0.066% (221) [8.7] | -0.072% (249) [9.4] | +0.108% (76) [2.6] | -0.081% (60) [2.2] | +0.034% (51) [1.8] | +0.081% (15) [0.6] | -0.158% (69) [2.5] | -0.072% (52) [2.1] |
| pday | osc+htf | -0.279% (191) [7.4] | -0.300% (196) [7.3] | +0.073% (183) [6.9] | -0.208% (159) [6.0] | +0.033% (157) [6.6] | +0.001% (132) [5.7] | -0.072% (174) [6.7] | -0.039% (156) [6.1] |
| roll24 | trend+part | -0.140% (405) [16.2] | -0.089% (426) [16.8] | +0.017% (119) [4.1] | -0.115% (116) [4.2] | -0.014% (76) [2.7] | -0.038% (36) [1.2] | -0.036% (120) [4.3] | -0.033% (98) [3.8] |
| roll24 | speed+trend | -0.161% (478) [21.9] | -0.122% (489) [21.2] | -0.034% (362) [13.6] | -0.147% (333) [12.4] | +0.003% (339) [13.7] | -0.023% (153) [5.5] | -0.069% (363) [14.2] | -0.170% (314) [12.2] |
| roll24 | trend | -0.180% (505) [23.9] | -0.170% (505) [22.5] | -0.041% (412) [16.2] | -0.127% (410) [15.9] | -0.007% (399) [16.9] | -0.020% (205) [7.8] | -0.077% (438) [18.2] | -0.146% (399) [16.6] |
| pday | htf | -0.279% (284) [11.5] | -0.194% (279) [11.0] | +0.042% (277) [10.8] | -0.156% (265) [10.2] | +0.028% (255) [11.1] | -0.006% (253) [10.2] | -0.099% (245) [9.7] | -0.088% (209) [8.5] |

Per market, first half:

| level | bucket | BTCUSDT | ETHUSDT | XAUUSD | XAGUSD | USDJPY | SPX | WTI | BRENT |
|---|---|---|---|---|---|---|---|---|---|
| pday | trend+htf | -0.312% (338) [9.3] | -0.427% (345) [9.5] | -0.005% (253) [6.9] | -0.025% (246) [6.8] | -0.009% (257) [7.1] | -0.166% (202) [5.3] | +0.085% (275) [7.7] | +0.234% (232) [6.7] |
| roll24 | trend+htf | -0.339% (370) [10.2] | -0.423% (380) [10.5] | -0.042% (273) [7.4] | +0.017% (255) [7.1] | -0.002% (258) [7.1] | -0.123% (185) [5.0] | -0.065% (292) [7.9] | +0.196% (255) [7.4] |
| roll24 | count>=5 | -0.417% (517) [14.4] | -0.236% (447) [12.5] | -0.084% (146) [3.6] | -0.070% (159) [4.1] | +0.002% (148) [3.7] | -0.148% (74) [1.9] | -0.067% (155) [4.0] | +0.373% (127) [3.3] |
| roll24 | squeeze+htf | -0.465% (256) [6.7] | -0.366% (261) [7.1] | -0.065% (183) [4.8] | -0.013% (176) [4.7] | -0.019% (194) [5.2] | -0.098% (119) [3.1] | +0.015% (185) [4.9] | +0.193% (163) [4.3] |
| roll24 | part+htf | -0.276% (348) [9.5] | -0.252% (353) [9.9] | -0.071% (93) [2.3] | -0.072% (105) [2.7] | +0.010% (97) [2.4] | -0.805% (23) [0.6] | -0.100% (118) [3.1] | +0.468% (91) [2.4] |
| pday | osc+htf | -0.469% (299) [8.4] | -0.355% (315) [8.8] | -0.034% (228) [6.2] | -0.027% (215) [6.0] | +0.004% (251) [7.2] | -0.183% (202) [5.6] | +0.037% (266) [7.7] | +0.261% (238) [6.9] |
| roll24 | trend+part | -0.331% (591) [17.1] | -0.374% (607) [17.8] | +0.005% (122) [3.1] | +0.040% (182) [4.7] | +0.010% (156) [3.8] | -0.121% (51) [1.2] | -0.186% (170) [4.3] | +0.034% (146) [3.8] |
| roll24 | speed+trend | -0.423% (726) [22.4] | -0.465% (710) [22.2] | -0.015% (498) [13.6] | -0.025% (501) [13.8] | -0.001% (515) [14.3] | -0.096% (250) [6.4] | -0.045% (523) [14.3] | -0.120% (447) [12.7] |
| roll24 | trend | -0.413% (747) [23.6] | -0.433% (744) [23.7] | -0.026% (568) [16.1] | -0.044% (563) [16.0] | +0.005% (574) [16.6] | -0.075% (310) [8.2] | -0.060% (614) [17.4] | -0.101% (529) [16.1] |
| pday | htf | -0.319% (399) [11.3] | -0.341% (415) [11.9] | -0.034% (374) [10.5] | -0.061% (346) [10.0] | -0.011% (360) [10.7] | -0.143% (348) [9.8] | +0.044% (386) [11.4] | +0.104% (313) [9.3] |

## Every bucket, pooled (sorted by the lower half's hit rate; then the rest)

### pday

| bucket | first: hit | n | p | second: hit | n | p | Bonferroni both |
|---|---|---|---|---|---|---|---|
| trend+htf | 51.4% | 2337 (106 unres.) | 0.172 | 51.5% | 1567 (70 unres.) | 0.245 |  |
| osc+htf | 50.1% | 2223 (113 unres.) | 0.966 | 50.9% | 1452 (80 unres.) | 0.512 |  |
| htf | 50.0% | 3329 (170 unres.) | 1.000 | 50.6% | 2312 (111 unres.) | 0.574 |  |
| count>=5 | 49.8% | 1747 (61 unres.) | 0.886 | 50.8% | 1185 (38 unres.) | 0.601 |  |
| squeeze+htf | 49.8% | 1523 (80 unres.) | 0.878 | 51.7% | 990 (51 unres.) | 0.294 |  |
| trend | 50.0% | 4893 (258 unres.) | 0.954 | 49.8% | 3435 (167 unres.) | 0.785 |  |
| speed+htf | 49.7% | 2755 (119 unres.) | 0.790 | 50.5% | 1858 (73 unres.) | 0.659 |  |
| count>=3 | 49.6% | 5255 (274 unres.) | 0.544 | 49.8% | 3654 (176 unres.) | 0.804 |  |
| trend+part | 49.6% | 1947 (62 unres.) | 0.717 | 49.9% | 1328 (50 unres.) | 0.978 |  |
| count>=4 | 49.4% | 3512 (150 unres.) | 0.510 | 50.1% | 2401 (104 unres.) | 0.903 |  |
| speed+trend | 49.9% | 4102 (202 unres.) | 0.938 | 49.3% | 2773 (112 unres.) | 0.494 |  |
| part | 49.2% | 2601 (79 unres.) | 0.433 | 49.8% | 1819 (63 unres.) | 0.851 |  |
| trend+osc | 49.5% | 3366 (179 unres.) | 0.570 | 49.1% | 2309 (130 unres.) | 0.405 |  |
| part+htf | 49.1% | 1222 (26 unres.) | 0.548 | 50.8% | 836 (24 unres.) | 0.653 |  |
| osc | 49.0% | 3941 (213 unres.) | 0.226 | 49.5% | 2714 (160 unres.) | 0.604 |  |
| speed | 48.9% | 5795 (285 unres.) | 0.109 | 49.8% | 3988 (166 unres.) | 0.788 |  |
| speed+part | 48.9% | 2480 (70 unres.) | 0.287 | 49.8% | 1707 (58 unres.) | 0.885 |  |
| part+squeeze | 48.9% | 1278 (42 unres.) | 0.450 | 50.6% | 774 (31 unres.) | 0.746 |  |
| squeeze | 48.8% | 3147 (173 unres.) | 0.175 | 50.0% | 2038 (107 unres.) | 0.982 |  |
| speed+osc | 48.6% | 3291 (157 unres.) | 0.125 | 49.0% | 2170 (105 unres.) | 0.356 |  |
| speed+squeeze | 48.2% | 2773 (142 unres.) | 0.063 | 50.2% | 1716 (82 unres.) | 0.904 |  |
| trend+squeeze | 49.9% | 2186 (117 unres.) | 0.915 | 48.1% | 1392 (73 unres.) | 0.172 |  |
| osc+squeeze | 48.5% | 1770 (94 unres.) | 0.225 | 48.0% | 1105 (69 unres.) | 0.186 |  |
| osc+part | 47.8% | 1582 (48 unres.) | 0.083 | 50.1% | 1021 (41 unres.) | 0.950 |  |
| squeeze+lev | 47.8% | 377 (15 unres.) | 0.410 | 54.6% | 326 (13 unres.) | 0.108 |  |
| trend+lev | 47.6% | 611 (22 unres.) | 0.257 | 53.2% | 658 (16 unres.) | 0.110 |  |
| speed+lev | 47.2% | 674 (20 unres.) | 0.154 | 52.0% | 721 (17 unres.) | 0.297 |  |
| htf+lev | 47.0% | 383 (8 unres.) | 0.261 | 52.3% | 430 (7 unres.) | 0.360 |  |
| lev | 46.7% | 726 (24 unres.) | 0.081 | 53.4% | 791 (20 unres.) | 0.064 |  |
| part+lev | 46.5% | 544 (13 unres.) | 0.113 | 51.2% | 568 (10 unres.) | 0.585 |  |
| all | 45.7% | 302 (7 unres.) | 0.150 | 54.9% | 133 (8 unres.) | 0.298 |  |
| osc+lev | 44.9% | 492 (16 unres.) | 0.027 | 52.1% | 514 (13 unres.) | 0.354 |  |

### roll24

| bucket | first: hit | n | p | second: hit | n | p | Bonferroni both |
|---|---|---|---|---|---|---|---|
| trend+htf | 51.0% | 2466 (117 unres.) | 0.324 | 53.1% | 1664 (72 unres.) | 0.013 |  |
| count>=5 | 50.4% | 1890 (63 unres.) | 0.730 | 53.2% | 1251 (42 unres.) | 0.024 |  |
| squeeze+htf | 50.2% | 1603 (74 unres.) | 0.920 | 53.9% | 991 (49 unres.) | 0.016 |  |
| part+htf | 50.1% | 1318 (33 unres.) | 0.934 | 53.8% | 846 (23 unres.) | 0.030 |  |
| trend+part | 50.1% | 2229 (73 unres.) | 0.966 | 51.6% | 1511 (44 unres.) | 0.237 |  |
| speed+trend | 50.1% | 4678 (253 unres.) | 0.942 | 50.0% | 3223 (130 unres.) | 0.972 |  |
| trend | 50.1% | 5372 (303 unres.) | 0.902 | 50.0% | 3849 (179 unres.) | 1.000 |  |
| trend+squeeze | 49.9% | 2517 (138 unres.) | 0.968 | 50.4% | 1594 (78 unres.) | 0.783 |  |
| count>=4 | 49.9% | 3929 (163 unres.) | 0.898 | 51.4% | 2683 (95 unres.) | 0.165 |  |
| trend+osc | 49.8% | 3467 (171 unres.) | 0.865 | 50.3% | 2440 (119 unres.) | 0.761 |  |
| speed+htf | 49.8% | 2895 (126 unres.) | 0.853 | 52.5% | 1930 (73 unres.) | 0.027 |  |
| htf | 49.8% | 3351 (164 unres.) | 0.782 | 52.0% | 2278 (105 unres.) | 0.057 |  |
| part | 49.7% | 2931 (99 unres.) | 0.768 | 51.5% | 2006 (59 unres.) | 0.188 |  |
| all | 49.7% | 306 (9 unres.) | 0.954 | 55.8% | 138 (6 unres.) | 0.201 |  |
| part+squeeze | 49.6% | 1510 (53 unres.) | 0.777 | 52.3% | 889 (30 unres.) | 0.180 |  |
| osc+htf | 49.6% | 2231 (106 unres.) | 0.703 | 53.1% | 1460 (73 unres.) | 0.017 |  |
| speed+part | 49.5% | 2844 (92 unres.) | 0.639 | 51.5% | 1911 (56 unres.) | 0.200 |  |
| htf+lev | 49.5% | 420 (6 unres.) | 0.884 | 51.4% | 467 (9 unres.) | 0.579 |  |
| osc+part | 49.4% | 1619 (49 unres.) | 0.655 | 52.5% | 1042 (35 unres.) | 0.114 |  |
| count>=3 | 49.4% | 5756 (289 unres.) | 0.363 | 50.5% | 4081 (184 unres.) | 0.552 |  |
| speed | 49.2% | 6241 (337 unres.) | 0.215 | 50.4% | 4322 (185 unres.) | 0.574 |  |
| part+lev | 49.0% | 635 (14 unres.) | 0.634 | 52.0% | 673 (12 unres.) | 0.316 |  |
| speed+osc | 49.0% | 3440 (158 unres.) | 0.239 | 50.5% | 2309 (104 unres.) | 0.647 |  |
| osc | 48.9% | 4003 (201 unres.) | 0.174 | 50.4% | 2812 (147 unres.) | 0.692 |  |
| squeeze | 48.9% | 3365 (183 unres.) | 0.202 | 51.4% | 2190 (110 unres.) | 0.207 |  |
| osc+squeeze | 48.9% | 1860 (97 unres.) | 0.342 | 50.7% | 1184 (62 unres.) | 0.663 |  |
| speed+squeeze | 48.8% | 3080 (160 unres.) | 0.177 | 51.5% | 1941 (94 unres.) | 0.188 |  |
| trend+lev | 48.2% | 714 (18 unres.) | 0.349 | 51.0% | 745 (15 unres.) | 0.608 |  |
| squeeze+lev | 48.0% | 479 (12 unres.) | 0.411 | 54.3% | 383 (15 unres.) | 0.102 |  |
| lev | 48.0% | 857 (20 unres.) | 0.245 | 51.1% | 930 (24 unres.) | 0.533 |  |
| speed+lev | 47.9% | 822 (20 unres.) | 0.250 | 51.3% | 865 (23 unres.) | 0.454 |  |
| osc+lev | 46.8% | 491 (11 unres.) | 0.176 | 50.0% | 506 (11 unres.) | 1.000 |  |

## Every bucket per market group (top 8 by the lower half, then any passing Bonferroni in both halves)

### pday, crypto

| bucket | first: hit | n | p | second: hit | n | p | Bonferroni both |
|---|---|---|---|---|---|---|---|
| trend+part | 49.0% | 1150 (27 unres.) | 0.498 | 50.1% | 774 (21 unres.) | 0.971 |  |
| trend | 48.6% | 1569 (46 unres.) | 0.267 | 51.3% | 1094 (33 unres.) | 0.414 |  |
| speed+trend | 48.4% | 1425 (37 unres.) | 0.244 | 50.5% | 992 (26 unres.) | 0.775 |  |
| part+htf | 48.4% | 690 (8 unres.) | 0.424 | 50.5% | 471 (12 unres.) | 0.854 |  |
| part | 48.4% | 1432 (31 unres.) | 0.234 | 50.4% | 975 (26 unres.) | 0.848 |  |
| speed+part | 48.3% | 1411 (30 unres.) | 0.221 | 50.2% | 957 (24 unres.) | 0.948 |  |
| trend+squeeze | 48.2% | 768 (27 unres.) | 0.330 | 50.7% | 428 (18 unres.) | 0.809 |  |
| count>=5 | 48.2% | 982 (26 unres.) | 0.264 | 50.1% | 709 (20 unres.) | 1.000 |  |

### pday, metals

| bucket | first: hit | n | p | second: hit | n | p | Bonferroni both |
|---|---|---|---|---|---|---|---|
| osc+part | 51.3% | 230 (10 unres.) | 0.742 | 55.5% | 164 (9 unres.) | 0.184 |  |
| trend+htf | 52.0% | 538 (24 unres.) | 0.365 | 51.2% | 363 (12 unres.) | 0.675 |  |
| count>=5 | 50.0% | 284 (10 unres.) | 1.000 | 54.2% | 190 (5 unres.) | 0.276 |  |
| squeeze+htf | 50.8% | 370 (15 unres.) | 0.795 | 49.8% | 269 (8 unres.) | 1.000 |  |
| osc+htf | 49.7% | 487 (16 unres.) | 0.928 | 52.0% | 367 (10 unres.) | 0.465 |  |
| htf | 49.4% | 818 (29 unres.) | 0.753 | 51.4% | 595 (19 unres.) | 0.512 |  |
| speed+part | 49.2% | 400 (14 unres.) | 0.803 | 49.5% | 305 (12 unres.) | 0.909 |  |
| count>=3 | 49.2% | 1184 (61 unres.) | 0.621 | 49.4% | 860 (37 unres.) | 0.759 |  |

### pday, fx

| bucket | first: hit | n | p | second: hit | n | p | Bonferroni both |
|---|---|---|---|---|---|---|---|
| osc+htf | 57.4% | 277 (20 unres.) | 0.016 | 54.6% | 172 (20 unres.) | 0.253 |  |
| htf | 54.3% | 418 (22 unres.) | 0.087 | 54.5% | 297 (26 unres.) | 0.131 |  |
| squeeze | 53.3% | 411 (21 unres.) | 0.200 | 53.2% | 246 (18 unres.) | 0.339 |  |
| speed+htf | 52.8% | 356 (21 unres.) | 0.314 | 56.8% | 236 (16 unres.) | 0.043 |  |
| speed | 52.8% | 758 (42 unres.) | 0.136 | 54.1% | 510 (26 unres.) | 0.069 |  |
| trend+htf | 54.7% | 274 (17 unres.) | 0.131 | 52.4% | 185 (17 unres.) | 0.557 |  |
| speed+squeeze | 52.0% | 356 (19 unres.) | 0.491 | 53.3% | 212 (14 unres.) | 0.372 |  |
| speed+osc | 54.6% | 432 (31 unres.) | 0.060 | 51.2% | 256 (17 unres.) | 0.755 |  |

### pday, index

| bucket | first: hit | n | p | second: hit | n | p | Bonferroni both |
|---|---|---|---|---|---|---|---|
| trend+squeeze | 55.1% | 156 (14 unres.) | 0.230 | 52.5% | 118 (8 unres.) | 0.645 |  |
| squeeze+htf | 50.0% | 142 (30 unres.) | 1.000 | 55.0% | 111 (12 unres.) | 0.343 |  |
| squeeze | 51.5% | 295 (42 unres.) | 0.641 | 50.0% | 204 (18 unres.) | 1.000 |  |
| trend | 49.0% | 412 (42 unres.) | 0.730 | 50.5% | 289 (23 unres.) | 0.906 |  |
| speed+squeeze | 50.6% | 251 (31 unres.) | 0.900 | 48.9% | 176 (12 unres.) | 0.821 |  |
| count>=4 | 48.5% | 194 (20 unres.) | 0.720 | 54.4% | 147 (11 unres.) | 0.322 |  |
| speed+trend | 48.0% | 333 (31 unres.) | 0.511 | 49.8% | 219 (12 unres.) | 1.000 |  |
| trend+htf | 48.0% | 200 (20 unres.) | 0.621 | 56.3% | 151 (12 unres.) | 0.143 |  |

### pday, energy

| bucket | first: hit | n | p | second: hit | n | p | Bonferroni both |
|---|---|---|---|---|---|---|---|
| trend+htf | 55.7% | 564 (29 unres.) | 0.008 | 51.0% | 351 (15 unres.) | 0.749 |  |
| trend+part | 49.5% | 305 (13 unres.) | 0.909 | 51.7% | 205 (13 unres.) | 0.675 |  |
| part | 49.0% | 433 (22 unres.) | 0.701 | 49.3% | 296 (14 unres.) | 0.862 |  |
| trend | 50.6% | 1165 (74 unres.) | 0.725 | 48.8% | 836 (51 unres.) | 0.511 |  |
| trend+osc | 49.9% | 851 (52 unres.) | 1.000 | 48.7% | 596 (36 unres.) | 0.539 |  |
| osc+htf | 54.4% | 566 (34 unres.) | 0.039 | 48.5% | 355 (16 unres.) | 0.596 |  |
| count>=4 | 50.1% | 718 (33 unres.) | 0.970 | 48.4% | 444 (27 unres.) | 0.537 |  |
| count>=5 | 55.4% | 267 (9 unres.) | 0.086 | 48.2% | 168 (5 unres.) | 0.700 |  |

### roll24, crypto

| bucket | first: hit | n | p | second: hit | n | p | Bonferroni both |
|---|---|---|---|---|---|---|---|
| htf+lev | 49.5% | 420 (6 unres.) | 0.884 | 51.4% | 467 (9 unres.) | 0.579 |  |
| part+htf | 49.4% | 780 (17 unres.) | 0.747 | 53.9% | 516 (12 unres.) | 0.086 |  |
| part+lev | 49.0% | 635 (14 unres.) | 0.634 | 52.0% | 673 (12 unres.) | 0.316 |  |
| count>=5 | 48.8% | 1077 (28 unres.) | 0.465 | 52.5% | 748 (20 unres.) | 0.176 |  |
| osc+part | 48.8% | 959 (25 unres.) | 0.477 | 51.8% | 635 (16 unres.) | 0.383 |  |
| speed+part | 48.6% | 1743 (49 unres.) | 0.250 | 51.7% | 1172 (27 unres.) | 0.255 |  |
| part | 48.5% | 1766 (50 unres.) | 0.225 | 51.8% | 1200 (28 unres.) | 0.237 |  |
| trend+part | 48.5% | 1399 (40 unres.) | 0.285 | 51.6% | 945 (19 unres.) | 0.329 |  |

### roll24, metals

| bucket | first: hit | n | p | second: hit | n | p | Bonferroni both |
|---|---|---|---|---|---|---|---|
| trend+part | 53.9% | 308 (11 unres.) | 0.190 | 51.5% | 233 (8 unres.) | 0.694 |  |
| trend+htf | 50.9% | 572 (26 unres.) | 0.707 | 51.9% | 397 (8 unres.) | 0.482 |  |
| part | 50.6% | 423 (14 unres.) | 0.846 | 51.7% | 331 (12 unres.) | 0.583 |  |
| count>=4 | 50.8% | 758 (28 unres.) | 0.690 | 50.5% | 568 (17 unres.) | 0.834 |  |
| osc+part | 50.2% | 231 (7 unres.) | 1.000 | 54.9% | 162 (7 unres.) | 0.239 |  |
| speed+part | 50.0% | 412 (14 unres.) | 1.000 | 51.6% | 310 (12 unres.) | 0.609 |  |
| squeeze+htf | 49.7% | 376 (14 unres.) | 0.959 | 53.1% | 275 (5 unres.) | 0.335 |  |
| trend+osc | 49.8% | 794 (38 unres.) | 0.915 | 49.6% | 579 (28 unres.) | 0.868 |  |

### roll24, fx

| bucket | first: hit | n | p | second: hit | n | p | Bonferroni both |
|---|---|---|---|---|---|---|---|
| osc+htf | 57.0% | 270 (19 unres.) | 0.024 | 58.2% | 177 (17 unres.) | 0.035 |  |
| trend+htf | 56.1% | 278 (16 unres.) | 0.048 | 57.8% | 204 (16 unres.) | 0.030 |  |
| count>=4 | 54.9% | 423 (24 unres.) | 0.052 | 55.6% | 257 (13 unres.) | 0.081 |  |
| htf | 54.6% | 401 (21 unres.) | 0.072 | 57.4% | 298 (25 unres.) | 0.013 |  |
| speed+part | 54.4% | 217 (11 unres.) | 0.222 | 54.4% | 114 (5 unres.) | 0.399 |  |
| speed+osc | 55.7% | 436 (28 unres.) | 0.019 | 54.1% | 281 (17 unres.) | 0.189 |  |
| speed | 54.1% | 773 (49 unres.) | 0.026 | 55.4% | 545 (31 unres.) | 0.013 |  |
| osc+squeeze | 53.9% | 241 (13 unres.) | 0.246 | 54.4% | 136 (13 unres.) | 0.346 |  |

### roll24, index

| bucket | first: hit | n | p | second: hit | n | p | Bonferroni both |
|---|---|---|---|---|---|---|---|
| speed+squeeze | 52.7% | 146 (14 unres.) | 0.563 | 53.5% | 101 (11 unres.) | 0.551 |  |
| speed+trend | 51.2% | 240 (24 unres.) | 0.747 | 56.7% | 150 (11 unres.) | 0.121 |  |
| squeeze | 51.2% | 168 (19 unres.) | 0.817 | 52.1% | 117 (12 unres.) | 0.712 |  |
| trend | 50.2% | 305 (34 unres.) | 1.000 | 56.1% | 205 (23 unres.) | 0.093 |  |
| trend+htf | 49.5% | 182 (24 unres.) | 0.941 | 57.6% | 132 (16 unres.) | 0.098 |  |
| speed | 47.7% | 331 (33 unres.) | 0.442 | 53.6% | 224 (22 unres.) | 0.316 |  |
| count>=3 | 47.1% | 325 (35 unres.) | 0.318 | 54.2% | 214 (27 unres.) | 0.245 |  |
| count>=4 | 47.1% | 204 (20 unres.) | 0.441 | 56.0% | 134 (10 unres.) | 0.195 |  |

### roll24, energy

| bucket | first: hit | n | p | second: hit | n | p | Bonferroni both |
|---|---|---|---|---|---|---|---|
| trend+htf | 53.8% | 599 (31 unres.) | 0.072 | 51.7% | 379 (18 unres.) | 0.538 |  |
| squeeze+htf | 54.9% | 357 (22 unres.) | 0.072 | 51.3% | 228 (10 unres.) | 0.741 |  |
| trend+part | 50.9% | 320 (15 unres.) | 0.780 | 50.7% | 223 (13 unres.) | 0.893 |  |
| count>=5 | 55.8% | 287 (12 unres.) | 0.059 | 50.6% | 176 (5 unres.) | 0.940 |  |
| osc+squeeze | 53.4% | 427 (28 unres.) | 0.175 | 50.5% | 319 (19 unres.) | 0.911 |  |
| count>=4 | 51.2% | 775 (43 unres.) | 0.518 | 50.2% | 492 (26 unres.) | 0.964 |  |
| osc+part | 49.8% | 269 (10 unres.) | 1.000 | 52.1% | 169 (9 unres.) | 0.645 |  |
| trend+osc | 50.1% | 888 (48 unres.) | 0.973 | 49.8% | 669 (33 unres.) | 0.938 |  |

## Checks

- BTCUSDT: 240306 bars (2019-01-01 00:00 to 2025-11-10 23:45), fee 0.10% a side, OI rows 181908; excluded pday no_entry_same_day 7, before_start 253, open_at_seal 1; roll24 no_entry_same_day 10, before_start 304, open_at_seal 1; truncation 2 cuts, 6921 events compared, 0 mismatched event runs, 0 mismatched flag arrays.
- ETHUSDT: 240306 bars (2019-01-01 00:00 to 2025-11-10 23:45), fee 0.10% a side, OI rows 138290; excluded pday no_entry_same_day 6, before_start 260, open_at_seal 1; roll24 no_entry_same_day 14, before_start 307, open_at_seal 0; truncation 2 cuts, 6907 events compared, 0 mismatched event runs, 0 mismatched flag arrays.
- XAUUSD: 162247 bars (2019-01-01 23:00 to 2025-11-10 23:45), fee 0.02% a side, OI rows 0; excluded pday no_entry_same_day 4, before_start 250, open_at_seal 0; roll24 no_entry_same_day 3, before_start 249, open_at_seal 0; truncation 2 cuts, 5747 events compared, 0 mismatched event runs, 0 mismatched flag arrays.
- XAGUSD: 162216 bars (2019-01-01 23:00 to 2025-11-10 23:45), fee 0.03% a side, OI rows 0; excluded pday no_entry_same_day 4, before_start 252, open_at_seal 0; roll24 no_entry_same_day 5, before_start 230, open_at_seal 0; truncation 2 cuts, 5670 events compared, 0 mismatched event runs, 0 mismatched flag arrays.
- USDJPY: 171130 bars (2019-01-01 22:00 to 2025-11-10 23:45), fee 0.01% a side, OI rows 0; excluded pday no_entry_same_day 9, before_start 250, open_at_seal 1; roll24 no_entry_same_day 16, before_start 264, open_at_seal 1; truncation 2 cuts, 5911 events compared, 0 mismatched event runs, 0 mismatched flag arrays.
- SPX: 44687 bars (2019-01-02 14:30 to 2025-11-10 20:45), fee 0.02% a side, OI rows 0; excluded pday no_entry_same_day 39, before_start 206, open_at_seal 0; roll24 no_entry_same_day 35, before_start 115, open_at_seal 1; truncation 2 cuts, 4022 events compared, 0 mismatched event runs, 0 mismatched flag arrays.
- WTI: 161931 bars (2019-01-01 23:00 to 2025-11-10 23:45), fee 0.04% a side, OI rows 0; excluded pday no_entry_same_day 5, before_start 270, open_at_seal 2; roll24 no_entry_same_day 7, before_start 250, open_at_seal 0; truncation 2 cuts, 6125 events compared, 0 mismatched event runs, 0 mismatched flag arrays.
- BRENT: 147959 bars (2019-01-02 01:00 to 2025-11-10 21:45), fee 0.04% a side, OI rows 0; excluded pday no_entry_same_day 3, before_start 203, open_at_seal 0; roll24 no_entry_same_day 6, before_start 228, open_at_seal 0; truncation 2 cuts, 5305 events compared, 0 mismatched event runs, 0 mismatched flag arrays.

Group 7 (open interest) uses Binance archive snapshots that the live engine only sees ~12-36 h later; it describes a live OI feed the engine does not have. Non-crypto volume changes source at each market's join (VOLUME_NOTE); USDJPY has no volume after its join, so group 4 rarely reads there.
