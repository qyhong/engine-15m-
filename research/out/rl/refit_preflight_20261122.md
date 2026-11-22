# RL weekly refit: preflight for the first server refit (Mon 23 Nov 2026)

Read-only check, done 22 Nov 2026 around 10:45-11:10 UTC. Nothing in the repo or on the server was changed, started or stopped. The three RL books (`p5_rlq`, `p6_mtrend`, `p6_p4trend`) are forward paper books that have NOT passed. Nothing below says they have an edge.

## (a) When it runs, and whether it blocks the step

- **Trigger.** It is not on a wall-clock timer. Every live step, `reports.playbooks` runs `playbook5.step` and then `playbook6.step`. Each one calls `forward5.maybe_launch_update` (Phase 6 goes through `forward6.maybe_launch_update`). A refit is due once the newest model's data end is before the latest Monday 00:00 UTC (`forward5.last_monday_ms` / `update_due`). Today the newest models end 16 Nov 02:45 (models5) and 16 Nov 03:15 (models6). So the refit becomes due with the first step after **Mon 23 Nov 00:00 UTC**. I checked on the server: `update_due` is False now and True at Mon 00:03.
- **Expected times (UTC, Monday 23 Nov):**
  - The step starts at about 00:01:15. The loop sleeps until the close plus 75 s.
  - The RL books are reached about 2 min 50 s after the close. The recorded `lag_s` is about 172 s, and the strategy-books part takes about 5.2 s of a step of about 90-115 s. So **Phase 5 is launched at about 00:03 UTC**. The Monday step may run a little longer, because the day change also starts the 1-day and 7-day surprise-mining jobs.
  - In that same step Phase 6 answers "waiting for the phase5 refit" and does not start.
  - **Phase 6 is launched by the next step, at about 00:18-00:19**, if Phase 5 has finished by then. If not, it starts one step later, at about 00:34.
- **Past durations (laptop, 16 Nov):** Phase 5 took 2.9 min (seeds 91 s, 46 s, 34 s). Phase 6 took 8.1 min (seeds 195 s, 165 s, 124 s). The 13 Nov Phase 6 refit had seeds of 115 s, 104 s and 179 s. Memory events: none. Sources: `forward5/last_update.json`, `forward6/last_update.json` and the `update.log` files. They are the same on the laptop and the server, because the server copies came from the laptop.
- **Expected on the server:** the server has 4 vCPU (Xeon E5-2686 v4, 2.3 GHz) and torch uses 2 threads. The RL live step costs about the same there as on the laptop (0.17 s and 0.27 s), so I expect roughly 3-8 min for Phase 5 and 8-20 min for Phase 6. That puts all three books on new models by about 00:35-00:55 UTC. This is an estimate: nothing has been timed on this box.
- **Does it block the step? No.** The step only does a free-memory read, writes `update_attempt.json` and calls `subprocess.Popen([sys.executable, "-m", "engine15.rl", "phase5-update"], ...)`, then returns at once ("launched"). The training runs in a separate child process with stdout and stderr going to `update.log`. Its niceness is 15, because `os.nice(5)` is called three times: in `rl/__main__.main`, in `update_cli` and in `train_model`. torch uses 2 threads. The setups write and the vault post come after the strategy books in `live.step`, and they do not wait for the child. The only cost to the step is CPU competition from a nice-15 process on 4 cores. I expect that to be small, but it is not measured.

## (b) Will it run? Probably yes, but this cannot be proven until it runs once

