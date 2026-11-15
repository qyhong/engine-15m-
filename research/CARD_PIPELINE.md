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
6. **Next batch.** When a batch is live (step 2 done), the next five can be built; ratings run monthly or after each
   batch, whichever comes first.

## Batches

| Batch | Cards | Status |
|---|---|---|
| 0 | Binance positioning, Bitfinex margin, CME positioning, on-chain activity (`sources/flows.py`) | live 13 Nov 2026 (v5.1.1), reading-only |
| 1 | Supertrend 15m-daily, StochRSI 15m-daily (`sources/osc.py`) | built and tested 15 Nov 2026; goes live as v5.1.2 after H42 finishes |
| 2 | Parabolic SAR, Money Flow Index, Volume profile, Heikin-Ashi trend, Aroon/Vortex (`sources/osc2.py`) | owner "Ok" 15 Nov 2026; built and tested; goes live with batch 1 as v5.1.2 after H42 |
| 3 | next five from the queue | waiting for the owner's go |

## Queue (proposed by Claude, 15 Nov 2026; the owner edits freely)

Not yet read anywhere in the engine (checked with grep, 15 Nov 2026), one per family:

1. **Parabolic SAR** (15m to daily): trend direction and a trailing-stop level, how far price is from it, bars since it flipped.
2. **Money Flow Index** (15m to daily): a volume-weighted RSI; overbought / oversold with volume behind it.
3. **Volume profile** (session and 7-day): point of control, value-area high / low, where price sits against them.
4. **Heikin-Ashi trend** (15m to 4h): smoothed candles' colour run and wick-less candles (trend strength).
5. **Aroon / Vortex** (1h to daily): how recently the high or low was made (trend age) and the vortex cross.

Later candidates: Williams %R, Chaikin Money Flow / OBV divergence, Elder-Ray, pivot points (classic / Camarilla),
RSI divergence detector, liquidation history (paid, owner said "Not now").
