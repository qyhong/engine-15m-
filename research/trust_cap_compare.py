# -*- coding: utf-8 -*-
"""H43 history comparison (recorded, not a gate): the v5.2 trust cap (40%) against no cap, on the H42 machinery.

The owner set the cap at 40% (15 Nov 2026). This replays research/trust_study.py twice per group with the live constants
(eta 0.2, floor 0.02): once as before, once with model.cap_shares(w, 0.40) applied to the final mixing weights (the
same place v5.2 applies it). Development data only (to 2025-11-11), cached private refits in research/out/trust/fits/.
Output: research/out/trust_cap/compare.md (+ group json).
    py -3 research/trust_cap_compare.py
"""
import gc
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

import trust_study as ts  # noqa: E402
from engine15 import model  # noqa: E402
from engine15.config import CFG  # noqa: E402

OUT = os.path.join(ROOT, "research", "out", "trust_cap")
_plain_mix = model.mix


def _run(group, assets, cap, log):
    ts.VARIANTS[:] = [("cap40" if cap else "nocap", {"trust_eta": 0.2, "trust_floor": 0.02})]
    ts.NAMES[:] = [k for k, _ in ts.VARIANTS]
    model.mix = (lambda p, w: _plain_mix(p, model.cap_shares(w, cap))) if cap else _plain_mix
    try:
        return ts.run_group(group, assets, log)
    finally:
        model.mix = _plain_mix


def main():
    os.makedirs(OUT, exist_ok=True)
    log = lambda *m: print(time.strftime("%H:%M:%S"), *m, flush=True)      # noqa: E731
    ts.ex.below_normal()
    groups = dict((g, list(a)) for g, a in CFG["universes"])
    rows = []
    for g in ts.GROUPS:
        ts.ex.acquire("trust_cap_compare %s (H43)" % g, log)
        try:
            ts.ex.wait_memory(ts.ex.MIN_FREE_START, log)
            res = {}
            for cap in (None, 0.40):
                r = _run(g, groups[g], cap, log)
                res["cap40" if cap else "nocap"] = r["variants"]["cap40" if cap else "nocap"]
            with open(os.path.join(OUT, "group_%s.json" % g), "w", encoding="utf-8") as fh:
                json.dump(res, fh)
            for half in ("first", "second"):
                for name in ("nocap", "cap40"):
                    h = res[name][half]
                    rows.append((g, half, name, h["skill"], h["books"]))
        finally:
            ts.ex.release()
        gc.collect()
    with open(os.path.join(OUT, "rows.json"), "w", encoding="utf-8") as fh:
        json.dump([[g, half, name, skill, books] for g, half, name, skill, books in rows], fh, default=str)
    log("done")


if __name__ == "__main__":
    main()
