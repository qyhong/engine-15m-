# H51: cross-market confirmation at a daily-level break

PAPER RESEARCH ONLY. Registered 2026-11-16 09:50 UTC (`research/hypotheses_pending/H51.md`) before any outcome. Development data only (rows before 2025-11-11 00:00 UTC; the holdout was not read). Events with entry from 2020-01-01; first half before 2023-06-07. Written 2026-11-16 09:54 UTC.

Event = the first 15m close beyond the level in its UTC day per direction (H45/H46 code). Follow hit = +0.5 daily ATR before -0.5 from the next 15m open within 72 h (a bar touching both = miss; neither = unresolved, excluded); fade = the mirror. Partner window = the partner's bars closing in (T - 60 min, T], T = the event bar's close. Confirmed = a partner close beyond its own same-type level in the expected direction (inverse for USDJPY vs XAU); divergent = not confirmed and the partner moved the other way by >= 1.0 of its own ATR15 over the window; unconfirmed = neither; no read = no partner bar in the window. p = exact two-sided binomial vs 50%. Tests: 8 variants x 3 buckets x 2 sides = **48** per half; Bonferroni p < 1.04e-03.

Pairs: P1 BTC <-> ETH; P2 XAU <-> XAG; P3 WTI <-> BRENT; P4 XAU vs USDJPY (inverse); P5 SPX vs BTC (risk-on); P6 WTI vs SPX (oil / risk).

Variants: V1 = P1 BTC <-> ETH pday; V2 = P2 XAU <-> XAG pday; V3 = P3 WTI <-> BRENT pday; V4 = P4 XAU vs USDJPY (inverse) pday; V5 = P5 SPX vs BTC (risk-on) pday; V6 = P6 WTI vs SPX (oil / risk) pday; V7 = all pairs (any partner) pday; V8 = all pairs (any partner) roll24.

## Verdict: NO PASS

No variant / bucket / side met all of: >= 55% in both halves, >= 200 resolved per half, p < 1.04e-03 in both halves, net > 0 after costs in the second half pooled and in a majority of its markets.

Cells passing Bonferroni in both halves (any direction): 0 of 48. Cells with >= 55% in both halves and >= 200 resolved: 0. Cells passing the cost part: 2.

Sanity (union of all events, follow): pday 49.1% | 6916 | 0.152 / 50.0% | 4919 | 0.977; roll24 49.2% | 7051 | 0.190 / 50.2% | 5058 | 0.746 (first / second: hit | n | p).

## Hit rates per variant, bucket and side

