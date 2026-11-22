# -*- coding: utf-8 -*-
"""H63: one member wallet on the Setups book's BTC and ETH trades under three sizings. Research only; registered in
research/HYPOTHESES.md before this file existed. It reads the evidence store, the cached fits, the stored funding series
and (for the forward record) the live book's trade files and state, all read-only. It changes no book.

    /data/venv-research/bin/python research/h63_member_wallet.py --fits-dir research/out/h60_regime_exits/fits_today

The book's entries, stops, targets and exits do not depend on its size, so each trade is taken as prices and bars
(`setup_of`) and walked through one wallet (`walk`). GATE: walked with the paper book's own sizing, one coin at a time,
the walk reproduces the replay's marked equity at every bar.
"""
import argparse
import bisect
import json
import os
import sys
import time
from collections import OrderedDict

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

from engine15 import backtest, data, exits, live, shadows  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "h63_member_wallet")
COINS = ("BTCUSDT", "ETHUSDT")
ORDER = {"BTCUSDT": 0, "ETHUSDT": 1}
START_W = 10000.0
MID = "2023-06-08"
MAINT = 0.005                                    # assumed maintenance margin, share of the open notional
DAYS = 365
UP, DOWN = 2.0, 0.5                              # the finish lines, x the starting wallet
PART = exits.PART
IN_BAR = ("STOP", "STOP_BE", "T2")               # exits filled inside a bar; anything else is filled at an open
SIZINGS = OrderedDict([
    ("S1", {"title": "S1: 2% rule", "kind": "risk", "risk": 0.02, "cap": 1.0, "brake": 0.05}),
    ("S2", {"title": "S2: 100% per coin", "kind": "notional", "mult": 1.0, "brake": 0.15}),
    ("S3", {"title": "S3: 3x book", "kind": "notional", "mult": 1.5, "brake": 0.15}),
])


# =====================================================================================
# a trade as prices and bars
# =====================================================================================
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


def setups_of_book(coin, book, px, row_of=None, last=None):
    """The trades of an h62.run_setups / shadows.run result (and its open trade, if any) as setups."""
    out = [setup_of(coin, t.side, t.p_in, t.stop0, t.i_in, t.i_out, t.p_out, t.why_out, t.target_1, px)
           for t in book["trades"].itertuples()]
    op = book.get("open")
    if op is not None:
        t1 = None
        if op.get("t1_hit"):
            t1 = live.plan_targets(int(op["side"]), float(op["entry"]), float(op["own"]), row_of(op["i_in"] - 1)).get("target_1")
        out.append(setup_of(coin, op["side"], op["entry"], op["carried"], op["i_in"], None, None, None, t1, px,
                            t1_hit=op.get("t1_hit"), last=last))
    return out


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


def context(setups, px, times, fee, funding=None):
    ev = build_events(setups, funding)
    day = np.asarray(pd.DatetimeIndex(times).floor("D").asi8) if times is not None else np.zeros(len(px[setups[0]["coin"]]["close"]))
    return {"setups": setups, "events": ev, "bars": [e[0] for e in ev], "px": px, "day_of": day, "fee": float(fee)}


# =====================================================================================
# the sizings
# =====================================================================================
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


def paper_sizer(cfg):
    """The paper book's own sizing (one coin, its own wallet): for the gate only."""
    def size(W, W_day, s, other):
        return W * backtest.leverage(cfg, s["entry"], abs(s["entry"] - s["stop0"])) / s["entry"], ""
    return size


# =====================================================================================
# the walk
# =====================================================================================
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
        """Equity at the closes of bars a .. b-1 with the positions held now. -> (bar, outcome) of the first end, or None."""
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


# =====================================================================================
# read-outs
# =====================================================================================
def worst_fall(eq):
    e = eq[np.isfinite(eq)]
    if not len(e):
        return 0.0
    peak = np.maximum.accumulate(e)
    return float(np.min(e / np.where(peak > 0, peak, np.nan) - 1.0) * 100.0)


def losing_run(results):
    best = run = 0
    for _b, _c, pnl in sorted(results, key=lambda r: r[0]):
        run = run + 1 if pnl < 0 else 0
        best = max(best, run)
    return best


