# -*- coding: utf-8 -*-
"""vault_feed's optional book key `opened_by` ("ENTER" / "FORCED"), switched OFF in the shipped code. No network.

    py -3 -m pytest tests/test_vault_opened_by.py -q
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import vault_feed as vf  # noqa: E402
from test_vault_trail import bar, ep, passes, targets, trail  # noqa: E402,F401  (passes: the vault replaced by a list)

OPENED = "2026-11-25T18:45:00Z"


def page(view, book="b_targets", sym="BTCUSDT"):
    return {"shadows": {"books": {book: {"assets": {sym: view}}}}}


def view(side="SHORT", opened="2026-11-25 18:45", by="FORCED"):
    return {"status": side, "entry": 60000.0, "stop": 61500.0, "opened_utc": opened, "opened_by": by}


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setattr(vf, "SEND_OPENED_BY", True)


def test_the_switch_is_off_in_the_shipped_code_and_then_nothing_changes(tmp_path):
    """Switching it on needs the AI Trading session's word that an installed vault package accepts the key, and the
    owner's yes (CLAUDE.md, the money path)."""
    assert vf.SEND_OPENED_BY is False and vf.OPENED_BY == ("ENTER", "FORCED", "FLIP")
    b = vf.build_book(targets(), bar(0), opened_by="FORCED")[0]["book"]
    assert "opened_by" not in b
    st = {"pos": {"BTCUSDT": {"opened_utc": OPENED, "opened_by": "FORCED"}}}
    assert vf.remembered_opened_by(st, "BTCUSDT", targets(), page(view())) is None


def test_the_word_is_read_from_the_books_own_view_of_this_very_setup():
    m = targets()
    assert vf.opened_by_of(page(view()), m) == "FORCED"
    assert vf.opened_by_of(page(view(by="ENTER")), m) == "ENTER"
    assert vf.opened_by_of(page(view(by="FLIP")), m) == "FLIP"                   # said, so it is not "unknown"
    assert vf.opened_by_of(page(view(by="REBOUND")), m) is None                  # any other word: the key is left out
    assert vf.opened_by_of(page(view(by=None)), m) is None
    assert vf.opened_by_of(page(view(opened="2026-11-25 19:00")), m) is None     # another setup
    assert vf.opened_by_of(page(view(side="LONG")), m) is None
    assert vf.opened_by_of(page(view(), book="b_trail_setups"), m) is None       # the other voice's book is not asked
    assert vf.opened_by_of(None, m) is None and vf.opened_by_of(page(view()), dict(m, side="FLAT")) is None
    t = trail(opened=OPENED)
    assert vf.opened_by_of(page(view(by="ENTER"), book="b_trail_setups"), t) == "ENTER"
    assert vf.opened_by_of(page(view(by="ENTER")), t) is None                    # a trail market asks the trail book


def test_on_both_bodies_carry_it_and_only_the_two_words(on, monkeypatch):
    b = vf.build_book(targets(), bar(0), opened_by="FORCED")[0]["book"]
    assert b["opened_by"] == "FORCED"
    assert vf.build_book(targets(), bar(0), opened_by="FLIP")[0]["book"]["opened_by"] == "FLIP"
    assert "opened_by" not in vf.build_book(targets(), bar(0), opened_by="REBOUND")[0]["book"]
    assert "opened_by" not in vf.build_book(targets(), bar(0))[0]["book"]
    assert "opened_by" not in vf.build_book(targets(side="FLAT"), bar(0), opened_by="FORCED")[0]["book"]
    monkeypatch.setattr(vf, "SEND_TRAIL", True)
    assert vf.build_book(trail(), bar(0), opened_by="ENTER")[0]["book"]["opened_by"] == "ENTER"


def test_the_word_is_remembered_for_the_setups_life(on, tmp_path):
    st, d = {}, str(tmp_path)
    m = targets(at=bar(0))
    vf.track("BTCUSDT", m, st, d, 1)
    assert vf.remembered_opened_by(st, "BTCUSDT", m, page(view())) == "FORCED"
    m2 = targets(at=bar(1))
    vf.track("BTCUSDT", m2, st, d, 2)
    assert st["pos"]["BTCUSDT"]["opened_by"] == "FORCED"                         # carried by track
    assert vf.remembered_opened_by(st, "BTCUSDT", m2, None) == "FORCED"          # a page that could not be read
    new = targets(opened="2026-11-26T09:15:00Z", at=bar(2))                      # the next setup starts without a word
    vf.track("BTCUSDT", new, st, d, 3)
    assert "opened_by" not in st["pos"]["BTCUSDT"]
    assert vf.remembered_opened_by(st, "BTCUSDT", new, page(view())) is None     # the page still shows the old one
    assert vf.remembered_opened_by(st, "BTCUSDT", new, page(view(opened="2026-11-26 09:15", by="ENTER"))) == "ENTER"


def test_a_pass_reads_the_page_only_when_the_switch_is_on(passes, tmp_path, monkeypatch):  # noqa: F811
    run, calls, _ = passes
    with open(str(tmp_path / "page.json"), "w", encoding="utf-8") as fh:
        json.dump(page(view()), fh)
    read = []
    real = vf.read_page
    monkeypatch.setattr(vf, "read_page", lambda p: read.append(p) or real(p))
    run([targets(at=bar(0))], ep(bar(0)))
    assert read == [] and "opened_by" not in calls[-1][1]["book"]                # off: not read, not sent
    monkeypatch.setattr(vf, "SEND_OPENED_BY", True)
    run([targets(at=bar(1))], ep(bar(1)))
    assert len(read) == 1 and calls[-1][1]["book"]["opened_by"] == "FORCED"
    os.remove(str(tmp_path / "page.json"))
    run([targets(at=bar(2))], ep(bar(2)))
    assert calls[-1][1]["book"]["opened_by"] == "FORCED"                         # remembered when the page is gone
