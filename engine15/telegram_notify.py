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

Two read-only reports (the arithmetic is in livecheck.py):
  DATA HEALTH, every check, from the page it already loads (never the journal): a card that was reading and has said
    "no read" for 8 closes in a row of its own market gets ONE alert (all cards in one message per check) and a line when
    it reads again; a closed market has no new close and is never counted. One line in the daily summary; /health lists all.
  LIVE CALIBRATION, with the first daily summary of each ISO week and on /calibration: the stated odds against what
    happened, per market, from the live journal (streamed, a few numbers kept per line; at most CALIB_DAYS days and
    CALIB_BUDGET_S seconds). A record of forecasts, never proof of an edge.

SUBSCRIBER SIGNAL PREVIEW (H53, the signal book S1; the rules and the arithmetic are in signals.py): when the b_targets
  paper book opens a position a signal card goes out, and follow-ups (entry filled, no fill, Target 1, Target 2, stopped,
  closed by the model) are sent as replies to it; a daily recap goes with the daily summary; /signals and /record answer
  on request. PREVIEW: every one of these goes to the owner's own chat only, under a first line "Subscriber preview".
  No subscriber channel exists. A failure in the signals code is logged once and never stops the alerts above.

VIP VAULT EXIT INSTRUCTIONS (owner, 19 Nov 2026): every exit intent vault_feed.py sends to the live VIP vault gets ONE card
  the first time its status is final: accepted by the vault, refused, or given up after 24 h; and one card when sends have
  failed for 30 min (one more when they go through again). Read only: one small read of data/vault_feed_state.json per
  check; vault_feed is never imported. A missing or garbled file means no card; a failure there never stops the rest.

EARLY SIGNAL PREVIEW (H56, the early signal book S2; signals_early.py): the same entries announced at the model's decision
  (side and limit price; stop and targets follow as a reply one bar later), under a first line "Early signal preview",
  to the owner's chat only, beside the S1 preview; /early answers with its record and the paired comparison; one line in
  the daily recap. Its own guard: a failure there never touches S1, the alerts or the summary.

DATA HISTORY CHANGED (owner, 19 Nov 2026, "add an alert"): the reading cache's once-a-day check (evcache.update) re-reads
  every stored row and rewrites the ones whose readings changed; live.py writes what it found to data/check_report.json.
  ONE card per group and UTC day when an asset had more than MIND15_CHECK_ALERT_ROWS (default 2,000) changed old rows or
  the check was stopped by its budget. Read only; a missing or garbled file means no card; never twice for a group/day.

WEEKLY RANKING (owner, 19 Nov 2026): with the first daily summary of each ISO week (Monday 00:00 UTC), once (state key
  rank_week), and on /ranking: every forward book ranked by return %. Table 1, the books on the main engine's entries
  (page shadows scoreboard; marked incl. open trades; capital $10k x markets); table 2, the strategy and RL books (page
  playbook; closed trades only; capital $10k x markets traded, RL books 2, the pair book 1). Retired books at the bottom,
  unranked. "This week": 30 trades reached, verdict changed, retired, best and worst mover, against the snapshot stored at
  the previous weekly card (rank_prev, rank_prev_utc). Its own guard: a failure there never stops the rest.

RL HEALTH (owner, 21 Nov 2026, after the RL audit: "Yes, start them"): read only, from the page's RL book states.
  NO AGENT TRADING: one card when every seed agent of an RL book on a coin is on its 'do no harm' fallback (flat for the
  Phase 4 book, the 30-day momentum position for the Phase 6 books), so the results there are the fallback's and not the
  agent's; one line when an agent is back. WEEKLY CHECK: one card when the books start using a new weekly model, and on
  /rl: per book and coin, how many of the 3 seed agents trade, the past week's result split into agent and fallback, and
  the input drift reading (the share of the model's inputs more than 3 training standard deviations from their training
  mean; marked as drifting when it is above RL_DRIFT_PCT and more than twice the week before). Its own guard.

GIVE-BACK (owner, 21 Nov 2026: "Yes"): one card when an open MAIN-book trade has given back GIVEBACK_PCT (25%) or more of
  its best open profit. Read only, from the page: the best is the best the bot has SEEN at its checks (the page moves once
  a close, so it is a best of 15-minute marks, and for a trade already running when this started, the best since then).
  Measured on price (mark against entry), so closing half at a target is not a give-back. Only when that best was worth
  at least GIVEBACK_MIN_PEAK_PCT (1%) of the book's equity; once per best: a new, higher best can alert again. An alert
  only: no stop, book or setting changes. Its own guard.

