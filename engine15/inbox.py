# -*- coding: utf-8 -*-
"""inbox -- answers given on the web page, read at each step.

The web server keeps PIN-checked answers; the AI Trading Bot's pull tool
(C:/tmp/kronos/aitrading-pages-ans/answers/pull_answers.py, the ONLY path to the server) appends
them to data/answers_inbox.jsonl. This module reads the lines it has not read before, records
each as an owner view and writes the audit-trail row. Format and rules:
C:/tmp/kronos/aitrading-pages-ans/answers/FORMAT.md (v1).

  - A missing inbox file means no web answers.
  - Only complete lines (ending in a newline) are read; a half-written last line waits a step.
  - Our own bookmark (data/answers_inbox.cursor.json, {"last_seq": N}); the inbox is never written.
  - who == "test" (any case) is the go-live test: counted, not recorded.
  - An answer already on the audit trail (same answer_id) is never recorded twice.
  - The PIN is never in a line; the server checked it.
"""
import json
import os
import time

from . import owner
from .config import DATA_DIR

INBOX = os.environ.get("MIND15_INBOX", os.path.join(DATA_DIR, "answers_inbox.jsonl"))
CURSOR = os.path.join(DATA_DIR, "answers_inbox.cursor.json")
ASSETS = ("BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "USDJPY", "SPX", "WTI", "BRENT")


PULL_TOOL = os.environ.get("MIND15_PULL_TOOL", "C:/tmp/kronos/aitrading-pages-ans/answers/pull_answers.py")
PULL_EVERY_S = 300                                                  # at most one pull per 5 minutes
_last_pull = [0.0]


def pull(log=print, timeout=90):
    """Copy new web answers from the server into the local inbox with the AI Trading Bot's pull tool
    (the only path to the server: one ssh connection, its own cursor, no repeats or gaps). Never raises.
    Exit codes (the tool's README): 0 done, 1 did not complete (nothing written), 4 server does not
    continue from the cursor, 5 local write failed. -> exit code, or None when skipped."""
    import subprocess
    import sys
    if not os.path.exists(PULL_TOOL) or time.time() - _last_pull[0] < PULL_EVERY_S:
        return None
    _last_pull[0] = time.time()
    try:
        extra = ["--key", os.environ["MIND15_PULL_KEY"]] if os.environ.get("MIND15_PULL_KEY") else []   # Singapore box: own key
        r = subprocess.run([sys.executable, PULL_TOOL] + extra, capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        log("web answers: pull did not run (%r)" % (e,))
        return None
    if r.returncode != 0:
        log("web answers: pull exit %d: %s" % (r.returncode, (r.stdout or r.stderr or "").strip().splitlines()[-1:]))
    elif "No new answers" not in (r.stdout or ""):
        log("web answers: %s" % ((r.stdout or "").strip().splitlines()[-1:] or ["pulled"])[0])
    return r.returncode


def _bookmark(path):
    if not os.path.exists(path):
        return 0
    try:
        with open(path, encoding="utf-8") as fh:
            return int(json.load(fh).get("last_seq", 0))
    except (ValueError, OSError):
        return 0


def _save_bookmark(path, seq):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"last_seq": int(seq)}, fh)
    os.replace(tmp, path)


def _valid(d):
    try:
        return (isinstance(d, dict) and d.get("v") == 1 and d.get("kind") == "answer"
                and isinstance(d.get("seq"), int) and d["seq"] > 0 and isinstance(d.get("id"), str)
                and isinstance(d.get("who"), str) and 0 < len(d["who"].strip()) <= 40
                and d.get("asset") in ASSETS and d.get("side") in ("long", "short", "none")
                and isinstance(d.get("conviction"), (int, float)) and not isinstance(d.get("conviction"), bool)
                and 0 <= d["conviction"] <= 100 and isinstance(d.get("note", ""), str)
                and isinstance(d.get("received_utc"), str)
                and (d.get("decision_time") is None or isinstance(d.get("decision_time"), str)))
    except Exception:
        return False


def _ms(utc):
    return int(time.mktime(time.strptime(utc, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone) * 1000


def _question_for(trail, asset, decision_time, received_utc):
    qs = [r for r in trail if r.get("kind") == "question" and r.get("asset") == asset]
    if decision_time:
        same = [r for r in qs if r.get("session") == decision_time]
        if same:
            return same[-1]
    before = [r for r in qs if r.get("t_utc", "") <= received_utc]
    return before[-1] if before else None


def read_new(inbox=None, cursor=None, views_path=None, audit_path=None, log=print):
    """Handle every new line. -> counts {"recorded", "test", "duplicate", "invalid"}."""
    inbox, cursor = inbox or INBOX, cursor or CURSOR
    counts = {"recorded": 0, "test": 0, "duplicate": 0, "invalid": 0}
    if not os.path.exists(inbox):
        return counts
    with open(inbox, "rb") as fh:
        raw = fh.read()
    last = _bookmark(cursor)
    lines = [ln for ln in raw.split(b"\n")[:-1]]                   # the piece after the last newline waits
    new = []
    for ln in lines:
        try:
            d = json.loads(ln.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            counts["invalid"] += 1
            continue
        if not _valid(d):
            counts["invalid"] += 1
            continue
        if d["seq"] > last:
            new.append(d)
    if not new:
        return counts
    trail = owner.read_audit(audit_path)
    seen = set(r.get("answer_id") for r in trail if r.get("kind") == "answer" and r.get("answer_id"))
    top = last
    for d in sorted(new, key=lambda r: r["seq"]):
        top = max(top, d["seq"])
        if d["who"].strip().lower() == "test":
            counts["test"] += 1
            continue
        if d["id"] in seen:
            counts["duplicate"] += 1
            continue
        conv = float(d["conviction"]) / 100.0
        note = d.get("note", "") or ""
        owner.tell(d["asset"], d["side"], conv, hours=24.0, note=note, now_ms=_ms(d["received_utc"]), path=views_path)
        q = _question_for(trail, d["asset"], d.get("decision_time"), d["received_utc"])
        owner.audit("answer", audit_path, who=d["who"].strip()[:40], asset=d["asset"], side=d["side"], conviction=conv,
                    hours=24.0, note=note[:300], question=q["question"] if q else None,
                    question_session=q["session"] if q else None, source="web", answer_id=d["id"],
                    received_utc=d["received_utc"])
        seen.add(d["id"])
        counts["recorded"] += 1
    _save_bookmark(cursor, top)
    if any(counts.values()):
        log("web answers: %(recorded)d recorded, %(test)d test, %(duplicate)d already on file, %(invalid)d unreadable" % counts)
    return counts
