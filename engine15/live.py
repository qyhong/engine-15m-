# -*- coding: utf-8 -*-
"""live -- the engine, awake: one step per closed 15-minute session. PAPER ONLY.

    py -3 -m engine15 step        one step now, then exit
    py -3 -m engine15 live        step a little after every 15-minute close, until stopped

One step, in order:
  1. SOURCES   fetch every bar closed since the last step; funding; then the live-only reads
               for the session that just closed (order book, open interest, Kronos, news)
               and keep them forever (data/live_<asset>.csv, data/raw/).
  2. THINK     rebuild the evidence, refit the voices week by week over the last LEARN_DAYS
               (each fit learns from all graded history) with the same code the replay uses,
               re-weigh trust on every graded call, and form the odds.
  3. DECIDE    advance each coin's paper book across the sessions not yet processed
               (the mandate in policy.py), from the state the last step left.
  4. JOURNAL   one entry per coin per session into journal/<day>.jsonl and .md.
  5. PUBLISH   out/live/page.json for the web tab (export.py).
Nothing here places an order anywhere. It reads public market data and writes local files.
"""
import json
import os
import time

import numpy as np
import pandas as pd

from . import backtest, data, econ, export, journal, livefeeds, owner
from .config import CFG, DATA_DIR, OUT_DIR, voting_for

LEARN_DAYS = 240            # odds and trust are rebuilt over this much recent history each step
STATE = os.path.join(DATA_DIR, "live_state.json")
LIVE_OUT = os.path.join(OUT_DIR, "live")


def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as fh:
            return json.load(fh)
    return {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "last_session_ms": None,
            "books": {}, "version": CFG["version"]}


def save_state(state):
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=1)
    os.replace(tmp, STATE)


def open_trade(asset, st, mark, close_time, cfg):
    """The execution details of one coin's book after this session: the running trade, or the
    flat book and what it is waiting for. Dollars are paper dollars."""
    fee, pend = cfg["cost_side"], st.get("pending")
    base = {"equity_realized": round(st["eq"], 2), "realized_usd": round(st["eq"] - backtest.START_EQUITY, 2),
            "fees_paid_usd": round(st.get("fees", 0.0), 2),
            "next_open": None if not pend else "%s -> %s" % (pend[0], {1: "LONG", -1: "SHORT", 0: "FLAT"}[int(pend[1])])}
    if st["pos"] == 0:
        return dict(base, status="FLAT", idle_sessions=st["idle"], idle_max=cfg["idle_max"], equity_marked=round(st["eq"], 2))
    pos, qty, entry, stop = st["pos"], st["qty"], st["entry"], st["stop"]
    unreal = qty * pos * (mark - entry)
    opened = st.get("t_in_ms")
    return dict(base, status="LONG" if pos > 0 else "SHORT", opened_by=st.get("why_in"),
                opened_utc=None if not opened else str(pd.Timestamp(int(opened), unit="ms", tz="UTC"))[:16],
                sessions_held=None if not opened else int(round((close_time.timestamp() * 1000 - opened) / cfg["bar_ms"])),
                quantity=round(qty, 6), entry_price=round(entry, 2), notional_usd=round(qty * entry, 2),
                leverage=round(qty * entry / st["eq"], 2) if st["eq"] else None,
                leverage_cap=CFG.get("max_leverage", {}).get(asset, 1.0),
                stop_price=None if stop is None else round(stop, 2),
                stop_distance_pct=None if stop is None else round(abs(stop - entry) / entry * 100, 2),
                risk_to_stop_usd=None if stop is None else round(qty * abs(stop - entry), 2),
                mark_price=round(mark, 2), unrealized_usd=round(unreal, 2), unrealized_pct=round(pos * (mark - entry) / entry * 100, 3),
                **_target_fields(st, pos, qty, entry, stop),
                entry_fee_usd=round(fee * qty * entry, 2), exit_fee_est_usd=round(fee * qty * mark, 2),
                net_if_closed_now_usd=round(unreal - fee * qty * (entry + mark), 2), equity_marked=round(st["eq"] + unreal, 2))


