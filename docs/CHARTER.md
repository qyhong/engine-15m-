# Mind 15 charter (agreed with the owner, 11 Nov 2026)

## Purpose

Find what makes trading on 15-minute bars consistently profitable, until it earns more than
a 4h/daily engine on the same assets, after costs, at no worse drawdown.

Owner, 11 Nov 2026: on 4h and daily the big returns are easy to "see" and capture; on 15m we
do not yet know how to earn consistently. This project exists to explore "what we do not
know what we do not know". So the centre of the work is DISCOVERY of edges native to 15m.
Borrowing the 4h/daily direction is one idea among many, never the centre. A 4h/daily book
run on the same data and costs is the yardstick, not a crutch.

What is already known: 15m direction read on its own is right about 51% of the time (replay,
2020 to Nov 2026), and the AI Trading Bot's screens found no stand-alone 15m edge on BTC/ETH.

## Unchanged by this charter

Paper only. Full size, $10,000 per asset. Always-positioned mandate (idle at most 4
sessions). Top ten cards vote. PIN-gated owner answers with an audit trail.

## Scoreboard

- **Learning:** ideas tried (the count in `research/HYPOTHESES.md`), ideas that survive
  forward, forward profit of the survivors.
- **Results:** best 15m book against the 4h/daily yardstick book and buy and hold, on net
  return, max drawdown, return / drawdown, expectancy per trade in R, profit factor, fees paid.
- Forward results decide. The history replay can reject an idea, never prove one.

Reviews: **10 Dec 2026** (what has the lab found?) and **10 Feb 2027** (is any 15m book
ahead of the yardstick? promote or change course).

## Task queue (owner: "Make them tasks to implement", 11 Nov 2026)

Status: queued / building / shadow running / verdict.

### Ways 15m could beat 4h/daily (each becomes a registered hypothesis and a shadow book)