| variant | bucket | side | first: hit | n | p | second: hit | n | p | Bonf. both | >=55% & n | cost ok | events / month 1st / 2nd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 | reference (all read) | follow | 47.9% | 1930 | 0.072 | 51.1% | 1345 | 0.413 | | | | |
| V1 | reference (all read) | fade | 52.1% | 1930 | 0.072 | 48.9% | 1345 | 0.413 | | | | |
| V1 | confirmed | follow | 46.8% | 1030 | 0.043 | 50.0% | 630 | 1.000 |  |  |  | 25.8 / 22.4 |
| V1 | confirmed | fade | 53.2% | 1030 | 0.043 | 50.0% | 630 | 1.000 |  |  |  | 25.8 / 22.4 |
| V1 | unconfirmed | follow | 49.2% | 898 | 0.664 | 51.9% | 709 | 0.329 |  |  |  | 22.4 / 24.9 |
| V1 | unconfirmed | fade | 50.8% | 898 | 0.664 | 48.1% | 709 | 0.329 |  |  |  | 22.4 / 24.9 |
| V1 | divergent | follow | 50.0% | 2 | 1.000 | 83.3% | 6 | 0.219 |  |  | yes | 0.1 / 0.2 |
| V1 | divergent | fade | 50.0% | 2 | 1.000 | 16.7% | 6 | 0.219 |  |  |  | 0.1 / 0.2 |
| V2 | reference (all read) | follow | 47.8% | 1757 | 0.070 | 49.0% | 1266 | 0.482 | | | | |
| V2 | reference (all read) | fade | 52.1% | 1757 | 0.077 | 50.9% | 1266 | 0.555 | | | | |
| V2 | confirmed | follow | 46.1% | 862 | 0.022 | 48.5% | 549 | 0.495 |  |  |  | 22.1 / 19.4 |
| V2 | confirmed | fade | 53.9% | 862 | 0.022 | 51.4% | 549 | 0.550 |  |  |  | 22.1 / 19.4 |
| V2 | unconfirmed | follow | 49.7% | 886 | 0.867 | 48.9% | 694 | 0.569 |  |  |  | 22.1 / 24.9 |
| V2 | unconfirmed | fade | 50.2% | 886 | 0.920 | 51.0% | 694 | 0.622 |  |  |  | 22.1 / 24.9 |
| V2 | divergent | follow | 33.3% | 9 | 0.508 | 65.2% | 23 | 0.210 |  |  |  | 0.2 / 0.8 |
| V2 | divergent | fade | 66.7% | 9 | 0.508 | 34.8% | 23 | 0.210 |  |  |  | 0.2 / 0.8 |
| V3 | reference (all read) | follow | 50.4% | 1554 | 0.780 | 48.7% | 1138 | 0.390 | | | | |
| V3 | reference (all read) | fade | 49.6% | 1554 | 0.780 | 51.3% | 1138 | 0.390 | | | | |
| V3 | confirmed | follow | 49.0% | 955 | 0.560 | 47.6% | 745 | 0.213 |  |  |  | 24.9 / 26.8 |
| V3 | confirmed | fade | 51.0% | 955 | 0.560 | 52.4% | 745 | 0.213 |  |  |  | 24.9 / 26.8 |
| V3 | unconfirmed | follow | 52.6% | 593 | 0.218 | 50.5% | 392 | 0.880 |  |  |  | 15.3 / 14.4 |
| V3 | unconfirmed | fade | 47.4% | 593 | 0.218 | 49.5% | 392 | 0.880 |  |  |  | 15.3 / 14.4 |
| V3 | divergent | follow | 50.0% | 6 | 1.000 | 100.0% | 1 | 1.000 |  |  |  | 0.1 / 0.0 |
| V3 | divergent | fade | 50.0% | 6 | 1.000 | 0.0% | 1 | 1.000 |  |  |  | 0.1 / 0.0 |
| V4 | reference (all read) | follow | 51.0% | 1726 | 0.400 | 52.4% | 1226 | 0.104 | | | | |
| V4 | reference (all read) | fade | 48.8% | 1726 | 0.348 | 47.1% | 1226 | 0.049 | | | | |
| V4 | confirmed | follow | 49.3% | 608 | 0.777 | 50.2% | 408 | 0.961 |  |  |  | 15.3 / 14.7 |
| V4 | confirmed | fade | 50.5% | 608 | 0.839 | 48.5% | 408 | 0.586 |  |  |  | 15.3 / 14.7 |
| V4 | unconfirmed | follow | 52.5% | 998 | 0.121 | 54.5% | 695 | 0.019 |  |  | yes | 25.6 / 25.1 |
| V4 | unconfirmed | fade | 47.4% | 998 | 0.106 | 45.5% | 695 | 0.019 |  |  |  | 25.6 / 25.1 |
| V4 | divergent | follow | 47.5% | 120 | 0.648 | 47.1% | 123 | 0.589 |  |  |  | 3.0 / 4.4 |
| V4 | divergent | fade | 52.5% | 120 | 0.648 | 52.0% | 123 | 0.719 |  |  |  | 3.0 / 4.4 |
| V5 | reference (all read) | follow | 48.1% | 850 | 0.288 | 50.1% | 658 | 0.969 | | | | |
| V5 | reference (all read) | fade | 51.9% | 850 | 0.288 | 49.9% | 658 | 0.969 | | | | |
| V5 | confirmed | follow | 49.2% | 303 | 0.818 | 48.1% | 214 | 0.632 |  |  |  | 7.9 / 7.8 |
| V5 | confirmed | fade | 50.8% | 303 | 0.818 | 51.9% | 214 | 0.632 |  |  |  | 7.9 / 7.8 |
| V5 | unconfirmed | follow | 47.6% | 479 | 0.315 | 52.7% | 370 | 0.323 |  |  |  | 13.1 / 13.8 |
| V5 | unconfirmed | fade | 52.4% | 479 | 0.315 | 47.3% | 370 | 0.323 |  |  |  | 13.1 / 13.8 |
| V5 | divergent | follow | 47.1% | 68 | 0.716 | 43.2% | 74 | 0.295 |  |  |  | 1.9 / 2.7 |
| V5 | divergent | fade | 52.9% | 68 | 0.716 | 56.8% | 74 | 0.295 |  |  |  | 1.9 / 2.7 |
| V6 | reference (all read) | follow | 48.3% | 845 | 0.335 | 48.3% | 609 | 0.418 | | | | |
| V6 | reference (all read) | fade | 51.7% | 845 | 0.335 | 51.7% | 609 | 0.418 | | | | |
| V6 | confirmed | follow | 48.2% | 313 | 0.572 | 45.3% | 192 | 0.220 |  |  |  | 8.6 / 7.1 |
| V6 | confirmed | fade | 51.8% | 313 | 0.572 | 54.7% | 192 | 0.220 |  |  |  | 8.6 / 7.1 |
| V6 | unconfirmed | follow | 48.8% | 418 | 0.660 | 50.5% | 309 | 0.909 |  |  |  | 11.3 / 11.7 |
| V6 | unconfirmed | fade | 51.2% | 418 | 0.660 | 49.5% | 309 | 0.909 |  |  |  | 11.3 / 11.7 |
| V6 | divergent | follow | 46.5% | 114 | 0.512 | 47.2% | 108 | 0.631 |  |  |  | 3.2 / 4.0 |
| V6 | divergent | fade | 53.5% | 114 | 0.512 | 52.8% | 108 | 0.631 |  |  |  | 3.2 / 4.0 |
| V7 | reference (all read) | follow | 49.1% | 6687 | 0.163 | 50.1% | 4758 | 0.919 | | | | |
| V7 | reference (all read) | fade | 50.8% | 6687 | 0.179 | 49.8% | 4758 | 0.783 | | | | |
| V7 | confirmed | follow | 47.9% | 3640 | 0.012 | 48.9% | 2464 | 0.286 |  |  |  | 93.3 / 88.2 |
| V7 | confirmed | fade | 52.1% | 3640 | 0.014 | 50.9% | 2464 | 0.386 |  |  |  | 93.3 / 88.2 |
| V7 | unconfirmed | follow | 51.1% | 2843 | 0.260 | 51.6% | 2063 | 0.159 |  |  |  | 72.2 / 74.5 |
| V7 | unconfirmed | fade | 48.9% | 2843 | 0.245 | 48.4% | 2063 | 0.159 |  |  |  | 72.2 / 74.5 |
| V7 | divergent | follow | 44.1% | 204 | 0.107 | 49.4% | 231 | 0.895 |  |  |  | 5.5 / 8.3 |
| V7 | divergent | fade | 55.9% | 204 | 0.107 | 50.2% | 231 | 1.000 |  |  |  | 5.5 / 8.3 |
| V8 | reference (all read) | follow | 49.2% | 6884 | 0.197 | 50.3% | 4936 | 0.701 | | | | |
| V8 | reference (all read) | fade | 50.7% | 6884 | 0.233 | 49.6% | 4936 | 0.598 | | | | |
| V8 | confirmed | follow | 49.0% | 3132 | 0.276 | 49.6% | 2127 | 0.761 |  |  |  | 80.7 / 76.2 |
| V8 | confirmed | fade | 51.0% | 3132 | 0.292 | 50.2% | 2127 | 0.862 |  |  |  | 80.7 / 76.2 |
| V8 | unconfirmed | follow | 49.7% | 3502 | 0.723 | 50.8% | 2593 | 0.456 |  |  |  | 89.5 / 93.2 |
| V8 | unconfirmed | fade | 50.2% | 3502 | 0.800 | 49.2% | 2593 | 0.409 |  |  |  | 89.5 / 93.2 |
| V8 | divergent | follow | 45.2% | 250 | 0.146 | 50.9% | 216 | 0.838 |  |  |  | 6.6 / 8.1 |
| V8 | divergent | fade | 54.8% | 250 | 0.146 | 49.1% | 216 | 0.838 |  |  |  | 6.6 / 8.1 |

