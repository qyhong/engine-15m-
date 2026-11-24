# -*- coding: utf-8 -*-
"""H116: BTC and ETH, the RETEST of a capitulation low. Rule C1 buys when the low holds, rule C2 buys a sweep of the low
that is reclaimed. Research only; registered in research/HYPOTHESES.md (H116) before any H116 number on history was
computed. Reads only the 15-minute bar files and the funding files (through H107's loader); uses no evidence store, no
fits, no engine book. Changes nothing in the engine, the books or the vault.

    py -3 -X utf8 research/h116_retest_capitulation_low.py [--data-dir <folder>] [--event]

History run: every input is CUT at 2025-11-10 23:45 UTC before anything is computed (H107's `coin_frame`), and a trade
must end by that bar. `--event` reads bars from 2026-08-01 only and states, for the levels made from 2026-11-19 on, what
the two rules need to see (Part 4; descriptive, no result computed).
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import h107_capitulation_rebound as h107  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "h116_retest_capitulation_low")
COINS = h107.COINS
START, CUT, MID = h107.START, h107.CUT, h107.MID
EVENT_FROM, EVENT_LOAD = h107.EVENT_FROM, h107.EVENT_LOAD
FEE = h107.FEE
B, SEED = 10000, 20261124
REG = {"zone": 0.015, "bounce": 0.05, "life_days": 30, "c1_atr": 1.0, "pad_atr": 0.5, "c2_bars": 96, "hold": 192}
MIN_ALL, MIN_HALF, ALPHA = 60, 20, 0.05
FULL_VIEW_DAYS = 34                  # Part 1: a level is "seen in full" when its trigger is 30 days + 96 hours before the cut
RULES = ("C1", "C2")
HOWS = ("stop", "T1_then_entry", "T1_T2", "T1_then_time", "time")


# ------------------------------------------------------------------------------------------------- the level machine
def machine(fx, p=REG, k_from=0, n=None):
    """Every level made by a rule A onset at a bar >= k_from, walked through its states with bars [0, n) only.
    Each step at bar j uses bars up to j, so the levels and signals found on a prefix of the data are the same as on
    the whole of it (checked by `lookahead_test`). -> list of level dicts."""
    t, h, l, c, atr = fx["t"], fx["h"], fx["l"], fx["c"], fx["atr1h"]
    n = len(t) if n is None else n
    life = pd.Timedelta(days=p["life_days"])
    onsets = np.flatnonzero(fx["A"][:n])
    onsets = onsets[onsets >= k_from]
    levels, dup = [], 0
    for k in onsets:
        k = int(k)
        L = float(fx["low16"][k])
        w = l[k - 15:k + 1]
        b = k - 15 + int(np.argmin(w))                            # the first of the 16 bars with that low
        if any(lv["L"] == L and t[k] - t[lv["k"]] <= life for lv in levels[-40:]):
            dup += 1                                              # the same low again: one level
            continue
        e_full = int(t.searchsorted(t[k] + life, side="right")) - 1   # last bar that opens within 30 days of bar k
        e = min(e_full, n - 1)
        lv = {"k": k, "L": L, "b": b, "e": e, "complete": bool(t[k] + life <= t[n - 1]), "a": None, "f": None,
              "s": None, "u": None, "m": None, "broke": None, "c1": None, "c2": None, "state": None, "outcome": None}
        levels.append(lv)
        arm = np.flatnonzero(h[b + 1:e + 1] >= (1.0 + p["bounce"]) * L)
        und = np.flatnonzero(l[b + 1:e + 1] < L)
        a = b + 1 + int(arm[0]) if len(arm) else None
        u = b + 1 + int(und[0]) if len(und) else None
        if u is not None and (a is None or u <= a):
            lv["state"], lv["u"] = "undercut", u                  # undercut before (or in) the arming bar: dead
            continue
        if a is None:
            lv["state"] = "no_bounce"
            continue
        lv["a"] = a
        g = max(a, k) + 1
        touch = np.flatnonzero(l[g:e + 1] <= (1.0 + p["zone"]) * L)
        if not len(touch):
            lv["state"] = "armed_no_touch"
            continue
        f = g + int(touch[0])
        lv["f"], lv["state"] = f, "retest"
        m, s, sweep_low = np.inf, None, np.inf
        c1 = c2 = None
        c1_off = c2_off = False
        for j in range(f, e + 1):
            m = min(m, l[j])
            if s is None and l[j] < L:
                s = j
            ok = np.isfinite(atr[j]) and atr[j] > 0
            if s is not None and c2 is None and not c2_off:
                sweep_low = min(sweep_low, l[j])
                if j - s > p["c2_bars"] - 1:
                    c2_off = True
                elif c[j] > L and ok:
                    c2 = {"j": j, "stop": float(sweep_low - p["pad_atr"] * atr[j]), "low": float(sweep_low)}
            if c1 is None and not c1_off:
                if c[j] < L:
                    c1_off, lv["broke"] = True, j
                elif ok and c[j] >= m + p["c1_atr"] * atr[j]:
                    c1 = {"j": j, "stop": float(min(L, m) - p["pad_atr"] * atr[j]), "low": float(m)}
            # both rules settled; C1's turn before any sweep ends the first retest (a later sweep gives no C2)
            if (c1 is not None or c1_off) and (c2 is not None or c2_off or (s is None and c1 is not None)):
                break
        lv["s"], lv["c1"], lv["c2"], lv["m"] = s, c1, c2, float(m)
        lv["outcome"] = "HOLD" if c1 is not None else ("BREAK" if c1_off else "UNRESOLVED")
    return levels, dup


def signals_of(levels):
    """-> sorted list of (rule, bar, L, stop) for every signal the machine found."""
    out = []
    for lv in levels:
        for rule, key in (("C1", "c1"), ("C2", "c2")):
            if lv[key] is not None:
                out.append((rule, int(lv[key]["j"]), round(lv["L"], 8), round(lv[key]["stop"], 8)))
    return sorted(out)


# ------------------------------------------------------------------------------------------------- the trade
def walk_stop(fx, ks, stops, hold):
    """H107's `walk` line for line, with the stop handed in (R = entry - stop). The long decided at the close of each
    bar in `ks` (bars k+1 .. k+hold must exist). -> dict of arrays as h107.walk."""
    o, h, l, c = fx["o"], fx["h"], fx["l"], fx["c"]
    ks = np.asarray(ks, int)
    m = len(ks)
    out = {k: np.full(m, np.nan) for k in ("r", "pct", "entry", "stop")}
    out["xbar"], out["how"] = np.full(m, -1, int), np.full(m, -1, int)
    if not m:
        return out
    J = np.arange(hold)
    k = ks
    P = o[k + 1]
    S = np.asarray(stops, float)
    R = P - S
    T1, T2 = P + R, P + 2 * R
    idx = k[:, None] + 1 + J[None, :]
    L, H, O, C = l[idx], h[idx], o[idx], c[idx]
    rows = np.arange(m)

    def first(mask):
        return np.where(mask.any(1), mask.argmax(1), hold)
    js = first(L <= S[:, None])                                    # the stop is looked at first in a bar
    j1 = first(H >= T1[:, None])
    A = (js < hold) & (js <= j1)                                   # stopped before (or in the bar of) Target 1
    Bm = (~A) & (j1 < hold)
    fillA = np.minimum(O[rows, np.minimum(js, hold - 1)], S)       # at the stop, or at the open below it
    after = J[None, :] > j1[:, None]                               # stop at the entry from the bar after T1
    jb = first((L <= P[:, None]) & after)
    j2 = first((H >= T2[:, None]) & (J[None, :] >= j1[:, None]))
    same = j2 == j1
    be_first = (~same) & (jb < hold) & (jb <= j2)
    t2_first = (~same) & (~be_first) & (j2 < hold)
    restX = np.where(same | t2_first, T2, np.where(be_first, np.minimum(O[rows, np.minimum(jb, hold - 1)], P), C[:, -1]))
    restJ = np.where(same, j1, np.where(be_first, jb, np.where(t2_first, j2, hold - 1)))
    Xfull = np.where(A, fillA, C[:, -1])
    gross = np.where(Bm, 0.5 * (T1 - P) + 0.5 * (restX - P), Xfull - P)
    fees = FEE * np.where(Bm, P + 0.5 * T1 + 0.5 * restX, P + Xfull)
    out["r"] = (gross - fees) / R
    out["pct"] = (gross - fees) / P
    out["xbar"] = k + 1 + np.where(A, js, np.where(Bm, restJ, hold - 1))
    out["how"] = np.where(A, 0, np.where(Bm, np.where(be_first, 1, np.where(same | t2_first, 2, 3)), 4))
    out["entry"], out["stop"] = P, S
    return out


def walk_loop_stop(fx, k, stop0, hold):
    """The same trade, bar by bar (a cross-check of `walk_stop`). -> net R."""
    o, h, l, c = fx["o"], fx["h"], fx["l"], fx["c"]
    P = o[k + 1]
    R = P - stop0
    stop, T1, T2, q, got, fees = stop0, P + R, P + 2 * R, 1.0, 0.0, FEE * P
    t1 = False
    for j in range(k + 1, k + 1 + hold):
        if l[j] <= stop:
            x = min(o[j], stop)
            got += q * (x - P)
            fees += FEE * q * x
            return (got - fees) / R
        new_t1 = False
        if not t1 and h[j] >= T1:
            got += 0.5 * (T1 - P)
            fees += FEE * 0.5 * T1
            q, t1, new_t1 = 0.5, True, True
        if t1 and h[j] >= T2:
            got += q * (T2 - P)
            fees += FEE * q * T2
            return (got - fees) / R
        if new_t1:
            stop = P
    x = c[k + hold]
    got += q * (x - P)
    fees += FEE * q * x
    return (got - fees) / R


def trades_of(coin, fx, levels, rule, k1, p=REG):
    """One trade per level per rule; one at a time per rule and coin; a trade must end by bar k1.
    -> (rows, counts of signals not taken)."""
    key = rule.lower()
    hold = p["hold"]
    t, o, h = fx["t"], fx["o"], fx["h"]
    sig = sorted([lv for lv in levels if lv[key] is not None], key=lambda lv: lv[key]["j"])
    skipped = {"past_the_cut": 0, "entry_at_or_under_stop": 0, "a_trade_was_open": 0}
    rows, last = [], -1
    for lv in sig:
        j, stop = lv[key]["j"], lv[key]["stop"]
        if j + hold > k1:
            skipped["past_the_cut"] += 1
            continue
        if not o[j + 1] > stop:
            skipped["entry_at_or_under_stop"] += 1
            continue
        if j < last:
            skipped["a_trade_was_open"] += 1
            continue
        w = walk_stop(fx, [j], [stop], hold)
        last = int(w["xbar"][0])
        P, L, b, f = float(w["entry"][0]), lv["L"], lv["b"], lv["f"]
        Hh = float(np.max(h[b + 1:f]))                               # the bounce high before the retest (hindsight)
        Z = (1.0 + p["zone"]) * L
        half = 0.5 * (Hh + Z)
        rows.append({
            "coin": coin, "rule": rule, "k": int(j), "time": str(t[j])[:16], "month": h107.month_of(t[j]),
            "year": int(t[j].year), "half": 1 if t[j] < pd.Timestamp(MID, tz="UTC") else 2,
            "r": float(w["r"][0]), "pct": float(w["pct"][0]), "how": int(w["how"][0]), "entry": P, "stop": float(stop),
            "exit_time": str(t[last])[:16], "L": L, "low_time": str(t[b])[:16], "trigger_time": str(t[lv["k"]])[:16],
            "touch_time": str(t[f])[:16], "retest_low": float(lv[key]["low"]),
            "stop_pct": float((P - stop) / P * 100), "fee_r": float(2 * FEE * P / (P - stop)),
            "hours_low_to_entry": float((t[j] - t[b]) / pd.Timedelta(hours=1)),
            # Part 3: arithmetic on prices, not a book
            "bounce_high": Hh, "zone_top": float(Z), "fall_pct": float((Hh - Z) / Hh * 100),
            "short_from_high_pct": float(((Hh - Z) / Hh - 2 * FEE) * 100),
            "short_from_half_pct": float(((half - Z) / half - 2 * FEE) * 100),
            "zone_to_entry_pct": float((Z - P) / Z * 100)})
    return rows, skipped


# ------------------------------------------------------------------------------------------------- statistics
def qs(v):
    v = np.asarray([x for x in v if x is not None and np.isfinite(x)], float)
    if not len(v):
        return {"n": 0}
    return {"n": int(len(v)), "median": float(np.median(v)), "q1": float(np.percentile(v, 25)),
            "q3": float(np.percentile(v, 75)), "min": float(v.min()), "max": float(v.max()), "mean": float(v.mean()),
            "share_above_zero": float((v > 0).mean() * 100)}


def cells(rows, months, m1, m2, D, D1, D2):
    out = {}
    parts = {"all": (rows, months, D), "h1": ([r for r in rows if r["half"] == 1], m1, D1),
             "h2": ([r for r in rows if r["half"] == 2], m2, D2)}
    for pname, (pr, ms, Dp) in parts.items():
        for cname, cr in (("pooled", pr), ("BTC", [r for r in pr if r["coin"] == "BTCUSDT"]),
                          ("ETH", [r for r in pr if r["coin"] == "ETHUSDT"])):
            s = h107.summary(cr)
            s["boot_r"] = h107.boot(cr, ms, Dp, "r")
            if cr:
                s["median_stop_pct"] = float(np.median([r["stop_pct"] for r in cr]))
                s["median_fee_r"] = float(np.median([r["fee_r"] for r in cr]))
                s["mean_drift_excess_pct"] = float(np.nanmean([r["pct"] * 100 - r["drift_pct"] for r in cr]))
            out["%s_%s" % (cname, pname)] = s
    return out


def drift(fx, k0, k1, hold, months_needed):
    """Mean net percent of a plain 48-hour long (next open to the close `hold` bars later, less fees) entered at every
    bar of each needed calendar month."""
    t, o, c = fx["t"], fx["o"], fx["c"]
    ks = np.arange(k0, k1 - hold + 1)
    mo = np.asarray(t[ks].year * 100 + t[ks].month)
    out = {}
    for m_ in months_needed:
        sel = ks[mo == m_]
        if len(sel):
            P, X = o[sel + 1], c[sel + hold]
            out[int(m_)] = float(np.mean((X - P - FEE * (P + X)) / P) * 100)
    return out


def verdict_of(cell, p_holm):
    pa, h1, h2 = cell["pooled_all"], cell["pooled_h1"], cell["pooled_h2"]
    chk = {"n_all>=60": pa["n"] >= MIN_ALL, "n_h1>=20": h1["n"] >= MIN_HALF, "n_h2>=20": h2["n"] >= MIN_HALF,
           "mean_r_h1>0": h1["n"] > 0 and h1["mean_r"] > 0, "mean_r_h2>0": h2["n"] > 0 and h2["mean_r"] > 0,
           "mean_r_all>0": pa["n"] > 0 and pa["mean_r"] > 0, "holm_p<0.05": bool(p_holm < ALPHA)}
    enough = chk["n_all>=60"] and chk["n_h1>=20"] and chk["n_h2>=20"]
    return chk, ("PASS" if all(chk.values()) else ("TOO FEW TRADES TO JUDGE (no pass)" if not enough else "FAIL"))


# ------------------------------------------------------------------------------------------------- Part 1
def part1_rows(coin, fx, levels, k1):
    """One row per level seen in full (trigger at least 34 days before the cut)."""
    t, h, l, c = fx["t"], fx["h"], fx["l"], fx["c"]
    last_ok = pd.Timestamp(CUT, tz="UTC") - pd.Timedelta(days=FULL_VIEW_DAYS)
    rows, late = [], 0
    for lv in levels:
        k, L, b, f = lv["k"], lv["L"], lv["b"], lv["f"]
        if t[k] > last_ok:
            late += 1
            continue
        row = {"coin": coin, "trigger_time": str(t[k])[:16], "low_time": str(t[b])[:16], "L": L,
               "half": 1 if t[k] < pd.Timestamp(MID, tz="UTC") else 2, "year": int(t[k].year), "state": lv["state"],
               "outcome": lv["outcome"], "c1": lv["c1"] is not None, "c2": lv["c2"] is not None,
               "swept": lv["s"] is not None}
        if f is not None:
            cf = c[f]
            row.update({"touch_time": str(t[f])[:16], "hours_low_to_touch": float((t[f] - t[b]) / pd.Timedelta(hours=1)),
                        "hours_trigger_to_touch": float((t[f] - t[k]) / pd.Timedelta(hours=1)),
                        "bounce_high_pct": float((np.max(h[b + 1:f]) / L - 1) * 100),
                        "touch_close_vs_L_pct": float((cf / L - 1) * 100)})
            for hrs in (24, 48, 96):
                q = min(f + hrs * 4, k1)
                row["ret_%dh" % hrs] = float((c[q] / cf - 1) * 100)
                row["close_below_L_%dh" % hrs] = bool(np.any(c[f:q + 1] < L))
            q = min(f + 384, k1)
            row["low_96h_vs_L_pct"] = float((np.min(l[f:q + 1]) / L - 1) * 100)
            row["high_96h_vs_L_pct"] = float((np.max(h[f:q + 1]) / L - 1) * 100)
        rows.append(row)
    return rows, late


def part1_table(rows):
    n = len(rows)
    if not n:
        return {"levels": 0}
    st = lambda s: [r for r in rows if r["state"] == s]            # noqa: E731
    ret = st("retest")
    hold = [r for r in ret if r["outcome"] == "HOLD"]
    brk = [r for r in ret if r["outcome"] == "BREAK"]
    armed = [r for r in rows if r["state"] in ("armed_no_touch", "retest")]

    def fwd(rr):
        o = {"n": len(rr)}
        for key in ("ret_24h", "ret_48h", "ret_96h", "low_96h_vs_L_pct", "high_96h_vs_L_pct", "hours_low_to_touch",
                    "bounce_high_pct"):
            o[key] = qs([r.get(key) for r in rr])
        for hrs in (24, 48, 96):
            o["close_below_L_within_%dh_pct" % hrs] = (float(np.mean([r["close_below_L_%dh" % hrs] for r in rr]) * 100)
                                                       if rr else None)
        return o
    return {"levels": n, "undercut_before_bounce": len(st("undercut")), "no_5pct_bounce_in_30d": len(st("no_bounce")),
            "armed": len(armed), "armed_not_retested": len(st("armed_no_touch")), "retested": len(ret),
            "hold": len(hold), "hold_with_wick_below_L": len([r for r in hold if r["swept"]]),
            "break": len(brk), "break_reclaimed_24h": len([r for r in brk if r["c2"]]),
            "unresolved": len([r for r in ret if r["outcome"] == "UNRESOLVED"]),
            "c1_signals": len([r for r in ret if r["c1"]]), "c2_signals": len([r for r in ret if r["c2"]]),
            "all_retests": fwd(ret), "hold_retests": fwd(hold), "break_retests": fwd(brk)}


# ------------------------------------------------------------------------------------------------- guards
def lookahead_test(coin, ddir, fx, k0, k1, levels, n_random=40, seed=SEED):
    """H107's readings AND the level machine recomputed on data cut at bar j, for every signal bar and some random
    bars: the set of signals up to j must equal the full run's."""
    df, fund = h107.load(coin, ddir, end=CUT)
    full = signals_of(levels)
    rng = np.random.default_rng(seed)
    bars = sorted(set(s[1] for s in full)) + [int(x) for x in rng.integers(k0, k1 + 1, n_random)]
    bad = []
    for j in bars:
        g = h107.features(df.iloc[:j + 1], fund.loc[:fx["t"][j] + pd.Timedelta(minutes=15)])
        lev_g, _ = machine(g, k_from=k0)
        want = [s for s in full if s[1] <= j]
        got = signals_of(lev_g)
        if got != want:
            bad.append(j)
    return {"bars_checked": len(bars), "signal_bars": len(set(s[1] for s in full)), "n_mismatch": len(bad),
            "mismatches": bad[:20]}


