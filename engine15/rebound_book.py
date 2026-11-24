# -*- coding: utf-8 -*-
"""rebound_book -- H117: the Setups rule with a capitulation-rebound override, as the forward paper shadow book
`b_rebound` on BTC and ETH. PAPER ONLY. NOT passed.

Owner, 24 Nov 2026: "So we can earn the short and then turn long"; step 1 of the rebound plan (a paper copy of the
Setups book with the rebound override): "1. Yes."; "I want minds15 engine able to take this opportunity". Registered
as H117 in research/HYPOTHESES.md BEFORE this file existed. History does NOT support the rule (H107: rule A flat over
123 trades; H113: in the holdout year the shorts this override withholds were the book's better shorts; H116: buying
a retest lost) and the override itself was never run on history. The book exists because the owner asked for it.

    the book       shadows.run under b_targets' own rule plus the key "rebound" (rule(), read from
                   shadows.CHALLENGERS at each step, so it is always the Setups rule of the day), b_targets' cfg, the
                   same odds, readings, bars, sizing rule and fee. BTCUSDT and ETHUSDT only.
    the trigger    playbook9.features on the book's own 15m bars (the last 45 days of them): H107's rule A onset flag
                   and its ATR(1h), read at each close from bars up to that close. Rule B's flag is recorded, never used.
    the override   (in shadows.run, behind the rule key) at a trigger: a SHORT book closes the short and opens the long
                   at the next open; a FLAT book opens the long at the next open; a book that is LONG counts it. The
                   long is H107's trade (stop 3 x ATR(1h) below the fill, half off at +1R and the stop to the entry
                   from the next bar, the rest at +2R, what is left out at the close of the 192nd bar), at the Setups
                   book's own size and fee. While it lives the Setups rule is not consulted.

IT CANNOT TOUCH ANOTHER BOOK. shadows.advance calls `advance` here after every challenger and follower, inside a
try/except; this module writes only sst["books"][NAME] and sst["late_starts"][NAME]. playbook9 is imported inside
`trigger` only, so no other book's path loads it. A trigger that cannot be computed leaves the step to the plain
Setups rule (one log line); a market that fails is logged in one line and caught up at the next step from the last
bar the book processed. The VIP vault copies b_targets (setups.BOOK); nothing here is read by setups.py, signals.py or
vault_feed.py.

The read (H117): the scoreboard's row at 30 closed forward trades, and `compare`'s line against b_targets over the
same days. Beside it, with no verdict: the override's own record (`record`).
"""
import time

import numpy as np
import pandas as pd

NAME = "b_rebound"
BASE = "b_targets"                               # the book this one copies, and is compared with
HYPOTHESIS = "H117"
ASSETS = ("BTCUSDT", "ETHUSDT")                  # on the other six markets the book does not exist
LABEL = "NOT passed, paper only"
TITLE = "Setups with the capitulation-rebound override (H117), BTC and ETH. NOT passed, paper only"
# reports.scoreboard: it must start with "Shadow" (the Telegram bot tells shadow rows by that word)
SCOREBOARD_TITLE = ("Shadow: %s (H117, the Setups rule + the capitulation-rebound long; BTC and ETH). "
                    "NOT passed, paper only" % NAME)
NOTE = ("NOT passed. Started on the owner's word (24 Nov 2026), not because a study passed: on history H107's rule A, "
        "the trigger and the long used here, was flat over 123 trades, and this override was never run on history. "
        "Paper only; the vault copies b_targets, never this book.")

# ---- the verdict rule's constants (H117)
MIN_TRADES = 30                                  # nothing is read before this many closed trades
LEVEL_BAND_PTS = 1.0                             # "level with": returns less than 1.0 point apart (H108's band)
START_EQUITY = 10000.0
COUNTS = ("seen", "from_short", "from_flat", "while_long", "in_trade")
META = "h117"                                    # this module's own key in the book's state (run() never reads it)


def rule():
    """The Setups rule of the day plus the one key (read from shadows at each call, never copied here)."""
    from . import shadows
    return dict(shadows.CHALLENGERS[BASE]["rule"], rebound=True)


def funding_of(asset):
    """The engine's own funding file (live._update_bars refreshes it at every crypto step). Read only at a trigger."""
    from . import data
    return data.load_funding(asset)


