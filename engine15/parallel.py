# -*- coding: utf-8 -*-
"""parallel -- the live step's market groups, thinking at the same time. PAPER ONLY.

SWITCH: the environment variable ENGINE15_PARALLEL = how many groups may think at once (the server: 4).
Unset, 0 or 1 = live.step steps one group after another, as it always did, and never comes here.

What a step writes is the same as one group after another, byte for byte, because only the part of a
group's step that touches nothing shared runs beside the others:

  beside the others   each group in a process of its own (live.step_group with a gate): its bars, its live
                      reads, the lean think (the reading cache data/evcache/<group>/ and its refits). These
                      read and write only that group's own files; the cross-market cards read the bars of
                      their own group only. This is nine tenths of a group's time.
  one at a time       from the gate on: decide (the total-risk cap reads every book), shadow books
                      (shadow_state.json), journal (the day's files), the audit trail, live_state.json, the
                      page. The parent gives the turn to the groups in their fixed order (config
                      "universes") and hands each the state the group before it left, so every shared file
                      sees the same writes in the same order as before. A full prepare (the lean think
                      failed, or a catch-up older than the birth date) also waits for the turn: it holds all
                      history in memory, and two of those at once are too much.
                      (One read in a turn crosses the groups: every group's page carries the CPI shadow
                      book, shadow.py, which reads the crypto bars. Crypto is the FIRST group, so in both
                      kinds of step its bars are updated before any group's turn. Keep it first.)
  the parent          everything else of live.step, unchanged: sources, answers, reports before; strategy
                      books, page, setups, push after. It writes no group file while workers run.

The process mechanism: one plain process per group and two one-way pipes each (multiprocessing.Process and
Pipe(duplex=False): fork and os.pipe on Linux, where the child inherits the loaded modules for nothing;
spawn on Windows). No pool, no queue, no lock, no semaphore, no shared memory, no socket, no temp file: it
needs nothing a sandbox (PrivateDevices, ProtectSystem=strict, PrivateTmp) could withhold. The parent never
waits on one pipe: it reads all of them (connection.wait), so a worker can never block on a full pipe, and it
prints each group's lines only when that group's turn has come, so live.log reads as it always did.

BLAS threads are left exactly as the step has them (inherited): a refit computed with another thread count
may differ in its last bits, and identical results come first. The readings, where the time goes, do not use
BLAS. (To pin them, set OPENBLAS_NUM_THREADS for the whole service, which is a decision of its own.)

One clock for every Yahoo request is a rule of the project (extdata.YF_PAUSE between two requests). Each
worker has its own copy of that clock, so a worker's first request waits two pauses for every non-crypto
market of the groups before it: the requests stay apart as they were (a few seconds, off the critical path).

What does change is WHEN the later groups fetch: every group now reads its bars and its live reads (the candle
forecast) at the start of the step, not after the groups before it have finished (minutes earlier for the
last groups). Given the same inputs the step is the same. So that a bar published a little late is not left
for the next step, a worker whose market should have a new bar by now and has not got it asks again
(wait_for_bars): every BAR_RETRY_S seconds until ENGINE15_PARALLEL_BAR_WAIT seconds (default 75, 0 = never)
after the start of the group phase, then it carries on with what it has, as the step always did. "Should
have by now" is bar_due: the latest 15-minute slot that closed at least fill_delay bars ago (config: 1 for the
futures feeds, which run ten minutes late; 0 for USDJPY and the S&P), inside the market's hours
(extdata.is_open, the feed's hours), and the very next slot of those hours after the last stored bar. Crypto
never waits, a closed market never waits, a market with an older gap never waits. The live reads follow the
bar fetch as before, so a candle forecast published later than that is still missed for the session.

When something goes wrong:
  a group's step raises     logged "<group>: STEP FAILED: ..." as always; the other groups go on; the state is
                            as that step left it (as it is when a group fails in the step one after another).
  a worker dies / is killed the same line, with the exit code. If it held the turn and had already saved
                            live_state.json, that saved state is taken (as after a restart of the engine).
  a worker takes too long   (ENGINE15_PARALLEL_TIMEOUT seconds, default two hours, for its think and again
                            for its turn) it is stopped and logged as failed.
  No failed group is stepped again in the same step: its mark has not moved, so the next step catches up
  every missed session, which is what the engine does after any failed group.
  the machinery itself      (a process cannot be started, a pipe breaks in the parent) one line
                            "parallel step failed (...)", every worker is stopped, and the groups that have
                            not finished are stepped one after another by live.step.
No worker outlives run(): each is joined, or killed and joined, before it returns.
"""
import copy
import hashlib
import multiprocessing
import os
import time
from multiprocessing import connection

