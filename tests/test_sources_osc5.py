# -*- coding: utf-8 -*-
"""osc5 (card pipeline batch 4: Fisher Transform, Ultimate Oscillator, TRIX, linear-regression channel, Mass Index):
no look-ahead on synthetic and real bars, sane ranges, daily / 4h / 1h values wait for their close, textbook values,
plain-English cards, and NOT yet wired into sources.MODULES."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import data, sources  # noqa: E402
from engine15.sources import osc5  # noqa: E402

COLS = osc5.FEATURES + osc5.RAW
M15 = pd.Timedelta(minutes=15)


def bars(n=96 * 150, seed=7):
    """A random walk whose volatility comes in bursts (so ranges widen and narrow: the Mass Index bulges)."""
    rng = np.random.RandomState(seed)
    vol = np.exp(1.2 * np.sin(np.arange(n) * 2 * np.pi / (96 * 9.3)) + 0.8 * np.sin(np.arange(n) * 2 * np.pi / 517.0))
    c = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.002, n) * vol))
    o = np.concatenate([[100.0], c[:-1]])
    sp = np.abs(rng.normal(0, 0.0015, n)) * c * vol
    idx = pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC")
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) + sp, "low": np.minimum(o, c) - sp, "close": c,
                         "volume": rng.lognormal(3.0, 0.6, n)}, index=idx)


B = bars()
FULL = osc5.features(B.index, "TEST", bars=B)


def _same(full, part, cut):
    a = full.iloc[:cut][COLS].values.astype(float)
    p = part[COLS].values.astype(float)
    bad = ~np.isclose(a, p, equal_nan=True, atol=1e-9)
    assert not bad.any(), (cut, [c for c, x in zip(COLS, bad.any(axis=0)) if x])


def test_no_look_ahead_synthetic():
    for cut in (96 * 9 + 5, 96 * 20 + 7, 96 * 33 + 50, 96 * 61 + 16, 96 * 90 - 1, 96 * 133 + 3, len(B) - 3):
        _same(FULL, osc5.features(B.index[:cut], "TEST", bars=B.iloc[:cut]), cut)


@pytest.mark.parametrize("asset", ["BTCUSDT", "XAUUSD"])
def test_no_look_ahead_real_bars(asset):
    try:
        b = data.load(asset)
    except Exception as ex:                                           # pragma: no cover - data file missing
        pytest.skip("no bars for %s: %s" % (asset, ex))
    b = b.iloc[-96 * 120:]
    full = osc5.features(b.index, asset, bars=b)
    assert not full.attrs["errors"], full.attrs["errors"]
    n = len(b)
    for cut in (n // 3 + 11, n // 2 + 37, (3 * n) // 4 + 2, n - 5):
        _same(full, osc5.features(b.index[:cut], asset, bars=b.iloc[:cut]), cut)


def test_ranges_and_reads():
    f = FULL
    assert not f.attrs["errors"], f.attrs["errors"]
    assert list(f.columns) == COLS
    assert not f[osc5.FEATURES].isna().any().any()
    assert (f[osc5.FEATURES].abs() <= 1.0).all().all()
    late = f.iloc[96 * 70:]                                            # the daily cards need up to 53 closed days
    assert late[osc5.RAW].drop(columns=[c for c in osc5.RAW if "_age_" in c or c.startswith("massb_")]).notna().all().all()
    for tag, _ in osc5.TFS_FISH:
        assert set(late["fishx_" + tag].unique()) <= {-1.0, 1.0}
        assert set(late["fishext_" + tag].unique()) <= {-1.0, 0.0, 1.0}
        ext = late["fish_raw_" + tag].abs() > osc5.FISH_EXT
        assert ((late["fishext_" + tag] != 0) == ext).all() and ext.any() and not ext.all()
        assert (late["fishx_" + tag] == np.sign(late["fish_raw_" + tag] - late["fish_trig_" + tag])).all()
        assert (late["fishx_age_" + tag].dropna() >= 0).all()
    for tag, _ in osc5.TFS_UO:
        u = late["uo_raw_" + tag]
        assert ((u >= 0) & (u <= 100)).all() and 40 < u.mean() < 60
        assert ((late["uoz_" + tag] == 1) == (u > 70)).all() and ((late["uoz_" + tag] == -1) == (u < 30)).all()
    for tag, _ in osc5.TFS_HTF:
        assert (late["trixz_" + tag] == np.sign(late["trix_raw_" + tag])).all()
        assert (np.sign(late["trix_atr_" + tag]) == np.sign(late["trix_raw_" + tag])).all()
        assert set(late["trixx_" + tag].unique()) <= {-1.0, 1.0}
        assert ((late["lrc_r2_" + tag] >= 0) & (late["lrc_r2_" + tag] <= 1)).all()
        assert (np.sign(late["lrc_slope_" + tag]) == np.sign(late["lrc_slope_raw_" + tag])).all()
        assert (late["lrc_se_" + tag] > 0).all()
        assert np.allclose(late["lrc_pos_" + tag], late["lrc_pos_raw_" + tag].clip(-1, 1))
        m = late["mass_raw_" + tag]
        assert ((m > 0) & (m < 3 * osc5.MASS_SUM)).all() and 23 < m.median() < 27
        age = f["massb_age_" + tag].dropna()
        assert ((age >= 0) & (age <= osc5.MASS_HOLD)).all()
        on = f["massb_" + tag] != 0
        assert (np.sign(f["massb_" + tag][on]) == -f["massb_trend_" + tag][on]).all()   # signed against the trend
    assert (f["massb_1h"] != 0).any() and (f["massb_4h"] != 0).any()         # the bulge does complete sometimes
    assert (f["uoz_15m"] != 0).any()


def _changes_only_at(col, ok):
    s = FULL[col].dropna()
    changed = s.index[1:][~np.isclose(s.values[1:], s.values[:-1], rtol=0, atol=1e-12)]
    assert len(changed), col
    bad = [t for t in changed if not ok(t + M15)]
    assert not bad, (col, bad[:3])


def test_higher_timeframes_wait_for_their_close():
    """Rows are keyed by OPEN time; the row's close (open + 15 min) is what decides."""
    midnight = lambda t: t == t.normalize()                                    # noqa: E731
    four = lambda t: t == t.floor("4h")                                          # noqa: E731
    hour = lambda t: t == t.floor("1h")                                          # noqa: E731
    for col in ("uo_raw_1d", "trix_raw_1d", "trix_sig_1d", "lrc_mid_1d", "lrc_slope_raw_1d", "mass_raw_1d"):
        _changes_only_at(col, midnight)
    for col in ("fish_raw_4h", "fish_trig_4h", "trix_raw_4h", "lrc_mid_4h", "lrc_pos_raw_4h", "mass_raw_4h"):
        _changes_only_at(col, four)
    for col in ("fish_raw_1h", "uo_raw_1h", "trix_raw_1h", "lrc_mid_1h", "mass_raw_1h"):
        _changes_only_at(col, hour)


