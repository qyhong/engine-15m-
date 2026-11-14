# Surprise mining (charter L1): last 1 days

Generated 2026-11-14 00:01. History 2020-01-01 to 2026-11-13 23:45; first half H1 to 2023-06-08, second half H2 after. All times UTC.

**These are leads, not proven edges.** Anything worth keeping goes into `research/HYPOTHESES.md` and is graded forward.

## What counts as a surprise

A move from the close of a 15m bar to the close 1 hour (4 bars) or 4 hours (16 bars) later, measured in units of the 1-hour ATR at the start, in the top 2% by size for that coin. Cut points: BTC 2.05 ATR (1h) / 4.36 ATR (4h); ETH 2.00 ATR (1h) / 4.21 ATR (4h). Overlapping bars of one move count once. Found: BTC 2085 (1h) and 708 (4h); ETH 2097 (1h) and 725 (4h).

Where the engine stood when they started (replay and live): right side 2865, WRONG side 2628, no record 68, flat (missed) 54.

## The 5 biggest surprises of the last 1 days

| Start (UTC) | Coin | Move | Over | Before it | Engine |
|---|---|---|---|---|---|
| 2026-11-13 02:00 | ETH | DOWN -6.2 ATR (-4.97%) | 4h | wild, trend down, flow balanced, near 24h low, last hour flat; next_bar_top_of_hour | right side: live journal: SHORT at 2026-11-13 02:15 UTC; decision at the surprise bar: HOLD (edge_still_with_position, edge -3.5 pts) |
| 2026-11-13 02:00 | BTC | DOWN -6.0 ATR (-3.95%) | 4h | wild, trend down, flow selling, near 24h low, last hour fell; at_7d_low, next_bar_top_of_hour | right side: live journal: SHORT at 2026-11-13 02:15 UTC; decision at the surprise bar: HOLD (edge_still_with_position, edge -4.9 pts) |
| 2026-11-13 03:00 | ETH | DOWN -3.2 ATR (-2.80%) | 1h | wild, trend down, flow selling, near 24h low, last hour fell; vol_building, volume_surge, at_7d_low, flow_sell_1h, next_bar_top_of_hour | right side: live journal: SHORT at 2026-11-13 03:15 UTC; decision at the surprise bar: HOLD (edge_still_with_position, edge -8.3 pts) |
| 2026-11-13 03:00 | BTC | DOWN -2.5 ATR (-1.83%) | 1h | wild, trend down, flow selling, near 24h low, last hour fell; vol_building, volume_surge, at_7d_low, ran_down_4h, flow_sell_1h, next_bar_top_of_hour | right side: live journal: SHORT at 2026-11-13 03:15 UTC; decision at the surprise bar: HOLD (edge_still_with_position, edge -12.1 pts) |
| 2026-11-13 14:45 | ETH | DOWN -2.1 ATR (-2.31%) | 1h | wild, trend down, flow buying, middle of 24h range, last hour fell; release_last_2h | right side: live journal: SHORT at 2026-11-13 15:00 UTC; decision at the surprise bar: HOLD (edge_still_with_position, edge -3.6 pts) |

## What repeats before surprises

Lift = how many times more common a reading was at the close just before a surprise than at an ordinary bar (1.00 = no difference). k/n = surprise bars with the reading / all surprise bars. Listed only if it leans the same way in all four tests (BTC and ETH, H1 and H2). 'Chance' = how often a top-2% move followed any bar with this reading, against all bars.

**Luck count:** 456 tests (38 precursors x 6 surprise groups (1h and 4h; any, up, down) x 2 (more often / less often), where all four tests have data); 68 passed (lift on the same side of 1 in all four tests (BTC/ETH x first/second half), at least 5 surprise bars each, binomial |z| >= 1.5 each). With the surprise times slid to random places (30 placebo runs) 2.77 passed on average (95th percentile 10.1, max 12.0). Big moves bunch together in volatile weeks, so the simple z-score overstates the evidence; the placebo keeps that bunching. Per reading, 'Luck' is the share of placebo runs in which that same reading passed too: **68** passing readings passed in at most 10% of placebo runs ('robust').

### More common before surprises

