# -*- coding: utf-8 -*-
"""The 30-day trend filter (H67, shadow book b_trend30): b_targets, but no entry against the market's own 30-day move.
A paper shadow; b_targets itself must be untouched. No network.

    py -3 -m pytest tests/test_trend30.py -q
"""
import json
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from engine15 import policy, shadows  # noqa: E402
from engine15.config import CFG  # noqa: E402
from test_shadows import COMPARE, random_inputs  # noqa: E402

BASE = shadows.CHALLENGERS["b_targets"]["rule"]
RULE = shadows.CHALLENGERS["b_trend30"]["rule"]
BAR = CFG["bar_ms"]


def run(inp, rule, move=None, lo=1, hi=None, state=None, cfg=None):
    px, odds, unit, shock, tide, bias, guard, aux = inp
    n = len(px["close"])
    aux = dict(aux, trend_move=move) if move is not None else aux
    return shadows.run(px, odds, shock, tide, unit, cfg or shadows.asset_cfg("BTCUSDT", dict(CFG)), lo, hi or n, state=state,
                       bias=bias, guard=guard, rule=rule, aux=aux, times_ms=np.arange(n, dtype="int64") * BAR,
                       row_of=lambda k: aux["targets"].iloc[k])


def test_the_book_is_b_targets_plus_one_key_and_nothing_else_uses_it():
    assert RULE == dict(BASE, trend_days=30) and shadows.CHALLENGERS["b_trend30"]["cfg"] == {}
    assert [k for k, v in shadows.CHALLENGERS.items() if v["rule"].get("trend_days")] == ["b_trend30"]
    assert "trend_days" not in BASE


def test_the_move_is_the_close_against_the_first_bar_thirty_days_back():
    n = 40 * 96
    t = np.arange(n, dtype="int64") * BAR
    c = np.linspace(100.0, 200.0, n)
    m = shadows.trend_move(t, c, 30, 0, n)
    k = 35 * 96
    assert np.isnan(m[:30 * 96]).all() and abs(m[k] - (c[k] / c[k - 30 * 96] - 1.0)) < 1e-12 and np.isfinite(m[30 * 96:]).all()
    gap = np.concatenate([t[:1000], t[1000:] + 3 * 86400000])       # three days missing: the first bar AT OR AFTER then
    m2 = shadows.trend_move(gap, c, 30, 0, n)
    k = 3500
    back = int(np.searchsorted(gap, gap[k] - 30 * 86400000))
    assert abs(m2[k] - (c[k] / c[back] - 1.0)) < 1e-12
    part = shadows.trend_move(t, c, 30, k, k + 1)                   # one bar of a live step: the same number
    assert part[k] == m[k] and np.isnan(part[k - 1]) and np.isnan(shadows.trend_move(None, c, 30, 0, n)).all()


@pytest.mark.parametrize("seed", [3, 11])
def test_with_no_bar_thirty_days_back_nothing_is_filtered(seed):
    inp = random_inputs(seed=seed)                                  # 900 bars: under ten days
    a, b = run(inp, BASE), run(inp, RULE)
    assert len(a["trades"]) == len(b["trades"]) > 30
    for c in COMPARE:
        x, y = a["trades"][c].values, b["trades"][c].values
        assert (x == y).all() if x.dtype.kind in "OU" else np.allclose(x.astype(float), y.astype(float), equal_nan=True), c


@pytest.mark.parametrize("sign", [1, -1])
def test_no_trade_is_ever_opened_against_the_move(sign):
    inp = random_inputs(seed=3)
    n = len(inp[0]["close"])
    base = run(inp, BASE)
    got = run(inp, RULE, move=np.full(n, 0.05 * sign))
    assert len(got["trades"]) > 5 and (got["trades"].side.values == sign).all()
    assert (base["trades"].side.values == -sign).any() and len(got["trades"]) < len(base["trades"])
    assert not (got["held"] == -sign).any()


def test_a_flip_into_the_wrong_side_closes_and_opens_nothing_and_a_blocked_entry_keeps_the_idle_count():
    inp = random_inputs(seed=3)
    n = len(inp[0]["close"])
    move = np.full(n, 0.05)                                         # the market is up over 30 days: no shorts
    st, flips, waits = None, 0, 0
    for i in range(1, n):
        was = st
        b = run(inp, RULE, move=move, lo=i, hi=i + 1, state=st)
        st = json.loads(json.dumps(b["state"]))
        if st["pending"]:
            assert st["pending"][0] == policy.FLIP and st["pending"][1] == 0 and st["pos"] == 1   # a flip to FLAT only
            flips += 1
        if was and was["pending"] and was["pending"][1] == 0:
            closed = [t for t in b["trades"].itertuples() if t.why_out != "OPEN"]
            assert closed and closed[0].why_out.split("+")[-1] == "FLIP" and closed[0].i_out == i
            if "+" not in closed[0].why_out:                         # no Target 1 before: all of it at this open
                assert closed[0].p_out == inp[0]["open"][i]
        if was and was["pos"] == 0 and st["pos"] == 0 and was["idle"] >= CFG["idle_max"]:
            waits += 1
            assert st["idle"] == was["idle"] + 1                    # past the mandate and still flat: the count goes on
    assert flips >= 1 and waits >= 1


def test_an_open_position_is_not_closed_when_the_move_turns():
    inp = random_inputs(seed=3)
    n = len(inp[0]["close"])
    base = run(inp, BASE)
    t = base["trades"].iloc[0]
    move = np.full(n, 0.05 * t.side)
    move[int(t.i_in):] = -0.05 * t.side                             # the move turns against it right after its entry
    got = run(inp, RULE, move=move)["trades"].iloc[0]
    if t.why_out.split("+")[-1] in ("STOP", "STOP_BE", "T2"):
        assert (got.i_in, got.i_out, got.why_out, got.p_out) == (t.i_in, t.i_out, t.why_out, t.p_out)
    else:
        assert got.i_in == t.i_in and got.i_out == t.i_out          # a flip still closes it, at the same open


def test_bar_by_bar_is_the_whole_run_and_b_targets_is_untouched():
    inp = random_inputs(seed=11)
    n = len(inp[0]["close"])
    rng = np.random.RandomState(5)
    move = np.where(rng.rand(n) < 0.5, 0.03, -0.03) * np.repeat(rng.choice([1, -1], n // 50 + 1), 50)[:n]
    whole = run(inp, RULE, move=move)
    st, rows = None, []
    for i in range(1, n):
        b = run(inp, RULE, move=move, lo=i, hi=i + 1, state=st)
        st = json.loads(json.dumps(b["state"]))
        rows += [t for t in b["trades"].itertuples() if t.why_out != "OPEN"]
    assert len(rows) == len(whole["trades"]) > 10
    for a, b in zip(rows, whole["trades"].itertuples()):
        assert (a.t_in_ms, a.t_out_ms, a.side, a.why_out) == (b.t_in_ms, b.t_out_ms, b.side, b.why_out)
    with_aux = run(inp, BASE, move=move)                             # the base rule ignores the move even when it is there
    plain = run(inp, BASE)
    assert len(with_aux["trades"]) == len(plain["trades"]) and np.allclose(with_aux["equity"][1:], plain["equity"][1:])
