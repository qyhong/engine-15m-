# -*- coding: utf-8 -*-
"""engine15/sources/ltf.py checked on planted data. No network, no real bars, no files.

    py -3 -m pytest tests/test_sources_ltf.py -q        (from the project folder)
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import data  # noqa: E402
from engine15.sources import ltf  # noqa: E402

A = "BTCUSDT"
BAR, HOUR, DAY = ltf.BAR_MS, ltf.HOUR_MS, ltf.DAY_MS
MONDAY = "2024-01-01"                                 # a Monday, 00:00 UTC
ALL = ltf.FEATURES + ltf.RAW


def make_bars(n=9000, seed=1, start=MONDAY, holes=False):
    """A random walk with wicks and an hour-of-day volume pattern; holes=True drops scattered bars
    and one six-hour stretch, as a real tape has."""
    rng = np.random.RandomState(seed)
    vol_now = 0.002 * np.exp(0.5 * np.sin(np.arange(n) / 700.0))     # volatility that drifts, so readings move
    close = 100.0 * np.exp(np.cumsum(rng.normal(0, 1, n) * vol_now))
    opn = np.concatenate([[100.0], close[:-1]])
    spread = np.abs(rng.normal(0, 0.001, n)) * close
    volume = rng.uniform(50, 150, n) * (1.0 + 0.5 * np.sin(2 * np.pi * np.arange(n) / 96.0))
    bars = pd.DataFrame({"open": opn, "high": np.maximum(opn, close) + spread, "low": np.minimum(opn, close) - spread,
                         "close": close, "volume": volume, "taker_buy": volume * rng.uniform(0.3, 0.7, n)},
                        index=pd.date_range(start, periods=n, freq="15min", tz="UTC"))
    if holes:
        keep = rng.rand(n) > 0.004
        keep[n // 2: n // 2 + 24] = False
        bars = bars[keep]
    return bars


def flat_bars(days, price=100.0, wick=0.5, volume=1.0, start=MONDAY):
    """Bars that open and close at `price` with a wick each side: typical price = price, true range = 2 x wick."""
    n = 96 * days
    return pd.DataFrame({"open": price, "high": price + wick, "low": price - wick, "close": price, "volume": volume,
                         "taker_buy": volume / 2.0}, index=pd.date_range(start, periods=n, freq="15min", tz="UTC"))


def put(bars, row, o, h, l, c, v=None):
    bars.iloc[row, :4] = [o, h, l, c]
    if v is not None:
        bars.iloc[row, 4] = v


def same(a, b):
    return np.array_equal(a.values.astype(float), b.values.astype(float), equal_nan=True)


def feats(bars, index=None):
    f = ltf.features(bars.index if index is None else index, A, bars=bars)
    assert f.attrs["errors"] == {}, f.attrs["errors"]
    return f


# ------------------------------------------------------------------ the interface
def test_interface_and_ranges():
    assert list(ltf.GROUPS) == ["intraday", "trendq", "candles"]
    assert [t for t, _f in ltf.GROUPS.values()] == ["Intraday levels (VWAP and opening range)",
                                                    "Trend quality and squeeze", "Candle size and realistic targets"]
    assert ltf.update(log=lambda *_a: None) == {}
    assert len(set(ALL)) == len(ALL)
    bars = make_bars()
    f = feats(bars)
    assert list(f.columns) == ALL and f.index.equals(bars.index)
    assert all(str(t) == "float64" for t in f.dtypes)
    assert np.isfinite(f[ltf.FEATURES].values).all(), "a feature is NaN or infinite"
    assert f[ltf.FEATURES].abs().values.max() <= 3.0
    unit = ["id_band", "id_or", "id_day_pos", "tq_di_15m", "tq_di_1h", "tq_bbw", "tq_squeeze", "tq_sq_release",
            "tq_st_15m", "tq_st_1h", "tq_st_flip", "tq_struct", "tq_bos", "tq_macd_15m", "tq_macd_rise_15m",
            "tq_macd_1h", "tq_macd_rise_1h", "tq_rsi_15m", "tq_rsi_1h", "cs_body_share"]
    assert f[unit].abs().values.max() <= 1.0
    assert set(np.unique(f["id_band"])) <= {-1.0, -0.5, 0.0, 0.5, 1.0}
    assert not np.isfinite(f[ltf.REACH_COLS].iloc[:ltf.REACH_MIN * 4].values).any()      # NaN before enough history
    assert np.isfinite(f[ltf.REACH_COLS].iloc[-1].values).all()


# ------------------------------------------------------------------ THE ONE RULE
CUTS = (700, 1500, 3333, 4804, 5760, 5761, 7003, 8990)   # 4804: its last bar closes on an hour; 5760 / 5761: around midnight


@pytest.mark.parametrize("holes", [False, True])
def test_no_lookahead(holes):
    """Cut the future off: every row before the cut must stay exactly the same, in EVERY column."""
    bars = make_bars(holes=holes)
    full = feats(bars)
    for col in ltf.FEATURES:                                         # the comparison must not be zero against zero
        assert (full[col] != 0).mean() > 0.005, "%s never speaks on the planted data" % col
    for col in ltf.RAW:
        assert full[col].iloc[:CUTS[-2]].notna().mean() > 0.005, "%s is never read on the planted data" % col
    for cut in CUTS:
        cut = min(cut, len(bars) - 5)
        part = feats(bars.iloc[:cut])                                # the bars end at the cut
        assert list(part.columns) == list(full.columns) and len(part) == cut
        for col in full.columns:
            assert same(full[col].iloc[:cut], part[col]), "%s changed when the bars were cut at %d" % (col, cut)
        part = feats(bars, index=bars.index[:cut])                   # only the index ends at the cut
        assert same(full.iloc[:cut], part), "a reading changed when the index was cut at %d" % cut


def test_bars_after_a_cut_do_not_reach_rows_before_it():
    """Rewrite every bar after the cut (prices, wicks and volume): nothing before the cut may move."""
    bars = make_bars(holes=True)
    full = feats(bars)
    for cut in (1500, 4804, 7003):
        later = bars.copy()
        rng = np.random.RandomState(cut)
        later.iloc[cut:, :4] = later.iloc[cut:, :4].values * 1.5
        later.iloc[cut:, 1] = later.iloc[cut:, 1].values * (1.0 + rng.rand(len(bars) - cut))
        later.iloc[cut:, 4] = later.iloc[cut:, 4].values * 7.0
        moved = feats(later)
        for col in full.columns:
            assert same(full[col].iloc[:cut], moved[col].iloc[:cut]), "%s saw bars after row %d" % (col, cut)
        assert not same(full.iloc[cut:], moved.iloc[cut:])           # and the rewrite was a real one


def test_index_rows_without_a_bar_are_no_read():
    bars = make_bars(n=3000)
    full = feats(bars)
    gone = bars.drop(bars.index[[100, 101, 2500]])
    f = feats(gone, index=bars.index)
    assert len(f) == len(bars)
    for row in (100, 101, 2500):
        assert (f[ltf.FEATURES].iloc[row] == 0.0).all() and f[ltf.RAW].iloc[row].isna().all()
    assert same(f.iloc[:100], full.iloc[:100])
    later = pd.date_range(bars.index[-1] + pd.Timedelta(minutes=15), periods=3, freq="15min")
    f = feats(bars, index=bars.index[-2:].append(later))
    assert same(f.iloc[:2], full.iloc[-2:]) and (f[ltf.FEATURES].iloc[2:] == 0.0).all().all()
    for unit in ("s", "ms", "us", "ns"):                             # pandas 3 keeps datetimes in mixed units
        assert same(feats(bars, index=bars.index.as_unit(unit)), full)
        other = bars.copy()
        other.index = bars.index.as_unit(unit)
        assert same(feats(other, index=bars.index), full)
    empty = ltf.features(bars.index[:5], A, bars=bars.iloc[:0])
    assert (empty[ltf.FEATURES] == 0.0).all().all() and empty[ltf.RAW].isna().all().all()


# ------------------------------------------------------------------ card 1: intraday levels
def test_vwap_of_a_hand_computed_day():
    """Monday is flat at 100 (volume 1 a bar). Tuesday opens with four bars at 100, 102, 104, 106 on
    volumes 1, 2, 3, 4, then two no-volume bars at 110 and 101, then nothing but no-volume bars."""
    bars = flat_bars(9)
    t0 = 96                                                          # Tuesday 00:00
    bars.iloc[t0:2 * 96, 4] = 0.0
    for k, (p, v) in enumerate([(100, 1), (102, 2), (104, 3), (106, 4), (110, 0), (101, 0)]):
        put(bars, t0 + k, p, p + 0.5, p - 0.5, p, v)
    f = feats(bars)
    assert np.allclose(f["id_vwap_d_px"].iloc[:96], 100.0) and np.allclose(f["id_vwap_w_px"].iloc[:96], 100.0)
    want = [100.0, 304.0 / 3.0, 616.0 / 6.0, 104.0]                  # sum(price x volume) / sum(volume), bar by bar
    assert np.allclose(f["id_vwap_d_px"].iloc[t0:t0 + 4], want, atol=1e-9)
    assert np.allclose(f["id_vwap_d_px"].iloc[t0 + 4:2 * 96], 104.0, atol=1e-9)       # no volume: the VWAP stands
    assert abs(f["id_vwap_d_sd_px"].iloc[t0 + 3] - 2.0) < 1e-9       # sqrt((1x16 + 2x4 + 3x0 + 4x4) / 10)
    assert abs(f["id_vwap_d_pct"].iloc[t0 + 3] - 100.0 * 2.0 / 104.0) < 1e-9
    week = (96 * 100.0 + 1040.0) / (96 + 10)                         # the week so far: Monday's 96 bars, Tuesday's four
    assert abs(f["id_vwap_w_px"].iloc[t0 + 3] - week) < 1e-9
    assert abs(f["id_vwap_w_pct"].iloc[t0 + 3] - 100.0 * (106.0 - week) / week) < 1e-9
    # the hour 00:00-01:00 closes with this bar: true range 106.5 - 99.5 = 7 after thirteen hours... of 1
    atr = f["ltf_atr1h"].iloc[t0 + 3]
    assert abs(f["ltf_atr1h"].iloc[t0 + 2] - 1.0) < 1e-9 and abs(atr - (13.0 * 1.0 + 7.0) / 14.0) < 1e-9
    assert abs(f["id_vwap_d"].iloc[t0 + 3] - 2.0 / atr) < 1e-9       # in hourly ATRs
    assert abs(f["id_vwap_w"].iloc[t0 + 3] - (106.0 - week) / (np.sqrt(7.0) * atr)) < 1e-9
    assert (f["id_band"].iloc[t0:t0 + 3] == 0.0).all()               # a session younger than an hour has no bands
    assert f["id_band"].iloc[t0 + 4] == 1.0                          # 110 is 3 sd above 104: the outer zone
    assert f["id_band"].iloc[t0 + 5] == -0.5                         # 101 is 1.5 sd below: between the bands
    assert f["id_band"].iloc[t0 + 6] == -1.0                         # 100 is 2 sd below
    assert abs(f["id_vwap_d_px"].iloc[2 * 96] - 100.0) < 1e-9        # Wednesday 00:00: a new day, a new VWAP
    assert abs(f["id_vwap_w_px"].iloc[2 * 96 - 1] - week) < 1e-9     # ... while the week carries on
    assert abs(f["id_vwap_w_px"].iloc[2 * 96] - (96 * 100.0 + 1040.0 + 100.0) / 107.0) < 1e-9
    assert abs(f["id_vwap_w_px"].iloc[7 * 96] - 100.0) < 1e-12       # next Monday 00:00: the weekly VWAP starts again
    assert f["id_vwap_w_px"].iloc[7 * 96 - 1] > 100.0


def test_opening_range_and_its_breakout():
    bars = flat_bars(4)
    d = 2 * 96                                                       # Wednesday 00:00
    for k, (h, l, c) in enumerate([(101, 99, 100), (103, 100, 102), (102, 98, 99), (101.5, 99.5, 100)]):
        put(bars, d + k, 100, h, l, c)
    put(bars, d + 6, 100, 104.5, 100, 104)                           # a close above the first hour's high
    put(bars, d + 8, 100, 100, 96.5, 97)                             # a close below its low
    put(bars, d + 10, 100, 105, 100, 100)                            # a wick above it, a close inside
    f = feats(bars)
    assert f["id_or_high_px"].iloc[d:d + 3].isna().all() and f["id_or_low_px"].iloc[d:d + 3].isna().all()
    assert (f["id_or"].iloc[d:d + 3] == 0.0).all()                   # unknown while the first hour is still open
    assert (f["id_or_high_px"].iloc[d + 3:d + 96] == 103.0).all() and (f["id_or_low_px"].iloc[d + 3:d + 96] == 98.0).all()
    assert f["id_or"].iloc[d + 3] == 0.0 and f["id_or"].iloc[d + 5] == 0.0
    assert f["id_or"].iloc[d + 6] == 1.0 and f["id_or"].iloc[d + 8] == -1.0 and f["id_or"].iloc[d + 10] == 0.0
    assert f["id_day_high_px"].iloc[d + 1] == 103.0 and f["id_day_high_px"].iloc[d + 6] == 104.5
    assert f["id_day_high_px"].iloc[d + 9] == 104.5 and f["id_day_high_px"].iloc[d + 10] == 105.0
    assert f["id_day_low_px"].iloc[d + 7] == 98.0 and f["id_day_low_px"].iloc[d + 8] == 96.5
    assert abs(f["id_day_pos"].iloc[d + 6] - (2.0 * (104.0 - 98.0) / (104.5 - 98.0) - 1.0)) < 1e-12
    assert abs(f["id_day_pos"].iloc[d + 8] - (2.0 * (97.0 - 96.5) / (104.5 - 96.5) - 1.0)) < 1e-12
    assert f["id_or_high_px"].iloc[3 * 96] != f["id_or_high_px"].iloc[3 * 96]     # the next day starts unknown again
    assert f["id_or_high_px"].iloc[3 * 96 + 3] == 100.5


# ------------------------------------------------------------------ card 2: trend quality and squeeze
def _ref_adx(h, l, c, n):
    """Wilder's ADX in a plain loop: s = s + (x - s) / n, started at the first value."""
    size = len(c)
    tr, plus, minus = np.zeros(size), np.zeros(size), np.zeros(size)
    for i in range(size):
        tr[i] = h[i] - l[i] if i == 0 else max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        if i:
            up, dn = h[i] - h[i - 1], l[i - 1] - l[i]
            plus[i] = up if (up > dn and up > 0) else 0.0
            minus[i] = dn if (dn > up and dn > 0) else 0.0
    out = np.full((size, 3), np.nan)
    st = sp = sm = sx = None
    for i in range(size):
        st = tr[i] if i == 0 else st + (tr[i] - st) / n
        sp = plus[i] if i == 0 else sp + (plus[i] - sp) / n
        sm = minus[i] if i == 0 else sm + (minus[i] - sm) / n
        if i >= n - 1:
            pdi, mdi = 100.0 * sp / st, 100.0 * sm / st
            dx = 100.0 * abs(pdi - mdi) / (pdi + mdi)
            sx = dx if sx is None else sx + (dx - sx) / n
            out[i, 1:] = pdi, mdi
            if i >= 2 * n - 2:
                out[i, 0] = sx
    return out


