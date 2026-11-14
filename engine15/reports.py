# -*- coding: utf-8 -*-
"""reports -- the discovery loops that run by themselves (charter L1 and L5).

L1  Surprise mining, daily: the first live step of each UTC day starts
    `research/surprises.py --days 1` in the background (about 10 s, ~200 MB), which writes
    research/out/surprises_1d.{json,md}: the biggest 1h/4h moves of the last day, what the
    readings were before them, and where the engine stood. On Mondays it also runs --days 7.
L5  The owner as a source, weekly: once the Monday 7-day report exists, the engine puts the
    week's biggest surprise to the owner as a question on the audit trail ("what did you see?").
    Answers go through the usual PIN-checked paths and are graded like any reading.

page.json gets a small "surprises" block (export.py calls `page_block()`).
Nothing here trades. A report that fails to run is logged and retried the next day.
"""
import json
import os
import subprocess
import sys
import time

from .config import ROOT

OUT = os.path.join(ROOT, "research", "out")
SCRIPT = os.path.join(ROOT, "research", "surprises.py")


def _read(stem):
    p = os.path.join(OUT, stem + ".json")
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (ValueError, OSError):
        return None


def _spawn(days, log):
    try:
        subprocess.Popen([sys.executable, "-W", "ignore", SCRIPT, "--days", str(days)], cwd=ROOT,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))
        log("reports: surprise mining for the last %d day(s) started in the background" % days)
        return True
    except Exception as e:
        log("reports: could not start surprise mining (%r)" % (e,))
        return False


def daily(state, log=print):
    """Call once per live step (cheap). Starts the day's reports once; posts the weekly question."""
    if not os.path.exists(SCRIPT):
        return
    now = time.gmtime()
    today = time.strftime("%Y-%m-%d", now)
    if state.get("report_day") != today:
        state["report_day"] = today
        _spawn(1, log)
        if now.tm_wday == 0:                                       # Monday: the week as well
            _spawn(7, log)
    week = time.strftime("%G-W%V", now)
    if state.get("review_week") == week:
        return
    rep = _read("surprises_7d")
    if not rep or not str(rep.get("generated_utc", "")).startswith(today) or now.tm_wday != 0:
        return
    q = weekly_question(rep)
    if q:
        from . import owner
        owner.audit("question", session=time.strftime("%Y-%m-%d %H:%M", now), asset=q["asset"], question=q["text"],
                    kind_detail="weekly_review", surprise_start=q["start"])
        log("reports: weekly review question posted (%s)" % q["asset"])
    state["review_week"] = week


def weekly_question(rep):
    """The week's most instructive surprise: the biggest one the engine was on the WRONG side of,
    else the biggest one overall."""
    rows = rep.get("recent_surprises") or []
    if not rows:
        return None
    wrong = [r for r in rows if str(r.get("engine_verdict", "")).lower().startswith("wrong")]
    r = max(wrong or rows, key=lambda x: abs(x.get("move_atr") or 0))
    coin = str(r.get("asset", "")).replace("USDT", "")
    side = r.get("engine_side") or "flat"
    hrs = 4 if r.get("horizon_bars") == 16 else 1
    text = ("Weekly review: the biggest surprise last week was %s %s %+.2f%% in %d hour%s from %s, while I was %s (%s). "
            "What did you see in it that I could not read: a headline, a level, the flow?" % (
                coin, "falling" if r.get("direction") == "DOWN" else "rising", r.get("move_pct") or 0.0, hrs,
                "" if hrs == 1 else "s", r.get("start_utc", "?"), side.lower(), r.get("engine_verdict", "?")))
    return {"asset": r.get("asset"), "start": r.get("start_utc"), "text": text}


PLAYBOOK_MODULES = ("playbook", "playbook2", "playbook3",     # strategy books (docs/PLAYBOOK_INTERFACE.md)
                    "playbook4",                            # the loop's round-2 rules, forward, NOT passed (12 Nov 2026)
                    "playbook5",                            # the RL agent (Phase 4 primary), forward, NOT passed (12 Nov 2026)
                    "playbook6",                            # RL Phase 6 primary + its control, forward, NOT passed (13 Nov 2026)
                    "playbook7")                            # H37 V4 BTC/ETH pair book, forward, NOT passed (13 Nov 2026)
PLAYBOOK_JSON = os.path.join(ROOT, "out", "live", "playbook.json")


