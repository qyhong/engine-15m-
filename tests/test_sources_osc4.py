# -*- coding: utf-8 -*-
"""osc4 (card pipeline batch 3: Williams %R, CMF/OBV, Elder-Ray, pivot points, RSI divergence): no look-ahead on
synthetic and real bars, sane ranges, daily / weekly / 4h values wait for their close, textbook values, plain-English
cards, honest "no read" without volume, and NOT yet wired into sources.MODULES."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import data, sources  # noqa: E402
from engine15.sources import osc4  # noqa: E402

COLS = osc4.FEATURES + osc4.RAW
M15 = pd.Timedelta(minutes=15)


def bars(n=96 * 60, seed=7, volume=True):
    rng = np.random.RandomState(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    o = np.concatenate([[100.0], c[:-1]])
    sp = np.abs(rng.normal(0, 0.002, n)) * c
    idx = pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC")
    df = pd.DataFrame({"open": o, "high": np.maximum(o, c) + sp, "low": np.minimum(o, c) - sp, "close": c}, index=idx)
    if volume:
        df["volume"] = rng.lognormal(3.0, 0.6, n)
    return df


B = bars()
FULL = osc4.features(B.index, "TEST", bars=B)


def _same(full, part, cut):
    a = full.iloc[:cut][COLS].values.astype(float)
    p = part[COLS].values.astype(float)
    bad = ~np.isclose(a, p, equal_nan=True, atol=1e-9)
    assert not bad.any(), (cut, [c for c, x in zip(COLS, bad.any(axis=0)) if x])


def test_no_look_ahead_synthetic():
    for cut in (96 * 9 + 5, 96 * 20 + 7, 96 * 33 + 50, 96 * 47 + 16, 96 * 56 - 1, len(B) - 3):
        _same(FULL, osc4.features(B.index[:cut], "TEST", bars=B.iloc[:cut]), cut)


@pytest.mark.parametrize("asset", ["BTCUSDT", "XAUUSD"])
def test_no_look_ahead_real_bars(asset):
    try:
        b = data.load(asset)
    except Exception as ex:                                           # pragma: no cover - data file missing
        pytest.skip("no bars for %s: %s" % (asset, ex))
    b = b.iloc[-96 * 90:]
    full = osc4.features(b.index, asset, bars=b)
    assert not full.attrs["errors"], full.attrs["errors"]
    n = len(b)
    for cut in (n // 3 + 11, n // 2 + 37, (3 * n) // 4 + 2, n - 5):
        _same(full, osc4.features(b.index[:cut], asset, bars=b.iloc[:cut]), cut)


def test_ranges_and_reads():
    f = FULL
    assert not f.attrs["errors"], f.attrs["errors"]
    assert not f[osc4.FEATURES].isna().any().any()
    assert (f[osc4.FEATURES].abs() <= 1.0).all().all()
    late = f.iloc[96 * 30:]
    for tag, _ in osc4.TFS4:
        w = late["wr_raw_" + tag].dropna()
        assert len(w) and ((w >= -100) & (w <= 0)).all()
    for tag, _ in osc4.TFS_HTF:
        m = late["cmf_raw_" + tag]
        assert m.notna().all() and (m.abs() <= 1).all()
        assert late["eld_ema_" + tag].notna().all()
        assert (late["eld_bull_raw_" + tag] >= late["eld_bear_raw_" + tag]).all()       # high >= low
        assert set(late["eld_slope_" + tag].unique()) <= {-1.0, 0.0, 1.0}
        for k in ("bull", "bear"):
            a = late["obvdiv_%s_age_%s" % (k, tag)].dropna()
            assert ((a >= 0) & (a <= osc4.OBV_HOLD)).all()
    for tag, _ in osc4.PIV_TAGS:
        lv = late[["pvt_%s_%s" % (k, tag) for k in osc4.CLASSIC]].values
        assert np.isfinite(lv).all() and (np.diff(lv, axis=1) >= -1e-9).all()
        cam = late[["pvt_%s_%s" % (k, tag) for k in osc4.CAMARILLA]].values
        assert (np.diff(cam, axis=1) >= -1e-9).all()
        c = B["close"].reindex(late.index)
        assert (late["pvt_above_px_" + tag].dropna() > c[late["pvt_above_px_" + tag].notna()]).all()
        assert (late["pvt_below_px_" + tag].dropna() <= c[late["pvt_below_px_" + tag].notna()]).all()
        assert (late["pvt_above_atr_" + tag].dropna() > 0).all() and (late["pvt_below_atr_" + tag].dropna() >= 0).all()
    for tag, _ in osc4.TFS_DIV:
        r = late["rdiv_rsi_" + tag]
        assert r.notna().all() and ((r >= 0) & (r <= 100)).all()
        for k in ("bull", "bear"):
            a = f["rdiv_%s_age_%s" % (k, tag)].dropna()
            assert ((a >= 0) & (a <= osc4.DIV_HOLD)).all()
    assert (f["rdiv_15m"] != 0).any() and (f["obvdiv_1h"] != 0).any()      # the event cards do fire sometimes


def _changes_only_at(col, ok):
    s = FULL[col].dropna()
    changed = s.index[1:][~np.isclose(s.values[1:], s.values[:-1], rtol=0, atol=1e-12)]
    assert len(changed), col
    bad = [t for t in changed if not ok(t + M15)]
    assert not bad, (col, bad[:3])


def test_higher_timeframes_wait_for_their_close():
    """Rows are keyed by OPEN time; the row's close (open + 15 min) is what decides."""
    midnight = lambda t: t == t.normalize()                                    # noqa: E731
    monday = lambda t: t == t.normalize() and t.weekday() == 0                  # noqa: E731
    four = lambda t: t == t.floor("4h")                                          # noqa: E731
    hour = lambda t: t == t.floor("1h")                                          # noqa: E731
    for col in ("wr_raw_1d", "cmf_raw_1d", "eld_ema_1d", "pvt_p_day", "pvt_r3_day", "pvt_h4_day", "pvt_atr_d"):
        _changes_only_at(col, midnight)
    for col in ("pvt_p_wk", "pvt_s3_wk", "pvt_l4_wk"):
        _changes_only_at(col, monday)
    for col in ("wr_raw_4h", "cmf_raw_4h", "eld_ema_4h", "rdiv_rsi_4h"):
        _changes_only_at(col, four)
    for col in ("wr_raw_1h", "eld_ema_1h", "rdiv_rsi_1h"):
        _changes_only_at(col, hour)


