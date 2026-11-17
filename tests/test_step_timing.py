# -*- coding: utf-8 -*-
"""The step log says where a step's time went (live.StepClock), and a clock can never stop a step.

    py -3 -m pytest tests/test_step_timing.py -q

Nothing real runs here: every source, fetch, report, book, push and state file of live.step is replaced
by a stand-in, and the network is closed for the test.
"""
import os
import re
import socket
import sys
import time
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import evidence, export, inbox, live, push, reports  # noqa: E402


def test_clock_books_laps_and_parts():
    tm = live.StepClock()
    time.sleep(0.06)
    tm.lap("bars")
    time.sleep(0.12)
    tm.lap_parts({"cache": 0.05, "voices": 0.01}, "think", {"cache": "96 rows", "voices": None})
    tm.lap("decide")                                                  # (too short to be listed)
    time.sleep(0.06)
    tm.lap("journal", "2 entries")
    line = tm.line("crypto")
    assert re.match(r"^timing crypto: \d+\.\ds = bars \d+\.\d \| cache 0\.1 \(96 rows\) \| think \d+\.\d \| journal \d+\.\d \(2 entries\)$", line), line
    assert abs(sum(tm.parts.values()) - (time.perf_counter() - tm.t0)) < 0.05      # the parts add up to the total
    assert "step done in" not in line and "sleeping" not in line and "web push:" not in line


def test_think_notes():
    notes = live._think_notes({"evcache": {"rebuilt": False, "rows_written": 2881, "checked": True, "evidence_s": 38.24},
                               "fits": {"refits": 2, "reused": 32}})
    assert notes == {"cache": "2881 rows, daily check, readings 38.2", "voices": "2 refits"}
    assert live._think_notes({"evcache": {"rebuilt": True, "rows_written": 0}, "fits": {"refits": 0}}) == {"cache": "rebuilt", "voices": None}
    assert live._think_notes(None) == {} and live._think_notes({}) == {"cache": "0 rows", "voices": None}
    assert live._think_notes({"timing": {"cache": 1.5}}, "timing") == {"cache": 1.5}       # the seconds leanprep measured
    assert live._think_notes({}, "timing") == {} and live._think_notes(None, "timing") == {}


def test_a_clock_never_raises(monkeypatch):
    tm = live.StepClock()
    tm.lap_parts({"cache": "not a number"}, "think")                  # nonsense from a callee
    tm.lap_parts(None, "think")
    tm.parts = None                                                   # a clock broken beyond repair
    tm.lap("x")
    tm.lap_parts({"a": 1.0}, "rest")
    assert tm.line("g").startswith("timing g: not available")
    tm.say(lambda *_: 1 / 0, "g")                                     # even a log that fails
    monkeypatch.setattr(live.time, "perf_counter", lambda: 1 / 0)     # even a clock that cannot be read
    tm = live.StepClock()
    tm.lap("x")
    tm.lap_parts({"a": 1.0}, "rest")
    assert tm.line("g").startswith("timing g: not available")


