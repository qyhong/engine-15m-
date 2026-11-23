# H81b: causal side placebo: each trade's side drawn from the long share of the book's previous 20 trades on the market (and a fair coin)

## Conclusion

**The Setups book's choice of side (b_targets) IS distinguishable from its placebo (sides drawn from the long share of its previous 20 trades on the market) at p = 0.0338** (primary: pooled mean R per trade over the eight markets, one-sided, real at least as good; 200000 draws). Real -0.0030R a trade; placebo median -0.0291R (5%-95%: -0.0525 to -0.0055). Lower-tail p (real at most as good) = 0.9662.

Secondary (registered, not used for the conclusion): The Setups book's choice of side (b_targets) IS distinguishable from a fair coin for each trade's side at p = 0.0105 (lower-tail p = 0.9895; placebo median -0.0405R).

Exact placebo expectations (descriptive): `{"pooled": {"main": -0.029050816287546466, "coin": -0.0404264053800163}, "vault": {"main": -0.03935261549455284, "coin": -0.04092600968764028}, "others": {"main": -0.023689025654621502, "coin": -0.04016637568588623}}`

Never read as proof: this family makes many tests (see the ledger in research/HYPOTHESES.md), and one or two will look significant by chance. Data end at the last session at or before 2025-11-10 23:45 (the holdout is not read).

## All cells (p_upper: share of draws at least as good, +1 corrected)

| Cell | real trades | real mean R | real sum R | current rule mean R | placebo median mean R | p mean R | p sum R | p lower (mean) | placebo trades (median) |
|---|---|---|---|---|---|---|---|---|---|
| pooled_all | 5162 | -0.0030 | -15.4 | -0.0021 | -0.0291 | 0.0338 | 0.0338 | 0.9662 | 5162 |
| pooled_h1 | 2953 | +0.0119 | +35.1 | +0.0100 | -0.0102 | 0.1225 | 0.1225 | 0.8775 | 2953 |
| pooled_h2 | 2209 | -0.0229 | -50.5 | -0.0184 | -0.0543 | 0.0739 | 0.0739 | 0.9261 | 2209 |
| vault_all | 1767 | -0.0105 | -18.5 | -0.0101 | -0.0394 | 0.1277 | 0.1277 | 0.8723 | 1767 |
| vault_h1 | 991 | +0.0487 | +48.3 | +0.0452 | -0.0025 | 0.0664 | 0.0664 | 0.9336 | 991 |
| vault_h2 | 776 | -0.0860 | -66.8 | -0.0807 | -0.0867 | 0.4936 | 0.4936 | 0.5064 | 776 |
| others_all | 3395 | +0.0009 | +3.1 | +0.0020 | -0.0237 | 0.0763 | 0.0763 | 0.9237 | 3395 |
| others_h1 | 1962 | -0.0067 | -13.2 | -0.0077 | -0.0141 | 0.3729 | 0.3729 | 0.6271 | 1962 |
| others_h2 | 1433 | +0.0114 | +16.3 | +0.0154 | -0.0369 | 0.0325 | 0.0325 | 0.9675 | 1433 |

## Per market (all; descriptive)

| Market | trades | real mean R | placebo median | p |
|---|---|---|---|---|
| BTCUSDT | 879 | -0.0817 | -0.0694 | 0.6346 |
| ETHUSDT | 888 | +0.0601 | -0.0096 | 0.0273 |
| XAUUSD | 655 | -0.0148 | -0.0020 | 0.6306 |
| XAGUSD | 609 | -0.0201 | +0.0152 | 0.8067 |
| USDJPY | 636 | +0.0284 | -0.0266 | 0.0784 |
| SPX | 199 | +0.0937 | +0.0041 | 0.1004 |
| WTI | 653 | -0.0003 | -0.0561 | 0.0785 |
| BRENT | 643 | -0.0180 | -0.0557 | 0.1769 |

Gates: {"crypto": {"BTCUSDT": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 879, "mismatches": 0}, "ETHUSDT": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 888, "mismatches": 0}}, "metals": {"XAUUSD": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 655, "mismatches": 0}, "XAGUSD": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 609, "mismatches": 0}}, "fx": {"USDJPY": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 636, "mismatches": 0}}, "index": {"SPX": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 199, "mismatches": 0}}, "energy": {"WTI": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 653, "mismatches": 0}, "BRENT": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 643, "mismatches": 0}}}
