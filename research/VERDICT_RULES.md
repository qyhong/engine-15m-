# Verdict rules for `p8_fvg` and `b_trail`: what a pass or a fail changes

**Status: APPROVED by the owner on 17 Nov 2026 ("Approve all", including the optional 10 Dec line 4), before either book reached 30 live trades (server scoreboard at the time: `p8_fvg` 24 of 30, `b_trail` 22 of 30). In force as written. Where the text below says PROPOSED, read it as approved on that date; the wording is kept as it was approved.**

Written 17 Nov 2026, before either book reached 30 live trades. Paper only. Nothing here places an order.

The owner agreed today that we write down now what each result will change. Then the result cannot
bend the decision. This file changes no code and no other document.

Words used here:

- **Book**: one paper account that follows one fixed rule.
- **Main books**: the engine's own eight paper accounts, one per market.
- **Shadow book**: a paper copy of the main rule with one thing changed, run beside it.
- **Stop**: the price at which a trade is closed to limit the loss.
- **R**: the planned risk of one trade, the distance from the entry price to the stop. "+2R" means the
  trade made twice what it risked.
- **ATR**: the usual size of a bar's move over the last 14 bars.
- **Flip**: closing a position and opening the opposite one.

---

## 1. What had already been seen when this was written (disclosure)

This is not a blind pre-registration. Partial results were already visible.

- From the owner's brief, 17 Nov 2026: `p8_fvg` had 24 of 30 trades, net +$285. `b_trail` had 22 of 30
  trades, net +$4,978.
- The laptop's copy of `out/live/scoreboard.json` is stale (written 16 Nov 2026 10:33 UTC; the engine
  runs on the server now, `HANDOFF.md` "WHERE IT RUNS"). On that copy both books had 20 trades.
  `b_trail`'s range was already wholly above zero (90% of its trades won). `p8_fvg`'s range included zero.

So the writer knew which way each book leaned. The rules below were chosen from what the project had
already written down (cited in each section), not from those numbers. The owner should weigh that.

---

## 2. How the scoreboard reaches a verdict (the same for every book)

Source: `engine15/reports.py`, functions `_stats` and `scoreboard`; `MIN_TRADES = 30`.

1. It takes each closed live trade's result in dollars after fees (`pnl_usd`). Trades from all the
   book's markets are pooled into one list. History trades never count.
2. It works out the average result per trade and how much the results vary (the standard deviation).
3. It builds a "90% range" for the true average: `mean - half` to `mean + half`, where
   `half = 1.645 * sd / math.sqrt(n)` (n = number of trades).
4. The verdict, quoted from the code:

| Condition in the code | Verdict text | Called here |
|---|---|---|
| `n < MIN_TRADES` (fewer than 30 trades) | `too few trades to judge (N of 30)` | no verdict yet |
| `lo > 0` (low end of the range above zero) | `ahead: even the low end of the range is positive` | **pass** |
| `hi < 0` (high end of the range below zero) | `behind: even the high end of the range is negative` | **fail** |
| otherwise | `undecided: the range includes zero` | **in-between** |

Four things the code does that matter for this file:

- **The comparison is with zero, not with the main books.** A book is "ahead" when it makes money per
  trade, not when it beats another rule. The file's own note says: "ahead if the low end of its 90% range
  per trade is above zero, behind if the high end is below zero".
- **It is a 90% range, not 95%, and it uses 1.645** (the bell-curve figure), not a t-test.
- **The verdict is not given once.** It is worked out again every 15 minutes after trade 30. The text can
  change at trade 31, 32 and so on. `engine15/telegram_notify.py` alerts "any book reaching 30 trades or
  changing its verdict".
- **The win rate (`won_pct`) is shown but plays no part in the verdict.**

Where each book's trades come from:

- `b_trail`: every file `out/live/shadow_trades_b_trail_<market>.csv`, eight markets together
  (`reports.scoreboard`, the `shadow_trades_*.csv` loop).
- `p8_fvg`: the closed rows the strategy book returns each step (`status == "CLOSED"`), six markets
  together (`reports.scoreboard`, `playbook_rows`; `engine15/playbook3.py` `step`).

The code read here is the laptop's copy. The server's copy is assumed to be the same (code is deployed
from the laptop, `HANDOFF.md` "Deploying code"). That was not checked: this task did not connect to the server.

