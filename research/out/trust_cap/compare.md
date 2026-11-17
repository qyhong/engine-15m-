# H43: 40% trust cap vs no cap on history (recorded, not a gate; updated 17 Nov 2026)

Script `research/trust_cap_compare.py` (the H42 machinery; live constants eta 0.2 / floor 0.02; the cap applied to
the final mixing weights as v5.2 does). Development data to 2025-11-10; halves as in H42. Both runs include every
card up to v5.2.2 as (non-voting) voices, so the no-cap numbers differ slightly from H42's.

| Group, half | log-loss no cap -> cap | books, no cap | books, cap 40% |
|---|---|---|---|
| crypto, 1st | 0.84086 -> 0.84029 | BTC -47% (Sharpe 0.00), ETH +540% (1.20) | BTC -5% (0.30), ETH +756% (1.36) |
| crypto, 2nd | 0.86692 -> 0.86672 | BTC +136% (0.88), ETH +94% (0.69) | BTC +151% (0.93), ETH +58% (0.56) |
| metals, 1st | 0.80735 -> 0.80705 | gold -46%, silver +26% | gold -45%, silver +33% |
| metals, 2nd | 0.79084 -> 0.79076 | gold +420%, silver -45% | identical |
| fx, 1st | 0.79086 -> 0.79135 | USDJPY +146% | +149% |
| fx, 2nd | 0.80191 -> 0.80190 | USDJPY +21% | identical |
| energy, 1st | 0.75845 -> 0.75696 | WTI +289%, Brent +255% | WTI +284%, Brent +336% |
| energy, 2nd | 0.73644 -> 0.73529 | WTI -38%, Brent -50% | WTI -54%, Brent -53% |
| index, 1st | 1.07687 -> 1.07687 | S&P +2.0% (15 trades) | identical |
| index, 2nd | 1.07604 -> 1.07604 | S&P +59.6% | identical (run 16 Nov 16:10 UTC on the server; one card held over 30% of the say only 1% of the time, never over 40%) |

Reading: the cap almost never binds in metals, fx and the S&P (one card held over half the say 0-3% of the time), so they
trade the same. In crypto and oil it binds more (17-21% of the time): predictions are marginally better in 7 of 8
group-halves, and the books move both ways (better in the first half, mixed or worse in the second). Same conclusion
as the crypto-only read: no consistent effect either way; the live record from 15 Nov decides.
