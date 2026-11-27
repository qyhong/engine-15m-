# -*- coding: utf-8 -*-
"""trail_preview: the dry run of the trail book (docs/TRAIL_SWITCH_PLAN.md). It writes a file and posts nothing.

    py -3 -m pytest tests/test_trail_preview.py -q
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import setups, trail_preview  # noqa: E402
from engine15 import vault_feed as vf  # noqa: E402

TRAIL = "b_trail_setups"


def page(at, btc, eth, price=(60000.0, 1700.0), edge=(-8.0, 3.0)):
    """A page at the bar close `at` ('YYYY-MM-DD HH:MM') with the two voices' views of BTC and ETH."""
    flat = {"status": "FLAT", "equity": 10000.0, "realized_usd": 0.0, "fees_usd": 0.0, "trades": 0, "wins": 0}
    return {"name": "Mind 15", "generated_utc": at.replace(" ", "T") + ":40Z", "version": "test",
            "markets": {"crypto": ["BTCUSDT", "ETHUSDT"]},
            "assets": {"BTCUSDT": {"short": "BTC", "time": at, "price": price[0], "edge_pts": edge[0],
                                   "market_group": "crypto"},
                       "ETHUSDT": {"short": "ETH", "time": at, "price": price[1], "edge_pts": edge[1],
                                   "market_group": "crypto"}},
            "shadows": {"books": {setups.BOOK: {"assets": {"BTCUSDT": dict(flat), "ETHUSDT": dict(flat)}},
                                  TRAIL: {"assets": {"BTCUSDT": dict(flat, **(btc or {})),
                                                     "ETHUSDT": dict(flat, **(eth or {}))}}},
                        "markets": {"crypto": {"as_of_utc": at}}}}


def short(opened, entry, stop, trailing=False):
    v = {"status": "SHORT", "entry": entry, "stop": stop, "opened_utc": opened, "opened_by": "ENTER", "unrealized_usd": 1.0}
    if trailing:
        v["trailing"] = True
    return v


def read(d):
    with open(os.path.join(str(d), vf.PREVIEW_FILE), encoding="utf-8") as fh:
        return json.load(fh)


def test_the_preview_follows_a_trail_setup_from_its_opening_and_never_posts(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("the preview must never post")

    monkeypatch.setattr(vf, "post", boom)
    d = str(tmp_path)
    # step 1: the trail book already holds a short (opened before the preview began): not shown, as at a real changeover
    line = trail_preview.write(page("2026-11-26 10:00", short("2026-11-26 08:00", 61000.0, 62500.0), None), d)
    doc = read(d)
    assert line.startswith("trail preview: BTCUSDT FLAT, ETHUSDT FLAT")
    assert doc["schema"] == 1 and doc["intents"] == []
    assert doc["books"]["BTCUSDT"]["body"]["book"] == {"symbol": "BTCUSDT", "side": "FLAT", "t1_taken": False,
                                                       "entry_window_open": False, "as_of_utc": "2026-11-26T10:00:00Z",
                                                       "price": "60000"}
    assert doc["state"]["preview_from_utc"] == {"BTCUSDT": "2026-11-26T10:00:00Z", "ETHUSDT": "2026-11-26T10:00:00Z"}
    # step 2: it opens a new short at this close (the early entry): a trail body, window open, the opening Lead
    trail_preview.write(page("2026-11-26 10:15", short("2026-11-26 10:15", 60000.0, 61500.0), None), d)
    b = read(d)["books"]["BTCUSDT"]["body"]["book"]
    assert b == {"symbol": "BTCUSDT", "side": "SHORT", "entry": "60000", "stop": "61500", "price": "60000",
                 "exit_rule": "trail", "trail_active": False, "entry_window_open": True,
                 "opened_utc": "2026-11-26T10:15:00Z", "as_of_utc": "2026-11-26T10:15:00Z", "lead_pts": -8.0,
                 "opened_by": "ENTER"}                           # v5.2.11: how the book opened it
    # step 3: six bars on, the trail has armed and the stop moved: one move_stop; the window has shut
    trail_preview.write(page("2026-11-26 11:45", short("2026-11-26 10:15", 60000.0, 59700.0, trailing=True), None,
                             price=(58400.0, 1700.0)), d)
    doc = read(d)
    b = doc["books"]["BTCUSDT"]["body"]["book"]
    assert (b["stop"], b["trail_active"], b["entry_window_open"], b["lead_pts"]) == ("59700", True, False, -8.0)
    (it,) = doc["intents"]
    assert it["intent_id"] == "BTCUSDT.20261126T101500Z.ms.261145" and it["action"] == "move_stop"
    assert it["stop_price"] == "59700" and it["reference_price"] == "58400" and it["ok"] is True
    # step 4: the setup is gone: a close; the book is FLAT again
    trail_preview.write(page("2026-11-26 12:00", None, None, price=(59750.0, 1700.0)), d)
    doc = read(d)
    assert doc["books"]["BTCUSDT"]["body"]["book"]["side"] == "FLAT"
    assert [x["action"] for x in doc["intents"]] == ["move_stop", "close"]
    assert doc["state"]["preview_from_utc"]["BTCUSDT"] == "2026-11-26T10:00:00Z"         # the pretend changeover stays
    assert not os.path.exists(os.path.join(d, "vault_feed_state.json"))                  # the feed's memory: untouched
    assert not os.path.exists(os.path.join(d, "setups_voice_state.json"))


def test_a_page_without_the_trail_book_writes_nothing(tmp_path):
    p = page("2026-11-26 10:00", None, None)
    del p["shadows"]["books"][TRAIL]
    assert "not written" in trail_preview.write(p, str(tmp_path))
    assert not os.path.exists(os.path.join(str(tmp_path), vf.PREVIEW_FILE))


def test_the_step_hands_over_the_path_of_page_json(tmp_path):
    """live.step holds the PATH of page.json after export.rewrite_merged, not the dict (found on the box, 26 Nov 2026:
    the first deploy wrote no preview). Both are taken."""
    src = tmp_path / "page.json"
    src.write_text(json.dumps(page("2026-11-26 10:15", short("2026-11-26 10:15", 60000.0, 61500.0), None)), encoding="utf-8")
    out = tmp_path / "live"
    out.mkdir()
    line = trail_preview.write(str(src), str(out))
    assert line.startswith("trail preview: BTCUSDT SHORT, ETHUSDT FLAT")      # opened at this very close: shown
    assert read(out)["generated_utc"] == "2026-11-26T10:15:40Z"