def test_adx_matches_a_plain_loop_and_reads_a_trend():
    bars = make_bars(n=600)
    got = ltf.adx(bars, 14)
    ref = _ref_adx(bars["high"].values, bars["low"].values, bars["close"].values, 14)
    assert np.allclose(got[["adx", "plus", "minus"]].values, ref, equal_nan=True, atol=1e-9)
    n = 400                                                          # 200 bars up, then 200 down
    path = np.concatenate([100.0 + 0.3 * np.arange(200), 160.0 - 0.3 * np.arange(200)])
    rng = np.random.RandomState(3)
    close = path + rng.normal(0, 0.05, n)
    opn = np.concatenate([[100.0], close[:-1]])
    bars = pd.DataFrame({"open": opn, "high": np.maximum(opn, close) + 0.1, "low": np.minimum(opn, close) - 0.1,
                         "close": close, "volume": 1.0}, index=pd.date_range(MONDAY, periods=n, freq="15min", tz="UTC"))
    f = feats(bars)
    assert f["tq_adx15"].iloc[150] > 40 and f["tq_plus_di15"].iloc[150] > f["tq_minus_di15"].iloc[150]
    assert f["tq_di_15m"].iloc[150] > 0.5 and f["tq_adx_15m"].iloc[150] > 0.6
    assert f["tq_minus_di15"].iloc[390] > f["tq_plus_di15"].iloc[390] and f["tq_di_15m"].iloc[390] < -0.5
    assert f["tq_adx1h"].iloc[190] > 40 and f["tq_di_1h"].iloc[190] > 0.5
    # Supertrend: up through the rise, one flip soon after the top, down afterwards, and it counts the bars
    assert (f["tq_st_15m"].iloc[60:200] == 1.0).all() and (f["tq_st_15m"].iloc[230:] == -1.0).all()
    flip = int(np.flatnonzero(f["tq_st_15m"].values[200:] == -1.0)[0]) + 200
    assert 200 < flip < 230
    assert f["tq_st_bars_15m"].iloc[flip] == 0 and f["tq_st_bars_15m"].iloc[flip + 20] == 20
    assert f["tq_st_flip"].iloc[flip] == -1.0 and f["tq_st_flip"].iloc[flip + 4] == -0.5 and f["tq_st_flip"].iloc[flip + 8] == 0.0
    assert f["tq_st_1h"].iloc[190] == 1.0 and f["tq_st_1h"].iloc[399] == -1.0
    assert f["tq_rsi15"].iloc[150] > 70 and f["tq_rsi15"].iloc[390] < 30 and f["tq_rsi_15m"].iloc[390] < -0.4
    # MACD histogram: above zero while the rise is still gathering pace, below zero and falling just after the top
    assert f["tq_macd_15m"].iloc[40] == 1.0 and f["tq_macd_15m"].iloc[212] == -1.0 and f["tq_macd_rise_15m"].iloc[206] == -1.0
    assert f["tq_macd_1h"].iloc[236] == -1.0 and f["tq_macd_rise_1h"].iloc[220] == -1.0


