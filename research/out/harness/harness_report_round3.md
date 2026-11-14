# Harness loop, round 3: vol management, better exits, fewer variants

Generated 2026-11-11 14:15 UTC by `py -3 research/harness/round3.py`. Paper research only. H32-H35 registered in `research/HYPOTHESES.md` at 14:13 UTC on 11 Nov 2026, before any round-3 result. Development data only (out of sample 2020-10-01 to 2025-11-11, 21 folds); sealed holdout untouched; 0 holdout looks used.

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

## Rules (unchanged from round 2)

Per coin (BTC and ETH), against spot buy-and-hold: CAGR >= 25%; CAGR > B&H; Sharpe > B&H and max DD <= B&H; Sharpe > B&H in >= half the folds; bootstrap p <= 0.05 / 1910 = 2.6e-05 (z >= 4.04); no fee-only-at-0.05%; <= 100 trades a year; > half the folds positive.

## BTCUSDT (graded)

| Strategy | CAGR | Sharpe | Max DD | Calmar | Trades/yr | Avg exposure | Fold share vs B&H | Folds positive | Sharpe edge (daily) | Edge needed | Boot p | DSR | Rules met (of 8) | Failing | Pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H32 vol-managed buy-and-hold core (spot) | +55.2% | 1.01 | 82% | 0.67 | 44 | 1.24 | 24% | 48% | -0.08 | 0.69 | 0.678 | 0.13 | 3 | 2_cagr_gt_bh, 3_sharpe_gt_bh_and_dd_le_bh, 4_fold_share_ge_half, 5_significant, 7_positive_folds_gt_half | no |
| H33 vol-target + trail 4 ATR, ensemble direction (spot) | +65.3% | 1.30 | 66% | 0.98 | 53 | 0.71 | 29% | 48% | +0.27 | 1.31 | 0.200 | 0.31 | 5 | 4_fold_share_ge_half, 5_significant, 7_positive_folds_gt_half | no |
| H34 funding-aware 1.5x/0x trend core (spot) | +64.6% | 1.18 | 56% | 1.14 | 118 | 0.68 | 29% | 57% | +0.22 | 1.47 | 0.269 | 0.22 | 5 | 4_fold_share_ge_half, 5_significant, 6_no_high_turnover | no |
| H35 H32 in positive hours only (spot) | -99.8% | -12.10 | 100% | -1.00 | 4066 | 0.73 | 0% | 0% | -12.96 | 2.87 | 1.000 | 0.00 | 1 | 1_cagr_ge_25, 2_cagr_gt_bh, 3_sharpe_gt_bh_and_dd_le_bh, 4_fold_share_ge_half, 5_significant, 6_no_high_turnover, 7_positive_folds_gt_half | no |
| Buy-and-hold, spot | +56.2% | 1.03 | 77% | 0.73 | 0 | | | | | | | | | | |
| Buy-and-hold, perp | +37.9% | 0.83 | 79% | 0.48 | 0 | | | | | | | | | | |
| Momentum (daily, 30-day) | +25.4% | 0.67 | 63% | 0.41 | 30 | | | | | | | | | | |

**Calendar-year returns, 0.10% a side (2020 from 1 Oct, 2025 to 10 Nov):**

| Strategy | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | Years beating spot B&H |
|---|---|---|---|---|---|---|---|
| Buy-and-hold, spot | +168% | +60% | -64% | +156% | +121% | +13% | 0 of 6 |
| Buy-and-hold, perp | +156% | +18% | -66% | +136% | +96% | +8% | 0 of 6 |
| Momentum | +168% | +23% | -29% | +144% | -29% | -22% | 2 of 6 |
| H32 vol-managed buy-and-hold core (spot) | +220% | +25% | -70% | +200% | +151% | +5% | 3 of 6 |
| H33 vol-target + trail 4 ATR, ensemble direction (spot) | +211% | +78% | -56% | +140% | +117% | +3% | 3 of 6 |
| H34 funding-aware 1.5x/0x trend core (spot) | +307% | +123% | -49% | +172% | +19% | -14% | 4 of 6 |
| H35 H32 in positive hours only (spot) | -57% | -92% | -100% | -100% | -99% | -100% | 0 of 6 |

