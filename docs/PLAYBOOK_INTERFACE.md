# Strategy books: the one interface every playbook module follows

Owner, 11 Nov 2026: build twelve 15-minute strategy books (liquidation hunt, breakout trap,
opening range breakout, overnight gap fill, squeeze breakout, VWAP reversion/reclaim, session
plays, fair value gap / order block, crypto liquidation cascades, round-number magnets, release-
day trades beyond CPI, and the trend pullback already in the shadow books). Each is a STANDALONE
rule-based paper book, recomputed from the bars at every live step (like `engine15/shadow.py`'s
H1), on all six markets where it applies. The main session hooks every module into the live
loop and page.json the same way, so every module must expose exactly this:

```python
BOOKS = {                     # book id -> facts (ids are short, lowercase, unique across modules)
    "p1_liqhunt": {"title": "Liquidation hunt", "hypothesis": "H6", "registered": "2026-11-11",
                   "assets": ("BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "USDJPY", "SPX")},
}

def step(bars, now_ms=None):
    """bars: {asset: 15m frame from engine15.data.load} (the live loop passes what it has).
    -> list of dict rows, one per trade or pending setup since each book's registration date:
       book, asset, status ("WAITING" | "OPEN" | "CLOSED"), side (1 / -1),
       setup_utc, entry_utc, entry, stop, target_1, target_2,
       exit_utc, exit, why_out ("STOP" | "T1" | "T2" | "TIME" | "OPEN"),
       r (result in R), pnl_usd, fees_usd (at $10,000 per trade, the asset's own fee a side:
       config CFG["asset_cost"] / CFG["cost_side"]), text (one plain-English sentence).
    Stateless and deterministic: the same bars give the same rows. Closed bars only."""

def page_block(rows):
    """-> small dict for page.json: per book: title, hypothesis, open setups/trades (with entry,
    stop, targets), the last 5 closed trades, totals (trades, win rate, avg R, net $)."""
```

Fill rule for all books: decision at the close of bar i, fill at the open of bar i+1; a stop and a
target inside the same bar count as the stop first; one open trade per book per asset at a time.

History study for each module: `research/<module>_study.py` -> `research/out/<module>.md/.json`,
first half vs second half, per asset, after costs, every variant counted; the variant to register
is chosen on the first half only.

Hypothesis entries are DRAFTED in the module's doc (`docs/<MODULE>.md`); the main session copies
them into `research/HYPOTHESES.md` (numbering continues from H6).