**PROPOSED definition, so the moment cannot be chosen afterwards:** "the verdict at 30" is the verdict
text in the first `scoreboard.json` written by the server in which the book's `trades` is 30 or more.
(Two trades can close in one step, so the count may jump from 29 to 31.) That row is copied into section 8
of this file. Later changes of the text do not change it.

---

## 3. How much 30 trades can show

Thirty trades is a small sample. The charter says so in its own words: the scoreboard exists "so that a
lucky streak is not mistaken for an edge" (`engine15/reports.py`, `scoreboard` docstring), and "Forward
results decide. The history replay can reject an idea, never prove one" (`docs/CHARTER.md`, "Scoreboard").

The figures below were worked out for this file by simulation. They assume trades are independent and
bell-shaped. Real trades are neither, so the true uncertainty is larger.

**Win rate.** A 95% interval on a win rate from 30 trades is wide:

| Seen in 30 trades | The true rate could be |
|---|---|
| 15 wins (50%) | 33% to 67% |
| 18 wins (60%) | 42% to 75% |
| 27 wins (90%) | 74% to 97% |

And a win rate alone says little about profit. The main book wins about 1 trade in 5 and still earned
most in the history read, because its winners are 4 to 6 times its losers (`docs/CHARTER.md`, status
notes 13 Nov 2026).

**The "ahead" test.** To read "ahead" at 30 trades the average trade must be more than 0.30 times the
spread of the results (1.645 / sqrt(30) = 0.30).

- A book with **no edge at all** reads "ahead" at 30 trades about 5.5% of the time (1 time in 18), and
  "behind" about 5.5% of the time.
- Up to 33 books can appear on the scoreboard (the main books, the 14 shadow books in `shadows.CHALLENGERS`,
  the 18 strategy books in `reports.PLAYBOOK_MODULES`). If none had any edge, one or two would still be
  expected to read "ahead" by luck.
- A book with a **real but modest edge** is usually missed. If the true average is 0.1 of the spread, it
  reads "ahead" 14% of the time. At 0.2: 30%. At 0.3: 50%. It takes about 0.46 to be caught 4 times in 5.
- More trades help: an edge of 0.2 reads "ahead" 47% of the time at 60 trades and 64% at 100. An edge of
  0.3: 75% at 60 and 91% at 100.

**Looking too often.** If a no-edge book is checked after every trade from 30 to 100, it shows "ahead"
at some point 18% of the time (14% by trade 60). If it must read "ahead" at two fixed points, 30 and 60,
that falls to about 2%. This is why the tables below use fixed checkpoints and take no decision between them.

**What the formulas miss.**

- The record so far covers about one week (11 to 17 Nov 2026). One week can be one market mood.
- The markets move partly together (BTC and ETH most of all), so 30 trades hold fewer than 30 separate facts.
- A trailing stop makes many small wins and, now and then, a large loss. Thirty trades may not have
  met the large loss yet.

So: "ahead" at 30 means "worth a second look". "Behind" at 30 means "probably loses, check why".
Neither is proof. `CLAUDE.md` ("Rules"): never describe anything here as having a proven edge.

---

## 4. Book: `b_trail` (shadow book "B: trailing swing / 2 ATR stop after 1R")

### What it is

It is a paper copy of the main rule with a moving stop. Once a trade is ahead by its own risk (1R), the
stop follows the price instead of staying where it was set.

Exactly (`engine15/shadows.py`, module docstring, `CHALLENGERS`, and section "2c. the trailing stop" in `run`):

- **Entry: the main rule.** It reads the same odds, readings and bars as the main book at every 15-minute
  close and uses the same decision rule (`policy.decide`). It keeps its own $10,000 per market, its own
  position and its own idle clock. It started flat on 11 Nov 2026 (metals 05:30 UTC, crypto, USDJPY and oil
  05:45, the S&P 14:45; `data/shadow_state.json`, `groups`).
- **Exit: the one change.** The first stop is the main book's (3 x the 1-hour ATR from the fill;
  `config.py` `stop_units`). When a bar's high (for a long) has gone 1 stop-distance in favour
  (`TRAIL_ARM_R = 1.0`), the trail switches on. At each close the stop moves to the tighter of two levels:
  the close less 2 x ATR(14, 15m) (`TRAIL_ATR = 2.0`), or the last confirmed 15-minute swing low. It never
  moves back. Shorts mirror this. A stop-out of this kind is logged as `TRAIL`.
- Flips, fees, sizing and the must-be-positioned mandate are the main book's.

