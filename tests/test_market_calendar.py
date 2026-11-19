# -*- coding: utf-8 -*-
"""engine15/market_calendar.py: exchange holidays and early closes (2026-2027), used for scheduling only, and its
consumers (parallel.bar_due, setups.market_hours, stocks). Pure, no network.

    py -3 -m pytest tests/test_market_calendar.py -q
"""
import datetime as dt
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from engine15 import evcache, extdata, market_calendar as mc, parallel, setups, stocks  # noqa: E402


def T(s):
    return pd.Timestamp(s, tz="UTC")


def test_the_nyse_list_is_the_rule_extdata_uses():
    for y in (2026, 2027):
        shut, early = extdata.nyse_days(y)
        assert {d for d in mc.NYSE_CLOSED if d.year == y} == shut
        assert {d for d in mc.NYSE_EARLY if d.year == y} == early
    assert all(hm == (13, 0) for hm in mc.NYSE_EARLY.values())


def test_thanksgiving_week_2026():
    # Thursday 26 November: the NYSE is shut all day; CME metals/energy halt at 13:30 New York (18:30 UTC)
    assert mc.closed("SPX", T("2026-11-26 15:00")) and not mc.is_open("SPX", T("2026-11-26 15:00"))
    assert not mc.closed("XAUUSD", T("2026-11-26 15:00")) and mc.is_open("XAUUSD", T("2026-11-26 18:15"))
    assert not mc.is_open("XAUUSD", T("2026-11-26 18:30")) and not mc.is_open("WTI", T("2026-11-26 20:00"))
    assert mc.is_open("XAUUSD", T("2026-11-26 23:00"))                           # 18:00 New York: Friday's session
    assert mc.early_close_utc("XAUUSD", dt.date(2026, 11, 26)) == T("2026-11-26 18:30")
    # Friday 27 November: the NYSE closes at 13:00 New York (18:00 UTC); CME at 13:45 (18:45 UTC)
    assert mc.early_close_utc("SPX", dt.date(2026, 11, 27)) == T("2026-11-27 18:00")
    assert mc.early_close_utc("SPX", "2026-11-27") == T("2026-11-27 18:00")
    assert mc.is_open("SPX", T("2026-11-27 17:45")) and not mc.is_open("SPX", T("2026-11-27 18:00"))
    assert not mc.closed("SPX", T("2026-11-27 18:30"))                           # an early close, not a holiday
    assert mc.is_open("XAGUSD", T("2026-11-27 18:30")) and not mc.is_open("XAGUSD", T("2026-11-27 18:45"))
    assert mc.early_close_utc("SPX", dt.date(2026, 11, 30)) is None
    # Brent and USDJPY: nothing modelled for Thanksgiving
    assert mc.is_open("BRENT", T("2026-11-26 19:00")) and mc.is_open("USDJPY", T("2026-11-26 19:00"))
    assert mc.early_close_utc("BRENT", dt.date(2026, 11, 27)) is None
    # a normal day
    assert all(mc.is_open(a, T("2026-11-30 15:00")) for a in ("SPX", "XAUUSD", "WTI", "BRENT", "USDJPY"))
    assert not mc.closed("BTCUSDT", T("2026-11-26 15:00")) and mc.early_close_utc("BTCUSDT", "2026-11-27") is None


def test_christmas_new_year_and_2027():
    for a in ("SPX", "XAUUSD", "WTI", "BRENT"):
        assert mc.closed(a, T("2026-12-25 15:00")) and not mc.is_open(a, T("2026-12-25 15:00"))
    assert mc.closed("XAUUSD", T("2026-12-24 23:30"))                            # Thursday evening = trade date 25th
    assert not mc.is_open("XAUUSD", T("2026-12-24 19:00"))                       # Christmas Eve: 13:45 New York
    assert mc.is_open("SPX", T("2026-12-24 17:45")) and not mc.is_open("SPX", T("2026-12-24 18:00"))
    assert mc.is_open("USDJPY", T("2026-12-25 15:00"))                           # spot FX: not modelled
    assert mc.closed("XAUUSD", T("2027-01-01 12:00")) and mc.closed("BRENT", T("2027-01-01 12:00"))
    assert mc.closed("SPX", T("2027-03-26 15:00")) and mc.closed("WTI", T("2027-03-26 15:00"))   # Good Friday
    assert mc.closed("SPX", T("2027-11-25 15:00")) and mc.early_close_utc("SPX", "2027-11-26") == T("2027-11-26 18:00")
    assert mc.closed("SPX", T("2027-12-24 15:00")) and mc.closed("SPX", T("2027-06-18 15:00"))
    assert mc.early_close_utc("WTI", "2027-07-05") == T("2027-07-05 17:30")     # summer: 13:30 New York = 17:30 UTC
    assert mc.is_open("SPX", T("2027-12-23 15:00"))


