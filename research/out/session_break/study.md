# H48: FX daily-break continuation and session-range breakouts

PAPER RESEARCH ONLY. Registered 2026-11-16 05:55 UTC (`research/HYPOTHESES.md` H48) before any outcome. Development data only (rows before 2025-11-11 00:00 UTC; the holdout was not read). Events with entry from 2020-01-01; first half before 2023-06-07. Written 2026-11-16 05:53 UTC.

Outcome = +0.5 daily ATR in the break direction before -0.5 daily ATR from the next 15m open (A: within 72 h, H46's code; B: within the same UTC day). A bar touching both = miss; neither = unresolved, excluded. Hit rate = hits / resolved; a coin flip is ~50%. p = exact two-sided binomial against 50%. Tests per half: **33** (each variant's pooled cell + one per market); Bonferroni threshold p < 1.52e-03. Trade: next open, stop and target 0.5 daily ATR, out after 72 h (A) or at the close of the UTC day's last bar (B), one position per market, $10,000, own fee a side.

## Verdict: NO PASS

| id | rule | markets | 1st: hit | n | p | 2nd: hit | n | p | hit>=55 both | n>=200 both | p both | net 2nd pooled > 0 | markets net > 0 (2nd) | PASS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | first 15m close beyond the prior UTC day's high/low; 72 h | USDJPY, USDSGD | 49.7% | 1803 (71 unres.) | 0.814 | 51.6% | 1218 (65 unres.) | 0.264 | no | yes | no | no | 1 of 2 (need 2): USDJPY | **no** |
| A2 | first 15m close beyond the previous 96 bars' high/low; 72 h | USDJPY, USDSGD | 50.4% | 1858 (92 unres.) | 0.763 | 51.6% | 1272 (81 unres.) | 0.274 | no | yes | no | no | 1 of 2 (need 2): USDJPY | **no** |
| B1 | range 00:00-07:00 UTC broken by the first close in 07:00-10:00 UTC; rest of the UTC day | USDJPY, USDSGD, XAUUSD, XAGUSD, WTI, BRENT | 49.5% | 2719 (1076 unres.) | 0.618 | 50.1% | 1944 (775 unres.) | 0.946 | no | yes | no | no | 1 of 6 (need 4): USDJPY | **no** |
| B2 | range 00:00-13:30 UTC broken by the first close in 13:30-16:00 UTC; rest of the UTC day | USDJPY, USDSGD, XAUUSD, XAGUSD, WTI, BRENT | 53.5% | 1177 (1795 unres.) | 0.017 | 52.1% | 964 (1306 unres.) | 0.209 | no | yes | no | no | 1 of 6 (need 4): XAGUSD | **no** |
| B3 | range 07:00-13:30 UTC broken by the first close in 13:30-16:00 UTC; rest of the UTC day | USDJPY, USDSGD, XAUUSD, XAGUSD, WTI, BRENT | 53.2% | 1423 (2103 unres.) | 0.017 | 51.6% | 1138 (1564 unres.) | 0.299 | no | yes | no | no | 0 of 6 (need 4): none | **no** |
| B4 | opening range = first 30 min of the NYSE cash session, broken by a close up to open + 2 h 30; rest of the session | SPX, NDX | 49.4% | 806 (851 unres.) | 0.751 | 48.4% | 616 (587 unres.) | 0.444 | no | yes | no | no | 0 of 2 (need 2): none | **no** |
| B5 | opening range = first 60 min of the NYSE cash session, broken by a close up to open + 2 h 30; rest of the session | SPX, NDX | 48.7% | 495 (707 unres.) | 0.590 | 49.6% | 377 (493 unres.) | 0.918 | no | yes | no | no | 0 of 2 (need 2): none | **no** |

Cells passing Bonferroni in BOTH halves (any side of 50%), of 33: none.

## Per market (hit rate, resolved n, p)

