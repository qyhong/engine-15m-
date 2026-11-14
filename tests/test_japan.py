# -*- coding: utf-8 -*-
"""engine15/sources/japan.py on planted bars and files. No network.

    py -3 -m pytest tests/test_japan.py -q        (from the project folder)
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15.sources import _util as U  # noqa: E402
from engine15.sources import japan  # noqa: E402

CUTS = ("2022-10-31 09:45", "2022-10-31 10:00", "2024-05-01 06:00", "2026-11-12 03:30")


def make_bars(start="2021-06-01", end="2026-11-20", seed=5):
    idx = pd.date_range(start, end, freq="15min", tz="UTC")
    idx = idx[idx.dayofweek < 5]                                     # FX: no weekend bars
    rng = np.random.RandomState(seed)
    close = 110.0 * np.exp(np.cumsum(rng.normal(0.00001, 0.0007, len(idx))))
    return pd.DataFrame({"open": close, "high": close * 1.0005, "low": close * 0.9995, "close": close,
                         "volume": 0.0, "taker_buy": np.nan}, index=idx)


def plant_events(folder):
    ev = pd.DataFrame({"ts_ms": [U.to_ms_vec(["2026-11-12 23:30"])[0], U.to_ms_vec(["2026-11-13 03:00"])[0]],
                       "title": ["Tokyo Core CPI y/y", "BOJ Policy Rate"], "impact": ["Medium", "High"],
                       "forecast": ["", ""], "previous": ["", ""],
                       "first_seen_ms": [U.to_ms_vec(["2026-11-09 06:00"])[0], U.to_ms_vec(["2026-11-11 06:00"])[0]]})
    U.write_csv(ev, japan.events_path(folder))
    U.save_state(japan.state_path(folder), {"first_feed_ms": int(U.to_ms_vec(["2026-11-09 06:00"])[0]),
                                            "last_feed_ms": int(U.to_ms_vec(["2026-11-11 06:00"])[0])})
    return ev


def same(a, b):
    return list(a.columns) == list(b.columns) and np.array_equal(a.values, b.values, equal_nan=True)


def test_no_lookahead_truncation(tmp_path):
    """Cut the bars and the index at T and drop feed events first seen after T: rows up to T are unchanged."""
    full_dir = str(tmp_path / "full")
    ev = plant_events(full_dir)
    bars = make_bars()
    full = japan.features(bars.index, "USDJPY", bars=bars, src_dir=full_dir)
    for cut in CUTS:
        t = pd.Timestamp(cut, tz="UTC")
        t_ms = int(t.value // 1000000)
        part_dir = str(tmp_path / ("cut%d" % t_ms))
        U.write_csv(ev[ev["first_seen_ms"] <= t_ms], japan.events_path(part_dir))
        st = U.load_state(japan.state_path(full_dir))
        if st["first_feed_ms"] <= t_ms:
            U.save_state(japan.state_path(part_dir), {"first_feed_ms": st["first_feed_ms"],
                                                      "last_feed_ms": min(st["last_feed_ms"], t_ms)})
        sub_bars = bars[bars.index + pd.Timedelta(minutes=15) <= t]
        part = japan.features(sub_bars.index, "USDJPY", bars=sub_bars, src_dir=part_dir)
        assert same(part, full.loc[sub_bars.index]), cut


def test_intervention_counts_only_after_confirmation(tmp_path):
    bars = make_bars("2022-06-01", "2022-11-30")
    f = japan.features(bars.index, "USDJPY", bars=bars, src_dir=str(tmp_path))
    before = f.loc[:"2022-09-22 08:30"]
    assert before["jp_mof_level"].isna().all() and (before["jp_mof_zone"] == 0).all()
    oct_ = f.loc["2022-10-25":"2022-10-31 09:30"]                   # the 21 Oct level is not yet confirmed
    assert (oct_["jp_mof_level"].dropna() == 145.90).all() or (oct_["jp_mof_level"].dropna() >= 145.90).all()
    assert not (oct_["jp_mof_level"] == 151.94).any()
    after = f.loc["2022-11-01":]
    assert (after["jp_mof_level"].dropna().isin([145.90, 149.45, 151.94])).all()


def test_boj_hours_and_the_2020_change(tmp_path):
    idx = pd.date_range("2026-12-10", "2026-12-19", freq="15min", tz="UTC")
    f = japan.features(idx, "USDJPY", bars=make_bars("2026-06-01", "2026-12-20"), src_dir=str(tmp_path))
    dec = pd.Timestamp("2026-12-18 03:00", tz="UTC")
    row = f.loc[dec - pd.Timedelta(hours=24, minutes=15)]          # closes exactly 24 h before
    assert row["jp_boj_hours"] == pytest.approx(24.0)
    assert row["jp_boj_next"] == pytest.approx(1.0 - 24.0 / 168.0)
    assert f.loc[dec - pd.Timedelta(minutes=15), "jp_boj_hours"] > 24 * 30   # at the decision: the next one (Jan)
    idx = pd.date_range("2020-03-10", "2020-03-17", freq="15min", tz="UTC")
    f = japan.features(idx, "USDJPY", bars=make_bars("2019-06-01", "2020-03-18"), src_dir=str(tmp_path))
    assert f.loc["2020-03-12 12:00", "jp_boj_hours"] == pytest.approx((pd.Timestamp("2020-03-19 03:00") -
                                                                       pd.Timestamp("2020-03-12 12:15")).total_seconds() / 3600)
    assert f.loc["2020-03-13 12:00", "jp_boj_hours"] == pytest.approx((pd.Timestamp("2020-03-16 03:00") -
                                                                       pd.Timestamp("2020-03-13 12:15")).total_seconds() / 3600)


def test_feed_events_are_used_from_first_seen(tmp_path):
    plant_events(str(tmp_path))
    idx = pd.date_range("2026-11-08", "2026-11-14", freq="15min", tz="UTC")
    f = japan.features(idx, "USDJPY", bars=make_bars("2026-05-01", "2026-11-20"), src_dir=str(tmp_path))
    assert f.loc[:"2026-11-09 05:30", "jp_event_hours"].isna().all()       # before the first read: no read
    assert f.loc["2026-11-10 00:00", "jp_event_hours"] != f.loc["2026-11-10 00:00", "jp_event_hours"]  # the High one unseen yet
    row = f.loc["2026-11-12 02:45"]                                        # closes 03:00, a day before the BoJ event
    assert row["jp_event_hours"] == pytest.approx(24.0) and row["jp_event_next"] == pytest.approx(0.0)
    assert f.loc["2026-11-12 14:45", "jp_event_next"] == pytest.approx(0.5)


def test_bounded_never_nan_and_other_assets(tmp_path):
    bars = make_bars()
    f = japan.features(bars.index, "USDJPY", bars=bars, src_dir=str(tmp_path))
    assert not f[japan.FEATURES].isna().any().any()
    assert (f[japan.FEATURES].abs() <= 1.0).all().all()
    assert f["jp_speed_1w_z"].notna().mean() > 0.8
    g = japan.features(bars.index[:1000], "XAUUSD", bars=bars, src_dir=str(tmp_path))
    assert (g[japan.FEATURES] == 0).all().all() and g[japan.RAW].isna().all().all()


def test_speed_reads_the_rows_own_close(tmp_path):
    bars = make_bars("2025-01-01", "2026-03-01")
    f = japan.features(bars.index, "USDJPY", bars=bars, src_dir=str(tmp_path))
    t = pd.Timestamp("2026-02-18 14:00", tz="UTC")
    week = bars["close"].asof(t - pd.Timedelta(days=7))
    assert f.loc[t, "jp_px"] == pytest.approx(bars.loc[t, "close"])
    assert f.loc[t, "jp_chg_1w_pct"] == pytest.approx(100 * (bars.loc[t, "close"] / week - 1))


def test_update_parses_feed_is_polite_and_never_raises(tmp_path, monkeypatch):
    folder = str(tmp_path)
    feed = [{"title": "BOJ Policy Rate", "country": "JPY", "date": "2026-12-18T00:00:00-05:00", "impact": "High",
             "forecast": "0.75%", "previous": "0.50%"},
            {"title": "CPI m/m", "country": "USD", "date": "2026-11-12T08:30:00-05:00", "impact": "High"}]
    calls = []

    class R:
        def json(self):
            return feed

    def fake_get(url, params=None, pause=1.0, timeout=30):
        calls.append(url)
        return R()

    monkeypatch.setattr(U, "get", fake_get)
    out = japan.update(log=None, src_dir=folder)
    assert out["jpy_events"] == 1 and out["interventions"] == len(japan.INTERVENTIONS)
    ev = japan.load_events(folder)
    assert ev["title"].tolist() == ["BOJ Policy Rate"] and ev["first_seen_ms"].notna().all()
    japan.update(log=None, src_dir=folder)                               # within 3 hours: not asked again
    assert len(calls) == 1

    def broken(*a, **k):
        raise RuntimeError("down")
    monkeypatch.setattr(U, "get", broken)
    st = U.load_state(japan.state_path(folder))
    st["last_feed_ms"] = 0
    U.save_state(japan.state_path(folder), st)
    out = japan.update(log=None, src_dir=folder)
    assert out["jpy_events"].startswith("failed") and len(japan.load_events(folder)) == 1


def test_describe_and_facts(tmp_path):
    bars = make_bars("2025-06-01", "2026-11-11")
    f = japan.features(bars.index, "USDJPY", bars=bars, src_dir=str(tmp_path))
    s = japan.describe(f.iloc[-1], "USDJPY")["Japan watch"]
    assert "BoJ" in s and "in a week" in s
    rows = dict(japan.facts(f.iloc[-1], "USDJPY")["Japan watch"])
    assert "Next BoJ decision" in rows and "Change over 1 month" in rows