def test_weekly_pivots_are_the_prior_completed_week():
    close = FULL.index + M15
    key = close.normalize() - pd.to_timedelta(close.weekday, unit="D")         # Monday 00:00 of the row's close
    for wk in key.unique()[2:6]:
        prior = B[(B.index >= wk - pd.Timedelta(days=7)) & (B.index < wk)]
        lv = osc4.pivot_levels(prior["high"].max(), prior["low"].min(), prior["close"].iloc[-1])
        rows = FULL[key == wk]
        for k in ("p", "r1", "s3", "h4", "l3"):
            assert np.allclose(rows["pvt_%s_wk" % k].values, lv[k]), (wk, k)


def test_daily_pivots_textbook():
    """Day 1 has high 110, low 90, close 105: day 2 reads the textbook classic and Camarilla levels."""
    idx = pd.date_range("2025-03-03", periods=96 * 3, freq="15min", tz="UTC")
    c = np.full(len(idx), 100.0)
    c[95] = 105.0
    h, l = c + 1.0, c - 1.0
    h[10], l[20] = 110.0, 90.0
    df = pd.DataFrame({"open": c, "high": h, "low": l, "close": c, "volume": 1.0}, index=idx)
    f = osc4.features(idx, "TEST", bars=df)
    day2 = f[(f.index + M15).normalize() == idx[96]]
    want = {"p": 305.0 / 3, "r1": 2 * 305.0 / 3 - 90, "s1": 2 * 305.0 / 3 - 110, "r2": 305.0 / 3 + 20,
            "s2": 305.0 / 3 - 20, "r3": 110 + 2 * (305.0 / 3 - 90), "s3": 90 - 2 * (110 - 305.0 / 3),
            "h4": 116.0, "h3": 110.5, "l3": 99.5, "l4": 94.0}
    for k, v in want.items():
        assert np.allclose(day2["pvt_%s_day" % k].values, v), (k, day2["pvt_%s_day" % k].iloc[0], v)
    assert abs(want["p"] - 101.6666667) < 1e-6 and abs(want["r3"] - 133.3333333) < 1e-6
    # before the first day closes there is no daily pivot
    assert f[(f.index + M15) < idx[96]]["pvt_p_day"].isna().all()
    # the close (100) is in S1-P, below P, inside L3-H3 (99.5 < 100 < 110.5); the nearest level above is P, below L3
    r = day2.iloc[5]
    assert r["pvt_zone_day"] == pytest.approx((3 - 3.5) / 3.5)
    assert r["pvt_above_px_day"] == pytest.approx(want["p"]) and r["pvt_below_px_day"] == pytest.approx(99.5)
    s = osc4.describe(r, "TEST")["Pivot points (daily and weekly)"]
    assert "daily P 101.67 with price below it in S1-P" in s and "above P" in s and "below L3 99.5" in s