| id | market | 1st: hit | n | p | 2nd: hit | n | p | all dev: hit | n | p |
|---|---|---|---|---|---|---|---|---|---|---|
| A1 | USDJPY | 53.3% | 875 (46 unres.) | 0.058 | 53.3% | 612 (40 unres.) | 0.115 | 53.3% | 1487 (86 unres.) | 0.013 |
| A1 | USDSGD | 46.3% | 928 (25 unres.) | 0.028 | 50.0% | 606 (25 unres.) | 1.000 | 47.8% | 1534 (50 unres.) | 0.087 |
| A2 | USDJPY | 54.9% | 875 (52 unres.) | 0.004 | 54.2% | 635 (44 unres.) | 0.039 | 54.6% | 1510 (96 unres.) | 4.2e-04 |
| A2 | USDSGD | 46.4% | 983 (40 unres.) | 0.026 | 49.0% | 637 (37 unres.) | 0.634 | 47.4% | 1620 (77 unres.) | 0.039 |
| B1 | USDJPY | 54.5% | 398 (175 unres.) | 0.079 | 53.1% | 226 (135 unres.) | 0.387 | 54.0% | 624 (310 unres.) | 0.050 |
| B1 | USDSGD | 46.4% | 397 (194 unres.) | 0.160 | 57.1% | 245 (127 unres.) | 0.030 | 50.5% | 642 (321 unres.) | 0.844 |
| B1 | XAUUSD | 50.7% | 454 (145 unres.) | 0.815 | 55.3% | 275 (102 unres.) | 0.091 | 52.4% | 729 (247 unres.) | 0.208 |
| B1 | XAGUSD | 47.1% | 391 (140 unres.) | 0.266 | 49.8% | 265 (103 unres.) | 1.000 | 48.2% | 656 (243 unres.) | 0.369 |
| B1 | WTI | 49.2% | 575 (165 unres.) | 0.739 | 47.2% | 508 (110 unres.) | 0.231 | 48.3% | 1083 (275 unres.) | 0.274 |
| B1 | BRENT | 49.2% | 504 (257 unres.) | 0.755 | 44.7% | 425 (198 unres.) | 0.033 | 47.1% | 929 (455 unres.) | 0.088 |
| B2 | USDJPY | 61.1% | 162 (305 unres.) | 0.006 | 55.5% | 110 (216 unres.) | 0.294 | 58.8% | 272 (521 unres.) | 0.004 |
| B2 | USDSGD | 41.0% | 144 (273 unres.) | 0.037 | 47.7% | 130 (197 unres.) | 0.661 | 44.2% | 274 (470 unres.) | 0.061 |
| B2 | XAUUSD | 54.0% | 213 (302 unres.) | 0.273 | 55.4% | 175 (208 unres.) | 0.173 | 54.6% | 388 (510 unres.) | 0.075 |
| B2 | XAGUSD | 57.8% | 199 (288 unres.) | 0.033 | 56.4% | 165 (196 unres.) | 0.119 | 57.1% | 364 (484 unres.) | 0.007 |
| B2 | WTI | 51.1% | 274 (285 unres.) | 0.763 | 49.8% | 223 (231 unres.) | 1.000 | 50.5% | 497 (516 unres.) | 0.858 |
| B2 | BRENT | 55.1% | 185 (342 unres.) | 0.186 | 48.5% | 161 (258 unres.) | 0.753 | 52.0% | 346 (600 unres.) | 0.485 |
| B3 | USDJPY | 60.9% | 189 (374 unres.) | 0.004 | 55.1% | 136 (271 unres.) | 0.265 | 58.5% | 325 (645 unres.) | 0.003 |
| B3 | USDSGD | 42.7% | 199 (344 unres.) | 0.047 | 48.8% | 164 (247 unres.) | 0.815 | 45.5% | 363 (591 unres.) | 0.093 |
| B3 | XAUUSD | 54.6% | 260 (352 unres.) | 0.154 | 52.3% | 216 (257 unres.) | 0.540 | 53.6% | 476 (609 unres.) | 0.130 |
| B3 | XAGUSD | 58.0% | 250 (343 unres.) | 0.013 | 54.8% | 199 (264 unres.) | 0.202 | 56.6% | 449 (607 unres.) | 0.006 |
| B3 | WTI | 49.8% | 315 (312 unres.) | 1.000 | 50.6% | 243 (242 unres.) | 0.898 | 50.2% | 558 (554 unres.) | 0.966 |
| B3 | BRENT | 53.8% | 210 (378 unres.) | 0.301 | 48.3% | 180 (283 unres.) | 0.709 | 51.3% | 390 (661 unres.) | 0.649 |
| B4 | SPX | 49.6% | 409 (431 unres.) | 0.921 | 48.5% | 328 (290 unres.) | 0.619 | 49.1% | 737 (721 unres.) | 0.658 |
| B4 | NDX | 49.1% | 397 (420 unres.) | 0.763 | 48.3% | 288 (297 unres.) | 0.596 | 48.8% | 685 (717 unres.) | 0.541 |
| B5 | SPX | 49.4% | 263 (346 unres.) | 0.902 | 50.5% | 200 (254 unres.) | 0.944 | 49.9% | 463 (600 unres.) | 1.000 |
| B5 | NDX | 47.8% | 232 (361 unres.) | 0.555 | 48.6% | 177 (239 unres.) | 0.764 | 48.2% | 409 (600 unres.) | 0.489 |

