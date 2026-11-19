# RL for Mind 15: what we learned and where it fits next (20 Nov 2026)

Owner, 20 Nov 2026: "Learn how to apply RL and utilise RL model for the AI engine". This note puts together six RL
phases and four loop rounds (`docs/RL.md`, `research/rl_loop/LOOP_RL.md`) and proposes where RL can actually help now.
It is a plan only. Nothing here is built, and nothing changes the live engine or what is sent to the VIP vault.

## 1. RL in one page

- **The idea.** An agent sees a **state** (the market readings, its own position), picks an **action** (long, short,
  flat, a size, an exit), gets a **reward** (net P&L after fees), and changes its choices so the total reward grows.
- **Three levels, from simple to hard:**
  1. **Online learning with full information ("experts").** Every option's result is seen after each round, so the
     learner just shifts weight toward what has been working. Mind 15 already does this: card trust is an
     exponential-weights rule (`engine15/model.py:137` `trust_path`, 10-day half-life, 40% cap). It learns fast and it
     is safe, because it can only re-weight options that exist.
  2. **Contextual bandit.** One decision at a time, a reward comes back, and the best choice depends on the context
     (regime, volatility, time of day). There is no long chain of consequences.
  3. **Full RL.** Today's action changes tomorrow's state: holding a position, paying fees to change it, stops, a
     drawdown brake. PPO, DQN and Q-learning live here. It needs by far the most data.
- **What paper trading changes.** A paper book does not move the market. So for every bar, every action's reward is
  known exactly, and "RL on direction" reduces to *predict the next move, then trade only when the prediction beats
  the round-trip cost*. Phase 3 found this and built the agent that way (`engine15/rl/qagent.py`).

## 2. What six phases taught us (BTC/ETH, 15m, out of sample, 0.10% a side)

| Lesson | Evidence |
|---|---|
| On 15m, **costs are the opponent**. | A random agent trading about daily loses 87-95% to costs alone (Phase 1). |
| **Deep RL (PPO) failed** even to learn a planted edge. | Phase 2: -99.6%, about 600 trades a year. It failed the learnability check (Phase 3). |
| **Data size decides it.** | A 9-month window finds nothing. 6 years pooled over BTC+ETH finds an edge before costs (BTC gross Sharpe ~0.78, ETH ~1.1; Phase 4). |
| **The Mind 15 readings carry the signal, not trend.** | Without the readings: Sharpe 0.14; with them: 0.58. Flow, volatility regime, basis and levels lead (Phase 4/5 ablations). |
| **After fees it still trails holding on BTC.** | Phase 4 primary net 0.48 vs buy-and-hold 0.64. Phase 6 reached 0.87, but much of that is the trend fallback, chosen with hindsight. |
| **More rounds now hurt.** | Each tried variant raises the significance bar (Bonferroni). Round 4: no pass, and no round 5 is proposed. |

Forward paper (scoreboard of 19 Nov, judged at 30 trades): `p5_rlq` 5 trades +$212, `p6_mtrend` 2 trades +$90,
`p6_p4trend` 2 trades +$425. All are far too early to judge, and all are NOT passed.

**The takeaway:** RL as a *direction picker every 15 minutes* has been tried thoroughly and keeps losing to costs.
RL is better used for the decisions *around* the engine's calls, where results come back quickly and every option
can be scored.

## 3. Where RL fits next (ranked)

### R1. Exit and join learner for setups (recommended first)

- **Decision.** For each setup the engine opens: how to manage it. The arms are the exit rules the shadows already
  run (planned targets, `b_trail`, break-even after T1, EMA20 or SMA20 trail after T1, hold to flip). Later it could
  also choose join at market vs wait for a limit, in the spirit of the hybrid join rule.
- **Why it learns fast.** The bars are known, so **every arm's result can be computed for every setup**: a single
  setup grades all five exits at once. That is full information (level 1), the same kind of learning card trust
  already uses. A bandit would see only one arm per setup.
- **Context.** A few readings Phase 4/5 showed carry signal: volatility regime (`vol_rank`), trend agreement
  (`tr_4h`/`tr_1d`), room to the next level (`sr_room`), the market group. Begin with one weight table per regime
  bucket (about 4-6 buckets). Adding a linear model comes later, and only if the buckets run short of data.
- **Reward.** Net R-multiple after fees, per setup.
- **Baseline to beat.** The best *single* exit rule over the same setups. H36 found that holding beat every trail
  in history, so the learner only adds value if the right exit **depends on context**. An exponential-weights
  learner is guaranteed to end close to the best single rule. Anything better is the contextual part, and that is
  the part that has to show itself in forward results.
- **How it runs.** First, a replay over history to set the starting weights, labelled warm-up, not proof. Then a
  forward shadow book `b_learn` on the scoreboard, judged at 30 and 60 trades under the same verdict rules as
  `b_trail` (`research/VERDICT_RULES.md`). It is register-first: hypothesis H-number in `research/HYPOTHESES.md`.
- **VIP.** The vault keeps receiving today's setups book. Anything the learner changes in what is sent needs the
  owner's word in this project (CLAUDE.md rule), and only after a forward verdict.

### R2. Book allocator

- **Decision.** Each day, how much paper capital each forward book gets: main, shadows, playbooks, RL books.
- **Method.** Thompson sampling or exponential weights on each book's daily net return, using forward trades only.
  Caps: no book above 25%, and an always-on floor so no book is starved before it reaches 30 trades.
- **Why.** About 30 books run forward and a few are separating already (`b_trail` *ahead* at 33 trades; `p10_round`
  and `p1_liqhunt` *behind*). The allocator routes paper capital to what is working forward and away from what isn't.
  It cannot create an edge that none of the books has.
- **How it runs.** A paper book `a_alloc` on the Books tab, with the equal-weight mix of the same books as its
  yardstick.

### R3. Trust that depends on the regime

- **Decision.** The card weights the engine already learns, kept separately per regime bucket (trend or range,
  high or low volatility) instead of one set for everything.
- **Method.** The existing `trust_path`, run once per bucket (same half-life, same 40% cap), as a shadow mind.
  This is the smallest change of the three.
- **Risk.** Each bucket sees fewer graded calls, so the weights get noisier. The forward shadow is the test.

### Not recommended now

- **RL round 5 on direction, deep RL (PPO/DQN/transformers), offline RL (CQL/IQL).** The record above says these
  need more independent data than we have. Revisit only with a genuinely new input (e.g. paid liquidations, tested
  alone first), as agreed on 14 Nov.

## 4. How each would be built (same discipline as Phases 1-6)

1. Register the hypothesis and its verdict rule before any number is seen.
2. Closed bars only. Every reading goes through `data.htf_on_15`, plus a truncation test (the result must not change
   when future bars are removed).
3. The same cost model as the books (0.10% a side; 0.05% shown alongside).
4. The replay is warm-up only. The verdict comes from forward trades on the scoreboard.
5. Light in the live step: the learner only updates a small weight table each step. No training runs inside the step.
6. Deploy to the Singapore box with `tools/deploy.sh`, as usual.

Rough size: R1 is 1-2 days of build plus tests (most of the exit logic already exists in `engine15/shadows.py` and
`engine15/exits.py`). R2 is about 1 day. R3 is about half a day.
