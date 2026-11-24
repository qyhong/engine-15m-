# H113: how fast the Lead turns after a capitulation low (BTC and ETH)

Research only. Nothing in the engine, the books or the vault was changed. Registered in
`research/HYPOTHESES.md` (H113, commit 5a2241c) before any number below was computed.

This is a replay on history. A replay is post-mortem material. It is not validation, and nothing here shows
that a reading or a rule has an edge.

## In short

**The test (part b): the two halves pass, the holdout does not confirm, so no proposal follows.**

The claim was that Setups shorts opened in the 48 hours after a capitulation rebound do worse than the book's
other shorts.

- First half: 58 such shorts averaged -0.085R. The 428 other shorts averaged -0.032R. The gap is small and could
  be chance (95% range -0.50 to +0.31).
- Second half: 37 such shorts averaged -0.501R. The 305 other shorts averaged -0.093R (95% range of the gap
  -0.74 to -0.03).
- Holdout, the last year, kept aside as the check: 28 such shorts averaged +0.588R and 61% won. The 165 other
  shorts averaged +0.079R. This is the opposite of the claim.
- By calendar year (added after the run): these shorts were about flat in 2020 and lost in 2021, 2023, 2024 and
  2025. They won in 2022 (+0.249R, 28 trades) and in 2026 (+0.678R, 25 trades). 2022 is the year in which H107's
  rebound long lost most. In the holdout year price stood lower three days after a trigger (median -3.7%). In the
  two halves it stood higher (+1.6% and +3.4%). So these shorts paid when the bounces failed and lost when they
  held. The trigger cannot tell at the time which kind of bounce it is.
- So "no new short for 48 hours after a capitulation rebound" is not supported as a rule. The trades it would
  withhold lost or were flat in five calendar years and won in two, the latest year among them.

**How fast the Lead turns (part a): slowly. Three days after a capitulation low it still favours down in three
events out of four.**

76 confirmed capitulation lows, 34 on BTC and 42 on ETH, from 2020-02 to 2026-11-18.

- At the low the Lead is at its most bearish: -10.4 points at the median, and below zero in 99% of events.
- It first touches zero or better about 20 hours after the low (median). That happened within 24 hours in 54% of
  events, within 48 hours in 79%, within 72 hours in 84%. In 12 of 76 it never happened in 72 hours.
- The touch does not last. The Lead still favours down in 79% of events at +24h, 74% at +48h and 75% at +72h.
  The median Lead is -3.1 a day after the low and -2.0 three days after. Over all closes the Lead favours down
  55% to 67% of the time, so this is more bearish than usual.
- The Lead reached +5 points, what a long from flat needs, within 72 hours in 29% of events. Its highest value in
  those 72 hours was +2.5 at the median.
- Over the same hours price stood 6.3% above the low after a day and 8.8% after three days (median). The lows are
  picked with hindsight, so this flatters them.
- In the holdout year the Lead was slower: 37 hours at the median, and still down a day later in 11 of 11 events.

This agrees with H71: the Lead follows the recent fall and does not call the turn.

**The 21 Nov 2026 event (apart).** The live Lead first favoured up 55.5 hours after the BTC low and 57.75 hours
after the ETH low. Its highest value was +4.9 (BTC) and +5.5 (ETH). Price was 11.7% (BTC) and 12.7% (ETH) above the
low after 48 hours. Live shorts opened inside the window all lost: Setups 2 of 2 (-$1,254), B trail 4 of 4
(-$2,516), main 4 of 4 (-$2,361). That is one event. It looks like the second half and unlike the holdout year.

## Words

- **Lead**: the engine's chance of "up first" minus its chance of "down first", in points. Above 0 it favours
  up. Below 0 it favours down. From flat, the engine goes long by itself only at +5 points or more.
- **Capitulation low**: a 15-minute low that is the lowest of the last 30 days, at least 10% under the price a
  week earlier, and not undercut in the next 48 hours. It can only be named two days later (hindsight).
- **Trigger**: H107's rule A, known at the time. A fresh 30-day low in the last 4 hours, 10% under a week
  earlier, and a close that has bounced 2 x ATR(1h) off that low. ATR(1h) is the average size of a 1-hour bar.
- **Window**: the 48 hours that start at a trigger's close.
- **Setups book**: the paper book `b_targets`. **R**: a trade's result divided by what it risked at its stop,
  after fees. +1R wins what was risked. -1R loses it.
- **Segments**: first half (2020-02 to 2023-06-07), second half (2023-06-08 to 2025-11-10), holdout
  (2025-11-11 to 2026-11-18, kept aside as a check), and the 21 Nov 2026 event, shown apart.

