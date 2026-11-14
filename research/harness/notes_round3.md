## Summary (round 3)

**No development pass; 0 holdout looks.** Four rules, one variant each (8 variants on BTC/ETH; 1,910 cumulative).

- **H32 vol-managed buy-and-hold core:** vol management did **not** raise Sharpe on crypto. BTC: Sharpe 1.01 vs spot
  buy-and-hold 1.03, drawdown 82% vs 77%. ETH: 0.81 vs 0.96. Crypto's realised vol does not predict its next returns
  well enough for vol timing to help. On gold, USDJPY and the S&P the 60% vol target simply means a constant 2x (the same
  Sharpe as buy-and-hold, with twice the drawdown); the target was set for crypto.
- **H33 vol-target + 4-ATR trailing exit with the ensemble direction:** BTC +65.3%, Sharpe 1.30, DD 66% (spot
  buy-and-hold +56.2%, 1.03, 77%), but ETH only +38.0% (Sharpe 0.91). It is worse than round 2's H29 H31 with the 30-day
  direction (BTC 1.32 / ETH 1.38), so the ensemble did not help.
- **H34 funding-aware leverage:** compared with round 2's H29 H30 1.5x/0x spot, it has about the same Sharpe (BTC 1.18
  vs 1.19, ETH 1.26 vs 1.25), a smaller drawdown (56% vs 65%, 61% vs 67%) and lower CAGR (BTC +64.6%, ETH +94.4%). But
  the funding flag flips 1.5x <-> 1x so often that it trades 110-118 times a year, which fails the turnover rule.
- **H35 hour-of-day exposure:** as feared. About 4,000 position changes a year; -99% on both coins. Hour-of-day means
  on 12 months of training data are noise.
- **Other markets (report only):** no rule beats buy-and-hold on both Sharpe and drawdown on any of the six. The
  closest is USDJPY H33 (Sharpe 0.94 vs 0.81, drawdown 17% vs 16%). The trend and vol rules built for crypto do not
  carry over.

**How close is anything?** BTC H33 and H34, and ETH H34, meet 5 of 8 rules. Every candidate fails fold share (best 43%,
ETH H32) and significance. The Sharpe edge over spot buy-and-hold that significance demands (z = 4.04 x the paired
bootstrap standard error) is 0.69-0.71 for the rules that track buy-and-hold closely (H32) and 1.31-1.47 for the trend
rules. The best observed edge in rounds 2-3 is +0.58 (ETH, round 2's H29 H28). Put another way, a pass needs an
information ratio against spot buy-and-hold of roughly 1.8 sustained over five years. No rule here is near that.

## Proposed round 4 (development data only; register before running; 3 rules, 6 variants)

1. **H36 H34 with a daily funding check (turnover fix).** As H34, but the funding test (latest rate <= its 270-settlement
   median) is read only at the 00:00 UTC decision, and leverage changes only there. That should bring it to about 60
   trades a year. It keeps H34's smaller drawdown.
2. **H37 Crash-only filter on spot buy-and-hold.** Spot 1x always, except 0 when the daily momentum is negative AND the
   7-day vol is above its trailing one-year 80th percentile (rare, crash-like states), with the E2 pullback for re-entry.
   Aim: small tracking error (a smaller standard error, so a smaller edge is needed) and wins in the few crash folds.
3. **H38 BTC/ETH relative momentum (one book).** At each 00:00 UTC decision hold, spot 1x, the coin with the higher 30-day
   return (flat if both are negative), with the E2 pullback on a switch. Graded as a book against the half-and-half
   spot buy-and-hold book. Aim: a higher Sharpe in up folds by holding the stronger coin. This is a different source of
   return from anything tried so far.

Status: **paused by the owner after round 3; resume on request.** Round 4 has not been started or registered.
