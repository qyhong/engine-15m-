# -*- coding: utf-8 -*-
"""bridge: bars from a second source when the usual feed serves none for an open market. No network.

    py -3 -m pytest tests/test_bridge.py -q
"""
import calendar
import os
import sys
import time

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import bridge, data, extdata  # noqa: E402

BAR = 900
T0 = calendar.timegm(time.strptime("2026-11-26 04:30", "%Y-%m-%d %H:%M"))      # the last stored bar opens here
OPEN = (lambda a, t: True, lambda a, idx: np.ones(len(idx), dtype=bool))
DEAD = lambda a, now_ms: False                                                 # noqa: E731  the usual feed serves nothing


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "DATA_DIR", str(tmp_path))

    def boom(*a, **k):
        raise AssertionError("no network in tests")

    monkeypatch.setattr(extdata, "fetch_chart", boom)
    ts = [(T0 - k * BAR) * 1000 for k in range(5, -1, -1)]
    c = [3640.0, 3636.0, 3632.0, 3628.0, 3624.0, 3620.0]
    extdata._save("XAUUSD", extdata._tidy("XAUUSD", extdata._frame(ts, c, [x + 2 for x in c], [x - 2 for x in c], c,
                                                                 [5.0] * 6)))
    return tmp_path


def src(n, start=T0, first=3606.0, step=-2.0):
    """A source's bars from the anchor on: the anchor closes at `first`, each later bar moves by `step`."""
    out = []
    for k in range(n + 1):
        c = first + k * step
        out.append(((start + k * BAR) * 1000, c - step, max(c, c - step) + 1.0, min(c, c - step) - 1.0, c))
    return out


def fetch_of(rows, calls=None):
    def f(symbol, start_ms, end_ms):
        if calls is not None:
            calls.append(symbol)
        return [r for r in rows if start_ms <= r[0] <= end_ms]
    return {"binance": f, "okx": f, "hyperliquid": f}


def test_scaled_joins_the_source_to_the_stored_level_and_keeps_only_closed_bars():
    rows = src(4)
    now_ms = (T0 + 4 * BAR + 60) * 1000                          # the 4th bar after the anchor is still trading
    new, ratio = bridge.scaled(rows, T0 * 1000, 3620.0, now_ms)
    assert ratio == pytest.approx(3620.0 / 3606.0) and [r[0] for r in new] == [(T0 + k * BAR) * 1000 for k in (1, 2, 3)]
    assert new[0][4] == pytest.approx(3604.0 * ratio) and new[0][1] == pytest.approx(3620.0)   # opens where it joined
    assert bridge.scaled(rows[1:], T0 * 1000, 3620.0, now_ms) == (None, "no bar at the last stored bar's time")
    assert bridge.scaled(rows[:1], T0 * 1000, 3620.0, now_ms)[0] is None
    bad = rows[:2] + [(rows[2][0], 3600.0, 3590.0, 3601.0, 3600.0)]             # a high below its low
    assert "impossible" in bridge.scaled(bad, T0 * 1000, 3620.0, now_ms)[1]
    off = rows[:2] + [(rows[2][0] + 1000, 1.0, 1.0, 1.0, 1.0)]
    assert "grid" in bridge.scaled(off, T0 * 1000, 3620.0, now_ms)[1]
    far = src(3, step=-300.0)
    assert "more than 15%" in bridge.scaled(far, T0 * 1000, 3620.0, now_ms)[1]