## After costs (stop / target 0.5 daily ATR)

| id | scope | half | trades | won | R before / after costs | per trade (% stake) | net $ |
|---|---|---|---|---|---|---|---|
| A1 | pooled | first | 1422 | 49.5% | -0.006 / -0.122 | -0.0270% | -3,845 |
| A1 | pooled | second | 977 | 50.8% | +0.029 / -0.079 | -0.0112% | -1,092 |
| A1 | USDJPY | second | 485 | 52.8% | +0.066 / +0.013 | +0.0088% | +426 |
| A1 | USDSGD | second | 492 | 48.8% | -0.009 / -0.170 | -0.0308% | -1,518 |
| A2 | pooled | first | 1526 | 49.9% | +0.003 / -0.115 | -0.0230% | -3,510 |
| A2 | pooled | second | 1032 | 49.6% | +0.007 / -0.101 | -0.0158% | -1,629 |
| A2 | USDJPY | second | 510 | 53.1% | +0.080 / +0.027 | +0.0113% | +575 |
| A2 | USDSGD | second | 522 | 46.2% | -0.065 / -0.225 | -0.0422% | -2,204 |
| B1 | pooled | first | 3662 | 47.3% | -0.013 / -0.086 | -0.0652% | -23,864 |
| B1 | pooled | second | 2604 | 47.5% | -0.007 / -0.084 | -0.0855% | -22,271 |
| B1 | USDJPY | second | 358 | 52.0% | +0.059 / +0.005 | +0.0078% | +280 |
| B1 | USDSGD | second | 368 | 49.5% | +0.071 / -0.090 | -0.0153% | -561 |
| B1 | XAUUSD | second | 372 | 47.8% | +0.046 / -0.025 | -0.0065% | -243 |
| B1 | XAGUSD | second | 366 | 47.8% | -0.015 / -0.071 | -0.0800% | -2,927 |
| B1 | WTI | second | 572 | 46.2% | -0.049 / -0.116 | -0.1411% | -8,068 |
| B1 | BRENT | second | 568 | 44.2% | -0.086 / -0.150 | -0.1893% | -10,752 |
| B2 | pooled | first | 2967 | 46.2% | +0.021 / -0.050 | -0.0298% | -8,848 |
| B2 | pooled | second | 2260 | 47.7% | +0.026 / -0.052 | -0.0254% | -5,731 |
| B2 | USDJPY | second | 326 | 47.9% | +0.042 / -0.013 | -0.0045% | -146 |
| B2 | USDSGD | second | 326 | 37.4% | -0.039 / -0.201 | -0.0363% | -1,185 |
| B2 | XAUUSD | second | 382 | 46.3% | +0.041 / -0.032 | -0.0116% | -444 |
| B2 | XAGUSD | second | 361 | 51.2% | +0.065 / +0.009 | +0.0251% | +907 |
| B2 | WTI | second | 450 | 49.8% | +0.019 / -0.048 | -0.0641% | -2,884 |
| B2 | BRENT | second | 415 | 51.8% | +0.023 / -0.041 | -0.0477% | -1,979 |
| B3 | pooled | first | 3508 | 45.8% | +0.020 / -0.052 | -0.0445% | -15,609 |
| B3 | pooled | second | 2673 | 46.7% | +0.013 / -0.065 | -0.0362% | -9,680 |
| B3 | USDJPY | second | 405 | 47.2% | +0.032 / -0.022 | -0.0056% | -229 |
| B3 | USDSGD | second | 408 | 37.7% | -0.023 / -0.185 | -0.0337% | -1,375 |
| B3 | XAUUSD | second | 468 | 44.9% | -0.003 / -0.075 | -0.0414% | -1,938 |
| B3 | XAGUSD | second | 460 | 48.0% | +0.023 / -0.032 | -0.0291% | -1,340 |
| B3 | WTI | second | 479 | 49.7% | +0.023 / -0.044 | -0.0572% | -2,739 |
| B3 | BRENT | second | 453 | 51.4% | +0.023 / -0.041 | -0.0455% | -2,059 |
| B4 | pooled | first | 1584 | 51.5% | +0.025 / -0.025 | -0.0295% | -4,670 |
| B4 | pooled | second | 1149 | 49.5% | +0.017 / -0.050 | -0.0336% | -3,866 |
| B4 | SPX | second | 582 | 50.2% | +0.033 / -0.045 | -0.0252% | -1,469 |
| B4 | NDX | second | 567 | 48.9% | +0.001 / -0.055 | -0.0423% | -2,396 |
| B5 | pooled | first | 1192 | 52.8% | +0.029 / -0.021 | -0.0183% | -2,180 |
| B5 | pooled | second | 868 | 50.0% | +0.034 / -0.034 | -0.0239% | -2,076 |
| B5 | SPX | second | 453 | 49.2% | +0.044 / -0.034 | -0.0176% | -799 |
| B5 | NDX | second | 415 | 50.8% | +0.022 / -0.033 | -0.0308% | -1,277 |

