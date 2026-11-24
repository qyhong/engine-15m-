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
- **Version history:** the folder became a local git repository; since 20 Nov 2026 it has a private GitHub remote
  (`origin`, branch `main`) and deploys go only from a pushed commit; data, caches, models and
  live outputs are ignored.
- **H40 Deribit options flow** (owner: "Yes. Test them"; free history.deribit.com trades, dev data only to the seal,
  `research/out/options/study.md`): 6 inputs (put/call, taker and block flow, approximate 25-delta skew), 120 tests.
  No input meets the bar: best registered-side 7-day partial IC +0.026 (ETH skew); the largest effect had the wrong sign
  (BTC put/call -0.122, p 0.011, not significant; heavy put buying preceded better weeks, unregistered so not claimed).
  Only next-day drawdown (size) tests survive Bonferroni. `engine15/sources/options_hist.py` is built, NOT wired.
  Paid survey (`research/out/paid_data/survey.md`): liquidations via CryptoQuant $39-109/month (owner signs up; unverified
  which tier has the hourly liquidation API), whale flows $109, order-book depth history has no cheap route to 2021.
- **P1 liquidation hunt retired** (owner: "Retire it", 15 Nov 2026 06:15 UTC) after its post-mortem and H41 (no edge
  before costs in 37 variants). `playbook.RETIRED`; the record of 65 live trades (-$1,421) stays on the page, frozen.

### Status notes, 15-16 Nov 2026

