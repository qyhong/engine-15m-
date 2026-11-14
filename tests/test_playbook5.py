# -*- coding: utf-8 -*-
"""tests for engine15/playbook5.py: the RL agent (Phase 4 primary) as a forward paper book (NOT passed).

1. Interface: BOOKS / step / page_block as docs/PLAYBOOK_INTERFACE.md and playbook4's block fields (title, hypothesis,
   registered, not_passed, rule, note, per-coin books with position / equity / spot buy-and-hold since go-live), "NOT
   passed" in the title, the note and the scoreboard title; registered in engine15/reports.py.
2. Forward only: nothing before REGISTERED counts; the book is $10,000 until the first decision after it.
3. Accounting: the trades' P&L adds up to the book's equity change; a step again on the same bars records nothing new.
4. The live step stays light (planted data: well under the 5 s budget).
The forward == batch and no-look-ahead tests on real data are in tests/rl/test_phase5.py."""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine15 import playbook5 as p5  # noqa: E402
from engine15.rl import features4, forward5, pool4  # noqa: E402

CFG = forward5.load_cfg()


def _bars(n, seed):
    rng = np.random.RandomState(seed)
    close = 30000.0 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    opn = np.concatenate([[30000.0], close[:-1]])
    sp = np.abs(rng.normal(0, 0.001, n)) * close
    return pd.DataFrame({"open": opn, "high": np.maximum(opn, close) + sp, "low": np.minimum(opn, close) - sp,
                         "close": close, "volume": rng.uniform(50, 150, n)},
                        index=pd.date_range("2026-01-01", periods=n, freq="15min", tz="UTC").as_unit("ms"))


def _funding(index):
    from engine15.rl import data
    t = pd.date_range(index[0].floor("8h"), index[-1], freq="8h", tz="UTC")
    raw = t.as_unit("ms").asi8.astype("int64")
    return pd.DataFrame({"rate": np.full(len(t), 0.0001), "settle_ms": data.settlement_ms(raw)},
                        index=pd.to_datetime(raw, unit="ms", utc=True))


def _setup(tmp_path, n=5600):
    bars, fund, snaps, feats = {}, {}, {}, {}
    for k, a in enumerate(p5.ASSETS):
        b = _bars(n, 30 + k)
        bars[a], fund[a] = b, _funding(b.index)
        rng = np.random.default_rng(40 + k)
        vals = dict((c, rng.standard_normal(n).astype(np.float32)) for c in list(features4.READINGS) + features4.AVAIL_COLS)
        snaps[a] = str(tmp_path / ("snap_%s.npz" % a))
        np.savez(snaps[a], times_ms=np.asarray(b.index.as_unit("ms").asi8, dtype=np.int64), meta="{}", **vals)
        feats[a] = features4.build(b, fund[a], CFG["features"], features4.readings_frame(snaps[a], b.index)).astype("float32")
    cols = list(feats["BTCUSDT"].columns)
    F = len(cols)
    q = CFG["qagent"]
    seeds = {}
    for s in range(3):
        stats = {}
        for a in p5.ASSETS:
            mu, sd = pool4.norm_stats(feats[a].values, 0, n, np.arange(F))
            stats[a] = {"mu": mu.tolist(), "sd": sd.tolist()}
        seeds[str(s)] = {"weights": [(3.0 * np.random.default_rng(s).standard_normal((5, F))).tolist()],
                         "biases": [np.zeros(5).tolist()], "stats": stats, "fallback": {"BTCUSDT": False, "ETHUSDT": False}}
    reg = bars["BTCUSDT"].index[4900] + pd.Timedelta("15min")
    model = {"id": "m_planted", "data_end_close_ms": int(reg.value // 10**6), "data_end_utc": str(reg)[:16],
             "columns": cols, "actions": CFG["actions"], "min_hold_bars": 4,
             "qagent": dict((k, q[k]) for k in ("reward_scale", "cost_mult", "obs_clip", "activation", "vol_scale",
                                                "vol_ref_annual", "vol_scale_cap", "risk_aversion", "net_arch")),
             "seeds": seeds, "info": {}}
    md = tmp_path / "models"
    md.mkdir()
    with open(md / "model_planted.json", "w") as fh:
        json.dump(model, fh)
    return bars, fund, snaps, str(md), reg


def _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg, now=None):
    monkeypatch.setattr(p5, "REGISTERED", str(reg)[:16])
    return p5.step(bars=bars, funding=fund, readings=snaps, journal_dir=str(tmp_path / "fwd"), models_dir=md,
                   now_ms=now, launch=False, log=lambda *_: None)


