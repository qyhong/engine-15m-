# -*- coding: utf-8 -*-
"""H70 POST-HOC, descriptive only (not registered, passes nothing): on Stage 1 data only (cut at 2023-06-07 23:45),
the 18 candidates and the all-bar baseline WITHOUT fees, and the median stop distance, to show how much of the
negative mean R is the fee. Never touches Stage 2 or Stage 3 data.

    python research/h70_posthoc_fees.py --fits-dir <fits>
"""
import argparse
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

import h70_rebound_long as h  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits-dir", required=True)
    a = ap.parse_args(argv)
    prep = h.load_group("crypto", h.COINS, h.PERIODS[1][1], a.fits_dir)
    out = {"note": "post hoc, Stage 1 data only, descriptive", "baseline": {}, "candidates": {}}
    frames = {}
    for coin in h.COINS:
        fr = h.market_frame(prep, coin, 1)
        good = fr["out"]["status"] == 0
        ks = fr["ks"][good]
        P = fr["px"]["open"][ks + 1]
        S = fr["rd"]["low16"][ks] - 0.25 * fr["rd"]["atr15"][ks]
        fee_r = fr["fee"] * 2 * P / (P - S)                  # about the round-trip fee in R
        nofee = h.outcomes(fr["px"], fr["rd"], fr["ks"], 0.0)
        fr["nofee"] = nofee
        out["baseline"][coin] = {"mean_r_net": float(np.mean(fr["out"]["r"][good])),
                                 "mean_r_no_fee": float(np.mean(nofee["r"][good])),
                                 "median_stop_pct": float(np.median((P - S) / P * 100)),
                                 "median_round_trip_fee_r": float(np.median(fee_r))}
        frames[coin] = fr
    for cand in h.CANDS:
        net, gross, stop = [], [], []
        for coin, fr in frames.items():
            tr, _ = h.trades_of(fr, cand)
            pos = np.searchsorted(fr["ks"], [t["k"] for t in tr])
            net += [t["r"] for t in tr]
            gross += list(fr["nofee"]["r"][pos])
            k = np.array([t["k"] for t in tr], int)
            if len(k):
                P = fr["px"]["open"][k + 1]
                S = fr["rd"]["low16"][k] - 0.25 * fr["rd"]["atr15"][k]
                stop += list((P - S) / P * 100)
        out["candidates"][cand] = {"n": len(net), "mean_r_net": float(np.mean(net)), "mean_r_no_fee": float(np.mean(gross)),
                                   "median_stop_pct": float(np.median(stop))}
    os.makedirs(h.OUT, exist_ok=True)
    with open(os.path.join(h.OUT, "posthoc_fees_stage1.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