Trades a month (pooled, 1st / 2nd half): A1 34.5 / 33.5; A2 37.1 / 35.4; B1 89.0 / 89.3; B2 72.1 / 77.5; B3 85.2 / 91.6; B4 38.5 / 39.4; B5 29.0 / 29.8.

## (A) FX steadiness

### By direction

| id | scope | direction | 1st: hit | n | p | 2nd: hit | n | p |
|---|---|---|---|---|---|---|---|---|
| A1 | pooled | up | 51.1% | 956 (37 unres.) | 0.497 | 52.0% | 646 (39 unres.) | 0.325 |
| A1 | USDJPY | up | 56.4% | 482 (30 unres.) | 0.005 | 55.1% | 334 (25 unres.) | 0.071 |
| A1 | USDSGD | up | 45.8% | 474 (7 unres.) | 0.073 | 48.7% | 312 (14 unres.) | 0.692 |
| A1 | pooled | down | 48.0% | 847 (34 unres.) | 0.272 | 51.2% | 572 (26 unres.) | 0.587 |
| A1 | USDJPY | down | 49.4% | 393 (16 unres.) | 0.840 | 51.1% | 278 (15 unres.) | 0.764 |
| A1 | USDSGD | down | 46.9% | 454 (18 unres.) | 0.205 | 51.4% | 294 (11 unres.) | 0.683 |
| A2 | pooled | up | 50.5% | 971 (47 unres.) | 0.797 | 50.5% | 668 (48 unres.) | 0.847 |
| A2 | USDJPY | up | 54.5% | 477 (34 unres.) | 0.054 | 54.4% | 342 (30 unres.) | 0.117 |
| A2 | USDSGD | up | 46.6% | 494 (13 unres.) | 0.138 | 46.3% | 326 (18 unres.) | 0.203 |
| A2 | pooled | down | 50.3% | 887 (45 unres.) | 0.893 | 52.8% | 604 (33 unres.) | 0.179 |
| A2 | USDJPY | down | 55.3% | 398 (18 unres.) | 0.040 | 53.9% | 293 (14 unres.) | 0.199 |
| A2 | USDSGD | down | 46.2% | 489 (27 unres.) | 0.103 | 51.8% | 311 (19 unres.) | 0.571 |