- **Engine versions (all reading-only additions except v5.2):** v5.1.2 seven indicator cards (`sources/osc.py`
  Supertrend, StochRSI; `sources/osc2.py` Parabolic SAR, Money Flow Index, volume profile, Heikin-Ashi, Aroon/Vortex);
  **v5.2 trust cap: no voting card above 40% of the say** (owner's choice, `config.trust_cap`, `model.cap_shares`; H43
  records a history comparison: no consistent effect either way); v5.2.1 CCI card for every market (`sources/osc3.py`);
  v5.2.2 six crypto cards (`sources/cryptox.py`: Deribit options flow, Korea premium, CME gap from spot prices, BTC
  dominance of a tracked basket, spot vs perp leadership, cross-exchange funding/OI). Card pipeline:
  `research/CARD_PIPELINE.md` (batches of five, reading-only, rated, 30 days forward, a vote only on the owner's yes).
- **H42** balanced trust blend: no pass (predicts marginally better, trades worse); trust constants unchanged.
- **Breakout research for the owner's ">70% continuation" goal, all NO PASS:** H44 15m range break with momentum and
  daily-ATR room; H45 daily breakout with daily-sized trades; H46 384 confluence buckets; H47 regime split (trend vs
  range); H48 FX and session timing. A daily-level break continues +0.5 before -0.5 daily ATR about 50% of the time in
  every market and regime; the best confluence ~51-54%. USDJPY leans ~54% but USDSGD goes the other way.
  `engine15/sources/adr.py` (daily range budget card) is built, not wired.
- **Hosting:** a read-only probe from the US web box found Binance futures/api (451) and Bybit (403) blocked. The owner
  keeps the engine on the laptop for now ("utilise laptop first"); a Singapore EC2 may come later (the owner launches it).
  The live loop stays in the Claude terminal tab (owner); it stops when a Claude session ends and is restarted on resume.
- **Moved to the Singapore EC2 (16 Nov 2026):** the owner created a box and said "migrate all minds15 project to there"; the
  owner chose a new key on the box, pinned wheels only, and an automatic switch after 4 matching shadow steps. 5 shadow
  sessions (09:30-10:30 UTC) matched the laptop exactly; the box has pushed since 10:50 UTC as systemd service `mind15`;
  the laptop loop is stopped. Research H50 (news drift), H51 (cross-market confirmation), H52 (size by expected move) ran on
  the box: all no pass. Laptop cleanup (owner-approved): out/replay, RL caches and data/evcache deleted (20 GB -> 1.5 GB).

### Status notes, 17 Nov 2026 (owner decisions)
- **Verdict rules approved** ("Approve all", 17 Nov 2026, before either book reached 30 live trades):
  `research/VERDICT_RULES.md` is in force for `b_trail` and `p8_fvg`. In short: the verdict at 30 is the first server
  scoreboard showing 30 or more trades; `b_trail` changes nothing at 30, and a proposal to make its trail the main exit
  (new version, registered first, owner's yes) is made only if it is "ahead" at both 30 and 60 trades, beats the fresh
  main copy in total and in at least 5 of 8 markets, with the second check read no earlier than 10 Dec 2026; "behind" =
  post-mortem, then the owner chooses retire or keep as a reference; "undecided" = run on to 60, then 100. `p8_fvg`'s
  30-trade verdict is interim: H13's registered rule (200 trades or 30 days) still decides. No tuning and re-grading,
  no moving the lines, no real money.
- **Card batch 4** live as think15-v5.2.4 (Fisher Transform, Ultimate Oscillator, TRIX, linear-regression channel,
  Mass Index; `sources/osc5.py`), reading-only. H43 finished: the S&P trades identically with and without the 40% cap.
- **Subagents run on Opus 5.5** ("Let all the agents utilise opus 5.5", 17 Nov evening; Fable 5.2 earlier that day).
- **Ten-task plan agreed**: 1 backup to the laptop (done: `tools/backup_pull.py`, daily 12:00 SGT, 7 kept), 2 outside
  alarm (owner chose the AI Trading Bot's stale-page alarm; asked for), 3 slim the reading cache, 4 one-command deploy
  (done: `tools/deploy.sh`), 5 verdict rules (done, above), 6 live calibration report, 7 data-health check, 8 rate the
  new cards, 9 find duplicate cards, 10 where the step time goes. RL loop Round 4 registered 03:21 UTC on the owner's
  "Concurrently do the RL tasks too" (my 14 Nov advice against it stands as a caution, not a block).
- **The data disk stays 24 GB** ("just utilise whatever we have now"); the laptop no longer runs the 30-minute watcher.
- **Own user + sandbox for the engine and the bot** on the Singapore box: owner "Yes, do it" (the box audit's top
  finding); script `tools/server/mind15_own_user.sh` (apply / --undo).
- **Subscriber product (owner, 17 Nov 2026):** subscribers "only want to know trade opportunity", not the research.
  Signal book S1 = `b_targets` scored the way a person can follow it (H53, with its 17 Nov amendment); preview cards go
  to the owner's chat only ("Yes, build preview"; the card "look ok"). The site gets a main page "Setups" fed by
  `setups.json`; the owner's rulings, in order: "no, launch now" (to the site session), then here "Launch now, gate
  for charging", then, told the site serves data behind its paywall, **"Included for paying members"**: Setups is
  part of the paid plan from day one; H53's gate no longer conditions selling the Setups page (against my
  recommendation "Free for now"). S1's grading is unchanged and the Telegram signal product stays an owner-only preview.
- **Real-money exception (owner, 18 Nov 2026, 13:29 UTC):** asked whether to lift the founding "paper only" rule so Mind 15 can send its
  BTC/ETH setups book to the site's VIP key vault, which places REAL orders on the opted-in "helix" Binance account
  (site session's request; owner's words there: "Let the helix user able to access the VIP feature where can automate
  the trading... As we are experiment the binance automation trading"), the owner chose **"Yes, feed the vault
  (experiment)"**, after being told the setups book lost about -0.03R per signal on 2023-2025 history (H55) and has 17
  live trades. Scope: Mind 15 itself still places no order and holds no exchange key; it only SENDS its book
  (BTCUSDT, ETHUSDT) to the vault on 127.0.0.1 each step; the vault decides and places orders. Everything else in
  Mind 15 stays paper. A vault failure never affects Mind 15's paper books or outputs.
- **Vault exits (owner, 18 Nov 2026, 13:31 UTC):** asked whether the feed may also send exit instructions, the owner chose **"Allow close,
  reduce, stop"**: `close` when the setups book exits (stop, flip, its exit rule), `reduce` to take half at Target 1, and
  `move_stop` to the entry after Target 1, exactly as the book does, for BTCUSDT and ETHUSDT only. Never `open` or any
  instruction that adds to a position.
- **P10 round numbers retired** (owner: "Post-mortem, then retire", 19 Nov 2026; stamp 04:00 UTC) after its post-mortem
  (`research/out/p10_postmortem.md`: no pull toward round numbers even before costs, live as on history).
  `playbook3.RETIRED`; the record of 120 live trades (-$2,018) stays on the page, frozen.
- **USDJPY main book: stop to entry after Target 1** (think15-v5.2.5, 19 Nov 2026). The owner, of the USDJPY long
  that was past Target 1 with its stop still below the entry and price stalling under 160: "Follow the target";
  of the two readings offered (stop to entry after Target 1, or take profit at the targets) the owner chose
  "Stop to entry after T1". The first change to a main-book exit rule, and for one market only. History (H36,
  in-sample, 1 of 15 variants): USDJPY +$27,238 against +$19,209 for holding; all eight markets pooled, less than
  holding. The owner's earlier idea the same evening (close a profitable trade when the odds lean against it) was
  not adopted: on USDJPY the odds leaned against the open long in 327 of 646 bars, by a median 0.9 points.
  Still paper only; nothing about the vault changes (it carries BTC and ETH setups only).
- **S&P 500 main book: half at Target 1, stop of the rest to the entry, the rest runs** (think15-v5.2.6, 20 Nov
  2026). The owner, of the S&P short from 7,626 that was past Target 1 (7,251) with its stop still above the entry:
  "The snp 500 should close half of the profit now under mind 15 as TP1 already achieve"; of three ways to treat
  the other half (run with the stop at entry; close at Target 2; no half, stop to entry only) the owner chose
  "Rest runs, stop at entry". Target 1 had traded the day before, so the half is closed at the next S&P open at
  that open's price, not back-dated to the target. Adopted on the owner's word; this combination was not among
  H36's 15 variants, and its history read (H59) is descriptive and gates nothing. Paper only.
- **USDJPY main book: one closed trade rewritten on the owner's word (20 Nov 2026).** The long of 10 Nov 17:00 UTC
  (158.76401, 378.19 units) traded through its Target 1 (159.3945) on 11 Nov 13:30 UTC and its Target 2 (159.8217)
  on 11 Nov 15:30 UTC, went as high as 160.188 on 13 Nov, and was closed whole at its entry on 20 Nov 09:45 UTC by
  the stop-to-entry rule (-12.01 USD, the fees): the main book does not sell at its targets. The owner: "It is a
  profitable trade and we never manage it well", first "take half profit it at 159.5" (written 11:27 UTC:
  +127.15 USD), then, shown that both targets had traded, "Record the trade as it achieve TP1 and TP2" (written
  11:36 UTC, replacing the first). `out/live/trades_USDJPY.csv` now holds that trade as two rows with the same
  entry time: half (189.097 units) at Target 1, `T1_OWNER`, +113.22 USD, and half at Target 2, `T2_OWNER`,
  +193.98 USD; +307.19 USD in all, and the book's realized equity is 10,307.19 (it was 9,987.99). The targets are
  the trade's own, set at its entry. The files as they were at each step are kept beside them
  (`*.before-owner-half-20261120T112750Z`, `*.before-owner-targets-20261120T113632Z`). The `_OWNER` tags mark
  fills decided AFTER the fact: the engine did not take them at the time, so this trade is not evidence about
  any exit rule, and the shadow books (`main` copy, `b_be_t1`, `b_targets`) keep their own untouched records.
  The rule itself was not changed (USDJPY: stop to entry after Target 1, no half), and the open USDJPY long of
  20 Nov 11:00 UTC (158.868) was not touched. Paper only.
- **USDJPY main book: half at Target 1, the rest at Target 2, stop to the entry after Target 1** (think15-v5.2.7, 20
  Nov 2026). After the post-mortem of the trade above (`research/out/usdjpy_postmortem_20261120.md`: the main book
  cannot take profit; the odds on USDJPY moved 1 point typically and never the 10 a flip needs; the Setups book banked
  $304 on both targets and then lost $392 on three forced re-entries) two questions were put to the owner. Should the
  open USDJPY long sell at its targets: "1. Sell at target". Should a trade that ended at a target be exempt from
  the forced re-entry: "2. Still follow our rules. Our goal is to ace the directional setup at highest probability. 4
  session (max 1 hour) flat is good enough to re-read the market condition and choose best probability option." So
  the mandate is unchanged and `CFG["t2_exit"] = ("USDJPY",)` joins `half_t1` and `be_t1`: on USDJPY the main book now
  exits exactly as the Setups book does (checked to the cent against `shadows.run` on random bars,
  `tests/test_t2_exit.py`). It applies to the open long of 20 Nov (Target 1 159.586, Target 2 160.093). Adopted on
  the owner's word; on history this rule earned less than holding on USDJPY (H36: +$2,939 against +$19,209). The
  shadow `main` copy keeps holding as the forward comparison. The owner's further idea the same day (flip exits in
  directional regimes, target exits in the others, and one rule per market) is H60, registered before any number.
- **Vault feed: the exit guard is off; BTC's missed Target 1 exit sent once** (20 Nov 2026, owner: "Yes, both"). The
  feed's guard of 18 Nov (`EXITS_ONLY_IF_WINDOW_SEEN`: exits only for a setup whose entry window the feed saw open)
  assumed the vault joins only inside the entry window. Under the owner's hybrid join rule the vault also joins a
  setup later: per the AI Trading Bot session it joined a member into the BTC and ETH shorts of 15 Nov on 19 Nov.
  The guard marked both "not joinable", so no exit was ever sent: BTC's Target 1 of 20 Nov ~12:15 UTC produced no
  reduce and no stop move, and no close would have followed. Found by the AI Trading Bot session; the fault was in
  this project's feed. Put to the owner as: fix and send BTC's missed Target 1 exit once / fix only / leave it; the
  owner chose both. The guard is now False (the switch stays in the code; only the owner turns it back on), and
  the missed BTC pair (reduce 0.5, then the futures stop to the entry 65,203.2) is queued once by hand through the
  feed's own track(). Exits stay exits only: nothing opens or adds, the markets stay BTC and ETH.
- **Vault feed: the "share held" field stays off** (21 Nov 2026 Singapore time, 20 Nov ~17:55 UTC; owner: "Leave it
  off"). The AI Trading Bot session reported a second vault package live since 20 Nov 17:48 UTC with late fill
  switched on by the owner there: the vault now READS `held_share`, and joins or tops up a setup whose Target 1 is
  taken only if the book states it; without it the vault skips with a `t1_no_share` line. Put to the owner as:
  switch the field on (new version, new golden record, a restart of about 15 minutes) / leave it off. The owner
  chose to leave it off: `SEND_CONTRACT_1` stays False, so the vault joins only setups that have not reached
  Target 1. Turning it on later needs the owner's word in this project.
- **think15-v5.2.8: a tight trailing stop on six main books; no forced entry after a trail exit** (21 Nov 2026).
  The owner, in the site-coordination session, with six main-book shorts 2 to 10 R in open profit and nothing
  banked: "Lets monitor all assets for minds15. As currently all are in profit. It is crucial to see what is the
  optimal way to capture the profit." Shown the B trail shadow book's forward lead (+$11,534 against the main
  book's +$9,850) and its 2020-26 history (-$47k against +$329k), the owner there: "Update minds 15 with tight
  trailing stop" (relayed by that session). Confirmed in this project by prompt: markets -> "Six markets" (BTC,
  ETH, gold, silver, WTI, Brent; USDJPY and the S&P 500 keep their target rules of 20 Nov); how the book comes
  back after a trail exit -> "Wait for a signal" (no forced entry; flat until one side clears the entry bar).
  The trail is the B trail book's: armed at 1R, then the tighter of the last confirmed 15m swing and 2 x ATR(15m),
  never looser. A stop-out at the entry stop and a flip keep the 4-session mandate. Trades already running come
  under the rule at the first step. Not a passed test: every tight trail lost against holding on history (H36),
  and the wait-for-a-signal re-entry is new. The vault's book (`b_targets`) is not touched; the golden money-path
  test is unchanged and green. The wide profit floor the coordination session asked for is H61 (registered
  before any number; results in research/HYPOTHESES.md).
- **A profit-floor shadow book beside the main book** (21 Nov 2026). Asked whether to run H61's one passing
  variant forward on paper, the owner in this project: "Add shadow" (and, relayed from the site-coordination
  session, "Lock a third once 3× up: Ok"). Book `f_floor_33_3r` (`engine15/floor_book.py`): the hold copy's
  trades on all eight markets; once a close shows 3R of open profit a stop locks a third of the best closed
  profit; flat after its own exit until the hold copy's next entry. It started as a copy of the hold copy's book
  (its equity and its running trades, at its size), with the floor set from the closes since each entry and able
  to fill only from the first bar after the start. Its scoreboard row compares it with the hold copy on the same
  markets. Forward data points, not a passed rule: on history it beat holding only weakly and no floor helped per
  trade at equal size (H61). It is a follower, not a rule of `shadows.run`: the vault's book cannot be changed by
  it, and an error in it is logged and skipped. No version change (no constant moved), so no reading rebuild.
  Not built: the Telegram alert at a 25% give-back (no answer yet).
- **RL audit, 21 Nov 2026 (owner: "audit again RL from day 1 until now"), and what followed.** The history in one
  place, since this file had only Phase 1, the Lab decision, rounds 2-4 and the hold; details and numbers are in
  `docs/RL.md`, `research/rl_loop/LOOP_RL.md` and `docs/RL_NEXT.md`.
  - 11 Nov: Phase 1 (benchmarks; the "momentum -100%" above was the every-bar rule, replaced the same day by the
    frozen daily 30-day rule: +237.7%, Sharpe 0.63, against buy-and-hold +249.3%, 0.64). Phase 2 (PPO): -99.6%, no.
    Phase 3 (linear Q agent, 15m): -53%, no. Phase 4 (pooled BTC+ETH, 18 Mind 15 readings): +79%, Sharpe 0.48
    against 0.64; something before fees, not after.
  - 12 Nov 04:30 UTC: `p5_rlq` (the Phase 4 primary) goes live forward, labelled NOT passed. Phase 5 (trade-less
    variants): none beats buy-and-hold on BTC. Phase 6 (missed-opportunity reward, momentum fallback): 1 of 8
    variants passed its own bar, which was against Phase 4, not against buy-and-hold; the fallback was chosen with
    hindsight and the control (Phase 4 + fallback) is ahead of it on BTC in history.
  - 13 Nov 03:00 UTC: `p6_mtrend` and its control `p6_p4trend` go live forward, both NOT passed. Loop rounds 1-3
    the same day and round 4 on 17 Nov: no pass (best p 0.036 against a bar of 0.002 after 25 variants).
  - Verdict rule for all three books: nothing before 30 closed forward trades PER COIN.
  **Found on 21 Nov** (the server's own records):
  - Since the refit of 16 Nov every BTC seed is on its 'do no harm' fallback: `p5_rlq` BTC is flat and both Phase 6
    books hold the 30-day momentum short. The BTC results since then are the fallback's, and on BTC the Phase 6 book
    and its control hold the same position.
  - Closed trades per coin after 8 to 9 days: 0 to 5. A verdict by the 30-per-coin rule is months away.
  - Late decisions (more than 15 minutes after the close; `p5_rlq`, BTC record): by day, 184 of 461 on 12-16 Nov (the laptop), 20 of 430
    on 17-21 Nov (the server), all on 17, 19 and 20 Nov, days with deploys that rebuilt the reading cache (not
    matched minute by minute). Nothing to fix in the RL code; fewer rebuild deploys is the cure.
  - The refit of Mon 23 Nov will be the first on the server; the code loads there, the run itself is unproven.
  - Of the Lab items of 11 Nov only the Books rows exist in this project; there was no drift monitor.
  - Record gaps, now closed: HANDOFF said the loop stopped after round 3; this file had no entry for Phases 2-6 or
    the go-lives; `p5_rlq` had no block in research/HYPOTHESES.md (added, marked as written after the fact).
  **Owner's decisions the same day:** the RL exit chooser (RL_NEXT's R1) -> "Not now"; four housekeeping tasks ->
  "Yes, start them": (2) the record gaps above; (3) each RL book's result split into agent and fallback on the
  page; (5) the lateness measured (above); (6) a Telegram card when no seed agent trades a coin, and a weekly card
  with the split and an input-drift reading (`/rl` on request). None of this changes a decision of any book: the
  only change in the decision path is one extra field (`dz`) written with each new decision record. Still open, each
  needing the owner's word: a momentum-only yardstick book, an interim time-based read, the page's Lab block, tests
  of the untested inputs, the exit-and-join learner and the book allocator.
- **The deploy gate stays on the laptop** (21 Nov 2026). The laptop's VM stalled during two full test runs (one
  timing test failed, then the run froze for hours); the owner: "Move to sg box and test it there". Done once, by
  hand, in a scratch copy of commit 65da08d under /tmp on the box (never over the live tree): 1,229 passed, 107
  skipped, 7 failed and 4 errors. Nine of the eleven named a missing file or module (the bar histories under
  `data/` are not in git; the box has no `stable_baselines3`); the other two (test_lean's rebuild test and
  playbook3's release-calendar test) were not traced, and the commit touches neither module. The box also has no
  `cryptography` and no vault worktree, so the vault-feed certificate tests skip there. The box therefore cannot run the whole suite, and using
  it as the gate would weaken the money-path check. `tools/deploy.sh` is unchanged; the deploy runs from the
  laptop with the app's keep-awake on.
- **Give-back alert on the main books** (21 Nov 2026). Suggested by the site-coordination session with the profit
  study; the owner there "Yes" (relayed), and in this project, asked "Build the Telegram alert for a trade giving
  back 25% of its peak profit?": "Yes". `telegram_notify.giveback_update`: one Telegram card when an open main-book
  trade is 25% or more below its best open profit. The best is the best the bot has seen at its checks (15-minute
  marks; for a trade already running, the best since the alert went live); measured on price, so closing half at a
  target is not a give-back; only when the best was worth at least 1% of the book's equity (my choice, to keep small
  wobbles quiet); once per best. An alert only: it reads the page and changes no stop, book or setting.
