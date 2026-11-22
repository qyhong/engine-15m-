# -*- coding: utf-8 -*-
"""H68: the Setups rule that waits for a real signal after a stop-out, replayed against the current rule (and, as a
descriptive extra, together with the H67 30-day trend filter). Research only; registered in
research/HYPOTHESES.md before any number. Both books are the engine's own shadows.run. Reads the evidence store and the
cached fits; changes nothing.

    python research/h68_wait_after_stop.py --fits-dir <fits_today>
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

from engine15 import data, shadows  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "h68_wait_after_stop")
GROUPS = [("crypto", ["BTCUSDT", "ETHUSDT"]), ("metals", ["XAUUSD", "XAGUSD"]), ("fx", ["USDJPY"]), ("index", ["SPX"]),
          ("energy", ["WTI", "BRENT"])]
VAULT = ("BTCUSDT", "ETHUSDT")
CUTS = (("mid", "2023-06-08"), ("holdout", "2025-11-11"), ("forward", "2026-11-11"))
BOOKS = (("current", {}), ("wait", {"wait_after_stop": True}),
         ("both", {"wait_after_stop": True, "trend_days": 30}))          # both: descriptive only, not a live book
START = shadows.START_EQUITY


def seg(book, times, a, z):
    """Read-outs of one book over bars a .. z-1 (trades by entry time)."""
    tr = book["trades"]
    tr = tr[(tr.i_in >= a) & (tr.i_in < z)]
    r = tr.r_mult.values.astype(float)
    r = r[np.isfinite(r)]
    eq = book["equity"]
    base = eq[a - 1] if a > 0 and np.isfinite(eq[a - 1]) else START
    return {"trades": int(len(tr)), "won": float((tr.pnl_usd > 0).mean() * 100) if len(tr) else None,
            "sum_r": float(r.sum()), "mean_r": float(r.mean()) if len(r) else None,
            "net": float(eq[z - 1] - base), "flat_pct": float((book["held"][a:z] == 0).mean() * 100)}


def waits(tr, end_ms):
    """Hours from each exit at the entry stop ("STOP") to the next entry; the last one, if nothing followed, is open."""
    rows = list(tr.itertuples())
    done = [(t.t_in_ms - p.t_out_ms) / 3600000.0 for p, t in zip(rows, rows[1:]) if p.why_out == "STOP"]
    still = (end_ms - rows[-1].t_out_ms) / 3600000.0 if rows and rows[-1].why_out == "STOP" else None
    return {"n": len(done), "median": float(np.median(done)) if done else None, "max": float(max(done)) if done else None,
            "open": still, "list": [float(x) for x in done]}


def forced_after_stop(tr, a, z):
    """The current rule's trades entered by force right after a trade ended at "STOP" (by entry bar in a .. z-1)."""
    rows = list(tr.itertuples())
    r = np.array([t.r_mult for p, t in zip(rows, rows[1:]) if p.why_out == "STOP" and t.why_in == "FORCED" and a <= t.i_in < z],
                 dtype=float)
    r = r[np.isfinite(r)]
    return {"trades": int(len(r)), "mean_r": float(r.mean()) if len(r) else None, "sum_r": float(r.sum()),
            "won": float((r > 0).mean() * 100) if len(r) else None}


def fall(eq):
    e = eq[np.isfinite(eq)]
    return float(np.min(e / np.maximum.accumulate(e) - 1.0) * 100.0) if len(e) else 0.0


