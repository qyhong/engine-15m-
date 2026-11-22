# -*- coding: utf-8 -*-
"""H64: what the one-bar delay costs a member at the entry. Research only; registered in research/HYPOTHESES.md before
this file existed. Reads what H63 reads, changes nothing.

    /data/venv-research/bin/python research/h64_entry_delay.py --fits-dir research/out/h60_regime_exits/fits_today
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

import h63_member_wallet as h63  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "h64_entry_delay")
MID = "2023-06-08"


def cost_rows(coin, trades, px, times, n):
    """One row per trade whose next bar exists: the cost of entering at the next bar's open, in % of price and in R."""
    o, h, l = px["open"], px["high"], px["low"]
    rows = []
    for t in trades.itertuples():
        i = int(t.i_in)
        if i + 1 >= n:
            continue
        side, entry = int(t.side), float(t.p_in)
        cost = side * (o[i + 1] - o[i]) / o[i] * 100.0
        stop_pct = abs(entry - float(t.stop0)) / entry * 100.0
        t1 = t.target_1
        in_bar_t1 = bool(t1 == t1 and ((l[i] <= t1) if side < 0 else (h[i] >= t1)) and "T1" in str(t.why_out))
        rows.append({"coin": coin, "time": str(times[i])[:16], "half": 1 if times[i] < pd.Timestamp(MID, tz="UTC") else 2,
                     "word": str(t.why_in), "cost_pct": float(cost), "cost_r": float(cost / stop_pct) if stop_pct else np.nan,
                     "closed_in_entry_bar": int(t.i_out) == i, "t1_in_entry_bar": in_bar_t1})
    return rows


def summary(rows):
    if not rows:
        return {"trades": 0}
    c = np.array([r["cost_pct"] for r in rows])
    r_ = np.array([r["cost_r"] for r in rows])
    return {"trades": len(rows), "mean_pct": float(c.mean()), "median_pct": float(np.median(c)),
            "worse_share": float((c > 0).mean() * 100), "better_share": float((c < 0).mean() * 100),
            "p05_pct": float(np.percentile(c, 5)), "p95_pct": float(np.percentile(c, 95)),
            "sum_r": float(np.nansum(r_)), "mean_r": float(np.nanmean(r_)),
            "t_stat": float(c.mean() / (c.std(ddof=1) / np.sqrt(len(c)))) if len(c) > 1 and c.std(ddof=1) > 0 else None,
            "closed_in_entry_bar_share": float(np.mean([r["closed_in_entry_bar"] for r in rows]) * 100),
            "t1_in_entry_bar_share": float(np.mean([r["t1_in_entry_bar"] for r in rows]) * 100)}


def run(fits_root, live_dir, state_path, log=print):
    times, px, books = h63.replay(fits_root, log=log)
    n = len(times)
    rows = []
    for a in h63.COINS:
        rows += cost_rows(a, books[a][0]["trades"], px[a], times, n)
    res = {"end": str(times[n - 1])[:16], "all": summary(rows)}
    for a in h63.COINS:
        res[a] = summary([r for r in rows if r["coin"] == a])
    for hf in (1, 2):
        res["half_%d" % hf] = summary([r for r in rows if r["half"] == hf])
    for w in sorted(set(r["word"] for r in rows)):
        res["word_" + w] = summary([r for r in rows if r["word"] == w])
    try:                                                           # the live record: the same cost on its own trades
        ft, fpx, fset, _lo = h63.live_record(live_dir, state_path, log=log)
        live = []
        for s in fset:
            i = s["i_in"]
            if i + 1 < len(ft):
                o = fpx[s["coin"]]["open"]
                c = s["side"] * (o[i + 1] - o[i]) / o[i] * 100.0
                sp = abs(s["entry"] - s["stop0"]) / s["entry"] * 100.0
                live.append({"coin": s["coin"], "time": str(ft[i])[:16], "half": 2, "word": "", "cost_pct": float(c),
                             "cost_r": float(c / sp), "closed_in_entry_bar": s["i_out"] == i, "t1_in_entry_bar": False})
        res["live"] = dict(summary(live), rows=[(r["coin"], r["time"], round(r["cost_pct"], 3)) for r in live])
    except Exception as e:
        res["live"] = {"error": "%s: %s" % (type(e).__name__, e)}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "results.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    for k, v in res.items():
        if isinstance(v, dict):
            log("%s: %s" % (k, json.dumps(dict((x, (round(y, 4) if isinstance(y, float) else y)) for x, y in v.items()
                                               if x != "rows"), default=float)))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits-dir", default=os.path.join(ROOT, "research", "out", "h60_regime_exits", "fits_today"))
    ap.add_argument("--live-dir", default=os.path.join(ROOT, "out", "live"))
    ap.add_argument("--state", default=os.path.join(ROOT, "data", "shadow_state.json"))
    a = ap.parse_args(argv)
    run(a.fits_dir, a.live_dir, a.state)


if __name__ == "__main__":
    main()
