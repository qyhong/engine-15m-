# -*- coding: utf-8 -*-
"""The parallel live step (ENGINE15_PARALLEL, engine15/parallel.py) is the step one group after another:
the same files byte for byte, the same lines in the same order, and a worker that raises, dies or hangs
costs only its own group.

    py -3 -m pytest tests/test_parallel_step.py -q

Two kinds of test, on every process start method this machine has (Windows: spawn; Linux: fork and spawn):
  * the real step on synthetic bars, inside throw-away copies of the project (tests/parallel_driver.py):
    one copy stepped one group after another, one in parallel, every file they wrote compared by sha256;
  * live.step with a stand-in for step_group (as tests/test_step_timing.py does), run in real worker
    processes: the order of state, entries and log lines, a worker that raises, one that dies (os._exit),
    one that hangs, the machinery failing, and the switch left off.
Nothing here reads or writes the project's data/, journal/ or out/, and the network is closed.
"""
import json
import multiprocessing
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import backtest, evcache, export, extdata, inbox, leanprep, live, parallel, push, reports, setups  # noqa: E402
import parallel_driver as drv  # noqa: E402
from test_engine import make_bars  # noqa: E402

METHODS = [m for m in ("fork", "spawn") if m in multiprocessing.get_all_start_methods()]


# =====================================================================================
# 1. the real step, synthetic bars: every file the same
# =====================================================================================
UNIVERSES = [["crypto", ["BTCUSDT", "ETHUSDT"]], ["metals", ["XAUUSD", "XAGUSD"]], ["fx", ["USDJPY"]]]
N0 = 30000                                  # bars before the first step (the regime read needs 210 days)


BAR_WAIT = 10                               # ENGINE15_PARALLEL_BAR_WAIT of the parallel runs, seconds
WAIT_LINE = re.compile(r"^(\w+): (waited \d+s for the new bar|no new bar after \d+s)$")


def _plan(workers, env=None):
    """Five steps. The parallel run differs from the other only in WHEN two bars are published in the fourth:
    USDJPY's and silver's newest bar are not there at the first fetch and arrive a few seconds later."""
    t0 = int(pd.Timestamp("2022-01-01", tz="UTC").timestamp())

    def stage(c, m, f, late=None):                                    # bars of crypto, metals, fx at this step
        return {"clock": t0 + 900 * max(c, m, f) + 100,                # 100 s after the newest bar closed
                "rows": {"BTCUSDT": c, "ETHUSDT": c, "XAUUSD": m, "XAGUSD": m, "USDJPY": f}, "late": late if workers else None}
    late = {"USDJPY": {"rows": N0 + 3, "after_s": 3}, "XAGUSD": {"rows": N0 + 2, "after_s": 4}}
    return {"workers": workers, "universes": UNIVERSES, "learn_days": 40, "playbooks": [], "env": env or {},
            "retry_s": 1.5, "hash_stages": True,
            "stages": [stage(N0, N0, N0),                              # 0 a first build of every cache
                       stage(N0 + 1, N0 + 1, N0),                      # 1 one new bar; USDJPY's is due and never comes
                       stage(N0 + 2, N0 + 1, N0 + 3),                  # 2 the metals' is due and never comes (their feed
                                                                       #   runs a bar late); fx catches up three
                       stage(N0 + 3, N0 + 3, N0 + 4, late),            # 3 two bars arrive a few seconds late (parallel)
                       stage(N0 + 150, N0 + 140, N0 + 130)]}           # 4 a long catch-up into the next UTC day


