# -*- coding: utf-8 -*-
"""engine15/sources/trendtools.py: Hull, KAMA and Ichimoku against plain loops, the cloud's 26-bar
displacement, ramps, the no-look-ahead cut, and the six real assets.

    py -3 -m pytest tests/test_trendtools.py -q        (from the project folder)
"""
import math
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import data  # noqa: E402
from engine15.sources import trendtools as tt  # noqa: E402

ASSETS = ("BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "USDJPY", "SPX")
ALL = tt.FEATURES + tt.RAW


def bars_from(close, start="2024-01-01", wick=0.05):
    close = np.asarray(close, dtype=float)
    opn = np.concatenate([[close[0]], close[:-1]])
    return pd.DataFrame({"open": opn, "high": np.maximum(opn, close) + wick, "low": np.minimum(opn, close) - wick,
                         "close": close, "volume": 100.0, "taker_buy": 50.0},
                        index=pd.date_range(start, periods=len(close), freq="15min", tz="UTC"))


def random_bars(n=8000, seed=4, holes=False):
    rng = np.random.RandomState(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    df = bars_from(close, wick=0.0)
    spread = np.abs(rng.normal(0, 0.001, n)) * close
    df["high"] += spread
    df["low"] -= spread
    if holes:
        keep = rng.rand(n) > 0.004
        keep[n // 2: n // 2 + 30] = False
        df = df[keep]
    return df


def loop_wma(x, k):
    out = np.full(len(x), np.nan)
    w = np.arange(1, k + 1, dtype=float)
    for i in range(len(x)):
        seg = x[i - k + 1:i + 1] if i >= k - 1 else None
        if seg is not None and np.isfinite(seg).all():
            out[i] = (seg * w).sum() / w.sum()
    return out


def loop_kama(c, n=10, fast=2, slow=30):
    out = np.full(len(c), np.nan)
    fs, ss = 2.0 / (fast + 1), 2.0 / (slow + 1)
    k = None
    for i in range(n, len(c)):
        noise = sum(abs(c[j] - c[j - 1]) for j in range(i - n + 1, i + 1))
        er = abs(c[i] - c[i - n]) / noise if noise > 0 else 0.0
        sc = (er * (fs - ss) + ss) ** 2
        k = c[i] if k is None else k + sc * (c[i] - k)
        out[i] = k
    return out


def test_wma_and_hull_match_plain_loops():
    x = random_bars(600)["close"].values
    for k in (3, 4, 10):
        np.testing.assert_allclose(tt.wma(x, k), loop_wma(x, k), rtol=1e-12, equal_nan=True)
    for n in (9, 21, 55):
        want = loop_wma(2 * loop_wma(x, n // 2) - loop_wma(x, n), int(math.floor(math.sqrt(n))))
        np.testing.assert_allclose(tt.hma(x, n), want, rtol=1e-10, equal_nan=True)


def test_kama_matches_a_plain_loop_and_the_efficiency_ratio_is_known():
    x = random_bars(800)["close"].values
    k, er = tt.kama(x)
    np.testing.assert_allclose(k, loop_kama(x), rtol=1e-12, equal_nan=True)
    _k, er_line = tt.kama(np.arange(100, dtype=float))                      # a straight line: ER 1
    assert np.allclose(er_line[10:], 1.0)
    _k, er_chop = tt.kama(np.tile([100.0, 101.0], 50))                       # back and forth: ER 0
    assert np.allclose(er_chop[10:], 0.0)


def test_ichimoku_cloud_now_is_the_one_computed_26_bars_ago():
    df = random_bars(400)
    ic = tt.ichimoku(df)
    h, l = df["high"].values, df["low"].values
    i = 300
    tenkan = (h[i - 8:i + 1].max() + l[i - 8:i + 1].min()) / 2
    kijun = (h[i - 25:i + 1].max() + l[i - 25:i + 1].min()) / 2
    assert ic["tenkan"][i] == pytest.approx(tenkan) and ic["kijun"][i] == pytest.approx(kijun)
    assert ic["span_a"][i + 26] == pytest.approx((tenkan + kijun) / 2)       # drawn 26 bars ahead
    j = i - 26                                                               # the cloud under bar i: computed at bar i - 26
    b_then = (h[j - 51:j + 1].max() + l[j - 51:j + 1].min()) / 2
    assert ic["span_b"][i] == pytest.approx(b_then)
    assert ic["lag_ref"][i] == df["close"].values[i - 26]


def test_ramp_reads_up_on_every_tool():
    df = bars_from(100 + 0.05 * np.arange(6000))
    row = tt.features(df.index, "BTCUSDT", bars=df).iloc[-1]
    for f in ("ich_pos_1h", "ich_pos_4h", "ich_cloud_1h", "ich_lag_4h", "hull_dir_15m", "hull_dir_1h", "kama_er_4h"):
        assert row[f] > 0.5, f
    assert row["kama_4h_state"] == 1.0 and row["kama_15m_er"] == pytest.approx(1.0)
    say = tt.describe(row, "BTCUSDT")
    assert "price above the cloud" in say["Ichimoku cloud"] and "trending up" in say[tt.GROUPS["kama"][0]]
    flat = bars_from(100 + np.tile([0.0, 0.5], 3000))
    r2 = tt.features(flat.index, "BTCUSDT", bars=flat).iloc[-1]
    assert r2["kama_15m_state"] == 0.0 and abs(r2["kama_er_15m"]) < 0.05


def _cut_equal(df, asset, cuts):
    full = tt.features(df.index, asset, bars=df)
    assert full["ich_4h_kijun_px"].notna().any()
    for cut in cuts:
        part = tt.features(df.index[:cut], asset, bars=df.iloc[:cut])
        for col in ALL:
            x, y = full[col].values[:cut], part[col].values
            assert np.array_equal(x, y, equal_nan=True), "column %s changed when the future was cut at %d" % (col, cut)


@pytest.mark.parametrize("holes", [False, True])
def test_no_lookahead_synthetic(holes):
    _cut_equal(random_bars(9000, 9, holes), "BTCUSDT", (1501, 4444, 7001, 8990))


@pytest.mark.parametrize("asset,n", [("BTCUSDT", 15000), ("SPX", 8000)])
def test_no_lookahead_real(asset, n):
    try:
        df = data.load(asset).iloc[-n:]
    except Exception:
        pytest.skip("no %s file" % asset)
    _cut_equal(df, asset, (n // 3 + 7, n // 2 + 1, n - 5))


def test_rows_without_a_bar_are_no_read():
    df = random_bars(3000, 2)
    idx = df.index.append(pd.DatetimeIndex([df.index[-1] + pd.Timedelta(minutes=15)]))
    f = tt.features(idx, "BTCUSDT", bars=df)
    assert (f[tt.FEATURES].iloc[-1] == 0).all() and f[tt.RAW].iloc[-1].isna().all()


@pytest.mark.parametrize("asset", ASSETS)
def test_real_assets(asset):
    try:
        df = data.load(asset).iloc[-20000:]
    except Exception:
        pytest.skip("no %s file" % asset)
    f = tt.features(df.index, asset, bars=df)
    assert not f.attrs["errors"]
    feats = f[tt.FEATURES].values
    assert np.isfinite(feats).all() and np.abs(feats).max() <= 1.0 + 1e-6
    row = f.iloc[-1]
    say = tt.describe(row, asset)
    assert list(say) == [t for t, _ in tt.GROUPS.values()]
    assert all(s.endswith(".") and "nan" not in s.lower() and "n/a" not in s for s in say.values())
    for title, rows in tt.facts(row, asset).items():
        assert 4 <= len(rows) <= 6 and all("nan" not in v.lower() for _l, v in rows)
