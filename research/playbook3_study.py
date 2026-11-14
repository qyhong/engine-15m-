# -*- coding: utf-8 -*-
"""playbook3_study -- history of the batch-3 strategy books (engine15/playbook3.py), before and after costs.

    py -3 research/playbook3_study.py          -> research/out/playbook3.md and .json

P6 VWAP reversion / reclaim (H11), P7 session plays (H12), P8 fair value gap / order block (H13), P9 crypto
liquidation cascades (H14), P10 round-number magnets (H15), P11 release-day trades beyond CPI (H16), P12
crypto opening range at the US equity open (H17), on every market each applies to, from 2019 to the newest
bar, split into a first and a second half at the midpoint of that span (the same date for every market).

THE LUCK RULE. Every variant run is counted and listed. The variant to register is chosen on the FIRST half
only, by one score fixed before the run: the mean, over the markets the variant trades, of each market's
average R after costs, among variants with at least MIN_H1 first-half trades on every market (if none is
eligible: the best of all). Books with sub-plays choose the best variant of each sub-play, then:
  P6   register both modes (fade, reclaim) if both first-half scores are positive, else the better one;
  P7   register the sub-plays (London false move, Asian-range breakout, New York drift) with a positive
       first-half score, at most two; if none is positive, the single best;
  P9   stage 1 = the base grid; stage 2 adds the funding filter to each mode's winner (kept if it lifts the
       first-half score); then the mode with the better first-half score;
  P10  the mode (magnet, reject) with the better first-half score;
  P11  the calendar on file starts in May 2026, so there is NO first half: the variants are compared on every
       release on file (in-sample, a handful of cases) and the better one is registered, graded forward only;
  P12  not chosen: the one rule where the lead was found (playbook2's P3 rule at the US open); its history
       is reported as "where it was found" and its verdict is purely forward.
The second half of each registered variant is reported untouched; nothing is re-chosen after looking at it.

One market at a time (memory): the bars of one market are loaded, every variant run, only the trade results
kept, then the next market.
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
from engine15 import playbook3 as pb  # noqa: E402

OUT_DIR = os.path.join(ROOT, "research", "out")
START = "2019-01-01"
MIN_H1 = 30
MIN_H1_FILTER = 20
BOOK_ORDER = ("p6_vwap", "p7_session", "p8_fvg", "p9_cascade", "p10_round", "p11_release", "p12_orb_us")


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
    """-> compact closed-trade arrays of one variant (or registered rule) on one market."""
    S, T = pb.run(book, ctx, p)
    cl = T["status"] == pb.ST_CLOSED
    k = T["k"][cl]
    i = S["i"][k]
    with np.errstate(invalid="ignore", divide="ignore"):
        risk_usd = pb.STAKE * T["risk"][cl] / T["entry"][cl]
        r_gross = T["gross"][cl] / risk_usd
    return {"ms": ctx.ms[i + 1].astype("int64"), "r": T["r"][cl].astype(float), "rg": r_gross.astype(float),
            "pnl": T["pnl"][cl].astype(float), "gross": T["gross"][cl].astype(float), "fees": T["fees"][cl].astype(float),
            "lab": S["lab"][k].astype(int), "why": T["why"][cl].astype(int)}


def _max_dd(r):
    if not len(r):
        return 0.0
    eq = np.concatenate([[0.0], np.cumsum(r)])
    return float((np.maximum.accumulate(eq) - eq).max())


def _pf(x):
    win, loss = x[x > 0].sum(), -x[x < 0].sum()
    return round(float(win / loss), 2) if loss > 0 else None


def stats(t, mask, months):
    r, pnl, gross = t["r"][mask], t["pnl"][mask], t["gross"][mask]
    n = int(len(r))
    if not n:
        return {"trades": 0}
    return {"trades": n, "win_pct": round(100.0 * float(np.mean(pnl > 0)), 1),
            "win_pct_before_costs": round(100.0 * float(np.mean(gross > 0)), 1),
            "avg_r": round(float(r.mean()), 3), "avg_r_before_costs": round(float(np.mean(t["rg"][mask])), 3),
            "pf": _pf(pnl), "pf_before_costs": _pf(gross), "exp_usd": round(float(pnl.mean()), 2),
            "exp_usd_before_costs": round(float(gross.mean()), 2),
            "net_usd": round(float(pnl.sum()), 2), "fees_usd": round(float(t["fees"][mask].sum()), 2),
            "fees_r": round(float(np.mean(t["rg"][mask] - r)), 3),
            "max_dd_r": round(_max_dd(r), 2), "per_month": round(n / months, 2) if months > 0 else None}


def halves(t, split_ms, span):
    first_ms, last_ms = span
    m1 = max((split_ms - first_ms) / (30.44 * pb.DAY_MS), 1e-9)
    m2 = max((last_ms - split_ms) / (30.44 * pb.DAY_MS), 1e-9)
    mall = max((last_ms - first_ms) / (30.44 * pb.DAY_MS), 1e-9)
    return (stats(t, t["ms"] < split_ms, m1), stats(t, t["ms"] >= split_ms, m2),
            stats(t, np.ones(len(t["ms"]), dtype=bool), mall))


def score(per_asset, half, min_trades):
    """Mean over markets of the half's average R; None when a market has fewer than min_trades."""
    vals = []
    for st in per_asset.values():
        s = st[half]
        if s.get("trades", 0) < min_trades:
            return None
        vals.append(s["avg_r"])
    return round(float(np.mean(vals)), 4) if vals else None


