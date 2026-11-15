# -*- coding: utf-8 -*-
"""osc (Supertrend and StochRSI cards, think15-v5.1.2): no look-ahead, sane ranges, plain-English cards."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15.sources import osc  # noqa: E402


def bars(n=96 * 120, seed=3):
    rng = np.random.RandomState(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    o = np.concatenate([[100.0], c[:-1]])
    sp = np.abs(rng.normal(0, 0.002, n)) * c
    idx = pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC")
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) + sp, "low": np.minimum(o, c) - sp, "close": c}, index=idx)


def test_no_look_ahead():
    b = bars()
    full = osc.features(b.index, "TEST", bars=b)
    for cut in (96 * 60 + 7, 96 * 90 + 50, len(b) - 3):
        part = osc.features(b.index[:cut], "TEST", bars=b.iloc[:cut])
        a = full.iloc[:cut][osc.FEATURES + osc.RAW].values.astype(float)
        p = part[osc.FEATURES + osc.RAW].values.astype(float)
        assert np.allclose(a, p, equal_nan=True, atol=1e-9), cut


def test_ranges_and_cards():
    b = bars()
    f = osc.features(b.index, "TEST", bars=b)
    assert not f[osc.FEATURES].isna().any().any()
    assert (f[osc.FEATURES].abs() <= 1.0).all().all()
    late = f.iloc[-1]
    for tag, _ in osc.TFS:
        assert late["os_st_" + tag] in (-1.0, 1.0)
        assert 0.0 <= late["os_k_raw_" + tag] <= 100.0
    say = osc.describe(late, "TEST")
    assert set(say) == set(t for t, _ in osc.GROUPS.values())
    assert "Supertrend" in say["Supertrend (15m to daily)"] and "StochRSI" in say["StochRSI (15m to daily)"]


def test_higher_timeframe_waits_for_its_close():
    b = bars()
    f = osc.features(b.index, "TEST", bars=b)
    k1d = f["os_k_raw_1d"]
    day = (k1d.index + pd.Timedelta(minutes=15)).normalize()      # rows keyed by OPEN time: a row's CLOSE decides
    inside = k1d[(day == day[-1])].dropna()                       # between two daily closes the daily value cannot change
    assert inside.nunique() <= 1
