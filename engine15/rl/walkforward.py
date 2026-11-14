# -*- coding: utf-8 -*-
"""walkforward -- rolling train window, the next unseen test window, roll forward.

    [ train 12 months ][ test 3 months ]
              [ train 12 months ][ test 3 months ]  ...   (step = 3 months)

Test windows are back to back, so their concatenation is one unbroken out-of-sample span.
A strategy's out-of-sample target series is stitched from what it decided in each test
window (an agent: the model trained on that window's train span; a benchmark: its fixed rule),
then ONE backtest runs over it, so positions and costs carry across window boundaries exactly
as they would live. Metrics are reported per test window (slices) and for the stitched span.
"""
import numpy as np
import pandas as pd

from . import metrics


def windows(index, train_months=12, test_months=3, step_months=3, start=None, min_test_days=30, interval_ms=900000):
    """-> list of dicts: i, train_start, train_end, test_start, test_end (end exclusive, UTC)."""
    first, last = index[0], index[-1] + pd.Timedelta(milliseconds=interval_ms)
    ts = pd.Timestamp(start, tz="UTC") if start is not None else first
    ts = max(ts, first)
    out = []
    while True:
        tr_end = ts + pd.DateOffset(months=train_months)
        te_end = tr_end + pd.DateOffset(months=test_months)
        if tr_end >= last:
            break
        if te_end > last:
            te_end = last
            if te_end - tr_end < pd.Timedelta(days=min_test_days):
                break
        out.append({"i": len(out), "train_start": ts, "train_end": tr_end, "test_start": tr_end, "test_end": te_end})
        if te_end >= last:
            break
        ts = ts + pd.DateOffset(months=step_months)
    return out


def mask(index, a, b):
    return (index >= a) & (index < b)


def stitch(index, wins, target_fn):
    """target_fn(train_mask, test_mask) -> targets for the test bars. -> one series, flat (0)
    outside the out-of-sample span."""
    out = pd.Series(0.0, index=index)
    for w in wins:
        tr, te = mask(index, w["train_start"], w["train_end"]), mask(index, w["test_start"], w["test_end"])
        out[te] = np.asarray(target_fn(tr, te), dtype=float)
    return out


def oos_mask(index, wins):
    return mask(index, wins[0]["test_start"], wins[-1]["test_end"])


def evaluate(frame, wins):
    """A backtest frame over the full index -> {"windows": [metrics per test window], "stitched": metrics}."""
    idx = frame.index
    per = []
    for w in wins:
        m = mask(idx, w["test_start"], w["test_end"])
        first = int(np.argmax(m))
        prev = float(frame["pos"].values[first - 1]) if first > 0 else 0.0
        s = metrics.summary(frame[m], prev_pos=prev)
        s.update({"window": w["i"], "test_start": str(w["test_start"].date()), "test_end": str(w["test_end"].date())})
        per.append(s)
    om = oos_mask(idx, wins)
    first = int(np.argmax(om))
    prev = float(frame["pos"].values[first - 1]) if first > 0 else 0.0
    st = metrics.summary(frame[om], prev_pos=prev)
    st.update({"test_start": str(wins[0]["test_start"].date()), "test_end": str(wins[-1]["test_end"].date())})
    return {"windows": per, "stitched": st}
