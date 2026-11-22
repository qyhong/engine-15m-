# -*- coding: utf-8 -*-
"""paper_desk -- three forward PAPER wallets on the Setups book's BTC and ETH trades. PAPER ONLY.

Owner, 22 Nov 2026 (in the site session "Study first, then paper desk"; in this project "I want stick to my plan"):
after H63 walked one member wallet through the Setups book's history at three sizes, the same three sizes run FORWARD on
paper from START_UTC, so that the question "what would a larger size have done" is answered by trades that had not
happened when the sizes were chosen:

    S1  the 2% rule       lose 2% of the wallet at the stop, notional capped at the wallet (1x), daily brake 5%
    S2  100% per coin     notional = 1.0 x the wallet per coin, daily brake 15%
    S3  the 3x book       notional = 1.5 x the wallet per coin, daily brake 15%

Each is ONE $10,000 wallet across both coins with two finish lines: +100% (20,000) and -50% (5,000). A wallet that
reaches a line, or is wiped out, stops there. The rules are H63's, word for word (research/HYPOTHESES.md, H63; the walk
below is the walk of research/h63_member_wallet.py and tests/test_paper_desk.py holds the two to the same numbers).

It places nothing and changes no book. It READS the Setups book's closed-trade files, the book's state, the stored
15-minute bars (the tail only) and the stored funding series, and is recomputed from START_UTC at every step: it keeps
no state of its own, so there is nothing to lose or to roll back. Its only output is the "paper_desk" block of
out/live/scoreboard.json (reports.scoreboard), which the page carries under scoreboard_all.

What it is not: the vault. The member's fill, the vault's join window, refusals, rounding and the exchange's limits are
not modelled; fees are the paper book's (0.10% of the notional per side); the brake is a model of the vault's.
A trade already open at START_UTC is not joined. A new entry is walked once its first bar has closed.
"""
import bisect
import calendar
import csv
import io
import json
import os
import time
from collections import OrderedDict

import numpy as np

from . import data, exits, signals
from .config import CFG
from .shadows import STATE_PATH

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE_DIR = os.path.join(ROOT, "out", "live")
BOOK = "b_targets"
COINS = ("BTCUSDT", "ETHUSDT")
ORDER = {"BTCUSDT": 0, "ETHUSDT": 1}
START_UTC = "2026-11-23T00:00:00Z"               # the desk's first bar; trades opened before it are not joined
START_MS = calendar.timegm(time.strptime(START_UTC, "%Y-%m-%dT%H:%M:%SZ")) * 1000
BAR_MS = int(CFG.get("bar_ms", 900000))
START_W = 10000.0
UP, DOWN = 2.0, 0.5                              # the finish lines, x the starting wallet
MAINT = 0.005                                    # assumed maintenance margin, share of the open notional (H63)
BARS_CAP = 1 << 27                               # how far back the tail read of a bar file may go (decades of bars)
PART = exits.PART
IN_BAR = ("STOP", "STOP_BE", "T2")               # exits filled inside a bar; anything else is filled at an open
SIZINGS = OrderedDict([
    ("S1", {"title": "2% rule", "kind": "risk", "risk": 0.02, "cap": 1.0, "brake": 0.05}),
    ("S2", {"title": "100% per coin", "kind": "notional", "mult": 1.0, "brake": 0.15}),
    ("S3", {"title": "3x book", "kind": "notional", "mult": 1.5, "brake": 0.15}),
])
NOTE = ("Three paper wallets of $10,000 on the Setups book's BTC and ETH trades since %s, each at its own size, both "
        "coins in one wallet. A wallet stops at +100%% or -50%%. Paper only: the member's fill, the vault's own rules and "
        "the exchange's limits are not modelled." % START_UTC[:10])