def test_a_feed_that_fell_behind_an_open_market_is_bridged(store):
    said = []
    now = T0 + 8 * BAR + 30                                      # seven bars have closed since the last stored one
    df, n = bridge.fill("XAUUSD", log=said.append, now=now, fetch=fetch_of(src(8)), is_open=OPEN, alive=DEAD)
    assert n == 7 and len(df) == 13
    ratio = 3620.0 / 3606.0
    assert df["close"].iloc[-1] == pytest.approx(round((3606.0 - 14.0) * ratio, 3))
    assert df["open"].iloc[6] == pytest.approx(3620.0)           # no jump at the join
    assert (df["volume"].iloc[6:] == 0).all() and (df["volume"].iloc[:6] == 5.0).all()
    assert extdata.ohlc_violations(df) == 0
    assert len(data.load("XAUUSD")) == 13                        # stored
    assert said == ["XAUUSD: 7 bars bridged from binance XAUUSDT (the usual feed served none since 04:45 UTC); "
                    "scaled by %.6f" % ratio]
    rows = open(os.path.join(str(store), bridge.LOG_FILE), encoding="utf-8").read().splitlines()
    assert rows[0].startswith("t_utc,asset,source,symbol,ratio,bars") and ",XAUUSD,binance,XAUUSDT," in rows[1]
    assert rows[1].endswith(",7,2026-11-26T04:45:00Z,2026-11-26T06:15:00Z")
    assert bridge.bridged_last("XAUUSD") == (T0 + 7 * BAR) * 1000


def test_the_usual_lag_never_starts_a_bridge_and_a_shut_market_never_does(store):
    f = fetch_of(src(8))
    assert bridge.fill("XAUUSD", now=T0 + 3 * BAR + 30, fetch=f, is_open=OPEN, alive=DEAD) == (None, 0)   # 2 bars behind
    shut = (lambda a, t: False, OPEN[1])
    assert bridge.fill("XAUUSD", now=T0 + 8 * BAR, fetch=f, is_open=shut, alive=DEAD) == (None, 0)
    assert bridge.fill("BTCUSDT", now=T0 + 8 * BAR, fetch=f, is_open=OPEN, alive=DEAD) == (None, 0)     # not a bridged market
    assert bridge.SOURCES["USDJPY"] == (("hyperliquid", "xyz:JPY"),)    # the rough bridge (owner, 28 Nov 2026)
    assert len(data.load("XAUUSD")) == 6 and not os.path.exists(os.path.join(str(store), bridge.LOG_FILE))


def test_once_bridging_it_goes_on_bar_by_bar_until_the_usual_feed_is_back(store):
    rows = src(12)
    bridge.fill("XAUUSD", log=lambda t: None, now=T0 + 8 * BAR + 30, fetch=fetch_of(rows), is_open=OPEN, alive=DEAD)
    # the very next close: one bar behind only, but the newest stored bar is a bridged one
    df, n = bridge.fill("XAUUSD", log=lambda t: None, now=T0 + 9 * BAR + 5, fetch=fetch_of(rows), is_open=OPEN, alive=DEAD)
    assert n == 1 and len(df) == 14
    assert bridge.fill("XAUUSD", now=T0 + 9 * BAR + 300, fetch=fetch_of(rows), is_open=OPEN, alive=DEAD) == (None, 0)
    # the usual feed serves again: the bridge stands back
    back = lambda a, now_ms: True                                # noqa: E731
    assert bridge.fill("XAUUSD", now=T0 + 10 * BAR + 5, fetch=fetch_of(rows), is_open=OPEN, alive=back) == (None, 0)
    assert len(data.load("XAUUSD")) == 14
    # the bridged series is one continuous series: the scale is taken anew at each join, on the stored close
    c = data.load("XAUUSD")["close"].values
    assert np.all(np.abs(np.diff(c[5:])) < 3.0)


