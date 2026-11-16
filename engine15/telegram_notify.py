# -*- coding: utf-8 -*-
"""telegram_notify -- Mind 15's Telegram alerts and daily summary. PAPER ONLY; it sends messages, nothing else.

Owner, 16 Nov 2026: a new Telegram bot for Mind 15, "Alerts + daily summary". A separate process beside the live loop (the
Singapore box runs it as systemd service mind15-telegram); it only READS the engine's own outputs and never touches the
engine, its data or the web box.

    python -m engine15.telegram_notify            run forever (one check a minute)
    python -m engine15.telegram_notify --once     one check, then exit (tests / manual)
    python -m engine15.telegram_notify --summary  send the daily summary now

Alerts: a closed trade on the main, shadow, RL and pair books; any book reaching 30 trades or changing its verdict; the page
not updated for STALE_MIN minutes (and when it is fresh again); the weekly RL refits finishing. Busy strategy books only
alert at 30 trades or a verdict change. Daily summary at SUMMARY_UTC (00:00 UTC = 08:00 Singapore).

THE KEY: read from a file the owner places (TOKEN_FILE, chmod 600); never printed, logged or stored anywhere else.
THE CHAT: the first chat that sends /start is locked in (state file); every other chat is ignored. No key file = it waits.
"""
import io
import json
import os
import sys
import time
from datetime import datetime, timezone

from .config import DATA_DIR, OUT_DIR, ROOT

TOKEN_FILE = os.environ.get("MIND15_TELEGRAM_TOKEN_FILE", os.path.join(ROOT, "secrets", "telegram_token"))
STATE = os.path.join(DATA_DIR, "telegram_state.json")
PAGE = os.path.join(OUT_DIR, "live", "page.json")
SCORE = os.path.join(OUT_DIR, "live", "scoreboard.json")
REFIT_LOGS = (os.path.join(ROOT, "research", "out", "rl", "forward5", "update.log"),
              os.path.join(ROOT, "research", "out", "rl", "forward6", "update.log"))
API = "https://api.telegram.org/bot%s/%s"
STALE_MIN = 40
SUMMARY_UTC = (0, 0)
QUIET = ("p1_", "p2_", "p3_", "p6_vwap", "p7_session", "p8_", "p9_", "p10_", "p11_", "p12_")
FORWARD = ("playbook4", "playbook5", "playbook6", "playbook7")


# ------------------------------------------------------------------ small helpers
def _load(path, default=None):
    try:
        with io.open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def _save(path, obj):
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1)
    os.replace(tmp, path)


def token():
    """The bot key from the owner's file, or None. Never printed."""
    try:
        with io.open(TOKEN_FILE, encoding="utf-8") as fh:
            t = fh.read().strip()
        return t or None
    except Exception:
        return None


def _call(tok, method, payload, timeout=20):
    import requests
    r = requests.post(API % (tok, method), json=payload, timeout=timeout)
    try:
        return r.json()
    except Exception:
        return {"ok": False, "description": "HTTP %s" % r.status_code}


def _usd(v):
    return ("+$%s" if v >= 0 else "-$%s") % "{:,.0f}".format(abs(v))


# ------------------------------------------------------------------ what the engine wrote
def counts(score, page):
    """-> ({book key: closed trades}, {book key: verdict}, {book key: net usd}) from the scoreboard and forward books."""
    c, v, net = {}, {}, {}
    for r in (score or {}).get("rows", []):
        k = "%s|%s" % (r.get("book"), r.get("title"))
        c[k], v[k], net[k] = int(r.get("trades") or 0), str(r.get("verdict") or ""), float(r.get("net_usd") or 0.0)
    for mod in FORWARD:
        for bk, b in ((page or {}).get("playbook", {}).get(mod) or {}).items():
            if isinstance(b, dict) and "totals" in b and not any(k.startswith(bk + "|") for k in c):
                c[bk + "|forward"] = int(b["totals"].get("trades") or 0)
                net[bk + "|forward"] = float(b["totals"].get("net_usd") or 0.0)
    return c, v, net


