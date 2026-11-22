# H81: side placebo: the real trades' sides permuted within market and month

## Conclusion

**The Setups book (b_targets) is NOT distinguishable from its placebo (its trades' sides permuted within market and month) at p = 1.0000** (primary: pooled mean R per trade over the eight markets, one-sided, real at least as good; 100000 draws). Real -0.0030R a trade; placebo median +0.1083R (5%-95%: +0.0875 to +0.1289). Lower-tail p (real at most as good) = 0.0000.

Never read as proof: this family makes many tests (see the ledger in research/HYPOTHESES.md), and one or two will look significant by chance. Data end at the last session at or before 2025-11-10 23:45 (the holdout is not read).

## All cells (p_upper: share of draws at least as good, +1 corrected)

| Cell | real trades | real mean R | real sum R | current rule mean R | placebo median mean R | p mean R | p sum R | p lower (mean) | placebo trades (median) |
|---|---|---|---|---|---|---|---|---|---|
| pooled_all | 5162 | -0.0030 | -15.4 | -0.0021 | +0.1083 | 1.0000 | 1.0000 | 0.0000 | 5162 |
| pooled_h1 | 2953 | +0.0119 | +35.1 | +0.0100 | +0.1154 | 1.0000 | 1.0000 | 0.0000 | 2953 |
| pooled_h2 | 2209 | -0.0229 | -50.5 | -0.0184 | +0.0988 | 1.0000 | 1.0000 | 0.0000 | 2209 |
| vault_all | 1767 | -0.0105 | -18.5 | -0.0101 | +0.0913 | 1.0000 | 1.0000 | 0.0000 | 1767 |
| vault_h1 | 991 | +0.0487 | +48.3 | +0.0452 | +0.1261 | 0.9944 | 0.9944 | 0.0056 | 991 |
| vault_h2 | 776 | -0.0860 | -66.8 | -0.0807 | +0.0470 | 1.0000 | 1.0000 | 0.0001 | 776 |
| others_all | 3395 | +0.0009 | +3.1 | +0.0020 | +0.1171 | 1.0000 | 1.0000 | 0.0000 | 3395 |
| others_h1 | 1962 | -0.0067 | -13.2 | -0.0077 | +0.1100 | 1.0000 | 1.0000 | 0.0000 | 1962 |
| others_h2 | 1433 | +0.0114 | +16.3 | +0.0154 | +0.1268 | 1.0000 | 1.0000 | 0.0000 | 1433 |

## Per market (all; descriptive)

| Market | trades | real mean R | placebo median | p |
|---|---|---|---|---|
| BTCUSDT | 879 | -0.0817 | +0.0532 | 1.0000 |
| ETHUSDT | 888 | +0.0601 | +0.1290 | 0.9805 |
| XAUUSD | 655 | -0.0148 | +0.1081 | 0.9998 |
| XAGUSD | 609 | -0.0201 | +0.1111 | 0.9999 |
| USDJPY | 636 | +0.0284 | +0.1271 | 0.9984 |
| SPX | 199 | +0.0937 | +0.2367 | 0.9999 |
| WTI | 653 | -0.0003 | +0.1097 | 0.9994 |
| BRENT | 643 | -0.0180 | +0.0923 | 0.9994 |

Gates: {"crypto": {"BTCUSDT": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 879, "mismatches": 0}, "ETHUSDT": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 888, "mismatches": 0}}, "metals": {"XAUUSD": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 655, "mismatches": 0}, "XAGUSD": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 609, "mismatches": 0}}, "fx": {"USDJPY": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 636, "mismatches": 0}}, "index": {"SPX": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 199, "mismatches": 0}}, "energy": {"WTI": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 653, "mismatches": 0}, "BRENT": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 643, "mismatches": 0}}}
