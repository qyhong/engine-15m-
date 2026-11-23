# H83: trend-filter placebo: the 30-day move circularly shifted in time (>= 60 days)

## Conclusion

**The 30-day filter book (b_trend30) is NOT distinguishable from its placebo (the 30-day move shifted in time) at p = 0.0550** (primary: pooled mean R per trade over the eight markets, one-sided, real at least as good; 10000 draws). Real +0.0150R a trade; placebo median -0.0134R (5%-95%: -0.0423 to +0.0160). Lower-tail p (real at most as good) = 0.9451.

Never read as proof: this family makes many tests (see the ledger in research/HYPOTHESES.md), and one or two will look significant by chance. Data end at the last session at or before 2025-11-10 23:45 (the holdout is not read).

## All cells (p_upper: share of draws at least as good, +1 corrected)

| Cell | real trades | real mean R | real sum R | current rule mean R | placebo median mean R | p mean R | p sum R | p lower (mean) | placebo trades (median) |
|---|---|---|---|---|---|---|---|---|---|
| pooled_all | 4763 | +0.0150 | +71.5 | -0.0021 | -0.0134 | 0.0550 | 0.0396 | 0.9451 | 3837 |
| pooled_h1 | 2721 | +0.0317 | +86.3 | +0.0100 | -0.0063 | 0.0479 | 0.0206 | 0.9522 | 2271 |
| pooled_h2 | 2042 | -0.0072 | -14.7 | -0.0184 | -0.0229 | 0.3155 | 0.3372 | 0.6846 | 1569 |
| vault_all | 1529 | +0.0793 | +121.3 | -0.0101 | -0.0036 | 0.0011 | 0.0003 | 0.9990 | 1325 |
| vault_h1 | 863 | +0.1229 | +106.1 | +0.0452 | +0.0130 | 0.0021 | 0.0001 | 0.9980 | 788 |
| vault_h2 | 666 | +0.0228 | +15.2 | -0.0807 | -0.0313 | 0.1472 | 0.1259 | 0.8529 | 539 |
| others_all | 3234 | -0.0154 | -49.8 | +0.0020 | -0.0188 | 0.4418 | 0.5197 | 0.5583 | 2515 |
| others_h1 | 1858 | -0.0107 | -19.8 | -0.0077 | -0.0179 | 0.4033 | 0.4398 | 0.5968 | 1486 |
| others_h2 | 1376 | -0.0217 | -29.9 | +0.0154 | -0.0165 | 0.5550 | 0.6288 | 0.4451 | 1031 |

## Per market (all; descriptive)

| Market | trades | real mean R | placebo median | p |
|---|---|---|---|---|
| BTCUSDT | 727 | +0.0596 | -0.0231 | 0.0078 |
| ETHUSDT | 802 | +0.0972 | +0.0149 | 0.0089 |
| XAUUSD | 644 | -0.0363 | +0.0206 | 0.9312 |
| XAGUSD | 577 | -0.0552 | -0.0564 | 0.4903 |
| USDJPY | 611 | -0.0004 | -0.0248 | 0.3019 |
| SPX | 190 | +0.0775 | +0.0586 | 0.3883 |
| WTI | 597 | +0.0189 | -0.0190 | 0.2093 |
| BRENT | 615 | -0.0329 | -0.0382 | 0.4547 |

Gates: {"crypto": {"BTCUSDT": {"run_is_engine_b_targets": true, "run_is_engine_b_trend30": true}, "ETHUSDT": {"run_is_engine_b_targets": true, "run_is_engine_b_trend30": true}}, "metals": {"XAUUSD": {"run_is_engine_b_targets": true, "run_is_engine_b_trend30": true}, "XAGUSD": {"run_is_engine_b_targets": true, "run_is_engine_b_trend30": true}}, "fx": {"USDJPY": {"run_is_engine_b_targets": true, "run_is_engine_b_trend30": true}}, "index": {"SPX": {"run_is_engine_b_targets": true, "run_is_engine_b_trend30": true}}, "energy": {"WTI": {"run_is_engine_b_targets": true, "run_is_engine_b_trend30": true}, "BRENT": {"run_is_engine_b_targets": true, "run_is_engine_b_trend30": true}}}
