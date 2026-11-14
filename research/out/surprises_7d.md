# Surprise mining (charter L1): last 7 days

Generated 2026-11-10 16:27. History 2020-01-01 to 2026-11-10 16:00; first half H1 to 2023-06-06, second half H2 after. All times UTC.

**These are leads, not proven edges.** Anything worth keeping goes into `research/HYPOTHESES.md` and is graded forward.

## What counts as a surprise

A move from the close of a 15m bar to the close 1 hour (4 bars) or 4 hours (16 bars) later, measured in units of the 1-hour ATR at the start, in the top 2% by size for that coin. Cut points: BTC 2.05 ATR (1h) / 4.36 ATR (4h); ETH 2.00 ATR (1h) / 4.21 ATR (4h). Overlapping bars of one move count once. Found: BTC 2081 (1h) and 707 (4h); ETH 2094 (1h) and 724 (4h).

Where the engine stood when they started (replay and live): right side 2873, WRONG side 2620, no record 68, flat (missed) 45.

## The 10 biggest surprises of the last 7 days

| Start (UTC) | Coin | Move | Over | Before it | Engine |
|---|---|---|---|---|---|
| 2026-11-08 18:45 | ETH | DOWN -15.2 ATR (-4.94%) | 4h | quiet, trend down, flow selling, middle of 24h range, last hour rose; squeeze, vol_building | right side: replay trade SHORT from 2026-11-04 16:15 UTC (FORCED), out 2026-11-10 15:15 UTC (OPEN), +15.26% |
| 2026-11-08 21:00 | ETH | DOWN -13.9 ATR (-4.46%) | 1h | quiet, trend down, flow selling, near 24h low, last hour fell; squeeze, vol_building, flow_sell_1h, next_bar_top_of_hour | right side: replay trade SHORT from 2026-11-04 16:15 UTC (FORCED), out 2026-11-10 15:15 UTC (OPEN), +15.26% |
| 2026-11-05 12:00 | BTC | DOWN -10.7 ATR (-5.42%) | 4h | quiet, trend mixed, flow selling, near 24h high, last hour rose; flow_buy_1h, next_bar_top_of_hour | right side: replay trade SHORT from 2026-10-27 22:45 UTC (FORCED), out 2026-11-10 15:15 UTC (OPEN), +8.31% |
| 2026-11-05 12:00 | ETH | DOWN -9.7 ATR (-6.95%) | 4h | quiet, trend mixed, flow selling, near 24h high, last hour flat; next_bar_top_of_hour | right side: replay trade SHORT from 2026-11-04 16:15 UTC (FORCED), out 2026-11-10 15:15 UTC (OPEN), +15.26% |
| 2026-11-08 18:00 | BTC | DOWN -9.5 ATR (-2.14%) | 4h | quiet, trend down, flow selling, near 24h low, last hour flat; squeeze, vol_building, next_bar_top_of_hour | right side: replay trade SHORT from 2026-10-27 22:45 UTC (FORCED), out 2026-11-10 15:15 UTC (OPEN), +8.31% |
| 2026-11-08 21:00 | BTC | DOWN -9.4 ATR (-2.12%) | 1h | quiet, trend down, flow selling, near 24h low, last hour fell; squeeze, flow_sell_1h, next_bar_top_of_hour | right side: replay trade SHORT from 2026-10-27 22:45 UTC (FORCED), out 2026-11-10 15:15 UTC (OPEN), +8.31% |
| 2026-11-04 14:30 | ETH | UP +7.3 ATR (+5.33%) | 1h | normal, trend mixed, flow balanced, near 24h high, last hour fell; next_bar_1330_or_1430 | WRONG side: replay trade SHORT from 2026-10-22 17:00 UTC (ENTER), out 2026-11-04 15:00 UTC (STOP), -2.51% |
| 2026-11-04 12:15 | ETH | UP +7.1 ATR (+5.37%) | 4h | wild, trend mixed, flow buying, near 24h high, last hour fell | WRONG side: replay trade SHORT from 2026-10-22 17:00 UTC (ENTER), out 2026-11-04 15:00 UTC (STOP), -2.51% |
| 2026-11-05 14:30 | BTC | DOWN -7.1 ATR (-3.85%) | 1h | wild, trend mixed, flow selling, middle of 24h range, last hour fell; ran_down_4h, next_bar_1330_or_1430 | right side: replay trade SHORT from 2026-10-27 22:45 UTC (FORCED), out 2026-11-10 15:15 UTC (OPEN), +8.31% |
| 2026-11-05 14:30 | ETH | DOWN -6.1 ATR (-4.62%) | 1h | wild, trend mixed, flow selling, middle of 24h range, last hour fell; ran_down_4h, flow_sell_1h, next_bar_1330_or_1430 | right side: replay trade SHORT from 2026-11-04 16:15 UTC (FORCED), out 2026-11-10 15:15 UTC (OPEN), +15.26% |

