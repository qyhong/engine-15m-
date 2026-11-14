# H37 study: hedged long-short structures for BTC and ETH downtrends (exploration, development data only)

Registered in `research/HYPOTHESES.md` (H37, 2026-11-13 09:33 UTC) before this code existed. **Not a loop round**: no loop rule is changed, nothing here is a pass, and the loop count (1,910) is unchanged. Sealed holdout 2025-11-11 .. 2026-11-11 never loaded (`core.load(..., dev_only=True)`; last bar used: 2025-11-10 23:45:00+00:00). Span: the loop's out-of-sample folds 2020-10-01 .. 2025-11-11 (21 folds). Costs: 0.10% a side on every leg + half spread 0.5 bp + slippage 0.10 x bar vol; real perp funding on every perp leg (paid or received); spot legs pay none. Generated 2026-11-13 09:39 UTC.

Downtrend rule D: last daily close < SMA200 and SMA200 below its value 20 days earlier (closed daily bars via `data.htf_on_15`). V6 (agent hedge ratio) was not run (see HYPOTHESES.md). Spot buy-and-hold check: equals the harness's own to 0.0e+00 (BTC) / 0.0e+00 (ETH).

## BTCUSDT, full development span (2020-10-01 .. 2025-11-11)

| Strategy | Total return | CAGR | Sharpe | Max DD (peak .. trough) | Calmar | Trades/yr | Fold share (of differing folds) | Folds > 0 | Avg net | p vs B&H |
|---|---|---|---|---|---|---|---|---|---|---|
| Spot buy-and-hold 1x | +880% | +56.2% | 1.03 | -77% (2021-11-10 .. 2022-11-21) | 0.73 | 0.2 | - | 57% | 1.00 | - |
| V1 dial0: D -> spot 0.75 + perp -0.75 (net 0) | +1669% | +75.4% | 1.28 | -57% (2021-04-14 .. 2022-01-24) | 1.33 | 1.8 | 14% (38% of 8) | 67% | 0.82 | 0.087 |
| V2 dialm05: D -> spot 0.5 + perp -1.0 (net -0.5) | +1964% | +80.7% | 1.31 | -60% (2021-04-14 .. 2022-01-24) | 1.34 | 1.8 | 10% (25% of 8) | 62% | 0.72 | 0.153 |
| V3 dial0_fund: V1 only when funding > 0, else flat | +1472% | +71.4% | 1.24 | -57% (2021-04-14 .. 2022-01-24) | 1.26 | 12.9 | 0% (0% of 8) | 52% | 0.82 | 0.113 |
| V5 fr_hedge: D -> spot 0.5, + perp -1 on a failed rally | +1157% | +64.0% | 1.14 | -63% (2021-04-14 .. 2023-01-06) | 1.02 | 9.6 | 5% (12% of 8) | 57% | 0.84 | 0.189 |
| ref R-flat: D -> flat | +1616% | +74.3% | 1.27 | -57% (2021-04-14 .. 2022-01-24) | 1.31 | 1.8 | 10% (25% of 8) | 52% | 0.82 | 0.095 |
| ref R-naked: D -> perp -1 (naked short) | +2077% | +82.6% | 1.28 | -64% (2021-04-14 .. 2022-01-24) | 1.29 | 1.8 | 10% (25% of 8) | 62% | 0.63 | 0.255 |
| ref R-naked-FR: V5 signal, flat base, perp -1 | +1433% | +70.5% | 1.21 | -59% (2021-04-14 .. 2022-01-24) | 1.20 | 9.6 | 5% (12% of 8) | 57% | 0.75 | 0.209 |
| V4 rv_bear: D -> long stronger spot 0.75 / short weaker perp 0.75 (common index) | +1833% | +78.5% | 1.29 | -57% (2021-04-14 .. 2022-01-24) | 1.37 | 6.8 | 10% (25% of 8) | 62% | 0.82 | 0.106 |

Attribution per year over the span (sums of per-bar contributions, fraction of equity): spot leg / perp leg price / funding (+ received) / costs.

