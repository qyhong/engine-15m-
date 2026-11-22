# -*- coding: utf-8 -*-
"""H73: one member wallet on the BTC and ETH trades of three engine books (b_targets, b_trend30, b_wait_stop) at three
fee levels and three sizings. Research only; registered in research/HYPOTHESES.md before this file was run. Reuses H63's
wallet walk (research/h63_member_wallet.py, imported, not edited). Reads the evidence store, the cached fits and the
stored funding series, all read-only. It changes no book.

    /data/venv-research/bin/python research/h73_wallet_real_fees.py --fits-dir <fits_today>
    py -3 -X utf8 research/h73_wallet_real_fees.py --report     # report.md again from results.json; computes nothing

GATE (per book and coin): walked with the paper book's own sizing and fee, one coin at a time, funding off, the walk
reproduces that engine book's marked equity at every bar.
"""
import argparse
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
import h63_member_wallet as h63  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "h73_wallet_real_fees")
H63_RES = os.path.join(ROOT, "research", "out", "h63_member_wallet", "results.json")
COINS = h63.COINS
BOOKS = OrderedDict([("b_targets", "current rule (b_targets)"),
                     ("b_trend30", "30-day trend filter (b_trend30, H67; found on this history)"),
                     ("b_wait_stop", "wait after a stop-out (b_wait_stop, H68; found on this history)")])
FEES = OrderedDict([("f10", 0.0010), ("f05", 0.0005), ("f02", 0.0002)])
FEE_WORD = {"f10": "0.10% (H63's, check)", "f05": "0.05% (taker, PRIMARY)", "f02": "0.02% (maker-like bound)"}
SEGS = (("h1", None, "2023-06-08"), ("h2", "2023-06-08", None), ("holdout", "2025-11-11", None))
SEG_WORD = {"h1": "first half (to 2023-06-07)", "h2": "second half (2023-06-08 on)", "holdout": "holdout (2025-11-11 on)"}
MID = h63.MID
SEED, DRAWS, PATH_M = 73, 10000, 12
VARIANT_NOTE = "(found on this same history: cannot show an advantage)"


# =====================================================================================
# the trades of an engine book as setups (shadows.run's end state carries the open trade)
# =====================================================================================
def setups_of_shadow(coin, book, px, n):
    out = [h63.setup_of(coin, t.side, t.p_in, t.stop0, t.i_in, t.i_out, t.p_out, t.why_out, t.target_1, px)
           for t in book["trades"].itertuples()]
    st = book["state"]
    dropped = 0
    if st.get("pos"):
        i_in = int(st["i_in"])
        if i_in >= n:                                   # booked at the last close, held from a bar beyond the cut
            dropped = 1
        else:
            out.append(h63.setup_of(coin, st["pos"], st["entry"], st["stop0"], i_in, None, None, None, st.get("t1"), px,
                                    t1_hit=st.get("t1_hit"), last=n - 1))
    return out, dropped


def gate(coin, book, setups, lo, n, cfg, px):
    ctx = h63.context(setups, px, None, cfg["cost_side"])
    r = h63.walk(ctx, lo, n, h63.paper_sizer(cfg), start_w=shadows.START_EQUITY, funding_on=False, worst_px=False)
    ref = book["equity"][lo:n]
    if r["outcome"] is not None:
        return False, "the paper walk ended early (%s)" % r["outcome"]
    d = np.nanmax(np.abs(r["eq"] - ref) / np.maximum(1.0, np.abs(ref)))
    return bool(d < 1e-7), "largest relative gap %.3g over %d bars, %d trades" % (d, n - lo, len(setups))


