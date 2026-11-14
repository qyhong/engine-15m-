# -*- coding: utf-8 -*-
"""engine15/sources/fib.py: a hand-made leg with known fib prices, the leg state machine, the
no-look-ahead cut, and the six real assets.

    py -3 -m pytest tests/test_fib.py -q        (from the project folder)
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import data  # noqa: E402
from engine15.sources import fib  # noqa: E402

ASSETS = ("BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "USDJPY", "SPX")
TITLE = fib.GROUPS["fib"][0]


def bars_from(close, start="2024-01-01", wick=0.05):
    close = np.asarray(close, dtype=float)
    opn = np.concatenate([[close[0]], close[:-1]])
    return pd.DataFrame({"open": opn, "high": np.maximum(opn, close) + wick, "low": np.minimum(opn, close) - wick,
                         "close": close, "volume": 100.0, "taker_buy": 50.0},
                        index=pd.date_range(start, periods=len(close), freq="15min", tz="UTC"))


def zigzag(points, step=48):
    out = []
    for a, b in zip(points[:-1], points[1:]):
        out += list(np.linspace(a, b, step, endpoint=False))
    return np.array(out + [points[-1]])


def test_leg_state_machine():
    """Pullback low that holds -> the leg is redrawn from it on a higher high; a lower high is
    ignored; a low below the origin flips the leg."""
    p = np.array([5, 1, 10, 6, 14, 9, 11, 0.5, 4, 2, 3], dtype=float)
    d, o, e, oj, ej = fib.legs(p + 0.5, p - 0.5, p, 1)
    assert d[2] == 0                                                  # one swing low known, no high yet
    assert (d[3], o[3], e[3]) == (1, 0.5, 10.5)                       # first up-leg, known 1 bar after the high
    assert (d[4], o[4], e[4]) == (1, 0.5, 10.5)                       # the higher low (5.5) does not change the leg
    assert (d[5], o[5], e[5]) == (1, 5.5, 14.5)                       # higher high: redrawn from the pullback low
    assert (d[7], o[7], e[7]) == (1, 5.5, 14.5)                       # the lower high (11.5) is ignored
    assert (d[8], o[8], e[8]) == (-1, 14.5, 0.0)                      # a low below the origin: down-leg from the high
    assert (d[10], o[10], e[10]) == (-1, 14.5, 0.0)
    assert (oj[8], ej[8]) == (4, 7)


def test_hand_made_leg_has_known_fib_prices():
    """1h up-leg from 99.95 to 200.05 (span 100.1), a pullback low at 150 that holds, a lower high,
    and a close at 145: depth 0.55, in the golden zone."""
    close = zigzag([120, 100, 200, 150, 160, 145])
    df = bars_from(close)
    f = fib.features(df.index, "BTCUSDT", bars=df)
    row = f.iloc[-1]
    o, e = 99.95, 200.05
    span = e - o
    assert row["fib_1h_dir"] == 1
    assert row["fib_1h_origin_px"] == pytest.approx(o) and row["fib_1h_end_px"] == pytest.approx(e)
    for col, r in (("r236_px", 0.236), ("r382_px", 0.382), ("r500_px", 0.5), ("entry_px", 0.618), ("inval_px", 0.786)):
        assert row["fib_1h_" + col] == pytest.approx(e - r * span), col
    assert row["fib_1h_t1_px"] == pytest.approx(o + 1.272 * span)
    assert row["fib_1h_t2_px"] == pytest.approx(o + 1.618 * span)
    depth = (e - 145.0) / span
    assert row["fib_1h_depth"] == pytest.approx(depth)
    assert row["fib_1h_maxdepth"] == pytest.approx(depth)            # 145 is the deepest close since the leg was known
    assert row["fib_1h_gz"] == 1 and row["fib_1h_broken"] == 0
    assert row["fib_gz_1h"] == 1.0                                    # signed golden-zone pullback, up-leg
    assert row["fib_depth_1h"] == pytest.approx(depth / 1.5)
    rr = (o + 1.272 * span - 145.0) / (145.0 - (e - 0.786 * span))
    assert row["fib_1h_rr"] == pytest.approx(rr)
    assert row["fib_1h_t1_pct"] == pytest.approx(100.0 * (o + 1.272 * span - 145.0) / 145.0)
    assert row["fib_1h_near_lvl"] == 0.5                              # 145 is nearest the 0.5 (150.0)
    words = fib.describe(row, "ETHUSDT")[TITLE]          # two decimals (BTC is shown in whole dollars)
    assert words.startswith("1h up-leg 99.95 -> 200.05; price 145.00 is at the 0.55 retracement, inside the golden zone")
    assert "invalid below 121.37" in words and "227.28 (1.272)" in words and "261.91 (1.618)" in words
    labels = [r[0] for r in fib.facts(row, "BTCUSDT")[TITLE]]
    assert labels[:3] == ["1h leg", "Where price is (1h)", "Levels (1h)"] and labels[-1] == "Confluence"


def test_a_break_of_the_0786_is_remembered():
    close = zigzag([120, 100, 200, 112, 140])                          # down to depth 0.88, then back up to 0.6
    df = bars_from(close)
    row = fib.features(df.index, "BTCUSDT", bars=df).iloc[-1]
    assert row["fib_1h_dir"] == 1 and row["fib_1h_depth"] < 0.618
    assert row["fib_1h_broken"] == 1 and row["fib_1h_gz"] == 0 and row["fib_gz_1h"] == 0.0
    assert row["fib_1h_maxdepth"] > 0.786


def random_bars(n, seed, holes=False):
    rng = np.random.RandomState(seed)
    df = bars_from(100 * np.exp(np.cumsum(rng.normal(0, 0.003, n))))
    if holes:
        keep = rng.rand(n) > 0.004
        keep[n // 2: n // 2 + 24] = False
        df = df[keep]
    return df


@pytest.mark.parametrize("holes", [False, True])
def test_no_lookahead(holes):
    df = random_bars(9000, 21, holes)
    full = fib.features(df.index, "BTCUSDT", bars=df)
    assert full["fib_1h_dir"].abs().sum() > 0 and np.isfinite(full["fib_reach24_pct"]).any()
    for cut in (3000, 5001, 7333, len(df) - 3):
        part = fib.features(df.index[:cut], "BTCUSDT", bars=df.iloc[:cut])
        for col in full.columns:
            x, y = full[col].values[:cut].astype(float), part[col].values.astype(float)
            assert np.array_equal(x, y, equal_nan=True), "column %s changed when the future was cut at %d" % (col, cut)


def test_features_are_clean():
    df = random_bars(12000, 5)
    f = fib.features(df.index, "BTCUSDT", bars=df)
    F = f[fib.FEATURES]
    assert not F.isna().any().any() and F.abs().max().max() <= 1.0
    assert (F != 0).mean().min() > 0.05                               # every feature reads something on a random walk
    assert list(f.columns) == fib.FEATURES + fib.RAW
    assert fib.describe(pd.Series(np.nan, index=f.columns), "BTCUSDT")[TITLE].startswith("No read")


@pytest.mark.parametrize("asset", ASSETS)
def test_real_assets_load(asset):
    if not os.path.exists(data.path_for(asset)):
        pytest.skip("no bars for %s" % asset)
    b = data.load(asset)
    idx = b.index[-3000:]
    f = fib.features(idx, asset)                                       # loads the bars itself, as evidence.build calls it
    assert f.attrs["errors"] == {}
    F = f[fib.FEATURES]
    assert not F.isna().any().any() and F.abs().max().max() <= 1.0
    assert f["fib_1h_dir"].abs().mean() > 0.9 and f["fib_4h_dir"].abs().mean() > 0.9
    row = f.iloc[-1]
    assert TITLE in fib.describe(row, asset) and len(fib.facts(row, asset)[TITLE]) >= 5