| ID | Task | Status |
|---|---|---|
| A | **Timing**: side from the 4h/daily trend, entry on a 15m setup, stop under 15m structure, so the same trend move is caught with a smaller stop (more R per trade) | queued |
| B | **Exits**: act on a 15m reversal (structure break, realistic-reach target, trailing swing stop, partial at 1R) instead of waiting for the slow bar | shadow running: b_targets, b_trail (11 Nov); H36 (13 Nov) history 2020-2026: all 15 MA-trail / break-even variants made less than holding (main +$329k pooled; best be_t1 +$108k, best MA trail -$25k); forward books b_be_t1, b_ema20_1h_t1, b_sma20_1h_t1 (`research/out/exits/trail_study.md`) |
| C | **Release days**: CPI (H1, running), FOMC, payrolls; trades that live inside minutes to hours | H1 shadow running; others queued |
| D | **Trading sessions** on the new markets: S&P cash open, London and New York sessions for gold, silver, USDJPY | queued (needs the four markets wired in) |
| E | **Cheaper fills**: limit (maker) entries instead of market orders; measure fees saved against trades missed | study done (`docs/FILLS.md`): skipping unfilled limits loses money; a limit on flip exits helped in both halves, registered as **H3**; its shadow book is still to build |
| J | **Liquidation hunt and breakout trap** (owner, 11 Nov 2026): P1 fades a stop-run through an obvious liquidity pool (swing / 24h / prior-day high or low, round number) that closes back inside with a long wick; P2 trades a failed breakout that closes back inside the range within 4 bars. Each a standalone strategy book, studied on history (both halves, all six markets) then run forward; hypotheses H6 and H7 | live (`playbook.py`, H6/H7): neither clears costs in history; running forward |
| K | **Ten more 15m strategy books** (owner, 11 Nov 2026: "build all 12", in the recommended order; one interface: `docs/PLAYBOOK_INTERFACE.md`). Batch 2: opening range breakout (H8), S&P overnight gap fill (H9), squeeze breakout (H10). Batch 3: VWAP reversion/reclaim, session plays (London false move, NY afternoon drift, Asian-range breakout), fair value gap / order block, crypto liquidation cascades, round-number magnets, release-day trades beyond CPI (FOMC, payrolls). Trend pullback = task A (shadow books) | all live: `playbook2.py` (H8-H10), `playbook3.py` (H11-H17). History: none of P6-P10 clears costs in its second half; leads: cascade continuation (positive before costs), gold VWAP reclaim in London, FOMC follow-through (few cases) |
| I | **Higher-timeframe bias and release guard** (owner's BTC post-mortem, 11 Nov 2026): engine v5, hypotheses H4 and H2 | live in the main books from the 17:00 UTC step, 10 Nov; v4 shadow book to compare still to build |
| G | **Moving averages** (owner, 11 Nov 2026): SMA and EMA 5/10/20/50/200 on 15m to 1d with crosses; an EMA ribbon (8-55) and Guppy groups; moving averages as dynamic support and resistance (tests, hold record, confluence with horizontal and Fib levels) | live from 17:15 UTC, 10 Nov (`mavg.py`: mavg, ribbon, mavg_sr; `trendtools.py`: Ichimoku, Hull, KAMA as readings only) |
| H | **Ten cards for gold, silver, USDJPY, S&P 500** (owner: "All ten"): CFTC positioning, volatility gauges, rates and the dollar, S&P futures overnight, Japan watch, metals ratios, stock breadth, put/call, megacap earnings, gold/silver ETF holdings | all 10 registered: 6 live from 17:15 UTC and 4 (`cot.py`, `japan.py`, `equity_events.py`) from the 18:00 step, 10 Nov; gaps: put/call has no free data Oct 2019 to Nov 2024, silver ETF holdings and JPY releases start live |
| F | **Fibonacci retracement and extension** (owner, 11 Nov 2026: "to help it plan entry and exit"): golden-zone pullback entries, invalidation beyond 0.786, 1.272 / 1.618 targets checked against realistic reach; a new card that feeds A and B | building (`engine15/sources/fib.py`) |

### Discovery machine (the main work)

| ID | Task | Status |
|---|---|---|
| L1 | **Surprise mining (daily)**: the biggest 15m moves the engine got wrong or missed, every reading beforehand, what repeats | running daily: the first live step of each UTC day runs `research/surprises.py --days 1` (and --days 7 on Mondays) via `engine15/reports.py`; page.json carries the last day's biggest surprises |
| L2 | **Market-state map (weekly)**: sort every session into states (volatility, trend, session, flow, structure) and measure what followed in each; lopsided states surface without being named first | first version done (`research/state_map.py`): 185 states, 1,480 tests; no state pays the 0.20% round trip on its own; leads: New York afternoon drift, near the 7-day high (a few large moves, so an exits question), pullback in an uptrend, big moves cluster at 13:30/14:30 UTC |
| L3 | **Idea factory**: every pattern found becomes a written hypothesis, is checked in both halves of history and on more than one asset, then runs forward as a shadow book; failures stay on file | queued |
| L4 | **Guard against luck**: forward-only proof, cross-asset checks, an honest count of ideas tried | queued (count kept in HYPOTHESES.md) |
| L5 | **The owner as a source (weekly)**: the engine shows its three biggest surprises and asks what the owner saw; answers are graded like any reading | wired 11 Nov: each Monday the engine posts the week's biggest surprise (preferring one it was wrong about) to the owner as a question on the audit trail |

### Yardstick

| ID | Task | Status |
|---|---|---|
| Y | 4h/daily book: the same engine deciding only at 4h closes, same data, fees and mandate | live 11 Nov 06:45 UTC as shadow books `y_4h` and `y_1d` (same odds, decisions only at 4h / daily closes, stops live every 15m) |

### Status notes, 11 Nov 2026 (05:30 UTC)

- A, B, H3, H4: an Opus agent is building `engine15/shadows.py`: challenger books `v4` (H4),
  `h3_flip_limit`, `b_targets`, `b_trail`, `a_pullback`, run forward beside the main books on the same
  odds, plus a 120-day in-sample read in `research/out/challengers.md`.
- H5 registered (metals post-mortem: slow daily voices kept the metals engine bearish through a
  bounce; damp them when 1h and 4h structure turn). Not built yet.
- Y (4h/daily yardstick book) still queued.

### Status notes, 11 Nov 2026 (05:55 UTC)

- Owner: BTC's two old trades removed and the BTC book restarted at $10,000 with the running short
  (backups in data/backup_*; audit rows "book_reset").
- Owner: leverage. USDJPY up to 100x, S&P 500, gold, silver up to 5x; crypto 1x. The engine sizes each
  new trade so its stop risks ~2% of equity, between 1x and the cap (`backtest.leverage`,
  `CFG["max_leverage"]`, `CFG["risk_per_trade"]`). Open USDJPY long resized to 6.0x, gold short to 1.43x;
  S&P short stays 1x (its stop is 2.1% away).
- Shadow books live (engine15/shadows.py): main, v4, h3_flip_limit, b_targets, b_trail, a_pullback.
  120-day in-sample read: a_pullback +$256 vs main, h3 -$18, v4 -$766, b_targets -$2,710, b_trail -$8,670.
- Strategy books live (engine15/playbook.py, playbook2.py; page block "playbook"): P1 liquidation hunt,
  P2 breakout trap, P3 opening range, P4 S&P gap fill, P5 squeeze. History: none clears costs in its
  second half (fees on tight 15m stops). Registered H6-H10 and run forward anyway. Lead: crypto ORB at
  the US open (positive after costs in both halves; found, so forward-only, H17).
- Batch 3 building (engine15/playbook3.py, H11-H17).

### Status notes, 11 Nov 2026 (06:25 UTC)

- Oil added: WTI and Brent, energy group, $10,000 each, 5x cap, 0.04% a side. Known limit: monthly futures roll
  steps in the live series are not adjusted.
- Liquidity eagle view: Coinbase full book binned 0.5% to +-10% (raw.book_eagle), archived each session.
- Page: tabs (Overview / Cards / Books / Journal), all-markets summary, books panel, journal and closed trades
  folded to the last 3; phone height per tab ~3,400-3,800 px (was 20,536 px for the whole page).
- All twelve strategy books built and running forward (H6-H17).

### Status notes, 11 Nov 2026 (06:45 UTC)

- Y live as shadow books y_4h / y_1d; H5 live as shadow book h5_damp (odds with the strategies voice halved
  when 1h and 4h structure turn against it).
- L4: out/live/scoreboard.json and page.json "scoreboard_all": every book (main, shadows, strategy books), live
  trades only, net, a 90% range per trade, a verdict once a book has 30 trades.
- L3: research/out/ideas_queue.md written once a day from the surprise report's robust precursors.
- Portfolio readout in page.json "portfolio": long/short notional, gross vs equity, risk if every stop hit.
- Oil and metals futures roll: extdata.roll_adjust scales re-served new-contract bars to the stored level;
  rolls logged to data/rolls.csv.
- C: an agent is backfilling the US release calendar 2019-2026 (and EIA/OPEC for oil, stored only).
- Waiting for memory: the history replay refresh (v5, leverage, eight markets).

### Status notes, 11 Nov 2026 (07:00 UTC)

- C: release calendar history 2019-2026 live (engine15/calhistory.py, data/sources/calendar_history.csv, 1,209 rows;
  econ.load_events merges it). The macro voice and the release guard now see releases across the whole history.
  Study (research/out/release_history.md): CPI follow-through did NOT hold over 2019-2026 (BTC 1h 49% / 43% in
  the two halves); FOMC 4h follow-through 50% / 72% (BTC), 55% / 62% (ETH); NFP tends to fade. 1 of 64 tests
  significant, about chance. H1's registration rested on 6 releases; its forward verdict rule stands.
- Web answers: the engine pulls from the server before each step (inbox.pull). The AI Trading Bot session has the
  form rebased onto the tabbed page (branch mind15-form), held until the owner sets the PIN and says go.

## Workstream M: the intraday mind (owner, 11 Nov 2026)

Owner: "explore to improve the engine's analysis and intelligence on trading the lower timeframe, where
trading more brings more profitability also - rather than just better timing but doing almost the same as
on the 4h or daily chart." Today's main engine predicts a 24h move, holds for days and takes no profit, so
it is a slow trend-follower with 15m timing. Workstream M builds an engine that thinks in 15m-to-4h swings.

| ID | Task | Status |
|---|---|---|
| M1 | Short-horizon minds: the same readings and voices, trained to call the next 1h (4 bars) and 4h (16 bars) move (triple barrier on 1 x ATR), graded per market and session | done |
| M2 | Expected value per trade, fee-aware: P(win) x reward - P(loss) x risk - round-trip cost for that market; trade only above a margin (crypto pays 0.20%, USDJPY 0.02%) | building |
| M3 | Swing trade management: stop at structure / 1R, take profit at 1.5-2R or the realistic reach, time stop, re-entry on the next signal | building |
| M4 | Where short-horizon skill lives: which markets, sessions and regimes give the M1 minds an edge after costs (both halves of history) | building |
| M5 | Swing-mode books on all eight markets as shadows, on the forward scoreboard next to the main book and the 4h/daily yardsticks | building |
| M6 | A weekly skill report per horizon (1h / 4h / 24h) per market, so the engine learns which clock to trust where | building |

- Owner decision, 11 Nov 2026 08:10 UTC: crypto paper fee stays 0.10% a side (cost_side); do not re-ask.

### Workstream M result, 11 Nov 2026 (09:00 UTC)

- Built (engine15/intraday.py, research/intraday_study.py, docs/INTRADAY.md); swing books m_swing_1h (H18) and
  m_swing_4h (H19) live as shadows from the 08:55 UTC restart; weekly horizon-skill report and page block.
- Finding: crypto's next HOUR is the one steady short-horizon read (BTC 55.3% / 54.2%, ETH 55.4% / 55.2% in the
  two halves) - real direction skill, but worth about +0.04R a call before costs against a 0.37R crypto round
  trip. Gold, silver, USDJPY, S&P and oil: 49-53% (the cards know when price will move, not which way).
  The 4h mind is ~51% everywhere. 0 of 40 market x session cells positive after costs in both halves.
  Leads only: gold in the London/NY overlap, silver in London, WTI in New York.