def test_structure_flips_from_higher_highs_to_lower_lows():
    """A zigzag through planted turning points. Each swing is known SWING_K = 5 bars after its bar."""
    turns = [(0, 100), (10, 110), (20, 105), (30, 115), (40, 108), (50, 112), (60, 102), (70, 106), (80, 98), (95, 99)]
    rows = np.arange(96)
    close = np.interp(rows, [r for r, _p in turns], [p for _r, p in turns]).astype(float)
    opn = np.concatenate([[100.0], close[:-1]])
    high, low = np.maximum(opn, close), np.minimum(opn, close)
    for r, _p in turns[1:-1:2]:
        high[r] += 0.5                                               # the peaks: 110.5, 115.5, 112.5, 106.5
    for r, _p in turns[2:-1:2]:
        low[r] -= 0.5                                                # the troughs: 104.5, 107.5, 101.5, 97.5
    bars = pd.DataFrame({"open": opn, "high": high, "low": low, "close": close, "volume": 1.0},
                        index=pd.date_range(MONDAY, periods=96, freq="15min", tz="UTC"))
    f = feats(bars)
    hi, lo, s = f["tq_swing_hi_px"], f["tq_swing_lo_px"], f["tq_struct"]
    assert hi.iloc[:15].isna().all() and hi.iloc[15] == 110.5        # the peak of bar 10 appears at bar 15, not before
    assert lo.iloc[:25].isna().all() and lo.iloc[25] == 104.5
    assert hi.iloc[34] == 110.5 and hi.iloc[35] == 115.5 and f["tq_swing_hi_prev_px"].iloc[35] == 110.5
    assert lo.iloc[44] == 104.5 and lo.iloc[45] == 107.5 and f["tq_swing_lo_prev_px"].iloc[45] == 104.5
    assert (s.iloc[:45] == 0.0).all()                                # two highs and two lows are not known before bar 45
    assert (s.iloc[45:55] == 1.0).all()                              # higher highs and higher lows
    assert (s.iloc[55:65] == 0.0).all()                              # a lower high (112.5), the low still higher: mixed
    assert (s.iloc[65:85] == -1.0).all()                             # lower highs and lower lows (101.5 known at bar 65)
    # breaks of structure: the first close above 110.5 is bar 26 (111), the first close below 107.5 is bar 55 (107)
    b = f["tq_bos"]
    assert (b.iloc[:26] == 0.0).all()
    assert [b.iloc[26 + k] for k in range(9)] == [1.0, 0.875, 0.75, 0.625, 0.5, 0.375, 0.25, 0.125, 0.0]
    assert f["tq_bos_bars"].iloc[26] == 0 and f["tq_bos_dir"].iloc[30] == 1.0
    assert b.iloc[54] == 0.0 and b.iloc[55] == -1.0 and b.iloc[59] == -0.5 and b.iloc[63] == 0.0
    words = ltf.facts(f.iloc[50], A)["Trend quality and squeeze"][3][1]
    assert words.startswith("higher highs and higher lows") and "110.50 then 115.50" in words
    assert ltf.facts(f.iloc[70], A)["Trend quality and squeeze"][3][1].startswith("lower highs and lower lows")
    assert "not enough" in ltf.facts(f.iloc[20], A)["Trend quality and squeeze"][3][1]


