# Card pipeline: studying new cards five at a time

Owner, 15 Nov 2026: "we should have a mechanism to continue study next new 5 cards".

The engine reads about 50 cards; only the top-rated ones vote (`config.voting_by_group`). New cards enter through this
pipeline, a batch of up to five at a time. Nothing in it changes a trade until a card earns a vote AND the owner says yes.

## The steps for each batch

1. **Queue.** Candidates wait in the queue below (the owner can add, remove or reorder any line). Before building, check
   the card is not already read somewhere (`grep` the indicator in `engine15/`): if it is, give it its own card only if
   the owner wants it shown separately.
2. **Build as reading-only cards.** One source module per batch under `engine15/sources/` (pattern: `osc.py`, `flows.py`):
   `GROUPS`, `features(index15, asset, bars=None)`, `describe(row, asset)`, `update()`. Closed bars only; higher
   timeframes through `data.htf_on_15`. Tests: no look-ahead (truncation test), ranges, plain-English text.
   Add to `sources.MODULES`, bump `config.version` (a patch number: readings change, trades do not), set
   `VERSION_NOTE` so the journal says what changed, restart the live loop between steps. Not voting.
3. **Rate on history.** Re-run the card rating for the groups the batch applies to
   (`py -3 research/rate_cards.py <group>`, one group at a time, heavy-job lock): it ranks every card by its steadiest
   reading in both halves of 2020 onward. In-sample: a rating ranks cards, it proves no edge.
4. **Grade forward.** The cards are journaled every 15 minutes from go-live. After at least 30 days live, rate again on
   the forward rows only and compare with the history rank.
5. **Promotion (owner's word).** A batch card is proposed for a vote only if, in both the history rating and the 30-day
   forward check, it beats the weakest current voter of that group. A change to the voting list is a new minor version
   (v5.x), registered in `research/HYPOTHESES.md` first, and goes live only on the owner's yes. A voter that falls
   below the floor in a later rating is proposed for removal the same way.
   **Not a near-copy (17 Nov 2026, owner: "Ok add it"):** a card is not proposed as an
   additional voter if its readings overlap a current voter's of that group at |rho| >= 0.70 in BOTH halves (the H54
   measure: `research/card_overlap.py`, the reading-overlap matrix). If it ranks clearly above that voter in both the
   history rating and the 30-day forward check, it may be proposed as a REPLACEMENT for that voter instead (one idea,
   one vote). Existing near-copies among the voters are not removed by this rule; removal is a new version and the
   owner's decision.
6. **Next batch.** When a batch is live (step 2 done), the next five can be built; ratings run monthly or after each
   batch, whichever comes first.

## Batches

| Batch | Cards | Status |
|---|---|---|
| 0 | Binance positioning, Bitfinex margin, CME positioning, on-chain activity (`sources/flows.py`) | live 13 Nov 2026 (v5.1.1), reading-only; rated 17 Nov 2026 |
| 1 | Supertrend 15m-daily, StochRSI 15m-daily (`sources/osc.py`) | live 15 Nov 2026 10:21 UTC (v5.1.2), reading-only; rated 17 Nov 2026 |
| 2 | Parabolic SAR, Money Flow Index, Volume profile, Heikin-Ashi trend, Aroon/Vortex (`sources/osc2.py`) | live 15 Nov 2026 10:21 UTC (v5.1.2), reading-only; rated 17 Nov 2026 |
| 2b | CCI 15m-daily, all markets (`sources/osc3.py`), owner's request for metals | live 15 Nov 2026 as v5.2.1, reading-only; rated 17 Nov 2026 |
| 3c | Crypto: Deribit options flow, Korea premium, CME gap (spot proxy: no clean free CME price source), BTC dominance (tracked-basket proxy, reads ~6-7 points above a full-market figure), spot vs perp leadership, cross-exchange funding/OI (OKX only ~3 months free) (`sources/cryptox.py`) | owner "Yes" 15 Nov 2026; live as v5.2.2, BTC/ETH only, reading-only; rated 17 Nov 2026 |
| 3 | Williams %R, Chaikin money flow / OBV divergence, Elder-Ray, pivot points, RSI divergence (`sources/osc4.py`) + the daily range budget card (`sources/adr.py`, from H44) | owner "Yes" 16 Nov 2026; live as v5.2.3, reading-only; rated 17 Nov 2026 |
| 4 | Fisher Transform, Ultimate Oscillator, TRIX, Linear-regression channel, Mass Index (`sources/osc5.py`) | owner "let's continue pending tasks" 17 Nov 2026; wired as v5.2.4 (17 Nov 2026), reading-only; rated 17 Nov 2026 |
| 5 | next five (to be proposed) | waiting for the owner's go |

Rating of 17 Nov 2026 (step 3 for batches 0 to 4): `research/out/card_rating_summary_20261117.md`, files in
`research/out/card_rating_20261117/` (run through `research/rate_cards_snapshot.py`, history before the sealed holdout;
the page's rating files of 11 Nov are untouched). In-sample ranks, no proof of an edge; nothing is proposed for a vote
before step 4. Duplicate cards are studied in H54 (`research/out/card_overlap_20261117.md`).

## Queue for batch 3 (proposed by Claude, 15 Nov 2026; the owner edits freely)

Not yet read anywhere in the engine (check with grep before building), one per family:

1. **Williams %R** (15m to daily): where the close sits in the recent range; overbought / oversold.
2. **Chaikin Money Flow / OBV divergence** (1h to daily): volume flow and whether it disagrees with price.
3. **Elder-Ray** (1h to daily): bull and bear power around the 13-period EMA.
4. **Pivot points** (classic and Camarilla, daily and weekly): the levels and where price sits against them.
5. **RSI divergence detector** (15m to 4h): price makes a new high/low that RSI does not confirm.

Later candidates: Keltner position, Donchian breakouts as a card, ADX/DMI as its own card, Ichimoku on daily,
liquidation history (paid, owner said "Not now").

Note (17 Nov 2026): Keltner, Bollinger, ADX/DMI and TTM squeeze are already read in `sources/ltf.py`, Ichimoku and
Kaufman efficiency in `sources/trendtools.py`, Donchian in `evidence.py`; so batch 4 took five families read nowhere:
Fisher Transform, Ultimate Oscillator, TRIX, Linear-regression channel, Mass Index. Still unread for batch 5: Hurst
exponent, Choppiness Index, Chande momentum, Coppock curve, Ulcer index.
