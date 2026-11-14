# -*- coding: utf-8 -*-
"""A first, IN-SAMPLE look at the challenger shadow books (engine15/shadows.py) on recent history.

For each market group the script builds the odds exactly as the live step does (backtest.prepare,
cfg["birth"] LEARN_DAYS = 240 days before the last bar, the group's own grading horizon), then runs
the main rule and every challenger from a fresh $10,000 per asset over the last --days (120) days,
on the same odds and readings, with the same fees. Writes research/out/challengers.md and .json.

WHAT THIS IS NOT. It is history the rules' authors had already seen (the H3 rule was picked from a
grid on this kind of history; the main rule's constants too), one window, six correlated assets.
It can reject an idea, never prove one (docs/CHARTER.md). Forward results decide.

ONE DIFFERENCE FROM LIVE (memory: an 8 GB laptop with the live loop running). Live hands prepare
ALL history since 2019 and the voices learn from all of it; here only the last --history-days (700)
days of bars are loaded, so the voices learn from about 460 days before the 240-day walk-forward
starts. The odds are therefore close to live's, not identical.

    py -3 research/challengers.py [--days 120] [--history-days 700] [--groups crypto,metals,fx,index]
"""
import argparse
import ctypes
import gc
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine15 import backtest, data, livefeeds, shadows  # noqa: E402
from engine15.config import CFG, voting_for  # noqa: E402

LEARN_DAYS = 240                                    # engine15/live.py LEARN_DAYS
OUT = os.path.join(ROOT, "research", "out")
START = shadows.START_EQUITY


def peak_mb():
    """This process's peak working set (Windows), MB; None elsewhere."""
    if os.name != "nt":
        return None

    class PMC(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]
    c = PMC()
    c.cb = ctypes.sizeof(PMC)
    try:
        ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(c), c.cb)
        return int(c.PeakWorkingSetSize / 2 ** 20)
    except Exception:
        return None


def stats(eq, trades, lo, hi):
    """Return, max drawdown (marked every session), closed trades, win rate, average R, profit factor, fees."""
    e = eq[lo:hi]
    e = e[np.isfinite(e)]
    if not len(e):
        return {}
    base = START if lo == 0 or not np.isfinite(eq[lo - 1]) else eq[lo - 1]
    curve = np.concatenate([[base], e])
    t = trades
    win, loss = t.pnl_usd[t.pnl_usd > 0].sum(), -t.pnl_usd[t.pnl_usd <= 0].sum()
    return {"return_pct": round(float(e[-1] / base - 1) * 100, 2),
            "max_dd_pct": round(float((curve / np.maximum.accumulate(curve) - 1).min()) * 100, 2),
            "trades": int(len(t)), "win_rate_pct": round(float((t.pnl_usd > 0).mean() * 100), 1) if len(t) else None,
            "avg_r": round(float(t.r_mult.mean()), 3) if len(t) and t.r_mult.notna().any() else None,
            "profit_factor": round(float(win / loss), 2) if loss > 0 else None,
            "fees_usd": round(float(t.fees_usd.sum()), 2), "pnl_usd": round(float(t.pnl_usd.sum()), 2)}