def test_squeeze_and_its_release():
    n = 140
    close = np.where(np.arange(n) % 2 == 0, 100.05, 99.95)           # 80 quiet bars: closes barely move, ranges are wide
    close[80:] = 100.0 + 2.0 * np.arange(1, n - 80 + 1)              # then price walks away upward
    opn = np.concatenate([[100.0], close[:-1]])
    bars = pd.DataFrame({"open": opn, "high": np.maximum(opn, close) + 0.5, "low": np.minimum(opn, close) - 0.5,
                         "close": close, "volume": 1.0}, index=pd.date_range(MONDAY, periods=n, freq="15min", tz="UTC"))
    f = feats(bars)
    assert (f["tq_squeeze"].iloc[20:80] == 1.0).all()                # Bollinger (0.1 wide) inside Keltner (1.5 wide)
    assert f["tq_sq_bars_on"].iloc[79] == 79 - 19 + 1                # on since bar 19, the first with 20 closes
    assert f["tq_sq_bars_since"].iloc[20:80].isna().all() and (f["tq_sq_release"].iloc[:80] == 0.0).all()
    rel = int(np.flatnonzero(f["tq_squeeze"].values[80:] == 0.0)[0]) + 80
    assert 80 <= rel <= 84
    assert f["tq_sq_dir"].iloc[rel] == 1.0 and f["tq_sq_bars_since"].iloc[rel] == 0 and f["tq_sq_release"].iloc[rel] == 1.0
    assert f["tq_sq_release"].iloc[rel + 2] == 0.75 and f["tq_sq_release"].iloc[rel + 8] == 0.0
    assert f["tq_sq_bars_since"].iloc[rel + 10] == 10 and f["tq_sq_bars_on"].iloc[rel + 10] == 0
    assert "released upward 3 bars ago" in ltf.facts(f.iloc[rel + 3], A)["Trend quality and squeeze"][1][1]
    assert ltf.facts(f.iloc[60], A)["Trend quality and squeeze"][1][1].startswith("ON for 42 bars")


