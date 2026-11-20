# Rebuilding the Mind 15 box from nothing

Written 20 Nov 2026 from what is on the box that day. It has NOT been drilled: no box has been rebuilt from this page
yet. Where a step is from the record and not from a run, it says so.

Everything here is this project's part. The web host, nginx, the candle-forecast feed and the VIP vault on the same box
belong to the AI Trading Bot session and are rebuilt from its records.

## What the box is

- AWS EC2, Singapore, t2.xlarge (4 vCPU, 16 GB), Amazon Linux 2023, Elastic IP 13.251.40.113.
- Root disk 8 GB. Data disk 24 GB, xfs, mounted at `/data` by UUID with `nofail` (`/etc/fstab`).
- Users: `ec2-user` (owns the code in `/data/mind15`), `mind15` (uid 990, runs the services; `ec2-user` is in its
  group). Home of the service user: `/var/lib/mind15`.

## What is in git (this folder)

| File | Goes to | What it is |
|---|---|---|
| `units/mind15.service`, `units/mind15-telegram.service` | `/etc/systemd/system/` | the engine and the Telegram bot, sandboxed |
| `dropins/24x7.conf` | `/etc/systemd/system/mind15.service.d/` and `mind15-telegram.service.d/` | wait for `/data`, never give up restarting |
| `units/mind15-watchdog.*`, `bin/mind15-watchdog` | `/etc/systemd/system/`, `/usr/local/bin/` | restarts a stuck engine (installer: `mind15_watchdog.sh`) |
| `units/mind15-state-copy.*` | `/etc/systemd/system/` | hourly copy of the engine's memory (installer: `install_state_copy.sh`) |
| `run_live.sh` | `/data/mind15/run_live.sh` (mode 755) | loads `mind15.env`, starts the loop |
| `logrotate/mind15` | `/etc/logrotate.d/mind15` | weekly, 8 kept |
| `requirements-box.txt` | `/data/venv` | the exact Python packages; numpy and pandas sign the reading cache |
| `mind15.env.example` | `/data/mind15/mind15.env` (mode 640, `ec2-user:mind15`) | the switch NAMES; the values are not in git |
| `mind15_own_user.sh` | run once | creates the `mind15` user and moves the services under it |
| `check_drift.sh` | run on the laptop | read-only: does the box still match this folder? |

## What is NOT in git and where it comes from

| Thing | Source |
|---|---|
| `data/`, `journal/`, `out/live/`, RL forward books | the laptop's daily archive `backup/server/` (`tools/backup_pull.py`, 7 kept) |
| the reading cache `data/evcache` (about 13 GB) | not backed up: the first step rebuilds it |
| raw archives `data/raw` | not backed up: downloaded again |
| `mind15.env` values | the owner, and the session that owns each item; nobody in this project reads that file |
| Telegram bot token file | the owner puts it on the box; never in git, never in chat |
| the page push key (`/etc/mind15/push_key`) and the web box's `authorized_keys` line | made on the box; the AI Trading Bot session adds the public half on the web box |
| `/etc/ait-engine/*` (vault config, secret, certificates) | the AI Trading Bot session's vault installer |
| `tools/pull_answers.py`, `tools/FORMAT.md` | the AI Trading Bot session's files |

## Steps

1. **Instance and disk.** Launch the instance, attach the Elastic IP, attach and mount the data disk at `/data`
   (xfs, by UUID, `nofail`). Install Python 3.12.
2. **Stop the vault from following a half-built engine.** Tell the AI Trading Bot session before anything starts. The
   vault feed is on only when `MIND15_VAULT_CONFIG` is set: leave it out of `mind15.env` until step 8.
3. **Python.** `python3.12 -m venv /data/venv`, then install `requirements-box.txt` exactly
   (`torch==2.15.0+cpu` from the CPU index named in that file). Do not upgrade anything: a different numpy or pandas
   means a different reading cache. The research environment `/data/venv-research` is optional and described in the
   same file.
4. **Code.** Create `/data/mind15` (owner `ec2-user`). From the laptop: `bash tools/deploy.sh` cannot run yet (no
   service), so unpack the commit by hand once: `git archive origin/main | ssh <box> "tar xf - -C /data/mind15"`.
   Copy `tools/server/run_live.sh` to `/data/mind15/run_live.sh`, mode 755.
5. **Data.** Unpack the newest laptop archive from `backup/server/` over `/data/mind15`. It holds the journal, the
   live outputs and `data/` including the hourly memory copies of that day. Read `docs/RESTORE.md` before starting
   the engine: a memory that is a day old while a setup is open is exactly the case that page is about.
6. **User and units.** Run `mind15_own_user.sh` (from the record: it expects the unit files to exist, so first copy
   `units/*.service`, `units/*.timer` and the drop-ins into place, `sudo systemctl daemon-reload`). Then
   `bash mind15_watchdog.sh` and `bash install_state_copy.sh`. Copy `logrotate/mind15`.
7. **Secrets and switches.** The owner supplies the Telegram token file and the values of `mind15.env` (names in
   `mind15.env.example`). Make the push key on the box and give its public half to the AI Trading Bot session.
8. **First start, without the vault.** `sudo systemctl enable --now mind15 mind15-telegram`. The first step rebuilds
   the reading cache: about 15 minutes after a card change on a warm box; from an empty cache it takes longer and has not
   been timed. Watch `/data/mind15/live.log` until every group prints `step done`.
9. **Check, then the vault.** On the laptop: `bash tools/server/check_drift.sh` must print `NO DRIFT`. Compare
   `out/live/setups.json` with the Setups page. Only then, with the owner's word and the AI Trading Bot session ready,
   set `MIND15_VAULT_CONFIG` and restart. Write a deploy receipt by running `bash tools/deploy.sh` once.

## Keeping this page true

`bash tools/server/check_drift.sh` after any change on the box. If you change a unit, the launcher, the watchdog or a
package on the box, change the copy here in the same commit.
