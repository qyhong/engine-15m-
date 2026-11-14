# -*- coding: utf-8 -*-
"""engine15/sources/overnight.py checked on planted data. No network; files only in a temporary folder.

    py -3 -m pytest tests/test_overnight.py -q        (from the project folder)
"""
import os
import sys
from collections import OrderedDict

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import extdata  # noqa: E402
from engine15.sources import overnight as on  # noqa: E402

NY = "America/New_York"
BASIS = 1.004                                          # planted futures / cash ratio
BAR = pd.Timedelta(minutes=15)
OHLC = ["open", "high", "low", "close"]


def make(start="2024-01-02", end="2024-04-06", seed=3):
    """A random walk on CME equity-futures hours (Sunday 18:00 to Friday 17:00 New York, shut 17:00-18:00);
    each bar opens where the last kept bar closed. Cash = the futures bars inside NYSE hours / BASIS.
    -> (cash 15m frame as data.load returns it, futures frame as load_series returns it)."""
    grid = pd.date_range(start, end, freq="15min", tz="UTC")
    loc = grid.tz_convert(NY)
    wd, mins = np.asarray(loc.dayofweek), np.asarray(loc.hour) * 60 + np.asarray(loc.minute)
    shut = (wd == 5) | ((wd == 6) & (mins < 1080)) | ((wd == 4) & (mins >= 1020)) | ((mins >= 1020) & (mins < 1080))
    idx = grid[~shut]
    rng = np.random.RandomState(seed)
    n = len(idx)
    close = 4700.0 * np.exp(np.cumsum(rng.normal(0, 0.0012, n)))
    opn = np.concatenate([[4700.0], close[:-1]])
    spread = np.abs(rng.normal(0, 0.0006, n)) * close
    fut = pd.DataFrame({"open": opn, "high": np.maximum(opn, close) + spread, "low": np.minimum(opn, close) - spread,
                        "close": close, "volume": 1.0, "src": 1.0}, index=pd.DatetimeIndex(idx, name="open_time"))
    cash = fut.loc[extdata.open_mask("SPX", fut.index), OHLC] / BASIS
    cash["volume"], cash["taker_buy"] = 1.0, np.nan
    return cash, fut


def feats(cash, fut, index=None):
    return on.features(cash.index if index is None else index, "SPX", bars=cash, fut=fut)