def test_relative_volume_is_against_the_same_hour_of_day():
    bars = flat_bars(25, volume=100.0)
    tod = data.to_ms(bars.index) % DAY
    noon = (tod >= 12 * HOUR) & (tod < 13 * HOUR)
    bars.loc[noon, "volume"] = 300.0                                 # every day trades three times as much from 12:00 to 13:00
    last = np.flatnonzero(noon)[-4:]
    bars.iloc[last, 4] = 540.0                                       # the last day: 1.8 times its usual noon hour
    f = feats(bars)
    usual_day = np.flatnonzero(noon)[-8:-4][-1]                      # 12:45 of the day before
    assert abs(f["tq_rvol_x"].iloc[usual_day] - 1.0) < 1e-12 and abs(f["tq_rvol"].iloc[usual_day]) < 1e-12
    assert abs(f["tq_rvol_x"].iloc[last[-1]] - 1.8) < 1e-12
    assert abs(f["tq_rvol"].iloc[last[-1]] - np.log2(1.8)) < 1e-12
    assert f["tq_rvol_x"].iloc[:ltf.RVOL_MIN_DAYS * 96].isna().all() and f["tq_rvol_x"].iloc[ltf.RVOL_MIN_DAYS * 96 + 3] == 1.0
    assert ltf.facts(f.iloc[last[-1]], A)["Trend quality and squeeze"][5][1] == "1.8x usual for this hour of day"