def whole(ctx, lo, hi, times, sz):
    """Read-outs (a) and (c) for one sizing."""
    r = walk(ctx, lo, hi, member_sizer(sz))
    eq = r["eq"]
    last = eq[np.isfinite(eq)][-1]
    days = pd.Series(eq, index=times[lo:hi]).resample("D").last().dropna()
    chg = days.pct_change().dropna() * 100.0
    nofund = walk(ctx, lo, hi, member_sizer(sz), funding_on=False)
    closes = walk(ctx, lo, hi, member_sizer(sz), worst_px=False)
    out = {"final_equity": float(last), "final_wallet": float(r["wallet"]), "worst_fall_pct": worst_fall(eq),
           "lowest_equity": float(np.nanmin(eq)), "lowest_at": str(times[lo + int(np.nanargmin(eq))])[:16],
           "joined": r["joined"], "trimmed": r["trimmed"], "capped": r["capped"], "not_joined": r["not_joined"],
           "fees": float(r["fees"]), "funding_paid": float(r["funding"]),
           "final_equity_no_funding": float(nofund["eq"][np.isfinite(nofund["eq"])][-1]),
           "wiped_out": r["outcome"] == "wiped", "wiped_at": str(times[r["end"]])[:16] if r["outcome"] == "wiped" else None,
           "wiped_out_closes_only": closes["outcome"] == "wiped",
           "worst_day_pct": float(chg.min()) if len(chg) else None, "worst_day": str(chg.idxmin())[:10] if len(chg) else None,
           "longest_losing_run": losing_run(r["results"]),
           "open_at_end": len(r["open"])}
    return out, r


def month_starts(ctx, lo, n, times, sz):
    """Read-out (b): a fresh wallet from every month-start, walked for DAYS days or to a finish line."""
    first = times[lo]
    starts = [m for m in pd.date_range(first.normalize(), times[n - 1], freq="MS") if m >= first]
    rows = []
    sizer = member_sizer(sz)
    for m in starts:
        a = int(times.searchsorted(m))
        if a >= n:
            break
        z = int(times.searchsorted(m + pd.Timedelta(days=DAYS)))
        full = z <= n - 1
        r = walk(ctx, a, min(z, n), sizer, lines=(UP * START_W, DOWN * START_W), join_from=a)
        oc = r["outcome"] or ("neither" if full else "unfinished")
        e = r["eq"][np.isfinite(r["eq"])]
        rows.append({"start": str(m)[:10], "outcome": oc, "days": float((times[r["end"]] - m) / pd.Timedelta(days=1)),
                     "end_equity": float(e[-1]) if len(e) else START_W})
    return rows


def tally(rows):
    out = {"starts": len(rows)}
    for k in ("up", "down", "wiped", "neither", "unfinished"):
        out[k] = sum(1 for r in rows if r["outcome"] == k)
    done = [r["days"] for r in rows if r["outcome"] in ("up", "down", "wiped")]
    out["median_days_to_either"] = float(np.median(done)) if done else None
    for k in ("up", "down"):
        d = [r["days"] for r in rows if r["outcome"] == k or (k == "down" and r["outcome"] == "wiped")]
        out["median_days_" + k] = float(np.median(d)) if d else None
    rest = [r["end_equity"] for r in rows if r["outcome"] == "neither"]
    out["median_end_neither"] = float(np.median(rest)) if rest else None
    return out


# =====================================================================================
# inputs
# =====================================================================================
def funding_bars(coin, times, series=None):
    """The stored funding series as (bar index, rate, funding times with no bar): the bar whose open time is the
    funding time."""
    f = data.load_funding(coin) if series is None else series
    if not len(f):
        return np.zeros(0, dtype=int), np.zeros(0), 0
    ts = data.to_ms(f.index.round("min"))
    tms = data.to_ms(times)
    ix = np.searchsorted(tms, ts)
    ok = ix < len(tms)
    ok[ok] &= tms[ix[ok]] == ts[ok]
    inside = (ts >= tms[0]) & (ts <= tms[-1])
    return np.asarray(ix[ok], dtype=int), np.asarray(f.values, float)[ok], int((~ok & inside).sum())