def test_williams_r_textbook():
    hi = np.array([12, 14, 20, 15, 13, 12, 11, 12, 13, 14, 15, 14, 13, 12.5], float)
    lo = np.array([10, 11, 13, 12, 11, 10, 11, 10.5, 11, 12, 13, 12, 11, 11.5], float)
    cl = np.full(14, 12.0)                                                        # HH 20, LL 10, close 12
    df = pd.DataFrame({"high": hi, "low": lo, "close": cl})
    w = osc4.williams_r(df)
    assert w.iloc[:13].isna().all() and w.iloc[-1] == pytest.approx(-80.0)
    df.loc[13, "close"] = 20.0
    assert osc4.williams_r(df).iloc[-1] == pytest.approx(0.0)
    flat = pd.DataFrame({"high": np.ones(14), "low": np.ones(14), "close": np.ones(14)})
    assert osc4.williams_r(flat).isna().all()                                     # flat window: no read


def test_cmf_textbook():
    rng = np.random.RandomState(3)
    n = 25
    lo = 100 + rng.normal(0, 1, n)
    hi = lo + rng.uniform(0.5, 2.0, n)
    cl = lo + rng.uniform(0, 1, n) * (hi - lo)
    v = rng.uniform(10, 100, n)
    df = pd.DataFrame({"high": hi, "low": lo, "close": cl, "volume": v})
    got = osc4.cmf(df)
    for i in range(19, n):
        s = slice(i - 19, i + 1)
        mfv = ((cl[s] - lo[s]) - (hi[s] - cl[s])) / (hi[s] - lo[s]) * v[s]
        assert got.iloc[i] == pytest.approx(mfv.sum() / v[s].sum())
    assert got.iloc[:19].isna().all()
    const = pd.DataFrame({"high": np.full(20, 12.0), "low": np.full(20, 10.0), "close": np.full(20, 11.5),
                          "volume": rng.uniform(1, 9, 20)})
    assert osc4.cmf(const).iloc[-1] == pytest.approx(0.5)                        # ((1.5) - (0.5)) / 2


def test_obv_divergence_flag():
    """A new 20-bar closing high on falling volume flow is flagged; one OBV confirms is not."""
    c = np.r_[np.linspace(100, 110, 20), np.linspace(110, 105, 10), np.linspace(105, 111, 3)]
    v = np.r_[np.full(20, 100.0), np.full(10, 100.0), np.full(3, 1.0)]
    df = pd.DataFrame({"high": c + 0.1, "low": c - 0.1, "close": c, "volume": v})
    bear, bull = osc4.obv_divergence(df)
    assert bear[-1] and not bear[:-1].any()
    df["volume"] = np.r_[np.full(30, 1.0), np.full(3, 1000.0)]
    bear, _ = osc4.obv_divergence(df)
    assert not bear[-1]


def _div_bars(flip=False):
    c = np.r_[np.full(20, 100.0), np.linspace(100, 80, 11)[1:], np.linspace(80, 95, 16)[1:],
              np.linspace(95, 79, 31)[1:], np.linspace(79, 90, 21)[1:]]
    if flip:
        c = 200.0 - c
    idx = pd.date_range("2025-01-01", periods=len(c), freq="15min", tz="UTC")
    return pd.DataFrame({"open": c, "high": c + 0.5, "low": c - 0.5, "close": c, "volume": 1.0}, index=idx)