### A1 by calendar year (hit rate, resolved n)

| scope | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| pooled | 51.6% (506) | 49.3% (531) | 52.0% (519) | 48.7% (542) | 49.7% (501) | 51.9% (422) |
| USDJPY | 52.6% (245) | 54.4% (259) | 57.3% (253) | 52.5% (259) | 50.8% (248) | 51.6% (223) |
| USDSGD | 50.6% (261) | 44.5% (272) | 47.0% (266) | 45.2% (283) | 48.6% (253) | 52.3% (199) |

### A2 by calendar year (hit rate, resolved n)

| scope | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| pooled | 50.4% (532) | 49.9% (539) | 52.6% (544) | 50.8% (533) | 48.1% (528) | 53.7% (454) |
| USDJPY | 53.3% (244) | 54.1% (253) | 59.2% (255) | 55.0% (258) | 50.6% (257) | 55.1% (243) |
| USDSGD | 47.9% (288) | 46.1% (286) | 46.7% (289) | 46.9% (275) | 45.8% (271) | 52.1% (211) |

## (B) secondary: X = 0.25 daily ATR (descriptive, not counted)

| id | scope | 1st: hit | n | p | 2nd: hit | n | p |
|---|---|---|---|---|---|---|---|
| B1 | pooled | 48.6% | 3709 (86 unres.) | 0.082 | 48.8% | 2670 (49 unres.) | 0.238 |
| B1 | USDJPY | 53.1% | 561 (12 unres.) | 0.151 | 50.1% | 345 (16 unres.) | 1.000 |
| B1 | USDSGD | 46.6% | 568 (23 unres.) | 0.120 | 49.6% | 363 (9 unres.) | 0.916 |
| B1 | XAUUSD | 47.8% | 590 (9 unres.) | 0.303 | 47.6% | 372 (5 unres.) | 0.378 |
| B1 | XAGUSD | 45.1% | 525 (6 unres.) | 0.029 | 49.5% | 364 (4 unres.) | 0.875 |
| B1 | WTI | 50.1% | 732 (8 unres.) | 0.971 | 48.9% | 615 (3 unres.) | 0.629 |
| B1 | BRENT | 48.0% | 733 (28 unres.) | 0.301 | 48.0% | 611 (12 unres.) | 0.332 |
| B2 | pooled | 50.2% | 2556 (416 unres.) | 0.859 | 50.8% | 1958 (312 unres.) | 0.484 |
| B2 | USDJPY | 52.2% | 385 (82 unres.) | 0.415 | 52.2% | 245 (81 unres.) | 0.523 |
| B2 | USDSGD | 48.9% | 348 (69 unres.) | 0.708 | 42.4% | 271 (56 unres.) | 0.015 |
| B2 | XAUUSD | 52.2% | 427 (88 unres.) | 0.384 | 55.0% | 331 (52 unres.) | 0.078 |
| B2 | XAGUSD | 49.0% | 418 (69 unres.) | 0.732 | 52.8% | 322 (39 unres.) | 0.343 |
| B2 | WTI | 47.5% | 522 (37 unres.) | 0.274 | 50.1% | 425 (29 unres.) | 1.000 |
| B2 | BRENT | 51.8% | 456 (71 unres.) | 0.482 | 51.4% | 364 (55 unres.) | 0.637 |
| B3 | pooled | 50.5% | 3026 (500 unres.) | 0.598 | 50.2% | 2317 (385 unres.) | 0.868 |
| B3 | USDJPY | 52.5% | 453 (110 unres.) | 0.301 | 51.5% | 307 (100 unres.) | 0.648 |
| B3 | USDSGD | 49.7% | 457 (86 unres.) | 0.925 | 44.5% | 346 (65 unres.) | 0.047 |
| B3 | XAUUSD | 51.7% | 526 (86 unres.) | 0.459 | 51.4% | 407 (66 unres.) | 0.620 |
| B3 | XAGUSD | 49.4% | 506 (87 unres.) | 0.824 | 51.1% | 407 (56 unres.) | 0.692 |
| B3 | WTI | 48.0% | 583 (44 unres.) | 0.362 | 51.4% | 451 (34 unres.) | 0.572 |
| B3 | BRENT | 52.1% | 501 (87 unres.) | 0.372 | 50.6% | 399 (64 unres.) | 0.841 |
| B4 | pooled | 50.3% | 1504 (153 unres.) | 0.816 | 52.0% | 1086 (117 unres.) | 0.192 |
| B4 | SPX | 49.1% | 763 (77 unres.) | 0.664 | 53.9% | 564 (54 unres.) | 0.070 |
| B4 | NDX | 51.5% | 741 (76 unres.) | 0.419 | 50.0% | 522 (63 unres.) | 1.000 |
| B5 | pooled | 50.3% | 1046 (156 unres.) | 0.877 | 52.1% | 762 (108 unres.) | 0.261 |
| B5 | SPX | 49.4% | 526 (83 unres.) | 0.827 | 53.6% | 397 (57 unres.) | 0.160 |
| B5 | NDX | 51.1% | 520 (73 unres.) | 0.630 | 50.4% | 365 (51 unres.) | 0.917 |