Data: the laptop's copy of the box's data, sessions 2019-01-01 00:00 to 2026-11-24 04:30. The Lead is the replay's Lead. It has no trust cap,
so it is close to the live Lead but not the same.

## Verdict on the registered test (part b)

**The two halves PASS. The holdout does NOT confirm. The proposal does not stand.**
The claim was: shorts opened in the 48 hours after a trigger do worse than the book's other shorts.
To pass, in EACH half the in-window shorts had to number at least 20, average below zero, and average below the
other shorts.

| Check | First half | Second half |
|---|---|---|
| At least 20 in-window shorts | yes (58) | yes (37) |
| Their mean R is below zero | yes (-0.085) | yes (-0.501) |
| Their mean R is below the other shorts' | yes (-0.085 vs -0.032) | yes (-0.501 vs -0.093) |

Both halves passed, so the holdout was opened: in-window 28, 61%, +0.588, +16.5; others 165, 45%, +0.079, +13.0 (trades, share won, mean R, sum of R).
**The holdout does NOT confirm.** The proposal does not stand.

## Part (a): the Lead after a confirmed capitulation low

Descriptive. The lows are picked with hindsight, so this is a description and not a forecast.
BTC and ETH mostly make their lows on the same days, so "both" is not twice the evidence.

| Segment, both coins | Events | Lead at the low (median) | Hours until the Lead first favours up (median) | Turned up within 24h / 48h / 72h | Still favours down at +24h / +48h / +72h | Price against the low at +24h / +48h / +72h (median) |
|---|---|---|---|---|---|---|
| First half (2020-02 to 2023-06-07) | 37 | -11.4 | 15.0 | 51% / 70% / 76% | 73% / 73% / 70% | +8.9% / +8.6% / +9.6% |
| Second half (2023-06-08 to 2025-11-10) | 28 | -9.8 | 18.4 | 64% / 93% / 100% | 79% / 71% / 71% | +7.5% / +8.3% / +9.6% |
| Holdout (2025-11-11 to 2026-11-18) | 11 | -11.1 | 37.0 | 36% / 73% / 73% | 100% / 82% / 100% | +4.1% / +6.4% / +6.9% |
| All three together | 76 | -10.4 | 19.9 | 54% / 79% / 84% | 79% / 74% / 75% | +6.3% / +8.3% / +8.8% |
| BTC, all three | 34 | -9.0 | 18.6 | 53% / 76% / 82% | 76% / 71% / 74% | +5.5% / +6.7% / +7.6% |
| ETH, all three | 42 | -10.8 | 20.2 | 55% / 81% / 86% | 81% / 76% / 76% | +7.7% / +8.4% / +9.9% |
| Not registered: every candidate, no 7-day rule | 95 | -10.6 | 19.2 | 55% / 78% / 84% | 78% / 75% / 78% | +7.7% / +8.4% / +9.4% |

Candidates before the 7-day rule: BTC 44, ETH 53. Kept: BTC 34, ETH 42.
Events where the Lead never favoured up in 72 hours: 12 of 76. Of those that turned, the median wait was 14.9 hours.
The Lead reached the +5 points that a long from flat needs within 24h / 48h / 72h in 8% / 14% / 29% of events.
Median share of the 72 hours after the low spent favouring down: 87%. Median highest Lead in those 72 hours: +2.5 points.
Price at +72h was above the low bar's close in 88% of events (at +24h: 99%).

The Lead's path around the low, all three segments, both coins (points; hour 0 is the low bar's close):

| Hour | -24 | -12 | -6 | +0 | +3 | +6 | +12 | +18 | +24 | +36 | +48 | +60 | +72 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Median Lead | -4.3 | -6.5 | -7.5 | -10.4 | -6.8 | -5.9 | -3.6 | -3.0 | -3.1 | -2.5 | -2.3 | -2.8 | -2.0 |
| Lower quarter | -9.0 | -10.0 | -12.3 | -14.8 | -9.3 | -8.7 | -7.5 | -8.1 | -6.0 | -3.9 | -4.2 | -5.5 | -5.0 |
| Upper quarter | -2.1 | -3.5 | -4.4 | -7.3 | -4.7 | -2.4 | -1.0 | -0.2 | -0.5 | -0.5 | +0.3 | -0.2 | -0.0 |
| Share of events favouring down | 92% | 95% | 95% | 99% | 96% | 95% | 92% | 78% | 79% | 76% | 74% | 76% | 75% |

Yardstick: how often the Lead favours down at ANY close, and how often it is at +5 or more:

| Segment | BTC: below 0 | BTC: +5 or more | ETH: below 0 | ETH: +5 or more |
|---|---|---|---|---|
| First half (2020-02 to 2023-06-07) | 67% | 4.5% | 67% | 4.2% |
| Second half (2023-06-08 to 2025-11-10) | 55% | 5.3% | 56% | 4.7% |
| Holdout (2025-11-11 to 2026-11-18) | 64% | 2.1% | 65% | 1.8% |
| The event apart (from 2026-11-19) | 98% | 0.2% | 98% | 0.2% |

Without hindsight: the same read-outs counted from the trigger that opens a window (price against the
trigger's close, which can be undercut):

| Segment, both coins | Events | Lead at the trigger (median) | Hours until the Lead first favours up (median) | Turned up within 24h / 48h / 72h | Still favours down at +24h / +48h / +72h | Price against the trigger's close at +24h / +48h / +72h (median) |
|---|---|---|---|---|---|---|
| First half (2020-02 to 2023-06-07) | 43 | -8.6 | 58.2 | 35% / 47% / 67% | 88% / 84% / 81% | +0.0% / +1.0% / +1.6% |
| Second half (2023-06-08 to 2025-11-10) | 29 | -6.9 | 17.8 | 62% / 83% / 100% | 79% / 66% / 59% | +2.2% / +1.9% / +3.4% |
| Holdout (2025-11-11 to 2026-11-18) | 15 | -6.3 | 46.2 | 40% / 53% / 60% | 100% / 93% / 100% | -1.2% / -0.7% / -3.7% |
| All three together | 87 | -7.1 | 27.5 | 45% / 60% / 77% | 87% / 79% / 77% | +0.6% / +1.3% / +1.6% |
| 21 Nov 2026 (apart, replay Lead) | 2 | -5.1 | 28.5 | 50% / 50% / 100% | 100% / 100% / - | +3.3% / +7.2% / - |

## Part (b): the Setups book's shorts inside the window against its other shorts

No look-ahead: the trigger is known at its close, and a short counts as in-window by the close that decided it.
Each cell: trades, share won, mean R, sum of R. BTC and ETH together.

| Segment | Shorts in the window | Other shorts | Difference in mean R [95% range] | Other shorts in the same coin-months |
|---|---|---|---|---|
| First half (2020-02 to 2023-06-07) | 58, 43%, -0.085, -4.9 | 428, 42%, -0.032, -13.9 | -0.052 [-0.502, +0.310] | 162, 54%, +0.325, +52.7 |
| Second half (2023-06-08 to 2025-11-10) | 37, 27%, -0.501, -18.5 | 305, 41%, -0.093, -28.2 | -0.409 [-0.744, -0.033] | 124, 55%, +0.218, +27.1 |
| Holdout (2025-11-11 to 2026-11-18) | 28, 61%, +0.588, +16.5 | 165, 45%, +0.079, +13.0 | +0.509 [-0.234, +1.591] | 42, 57%, +0.518, +21.8 |

The 95% range comes from redrawing whole calendar months 10,000 times. A range that spans zero means the
difference could be chance.

Beside the test (descriptive, decides nothing):

| Read-out | First half | Second half | Holdout |
|---|---|---|---|
| BTC shorts: in window / others | 31, 39%, -0.158, -4.9 / 220, 43%, -0.006, -1.2 | 15, 13%, -0.822, -12.3 / 147, 35%, -0.236, -34.7 | 14, 57%, +0.370, +5.2 / 97, 44%, +0.026, +2.5 |
| ETH shorts: in window / others | 27, 48%, +0.000, +0.0 / 208, 41%, -0.061, -12.6 | 22, 36%, -0.282, -6.2 / 158, 47%, +0.041, +6.5 | 14, 64%, +0.805, +11.3 / 68, 47%, +0.154, +10.5 |
| Shorts entered by ENTER: in window / others | 43, 51%, +0.077, +3.3 / 234, 46%, +0.016, +3.8 | 17, 29%, -0.454, -7.7 / 134, 40%, -0.184, -24.7 | 18, 50%, +0.222, +4.0 / 55, 42%, -0.051, -2.8 |
| Shorts entered by FORCED: in window / others | 15, 20%, -0.549, -8.2 / 157, 37%, -0.063, -9.9 | 20, 25%, -0.541, -10.8 / 155, 42%, -0.017, -2.7 | 10, 80%, +1.247, +12.5 / 107, 46%, +0.110, +11.7 |
| Shorts entered by FLIP: in window / others | - / 37, 38%, -0.208, -7.7 | - / 16, 50%, -0.054, -0.9 | - / 3, 100%, +1.356, +4.1 |
| In-window shorts, first 24 hours of the window | 48, 46%, -0.040, -1.9 | 32, 31%, -0.414, -13.2 | 21, 67%, +0.658, +13.8 |
| In-window shorts, second 24 hours | 10, 30%, -0.298, -3.0 | 5, 0%, -1.062, -5.3 | 7, 43%, +0.377, +2.6 |
| LONGS in the window / other longs (the mirror) | 2, 50%, +0.242, +0.5 / 503, 49%, +0.125, +63.0 | 1, 100%, +0.816, +0.8 / 435, 43%, -0.043, -18.8 | - / 110, 39%, -0.152, -16.7 |
| Window of 24 hours instead of 48: shorts in / others | 48, 46%, -0.040, -1.9 / 438, 42%, -0.038, -16.8 | 32, 31%, -0.414, -13.2 / 310, 41%, -0.108, -33.5 | 21, 67%, +0.658, +13.8 / 172, 45%, +0.091, +15.6 |
| Window of 96 hours instead of 48: shorts in / others | 70, 41%, -0.055, -3.9 / 416, 42%, -0.036, -14.9 | 47, 26%, -0.509, -23.9 / 295, 42%, -0.077, -22.8 | 32, 59%, +0.516, +16.5 / 161, 45%, +0.080, +13.0 |
| Median Lead when an in-window short was decided (points) | -8.7 | -5.2 | -6.3 |
| Triggers (BTC + ETH) / share of closes inside a window | 120 / 4.8% | 61 / 3.8% | 61 / 7.5% |

Not registered, added after the run: the shorts by calendar year of the deciding bar (holdout included, since it was opened).

| Year | Shorts in the window | Other shorts |
|---|---|---|
| 2020 | 11, 36%, -0.024, -0.3 | 82, 33%, -0.256, -21.0 |
| 2021 | 12, 25%, -0.511, -6.1 | 174, 46%, +0.032, +5.6 |
| 2022 | 28, 61%, +0.249, +7.0 | 133, 43%, +0.024, +3.3 |
| 2023 | 10, 20%, -0.700, -7.0 | 108, 36%, -0.192, -20.7 |
| 2024 | 15, 13%, -0.751, -11.3 | 150, 44%, -0.040, -5.9 |
| 2025 | 22, 36%, -0.284, -6.2 | 118, 44%, +0.026, +3.1 |
| 2026 | 25, 64%, +0.678, +16.9 | 133, 44%, +0.049, +6.5 |

Check against H67's record of the same book to 21 Nov 13:45 (2,074 trades, -7.7R; BTC -66.9R, ETH +59.2R):
this run has 2074 trades, -7.7R (BTC -66.9R, ETH +59.2R) closed by then.

Look-ahead guard: the trigger was recomputed on bars cut at 348 bars (every trigger bar and 40 random bars per
coin). Mismatches: 0.

## The 21 Nov 2026 event, apart (descriptive only)

This event shaped H107's trigger and prompted this study. It is not part of any test.

Triggers in the replay: BTC at the 11-21 06:45 close; ETH at the 11-21 06:45 close (UTC).

| Coin | Lead used | Low (UTC) | Lead at the low | Hours until the Lead first favoured up | Still favours down at +24h / +48h / +72h | Highest Lead after the low | Price against the low at +24h / +48h / +72h |
|---|---|---|---|---|---|---|---|
| BTC | replay | 11-21 06:15 | -16.1 | 2.00 | yes / yes / - | +5.1 | +7.1% / +11.7% / - |
| ETH | replay | 11-21 04:00 | -15.4 | 57.75 | yes / yes / yes | +5.7 | +8.3% / +12.7% / +10.4% |
| BTC | live journal | 11-21 06:15 | -11.3 | 55.50 | yes / yes / - | +4.9 | +7.1% / +11.7% / - |
| ETH | live journal | 11-21 04:00 | -10.9 | 57.75 | yes / yes / yes | +5.5 | +8.3% / +12.7% / +10.4% |

Live journal against the replay over the live days: BTC 1311 closes with both, same sign 99%, mean gap 2.2 points, live Lead below 0 in 98% of its steps; ETH 1311 closes with both, same sign 100%, mean gap 2.2 points, live Lead below 0 in 98% of its steps.

BTC: the 21 Nov low is left out of part (a)'s tables by the 7-day rule (a confirmed low on 2026-11-15 was kept).

ETH: the 21 Nov low is left out of part (a)'s tables by the 7-day rule (a confirmed low on 2026-11-15 was kept).

Replay Setups book, trades decided from 19 Nov 2026 on:

| Coin | Decided (bar open, UTC) | Side | Entry word | Exit | R | In a window | Lead at the decision |
|---|---|---|---|---|---|---|---|
| BTC | 11-20 16:45 | short | ENTER | T1+STOP_BE | +0.60 | no | -8.3 |
| ETH | 11-20 18:45 | short | ENTER | STOP | -1.04 | no | -17.6 |
| BTC | 11-21 13:15 | short | ENTER | STOP | -1.05 | yes | -6.4 |
| ETH | 11-21 13:45 | short | ENTER | STOP | -1.04 | yes | -6.7 |

Live Setups (b_targets) book, BTC and ETH trades decided from 19 Nov 2026 on (the audit's copy of the box's files):

| Coin | Entered (UTC) | Side | Entry word | Exit | Result | In a window |
|---|---|---|---|---|---|---|
| BTC | 11-20 17:00 | short | ENTER | T1+STOP_BE | +0.60R, +284 USD | no |
| ETH | 11-20 19:30 | short | ENTER | STOP | -1.04R, -648 USD | no |
| BTC | 11-21 14:30 | short | FORCED | STOP | -1.04R, -618 USD | yes |
| ETH | 11-21 14:30 | short | FORCED | STOP | -1.04R, -635 USD | yes |

Shorts in a window: 2, 0 won, -1254 USD.

Live B trail book, BTC and ETH trades decided from 19 Nov 2026 on (the audit's copy of the box's files):

| Coin | Entered (UTC) | Side | Entry word | Exit | Result | In a window |
|---|---|---|---|---|---|---|
| BTC | 11-19 22:30 | short | ENTER | TRAIL | +1.64R, +578 USD | no |
| BTC | 11-20 21:45 | short | ENTER | TRAIL | +1.09R, +567 USD | no |
| ETH | 11-20 21:45 | short | ENTER | TRAIL | +0.58R, +385 USD | no |
| ETH | 11-21 06:45 | short | ENTER | STOP | -1.04R, -670 USD | yes |
| BTC | 11-21 07:45 | short | ENTER | STOP | -1.04R, -703 USD | yes |
| ETH | 11-21 14:45 | short | FORCED | STOP | -1.04R, -700 USD | yes |
| BTC | 11-22 11:00 | short | FORCED | STOP | -1.06R, -442 USD | yes |
| BTC | 11-23 15:00 | short | FORCED | TRAIL | +1.08R, +465 USD | no |
| ETH | 11-23 15:00 | short | FORCED | TRAIL | +1.08R, +502 USD | no |

Shorts in a window: 4, 0 won, -2516 USD.

Live main book, BTC and ETH trades decided from 19 Nov 2026 on (the audit's copy of the box's files):

| Coin | Entered (UTC) | Side | Entry word | Exit | Result | In a window |
|---|---|---|---|---|---|---|
| ETH | 11-21 06:45 | short | ENTER | STOP | -641 USD | yes |
| BTC | 11-21 07:45 | short | ENTER | STOP | -644 USD | yes |
| ETH | 11-21 14:45 | short | FORCED | STOP | -670 USD | yes |
| BTC | 11-22 11:00 | short | FORCED | STOP | -405 USD | yes |
| BTC | 11-23 15:00 | short | FORCED | TRAIL | +425 USD | no |
| ETH | 11-23 15:00 | short | FORCED | TRAIL | +481 USD | no |

Shorts in a window: 4, 0 won, -2361 USD.

## Limits

- A replay on history. The engine was fitted week by week on the past only, but the rules of the book were
  shaped on this same history. Nothing here is a forward result.
- Few separate events. The triggers come in clusters, and BTC and ETH fall together. Calendar months that hold
  an in-window short: first half 16, second half 12, holdout 5. A handful of sell-offs decides each number.
- Part (a) picks its lows with hindsight. Price after the low looks good by construction.
- The replay's Lead has no trust cap, so it is not the live Lead. Over the live days it had the live Lead's sign at 99% of closes and differed by 2.2 points on average.
  Before 10 Nov 2026 there is no live Lead to compare with.
- The trigger was shaped on the 21 Nov 2026 event (H107). That event is kept out of every test.
- The holdout has now been read for this question. It cannot serve as a fresh check for a variant of it.
- Part (b) splits the trades the book made. A book that skips some shorts would trade a different sequence
  afterwards. That book was not replayed.
- Fees are the book's own (0.10% a side). Funding is not charged or paid.