## What repeats before surprises

Lift = how many times more common a reading was at the close just before a surprise than at an ordinary bar (1.00 = no difference). k/n = surprise bars with the reading / all surprise bars. Listed only if it leans the same way in all four tests (BTC and ETH, H1 and H2). 'Chance' = how often a top-2% move followed any bar with this reading, against all bars.

**Luck count:** 432 tests (38 precursors x 6 surprise groups (1h and 4h; any, up, down) x 2 (more often / less often), where all four tests have data); 61 passed (lift on the same side of 1 in all four tests (BTC/ETH x first/second half), at least 5 surprise bars each, binomial |z| >= 1.5 each). With the surprise times slid to random places (30 placebo runs) 8.63 passed on average (95th percentile 22.0, max 24.0). Big moves bunch together in volatile weeks, so the simple z-score overstates the evidence; the placebo keeps that bunching. Per reading, 'Luck' is the share of placebo runs in which that same reading passed too: **59** passing readings passed in at most 10% of placebo runs ('robust').

### More common before surprises

| Before | Reading | BTC H1 lift (k/n) | BTC H2 lift (k/n) | ETH H1 lift (k/n) | ETH H2 lift (k/n) | Chance with / all bars | Luck |
|---|---|---|---|---|---|---|---|
| big 1h moves, either way | session=London+NY overlap: L2 state: London+NY overlap (session) | 1.96 (223/957) | 2.96 (396/1124) | 1.92 (224/980) | 2.46 (327/1114) | BTC 5.0% / 2.0%; ETH 4.3% / 2.0% | 10% |
| big 1h moves UP | session=London+NY overlap: L2 state: London+NY overlap (session) | 2.19 (128/491) | 2.84 (191/564) | 2.14 (124/488) | 2.17 (140/542) | BTC 5.0% / 2.0%; ETH 4.3% / 2.0% | 7% |
| big 1h moves, either way | volume_surge: last hour's volume is high against the month (top tenth) | 1.89 (181/957) | 1.96 (245/1124) | 1.84 (180/980) | 1.72 (204/1114) | BTC 4.1% / 2.0%; ETH 3.8% / 2.0% | 0% |
| big 1h moves, either way | vol_building: the last 4h ranges are wide against the last 24h (top fifth): volatility building | 1.47 (281/957) | 1.61 (458/1124) | 1.43 (281/980) | 1.50 (404/1114) | BTC 3.2% / 2.0%; ETH 3.1% / 2.0% | 7% |
| big 1h moves UP | at_7d_high: within 1 ATR of the 7-day high | 2.25 (70/491) | 2.19 (69/564) | 1.98 (73/488) | 2.12 (58/542) | BTC 4.1% / 2.0%; ETH 3.3% / 2.0% | 0% |
| big 1h moves UP | place=near 24h high: L2 state: near 24h high (place) | 1.51 (248/491) | 1.37 (245/564) | 1.46 (238/488) | 1.40 (224/542) | BTC 2.5% / 2.0%; ETH 2.3% / 2.0% | 0% |
| big 1h moves DOWN | session=London+NY overlap: L2 state: London+NY overlap (session) | 1.71 (95/466) | 3.08 (205/560) | 1.71 (100/492) | 2.75 (187/572) | BTC 5.0% / 2.0%; ETH 4.3% / 2.0% | 7% |
| big 1h moves DOWN | volume_surge: last hour's volume is high against the month (top tenth) | 1.93 (90/466) | 2.00 (125/560) | 1.75 (86/492) | 1.76 (107/572) | BTC 4.1% / 2.0%; ETH 3.8% / 2.0% | 0% |
| big 1h moves UP | volume_surge: last hour's volume is high against the month (top tenth) | 1.85 (91/491) | 1.91 (120/564) | 1.93 (94/488) | 1.68 (97/542) | BTC 4.1% / 2.0%; ETH 3.8% / 2.0% | 3% |
| big 4h moves, either way | session=London+NY overlap: L2 state: London+NY overlap (session) | 1.83 (67/308) | 2.88 (137/399) | 1.86 (74/335) | 2.66 (123/389) | BTC 4.6% / 2.0%; ETH 4.3% / 2.0% | 0% |
| big 1h moves DOWN | vol_building: the last 4h ranges are wide against the last 24h (top fifth): volatility building | 1.51 (141/466) | 1.65 (234/560) | 1.45 (143/492) | 1.49 (206/572) | BTC 3.2% / 2.0%; ETH 3.1% / 2.0% | 7% |
| big 1h moves DOWN | place=near 24h low: L2 state: near 24h low (place) | 1.40 (217/466) | 1.29 (250/560) | 1.51 (248/492) | 1.34 (280/572) | BTC 2.0% / 2.0%; ETH 2.1% / 2.0% | 0% |
| big 1h moves, either way | at_7d_high: within 1 ATR of the 7-day high | 1.97 (119/957) | 1.82 (114/1124) | 1.53 (113/980) | 1.63 (92/1114) | BTC 4.1% / 2.0%; ETH 3.3% / 2.0% | 0% |
| big 1h moves, either way | vol=wild: L2 state: wild (vol) | 1.27 (404/957) | 1.45 (570/1124) | 1.21 (396/980) | 1.32 (506/1114) | BTC 2.8% / 2.0%; ETH 2.6% / 2.0% | 3% |
| big 1h moves UP | vol_building: the last 4h ranges are wide against the last 24h (top fifth): volatility building | 1.43 (140/491) | 1.57 (224/564) | 1.41 (138/488) | 1.52 (198/542) | BTC 3.2% / 2.0%; ETH 3.1% / 2.0% | 7% |
| big 1h moves, either way | ran_down_4h: the last 4 hours fell hard (bottom tenth, ATR units) | 1.46 (140/957) | 1.37 (172/1124) | 1.56 (153/980) | 1.52 (176/1114) | BTC 2.9% / 2.0%; ETH 3.2% / 2.0% | 3% |
| big 1h moves DOWN | ran_down_4h: the last 4 hours fell hard (bottom tenth, ATR units) | 1.65 (77/466) | 1.50 (94/560) | 1.95 (96/492) | 1.76 (105/572) | BTC 2.9% / 2.0%; ETH 3.2% / 2.0% | 0% |
| big 1h moves, either way | next_bar_1330_or_1430: the next 15m bar opens at 13:30 or 14:30 UTC on a weekday (US data releases / stock open) | 2.11 (30/957) | 5.02 (84/1124) | 2.68 (39/980) | 3.32 (55/1114) | BTC 7.3% / 2.0%; ETH 6.0% / 2.0% | 0% |
| big 4h moves UP | session=London+NY overlap: L2 state: London+NY overlap (session) | 1.92 (34/149) | 2.59 (62/201) | 2.10 (44/176) | 2.48 (56/190) | BTC 4.6% / 2.0%; ETH 4.3% / 2.0% | 0% |
| big 1h moves DOWN | vol=wild: L2 state: wild (vol) | 1.32 (205/466) | 1.51 (296/560) | 1.26 (207/492) | 1.43 (281/572) | BTC 2.8% / 2.0%; ETH 2.6% / 2.0% | 0% |
| big 1h moves, either way | at_7d_low: within 1 ATR of the 7-day low | 1.89 (56/957) | 1.68 (59/1124) | 2.24 (62/980) | 1.87 (52/1114) | BTC 3.4% / 2.0%; ETH 4.6% / 2.0% | 0% |
| big 1h moves DOWN | at_7d_low: within 1 ATR of the 7-day low | 2.77 (40/466) | 1.94 (34/560) | 3.16 (44/492) | 2.59 (37/572) | BTC 3.4% / 2.0%; ETH 4.6% / 2.0% | 0% |
| big 1h moves UP | ran_up_4h: the last 4 hours rose hard (top tenth, ATR units) | 2.12 (104/491) | 1.80 (111/564) | 1.66 (81/488) | 1.51 (77/542) | BTC 4.2% / 2.0%; ETH 3.1% / 2.0% | 0% |
| big 1h moves, either way | ran_up_4h: the last 4 hours rose hard (top tenth, ATR units) | 1.96 (188/957) | 1.88 (230/1124) | 1.36 (133/980) | 1.40 (147/1114) | BTC 4.2% / 2.0%; ETH 3.1% / 2.0% | 0% |
| big 1h moves DOWN | next_bar_1330_or_1430: the next 15m bar opens at 13:30 or 14:30 UTC on a weekday (US data releases / stock open) | 2.17 (15/466) | 5.76 (48/560) | 2.60 (19/492) | 3.76 (32/572) | BTC 7.3% / 2.0%; ETH 6.0% / 2.0% | 0% |