## Counts per variant (events by partner status, first / second half)

| variant | events | no read | confirmed | unconfirmed | divergent | mixed (V7/V8) | confirmed and moved >= 1 ATR15 the other way |
|---|---|---|---|---|---|---|---|
| V1 | 1982 / 1385 | 0 / 0 | 1060 / 652 | 920 / 727 | 2 / 6 | 0 / 0 | 1 / 1 |
| V2 | 1830 / 1315 | 0 / 0 | 910 / 567 | 910 / 725 | 10 / 23 | 0 / 0 | 0 / 5 |
| V3 | 1773 / 1266 | 111 / 64 | 1024 / 782 | 632 / 419 | 6 / 1 | 0 / 0 | 3 / 5 |
| V4 | 1834 / 1303 | 25 / 12 | 631 / 429 | 1054 / 733 | 124 / 129 | 0 / 0 | 28 / 25 |
| V5 | 1777 / 1242 | 838 / 533 | 324 / 228 | 539 / 402 | 76 / 79 | 0 / 0 | 21 / 20 |
| V6 | 1747 / 1228 | 798 / 562 | 352 / 208 | 465 / 342 | 132 / 116 | 0 / 0 | 45 / 29 |
| V7 | 7284 / 5158 | 136 / 76 | 3840 / 2574 | 2972 / 2173 | 225 / 243 | 111 / 92 | - |
| V8 | 7452 / 5302 | 101 / 63 | 3322 / 2224 | 3685 / 2718 | 270 / 235 | 74 / 62 | - |