def same(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return a.shape == b.shape and bool(np.all((a == b) | (np.isnan(a) & np.isnan(b))))


def close_enough(a, b, tol=1e-9):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    both = np.isfinite(a) & np.isfinite(b)
    return bool(np.array_equal(np.isfinite(a), np.isfinite(b)) and np.all(np.abs(a[both] - b[both]) <= tol * (1 + np.abs(b[both]))))


@pytest.fixture(scope="module")
def planted():
    cash, fut = make()
    return cash, fut, feats(cash, fut)


def _day_rows(f, day):
    return f[f.index.tz_convert(NY).normalize() == pd.Timestamp(day, tz=NY)]


# ------------------------------------------------------------------ the module's shape
def test_api():
    assert list(on.GROUPS) == ["overnight"] and on.GROUPS["overnight"][0] == "S&P futures overnight"
    assert on.APPLIES == {"overnight": ("SPX",)}
    assert 3 <= len(on.FEATURES) <= 6 and len(set(on.FEATURES + on.RAW)) == len(on.FEATURES + on.RAW)
    for fn in ("update", "features", "describe", "facts"):
        assert callable(getattr(on, fn))


def test_shapes_ranges_and_every_column_speaks(planted):
    cash, fut, f = planted
    assert list(f.columns) == on.FEATURES + on.RAW and len(f) == len(cash) and not f.attrs["errors"]
    x = f[on.FEATURES].values
    assert np.isfinite(x).all() and np.abs(x).max() <= on.CLIP
    for col in on.FEATURES:
        assert (f[col] != 0).mean() > 0.3, "%s rarely speaks" % col
    for col in on.RAW:
        if col not in ("on_fill_bars",):
            assert f[col].notna().mean() > 0.5, "%s is rarely read" % col
    assert f["on_fill_bars"].notna().any()
    assert (f["on_roll"].dropna() == 0).all() and (f["on_src"].dropna() == 1).all()


# ------------------------------------------------------------------ the readings, checked by hand
def test_one_session_by_hand(planted):
    cash, fut, f = planted
    day = "2024-02-07"                                               # a Wednesday
    rows = _day_rows(f, day)
    today = cash[cash.index.tz_convert(NY).normalize() == pd.Timestamp(day, tz=NY)]
    yday = cash[cash.index.tz_convert(NY).normalize() == pd.Timestamp("2024-02-06", tz=NY)]
    t_prev, t_open = yday.index[-1] + BAR, today.index[0]            # 16:00 yesterday, 09:30 today (UTC instants)
    win = fut[(fut.index >= t_prev) & (fut.index + BAR <= t_open)]
    p0 = fut.loc[t_prev - BAR, "close"]                              # the futures bar that closed at 16:00
    fo = fut.loc[t_open - BAR, "close"]                              # ... and at 09:30
    pc, op = yday["close"].iloc[-1], today["open"].iloc[0]
    k = pc / p0
    r = rows.iloc[0]
    assert len(win) == 66 and r["on_bars"] == 66 and r["on_hours"] == 17.5
    assert np.isclose(r["on_prev_close"], pc) and np.isclose(r["on_open"], op)
    assert np.isclose(r["on_gap_pct"], 100 * (op / pc - 1))
    assert np.isclose(r["on_move_pct"], 100 * (fo / p0 - 1))
    assert np.isclose(r["on_high_px"], win["high"].max() * k) and np.isclose(r["on_low_px"], win["low"].min() * k)
    assert np.isclose(r["on_basis_pct"], 100 * (BASIS - 1))
    assert np.isclose(r["on_open_pos_pct"], 100 * (fo - win["low"].min()) / (win["high"].max() - win["low"].min()))
    path = np.abs(np.diff(np.concatenate([[p0], win["close"].values]))).sum()
    assert np.isclose(r["on_er"], (fo - p0) / path)
    # sessions: late US to 18:00 New York yesterday, Asia to 08:00 London, Europe to 09:30
    t_asia = pd.Timestamp("2024-02-06 18:00", tz=NY).tz_convert("UTC")
    t_eur = pd.Timestamp("2024-02-07 08:00", tz="Europe/London").tz_convert("UTC")
    pa = fut[fut.index + BAR <= t_asia]["close"].iloc[-1]            # 17:00 close: the futures are shut 17:00-18:00
    pe = fut.loc[t_eur - BAR, "close"]
    assert fut[fut.index + BAR <= t_asia].index[-1] == pd.Timestamp("2024-02-06 16:45", tz=NY)
    assert np.isclose(r["on_late_pct"], 100 * (pa / p0 - 1)) and np.isclose(r["on_asia_pct"], 100 * (pe / pa - 1))
    assert np.isclose(r["on_europe_pct"], 100 * (fo / pe - 1))
    # the day's readings do not change through the session; position and fill do
    for col in ("on_gap_pct", "on_move_pct", "on_high_px", "on_low_px", "on_gap_atr", "on_typical_pct"):
        assert rows[col].nunique() == 1, col
    c = rows["on_close"].values
    assert np.allclose(rows["on_pos_pct"], 100 * (c - r["on_low_px"]) / (r["on_high_px"] - r["on_low_px"]))
    assert np.allclose(rows["on_high_atr"], (r["on_high_px"] - c) / rows["on_atr1h"])
    # the typical move: mean |move| of the previous 20 sessions
    firsts = f.groupby(f.index.tz_convert(NY).normalize()).first()
    pos = list(firsts.index).index(pd.Timestamp(day, tz=NY))
    assert np.isclose(r["on_typical_pct"], firsts["on_move_pct"].abs().iloc[pos - 20:pos].mean())


def test_gap_fill_by_hand():
    cash, fut = make(seed=5)
    day = pd.Timestamp("2024-03-06", tz=NY)
    today = cash.index.tz_convert(NY).normalize() == day
    i0 = np.flatnonzero(today)[0]
    pc = cash["close"].iloc[i0 - 1]
    cash = cash.copy()
    # an up gap of 0.6%, then price walks back down: reaches yesterday's close in the 5th bar
    path = pc * np.array([1.006, 1.005, 1.004, 1.002, 0.999, 1.001])
    for j, px in enumerate(path):
        o = pc * 1.006 if j == 0 else path[j - 1]
        cash.iloc[i0 + j, :4] = [o, max(o, px) + 0.01, min(o, px) - 0.01, px]
    f = feats(cash, fut)
    rows = f.iloc[i0:i0 + 6]
    assert np.isclose(rows["on_gap_pct"].iloc[0], 0.6)
    assert (rows["on_filled"].values == [0, 0, 0, 0, 1, 1]).all()
    assert np.isnan(rows["on_fill_bars"].iloc[3]) and (rows["on_fill_bars"].iloc[4:] == 5).all()
    expect = np.clip((pc * 1.006 - (np.minimum.accumulate(np.minimum(np.r_[pc * 1.006, path[:-1]], path)) - 0.01))
                     / (pc * 0.006), 0, 1)
    assert np.allclose(rows["on_fill_pct"], 100 * expect)
    assert (rows["on_fill"] <= 0).all() and rows["on_fill"].iloc[-1] == -1.0      # an up gap filling: negative
    assert rows["on_gap"].iloc[0] > 0


# ------------------------------------------------------------------ THE ONE RULE
CUTS = (300, 801, 1000, 1001, 1013, 1500, 1690)                  # 1,716 cash rows: mid-session, first bar, last bar


def test_no_lookahead(planted):
    """Cut the cash bars after row k and the futures at the close of row k: rows up to k must not change."""
    cash, fut, full = planted
    assert any(full["on_move_pct"].iloc[:CUTS[0]].notna())
    for k in CUTS:
        t = cash.index[k] + BAR                                       # the close of row k
        part = feats(cash.iloc[:k + 1], fut[fut.index + BAR <= t])
        assert list(part.columns) == list(full.columns) and len(part) == k + 1
        for col in full.columns:
            assert same(full[col].iloc[:k + 1], part[col]), "%s changed when the data was cut at row %d" % (col, k)
        part = feats(cash, fut, index=cash.index[:k + 1])             # only the index ends at the cut
        assert same(full.iloc[:k + 1], part)


def test_cut_at_the_open_has_the_whole_overnight(planted):
    """At the first cash close (09:45) the overnight window is complete: cutting the futures at 09:30 or at
    09:45 gives the same first row."""
    cash, fut, full = planted
    first = np.flatnonzero(np.diff(cash.index.tz_convert(NY).normalize().asi8) != 0) + 1
    for k in first[25:30]:
        t_open = cash.index[k]
        a = feats(cash.iloc[:k + 1], fut[fut.index + BAR <= t_open])
        assert same(full.iloc[k], a.iloc[k])


def test_futures_traded_during_the_cash_session_are_never_read(planted):
    """Rewrite every futures bar from 09:30 to 15:45 New York on the days the cash market trades (the bar
    ending at 16:00 gives the basis; on a cash holiday the futures day is part of the overnight): nothing moves."""
    cash, fut, full = planted
    loc = fut.index.tz_convert(NY)
    mins = np.asarray(loc.hour) * 60 + np.asarray(loc.minute)
    traded = np.asarray(loc.normalize().isin(cash.index.tz_convert(NY).normalize().unique()))
    day = (mins >= 570) & (mins < 945) & traded
    other = fut.copy()
    rng = np.random.RandomState(9)
    other.loc[day, OHLC] = other.loc[day, OHLC].values * (1.3 + rng.rand(int(day.sum()), 1))
    moved = feats(cash, other)
    assert same(full.values, moved.values)


def test_later_bars_do_not_reach_earlier_rows(planted):
    cash, fut, full = planted
    for k in (900, 1601):
        t = cash.index[k] + BAR
        c2, f2 = cash.copy(), fut.copy()
        c2.iloc[k + 1:, :4] = c2.iloc[k + 1:, :4].values * 1.5
        f2.loc[f2.index + BAR > t, OHLC] = f2.loc[f2.index + BAR > t, OHLC].values * 0.7
        moved = feats(c2, f2)
        assert same(full.iloc[:k + 1].values, moved.iloc[:k + 1].values)
        assert not same(full.iloc[k + 1:].values, moved.iloc[k + 1:].values)


# ------------------------------------------------------------------ rolls, stray prints, holes
def test_contract_roll_at_the_sunday_reopen_is_removed(planted):
    cash, fut, full = planted
    reopen = pd.Timestamp("2024-03-10 18:00", tz=NY).tz_convert("UTC")     # Sunday
    rolled = fut.copy()
    rolled.loc[rolled.index >= reopen, OHLC] *= 1.008                       # the next contract, 0.8% dearer
    f = feats(cash, rolled)
    monday = _day_rows(f, "2024-03-11")
    assert (monday["on_roll"] == 1).all() and (f["on_roll"].drop(monday.index).dropna() == 0).all()
    for col in on.RAW:
        if col in ("on_basis_pct", "on_roll"):
            continue
        assert close_enough(f[col], full[col]), col
    assert close_enough(f[on.FEATURES], full[on.FEATURES])
    # without the roll check the Monday move would carry the 0.8% step
    old = on.ROLL_GUARD
    try:
        on.ROLL_GUARD = 1.0
        g = feats(cash, rolled)
    finally:
        on.ROLL_GUARD = old
    assert np.isclose(_day_rows(g, "2024-03-11")["on_move_pct"].iloc[0] - monday["on_move_pct"].iloc[0], 0.8, atol=0.02)


def test_a_step_with_no_break_to_place_it_is_no_read(planted):
    cash, fut, full = planted
    mid = pd.Timestamp("2024-03-12 02:00", tz=NY).tz_convert("UTC")         # in continuous trading: not a break
    stepped = fut.copy()
    stepped.loc[stepped.index >= mid, OHLC] *= 1.008
    stepped.loc[mid, "open"] = stepped.loc[mid - BAR, "close"]              # and no stray open to repair either
    f = feats(cash, stepped)
    tue = _day_rows(f, "2024-03-12")
    assert (tue["on_roll"] == 2).all() and tue["on_move_pct"].isna().all() and (tue["on_move"] == 0).all()
    assert tue["on_gap_pct"].notna().all()                                  # the cash gap is still read
    assert "futures" in on.describe(tue.iloc[0], "SPX")["S&P futures overnight"]


def test_a_stray_open_is_repaired(planted):
    cash, fut, full = planted
    t = pd.Timestamp("2024-02-08 03:00", tz=NY).tz_convert("UTC")
    bad = fut.copy()
    bad.loc[t, "open"] = bad.loc[t, "high"] = bad.loc[t, "close"] * 1.03
    f = feats(cash, bad)
    day = _day_rows(f, "2024-02-08")
    ref = _day_rows(full, "2024-02-08")
    hi = max(fut.loc[t - BAR, "close"], fut.loc[t, "close"])
    win = fut[(fut.index >= pd.Timestamp("2024-02-07 16:00", tz=NY)) & (fut.index < pd.Timestamp("2024-02-08 09:30", tz=NY))]
    exp_high = max(win.drop(t)["high"].max(), hi) / BASIS
    assert np.isclose(day["on_high_px"].iloc[0], exp_high)
    assert day["on_high_px"].iloc[0] <= ref["on_high_px"].iloc[0] + 1e-9
    assert abs(day["on_high_px"].iloc[0] / (bad.loc[t, "open"] / BASIS) - 1) > 0.01


def test_missing_futures_and_other_assets_are_no_read(planted):
    cash, fut, full = planted
    f = feats(cash, fut.iloc[:0])
    assert "futures" in f.attrs["errors"] and f["on_move_pct"].isna().all() and f["on_gap_pct"].notna().any()
    assert (f[["on_move", "on_pos", "on_trend"]] == 0).all().all()
    g = on.features(cash.index, "BTCUSDT", bars=cash, fut=fut)
    assert (g[on.FEATURES] == 0).all().all() and g[on.RAW].isna().all().all()
    hole = fut[(fut.index < pd.Timestamp("2024-02-13 20:00", tz=NY)) | (fut.index >= pd.Timestamp("2024-02-14 04:00", tz=NY))]
    h = _day_rows(feats(cash, hole), "2024-02-14")
    assert h["on_move_pct"].notna().all() and (h["on_bars"] == 34).all()    # an 8-hour hole: the window keeps its ends
    hole = fut[(fut.index < pd.Timestamp("2024-02-13 20:00", tz=NY)) | (fut.index >= pd.Timestamp("2024-02-14 09:00", tz=NY))]
    h = _day_rows(feats(cash, hole), "2024-02-14")
    assert h["on_move_pct"].isna().all() and (h["on_bars"] == 14).all()     # 14 bars: under six hours, no read
    hole = fut[fut.index < pd.Timestamp("2024-02-14 08:30", tz=NY)]
    hole = pd.concat([hole, fut[fut.index >= pd.Timestamp("2024-02-14 09:30", tz=NY)]])
    h = _day_rows(feats(cash, hole), "2024-02-14")
    assert h["on_move_pct"].isna().all()                                    # no futures price within 30 min of 09:30


def test_index_rows_without_a_cash_bar_are_no_read(planted):
    cash, fut, full = planted
    idx = cash.index[:500].union(pd.DatetimeIndex([cash.index[10] + pd.Timedelta(minutes=5)]))
    f = feats(cash, fut, index=idx)
    extra = f.loc[cash.index[10] + pd.Timedelta(minutes=5)]
    assert (extra[on.FEATURES] == 0).all() and extra[on.RAW].isna().all()
    assert same(f.drop(extra.name).values, full.iloc[:500].values)


# ------------------------------------------------------------------ plain English
def test_describe_and_facts(planted):
    cash, fut, full = planted
    title = on.GROUPS["overnight"][0]
    row = full.iloc[-1]
    say = on.describe(row, "SPX")
    assert list(say) == [title] and "opened" in say[title] and "overnight range" in say[title]
    fx = on.facts(row, "SPX")[title]
    assert 4 <= len(fx) <= 6 and all(len(p) == 2 and isinstance(p[1], str) for p in fx)
    assert on.describe(full.iloc[0], "SPX")[title].startswith("No read")              # the first session has no yesterday
    assert "S&P 500 only" in on.describe(row, "XAUUSD")[title]
    assert on.facts(full.iloc[0], "SPX")[title][0][1] == "n/a"


# ------------------------------------------------------------------ the stored series and update()
def _yahoo_from(frame):
    def fake(rng, now=None):
        fake.calls.append(rng)
        return frame.copy(), {}
    fake.calls = []
    return fake


def test_splice_keeps_the_cfd_and_scales_it():
    _cash, fut = make(end="2024-02-01")
    duka = fut.iloc[:-200].copy()
    duka[OHLC] = duka[OHLC] / 1.006                                         # the CFD sits 0.6% under the future
    es = fut.iloc[-1000:].copy()
    out, info = on.splice(duka, es)
    assert np.isclose(info["splice_ratio"], 1.006) and info["overlap_bars"] == 800
    assert np.allclose(out["close"].values, fut["close"].values)            # one level, no step at the join
    assert (out["src"].iloc[:-200] == 0).all() and (out["src"].iloc[-200:] == 1).all()


def test_update_builds_stitches_and_never_raises(tmp_path, monkeypatch):
    _cash, fut = make(end="2024-02-01")
    src = str(tmp_path)
    clock = [pd.Timestamp("2024-01-25 12:00", tz="UTC").timestamp()]
    monkeypatch.setattr(on, "_now", lambda: clock[0])
    monkeypatch.setattr(on, "_last_try", [0.0])
    monkeypatch.setattr(extdata, "read_dukascopy", lambda asset, start=None: fut[fut.index < "2024-01-20"][OHLC + ["volume"]])
    first = fut[(fut.index >= "2024-01-10") & (fut.index < "2024-01-25 11:00")]
    fake = _yahoo_from(first)
    monkeypatch.setattr(on, "_yahoo", fake)
    logs = []
    got = on.update(log=logs.append, src_dir=src)
    assert isinstance(got, OrderedDict) and got["overnight_ES"] == len(fut[fut.index < "2024-01-25 11:00"])
    assert fake.calls == ["60d"] and os.path.exists(on.path_for(src))
    stored = on.load_series(src)
    assert np.allclose(stored["close"].values, fut.loc[stored.index, "close"].values)

    # fresh: no request
    clock[0] = pd.Timestamp("2024-01-25 11:20", tz="UTC").timestamp()
    on.update(log=logs.append, src_dir=src)
    assert fake.calls == ["60d"]
    # stale, and Yahoo now serves another contract 1% higher: the new bars are stitched on at the stored level
    clock[0] = pd.Timestamp("2024-01-26 12:00", tz="UTC").timestamp()
    os.utime(on.path_for(src), (clock[0] - 86400, clock[0] - 86400))       # written yesterday on the test's clock
    newer = fut[(fut.index >= "2024-01-22") & (fut.index < "2024-01-26 11:00")].copy()
    newer[OHLC] *= 1.01
    fake2 = _yahoo_from(newer)
    monkeypatch.setattr(on, "_yahoo", fake2)
    got = on.update(log=logs.append, src_dir=src)
    assert fake2.calls == ["5d"] and got["overnight_ES"] == len(fut[fut.index < "2024-01-26 11:00"])
    stored = on.load_series(src)
    assert np.allclose(stored["close"].values, fut.loc[stored.index, "close"].values)
    assert any("scaled" in m for m in logs)
    # asked a minute ago: no second request
    clock[0] += 60
    fake3 = _yahoo_from(newer)
    monkeypatch.setattr(on, "_yahoo", fake3)
    os.utime(on.path_for(src), (clock[0] - 120, clock[0] - 120))
    on.update(log=logs.append, src_dir=src)
    assert fake3.calls == []

    # failures: kept file, a reason, no exception
    def boom(rng, now=None):
        raise RuntimeError("HTTP 429")
    monkeypatch.setattr(on, "_yahoo", boom)
    clock[0] += 3 * 3600
    os.utime(on.path_for(src), (clock[0] - 7200, clock[0] - 7200))
    before = os.path.getsize(on.path_for(src))
    got = on.update(log=logs.append, src_dir=src)
    assert got["overnight_ES"].startswith("failed:") and "429" in got["overnight_ES"]
    assert os.path.getsize(on.path_for(src)) == before
    monkeypatch.setattr(extdata, "read_dukascopy", lambda *a, **k: (_ for _ in ()).throw(OSError("no store")))
    got = on.update(log=logs.append, src_dir=str(tmp_path / "empty"))
    assert got["overnight_ES"].startswith("failed:")
    on.update(log=None, src_dir=str(tmp_path / "empty"))                    # even a broken logger does not raise


def test_futures_hours():
    t = lambda s: pd.Timestamp(s, tz=NY).timestamp()                         # noqa: E731
    assert on.futures_open(t("2024-01-10 03:00")) and on.futures_open(t("2024-01-07 18:15"))
    assert not on.futures_open(t("2024-01-10 17:30")) and not on.futures_open(t("2024-01-13 12:00"))
    assert not on.futures_open(t("2024-01-12 17:05")) and not on.futures_open(t("2024-01-07 17:00"))