# ------------------------------------------------------------------ a trade as prices and bars (H63)
def setup_of(coin, side, entry, stop0, i_in, i_out, p_out, why_out, t1, px, t1_hit=None, last=None):
    """One trade of the book. i_out None = still open (t1_hit says whether Target 1 was taken; `last` = the last bar)."""
    side = int(side)
    tags = str(why_out).split("+") if i_out is not None else []
    took = ("T1" in tags) if i_out is not None else bool(t1_hit)
    i_t1, p_final = None, (None if i_out is None else float(p_out))
    if took:
        z = (last if i_out is None else i_out) + 1
        hit = (px["low"][i_in:z] <= t1) if side < 0 else (px["high"][i_in:z] >= t1)
        if not hit.any():
            raise RuntimeError("%s trade at bar %d took Target 1 but no bar reaches it" % (coin, i_in))
        i_t1 = i_in + int(np.argmax(hit))
        if i_out is not None:
            p_final = (float(p_out) - PART * float(t1)) / (1.0 - PART)
    in_bar = bool(tags) and tags[-1] in IN_BAR
    if i_t1 is not None and i_out is not None and i_t1 == i_out and not in_bar:
        raise RuntimeError("%s trade at bar %d: Target 1 in the bar it was closed at the open of" % (coin, i_in))
    return {"coin": coin, "side": side, "entry": float(entry), "stop0": float(stop0), "i_in": int(i_in),
            "i_out": None if i_out is None else int(i_out), "t1": None if t1 is None or t1 != t1 else float(t1),
            "i_t1": i_t1, "p_final": p_final, "in_bar": in_bar, "why": "+".join(tags) or "OPEN"}


def build_events(setups, funding=None):
    """-> events sorted by (bar, phase, coin). Phases: 0 funding, 1 a close at the open, 2 an entry at the open,
    3 Target 1 inside the bar, 4 a stop or Target 2 inside the bar."""
    ev = []
    for k, s in enumerate(setups):
        c = ORDER.get(s["coin"], 9)
        ev.append((s["i_in"], 2, c, "in", k))
        if s["i_t1"] is not None:
            ev.append((s["i_t1"], 3, c, "t1", k))
        if s["i_out"] is not None:
            ev.append((s["i_out"], 4 if s["in_bar"] else 1, c, "out", k))
    for coin, (bars, rates) in (funding or {}).items():
        for b, r in zip(bars, rates):
            ev.append((int(b), 0, ORDER.get(coin, 9), "fund", (coin, float(r))))
    ev.sort(key=lambda e: e[:3])
    return ev


def context(setups, px, times_ms, fee, funding=None):
    ev = build_events(setups, funding)
    day = np.asarray(times_ms, dtype="int64") // 86400000
    return {"setups": setups, "events": ev, "bars": [e[0] for e in ev], "px": px, "day_of": day, "fee": float(fee)}


def member_sizer(sz):
    def size(W, W_day, s, other):
        dist = abs(s["entry"] - s["stop0"])
        if dist <= 0 or W <= 0:
            return 0.0, "none"
        o_notional = other["qty"] * other["entry"] if other else 0.0
        o_risk = max(0.0, other["qty"] * other["side"] * (other["entry"] - other["stop"])) if other else 0.0
        note = ""
        if sz["kind"] == "risk":
            qty = sz["risk"] * W / dist
            cap = max(0.0, sz["cap"] * W - o_notional) / s["entry"]
            if qty > cap:
                qty, note = cap, "capped"
        else:
            qty = sz["mult"] * W / s["entry"]
        budget = sz["brake"] * W_day - max(0.0, W_day - W) - o_risk
        if qty * dist > budget:
            qty, note = max(0.0, budget) / dist, "trimmed"
        return qty, note
    return size