def pooled(per_asset, half, key="avg_r"):
    vals = [st[half][key] for st in per_asset.values() if st[half].get("trades", 0)]
    return round(float(np.mean(vals)), 4) if vals else None


# ---------------------------------------------------------------- the passes
def load_ctx(asset):
    df = data.load(asset)
    df = df[df.index >= pd.Timestamp(START, tz="UTC")]
    return pb.Ctx(df, asset)


def run_pass(jobs, store, spans, stage):
    """jobs: [(book, params or rule list, name), ...]. Runs every job on every market it applies to, one market at a time."""
    for asset in pb.ASSETS:
        wanted = []
        for b, p, name in jobs:
            ps = p if isinstance(p, list) else [p]
            if any(pb.applies(b, q, asset) for q in ps):
                wanted.append((b, p, name))
        if not wanted:
            continue
        t0 = time.time()
        ctx = load_ctx(asset)
        spans[asset] = (int(ctx.ms[0]), int(ctx.ms[-1]) + pb.BAR_MS)
        for b, p, name in wanted:
            v = store.setdefault((b, name), {"book": b, "params": p, "name": name, "stage": stage, "trades": {}})
            v["trades"][asset] = trades_of(b, ctx, p)
        log("  %s: %d jobs in %.1fs (peak %s MB)" % (asset, len(wanted), time.time() - t0, peak_mb()))
        del ctx


def summarise(store, split_ms, spans):
    for v in store.values():
        if "per_asset" in v:
            continue
        v["per_asset"] = dict((a, dict(zip(("h1", "h2", "all"), halves(t, split_ms, spans[a]))))
                              for a, t in v["trades"].items())


def choose(cands, min_trades, half="h1"):
    best, best_s = None, None
    for v in cands:
        s = score(v["per_asset"], half, min_trades)
        if s is not None and (best_s is None or s > best_s):
            best, best_s = v, s
    if best is None:                                                 # nothing eligible: the best of what there is
        best = max(cands, key=lambda v: pooled(v["per_asset"], half) if pooled(v["per_asset"], half) is not None else -9e9)
        best_s = pooled(best["per_asset"], half)
    return best, best_s


def by_label(book, v, split_ms):
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
                rows[lab][half] = {k: s.get(k) for k in ("trades", "win_pct", "avg_r", "avg_r_before_costs")}
        out[a] = rows
    return out


# ---------------------------------------------------------------- the report
def _f(v, fmt="%.2f"):
    return "-" if v is None else fmt % v


