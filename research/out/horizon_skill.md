# Skill per horizon (charter M6)

Written 2026-11-11 07:32 UTC (week 2026-W46) from the live steps' own graded calls. Which clock does the engine read best, market by market? A hit rate is the share of calls graded up or down whose direction was right; the claimed-edge hit rate counts only calls where the mind said at least a 5-point edge. 50% is a coin flip; a few days of calls say little (counts are shown).

- **1h**: 1 hour (4 bars, 0.75 x ATR 1h)
- **4h**: 4 hours (16 bars, 1 x ATR 1h)
- **24h**: 24 hours (the main engine: 96 bars, 1.5 x ATR 1h; S&P 26 bars)

| Market | Horizon | 7d hit | 7d edge hit (calls) | 30d hit | 30d edge hit (calls) |
|---|---|---|---|---|---|
| BTCUSDT | 1h | 50.0% | 0.0% (3) | 52.7% | 56.0% (25) |
| BTCUSDT | 4h | 54.6% | - (0) | 52.0% | 14.3% (7) |
| BTCUSDT | 24h | 60.2% | 40.0% (10) | 52.1% | 23.0% (226) |
| ETHUSDT | 1h | 53.6% | 0.0% (3) | 54.6% | 38.1% (21) |
| ETHUSDT | 4h | 56.9% | - (0) | 50.7% | 25.0% (8) |
| ETHUSDT | 24h | 73.5% | 28.3% (46) | 52.6% | 24.8% (302) |

Paper only. A history read can reject an idea, never prove one; these are forward counts.
