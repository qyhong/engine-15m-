# -*- coding: utf-8 -*-
"""engine15/sources/cot.py on planted files. No network.

    py -3 -m pytest tests/test_cot.py -q        (from the project folder)
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15.sources import _util as U  # noqa: E402
from engine15.sources import cot  # noqa: E402

CUTS = ("2021-03-05 20:15", "2021-03-05 20:30", "2023-02-20 12:00", "2025-11-21 21:00", "2026-06-22 20:45")


def plant(folder, asset="XAUUSD", start="2018-01-02", end="2026-11-03", seed=3):
    rng = np.random.RandomState(seed)
    days = pd.date_range(start, end, freq="7D")
    n = len(days)
    oi = 400000 + rng.normal(0, 20000, n)
    net = 80000 * np.sin(np.arange(n) / 20.0) + rng.normal(0, 8000, n)
    d = pd.DataFrame({"date": days.strftime("%Y-%m-%d"), "oi": oi, "long": 150000 + net / 2, "short": 150000 - net / 2,
                      "am_long": 90000.0, "am_short": 60000.0, "first_seen_ms": np.nan, "known_ms": np.nan})
    U.write_csv(d, cot.path_for(asset, folder))
    return d


def index15(start="2018-01-01", end="2026-11-10"):
    return pd.date_range(start, end, freq="15min", tz="UTC")


def same(a, b):
    return list(a.columns) == list(b.columns) and np.array_equal(a.values, b.values, equal_nan=True)


def test_release_rule_matches_the_cftc_2026_schedule():
    rel = {1: [5, 9, 16, 23, 30], 2: [6, 13, 20, 27], 3: [6, 13, 20, 27], 4: [3, 10, 17, 24], 5: [1, 8, 15, 22, 29],
           6: [5, 12, 22, 26], 7: [6, 10, 17, 24, 31], 8: [7, 14, 21, 28], 9: [4, 11, 18, 25], 10: [2, 9, 16, 23, 30],
           11: [6, 16, 20, 30], 12: [4, 11, 18, 28]}
    want = sorted("2026-%02d-%02d" % (m, d) for m, ds in rel.items() for d in ds)
    got = []
    for t in pd.date_range("2025-12-30", "2026-12-22", freq="7D"):
        d = t.date()
        if d in cot.federal_holidays(d.year):                # a Tuesday holiday: positions as of the Monday
            d = d - pd.Timedelta(days=1)
        ms = cot.release_ms(str(d))
        local = pd.Timestamp(ms, unit="ms", tz="UTC").tz_convert(U.NY)
        assert (local.hour, local.minute) == (15, 30)
        got.append(local.strftime("%Y-%m-%d"))
    assert got == want


def test_release_overrides_for_shutdowns():
    assert pd.Timestamp(cot.release_ms("2025-09-30"), unit="ms", tz="UTC").tz_convert(U.NY).strftime("%Y-%m-%d") == "2025-11-19"
    assert pd.Timestamp(cot.release_ms("2018-12-24"), unit="ms", tz="UTC").tz_convert(U.NY).strftime("%Y-%m-%d") == "2019-02-01"
    assert pd.Timestamp(cot.release_ms("2023-01-31"), unit="ms", tz="UTC").tz_convert(U.NY).strftime("%Y-%m-%d") == "2023-02-24"


def test_no_lookahead_truncation(tmp_path):
    """Cut the index at T and keep only reports released by T: every row up to T is unchanged."""
    full_dir = str(tmp_path / "full")
    d = plant(full_dir)
    idx = index15()
    full = cot.features(idx, "XAUUSD", src_dir=full_dir)
    assert full["cot_net"].notna().sum() > 1000
    for cut in CUTS:
        t_ms = int(pd.Timestamp(cut, tz="UTC").value // 1000000)
        part_dir = str(tmp_path / ("cut%d" % t_ms))
        known = cot.table("XAUUSD", full_dir)["known_at"].values              # published in order, as the CFTC does
        U.write_csv(d[known <= t_ms], cot.path_for("XAUUSD", part_dir))
        sub = idx[idx + pd.Timedelta(minutes=15) <= pd.Timestamp(cut, tz="UTC")]
        part = cot.features(sub, "XAUUSD", src_dir=part_dir)
        assert same(part, full.loc[sub]), cut


def test_a_report_reaches_rows_only_from_its_release(tmp_path):
    d = plant(str(tmp_path))
    idx = index15("2024-03-01", "2024-03-20")
    f = cot.features(idx, "XAUUSD", src_dir=str(tmp_path))
    rel = pd.Timestamp(cot.release_ms("2024-03-05"), unit="ms", tz="UTC")       # Fri 8 Mar 15:30 ET = 20:30 UTC
    assert rel == pd.Timestamp("2024-03-08 20:30", tz="UTC")
    before = f.loc[rel - pd.Timedelta(minutes=30)]                            # closes 20:15
    at = f.loc[rel - pd.Timedelta(minutes=15)]                                # closes 20:30
    net = d.set_index("date").loc["2024-03-05"]
    assert at["cot_net"] == pytest.approx(net["long"] - net["short"])
    assert before["cot_net"] != pytest.approx(net["long"] - net["short"])


def test_late_report_counts_from_when_it_was_seen(tmp_path):
    d = plant(str(tmp_path))
    seen = cot.release_ms("2024-03-05") + 3 * U.D_MS
    d.loc[d["date"] == "2024-03-05", "known_ms"] = float(seen)
    U.write_csv(d, cot.path_for("XAUUSD", str(tmp_path)))
    idx = index15("2024-03-08", "2024-03-14")
    f = cot.features(idx, "XAUUSD", src_dir=str(tmp_path))
    t_seen = pd.Timestamp(seen, unit="ms", tz="UTC")
    row_before = f.loc[t_seen - pd.Timedelta(minutes=30)]
    row_after = f.loc[t_seen - pd.Timedelta(minutes=15)]
    assert row_before["cot_report_age_d"] > 9                                  # still the previous week's report
    assert row_after["cot_report_age_d"] < 7


def test_yen_sign_is_flipped(tmp_path):
    plant(str(tmp_path), "USDJPY")
    plant(str(tmp_path), "SPX")
    idx = index15("2024-01-01", "2024-06-01")
    jpy = cot.features(idx, "USDJPY", src_dir=str(tmp_path))
    spx = cot.features(idx, "SPX", src_dir=str(tmp_path))
    assert np.allclose(jpy["cot_net"], spx["cot_net"], equal_nan=True)         # readable: the CFTC's own sign
    for f in cot.FEATURES:
        assert np.allclose(jpy[f], -spx[f])
    assert "USDJPY to" in cot.describe(jpy.iloc[-1], "USDJPY")["Futures positioning (CFTC)"]


def test_bounded_never_nan_and_no_file_is_no_read(tmp_path):
    plant(str(tmp_path))
    idx = index15()
    f = cot.features(idx, "XAUUSD", src_dir=str(tmp_path))
    assert not f[cot.FEATURES].isna().any().any()
    assert (f[cot.FEATURES].abs() <= 1.0).all().all()
    empty = cot.features(idx[:500], "XAGUSD", src_dir=str(tmp_path / "none"))
    assert (empty[cot.FEATURES] == 0).all().all() and empty[cot.RAW].isna().all().all()
    other = cot.features(idx[:500], "BTCUSDT", src_dir=str(tmp_path))
    assert (other[cot.FEATURES] == 0).all().all()


def test_stale_report_goes_quiet(tmp_path):
    d = plant(str(tmp_path), end="2024-01-02")
    idx = index15("2024-01-01", "2024-02-15")
    f = cot.features(idx, "XAUUSD", src_dir=str(tmp_path))
    assert f["cot_net"].iloc[-1] != f["cot_net"].iloc[-1]                     # NaN: over 15 days since the release
    assert (f[cot.FEATURES].iloc[-1] == 0).all()
    assert len(d)


def test_update_is_incremental_polite_and_never_raises(tmp_path, monkeypatch):
    folder = str(tmp_path)
    calls = []
    hist = [{"date": x, "oi": 1e5, "long": 6e4, "short": 4e4, "am_long": np.nan, "am_short": np.nan}
            for x in pd.date_range("2025-01-07", "2026-10-27", freq="7D").strftime("%Y-%m-%d")]

    def fake_fetch(asset, since=None):
        calls.append(since)
        return [dict(r) for r in hist if since is None or r["date"] > since]

    now = [cot.release_ms("2026-11-03") + 3600000]                             # an hour after the 3 Nov report's release
    monkeypatch.setattr(cot, "fetch", fake_fetch)
    monkeypatch.setattr(U, "now_ms", lambda: now[0])
    out = cot.update(log=None, src_dir=folder, assets=["XAUUSD"])
    assert out["XAUUSD"] == len(hist) and calls == [None]
    out = cot.update(log=None, src_dir=folder, assets=["XAUUSD"])              # due (3 Nov) but asked a moment ago
    assert calls == [None]
    now[0] += 31 * 60000                                                       # 31 minutes later: asks, finds nothing
    cot.update(log=None, src_dir=folder, assets=["XAUUSD"])
    assert calls[-1] == "2026-10-27"
    assert "missing_since_ms" in U.load_state(cot.state_path(folder))["XAUUSD"]
    hist.append({"date": "2026-11-03", "oi": 1e5, "long": 7e4, "short": 3e4, "am_long": np.nan, "am_short": np.nan})
    now[0] += 31 * 60000
    cot.update(log=None, src_dir=folder, assets=["XAUUSD"])
    d = cot.load("XAUUSD", folder)
    assert d["date"].iloc[-1] == "2026-11-03" and d["known_ms"].iloc[-1] == now[0]   # late: counts from when seen
    n_calls = len(calls)
    cot.update(log=None, src_dir=folder, assets=["XAUUSD"])                    # next report not due: no request
    assert len(calls) == n_calls

    def broken(asset, since=None):
        raise RuntimeError("network down")
    monkeypatch.setattr(cot, "fetch", broken)
    now[0] = cot.release_ms("2026-11-10") + 3600000
    out = cot.update(log=None, src_dir=folder, assets=["XAUUSD"])
    assert out["XAUUSD"].startswith("failed") and len(cot.load("XAUUSD", folder)) == len(hist)


def test_describe_and_facts(tmp_path):
    plant(str(tmp_path))
    f = cot.features(index15("2026-10-01", "2026-11-10"), "XAUUSD", src_dir=str(tmp_path))
    s = cot.describe(f.iloc[-1], "XAUUSD")["Futures positioning (CFTC)"]
    assert "managed-money" in s and "percentile" in s
    rows = dict(cot.facts(f.iloc[-1], "XAUUSD")["Futures positioning (CFTC)"])
    assert "Net position" in rows and "3-year percentile" in rows