THE KEY: read from a file the owner places (TOKEN_FILE, chmod 600); never printed, logged or stored anywhere else.
THE CHAT: the first chat that sends /start is locked in (state file); every other chat is ignored. No key file = it waits.
"""
import io
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

from . import livecheck, signals
from .config import DATA_DIR, JOURNAL_DIR, OUT_DIR, ROOT

TOKEN_FILE = os.environ.get("MIND15_TELEGRAM_TOKEN_FILE", os.path.join(ROOT, "secrets", "telegram_token"))
STATE = os.path.join(DATA_DIR, "telegram_state.json")
PAGE = os.path.join(OUT_DIR, "live", "page.json")
SCORE = os.path.join(OUT_DIR, "live", "scoreboard.json")
REFIT_LOGS = (os.path.join(ROOT, "research", "out", "rl", "forward5", "update.log"),
              os.path.join(ROOT, "research", "out", "rl", "forward6", "update.log"))
API = "https://api.telegram.org/bot%s/%s"
STALE_MIN = 40
DISK_LOW_GB = 3.0                                                     # warn when the data disk has less than this free
JOURNAL = JOURNAL_DIR                                                 # the live day files (read only for the calibration card)
BARS = DATA_DIR                                                       # the engine's own 15m bar files (read only, tail only)
CALIB_DAYS = 90                                                       # the calibration card looks back at most this far
CALIB_BUDGET_S = 45.0                                                 # ... and stops reading older days after this long
LIST_MAX = 8                                                          # lines per section in one data alert
SIGNALS_PREVIEW = True                                                # H53: signal cards go to the owner's own chat ONLY
SIGNALS_CHANNEL = None                                                # a future subscriber channel id; unused in the preview
SIGNALS_HEAD = u"\U0001f9ea Subscriber preview"                       # the first line of every signal message in the preview
SIGNALS_STATE = os.path.join(DATA_DIR, "signals_state.json")          # the signals' own state and log (signals.py writes them)
SIGNALS_LOG = os.path.join(DATA_DIR, "signals_log.jsonl")
LIVE = os.path.join(OUT_DIR, "live")                                  # the book's closed-trade files (read only)
_SIGNALS_ERR = [None]                                                 # the last signals failure printed (printed once)
_SIGNALS_UNREAD = [""]                                                # the markets whose bars could not be read, as last printed
# VIP vault exit alerts (owner, 19 Nov 2026): the feed's own state file, READ ONLY (vault_feed.py writes it; never imported here)
VAULT_STATE = os.path.join(DATA_DIR, "vault_feed_state.json")
VAULT_READ_MAX = 1 << 20                                              # bytes read at most; a larger file is not read (no alert)
VAULT_WINDOW_S = 2 * 86400                                            # only intents made this recently are alerted (made + 24 h)
VAULT_MEMORY_S = 8 * 86400                                            # alerted ids kept this long (the feed drops them after 7 d)
VAULT_MEMORY_MAX = 400                                                # ... and at most this many (the newest)
VAULT_FAIL_S = 1800                                                   # sends failing this long -> one card
VAULT_BAR_S = 900                                                     # a book goes once per 15m bar: its as_of may lag one bar
VAULT_ALIVE_S = 600                                                   # the feed wrote its state this recently = it is running
_VAULT_ERR = [None]                                                   # the last vault-alert failure printed (printed once)


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


# Owner, 17 Nov 2026: the website shows paper-book dollars enlarged ("Enlarge the capital by 100 times"), the bot matches
# ("Scale the bot 100x too"); later the same day: "Lets adjust 100x to 15x. So it is at 1mil usd range". Display only: every
# paper-book dollar amount the bot prints goes through _usd; percentages, win rates, prices and points are unchanged, and
# the engine's files keep the real figures.
DISPLAY_X = float(os.environ.get("MIND15_TG_DISPLAY_X", "15"))


def _usd(v):
    v = float(v) * DISPLAY_X
    return ("+$%s" if v >= 0 else "-$%s") % "{:,.0f}".format(abs(v))


def _usd_short(v):
    """The same amount for the fixed-width tables (phone width): +$950, +$12.3k, +$136k, +$1.24M."""
    v = float(v) * DISPLAY_X
    a, sign = abs(v), ("+" if v >= 0 else "-")
    if a >= 1e6:
        return "%s$%.2fM" % (sign, a / 1e6)
    if a >= 1e5:
        return "%s$%.0fk" % (sign, a / 1e3)
    if a >= 1e4:
        return "%s$%.1fk" % (sign, a / 1e3)
    return "%s$%s" % (sign, "{:,.0f}".format(a))


NAMES = {"main": "Main engine", "b_trail": "B trail (shadow)", "b_targets": "B targets (shadow)",
         "b_trend30": "Trend 30d (shadow)",
         "b_ema20_1h_t1": "EMA20 trail (shadow)", "b_sma20_1h_t1": "SMA20 trail (shadow)", "b_be_t1": "Break-even trail",
         "a_pullback": "A pullback (shadow)", "h3_flip_limit": "H3 flip limit", "h5_damp": "H5 damped", "v4": "v4 (old rules)",
         "y_4h": "4h yardstick", "y_1d": "Daily yardstick", "m_swing_1h": "1h swing mind", "m_swing_4h": "4h swing mind",
         "p5_rlq": "P5 RL agent", "p6_mtrend": "P6 RL momentum", "p6_p4trend": "P6 control (RL)", "p7_rvbear": "P7 BTC/ETH pair",
         "p4_h30spot": "P4 rule A", "p4_h31trail": "P4 rule B", "p1_liqhunt": "P1 liquidity hunt (retired)",
         "p3_orb": "P3 opening range", "p6_vwap": "P6 VWAP", "p7_session": "P7 session", "p8_fvg": "P8 fair-value gap",
         "p10_round": "P10 round numbers (retired)", "p11_release": "P11 release", "p12_orb_us": "P12 US opening range",
         "p5_squeeze": "P5 squeeze", "f_floor_33_3r": "Floor 1/3 (shadow)"}
GREEN, RED, FLAG_END, SCALE, BRAIN, WARN, OK, WAVE, CHART = (u"\U0001f7e2", u"\U0001f534", u"\U0001f3c1", u"\u2696\ufe0f",
                                                            u"\U0001f9e0", u"\u26a0\ufe0f", u"\u2705", u"\U0001f44b", u"\U0001f4ca")
TARGET, DISH, BANK, CROSS = u"\U0001f3af", u"\U0001f4e1", u"\U0001f3e6", u"❌"


def _esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


TABLE = {"b_trail": "B trail", "b_targets": "B targets",
         "b_trend30": "Trend 30d", "b_ema20_1h_t1": "EMA20 trail", "b_sma20_1h_t1": "SMA20 trail",
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


def _send(tok, chat, text, reply_to=None):
    """One message as HTML (bold, fixed-width tables); plain text if Telegram rejects the markup.
    reply_to: send it as a reply to that message; if the reply is refused it goes out as a message of its own."""
    text = text.replace("Kronos", "AlphaPrediction AI").replace("kronos", "candle forecast")   # same wording rule as the page (export.py)
    msg = {"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    r = _call(tok, "sendMessage", dict(msg, reply_to_message_id=reply_to)) if reply_to is not None else {"ok": False}
    if not r.get("ok"):
        r = _call(tok, "sendMessage", msg)
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
    pb = (page or {}).get("playbook") if isinstance(page, dict) else None
    for mod in FORWARD:
        books = pb.get(mod) if isinstance(pb, dict) else None             # a garbled page never stops the check
        for bk, b in (books.items() if isinstance(books, dict) else ()):
            if isinstance(b, dict) and isinstance(b.get("totals"), dict) and not any(k.startswith(bk + "|") for k in c):
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


# ------------------------------------------------------------------ data health (the page's cards) and live calibration
def _mk(a):
    return MKT.get(a, a)


def _short(title):
    """A card's name without its bracket: 'Liquidity (order book)' -> 'Liquidity'."""
    return str(title).split(" (")[0]


def _when(t, date=True):
    """'2026-11-16 14:45' -> '16 Nov 14:45 UTC' (or '14:45 UTC')."""
    try:
        d = datetime.strptime(str(t)[:16], "%Y-%m-%d %H:%M")
    except Exception:
        return "?"
    return ("%d %s " % (d.day, d.strftime("%b")) if date else "") + d.strftime("%H:%M") + " UTC"


def _feeds(rows, fmt, limit=LIST_MAX):
    out = [u"• %s: %s" % (_esc(_short(r["card"])), fmt(r)) for r in rows[:limit]]
    return out + (["+%d more" % (len(rows) - limit)] if len(rows) > limit else [])


def _markets(r):
    return _esc(", ".join(_mk(a) for a in r["assets"]))


def health_line(h):
    """The ONE data line of the daily summary; None before the first look at the page's cards."""
    v = livecheck.health_view(h)
    if not v["cards"]:
        return None
    names = [_short(r["card"]) for r in v["silent"]]
    s = u"%s Data: %d of %d cards reading" % (OK if not names else WARN, v["reading"], v["cards"])
    if names:
        s += u" · silent: %s%s" % (_esc(", ".join(names[:3])), " +%d more" % (len(names) - 3) if len(names) > 3 else "")
    return s


def health_alert(gone, back):
    """ONE message for everything that went silent or came back at this check (a feed outage cannot spam the chat)."""
    L = []
    if gone:
        rows = livecheck._by_card(gone)
        L += [u"%s <b>Data feed silent</b>" % WARN] + _feeds(rows, lambda r: u"%s · no read for %d closes, since %s" % (
            _markets(r), r["closes"], _when(r["since"], False)))
    if back:
        rows = livecheck._by_card(back)
        L += [u"%s <b>Data back</b>" % OK] + _feeds(rows, lambda r: u"%s · reading again after %d closes" % (
            _markets(r), r["closes"]))
    return "\n".join(L + ["Send /health for the full list."]) if L else None


def health_card(h):
    """The /health answer: every silent card and since when."""
    v = livecheck.health_view(h)
    head = u"%s <b>Mind 15 · data health</b>\n" % DISH
    if not v["last"]:
        return head + u"<i>paper only</i>\n\nNo cards seen yet: the page has not been read."
    L = [head + u"Last close seen %s · <i>paper only</i>" % _when(v["last"]),
         u"%s <b>%d of %d cards reading</b>" % (OK if not v["silent"] else WARN, v["reading"], v["cards"]), ""]
    L += [u"<b>Silent</b> (was reading, now past its limit)"]
    L += _feeds(v["silent"], lambda r: u"%s\n   since %s · %d closes" % (_markets(r), _when(r["since"]), r["closes"]),
                20) or ["none"]
    if v["missed"]:
        L += ["", u"<b>Missed the last closes</b> (inside the limit)"]
        L += _feeds(v["missed"], lambda r: u"%s · %d" % (_markets(r), r["closes"]), 10)
    if v["never"]:
        L += ["", u"<b>Never read here</b> since the watch began (not counted): %d" % len(v["never"]),
              _esc(u" · ".join("%s: %s" % (_short(r["card"]), ", ".join(_mk(a) for a in r["assets"]))
                                    for r in v["never"][:12])) + (" +%d more" % (len(v["never"]) - 12) if len(v["never"]) > 12 else "")]
    L += ["", u"Limit: %d closes in a row of its own market (2 h of trading), or twice its longest earlier gap, at most %d. "
              u"A closed market has no new close, so it is not counted." % (livecheck.SILENT_CLOSES, livecheck.SILENT_CAP)]
    return "\n".join(L)


def calibration_now(now=None):
    """The heavy read: the live journal of the last CALIB_DAYS days, streamed. Only at the weekly card or on /calibration."""
    now = now or datetime.now(timezone.utc)
    return livecheck.calibration(JOURNAL, BARS, start=(now - timedelta(days=CALIB_DAYS)).strftime("%Y-%m-%d"),
                                 end=now.strftime("%Y-%m-%d"), budget_s=CALIB_BUDGET_S)


