# Mind 15: where things stand (updated 21 Nov 2026: think15-v5.2.8; the vault feed is on the REAL-MONEY path)

Main-book exit rules by market (config.py `be_t1`, `half_t1`, `t2_exit`, `trail_stop`, `trail_wait_signal`): USDJPY
sells half at Target 1 and the rest at Target 2 with the stop to the entry after Target 1 (v5.2.7); the S&P 500 sells
half at Target 1 and lets the rest run with its stop at the entry (v5.2.6); the other six (BTC, ETH, gold, silver,
WTI, Brent) trail their stop once a trade is 1R in profit (the tighter of the last confirmed 15m swing and 2 x
ATR(15m), never looser; exit word `TRAIL`) and, after a trail exit, stay flat until one side clears the entry bar:
no forced entry (v5.2.8, owner 21 Nov 2026). Everywhere else the 4-session mandate is unchanged, including after an
exit at the entry stop or on a flip. The vault copies the Setups book (`b_targets`), which v5.2.8 does not touch. H60 (exits by regime, per market) is registered and running; it may change this table.

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
- The RL loop (`research/rl_loop/`) is ON HOLD after round 3 (owner, 14 Nov 2026); proposals in `loop_state.json`.

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

## Open items
See the task tables and the dated status notes at the end of `docs/CHARTER.md`.
- **Bars note (15 Nov 2026):** `data.load("BTCUSDT"/"ETHUSDT")` returns Binance SPOT 15m bars (the stored bar matches the
  spot kline exactly); funding comes from the USD-M perpetual. The perpetual's own klines are fetched by
  `sources/cryptox.py` for the spot-vs-perp card.