def _target_fields(st, pos, qty, entry, stop):
    out = {}
    for k in ("target_1", "target_2"):
        t = st.get(k)
        if t is None:
            continue
        out[k + "_price"] = round(t, 5 if t < 100 else 3 if t < 1000 else 2)
        out[k + "_basis"] = st.get(k + "_basis")
        out[k + "_pct"] = round(pos * (t - entry) / entry * 100, 2)
        out[k + "_usd"] = round(qty * pos * (t - entry), 2)
        if stop is not None and stop != entry:
            out[k + "_r"] = round(pos * (t - entry) / abs(entry - stop), 2)
    return out


def _f(row, col):
    v = row.get(col) if hasattr(row, "get") else None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def plan_targets(side, entry, stop, row):
    """Profit targets for a trade, set once at entry from the readings at the decision close.
    Target 1: the Fibonacci 1.272 extension of the 1h (else 4h) leg when that leg runs the trade's
    way and the target is 0.5 to 4 stop-distances away; else a typical day's travel (the median
    24h reach of the "Candle size and realistic targets" card); else 1.5R.
    Target 2: that leg's 1.618 extension when Target 1 came from it; else 2R.
    PLANNED levels shown on the page and graded in post-mortems; the paper book does not yet take
    profit at them (exits are charter task B)."""
    R = abs(entry - stop) if stop is not None else None
    if not R:
        return {}
    t1 = t2 = None
    for tf in ("1h", "4h"):
        d, f1, f2 = _f(row, "fib_%s_dir" % tf), _f(row, "fib_%s_t1_px" % tf), _f(row, "fib_%s_t2_px" % tf)
        if d and int(round(d)) == side and f1 is not None and 0.5 * R <= side * (f1 - entry) <= 4.0 * R:
            t1 = (f1, "Fibonacci 1.272 of the %s leg" % tf)
            if f2 is not None and side * (f2 - f1) > 0:
                t2 = (f2, "Fibonacci 1.618 of the %s leg" % tf)
            break
    if t1 is None:
        reach = _f(row, "reach_24h_med_pct")
        if reach and reach > 0:
            t1 = (entry * (1 + side * reach / 100.0), "a typical day's travel (median 24h reach %.2f%%)" % reach)
        else:
            t1 = (entry + side * 1.5 * R, "1.5 x the stop distance")
    if t2 is None or side * (t2[0] - t1[0]) <= 0:
        t2 = (entry + side * max(2.0 * R, abs(t1[0] - entry) * 1.5), "2 x the stop distance (2R)")
    return {"target_1": float(t1[0]), "target_1_basis": t1[1], "target_2": float(t2[0]), "target_2_basis": t2[1]}


def closed_trades(asset, limit=10):
    path = os.path.join(LIVE_OUT, "trades_%s.csv" % asset)
    if not os.path.exists(path):
        return []
    d = pd.read_csv(path).tail(limit).iloc[::-1]
    return json.loads(d.to_json(orient="records"))


def universes():
    """[(market group, assets)]: markets whose bars share one clock are thought about together."""
    return [(g, tuple(a)) for g, a in CFG.get("universes", (("crypto", CFG["assets"]),))]


def asset_cfg(a, cfg):
    """The asset's own fee: gold, silver, USDJPY and the S&P 500 trade far cheaper than crypto spot."""
    return dict(cfg, cost_side=CFG.get("asset_cost", {}).get(a, cfg["cost_side"]),
                leverage_cap=CFG.get("max_leverage", {}).get(a, 1.0),
                fill_delay_bars=CFG.get("fill_delay", {}).get(a, 0))


def risk_budget(asset, state):
    """USD of stop-risk the total-risk cap leaves for a new entry on `asset`: cap x total equity of all
    main books, minus what the OTHER open books would lose at their stops."""
    cap = CFG.get("risk_cap_pct")
    if not cap:
        return None
    books = state.get("books", {})
    every = [a for _, assets in universes() for a in assets]
    total = sum(float((books.get(a) or {}).get("eq", 10000.0)) for a in every)
    used = 0.0
    for a in every:
        b = books.get(a) or {}
        if a != asset and b.get("pos") and b.get("stop") is not None:
            used += float(b["qty"]) * abs(float(b["entry"]) - float(b["stop"]))
    return cap / 100.0 * total - used


