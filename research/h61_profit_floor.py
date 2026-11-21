# -*- coding: utf-8 -*-
"""H61: a wide profit floor for the main book's big winners (research/HYPOTHESES.md, H61). PAPER ONLY. IN-SAMPLE.

    python research/h61_profit_floor.py --group fx       one group (one at a time: memory), H60's frame
    python research/h61_profit_floor.py --today          the live book's open trades under each rule (read-only)
    python research/h61_profit_floor.py --report         merge, write research/out/h61_profit_floor/report.md + results.json

THE FRAME is H60's (= H59's "today" run): research/h59_half_be.prep_cut, cut at H60's last session per group, and
`main` = shadows.run under the main rule, run exactly as H59 / H60 ran it.

THE RULES ARE AN OVERLAY on the main book's own trades (`overlay` below): no engine file is edited and no policy is
re-run. Each rule takes every main trade at the main book's fill; it leaves at its own level or, if that never
fills, exactly where the main book left; after an exit at its own level it is FLAT until the main book's next entry.
Size = the main book's size x (this book's equity / the main book's equity) at the entry (exact: the main book's
size is equity x a leverage that does not depend on equity).

A LEVEL is set at a 15-minute CLOSE from closed bars only (the 4-hour ATR and swing through data.htf_on_15) and is a
stop order from the NEXT bar, filled like the book's own stop: at the level, or at the open if the bar opens through
it. It only ever tightens and is never looser than the entry stop.

Gate, on every market, before any rule is read: the overlay with a rule that never arms == `main` (each trade's P&L
and the marked equity at every bar within 1e-6).
"""
import argparse
import gc
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

from engine15 import data, shadows  # noqa: E402
from engine15 import indicators as ind  # noqa: E402
from engine15.config import CFG  # noqa: E402
from engine15.shadows import START_EQUITY, TRADE_COLS  # noqa: E402
from engine15.sources import structure  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "h61_profit_floor")
H60_OUT = os.path.join(ROOT, "research", "out", "h60_regime_exits")
START = START_EQUITY
MID = "2023-06-08"
# H60's cut (research/h60_regime_exits.H59_END), repeated here so this file does not import that study's runner
END = {"crypto": "2026-11-20 03:45", "metals": "2026-11-20 03:30", "fx": "2026-11-20 03:45",
       "index": "2026-11-19 20:45", "energy": "2026-11-20 03:30"}