## Secondary: confirmed-follow minus divergent-follow (points, two-proportion z; 'matters' needs the same sign and p < 0.0063 in both halves)

| variant | first: diff | p | second: diff | p | matters |
|---|---|---|---|---|---|
| V1 | -3.2 | 0.9277 | -33.3 | 0.1041 | no |
| V2 | +12.7 | 0.4461 | -16.8 | 0.1151 | no |
| V3 | -1.0 | 0.9612 | -52.4 | 0.2949 | no |
| V4 | +1.8 | 0.7122 | +3.1 | 0.5479 | no |
| V5 | +2.1 | 0.7524 | +4.9 | 0.4677 | no |
| V6 | +1.8 | 0.7485 | -1.9 | 0.7501 | no |
| V7 | +3.8 | 0.2910 | -0.5 | 0.8967 | no |
| V8 | +3.8 | 0.2461 | -1.3 | 0.7203 | no |

## After costs: every bucket traded (stop and target 0.5 dATR, 72 h max, own fee a side, one position per market)

| variant | bucket | side | half | trades | won | R before costs | R after costs | per trade (% stake) | net $ | markets net > 0 (2nd) |
|---|---|---|---|---|---|---|---|---|---|---|
| V1 | confirmed | follow | first | 897 | 46.9% | -0.061 | -0.138 | -0.4064% | -36,452 |  |
|  |  |  | second | 572 | 50.0% | +0.014 | -0.091 | -0.2367% | -13,538 | 0 of 2 (need 2): none |
| V1 | confirmed | fade | first | 897 | 53.1% | +0.061 | -0.016 | +0.0061% | +548 |  |
|  |  |  | second | 572 | 49.7% | -0.014 | -0.119 | -0.1634% | -9,346 | 0 of 2 (need 2): none |
| V1 | unconfirmed | follow | first | 787 | 49.0% | -0.014 | -0.090 | -0.2545% | -20,027 |  |
|  |  |  | second | 628 | 50.8% | +0.027 | -0.082 | -0.1658% | -10,414 | 0 of 2 (need 2): none |
| V1 | unconfirmed | fade | first | 787 | 50.6% | +0.014 | -0.063 | -0.1454% | -11,440 |  |
|  |  |  | second | 628 | 48.4% | -0.027 | -0.136 | -0.2340% | -14,693 | 0 of 2 (need 2): none |
| V1 | divergent | follow | first | 2 | 50.0% | +0.000 | -0.100 | +0.4934% | +99 |  |
|  |  |  | second | 6 | 83.3% | +0.667 | +0.543 | +1.3224% | +793 | 2 of 2 (need 2): BTCUSDT, ETHUSDT |
| V1 | divergent | fade | first | 2 | 50.0% | +0.000 | -0.100 | -0.8948% | -179 |  |
|  |  |  | second | 6 | 16.7% | -0.667 | -0.791 | -1.7214% | -1,033 | 0 of 2 (need 2): none |
| V2 | confirmed | follow | first | 780 | 46.2% | -0.073 | -0.132 | -0.1197% | -9,335 |  |
|  |  |  | second | 496 | 48.0% | -0.026 | -0.089 | -0.0940% | -4,662 | 0 of 2 (need 2): none |
| V2 | confirmed | fade | first | 780 | 53.2% | +0.073 | +0.014 | +0.0206% | +1,610 |  |
|  |  |  | second | 496 | 51.2% | +0.021 | -0.042 | -0.0081% | -403 | 1 of 2 (need 2): XAGUSD |
| V2 | unconfirmed | follow | first | 791 | 50.8% | +0.010 | -0.048 | -0.0157% | -1,242 |  |
|  |  |  | second | 620 | 48.7% | -0.021 | -0.085 | -0.0947% | -5,871 | 0 of 2 (need 2): none |
| V2 | unconfirmed | fade | first | 791 | 49.1% | -0.012 | -0.070 | -0.0863% | -6,824 |  |
|  |  |  | second | 620 | 51.1% | +0.018 | -0.045 | -0.0073% | -453 | 1 of 2 (need 2): XAGUSD |
| V2 | divergent | follow | first | 9 | 44.4% | -0.130 | -0.184 | -0.4569% | -411 |  |
|  |  |  | second | 22 | 63.6% | +0.273 | +0.213 | +0.2862% | +630 | 1 of 2 (need 2): XAGUSD |
| V2 | divergent | fade | first | 9 | 55.6% | +0.130 | +0.076 | +0.3547% | +319 |  |
|  |  |  | second | 22 | 36.4% | -0.273 | -0.333 | -0.3879% | -853 | 0 of 2 (need 2): none |
| V3 | confirmed | follow | first | 894 | 49.0% | -0.005 | -0.054 | -0.0604% | -5,398 |  |
|  |  |  | second | 688 | 48.0% | -0.040 | -0.105 | -0.1347% | -9,264 | 0 of 2 (need 2): none |
| V3 | confirmed | fade | first | 894 | 50.4% | +0.005 | -0.044 | -0.0997% | -8,911 |  |
|  |  |  | second | 688 | 51.6% | +0.040 | -0.025 | -0.0253% | -1,742 | 1 of 2 (need 2): WTI |
| V3 | unconfirmed | follow | first | 545 | 51.7% | +0.036 | -0.014 | +0.0087% | +475 |  |
|  |  |  | second | 358 | 50.0% | +0.002 | -0.065 | -0.1010% | -3,617 | 0 of 2 (need 2): none |
| V3 | unconfirmed | fade | first | 545 | 47.9% | -0.036 | -0.085 | -0.1687% | -9,195 |  |
|  |  |  | second | 358 | 49.7% | -0.002 | -0.069 | -0.0589% | -2,108 | 1 of 2 (need 2): BRENT |
| V3 | divergent | follow | first | 6 | 50.0% | +0.000 | -0.048 | -0.0472% | -28 |  |
|  |  |  | second | 1 | 100.0% | +1.000 | +0.954 | +1.6312% | +163 | 1 of 2 (need 2): BRENT |
| V3 | divergent | fade | first | 6 | 50.0% | -0.000 | -0.048 | -0.1125% | -68 |  |
|  |  |  | second | 1 | 0.0% | -1.000 | -1.046 | -1.7898% | -179 | 0 of 2 (need 2): none |
| V4 | confirmed | follow | first | 574 | 50.0% | -0.001 | -0.070 | -0.0382% | -2,193 |  |
|  |  |  | second | 399 | 49.1% | +0.000 | -0.062 | -0.0337% | -1,346 | 1 of 2 (need 2): USDJPY |
| V4 | confirmed | fade | first | 574 | 49.7% | -0.002 | -0.071 | -0.0243% | -1,393 |  |
|  |  |  | second | 399 | 48.9% | -0.025 | -0.088 | -0.0357% | -1,424 | 0 of 2 (need 2): none |
| V4 | unconfirmed | follow | first | 867 | 52.6% | +0.051 | -0.017 | -0.0190% | -1,650 |  |
|  |  |  | second | 607 | 53.9% | +0.084 | +0.021 | +0.0053% | +320 | 2 of 2 (need 2): XAUUSD, USDJPY |
| V4 | unconfirmed | fade | first | 867 | 46.9% | -0.053 | -0.121 | -0.0417% | -3,614 |  |
|  |  |  | second | 607 | 46.0% | -0.084 | -0.148 | -0.0654% | -3,973 | 0 of 2 (need 2): none |
| V4 | divergent | follow | first | 121 | 47.9% | -0.036 | -0.102 | -0.0569% | -688 |  |
|  |  |  | second | 123 | 48.0% | -0.037 | -0.099 | -0.0286% | -352 | 0 of 2 (need 2): none |
| V4 | divergent | fade | first | 121 | 52.1% | +0.036 | -0.030 | -0.0056% | -68 |  |
|  |  |  | second | 123 | 50.4% | +0.021 | -0.041 | -0.0392% | -482 | 0 of 2 (need 2): none |
| V5 | confirmed | follow | first | 306 | 48.7% | -0.030 | -0.096 | -0.2154% | -6,591 |  |
|  |  |  | second | 219 | 47.9% | -0.038 | -0.129 | -0.1003% | -2,197 | 0 of 2 (need 2): none |
| V5 | confirmed | fade | first | 306 | 50.7% | +0.030 | -0.037 | +0.0569% | +1,740 |  |
|  |  |  | second | 219 | 51.6% | +0.038 | -0.054 | -0.0676% | -1,480 | 0 of 2 (need 2): none |
| V5 | unconfirmed | follow | first | 496 | 48.8% | +0.007 | -0.058 | -0.1166% | -5,784 |  |
|  |  |  | second | 355 | 50.4% | +0.016 | -0.075 | -0.0516% | -1,833 | 0 of 2 (need 2): none |
| V5 | unconfirmed | fade | first | 496 | 50.4% | -0.007 | -0.072 | -0.0136% | -676 |  |
|  |  |  | second | 355 | 48.7% | -0.016 | -0.107 | -0.1121% | -3,980 | 0 of 2 (need 2): none |
| V5 | divergent | follow | first | 76 | 44.7% | -0.098 | -0.163 | -0.0802% | -609 |  |
|  |  |  | second | 77 | 42.9% | -0.124 | -0.209 | -0.1643% | -1,265 | 0 of 2 (need 2): none |
| V5 | divergent | fade | first | 76 | 52.6% | +0.098 | +0.034 | -0.0292% | -222 |  |
|  |  |  | second | 77 | 57.1% | +0.124 | +0.038 | +0.0469% | +361 | 1 of 2 (need 2): SPX |
| V6 | confirmed | follow | first | 334 | 49.4% | +0.021 | -0.036 | -0.0796% | -2,660 |  |
|  |  |  | second | 198 | 45.5% | -0.080 | -0.156 | -0.1014% | -2,008 | 0 of 2 (need 2): none |
| V6 | confirmed | fade | first | 334 | 49.7% | -0.021 | -0.078 | -0.0126% | -422 |  |
|  |  |  | second | 198 | 54.0% | +0.080 | +0.003 | +0.0061% | +121 | 1 of 2 (need 2): WTI |
| V6 | unconfirmed | follow | first | 430 | 48.6% | -0.006 | -0.062 | -0.0937% | -4,028 |  |
|  |  |  | second | 304 | 49.7% | -0.014 | -0.089 | -0.0819% | -2,490 | 0 of 2 (need 2): none |
| V6 | unconfirmed | fade | first | 430 | 50.7% | +0.006 | -0.049 | -0.0055% | -236 |  |
|  |  |  | second | 304 | 49.7% | +0.014 | -0.061 | -0.0163% | -495 | 1 of 2 (need 2): WTI |
| V6 | divergent | follow | first | 128 | 48.4% | -0.033 | -0.094 | -0.1219% | -1,560 |  |
|  |  |  | second | 111 | 46.8% | -0.034 | -0.110 | -0.0500% | -555 | 0 of 2 (need 2): none |
| V6 | divergent | fade | first | 128 | 50.8% | +0.033 | -0.028 | +0.0324% | +415 |  |
|  |  |  | second | 111 | 52.3% | +0.034 | -0.043 | -0.0409% | -454 | 0 of 2 (need 2): none |
| V7 | confirmed | follow | first | 3315 | 48.5% | -0.022 | -0.084 | -0.1572% | -52,122 |  |
|  |  |  | second | 2274 | 48.8% | -0.016 | -0.091 | -0.1311% | -29,820 | 1 of 8 (need 5): USDJPY |
| V7 | confirmed | fade | first | 3315 | 51.1% | +0.021 | -0.041 | -0.0346% | -11,478 |  |
|  |  |  | second | 2274 | 50.5% | +0.011 | -0.065 | -0.0595% | -13,527 | 2 of 8 (need 5): XAGUSD, WTI |
| V7 | unconfirmed | follow | first | 2578 | 51.1% | +0.023 | -0.040 | -0.0935% | -24,113 |  |
|  |  |  | second | 1866 | 51.1% | +0.027 | -0.050 | -0.0928% | -17,325 | 2 of 8 (need 5): XAUUSD, USDJPY |
| V7 | unconfirmed | fade | first | 2578 | 48.6% | -0.024 | -0.087 | -0.0973% | -25,076 |  |
|  |  |  | second | 1866 | 48.4% | -0.027 | -0.104 | -0.1037% | -19,342 | 2 of 8 (need 5): XAGUSD, BRENT |
| V7 | divergent | follow | first | 222 | 44.6% | -0.114 | -0.178 | -0.1285% | -2,852 |  |
|  |  |  | second | 231 | 48.9% | -0.005 | -0.076 | +0.0058% | +134 | 4 of 8 (need 5): BTCUSDT, ETHUSDT, XAGUSD, BRENT |
| V7 | divergent | fade | first | 222 | 54.5% | +0.114 | +0.050 | +0.0456% | +1,012 |  |
|  |  |  | second | 231 | 50.2% | -0.004 | -0.075 | -0.1014% | -2,343 | 1 of 8 (need 5): WTI |
| V8 | confirmed | follow | first | 2912 | 49.0% | -0.010 | -0.073 | -0.1631% | -47,506 |  |
|  |  |  | second | 1964 | 49.0% | -0.010 | -0.087 | -0.1088% | -21,371 | 1 of 8 (need 5): USDJPY |
| V8 | confirmed | fade | first | 2912 | 50.4% | +0.010 | -0.053 | -0.0504% | -14,681 |  |
|  |  |  | second | 1964 | 50.2% | +0.007 | -0.069 | -0.1031% | -20,254 | 1 of 8 (need 5): XAGUSD |
| V8 | unconfirmed | follow | first | 3102 | 49.5% | -0.003 | -0.067 | -0.1624% | -50,379 |  |
|  |  |  | second | 2267 | 50.5% | +0.017 | -0.061 | -0.1336% | -30,285 | 2 of 8 (need 5): XAUUSD, USDJPY |
| V8 | unconfirmed | fade | first | 3102 | 49.9% | +0.002 | -0.062 | -0.0394% | -12,223 |  |
|  |  |  | second | 2267 | 49.0% | -0.018 | -0.095 | -0.0651% | -14,758 | 1 of 8 (need 5): BRENT |
| V8 | divergent | follow | first | 264 | 45.8% | -0.073 | -0.136 | -0.1810% | -4,778 |  |
|  |  |  | second | 222 | 52.3% | +0.053 | -0.016 | +0.0181% | +402 | 3 of 8 (need 5): BTCUSDT, ETHUSDT, XAGUSD |
| V8 | divergent | fade | first | 264 | 53.8% | +0.073 | +0.009 | +0.0896% | +2,366 |  |
|  |  |  | second | 222 | 47.3% | -0.053 | -0.123 | -0.1157% | -2,568 | 3 of 8 (need 5): USDJPY, WTI, BRENT |

