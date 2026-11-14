# -*- coding: utf-8 -*-
"""Storage round trip, cleaning, gap reports and the never-raise network rule."""
import numpy as np
import pandas as pd

from conftest import make_bars
from engine15.rl import data, store


def test_csv_gz_round_trip_is_bit_exact(tmp_path):
    b = make_bars(n=500, seed=2)
    b.iloc[3, 0] = 0.1 + 0.2                                    # an awkward float
    p = store.path(str(tmp_path), "bars")
    assert p.endswith(".csv.gz")
    store.write_frame(b, p)
    back = store.read_frame(p)
    assert back.index.equals(b.index) and str(back.index.tz) == "UTC"
    assert np.array_equal(back.values, b.values)


def test_read_missing_file_is_empty(tmp_path):
    assert len(store.read_frame(str(tmp_path / "nope.csv.gz"))) == 0


def test_clean_drops_duplicates_head_and_bad_bars_and_reports_gaps():
    b = make_bars(n=300, seed=3)
    b.iloc[:5, b.columns.get_loc("volume")] = 0.0               # pre-listing placeholder bars
    b.iloc[100, b.columns.get_loc("high")] = b["low"].iloc[100] - 1.0   # high below low
    dup = b.iloc[[50]].copy()
    dup["close"] = dup["close"] * 1.0001
    b = pd.concat([b, dup])
    b = b.drop(b.index[200:204])                                # a 4-bar gap
    out, rep = data.clean(b, 900000)
    assert rep["duplicates_dropped"] == 1 and rep["pre_listing_bars_dropped"] == 5
    assert rep["ohlc_invalid_dropped"] == 1
    assert out.index.is_monotonic_increasing and not out.index.duplicated().any()
    assert rep["missing_bars"] == 4 + 1                          # the gap, plus the dropped bad bar
    assert rep["gap_events"] == 2
    assert out.loc[dup.index[0], "close"] == dup["close"].iloc[0]    # the later copy wins


def test_get_never_raises(monkeypatch):
    import requests

    def boom(*a, **k):
        raise requests.ConnectionError("network blip")
    monkeypatch.setattr(requests, "get", boom)
    monkeypatch.setattr(data.time, "sleep", lambda s: None)
    assert data._get("https://example.invalid", {}, retries=3) is None


def test_fetch_returns_partial_and_flags_incomplete(monkeypatch):
    calls = {"n": 0}
    t0 = 1600000000000 - 1600000000000 % 900000

    def fake_get(url, params, **k):
        calls["n"] += 1
        if calls["n"] > 1:
            return None                                          # the network goes away on page 2
        return [[t0 + i * 900000, "1", "2", "0.5", "1.5", "10", t0 + i * 900000 + 899999, "15", 3, "5", "7", "0"]
                for i in range(1500)]
    monkeypatch.setattr(data, "_get", fake_get)
    monkeypatch.setattr(data.time, "sleep", lambda s: None)
    d = {"base_url": "x", "symbol": "BTCUSDT", "interval_ms": 900000, "page_limit": 1500, "pause_s": 0,
         "timeout_s": 1, "retries": 1, "save_every_pages": 100}
    df, complete = data.fetch_klines(d, t0)
    assert len(df) == 1500 and not complete
    assert list(df.columns) == data.BAR_COLS
