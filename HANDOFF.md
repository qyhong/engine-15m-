# Mind 15: where things stand (updated 24 Nov 2026: think15-v5.2.10; the vault feed is on the REAL-MONEY path)

Main-book exit rules by market (config.py `be_t1`, `half_t1`, `t2_exit`, `trail_stop`, `trail_wait_signal`): USDJPY
sells half at Target 1 and the rest at Target 2 with the stop to the entry after Target 1 (v5.2.7); the S&P 500 sells
half at Target 1 and lets the rest run with its stop at the entry (v5.2.6); the other six (BTC, ETH, gold, silver,
WTI, Brent) trail their stop once a trade is 1R in profit (the tighter of the last confirmed 15m swing and 2 x
ATR(15m), never looser; exit word `TRAIL`) and, after a trail exit, stay flat until one side clears the entry bar:
no forced entry (v5.2.8, owner 21 Nov 2026). Everywhere else the 4-session mandate is unchanged, including after an
exit at the entry stop or on a flip. The vault copies the Setups book (`b_targets`), which v5.2.8 does not touch.
v5.2.9 (owner 22 Nov 2026, "Cut the 15-minute delay") changes WHEN that book shows a new BTC or ETH entry from flat:
in the step that decides it, booked at that close's price (`CFG["early_entry"]`), so `opened_utc` equals the book's
`as_of_utc` on its first post. Flips still appear one bar after the decision; exits are as they were.
v5.2.10 (owner 23-24 Nov 2026) adds one key to the open book the vault gets: `lead_pts`, the Lead (P(up) minus P(down),
points, positive favours LONG) of the step that opened the setup, fixed for its life (`vault_feed.SEND_LEAD`,
`opening_lead`; kept in the feed's memory as `pos[sym]["lead_pts"]`, with each step's reading in `lead_seen` for a flip
shown a step later). The vault's join filter on it (lead above 5.0 in the setup's direction) is the AI Trading Bot
session's switch; a setup with no known opening Lead carries no key and does not pass that filter. Live on the box since
24 Nov 2026 08:33 UTC (commit 5ed3d6e); the vault's lead filter is ON since 09:25 UTC the same day (that session's
switch). The three RL-style paper books (H108, H109, H110) are live since 09:52 UTC (commit 6f9c400). `tests/conftest.py` keeps the queue harnesses' BLAS thread settings from
leaking into other tests (they crashed the parallel-step test's child engine on the Windows ARM64 laptop).
Since 21 Nov 2026 a follower book runs beside the shadow books (`engine15/floor_book.py`, `shadows.FOLLOWERS`,
book name `f_floor_33_3r`): the hold copy's trades with a third of the best closed profit locked once 3R up (H61).
It started as a copy of the hold copy's book, is not a rule of `shadows.run`, and a failure in it is logged and
skipped. No version change: no constant of the main book moved.
H67 (22 Nov 2026) adds the shadow book `b_trend30` (`shadows.CHALLENGERS`): `b_targets` with a 30-day trend
filter (rule key `trend_days`); it starts flat at its first live bar, the vault never reads it.
H68 (22 Nov 2026) adds `b_wait_stop`: `b_targets` with no forced entry after an entry-stop exit until a signal
enters (rule key `wait_after_stop`, state key `wait_stop` in that book only); also a shadow, never read by the vault. H60 (exits by regime, per market) is registered and running; it may change this table.
H108 (24 Nov 2026; RL idea R3, owner "Ok lets do it") adds the shadow MIND `m_regime_trust` (`engine15/regime_trust.py`,
registry `shadows.MINDS`): NOT passed, paper only. The live card-trust learner kept separately per regime bucket (the
`regime` reading: trend or range; `vol_rank` at 0.5: high or low; four buckets), the live constants read from the config,
the live mixing unchanged; its book is `shadows.run` with no rule (the fresh main copy's rule and sizing) on those odds,
all eight markets, flat at its first live bar. It is not a rule of `run()`: `shadows.advance` calls it after every
challenger and follower inside a try/except (a failure is one log line, `shadow mind m_regime_trust failed` or `regime
trust mind failed on <market>`, and the next step catches the book up from its own `mind.last_ms`). It keeps no table:
every step it recomputes the four tables from the prep's graded calls. State: `shadow_state.json` `books.m_regime_trust`
(the book plus `mind`: last bar, bucket, graded calls behind the bucket, forward bars per bucket) and
`late_starts.m_regime_trust` (its start and the main copy's equity then). One log line per group and step:
`<group>: regime trust mind (H108, paper) 0.0Ns: <market> <bucket>, ...`. Trades: `shadow_trades_m_regime_trust_<market>.csv`.
Scoreboard: its row in `scoreboard.json` carries `label`, `passed: false` and `vs_main_copy` (H108's comparison line; no
number and no word before 30 closed trades). The Telegram ranking shows it under its raw name (no short name was added).
H117 (24 Nov 2026; owner on step 1 of the rebound plan: "1. Yes.") adds the paper shadow book `b_rebound`
(`engine15/rebound_book.py`; NOT passed, NOT deployed when this was written): `b_targets` on BTCUSDT and ETHUSDT only, plus
the rule key `rebound` in `shadows.run`. At an H107 rule A trigger (`playbook9.features` on the step's own bars, the
last 45 days of them) a SHORT book closes the short and opens a long at the next open, a FLAT book opens the long, a
LONG book counts the trigger; the long is H107's trade (stop 3 x ATR(1h), half at +1R and the stop to the entry, the
rest at +2R, out at the close of the 192nd bar) at the Setups book's own size and fee, and the Setups rule is not
consulted while it lives. It is a rule of `run()` but it is NOT in `shadows.CHALLENGERS`: that loop runs every book on
all eight markets and one exception in it stops every book's step, `b_targets` included. It sits in `shadows.MINDS`,
so `shadows.advance` calls it after every challenger and follower inside a try/except; `playbook9` is imported only
inside `rebound_book.trigger`. State: `shadow_state.json` `books.b_rebound.<coin>` (the book as `b_targets` keeps it,
plus `rebound`: the open long, a trigger waiting for the next open, the counts `seen` / `from_short` / `from_flat` /
`while_long` / `in_trade`, the last 50 rebound longs; plus `h117`: `last_ms`, `no_trigger_steps`) and
`late_starts.b_rebound` (its start, the main copy's equity then, and `ref_utc` / `own_eq` / `setups_eq` for the
comparison with `b_targets`). It starts FLAT at the first step after the deploy; no key of any other book moves.
Log, one line per crypto step: `crypto: b_rebound (H117, paper) 0.0Ns: BTCUSDT <side>, ETHUSDT <side>`; on events
`b_rebound <coin>: rule A trigger at the ... UTC close, taken from SHORT|FLAT ...`, `... counted, not taken: ...`,
`... the rebound long of ... closed (...)`; on trouble `the rebound trigger could not be computed (...): this step
runs as the Setups rule` (the step then is plain `b_targets`; an open rebound long is still managed) or `b_rebound
failed on <coin>` (not advanced; the next step walks the missed bars from `h117.last_ms`). Trades:
`shadow_trades_b_rebound_<coin>.csv` (entry word `REBOUND`; exit words `STOP`, `T1+STOP_BE`, `T1+T2`, `T1+TIME`,
`TIME`; a short it replaced ends `REBOUND` or `T1+REBOUND`). Page: `shadows.books.b_rebound` (two coins; each view
adds `label`, `rebound_long`, `rebound_triggers`, and for an open rebound long `rebound_from`,
`rebound_time_exit_utc`). Scoreboard: its row carries `label`, `passed: false`, `vs_setups_book` (H117's comparison
line; no number and no word before 30 closed trades) and `override` (the override's own record, no verdict). The
Telegram bot sends its generic closed-trade card for it as for the other Setups copies (it is not in `QUIET`).
Measured on the laptop, real bar files, 276,613 bars: 20 to 35 ms a step for both coins (the trigger about 3 ms a
coin). The vault never reads it: `setups.BOOK` stays `b_targets`. Tests: `tests/test_rebound_book.py`, with
`tests/fixtures/rebound_main_books.json` (what every book gave on main's code before the rule key; never rewritten to
make a change pass).
H109 (24 Nov 2026) adds the exit learner `b_learn` (`engine15/learn_book.py`, BTC and ETH, paper only, NOT passed): it
copies the next trade of whichever of six exit shadow books leads in the entry's market state. It is not a rule of
`shadows.run` and not in `shadows.FOLLOWERS`; `reports.scoreboard` runs it (see "Exit learner" below).
Every scoreboard row also carries the by-day read (`days`, `range90_by_day_usd`, `verdict_by_day`; `reports.by_day`,
24 Nov 2026): the same mean with a range that lets one day's results move together. It is shown beside the registered
per-trade `verdict`, which nothing here changes.

Read `docs/CHARTER.md` first (purpose, every task and status, the owner's decisions), then
`THOUGHT_PROCESS.md` ("Now" section) and `CLAUDE.md`. This file is only the moving parts.

## Running
- **REAL MONEY FOLLOWS THIS ENGINE (BTC and ETH).** The site's VIP vault copies the paper book `b_targets` through
  `engine15/vault_feed.py` and places real orders for opted-in accounts. Read CLAUDE.md "The money path" before touching
  `shadows.py`, `live.py`, `policy.py`, `backtest.py`, `exits.py`, `setups.py`, `signals.py`, `vault_feed.py` or `config.py`.
  Deploy only with `bash tools/deploy.sh` (what is live: `/data/mind15/DEPLOYED.json`). Restore: `docs/RESTORE.md`.
  Rebuild the box: `tools/server/REBUILD.md`.
- **Live loop (it runs on the Singapore box, see below; NEVER start it on the laptop while the service runs)**. The
  laptop command, for the record only:
  `$env:ENGINE15_PUSH = '1'; $env:ENGINE15_LEAN = '1'; py -3 -W ignore -u -m engine15 live` in this folder (lean step on). Steps after every 15-minute close for five market groups, writes the journal, pushes
  `out/live/page.json` to alphaprediction.ai/aitrading/mind15 (the AI Trading Bot session deploys the PAGE;
  this project pushes only the data). Asks Windows not to idle-sleep; a closed lid still sleeps the laptop.
  After ANY code change: Ctrl-C and start it again (between steps). It naps against the wall clock: after the Mac
  sleeps (the Windows VM pauses) it logs "woke ...s late" and catches up every missed bar.
- **WHERE IT RUNS (since 16 Nov 2026 10:45 UTC): the Singapore EC2 box, NOT the laptop.** ec2-user@13.251.40.113 (Elastic IP
  since 16 Nov 11:05 UTC; it was 47.129.218.75 before) (key
  `~/.ssh/minds15.pem` on the laptop; Amazon Linux 2023, t2.xlarge 4 vCPU / 16 GB; project at `/data/mind15`, Python
  `/data/venv` with pinned wheels, env `/data/mind15/mind15.env`, launcher `/data/mind15/run_live.sh`). systemd service
  `mind15` (Restart=always, enabled at boot, ENGINE15_PUSH=1), log `/data/mind15/live.log`. It pushes page.json with its
  own key `~/.ssh/mind15_web` (in the web box's authorized_keys, from="13.251.40.113", no pty) and pulls web answers with
  the same key (`/data/mind15/tools/pull_answers.py`, cursor `/data/mind15/data/pull_cursor.json`). Estate files copied to
  `/data/estate`. NEVER start the laptop loop again while the service runs (two engines would overwrite the page).
  Status: `ssh -i ~/.ssh/minds15.pem ec2-user@13.251.40.113 "systemctl is-active mind15; tail -5 /data/mind15/live.log"`.
  **Own user + sandbox (17 Nov 2026 04:05 UTC, owner "Yes, do it"; the box audit's top finding):** both services run as
  the system user `mind15` (no shell, no sudo) under systemd sandboxing (ProtectSystem=strict; they can write only
  `/data/mind15/{data,journal,out,research/out}` and `/var/lib/mind15`; the engine cannot read `secrets/`, the bot
  cannot read the push key; the site's auth/backup/letsencrypt paths are inaccessible). The push key is a copy at
  `/etc/mind15/push_key` (root:mind15 0640; `mind15.env` points there), known_hosts in `/var/lib/mind15/.ssh`.
  State folders are mind15:mind15, setgid, group-writable; ec2-user is in group `mind15` (deploys, research runs, the
  laptop's backup). Code and `/data/venv` stay ec2-user's, read-only to the service (it writes no .pyc: the deploy
  compiles them). Script with `--undo`: `tools/server/mind15_own_user.sh` (unit backups in
  `/home/ec2-user/mind15_backups/`). Deploy with `bash tools/deploy.sh [pytest args]` (tests, waits for a real gap,
  unpacks HEAD, restarts both services). "Asleep" means the log's last line is `sleeping Ns ...` AND log mtime + N is
  still in the future: the last line alone is wrong during a long silent step. A restart is followed at once by a
  catch-up step if a close was missed.
  24/7 hardening (16 Nov 13:05 UTC): drop-ins `/etc/systemd/system/{mind15,mind15-telegram}.service.d/24x7.conf`
  (RequiresMountsFor=/data, StartLimitIntervalSec=0: they wait for the data disk and never give up restarting);
  `/etc/logrotate.d/mind15` rotates `/data/mind15/*.log` weekly (copytruncate, 8 kept). Crash test: SIGKILL between
  steps, back in 30 s, next step on time. The Telegram bot warns when the data disk has under 3 GB free (it had
  6.5 GB free of 24 GB; the reading cache `data/evcache` is 13 GB and the S&P cache is not built yet).
  Deploying code: commit, `git push origin main`, then `bash tools/deploy.sh` and nothing else (never a hand-made
  `git archive | ssh`: it leaves no receipt and skips the gates). Research runs on the box too
  (`nice -n 5 /data/venv/bin/python research/<study>.py`; outputs copied back with scp). The laptop keeps the code, the
  version history and a copy of the data, so it can take over again (its reading cache was deleted: a first laptop step
  would rebuild it). The candle-forecast feed runs on the same box since 16 Nov 11:35 UTC (AI Trading Bot's systemd
  `aitrading-forecast`, nice 10): `ENGINE15_KRONOS=/var/www/aitrading` (forecasts.json, news.json). nginx on the box serves
  the new public host https://aitrading.alphaprediction.ai/ (page: /mind15/page.json); the old alphaprediction.ai/aitrading/
  redirects there. The page is still PUSHED to the old web box over ssh until the AI Trading Bot session says otherwise.
- **Telegram alerts (16 Nov 2026, owner: "Alerts + daily summary"):** `engine15/telegram_notify.py`, systemd service
  `mind15-telegram` on the box (log `/data/mind15/telegram.log`, state `data/telegram_state.json`). It only reads
  out/live/page.json, scoreboard.json and the RL refit logs. The bot key is a file the OWNER places at
  `/data/mind15/secrets/telegram_token` (chmod 600; `secrets/` is git-ignored); never handle or print it. The first chat
  that sends /start is locked in; /summary sends the summary on demand; the daily summary goes at 00:00 UTC (08:00 SGT).
  Since 17 Nov: `/health` and one "Data: N of M cards reading" line in the summary (a card is silent after 8 closes of
  its own market without a read; alert once, recovery once), and a weekly live-calibration card with `/calibration`
  (`engine15/livecheck.py` re-grades each stated call with the engine's own triple-barrier rule on the bar files and
  checks it against `graded_now`). The bot replaces the forecast model's name as the page does.
  Since 17 Nov 2026 the bot shows every paper-book dollar amount at 15x (`DISPLAY_X`, env `MIND15_TG_DISPLAY_X`; first 100x, then
  "Lets adjust 100x to 15x. So it is at 1mil usd range"), matching the
  website's display-only scaling (owner: "Enlarge the capital by 100 times"; for the bot "Scale the bot 100x too"). The engine's
  files keep the real figures; never rescale page.json or setups.json (the pages already multiply). The owner chose to
  keep the word "edge" in engine sentences and let the website relabel it ("Leave it to the website"); tell the AI Trading
  Bot session before adding any new engine sentence with "edge" or book money in it.
- **Subscriber signal preview (17 Nov 2026, owner "Yes, build preview"; H53, signal book S1):** `engine15/signals.py`,
  run inside the bot's check. Source: the shadow book `b_targets` (`page["shadows"]["books"]["b_targets"]["assets"]`);
  a signal = a new open position; the FOLLOWABLE record (limit at the book's entry, four bars after the alert bar, half
  at Target 1, rest at Target 2) is the one judged; rules and the 17 Nov amendment are in `research/HYPOTHESES.md` H53
  and must not be tuned. State `data/signals_state.json`, log `data/signals_log.jsonl` (the registered record: live
  since 2026-11-17 04:58 UTC; positions open then were not signalled). PREVIEW: every card goes only to the owner's
  chat, first line "Subscriber preview"; no channel exists; commercial gate = 100 signals, 60 days, "ahead".
  Commands `/signals`, `/record`. Subscriber cards never name books, research or the server.
- **Setups page feed (17 Nov 2026):** `engine15/setups.py`, called in `live.step()` after the page is written (guarded;
  log line `setups: 8 markets -> ...`). It writes `out/live/setups.json` and, when `MIND15_SETUPS_WEB_DIR` is set (the
  box: `/var/www/aitrading-m15`, in the unit's ReadWritePaths), the same bytes there, atomically, mode 0644. Schema 1:
  one entry per market from `b_targets` (side, entry, stop, targets, price, `rr_now_*`, `stop_dist_now_pct`,
  `entry_window_open`), the book record, the S1 followable record, learning hit rates. No push; the AI Trading Bot
  session serves it at /setups/setups.json behind the paywall (owner: "Included for paying members"). No display text
  may contain the word "edge" or the forecast model's name. The page is the site sessions' work.
  Since 17 Nov 13:48 UTC setups.json also has per-market `closes` (96 x 15m, ending at `price_bar_utc`) and top-level
  `closed_setups` (the book's last 30 closed trades, why_out codes TARGET_2/STOP/T1_THEN_ENTRY/FLIP/T1_THEN_FLIP/EXIT/
  T1_THEN_EXIT/OTHER), and a second file `setup_events.json` (last 100 S1 events from `data/signals_log.jsonl`, stable ids
  `<signal_id>:<type>`) is written beside it for alert senders.
- **Stock stances (17 Nov 2026, owner: "S&P model on each stock"):** `engine15/stocks.py`, hooked after setups in
  `live.step()`, runs when the S&P stepped (or the ticker list changed). Tickers from `/var/lib/aitrading-top5/top5.json`
  (env `MIND15_TOP5_FILE`; the website's single source of truth; fallbacks: last list, env `MIND15_STOCKS`, default five).
  Readings from each stock's Yahoo bars (`data/stocks/`) with the engine's own card code, market-wide cards copied from the
  S&P entry, mixed with the S&P call's own trust and refit voices (read only). Writes `stocks.json` (out/live + web dir);
  every stance is logged (`data/stocks_log.jsonl`) and graded with `labels.triple_barrier` (26 bars). Labelled "S&P 500
  model applied to single stocks; not validated on single stocks". No positions, stops or sizing.
- **Research Python on the box (17 Nov 2026, owner approved):** `/data/venv-research` = scikit-learn 1.9.1, scipy 1.18.1,
  joblib, threadpoolctl, narwhals (installed `--no-deps`), and every engine package through a `.pth` pointing at
  `/data/venv` (numpy 2.4.5 shared). Research scripts that need sklearn/scipy run with it. Never install into `/data/venv`:
  numpy/pandas versions are part of the reading cache's signature (a change = 20-minute rebuild).
- **VIP vault feed (18 Nov 2026, owner's exception to paper-only, docs/CHARTER.md):** `engine15/vault_feed.py`, hooked after
  setups in `live.step()`, OFF unless `MIND15_VAULT_CONFIG=/etc/ait-engine/engine.json` is set in `mind15.env`. The installer
  (AI Trading Bot session) owns `/etc/ait-engine` (root:mind15 0750; engine.secret = 64 hex -> bytes.fromhex; engine.crt/key
  + vault_ca.pem for mTLS). Calls `https://127.0.0.1:8443/v1/<op>` with mTLS + HMAC (caller "engine"), as the vault's
  VaultClient. Sends the BTC/ETH setups book (`submit_book`, as_of = price_bar_utc, once per bar, incl. after T1 with
  stop == entry) and exit-only intents (reduce 0.5 + futures move_stop at Target 1, close at the book's exit; never
  `open`). State `data/vault_feed_state.json` (hourly copies in `data/state_copies/`, `docs/RESTORE.md`). **The vault is LIVE on real
  accounts**: the feed's exit guard dates from 18 Nov ("the vault live"), and on 20 Nov 2026 the AI Trading Bot session
  reported that it sizes each setup at 2% of a member's USD-M futures balance. The vault itself belongs to that session. The Telegram unit cannot read /etc/ait-engine. VIP member: `helix2d`.
- **B trail book (18 Nov 2026, owner's request):** `research/b_trail_history.py` replayed `b_trail` and the main rule with
  today's engine from 2020 to each group's live start (`research/out/b_trail_history/trades.csv`, `summary.json`, also on
  the box). `engine15/book_view.py` (guarded hook after the setups/vault/stocks hooks) writes `b_trail_book.json` every
  step (history totals, yearly rows, monthly curve labelled "history replay with today's engine, in-sample, not a test",
  plus the live record since 11 Nov and a combined curve) and `b_trail_history_trades.json` (web dir only, when the CSV
  is newer). History: B trail -$47,444 (11,420 trades) vs main +$187,617 on the same span.
- **Hourly copies of the engine's memory (20 Nov 2026):** timer `mind15-state-copy` (minute 8) runs
  `tools/server/state_copies.py copy` as `mind15`: `vault_feed_state.json`, `shadow_state.json`, `live_state.json` and
  `signals_state.json` into `data/state_copies/<stamp>/` with a manifest, 48 kept. Restore with the same tool
  (`docs/RESTORE.md`); it refuses while the engine runs. If the feed's memory is lost while a setup is open the feed
  logs `vault: ALARM ...` every step and the Telegram bot sends "feed memory lost" (it used to adopt silently).
  `bash tools/server/check_drift.sh` (laptop, read-only) compares the box with `tools/server/`.
- **Backups (17 Nov 2026):** `tools/backup_pull.py`, Windows scheduled task "Mind15 server backup" daily 12:00 SGT:
  one tar over ssh of journal, out/live, data (no evcache/raw), RL forward books and logs into `backup/server/`
  (git-ignored), 7 kept, taken in a gap between steps, rejected if a bar or state file is empty.
- **Sources**: every step calls each source module's `update()` (`engine15/sources/__init__.py` MODULES). `flows`
  (v5.1.1) throttles itself per source (`MIN_GAP_S`; last attempts in `data/sources/flows_state.json`) and keeps the
  Binance archive zips in `data/raw/binance_metrics/`. `cryptox` (v5.2.2) throttles each of its six feeds the same
  way and extends `options_hist`'s Deribit aggregates live (`options_hist` itself is not in MODULES).
- **Version history**: a git repository with a private GitHub remote, `origin` = github.com/qyhong/engine-15m- (branch
  `main`, first pushed 20 Nov 2026). `tools/deploy.sh` deploys only a commit that is on `origin/main`. Large data, caches,
  models and live outputs are ignored (`.gitignore`); commit code and docs after a change.
- **Web answers**: `inbox.pull()` runs the AI Trading Bot's `pull_answers.py` before each step; answers are
  recorded per FORMAT.md (audit trail `data/owner_audit.jsonl`). The PIN lives only on the server.
- **Stale-page alarm**: the AI Trading Bot session adds Mind 15 to its S328 alarm (Telegram), built OFF,
  switched on with the owner's word.

## Page
The live page is the AI Trading Bot's `aitrading-pages/pages/mind15/index.html`; `web/mind15/index.html`
here is our copy. Build page changes on the live copy (the answer form lives in it), send md5 + diff
summary to the AI Trading Bot session; never deploy yourself. Rules: one `fetch("./page.json")`, no new
hosts/scripts/fonts, no innerHTML, the word Kronos never appears (export.py replaces it).

## Memory
8 GB laptop. Old live step: `backtest.prepare` over all history every 15 minutes, about 5-6 GB per step
(crypto). **Lean step** (`ENGINE15_LEAN=1` before `py -3 -m engine15 live`; off by default until the owner's
session switches it on): `engine15/evcache.py` keeps each group's readings on disk in
`data/evcache/<group>/` (memory maps). Since 17 Nov 2026 (layout 2) the feature matrix X is NOT stored: it is rebuilt row by row from the stored reading columns, and every write checks bit for bit that the store gives back the matrix (a mismatch = StoreError, the step falls back to the full prepare and says so). Before that X.bin was a third of the store (15 GB at v5.2.4). Each step logs `timing <group>: ...` and `timing step: ...` lines (where the time went). **Incident 19 Nov 2026 00:04-00:48 UTC:** the crypto daily check rewrote ~130k scattered runs one `write()` (and
flush of every file) at a time: ~292 GB written, the step hung in disk-wait. Fixed the same day (`AssetStore.write_rows`:
one write and one flush per piece) with a budget (`CHECK_MAX_BYTES` 2 GB, `CHECK_MAX_SECONDS` 300 per asset: the check
stops for the day with one log line, the step carries on). If a step ever hangs: `tail live.log`, `ps -C python`, a worker
in state D with huge `/proc/<pid>/io` write_bytes = this kind of runaway; stop the service, set that group's
`checked_day` in `data/evcache/<group>/group.json` to today, start it.
Guards against a long delay since 19 Nov (owner: "put a guard measure in place so the data no delay"): (1) the daily
check's budget (2 GB / 300 s per asset); (2) `ENGINE15_PARALLEL_TIMEOUT=1500` in `mind15.env`: a market group's worker
that thinks (or waits its turn) longer than 25 minutes is stopped and logged as STEP FAILED, the other groups still
publish (a full rebuild after a deploy takes up to ~16 min, inside it); (3) the root watchdog timer
`mind15-watchdog.timer` (every 5 min; `tools/server/mind15_watchdog.sh`, `--undo`): no engine log line for 30 min ->
restart the service, at most once per 45 min, logged in live.log; (4) the Telegram bot's 40-minute stale warning and the
AI Trading Bot's hourly outside alarm. **Parallel step (17 Nov 2026 08:05 UTC, owner approved):** `ENGINE15_PARALLEL=4` in `mind15.env` runs each group's bars + readings + refits in its own worker process (`engine15/parallel.py`, fork + pipes); decisions, shadow books, journal, state and page stay one group at a time in config order (crypto must stay first), so every file is byte-identical to the sequential step (proved on synthetic data and on real fx + index data; tests `tests/test_parallel_step.py`, also run on the box). Steps went from about 243 s to about 145 s. A worker that fails or hangs = that group's `STEP FAILED` line, others continue; a failure of the machinery falls back to the old path for that step. Non-crypto groups that lack their due bar retry for up to `ENGINE15_PARALLEL_BAR_WAIT` (75) seconds. Switch off: remove the env line and restart between steps. Gold, silver and oil step one bar behind in either mode (their feed is about ten minutes late; `fill_delay` 1). `engine15/leanprep.py` caches the
weekly refits in `data/evcache/<group>/fits/`. A step computes only new rows plus a 30-day refresh, and runs
a full check of the learning rows once a UTC day. Peaks: crypto about 1.3 GB per step and 1.5 GB on the
daily check, metals 1.1 GB. A first build after a code or config change rebuilds the store in pieces: crypto
about 4.5 minutes at about 1.1 GB. Any change to evidence/levels/indicators/sources/econ/owner/data/
extdata/livefeeds/calhistory/evcache or CFG rebuilds the store automatically. A failure in the lean path
falls back to the full prepare and logs it. Identical outputs proven bar by bar against the old code: tests
in `tests/test_lean.py`, and a frozen-input proof for every group. Run heavy jobs (history studies, model
fits) one at a time, one market group at a time; never load `out/replay/store.pkl` (1.9 GB, the old v4
crypto replay).

## RL forward paper books (NOT passed)
- `engine15/playbook5.py` (`p5_rlq`, Phase 4 primary) and `engine15/playbook6.py` (`p6_mtrend` Phase 6 primary,
  `p6_p4trend` its control, go-live 2026-11-13 03:00 UTC) run inside the live step via `reports.PLAYBOOK_MODULES`. Records:
  `research/out/rl/forward5/`, `research/out/rl/forward6/decisions_<book>_<asset>.jsonl` (append-only; never edit).
- Weekly refits are separate below-normal processes started by the step: `py -3 -m engine15.rl phase5-update`
  (models5/live) and `phase6-update` (models6/live, Phase 6 only; the control reuses models5). One shared lock
  (`research/out/rl/forward5/update.lock`): never two at once, Phase 5's first; each needs >= 1,500 MB free.
  Logs: `research/out/rl/forward5/update.log`, `research/out/rl/forward6/update.log`.
- `engine15/playbook7.py` (`p7_rvbear`, H37 V4 BTC/ETH pair book, go-live 2026-11-13 11:30 UTC): no model and no refit;
  it recomputes from bars and funding each step (tests: `tests/test_playbook7.py`).
- The RL loop (`research/rl_loop/`) is ON HOLD after round 4 (put on hold by the owner on 14 Nov 2026 after round 3;
  round 4 ran on 17 Nov at the owner's request: no pass, no round 5 proposed); notes in `loop_state.json`.
- RL health readings (21 Nov 2026; they decide nothing): each RL book's page state carries `split` (the gross result
  by who held the exposure: seeds on their model / seeds on the 'do no harm' fallback; costs are the whole book's)
  and `input_drift` (from the `dz` field each new decision record carries: the share of the model's inputs more than
  3 training standard deviations from their training mean). Code: `engine15/rl/forward5.py` (`agent_split`,
  `input_drift`, `drift_view`). The Telegram bot sends one card when no seed agent trades a coin, one weekly card
  when a new model is in use, and answers `/rl` (`telegram_notify.rl_fallback_update`, `rl_weekly_update`).
- Paper desk (22 Nov 2026, owner "Study first, then paper desk"): `engine15/paper_desk.py`, called by
  `reports.scoreboard` inside a try/except. Three forward paper wallets (2% rule, 100% per coin, 3x book) on the Setups
  book's BTC and ETH trades from `paper_desk.START_UTC` (23 Nov 2026 00:00 UTC). It keeps NO state: every step it
  reads the book's closed-trade files, `data/shadow_state.json`, the tail of the two bar files and the funding files
  and walks them again (H63's rules; `tests/test_paper_desk.py` holds its walk to H63's numbers). Its output is the
  `paper_desk` block of `out/live/scoreboard.json`. To restart the desk from a new date, change START_UTC.
- Book allocator `a_alloc` (24 Nov 2026, H110, RL idea R2; owner "Ok lets do it"; paper only, NOT passed):
  `engine15/book_alloc.py`, called by `reports.scoreboard(playbook_rows)` inside a try/except after the paper desk.
  One paper wallet of $10,000 from `book_alloc.START_UTC` (25 Nov 2026 00:00 UTC), split each UTC day between the 37
  books of `book_alloc.BOOKS` (the main books, 17 shadow books, 19 strategy books; a book added later is NOT in until
  the hypothesis is amended, it shows under `books_not_registered`). Exponential weights on each book's daily result
  (`ETA` 7.0), cap 25%, floor half the equal share until 30 closed trades; yardstick = the same books held equally.
  A daily result is CLOSED trades only, booked on the close day, over $10,000 x the book's markets: open trades are
  not marked. It keeps NO state: every step it reads `out/live/trades_*.csv`, `shadow_trades_*.csv` and the step's
  strategy rows and recomputes every day from the start (about 7 ms on today's files, 75 ms on a planted year). A
  book whose file cannot be read is left out of that step (`books_left_out`), never an error; any other failure is
  one log line `book allocator: ...` and the scoreboard is written without the block. Output: the `a_alloc` block of
  `out/live/scoreboard.json` (today's shares, both wallets, daily rows, the reads at 30 and 60 completed days). It
  changes no book and no decision; the constants are in the module, not in `CFG`. Tests: `tests/test_book_alloc.py`.
- Exit learner `b_learn` (24 Nov 2026, H109, owner "Ok lets do it"; paper only, NOT passed): `engine15/learn_book.py`,
  called by `reports.scoreboard` inside a try/except, before the shadow rows are read. Arms: `b_targets`, `main` (the
  hold copy), `b_trail`, `b_be_t1`, `b_ema20_1h_t1`, `b_sma20_1h_t1`, on BTC and ETH. It keeps NO state: every step it
  reads the arms' `shadow_trades_<arm>_<coin>.csv`, `data/shadow_state.json` (open trades) and the tail of the two bar
  files (from 40 days before the arms' first trade), recomputes the whole book from `learn_book.START_UTC` (25 Nov 2026
  00:00 UTC) and rewrites `out/live/shadow_trades_b_learn_<coin>.csv` only when it changed; that file is what puts it
  on the scoreboard (title in `reports.SHADOW_TITLES`). The `exit_learner` block of `scoreboard.json` holds the four
  tables (scores, weights, leader), whom each coin follows, the arms over the same days and what was left out. If a
  bar file or the state cannot be read at a step, the block says so and the record on file is left as it was. A
  failure logs one line, `exit learner: ...`, and the scoreboard goes on. Constants are in the module (none in `CFG`);
  they are H109's and are not to be tuned. To read it by hand: `py -3 -m engine15.learn_book` (prints the block, writes
  nothing). Measured cost: about 0.03 s a step now, 0.23 s with a year of records. Tests: `tests/test_learn_book.py`.
- Capitulation-long books `p9_rebound_a` / `p9_rebound_b` (24 Nov 2026, H115; owner: "build the paper
  capitulation-long book with the Telegram alert"; paper only, NOT passed; NOT deployed when this was written):
  `engine15/playbook9.py`, in `reports.PLAYBOOK_MODULES`, so it runs with the strategy books after the groups fetched
  their bars. H107's rule A and rule B on BTC and ETH (a fresh 30-day low, 10% under a week earlier, a 2 x ATR(1h)
  rebound; rule B also needs negative funding; stop 3 x ATR(1h), half out at Target 1 then the stop at the entry, the
  rest at Target 2 or at the close 48 hours after the signal), $10,000 a trade, 1x, 0.10% a side. History does not
  support it (rule A flat over 123 trades, rule B 32 trades): it runs because the owner asked.
  UNLIKE the other new paper books IT KEEPS STATE: `data/capit_long_state.json` (written atomically: the last bar seen
  per coin, the waiting and open trades with their fixed levels, the closed trades, the alerts). A decision is made
  once, by the step that first sees the bar. The record starts at the first step after the deploy (`started_utc` in
  the file; never before `playbook9.REGISTERED`). A missing or unreadable file means the book starts flat again from
  that step: one log line, the unreadable file kept as `capit_long_state.json.bad-<unix time>`, and the record made
  so far is no longer on the page or the scoreboard. The daily laptop backup holds `data/`; the hourly
  `tools/server/state_copies.py` does NOT list this file. Each step reads the tail of the two bar files (45 days plus
  the bars not seen yet) and the two funding files; rule B fires only on a rate set at most 9 hours before the
  deciding close (`FUND_MAX_AGE_MS`), else one line `playbook9 <coin>: rule A fired ... rule B does not fire`. It logs
  only on events (a signal, a fill, a close, a state problem), every line starting `playbook9`. A failure is one line
  and the step goes on. Measured on the laptop on the real files: 12 ms a step with no new bar, 26 ms with a new bar
  on both coins, 34 ms to catch up five days. Page: block `playbook.playbook9` (`not_passed: true`, per-coin readings
  under `coins`: how far each coin is from a signal). `a_alloc` lists both books under `books_not_registered`
  (H110 fixed its 37 books). To read it by hand: `py -3 -m engine15.playbook9` (prints the state file, writes nothing).
  THE REBOUND SIGNAL FILE (25 Nov 2026, for the VIP vault's dry run only): the live step also rewrites
  `out/live/rebound_signal.json` (schema 1): per coin, `p9_rebound_a`'s trade as `state` none / waiting / open, its `id`
  (`<coin>.<trigger close>.rebound`), `decided_utc`, `entry_utc`, the levels (`*_est` while waiting), `time_exit_utc`,
  `rule_b_too`, and `last_closed`. Older than 30 minutes = unknown. A failed write is one line; the trades go on.
  `data/capit_long_state.json` is in the hourly state copies since the same day (docs/RESTORE.md).
  THE ALERT: `telegram_notify.capit_check`, in the bot's own process (`mind15-telegram`; restart it after a deploy so
  it loads the new code). It reads the state file (never imports the book) and sends, to the owner's locked chat only,
  one card per coin and deciding close at which a rule opened a paper trade (rule(s), entry, stop, Target 1 and 2, the
  48-hour exit time, risk %, funding, "Paper only, NOT passed" with the history line; a card sent more than 30 minutes
  after the close says "Late") and one card when a coin's trades close (R per rule). Delivered ids are in the bot's
  state under `capit_alerted`; a failed send is retried at the next check; nothing older than 48 hours is sent. These
  books' closes do not also get the generic closed-trade card (their ids start with `p9_`, which is in
  `telegram_notify.QUIET`); 30 trades and a verdict change alert as for any book. Tests: `tests/test_playbook9.py`
  (parity with `research/h107_capitulation_rebound.py` trade for trade on the real files, no look-ahead, forward
  only, stale funding, state and restart, the cards).
- Back at a capitulation low: the retest levels and their two Telegram notices (24 Nov 2026; the owner chose "a plain
  Telegram notice when price enters the zone"; a NOTICE built from H116's descriptive base rates, NOT a setup, not a
  hypothesis, no trade; NOT deployed when this was written). `playbook9.levels_of` is H116's level machine (the low
  behind a rule A trigger; dead if undercut before a 5% bounce; armed; first touch = a 15m low within 1.5% above the
  low; and, new here, broken = a low under it from the first touch on; a level counts for 30 days). The levels are NOT
  kept from triggers seen live: at every new bar `playbook9._step_levels` recomputes them from the last 93 days of
  closed bars (`LEVEL_TAIL_DAYS`, the comment there says why 93), after the trades and in its own try/except, and
  writes them under the key `zone` of `data/capit_long_state.json` beside the trades (the trades' keys, the rows and
  the books are untouched; an old state file without `zone` simply gets it). A level is listed for its 30 days and 2
  more. Log: one line per change of state, `playbook9 <coin>: the <low> low of <time> UTC is <state> ... A notice
  only, no trade` (at the first step after a deploy, one line per level listed); a failure is one line, `playbook9
  <coin>: the retest levels were not updated (...); the trades are not affected`. Page: `levels` (per coin: L, low_utc,
  made_utc, zone_top, state, live, live_until_utc, touch_utc, broken_utc, new_low) and `levels_note` in each of the two
  book blocks; the web tab does not show them yet. Cost on the laptop on the real files: a step with a new bar on both
  coins went from about 10 ms to about 38 ms (a second, longer tail read per coin); a step with no new bar reads
  nothing more. THE NOTICES: `telegram_notify.zone_check`, called in `check()` right after `capit_check`, with its
  own guard (a failure prints `capitulation-low notices failed (...)` once). It reads the same state file and sends,
  to the owner's locked chat only: the zone notice at a level's first touch (the low, its date, the zone, the price,
  "A notice, NOT a setup", the base rates, what the long would need) and the break notice when a touched level gets a
  15m low under it (the new low so far, the close rule A needs now, whether its other two conditions hold at the last
  close). Each once per level (bot state key `zone_alerted`, `z|<id>` and `x|<id>`; the id is the trigger's, as in
  `capit_alerted`); a failed send is retried; nothing older than 48 hours is sent; a level first seen already broken
  gets the break notice only. Restart `mind15-telegram` after the deploy. Tests: `tests/test_capit_zone.py` (the rules
  on made-up bars and the parity with `research/h116_retest_capitulation_low.py` on the real files at 338 BTC and 460
  ETH test dates; no look-ahead; the two texts; delivery).
- "Setups moving against" alert (22 Nov 2026, owner asked for it): `telegram_notify.adverse_update`, hooked into
  `check()` in its own try/except. It reads the page's `b_targets` book and the market closes; its state is the key
  `adverse` in the bot's state (per market: trade id, entry, starting stop, flags a, b and t1). Thresholds
  `ADVERSE_A_R` (0.5) and `ADVERSE_B_R` (0.75) in `telegram_notify.py`. If it fails the bot log shows "setups adverse
  check failed". On the first start after a deploy, open trades already past a threshold get their card at once.
- Momentum yardstick (22 Nov 2026, owner "Run all above"): `engine15/playbook8.py` (`p8_mom`, from 2026-11-23 00:00
  UTC) runs in `reports.PLAYBOOK_MODULES` after `playbook6`. Record: `research/out/rl/forward8/decisions_p8_mom_<asset>.jsonl`
  (append-only; never edit). No model and no refit: a stand-in model with every seed on the fallback, through
  `forward5.advance(fallback="trend")`. Interim read: `research/rl_interim_read.py` prints nothing before 2027-01-07
  04:30 (`p5_rlq`) and 2027-01-08 03:00 UTC (Phase 6); run it on the box, where the records are. Page block `rl_lab`
  (schema 1): `engine15/rl_lab.py`, called by `export.merge` in a try/except (null on failure); fields in `docs/RL.md`.
- Research job queue (22 Nov 2026). Long research computations run on the Singapore box from `/data/research_queue/`,
  worked through by `research/queue/runner.py` (pid in `runner.pid`; log in `runner.log`). At most 2 jobs at a time, at
  nice 19 and ionice idle, single-threaded. It starts nothing new when free disk on `/data` is under 4 GB, available
  memory is under 3 GB, PAUSE exists, or the engine was deployed less than 45 minutes ago; it stops jobs (they resume
  later) when disk is under 2 GB, memory under 1.5 GB, or STOP exists. Jobs are resumable harnesses
  (`research/queue/placebo.py`, `walkforward.py`, `pattern.py`) run from code snapshots in `code/<commit>/`, which read
  `/data/mind15/data` through a symlink and never write there. From the laptop: `py -3 -X utf8 tools/research_queue.py
  status` (the backlog in hours), `snapshot`, `add`, `fetch`, `logs`, `start`, `stop`, `pause`, `resume`. NOT a systemd
  service: after a reboot run `tools/research_queue.py start`. To stop everything at once:
  `touch /data/research_queue/STOP`. `walkforward.py --study H101` needs the choice files of H90 to H100 and must be
  queued after they are done. Details in `research/queue/README.md`.
  The box is a t2.xlarge (burstable CPU credits): never run two queue jobs at once there (owner, 23 Nov 2026:
  sequential, no T2 Unlimited). Start it with `tools/research_queue.py start --workers 1`. If the engine's step time
  (`grep "timing step" /data/mind15/live.log`) climbs well above 3 minutes, `touch /data/research_queue/STOP` first.
  Since 23 Nov 2026 the runner also pauses its job (SIGSTOP) from 45 s before each 15-minute close until the engine has
  written its page for that close (at most 14 minutes), then continues it (`engine_busy` in `runner.py`; `--no-yield`
  turns it off). One job without this pause still made a step take 391 s.
- Give-back alert (21 Nov 2026, owner "Yes"): `telegram_notify.giveback_update` sends one card when an open
  main-book trade is 25% or more below the best open profit the bot has seen for it (state key `giveback`). Alert only.

## Exits study H36 (13 Nov 2026)
- `research/exit_study.py --group <g>` (one group at a time, ~1-5 min each, peak well under 1.5 GB; reads
  `data/evcache` READ-ONLY and keeps its own refits in `research/out/exits/fits/`, never the live fits dir, because
  `leanprep.walk_forward_cached` deletes fits it did not use) then `--report`. Uses `research/out/heavy_job.lock`
  (shared with the RL loop agent), below-normal priority, waits for 1,500 MB free.
- Result: all 15 variants lose to holding (`research/out/exits/trail_study.md`). Shadow books `b_be_t1`,
  `b_ema20_1h_t1`, `b_sma20_1h_t1` start flat at the next live-loop restart (no state reset: `advance` adds them and
  records `late_starts` so the scoreboard compares them with main over their own time only). Open-trade view:
  `trail_price`, `trail_basis` ("EMA20 on 1h"), `trail_arm`, `trail_armed`, `stop_basis`.
- Shared exit code for a possible v5.2: `engine15/exits.py`; the switch checklist is in the study's last section.
- **Live since think15-v5.2.5 (19 Nov 2026), USDJPY's main book only:** the stop moves to the entry once Target 1
  trades. Where: `CFG["be_t1"] = ("USDJPY",)`; `live.asset_cfg` turns it into `be_t1=True` for that market (the
  raw CFG holds the list, and `run_book` acts only on exactly `True` plus a `t1_of` planner, so the replay and every
  other caller are unchanged); `backtest.run_book` keeps `t1`, `t1_hit`, `stop0` in the book's state;
  `live.adopt_be_t1` brings a trade that was already open under the rule (Target 1 traded since entry -> the stop
  goes to the entry from the next bar; nothing is back-dated and no switch exit is made, a narrower migration than
  the study's checklist item 3). The open-trade view gains `stop_basis`. The shadow books are NOT changed: their
  `main` copy keeps hold-to-stop-or-flip on every market, so on USDJPY it is now the old rule's forward record.
  Tests: `tests/test_be_t1.py`. To undo: empty the tuple and bump the version (an open trade keeps the stop it has).
- **Live since think15-v5.2.6 (20 Nov 2026), the S&P 500's main book only:** half at Target 1, then the rule above
  on the rest. `CFG["half_t1"] = ("SPX",)` (a market there must be in `be_t1` too); `run_book` closes
  `exits.PART` at Target 1 in the bar that reaches it, keeps the closed half in `state["part"]` (pnl, fees, q, qpx,
  tag) and books it as a closed trade AT ONCE (its own row in `trades_SPX.csv`, `why_out` `T1`; owner: "It should
  reflect on the close trade also"); the rest is a second row when it closes (`STOP_BE`, `FLIP`...). The two rows
  share `time_in` and `side`; `reports.per_entry` counts them as one trade on the scoreboard. A trade already past
  Target 1 when the rule began: `live.adopt_be_t1(..., half=True)` sets `half_due`, and the half is closed at the
  next bar's open (`T1_LATE`). Journal: `half_closed`; open-trade view: `t1_half*`. Tests: `tests/test_half_t1.py`.

## The trail voice (26 Nov 2026; ON for BTC and ETH since think15-v5.2.12, 27 Nov 2026 08:40 UTC)
The owner decided the Setups page, the signals and the VIP vault move to a trailing-stop book ("Page and VIP").
Plan, contract and order: `docs/TRAIL_SWITCH_PLAN.md`; the forward read: H119.
- The book: `b_trail_setups` in `shadows.CHALLENGERS` (`{"trail": True, "early": True}`), starts flat at its deploy.
- Which book speaks for a market: `engine15/setups_voice.py` (`TRAIL_MARKETS`, state `data/setups_voice_state.json`,
  `published()` is the one rule). `setups.write` moves the state; `signals.py` and the adverse alert read it.
- The vault: `vault_feed.SEND_TRAIL` (the trail body, `move_stop` per step when tighter, `close`; never `reduce`).
- The dry run: `engine15/trail_preview.py` writes `out/live/trail_book_preview.json` every step while `SEND_TRAIL` is
  off (so not since v5.2.12). It posts nothing and keeps its own memory inside that file.
- Live since v5.2.12: `TRAIL_MARKETS = ("BTCUSDT", "ETHUSDT")`, `SEND_TRAIL = True`. BTC changed over at 15:15 UTC on
  27 Nov (its first trail setup: SHORT 16:45, entry 60,298.01, stop 62,126.09, both VIP members joined); ETH changes
  over when its targets short of 25 Nov 19:30 ends. Tests run with both switches off (`tests/conftest.py`); the
  shipped values are read by `tests/shipped_values.py`.
- Tests: `test_setups_voice.py`, `test_setups_trail.py`, `test_signals_trail.py`, `test_vault_trail.py`,
  `test_trail_preview.py`, `test_money_path_trail_golden.py` (the frozen record of the trail voice).
- To take a coin off (owner's word): remove it from `setups_voice.TRAIL_MARKETS`, bump the version, update the two
  "shipped switches" tests, deploy with `tools/deploy.sh`. It changes back by itself when its open trail setup ends.
  `SEND_TRAIL` goes off only once no vault market is on the trail voice, and before any vault rollback below f7609091.

## Price feed watch (28 Nov 2026)
- `engine15/feed_watch.py`: a market is stale when three 15-minute bars are due and missing while its whole group is
  open (market_calendar hours, holidays and early closes; WTI waits for Brent). Weekends and breaks never count.
- setups.json: `bar_age_min` and `stale` per market (setups.py). The website can show a badge from `stale`.
- Telegram (`telegram_notify.feed_stale_update`, on the box, every minute): "Prices stopped" once, "Prices back" once.
- `tools/trail_check.py` (laptop, read only): the trail side of BTC and ETH: voice, setup, every move_stop made for it
  and its status, the stop-moved cards; PROBLEM on a refused move or a Setups stop tighter than the last one sent.
- The laptop's `tools/price_check.py` (scheduled `mind15-price-check`, every 8 h, only while the app is open) still runs
  and also compares prices with an outside quote.
- Backup bars: `engine15/bridge.py` (gold, silver, WTI, Brent; see `docs/FEED_PLAN.md` for the other two and a
  permanent replacement).

## H122 commodity cards (28 Nov 2026; paper only, NOT passed)
- Registration and rules: research/HYPOTHESES.md H122 (and its code note). Owner: "Yes, build all six" (separate paper
  test, the switch calendar first). Built: C1 release impulse, C2 leader lag, C5 time-of-week drift. To build: C3 weekly
  reopen gap, C4 fix and settlement fade, C6 curve momentum (oil).
- `engine15/cards6.py`: the votes (pure functions) and the mind mixing; `engine15/cards6_books.py`: the five books as
  `shadows.MINDS` entries (card books first, then m_cards6 / m_cards6_nf); kill state in `sst["cards6"]`
  (`data/shadow_state.json`). Metals and energy groups only.
- `engine15/rolls.py`: contract switches seen (CL, BZ 18 Nov; GC, SI 25 Nov 2026) and forecast by rule (next: ES 10 Dec,
  CL and BZ 17 Dec). Add each switch seen to `SEEN`. The stored bars carry the past switches' steps unadjusted (the
  owner chose to leave history as it is, 28 Nov).
- Tests: `tests/test_cards6.py`, `tests/test_rolls.py`.

## Chinese maps for the website (28 Nov 2026)

Owner: "Ensure all other locale in the website are fully translate", then "Automatic" and "Translate them" (headlines too).
Every label on the site was already in 繁中/简中; what stayed English was the text inside the data files.
`engine15/zh.py` (self-contained: copy it unchanged to other jobs) writes `X.zh.json` beside a data file:
`{"schema": 1, "generated_utc", "source_md5", "strings", "translated", "zh-TW": {english: chinese}, "zh-CN": {...}}`.
Strings are cut at "; " and " · ", numbers are masked ("lead of [[0]] pts"), each pattern is translated once by Claude
(`claude-opus-5-5`, effort low, server-side fallbacks, JSON schema output) and kept in a cache (`data/zh_cache.json`).
Checks: every [[n]] kept, Chinese present, no banned word. Limits: 600 new patterns a run, 400k output tokens a UTC day.
Keys use the brand in place of the model's old name (the Mind 15 page renames it before reading page.json).
`engine15/zh_live.py` runs after each step as its own process (`live.start_zh`, never waited for) and only when the key
file exists: `/etc/mind15/anthropic.key` (owner places it, root:mind15 0640; read at run time, never printed). It writes
page/setups/stocks/b_trail_book/landing `.zh.json` in out/live, copies the four Setups-side ones into
MIND15_SETUPS_WEB_DIR, and pushes `page.zh.json` with `push.push_file` (fixed names in `push.EXTRA`). Log: out/live/zh.log.
Needs the `anthropic` package in /data/venv. The pages read the maps on branch `zh-data-maps` of the page repo (the AI
Trading Bot session merges and deploys); nginx needs the new names served beside their files.

## Open items
See the task tables and the dated status notes at the end of `docs/CHARTER.md`.
- **Bars note (15 Nov 2026):** `data.load("BTCUSDT"/"ETHUSDT")` returns Binance SPOT 15m bars (the stored bar matches the
  spot kline exactly); funding comes from the USD-M perpetual. The perpetual's own klines are fetched by
  `sources/cryptox.py` for the spot-vs-perp card.
