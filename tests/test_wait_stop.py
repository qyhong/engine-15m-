# -*- coding: utf-8 -*-
"""Wait for a real signal after a stop-out (H68, shadow book b_wait_stop): b_targets, but after a trade ends at its
entry stop ("STOP") there is no forced entry until a signal (ENTER) enters. A paper shadow; b_targets itself must be
untouched. No network.

    py -3 -m pytest tests/test_wait_stop.py -q
"""
import json
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from engine15 import shadows  # noqa: E402
from engine15.config import CFG  # noqa: E402
from test_shadows import COMPARE, random_inputs  # noqa: E402

BASE = shadows.CHALLENGERS["b_targets"]["rule"]
RULE = shadows.CHALLENGERS["b_wait_stop"]["rule"]
BAR = CFG["bar_ms"]


def run(inp, rule, lo=1, hi=None, state=None):
    px, odds, unit, shock, tide, bias, guard, aux = inp
    n = len(px["close"])
    return shadows.run(px, odds, shock, tide, unit, shadows.asset_cfg("BTCUSDT", dict(CFG)), lo, hi or n, state=state,
                       bias=bias, guard=guard, rule=rule, aux=aux, times_ms=np.arange(n, dtype="int64") * BAR,
                       row_of=lambda k: aux["targets"].iloc[k])


def pairs(tr):
    """(previous trade's exit word, this trade's entry word) for each trade after the first."""
    rows = list(tr.itertuples())
    return [(p.why_out, t.why_in) for p, t in zip(rows, rows[1:])]


def test_the_book_is_b_targets_plus_one_key_and_nothing_else_uses_it():
    assert RULE == dict(BASE, wait_after_stop=True) and shadows.CHALLENGERS["b_wait_stop"]["cfg"] == {}
    assert [k for k, v in shadows.CHALLENGERS.items() if v["rule"].get("wait_after_stop")] == ["b_wait_stop"]
    assert "wait_after_stop" not in BASE


@pytest.mark.parametrize("seed", [3, 11, 17])
def test_no_forced_entry_after_a_stop_and_forced_entries_as_usual_after_other_exits(seed):
    inp = random_inputs(n=3000, seed=seed)
    base, got = run(inp, BASE), run(inp, RULE)
    pb, pg = pairs(base["trades"]), pairs(got["trades"])
    assert any(o == "STOP" and i == "FORCED" for o, i in pb)          # the current rule does re-enter by force
    assert any(o == "STOP" for o, _i in pg)
    assert not any(o == "STOP" and i == "FORCED" for o, i in pg)      # the new one never does
    others = [o for o, i in pg if i == "FORCED"]
    assert others and all(o != "STOP" for o in others)               # after STOP_BE, T2, a flip ...: forced as usual
    assert any(o.split("+")[-1] in ("STOP_BE", "T2", "FLIP") for o in others)
    # up to the first stop-out the two books are the same book
    k = next(j for j, t in enumerate(base["trades"].itertuples()) if t.why_out == "STOP")
    for c in COMPARE:
        x, y = base["trades"][c].values[:k + 1], got["trades"][c].values[:k + 1]
        assert (x == y).all() if x.dtype.kind in "OU" else np.allclose(x.astype(float), y.astype(float), equal_nan=True), c
    st = got["state"]["wait_stop"]
    assert st["episodes"] >= 1 and st["blocked"] >= st["episodes"]


def test_bar_by_bar_is_the_whole_run_and_a_signal_clears_the_switch():
    inp = random_inputs(n=3000, seed=11)
    n = len(inp[0]["close"])
    whole = run(inp, RULE)
    st, rows, waited, cleared, withheld = None, [], 0, 0, 0
    for i in range(1, n):
        was = st
        b = run(inp, RULE, lo=i, hi=i + 1, state=st)
        st = json.loads(json.dumps(b["state"]))
        rows += [t for t in b["trades"].itertuples() if t.why_out != "OPEN"]
        if was and was["wait_stop"]["on"] and was["pos"] == 0:
            if st["pos"] == 0 and not st["pending"] and was["idle"] >= CFG["idle_max"]:
                waited += 1                                          # past the mandate and still flat: the count goes on
                assert st["idle"] == was["idle"] + 1 and st["wait_stop"]["on"] >= 1   # (1: an IDLE of its own, the guard)
                withheld += st["wait_stop"]["on"] == 2
            if st["pos"] != 0:
                cleared += 1
                assert st["wait_stop"]["on"] == 0 and st["why_in"] == "ENTER"   # only a signal entered, and cleared it
    assert waited >= 1 and cleared >= 1 and withheld >= 1
    assert len(rows) == len(whole["trades"]) > 10
    for a, b in zip(rows, whole["trades"].itertuples()):
        assert (a.t_in_ms, a.t_out_ms, a.side, a.why_in, a.why_out, a.p_out) == (b.t_in_ms, b.t_out_ms, b.side, b.why_in,
                                                                                b.why_out, b.p_out)
    assert st["wait_stop"] == whole["state"]["wait_stop"] and st["eq"] == pytest.approx(whole["state"]["eq"])


def test_the_state_key_is_only_in_this_book_and_b_targets_is_untouched():
    inp = random_inputs(n=1500, seed=3)
    for name, spec in shadows.CHALLENGERS.items():
        if spec["rule"].get("swing") or spec["rule"].get("h5") or spec["rule"].get("daily_close"):
            continue
        st = run(inp, spec["rule"])["state"]
        assert ("wait_stop" in st) == (name == "b_wait_stop"), name
    a = run(inp, BASE)
    b = run(inp, dict(BASE, wait_after_stop=False))                  # the flag off: the very same book
    assert list(a["state"]) == list(b["state"]) and len(a["trades"]) == len(b["trades"])
    assert np.allclose(a["equity"][1:], b["equity"][1:])