At 0.05% a side: H32 CAGR +56.1%, Sharpe 1.02; H33 CAGR +69.4%, Sharpe 1.35; H34 CAGR +71.7%, Sharpe 1.26; H35 CAGR -97.0%, Sharpe -6.99.

H35 hours kept per fold (of 24): 16, 19, 18, 19, 17, 15, 14, 11, 10, 8, 11, 14, 13, 16, 18, 15, 15, 16, 13, 13, 13.

## ETHUSDT (graded)

| Strategy | CAGR | Sharpe | Max DD | Calmar | Trades/yr | Avg exposure | Fold share vs B&H | Folds positive | Sharpe edge (daily) | Edge needed | Boot p | DSR | Rules met (of 8) | Failing | Pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H32 vol-managed buy-and-hold core (spot) | +37.1% | 0.81 | 78% | 0.48 | 34 | 0.99 | 43% | 62% | -0.11 | 0.71 | 0.727 | 0.05 | 4 | 2_cagr_gt_bh, 3_sharpe_gt_bh_and_dd_le_bh, 4_fold_share_ge_half, 5_significant | no |
| H33 vol-target + trail 4 ATR, ensemble direction (spot) | +38.0% | 0.91 | 63% | 0.60 | 51 | 0.53 | 33% | 48% | +0.06 | 1.38 | 0.431 | 0.08 | 3 | 2_cagr_gt_bh, 3_sharpe_gt_bh_and_dd_le_bh, 4_fold_share_ge_half, 5_significant, 7_positive_folds_gt_half | no |
| H34 funding-aware 1.5x/0x trend core (spot) | +94.4% | 1.26 | 61% | 1.54 | 110 | 0.63 | 38% | 62% | +0.33 | 1.35 | 0.161 | 0.28 | 5 | 4_fold_share_ge_half, 5_significant, 6_no_high_turnover | no |
| H35 H32 in positive hours only (spot) | -99.3% | -9.84 | 100% | -0.99 | 4077 | 0.56 | 0% | 0% | -10.54 | 2.32 | 1.000 | 0.00 | 1 | 1_cagr_ge_25, 2_cagr_gt_bh, 3_sharpe_gt_bh_and_dd_le_bh, 4_fold_share_ge_half, 5_significant, 6_no_high_turnover, 7_positive_folds_gt_half | no |
| Buy-and-hold, spot | +56.6% | 0.96 | 81% | 0.69 | 0 | | | | | | | | | | |
| Buy-and-hold, perp | +36.1% | 0.79 | 82% | 0.44 | 0 | | | | | | | | | | |
| Momentum (daily, 30-day) | +39.5% | 0.82 | 80% | 0.49 | 27 | | | | | | | | | | |

**Calendar-year returns, 0.10% a side (2020 from 1 Oct, 2025 to 10 Nov):**

| Strategy | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | Years beating spot B&H |
|---|---|---|---|---|---|---|---|
| Buy-and-hold, spot | +104% | +399% | -67% | +91% | +46% | +7% | 0 of 6 |
| Buy-and-hold, perp | +89% | +243% | -68% | +76% | +28% | +2% | 0 of 6 |
| Momentum | +51% | +119% | -0% | -4% | -39% | +183% | 2 of 6 |
| H32 vol-managed buy-and-hold core (spot) | +92% | +182% | -64% | +108% | +21% | +2% | 2 of 6 |
| H33 vol-target + trail 4 ATR, ensemble direction (spot) | +60% | +159% | -44% | +48% | -8% | +64% | 2 of 6 |
| H34 funding-aware 1.5x/0x trend core (spot) | +108% | +569% | -35% | +70% | -3% | +99% | 4 of 6 |
| H35 H32 in positive hours only (spot) | -45% | -94% | -100% | -100% | -98% | -99% | 0 of 6 |

