# -*- coding: utf-8 -*-
"""H114: USDJPY in the Setups book (b_targets) with its own stop at 3.0 barriers (PRIMARY) and 4.0 (descriptive)
against the current 2.0, and the current rule's own record per period (the "leave it out" read). Research only;
registered in research/HYPOTHESES.md before this file existed. Every book is the engine's own shadows.run; the stop is
passed in the cfg dict (stop_units). Reads the evidence store and the cached fits; changes nothing.

    py -3 -X utf8 research/h114_usdjpy_stop.py --fits-dir fits_today

Writes research/out/h114_usdjpy_stop/results.json and report.md. If a file reading.md is in that folder, its text is
placed in the report under "What it means" (written by hand after the run; the tables come from the numbers).
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

from engine15 import data, live, shadows  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "h114_usdjpy_stop")
GROUP, ASSET = "fx", "USDJPY"
END = "2026-11-24 04:30"                                          # registered: the last stored session at or before this
MID, HOLDOUT, FORWARD = "2023-06-08", "2025-11-11", "2026-11-11"
BOOKS = (("s2", 2.0), ("s3", 3.0), ("s4", 4.0))                   # current, PRIMARY, secondary (descriptive)
CUR, PRIMARY = "s2", "s3"
PERIODS = ("all", "h1", "h2", "mid", "holdout", "forward")        # mid = h2 before the holdout (descriptive)
LEGS = ("h1", "h2", "holdout")                                    # the periods of the PASS condition, leg (a)
LOOK = 96                                                         # sessions after a stop-out: 24 hours of trading
START = shadows.START_EQUITY


# =====================================================================================
# pure read-outs (tested in tests/test_h114.py)
# =====================================================================================
def fall_pct(eq, base):
    """The largest peak-to-trough fall of the marked equity inside a period, in percent (0 or negative). The running
    peak starts at `base`, the equity the period starts with."""
    e = np.asarray(eq, dtype=float)
    e = np.concatenate([[float(base)], e[np.isfinite(e)]])
    return float(np.min(e / np.maximum.accumulate(e) - 1.0) * 100.0)


def ratio(p):
    """Net percent over the size of the worst fall in percent; inf for a gain with no fall; None when undefined."""
    if p["fall_pct"] < 0:
        return p["net_pct"] / abs(p["fall_pct"])
    return float("inf") if p["net_pct"] > 0 else None


def period_stats(book, a, z, lo):
    """Read-outs 1 to 3 of one book over bars a .. z-1 (trades by entry bar)."""
    tr = book["trades"]
    t = tr[(tr.i_in >= a) & (tr.i_in < z)]
    r = t.r_mult.values.astype(float)
    r = r[np.isfinite(r)]
    eq = book["equity"]
    base = float(eq[a - 1]) if a > lo and np.isfinite(eq[a - 1]) else float(START)
    net = float(eq[z - 1] - base)
    out = {"trades": int(len(t)), "won_pct": float((t.pnl_usd > 0).mean() * 100) if len(t) else None,
           "sum_r": float(r.sum()), "mean_r": float(r.mean()) if len(r) else None,
           # added after the first run, not in the registration: a rough yardstick for chance. Two standard errors
           # of the sum of R if the trades were independent draws (they are not quite): 2 x sd x sqrt(n).
           "r_sd": float(r.std(ddof=1)) if len(r) > 1 else None,
           "sum_r_band": float(2.0 * r.std(ddof=1) * np.sqrt(len(r))) if len(r) > 1 else None,
           "net_usd": net, "net_pct": net / base * 100.0, "base_usd": base,
           "fees_usd": float(t.fees_usd.sum()), "closed_pnl_usd": float(t.pnl_usd.sum()),
           "fall_pct": fall_pct(eq[a:z], base), "flat_pct": float((book["held"][a:z] == 0).mean() * 100),
           "exits": dict((str(k), int(v)) for k, v in t.why_out.value_counts().items())}
    rt = ratio(out)
    out["net_over_fall"] = None if rt is None or not np.isfinite(rt) else float(rt)
    return out


def stop_reversals(tr, high, low, a, z, look=LOOK):
    """Read-out 4. Trades entered in bars a .. z-1 that ended at the entry stop (exit word exactly "STOP"). Of those
    with `look` later bars on file: after how many did price trade back at the ENTRY within the next `look` bars
    (`back`), and after how many did it instead go a further full stop distance beyond the stop (`further`)?"""
    n = len(high)
    rows = tr[(tr.why_out == "STOP") & (tr.i_in >= a) & (tr.i_in < z)]
    out = {"stopouts": int(len(rows)), "judged": 0, "back": 0, "further": 0, "both": 0, "neither": 0, "back_rows": []}
    for t in rows.itertuples():
        i, side, entry, stop = int(t.i_out), int(t.side), float(t.p_in), float(t.stop0)
        if i + look > n - 1:
            continue                                               # fewer than `look` bars follow: not judged
        hi_w, lo_w = high[i + 1:i + 1 + look], low[i + 1:i + 1 + look]
        beyond = stop - side * abs(entry - stop)                   # one more stop distance past the stop
        if side == 1:
            back_at, far = hi_w >= entry, lo_w <= beyond
        else:
            back_at, far = lo_w <= entry, hi_w >= beyond
        b, f = bool(back_at.any()), bool(far.any())
        out["judged"] += 1
        out["back"] += int(b)
        out["further"] += int(f)
        out["both"] += int(b and f)
        out["neither"] += int(not b and not f)
        if b:
            out["back_rows"].append((int(t.i_in), i + 1 + int(np.argmax(back_at)), side, entry, stop))
    j = out["judged"]
    out["back_pct"] = 100.0 * out["back"] / j if j else None
    out["further_pct"] = 100.0 * out["further"] / j if j else None
    return out


def sat_through(back_rows, high, low, units_now, units_wide):
    """Read-out 5. Of the stop-outs that were back at the entry (rows from stop_reversals), how many would a stop
    `units_wide` barriers from the SAME entry have sat through: from the entry bar to the bar of the return, price
    never reached it (lows for a long, highs for a short; the return bar included)."""
    kept = 0
    for i_in, j, side, entry, stop in back_rows:
        level = entry - side * abs(entry - stop) * units_wide / units_now
        if side == 1:
            kept += int(low[i_in:j + 1].min() > level)
        else:
            kept += int(high[i_in:j + 1].max() < level)
    return {"of": len(back_rows), "kept": kept, "kept_pct": 100.0 * kept / len(back_rows) if back_rows else None}


def sizing(tr, cfg):
    """Read-out 6, the size: how often the 2% rule ran into the 1x floor or the market's cap, and typical values."""
    if not len(tr):
        return {"trades": 0}
    dist = (tr.p_in - tr.stop0).abs().values.astype(float)
    price = tr.p_in.values.astype(float)
    cap = float(cfg.get("leverage_cap", 1.0) or 1.0)
    raw = cfg.get("risk_per_trade", 0.02) / (dist / price)
    stops = tr[tr.why_out == "STOP"]
    return {"trades": int(len(tr)), "at_floor_pct": float((raw < 1.0).mean() * 100), "at_cap_pct": float((raw > cap).mean() * 100),
            "stop_pct_median": float(np.median(dist / price * 100)), "stop_pct_min": float((dist / price * 100).min()),
            "stop_pct_max": float((dist / price * 100).max()), "leverage_median": float(np.median(np.clip(raw, 1.0, cap))),
            "stop_exit_mean_r": float(stops.r_mult.mean()) if len(stops) else None,
            "worst_r": float(tr.r_mult.min()), "hold_bars_median": float(np.median((tr.i_out - tr.i_in).values))}