def run(fits_root, log=print):
    import h59_half_be as h59
    import h62_setups_wide_stop as h62
    t0 = time.time()
    res = {"markets": {}, "curves": {}}
    curves = dict((k, {}) for k, _d in BOOKS)                     # book -> market -> marked equity
    for g, assets in GROUPS:
        prep = h59.prep_cut(g, assets, os.path.join(fits_root, g), h62.group_end(g, assets), log=log)
        times = prep["times"]
        tms = data.to_ms(times)
        n = len(times)
        for a in assets:
            ok = np.isfinite(prep["odds"][a][:, 0])
            lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
            aux = shadows.aux_from_ev(prep["ev"][a], prep["px"][a])
            inp = shadows.book_inputs(prep, a)
            cfg = shadows.asset_cfg(a, dict(prep["cfg"]))
            tgt = aux["targets"]
            row_of = lambda k, tgt=tgt: tgt.iloc[k] if len(tgt.columns) else pd.Series(dtype=float)   # noqa: E731
            idx = dict((k, min(max(int(times.searchsorted(pd.Timestamp(d, tz="UTC"))), lo + 1), n - 1)) for k, d in CUTS)
            out = {"window": [str(times[lo])[:16], str(times[n - 1])[:16]], "books": {}}
            base_rule = dict(shadows.CHALLENGERS["b_targets"]["rule"])
            for name, extra in BOOKS:
                rule = dict(base_rule, **extra)
                b = shadows.run(inp["px"], inp["odds"], inp["shock"], inp["tide"], inp["unit"], cfg, lo, n, bias=inp["bias"],
                                guard=inp["guard"], rule=rule, aux=aux, times_ms=tms, row_of=row_of)
                if name == "wait":                                 # the engine's own book must be this very rule
                    ref = shadows.run_challenger("b_wait_stop", prep, a, lo, n, aux=aux)
                    assert len(ref["trades"]) == len(b["trades"]) and np.allclose(ref["equity"][lo:n], b["equity"][lo:n])
                out["books"][name] = {"all": seg(b, times, lo, n), "h1": seg(b, times, lo, idx["mid"]),
                                      "h2": seg(b, times, idx["mid"], n), "holdout": seg(b, times, idx["holdout"], n),
                                      "forward": seg(b, times, idx["forward"], n), "worst_fall": fall(b["equity"][lo:n])}
                curves[name][a] = pd.Series(b["equity"][lo:n], index=times[lo:n])
                out["books"][name]["waits_h"] = waits(b["trades"], tms[n - 1])
                if "wait_stop" in b["state"]:
                    out["books"][name]["withheld"] = dict(b["state"]["wait_stop"])
                if name == "current":
                    out["forced_after_stop"] = dict((p_, forced_after_stop(b["trades"], z0, z1)) for p_, z0, z1 in (
                        ("all", lo, n), ("h1", lo, idx["mid"]), ("h2", idx["mid"], n), ("holdout", idx["holdout"], n),
                        ("forward", idx["forward"], n)))
            res["markets"][a] = out
            log("%s: %s (%.0fs)" % (a, "; ".join("%s %d trades, %+.1fR, net %+.0f" % (
                k, out["books"][k]["all"]["trades"], out["books"][k]["all"]["sum_r"], out["books"][k]["all"]["net"])
                for k, _d in BOOKS), time.time() - t0))
        del prep

    def pool(name, part, assets=None):
        ms = [m for a, m in res["markets"].items() if assets is None or a in assets]
        tr = sum(m["books"][name][part]["trades"] for m in ms)
        sr = sum(m["books"][name][part]["sum_r"] for m in ms)
        won = sum((m["books"][name][part]["won"] or 0) * m["books"][name][part]["trades"] for m in ms)
        return {"trades": tr, "sum_r": sr, "mean_r": sr / tr if tr else None, "won": won / tr if tr else None,
                "net": sum(m["books"][name][part]["net"] for m in ms),
                "flat_pct": float(np.mean([m["books"][name][part]["flat_pct"] for m in ms]))}
    res["pooled"], res["vault"], res["others"] = {}, {}, {}
    for name, _d in BOOKS:
        res["pooled"][name] = dict((p, pool(name, p)) for p in ("all", "h1", "h2", "holdout", "forward"))
        res["vault"][name] = dict((p, pool(name, p, VAULT)) for p in ("all", "h1", "h2", "holdout", "forward"))
        res["others"][name] = dict((p, pool(name, p, [a for a in res["markets"] if a not in VAULT]))
                                   for p in ("all", "h1", "h2", "holdout", "forward"))
        for key, assets in (("pooled", None), ("vault", VAULT), ("others", [a for a in res["markets"] if a not in VAULT])):
            cs = [v for a, v in curves[name].items() if assets is None or a in assets]
            tot = pd.concat(cs, axis=1).sort_index().ffill().fillna(START).sum(axis=1)
            res[key][name]["worst_fall"] = fall(tot.values)      # the books' marked equity summed
    for key, assets in (("pooled", None), ("vault", VAULT), ("others", [a for a in res["markets"] if a not in VAULT])):
        ms = [m for a, m in res["markets"].items() if assets is None or a in assets]
        fa = {}
        for p_ in ("all", "h1", "h2", "holdout", "forward"):
            tr = sum(m["forced_after_stop"][p_]["trades"] for m in ms)
            sr = sum(m["forced_after_stop"][p_]["sum_r"] for m in ms)
            won = sum((m["forced_after_stop"][p_]["won"] or 0) * m["forced_after_stop"][p_]["trades"] for m in ms)
            fa[p_] = {"trades": tr, "sum_r": sr, "mean_r": sr / tr if tr else None, "won": won / tr if tr else None}
        res[key]["forced_after_stop"] = fa
        for name in ("wait", "both"):
            w = [x for m in ms for x in m["books"][name]["waits_h"]["list"]]
            res[key][name]["waits_h"] = {"n": len(w), "median": float(np.median(w)) if w else None,
                                         "max": float(max(w)) if w else None}
            res[key][name]["withheld"] = dict((k, sum(m["books"][name]["withheld"][k] for m in ms))
                                              for k in ("episodes", "blocked"))
    c, f = res["pooled"]["current"], res["pooled"]["wait"]
    vc, vf_ = res["vault"]["current"], res["vault"]["wait"]
    checks = {"pooled_sum_r_h1": f["h1"]["sum_r"] > c["h1"]["sum_r"], "pooled_sum_r_h2": f["h2"]["sum_r"] > c["h2"]["sum_r"],
              "vault_sum_r_h1": vf_["h1"]["sum_r"] > vc["h1"]["sum_r"], "vault_sum_r_h2": vf_["h2"]["sum_r"] > vc["h2"]["sum_r"],
              "mean_r_positive_h1": (f["h1"]["mean_r"] or 0) > 0, "mean_r_positive_h2": (f["h2"]["mean_r"] or 0) > 0,
              "worst_fall_not_deeper": f["worst_fall"] >= c["worst_fall"]}
    res["checks"], res["survives"] = checks, all(checks.values())
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "results.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    write_report(res)
    log("checks: %s -> %s" % (checks, "SURVIVES AS A RULE" if res["survives"] else "does not survive as a rule"))
    return res