def run_group(g, assets, days, history_days, log=print):
    t0 = time.time()
    crypto = CFG.get("crypto", CFG["assets"])
    bars = dict((a, data.load(a)) for a in assets)
    last_open = min(df.index[-1] for df in bars.values())
    first = last_open - pd.Timedelta(days=history_days)
    bars = dict((a, df[(df.index <= last_open) & (df.index >= first)]) for a, df in bars.items())
    funding = dict((a, data.load_funding(a) if a in crypto else None) for a in assets)
    live = dict((a, livefeeds.load_live(a)) for a in assets)
    cfg = dict(CFG, assets=tuple(assets), birth=str((last_open - pd.Timedelta(days=LEARN_DAYS)).date()),
               voting=voting_for(g))                        # as live.step_group (v5.1: the group's own voting cards)
    if g in CFG.get("group_horizon", {}):
        cfg["horizon"] = CFG["group_horizon"][g]
    prep = backtest.prepare(cfg=cfg, bars=bars, funding=funding, live=live)
    del bars
    times = prep["times"]
    n = len(times)
    lo = max(int(times.searchsorted(last_open - pd.Timedelta(days=days))), prep["birth_idx"])
    mid = lo + (n - lo) // 2
    out = {"window": [str(times[lo])[:16], str(times[n - 1])[:16]], "split": str(times[mid])[:16], "assets": {}}
    curves = {}
    for a in assets:
        aux = shadows.aux_from_ev(prep["ev"][a], prep["px"][a])
        c, o = prep["px"][a]["close"], prep["px"][a]["open"]
        fee = shadows.asset_cfg(a, cfg)["cost_side"]
        seg = c[lo:n] / o[lo]
        res = {"buy_hold": {"return_pct": round(float(seg[-1] * (1 - 2 * fee) - 1) * 100, 2),
                            "max_dd_pct": round(float((seg / np.maximum.accumulate(seg) - 1).min()) * 100, 2)},
               "books": {}}
        curves[(a, "buy_hold")] = pd.Series(START * seg * (1 - 2 * fee), index=times[lo:n])
        for name in shadows.CHALLENGERS:
            b = shadows.run_challenger(name, prep, a, lo, n, aux=aux)
            tr = b["trades"]
            res["books"][name] = {"all": stats(b["equity"], tr, lo, n),
                                  "first_half": stats(b["equity"], tr[tr.i_out < mid], lo, mid),
                                  "second_half": stats(b["equity"], tr[tr.i_out >= mid], mid, n),
                                  "open_at_end": {1: "LONG", -1: "SHORT"}.get(b["state"]["pos"], "FLAT")}
            curves[(a, name)] = pd.Series(b["equity"][lo:n], index=times[lo:n])
        out["assets"][a] = res
    log("%s: %d sessions in the window, %s .. %s (%.0fs, peak %s MB)" % (g, n - lo, out["window"][0], out["window"][1],
                                                                        time.time() - t0, peak_mb()))
    del prep
    gc.collect()
    return out, curves


def totals(curves, names):
    """Each book's six assets summed on one clock (markets closed: the last equity carries)."""
    frame = pd.concat(curves, axis=1).sort_index().ffill()
    out = {}
    for name in names:
        cols = [k for k in frame.columns if k[1] == name]
        tot = frame[cols].bfill().sum(axis=1).values
        k = len(cols)
        mid = len(tot) // 2
        out[name] = {"assets": k, "pnl_usd": round(float(tot[-1] - START * k), 2),
                     "return_pct": round(float(tot[-1] / (START * k) - 1) * 100, 2),
                     "max_dd_pct": round(float((tot / np.maximum.accumulate(np.concatenate([[START * k], tot]))[1:] - 1).min()) * 100, 2),
                     "first_half_pct": round(float(tot[mid] / (START * k) - 1) * 100, 2),
                     "second_half_pct": round(float(tot[-1] / tot[mid] - 1) * 100, 2)}
    return out


def fmt(v, suffix=""):
    return "-" if v is None else ("%+.2f%s" % (v, suffix) if isinstance(v, float) else "%s%s" % (v, suffix))