def target_facts(tr, tgt):
    """Read-out 6, the targets: plan_targets recomputed for each trade from its entry, its stop and the readings row of
    the deciding close (the bar before the fill). -> where Target 1 and 2 came from, their distances, mismatches."""
    src1, src2, d1, d2, r1, r2, bad = {}, {}, [], [], [], [], 0
    for t in tr.itertuples():
        row = tgt.iloc[int(t.i_in) - 1] if len(tgt.columns) else pd.Series(dtype=float)
        p = live.plan_targets(int(t.side), float(t.p_in), float(t.stop0), row)
        if not p or t.target_1 is None or t.target_1 != t.target_1:
            bad += 1
            continue
        if abs(p["target_1"] - float(t.target_1)) > 1e-9 or abs(p["target_2"] - float(t.target_2)) > 1e-9:
            bad += 1
            continue
        b1, b2 = p["target_1_basis"], p["target_2_basis"]
        k1 = "fibonacci" if b1.startswith("Fibonacci") else "day_travel" if b1.startswith("a typical day") else "1.5R"
        k2 = "fibonacci" if b2.startswith("Fibonacci") else "2R_or_1.5xT1"
        src1[k1] = src1.get(k1, 0) + 1
        src2[k2] = src2.get(k2, 0) + 1
        risk = abs(float(t.p_in) - float(t.stop0))
        d1.append(abs(p["target_1"] - t.p_in) / t.p_in * 100)
        d2.append(abs(p["target_2"] - t.p_in) / t.p_in * 100)
        r1.append(abs(p["target_1"] - t.p_in) / risk)
        r2.append(abs(p["target_2"] - t.p_in) / risk)
    med = lambda x: float(np.median(x)) if x else None            # noqa: E731
    return {"t1_source": src1, "t2_source": src2, "t1_pct_median": med(d1), "t2_pct_median": med(d2),
            "t1_in_r_median": med(r1), "t2_in_r_median": med(r2), "not_reproduced": bad}


