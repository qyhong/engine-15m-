# Plan: the VIP vault follows a trailing-stop book on BTC and ETH

**Status (26 Nov 2026): planned. Nothing is built on Mind 15's side, nothing is deployed, nothing new is sent.**

## The decision

- The owner, 26 Nov 2026, shown the trail copy's forward lead (BTC + ETH, 11-25 Nov, paper: `b_trail` 24 trades, 19
  won, +$5,047, +15.2R against `b_targets` 17 trades, 11 won, +$2,780, +9.8R; all eight markets 71 trades, 55 won,
  +$12,032 against 42, 27, +$6,217): **"Lets switch. But explain to me what is the changed."** Then, asked whether the
  public Setups page moves too: **"Ok. Lets plan for this and apply for VIP"**. Read as: **VIP auto-trading only.** The
  Setups page, the signals and the Telegram cards stay on `b_targets` (Target 1 / Target 2).
- Not a passed test. On 2020-2026 history every tight trail made less than holding (H36: `b_trail` -$48,808 against
  the main book's +$329,439, `b_targets` -$28,862). The forward lead is two weeks in one falling market. The owner saw
  the history on 21 Nov (v5.2.8) and again today.
- This sets aside, for the vault's book only, the 17 Nov verdict rule that a trail proposal waits for the second check
  (60 trades, not before 10 Dec). That check still runs and is still reported.
- The AI Trading session reports the owner confirmed in its session (26 Nov) that the vault gets trail-book support in
  the same update as the per-member direction rule.

## What changes for a VIP member

| | Now (`b_targets`) | After (trail book) |
|---|---|---|
| Entry, first stop (3 x ATR 1h) | same | same |
| Profit | half at Target 1, rest at Target 2 | no targets; the whole position rides |
| Stop | to the entry once, after Target 1 | from 1R in favour it trails every 15m close: the tighter of the last confirmed 15m swing and 2 x ATR(15m), never looser |
| End of a trade | stop, Target 2, or a flip | the trailing stop, the first stop, or a flip |
| Trades | fewer, longer (about 35-40 h) | more, shorter (about 23 h); more fees |

## What the page shows and what the vault trades will differ

With "VIP only" the Setups page shows the targets book and a member's account trades the trail book. They enter
together most of the time (same entry rule), but they leave at different moments, and after a trail exit the trail book
can re-enter while the page's setup is still open (or the reverse). The VIP page and the Terms must say so in plain
words (the owner approves the text; the AI Trading session owns the pages).

## Mind 15's side (this project)

1. **A new paper book `b_trail_vip`** on BTC and ETH: rule `{"trail": True, "early": True}` (the trail of `b_trail`
   with the v5.2.9 early entry, so the entry and `opened_utc` are fixed in the step that decides them, as the vault
   needs). Started fresh at its deploy. `b_trail` is not touched and stays the yardstick. Before the build: confirm in
   `shadows.run` that `early` and `trail` work together and write a test for it.
2. **A second document for the vault, `out/live/vip_book.json`**: the two markets from `b_trail_vip`, built with the
   same market builder as setups.json but without targets. `setups.json`, `setups.BOOK` and `signals.BOOK` stay
   `b_targets`.
3. **`vault_feed.py`, behind one switch that is OFF** (`VIP_EXIT_RULE = "targets"`): with `"trail"` the feed reads
   `vip_book.json` and sends, in the shape agreed with the AI Trading session:
   - the book: `exit_rule: "trail"`, `trail_active` (true once the stop may sit on the profit side), entry, stop, price,
     `opened_utc`, `entry_window_open`, `lead_pts` as today; no `target_1`, `target_2`, `rr_now_t2`; `t1_taken` as the
     vault's package asks (false or absent);
   - `move_stop` (futures only) at a 15m close where the book's stop tightened, at most one a close, id
     `<SYM>.<opened YYYYMMDDTHHMMSSZ>.ms.<DDHHMM of as_of>` (unique, under 64 characters);
   - `close` when the book leaves; never `reduce`.
4. **The changeover, per coin**, when the switch goes on: a coin keeps the targets book until the targets setup a
   member may hold has ended (its exits are still sent); from then it gets the trail book as it stands. A trail setup
   already open at that moment arrives with its entry window closed, so nobody joins it late.
5. **Tests**: the golden money-path test stays green with the switch off (the vault is told exactly what it is told
   today). A second golden record for the trail mode (same fixed bars) covers every book body and intent. Unit tests
   for the id scheme, "only tighter", the changeover, and a lost-memory case. Full suite before any deploy.
6. **Version**: the build with the switch off deploys as a paper change (new shadow book; reading cache not rebuilt).
   Turning the switch on is a new engine version with a `VERSION_NOTE`, deployed with `tools/deploy.sh` when both coins
   are flat in the vault or far from an exit.
7. **Records**: CLAUDE.md (the money path now also `b_trail_vip` and `vip_book.json`), HANDOFF.md, docs/RESTORE.md
   (the feed's memory holds the last stop sent), `tools/money_files.txt`.

## The vault's side (the AI Trading session; reported, not this project's to build)

- A new vault package: accepts `exit_rule: "trail"` books; joins only before 1R in favour; no Target 1 reduce; repeated
  `move_stop` already works (each move is a new reduce-only stop order, then a cancel of the old one; the new stop must
  be tighter and not past the price). Built together with the per-member direction rule, then reviewed, then installed
  on the owner's yes there.
- Wording that names Target 1 / Target 2: the VIP page, the Terms, status lines. A short notice to members before the
  rule changes.

## Order

1. Mind 15 builds steps 1-5 with the switch off; deploy (paper). `b_trail_vip` starts its own forward record.
2. The vault package is installed; the AI Trading session confirms the installed package accepts the trail shape.
3. Dry run: Mind 15 writes the trail bodies it WOULD send to a log for a few setups; the two sessions compare them with
   what the vault's parser accepts. No real order.
4. The owner approves the member wording; members are told.
5. The owner's word to switch on, in both sessions. Mind 15 turns the switch on (new version) when both members are
   flat. First real trail setup: both sessions watch the join, every stop move and the exit, and report.

## After the switch

- A registered forward read (to be written into research/HYPOTHESES.md before the switch): `b_trail_vip` against
  `b_targets` on BTC and ETH at 30 and 60 closed trades, and members' real fills against the paper book (slippage at a
  moving stop is the open question).
- Going back is the same switch: `VIP_EXIT_RULE = "targets"`, same per-coin changeover, the owner's word.

## Risks said once

- History is against tight trails (above).
- Real fills at a trailing stop are worse than the paper book's (stop-market in a fast move); more trades, more fees.
- Page and account differ (above).
- A feed stall while a trail is live leaves the member's last stop resting where it was: safe, but not trailing.