def _stand_ins(monkeypatch, tmp_path, calls):
    """live.step with nothing real behind it. A stand-in that is missing fails the test before step runs."""
    def no_network(*a, **k):
        raise AssertionError("the test tried to open a socket")
    monkeypatch.setattr(socket, "socket", no_network)
    monkeypatch.setattr(live, "STATE", str(tmp_path / "live_state.json"))
    monkeypatch.setattr(live, "LIVE_OUT", str(tmp_path / "live"))

    def source(name, seconds):
        def update(log=print):
            calls.append("source " + name)
            time.sleep(seconds)
        return types.SimpleNamespace(__name__="engine15.sources." + name, update=update)

    def broken(log=print):
        calls.append("source broken")
        raise RuntimeError("no data today")
    monkeypatch.setattr(evidence, "SOURCES", [source("fast", 0.0), source("slowone", 1.05),
                                              types.SimpleNamespace(__name__="engine15.sources.broken", update=broken)])
    monkeypatch.setattr(live.econ, "update_calendar", lambda *a, **k: calls.append("calendar"))
    monkeypatch.setattr(live.econ, "update_macro", lambda *a, **k: calls.append("macro"))
    monkeypatch.setattr(inbox, "pull", lambda log=print, **k: calls.append("pull"))
    monkeypatch.setattr(inbox, "read_new", lambda log=print, **k: calls.append("read_new"))
    monkeypatch.setattr(live, "load_state", lambda: {"books": {}})
    monkeypatch.setattr(live, "save_state", lambda state: calls.append("save_state"))
    monkeypatch.setattr(reports, "daily", lambda state, log=print: calls.append("daily"))
    monkeypatch.setattr(reports, "idea_queue", lambda log=print: False)
    monkeypatch.setattr(reports, "playbooks", lambda log=print: calls.append("playbooks") or [])
    monkeypatch.setattr(reports, "scoreboard", lambda rows=None, log=print: calls.append("scoreboard"))
    monkeypatch.setattr(export, "rewrite_merged", lambda out_dir: calls.append("rewrite") or "page.json")
    monkeypatch.setattr(push, "enabled", lambda: True)
    monkeypatch.setattr(push, "push", lambda page: calls.append("push") or (True, "ok (a stand-in, nothing sent)"))
    monkeypatch.setattr(live, "universes", lambda: [("crypto", ("AAA", "BBB")), ("index", ("CCC",)), ("fx", ("DDD",))])

    def step_group(g, assets, state, log=print, fetch=True):
        calls.append("group " + g)
        if g == "index":
            return None                                               # its market has not closed a new bar
        if g == "fx":
            raise RuntimeError("fx is broken today")
        time.sleep(0.07)
        log("%s: 1 sessions journaled -> -" % g)
        return [{"asset": a} for a in assets], "page.json"
    monkeypatch.setattr(live, "step_group", step_group)


def test_step_logs_where_the_time_went_and_keeps_its_lines(monkeypatch, tmp_path):
    calls, lines = [], []
    _stand_ins(monkeypatch, tmp_path, calls)
    out = live.step(log=lines.append, fetch=True)
    assert out == [{"asset": "AAA"}, {"asset": "BBB"}]
    assert [c for c in calls if c.startswith(("group", "push"))] == ["group crypto", "group index", "group fx", "push"]
    # the lines other tools look for are as they were
    assert "source engine15.sources.broken did not update: RuntimeError('no data today')" in lines
    assert "fx: STEP FAILED: RuntimeError('fx is broken today')" in lines
    assert "web push: ok (a stand-in, nothing sent)" in lines
    assert re.match(r"^step done in \d+s: 2 entries ; page page\.json$", lines[-1]), lines[-1]
    # one total line, just before "step done", with the slow source by name and every group
    timing = [x for x in lines if x.startswith("timing ")]
    assert len(timing) == 1 and lines[-2] == timing[0], lines
    t = timing[0]
    assert re.match(r"^timing step: \d+\.\ds = sources 1\.\d \(slowone 1\.\d\) \| ", t), t
    assert "fast" not in t and "broken" not in t                      # sources under a second are not named
    assert re.search(r"\| crypto 0\.\d \| index 0\.0 \(no new bar\) \| fx 0\.0 \(FAILED\)$", t), t
    assert "step done in" not in t and "sleeping" not in t and "web push:" not in t
    total = float(re.match(r"^timing step: (\d+\.\d)s", t).group(1))
    assert 1.1 <= total < 5.0


def test_a_step_with_a_broken_clock_is_the_same_step(monkeypatch, tmp_path):
    calls, lines = [], []
    _stand_ins(monkeypatch, tmp_path, calls)

    class Broken(live.StepClock):
        def __init__(self):
            self.parts = self.notes = None                            # every lap fails inside

        def line(self, label):
            raise RuntimeError("the clock is broken")
    monkeypatch.setattr(live, "StepClock", Broken)
    out = live.step(log=lines.append, fetch=True)
    assert out == [{"asset": "AAA"}, {"asset": "BBB"}]
    assert "web push: ok (a stand-in, nothing sent)" in lines and lines[-1].startswith("step done in ")
    assert not [x for x in lines if x.startswith("timing ")]


def test_no_page_no_push_still_one_timing_line(monkeypatch, tmp_path):
    calls, lines = [], []
    _stand_ins(monkeypatch, tmp_path, calls)
    monkeypatch.setattr(live, "universes", lambda: [("index", ("CCC",))])
    assert live.step(log=lines.append, fetch=False) is None            # nothing stepped: no page, no push, no "step done"
    assert "push" not in calls and "pull" not in calls and not [c for c in calls if c.startswith("source")]
    assert [x.split(":")[0] for x in lines] == ["timing step"]
    assert "index 0.0 (no new bar)" in lines[0] and "sources" not in lines[0]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