| Before | Reading | BTC H1 lift (k/n) | BTC H2 lift (k/n) | ETH H1 lift (k/n) | ETH H2 lift (k/n) | Chance with / all bars | Luck |
|---|---|---|---|---|---|---|---|
| big 1h moves, either way | session=London+NY overlap: L2 state: London+NY overlap (session) | 1.96 (223/957) | 2.96 (398/1128) | 1.92 (224/981) | 2.47 (328/1116) | BTC 5.0% / 2.0%; ETH 4.3% / 2.0% | 0% |
| big 1h moves UP | session=London+NY overlap: L2 state: London+NY overlap (session) | 2.19 (128/491) | 2.84 (191/564) | 2.14 (124/488) | 2.17 (140/542) | BTC 5.0% / 2.0%; ETH 4.3% / 2.0% | 0% |
| big 1h moves, either way | volume_surge: last hour's volume is high against the month (top tenth) | 1.89 (181/957) | 1.95 (245/1128) | 1.83 (180/981) | 1.72 (204/1116) | BTC 4.1% / 2.0%; ETH 3.8% / 2.0% | 0% |
| big 1h moves, either way | vol_building: the last 4h ranges are wide against the last 24h (top fifth): volatility building | 1.47 (281/957) | 1.60 (459/1128) | 1.43 (281/981) | 1.50 (405/1116) | BTC 3.2% / 2.0%; ETH 3.1% / 2.0% | 0% |
| big 1h moves, either way | release_last_2h: a US high-impact release printed in the last 2 hours (calendar from May 2026 only) | 2.44 (44/957) | 3.95 (80/1128) | 2.60 (48/981) | 3.35 (67/1116) | BTC 6.7% / 2.0%; ETH 5.9% / 2.0% | 0% |
| big 1h moves UP | place=near 24h high: L2 state: near 24h high (place) | 1.51 (248/491) | 1.37 (245/564) | 1.46 (238/488) | 1.41 (224/542) | BTC 2.5% / 2.0%; ETH 2.3% / 2.0% | 0% |
| big 1h moves UP | at_7d_high: within 1 ATR of the 7-day high | 2.26 (70/491) | 2.20 (69/564) | 1.99 (73/488) | 2.12 (58/542) | BTC 4.1% / 2.0%; ETH 3.3% / 2.0% | 0% |
| big 1h moves DOWN | session=London+NY overlap: L2 state: London+NY overlap (session) | 1.71 (95/466) | 3.08 (207/564) | 1.71 (100/493) | 2.75 (188/574) | BTC 5.0% / 2.0%; ETH 4.3% / 2.0% | 0% |
| big 1h moves DOWN | volume_surge: last hour's volume is high against the month (top tenth) | 1.93 (90/466) | 2.01 (126/564) | 1.74 (86/493) | 1.77 (108/574) | BTC 4.1% / 2.0%; ETH 3.8% / 2.0% | 0% |
| big 1h moves, either way | release_within_2h: a US high-impact release is due within 2 hours (calendar from May 2026 only) | 2.22 (45/957) | 2.16 (49/1128) | 2.21 (46/981) | 2.13 (48/1116) | BTC 4.9% / 2.0%; ETH 4.8% / 2.0% | 0% |
| big 1h moves UP | volume_surge: last hour's volume is high against the month (top tenth) | 1.85 (91/491) | 1.90 (119/564) | 1.93 (94/488) | 1.67 (96/542) | BTC 4.1% / 2.0%; ETH 3.8% / 2.0% | 0% |
| big 4h moves, either way | session=London+NY overlap: L2 state: London+NY overlap (session) | 1.83 (67/308) | 2.87 (137/400) | 1.86 (74/335) | 2.67 (124/390) | BTC 4.6% / 2.0%; ETH 4.3% / 2.0% | 0% |
| big 1h moves DOWN | vol_building: the last 4h ranges are wide against the last 24h (top fifth): volatility building | 1.51 (141/466) | 1.64 (235/564) | 1.45 (143/493) | 1.50 (207/574) | BTC 3.2% / 2.0%; ETH 3.1% / 2.0% | 0% |
| big 1h moves DOWN | place=near 24h low: L2 state: near 24h low (place) | 1.40 (217/466) | 1.29 (252/564) | 1.51 (248/493) | 1.34 (281/574) | BTC 2.0% / 2.0%; ETH 2.1% / 2.0% | 0% |
| big 1h moves, either way | at_7d_high: within 1 ATR of the 7-day high | 1.97 (119/957) | 1.81 (114/1128) | 1.53 (113/981) | 1.63 (92/1116) | BTC 4.1% / 2.0%; ETH 3.3% / 2.0% | 0% |
| big 1h moves, either way | vol=wild: L2 state: wild (vol) | 1.26 (403/957) | 1.44 (570/1128) | 1.21 (396/981) | 1.32 (507/1116) | BTC 2.8% / 2.0%; ETH 2.6% / 2.0% | 0% |
| big 1h moves UP | vol_building: the last 4h ranges are wide against the last 24h (top fifth): volatility building | 1.43 (140/491) | 1.57 (224/564) | 1.41 (138/488) | 1.51 (198/542) | BTC 3.2% / 2.0%; ETH 3.1% / 2.0% | 0% |
| big 1h moves UP | release_last_2h: a US high-impact release printed in the last 2 hours (calendar from May 2026 only) | 2.49 (23/491) | 3.26 (33/564) | 2.61 (24/488) | 2.47 (24/542) | BTC 6.7% / 2.0%; ETH 5.9% / 2.0% | 0% |
| big 1h moves, either way | ran_down_4h: the last 4 hours fell hard (bottom tenth, ATR units) | 1.46 (140/957) | 1.38 (174/1128) | 1.56 (153/981) | 1.51 (175/1116) | BTC 2.9% / 2.0%; ETH 3.2% / 2.0% | 0% |
| big 1h moves DOWN | ran_down_4h: the last 4 hours fell hard (bottom tenth, ATR units) | 1.65 (77/466) | 1.52 (96/564) | 1.95 (96/493) | 1.76 (105/574) | BTC 2.9% / 2.0%; ETH 3.2% / 2.0% | 0% |
| big 1h moves DOWN | at_7d_low: within 1 ATR of the 7-day low | 2.77 (40/466) | 2.00 (36/564) | 3.16 (44/493) | 2.62 (38/574) | BTC 3.5% / 2.0%; ETH 4.6% / 2.0% | 0% |
| big 1h moves, either way | at_7d_low: within 1 ATR of the 7-day low | 1.89 (56/957) | 1.70 (61/1128) | 2.24 (62/981) | 1.88 (53/1116) | BTC 3.5% / 2.0%; ETH 4.6% / 2.0% | 0% |
| big 1h moves, either way | next_bar_1330_or_1430: the next 15m bar opens at 13:30 or 14:30 UTC on a weekday (US data releases / stock open) | 2.11 (30/957) | 5.00 (84/1128) | 2.67 (39/981) | 3.31 (55/1116) | BTC 7.3% / 2.0%; ETH 6.0% / 2.0% | 0% |
| big 1h moves DOWN | release_last_2h: a US high-impact release printed in the last 2 hours (calendar from May 2026 only) | 2.39 (21/466) | 4.65 (47/564) | 2.59 (24/493) | 4.18 (43/574) | BTC 6.7% / 2.0%; ETH 5.9% / 2.0% | 0% |
| big 4h moves UP | session=London+NY overlap: L2 state: London+NY overlap (session) | 1.92 (34/149) | 2.59 (62/201) | 2.10 (44/176) | 2.47 (56/190) | BTC 4.6% / 2.0%; ETH 4.3% / 2.0% | 0% |

