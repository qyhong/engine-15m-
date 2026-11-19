# -*- coding: utf-8 -*-
"""The daily check's report (live.check_entry / write_check_report -> data/check_report.json) and its Telegram card
(telegram_notify.history_check): written once per group, in the groups' order, in the step one after another and in
the parallel step's workers; the card's thresholds; never twice for a group and day; a garbled file.

    py -3 -m pytest tests/test_check_report.py -q

Nothing here reads or writes the project's data/, journal/ or out/; the network is never used.
"""
import json
import multiprocessing
import os
import sys
import time
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import leanprep, live, parallel, telegram_notify as tn  # noqa: E402
from test_engine import make_bars  # noqa: E402

METHODS = [m for m in ("fork", "spawn") if m in multiprocessing.get_all_start_methods()]
GROUPS = [("aaa", ("AAA", "AAB")), ("bbb", ("BBB",)), ("ccc", ("CCC",))]


def _rep(g, checked=True, stopped=None):
    rep = {"rebuilt": False, "rows_written": 3, "checked": checked, "seconds": 12.34,
           "changed_rows": dict((a, 1000 * (k + 1)) for k, a in enumerate(dict(GROUPS).get(g, ("X",))))}
    if stopped:
        rep["check_stopped"] = stopped
    return rep


# =====================================================================================
# the entry and the file
# =====================================================================================
def test_the_entry():
    t = datetime(2026, 11, 19, 0, 3, tzinfo=timezone.utc).timestamp()
    assert live.check_entry(None) is None and live.check_entry({}) is None
    assert live.check_entry({"evcache": {"checked": False, "changed_rows": {"A": 5}}}) is None   # no check today
    assert live.check_entry({"evcache": {"rebuilt": True, "checked": False}}) is None
    e = live.check_entry({"evcache": _rep("aaa")}, now_s=t)
    assert e == {"day": "2026-11-19", "changed_rows": {"AAA": 1000, "AAB": 2000}, "stopped": False, "stop_reason": None,
                 "seconds": 12.3, "at_utc": "2026-11-19T00:03:00Z"}
    e = live.check_entry({"evcache": _rep("bbb", checked=False, stopped="BBB: 2.10 GB to write")}, now_s=t)
    assert e["stopped"] is True and e["stop_reason"] == "BBB: 2.10 GB to write"


def test_the_file_is_written_atomically_and_keeps_other_groups(tmp_path):
    path = str(tmp_path / "check_report.json")
    t = datetime(2026, 11, 19, 0, 3, tzinfo=timezone.utc).timestamp()
    assert live.write_check_report("aaa", None, path=path) is False and not os.path.exists(path)
    assert live.write_check_report("aaa", live.check_entry({"evcache": _rep("aaa")}, t), path=path)
    assert live.write_check_report("bbb", live.check_entry({"evcache": _rep("bbb")}, t), path=path)
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    assert sorted(doc["groups"]) == ["aaa", "bbb"] and doc["groups"]["bbb"]["changed_rows"] == {"BBB": 1000}
    assert not os.path.exists(path + ".tmp")
    with open(path, "w", encoding="utf-8") as fh:                     # garbled: started again
        fh.write("{not json")
    assert live.write_check_report("ccc", live.check_entry({"evcache": _rep("ccc")}, t), path=path)
    with open(path, encoding="utf-8") as fh:
        assert list(json.load(fh)["groups"]) == ["ccc"]
    lines = []                                                        # a folder that is not there: one line, no raise
    assert live.write_check_report("ccc", {"x": 1}, log=lines.append, path=str(tmp_path / "no" / "r.json")) is False
    assert len(lines) == 1 and "could not be written" in lines[0]


# =====================================================================================
# the real live.step_group: written in the guarded part, once per group, in order
# =====================================================================================
def _install(spec):
    """The real step_group with a stand-in think (a lean prep that carries a check report) and the files in the test's
    folder. In the parent and in every worker (parallel.WORKER_INIT). The step fails right after the gate (the stand-in
    prep has no readings), after the report is written: what is tested is the report alone."""
    bars = make_bars(n=300, seed=3)
    live.STATE = spec["state"]
    live.CHECK_REPORT = spec["report"]
    live.data.load = lambda a: bars
    live.livefeeds.load_live = lambda a: None
    os.environ["ENGINE15_LEAN"] = "1"

    def prepare_live(cfg, b, funding, lv, g):
        time.sleep(spec["think"].get(g, 0.05))                        # the first group thinks longest
        times = b[list(b)[0]].index
        if spec.get("short_times"):                                   # "nothing new": the journal already has the last one
            times = times[:-1]
        return {"evcache": _rep(g), "times": times, "lean_lo": 0, "timing": {}, "fits": {}}
    leanprep.prepare_live = prepare_live
    write = live.write_check_report.__wrapped__ if hasattr(live.write_check_report, "__wrapped__") else live.write_check_report

    def recorded(g, entry, log=print, path=None):
        with open(spec["calls"], "a", encoding="utf-8") as fh:        # one line per call, in the order they happen
            fh.write("%s %s\n" % (g, "entry" if entry else "none"))
        return write(g, entry, log=log, path=path)
    recorded.__wrapped__ = write
    live.write_check_report = recorded