# ------------------------------------------------------------------ card 3: candle size and realistic targets
def test_average_body_and_range():
    n = 96 * 20                                                      # up 1, down 1, for ever; every candle spans 99.5 to 101.5
    even = np.arange(n) % 2 == 0
    bars = pd.DataFrame({"open": np.where(even, 100.0, 101.0), "high": 101.5, "low": 99.5,
                         "close": np.where(even, 101.0, 100.0), "volume": 1.0},
                        index=pd.date_range(MONDAY, periods=n, freq="15min", tz="UTC"))
    f = feats(bars)
    body, rng = (1.0 + 100.0 / 101.0) / 2.0, (2.0 + 200.0 / 101.0) / 2.0     # % of each candle's own open, averaged
    assert f["cs_body15_pct"].iloc[:95].isna().all()
    assert abs(f["cs_body15_pct"].iloc[95] - body) < 1e-9 and abs(f["cs_range15_pct"].iloc[-1] - rng) < 1e-9
    row = f.iloc[-1]                                                 # an odd candle: opens 101, closes 100
    assert abs(row["cs_last_body_x"] - (100.0 / 101.0) / body) < 1e-9 and abs(row["cs_body"] - np.log2(row["cs_last_body_x"])) < 1e-9
    assert abs(row["cs_last_body_share"] - 0.5) < 1e-12 and abs(row["cs_body_share"]) < 1e-12
    assert abs(row["cs_expand_x"] - 1.0) < 1e-9 and abs(row["cs_expand"]) < 1e-9
    # an hour (and four hours, and a day) opens at 100, closes at 100 and spans 99.5 to 101.5: body 0%, range 2%
    assert f["cs_range1h_pct"].iloc[:48 * 4 - 1].isna().all() and abs(f["cs_range1h_pct"].iloc[48 * 4 - 1] - 2.0) < 1e-9
    assert f["cs_range4h_pct"].iloc[:30 * 16 - 1].isna().all() and abs(f["cs_range4h_pct"].iloc[30 * 16 - 1] - 2.0) < 1e-9
    assert abs(row["cs_body1h_pct"]) < 1e-12 and abs(row["cs_body4h_pct"]) < 1e-12 and abs(row["cs_body1d_pct"]) < 1e-12
    assert abs(row["cs_adr_pct"] - 2.0) < 1e-9
    bars.iloc[-1, :4] = [101.0, 101.5, 97.0, 98.0]                   # a last candle three times the size: body 3, range 4.5
    f = feats(bars)
    row = f.iloc[-1]
    assert abs(row["cs_last_body_share"] - 3.0 / 4.5) < 1e-12 and abs(row["cs_body_share"] - (2.0 * 3.0 / 4.5 - 1.0)) < 1e-12
    assert row["cs_last_body_x"] > 2.9 and row["cs_expand_x"] > 1.2 and row["cs_expand"] > 0
    facts = ltf.facts(row, A)["Candle size and realistic targets"]
    want = (row["cs_body15_pct"], row["cs_body15_pct"] * 0.98, row["cs_range15_pct"], row["cs_range15_pct"] * 0.98)
    assert facts[0][1] == "%.2f%% / $%.2f body, %.2f%% / $%.2f range" % want     # % of price, and that % of the close (98)
    assert facts[0][1].startswith("1.02% / $1.00 body, 2.02% / $1.98 range")
    assert "expanding" in facts[4][1] and "67% body / 33% wick" in facts[4][1]