def playbooks(log=print):
    """Run every strategy-book module that exists; write out/live/playbook.json for the page."""
    import importlib
    out, rows_all = {}, []
    for name in PLAYBOOK_MODULES:
        try:
            m = importlib.import_module("engine15." + name)
        except ImportError:
            continue
        try:
            rows = m.step(None)
            rows_all += rows
            out[name] = m.page_block(rows)
        except Exception as e:
            log("playbook %s failed: %r" % (name, e))
    if out:
        tmp = PLAYBOOK_JSON + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, default=str)
        os.replace(tmp, PLAYBOOK_JSON)
    return rows_all


SCOREBOARD_JSON = os.path.join(ROOT, "out", "live", "scoreboard.json")
IDEAS_MD = os.path.join(OUT, "ideas_queue.md")
MIN_TRADES = 30


def _stats(pnls):
    """Forward results of one book: count, net, mean per trade and a 90% range for that mean."""
    import math
    n = len(pnls)
    if not n:
        return {"trades": 0, "net_usd": 0.0, "mean_usd": None, "range90_usd": None, "verdict": "no trades yet"}
    mean = sum(pnls) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in pnls) / (n - 1)) if n > 1 else 0.0
    half = 1.645 * sd / math.sqrt(n) if n > 1 else None
    lo, hi = (None, None) if half is None else (mean - half, mean + half)
    if n < MIN_TRADES:
        verdict = "too few trades to judge (%d of %d)" % (n, MIN_TRADES)
    elif lo is not None and lo > 0:
        verdict = "ahead: even the low end of the range is positive"
    elif hi is not None and hi < 0:
        verdict = "behind: even the high end of the range is negative"
    else:
        verdict = "undecided: the range includes zero"
    return {"trades": n, "net_usd": round(sum(pnls), 2), "mean_usd": round(mean, 2),
            "range90_usd": None if lo is None else [round(lo, 2), round(hi, 2)], "verdict": verdict,
            "won_pct": round(100.0 * sum(1 for x in pnls if x > 0) / n, 1)}


def _scoreboard_titles():
    """Book id -> scoreboard title, for the strategy-book modules whose BOOKS give a "scoreboard_title"
    (playbook4's loop books, so that "NOT passed" shows on the scoreboard); the others keep "Strategy: <id>"."""
    import importlib
    out = {}
    for name in PLAYBOOK_MODULES:
        try:
            m = importlib.import_module("engine15." + name)
        except ImportError:
            continue
        for b, f in (getattr(m, "BOOKS", None) or {}).items():
            if isinstance(f, dict) and f.get("scoreboard_title"):
                out[b] = f["scoreboard_title"]
    return out


def scoreboard(playbook_rows=None, log=print):
    """Charter L4: one forward-only scoreboard for every book (the main books, the shadow challengers,
    the strategy books), with a 90% range for the mean result per trade, so that a lucky streak is not
    mistaken for an edge. Only trades closed live count (the main books since 10 Nov, shadows and
    strategy books since their registration). Writes out/live/scoreboard.json."""
    import glob
    import csv
    rows = []
    live_dir = os.path.join(ROOT, "out", "live")

    def pnl_of(path):
        out = []
        try:
            with open(path, encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    try:
                        out.append(float(r.get("pnl_usd") or "nan"))
                    except ValueError:
                        pass
        except OSError:
            pass
        return [x for x in out if x == x]
    main = []
    for p in glob.glob(os.path.join(live_dir, "trades_*.csv")):
        main += pnl_of(p)
    rows.append(dict({"book": "main", "title": "Main books (live)", "kind": "main"}, **_stats(main)))
    shadow = {}
    for p in glob.glob(os.path.join(live_dir, "shadow_trades_*.csv")):
        name = os.path.basename(p)[len("shadow_trades_"):].rsplit("_", 1)[0]
        shadow.setdefault(name, []).extend(pnl_of(p))
    for name, pn in sorted(shadow.items()):
        rows.append(dict({"book": name, "title": "Shadow: " + name, "kind": "shadow"}, **_stats(pn)))
    by_book = {}
    for r in playbook_rows or []:
        if r.get("status") == "CLOSED" and r.get("pnl_usd") is not None:
            by_book.setdefault(r.get("book"), []).append(float(r["pnl_usd"]))
    titles = _scoreboard_titles()
    for b, pn in sorted(by_book.items()):
        rows.append(dict({"book": b, "title": titles.get(b) or "Strategy: " + b, "kind": "strategy"}, **_stats(pn)))
    out = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "min_trades": MIN_TRADES, "rows": rows,
           "note": "Forward results only. A book is judged once it has %d trades: ahead if the low end of its 90%% range "
                   "per trade is above zero, behind if the high end is below zero." % MIN_TRADES}
    tmp = SCOREBOARD_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(out, fh)
    os.replace(tmp, SCOREBOARD_JSON)
    return out