# ------------------------------------------------------------------------------------------------- history run
def run_history(ddir, log=print):
    t0 = time.time()
    res = {"registered": REG, "start": START, "cut": CUT, "mid": MID, "fee_side": FEE,
           "bootstrap": {"draws": B, "seed": SEED}, "files": {}, "rules": {}, "part1": {}, "part3": {}}
    for c_ in COINS:
        for suf in ("_15m.csv", "_funding.csv"):
            pth = os.path.join(ddir, c_.lower() + suf)
            res["files"][os.path.basename(pth)] = h107.md5(pth)
    months = h107.all_months(START, CUT)
    m1 = [m_ for m_ in months if m_ <= 202306]
    m2 = [m_ for m_ in months if m_ >= 202306]
    rng = np.random.default_rng(SEED)
    D = rng.integers(0, len(months), size=(B, len(months)))
    D1 = rng.integers(0, len(m1), size=(B, len(m1)))
    D2 = rng.integers(0, len(m2), size=(B, len(m2)))
    frames, lev, p1rows, trig = {}, {}, [], {}
    for c_ in COINS:
        fx, k0, k1 = h107.coin_frame(c_, ddir)
        assert str(fx["t"][-1])[:16] <= CUT, "holdout read"
        frames[c_] = (fx, k0, k1)
        lev[c_], dup = machine(fx, k_from=k0)
        trig[c_] = {"rule_A_onsets": int(np.sum(fx["A"][k0:])), "same_low_again": int(dup), "levels": len(lev[c_])}
        rr, late = part1_rows(c_, fx, lev[c_], k1)
        trig[c_]["levels_too_late_for_part1"] = late
        p1rows += rr
        log("%s: bars %s .. %s, %d onsets, %d levels" % (c_, str(fx["t"][0])[:16], str(fx["t"][k1])[:16],
                                                         trig[c_]["rule_A_onsets"], len(lev[c_])))
    res["part1"] = {"counts": trig, "levels": p1rows, "tables": {}}
    for pname, pr in (("all", p1rows), ("h1", [r for r in p1rows if r["half"] == 1]),
                      ("h2", [r for r in p1rows if r["half"] == 2])):
        for cname, cr in (("pooled", pr), ("BTC", [r for r in pr if r["coin"] == "BTCUSDT"]),
                          ("ETH", [r for r in pr if r["coin"] == "ETHUSDT"])):
            res["part1"]["tables"]["%s_%s" % (cname, pname)] = part1_table(cr)
    by_year = {}
    for r in p1rows:
        y = by_year.setdefault(r["year"], {"levels": 0, "retested": 0, "hold": 0, "break": 0})
        y["levels"] += 1
        y["retested"] += r["state"] == "retest"
        y["hold"] += r["outcome"] == "HOLD"
        y["break"] += r["outcome"] == "BREAK"
    res["part1"]["by_year"] = by_year
    pvals = {}
    for rule in RULES:
        rows, skipped, checks = [], {}, {}
        for c_ in COINS:
            fx, k0, k1 = frames[c_]
            rr, sk = trades_of(c_, fx, lev[c_], rule, k1)
            skipped[c_] = sk
            d1 = [abs(walk_loop_stop(fx, r["k"], r["stop"], REG["hold"]) - r["r"]) for r in rr]
            checks[c_] = float(max(d1)) if d1 else 0.0
            dr = drift(fx, k0, k1, REG["hold"], sorted(set(r["month"] for r in rr)))
            for r in rr:
                r["drift_pct"] = dr.get(r["month"], np.nan)
            rows += rr
        cell = cells(rows, months, m1, m2, D, D1, D2)
        pvals[rule] = cell["pooled_all"]["boot_r"]["p"] if cell["pooled_all"].get("boot_r") else 1.0
        yr = {}
        for r in rows:
            y = yr.setdefault(r["year"], {"n": 0, "sum_r": 0.0})
            y["n"] += 1
            y["sum_r"] += r["r"]
        res["rules"][rule] = {"cells": cell, "signals_not_taken": skipped, "walk_crosscheck_max_abs_diff_r": checks,
                              "by_year": yr, "trades": rows}
        p3 = {}
        for pname, pr in (("all", rows), ("h1", [r for r in rows if r["half"] == 1]),
                          ("h2", [r for r in rows if r["half"] == 2])):
            p3[pname] = dict((key, qs([r[key] for r in pr])) for key in
                             ("fall_pct", "short_from_high_pct", "short_from_half_pct", "zone_to_entry_pct"))
            p3[pname]["long_pct"] = qs([r["pct"] * 100 for r in pr])
            p3[pname]["long_r"] = qs([r["r"] for r in pr])
        res["part3"][rule] = p3
    adj = h107.holm([pvals[r] for r in RULES])
    for i, rule in enumerate(RULES):
        chk, v = verdict_of(res["rules"][rule]["cells"], adj[i])
        res["rules"][rule].update({"p_raw": float(pvals[rule]), "p_holm": float(adj[i]), "checks": chk, "verdict": v})
    # guard (ii) against H107's own walk, on every bar with a signal: hand walk_stop H107's stop
    res["walk_vs_h107"] = {}
    for c_ in COINS:
        fx, k0, k1 = frames[c_]
        ks = np.array(sorted(set(s[1] for s in signals_of(lev[c_]) if s[1] + REG["hold"] <= k1)), int)
        ks = ks[np.isfinite(fx["atr1h"][ks]) & (fx["atr1h"][ks] > 0)]
        if len(ks):
            a = h107.walk(fx, ks, REG["hold"])
            b_ = walk_stop(fx, ks, fx["o"][ks + 1] - h107.STOP_ATR * fx["atr1h"][ks], REG["hold"])
            res["walk_vs_h107"][c_] = {"bars": int(len(ks)), "max_abs_diff_r": float(np.max(np.abs(a["r"] - b_["r"]))),
                                       "same_exit_bars": bool(np.all(a["xbar"] == b_["xbar"]))}
    res["lookahead_test"] = {}
    for c_ in COINS:
        fx, k0, k1 = frames[c_]
        res["lookahead_test"][c_] = lookahead_test(c_, ddir, fx, k0, k1, lev[c_])
        log("%s look-ahead: %s" % (c_, res["lookahead_test"][c_]))
    res["descriptive_sensitivity"] = sensitivity(frames)
    res["posthoc_not_registered"] = posthoc(p1rows, dict((r_, res["rules"][r_]["trades"]) for r_ in RULES))
    res["seconds"] = round(time.time() - t0, 1)
    return res


