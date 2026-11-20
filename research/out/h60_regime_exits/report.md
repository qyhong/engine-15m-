# H60: exits by regime, per market (history replay, IN-SAMPLE, not proof)

Written by `research/h60_regime_exits.py` on 2026-11-20 11:57 UTC. Paper only. These are replays of history the project has already read for exits (H36, H59). Nothing here is a proven edge, and nothing here changes a book.

## The answers, in plain words

- **The check on the tools.** The study's own copy of the book runner gave the same trades as the engine's runner on all 8 markets, in both switch positions: yes. The four H59 books came out exactly as in H59's run.
- **(a) Does holding pay more in directional regimes, and targets pay more in the others?** **Not supported.** Pooled, first half: holding earned more per trade in directional regimes: yes; targets earned more in the others: no. Second half: no and no. Markets where both held over the whole window: 1 of 8 (XAGUSD; needs 5).
- **(b) The owner's rule as a whole book (variant 1, `rg_dir_entry`).** Better than holding: **NO**. Pooled net $+41188 against main $+339325; halves vs main $-127865 / $-170273; ahead of main in 2 of 8 markets; max drawdown -36.7% vs main -32.8%.
- **(b) Variant 1 against its control (the idea turned round, variant 5).** The idea needs variant 1 above the control in both halves: **it is not** (first half $-78386, second half $-113359).
- **(b) The other variants.** Better than holding: none.
- **(c) One rule per market.** Picking each market's best rule on the first half and using it on the second half: **a rule per market does not help**. Picks' second half together $+137211 against main's $+186970; ahead of main in 1 of 8 markets (needs 5).

**Why it comes out this way, in one line.** Most of the main book's trades start in a RANGE or TRANSITION day (920 of 1080 pooled), and that is where holding made most of its money (RANGE alone $+221532). The owner's rule puts targets on exactly those trades, so it cuts the winners short where the main book earns. Directional days are rarer (160 main trades), and there holding was ahead in the first half and behind in the second.

How to read this: one history, read many times (21 exit rules on these same entries now). A pass would not prove anything and a fail does not stop the owner from choosing a rule. What the owner adopts is read forward at 30 closed trades per market.

## The checks

### Equivalence gate (the study's runner copy vs engine15/shadows.run)

| Market | switch off = main | trades | switch on = b_targets | trades |
|---|---|---|---|---|
| SPX | same | 37 | same | 239 |
| USDJPY | same | 98 | same | 721 |
| BTCUSDT | same | 228 | same | 1060 |
| ETHUSDT | same | 208 | same | 1011 |
| XAUUSD | same | 115 | same | 750 |
| XAGUSD | same | 144 | same | 725 |
| WTI | same | 118 | same | 731 |
| BRENT | same | 132 | same | 721 |

Same = the same closed trades (entry and exit bar, side, words), prices, size, fees and P&L within $0.000001, the same final equity and the same open position at the end.

### Reconciliation with H59's "today" run

**Reproduced exactly: every book within one cent and the same trade count.**

