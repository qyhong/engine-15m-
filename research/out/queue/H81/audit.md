# H81 audit: why the side placebo beats the book by 0.11R a trade

Audit of the H81 result (22 Nov 2026), not a new study: nothing registered, `placebo.py` and the engine unchanged.
Script: `research/queue/h81_audit.py` (extract / analyse / toy / h82probe), run on the research server with
placebo.py's own loader, book, replay gate and `machine_r`; data to 2025-11-10 23:45 (holdout not read).

## Verdict

**The H81 result is an artefact of the placebo's design, not of the scoring and not a property of the book.** The
within-month permutation gives a trade the side of a LATER trade of the same month, and the book's later sides react
to the price moves that happened during the earlier trade. The placebo therefore trades with knowledge of the month's
direction, which the book cannot have. `machine_r` / `replay_trade` are sound.

**H82 has the same flaw**, by the mirror route: it moves each trade to a random bar of its month while keeping its
side, so about half the placebo trades start BEFORE the bar where that side was chosen.

## Evidence

The audit's own recomputation matched H81's `sides_<group>.json` exactly (sides identical, r_plus and r_minus to
0.0 on all eight markets); the replay gate passed on every market.

### 1. The scoring is symmetric (no artefact in `machine_r`)

| | BTC | ETH | BTC+ETH | pooled 8 |
|---|---|---|---|---|
| trades | 879 | 888 | 1767 | 5162 |
| own side (= H81 real) | -0.082 | +0.060 | -0.010 | -0.003 |
| opposite side, same bars | -0.061 | -0.082 | -0.071 | -0.078 |
| own + opposite | -0.142 | -0.022 | -0.082 | -0.081 |
| minus two round-trip fees in R | -0.160 | -0.128 | -0.144 | -0.104 |

Flipped trades are on average WORSE than the book's own side, not better. Own + flipped is close to two fees (the
rest is the targets: a flipped trade more often has the leg against it and falls back to the 24h-reach target).
For every one of the 5,162 trades and both sides: stop on the correct side, Target 1 on the correct side and at
0.5R or more, Target 2 beyond Target 1 (0 violations). Flipped targets are `live.plan_targets(flipped side, entry,
stop, row i0-1)`, nothing inherited. Target 1 basis own / flipped (pooled): reach 50% / 73%, Fibonacci 50% / 27%;
median Target 1 1.30R / 1.28R; median Target 2 2.0R both. Fees enter both sides by the same line. Stop and targets
read row and unit i0-1, the entry is the close of i0-1 (BTC, ETH) or the open of i0: no future bar. 64 of 5,162
trades reach the data end before 30 days and close at the last bar's close, both sides alike (negligible). The
machinery's real mean (-0.0030R) matches the book's own R (-0.0021R).

### 2. Where the placebo's +0.11R comes from (expected R a trade)

| null for the side | BTC | ETH | BTC+ETH | pooled 8 |
|---|---|---|---|---|
| book's own side | -0.082 | +0.060 | -0.010 | -0.003 |
| coin 50/50 | -0.071 | -0.011 | -0.041 | -0.040 |
| coin at the market's whole-window long share | -0.067 | -0.005 | -0.036 | -0.027 |
| side share of the PREVIOUS month | -0.057 | -0.040 | -0.048 | -0.021 |
| side share of the previous 10 trades | -0.063 | +0.014 | -0.024 | -0.014 |
| H81 as registered (exact expectation) | +0.053 | +0.129 | +0.091 | +0.108 |
| H81, 300 draws: median | +0.056 | +0.126 | +0.090 | +0.109 |

Split of the registered permutation by donor timing (trades with donors both before and after them in the month;
4,123 pooled):

| | BTC | ETH | BTC+ETH | pooled 8 |
|---|---|---|---|---|
| book's own side on these trades | -0.117 | -0.015 | -0.066 | -0.089 |
| side drawn from EARLIER trades of the month | -0.068 | -0.046 | -0.057 | -0.063 |
| side drawn from LATER trades of the month | +0.187 | +0.282 | +0.235 | +0.223 |

