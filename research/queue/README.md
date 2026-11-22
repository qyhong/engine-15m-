# Research job queue on the Singapore box

A small runner that works through long research computations on the server one after another, unattended, for
days, while staying out of the live engine's way. The owner asked (22 Nov 2026): "Queue at least 20 studies for SG
box so it will have always have min 72 hours queue tasks backlog to clear".

- `research/queue/runner.py` runs ON THE SERVER as `/data/research_queue/runner.py` with `/data/venv-research/bin/python`.
- `tools/research_queue.py` runs on the laptop and drives it over ssh / scp.
- It is NOT a systemd service and has no cron entry. **After a server reboot it is not running: start it again
  with `py -3 -X utf8 tools/research_queue.py start`.** Queued and interrupted jobs are kept and resume.

## Folder layout (`/data/research_queue/`, owned by ec2-user; nothing outside it is written)

| path | what |
|---|---|
| `jobs/<ID>.json` | queued jobs: `id`, `command` (list), `cwd`, `out`, `est_hours`, `priority`, `added_utc`, `failures` |
| `running/`, `done/`, `failed/` | the same files as the job moves on (failed ones carry exit code and last log lines) |
| `logs/<ID>.log` | the job's stdout and stderr, appended across runs |
| `out/<ID>/` | the job's `--out`: `progress.json`, checkpoints, then `results.json`, `report.md`, `DONE` |
| `code/<commit>/` | code snapshot: `engine15/`, `research/` from that commit, `data -> /data/mind15/data` (read only) |
| `status.json` | rewritten every minute: running jobs with their progress, queued, BACKLOG HOURS, done, failed, disk, memory |
| `runner.pid`, `runner.lock`, `runner.log`, `runner.out` | the runner's pid, single-instance lock, its log |
| `STOP`, `PAUSE`, `LAST_GUARD_STOP.txt` | control files and the last guard that stopped jobs |

## The job contract

A job is one command, run with its working directory at `code/<commit>/`:

    /data/venv-research/bin/python research/queue/<harness>.py --study <ID> \
        --fits-dir /data/mind15/research/out/h60_regime_exits/fits_today --out /data/research_queue/out/<ID>

It must be resumable (checkpoints in `--out`, continues if run again), keep `progress.json` up to date (`done`,
`total`, `started_utc`, `updated_utc`, `est_hours_left`), and on success write `results.json`, `report.md` and an empty
`DONE`, then exit 0. Exit 0 without `DONE` counts as a failure. `--estimate` prints the CPU hours as one number;
`--smoke` runs a tiny version in under 2 minutes. The runner adds `nice 19`, `ionice -c3` (when allowed),
`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1`, and stops a job with SIGTERM to its process group
(SIGKILL 60 s later): checkpoint often.

## Adding a study

    py -3 -X utf8 tools/research_queue.py snapshot <commit>           # once per commit (refuses if it exists)
    py -3 -X utf8 tools/research_queue.py add --id H70_exits --harness <harness> --study H70 --commit <commit> --est-hours 6 [--priority 10]
    py -3 -X utf8 tools/research_queue.py status                      # BACKLOG in hours
    py -3 -X utf8 tools/research_queue.py fetch H70_exits             # -> research/out/queue/H70_exits/
    py -3 -X utf8 tools/research_queue.py logs H70_exits

Without `--est-hours` the tool runs the harness's `--estimate` on the server. Lower priority numbers run first, then
the oldest. An id that already exists anywhere (queued, running, done, failed, out, logs) is refused. To run a failed
job again, give it a new id. `install` copies `runner.py` and this README to the server (restart the runner to load it).

## Stopping everything at once

    ssh ... 'touch /data/research_queue/STOP'      # or: py -3 -X utf8 tools/research_queue.py stop

Running jobs get SIGTERM, go back to the queue (they resume later) and the runner exits within a minute. `start`
removes `STOP` and starts the runner again. `pause` / `resume` (the `PAUSE` file) let running jobs finish but start
nothing new.

## Guards (checked before every start and every few seconds while jobs run)

| guard | threshold | effect |
|---|---|---|
| workers | `--workers`, default 2, hard maximum 2 | the engine needs one CPU and the vault another |
| free disk on /data | under 4 GB | start nothing new |
| | under 2 GB | stop all running jobs (back to the queue), reason in `LAST_GUARD_STOP.txt` |
| available memory | under 3 GB | start nothing new |
| | under 1.5 GB | stop the youngest running job (at most one per minute) |
| `STOP` file | present | stop running jobs and exit |
| `PAUSE` file | present | start nothing new |
| engine deploy | `/data/mind15/DEPLOYED.json` modified in the last 45 minutes | start nothing new (its first step rebuilds a cache jobs read) |
| run time | over 3 x `est_hours` (at least 2 hours) for one run | stop it, mark failed "over time" (no retry) |
| failures | a failing job | retried automatically once, then `failed/` |

A job stopped by a guard or by `STOP` is not a failure; it goes back to the queue with its place. On start the runner
puts any job left in `running/` back in the queue (stopping a still-living orphan first), so a crash or reboot loses
only the work since the job's last checkpoint. A second runner refuses to start (flock on `runner.lock`).
