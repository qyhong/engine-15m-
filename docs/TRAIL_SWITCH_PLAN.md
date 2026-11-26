# Plan: the Setups page, the signals and the VIP vault move to a trailing-stop book

**Status (26 Nov 2026): Mind 15's side is BUILT with both switches OFF (not deployed yet). Nothing new is sent to
the vault and nothing on the page changes until the switches go on.**

## The decision

- The owner, 26 Nov 2026, shown the trail copy's forward lead (BTC + ETH, 11-25 Nov, paper: `b_trail` 24 trades, 19
  won, +$5,047, +15.2R against `b_targets` 17 trades, 11 won, +$2,780, +9.8R; all eight markets 71 trades, 55 won,
  +$12,032 against 42, 27, +$6,217): **"Lets switch. But explain to me what is the changed."**, then **"Ok. Lets plan
  for this and apply for VIP"**, then, asked in this project whether the Setups page and the signals move too:
  **"Page and VIP"**. So ONE book for the Setups page, the signals, the Telegram cards and the vault. (The AI Trading
  session reported the same answer from its session.)
- Not a passed test. On 2020-2026 history every tight trail made less than holding (H36: `b_trail` -$48,808 against
  the main book's +$329,439, `b_targets` -$28,862). The forward lead is two weeks in one falling market. The owner saw
  the history on 21 Nov (v5.2.8) and again today.
- This sets aside the 17 Nov verdict rule that a trail proposal waits for the second check (60 trades, not before
  10 Dec). That check still runs and is still reported.
- Open, the owner's to choose before the switch: WHICH markets move. The vault trades BTC and ETH only; the page shows
  eight. The build takes a list of markets, so either answer (BTC and ETH only, or all eight) is the same code.

## What changes for a follower or a VIP member

| | Now (`b_targets`) | After (the trail book) |
|---|---|---|
| Entry, first stop (3 x ATR 1h) | same | same |
| Profit | half at Target 1, rest at Target 2 | no targets; the whole position rides |
| Stop | to the entry once, after Target 1 | from 1R in favour it trails every 15m close: the tighter of the last confirmed 15m swing and 2 x ATR(15m), never looser |
| End of a trade | stop, Target 2, or a flip | the trailing stop, the first stop, or a flip |
| Trades | fewer, longer (about 35-40 h) | more, shorter (about 23 h); more fees |

## The design (Mind 15's side). This section is the contract the code is built to.

### 1. The book

`b_trail_setups` in `shadows.CHALLENGERS`: rule `{"trail": True, "early": True}`, every market (the early entry acts
only where `CFG["early_entry"]` names the market: BTC and ETH). It starts flat at its deploy. `b_trail` (no early
entry) is not touched and stays the yardstick; `b_targets` keeps running on paper after the switch.

### 2. The switch and the voice of each market

- `engine15/setups_voice.py` (new, money path). `TRAIL_MARKETS = ()` is the switch: the markets whose published
  voice is the trail book. Empty = OFF = today, exactly.
- A market's published voice is `targets` (book `b_targets`) or `trail` (book `b_trail_setups`). It changes only
  between setups, never inside one:
  - A market named in `TRAIL_MARKETS` whose voice is `targets`: at the first step the switch is seen, the opened_utc of
    the targets setup open then is remembered (`wait_opened_utc`; none when flat). The voice becomes `trail` at the
    first step where the targets book no longer shows that setup (flat, or a new setup). `from_utc` = that step's
    price bar close.
  - With voice `trail`, the trail book's setup is published only when its `opened_utc >= from_utc`. A trail setup
    that was already open at the changeover is never shown: the market reads FLAT until the trail book opens its next
    one. (So nobody joins half-way, a setup's first sight is always its opening, and an exit id can never be made twice.)
  - Going back is the mirror: take the market out of `TRAIL_MARKETS`; the voice returns to `targets` when the
    published trail setup has ended, and a targets setup opened before that moment is not shown.
- Memory: `data/setups_voice_state.json` (atomic; written only once a market has left the targets voice; in the
  hourly state copies). `setups.write` moves it one step (`setups_voice.update`) and saves it BEFORE setups.json is
  built. The Telegram bot (another process) reads the same file; the rule below is safe in whichever order the two
  read and write: a market shows the same thing or nothing yet, never a setup the page will not show. setups.json is
  the second copy: a trail market carries `exit_rule` and `exit_rule_from_utc`, and a lost state file is rebuilt from
  them (`setups_voice.recover`).
- ONE function decides what a market shows, used by setups.py, signals.py, the adverse alert and the preview:
  `setups_voice.published(page, sym, state) -> {"rule", "book", "view", "open", "from_utc", "pending"}`. The bot
  issues a new signal only when the published voice is also the wanted one (nothing new while a market is changing).

### 3. setups.json (the page's data; keys added only, and only on a trail market)

A market whose voice is `trail`:
- `exit_rule: "trail"`, `exit_rule_from_utc`, `trail_active: true|false` (true once the trail has armed: price has
  gone 1R in favour).
- `trail_from`: the price at which the trail arms (1R in favour), while the setup is open and not armed; null
  otherwise. Page data only, never in the vault's book.
- `stop` is the book's stop as it stands (it moves). `target_1`, `target_2`, `rr_now_t1`, `rr_now_t2`, `held_share`
  null; `t1_taken` false.
- Its record (`closed`, `wins`, `realized_usd`, and its rows in `closed_setups`) is what the page showed: the
  targets book's trades closed before `from_utc` plus the trail book's trades opened at or after it.
- `closed_setups[].why_out` gains the code `TRAIL_STOP`; setup_events.json gains the type `STOP_MOVED` (reason codes
  `TRAIL_ARMED`, `PAST_ENTRY`, `STEP`), the no-fill code `RAN_FIRST` and the closed code `TRAIL_STOP`. `book.verdict` is null while any market is on the trail voice
  (one scoreboard row no longer describes the record); `book.rule` names the rule in force (a fixed short list).
A market on the targets voice carries no new key. With the switch off the file is byte-for-byte what it is today.

### 4. The signals and the Telegram cards (signals.py; the bot's process reads the page)

A signal from a trail setup follows these rules (to be registered in research/HYPOTHESES.md as the trail version of
H53 before the switch; H53's record is kept, the two are never pooled):
1. Entry: as H53 (a limit at the entry, the four bars after the alert's bar).
2. No fill: the stop trades first, the window passes, the book closes first, or price goes 1R in favour before the
   fill (the trail has armed; the same line the vault uses for a join).
3. After the fill: no targets. In each bar the stop is the one the book published at the close before that bar; the
   stop is looked at first; a gap through it fills at the bar's open. The exit word is `stop` (never moved) or `trail`.
4. The book closes its own trade for another reason: as H53 rule 4.
5. Costs as H53.
Cards: the new-setup card shows the entry, the stop and the price where the trail starts; a "stop moved" card when
the trail arms, when the stop first passes the entry, and after that whenever it has moved at least half an R since
the last card (constants, declared once). No research words, no book names.

### 5. vault_feed.py (two keys must both be on)

- `SEND_TRAIL = False`. A BTC or ETH entry that carries `exit_rule: "trail"` while this is False is NOT sent (one
  line and the memory alarm): the vault refuses a body with a key it does not know. A test fails if a vault market is
  in `TRAIL_MARKETS` while `SEND_TRAIL` is False.
- The trail book body, as agreed with the AI Trading session: `exit_rule: "trail"`, `trail_active`, `symbol`, `side`,
  `entry`, `stop`, `price`, `opened_utc`, `entry_window_open`, `as_of_utc`, `lead_pts` as today; NO `target_1`,
  `target_2`, `rr_now_t2`, `t1_taken`. Checks before sending: not armed = the stop strictly on the loss side of the
  entry; always = the stop strictly on the loss side of the price. A FLAT book is exactly today's FLAT body.
- Intents in trail mode: `move_stop` (futures only) at a step where the book's stop is tighter than the last one
  sent for that setup, at most one a step, id `<SYM>.<opened YYYYMMDDTHHMMSSZ>.ms.<DDHHMM of as_of>`,
  `stop_price` the new stop, `reference_price` the price now; `close` when the setup leaves (from the trail book's
  own trade file); never `reduce`. The feed's memory keeps the last stop sent.
- A `move_stop` that was not sent yet is dropped when a newer one (or the close) is made for the same setup, and a
  403 on a trail `move_stop` is final (not tighter than the member's stop, or past the price): neither may hold the
  book back.
- The dry run, switch off (`engine15/trail_preview.py`): every step writes `out/live/trail_book_preview.json`, the
  exact bodies the feed WOULD post for BTC and ETH if the trail book were the voice from the preview's first step (book
  bodies, and the last 50 `move_stop` / `close` bodies it would have made, each with `made_utc` and `ok`). Never
  posted. The AI Trading session checks it with the vault's `aitvault book-check`.

### 6. Tests

- `tests/test_money_path_golden.py` stays green untouched with the switch off.
- A second golden record for trail mode on the same fixed bars (`tests/test_money_path_trail_golden.py`): every
  trade, book body and intent (147 trades, 260 bodies, 242 intents).
- Unit tests: the voice changeover both ways, the lost state file, the "already open is not shown" rule, the id
  scheme, "only tighter", the two-key guard, the signal rules bar by bar, the cards.
- The full suite before any deploy (`tools/deploy.sh`).

### 7. Versions and records

- The build with the switch off deploys as a paper change: a new shadow book and a preview file. No reading changes.
- Switching on is a new engine version with a `VERSION_NOTE`, deployed with `tools/deploy.sh`.
- Records: CLAUDE.md (the money path), HANDOFF.md, docs/RESTORE.md (the two state files), `tools/money_files.txt`.

## The vault's and the page's side (the AI Trading session; reported, not this project's to build)

- A new vault package: accepts `exit_rule: "trail"` books; joins only while `trail_active` is false; no Target 1
  reduce; repeated `move_stop` already works (each its own id; the new stop must be tighter and not past the price).
  Built together with the per-member direction rule, reviewed, installed on the owner's yes there.
- The Setups page: a trail market shows the moving stop and no targets; the closed list knows `TRAIL_STOP`; a null
  verdict. The VIP page, the Terms and the status lines that name Target 1 / Target 2. A short notice to members.

## Order

1. Mind 15 builds sections 1-6 with the switch off; deploy (paper). `b_trail_setups` starts its record; the preview
   file starts.
2. The vault package is installed; the AI Trading session confirms it accepts the preview's bodies.
3. The page shows a trail market correctly (tested on a copy with a sample file).
4. The owner approves the wording; members are told.
5. The owner's word to switch on, in both sessions, with the list of markets. Mind 15 sets `TRAIL_MARKETS` and
   `SEND_TRAIL` (new version). Each market changes over by itself when its open targets setup ends. First real trail
   setup: both sessions watch the join, every stop move and the exit, and report.

## After the switch

- A registered forward read (written into research/HYPOTHESES.md before the switch): `b_trail_setups` against
  `b_targets` on the switched markets at 30 and 60 closed trades; the trail signals' followable record; members' real
  fills against the paper book (slippage at a moving stop is the open question).
- Going back is the same switch, the same changeover, the owner's word.

## Risks said once

- History is against tight trails (above).
- Real fills at a trailing stop are worse than the paper book's (stop-market in a fast move); more trades, more fees.
- A feed stall while a trail is live leaves the member's last stop resting where it was: safe, but not trailing.
- A person following by hand cannot move a stop every 15 minutes; the cards give the larger moves only.