import numpy as np
import pandas as pd

from .config import CFG

TIMEOUT_S = 7200.0          # a worker's think, and its turn: far above a first build of the largest cache
BAR_WAIT_S = 75.0           # a due bar is asked for again until this long after the start of the group phase
BAR_RETRY_S = 15.0          # ... this often
_PHASE_MONO = None          # in a worker: time.monotonic() when the step's group phase started
WORKER_INIT = None          # tests only: (function, args) each worker calls before it steps (stand-ins)
_PIPES = []                 # the parent's pipe ends of the running workers (a forked child closes its copies)


def start_method():
    """fork where there is one (Linux: the child shares the parent's loaded modules), else spawn (Windows).
    ENGINE15_PARALLEL_START overrides (tests)."""
    want = os.environ.get("ENGINE15_PARALLEL_START", "").strip()
    have = multiprocessing.get_all_start_methods()
    if want in have:
        return want
    return "fork" if "fork" in have else "spawn"


def timeout_s():
    try:
        v = float(os.environ.get("ENGINE15_PARALLEL_TIMEOUT", "") or TIMEOUT_S)
        return v if v > 0 else TIMEOUT_S
    except ValueError:
        return TIMEOUT_S


def bar_wait_s():
    """ENGINE15_PARALLEL_BAR_WAIT: seconds after the start of the group phase until which a due bar is asked
    for again (0 = never)."""
    try:
        v = float(os.environ.get("ENGINE15_PARALLEL_BAR_WAIT", "") or BAR_WAIT_S)
        return v if v >= 0 else BAR_WAIT_S
    except ValueError:
        return BAR_WAIT_S


