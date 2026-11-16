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
DISK_LOW_GB = 3.0                                                     # warn when the data disk has less than this free


def disk_free_gb(path=None):
    """Free space (GB) on the disk that holds the engine's data; None if it cannot be read."""
    try:
        import shutil
        return shutil.disk_usage(path or DATA_DIR).free / 1e9
    except Exception:
        return None
SUMMARY_UTC = (0, 0)
QUIET = ("p1_", "p2_", "p3_", "p6_vwap", "p7_session", "p8_", "p9_", "p10_", "p11_", "p12_")
FORWARD = ("playbook4", "playbook5", "playbook6", "playbook7")
WON = {}                                                    # book key -> win % (scoreboard)


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


NAMES = {"main": "Main engine", "b_trail": "B trail (shadow)", "b_targets": "B targets (shadow)",
         "b_ema20_1h_t1": "EMA20 trail (shadow)", "b_sma20_1h_t1": "SMA20 trail (shadow)", "b_be_t1": "Break-even trail",
         "a_pullback": "A pullback (shadow)", "h3_flip_limit": "H3 flip limit", "h5_damp": "H5 damped", "v4": "v4 (old rules)",
         "y_4h": "4h yardstick", "y_1d": "Daily yardstick", "m_swing_1h": "1h swing mind", "m_swing_4h": "4h swing mind",
         "p5_rlq": "P5 RL agent", "p6_mtrend": "P6 RL momentum", "p6_p4trend": "P6 control (RL)", "p7_rvbear": "P7 BTC/ETH pair",
         "p4_h30spot": "P4 rule A", "p4_h31trail": "P4 rule B", "p1_liqhunt": "P1 liquidity hunt (retired)",
         "p3_orb": "P3 opening range", "p6_vwap": "P6 VWAP", "p7_session": "P7 session", "p8_fvg": "P8 fair-value gap",
         "p10_round": "P10 round numbers", "p11_release": "P11 release", "p12_orb_us": "P12 US opening range",
         "p5_squeeze": "P5 squeeze"}
GREEN, RED, FLAG_END, SCALE, BRAIN, WARN, OK, WAVE, CHART = (u"\U0001f7e2", u"\U0001f534", u"\U0001f3c1", u"\u2696\ufe0f",
                                                            u"\U0001f9e0", u"\u26a0\ufe0f", u"\u2705", u"\U0001f44b", u"\U0001f4ca")


def _esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


TABLE = {"b_trail": "B trail", "b_targets": "B targets", "b_ema20_1h_t1": "EMA20 trail", "b_sma20_1h_t1": "SMA20 trail",
         "b_be_t1": "BE trail", "p8_fvg": "P8 FVG", "p3_orb": "P3 ORB", "p6_vwap": "P6 VWAP", "p10_round": "P10 round",
         "p1_liqhunt": "P1 liq hunt", "p5_rlq": "P5 RL", "p6_mtrend": "P6 RL mom", "p6_p4trend": "P6 RL ctrl",
         "p7_rvbear": "P7 pair", "a_pullback": "A pullback", "main": "Main"}
MKT = {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "XAUUSD": "Gold", "XAGUSD": "Silver", "USDJPY": "USDJPY", "SPX": "S&P", "WTI": "WTI",
       "BRENT": "Brent"}


def _tname(book):
    return TABLE.get(book, NAMES.get(book, book))[:12]


def _name(key):
    book = key.split("|")[0]
    return NAMES.get(book, book)


def _bar(n, total=30, width=10):
    k = max(0, min(width, int(round(width * float(n) / total))))
    return u"\u2588" * k + u"\u2591" * (width - k)


