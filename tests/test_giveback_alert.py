# -*- coding: utf-8 -*-
"""The give-back alert (telegram_notify.giveback_update; owner, 21 Nov 2026): one card when an open main trade has given
back 25% of its best open profit. Read only; planted pages.

    py -3 -m pytest tests/test_giveback_alert.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import telegram_notify as tn  # noqa: E402


def page(mark, status="SHORT", entry=100.0, qty=10.0, opened="2026-11-21 07:45", gen="2026-11-21T08:00:00Z", **more):
    trade = dict({"status": status, "opened_utc": opened, "entry_price": entry, "mark_price": mark, "quantity": qty,
                  "equity_realized": 10000.0, "stop_price": 104.0}, **more)
    return {"generated_utc": gen, "assets": {"BTCUSDT": {"short": "BTC", "trade": trade}}}


def run(pages, st=None):
    out = []
    for p in pages:
        st, cards = tn.giveback_update(st, p)
        out.append(cards)
    return st, out


def test_one_card_at_a_quarter_given_back_and_not_again_until_a_new_best():
    # short from 100, 10 units: +200 at 80 (the best), +160 at 84 (20% back: quiet), +150 at 85 (25% back: the card)
    st, out = run([page(90), page(80, gen="2026-11-21T08:15:00Z"), page(84), page(85), page(86), page(85)])
    assert [len(c) for c in out] == [0, 0, 0, 1, 0, 0]
    card = out[3][0]
    assert "Give-back" in card and "BTC short" in card and "25% below" in card
    assert "+$2,250" in card and "+$3,000" in card                 # the bot's 15x display of +150 and +200
    assert "seen 2026-11-21 08:15 UTC" in card and "nothing changes" in card and "Stop 104.0" in card
    assert st["BTCUSDT"]["peak"] == 20.0 and st["BTCUSDT"]["alerted_peak"] == 20.0
    # a new, higher best, then a quarter back again: a second card
    st, out = run([page(70), page(77.5)], st)
    assert [len(c) for c in out] == [0, 1] and st["BTCUSDT"]["alerted_peak"] == 30.0


def test_a_small_best_is_not_news_and_a_loss_never_alerts():
    st, out = run([page(99.5), page(99.9), page(101.0)])           # best +5 USD: under 1% of the book
    assert out == [[], [], []]
    st, out = run([page(91.0), page(93.0)])                        # best +90: still under $100
    assert out == [[], []]
    st, out = run([page(102.0), page(103.0), page(110.0)])         # never in profit
    assert out == [[], [], []] and st["BTCUSDT"]["peak"] == -2.0


def test_closing_half_at_a_target_is_not_a_give_back():
    st, out = run([page(80), page(80, qty=5.0), page(81, qty=5.0)])   # half sold: the price profit is unchanged
    assert out == [[], [], []]
    st, out = run([page(85, qty=5.0)], st)                          # ... and 25% back on price still alerts
    assert len(out[0]) == 1 and "+$1,125" in out[0][0]              # +75 on the half that is left, 15x


def test_a_new_trade_starts_a_new_best_and_a_flat_book_drops_it():
    st, _ = run([page(80)])
    st, out = run([page(99, opened="2026-11-21 09:00")], st)        # a new trade at a small profit: no card
    assert out == [[]] and st["BTCUSDT"]["peak"] == 1.0
    st, out = run([{"generated_utc": "x", "assets": {"BTCUSDT": {"short": "BTC", "trade": {"status": "FLAT"}}}}], st)
    assert out == [[]] and "BTCUSDT" not in st
    long_st, out = run([page(120, status="LONG"), page(115, status="LONG")])
    assert len(out[1]) == 1 and "BTC long" in out[1][0]


def test_a_garbled_page_forgets_nothing_and_the_stop_lock_is_shown():
    st, _ = run([page(80)])
    for bad in (None, {}, {"assets": "x"}, {"assets": {"ETHUSDT": {"trade": None}}}):
        st2, cards = tn.giveback_update(st, bad)
        assert cards == [] and st2["BTCUSDT"] == st["BTCUSDT"]
    _st, out = run([page(85, stop_locks_usd=120.0)], st)
    assert "the stop locks +$1,800" in out[0][0]
