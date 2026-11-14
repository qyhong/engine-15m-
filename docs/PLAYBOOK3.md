# Strategy books, batch 3: VWAP, session plays, fair value gap, cascades, round numbers, releases, US-open range

Status: built 11 Nov 2026, **paper only**, registered to run forward from 11 Nov 2026. Charter task K
(batch 3). Code: `engine15/playbook3.py` (interface: `docs/PLAYBOOK_INTERFACE.md`). History:
`research/playbook3_study.py` -> `research/out/playbook3.md` / `.json`. Tests: `tests/test_playbook3.py`.

**The short version.** None of the five books chosen on the first half of history (P6 to P10) clears
costs in the second half. Before costs, most of them are a little above zero; the fees on 15-minute
stops (0.1R to 0.4R a trade) are what kill them, as in batches 1 and 2. P11 (release days) has only 2
to 10 releases per market on file, all since May 2026, so it has no first half at all. P12 (crypto
opening range at the US open) is positive in both halves, but it was FOUND in this same history, so its
numbers are not evidence and it is graded forward only. **83 variants were tried in all.** Every book
runs forward as a paper book only so the forward record, not the history, gives the verdict.

## The frame every book shares

Unchanged from batch 2 (`docs/PLAYBOOK2.md`); the same simulator is reused.

- **Bars and fills.** 15-minute bars, closed bars only. The decision is at a bar's close; the fill is at
  the next bar's open. If that open is already beyond the stop (or already past the target), no trade.
- **Stop first.** A bar that touches both the stop and a target counts as the stop. A gap through the stop
  fills at the open.
- **One trade at a time** per book per market. $10,000 a trade, full size.
- **Costs.** Each market's own fee a side: BTC and ETH 0.10%, gold 0.02%, silver 0.03%, USDJPY 0.01%,
  S&P 500 0.02%. Results are given **before and after costs**. R = the result in dollars divided by the
  dollar risk to the stop.
- **Minimum stop.** The stop must be at least four one-side fees away (0.40% crypto, 0.08% gold and S&P,
  0.12% silver, 0.04% USDJPY), so the round trip costs at most half of 1R. Tighter setups are skipped.
- **No position through a market close** longer than 3 hours (weekends, the S&P overnight): closed at
  the close of the last bar before it.
- **Wider structural stops.** Stops sit beyond the structure (the excursion's extreme, the gap's far edge,
  the cascade's extreme) plus 0.25 x ATR(14) of the 1-hour chart ("hourly ATR"). Targets are 2R or more,
  or a structural price.
- **Higher-timeframe bias**: the engine's v5 bias (1h, 4h and daily trend scores all one way and price
  on that side of the 1h EMA50 and the 4h EMA20/EMA50). Higher bars count only once closed.

## P6: VWAP reversion / reclaim (`p6_vwap`, draft H11)

**What it looks for.** Two plays around the daily VWAP (volume-weighted average price from 00:00 UTC,
with volume-weighted standard-deviation bands). *Fade*: in a quiet range, a close beyond the 2-sigma band
is faded back toward VWAP. *Reclaim*: in a trend, the first pullback of the day to VWAP that closes back
on the trend side is joined.

**Why it might work.** Intraday traders and execution desks use VWAP as fair value; stretched prices in a
range get pulled back, and in a trend VWAP is where late buyers (sellers) step in.

**The registered rule (reclaim).** With the higher-timeframe bias LONG (SHORT), the day's first 15m bar
whose low (high) tags the daily VWAP and closes back above (below) it, the bar before also on that side,
is traded at the next open. Stop **1 hourly ATR beyond VWAP**. Target **2R**. Time exit after 32 bars
(8 hours). USDJPY's VWAP weights every bar equally (its live feed has no volume).

**History (registered rule):**

| Market | Half | Trades | Win % | Avg R before costs | Avg R after costs | PF after |
|---|---|---|---|---|---|---|
| BTC | first / second | 616 / 467 | 39.1 / 37.3 | +0.054 / +0.076 | -0.137 / -0.182 | 0.76 / 0.71 |
| ETH | first / second | 576 / 489 | 36.6 / 35.6 | -0.012 / +0.002 | -0.160 / -0.200 | 0.76 / 0.75 |
| Gold | first / second | 433 / 467 | 40.0 / 43.3 | +0.034 / +0.123 | -0.113 / -0.005 | 0.79 / 0.96 |
| Silver | first / second | 385 / 452 | 42.1 / 39.6 | +0.042 / -0.000 | -0.066 / -0.096 | 0.93 / 0.82 |
| USDJPY | first / second | 410 / 432 | 41.0 / 39.4 | +0.066 / +0.011 | -0.095 / -0.130 | 0.90 / 0.81 |
| S&P 500 | first / second | 348 / 338 | 45.7 / 47.0 | -0.048 / +0.038 | -0.149 / -0.069 | 0.71 / 0.79 |

