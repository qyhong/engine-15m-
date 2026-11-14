# -*- coding: utf-8 -*-
"""The structure reader and the setup library, on planted series. No network, no real bars."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15.sources import structure  # noqa: E402


def bars_from(close, start="2024-01-01"):
    close = np.asarray(close, dtype=float)
    opn = np.concatenate([[close[0]], close[:-1]])
    return pd.DataFrame({"open": opn, "high": np.maximum(opn, close) + 0.05, "low": np.minimum(opn, close) - 0.05,
                         "close": close, "volume": 100.0, "taker_buy": 50.0},
                        index=pd.date_range(start, periods=len(close), freq="15min", tz="UTC"))


def zigzag(points, step=12):
    """A path through the given turning points, `step` bars a leg."""
    out = []
    for a, b in zip(points[:-1], points[1:]):
        out += list(np.linspace(a, b, step, endpoint=False))
    return np.array(out + [points[-1]])


def test_swings_are_known_only_k_bars_later():
    path = zigzag([100, 110, 104, 116, 108, 122])
    h, l = path + 0.05, path - 0.05
    state, hi, lo = structure.swings(h, l, 3)
    first_peak = 12                                   # bar of the 110 turn
    assert np.isnan(hi[first_peak + 2])               # two bars later: not yet known
    assert abs(hi[first_peak + 3] - 110.05) < 1e-9    # three bars later: known
    assert state[-1] == 1                             # higher highs and higher lows by the end


def test_structure_reads_up_then_down():
    up = zigzag([100, 108, 104, 114, 109, 120, 115, 126])
    down = zigzag([126, 116, 121, 110, 115, 104, 109, 98])
    st_up, _, _ = structure.swings(up + 0.05, up - 0.05, 3)
    st_dn, _, _ = structure.swings(down + 0.05, down - 0.05, 3)
    assert st_up[-1] == 1 and st_dn[-1] == -1


def test_no_lookahead():
    rng = np.random.RandomState(11)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.003, 9000)))
    df = bars_from(close)
    full = structure.features(df.index, "BTCUSDT", bars=df)
    for cut in (5000, 7333, 8990):
        part = structure.features(df.index[:cut], "BTCUSDT", bars=df.iloc[:cut])
        a, b = full.iloc[:cut], part
        for col in full.columns:
            x, y = a[col].values.astype(float), b[col].values.astype(float)
            assert np.allclose(x, y, equal_nan=True), "column %s changed when the future was cut at %d" % (col, cut)


def test_features_are_clean_and_setups_fire():
    rng = np.random.RandomState(12)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.003, 12000)))
    df = bars_from(close)
    f = structure.features(df.index, "BTCUSDT", bars=df)
    feats = [x for g in structure.GROUPS.values() for x in g[1]]
    assert not f[feats].isna().any().any()
    assert f[feats].abs().max().max() <= 2.0
    fired = sum(int((f["ev_" + s] != 0).sum()) for s in structure.SETUPS)
    assert fired > 20                                  # a random walk still breaks levels now and then
    for s in structure.SETUPS:                         # a firing bar is +1 or -1, and the reading holds 8 bars
        assert set(np.unique(f["ev_" + s])) <= {-1.0, 0.0, 1.0}
        assert (f["su_" + s] != 0).sum() >= (f["ev_" + s] != 0).sum()
    row = f.iloc[-1]
    assert "Structure:" in structure.describe(row, "BTCUSDT")["Market structure"]
    assert len(structure.facts(row, "BTCUSDT")["Market structure"]) == 5
