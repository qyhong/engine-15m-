# -*- coding: utf-8 -*-
"""L2 market-state map: sort every closed 15m bar into coarse states, measure what followed.

Six dimensions (discovery_lib.DIMS), each read at the bar's close from closed bars only:
volatility, 4h+daily trend, session, 4h order flow, place in the 24h range, last hour's move.
For every single state and every pair of dimensions, per coin and per half of history:
forward return over 1, 4 and 16 bars (entry at the next open), the 4h and 24h triple-barrier
trade (the engine's unit, 1.5 x ATR14 on 1h), count, independence-adjusted count, mean,
median, share up / down, t.

A cell is ranked only if it leans the SAME way in all four tests (BTC and ETH, first and second
half). Two lists: cells whose worst test still clears the 0.20% round-trip fee, and cells that are
consistent but too small to pay the fee on their own (candidates for a filter or timing rule).

Honesty (charter L4): the run counts every test it made, and re-runs the whole scan with the
states slid in time against the outcomes (a placebo: same states, same outcomes, no real link)
to show how many cells pass by luck alone.

    py -3 research/state_map.py               # writes research/out/state_map.json and .md
    py -3 research/state_map.py --placebo 10  # fewer placebo runs (faster)
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discovery_lib as L  # noqa: E402

from engine15.config import CFG  # noqa: E402

MIN_NEFF = 30          # every one of the four tests needs at least this many independent cases
T_CONSISTENT = 2.0     # "consistent" list: t >= 2 in every one of the four tests
T_FEE = 1.0            # "pays the fee" list: t >= 1 in every test and the worst mean clears the fee
RANK_METRICS = ("f4", "f16", "tb16", "tb96")


# ---------------------------------------------------------------- data
def pack(asset):
    """One asset -> only the small arrays the scan needs (the bars are dropped)."""
    b = L.build(asset)
    w = b["half"] > 0
    p = {"asset": asset, "times": b["df"].index[w], "thr": b["thr"],
         "start": b["start"], "mid": b["mid"], "end": b["end"],
         "half": b["half"][w].astype(np.int8),
         "st": dict((d, b["st"][d].values[w].astype(np.int8)) for d in L.DIM_NAMES),
         "y": dict((m, b["out"][m].values[w].astype(np.float32)) for m in L.METRICS),
         "cls": dict((h, b["out"]["y%d" % h].values[w].astype(np.int8)) for h in L.TB_H),
         "cuts": dict((d, [float(x) for x in b["thr"][d]]) for d in L.TERCILE_SOURCE)}
    p["pos"] = np.arange(len(p["half"]), dtype=np.int64)
    del b
    return p


# ---------------------------------------------------------------- the scan
def scan(packs, offset=0, full=False):
    """All cells x metrics x four tests. offset != 0 slides every state series by that many bars
    (the same for both coins) against the outcomes: the placebo.
    -> (results by grouping, pass counts, tests made)."""
    res = {}
    counts = {"consistent": 0, "pays_fee": 0}
    tests = 0
    cells = 0
    for dims in L.groupings():
        per = {}
        k = None
        for p in packs:
            st = p["st"] if offset == 0 else dict((d, np.roll(v, offset)) for d, v in p["st"].items())
            code, k = L.combo_codes(st, dims)
            code2 = np.where(code >= 0, code * 2 + (p["half"] - 1), -1)
            per[p["asset"]] = {}
            for m in L.METRICS:
                h = L.METRIC_H[m]
                n, neff, s, ss, up, dn = L.group_stats(code2, 2 * k, p["y"][m], p["pos"], h)
                mean, t = L.finish(n, neff, s, ss)
                d = {"n": n, "neff": neff, "mean": mean, "t": t, "up": up, "dn": dn}
                if full:
                    d["median"] = L.group_medians(code2, 2 * k, p["y"][m])
                    if m.startswith("tb"):
                        hh = int(m[2:])
                        cls = p["cls"][hh].astype(float)
                        valid = np.where(cls >= 0, 1.0, np.nan)
                        _, _, su, _, _, _ = L.group_stats(code2, 2 * k, (cls == 1) * valid, p["pos"], hh)
                        _, _, sd, _, _, _ = L.group_stats(code2, 2 * k, (cls == 2) * valid, p["pos"], hh)
                        d["tb_up"], d["tb_dn"] = su, sd
                per[p["asset"]][m] = dict((kk, vv.reshape(k, 2)) for kk, vv in d.items())
        res[dims] = per
        assets = [p["asset"] for p in packs]
        for m in RANK_METRICS:
            mean = np.stack([per[a][m]["mean"] for a in assets], axis=1)     # (k, coin, half)
            t = np.stack([per[a][m]["t"] for a in assets], axis=1)
            neff = np.stack([per[a][m]["neff"] for a in assets], axis=1)
            ok = (neff >= MIN_NEFF).all(axis=(1, 2))
            if m == RANK_METRICS[0]:
                cells += int(ok.sum())
            tests += 2 * int(ok.sum())
            for side in (1, -1):
                sm, stt = side * mean, side * t
                cons = ok & (sm > 0).all(axis=(1, 2)) & (stt >= T_CONSISTENT).all(axis=(1, 2))
                fee = ok & (sm - L.FEE_RT_PCT > 0).all(axis=(1, 2)) & (stt >= T_FEE).all(axis=(1, 2))
                counts["consistent"] += int(cons.sum())
                counts["pays_fee"] += int(fee.sum())
    return res, counts, tests, cells


def rank(res, assets):
    """-> list of candidate (cell, side, metric) rows that lean the same way in all four tests."""
    rows = []
    for dims, per in res.items():
        for m in RANK_METRICS:
            mean = np.stack([per[a][m]["mean"] for a in assets], axis=1)
            t = np.stack([per[a][m]["t"] for a in assets], axis=1)
            neff = np.stack([per[a][m]["neff"] for a in assets], axis=1)
            ok = (neff >= MIN_NEFF).all(axis=(1, 2))
            for side in (1, -1):
                sm, stt = side * mean, side * t
                same = ok & (sm > 0).all(axis=(1, 2))
                for code in np.where(same)[0]:
                    worst_net = float(sm[code].min() - L.FEE_RT_PCT)
                    min_t = float(stt[code].min())
                    rows.append({"dims": dims, "code": int(code), "cell": L.cell_name(dims, int(code)),
                                 "side": "LONG" if side == 1 else "SHORT", "metric": m,
                                 "worst_mean_pct": round(float(sm[code].min()), 4),
                                 "worst_net_pct": round(worst_net, 4), "min_t": round(min_t, 2),
                                 "pays_fee": bool(worst_net > 0 and min_t >= T_FEE),
                                 "consistent": bool(min_t >= T_CONSISTENT)})
    return rows


def slice_table(res, dims, code, assets):
    """-> {asset: {half: {metric: stats}}} for one cell (plain numbers for JSON / Markdown)."""
    out = {}
    per = res[dims]
    for a in assets:
        out[a] = {}
        for hi, hname in ((0, "first_half"), (1, "second_half")):
            row = {}
            for m in L.METRICS:
                d = per[a][m]
                n = int(d["n"][code, hi])
                r = {"n": n, "n_indep": int(d["neff"][code, hi]),
                     "mean_pct": _r(d["mean"][code, hi]), "t": _r(d["t"][code, hi], 2),
                     "share_up": _r(d["up"][code, hi] / n if n else np.nan, 3),
                     "share_down": _r(d["dn"][code, hi] / n if n else np.nan, 3)}
                if "median" in d:
                    r["median_pct"] = _r(d["median"][code, hi])
                if "tb_up" in d:
                    r["first_touch_up"] = _r(d["tb_up"][code, hi] / n if n else np.nan, 3)
                    r["first_touch_down"] = _r(d["tb_dn"][code, hi] / n if n else np.nan, 3)
                row[m] = r
            out[a][hname] = row
    return out


def _r(x, nd=4):
    x = float(x)
    return None if not np.isfinite(x) else round(x, nd)


# ---------------------------------------------------------------- plain English
PHRASE = {
    ("vol", "quiet"): "the market is quiet (last hour's 15m ranges in the bottom third against the past month)",
    ("vol", "normal"): "volatility is normal (middle third against the past month)",
    ("vol", "wild"): "the market is wild (last hour's 15m ranges in the top third against the past month)",
    ("trend", "up"): "the 4h and daily trends are both UP",
    ("trend", "down"): "the 4h and daily trends are both DOWN",
    ("trend", "mixed"): "the 4h and daily trends do not agree (or are not strong)",
    ("session", "Asia"): "it is the Asia session (bar closes 22:00-07:00 UTC, weekdays)",
    ("session", "London"): "it is the London session (07:00-12:00 UTC, weekdays)",
    ("session", "London+NY overlap"): "it is the London/New York overlap (12:00-16:00 UTC, weekdays)",
    ("session", "New York"): "it is the New York afternoon (16:00-22:00 UTC, weekdays)",
    ("session", "weekend"): "it is the weekend (Saturday or Sunday, UTC)",
    ("flow", "selling"): "takers have been net SELLERS over the last 4 hours (bottom third)",
    ("flow", "balanced"): "taker flow over the last 4 hours is balanced (middle third)",
    ("flow", "buying"): "takers have been net BUYERS over the last 4 hours (top third)",
    ("place", "near 24h low"): "price sits in the bottom third of its last-24h range",
    ("place", "middle of 24h range"): "price sits in the middle of its last-24h range",
    ("place", "near 24h high"): "price sits in the top third of its last-24h range",
    ("move", "fell"): "the last hour FELL (bottom third, in 1h-ATR units)",
    ("move", "flat"): "the last hour went roughly nowhere (middle third)",
    ("move", "rose"): "the last hour ROSE (top third, in 1h-ATR units)",
}


def describe(dims, code):
    return " and ".join(PHRASE[(d, lab)] for d, lab in L.decode(dims, code))


def md_cell(i, row, tab, assets, halves_txt):
    m = row["metric"]
    side = row["side"]
    lines = ["### %d. %s -> %s, judged over %s" % (i, row["cell"], side, L.METRIC_TEXT[m]), ""]
    sign = 1 if side == "LONG" else -1
    lines.append("**In plain words:** when %s, a %s entered at the next 15m open and judged over %s "
                 "made at least %+.3f%% a trade in every one of the four tests (two coins x two halves) "
                 "before fees; after the 0.20%% round-trip fee the worst test %s %+.3f%%. "
                 "The weakest test has t = %.1f." % (
                     describe(row["dims"], row["code"]), side, L.METRIC_TEXT[m], row["worst_mean_pct"],
                     "keeps" if row["worst_net_pct"] > 0 else "is at", row["worst_net_pct"], row["min_t"]))
    lines.append("")
    lines.append("| Coin | Half | Cases | Independent | Mean %s %% | Median %% | Share up | Share down | t | "
                 "24h barrier: up first / down first |" % ("(long)" if sign == 1 else "(price)"))
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for a in assets:
        for hk in ("first_half", "second_half"):
            r = tab[a][hk][m]
            tb = tab[a][hk]["tb96"]
            lines.append("| %s | %s | %d | %d | %s | %s | %s | %s | %s | %s / %s |" % (
                a[:3], halves_txt[hk], r["n"], r["n_indep"], _f(r["mean_pct"], "%+.3f"),
                _f(r.get("median_pct"), "%+.3f"), _f(r["share_up"], "%.1f%%", 100), _f(r["share_down"], "%.1f%%", 100),
                _f(r["t"], "%.1f"), _f(tb.get("first_touch_up"), "%.1f%%", 100), _f(tb.get("first_touch_down"), "%.1f%%", 100)))
    lines.append("")
    return lines


def _f(x, fmt, mult=1):
    return "-" if x is None else fmt % (x * mult)


def baseline(packs):
    out = {}
    for p in packs:
        out[p["asset"]] = {}
        for hi, hk in ((1, "first_half"), (2, "second_half")):
            msk = p["half"] == hi
            r = {}
            for m in L.METRICS:
                y = p["y"][m][msk]
                y = y[np.isfinite(y)].astype(float)
                r[m] = {"n": int(len(y)), "mean_pct": _r(y.mean()), "share_up": _r((y > 0).mean(), 3)}
            out[p["asset"]][hk] = r
    return out


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--placebo", type=int, default=30, help="placebo re-runs with states slid in time (default 30)")
    ap.add_argument("--top", type=int, default=12, help="cells explained in the Markdown (default 12)")
    ap.add_argument("--out", default=L.OUT_DIR)
    a = ap.parse_args(argv)
    t0 = time.time()
    packs = [pack(asset) for asset in CFG["assets"]]
    if not all(p["times"].equals(packs[0]["times"]) for p in packs):
        common = packs[0]["times"]
        for p in packs[1:]:
            common = common.intersection(p["times"])
        for p in packs:
            keep = p["times"].isin(common)
            p["times"], p["half"] = p["times"][keep], p["half"][keep]
            p["st"] = dict((d, v[keep]) for d, v in p["st"].items())
            p["y"] = dict((m, v[keep]) for m, v in p["y"].items())
            p["cls"] = dict((h, v[keep]) for h, v in p["cls"].items())
            p["pos"] = np.arange(len(p["half"]), dtype=np.int64)
    assets = [p["asset"] for p in packs]
    print("states built in %.1fs, peak %s MB" % (time.time() - t0, L.peak_mb()))

    res, counts, tests, cells = scan(packs, full=True)
    rows = rank(res, assets)
    print("scan: %d cells with enough cases, %d tests, %d consistent, %d pay the fee (%.1fs)" % (
        cells, tests, counts["consistent"], counts["pays_fee"], time.time() - t0))

    rng = np.random.RandomState(15)
    n_bars = len(packs[0]["half"])
    plc = []
    for r in range(a.placebo):
        off = int(rng.randint(n_bars // 10, n_bars - n_bars // 10))
        _, c, _, _ = scan(packs, offset=off)
        plc.append(c)
    print("placebo: %d runs (%.1fs)" % (len(plc), time.time() - t0))

    def pstats(key):
        v = np.array([c[key] for c in plc], dtype=float) if plc else np.array([np.nan])
        return {"mean": _r(v.mean(), 2), "p95": _r(np.percentile(v, 95), 1), "max": _r(v.max(), 0),
                "runs_at_or_above_real": int((v >= counts[key]).sum()) if plc else None}

    p_one = 0.0228                                     # one-sided chance of t >= 2 with no effect
    luck = {
        "cells_examined": cells,
        "tests": tests,
        "how_tests_are_counted": "cells with >= %d independent cases in all four tests x %d outcome measures (%s) x 2 sides"
                                 % (MIN_NEFF, len(RANK_METRICS), ", ".join(RANK_METRICS)),
        "real": counts,
        "placebo": {"runs": len(plc), "consistent": pstats("consistent"), "pays_fee": pstats("pays_fee")},
        "binomial_same_sign_all_four_if_independent": round(tests / 16.0, 1),
        "binomial_consistent_if_coins_were_one": round(tests * p_one ** 2, 2),
        "binomial_consistent_if_all_four_independent": round(tests * p_one ** 4, 6),
        "note": "Cells overlap (a pair contains its singles) and BTC and ETH move together, so the "
                "binomial numbers are rough bounds; the placebo (states slid in time, both coins by the "
                "same amount) keeps all of that structure and is the number to trust.",
    }

    halves_txt = {"first_half": "%s to %s" % (packs[0]["start"].strftime("%Y-%m"), packs[0]["mid"].strftime("%Y-%m")),
                  "second_half": "%s to %s" % (packs[0]["mid"].strftime("%Y-%m"), packs[0]["end"].strftime("%Y-%m"))}
    cons_rows = sorted([r for r in rows if r["consistent"]], key=lambda r: -r["min_t"])
    fee_rows = sorted([r for r in rows if r["pays_fee"]], key=lambda r: -r["worst_net_pct"])
    near_rows = sorted(rows, key=lambda r: -r["min_t"])

    def best_per_cell(rs, n):
        seen, out = set(), []
        for r in rs:
            key = (r["cell"], r["side"])
            if key not in seen:
                seen.add(key)
                out.append(r)
            if len(out) >= n:
                break
        return out

    top_fee = best_per_cell(fee_rows, a.top)
    top_cons = best_per_cell([r for r in cons_rows if not r["pays_fee"]], a.top)
    shown = set((r["cell"], r["side"]) for r in top_fee + top_cons)
    top_near = best_per_cell([r for r in near_rows if (r["cell"], r["side"]) not in shown
                              and not r["consistent"]], max(6, a.top // 2))

    def with_tables(rs):
        out = []
        for r in rs:
            rr = dict(r)
            rr["dims"] = list(r["dims"])
            rr["plain"] = describe(r["dims"], r["code"])
            rr["tests"] = slice_table(res, r["dims"], r["code"], assets)
            out.append(rr)
        return out

    all_cells = []
    for dims in L.groupings():
        _, k = L.combo_codes(packs[0]["st"], dims)
        for code in range(k):
            all_cells.append({"dims": list(dims), "code": code, "cell": L.cell_name(dims, code),
                              "tests": slice_table(res, dims, code, assets)})

    report = {
        "what": "Mind 15 market-state map (charter L2). Leads, not proven edges.",
        "generated_utc": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M"),
        "assets": assets,
        "window": {"start": str(packs[0]["start"]), "mid": str(packs[0]["mid"]), "end": str(packs[0]["end"])},
        "halves": halves_txt,
        "fee_round_trip_pct": L.FEE_RT_PCT,
        "dimensions": dict((d, {"buckets": list(L.DIM_LABELS[d]), "how": L.DIM_TEXT[d]}) for d in L.DIM_NAMES),
        "cut_points_first_half": dict((p["asset"], p["cuts"]) for p in packs),
        "metrics": L.METRIC_TEXT,
        "rules": {"min_independent_cases": MIN_NEFF, "t_consistent": T_CONSISTENT, "t_pays_fee": T_FEE},
        "baseline": baseline(packs),
        "luck": luck,
        "top_pays_fee": with_tables(top_fee),
        "top_consistent_below_fee": with_tables(top_cons),
        "top_nearest": with_tables(top_near),
        "all_candidates_same_sign": [dict((k, (list(v) if k == "dims" else v)) for k, v in r.items()) for r in rows],
        "cells": all_cells,
        "runtime_s": round(time.time() - t0, 1),
        "peak_mb": L.peak_mb(),
    }
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "state_map.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    md = render_md(report, packs, assets, halves_txt, top_fee, top_cons, top_near, res)
    with open(os.path.join(a.out, "state_map.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    print("wrote %s (state_map.json, state_map.md) in %.1fs, peak %s MB" % (a.out, time.time() - t0, L.peak_mb()))
    return report


def render_md(rep, packs, assets, halves_txt, top_fee, top_cons, top_near, res):
    lk = rep["luck"]
    md = ["# Market-state map (charter L2)", "",
          "Generated %s. Coins: %s. History %s to %s, split in two halves: **%s** and **%s**. "
          "Cut points were fixed on the first half only, so the second half is out of sample." % (
              rep["generated_utc"], ", ".join(assets), packs[0]["start"].strftime("%Y-%m-%d"),
              packs[0]["end"].strftime("%Y-%m-%d"), halves_txt["first_half"], halves_txt["second_half"]),
          "",
          "**These are leads, not proven edges.** History can reject an idea, never prove one; anything "
          "worth keeping goes into `research/HYPOTHESES.md` and is graded forward.", "",
          "## How to read this", "",
          "Every closed 15-minute bar is put in a state from six readings known at its close:", ""]
    for d in L.DIM_NAMES:
        md.append("- **%s** (%s): %s" % (d, " / ".join(L.DIM_LABELS[d]), L.DIM_TEXT[d]))
    md += ["", "Cut points (first half): " + "; ".join(
        "%s vol %.2f/%.2f, flow %+.3f/%+.3f, place %.2f/%.2f, move %+.2f/%+.2f ATR" % (
            p["asset"][:3], p["cuts"]["vol"][0], p["cuts"]["vol"][1], p["cuts"]["flow"][0], p["cuts"]["flow"][1],
            p["cuts"]["place"][0], p["cuts"]["place"][1], p["cuts"]["move"][0], p["cuts"]["move"][1]) for p in packs) + ".",
           "",
           "For each state (and each pair of states) we look at what happened next if you entered at the next "
           "15-minute open: the % move over 15 minutes, 1 hour and 4 hours, and the triple-barrier trade "
           "(one unit = 1.5 x the 1-hour ATR above and below; whichever is touched first, within 4 hours or "
           "24 hours). 'Independent' counts overlapping holding periods once. A cell is listed only if it leans "
           "the same way in all four tests: BTC first half, BTC second half, ETH first half, ETH second half.", "",
           "Average bar, for comparison (no state at all): " + "; ".join(
               "%s %s: next 4h %+.3f%% (up %.1f%% of the time)" % (
                   a[:3], hk.replace("_", " "), rep["baseline"][a][hk]["f16"]["mean_pct"],
                   100 * rep["baseline"][a][hk]["f16"]["share_up"])
               for a in assets for hk in ("first_half", "second_half")) + ".", "",
           "## The luck count (charter L4)", "",
           "- Cells examined: **%d** (states and pairs of states with at least %d independent cases in every test)." % (
               lk["cells_examined"], MIN_NEFF),
           "- Tests made: **%d** (%s)." % (lk["tests"], lk["how_tests_are_counted"]),
           "- Passed 'consistent' (same side in all four tests, t >= %.0f in each): **%d**. "
           "Pass after fees (worst test still clears 0.20%%, t >= %.0f in each): **%d**." % (
               T_CONSISTENT, lk["real"]["consistent"], T_FEE, lk["real"]["pays_fee"]),
           "- Placebo: the same scan with the states slid in time against the outcomes (%d runs), i.e. states "
           "that cannot know anything: 'consistent' passed %.1f on average (95th percentile %s, max %s); "
           "'pays the fee' passed %.1f on average (max %s). %s of %d placebo runs matched or beat the real "
           "'consistent' count." % (
               lk["placebo"]["runs"], lk["placebo"]["consistent"]["mean"] or 0, lk["placebo"]["consistent"]["p95"],
               lk["placebo"]["consistent"]["max"], lk["placebo"]["pays_fee"]["mean"] or 0,
               lk["placebo"]["pays_fee"]["max"], lk["placebo"]["consistent"]["runs_at_or_above_real"],
               lk["placebo"]["runs"]),
           "- Simple binomial: with no real effect, %.0f tests would lean the same way in all four tests by "
           "chance if the four were independent (1 in 16); if BTC and ETH were the same coin, about %.2f "
           "tests would pass 'consistent' by luck." % (
               lk["binomial_same_sign_all_four_if_independent"], lk["binomial_consistent_if_coins_were_one"]),
           "- " + lk["note"], ""]
    if top_fee:
        md += ["## Cells that lean the same way everywhere AND clear the fee", ""]
        for i, r in enumerate(top_fee, 1):
            md += md_cell(i, r, slice_table(res, r["dims"], r["code"], assets), assets, halves_txt)
    else:
        md += ["## Cells that lean the same way everywhere AND clear the fee", "",
               "**None.** No state or pair of states leaned the same way in all four tests by enough to pay a "
               "0.20% round trip in its worst test. On its own, no coarse state is a trade.", ""]
    if top_cons:
        md += ["## Consistent cells that do not clear the fee on their own", "",
               "These lean the same way, strongly, in all four tests, but the move is too small to pay the fee "
               "as a stand-alone trade. They are candidates for a filter (when to sit out, which side the "
               "mandate should force) or for timing inside a bigger-picture trade.", ""]
        start = len(top_fee) + 1
        for i, r in enumerate(top_cons, start):
            md += md_cell(i, r, slice_table(res, r["dims"], r["code"], assets), assets, halves_txt)
    if top_near:
        md += ["## Near misses (same side in all four tests, but weaker)", "",
               "These lean the same way in all four tests but at least one test has t below %.0f. Weaker "
               "leads; listed so they can be watched, not traded." % T_CONSISTENT, ""]
        for i, r in enumerate(top_near, len(top_fee) + len(top_cons) + 1):
            md += md_cell(i, r, slice_table(res, r["dims"], r["code"], assets), assets, halves_txt)
    md += ["## The map, one dimension at a time", "",
           "Mean % move over the next 4 hours after each state (entry at the next open), and how often the "
           "engine's 24-hour barrier was touched up first minus down first, in points.", "",
           "| State | " + " | ".join("%s %s 4h %%" % (a[:3], h) for a in assets for h in ("H1", "H2")) + " | " +
           " | ".join("%s %s up-down" % (a[:3], h) for a in assets for h in ("H1", "H2")) + " |",
           "|---|" + "---|" * (4 * len(assets))]
    for d in L.DIM_NAMES:
        for code in range(len(L.DIM_LABELS[d])):
            tab = slice_table(res, (d,), code, assets)
            vals, tbs = [], []
            for a in assets:
                for hk in ("first_half", "second_half"):
                    vals.append(_f(tab[a][hk]["f16"]["mean_pct"], "%+.3f"))
                    tb = tab[a][hk]["tb96"]
                    tbs.append("-" if tb.get("first_touch_up") is None else "%+.1f" % (
                        100 * (tb["first_touch_up"] - tb["first_touch_down"])))
            md.append("| %s=%s | %s | %s |" % (d, L.DIM_LABELS[d][code], " | ".join(vals), " | ".join(tbs)))
    md += ["", "## Limits", "",
           "- Fills at the next open with a flat 0.10% a side; no slippage, no funding.",
           "- The barrier P&L counts a 'neither' (and a bar that touches both barriers) at the horizon's close.",
           "- States are coarse on purpose; 185 cells and 4 outcome measures make many tests, see the luck count.",
           "- 'Independent' is the number of distinct holding-period blocks a cell touches; it is an approximation.",
           "- Full tables for every cell are in `state_map.json` (key `cells`).", ""]
    return md


if __name__ == "__main__":
    main()