def replay(fits_root, log=print):
    import h59_half_be as h59
    import h62_setups_wide_stop as h62
    g = "crypto"
    prep = h59.prep_cut(g, list(COINS), os.path.join(fits_root, g), h62.group_end(g, list(COINS)), log=log)
    times = prep["times"]
    n = len(times)
    out = {"times": times, "px": prep["px"], "books": OrderedDict(), "gate": {}, "lo": {}, "fee_book": None, "dropped": {},
           "closed": {}}
    for name in BOOKS:
        out["books"][name] = []
    for a in COINS:
        ok = np.isfinite(prep["odds"][a][:, 0])
        lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
        out["lo"][a] = lo
        aux = shadows.aux_from_ev(prep["ev"][a], prep["px"][a])
        for name in BOOKS:
            cfg = shadows.asset_cfg(a, dict(prep["cfg"], **shadows.CHALLENGERS[name]["cfg"]))
            if cfg.get("early_fill") is not True:
                raise RuntimeError("%s: early_fill is not on for %s (expected since v5.2.9)" % (name, a))
            b = shadows.run_challenger(name, prep, a, lo, n, aux=aux)
            s, dropped = setups_of_shadow(a, b, prep["px"][a], n)
            ok_g, why = gate(a, b, s, lo, n, cfg, prep["px"])
            out["gate"]["%s %s" % (name, a)] = {"ok": ok_g, "detail": why}
            out["dropped"]["%s %s" % (name, a)] = dropped
            out["closed"]["%s %s" % (name, a)] = int(len(b["trades"]))
            log("%s %s gate: %s (%s)" % (name, a, "passed" if ok_g else "FAILED", why))
            if not ok_g:
                raise RuntimeError("GATE FAILED on %s %s: %s" % (name, a, why))
            out["books"][name] += s
            fee = cfg["cost_side"]
            if out["fee_book"] is None:
                out["fee_book"] = fee
            assert fee == out["fee_book"]
    for name in BOOKS:
        out["books"][name].sort(key=lambda s: (s["i_in"], h63.ORDER[s["coin"]]))
    return out


# =====================================================================================
# the monthly statistic
# =====================================================================================
def monthly(eq, times):
    """Complete calendar months only: returns between consecutive month-end equities."""
    s = pd.Series(eq, index=times).dropna()
    last = s.resample("MS").last()
    first_full = s.index[0] == s.index[0].normalize().replace(day=1)
    bar = times[1] - times[0]
    end_full = (s.index[-1] + bar).day == 1 and (s.index[-1] + bar).normalize() == s.index[-1] + bar
    v = last.values.astype(float)
    labels = [str(x)[:7] for x in last.index]
    if not end_full:
        v, labels = v[:-1], labels[:-1]
    if first_full:                                     # a complete first month: its base is the start
        v, labels = np.concatenate([[s.values[0]], v]), ["start"] + labels
    R, months = [], []
    for k in range(1, len(v)):
        if v[k - 1] <= 0:
            break
        R.append(v[k] / v[k - 1] - 1.0)
        months.append(labels[k])
        if v[k] <= 0:
            break
    return np.asarray(R), months


def stat(R):
    m = len(R)
    if m < 2:
        return {"months": m}
    rng = np.random.default_rng(SEED)
    means = R[rng.integers(0, m, size=(DRAWS, m))].mean(axis=1)
    rng = np.random.default_rng(SEED)
    cum = np.cumprod(1.0 + R[rng.integers(0, m, size=(DRAWS, PATH_M))], axis=1)
    return {"months": m, "mean_pct": float(R.mean() * 100), "median_pct": float(np.median(R) * 100),
            "ci90_pct": [float(np.percentile(means, 5) * 100), float(np.percentile(means, 95) * 100)],
            "share_up_months_pct": float((R > 0).mean() * 100), "worst_month_pct": float(R.min() * 100),
            "best_month_pct": float(R.max() * 100),
            "paths12_end_above_pct": float((cum[:, -1] > 1.0).mean() * 100),
            "paths12_below_half_pct": float((cum.min(axis=1) < 0.5).mean() * 100),
            "paths12_median_end_x": float(np.median(cum[:, -1]))}