def test_rsi_divergence_appears_only_once_confirmed():
    """Lows at bar 29 (fast drop, RSI near 0) and bar 74 (slow drift lower, RSI higher): a regular bullish
    divergence, visible from bar 74 + k on, with age 0 there; the mirror image gives the bearish one."""
    k = osc4.SWING_K
    d = osc4.rsi_divergence(_div_bars())
    lows = np.flatnonzero(osc4._swings(_div_bars()["low"].values, k, high=False))
    assert list(lows) == [29, 74]
    assert d["rsi"].iloc[74] > d["rsi"].iloc[29]
    assert d["bull_age"].iloc[:74 + k].isna().all()
    assert d["bull_age"].iloc[74 + k] == 0 and d["bull_age"].iloc[74 + k + 4] == 4
    assert d["bear_age"].isna().all()
    m = osc4.rsi_divergence(_div_bars(flip=True))
    assert m["bear_age"].iloc[74 + k] == 0 and m["bear_age"].iloc[:74 + k].isna().all() and m["bull_age"].isna().all()
    f = osc4.features(_div_bars().index, "TEST", bars=_div_bars())
    assert f["rdiv_15m"].iloc[74 + k] == 1.0 and f["rdiv_15m"].iloc[74 + k - 1] == 0.0
    assert "bullish divergence" in osc4.describe(f.iloc[74 + k], "TEST")["RSI divergence (15m to 4h)"]


def test_describe_one_sentence_per_card():
    say = osc4.describe(FULL.iloc[-1], "TEST")
    assert list(say) == [t for t, _ in osc4.GROUPS.values()]
    for title, text in say.items():
        assert isinstance(text, str) and text.endswith(".") and text.count(". ") == 0, (title, text)
        assert "no read" not in text, (title, text)
    for word in ("will", "expect", "likely", "should"):
        assert not any(word in t for t in say.values())                            # no forecasts


def test_no_volume_is_no_read():
    nb = bars(n=96 * 20, volume=False)
    for asset, b in (("TEST", nb), ("USDJPY", bars(n=96 * 20))):
        f = osc4.features(b.index, asset, bars=b)
        vraw = [c for c in osc4.RAW if c.startswith(("cmf", "obvdiv"))]
        vfeat = [c for c in osc4.FEATURES if c.startswith(("cmf", "obvdiv"))]
        assert f[vraw].isna().all().all() and (f[vfeat] == 0.0).all().all()
        assert f["wr_raw_15m"].notna().any() and f["eld_ema_1h"].notna().any() and f["pvt_p_day"].notna().any()
        say = osc4.describe(f.iloc[-1], asset)
        assert "no read" in say["Chaikin money flow and OBV (1h to daily)"]
        assert "no read" not in say["Williams %R (15m to daily)"]
    assert "USDJPY" in say["Chaikin money flow and OBV (1h to daily)"]
    zero = bars(n=96 * 20)
    zero["volume"] = 0.0
    f = osc4.features(zero.index, "TEST", bars=zero)
    assert f["cmf_raw_1h"].isna().all() and (f["obvdiv_1d"] == 0).all()


def test_index_unit_does_not_matter():
    """data.load gives a millisecond index; pandas arithmetic can return microseconds. Same readings either way."""
    for unit in ("ms", "us", "ns"):
        bm = B.copy()
        bm.index = bm.index.as_unit(unit)
        f = osc4.features(bm.index, "TEST", bars=bm)
        assert f["pvt_p_wk"].notna().sum() == FULL["pvt_p_wk"].notna().sum() > 0
        assert np.allclose(f[COLS].values, FULL[COLS].values, equal_nan=True), unit


def test_names_do_not_collide():
    import importlib
    mine = set(COLS) | set(osc4.GROUPS)
    assert len(COLS) == len(set(COLS))
    sdir = os.path.dirname(osc4.__file__)
    for fn in os.listdir(sdir):
        name = fn[:-3]
        if not fn.endswith(".py") or name in ("osc4", "__init__", "_util"):
            continue
        try:
            m = importlib.import_module("engine15.sources." + name)
        except Exception:                                                        # pragma: no cover
            continue
        theirs = set(getattr(m, "GROUPS", {})) | set(getattr(m, "FEATURES", [])) | set(getattr(m, "RAW", []))
        theirs |= set(f for _t, fs in getattr(m, "GROUPS", {}).values() for f in fs)
        assert not (mine & theirs), (name, mine & theirs)
    from engine15 import evidence
    assert not (mine & ((set(evidence.GROUPS) | set(evidence.FEATURES)) - mine))   # wired: evidence now holds osc4 itself


def test_wired_as_v5_2_3():
    assert "osc4" in sources.MODULES                                             # wired as think15-v5.2.3 (16 Nov 2026)
