# -*- coding: utf-8 -*-
"""H62's replay (research/h62_setups_wide_stop.py): the reduced Setups book against shadows.run, and the wide stop.

    py -3 -m pytest tests/test_h62.py -q
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

import h62_setups_wide_stop as h62  # noqa: E402
from engine15 import backtest  # noqa: E402
from engine15.config import CFG  # noqa: E402
from test_shadows import random_inputs, run_random  # noqa: E402


def _run(inp, mode=None, m_pos=None, m_stop=None, cfg=None):
    px, odds, unit, shock, tide, bias, guard, aux = inp
    n = len(px["close"])
    return h62.run_setups(px, odds, shock, tide, unit, cfg or CFG, 1, n, bias=bias, guard=guard,
                          times_ms=np.arange(n, dtype="int64") * 900000, row_of=lambda k: aux["targets"].iloc[k],
                          mode=mode, m_pos=m_pos, m_stop=m_stop)


@pytest.mark.parametrize("seed", [3, 11, 17])
def test_with_no_wide_stop_the_copy_is_the_setups_book(seed):
    inp = random_inputs(seed=seed)
    n = len(inp[0]["close"])
    ref = run_random({"targets": True}, inp)
    mine = _run(inp)
    ok, why = h62.same_book(ref, mine, 1, n)
    assert ok, why
    assert len(ref["trades"]) > 30 and ref["trades"].why_out.str.contains("T1").any()
    # a main book that never counts (other side, or flat) changes nothing either
    none = _run(inp, mode="follow", m_pos=np.zeros(n, dtype=np.int8), m_stop=np.full(n, np.nan))
    ok, why = h62.same_book(ref, none, 1, n)
    assert ok, why


def _main_like(inp, extra):
    """A 'main book' that always holds the Setups book's side with a stop `extra` x further than the book's own."""
    base = _run(inp)
    px, unit = inp[0], inp[2]
    n = len(px["close"])
    m_pos, m_stop = np.zeros(n, dtype=np.int8), np.full(n, np.nan)
    for t in base["trades"].itertuples():
        i = int(t.i_in)
        m_pos[i:int(t.i_out) + 1] = int(t.side)
        m_stop[i:int(t.i_out) + 1] = t.p_in - t.side * extra * CFG["stop_units"] * unit[i - 1]
    return base, m_pos, m_stop


def test_a_carries_the_main_books_stop_from_the_fill_and_keeps_the_targets():
    inp = random_inputs(seed=3)
    base, m_pos, m_stop = _main_like(inp, 3.0)
    a = _run(inp, mode="entry", m_pos=m_pos, m_stop=m_stop)
    first_b, first_a = base["trades"].iloc[0], a["trades"].iloc[0]
    assert first_a.i_in == first_b.i_in and first_a.p_in == first_b.p_in           # the same entry
    assert first_a.target_1 == first_b.target_1 and first_a.target_2 == first_b.target_2   # targets from the OWN stop
    assert abs(abs(first_a.p_in - first_a.stop0) - 3.0 * abs(first_b.p_in - first_b.stop0)) < 1e-9
    f = a["wide"][0]
    assert f["wide_at_entry"] and abs(f["ratio"] - 3.0) < 1e-9 and f["moves_out"] == f["moves_in"] == 0
    assert (a["trades"].why_out == "STOP").sum() < (base["trades"].why_out == "STOP").sum()   # fewer stop-outs
    # a main-book stop that is TIGHTER never counts: the book is unchanged
    _b, m_pos2, m_stop2 = _main_like(inp, 0.5)
    ok, why = h62.same_book(base, _run(inp, mode="entry", m_pos=m_pos2, m_stop=m_stop2), 1, len(inp[0]["close"]))
    assert ok, why


def test_the_position_is_sized_on_the_stop_it_carries():
    inp = random_inputs(seed=3)
    cfg = dict(CFG, leverage_cap=100.0)
    px, unit = inp[0], inp[2]
    base = _run(inp, cfg=cfg)
    n = len(px["close"])
    t = base["trades"].iloc[0]
    i = int(t.i_in)
    m_pos, m_stop = np.zeros(n, dtype=np.int8), np.full(n, np.nan)
    m_pos[i], m_stop[i] = int(t.side), t.p_in - t.side * 4.0 * CFG["stop_units"] * unit[i - 1]
    a = _run(inp, mode="entry", m_pos=m_pos, m_stop=m_stop, cfg=cfg)
    ta = a["trades"].iloc[0]
    want = backtest.leverage(cfg, t.p_in, 4.0 * CFG["stop_units"] * unit[i - 1]) * 10000.0 / t.p_in
    assert abs(ta.qty - want) < 1e-9 and ta.qty < t.qty                     # a wider stop, a smaller position


def _px(o, h, l, c):
    return dict((k, np.asarray(v, float)) for k, v in zip(("open", "high", "low", "close"), (o, h, l, c)))


def _planted(mode, m_pos, m_stop, highs):
    """Short from 100 at bar 2 (own stop 104), decided at bar 1; then the highs given. No targets."""
    n = len(highs)
    px = _px([100.0] * n, highs, [99.5] * n, [100.0] * n)
    odds = np.zeros((n, 3))                                       # down leads by 30 points: enter short, then hold
    odds[:, h62.labels.UP], odds[:, h62.labels.DOWN] = 0.30, 0.60
    odds[0] = np.nan
    return h62.run_setups(px, odds, np.zeros(n, bool), np.zeros(n), np.full(n, 2.0), dict(CFG, htf_bias=False), 1, n,
                          times_ms=np.arange(n, dtype="int64") * 900000, row_of=None, mode=mode,
                          m_pos=np.asarray(m_pos, dtype=np.int8), m_stop=np.asarray(m_stop, float))


def test_b_moves_out_and_back_in_and_c_only_moves_in():
    nan = np.nan
    highs = [100.5, 100.5, 100.5, 100.5, 104.5, 100.5, 100.5, 104.5, 100.5]
    # the main book: flat at the fill (bar 2), short with a stop at 106 from bar 4 to bar 6, then gone
    m_pos = [0, 0, 0, 0, -1, -1, -1, 0, 0]
    m_stop = [nan, nan, nan, nan, 106.0, 106.0, 106.0, nan, nan]
    cur = _planted(None, m_pos, m_stop, highs)
    assert cur["trades"].iloc[0].i_out == 4 and cur["trades"].iloc[0].why_out == "STOP"     # own stop 104 is hit
    a = _planted("entry", m_pos, m_stop, highs)
    assert a["trades"].iloc[0].i_out == 4                         # the main book was flat at the fill: A changes nothing
    b = _planted("follow", m_pos, m_stop, highs)
    tb, fb = b["trades"].iloc[0], b["wide"][0]
    assert tb.i_out == 7 and tb.p_out == 104.0 and tb.why_out == "STOP"     # out to 106 at bar 4, back to 104 at bar 7
    assert fb["moves_out"] == 1 and fb["moves_in"] == 1 and not fb["wide_at_entry"]
    c = _planted("entry_tighten", m_pos, m_stop, highs)
    assert c["trades"].iloc[0].i_out == 4 and c["wide"][0]["moves_out"] == 0    # C never moves out
    # C: wide at the fill, then in when the main book leaves
    m_pos2 = [0, 0, -1, -1, -1, 0, 0, 0, 0]
    m_stop2 = [nan, nan, 106.0, 106.0, 106.0, nan, nan, nan, nan]
    c2 = _planted("entry_tighten", m_pos2, m_stop2, highs)
    t2, f2 = c2["trades"].iloc[0], c2["wide"][0]
    assert f2["wide_at_entry"] and f2["moves_in"] == 1 and t2.i_out == 7 and t2.p_out == 104.0
    a2 = _planted("entry", m_pos2, m_stop2, highs)
    assert a2["open"] is not None and a2["open"]["stop_now"] == 106.0 and len(a2["trades"]) == 0   # A keeps 106: still open


def test_the_main_books_stop_series_is_what_was_in_force_at_each_open():
    tr = pd.DataFrame([(5, 9, -1, 100.0, 101.0, "ENTER", "TRAIL", 0, 0, 1, 0, 0),
                       (12, 15, 1, 100.0, 102.0, "FLIP", "FLIP", 0, 0, 1, 0, 0)],
                      columns=["i_in", "i_out", "side", "p_in", "p_out", "why_in", "why_out", "pnl_pct", "equity", "qty",
                               "pnl_usd", "fees_usd"])
    stop = np.full(20, np.nan)
    stop[5:9] = [104.0, 104.0, 103.0, 101.0]
    stop[12:15] = 96.0
    m_pos, m_stop = h62.main_series({"trades": tr, "stop": stop}, np.full(20, 2.0), 2.0, 20)
    assert list(m_pos[4:11]) == [0, -1, -1, -1, -1, -1, 0]        # held in its exit bar (a stop filled inside it)
    assert list(m_stop[5:10]) == [104.0, 104.0, 104.0, 103.0, 101.0]   # entry stop, then the level of the close before
    assert list(m_pos[11:17]) == [0, 1, 1, 1, 0, 0]               # a flip at the open of bar 15: not held in bar 15
    assert m_stop[12] == 96.0 and m_stop[14] == 96.0 and np.isnan(m_stop[15])