def test_known_adr_and_range_used():
    """Every day is flat at 100 but for one wick to 101 and one to 99: a 2% day, twenty times over."""
    bars = flat_bars(20, wick=0.0)
    for day in range(16):
        put(bars, day * 96 + 30, 100, 101, 100, 100)
        put(bars, day * 96 + 60, 100, 100, 99, 100)
    d = 16 * 96
    put(bars, d + 24, 100, 100.5, 100, 100)                          # day 17: half a percent up by 06:15 ...
    put(bars, d + 40, 100, 100, 99.5, 100)                           # ... and half a percent down by 10:15
    f = feats(bars)
    assert f["cs_adr_pct"].iloc[:14 * 96 - 1].isna().all()           # fourteen CLOSED days are needed ...
    assert abs(f["cs_adr_pct"].iloc[14 * 96 - 1] - 2.0) < 1e-12      # ... and the 14th closes with its 23:45 bar
    assert abs(f["cs_adr_pct"].iloc[d + 40] - 2.0) < 1e-12
    assert f["cs_used_x"].iloc[d] == 0.0 and f["cs_used"].iloc[d] == -1.0
    assert abs(f["cs_used_x"].iloc[d + 24] - 0.25) < 1e-12 and abs(f["cs_used_x"].iloc[d + 39] - 0.25) < 1e-12
    assert abs(f["cs_used_x"].iloc[d + 40] - 0.5) < 1e-12 and abs(f["cs_used"].iloc[d + 40] + 0.5) < 1e-12
    assert abs(f["cs_today_range_pct"].iloc[d + 95] - 1.0) < 1e-12
    assert abs(f["cs_used_x"].iloc[15 * 96 + 59] - 0.5) < 1e-12 and abs(f["cs_used_x"].iloc[15 * 96 + 60] - 1.0) < 1e-12
    assert f["cs_used"].iloc[15 * 96 + 60] == 0.0                    # exactly one average day travelled
    row = ltf.facts(f.iloc[d + 40], A)["Candle size and realistic targets"]
    assert row[2] == ["Average daily range (14 days)", "2.00% / $2.00"]
    assert row[3][1] == "50% of an average day (today so far: 1.00% / $1.00)"


def test_reach_ratios_on_a_ramp(monkeypatch):
    """Price climbs 0.01 a bar for ever. The largest move within the next N bars is N x 0.01 and the
    hourly ATR is 4 x 0.01, so the ratios are N / 4 = 1, 4 and 24; each is known N bars late."""
    monkeypatch.setattr(ltf, "REACH_WIN", 48)
    monkeypatch.setattr(ltf, "REACH_MIN", 24)
    n, step = 600, 0.01
    opn = 100.0 + step * np.arange(n)
    bars = pd.DataFrame({"open": opn, "high": opn + step, "low": opn, "close": opn + step, "volume": 1.0},
                        index=pd.date_range(MONDAY, periods=n, freq="15min", tz="UTC"))
    f = feats(bars)
    assert np.allclose(f["ltf_atr1h"].iloc[60:], 4 * step, atol=1e-9)
    # the ATR exists from the 14th hour (bar 55), so the 24th ratio is the hour that closes with bar 147
    for tag, n_bars in ltf.REACH_HORIZONS.items():
        first = 147 + n_bars                                         # ... and it is history only n_bars bars later
        for stat in ("med", "p80"):
            col = f["reach_%s_%s_pct" % (tag, stat)]
            assert col.iloc[:first].isna().all(), "%s is read before its ratios are history" % col.name
            want = 100.0 * (n_bars * step) / bars["close"].values[first:]
            assert np.allclose(col.iloc[first:].values, want, atol=1e-9), col.name
    c = bars["close"].iloc[-1]
    words = ltf.facts(f.iloc[-1], A)["Candle size and realistic targets"][5][1]
    assert words.startswith("1h %.2f%% ($0.0400), 4h %.2f%% ($0.16), 24h %.2f%% ($0.96)" % (4 / c, 16 / c, 96 / c))


