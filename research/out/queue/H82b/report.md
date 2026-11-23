# H82b: causal entry-time placebo: each trade, same side, moved to a random bar at or after its real entry, within the median of the book's previous 20 entry gaps

## Conclusion

**The Setups book's entry timing (b_targets) is NOT distinguishable from its placebo (the same trades moved to random bars at or after the real entry, within the median of its previous 20 entry gaps) at p = 0.0802** (primary: pooled mean R per trade over the eight markets, one-sided, real at least as good; 200000 draws). Real -0.0030R a trade; placebo median -0.0192R (5%-95%: -0.0381 to -0.0002). Lower-tail p (real at most as good) = 0.9198.

Exact placebo expectations (descriptive): `{"pooled": {"main": -0.019168830678588013}, "vault": {"main": -0.03343785066413662}, "others": {"main": -0.01174221556387096}}`

Windows (H82b, descriptive): `{"BTCUSDT": {"window_median_bars": 114.0, "share_window_past_next_entry": 0.49715585893060293}, "ETHUSDT": {"window_median_bars": 120.0, "share_window_past_next_entry": 0.49774774774774777}, "XAUUSD": {"window_median_bars": 124.0, "share_window_past_next_entry": 0.48396946564885496}, "XAGUSD": {"window_median_bars": 126.0, "share_window_past_next_entry": 0.4942528735632184}, "USDJPY": {"window_median_bars": 124.0, "share_window_past_next_entry": 0.49842767295597484}, "SPX": {"window_median_bars": 114.0, "share_window_past_next_entry": 0.5025125628140703}, "WTI": {"window_median_bars": 118.0, "share_window_past_next_entry": 0.5038284839203675}, "BRENT": {"window_median_bars": 108.0, "share_window_past_next_entry": 0.49300155520995337}}`

Never read as proof: this family makes many tests (see the ledger in research/HYPOTHESES.md), and one or two will look significant by chance. Data end at the last session at or before 2025-11-10 23:45 (the holdout is not read).

## All cells (p_upper: share of draws at least as good, +1 corrected)

| Cell | real trades | real mean R | real sum R | current rule mean R | placebo median mean R | p mean R | p sum R | p lower (mean) | placebo trades (median) |
|---|---|---|---|---|---|---|---|---|---|
| pooled_all | 5162 | -0.0030 | -15.4 | -0.0021 | -0.0192 | 0.0802 | 0.0802 | 0.9198 | 5162 |
| pooled_h1 | 2953 | +0.0119 | +35.1 | +0.0100 | -0.0139 | 0.0431 | 0.0431 | 0.9569 | 2953 |
| pooled_h2 | 2209 | -0.0229 | -50.5 | -0.0184 | -0.0262 | 0.4248 | 0.4248 | 0.5752 | 2209 |
| vault_all | 1767 | -0.0105 | -18.5 | -0.0101 | -0.0334 | 0.1108 | 0.1108 | 0.8892 | 1767 |
| vault_h1 | 991 | +0.0487 | +48.3 | +0.0452 | -0.0241 | 0.0020 | 0.0020 | 0.9980 | 991 |
| vault_h2 | 776 | -0.0860 | -66.8 | -0.0807 | -0.0455 | 0.9245 | 0.9245 | 0.0755 | 776 |
| others_all | 3395 | +0.0009 | +3.1 | +0.0020 | -0.0118 | 0.1917 | 0.1917 | 0.8083 | 3395 |
| others_h1 | 1962 | -0.0067 | -13.2 | -0.0077 | -0.0089 | 0.4551 | 0.4551 | 0.5449 | 1962 |
| others_h2 | 1433 | +0.0114 | +16.3 | +0.0154 | -0.0158 | 0.1154 | 0.1154 | 0.8846 | 1433 |

## Per market (all; descriptive)

| Market | trades | real mean R | placebo median | p |
|---|---|---|---|---|
| BTCUSDT | 879 | -0.0817 | -0.0631 | 0.7610 |
| ETHUSDT | 888 | +0.0601 | -0.0042 | 0.0085 |
| XAUUSD | 655 | -0.0148 | -0.0038 | 0.6312 |
| XAGUSD | 609 | -0.0201 | -0.0662 | 0.0827 |
| USDJPY | 636 | +0.0284 | +0.0160 | 0.3608 |
| SPX | 199 | +0.0937 | -0.0023 | 0.0632 |
| WTI | 653 | -0.0003 | +0.0207 | 0.7362 |
| BRENT | 643 | -0.0180 | -0.0320 | 0.3351 |

Gates: {"crypto": {"BTCUSDT": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 879, "mismatches": 0}, "ETHUSDT": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 888, "mismatches": 0}}, "metals": {"XAUUSD": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 655, "mismatches": 0}, "XAGUSD": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 609, "mismatches": 0}}, "fx": {"USDJPY": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 636, "mismatches": 0}}, "index": {"SPX": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 199, "mismatches": 0}}, "energy": {"WTI": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 653, "mismatches": 0}, "BRENT": {"run_is_engine_b_targets": true, "replay_gate": true, "trades": 643, "mismatches": 0}}}