At 0.05% a side: H32 CAGR +37.8%, Sharpe 0.82; H33 CAGR +41.1%, Sharpe 0.96; H34 CAGR +102.0%, Sharpe 1.31; H35 CAGR -94.7%, Sharpe -5.81.

H35 hours kept per fold (of 24): 16, 17, 16, 16, 15, 17, 13, 11, 10, 8, 12, 16, 13, 13, 16, 14, 15, 15, 11, 12, 14.

## Other Mind 15 markets (robustness, report only; cannot pass or block a pass)

Same frozen rules; each market's fee a side; no funding; 'daily' = the last bar of each UTC day; momentum lookbacks in calendar days; leverage financing not modelled. Annualised with each market's own bars a year.

| Market | Fee/side | Buy-and-hold CAGR / Sharpe / DD | H32 | H33 | H34 | H35 | Momentum CAGR / Sharpe |
|---|---|---|---|---|---|---|---|
| XAUUSD | 0.02% | +16.5% / 1.09 / 22% | +32.3% / 1.09 / 39% (fold share 38%, 1 tr/yr) | +13.0% / 0.62 / 29% (fold share 19%, 33 tr/yr) | +7.9% / 0.51 / 24% (fold share 29%, 25 tr/yr) | -88.0% / -9.41 / 100% (fold share 0%, 3348 tr/yr) | -5.4% / -0.29 |
| XAGUSD | 0.03% | +16.3% / 0.66 / 41% | +23.1% / 0.66 / 61% (fold share 38%, 11 tr/yr) | -4.6% / 0.09 / 67% (fold share 24%, 40 tr/yr) | +0.1% / 0.17 / 44% (fold share 19%, 25 tr/yr) | -92.5% / -6.66 / 100% (fold share 0%, 2960 tr/yr) | -14.7% / -0.39 |
| USDJPY | 0.01% | +7.7% / 0.81 / 16% | +14.9% / 0.81 / 30% (fold share 0%, 0 tr/yr) | +12.8% / 0.94 / 17% (fold share 33%, 31 tr/yr) | +5.0% / 0.52 / 16% (fold share 14%, 25 tr/yr) | -66.0% / -7.11 / 100% (fold share 0%, 3174 tr/yr) | +0.2% / 0.07 |
| SPX | 0.02% | +14.7% / 0.90 / 27% | +25.2% / 0.90 / 45% (fold share 29%, 1 tr/yr) | +14.0% / 0.74 / 32% (fold share 29%, 19 tr/yr) | +10.0% / 0.68 / 25% (fold share 19%, 18 tr/yr) | -41.8% / -2.27 / 94% (fold share 0%, 925 tr/yr) | +1.9% / 0.20 |
| WTI | 0.04% | +8.2% / 0.40 / 57% | +1.7% / 0.32 / 81% (fold share 24%, 20 tr/yr) | +3.9% / 0.29 / 71% (fold share 24%, 37 tr/yr) | +13.4% / 0.52 / 63% (fold share 38%, 27 tr/yr) | -96.6% / -8.15 / 100% (fold share 0%, 2982 tr/yr) | +5.3% / 0.32 |
| BRENT | 0.04% | +8.5% / 0.41 / 56% | +3.9% / 0.35 / 80% (fold share 24%, 16 tr/yr) | -6.5% / 0.01 / 75% (fold share 24%, 36 tr/yr) | +0.4% / 0.19 / 71% (fold share 29%, 28 tr/yr) | -95.1% / -7.61 / 100% (fold share 0%, 2565 tr/yr) | -7.9% / -0.06 |

Markets (of 6) where the rule has a higher Sharpe AND no deeper drawdown than buy-and-hold: H32 0, H33 0, H34 0, H35 0.

## Round 3 result

- Development passes (all rules, BTC and ETH): **none**.
- Sharpe edge over spot buy-and-hold the significance rule now demands (z = 4.04 x bootstrap standard error): BTC H32: 0.69; BTC H33: 1.31; BTC H34: 1.47; ETH H32: 0.71; ETH H33: 1.38; ETH H34: 1.35.
- Holdout looks used: 0. Cumulative variants: 1910.
