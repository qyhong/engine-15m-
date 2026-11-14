# -*- coding: utf-8 -*-
"""extdata: gold, silver, USDJPY and S&P 500 bars, checked on planted frames. No network, no real files.

    py -3 -m pytest tests/test_extdata.py -q        (from the project folder)
"""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import data  # noqa: E402
from engine15 import extdata as X  # noqa: E402

BAR = 900
ASSETS = ("XAUUSD", "XAGUSD", "USDJPY", "SPX")


def utc(text):
    return pd.Timestamp(text, tz="UTC")


def sec(text):
    return int(utc(text).timestamp())


def session_index(asset, start, end):
    """Every 15-minute slot of [start, end) in which the market trades."""
    idx = pd.date_range(utc(start), utc(end), freq="15min", inclusive="left")
    return idx[X.open_mask(asset, idx)]


def make_bars(idx, base=100.0, seed=1, vol=0.0005):
    rng = np.random.RandomState(seed)
    close = base * np.exp(np.cumsum(rng.normal(0, vol, len(idx))))
    opn = np.concatenate([[base], close[:-1]])
    wick = rng.uniform(0, vol, len(idx))
    df = pd.DataFrame({"open": opn, "high": np.maximum(opn, close) * (1 + wick), "low": np.minimum(opn, close) * (1 - wick),
                       "close": close, "volume": rng.uniform(50, 150, len(idx)), "taker_buy": np.nan}, index=idx)
    df.index.name = "open_time"
    return df[data.COLS]


def scaled(df, factor, volume=None):
    out = df.copy()
    factor = np.asarray(factor, dtype=float)
    for k in X.OHLC:
        out[k] = out[k].values * factor
    if volume is not None:
        out["volume"] = volume
    return out