| Market | Book | H59 net | Here | Diff $ | H59 trades | Here | Diff |
|---|---|---|---|---|---|---|---|
| SPX | `main` | $+6320 | $+6320 | +0.00 | 37 | 37 | +0 |
| SPX | `b_targets` | $+1283 | $+1283 | +0.00 | 239 | 239 | +0 |
| SPX | `be_t1` | $+5851 | $+5851 | +0.00 | 43 | 43 | +0 |
| SPX | `half_be_t1` | $+4438 | $+4438 | +0.00 | 43 | 43 | +0 |
| USDJPY | `main` | $+6965 | $+6965 | +0.00 | 98 | 98 | +0 |
| USDJPY | `b_targets` | $-579 | $-579 | +0.00 | 721 | 721 | +0 |
| USDJPY | `be_t1` | $+9061 | $+9061 | +0.00 | 122 | 122 | +0 |
| USDJPY | `half_be_t1` | $+4014 | $+4014 | +0.00 | 122 | 122 | +0 |
| BTCUSDT | `main` | $+25155 | $+25155 | +0.00 | 228 | 228 | +0 |
| BTCUSDT | `b_targets` | $-9224 | $-9224 | +0.00 | 1060 | 1060 | +0 |
| BTCUSDT | `be_t1` | $+23993 | $+23993 | +0.00 | 295 | 295 | +0 |
| BTCUSDT | `half_be_t1` | $+10355 | $+10355 | +0.00 | 295 | 295 | +0 |
| ETHUSDT | `main` | $+240638 | $+240638 | +0.00 | 208 | 208 | +0 |
| ETHUSDT | `b_targets` | $+4139 | $+4139 | +0.00 | 1011 | 1011 | +0 |
| ETHUSDT | `be_t1` | $+78291 | $+78291 | +0.00 | 299 | 299 | +0 |
| ETHUSDT | `half_be_t1` | $+57567 | $+57567 | +0.00 | 299 | 299 | +0 |
| XAUUSD | `main` | $+26565 | $+26565 | +0.00 | 115 | 115 | +0 |
| XAUUSD | `b_targets` | $-2500 | $-2500 | +0.00 | 750 | 750 | +0 |
| XAUUSD | `be_t1` | $+23094 | $+23094 | +0.00 | 147 | 147 | +0 |
| XAUUSD | `half_be_t1` | $+16787 | $+16787 | +0.00 | 147 | 147 | +0 |
| XAGUSD | `main` | $+3104 | $+3104 | +0.00 | 144 | 144 | +0 |
| XAGUSD | `b_targets` | $-6588 | $-6588 | +0.00 | 725 | 725 | +0 |
| XAGUSD | `be_t1` | $+1136 | $+1136 | +0.00 | 197 | 197 | +0 |
| XAGUSD | `half_be_t1` | $-1183 | $-1183 | +0.00 | 197 | 197 | +0 |
| WTI | `main` | $+24898 | $+24898 | +0.00 | 118 | 118 | +0 |
| WTI | `b_targets` | $-3230 | $-3230 | +0.00 | 731 | 731 | +0 |
| WTI | `be_t1` | $+17918 | $+17918 | +0.00 | 178 | 178 | +0 |
| WTI | `half_be_t1` | $+16812 | $+16812 | +0.00 | 178 | 178 | +0 |
| BRENT | `main` | $+5682 | $+5682 | +0.00 | 132 | 132 | +0 |
| BRENT | `b_targets` | $-4876 | $-4876 | +0.00 | 721 | 721 | +0 |
| BRENT | `be_t1` | $-1206 | $-1206 | +0.00 | 205 | 205 | +0 |
| BRENT | `half_be_t1` | $-816 | $-816 | +0.00 | 205 | 205 | +0 |

## (a) What each rule earned per trade, by the regime at entry

Every closed trade of `main` (hold to stop or flip) and of `b_targets` (half at Target 1, the rest at Target 2) is put in the bucket of the daily regime label on its decision bar. Halves by the trade's exit bar (before or after 2023-06-08). Mean = net dollars per trade.

