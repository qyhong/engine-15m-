# -*- coding: utf-8 -*-
"""playbook8 -- the momentum yardstick for the RL Phase 6 books (book p8_mom). PAPER ONLY. A YARDSTICK, NOT A HYPOTHESIS.

Owner, 22 Nov 2026: "Run all above" (task 4 of the RL audit of 21 Nov 2026: "Add a momentum-only paper book as the plain
yardstick for the Phase 6 books"). Registered in research/HYPOTHESES.md ("Forward yardstick p8_mom") before this code.

Why: since the refit of 16 Nov every BTC seed of the Phase 6 books (engine15/playbook6.py) holds its 'do no harm'
fallback, the daily 30-day momentum rule, so most of their BTC result is that rule's. This book trades ONLY that rule,
through the very same code, so that its result is read beside the Phase 6 books and never credited to an agent.

How (nothing is copied; the Phase 6 books' functions are called): every step calls engine15/rl/forward5.advance with
fallback="trend" and one stand-in model (no weights, nothing trained) whose every seed carries the 'do no harm' flag on
both coins, so every decision is forward5.model_w -> forward5.trend_w (W = -10 x |a - mom_signal|; mom_signal =
rl.benchmarks.momentum(close, 30, True): the sign of the trailing 30-day return, decided at the close of the bar ending
00:00 UTC, long or short, held until the next day's decision) -> the cost band and Phase 3's policy (minimum hold 4 bars);
the book is rebuilt by forward5.risk_and_book (each seed through the Phase 3 risk manager, the mean of the seeds, decided at
a 15m close, filled at the next open, 0.10% a side, half spread 0.5 bp, volatility slippage, perp funding both sides) with
the Phase 6 books' configuration (forward6.load_cfg). advance decides only closes the evidence store's readings cover, so
the decision times are the Phase 6 books'. BTC and ETH, $10,000 each from REGISTERED, starting flat; spot buy-and-hold
beside it. Record (its own state, append-only): research/out/rl/forward8/decisions_p8_mom_<asset>.jsonl.

Each coin's state also carries `same_days`: each Phase 6 book's return over the yardstick's own days (the Phase 6 book's
equity marked at REGISTERED to the last close both have) beside this book's, rebuilt from the Phase 6 records (read only).

Rows follow docs/PLAYBOOK_INTERFACE.md (as playbook5/6: status OPEN / CLOSED, no stop or targets, why_out "RULE" or
"OPEN", r None). A failure is logged and skipped; it never stops the engine's step (reports.playbooks wraps the module too).
"""
import os
import time

import numpy as np

from . import playbook5 as p5
from .playbook5 import _dd, _px, _rnd, _side, _totals, _utc, trades

REGISTERED = "2026-11-23 00:00"     # UTC: start (research/HYPOTHESES.md); only decisions at closes after this count
BOOK = "p8_mom"
STAKE = p5.STAKE
BAR_MS = p5.BAR_MS
ASSETS = p5.ASSETS
SHORT_NAME = p5.SHORT_NAME
FORWARD_DIR = "research/out/rl/forward8"
MODEL_ID = "momentum_only"
P6_BOOKS = ("p6_mtrend", "p6_p4trend")

NOT_A_HYPOTHESIS = ("Momentum yardstick for the RL Phase 6 books: the daily 30-day momentum rule they fall back on, alone, "
                    "forward paper. Not a hypothesis and not an agent: it is never graded; it is there so that the "
                    "momentum rule's result is not credited to an agent.")
BOOKS = {
    BOOK: {"title": "Momentum yardstick for the RL Phase 6 books (their fallback rule alone), forward paper; not a "
                    "hypothesis",
           "short": "Momentum yardstick", "hypothesis": "Yardstick (not a hypothesis): research/HYPOTHESES.md, "
                                                       "\"Forward yardstick p8_mom\"",
           "registered": REGISTERED, "assets": ASSETS, "yardstick_for": P6_BOOKS,
           "scoreboard_title": "Strategy: momentum yardstick for the RL Phase 6 books (their 30-day momentum fallback "
                               "alone; not a hypothesis; forward paper)"},
}

LAST_STATE = {}
LAST_RUN = {}