Every bit of the placebo's advantage comes from donors entered after the trade. With causal sides (earlier trades,
previous month, previous 10 trades, a coin), the placebo is at or below the book.

### 3. The monthly long share follows the month, it does not predict it

Correlation of a market-month's long share with that month's move (in stop units): BTC 0.77, ETH 0.74, pooled
0.63; with the previous month's move 0.39 (pooled); with the next month's move 0.03. The share agrees in sign with
the month's own move in 80% of months. The book's next side follows the move since its previous entry in 64% of
BTC/ETH pairs (53% on the other six). This is a reactive book (stop-outs, flips, the higher-timeframe bias follow the
price), so the month's mix is information about the month that is only known at its end. Keeping it in the placebo
is look-ahead, not a legitimate structure.

### 4. The mechanism reproduces on a random walk

Twelve random walks (no drift, about 3% a day, 6 years of 15-minute bars, about 1,000 trades each, an entry every
0.5 to 4 days), scored with `placebo.replay_trade` (no readings: Target 1 1.5R, Target 2 2R, 30-day cap), sides
permuted within month exactly as H81 does:

| causal side rule | real mean R | placebo minus real (SE) | placebo with earlier donors only, minus real | walks with p_upper >= 0.95 (placebo "better") | walks with p_upper <= 0.05 (placebo "worse") |
|---|---|---|---|---|---|
| 3-day momentum | -0.065 | +0.045 (0.008) | -0.016 (0.009) | 4 of 12 | 0 |
| 3-day reversal | -0.082 | -0.045 (0.011) | +0.016 (0.012) | 0 | 7 of 12 |
| coin | -0.070 | +0.003 (0.011) | -0.006 (0.011) | 0 | 1 of 12 |

On a martingale, where no side rule can earn anything, the H81 placebo "beats" a momentum rule and "loses to" a
reversal rule. The book behaves like the momentum case.

### 5. H82 is biased the same way (sampled probe of its draw)

Each real trade moved to 4 random bars of its month with placebo.py's own bar rule and entry price, same side,
`machine_r`:

| | BTC | ETH | BTC+ETH | pooled 8 |
|---|---|---|---|---|
| real trades under the machinery | -0.082 | +0.060 | -0.010 | -0.003 |
| placebo, all drawn bars | +0.035 | +0.061 | +0.048 | +0.091 |
| drawn bar BEFORE the real entry | +0.196 (0.035) | +0.165 (0.033) | +0.180 (0.024) | +0.211 (0.014) |
| drawn bar AFTER the real entry | -0.109 (0.030) | -0.039 (0.031) | -0.074 (0.022) | -0.024 (0.013) |

A placebo trade that starts before the bar where its side was decided earns about 0.2R more than one that starts
after. H82 as registered would report the book's entry timing as worse than random, for the same reason.

## What this means

- H81's literal reading ("the book picks the wrong side within a month") is not supported. Against causal nulls the
  book's side is about as good as a coin or slightly better (pooled -0.003R against -0.040R for a coin; ETH +0.060
  against -0.011; BTC -0.082 against -0.071). These comparisons are descriptive, not registered tests.
- H81 should be reported as void (design flaw), not as "not distinguishable at p = 1.0000".
- H82 should not run as registered. A placebo for H82 has to draw bars at or after the real decision, or draw the side
  afresh (coin) when it moves the bar.
- H83 to H86 use `run_book` / `copy_book`, not `machine_r`, and do not take sides from later decisions. H86 shuffles the
  stop unit within month, so a bar can get a later bar's volatility: that is a leak of future volatility, not of
  direction, so it should not tilt mean R the way H81 and H82 are tilted, but it is the same "within month" pattern
  and worth a line in its report. H80, H83 and H85 shift by at least 30 or 60 days and are not affected.

## Not checked

- H86's within-month volatility leak was not quantified.
- The H82 numbers are a 4-draw-per-trade sample (20,648 placebo trades), not the registered 100,000 draws.
- Whether the book's slight edge over a coin on ETH is real (not a registered test; would need its own block).