def leg(c, w):
    """Leg (a) of the PASS condition in one period: c = the current rule's read-outs, w = the wider stop's.
    Above zero net: net / worst fall higher than the current rule's. At or below zero (the registered guard): the net
    percent is higher AND the worst fall is not deeper."""
    rw, rc = ratio(w), ratio(c)
    bare = bool(rw is not None and rc is not None and rw > rc)     # the brief's wording, with no guard
    if w["net_pct"] > 0:
        return {"holds": bare, "by": "ratio", "bare_ratio_higher": bare}
    ok = w["net_pct"] > c["net_pct"] and w["fall_pct"] >= c["fall_pct"]
    return {"holds": bool(ok), "by": "guard", "bare_ratio_higher": bare}


def verdict(cur, wide):
    """The registered PASS condition for a wider stop against the current rule ({period: read-outs} each)."""
    legs = dict((p, leg(cur[p], wide[p])) for p in LEGS)
    net_all = bool(wide["all"]["net_usd"] > cur["all"]["net_usd"])
    return {"legs": legs, "net_all_higher": net_all, "passes": bool(all(v["holds"] for v in legs.values()) and net_all),
            # the same verdict with the brief's bare ratio in every leg (no guard): shown so the guard can be judged
            "passes_bare_ratio": bool(all(v["bare_ratio_higher"] for v in legs.values()) and net_all)}


def leave_out(cur):
    """The descriptive read: is the current rule's sum of R at or below zero in h1 AND h2 AND the holdout?"""
    at = dict((p, bool(cur[p]["sum_r"] <= 0)) for p in LEGS)
    return {"at_or_below_zero": at, "proposal": bool(all(at.values()))}


def analyse(books, cfgs, px, lo, n, idx, tgt, times=None):
    """Every read-out from the three books. idx = {"mid", "holdout", "forward"} bar numbers."""
    spans = {"all": (lo, n), "h1": (lo, idx["mid"]), "h2": (idx["mid"], n), "mid": (idx["mid"], idx["holdout"]),
             "holdout": (idx["holdout"], n), "forward": (idx["forward"], n)}
    high, low = px["high"], px["low"]
    res = {"books": {}, "spans": dict((k, [int(a), int(z)]) for k, (a, z) in spans.items())}
    for name, units in BOOKS:
        b, tr = books[name], books[name]["trades"]
        out = {"stop_units": units, "periods": {}, "stops": {}}
        for p, (a, z) in spans.items():
            out["periods"][p] = period_stats(b, a, z, lo)
            sr = stop_reversals(tr, high, low, a, z)
            rows = sr.pop("back_rows")
            if name == CUR:                                        # read-out 5: the same entries under a wider stop
                sr["sat_through"] = dict((w, sat_through(rows, high, low, units, wu)) for w, wu in BOOKS if w != CUR)
            out["stops"][p] = sr
        out["sizing"] = sizing(tr, cfgs[name])
        out["targets"] = target_facts(tr, tgt)
        out["open_at_end"] = {1: "LONG", -1: "SHORT"}.get(int(b["state"].get("pos", 0)), "FLAT")
        if times is not None:
            f = tr[tr.i_in >= idx["forward"]]
            out["forward_trades"] = [{"t_in": str(times[int(t.i_in)])[:16], "t_out": str(times[int(t.i_out)])[:16],
                                      "side": int(t.side), "p_in": float(t.p_in), "why_in": str(t.why_in),
                                      "stop_pct": abs(float(t.p_in) - float(t.stop0)) / float(t.p_in) * 100,
                                      "why_out": str(t.why_out), "r": float(t.r_mult), "pnl_usd": float(t.pnl_usd)}
                                     for t in f.itertuples()]
        res["books"][name] = out
    cur = res["books"][CUR]["periods"]
    res["verdict"] = dict((name, verdict(cur, res["books"][name]["periods"])) for name, _u in BOOKS if name != CUR)
    res["passes"] = res["verdict"][PRIMARY]["passes"]
    res["leave_out"] = leave_out(cur)
    return res