def replay(fits_root, log=print):
    """The crypto group as H62 replayed it -> (times, px, {coin: (book, lo, cfg, row_of)}), gate checked against b_targets."""
    import h59_half_be as h59
    import h62_setups_wide_stop as h62
    g = "crypto"
    prep = h59.prep_cut(g, list(COINS), os.path.join(fits_root, g), h62.group_end(g, list(COINS)), log=log)
    times = prep["times"]
    tms = data.to_ms(times)
    n = len(times)
    books = {}
    for a in COINS:
        ok = np.isfinite(prep["odds"][a][:, 0])
        lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
        aux = shadows.aux_from_ev(prep["ev"][a], prep["px"][a])
        inp = shadows.book_inputs(prep, a)
        cfg = shadows.asset_cfg(a, dict(prep["cfg"]))
        tgt = aux["targets"]
        row_of = lambda k, tgt=tgt: tgt.iloc[k] if len(tgt.columns) else pd.Series(dtype=float)   # noqa: E731
        ref = h59.run_book("b_targets", prep, a, lo, n, aux)
        cur = h62.run_setups(inp["px"], inp["odds"], inp["shock"], inp["tide"], inp["unit"], cfg, lo, n, bias=inp["bias"],
                             guard=inp["guard"], times_ms=tms, row_of=row_of)
        okk, why = h62.same_book(ref, cur, lo, n)
        if not okk:
            raise RuntimeError("GATE FAILED on %s: the reduced copy is not b_targets: %s" % (a, why))
        books[a] = (cur, lo, cfg, row_of)
    return times, prep["px"], books


def gate(coin, book, lo, n, cfg, px, row_of):
    """The walk with the paper book's own sizing must reproduce the replay's marked equity at every bar."""
    setups = setups_of_book(coin, book, px[coin], row_of, last=n - 1)
    ctx = context(setups, px, None, cfg["cost_side"])
    r = walk(ctx, lo, n, paper_sizer(cfg), start_w=shadows.START_EQUITY, funding_on=False, worst_px=False)
    ref = book["equity"][lo:n]
    if r["outcome"] is not None:
        return False, "the paper walk ended early (%s)" % r["outcome"], setups
    d = np.nanmax(np.abs(r["eq"] - ref) / np.maximum(1.0, np.abs(ref)))
    return bool(d < 1e-7), "largest relative gap %.3g over %d bars, %d trades" % (d, n - lo, len(setups)), setups


def live_record(live_dir, state_path, log=print):
    """The LIVE Setups book's BTC and ETH trades (closed, from the trade files; open, from the book's state) on the stored
    bars -> (times, px, setups, first bar)."""
    bars = dict((a, data.load(a)) for a in COINS)
    rows, first_ms = {}, None
    for a in COINS:
        p = os.path.join(live_dir, "shadow_trades_b_targets_%s.csv" % a)
        rows[a] = pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()
        if len(rows[a]):
            first_ms = int(rows[a].t_in_ms.min()) if first_ms is None else min(first_ms, int(rows[a].t_in_ms.min()))
    if first_ms is None:
        raise RuntimeError("no live trades")
    t0 = pd.Timestamp(first_ms, unit="ms", tz="UTC") - pd.Timedelta(days=1)
    times = bars[COINS[0]].index.intersection(bars[COINS[1]].index)
    times = times[times >= t0]
    px = dict((a, dict((k, bars[a].loc[times, k].values.astype(float)) for k in ("open", "high", "low", "close")))
              for a in COINS)
    tms = data.to_ms(times)

    def ix(ms):
        i = int(np.searchsorted(tms, int(ms)))
        if i >= len(tms) or tms[i] != int(ms):
            raise RuntimeError("no stored bar at %s" % pd.Timestamp(int(ms), unit="ms", tz="UTC"))
        return i
    setups = []
    for a in COINS:
        for t in rows[a].itertuples():
            setups.append(setup_of(a, t.side, t.p_in, t.stop0, ix(t.t_in_ms), ix(t.t_out_ms), t.p_out, t.why_out,
                                   t.target_1, px[a]))
    st = json.load(open(state_path))
    for a in COINS:
        b = (st.get("books", {}).get("b_targets", {}) or {}).get(a) or {}
        if b.get("pos"):
            setups.append(setup_of(a, b["pos"], b["entry"], b["stop0"], ix(b["t_in_ms"]), None, None, None, b.get("t1"),
                                   px[a], t1_hit=b.get("t1_hit"), last=len(times) - 1))
    setups.sort(key=lambda s: (s["i_in"], ORDER[s["coin"]]))
    return times, px, setups, ix(first_ms)