### Less common before surprises

| Before | Reading | BTC H1 lift (k/n) | BTC H2 lift (k/n) | ETH H1 lift (k/n) | ETH H2 lift (k/n) | Chance with / all bars | Luck |
|---|---|---|---|---|---|---|---|
| big 1h moves UP | place=near 24h low: L2 state: near 24h low (place) | 0.75 (123/491) | 0.78 (152/564) | 0.75 (122/488) | 0.78 (155/542) | BTC 2.0% / 2.0%; ETH 2.1% / 2.0% | 0% |
| big 1h moves, either way | place=middle of 24h range: L2 state: middle of 24h range (place) | 0.72 (229/957) | 0.81 (308/1128) | 0.78 (255/981) | 0.85 (322/1116) | BTC 1.5% / 2.0%; ETH 1.6% / 2.0% | 0% |
| big 1h moves DOWN | place=middle of 24h range: L2 state: middle of 24h range (place) | 0.70 (109/466) | 0.74 (141/564) | 0.77 (127/493) | 0.81 (159/574) | BTC 1.5% / 2.0%; ETH 1.6% / 2.0% | 0% |
| big 1h moves, either way | session=Asia: L2 state: Asia (session) | 0.83 (213/957) | 0.67 (202/1128) | 0.76 (200/981) | 0.67 (200/1116) | BTC 1.5% / 2.0%; ETH 1.4% / 2.0% | 0% |
| big 1h moves, either way | move=flat: L2 state: flat (move) | 0.84 (267/957) | 0.71 (251/1128) | 0.87 (284/981) | 0.85 (318/1116) | BTC 1.4% / 2.0%; ETH 1.6% / 2.0% | 0% |
| big 1h moves, either way | vol=quiet: L2 state: quiet (vol) | 0.86 (276/957) | 0.59 (234/1128) | 0.89 (291/981) | 0.72 (278/1116) | BTC 1.4% / 2.0%; ETH 1.6% / 2.0% | 0% |
| big 1h moves DOWN | vol=quiet: L2 state: quiet (vol) | 0.76 (118/466) | 0.52 (104/564) | 0.85 (139/493) | 0.67 (132/574) | BTC 1.4% / 2.0%; ETH 1.6% / 2.0% | 0% |
| big 1h moves DOWN | session=Asia: L2 state: Asia (session) | 0.82 (103/466) | 0.69 (105/564) | 0.73 (97/493) | 0.63 (97/574) | BTC 1.5% / 2.0%; ETH 1.4% / 2.0% | 0% |
| big 1h moves UP | session=Asia: L2 state: Asia (session) | 0.84 (110/491) | 0.64 (97/564) | 0.79 (103/488) | 0.71 (103/542) | BTC 1.5% / 2.0%; ETH 1.4% / 2.0% | 0% |
| big 1h moves UP | place=middle of 24h range: L2 state: middle of 24h range (place) | 0.73 (120/491) | 0.88 (167/564) | 0.79 (128/488) | 0.88 (163/542) | BTC 1.5% / 2.0%; ETH 1.6% / 2.0% | 0% |
| big 1h moves, either way | session=weekend: L2 state: weekend (session) | 0.85 (233/957) | 0.79 (253/1128) | 0.90 (253/981) | 0.84 (268/1116) | BTC 1.6% / 2.0%; ETH 1.8% / 2.0% | 3% |
| big 4h moves, either way | session=Asia: L2 state: Asia (session) | 0.82 (68/308) | 0.64 (68/400) | 0.75 (67/335) | 0.58 (61/390) | BTC 1.4% / 2.0%; ETH 1.3% / 2.0% | 0% |
| big 1h moves UP | flow=selling: L2 state: selling (flow) | 0.75 (123/491) | 0.92 (240/564) | 0.72 (117/488) | 0.92 (212/542) | BTC 1.8% / 2.0%; ETH 2.0% / 2.0% | 0% |
| big 1h moves UP | session=weekend: L2 state: weekend (session) | 0.87 (122/491) | 0.83 (134/564) | 0.88 (123/488) | 0.89 (137/542) | BTC 1.6% / 2.0%; ETH 1.8% / 2.0% | 0% |
| big 4h moves DOWN | session=Asia: L2 state: Asia (session) | 0.75 (32/159) | 0.60 (32/199) | 0.80 (34/159) | 0.60 (32/200) | BTC 1.4% / 2.0%; ETH 1.3% / 2.0% | 0% |

