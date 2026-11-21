# -*- coding: utf-8 -*-
"""RL health readings (21 Nov 2026): who earned a book's result (agent / fallback), the input drift reading, and the
Telegram cards built from them. They decide nothing; planted data only.

    py -3 -m pytest tests/test_rl_health.py -q
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from engine15 import playbook6 as p6  # noqa: E402
from engine15 import telegram_notify as tn  # noqa: E402
from engine15.rl import forward5  # noqa: E402
from test_playbook6 import BOOK4, BOOK6, CFG, _J, _model, _setup, _step  # noqa: E402


def test_the_split_adds_up_to_the_book_and_follows_the_seed_modes(monkeypatch, tmp_path):
    bars, fund, snaps, md, reg, feats = _setup(tmp_path)
    rows = _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg)
    blk = p6.page_block(rows)
    for book, fb_seeds in ((BOOK6, {"BTCUSDT": 1, "ETHUSDT": 0}), (BOOK4, {"BTCUSDT": 1, "ETHUSDT": 1})):
        tot = {"agent_gross_usd": 0.0, "fallback_gross_usd": 0.0, "costs_usd": 0.0, "net_usd": 0.0}
        for a, s in blk[book]["books"].items():
            sp = s["split"]
            assert abs(sp["agent_gross_usd"] + sp["fallback_gross_usd"] - sp["costs_usd"] - sp["net_usd"]) < 0.03
            assert abs(sp["net_usd"] - (s["equity_usd"] - p6.STAKE)) < 0.011
            assert abs(sp["agent_seed_bars_pct"] - 100.0 * (3 - fb_seeds[a]) / 3) < 0.06
            assert sp["all_fallback_bars_pct"] == 0.0
            if fb_seeds[a] == 0:
                assert sp["fallback_gross_usd"] == 0.0 and sp["last_7d"]["fallback_gross_usd"] == 0.0
            else:
                assert sp["fallback_gross_usd"] != 0.0                 # a trend seed holds a position
            assert sp["costs_usd"] > 0
            for k in tot:
                tot[k] += sp[k]
        whole = blk[book]["split"]
        assert whole["coins"] == 2 and all(abs(whole[k] - tot[k]) < 0.011 for k in tot)


def test_a_coin_with_every_seed_on_the_fallback_has_no_agent_result(monkeypatch, tmp_path):
    bars, fund, snaps, md, reg, feats = _setup(tmp_path)
    cols = list(feats["BTCUSDT"].columns)
    all_fb = dict(((s, "BTCUSDT"), True) for s in range(3))
    with open(os.path.join(md[BOOK6], "model_a.json"), "w") as fh:
        json.dump(_model("m6_planted", int(reg.value // 10**6), cols, feats, all_fb, 0), fh)
    rows = _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg)
    s = p6.page_block(rows)[BOOK6]["books"]["BTCUSDT"]
    sp = s["split"]
    assert s["fallback_seeds"] == 3 and sp["agent_gross_usd"] == 0.0 and sp["agent_seed_bars_pct"] == 0.0
    assert sp["all_fallback_bars_pct"] == 100.0
    assert abs(sp["fallback_gross_usd"] - sp["costs_usd"] - sp["net_usd"]) < 0.03


def test_the_drift_reading_counts_inputs_far_from_training():
    F = 10
    model = {"seeds": {"0": {"stats": {"BTCUSDT": {"mu": [1.0] * F, "sd": [2.0] * F}}}}}
    rows = np.ones((3, F))
    rows[1, :5] = 1.0 + 4 * 2.0                                   # half the inputs 4 sd away
    rows[2, 0] = np.nan                                           # a missing input reads as the mean
    rows[2, 1] = 1.0 - 3.1 * 2.0
    got = forward5.input_drift(model, 0, "BTCUSDT", rows)
    assert list(np.round(got, 3)) == [0.0, 0.5, 0.1]
    assert forward5.drift_view([{"t": 1}]) is None
    j = [{"dz": 0.02}] * forward5.WEEK_BARS + [{"dz": 0.10}] * forward5.WEEK_BARS
    v = forward5.drift_view(j)
    assert v["last_7d_pct"] == 10.0 and v["week_before_pct"] == 2.0 and v["decisions_7d"] == forward5.WEEK_BARS


def test_every_decision_carries_the_reading_and_the_page_shows_it(monkeypatch, tmp_path):
    bars, fund, snaps, md, reg, feats = _setup(tmp_path)
    rows = _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg)
    J = _J(tmp_path, BOOK6, "ETHUSDT")
    assert all(0.0 <= r["dz"] <= 1.0 for r in J)
    d = p6.page_block(rows)[BOOK6]["books"]["ETHUSDT"]["input_drift"]
    assert d["z"] == 3.0 and abs(d["last_7d_pct"] - 100 * float(np.mean([r["dz"] for r in J][-forward5.WEEK_BARS:]))) < 0.006


def test_a_failure_in_the_health_fields_changes_no_decision_and_no_trade(monkeypatch, tmp_path):
    bars, fund, snaps, md, reg, feats = _setup(tmp_path)
    good = _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg, jd="a")

    def boom(*_a, **_k):
        raise RuntimeError("planted")
    monkeypatch.setattr(forward5, "health_fields", boom)
    monkeypatch.setattr(forward5, "input_drift", boom)
    bad = _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg, jd="b")
    assert [dict(r, text="") for r in bad] == [dict(r, text="") for r in good]
    for a in p6.ASSETS:
        ja, jb = _J(tmp_path, BOOK6, a, jd="a"), _J(tmp_path, BOOK6, a, jd="b")
        strip = lambda r: dict((k, v) for k, v in r.items() if k not in ("dz", "at", "lag_s"))   # noqa: E731
        assert [strip(r) for r in ja] == [strip(r) for r in jb] and "dz" not in jb[0] and "dz" in ja[0]
    st = p6.page_block(bad)[BOOK6]
    assert "split" not in st["books"]["BTCUSDT"] and st["split"] is None


# ------------------------------------------------------------------ the Telegram cards
def _page(fb_btc, model="m6_a", drift=1.0, pos="short 1.00x since 2026-11-15 23:45 UTC"):
    def st(fb, rule=True):
        s = {"seed_fallback": fb, "model": model, "book_position": pos,
             "split": {"last_7d": {"agent_gross_usd": 10.0, "fallback_gross_usd": 80.0, "costs_usd": 4.0}},
             "input_drift": {"last_7d_pct": drift, "week_before_pct": None}}
        if rule:
            s["fallback_rule"] = "momentum"
        return s
    return {"playbook": {"playbook5": {"p5_rlq": {"books": {"BTCUSDT": st([True, True, True], rule=False),
                                                              "ETHUSDT": st([False, True, True], rule=False)}}},
                         "playbook6": {"p6_mtrend": {"books": {"BTCUSDT": st(fb_btc), "ETHUSDT": st([False] * 3)}}}}}


def test_one_card_when_no_agent_trades_and_one_line_when_one_is_back():
    st, card = tn.rl_fallback_update(None, _page([True, True, True]))
    assert st == {"p5_rlq|BTCUSDT": True, "p5_rlq|ETHUSDT": False, "p6_mtrend|BTCUSDT": True, "p6_mtrend|ETHUSDT": False}
    assert "no agent is trading" in card and "stays flat" in card and "30-day momentum position (short 1.00x" in card
    assert card.count("all 3 seed agents") == 2 and "ETH" not in card and "paper only" in card
    st2, again = tn.rl_fallback_update(st, _page([True, True, True]))
    assert again is None and st2 == st                            # said once
    st3, back = tn.rl_fallback_update(st2, _page([True, False, True]))
    assert "agent back" in back and "1 of 3 seed agents trade again" in back and st3["p6_mtrend|BTCUSDT"] is False
    st4, none = tn.rl_fallback_update(st3, {"playbook": "garbled"})
    assert none is None and st4 == st3                            # a garbled page: no card, nothing forgotten


def test_the_weekly_card_goes_out_once_when_a_new_model_is_in_use():
    models, week, card = tn.rl_weekly_update(None, None, _page([True] * 3, model="m6_a", drift=1.0))
    assert card is None and models["p6_mtrend|BTCUSDT"] == "m6_a" and week["p6_mtrend|BTCUSDT"] == {"agents": 0, "drift": 1.0}
    m2, w2, none = tn.rl_weekly_update(models, week, _page([True] * 3, model="m6_a", drift=1.2))
    assert none is None and w2 == week                            # same model: nothing sent, the snapshot kept
    m3, w3, card = tn.rl_weekly_update(m2, w2, _page([False, False, True], model="m6_b", drift=6.0))
    assert "new models in use" in card and "agents 2/3 (was 0/3)" in card
    assert "inputs off-range 6.0% (was 1.0%)" in card and "drifting" in card
    assert "week: agent +$150" in card and "fallback +$1,200" in card and "costs -$60" in card   # the bot's 15x display
    assert m3["p6_mtrend|BTCUSDT"] == "m6_b" and w3["p6_mtrend|BTCUSDT"] == {"agents": 2, "drift": 6.0}
    calm = tn.rl_health_card(_page([False] * 3, drift=1.5), {"p6_mtrend|BTCUSDT": {"agents": 3, "drift": 1.0}})
    assert "drifting" not in calm and "none of these books has passed" in calm
    assert "no RL book state" in tn.rl_health_card({})
