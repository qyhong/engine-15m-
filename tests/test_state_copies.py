# -*- coding: utf-8 -*-
"""tools/server/state_copies.py: the hourly copies of the engine's memory and the restore. Temp folders, no network."""
import calendar
import importlib.util
import json
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("state_copies", os.path.join(ROOT, "tools", "server", "state_copies.py"))
sc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sc)

T0 = calendar.timegm((2026, 11, 18, 0, 0, 0))                    # 2026-11-18 00:00:00 UTC
FEED = {"pos": {"BTCUSDT": {"side": "LONG", "opened_utc": "2026-11-18T09:00:00Z", "entry": "65000", "t1_taken": False,
                            "eligible": True}, "ETHUSDT": None},
        "intents": {"BTCUSDT.20261117T030000Z.close.futures": {"status": "pending", "made": 1.0, "seq": 1, "body": {}},
                    "BTCUSDT.20261116T030000Z.close.futures": {"status": "sent", "made": 1.0, "seq": 0, "body": {}}},
        "book": {"BTCUSDT": {"content": "h", "as_of": "2026-11-18T10:15:00Z"}}, "seq": 2}
SHADOW = {"version": 1, "groups": {"crypto": {"last_ms": T0 * 1000}},
          "books": {"b_targets": {"BTCUSDT": {"pos": 1, "qty": 0.1, "qty0": 0.1, "entry": 65000.0, "t1_hit": False,
                                              "t_in_ms": (T0 + 9 * 3600) * 1000},
                                  "ETHUSDT": {"pos": 0, "qty": 0.0}}}}


def put(d, name, doc):
    with open(os.path.join(str(d), name), "w", encoding="utf-8") as fh:
        fh.write(doc if isinstance(doc, str) else json.dumps(doc))