# --------------------------------------------------------------------------------------------
# a bar that is due and not published yet (workers only)
# --------------------------------------------------------------------------------------------
def bar_due(asset, last_open, now_s):
    """The open time (epoch seconds) of the bar this market should have by now and has not, or None.
    The latest 15-minute slot that closed at least fill_delay bars ago (config: the futures feeds run about
    ten minutes late, so their newest bar is one behind) is due when the market traded in it
    (extdata.is_open, the feed's hours) and it is the very next slot of the market's hours after the last
    stored bar. None for crypto (not a Yahoo market), a closed market, a market that already has it, and a
    market with an older gap as well (an outage, a holiday the calendar does not know: not this step's bar)."""
    from . import extdata
    if asset not in extdata.MARKETS:
        return None
    bar = CFG["bar_ms"] // 1000
    late = bar * (1 + int(CFG.get("fill_delay", {}).get(asset, 0)))
    last_s = int(pd.Timestamp(last_open).timestamp())
    s = ((int(now_s) - late) // bar) * bar
    if s <= last_s or (s - last_s) // bar > 1000 or not extdata.is_open(asset, s * 1000, feed=True):
        return None
    between = pd.to_datetime(np.arange(last_s + bar, s, bar, dtype="int64"), unit="s", utc=True)
    if len(between) and extdata.open_mask(asset, between, feed=True).any():
        return None
    return s


def wait_for_bars(g, assets, bars, update, log=print):
    """After a worker's bar fetch (live.step_group): while a market of the group lacks the bar that is due
    (bar_due), fetch it again (`update`, the same function, so the same Yahoo spacing) every BAR_RETRY_S
    seconds, until bar_wait_s() seconds after the start of the group phase. `bars` is changed in place.
    Says one line, and only if it waited. -> seconds waited (0.0: it did not). Never raises."""
    t0 = time.monotonic()
    slept = False
    try:
        limit = bar_wait_s()
        deadline = (t0 if _PHASE_MONO is None else _PHASE_MONO) + limit

        def lacking():
            now = time.time()
            return [a for a in assets if len(bars[a]) and bar_due(a, bars[a].index[-1], now) is not None]
        todo = lacking() if limit > 0 else []
        while todo:
            left = deadline - time.monotonic()
            if left <= 0:
                break
            time.sleep(min(BAR_RETRY_S, left))
            slept = True
            for a in todo:
                bars[a] = update(a)
            todo = lacking()
            if left <= BAR_RETRY_S:                              # (that was the try at the deadline)
                break
        if slept:
            log("%s: no new bar after %.0fs" % (g, limit) if todo else
                "%s: waited %.0fs for the new bar" % (g, time.monotonic() - t0))
    except Exception as e:
        try:
            log("%s: the wait for the new bar stopped (%r)" % (g, e))
        except Exception:
            pass
    return time.monotonic() - t0 if slept else 0.0


# --------------------------------------------------------------------------------------------
# the worker process
# --------------------------------------------------------------------------------------------
def _worker(g, assets, state, fetch, up, down, init, inherited, phase):
    """One market group's live.step_group. Every line it logs goes up the pipe as it is said; at the gate
    it asks for its turn and waits for the state; its result (or its error) goes up last."""
    for c in inherited or ():                                    # fork: this process's copies of the other
        try:                                                     # workers' pipes (so a dead worker's pipe ends)
            c.close()
        except Exception:
            pass
    if init:
        init[0](*init[1])
    from . import live
    try:                                                         # phase: (when the group phase started, the
        global _PHASE_MONO                                       # non-crypto markets of the groups before this one)
        _PHASE_MONO = time.monotonic() - min(max(time.time() - phase[0], 0.0), 3600.0)
        from . import extdata                                    # the Yahoo clock (see the module doc): this
        extdata._last_request[0] = max(extdata._last_request[0],  # group's first request not before its place
                                       phase[0] + (2 * phase[1] - 1) * extdata.YF_PAUSE)
    except Exception:
        pass
    turn = {}

    def log(*parts):
        up.send(("log", " ".join(str(p) for p in parts)))

    def gate():
        up.send(("ready", None))
        kind, st = down.recv()
        if kind != "go":
            raise RuntimeError("the parallel step gave this group no turn (%r)" % (kind,))
        turn["state"] = st
        return st
    try:
        got = live.step_group(g, assets, state, log=log, fetch=fetch, gate=gate)
        answer = ("done", (None if not got else (got[0], got[1]), turn.get("state")))
    except Exception as e:                                       # the group's step failed: said by the parent
        answer = ("failed", (repr(e), turn.get("state")))
    up.send(answer)
    up.close()


class _Worker:
    def __init__(self, g, assets):
        self.g, self.assets = g, assets
        self.proc = self.up = self.down = None
        self.lines = []                                          # logged, not yet printed
        self.ready = self.granted = self.gone = False            # asked for its turn / was given it / pipe ended
        self.final = None                                        # ("done" | "failed" | "dead", payload)
        self.t_start = self.t_ready = self.t_go = self.t_end = None
        self.deadline = None
        self.disk = None                                         # live_state.json as it was when the turn was given

    def busy_s(self, now):
        """Seconds of its own work: start to end, without the wait for its turn."""
        end = self.t_end if self.t_end is not None else now
        wait = (self.t_go - self.t_ready) if self.t_go is not None and self.t_ready is not None else 0.0
        return max(end - self.t_start - wait, 0.0)


def _start(ctx, g, assets, state, fetch, phase=(0.0, 0)):
    w = _Worker(g, assets)
    up_r, up_w = ctx.Pipe(duplex=False)                          # worker -> parent
    down_r, down_w = ctx.Pipe(duplex=False)                      # parent -> worker
    forked = ctx.get_start_method() == "fork"
    w.proc = ctx.Process(target=_worker, name="mind15-%s" % g, daemon=True,
                         args=(g, assets, state, fetch, up_w, down_r, WORKER_INIT,
                               list(_PIPES) + [up_r, down_w] if forked else None, phase))
    try:
        w.proc.start()
    finally:
        up_w.close()                                             # the parent keeps only its own ends: the pipe ends
        down_r.close()                                           # when the worker does
    w.up, w.down = up_r, down_w
    _PIPES.extend((up_r, down_w))
    w.t_start = time.monotonic()
    w.deadline = w.t_start + timeout_s()
    return w


def _stop(w):
    """Collect a worker that has given its result; stop any other for good and collect it (no process is
    left behind). Never raises."""
    p = w.proc
    try:
        if p is not None and w.final is not None and w.final[0] != "dead":
            p.join(10)                                           # it has answered: it is on its way out
        if p is not None and p.is_alive():
            p.terminate()
            p.join(5)
            if p.is_alive():
                p.kill()
                p.join(5)
        elif p is not None:
            p.join(1)
    except Exception:
        pass
    for c in (w.up, w.down):
        try:
            if c is not None:
                c.close()
        except Exception:
            pass
        if c in _PIPES:
            _PIPES.remove(c)
    w.gone = True


def _read(ws, wait_s):
    """Take whatever the workers have sent. A worker that ended without a result is marked dead."""
    waiting = [w for w in ws if w.final is None and not w.gone]
    if waiting and wait_s > 0:                                   # until a worker says something or ends
        connection.wait([w.up for w in waiting] + [w.proc.sentinel for w in waiting], wait_s)
    alive = dict((w.g, w.proc.is_alive()) for w in waiting)      # asked BEFORE its pipe is read: whatever a worker
    now = time.monotonic()                                       # sent before it ended is then read below
    for w in waiting:
        try:
            while w.final is None and w.up.poll(0):
                kind, payload = w.up.recv()
                if kind == "log":
                    w.lines.append(payload)
                elif kind == "ready":
                    w.ready, w.t_ready = True, now
                elif kind in ("done", "failed"):
                    w.final, w.t_end = (kind, payload), now
        except (EOFError, OSError):                              # the pipe ended: the worker is gone
            alive[w.g] = False
        except Exception as e:                                   # a result that cannot be read
            w.final, w.t_end = ("dead", "its result could not be read (%r)" % (e,)), now
        if w.final is None and not alive.get(w.g):
            try:
                w.proc.join(5)
                code = w.proc.exitcode
            except Exception:
                code = None
            w.final, w.t_end = ("dead", "the worker process died (exit code %s) %s"
                                % (code, "during its turn" if w.granted else "while it waited for its turn"
                                   if w.ready else "while thinking")), now


def _file_mark(path):
    try:
        with open(path, "rb") as fh:
            return hashlib.sha1(fh.read()).hexdigest()
    except OSError:
        return None


def _adopt(state, new):
    if new is not None and new is not state:
        state.clear()
        state.update(new)


# --------------------------------------------------------------------------------------------
# the parent
# --------------------------------------------------------------------------------------------
def _overdue(ws, limit):
    """Stop a worker that has taken too long to think, or for its turn (waiting for a turn is not its time)."""
    now = time.monotonic()
    for w in ws:
        if w.final is None and now > w.deadline and (w.granted or not w.ready):
            _stop(w)
            w.final, w.t_end = ("dead", "the worker took longer than %.0fs %s and was stopped"
                                % (limit, "for its turn" if w.granted else "to think")), now


def _settle(w, state, out, log):
    """A finished worker's lines and result into the step, as the step one after another has them.
    -> (page or None, remark for the timing line)"""
    from . import live
    for line in w.lines:
        log(line)
    w.lines = []
    kind, payload = w.final
    if kind == "dead":
        if w.granted and _file_mark(live.STATE) != w.disk:       # it saved the state before it ended: that counts,
            _adopt(state, live.load_state())                     # as it does after a restart of the engine
        log("%s: STEP FAILED: %r" % (w.g, RuntimeError(payload)))
        return None, "FAILED"
    _adopt(state, payload[1])                                    # the state as its step left it (None: untouched)
    if kind == "failed":
        log("%s: STEP FAILED: %s" % (w.g, payload[0]))
        return None, "FAILED"
    got = payload[0]
    if not got:
        return None, "no new bar"
    out += got[0]
    return got[1], None


def run(groups, state, out, clock=None, log=print, fetch=True, workers=2, finished=None):
    """Step the market groups with up to `workers` of them thinking at once (see the module doc).
    groups: [(group, assets)] in their fixed order. state: live.step's state, changed in place as the step
    one after another changes it. out: the step's journal entries, extended in group order. finished: the
    groups that are done with (stepped, nothing new, or failed and logged) are appended; a group that is
    not in it when run returns is still to be stepped by the caller. -> the page path (or None)."""
    from . import live
    groups = [(g, tuple(a)) for g, a in groups]
    finished = [] if finished is None else finished
    page, ws, by, notes, limit = None, [], {}, [], timeout_s()

    def settle(w):
        nonlocal page
        got, remark = _settle(w, state, out, log)
        page = got or page
        notes.append((w.g, w.busy_s(time.monotonic()), remark))
        finished.append(w.g)
        _stop(w)
    try:
        ctx = multiprocessing.get_context(start_method())
        snap = copy.deepcopy(state)                              # every worker starts from the same state
        pending, cur = list(groups), 0
        crypto, t_base, before, k = set(CFG.get("crypto", CFG["assets"])), time.time(), {}, 0
        for g, assets in groups:                                 # non-crypto markets before each group (Yahoo clock)
            before[g] = k
            k += sum(1 for a in assets if a not in crypto)
        while cur < len(groups):
            thinking = sum(1 for w in ws if w.final is None and not w.ready)
            while pending and thinking < workers:                # in group order; a worker waiting for its turn
                g, assets = pending.pop(0)                       # uses no processor, so the next group may start
                by[g] = _start(ctx, g, assets, snap, fetch, (t_base, before[g]))
                ws.append(by[g])
                thinking += 1
            _read(ws, 1.0)
            _overdue(ws, limit)
            while cur < len(groups) and groups[cur][0] in by:    # the groups' turns, in their fixed order
                w = by[groups[cur][0]]
                if w.final is not None:
                    settle(w)
                    cur += 1
                    continue
                for line in w.lines:                             # its lines, now that every earlier group is done
                    log(line)
                w.lines = []
                if w.ready and not w.granted:                    # its turn: the state as the groups before it left it
                    w.disk = _file_mark(live.STATE)
                    try:
                        w.down.send(("go", state))
                    except OSError as e:                         # it ended while it waited for its turn
                        _stop(w)
                        w.final, w.t_end = ("dead", "the worker could not be given its turn (%r)" % (e,)), time.monotonic()
                        continue
                    w.granted, w.t_go = True, time.monotonic()
                    w.deadline = w.t_go + limit
                break
    except Exception as e:                                       # the machinery itself: the rest one after another
        for w in ws:
            if w.granted and w.g not in finished:                # the group in the middle of its turn finishes it
                try:                                             # (no other worker has touched anything shared)
                    while w.final is None:
                        _read([w], 1.0)
                        _overdue([w], limit)
                    settle(w)
                except Exception:
                    _stop(w)
                    try:
                        if _file_mark(live.STATE) != w.disk:     # stopped during its turn: what it saved counts
                            _adopt(state, live.load_state())
                    except Exception:
                        pass
        log("parallel step failed (%r): the remaining market groups one after another" % (e,))
    finally:
        for w in ws:
            _stop(w)
    try:
        if clock is not None:
            clock.lap("groups", "parallel %d: %s = %.1f of work" % (
                workers, ", ".join("%s %.1f%s" % (g, s, " " + r if r else "") for g, s, r in notes) or "-",
                sum(s for _, s, _ in notes)))
    except Exception:
        pass
    return page
