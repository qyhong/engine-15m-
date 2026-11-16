# Mind 15: where things stand (updated 16 Nov 2026: think15-v5.2.2, trust cap, card pipeline, breakout studies)

Read `docs/CHARTER.md` first (purpose, every task and status, the owner's decisions), then
`THOUGHT_PROCESS.md` ("Now" section) and `CLAUDE.md`. This file is only the moving parts.

## Running
- **Live loop**: terminal tab "Mind 15 live loop",
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
  Deploying code: commit on the laptop, `git archive HEAD | ssh ... "tar xf - -C /data/mind15"`, then
  `sudo systemctl restart mind15` between steps (right after a "step done" line). Research runs on the box too
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
- **Sources**: every step calls each source module's `update()` (`engine15/sources/__init__.py` MODULES). `flows`
  (v5.1.1) throttles itself per source (`MIN_GAP_S`; last attempts in `data/sources/flows_state.json`) and keeps the
  Binance archive zips in `data/raw/binance_metrics/`. `cryptox` (v5.2.2) throttles each of its six feeds the same
  way and extends `options_hist`'s Deribit aggregates live (`options_hist` itself is not in MODULES).
- **Version history**: this folder is a local git repository (no remote; nothing is pushed). Large data, caches,
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
session switches it on): `engine15/evcache.py` keeps each group's readings and X on disk in
`data/evcache/<group>/` (memory maps, about 11 GB for all five groups; pre-built 11 Nov ~16:10 UTC). `engine15/leanprep.py` caches the
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

## Open items
See the task tables and the dated status notes at the end of `docs/CHARTER.md`.
- **Bars note (15 Nov 2026):** `data.load("BTCUSDT"/"ETHUSDT")` returns Binance SPOT 15m bars (the stored bar matches the
  spot kline exactly); funding comes from the USD-M perpetual. The perpetual's own klines are fetched by
  `sources/cryptox.py` for the spot-vs-perp card.
