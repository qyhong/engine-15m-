# H86: stop-size placebo: the volatility unit shuffled across bars within each month

## Conclusion

**The Setups book (b_targets) IS distinguishable from its placebo (its volatility unit shuffled within each month) at p = 0.0025** (primary: pooled mean R per trade over the eight markets, one-sided, real at least as good; 10000 draws). Real -0.0021R a trade; placebo median -0.0278R (5%-95%: -0.0425 to -0.0131). Lower-tail p (real at most as good) = 0.9976.

Never read as proof: this family makes many tests (see the ledger in research/HYPOTHESES.md), and one or two will look significant by chance. Data end at the last session at or before 2025-11-10 23:45 (the holdout is not read).

## All cells (p_upper: share of draws at least as good, +1 corrected)

| Cell | real trades | real mean R | real sum R | current rule mean R | placebo median mean R | p mean R | p sum R | p lower (mean) | placebo trades (median) |
|---|---|---|---|---|---|---|---|---|---|
| pooled_all | 5162 | -0.0021 | -11.0 | -0.0021 | -0.0278 | 0.0025 | 0.0025 | 0.9976 | 5981 |
| pooled_h1 | 2953 | +0.0100 | +29.6 | +0.0100 | -0.0138 | 0.0221 | 0.0283 | 0.9780 | 3411 |
| pooled_h2 | 2209 | -0.0184 | -40.5 | -0.0184 | -0.0464 | 0.0207 | 0.0134 | 0.9794 | 2570 |
| vault_all | 1767 | -0.0101 | -17.9 | -0.0101 | -0.0410 | 0.0374 | 0.0286 | 0.9627 | 2136 |
| vault_h1 | 991 | +0.0452 | +44.7 | +0.0452 | -0.0259 | 0.0006 | 0.0021 | 0.9995 | 1232 |
| vault_h2 | 776 | -0.0807 | -62.6 | -0.0807 | -0.0612 | 0.7688 | 0.6168 | 0.2313 | 905 |
| others_all | 3395 | +0.0020 | +6.9 | +0.0020 | -0.0205 | 0.0150 | 0.0158 | 0.9851 | 3845 |
| others_h1 | 1962 | -0.0077 | -15.1 | -0.0077 | -0.0071 | 0.5220 | 0.4969 | 0.4781 | 2179 |
| others_h2 | 1433 | +0.0154 | +22.1 | +0.0154 | -0.0385 | 0.0003 | 0.0005 | 0.9998 | 1666 |

## Per market (all; descriptive)

| Market | trades | real mean R | placebo median | p |
|---|---|---|---|---|
| BTCUSDT | 879 | -0.0637 | -0.0691 | 0.4097 |
| ETHUSDT | 888 | +0.0429 | -0.0129 | 0.0098 |
| XAUUSD | 655 | -0.0188 | -0.0242 | 0.4035 |
| XAGUSD | 609 | -0.0172 | -0.0474 | 0.0952 |
| USDJPY | 636 | +0.0267 | -0.0170 | 0.0493 |
| SPX | 199 | +0.1069 | +0.0988 | 0.4371 |
| WTI | 653 | -0.0002 | -0.0080 | 0.3658 |
| BRENT | 643 | -0.0131 | -0.0400 | 0.1108 |

Gates: {"crypto": {"BTCUSDT": {"run_is_engine_b_targets": true}, "ETHUSDT": {"run_is_engine_b_targets": true}}, "metals": {"XAUUSD": {"run_is_engine_b_targets": true}, "XAGUSD": {"run_is_engine_b_targets": true}}, "fx": {"USDJPY": {"run_is_engine_b_targets": true}}, "index": {"SPX": {"run_is_engine_b_targets": true}}, "energy": {"WTI": {"run_is_engine_b_targets": true}, "BRENT": {"run_is_engine_b_targets": true}}}
