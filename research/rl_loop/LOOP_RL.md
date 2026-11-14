# RL strategy loop ("Phase 6 core strategy"): target, rules, rounds

Paper research only. Code: `research/rl_loop/`. State: `research/out/rl_loop/loop_state.json`. Progress log:
`research/out/rl_loop/progress.log`. Reports: `research/out/rl_loop/round<N>_report.md`.

**Owner's request (13 Nov 2026):** "The phase 6 agent need continue furnish its core strategy so its return can outperform
btc buy and hold. Create a loop task to harness this until achieve the performance return result while not compromise on
its sharpe ratio." Background: the owner rejected loosened pass rules before ("I want a strict outperforming buy and
hold"). Nothing below may be relaxed after a result is seen; a rule that fails is reported, not changed.

**FROZEN 13 Nov 2026, 04:10 UTC, before any loop result existed** (no round-1 variant had been coded or evaluated; the
only numbers known were Phase 4-6's published ones and the Phase 6 primary's own per-seed run data).

## The agent being improved

The Phase 6 primary `m_trend` (`configs/rl/phase6.yaml`, frozen; `research/out/rl/phase6_report.md`): pooled BTC+ETH Q
agent with the missed-opportunity reward, 25 walk-forward folds (2020-10-01 .. 2026-11-11, out of sample), seeds 0, 1, 2;
a fold whose validation net Sharpe is under 0.5 holds the daily 30-day momentum position (the "trend fallback"); Phase 3
risk manager; perp accounting. BTC, 0.10% a side, seed mean: net +458.6%, Sharpe 0.87 (seeds 1.04 / 0.73 / 0.82), max DD
47%, 178 trades and 84 turnover a year. Its trained fold models (`research/out/rl/models6/b6a25c5d/r_missed`) are reused
by any variant that changes only execution, accounting or sizing; a variant that changes the reward or the inputs
retrains (and costs ~2 h per reward setting on this laptop).

## Target (a variant PASSES only if every rule below holds; nothing is averaged away)

