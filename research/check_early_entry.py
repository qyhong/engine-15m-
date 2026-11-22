# -*- coding: utf-8 -*-
"""A check for think15-v5.2.9, not a study: what the Setups book's early entry does to its own paper record on the
stored history. Reads the evidence store and the cached fits; writes nothing but what it prints.

    python research/check_early_entry.py --fits-dir <fits_today>

OLD = the b_targets rule as it was ({"targets": True}: a new entry fills at the next bar's open).
NEW = the rule as it is now (shadows.run_challenger("b_targets"): from flat, at the deciding close).
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

from engine15 import data, shadows  # noqa: E402


def fall(eq):
    e = eq[np.isfinite(eq)]
    return float(np.min(e / np.maximum.accumulate(e) - 1.0) * 100.0)


def main(argv=None):
    import h59_half_be as h59
    import h62_setups_wide_stop as h62
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits-dir", required=True)
    a_ = ap.parse_args(argv)
    assets = ["BTCUSDT", "ETHUSDT"]
    prep = h59.prep_cut("crypto", assets, os.path.join(a_.fits_dir, "crypto"), h62.group_end("crypto", assets), log=print)
    times = prep["times"]
    tms = data.to_ms(times)
    n = len(times)
    for a in assets:
        ok = np.isfinite(prep["odds"][a][:, 0])
        lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
        aux = shadows.aux_from_ev(prep["ev"][a], prep["px"][a])
        inp = shadows.book_inputs(prep, a)
        cfg = shadows.asset_cfg(a, dict(prep["cfg"]))
        tgt = aux["targets"]
        row_of = lambda k, tgt=tgt: tgt.iloc[k] if len(tgt.columns) else pd.Series(dtype=float)   # noqa: E731
        kw = dict(bias=inp["bias"], guard=inp["guard"], times_ms=tms, row_of=row_of, aux=aux)
        old = shadows.run(inp["px"], inp["odds"], inp["shock"], inp["tide"], inp["unit"], cfg, lo, n,
                          rule={"targets": True}, **kw)
        new = h59.run_book("b_targets", prep, a, lo, n, aux)
        assert shadows.CHALLENGERS["b_targets"]["rule"].get("early") and cfg["early_fill"] is True
        to, tn = old["trades"], new["trades"]
        ko = dict(((int(t.t_in_ms), int(t.side)), t) for t in to.itertuples())
        kn = dict(((int(t.t_in_ms), int(t.side)), t) for t in tn.itertuples())
        same = [k for k in ko if k in kn]
        gap = np.array([abs(kn[k].p_in - ko[k].p_in) / ko[k].p_in * 100.0 for k in same])
        o, c = inp["px"]["open"], inp["px"]["close"]
        oc = np.abs(o[lo + 1:n] - c[lo:n - 1]) / c[lo:n - 1] * 100.0
        early_n = int(((tn.why_in == "ENTER") | (tn.why_in == "FORCED")).sum())
        print("%s %s .. %s" % (a, str(times[lo])[:16], str(times[n - 1])[:16]))
        print("  bars where the open is not the close before it: %.2f%% (median gap of those %.4f%%, largest %.3f%%)" % (
            float((oc > 0).mean() * 100), float(np.median(oc[oc > 0])) if (oc > 0).any() else 0.0, float(oc.max())))
        print("  trades: old %d, new %d; the same entry time and side: %d; only old %d, only new %d" % (
            len(to), len(tn), len(same), len(ko) - len(same), len(kn) - len(same)))
        print("  of the same trades: entry price identical %d, median gap %.4f%%, largest %.3f%%; the same exit word %d, "
              "the same exit bar %d" % (int((gap == 0).sum()), float(np.median(gap)), float(gap.max()),
                                        sum(ko[k].why_out == kn[k].why_out for k in same),
                                        sum(int(ko[k].t_out_ms) == int(kn[k].t_out_ms) for k in same)))
        print("  net: old %+.0f, new %+.0f; worst fall: old %.1f%%, new %.1f%%; wins: old %.1f%%, new %.1f%%" % (
            old["equity"][n - 1] - shadows.START_EQUITY, new["equity"][n - 1] - shadows.START_EQUITY, fall(old["equity"][lo:n]),
            fall(new["equity"][lo:n]), float((to.pnl_usd > 0).mean() * 100), float((tn.pnl_usd > 0).mean() * 100)))
        print("  new: entries from flat (posted in their deciding step) %d of %d; flips (one bar later, as before) %d; "
              "closed inside their entry bar %d" % (early_n, len(tn), int((tn.why_in == "FLIP").sum()),
                                                    int((tn.t_in_ms == tn.t_out_ms).sum())))


if __name__ == "__main__":
    main()
