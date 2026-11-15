# H43: 40% trust cap vs no cap on history (recorded, not a gate; 15 Nov 2026)

Script `research/trust_cap_compare.py` (the H42 machinery, live constants eta 0.2 / floor 0.02, cap applied to the final
mixing weights as v5.2 does). Development data to 2025-11-10; halves split as in H42. Both runs include the v5.1.2
cards as (non-voting) voices.

**Crypto only so far.** Metals, fx, index and energy stopped: their evidence caches still have the pre-v5.1.2 columns
(those markets are closed until Monday 16 Nov; the live engine rebuilds each cache at its first step). Re-run then.

| Crypto | log-loss | hit % | BTC return / Sharpe / max DD / trades | ETH return / Sharpe / max DD / trades |
|---|---|---|---|---|
| no cap, 1st half | 0.84091 | 50.18 | -64.8% / -0.21 / -79.2% / 160 | +554% / 1.21 / -54.0% / 120 |
| cap 40%, 1st half | 0.84032 | 50.21 | -11.7% / 0.26 / -73.3% / 123 | +738% / 1.34 / -54.0% / 96 |
| no cap, 2nd half | 0.86688 | 51.71 | +118.7% / 0.82 / -51.2% / 113 | +133.2% / 0.80 / -56.7% / 98 |
| cap 40%, 2nd half | 0.86669 | 51.67 | +115.6% / 0.81 / -60.4% / 86 | +38.6% / 0.47 / -57.4% / 84 |

Reading: the cap predicts marginally better in both halves (log-loss -0.06% / -0.02%) and trades less often. The book
results move a lot in both directions (much better in the first half, ETH much worse in the second): the main book
lives on a few long holds, so a small change in the odds moves which holds are taken. On crypto alone there is no
consistent sign either way. Not a reason to reverse the owner's choice; not evidence that it helps.
