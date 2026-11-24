# -*- coding: utf-8 -*-
"""The profit-floor follower book (engine15/floor_book.py): H61's `floor_33pct_3r`, one step at a time.

    py -3 -m pytest tests/test_floor_book.py -q
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import h61_profit_floor as h61  # noqa: E402
from engine15 import floor_book, shadows  # noqa: E402
from engine15.config import CFG  # noqa: E402
from test_shadows import fake_prep, random_inputs, run_random  # noqa: E402

FEE = CFG["cost_side"]
COLS = [c for c in shadows.TRADE_COLS if c not in ("i_in", "i_out", "target_1", "target_2")]


def _times(n):
    return np.arange(n, dtype="int64") * 900000


def _stepped(inp, cuts, lo=1):
    """The hold copy and the follower, advanced together over the cuts. -> (trade rows, follower state, main state)."""
    px = inp[0]
    n = len(px["close"])
    m_st, f_st, rows = None, None, []
    for a, b in zip([lo] + list(cuts), list(cuts) + [n]):
        main = run_random({}, inp, lo=a, hi=b, state=m_st)
        r, f_st = floor_book.follow(m_st, main, px, _times(n), a, b, FEE, state=f_st)
        rows += r
        m_st = main["state"]
    return pd.DataFrame(rows, columns=shadows.TRADE_COLS), f_st, m_st


def _study(inp, rule, lo=1):
    px = inp[0]
    n = len(px["close"])
    main = run_random({}, inp, lo=lo)
    x4 = {"atr": np.full(n, 1.0), "sw_lo": np.full(n, np.nan), "sw_hi": np.full(n, np.nan)}
    return main, h61.overlay(main, px, rule, x4, FEE, lo, n, _times(n))


def test_the_constants_are_the_registered_rule():
    r = h61.RULES["floor_33pct_3r"]
    assert (floor_book.ARM_R, floor_book.LOCK, floor_book.WORD) == (r["arm_r"], r["lock"], r["word"])
    assert shadows.FOLLOWERS[floor_book.NAME]["follows"] == "main"
    assert floor_book.NAME not in shadows.CHALLENGERS            # not a rule of run(): the vault's book cannot see it


@pytest.mark.parametrize("arm_r,lock", [(floor_book.ARM_R, floor_book.LOCK), (0.5, 0.5), (1.0, 1.0 / 3.0)])
@pytest.mark.parametrize("seed", [3, 11])
def test_stepping_equals_the_study_trade_for_trade(monkeypatch, seed, arm_r, lock):
    """Bar by bar and in uneven pieces, the book closes the same trades as research/h61_profit_floor.overlay."""
    monkeypatch.setattr(floor_book, "ARM_R", arm_r)
    monkeypatch.setattr(floor_book, "LOCK", lock)
    inp = random_inputs(seed=seed)
    n = len(inp[0]["close"])
    main, ref = _study(inp, {"kind": "floor", "arm_r": arm_r, "lock": lock, "word": "FLOOR"})
    want = ref["trades"]
    if ref["state"]["open"] is None and len(want) > len(main["trades"]):
        pass                                                     # the rule closed the trade main still holds
    for cuts in ([], [237, 238, 640], list(range(2, n))):
        got, f_st, _m = _stepped(inp, cuts)
        assert len(got) == len(want), (cuts[:3], len(got), len(want))
        pd.testing.assert_frame_equal(got[COLS].reset_index(drop=True), want[COLS].reset_index(drop=True),
                                      check_dtype=False, rtol=1e-12, atol=1e-9)
        assert abs(f_st["eq"] - ref["state"]["eq"]) < 1e-6
        assert abs(f_st["equity_marked"] - ref["state"]["equity_marked"]) < 1e-6
    if (arm_r, lock) == (0.5, 0.5):
        assert (want.why_out == "FLOOR").sum() > 5               # the rule really acted on these bars


def test_it_never_reads_the_future():
    inp = random_inputs(seed=11)
    whole, _f, _m = _stepped(inp, [])
    for k in (300, 611):
        rng = np.random.RandomState(k)
        px = dict((key, np.array(v, copy=True)) for key, v in inp[0].items())
        for key in px:
            px[key][k + 1:] = px[key][k + 1:] * (1 + rng.normal(0, 0.05, len(px[key]) - k - 1))
        odds = np.array(inp[1], copy=True)
        odds[k + 1:] = rng.dirichlet(np.ones(3), size=len(odds) - k - 1)
        other, _f, _m = _stepped((px, odds) + tuple(inp[2:]), [])
        a = whole[whole.t_out_ms <= k * 900000][COLS].reset_index(drop=True)
        b = other[other.t_out_ms <= k * 900000][COLS].reset_index(drop=True)
        pd.testing.assert_frame_equal(a, b, check_dtype=False)


def _px(closes, lows=None, highs=None, opens=None, wick=0.1):
    c = np.asarray(closes, float)
    o = np.concatenate([[c[0]], c[:-1]]) if opens is None else np.asarray(opens, float)
    return {"open": o, "close": c,
            "high": np.maximum(o, c) + wick if highs is None else np.asarray(highs, float),
            "low": np.minimum(o, c) - wick if lows is None else np.asarray(lows, float)}


def _main_open(entry=100.0, stop0=99.0, side=1, qty=10.0, eq=10400.0, t_in_ms=0):
    return {"pos": side, "qty": qty, "entry": entry, "stop": stop0, "stop0": stop0, "eq": eq, "fees": 3.0,
            "why_in": "ENTER", "t_in_ms": t_in_ms, "i_in": -1,
            "stats": {"n": 2, "wins": 1, "pnl": 400.0, "r_sum": 1.0, "r_n": 2, "win_usd": 500.0, "loss_usd": 100.0}}


def _no_trades():
    return pd.DataFrame(columns=shadows.TRADE_COLS)


def test_a_book_added_mid_trade_copies_the_hold_copy_and_fills_only_forward():
    # the hold copy is long from 100 (R = 1) since bar 0. Closes reached 109, fell to 101 (through any floor), now 106.
    px = _px([100, 109, 101, 106, 106.5, 103.9, 103.9])
    mb = _main_open()
    rows, st = floor_book.follow(mb, {"trades": _no_trades(), "state": dict(mb)}, px, _times(7), 4, 5, FEE)
    assert rows == [] and st["pos"] == 1 and st["qty"] == 10.0 and st["eq"] == 10400.0 and st["adopted"]
    assert st["best"] == 9.0 and st["level"] == 103.0            # a third of the best CLOSE's profit; bar 2 is not replayed
    assert st["stats"]["n"] == 2 and st["copied_ms"] == 4 * 900000
    v = shadows.asset_view(st)
    assert v["status"] == "LONG" and v["stop"] == 103.0 and v["floor_armed"] and "floor" in v["stop_basis"]
    # the next bar trades 103.8 at its low: not filled; then a low of 102.9: out at 103
    px["low"][5], px["low"][6] = 103.8, 102.9
    rows, st = floor_book.follow(mb, {"trades": _no_trades(), "state": dict(mb)}, px, _times(7), 5, 6, FEE, state=st)
    assert rows == [] and st["pos"] == 1
    rows, st = floor_book.follow(mb, {"trades": _no_trades(), "state": dict(mb)}, px, _times(7), 6, 7, FEE, state=st)
    assert len(rows) == 1 and st["pos"] == 0 and st["wait_main"] and st["left_ms"] == 0
    t = dict(zip(shadows.TRADE_COLS, rows[0]))
    assert t["why_out"] == "FLOOR" and t["p_out"] == 103.0 and t["p_in"] == 100.0 and t["qty"] == 10.0
    assert abs(st["eq"] - (10400.0 + 30.0 - FEE * 10 * 203.0)) < 1e-9
    v = shadows.asset_view(st)
    assert v["status"] == "FLAT" and v["waiting_for"] == "the hold copy's next entry" and v["trades"] == 3
    # while the hold copy keeps that trade, nothing happens; its close is not this book's
    px2 = _px([100, 109, 101, 106, 106.5, 103.9, 103.9, 104, 90])
    rows, st2 = floor_book.follow(mb, {"trades": _no_trades(), "state": dict(mb)}, px2, _times(9), 7, 8, FEE, state=st)
    assert rows == [] and st2["pos"] == 0 and st2["eq"] == st["eq"]


def test_under_3r_the_copy_keeps_the_entry_stop_and_leaves_with_the_hold_copy():
    px = _px([100, 102.9, 102, 102, 101])
    mb = _main_open()
    _r, st = floor_book.follow(mb, {"trades": _no_trades(), "state": dict(mb)}, px, _times(5), 3, 4, FEE)
    assert st["level"] is None and st["stop"] == 99.0 and not st["floor"]["armed"]
    assert shadows.asset_view(st)["stop_basis"].startswith("the entry stop")
    out = pd.DataFrame([(0, 4 * 900000, -1, 4, 1, 100.0, 102.0, "ENTER", "FLIP", 2.0, 10420.0, 10.0, 20.0, 1.0, 99.0,
                         10.0, 2.0, None, None)], columns=shadows.TRADE_COLS)
    flat = dict(mb, pos=0, qty=0.0, eq=10420.0, t_in_ms=None)
    rows, st = floor_book.follow(mb, {"trades": out, "state": flat}, px, _times(5), 4, 5, FEE, state=st)
    t = dict(zip(shadows.TRADE_COLS, rows[0]))
    assert t["why_out"] == "FLIP" and t["p_out"] == 102.0 and st["pos"] == 0 and not st["wait_main"]


def test_with_no_hold_copy_before_it_the_book_starts_flat_on_the_starting_equity():
    px = _px([100, 100, 100])
    flat = {"pos": 0, "eq": 10000.0}
    _r, st = floor_book.follow(None, {"trades": _no_trades(), "state": flat}, px, _times(3), 1, 3, FEE)
    assert st["pos"] == 0 and st["eq"] == 10000.0 and "copied_ms" not in st and not st["wait_main"]


# ------------------------------------------------------------------ in the shadow step
def test_the_step_runs_it_beside_the_other_books_and_two_steps_equal_one():
    prep = fake_prep()
    one = {"version": 1, "groups": {}, "books": {}}
    two = {"version": 1, "groups": {}, "books": {}}
    _v, c_one = shadows.advance(prep, "crypto", ["BTCUSDT"], 700, one, start_lo=100)
    _v, c_a = shadows.advance(prep, "crypto", ["BTCUSDT"], 420, two, start_lo=100)
    view, c_b = shadows.advance(prep, "crypto", ["BTCUSDT"], 700, two)
    assert one["books"][floor_book.NAME] == two["books"][floor_book.NAME]
    key = (floor_book.NAME, "BTCUSDT")
    parts = [x[key] for x in (c_a, c_b) if key in x]
    assert key in c_one and len(pd.concat(parts)) == len(c_one[key])
    book = view["books"][floor_book.NAME]
    assert book["follows"] == "main" and "floor_armed" in book["assets"]["BTCUSDT"]
    board = shadows.scoreboard({"crypto": view})
    row = [r for r in board["rows"] if r["book"] == floor_book.NAME][0]
    main = [r for r in board["rows"] if r["book"] == "main"][0]
    assert row["follows"] == "main" and abs(row["vs_main_usd"] - (row["equity"] - main["equity"])) < 0.011


def test_added_to_a_running_group_it_starts_as_a_copy_of_the_hold_copy(monkeypatch):
    prep = fake_prep()
    sst = {"version": 1, "groups": {}, "books": {}}
    saved = shadows.FOLLOWERS.pop(floor_book.NAME)               # the group runs before the book exists
    try:
        shadows.advance(prep, "crypto", ["BTCUSDT"], 420, sst, start_lo=100)
    finally:
        shadows.FOLLOWERS[floor_book.NAME] = saved
    assert floor_book.NAME not in sst["books"]
    main_then = dict(sst["books"]["main"]["BTCUSDT"])
    view, _c = shadows.advance(prep, "crypto", ["BTCUSDT"], 421, sst)
    st = sst["books"][floor_book.NAME]["BTCUSDT"]
    assert st["copied_ms"] == int(prep["times"][420].timestamp() * 1000) and st["copied_utc"]
    if main_then.get("pos") and sst["books"]["main"]["BTCUSDT"].get("t_in_ms") == main_then.get("t_in_ms") and st["pos"]:
        assert st["qty"] == main_then["qty"] and st["entry"] == main_then["entry"]
    v = view["books"][floor_book.NAME]["assets"]["BTCUSDT"]
    assert v["copied_from_main_utc"] == st["copied_utc"]
    row = [r for r in shadows.scoreboard({"crypto": view})["rows"] if r["book"] == floor_book.NAME][0]
    assert row["since_utc"] == st["copied_utc"]
    assert floor_book.NAME not in (sst.get("late_starts") or {})


def test_a_failure_in_the_follower_leaves_every_other_book_as_it_was(monkeypatch):
    prep = fake_prep()
    good = {"version": 1, "groups": {}, "books": {}}
    bad = {"version": 1, "groups": {}, "books": {}}
    _v, c_good = shadows.advance(prep, "crypto", ["BTCUSDT"], 700, good, start_lo=100)

    def boom(*_a, **_k):
        raise RuntimeError("planted")
    monkeypatch.setattr(floor_book, "follow", boom)
    said = []
    view, c_bad = shadows.advance(prep, "crypto", ["BTCUSDT"], 700, bad, start_lo=100, log=lambda m: said.append(m))
    assert any("follower book" in m and "planted" in m for m in said)
    for name in shadows.CHALLENGERS:                             # b_targets among them: the vault's book
        assert bad["books"][name] == good["books"][name], name
        key = (name, "BTCUSDT")
        assert (key in c_bad) == (key in c_good)
        if key in c_good:
            pd.testing.assert_frame_equal(c_bad[key], c_good[key])
    assert floor_book.NAME not in view["books"] and floor_book.NAME not in bad["books"]
    # (H117: b_rebound, a guarded book of its own, is not touched by the follower's failure either)
    assert [r["book"] for r in shadows.scoreboard({"crypto": view})["rows"]] == list(shadows.CHALLENGERS) + ["b_rebound"]
