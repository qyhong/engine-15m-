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
                    "playbook7",                            # H37 V4 BTC/ETH pair book, forward, NOT passed (13 Nov 2026)
                    "playbook8",                            # the momentum yardstick for playbook6 (not a hypothesis; 22 Nov 2026)
                    "playbook9")                            # H115: H107 capitulation long, rules A/B, forward, NOT passed (24 Nov 2026)
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
SHADOW_TITLES = {                                               # shadow books that carry their own label on the scoreboard
    "b_learn": "Shadow: b_learn (exit learner, H109; paper only, NOT passed)",   # = learn_book.SCOREBOARD_TITLE
}


def per_entry(rows):
    """Results per TRADE from closed-trade rows [(key, pnl_usd)]: rows that share a key are one trade closed in parts
    (think15-v5.2.6: the S&P 500's main book books the half closed at Target 1 and the rest as two rows with the same
    entry time and side) and count once, with their results added. A row without a key (None / "") counts by itself."""
    out, at = [], {}
    for key, pnl in rows:
        if key in (None, "") or key not in at:
            if key not in (None, ""):
                at[key] = len(out)
            out.append(float(pnl))
        else:
            out[at[key]] += float(pnl)
    return out


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


# Student's t, two-sided 90% (0.95 quantile), by degrees of freedom: the by-day read has few days, and 1.645 (the
# bell-curve figure the per-trade range uses) would make a range from 5 or 10 days look tighter than it is.
T90 = {1: 6.314, 2: 2.920, 3: 2.353, 4: 2.132, 5: 2.015, 6: 1.943, 7: 1.895, 8: 1.860, 9: 1.833, 10: 1.812, 11: 1.796,
       12: 1.782, 13: 1.771, 14: 1.761, 15: 1.753, 16: 1.746, 17: 1.740, 18: 1.734, 19: 1.729, 20: 1.725, 21: 1.721,
       22: 1.717, 23: 1.714, 24: 1.711, 25: 1.708, 26: 1.706, 27: 1.703, 28: 1.701, 29: 1.699, 30: 1.697, 40: 1.684,
       60: 1.671, 120: 1.658}
BY_DAY_NOTE = ("By day: trades that close on the same UTC day are not separate bets (BTC and ETH, gold and silver, WTI "
               "and Brent open and close together, and one market move can stop several books at once). This second "
               "range for the same mean per trade lets results move together within a day, so it is wider when they "
               "do. It is shown beside the verdict; it does not replace it.")


def _t90(df):
    """The 0.95 quantile of Student's t for `df` degrees of freedom (the next smaller tabled value, so never too tight)."""
    if df < 1:
        return None
    best = None
    for k in sorted(T90):
        if k <= df:
            best = T90[k]
    return 1.645 if df > 120 else best


def per_entry_days(rows):
    """per_entry for rows [(key, pnl_usd, close day)] -> [(pnl_usd, day)]: a trade closed in parts counts once, on the
    day its last part closed. The results, and their order, are exactly per_entry's."""
    out, at = [], {}
    for key, pnl, day in rows:
        if key in (None, "") or key not in at:
            if key not in (None, ""):
                at[key] = len(out)
            out.append([float(pnl), day])
        else:
            i = at[key]
            out[i][0] += float(pnl)
            if day and (not out[i][1] or day > out[i][1]):
                out[i][1] = day
    return [(p, d) for p, d in out]


def _day(v):
    """The UTC day 'YYYY-MM-DD' of a close time as the books write it ('2026-11-23 13:45', '...+00:00', '...T13:45:00Z'),
    or None."""
    s = str(v or "").strip()[:10]
    return s if len(s) == 10 and s[4] == "-" and s[7] == "-" and s.replace("-", "").isdigit() else None


