# -*- coding: utf-8 -*-
"""The profit-floor shadow book (H61's `floor_33pct_3r`, forward, on paper; owner 21 Nov 2026: "Add shadow").

It FOLLOWS the hold copy of the main book (shadows.CHALLENGERS["main"]): every trade that copy takes, at that copy's
fill, sized by this book's equity over that copy's at the entry. It adds one exit of its own:

    once a 15-minute CLOSE has shown ARM_R entry-stop distances of open profit, a stop order rests at
    entry + LOCK x (the best open profit a close has shown), never looser than the entry stop, live from the
    NEXT bar (a bar that opens through it fills at its open), and it only ever tightens.

Otherwise it leaves where the hold copy leaves. After its own exit it is FLAT until the hold copy's next entry.
This is research/h61_profit_floor.py's overlay, one step at a time (tests/test_floor_book.py holds the two equal,
trade for trade). It reads the hold copy's result and the bars; it changes no other book.

A book added while the hold copy is in a trade starts as a COPY of that copy's book (its realized equity, its open
trade at its size). The floor is then set from the closes since that trade's entry, but it can fill only from the
first bar after the start: nothing is replayed.
"""
import json

import numpy as np

NAME = "f_floor_33_3r"
TITLE = "Floor: lock a third of the best profit once 3R up, on the hold copy's trades (H61 history: +$393k vs hold +$339k)"
ARM_R, LOCK = 3.0, 1.0 / 3.0            # research/HYPOTHESES.md H61, `floor_33pct_3r` (not tuned here)
WORD = "FLOOR"
STOP_WORDS = ("STOP", "STOP_BE", "TRAIL")                         # the hold copy's own stop, filled inside a bar
START_EQUITY = 10000.0


def _blank_stats():
    return {"n": 0, "wins": 0, "pnl": 0.0, "r_sum": 0.0, "r_n": 0, "win_usd": 0.0, "loss_usd": 0.0}


def _nan(v):
    return float("nan") if v is None else float(v)


def floor_level(side, entry, stop0, best):
    """The level a best open profit `best` (price units, at a close) asks for, or None while it is under ARM_R x R."""
    R = abs(entry - stop0) if stop0 == stop0 else float("nan")
    if best is None or best != best or not (R == R and R > 0) or best < ARM_R * R:
        return None
    lvl = entry + side * LOCK * best
    return float(max(lvl, stop0) if side == 1 else min(lvl, stop0))          # never looser than the entry stop


def _fresh(eq):
    return {"pos": 0, "qty": 0.0, "entry": 0.0, "stop": None, "stop0": None, "eq": float(eq), "fees": 0.0,
            "why_in": "", "t_in_ms": None, "best": None, "level": None, "left_ms": None, "stats": _blank_stats()}


def start_state(main_before, px, times_ms, lo, start_ms=None):
    """The book's first state. With no hold copy before it (both start together): flat, the starting equity.
    Otherwise a copy of the hold copy's book as it stood before session lo."""
    mb = main_before or {}
    if not mb:
        return _fresh(START_EQUITY)
    st = _fresh(mb.get("eq", START_EQUITY))
    st.update(fees=float(mb.get("fees", 0.0)), copied_ms=None if start_ms is None else int(start_ms))
    if mb.get("stats"):
        st["stats"] = dict(mb["stats"])
    if mb.get("pos"):
        side, entry = int(mb["pos"]), float(mb["entry"])
        s0 = mb.get("stop0") if mb.get("stop0") is not None else mb.get("stop")
        st.update(pos=side, qty=float(mb["qty"]), entry=entry, stop0=s0, why_in=mb.get("why_in", ""),
                  t_in_ms=mb.get("t_in_ms"), adopted=True)
        c = px["close"]
        i0 = 0 if mb.get("t_in_ms") is None else int(np.searchsorted(times_ms, int(mb["t_in_ms"])))
        if lo > i0:                                              # the closes since the entry that the store holds
            st["best"] = float(np.nanmax(side * (np.asarray(c[i0:lo], float) - entry)))
        st["level"] = floor_level(side, entry, _nan(s0), st["best"])
        st["stop"] = st["level"] if st["level"] is not None else s0
    return st