def calibration_card(res):
    """The weekly calibration card: one line per market, then the stated odds against what came, all markets pooled."""
    head = u"%s <b>Mind 15 · live calibration</b>\n" % TARGET
    mk = dict((a, s) for a, s in ((res or {}).get("markets") or {}).items() if s.get("n"))
    if not mk:
        return head + u"<i>paper only</i>\n\nNo graded live forecasts in the journal yet."
    try:
        since = datetime.strptime(res["since"], "%Y-%m-%d")
        since = "%d %s" % (since.day, since.strftime("%b %Y"))
    except Exception:
        since = "?"
    L = [head + u"Live data since %s · <i>paper only</i>" % since,
         u"When it says 60%, does it happen 60% of the time?", ""]
    rows, notes, most = [], [], None
    for a, s in mk.items():
        checked = s.get("source") == "bars"
        rows.append("%-6s %4d %3s %s" % (_mk(a)[:6], s["n"], "-" if s.get("hit_pct") is None else "%.0f%%" % s["hit_pct"],
                                         s.get("verdict") if checked else "n/a *"))
        if not checked:
            notes.append(u"* %s: %s, so the engine's own tallies and no odds check." % (_mk(a), s.get("why") or "not re-graded"))
        elif most is None or s.get("ind_n", 0) > most[1]:
            most = (_mk(a), s.get("ind_n", 0))
    L += ["<pre>%s</pre>" % _esc("\n".join(["%-6s %4s %3s %s" % ("Market", "n", "Hit", "Verdict"), "-" * 30] + rows))]
    p = res.get("pooled") or {}
    table = ["%-8s %5d %4s %4s" % (r["said"], r["n"], "%.0f%%" % r["avg_said_pct"], "%.0f%%" % r["came_pct"])
             for r in p.get("table") or [] if r.get("n")]
    if table:
        L += ["<b>All markets pooled</b>",
              "<pre>%s</pre>" % _esc("\n".join(["%-8s %5s %4s %4s" % ("Said %", "n", "Avg", "Came"), "-" * 24] + table))]
        if p.get("brier") is not None:
            L.append(u"Brier %.3f against %.3f for the base rate (lower is better)." % (p["brier"], p["brier_base"]))
    L += [u"<b>Hit</b>: direction right among calls graded up or down, by the engine's own grading. "
          u"<b>Said / Came</b>: the odds it gave the side it favoured, and how often that side came first."]
    if most:
        L.append(u"<b>Verdict</b>: a 95%% binomial interval on calls that do not overlap in time; under %d of those is too few "
                 u"(most so far: %s %d)." % (res.get("min_ind", livecheck.MIN_IND), most[0], most[1]))
    L += [_esc(n) for n in notes]
    if res.get("partial"):
        L.append("Older days were not read (time limit).")
    L.append(u"<i>A record of live forecasts, not proof of an edge.</i>")
    return "\n".join(L)


def summary(page, score, now=None, health=None):
    """The daily summary card (HTML: bold headings, fixed-width tables). health: the bot's remembered card health."""
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
    data = health_line(health)
    if data:
        L.append(data)
    L.append("")
    rows, tot_open = [], 0.0
    for a, d in (page.get("assets") or {}).items():
        tr = d.get("trade") or {}
        u = float(tr.get("unrealized_usd") or 0.0)
        tot_open += u
        pos = str(d.get("position") or tr.get("status") or "-")
        edge = d.get("edge_pts")
        rows.append("%-6s %-5s %6s %9s" % (MKT.get(a, d.get("short") or a)[:6], pos[:5],
                                          "" if edge is None else "%+.1f" % float(edge), _usd_short(u)))
    table = "\n".join(["%-6s %-5s %6s %9s" % ("Market", "Side", "Edge", "Open"), "-" * 29] + rows +
                      ["-" * 29, "%-19s %9s" % ("Total open", _usd_short(tot_open))])
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
            "%-12s %8s %3d trades" % (_tname(r["book"]), _usd_short(float(r["net_usd"] or 0)), int(r["trades"]))
            for r in lead))]
    near = sorted((r for r in srows if 15 <= int(r.get("trades") or 0) < 30), key=lambda r: -int(r["trades"]))
    L += ["", "<b>Close to a verdict</b>"]
    L += ["<pre>%s</pre>" % _esc("\n".join(u"%-12s %s %2d/30" % (_tname(r["book"]), _bar(int(r["trades"])),
                                                                int(r["trades"])) for r in near))] if near else ["none"]
    return "\n".join(L)


# ------------------------------------------------------------------ the subscriber signal preview (H53; signals.py)
def _signal_send(tok, st, text, reply_to=None):
    """One signal message -> (delivered, its message id). PREVIEW: the owner's own chat only, under the preview line."""
    chat = st.get("chat_id") if SIGNALS_PREVIEW else SIGNALS_CHANNEL
    if not tok or chat is None:
        return False, None
    r = _send(tok, chat, (SIGNALS_HEAD + u"\n" if SIGNALS_PREVIEW else u"") + text, reply_to)
    ok = bool(isinstance(r, dict) and r.get("ok"))
    return ok, ((r.get("result") or {}).get("message_id") if ok else None)


def _signals_guard(what, fn):
    """Run one piece of signals code. Whatever it raises is caught and printed once (never the key): the admin alerts,
    the summary and the state of this bot never depend on it."""
    try:
        out = fn()
        _SIGNALS_ERR[0] = None
        return out
    except Exception as e:
        tag = "%s: %s" % (what, type(e).__name__)
        if _SIGNALS_ERR[0] != tag:
            _SIGNALS_ERR[0] = tag
            print(time.strftime("%Y-%m-%d %H:%M:%S"), "signals failed (%s)" % tag, flush=True)
        return None


def signals_check(st, tok, page, now, recap=False):
    """The signals part of one check: follow the signals out, issue new ones, and the daily recap with the summary."""
    def work():
        send = lambda text, reply_to=None: _signal_send(tok, st, text, reply_to)   # noqa: E731
        info = signals.run(page, now, send, BARS, LIVE, SIGNALS_STATE, SIGNALS_LOG)
        unread = ",".join(sorted(set(info.get("bars_unread") or [])))
        if unread != _SIGNALS_UNREAD[0]:                              # a bar file caught mid-write: said once, read again later
            _SIGNALS_UNREAD[0] = unread
            if unread:
                print(time.strftime("%Y-%m-%d %H:%M:%S"), "signals: bars not readable now, will retry (%s)" % unread, flush=True)
        if recap and os.path.exists(SIGNALS_STATE):                   # only once the preview has started
            send(signals.recap_card(SIGNALS_LOG, now, signals.load_state(SIGNALS_STATE), extra=[early_recap_line(now)]))
        return info
    return _signals_guard("check", work)


# ------------------------------------------------------------------ VIP vault exit instructions (vault_feed.py's state, read only)
# The feed (vault_feed.run) queues each exit intent once: {"body", "status", "made", "seq"}. Its statuses:
#   pending   queued, retried every step until the vault answers (also while the vault is down or the config is wrong)
#   sent      the vault took it (HTTP 200 ok; a duplicate of one it already holds is "sent" too)      -> alert: accepted
#   refused   the vault answered 400 / 409, or the feed's own last guard refused the body           -> alert: refused
#   expired   still pending 24 h after it was made: given up                                        -> alert: given up
# Finished intents stay in the file for 7 days, then the feed deletes them.
VAULT_ACTION = {"close": u"close the position", "move_stop": u"move the stop to the entry"}


def _vault_read(path=None):
    """-> (the feed's state dict, its mtime) or (None, None): missing, too large, garbled or not an object. One read."""
    path = path or VAULT_STATE
    try:
        mtime = os.path.getmtime(path)
        with open(path, "rb") as fh:
            raw = fh.read(VAULT_READ_MAX + 1)
        if len(raw) > VAULT_READ_MAX:
            return None, None
        doc = json.loads(raw.decode("utf-8"))
    except Exception:
        return None, None
    return (doc, mtime) if isinstance(doc, dict) else (None, None)


def _vault_px(s):
    """The vault's decimal string with thousands commas: '65203.2' -> '65,203.2'; anything else as text (escaped)."""
    s = str(s)
    whole, dot, frac = s.partition(".")
    if not whole.isdigit() or (frac and not frac.isdigit()):
        return _esc(s[:24])
    return "{:,}".format(int(whole)) + dot + frac


