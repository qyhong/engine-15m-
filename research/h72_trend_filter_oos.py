# -*- coding: utf-8 -*-
"""H72: out-of-sample test of the H67 trend filter (length chosen on 2020-2023 only) and the H68 wait after a stop-out,
with a paired, month-clustered bootstrap. Research only; registered in research/HYPOTHESES.md before any number. Every
book is the engine's own shadows.run, called as research/h67_trend_filter.py and research/h68_wait_after_stop.py call
it. Reads the evidence store and the cached fits; changes nothing.

Stages, in this order, each writing its file before the next may start:
  choice  runs the current rule and the seven lengths ONLY on bars before the TEST start; writes choice.json
  test    needs choice.json; runs the frozen rules (A: filter N*, B: wait, C: both) on all bars; writes results.json
  sens    needs results.json; the registered descriptive table, all seven N on every period; writes sensitivity.json
  report  writes report.md from the three files

    python research/h72_trend_filter_oos.py --fits-dir <fits_today> [--stage all|choice|test|sens|report]
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

OUT = os.path.join(ROOT, "research", "out", "h72_trend_filter_oos")
GROUPS = [("crypto", ["BTCUSDT", "ETHUSDT"]), ("metals", ["XAUUSD", "XAGUSD"]), ("fx", ["USDJPY"]), ("index", ["SPX"]),
          ("energy", ["WTI", "BRENT"])]
VAULT = ("BTCUSDT", "ETHUSDT")
TEST_START, HOLD_START = "2023-06-08", "2025-11-11"
PERIODS = ("choice", "test", "holdout")
GRID = (10, 15, 20, 30, 45, 60, 90)
B_DRAWS, SEED = 10000, 72
START = shadows.START_EQUITY


def path(name):
    return os.path.join(OUT, name)


def groups(fits_root, log):
    """Yield (prep, times, tms, n, asset, lo, inp, cfg, aux, row_of) per market, one group's prep at a time."""
    import h59_half_be as h59
    import h62_setups_wide_stop as h62
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
            yield prep, times, tms, n, a, lo, inp, cfg, aux, row_of
        del prep


def book(inp, cfg, aux, row_of, tms, lo, hi, extra):
    rule = dict(shadows.CHALLENGERS["b_targets"]["rule"], **extra)
    return shadows.run(inp["px"], inp["odds"], inp["shock"], inp["tide"], inp["unit"], cfg, lo, hi, bias=inp["bias"],
                       guard=inp["guard"], rule=rule, aux=aux, times_ms=tms, row_of=row_of)


def trades_of(b, times):
    """Closed trades: entry time, R, won."""
    tr = b["trades"]
    t = pd.DatetimeIndex(times[tr.i_in.values.astype(int)]) if len(tr) else pd.DatetimeIndex([], tz="UTC")
    return pd.DataFrame({"t": t, "r": tr.r_mult.values.astype(float), "won": (tr.pnl_usd.values > 0)})