# =====================================================================================
# run and report
# =====================================================================================
def run(fits_root, log=print):
    t0 = time.time()
    rp = replay(fits_root, log=log)
    times, px = rp["times"], rp["px"]
    n = len(times)
    lo = min(rp["lo"].values())
    fund, missing = {}, 0
    for a in COINS:
        ib, rt, miss = h63.funding_bars(a, times)
        fund[a] = (ib, rt)
        missing += miss
    res = {"first": str(times[lo])[:16], "end": str(times[n - 1])[:16], "fee_book": rp["fee_book"], "gate": rp["gate"],
           "dropped_entry_at_cut": rp["dropped"], "closed_trades": rp["closed"],
           "funding_rows": dict((a, int(len(fund[a][0]))) for a in COINS), "funding_times_without_a_bar": missing,
           "trades": dict((b, len(s)) for b, s in rp["books"].items()), "cells": OrderedDict(),
           "seed": SEED, "draws": DRAWS}
    mid = pd.Timestamp(MID, tz="UTC")
    for bname, setups in rp["books"].items():
        for fk, fee in FEES.items():
            ctx = h63.context(setups, px, times, fee, fund)
            for sk, sz in h63.SIZINGS.items():
                key = "%s|%s|%s" % (bname, sk, fk)
                w, r = h63.whole(ctx, lo, n, times, sz)
                R, months = monthly(r["eq"], times[lo:n])
                cell = {"book": bname, "sizing": sk, "fee": fk, "whole": w, "monthly": stat(R),
                        "monthly_returns": dict(zip(months, [float(x) for x in R])), "segments": {}}
                for seg, a_d, z_d in SEGS:
                    a = lo if a_d is None else int(times.searchsorted(pd.Timestamp(a_d, tz="UTC")))
                    z = n if z_d is None else int(times.searchsorted(pd.Timestamp(z_d, tz="UTC")))
                    cell["segments"][seg], _ = h63.whole(ctx, a, z, times, sz)
                    cell["segments"][seg]["from"], cell["segments"][seg]["to"] = str(times[a])[:16], str(times[z - 1])[:16]
                rows = h63.month_starts(ctx, lo, n, times, sz)
                cell["months"] = h63.tally(rows)
                cell["months_first_half"] = h63.tally([x for x in rows if pd.Timestamp(x["start"], tz="UTC") < mid])
                cell["months_second_half"] = h63.tally([x for x in rows if pd.Timestamp(x["start"], tz="UTC") >= mid])
                cell["month_rows"] = rows
                res["cells"][key] = cell
                m = cell["months"]
                log("%s: final %.0f, fall %.1f%%, wiped %s, fees %.0f; months up %d down %d neither %d; mean month %s (%.0fs)" % (
                    key, w["final_equity"], w["worst_fall_pct"], w["wiped_out"], w["fees"], m["up"], m["down"] + m["wiped"],
                    m["neither"], cell["monthly"].get("mean_pct"), time.time() - t0))
                os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "results.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    write_report(res)
    return res


def _usd(x):
    return "n/a" if x is None else "{:,.0f}".format(x)


def _p(x, d=1):
    return "n/a" if x is None else ("%+." + str(d) + "f%%") % x


def _title(bname):
    return BOOKS[bname]


