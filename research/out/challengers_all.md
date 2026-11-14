# All books, last 120 days, eight markets ($80,000 start), 11 Nov 2026

In-sample history (research/challengers.py, run one market group at a time). Not proof: forward results decide.

| Book | P&L | Return | Worst drawdown (a group) | crypto | metals | USDJPY | S&P | oil |
|---|---|---|---|---|---|---|---|---|
| A: pullback entry | +7,889 | +9.9% | -29.3% | +3,271 | +991 | +5,292 | +408 | -2,074 |
| H5: damp slow voices | +7,031 | +8.8% | -34.4% | +3,031 | +1,101 | +5,892 | +408 | -3,400 |
| Main rule (v5) | +6,114 | +7.6% | -34.4% | +3,031 | +1,101 | +4,975 | +408 | -3,400 |
| H3: limit on flip exits | +6,057 | +7.6% | -34.4% | +3,086 | +1,134 | +4,771 | +408 | -3,341 |
| v4 (no bias rule) | +5,127 | +6.4% | -34.4% | +2,534 | +912 | +4,209 | +408 | -2,936 |
| Y: 4h yardstick | +4,865 | +6.1% | -26.0% | +2,003 | +558 | +5,057 | -670 | -2,084 |
| Buy and hold | +3,424 | +4.3% | -24.3% | +3,263 | -947 | -215 | -22 | +1,345 |
| Y: daily yardstick | +1,192 | +1.5% | -28.3% | +269 | -1,325 | +6,403 | -207 | -3,949 |
| B: targets | +474 | +0.6% | -27.3% | +2,563 | +810 | -1,259 | +484 | -2,124 |
| B: trailing stop | -6,830 | -8.5% | -32.1% | -2,541 | -611 | -2,019 | +614 | -2,273 |

Notes: USDJPY results include leverage (sized to risk 2% at the stop, ~6x). Swing books (H18/H19) are judged live
only (this study does not build their odds). The daily yardstick decides at each market's own daily close
(fixed 11 Nov: S&P 16:00 New York; gold, silver, USDJPY, oil 17:00 New York; crypto 00:00 UTC).