def _run_root(workers, env=None):
    """One throw-away project, stepped through the plan in a process of its own. -> ({file: sha256}, result)"""
    root = tempfile.mkdtemp(prefix="mind15_par_")
    try:
        drv.make_root(root)
        for k, a in enumerate(a for _, assets in UNIVERSES for a in assets):
            df = make_bars(n=N0 + 200, seed=k + 1)
            df.insert(0, "ts_ms", np.asarray(df.index.as_unit("ms").asi8, dtype="int64"))
            df.to_csv(os.path.join(root, "master", "%s_15m.csv" % a.lower()), index=False)
        plan = os.path.join(root, "plan.json")
        with open(plan, "w", encoding="utf-8") as fh:
            json.dump(_plan(workers, env), fh)
        r = subprocess.run([sys.executable, "-W", "ignore", os.path.join(os.path.dirname(drv.__file__), "parallel_driver.py"),
                            root, plan], capture_output=True, text=True, timeout=1800)
        assert r.returncode == 0, (r.stdout[-3000:], r.stderr[-3000:])
        with open(os.path.join(root, "run", "result.json"), encoding="utf-8") as fh:
            result = json.load(fh)
        with open(os.path.join(root, "data", "live_state.json"), encoding="utf-8") as fh:
            state = json.load(fh)
        return drv.file_hashes(root), result, state
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _plain(lines):
    """Log lines without what differs by design: the timing lines and the seconds in a line."""
    out = []
    for x in lines:
        if x.startswith("timing "):
            continue
        x = re.sub(r"mind15_par_\w+", "ROOT", x)
        out.append(re.sub(r"\d+(\.\d+)?s\b", "Ns", x))
    return out


def test_parallel_step_writes_the_same_files():
    seq, res_seq, state = _run_root(0)
    # the comparison means something: caches, state, journal, pages, a closed trade and an open book are in it
    assert len(seq) > 80 and set(state["last_ms"]) == {"crypto", "metals", "fx"}
    assert len(state["books"]) == 5 and any(b["pos"] != 0 for b in state["books"].values())
    for must in ("data/live_state.json", "data/shadow_state.json", "data/owner_audit.jsonl", "data/live_usdjpy.csv",
                 "data/evcache/crypto/group.json", "data/evcache/crypto/BTCUSDT/f8.bin", "data/evcache/fx/USDJPY/meta.json",
                 "data/intraday_minds_metals.json", "out/live/page.json", "out/live/page_fx.json", "out/live/setups.json",
                 "out/live/scoreboard.json", "journal/2022-11-10.jsonl", "journal/2022-11-10.md"):
        assert must in seq, must
    assert any(f.startswith("data/evcache/crypto/fits/") for f in seq)
    assert any(f.startswith("out/live/shadow_trades_") for f in seq) and any(f.startswith("out/live/trades_") for f in seq)
    assert [r["entries"] for r in res_seq] == [5, 4, 5, 2 + 4 + 1, 2 * 147 + 2 * 137 + 126]
    assert not [x for r in res_seq for x in r["lines"] if "FAILED" in x or "failed" in x or WAIT_LINE.match(x)]
    assert res_seq[-1]["hashes"] == seq
    for method in METHODS:
        par, res_par, _ = _run_root(2, {"ENGINE15_PARALLEL_START": method, "ENGINE15_PARALLEL_BAR_WAIT": str(BAR_WAIT)})
        assert sorted(par) == sorted(seq), (method, sorted(set(par) ^ set(seq)))
        assert [f for f in seq if seq[f] != par[f]] == [], method          # every file, byte for byte
        for a, b in zip(res_seq, res_par):                                 # after every step, and the log reads the same
            assert [f for f in a["hashes"] if a["hashes"][f] != b["hashes"].get(f)] == [] and len(a["hashes"]) == len(b["hashes"]), \
                (method, a["stage"])
            assert _plain(a["lines"]) == _plain([x for x in b["lines"] if not WAIT_LINE.match(x)]), (method, a["stage"])
            t = [x for x in b["lines"] if x.startswith("timing step:")]
            assert len(t) == 1 and re.search(r"groups \d+\.\d \(parallel 2: crypto \d+\.\d", t[0]) and " of work)" in t[0], t
            assert b["lines"][-1].startswith("step done in ") and b["lines"][-2] == t[0]
        waits = [x for r in res_par for x in r["lines"] if x.startswith("timing ") and "wait for turn" in x]
        assert waits and not [x for r in res_seq for x in r["lines"] if "wait for turn" in x or "parallel" in x]
        # the bounded wait for a bar that is due: one line per group that waited, at its turn, and only then
        said = [[WAIT_LINE.match(x).groups() for x in r["lines"] if WAIT_LINE.match(x)] for r in res_par]
        assert said[0] == [] and said[4] == [], said
        assert said[1] == [("fx", "no new bar after %ds" % BAR_WAIT)], said          # it never came: no new bar this step,
        assert "fx" in res_par[1]["lines"][-2] and "no new bar" in res_par[1]["lines"][-2]   # the others unaffected, and
        assert said[2] == [("metals", "no new bar after %ds" % BAR_WAIT)], said      # the next step catches up the same
        assert [g for g, _ in said[3]] == ["metals", "fx"] and all(w.startswith("waited ") for _, w in said[3]), said
        lines3 = res_par[3]["lines"]                                              # (said after the group's other lines began)
        assert lines3.index("metals: %s" % said[3][0][1]) > max(i for i, x in enumerate(lines3) if x.startswith("timing crypto:"))
        for g in ("metals", "fx"):
            t = [x for x in lines3 if x.startswith("timing %s:" % g)]
            assert len(t) == 1 and re.search(r"bar wait \d+\.\d \|", t[0]), t
        assert not [x for r in res_par[:3] + res_par[4:] for x in r["lines"] if x.startswith("timing ") and "bar wait" in x]
        assert res_par[1]["seconds"] >= BAR_WAIT - 1 and res_par[2]["seconds"] >= BAR_WAIT - 1