### History refresh, 11 Nov 2026 (09:30 UTC) - research/out/challengers_all.md

120 days, eight markets, in-sample: main rule +7.6%, 4h yardstick +6.1%, daily yardstick +1.5%, buy and hold +4.3%.
Pullback entry (A) +9.9% and H5 +8.8% ahead of main; trailing stop -8.5% worst. Oil lost in every book but buy and
hold (-17% main). Fixed: the daily yardstick now decides at each market's own daily close (it never traded the S&P
or oil before).

### Status notes, 11 Nov 2026 (09:30 UTC) - the owner's nine-item list

1. Oil readings: agent building engine15/sources/oil.py (EIA, OPEC calendar, OVX, CFTC crude, WTI-Brent).
2. Honest fills: done. Gold, silver, WTI, Brent orders fill one bar later (config fill_delay; their live bars
   arrive ~10 minutes late). Main book and shadow books alike.
3. Crypto 1h call toward 60%: agent researching (research/crypto1h_study.py).
4. Card ratings per market: after 3.
5. Total-risk cap: done. risk_cap_pct 10% of total equity across all open main-book stops; a new entry over it
   is shrunk or skipped (live.risk_budget, backtest.run_book risk_budget_usd).
6. Page: done (sent for deploy): "Which clock is right" (1h/4h/24h hit rates) and the idea queue.
7. Guides: done (CLAUDE.md, THOUGHT_PROCESS.md "Now", HANDOFF.md).
8. Stale-page alarm: the AI Trading Bot session adds Mind 15 to its S328 Telegram alarm (built off, on with the owner's word).
9. Full replay refresh: last.

### Item 3 result, 11 Nov 2026 (10:30 UTC) - research/out/crypto1h.md

Crypto 1h call: 5,760 variants (+28 model settings), chosen on the first half. Picking the surest calls lifts the hit
rate to ~60% (pooled logistic top 10%: BTC 61.3 / 57.6%, ETH 60.1 / 59.4%), but that is worth only +0.02 to +0.06R a
trade before costs against 0.26-0.51R of round-trip fees. Best first-half pick: +0.09R / +0.07R after costs; untouched
second half -0.23R (BTC) / -0.14R (ETH). 0 of 5,760 clear costs on both coins in both halves; a slid-signal placebo
confirms. Verdict: rejected at the 0.10%-a-side fee; no hypothesis registered, no challenger built.

- Owner decision, 11 Nov 2026: the RL module gets its own "Lab" tab on the page (status, out-of-sample vs benchmarks, overfitting flags, risk-manager log, drift monitor, retrain history, Phase 3 ablation); plus an RL chip on Overview, a reading-only RL card, a Books row and Journal entries from Phase 4. Lab skeleton is built once Phase 1 results are approved; data via an "rl" block in page.json.

### Item 4 result, 11 Nov 2026 (12:00 UTC) - engine think15-v5.1

Cards rated per market group (research/rate_cards.py, research/out/card_rating_<group>.*, same method as the crypto
rating). Each non-crypto group now votes with its own top ten (CFG voting_by_group): metals led by volatility gauges,
Ichimoku, momentum, gold/silver ETF holdings; fx by trade setups (read inversely), regime, working strategies;
the S&P by trade setups, moving averages, S&P overnight; oil by oil volatility (inversely), regime, trade setups.
Crypto keeps its list (owner decision); the new rating would swap six crypto cards (ribbon, trend quality, KAMA,
intraday levels, moving averages, Ichimoku in) - reported, not applied. Live from the 12:00 UTC restart.

### RL Phase 1 done, 11 Nov 2026 (11:50 UTC) - research/out/rl/phase1_report.md, docs/RL.md

BTCUSDT perp 15m 2019-09 to today (251,586 bars), funding, OI live-only; 15 point-in-time features; one cost model;
vectorised backtester; walk-forward (25 three-month windows). Out of sample after costs: buy and hold +249% (Sharpe 0.64,
max DD 79%); momentum -100%; random -95% +- spread. Waiting for the owner's review before Phase 2.

### Status notes, 13 Nov 2026 (~04:30 UTC): task B, H36 (owner: "follow their own planned target profit", "trail profit with ema or sma")

- The main books exit only at the entry stop or on a flip; the planned Target 1/2 are shown but never traded, and the stop
  never moves. Unchanged (owner: "let the profit run"; a v5.2 is the owner's call after the study).
- H36 registered first (15 frozen variants: EMA/SMA 20/50 on 15m and 20 on 1h, armed from entry / after 1R / after
  Target 1; break-even after Target 1 alone and with a trail; half at Target 1 plus a trail), then read on 2020-2026, all
  eight markets, the main book's own entries (`research/exit_study.py`, `research/out/exits/trail_study.md`).
- Result (in-sample): **every variant made less than holding.** Main +$329,439 pooled (Sharpe 0.92, max DD -29.6%);
  be_t1 +$107,673 (Sharpe 0.62, DD -37.1%; without ETH -$8,554 vs main); best MA trail sma20_1h_t1 -$24,645; from-entry
  trails -99%; b_targets -$28,862, b_trail -$48,808. The main book wins ~1 trade in 5 with winners 4-6x its losers; its
  six largest trades per market exceed its whole net. Trails cut those, then re-entries were stopped.
- Forward shadow books from the next live-loop restart: `b_be_t1` (owner: "Shadow test plus label"), `b_ema20_1h_t1`,
  `b_sma20_1h_t1`, titled with their history result. The pick rule for the two MA books was amended after the results
  (disclosed in HYPOTHESES.md). The rule lives in `engine15/exits.py`, shared code for a possible v5.2 (notes in the study).

### Status notes, 13 Nov 2026 (owner decisions through the day)

- **Exits:** after H36 the owner chose "Let the winner run": no v5.2; the main books take profit only by flipping. The
  page's target tiles read "reference" (deployed 1a5cc082).
- **RL loop rounds 2-3** (`research/rl_loop/LOOP_RL.md`, frozen rules; target: beat BTC spot buy-and-hold out of sample
  without lowering Sharpe): no pass. Best R3-b (long core, risk-off switch at 1.25x): +1,428%, Sharpe 1.14, fails only
  S1 (fold share 40%, needs 50%) and S4 (p 0.033-0.044; with 23 variants S4 needs p <= 0.00217, a Sharpe gap of about
  0.7 against about 0.4). Reports: `research/out/rl_loop/round{2,3}_report.md`; round-4 proposals in `loop_state.json`.
- **H37 long-short study** (owner: "explore long-short strategies, not fully naked short"; dev data only,
  `research/out/longshort/study.md`): no candidate passed. V4, the BTC/ETH relative-value trade in daily downtrends, was
  the only structure that made money in downtrends on both coins. Owner "Yes": it runs forward as `engine15/playbook7.py`
  (`p7_rvbear`, BTC and ETH sleeves) from 2026-11-13 11:30 UTC, NOT passed (first positions at the 11:45 close).
- **H39 new free data** (owner: "New data first"; dev data only, `research/out/flows/study.md`): 12 free positioning and
  on-chain inputs. None gives an independent risk-off call near the IC of about 0.12-0.17 S4 needs (best: BTC exchange
  inflow +0.075, not significant); some carry volatility (size) information. Paid candidates noted, not bought:
  Coinglass liquidations, options-history providers.
- **think15-v5.1.1** (owner: "Yes" to wiring the new data in): `engine15/sources/flows.py` is a live source with four
  crypto-only READING-ONLY cards (Binance archive positioning, Bitfinex margin, CME positioning from the CFTC, on-chain
  activity). They do not vote (crypto voting list unchanged), so decisions are unchanged; fetches are throttled per source
  (`MIN_GAP_S`). Live from the 13:45 UTC step; the journal's first entry per group carries a "New version" note.

### Status notes, 14 Nov 2026

- **Practice mode** (owner: "Let it practice"): no new research for now; every paper book builds its forward record.
- **RL round 4 on hold** (owner "Ok" to my advice): low odds, and each variant tightens the Bonferroni bar. Revisit only
  on new independent information (e.g. paid liquidations, tested alone, owner's yes first) or forward RL verdicts.
- **Owner alerts** ("When something happens"): a closed trade on the main, shadow, RL or pair books, any book at 30
  trades or changing verdict, or a page older than 40 minutes, pushed to the owner's phone from the working session.
- **Known gap:** when the Mac sleeps, the Windows VM and the loop pause (13-14 Nov: about 2 h and 3 h). The loop catches
  up every missed bar on waking; the page is stale meanwhile. The owner keeps the Mac awake; the weekly RL refits are
  due after Mon 16 Nov 00:00 UTC.
- **Version history:** the folder became a local git repository (no remote, nothing pushed); data, caches, models and
  live outputs are ignored.