def _spec(tmp_path, name, **kw):
    folder = tmp_path / name
    folder.mkdir()
    spec = {"state": str(folder / "live_state.json"), "report": str(folder / "check_report.json"),
            "calls": str(folder / "calls.txt"), "think": {"aaa": 1.5}}
    spec.update(kw)
    with open(spec["state"], "w", encoding="utf-8") as fh:
        json.dump({"books": {}}, fh)
    return spec


def _keep(monkeypatch):
    for name in ("STATE", "CHECK_REPORT", "write_check_report"):
        monkeypatch.setattr(live, name, getattr(live, name))
    monkeypatch.setattr(live.data, "load", live.data.load)
    monkeypatch.setattr(live.livefeeds, "load_live", live.livefeeds.load_live)
    monkeypatch.setattr(leanprep, "prepare_live", leanprep.prepare_live)
    monkeypatch.setenv("ENGINE15_LEAN", "1")


def _result(spec):
    with open(spec["calls"], encoding="utf-8") as fh:
        calls = fh.read().split()
    with open(spec["report"], encoding="utf-8") as fh:
        doc = json.load(fh)
    return calls, doc


def test_written_once_per_group_in_order_one_after_another(monkeypatch, tmp_path):
    _keep(monkeypatch)
    spec = _spec(tmp_path, "seq")
    _install(spec)
    lines = []
    for g, assets in GROUPS:
        with pytest.raises(KeyError):                                 # the stand-in prep ends the step after the gate
            live.step_group(g, assets, {"books": {}}, log=lines.append, fetch=False)
    calls, doc = _result(spec)
    assert calls == ["aaa", "entry", "bbb", "entry", "ccc", "entry"]
    assert doc["groups"]["aaa"]["changed_rows"] == {"AAA": 1000, "AAB": 2000} and sorted(doc["groups"]) == ["aaa", "bbb", "ccc"]


def test_nothing_new_still_writes_in_its_turn(monkeypatch, tmp_path):
    _keep(monkeypatch)
    spec = _spec(tmp_path, "nothing", short_times=True)
    _install(spec)
    turns, lines = [], []

    def gate():
        turns.append("turn")
        return {"books": {}}
    done = int(make_bars(n=300, seed=3).index[-2].timestamp() * 1000)     # the journal has the stand-in's last session
    st = {"books": {}, "last_ms": {"aaa": done}}
    assert live.step_group("aaa", GROUPS[0][1], st, log=lines.append, fetch=False, gate=gate) is None
    calls, doc = _result(spec)
    assert turns == ["turn"] and calls == ["aaa", "entry"] and list(doc["groups"]) == ["aaa"]
    assert any("nothing new" in x for x in lines)


@pytest.mark.parametrize("method", METHODS)
def test_written_once_per_group_in_order_in_the_parallel_step(monkeypatch, tmp_path, method):
    _keep(monkeypatch)
    monkeypatch.setenv("ENGINE15_PARALLEL_START", method)
    spec = _spec(tmp_path, "par_" + method)
    _install(spec)
    monkeypatch.setattr(parallel, "WORKER_INIT", (_install, (spec,)))
    state, out, lines, finished = {"books": {}}, [], [], []
    parallel.run(GROUPS, state, out, log=lines.append, fetch=False, workers=3, finished=finished)
    assert multiprocessing.active_children() == []
    calls, doc = _result(spec)
    assert calls == ["aaa", "entry", "bbb", "entry", "ccc", "entry"]         # aaa thinks longest, still writes first
    assert sorted(doc["groups"]) == ["aaa", "bbb", "ccc"] and finished == ["aaa", "bbb", "ccc"]
    assert [x.split(":")[0] for x in lines if "STEP FAILED" in x] == ["aaa", "bbb", "ccc"]   # (the stand-in prep)


# =====================================================================================
# the Telegram card
# =====================================================================================
NOW = datetime(2026, 11, 19, 0, 20, tzinfo=timezone.utc)


@pytest.fixture
def tg(monkeypatch, tmp_path):
    path = str(tmp_path / "check_report.json")
    monkeypatch.setattr(tn, "CHECK_REPORT", path)
    monkeypatch.setattr(tn, "_CHECK_ERR", [None])
    monkeypatch.delenv("MIND15_CHECK_ALERT_ROWS", raising=False)
    sent = []

    def send(tok, chat, text, reply_to=None):
        sent.append(text)
        return {"ok": True, "result": {"message_id": len(sent)}}
    monkeypatch.setattr(tn, "_send", send)

    def write(groups):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"groups": groups}, fh)
    return path, sent, write


def _e(rows, stopped=False, day="2026-11-19", seconds=41.6):
    return {"day": day, "changed_rows": rows, "stopped": stopped, "stop_reason": "x" if stopped else None, "seconds": seconds}