# =====================================================================================
# 2. live.step with a stand-in group step, in real worker processes
# =====================================================================================
GROUPS = [["aaa", ["AAA", "AAB"]], ["bbb", ["BBB"]], ["ccc", ["CCC"]], ["ddd", ["DDD"]], ["eee", ["EEE"]]]


def _install(spec):
    """The stand-in for live.step_group, and the state file in the test's own folder. In the parent, and in
    every worker before it steps (parallel.WORKER_INIT). What a group does depends on the groups before it
    (the list state["seq"]), as the real step's total-risk cap does."""
    live.STATE = spec["state"]
    live.LIVE_OUT = spec["out"]
    live.universes = lambda: [(g, tuple(a)) for g, a in GROUPS]

    def step_group(g, assets, state, log=print, fetch=True, gate=None):
        how = spec["how"].get(g, "ok")
        time.sleep(spec["think"].get(g, 0.05))                        # (the first group thinks longest)
        log("%s: thinking done" % g)
        if how == "none":
            return None
        if how == "raise_before":
            raise RuntimeError("%s is broken today" % g)
        if how == "die_before":
            os._exit(3)
        if how == "hang":
            time.sleep(600)
        if how == "die_waiting":                                      # (the first group is still thinking then)
            threading.Timer(0.3, lambda: os._exit(5)).start()
        if gate is not None:
            state = gate()
        seq = state.setdefault("seq", [])
        seq.append(g)
        for a in assets:
            state.setdefault("books", {})[a] = {"eq": 10000.0 + len(seq), "after": list(seq)}
        if how == "raise_after":
            raise RuntimeError("%s broke after its decision" % g)
        if how == "hang_after":
            time.sleep(600)
        live.save_state(state)
        if how == "die_after":
            os._exit(4)
        log("%s: 1 sessions journaled -> -" % g)
        if spec.get("yahoo"):                                         # this process's Yahoo clock (extdata.fetch_chart)
            return [{"asset": a, "clock": extdata._last_request[0]} for a in assets], "page.json"
        return [{"asset": a, "n": len(seq)} for a in assets], "page.json"
    live.step_group = step_group


