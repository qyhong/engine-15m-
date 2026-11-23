# H80: odds placebo: each market's odds circularly shifted in time (>= 30 days)

## Conclusion

**The Setups book (b_targets) is NOT distinguishable from its placebo (its odds shifted in time) at p = 0.1143** (primary: pooled mean R per trade over the eight markets, one-sided, real at least as good; 10000 draws). Real -0.0021R a trade; placebo median -0.0158R (5%-95%: -0.0343 to +0.0028). Lower-tail p (real at most as good) = 0.8858.

Never read as proof: this family makes many tests (see the ledger in research/HYPOTHESES.md), and one or two will look significant by chance. Data end at the last session at or before 2025-11-10 23:45 (the holdout is not read).

## All cells (p_upper: share of draws at least as good, +1 corrected)

| Cell | real trades | real mean R | real sum R | current rule mean R | placebo median mean R | p mean R | p sum R | p lower (mean) | placebo trades (median) |
|---|---|---|---|---|---|---|---|---|---|
| pooled_all | 5162 | -0.0021 | -11.0 | -0.0021 | -0.0158 | 0.1143 | 0.1121 | 0.8858 | 5580 |
| pooled_h1 | 2953 | +0.0100 | +29.6 | +0.0100 | -0.0168 | 0.0386 | 0.0400 | 0.9615 | 3117 |
| pooled_h2 | 2209 | -0.0184 | -40.5 | -0.0184 | -0.0138 | 0.6087 | 0.5610 | 0.3914 | 2463 |
| vault_all | 1767 | -0.0101 | -17.9 | -0.0101 | -0.0193 | 0.3341 | 0.3154 | 0.6660 | 2005 |
| vault_h1 | 991 | +0.0452 | +44.7 | +0.0452 | -0.0009 | 0.0643 | 0.0740 | 0.9358 | 1101 |
| vault_h2 | 776 | -0.0807 | -62.6 | -0.0807 | -0.0393 | 0.9005 | 0.8149 | 0.0996 | 894 |
| others_all | 3395 | +0.0020 | +6.9 | +0.0020 | -0.0139 | 0.1105 | 0.1119 | 0.8896 | 3573 |
| others_h1 | 1962 | -0.0077 | -15.1 | -0.0077 | -0.0249 | 0.1465 | 0.1454 | 0.8536 | 1996 |
| others_h2 | 1433 | +0.0154 | +22.1 | +0.0154 | +0.0011 | 0.2241 | 0.2419 | 0.7760 | 1554 |

## Per market (all; descriptive)

| Market | trades | real mean R | placebo median | p |
|---|---|---|---|---|
| BTCUSDT | 879 | -0.0637 | -0.0322 | 0.8868 |
| ETHUSDT | 888 | +0.0429 | -0.0073 | 0.0278 |
| XAUUSD | 655 | -0.0188 | -0.0315 | 0.2559 |
| XAGUSD | 609 | -0.0172 | -0.0394 | 0.1136 |
| USDJPY | 636 | +0.0267 | +0.0300 | 0.5817 |
| SPX | 199 | +0.1069 | +0.1156 | 0.6787 |
| WTI | 653 | -0.0002 | -0.0198 | 0.2599 |
| BRENT | 643 | -0.0131 | -0.0425 | 0.1555 |

Gates: {"crypto": {"BTCUSDT": {"run_is_engine_b_targets": true}, "ETHUSDT": {"run_is_engine_b_targets": true}}, "metals": {"XAUUSD": {"run_is_engine_b_targets": true}, "XAGUSD": {"run_is_engine_b_targets": true}}, "fx": {"USDJPY": {"run_is_engine_b_targets": true}}, "index": {"SPX": {"run_is_engine_b_targets": true}}, "energy": {"WTI": {"run_is_engine_b_targets": true}, "BRENT": {"run_is_engine_b_targets": true}}}