def table_registered(v, halves_=(("h1", "first"), ("h2", "second"))):
    lines = ["| Market | Half | Trades | Win % | Avg R before costs | Avg R after costs | Fees (R/trade) | PF before / after | "
             "Expectancy $ before / after | Net $ | Max DD (R) | Trades/month |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for a in pb.ASSETS:
        if a not in v["per_asset"]:
            continue
        for half, name in halves_:
            s = v["per_asset"][a][half]
            if not s.get("trades"):
                lines.append("| %s | %s | 0 | | | | | | | | | |" % (pb.SHORT_NAME[a], name))
                continue
            lines.append("| %s | %s | %d | %.1f | %+.3f | %+.3f | %.3f | %s / %s | %+.2f / %+.2f | %+.0f | %.1f | %.1f |" % (
                pb.SHORT_NAME[a], name, s["trades"], s["win_pct"], s["avg_r_before_costs"], s["avg_r"], s["fees_r"],
                _f(s["pf_before_costs"]), _f(s["pf"]), s["exp_usd_before_costs"], s["exp_usd"], s["net_usd"], s["max_dd_r"],
                s["per_month"]))
    return lines


def table_variants(vs, half_names=("h1", "h2")):
    lines = ["| Variant | Stage | First-half score (after / before costs) | Second-half score (after / before costs) | "
             "First-half trades (min market) |", "|---|---|---|---|---|"]
    rows = sorted(vs, key=lambda v: -(pooled(v["per_asset"], half_names[0]) or -9e9))
    for v in rows:
        mins = min(st[half_names[0]].get("trades", 0) for st in v["per_asset"].values()) if v["per_asset"] else 0
        lines.append("| %s | %s | %s / %s | %s / %s | %d |" % (
            v["name"], v["stage"], _f(pooled(v["per_asset"], "h1"), "%+.3f"),
            _f(pooled(v["per_asset"], "h1", "avg_r_before_costs"), "%+.3f"), _f(pooled(v["per_asset"], "h2"), "%+.3f"),
            _f(pooled(v["per_asset"], "h2", "avg_r_before_costs"), "%+.3f"), mins))
    return lines


def table_labels(sess, title="Session"):
    lines = ["| Market | %s | First half: trades / win %% / avg R after (before) costs | Second half: trades / win %% / avg R after "
             "(before) costs |" % title, "|---|---|---|---|"]
    cell = lambda s: "-" if not s or not s.get("trades") else "%d / %.1f / %+.3f (%+.3f)" % (   # noqa: E731
        s["trades"], s["win_pct"], s["avg_r"], s["avg_r_before_costs"])
    for a in pb.ASSETS:
        for lab, h in sess.get(a, {}).items():
            lines.append("| %s | %s | %s | %s |" % (pb.SHORT_NAME[a], lab, cell(h.get("h1")), cell(h.get("h2"))))
    return lines


def verdict(v, half="h2"):
    h2 = [(a, st[half]) for a, st in v["per_asset"].items() if st[half].get("trades")]
    pos = [a for a, s in h2 if s["avg_r"] > 0]
    pre = [a for a, s in h2 if s["avg_r_before_costs"] > 0]
    sc2 = pooled(v["per_asset"], half)
    if sc2 is None:
        return "no trades in that span."
    if not pos:
        word = "DOES NOT CLEAR COSTS on any market"
    elif sc2 <= 0:
        word = "does not clear costs overall (positive after costs only on %s)" % ", ".join(pb.SHORT_NAME[a] for a in pos)
    else:
        word = "is positive after costs on %s" % ", ".join(pb.SHORT_NAME[a] for a in pos)
    return "%s; before costs it was positive on %s. Mean avg R across markets %+.3f after costs, %+.3f before." % (
        word, ", ".join(pb.SHORT_NAME[a] for a in pre) or "none", sc2, pooled(v["per_asset"], half, "avg_r_before_costs"))


def main():
    t0 = time.time()
    store, spans = {}, {}
    log("pass 1: base grids")
    jobs = [(b, p, pb.vname(b, p)) for b in BOOK_ORDER for p in pb.GRIDS[b]]
    run_pass(jobs, store, spans, "base")
    last_ms = max(s[1] for s in spans.values())
    start_ms = int(pd.Timestamp(START, tz="UTC").value // 10**6)
    split_ms = start_ms + (last_ms - start_ms) // 2
    split = str(pd.Timestamp(split_ms, unit="ms", tz="UTC"))[:10]
    summarise(store, split_ms, spans)

    def group(book, g):
        return [v for v in store.values() if v["book"] == book and pb.group_of(book, v["params"]) == g and v["stage"] != "registered"]

    # ---- stage 2: P9's funding filter on each mode's winner
    casc_best = {}
    for g in ("cont", "bounce"):
        casc_best[g] = choose(group("p9_cascade", g), MIN_H1)
    log("pass 2: P9 funding filter on %s" % ", ".join(v["name"] for v, _s in casc_best.values()))
    jobs2 = [("p9_cascade", dict(v["params"], filter=f), pb.vname("p9_cascade", dict(v["params"], filter=f)))
             for v, _s in casc_best.values() for f in pb.CASC_FILTERS]
    store2 = {}
    run_pass(jobs2, store2, spans, "filter")
    summarise(store2, split_ms, spans)
    store.update(store2)

    # ---- the choices (first half only; P11 on everything on file)
    chosen, notes = {}, {}
    parts = {}
    for book in BOOK_ORDER:
        if book == "p6_vwap":
            fb, fs = choose(group(book, "fade"), MIN_H1)
            rb, rs = choose(group(book, "reclaim"), MIN_H1)
            if (fs or -1) > 0 and (rs or -1) > 0:
                parts[book] = [fb, rb]
            else:
                parts[book] = [fb if (fs if fs is not None else -9) >= (rs if rs is not None else -9) else rb]
            notes[book] = "best fade %s (%s); best reclaim %s (%s)" % (fb["name"], fs, rb["name"], rs)
        elif book == "p7_session":
            best = [(g,) + choose(group(book, g), MIN_H1) for g in ("judas", "abo", "drift")]
            pos = sorted([b for b in best if (b[2] or -1) > 0], key=lambda b: -b[2])[:2]
            if not pos:
                pos = [max(best, key=lambda b: b[2] if b[2] is not None else -9)]
            parts[book] = [b[1] for b in pos]
            notes[book] = "; ".join("best %s %s (%s)" % (g, v["name"], s) for g, v, s in best)
        elif book == "p8_fvg":
            parts[book] = [choose(group(book, "all"), MIN_H1)[0]]
        elif book == "p9_cascade":
            fin = []
            for g in ("cont", "bounce"):
                base, base_s = casc_best[g]
                best, best_s = base, score(base["per_asset"], "h1", MIN_H1_FILTER)
                for v in store2.values():
                    if pb.group_of(book, v["params"]) != g:
                        continue
                    s = score(v["per_asset"], "h1", MIN_H1_FILTER)
                    if s is not None and best_s is not None and s > best_s:
                        best, best_s = v, s
                fin.append((g, best, pooled(best["per_asset"], "h1")))
            parts[book] = [max(fin, key=lambda b: b[2] if b[2] is not None else -9)[1]]
            notes[book] = "; ".join("best %s %s (%s)" % (g, v["name"], s) for g, v, s in fin)
        elif book == "p10_round":
            mb, ms_ = choose(group(book, "magnet"), MIN_H1)
            rj, rs = choose(group(book, "reject"), MIN_H1)
            parts[book] = [mb if (ms_ if ms_ is not None else -9) >= (rs if rs is not None else -9) else rj]
            notes[book] = "best magnet %s (%s); best reject %s (%s)" % (mb["name"], ms_, rj["name"], rs)
        elif book == "p11_release":
            parts[book] = [choose([v for v in store.values() if v["book"] == book], 0, half="all")[0]]
        else:
            parts[book] = [v for v in store.values() if v["book"] == book]

    # ---- the registered rules as books (several parts share one-trade-at-a-time): one more pass, not a variant
    jobs3 = []
    for book in BOOK_ORDER:
        ps = [v["params"] for v in parts[book]]
        if len(ps) > 1:
            jobs3.append((book, ps, "REGISTERED: " + " + ".join(v["name"] for v in parts[book])))
    store3 = {}
    if jobs3:
        log("pass 3: registered multi-part rules")
        run_pass(jobs3, store3, spans, "registered")
        summarise(store3, split_ms, spans)
    for book in BOOK_ORDER:
        if len(parts[book]) > 1:
            chosen[book] = [v for v in store3.values() if v["book"] == book][0]
        else:
            chosen[book] = parts[book][0]

    out = {"generated_utc": str(pd.Timestamp.now(tz="UTC"))[:19], "start": START, "split": split,
           "end": str(pd.Timestamp(last_ms, unit="ms", tz="UTC"))[:16], "min_h1": MIN_H1, "min_h1_filter": MIN_H1_FILTER,
           "score": "mean over markets of first-half average R after costs", "books": {}}
    md = ["# Batch-3 strategy books: history study (P6-P12)", "",
          "Generated by `research/playbook3_study.py` on %s UTC. Paper only. History can reject a rule, never prove one." % out["generated_utc"],
          "", "- Span: %s to %s; **first half before %s, second half from it** (same date for every market)." % (START, out["end"], split),
          "- Costs: each market's own fee a side (crypto 0.10%, gold 0.02%, silver 0.03%, USDJPY 0.01%, S&P 0.02%), "
          "$10,000 a trade; R = result / the dollar distance to the stop. 'Before costs' = the same trades with no fee.",
          "- Choice rule (fixed before the run): highest mean over markets of first-half avg R after costs, every market with at least "
          "%d first-half trades (filters: %d); sub-play rules in the script's docstring. The registered variant's second half is "
          "shown untouched." % (MIN_H1, MIN_H1_FILTER), ""]
    total = 0
    for book in BOOK_ORDER:
        vs = [v for v in store.values() if v["book"] == book and v["stage"] != "registered"]
        total += len(vs)
        reg = chosen[book]
        sess = by_label(book, reg, split_ms)
        reg_params = [v["params"] for v in parts[book]]
        match = [pb.vname(book, q) for q in reg_params] == [pb.vname(book, q) for q in pb.RULES[book]]
        b = {"title": pb.BOOKS[book]["title"], "hypothesis": pb.BOOKS[book]["hypothesis"], "variants_run": len(vs),
             "registered": [v["name"] for v in parts[book]], "registered_params": reg_params, "rules_match_module": match,
             "registered_per_asset": reg["per_asset"], "by_label": sess, "note": notes.get(book),
             "registered_score_h1": pooled(reg["per_asset"], "h1"), "registered_score_h2": pooled(reg["per_asset"], "h2"),
             "registered_score_h1_before_costs": pooled(reg["per_asset"], "h1", "avg_r_before_costs"),
             "registered_score_h2_before_costs": pooled(reg["per_asset"], "h2", "avg_r_before_costs"),
             "variants": [{"name": v["name"], "stage": v["stage"], "params": v["params"], "per_asset": v["per_asset"],
                           "score_h1": pooled(v["per_asset"], "h1"), "score_h2": pooled(v["per_asset"], "h2"),
                           "score_all": pooled(v["per_asset"], "all")} for v in vs]}
        out["books"][book] = b
        n_pos1 = sum(1 for v in vs if (pooled(v["per_asset"], "h1") or -1) > 0)
        n_pos2 = sum(1 for v in vs if (pooled(v["per_asset"], "h2") or -1) > 0)
        n_both = sum(1 for v in vs if (pooled(v["per_asset"], "h1") or -1) > 0 and (pooled(v["per_asset"], "h2") or -1) > 0)
        md += ["## %s (%s), %s" % (pb.BOOKS[book]["title"], pb.BOOKS[book]["hypothesis"], book), "",
               "**Registered:** %s%s" % (" + ".join("`%s`" % v["name"] for v in parts[book]),
                                         "" if match else "  (WARNING: engine15/playbook3.py RULES differ: update them)"), "",
               "Rule: %s" % pb.rule_text(book, reg_params), ""]
        if notes.get(book):
            md += ["Sub-play winners on the first half: %s." % notes[book], ""]
        if book == "p11_release":
            md += ["**Few cases.** The release calendar on file starts in May 2026, so every release is in the second half and "
                   "there is no first half to choose on. The registered variant was the better one on ALL releases on file "
                   "(in-sample); it is graded forward only.", "",
                   "**On every release on file:** the registered variant %s" % verdict(reg, "all"), ""]
            md += table_registered(reg, (("all", "all on file"),)) + ["", "By kind of release:", ""] + table_labels(sess, "Kind")
        else:
            if book == "p12_orb_us":
                md += ["**Where it was found.** This rule was FOUND in this history (the playbook2 session breakdown), so the numbers "
                       "below are not evidence for it: they are where the lead came from. One variant, nothing chosen. Its verdict "
                       "is purely forward.", ""]
            md += ["**Verdict (second half):** the registered rule %s" % verdict(reg), ""]
            md += table_registered(reg) + ["", "By %s (registered rule):" % ("sub-play" if book == "p7_session" else "UTC session"),
                                           ""] + table_labels(sess, "Sub-play" if book == "p7_session" else "Session")
        md += ["", "Variants run: **%d** (counted). Mean avg R after costs across markets positive in the first half: %d; in the "
               "second half: %d; in both: %d." % (len(vs), n_pos1, n_pos2, n_both), "",
               "Every variant (score = mean over the markets it trades of avg R; sorted by first half after costs):", ""]
        md += table_variants(vs) + [""]
        if book == "p11_release":
            md += ["(P11 scores on every release on file: %s)" % "; ".join(
                "%s %+.3f" % (v["name"], pooled(v["per_asset"], "all") or 0) for v in vs), ""]
    out["variants_total"] = total
    md.insert(7, "- **Variants run in all: %d** (%s). Count them all when judging any result here." % (
        total, ", ".join("%s %d" % (b.split("_")[0].upper(), out["books"][b]["variants_run"]) for b in BOOK_ORDER)))
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "playbook3.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x))
    with open(os.path.join(OUT_DIR, "playbook3.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    for book in BOOK_ORDER:
        b = out["books"][book]
        log("%s registered %s (module match: %s) h1 %s h2 %s (before costs %s / %s)" % (
            book, b["registered"], b["rules_match_module"], b["registered_score_h1"], b["registered_score_h2"],
            b["registered_score_h1_before_costs"], b["registered_score_h2_before_costs"]))
        if b.get("note"):
            log("   ", b["note"])
    log("done in %.0fs; %d variants; peak memory %s MB" % (time.time() - t0, total, peak_mb()))


if __name__ == "__main__":
    main()