How it differs from its neighbours:

- **From the main book:** the main book's stop never moves. It exits only at that stop or on a flip
  (`THOUGHT_PROCESS.md`, "Now", "Exits").
- **From `b_targets`:** that book sells half at Target 1 and the rest at Target 2, and moves the stop to
  the entry price after Target 1. `b_trail` has no targets. It only moves the stop.

One correction to the brief. `b_trail` takes "the main book's own entries" only until its first early
exit. After a trail exit it is flat while the main book is still in its trade. It then enters again by the
same rule on its own clock. So it makes many more trades than the main book (history: 11,663 against 1,322;
`research/out/exits/trail_study.md`, "All markets together").

### What was registered, and when

- It has **no numbered hypothesis of its own** in `research/HYPOTHESES.md`. It was built on 11 Nov 2026
  under charter task B, "Exits" (`docs/CHARTER.md`, task table and "Status notes, 11 Nov 2026 (05:30 UTC)"
  and "(05:55 UTC)"). Its constants are in `shadows.py` ("declared once ... none tuned here").
- **No pass bar was fixed for it then.** The only rule on file is general: "Promotion is decided later on
  forward results (docs/CHARTER.md), never here" (`shadows.py` docstring). A pass bar specific to `b_trail`:
  not found in the project files.
- Its history, all in-sample and all negative:
  - 120 days, first read: -$8,670 against the main rule (`docs/CHARTER.md`, "Status notes, 11 Nov 2026 (05:55 UTC)").
  - 120 days, eight markets: -$6,830 (-8.5%), the worst book, against main +$6,114 (`research/out/challengers_all.md`).
  - 2020 to Nov 2026, eight markets: **-$48,808** against main **+$329,439**; worst fall -78%; ahead of main in
    0 of 8 markets (`research/out/exits/trail_study.md`, "All markets together"; `research/HYPOTHESES.md`,
    "H36 history read and one amendment").
- H36 (registered 13 Nov 2026) used `b_trail` as a comparison book, "already counted". H36's own forward
  rule covers its three new books, not `b_trail`.
- Two standing rules already apply to any exit challenger:
  - `THOUGHT_PROCESS.md`, "Scoring every trade": "promote the challenger only if it beats the incumbent on
    that part without lowering the total score over at least 50 trades". (Whether `engine15/scorecard.py`
    can score shadow trades: not found in the project files.)
  - The owner's decision of 13 Nov 2026 after H36: "Let the winner run". The main books take profit only by
    flipping (`docs/CHARTER.md`, "Status notes, 13 Nov 2026 (owner decisions through the day)").

### What the scoreboard will compute at 30 trades

The average dollar result of its pooled trades, the 90% range of section 2, and one of the three verdicts.
It will **not** compare `b_trail` with the main book. That comparison exists elsewhere, without any pass
line: `shadows.scoreboard` puts `vs_main_usd` on the page, the book's equity less the fresh main copy's
(shadow book `main`, started at the same moment).

For an exit rule the useful question is "does it make more than holding?", not "does it make more than
zero?". In a week when prices run one way, both can be above zero. The table below therefore adds the
comparison with the fresh main copy at the second check.

### PROPOSED decision table for `b_trail`

Checkpoints, fixed now: **30 trades**, a **second check at 60 trades**, a **last check at 100 trades**.
Each is the first server scoreboard at or past that count. (Section 7, line 4, offers a date floor for the
second check.) No decision is taken between checkpoints.

| Verdict at 30 | What happens |
|---|---|
| **ahead** (pass) | Nothing changes in the main books. `b_trail` runs on with the same rule. I write a short note: results by market, by exit reason, the largest loss, and `vs_main_usd`. No proposal to change anything is made at 30. The question goes to the second check. |
| **undecided** (in-between) | Nothing changes. It runs on to 60 trades. No note beyond the row in section 8. |
| **behind** (fail) | It keeps running unchanged while I write a post-mortem in the P1 form (below). Then I PROPOSE to the owner: retire it as P1 was, or keep it as a labelled reference. The owner decides. |

| At the second check (60 trades) | What happens |
|---|---|
| "ahead" at 30 **and** at 60, **and** all three conditions below hold | I PROPOSE to the owner that the trailing exit becomes the main books' exit in a **new engine version**. Only a proposal. See "What a proposal would contain". |
| "ahead" at 60 but not at 30 | No proposal yet. The same test is applied at 100 trades with 60 and 100 as the two checkpoints. |
| "ahead" but a condition fails | No proposal. It stays a shadow book. It is read once more at 100 trades, for the record. |
| "undecided" | It runs on to 100 trades. No decision. |
| "behind" | Post-mortem, then the retire-or-reference proposal, as in the first table. |