# ---------------------------------------------------------------- stage 1: the choice, on bars before TEST only
def stage_choice(fits_root, log):
    res = {"grid": list(GRID), "test_start": TEST_START, "markets": {}}
    for prep, times, tms, n, a, lo, inp, cfg, aux, row_of in groups(fits_root, log):
        hi = int(times.searchsorted(pd.Timestamp(TEST_START, tz="UTC")))   # the run ends here: no later bar is read
        m = {"window": [str(times[lo])[:16], str(times[hi - 1])[:16]], "sum_r": {}, "trades": {}}
        for name, extra in [("current", {})] + [("trend%d" % d, {"trend_days": d}) for d in GRID]:
            b = book(inp, cfg, aux, row_of, tms, lo, hi, extra)
            r = b["trades"].r_mult.values.astype(float)
            r = r[np.isfinite(r)]
            m["sum_r"][name], m["trades"][name] = float(r.sum()), int(len(r))
        res["markets"][a] = m
        log("choice %s: %s" % (a, ", ".join("%s %+.1f" % kv for kv in m["sum_r"].items())))
    names = ["current"] + ["trend%d" % d for d in GRID]
    pooled = dict((k, sum(m["sum_r"][k] for m in res["markets"].values())) for k in names)
    vault = dict((k, sum(res["markets"][a]["sum_r"][k] for a in VAULT)) for k in names)
    ok = [d for d in GRID if pooled["trend%d" % d] > pooled["current"] and vault["trend%d" % d] > vault["current"]]
    chosen = None
    if ok:
        best = max(pooled["trend%d" % d] for d in ok)
        chosen = max(d for d in ok if pooled["trend%d" % d] == best)      # exact ties: the longer N
    res.update(pooled=pooled, vault=vault, qualified=ok, chosen_n=chosen)
    os.makedirs(OUT, exist_ok=True)
    with open(path("choice.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    log("CHOICE: qualified %s -> chosen N = %s" % (ok, chosen))
    return res


# ---------------------------------------------------------------- statistics
def months_of(t0, t1):
    return pd.period_range(t0.tz_convert(None).to_period("M"), t1.tz_convert(None).to_period("M"), freq="M")


def monthly(tr, months):
    """Sum of R and count per calendar month (all months of the period, 0 where none)."""
    if len(tr):
        k = tr.t.dt.tz_convert(None).dt.to_period("M")
        s = tr.r.groupby(k).sum().reindex(months, fill_value=0.0).values
        c = tr.r.groupby(k).size().reindex(months, fill_value=0).values
    else:
        s, c = np.zeros(len(months)), np.zeros(len(months))
    return s.astype(float), c.astype(float)


def boot_mean(d):
    rng = np.random.default_rng(SEED)
    d = np.asarray(d, dtype=float)
    draws = d[rng.integers(0, len(d), (B_DRAWS, len(d)))].mean(axis=1)
    return {"months": int(len(d)), "mean": float(d.mean()), "lo": float(np.percentile(draws, 2.5)),
            "hi": float(np.percentile(draws, 97.5)), "p": float((1 + (draws <= 0).sum()) / (1.0 + B_DRAWS)),
            "months_up": int((d > 0).sum()), "months_down": int((d < 0).sum())}


def boot_ratio(s, c):
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(s), (B_DRAWS, len(s)))
    ss, cc = s[idx].sum(axis=1), c[idx].sum(axis=1)
    rr = ss[cc > 0] / cc[cc > 0]
    return (float(np.percentile(rr, 2.5)), float(np.percentile(rr, 97.5))) if len(rr) else (None, None)


def fall(e):
    e = e[np.isfinite(e)]
    return float(np.min(e / np.maximum.accumulate(e) - 1.0) * 100.0) if len(e) else 0.0


def bounds(times):
    t0 = times[0]
    return {"choice": (t0, pd.Timestamp(TEST_START, tz="UTC")),
            "test": (pd.Timestamp(TEST_START, tz="UTC"), pd.Timestamp(HOLD_START, tz="UTC")),
            "holdout": (pd.Timestamp(HOLD_START, tz="UTC"), None)}


def full_books(fits_root, log, names_extra, check_wait=False):
    """Run each named book over all bars per market. -> per market: {name: {"tr", "eq", "held"}, "times", "lo"}."""
    out = {}
    for prep, times, tms, n, a, lo, inp, cfg, aux, row_of in groups(fits_root, log):
        m = {"times": times[lo:n], "books": {}}
        for name, extra in names_extra:
            b = book(inp, cfg, aux, row_of, tms, lo, n, extra)
            if check_wait and name == "wait":                  # the engine's own b_wait_stop must be this very rule
                ref = shadows.run_challenger("b_wait_stop", prep, a, lo, n, aux=aux)
                assert len(ref["trades"]) == len(b["trades"]) and np.allclose(ref["equity"][lo:n], b["equity"][lo:n])
            m["books"][name] = {"tr": trades_of(b, times), "eq": b["equity"][lo:n], "held": b["held"][lo:n]}
        out[a] = m
        log("ran %s: %s" % (a, ", ".join("%s %d" % (k, len(v["tr"])) for k, v in m["books"].items())))
    return out


def read_period(runs, assets, name, base, per):
    """Book `name` against `base` over the assets in period `per`."""
    t_first = min(runs[a]["times"][0] for a in assets)
    t_last = max(runs[a]["times"][-1] for a in assets)
    b0, b1 = bounds(pd.DatetimeIndex([t_first]))[per]
    b1 = b1 or (t_last + pd.Timedelta(minutes=1))
    months = months_of(max(b0, t_first), min(b1, t_last + pd.Timedelta(minutes=1)) - pd.Timedelta(minutes=1))
    S, C, S0, C0, W, eqs, flats = 0, 0, 0, 0, 0, [], []
    for a in assets:
        r = runs[a]
        for nm, acc in ((name, "new"), (base, "base")):
            tr = r["books"][nm]["tr"]
            tr = tr[(tr.t >= b0) & (tr.t < b1)]
            s, c = monthly(tr, months)
            if acc == "new":
                S, C, W = S + s, C + c, W + int(tr.won.sum())
            else:
                S0, C0 = S0 + s, C0 + c
        msk = (r["times"] >= b0) & (r["times"] < b1)
        flats.append(float((r["books"][name]["held"][msk] == 0).mean() * 100) if msk.any() else float("nan"))
        eqs.append(pd.Series(r["books"][name]["eq"], index=r["times"]))
    tot = pd.concat(eqs, axis=1).sort_index().ffill().fillna(START).sum(axis=1)
    tot = tot[(tot.index >= b0) & (tot.index < b1)]
    nt = int(np.sum(C))
    lo_, hi_ = boot_ratio(np.asarray(S, float), np.asarray(C, float))
    return {"trades": nt, "won": (W / nt * 100) if nt else None, "sum_r": float(np.sum(S)),
            "mean_r": float(np.sum(S) / nt) if nt else None, "mean_r_lo": lo_, "mean_r_hi": hi_,
            "flat_pct": float(np.nanmean(flats)), "worst_fall": fall(tot.values),
            "base_sum_r": float(np.sum(S0)), "diff": boot_mean(np.asarray(S, float) - np.asarray(S0, float))}


SETS = (("vault", VAULT), ("all8", None), ("others", "others"))


def set_assets(runs, spec):
    if spec is None:
        return list(runs)
    if spec == "others":
        return [a for a in runs if a not in VAULT]
    return [a for a in spec if a in runs]


def holm(ps):
    keys = sorted(ps, key=lambda k: ps[k])
    m, out, run = len(keys), {}, 0.0
    for j, k in enumerate(keys):
        run = max(run, min(1.0, (m - j) * ps[k]))
        out[k] = run
    return out


# ---------------------------------------------------------------- stage 2: the frozen rules
def stage_test(fits_root, log):
    if not os.path.exists(path("choice.json")):
        raise SystemExit("choice.json missing: run the choice stage first")
    ch = json.load(open(path("choice.json")))
    n_star = ch["chosen_n"]
    rules = [("current", {}), ("wait", {"wait_after_stop": True})]
    if n_star is not None:
        rules += [("filter", {"trend_days": n_star}), ("both", {"trend_days": n_star, "wait_after_stop": True})]
    runs = full_books(fits_root, log, rules, check_wait=True)
    res = {"chosen_n": n_star, "frozen": [k for k, _e in rules if k != "current"], "read": {}, "current": {}}
    for k in res["frozen"]:
        res["read"][k] = dict((s, dict((p, read_period(runs, set_assets(runs, spec), k, "current", p)) for p in PERIODS))
                              for s, spec in SETS)
    res["current"] = dict((s, dict((p, read_period(runs, set_assets(runs, spec), "current", "current", p))
                                   for p in PERIODS)) for s, spec in SETS)
    ps = dict((k, res["read"][k]["vault"]["test"]["diff"]["p"]) for k in res["frozen"])
    adj = holm(ps)
    res["verdict"] = {}
    for k in res["frozen"]:
        v, a8 = res["read"][k]["vault"], res["read"][k]["all8"]
        res["verdict"][k] = {
            "test_vault_mean_d": v["test"]["diff"]["mean"], "p_raw": ps[k], "p_holm": adj[k], "m": len(ps),
            "raw_below_0.05/3": ps[k] < 0.05 / 3, "test_all8_mean_d": a8["test"]["diff"]["mean"],
            "pass": bool(v["test"]["diff"]["mean"] > 0 and adj[k] < 0.05 and a8["test"]["diff"]["mean"] >= 0),
            "holds_in_holdout": bool(v["holdout"]["diff"]["mean"] > 0)}
    res["markets"] = dict((a, dict((k, int(len(r["books"][k]["tr"]))) for k in r["books"])) for a, r in runs.items())
    with open(path("results.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=str)
    log("VERDICT: %s" % json.dumps(res["verdict"]))
    return res


# ---------------------------------------------------------------- stage 3: descriptive sensitivity (no choice)
def stage_sens(fits_root, log):
    if not os.path.exists(path("results.json")):
        raise SystemExit("results.json missing: the frozen rules must be written first")
    runs = full_books(fits_root, log, [("current", {})] + [("trend%d" % d, {"trend_days": d}) for d in GRID])
    res = {"note": "descriptive only; not used for any choice", "rows": {}}
    for d in GRID:
        k = "trend%d" % d
        res["rows"][k] = dict((s, dict((p, read_period(runs, set_assets(runs, spec), k, "current", p)) for p in PERIODS))
                              for s, spec in SETS[:2])
    with open(path("sensitivity.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=str)
    log("sensitivity written")
    return res


# ---------------------------------------------------------------- report
def _d(x):
    d = x["diff"]
    return "%+.2f [%+.2f, %+.2f], p %.4f, %d mo" % (d["mean"], d["lo"], d["hi"], d["p"], d["months"])


def _b(x):
    if not x["trades"]:
        return "0 trades"
    return "%d, %.0f%%, %+.3f [%+.3f, %+.3f], %+.1fR, flat %.0f%%, fall %.1f%%" % (
        x["trades"], x["won"], x["mean_r"], x["mean_r_lo"], x["mean_r_hi"], x["sum_r"], x["flat_pct"], x["worst_fall"])


def stage_report(log):
    ch = json.load(open(path("choice.json")))
    rs = json.load(open(path("results.json")))
    sn = json.load(open(path("sensitivity.json"))) if os.path.exists(path("sensitivity.json")) else None
    names = {"filter": "A: trend filter N=%s" % rs["chosen_n"], "wait": "B: wait after a stop",
             "both": "C: both (N=%s + wait)" % rs["chosen_n"]}
    L = ["# H72: out-of-sample test of the trend filter and the wait after a stop-out", "",
         "Registered in research/HYPOTHESES.md before any number. The IDEAS were found on all the data (H65); only the",
         "length was chosen here, on CHOICE (to 2023-06-07) only. TEST 2023-06-08 to 2025-11-10; HOLDOUT 2025-11-11 on.", "",
         "## Part A: the choice (CHOICE period, books run only to the TEST start)", "",
         "| Book | 8 markets sum R | BTC+ETH sum R |", "|---|---|---|"]
    for k in ["current"] + ["trend%d" % d for d in GRID]:
        L.append("| %s | %+.1f | %+.1f |" % (k, ch["pooled"][k], ch["vault"][k]))
    L += ["", "Qualified (beat the current rule on both): %s. **Chosen N = %s.**" % (ch["qualified"], ch["chosen_n"]), "",
          "## Verdicts on TEST (registered pass rule)", "",
          "| Rule | BTC+ETH mean monthly d (R) | p raw | p Holm (m=%d) | raw < 0.05/3 | 8-market mean d | PASS | Holds in holdout |"
          % len(rs["frozen"]), "|---|---|---|---|---|---|---|---|"]
    for k in rs["frozen"]:
        v = rs["verdict"][k]
        L.append("| %s | %+.2f | %.4f | %.4f | %s | %+.2f | **%s** | %s |" % (
            names[k], v["test_vault_mean_d"], v["p_raw"], v["p_holm"], "yes" if v["raw_below_0.05/3"] else "no",
            v["test_all8_mean_d"], "PASS" if v["pass"] else "FAIL", "yes" if v["holds_in_holdout"] else "no"))
    L += ["", "## Paired monthly difference against the current rule (mean R per month, 95% month-clustered interval, one-sided p)",
          "", "| Rule | Markets | CHOICE | TEST | HOLDOUT |", "|---|---|---|---|---|"]
    for k in rs["frozen"]:
        for s, t in (("vault", "BTC+ETH"), ("all8", "8 markets"), ("others", "other six")):
            x = rs["read"][k][s]
            L.append("| %s | %s | %s | %s | %s |" % (names[k], t, _d(x["choice"]), _d(x["test"]), _d(x["holdout"])))
    L += ["", "## Each book by period (trades, won, mean R [95% interval], sum R, flat, worst fall of summed equity)", "",
          "| Book | Markets | CHOICE | TEST | HOLDOUT |", "|---|---|---|---|---|"]
    for k, title in [("current", "current rule")] + [(k, names[k]) for k in rs["frozen"]]:
        src = rs["current"] if k == "current" else rs["read"][k]
        for s, t in (("vault", "BTC+ETH"), ("all8", "8 markets"), ("others", "other six")):
            L.append("| %s | %s | %s | %s | %s |" % (title, t, _b(src[s]["choice"]), _b(src[s]["test"]), _b(src[s]["holdout"])))
    if sn:
        L += ["", "## Descriptive only, NOT used for any choice: every length against the current rule", "",
              "Cells: sum of R (current rule's in brackets); mean monthly d [95% interval], p.", "",
              "| N | Markets | CHOICE | TEST | HOLDOUT |", "|---|---|---|---|---|"]
        for d in GRID:
            for s, t in (("vault", "BTC+ETH"), ("all8", "8 markets")):
                x = sn["rows"]["trend%d" % d][s]
                L.append("| %d | %s | %s |" % (d, t, " | ".join("%+.1f (%+.1f); %s" % (x[p]["sum_r"], x[p]["base_sum_r"], _d(x[p]))
                                                              for p in PERIODS)))
    with open(path("report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")
    log("report written")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits-dir", required=True)
    ap.add_argument("--stage", default="all", choices=("all", "choice", "test", "sens", "report"))
    a = ap.parse_args(argv)
    t0 = time.time()
    log = lambda s: print("[%5.0fs] %s" % (time.time() - t0, s), flush=True)   # noqa: E731
    if a.stage in ("all", "choice"):
        stage_choice(a.fits_dir, log)
    if a.stage in ("all", "test"):
        stage_test(a.fits_dir, log)
    if a.stage in ("all", "sens"):
        stage_sens(a.fits_dir, log)
    if a.stage in ("all", "report"):
        stage_report(log)


if __name__ == "__main__":
    main()