def write_md(res, path):
    names = list(shadows.CHALLENGERS)
    L = ["# Challenger books on recent history (IN-SAMPLE, not proof)", "",
         "Written by `research/challengers.py` on %s. Every book starts flat with $10,000 per asset at the "
         "window's start and trades the same odds the live step would have formed (voices walked forward "
         "from 240 days back; trained on the last %d days of bars, not all history as live does). "
         "Fees as live. Paper only." % (res["written_utc"], res["history_days"]), "",
         "**Read this plainly:** one %d-day window that the rules' authors had already lived through; the H3 "
         "limit was chosen from a grid on this kind of history; six assets that move together. A history "
         "read can reject an idea, never prove one. Promotion is decided on forward results "
         "(docs/CHARTER.md)." % res["days"], "",
         "## All six assets together ($60,000 start)", "",
         "| Book | P&L | Return | vs main | Max drawdown | First half | Second half | Trades | Win rate | Avg R | Fees |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    tot = res["totals"]
    base = tot["main"]["pnl_usd"]
    for name in names + ["buy_hold"]:
        t = tot[name]
        tr = [res["groups"][g]["assets"][a]["books"][name]["all"] for g in res["groups"]
              for a in res["groups"][g]["assets"]] if name != "buy_hold" else []
        ntr = sum(x.get("trades", 0) for x in tr)
        wins = sum((x.get("win_rate_pct") or 0) * x.get("trades", 0) / 100.0 for x in tr)
        rs = [x["avg_r"] * x["trades"] for x in tr if x.get("avg_r") is not None]
        title = shadows.CHALLENGERS[name]["title"] if name in shadows.CHALLENGERS else "Buy and hold (one round trip)"
        L.append("| %s (`%s`) | $%+.0f | %+.2f%% | $%+.0f | %.2f%% | %+.2f%% | %+.2f%% | %s | %s | %s | %s |" % (
            title, name, t["pnl_usd"], t["return_pct"], t["pnl_usd"] - base, t["max_dd_pct"], t["first_half_pct"],
            t["second_half_pct"], ntr if tr else "-", "%.1f%%" % (100.0 * wins / ntr) if ntr else "-",
            "%+.3f" % (sum(rs) / ntr) if ntr and rs else "-",
            "$%.0f" % sum(x.get("fees_usd", 0) for x in tr) if tr else "-"))
    L += ["", "Max drawdown: of the six books summed and marked every session. Halves split the window by sessions.", ""]
    for g, gr in res["groups"].items():
        L += ["## %s: %s to %s UTC (halves split at %s)" % (g, gr["window"][0], gr["window"][1], gr["split"]), ""]
        for a, ar in gr["assets"].items():
            bh = ar["buy_hold"]
            L += ["### %s (buy and hold %+.2f%%, its max drawdown %.2f%%)" % (a, bh["return_pct"], bh["max_dd_pct"]), "",
                  "| Book | Return | Max DD | Trades | Win rate | Avg R | Profit factor | Fees | 1st half | 2nd half | At end |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
            for name in names:
                b = ar["books"][name]
                s, h1, h2 = b["all"], b["first_half"], b["second_half"]
                L.append("| `%s` | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                    name, fmt(s.get("return_pct"), "%"), fmt(s.get("max_dd_pct"), "%"), s.get("trades"),
                    fmt(s.get("win_rate_pct"), "%").replace("+", ""), fmt(s.get("avg_r")), fmt(s.get("profit_factor")).replace("+", ""),
                    "$%.0f" % s.get("fees_usd", 0), fmt(h1.get("return_pct"), "%"), fmt(h2.get("return_pct"), "%"), b["open_at_end"]))
            L.append("")
    L += ["## The rules (engine15/shadows.py)", ""]
    for name, spec in shadows.CHALLENGERS.items():
        L.append("- `%s`: %s" % (name, spec["title"]))
    L += ["", "Intrabar conventions: limits fill only when a bar trades strictly through them, at the limit; a stop "
          "live at a bar's start comes before any target or limit in that bar; Target 1 and 2 may fill in one bar, the "
          "break-even stop is live from the next bar. Trade counts are closed trades; a b_targets trade with a partial "
          "exit counts once.", ""]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=120)
    ap.add_argument("--history-days", type=int, default=700)
    ap.add_argument("--groups", default=None)
    args = ap.parse_args(argv)
    want = None if not args.groups else set(args.groups.split(","))
    res = {"written_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "days": args.days,
           "history_days": args.history_days, "groups": {}}
    curves = {}
    for g, assets in CFG["universes"]:
        if want and g not in want:
            continue
        res["groups"][g], c = run_group(g, list(assets), args.days, args.history_days)
        curves.update(c)
    res["totals"] = totals(curves, list(shadows.CHALLENGERS) + ["buy_hold"])
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "challengers.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    write_md(res, os.path.join(OUT, "challengers.md"))
    for name, t in res["totals"].items():
        print("%-14s P&L %+9.2f  return %+6.2f%%  max DD %6.2f%%  halves %+6.2f%% / %+6.2f%%" % (
            name, t["pnl_usd"], t["return_pct"], t["max_dd_pct"], t["first_half_pct"], t["second_half_pct"]))
    print("peak memory %s MB; written to %s" % (peak_mb(), os.path.join(OUT, "challengers.md")))


if __name__ == "__main__":
    main()
