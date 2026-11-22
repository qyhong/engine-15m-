# H99: no new entry when 24-hour realised volatility is in a trailing third

**Conclusion: the current setting was already the choice.**


## The choice period (the only numbers the choice used)

| value | pooled sum R | BTC+ETH sum R | trades |
|---|---|---|---|
| none (current) | +25.2 | +46.9 | 2945 |
| block_top_third | -37.7 | +14.3 | 2612 |
| block_bottom_third | +49.3 | +36.8 | 2600 |

A pass here is a proposal for a forward PAPER shadow book only, and needs the owner's word. Nothing in the engine,
the Setups book or the vault changes. The holdout (2025-11-11 onward) was not loaded.
