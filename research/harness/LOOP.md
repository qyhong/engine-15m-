# Mind 15 research loop: target, rules, round log, holdout ledger

Paper research only. Code: `research/harness/`. State: `research/out/harness/loop_state.json`.

## Target (owner, 11 Nov 2026)

A strategy that **decides on the 15m clock** and earns a **CAGR of at least 25% a year** on its stitched
out-of-sample equity, net of 0.10%-a-side fees and funding (CAGR = (final / initial)^(1 / years) - 1 over the
evaluated span, not an average of yearly returns), with **max drawdown no worse than buy-and-hold's** over the same
span and **net return positive in more than half of the test folds**, flags clear. **10% CAGR is kept as a milestone.**

- Target history: first set at 10% CAGR; **raised to 25% CAGR by the owner before any holdout look** (no holdout look
  had been taken when it was raised, nor since). Confirmed as a CAGR basis the same day.
- 25% a year is above both BTC benchmarks over Oct 2020 - Nov 2026 (buy-and-hold about +22.7% a year, daily momentum
  about +22%, RL Phase 2 report), so a pass over that span means beating them. Over the development span alone (Oct 2020 -
  Nov 2025) buy-and-hold made +38.1% a year on BTC and +36.2% on ETH, so on development data 25% is below buy-and-hold.
- The holdout is 12 months, so a holdout CAGR is simply that year's return.

## Rules

1. **Sealed holdout: 2025-11-11 00:00 UTC to 2026-11-11.** All design, parameter choice and walk-forward reporting use
   bars before 2025-11-11 only (`core.load(..., dev_only=True)`, tested). Only `research/harness/holdout.py` reads the
   holdout. Round 1 never evaluated on the full span: the split was set before any harness result was computed.
   Caveat: the holdout is not perfectly blind. The RL Phase 2 report (written before the seal) shows buy-and-hold and
   momentum per quarter through Nov 2026, and the engine's replay has seen that price history. Nothing in round 1 used
   it; later rounds must not either.
2. **Rounds.** Each round registers its hypotheses in `research/HYPOTHESES.md` (exact rule, parameters, pass criteria)
   before any result, freezes them, and evaluates them walk-forward on development data (12-month train, 3-month test,
   roll 3 months, 21 folds, out of sample 2020-10-01 to 2025-11-11). Parameters are chosen only on each fold's train
   window. A candidate that meets the target there with flags clear is a **development pass**.
   Flags: `fold_share` (Sharpe above buy-and-hold's in fewer than half the folds), `fee_only_at_0.05` (beats buy-and-hold
   risk-adjusted only at 0.05%), `high_turnover` (> 100 position changes a year), `eth_fails` / `btc_fails` (the same
   procedure on the other coin has CAGR <= 0 or a deeper drawdown than its buy-and-hold), `not_significant` (paired
   block-bootstrap p-value of Sharpe minus buy-and-hold Sharpe above 0.05 / number of graded strategies in the round).
3. **Holdout looks.** Only development passes may be tested on the holdout, each **once**, frozen exactly as registered
   (`py -3 research/harness/holdout.py --candidate <id>`; it refuses anything else and writes the look to the ledger
   before computing). A holdout pass is a **historical pass**, reported with the number of variants and looks so far and
   a deflated-Sharpe caution.
4. **Forward confirmation.** A historical pass then runs forward on paper (a later step the owner approves) until it has
   30 trades. Only then is the target **confirmed**.
5. Every round adds its variants to the count below and to `loop_state.json`. No re-running a round after seeing its
   results; a changed idea is a new hypothesis in a new round.

### Development pass rules from round 2 on (owner: "I want a strict outperforming buy and hold. Achieve yearly min 25% CAGR."; set 11 Nov 2026 before any round-2 result; stricter than round 1, nothing loosened)

Each rule applies per coin: the BTC headline passes AND ETH under the same frozen rule passes. A two-coin book is graded
as one book against the same two-coin buy-and-hold book.

1. CAGR >= 25% net of 0.10%-a-side fees and funding.
2. CAGR strictly above buy-and-hold's CAGR over the same span.
3. Sharpe strictly above buy-and-hold's Sharpe, and max drawdown no worse than buy-and-hold's.
4. `fold_share` unchanged: Sharpe above buy-and-hold's in at least half the folds.
5. Significance: Bonferroni over ALL variants tried in the loop so far (cumulative across rounds); the p-value comes
   from the paired block bootstrap's standard error (normal approximation, since 2,000 draws cannot resolve p < 0.0005);
   the deflated-Sharpe probability is reported.
6. No `fee_only_at_0.05` flag and no `high_turnover` flag.
Kept from round 1: more than half the folds net positive; a 15m decision clock.
**Benchmark:** spot buy-and-hold (1x long, one fee, no funding) is the yardstick for rules 2-4. It is stricter than the
perpetual buy-and-hold used in round 1 (a perp long paid about 12% a year in funding on BTC). Perp buy-and-hold is
shown too. Every report shows calendar-year returns of each candidate next to buy-and-hold's.

## Round log

