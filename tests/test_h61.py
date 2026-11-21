# -*- coding: utf-8 -*-
"""H61's overlay (research/h61_profit_floor.py): a wide stop on the main book's own trades, checked on planted bars.

    py -3 -m pytest tests/test_h61.py -q
"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import h61_profit_floor as h61  # noqa: E402
from engine15.config import CFG  # noqa: E402
from test_shadows import random_inputs, run_random  # noqa: E402

FLOOR = h61.RULES["floor_50pct_5r"]


def _px(closes, wick=0.1, lows=None, opens=None):
    c = np.asarray(closes, float)
    o = np.concatenate([[c[0]], c[:-1]]) if opens is None else np.asarray(opens, float)
    lo = np.minimum(o, c) - wick if lows is None else np.asarray(lows, float)
    return {"open": o, "high": np.maximum(o, c) + wick, "low": lo, "close": c}


def _x4(n, atr=1.0, lo=np.nan, hi=np.nan):
    return {"atr": np.full(n, float(atr)), "sw_lo": np.full(n, float(lo)), "sw_hi": np.full(n, float(hi))}


def test_the_floor_arms_at_5r_and_locks_half_of_the_best_close():
    # long from 100, entry stop 99 (R = 1). Closes 103, 106 (arms: level 103), 108 (level 104), then down through it.
    px = _px([100, 103, 106, 108, 107, 103.5, 103.5])
    w = h61.walk(1, 100.0, 99.0, 0, 6, px, FLOOR, _x4(7))
    assert w["armed_i"] == 2 and w["exit_i"] == 5 and w["exit_px"] == 104.0       # the low of bar 5 trades 104
    assert h61.walk(1, 100.0, 99.0, 0, 4, px, FLOOR, _x4(7))["level"] == 104.0    # not filled by bar 4 (low 106.9)
    not_yet = h61.walk(1, 100.0, 99.0, 0, 1, px, FLOOR, _x4(7))                   # 3R at the close: not armed
    assert not_yet["armed_i"] is None and not_yet["level"] is None


def test_a_bar_that_opens_through_the_level_fills_at_its_open():
    px = _px([100, 106, 106, 101, 101], opens=[100, 100, 106, 102, 101])
    w = h61.walk(1, 100.0, 99.0, 0, 4, px, FLOOR, _x4(5))
    assert w["exit_i"] == 3 and w["exit_px"] == 102.0                             # level 103, the open is 102
    short = _px([100, 94, 94, 99, 99], opens=[100, 100, 94, 98, 99])
    short["high"], short["low"] = np.maximum(short["open"], short["close"]) + 0.1, np.minimum(short["open"], short["close"]) - 0.1
    ws = h61.walk(-1, 100.0, 101.0, 0, 4, short, FLOOR, _x4(5))
    assert ws["exit_i"] == 3 and ws["exit_px"] == 98.0                            # level 97, the open is 98


def test_the_level_is_live_only_from_the_next_bar_and_never_loosens():
    px = _px([100, 106, 105, 110, 109], lows=[99.9, 99.9, 104.9, 104.9, 108.9])
    w = h61.walk(1, 100.0, 99.0, 0, 4, px, FLOOR, _x4(5))
    assert w["exit_i"] is None and w["level"] == 105.0            # bar 1's own low (99.9) is before its close set 103
    third = dict(h61.RULES["floor_33pct_3r"])
    assert abs(h61.walk(1, 100.0, 99.0, 0, 1, px, third, _x4(5))["level"] - 102.0) < 1e-12


def test_chandelier_and_swing_levels():
    px = _px([100, 104, 105, 104.5])
    ch = h61.walk(1, 100.0, 99.0, 0, 3, px, h61.RULES["chandelier_4h_3atr_3r"], _x4(4, atr=0.5))
    assert ch["armed_i"] == 1 and ch["level"] == 105 - 1.5        # best close 105, 3 x ATR 0.5
    sw = h61.walk(1, 100.0, 99.0, 0, 3, _px([100, 106, 107, 106.5]), h61.RULES["swing_4h_5r"], _x4(4, lo=103.0))
    assert sw["level"] == 103.0
    wrong = h61.walk(1, 100.0, 99.0, 0, 3, _px([100, 106, 107, 106.5]), h61.RULES["swing_4h_5r"], _x4(4, lo=108.0))
    assert wrong["armed_i"] == 1 and wrong["level"] is None       # a swing above the close is not a stop for a long


def test_the_overlay_that_never_arms_is_the_main_book():
    for seed in (3, 11):
        inp = random_inputs(seed=seed)
        px = inp[0]
        n = len(px["close"])
        main = run_random({}, inp)
        mine = h61.overlay(main, px, h61.NEVER, _x4(n), CFG["cost_side"], 1, n)
        ok, why = h61.same_as_main(main, mine, 1, n)
        assert ok, why
        assert mine["armed"] == [] and len(main["trades"]) > 20


def test_after_its_own_exit_the_overlay_is_flat_until_the_main_books_next_entry():
    inp = random_inputs(seed=3)
    px = inp[0]
    n = len(px["close"])
    main = run_random({}, inp)
    tight = {"kind": "floor", "arm_r": 0.5, "lock": 0.5, "word": "FLOOR"}        # arms often on these bars
    b = h61.overlay(main, px, tight, _x4(n), CFG["cost_side"], 1, n)
    mt, bt = main["trades"], b["trades"]
    assert len(bt) in (len(mt), len(mt) + 1)                      # + the trade main still holds, if the rule closed it
    bt = bt.iloc[:len(mt)]
    assert list(bt.i_in) == list(mt.i_in) and list(bt.p_in) == list(mt.p_in)      # main's entries, bar and price
    early = bt[(bt.why_out == "FLOOR").values & (bt.i_out.values < mt.i_out.values)]
    assert len(early) > 5
    for r in early.itertuples():
        i_main_out = int(mt.i_out[mt.i_in == r.i_in].iloc[0])
        seg = b["equity"][r.i_out:i_main_out]
        assert len(seg) and np.all(seg == seg[0])                 # flat: nothing marks, nothing re-enters
    assert (bt.i_out.values <= mt.i_out.values).all()             # the rule only ever leaves earlier, never later
    assert all(a["r_rule"] <= a["peak_r"] + 1e-9 for a in b["armed"])
    # size: scaled by this book's equity over the main book's at the entry
    k = 5
    eq_m = 10000.0 + float(mt.pnl_usd.iloc[:k].sum())
    eq_b = 10000.0 + float(bt.pnl_usd.iloc[:k].sum())
    assert abs(bt.qty.iloc[k] - mt.qty.iloc[k] * eq_b / eq_m) < 1e-9