- **The Setups book's stop stays as it is** (H62, 21-22 Nov 2026). In the site session the owner said the Setups book
  "Should follow the main book stop loss where is wider" and chose "Setups trades, main-book stop" (relayed). Replayed
  before anything was built (H62, `research/out/h62_setups_wide_stop/report.md`): the rule in the form the vault can
  follow (the main book's stop if wider, fixed at the fill) failed the registered bar (worse in the second half pooled
  and on BTC and ETH, deeper worst fall); the forms that move the stop mid-trade did not separate from the current rule
  either. Asked in this project "Keep the Setups book's stop as it is?", the owner: "Keep as is". No engine change; the
  study file and its checks stay in the repo.
- **Three sizes studied; the owner keeps their plan** (H63, H64, 22 Nov 2026). The site session relayed two owner
  decisions made there: "Study first, then paper desk" (the owner wants VIP accounts to be able to run much larger than
  the 2% rule) and "Cut the 15-minute delay". H63 walked one $10,000 wallet through the Setups book's BTC and ETH
  history at three sizes: every size loses on the replay and a larger one loses faster (the 3x book halved before it
  doubled 54 times against 24 from 81 month-starts); the eleven forward days are up at every size and too short to
  judge. H64: over 2,075 entries the bar of delay cost a member nothing on average (+0.001% of price). I recommended
  keeping the 2% rule, adding the paper desk, and leaving the delay. The owner, in this project: "No. I want stick to my
  plan". So both are built as the owner decided; larger real sizes are the site session's vault build, not this project's.