def _step(monkeypatch, tmp_path, how, workers=None, method=None, timeout=None, think=None, yahoo=False):
    """live.step with nothing real behind it. -> (out, lines, the state on disk afterwards)"""
    def no_network(*a, **k):
        raise AssertionError("the test tried to open a socket")
    monkeypatch.setattr(socket, "socket", no_network)                 # (the worker pipes are not sockets)
    for name in ("STATE", "LIVE_OUT", "universes", "step_group"):
        monkeypatch.setattr(live, name, getattr(live, name))          # put back after the test
    monkeypatch.setattr(reports, "daily", lambda state, log=print: None)
    monkeypatch.setattr(reports, "idea_queue", lambda log=print: False)
    monkeypatch.setattr(reports, "playbooks", lambda log=print: [])
    monkeypatch.setattr(reports, "scoreboard", lambda rows=None, log=print: None)
    monkeypatch.setattr(export, "rewrite_merged", lambda out_dir: "page.json")
    monkeypatch.setattr(inbox, "read_new", lambda log=print, **k: None)
    monkeypatch.setattr(setups, "write", lambda page, out_dir=None, log=print: {})
    monkeypatch.setattr(setups, "line", lambda info: "setups: a stand-in")
    monkeypatch.setattr(push, "enabled", lambda: False)
    for k, v in (("ENGINE15_PARALLEL", workers), ("ENGINE15_PARALLEL_START", method), ("ENGINE15_PARALLEL_TIMEOUT", timeout)):
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, str(v))
    folder = tmp_path / ("run%d" % len(list(tmp_path.iterdir())))
    folder.mkdir()
    spec = {"state": str(folder / "live_state.json"), "out": str(folder / "live"), "how": how,
            "think": think or {"aaa": 0.8}, "yahoo": yahoo}
    with open(spec["state"], "w", encoding="utf-8") as fh:
        json.dump({"started_utc": "2026-01-01T00:00:00Z", "books": {}, "version": "test"}, fh)
    _install(spec)
    monkeypatch.setattr(parallel, "WORKER_INIT", (_install, (spec,)))
    lines = []
    out = live.step(log=lines.append, fetch=False)
    assert multiprocessing.active_children() == []                    # no worker outlives the step
    with open(spec["state"], encoding="utf-8") as fh:
        return out, lines, json.load(fh)


@pytest.mark.parametrize("method", METHODS)
def test_order_of_state_entries_and_lines(monkeypatch, tmp_path, method):
    how = {"bbb": "none", "ccc": "raise_after", "eee": "raise_before"}
    out1, lines1, state1 = _step(monkeypatch, tmp_path, how)
    out2, lines2, state2 = _step(monkeypatch, tmp_path, how, workers=3, method=method)
    assert out1 == out2 and [e["asset"] for e in out2] == ["AAA", "AAB", "DDD"]
    assert state1 == state2 and state2["seq"] == ["aaa", "ccc", "ddd"]          # ccc's change stayed, as it does in the
    assert state2["books"]["DDD"] == {"eq": 10003.0, "after": ["aaa", "ccc", "ddd"]}   # step one after another
    assert _plain(lines1) == _plain(lines2) == [
        "aaa: thinking done", "aaa: 1 sessions journaled -> -", "bbb: thinking done", "ccc: thinking done",
        "ccc: STEP FAILED: RuntimeError('ccc broke after its decision')", "ddd: thinking done",
        "ddd: 1 sessions journaled -> -", "eee: thinking done", "eee: STEP FAILED: RuntimeError('eee is broken today')",
        "setups: a stand-in", "step done in Ns: 3 entries ; page page.json"]
    t1, t2 = ([x for x in ls if x.startswith("timing step:")] for ls in (lines1, lines2))
    assert re.search(r"aaa \d\.\d \| bbb 0\.\d \(no new bar\) \| ccc 0\.\d \(FAILED\) \| ddd 0\.\d \| eee 0\.\d \(FAILED\)", t1[0]), t1
    assert re.search(r"groups \d+\.\d \(parallel 3: aaa \d+\.\d, bbb \d+\.\d no new bar, ccc \d+\.\d FAILED, ddd \d+\.\d, "
                     r"eee \d+\.\d FAILED = \d+\.\d of work\)", t2[0]), t2
    assert "groups" not in t1[0] and lines2[-2] == t2[0]