def _brute_reach(bars, atr, n_bars, window, least, q):
    """The definition, written the slow way: at row i, of the hourly-sampled bars whose n_bars-bar
    future had fully closed by row i, take the last `window`; reach = their median (or quantile)
    ratio x the hourly ATR now, as a % of the close."""
    ms = data.to_ms(bars.index)
    h, l, c = bars["high"].values, bars["low"].values, bars["close"].values
    size = len(c)
    sampled = [t for t in range(size) if ms[t] % HOUR == HOUR - BAR]
    ratio = {}
    for t in sampled:
        if t + n_bars <= size - 1 and atr[t] == atr[t]:
            ratio[t] = max(h[t + 1:t + n_bars + 1].max() - c[t], c[t] - l[t + 1:t + n_bars + 1].min()) / atr[t]
    med, top = np.full(size, np.nan), np.full(size, np.nan)
    for i in range(size):
        history = [t for t in sampled if t + n_bars <= i][-window:]
        vals = [ratio[t] for t in history if t in ratio]
        if len(vals) >= least:
            med[i] = 100.0 * np.median(vals) * atr[i] / c[i]
            top[i] = 100.0 * np.quantile(vals, q) * atr[i] / c[i]
    return med, top


def test_reach_matches_the_definition_written_the_slow_way(monkeypatch):
    monkeypatch.setattr(ltf, "REACH_WIN", 60)
    monkeypatch.setattr(ltf, "REACH_MIN", 20)
    bars = make_bars(n=1300, seed=5, holes=True)
    f = feats(bars)
    atr = f["ltf_atr1h"].values
    for tag, n_bars in ltf.REACH_HORIZONS.items():
        med, top = _brute_reach(bars, atr, n_bars, 60, 20, ltf.REACH_Q)
        assert np.isfinite(med).sum() > 500
        assert np.allclose(f["reach_%s_med_pct" % tag].values, med, equal_nan=True, rtol=1e-9, atol=1e-12), tag
        assert np.allclose(f["reach_%s_p80_pct" % tag].values, top, equal_nan=True, rtol=1e-9, atol=1e-12), tag
        assert (top[np.isfinite(top)] >= med[np.isfinite(med)]).all()


# ------------------------------------------------------------------ plain English
def test_describe_and_facts_are_readable():
    bars = make_bars(holes=True)
    f = feats(bars)
    titles = [t for t, _f in ltf.GROUPS.values()]
    for row in (f.iloc[-1], f.iloc[5000], f.iloc[40], f.iloc[0], dict(f.iloc[-1]), pd.Series(dtype=float), {}):
        said, shown = ltf.describe(row, A), ltf.facts(row, A)
        assert list(said) == titles and list(shown) == titles
        for title in titles:
            assert isinstance(said[title], str) and said[title].endswith(".") and "nan" not in said[title].lower()
            assert 4 <= len(shown[title]) <= 6
            for label, value in shown[title]:
                assert isinstance(label, str) and isinstance(value, str) and "nan" not in value.lower() and "inf" not in value
    shown = ltf.facts(f.iloc[-1], "ETHUSDT")
    text = " ".join(v for rows in shown.values() for _l, v in rows)
    assert "n/a" not in text and "$" in text and "%" in text
    last = f.iloc[-1]
    travel = shown["Candle size and realistic targets"][5][1]
    for col in ltf.REACH_COLS:                                       # the owner reads the very numbers the columns hold
        assert ("%.2f%%" % last[col]) in travel
    assert ("$%.2f" % (last["reach_24h_med_pct"] / 100.0 * last["ltf_close"])) in travel
    assert ltf.describe(f.iloc[-1], "ETHUSDT")["Intraday levels (VWAP and opening range)"].startswith("ETH closed at")
    assert "No read" in ltf.describe({}, A)["Candle size and realistic targets"]