def reg_ms():
    import pandas as pd
    return int(pd.Timestamp(REGISTERED, tz="UTC").value // 10**6)


def forward_dir():
    from .rl.config import resolve
    return resolve(FORWARD_DIR)


def yard_model(cfg):
    """The stand-in model: every seed on the 'do no harm' flag on both coins, so forward5.model_w gives the trend fallback's
    values (forward5.trend_w) for every bar. No weights: nothing here is trained or fitted."""
    seeds = [int(s) for s in cfg["phase5"]["forward"]["seeds"]]
    return {"id": MODEL_ID, "kind": "the Phase 6 books' trend fallback alone (no agent)", "data_end_close_ms": 0,
            "data_end_utc": None, "actions": list(cfg["actions"]),
            "seeds": dict((str(s), {"fallback": dict((a, True) for a in ASSETS)}) for s in seeds)}


def mark_at(B, t_ms, key="equity"):
    """A book's equity (or its buy-and-hold's) marked at the last close at or before t_ms; STAKE before its first bar."""
    cm = np.asarray(B["close_ms"][B["lo"]:B["n"]], dtype=np.int64)
    k = int(np.searchsorted(cm, int(t_ms), side="right")) - 1
    return float(STAKE) if k < 0 else float(B[key][k])


def last_close(B):
    return int(B["close_ms"][B["n"] - 1]) if B["n"] > B["lo"] else None


def window(B, t0_ms, t1_ms):
    """-> (book return %, spot buy-and-hold return %) from the mark at t0 to the mark at t1."""
    e0, e1 = mark_at(B, t0_ms), mark_at(B, t1_ms)
    b0, b1 = mark_at(B, t0_ms, "bh_equity"), mark_at(B, t1_ms, "bh_equity")
    return 100.0 * (e1 / e0 - 1.0), 100.0 * (b1 / b0 - 1.0)


def same_days(B6, B8, start_ms):
    """A Phase 6 book beside the yardstick over the yardstick's own days: start_ms (its REGISTERED) to the last close
    both books have. -> dict or None (no common close yet)."""
    if B6 is None or B8 is None:
        return None
    e6, e8 = last_close(B6), last_close(B8)
    end = min(e6, e8) if e6 is not None and e8 is not None else None
    if end is None or end <= int(start_ms):
        return None
    r6, bh = window(B6, start_ms, end)
    r8, _ = window(B8, start_ms, end)
    return {"from_utc": _utc(start_ms), "to_utc": _utc(end), "book_return_pct": _rnd(r6, 3),
            "yardstick_return_pct": _rnd(r8, 3), "bh_spot_return_pct": _rnd(bh, 3),
            "difference_pts": _rnd(r6 - r8, 3)}


def sentence(asset, t, B):
    a = SHORT_NAME.get(asset, asset)
    head = "Momentum yardstick, %s: %s %.2fx from %s, entry decided at the %s UTC close" % (
        a, _side(t["side"]), abs(t["x_entry"]), _px(t["entry"]), _utc(t["entry_ms"]))
    if t["resizes"]:
        head += ", re-sized %d time%s" % (t["resizes"], "" if t["resizes"] == 1 else "s")
    if t["closed"]:
        out = "%s. Closed at %s (the daily 30-day momentum rule or the risk manager went flat or turned at the %s UTC " \
              "close): %+.2f%%, %+.2f USD after %.2f USD fees and %.2f USD spread, slippage and funding." % (
                  head, _px(t["exit"]), _utc(t["exit_ms"]), 100 * t["pnl"] / t["e0"], t["pnl"], t["fees"], t["costs"])
    else:
        cm = B["close_ms"]
        out = "%s, now %s %.2fx. Open, marked at the %s UTC close %s: %+.2f%%, %+.2f USD so far (fees %.2f USD)." % (
            head, _side(t["x_now"]), abs(t["x_now"]), _utc(cm[-1]), _px(B["bars"]["close"].values[-1]),
            100 * t["pnl"] / t["e0"], t["pnl"], t["fees"])
    return out + " Paper, forward; a yardstick, not a hypothesis."


def _row(asset, t, B):
    r = p5._row(asset, t, B)
    r["book"] = BOOK
    r["why_out"] = "RULE" if t["closed"] else "OPEN"
    r["text"] = sentence(asset, t, B)
    return r


def _state(asset, B, journal, tr):
    from . import playbook6 as p6
    cm = B["close_ms"]
    last = journal[-1]
    held_next = float(B["book"][-1])
    eq, beq = B["equity"], B["bh_equity"]
    st = {"last_close_utc": _utc(cm[-1]), "close": _rnd(B["bars"]["close"].values[-1]),
          "rule_exposure": _rnd(held_next, 4), "equity_usd": _rnd(eq[-1], 2), "return_pct": _rnd(100 * (eq[-1] / STAKE - 1), 3),
          "bh_spot_equity_usd": _rnd(beq[-1], 2), "bh_spot_return_pct": _rnd(100 * (beq[-1] / STAKE - 1), 3),
          "max_dd_pct": _rnd(100 * _dd(eq), 3), "bh_max_dd_pct": _rnd(100 * _dd(beq), 3),
          "forward_trades": len(tr), "closed": sum(1 for t in tr if t["closed"]),
          "seed_requests": [float(x) for x in last["req"]], "model": last["m"],
          "decisions": len(journal), "first_decision_utc": _utc(journal[0]["c"]), "last_decision_utc": _utc(last["c"]),
          "late_decisions": int(sum(1 for r in journal if r.get("lag_s", 0) > 1800))}
    st.update(p6._momentum(B["bars"]["close"]))
    bk = np.sign(B["book"])
    if held_next != 0:
        j = len(bk) - 1
        while j > 0 and bk[j - 1] == bk[-1]:
            j -= 1
        st["book_position"] = "%s %.2fx since %s UTC" % (_side(held_next), abs(held_next), _utc(cm[j]))
    else:
        st["book_position"] = "flat"
    st["decision"] = ("At the %s UTC close the daily 30-day momentum rule asked for %+.1f; after the risk manager the "
                      "yardstick holds %s %.2fx from the next open." % (
                          _utc(last["c"]), float(last["req"][0]), _side(held_next), abs(held_next)))
    return st


# ---------------------------------------------------------------- live interface
def step(bars=None, now_ms=None, funding=None, readings=None, journal_dir=None, p6_journal_dir=None, cfg=None, log=print):
    """bars: {asset: 15m frame} (None reads the tails of the engine's files); funding: {asset: frame rate / settle_ms};
    readings: {asset: snapshot .npz path} (None = the evidence store, read only). journal_dir: default
    research/out/rl/forward8; p6_journal_dir: the Phase 6 records (read only; default research/out/rl/forward6).
    -> rows (docs/PLAYBOOK_INTERFACE.md). Records new decisions; trains nothing; never raises."""
    from . import playbook6 as p6
    from .rl import forward5 as f5
    from .rl import forward6 as f6
    t_start = time.time()
    rows = []
    LAST_STATE.clear()
    try:
        cfg = cfg or f6.load_cfg()
        jd = journal_dir or forward_dir()
        jd6 = p6_journal_dir or f6.forward_dir(cfg)
        rms, rms6 = reg_ms(), p6.reg_ms()
        W = int(cfg["phase5"]["forward"]["feature_window_bars"])
        now = int(time.time() * 1000) if now_ms is None else int(now_ms)
        models = [(0, yard_model(cfg))]
        os.makedirs(jd, exist_ok=True)
    except Exception as e:
        log("playbook8 setup failed: %r" % (e,))
        return rows
    for asset in ASSETS:
        try:
            nrows = W + 900 + max(0, (now - min(rms, rms6)) // BAR_MS) + 10
            if bars is None:
                df = f5.tail_bars(asset, nrows)
            else:
                df = bars.get(asset)
                if df is None:
                    continue
                df = df[["open", "high", "low", "close", "volume"]].astype(float)
            df = df[np.asarray(df.index.as_unit("ms").asi8) + BAR_MS <= now].iloc[-nrows:]
            if funding is not None and funding.get(asset) is not None:
                fund = funding[asset]
            else:
                from . import data
                fund = f5.funding_frame(data.load_funding(asset))
            fund = fund[np.asarray(fund["settle_ms"], dtype="int64") <= now]
            if len(df) < W + 10:
                continue
            t0 = int(df.index[0].value // 10**6)
            times, raw, last = f5.readings_tail(asset, t0, snapshot=(readings or {}).get(asset))
            keep = times + BAR_MS <= now
            if not keep.all():
                times = times[keep]
                raw = dict((k, v[keep]) for k, v in raw.items())
                last = int(times[-1]) if len(times) else None
            jp = os.path.join(jd, "decisions_%s_%s.jsonl" % (BOOK, asset))
            lock = os.path.join(jd, "step_%s_%s.lock" % (BOOK, asset))
            try:
                fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                locked = True
            except FileExistsError:
                locked = False
                if time.time() - os.path.getmtime(lock) > 600:
                    os.remove(lock)
            if locked:
                try:
                    f5.advance(asset, cfg, rms, jp, models, df, fund, (times, raw, last), log=log, fallback="trend")
                finally:
                    os.remove(lock)
            journal = f5.read_journal(jp)
            B = f5.risk_and_book(cfg, df, fund, journal, rms)
            if B is None:
                continue
            tr = trades(B)
            for t in tr:
                rows.append(_row(asset, t, B))
            st = _state(asset, B, journal, tr)
            LAST_STATE.setdefault(BOOK, {})[asset] = st
            sd = {}
            for book6 in P6_BOOKS:                                # the Phase 6 books over the same days (page only)
                try:
                    J6 = f5.read_journal(os.path.join(jd6, "decisions_%s_%s.jsonl" % (book6, asset)))
                    v = same_days(f5.risk_and_book(cfg, df, fund, J6, rms6) if J6 else None, B, rms)
                    if v is not None:
                        sd[book6] = v
                except Exception as e:
                    log("playbook8 %s same days with %s failed: %r" % (asset, book6, e))
            st["same_days"] = sd
        except Exception as e:
            log("playbook8 %s failed: %r" % (asset, e))
            continue
    LAST_RUN.update({"seconds": round(time.time() - t_start, 2), "utc": _utc(int(time.time() * 1000))})
    return rows


def rule_text():
    return ("%s Every 15-minute close the RL Phase 6 books decide, per coin: the target is the daily 30-day momentum "
            "position (the sign of the last 30 days' return, decided at the 00:00 UTC close, long or short), through "
            "the same code as a Phase 6 seed on its 'do no harm' fallback: the round-trip cost band, at least 1 hour "
            "held, sized by the Phase 3 risk manager (60%%-a-year vol target, drawdown brake), filled at the next 15m "
            "open; 0.10%% a side, spread 0.5 bp, volatility slippage, perp funding both sides. BTC and ETH, each its "
            "own $10,000 paper book from %s UTC, starting flat; it is compared with the Phase 6 books over the same "
            "days only." % (NOT_A_HYPOTHESIS, REGISTERED))


def page_block(rows):
    out = {}
    for book, facts in BOOKS.items():
        mine = [r for r in rows if r["book"] == book]
        closed = sorted([r for r in mine if r["status"] == "CLOSED"], key=lambda r: r["exit_utc"] or "")
        live = [dict((k, r.get(k)) for k in ("asset", "status", "side", "setup_utc", "entry", "stop", "target_1",
                                              "target_2", "r", "pnl_usd", "text"))
                for r in mine if r["status"] in ("WAITING", "OPEN")]
        per = {}
        for a in facts["assets"]:
            t = _totals([r for r in closed if r["asset"] == a])
            if t["trades"]:
                per[a] = t
        out[book] = {"title": facts["title"], "hypothesis": facts["hypothesis"], "registered": facts["registered"] + " UTC",
                     "not_passed": True, "yardstick": True, "yardstick_for": list(P6_BOOKS), "rule": rule_text(),
                     "open": live,
                     "recent": [dict((k, r.get(k)) for k in ("asset", "side", "entry_utc", "entry", "exit_utc", "exit",
                                                              "why_out", "r", "pnl_usd", "pnl_pct", "text"))
                                for r in closed[-5:]],
                     "totals": _totals(closed), "by_asset": per, "books": dict(LAST_STATE.get(book, {})),
                     "pass_rule": "None: a yardstick is never graded. The Phase 6 books are read beside it over the same days.",
                     "note": NOT_A_HYPOTHESIS, "step_seconds": LAST_RUN.get("seconds")}
    return out


def main(argv=None):
    rows = step()
    for r in rows:
        print(r["text"])
    for book, b in page_block(rows).items():
        print(book, b["totals"], "step %.2fs" % (b["step_seconds"] or 0))
        for a, s in b["books"].items():
            print("  ", a, s)


if __name__ == "__main__":
    main()