| Requirement | Server state (checked read-only) | Verdict |
|---|---|---|
| Python packages used by the refit: numpy, pandas, yaml, torch, gymnasium (`rl/env.py` imports it at top level via `pool4`) | numpy 2.4.5, pandas 3.0.3, PyYAML 6.0.3, torch 2.15.0+cpu, gymnasium 1.4.0. These are exactly the laptop's versions. stable_baselines3 and scipy are missing, but the refit path does not use them: they are imported only inside PPO functions in `agent.py` and `train.py`, which are never called. | yes |
| Modules import | `engine15.rl.forward5`, `forward6`, `models4`, `learn6`, `pool4`, `phase4`, `phase6`, `qagent`, `features4`, `engine15.evcache` and `engine15.rl.__main__` all import. `forward5.load_cfg()` and `forward6.load_cfg()` (with `check_frozen`) both load. | yes |
| Interpreter and paths | `sys.executable` = `/data/venv/bin/python`, ROOT = `/data/mind15`. All refit paths are relative to ROOT, and none is laptop-specific. The Windows paths inside the copied `last_update.json` and `update.log` are read by nothing except the Telegram bot's count of "model written" lines. | yes |
| Data it reads: `data/btcusdt_15m.csv`, `data/ethusdt_15m.csv`, the funding CSVs, the evidence store `data/evcache/crypto/{BTCUSDT,ETHUSDT}` | All present and fresh: bars updated 10:46, store files 10:47. The store has n = 276,445 and was built 2026-11-21T02:33Z. | yes |
| Folders it writes: `research/out/rl/phase5_cache/<stamp>`, `phase6_cache/<stamp>` (temporary), `models5/live`, `models6/live`, `forward5/` (lock, last_update.json), `forward6/` | All are under `/data/mind15/research/out`, which is in the unit's `ReadWritePaths`. The child inherits the unit's sandbox (`ProtectSystem=strict`). `rl/` is `ec2-user:mind15 775`; `forward5`, `models5/live` and `models6/live` are `mind15:mind15 2775`; UMask is 0002. No `update.lock` is present and no refit process is running. | yes |
| Memory (needs >= 1,500 MB MemAvailable to start; pauses under 400 MB) | 16 GB total, about 13,400 MB available (`free_mb()` read 13,363). The engine uses about 400 MB RSS. There is no swap. | yes |
| Disk | `/data` has 8.5 GB free (65% used). One refit's cache is a few hundred MB at most (my estimate) and is deleted on success. | yes |
| CPU | 4 vCPU. The engine's step uses 4 parallel groups for about 66 s of its about 100 s. | yes (slower than the laptop is possible) |
| Environment | The unit sets HOME, XDG_CACHE_HOME, MPLCONFIGDIR and PYTHONDONTWRITEBYTECODE (values not read), plus PrivateTmp. The refit reads no environment variable. The refit's process is a child of the engine, so it inherits these. | yes |
| The training run itself (pool4 cache build, q_fold or q_fold6 on torch, on Linux x86_64) | **Never executed on this box.** It was never run on x86 either: the laptop is ARM64 Windows. The RL tests have never run on the server. | **cannot tell** |

Overall: every precondition I could check is met. Whether the training completes is unproven until Monday 00:03.

## (c) Risks, ranked

1. **The training path has never run on Linux/x86.** The imports, config and data are fine, but `pool4.prepare`, `q_fold` and `q_fold6` have only ever run on the ARM64 laptop. Library versions are identical, which lowers the risk. If it fails, the traceback goes to `research/out/rl/forward5/update.log` (or `forward6/update.log`), the lock is removed in `finally`, and the launcher tries again every 30 min, indefinitely.
2. **A failure is silent, and repeated failures could fill `/data`.** Nothing alerts on a failed refit. The Telegram bot only sends "Weekly RL refit done (Phase N)" when a new "model written" line appears, and "RL weekly check · new models in use" when a book's model id changes. The page field `update` would just cycle through "launched", "running" and "waiting to retry". Also, `train_model` deletes its cache folder only after success. A failure that happens after caching leaves `research/out/rl/phase5_cache/<stamp>` (or `phase6_cache`) behind on every attempt, 48 times a day. I estimate a few hundred MB per attempt; I could not measure it, because no cache exists now. Against 8.5 GB free, that could fill `/data` in roughly a day. `/data` also holds the bar files, `data/shadow_state.json` and `data/vault_feed_state.json`, which are the money path's memory. **This is the consequence that matters most.**
3. **A restart of `mind15` while a refit runs kills it.** The unit uses `KillMode=control-group`. Today's deploy (11:30-11:55 UTC) is not affected. Any restart or deploy between Mon 00:00 and about 01:00 UTC would kill the refit. The next attempt cleans up the dead lock, because the PID is gone, and relaunches about 30 min later. A cache folder is left behind.
4. **A new model that is written but breaks the live decision has no automatic fallback.** `advance` uses the newest model whose data end is at or before each bar's close. If that model makes the step raise, for example through a column mismatch, the book logs "playbook5 BTCUSDT failed" every step and records no decisions. It never falls back to the older model. Recovery means moving the bad file out of `models5/live` or `models6/live` by hand. The likelihood is low, because the same code builds and reads the model.
5. **CPU competition at Monday 00:00.** The same day-change step spawns the 1-day and 7-day surprise-mining jobs (`reports.daily`), so the refit runs alongside them and the engine's step. The engine runs at nice 0 against the refit's nice 15, so it keeps priority. The refit may take longer than on the laptop. Low risk.
6. **Lock edge case.** If the refit is killed hard (OOM, SIGKILL), its lock survives. Until the engine reaps the zombie, `os.kill(pid, 0)` still reports the PID as alive, so the lock blocks for up to one step. The engine's next `subprocess` call, the ssh push, reaps it. The worst case is the 6-hour `stale_lock_hours`. Low risk, given about 13 GB free.
7. **Not a failure, but worth knowing:** x86 floating point differs from ARM64, so the weights will not be identical to what the laptop would have produced. "New model picked up" does not mean "BTC agents trade again". The 'do no harm' flags may stay True for BTC.

