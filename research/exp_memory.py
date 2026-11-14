# -*- coding: utf-8 -*-
"""Round 1 of the direction-accuracy work (10 Nov 2026): does a longer memory help?

FINDING THAT PROMPTED IT: in the replay the learned voices call direction at 50% while the
plain sign of several raw readings, in their most extreme fifth, is right 52-55% in BOTH
halves of history. A voice refitted on only 180 days seems to chase noise and lose a small,
steady effect. So: refit on ALL graded history instead (and with a heavier ridge), and see.

Declared before running. Three learning rules, everything else unchanged, weekly refits so
the three are comparable and quick:
    V0  180 days, one row an hour      (today's rule, at a weekly cadence)
    V1  all history, one row per 4h
    V2  all history, one row per 4h, ridge x10
Read-out: direction accuracy (calls graded up or down) on all calls, on the most confident
20% and on the most confident 5%, for 2020-2023 and for 2024 onward, for three ways of
forming the final odds: the trust mix, the plain average of the voices, the all-evidence voice.

Honest limit: all of this history has now been looked at, so none of it is a clean test.
The clean test is the live journal from 10 Nov 2026 on.

    py -3 research/exp_memory.py        (needs out/replay/store.pkl)
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import journal, labels, model  # noqa: E402
from engine15.evidence import CARDS, FEATURES, GROUPS, REQUIRED  # noqa: E402

VARIANTS = (("V0 180 days", dict(train_days=180, train_step=4, l2=10.0)),
            ("V1 all history", dict(train_days=4000, train_step=16, l2=10.0)),
            ("V2 all history, ridge x10", dict(train_days=4000, train_step=16, l2=100.0)))


def acc(edge, up, top=None):
    if top is not None:
        cut = np.quantile(np.abs(edge), 1 - top)
        keep = np.abs(edge) >= cut
        edge, up = edge[keep], up[keep]
    return round(float(((edge > 0) == up).mean() * 100), 1) if len(edge) else None


def main():
    t0 = time.time()
    s = journal.load_store("replay")
    assets, times, birth = s["assets"], s["times"], s["span"][0]
    X = dict((a, s["X"][a].astype(float)) for a in assets)
    ready = dict((a, s["ev"][a][REQUIRED].notna().all(axis=1).values) for a in assets)
    y, res = s["y"], s["res"]
    year = times.year.values
    out = {}

    # ---- the first ten cards, rated on what the raw readings did (no model at all)
    rows, half = [], None
    up_all = np.concatenate([(y[a][birth:] == labels.UP)[(y[a][birth:] > 0) & ready[a][birth:]] for a in assets])
    Xg = np.concatenate([X[a][birth:][(y[a][birth:] > 0) & ready[a][birth:]] for a in assets])
    order = np.concatenate([np.arange(len(times))[birth:][(y[a][birth:] > 0) & ready[a][birth:]] for a in assets])
    first = order < np.median(order)
    feat = {}
    for j, f in enumerate(FEATURES):
        x = Xg[:, j]
        if np.abs(x).sum() == 0 or (x != 0).mean() < 0.002:
            continue
        cut = np.quantile(np.abs(x[x != 0]), 0.8) if len(np.unique(x[::97])) > 3 else 0.0     # a yes/no reading: every "yes"
        keep = (np.abs(x) >= cut) & (x != 0)
        if (keep & first).sum() < 200 or (keep & ~first).sum() < 200:
            feat[f] = (None, None, 0.0, "too little history")
            continue
        h = [float(((x[keep & m] > 0) == up_all[keep & m]).mean() * 100) for m in (first, ~first)]
        steady = min(abs(h[0] - 50), abs(h[1] - 50)) if (h[0] - 50) * (h[1] - 50) > 0 else 0.0
        feat[f] = (round(h[0], 1), round(h[1], 1), round(steady, 1), "with" if h[0] > 50 else "against")
    for card, voices in CARDS.items():
        fs = [f for v in voices if v in GROUPS for f in GROUPS[v][1] if f in feat]
        if not fs:
            rows.append((card, None, None, None, 0.0, "no history yet"))
            continue
        best = max(fs, key=lambda f: feat[f][2])
        rows.append((card, journal.WORDS.get(best, best), feat[best][0], feat[best][1], feat[best][2], feat[best][3]))
    out["cards"] = sorted(rows, key=lambda r: -r[4])
    print("THE CARDS, rated by their steadiest raw reading (accuracy of its sign in its most extreme fifth)")
    print("%-28s %-30s %8s %8s %8s  %s" % ("card", "best reading", "1st half", "2nd half", "steady", "direction"))
    for r in out["cards"]:
        print("%-28s %-30s %8s %8s %8s  %s" % (r[0], r[1] or "-", r[2], r[3], r[4], r[5]))

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "card_rating.json"), "w", encoding="utf-8") as fh:
        json.dump(out["cards"], fh, indent=1)
    if "--rate-only" in sys.argv:
        return

    # ---- the three learning rules
    cfg0 = dict(s["cfg"], refit_every=672)
    for name, over in VARIANTS:
        cfg = dict(cfg0, **over)
        probs, models = model.walk_forward(X, ready, y, cfg, birth)
        trust = model.trust_path(probs, y, res, cfg)
        k_all = model.VOICE_NAMES.index("all")
        k_skip = [k for k, v in enumerate(model.VOICE_NAMES) if v in ("all", "base", "risk")]
        table = {}
        for label, lo_y, hi_y in (("2020-2023", 2020, 2023), ("2024 on", 2024, 2100)):
            e_mix, e_avg, e_all, ups, e_voice = [], [], [], [], dict((v, []) for v in model.VOICE_NAMES)
            for a in assets:
                ok = (y[a] > 0) & np.isfinite(probs[a][:, 0, 0]) & (year >= lo_y) & (year <= hi_y)
                p = probs[a][ok]
                edges = p[:, :, labels.UP] - p[:, :, labels.DOWN]
                e_mix.append((trust[ok] * edges).sum(axis=1))
                e_avg.append(np.delete(edges, k_skip, axis=1).mean(axis=1))
                e_all.append(edges[:, k_all])
                ups.append(y[a][ok] == labels.UP)
                for k, v in enumerate(model.VOICE_NAMES):
                    e_voice[v].append(edges[:, k])
            up = np.concatenate(ups)
            row = {"calls": int(len(up))}
            for nm, e in (("trust mix", e_mix), ("plain average", e_avg), ("all-evidence voice", e_all)):
                e = np.concatenate(e)
                row[nm] = [acc(e, up), acc(e, up, 0.20), acc(e, up, 0.05)]
            row["voices_top20"] = dict((v, acc(np.concatenate(e_voice[v]), up, 0.20)) for v in model.VOICE_NAMES
                                       if np.abs(np.concatenate(e_voice[v])).sum() > 0)
            table[label] = row
        out[name] = table
        print("\n%s  (%d weekly refits, %.0fs)" % (name, len(models), time.time() - t0))
        for label, row in table.items():
            print("  %s, %d calls: accuracy on all / most confident 20%% / most confident 5%%" % (label, row["calls"]))
            for nm in ("trust mix", "plain average", "all-evidence voice"):
                print("     %-20s %s" % (nm, row[nm]))
            print("     voices, top 20%%: %s" % row["voices_top20"])
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp_memory_result.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("\ndone in %.0fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