### Less common before surprises

| Before | Reading | BTC H1 lift (k/n) | BTC H2 lift (k/n) | ETH H1 lift (k/n) | ETH H2 lift (k/n) | Chance with / all bars | Luck |
|---|---|---|---|---|---|---|---|
| big 1h moves UP | place=near 24h low: L2 state: near 24h low (place) | 0.75 (123/491) | 0.78 (152/564) | 0.75 (122/488) | 0.78 (155/542) | BTC 2.0% / 2.0%; ETH 2.1% / 2.0% | 0% |
| big 1h moves, either way | place=middle of 24h range: L2 state: middle of 24h range (place) | 0.72 (229/957) | 0.81 (308/1124) | 0.78 (255/980) | 0.84 (320/1114) | BTC 1.5% / 2.0%; ETH 1.6% / 2.0% | 0% |
| big 1h moves DOWN | place=middle of 24h range: L2 state: middle of 24h range (place) | 0.70 (109/466) | 0.75 (141/560) | 0.77 (127/492) | 0.81 (157/572) | BTC 1.5% / 2.0%; ETH 1.6% / 2.0% | 0% |
| big 1h moves, either way | session=Asia: L2 state: Asia (session) | 0.83 (213/957) | 0.66 (200/1124) | 0.76 (200/980) | 0.66 (198/1114) | BTC 1.5% / 2.0%; ETH 1.4% / 2.0% | 3% |
| big 1h moves, either way | move=flat: L2 state: flat (move) | 0.84 (267/957) | 0.72 (251/1124) | 0.87 (283/980) | 0.85 (319/1114) | BTC 1.4% / 2.0%; ETH 1.6% / 2.0% | 0% |
| big 1h moves, either way | vol=quiet: L2 state: quiet (vol) | 0.86 (276/957) | 0.59 (233/1124) | 0.89 (290/980) | 0.73 (279/1114) | BTC 1.4% / 2.0%; ETH 1.6% / 2.0% | 3% |
| big 1h moves DOWN | vol=quiet: L2 state: quiet (vol) | 0.76 (118/466) | 0.52 (103/560) | 0.84 (138/492) | 0.67 (133/572) | BTC 1.4% / 2.0%; ETH 1.6% / 2.0% | 3% |
| big 1h moves DOWN | session=Asia: L2 state: Asia (session) | 0.82 (103/466) | 0.69 (103/560) | 0.74 (97/492) | 0.62 (95/572) | BTC 1.5% / 2.0%; ETH 1.4% / 2.0% | 3% |
| big 1h moves UP | session=Asia: L2 state: Asia (session) | 0.84 (110/491) | 0.64 (97/564) | 0.79 (103/488) | 0.71 (103/542) | BTC 1.5% / 2.0%; ETH 1.4% / 2.0% | 7% |
| big 1h moves UP | place=middle of 24h range: L2 state: middle of 24h range (place) | 0.73 (120/491) | 0.88 (167/564) | 0.79 (128/488) | 0.88 (163/542) | BTC 1.5% / 2.0%; ETH 1.6% / 2.0% | 0% |
| big 4h moves, either way | session=Asia: L2 state: Asia (session) | 0.82 (68/308) | 0.63 (67/399) | 0.75 (67/335) | 0.58 (60/389) | BTC 1.4% / 2.0%; ETH 1.3% / 2.0% | 7% |
| big 1h moves UP | flow=selling: L2 state: selling (flow) | 0.76 (124/491) | 0.92 (240/564) | 0.72 (117/488) | 0.92 (212/542) | BTC 1.8% / 2.0%; ETH 2.0% / 2.0% | 0% |
| big 1h moves UP | session=weekend: L2 state: weekend (session) | 0.87 (122/491) | 0.83 (134/564) | 0.88 (123/488) | 0.89 (137/542) | BTC 1.6% / 2.0%; ETH 1.8% / 2.0% | 10% |
| big 4h moves DOWN | session=Asia: L2 state: Asia (session) | 0.75 (32/159) | 0.58 (31/198) | 0.80 (34/159) | 0.58 (31/199) | BTC 1.4% / 2.0%; ETH 1.3% / 2.0% | 3% |
| big 1h moves DOWN | move=flat: L2 state: flat (move) | 0.81 (125/466) | 0.68 (118/560) | 0.90 (148/492) | 0.79 (152/572) | BTC 1.4% / 2.0%; ETH 1.6% / 2.0% | 0% |
| big 1h moves, either way | session=weekend: L2 state: weekend (session) | 0.85 (233/957) | 0.79 (253/1124) | 0.90 (253/980) | 0.84 (268/1114) | BTC 1.6% / 2.0%; ETH 1.8% / 2.0% | 23% |
| big 1h moves, either way | session=London: L2 state: London (session) | 0.85 (121/957) | 0.54 (91/1124) | 0.88 (129/980) | 0.74 (122/1114) | BTC 1.5% / 2.0%; ETH 1.7% / 2.0% | 30% |