def walk(ctx, lo, hi, sizer, start_w=START_W, funding_on=True, lines=None, join_from=None, worst_px=True):
    """One wallet over bars lo .. hi-1. lines = (up, down) in dollars ends the walk at the first close beyond either.
    -> {"eq": equity at each close, "wallet", "outcome": None | "up" | "down" | "wiped", "end": the last bar walked, ...}"""
    setups, ev, bars, px, day_of, fee = ctx["setups"], ctx["events"], ctx["bars"], ctx["px"], ctx["day_of"], ctx["fee"]
    join_from = lo if join_from is None else join_from
    eq = np.full(hi - lo, np.nan)
    pos = {}
    S = {"W": float(start_w), "day": None, "W_day": float(start_w)}
    st = {"joined": 0, "trimmed": 0, "capped": 0, "not_joined": 0, "fees": 0.0, "funding": 0.0, "results": []}
    outcome, end = None, hi - 1

    def mark(a, b):
        e = np.full(b - a, S["W"])
        k_liq = None
        if pos:
            w = np.full(b - a, S["W"])
            nw = np.zeros(b - a)
            for p in pos.values():
                x = px[p["coin"]]
                e += p["qty"] * p["side"] * (x["close"][a:b] - p["entry"])
                adv = x["close"][a:b] if not worst_px else (x["low"][a:b] if p["side"] > 0 else x["high"][a:b])
                w += p["qty"] * p["side"] * (adv - p["entry"])
                nw += p["qty"] * adv
            hit = np.flatnonzero(w <= MAINT * nw)
            if len(hit):
                k_liq = a + int(hit[0])
        eq[a - lo:b - lo] = e
        k_line = None
        if lines is not None:
            hit = np.flatnonzero((e >= lines[0]) | (e <= lines[1]))
            if len(hit):
                k_line = a + int(hit[0])
        if k_liq is not None and (k_line is None or k_liq <= k_line):
            eq[k_liq - lo:] = 0.0
            S["W"] = 0.0
            pos.clear()
            return k_liq, "wiped"
        if k_line is not None:
            eq[k_line - lo + 1:] = np.nan
            return k_line, ("up" if e[k_line - a] >= lines[0] else "down")
        return None

    e_i = bisect.bisect_left(bars, lo)
    i = lo
    while True:
        nb = bars[e_i] if e_i < len(ev) and bars[e_i] < hi else hi
        if nb > i:
            got = mark(i, nb)
            if got is not None:
                end, outcome = got
                break
        if nb >= hi:
            break
        if day_of[nb] != S["day"]:
            S["day"], S["W_day"] = day_of[nb], S["W"]
        while e_i < len(ev) and bars[e_i] == nb:
            _b, _ph, _c, kind, k = ev[e_i]
            e_i += 1
            if kind == "fund":
                coin, rate = k
                p = pos.get(coin)
                if p is not None and funding_on:
                    amt = p["side"] * rate * p["qty"] * px[coin]["open"][nb]
                    S["W"] -= amt
                    st["funding"] += amt
                continue
            s = setups[k]
            coin = s["coin"]
            p = pos.get(coin)
            if kind == "in":
                if s["i_in"] < join_from:
                    continue
                if p is not None:
                    raise RuntimeError("%s: an entry at bar %d while a trade is open" % (coin, nb))
                other = next((q for c2, q in pos.items() if c2 != coin), None)
                qty, note = sizer(S["W"], S["W_day"], s, other)
                if note in ("trimmed", "capped"):
                    st[note] += 1
                if qty <= 0:
                    st["not_joined"] += 1
                    continue
                st["joined"] += 1
                pos[coin] = {"coin": coin, "k": k, "qty": qty, "side": s["side"], "entry": s["entry"], "stop": s["stop0"],
                             "pnl": 0.0}
            elif p is not None and p["k"] == k:
                price = s["t1"] if kind == "t1" else s["p_final"]
                q = p["qty"] * PART if kind == "t1" else p["qty"]
                fees = fee * q * (p["entry"] + price)
                net = q * p["side"] * (price - p["entry"]) - fees
                S["W"] += net
                st["fees"] += fees
                p["pnl"] += net
                if kind == "t1":
                    p["qty"] -= q
                    p["stop"] = p["entry"]
                else:
                    st["results"].append((nb, coin, p["pnl"]))
                    del pos[coin]
        i = nb
    st.update(eq=eq, wallet=S["W"], outcome=outcome, end=end, open=[dict(p) for p in pos.values()])
    return st


def worst_fall(eq):
    e = eq[np.isfinite(eq)]
    if not len(e):
        return 0.0
    peak = np.maximum.accumulate(e)
    return float(np.min(e / np.where(peak > 0, peak, np.nan) - 1.0) * 100.0)


# ------------------------------------------------------------------ the live inputs (read only)
def _iso(ms):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(ms) // 1000))


