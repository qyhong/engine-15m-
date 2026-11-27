# Mind 15: context for a Claude session in this folder

This folder is a stand-alone 15-minute paper-trading engine ("Mind 15") for eight markets in five
groups: crypto (BTCUSDT, ETHUSDT), metals (XAUUSD, XAGUSD), fx (USDJPY), index (SPX, cash hours) and
energy (WTI, BRENT). Each market has its own $10,000 paper book. Read, in order: `docs/CHARTER.md`
(the agreed purpose, every task and its status, decisions the owner has made), `THOUGHT_PROCESS.md`
(the design; its "Now" section lists what changed since it was first written), `HANDOFF.md` (moving parts).

Beside the main books run, all forward and on paper: shadow books (`engine15/shadows.py`: v4, H3, A, B,
H5, the H67 30-day trend filter `b_trend30`, the H68 wait after a stop-out `b_wait_stop`, the 4h/daily yardsticks, the 1h/4h swing minds, the H36 exit shadows,
and the H61 profit-floor follower in
`engine15/floor_book.py`, which copies the hold copy's trades and is not a rule of `run()`), twelve strategy books
(`engine15/playbook.py` to `playbook3.py`, H6-H17), the CPI book (H1), and forward books that are NOT passed:
rules A/B (`playbook4`), the RL agents (`playbook5`, `playbook6`) and the BTC/ETH pair book (`playbook7`, H37 V4).
The paper desk (`engine15/paper_desk.py`, 22 Nov 2026) walks three paper wallets through the Setups book's BTC and ETH
trades at three sizes; it is read only and lives in `scoreboard.json`.
The H108 shadow mind `m_regime_trust` (`engine15/regime_trust.py`, `shadows.MINDS`, 24 Nov 2026; RL idea R3) trades the
main rule on odds mixed with card trust kept per regime bucket: NOT passed, paper only, not a rule of `run()`.
The exit learner `b_learn` (`engine15/learn_book.py`, H109, 24 Nov 2026; paper only, NOT passed) copies, on BTC and ETH,
the next trade of whichever of six exit shadow books (`b_targets`, `main`, `b_trail`, `b_be_t1`, `b_ema20_1h_t1`,
`b_sma20_1h_t1`) leads in the entry's market state; it is recomputed every step from those books' records inside
`reports.scoreboard`, keeps no state, is not a rule of `run()` and never reaches the vault.
The book allocator `a_alloc` (`engine15/book_alloc.py`, H110, 24 Nov 2026; paper only, NOT passed) splits one paper wallet
each UTC day between the forward books on the scoreboard; read only, in `scoreboard.json`.
The capitulation-long books `p9_rebound_a` and `p9_rebound_b` (`engine15/playbook9.py`, H115, 24 Nov 2026; paper only,
NOT passed) run H107's rules A and B forward on BTC and ETH because the owner asked for them, although history does not
support the rule; they keep their own state in `data/capit_long_state.json`, the Telegram bot sends the owner one card
per trigger, and they never reach the vault.
The Setups copy `b_rebound` (`engine15/rebound_book.py` and the rule key `rebound` in `shadows.run`, registry
`shadows.MINDS`; H117, 24 Nov 2026; paper only, NOT passed) is `b_targets` on BTC and ETH with one override: at an H107
rule A trigger a short or flat book goes long at the next open (H107's trade) and the Setups rule is not consulted
while that long lives. Started on the owner's word although history does not support the rule; its state is its own key
in `data/shadow_state.json`, and it never reaches the vault.
The engine version is `CFG["version"]` in `engine15/config.py` (think15-v5.2.11 on 27 Nov 2026); what each version changed
is in `VERSION_NOTE` there and in THOUGHT_PROCESS.md "Now". It runs on the Singapore box, not on this laptop (HANDOFF.md).
`out/live/scoreboard.json` judges every book on live trades only.
Hypotheses are registered in `research/HYPOTHESES.md` before they are graded.

## Discussing the engine with the owner

The owner will ask what the engine is thinking and why. Answer from what the engine wrote,
never from your own view of the market:

- `journal/<YYYY-MM-DD>.jsonl`: one JSON line per coin per 15-minute close (live sessions).
  Fields: `decision` (a sentence), `action`, `position`, `odds`, `edge_pts`, `cards` (the ten
  cards: reading, pull, trust), `voices`, `for_long`, `for_short`, `data` (every reading),
  `graded_now`, `levels`, `econ_next`, `raw` (live feeds). `journal/<day>.md` is the same for reading.
- `journal/replay/`: days rendered from the history replay on request (`py -3 -m engine15 journal DATE`).
- `out/live/page.json`: the latest state as the web tab sees it.
- `py -3 -m engine15 ask now | why ETH | cards BTC | today | learning` prints ready answers.
- `py -3 -m engine15 postmortem [reading|trades] [--days N]` for look-backs.

Quote the readings and the reason the entry gives. If the journal does not hold the answer, say so.

## The money path (real orders follow this code)

The site's VIP vault copies the paper book `b_targets` for BTC and ETH through `engine15/vault_feed.py` (owner, 18 Nov
2026) and places real orders for opted-in accounts; on 20 Nov 2026 the AI Trading Bot session reported that it sizes
real futures trades from it. So a change in any of these changes real entries, stops and exits:

- `engine15/shadows.py`: `run()` under the `b_targets` rule (`{"targets": True, "early": True}`), `asset_view`, `PART`. The same `run()`
  serves a dozen research books: an edit for one of them must leave `b_targets` exactly as it was.
- `engine15/live.py`: `plan_targets` (the two targets, set once at entry) and `asset_cfg` (fee, leverage cap).
- `engine15/policy.py`: `decide` (entries, flips, the forced entry after `idle_max` flat sessions).
  Since v5.2.9 a BTC or ETH entry from flat is booked in `shadows.run` at the close that decides it (`CFG["early_entry"]`):
  the vault identifies a setup by its entry and `opened_utc`, so neither may change after the first post.
- `engine15/backtest.py`: `leverage` (position size). `engine15/exits.py`: `PART`, `reached`, `be_stop`.
- `engine15/setups.py` (the market entry of setups.json the feed reads) and `engine15/signals.py` (the entry window).
- `engine15/setups_voice.py`: which book speaks for each market (the switch `TRAIL_MARKETS`, off = `()`; the state in
  `data/setups_voice_state.json`; docs/TRAIL_SWITCH_PLAN.md). Naming a market there is the owner's decision only.

**The trail voice (built 26 Nov 2026, both switches OFF).** The owner decided the Setups page, the signals and the vault
move to a trailing-stop book ("Lets switch", "Page and VIP"; docs/TRAIL_SWITCH_PLAN.md, H119). The book is
`b_trail_setups` (`{"trail": True, "early": True}`): the same `run()`, so the rule above about leaving `b_targets`
exactly as it was now covers this book too. It is published nowhere until `setups_voice.TRAIL_MARKETS` names a market,
and nothing of it is sent to the vault until `vault_feed.SEND_TRAIL` is True as well. Both go on together, only on the
owner's word in this project AND after the AI Trading Bot session confirms an installed vault package that accepts the
trail bodies (`out/live/trail_book_preview.json`, written every step by `engine15/trail_preview.py`, is the dry run it
checks; that module never posts). `tests/test_money_path_trail_golden.py` freezes what the vault is told on the trail
voice; from the day the switches go on it is a golden test like the first one.
- `engine15/vault_feed.py`: all of it (the book body, the exit intents, the state in `data/vault_feed_state.json`).
- `engine15/config.py`: every constant the above read (`idle_max`, `stop_units`, `risk_per_trade`, fees, flip and edge
  thresholds, the release guard, the higher-timeframe bias).

`b_rebound` (H117) is a paper copy of the Setups book that runs through the same `run()` behind the rule key `rebound`
(off for every other book). The vault must never read it: `setups.BOOK` (and `signals.BOOK`) stay `b_targets`. Pointing
the feed at `b_rebound` is a real-money decision that only the owner takes (docs/CHARTER.md, the rebound plan).

The list as files is `tools/money_files.txt`. Rules for it:

- `tests/test_money_path_golden.py` plays fixed bars through this chain and compares every trade, book body and exit
  intent with a record. If it fails, your change alters what the vault is told. That needs the owner's word in this
  project and a version bump; only then is the record rewritten (`--write-golden`). Never rewrite it to make a change pass.
- A change here that keeps the golden test green (a new field behind a switch that is off, a comment) still deploys only
  after the FULL test suite. `tools/deploy.sh` enforces this, refuses a commit that is not on `origin/main`, and writes
  `/data/mind15/DEPLOYED.json` (the commit that is live). Deploy only with that script.
- Do not add a key to the book or an intent until the AI Trading Bot session confirms the LIVE vault accepts it: the vault
  refuses a body with any key it does not know, and a refused book means members get no update.
- Since v5.2.10 (24 Nov 2026) an open book carries `lead_pts`, the setup's opening Lead (`vault_feed.SEND_LEAD`; a
  number, at most 2 decimals, -100..100, never on FLAT, left out when unknown). The vault can filter joins on it
  (owner, 23 Nov: VIP accounts take a setup only when its opening Lead is above 5.0 in its direction; the filter is the
  AI Trading Bot session's switch) and treats a missing value as "does not pass": do not switch `SEND_LEAD` off, lose
  the feed's memory or change how the value is taken without telling that session first.
- Since v5.2.11 (27 Nov 2026) an open book carries `opened_by` (`vault_feed.SEND_OPENED_BY`): "ENTER", "FORCED" or
  "FLIP", the book's own word for the entry, read from page.json beside setups.json (setups.json does not carry it);
  never on FLAT, left out when unknown. The vault (package 0a74aa29) uses it so that a member skips a FORCED setup after
  a losing first stop on that coin (owner; H68: those entries lost on BTC and ETH in history); the rule is the AI
  Trading Bot session's switch. If the vault is ever rolled back to an older package, switch `SEND_OPENED_BY` off
  FIRST: the older code refuses a book that carries the key.
- A restart is short, but a deploy that rebuilds the reading cache (a card or `CFG` change) takes about 15 minutes: the
  book ages, the vault stops joining after 30 minutes, and exits wait. Do it when BTC and ETH are flat or far from an exit.
- The feed's memory is `data/vault_feed_state.json`; the book's is `data/shadow_state.json`. Losing or rolling back either
  while a setup is open loses exits or sends wrong ones: follow `docs/RESTORE.md`, never copy an old file in by hand.

## Rules

- Paper only. Nothing here places orders; do not add anything that does. One owner-approved exception (18 Nov 2026,
  docs/CHARTER.md): `engine15/vault_feed.py` SENDS the BTC/ETH setups book to the site's VIP key vault on the box,
  which places real orders for opted-in accounts, plus exit-only intents (close, reduce at Target 1, move stop to entry
  after Target 1; owner 18 Nov). Mind 15 holds no exchange key and sends no order itself; do not widen this (more
  markets, intents that open or add, sizes) without the owner's word in this project.
- Never describe a reading, a voice or Kronos as having a proven edge. The replay is a
  warm-up and post-mortem material, not validation (see THOUGHT_PROCESS.md).
- `C:\Ai Dataset\eth-signal-bot` (the AI Trading Bot) is read-only from here. Its own session owns it.
- Constants live in `engine15/config.py`. Changing one is a new version of the thought
  process: bump `version` and say so in the journal's next entry.
- Closed bars only; anything computed on 1h/4h/1d bars goes through `data.htf_on_15`.
  `tests/test_engine.py::test_evidence_never_reads_the_future` must stay green.
- The web tab on alphaprediction.ai/aitrading is deployed by the AI Trading Bot session's
  page pipeline (`C:\tmp\kronos\aitrading-pages`), on the owner's word. This project only writes `page.json`.