def test_daily_value_is_the_last_closed_day():
    d1 = B.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"})
    uo = osc5.ultimate_oscillator(d1)
    close = FULL.index + M15
    for day in d1.index[[40, 77, 120]]:
        rows = FULL[close.normalize() == day + pd.Timedelta(days=1)]          # rows closing during the NEXT day ...
        rows = rows[(rows.index + M15) > day + pd.Timedelta(days=1)]
        assert len(rows) and np.allclose(rows["uo_raw_1d"].values[:-1], uo[day])   # ... read the day just closed


def test_fisher_textbook():
    rng = np.random.RandomState(1)
    n = 60
    med = 100 + np.cumsum(rng.normal(0, 1, n))
    df = pd.DataFrame({"high": med + 0.5, "low": med - 0.5, "close": med})
    got = osc5.fisher(df)
    x = f = 0.0
    want = np.full(n, np.nan)
    for i in range(osc5.FISH_N - 1, n):
        w = med[i - osc5.FISH_N + 1:i + 1]
        x = 0.33 * 2 * ((med[i] - w.min()) / (w.max() - w.min()) - 0.5) + 0.67 * x
        x = min(max(x, -0.999), 0.999)
        f = 0.5 * np.log((1 + x) / (1 - x)) + 0.5 * f
        want[i] = f
    assert np.allclose(got["fisher"].values, want, equal_nan=True)
    assert got["fisher"].iloc[:osc5.FISH_N - 1].isna().all()
    assert np.allclose(got["trigger"].values[1:], want[:-1], equal_nan=True)
    up = pd.DataFrame({"high": np.arange(40.0) + 1, "low": np.arange(40.0), "close": np.arange(40.0)})
    g = osc5.fisher(up)["fisher"]
    assert g.iloc[-1] > osc5.FISH_EXT and (g.diff().dropna() > 0).all()          # a steady climb pins it high
    flat = pd.DataFrame({"high": np.ones(20), "low": np.ones(20), "close": np.ones(20)})
    assert (osc5.fisher(flat)["fisher"].dropna() == 0).all()


