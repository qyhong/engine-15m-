# -*- coding: utf-8 -*-
"""Release follow-through over the full calendar history, 2019 onward (informational only).

research/event_study.py read the calendar that started in May 2026. This reads the historical
calendar (engine15/calhistory.py, data/sources/calendar_history.csv) with the same measure:
for each release time T the "release bar" is the 15m bar that opens at T; follow-through after
1h / 4h is the move from the release bar's close to the close 4 / 16 bars later, signed by the
release bar's own direction (positive = the first reaction continued, negative = faded).
Split at the middle of the period into a first and a second half. One coin at a time.

It grades nothing: H1 and H16 keep their forward-only verdict rules (research/HYPOTHESES.md).

    py -3 research/release_history.py          -> research/out/release_history.md
"""
import math
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine15 import calhistory, data  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "release_history.md")
KINDS = ["CPI", "NFP", "FOMC"]
OTHER = ["PPI", "RETAIL", "GDP", "PCE", "ISM"]
H1_MIN = 0.3                     # H1's release-bar threshold, percent


def binom_p(k, n):
    """Two-sided exact sign-test p-value for k successes in n at 1/2."""
    if n == 0:
        return float("nan")
    lo = min(k, n - k)
    tail = sum(math.comb(n, j) for j in range(0, lo + 1)) / 2.0 ** n
    return min(1.0, 2 * tail)


def measure(asset, ev):
    df = data.load(asset)
    ms = data.to_ms(df.index)
    o, c = df["open"].values, df["close"].values
    rows = []
    for ts, kind in zip(ev.ts_ms.values, ev.kind.values):
        i = int(np.searchsorted(ms, ts))
        if i >= len(ms) or ms[i] != ts or i + 16 >= len(ms):
            continue
        if ms[i + 16] - ms[i] != 16 * 900000:                        # a gap in the bars: skip
            continue
        r0 = c[i] / o[i] - 1.0
        if r0 == 0:
            continue
        s = 1.0 if r0 > 0 else -1.0
        rows.append({"asset": asset[:3], "kind": kind, "ts_ms": int(ts), "release_pct": r0 * 100,
                     "f1": s * (c[i + 4] / c[i] - 1) * 100, "f4": s * (c[i + 16] / c[i] - 1) * 100})
    del df
    return rows


def table(d):
    def agg(g):
        n = len(g)
        k1, k4 = int((g.f1 > 0).sum()), int((g.f4 > 0).sum())
        return pd.Series({"n": n, "abs_release_%": g.release_pct.abs().mean(),
                          "cont_1h_%": 100.0 * k1 / n, "mean_1h_%": g.f1.mean(), "p_1h": binom_p(k1, n),
                          "cont_4h_%": 100.0 * k4 / n, "mean_4h_%": g.f4.mean(), "p_4h": binom_p(k4, n)})
    return d.groupby(["kind", "asset", "half"], sort=False).apply(agg, include_groups=False)