def test_interface_and_registration():
    b = p5.BOOKS[p5.BOOK]
    assert "NOT passed" in b["title"] and "NOT passed" in b["scoreboard_title"]
    assert set(b["assets"]) == {"BTCUSDT", "ETHUSDT"}
    assert "RL agent (Phase 4 primary), forward paper; NOT passed: after fees it trailed buy-and-hold in history." in p5.NOT_PASSED
    from engine15 import reports
    assert "playbook5" in reports.PLAYBOOK_MODULES
    assert reports._scoreboard_titles()[p5.BOOK] == b["scoreboard_title"]
    pd.Timestamp(p5.REGISTERED, tz="UTC")


def test_forward_book_block_and_accounting(monkeypatch, tmp_path):
    bars, fund, snaps, md, reg = _setup(tmp_path)
    t0 = time.time()
    rows = _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg)
    assert time.time() - t0 < 5.0
    blk = p5.page_block(rows)[p5.BOOK]
    for k in ("title", "hypothesis", "registered", "not_passed", "rule", "note", "books", "open", "recent", "totals"):
        assert k in blk
    assert blk["not_passed"] is True and "NOT passed" in blk["note"] and "NOT passed" in blk["title"]
    assert set(blk["books"]) == {"BTCUSDT", "ETHUSDT"}
    for a, s in blk["books"].items():
        for k in ("book_position", "equity_usd", "return_pct", "bh_spot_equity_usd", "bh_spot_return_pct", "max_dd_pct",
                  "bh_max_dd_pct", "rule_exposure", "last_close_utc", "forward_trades"):
            assert k in s, k
        J = forward5.read_journal(str(tmp_path / "fwd" / ("decisions_%s.jsonl" % a)))
        assert J and min(r["c"] for r in J) > p5.reg_ms()                       # forward only
        assert len(J) == len(bars[a]) - 4901
        # the trades' P&L adds up to the equity change (every bar counted once)
        mine = [r for r in rows if r["asset"] == a]
        assert len(mine) >= 3
        assert abs(sum(r["pnl_usd"] for r in mine) - (s["equity_usd"] - p5.STAKE)) < 0.05 + 0.01 * len(mine)
    for r in rows:
        assert r["status"] in ("OPEN", "CLOSED") and r["side"] in (1, -1) and "NOT passed" in r["text"]
        assert r["entry_utc"] > str(reg)[:16]
    # the same bars again: nothing new recorded, the same rows
    n0 = [len(forward5.read_journal(str(tmp_path / "fwd" / ("decisions_%s.jsonl" % a)))) for a in p5.ASSETS]
    rows2 = _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg)
    assert [len(forward5.read_journal(str(tmp_path / "fwd" / ("decisions_%s.jsonl" % a)))) for a in p5.ASSETS] == n0
    assert [r["pnl_usd"] for r in rows2] == [r["pnl_usd"] for r in rows]


def test_nothing_counts_before_registered(monkeypatch, tmp_path):
    bars, fund, snaps, md, reg = _setup(tmp_path)
    now = int(reg.value // 10**6)                                              # exactly at go-live: nothing yet
    rows = _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg, now=now)
    assert rows == [] and p5.LAST_STATE.get(p5.BOOK, {}) == {}
    rows = _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg, now=now + 2 * 900000)
    blk = p5.page_block(rows)[p5.BOOK]
    for a, s in blk["books"].items():
        assert s["decisions"] == 2 and abs(s["equity_usd"] - p5.STAKE) < 50