# =====================================================================================
# run and report
# =====================================================================================
def run(fits_root, live_dir, state_path, log=print):
    t0 = time.time()
    times, px, books = replay(fits_root, log=log)
    n = len(times)
    res = {"end": str(times[n - 1])[:16], "gate": {}, "sizings": {}, "maint": MAINT, "days": DAYS}
    setups, lo, fee = [], n, None
    for a in COINS:
        cur, lo_a, cfg, row_of = books[a]
        ok, why, s_a = gate(a, cur, lo_a, n, cfg, px, row_of)
        res["gate"][a] = {"ok": ok, "detail": why}
        log("%s gate: %s (%s)" % (a, "passed" if ok else "FAILED", why))
        if not ok:
            raise RuntimeError("GATE FAILED on %s: %s" % (a, why))
        setups += s_a
        lo = min(lo, lo_a)
        fee = cfg["cost_side"] if fee is None else fee
        assert fee == cfg["cost_side"]
    setups.sort(key=lambda s: (s["i_in"], ORDER[s["coin"]]))
    fund, missing = {}, 0
    for a in COINS:
        ib, rt, miss = funding_bars(a, times)
        fund[a] = (ib, rt)
        missing += miss
    ctx = context(setups, px, times, fee, fund)
    mid = pd.Timestamp(MID, tz="UTC")
    res.update(first=str(times[lo])[:16], trades=len(setups), fee_side=fee, funding_times_without_a_bar=missing,
               funding_rows=dict((a, int(len(fund[a][0]))) for a in COINS))
    for key, sz in SIZINGS.items():
        a_out, _r = whole(ctx, lo, n, times, sz)
        rows = month_starts(ctx, lo, n, times, sz)
        res["sizings"][key] = {"title": sz["title"], "whole": a_out, "months": tally(rows),
                               "months_first_half": tally([r for r in rows if pd.Timestamp(r["start"], tz="UTC") < mid]),
                               "months_second_half": tally([r for r in rows if pd.Timestamp(r["start"], tz="UTC") >= mid]),
                               "month_rows": rows}
        log("%s: final %.0f, worst fall %.1f%%, wiped %s; months %s (%.0fs)" % (
            key, a_out["final_equity"], a_out["worst_fall_pct"], a_out["wiped_at"], res["sizings"][key]["months"],
            time.time() - t0))
    # ---- (d) the forward record: the live book's own trades
    try:
        ft, fpx, fset, f_lo = live_record(live_dir, state_path, log=log)
        ffund = dict((a, funding_bars(a, ft)[:2]) for a in COINS)
        fctx = context(fset, fpx, ft, fee, ffund)
        fwd = {"from": str(ft[f_lo])[:16], "to": str(ft[-1])[:16], "trades": len(fset),
               "open": sum(1 for s in fset if s["i_out"] is None), "sizings": {}}
        for key, sz in SIZINGS.items():
            r = walk(fctx, f_lo, len(ft), member_sizer(sz))
            e = r["eq"][np.isfinite(r["eq"])]
            fwd["sizings"][key] = {"equity_now": float(e[-1]), "wallet": float(r["wallet"]), "worst_fall_pct": worst_fall(r["eq"]),
                                   "joined": r["joined"], "trimmed": r["trimmed"], "capped": r["capped"],
                                   "not_joined": r["not_joined"], "funding_paid": float(r["funding"]),
                                   "wiped_out": r["outcome"] == "wiped", "longest_losing_run": losing_run(r["results"])}
        res["forward"] = fwd
        log("forward: %s" % json.dumps(fwd, default=float)[:600])
    except Exception as e:                                         # the replay's read-outs stand without it; say so
        res["forward"] = {"error": "%s: %s" % (type(e).__name__, e)}
        log("forward record NOT read: %s" % res["forward"]["error"])
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "results.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    write_report(res)
    return res


def _usd(x):
    return "n/a" if x is None else "{:,.0f}".format(x)


