# P1 liquidation hunt: post-mortem of the first 65 live trades (15 Nov 2026)

Owner, 15 Nov 2026: "i think liquidity hunt workflow might got issue, it should be almost 100% winning rate,
dissect do post morterm and improve rather test the same setup".

Source: a read-only replay of `engine15/playbook.py` (the book holds no state; the same bars give the same rows),
11 Nov 2026 to 15 Nov 2026 05:30 UTC, six markets. Script: scratchpad `p1_postmortem.py`; rows `p1_trades.csv`.

## 1. Is the code doing what the rule says?

Yes. Checked: the sweep test (pool beyond the prior close, a bar through it by >= 0.25 ATR, a close back inside on
the sweep bar or within 2 bars, swept-side wick >= 50% of the sweep candle), the funding confirmation on BTC/ETH
(`prepare()` loads funding from disk when none is passed, so the filter is live), entry at the next open (median
gap from the reclaim close: 0.00R), stop at the extreme + 0.1 ATR, half at 1R / rest at 2R, break-even after 1R,
16-bar time exit, the asset's own fee. No bug found. The losses come from the rule, not the plumbing.

Expectation check: the registered H6 note already said it lost on 2020-2026 history in both halves (about zero
before costs). No sweep-fade setup wins nearly every time; stop-runs that keep going are exactly the losers.

## 2. The numbers

| | |
|---|---|
| Closed trades | 65 |
| Net / gross / fees | -$1,421 / -$935 / $485 |
| Won (net > 0) | 32% |
| Reached Target 1 (1R) | 31% |
| Mean result | -0.38R before costs, -0.68R after |
| Median stop distance | 0.23% of price (USDJPY 0.05%) |
| Median cost per trade | 0.26R (BTC 0.49R) |

By exit: STOP 53 trades (-$1,822, -0.98R mean); T2 6 (+$359); TIME 6 (+$43).

## 3. What went wrong (in order of size)

1. **Fading the trend.** Long fades (buying a sweep of a low) lost -$1,346 on 36 trades, 19% won. Short fades lost
   only -$74 on 29 trades, 48% won. Crypto, gold and silver fell over these days: the rule kept buying stop-runs of
   lows in a downtrend, and the "stop-run" was the trend continuing. It has no trend filter.
2. **The stop sits where the next sweep goes.** The stop is just 0.1 ATR beyond the sweep's extreme. 20 of 53 stops
   hit within 2 bars, and 22 of the 53 stopped trades reached the 1R target within the next 16 bars after stopping
   out: the direction was right but the level was re-swept first (the double sweep). Winners had wider stops
   (median 0.35% of price) than losers (0.20%).
3. **Costs on tiny stops.** With stops of 0.2% to 0.4%, a round trip costs 0.26R on the median trade and about 0.5R
   on BTC: a trade must reach about +0.5R just to break even on BTC.
4. **Weak pools.** Round numbers gave 24 of 65 trades (-$631); swing lows won 1 in 9. The 24h and prior-day highs were
   about flat.
5. **Small sample, one regime.** Four days, mostly one falling market. These are directions to test, not proof.

## 4. What to change (registered as H41 before any test)

- Trade a sweep only against the trend's weak side: fade a sweep of a HIGH only when the higher-timeframe bias is
  down (or neutral), a sweep of a LOW only when it is up (the engine's v5 bias, `playbook.htf_bias`).
- Survive the double sweep: a wider stop (beyond the extreme + 0.5 ATR) and/or enter only after confirmation (a
  15m close back beyond the reclaimed level that holds for one more bar, or a retest entry).
- Drop round-number pools; keep the 24h, 7-day, prior-day and swing pools.
- Size targets in R so costs are a smaller share (a wider stop does this by itself).

The original P1 keeps running unchanged as the control until its own verdict rule (200 trades or 30 days) or the
owner retires it; the improved rules are tested on history first (dev data, never the sealed holdout) and, if they
earn it, run forward as a new book.

## 5. Result of the improvement test (H41, 15 Nov 2026; `research/out/liqhunt2/study.md`)

No pass. 8 registered variants (trend filter, stop pads 0.1/0.5/1.0 ATR, confirmation close, limit retest, 1.5R exit,
no round numbers), 2020 to Nov 2025, six markets, about 23,000 trades per variant. Every variant averaged -0.03R to
+0.01R BEFORE costs in both halves: the sweep fade has no edge on 15m bars to remove costs from. Wider stops cut the
cost share (0.25R -> 0.13-0.19R) and made it lose less than the original (-0.066% vs -0.076% a trade in the second
half), but all six markets still lost. On history the trend filter made no difference; confirmation entries were worse.
The live four days' trend effect is one regime, not a lasting pattern. Variants tried overall: 37.