def test_only_the_markets_own_hours_and_the_second_source_when_the_first_fails(store):
    calls = []
    halt_ms = (T0 + 4 * BAR) * 1000                              # the calendar: the market halts after three more bars
    hours = (lambda a, t: True, lambda a, idx: np.asarray([int(x.value // 1000000) < halt_ms for x in idx]))

    def broken(symbol, start_ms, end_ms):
        calls.append("binance")
        raise OSError("down")

    def good(symbol, start_ms, end_ms):
        calls.append("okx")
        return src(8)

    said = []
    df, n = bridge.fill("XAUUSD", log=said.append, now=T0 + 8 * BAR + 30, fetch={"binance": broken, "okx": good},
                        is_open=hours, alive=DEAD)
    assert calls == ["binance", "okx"] and n == 3 and "from okx XAU-USDT-SWAP" in said[0]


def test_no_source_is_one_line_and_nothing_is_written_and_it_never_raises(store, monkeypatch):
    said = []

    def broken(symbol, start_ms, end_ms):
        raise OSError("down")

    assert bridge.fill("XAUUSD", log=said.append, now=T0 + 8 * BAR, fetch={"binance": broken, "okx": broken},
                       is_open=OPEN, alive=DEAD) == (None, 0)
    assert len(said) == 1 and said[0].startswith("XAUUSD: the feed is 105 minutes behind an open market and no bridge")
    assert len(data.load("XAUUSD")) == 6
    monkeypatch.setattr(extdata, "_stored", lambda a: 1 / 0)
    assert bridge.fill("XAUUSD", log=said.append, now=T0 + 8 * BAR, fetch=fetch_of(src(8)), is_open=OPEN,
                       alive=DEAD) == (None, 0)
    assert "bridge failed (ZeroDivisionError" in said[-1]


def test_every_bridged_market_is_a_paper_market():
    from engine15 import vault_feed
    assert set(bridge.SOURCES) == {"XAUUSD", "XAGUSD", "WTI", "BRENT", "SPX", "USDJPY"} == set(extdata.ROLL_ASSETS) | {"SPX", "USDJPY"}
    assert not set(bridge.SOURCES) & set(vault_feed.ALLOWED)
    assert all(src in bridge.FETCH for cands in bridge.SOURCES.values() for src, _sym in cands)
    assert all(a in extdata.MARKETS for a in bridge.SOURCES)


def test_the_index_is_bridged_inside_cash_hours_only_and_the_night_arrives_as_the_opening_gap(store):
    close = calendar.timegm(time.strptime("2026-11-24 20:45", "%Y-%m-%d %H:%M"))      # the last bar of Tuesday's session
    opens = calendar.timegm(time.strptime("2026-11-25 14:30", "%Y-%m-%d %H:%M"))      # Wednesday 09:30 New York
    ts = [(close - k * BAR) * 1000 for k in range(3, -1, -1)]
    c = [7290.0, 7294.0, 7298.0, 7300.0]
    extdata._save("SPX", extdata._tidy("SPX", extdata._frame(ts, c, [x + 2 for x in c], [x - 2 for x in c], c, [9.0] * 4)))
    night = (opens - close) // BAR                               # the contract trades all night: 71 bars to the open
    rows = src(night + 3, start=close, first=730.0, step=0.01)   # a fund contract at a tenth of the index
    cash = (lambda a, t: True, lambda a, idx: np.asarray([int(x.value // 1000000) >= opens * 1000 for x in idx]))
    calls, said = [], []

    def broken(symbol, start_ms, end_ms):
        calls.append(symbol)
        raise OSError("down")

    def fund(symbol, start_ms, end_ms):
        calls.append(symbol)
        return [r for r in rows if start_ms <= r[0] <= end_ms]

    df, n = bridge.fill("SPX", log=said.append, now=opens + 3 * BAR + 30, is_open=cash, alive=DEAD,
                        fetch={"hyperliquid": broken, "okx": fund, "binance": broken})
    assert calls == ["xyz:SP500", "SPY-USDT-SWAP"] and n == 3 and len(df) == 7
    assert [int(x.value // 1000000) for x in df.index[4:]] == [(opens + k * BAR) * 1000 for k in (0, 1, 2)]
    ratio = 7300.0 / 730.0
    assert df["open"].iloc[4] == pytest.approx((730.0 + (night - 1) * 0.01) * ratio, abs=0.01)  # the night's move, at the open
    assert df["close"].iloc[-1] == pytest.approx((730.0 + (night + 2) * 0.01) * ratio, abs=0.01)
    assert (df["volume"].iloc[4:] == 0).all() and extdata.ohlc_violations(df) == 0
    assert said == ["SPX: 3 bars bridged from okx SPY-USDT-SWAP (the usual feed served none since 21:00 UTC); "
                    "scaled by %.6f" % ratio]
    assert bridge.bridged_last("SPX") == (opens + 2 * BAR) * 1000 and bridge.bridged_last("XAUUSD") is None