## Per event market inside each variant (follow hit, first / second half: hit (resolved))

### V1

| market | confirmed | unconfirmed | divergent |
|---|---|---|---|
| BTCUSDT | 46.6% (515) / 49.7% (302) | 48.0% (454) / 49.9% (377) | 50.0% (2) / 75.0% (4) |
| ETHUSDT | 47.0% (515) / 50.3% (328) | 50.5% (444) / 54.2% (332) | - (0) / 100.0% (2) |

### V2

| market | confirmed | unconfirmed | divergent |
|---|---|---|---|
| XAUUSD | 48.1% (441) / 51.8% (274) | 49.6% (429) / 52.0% (342) | 33.3% (3) / 50.0% (10) |
| XAGUSD | 43.9% (421) / 45.1% (275) | 49.7% (457) / 45.7% (352) | 33.3% (6) / 76.9% (13) |

### V3

| market | confirmed | unconfirmed | divergent |
|---|---|---|---|
| WTI | 49.7% (457) / 47.0% (362) | 51.5% (355) / 53.3% (240) | - (0) / - (0) |
| BRENT | 48.4% (498) / 48.3% (383) | 54.2% (238) / 46.0% (152) | 50.0% (6) / 100.0% (1) |

### V4

| market | confirmed | unconfirmed | divergent |
|---|---|---|---|
| XAUUSD | 46.6% (309) / 46.9% (211) | 50.2% (496) / 55.3% (347) | 48.5% (68) / 50.0% (68) |
| USDJPY | 52.2% (299) / 53.8% (197) | 54.8% (502) / 53.7% (348) | 46.1% (52) / 43.6% (55) |