@pytest.mark.parametrize("method", METHODS)
def test_a_worker_that_dies_costs_only_its_group(monkeypatch, tmp_path, method):
    out, lines, state = _step(monkeypatch, tmp_path, {"bbb": "die_before", "ccc": "die_after", "ddd": "die_waiting"},
                              workers=5, method=method, think={"aaa": 3.0})
    assert [e["asset"] for e in out] == ["AAA", "AAB", "EEE"]
    assert "ddd: STEP FAILED: RuntimeError('the worker process died (exit code 5) while it waited for its turn')" in lines
    assert "bbb: STEP FAILED: RuntimeError('the worker process died (exit code 3) while thinking')" in lines
    assert "ccc: STEP FAILED: RuntimeError('the worker process died (exit code 4) during its turn')" in lines
    assert lines.index("bbb: thinking done") < lines.index("bbb: STEP FAILED: RuntimeError('the worker process died "
                                                           "(exit code 3) while thinking')")     # what it said is kept
    # ccc had saved the state before it died: the groups after it went on from that, as after a restart
    assert state["seq"] == ["aaa", "ccc", "eee"] and state["books"]["EEE"]["eq"] == 10003.0
    assert re.search(r"bbb \d+\.\d FAILED, ccc \d+\.\d FAILED, ddd \d+\.\d FAILED, eee \d+\.\d = ",
                     [x for x in lines if x.startswith("timing step:")][0])
    assert lines[-1].startswith("step done in ") and not [x for x in lines if x.startswith("parallel step failed")]


@pytest.mark.parametrize("method", METHODS)
def test_a_worker_that_hangs_is_stopped(monkeypatch, tmp_path, method):
    t0 = time.time()
    out, lines, state = _step(monkeypatch, tmp_path, {"bbb": "hang", "ddd": "hang_after"}, workers=5, method=method, timeout=10)
    assert time.time() - t0 < 90
    assert [e["asset"] for e in out] == ["AAA", "AAB", "CCC", "EEE"]
    assert "bbb: STEP FAILED: RuntimeError('the worker took longer than 10s to think and was stopped')" in lines
    assert "ddd: STEP FAILED: RuntimeError('the worker took longer than 10s for its turn and was stopped')" in lines
    assert state["seq"] == ["aaa", "ccc", "eee"]                      # ddd saved nothing; eee waited far longer than
    assert lines[-1].startswith("step done in ")                      # the limit for its turn and was not stopped


