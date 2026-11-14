# Discovery tools: surprise mining (L1) and the market-state map (L2)

Two research scripts for the charter's discovery machine. They write reports. They never trade
and they never change the engine. Everything they find is a **lead** for `research/HYPOTHESES.md`.
A lead is not an edge until it has been graded forward.

| File | What it is |
|---|---|
| `research/discovery_lib.py` | shared code: readings, states, outcomes, grouped statistics |
| `research/state_map.py` | L2, weekly: every 15m bar sorted into states, and what followed each state |
| `research/surprises.py` | L1, daily: the biggest 1h and 4h moves, the engine's worst calls, and what came before them |
| `tests/test_discovery.py` | checks on planted data, including that cutting off the future changes no state |

## How to run

```
py -3 research/state_map.py                # about 3.5 min, under 200 MB; research/out/state_map.json + .md
py -3 research/state_map.py --placebo 10   # fewer luck re-runs, about 1.3 min
py -3 research/surprises.py                # about 6 s; research/out/surprises.json + .md (recent = 30 days)
py -3 research/surprises.py --days 7       # daily report: research/out/surprises_7d.json + .md
py -3 -m pytest tests/test_discovery.py -q
```

Both scripts read `data/<coin>_15m.csv` and `data/<coin>_funding.csv`. `surprises.py` also reads
`data/econ_events.csv`, `out/replay/trades_<coin>.csv` and `journal/*.jsonl`. They never load
`out/replay/store.pkl`. They handle one coin at a time and keep only small arrays in memory.

## The states (L2)

Every closed 15m bar gets six labels. Each label uses only data known at that bar's close. 1h, 4h
and daily values go through `data.htf_on_15`, so a higher-timeframe bar counts only once it has closed.

| Dimension | Buckets | How |
|---|---|---|
| vol | quiet / normal / wild | the last hour's average 15m range against its 30-day average, split into thirds |
| trend | down / mixed / up | the 4h AND daily trend scores (the estate's trend map) both <= -0.5 / both >= +0.5 / anything else |
| session | Asia / London / overlap / New York / weekend | UTC hour of the bar's close: 22-07, 07-12, 12-16, 16-22; Sat and Sun |
| flow | selling / balanced / buying | net taker buying over the last 4 hours as a share of volume, split into thirds |
| place | near 24h low / middle / near 24h high | where the close sits in the last 24h high-low range, split into thirds |
| move | fell / flat / rose | the last hour's return in units of the 1h ATR14, split into thirds |

The tercile cut points come from the **first half** of history only (2020-01 to 2023-06). That
makes the second half out of sample.

**What followed.** Every trade is entered at the next 15m open. The scripts measure the % move over
1, 4 and 16 bars, plus a triple-barrier trade at +-1.5 x ATR14(1h) over 16 and 96 bars (the
engine's own grade, `labels.triple_barrier`). For each state and each pair of states they report,
per coin and per half: count, independent count (overlapping holding periods counted once), mean,
median, share up / down, t, and how often each barrier was touched first.

## How to read `state_map.md`

- A cell is listed only if it leans the same way in all **four tests**: BTC first half, BTC second
  half, ETH first half, ETH second half.
- **Pays the fee:** in its worst test, the cell still makes more than 0.20% a round trip.
- **Consistent:** t >= 2 in every test, but the move is too small to pay the fee on its own. Such
  a cell is a candidate filter or timing rule, not a trade.
- **The luck count** is the charter's L4 honesty rule. It reports the number of cells examined,
  the number of tests made, and how many cells pass when the states are slid in time against the
  outcomes (the placebo). Trust the placebo over the binomial bounds. It keeps BTC and ETH moving
  together and keeps states lasting for hours.

## Surprises (L1)

- **Surprise:** the move from the close of bar t to the close 4 or 16 bars later, measured in 1h-ATR
  units, in the top 2% for that coin. Overlapping bars of one move count once: only the biggest is kept.
- **Readings at the close of t:** the L2 state, plus these yes/no precursors:
  - a narrow 24h range
  - volatility building (4h range against 24h)
  - a volume surge
  - within 0.5 ATR of the 24h high or low, within 1 ATR of the 7-day high or low
  - a hard 4h run
  - heavy 1h taker flow
  - extreme funding
  - a US release within 2h or in the last 2h
  - the next bar opening at 13:30 or 14:30 UTC, on the hour, or at the daily open
- **Lift:** how much more common a reading is before surprises than at ordinary bars, with counts,
  per coin and per half. A reading passes only if it leans the same way in all four tests. Its
  **Luck** column shows how often that same reading passed in the placebo (surprise times slid in
  time). Big moves bunch together in volatile weeks, so a plain z-score overstates the evidence.
- **The engine at each surprise:** the side held during the first bar of the move. It comes from
  the live journal where the journal covers that time, otherwise from the replay trades.
- **The engine's worst calls:** the bottom 10% of closed replay trades per coin, compared with all
  of its entries. The samples are small (about 50 trades), so read them as hints.

## Limits

- Fills are at the next open with a flat 0.10% a side. There is no slippage and no funding.
- The barrier P&L counts "neither" (and a bar that touches both barriers) at the horizon's close.
- "Independent" counts the distinct holding-period blocks a cell touches. It is an approximation.
- The economic calendar starts in May 2026. The release precursors are snapshotted, but the
  four-test rule cannot grade them yet.
- Replay trades are matched to bars by `time_in` / `time_out` (all fill prices match the bar opens).
  The engine's per-bar odds are not used, because they live only in `store.pkl`.
- 185 cells, 4 measures and 2 sides make 1,480 tests. The surprise mining makes 432 tests. Some
  cells will look good by luck. That is why the placebo exists, and why only forward grading decides.