| Market | Part | Directional: main trades / mean | Directional: b_targets trades / mean | Holds? | Other: main trades / mean | Other: b_targets trades / mean | Holds? |
|---|---|---|---|---|---|---|---|
| POOLED | all | 160 / $+24 | 1354 / $-8 | yes | 920 / $+290 | 4604 / $-3 | no |
| POOLED | first half | 124 / $+467 | 734 / $+6 | yes | 528 / $+160 | 2212 / $-5 | no |
| POOLED | second half | 36 / $-1501 | 620 / $-25 | no | 392 / $+466 | 2392 / $-1 | no |
| SPX | all | 1 / $+1900 | 52 / $+17 | yes | 36 / $+112 | 187 / $-1 | no |
| SPX | first half | 0 / $- | 16 / $-17 | no | 25 / $-56 | 78 / $+0 | yes |
| SPX | second half | 1 / $+1900 | 36 / $+33 | yes | 11 / $+495 | 109 / $-2 | no |
| USDJPY | all | 2 / $+85 | 148 / $-9 | yes | 96 / $+62 | 573 / $+1 | no |
| USDJPY | first half | 1 / $+620 | 78 / $+10 | yes | 36 / $+295 | 259 / $-11 | no |
| USDJPY | second half | 1 / $-450 | 70 / $-31 | no | 60 / $-77 | 314 / $+12 | yes |
| BTCUSDT | all | 39 / $-137 | 262 / $-3 | no | 189 / $+127 | 798 / $-11 | no |
| BTCUSDT | first half | 31 / $-77 | 125 / $+6 | no | 113 / $+27 | 343 / $-16 | no |
| BTCUSDT | second half | 8 / $-370 | 137 / $-11 | no | 76 / $+274 | 455 / $-7 | no |
| ETHUSDT | all | 46 / $-152 | 263 / $+1 | no | 162 / $+1245 | 748 / $+5 | no |
| ETHUSDT | first half | 35 / $+1105 | 152 / $-15 | yes | 92 / $+649 | 370 / $+11 | no |
| ETHUSDT | second half | 11 / $-4150 | 111 / $+23 | no | 70 / $+2027 | 378 / $-2 | no |
| XAUUSD | all | 11 / $-169 | 167 / $-20 | no | 104 / $+183 | 583 / $+1 | no |
| XAUUSD | first half | 9 / $-64 | 87 / $-28 | no | 83 / $-48 | 324 / $-11 | yes |
| XAUUSD | second half | 2 / $-642 | 80 / $-11 | no | 21 / $+1093 | 259 / $+17 | no |
| XAGUSD | all | 9 / $+83 | 166 / $-44 | yes | 135 / $-9 | 559 / $+1 | yes |
| XAGUSD | first half | 6 / $+202 | 76 / $-51 | yes | 65 / $+46 | 287 / $-2 | no |
| XAGUSD | second half | 3 / $-155 | 90 / $-38 | no | 70 / $-60 | 272 / $+4 | yes |
| WTI | all | 27 / $+592 | 150 / $+44 | yes | 91 / $+83 | 581 / $-18 | no |
| WTI | first half | 23 / $+850 | 104 / $+135 | yes | 51 / $+149 | 288 / $-19 | no |
| WTI | second half | 4 / $-887 | 46 / $-161 | no | 40 / $-2 | 293 / $-16 | no |
| BRENT | all | 25 / $-30 | 146 / $-42 | yes | 107 / $+57 | 575 / $+1 | no |
| BRENT | first half | 19 / $+43 | 96 / $-22 | yes | 63 / $+88 | 263 / $+16 | no |
| BRENT | second half | 6 / $-262 | 50 / $-82 | no | 44 / $+13 | 312 / $-11 | no |

The six labels, pooled, whole window (main / b_targets: trades, net, mean per trade, win rate):

| Label | main trades | main net | main mean | main win | b_targets trades | b_targets net | b_targets mean | b_targets win |
|---|---|---|---|---|---|---|---|---|
| TREND_UP | 65 | $+3821 | $+59 | 34% | 752 | $+28524 | $+38 | 45% |
| TREND_DOWN | 16 | $+11634 | $+727 | 38% | 215 | $+1721 | $+8 | 35% |
| MOMENTUM_UP | 47 | $-8996 | $-191 | 28% | 230 | $-7654 | $-33 | 47% |
| MOMENTUM_DOWN | 32 | $-2583 | $-81 | 28% | 157 | $-33713 | $-215 | 31% |
| RANGE | 595 | $+221532 | $+372 | 19% | 2799 | $+1005 | $+0 | 43% |
| TRANSITION | 325 | $+45529 | $+140 | 15% | 1805 | $-13539 | $-8 | 42% |

Per market and label (whole window; main mean / b_targets mean per trade, trades in brackets):

