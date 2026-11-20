# Mind 15

A 15-minute thinking engine for eight markets (BTC, ETH, gold, silver, USDJPY, the S&P 500, WTI and Brent). The engine
itself is paper only: it reads public market data, writes local files and holds no exchange key. One exception, by the
owner's decision of 18 Nov 2026: it SENDS its BTC/ETH setups book to the site's VIP vault, which places real orders for
opted-in accounts. Read CLAUDE.md, "The money path", before changing anything.

Every 15 minutes it reads ten sources, turns them into odds for "up first / down first /
neither", takes a side under a must-be-positioned mandate (at most 1 hour flat), journals
its reasoning, and grades its earlier calls so it can learn which sources to trust.

- **How it thinks:** [THOUGHT_PROCESS.md](THOUGHT_PROCESS.md)
- **Support and resistance research:** [docs/SUPPORT_RESISTANCE.md](docs/SUPPORT_RESISTANCE.md)
- **Journal:** `journal/<day>.md` (live), `journal/replay/` (history, on request)
- **Web tab data:** `out/live/page.json`

```
py -3 -m engine15 update        # data
py -3 -m engine15 backtest      # replay history (warm-up; a few minutes)
py -3 -m engine15 step          # one live step now
py -3 -m engine15 live          # keep stepping every 15 minutes
py -3 -m engine15 ask now       # what it thinks, in plain English
py -3 -m pytest tests -q        # tests
```

Layout: `engine15/` (data, indicators, evidence, levels, labels, model, policy, backtest,
journal, livefeeds, econ, live, export, postmortem, discuss), `data/` (bars, funding,
macro, calendar, live reads, raw order-book profiles), `out/`, `journal/`, `tests/`.

Needs Python 3.12 with pandas, numpy and requests. No other packages.