@pytest.mark.parametrize("method", METHODS)
def test_the_machinery_failing_falls_back_to_one_after_another(monkeypatch, tmp_path, method):
    how = {"bbb": "none", "ccc": "raise_after"}
    out1, lines1, state1 = _step(monkeypatch, tmp_path, how)
    fall = "parallel step failed (OSError('no more processes')): the remaining market groups one after another"
    # a. the second worker cannot be started: every group is stepped one after another
    real_start, calls = parallel._start, []

    def start(*a, **k):
        calls.append(1)
        if len(calls) == 2:
            raise OSError("no more processes")
        return real_start(*a, **k)
    monkeypatch.setattr(parallel, "_start", start)
    out2, lines2, state2 = _step(monkeypatch, tmp_path, how, workers=4, method=method)
    assert (out2, state2) == (out1, state1) and lines2.count(fall) == 1 and lines2[0] == fall
    assert _plain(lines2[1:]) == _plain(lines1)
    assert re.search(r"groups \d+\.\d \(parallel 4: - = 0\.0 of work\) \| aaa \d\.\d \| bbb", lines2[-2]), lines2[-2]
    monkeypatch.setattr(parallel, "_start", real_start)
    # b. it breaks after the first group has finished: that group's step is kept (and a group in the middle of
    #    its turn finishes it), the rest are stepped here
    real_read = parallel._read

    def read(ws, wait_s):
        if ws and ws[0].gone:
            raise OSError("no more processes")
        return real_read(ws, wait_s)
    monkeypatch.setattr(parallel, "_read", read)
    out3, lines3, state3 = _step(monkeypatch, tmp_path, how, workers=4, method=method)
    assert (out3, state3) == (out1, state1) and lines3.count(fall) == 1
    assert _plain([x for x in lines3 if x != fall]) == _plain(lines1)
    assert re.search(r"groups \d+\.\d \(parallel 4: aaa \d+\.\d.* of work\).* \| ddd \d\.\d \| eee \d\.\d$", lines3[-2]), lines3[-2]
    monkeypatch.setattr(parallel, "_read", real_read)
    # c. the parallel step cannot even begin
    monkeypatch.setattr(parallel, "run", lambda *a, **k: 1 / 0)
    out4, lines4, state4 = _step(monkeypatch, tmp_path, how, workers=4, method=method)
    assert (out4, state4) == (out1, state1)
    assert lines4[0] == "parallel step failed (ZeroDivisionError('division by zero')): the market groups one after another"
    assert _plain(lines4[1:]) == _plain(lines1)


@pytest.mark.parametrize("method", METHODS)
def test_yahoo_requests_stay_apart(monkeypatch, tmp_path, method):
    """One clock for every Yahoo request in the project: each worker's first request has its own place, two
    pauses for every (non-crypto) market of the groups before it."""
    monkeypatch.setattr(extdata, "_last_request", [0.0])
    out, lines, state = _step(monkeypatch, tmp_path, {}, workers=5, method=method, yahoo=True)
    clock = dict((e["asset"], e["clock"]) for e in out)
    assert list(clock) == ["AAA", "AAB", "BBB", "CCC", "DDD", "EEE"] and abs(clock["AAA"] - time.time()) < 120
    gaps = [round(clock[a] - clock["AAA"], 3) for a in ("BBB", "CCC", "DDD", "EEE")]
    assert gaps == [x * extdata.YF_PAUSE for x in (4, 6, 8, 10)], gaps         # (aaa has two markets)


def test_which_bar_is_due():
    """parallel.bar_due on the markets' real hours (Thursday 12 November 2026, New York = UTC-5)."""
    def due(asset, last, now):
        r = parallel.bar_due(asset, pd.Timestamp(last, tz="UTC"), pd.Timestamp(now, tz="UTC").timestamp())
        return None if r is None else str(pd.Timestamp(r, unit="s"))[5:16]
    # USDJPY and the S&P: the bar that has just closed
    assert due("USDJPY", "2026-11-12 18:00", "2026-11-12 18:31:15") == "11-12 18:15"
    assert due("USDJPY", "2026-11-12 18:15", "2026-11-12 18:31:15") is None            # it has it
    assert due("USDJPY", "2026-11-12 17:30", "2026-11-12 18:31:15") is None            # an older bar is missing too
    assert due("SPX", "2026-11-12 20:30", "2026-11-12 21:01:15") == "11-12 20:45"      # the day's last bar, market now shut
    assert due("SPX", "2026-11-12 20:45", "2026-11-12 21:16:15") is None               # closed
    assert due("SPX", "2026-11-12 20:45", "2026-11-13 14:31:15") is None               # the first bar is still trading
    assert due("SPX", "2026-11-12 20:45", "2026-11-13 14:46:15") == "11-13 14:30"      # the day's first bar
    assert due("SPX", "2026-11-13 20:45", "2026-11-16 14:46:15") == "11-16 14:30"      # across a weekend
    assert due("USDJPY", "2026-11-13 21:30", "2026-11-13 22:01:15") == "11-13 21:45"   # the week's last bar
    assert due("USDJPY", "2026-11-13 21:45", "2026-11-14 10:01:15") is None            # Saturday
    assert due("USDJPY", "2026-11-13 21:45", "2026-11-15 22:16:15") is None            # Yahoo's FX week starts at London
    assert due("USDJPY", "2026-11-13 21:45", "2026-11-16 00:16:15") == "11-16 00:00"   # midnight on Monday
    # gold, silver and oil: the feed runs ten minutes late (config fill_delay 1), so the bar before that one
    assert due("XAUUSD", "2026-11-12 18:00", "2026-11-12 18:31:15") is None            # 18:15 is not expected yet
    assert due("XAUUSD", "2026-11-12 17:45", "2026-11-12 18:31:15") == "11-12 18:00"
    assert due("XAUUSD", "2026-11-12 21:45", "2026-11-12 22:31:15") is None            # the daily break
    assert due("XAUUSD", "2026-11-12 21:45", "2026-11-12 23:16:15") is None            # reopened; its first bar comes late
    assert due("XAUUSD", "2026-11-12 21:45", "2026-11-12 23:31:15") == "11-12 23:00"
    assert due("WTI", "2026-11-12 21:45", "2026-11-12 23:31:15") == "11-12 23:00"
    assert due("BRENT", "2026-11-12 21:45", "2026-11-12 23:31:15") is None             # Brent's break is three hours
    assert due("BTCUSDT", "2026-11-12 18:00", "2026-11-12 18:31:15") is None           # crypto never waits