### V5

| market | confirmed | unconfirmed | divergent |
|---|---|---|---|
| SPX | 51.7% (230) / 46.4% (153) | 46.8% (402) / 52.4% (277) | 44.3% (61) / 41.5% (65) |
| BTCUSDT | 41.1% (73) / 52.5% (61) | 52.0% (77) / 53.8% (93) | 71.4% (7) / 55.6% (9) |

### V6

| market | confirmed | unconfirmed | divergent |
|---|---|---|---|
| WTI | 43.9% (41) / 45.5% (33) | 52.6% (97) / 42.4% (66) | 38.5% (13) / 53.3% (15) |
| SPX | 48.9% (272) / 45.3% (159) | 47.7% (321) / 52.7% (243) | 47.5% (101) / 46.2% (93) |

### V7

| market | confirmed | unconfirmed | divergent |
|---|---|---|---|
| BTCUSDT | 46.4% (539) / 49.1% (332) | 48.0% (423) / 50.3% (338) | 75.0% (4) / 63.6% (11) |
| ETHUSDT | 47.0% (515) / 50.3% (328) | 50.5% (444) / 54.2% (332) | - (0) / 100.0% (2) |
| XAUUSD | 47.1% (562) / 50.5% (370) | 52.9% (240) / 56.0% (182) | 38.9% (36) / 50.0% (48) |
| XAGUSD | 43.9% (421) / 45.1% (275) | 49.7% (457) / 45.7% (352) | 33.3% (6) / 76.9% (13) |
| USDJPY | 52.2% (299) / 53.8% (197) | 54.8% (502) / 53.7% (348) | 46.1% (52) / 43.6% (55) |
| SPX | 50.3% (340) / 48.6% (216) | 46.6% (206) / 54.8% (135) | 42.4% (92) / 45.8% (96) |
| WTI | 50.2% (466) / 46.8% (363) | 51.4% (333) / 53.6% (224) | 62.5% (8) / 40.0% (5) |
| BRENT | 48.4% (498) / 48.3% (383) | 54.2% (238) / 46.0% (152) | 50.0% (6) / 100.0% (1) |