The three conditions, all measured against the fresh main copy over the same time:

1. Its total profit is above the fresh main copy's (`vs_main_usd` above zero).
2. It is ahead of the fresh main copy in at least 5 of the 8 markets. This is H36's own bar for "better
   than holding" (`research/HYPOTHESES.md`, H36, "What counts as better than holding").
3. It has at least 50 closed trades, the standing minimum in `THOUGHT_PROCESS.md`. (60 meets it.)

Reported beside them, not as conditions: the worst fall in equity against main's (the forward scoreboard
does not compute it; it would be worked out from the trade files), the share of profit from the largest
trades, and the history result.

After 100 trades there is no further decision point unless the owner sets one in writing first.

**What a proposal would contain** (if the conditions are met):

- The forward numbers and the history numbers side by side. The history says the opposite (-$48,808, 0 of 8
  markets). The owner has asked for forward data points rather than backtest gating (`research/HYPOTHESES.md`,
  H36: "the owner wants forward data points, not backtest gating"). The charter also says history "can reject
  an idea". Both go in front of the owner.
- A new hypothesis written in `research/HYPOTHESES.md` first, with its own forward rule.
- A new engine version. The engine is at `think15-v5.2.4` (`engine15/config.py`). `CLAUDE.md` ("Rules"):
  changing a constant "is a new version of the thought process". The number it would take: not fixed here.
- The old hold rule kept running as a shadow book, so the two can still be compared
  (`research/out/exits/trail_study.md`, "If the owner switches the main book (v5.2): what it needs", step 4).
- Still paper only.

Until the owner says yes to such a proposal, "Let the winner run" stands.

**"Retire as P1 was"** means the precedent in `engine15/playbook.py` (`RETIRED`) and `research/HYPOTHESES.md`
("H6 retired (owner, 15 Nov 2026, 06:15 UTC)"):

1. A post-mortem first, in the form of `research/out/p1_postmortem.md`: is the code doing what the rule
   says; the numbers; what went wrong, largest cause first; what a new version would change.
2. The owner's word ("Retire it").
3. A time stamp. No trade entered from the stamp on counts. The record before it is kept, frozen, and
   stays on the page. Failures stay on file (`docs/CHARTER.md`, task L3).

`RETIRED` exists only in `playbook.py` today. `shadows.py` and `playbook3.py` have no such switch. Retiring
either book would need the same few lines added there. That is a code change for the owner to approve at
that time, not now.

---

## 5. Book: `p8_fvg` (strategy book P8, "Fair value gap / order block", hypothesis H13)

### What it is

It is a stand-alone paper strategy, separate from the main books. It looks for a sharp three-candle move
that leaves a price gap, waits for the price to come back into the gap, and then trades in the direction of
the first move.

Exactly (`engine15/playbook3.py`, module docstring, `RULES["p8_fvg"]`, `fvg_setups`; `docs/PLAYBOOK3.md`, "P8"):

- The gap: candle 1's high is below candle 3's low (bullish; the mirror for bearish). The middle candle
  moves that way. The gap is at least 1.0 x ATR(14, 15m).
- The entry: the first bar within 12 hours that trades back into the gap, if it does not close through the
  gap's far edge. Enter at the next bar's open.
- The exit: stop beyond the far edge plus 0.25 of the hourly ATR. Half is sold at the first move's extreme,
  the rest at 2R or 1R past the extreme. The stop moves to the entry price after the first half. Out after
  32 bars (8 hours) at the latest.
- $10,000 a trade, each market's own fee, six markets: BTC, ETH, gold, silver, USDJPY, S&P 500. (Not oil.)

The book's title says "order block" too. The registered rule uses the gap only (`RULES`: `"zone": "fvg"`).
It does not use the main engine's odds, and it does not touch the main books.

### What was registered, and when

`research/HYPOTHESES.md`, "H13. Fair value gap retest (registered 11 Nov 2026)":

- **History:** 16 variants tried, "none positive after costs in either half". The registered rule: -0.166R
  and -0.199R a trade after costs in the two halves, about zero before costs (+0.012R / -0.010R). Fees take
  about 0.2R a trade because the stops are tight (`docs/PLAYBOOK3.md`, "P8", "Verdict: does not clear costs").
