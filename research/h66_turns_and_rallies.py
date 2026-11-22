# -*- coding: utf-8 -*-
"""H66: BTC and ETH, how a Setups short has turned long and what the book did in a sudden rally. Research only;
registered in research/HYPOTHESES.md before this file existed. Reads what H63 reads, changes nothing.

    /data/venv-research/bin/python research/h66_turns_and_rallies.py --fits-dir research/out/h60_regime_exits/fits_today
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

OUT = os.path.join(ROOT, "research", "out", "h66_turns_and_rallies")
MID = pd.Timestamp("2023-06-08", tz="UTC")
WIN = 96


def _end(why):
    last = str(why).split("+")[-1]
    return "stop" if last == "STOP" else ("target" if last in ("T2", "STOP_BE") else "flip or other")


def turns(tr, from_side):
    """Trades on `from_side` followed by a trade on the other side: by how the first one ended."""
    rows = list(tr.itertuples())
    out, again = {}, []
    for a, b in zip(rows[:-1], rows[1:]):
        if int(a.side) != from_side:
            continue
        end = _end(a.why_out)
        if int(b.side) == from_side:
            if end == "stop":
                again.append(float(b.r_mult))
            continue
        d = out.setdefault(end, {"hours": [], "r": [], "words": {}})
        d["hours"].append((int(b.i_in) - int(a.i_out)) * 0.25)
        d["r"].append(float(b.r_mult))
        d["words"][str(b.why_in)] = d["words"].get(str(b.why_in), 0) + 1
    res = {}
    for k, d in out.items():
        r = np.array(d["r"])
        res[k] = {"n": len(r), "median_hours_to_the_turn": float(np.median(d["hours"])), "entry_words": d["words"],
                  "won_pct": float((r > 0).mean() * 100), "mean_r": float(r.mean()), "sum_r": float(r.sum())}
    stops = sum(1 for a in rows[:-1] if int(a.side) == from_side and _end(a.why_out) == "stop")
    res["after_a_stop"] = {"stopped": stops, "next_same_side": len(again),
                           "next_same_side_pct": float(len(again) / stops * 100) if stops else None,
                           "next_same_side_mean_r": float(np.mean(again)) if again else None,
                           "next_same_side_won_pct": float((np.array(again) > 0).mean() * 100) if again else None}
    return res


def episodes(book, px, times, lo, n, side, pct):
    """Sudden moves against a held side: -> list of episode facts."""
    c, held, eq, tr = px["close"], book["held"], book["equity"], book["trades"]
    i_in, i_out = tr.i_in.values.astype(int), tr.i_out.values.astype(int)
    sides, why, r = tr.side.values.astype(int), tr.why_out.astype(str).values, tr.r_mult.values.astype(float)
    out, t = [], lo
    while t + WIN < n:
        mv = c[t + WIN] / c[t] - 1.0
        if held[t] == side and -side * mv >= pct:
            z = t + WIN
            inside = (i_out > t) & (i_out <= z)
            new_same = int(((i_in > t) & (i_in <= z) & (sides == side)).sum())
            first_other = np.flatnonzero((i_in > t) & (i_in <= z) & (sides == -side))
            out.append({"time": str(times[t])[:16], "half": 1 if times[t] < MID else 2, "move_pct": float(mv * 100),
                        "book_pct": float((eq[z] / eq[t] - 1.0) * 100), "sum_r_closed": float(np.nansum(r[inside])),
                        "stop_outs": int((inside & (np.array([w.split("+")[-1] for w in why]) == "STOP")).sum()),
                        "new_same_side": new_same,
                        "holds_at_end": {1: "long", -1: "short", 0: "flat"}[int(held[z])],
                        "hours_to_other_side": float((i_in[first_other[0]] - t) * 0.25) if len(first_other) else None})
            t = z
        else:
            t += 1
    return out


def tally(eps):
    if not eps:
        return {"episodes": 0}
    f = lambda k: np.array([e[k] for e in eps], dtype=float)                                     # noqa: E731
    hrs = [e["hours_to_other_side"] for e in eps if e["hours_to_other_side"] is not None]
    ends = [e["holds_at_end"] for e in eps]
    return {"episodes": len(eps), "median_move_pct": float(np.median(f("move_pct"))),
            "median_book_pct": float(np.median(f("book_pct"))), "mean_book_pct": float(f("book_pct").mean()),
            "worst_book_pct": float(f("book_pct").min()), "best_book_pct": float(f("book_pct").max()),
            "book_lost_in_pct_of_episodes": float((f("book_pct") < 0).mean() * 100),
            "median_sum_r_closed": float(np.median(f("sum_r_closed"))), "mean_sum_r_closed": float(f("sum_r_closed").mean()),
            "worst_sum_r_closed": float(f("sum_r_closed").min()),
            "median_stop_outs": float(np.median(f("stop_outs"))), "max_stop_outs": int(f("stop_outs").max()),
            "mean_new_same_side": float(f("new_same_side").mean()),
            "episodes_with_a_new_same_side_trade_pct": float((f("new_same_side") > 0).mean() * 100),
            "turned_within_24h_pct": float(len(hrs) / len(eps) * 100),
            "median_hours_to_turn": float(np.median(hrs)) if hrs else None,
            "ends": dict((k, ends.count(k)) for k in ("long", "short", "flat"))}


def run(fits_root, log=print):
    times, px, books = h63.replay(fits_root, log=log)
    n = len(times)
    res = {"end": str(times[n - 1])[:16], "turns": {}, "rallies": {}, "drops": {}}
    alls = {("rallies", 0.05): [], ("rallies", 0.08): [], ("drops", 0.05): [], ("drops", 0.08): []}
    for a in h63.COINS:
        book, lo = books[a][0], books[a][1]
        res["turns"][a] = {"short_to_long": turns(book["trades"], -1), "long_to_short": turns(book["trades"], 1)}
        for name, side in (("rallies", -1), ("drops", 1)):
            for pct in (0.05, 0.08):
                eps = episodes(book, px[a], times, lo, n, side, pct)
                alls[(name, pct)] += eps
                res[name].setdefault(a, {})["%d%%" % (pct * 100)] = dict(tally(eps), worst=sorted(eps, key=lambda e: e["book_pct"])[:3])
    for (name, pct), eps in alls.items():
        k = "%d%%" % (pct * 100)
        res[name].setdefault("both", {})[k] = {"all": tally(eps), "h1": tally([e for e in eps if e["half"] == 1]),
                                               "h2": tally([e for e in eps if e["half"] == 2])}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "results.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    rnd = lambda d: dict((x, (round(y, 2) if isinstance(y, float) else y)) for x, y in d.items() if x != "worst")   # noqa: E731
    for a in h63.COINS:
        for way in ("short_to_long", "long_to_short"):
            for k, v in res["turns"][a][way].items():
                log("%s %s | %s: %s" % (a, way, k, json.dumps(rnd(v))))
    for name in ("rallies", "drops"):
        for k in ("5%", "8%"):
            for part in ("all", "h1", "h2"):
                log("%s %s both coins %s: %s" % (name, k, part, json.dumps(rnd(res[name]["both"][k][part]))))
        for a in h63.COINS:
            log("%s 5%% %s worst: %s" % (name, a, json.dumps(res[name][a]["5%"]["worst"])))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits-dir", default=os.path.join(ROOT, "research", "out", "h60_regime_exits", "fits_today"))
    run(ap.parse_args(argv).fits_dir)


if __name__ == "__main__":
    main()
