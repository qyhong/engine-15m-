# -*- coding: utf-8 -*-
"""playbook2_study -- history of the batch-2 strategy books (engine15/playbook2.py), after costs.

    py -3 research/playbook2_study.py          -> research/out/playbook2.md and .json

P3 opening range breakout (H8), P4 S&P overnight gap fill (H9), P5 squeeze breakout (H10), on every
market each applies to, from 2019 to the newest bar, split into a first and a second half at the
midpoint of that span (the same date for every market).

THE LUCK RULE. Every variant run is counted and listed. The variant to register is chosen on the FIRST
half only, by one score fixed before the run: the mean, over the book's markets, of each market's
average R after costs, among variants with at least MIN_H1 first-half trades on every market. P3 and P5
are chosen in two stages: stage 1 runs the base grid (no filter); stage 2 adds each filter, one at a
time, to the stage-1 winner, and a filter is kept only if it lifts the first-half score (eligibility
MIN_H1_FILTER trades a market). P4 is one grid. The second half of the registered variant is
reported untouched; nothing is re-chosen after looking at it.

One market at a time (memory): the bars of one market are loaded, every variant run, only the trade
results kept, then the next market.
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine15 import data  # noqa: E402
from engine15 import playbook2 as pb  # noqa: E402

OUT_DIR = os.path.join(ROOT, "research", "out")
START = "2019-01-01"
MIN_H1 = 30
MIN_H1_FILTER = 20
BOOK_ORDER = ("p3_orb", "p4_gapfill", "p5_squeeze")


def log(*a):
    print(*a, flush=True)


def peak_mb():
    """Peak working set of this process in MB (Windows), else None."""
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t), ("a", ctypes.c_size_t), ("b", ctypes.c_size_t),
                        ("c", ctypes.c_size_t), ("d", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        h = ctypes.windll.kernel32.GetCurrentProcess()
        ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb)
        return round(pmc.PeakWorkingSetSize / 2**20)
    except Exception:
        return None


# ---------------------------------------------------------------- running variants
def trades_of(book, ctx, p):
    """-> compact closed-trade arrays of one variant on one market."""
    S, T = pb.run(book, ctx, p)
    cl = T["status"] == pb.ST_CLOSED
    k = T["k"][cl]
    i = S["i"][k]
    with np.errstate(invalid="ignore", divide="ignore"):
        risk_usd = pb.STAKE * T["risk"][cl] / T["entry"][cl]
        r_gross = T["gross"][cl] / risk_usd
    return {"ms": ctx.ms[i + 1].astype("int64"), "r": T["r"][cl], "rg": r_gross, "pnl": T["pnl"][cl],
            "fees": T["fees"][cl], "lab": S["lab"][k].astype(int), "why": T["why"][cl].astype(int)}


def _max_dd(r):
    if not len(r):
        return 0.0
    eq = np.concatenate([[0.0], np.cumsum(r)])
    return float((np.maximum.accumulate(eq) - eq).max())


def stats(t, mask, months):
    r, pnl = t["r"][mask], t["pnl"][mask]
    n = int(len(r))
    if not n:
        return {"trades": 0}
    win, loss = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    return {"trades": n, "win_pct": round(100.0 * float(np.mean(pnl > 0)), 1), "avg_r": round(float(r.mean()), 3),
            "avg_r_before_costs": round(float(np.mean(t["rg"][mask])), 3),
            "pf": round(float(win / loss), 2) if loss > 0 else None, "exp_usd": round(float(pnl.mean()), 2),
            "net_usd": round(float(pnl.sum()), 2), "fees_usd": round(float(t["fees"][mask].sum()), 2),
            "max_dd_r": round(_max_dd(r), 2), "per_month": round(n / months, 2) if months > 0 else None}


def halves(t, split_ms, span):
    first_ms, last_ms = span
    m1 = max((split_ms - first_ms) / (30.44 * pb.DAY_MS), 1e-9)
    m2 = max((last_ms - split_ms) / (30.44 * pb.DAY_MS), 1e-9)
    return stats(t, t["ms"] < split_ms, m1), stats(t, t["ms"] >= split_ms, m2)


def score(per_asset, half, min_trades):
    """Mean over markets of the half's average R; None when a market has fewer than min_trades."""
    vals = []
    for st in per_asset.values():
        s = st[half]
        if s.get("trades", 0) < min_trades:
            return None
        vals.append(s["avg_r"])
    return round(float(np.mean(vals)), 4) if vals else None


