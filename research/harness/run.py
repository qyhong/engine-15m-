# -*- coding: utf-8 -*-
"""Harness study, loop round 1 (H20-H24). Paper research only, development data only (sealed holdout untouched).

    py -3 research/harness/run.py               BTCUSDT then ETHUSDT (cached per asset), then the report
    py -3 research/harness/run.py --fresh       recompute both assets
    py -3 research/harness/run.py --report      rebuild the report from the caches only
    py -3 research/harness/run.py --offline     accepted for symmetry with engine15.rl: this study never uses the network

Outputs: research/out/harness/harness_report.md, harness_summary.json, loop_state.json, cache_<asset>.json.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine15.rl import resources  # noqa: E402
from research.harness import core, families, report  # noqa: E402
from research.harness.study import Study  # noqa: E402

ASSETS = ("BTCUSDT", "ETHUSDT")
N_GRADED = 3 + 24            # H20, H22, H23 headlines + 24 ladder levels, per asset (Bonferroni)
N_TRIALS = 864 + 36 + 18 + 1  # variants this round, per asset (DSR caution)


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def wait_mem(need=1000):
    while True:
        f = resources.free_mb()
        if f is None or f >= need:
            return
        log("waiting for memory: %.0f MB free, need %d" % (f, need))
        time.sleep(30)


def run_asset(asset):
    wait_mem(1000)
    st = Study(asset, log=log)
    out = {"asset": asset, "bars": len(st.bars), "first_bar": str(st.bars.index[0]), "last_bar": str(st.bars.index[-1]),
           "oos_start": str(st.wins[0]["test_start"].date()), "oos_end": str(st.wins[-1]["test_end"].date()),
           "folds": len(st.wins), "benchmarks": st.benchmarks()}
    fams = {}
    for h in ("H22", "H23", "H20"):
        wait_mem(1000)
        res, _ = st.family(h)
        r = res.pop("_r")
        st._r_head = r
        res["significance"] = st.significance(N_GRADED, N_TRIALS)
        fams[h] = res
        log("%s %s: CAGR %.1f%%, Sharpe %.2f, trades/yr %.0f" % (
            asset, h, 100 * res["fee_0.10%"]["stitched"]["cagr"], res["fee_0.10%"]["stitched"]["sharpe"],
            res["fee_0.10%"]["stitched"]["trades_per_year"]))
    out["families"] = fams
    lad = st.ladder()
    for r in lad:
        st._r_head = r.pop("_r")
        r["significance"] = st.significance(N_GRADED, N_TRIALS)
    out["ladder"] = lad
    log("%s ladder done" % asset)
    return out


def replay_family():
    import pandas as pd
    out = {}
    for asset in ASSETS:
        p = os.path.join(ROOT, "out", "replay", "trades_%s.csv" % asset)
        if not os.path.exists(p):
            continue
        bars, _ = core.load(asset, dev_only=True)
        out[asset] = families.replay_filter(pd.read_csv(p), bars)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--assets", default=",".join(ASSETS))
    a = ap.parse_args()
    resources.low_priority()
    os.makedirs(core.OUT_DIR, exist_ok=True)
    caches = {}
    for asset in a.assets.split(","):
        p = os.path.join(core.OUT_DIR, "cache_%s.json" % asset)
        if a.report or (os.path.exists(p) and not a.fresh):
            if os.path.exists(p):
                with open(p, encoding="utf-8") as f:
                    caches[asset] = json.load(f)
            continue
        caches[asset] = run_asset(asset)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(caches[asset], f, default=float)
        log("saved %s" % p)
    rep = replay_family()
    report.build(caches, rep, N_GRADED, N_TRIALS, log=log)


if __name__ == "__main__":
    main()
