# -*- coding: utf-8 -*-
"""Run live steps inside a THROW-AWAY COPY of the project, one after another or in parallel. PAPER ONLY.

    python tests/parallel_driver.py <root> <plan.json>

Used by tests/test_parallel_step.py (synthetic bars) and by the real-data equivalence run (two groups).
<root> is a temporary folder that holds its own copy of the engine15 package, so every path the engine
derives from its own location (data/, journal/, out/, research/out/) is inside <root>: nothing here can
read or write the real project's state. This script never runs from the real project (it refuses to).

  <root>/engine15/            a copy of the package (make_root)
  <root>/master/<a>_15m.csv   each market's bars, future included
  <root>/data/ ...            the state the steps start from; the steps write here, journal/ and out/
  <root>/plan.json            {"workers": 0 | N, "universes": [[group, [assets]], ...], "learn_days": N | null,
                               "playbooks": [...], "retry_s": seconds between two tries for a late bar,
                               "stages": [{"clock": epoch seconds, "rows": {asset: bars},
                                           "late": {asset: {"rows": bars at first, "after_s": seconds}}}]}
  <root>/run/result.json      per stage: the wall time, the log lines, {file: sha256} of everything written

So that both runs see exactly the same inputs, in the parent and in every worker (parallel.WORKER_INIT):
  * the clock is frozen at the stage's time (time.time, gmtime, localtime, strftime), so every file that
    carries a wall-clock stamp is comparable byte for byte;
  * the network is closed (socket) and no other program can be started (subprocess);
  * the bar update of a stage copies the first `rows` bars of the master file (the "fetch"), the live reads
    are numbers made from the asset and the session, source updates / answers pull / push do nothing;
  * a bar that is published late ("late"): the asset's fetch gives only the first `rows` bars until `after_s`
    real seconds after it was first asked for in this process, the stage's own `rows` from then on.
"""
import hashlib
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
STATE_DIRS = ("data", "journal", "out", "research")       # everything a step may write, compared file by file
_REAL = {"time": time.time, "gmtime": time.gmtime, "localtime": time.localtime, "strftime": time.strftime}


