# -*- coding: utf-8 -*-
"""Grade every named setup on history: when it fired, did price then go its way?

For each coin and each setup (engine15/sources/structure.py), every bar on which the setup
FIRED is graded with the engine's own yardstick (labels.py): right if price travelled one
unit (1.5 x the 1-hour ATR) in the setup's direction before one unit against it, within 24
hours. Bars graded "neither" are left out of the hit rate and counted separately.

Reported per setup and side: how many times it fired, the hit rate, the hit rate in the
first and the second half of history (a setup worth trusting holds up in both), and the mean
move 4 hours and 24 hours later in its direction. The no-setup baseline is 50%.

Writes research/setup_stats.json, which the "Trade setups" card reads.

    py -3 research/setup_stats.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import data, indicators as ind, labels  # noqa: E402
from engine15.config import CFG  # noqa: E402
from engine15.sources import structure  # noqa: E402


def main():
    out = {}
    rows = []
    for asset in CFG["assets"]:
        df = data.load(asset)
        df = df[df.index >= pd.Timestamp(CFG["birth"], tz="UTC") - pd.Timedelta(days=120)]
        f = structure.features(df.index, asset, bars=df)
        h1 = data.resample(df, "1h")
        unit = (CFG["barrier_atr"] * data.htf_on_15(df, "1h", ind.atr_wilder(h1))).values
        o, h, l, c = (df[k].values for k in ("open", "high", "low", "close"))
        y, _ = labels.triple_barrier(o, h, l, unit, CFG["horizon"])
        n = len(c)
        live = np.arange(n) >= int(df.index.searchsorted(pd.Timestamp(CFG["birth"], tz="UTC")))
        half = int(np.median(np.where(live)[0]))
        fwd = {}
        for name, k in (("4h", 16), ("24h", 96)):
            v = np.full(n, np.nan)
            v[:n - k] = (c[k:] / c[:n - k] - 1.0) * 100
            fwd[name] = v
        out[asset] = {}
        for s in structure.SETUPS:
            e = f["ev_" + s].values
            out[asset][s] = {}
            for side, word in ((1, "long"), (-1, "short")):
                fired = (e == side) & live & (y >= 0)
                decided = fired & (y > 0)
                hit = (y == (labels.UP if side > 0 else labels.DOWN))
                def rate(mask):
                    return round(float(hit[mask].mean() * 100), 1) if mask.sum() else None
                first = decided & (np.arange(n) < half)
                rec = {"n": int(decided.sum()), "neither": int((fired & (y == 0)).sum()), "hit": rate(decided),
                       "hit_first_half": rate(first), "hit_second_half": rate(decided & ~first),
                       "n_first_half": int(first.sum()), "n_second_half": int((decided & ~first).sum()),
                       "move_4h_pct": round(float(np.nanmean(side * fwd["4h"][fired])), 3) if fired.sum() else None,
                       "move_24h_pct": round(float(np.nanmean(side * fwd["24h"][fired])), 3) if fired.sum() else None}
                out[asset][s][word] = rec
                rows.append((asset[:3], structure.SETUP_NAMES[s], word, rec["n"], rec["hit"], rec["hit_first_half"],
                             rec["hit_second_half"], rec["move_4h_pct"], rec["move_24h_pct"]))
        anyfire = np.zeros(n, bool)
        for s in structure.SETUPS:
            anyfire |= f["ev_" + s].values != 0
        base = live & (y > 0)
        print("%s: %d graded sessions, a named setup fired on %d of them; up-first share of all sessions %.1f%%" % (
            asset, int(base.sum()), int((anyfire & base).sum()), float((y[base] == labels.UP).mean() * 100)))
    d = pd.DataFrame(rows, columns=["coin", "setup", "side", "times", "right_%", "first_half_%", "second_half_%", "move_4h_%", "move_24h_%"])
    pd.set_option("display.width", 200)
    print(d.to_string(index=False))
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "setup_stats.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