def _c(p):
    return "-" if not p.get("trades") else "%d, %.0f%%, %+.3f, %+.1f, %+.0f, flat %.0f%%" % (
        p["trades"], p["won"] or 0, p["mean_r"] or 0, p["sum_r"], p["net"], p["flat_pct"])


def _h(x):
    return "-" if x is None else "%.1f" % x


def _f(p):
    return "-" if not p["trades"] else "%d, %.0f%%, %+.3f, %+.1f" % (p["trades"], p["won"] or 0, p["mean_r"] or 0, p["sum_r"])


def write_report(res):
    names = {"current": "current rule", "wait": "wait after a stop", "both": "both (wait + 30-day filter; descriptive)"}
    L = ["# H68: the Setups rule that waits for a real signal after a stop-out", "",
         "History replay, every book run by the engine's own code. Registered before any number. The idea was found on",
         "this same history (H65, H66), so this replay cannot validate it; the forward shadow book `b_wait_stop` is the test.",
         "Every cell: trades, share won, mean R, sum of R, paper net, share of bars flat (pooled: the markets' mean).", "",
         "## Verdict by the registered bar", "",
         ("**The pattern SURVIVES as a rule.**" if res["survives"] else "**The pattern DOES NOT SURVIVE as a rule.**")
         + " Checks: " + ", ".join("%s %s" % (k, "yes" if v else "NO") for k, v in res["checks"].items()) + "."]
    for title, key in (("All eight markets", "pooled"), ("BTC and ETH", "vault"), ("The other six", "others")):
        L += ["", "## %s" % title, "", "| Book | All | First half | Second half | Holdout | Forward | Worst fall |",
              "|---|---|---|---|---|---|---|"]
        for k, n_ in names.items():
            p = res[key][k]
            L.append("| %s | %s | %s | %s | %s | %s | %.1f%% |" % (
                n_, _c(p["all"]), _c(p["h1"]), _c(p["h2"]), _c(p["holdout"]), _c(p["forward"]), p["worst_fall"]))
    L += ["", "## Withheld forced entries and waits", "",
          "| Markets | Book | Stop-outs with a withheld forced entry | Sessions withheld | Waits after a stop: n, median h, longest h |",
          "|---|---|---|---|---|"]
    for title, key in (("All eight", "pooled"), ("BTC + ETH", "vault"), ("Other six", "others")):
        for k in ("wait", "both"):
            p = res[key][k]
            L.append("| %s | %s | %d | %d | %d, %s, %s |" % (title, names[k], p["withheld"]["episodes"], p["withheld"]["blocked"],
                                                          p["waits_h"]["n"], _h(p["waits_h"]["median"]), _h(p["waits_h"]["max"])))
    L += ["", "## What the withheld entries made in the current rule's record", "",
          "The current rule's trades entered by FORCE right after a trade ended at the entry stop: trades, share won, mean R, sum of R.",
          "", "| Markets | All | First half | Second half | Holdout | Forward |", "|---|---|---|---|---|---|"]
    for title, key in (("All eight", "pooled"), ("BTC + ETH", "vault"), ("Other six", "others")):
        fa = res[key]["forced_after_stop"]
        L.append("| %s | %s |" % (title, " | ".join(_f(fa[p_]) for p_ in ("all", "h1", "h2", "holdout", "forward"))))
    L += ["", "## Per market (all: trades, won, mean R, sum R, net, flat; worst fall)", "",
          "| Market | current rule | wait after a stop | both (descriptive) |", "|---|---|---|---|"]
    for a, m in res["markets"].items():
        L.append("| %s | %s | %s | %s |" % tuple([a] + ["%s; %.1f%%" % (_c(m["books"][k]["all"]), m["books"][k]["worst_fall"])
                                                       for k in names]))
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits-dir", required=True)
    run(ap.parse_args(argv).fits_dir)


if __name__ == "__main__":
    main()
