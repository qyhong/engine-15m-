# -*- coding: utf-8 -*-
"""H44 range-break study: the signal function never reads the future, and the break definition is the registered one."""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

import rangebreak_study as rb  # noqa: E402
from engine15.sources import adr  # noqa: E402


def bars(n=96 * 60, seed=11, gaps=False):
    rng = np.random.RandomState(seed)
    ret = rng.normal(0, 0.003, n) + np.where(rng.rand(n) < 0.02, rng.normal(0, 0.02, n), 0.0)   # some momentum bars
    c = 100.0 * np.exp(np.cumsum(ret))
    o = np.concatenate([[100.0], c[:-1]])
    sp = np.abs(rng.normal(0, 0.002, n)) * c
    idx = pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC")
    df = pd.DataFrame({"open": o, "high": np.maximum(o, c) + sp, "low": np.minimum(o, c) - sp, "close": c,
                       "volume": 1.0, "taker_buy": np.nan}, index=idx)
    if gaps:                                                       # a market that shuts: drop 20:00-13:30 UTC
        m = df.index.hour * 60 + df.index.minute
        df = df[(m >= 810) & (m < 1200)]
    return df


def _r(x):
    return None if x != x else round(x, 9)


def _key(sigs):
    return [(s["i_dec"], s["side"], round(s["stop"], 9), _r(s["t2_cand"][1]), _r(s["level"])) for s in sigs]


def test_signals_never_read_the_future():
    for gaps in (False, True):
        df = bars(gaps=gaps)
        n = len(df)
        for v, var in rb.ALL.items():
            full = _key(rb.signals(adr.readings(df, box=var["box"]), var))
            assert full, v
            for cut in (int(n * 0.5) + 3, int(n * 0.8) + 11, n - 2):
                part = _key(rb.signals(adr.readings(df.iloc[:cut], box=var["box"]), var))
                assert part == [x for x in full if x[0] < cut], (v, gaps, cut)


def test_break_definition_by_hand():
    df = bars()
    R = adr.readings(df, box=24)
    br = adr.breaks(R, "box", 1.5)
    h, l, c, tr, atr = df["high"].values, df["low"].values, df["close"].values, R["tr"], R["atr15"]
    for i in range(40, len(df)):
        up = c[i] > h[i - 24:i].max() and tr[i] >= 1.5 * atr[i - 1]
        dn = c[i] < l[i - 24:i].min() and tr[i] >= 1.5 * atr[i - 1]
        assert br[i] == (1 if up else -1 if dn else 0), i


def test_filters_and_twins():
    df = bars()
    R = adr.readings(df, box=24)
    room = rb.signals(R, rb.VARIANTS["V1"])
    exh = rb.signals(R, rb.VARIANTS["V7"])
    none = rb.signals(R, rb.VARIANTS["V8"])
    assert all(s["used"] < 0.65 for s in room) and all(s["used"] >= 1.0 for s in exh)
    ids = set(s["i_dec"] for s in none)
    assert set(s["i_dec"] for s in room) <= ids and set(s["i_dec"] for s in exh) <= ids
    for s in none:                                                 # stop = break close -/+ 1 x ATR15
        assert abs(s["stop"] - (R["c"][s["i_dec"]] - s["side"] * R["atr15"][s["i_dec"]])) < 1e-9
