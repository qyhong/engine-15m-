# -*- coding: utf-8 -*-
"""H60's copy of the book runner (research/h60_regime_exits.run_switch), checked on planted bars. No network.

    py -3 -m pytest tests/test_h60.py -q
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import h60_regime_exits as h60  # noqa: E402
from engine15 import shadows  # noqa: E402
from engine15.config import CFG  # noqa: E402
from test_shadows import LONG, aux_for, bars, random_inputs, run_random  # noqa: E402


def run_copy(inp, tswitch, rule=None):
    px, odds, unit, shock, tide, bias, guard, aux = inp
    n = len(px["close"])
    return h60.run_switch(px, odds, shock, tide, unit, CFG, 1, n, bias=bias, guard=guard, rule=rule or {}, aux=aux,
                          times_ms=np.arange(n, dtype="int64") * 900000, row_of=lambda k: aux["targets"].iloc[k],
                          tswitch=tswitch)


def test_copy_without_switch_is_shadows_run():
    inp = random_inputs()
    for rule in ({}, {"targets": True}):
        ok, why = h60.same_book(run_random(rule, inp), run_copy(inp, None, rule))
        assert ok, why


def test_switch_off_is_main_and_on_is_b_targets():
    for seed in (3, 11):
        inp = random_inputs(seed=seed)
        reg = np.array(["RANGE"] * len(inp[0]["close"]), dtype=object)
        main, tgt = run_random({}, inp), run_random({"targets": True}, inp)
        off = run_copy(inp, h60.switch_for("always_off", reg))
        on = run_copy(inp, h60.switch_for("always_on", reg))
        assert len(main["trades"]) > 20 and len(tgt["trades"]) > 20
        ok, why = h60.same_book(main, off)
        assert ok, why
        ok, why = h60.same_book(tgt, on)
        assert ok, why
        assert not any(off["modes"]) and all(on["modes"])
        assert (tgt["trades"].why_out.str.contains("T1|T2")).any()   # targets really acted


def test_gate_catches_a_difference():
    inp = random_inputs()
    main, tgt = run_random({}, inp), run_random({"targets": True}, inp)
    assert not h60.same_book(main, tgt)[0]


# ------------------------------------------------------------------ planted bars: the mode each variant chooses
def planted(reg_label):
    """A long entered at bar 2's open (decided at bar 1's close), price 100, stop 2 x 2 = 4 below; a bar that
    reaches Target 1 (102) and Target 2 (104) at bar 4; the odds stay long (no flip)."""
    n = 12
    px = bars(n, 100.0, wick=0.2)
    px["high"][4] = 104.5
    aux = aux_for(n)
    aux["targets"] = pd.DataFrame(index=range(n))
    reg = np.array([reg_label] * n, dtype=object)
    return px, aux, reg


def go_planted(px, aux, reg, name, plan):
    n = len(px["close"])
    od = np.tile(np.asarray(LONG, float), (n, 1))
    import engine15.live as live
    old = live.plan_targets
    live.plan_targets = lambda side, entry, stop, row: {"target_1": entry + side * 2.0, "target_2": entry + side * 4.0,
                                                         "target_1_basis": "t", "target_2_basis": "t"}
    try:
        return h60.run_switch(px, od, np.zeros(n, bool), np.zeros(n), np.full(n, 2.0), CFG, 1, n, rule={}, aux=aux,
                              times_ms=np.arange(n, dtype="int64") * 900000, row_of=lambda k: pd.Series(dtype=float),
                              tswitch=h60.switch_for(name, reg if plan is None else plan))
    finally:
        live.plan_targets = old


def test_variant1_flip_mode_in_a_directional_regime_and_target_mode_otherwise():
    px, aux, reg = planted("TREND_UP")
    b = go_planted(px, aux, reg, "rg_dir_entry", None)
    assert len(b["trades"]) == 0 and b["state"]["pos"] == 1          # held: no target taken
    px, aux, reg = planted("RANGE")
    b = go_planted(px, aux, reg, "rg_dir_entry", None)
    assert b["modes"][0] is True
    assert b["trades"].why_out.iloc[0] == "T1+T2" and int(b["trades"].i_out.iloc[0]) == 4


def test_variant5_is_the_mirror():
    px, aux, reg = planted("MOMENTUM_UP")
    b = go_planted(px, aux, reg, "rg_dir_entry_inv", None)
    assert b["modes"][0] is True and b["trades"].why_out.iloc[0] == "T1+T2"
    px, aux, reg = planted("TRANSITION")
    b = go_planted(px, aux, reg, "rg_dir_entry_inv", None)
    assert len(b["trades"]) == 0 and b["state"]["pos"] == 1


def test_variant3_passes_a_target_in_a_directional_bar_and_takes_it_later():
    px, aux, reg = planted("RANGE")
    reg[:] = "TRANSITION"
    reg[3] = "TREND_UP"                          # the label known before bar 4: directional -> bar 4 passes it by
    px["high"][6] = 104.5                        # bar 6 reaches both again; row 5 is TRANSITION -> acted on
    b = go_planted(px, aux, reg, "rg_dir_live", reg)
    assert b["trades"].why_out.iloc[0] == "T1+T2" and int(b["trades"].i_out.iloc[0]) == 6
    reg[:] = "TREND_DOWN"                        # directional all through: no target ever acted on
    b = go_planted(px, aux, reg, "rg_dir_live", reg)
    assert len(b["trades"]) == 0 and b["state"]["pos"] == 1


def test_variant2_aligned():
    px, aux, reg = planted("TREND_DOWN")         # directional but against a long: target mode
    b = go_planted(px, aux, reg, "rg_dir_aligned", None)
    assert b["trades"].why_out.iloc[0] == "T1+T2"
    px, aux, reg = planted("TREND_UP")           # with the long: flip mode
    b = go_planted(px, aux, reg, "rg_dir_aligned", None)
    assert len(b["trades"]) == 0


def test_shadows_is_not_imported_as_modified():
    assert h60.run_switch is not shadows.run