### V8

| market | confirmed | unconfirmed | divergent |
|---|---|---|---|
| BTCUSDT | 47.6% (576) / 51.2% (326) | 45.3% (580) / 48.6% (494) | 60.0% (10) / 81.8% (11) |
| ETHUSDT | 47.7% (509) / 53.1% (354) | 49.0% (671) / 47.6% (462) | - (0) / 75.0% (4) |
| XAUUSD | 46.1% (425) / 48.8% (256) | 52.7% (338) / 56.2% (283) | 42.9% (49) / 45.2% (42) |
| XAGUSD | 45.6% (340) / 47.9% (217) | 50.3% (487) / 47.5% (377) | 40.0% (5) / 83.3% (6) |
| USDJPY | 60.4% (154) / 53.0% (83) | 54.0% (637) / 55.0% (476) | 50.8% (67) / 46.1% (65) |
| SPX | 56.6% (99) / 47.8% (67) | 41.7% (211) / 55.1% (138) | 43.6% (94) / 52.8% (72) |
| WTI | 50.1% (527) / 48.5% (421) | 52.7% (277) / 52.6% (175) | 31.2% (16) / 38.5% (13) |
| BRENT | 50.6% (502) / 47.6% (403) | 48.8% (301) / 46.8% (188) | 44.4% (9) / 33.3% (3) |