def by_day(pairs):
    """The by-day read of one book (owner, 24 Nov 2026, after the live audit: "judge by day or by pair of markets, not by
    trade"), from [(pnl_usd, close day)]. Same mean per trade as _stats; the 90% range is built from the days' sums of
    (result - mean) instead of from single trades (a cluster-robust standard error, days as clusters, Student's t with
    days - 1 degrees of freedom). A trade without a readable day is a day of its own. -> the three keys added to a row.
    The registered verdict (_stats, research/VERDICT_RULES.md) is NOT changed by this."""
    import math
    n = len(pairs)
    if not n:
        return {"days": 0, "range90_by_day_usd": None, "verdict_by_day": "no trades yet"}
    mean = sum(p for p, _d in pairs) / n
    sums = {}
    for i, (p, d) in enumerate(pairs):
        k = d if d else ("?", i)
        sums[k] = sums.get(k, 0.0) + (p - mean)
    g = len(sums)
    rng = None
    if g > 1:
        se = math.sqrt(g / (g - 1.0) * sum(v * v for v in sums.values())) / n
        half = _t90(g - 1) * se
        rng = [round(mean - half, 2), round(mean + half, 2)]
    if n < MIN_TRADES:
        verdict = "too few trades to judge (%d of %d)" % (n, MIN_TRADES)
    elif rng is None:
        verdict = "too few days to judge (%d of 2)" % g
    elif rng[0] > 0:
        verdict = "ahead: even the low end of the range is positive"
    elif rng[1] < 0:
        verdict = "behind: even the high end of the range is negative"
    else:
        verdict = "undecided: the range includes zero"
    return {"days": g, "range90_by_day_usd": rng, "verdict_by_day": verdict}


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
                        v = float(r.get("pnl_usd") or "nan")
                    except ValueError:
                        continue
                    if v == v:                                     # a trade closed in parts counts once (per_entry)
                        t_in = (r.get("time_in") or "").strip()
                        out.append(((t_in, r.get("side")) if t_in else None, v, _day(r.get("time_out"))))
        except OSError:
            pass
        return per_entry_days(out)                                 # [(pnl_usd, close day)]

    def row(pairs):                                                # the registered per-trade read, then the by-day read
        return dict(_stats([p for p, _d in pairs]), **by_day(pairs))
    main = []
    for p in glob.glob(os.path.join(live_dir, "trades_*.csv")):
        main += pnl_of(p)
    rows.append(dict({"book": "main", "title": "Main books (live)", "kind": "main"}, **row(main)))
    learner = None
    try:                                                           # the exit learner b_learn (learn_book.py, H109; owner,
        from . import learn_book                                   # 24 Nov 2026): recomputed from six shadow books' own
        learner = learn_book.step(live_dir=live_dir, log=log)      # records, then read below like any shadow book. Paper
    except Exception as e:                                         # only, NOT passed; it never stops the scoreboard
        log("exit learner: %r" % (e,))
    shadow = {}
    for p in glob.glob(os.path.join(live_dir, "shadow_trades_*.csv")):
        name = os.path.basename(p)[len("shadow_trades_"):].rsplit("_", 1)[0]
        shadow.setdefault(name, []).extend(pnl_of(p))
    mind_rows = {}                                                 # shadow minds (H108, regime_trust.py): the row says
    try:                                                           # "NOT passed, paper only" and carries the registered
        from . import regime_trust                                 # comparison with the fresh main copy. Read only; a
        extra = regime_trust.scoreboard_extra(len(shadow.get(regime_trust.NAME, [])))   # failure never stops the scoreboard
        if extra is not None:
            shadow.setdefault(regime_trust.NAME, [])               # shown from its first live bar, before any trade
            mind_rows[regime_trust.NAME] = extra
    except Exception as e:
        log("regime trust mind: %r" % (e,))
    try:                                                           # b_rebound (rebound_book.py, H117; owner, 24 Nov 2026):
        from . import rebound_book                                 # the Setups rule + the capitulation-rebound long on BTC
        extra = rebound_book.scoreboard_extra(len(shadow.get(rebound_book.NAME, [])))   # and ETH. The row says "NOT passed,
        if extra is not None:                                      # paper only" and carries the registered comparison with
            shadow.setdefault(rebound_book.NAME, [])               # b_targets and the override's own record. Read only; a
            mind_rows[rebound_book.NAME] = extra                   # failure never stops the scoreboard
    except Exception as e:
        log("rebound book: %r" % (e,))
    for name, pn in sorted(shadow.items()):
        rows.append(dict({"book": name, "title": SHADOW_TITLES.get(name) or "Shadow: " + name, "kind": "shadow"},
                         **row(pn)))
        rows[-1].update(mind_rows.get(name) or {})
    by_book = {}
    for r in playbook_rows or []:
        if r.get("status") == "CLOSED" and r.get("pnl_usd") is not None:
            by_book.setdefault(r.get("book"), []).append((float(r["pnl_usd"]), _day(r.get("exit_utc"))))
    titles = _scoreboard_titles()
    for b, pn in sorted(by_book.items()):
        rows.append(dict({"book": b, "title": titles.get(b) or "Strategy: " + b, "kind": "strategy"}, **row(pn)))
    out = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "min_trades": MIN_TRADES, "rows": rows,
           "note": "Forward results only. A book is judged once it has %d trades: ahead if the low end of its 90%% range "
                   "per trade is above zero, behind if the high end is below zero." % MIN_TRADES,
           "note_by_day": BY_DAY_NOTE}
    if learner is not None:
        out["exit_learner"] = learner                              # its tables, whom it follows, the arms over the same days
    try:                                                           # the paper desk (paper_desk.py; owner, 22 Nov 2026):
        from . import paper_desk                                   # three forward paper wallets on the Setups book's BTC
        out["paper_desk"] = paper_desk.block()                     # and ETH trades. Read only; it never stops the scoreboard
    except Exception as e:
        log("paper desk: %r" % (e,))
    try:                                                           # the book allocator a_alloc (book_alloc.py; H110, owner
        from . import book_alloc                                   # 24 Nov 2026): one paper wallet split daily between the
        out["a_alloc"] = book_alloc.block(playbook_rows)           # forward books. Read only, NOT passed; never stops this
    except Exception as e:
        log("book allocator: %r" % (e,))
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
