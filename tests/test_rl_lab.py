# -*- coding: utf-8 -*-
"""tests for engine15/rl_lab.py: the page's rl_lab block for the Lab tab (schema 1; field list in docs/RL.md).
Planted states only: test_playbook6's fixture run through playbook6 and playbook8, and planted records."""
import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from engine15 import playbook6 as p6  # noqa: E402
from engine15 import playbook8 as p8  # noqa: E402
from engine15 import rl_lab  # noqa: E402
from test_playbook6 import BOOK4, BOOK6, CFG, _setup, _step  # noqa: E402

COIN_KEYS = ("status", "position", "exposure", "equity_usd", "return_pct", "bh_spot_equity_usd", "bh_spot_return_pct",
             "max_dd_pct", "bh_max_dd_pct", "closed_trades", "trades_needed", "progress_pct", "seeds", "seeds_on_model",
             "seeds_on_fallback", "fallback_kind", "seed_modes", "split", "input_drift", "model_id", "model_data_end_utc",
             "last_decision_utc", "decisions", "late_decisions", "late_share_pct")


def _built(monkeypatch, tmp_path):
    bars, fund, snaps, md, reg, feats = _setup(tmp_path, later=True)
    rows6 = _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg)
    pb6 = p6.page_block(rows6)
    reg8 = reg + pd.Timedelta(hours=24)
    monkeypatch.setattr(p8, "REGISTERED", str(reg8)[:16])
    rows8 = p8.step(bars=bars, funding=fund, readings=snaps, journal_dir=str(tmp_path / "y8"),
                    p6_journal_dir=str(tmp_path / "fwd"), cfg=CFG, log=lambda *_: None)
    pb = {"playbook6": pb6, "playbook8": p8.page_block(rows8)}
    (tmp_path / "f5none").mkdir()
    dirs = {"forward5": str(tmp_path / "f5none"), "forward6": str(tmp_path / "fwd"), "forward8": str(tmp_path / "y8")}
    models = {"phase5": md[BOOK4], "phase6": md[BOOK6]}
    last = max(int(bars[a].index[-1].value // 10**6) + 900000 for a in bars)
    return rl_lab.block(pb, dirs, models, now_ms=last + 600000, log=lambda *_: None), pb, reg, reg8


def test_block_shape_and_values(monkeypatch, tmp_path):
    blk, pb, reg, reg8 = _built(monkeypatch, tmp_path)
    assert blk["schema"] == rl_lab.SCHEMA == 1 and blk["not_passed"] is True
    assert "None of these books has passed" in blk["note"] and "30 closed forward trades per coin" in blk["verdict_rule"]
    text = json.dumps(blk).lower()
    assert "edge" not in text and "kronos" not in text
    assert blk["interim_read"]["books"]["p6_mtrend"] == {"start_utc": "2026-11-13 03:00", "read_utc": "2027-01-08 03:00"}
    assert blk["interim_read"]["books"]["p5_rlq"]["read_utc"] == "2027-01-07 04:30"
    assert "p5_rlq" in blk["books"] and blk["books"]["p5_rlq"]["coins"] == {}          # no record, no state: no coins
    for book in (BOOK6, BOOK4):
        b = blk["books"][book]
        assert b["not_passed"] is True and b["kind"] == ("agent" if book == BOOK6 else "control")
        assert b["interim_read_utc"] == "2027-01-08 03:00" and b["fallback_kind"] == "momentum"
        assert b["started_utc"] == p6.BOOKS[book]["registered"] and b["split"] == pb["playbook6"][book]["split"]
        for a, c in b["coins"].items():
            st = pb["playbook6"][book]["books"][a]
            for k in COIN_KEYS:
                assert k in c, k
            assert c["status"] == "running" and c["trades_needed"] == 30
            assert c["equity_usd"] == st["equity_usd"] and c["split"] == st["split"]
            assert c["seeds_on_fallback"] == st["fallback_seeds"] and c["seeds"] == 3
            assert c["seeds_on_model"] + c["seeds_on_fallback"] == 3
            assert [m["mode"] for m in c["seed_modes"]] == ["fallback" if f else "model" for f in st["seed_fallback"]]
            assert c["progress_pct"] == round(min(100.0, 100.0 * c["closed_trades"] / 30), 1)
            assert c["momentum_yardstick"] == pb["playbook8"]["p8_mom"]["books"][a]["same_days"][book]
            assert c["momentum_yardstick"]["from_utc"] == str(reg8)[:16]
        ids = [r["model_id"] for r in b["refits"]]
        assert ids == (["m6_planted", "m6_later"] if book == BOOK6 else ["m5_planted"])
        r0 = b["refits"][0]
        assert r0["seeds_passed_validation"]["BTCUSDT"] == [1, 2]                 # seed 0 on the fallback for BTC
        assert r0["seeds_passed_validation"]["ETHUSDT"] == ([0, 1, 2] if book == BOOK6 else [1, 2])
        assert r0["first_decision_utc"] == str(reg + pd.Timedelta("15min"))[:16]
    # the later Phase 6 model passes every seed: since its first decision every BTC seed is on its model
    c = blk["books"][BOOK6]["coins"]["BTCUSDT"]
    later = blk["books"][BOOK6]["refits"][1]
    assert later["seeds_passed_validation"]["BTCUSDT"] == [0, 1, 2]
    assert c["seed_modes"][0] == {"seed": 0, "mode": "model", "since_utc": later["first_decision_utc"]}
    assert c["seed_modes"][1]["since_utc"] == str(reg + pd.Timedelta("15min"))[:16]
    y = blk["momentum_yardstick"]
    assert y["book"] == "p8_mom" and y["not_a_hypothesis"] is True and y["started_utc"] == p8.BOOKS["p8_mom"]["registered"]
    assert set(y["coins"]) == {"BTCUSDT", "ETHUSDT"} and set(y["coins"]["BTCUSDT"]["same_days"]) == {BOOK6, BOOK4}


def test_seed_modes_since_and_stale(tmp_path):
    J = [{"c": 1000 * 900000, "fb": [True, False]}, {"c": 1001 * 900000, "fb": [False, False]},
         {"c": 1002 * 900000, "fb": [True, False]}, {"c": 1003 * 900000, "fb": [True, True]}]
    sm = rl_lab.seed_modes(J)
    assert sm[0] == {"seed": 0, "mode": "fallback", "since_utc": rl_lab._utc(1002 * 900000)}
    assert sm[1] == {"seed": 1, "mode": "fallback", "since_utc": rl_lab._utc(1003 * 900000)}
    st = {"closed": 45, "decisions": 4, "late_decisions": 1}
    c = rl_lab._coin(st, J, 1003 * 900000 + 3 * 3600 * 1000, "flat")
    assert c["status"] == "stale" and c["progress_pct"] == 100.0 and c["late_share_pct"] == 25.0
    assert rl_lab.seed_modes([]) == []


def test_a_failure_never_stops_the_page(monkeypatch, tmp_path):
    from engine15 import export
    page = {"assets": {}, "learning": {"last_7_days": {}, "last_30_days": {}, "trust": {}}}

    def boom(*a, **k):
        raise RuntimeError("planted")
    monkeypatch.setattr(rl_lab, "block", boom)
    frag = dict(page, learning={"last_7_days": dict((k, 0) for k in ("right", "wrong", "neither", "edge_calls", "edge_right")),
                                "last_30_days": dict((k, 0) for k in ("right", "wrong", "neither", "edge_calls", "edge_right")),
                                "trust": {}})
    out = export.merge({"crypto": frag}, ["crypto"])
    assert out["rl_lab"] is None and "learning" in out
    # a broken playbook block or missing folders give a block, not an exception
    monkeypatch.undo()
    blk = rl_lab.block({"playbook6": {"p6_mtrend": {"books": {"BTCUSDT": "not a dict"}}}},
                       {"forward5": str(tmp_path), "forward6": str(tmp_path), "forward8": str(tmp_path)},
                       {"phase5": str(tmp_path), "phase6": str(tmp_path)}, log=lambda *_: None)
    assert blk["schema"] == 1 and blk["books"]["p6_mtrend"]["refits"] == []