def _update_bars(a):
    if a in CFG.get("crypto", CFG["assets"]):
        df, _ = data.update(a)
        data.update_funding(a)
        return df
    from . import extdata
    df, _ = extdata.update(a, log=lambda *_: None)
    return df


class StepClock:
    """Where a step's time went, for the log (time.perf_counter; nothing else reads it). lap(name)
    books the time since the last lap under `name`. A clock must never stop a step: every method
    keeps its own errors to itself."""

    def __init__(self):
        self.parts, self.notes = {}, {}                            # name -> seconds (first-seen order), name -> remark
        try:
            self.t0 = self.last = time.perf_counter()
        except Exception:
            self.t0 = self.last = None

    def lap(self, name, note=None):
        try:
            now = time.perf_counter()
            self.parts[name] = self.parts.get(name, 0.0) + (now - self.last)
            self.last = now
            if note:
                self.notes[name] = str(note)
        except Exception:
            pass

    def lap_parts(self, parts, rest, notes=None):
        """The time since the last lap, split as `parts` ({name: seconds}, measured by the callee);
        what they do not cover goes to `rest`."""
        try:
            now = time.perf_counter()
            left = now - self.last
            self.last = now
            for k, v in (parts or {}).items():
                self.parts[k] = self.parts.get(k, 0.0) + float(v)
                left -= float(v)
            if left > 0.05 or not parts:
                self.parts[rest] = self.parts.get(rest, 0.0) + max(left, 0.0)
            for k, v in (notes or {}).items():
                if v:
                    self.notes[k] = str(v)
        except Exception:
            pass

    def slowest(self, floor=1.0):
        """"flows 31.0, cryptox 22.1": the parts that took `floor` seconds or more, slowest first."""
        try:
            return ", ".join("%s %.1f" % (k, v) for k, v in sorted(self.parts.items(), key=lambda kv: -kv[1]) if v >= floor)
        except Exception:
            return ""

    def line(self, label):
        """"timing <label>: 12.3s = bars 1.0 | cache 8.2 (96 rows) | ..." (parts under 0.05 s are left out)."""
        try:
            total = time.perf_counter() - self.t0
            bits = []
            for k, v in self.parts.items():
                if v >= 0.05 or k in self.notes:
                    bits.append("%s %.1f%s" % (k, v, " (%s)" % self.notes[k] if k in self.notes else ""))
            other = total - sum(self.parts.values())
            if other >= 0.5:
                bits.append("other %.1f" % other)
            return "timing %s: %.1fs = %s" % (label, total, " | ".join(bits) or "-")
        except Exception as e:
            return "timing %s: not available (%r)" % (label, e)

    def say(self, log, label):
        try:
            log(self.line(label))
        except Exception:
            pass


def _think_notes(prep, key=None):
    """Remarks for the timing line of a lean think: what the evidence store and the refits did
    (key="timing": the seconds leanprep measured instead). Never raises."""
    try:
        if key:
            return dict(prep.get(key) or {})
        rep, fits = prep.get("evcache") or {}, prep.get("fits") or {}
        cache = "rebuilt" if rep.get("rebuilt") else "%d rows" % rep.get("rows_written", 0)
        if rep.get("checked"):
            cache += ", daily check"
        if rep.get("evidence_s") is not None and not rep.get("rebuilt"):
            cache += ", readings %.1f" % rep["evidence_s"]
        return {"cache": cache, "voices": "%d refits" % fits["refits"] if fits.get("refits") else None}
    except Exception:
        return {}