def test_fisher_cross_side_and_age():
    side, age = osc5._side_and_age([np.nan, 1, 2, 3, 2, 1, 1, 4], [np.nan, np.nan, 1, 2, 3, 2, 1, 1])
    assert np.isnan(side[:2]).all() and list(side[2:]) == [1, 1, -1, -1, -1, 1]   # the tie keeps the old side
    assert np.isnan(age[:4]).all() and list(age[4:]) == [0, 1, 2, 0]


def test_ultimate_oscillator_textbook():
    rng = np.random.RandomState(5)
    n = 45
    c = 50 + np.cumsum(rng.normal(0, 1, n))
    h, l = c + rng.uniform(0.2, 1.5, n), c - rng.uniform(0.2, 1.5, n)
    got = osc5.ultimate_oscillator(pd.DataFrame({"high": h, "low": l, "close": c}))
    assert got.iloc[:28].isna().all()                                             # 28 bars each with a prior close
    for i in (28, 35, 44):
        avg = []
        for p in (7, 14, 28):
            j = np.arange(i - p + 1, i + 1)
            lo, hi = np.minimum(l[j], c[j - 1]), np.maximum(h[j], c[j - 1])
            avg.append((c[j] - lo).sum() / (hi - lo).sum())
        assert got.iloc[i] == pytest.approx(100 * (4 * avg[0] + 2 * avg[1] + avg[2]) / 7)
    top = pd.DataFrame({"high": np.arange(40.0) + 1, "low": np.arange(40.0), "close": np.arange(40.0) + 1})
    assert osc5.ultimate_oscillator(top).iloc[-1] == pytest.approx(100.0)         # every close on its high
    flat = pd.DataFrame({"high": np.ones(40), "low": np.ones(40), "close": np.ones(40)})
    assert osc5.ultimate_oscillator(flat).isna().all()                           # flat: no read


def test_trix_textbook():
    n = 120
    c = 100.0 * 1.01 ** np.arange(n)                                              # +1% a bar, every bar
    df = pd.DataFrame({"high": c * 1.001, "low": c * 0.999, "close": c})
    t = osc5.trix(df)
    first = 3 * (osc5.TRIX_N - 1) + 1
    assert t["trix"].iloc[:first].isna().all() and t["trix"].iloc[first:].notna().all()
    assert t["signal"].iloc[:first + osc5.TRIX_SIG - 1].isna().all() and np.isfinite(t["signal"].iloc[first + osc5.TRIX_SIG - 1])
    assert t["trix"].iloc[-1] == pytest.approx(1.0, abs=1e-3) and t["signal"].iloc[-1] == pytest.approx(1.0, abs=1e-2)
    assert t["atr"].iloc[-1] > 0
    e = pd.Series(c)
    for _ in range(3):                                                            # the plain triple EMA, unseeded
        e = e.ewm(span=osc5.TRIX_N, adjust=False).mean()
    assert t["trix"].iloc[-1] == pytest.approx(100 * (e.iloc[-1] / e.iloc[-2] - 1), abs=1e-3)
    assert osc5.trix(df.iloc[::-1].reset_index(drop=True))["trix"].iloc[-1] == pytest.approx(-100 * (1 - 1 / 1.01), abs=1e-3)


def test_linreg_channel_textbook():
    n = osc5.LRC_N
    rng = np.random.RandomState(2)
    x = np.arange(n + 10, dtype=float)
    c = 200.0 + 0.5 * x + rng.normal(0, 1.0, len(x))
    df = pd.DataFrame({"high": c + 1, "low": c - 1, "close": c})
    got = osc5.linreg_channel(df)
    assert got.iloc[:n - 1].isna().all().all()
    for i in (n - 1, n + 4, n + 9):
        y, xx = c[i - n + 1:i + 1], np.arange(n)
        slope, icpt = np.polyfit(xx, y, 1)
        fit = icpt + slope * xx
        se = np.sqrt(((y - fit) ** 2).sum() / (n - 2))
        r = got.iloc[i]
        assert r["slope_pct"] == pytest.approx(100 * slope / y[-1]) and r["mid"] == pytest.approx(fit[-1])
        assert r["r2"] == pytest.approx(np.corrcoef(xx, y)[0, 1] ** 2) and r["se"] == pytest.approx(se)
        assert r["pos"] == pytest.approx((y[-1] - fit[-1]) / (2 * se))
    line = pd.DataFrame({"high": x + 1, "low": x - 1, "close": 100 + 2.0 * x})
    r = osc5.linreg_channel(line).iloc[-1]
    assert r["r2"] == pytest.approx(1.0) and r["slope_pct"] == pytest.approx(200.0 / line["close"].iloc[-1])
    assert np.isnan(r["pos"])                                                    # zero-width channel: no position
    flat = pd.DataFrame({"high": np.full(60, 5.0), "low": np.full(60, 5.0), "close": np.full(60, 5.0)})
    r = osc5.linreg_channel(flat).iloc[-1]
    assert r["r2"] == 0.0 and r["slope_pct"] == 0.0 and np.isnan(r["pos"])
    f = osc5.features(B.index[:96 * 3], "TEST", bars=B.iloc[:96 * 3])              # 72 hourly bars: the 1h card reads
    assert f["lrc_mid_1h"].notna().any() and f["lrc_mid_4h"].isna().all() and (f["lrc_pos_4h"] == 0).all()


