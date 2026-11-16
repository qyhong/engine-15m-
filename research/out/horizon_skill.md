# Skill per horizon (charter M6)

Written 2026-11-16 03:00 UTC (week 2026-W47) from the live steps' own graded calls. Which clock does the engine read best, market by market? A hit rate is the share of calls graded up or down whose direction was right; the claimed-edge hit rate counts only calls where the mind said at least a 5-point edge. 50% is a coin flip; a few days of calls say little (counts are shown).

- **1h**: 1 hour (4 bars, 0.75 x ATR 1h)
- **4h**: 4 hours (16 bars, 1 x ATR 1h)
- **24h**: 24 hours (the main engine: 96 bars, 1.5 x ATR 1h; S&P 26 bars)

| Market | Horizon | 7d hit | 7d edge hit (calls) | 30d hit | 30d edge hit (calls) |
|---|---|---|---|---|---|
| BTCUSDT | 1h | 57.6% | 36.4% (22) | 54.4% | 44.2% (43) |
| BTCUSDT | 4h | 60.4% | 67.7% (65) | 54.1% | 62.5% (72) |
| BTCUSDT | 24h | 67.0% | 79.3% (188) | 54.7% | 50.0% (414) |
| ETHUSDT | 1h | 53.5% | 46.4% (28) | 54.1% | 43.5% (46) |
| ETHUSDT | 4h | 62.5% | 62.2% (82) | 52.0% | 58.9% (90) |
| ETHUSDT | 24h | 65.9% | 62.1% (224) | 55.1% | 41.8% (471) |
| XAUUSD | 1h | 57.2% | - (0) | 52.6% | - (0) |
| XAUUSD | 4h | 45.1% | - (0) | 52.4% | - (0) |
| XAUUSD | 24h | 29.9% | - (0) | 54.9% | - (0) |
| XAGUSD | 1h | 48.6% | - (0) | 49.0% | - (0) |
| XAGUSD | 4h | 50.4% | - (0) | 53.0% | - (0) |
| XAGUSD | 24h | 30.6% | - (0) | 54.3% | - (0) |
| USDJPY | 1h | 49.1% | - (0) | 46.3% | - (0) |
| USDJPY | 4h | 58.0% | - (0) | 50.7% | - (0) |
| USDJPY | 24h | 33.3% | 25.0% (4) | 56.1% | 40.0% (65) |
| WTI | 1h | 50.9% | - (0) | 51.8% | - (0) |
| WTI | 4h | 40.1% | - (0) | 52.2% | 50.0% (6) |
| WTI | 24h | 42.8% | - (0) | 52.4% | 52.1% (654) |
| BRENT | 1h | 52.0% | - (0) | 50.3% | - (0) |
| BRENT | 4h | 56.9% | - (0) | 51.7% | 0.0% (5) |
| BRENT | 24h | 58.4% | - (0) | 52.7% | 54.6% (654) |
| SPX | 1h | 64.0% | - (0) | 53.5% | - (0) |
| SPX | 4h | 66.3% | - (0) | 54.6% | - (0) |
| SPX | 24h | 51.9% | - (0) | 53.1% | - (0) |

Paper only. A history read can reject an idea, never prove one; these are forward counts.