def step(log=print, fetch=True):
    """One step for every market group; a group whose market has no new closed bar (the S&P at
    night, everything but crypto at the weekend) is skipped. One page for all of them."""
    t0 = time.time()
    tm = StepClock()                                               # where the time went: one "timing" line per group
    if fetch:                                                      # that stepped and one for the whole step
        from .evidence import SOURCES
        src = StepClock()                                          # each source module's own seconds
        for m in SOURCES:                                          # cards 11 to 20 keep their own files fresh
            try:
                m.update(log=lambda *_: None)
            except Exception as err:
                log("source %s did not update: %r" % (m.__name__, err))
            src.lap(str(getattr(m, "__name__", m)).rsplit(".", 1)[-1])
        tm.lap("sources", src.slowest())
        econ.update_calendar()
        if time.gmtime().tm_min < 15:                              # the macro tape is daily: once an hour is plenty
            econ.update_macro()
        tm.lap("calendar")
    try:                                                           # answers given on the web page (PIN checked there)
        from . import inbox
        if fetch:
            inbox.pull(log=log)                                    # server -> data/answers_inbox.jsonl (pull tool)
        inbox.read_new(log=log)
    except Exception as e:
        log("web answers could not be read: %r" % (e,))
    tm.lap("answers")
    state = load_state()
    try:                                                           # charter L1/L5: the daily and weekly discovery reports
        from . import reports
        reports.daily(state, log=log)
        save_state(state)
        if state.get("ideas_day") != state.get("report_day"):      # charter L3: the idea queue, once a day
            if reports.idea_queue(log=log):
                state["ideas_day"] = state.get("report_day")
    except Exception as e:
        log("reports: %r" % (e,))
    tm.lap("reports")
    out, page = [], None
    for g, assets in universes():
        try:
            got = step_group(g, assets, state, log=log, fetch=fetch)
        except Exception as e:                                     # one market failing never stops the others
            log("%s: STEP FAILED: %r" % (g, e))
            tm.lap(g, "FAILED")
            continue
        tm.lap(g, None if got else "no new bar")
        if got:
            out += got[0]
            page = got[1]
    try:                                                           # the strategy books run AFTER the groups fetched the new
        from . import reports                                      # bars, so a decision at a close is made on that close
        pb_rows = reports.playbooks(log=log)                       # (before 12 Nov 2026 they ran first, on bars one step old,
        reports.scoreboard(pb_rows, log=log)                       # and were recorded ~16 min late: optimistic fills)
        tm.lap("strategy books")
        if page is not None:
            from . import export
            page = export.rewrite_merged(LIVE_OUT)                 # the page carries the books as they stand now
            tm.lap("page")
    except Exception as e:
        log("strategy books: %r" % (e,))
        tm.lap("strategy books")
    if page is None:
        tm.say(log, "step")
        return out or None
    try:                                                           # setups.json beside the page (setups.py: one call per
        from . import setups                                       # market for the Setups page); it never stops the step,
        log(setups.line(setups.write(page, out_dir=LIVE_OUT, log=log)))    # the page or the push
    except Exception as e:
        log("setups: not written (%r)" % (e,))
    tm.lap("setups")
    from . import push
    if push.enabled():                                             # to the web server, only when switched on
        log("web push: %s" % push.push(page)[1])
        tm.lap("push")
    tm.say(log, "step")
    log("step done in %.0fs: %d entries ; page %s" % (time.time() - t0, len(out), page))
    return out