# =====================================================================================
# the trigger (row k = known at the close of bar k)
# =====================================================================================
def trigger(px, times_ms, lo, hi, asset=None, funding=None):
    """H107's rule A at the closes of bars lo .. hi-1 of the book's own bars, as playbook9.features reads them on the
    last 45 days of bars (playbook9.TAIL_BARS + 8, as that book's own step) plus the bars lo .. hi-1.
    px: {"open", "high", "low", "close"} arrays; times_ms: the bars' open times. funding: a Series of rates keyed by
    the time each was set (None: read from the engine's file, and only when a trigger is there).
    -> {"A": onset flag, "atr": ATR(1h), "B": rule B's flag (1 / 0, -1 = no fresh funding reading), each as long as
        the bars and filled for lo .. hi-1 only; "stop_atr", "hold", "fee": playbook9's frozen constants}.
    Raises on anything it cannot read: the caller logs one line and runs the step without a trigger."""
    from . import playbook9 as p9                # lazy, and only on this book's path
    n = len(px["close"])
    lo, hi = int(lo), int(hi)
    A, atr, B = np.zeros(n, dtype=bool), np.full(n, np.nan), np.full(n, -1, dtype=np.int8)
    out = {"A": A, "atr": atr, "B": B, "stop_atr": float(p9.STOP_ATR), "hold": int(p9.HOLD), "fee": float(p9.FEE)}
    if hi <= lo:
        return out
    f0 = max(0, lo - (p9.TAIL_BARS + 8))
    cols = dict((k, np.asarray(px[k][f0:hi], dtype=float)) for k in ("open", "high", "low", "close"))
    ok = np.isfinite(cols["open"]) & np.isfinite(cols["high"]) & np.isfinite(cols["low"]) & np.isfinite(cols["close"])
    rows = np.arange(f0, hi)[ok]
    if not len(rows):
        return out
    t = pd.to_datetime(np.asarray(times_ms[f0:hi], dtype="int64")[ok], unit="ms", utc=True)
    df = pd.DataFrame(dict((k, v[ok]) for k, v in cols.items()), index=t)
    fx = p9.features(df, None)
    mine = rows >= lo
    A[rows[mine]] = fx["A"][mine]
    atr[rows[mine]] = fx["atr1h"][mine]
    if A.any():                                  # rule B's flag is a record only: the file is read only at a trigger
        try:
            fb = p9.features(df, funding if funding is not None else funding_of(asset))
            flag = np.where(fb["B"], 1, np.where(fb["fund_fresh"], 0, -1)).astype(np.int8)
            B[rows[mine]] = flag[mine]
        except Exception:
            pass                                 # unknown stays -1; rule A's trigger does not depend on it
    return out


# =====================================================================================
# the forward book (called by shadows.advance, guarded there)
# =====================================================================================
def _utc(ms):
    return None if ms is None else str(pd.Timestamp(int(ms), unit="ms", tz="UTC"))[:16]


def _marked(st):
    st = st or {}
    v = st.get("equity_marked", st.get("eq"))
    return None if v is None else float(v)


def _events(a, before, after, ended, say):
    """One log line per thing the override did in this step."""
    b, r = before or {}, after or {}
    took = int(r.get("from_short", 0)) + int(r.get("from_flat", 0)) - int(b.get("from_short", 0)) - int(b.get("from_flat", 0))
    if took:
        nx = r.get("next") or r.get("trade") or (r.get("closed") or [{}])[-1]
        say("%s %s: rule A trigger at the %s UTC close, taken from %s: paper long at the next open (stop %.2f below "
            "the fill)%s. NOT passed, paper only" % (
                NAME, a, _utc(nx.get("decided_ms")), nx.get("from"), float(nx.get("r_dist") or 0.0),
                "" if took == 1 else "; %d triggers were taken in this step, this is the last" % took))
    for key, why in (("while_long", "the book already holds a Setups long"), ("in_trade", "its rebound long is open")):
        d = int(r.get(key, 0)) - int(b.get(key, 0))
        if d:
            say("%s %s: %d rule A trigger(s) counted, not taken: %s" % (NAME, a, d, why))
    for rec in ended:
        say("%s %s: the rebound long of %s UTC closed (%s) at %s: %s on paper" % (
            NAME, a, _utc(rec.get("decided_ms")), rec.get("why_out"), rec.get("exit"),
            "n/a" if rec.get("r") is None else "%+.2fR" % rec["r"]))


