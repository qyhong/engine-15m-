# -*- coding: utf-8 -*-
"""tests for engine15/playbook8.py: the momentum yardstick p8_mom (the Phase 6 books' trend fallback alone; a yardstick,
not a hypothesis). Planted data only (test_playbook6's fixture); the live folders and the evidence store are never touched.

1. Interface and labels: BOOKS / step / page_block as the other strategy books; in reports.PLAYBOOK_MODULES with its
   scoreboard title; no "edge" or "Kronos" in what reaches the page; it never calls itself passed.
2. The very same rule: on the same bars its decisions equal a Phase 6 book's whose every seed is on the 'do no harm'
   fallback, record for record, and its book equals that book's to the cent (same start).
3. Accounting: fills at the next open, rows add up to the equity, nothing before REGISTERED, append-only record.
4. Same days: a Phase 6 book's return over the yardstick's own days is its equity marked at the yardstick's start.
5. A failure never stops the step."""
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from engine15 import playbook6 as p6  # noqa: E402
from engine15 import playbook8 as p8  # noqa: E402
from engine15.rl import forward5  # noqa: E402
from test_playbook6 import BOOK4, BOOK6, CFG, _J, _model, _setup, _step  # noqa: E402

BOOK = "p8_mom"


def _step8(monkeypatch, tmp_path, bars, fund, snaps, reg, now=None, jd="y8", jd6="fwd"):
    monkeypatch.setattr(p8, "REGISTERED", str(reg)[:16])
    return p8.step(bars=bars, funding=fund, readings=snaps, journal_dir=str(tmp_path / jd),
                   p6_journal_dir=str(tmp_path / jd6), now_ms=now, cfg=CFG, log=lambda *_: None)


def _J8(tmp_path, a, jd="y8"):
    return forward5.read_journal(str(tmp_path / jd / ("decisions_%s_%s.jsonl" % (BOOK, a))))