| Strategy | Spot leg | Perp leg price | Funding | Costs | Worst 7-day perp leg (squeeze) | Worst bar (gap) |
|---|---|---|---|---|---|---|
| Spot buy-and-hold 1x | +64.1% | +0.0% | +0.00% | -0.02% | - | -10.33% (2023-08-17 21:30) |
| V1 dial0: D -> spot 0.75 + perp -0.75 (net 0) | +66.0% | +5.7% | +0.59% | -0.25% | -17.3% (to 2022-07-20) | -10.33% (2023-08-17 21:30) |
| V2 dialm05: D -> spot 0.5 + perp -1.0 (net -0.5) | +67.9% | +7.6% | +0.79% | -0.37% | -23.1% (to 2022-07-20) | -10.33% (2023-08-17 21:30) |
| V3 dial0_fund: V1 only when funding > 0, else flat | +63.2% | +8.5% | +0.64% | -2.61% | -16.0% (to 2022-07-20) | -10.33% (2023-08-17 21:30) |
| V5 fr_hedge: D -> spot 0.5, + perp -1 on a failed rally | +67.9% | -0.7% | +0.34% | -1.24% | -15.4% (to 2022-07-08) | -10.33% (2023-08-17 21:30) |
| ref R-flat: D -> flat | +71.7% | +0.0% | +0.00% | -0.25% | - | -10.33% (2023-08-17 21:30) |
| ref R-naked: D -> perp -1 (naked short) | +71.7% | +7.6% | +0.79% | -0.48% | -23.1% (to 2022-07-20) | -10.33% (2023-08-17 21:30) |
| ref R-naked-FR: V5 signal, flat base, perp -1 | +71.7% | -0.7% | +0.34% | -1.35% | -15.4% (to 2022-07-08) | -10.33% (2023-08-17 21:30) |
| V4 rv_bear: D -> long stronger spot 0.75 / short weaker perp 0.75 | +69.9% | +6.9% | +0.35% | -2.45% | -23.7% (to 2022-06-25) | -10.33% (2023-08-17 21:30) |

### BTCUSDT inside downtrends

D held on 18% of the span; 4 D turn-ons, 3 of them episodes shorter than 30 days (whipsaw). Median fall from the 180-day high close before D turned on: -33% (late entry). Funding: 16% of D days net negative (U days 8%); annualised funding rate in D +4.3%, in U +14.3%.

Pooled returns: all D bars, all U bars, D bars in short (< 30 d) episodes, D bars in long episodes.

| Strategy | D bars | U bars | D short episodes | D long episodes | Funding in D /yr of D | Perp price in D /yr of D |
|---|---|---|---|---|---|---|
| Spot buy-and-hold 1x | -44% | +1637% | +22% | -54% | +0.00% | +0.0% |
| V1 dial0: D -> spot 0.75 + perp -0.75 (net 0) | +2% | +1627% | -0% | +3% | +3.21% | +31.0% |
| V2 dialm05: D -> spot 0.5 + perp -1.0 (net -0.5) | +20% | +1622% | -11% | +34% | +4.28% | +41.3% |
| V3 dial0_fund: V1 only when funding > 0, else flat | -9% | +1627% | -1% | -8% | +3.45% | +46.1% |
| V5 fr_hedge: D -> spot 0.5, + perp -1 on a failed rally | -27% | +1629% | +4% | -30% | +1.84% | -4.0% |
| ref R-flat: D -> flat | -1% | +1627% | -0% | -0% | +0.00% | +0.0% |
| ref R-naked: D -> perp -1 (naked short) | +27% | +1617% | -21% | +60% | +4.28% | +41.3% |
| ref R-naked-FR: V5 signal, flat base, perp -1 | -11% | +1625% | -6% | -5% | +1.84% | -4.0% |
| V4 rv_bear: D -> long stronger spot 0.75 / short weaker perp 0.75 | +12% | +1620% | +0% | +12% | +1.87% | +37.4% |

Each D window found by the rule (episodes merged across gaps <= 14 days, >= 30 days kept): return over the window.