def _vault_hm(t):
    try:
        return datetime.fromtimestamp(float(t), timezone.utc).strftime("%d %b %H:%M UTC").lstrip("0")
    except Exception:
        return "?"


def _vault_opened(iid):
    """The setup's opening time from the intent id 'BTCUSDT.20261118T101500Z.close.futures' -> '18 Nov 10:15 UTC'."""
    try:
        d = datetime.strptime(iid.split(".")[1], "%Y%m%dT%H%M%SZ")
    except Exception:
        return None
    return d.strftime("%d %b %H:%M UTC").lstrip("0")


def _vault_side(iid, body, intents):
    """The setup's side. A move_stop names it (BUY = a long book, as vault_feed builds it); the feed makes spot intents
    for a LONG book only, and always together with the futures ones of the same step, so the same setup (symbol and
    opening time) with a spot intent is long and without one short. None when it cannot be read."""
    if body.get("action") == "move_stop" and body.get("side") in ("BUY", "SELL"):
        return "long" if body["side"] == "BUY" else "short"
    parts = iid.split(".")
    if len(parts) < 4:
        return None
    sibs = [it.get("body") for k, it in intents.items()
            if isinstance(k, str) and k.split(".")[:2] == parts[:2] and isinstance(it, dict) and isinstance(it.get("body"), dict)]
    for b in sibs:
        if b.get("action") == "move_stop" and b.get("side") in ("BUY", "SELL"):
            return "long" if b["side"] == "BUY" else "short"
    return "long" if any(b.get("market") == "spot" for b in sibs) else "short"


def vault_card(iid, it, intents, now):
    """One exit instruction's card (HTML, plain words, no id, no secret, no URL), or None when it is not final."""
    status, b = it.get("status"), it.get("body")
    if status not in ("sent", "refused", "expired") or not isinstance(b, dict):
        return None
    act = b.get("action")
    if act == "reduce":
        try:
            pct = float(b.get("fraction")) * 100
            words = (u"take half (reduce 50%)" if pct == 50 else u"reduce %.0f%%" % pct)
        except Exception:
            words = u"reduce the position"
    elif act == "move_stop":
        words = VAULT_ACTION[act] + (u" at %s" % _vault_px(b["stop_price"]) if b.get("stop_price") else u"")
    else:
        words = VAULT_ACTION.get(act, _esc(str(act)[:20]))
    if status == "sent":
        outcome = u"%s Accepted by the vault" % OK
    elif status == "refused":
        code = next((it[k] for k in ("code", "why", "error") if it.get(k)), None)
        outcome = u"%s Refused: %s" % (CROSS, _esc(str(code)[:60]) if code else
                                       u"code not kept in the feed's state (see the engine log)")
    else:
        outcome = u"%s Not delivered for 24 h, given up" % WARN
    side, opened = _vault_side(iid, b, intents), _vault_opened(iid)
    setup = u"%s opened %s" % (side or u"side unknown", opened) if opened else (side or u"unknown")
    return u"\n".join([
        u"%s <b>VIP vault · exit instruction</b>" % BANK,
        u"%s %s: <b>%s</b>" % (_esc(_mk(str(b.get("symbol")))), _esc(str(b.get("market"))), words),
        u"Reference price %s" % _vault_px(b.get("reference_price")),
        u"Setup: %s" % _esc(setup),
        outcome,
        u"Made %s · seen %s" % (_vault_hm(it.get("made")), now.strftime("%d %b %H:%M UTC").lstrip("0"))])