def _all_fallback(md, reg, feats):
    """BOOK6's model with every seed on the fallback on both coins."""
    cols = list(feats["BTCUSDT"].columns)
    fb = dict(((s, a), True) for s in range(3) for a in p6.ASSETS)
    with open(os.path.join(md[BOOK6], "model_a.json"), "w") as fh:
        json.dump(_model("m6_planted", int(reg.value // 10**6), cols, feats, fb, 0), fh)


# ---------------------------------------------------------------- 1. interface and labels
def test_interface_labels_and_registration():
    assert set(p8.BOOKS) == {BOOK}
    f = p8.BOOKS[BOOK]
    assert set(f["assets"]) == {"BTCUSDT", "ETHUSDT"} and tuple(f["yardstick_for"]) == (BOOK6, BOOK4)
    assert "not a hypothesis" in f["title"] and "not a hypothesis" in f["scoreboard_title"]
    from engine15 import reports
    assert "playbook8" in reports.PLAYBOOK_MODULES
    assert reports.PLAYBOOK_MODULES.index("playbook8") > reports.PLAYBOOK_MODULES.index("playbook6")   # P6 records first
    assert reports._scoreboard_titles()[BOOK] == f["scoreboard_title"]
    r = pd.Timestamp(p8.REGISTERED, tz="UTC")
    assert r == pd.Timestamp("2026-11-23 00:00", tz="UTC")                   # as registered in research/HYPOTHESES.md
    with open(os.path.join(ROOT, "research", "HYPOTHESES.md"), encoding="utf-8") as fh:
        reg = fh.read()
    assert "Forward yardstick p8_mom" in reg and "2026-11-23 00:00 UTC" in reg
    for path in ("engine15/playbook8.py", "engine15/rl_lab.py"):
        with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
            low = fh.read().lower()
        assert "kronos" not in low and "edge" not in low
    texts = json.dumps(p8.page_block([])).lower()
    assert "edge" not in texts and " passed" not in texts.replace("not_passed", "")
    m = p8.yard_model(CFG)
    assert all(all(s["fallback"][a] for a in p8.ASSETS) for s in m["seeds"].values())
    assert "weights" not in json.dumps(m) and len(m["seeds"]) == len(CFG["phase5"]["forward"]["seeds"])


# ---------------------------------------------------------------- 2. the very same rule
def test_same_decisions_and_book_as_a_phase6_book_on_the_fallback(monkeypatch, tmp_path):
    bars, fund, snaps, md, reg, feats = _setup(tmp_path)
    _all_fallback(md, reg, feats)
    _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg)
    rows = _step8(monkeypatch, tmp_path, bars, fund, snaps, reg)
    blk6 = p6.page_block(_step(monkeypatch, tmp_path, bars, fund, snaps, md, reg))[BOOK6]["books"]
    blk8 = p8.page_block(rows)[BOOK]["books"]
    for a in p8.ASSETS:
        J6, J8 = _J(tmp_path, BOOK6, a), _J8(tmp_path, a)
        assert len(J8) == len(J6) == len(bars[a]) - 4901
        for x, y in zip(J6, J8):
            assert (x["t"], x["c"], x["ip"], x["req"], x["fb"], x["mode"]) == (y["t"], y["c"], y["ip"], y["req"], y["fb"], y["mode"])
        assert all(r["m"] == p8.MODEL_ID and r["mode"] == ["trend"] * 3 for r in J8)
        ref = np.nan_to_num(feats[a]["mom_signal"].astype(np.float32).values)
        ms = np.asarray(bars[a].index.as_unit("ms").asi8)
        r_at = ref[np.searchsorted(ms, [r["t"] for r in J8])]
        assert np.mean(np.array([r["req"][0] for r in J8]) == r_at) > 0.98      # it holds the daily momentum position
        for k in ("equity_usd", "bh_spot_equity_usd", "rule_exposure", "forward_trades", "closed", "book_position"):
            assert blk6[a][k] == blk8[a][k], k
        assert blk8[a]["daily_direction"] == blk6[a]["daily_direction"]


# ---------------------------------------------------------------- 3. accounting, start, record
def test_rows_block_fills_and_start(monkeypatch, tmp_path):
    bars, fund, snaps, md, reg, feats = _setup(tmp_path)
    now = int(reg.value // 10**6)
    assert _step8(monkeypatch, tmp_path, bars, fund, snaps, reg, now=now, jd="early") == []   # nothing at the start itself
    assert p8.LAST_STATE == {}
    rows = _step8(monkeypatch, tmp_path, bars, fund, snaps, reg)
    blk = p8.page_block(rows)[BOOK]
    for k in ("title", "hypothesis", "registered", "rule", "note", "books", "open", "recent", "totals", "yardstick"):
        assert k in blk
    assert blk["yardstick"] is True and "not a hypothesis" in blk["note"].lower()
    for a, s in blk["books"].items():
        J = _J8(tmp_path, a)
        assert J and min(r["c"] for r in J) > p8.reg_ms()
        assert s["first_decision_utc"] == str(reg + pd.Timedelta("15min"))[:16]
        mine = [r for r in rows if r["asset"] == a]
        assert mine and abs(sum(r["pnl_usd"] for r in mine) - (s["equity_usd"] - p8.STAKE)) < 0.05 + 0.01 * len(mine)
        op = bars[a]["open"]
        for r in mine:
            assert abs(r["entry"] - op.loc[pd.Timestamp(r["entry_utc"], tz="UTC")]) < 1e-6
            if r["status"] == "CLOSED":
                assert abs(r["exit"] - op.loc[pd.Timestamp(r["exit_utc"], tz="UTC")]) < 1e-6
    for r in rows:
        assert r["book"] == BOOK and r["status"] in ("OPEN", "CLOSED") and r["side"] in (1, -1)
        assert r["why_out"] in ("RULE", "OPEN") and r["stop"] is None and r["r"] is None
        assert "yardstick" in r["text"] and "edge" not in r["text"].lower()
    # append-only and idempotent
    paths = [str(tmp_path / "y8" / ("decisions_%s_%s.jsonl" % (BOOK, a))) for a in p8.ASSETS]
    before = [open(p, "rb").read() for p in paths]
    rows2 = _step8(monkeypatch, tmp_path, bars, fund, snaps, reg)
    assert [open(p, "rb").read() for p in paths] == before
    assert [r["pnl_usd"] for r in rows2] == [r["pnl_usd"] for r in rows]


# ---------------------------------------------------------------- 4. same days
def test_same_days_beside_the_phase6_books(monkeypatch, tmp_path):
    bars, fund, snaps, md, reg, feats = _setup(tmp_path)
    _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg)
    reg8 = reg + pd.Timedelta(hours=50)                                       # the yardstick starts later
    _step8(monkeypatch, tmp_path, bars, fund, snaps, reg8)
    r8 = int(reg8.value // 10**6)
    for a in p8.ASSETS:
        st = p8.LAST_STATE[BOOK][a]
        assert set(st["same_days"]) == {BOOK6, BOOK4}
        J8 = _J8(tmp_path, a)
        B8 = forward5.risk_and_book(CFG, bars[a], fund[a], J8, r8)
        for book in (BOOK6, BOOK4):
            sd = st["same_days"][book]
            B6 = forward5.risk_and_book(CFG, bars[a], fund[a], _J(tmp_path, book, a), p6.reg_ms())
            cm = B6["close_ms"][B6["lo"]:B6["n"]]
            k0 = int(np.nonzero(cm == r8)[0][0])
            want = 100 * (B6["equity"][-1] / B6["equity"][k0] - 1)
            assert abs(sd["book_return_pct"] - want) < 1e-3
            assert abs(sd["yardstick_return_pct"] - 100 * (B8["equity"][-1] / p8.STAKE - 1)) < 1e-3
            assert abs(sd["bh_spot_return_pct"] - 100 * (B6["bh_equity"][-1] / B6["bh_equity"][k0] - 1)) < 1e-3
            assert sd["from_utc"] == str(reg8)[:16] and abs(sd["difference_pts"] - (want - sd["yardstick_return_pct"])) < 2e-3
    assert p8.mark_at(B8, r8) == p8.STAKE


# ---------------------------------------------------------------- 5. a failure never stops the step
def test_a_failure_is_logged_not_raised(monkeypatch, tmp_path):
    bars, fund, snaps, md, reg, feats = _setup(tmp_path)

    def boom(*a, **k):
        raise RuntimeError("planted")
    monkeypatch.setattr(forward5, "advance", boom)
    seen = []
    monkeypatch.setattr(p8, "REGISTERED", str(reg)[:16])
    rows = p8.step(bars=bars, funding=fund, readings=snaps, journal_dir=str(tmp_path / "x"), cfg=CFG, log=seen.append)
    assert rows == [] and any("planted" in s for s in seen)
    from engine15 import reports
    monkeypatch.setattr(reports, "PLAYBOOK_MODULES", ("playbook8",))
    monkeypatch.setattr(reports, "PLAYBOOK_JSON", str(tmp_path / "playbook.json"))
    monkeypatch.setattr(p8, "step", boom)
    out = []
    assert reports.playbooks(log=out.append) == [] and any("playbook8 failed" in s for s in out)