def test_the_wait_for_a_due_bar(monkeypatch):
    """parallel.wait_for_bars: asks again only while a bar is due, stops at the deadline, says one line and
    only if it waited, and never raises."""
    now = pd.Timestamp("2026-11-12 18:31:15", tz="UTC").timestamp()
    monkeypatch.setattr(parallel.time, "time", lambda: now)
    monkeypatch.setattr(parallel, "BAR_RETRY_S", 0.05)
    monkeypatch.setattr(parallel, "_PHASE_MONO", None)
    full = make_bars(n=200, seed=3, start="2026-11-10 16:30")         # its last bar opens at 18:15
    assert str(full.index[-1])[:16] == "2026-11-12 18:15"

    def run(wait, arrives_at_try, assets=("USDJPY",), have=199, phase_ago=None):
        monkeypatch.setenv("ENGINE15_PARALLEL_BAR_WAIT", str(wait))
        monkeypatch.setattr(parallel, "_PHASE_MONO", None if phase_ago is None else time.monotonic() - phase_ago)
        bars, tries, lines = dict((a, full.iloc[:have]) for a in assets), [], []

        def update(a):
            tries.append(a)
            if arrives_at_try == "raise":
                raise OSError("the disk is full")
            return full if len(tries) >= arrives_at_try else full.iloc[:199]
        t = parallel.wait_for_bars("fx", list(assets), bars, update, log=lines.append)
        return t, len(tries), lines, len(bars[assets[0]])
    t, tries, lines, n = run(5, 3)                                    # the bar comes at the third retry
    assert 0.1 <= t < 3 and tries == 3 and n == 200 and len(lines) == 1 and re.match(r"^fx: waited \d+s for the new bar$", lines[0])
    t, tries, lines, n = run(0.3, 99)                                 # it never comes: the deadline, then carry on
    assert 0.25 <= t < 3 and 2 <= tries <= 8 and n == 199 and lines == ["fx: no new bar after 0s"]
    assert run(5, 1, have=200) == (0.0, 0, [], 200)                   # it has its bar: no wait, no line
    assert run(0, 1) == (0.0, 0, [], 199)                             # switched off
    assert run(5, 1, assets=("BTCUSDT",)) == (0.0, 0, [], 199)        # crypto never waits
    assert run(5, 1, phase_ago=60) == (0.0, 0, [], 199)               # the group phase began 60 s ago: too late to wait
    t, tries, lines, n = run(5, 1, assets=("XAUUSD", "USDJPY"))       # gold's feed is a bar late: only USDJPY is asked again
    assert tries == 1 and re.match(r"^fx: waited \d+s for the new bar$", lines[0])
    t, tries, lines, n = run(5, "raise")                              # a fetch that fails does not fail the group
    assert tries == 1 and n == 199 and lines == ["fx: the wait for the new bar stopped (OSError('the disk is full'))"]
    monkeypatch.setenv("ENGINE15_PARALLEL_BAR_WAIT", "x")
    assert parallel.bar_wait_s() == parallel.BAR_WAIT_S == 75.0
    monkeypatch.delenv("ENGINE15_PARALLEL_BAR_WAIT")
    assert parallel.bar_wait_s() == 75.0