def vault_failing(doc, mtime, now_s):
    """-> the lines of the 'sends failing' card, [] when sends go through. Two signs, both from the feed's state:
    an exit still pending VAULT_FAIL_S after it was made, and (while the feed keeps writing its state) no book accepted
    for VAULT_FAIL_S beyond the one-bar lag (the state keeps the as_of of the last accepted book, not a send time)."""
    out = []
    intents = doc.get("intents") if isinstance(doc.get("intents"), dict) else {}
    late = []
    for it in intents.values():
        try:
            if it.get("status") == "pending" and now_s - float(it["made"]) > VAULT_FAIL_S:
                late.append(now_s - float(it["made"]))
        except Exception:
            continue
    if late:
        out.append(u"• %d exit instruction%s waiting, the oldest for %.0f min" % (
            len(late), "" if len(late) == 1 else "s", max(late) / 60.0))
    if mtime is not None and now_s - mtime <= VAULT_ALIVE_S:
        newest = None
        for v in (doc.get("book") if isinstance(doc.get("book"), dict) else {}).values():
            try:
                t = datetime.strptime(v["as_of"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
            except Exception:
                continue
            newest = t if newest is None else max(newest, t)
        if newest is not None and now_s - newest > VAULT_FAIL_S + VAULT_BAR_S:
            out.append(u"• no book accepted for %.0f min (newest: bar of %s) while the feed keeps running"
                       % ((now_s - newest) / 60.0, _vault_hm(newest)))
    return out


def vault_memory_lost(doc, mem, tok, chat, now, done):
    """The feed lost its memory while a setup was open (vault_feed.memory_alarm): ONE card per setup. -> the keys to
    remember {key: time}, only for cards that were delivered."""
    out = {}
    alarm = doc.get("alarm") if isinstance(doc.get("alarm"), dict) else {}
    lost = alarm.get("memory_lost") if isinstance(alarm.get("memory_lost"), dict) else {}
    for sym in sorted(k for k in lost if isinstance(k, str)):
        a = lost[sym]
        if not isinstance(a, dict):
            continue
        key = "memory_lost:%s:%s" % (sym[:20], str(a.get("opened_utc"))[:20])
        if key in mem:
            continue
        try:
            opened = datetime.strptime(str(a.get("opened_utc")), "%Y-%m-%dT%H:%M:%SZ").strftime("%d %b %H:%M UTC").lstrip("0")
        except Exception:
            opened = u"time unknown"
        side = {"LONG": u"long", "SHORT": u"short"}.get(a.get("side"), u"side unknown")
        why = u"could not be read" if a.get("why") == "unreadable" else u"was missing"
        card = u"\n".join([
            u"%s <b>VIP vault \u00b7 feed memory lost</b>" % WARN,
            u"%s: %s setup opened %s" % (_esc(_mk(sym[:20])), side, opened),
            u"The feed's record %s while this setup was open." % why,
            (u"An exit that was due before now (a Target 1 taken meanwhile, or one still waiting) was <b>not sent</b>. "
             u"Later exits for this setup will be sent.") if a.get("exits") == "later" else
            u"It will send <b>no exit</b> for this setup, and any exit that was still waiting is gone.",
            u"Members in it are covered only by their stop on the exchange.",
            u"What to do is in the engine's restore page."])
        r = _send(tok, chat, card)
        if isinstance(r, dict) and r.get("ok"):
            out[key] = now.timestamp()
            done.append(card)
    return out


def vault_check(st, tok, chat, now):
    """The vault part of one check: a card per intent the first time it is final, and one card when sends fail for
    30 min (and one when they go through again). An id is remembered only once its card is delivered. Never raises.
    -> the cards delivered."""
    done = []
    try:
        doc, mtime = _vault_read()
        if doc is None:
            return done
        now_s = now.timestamp()
        mem = st.get("vault_alerted") if isinstance(st.get("vault_alerted"), dict) else {}
        intents = doc.get("intents") if isinstance(doc.get("intents"), dict) else {}
        order = []
        for iid, it in intents.items():
            if not isinstance(iid, str) or not isinstance(it, dict) or iid in mem:
                continue
            try:
                made = float(it.get("made"))
                seq = int(it.get("seq") or 0)
            except Exception:
                continue
            if now_s - made <= VAULT_WINDOW_S and it.get("status") in ("sent", "refused", "expired"):
                order.append((seq, made, iid, it))
        for seq, made, iid, it in sorted(order, key=lambda r: (r[0], r[1])):
            card = vault_card(iid, it, intents, now)
            if card is None:
                continue
            r = _send(tok, chat, card)
            if isinstance(r, dict) and r.get("ok"):
                mem[iid] = made
                done.append(card)
        cut = now_s - VAULT_MEMORY_S
        keep = sorted(((k, v) for k, v in mem.items() if isinstance(v, (int, float)) and v >= cut), key=lambda kv: -kv[1])
        st["vault_alerted"] = dict(keep[:VAULT_MEMORY_MAX])
        st["vault_alerted"].update(vault_memory_lost(doc, st["vault_alerted"], tok, chat, now, done))
        lines = vault_failing(doc, mtime, now_s)
        if lines and not st.get("vault_failing"):
            card = u"\n".join([u"%s <b>VIP vault · sends failing</b>" % WARN] + lines +
                              [u"The feed retries every step; an exit still pending after 24 h is given up."])
            r = _send(tok, chat, card)
            if isinstance(r, dict) and r.get("ok"):
                st["vault_failing"] = True
                done.append(card)
        elif not lines and st.get("vault_failing"):
            card = u"%s <b>VIP vault · sends going through again</b>" % OK
            r = _send(tok, chat, card)
            if isinstance(r, dict) and r.get("ok"):
                st["vault_failing"] = False
                done.append(card)
        _VAULT_ERR[0] = None
    except Exception as e:                                            # never stops the other alerts; printed once
        tag = type(e).__name__
        if _VAULT_ERR[0] != tag:
            _VAULT_ERR[0] = tag
            print(time.strftime("%Y-%m-%d %H:%M:%S"), "vault alerts failed (%s)" % tag, flush=True)
    return done

# ------------------------------------------------------------------ data history changed (the daily check's report, read only)
# Owner, 19 Nov 2026: "add an alert". Once a UTC day the reading cache re-reads every stored row of each group and rewrites
# the rows whose readings changed (evcache.update); live.write_check_report puts what it found in data/check_report.json:
#   {"groups": {group: {"day", "changed_rows": {asset: n}, "stopped", "stop_reason", "seconds", "at_utc"}}}
# ONE card per group and UTC day when an asset had more than CHECK_ALERT_ROWS changed old rows (MIND15_CHECK_ALERT_ROWS)
# or the check was stopped by its budget. Read only, one small read per check; a missing or garbled file means no card.
CHECK_REPORT = os.path.join(DATA_DIR, "check_report.json")
CHECK_ALERT_ROWS = 2000                                               # changed old rows of ONE asset that make a card
CHECK_READ_MAX = 1 << 16                                              # bytes read at most; a larger file is not read
CHECK_FRESH_DAYS = 1                                                  # a report of today or yesterday (UTC) only
CHECK_MEMORY_DAYS = 8                                                 # group/day keys alerted, kept this long
COMPASS = u"\U0001f9ed"
_CHECK_ERR = [None]                                                   # the last failure printed (printed once)


def check_alert_rows():
    """MIND15_CHECK_ALERT_ROWS (a whole number >= 1), else CHECK_ALERT_ROWS."""
    try:
        v = int(str(os.environ.get("MIND15_CHECK_ALERT_ROWS", "")).strip() or CHECK_ALERT_ROWS)
        return v if v >= 1 else CHECK_ALERT_ROWS
    except ValueError:
        return CHECK_ALERT_ROWS


def _check_read(path=None):
    """-> {group: entry} from the report, or {} when it is missing, too large, garbled or shaped otherwise."""
    try:
        with open(path or CHECK_REPORT, "rb") as fh:
            raw = fh.read(CHECK_READ_MAX + 1)
        if len(raw) > CHECK_READ_MAX:
            return {}
        doc = json.loads(raw.decode("utf-8"))
        groups = doc.get("groups") if isinstance(doc, dict) else None
        return dict((g, e) for g, e in groups.items() if isinstance(g, str) and isinstance(e, dict)) \
            if isinstance(groups, dict) else {}
    except Exception:
        return {}


def history_card(g, e, limit=None):
    """One group's entry -> the card, or None when no asset passed the limit and the check was not stopped."""
    limit = check_alert_rows() if limit is None else limit
    rows = {}
    for a, n in (e.get("changed_rows") if isinstance(e.get("changed_rows"), dict) else {}).items():
        try:
            n = int(n)
        except (TypeError, ValueError):
            continue
        if n > 0:
            rows[str(a)] = n
    stopped = e.get("stopped") is True
    if not stopped and not any(n > limit for n in rows.values()):
        return None
    total = sum(rows.values())
    who = u" · ".join(u"%s %s" % (_esc(MKT.get(a, a)), "{:,}".format(n)) for a, n in sorted(rows.items(), key=lambda r: -r[1]))
    try:
        secs = u"finished in %.0fs" % float(e.get("seconds"))
    except (TypeError, ValueError):
        secs = u"finished"
    how = u"was stopped by its limit and resumes tomorrow" if stopped else secs
    return u"%s <b>Data history changed · %s</b>: %s old row%s revised today%s; the daily check %s" % (
        COMPASS, _esc(g), "{:,}".format(total), "" if total == 1 else "s", u" (%s)" % who if who else "", how)


def history_check(st, tok, chat, now, path=None):
    """The data-history part of one check: one card per group and UTC day (a key is remembered only once its card is
    delivered, so never twice). Never raises. -> the cards delivered."""
    done = []
    try:
        mem = st.get("history_alerted") if isinstance(st.get("history_alerted"), dict) else {}
        today = now.date()
        now_s = now.timestamp()
        for g, e in _check_read(path).items():
            try:
                day = datetime.strptime(str(e.get("day")), "%Y-%m-%d").date()
            except Exception:
                continue
            if not 0 <= (today - day).days <= CHECK_FRESH_DAYS:
                continue
            key = "%s|%s" % (g, day.isoformat())
            if key in mem:
                continue
            card = history_card(g, e)
            if card is None:
                continue
            r = _send(tok, chat, card)
            if isinstance(r, dict) and r.get("ok"):
                mem[key] = now_s
                done.append(card)
        cut = now_s - CHECK_MEMORY_DAYS * 86400
        st["history_alerted"] = dict((k, v) for k, v in mem.items() if isinstance(v, (int, float)) and v >= cut)
        _CHECK_ERR[0] = None
    except Exception as e:                                            # never stops the other alerts; printed once
        tag = type(e).__name__
        if _CHECK_ERR[0] != tag:
            _CHECK_ERR[0] = tag
            print(time.strftime("%Y-%m-%d %H:%M:%S"), "data history alert failed (%s)" % tag, flush=True)
    return done


# ------------------------------------------------------------------ the early signal preview (H56; signals_early.py)
EARLY_HEAD = u"\U0001f9ea Early signal preview"                       # the first line of every early signal message
EARLY_STATE = os.path.join(DATA_DIR, "signals_early_state.json")      # its own state and log (signals_early.py writes them)
EARLY_LOG = os.path.join(DATA_DIR, "signals_early_log.jsonl")
_EARLY_ERR = [None]                                                   # {piece: its last failure printed} (each printed once)


def _early_send(tok, st, text, reply_to=None):
    """One early signal message -> (delivered, message id). PREVIEW: the owner's own chat only, under the early line."""
    chat = st.get("chat_id")
    if not tok or chat is None:
        return False, None
    r = _send(tok, chat, EARLY_HEAD + u"\n" + text, reply_to)
    ok = bool(isinstance(r, dict) and r.get("ok"))
    return ok, ((r.get("result") or {}).get("message_id") if ok else None)


def _early_guard(what, fn, default=None):
    """Run one piece of early-signal code (imported here, so even a broken module stays inside). Whatever it raises is
    printed once and swallowed: S1, the admin alerts and the summary never depend on it."""
    errs = _EARLY_ERR[0] = _EARLY_ERR[0] or {}                        # the last failure of each piece, printed once
    try:
        out = fn()
        errs.pop(what, None)
        return out
    except Exception as e:
        tag = "%s: %s" % (what, type(e).__name__)
        if errs.get(what) != tag:
            errs[what] = tag
            print(time.strftime("%Y-%m-%d %H:%M:%S"), "early signals failed (%s)" % tag, flush=True)
        return default


def early_check(st, tok, page, now):
    def work():
        from . import signals_early
        return signals_early.run(page, now, lambda text, reply_to=None: _early_send(tok, st, text, reply_to),
                                 BARS, LIVE, EARLY_STATE, EARLY_LOG)
    return _early_guard("check", work)


def early_command(st, tok):
    def work():
        from . import signals_early
        return _early_send(tok, st, signals_early.record_card(EARLY_LOG, SIGNALS_LOG, signals.load_state(EARLY_STATE)))
    return _early_guard("/early", work)


def early_recap_line(now):
    """The early signals' line in the daily recap; "" when the preview has not started or anything fails."""
    def work():
        if not os.path.exists(EARLY_STATE):
            return ""
        from . import signals_early
        return signals_early.recap_line(EARLY_LOG, SIGNALS_LOG, now)
    return _early_guard("recap", work, default="") or ""


# ------------------------------------------------------------------ the weekly ranking (owner, 19 Nov 2026)
RANK_CAPITAL = 10000.0                                                # paper capital per market, as on the page
RANK_SINCE = u"11 Nov 2026"                                           # the forward books' common start
RANK_MARKETS = {"playbook5": 2, "playbook6": 2, "playbook7": 1}       # RL books trade BTC and ETH by design; the pair book is one
RANK_SHORT = {"v4": "v4 old", "h3_flip_limit": "H3 flip", "h5_damp": "H5 damped", "y_4h": "Y 4h", "y_1d": "Y daily",
              "m_swing_1h": "M swing 1h", "m_swing_4h": "M swing 4h", "p2_trap": "P2 trap", "p4_gapfill": "P4 gap fill",
              "p5_squeeze": "P5 squeeze", "p7_session": "P7 session", "p9_cascade": "P9 cascade", "p11_release": "P11 release",
              "p12_orb_us": "P12 US ORB", "p4_h30spot": "P4 rule A", "p4_h31trail": "P4 rule B"}
TROPHY, STOP, UP, DOWN = u"\U0001f3c6", u"\U0001f6d1", u"\U0001f4c8", u"\U0001f4c9"
_RANK_ERR = [None]                                                    # the last ranking failure printed (printed once)


def _rname(book):
    """The table's short name (11 characters): the bot's TABLE label, then RANK_SHORT, then NAMES."""
    return TABLE.get(book) or RANK_SHORT.get(book) or NAMES.get(book, str(book))


def _num(v):
    """A finite float or None (garbled values are skipped, never raised)."""
    import math
    try:
        f = float(v)
    except Exception:
        return None
    return f if math.isfinite(f) else None


def _rank_verdict(s):
    """'behind: even the high end ...' -> 'behind'; 'too few trades to judge (5 of 30)' -> 'too few'."""
    s = str(s or "").strip()
    if not s:
        return ""
    return "too few" if s.startswith("too few") else s.split(":")[0].strip()[:12]


def ranking_books(page, score):
    """-> list of book dicts {id, book, kind ('main'|'strat'), name, ret, pnl, trades, retired, verdict} from the page.
    kind 'main': the shadows scoreboard (marked incl. open trades; capital $10k x its markets).
    kind 'strat': the strategy and RL books (closed trades only; capital $10k x markets traded, RL 2, pair book 1)."""
    page = page if isinstance(page, dict) else {}
    verdict = {}
    for r in ((score if isinstance(score, dict) else {}).get("rows") or []):
        if isinstance(r, dict):
            t = str(r.get("title") or "")
            kind = "main" if t.startswith("Shadow") else "strat" if t.startswith("Strategy") else None
            if kind:
                verdict[(kind, str(r.get("book")))] = _rank_verdict(r.get("verdict"))
    out, seen = [], set()
    sh = page.get("shadows")
    sb = sh.get("scoreboard") if isinstance(sh, dict) else None
    for r in ((sb.get("rows") if isinstance(sb, dict) else None) or []):
        if not isinstance(r, dict) or not r.get("book"):
            continue
        book, pnl, n = str(r["book"]), _num(r.get("pnl_usd")), _num(r.get("trades"))
        mk = _num(r.get("assets"))
        ret = pnl / (RANK_CAPITAL * mk) * 100.0 if pnl is not None and mk and mk > 0 else _num(r.get("return_pct"))
        if ret is None or ("main", book) in seen:
            continue
        seen.add(("main", book))
        out.append({"id": "s:" + book, "book": book, "kind": "main", "name": _rname(book)[:11], "ret": ret,
                    "pnl": pnl if pnl is not None else ret / 100.0 * RANK_CAPITAL * (mk or 1),
                    "trades": int(n or 0), "retired": bool(r.get("retired")), "verdict": verdict.get(("main", book), "")})
    pb = page.get("playbook")
    for mod, books in (sorted(pb.items()) if isinstance(pb, dict) else []):
        if not isinstance(books, dict):
            continue
        for book, b in sorted(books.items()):
            if not isinstance(b, dict) or not isinstance(b.get("totals"), dict) or ("strat", book) in seen:
                continue
            net, n = _num(b["totals"].get("net_usd")), _num(b["totals"].get("trades"))
            if net is None:
                continue
            mk = RANK_MARKETS.get(mod) or (len(b["by_asset"]) if isinstance(b.get("by_asset"), dict) else 0) or 1
            seen.add(("strat", book))
            out.append({"id": "p:" + book, "book": book, "kind": "strat", "name": _rname(book)[:11],
                        "ret": net / (RANK_CAPITAL * mk) * 100.0, "pnl": net, "trades": int(n or 0), "markets": mk,
                        "retired": bool(b.get("retired")) or "(retired" in str(b.get("title") or "").lower(),
                        "verdict": verdict.get(("strat", book), "")})
    return out


def _rank_table(rows):
    """One fixed-width table (28 characters): ranked books by return %, then the retired ones, unranked, at the bottom."""
    live = sorted((b for b in rows if not b["retired"] and b["trades"] > 0), key=lambda b: (-b["ret"], -b["trades"], b["name"]))
    gone = sorted((b for b in rows if b["retired"]), key=lambda b: -b["ret"])
    L = ["%2s %-11s %8s %4s" % ("#", "Book", "Return", "Trd"), "-" * 28]
    L += ["%2d %-11s %8s %4d" % (i, b["name"], "%+.2f%%" % b["ret"], b["trades"]) for i, b in enumerate(live, 1)]
    if gone:
        L += ["-" * 9 + " retired " + "-" * 10]
        L += ["%2s %-11s %8s %4d" % ("--", b["name"], "%+.2f%%" % b["ret"], b["trades"]) for b in gone]
    out = ["<pre>%s</pre>" % _esc("\n".join(L))] if live or gone else ["none yet"]
    idle = [b["name"] for b in rows if not b["retired"] and b["trades"] <= 0]
    if idle:
        out.append(u"No trades yet: %s%s" % (_esc(", ".join(idle[:8])), " +%d more" % (len(idle) - 8) if len(idle) > 8 else ""))
    return out


def ranking_snapshot(books):
    """What the next weekly card compares with: {id: {t: trades, v: verdict, r: return %, x: retired}}."""
    return dict((b["id"], {"t": b["trades"], "v": b["verdict"], "r": round(b["ret"], 4), "x": b["retired"]}) for b in books)


def ranking_week_lines(books, prev):
    """The 'this week' lines: 30 trades reached, verdict changed, retired; the best and worst mover by return % change."""
    if not isinstance(prev, dict) or not prev:
        return [u"First weekly card: changes are counted from here on."]
    L, moves = [], []
    for b in books:
        p = prev.get(b["id"]) if isinstance(prev.get(b["id"]), dict) else {}
        old_t = int(_num(p.get("t")) or 0)
        nm = _esc(b["name"])
        if b["trades"] >= 30 > old_t:
            L.append(u"%s %s reached <b>30 trades</b> (%d)" % (FLAG_END, nm, b["trades"]))
        if p.get("v") and b["verdict"] and b["verdict"] != p.get("v"):
            L.append(u"%s %s verdict now <b>%s</b> (was %s)" % (SCALE, nm, _esc(b["verdict"]), _esc(p["v"])))
        if b["retired"] and not p.get("x") and p:
            L.append(u"%s %s retired" % (STOP, nm))
        old_r = _num(p.get("r"))
        if old_r is not None and not b["retired"]:
            moves.append((b["ret"] - old_r, b))
    if moves:
        best, worst = max(moves, key=lambda m: m[0]), min(moves, key=lambda m: m[0])
        if best[0] > 0:
            L.append(u"%s Best mover: %s %+.2f pts, now %+.2f%% (%s)" % (UP, _esc(best[1]["name"]), best[0], best[1]["ret"],
                                                                      _usd_short(best[1]["pnl"])))
        if worst[0] < 0 and worst[1] is not best[1]:
            L.append(u"%s Worst mover: %s %+.2f pts, now %+.2f%% (%s)" % (DOWN, _esc(worst[1]["name"]), worst[0],
                                                                       worst[1]["ret"], _usd_short(worst[1]["pnl"])))
    return L or [u"No checkpoint crossed and no return change."]


def ranking_card(books, prev=None, prev_utc=None, now=None):
    """The weekly ranking card (HTML). books: ranking_books(); prev: the snapshot stored at the previous weekly card."""
    now = now or datetime.now(timezone.utc)
    L = [u"%s <b>Mind 15 · weekly ranking</b>" % TROPHY,
         u"Week %d · %s UTC" % (now.isocalendar()[1], now.strftime("%a %d %b %Y, %H:%M"))]
    if not books:
        return "\n".join(L + ["", u"No forward books in the page yet.", u"<i>paper only · not advice</i>"])
    L += ["", u"<b>On the main engine's entries</b>", u"<i>marked incl. open trades · $10k per market</i>"]
    L += _rank_table([b for b in books if b["kind"] == "main"])
    L += ["", u"<b>Strategy and RL books</b>", u"<i>closed trades only · $10k per market traded (RL 2, pair 1)</i>"]
    L += _rank_table([b for b in books if b["kind"] == "strat"])
    try:
        since = datetime.strptime(str(prev_utc)[:10], "%Y-%m-%d")
        since = u" (since %d %s)" % (since.day, since.strftime("%b"))
    except Exception:
        since = ""
    L += ["", u"<b>This week</b>%s" % since] + ranking_week_lines(books, prev)
    L += ["", u"<i>paper only · returns since %s · not advice</i>" % RANK_SINCE]
    return "\n".join(L)


def _rank_guard(what, fn):
    """Run one ranking piece; any failure is printed once (by kind) and swallowed: alerts and the summary never wait on it."""
    try:
        return fn()
    except Exception as e:
        err = "%s: %s" % (what, type(e).__name__)
        if _RANK_ERR[0] != err:
            _RANK_ERR[0] = err
            print(time.strftime("%Y-%m-%d %H:%M:%S"), "ranking failed (%s)" % err, flush=True)
        return None


def ranking_weekly(st, tok, chat, page, score, now):
    """With the first daily summary of the ISO week: the card, then this week's snapshot (state keys rank_prev, rank_prev_utc).
    rank_week is marked by the caller before this runs, so a failure is not retried every minute."""
    def work():
        books = ranking_books(page, score)
        if not books:
            return None                                               # no page or no books: no card, last snapshot kept
        _send(tok, chat, ranking_card(books, st.get("rank_prev"), st.get("rank_prev_utc"), now))
        st["rank_prev"], st["rank_prev_utc"] = ranking_snapshot(books), now.strftime("%Y-%m-%dT%H:%M:%SZ")
        return True
    return _rank_guard("weekly", work)


def ranking_command(st, tok, chat, now):
    """/ranking: the same card any time, against the last weekly snapshot (the snapshot is not changed)."""
    return _rank_guard("/ranking", lambda: _send(tok, chat, ranking_card(ranking_books(_load(PAGE), _load(SCORE)),
                                                                         st.get("rank_prev"), st.get("rank_prev_utc"), now)))


# ------------------------------------------------------------------ give-back (read only; owner, 21 Nov 2026)
GIVEBACK_PCT = 25.0                      # alert when the open profit is this share (or more) below its best
GIVEBACK_MIN_PEAK_PCT = 1.0              # ... and the best was at least this share of the book's realized equity


def giveback_update(prev, page):
    """-> (state {asset: {"id", "peak" (price units), "peak_utc", "alerted_peak"}}, [cards]). A flat book drops its
    entry (the next trade starts a new best); a page without assets, or an asset missing from it, changes nothing."""
    prev = prev if isinstance(prev, dict) else {}
    assets = (page or {}).get("assets") if isinstance(page, dict) else None
    if not isinstance(assets, dict):
        return prev, []
    cur, cards = dict(prev), []
    seen = str(page.get("generated_utc") or "")[:16].replace("T", " ")
    for a, v in sorted(assets.items()):
        t = v.get("trade") if isinstance(v, dict) else None
        if not isinstance(t, dict):
            continue
        side = {"LONG": 1, "SHORT": -1}.get(t.get("status"))
        try:
            entry, mark, qty = float(t["entry_price"]), float(t["mark_price"]), float(t["quantity"])
        except (KeyError, TypeError, ValueError):
            entry = mark = qty = None
        if side is None or entry is None:
            cur.pop(a, None)                                          # flat (or not readable as a trade)
            continue
        tid = "%s|%s" % (t.get("opened_utc"), t.get("status"))
        now_px = side * (mark - entry)                                # open profit per unit, in price
        old = prev.get(a)
        st = dict(old) if isinstance(old, dict) and old.get("id") == tid else {"id": tid, "peak": now_px, "peak_utc": seen,
                                                                             "alerted_peak": None}
        if now_px > st["peak"]:
            st["peak"], st["peak_utc"] = now_px, seen
        peak = float(st["peak"])
        try:
            eq = float(t.get("equity_realized") or 0.0)
        except (TypeError, ValueError):
            eq = 0.0
        big = peak > 0 and eq > 0 and peak * qty >= GIVEBACK_MIN_PEAK_PCT / 100.0 * eq
        new_best = st.get("alerted_peak") is None or peak > float(st["alerted_peak"])
        if big and new_best and now_px <= (1.0 - GIVEBACK_PCT / 100.0) * peak:
            st["alerted_peak"] = peak
            back = 100.0 * (1.0 - now_px / peak)
            name = v.get("short") or a
            lock = t.get("stop_locks_usd")
            tail = u"" if not isinstance(lock, (int, float)) else u" \u00b7 the stop locks %s" % _usd(lock)
            cards.append(
                u"%s <b>Give-back</b> \u00b7 %s %s\n"
                u"Open profit <b>%s</b>, %.0f%% below its best <b>%s</b> (seen %s UTC).\n"
                u"Stop %s%s\n"
                u"<i>paper only \u00b7 an alert, nothing changes</i>" % (
                    WARN, _esc(str(name)), "long" if side == 1 else "short", _usd(now_px * qty), back, _usd(peak * qty),
                    _esc(str(st.get("peak_utc") or "?")), _esc(str(t.get("stop_price"))), tail))
        cur[a] = st
    return cur, cards


# ------------------------------------------------------------------ RL health (read only; owner, 21 Nov 2026)
RL_MODS = ("playbook5", "playbook6")
RL_DRIFT_PCT = 5.0                       # the weekly card says "drifting" above this AND above twice the week before


def rl_states(page):
    """-> {"book|coin": that book's page state} for the RL forward books (empty on a page shaped unexpectedly)."""
    out = {}
    pb = (page or {}).get("playbook") if isinstance(page, dict) else None
    for mod in RL_MODS:
        books = pb.get(mod) if isinstance(pb, dict) else None
        for bk, b in (books.items() if isinstance(books, dict) else ()):
            states = b.get("books") if isinstance(b, dict) else None
            for coin, v in (states.items() if isinstance(states, dict) else ()):
                if isinstance(v, dict) and isinstance(v.get("seed_fallback"), list) and v["seed_fallback"]:
                    out["%s|%s" % (bk, coin)] = v
    return out


def _rl_label(key):
    book, coin = key.split("|")
    return u"<b>%s</b> \u00b7 %s" % (_esc(NAMES.get(book, book)), _esc(coin.replace("USDT", "")))


def _rl_agents(v):
    fb = [bool(x) for x in v["seed_fallback"]]
    return len(fb) - sum(fb), len(fb)


def rl_fallback_update(prev, page):
    """-> (state {"book|coin": every seed on the fallback}, one card or None). A book missing from this page keeps its
    last state and gets no card. The first sight of a book already without an agent is news and gets the card."""
    prev = dict(prev or {})
    cur, gone, back = dict(prev), [], []
    for k, v in sorted(rl_states(page).items()):
        n, tot = _rl_agents(v)
        cur[k] = (n == 0)
        if n == 0 and not prev.get(k):
            holds = (u"holds the 30-day momentum position (%s)" % _esc(str(v.get("book_position") or "?"))
                     if v.get("fallback_rule") else u"stays flat")
            gone.append(u"%s: all %d seed agents failed their own check at the last refit. The book %s." % (
                _rl_label(k), tot, holds))
        elif n > 0 and prev.get(k):
            back.append(u"%s: %d of %d seed agents trade again." % (_rl_label(k), n, tot))
    parts = []
    if gone:
        parts.append(u"%s <b>RL: no agent is trading</b>\n%s\nResults there are the fallback's, not the agent's."
                     % (WARN, u"\n".join(gone)))
    if back:
        parts.append(u"%s <b>RL: agent back</b>\n%s" % (OK, u"\n".join(back)))
    return cur, (u"\n\n".join(parts) + u"\n<i>paper only</i>") if parts else None


def _rl_snapshot(states):
    return dict((k, {"agents": _rl_agents(v)[0], "drift": (v.get("input_drift") or {}).get("last_7d_pct")})
                for k, v in states.items())


def rl_health_card(page, prev_week=None, head=u"RL weekly check"):
    """The weekly card (also /rl): per book and coin, agents trading, the week's split, the drift reading."""
    states = rl_states(page)
    if not states:
        return u"%s <b>%s</b>\nThe page has no RL book state yet." % (BRAIN, head)
    prev_week = prev_week or {}
    lines, book0 = [u"%s <b>%s</b>" % (BRAIN, head)], None
    for k, v in sorted(states.items()):
        book, coin = k.split("|")
        if book != book0:
            lines.append(u"<b>%s</b>" % _esc(NAMES.get(book, book)))
            book0 = book
        n, tot = _rl_agents(v)
        was = (prev_week.get(k) or {}).get("agents")
        row = u"%s \u00b7 agents %d/%d%s \u00b7 %s" % (_esc(coin.replace("USDT", "")), n, tot,
                                                      u"" if was is None or was == n else u" (was %d/%d)" % (was, tot),
                                                      _esc(str(v.get("book_position") or "?")))
        wk = (v.get("split") or {}).get("last_7d")
        if isinstance(wk, dict):
            row += u"\n   week: agent %s \u00b7 fallback %s \u00b7 costs %s" % (
                _usd(wk.get("agent_gross_usd") or 0.0), _usd(wk.get("fallback_gross_usd") or 0.0),
                _usd(-(wk.get("costs_usd") or 0.0)))
        d = (v.get("input_drift") or {}).get("last_7d_pct")
        if d is not None:
            d0 = (prev_week.get(k) or {}).get("drift")
            if d0 is None:
                d0 = (v.get("input_drift") or {}).get("week_before_pct")
            flag = u" %s drifting" % WARN if (d > RL_DRIFT_PCT and d0 is not None and d > 2.0 * d0) else u""
            row += u"\n   inputs off-range %.1f%%%s%s" % (d, u"" if d0 is None else u" (was %.1f%%)" % d0, flag)
        lines.append(row)
    lines.append(u"<i>paper only \u00b7 none of these books has passed</i>")
    return u"\n".join(lines)


def rl_weekly_update(prev_models, prev_week, page):
    """-> (models {"book|coin": model id}, the week's snapshot, a card or None). The card goes out when a book starts
    using a new model (the weekly refit reached the books); the first sight only stores the baseline."""
    states = rl_states(page)
    models = dict(prev_models or {})
    cur = dict((k, v.get("model")) for k, v in states.items() if v.get("model"))
    if not cur:
        return models, prev_week, None
    if not prev_models:
        return cur, _rl_snapshot(states), None
    changed = any(prev_models.get(k) is not None and prev_models.get(k) != m for k, m in cur.items())
    models.update(cur)
    if not changed:
        return models, prev_week, None
    return models, _rl_snapshot(states), rl_health_card(page, prev_week, head=u"RL weekly check \u00b7 new models in use")


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
                                 u"daily summary at 08:00 SGT. Send /summary, /health, /calibration or /ranking any time.\n"
                                 u"<i>paper only</i>" % WAVE)
            elif chat != st.get("chat_id"):
                continue                                              # the chat lock: nobody else gets an answer
            elif text.startswith("/summary"):
                _send(tok, chat, summary(_load(PAGE), _load(SCORE), now, st.get("health")))
            elif text.startswith("/health"):
                _send(tok, chat, health_card(st.get("health")))
            elif text.startswith("/calibration"):
                try:
                    _send(tok, chat, calibration_card(calibration_now(now)))
                except Exception as e:
                    _send(tok, chat, u"%s Calibration could not be read (%s)." % (WARN, type(e).__name__))
            elif text.startswith("/signals"):
                _signals_guard("/signals", lambda: _signal_send(tok, st, signals.open_card(
                    signals.load_state(SIGNALS_STATE), now)))
            elif text.startswith("/record"):
                _signals_guard("/record", lambda: _signal_send(tok, st, signals.record_card(
                    SIGNALS_LOG, signals.load_state(SIGNALS_STATE))))
            elif text.startswith("/early"):
                early_command(st, tok)                                # H56 early signal preview (own guard)
            elif text.startswith("/ranking"):
                ranking_command(st, tok, chat, now)                   # the weekly ranking on request (own guard)
            elif text.startswith("/rl"):
                try:                                                  # the RL weekly card on request (state not changed)
                    _send(tok, chat, rl_health_card(_load(PAGE), st.get("rl_week"), head=u"RL check"))
                except Exception as e:
                    _send(tok, chat, u"%s The RL check could not be read (%s)." % (WARN, type(e).__name__))
    page, score = _load(PAGE), _load(SCORE)
    c, v, net = counts(score, page)
    cur = {"c": c, "v": v, "net": net, "refits": refit_marks()}
    ev = events(st, cur, page, now)
    try:                                                              # give-back on open main trades (alert only)
        st["giveback"], cards = giveback_update(st.get("giveback"), page)
        ev.extend(cards)
    except Exception as e:
        print(time.strftime("%Y-%m-%d %H:%M:%S"), "give-back check failed: %s" % type(e).__name__, flush=True)
    try:                                                              # RL health, from the page already in hand
        st["rl_fb"], card = rl_fallback_update(st.get("rl_fb"), page)
        if card:
            ev.append(card)
        st["rl_models"], st["rl_week"], card = rl_weekly_update(st.get("rl_models"), st.get("rl_week"), page)
        if card:
            ev.append(card)
    except Exception as e:                                            # a page shaped unexpectedly never stops the other alerts
        print(time.strftime("%Y-%m-%d %H:%M:%S"), "rl health failed: %s" % type(e).__name__, flush=True)
    try:                                                              # data health, from the page already in hand
        st["health"], gone, back = livecheck.health_update(st.get("health"), (page or {}).get("assets"))
        feeds = health_alert(gone, back)                              # one message, whatever the number of cards
        if feeds:
            ev.append(feeds)
    except Exception as e:                                            # a page shaped unexpectedly never stops the other alerts
        print(time.strftime("%Y-%m-%d %H:%M:%S"), "data health failed: %s" % type(e).__name__, flush=True)
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
            _send(tok, st["chat_id"], summary(page, score, now, st.get("health")))
            st["summary_day"] = day
            week = "%d-W%02d" % tuple(now.isocalendar())[:2]
            if st.get("calib_week") != week:                          # with the first daily summary of each ISO week, once
                st["calib_week"] = week                               # marked before the read: a failed read is not retried every minute
                try:
                    res = calibration_now(now)
                    if any(s.get("n") for s in res["markets"].values()):
                        _send(tok, st["chat_id"], calibration_card(res))
                except Exception as e:
                    print(time.strftime("%Y-%m-%d %H:%M:%S"), "calibration failed: %s" % type(e).__name__, flush=True)
            if st.get("rank_week") != week:                          # the weekly ranking: same first summary of the week, once
                st["rank_week"] = week                                # marked before the build: a failure is not retried
                ranking_weekly(st, tok, st["chat_id"], page, score, now)   # guarded inside
        ev += vault_check(st, tok, st["chat_id"], now)                # guarded inside: it cannot stop anything above
        ev += history_check(st, tok, st["chat_id"], now)              # the daily check's report; guarded inside
        signals_check(st, tok, page, now, recap=due)                  # last, and guarded: it cannot stop anything above
        early_check(st, tok, page, now)                               # H56 early signal preview: after S1, its own guard
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
        _send(tok, st["chat_id"], summary(_load(PAGE), _load(SCORE), health=st.get("health")))
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