Common frame: out-of-sample walk-forward over the same span and folds as Phase 4-6 (25 folds, 2020-10-01 .. 2026-11-11,
each fold's model trained only before its window), after 0.10% a side, half spread 0.5 bp, slippage 0.10 x 96-bar vol and
funding, seeds 0, 1, 2. "Seed mean" = the arithmetic mean over the three seeds (as Phase 6 reports). The yardstick is
**BTC SPOT buy-and-hold** over the same span (1x long from the first out-of-sample bar, one fee, no funding): full span
+583.9%, CAGR 36.9%, Sharpe 0.82, max DD 77%; to 2025-11-11 +879.7%, Sharpe 1.03, max DD 77%.

**BTC headline (full span 2020-10-01 .. 2026-11-11):**
- T1 return: seed-mean net total return strictly above spot buy-and-hold's, AND the mean of the three seeds' CAGRs strictly
  above spot buy-and-hold's CAGR (the second is stricter: one lucky seed cannot carry it).
- T2 Sharpe: seed-mean net Sharpe >= 0.87 (the Phase 6 primary's: "not compromise on its Sharpe") AND strictly above spot
  buy-and-hold's; AND every seed's net Sharpe strictly above spot buy-and-hold's.
- T3 drawdown: every seed's max drawdown no worse than spot buy-and-hold's.

**BTC sub-span (2020-10-01 .. 2025-11-11, the 21 folds that end by then):**
- T4: T1-T3 again against spot buy-and-hold over the sub-span, with the Sharpe floor set to the Phase 6 primary's own
  sub-span seed mean (1.05; it must also be strictly above buy-and-hold's 1.03, and every seed above 1.03).

**Strictness carried from `research/harness/LOOP.md` (round-2 rules), BTC full span:**
- S1 fold share: the seed-mean Sharpe of a fold above spot buy-and-hold's Sharpe in that fold in at least half of the 25
  folds (per-seed shares and the sub-span share are reported too).
- S2 no `fee_only_at_0.05`: not (beats spot buy-and-hold at 0.05% a side and not at 0.10%), "beats" = seed-mean Sharpe and
  Calmar both above buy-and-hold's.
- S3 no `high_turnover`: every seed at most 100 position changes (trades) a year, LOOP.md's definition, AND at most 100
  turnover a year (Phase 4's flag). (The Phase 6 primary itself makes 152-210 trades a year: this rule binds.)
- S4 significance: paired block bootstrap of the daily Sharpe gap over spot buy-and-hold (`research/harness/core.py`
  `boot_sharpe_diff_z`: daily log returns, block 20, 2,000 draws, p from the bootstrap standard error, one-sided) on the
  seed-mean book (per-bar mean of the three seeds' net returns), p <= 0.05 / N, **N = all RL variants tried, cumulative:
  Phase 6's 8 + every variant of this loop so far** (round 1 graded with N = 8 + its own count). The deflated-Sharpe
  probability (`core.deflated_sharpe`, N trials) is reported; so is the p threshold if the strategy loop's 1,910 were added.
- S5 calendar-year net returns of every variant are shown next to spot buy-and-hold's (reported, not a pass rule).

**ETH guard ("not compromise"), the same frozen procedure on ETHUSDT, full span:**
- E1 seed-mean net Sharpe >= 0.96 (the Phase 6 primary's ETH seed mean).
- E2 seed-mean net total return AND mean of seed CAGRs strictly above ETH spot buy-and-hold's (+470.6%, CAGR 33.0%).
- E3 every seed's max drawdown no worse than ETH spot buy-and-hold's (81%) (LOOP.md's `eth_fails` drawdown leg).
If E1 is the only failing rule of a variant, that is reported plainly as a fail; the rule is not changed.

Floors quoted to two decimals (0.87, 1.05, 0.96) are applied as max(quoted, the unrounded Phase 6 seed mean from
`research/out/rl/runs/phase6_20261112T141341Z_30a4dd4f/phase6_full.json`), so rounding never loosens a floor.

Leverage note (stated in every report that uses it): exposure above 1x raises return and drawdown together; it leaves
Sharpe unchanged only before costs. After fees, slippage and the funding paid on the part above 1x, leverage lowers Sharpe
unless the extra exposure is placed where the edge is larger.

## Honesty

- **No historical span is unseen for RL any more.** Phase 4 scored every test window through 2026-11-11; Phase 5 and 6 were
  designed after that, and this loop is designed after Phase 6's per-fold results. The trend fallback itself was chosen
  with hindsight. A historical pass is therefore **not proof of an edge**.
- A pass becomes **a proposal** for a forward paper book (the session lead and the owner decide; nothing is wired in by a
  round). It is confirmed only at **30 forward trades** on paper. Mind 15 is paper only: nothing here places orders.
- Every result states the cumulative number of RL variants tried (Phase 6's 8 + this loop's).
- Instrument accounting is stated wherever used: "spot longs" = the long part up to 1x is held as spot (no funding); shorts
  and any exposure above 1x are perp (funding paid or received). This is the strategy loop's rule A/B accounting
  (`research/harness/core.Market.funded`, `engine15/playbook4.py`). Live Mind 15 trades perps; the difference is disclosed.

## Rounds

1. Each round registers its variants (exact rule, parameters) here and in `research/HYPOTHESES.md` **before** any of its
   results is computed; at most 6 variants a round.
2. No re-running a round after seeing its results; a changed idea is a new variant in a later round. Code bugs found after
   a run are fixed and disclosed in the report, with both numbers if any result changed.
3. Before grading, the round's harness must reproduce the Phase 6 primary exactly (perp accounting, unchanged execution):
   BTC +458.6% / Sharpe 0.87 (difference < 0.5% return, < 0.005 Sharpe); otherwise the round stops.
4. The state file records variants tried, results and the next round's proposals. Proposals are written after a round,
   not run, until the next round is registered.
5. Heavy jobs: one at a time, below-normal priority, start only with >= 1,500 MB free, pause under 600 MB; the shared lock
   `research/out/heavy_job.lock` (created O_CREAT|O_EXCL, holds PID + label; a dead PID's lock is taken over); never train
   while `research/out/rl/forward5/update.lock` is held. The live loop, `web/`, `out/live/` and the forward books
   (playbook4/5/6) are never touched.

## Round log

| Round | Date | Variants (this round / cumulative incl. Phase 6's 8) | Best BTC (seed mean, full span) | Passes | Verdict |
|---|---|---|---|---|---|
| 1 | 13 Nov 2026 | 5 / 13 | V5 spot_lean_blend +1,127%, Sharpe 1.03, DD 54% (B&H spot +584%, 0.82, 77%); V2 spot_lean +642%, 0.96, fold share 52% | none | No pass. V3-V5 meet 19 of 21 rules (all return, Sharpe, drawdown, sub-span, turnover, ETH rules) and fail fold share (36-40%) and significance (p 0.26-0.35; edge needed ~1.2, seen +0.18 to +0.36). V2 fails sub-span return and significance. Report: `research/out/rl_loop/round1_report.md`. |
| 2 | 13 Nov 2026 | 6 / 19 | R2-f retrain_spot_longlever +1,574%, Sharpe 1.09, DD 54% (worst seed 60%); R2-b blend_125 +1,073%, 1.06, 48%; R2-d retrain_spot_lean +867%, 1.03, fold share 48% | none | No pass. R2-b, c, e, f meet 19 of 21 (fail fold share 32-44% and significance); R2-d 15/21 (fold share 48%, seed 2 Sharpe 0.82, sub-span return); R2-a 17/21 (218 trades/yr: the funding cap flips the request at each settlement). Best p 0.151 vs 0.00263 (edge +0.41 vs ~1.1 needed). Retrained agent: gain mostly from more fallback folds, ETH worse. Report: `research/out/rl_loop/round2_report.md`. |
| 3 | 13 Nov 2026 | 4 / 23 | R3-b core_riskoff_125 +1,428%, Sharpe 1.14, DD 57% (worst seed 60%), 44 trades/yr; R3-c committee_riskoff +710%, 1.09, fold share 52% | none | No pass. R3-b 19/21 (fails fold share 40% and significance); R3-c 18/21 (passes fold share 13/25 with 4 bull folds; fails sub-span return +746% vs +880% and significance); R3-a 17/21; R3-d 18/21 (ETH Sharpe 0.93 < 0.962). Long core: SE of the Sharpe gap 0.22-0.26 (was 0.37-0.44), edge needed 0.64-0.73, seen +0.40 to +0.44, p 0.033-0.044 vs 0.00217. Round 2's proposals replaced (disclosed). Report: `research/out/rl_loop/round3_report.md`. |

Running count of RL variants: **23** (Phase 6's 8 + round 1's 5 + round 2's 6 + round 3's 4; round 3 registered 13 Nov 2026,
08:02 UTC, run 10:13 UTC). Round 4 proposals: `research/out/rl_loop/loop_state.json` (not registered, not run).

## Round 1 (registered 13 Nov 2026, 04:10 UTC, before any round-1 code ran)

All five reuse the trained `m_trend` fold models (r_missed, trend fallback) unchanged: the agent's Q values and its own
decisions (`policy3.decide`, agent state = its own last action) are exactly Phase 6's except where "min hold" says
otherwise. What changes is how a decision becomes an executed position and how it is accounted. Notation: `a` = the
agent's decided action in {-1, -0.5, 0, 0.5, 1} (in a fallback fold, the daily momentum position); `s = sign(a)`;
`m` = the frozen daily 30-day momentum sign at the same close (features3 `mom_signal`, +1 / -1 / 0); risk manager = the
Phase 3 manager as configured in Phase 4 (vol target 60% a year on the 7-day realised vol, size = min(1, 0.60 / vol),
drawdown brake x0.75 at 20% and x0.50 at 30% from the 90-day rolling peak; a new request or a request of 0 executes at
once), with the executed position = request x size, so a request of 1.5 can reach 1.5x. In every variant the risk
manager's equity marks use the variant's own accounting (spot longs).

- **V1 `spot`** (accounting only): request = a; min hold 4 bars (Phase 6's); re-size band 0.20 (Phase 6's). Spot longs.
  Why: perp funding on longs is the single largest drag (perp buy-and-hold +249% vs spot +584%); this isolates it.
- **V2 `spot_lean`** (cost cut): request = s (the agent's side at full vol-targeted size: a half-size choice becomes full
  size, so size-only flips stop trading); min hold 16 bars (4 h; whipsaws inside 4 h are refused); re-size band 0.40.
  Spot longs. Why: 178 trades a year and 15% a year of cost drag; LOOP.md's 100-trades rule binds.
- **V3 `spot_lean_agree`** (sizing): as V2, but request = 1.5 s when s = m (agent and daily trend agree), else s.
  Drawdown brake kept. The long part above 1x is perp (pays funding). Why: put the extra exposure where the agent and the
  trend agree; return up, drawdown checked against spot buy-and-hold's.
- **V4 `spot_lean_agree_veto`** (sizing + trend veto): as V3, but request = 0 when s != m (a counter-trend position is
  refused; the book is flat instead). Why: counter-trend positions are the likely losers in bull folds, where the fold
  share fails.
- **V5 `spot_lean_blend`** (ensemble instead of a hard fallback): as V2, but request = clip(s + 0.5 m, -1.5, 1.5): 1.5 when
  agent and trend agree, 0.5 on the agent's side when they disagree, 0.5 m when the agent is flat. Why: the loop found the
  daily trend held as spot to be the real edge (H29/H30); a blend keeps the agent's view and the trend's.

V3-V5 differ only in what happens when agent and trend disagree (full agent side / flat / half agent side) and when the
agent is flat (flat / flat / half trend). In a fallback fold a = the momentum position, so s = m and V3-V5 hold momentum at
1.5x request there. Reference (not a variant, not counted): the Phase 6 primary reproduced with perp accounting.

Cumulative RL variants after round 1: 8 (Phase 6) + 5 = **13**; significance threshold p <= 0.05 / 13 = 0.0038.

## Round 2 (registered 13 Nov 2026, 04:31 UTC, before any round-2 code ran or any round-2 number existed)

Aim: the two binding rules, S1 fold share and S4 significance. Same frame, rules, yardstick, seeds, folds, costs and
grading as round 1 (nothing above is changed); harness `research/rl_loop/round2.py`, which reuses round 1's
(`round1.py`: risk manager with spot accounting, metrics, grading) and must again reproduce the Phase 6 primary (rule 3)
before anything is graded. Notation as round 1 (a, s = sign(a), m = daily 30-day momentum sign; V2 execution = request
s-based, min hold 16 bars, re-size band 0.40, spot longs, part above 1x on perp; V5 request = clip(s + 0.5 m, -1.5, 1.5)).
Six variants; cumulative RL variants after round 2: 13 + 6 = **19**; significance threshold p <= 0.05 / 19 = 0.00263.

Execution-only (Phase 6's `m_trend` fold models reused unchanged, as round 1):
- **R2-a `blend_fundcap`**: V5's request r, but the part beyond 1x only where funding makes it cheap: r > 1 is capped
  at 1.0 unless the latest settled funding rate (at or before the bar's close) is <= the median of the last 270
  settlements (min 90; H34's rule); r < -1 is capped at -1.0 unless that rate is >= the median (a short receives
  funding when it is high). Why: funding peaks in strong bull runs, so V3-V5's leverage is most expensive exactly in the
  bull folds where fold share is lost; lever only where it is cheap.
- **R2-b `blend_125`**: V2 execution with request clip(s + 0.25 m, -1.25, 1.25) (agree 1.25, disagree 0.75, agent flat
  0.25 m). Why: between V2 (fold share 52%, sub-span return short of buy-and-hold) and V5 (return clear, fold share
  36%): the smallest tilt that might keep both.
- **R2-c `lean_longlever`**: V2 execution with request 1.5 when s = m = +1, else s (shorts and counter-trend longs at
  1x). Why: the short leg earns little on BTC (V2: +4%/yr from short bars) and 1.5x on it adds variance and funding more
  than return; lever only longs that agree with the trend.

Retrained agent (one new training run, `r_missed_spot`, models under `research/out/rl_loop/models_r2/`):
- **R2-d `retrain_spot_lean`**: Phase 6's r_missed training exactly (`learn6.q_fold6`: same data, inputs, 25 folds,
  seeds 0/1/2 with the same per-fold seeds seed x 1000 + fold, beta grid {0.25, 0.5, 1.0}, half-life grid, steps,
  patience, refit, trend fallback), with spot-long accounting everywhere the agent learns or is selected:
  (i) reward a x rpx - f(a) x rate, f(a) = funded part (long up to 1x unfunded, shorts and above 1x on perp;
  `qagent.funding_mode: spot`); (ii) the missed-opportunity term's reference return on the same accounting,
  ref x rpx - min(ref, 0) x rate; (iii) the validation net Sharpe that chooses beta and sets the 0.5 fallback bar
  computed on the same accounting (net = a x rpx - f(a) x rate - c1 x |change|). Execution: V2 (request s).
  Why: Phase 6's agent was trained and selected as if every long paid perp funding (~5%/yr on BTC), so it learned the
  wrong trade-off between long, flat and short for the book it is scored as; only a better agent can move fold share
  and significance. (ii)-(iii) go beyond the round-1 proposal's reward-only change so the agent is trained AND selected
  on the accounting it is scored by; the fallback folds can therefore differ from Phase 6's.
- **R2-e `retrain_spot_blend`**: R2-d's models, V5 execution.
- **R2-f `retrain_spot_longlever`**: R2-d's models, R2-c execution (added: the retrained agent with the leverage rule
  least likely to cost fold share).

Compute: the retrain is ~2-4 h (Phase 6 took 243 min for two reward settings), below-normal priority, memory-gated
(start >= 1,500 MB free, pause < 600 MB), the shared heavy-job lock taken per seed and released between seeds, never
while `research/out/rl/forward5/update.lock` is held. Evaluation of all six at once after the retrain.

## Round 3 (registered 13 Nov 2026, 08:02 UTC, before any round-3 code ran or any round-3 number existed)

Aim: the two binding rules, S1 fold share (above all the 9 bull folds, where every variant so far wins at most 3) and S4
significance (the size of the Sharpe gap over spot buy-and-hold). Same frame, rules, yardstick, seeds, folds, costs and
grading as rounds 1-2 (nothing above is changed); harness `research/rl_loop/round3.py` / `round3_eval.py`, which reuse
round 1's and round 2's code and must again reproduce the Phase 6 primary (rule 3) before anything is graded.
Notation as before: s = sign of the agent's decided action (decisions with min hold 16, as V2), m = daily 30-day momentum
sign at the same close; "V2 execution" = min hold 16 bars, re-size band 0.40, the risk manager (vol target 60%, drawdown
brake), spot longs, any part above 1x on perp.

**Deviation, disclosed:** round 2's five proposals (fundcap_sticky, committee_lean, committee_longlever,
retrain_spot_lean_select and its longlever twin, in `loop_state.json`) are NOT run. Reason: the leverage and tilt variants
so far LOWERED fold share (V2 52% -> 36-44%), and every one of them keeps the agent's short leg, which earns only +4-7% a
year on BTC yet is the main reason the bull folds are lost; the proposals did not address either. The letters R3-a..d
below are new variants, not the proposals of the same letters.

The idea of the round: turn the agent from a long/short timer into a **risk-off switch on a long core**. Every fold the
book loses against buy-and-hold in a bull run is lost by being short or flat during it; every bear fold is won by being
out. A book that is long by default and goes flat only on a confirmed bearish signal (no shorts) is long through rallies
(a bull fold becomes a near-tie that any well-timed exit can win, instead of a near-certain loss) and out of confirmed
downtrends (a bear fold is won when flat beats a negative Sharpe). Its returns track buy-and-hold far more closely,
which shrinks the bootstrap standard error of the Sharpe gap, so a given edge is more significant. Prior, stated now: S4
is still not expected to pass (it needs an overlay with an information ratio of roughly 1.2 over buy-and-hold); the
realistic target is all 20 other rules. Risk, stated now: the 60% vol target holds a 1x request at min(1, 0.60 / vol),
below 1x in most high-vol rallies, so the return rules (T1, T4) may fail; R3-b is registered as the guard.

Execution-only (Phase 6's `m_trend` fold models, and for R3-c also round 2's `r_missed_spot` models, reused unchanged):
- **R3-a `core_riskoff`**: request r = 0 when s <= 0 AND m = -1 (the agent is not long and the daily trend is down),
  else r = 1. No shorts. V2 execution. In a fallback fold (a = the momentum position, s = m) this is long-only momentum.
- **R3-b `core_riskoff_125`**: R3-a with r = 1.25 instead of 1 (0 unchanged). The same as a 75% vol target capped at
  1.25x; the part above 1x is perp and pays funding. Guard for the return rules if the 1x core lags buy-and-hold.
- **R3-c `committee_riskoff`**: per seed k, r = 0 when at least two of three vote bearish: {Phase 6 agent seed k: s <= 0},
  {round 2 spot-trained agent seed k: s <= 0}, {m = -1}; else r = 1. V2 execution. Two independently trained agents and
  the trend; aims at seed dispersion (R2-d seeds 1.03 / 1.23 / 0.82) and at exits inside up-trends that both agents see.

Retrained agent (one new training run, `r_missed_longflat`, models under `research/out/rl_loop/models_r3/`):
- **R3-d `retrain_longflat_riskoff`**: Phase 6's r_missed training exactly as round 2's R2-d (`learn6.q_fold6`, same
  data, inputs, 25 folds, seeds 0/1/2 with per-fold seeds seed x 1000 + fold, beta grid {0.25, 0.5, 1.0}, half-life grid,
  steps, patience, refit, 0.5 fallback bar, trend fallback, spot-long accounting in reward and validation score) with
  two changes that train the agent for the job R3-a gives it: (i) actions {0, 0.5, 1} (long/flat only; no funding on any
  action under spot accounting); (ii) the missed-opportunity reference is the long part of the trend, max(ref, 0), so
  only a missed long move is charged (with shorts unavailable, charging a missed short would push the agent from flat
  into longs in a falling market). Validation: the greedy hold-4 policy on the long/flat actions (as R2-d). A fallback
  fold holds the action nearest the momentum position (long, or flat when momentum is short). Execution: R3-a's rule with
  this agent's side (s in {0, 1}): r = 0 when s = 0 AND m = -1, else r = 1; V2 execution.

Cumulative RL variants after round 3: 19 + 4 = **23**; significance threshold p <= 0.05 / 23 = 0.00217.
Compute: the retrain is ~3-4 h at below-normal priority with the shared heavy-job lock taken per seed and released between
seeds (90 s gaps), memory-gated more strictly than rule 5 (start >= 1,600 MB free, pause under 1,500 MB), never while
`research/out/rl/forward5/update.lock` is held. All four are evaluated at once after the retrain.
