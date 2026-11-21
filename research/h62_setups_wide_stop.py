# -*- coding: utf-8 -*-
"""H62: the Setups book (b_targets) with the main book's stop where it is wider. Research only; registered in
research/HYPOTHESES.md before this file existed. It reads the evidence store and the cached fits; it changes no book.

    /data/venv-research/bin/python research/h62_setups_wide_stop.py --group crypto --fits-dir research/out/h60_regime_exits/fits_today
    ... one run per group (crypto metals fx index energy), then:
    /data/venv-research/bin/python research/h62_setups_wide_stop.py --report

The Setups book is run by `run_setups`, a copy of engine15.shadows.run reduced to the targets rule. With no wide stop it
must reproduce shadows.run_challenger("b_targets") exactly (the gate). The main book is backtest.run_book under the live
rules (live.asset_cfg), without the total-risk cap across books.
"""
import argparse
import gc
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

from engine15 import backtest, data, exits, labels, live, policy, shadows  # noqa: E402
from engine15.shadows import START_EQUITY, TRADE_COLS  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "h62_setups_wide_stop")
START = START_EQUITY
MID = "2023-06-08"
HOLDOUT = "2025-11-11"
FORWARD = "2026-11-11"
END = "2026-11-21 13:45"
ORDER = ["SPX", "USDJPY", "BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "WTI", "BRENT"]
VAULT = ("BTCUSDT", "ETHUSDT")
MODES = ("entry", "follow", "entry_tighten")                      # A (PRIMARY), B, C
NAMES = {"current": "current rule", "entry": "A wide_entry", "follow": "B wide_follow", "entry_tighten": "C wide_entry_tighten"}
BOOKS = ["current"] + list(MODES)
PART = exits.PART
IN_BAR = ("STOP", "TRAIL", "T2")                                  # main-book exits filled inside a bar (held at its open)


# =====================================================================================
# the main book's position and stop in force for each bar (known at that bar's open)
# =====================================================================================
def main_live(prep, a, lo, n):
    """backtest.run_book as the live step wires it (live.py, step 3), without the total-risk cap across books."""
    ev, cfg = prep["ev"][a], prep["cfg"]
    acfg = live.asset_cfg(a, dict(cfg))
    t1_of = t2_of = None
    if acfg.get("be_t1"):
        if acfg.get("t2_exit"):
            t2_of = lambda i, side, entry, stop, ev=ev: live.plan_targets(                       # noqa: E731
                int(side), float(entry), float(stop), ev.iloc[max(i - 1, 0)]).get("target_2")
        t1_of = lambda i, side, entry, stop, ev=ev: live.plan_targets(                           # noqa: E731
            int(side), float(entry), float(stop), ev.iloc[max(i - 1, 0)]).get("target_1")
    trail_aux = None
    if acfg.get("trail_stop"):
        ax = shadows.aux_from_ev(ev, prep["px"][a])
        trail_aux = {"atr15": ax["atr15"], "sw_lo": ax["sw_lo"], "sw_hi": ax["sw_hi"]}
    return backtest.run_book(prep["px"][a], prep["odds"][a], ev["shock"].values, ev["tide"].values,
                             (cfg["barrier_atr"] * ev["atr1h"]).values, acfg, lo, n,
                             bias=ev["htf_bias"].values, guard=ev["release_soon"].values, t1_of=t1_of, t2_of=t2_of,
                             trail_aux=trail_aux), acfg


def main_series(b, unit, stop_units, n):
    """-> (m_pos, m_stop): the main book's side during bar i and the stop in force for that bar. In its entry bar the
    stop is the entry stop; afterwards the level standing at the previous close (a trailed stop is live from the next
    bar). A trade closed at an open (a flip) is not held in that bar; one closed inside a bar is."""
    m_pos = np.zeros(n, dtype=np.int8)
    m_stop = np.full(n, np.nan)
    st = b["stop"]
    for t in b["trades"].itertuples():
        i_in, i_out, side = int(t.i_in), int(t.i_out), int(t.side)
        if i_in < 0:
            continue
        held_last = i_out if (t.why_out == "OPEN" or any(w in str(t.why_out) for w in IN_BAR)) else i_out - 1
        if held_last < i_in:
            continue
        m_pos[i_in:held_last + 1] = side
        m_stop[i_in] = float(t.p_in) - side * stop_units * unit[i_in - 1]
        if held_last > i_in:
            m_stop[i_in + 1:held_last + 1] = st[i_in:held_last]
    return m_pos, m_stop


# =====================================================================================
# the Setups book: shadows.run reduced to the targets rule, plus the wide stop
# =====================================================================================
def _further(side, entry, x, y):
    """Is stop x further from the entry than stop y, on the losing side?"""
    return side * (entry - x) > side * (entry - y)


def run_setups(px, odds, shock, tide, unit, cfg, lo, hi, bias=None, guard=None, times_ms=None, row_of=None,
               mode=None, m_pos=None, m_stop=None):
    """-> {"trades", "equity", "held", "state", "wide": per-trade facts}. mode None = b_targets as it is."""
    o, h, l, c = px["open"], px["high"], px["low"], px["close"]
    n = len(c)
    held = np.zeros(n, dtype=np.int8)
    eq_arr = np.full(n, np.nan)
    trades, facts = [], []
    fee = cfg["cost_side"]
    tms = (lambda i: None) if times_ms is None else (lambda i: int(times_ms[i]))
    S = {"pos": 0, "idle": 0, "qty": 0.0, "entry": 0.0, "eq": START, "stop": np.nan, "why_in": "", "pending": None,
         "t_in": -1, "t_in_ms": None, "stop0": np.nan, "own0": np.nan, "qty0": 0.0, "t1": None, "t2": None,
         "t1_hit": False, "part": {"pnl": 0.0, "fees": 0.0, "qpx": 0.0, "q": 0.0, "tags": []}, "fact": None}

    def book_trade(i, price, why, pnl, fees_t, q0):
        s0 = S["stop0"]
        risk = q0 * abs(S["entry"] - s0) if s0 == s0 else np.nan
        r = pnl / risk if risk and risk == risk else np.nan
        trades.append((S["t_in_ms"], tms(i), S["t_in"], i, S["pos"], S["entry"], price, S["why_in"], why,
                       pnl / (q0 * S["entry"]) * 100.0, S["eq"], q0, pnl, fees_t, s0, risk, r, S["t1"], S["t2"]))
        if S["fact"] is not None:
            facts.append(dict(S["fact"], i_out=i, why_out=why, pnl_usd=float(pnl)))

    def close(i, price, why):
        qty, pos, entry, part = S["qty"], S["pos"], S["entry"], S["part"]
        gross = qty * pos * (price - entry)
        fees = fee * qty * (entry + price)
        S["eq"] += gross - fees
        if part["q"]:
            tot_q = part["q"] + qty
            book_trade(i, (part["qpx"] + qty * price) / tot_q, "+".join(part["tags"] + [why]),
                       part["pnl"] + gross - fees, part["fees"] + fees, tot_q)
        else:
            book_trade(i, price, why, gross - fees, fees, qty)
        S.update(pos=0, qty=0.0, stop=np.nan, t1=None, t2=None, t1_hit=False, fact=None,
                 part={"pnl": 0.0, "fees": 0.0, "qpx": 0.0, "q": 0.0, "tags": []})

    def take_part(i, price, q, tag):
        gross = q * S["pos"] * (price - S["entry"])
        fees = fee * q * (S["entry"] + price)
        S["eq"] += gross - fees
        p = S["part"]
        p["pnl"] += gross - fees
        p["fees"] += fees
        p["qpx"] += q * price
        p["q"] += q
        p["tags"].append(tag)
        S["qty"] -= q

    def main_stop_at(i, side, entry, own):
        """The main book's stop for bar i if it counts (same side, further than the book's own), else None."""
        if mode is None or m_pos[i] != side:
            return None
        w = m_stop[i]
        return float(w) if (w == w and _further(side, entry, w, own)) else None

    def open_pos(i, side, price, why, k_dec):
        dist = cfg["stop_units"] * unit[i - 1]
        own = price - side * dist
        w = main_stop_at(i, side, price, own)
        carried = own if w is None else w
        lev = backtest.leverage(cfg, price, dist if w is None else abs(price - carried))
        S.update(pos=side, entry=price, qty=S["eq"] * lev / price, t_in=i, why_in=why, t_in_ms=tms(i), stop=carried,
                 stop0=carried, own0=own, t1=None, t2=None, t1_hit=False)
        S["qty0"] = S["qty"]
        if row_of is not None:
            t = live.plan_targets(int(side), float(price), float(own), row_of(k_dec))   # targets from the book's OWN stop
            S.update(t1=t.get("target_1"), t2=t.get("target_2"))
        S["fact"] = {"i_in": i, "side": side, "entry": float(price), "own": float(own), "carried": float(carried),
                     "wide_at_entry": w is not None, "ratio": float(abs(price - carried) / dist) if dist else 1.0,
                     "moves_out": 0, "moves_in": 0}

    p_up, p_dn = odds[:, labels.UP], odds[:, labels.DOWN]
    for i in range(lo, hi):
        # ---- 1. fills at this open
        pending = S["pending"]
        if pending is not None and len(pending) > 3 and pending[3] > 0:
            S["pending"] = tuple(pending[:3]) + (pending[3] - 1,)
        elif pending is not None:
            a, target, why = pending[:3]
            if S["pos"] != 0 and target != S["pos"]:
                close(i, o[i], a)
            if target != 0 and S["pos"] == 0:
                open_pos(i, target, o[i], a, i - 1)
            S["pending"] = None
        held[i] = S["pos"]
        # ---- 1b. B / C: the stop for this bar, from what the main book holds at this open (never after Target 1)
        if mode in ("follow", "entry_tighten") and S["pos"] != 0 and not S["t1_hit"] and i > S["t_in"]:
            pos, entry = S["pos"], S["entry"]
            w = main_stop_at(i, pos, entry, S["own0"])
            want = S["own0"] if w is None else w
            cur = S["stop"]
            if want != cur:
                out = _further(pos, entry, want, cur)
                if mode == "follow" or not out:                    # C never moves out
                    S["stop"] = want
                    S["fact"]["moves_out" if out else "moves_in"] += 1
        # ---- 2. the protective stop, first inside the bar
        pos, stop = S["pos"], S["stop"]
        word = "STOP_BE" if S["t1_hit"] else "STOP"
        if pos == 1 and l[i] <= stop:
            close(i, min(o[i], stop), word)
            S["idle"] = 0
        elif pos == -1 and h[i] >= stop:
            close(i, max(o[i], stop), word)
            S["idle"] = 0
        # ---- 2b. Target 1 then Target 2, both may fill in one bar
        if S["pos"] != 0 and S["t1"] is not None:
            pos = S["pos"]
            reach = (lambda t: h[i] >= t) if pos == 1 else (lambda t: l[i] <= t)
            if not S["t1_hit"] and reach(S["t1"]):
                take_part(i, S["t1"], S["qty"] * PART, "T1")
                S["t1_hit"] = True
                S["stop"] = S["entry"]
            if S["t1_hit"] and S["t2"] is not None and S["pos"] != 0 and reach(S["t2"]):
                close(i, S["t2"], "T2")
                S["idle"] = 0
        # ---- 3. the decision at this close
        pos = S["pos"]
        pu = p_up[i]
        a, target, why = policy.decide(pos, S["idle"], None if pu != pu else pu, p_dn[i], bool(shock[i]),
                                       tide[i] if tide[i] == tide[i] else 0.0, cfg,
                                       bias=0 if bias is None or bias[i] != bias[i] else int(bias[i]),
                                       guard=False if guard is None else bool(guard[i]))
        if a == policy.IDLE:
            S["idle"] += 1
        elif a == policy.STEP_ASIDE:
            S["idle"] = 1
        elif a != policy.HOLD:
            S["idle"] = 0
        if a in (policy.ENTER, policy.FORCED, policy.FLIP, policy.STEP_ASIDE):
            if not (a == policy.STEP_ASIDE and pos == 0):
                delay = int(cfg.get("fill_delay_bars", 0) or 0)
                if not (delay and S["pending"] is not None and S["pending"][1] == target):
                    S["pending"] = (a, target, why) if not delay else (a, target, why, delay)
        eq_arr[i] = S["eq"] + (S["qty"] * S["pos"] * (c[i] - S["entry"]) if S["pos"] else 0.0)
    open_fact = None if S["fact"] is None else dict(S["fact"], i_out=None, why_out="OPEN", pnl_usd=None,
                                                    stop_now=None if S["stop"] != S["stop"] else float(S["stop"]),
                                                    t1_hit=bool(S["t1_hit"]))
    return {"trades": pd.DataFrame(trades, columns=TRADE_COLS), "equity": eq_arr, "held": held,
            "state": {"pos": int(S["pos"]), "eq": float(S["eq"]), "entry": float(S["entry"]),
                      "stop": None if S["stop"] != S["stop"] else float(S["stop"])},
            "wide": facts, "open": open_fact}


def same_book(ref, mine, lo, n, tol=1e-6):
    a, b = ref["trades"], mine["trades"]
    if len(a) != len(b):
        return False, "trades %d vs %d" % (len(a), len(b))
    for col in ("i_in", "i_out", "side"):
        if not np.array_equal(a[col].values.astype(int), b[col].values.astype(int)):
            return False, "trade column %s differs" % col
    if not np.array_equal(a["why_out"].values, b["why_out"].values):
        return False, "exit words differ"
    for col in ("p_in", "p_out", "qty", "pnl_usd", "fees_usd", "equity", "stop0"):
        d = np.abs(a[col].values.astype(float) - b[col].values.astype(float))
        if len(d) and float(np.nanmax(d)) > tol:
            return False, "trade column %s differs by %.9f" % (col, float(np.nanmax(d)))
    ea, eb = ref["equity"][lo:n], mine["equity"][lo:n]
    if not np.array_equal(np.isfinite(ea), np.isfinite(eb)):
        return False, "equity is marked on different bars"
    d = np.abs(ea - eb)[np.isfinite(ea)]
    if len(d) and float(d.max()) > tol:
        return False, "marked equity differs by %.9f" % float(d.max())
    return True, "same"


# =====================================================================================
# one group
# =====================================================================================
def _stats(ex, b, times, lo, n, mid_i, hold_i, fwd_i):
    eq, tr = b["equity"], b["trades"]

    def seg(a, z, base):
        s = ex.seg_stats(eq, tr[(tr.i_out >= a) & (tr.i_out < z)], times, a, z, base)
        t = tr[(tr.i_out >= a) & (tr.i_out < z)]
        s["worst_trade_usd"] = round(float(t.pnl_usd.min()), 2) if len(t) else None
        r = t.r_mult.dropna()                                      # the result in units of the trade's own risk at the
        s["sum_r"] = round(float(r.sum()), 2)                      # carried stop: what a member sized to lose a fixed
        s["worst_r"] = round(float(r.min()), 2) if len(r) else None  # share of the wallet at that stop would see
        s["win_rate_pct"] = round(100.0 * float((t.pnl_usd > 0).mean()), 1) if len(t) else None
        return s

    def base(i):
        v = eq[i - 1] if i - 1 >= lo else np.nan
        return float(v) if np.isfinite(v) else START
    out = {"all": seg(lo, n, START), "first_half": seg(lo, mid_i, START), "second_half": seg(mid_i, n, base(mid_i)),
           "holdout": seg(hold_i, n, base(hold_i)), "forward": seg(fwd_i, n, base(fwd_i)),
           "exits": dict((str(k), int(v)) for k, v in tr.why_out.value_counts().items()),
           "open_at_end": {1: "LONG", -1: "SHORT"}.get(b["state"]["pos"], "FLAT")}
    w = b["wide"]
    if w:
        ratios = np.array([x["ratio"] for x in w])
        wide = np.array([x["wide_at_entry"] for x in w])
        out["wide"] = {"trades": len(w), "wide_at_entry": int(wide.sum()),
                       "wide_at_entry_pct": round(100.0 * float(wide.mean()), 1),
                       "ratio_median_when_wide": round(float(np.median(ratios[wide])), 2) if wide.any() else None,
                       "ratio_max": round(float(ratios.max()), 2),
                       "moves_out": int(sum(x["moves_out"] for x in w)), "moves_in": int(sum(x["moves_in"] for x in w)),
                       "trades_with_a_move": int(sum(1 for x in w if x["moves_out"] or x["moves_in"]))}
    return out


def run_group(g, assets, fits_root, log=print):
    import exit_study as ex
    import h59_half_be as h59
    t0 = time.time()
    prep = h59.prep_cut(g, assets, os.path.join(fits_root, g), END, log=log)
    times = prep["times"]
    tms = data.to_ms(times)
    n = len(times)
    idx = lambda s: int(times.searchsorted(pd.Timestamp(s, tz="UTC")))   # noqa: E731
    out = {"group": g, "end": str(times[n - 1])[:16], "assets": {}, "gate": {}, "curves": {}, "eth_trade": {}}
    for a in assets:
        ok = np.isfinite(prep["odds"][a][:, 0])
        lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
        mid_i = min(max(idx(MID), lo + 1), n - 1)
        hold_i, fwd_i = min(max(idx(HOLDOUT), lo + 1), n - 1), min(max(idx(FORWARD), lo + 1), n - 1)
        aux = shadows.aux_from_ev(prep["ev"][a], prep["px"][a])
        inp = shadows.book_inputs(prep, a)
        cfg = shadows.asset_cfg(a, dict(prep["cfg"]))
        tgt = aux["targets"]
        row_of = lambda k: tgt.iloc[k] if len(tgt.columns) else pd.Series(dtype=float)   # noqa: E731
        kw = dict(bias=inp["bias"], guard=inp["guard"], times_ms=tms, row_of=row_of)
        ref = h59.run_book("b_targets", prep, a, lo, n, aux)
        cur = run_setups(inp["px"], inp["odds"], inp["shock"], inp["tide"], inp["unit"], cfg, lo, n, **kw)
        okk, why = same_book(ref, cur, lo, n)
        out["gate"][a] = {"ok": okk, "detail": why, "trades": int(len(ref["trades"]))}
        if not okk:
            raise RuntimeError("GATE FAILED on %s: the reduced copy is not b_targets: %s" % (a, why))
        mb, acfg = main_live(prep, a, lo, n)
        m_pos, m_stop = main_series(mb, inp["unit"], acfg["stop_units"], n)
        books = {"current": cur}
        for mode in MODES:
            books[mode] = run_setups(inp["px"], inp["odds"], inp["shock"], inp["tide"], inp["unit"], cfg, lo, n,
                                     mode=mode, m_pos=m_pos, m_stop=m_stop, **kw)
        mtr = mb["trades"]
        res = {"window": [str(times[lo])[:16], str(times[n - 1])[:16]], "split": str(times[mid_i])[:16],
               "main_live": {"pnl_usd": round(float(mb["equity"][n - 1] - START), 2), "trades": int(len(mtr)),
                             "flat_bars_pct": round(100.0 * float((mb["held"][lo:n] == 0).mean()), 1),
                             "risk_cap_left_out": True},
               "books": dict((k, _stats(ex, b, times, lo, n, mid_i, hold_i, fwd_i)) for k, b in books.items())}
        curves = {}
        for k, b in books.items():
            cv = ex.daily(b["equity"], times, lo, n)
            curves[k] = {"t": [str(x)[:10] for x in cv.index], "eq": [round(float(x), 2) for x in cv.values]}
        out["assets"][a] = res
        out["curves"][a] = curves
        if a == "ETHUSDT":                                         # the trade of 20 Nov 2026 19:30 UTC, if the replay has it
            i0, i1 = idx("2026-11-20 19:00"), idx("2026-11-20 20:15")
            for k, b in books.items():
                rows = [x for x in b["wide"] if i0 <= x["i_in"] <= i1]
                if b["open"] is not None and i0 <= b["open"]["i_in"] <= i1:
                    rows.append(b["open"])
                out["eth_trade"][k] = [dict(x, t_in=str(times[x["i_in"]])[:16],
                                            t_out=None if x["i_out"] is None else str(times[x["i_out"]])[:16])
                                       for x in rows]
        log("%s %s: gate passed (%d trades); %s .. %s; main(live) %+.0f; %s (%.0fs)" % (
            g, a, len(ref["trades"]), res["window"][0], res["window"][1], res["main_live"]["pnl_usd"],
            ", ".join("%s %+.0f" % (k, res["books"][k]["all"].get("pnl_usd", 0)) for k in BOOKS), time.time() - t0))
        del books, cur, ref, mb
        gc.collect()
    del prep
    gc.collect()
    return out


# =====================================================================================
# the report
# =====================================================================================
def load_groups():
    out = {}
    for f in sorted(os.listdir(OUT)):
        if f.startswith("group_") and f.endswith(".json"):
            with open(os.path.join(OUT, f), encoding="utf-8") as fh:
                d = json.load(fh)
            out[d["group"]] = d
    return out


def pooled(groups, assets=None):
    """Sum over markets of each book's dollars per segment; the worst fall of the summed daily curve."""
    per = dict((a, r) for g in groups.values() for a, r in g["assets"].items() if assets is None or a in assets)
    curves = dict((a, c) for g in groups.values() for a, c in g["curves"].items() if a in per)
    out = {}
    for k in BOOKS:
        row = {}
        for seg in ("all", "first_half", "second_half", "holdout", "forward"):
            row[seg] = round(sum(per[a]["books"][k][seg].get("pnl_usd", 0.0) for a in per), 2)
            row[seg + "_trades"] = int(sum(per[a]["books"][k][seg].get("trades", 0) or 0 for a in per))
            row[seg + "_r"] = round(sum(per[a]["books"][k][seg].get("sum_r", 0.0) or 0.0 for a in per), 1)
        wins = sum((per[a]["books"][k]["all"].get("win_rate_pct") or 0.0) * (per[a]["books"][k]["all"].get("trades") or 0)
                   for a in per)
        row["win_rate_pct"] = round(wins / row["all_trades"], 1) if row["all_trades"] else None
        row["worst_r"] = min((per[a]["books"][k]["all"].get("worst_r") or 0.0) for a in per)
        frames = [pd.Series(curves[a][k]["eq"], index=pd.to_datetime(curves[a][k]["t"])) for a in per]
        tot = pd.concat(frames, axis=1).sort_index().ffill().bfill().sum(axis=1)
        peak = tot.cummax()
        row["max_dd_pct"] = round(float(((tot - peak) / peak).min()) * 100, 2)
        row["worst_trade_usd"] = min((per[a]["books"][k]["all"].get("worst_trade_usd") or 0.0) for a in per)
        w = [per[a]["books"][k].get("wide") for a in per]
        w = [x for x in w if x]
        if w:
            n = sum(x["trades"] for x in w)
            row["wide_at_entry_pct"] = round(100.0 * sum(x["wide_at_entry"] for x in w) / n, 1) if n else None
            row["ratio_max"] = max(x["ratio_max"] for x in w)
            row["moves_out"], row["moves_in"] = sum(x["moves_out"] for x in w), sum(x["moves_in"] for x in w)
        out[k] = row
    return out, per


def verdict(pool_all, pool_vault):
    c, a = pool_all["current"], pool_all["entry"]
    vc, va = pool_vault["current"], pool_vault["entry"]
    checks = {"pooled_first_half": a["first_half"] >= c["first_half"], "pooled_second_half": a["second_half"] >= c["second_half"],
              "worst_fall_not_deeper": a["max_dd_pct"] >= c["max_dd_pct"],
              "btc_eth_first_half": va["first_half"] >= vc["first_half"], "btc_eth_second_half": va["second_half"] >= vc["second_half"]}
    return all(checks.values()), checks


def write_report(log=print):
    groups = load_groups()
    pool_all, per = pooled(groups)
    pool_vault, _ = pooled(groups, VAULT)
    ok, checks = verdict(pool_all, pool_vault)
    eth = next((g["eth_trade"] for g in groups.values() if g.get("eth_trade")), {})
    res = {"end": END, "groups": sorted(groups), "gate": dict((a, v) for g in groups.values() for a, v in g["gate"].items()),
           "pooled": pool_all, "pooled_btc_eth": pool_vault, "A_not_worse": ok, "A_checks": checks,
           "per_market": dict((a, per[a]) for a in ORDER if a in per), "eth_trade_20_nov": eth}
    with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=float)
    L = ["# H62: the Setups book with the main book's stop where it is wider", "",
         "History replay to %s UTC, paper. Registered before any number (research/HYPOTHESES.md)." % END, "",
         "Gate: the reduced copy reproduced `b_targets` on %d of %d markets." % (
             sum(1 for v in res["gate"].values() if v["ok"]), len(res["gate"])), "",
         "## Pooled, eight markets", "",
         "| Book | Net | First half | Second half | Holdout | Forward | Trades | Won | Worst fall | Worst trade | Sum of R (all / 1st / 2nd / forward) | Worst R | Wide at entry | Largest stop ratio | Moves out / in |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]

    def line(k, r):
        return "| %s | %+.0f | %+.0f | %+.0f | %+.0f | %+.0f | %d | %s%% | %.1f%% | %+.0f | %+.1f / %+.1f / %+.1f / %+.1f | %+.1f | %s | %s | %s |" % (
            NAMES[k], r["all"], r["first_half"], r["second_half"], r["holdout"], r["forward"], r["all_trades"],
            r["win_rate_pct"], r["max_dd_pct"], r["worst_trade_usd"], r["all_r"], r["first_half_r"], r["second_half_r"],
            r["forward_r"], r["worst_r"],
            "-" if r.get("wide_at_entry_pct") is None or k == "current" else "%.1f%%" % r["wide_at_entry_pct"],
            "-" if k == "current" else "%.1fx" % r.get("ratio_max", 1.0),
            "-" if k in ("current", "entry") else "%d / %d" % (r.get("moves_out", 0), r.get("moves_in", 0)))
    L += [line(k, pool_all[k]) for k in BOOKS]
    L += ["", "R = a trade's result divided by its own risk at the stop it carried at the fill. The paper book trades BTC and",
          "ETH at full size whatever the stop, so its dollars grow with a wider stop; a member is sized to lose a fixed share",
          "of the wallet at the stop, so the sum of R is the member's view.",
          "", "## BTC and ETH only (what the vault copies)", "", L[8], L[9]] + [line(k, pool_vault[k]) for k in BOOKS]
    L += ["", "## Verdict for A (PRIMARY)", "",
          "A is %s the current rule by the registered bar. Checks: %s." % (
              "NOT WORSE than" if ok else "NOT SHOWN TO BE BETTER than",
              ", ".join("%s %s" % (k, "yes" if v else "NO") for k, v in checks.items())), "",
          "## Per market (net, trades, worst fall)", "",
          "| Market | " + " | ".join(NAMES[k] for k in BOOKS) + " | Main (live rules) | Main flat |", "|---|" + "---|" * (len(BOOKS) + 2)]
    for a in ORDER:
        if a in per:
            L.append("| %s | %s | %+.0f (%d) | %.0f%% |" % (
                a, " | ".join("%+.0f (%d, %.1f%%)" % (per[a]["books"][k]["all"].get("pnl_usd", 0),
                                                      per[a]["books"][k]["all"].get("trades", 0) or 0,
                                                      per[a]["books"][k]["all"].get("max_dd_pct", 0) or 0) for k in BOOKS),
                per[a]["main_live"]["pnl_usd"], per[a]["main_live"]["trades"], per[a]["main_live"]["flat_bars_pct"]))
    L += ["", "## The ETH trade of 20 Nov 2026 in the replay", ""]
    for k in BOOKS:
        rows = eth.get(k) or []
        L.append("- %s: %s" % (NAMES[k], "not in the replay" if not rows else "; ".join(
            "in %s at %.2f, own stop %.2f, carried %.2f (%.1fx), out %s %s, %s" % (
                x["t_in"], x["entry"], x["own"], x["carried"], x["ratio"], x.get("t_out") or "still open",
                x.get("why_out"), "n/a" if x.get("pnl_usd") is None else "%+.0f" % x["pnl_usd"]) for x in rows)))
    L += ["", "Not in the replay: the main book's total-risk cap across books. A replay is not a forward result."]
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    log("\n".join(L))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--group")
    ap.add_argument("--fits-dir", default=os.path.join(ROOT, "research", "out", "h60_regime_exits", "fits_today"))
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    if args.group:
        from engine15.config import CFG
        assets = dict(CFG["universes"])[args.group]
        res = run_group(args.group, list(assets), args.fits_dir)
        with open(os.path.join(OUT, "group_%s.json" % args.group), "w", encoding="utf-8") as fh:
            json.dump(res, fh, default=float)
    if args.report:
        write_report()


if __name__ == "__main__":
    main()