def test_mass_index_textbook():
    n = 80
    c = np.full(n, 100.0)
    const = pd.DataFrame({"high": c + 1, "low": c - 1, "close": c})
    mi = osc5.mass_index(const)
    first = 2 * (osc5.MASS_EMA - 1) + osc5.MASS_SUM - 1
    assert mi.iloc[:first].isna().all() and np.allclose(mi.iloc[first:], 25.0)   # a constant range: 25 x 1.0
    wide = const.copy()
    wide.loc[50:, "high"] += np.linspace(0, 20, n - 50)                           # ranges widening: ratio above 1
    assert osc5.mass_index(wide).iloc[-1] > 25.5
    rng = np.random.RandomState(4)
    hl = rng.uniform(1, 3, n)
    df = pd.DataFrame({"high": c + hl, "low": c, "close": c})
    e1 = np.full(n, np.nan)
    e1[8] = hl[:9].mean()
    for i in range(9, n):
        e1[i] = e1[i - 1] + 0.2 * (hl[i] - e1[i - 1])
    e2 = np.full(n, np.nan)
    e2[16] = e1[8:17].mean()
    for i in range(17, n):
        e2[i] = e2[i - 1] + 0.2 * (e1[i] - e2[i - 1])
    assert osc5.mass_index(df).iloc[-1] == pytest.approx((e1 / e2)[-25:].sum())


def test_mass_bulge_needs_27_then_26_5():
    mi = [25, 26.8, 26.4, 26.9, 27.1, 26.7, 27.3, 26.6, 26.4, 26.0, 26.8, 26.4, np.nan, 27.5, 26.5, 26.49]
    ev = osc5.mass_bulge(mi)
    assert list(np.flatnonzero(ev)) == [8, 15]              # not at 2 (never above 27), once per bulge, 26.5 is not below
    idx = pd.date_range("2025-01-01", periods=len(B) // 4, freq="1h", tz="UTC")
    h1 = B.resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).reindex(idx)
    fr = osc5.mass_frame(h1)
    ev = np.flatnonzero(osc5.mass_bulge(fr["mi"].values))
    assert len(ev) >= 2
    i = ev[1]
    assert fr["age"].iloc[i] == 0 and fr["btrend"].iloc[i] == fr["trend"].iloc[i]
    gap = (ev[2] - i) if len(ev) > 2 else 10 ** 6
    if gap > osc5.MASS_HOLD + 1:
        assert fr["age"].iloc[i + osc5.MASS_HOLD] == osc5.MASS_HOLD and np.isnan(fr["age"].iloc[i + osc5.MASS_HOLD + 1])
        assert fr["btrend"].iloc[i + 3] == fr["trend"].iloc[i]                     # the trend of the bulge bar is kept


def test_describe_one_sentence_per_card():
    say = osc5.describe(FULL.iloc[-1], "TEST")
    assert list(say) == [t for t, _ in osc5.GROUPS.values()]
    for title, text in say.items():
        assert isinstance(text, str) and text.endswith(".") and text.count(". ") == 0, (title, text)
        assert "no read" not in text, (title, text)
        assert "nan" not in text.lower(), (title, text)
    for i in range(96 * 70, len(FULL), 211):                                       # many rows: never a forecast word
        for text in osc5.describe(FULL.iloc[i], "TEST").values():
            assert text.endswith(".") and text.count(". ") == 0 and "nan" not in text.lower(), text
            for word in ("will", "expect", "likely", "should"):
                assert word not in text, text


