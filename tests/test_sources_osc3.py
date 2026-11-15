# -*- coding: utf-8 -*-
"""osc3 (CCI card, think15-v5.2.1): textbook value, no look-ahead, ranges, daily waits for its close, wired."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15.sources import osc3  # noqa: E402


def bars(n=96 * 120, seed=5):
    rng = np.random.RandomState(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    o = np.concatenate([[100.0], c[:-1]])
    sp = np.abs(rng.normal(0, 0.002, n)) * c
    idx = pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC")
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) + sp, "low": np.minimum(o, c) - sp, "close": c}, index=idx)


def test_textbook_value():
    tp = np.arange(1.0, 21.0)                                     # typical price 1..20 (high = low = close)
    df = pd.DataFrame({"high": tp, "low": tp, "close": tp})
    md = np.mean(np.abs(tp - tp.mean()))
    want = (20.0 - tp.mean()) / (0.015 * md)
    assert abs(osc3.cci(df).iloc[-1] - want) < 1e-9


def test_no_look_ahead():
    b = bars()
    full = osc3.features(b.index, "TEST", bars=b)
    for cut in (96 * 60 + 7, 96 * 90 + 50, len(b) - 3):
        part = osc3.features(b.index[:cut], "TEST", bars=b.iloc[:cut])
        a = full.iloc[:cut][osc3.FEATURES + osc3.RAW].values.astype(float)
        p = part[osc3.FEATURES + osc3.RAW].values.astype(float)
        assert np.allclose(a, p, equal_nan=True, atol=1e-9), cut


def test_ranges_card_and_daily_close():
    b = bars()
    f = osc3.features(b.index, "TEST", bars=b)
    assert not f[osc3.FEATURES].isna().any().any() and (f[osc3.FEATURES].abs() <= 1.0).all().all()
    say = osc3.describe(f.iloc[-1], "TEST")
    assert list(say) == ["CCI (15m to daily)"] and say["CCI (15m to daily)"].startswith("CCI (20):")
    day = (f.index + pd.Timedelta(minutes=15)).normalize()
    assert f["cci_raw_1d"][day == day[-1]].dropna().nunique() <= 1


def test_wired_as_v5_2_1():
    from engine15 import sources
    assert "osc3" in sources.MODULES