def test_card_thresholds(tg, monkeypatch):
    path, sent, write = tg
    assert tn.history_card("crypto", _e({"BTCUSDT": 2000, "ETHUSDT": 1999})) is None          # not MORE than 2,000
    card = tn.history_card("crypto", _e({"BTCUSDT": 61204, "ETHUSDT": 69208}))
    assert card == (u"\U0001f9ed <b>Data history changed · crypto</b>: 130,412 old rows revised today "
                    u"(ETH 69,208 · BTC 61,204); the daily check finished in 42s")
    card = tn.history_card("metals", _e({"XAUUSD": 3, "XAGUSD": 0}, stopped=True))           # stopped: always a card
    assert card.endswith(u"3 old rows revised today (Gold 3); the daily check was stopped by its limit and resumes tomorrow")
    monkeypatch.setenv("MIND15_CHECK_ALERT_ROWS", "100")
    assert tn.check_alert_rows() == 100 and tn.history_card("fx", _e({"USDJPY": 101})) is not None
    for bad in ("", "x", "0", "-5"):
        monkeypatch.setenv("MIND15_CHECK_ALERT_ROWS", bad)
        assert tn.check_alert_rows() == 2000


def test_one_card_per_group_and_day_never_twice(tg):
    path, sent, write = tg
    write({"crypto": _e({"BTCUSDT": 61204, "ETHUSDT": 69208}), "fx": _e({"USDJPY": 12}),
           "metals": _e({"XAUUSD": 5}, stopped=True), "energy": _e({"WTI": 9000}, day="2026-11-12")})   # a week old: no
    st = {}
    got = tn.history_check(st, "tok", 1, NOW)
    assert len(got) == 2 == len(sent) and "crypto" in sent[0] and "metals" in sent[1]
    assert sorted(st["history_alerted"]) == ["crypto|2026-11-19", "metals|2026-11-19"]
    assert tn.history_check(st, "tok", 1, NOW) == [] and len(sent) == 2                    # every later check: nothing
    write({"crypto": _e({"BTCUSDT": 70000}, day="2026-11-20")})                                 # the next day: a new card
    later = datetime(2026, 11, 20, 0, 20, tzinfo=timezone.utc)
    assert len(tn.history_check(st, "tok", 1, later)) == 1 and len(sent) == 3
    assert len(tn.history_check(st, "tok", 1, later)) == 0


def test_a_failed_send_is_tried_again(tg, monkeypatch):
    path, sent, write = tg
    write({"crypto": _e({"BTCUSDT": 5000})})
    monkeypatch.setattr(tn, "_send", lambda tok, chat, text, reply_to=None: {"ok": False})
    st = {}
    assert tn.history_check(st, "tok", 1, NOW) == [] and st["history_alerted"] == {}
    monkeypatch.setattr(tn, "_send", lambda tok, chat, text, reply_to=None: {"ok": True})
    assert len(tn.history_check(st, "tok", 1, NOW)) == 1


def test_missing_or_garbled_file(tg, capsys):
    path, sent, write = tg
    st = {}
    assert tn.history_check(st, "tok", 1, NOW) == []                                         # missing
    for raw in ("{not json", "[]", '{"groups": [1, 2]}', '{"groups": {"crypto": "x", "fx": {"day": "soon"}}}',
                '{"groups": {"crypto": {"day": "2026-11-19", "changed_rows": {"BTCUSDT": "many"}, "stopped": "yes"}}}'):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(raw)
        assert tn.history_check(st, "tok", 1, NOW) == [], raw
    with open(path, "wb") as fh:                                                              # too large: not read
        fh.write(b" " * (tn.CHECK_READ_MAX + 10))
    assert tn.history_check(st, "tok", 1, NOW) == [] and sent == []
    assert tn.history_check({"history_alerted": "garbled"}, "tok", 1, NOW) == []
    assert "failed" not in capsys.readouterr().out


def test_check_sends_it_beside_the_other_alerts(tg, monkeypatch):
    path, sent, write = tg
    write({"crypto": _e({"BTCUSDT": 61204, "ETHUSDT": 69208})})
    monkeypatch.setattr(tn, "_call", lambda tok, method, payload, timeout=20: {"ok": True, "result": []})
    monkeypatch.setattr(tn, "_load", lambda p, d=None: None)
    monkeypatch.setattr(tn, "refit_marks", lambda: [0, 0])
    monkeypatch.setattr(tn, "disk_free_gb", lambda path=None: 50.0)
    monkeypatch.setattr(tn, "vault_check", lambda st, tok, chat, now: [])
    monkeypatch.setattr(tn, "signals_check", lambda *a, **k: None)
    monkeypatch.setattr(tn, "early_check", lambda *a, **k: None)
    st = {"chat_id": 7, "summary_day": "2026-11-19"}
    st, ev = tn.check(st, "tok", now=NOW)
    assert sum("Data history changed" in x for x in sent) == 1 and any("Data history changed" in x for x in ev)
    st, ev = tn.check(st, "tok", now=NOW)
    assert sum("Data history changed" in x for x in sent) == 1
