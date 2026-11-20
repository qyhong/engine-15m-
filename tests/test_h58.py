# -*- coding: utf-8 -*-
"""H58 research helpers: the two stock-only readings never read the future; the training mask keeps only known grades."""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "research"))

import h58_stocks as h58  # noqa: E402


def _bars(n, seed):
    rng = np.random.RandomState(seed)
    idx = pd.date_range("2021-01-04 14:30", periods=n, freq="15min", tz="UTC")
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.002, n)))
    return pd.DataFrame({"open": c, "high": c * 1.001, "low": c * 0.999, "close": c, "volume": 1.0}, index=idx)


def test_rel_strength_never_reads_the_future():
    s, x = _bars(1500, 1), _bars(1500, 2)
    x = x.drop(x.index[[700, 701]])                     # a gap in the S&P bars
    full = h58.rel_strength(s, x)
    cut = h58.rel_strength(s.iloc[:1000], x[x.index < s.index[1000]])
    a, b = full.iloc[:1000].values, cut.values
    assert np.allclose(np.nan_to_num(a, nan=9), np.nan_to_num(b, nan=9))
    assert full["rs_5d"].iloc[1400] == full["rs_5d"].iloc[1400]     # reads again after the gap
    assert np.isnan(full["rs_1h"].iloc[702])                         # no read across the missing bar


def test_train_mask_only_known_grades():
    dd = {"req": np.array([True, True, True, False]), "y": np.array([1, 2, -1, 1]),
          "hz_ms": np.array([100, 300, 100, 100]), "g": np.array([5, 6, 7, 8])}
    m = h58.train_mask(dd, 200, 0)
    assert m.tolist() == [True, False, False, False]
    assert h58.train_mask(dd, 200, 6).tolist() == [False, False, False, False]


def test_earnings_feats_known_at_rule(tmp_path):
    p = tmp_path / "earnings_megacap.csv"
    p.write_text("date,symbol,when,first_seen_ms,last_seen_ms,gone_ms\n2022-02-01,NVDA,amc,1794377340678.0,1794377340678.0,\n")
    rel = int(pd.Timestamp("2022-02-01 16:05", tz="America/New_York").tz_convert("UTC").timestamp() * 1000)
    opens = np.array([rel - 8 * 86400000, rel - 3 * 86400000 - h58.BAR_MS, rel + 86400000 - h58.BAR_MS], dtype=np.int64)
    nxt, last, ok = h58.earnings_feats(opens, "NVDA", str(tmp_path))
    assert ok and nxt[0] == 0.0 and abs(nxt[1] - (1 - 3 / 7.0)) < 1e-9 and nxt[2] == 0.0
    assert last[0] == 0.0 and abs(last[2] - (1 - 1 / 5.0)) < 1e-9
    assert h58.earnings_feats(opens, "MU", str(tmp_path))[2] is False
