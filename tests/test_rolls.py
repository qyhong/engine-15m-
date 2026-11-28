# -*- coding: utf-8 -*-
"""rolls: the contract-switch calendar reproduces the switches measured on 28 Nov 2026 and forecasts by rule."""
import datetime as dt

from engine15 import rolls as r

D = dt.date


def test_the_rules_give_the_switches_that_were_seen():
    assert r.cl_ltd(2026, 12) == D(2026, 11, 20)                       # CLZ26: 3 business days before 25 Nov
    assert r._forecast("CL", 2026, 12) == D(2026, 11, 18)
    assert r._forecast("BZ", 2027, 1) == D(2026, 11, 18)                # BZF27 left with CLZ26
    assert r._forecast("GC", 2026, 12) == D(2026, 11, 25)               # FND 30 Nov; 26 Nov is Thanksgiving
    assert r._forecast("SI", 2026, 12) == D(2026, 11, 25)
    for p, seen in r.SEEN.items():
        for d, frm, _to in seen:
            y, m = 2000 + int(frm[-2:]), r.CODE.index(frm[2]) + 1
            assert abs((r._forecast(p, y, m) - d).days) <= 1, (p, frm)


def test_es_and_the_next_ones():
    assert r._forecast("ES", 2026, 12) == D(2026, 12, 10)               # 3rd Friday 18 Dec minus 8 days
    nxt = dict((a, [s for s in r.switches(a, D(2026, 11, 28), D(2027, 1, 31))]) for a in ("WTI", "BRENT", "XAUUSD", "ES"))
    assert nxt["WTI"][0][:2] == (D(2026, 12, 17), "forecast")
    assert nxt["BRENT"][0][0] == nxt["WTI"][0][0]
    assert nxt["XAUUSD"][0][0] == D(2027, 1, 27)
    assert nxt["ES"][0][0] == D(2026, 12, 10)
    assert r.switches("USDJPY", D(2026, 1, 1), D(2027, 1, 1)) == []


def test_seen_replaces_its_forecast_and_the_window():
    s = r.switches("BRENT", D(2026, 11, 1), D(2026, 11, 30))
    assert s == [(D(2026, 11, 18), "seen", "BZF27 -> BZG27")]
    assert r.near_switch("BRENT", "2026-11-18 03:00")                   # 22:00 New York on the 17th: one day before
    assert r.near_switch("BRENT", "2026-11-19 15:00")
    assert not r.near_switch("BRENT", "2026-11-23 15:00")
    assert r.near_switch("XAUUSD", "2026-11-24 15:00") and r.near_switch("XAUUSD", "2026-11-27 15:00")
    assert not r.near_switch("USDJPY", "2026-11-18 12:00")


def test_business_days_outside_the_known_table():
    assert not r.is_bday(D(2024, 12, 25)) and not r.is_bday(D(2024, 3, 29))   # Christmas, Good Friday 2024
    assert r.is_bday(D(2024, 10, 14)) and r.is_bday(D(2024, 11, 11))          # Columbus / Veterans: markets open
    assert r.add_bdays(D(2026, 11, 30), -2) == D(2026, 11, 25)