## Daylight saving (descriptive)

UTC windows split by season, and B1-B3 recomputed with the same clock windows read in London local time (so in BST they sit one hour earlier in UTC).

| id | split | 1st: hit | n | p | 2nd: hit | n | p |
|---|---|---|---|---|---|---|---|
| B1 | London BST (summer) | 49.2% | 1475 (639 unres.) | 0.567 | 51.3% | 1178 (478 unres.) | 0.398 |
| B1 | London GMT (winter) | 49.8% | 1244 (437 unres.) | 0.932 | 48.3% | 766 (297 unres.) | 0.366 |
| B1 | London-local windows, pooled | 49.3% | 2851 (1088 unres.) | 0.454 | 50.2% | 2072 (809 unres.) | 0.843 |
| B2 | London BST (summer) | 53.8% | 556 (1122 unres.) | 0.082 | 52.6% | 570 (813 unres.) | 0.224 |
| B2 | London GMT (winter) | 53.3% | 621 (673 unres.) | 0.108 | 51.3% | 394 (493 unres.) | 0.650 |
| B2 | London-local windows, pooled | 51.1% | 1530 (1709 unres.) | 0.399 | 51.5% | 1237 (1216 unres.) | 0.306 |
| B3 | London BST (summer) | 53.6% | 666 (1313 unres.) | 0.068 | 51.3% | 680 (975 unres.) | 0.514 |
| B3 | London GMT (winter) | 52.8% | 757 (790 unres.) | 0.127 | 52.0% | 458 (589 unres.) | 0.427 |
| B3 | London-local windows, pooled | 51.3% | 1836 (2018 unres.) | 0.273 | 51.5% | 1448 (1459 unres.) | 0.281 |
| B4 | US summer time | 51.6% | 488 (583 unres.) | 0.497 | 52.3% | 442 (416 unres.) | 0.366 |
| B4 | US winter time | 45.9% | 318 (268 unres.) | 0.161 | 38.5% | 174 (171 unres.) | 0.003 |
| B5 | US summer time | 50.3% | 292 (493 unres.) | 0.953 | 55.4% | 269 (352 unres.) | 0.088 |
| B5 | US winter time | 46.3% | 203 (214 unres.) | 0.326 | 35.2% | 108 (141 unres.) | 0.003 |

## Best (highest lower-half hit rate, not passing) variant B2: by weekday and month of year (all development data, pooled)