| Round | Date | Hypotheses | Variants (per asset / total) | Development result (BTC, 0.10%, CAGR) | Development passes | Holdout looks | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | 11 Nov 2026 | H20 filters on 15m bases; H21 filter ladder; H22 meta-labeling on daily momentum; H23 core-satellite; H24 replay trades (in-sample) | 919 / 1,838 | H20 -12.4%; H21 best +5.1% (ema L4); H22 +26.8% (ETH +35.8%); H23 +29.9% (ETH +41.6%); B&H +38.1%; momentum +25.4% | none | 0 | Thesis not supported. H22 meets CAGR, drawdown and positive-fold criteria on both coins but fails flags (fold_share, not_significant; BTC also fee_only_at_0.05). H23 fails drawdown on ETH. 10% milestone reached on CAGR only, not as a pass. |
| 2 | 11 Nov 2026 | H25 vol-targeted momentum; H26 momentum ensemble; H27 two-coin books; H28 fixed H22 variant; H29 spot long legs; H30 leveraged trend core; H31 vol-target + 15m trailing exit (strict rules, vs spot buy-and-hold) | 31 per coin + 2 books = 64 | best: H29 H30 1.5x/0x spot +78.0% (ETH +105.8%), Sharpe 1.19 / 1.25 vs spot B&H 1.03 / 0.96, DD 65% / 67% vs 77% / 81%; H29 H31 trail 4 ATR spot +67.6% / +71.9%, Sharpe 1.32 / 1.38; spot B&H +56.2% / +56.6%; perp B&H +37.9% / +36.1% | none | 0 | No pass. Several rules beat spot buy-and-hold on CAGR, Sharpe and drawdown on both coins, but every one fails fold_share (best 52% ETH, 43% BTC) and significance (Bonferroni 0.05/1,902 needs a Sharpe edge of about +0.8 to +1.6; best observed +0.58, p = 0.044). |
| 3 | 11 Nov 2026 | H32 vol-managed buy-and-hold core; H33 vol-target + trail with ensemble direction; H34 funding-aware leverage; H35 hour-of-day exposure (one variant each; other markets report only) | 4 per coin = 8 | H33 BTC +65.3% (Sharpe 1.30, DD 66%), ETH +38.0%; H34 BTC +64.6% (1.18, 56%), ETH +94.4% (1.26, 61%) but 110-118 trades/yr; H32 no Sharpe gain (BTC 1.01 vs 1.03); H35 -99%; spot B&H +56.2% / +56.6% | none | 0 | No pass. Best 5 of 8 rules. All fail fold share (best 43%) and significance (edge needed 0.69-1.47 vs best seen +0.58). Other markets: no rule beats buy-and-hold on Sharpe and drawdown on any. |

Running count of variants tried in the loop: **1,910** (1,838 in round 1 + 64 in round 2 + 8 in round 3; other-market runs are report-only and not counted). Holdout looks used: **0**.

**Status: PAUSED BY THE OWNER after round 3 (11 Nov 2026). Resume on request with round 4 below; nothing of round 4 has been registered or run.**

## Forward paper books (not passed, owner-approved 12 Nov 2026)

The owner approved on 12 Nov 2026 ("Yes, add both") running round 2's two best rules forward as paper books in Mind 15:
**book A** `R2-H29 H30 1.5x/0x spot longs` and **book B** `R2-H29 H31 trail 4 ATR spot longs`, frozen exactly as in
round 2, on BTCUSDT and ETHUSDT (each its own $10,000 paper book), from **2026-11-11 20:00 UTC** (12 Nov, 04:00 local).
From the strategy loop; NOT passed: both failed fold share and significance on development data; they run forward on
paper to collect unseen evidence. Code `engine15/playbook4.py` (reproduces round 2 exactly, `tests/test_playbook4.py`);
registry note and forward pass criteria in `research/HYPOTHESES.md` ("Forward paper books from round 2").

- This is **not** rule 4's forward confirmation: neither rule is a development or historical pass, and no holdout look
  was taken or used (ledger still empty). A forward pass would be reported to the owner as unseen evidence; it does not
  confirm the target and changes no verdict above.
- No loop rule changes; no variants are added (count stays 1,910); the loop status stays **paused**.

## Holdout ledger

| # | Candidate | Date (UTC) | Frozen as | Holdout CAGR (= 12-month return) | Max DD vs B&H | Result |
|---|---|---|---|---|---|---|
| - | none yet | | | | | |

## Next round (round 4), proposed from development data only; register in `research/HYPOTHESES.md` before running

1. **H36** H34 with the funding check read only at the 00:00 UTC decision (leverage 1.5x only when the latest funding
   rate <= its 270-settlement median, else 1x; 0 in downtrends; spot long legs; E2 pullback on increases). Fixes H34's
   110-118 trades a year while keeping its smaller drawdown.
2. **H37** Crash-only filter: spot 1x always, 0 when the daily momentum is negative AND the 7-day vol is above its
   trailing one-year 80th percentile; E2 pullback on re-entry. Small tracking error means a smaller edge is needed.
3. **H38** BTC/ETH relative momentum book: at each 00:00 UTC decision hold (spot, 1x) the coin with the higher 30-day
   return, flat if both are negative; E2 pullback on a switch. Graded against the half-and-half spot buy-and-hold book.
Per coin: 3 rules x 2 coins = 6 variants (H38 is one book, so 5 in practice). After round 4 the cumulative count would
be about 1,916. Details and reasoning: `research/out/harness/harness_report_round3.md`.

To resume: read this file, `research/out/harness/loop_state.json` and the round-3 report; register H36-H38; then
write `research/harness/round4.py` on the pattern of `round3.py` (the pass rules and grading live in `round2.grade`).