| Market | TREND_UP | TREND_DOWN | MOMENTUM_UP | MOMENTUM_DOWN | RANGE | TRANSITION |
|---|---|---|---|---|---|---|
| SPX | $- (0) / $+48 (46) | $+1900 (1) / $+11 (4) | - | $- (0) / $-668 (2) | $+404 (18) / $-8 (108) | $-179 (18) / $+9 (79) |
| USDJPY | $-450 (1) / $+2 (126) | $+620 (1) / $-73 (22) | - | - | $+46 (46) / $+2 (328) | $+78 (50) / $+1 (245) |
| BTCUSDT | $-283 (27) / $-1 (150) | $+223 (4) / $-52 (40) | $+461 (6) / $+276 (39) | $-670 (2) / $-283 (33) | $+292 (130) / $+4 (503) | $-238 (59) / $-36 (295) |
| ETHUSDT | $+751 (18) / $+59 (90) | $+4285 (2) / $+130 (47) | $-1080 (21) / $+11 (88) | $-1279 (5) / $-321 (38) | $+1070 (108) / $+22 (463) | $+1593 (54) / $-24 (285) |
| XAUUSD | $-47 (8) / $-1 (131) | $-642 (2) / $-59 (27) | $-199 (1) / $-154 (8) | $- (0) / $-379 (1) | $+259 (78) / $-5 (370) | $-47 (26) / $+13 (213) |
| XAGUSD | $+151 (7) / $-7 (83) | $-83 (1) / $-30 (38) | $- (0) / $-84 (35) | $-226 (1) / $-262 (10) | $+25 (85) / $-0 (317) | $-66 (50) / $+3 (242) |
| WTI | $-790 (2) / $+215 (67) | $- (0) / $+273 (13) | $+771 (14) / $-322 (31) | $+617 (11) / $-34 (39) | $+622 (52) / $-31 (355) | $-637 (39) / $+3 (226) |
| BRENT | $-346 (2) / $+121 (59) | $+203 (5) / $-66 (24) | $+64 (5) / $-181 (29) | $-108 (13) / $-191 (34) | $+49 (78) / $+6 (355) | $+78 (29) / $-6 (220) |

## (b) The five variants as whole books