def page_age_min(page, now=None):
    try:
        t = datetime.strptime(page["generated_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None
    return ((now or datetime.now(timezone.utc)) - t).total_seconds() / 60.0


def refit_marks():
    """-> number of 'model written' lines per refit log (a new line = a refit finished)."""
    out = []
    for p in REFIT_LOGS:
        try:
            with io.open(p, encoding="utf-8", errors="replace") as fh:
                out.append(sum(1 for ln in fh if "model written" in ln))
        except Exception:
            out.append(0)
    return out


def events(prev, cur, page, now=None):
    """-> list of alert texts by comparing the previous check (prev) with this one (cur)."""
    ev = []
    if prev.get("c") is not None:
        for k, n in cur["c"].items():
            old = prev["c"].get(k)
            book = k.split("|")[0]
            if old is None or n <= old:
                continue
            tot = cur["net"].get(k, 0.0)
            if n >= 30 > old:
                ev.append("Mind 15: %s reached %d trades - verdict due (net %s)." % (book, n, _usd(tot)))
            elif not book.startswith(QUIET):
                delta = tot - prev.get("net", {}).get(k, tot)
                ev.append("Mind 15: %s closed %d trade(s) (%s), now %d of 30, net %s." % (book, n - old, _usd(delta), n, _usd(tot)))
        for k, s in cur["v"].items():
            old = prev.get("v", {}).get(k)
            if old and s != old and not s.startswith("too few trades"):
                ev.append("Mind 15: %s verdict - %s" % (k.split("|")[0], s))
        for i, (a, b) in enumerate(zip(prev.get("refits", []), cur["refits"])):
            if b > a:
                ev.append("Mind 15: weekly RL refit (Phase %d) finished." % (5 + i))
    age = page_age_min(page, now)
    if age is not None:
        if age > STALE_MIN and not prev.get("stale"):
            ev.append("Mind 15: page STALE - last update %s (%.0f min ago). The engine may be down." % (page["generated_utc"], age))
        if age <= STALE_MIN and prev.get("stale"):
            ev.append("Mind 15: page fresh again (%s)." % page["generated_utc"])
    return ev


def summary(page, score, now=None):
    """The daily summary as plain text."""
    now = now or datetime.now(timezone.utc)
    L = ["Mind 15 daily summary - %s UTC (paper only)" % now.strftime("%a %d %b %H:%M"), ""]
    if not page:
        return "\n".join(L + ["No page available - the engine may be down."])
    age = page_age_min(page, now)
    L.append("Engine %s, page %s (%s min old)." % (page.get("version", "?"), page.get("generated_utc", "?"),
                                                  "?" if age is None else "%.0f" % age))
    L += ["", "Positions:"]
    tot_open = 0.0
    for a, d in (page.get("assets") or {}).items():
        tr = d.get("trade") or {}
        u = float(tr.get("unrealized_usd") or 0.0)
        tot_open += u
        L.append("- %s: %s, edge %s pts, open %s" % (d.get("short") or a, d.get("position") or tr.get("status") or "?",
                                                    d.get("edge_pts"), _usd(u)))
    L.append("Open P&L across markets: %s" % _usd(tot_open))
    since = now.timestamp() - 86400
    closed = []
    for a, d in (page.get("assets") or {}).items():
        for t in d.get("closed_trades") or []:
            try:
                ts = datetime.fromisoformat(str(t.get("time_out")).replace("Z", "+00:00")).timestamp()
            except Exception:
                continue
            if ts >= since:
                closed.append("- %s %s: %s" % (d.get("short") or a, "long" if t.get("side", 0) > 0 else "short",
                                              _usd(float(t.get("pnl_usd") or 0.0))))
    L += ["", "Main books, closed in the last 24 h:"] + (closed or ["- none"])
    rows = sorted((score or {}).get("rows", []), key=lambda r: -int(r.get("trades") or 0))
    near = [r for r in rows if 15 <= int(r.get("trades") or 0) < 30]
    lead = sorted((r for r in rows if int(r.get("trades") or 0) >= 5), key=lambda r: -float(r.get("net_usd") or 0))[:3]
    L += ["", "Leaders (5+ trades):"] + ["- %s: %s over %d trades" % (r["book"], _usd(float(r["net_usd"] or 0)), r["trades"]) for r in lead]
    L += ["", "Close to a verdict (15-29 trades):"] + (["- %s: %d of 30, %s" % (r["book"], r["trades"], _usd(float(r["net_usd"] or 0)))
                                                         for r in near] or ["- none"])
    return "\n".join(L)


# ------------------------------------------------------------------ the loop
def check(st, tok, send=True, now=None):
    """One check: learn the chat from /start, send alerts, send the daily summary once a day. -> the new state."""
    now = now or datetime.now(timezone.utc)
    if tok:
        up = _call(tok, "getUpdates", {"offset": st.get("update_offset", 0), "timeout": 0})
        for u in (up.get("result") or []) if up.get("ok") else []:
            st["update_offset"] = int(u["update_id"]) + 1
            msg = u.get("message") or {}
            chat = (msg.get("chat") or {}).get("id")
            text = (msg.get("text") or "").strip()
            if chat is None:
                continue
            if st.get("chat_id") is None and text.startswith("/start"):
                st["chat_id"] = chat
                _call(tok, "sendMessage", {"chat_id": chat, "text": "Mind 15 alerts are on for this chat (paper only). "
                                           "You will get trade closes, verdicts, stale-page warnings and a daily summary at 08:00 SGT."})
            elif chat == st.get("chat_id") and text.startswith("/summary"):
                _call(tok, "sendMessage", {"chat_id": chat, "text": summary(_load(PAGE), _load(SCORE), now)})
    page, score = _load(PAGE), _load(SCORE)
    c, v, net = counts(score, page)
    cur = {"c": c, "v": v, "net": net, "refits": refit_marks()}
    ev = events(st, cur, page, now)
    age = page_age_min(page, now)
    stale = bool(age is not None and age > STALE_MIN)
    day = now.strftime("%Y-%m-%d")
    due = (now.hour, now.minute) >= SUMMARY_UTC and st.get("summary_day") != day
    if send and tok and st.get("chat_id") is not None:
        for e in ev:
            _call(tok, "sendMessage", {"chat_id": st["chat_id"], "text": e})
        if due:
            _call(tok, "sendMessage", {"chat_id": st["chat_id"], "text": summary(page, score, now)})
            st["summary_day"] = day
    elif due and st.get("chat_id") is None:
        pass                                                          # no chat yet: the summary waits
    st.update(cur, stale=stale, checked_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"))
    return st, ev


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    st = _load(STATE, {}) or {}
    if "--summary" in argv:
        tok = token()
        if not (tok and st.get("chat_id") is not None):
            print("no key file or no chat yet: send /start to the bot after the key file is in place")
            return 1
        _call(tok, "sendMessage", {"chat_id": st["chat_id"], "text": summary(_load(PAGE), _load(SCORE))})
        return 0
    while True:
        try:
            st, ev = check(st, token())
            _save(STATE, st)
            for e in ev:
                print(time.strftime("%Y-%m-%d %H:%M:%S"), e, flush=True)
        except Exception as e:                                        # never die; never print the key
            print(time.strftime("%Y-%m-%d %H:%M:%S"), "check failed: %s" % type(e).__name__, flush=True)
        if "--once" in argv:
            return 0
        time.sleep(60)


if __name__ == "__main__":
    sys.exit(main())