def advance(prep, group, assets, lo, n, sst, cfg=None, mains_before=None, log=None):
    """Advance the book on BTC and ETH to session n-1 (changes only sst["books"][NAME] and sst["late_starts"][NAME]).
    A market seen for the first time starts FLAT at session lo (the group's first new session); afterwards each market
    resumes after the last session it processed, so a skipped step is caught up bar by bar.
    One market failing is logged in one line and skipped; the other goes on. -> {(NAME, asset): closed trades}"""
    from . import data, shadows                                  # shadows imports this module: late import
    from .config import CFG
    mine = [a for a in assets if a in ASSETS]
    if not mine:
        return {}
    t0 = time.perf_counter()
    say = log or (lambda *_: None)
    times_ms = data.to_ms(prep["times"])
    books = sst.get("books", {}).get(NAME) or {}
    spec = shadows.CHALLENGERS[BASE]
    the_rule = rule()
    closed, said = {}, []
    for a in mine:
        try:
            old = books.get(a)
            last = ((old or {}).get(META) or {}).get("last_ms")
            start = int(lo) if last is None else int(np.searchsorted(times_ms, int(last), side="right"))
            if start >= n:
                continue
            inp = shadows.book_inputs(prep, a)
            meta = dict((old or {}).get(META) or {"no_trigger_steps": 0})
            trig = None
            try:
                trig = trigger(inp["px"], times_ms, start, n, asset=a)
            except Exception as e:                               # the step runs as the plain Setups rule
                meta["no_trigger_steps"] = int(meta.get("no_trigger_steps", 0)) + 1
                say("%s: %s on %s: the rebound trigger could not be computed (%r): this step runs as the Setups rule" % (
                    group, NAME, a, e))
            aux = dict(shadows.aux_from_ev(prep["ev"][a], inp["px"]), rebound=trig)
            tgt = aux["targets"]
            b = shadows.run(inp["px"], inp["odds"], inp["shock"], inp["tide"], inp["unit"],
                            shadows.asset_cfg(a, dict(cfg or prep["cfg"], **spec["cfg"])), start, n, state=old,
                            bias=inp["bias"], guard=inp["guard"], rule=the_rule, aux=aux, times_ms=times_ms,
                            row_of=lambda k: tgt.iloc[k] if len(tgt.columns) else pd.Series(dtype=float))
            st = b["state"]
            rb, rb_old = st["rebound"], (old or {}).get("rebound") or {}
            base_now = _marked(((sst.get("books") or {}).get(BASE) or {}).get(a))    # b_targets, already at session n-1
            one_bar = (n - start) == 1
            if rb.get("next") is not None and rb_old.get("next") is None:
                rb["next"].update(setups_eq=base_now, setups_exact=one_bar)        # beside the read, not the rule: what
            ended = [rec for rec in rb["closed"] if "setups_eq_out" not in rec]   # the Setups book did over the same bars
            for rec in ended:
                eq0 = rec.setdefault("setups_eq", None)
                rec["setups_eq_out"] = base_now
                rec["setups_pct"] = None if not eq0 or base_now is None else round((base_now / eq0 - 1.0) * 100.0, 4)
                rec["setups_exact"] = bool(rec.get("setups_exact")) and one_bar
            meta["last_ms"] = int(times_ms[n - 1])
            st[META] = meta
            if old is None:                                      # its first live bar: the same-days references
                mb = (mains_before or {}).get(a) or {}
                sst.setdefault("late_starts", {}).setdefault(NAME, {})[a] = {
                    "ms": int(times_ms[start]), "utc": _utc(int(times_ms[start]) + CFG["bar_ms"]),
                    "main_eq": float(mb.get("equity_marked", mb.get("eq", START_EQUITY))),
                    "ref_utc": _utc(int(times_ms[n - 1]) + CFG["bar_ms"]),   # the close both books are counted from
                    "own_eq": _marked(st), "setups_eq": base_now}
            sst.setdefault("books", {}).setdefault(NAME, {})[a] = st
            if len(b["trades"]):
                closed[(NAME, a)] = b["trades"]
            _events(a, rb_old, rb, ended, say)
            said.append("%s %s%s" % (a, {1: "LONG", -1: "SHORT"}.get(st.get("pos"), "FLAT"),
                                     " (rebound long)" if rb.get("on") else ""))
        except Exception as e:
            say("%s: %s failed on %s: %r" % (group, NAME, a, e))
    if said:
        say("%s: %s (%s, paper) %.3fs: %s" % (group, NAME, HYPOTHESIS, time.perf_counter() - t0, ", ".join(said)))
    return closed


def view_extra(st):
    """What the page view of one market's book adds to shadows.asset_view."""
    from .config import CFG
    rb = (st or {}).get("rebound") or {}
    out = {"label": LABEL, "rebound_long": bool(rb.get("on")),
           "rebound_triggers": dict((k, int(rb.get(k, 0))) for k in COUNTS)}
    t = rb.get("trade") if rb.get("on") else None
    if t:
        out["rebound_from"] = t.get("from")
        out["rebound_decided_utc"] = _utc(t.get("decided_ms"))
        if t.get("decided_ms") is not None and t.get("hold"):
            out["rebound_time_exit_utc"] = _utc(int(t["decided_ms"]) + int(t["hold"]) * CFG["bar_ms"])
    if rb.get("next"):
        out["rebound_at_next_open"] = True
    return out