**Verdict: does not clear costs.** Negative after costs on every market in both halves; before costs
+0.02R then +0.04R (mean across markets). None of the 16 fade variants came near: the best lost 0.25R a
trade after costs and was negative even before costs, so fading VWAP bands on 15m bars is rejected
outright. About 56 trades a month across the six markets.

## P7: Session plays (`p7_session`, draft H12)

**What it looks for.** Three plays graded separately:
- *London false move* ("Judas swing"): Asian range = 00:00 UTC to the London open (08:00 London: 07:00
  UTC in summer, 08:00 in winter). The first take-out of that range soon after the London open that
  closes back inside within 4 bars is faded. (Gold, silver, USDJPY, BTC, ETH.)
- *Asian-range breakout* at London (gold, USDJPY): the first 15m close outside the Asian range in the
  first 4 London hours is traded in its direction.
- *New York afternoon drift* (the market-state map's lead, `research/out/state_map.md`): long BTC/ETH at
  a weekday 16:00 or 18:00 UTC close, held 4 hours.

**The registered rule (Asian-range breakout only).** No sub-play had a positive first half after costs,
so by the fixed rule only the best one is registered: gold and USDJPY, the first 15m close outside the
Asian range within the first 4 hours after the London open, at the next open; stop at the **opposite side
of the Asian range**; target **3R**; flat 8 hours after the London open.

**History (registered rule):**

| Market | Half | Trades | Win % | Avg R before costs | Avg R after costs | PF after |
|---|---|---|---|---|---|---|
| Gold | first / second | 705 / 617 | 41.1 / 42.3 | +0.022 / +0.004 | -0.058 / -0.067 | 0.89 / 0.95 |
| USDJPY | first / second | 638 / 607 | 48.0 / 48.4 | +0.076 / +0.064 | -0.000 / +0.006 | 1.06 / 1.02 |

**Verdict: does not clear costs overall** (-0.030R after costs in the second half, +0.034R before).
USDJPY alone is flat after costs in both halves. The **London false move lost heavily** (-0.32R to
-0.37R after costs, negative before costs in all 4 variants): in this history the first take-out after
London more often kept going than reversed. The **New York drift** is positive before costs (about
+0.02R) but not after (-0.05R to -0.16R): it confirms the state map, whose average move (+0.05% to +0.09%
in 4 hours) is far below the 0.20% crypto round trip. About 26 trades a month.

## P8: Fair value gap / order block (`p8_fvg`, draft H13)

**What it looks for.** A three-candle impulse where the first candle's high is below the third candle's
low (bullish; mirror for bearish), the middle candle moving that way, and a gap of at least k x ATR(15m)
(the ATR before the three candles). When price later comes back into the gap (or the "order block": the
last opposite candle before the impulse), trade in the impulse direction.

**The registered rule.** Gap at least **1.0 x ATR(15m)**; zone = **the gap itself**. The first bar within
12 hours that trades into the zone is the decision bar, if its close has not gone through the zone's far
edge; enter at the next open. Stop beyond the far edge + 0.25 hourly ATR. Targets: **half at the impulse
extreme** (the high reached before the return; 1R if that is nearer than 0.5R), **the rest at 2R or 1R
past the extreme**, stop to the entry after the first half. Time exit after 32 bars.

**History (registered rule):**

| Market | Half | Trades | Win % | Avg R before costs | Avg R after costs | PF after |
|---|---|---|---|---|---|---|
| BTC | first / second | 1,407 / 1,297 | 44.0 / 41.6 | -0.016 / -0.009 | -0.231 / -0.297 | 0.61 / 0.55 |
| ETH | first / second | 1,672 / 1,633 | 45.2 / 43.8 | -0.007 / +0.005 | -0.194 / -0.247 | 0.74 / 0.65 |
| Gold | first / second | 1,177 / 1,169 | 47.7 / 43.9 | +0.043 / -0.036 | -0.149 / -0.204 | 0.77 / 0.77 |
| Silver | first / second | 1,072 / 1,016 | 49.2 / 46.4 | +0.090 / -0.018 | -0.057 / -0.139 | 1.00 / 0.92 |
| USDJPY | first / second | 1,297 / 1,284 | 47.5 / 45.4 | +0.053 / +0.007 | -0.149 / -0.155 | 0.75 / 0.78 |
| S&P 500 | first / second | 162 / 155 | 41.4 / 44.5 | -0.093 / -0.011 | -0.215 / -0.154 | 0.65 / 0.80 |

**Verdict: does not clear costs.** About zero before costs (-0.01R in the second half), -0.20R after.
Gaps on 15m bars are everywhere (about 140 trades a month) and the stops are tight, so fees take about
0.2R a trade. The order-block zone was worse than the gap in every pairing. The bias filter lifted the
first half but on as few as 23 trades on one market (below the 30 needed), so it was not eligible.

## P9: Crypto liquidation cascades (`p9_cascade`, draft H14)

**What it looks for.** A fast move on BTC or ETH: at least x hourly ATRs (the ATR from before the move)
from the 4-bar extreme to the close, on those 4 bars' volume at least 1.5x (or 2.5x) the previous day's
average, with the takers one-sided (taker buying at most 45% of the volume in a drop, at least 55% in a
rise). First bar of a cascade only. Two plays: *continuation* (trade with it at once) and *bounce*
(wait up to 8 bars for a bar that closes beyond the previous bar's extreme against the move, then fade it).

**What data history allowed.** Price, volume and taker flow: 2019 on. Funding: from September 2019 (used
as a stage-2 filter). **Open interest: only about 30 days on file** (Binance serves 30 days;
`data/sources/liq_oi_*.csv`), so the "open interest falling" part of the idea cannot be graded on history
and is not in the rule. Once 90 days of OI exist it can be tested as a new hypothesis.

**The registered rule (continuation).** x = **3 hourly ATRs**, volume **1.5x**, takers one-sided, and
funding has **reset**: at or below its 30-day median after a drop (at or above after a rise). Trade with
the move at the next open; stop at the **4-bar extreme where the move began**; target **3R**; exit after
16 bars (4 hours).

**History (registered rule):**

| Market | Half | Trades | Win % | Avg R before costs | Avg R after costs | PF after |
|---|---|---|---|---|---|---|
| BTC | first / second | 104 / 205 | 50.0 / 42.9 | +0.107 / +0.060 | +0.029 / -0.060 | 1.13 / 0.84 |
| ETH | first / second | 94 / 188 | 52.1 / 43.6 | +0.156 / +0.021 | +0.093 / -0.063 | 1.15 / 0.80 |

**Verdict: does not clear costs in the second half** (-0.061R after, +0.041R before). It was the only
book with positive first-half variants (8 of 18; all continuation), and all 18 were negative after costs
in the second half. The bounce (fade the cascade) lost in every variant, before and after costs. About 8
trades a month.

## P10: Round-number magnets (`p10_round`, draft H15)

**What it looks for.** Round numbers (BTC 1,000s, ETH 100s, gold 50s, silver 1s, USDJPY 0.50s, S&P 50s;
"major": BTC 5,000s, ETH 500s, gold 100s, silver 5s, USDJPY 1.00s, S&P 100s). *Magnet*: price first comes
within y hourly ATRs of the nearest one (untouched for 4 hours) -> trade toward it. *Rejection*: the
first touch in 24 hours closes back on the near side -> fade it.

**The registered rule (magnet).** Base grid; when the close first comes within **1 hourly ATR** of the
nearest round number, trade toward it at the next open; target the number; stop **as far behind the entry
as the number is ahead** (a 1R target); exit after 16 bars.

**History (registered rule, mean across markets):** first half -0.016R before costs, -0.210R after;
second half -0.026R before, -0.246R after. Every market negative after costs in both halves (per market:
`research/out/playbook3.md`). **Verdict: rejected.** No pull toward round numbers before costs, and the
rejection play was no better (-0.24R to -0.30R after costs). It also trades far too often (about 260
trades a month across markets).

## P11: Release-day trades beyond CPI (`p11_release`, draft H16)

**What it looks for.** US high-impact releases on the calendar other than CPI (which is H1's): FOMC
decisions, payrolls (NFP), and others (PPI, ...). The release bar is the 15m bar that opens at the
release time. *Follow*: take the side of its close (like H1). *Fade*: bet against it.

**Few cases.** `data/econ_events.csv` starts in May 2026: 10 non-CPI releases have happened since, and a
market only counts a release whose bar it trades (the S&P cash market is shut at 08:30 New York, so it
sees FOMC only) and whose move was big enough. So the history is **2 to 10 release-rows per market, about
28 in all, all in the "second half"**: there is no first half to choose on. Both modes were compared on
everything on file (in-sample) and the better one is registered, to be graded forward only.

**The registered rule (follow).** When the release bar moves at least **1.0 hourly ATR** open to close,
take its side at the next open; stop beyond its far extreme (its low for a long); exit after 16 bars
(4 hours). Every market where the bar exists.

**On file (in-sample, not evidence):** follow +0.50R after costs a release-row (mean across markets),
fade -0.53R. FOMC rows won 11 of 12 (all on BTC, ETH, gold, USDJPY and the S&P; silver 2 of 3);
payroll rows were mixed (1 of 5 won on gold and silver, but each with a large winner; 0 of 4 on USDJPY).
This is the same handful of 2026 releases that `research/event_study.py` looked at, read differently.

## P12: Crypto opening range at the US equity open (`p12_orb_us`, draft H17)

**Where it came from.** In the playbook2 study's session breakdown, the registered P3 rule was positive
after costs at the US equity open on BTC and ETH in both halves, while its 00:00 UTC session lost heavily.
That was found by looking at a breakdown, so it is registered **forward only**: the history below is
"where it was found", not support.

**The rule.** BTC and ETH, NYSE trading days. Opening range = the first 30 minutes from the US cash open
(09:30 New York: 13:30 UTC in US summer, 14:30 in winter; New York's daylight-saving dates, not
London's). The first 15m close outside it, if in the direction of the higher-timeframe bias, is traded at
the next open; stop at the range's opposite side; target 2R; flat 8 hours after the open. (playbook2's P3
rule, US-open session only; one variant, nothing chosen.)

**Where it was found (history, not evidence):**

| Market | Half | Trades | Win % | Avg R before costs | Avg R after costs | PF after |
|---|---|---|---|---|---|---|
| BTC | first / second | 156 / 144 | 46.2 / 51.4 | +0.220 / +0.307 | +0.032 / +0.115 | 0.94 / 1.26 |
| ETH | first / second | 143 / 119 | 44.1 / 46.2 | +0.209 / +0.221 | +0.034 / +0.072 | 0.99 / 1.23 |

About 5.5 trades a month on the two coins.

## Variants tried (count all of them)

| Book | Grid | Count |
|---|---|---|
| P6 VWAP | fade: band 2.0/2.5 sigma x entry on the close beyond / back inside x target VWAP/2R x range = ADX<20 / no bias (16); reclaim: stop tag bar / 1 ATR beyond VWAP x 2R/3R (4) | 20 |
| P7 sessions | London false move: take-out within 8/12 bars x target far side/2R (4); Asian breakout: stop far/mid x 2R/3R (4); NY drift: 16:00/18:00 x stop 1.5/3 ATR (4) | 12 |
| P8 FVG | zone gap/order block x k 0.5/1.0 x target 2R / extreme-then-2R x bias filter off/on | 16 |
| P9 cascades | continuation/bounce x x 2/3 ATR x volume 1.5/2.5 x two targets each (16) + funding filter on each mode's winner (2) | 18 |
| P10 round numbers | magnet: base/major x within 0.5/1.0 ATR x stop half/full (8); rejection: base/major x 2R/3R (4) | 12 |
| P11 releases | follow/fade x minimum move 0.5/1.0 hourly ATR | 4 |
| P12 US-open range | the one P3 rule | 1 |
| **All** | | **83** |

How the choice was made, fixed before the run (`research/playbook3_study.py` docstring): the highest mean
over markets of first-half average R after costs, every market with at least 30 first-half trades (20
for the funding filter). P6 registers both modes only if both first halves are positive; P7 the
sub-plays with a positive first half (at most two), else the single best; P9 and P10 the better mode.
Nothing was re-chosen after seeing the second half. Split date: 6 Dec 2022 (2019-01-01 to 11 Nov 2026).

## Leads found but NOT registered

Each was found by looking at breakdowns (more variants), so each would be a new hypothesis graded
forward only:

- **Cascade continuation pays before costs in both halves** (all 9 continuation variants: +0.08R to
  +0.13R first half, +0.04R to +0.07R second half before costs). Fees take 0.06R to 0.12R. Cheaper
  fills (maker entries, task E) or a longer hold are the questions, not the signal.
- **USDJPY Asian-range breakout** is flat after costs in both halves (PF 1.06 / 1.02) with ~13 trades
  a month: inside the registered P7 rule already, so the forward run grades it.
- **VWAP reclaim on gold in the London session** was +0.05R / +0.07R after costs (about 75 trades a half).
- **FOMC follow-through** looked consistent across markets on 1 to 3 cases each: far too few to mean
  anything; P11's forward record will say.

## Limits

- History can reject a rule, not prove one. The second half already rejects P6 to P10 as written; the
  forward run tests whether that holds. P11 and P12 have no clean out-of-sample history at all.
- No slippage beyond the fee; fills at the next open exactly. The cascade book trades exactly when
  slippage is worst, so live fills would be worse than shown.
- Round numbers are fixed price steps: BTC's 1,000s were 10-25% of price in 2019 and ~1.4% now, ETH's
  100s similar, so the early P10 history is a different game from today's.
- Open interest: 30 days only (not used). Funding: from September 2019. Release calendar: from May 2026.
- Volume changes source at the data join for gold, silver, the S&P (Dukascopy to Yahoo); USDJPY's VWAP
  is equal-weighted throughout so history and live agree. Gold/silver/USDJPY holidays are not modelled.
- The live books read 450 days back from registration (for the bias); a setup appears once decided
  (WAITING: fills at the next open); a range or gap that is set but not yet triggered is not listed.
- Funding paid or received on crypto positions is not charged.

## Hooking it in (for the main session)

Already wired: `engine15/reports.py` `PLAYBOOK_MODULES` includes `playbook3`, which calls
`playbook3.step(None)` and `playbook3.page_block(rows)`. Rows carry the interface's fields plus `t1_name`,
`t2_name`, `t1_hit`, `est_entry` (WAITING rows) and `session`. `target_2` is None for time-exit books
(P11 follow). `BOOKS["p12_orb_us"]["forward_only"]` is True and its page note says it was found in the
history. A live step over all six markets takes about 1.0 s including loading the bars from disk (0.3 s
of computing), peak ~180 MB.

## DRAFT hypothesis entries (for `research/HYPOTHESES.md`; not yet copied there)

Count note for the register: these add 7 ideas (H11 to H17) and **83 variants tried on history** before
registration (`research/out/playbook3.md`). H17 adds no variant of its own: it was found among the 130
of H8-H10.

---

## H11. VWAP reclaim with the higher-timeframe bias (registered 11 Nov 2026)

**Prompted by:** charter task K, batch 3 (VWAP reversion / reclaim); the intraday-levels card
(`sources/ltf.py`) already reads the daily VWAP and its bands.

**What the history on file says** (`research/playbook3_study.py`, 2019 to Nov 2026, split 6 Dec 2022; 20
variants): no variant positive after costs in either half. All 16 band-fade variants lost 0.25R to 0.50R
after costs and were negative before costs too. The registered reclaim lost -0.120R / -0.114R after costs
(first / second half, mean across markets), +0.023R / +0.042R before; negative after costs on every market
in both halves.

**The rule (shadow only, paper):**
1. Daily VWAP from 00:00 UTC (typical price, volume-weighted; equal weights for USDJPY).
2. With the engine's v5 bias LONG: the day's first 15m bar whose low reaches VWAP and whose close is back
   above it (the bar before also closed above), traded LONG at the next open. Mirror for SHORT.
3. Stop 1 hourly ATR beyond VWAP (at least 4 one-side fees away). Target 2R. Exit after 32 bars.
4. One trade at a time per market; $10,000; each market's own fee a side. All six markets.

**Graded forward on:** every trade from 11 Nov 2026 (about 55 a month).

**Verdict rule, fixed now:** after 100 forward trades, keep it only if the average result is above +0.05R
after costs, the profit factor is above 1.1, and at least 3 of the 6 markets are positive. Otherwise retire it.

**Why it may be nothing:** it lost after costs on every market in both halves; it lost least of 20.

---

## H12. Asian-range breakout at the London open, gold and USDJPY (registered 11 Nov 2026)

**Prompted by:** charter task K, batch 3 (session plays) and task D (trading sessions).

**What the history on file says** (12 variants over three plays): no play had a positive first half after
costs. The London false move lost about -0.33R after costs (negative before costs too); the New York
afternoon drift was +0.00R to +0.02R before costs and -0.05R to -0.16R after. The registered breakout:
-0.029R / -0.030R after costs (mean of gold and USDJPY), +0.049R / +0.034R before; USDJPY -0.000R / +0.006R.

**The rule (shadow only, paper):**
1. Asian range = the high and low of the bars from 00:00 UTC to the London open (08:00 London time).
2. The first 15m close above (below) it in the first 4 hours after the London open: LONG (SHORT) at the next open.
3. Stop at the opposite side of the Asian range (at least 4 one-side fees away). Target 3R.
4. Flat 8 hours after the London open. Gold and USDJPY; $10,000; each market's own fee.

**Graded forward on:** every London session from 11 Nov 2026 (about 26 trades a month).

**Verdict rule, fixed now:** after 100 forward trades, keep it only if the average result is above +0.05R
after costs and the profit factor is above 1.1, with both markets positive. Otherwise retire it.

**Why it may be nothing:** negative after costs overall in both halves; chosen as the least bad of three plays.

---

## H13. Fair value gap retest (registered 11 Nov 2026)

**Prompted by:** charter task K, batch 3 (fair value gap / order block).

**What the history on file says** (16 variants): none positive after costs in either half. Registered:
-0.166R / -0.199R after costs, +0.012R / -0.010R before. The order block was worse than the gap in every pairing.

**The rule (shadow only, paper):**
1. Bullish gap: candle 1's high below candle 3's low, candle 2 up, gap at least 1.0 x ATR(14, 15m) taken
   before the three candles (mirror for bearish).
2. The first bar within 12 hours that trades back into the gap, if its close is not beyond the gap's far
   edge: trade in the impulse direction at the next open.
3. Stop beyond the far edge + 0.25 hourly ATR. Half at the impulse extreme (1R if nearer than 0.5R), the
   rest at 2R or 1R past the extreme; stop to entry after the first half. Exit after 32 bars.
4. All six markets; $10,000; each market's own fee.

**Graded forward on:** every trade from 11 Nov 2026 (about 140 a month).

**Verdict rule, fixed now:** after 200 forward trades or 30 days, whichever is later, keep it only if the
average result is above +0.05R after costs, the profit factor is above 1.1, and at least 4 of 6 markets
are positive. Otherwise retire it.

**Why it may be nothing:** about zero before costs, -0.2R after, on thousands of trades.

---

## H14. Crypto liquidation cascade continuation (registered 11 Nov 2026)

**Prompted by:** charter task K, batch 3; the liquidation proxy of `sources/derivs.py` (whose open-interest
part has only 30 days of history).

**What the history on file says** (18 variants): continuation was positive after costs in the first half
in 8 of 9 variants and negative in the second half in all 9; positive before costs in both halves in all
9. Registered (with the funding filter): +0.061R / -0.061R after costs, +0.132R / +0.041R before. The
bounce lost in every variant.

**The rule (shadow only, paper):**
1. BTC and ETH. At a bar's close: price is at least 3 hourly ATRs (the ATR before the move) from the
   4-bar high (low), the 4 bars' volume is at least 1.5x the previous 24 hours' average, taker buying is
   at most 45% (at least 55%) of it, and the newest funding rate is at or below (above) its 30-day median.
   First bar of the cascade only.
2. Trade WITH the move at the next open; stop at the 4-bar extreme where the move began (at least 0.40% away).
3. Target 3R. Exit after 16 bars (4 hours). $10,000; 0.10% a side.

**Graded forward on:** every cascade from 11 Nov 2026 (about 8 a month).

**Verdict rule, fixed now:** after 40 forward trades (about five months), keep it only if the average
result is above +0.05R after costs and the profit factor is above 1.1. Otherwise retire it. Separately,
once 90 days of open-interest history exist, test whether a falling OI in the cascade separates winners
from losers, as a new hypothesis.

**Why it may be nothing:** the second half lost after costs; 18 variants; fills in a cascade would slip.

---

## H15. Round-number magnet (registered 11 Nov 2026)

**Prompted by:** charter task K, batch 3; the round-number pools of P1 (`playbook.py`).

**What the history on file says** (12 variants): no variant was positive even before costs on average.
Registered: -0.210R / -0.246R after costs, -0.016R / -0.026R before.

**The rule (shadow only, paper):**
1. Round numbers: BTC 1,000s, ETH 100s, gold 50s, silver 1s, USDJPY 0.50s, S&P 500 50s.
2. When the close first comes within 1 hourly ATR of the nearest one (not touched in the last 4 hours),
   trade toward it at the next open. Target the number; stop the same distance behind the entry (1R; at
   least 4 one-side fees away). Exit after 16 bars.
3. All six markets; $10,000; each market's own fee.

**Graded forward on:** every trade from 11 Nov 2026 (about 260 a month).

**Verdict rule, fixed now:** after 200 forward trades or 30 days, whichever is later, keep it only if the
average result is above +0.05R after costs and at least 4 of 6 markets are positive. Otherwise retire it.

**Why it may be nothing:** no edge even before costs on history; runs mainly as the control it already is.

---

## H16. Release-day follow-through beyond CPI (registered 11 Nov 2026)

**Prompted by:** charter task C (release days: FOMC, payrolls) and H1.

**What the history on file says** (4 variants): the calendar on file starts in May 2026, so about 28
release-rows in all (2 to 10 per market), all in-sample. Follow (1-ATR bar) +0.50R after costs a row,
fade -0.53R. FOMC rows won 11 of 12; payrolls 2 of 16. `research/event_study.py`
earlier found jobs and Fed releases did not follow through at 1 hour on BTC/ETH (58% / 38%): the two
views differ on the same few cases.

**The rule (shadow only, paper):**
1. Releases: every US high-impact release on `data/econ_events.csv` except CPI (H1): FOMC, payrolls, PPI, ...
2. Do nothing during the release bar. If it moved at least 1 hourly ATR open to close, take the side of its
   close at the next open.
3. Stop beyond its far extreme (at least 4 one-side fees away). Exit after 16 bars (4 hours).
4. Every market whose release bar exists (the S&P cash market sees FOMC only); $10,000; each market's own fee.

**Graded forward on:** every release from 11 Nov 2026 (about 3 releases a month).

**Verdict rule, fixed now:** after 12 forward releases (about four months), keep it only if at least half
of the release-rows are profitable after fees AND the mean result is above +0.2R. Otherwise retire it.

**Why it may be nothing:** about 28 in-sample rows from six months; markets move together on a release,
so the independent cases are about 10; chosen after seeing them.

---

## H17. Crypto opening range at the US equity open (registered 11 Nov 2026; FORWARD ONLY)

**Prompted by:** the playbook2 study's session breakdown of H8 (`research/out/playbook2.md`): at the US
equity open the rule was positive after costs on BTC (+0.03R then +0.12R) and ETH (+0.03R then +0.07R).

**What the history on file says:** nothing usable as evidence: the lead was FOUND in this history, by
splitting H8's results by session (one of many breakdowns of 130 variants). Reproduced in
`research/playbook3_study.py` as "where it was found": BTC +0.032R / +0.115R, ETH +0.034R / +0.072R
after costs (first / second half).

**The rule (shadow only, paper):**
1. BTC and ETH, NYSE trading days. Opening range = the first 30 minutes from 09:30 New York (13:30 UTC in
   US summer time, 14:30 in winter).
2. The first 15m close outside the range, if in the direction of the engine's v5 higher-timeframe bias,
   is traded at the next open. No bias, or bias the other way: no trade that day.
3. Stop at the range's opposite side (at least 0.40% away). Target 2R. Flat 8 hours after the open.
4. $10,000; 0.10% a side. (Identical to H8 at this one session.)

**Graded forward on:** every US session from 11 Nov 2026 (about 5 to 6 trades a month). History is not counted.

**Verdict rule, fixed now (purely forward):** after 60 forward trades (about ten months), keep it only if
the forward average result is above +0.05R after costs, the forward profit factor is above 1.1, and both
coins are positive. Otherwise retire it.

**Why it may be nothing:** a subset picked out of a losing rule after the fact; ~140 trades a half per
coin; the same trades also run inside H8.