| Window | Days | D share | Fall before D on | B&H | V1 | V2 | V3 | V4 | V5 | R-flat | R-naked | R-naked-FR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022-03-01 .. 2023-01-13 | 319 | 100% | -37% | -54% | +3% | +34% | -8% | +12% | -30% | -0% | +60% | -5% |

Named calendar windows (picked with hindsight by the owner's request; reference only):

| Window | B&H | V1 | V2 | V3 | V4 | V5 | R-flat | R-naked | R-naked-FR |
|---|---|---|---|---|---|---|---|---|---|
| Nov 2021 - Dec 2022 bear (2021-11-10 .. 2023-01-01) | -75% | -34% | -5% | -41% | -23% | -58% | -36% | +24% | -37% |
| Jan - Apr 2025 drawdown (2025-01-20 .. 2025-04-09) | -25% | -25% | -25% | -25% | -25% | -25% | -25% | -25% | -25% |
| Oct - Nov 2025 drawdown (to the seal) (2025-10-06 .. 2025-11-11) | -14% | -14% | -14% | -14% | -14% | -14% | -14% | -14% | -14% |

Calendar years (net):

| Strategy | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| Spot buy-and-hold 1x | +168% | +60% | -64% | +156% | +121% | +13% |
| V1 dial0: D -> spot 0.75 + perp -0.75 (net 0) | +168% | +36% | -4% | +112% | +112% | +13% |
| V2 dialm05: D -> spot 0.5 + perp -1.0 (net -0.5) | +168% | +24% | +38% | +93% | +106% | +13% |
| V3 dial0_fund: V1 only when funding > 0, else flat | +168% | +36% | -15% | +112% | +111% | +13% |
| V5 fr_hedge: D -> spot 0.5, + perp -1 on a failed rally | +168% | +40% | -39% | +127% | +114% | +13% |
| ref R-flat: D -> flat | +168% | +35% | -7% | +112% | +111% | +13% |
| ref R-naked: D -> perp -1 (naked short) | +168% | +13% | +81% | +76% | +101% | +13% |
| ref R-naked-FR: V5 signal, flat base, perp -1 | +168% | +29% | -9% | +106% | +109% | +13% |
| V4 rv_bear: D -> long stronger spot 0.75 / short weaker perp 0.75 | +168% | +33% | +11% | +99% | +117% | +13% |

V4 sleeve: share of its D bars spent long BTC / short ETH: 51%.

V5 hedge exits (all history incl. warm-up before the span): regime 1 (avg 24 h), stop 9 (avg 87 h), take_profit 6 (avg 88 h), time 7 (avg 240 h).

## ETHUSDT, full development span (2020-10-01 .. 2025-11-11)

| Strategy | Total return | CAGR | Sharpe | Max DD (peak .. trough) | Calmar | Trades/yr | Fold share (of differing folds) | Folds > 0 | Avg net | p vs B&H |
|---|---|---|---|---|---|---|---|---|---|---|
| Spot buy-and-hold 1x | +889% | +56.6% | 0.96 | -81% (2021-11-10 .. 2022-06-18) | 0.69 | 0.2 | - | 62% | 1.00 | - |
| V1 dial0: D -> spot 0.75 + perp -0.75 (net 0) | +1267% | +66.8% | 1.09 | -60% (2021-05-12 .. 2021-06-26) | 1.11 | 4.1 | 19% (33% of 12) | 57% | 0.71 | 0.217 |
| V2 dialm05: D -> spot 0.5 + perp -1.0 (net -0.5) | +1048% | +61.2% | 1.02 | -60% (2021-05-12 .. 2021-06-26) | 1.01 | 4.1 | 19% (33% of 12) | 62% | 0.57 | 0.380 |
| V3 dial0_fund: V1 only when funding > 0, else flat | +984% | +59.4% | 1.02 | -60% (2021-05-12 .. 2021-06-26) | 0.99 | 26.2 | 14% (25% of 12) | 52% | 0.71 | 0.298 |
| V5 fr_hedge: D -> spot 0.5, + perp -1 on a failed rally | +939% | +58.1% | 1.00 | -65% (2021-11-10 .. 2022-11-08) | 0.90 | 15.5 | 14% (25% of 12) | 57% | 0.75 | 0.342 |
| ref R-flat: D -> flat | +1230% | +65.9% | 1.08 | -60% (2021-05-12 .. 2021-06-26) | 1.09 | 4.1 | 19% (33% of 12) | 52% | 0.71 | 0.227 |
| ref R-naked: D -> perp -1 (naked short) | +665% | +48.9% | 0.90 | -70% (2024-03-11 .. 2025-07-04) | 0.70 | 4.1 | 19% (33% of 12) | 57% | 0.43 | 0.551 |
| ref R-naked-FR: V5 signal, flat base, perp -1 | +865% | +55.8% | 0.98 | -62% (2024-03-11 .. 2025-02-03) | 0.90 | 15.5 | 14% (25% of 12) | 52% | 0.61 | 0.424 |
| V4 rv_bear: D -> long stronger spot 0.75 / short weaker perp 0.75 (common index) | +1966% | +80.8% | 1.19 | -60% (2021-05-12 .. 2021-06-26) | 1.34 | 10.0 | 19% (33% of 12) | 67% | 0.71 | 0.150 |

Attribution per year over the span (sums of per-bar contributions, fraction of equity): spot leg / perp leg price / funding (+ received) / costs.

| Strategy | Spot leg | Perp leg price | Funding | Costs | Worst 7-day perp leg (squeeze) | Worst bar (gap) |
|---|---|---|---|---|---|---|
| Spot buy-and-hold 1x | +77.3% | +0.0% | +0.00% | -0.02% | - | -10.04% (2021-05-19 13:00) |
| V1 dial0: D -> spot 0.75 + perp -0.75 (net 0) | +76.8% | -1.8% | +0.54% | -0.55% | -35.2% (to 2022-07-20) | -10.04% (2021-05-19 13:00) |
| V2 dialm05: D -> spot 0.5 + perp -1.0 (net -0.5) | +76.2% | -2.3% | +0.73% | -0.81% | -46.9% (to 2022-07-20) | -10.04% (2021-05-19 13:00) |
| V3 dial0_fund: V1 only when funding > 0, else flat | +72.0% | +3.0% | +0.83% | -5.36% | -32.1% (to 2025-05-13) | -10.04% (2021-05-19 13:00) |
| V5 fr_hedge: D -> spot 0.5, + perp -1 on a failed rally | +76.2% | -2.6% | +0.12% | -1.94% | -32.3% (to 2022-07-20) | -10.04% (2021-05-19 13:00) |
| ref R-flat: D -> flat | +75.0% | +0.0% | +0.00% | -0.55% | - | -10.04% (2021-05-19 13:00) |
| ref R-naked: D -> perp -1 (naked short) | +75.0% | -2.3% | +0.73% | -1.08% | -46.9% (to 2022-07-20) | -10.04% (2021-05-19 13:00) |
| ref R-naked-FR: V5 signal, flat base, perp -1 | +75.0% | -2.6% | +0.12% | -2.20% | -32.3% (to 2022-07-20) | -10.04% (2021-05-19 13:00) |
| V4 rv_bear: D -> long stronger spot 0.75 / short weaker perp 0.75 | +83.0% | +4.3% | +0.69% | -3.40% | -23.7% (to 2022-06-25) | -10.04% (2021-05-19 13:00) |

### ETHUSDT inside downtrends

D held on 29% of the span; 10 D turn-ons, 6 of them episodes shorter than 30 days (whipsaw). Median fall from the 180-day high close before D turned on: -33% (late entry). Funding: 23% of D days net negative (U days 6%); annualised funding rate in D +2.5%, in U +18.6%.

Pooled returns: all D bars, all U bars, D bars in short (< 30 d) episodes, D bars in long episodes.

| Strategy | D bars | U bars | D short episodes | D long episodes | Funding in D /yr of D | Perp price in D /yr of D |
|---|---|---|---|---|---|---|
| Spot buy-and-hold 1x | -28% | +1266% | -5% | -24% | +0.00% | +0.0% |
| V1 dial0: D -> spot 0.75 + perp -0.75 (net 0) | +1% | +1248% | -0% | +2% | +1.90% | -6.1% |
| V2 dialm05: D -> spot 0.5 + perp -1.0 (net -0.5) | -14% | +1239% | +0% | -14% | +2.53% | -8.1% |
| V3 dial0_fund: V1 only when funding > 0, else flat | -20% | +1248% | -1% | -19% | +2.88% | +10.4% |
| V5 fr_hedge: D -> spot 0.5, + perp -1 on a failed rally | -23% | +1254% | -2% | -21% | +0.42% | -8.9% |
| ref R-flat: D -> flat | -1% | +1248% | -1% | -1% | +0.00% | +0.0% |
| ref R-naked: D -> perp -1 (naked short) | -42% | +1230% | -1% | -42% | +2.53% | -8.1% |
| ref R-naked-FR: V5 signal, flat base, perp -1 | -28% | +1245% | -2% | -27% | +0.42% | -8.9% |
| V4 rv_bear: D -> long stronger spot 0.75 / short weaker perp 0.75 | +55% | +1233% | -0% | +56% | +2.41% | +14.8% |

Each D window found by the rule (episodes merged across gaps <= 14 days, >= 30 days kept): return over the window.

| Window | Days | D share | Fall before D on | B&H | V1 | V2 | V3 | V4 | V5 | R-flat | R-naked | R-naked-FR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022-03-04 .. 2023-01-12 | 315 | 97% | -42% | -50% | -5% | +4% | -19% | +9% | -30% | -6% | -2% | -18% |
| 2023-09-20 .. 2023-10-29 | 40 | 57% | -23% | +9% | -1% | -6% | -1% | +5% | +1% | -1% | -12% | -4% |
| 2024-09-08 .. 2024-11-08 | 62 | 100% | -44% | +30% | +1% | -13% | -0% | +6% | -5% | -0% | -26% | -18% |
| 2025-02-05 .. 2025-07-05 | 151 | 97% | -33% | -8% | -3% | -9% | -9% | +14% | +3% | -4% | -20% | -0% |

Named calendar windows (picked with hindsight by the owner's request; reference only):

| Window | B&H | V1 | V2 | V3 | V4 | V5 | R-flat | R-naked | R-naked-FR |
|---|---|---|---|---|---|---|---|---|---|
| Nov 2021 - Dec 2022 bear (2021-11-10 .. 2023-01-01) | -75% | -44% | -32% | -52% | -32% | -62% | -44% | -31% | -51% |
| Jan - Apr 2025 drawdown (2025-01-20 .. 2025-04-09) | -54% | -15% | +11% | -18% | +8% | -14% | -15% | +40% | +14% |
| Oct - Nov 2025 drawdown (to the seal) (2025-10-06 .. 2025-11-11) | -21% | -21% | -21% | -21% | -21% | -21% | -21% | -21% | -21% |

Calendar years (net):

| Strategy | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| Spot buy-and-hold 1x | +104% | +399% | -67% | +91% | +46% | +7% |
| V1 dial0: D -> spot 0.75 + perp -0.75 (net 0) | +104% | +399% | -27% | +46% | +13% | +12% |
| V2 dialm05: D -> spot 0.5 + perp -1.0 (net -0.5) | +104% | +399% | -13% | +27% | -2% | +5% |
| V3 dial0_fund: V1 only when funding > 0, else flat | +104% | +399% | -38% | +46% | +12% | +6% |
| V5 fr_hedge: D -> spot 0.5, + perp -1 on a failed rally | +104% | +399% | -51% | +62% | +7% | +19% |
| ref R-flat: D -> flat | +104% | +399% | -27% | +45% | +12% | +11% |
| ref R-naked: D -> perp -1 (naked short) | +104% | +399% | -11% | +9% | -17% | -8% |
| ref R-naked-FR: V5 signal, flat base, perp -1 | +104% | +399% | -36% | +41% | -8% | +15% |
| V4 rv_bear: D -> long stronger spot 0.75 / short weaker perp 0.75 | +104% | +399% | -13% | +49% | +18% | +32% |

V4 sleeve: share of its D bars spent long BTC / short ETH: 66%.

V5 hedge exits (all history incl. warm-up before the span): regime 2 (avg 156 h), stop 12 (avg 113 h), take_profit 7 (avg 104 h), time 9 (avg 240 h).

## V4 two-coin book (half BTC sleeve, half ETH sleeve, never rebalanced) vs half-and-half spot buy-and-hold

| Book | Total return | CAGR | Sharpe | Max DD | Calmar | Trades/yr | Fold share | Folds > 0 | Return on bars with D on either coin |
|---|---|---|---|---|---|---|---|---|---|
| Half-and-half spot buy-and-hold | +884% | +56.4% | 0.99 | -79% | 0.71 | 0.0 | - | 57% | -7% |
| V4 rv_bear book | +1900% | +79.7% | 1.25 | -57% | 1.40 | 11.7 | 24% | 62% | +90% |

## The registered bar for a later formal registration (descriptive)

On BOTH coins: Sharpe above spot buy-and-hold's, max drawdown at most 0.75 x buy-and-hold's, pooled D-bar return above R-flat's and R-naked's.

| Variant | BTC: Sharpe > B&H / DD <= 0.75 B&H / D beats flat and naked | ETH: same | Meets |
|---|---|---|---|
| V1 dial0: D -> spot 0.75 + perp -0.75 (net 0) | yes / yes / no | yes / yes / yes | **no** |
| V2 dialm05: D -> spot 0.5 + perp -1.0 (net -0.5) | yes / no / no | yes / yes / no | **no** |
| V3 dial0_fund: V1 only when funding > 0, else flat | yes / yes / no | yes / yes / no | **no** |
| V4 rv_bear: D -> long stronger spot 0.75 / short weaker perp 0.75 | yes / yes / no | yes / yes / yes | **no** |
| V5 fr_hedge: D -> spot 0.5, + perp -1 on a failed rally | yes / no / no | yes / no / no | **no** |

p vs B&H: paired block bootstrap of the daily Sharpe gap against spot buy-and-hold (normal approximation, one-sided); this study's own level is 0.05 / 11 = 0.0045, and the loop's cumulative level (0.05 / 1,910) is far stricter. Information only.

## What it means

Development data only; no holdout bar was used.

**No variant meets the bar registered for a later formal registration.** The closest is V4 (rv_bear). It meets every
part on ETH, and on BTC it fails only one part: its D-bar return (+12%) is below the naked short's (+27%).

- **Everything that steps aside in downtrends beats buy-and-hold on this span, and the reason is one event.** The rule
  caught most of 2022. Almost every structure, R-flat included, earns about +58-83% CAGR against buy-and-hold's +56%,
  with a smaller drawdown (ETH's naked short, +48.9%, is the exception). Loop rounds 2-3 already found this and failed it on fold share and significance. These
  rules match buy-and-hold exactly in 13 of BTC's 21 folds (9 of ETH's), so their fold share is 0-24%. None reaches
  this study's significance level (best p 0.087 vs 0.0045).
- **The hedge dial (V1) is going flat plus a little carry.** Spot 0.75 + perp -0.75 trades the same amount as selling
  to flat, and with the basis ignored it has the same price exposure. Its only extra is funding, about +0.6% a year on
  each coin (+3% per year of D on BTC, +2% on ETH). V1 vs R-flat: BTC +75.4% vs +74.3% CAGR, ETH +66.8% vs +65.9%.
  Against flat, V1 earns the funding and keeps a spot core. It has no other edge.
- **The partial net short (V2) is the naked short at half size.** Both depend on the coin:
  - BTC's one long bear (Mar 2022 - Jan 2023): V2 made +34%, R-naked +60%, R-flat 0%.
  - ETH's bears whipsawed: V2 -14% and R-naked -42% over all D bars, R-flat -1%. ETH's naked short ended BELOW
    buy-and-hold over the whole span (+48.9% CAGR vs +56.6%).
  - The owner's observation holds: shorts pay in a clean, long bear and give it back in choppy ones.
- **The funding filter (V3) hurt on both coins.** Switching both legs on and off with the 3-settlement funding sign cost
  about 2.6% a year on BTC and 5.4% on ETH in fees and slippage. That is far more than the funding it avoided. In
  this sample, funding in downtrends was mostly POSITIVE for shorts: annualised +4.3% on BTC and +2.5% on ETH while
  D held, and negative on only 16% / 23% of D days. Paying negative funding while short was not a main loss source.
- **Shorting failed rallies (V5) lost on both coins.** The hedge signal alone (R-naked-FR) lost 11% (BTC) and 28% (ETH)
  over D bars. Its exits were mostly stops and time stops (BTC 9 stops and 7 time stops vs 6 take-profits; ETH 12, 9
  and 7). Bear rallies kept going past the 20/50-day averages. V5's base of 0.5 spot through D also carried half of
  the bear's loss (-27% on BTC's D bars).
- **Relative value in downtrends (V4) is the only structure that earned in D on both coins.** It made +12% on BTC's D
  bars and +55% on ETH's. As a two-coin book: +79.7% CAGR, Sharpe 1.25, max DD -57%, against half-and-half spot
  buy-and-hold at +56.4%, 0.99 and -79%. +90% on bars where either coin was in D, against -7%. The caveat is large:
  ETH lost ground to BTC almost all the way from late 2021 to mid-2025. V4 mostly harvests that one long trend (short
  ETH / long BTC in ETH's downtrends). A sharp ETH/BTC reversal inside a downtrend is its squeeze risk: the worst 7-day
  hedge-leg loss was -24% (to 2022-06-25).
- **Where the damage comes from, by cause:**
  - *Late entry* is the biggest. The median fall from the 180-day high before D turned on was -33% on both coins (BTC
    2022: -37%). Every dial structure's maximum drawdown on BTC (about -57%, Apr 2021 - Jan 2022) happened BEFORE the
    rule turned on. No hedge structure can fix that; only an earlier signal can.
  - *Whipsaw*: 3 of BTC's 4 D turn-ons and 6 of ETH's 10 lasted under 30 days. In BTC's short episodes buy-and-hold
    gained +22% while R-naked lost 21% and V2 lost 11%.
  - *Squeeze*: the worst 7-day result on the hedge leg was -23% (BTC, V2 / naked) and -47% (ETH, V2 / naked), both
    the July 2022 relief rally. V1's smaller hedge kept it to -17% / -35%.
  - *Funding*: a small net gain for shorts here, not a loss.
  - *Gaps*: the worst single 15m bars (-10.3% BTC, -10.0% ETH) fell in up regimes on the long leg, not on any hedge.

**Recommendation.**
- No structure here has earned a formal loop registration on this evidence. The one candidate, V4 rv_bear as a two-coin
  book, would have to be registered fresh under the loop's full rules, disclosing this study's 11 variants. On this
  data it would almost certainly fail fold share and significance, like every rule before it. The book's Sharpe edge
  over buy-and-hold is +0.34 on daily returns (bootstrap standard error 0.27, p 0.10). The loop's level (0.05 / 1,910)
  would need an edge of about 1.07 at that standard error. Its fold share is 24%.
- If the owner wants forward data points, V4 is the only structure worth a forward paper shadow book. It should be
  labelled not passed and run from a stated go-live, like the round-2 books.
- V1 needs no book of its own. In this model it is R-flat plus carry, so it adds nothing a forward test would teach.
- V2, V3 and V5 are not worth continuing.

**Caveats.**
- The span holds one long bear (2022) and a few short ones. Every D result rests on very few independent episodes.
- Spot-perp basis is ignored: BTC bars are perp prices and ETH bars are spot.
- Positions are fractions of equity held constant, so the drift between legs is rebalanced for free (the harness
  convention). Margin, liquidation and borrow limits are not modelled.
- The named calendar windows were picked with hindsight. The rule never turned on for BTC in early 2025 or Oct-Nov
  2025, so every structure equals buy-and-hold there.
- 11 variants were tried; a p of 0.09-0.55 against buy-and-hold is consistent with luck.
- V6 (agent hedge ratio) was not run: it would have needed fold-model inference over the full span, including the sealed
  holdout, and the heavy-job lock.