## The engine's worst calls (history replay)

Rule: bottom 10% of closed replay trades by P&L, per coin. BTC: 280 closed trades, worst cut -4.28%, 28 worst; ETH: 235 closed trades, worst cut -5.06%, 24 worst. Readings are taken at the close where the call was made.

Readings more common at the worst calls than at all the engine's entries (small samples: read as hints only):

| Reading | Worst calls with it | All entries with it | Lift | z |
|---|---|---|---|---|
| funding_high: funding rate high (top tenth): longs paying a lot | 15/52 | 53/515 | 2.80 | 4.4 |
| at_24h_low: within 0.5 ATR of the 24h low | 13/52 | 74/515 | 1.74 | 2.19 |
| next_bar_top_of_hour: the next 15m bar opens on the hour | 20/52 | 130/515 | 1.52 | 2.19 |
| vol=wild: L2 state: wild (vol) | 44/52 | 368/515 | 1.18 | 2.1 |
| place=near 24h low: L2 state: near 24h low (place) | 31/52 | 233/515 | 1.32 | 2.08 |
| ran_down_4h: the last 4 hours fell hard (bottom tenth, ATR units) | 27/52 | 198/515 | 1.35 | 2.0 |
| move=fell: L2 state: fell (move) | 30/52 | 238/515 | 1.25 | 1.66 |
| volume_surge: last hour's volume is high against the month (top tenth) | 29/52 | 240/515 | 1.20 | 1.33 |
| flow=selling: L2 state: selling (flow) | 25/52 | 211/515 | 1.17 | 1.04 |
| flow_buy_1h: heavy net taker BUYING in the last hour (top tenth) | 7/52 | 55/515 | 1.26 | 0.65 |

