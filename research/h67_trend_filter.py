# -*- coding: utf-8 -*-
"""H67: the Setups rule with a 30-day trend filter, replayed against the current rule. Research only; registered in
research/HYPOTHESES.md before any number. Both books are the engine's own shadows.run. Reads the evidence store and the
cached fits; changes nothing.

    python research/h67_trend_filter.py --fits-dir <fits_today>
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

OUT = os.path.join(ROOT, "research", "out", "h67_trend_filter")
GROUPS = [("crypto", ["BTCUSDT", "ETHUSDT"]), ("metals", ["XAUUSD", "XAGUSD"]), ("fx", ["USDJPY"]), ("index", ["SPX"]),
          ("energy", ["WTI", "BRENT"])]
VAULT = ("BTCUSDT", "ETHUSDT")
CUTS = (("mid", "2023-06-08"), ("holdout", "2025-11-11"), ("forward", "2026-11-11"))
BOOKS = (("current", None), ("trend30", 30), ("trend20", 20), ("trend45", 45))
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
            for name, days in BOOKS:
                rule = base_rule if days is None else dict(base_rule, trend_days=days)
                b = shadows.run(inp["px"], inp["odds"], inp["shock"], inp["tide"], inp["unit"], cfg, lo, n, bias=inp["bias"],
                                guard=inp["guard"], rule=rule, aux=aux, times_ms=tms, row_of=row_of)
                if name == "trend30":                              # the engine's own book must be this very rule
                    ref = shadows.run_challenger("b_trend30", prep, a, lo, n, aux=aux)
                    assert len(ref["trades"]) == len(b["trades"]) and np.allclose(ref["equity"][lo:n], b["equity"][lo:n])
                out["books"][name] = {"all": seg(b, times, lo, n), "h1": seg(b, times, lo, idx["mid"]),
                                      "h2": seg(b, times, idx["mid"], n), "holdout": seg(b, times, idx["holdout"], n),
                                      "forward": seg(b, times, idx["forward"], n), "worst_fall": fall(b["equity"][lo:n])}
                curves[name][a] = pd.Series(b["equity"][lo:n], index=times[lo:n])
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
    c, f = res["pooled"]["current"], res["pooled"]["trend30"]
    vc, vf_ = res["vault"]["current"], res["vault"]["trend30"]
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


def write_report(res):
    names = {"current": "current rule", "trend30": "30-day filter", "trend20": "20-day filter", "trend45": "45-day filter"}
    L = ["# H67: the Setups rule with a 30-day trend filter", "",
         "History replay, both books run by the engine's own code. Registered before any number. The filter was found on",
         "this same history (H65), so this replay cannot validate it; the forward shadow book `b_trend30` is the test.",
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
    L += ["", "## Per market (all: trades, won, mean R, sum R, net, flat; worst fall)", "",
          "| Market | current rule | 30-day filter | 20-day | 45-day |", "|---|---|---|---|---|"]
    for a, m in res["markets"].items():
        L.append("| %s | %s | %s | %s | %s |" % tuple([a] + ["%s; %.1f%%" % (_c(m["books"][k]["all"]), m["books"][k]["worst_fall"])
                                                             for k in names]))
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits-dir", required=True)
    run(ap.parse_args(argv).fits_dir)


if __name__ == "__main__":
    main()
