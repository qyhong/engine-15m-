# -*- coding: utf-8 -*-
"""engine15/sources/mavg.py: known SMA/EMA values, a known golden cross, the test counter, the ribbon on
ramps, the no-look-ahead cut, the higher-timeframe join, and the six real assets.

    py -3 -m pytest tests/test_mavg.py -q        (from the project folder)
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import data  # noqa: E402
from engine15.sources import mavg  # noqa: E402

ASSETS = ("BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "USDJPY", "SPX")
ALL = mavg.FEATURES + mavg.RAW


def bars_from(close, start="2024-01-01", wick=0.05):
    close = np.asarray(close, dtype=float)
    opn = np.concatenate([[close[0]], close[:-1]])
    return pd.DataFrame({"open": opn, "high": np.maximum(opn, close) + wick, "low": np.minimum(opn, close) - wick,
                         "close": close, "volume": 100.0, "taker_buy": 50.0},
                        index=pd.date_range(start, periods=len(close), freq="15min", tz="UTC"))


def random_bars(n=12000, seed=3, holes=False):
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


def manual_ema(x, n):
    """EMA seeded with the SMA of the first n values, reported from row 2n - 1 (indicators.ema_seeded)."""
    out = np.full(len(x), np.nan)
    e = np.mean(x[:n])
    a = 2.0 / (n + 1.0)
    vals = [e]
    for v in x[n:]:
        e = e + a * (v - e)
        vals.append(e)
    out[n - 1:] = vals
    out[:2 * n - 1] = np.nan
    return out


def manual_sma(x, n):
    out = np.full(len(x), np.nan)
    out[n - 1:] = np.convolve(x, np.ones(n) / n, mode="valid")
    return out


# ------------------------------------------------------------------ known values
def test_known_sma_and_ema_on_a_ramp():
    """On a straight ramp every average of length n sits exactly (n - 1) / 2 steps behind the close,
    the EMA too (its steady-state lag equals the SMA seed's)."""
    step = 0.5
    close = 1000.0 + step * np.arange(3000)
    df = bars_from(close)
    row = mavg.features(df.index, "BTCUSDT", bars=df).iloc[-1]
    for f, n in mavg.AVGS:
        want = close[-1] - step * (n - 1) / 2.0
        assert row["ma_15m_%s%d_px" % (f, n)] == pytest.approx(want, rel=1e-6), (f, n)
    assert row["ma_15m_sma200_slope"] > 0 and row["ma_share_1h"] == 1.0 and row["ma_stack_1h"] == 1.0
    say = mavg.describe(row, "BTCUSDT")[mavg.GROUPS["mavg"][0]]
    assert "price above 10 of 10 averages, both stacks fully bullish" in say


def test_ema_and_sma_match_plain_loops_and_the_1h_join():
    df = random_bars(6000, 5)
    f = mavg.features(df.index, "BTCUSDT", bars=df)
    c = df["close"].values
    for n in (5, 20, 200):
        np.testing.assert_allclose(f["ma_15m_ema%d_px" % n].values, manual_ema(c, n).astype(np.float32), rtol=1e-6)
        np.testing.assert_allclose(f["ma_15m_sma%d_px" % n].values, manual_sma(c, n).astype(np.float32), rtol=1e-6)
    h1 = data.resample(df, "1h")
    want = data.htf_on_15(df, "1h", pd.Series(manual_sma(h1["close"].values, 50), index=h1.index)).values
    np.testing.assert_allclose(f["ma_1h_sma50_px"].values, want.astype(np.float32), rtol=1e-6)
    assert np.isnan(f["ma_1h_sma50_px"].values[:4 * 50 - 1]).all()          # 50 CLOSED hours are needed first


def test_closed_positions_are_the_htf_on_15_lookup():
    df = random_bars(5000, 7, holes=True)
    ms = data.to_ms(df.index)
    for rule in ("1h", "4h", "1D"):
        h = mavg._hbars(df, rule)
        pos = mavg.closed_positions(ms, data.to_ms(h.index), rule)
        want = data.htf_on_15(df, rule, pd.Series(np.arange(len(h), dtype=float), index=h.index)).values
        got = np.where(pos >= 0, pos, np.nan)
        assert np.array_equal(got, want, equal_nan=True), rule


def test_a_known_golden_cross():
    """A fall then a rise: SMA 50 crosses above SMA 200 at the row a plain loop finds; age, price
    and direction are read back; the sentence names it a golden cross."""
    close = np.concatenate([np.linspace(200, 100, 600), np.linspace(100, 220, 600)])
    df = bars_from(close)
    f = mavg.features(df.index, "BTCUSDT", bars=df)
    s50, s200 = manual_sma(close, 50), manual_sma(close, 200)
    with np.errstate(invalid="ignore"):
        ups = np.flatnonzero((s50[1:] > s200[1:]) & (s50[:-1] <= s200[:-1])) + 1
    assert len(ups) == 1
    r = ups[0]
    last = f.iloc[-1]
    assert last["ma_15m_x_s50_200_age"] == len(close) - 1 - r
    assert last["ma_15m_x_s50_200_px"] == pytest.approx(0.5 * (s50[r] + s200[r]), rel=1e-6)
    assert f["ma_15m_x_s50_200_age"].iloc[r] == 0
    rd = mavg._tf_read(last, "15m")
    assert rd["crosses"]["s50_200"][2] == "up"
    assert "golden cross (SMA 50 over 200)" in mavg._cross_words("s50_200", rd["crosses"]["s50_200"], "BTCUSDT")
    before = f.iloc[r - 1]                                                   # the bar before: no cross yet (the lines never crossed before)
    assert np.isnan(before["ma_15m_x_s50_200_age"])


def test_the_1h_cross_signal_fades_and_is_signed():
    close = 100 + 10 * np.sin(np.arange(6000) / 300.0)                     # slow waves: crosses both ways
    df = bars_from(close)
    f = mavg.features(df.index, "BTCUSDT", bars=df)
    x = f["ma_cross_1h"].values
    assert x.min() < -0.1 and x.max() > 0.1 and np.abs(x).max() <= 1.0
    assert (f["ma_1h_x_e5_10_age"].dropna() >= 0).all()


# ------------------------------------------------------------------ tests of an average as a level
def test_tests_are_counted_only_after_price_moved_away():
    avg = np.full(9, 100.0)
    atr = np.ones(9)
    c = np.array([102, 101, 100.2, 100.3, 101, 100.1, 102, 99, 99.2])
    low = np.array([101.5, 100.8, 100.1, 100.15, 100.8, 99.9, 101, 98.5, 99.0])
    high = np.array([102.5, 101.5, 100.5, 100.5, 101.2, 100.5, 102.2, 100.5, 99.9])
    touch, side, held, test = mavg.ma_tests(high, low, c, avg, atr)
    assert touch.tolist() == [0, 0, 1, 1, 0, 1, 0, 1, 1]
    assert test.tolist() == [0, 0, 1, 0, 0, 1, 0, 1, 0]      # bar 3 hugs the line; bar 8 has not moved away since 7
    assert held.tolist() == [0, 0, 1, 1, 0, 1, 0, 0, 1]      # bar 7 closed through it
    assert side.tolist() == [0, 0, 1, 1, 0, 1, 0, 1, -1]     # bar 8 comes from below (a resistance touch)
    h, t = mavg.respect(test, held, 2)
    assert (h[-1], t[-1]) == (1.0, 2.0) and (h[5], t[5]) == (2.0, 2.0) and (h[1], t[1]) == (0.0, 0.0)


def test_a_bounce_off_a_rising_average_is_a_held_support_test():
    """A steady climb with regular dips to the EMA 50: the 15m card sees held tests from above."""
    n = 4000
    t = np.arange(n)
    trend = 100 + 0.02 * t
    close = trend + 1.2 * np.abs(np.sin(t * np.pi / 60.0))                  # dips back towards the trend line
    df = bars_from(close, wick=0.02)
    f = mavg.features(df.index, "BTCUSDT", bars=df)
    held, tests = f["mas_15m_ema50_held"].iloc[-1], f["mas_15m_ema50_tests"].iloc[-1]
    assert tests >= 5 and held >= 0.8 * tests
    assert f["mas_15m_sma200_tests"].iloc[-1] == 0                          # price never came back to the 200
    assert f["mas_test_15m"].max() == 1.0 and f["mas_test_15m"].min() >= 0.0


# ------------------------------------------------------------------ the ribbon
def test_ribbon_on_ramps():
    up = bars_from(100 + 0.05 * np.arange(3000))
    f = mavg.features(up.index, "BTCUSDT", bars=up).iloc[-1]
    assert f["rb_order_15m"] == 1.0 and f["rb_order_1h"] == 1.0 and f["rb_gmma_1h"] > 0
    assert f["rb_15m_gmma_overlap"] == 0.0 and f["rb_pos_15m"] > 0.5
    words = mavg.describe(f, "BTCUSDT")[mavg.GROUPS["ribbon"][0]]
    assert words.startswith("1h ribbon in order up") and "price above all five lines" in words
    dn = bars_from(np.concatenate([100 + 0.05 * np.arange(1000), 150 - 0.05 * np.arange(2000)]))   # up, then down
    g = mavg.features(dn.index, "BTCUSDT", bars=dn).iloc[-1]
    assert g["rb_order_1h"] == -1.0 and g["rb_width_1h"] < 0 and g["rb_gmma_15m"] < 0
    assert g["rb_15m_reorder_dir"] == -1.0


# ------------------------------------------------------------------ the one rule
def _cut_equal(df, asset, cuts):
    full = mavg.features(df.index, asset, bars=df)
    assert full["ma_1h_sma50_px"].notna().any()
    for cut in cuts:
        part = mavg.features(df.index[:cut], asset, bars=df.iloc[:cut])
        for col in ALL:
            x, y = full[col].values[:cut], part[col].values
            assert np.array_equal(x, y, equal_nan=True), "column %s changed when the future was cut at %d" % (col, cut)


@pytest.mark.parametrize("holes", [False, True])
def test_no_lookahead_synthetic(holes):
    df = random_bars(12000, 11, holes)
    _cut_equal(df, "BTCUSDT", (2001, 5555, 9999, len(df) - 2))


@pytest.mark.parametrize("asset,n", [("BTCUSDT", 30000), ("SPX", 12000)])
def test_no_lookahead_real(asset, n):
    try:
        df = data.load(asset).iloc[-n:]
    except Exception:
        pytest.skip("no %s file" % asset)
    _cut_equal(df, asset, (n // 3 + 7, n // 2 + 1, n - 5))


def test_rows_without_a_bar_are_no_read():
    df = random_bars(3000, 2)
    idx = df.index.append(pd.DatetimeIndex([df.index[-1] + pd.Timedelta(minutes=15 * k) for k in (1, 2)]))
    f = mavg.features(idx, "BTCUSDT", bars=df)
    assert (f[mavg.FEATURES].iloc[-2:] == 0).all().all() and f[mavg.RAW].iloc[-2:].isna().all().all()


# ------------------------------------------------------------------ reading and the real assets
def test_confluence_reads_levels_and_fib_from_the_row():
    row = pd.Series({"ma_1h_atr": 200.0, "sup_px": 73980.0, "fib_1h_dir": 1.0, "fib_1h_entry_px": 74050.0,
                     "fib_1h_r500_px": 75000.0, "ma_4h_ema50_px": 74010.0})
    got = mavg.confluence(row, 74020.0, "BTCUSDT")
    names = [g[0] for g in got]
    assert names[0] == "the 4h EMA 50" and "the 1h 0.618 Fib" in names and "a horizontal support" in names
    assert all("0.5" not in g for g in names)                               # 980 away: not within 0.25 ATR (50)
    assert mavg.confluence(row, 74020.0, "BTCUSDT", skip=("4h", "ema", 50))[0][0] == "the 1h 0.618 Fib"


@pytest.mark.parametrize("asset", ASSETS)
def test_real_assets(asset):
    try:
        df = data.load(asset).iloc[-40000:]
    except Exception:
        pytest.skip("no %s file" % asset)
    f = mavg.features(df.index, asset, bars=df)
    assert not f.attrs["errors"]
    feats = f[mavg.FEATURES].values
    assert np.isfinite(feats).all() and np.abs(feats).max() <= 1.0 + 1e-6
    row = f.iloc[-1]
    say = mavg.describe(row, asset)
    assert list(say) == [t for t, _ in mavg.GROUPS.values()]
    assert all(isinstance(s, str) and s.endswith(".") and "nan" not in s.lower() for s in say.values())
    fx = mavg.facts(row, asset)
    for title, rows in fx.items():
        assert 4 <= len(rows) <= 6 and all(isinstance(v, str) and "nan" not in v.lower() for _l, v in rows)
    if asset in ("USDJPY", "XAGUSD"):                                       # three decimals
        px = mavg._px(row["ma_1h_ema20_px"], asset)
        assert len(px.split(".")[1]) == 3