# =====================================================================================
# the run on history
# =====================================================================================
def group_end():
    """The fx store's last session at or before END, as prep_cut wants it."""
    from engine15 import evcache
    st = evcache.AssetStore(os.path.join(evcache.CACHE_DIR, GROUP, ASSET))
    if not st.load():
        raise RuntimeError("no evidence store for %s/%s" % (GROUP, ASSET))
    full = pd.DatetimeIndex(pd.to_datetime(st.times_ms(), unit="ms", utc=True))
    k = int(full.searchsorted(pd.Timestamp(END, tz="UTC"), side="right"))
    return str(full[k - 1])[:16]


def run(fits_root, log=print):
    import h59_half_be as h59
    import h62_setups_wide_stop as h62
    t0 = time.time()
    lines = []

    def say(msg):
        lines.append(str(msg))
        log(msg)
    prep = h59.prep_cut(GROUP, [ASSET], os.path.join(fits_root, GROUP), group_end(), log=say)
    times = prep["times"]
    tms = data.to_ms(times)
    n = len(times)
    ok = np.isfinite(prep["odds"][ASSET][:, 0])
    lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
    aux = shadows.aux_from_ev(prep["ev"][ASSET], prep["px"][ASSET])
    inp = shadows.book_inputs(prep, ASSET)
    base_cfg = shadows.asset_cfg(ASSET, dict(prep["cfg"]))
    if float(base_cfg["stop_units"]) != 2.0:
        raise RuntimeError("the engine's stop_units is %r, not the registered 2.0" % base_cfg["stop_units"])
    tgt = aux["targets"]
    row_of = lambda k: tgt.iloc[k] if len(tgt.columns) else pd.Series(dtype=float)   # noqa: E731
    rule = dict(shadows.CHALLENGERS["b_targets"]["rule"])
    idx = dict((k, min(max(int(times.searchsorted(pd.Timestamp(d, tz="UTC"))), lo + 1), n - 1))
               for k, d in (("mid", MID), ("holdout", HOLDOUT), ("forward", FORWARD)))
    books, cfgs = {}, {}
    for name, units in BOOKS:
        cfg = dict(base_cfg, stop_units=float(units))
        cfgs[name] = cfg
        books[name] = shadows.run(inp["px"], inp["odds"], inp["shock"], inp["tide"], inp["unit"], cfg, lo, n,
                                  bias=inp["bias"], guard=inp["guard"], rule=rule, aux=aux, times_ms=tms, row_of=row_of)
        say("stop %.1f: %d trades, net %+.0f (%.0fs)" % (units, len(books[name]["trades"]),
                                                         books[name]["equity"][n - 1] - START, time.time() - t0))
    ref = shadows.run_challenger("b_targets", prep, ASSET, lo, n, aux=aux)        # GATE: the engine's own book
    gate_ok, why = h62.same_book(ref, books[CUR], lo, n)
    if not gate_ok:
        raise RuntimeError("GATE FAILED: the 2.0 book is not the engine's b_targets: %s" % why)
    say("gate passed: the 2.0 book is the engine's own b_targets (%d trades)" % len(ref["trades"]))
    res = analyse(books, cfgs, inp["px"], lo, n, idx, tgt, times=times)
    res.update({"study": "H114", "asset": ASSET, "window": [str(times[lo])[:16], str(times[n - 1])[:16]],
                "cuts": {"mid": str(times[idx["mid"]])[:16], "holdout": str(times[idx["holdout"]])[:16],
                         "forward": str(times[idx["forward"]])[:16]},
                "gate": {"ok": True, "detail": why, "trades": int(len(ref["trades"]))},
                "cfg": {"risk_per_trade": base_cfg["risk_per_trade"], "leverage_cap": base_cfg["leverage_cap"],
                        "cost_side": base_cfg["cost_side"], "barrier_atr": base_cfg["barrier_atr"],
                        "version": base_cfg.get("version"), "rule": rule},
                "log": lines, "seconds": round(time.time() - t0, 1),
                "run_utc": time.strftime("%Y-%m-%d %H:%M", time.gmtime())})
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, indent=1, default=float)
    write_report(res)
    say("verdict for the 3.0 stop: %s; legs %s; net over all history higher: %s; leave-it-out proposal: %s" % (
        "PASSES" if res["passes"] else "does not pass",
        dict((k, v["holds"]) for k, v in res["verdict"][PRIMARY]["legs"].items()),
        res["verdict"][PRIMARY]["net_all_higher"], res["leave_out"]["proposal"]))
    return res