def posthoc(p1rows, trades):
    """NOT REGISTERED, added after the first run; descriptive only. The retests and the trades split by how long after
    the low the first touch came (the live case would be a touch more than three days after the low)."""
    bands = (("under 24h", 0, 24), ("24h to 7 days", 24, 168), ("over 7 days", 168, 1e9))
    out = {}
    for name, lo, hi in bands:
        rt = [r for r in p1rows if r["state"] == "retest" and lo <= r["hours_low_to_touch"] < hi]
        cell = {"retests": len(rt), "hold": sum(r["outcome"] == "HOLD" for r in rt),
                "break": sum(r["outcome"] == "BREAK" for r in rt),
                "close_below_L_within_96h": sum(r["close_below_L_96h"] for r in rt),
                "ret_96h": qs([r["ret_96h"] for r in rt])}
        for rule, rows in trades.items():
            rr = []
            for r in rows:
                hrs = (pd.Timestamp(r["touch_time"]) - pd.Timestamp(r["low_time"])) / pd.Timedelta(hours=1)
                if lo <= hrs < hi:
                    rr.append(r)
            cell[rule] = dict((x, v) for x, v in h107.summary(rr).items() if x in ("n", "won_pct", "mean_r", "sum_r"))
            for half in (1, 2):
                hh = [r for r in rr if r["half"] == half]
                cell["%s_h%d" % (rule, half)] = dict((x, v) for x, v in h107.summary(hh).items()
                                                     if x in ("n", "won_pct", "mean_r", "sum_r"))
        out[name] = cell
    return out