def pooled(per_asset, half):
    vals = [st[half]["avg_r"] for st in per_asset.values() if st[half].get("trades", 0)]
    return round(float(np.mean(vals)), 4) if vals else None


# ---------------------------------------------------------------- the passes
def load_ctx(asset):
    df = data.load(asset)
    df = df[df.index >= pd.Timestamp(START, tz="UTC")]
    return pb.Ctx(df, asset)


def run_pass(jobs, store, spans):
    """jobs: {book: [params, ...]}. Runs every job on every market the book applies to, one market at a time."""
    for asset in pb.ASSETS:
        wanted = [(b, p) for b, ps in jobs.items() for p in ps if asset in pb.BOOKS[b]["assets"]]
        if not wanted:
            continue
        t0 = time.time()
        ctx = load_ctx(asset)
        spans[asset] = (int(ctx.ms[0]), int(ctx.ms[-1]) + pb.BAR_MS)
        for b, p in wanted:
            store.setdefault((b, pb.vname(b, p)), {"book": b, "params": p, "trades": {}})["trades"][asset] = trades_of(b, ctx, p)
        log("  %s: %d variants in %.1fs" % (asset, len(wanted), time.time() - t0))
        del ctx


def summarise(store, split_ms, spans):
    for v in store.values():
        v["per_asset"] = dict((a, dict(zip(("h1", "h2"), halves(t, split_ms, spans[a])))) for a, t in v["trades"].items())


def choose(cands, min_trades):
    best, best_s = None, None
    for v in cands:
        s = score(v["per_asset"], "h1", min_trades)
        if s is not None and (best_s is None or s > best_s):
            best, best_s = v, s
    if best is None:                                                 # nothing eligible: the best of what there is
        best = max(cands, key=lambda v: pooled(v["per_asset"], "h1") or -9e9)
        best_s = pooled(best["per_asset"], "h1")
    return best, best_s


def by_session(book, v, split_ms):
    out = {}
    for a, t in v["trades"].items():
        labs = pb.labels_for(book, a)
        rows = {}
        for li, lab in enumerate(labs):
            m = t["lab"] == li
            if not m.any():
                continue
            rows[lab] = {}
            for half, hm in (("h1", t["ms"] < split_ms), ("h2", t["ms"] >= split_ms)):
                s = stats(t, m & hm, 1.0)
                rows[lab][half] = {k: s.get(k) for k in ("trades", "win_pct", "avg_r")}
        out[a] = rows
    return out


# ---------------------------------------------------------------- the report
def _f(v, fmt="%.2f"):
    return "-" if v is None else fmt % v


