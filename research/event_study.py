# -*- coding: utf-8 -*-
"""What BTC and ETH did around scheduled US releases (prompted by the CPI print of 10 Nov 2026).

Descriptive only, and the sample is small: the calendar on disk starts in May 2026. For each
release time T (a 15m bar opens exactly at T, the "release bar"):
    before    the hour before T
    release   the release bar itself: its return and its range against a normal 15m range
    after     the 1h, 4h and 24h that follow the release bar's close
"Follow-through" = the later move measured in the direction of the release bar's own close:
positive means the first reaction continued, negative means it was faded.

    py -3 research/event_study.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import data, econ, indicators as ind  # noqa: E402


def kind(titles):
    t = " ".join(titles).upper()
    return "CPI" if "CPI" in t else "FOMC" if ("FOMC" in t or "FEDERAL FUNDS" in t) else "JOBS" if ("NFP" in t or "NON-FARM" in t or "EMPLOYMENT" in t) else "OTHER"


def main():
    ev = econ.load_events()
    groups = ev.groupby("ts_ms")["title"].apply(list)
    now_ms = pd.Timestamp.now(tz="UTC").timestamp() * 1000
    rows = []
    for asset in ("BTCUSDT", "ETHUSDT"):
        df = data.load(asset)
        ms = data.to_ms(df.index)
        o, h, l, c = (df[k].values for k in ("open", "high", "low", "close"))
        norm = ind.true_range(df).rolling(96).mean().values / c
        for ts, titles in groups.items():
            if ts > now_ms - 3600e3:
                continue
            i = int(np.searchsorted(ms, ts))
            if i >= len(ms) - 1 or ms[i] != ts or i < 100:
                continue
            r0 = c[i] / o[i] - 1
            sign = np.sign(r0) or 1.0
            def later(k):
                return (c[i + k] / c[i] - 1) * 100 if i + k < len(c) else np.nan
            rows.append({"asset": asset[:3], "date": str(df.index[i])[:16], "kind": kind(titles),
                         "before_1h_pct": (o[i] / o[i - 4] - 1) * 100, "release_pct": r0 * 100,
                         "release_range_x_normal": ((h[i] - l[i]) / o[i]) / norm[i - 1],
                         "wick_against_close_pct": ((h[i] - max(o[i], c[i])) if r0 < 0 else (min(o[i], c[i]) - l[i])) / o[i] * 100,
                         "follow_1h": sign * later(4), "follow_4h": sign * later(16), "follow_24h": sign * later(96)})
    d = pd.DataFrame(rows)
    pd.set_option("display.width", 220)
    print("Releases on file with bars: %d rows (%d release times x 2 coins), %s to %s" % (len(d), d.date.nunique(), d.date.min(), d.date.max()))
    print("\nToday's CPI:")
    print(d[d.date == d.date.max()].round(2).to_string(index=False))
    print("\nBy kind of release (mean; 'continued' = share of releases whose first reaction was still ahead later):")
    g = d.groupby(["kind"]).agg(releases=("date", "size"), release_abs_pct=("release_pct", lambda s: s.abs().mean()),
                                range_x_normal=("release_range_x_normal", "mean"),
                                follow_1h=("follow_1h", "mean"), continued_1h=("follow_1h", lambda s: (s > 0).mean() * 100),
                                follow_4h=("follow_4h", "mean"), continued_4h=("follow_4h", lambda s: (s > 0).mean() * 100),
                                follow_24h=("follow_24h", "mean"), continued_24h=("follow_24h", lambda s: (s > 0).mean() * 100))
    print(g.round(2).to_string())
    big = d[d.release_pct.abs() >= 0.5]
    print("\nOnly releases whose release bar moved 0.5%% or more (%d rows):" % len(big))
    print(big[["follow_1h", "follow_4h", "follow_24h"]].agg(["mean", lambda s: (s > 0).mean() * 100]).rename(index={"<lambda>": "continued_%"}).round(2).to_string())
    print("\nEvery CPI on file:")
    print(d[d.kind == "CPI"].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