# ------------------------------------------------------------------ building a root (called by the tests)
def make_root(root):
    """An empty project at `root` with its own copy of the engine15 package."""
    os.makedirs(root, exist_ok=True)
    shutil.copytree(os.path.join(PROJECT, "engine15"), os.path.join(root, "engine15"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for d in ("data", "master", "run"):
        os.makedirs(os.path.join(root, d), exist_ok=True)
    return root


def file_hashes(root):
    """{relative path: sha256} of every file under the state folders of a root."""
    out = {}
    for d in STATE_DIRS:
        for base, _, files in os.walk(os.path.join(root, d)):
            for f in files:
                p = os.path.join(base, f)
                with open(p, "rb") as fh:
                    out[os.path.relpath(p, root).replace("\\", "/")] = hashlib.sha256(fh.read()).hexdigest()
    return out


# ------------------------------------------------------------------ the stand-ins (parent and workers)
def _control(root):
    with open(os.path.join(root, "run", "control.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _refuse(what):
    def refused(*a, **k):
        raise AssertionError("the equivalence run tried to %s" % what)
    return refused


def setup(root):
    """Freeze the clock and put the stand-ins in place, in this process. The parent calls it before every
    stage; every worker calls it when it starts (parallel.WORKER_INIT)."""
    root = os.path.abspath(root)
    if root not in sys.path:
        sys.path.insert(0, root)
    ctl = _control(root)
    now = float(ctl["clock"])
    time.time = lambda: now
    time.gmtime = lambda s=None: _REAL["gmtime"](now if s is None else s)
    time.localtime = lambda s=None: _REAL["localtime"](now if s is None else s)
    time.strftime = lambda fmt, t=None: _REAL["strftime"](fmt, _REAL["localtime"](now) if t is None else t)
    import socket
    import subprocess
    import engine15
    here = os.path.normcase(os.path.abspath(os.path.dirname(os.path.dirname(engine15.__file__))))
    assert here == os.path.normcase(root), "engine15 was imported from %s, not from the temporary root" % here
    from engine15 import data, econ, evidence, inbox, live, livefeeds, push, reports
    from engine15.config import DATA_DIR
    assert os.path.normcase(os.path.abspath(DATA_DIR)) == os.path.normcase(os.path.join(root, "data"))
    socket.socket = _refuse("open a socket")
    subprocess.Popen = _refuse("start another program")
    for m in evidence.SOURCES:
        m.update = lambda log=None, **k: None
    econ.update_calendar = lambda *a, **k: None
    econ.update_macro = lambda *a, **k: None
    inbox.pull = lambda log=print, **k: None
    push.push = _refuse("push the page")
    reports.PLAYBOOK_MODULES = tuple(ctl.get("playbooks") or ())
    live.universes = lambda: [(g, tuple(a)) for g, a in ctl["universes"]]
    if ctl.get("learn_days"):
        live.LEARN_DAYS = int(ctl["learn_days"])
    if ctl.get("retry_s"):
        from engine15 import parallel
        parallel.BAR_RETRY_S = float(ctl["retry_s"])

    asked = {}                                                        # asset -> when this process first fetched it

    def update_bars(a):                                               # the stage's "fetch": the master's first rows
        rows, late = int(ctl["rows"][a]), (ctl.get("late") or {}).get(a)
        if late and time.monotonic() - asked.setdefault(a, time.monotonic()) < float(late["after_s"]):
            rows = int(late["rows"])                                  # (not published yet)
        with open(os.path.join(root, "master", "%s_15m.csv" % a.lower()), encoding="utf-8", newline="") as fh:
            lines = fh.readlines()[:1 + rows]
        tmp = data.path_for(a) + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            fh.writelines(lines)
        os.replace(tmp, data.path_for(a))
        return data.load(a)
    live._update_bars = update_bars

    def numbers(a, close_s, cols):
        out = {}
        for c in cols:
            h = int(hashlib.sha256(("%s|%d|%s" % (a, close_s, c)).encode()).hexdigest()[:8], 16)
            out[c] = ((h % 2001) - 1000) / (1e5 if "ret" in c else 1e3)
        return out

    def kronos(a, close_s, path=None):
        return numbers(a, close_s, evidence.LIVE_RAW[:4]), {"15m": {"origin_t": close_s, "fresh": True}}

    def collect(a, close_s):
        quiet = {"error": "a stand-in: nothing was fetched"}
        return numbers(a, close_s, evidence.LIVE_RAW), {"book": quiet, "book_eagle": quiet, "positioning": quiet,
                                                         "kronos": kronos(a, close_s)[1], "news": []}
    livefeeds.kronos, livefeeds.collect = kronos, collect


# ------------------------------------------------------------------ the run
def main(argv):
    root = os.path.abspath(argv[0])
    with open(argv[1], encoding="utf-8") as fh:
        plan = json.load(fh)
    assert os.path.normcase(root) != os.path.normcase(PROJECT) and os.path.isdir(os.path.join(root, "engine15"))
    os.chdir(root)
    sys.path.insert(0, root)
    for k in ("ENGINE15_PUSH", "MIND15_SETUPS_WEB_DIR", "MIND15_INBOX", "MIND15_PULL_KEY", "ENGINE15_EVCHECK",
              "ENGINE15_PARALLEL", "ENGINE15_PARALLEL_TIMEOUT", "ENGINE15_PARALLEL_BAR_WAIT", "ENGINE15_PARALLEL_START"):
        os.environ.pop(k, None)
    os.environ.update(ENGINE15_LEAN="1", ENGINE15_PUSH="0", PYTHONDONTWRITEBYTECODE="1",
                      MIND15_PULL_TOOL=os.path.join(root, "no_pull_tool.py"), ENGINE15_KRONOS=os.path.join(root, "no_kronos"),
                      ENGINE15_ESTATE=os.path.join(root, "no_estate"))
    os.environ.update(plan.get("env") or {})
    if plan.get("workers"):
        os.environ["ENGINE15_PARALLEL"] = str(plan["workers"])
    sys.dont_write_bytecode = True
    result = []
    for k, stage in enumerate(plan["stages"]):
        ctl = dict(clock=stage["clock"], rows=stage["rows"], late=stage.get("late"), universes=plan["universes"],
                   learn_days=plan.get("learn_days"), playbooks=plan.get("playbooks"), retry_s=plan.get("retry_s"))
        with open(os.path.join(root, "run", "control.json"), "w", encoding="utf-8") as fh:
            json.dump(ctl, fh)
        setup(root)
        from engine15 import live, parallel
        parallel.WORKER_INIT = (setup, (root,))
        lines = []

        def log(*a):
            lines.append(" ".join(str(x) for x in a))
            print("[stage %d] %s" % (k, lines[-1]), flush=True)
        t0 = time.perf_counter()
        out = live.step(log=log, fetch=True)
        result.append({"stage": k, "seconds": round(time.perf_counter() - t0, 2), "entries": len(out or []), "lines": lines,
                       "hashes": file_hashes(root) if plan.get("hash_stages") else None})
        with open(os.path.join(root, "run", "result.json"), "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