def table_registered(v):
    lines = ["| Market | Half | Trades | Win % | Avg R | Avg R before costs | PF | Expectancy $ | Net $ | Max DD (R) | Trades/month |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for a in pb.ASSETS:
        if a not in v["per_asset"]:
            continue
        for half, name in (("h1", "first"), ("h2", "second")):
            s = v["per_asset"][a][half]
            if not s.get("trades"):
                lines.append("| %s | %s | 0 | | | | | | | | |" % (pb.SHORT_NAME[a], name))
                continue
            lines.append("| %s | %s | %d | %.1f | %+.3f | %+.3f | %s | %+.2f | %+.0f | %.1f | %.1f |" % (
                pb.SHORT_NAME[a], name, s["trades"], s["win_pct"], s["avg_r"], s["avg_r_before_costs"], _f(s["pf"]),
                s["exp_usd"], s["net_usd"], s["max_dd_r"], s["per_month"]))
    return lines


def table_variants(vs, top=None):
    lines = ["| Variant | Stage | First-half score | Second-half score | First-half trades (min market) |",
             "|---|---|---|---|---|"]
    rows = sorted(vs, key=lambda v: -(pooled(v["per_asset"], "h1") or -9e9))
    for v in rows[:top] if top else rows:
        mins = min(st["h1"].get("trades", 0) for st in v["per_asset"].values())
        lines.append("| %s | %s | %s | %s | %d |" % (v["name"], v["stage"], _f(pooled(v["per_asset"], "h1"), "%+.3f"),
                                                    _f(pooled(v["per_asset"], "h2"), "%+.3f"), mins))
    return lines


def table_sessions(sess):
    lines = ["| Market | Session | First half: trades / win % / avg R | Second half: trades / win % / avg R |", "|---|---|---|---|"]
    for a in pb.ASSETS:
        for lab, h in sess.get(a, {}).items():
            cell = lambda s: "-" if not s or not s.get("trades") else "%d / %.1f / %+.3f" % (s["trades"], s["win_pct"], s["avg_r"])  # noqa: E731
            lines.append("| %s | %s | %s | %s |" % (pb.SHORT_NAME[a], lab, cell(h.get("h1")), cell(h.get("h2"))))
    return lines


def verdict(v):
    h2 = [(a, st["h2"]) for a, st in v["per_asset"].items() if st["h2"].get("trades")]
    pos = [a for a, s in h2 if s["avg_r"] > 0]
    pre = [a for a, s in h2 if s["avg_r_before_costs"] > 0]
    sc2 = pooled(v["per_asset"], "h2")
    if sc2 is None:
        return "no second-half trades."
    if not pos:
        word = "DOES NOT CLEAR COSTS in the second half on any market"
    elif sc2 <= 0:
        word = "does not clear costs overall in the second half (positive after costs only on %s)" % ", ".join(pb.SHORT_NAME[a] for a in pos)
    else:
        word = "is positive after costs in the second half on %s" % ", ".join(pb.SHORT_NAME[a] for a in pos)
    return "%s; before costs it was positive on %s. Mean second-half avg R across markets %+.3f." % (
        word, ", ".join(pb.SHORT_NAME[a] for a in pre) or "none", sc2)


def main():
    t0 = time.time()
    store, spans = {}, {}
    log("pass 1: base grids")
    run_pass({"p3_orb": pb.ORB_GRID, "p4_gapfill": pb.GAP_GRID, "p5_squeeze": pb.SQ_GRID}, store, spans)
    last_ms = max(s[1] for s in spans.values())
    start_ms = int(pd.Timestamp(START, tz="UTC").value // 10**6)
    split_ms = start_ms + (last_ms - start_ms) // 2
    split = str(pd.Timestamp(split_ms, unit="ms", tz="UTC"))[:10]
    summarise(store, split_ms, spans)
    for (b, name), v in store.items():
        v["name"], v["stage"] = name, "base"

    chosen = {}
    base_orb, s_orb = choose([v for v in store.values() if v["book"] == "p3_orb"], MIN_H1)
    base_sq, s_sq = choose([v for v in store.values() if v["book"] == "p5_squeeze"], MIN_H1)
    gap_best, s_gap = choose([v for v in store.values() if v["book"] == "p4_gapfill"], MIN_H1)
    log("stage-1 winners: ORB %s (%s), squeeze %s (%s), gap %s (%s)" % (base_orb["name"], s_orb, base_sq["name"], s_sq,
                                                                        gap_best["name"], s_gap))
    log("pass 2: filters on the stage-1 winners")
    jobs = {"p3_orb": [dict(base_orb["params"], filter=f) for f in pb.ORB_FILTERS],
            "p5_squeeze": [dict(base_sq["params"], filter=f) for f in pb.SQ_FILTERS]}
    store2 = {}
    run_pass(jobs, store2, spans)
    summarise(store2, split_ms, spans)
    for (b, name), v in store2.items():
        v["name"], v["stage"] = name, "filter"
    store.update(store2)

    for book, base, base_s in (("p3_orb", base_orb, s_orb), ("p5_squeeze", base_sq, s_sq)):
        best, best_s = base, score(base["per_asset"], "h1", MIN_H1_FILTER)
        for v in store2.values():
            if v["book"] != book:
                continue
            s = score(v["per_asset"], "h1", MIN_H1_FILTER)
            if s is not None and best_s is not None and s > best_s:
                best, best_s = v, s
        chosen[book] = best
    chosen["p4_gapfill"] = gap_best

    out = {"generated_utc": str(pd.Timestamp.now(tz="UTC"))[:19], "start": START, "split": split,
           "end": str(pd.Timestamp(last_ms, unit="ms", tz="UTC"))[:16], "min_h1": MIN_H1, "min_h1_filter": MIN_H1_FILTER,
           "score": "mean over markets of first-half average R after costs", "books": {}}
    md = ["# Batch-2 strategy books: history study (P3 ORB, P4 S&P gap fill, P5 squeeze)", "",
          "Generated by `research/playbook2_study.py` on %s UTC. Paper only. History can reject a rule, never prove one." % out["generated_utc"],
          "", "- Span: %s to %s; **first half before %s, second half from it** (same date for every market)." % (START, out["end"], split),
          "- Costs: each market's own fee a side (crypto 0.10%, gold 0.02%, silver 0.03%, USDJPY 0.01%, S&P 0.02%), "
          "$10,000 a trade; R = result after costs / the dollar distance to the stop.",
          "- Choice rule (fixed before the run): highest mean over markets of first-half avg R, every market with at least "
          "%d first-half trades (filters: %d). The registered variant's second half is shown untouched." % (MIN_H1, MIN_H1_FILTER), ""]
    total = 0
    for book in BOOK_ORDER:
        vs = [v for v in store.values() if v["book"] == book]
        total += len(vs)
        reg = chosen[book]
        sess = by_session(book, reg, split_ms)
        match = pb.vname(book, pb.RULES[book]) == reg["name"]
        out["books"][book] = {
            "title": pb.BOOKS[book]["title"], "hypothesis": pb.BOOKS[book]["hypothesis"], "variants_run": len(vs),
            "registered": reg["name"], "registered_params": reg["params"], "rules_match_module": match,
            "registered_per_asset": reg["per_asset"], "by_session": sess,
            "registered_score_h1": pooled(reg["per_asset"], "h1"), "registered_score_h2": pooled(reg["per_asset"], "h2"),
            "variants": [{"name": v["name"], "stage": v["stage"], "params": v["params"], "per_asset": v["per_asset"],
                          "score_h1": pooled(v["per_asset"], "h1"), "score_h2": pooled(v["per_asset"], "h2")} for v in vs]}
        n_pos1 = sum(1 for v in vs if (pooled(v["per_asset"], "h1") or -1) > 0)
        n_pos2 = sum(1 for v in vs if (pooled(v["per_asset"], "h2") or -1) > 0)
        n_both = sum(1 for v in vs if (pooled(v["per_asset"], "h1") or -1) > 0 and (pooled(v["per_asset"], "h2") or -1) > 0)
        md += ["## %s (%s), %s" % (pb.BOOKS[book]["title"], pb.BOOKS[book]["hypothesis"], book), "",
               "**Registered variant:** `%s`%s" % (reg["name"], "" if match else "  (WARNING: engine15/playbook2.py RULES differ: update them)"),
               "", "Rule: %s" % pb.rule_text(book, reg["params"]), "",
               "**Verdict:** the registered variant %s" % verdict(reg), "",
               "Variants run: **%d** (counted). Mean avg R across markets positive in the first half: %d; in the second "
               "half: %d; in both: %d." % (len(vs), n_pos1, n_pos2, n_both), ""]
        md += table_registered(reg) + ["", "By session (registered variant):", ""] + table_sessions(sess)
        md += ["", "Every variant (score = mean over markets of avg R after costs; sorted by first half):", ""]
        md += table_variants(vs) + [""]
    out["variants_total"] = total
    md.insert(7, "- **Variants run in all: %d** (P3 %d, P4 %d, P5 %d). Count them all when judging any result here." % (
        total, out["books"]["p3_orb"]["variants_run"], out["books"]["p4_gapfill"]["variants_run"],
        out["books"]["p5_squeeze"]["variants_run"]))
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "playbook2.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x))
    with open(os.path.join(OUT_DIR, "playbook2.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    for book in BOOK_ORDER:
        b = out["books"][book]
        log("%s registered %s (module match: %s) h1 %s h2 %s" % (book, b["registered"], b["rules_match_module"],
                                                                 b["registered_score_h1"], b["registered_score_h2"]))
    log("done in %.0fs; %d variants; peak memory %s MB" % (time.time() - t0, total, peak_mb()))


if __name__ == "__main__":
    main()