def test_a_full_prepare_waits_for_its_turn(monkeypatch):
    """The real live.step_group: a full prepare (all history in memory) is never run beside the other groups."""
    bars = make_bars(n=400, seed=5)
    calls, lines = [], []

    class Stop(Exception):
        pass

    def no_store(*a, **k):
        raise evcache.StoreError("no store today")

    def prepare(**k):
        calls.append("full prepare")
        raise Stop()

    def gate():
        calls.append("turn")
        return {"books": {}}
    monkeypatch.setenv("ENGINE15_LEAN", "1")
    monkeypatch.setattr(live.data, "load", lambda a: bars)
    monkeypatch.setattr(leanprep, "prepare_live", no_store)
    monkeypatch.setattr(backtest, "prepare", prepare)
    with pytest.raises(Stop):                                         # the lean think failed: the turn first
        live.step_group("zzz", ("ZZZ",), {"books": {}}, log=lines.append, fetch=False, gate=gate)
    assert calls == ["turn", "full prepare"] and lines == ["zzz: lean think failed (StoreError('no store today')): the full prepare instead"]
    del calls[:]
    with pytest.raises(Stop):                                         # no gate: the step as it always was
        live.step_group("zzz", ("ZZZ",), {"books": {}}, log=lines.append, fetch=False)
    assert calls == ["full prepare"]
    del calls[:]
    seen = {"books": {}, "last_ms": {"zzz": int(bars.index[-1].timestamp() * 1000)}}
    assert live.step_group("zzz", ("ZZZ",), seen, log=lines.append, fetch=False, gate=gate) is None and calls == []   # no new bar: no turn


def test_the_switch(monkeypatch, tmp_path):
    for v, n in ((None, 0), ("", 0), ("0", 0), ("1", 0), ("x", 0), ("-3", 0), ("2", 2), (" 4 ", 4)):
        if v is None:
            monkeypatch.delenv("ENGINE15_PARALLEL", raising=False)
        else:
            monkeypatch.setenv("ENGINE15_PARALLEL", v)
        assert live.parallel_workers() == n, v
    # off: the parallel step is never entered and the step and its lines are as they always were
    def never(*a, **k):
        raise AssertionError("the parallel step ran with the switch off")
    monkeypatch.setattr(parallel, "run", never)
    monkeypatch.setattr(parallel, "_start", never)
    for v in (None, "0", "1"):
        out, lines, state = _step(monkeypatch, tmp_path, {"bbb": "none", "eee": "raise_before"}, workers=v)
        assert [e["asset"] for e in out] == ["AAA", "AAB", "CCC", "DDD"] and state["seq"] == ["aaa", "ccc", "ddd"]
        t = [x for x in lines if x.startswith("timing ")]
        assert len(t) == 1 and re.search(r"^timing step: \d+\.\ds = .*aaa \d\.\d \| bbb 0\.\d \(no new bar\) \| ccc 0\.\d \| "
                                        r"ddd 0\.\d \| eee 0\.\d \(FAILED\)$", t[0]), t
        assert "eee: STEP FAILED: RuntimeError('eee is broken today')" in lines and "parallel" not in " ".join(lines)
    assert parallel.start_method() in METHODS and parallel.timeout_s() == parallel.TIMEOUT_S


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
