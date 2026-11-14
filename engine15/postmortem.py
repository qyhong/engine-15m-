# -*- coding: utf-8 -*-
"""postmortem -- look back at what each reading was saying and what happened next.

This is the tool for forming new hypotheses: it describes, it does not prove. Every table
carries its counts; overlapping 24-hour outcomes mean the effective sample is far smaller
than the row count, so treat a difference as a lead to test forward, not as an edge.

    py -3 -m engine15 postmortem                 every reading, one line each
    py -3 -m engine15 postmortem cvd_4h          one reading in five buckets
    py -3 -m engine15 postmortem trades          the paper book's closed trades, by why they opened and closed
    (add  --days 30  to look only at the last 30 days; default is the whole run)
"""
import sys

import numpy as np
import pandas as pd

from . import journal, labels
from .evidence import FEATURES


def frame(store, days=None):
    """One row per coin per session: every reading, the engine's edge, the grade, the next moves."""
    rows = []
    n = len(store["times"])
    lo = store["span"][0] if days is None else max(store["span"][0], n - days * 96)
    for a in store["assets"]:
        c = store["px"][a]["close"]
        d = pd.DataFrame(store["X"][a][lo:n], columns=FEATURES)
        d.insert(0, "asset", a)
        d.insert(1, "time", store["times"][lo:n])
        od = store["odds"][a][lo:n]
        d["edge"] = od[:, labels.UP] - od[:, labels.DOWN]
        d["grade"] = store["y"][a][lo:n]
        for name, k in (("next_1h_pct", 4), ("next_4h_pct", 16), ("next_24h_pct", 96)):
            fwd = np.full(n, np.nan)
            fwd[:n - k] = (c[k:] / c[:n - k] - 1.0) * 100
            d[name] = fwd[lo:n]
        rows.append(d)
    return pd.concat(rows, ignore_index=True)


def by_reading(df, feature, buckets=5):
    g = df[(df.grade >= 0) & df[feature].notna()]
    if g[feature].nunique() <= buckets:
        key = g[feature].round(2)
    else:
        key = pd.qcut(g[feature], buckets, duplicates="drop")
    out = g.groupby(key, observed=True).agg(
        sessions=("grade", "size"), up_first_pct=("grade", lambda s: round((s == labels.UP).mean() * 100, 1)),
        down_first_pct=("grade", lambda s: round((s == labels.DOWN).mean() * 100, 1)),
        next_4h_pct=("next_4h_pct", lambda s: round(s.mean(), 3)), next_24h_pct=("next_24h_pct", lambda s: round(s.mean(), 3)))
    out["up_minus_down"] = (out.up_first_pct - out.down_first_pct).round(1)
    return out


def overview(df):
    """Per reading: the spread between its top and bottom fifth in (up first - down first)."""
    rows = []
    for f in FEATURES:
        if df[f].abs().sum() == 0:
            rows.append((f, journal.WORDS.get(f, f), 0, None, None, "no data yet (live only)"))
            continue
        t = by_reading(df, f)
        if len(t) < 2:
            continue
        spread = float(t.up_minus_down.iloc[-1] - t.up_minus_down.iloc[0])
        rows.append((f, journal.WORDS.get(f, f), int(t.sessions.sum()), round(spread, 1),
                     round(float(t.next_24h_pct.iloc[-1] - t.next_24h_pct.iloc[0]), 3),
                     "high reading -> up more often" if spread > 0 else "high reading -> down more often"))
    return pd.DataFrame(rows, columns=["reading", "meaning", "sessions", "top_minus_bottom_pts", "next_24h_gap_pct", "note"]
                        ).sort_values("top_minus_bottom_pts", key=lambda s: -s.abs().fillna(-1))


def trades(store):
    rows = []
    for a in store["assets"]:
        t = store["books"][a]["trades"]
        t = t[t.why_out != "OPEN"].assign(asset=a, side=lambda d: d.side.map({1: "LONG", -1: "SHORT"}),
                                          sessions=lambda d: d.i_out - d.i_in)
        rows.append(t)
    t = pd.concat(rows)
    return t.groupby(["asset", "side", "why_in", "why_out"]).agg(
        trades=("pnl_pct", "size"), won_pct=("pnl_pct", lambda s: round((s > 0).mean() * 100, 1)),
        avg_pct=("pnl_pct", lambda s: round(s.mean(), 3)), total_pct=("pnl_pct", lambda s: round(s.sum(), 1)),
        avg_sessions=("sessions", lambda s: round(s.mean(), 1)))


def main(argv):
    days = None
    if "--days" in argv:
        k = argv.index("--days")
        days = int(argv[k + 1])
        argv = argv[:k] + argv[k + 2:]
    store = journal.load_store("replay")
    pd.set_option("display.width", 200)
    if argv and argv[0] == "trades":
        print(trades(store).to_string())
    elif argv:
        print("%s (%s): what followed, by bucket of the reading" % (argv[0], journal.WORDS.get(argv[0], argv[0])))
        print(by_reading(frame(store, days), argv[0]).to_string())
    else:
        print(overview(frame(store, days)).to_string(index=False))
    print("\nDescriptive only: outcomes overlap, so the real sample is much smaller than the session count.")


if __name__ == "__main__":
    main(sys.argv[1:])