# =====================================================================================
# the report
# =====================================================================================
NAMES = {"s2": "Stop 2.0 (current)", "s3": "Stop 3.0 (tested)", "s4": "Stop 4.0 (for comparison)"}
PNAMES = {"all": "All history", "h1": "First half", "h2": "Second half", "mid": "Second half before the holdout",
          "holdout": "Holdout", "forward": "Forward"}


def _n(x, f="%+.1f"):
    return "-" if x is None else f % x


def write_report(res):
    B = res["books"]
    cuts, w = res["cuts"], res["window"]
    v = res["verdict"][PRIMARY]
    cur = B[CUR]["periods"]
    yes = lambda x: "yes" if x else "NO"                           # noqa: E731
    L = ["# H114: USDJPY in the Setups book. A wider stop, or leave it out?", "",
         "Run %s UTC on the laptop. History replay, paper only. Registered before any number" % res["run_utc"],
         "(`research/HYPOTHESES.md`, section H114). Nothing live was changed by this study.", "",
         "A replay on history is a look back. It is not proof that a rule works. The only test is forward paper trading.", "",
         "## The answer in short", ""]
    L += ["- **The wider stop (3.0): %s** by the condition fixed in advance." % (
        "PASSES" if res["passes"] else "DOES NOT PASS"),
        "  First half %s, second half %s, holdout %s, total result higher than today's rule %s." % (
            yes(v["legs"]["h1"]["holds"]), yes(v["legs"]["h2"]["holds"]), yes(v["legs"]["holdout"]["holds"]),
            yes(v["net_all_higher"])),
        "  (%s)" % ("; ".join("%s: %s by the registered check, %s by the plain ratio" % (
            PNAMES[p], yes(v["legs"][p]["holds"]), yes(v["legs"][p]["bare_ratio_higher"]))
            for p in LEGS if v["legs"][p]["holds"] != v["legs"][p]["bare_ratio_higher"])
            or "the registered check and the plain ratio agree in every period"),
        "- **Leave USDJPY out: %s.**" % (
            "the record meets the rule written down for a proposal (at or below zero in all three periods); the owner decides"
            if res["leave_out"]["proposal"] else
            "the record does not make that case by the rule written down in advance"),
        "  Today's rule, sum of R: first half %s, second half %s, holdout %s. The rule asked for all three at or below zero." % (
            _n(cur["h1"]["sum_r"]), _n(cur["h2"]["sum_r"]), _n(cur["holdout"]["sum_r"])), ""]
    rp = os.path.join(OUT, "reading.md")
    if os.path.exists(rp):
        with open(rp, encoding="utf-8") as fh:
            L += ["## What it means", "", fh.read().strip(), ""]
    L += ["## Words used", "",
          "- **Setups book**: the paper book `b_targets`. It sells half at Target 1, the rest at Target 2, and moves the stop to the entry after Target 1.",
          "- **Barrier**: 1.5 times the average hourly range of the last 14 hours. The engine measures distances in barriers.",
          "- **Stop**: the price where a losing trade is closed. Today it is 2.0 barriers from the entry. Tested here: 3.0 and 4.0.",
          "- **Size**: the engine sizes each trade so that a stop costs about 2% of the book. A wider stop means a smaller position.",
          "- **R**: a trade's result divided by what it risked at its stop. -1R is a full stop. +2R is twice the risk, won.",
          "- **Net**: the change in the book's value, fees included, open trades marked at the last price.",
          "- **Worst fall**: the largest drop of the book from a high to a later low inside the period, in percent.",
          "- **Net / worst fall**: net in percent divided by the worst fall in percent. Higher is better. It asks what the gain cost in pain.",
          "- **Stop-out**: a trade closed at its first stop, before Target 1.",
          "- **Periods**: first half = %s to %s. Second half = %s to %s (it contains the holdout)." % (
              w[0][:10], cuts["mid"][:10], cuts["mid"][:10], w[1][:10]),
          "  Holdout = from %s. Forward = from %s (the days the engine has run live)." % (cuts["holdout"][:10], cuts["forward"][:10]),
          "", "## How the check was run", "",
          "- USDJPY only, %s to %s UTC. Three books, each from $10,000, run by the engine's own code." % (w[0], w[1]),
          "- The only setting changed is the stop distance. No engine file was edited.",
          "- Gate: the 2.0 book equals the engine's own Setups book on every trade and every bar (%d trades). Passed." % res["gate"]["trades"],
          "- The targets move with the stop. That is the engine's own behaviour and it was kept. See the last table.", ""]
    L += ["## Results per period", "",
          "| Period | Book | Trades | Won | Sum of R | Chance band | Mean R | Net $ | Net % | Fees $ | Worst fall | Net / worst fall |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in PERIODS:
        for name, _u in BOOKS:
            s = B[name]["periods"][p]
            L.append("| %s | %s | %d | %s | %s | %s | %s | %+.0f | %+.1f%% | %.0f | %.1f%% | %s |" % (
                PNAMES[p], NAMES[name], s["trades"], _n(s["won_pct"], "%.0f%%"), _n(s["sum_r"]),
                _n(s.get("sum_r_band"), "+/- %.0f"), _n(s["mean_r"], "%+.3f"),
                s["net_usd"], s["net_pct"], s["fees_usd"], s["fall_pct"], _n(s["net_over_fall"], "%+.2f")))
    L += ["", "Trades are counted in the period they were entered. Net % is against the book's value at the period's start.",
          "The forward rows are about two weeks: a description, not a result.",
          "Chance band: how far the sum of R can drift by luck alone over that many trades (two standard errors, as if the",
          "trades were independent). A sum of R inside its band cannot be told from zero. This column was added after the",
          "first run. It is a yardstick and is not part of the registered condition.", "",
          "## The condition fixed in advance, leg by leg", "",
          "A period counts for the wider stop if its net / worst fall is higher than today's rule.",
          "Where the wider stop lost money in a period, the ratio misleads. There the period counts only if it lost less",
          "and its worst fall is not deeper. This guard was registered before the run.",
          "The plain ratio, with no guard, is shown beside it. Where the two disagree, both are given.", "",
          "| Check | Stop 2.0 (current) | Stop 3.0 | Plain ratio higher for 3.0 | Registered check holds for 3.0 | Stop 4.0 (not graded) |",
          "|---|---|---|---|---|---|"]
    v4 = res["verdict"]["s4"]
    for p in LEGS:
        how = {"ratio": "by the ratio", "guard": "by the guard: net %+.1f%% against %+.1f%%, worst fall %.1f%% against %.1f%%" % (
            B["s3"]["periods"][p]["net_pct"], cur[p]["net_pct"], B["s3"]["periods"][p]["fall_pct"], cur[p]["fall_pct"])}
        L.append("| %s: net / worst fall | %s | %s | %s | %s (%s) | %s (%s; plain ratio %s) |" % (
            PNAMES[p], _n(cur[p]["net_over_fall"], "%+.2f"), _n(B["s3"]["periods"][p]["net_over_fall"], "%+.2f"),
            yes(v["legs"][p]["bare_ratio_higher"]), yes(v["legs"][p]["holds"]), how[v["legs"][p]["by"]],
            _n(B["s4"]["periods"][p]["net_over_fall"], "%+.2f"),
            "would hold" if v4["legs"][p]["holds"] else "would not hold",
            "higher" if v4["legs"][p]["bare_ratio_higher"] else "not higher"))
    L.append("| All history: net $ | %+.0f | %+.0f | %s | %s | %+.0f (%s) |" % (
        cur["all"]["net_usd"], B["s3"]["periods"]["all"]["net_usd"], yes(v["net_all_higher"]), yes(v["net_all_higher"]),
        B["s4"]["periods"]["all"]["net_usd"], "higher" if v4["net_all_higher"] else "not higher"))
    for p in LEGS:                                                 # the guard's unit: percent (in the code before the run)
        c3, w3 = cur[p], B["s3"]["periods"][p]
        if v["legs"][p]["by"] == "guard" and (w3["net_usd"] > c3["net_usd"]) != (w3["net_pct"] > c3["net_pct"]):
            L += ["", "%s: the guard compares the net in percent of each book's value at the period's start (set in the code before"
                  % PNAMES[p], "the run; the registration did not name the unit). In dollars the 3.0 book lost %s there (%+.0f against %+.0f),"
                  % ("less" if w3["net_usd"] > c3["net_usd"] else "more", w3["net_usd"], c3["net_usd"]),
                  "because it entered the period with $%.0f against $%.0f. In dollars this check would %s. The verdict does not turn on it."
                  % (w3["base_usd"], c3["base_usd"],
                     "hold" if w3["net_usd"] > c3["net_usd"] and w3["fall_pct"] >= c3["fall_pct"] else "not hold")]
    L += ["", "**Verdict for the 3.0 stop: %s.** With the plain ratio and no guard: %s. The 4.0 stop, had it been graded: %s (plain ratio: %s)." % (
        "PASSES" if res["passes"] else "DOES NOT PASS", "passes" if v["passes_bare_ratio"] else "does not pass",
        "would pass" if v4["passes"] else "would not pass", "would pass" if v4["passes_bare_ratio"] else "would not pass"),
          "A pass would lead only to a proposal for a forward paper book. It would not change a live book.", "",
          "## Were the stops hit by noise?", "",
          "For each stop-out: did price trade back at the entry within the next 96 sessions (24 hours of trading)?",
          "The yardstick: did price instead run a further full stop distance past the stop in the same time?",
          "If price had no memory the two shares would be about equal. Stops hit by noise would show a clearly larger first share.", "",
          "| Period | Book | Stop-outs | Judged | Back at the entry | Ran a further stop distance | Both | Neither |",
          "|---|---|---|---|---|---|---|---|"]
    for p in PERIODS:
        for name, _u in BOOKS:
            s = B[name]["stops"][p]
            L.append("| %s | %s | %d | %d | %s | %s | %d | %d |" % (
                PNAMES[p], NAMES[name], s["stopouts"], s["judged"], _n(s["back_pct"], "%.0f%%"), _n(s["further_pct"], "%.0f%%"),
                s["both"], s["neither"]))
    L += ["", "\"Judged\" leaves out stop-outs with fewer than 96 later sessions on file. The rest of the bar that hit the stop is not counted.",
          "", "Of today's rule's stop-outs that were back at the entry: how many would a wider stop from the same entry have sat through?", "",
          "| Period | Back at the entry | A 3.0 stop holds | A 4.0 stop holds |", "|---|---|---|---|"]
    for p in PERIODS:
        st = B[CUR]["stops"][p]["sat_through"]
        L.append("| %s | %d | %d (%s) | %d (%s) |" % (PNAMES[p], st["s3"]["of"], st["s3"]["kept"], _n(st["s3"]["kept_pct"], "%.0f%%"),
                                                    st["s4"]["kept"], _n(st["s4"]["kept_pct"], "%.0f%%")))
    L += ["", "This is the same entry with a wider stop, not the wider book: once one exit differs, the books trade at different times.",
          "", "## Size, stop distance and targets (checks)", "",
          "| Book | Median stop distance | Range | Median size | Trades at the 1x floor | At the 100x cap | Mean result of a stop-out | Worst trade | Median hold |",
          "|---|---|---|---|---|---|---|---|---|"]
    for name, _u in BOOKS:
        z = B[name]["sizing"]
        L.append("| %s | %.2f%% | %.2f%% to %.2f%% | %.1fx | %.1f%% | %.1f%% | %sR | %sR | %.0f sessions |" % (
            NAMES[name], z["stop_pct_median"], z["stop_pct_min"], z["stop_pct_max"], z["leverage_median"], z["at_floor_pct"],
            z["at_cap_pct"], _n(z["stop_exit_mean_r"], "%+.2f"), _n(z["worst_r"], "%+.2f"), z["hold_bars_median"]))
    L += ["", "| Book | Target 1 from a Fibonacci level | from a day's travel | from 1.5R | Median Target 1 | Median Target 2 | Target 2 from a Fibonacci level | Not reproduced |",
          "|---|---|---|---|---|---|---|---|"]
    for name, _u in BOOKS:
        t = B[name]["targets"]
        s1, s2 = t["t1_source"], t["t2_source"]
        L.append("| %s | %d | %d | %d | %s%% (%sR) | %s%% (%sR) | %d | %d |" % (
            NAMES[name], s1.get("fibonacci", 0), s1.get("day_travel", 0), s1.get("1.5R", 0), _n(t["t1_pct_median"], "%.2f"),
            _n(t["t1_in_r_median"], "%.2f"), _n(t["t2_pct_median"], "%.2f"), _n(t["t2_in_r_median"], "%.2f"),
            s2.get("fibonacci", 0), t["not_reproduced"]))
    L += ["", "Target distances are from the entry, in percent of price and in R. \"Not reproduced\" counts trades whose targets",
          "this script could not recompute exactly from the engine's own function; they are left out of this table only.", "",
          "## Leave USDJPY out? Today's rule on its own record", "",
          "| Period | Trades | Won | Sum of R | Mean R | Net $ | Worst fall | Sum of R at or below zero |", "|---|---|---|---|---|---|---|---|"]
    for p in PERIODS:
        s = cur[p]
        L.append("| %s | %d | %s | %s | %s | %+.0f | %.1f%% | %s |" % (
            PNAMES[p], s["trades"], _n(s["won_pct"], "%.0f%%"), _n(s["sum_r"]), _n(s["mean_r"], "%+.3f"), s["net_usd"],
            s["fall_pct"], "yes" if s["sum_r"] <= 0 else "no"))
    L += ["", "Rule written down in advance: a proposal to leave the market out only if the sum of R is at or below zero in the",
          "first half AND the second half AND the holdout. Result: %s." % (
              "all three are at or below zero, so it is written down as a proposal for the owner to decide"
              if res["leave_out"]["proposal"] else "not all three, so no proposal by this rule"),
          "Leaving a market out is the owner's decision either way. This study changes nothing.", "",
          "## The replay's trades in the forward days", ""]
    for name, _u in BOOKS:
        rows = B[name].get("forward_trades") or []
        L.append("- %s: %s. Open at the end: %s." % (NAMES[name], "no closed trade" if not rows else "; ".join(
            "%s %s at %.3f, stop %.2f%% away, out %s %s, %+.2fR, %+.0f" % (
                x["t_in"][5:], "long" if x["side"] == 1 else "short", x["p_in"], x["stop_pct"], x["t_out"][5:], x["why_out"],
                x["r"], x["pnl_usd"]) for x in rows), B[name]["open_at_end"]))
    L += ["", "These are the replay's trades, not the live book's. The replay book arrives at 11 Nov with its own history.", "",
          "## Limits", "",
          "- One market, one history, three stop values. Earlier studies had already looked at this history (H90 looked at these stop distances on the first half, all markets pooled).",
          "- No allowance was made for looking at two stop values. A pass would be weak evidence.",
          "- Paper costs: 0.01% a side. No slippage. No financing cost on a leveraged position held for days.",
          "- A stop is filled at its price, or at the bar's open if price gapped through it.",
          "- Dollar totals on this market have moved by thousands between rebuilds of the readings store.",
          "- The books compound: each trade risks 2% of what the book holds then. Dollar results late in the history depend on what came before; the percent columns do not."]
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits-dir", default=None)
    ap.add_argument("--report", action="store_true", help="rewrite report.md from results.json (no history is loaded)")
    args = ap.parse_args(argv)
    if args.report:
        with open(os.path.join(OUT, "results.json"), encoding="utf-8") as fh:
            write_report(json.load(fh))
        return
    if not args.fits_dir:
        ap.error("--fits-dir is required for a run")
    run(args.fits_dir)


if __name__ == "__main__":
    main()