- **The Setups book's early entry, think15-v5.2.9** (22 Nov 2026; owner: "Cut the 15-minute delay", "I want stick to my
  plan"). On BTC and ETH the Setups book (`b_targets` only) books a new entry from flat at the close that decides it, at
  that close's price, instead of at the next bar's open one step later (`CFG["early_entry"]`, `shadows.run`). It is the
  same moment and uses closed bars only; the setup reaches the page, the signal and the vault's book in the deciding
  step. Flips and exits keep their timing. A money-path change: new golden record (the same 152 trades at the same
  prices; 68 setups now posted in their deciding step; 15 setups that end inside their entry bar are now posted and then
  closed by intent). On the stored history the paper record barely moves (BTC 1,061 of 1,062 trades the same, ETH 1,010
  of 1,013; `research/check_early_entry.py`). Known and accepted with it: a setup that ends inside its first bar is now
  joined by members (about 1 in 200), and the signal's "bar A" is now the entry bar itself (the followable entry window
  starts one bar sooner).
- **The paper desk** (22 Nov 2026; owner: "Study first, then paper desk"). `engine15/paper_desk.py`: three forward PAPER
  wallets of $10,000 on the Setups book's BTC and ETH trades from 23 Nov 2026 00:00 UTC, one wallet across both coins
  each: the 2% rule, 100% per coin, the 3x book; H63's rules; finish lines +100% and -50%. Read only, recomputed at
  every step, shown as the `paper_desk` block of `scoreboard.json` (the page's `scoreboard_all`). It models the book's
  trades at three sizes, not the vault. A first read at 30 closed trades.
- **The feed holds a market's book while an exit for it is unsent** (v5.2.9, 22 Nov 2026). Found by the independent
  review of the early entry and confirmed by the site session from the vault's code: the vault's exits go by symbol, so
  an exit that reached it after the next setup's book would close, halve or move the stop of the NEW position, and
  since the early entry a new setup can follow an ended one in the very next post (also on the same side).
  `vault_feed._run` now sends no book for a symbol while an exit intent for it is still pending; a refused or given-up
  exit does not hold it. The same review: the entry arithmetic is sound; the paper desk now leaves out a trade it
  cannot place (a row written twice counts once) instead of stopping; the early-signal preview S2 no longer fires for
  BTC and ETH entries from flat because the signal itself now goes out in that step.
- **Post-mortem of the Setups book and the rally study** (H65, H66, 22 Nov 2026; owner: "Audit from beginning to now
  and see any post mortem. How can we play the rules better", "under what circumstance for btc and eth will turn long.
  Can simulate the possible. Also how can we manage if sudden rally long"). On history the book is flat in R and makes
  its money with a market's own 30-day move (+139R over 4,493 trades) and loses against it (-117R over 1,470); every
  live trade so far is with that move. In 505 sudden rallies while short it turned long within a day in 26% and sold
  again into the move in 24%. Candidates put to the owner, none built: a 30-day trend filter, waiting for a signal
  after a stop-out, skipping unusually tight stops, a Telegram alert on a sharp move against an open Setups trade.
- **H67: the Setups rule with a 30-day trend filter** (22 Nov 2026; owner: "Test it"). Shadow book `b_trend30`:
  `b_targets` with no new entry, and no flip, against the market's own 30-day move (an open trade is never closed by
  it). History replay (found on the same history, so not a validation): the registered bar holds; pooled +127R vs +22R,
  BTC + ETH +135R vs -8R, worst fall -41% vs -62%; the other six markets roughly neutral. Runs forward on paper from its
  first live bar; first read at 30 closed trades. The Setups book and the vault are unchanged.
- **H68: the Setups rule that waits for a real signal after a stop-out** (22 Nov 2026; owner: "After a stop-out, wait
  for a real signal instead of a forced re-entry"). Shadow book `b_wait_stop`: `b_targets` with no forced entry after a
  trade ends at its entry stop, until a signal enters. History replay (found on the same history, so not a validation):
  the registered bar holds; pooled +144R vs +22R, BTC + ETH +64R vs -8R, worst fall -32% vs -62%; but on gold, silver and
  SPX the book was flat almost all of the second half (waits of months to years). Both changes together (descriptive):
  BTC + ETH +93R, less than the 30-day filter alone. Runs forward on paper; first read at 30 closed trades.
- **The Setups book's read at 30 trades has a fixed rule** (22 Nov 2026). An agent preparing the forward reads found
  that "read at 30 closed forward trades" named no moment, no consequence and no handling of the v5.2.9 entry change,
  with the book at 29 trades. Asked "Approve the proposed wording for the Setups book's 30-trade read?", the owner:
  "Approve it". The rule is `research/VERDICT_RULES.md` section 10: the first server scoreboard row with 30 or more
  trades, eight markets pooled against zero, BTC and ETH shown beside it, v5.2.9's own trades reported apart; ahead or
  undecided changes nothing and a second check follows at 60; behind means a post-mortem and the owner decides.
  The same agent drafted wording for five other reads (the profit-floor shadow, the main books, the paper desk, the RL
  books, the trend-filter shadow) in `research/out/forward_reads/status_20261122.md`; those are not approved yet.
- **RL audit task 9, the untested crypto inputs one at a time** (owner, 22 Nov 2026: "Run all above"): done, H69.
  Korea premium, BTC dominance, spot vs perp and the CME gap (spot proxy) were each tested alone on BTC and ETH from
  2020 to 2025-11-10, the holdout not loaded: rank correlation with 1h, 4h and 24h forward returns in both halves with
  month-clustered intervals, raw and beyond past price. None earns a registered place in an RL round 5. Korea premium
  and the CME gap are mostly past price; dominance and spot vs perp show nothing. No RL change follows.
- **Three preparations, 22 Nov 2026** (owner: "Start all 4 with opus 5.5 agents"; nothing graded, no rule changed):
  the RL refit preflight (`research/out/rl/refit_preflight_20261122.md`: Monday 23 Nov's first refit on the server
  should run and does not block the step; a failed refit is silent and can leave cache folders behind), the forward
  reads (`research/forward_reads.py`, read only, prints "due" or "not due"), and the B trail second check
  (`research/b_trail_second_check.py`, which refuses to grade before 60 trades and 10 Dec; its status note proposes
  precise wording for that check, not yet approved).
- **Five studies on turning long and on statistics, 22 Nov 2026 evening** (the owner: "Deploy a study to find how this
  15minds engine can confluence mean reversion and turn long when sharp rebound happen. With stasticially proven edge",
  "Double the workload", and a claim of their own: "within 30 days after price drop below daily ema200 and the price
  drop movement bigger than 20%. Then when price rally back and rise above ema10 has higher probability than 60% of
  winning rate"). Each by an Opus 5.5 agent on its own branch, registered before any number:
  - **H70, a long on a sharp rebound from an oversold state:** 18 candidates (three oversold states, three triggers,
    with and without the engine's odds). All 18 lost per trade after fees in the discovery period, so none was selected
    and the later periods were never opened. Before fees the best beat a random long by about 0.03R.
  - **H71, the engine's own readings in oversold states:** the odds, seven voices and four card readings. Nothing
    passed confirmation (funding against its norm failed narrowly, and it is a general funding effect, not a rebound
    signal). The engine's long bar is almost never reached in an oversold state, and no confirmed signal is being
    thrown away.
  - **H74, the owner's EMA200 / EMA10 claim:** not supported. Under the primary reading the pattern won 10 of 28
    (22 independent episodes, 95% range 20% to 57%) against 51% for the same trade at other EMA10 crosses. Telling 60%
    from 50% needs about 150 episodes; eight years hold 22.
  - **H72, the trend filter and the wait chosen on 2020-2023 and judged later:** on BTC and ETH both beat the current
    rule month by month in 2023-06 to 2025-11 (p about 0.011), by losing less; in the last year no difference; on the
    other six markets the filter was worse. Not a blind test: the ideas came from all the data. A reason to keep the
    two shadow books running, not to change the Setups book.
  - **H73, a member wallet at realistic fees:** at 100% per coin and 0.05% a side the current rule ends at $6,198 from
    $10,000 (worst fall -94.6%); the fee of H63 was double the real one and mattered sevenfold; every size still ends
    below its start. The site session inferred the member's taker fee from the wallet: about 0.05% a fill.
  No engine code was changed by any of the five.
- **The Setups book is not changed on H72; the two shadow books run forward** (22 Nov 2026). After H72 I wrote: "this is
  a good reason to keep the two paper shadow books running forward, and not enough to change the book members follow.
  The forward record is what will settle it." The owner: "Agree". So `b_trend30` and `b_wait_stop` are paper shadows
  only; each is read against `b_targets` at 30 closed trades over the same days, and nothing reaches the Setups book
  or the vault from them without the owner's word in this project.
- **Setups moving-against alert** (22 Nov 2026; owner: "A Telegram alert when price moves sharply against an open
  Setups trade."). `telegram_notify.adverse_update`, the owner's own chat only. For each open trade of the Setups book
  (`b_targets`): one card when the last close is half way from the entry to the trade's starting stop, one when it is
  within a quarter of that distance from the stop; once each per trade, none after Target 1. The thresholds (0.5R and
  0.75R) are a first setting chosen by the engine author; the owner was told. Information only: no stop, book or
  setting changes. It reads 15-minute closes, so a move inside a bar shows at the next close. Context: H66 found that
  in sudden rallies the book rarely turns and the stop is what bounds the loss.
- **The RL momentum yardstick, the interim read and the Lab block** (22 Nov 2026; owner: "Run all above", tasks 4, 7
  and 8 of the RL audit of 21 Nov).
  (4) `engine15/playbook8.py`, book `p8_mom`: the Phase 6 books' daily 30-day momentum fallback alone, through the very
  same code (`forward5.advance` with every seed on the 'do no harm' flag, then `forward5.risk_and_book`), the same
  fees and decision times; BTC and ETH, $10,000 each, from 2026-11-23 00:00 UTC, flat at the start. A yardstick, not a
  hypothesis: never graded; it is there so the momentum rule's result is not credited to an agent. On the scoreboard
  and the page; each Phase 6 book is shown beside it over the same days only.
  (7) An interim read at 8 weeks, registered before any number: `p5_rlq` on 2027-01-07 04:30 UTC, the Phase 6 books on
  2027-01-08 03:00 UTC; each book against buy-and-hold, the Phase 6 books also against `p8_mom` (same days), the agent
  and fallback parts shown apart; only "ahead of", "behind" or "level with" (1-point band), with the numbers.
  `research/rl_interim_read.py` refuses before the date. It changes nothing: the 30-closed-trades-per-coin rule still
  decides and every book stays NOT passed.
  (8) The page's `rl_lab` block (schema 1, `engine15/rl_lab.py`, field list in `docs/RL.md`): per book and coin the
  status, seeds on a model or on the fallback and since when, the split, drift, model and refit history, lateness, the
  yardstick's same-days numbers and the interim date, with the note that none has passed. The site session builds the
  Lab tab from it. No money file was touched.
- **The research queue on the Singapore box** (22 Nov 2026; owner: "Double the workload", then "Queue at least 20
  studies for SG box so it will have always have min 72 hours queue tasks backlog to clear").
  Machinery: `research/queue/runner.py` runs on the box from `/data/research_queue/` (at most 2 jobs, lowest priority,
  one thread each; it starts nothing new when disk or memory is low or for 45 minutes after an engine deploy; a STOP
  file ends everything; jobs resume from checkpoints), driven from the laptop by `tools/research_queue.py` (`snapshot`,
  `add`, `status` with the backlog in hours, `fetch`). It is not a service: after a reboot it is started by hand.
  Studies, 27, all registered before any number (H80 to H106): ten placebo, permutation and bootstrap studies
  (`research/queue/placebo.py`: are the odds, the side, the entry time, the trend filter, the wait after a stop, the
  bias and the stop size distinguishable from the same thing scrambled; a bootstrap of 12-month paths; a costs surface;
  year by year), about 71 CPU hours; twelve walk-forward tests of one setting of the Setups rule each
  (`research/queue/walkforward.py`: chosen on 2020 to 2023-06-07, judged on 2023-06-08 to 2025-11-10) and five
  chart-pattern claims on BTC and ETH daily bars (`research/queue/pattern.py`), about half an hour together.
  Standing rules for every queued study: the last year of data (from 2025-11-11) is never loaded; each family counts its
  tests in a ledger; a pass leads only to a proposal for a forward PAPER shadow book and needs the owner's word; nothing
  reaches the Setups book or the vault. Said to the owner: the first batch is about 72 hours of one processor (about 36
  hours with two jobs at a time); keeping the backlog at 72 hours means new studies must be designed and registered as
  it drains, and runs that add nothing will not be queued to pad it.
- **Queue batch 1 results** (22 Nov 2026, 20 quick studies, about 13:04 to 13:15 UTC; summary in
  `research/HYPOTHESES.md` under "Queue batch 1 results"). No setting of the Setups rule chosen on 2020-2023 beat the
  current one on 2023-2025 (H90 to H100; six times the current setting was already the choice); no daily pattern on BTC
  and ETH is supported (H102 to H106); the current rule's 12-month results lose 54% of the time on history (H87), break
  even at 0.086% a side on BTC and ETH in R (H88), and rest on single years (H89). H81 (side placebo) gave a
  surprising result and is under audit for an artefact before it is read. H101 queued after its siblings finished.
- **H81 void, H82 withdrawn** (22 Nov 2026). An Opus 5.5 agent audited H81's surprising result (the book's side choice
  "worse than random"): an artefact of the placebo's design. Permuting sides within a month gives trades the side of a
  later trade, and the book's later sides follow the month's move, so the placebo trades on information the book did
  not have yet. The scoring itself is sound. Against side choices with no future information the book is about as good
  as a coin. H82 had the same flaw and was taken out of the queue before it ran. Recorded under "Audit of H81" in
  `research/HYPOTHESES.md`.
- **The Setups book's read at 30 trades: ahead; nothing changes** (23 Nov 2026, by `research/VERDICT_RULES.md`
  section 10, approved 22 Nov). The 30th trade (a gold short stopped at 01:00 UTC, -$271) made the scoreboard row:
  30 trades, 73% won, +$6,915, mean +$230 a trade, 90% range +$105 to +$356, "ahead". BTC and ETH alone: 11 trades,
  9 won, +$3,381. So nothing changes and a second check follows at 60 trades. The record says plainly that these 30
  trades come from one two-week falling-market spell and that the same rule is flat on history.
- **The research queue throttled the box; it now runs one job at a time** (23 Nov 2026). The Singapore box is a
  t2.xlarge, a burstable instance whose CPU credits are earned at about 0.9 of one processor. Two queue jobs around
  the clock drained the credits by about 02:00 UTC; the hypervisor then withheld about 75% of processor time, the
  engine's steps went from about 1.5-3 minutes to about 11, and the vault's book posts landed about 11 minutes after
  each close (no exit fell due meanwhile; the member's stops rest on the exchange). The queue was stopped at 04:30 UTC
  and the next step took 192 s. Asked how to handle the throttled box, the owner: "No i dont want unlimited. We can let
  the studies go sequential rather concurrent". The queue restarted at 04:35 UTC with one worker (`tools/research_queue.py
  start --workers 1`); its jobs resumed from their checkpoints. With one job the credits will not rebuild while it runs,
  so the engine's steps are watched; if they slow materially the queue is paused first and the owner told.
- **The wait after a trailing-stop exit stays** (23 Nov 2026). The owner saw the gold, silver, WTI and Brent main books
  flat for more than four sessions after their trailing-stop exits (01:00 and 04:00 UTC) and asked whether that was
  normal. Told it is the v5.2.8 rule (no forced entry after a trailing-stop exit until one side leads by 5 points; the
  4-session limit after every other exit; the Setups book unchanged), the owner: "Ok noted". No change.
- **VIP joins only above a 5-point Lead; think15-v5.2.10** (23-24 Nov 2026). On 23 Nov a single 15-minute candle (13:45
  UTC, BTC +4.2%, ETH +4.9%) stopped the forced shorts of every book, and the VIP member's two shorts on Binance
  (wallet 17,215 to 16,670 USDT). The owner then ordered, in the AI Trading session (relayed here, "confirmed twice"):
  VIP accounts take a setup only when the engine's Lead at the step that opened it is above 5.0 points in the setup's
  direction. The vault applies the cut; Mind 15 supplies the number: `lead_pts` in the open book (`vault_feed.py`,
  spec agreed by message with that session: a number, at most 2 decimals, -100..100, never on FLAT, left out when
  unknown, and a missing value does not pass). Built with sending off on 23 Nov (commit 2e6c1c1); the vault that accepts
  the key was installed 23 Nov 16:20 UTC (package 81c96bd4); asked here whether to bump the version, deploy and switch
  sending on, the owner on 24 Nov: "Yes, deploy it". The golden record was rewritten for v5.2.10 (only `lead_pts` and
  the version changed). Numbers given to the owner beforehand: live since 11 Nov on BTC and ETH, setups opened on a
  real call 9 trades, 7 won, +$2,558, forced 4 trades, 2 won, -$430; on history (H65) both are about flat per trade.
  The paper Setups book itself is unchanged and still takes forced entries. The two shorts opened 23 Nov 15:00 UTC
  (forced, Lead 0.0 and 1.1 points toward up) were joined at 3x before the filter existed and carry no Lead.
- **H107: buying a capitulation bounce does not pass** (23 Nov 2026; owner: "Deploy a study how we can take advantage
  of last fri where price huge drop to 55k and then rally back to now"). Two long rules shaped by the 21 Nov low were
  registered before any history number: rule A broke even over 123 trades (2019 to Nov 2025), rule B had 32 trades,
  too few to judge. No shadow book proposed. `research/out/h107_capitulation_rebound/report.md`.
- **Agents on Fable 5.2** (24 Nov 2026; owner: "utilise fable 5.2 agents").
- **v5.2.10 is committed but NOT live; the queue is stopped; H86 runs on the laptop** (24 Nov 2026, about 04:50 UTC).
  The owner said "Do for me" and `tools/deploy.sh` was started, then stopped by this session during its test phase,
  before anything on the box changed (the box still runs d50b5bf, v5.2.9). Reason: the box has been out of CPU credits
  since 23 Nov 02:40 UTC (58% steal measured), the version bump makes the first step rebuild the reading cache, and a
  throttled rebuild can pass the 25-minute worker limit and the watchdog's 30 minutes while the vault member holds two
  3x shorts (Target 1 taken, stops at the entry on the exchange). The research queue was stopped (`STOP`; H85 keeps its
  checkpoint at 17,417 of 65,000) so credits can build before the deploy. The owner, the same hour: "For those sg box
  research still pending. Utilise this laptop to start 1": H86 was moved to `held/` on the box and started on the
  laptop in the worktree `C:\Ai Dataset\engine-15m-q86` (commit 0a94526, the box's fits, bars and reading cache copied
  while the engine slept; output `out_H86/`; the fits overlay was filled with copies because Windows refuses the
  harness's symlinks; no code changed). The AI Trading session reported the owner's choice there to cap the research
  runner's CPU (a slice at about 30%); it is not applied until the owner confirms it in this project.
- **The research queue on the box stays stopped** (24 Nov 2026). Asked whether to restart it under the 30% CPU cap
  or keep it stopped, the owner: "Keep it stop now". It is not restarted, capped or not, without the owner's word. H85
  waits with its checkpoint; H86 runs on the laptop.
- **The exit learner `b_learn` is built as a paper shadow, NOT passed** (24 Nov 2026; H109). The owner, on three
  RL-style ideas that "would run as a paper shadow first" (docs/RL_NEXT.md): "Ok lets do it" (on 21 Nov it was "Not
  now"). This is R1, the EXIT part only. `engine15/learn_book.py`: six shadow books' exit rules on BTC and ETH are the
  arms (`b_targets`, the hold copy `main`, `b_trail`, `b_be_t1`, `b_ema20_1h_t1`, `b_sma20_1h_t1`); each arm's closed
  trade is a reward (net R after fees, 30-day half-life) in one of four market states (volatility calm or wild, 4h and
  daily trend agreeing or mixed, from closed 15-minute bars); when flat, the book copies the next trade of the arm
  that leads in that entry's state. One $10,000 book per coin from 2026-11-25 00:00 UTC, recomputed every step from
  the arms' own records (no state of its own), shown on `scoreboard.json` as a shadow row and the `exit_learner`
  block. Registered before any code or number (commit d9002fd). H36 found holding beat every other exit on history,
  so the learner only adds something if the right exit depends on the market state: unproven. Read at 30 and 60
  closed trades against `b_targets` and the best single arm over the same days. Nothing reaches the Setups book or
  the vault. Not deployed: it goes live with the next deploy after the merge and the full test suite.