def step_group(g, assets, state, log=print, fetch=True):
    assets = list(assets)
    tm = StepClock()
    bars, funding, live = {}, {}, {}
    for a in assets:                                               # 1. sources
        bars[a] = _update_bars(a) if fetch else data.load(a)
    tm.lap("bars")
    last_open = min(df.index[-1] for df in bars.values())
    close_s = int(last_open.timestamp()) + CFG["bar_ms"] // 1000
    marks = state.setdefault("last_ms", {})
    done = marks.get(g, state.get("last_session_ms") if g == "crypto" else None)
    if done is not None and int(last_open.timestamp() * 1000) <= done:
        return None                                                # this market has not closed a new bar
    crypto = CFG.get("crypto", CFG["assets"])
    raws = {}
    for a in assets:
        if fetch and time.time() - close_s < 900:                  # live reads belong to the session just closed
            if a in crypto:
                reads, raws[a] = livefeeds.collect(a, close_s)
            else:                                                  # no book, open interest or crypto news there
                reads, payload = livefeeds.kronos(a, close_s)
                raws[a] = {"kronos": payload}
            if reads:
                livefeeds.upsert_live(a, {int(last_open.timestamp()) * 1000: reads})
        funding[a] = data.load_funding(a) if a in crypto else None
        live[a] = livefeeds.load_live(a)
    tm.lap("live reads")
    bars = dict((a, df[df.index <= last_open]) for a, df in bars.items())      # all history: the voices learn from all of it
    cfg = dict(CFG, assets=tuple(assets), birth=str((last_open - pd.Timedelta(days=LEARN_DAYS)).date()),
               voting=voting_for(g))                                # v5.1: the group's own voting cards
    if g in CFG.get("group_horizon", {}):
        cfg["horizon"] = CFG["group_horizon"][g]
    prep = None                                                    # 2. think
    if os.environ.get("ENGINE15_LEAN", "0") == "1":                # the evidence store and cached refits (leanprep.py), opt-in
        try:
            from . import leanprep
            prep = leanprep.prepare_live(cfg, bars, funding, live, g)
        except Exception as e:
            log("%s: lean think failed (%r): the full prepare instead" % (g, e))
            prep = None
            tm.lap("lean think (failed)")
    if prep is None:
        prep = backtest.prepare(cfg=cfg, bars=bars, funding=funding, live=live)
        tm.lap("full prepare")
    else:
        tm.lap_parts(_think_notes(prep, "timing"), "think", _think_notes(prep))
    times = prep["times"]
    n = len(times)
    lo = n - 1 if done is None else int(times.searchsorted(pd.Timestamp(done, unit="ms", tz="UTC"), side="right"))
    if "lean_lo" in prep and lo < prep["lean_lo"]:                 # a catch-up older than the birth date: all of it
        prep = backtest.prepare(cfg=cfg, bars=bars, funding=funding, live=live)
        tm.lap("full prepare")
    if lo >= n:
        log("%s: nothing new: the last closed session (%s) is already in the journal" % (g, times[-1]))
        return None
    books, entries, trades_now = {}, [], {}
    for a in assets:                                               # 3. decide
        ev = prep["ev"][a]
        old = state["books"].get(a) or {}
        acfg = asset_cfg(a, cfg)
        acfg["risk_budget_usd"] = risk_budget(a, state)          # the total-risk cap across all main books
        b = backtest.run_book(prep["px"][a], prep["odds"][a], ev["shock"].values, ev["tide"].values,
                              (cfg["barrier_atr"] * ev["atr1h"]).values, acfg, lo, n, state=old or None,
                              bias=ev["htf_bias"].values, guard=ev["release_soon"].values)
        books[a] = b
        tr = b["trades"]
        closed = tr[tr.why_out != "OPEN"]
        if len(closed):
            os.makedirs(LIVE_OUT, exist_ok=True)
            path = os.path.join(LIVE_OUT, "trades_%s.csv" % a)
            carried = "" if not old.get("t_in_ms") else str(pd.Timestamp(int(old["t_in_ms"]), unit="ms", tz="UTC"))
            rows = closed.assign(time_out=times[closed.i_out.values].astype(str),
                                 time_in=[str(times[i]) if i >= lo else carried for i in closed.i_in.values])
            rows = rows.drop(columns=["i_in", "i_out"])
            if os.path.exists(path):                               # one growing file; older rows keep their columns
                rows = pd.concat([pd.read_csv(path), rows], ignore_index=True)
            rows.to_csv(path, index=False)
        new = b["state"]
        if new["pos"] != 0:                                        # when the running trade was opened
            new["t_in_ms"] = int(times[new["i_in"]].timestamp() * 1000) if new["i_in"] >= lo else old.get("t_in_ms")
            same = old.get("pos") == new["pos"] and old.get("t_in_ms") == new["t_in_ms"] and old.get("target_1") is not None
            if same:                                               # targets are set once, at entry, and kept
                for k in ("target_1", "target_1_basis", "target_2", "target_2_basis"):
                    new[k] = old.get(k)
            else:
                k_dec = max(new["i_in"] - 1, 0) if new["i_in"] >= lo else n - 1   # the decision close (or now, for a carried trade)
                new.update(plan_targets(int(new["pos"]), float(new["entry"]), new.get("stop"), ev.iloc[k_dec]))
        state["books"][a] = new
        trades_now[a] = open_trade(a, new, float(prep["px"][a]["close"][n - 1]), times[n - 1] + pd.Timedelta(minutes=15), acfg)
    tm.lap("decide")
    shadow_view = None                                             # 3b. the challenger shadow books (shadows.py)
    try:                                                           # same odds and readings; never stops the main step
        from . import shadows
        shadow_view = shadows.step(prep, g, assets, n, cfg=cfg, main_books=state["books"], log=log)
    except Exception as e:
        log("%s: shadow books failed: %r" % (g, e))
    tm.lap("shadow books")
    store = backtest.store_from(prep, books, (lo, n))
    for i in range(lo, n):                                         # 4. journal
        for a in assets:
            entries.append(journal.entry(store, a, i, raw=raws.get(a) if i == n - 1 else None,
                                         trade=trades_now[a] if i == n - 1 else None))
    seen = state.setdefault("version_seen", {})                    # a new version is said once in each group's journal
    if entries and seen.get(g) != CFG["version"]:
        from .config import VERSION_NOTE
        for e in entries[-len(assets):]:
            e["version_note"] = "%s (was %s)" % (VERSION_NOTE, seen.get(g) or state.get("version") or "unknown")
        seen[g] = CFG["version"]
    written = journal.save_entries(entries)
    for e in entries[-len(assets):]:                               # the question asked this session goes on the audit trail
        owner.log_question(e)
    marks[g] = int(times[-1].timestamp() * 1000)
    if g == "crypto":
        state["last_session_ms"] = marks[g]
    save_state(state)
    tm.lap("journal")
    page = export.write_page(store, state, entries, out_dir=LIVE_OUT, group=g, shadows=shadow_view)     # 5. publish
    tm.lap("page")
    for e in entries[-len(assets):]:
        log("%s %s  %s" % (e["time"], e["asset"], e["decision"]))
    log("%s: %d sessions journaled -> %s" % (g, n - lo, written[-1] if written else "-"))
    tm.say(log, g)
    return entries, page