def sensitivity(frames):
    """Descriptive only, decides nothing: one setting moved at a time around the registered rules."""
    variants = [("zone 1.0%", {"zone": 0.010}), ("zone 2.5%", {"zone": 0.025}), ("first bounce 3%", {"bounce": 0.03}),
                ("first bounce 8%", {"bounce": 0.08}), ("C1 turn 0.5 ATR", {"c1_atr": 0.5}),
                ("C1 turn 2.0 ATR", {"c1_atr": 2.0}), ("stop pad 0.25 ATR", {"pad_atr": 0.25}),
                ("stop pad 1.0 ATR", {"pad_atr": 1.0}), ("C2 reclaim 6h", {"c2_bars": 24}),
                ("C2 reclaim 48h", {"c2_bars": 192}), ("level life 14 days", {"life_days": 14}),
                ("level life 60 days", {"life_days": 60})]
    out = {}
    for name, ch in variants:
        p = dict(REG, **ch)
        for rule in RULES:
            rows = []
            for c_ in COINS:
                fx, k0, k1 = frames[c_]
                lv, _ = machine(fx, p, k_from=k0)
                rr, _ = trades_of(c_, fx, lv, rule, k1, p)
                rows += rr
            out["%s | %s" % (rule, name)] = dict((pn, dict((x, v) for x, v in h107.summary(pr).items()
                                                           if x in ("n", "won_pct", "mean_r", "sum_r")))
                                                 for pn, pr in (("all", rows), ("h1", [r for r in rows if r["half"] == 1]),
                                                                ("h2", [r for r in rows if r["half"] == 2])))
    return out