def payload(df, rmt, live_ts=None, nulls=()):
    """Yahoo's chart JSON for these bars, with its always-live last element appended."""
    ts = [int(t) // 1000 for t in data.to_ms(df.index)]
    q = dict((k, [float(v) for v in df[k]]) for k in X.OHLC + ["volume"])
    for i in nulls:
        for k in q:
            q[k][i] = None
    last = float(df.close.iloc[-1])
    ts.append(int(rmt if live_ts is None else live_ts))
    for k in X.OHLC:
        q[k].append(last)
    q["volume"].append(0)
    return {"chart": {"result": [{"meta": {"regularMarketTime": int(rmt)}, "timestamp": ts,
                                  "indicators": {"quote": [q]}}], "error": None}}


def plant_dukascopy(root, asset, df):
    folder = os.path.join(root, asset)
    os.makedirs(folder, exist_ok=True)
    out = df[["open", "high", "low", "close", "volume"]].copy()
    out.insert(0, "ts_ms", data.to_ms(df.index))
    out.to_csv(os.path.join(folder, "15m.csv.gz"), index=False, compression="gzip")


@pytest.fixture
def box(tmp_path, monkeypatch):
    """A private data folder, a private Dukascopy store, a clock the test sets, and no way out to the network."""
    state = {"now": float(sec("2026-11-10 15:35")), "answer": None, "calls": []}

    def fake_fetch(symbol, rng):
        state["calls"].append((symbol, rng))
        if isinstance(state["answer"], Exception):
            raise state["answer"]
        return state["answer"]

    def no_network(*a, **k):
        raise AssertionError("a test reached for the network")

    import requests
    monkeypatch.setattr(requests, "get", no_network)
    monkeypatch.setattr(data, "DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(X, "DUKA_DIR", str(tmp_path / "duka"))
    monkeypatch.setattr(X, "fetch_chart", fake_fetch)
    monkeypatch.setattr(X, "_now", lambda: state["now"])
    state["duka"] = str(tmp_path / "duka")
    return state


# ------------------------------------------------------------------ the join
def test_splice_ratio_and_continuity_at_the_join():
    truth = make_bars(session_index("XAUUSD", "2026-08-03", "2026-09-19"), base=4000.0)
    duka = scaled(truth[truth.index < utc("2026-09-12")], 1.0, volume=7.0)
    yahoo = scaled(truth[truth.index >= utc("2026-09-01 04:00")], 1.01, volume=555.0)
    df, info = X.splice("XAUUSD", duka, yahoo)
    both = yahoo.index.intersection(duka.index)
    assert info["overlap_bars"] == len(both) > 500
    assert abs(info["splice_ratio"] - 1.01) < 1e-9 and abs(info["ratio_whole_overlap"] - 1.01) < 1e-9
    assert info["join"] == str(yahoo.index[0]) and info["mad_overlap_pct"] < 1e-6
    # one level throughout: the whole series is the true path times 1.01, on both sides of the join
    assert np.allclose(df.close.values, truth.close.values * 1.01, rtol=0, atol=6e-4)
    assert len(df) == len(truth) and df.index.equals(truth.index)
    j = df.index.get_loc(yahoo.index[0])
    true_move = truth.close.iloc[j] / truth.close.iloc[j - 1] - 1
    assert abs((df.close.iloc[j] / df.close.iloc[j - 1] - 1) - true_move) < 1e-6
    assert abs(info["join_step_pct"]) < 1e-9                    # Yahoo's first bar sits on the adjusted Dukascopy bar
    # each source keeps its own volume; nothing in taker_buy; no inverted bar
    assert (df.volume.iloc[:j] == 7.0).all() and (df.volume.iloc[j:] == 555.0).all()
    assert df.taker_buy.isna().all() and X.ohlc_violations(df) == 0
    assert list(df.columns) == data.COLS


def test_splice_uses_the_ratio_at_the_join_when_the_basis_drifts():
    """A futures price sinks toward spot as the contract ages: ratio 1.010 at the join, 1.002 two months on."""
    truth = make_bars(session_index("XAUUSD", "2026-08-03", "2026-11-06"), base=4000.0, seed=3)
    yahoo = truth[truth.index >= utc("2026-09-01 04:00")]
    yahoo = scaled(yahoo, np.linspace(1.010, 1.002, len(yahoo)))
    df, info = X.splice("XAUUSD", truth, yahoo)
    assert abs(info["splice_ratio"] / 1.010 - 1) < 2e-4         # taken where the sources meet
    assert abs(info["ratio_whole_overlap"] / 1.006 - 1) < 5e-4  # the whole-overlap median, reported next to it
    assert abs(info["join_step_pct"]) < 0.02                    # no step at the join
    assert info["mad_overlap_pct"] > 0.2 and info["drift_pct"] < -0.5      # ... and the drift is reported, not hidden
    _, literal = X.splice("XAUUSD", truth, yahoo, join_bars=None)
    assert literal["splice_ratio"] == literal["ratio_whole_overlap"]
    assert abs(literal["join_step_pct"]) > 0.3                  # what the whole-overlap median would have left


def test_splice_refuses_to_leave_a_hole():
    old = make_bars(session_index("USDJPY", "2026-06-01", "2026-07-01"), base=155.0)
    new = make_bars(session_index("USDJPY", "2026-09-01", "2026-09-10"), base=155.0)
    with pytest.raises(RuntimeError):
        X.splice("USDJPY", old, new)


# ------------------------------------------------------------------ sessions
@pytest.mark.parametrize("tz_ok", [True, False])
def test_spx_session_filter_across_daylight_saving(tz_ok, monkeypatch, box):
    if tz_ok and not X.TZ_OK:
        pytest.skip("no time-zone data on this machine: the fallback rule is the one in use")
    monkeypatch.setattr(X, "TZ_OK", tz_ok)                      # False: the hand-written US rule
    idx = pd.date_range(utc("2026-03-01"), utc("2026-03-15"), freq="15min", inclusive="left").append(
        pd.date_range(utc("2026-10-25"), utc("2026-11-08"), freq="15min", inclusive="left"))
    plant_dukascopy(box["duka"], "SPX", make_bars(idx, base=7000.0))        # a CFD that never sleeps
    kept = X._dukascopy_for("SPX")
    days = pd.Series(kept.index, index=kept.index.normalize())
    assert len(set(days.index)) == 20 and (days.groupby(level=0).count() == 26).all()
    first = days.groupby(level=0).min().dt.strftime("%H:%M")
    last = days.groupby(level=0).max().dt.strftime("%H:%M")
    for day in first.index:
        winter = day < utc("2026-03-08") or day >= utc("2026-11-01")       # US clocks: 8 March and 1 November 2026
        assert (first[day], last[day]) == (("14:30", "20:45") if winter else ("13:30", "19:45")), day
    assert set(kept.index.weekday) == {0, 1, 2, 3, 4}


def test_daylight_saving_fallback_matches_the_time_zone_database():
    if not X.TZ_OK:
        pytest.skip("no time-zone data on this machine")
    idx = pd.date_range(utc("2018-01-01"), utc("2030-01-01"), freq="15min")
    ms = data.to_ms(idx)
    for zone in (X.NY, X.LONDON):
        want = data.to_ms(idx.tz_convert(zone).tz_localize(None))
        assert (ms + X._manual_offset_ms(ms, zone) == want).all(), zone


def test_nyse_holidays_and_half_days():
    shut, early = X.nyse_days(2026)
    assert shut == {dt.date(2026, m, d) for m, d in ((1, 1), (1, 19), (2, 16), (4, 3), (5, 25), (6, 19), (7, 3),
                                                     (9, 7), (11, 26), (12, 25))}
    assert early == {dt.date(2026, 11, 27), dt.date(2026, 12, 24)}
    assert dt.date(2021, 12, 31) not in X.nyse_days(2021)[0]    # a Saturday New Year is not observed
    assert dt.date(2025, 1, 9) in X.nyse_days(2025)[0]          # day of mourning
    assert not X.is_open("SPX", "2026-11-26 15:00")             # Thanksgiving
    assert X.is_open("SPX", "2026-11-27 17:45") and not X.is_open("SPX", "2026-11-27 18:00")    # shuts 13:00 New York


def test_is_open_weekday_weekend_and_the_gold_break():
    for asset in ASSETS:
        assert X.is_open(asset, "2026-11-04 15:00"), asset      # a Wednesday, 10:00 in New York
        assert not X.is_open(asset, "2026-11-07 12:00"), asset  # a Saturday
        assert not X.is_open(asset, "2026-07-11 12:00"), asset
    for metal in ("XAUUSD", "XAGUSD"):
        assert X.is_open(metal, "2026-11-04 21:45")             # winter: the break is 22:00-23:00 UTC
        assert not X.is_open(metal, "2026-11-04 22:00") and not X.is_open(metal, "2026-11-04 22:45")
        assert X.is_open(metal, "2026-11-04 23:00")
        assert X.is_open(metal, "2026-07-08 20:45")             # summer: 21:00-22:00 UTC
        assert not X.is_open(metal, "2026-07-08 21:30") and X.is_open(metal, "2026-07-08 22:00")
        assert not X.is_open(metal, "2026-11-08 22:45") and X.is_open(metal, "2026-11-08 23:00")    # Sunday's open
        assert X.is_open(metal, "2026-11-06 21:45") and not X.is_open(metal, "2026-11-06 22:00")    # Friday's close
    assert X.is_open("USDJPY", "2026-11-04 22:30")              # no daily break in FX
    assert not X.is_open("USDJPY", "2026-11-08 21:45") and X.is_open("USDJPY", "2026-11-08 22:00")  # Sunday 22:00 UTC
    assert X.is_open("USDJPY", "2026-11-06 21:45") and not X.is_open("USDJPY", "2026-11-06 22:00")  # Friday 22:00 UTC
    assert not X.is_open("USDJPY", "2026-11-08 22:30", feed=True)           # Yahoo starts at London midnight
    assert X.is_open("USDJPY", "2026-11-09 00:00", feed=True)
    assert not X.is_open("SPX", "2026-11-04 14:15") and X.is_open("SPX", "2026-11-04 14:30")
    assert X.is_open("SPX", "2026-11-04 20:59") and not X.is_open("SPX", "2026-11-04 21:00")
    assert not X.is_open("SPX", "2026-11-04 03:00")
    # a naive datetime, an aware one and epoch milliseconds all mean the same moment
    assert X.is_open("SPX", dt.datetime(2026, 11, 4, 15, 0)) and X.is_open("SPX", sec("2026-11-04 15:00") * 1000)
    assert X.is_open("SPX", dt.datetime(2026, 11, 4, 10, 0, tzinfo=dt.timezone(dt.timedelta(hours=-5))))


# ------------------------------------------------------------------ closed bars
def test_closed_bar_rule():
    idx = pd.date_range(utc("2026-11-04 15:00"), periods=6, freq="15min")   # 15:00 ... 16:15
    bars = make_bars(idx, base=4000.0)
    t = [int(x) // 1000 for x in data.to_ms(idx)]
    # the feed runs 10 minutes late: at 16:25 on the clock it has traded up to 16:15 only
    df, info = X.parse_chart(payload(bars, rmt=t[5]), now=t[5] + 600)
    assert list(data.to_ms(df.index) // 1000) == t[:5]          # 16:15 is still trading in the feed; the live tick is gone
    assert info["forming"] == 1 and info["feed_delay_s"] == 600 and not info["quiet"]
    # the clock has passed 16:15's end by 20 seconds, the feed has not: not stored
    df, _ = X.parse_chart(payload(bars, rmt=t[5] + BAR - 580), now=t[5] + BAR + 20)
    assert list(data.to_ms(df.index) // 1000) == t[:5]
    # the feed has passed its end: stored
    df, _ = X.parse_chart(payload(bars, rmt=t[5] + BAR + 3), now=t[5] + BAR + 5)
    assert list(data.to_ms(df.index) // 1000) == t
    # a live last element that sits ON the grid (the bar still trading) is dropped like any other
    df, _ = X.parse_chart(payload(bars.iloc[:5], rmt=t[5] + 100, live_ts=t[5]), now=t[5] + 101)
    assert list(data.to_ms(df.index) // 1000) == t[:5]
    # a market quiet for 20 minutes: every bar whose end the clock has passed is final; null rows are dropped
    df, info = X.parse_chart(payload(bars, rmt=t[5] + 400, nulls=(2,)), now=t[5] + 400 + X.YF_QUIET)
    assert info["quiet"] and list(data.to_ms(df.index) // 1000) == t[:2] + t[3:]
    # ... but never a bar the clock itself has not finished
    df, _ = X.parse_chart(payload(bars, rmt=t[5] - 2000), now=t[5] + 300)
    assert list(data.to_ms(df.index) // 1000) == t[:5]
    assert X.ohlc_violations(df) == 0 and df.taker_buy.isna().all()


def test_yahoo_bars_drops_prints_outside_the_session(box):
    idx = pd.date_range(utc("2026-11-04 21:00"), periods=5, freq="15min")   # gold: 21:00 .. 21:45, then 22:00 in the break
    bars = make_bars(idx, base=4000.0)
    box["answer"] = payload(bars, rmt=sec("2026-11-04 23:20"))
    box["now"] = float(sec("2026-11-04 23:30"))
    df, info = X.yahoo_bars("XAUUSD", "5d")
    assert len(df) == 4 and info["stray"] == 1 and df.index[-1] == utc("2026-11-04 21:45")
    assert box["calls"] == [("GC=F", "5d")]


# ------------------------------------------------------------------ update
def test_update_appends_closed_bars_then_is_a_no_op(box):
    idx = session_index("USDJPY", "2026-11-09", "2026-11-10 15:30")         # ... 15:15 is the last one
    bars = X._tidy("USDJPY", make_bars(idx, base=158.0))
    data.save("USDJPY", bars.iloc[:-3])                                     # stored up to 14:15
    box["now"] = float(sec("2026-11-10 15:35"))
    feed = bars.iloc[-40:]                                                  # Yahoo: 14:30, 14:45, 15:00 closed; 15:15 trading
    box["answer"] = payload(feed, rmt=sec("2026-11-10 15:24"))
    df, n = X.update("USDJPY", log=lambda m: None)
    assert n == 2 and df.index[-1] == utc("2026-11-10 15:00")               # 15:15 ends at 15:30, the feed is at 15:24
    assert box["calls"] == [("JPY=X", "5d")]
    stored = data.load("USDJPY")
    assert stored.index.equals(df.index) and np.allclose(stored[X.OHLC].values, bars.iloc[:-1][X.OHLC].values)
    assert stored.taker_buy.isna().all()
    path = data.path_for("USDJPY")
    before = (os.stat(path).st_mtime_ns, open(path, "rb").read())
    df2, n2 = X.update("USDJPY", log=lambda m: None)                        # the same answer again: nothing new
    assert n2 == 0 and df2.index.equals(df.index)
    assert before == (os.stat(path).st_mtime_ns, open(path, "rb").read())
    assert not os.path.exists(path + ".tmp")
    box["answer"] = payload(feed, rmt=sec("2026-11-10 15:31"))              # the feed passes 15:30: one more bar
    box["now"] = float(sec("2026-11-10 15:32"))
    df3, n3 = X.update("USDJPY", log=lambda m: None)
    assert n3 == 1 and df3.index[-1] == utc("2026-11-10 15:15") and len(data.load("USDJPY")) == len(bars)


def test_update_survives_a_failed_request(box):
    import requests
    bars = X._tidy("XAUUSD", make_bars(session_index("XAUUSD", "2026-11-09", "2026-11-10 15:00"), base=4000.0))
    data.save("XAUUSD", bars)
    path = data.path_for("XAUUSD")
    before = open(path, "rb").read()
    said = []
    for answer in (requests.ConnectionError("no route"), requests.HTTPError("429"), TimeoutError("slow"),
                   {"chart": {"result": None, "error": {"code": "Not Found"}}}, {"nonsense": 1}, None):
        box["answer"] = answer
        df, n = X.update("XAUUSD", log=said.append)
        assert n == 0 and df.index.equals(bars.index) and open(path, "rb").read() == before
    assert len(said) == 6 and all("keeping" in line for line in said)


def test_update_without_history_and_with_a_stale_store(box):
    df, n = X.update("SPX", log=lambda m: None)                             # nothing stored: nothing asked, nothing made
    assert n == 0 and len(df) == 0 and box["calls"] == [] and not os.path.exists(data.path_for("SPX"))
    bars = X._tidy("SPX", make_bars(session_index("SPX", "2026-10-26", "2026-10-31"), base=7000.0))
    data.save("SPX", bars)
    box["answer"] = payload(bars, rmt=sec("2026-10-30 20:00"))
    X.update("SPX", log=lambda m: None)                                     # 11 days old: one request, the long range
    assert box["calls"] == [("^GSPC", "60d")]


# ------------------------------------------------------------------ the whole build, and the report
def test_build_history_end_to_end_on_planted_sources(box):
    truth = make_bars(session_index("XAGUSD", "2019-01-01", "2019-01-20").append(
        session_index("XAGUSD", "2026-08-01", "2026-11-10 15:30")), base=50.0, seed=5)
    plant_dukascopy(box["duka"], "XAGUSD", truth[truth.index < utc("2026-11-06")])
    yahoo = truth[truth.index >= utc("2026-09-01 04:00")]                   # another feed: same market, its own prints
    yahoo = scaled(yahoo, 1.005 * (1 + np.random.RandomState(9).normal(0, 1e-4, len(yahoo))), volume=900.0)
    box["answer"] = payload(yahoo, rmt=sec("2026-11-10 15:25"))             # futures: 10 minutes behind the clock
    rep = X.build_history("XAGUSD", log=lambda m: None)
    assert box["calls"] == [("SI=F", "60d")]
    df = data.load("XAGUSD")                                                # the project's own loader reads it
    assert list(df.columns) == data.COLS and df.taker_buy.isna().all() and X.ohlc_violations(df) == 0
    assert df.index[0] == truth.index[0] and df.index[-1] == utc("2026-11-10 15:00")    # 15:15 was still trading
    assert rep["rows"] == len(df) and rep["join"] == "2026-09-01 04:00:00+00:00"
    assert abs(rep["splice_ratio"] / 1.005 - 1) < 5e-5 and rep["overlap_bars"] > 4000
    assert 0.002 < rep["mad_join_pct"] < 0.02 and abs(rep["join_step_pct"]) < 0.05
    assert rep["yahoo_feed_delay_s"] == 600 and rep["newest_closed_age_s"] == 1200      # closed 15:15, fetched 15:35
    assert rep["monotone"] and rep["duplicates"] == 0 and rep["off_grid"] == 0 and rep["ohlc_violations"] == 0
    old = df.index < utc(rep["join"])                                       # below the join: Dukascopy times the ratio
    assert np.allclose(df.close[old].values, truth.close[:old.sum()].values * rep["splice_ratio"], rtol=0, atol=6e-6)
    assert np.allclose(df.close[~old].values, yahoo.close[:(~old).sum()].values, rtol=0, atol=6e-6)
    again = X.report("XAGUSD")                                              # the join, read back out of the file
    assert again["join"] == rep["join"] and abs(again["splice_ratio"] - rep["splice_ratio"]) < 1e-6
    assert again["typical_bars_per_day"] == 92 and set(again["bars_per_weekday"]) == {"Mon", "Tue", "Wed", "Thu", "Fri", "Sun"}
    gate = data.gates(df)
    assert gate["monotone"] and gate["duplicates"] == 0 and gate["ohlc_violations"] == 0


def test_report_measures_gaps_inside_trading_hours_only(box):
    idx = session_index("SPX", "2026-10-26", "2026-11-07")
    hole = (idx >= utc("2026-11-03 15:00")) & (idx < utc("2026-11-03 15:45"))
    data.save("SPX", X._tidy("SPX", make_bars(idx[~hole], base=7000.0)))
    rep = X.report("SPX")                                                   # no Dukascopy store here: still answers
    assert rep["largest_gap_hours"] == 0.75 and rep["largest_gap_after"] == "2026-11-03 14:45:00+00:00"
    assert rep["missing_in_session"] == 3 and rep["bars_outside_session"] == 0   # nights and the weekend are not gaps
    assert rep["typical_bars_per_day"] == 26 and rep["splice_ratio"] is None


def test_roll_adjust_scales_new_contract_to_stored_level(tmp_path, monkeypatch):
    import numpy as np, pandas as pd
    from engine15 import extdata, data
    monkeypatch.setattr(data, "path_for", lambda a: str(tmp_path / ("%s_15m.csv" % a.lower())))
    idx = pd.date_range("2026-11-02 14:00", periods=20, freq="15min", tz="UTC")
    old = pd.DataFrame({"open": 90.0, "high": 90.2, "low": 89.8, "close": 90.0, "volume": 1.0, "taker_buy": np.nan}, index=idx[:16])
    new = pd.DataFrame({"open": 91.0, "high": 91.2, "low": 90.8, "close": 91.0, "volume": 1.0, "taker_buy": np.nan}, index=idx[4:])
    out = extdata.roll_adjust("WTI", old, new, log=lambda *_: None)
    assert abs(out["close"].iloc[-1] - 90.0) < 1e-9                       # continuous with the stored bars
    same = extdata.roll_adjust("WTI", old, old.iloc[4:], log=lambda *_: None)
    assert (same["close"] == old["close"].iloc[4:]).all()                 # no roll: unchanged
    assert extdata.roll_adjust("SPX", old, new, log=lambda *_: None) is new