def fmt(t):
    lines = ["| kind | coin | half | n | mean abs release bar | continued 1h | mean 1h | p 1h | continued 4h | mean 4h | p 4h |",
             "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for (kind, asset, half), r in t.iterrows():
        lines.append("| %s | %s | %s | %d | %.2f%% | %.0f%% | %+.2f%% | %.2f | %.0f%% | %+.2f%% | %.2f |" % (
            kind, asset, half, r["n"], r["abs_release_%"], r["cont_1h_%"], r["mean_1h_%"], r["p_1h"],
            r["cont_4h_%"], r["mean_4h_%"], r["p_4h"]))
    return "\n".join(lines)


def main():
    h = calhistory.load_history()
    if not len(h):
        print("no calendar history; run py -3 -m engine15.calhistory build")
        return
    ev = h[(h.country == "USD") & h.kind.isin(KINDS + OTHER)].drop_duplicates("ts_ms", keep="first")
    ev = ev[ev.ts_ms < int(pd.Timestamp.now(tz="UTC").value // 10**6) - 5 * 3600000]
    rows = []
    for asset in ("BTCUSDT", "ETHUSDT"):                              # one coin in memory at a time
        rows += measure(asset, ev)
    d = pd.DataFrame(rows)
    d["kind"] = np.where(d.kind.isin(KINDS), d.kind, "OTHER")
    t0, t1 = d.ts_ms.min(), d.ts_ms.max()
    mid = t0 + (t1 - t0) // 2
    d["half"] = np.where(d.ts_ms < mid, "1st", "2nd")
    order = {"CPI": 0, "NFP": 1, "FOMC": 2, "OTHER": 3}
    d = d.sort_values(["kind", "asset", "half"], key=lambda s: s.map(order) if s.name == "kind" else s)
    utc = lambda x: str(pd.Timestamp(int(x), unit="ms", tz="UTC"))[:10]   # noqa: E731
    t_all = table(d)
    both = d.assign(half="all")
    t_both = table(both)
    big = d[d.release_pct.abs() >= H1_MIN]
    t_big = table(big.assign(half="all"))

    md = ["# Release follow-through, 2019 onward (informational)", "",
          "Built %s by `research/release_history.py` from `data/sources/calendar_history.csv` "
          "(engine15/calhistory.py) and the 15m Binance bars on file." % pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"),
          "", "**This grades nothing.** H1 (CPI) and H16 (release days beyond CPI) keep their forward-only verdict rules in "
          "`research/HYPOTHESES.md`; history is warm-up and post-mortem material, not validation. Many ways of slicing "
          "these numbers exist; treat any one cell as a description, not an edge.", "",
          "Measure (same as `research/event_study.py`): the release bar is the 15m bar opening at the release time. "
          "Follow-through = the move from the release bar's close to the close 1h (4 bars) / 4h (16 bars) later, "
          "signed by the release bar's direction. *Continued* = share of releases where that is positive. "
          "*p* = two-sided exact sign test against 50%. No costs.", "",
          "Releases %s to %s; halves split at %s. CPI/NFP/FOMC as listed; OTHER = PPI, retail sales, advance GDP, "
          "PCE, ISM manufacturing (release times shared with CPI/NFP count once, under the first kind listed at that time)."
          % (utc(t0), utc(t1), utc(mid)), "",
          "## By half", "", fmt(t_all), "",
          "## Whole period", "", fmt(t_both), "",
          "## Only release bars that moved at least %.1f%% (H1's size filter), whole period" % H1_MIN, "", fmt(t_big), ""]
    note = []
    for kind in KINDS:
        for a in ("BTC", "ETH"):
            try:
                r1, r2 = t_all.loc[(kind, a, "1st")], t_all.loc[(kind, a, "2nd")]
                note.append("- %s %s: continued after 1h %.0f%% / %.0f%% (1st / 2nd half), after 4h %.0f%% / %.0f%%; "
                            "mean 4h follow-through %+.2f%% / %+.2f%%." % (
                                kind, a, r1["cont_1h_%"], r2["cont_1h_%"], r1["cont_4h_%"], r2["cont_4h_%"],
                                r1["mean_4h_%"], r2["mean_4h_%"]))
            except KeyError:
                pass
    cells = pd.concat([t_all, t_both, t_big])
    pv = pd.concat([cells["p_1h"], cells["p_4h"]])
    low = [("%s %s %s" % k) + (" 1h" if c == "p_1h" else " 4h") for c in ("p_1h", "p_4h") for k, v in cells[c].items() if v < 0.05]
    note.append("- %d of %d p-values in the tables are below 0.05 (%s); about %.1f would be by chance alone."
                % (len(low), len(pv), ", ".join(low) or "none", 0.05 * len(pv)))
    md += ["## Read", ""] + note + ["",
           "With roughly 45 releases per kind, coin and half, a continued-share between about 35% and 65% is within "
           "what a coin flip produces (the p column says so case by case). BTC and ETH react to the same release, so "
           "their rows are not independent evidence.", ""]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