def read_trades(live_dir, coin):
    """The book's closed trades of one coin opened at or after START_UTC: [dict]. A missing file is no trades."""
    path = os.path.join(live_dir, "shadow_trades_%s_%s.csv" % (BOOK, coin))
    if not os.path.exists(path):
        return []
    keep = {}
    with io.open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                t_in = int(float(r["t_in_ms"]))
                if t_in < START_MS or str(r.get("why_out")) == "OPEN":
                    continue
                t1 = r.get("target_1")
                row = {"t_in_ms": t_in, "t_out_ms": int(float(r["t_out_ms"])), "side": int(float(r["side"])),
                       "p_in": float(r["p_in"]), "p_out": float(r["p_out"]), "stop0": float(r["stop0"]),
                       "why_out": str(r["why_out"]), "t1": float(t1) if t1 not in (None, "", "nan") else None}
            except (KeyError, TypeError, ValueError):
                continue                                          # a garbled line is not a trade
            keep[(t_in, row["side"])] = row                       # the engine may write a row twice after a crash
    return [keep[k] for k in sorted(keep)]                        # (shadows.step: the file before the state): once here


def read_px(data_dir):
    """Both coins' closed bars from START_UTC on, on their common times -> (times_ms, {coin: open/high/low/close}),
    or None when a bar file cannot be read or holds no bar of the desk yet."""
    rows = {}
    for a in COINS:
        got = signals.read_bars(signals.bar_path(data_dir, a), START_MS - 1, cap=BARS_CAP)
        if not got:
            return None
        rows[a] = dict((b[0], b) for b in got)
    ts = sorted(set(rows[COINS[0]]) & set(rows[COINS[1]]))
    if not ts:
        return None
    px = dict((a, dict((k, np.array([rows[a][t][j] for t in ts], dtype=float))
                       for j, k in ((1, "open"), (2, "high"), (3, "low"), (4, "close")))) for a in COINS)
    return np.array(ts, dtype="int64"), px