## The engine's worst calls (history replay)

Rule: bottom 10% of closed replay trades by P&L, per coin. BTC: 317 closed trades, worst cut -4.36%, 32 worst; ETH: 237 closed trades, worst cut -4.77%, 24 worst. Readings are taken at the close where the call was made.

Readings more common at the worst calls than at all the engine's entries (small samples: read as hints only):

| Reading | Worst calls with it | All entries with it | Lift | z |
|---|---|---|---|---|
| funding_high: funding rate high (top tenth): longs paying a lot | 13/56 | 48/554 | 2.68 | 3.87 |
| trend=down: L2 state: down (trend) | 4/56 | 13/554 | 3.04 | 2.37 |
| vol=wild: L2 state: wild (vol) | 47/56 | 385/554 | 1.21 | 2.35 |
| move=fell: L2 state: fell (move) | 33/56 | 246/554 | 1.33 | 2.19 |
| volume_surge: last hour's volume is high against the month (top tenth) | 31/56 | 240/554 | 1.28 | 1.82 |
| session=Asia: L2 state: Asia (session) | 18/56 | 136/554 | 1.31 | 1.32 |
| funding_low: funding rate low (bottom tenth): shorts paying / longs cheap | 5/56 | 31/554 | 1.60 | 1.09 |
| place=middle of 24h range: L2 state: middle of 24h range (place) | 10/56 | 72/554 | 1.37 | 1.08 |
| release_last_2h: a US high-impact release printed in the last 2 hours (calendar from May 2026 only) | 4/56 | 25/554 | 1.58 | 0.95 |
| ran_down_4h: the last 4 hours fell hard (bottom tenth, ATR units) | 26/56 | 224/554 | 1.15 | 0.91 |