def test_describe_says_what_the_row_holds():
    r = FULL.iloc[-1].copy()
    r["fish_raw_15m"], r["fishx_15m"], r["fishx_age_15m"] = 2.8, 1.0, 2.0
    r["uo_raw_1h"], r["uo_raw_1d"] = 74.0, 22.0
    r["trix_raw_4h"], r["trixx_4h"], r["trixx_age_4h"] = -0.05, -1.0, 0.0
    r["lrc_slope_raw_1d"], r["lrc_r2_1d"], r["lrc_pos_raw_1d"] = 0.4, 0.85, 1.3
    r["lrc_pos_raw_1h"] = -0.5
    r["mass_raw_1h"], r["massb_age_1h"], r["massb_trend_1h"] = 26.2, 3.0, 1.0
    r["mass_raw_4h"], r["massb_age_4h"], r["mass_trend_4h"] = 27.8, np.nan, -1.0
    say = osc5.describe(r, "TEST")
    t = say["Fisher Transform (15m to 4h)"]
    assert "15m +2.80 above its trigger (crossed up 2 bars ago), extreme high (above +2.5)" in t
    t = say["Ultimate Oscillator (15m, 1h, daily)"]
    assert "1h 74 overbought (above 70)" in t and "1d 22 oversold (below 30)" in t
    assert "4h -0.050% (below zero), below its signal line (crossed down on the last closed bar)" in say["TRIX (1h to daily)"]
    t = say["Linear-regression channel (1h to daily)"]
    assert "1d rising +0.400% per bar, R-squared 0.85 (a straight move), close above the upper channel line" in t
    assert "close 50% of the way from the middle to the lower line" in t
    t = say["Mass Index (1h to daily)"]
    assert "1h 26.2, reversal bulge completed 3 bars ago during an up-move" in t
    assert "4h 27.8, above 27, bulge forming, EMA9 falling" in t


def test_too_few_bars_is_no_read():
    nb = B.iloc[:20]
    f = osc5.features(nb.index, "TEST", bars=nb)
    assert not f.attrs["errors"]
    assert (f[[c for c in osc5.FEATURES if not c.startswith("fish")]] == 0).all().all()
    assert f[[c for c in osc5.RAW if not c.startswith("fish")]].isna().all().all()
    assert f["fish_raw_15m"].notna().sum() == 20 - osc5.FISH_N + 1                # the 9-bar card already reads
    say = osc5.describe(f.iloc[-1], "TEST")
    for title in list(say)[1:]:
        assert "no read" in say[title] and say[title].endswith("."), say[title]
    empty = osc5.features(B.index[:5], "TEST", bars=B.iloc[:0])
    assert (empty[osc5.FEATURES] == 0).all().all() and empty[osc5.RAW].isna().all().all()


def test_volume_is_not_needed():
    nv = B.iloc[:96 * 40].drop(columns=["volume"])
    f = osc5.features(nv.index, "USDJPY", bars=nv)
    assert not f.attrs["errors"]
    assert np.allclose(f[COLS].values, FULL.iloc[:96 * 40][COLS].values, equal_nan=True)


def test_index_unit_does_not_matter():
    """data.load gives a millisecond index; pandas arithmetic can return microseconds. Same readings either way."""
    for unit in ("ms", "us", "ns"):
        bm = B.copy()
        bm.index = bm.index.as_unit(unit)
        f = osc5.features(bm.index, "TEST", bars=bm)
        assert np.allclose(f[COLS].values, FULL[COLS].values, equal_nan=True), unit


def test_names_do_not_collide():
    import importlib
    mine = set(COLS) | set(osc5.GROUPS)
    assert len(COLS) == len(set(COLS))
    titles = [t for t, _ in osc5.GROUPS.values()]
    sdir = os.path.dirname(osc5.__file__)
    for fn in os.listdir(sdir):
        name = fn[:-3]
        if not fn.endswith(".py") or name in ("osc5", "__init__", "_util"):
            continue
        try:
            m = importlib.import_module("engine15.sources." + name)
        except Exception:                                                        # pragma: no cover
            continue
        theirs = set(getattr(m, "GROUPS", {})) | set(getattr(m, "FEATURES", [])) | set(getattr(m, "RAW", []))
        theirs |= set(f for _t, fs in getattr(m, "GROUPS", {}).values() for f in fs)
        assert not (mine & theirs), (name, mine & theirs)
        assert not (set(titles) & set(t for t, _ in getattr(m, "GROUPS", {}).values())), name
    if "osc5" not in sources.MODULES:                                            # once wired, evidence holds osc5 itself
        from engine15 import evidence
        assert not (mine & (set(evidence.GROUPS) | set(evidence.FEATURES)))


def test_wired_as_v5_2_4():
    assert "osc5" in sources.MODULES                                             # wired as think15-v5.2.4 (17 Nov 2026)
