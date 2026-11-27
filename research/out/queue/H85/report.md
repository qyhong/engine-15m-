# H85: higher-timeframe placebo: bias and tide circularly shifted in time (>= 30 days)

## Conclusion

**The Setups book (b_targets) is NOT distinguishable from its placebo (its higher-timeframe bias and tide shifted in time) at p = 0.1037** (primary: pooled mean R per trade over the eight markets, one-sided, real at least as good; 13000 draws). Real -0.0021R a trade; placebo median -0.0278R (5%-95%: -0.0564 to +0.0060). Lower-tail p (real at most as good) = 0.8964.

Never read as proof: this family makes many tests (see the ledger in research/HYPOTHESES.md), and one or two will look significant by chance. Data end at the last session at or before 2025-11-10 23:45 (the holdout is not read).

## All cells (p_upper: share of draws at least as good, +1 corrected)

| Cell | real trades | real mean R | real sum R | current rule mean R | placebo median mean R | p mean R | p sum R | p lower (mean) | placebo trades (median) |
|---|---|---|---|---|---|---|---|---|---|
| pooled_all | 5162 | -0.0021 | -11.0 | -0.0021 | -0.0278 | 0.1037 | 0.1011 | 0.8964 | 6006 |
| pooled_h1 | 2953 | +0.0100 | +29.6 | +0.0100 | -0.0196 | 0.1145 | 0.1258 | 0.8856 | 3547 |
| pooled_h2 | 2209 | -0.0184 | -40.5 | -0.0184 | -0.0384 | 0.2486 | 0.2296 | 0.7515 | 2453 |
| vault_all | 1767 | -0.0101 | -17.9 | -0.0101 | -0.0436 | 0.1276 | 0.1158 | 0.8725 | 2181 |
| vault_h1 | 991 | +0.0452 | +44.7 | +0.0452 | -0.0226 | 0.0513 | 0.0772 | 0.9488 | 1270 |
| vault_h2 | 776 | -0.0807 | -62.6 | -0.0807 | -0.0706 | 0.5896 | 0.4816 | 0.4105 | 912 |
| others_all | 3395 | +0.0020 | +6.9 | +0.0020 | -0.0181 | 0.1851 | 0.1874 | 0.8149 | 3819 |
| others_h1 | 1962 | -0.0077 | -15.1 | -0.0077 | -0.0154 | 0.3939 | 0.3804 | 0.6062 | 2275 |
| others_h2 | 1433 | +0.0154 | +22.1 | +0.0154 | -0.0171 | 0.1791 | 0.1855 | 0.8210 | 1543 |

## Per market (all; descriptive)

| Market | trades | real mean R | placebo median | p |
|---|---|---|---|---|
| BTCUSDT | 879 | -0.0637 | -0.0645 | 0.4912 |
| ETHUSDT | 888 | +0.0429 | -0.0241 | 0.0312 |
| XAUUSD | 655 | -0.0188 | -0.0035 | 0.6285 |
| XAGUSD | 609 | -0.0172 | -0.0347 | 0.3683 |
| USDJPY | 636 | +0.0267 | -0.0261 | 0.1105 |
| SPX | 199 | +0.1069 | +0.0238 | 0.1422 |
| WTI | 653 | -0.0002 | -0.0090 | 0.3974 |
| BRENT | 643 | -0.0131 | -0.0244 | 0.3788 |

Gates: {"crypto": {"BTCUSDT": {"run_is_engine_b_targets": true}, "ETHUSDT": {"run_is_engine_b_targets": true}}, "metals": {"XAUUSD": {"run_is_engine_b_targets": true}, "XAGUSD": {"run_is_engine_b_targets": true}}, "fx": {"USDJPY": {"run_is_engine_b_targets": true}}, "index": {"SPX": {"run_is_engine_b_targets": true}}, "energy": {"WTI": {"run_is_engine_b_targets": true}, "BRENT": {"run_is_engine_b_targets": true}}}