def write_report(res):
    L = ["# H63: one member wallet on the Setups book's BTC and ETH trades, three sizings", "",
         "History replay %s to %s UTC, %d trades, paper. Registered before any number (research/HYPOTHESES.md)." % (
             res["first"], res["end"], res["trades"]),
         "Fees %.2f%% of the notional per side; funding from the stored Binance series (%s rows used, %d funding times had no bar)." % (
             res["fee_side"] * 100, ", ".join("%s %d" % (a, k) for a, k in res["funding_rows"].items()),
             res["funding_times_without_a_bar"]),
         "", "Gate: " + "; ".join("%s %s (%s)" % (a, "passed" if g["ok"] else "FAILED", g["detail"]) for a, g in res["gate"].items()),
         "", "## (a) and (c): one 10,000 wallet over the whole replay", "",
         "| Sizing | Final | Worst fall | Lowest equity | Wiped out | Joined / trimmed / capped / not joined | Fees | Funding paid | Final without funding | Worst day | Longest losing run |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for key, s in res["sizings"].items():
        w = s["whole"]
        L.append("| %s | %s | %.1f%% | %s (%s) | %s | %d / %d / %d / %d | %s | %s | %s | %s | %d |" % (
            s["title"], _usd(w["final_equity"]), w["worst_fall_pct"], _usd(w["lowest_equity"]), w["lowest_at"],
            ("YES, %s" % w["wiped_at"]) if w["wiped_out"] else ("no" + (" (closes only: YES)" if w["wiped_out_closes_only"] else "")),
            w["joined"], w["trimmed"], w["capped"], w["not_joined"], _usd(w["fees"]), _usd(w["funding_paid"]),
            _usd(w["final_equity_no_funding"]),
            "n/a" if w["worst_day_pct"] is None else "%.1f%% (%s)" % (w["worst_day_pct"], w["worst_day"]),
            w["longest_losing_run"]))
    L += ["", "## (b): a fresh 10,000 wallet from every month-start, %d days each" % res["days"], "",
          "| Sizing | Month-starts | +100% first | -50% first | Wiped out | Neither in %d days | Unfinished | Median days to either | Median days to +100% | Median days to -50% | Median end when neither |" % res["days"],
          "|---|---|---|---|---|---|---|---|---|---|---|"]

    def mrow(title, m):
        f = lambda x: "n/a" if x is None else "%.0f" % x                                           # noqa: E731
        return "| %s | %d | %d | %d | %d | %d | %d | %s | %s | %s | %s |" % (
            title, m["starts"], m["up"], m["down"], m["wiped"], m["neither"], m["unfinished"], f(m["median_days_to_either"]),
            f(m["median_days_up"]), f(m["median_days_down"]), _usd(m["median_end_neither"]))
    for key, s in res["sizings"].items():
        L.append(mrow(s["title"], s["months"]))
    L += ["", "The same, month-starts before 2023-06-08 and from it:", "",
          "| Sizing | Month-starts | +100% first | -50% first | Wiped out | Neither | Unfinished | Median days to either | to +100% | to -50% | Median end when neither |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for key, s in res["sizings"].items():
        L.append(mrow(s["title"] + ", first half", s["months_first_half"]))
        L.append(mrow(s["title"] + ", second half", s["months_second_half"]))
    L += ["", "## (d): the forward record alone (the live book's own trades)", ""]
    f = res.get("forward") or {}
    if f.get("error"):
        L.append("NOT READ: %s" % f["error"])
    else:
        L += ["%s to %s UTC: %d trades, %d still open. TOO SHORT TO JUDGE." % (f["from"], f["to"], f["trades"], f["open"]), "",
              "| Sizing | Equity now | Worst fall | Joined / trimmed / capped / not joined | Funding paid | Wiped out |",
              "|---|---|---|---|---|---|"]
        for key, s in res["sizings"].items():
            w = f["sizings"][key]
            L.append("| %s | %s | %.1f%% | %d / %d / %d / %d | %s | %s |" % (
                s["title"], _usd(w["equity_now"]), w["worst_fall_pct"], w["joined"], w["trimmed"], w["capped"],
                w["not_joined"], _usd(w["funding_paid"]), "YES" if w["wiped_out"] else "no"))
    L += ["", "Not modelled: the member's fill against the book's (slippage, the vault's join window), refusals, exchange",
          "limits, rounding. The brake is a model of the vault's, not its code. Wipe-out: equity at each position's worst",
          "price of a bar at or below %.1f%% of the open notional. A history replay is a warm-up, not a forward result." % (MAINT * 100)]
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits-dir", default=os.path.join(ROOT, "research", "out", "h60_regime_exits", "fits_today"))
    ap.add_argument("--live-dir", default=os.path.join(ROOT, "out", "live"))
    ap.add_argument("--state", default=os.path.join(ROOT, "data", "shadow_state.json"))
    a = ap.parse_args(argv)
    run(a.fits_dir, a.live_dir, a.state)


if __name__ == "__main__":
    main()