def scoreboard_block():
    if not os.path.exists(SCOREBOARD_JSON):
        return None
    try:
        with open(SCOREBOARD_JSON, encoding="utf-8") as fh:
            return json.load(fh)
    except (ValueError, OSError):
        return None


def idea_queue(log=print):
    """Charter L3: turn the robust precursors of the latest surprise report into a queue of candidate
    hypotheses (research/out/ideas_queue.md) for the owner and the next study. Ideas already named in
    research/HYPOTHESES.md are marked, not repeated. Nothing is registered automatically."""
    rep = _read("surprises_1d") or _read("surprises")
    if not rep:
        return 0
    reg = ""
    try:
        with open(os.path.join(ROOT, "research", "HYPOTHESES.md"), encoding="utf-8") as fh:
            reg = fh.read().lower()
    except OSError:
        pass
    pre = [p for p in (rep.get("precursors") or []) if p.get("robust")]
    pre.sort(key=lambda p: -(p.get("min_lift") or 0))
    lines = ["# Idea queue (charter L3)", "",
             "Written %s from the surprise report of %s. Each line is a reading that came before big 15m moves more often "
             "(or less often) than at ordinary bars, the same way in BTC and ETH and in both halves of history, and passed the "
             "placebo test. They are leads, not rules: to become a hypothesis one needs an exact trade rule, a first-half "
             "choice and a forward verdict (research/HYPOTHESES.md)." % (time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
                                                                       rep.get("generated_utc", "?")), ""]
    seen = set()
    for p in pre:
        key = (p.get("flag"), p.get("more_or_less"))
        if key in seen:
            continue
        seen.add(key)
        known = str(p.get("flag", "")).split("=")[-1].lower() in reg
        bars, _, way = str(p.get("group", "")).partition("_")
        span = {"4": "1-hour", "16": "4-hour"}.get(bars, bars + "-bar")
        lines.append("- %s %s before %s (lift at least %.2f, placebo pass %.0f%%)%s" % (
            p.get("text") or p.get("flag"), p.get("more_or_less"),
            "big %s moves%s" % (span, "" if way in ("", "any") else " " + way),
            p.get("min_lift") or 0, 100 * (p.get("placebo_pass_share") or 0), " [already in the register]" if known else ""))
    with open(IDEAS_MD + ".tmp", "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    os.replace(IDEAS_MD + ".tmp", IDEAS_MD)
    return len(seen)


HSKILL_LIVE = os.path.join(ROOT, "data", "horizon_skill_live.json")
HSKILL_STEM = "horizon_skill"
HORIZON_WORDS = (("1h", "1 hour (4 bars, 0.75 x ATR 1h)"), ("4h", "4 hours (16 bars, 1 x ATR 1h)"),
                 ("24h", "24 hours (the main engine: 96 bars, 1.5 x ATR 1h; S&P 26 bars)"))


def _hskill_live(path=None):
    p = path or HSKILL_LIVE
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (ValueError, OSError):
        return None


def horizon_skill_weekly(force=False, live_path=None, out_dir=None, log=print):
    """Charter M6: once a week (the first step of each ISO week), research/out/horizon_skill.md/.json:
    per market and horizon (1h / 4h / 24h), the direction hit rate and the hit rate of claimed-edge
    calls (|edge| >= 5 points) over the last 7 and 30 days, from the live steps' own grades
    (data/horizon_skill_live.json, kept by engine15/intraday.py). -> True when written."""
    out_dir = out_dir or OUT
    doc = _hskill_live(live_path)
    if not doc or not doc.get("groups"):
        return False
    week = time.strftime("%G-W%V", time.gmtime())
    old = None
    try:
        with open(os.path.join(out_dir, HSKILL_STEM + ".json"), encoding="utf-8") as fh:
            old = json.load(fh)
    except (ValueError, OSError):
        old = None
    if old and old.get("week") == week and not force:
        return False
    res = {"week": week, "generated_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "groups": doc["groups"],
           "note": "Forward grades of the live steps only. Hit rate = direction right on calls graded up or down; "
                   "claimed-edge hit rate = the same on calls with |P(up) - P(down)| >= 5 points. 50% is a coin."}
    L = ["# Skill per horizon (charter M6)", "",
         "Written %s (week %s) from the live steps' own graded calls. Which clock does the engine read best, "
         "market by market? A hit rate is the share of calls graded up or down whose direction was right; the "
         "claimed-edge hit rate counts only calls where the mind said at least a 5-point edge. 50%% is a coin "
         "flip; a few days of calls say little (counts are shown)." % (res["generated_utc"], week), ""]
    for h, words in HORIZON_WORDS:
        L.append("- **%s**: %s" % (h, words))
    L += ["", "| Market | Horizon | 7d hit | 7d edge hit (calls) | 30d hit | 30d edge hit (calls) |", "|---|---|---|---|---|---|"]
    fmt = lambda v: "-" if v is None else "%.1f%%" % v      # noqa: E731
    for g, gd in doc["groups"].items():
        for a, r in gd.get("assets", {}).items():
            for h, _w in HORIZON_WORDS:
                d7, d30 = (r.get(h) or {}).get("d7") or {}, (r.get(h) or {}).get("d30") or {}
                L.append("| %s | %s | %s | %s (%s) | %s | %s (%s) |" % (
                    a, h, fmt(d7.get("hit_pct")), fmt(d7.get("edge_hit_pct")), d7.get("edge_calls", 0),
                    fmt(d30.get("hit_pct")), fmt(d30.get("edge_hit_pct")), d30.get("edge_calls", 0)))
    L += ["", "Paper only. A history read can reject an idea, never prove one; these are forward counts.", ""]
    os.makedirs(out_dir, exist_ok=True)
    for ext, body in ((".json", json.dumps(res, indent=1)), (".md", "\n".join(L))):
        p = os.path.join(out_dir, HSKILL_STEM + ext)
        with open(p + ".tmp", "w", encoding="utf-8") as fh:
            fh.write(body)
        os.replace(p + ".tmp", p)
    log("reports: horizon skill report written (%s)" % week)
    return True


def horizon_skill_block(live_path=None):
    """Compact page.json block: per market, per horizon, [hit %, claimed-edge hit %, claimed-edge calls]
    over the last 7 and 30 days."""
    doc = _hskill_live(live_path)
    if not doc or not doc.get("groups"):
        return None
    mk = {}
    for g, gd in doc["groups"].items():
        for a, r in gd.get("assets", {}).items():
            row = {}
            for h, _w in HORIZON_WORDS:
                for d in ("d7", "d30"):
                    s = (r.get(h) or {}).get(d) or {}
                    row.setdefault(h, {})[d] = [s.get("hit_pct"), s.get("edge_hit_pct"), s.get("edge_calls", 0)]
            mk[a] = row
    return {"updated_utc": doc.get("updated_utc"), "fields": "[hit %, claimed-edge hit %, claimed-edge calls]",
            "markets": mk, "note": "Forward grades per horizon (1h, 4h, the main 24h). 50% is a coin flip."}


def ideas_block(limit=8):
    """The idea queue's leads for page.json (plain lines)."""
    if not os.path.exists(IDEAS_MD):
        return None
    try:
        with open(IDEAS_MD, encoding="utf-8") as fh:
            items = [ln[2:].strip() for ln in fh if ln.startswith("- ")]
    except OSError:
        return None
    return {"items": items[:limit], "count": len(items),
            "note": "Readings that came before big 15m moves more often than chance, in BTC and ETH, in both halves of history. "
                    "Leads for new hypotheses, not trading rules."}


def playbook_block():
    if not os.path.exists(PLAYBOOK_JSON):
        return None
    try:
        with open(PLAYBOOK_JSON, encoding="utf-8") as fh:
            return json.load(fh)
    except (ValueError, OSError):
        return None


def page_block(limit=5):
    """The last day's biggest surprises, small enough for page.json."""
    rep = _read("surprises_1d")
    if not rep:
        return None
    keep = []
    for r in (rep.get("recent_surprises") or [])[:limit]:
        keep.append({"asset": r.get("asset"), "start_utc": r.get("start_utc"), "direction": r.get("direction"),
                     "move_pct": r.get("move_pct"), "move_atr": r.get("move_atr"),
                     "hours": 4 if r.get("horizon_bars") == 16 else 1, "before": r.get("state"),
                     "precursors": r.get("precursors"), "engine": r.get("engine_verdict"),
                     "engine_side": r.get("engine_side")})
    return {"generated_utc": rep.get("generated_utc"), "window": rep.get("window"), "biggest": keep,
            "note": "Leads, not proven edges: the biggest 1h/4h moves of the last day (BTC and ETH) and where the engine stood."}