## Checks

- BTCUSDT: 240306 bars (2019-01-01 00:00 to 2025-11-10 23:45), fee 0.10% a side; events pday 1701, roll24 2063 (no same-day entry excluded: {'pday': 7, 'roll24': 10}); partner-reading truncation: pday 3111 compared, 0 mismatched; roll24 3752 compared, 0 mismatched.
- ETHUSDT: 240306 bars (2019-01-01 00:00 to 2025-11-10 23:45), fee 0.10% a side; events pday 1666, roll24 2066 (no same-day entry excluded: {'pday': 6, 'roll24': 14}); partner-reading truncation: pday 3046 compared, 0 mismatched; roll24 3742 compared, 0 mismatched.
- XAUUSD: 162247 bars (2019-01-01 23:00 to 2025-11-10 23:45), fee 0.02% a side; events pday 1564, roll24 1529 (no same-day entry excluded: {'pday': 4, 'roll24': 3}); partner-reading truncation: pday 2892 compared, 0 mismatched; roll24 2839 compared, 0 mismatched.
- XAGUSD: 162216 bars (2019-01-01 23:00 to 2025-11-10 23:45), fee 0.03% a side; events pday 1581, roll24 1499 (no same-day entry excluded: {'pday': 4, 'roll24': 5}); partner-reading truncation: pday 2876 compared, 0 mismatched; roll24 2722 compared, 0 mismatched.
- USDJPY: 171130 bars (2019-01-01 22:00 to 2025-11-10 23:45), fee 0.01% a side; events pday 1573, roll24 1606 (no same-day entry excluded: {'pday': 9, 'roll24': 16}); partner-reading truncation: pday 2871 compared, 0 mismatched; roll24 2935 compared, 0 mismatched.
- SPX: 44687 bars (2019-01-02 14:30 to 2025-11-10 20:45), fee 0.02% a side; events pday 1318, roll24 805 (no same-day entry excluded: {'pday': 39, 'roll24': 35}); partner-reading truncation: pday 2438 compared, 0 mismatched; roll24 1490 compared, 0 mismatched.
- WTI: 161931 bars (2019-01-01 23:00 to 2025-11-10 23:45), fee 0.04% a side; events pday 1657, roll24 1667 (no same-day entry excluded: {'pday': 5, 'roll24': 7}); partner-reading truncation: pday 3075 compared, 0 mismatched; roll24 3036 compared, 0 mismatched.
- BRENT: 147959 bars (2019-01-02 01:00 to 2025-11-10 21:45), fee 0.04% a side; events pday 1382, roll24 1519 (no same-day entry excluded: {'pday': 3, 'roll24': 6}); partner-reading truncation: pday 2494 compared, 0 mismatched; roll24 2752 compared, 0 mismatched.

Partners are read only from bars that closed by the event bar's close. Markets shut at different hours, so 'no read' is common for pairs with SPX (cash hours) and for weekend crypto events against metals / oil / fx.