def write_report(res):
    h63r = json.load(open(H63_RES)) if os.path.exists(H63_RES) else None
    C = res["cells"]
    L = ["# H73: one member wallet on the BTC and ETH trades of three engine books, three sizings, three fees", "",
         "History replay %s to %s UTC, paper, registered before any number (research/HYPOTHESES.md, H73). A description of"
         " history under stated assumptions, not a forecast and not advice. The two variants (b_trend30, b_wait_stop) were"
         " FOUND on this same history: their numbers cannot show an advantage." % (res["first"], res["end"]), "",
         "Trades (closed + open at the cut): " + ", ".join("%s %d" % (b, k) for b, k in res["trades"].items())
         + ". Closed per coin: " + ", ".join("%s %d" % (k, v) for k, v in res["closed_trades"].items())
         + ". Entries booked at the last close and dropped: " + ", ".join("%s %d" % (k, v) for k, v in res["dropped_entry_at_cut"].items() if v)
         + ".", "",
         "Funding from the stored Binance series (%s rows used; %d funding times had no bar). The paper book's own fee: %.2f%% per side." % (
             ", ".join("%s %d" % (a, k) for a, k in res["funding_rows"].items()), res["funding_times_without_a_bar"],
             res["fee_book"] * 100), "",
         "Gate: " + "; ".join("%s %s (%s)" % (k, "passed" if g["ok"] else "FAILED", g["detail"]) for k, g in res["gate"].items()),
         "", "Not modelled: the member's actual fee rate (not available), slippage against the book's prices, the vault's join"
         " window, refusals, exchange limits, rounding. The brake is H63's model of the vault's, not its code.", ""]

    def whole_table(cells, title_of, seg=None):
        T = ["| Cell | Final | Worst fall | Lowest equity | Worst UTC day | Longest losing run | Joined / trimmed / capped / not joined | Fees | Funding paid | Final without funding | Wiped out |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
        for key in cells:
            c = C[key]
            w = c["whole"] if seg is None else c["segments"][seg]
            T.append("| %s | %s | %.1f%% | %s (%s) | %s | %d | %d / %d / %d / %d | %s | %s | %s | %s |" % (
                title_of(c), _usd(w["final_equity"]), w["worst_fall_pct"], _usd(w["lowest_equity"]), w["lowest_at"][:10],
                "n/a" if w["worst_day_pct"] is None else "%.1f%% (%s)" % (w["worst_day_pct"], w["worst_day"]),
                w["longest_losing_run"], w["joined"], w["trimmed"], w["capped"], w["not_joined"], _usd(w["fees"]),
                _usd(w["funding_paid"]), _usd(w["final_equity_no_funding"]),
                ("YES, %s" % w["wiped_at"]) if w["wiped_out"] else ("no" + (" (closes only: YES)" if w["wiped_out_closes_only"] else ""))))
        return T

    def month_table(cells, title_of, part="months"):
        f = lambda x: "n/a" if x is None else "%.0f" % x                                           # noqa: E731
        T = ["| Cell | Starts | +100% first | -50% or wipe-out first (of which wiped) | Neither (median end) | Unfinished | Median days to either | to +100% | to -50% |",
             "|---|---|---|---|---|---|---|---|---|"]
        for key in cells:
            m = C[key][part]
            T.append("| %s | %d | %d | %d (%d) | %d (%s) | %d | %s | %s | %s |" % (
                title_of(C[key]), m["starts"], m["up"], m["down"] + m["wiped"], m["wiped"], m["neither"],
                _usd(m["median_end_neither"]), m["unfinished"], f(m["median_days_to_either"]), f(m["median_days_up"]),
                f(m["median_days_down"])))
        return T

    def stat_table(cells, title_of):
        T = ["| Cell | Complete months | Mean month (90% bootstrap interval) | Median month | Months up | Worst / best month | 12-month paths ending above start | 12-month paths below half at a month-end | Median 12-month path end |",
             "|---|---|---|---|---|---|---|---|---|"]
        for key in cells:
            s = C[key]["monthly"]
            if s.get("months", 0) < 2:
                T.append("| %s | %d | n/a | | | | | | |" % (title_of(C[key]), s.get("months", 0)))
                continue
            T.append("| %s | %d | %s (%s to %s) | %s | %.0f%% | %s / %s | %.1f%% | %.1f%% | %.2fx |" % (
                title_of(C[key]), s["months"], _p(s["mean_pct"], 2), _p(s["ci90_pct"][0], 2), _p(s["ci90_pct"][1], 2),
                _p(s["median_pct"], 2), s["share_up_months_pct"], _p(s["worst_month_pct"]), _p(s["best_month_pct"]),
                s["paths12_end_above_pct"], s["paths12_below_half_pct"], s["paths12_median_end_x"]))
        return T

    sz_word = dict((k, v["title"]) for k, v in h63.SIZINGS.items())
    by_book = lambda c: _title(c["book"]).split(" (")[0] + ("" if c["book"] == "b_targets" else " *")   # noqa: E731
    by_fee = lambda c: "%s, fee %s" % (sz_word[c["sizing"]], FEE_WORD[c["fee"]])                        # noqa: E731
    prim = ["%s|S2|f05" % b for b in BOOKS]
    L += ["## 1. The primary cells: 100% per coin (S2), fee 0.05% per side", "",
          "`*` = a variant found on this same history %s." % VARIANT_NOTE, ""]
    L += whole_table(prim, by_book)
    L += ["", "Month-start table (a fresh 10,000 from every month-start, 365 days):", ""] + month_table(prim, by_book)
    L += ["", "Monthly returns (complete calendar months of the whole-run wallet; months resampled with replacement, %d draws,"
          " seed %d; this treats months as exchangeable, which they are not exactly):" % (res["draws"], res["seed"]), ""]
    L += stat_table(prim, by_book)
    L += ["", "Fresh 10,000 wallets by period (primary cells):", ""]
    for seg, _a, _z in SEGS:
        L += ["%s:" % SEG_WORD[seg], ""] + whole_table(prim, by_book, seg) + [""]
    for bname in BOOKS:
        keys = ["%s|%s|%s" % (bname, sk, fk) for sk in h63.SIZINGS for fk in FEES]
        L += ["## %s: all sizings and fees%s" % (_title(bname), "" if bname == "b_targets" else " " + VARIANT_NOTE), "",
              "Whole replay:", ""] + whole_table(keys, by_fee)
        L += ["", "Month-starts:", ""] + month_table(keys, by_fee)
        L += ["", "Month-starts before / from 2023-06-08:", ""] + month_table(keys, lambda c: by_fee(c) + ", first half",
                                                                             "months_first_half")
        L += month_table(keys, lambda c: by_fee(c) + ", second half", "months_second_half")[2:]
        for seg, _a, _z in SEGS:
            L += ["", "%s, fresh 10,000:" % SEG_WORD[seg], ""] + whole_table(keys, by_fee, seg)
        L += ["", "Monthly statistic (descriptive for all but the S2 0.05% cell):", ""] + stat_table(keys, by_fee) + [""]
    if h63r:
        L += ["## Reproduction check: current rule at 0.10% against H63's published results", "",
              "| Sizing | Read-out | H63 | H73 | Difference |", "|---|---|---|---|---|"]
        for sk in h63.SIZINGS:
            a, b = h63r["sizings"][sk], C["b_targets|%s|f10" % sk]
            for lab, ga in (("final", lambda x: x["whole"]["final_equity"]), ("worst fall %", lambda x: x["whole"]["worst_fall_pct"]),
                            ("lowest", lambda x: x["whole"]["lowest_equity"]), ("fees", lambda x: x["whole"]["fees"]),
                            ("funding", lambda x: x["whole"]["funding_paid"]), ("joined", lambda x: x["whole"]["joined"]),
                            ("trimmed", lambda x: x["whole"]["trimmed"]), ("not joined", lambda x: x["whole"]["not_joined"]),
                            ("worst day %", lambda x: x["whole"]["worst_day_pct"]),
                            ("month-starts +100% first", lambda x: x["months"]["up"]),
                            ("month-starts -50% first", lambda x: x["months"]["down"] + x["months"]["wiped"]),
                            ("month-starts neither", lambda x: x["months"]["neither"])):
                va, vb = ga(a), ga(b)
                L.append("| %s | %s | %s | %s | %s |" % (sz_word[sk], lab, "%.1f" % va if isinstance(va, float) else va,
                                                          "%.1f" % vb if isinstance(vb, float) else vb,
                                                          "%+.1f" % (vb - va)))
        L += ["", "H63 trades: %d; H73 current-rule trades: %d." % (h63r["trades"], res["trades"]["b_targets"]), ""]
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits-dir", default=os.path.join(ROOT, "research", "out", "h60_regime_exits", "fits_today"))
    ap.add_argument("--report", action="store_true", help="write report.md again from results.json; computes nothing")
    a = ap.parse_args(argv)
    if a.report:
        with open(os.path.join(OUT, "results.json")) as fh:
            write_report(json.load(fh))
        return
    run(a.fits_dir)


if __name__ == "__main__":
    main()