**Recommendations only, none done:**
- Do not deploy or restart `mind15` between Mon 00:00 and about 01:00 UTC.
- Have someone run the checklist at about 00:45-01:00 UTC. If `update.log` shows a Traceback, stop the retry loop, or at least watch `df -h /data`, until it is fixed.
- If the owner wants proof before Monday, one option is a supervised run of the Phase 5 training as user `mind15` with the same sandbox, writing to a scratch `out_dir`. It must **not** write to `models5/live`, because the books would pick that model up at once. It should run at low priority at a quiet time and needs the owner's go-ahead. `phase5-update --fresh` is **not** a safe test, because it writes into the live folder.
- Later code changes, through the normal test-and-deploy path: a Telegram card when a refit attempt fails, and removal of the cache folder on failure as well as on success.

## (d) Monday checklist (read-only, run after about 00:45 UTC)

Prefix each with `ssh -i ~/.ssh/minds15.pem -o ConnectTimeout=20 -o LogLevel=ERROR ec2-user@13.251.40.113 '<command>' </dev/null`.

1. New model files (expect `model_20261123T00....json` in each):
   `ls -la --time-style=+%F_%T /data/mind15/research/out/rl/models5/live /data/mind15/research/out/rl/models6/live`
2. Finished cleanly (utc 2026-11-23, model path under `/data/mind15/...`, minutes, `memory_events: []`):
   `cat /data/mind15/research/out/rl/forward5/last_update.json /data/mind15/research/out/rl/forward6/last_update.json`
3. Log ends with `model written: /data/mind15/... (data end 2026-11-23 00:00)` for Phase 5 and about 00:15 for Phase 6, with zero Tracebacks:
   `cd /data/mind15/research/out/rl; tail -n 8 forward5/update.log; tail -n 8 forward6/update.log; grep -c Traceback forward5/update.log forward6/update.log`
4. Nothing left running or behind (expect no lock, no cache folders, no `engine15.rl` process):
   `cd /data/mind15/research/out/rl; ls forward5/update.lock; ls -d phase5_cache/* phase6_cache/* 2>&1; ps -eo pid,ni,etime,rss,cmd | grep "engine15.rl" | grep -v grep`
5. Exactly one launch per phase in the engine log:
   `grep -nE "update launched|update due|low memory|launch failed" /data/mind15/live.log`
6. The books use the new models. Expect `p5_rlq` and `p6_p4trend` on `m5_20261123T...`, `p6_mtrend` on `m6_20261123T...`, `model_data_end_utc` 2026-11-23, and `update` back to "not due" (or "phase5's refit" for p6_p4trend). The `seed_fallback` column shows whether BTC seeds left the fallback:
   `/data/venv/bin/python -B -c "import json;pb=json.load(open(\"/data/mind15/out/live/page.json\"))[\"playbook\"];[print(b,a,s.get(\"model\"),s.get(\"model_data_end_utc\"),s.get(\"seed_fallback\"),s.get(\"update\")) for m in (\"playbook5\",\"playbook6\") for b,v in pb[m].items() for a,s in v[\"books\"].items()]"`
7. The decision records carry the new id in `"m"`:
   `for f in /data/mind15/research/out/rl/forward5/decisions_*.jsonl /data/mind15/research/out/rl/forward6/decisions_*.jsonl; do echo "$(basename $f) $(tail -n1 $f | cut -c1-120)"; done`
8. Headroom: `df -h /data; free -m`
9. Telegram should have sent "Weekly RL refit done (Phase 5)", "Weekly RL refit done (Phase 6)" and "RL weekly check · new models in use". If an RL book regains a trading seed, it also sends "RL: agent back". `/rl` in the bot shows the card on request.

Note: the page's `model` field is the model id, stamped when the payload is written (for example `m5_20261116T030954Z`). The file name is stamped when training starts (`model_20261116T030703Z.json`). They differ by a few minutes, so do not expect them to match.

## (e) What I could not verify

- That the training completes on this box, and how long it takes. Nothing was run, by rule.
- The peak memory and the cache size of a server refit. The laptop logs record no memory peak, and the caches were deleted after success.
- How much a running refit slows the engine's step on 4 vCPU.
- Whether the Monday 00:00 step itself runs longer (surprise-mining jobs, evidence-store daily check). That would shift the launch by a minute or two.
- The values of the unit's environment variables (masked by rule). The refit code reads none of them.
- The Telegram bot's stored state (`rl_models`, `refits` baseline), which decides whether the cards fire. The code reads it, but I did not open it.