def funding_bars(coin, times_ms, data_dir):
    """The stored funding series (data/<coin>_funding.csv: ts_ms, rate) as (bar index, rate) on the desk's bars: the bar
    that opens at the funding time. No file, or an unreadable one, is no funding (said in the block)."""
    path = os.path.join(data_dir, "%s_funding.csv" % coin.lower())
    ts, rates = [], []
    try:
        with io.open(path, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                t = int(round(float(r["ts_ms"]) / 60000.0)) * 60000
                if t >= START_MS:
                    ts.append(t)
                    rates.append(float(r["rate"]))
    except (OSError, ValueError, KeyError, TypeError):
        return None
    at = dict((int(t), i) for i, t in enumerate(times_ms))
    keep = [(at[t], r) for t, r in zip(ts, rates) if t in at]
    return np.array([k[0] for k in keep], dtype=int), np.array([k[1] for k in keep], dtype=float)


def live_setups(times_ms, px, live_dir, state):
    """The book's trades since START_UTC as setups on the desk's bars; -> (setups, entries whose first bar is not closed yet)."""
    at = dict((int(t), i) for i, t in enumerate(times_ms))
    last = len(times_ms) - 1

    def ix(ms):
        if int(ms) not in at:
            raise RuntimeError("no stored bar at %s" % _iso(ms))
        return at[int(ms)]
    setups, waiting, left_out = [], 0, 0
    for a in COINS:
        mine = []
        for t in read_trades(live_dir, a):
            if t["t_in_ms"] > times_ms[last] or t["t_out_ms"] > times_ms[last]:
                waiting += 1                                      # booked, its bars not in the file yet: the next step
                continue
            try:
                mine.append(setup_of(a, t["side"], t["p_in"], t["stop0"], ix(t["t_in_ms"]), ix(t["t_out_ms"]), t["p_out"],
                                     t["why_out"], t["t1"], px[a]))
            except (RuntimeError, TypeError, ValueError):
                left_out += 1                                     # no bar at its entry or exit (a gap in a bar file),
                continue                                          # or a row that does not add up: said, not walked
        b = ((state.get("books") or {}).get(BOOK) or {}).get(a) or {}
        try:
            if b.get("pos") and b.get("t_in_ms") is not None and int(b["t_in_ms"]) >= START_MS:
                if int(b["t_in_ms"]) > times_ms[last]:
                    waiting += 1                                  # an early entry: its first bar has not closed yet
                else:
                    mine.append(setup_of(a, b["pos"], b["entry"], b["stop0"], ix(b["t_in_ms"]), None, None, None,
                                         b.get("t1"), px[a], t1_hit=b.get("t1_hit"), last=last))
        except (RuntimeError, TypeError, ValueError, KeyError):
            left_out += 1
        mine.sort(key=lambda s: s["i_in"])
        ok = []
        for s in mine:                                            # one trade at a time per coin: a trade that starts
            prev = ok[-1] if ok else None                         # before the one before it ended cannot be walked
            if prev is not None and (prev["i_out"] is None or s["i_in"] < prev["i_out"]):
                left_out += 1
                continue
            ok.append(s)
        setups += ok
    setups.sort(key=lambda s: (s["i_in"], ORDER[s["coin"]]))
    return setups, waiting, left_out


# ------------------------------------------------------------------ the block
def block(live_dir=None, data_dir=None, state_path=None, now=None):
    """The "paper_desk" block of scoreboard.json. Never raises for a missing input: it says what it could not read."""
    out = {"started_utc": START_UTC, "start_wallet": START_W, "line_up": UP * START_W, "line_down": DOWN * START_W,
           "note": NOTE, "wallets": []}
    got = read_px(data_dir or data.DATA_DIR)
    if got is None:
        begun = (time.time() if now is None else now) * 1000 >= START_MS + 2 * BAR_MS   # its first bar should have closed
        out["status"] = ("the bar files could not be read at this step" if begun else
                         "no bar of the desk yet (it starts %s UTC)" % START_UTC[:16].replace("T", " "))
        for key, sz in SIZINGS.items():
            out["wallets"].append({"key": key, "title": sz["title"], "equity": None if begun else START_W,
                                   "pct": None if begun else 0.0, "status": "not read" if begun else "not started"})
        return out
    times_ms, px = got
    try:
        with io.open(state_path or STATE_PATH, encoding="utf-8") as fh:
            state = json.load(fh)
    except (OSError, ValueError):
        state = {}
    setups, waiting, left_out = live_setups(times_ms, px, live_dir or LIVE_DIR, state)
    fee = float(CFG.get("asset_cost", {}).get(COINS[0], CFG["cost_side"]))
    fund = dict((a, funding_bars(a, times_ms, data_dir or data.DATA_DIR)) for a in COINS)
    if any(v is None for v in fund.values()):
        out["funding"] = "not counted (the funding file could not be read)"
        fund = dict((a, v) for a, v in fund.items() if v is not None)
    ctx = context(setups, px, times_ms, fee, fund)
    n = len(times_ms)
    out.update(as_of_utc=_iso(times_ms[-1] + BAR_MS), trades=len(setups), entries_waiting_for_their_bar=waiting,
               trades_left_out=left_out, status="running")
    if left_out:
        out["status"] = "running; %d trade(s) left out (no bar at their entry or exit, or an unreadable row)" % left_out
    words = {None: "running", "up": "reached +100%", "down": "reached -50%", "wiped": "wiped out"}
    for key, sz in SIZINGS.items():
        r = walk(ctx, 0, n, member_sizer(sz), lines=(UP * START_W, DOWN * START_W))
        e = r["eq"][np.isfinite(r["eq"])]
        eq_now = float(e[-1]) if len(e) else START_W
        w = {"key": key, "title": sz["title"], "equity": round(eq_now, 2), "pct": round((eq_now / START_W - 1.0) * 100.0, 2),
             "wallet": round(float(r["wallet"]), 2), "worst_fall_pct": round(worst_fall(r["eq"]), 2),
             "joined": r["joined"], "trimmed": r["trimmed"], "capped": r["capped"], "not_joined": r["not_joined"],
             "closed": len(r["results"]), "wins": sum(1 for x in r["results"] if x[2] > 0),
             "fees_usd": round(float(r["fees"]), 2), "funding_paid_usd": round(float(r["funding"]), 2),
             "status": words[r["outcome"]],
             "ended_utc": _iso(times_ms[r["end"]] + BAR_MS) if r["outcome"] else None,
             "open": [{"coin": p["coin"], "side": "LONG" if p["side"] > 0 else "SHORT", "entry": p["entry"],
                       "notional_x_wallet": round(p["qty"] * p["entry"] / r["wallet"], 2) if r["wallet"] > 0 else None}
                      for p in r["open"]]}
        out["wallets"].append(w)
    return out