def _send(tok, chat, text):
    """One message as HTML (bold, fixed-width tables); plain text if Telegram rejects the markup."""
    r = _call(tok, "sendMessage", {"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True})
    if not r.get("ok"):
        import re as _re
        plain = _re.sub(r"<[^>]+>", "", text).replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        r = _call(tok, "sendMessage", {"chat_id": chat, "text": plain})
    return r


# ------------------------------------------------------------------ what the engine wrote
def counts(score, page):
    """-> ({book key: closed trades}, {book key: verdict}, {book key: net usd}) from the scoreboard and forward books."""
    c, v, net = {}, {}, {}
    for r in (score or {}).get("rows", []):
        k = "%s|%s" % (r.get("book"), r.get("title"))
        c[k], v[k], net[k] = int(r.get("trades") or 0), str(r.get("verdict") or ""), float(r.get("net_usd") or 0.0)
        WON[k] = r.get("won_pct")
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


def _trade_card(key, added, delta, n, tot):
    won = WON.get(key)
    return (u"%s <b>%s</b> \u00b7 closed %d trade%s\n"
            u"Result <b>%s</b>   Total <b>%s</b>%s\n"
            u"<code>%s</code> %d / 30 to verdict\n"
            u"<i>paper only</i>") % (GREEN if delta >= 0 else RED, _esc(_name(key)), added, "" if added == 1 else "s",
                                     _usd(delta), _usd(tot), "" if won is None else "   Won %.0f%%" % float(won), _bar(n), n)


def events(prev, cur, page, now=None):
    """-> list of alert cards (HTML) by comparing the previous check (prev) with this one (cur)."""
    ev = []
    if prev.get("c") is not None:
        for k, n in cur["c"].items():
            old = prev["c"].get(k)
            book = k.split("|")[0]
            if old is None or n <= old:
                continue
            tot = cur["net"].get(k, 0.0)
            if n >= 30 > old:
                ev.append(u"%s <b>%s</b> reached <b>%d trades</b>\nVerdict due \u00b7 net <b>%s</b>\n<i>paper only</i>"
                          % (FLAG_END, _esc(_name(k)), n, _usd(tot)))
            elif not book.startswith(QUIET):
                ev.append(_trade_card(k, n - old, tot - prev.get("net", {}).get(k, tot), n, tot))
        for k, s in cur["v"].items():
            old = prev.get("v", {}).get(k)
            if old and s != old and not s.startswith("too few trades"):
                ev.append(u"%s <b>%s</b> verdict\n%s" % (SCALE, _esc(_name(k)), _esc(s)))
        for i, (a, b) in enumerate(zip(prev.get("refits", []), cur["refits"])):
            if b > a:
                ev.append(u"%s <b>Weekly RL refit done</b> (Phase %d)\nThe new model is used from the next step." % (BRAIN, 5 + i))
    age = page_age_min(page, now)
    if age is not None:
        if age > STALE_MIN and not prev.get("stale"):
            ev.append(u"%s <b>Engine quiet</b>\nNo page update for %.0f min (last %s UTC).\nIt may be down: check the server."
                      % (WARN, age, page["generated_utc"][11:16]))
        if age <= STALE_MIN and prev.get("stale"):
            ev.append(u"%s <b>Engine back</b>\nPage updated %s UTC." % (OK, page["generated_utc"][11:16]))
    return ev


def summary(page, score, now=None):
    """The daily summary card (HTML: bold headings, fixed-width tables)."""
    now = now or datetime.now(timezone.utc)
    head = u"%s <b>Mind 15 \u00b7 daily summary</b>\n%s UTC \u00b7 <i>paper only</i>" % (CHART, now.strftime("%a %d %b, %H:%M"))
    if not page:
        return head + u"\n\n%s No page available: the engine may be down." % WARN
    age = page_age_min(page, now)
    ok = age is not None and age <= STALE_MIN
    L = [head, u"%s Engine %s \u00b7 updated %s" % (OK if ok else WARN, _esc(page.get("version", "?")),
                                                   "?" if age is None else "%.0f min ago" % age)]
    free = disk_free_gb()
    if free is not None:
        L.append(u"%s Server disk %.1f GB free" % (OK if free >= DISK_LOW_GB else WARN, free))
    L.append("")
    rows, tot_open = [], 0.0
    for a, d in (page.get("assets") or {}).items():
        tr = d.get("trade") or {}
        u = float(tr.get("unrealized_usd") or 0.0)
        tot_open += u
        pos = str(d.get("position") or tr.get("status") or "-")
        edge = d.get("edge_pts")
        rows.append("%-6s %-5s %6s %9s" % (MKT.get(a, d.get("short") or a)[:6], pos[:5],
                                          "" if edge is None else "%+.1f" % float(edge), _usd(u)))
    table = "\n".join(["%-6s %-5s %6s %9s" % ("Market", "Side", "Edge", "Open"), "-" * 29] + rows +
                      ["-" * 29, "%-19s %9s" % ("Total open", _usd(tot_open))])
    L += ["<b>Positions</b>", "<pre>%s</pre>" % _esc(table)]
    since = now.timestamp() - 86400
    closed = []
    for a, d in (page.get("assets") or {}).items():
        for t in d.get("closed_trades") or []:
            try:
                ts = datetime.fromisoformat(str(t.get("time_out")).replace("Z", "+00:00")).timestamp()
            except Exception:
                continue
            if ts >= since:
                pnl = float(t.get("pnl_usd") or 0.0)
                closed.append(u"%s %s %s <b>%s</b>" % (GREEN if pnl >= 0 else RED, _esc(MKT.get(a, d.get("short") or a)),
                                                      "long" if t.get("side", 0) > 0 else "short", _usd(pnl)))
    L += ["", u"<b>Main engine \u00b7 closed in 24 h</b>"] + (closed or ["none"])
    srows = (score or {}).get("rows", [])
    lead = sorted((r for r in srows if int(r.get("trades") or 0) >= 5), key=lambda r: -float(r.get("net_usd") or 0))[:3]
    if lead:
        L += ["", "<b>Leaders</b> (5+ trades)", "<pre>%s</pre>" % _esc("\n".join(
            "%-12s %8s %3d trades" % (_tname(r["book"]), _usd(float(r["net_usd"] or 0)), int(r["trades"]))
            for r in lead))]
    near = sorted((r for r in srows if 15 <= int(r.get("trades") or 0) < 30), key=lambda r: -int(r["trades"]))
    L += ["", "<b>Close to a verdict</b>"]
    L += ["<pre>%s</pre>" % _esc("\n".join(u"%-12s %s %2d/30" % (_tname(r["book"]), _bar(int(r["trades"])),
                                                                int(r["trades"])) for r in near))] if near else ["none"]
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
                _send(tok, chat, u"%s <b>Mind 15 alerts are on</b> for this chat.\nTrade closes, verdicts, engine warnings and a "
                                 u"daily summary at 08:00 SGT. Send /summary any time.\n<i>paper only</i>" % WAVE)
            elif chat == st.get("chat_id") and text.startswith("/summary"):
                _send(tok, chat, summary(_load(PAGE), _load(SCORE), now))
    page, score = _load(PAGE), _load(SCORE)
    c, v, net = counts(score, page)
    cur = {"c": c, "v": v, "net": net, "refits": refit_marks()}
    ev = events(st, cur, page, now)
    free = disk_free_gb()
    if free is not None:                                              # server health: the data disk filling up
        if free < DISK_LOW_GB and not st.get("disk_low"):
            ev.append(u"%s <b>Server disk low</b>\nOnly %.1f GB free on the data disk. The engine stops writing when it is full."
                      % (WARN, free))
        elif free >= DISK_LOW_GB + 1 and st.get("disk_low"):
            ev.append(u"%s <b>Server disk OK again</b>\n%.1f GB free." % (OK, free))
        cur["disk_low"] = free < DISK_LOW_GB or (bool(st.get("disk_low")) and free < DISK_LOW_GB + 1)
    age = page_age_min(page, now)
    stale = bool(age is not None and age > STALE_MIN)
    day = now.strftime("%Y-%m-%d")
    due = (now.hour, now.minute) >= SUMMARY_UTC and st.get("summary_day") != day
    if send and tok and st.get("chat_id") is not None:
        for e in ev:
            _send(tok, st["chat_id"], e)
        if due:
            _send(tok, st["chat_id"], summary(page, score, now))
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
        _send(tok, st["chat_id"], summary(_load(PAGE), _load(SCORE)))
        return 0
    if "--sample" in argv:                                            # one example alert card, labelled as a sample
        tok = token()
        if not (tok and st.get("chat_id") is not None):
            print("no key file or no chat yet")
            return 1
        c, v, net = counts(_load(SCORE), _load(PAGE))
        k = next((x for x in c if x.startswith("b_trail|")), None)
        if k:
            _send(tok, st["chat_id"], u"<i>Sample of the new alert look:</i>\n" + _trade_card(k, 1, 210.0, c[k], net.get(k, 0.0)))
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
