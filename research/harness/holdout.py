# -*- coding: utf-8 -*-
"""holdout -- the ONLY code that reads the sealed holdout (2025-11-11 to 2026-11-11). One look per development pass.

    py -3 research/harness/holdout.py --candidate R1-BTCUSDT-H22

Refuses unless the candidate is listed in loop_state.json "development_passes" and has no look yet. The look is
written to the ledger BEFORE anything is computed (a crash still counts as a look). The candidate runs frozen
exactly as registered: the same variant grid and selection rule, re-selected each quarter on the trailing 12 months
(train windows end at the seal or later), stitched over the holdout. The holdout is 12 months, so its CAGR is that
year's return. A pass = CAGR >= 25%, max DD <= buy-and-hold's on the holdout, positive in more than half its folds.
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

import pandas as pd  # noqa: E402

from engine15.rl import resources  # noqa: E402
from research.harness import core  # noqa: E402
from research.harness.report import STATE, TARGET  # noqa: E402
from research.harness.study import FAMS  # noqa: E402


def holdout_windows(index):
    out, ts = [], core.HOLDOUT_START
    last = index[-1] + pd.Timedelta(minutes=15)
    while ts < last:
        te = min(ts + pd.DateOffset(months=3), last)
        if te - ts < pd.Timedelta(days=30) and out:
            out[-1]["test_end"] = te
            break
        out.append({"i": len(out), "train_start": ts - pd.DateOffset(months=12), "train_end": ts, "test_start": ts, "test_end": te})
        ts = te
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    a = ap.parse_args()
    with open(STATE, encoding="utf-8") as f:
        state = json.load(f)
    ids = [d["id"] for d in state.get("development_passes", [])]
    if a.candidate not in ids:
        raise SystemExit("refused: %s is not a development pass (%s)" % (a.candidate, ids or "none"))
    if any(l["id"] == a.candidate for l in state.get("holdout_looks", [])):
        raise SystemExit("refused: %s already had its one holdout look" % a.candidate)
    _, asset, h = a.candidate.split("-", 2)
    if h not in FAMS:
        raise SystemExit("holdout looks are implemented for walk-forward families %s only" % list(FAMS))
    look = {"id": a.candidate, "utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), "result": "started"}
    state.setdefault("holdout_looks", []).append(look)
    state["holdout_looks_used"] = len(state["holdout_looks"])
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1)
    resources.low_priority()
    bars, fund = core.load(asset, dev_only=False)
    feats = core.features(bars)
    mkt = core.Market(bars, fund)
    wins = holdout_windows(bars.index)
    _, cls, keyf, namef = FAMS[h]
    ob = cls(feats, bars["close"].values)
    choice, _ = core.select(mkt, wins, keyf(), ob.target)
    tgt = core.stitch(bars.index, wins, choice, ob.target)
    ev, _ = core.evaluate(mkt, tgt, wins)
    bh, _ = core.evaluate(mkt, pd.Series(1.0, index=bars.index).values, wins)
    st, bst = ev["stitched"], bh["stitched"]
    pos = sum(1 for w in ev["windows"] if w["total_return"] > 0) / len(ev["windows"])
    passed = st["cagr"] >= TARGET and st["max_drawdown"] <= bst["max_drawdown"] and pos > 0.5
    look.update({"result": "historical pass" if passed else "fail", "cagr": st["cagr"], "sharpe": st["sharpe"],
                 "max_drawdown": st["max_drawdown"], "bh_cagr": bst["cagr"], "bh_max_drawdown": bst["max_drawdown"],
                 "positive_fold_share": pos, "selected": [namef(k) for k in choice],
                 "note": "12-month holdout: CAGR = that year's return"})
    if passed:
        state.setdefault("historical_passes", []).append({"id": a.candidate, "utc": look["utc"]})
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1)
    print(json.dumps(look, indent=1))


if __name__ == "__main__":
    main()
