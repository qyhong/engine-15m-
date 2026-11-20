# Restoring the engine's memory on the box

Written 20 Nov 2026. The steps were drilled in tests (`tests/test_vault_feed.py`, the restore drill;
`tests/test_state_copies.py`). They have NOT been drilled on the live box.

## What the memory is

| File (in `/data/mind15/data/`) | What it holds | If it is lost or rolled back while a BTC or ETH setup is open |
|---|---|---|
| `vault_feed_state.json` | Which open setup the feed saw inside its entry window, the last book it sent, and every exit instruction (sent or still waiting). | The feed cannot know it may send exits for that setup, so it sends **none**, and waiting exits are gone. Members are covered only by their stop on the exchange. |
| `shadow_state.json` | Every shadow book, including `b_targets`, the book the VIP vault copies. | The books start flat. The open setup disappears from the Setups page; the feed sees a position that ended and sends a close. |
| `live_state.json`, `signals_state.json` | The main books; the signal record with the entry windows. | Not on the vault's exit path. Entry windows of new setups depend on `signals_state.json`. |

## Where the copies are

- **Hourly, on the box:** `/data/mind15/data/state_copies/<UTC stamp>/`, 48 kept (two days). Timer
  `mind15-state-copy`, minute 8 of every hour. Each copy has a `MANIFEST.json` that says what the files held.
- **Daily, on the laptop:** `backup/server/` (`tools/backup_pull.py`, 7 kept). It contains `data/`, so it contains the
  hourly copies too.

A file that is not readable JSON is never copied, so a copy is always something that can be put back.

## How you learn that the memory is lost

- Telegram card **"VIP vault · feed memory lost"**, one per setup.
- `/data/mind15/live.log`: `vault: ALARM <market> <side> setup opened <time> is open and the feed's memory was
  missing|unreadable: NO exit will be sent for it`, at every step while that setup stays open.
- An unreadable file is kept beside the new one as `vault_feed_state.json.bad-<unix time>`.

## Putting the feed's memory back

Do it between two steps (the engine sleeps most of each 15 minutes). Tell the AI Trading Bot session first: the vault
is its system.

1. Look at the copies, and at the one you mean to use beside what is in use now:

   ```bash
   cd /data/mind15
   sudo -u mind15 /data/venv/bin/python tools/server/state_copies.py list
   sudo -u mind15 /data/venv/bin/python tools/server/state_copies.py show <STAMP>
   ```

   Choose the newest copy in which the open setup appears with the **same side and the same `opened_utc`** as on the
   Setups page, and with `exits_will_be_sent: true`. If no copy shows that setup, a restore cannot help it: leave the
   file as it is (the alarm stays until the setup is over) and tell the owner.

2. Stop the engine right after a `step done` line, restore, start it:

   ```bash
   tail -2 /data/mind15/live.log        # the last line must be "sleeping ...s until the next close"
   sudo systemctl stop mind15
   sudo -u mind15 /data/venv/bin/python tools/server/state_copies.py restore <STAMP>
   sudo systemctl start mind15
   ```

   The tool refuses while the service is active, restores only `vault_feed_state.json` unless you name other files,
   and keeps the file that was in use as `vault_feed_state.json.before-restore-<stamp>`.

3. Watch the next step in `live.log`. Expected:
   - no `ALARM` line;
   - if Target 1 was taken while the memory was gone: `reduce` (spot and futures) and a futures `move_stop`, late;
   - when the setup ends: `close`;
   - an exit that had already gone out before the loss is sent again and the vault answers "duplicate": harmless.

   Not expected, and a reason to stop the engine and ask: a `close` for a setup that is still open on the Setups page.

## Putting the shadow books back (bigger: ask the owner first)

Only when `shadow_state.json` itself is lost or damaged. Restore it together with the feed's memory **from the same
stamp**:

```bash
sudo -u mind15 /data/venv/bin/python tools/server/state_copies.py restore <STAMP> shadow_state.json vault_feed_state.json
```

What happens next: on its next step the engine replays every bar since the copy for every shadow book. The books are
deterministic, so an open setup keeps its `opened_utc`, and the feed goes on as before. Trades that closed between the
copy and the restore are written to `out/live/shadow_trades_*.csv` **a second time**: remove the duplicate rows by hand
before trusting any scoreboard. Never restore a copy older than the daily one without the owner's word: the older the
copy, the more is replayed.

Do **not** restore `shadow_state.json` from one stamp and leave a newer `vault_feed_state.json` in place when the two
disagree about which setup is open: the feed would close the setup it remembers.

## After any restore

Run `bash tools/server/check_drift.sh` on the laptop, and write in HANDOFF.md what was restored, from which stamp, and
what the next step logged.
