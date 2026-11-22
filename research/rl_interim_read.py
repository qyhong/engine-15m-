# -*- coding: utf-8 -*-
"""rl_interim_read -- the registered 8-week interim read of the RL forward paper books. NOT a verdict.

Registered in research/HYPOTHESES.md ("Interim read of the RL forward books at 8 weeks", 22 Nov 2026) before this script
existed; owner, 22 Nov 2026: "Run all above". The 30-closed-trades-per-coin rule still decides every verdict; this read
changes no decision and every RL book stays NOT passed.

    py -3 -X utf8 research/rl_interim_read.py

For each book it REFUSES to print any comparison before that book's read date (8 weeks after its own start, UTC). On or
after it, it prints the registered read-outs for the window start -> read date only (closes at or before the read date),
rebuilt with forward5.risk_and_book from the books' own records (read only): per coin, the book against spot buy-and-hold
over the same days; for the Phase 6 books also against the momentum yardstick p8_mom over the SAME days only (from the
yardstick's start, 2026-11-23 00:00 UTC); the gross result split into agent-decided and fallback-decided parts with the
costs (forward5.agent_split); closed trades against the 30 per coin. There is deliberately no option to pretend another date.
"""
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

BAR_MS = 900000
STAKE = 10000.0
ASSETS = ("BTCUSDT", "ETHUSDT")
COIN = {"BTCUSDT": "BTC", "ETHUSDT": "ETH"}
READS = {                                       # book -> (start = go-live, read date = start + 56 days), UTC; registered
    "p5_rlq": ("2026-11-12 04:30", "2027-01-07 04:30"),
    "p6_mtrend": ("2026-11-13 03:00", "2027-01-08 03:00"),
    "p6_p4trend": ("2026-11-13 03:00", "2027-01-08 03:00"),
}
YARD_BOOK = "p8_mom"
YARD_START = "2026-11-23 00:00"
LEVEL_PTS = 1.0                                 # "level with" when two returns differ by less than 1.0 percentage point
NEED = 30                                       # the verdict rule: 30 closed forward trades per coin


def ms(utc):
    return int(pd.Timestamp(utc, tz="UTC").value // 10**6)


def due(book, now_ms):
    """True on or after the book's registered read date."""
    return int(now_ms) >= ms(READS[book][1])


def words(x, y):
    d = float(x) - float(y)
    return "level with" if abs(d) < LEVEL_PTS else ("ahead of" if d > 0 else "behind")


def line(book, asset, x, yard, y, start, end):
    """The registered sentence; the only verdict words are "ahead of", "behind" and "level with"."""
    return ("Interim read (8 weeks; not a verdict): %s %s %+.2f%% vs %s %+.2f%% over %s to %s UTC: %s %s by %.2f points."
            % (book, COIN.get(asset, asset), x, yard, y, start, end, words(x, y), yard, abs(float(x) - float(y))))


def refusal(book):
    return ("%s: the interim read is registered for %s UTC (8 weeks after its start, %s UTC); nothing is shown before then."
            % (book, READS[book][1], READS[book][0]))


# ---------------------------------------------------------------- computing (only ever reached on or after the date)
def _journal_path(book, asset):
    if book == "p5_rlq":
        return os.path.join(ROOT, "research", "out", "rl", "forward5", "decisions_%s.jsonl" % asset)
    sub = "forward8" if book == YARD_BOOK else "forward6"
    return os.path.join(ROOT, "research", "out", "rl", sub, "decisions_%s_%s.jsonl" % (book, asset))


def _book(book, asset, start_ms, end_ms):
    """The book rebuilt from its own record up to end_ms. -> (cfg, B, journal) or None."""
    from engine15 import data
    from engine15.rl import forward5 as f5
    from engine15.rl import forward6 as f6
    cfg = f5.load_cfg() if book == "p5_rlq" else f6.load_cfg()
    J = [r for r in f5.read_journal(_journal_path(book, asset)) if int(r["c"]) <= int(end_ms)]
    if not J:
        return None
    bars = data.load(asset)[["open", "high", "low", "close", "volume"]].astype(float)
    bars.index = bars.index.as_unit("ms")
    om = np.asarray(bars.index.as_unit("ms").asi8, dtype=np.int64)
    W = int(cfg["phase5"]["forward"]["feature_window_bars"])
    bars = bars[(om + BAR_MS <= int(end_ms)) & (om >= int(start_ms) - (W + 900) * BAR_MS)]
    fund = f5.funding_frame(data.load_funding(asset))
    fund = fund[np.asarray(fund["settle_ms"], dtype="int64") <= int(end_ms)]
    B = f5.risk_and_book(cfg, bars, fund, J, start_ms)
    return None if B is None else (cfg, B, J)


def compute(book, asset):
    """The registered read-outs of one book and coin as a dict (numbers and sentences)."""
    from engine15 import playbook8 as p8
    from engine15.playbook5 import trades
    from engine15.rl import forward5 as f5
    start, end = READS[book]
    s_ms, e_ms = ms(start), ms(end)
    got = _book(book, asset, s_ms, e_ms)
    if got is None:
        return {"book": book, "asset": asset, "missing": "no record"}
    cfg, B, J = got
    r, bh = p8.window(B, s_ms, e_ms)
    out = {"book": book, "asset": asset, "from_utc": start, "to_utc": end, "return_pct": round(r, 3),
           "bh_spot_return_pct": round(bh, 3), "lines": [line(book, asset, r, "buy-and-hold", bh, start, end)],
           "closed_trades": sum(1 for t in trades(B) if t["closed"]), "split": f5.agent_split(cfg, B, J, STAKE)}
    if book.startswith("p6_"):
        y0 = ms(YARD_START)
        Y = _book(YARD_BOOK, asset, y0, e_ms)
        if Y is None:
            out["yardstick"] = "no p8_mom record"
        else:
            r6, bhy = p8.window(B, y0, e_ms)
            r8, _ = p8.window(Y[1], y0, e_ms)
            out["same_days"] = {"from_utc": YARD_START, "to_utc": end, "book_return_pct": round(r6, 3),
                                "yardstick_return_pct": round(r8, 3), "bh_spot_return_pct": round(bhy, 3)}
            out["lines"].append(line(book, asset, r6, "the momentum yardstick p8_mom", r8, YARD_START, end))
    return out


def run(now_ms=None, out=print, compute_fn=None):
    """-> {book: [results] or None (refused)}. Prints the read-outs of every book whose date has come."""
    now = int(time.time() * 1000) if now_ms is None else int(now_ms)
    fn = compute_fn or compute
    res = {}
    for book in READS:
        if not due(book, now):
            out(refusal(book))
            res[book] = None
            continue
        rows = []
        for a in ASSETS:
            r = fn(book, a)
            rows.append(r)
            if r.get("missing"):
                out("%s %s: %s" % (book, COIN[a], r["missing"]))
                continue
            for ln in r["lines"]:
                out(ln)
            sp = r.get("split")
            if sp:
                out("  %s %s, interim: agent-decided gross %+.2f USD, fallback-decided gross %+.2f USD, costs %.2f USD "
                    "(the whole book's, not split), net %+.2f USD; seeds on a model %.1f%% of seed-bars." % (
                        book, COIN[a], sp["agent_gross_usd"], sp["fallback_gross_usd"], sp["costs_usd"], sp["net_usd"],
                        sp["agent_seed_bars_pct"]))
            out("  %s %s: %d closed trades of the %d the verdict needs; the 30-per-coin rule still decides. NOT passed."
                % (book, COIN[a], r["closed_trades"], NEED))
        res[book] = rows
    return res


if __name__ == "__main__":
    run()