def follow(main_before, main, px, times_ms, lo, n, fee, state=None):
    """Sessions lo .. n-1. main_before: the hold copy's state before them (None / {}: it started with them);
    main: shadows.run's result for them under the main rule. -> (closed trades as shadows.TRADE_COLS tuples, state)."""
    o, h, l, c = px["open"], px["high"], px["low"], px["close"]
    st = json.loads(json.dumps(state)) if state else start_state(main_before, px, times_ms, lo,
                                                                 None if lo >= n else times_ms[lo])
    stats = st.setdefault("stats", _blank_stats())
    rows = []
    eq_m = float((main_before or {}).get("eq", START_EQUITY))    # the hold copy's realized equity before its next trade
    todo = [dict(t_in_ms=None if t.t_in_ms != t.t_in_ms or t.t_in_ms is None else int(t.t_in_ms), i_in=int(t.i_in),
                 i_out=int(t.i_out), side=int(t.side), p_in=float(t.p_in), p_out=float(t.p_out), qty=float(t.qty),
                 stop0=float(t.stop0), why_in=t.why_in, why_out=t.why_out, eq_after=float(t.equity), open=False)
            for t in main["trades"].itertuples()]
    ms = main["state"]
    if ms.get("pos"):
        s0 = ms.get("stop0") if ms.get("stop0") is not None else ms.get("stop")
        todo.append(dict(t_in_ms=ms.get("t_in_ms"), i_in=int(ms.get("i_in", -1)), i_out=int(n), side=int(ms["pos"]),
                         p_in=float(ms["entry"]), p_out=None, qty=float(ms["qty"]), stop0=_nan(s0),
                         why_in=ms.get("why_in", ""), why_out=None, eq_after=None, open=True))

    def book(i_x, p_x, why, i_in):
        side, q, p_in, s0 = st["pos"], st["qty"], st["entry"], _nan(st["stop0"])
        fees = fee * q * (p_in + p_x)
        pnl = q * side * (p_x - p_in) - fees
        st["eq"] += pnl
        st["fees"] += fees
        risk = q * abs(p_in - s0) if s0 == s0 else float("nan")
        r = pnl / risk if risk and risk == risk else float("nan")
        rows.append((st["t_in_ms"], int(times_ms[i_x]), i_in, i_x, side, p_in, p_x, st["why_in"], why,
                     pnl / (q * p_in) * 100.0, st["eq"], q, pnl, fees, s0, risk, r, None, None))
        stats["n"] += 1
        stats["wins"] += int(pnl > 0)
        stats["pnl"] += pnl
        stats["win_usd" if pnl > 0 else "loss_usd"] += pnl if pnl > 0 else -pnl
        if r == r:
            stats["r_sum"] += r
            stats["r_n"] += 1
        st.update(pos=0, qty=0.0, stop=None, stop0=None, best=None, level=None, t_in_ms=None)
        st.pop("adopted", None)

    for t in todo:
        fresh = t["i_in"] >= lo                                  # opened in these sessions
        mine = bool(st["pos"]) and st["t_in_ms"] == t["t_in_ms"] and not fresh
        if fresh and st["pos"]:                                  # a trade the hold copy no longer has (a lost state):
            book(t["i_in"], float(o[t["i_in"]]), "SYNC", -1)     # out at this open, before the new one
        if fresh:                                                # the hold copy's entry: take it at its fill
            st.update(pos=t["side"], qty=t["qty"] * st["eq"] / eq_m, entry=t["p_in"],
                      stop0=None if t["stop0"] != t["stop0"] else t["stop0"], why_in=t["why_in"],
                      t_in_ms=t["t_in_ms"], best=None, level=None, left_ms=None)
            st["stop"] = st["stop0"]
            mine = True
        if mine:
            side, entry, s0 = st["pos"], st["entry"], _nan(st["stop0"])
            i_in = t["i_in"] if fresh else -1
            out, early = None, False
            for i in range(max(lo, t["i_in"]), min(t["i_out"], n)):
                lvl = st["level"]
                if lvl is not None and ((side == 1 and l[i] <= lvl) or (side == -1 and h[i] >= lvl)):
                    out, early = (i, float(min(o[i], lvl) if side == 1 else max(o[i], lvl)), WORD), True
                    break
                prof = float(side * (c[i] - entry))
                if st["best"] is None or prof > st["best"]:
                    st["best"] = prof
                cand = floor_level(side, entry, s0, st["best"])
                if cand is not None:
                    st["level"] = cand if lvl is None else (max(lvl, cand) if side == 1 else min(lvl, cand))
                    st["stop"] = st["level"]
            if out is None and not t["open"]:
                lvl = st["level"]
                if t["why_out"] in STOP_WORDS and lvl is not None:          # the floor is hit before the entry stop
                    i_x = t["i_out"]
                    out = (i_x, float(min(o[i_x], lvl) if side == 1 else max(o[i_x], lvl)), WORD)
                else:
                    out = (t["i_out"], t["p_out"], t["why_out"])            # where the hold copy leaves
            if out is not None:
                book(out[0], out[1], out[2], i_in)
                st["left_ms"] = t["t_in_ms"] if early else None  # out before the hold copy: flat until its next entry
        if not t["open"]:
            eq_m = t["eq_after"]
    if n > lo:
        mark = float(c[n - 1])
        st.update(mark=mark, mark_ms=int(times_ms[n - 1]),
                  equity_marked=float(st["eq"] + (st["qty"] * st["pos"] * (mark - st["entry"]) if st["pos"] else 0.0)))
    st["wait_main"] = bool(not st["pos"] and ms.get("pos") and st.get("left_ms") is not None
                           and st["left_ms"] == ms.get("t_in_ms"))
    st["floor"] = {"armed": bool(st["pos"] and st["level"] is not None), "arm_r": ARM_R, "lock": LOCK}
    return rows, st
