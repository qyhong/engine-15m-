## How this was run, and what to be careful with

- **Where.** On the research server (`/data/mind15`, code = the laptop's git HEAD, engine think15-v5.2.4), 17 Nov 2026
  06:12 to about 07:00 UTC, two workers at low priority, one group at a time per worker.
- **Nothing the engine reads was written.** `research/rate_cards.py` builds its readings from the bars itself
  (`evidence.build`); it never opens `data/evcache` and writes nothing under `data/`. Run as it stands it WOULD overwrite
  `research/out/card_rating_<group>.json` and `voting_by_group.json`, which the live page (`export.group_rating`) and
  `tests/test_rate_cards.py` read. So it was run through `research/rate_cards_snapshot.py` (new, same method, same code):
  results in `research/out/card_rating_20261117/`, temporary files under that folder (the server's `/tmp` is memory),
  removed when each group finished. The rating the page shows is still the one of 11 Nov 2026.
- **The sealed holdout was not read.** History stops at 2025-11-10 23:45 UTC (`rate_cards.run(end="2025-11-11")`). The
  halves are the method's own: split at the median graded call, which lands in early December 2022 (the 11 Nov rating
  ran to 11 Nov 2026 and split in mid 2023). A card's place here and its place on the page are therefore not the same
  measurement; the last column of each table gives the 11 Nov place for orientation only.
- **The index group (S&P 500).** The brief said to rate it only if its reading cache is on the current version. The
  cache is NOT (last built 16 Nov 21:04 UTC on the earlier version; it rebuilds at the 14:30 UTC open), but this rating
  does not use the cache at all, so the index was rated from the bars with the current code like the other groups. If
  the owner prefers to wait for the cache, ignore the index section; nothing depends on it.
- **A rating at the top of the list can be an artefact.** The method takes each card's single steadiest reading. A
  yes/no reading that fires rarely (a few hundred sessions a half, bunched into a handful of episodes) can show a
  lopsided score from a few events. **Mass Index is the clear case:** its "bulge" reading tops metals and energy with
  halves like 36.9 / 43.5 and 43.9 / 25.8, but gold and silver disagree with each other (XAU 51.6 / 41.7, XAG 6.9 /
  46.7), BTC and ETH point opposite ways (61.7 / 57.8 against 38.4 / 37.1), and in oil neither market has enough rows
  on its own to be scored. Read it as "too few independent events to rate", not as the best card. The same caution, to
  a lesser degree, applies to every daily reading (for example the Ultimate Oscillator's daily zone in metals, the
  OPEC+ week): a daily value is repeated on up to 96 sessions, so the session counts overstate the evidence.
- **Cards with no rating.** Live-only cards (Kronos, order book, liquidation proxy) have no history; "Long/short
  positioning" and "Spot ETF flows" have too little history before the holdout. Several crypto cards of batches 0 and 3c
  have short histories (OKX funding about three months, Deribit flow, Korea premium), so their halves rest on less data
  than the price-based cards.
- **What this is for.** Step 3 of the card pipeline. A card is proposed for a vote only after step 4 as well (30 days of
  forward grading) and the owner's yes. The lists of "non-voting cards above the weakest voter" are that and nothing
  more: lists.