The ten worst:

| Call (UTC) | Coin | Side | Why in -> why out | P&L | Held | State at the call |
|---|---|---|---|---|---|---|
| 2021-01-11 14:15 | ETH | SHORT | FLIP -> STOP | -17.72% | 15.5 h | wild, trend mixed, London+NY overlap, flow selling, near 24h low, last hour fell; vol_building, volume_surge, at_24h_low, at_7d_low, ran_down_4h, flow_sell_1h, funding_high |
| 2021-01-13 01:00 | ETH | SHORT | ENTER -> STOP | -13.06% | 19.2 h | wild, trend mixed, Asia, flow selling, near 24h low, last hour fell; squeeze, volume_surge, at_24h_low, ran_down_4h, flow_sell_1h, next_bar_top_of_hour |
| 2021-01-12 07:00 | ETH | LONG | FORCED -> STOP | -12.95% | 17.8 h | wild, trend mixed, London, flow buying, near 24h high, last hour flat; at_24h_high, next_bar_top_of_hour |
| 2021-01-11 07:00 | BTC | SHORT | FLIP -> STOP | -12.46% | 62.8 h | wild, trend mixed, London, flow selling, near 24h low, last hour fell; vol_building, volume_surge, at_24h_low, ran_down_4h, funding_high, next_bar_top_of_hour |
| 2021-01-29 20:00 | BTC | SHORT | ENTER -> STOP | -11.26% | 124.5 h | wild, trend up, New York, flow selling, near 24h low, last hour fell; volume_surge, ran_down_4h, funding_high, next_bar_top_of_hour |
| 2021-01-21 12:15 | ETH | SHORT | FLIP -> STOP | -9.60% | 64.5 h | wild, trend mixed, London+NY overlap, flow selling, near 24h low, last hour fell; vol_building, volume_surge, at_24h_low, ran_down_4h, funding_high |
| 2021-01-29 10:00 | BTC | LONG | FORCED -> STOP | -9.08% | 9.8 h | wild, trend mixed, London, flow buying, near 24h high, last hour rose; vol_building, volume_surge, ran_up_4h, flow_buy_1h, funding_high, next_bar_top_of_hour |
| 2021-01-15 16:15 | ETH | SHORT | FLIP -> STOP | -8.96% | 19.8 h | wild, trend up, New York, flow selling, near 24h low, last hour fell; vol_building, volume_surge, ran_down_4h, funding_high |
| 2021-01-26 14:45 | ETH | SHORT | ENTER -> STOP | -8.94% | 5.2 h | wild, trend mixed, London+NY overlap, flow selling, near 24h low, last hour fell; at_24h_low, ran_down_4h, flow_sell_1h |
| 2021-05-04 16:00 | ETH | SHORT | FLIP -> STOP | -8.63% | 30.2 h | wild, trend up, New York, flow balanced, near 24h low, last hour fell; vol_building, volume_surge, ran_down_4h, funding_high, next_bar_top_of_hour |

## Limits

- Replay trades carry the time of the fill (next open); the call was made at the close of the bar before, which is where readings are snapshotted.
- The live journal covers only the days it has run; elsewhere the engine's side comes from the replay trades (no per-bar odds: out/replay/store.pkl is deliberately not loaded).
- The economic calendar on file starts May 2026, so the two release precursors cannot be tested in the first half and are skipped by the four-test rule.
- Surprises are measured close to close; a fill at the next open would see slightly less.
- Lift says a reading is more common before big moves; it does not say the move's direction unless the group is 'UP' or 'DOWN', and even then it is not a trade until graded forward.