# =====================================================================================
# the registered comparison (H117: against b_targets, the same two coins, the same days) and the override's own record
# =====================================================================================
def record(sst):
    """The override's own record, beside the read and with no verdict: the triggers and what became of each, and the
    rebound longs kept in the state (the last 50 a coin; the trade files hold every one)."""
    mine = ((sst or {}).get("books") or {}).get(NAME) or {}
    out = dict((k, 0) for k in COUNTS)
    longs, open_now = [], []
    for a in ASSETS:
        rb = (mine.get(a) or {}).get("rebound") or {}
        for k in COUNTS:
            out[k] += int(rb.get(k, 0))
        longs += [dict(r, asset=a) for r in rb.get("closed") or []]
        if rb.get("on"):
            open_now.append(a)
    rs = [r["r"] for r in longs if r.get("r") is not None]
    beside = [(r["pct"], r["setups_pct"]) for r in longs if r.get("setups_pct") is not None and r.get("pct") is not None]
    out.update({"open_now": open_now, "rebound_longs_closed": len(longs),
                "mean_r": round(sum(rs) / len(rs), 3) if rs else None, "sum_r": round(sum(rs), 3) if rs else None,
                "net_usd": round(sum(r.get("pnl_usd") or 0.0 for r in longs), 2) if longs else None,
                "rule_b_true": sum(1 for r in longs if r.get("rule_b") is True),
                "against_setups_same_bars": None if not beside else {
                    "trades": len(beside), "rebound_long_mean_pct": round(sum(x for x, _y in beside) / len(beside), 3),
                    "setups_book_mean_pct": round(sum(y for _x, y in beside) / len(beside), 3),
                    "note": "each rebound long's return on the book against what b_targets made on its own book from "
                            "the trigger's close to the close of the bar the long ended in; descriptive, no verdict"},
                "note": "The override's own record: no verdict is read from it (H117)."})
    return out


def compare(sst, closed_trades):
    """The comparison line of H117's read, from the shadow books' state: the change in marked equity of this book
    against b_targets' on the same coins, both from the close of this book's first live step. Before MIN_TRADES
    closed forward trades it gives no number and no word: only how many trades there are."""
    books = (sst or {}).get("books") or {}
    mine, base = books.get(NAME) or {}, books.get(BASE) or {}
    late = ((sst or {}).get("late_starts") or {}).get(NAME) or {}
    out = {"hypothesis": HYPOTHESIS, "against": "%s (the Setups book): the same coins and the same days" % BASE,
           "closed_trades": int(closed_trades), "min_trades": MIN_TRADES, "level_band_pts": LEVEL_BAND_PTS}
    if closed_trades < MIN_TRADES:
        out["read"] = "no read before %d closed forward trades (%d of %d)" % (MIN_TRADES, closed_trades, MIN_TRADES)
        return out
    pairs = []
    for a in ASSETS:
        st, ls, m = mine.get(a), late.get(a), base.get(a)
        if not st or not ls or ls.get("own_eq") is None or ls.get("setups_eq") is None or not m:
            continue
        pairs.append((_marked(st) - float(ls["own_eq"]), _marked(m) - float(ls["setups_eq"])))
    if not pairs:
        out["read"] = "no read: the books' state is not available"
        return out
    k = len(pairs)
    own = 100.0 * sum(p[0] for p in pairs) / (START_EQUITY * k)
    other = 100.0 * sum(p[1] for p in pairs) / (START_EQUITY * k)
    d = own - other
    word = "ahead of" if d >= LEVEL_BAND_PTS else "behind" if d <= -LEVEL_BAND_PTS else "level with"
    starts = [late[a]["ref_utc"] for a in ASSETS if (late.get(a) or {}).get("ref_utc")]
    out.update({"markets": k, "return_pct": round(own, 2), "setups_book_return_pct": round(other, 2),
                "difference_pts": round(d, 2), "read": word, "since_utc": min(starts) if starts else None,
                "sentence": "%s %+.2f%% vs %s %+.2f%% over the same days, %d closed trades: %s the Setups book by %.2f "
                            "points. Most of these trades are ordinary Setups trades, and the book started flat. Paper "
                            "only, NOT passed." % (NAME, own, BASE, other, closed_trades, word, abs(d))})
    return out


def scoreboard_extra(closed_trades, state_path=None):
    """What reports.scoreboard adds to this book's row: the label, the comparison line and the override's record.
    None when the book has neither started nor closed a trade (no row for a book that does not exist yet)."""
    import json
    import os
    from .shadows import STATE_PATH
    sst = None
    path = state_path or STATE_PATH
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            sst = json.load(fh)
    if not closed_trades and not ((sst or {}).get("books") or {}).get(NAME):
        return None
    return {"title": SCOREBOARD_TITLE, "label": LABEL, "passed": False, "paper_only": True, "hypothesis": HYPOTHESIS,
            "note": NOTE, "vs_setups_book": compare(sst, int(closed_trades)), "override": record(sst)}