- **Why it runs anyway:** so that "the forward record, not the history, gives the verdict"
  (`playbook3.py`, comment above `RULES`).
- **A pass bar WAS fixed then.** Quoted: "Verdict rule, fixed now: after 200 forward trades or 30 days,
  whichever is later, keep it only if the average result is above +0.05R after costs, the profit factor is
  above 1.1, and at least 4 of 6 markets are positive. Otherwise retire it."
  (Profit factor: total dollars won divided by total dollars lost.)
- H13's own warning: "Why it may be nothing: about zero before costs, -0.2R after, on thousands of trades."

So `p8_fvg` has **two lines**: the scoreboard's general 30-trade line, and H13's own, stricter and later
line. Thirty days from registration is 11 Dec 2026. The date on which it will reach 200 trades: not found
in the project files (H13 expected "about 140 a month").

### What the scoreboard will compute at 30 trades

The average dollar result of its pooled trades after fees, the 90% range of section 2, and one of the three
verdicts. It will not compute H13's three tests. Average R and per-market results are in
`out/live/playbook.json` (`totals.avg_r`, `by_asset`). Profit factor is not in that file; it would be worked
out from the trade rows.

### PROPOSED decision table for `p8_fvg`

Checkpoints, fixed now: **30 trades** (the scoreboard, an interim reading) and **H13's own verdict** (the
later of 200 forward trades and 11 Dec 2026). H13's rule is not shortened, loosened or replaced by anything
that happens at 30.

| Verdict at 30 | What happens |
|---|---|
| **ahead** (pass) | It stays a separate paper book with the same rule. The row is recorded as "ahead at 30, interim". Nothing is proposed. Nothing feeds the main books. It runs on to H13's verdict. |
| **undecided** (in-between) | The same: it runs on unchanged to H13's verdict. No decision in between. |
| **behind** (fail) | It keeps running unchanged, as its own control, while I write a post-mortem in the P1 form. Then the owner chooses: retire it early as P1 was, or let it run to H13's verdict. If the owner gives no word, it runs to H13's verdict. |

| At H13's verdict (later of 200 trades and 11 Dec 2026) | What happens |
|---|---|
| All three of H13's tests pass | It is kept as a separate paper book. I PROPOSE the next step to the owner at that time. What "promotion" means for a strategy book: not found in the project files, so it will be the owner's call. The charter's review of 10 Feb 2027 asks "is any 15m book ahead of the yardstick?" and is the natural place for it. |
| Any of the three fails | "Otherwise retire it" (H13). Retired as P1 was: post-mortem, the owner's word, a stamp, the record kept. |

A pass here would still not be proof of an edge. With 16 variants tried on history and 83 across H11 to H17
(`research/HYPOTHESES.md`, opening count), one passing book can be luck.

Any improved version of the rule is a new hypothesis, registered first and tested on development history,
as H41 was for P1. It is never graded on these live trades.

---

## 6. What will NOT be done, whatever the result

1. **No real money.** Paper only. Nothing here places an order (`CLAUDE.md`, "Rules"; `docs/CHARTER.md`,
   "Unchanged by this charter").
2. **No change to the main books' rules** from either result alone. A change needs the owner's yes, a
   hypothesis registered first, and a new engine version.
3. **No tuning on the live trades.** The constants of `b_trail` (arm after 1R, 2 x ATR, the 15-minute swing)
   and of `p8_fvg` (1.0 x ATR gap, 12 hours, 0.25 ATR pad, 32 bars) stay as registered. A changed rule is a
   new book that starts from zero trades. The old trades are never re-graded under a new rule.
