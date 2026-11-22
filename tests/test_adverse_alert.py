# -*- coding: utf-8 -*-
"""The Setups moving-against alert (telegram_notify.adverse_update; owner, 22 Nov 2026): card A at half way from the entry
to the trade's starting stop, card B within a quarter R of it; once each per trade; nothing after Target 1. Read only;
planted pages.

    py -3 -m pytest tests/test_adverse_alert.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import telegram_notify as tn  # noqa: E402


def view(status="SHORT", entry=3000.0, stop=3100.0, opened="2026-11-22 08:00", t1=False, **more):
    if status == "FLAT":
        return {"status": "FLAT", "equity": 10000.0}
    return dict({"status": status, "entry": entry, "stop": stop, "opened_utc": opened, "target_1": 2900.0,
                 "target_2": 2800.0, "t1_taken": t1, "equity": 10000.0}, **more)


def page(price, market="ETHUSDT", group="crypto", as_of="2026-11-22 10:45", **kw):
    px = {} if price is None else {market: {"start_price": 2500.0, "price": price}}
    return {"generated_utc": "2026-11-22T10:46:00Z",
            "shadows": {"books": {"b_targets": {"title": "B", "assets": {market: view(**kw)}},
                                  "b_trail": {"title": "T", "assets": {market: view(entry=1.0, stop=2.0)}}},
                        "markets": {group: {"started_utc": "2026-11-11 05:45", "as_of_utc": as_of, "assets": px}}}}


def run(pages, st=None):
    out = []
    for p in pages:
        st, cards = tn.adverse_update(st, p)
        out.append(cards)
    return st, out


def test_card_a_once_then_card_b_once():
    # short from 3000, stop 3100, R 100: A at 3050 (half way), B at 3075 (within 0.25R of the stop)
    st, out = run([page(3020), page(3049), page(3050), page(3060), page(3040), page(3055), page(3075), page(3090),
                   page(3060), page(3080)])
    assert [len(c) for c in out] == [0, 0, 1, 0, 0, 0, 1, 0, 0, 0]
    a, b = out[2][0], out[6][0]
    assert "moving against" in a and "ETH short" in a and "entry 3,000.00" in a and "3,050.00" in a
    assert "half way to its stop" in a and "Stop 3,100.00" in a and "1.6% from the price" in a
    assert "close of 10:45 UTC" in a and "nothing was changed" in a and "Member accounts" in a
    assert "close to the stop" in b and "three quarters of the way" in b and "0.8% from the price" in b
    assert st["ETHUSDT"]["a"] and st["ETHUSDT"]["b"]


def test_straight_to_the_stop_sends_card_b_only():
    # DECISION: a trade first seen within 0.25R of its stop gets ONE card (B); A is marked as sent and never follows
    st, out = run([page(3010), page(3080), page(3060), page(3050)])
    assert [len(c) for c in out] == [0, 1, 0, 0] and "close to the stop" in out[1][0]
    st, out = run([page(3120)])                                     # past the stop (the book closes at the next bar)
    assert len(out[0]) == 1 and "at or past its stop" in out[0][0]


def test_a_long_and_the_wording_rules():
    kw = dict(status="LONG", entry=60000.0, stop=58000.0, market="BTCUSDT")
    st, out = run([page(59500, **kw), page(59000, **kw), page(58400, **kw)])
    assert [len(c) for c in out] == [0, 1, 1]
    assert "BTC long" in out[1][0] and "59,000.00" in out[1][0] and "Member accounts" in out[1][0]
    for c in out[1] + out[2]:
        low = c.lower()
        assert "edge" not in low and "kronos" not in low
    st, out = run([page(61000, **kw)])                              # in profit: nothing
    assert out == [[]]


def test_a_market_members_do_not_follow_has_no_member_line():
    st, out = run([page(31.5, market="XAGUSD", group="metals", status="SHORT", entry=30.0, stop=32.0)])
    assert len(out[0]) == 1 and "Silver short" in out[0][0] and "31.5000" in out[0][0]
    assert "Member accounts" not in out[0][0]


def test_nothing_after_target_1():
    st, out = run([page(2950), page(2950, t1=True, stop=3000.0), page(3080, t1=True, stop=3000.0)])
    assert out == [[], [], []] and st["ETHUSDT"]["t1"]
    st, out = run([page(3080, t1=False)], st)                       # the same trade: still nothing
    assert out == [[]]
    st, out = run([page(3080, t1=True)])                            # first seen after Target 1: nothing
    assert out == [[]]


def test_a_new_trade_rearms_and_flat_drops_the_state():
    st, out = run([page(3080)])
    assert len(out[0]) == 1
    st, out = run([page(3080, opened="2026-11-22 11:00")], st)      # another opening time: fresh
    assert len(out[0]) == 1
    st, out = run([page(3020, status="LONG", entry=3100.0, stop=3000.0, opened="2026-11-22 11:00")], st)   # another side
    assert len(out[0]) == 1 and "ETH long" in out[0][0]
    st, out = run([page(3080, status="FLAT")], st)
    assert out == [[]] and "ETHUSDT" not in st


def test_r_comes_from_the_first_stop_seen():
    # first seen with stop 3100 (R 100); later the page shows a tighter stop of 3060: card A still at 3050, B at 3075
    st, out = run([page(3010), page(3045, stop=3060.0), page(3050, stop=3060.0), page(3074, stop=3060.0)])
    assert [len(c) for c in out] == [0, 0, 1, 0]
    assert "Stop 3,100.00" in out[2][0] and st["ETHUSDT"]["stop0"] == 3100.0
    st, out = run([page(3075, stop=3060.0)], st)
    assert len(out[0]) == 1 and "close to the stop" in out[0][0]


def test_garbled_pages_and_no_price_change_nothing():
    st, _ = run([page(3050)])
    before = dict(st["ETHUSDT"])
    bad_pages = [None, {}, "x", {"shadows": None}, {"shadows": {"books": "x"}}, {"shadows": {"books": {}}},
                 {"shadows": {"books": {"b_targets": {"assets": None}}}},
                 {"shadows": {"books": {"b_targets": {"assets": {"ETHUSDT": None}}}}},
                 {"shadows": {"books": {"b_targets": {"assets": {"ETHUSDT": {"status": "SHORT"}}}}}},
                 {"shadows": {"books": {"b_targets": {"assets": {"ETHUSDT": view(entry="x")}}}}},
                 {"shadows": {"books": {"b_targets": {"assets": {}}}, "markets": "x"}}]
    for bad in bad_pages:
        st2, cards = tn.adverse_update(st, bad)
        assert cards == [] and st2["ETHUSDT"] == before
    # no price for the market: no card, the trade is still remembered; the card comes when a price is there
    st, out = run([page(None), page(3080, as_of=None)], st)
    assert out[0] == [] and len(out[1]) == 1 and "close of" not in out[1][0]
    st, out = run([page("nan"), page(-1.0)], {})
    assert out == [[], []] and "ETHUSDT" in st
