# -*- coding: utf-8 -*-
"""engine15/sources/options_hist.py checked on planted data with a fake network. No real network, no real files.

    py -3 -m pytest tests/test_sources_options_hist.py -q        (from the project folder)
"""
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import data  # noqa: E402
from engine15.sources import options_hist as oh  # noqa: E402

A, E = "BTCUSDT", "ETHUSDT"
BAR, HOUR, DAY = oh.BAR_MS, oh.HOUR_MS, oh.DAY_MS
START = "2023-01-01"
N_DAYS = 140
T0 = int(pd.Timestamp(START, tz="UTC").value // 10 ** 6)


def _expiry_name(coin, ts, days, strike, kind):
    e = pd.Timestamp(ts + days * DAY, unit="ms", tz="UTC")
    return "%s-%d%s%s-%s-%s" % (coin, e.day, e.strftime("%b").upper(), e.strftime("%y"), strike, kind)


def fake_trades(asset, start_ms, end_ms, seed=0, per_hour=6):
    """Deterministic synthetic trades in [start_ms, end_ms): several per hour, some sharing a millisecond, some blocks."""
    coin = oh.COIN[asset]
    out = []
    for h0 in range(start_ms // HOUR * HOUR, end_ms, HOUR):
        rng = np.random.RandomState((h0 // HOUR + seed) % (2 ** 31))
        spot = 20000.0 * (1 + 0.1 * np.sin(h0 / (30.0 * DAY)))
        for i in range(per_hour):
            ts = h0 + int(rng.randint(0, HOUR)) if i % 3 else h0 + 1234            # several trades on one ms
            kind = "P" if rng.rand() < 0.45 else "C"
            days = int(rng.choice([3, 10, 30, 45, 90]))
            k = int(round(spot * (0.85 if kind == "P" else 1.15) / 500.0) * 500)
            t = {"trade_id": "%s-%d-%d" % (coin, h0, i), "timestamp": ts, "instrument_name": _expiry_name(coin, ts, days, k, kind),
                 "amount": float(rng.choice([0.1, 1.0, 5.0])), "index_price": spot, "price": 0.01,
                 "iv": float(50 + 10 * rng.rand() + (5 if kind == "P" else 0)), "direction": "buy" if rng.rand() < 0.5 else "sell"}
            if rng.rand() < 0.2:
                t["block_trade_id"] = "B%d" % (h0 // HOUR)
            if start_ms <= ts < end_ms:
                out.append(t)
    return sorted(out, key=lambda t: (t["timestamp"], t["trade_id"]))


class FakeNet(object):
    """Serves fake_trades like the history endpoint: asc order, `count` per page, has_more."""

    def __init__(self, page=7, fail_after=None):
        self.page, self.calls, self.fail_after = page, [], fail_after

    def __call__(self, url, params=None):
        assert url == oh.HIST and params["kind"] == "option" and params["sorting"] == "asc"
        assert "key" not in str(params).lower()
        self.calls.append(dict(params))
        if self.fail_after is not None and len(self.calls) > self.fail_after:
            raise RuntimeError("network down")
        asset = "BTCUSDT" if params["currency"] == "BTC" else "ETHUSDT"
        s, e = int(params["start_timestamp"]), int(params["end_timestamp"])
        tr = fake_trades(asset, s, e + 1)
        page = tr[:self.page]
        return {"trades": page, "has_more": len(tr) > self.page}


def backfill(tmp, monkeypatch, n_days=N_DAYS, assets=(A, E), **kw):
    monkeypatch.setattr(oh, "_get", FakeNet(**kw))
    end = T0 + n_days * DAY
    return oh.update(log=lambda *_: None, src_dir=str(tmp), assets=assets, end_ms=end, start=START)


def same(a, b):
    return np.array_equal(a.values.astype(float), b.values.astype(float), equal_nan=True)


def test_parse_instrument_and_delta():
    exp, k, kind = oh.parse_instrument("BTC-25MAR22-50000-P")
    assert kind == "P" and k == 50000 and exp == int(pd.Timestamp("2022-03-25 08:00", tz="UTC").value // 10 ** 6)
    assert oh.parse_instrument("ETH-1JAN25-3500-C")[1] == 3500
    assert oh.parse_instrument("XRP_USDC-1JAN25-0d5-C") is None                # not an inverse option of a coin we read
    assert oh.parse_instrument("BTC-PERPETUAL") is None
    c = oh.bs_delta(100.0, 100.0, 30 / 365.0, 0.6, "C")
    p = oh.bs_delta(100.0, 100.0, 30 / 365.0, 0.6, "P")
    assert 0.5 < c < 0.56 and abs(c - p - 1.0) < 1e-12
    assert 0.15 < oh.bs_delta(100.0, 115.0, 30 / 365.0, 0.6, "C") < 0.35


def test_paging_gets_every_trade_once_including_shared_milliseconds(monkeypatch):
    net = FakeNet(page=4)
    monkeypatch.setattr(oh, "_get", net)
    got = oh.fetch_day(A, T0)
    want = fake_trades(A, T0, T0 + DAY)
    assert sorted(t["trade_id"] for t in got) == sorted(t["trade_id"] for t in want)
    assert len(net.calls) > 24


def test_aggregate_day_sums():
    tr = fake_trades(A, T0, T0 + DAY)
    f = oh.aggregate_day(tr, T0)
    assert len(f) == 24 and (np.diff(f.ts_ms.values) == HOUR).all() and (f.known_ms == f.ts_ms + HOUR).all()
    assert f["n"].sum() == len(tr) and f["skipped"].sum() == 0
    puts = [t for t in tr if t["instrument_name"].endswith("-P")]
    assert abs(f["put_usd"].sum() - sum(t["amount"] * t["index_price"] for t in puts)) < 1e-6
    assert (f["put_buy_usd"] <= f["put_usd"] + 1e-9).all() and (f["rr_put_n"] + f["rr_call_n"]).sum() > 0
    blk = f[["blk_put_buy_usd", "blk_put_sell_usd", "blk_call_buy_usd", "blk_call_sell_usd"]].sum().sum()
    assert abs(blk - sum(t["amount"] * t["index_price"] for t in tr if "block_trade_id" in t)) < 1e-6
    empty = oh.aggregate_day([], T0)
    assert len(empty) == 24 and empty[oh.SUM_COLS].sum().sum() == 0


def test_update_is_resumable_and_never_changes_stored_rows(tmp_path, monkeypatch):
    out = backfill(tmp_path, monkeypatch, n_days=10, assets=(A,))
    assert out["hourly_BTCUSDT"] == 240
    f = oh.load_source("hourly", A, str(tmp_path))
    assert (np.diff(f.ts_ms.values) == HOUR).all() and f.ts_ms.iloc[-1] == T0 + 10 * DAY - HOUR
    f[oh.SUM_COLS] = 7.0                                                         # plant: a later run must not touch these
    oh._write(oh.path_for("hourly", A, str(tmp_path)), f)
    net = FakeNet()
    monkeypatch.setattr(oh, "_get", net)
    out = oh.update(log=lambda *_: None, src_dir=str(tmp_path), assets=(A,), end_ms=T0 + 10 * DAY)
    assert out["hourly_BTCUSDT"] == 240 and net.calls == []                    # nothing to do: no request
    oh.update(log=lambda *_: None, src_dir=str(tmp_path), assets=(A,), end_ms=T0 + 12 * DAY + 5 * HOUR)
    g = oh.load_source("hourly", A, str(tmp_path))
    assert len(g) == 12 * 24                                                     # whole days only, nothing of the partial day
    assert g.iloc[:240].equals(f) and all(c["start_timestamp"] >= T0 + 10 * DAY for c in net.calls)


def test_a_failure_keeps_what_was_flushed_and_never_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(oh, "FLUSH_DAYS", 2)
    monkeypatch.setattr(oh, "_get", FakeNet(page=50, fail_after=12))
    out = oh.update(log=lambda *_: (_ for _ in ()).throw(ValueError("bad logger")), src_dir=str(tmp_path), assets=(A,),
                    end_ms=T0 + 30 * DAY, start=START)
    assert str(out["hourly_BTCUSDT"]).startswith("failed: ")
    f = oh.load_source("hourly", A, str(tmp_path))
    assert len(f) % 48 == 0 and len(f) > 0                                       # whole flushed pairs of days only
    monkeypatch.setattr(oh, "_get", FakeNet(page=50))
    oh.update(log=lambda *_: None, src_dir=str(tmp_path), assets=(A,), end_ms=T0 + 30 * DAY)
    g = oh.load_source("hourly", A, str(tmp_path))
    assert len(g) == 30 * 24 and g.iloc[:len(f)].equals(f)
    whole = oh.aggregate_day(fake_trades(A, T0 + 29 * DAY, T0 + 30 * DAY), T0 + 29 * DAY)
    assert np.allclose(g.iloc[-24:][oh.SUM_COLS].values, whole[oh.SUM_COLS].values)


CUTS = (96 * 40 + 47, 96 * 95, 96 * 120 + 3, 96 * N_DAYS - 1)


def test_no_lookahead_cutting_the_index(tmp_path, monkeypatch):
    backfill(tmp_path, monkeypatch)
    idx = pd.date_range(START, periods=N_DAYS * 96, freq="15min", tz="UTC")
    full = oh.features(idx, A, src_dir=str(tmp_path))
    assert full.attrs["errors"] == {}
    for col in oh.FEATURES:
        assert (full[col] != 0).mean() > 0.3, "%s never speaks on the planted data" % col
    for cut in CUTS:
        part = oh.features(idx[:cut], A, src_dir=str(tmp_path))
        assert same(full.iloc[:cut], part), "a reading changed when the index was cut at %d" % cut


def test_rows_added_later_or_not_yet_known_never_change_earlier_values(tmp_path, monkeypatch):
    """A row's value never changes when later data is added, and data not yet known cannot reach it."""
    backfill(tmp_path, monkeypatch)
    close = np.arange(T0 + DAY, T0 + N_DAYS * DAY + 1, DAY // 4, dtype="int64")
    full = oh.inputs(close, A, src_dir=str(tmp_path))
    h = oh.load_source("hourly", A, str(tmp_path))
    for t in (T0 + 50 * DAY + 3 * HOUR, T0 + 100 * DAY, T0 + 131 * DAY + 7 * HOUR):
        short = tmp_path / ("short%d" % t)
        oh._write(oh.path_for("hourly", A, str(short)), h[h.known_ms <= t])
        part = oh.inputs(close, A, src_dir=str(short))
        before = close <= t
        assert same(full[before], part[before]), "a value known by %d changed when later rows were added" % t
        rw = h.copy()
        late = rw.known_ms > t
        rw.loc[late, oh.SUM_COLS] = rw.loc[late, oh.SUM_COLS].values * 3.0 + 1.0
        oh._write(oh.path_for("hourly", A, str(short)), rw)
        got = oh.inputs(close, A, src_dir=str(short))
        assert same(full[before], got[before]), "data not yet known at %d reached an earlier row" % t
        assert not same(full[~before], got[~before])
    cut = oh.inputs(close, A, src_dir=str(tmp_path), cutoff_ms=T0 + 80 * DAY)
    assert same(full[close < T0 + 80 * DAY], cut[close < T0 + 80 * DAY])
    assert cut[close > T0 + 80 * DAY + oh.MAX_AGE].isna().all().all()


def test_known_at_is_the_hour_end_exactly(tmp_path, monkeypatch):
    backfill(tmp_path, monkeypatch, n_days=20, assets=(A,))
    h = oh.load_source("hourly", A, str(tmp_path))
    j = 14 * 24 + 5
    h.loc[j, "put_usd"] = 1e12
    oh._write(oh.path_for("hourly", A, str(tmp_path)), h)
    end = int(h.ts_ms[j]) + HOUR
    x = oh.inputs(np.array([end - 1, end], dtype="int64"), A, src_dir=str(tmp_path))
    assert x["op_put_usd_24h"].iloc[1] > 100 * x["op_put_usd_24h"].iloc[0]


def test_readings_have_the_registered_meaning():
    idx = np.arange(T0, T0 + 200 * DAY, HOUR, dtype="int64")
    g = pd.DataFrame(0.0, index=idx, columns=oh.HOURLY_COLS[1:])
    g["put_usd"], g["call_usd"] = 2.0, 1.0
    g["put_buy_usd"], g["call_buy_usd"] = 2.0, 0.0                               # takers buy every put, sell every call
    g["rr_put_ivw"], g["rr_put_w"], g["rr_put_n"] = 60.0, 1.0, 1.0
    g["rr_call_ivw"], g["rr_call_w"], g["rr_call_n"] = 50.0, 1.0, 1.0
    g["blk_n"], g["blk_put_buy_usd"], g["blk_call_sell_usd"] = 1.0, 3.0, 1.0
    g["known_ms"] = idx + HOUR
    r = oh.readings(g).iloc[-1]
    assert abs(r["op_pcr_7d"] - np.log(2.0)) < 1e-12
    assert abs(r["op_taker_bear_7d"] - 1.0) < 1e-12 and abs(r["op_block_bear_7d"] - 1.0) < 1e-12
    assert abs(r["op_rr25"] - 10.0) < 1e-9 and abs(r["op_rr25_chg7"]) < 1e-9
    assert not np.isfinite(r["op_pcr_1d_z90"])                                   # a constant ratio has no z
    first = oh.readings(g.iloc[:W7_minus_one()])
    assert first["op_pcr_7d"].isna().all()                                       # a 7-day window needs 7 days


def W7_minus_one():
    return oh.W7 - 1


def test_features_bounded_never_nan_and_no_file_is_no_read(tmp_path, monkeypatch):
    idx = pd.date_range(START, periods=30 * 96, freq="15min", tz="UTC")
    f = oh.features(idx, E, src_dir=str(tmp_path / "none"))
    assert f[oh.FEATURES].eq(0.0).all().all() and f[oh.RAW].isna().all().all()
    backfill(tmp_path, monkeypatch, n_days=30, assets=(E,))
    f = oh.features(idx, E, src_dir=str(tmp_path))
    assert f[oh.FEATURES].notna().all().all() and (f[oh.FEATURES].abs() <= 3.0).all().all()


def test_describe(tmp_path, monkeypatch):
    backfill(tmp_path, monkeypatch, n_days=20, assets=(A,))
    idx = pd.date_range(START, periods=20 * 96, freq="15min", tz="UTC")
    f = oh.features(idx, A, src_dir=str(tmp_path))
    for i in (0, len(idx) - 1):
        said = oh.describe(f.iloc[i], A)
        assert list(said) == [oh.GROUPS["options_hist"][0]]
        assert all(isinstance(s, str) and len(s) > 20 and not re.search(r"\bnan\b", s) for s in said.values())


def test_not_wired_into_the_live_engine():
    """H40 is research only: wiring is a separate, versioned, owner-approved step."""
    from engine15 import sources
    assert "options_hist" not in sources.MODULES
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for dirpath, _dirs, files in os.walk(os.path.join(root, "engine15")):
        for name in files:
            if name.endswith(".py") and name != "options_hist.py":
                with open(os.path.join(dirpath, name), encoding="utf-8") as fh:
                    assert "options_hist" not in fh.read(), "%s mentions options_hist" % name
    from engine15 import evidence
    assert oh not in getattr(evidence, "SOURCES", [])