def get(d, name):
    with open(os.path.join(str(d), name), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture
def data(tmp_path):
    put(tmp_path, "vault_feed_state.json", FEED)
    put(tmp_path, "shadow_state.json", SHADOW)
    return tmp_path


def test_a_copy_holds_the_files_a_manifest_and_what_they_say(data):
    lines = []
    st = sc.copy(str(data), now=T0 + 8 * 60, log=lines.append)
    assert st == "20261118T000800Z" and sc.copies(str(data)) == [st]
    m = sc.manifest(str(data), st)
    assert sorted(m["files"]) == ["shadow_state.json", "vault_feed_state.json"]
    assert m["skipped"] == {"live_state.json": "not there", "signals_state.json": "not there"}
    holds = m["files"]["vault_feed_state.json"]["holds"]
    assert holds["positions"]["BTCUSDT"] == {"side": "LONG", "opened_utc": "2026-11-18T09:00:00Z", "t1_taken": False,
                                             "exits_will_be_sent": True}
    assert holds["positions"]["ETHUSDT"] is None and holds["exits_waiting"] == ["BTCUSDT.20261117T030000Z.close.futures"]
    book = m["files"]["shadow_state.json"]["holds"]["setups_book"]
    assert book["BTCUSDT"]["side"] == "LONG" and book["BTCUSDT"]["opened_utc"] == "2026-11-18T09:00:00Z"
    assert book["ETHUSDT"] == {"side": "FLAT", "opened_utc": None, "t1_taken": False, "entry": None}
    assert get(data / "state_copies" / st, "vault_feed_state.json") == FEED


def test_a_file_that_is_not_json_is_never_copied(data):
    put(data, "vault_feed_state.json", '{"pos": {"BTCUSDT": ')
    lines = []
    st = sc.copy(str(data), now=T0, log=lines.append)
    m = sc.manifest(str(data), st)
    assert "vault_feed_state.json" not in m["files"] and "not readable JSON" in m["skipped"]["vault_feed_state.json"]
    assert not os.path.exists(os.path.join(str(data), "state_copies", st, "vault_feed_state.json"))
    assert any("NOT copied" in x for x in lines)
    with pytest.raises(ValueError, match="is not in copy"):
        sc.restore(str(data), st, now=T0, log=lines.append, active=lambda: False)
    os.remove(os.path.join(str(data), "shadow_state.json"))
    os.remove(os.path.join(str(data), "vault_feed_state.json"))
    assert sc.copy(str(data), now=T0 + 3600, log=lines.append) is None      # nothing to copy: no empty folder left
    assert sc.copies(str(data)) == [st]


def test_only_the_newest_copies_are_kept_and_nothing_else_is_removed(data):
    os.makedirs(os.path.join(str(data), "state_copies", "keep_me"))
    put(data / "state_copies" / "keep_me", "note.txt", "x")
    for h in range(6):
        sc.copy(str(data), keep=4, now=T0 + h * 3600, log=lambda *_: None)
    assert sc.copies(str(data)) == ["20261118T050000Z", "20261118T040000Z", "20261118T030000Z", "20261118T020000Z"]
    assert os.path.exists(os.path.join(str(data), "state_copies", "keep_me", "note.txt"))
    assert os.path.exists(os.path.join(str(data), "vault_feed_state.json"))


def test_restore_puts_the_feed_memory_back_and_keeps_what_was_in_use(data):
    st = sc.copy(str(data), now=T0, log=lambda *_: None)
    put(data, "vault_feed_state.json", {"pos": {}})               # the memory after a loss: adopted blind
    put(data, "shadow_state.json", {"version": 1, "groups": {}, "books": {}})
    lines = []
    assert sc.restore(str(data), st, now=T0 + 99, log=lines.append, active=lambda: False) == ["vault_feed_state.json"]
    assert get(data, "vault_feed_state.json") == FEED
    assert get(data, "shadow_state.json") == {"version": 1, "groups": {}, "books": {}}      # not asked for: untouched
    assert get(data, "vault_feed_state.json.before-restore-20261118T000139Z") == {"pos": {}}
    assert sc.restore(str(data), st, ["shadow_state.json", "vault_feed_state.json"], now=T0 + 200, log=lines.append,
                      active=lambda: None) == ["shadow_state.json", "vault_feed_state.json"]   # no systemctl (laptop)
    assert get(data, "shadow_state.json") == SHADOW


def test_restore_refuses_while_the_engine_runs_and_on_anything_odd(data):
    st = sc.copy(str(data), now=T0, log=lambda *_: None)
    put(data, "vault_feed_state.json", {"pos": {}})
    for kw, files, msg in ((dict(active=lambda: True), (), "engine service is running"),
                           (dict(active=lambda: False), ("page.json",), "not a state file"),
                           (dict(active=lambda: False), ("../secrets/x",), "not a state file")):
        with pytest.raises(ValueError, match=msg):
            sc.restore(str(data), st, files, log=lambda *_: None, **kw)
    for bad in ("20261118T000001Z", "../x", "", "keep_me"):
        with pytest.raises(ValueError, match="no such copy"):
            sc.restore(str(data), bad, log=lambda *_: None, active=lambda: False)
    put(data / "state_copies" / st, "vault_feed_state.json", {"pos": {"BTCUSDT": {"side": "SHORT"}}})   # tampered
    with pytest.raises(ValueError, match="does not match its manifest"):
        sc.restore(str(data), st, log=lambda *_: None, active=lambda: False)
    assert get(data, "vault_feed_state.json") == {"pos": {}}      # nothing was changed by any refusal
    assert not [f for f in os.listdir(str(data)) if "before-restore" in f]


def test_show_puts_the_copy_beside_what_is_in_use(data):
    st = sc.copy(str(data), now=T0, log=lambda *_: None)
    os.remove(os.path.join(str(data), "vault_feed_state.json"))
    lines = []
    sc.show(str(data), st, log=lines.append)
    text = "\n".join(lines)
    assert "== vault_feed_state.json" in text and "MISSING OR UNREADABLE" in text and "(identical)" in text
    assert "NOT IN THIS COPY (not there)" in text


def test_the_tool_stands_alone():
    with open(os.path.join(ROOT, "tools", "server", "state_copies.py"), encoding="utf-8") as fh:
        src = fh.read()
    assert "import engine15" not in src and "from engine15" not in src
    assert sc.BOOK == "b_targets" and sc.DEFAULT_RESTORE == ("vault_feed_state.json",)
    assert not [w for w in ("getenv", "os.environ", "open(\"/etc", "secrets/") if w in src]