def test_the_vector_form_agrees():
    idx = pd.date_range(T("2026-11-25 00:00"), T("2026-11-30 23:45"), freq="15min")
    for a in ("SPX", "XAUUSD", "BRENT", "USDJPY"):
        m = mc.open_mask(a, idx)
        assert list(m) == [mc.is_open(a, t) for t in idx]
    assert len(mc.open_mask("SPX", idx[:0])) == 0


def test_not_part_of_the_reading_signature():
    sig = evcache.code_signature.__code__.co_consts
    assert not any("market_calendar" in str(c) for c in sig)


def due(asset, last, now):
    r = parallel.bar_due(asset, T(last), T(now).timestamp())
    return None if r is None else str(pd.Timestamp(r, unit="s"))[5:16]


def test_no_bar_wait_on_a_holiday_or_after_an_early_close():
    assert due("SPX", "2026-11-25 20:45", "2026-11-26 15:01:15") is None         # Thanksgiving: no S&P bar due
    assert due("SPX", "2026-11-25 20:45", "2026-11-27 14:46:15") == "11-27 14:30"  # Friday's first bar, across it
    assert due("SPX", "2026-11-27 17:30", "2026-11-27 18:01:15") == "11-27 17:45"  # the early close's last bar
    assert due("SPX", "2026-11-27 17:45", "2026-11-27 18:16:15") is None         # nothing after 18:00 UTC
    assert due("SPX", "2026-11-27 17:45", "2026-11-30 14:46:15") == "11-30 14:30"
    assert due("XAUUSD", "2026-11-26 18:00", "2026-11-26 18:46:15") == "11-26 18:15"   # the halt's last bar (feed late)
    assert due("XAUUSD", "2026-11-26 18:15", "2026-11-26 19:01:15") is None      # halted from 18:30 UTC
    assert due("XAUUSD", "2026-11-26 18:15", "2026-11-26 23:31:15") == "11-26 23:00"   # reopened for Friday
    assert due("XAUUSD", "2026-11-27 18:30", "2026-11-27 19:31:15") is None      # after Friday's 13:45 close
    assert due("WTI", "2026-12-24 18:30", "2026-12-25 16:01:15") is None         # Christmas
    assert due("XAUUSD", "2026-12-24 18:30", "2026-12-27 23:31:15") == "12-27 23:00"   # the gap was the holiday


def test_setups_market_hours_on_the_holiday():
    ms = lambda s: int(T(s).timestamp() * 1000)                                  # noqa: E731
    assert setups.market_hours("SPX", ms("2026-11-26 15:00")) == (False, "2026-11-27T14:30:00Z")
    assert setups.market_hours("SPX", ms("2026-11-27 18:10")) == (False, "2026-11-30T14:30:00Z")
    assert setups.market_hours("SPX", ms("2026-11-27 17:50")) == (True, None)
    assert setups.market_hours("XAUUSD", ms("2026-11-26 19:00")) == (False, "2026-11-26T23:00:00Z")
    assert setups.market_hours("XAUUSD", ms("2026-11-27 19:00")) == (False, "2026-11-29T23:00:00Z")
    assert setups.market_hours("BRENT", ms("2026-12-25 12:00")) == (False, "2026-12-28T01:00:00Z")
    assert setups.market_hours("USDJPY", ms("2026-11-26 19:00")) == (True, None)


def test_stocks_session_slot_knows_the_holiday():
    ms = lambda s: int(T(s).timestamp() * 1000)                                  # noqa: E731
    assert stocks.last_session_bar_ms(T("2026-11-26 17:00").timestamp()) == ms("2026-11-25 20:45")
    assert stocks.last_session_bar_ms(T("2026-11-28 12:00").timestamp()) == ms("2026-11-27 17:45")