4. **No moving the line.** `MIN_TRADES = 30`, the 1.645 range and the three verdict texts are not edited
   after numbers are seen. The checkpoints in this file (30, 60, 100; H13's 200 trades or 30 days) are not
   moved either.
5. **No trimming the record.** No trade, market or day is dropped to change a verdict. Cuts such as
   "without ETH" may be reported beside the result, never used for it.
6. **No decision between checkpoints.** The page and the phone alerts will keep showing the numbers. They
   are not acted on until the next fixed checkpoint. The one exception is the owner's own word, recorded as
   such (as with P1, retired before its rule was reached).
7. **No calling a pass an edge.** "Ahead" is written as "ahead on N live trades", with the range beside it.
8. **No deleting a failure.** A retired book's record stays on the page and in the files.
9. **No hiding the history.** Any proposal shows the history result next to the forward one.

---

## 7. For the owner to approve

Each line was PROPOSED until answered. **Answered 17 Nov 2026: the owner approved all of them in one answer ("Approve all (Recommended)": all rules as drafted, including reading `b_trail`'s second check no earlier than 10 Dec).**

| # | Proposed rule | Yes / No |
|---|---|---|
| 1 | "The verdict at 30" is the first server scoreboard showing 30 or more trades for the book. Later changes of the text do not change it. | Yes (17 Nov 2026) |
| 2 | `b_trail` "ahead" at 30: nothing changes; a short note; the question goes to a second check at 60 trades. | Yes (17 Nov 2026) |
| 3 | `b_trail` second check: a proposal to the owner is made only if it is "ahead" at both checkpoints, beats the fresh main copy in total, and beats it in at least 5 of 8 markets. | Yes (17 Nov 2026) |
| 4 | Optional: the `b_trail` second check is read no earlier than 10 Dec 2026 (the charter's first review), so the record spans a month and not one week. | Yes (17 Nov 2026) |
| 5 | If line 3 is met, the proposal is: the trailing exit as the main books' exit in a new engine version, registered first, the hold rule kept as a shadow. Until the owner says yes to that, "Let the winner run" stands. | Yes (17 Nov 2026) |
| 6 | `b_trail` "behind" at any checkpoint: a post-mortem, then the owner chooses between retiring it as P1 was and keeping it as a labelled reference. | Yes (17 Nov 2026) |
| 7 | `b_trail` "undecided": it runs on to 60, then 100 trades. After 100 there is no further decision point unless the owner sets one in writing first. | Yes (17 Nov 2026) |
| 8 | `p8_fvg`: the 30-trade verdict is an interim reading. H13's registered rule (200 trades or 30 days; above +0.05R, profit factor above 1.1, 4 of 6 markets positive) still decides keep or retire. | Yes (17 Nov 2026) |
| 9 | `p8_fvg` "ahead" or "undecided" at 30: it stays a separate paper book, unchanged, to H13's verdict. | Yes (17 Nov 2026) |
| 10 | `p8_fvg` "behind" at 30: a post-mortem; the owner chooses early retirement or running to H13's verdict; with no word, it runs on. | Yes (17 Nov 2026) |
| 11 | `p8_fvg` passing H13's rule: kept as a paper book; the next step is put to the owner then (the 10 Feb 2027 review at the latest). | Yes (17 Nov 2026) |
| 12 | The nine "will NOT be done" points of section 6 hold for both books. | Yes (17 Nov 2026) |
| 13 | Retiring a shadow book or a batch-3 strategy book needs a small code change (a `RETIRED` stamp like P1's). It is asked for when needed, not approved here. | Yes (17 Nov 2026) |

---

## 8. Record (filled in when each checkpoint arrives; rows are added, never rewritten)

| Book | Checkpoint | Scoreboard written (UTC) | Trades | Net $ | Mean $ | 90% range $ | Won % | Verdict text | vs main $ (`b_trail`) | What was done | Owner's word |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `p8_fvg` | 30 (first server scoreboard seen with >= 30) | 2026-11-18 03:18 | 31 | -77.42 | -2.50 | -28.12 to +23.12 | 41.9 | undecided: the range includes zero | n/a | Rule 9: stays a separate paper book, unchanged, until H13's verdict (200 trades or 30 days). Disclosure: first seen at 31 trades (the 30th trade closed between my checks); the book passed 30 earlier in the evening of 17 Nov UTC. | approved rules (17 Nov 2026) |
| `b_trail` | 30 (first server scoreboard seen with >= 30) | 2026-11-18 13:18 | 31 | +6,330.69 | +204.22 | +138.45 to +269.98 | 83.9 | ahead: even the low end of the range is positive | +831 (marked, since 2026-11-11 05:30) | Rule 2: nothing changes; this note; the question goes to the second check at 60 trades, read no earlier than 10 Dec 2026 (rules 3-4). Disclosure: first seen at 31 trades. | approved rules (17 Nov 2026) |
| | | | | | | | | | | | |

---

## 9. Where the files differ from the brief for this task

1. **No baseline.** The 30-trade verdict compares each book with zero. It does not compare `b_trail` with
   the main book. The comparison with main (`vs_main_usd`) is on the page with no pass line.
2. **The verdict texts are "ahead", "behind" and "undecided"**, from a 90% range built with 1.645. There
   is no t-test and no "pass" or "fail" wording in the code.
3. **The verdict keeps being recomputed after 30 trades.** It is not a one-time ruling. Section 2 proposes
   a definition to pin it.
4. **`p8_fvg` already has a registered verdict rule** (H13: 200 trades or 30 days, three tests). The
   30-trade line is not the one H13 registered.
5. **`b_trail` has no numbered hypothesis and no pass bar of its own.** Its history is negative in every read.
6. **`b_trail` is an exit variant, but it does not keep to the main book's entries.** After its first early
   exit it re-enters on its own clock from the same odds.
7. **`p8_fvg` trades six markets, not eight**, and its registered rule uses the gap only, not the order block.
8. **Version.** `engine15/config.py` says `think15-v5.2.4` (17 Nov 2026). `THOUGHT_PROCESS.md` "Now" and
   `HANDOFF.md` still say v5.2.2.

## 10. Book: `b_targets` (the Setups book): the read at 30 trades (approved 22 Nov 2026)

**Why this section exists.** The records said the Setups book is "read at 30 closed forward trades" (docs/CHARTER.md,
research/HYPOTHESES.md) without fixing the moment of the read, what follows from each outcome, or how the entry change
of think15-v5.2.9 is handled. Section 7's rule 1 pinned the moment only for `b_trail` and `p8_fvg`. An agent preparing
the forward reads found the gap on 22 Nov 2026 (`research/out/forward_reads/status_20261122.md`).

**Disclosure: what had been seen when this was fixed.** The book stood at 29 closed trades (server scoreboard of
2026-11-22 11:03 UTC: "too few trades to judge (29 of 30)"), realised +$7,186 on paper, +27.25R, 22 wins; every one of
the 29 with its market's own 30-day move (H65). So this rule was written one trade before the count and with the
record known. It fixes how the read is made; it cannot make the read independent of what was already seen.

**The rule. Proposed 22 Nov 2026; the owner, in this project, asked "Approve the proposed wording for the Setups
book's 30-trade read?": "Approve it".**
1. The read at 30 is the first server scoreboard row for `b_targets` showing 30 or more trades, copied as it stands.
   Later changes of the text do not change it.
2. It pools all eight markets and compares each trade with zero (section 2's rule: ahead, behind or undecided from the
   90% range). BTC and ETH alone are shown beside it, not as the rule.
3. Trades from before and after think15-v5.2.9 are pooled; v5.2.9's own BTC and ETH trades are also reported apart.
4. Ahead or undecided: nothing changes, and a second check follows at 60 trades.
5. Behind: a post-mortem, then the owner decides.
6. Nothing changes the vault feed without the owner's word in this project.

A trade counts when it is fully closed (a half taken at Target 1 is not a trade; `reports.per_entry`). The 30th may be
any of the eight markets. Section 3 applies: 30 trades opened within two weeks of one market spell, many of them at the
same hours, show less than 30 independent results would.

**Record of the read at 30 (b_targets), made by section 10's rule.** The 30th closed trade was gold (XAUUSD), a short
opened 2026-11-20 03:30 UTC by the forced rule and stopped 2026-11-23 01:00 UTC (-$271.41, -1.02R). The first server
scoreboard row with 30 trades, copied as it stands (the scoreboard of 2026-11-23 04:27 UTC still holds 30 trades, and
the row is computed from those 30 trades only, so it is the same row the first such scoreboard showed):
`{"trades": 30, "net_usd": 6914.58, "mean_usd": 230.49, "range90_usd": [104.95, 356.02], "verdict": "ahead: even the
low end of the range is positive", "won_pct": 73.3}`.
- BTC and ETH alone, beside it (not the rule): 11 trades, 9 won, +$3,381.40, +10.77R.
- think15-v5.2.9's own BTC and ETH trades: none closed yet (both positions open were opened 2026-11-21 14:30 UTC).
- By rule 4: **ahead, so nothing changes, and a second check follows at 60 trades.**
- Section 3 applies in full: the 30 trades were opened within two weeks of one market spell (24 of them shorts in
  falling markets, all with their market's own 30-day move, per H65), many at the same hours, so they show much less
  than 30 independent results would; on history (H65, H87, H89) the same rule is flat per trade, loses in about half of
  12-month stretches, and its result rests on single years.