ORDER = ["SPX", "USDJPY", "BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "WTI", "BRENT"]

RULES = OrderedDict([
    ("floor_50pct_5r", {"kind": "floor", "arm_r": 5.0, "lock": 0.5, "word": "FLOOR"}),          # PRIMARY
    ("floor_50pct_3r", {"kind": "floor", "arm_r": 3.0, "lock": 0.5, "word": "FLOOR"}),
    ("floor_33pct_5r", {"kind": "floor", "arm_r": 5.0, "lock": 1.0 / 3.0, "word": "FLOOR"}),
    ("floor_33pct_3r", {"kind": "floor", "arm_r": 3.0, "lock": 1.0 / 3.0, "word": "FLOOR"}),
    ("chandelier_4h_3atr_3r", {"kind": "chandelier", "arm_r": 3.0, "atr_mult": 3.0, "word": "CHAND"}),
    ("swing_4h_5r", {"kind": "swing", "arm_r": 5.0, "word": "SWING"}),
])
PRIMARY = "floor_50pct_5r"
NEVER = {"kind": "floor", "arm_r": float("inf"), "lock": 0.5, "word": "FLOOR"}   # the gate's rule: never arms
BOOKS = ["main"] + list(RULES)
STOP_WORDS = ("STOP", "STOP_BE", "TRAIL")                         # the book's own stop, filled inside a bar
ATR_N = 14


# =====================================================================================
# the 4-hour readings, on the 15-minute rows, closed bars only
# =====================================================================================
def four_hour(times, px):
    """-> {"atr": ATR(14, Wilder) of the last CLOSED 4h bar, "sw_hi" / "sw_lo": the last CONFIRMED 4h swing high /
    low}, each as known at the close of every 15-minute row (data.htf_on_15)."""
    df = pd.DataFrame(dict((k, np.asarray(px[k], float)) for k in ("open", "high", "low", "close")),
                      index=pd.DatetimeIndex(times))
    h4 = df.resample("4h", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna(subset=["close"])
    atr = data.htf_on_15(df, "4h", ind.atr_wilder(h4, ATR_N))
    _st, hi, lo = structure.swings(h4["high"].values, h4["low"].values, structure.SWING_K["4h"])
    sw = data.htf_on_15(df, "4h", pd.DataFrame({"hi": hi, "lo": lo}, index=h4.index))
    return {"atr": atr.values.astype(float), "sw_hi": sw["hi"].values.astype(float),
            "sw_lo": sw["lo"].values.astype(float)}


# =====================================================================================
# one trade under one rule
# =====================================================================================
def candidate(rule, side, entry, best, best_close, close, i, x4):
    """The level the rule asks for at the close of bar i (None = no level from this bar)."""
    kind = rule["kind"]
    if kind == "floor":
        return entry + side * rule["lock"] * best
    if kind == "chandelier":
        a = x4["atr"][i]
        return None if not (a == a and a > 0) else best_close - side * rule["atr_mult"] * a
    if kind == "swing":
        s = x4["sw_lo"][i] if side == 1 else x4["sw_hi"][i]
        return s if (s == s and side * (close - s) > 0) else None
    raise ValueError(kind)


def walk(side, entry, stop0, i_in, i_last, px, rule, x4):
    """One trade, bars i_in .. i_last inclusive, under `rule` only (the book's own exits are the caller's).
    -> {"exit_i", "exit_px"} (None, None if the level never fills), "armed_i", "level" (in force after i_last),
    "best" (best close's open profit, price units), "best_close"."""
    o, h, l, c = px["open"], px["high"], px["low"], px["close"]
    R = abs(entry - stop0) if stop0 == stop0 else float("nan")
    level, armed_i, best, best_close = None, None, None, None
    for i in range(int(i_in), int(i_last) + 1):
        if level is not None:                                    # set at an earlier close: a stop order in this bar
            if (side == 1 and l[i] <= level) or (side == -1 and h[i] >= level):
                return {"exit_i": i, "exit_px": float(min(o[i], level) if side == 1 else max(o[i], level)),
                        "armed_i": armed_i, "level": float(level), "best": best, "best_close": best_close}
        prof = side * (c[i] - entry)
        if best is None or prof > best:
            best, best_close = float(prof), float(c[i])
        if armed_i is None and R == R and R > 0 and best >= rule["arm_r"] * R:
            armed_i = i
        if armed_i is not None:
            cand = candidate(rule, side, entry, best, best_close, c[i], i, x4)
            if cand is not None and cand == cand:
                cand = max(cand, stop0) if side == 1 else min(cand, stop0)        # never looser than the entry stop
                level = cand if level is None else (max(level, cand) if side == 1 else min(level, cand))
    return {"exit_i": None, "exit_px": None, "armed_i": armed_i, "level": None if level is None else float(level),
            "best": best, "best_close": best_close}


def stop_fill(side, level, o_i):
    return float(min(o_i, level) if side == 1 else max(o_i, level))


# =====================================================================================
# the overlay: every main trade, under one rule
# =====================================================================================
def overlay(main, px, rule, x4, fee, lo, n, times_ms=None):
    """`main` = shadows.run(...) under the main rule over sessions lo .. n-1. -> the same shape of result for the
    book that takes main's entries and adds `rule`: {"trades", "equity", "state", "armed"}."""
    c, o = px["close"], px["open"]
    tms = (lambda i: None) if times_ms is None else (lambda i: int(times_ms[i]))
    eq = float(START)
    eq_m = float(START)                                          # the main book's realized equity before the trade
    eq_arr = np.full(n, np.nan)
    rows, armed = [], []
    cursor = int(lo)
    todo = [dict(i_in=int(t.i_in), i_out=int(t.i_out), side=int(t.side), p_in=float(t.p_in), p_out=float(t.p_out),
                 qty=float(t.qty), stop0=float(t.stop0), why_in=t.why_in, why_out=t.why_out,
                 eq_after=float(t.equity), open=False) for t in main["trades"].itertuples()]
    st = main["state"]
    if st.get("pos"):
        s0 = st.get("stop0") if st.get("stop0") is not None else st.get("stop")
        todo.append(dict(i_in=int(st["i_in"]), i_out=int(n), side=int(st["pos"]), p_in=float(st["entry"]), p_out=None,
                         qty=float(st["qty"]), stop0=float("nan") if s0 is None else float(s0),
                         why_in=st.get("why_in", ""), why_out=None, eq_after=None, open=True))
    open_state = None
    for t in todo:
        i_in, i_out, side, p_in, s0 = t["i_in"], t["i_out"], t["side"], t["p_in"], t["stop0"]
        eq_arr[cursor:i_in] = eq                                 # flat since the last exit
        q = t["qty"] * eq / eq_m
        w = walk(side, p_in, s0, i_in, i_out - 1, px, rule, x4)
        by_rule = True
        if w["exit_i"] is not None:
            i_x, p_x, why = w["exit_i"], w["exit_px"], rule["word"]
        elif (not t["open"]) and t["why_out"] in STOP_WORDS and w["level"] is not None:
            i_x, p_x, why = i_out, stop_fill(side, w["level"], o[i_out]), rule["word"]   # hit before the entry stop
        elif t["open"]:
            i_x, p_x, why, by_rule = None, None, None, False
        else:
            i_x, p_x, why, by_rule = i_out, t["p_out"], t["why_out"], False
        R = abs(p_in - s0) if s0 == s0 else float("nan")
        if i_x is None:                                          # still open at the end of the window
            eq_arr[i_in:n] = eq + q * side * (c[i_in:n] - p_in)
            cursor = n
            open_state = {"pos": side, "qty": q, "entry": p_in, "stop0": None if s0 != s0 else s0, "i_in": i_in,
                          "level": w["level"], "armed": w["armed_i"] is not None}
        else:
            gross = q * side * (p_x - p_in)
            fees = fee * q * (p_in + p_x)
            pnl = gross - fees
            eq_arr[i_in:i_x] = eq + q * side * (c[i_in:i_x] - p_in)
            eq += pnl
            risk = q * R if R == R else float("nan")
            rows.append((tms(i_in), tms(i_x), i_in, i_x, side, p_in, p_x, t["why_in"], why, pnl / (q * p_in) * 100.0,
                         eq, q, pnl, fees, s0, risk, pnl / risk if risk and risk == risk else float("nan"), None, None))
            cursor = i_x
        if w["armed_i"] is not None and R == R and R > 0:
            end_px = t["p_out"] if not t["open"] else float(c[n - 1])
            armed.append({"i_in": i_in, "i_main_out": None if t["open"] else i_out, "side": side,
                          "main_open": bool(t["open"]), "armed_i": int(w["armed_i"]),
                          "peak_r": round(w["best"] / R, 4), "r_main": round(side * (end_px - p_in) / R, 4),
                          "r_rule": round(side * ((p_x if i_x is not None else end_px) - p_in) / R, 4),
                          "closed_by_rule": bool(by_rule and i_x is not None),
                          "i_rule_out": None if i_x is None else int(i_x)})
        if not t["open"]:
            eq_m = t["eq_after"]
    eq_arr[cursor:n] = eq if open_state is None else eq_arr[cursor:n]
    state = {"pos": 0 if open_state is None else open_state["pos"], "eq": float(eq), "open": open_state,
             "equity_marked": float(eq_arr[n - 1]) if n > lo else float(eq)}
    return {"trades": pd.DataFrame(rows, columns=TRADE_COLS), "equity": eq_arr, "state": state, "armed": armed}


def same_as_main(main, mine, lo, n, tol=1e-6):
    """The gate: the overlay under a rule that never arms against shadows.run's main book."""
    a, b = main["trades"], mine["trades"]
    if len(a) != len(b):
        return False, "trades %d vs %d" % (len(a), len(b))
    for col in ("i_in", "i_out", "side"):
        if not np.array_equal(a[col].values.astype(int), b[col].values.astype(int)):
            return False, "trade column %s differs" % col
    if not np.array_equal(a["why_out"].values, b["why_out"].values):
        return False, "exit words differ"
    for col in ("p_in", "p_out", "qty", "pnl_usd", "fees_usd", "equity"):
        d = np.abs(a[col].values.astype(float) - b[col].values.astype(float))
        if len(d) and float(np.nanmax(d)) > tol:
            return False, "trade column %s differs by %.9f" % (col, float(np.nanmax(d)))
    ea, eb = main["equity"][lo:n], mine["equity"][lo:n]
    if not np.array_equal(np.isfinite(ea), np.isfinite(eb)):
        return False, "equity is marked on different bars"
    d = np.abs(ea - eb)[np.isfinite(ea)]
    if len(d) and float(d.max()) > tol:
        return False, "marked equity differs by %.9f" % float(d.max())
    return True, "same"


# =====================================================================================
# one group
# =====================================================================================
def run_group(g, assets, fits_root, log=print):
    import exit_study as ex
    import h59_half_be as h59
    t0 = time.time()
    prep = h59.prep_cut(g, assets, os.path.join(fits_root, g), END[g], log=log)
    times = prep["times"]
    tms = data.to_ms(times)
    n = len(times)
    mid_ts = pd.Timestamp(MID, tz="UTC")
    out = {"group": g, "end": END[g], "assets": {}, "curves": {}, "gate": {}, "armed": {}}
    for a in assets:
        ok = np.isfinite(prep["odds"][a][:, 0])
        lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
        mid_i = min(max(int(times.searchsorted(mid_ts)), lo + 1), n - 1)
        aux = shadows.aux_from_ev(prep["ev"][a], prep["px"][a])
        px = prep["px"][a]
        fee = shadows.asset_cfg(a, prep["cfg"])["cost_side"]
        main = h59.run_book("main", prep, a, lo, n, aux)         # exactly as H59 / H60 ran it
        x4 = four_hour(times, px)
        okk, why = same_as_main(main, overlay(main, px, NEVER, x4, fee, lo, n, tms), lo, n)
        out["gate"][a] = {"ok": okk, "detail": why, "trades": int(len(main["trades"]))}
        if not okk:
            raise RuntimeError("GATE FAILED on %s: the overlay that never arms is not main: %s" % (a, why))
        books = {"main": main}
        for name, rule in RULES.items():
            books[name] = overlay(main, px, rule, x4, fee, lo, n, tms)
        c, o = px["close"], px["open"]
        res = {"window": [str(times[lo])[:16], str(times[n - 1])[:16]], "split": str(times[mid_i])[:16],
               "lo": lo, "mid_i": mid_i, "n": n, "fee_side": fee,
               "buy_hold_return_pct": round(float(c[n - 1] / o[lo] * (1 - 2 * fee) - 1) * 100, 2), "books": {}}
        curves, arm = {}, {}
        for name in BOOKS:
            b = books[name]
            eq, tr = b["equity"], b["trades"]
            base_mid = eq[mid_i - 1] if np.isfinite(eq[mid_i - 1]) else START
            res["books"][name] = {"all": ex.seg_stats(eq, tr, times, lo, n, START),
                                  "first_half": ex.seg_stats(eq, tr[tr.i_out < mid_i], times, lo, mid_i, START),
                                  "second_half": ex.seg_stats(eq, tr[tr.i_out >= mid_i], times, mid_i, n, base_mid),
                                  "exits": dict((str(k), int(v)) for k, v in tr.why_out.value_counts().items()),
                                  "open_at_end": {1: "LONG", -1: "SHORT"}.get(b["state"]["pos"], "FLAT")}
            cv = ex.daily(eq, times, lo, n)
            curves[name] = {"t": [str(x)[:10] for x in cv.index], "eq": [round(float(x), 2) for x in cv.values]}
            if name != "main":
                rows = []
                for r in b["armed"]:
                    r = dict(r, t_in=str(times[r["i_in"]])[:16],
                             half=None if r["main_open"] else (1 if r["i_main_out"] < mid_i else 2),
                             t_armed=str(times[r["armed_i"]])[:16],
                             t_rule_out=None if r["i_rule_out"] is None else str(times[min(r["i_rule_out"], n - 1)])[:16])
                    rows.append(r)
                arm[name] = rows
                res["books"][name]["armed"] = len(rows)
                res["books"][name]["closed_by_rule"] = int(sum(1 for r in rows if r["closed_by_rule"]))
        out["assets"][a] = res
        out["curves"][a] = curves
        out["armed"][a] = arm
        log("%s %s: gate passed (%d main trades); %s .. %s; main %+.0f; %s (%.0fs)" % (
            g, a, len(main["trades"]), res["window"][0], res["window"][1], res["books"]["main"]["all"].get("pnl_usd", 0),
            ", ".join("%s %+.0f [%d armed]" % (k, res["books"][k]["all"].get("pnl_usd", 0), res["books"][k]["armed"])
                      for k in RULES), time.time() - t0))
        del books, main
        gc.collect()
    del prep
    gc.collect()
    return out


# =====================================================================================
# today's open trades on the live book (description only)
# =====================================================================================
def today(page_path, log=print):
    with open(page_path, encoding="utf-8") as fh:
        page = json.load(fh)
    out = {"page_generated_utc": page.get("generated_utc"), "version": page.get("version"), "assets": {}}
    own_rule = set(CFG.get("be_t1", ())) | set(CFG.get("half_t1", ()))
    for a in ORDER:
        tr = ((page.get("assets") or {}).get(a) or {}).get("trade") or {}
        if tr.get("status") not in ("LONG", "SHORT"):
            out["assets"][a] = {"status": tr.get("status") or "FLAT"}
            continue
        side = 1 if tr["status"] == "LONG" else -1
        entry, stop, qty = float(tr["entry_price"]), float(tr["stop_price"]), float(tr["quantity"])
        row = {"status": tr["status"], "opened_utc": tr.get("opened_utc"), "entry": entry, "stop": stop, "qty": qty}
        if a in own_rule or side * (entry - stop) <= 0:
            row["skipped"] = "this market has its own exit rule on the live book (half at Target 1)" if a in own_rule \
                else "the live stop is no longer the entry stop"
            out["assets"][a] = row
            continue
        df = data.load(a)
        t_open = pd.Timestamp(tr["opened_utc"], tz="UTC")
        i_in = int(df.index.searchsorted(t_open))
        if i_in >= len(df) or df.index[i_in] != t_open:
            row["skipped"] = "no bar at the trade's open time"
            out["assets"][a] = row
            continue
        px = dict((k, df[k].values.astype(float)) for k in ("open", "high", "low", "close"))
        n = len(df)
        x4 = four_hour(df.index, px)
        fee = shadows.asset_cfg(a, CFG)["cost_side"]
        R = abs(entry - stop)
        last = float(px["close"][n - 1])
        net = lambda p: qty * side * (p - entry) - fee * qty * (entry + p)      # noqa: E731
        row.update(last_bar=str(df.index[n - 1])[:16], last_close=last, r_usd=round(qty * R, 2),
                   open_r=round(side * (last - entry) / R, 2), open_net_usd=round(net(last), 2),
                   entry_gap=round(abs(float(px["open"][i_in]) - entry) / entry * 100, 4), rules={})
        for name, rule in RULES.items():
            w = walk(side, entry, stop, i_in, n - 1, px, rule, x4)
            d = {"armed": w["armed_i"] is not None,
                 "armed_utc": None if w["armed_i"] is None else str(df.index[w["armed_i"]])[:16],
                 "peak_r": None if w["best"] is None else round(w["best"] / R, 2)}
            if w["exit_i"] is not None:
                d.update(closed=True, closed_utc=str(df.index[w["exit_i"]])[:16], closed_px=w["exit_px"],
                         closed_r=round(side * (w["exit_px"] - entry) / R, 2), banked_usd=round(net(w["exit_px"]), 2),
                         vs_open_now_usd=round(net(w["exit_px"]) - net(last), 2))
            else:
                d.update(closed=False, level=w["level"],
                         level_r=None if w["level"] is None else round(side * (w["level"] - entry) / R, 2),
                         locks_usd=None if w["level"] is None else round(net(w["level"]), 2),
                         away_pct=None if w["level"] is None else round(side * (last - w["level"]) / last * 100, 2))
            row["rules"][name] = d
        out["assets"][a] = row
        log("%s %s: open %+.1fR ($%+.0f); %s" % (a, tr["status"], row["open_r"], row["open_net_usd"], "; ".join(
            "%s %s" % (k, ("closed %s %+.1fR" % (v["closed_utc"], v["closed_r"])) if v["closed"] else
                       ("locks $%+.0f" % v["locks_usd"]) if v["level"] is not None else "not armed")
            for k, v in row["rules"].items())))
    return out


# =====================================================================================
# the report
# =====================================================================================
def load_groups():
    groups = {}
    for g, _a in CFG["universes"]:
        p = os.path.join(OUT, "today_%s.json" % g)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                groups[g] = json.load(fh)
    return groups


def pooled(groups):
    import exit_study as ex
    frames = {}
    for g in groups.values():
        for a, cv in g["curves"].items():
            for name, s in cv.items():
                frames[(a, name)] = pd.Series(s["eq"], index=pd.to_datetime(s["t"]))
    frame = pd.concat(frames, axis=1).sort_index().ffill().fillna(START)
    assets = sorted(set(k[0] for k in frame.columns))
    mid_t = pd.Timestamp(MID)
    out = {}
    for name in BOOKS:
        tot = frame[[(a, name) for a in assets]].sum(axis=1)
        base = START * len(assets)
        first = tot[tot.index < mid_t]
        b_mid = float(first.iloc[-1]) if len(first) else base
        out[name] = {"assets": len(assets), "pnl_usd": round(float(tot.iloc[-1] - base), 2),
                     "sharpe": ex.sharpe(pd.concat([pd.Series([base], index=[tot.index[0] - pd.Timedelta(days=1)]), tot])),
                     "max_dd_pct": ex.max_dd(np.concatenate([[base], tot.values])),
                     "first_half_usd": round(b_mid - base, 2), "second_half_usd": round(float(tot.iloc[-1]) - b_mid, 2)}
    return out


def better_than_hold(pool, per):
    m = pool["main"]
    for name in BOOKS:
        p = pool[name]
        beats = [a for a in ORDER if a in per and
                 per[a]["books"][name]["all"].get("pnl_usd", 0) > per[a]["books"]["main"]["all"].get("pnl_usd", 0)]
        g1, g2 = p["first_half_usd"] - m["first_half_usd"], p["second_half_usd"] - m["second_half_usd"]
        dd_ok = (p["max_dd_pct"] or 0) >= (m["max_dd_pct"] or 0)
        p.update(vs_main_usd=round(p["pnl_usd"] - m["pnl_usd"], 2), gap_first_half=round(g1, 2),
                 gap_second_half=round(g2, 2), markets_beating_main=beats, dd_no_worse=bool(dd_ok),
                 trades=sum(per[a]["books"][name]["all"].get("trades", 0) for a in per),
                 better_than_hold=None if name == "main" else bool(g1 > 0 and g2 > 0 and len(beats) >= 5 and dd_ok))


def per_trade(armed):
    """Reading (b): per armed trade the main book has CLOSED, R under the rule minus R under main, same entry."""
    out = {}
    for name in RULES:
        rows = [(a, r) for a in ORDER for r in armed.get(a, {}).get(name, []) if not r["main_open"]]
        d = {"armed": len(rows), "closed_by_rule": sum(1 for _a, r in rows if r["closed_by_rule"])}
        for key, sel in (("all", (1, 2)), ("first_half", (1,)), ("second_half", (2,))):
            x = [r["r_rule"] - r["r_main"] for _a, r in rows if r["half"] in sel]
            d[key] = {"n": len(x), "mean_dr": round(float(np.mean(x)), 3) if x else None,
                      "sum_dr": round(float(np.sum(x)), 2) if x else 0.0,
                      "better": sum(1 for v in x if v > 1e-9), "worse": sum(1 for v in x if v < -1e-9)}
        mk = {}
        for a in ORDER:
            x = [r["r_rule"] - r["r_main"] for b, r in rows if b == a]
            if x:
                mk[a] = {"n": len(x), "mean_dr": round(float(np.mean(x)), 3), "sum_dr": round(float(np.sum(x)), 2)}
        d["markets"] = mk
        d["markets_helped"] = [a for a, v in mk.items() if v["mean_dr"] > 0]
        d["main_worst_giveback_r"] = round(max([r["peak_r"] - r["r_main"] for _a, r in rows] or [0.0]), 2)
        d["rule_most_left_r"] = round(max([r["r_main"] - r["r_rule"] for _a, r in rows] or [0.0]), 2)
        d["mean_peak_r"] = round(float(np.mean([r["peak_r"] for _a, r in rows])), 2) if rows else None
        d["mean_r_main"] = round(float(np.mean([r["r_main"] for _a, r in rows])), 2) if rows else None
        d["mean_r_rule"] = round(float(np.mean([r["r_rule"] for _a, r in rows])), 2) if rows else None
        h1, h2 = d["first_half"]["mean_dr"], d["second_half"]["mean_dr"]
        d["helps_per_trade"] = bool(h1 is not None and h2 is not None and h1 > 0 and h2 > 0 and
                                    len(d["markets_helped"]) >= 5)
        out[name] = d
    return out


def reconcile_h60(per):
    rows, clean = [], True
    for g, _a in CFG["universes"]:
        p = os.path.join(H60_OUT, "today_%s.json" % g)
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as fh:
            ref = json.load(fh)["assets"]
        for a, r in ref.items():
            if a not in per:
                continue
            h, s = r["books"]["main"]["all"], per[a]["books"]["main"]["all"]
            same = abs(s.get("pnl_usd", 0) - h.get("pnl_usd", 0)) < 0.01 and s.get("trades") == h.get("trades")
            clean = clean and same
            rows.append({"asset": a, "h60_pnl": h.get("pnl_usd"), "pnl": s.get("pnl_usd"), "h60_trades": h.get("trades"),
                         "trades": s.get("trades"), "exact": bool(same)})
    return rows, clean and bool(rows)


def _f(v, pat="%+.0f"):
    return "n/a" if v is None else pat % v


def _yn(b):
    return "n/a" if b is None else ("YES" if b else "no")


def write_report(groups, log=print):
    per, armed = {}, {}
    for g in groups.values():
        per.update(g["assets"])
        armed.update(g["armed"])
    pool = pooled(groups)
    better_than_hold(pool, per)
    pt = per_trade(armed)
    rec, clean = reconcile_h60(per)
    tpath = os.path.join(OUT, "today_live.json")
    live = json.load(open(tpath, encoding="utf-8")) if os.path.exists(tpath) else None
    L = []
    w = L.append
    w("# H61: a wide profit floor for the main book's big winners")
    w("")
    w("Written by `research/h61_profit_floor.py` on %s UTC. Paper only. A replay of history this project has already "
      "read five times for exits. Nothing here is a proven edge, and nothing here changes a book." %
      time.strftime("%Y-%m-%d %H:%M", time.gmtime()))
    w("")
    w("Each rule takes every main-book trade at the main book's own fill, adds one wide stop that arms only on a big "
      "winner, and after an exit at that stop stays flat until the main book's next entry. R = the distance from "
      "entry to the entry stop.")
    w("")
    w("## Gates")
    w("")
    w("- The overlay with a rule that never arms reproduced `main` on %d of %d markets (every trade and the marked "
      "equity at every bar)." % (sum(1 for g in groups.values() for v in g["gate"].values() if v["ok"]),
                                 sum(len(g["gate"]) for g in groups.values())))
    if rec:
        w("- `main` here against H60's run: %s." % (
            "reproduced exactly on all %d markets" % len(rec) if clean else
            "NOT the same on %s (the readings store was rebuilt at the v5.2.7 deploy); the rules below are compared "
            "with the `main` of THIS run, like for like" % ", ".join(
                "%s (%s vs %s)" % (r["asset"], _f(r["pnl"]), _f(r["h60_pnl"])) for r in rec if not r["exact"])))
    w("")
    w("## (a) Whole books: is any rule better than holding?")
    w("")
    w("H36's test: pooled net P&L above the main book's in BOTH halves, above it in at least 5 of 8 markets, pooled "
      "max drawdown no worse.")
    w("")
    w("| Book | Net P&L | vs main | First half vs main | Second half vs main | Markets beating main | Max DD | "
      "Sharpe | Trades | Better than holding |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for name in BOOKS:
        p = pool[name]
        w("| `%s` | %s | %s | %s | %s | %s | %s%% | %s | %d | %s |" % (
            name, _f(p["pnl_usd"]), _f(p["vs_main_usd"]) if name != "main" else "",
            _f(p["gap_first_half"]) if name != "main" else _f(p["first_half_usd"]),
            _f(p["gap_second_half"]) if name != "main" else _f(p["second_half_usd"]),
            ("%d of %d" % (len(p["markets_beating_main"]), p["assets"])) if name != "main" else "",
            _f(p["max_dd_pct"], "%.1f"), _f(p["sharpe"], "%.2f"), p["trades"], _yn(p["better_than_hold"])))
    w("")
    w("(For `main` the two half columns show its own P&L in each half.)")
    w("")
    w("### Per market, whole window: net P&L (max drawdown)")
    w("")
    w("| Market | " + " | ".join("`%s`" % b for b in BOOKS) + " |")
    w("|---|" + "---|" * len(BOOKS))
    for a in ORDER:
        if a in per:
            w("| %s | " % a + " | ".join("%s (%s%%)" % (_f(per[a]["books"][b]["all"].get("pnl_usd")),
                                                        _f(per[a]["books"][b]["all"].get("max_dd_pct"), "%.0f"))
                                         for b in BOOKS) + " |")
    w("")
    w("### Per market, each half: net P&L")
    w("")
    w("| Market | Half | " + " | ".join("`%s`" % b for b in BOOKS) + " |")
    w("|---|---|" + "---|" * len(BOOKS))
    for a in ORDER:
        if a in per:
            for half, lab in (("first_half", "1st"), ("second_half", "2nd")):
                w("| %s | %s | " % (a, lab) + " | ".join(_f(per[a]["books"][b][half].get("pnl_usd")) for b in BOOKS) + " |")
    w("")
    w("## (b) The same question at equal size: R kept per armed trade")
    w("")
    w("Per main-book trade that armed the rule and that the main book has closed: the R the rule ended with minus "
      "the R the main book ended with, on the same entry and the same risk. No compounding, so one market cannot "
      "decide it. \"Helps per trade\" needs a mean above zero in BOTH halves and in at least 5 markets.")
    w("")
    w("| Rule | Armed trades | Closed by the rule | Mean peak | Main ended | Rule ended | Mean gain, all | 1st half "
      "(n) | 2nd half (n) | Better / worse | Markets helped | Helps per trade |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for name in RULES:
        d = pt[name]
        w("| `%s` | %d | %d | %sR | %sR | %sR | %sR | %sR (%d) | %sR (%d) | %d / %d | %d of %d | %s |" % (
            name, d["armed"], d["closed_by_rule"], _f(d["mean_peak_r"], "%.1f"), _f(d["mean_r_main"], "%+.1f"),
            _f(d["mean_r_rule"], "%+.1f"), _f(d["all"]["mean_dr"], "%+.2f"), _f(d["first_half"]["mean_dr"], "%+.2f"),
            d["first_half"]["n"], _f(d["second_half"]["mean_dr"], "%+.2f"), d["second_half"]["n"], d["all"]["better"],
            d["all"]["worse"], len(d["markets_helped"]), len(d["markets"]), _yn(d["helps_per_trade"])))
    w("")
    w("| Rule | Largest give-back the main book took from a peak | Most the rule left on the table in one trade |")
    w("|---|---|---|")
    for name in RULES:
        w("| `%s` | %sR | %sR |" % (name, _f(pt[name]["main_worst_giveback_r"], "%.1f"),
                                    _f(pt[name]["rule_most_left_r"], "%.1f")))
    w("")
    w("### Per market: armed trades and mean gain in R")
    w("")
    w("| Market | " + " | ".join("`%s`" % b for b in RULES) + " |")
    w("|---|" + "---|" * len(RULES))
    for a in ORDER:
        cells = []
        for name in RULES:
            v = pt[name]["markets"].get(a)
            cells.append("none armed" if v is None else "%d: %sR" % (v["n"], _f(v["mean_dr"], "%+.2f")))
        w("| %s | " % a + " | ".join(cells) + " |")
    w("")
    if live:
        w("## (c) Today's open main-book trades under each rule (description, not a test)")
        w("")
        w("Live book as of the page of %s UTC (engine %s). \"Locks\" = net dollars if the level were hit, at the live "
          "size." % (live.get("page_generated_utc"), live.get("version")))
        w("")
        w("| Market | Trade | Open now | " + " | ".join("`%s`" % b for b in RULES) + " |")
        w("|---|---|---|" + "---|" * len(RULES))
        for a in ORDER:
            r = live["assets"].get(a) or {}
            if "rules" not in r:
                w("| %s | %s | %s |" % (a, r.get("status", "FLAT"), r.get("skipped", "")) + " |" * len(RULES))
                continue
            cells = []
            for name in RULES:
                v = r["rules"][name]
                if v["closed"]:
                    cells.append("CLOSED %s at %sR, banked $%s (%s vs open now)" % (
                        v["closed_utc"][5:], _f(v["closed_r"], "%+.1f"), _f(v["banked_usd"]), _f(v["vs_open_now_usd"])))
                elif v["level"] is None:
                    cells.append("not armed (peak %sR)" % _f(v["peak_r"], "%.1f"))
                else:
                    cells.append("level %.6g = %sR, locks $%s, %s%% away" % (
                        v["level"], _f(v["level_r"], "%+.1f"), _f(v["locks_usd"]), _f(v["away_pct"], "%.1f")))
            w("| %s | %s from %.6g, %s | %sR, $%s | " % (a, r["status"], r["entry"], r["opened_utc"][5:],
                                                        _f(r["open_r"], "%+.1f"), _f(r["open_net_usd"])) +
              " | ".join(cells) + " |")
        w("")
    res = {"written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "pooled": pool, "per_trade": pt,
           "reconcile_h60": rec, "reconciled": clean, "markets": per, "armed": armed, "today": live,
           "gate": dict((a, v) for g in groups.values() for a, v in g["gate"].items())}
    with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    log("report written: %s" % os.path.join(OUT, "report.md"))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default=None)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--today", action="store_true")
    ap.add_argument("--page", default=os.path.join(ROOT, "out", "live", "page.json"))
    ap.add_argument("--fits-dir", default=None, help="default research/out/h61_profit_floor/fits_today")
    args = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    log = lambda *m: print(time.strftime("%H:%M:%S"), *m, flush=True)      # noqa: E731
    if args.today:
        r = today(args.page, log)
        with open(os.path.join(OUT, "today_live.json"), "w", encoding="utf-8") as fh:
            json.dump(r, fh, indent=1)
        return
    if args.report:
        groups = load_groups()
        if len(groups) != len(CFG["universes"]):
            raise SystemExit("only %d of %d groups ran: %s" % (len(groups), len(CFG["universes"]), sorted(groups)))
        write_report(groups, log)
        return
    import exit_study as ex
    groups = dict((g, list(a)) for g, a in CFG["universes"])
    fits = args.fits_dir or os.path.join(OUT, "fits_today")
    ex.below_normal()
    for g in ([args.group] if args.group else list(groups)):
        ex.acquire("h61 %s" % g, log)
        try:
            r = run_group(g, groups[g], fits, log)
        finally:
            ex.release()
        with open(os.path.join(OUT, "today_%s.json" % g), "w", encoding="utf-8") as fh:
            json.dump(r, fh)
        gc.collect()


if __name__ == "__main__":
    main()