Better than holding (H36's test): pooled net above main in BOTH halves, ahead of main in at least 5 of 8 markets, pooled max drawdown no worse.

| Book | Net P&L | vs main | Sharpe | Max DD | 1st half | 2nd half | 1st vs main | 2nd vs main | Markets ahead | Trades | Better than hold? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `main` | $+339325 | $+0 | 0.92 | -32.8% | $+152355 | $+186970 | $+0 | $+0 | 0/8 | 1080 | - |
| `b_targets` | $-21574 | $-360900 | -0.09 | -60.6% | $-4982 | $-16592 | $-157337 | $-203562 | 0/8 | 5958 | no |
| `be_t1` | $+158137 | $-181188 | 0.74 | -23.7% | $+107179 | $+50959 | $-45177 | $-136012 | 1/8 | 1486 | no |
| `half_be_t1` | $+107974 | $-231352 | 0.85 | -15.6% | $+73795 | $+34179 | $-78560 | $-152791 | 0/8 | 1486 | no |
| `rg_dir_entry` | $+41188 | $-298137 | 0.37 | -36.7% | $+24490 | $+16698 | $-127865 | $-170273 | 2/8 | 3880 | no |
| `rg_dir_aligned` | $+37315 | $-302010 | 0.36 | -37.3% | $+20550 | $+16765 | $-131805 | $-170205 | 1/8 | 4012 | no |
| `rg_dir_live` | $-43404 | $-382729 | -0.40 | -72.6% | $-20745 | $-22659 | $-173100 | $-209630 | 0/8 | 5245 | no |
| `rg_mom_entry` | $-6942 | $-346267 | 0.06 | -48.5% | $-1692 | $-5250 | $-154047 | $-192220 | 0/8 | 5469 | no |
| `rg_dir_entry_inv` | $+232932 | $-106393 | 0.85 | -27.0% | $+102876 | $+130056 | $-49479 | $-56914 | 4/8 | 1200 | no |

Variant 1 (`rg_dir_entry`) minus the control (`rg_dir_entry_inv`): first half $-78386, second half $-113359.

Net P&L per market, whole window (first half / second half below each):

| Market | `main` | `b_targets` | `be_t1` | `half_be_t1` | `rg_dir_entry` | `rg_dir_aligned` | `rg_dir_live` | `rg_mom_entry` | `rg_dir_entry_inv` |
|---|---|---|---|---|---|---|---|---|---|
| SPX | $+6320 | $+1283 | $+5851 | $+4438 | $+9268 | $+9268 | $-829 | $+1283 | $+6486 |
| (halves) | -688 / +7007 | -280 / +1563 | -1012 / +6863 | -463 / +4900 | +115 / +9153 | +115 / +9153 | -252 / -577 | -280 / +1563 | -688 / +7173 |
| USDJPY | $+6965 | $-579 | $+9061 | $+4014 | $+1403 | $+3245 | $-4174 | $-579 | $+7657 |
| (halves) | +14462 / -7497 | -1986 / +1407 | +16804 / -7743 | +8980 / -4966 | +9713 / -8310 | +9788 / -6543 | -4075 / -99 | -1986 / +1407 | +15279 / -7623 |
| BTCUSDT | $+25155 | $-9224 | $+23993 | $+10355 | $-2859 | $-5671 | $-9243 | $-8867 | $+17076 |
| (halves) | +1020 / +24135 | -4583 / -4641 | +1588 / +22405 | +411 / +9944 | -368 / -2491 | -1740 / -3931 | -5421 / -3822 | -3667 / -5200 | +343 / +16733 |
| ETHUSDT | $+240638 | $+4139 | $+78291 | $+57567 | $+27156 | $+30338 | $-6092 | $+11457 | $+138694 |
| (halves) | +99542 / +141096 | +1600 / +2539 | +30457 / +47834 | +22124 / +35443 | +5919 / +21238 | +7004 / +23334 | -7316 / +1225 | -951 / +12408 | +50212 / +88482 |
| XAUUSD | $+26565 | $-2500 | $+23094 | $+16787 | $+4828 | $+3842 | $-4239 | $-2878 | $+27677 |
| (halves) | -3012 / +29576 | -5993 / +3493 | -2530 / +25624 | -594 / +17381 | -5908 / +10735 | -6180 / +10021 | -5855 / +1616 | -5993 / +3115 | -2942 / +30619 |
| XAGUSD | $+3104 | $-6588 | $+1136 | $-1183 | $+4772 | $+1158 | $-7465 | $-1348 | $+2512 |
| (halves) | +4137 / -1033 | -4353 / -2235 | +1112 / +23 | -874 / -309 | -2847 / +7619 | -3755 / +4913 | -4838 / -2627 | -2856 / +1508 | +3778 / -1266 |
| WTI | $+24898 | $-3230 | $+17918 | $+16812 | $-1557 | $-1272 | $-4241 | $-847 | $+29627 |
| (halves) | +29593 / -4696 | +8511 / -11741 | +45884 / -27966 | +35250 / -18438 | +13227 / -14785 | +12892 / -14164 | +8629 / -12870 | +13655 / -14502 | +30987 / -1360 |
| BRENT | $+5682 | $-4876 | $-1206 | $-816 | $-1822 | $-3592 | $-7122 | $-5163 | $+3204 |
| (halves) | +7300 / -1619 | +2103 / -6979 | +14875 / -16082 | +8961 / -9777 | +4640 / -6462 | +2427 / -6020 | -1616 / -5506 | +386 / -5550 | +5906 / -2702 |

Trades per variant by the mode they ran in (target / flip), whole window (`rg_dir_live` decides bar by bar, so every trade counts as target-eligible there):

| Market | `rg_dir_entry` | `rg_dir_aligned` | `rg_dir_live` | `rg_mom_entry` | `rg_dir_entry_inv` |
|---|---|---|---|---|---|
| SPX | 75 / 13 | 75 / 13 | 215 / 0 | 237 / 2 | 7 / 37 |
| USDJPY | 371 / 55 | 377 / 43 | 623 / 0 | 721 / 0 | 5 / 91 |
| BTCUSDT | 593 / 111 | 665 / 80 | 896 / 0 | 915 / 44 | 64 / 202 |
| ETHUSDT | 544 / 105 | 603 / 73 | 902 / 0 | 758 / 65 | 83 / 172 |
| XAUUSD | 413 / 47 | 419 / 41 | 617 / 0 | 742 / 6 | 13 / 103 |
| XAGUSD | 443 / 63 | 486 / 51 | 613 / 0 | 632 / 14 | 12 / 143 |
| WTI | 475 / 70 | 492 / 56 | 680 / 0 | 602 / 53 | 32 / 91 |
| BRENT | 425 / 77 | 482 / 56 | 699 / 0 | 629 / 49 | 28 / 117 |

## (c) One rule per market

Menu: `main`, `be_t1`, `half_be_t1`, `b_targets`, `rg_dir_entry`, `rg_dir_aligned`, `rg_dir_live`, `rg_mom_entry`. The rule with the most net P&L in the first half (to 2023-06-08) is picked for each market (ties: the earlier name), then its second half is set beside main's second half.

| Market | First-half pick | Pick, 1st half | Main, 1st half | Pick, 2nd half | Main, 2nd half | Ahead? | Best over whole window | Same? |
|---|---|---|---|---|---|---|---|---|
| SPX | `rg_dir_entry` | $+115 | $-688 | $+9153 | $+7007 | yes | `rg_dir_entry` | yes |
| USDJPY | `be_t1` | $+16804 | $+14462 | $-7743 | $-7497 | no | `be_t1` | yes |
| BTCUSDT | `be_t1` | $+1588 | $+1020 | $+22405 | $+24135 | no | `main` | no |
| ETHUSDT | `main` | $+99542 | $+99542 | $+141096 | $+141096 | no | `main` | yes |
| XAUUSD | `half_be_t1` | $-594 | $-3012 | $+17381 | $+29576 | no | `main` | no |
| XAGUSD | `main` | $+4137 | $+4137 | $-1033 | $-1033 | no | `rg_dir_entry` | no |
| WTI | `be_t1` | $+45884 | $+29593 | $-27966 | $-4696 | no | `main` | no |
| BRENT | `be_t1` | $+14875 | $+7300 | $-16082 | $-1619 | no | `main` | no |
| **Together** | | | | $+137211 | $+186970 | 1/8 | | 3/8 |

## How often each market is in each regime (description only)

Share of 15-minute sessions in the window with each daily label (main's trades in brackets, by the label at entry).

| Market | TREND_UP | TREND_DOWN | MOMENTUM_UP | MOMENTUM_DOWN | RANGE | TRANSITION | no label | Directional |
|---|---|---|---|---|---|---|---|---|
| SPX | 18.5% (0) | 1.8% (1) | 0.1% (0) | 0.3% (0) | 45.8% (18) | 33.6% (18) | 0.0% (0) | 20.6% (1) |
| USDJPY | 17.2% (1) | 2.4% (1) | 0.0% (0) | 0.0% (0) | 46.7% (46) | 33.8% (50) | 0.0% (0) | 19.5% (2) |
| BTCUSDT | 11.4% (27) | 5.8% (4) | 5.2% (6) | 3.7% (2) | 47.0% (130) | 26.9% (59) | 0.0% (0) | 26.1% (39) |
| ETHUSDT | 7.5% (18) | 6.2% (2) | 7.8% (21) | 4.7% (5) | 43.9% (108) | 30.0% (54) | 0.0% (0) | 26.2% (46) |
| XAUUSD | 15.7% (8) | 4.0% (2) | 0.5% (1) | 0.1% (0) | 48.1% (78) | 31.6% (26) | 0.0% (0) | 20.3% (11) |
| XAGUSD | 12.0% (7) | 5.5% (1) | 2.5% (0) | 1.5% (1) | 44.6% (85) | 33.9% (50) | 0.0% (0) | 21.5% (9) |
| WTI | 9.5% (2) | 2.1% (0) | 3.2% (14) | 4.1% (11) | 50.6% (52) | 30.5% (39) | 0.0% (0) | 18.9% (27) |
| BRENT | 9.3% (2) | 2.9% (5) | 2.7% (5) | 3.7% (13) | 49.8% (78) | 31.6% (29) | 0.0% (0) | 18.6% (25) |

Conventions: the regime is the engine's own daily label (`ev["regime"]`, last closed daily bar). A trade's regime is the label on its decision bar (the bar before the fill). In `rg_dir_live` a target in a bar is acted on only if the label known before that bar opened (the previous row) is not directional; once half is off at Target 1 the stop stays at the entry. Sharpe on daily marked equity, sqrt(365). Pooled: markets' daily equity summed. (c)'s sums are the per-market half results added up.

## Details the registration did not fix (disclosed)

- The runner copy keeps every code line of `shadows.run` (two comments shortened); the switch replaces `use_targets` per trade (and per bar in `rg_dir_live`). With the switch on, the stop word after Target 1 is `STOP_BE` as in `b_targets`.
- `rg_dir_live`: the regime of bar i is the label on row i - 1 (known before the bar trades); row i already contains the daily bar that bar i closes.
- Halves in (a) and (c) are split by the trade's exit bar, as H59's half statistics are. A row with no label would count as "other"; there were none in these windows.
- Means in (a) are dollars per trade, so ETH (the largest book) weighs most in the pooled line; the mean percent per trade is in results.json.
- The refits were not recomputed: H59's cached refits (`fits_today`) were copied into this study's own folder on the server before the run; the reconciliation above then held exactly.