# ------------------------------------------------------------------------------------------------- Part 4 (descriptive)
def run_event(ddir):
    """The level machine on the levels made from 2026-11-19 on. States and prices only; no trade result is computed."""
    out = {}
    for c_ in COINS:
        df, fund = h107.load(c_, ddir, start=EVENT_LOAD)
        fx = h107.features(df, fund)
        t = fx["t"]
        n = len(t)
        k0 = int(t.searchsorted(pd.Timestamp(EVENT_FROM, tz="UTC")))
        levels, dup = machine(fx, k_from=k0)
        atr = float(fx["atr1h"][-1])
        rows = []
        for lv in levels:
            L, k, b = lv["L"], lv["k"], lv["b"]
            Z = (1 + REG["zone"]) * L
            row = {"L": L, "low_bar_open_utc": str(t[b])[:16], "trigger_close_utc": str(t[k] + pd.Timedelta(minutes=15))[:16],
                   "state_at_last_bar": lv["state"], "arm_price_5pct_above_L": 1.05 * L,
                   "armed_at_bar_open_utc": None if lv["a"] is None else str(t[lv["a"]])[:16],
                   "highest_high_since_low": float(np.max(fx["h"][b + 1:])),
                   "lowest_low_since_trigger": float(np.min(fx["l"][k + 1:])) if k + 1 < n else None,
                   "retest_zone_top": Z, "retest_zone": "a 15m low at or below %.2f" % Z,
                   "first_touch_bar_open_utc": None if lv["f"] is None else str(t[lv["f"]])[:16],
                   "c1_signal_bar_open_utc": None if lv["c1"] is None else str(t[lv["c1"]["j"]])[:16],
                   "c2_signal_bar_open_utc": None if lv["c2"] is None else str(t[lv["c2"]["j"]])[:16],
                   "live_until_close_utc": str(t[k] + pd.Timedelta(days=REG["life_days"]) + pd.Timedelta(minutes=15))[:16],
                   "last_signal_bar_opens_utc": str(t[k] + pd.Timedelta(days=REG["life_days"]))[:16],
                   "atr1h_at_last_bar": atr, "examples_at_that_atr": {}}
            ex = row["examples_at_that_atr"]

            def fill(entry, stop):
                r = entry - stop
                return {"entry": entry, "stop": stop, "r_distance": r, "stop_pct_of_entry": r / entry * 100,
                        "target_1": entry + r, "target_2": entry + 2 * r, "round_trip_fee_in_r": 2 * FEE * entry / r}
            ex["C1, retest low exactly at the zone top"] = dict(
                fill(Z + REG["c1_atr"] * atr, L - REG["pad_atr"] * atr), needs="a 15m close at or above %.2f" % (Z + atr))
            ex["C1, retest low exactly at L"] = dict(
                fill(L + REG["c1_atr"] * atr, L - REG["pad_atr"] * atr), needs="a 15m close at or above %.2f, and no "
                "15m close below %.2f before it" % (L + atr, L))
            sw = 0.99 * L
            ex["C2, sweep to 1% under L, reclaim close just above L"] = dict(
                fill(L, sw - REG["pad_atr"] * atr), needs="a 15m low below %.2f, then within 24 hours a 15m close above "
                "%.2f" % (L, L), sweep_low=sw)
            rows.append(row)
        out[c_] = {"last_bar_open_utc": str(t[-1])[:16], "last_close": float(fx["c"][-1]), "atr1h_at_last_bar": atr,
                   "rule_A_onsets_since_%s" % EVENT_FROM[:10]: int(np.sum(fx["A"][k0:])), "same_low_again": int(dup),
                   "levels": rows}
    return out


# ------------------------------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    ap.add_argument("--event", action="store_true", help="only Part 4: the live levels (descriptive, no result)")
    a = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    if a.event:
        ev = run_event(a.data_dir)
        with open(os.path.join(OUT, "event.json"), "w") as fh:
            json.dump(ev, fh, indent=1)
        print(json.dumps(ev, indent=1))
        return
    res = run_history(a.data_dir)
    with open(os.path.join(OUT, "results.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    print(json.dumps(res["part1"]["counts"]))
    for rule in RULES:
        r = res["rules"][rule]
        print(rule, r["verdict"], "p", round(r["p_raw"], 4), "holm", round(r["p_holm"], 4), r["checks"])
        for k, v in r["cells"].items():
            print("  ", k, dict((x, (round(y, 3) if isinstance(y, float) else y)) for x, y in v.items()
                                if x in ("n", "won_pct", "mean_r", "sum_r")), v.get("boot_r"))
    print("lookahead", res["lookahead_test"], "walk", res["walk_vs_h107"],
          {r: res["rules"][r]["walk_crosscheck_max_abs_diff_r"] for r in RULES}, "seconds", res["seconds"])


if __name__ == "__main__":
    main()