| weekday | Mon | Tue | Wed | Thu | Fri |
|---|---|---|---|---|---|
| hit (n) | 54.6% (346) | 54.8% (416) | 51.9% (503) | 50.2% (470) | 53.7% (406) |

| month | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hit (n) | 46.4% (261) | 51.1% (233) | 56.1% (196) | 46.4% (140) | 72.0% (132) | 44.6% (177) | 51.7% (178) | 47.4% (171) | 55.1% (176) | 60.4% (159) | 55.7% (176) | 55.6% (142) |

Events a month (pooled, 1st / 2nd): 72.2 / 77.8; trades a month: 72.1 / 77.5.

## Data and checks

- USDJPY (engine data/): 171130 bars 2019-01-01 22:00 to 2025-11-10 23:45, fee 0.010% a side; truncation check 2 cuts, 16504 events compared, 0 mismatched runs; excluded A1 no_entry_same_day 9, no_datr 11, before_start 250, open_at_end 1; A2 no_entry_same_day 16, no_datr 11, before_start 264, open_at_end 1; B1 no_entry_same_day 1, no_datr 2, before_start 132, open_at_end 1; B2 no_datr 4, before_start 128; B3 no_datr 7, before_start 171.
- USDSGD (Kronos store (read only)): 245680 bars 2016-01-03 22:00 to 2025-11-10 23:45, fee 0.015% a side; truncation check 2 cuts, 23178 events compared, 0 mismatched runs; excluded A1 no_entry_same_day 28, no_datr 10, before_start 1076; A2 no_entry_same_day 31, no_datr 12, before_start 1134; B1 no_datr 6, before_start 603; B2 no_datr 6, before_start 450; B3 no_datr 8, before_start 610.
- XAUUSD (engine data/): 162247 bars 2019-01-01 23:00 to 2025-11-10 23:45, fee 0.020% a side; truncation check 2 cuts, 11560 events compared, 0 mismatched runs; excluded B1 no_datr 7, before_start 167; B2 no_datr 4, before_start 137; B3 no_datr 9, before_start 166.
- XAGUSD (engine data/): 162216 bars 2019-01-01 23:00 to 2025-11-10 23:45, fee 0.030% a side; truncation check 2 cuts, 10933 events compared, 0 mismatched runs; excluded B1 no_datr 3, before_start 151; B2 no_datr 5, before_start 120; B3 no_datr 11, before_start 161.
- WTI (engine data/): 161931 bars 2019-01-01 23:00 to 2025-11-10 23:45, fee 0.040% a side; truncation check 2 cuts, 13019 events compared, 0 mismatched runs; excluded B1 no_datr 6, before_start 209; B2 no_datr 7, before_start 173, open_at_end 1; B3 no_datr 9, before_start 186, open_at_end 1.
- BRENT (engine data/): 147959 bars 2019-01-02 01:00 to 2025-11-10 21:45, fee 0.040% a side; truncation check 2 cuts, 12532 events compared, 0 mismatched runs; excluded B1 no_datr 10, before_start 210; B2 no_datr 7, before_start 152, open_at_end 1; B3 no_datr 9, before_start 169, open_at_end 1.
- SPX (engine data/): 44687 bars 2019-01-02 14:30 to 2025-11-10 20:45, fee 0.020% a side; truncation check 2 cuts, 4693 events compared, 0 mismatched runs; excluded B4 no_datr 13, before_start 233; B5 no_datr 13, before_start 173.
- NDX (Kronos store (read only)): 64217 bars 2016-01-04 14:30 to 2025-11-10 20:45, fee 0.020% a side; truncation check 2 cuts, 6405 events compared, 0 mismatched runs; excluded B4 no_datr 13, before_start 915; B5 no_datr 11, before_start 671.

USDJPY is where H46 found the FX lean, so A's pooled cells are not independent of H46; USDSGD alone is the out-of-family check. NDX = the Dukascopy Nasdaq-100 CFD restricted to NYSE cash hours (engine SPX filter). No data was fetched from the internet.