def stay_awake(log=print):
    """Ask Windows not to idle-sleep while this loop runs (the same request a video player makes;
    it ends with the process and changes no setting). A closed lid or choosing Sleep still sleeps.
    Why: on the night of 10-11 Nov 2026 the laptop slept from 18:15 to 04:45 UTC and the engine
    missed ten hours of live reads."""
    if os.name != "nt":
        return False
    try:
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ok = bool(ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED))
        log("keep-awake: %s" % ("on (Windows will not idle-sleep while the loop runs)" if ok else "refused by Windows"))
        return ok
    except Exception as e:
        log("keep-awake: not available (%r)" % (e,))
        return False


def loop(log=print, delay_s=75):
    """Step shortly after every 15-minute close. The delay lets the exchange finish the candle
    and the Kronos job publish its forecast for it."""
    stay_awake(log)
    while True:
        try:
            step(log=log)
        except Exception as e:                                      # a failed step is logged, the loop goes on
            log("STEP FAILED: %r" % (e,))
        now = time.time()
        wait = 900 - (now % 900) + delay_s
        log("sleeping %.0fs until the next close" % wait)
        until = now + wait                                          # short naps against the wall clock: when the laptop
        while time.time() < until:                                  # (a paused VM) wakes, one long sleep() resumes where
            time.sleep(max(0.5, min(30.0, until - time.time())))    # it froze (13 Nov 2026: page 50 min late); this
        if time.time() - until > 120:                               # notices within 30 s and steps at once
            log("woke %.0fs late (the laptop slept); catching up" % (time.time() - until))