The ten worst:

| Call (UTC) | Coin | Side | Why in -> why out | P&L | Held | State at the call |
|---|---|---|---|---|---|---|
| 2024-08-05 19:00 | ETH | SHORT | FLIP -> STOP | -11.73% | 74.8 h | wild, trend down, New York, flow balanced, middle of 24h range, last hour fell; volume_surge, flow_sell_1h, funding_low, next_bar_top_of_hour |
| 2021-01-29 10:15 | BTC | LONG | FORCED -> STOP | -9.17% | 17.0 h | wild, trend mixed, London, flow buying, near 24h high, last hour rose; vol_building, volume_surge, ran_up_4h, funding_high |
| 2024-08-05 19:00 | BTC | SHORT | FLIP -> STOP | -9.02% | 65.5 h | wild, trend down, New York, flow buying, middle of 24h range, last hour fell; volume_surge, next_bar_top_of_hour |
| 2020-11-26 08:30 | ETH | SHORT | FLIP -> FLIP | -8.38% | 59.5 h | wild, trend mixed, London, flow selling, near 24h low, last hour fell; vol_building, volume_surge, at_24h_low, ran_down_4h, flow_sell_1h |
| 2021-01-10 23:15 | BTC | LONG | FORCED -> STOP | -8.08% | 4.0 h | wild, trend mixed, weekend, flow selling, middle of 24h range, last hour fell; vol_building, funding_high |
| 2021-05-14 12:45 | ETH | LONG | FLIP -> STOP | -8.00% | 30.5 h | normal, trend up, London+NY overlap, flow balanced, near 24h high, last hour fell; at_24h_high, release_last_2h |
| 2021-01-10 20:30 | BTC | SHORT | FLIP -> STOP | -7.66% | 1.5 h | wild, trend mixed, weekend, flow selling, near 24h low, last hour fell; vol_building, volume_surge, ran_down_4h, flow_sell_1h, funding_high |
| 2021-05-12 19:15 | ETH | SHORT | FLIP -> STOP | -7.57% | 3.5 h | wild, trend up, New York, flow selling, near 24h low, last hour fell; vol_building, volume_surge, at_24h_low, ran_down_4h, funding_high |
| 2021-01-14 00:00 | BTC | LONG | FLIP -> STOP | -7.42% | 40.0 h | wild, trend up, Asia, flow balanced, near 24h high, last hour flat; ran_up_4h, funding_high, next_bar_top_of_hour, next_bar_daily_open |
| 2021-01-15 16:15 | BTC | SHORT | ENTER -> STOP | -7.15% | 17.8 h | wild, trend mixed, New York, flow balanced, near 24h low, last hour fell; vol_building, volume_surge, ran_down_4h, funding_high |

## Limits

- Replay trades carry the time of the fill (next open); the call was made at the close of the bar before, which is where readings are snapshotted.
- The live journal covers only the days it has run; elsewhere the engine's side comes from the replay trades (no per-bar odds: out/replay/store.pkl is deliberately not loaded).
- The economic calendar on file starts May 2026, so the two release precursors cannot be tested in the first half and are skipped by the four-test rule.
- Surprises are measured close to close; a fill at the next open would see slightly less.
- Lift says a reading is more common before big moves; it does not say the move's direction unless the group is 'UP' or 'DOWN', and even then it is not a trade until graded forward.

