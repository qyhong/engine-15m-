# -*- coding: utf-8 -*-
"""book_view -- b_trail_book.json: the shadow book B trail's history replay and its live forward record in one
file, so the owner can monitor it in one place (engine and book). PAPER ONLY.

    build(page, summary=None, live_trades=(), now=None)   a PURE function: the page the engine already wrote (the
                       dict behind out/live/page.json), the replay's summary (research/out/b_trail_history/summary.json,
                       written by research/b_trail_history.py; None = no history) and the live closed trades
                       (out/live/shadow_trades_b_trail_<ASSET>.csv, as written). No rule, no book, no reading changes.
    write(page, out_dir=...)   b_trail_book.json next to page.json, atomically (temp file + os.replace); also to
                       <MIND15_SETUPS_WEB_DIR>/b_trail_book.json when that variable is set (mode 0644). Into the web
                       folder only, b_trail_history_trades.json: every replay trade as compact arrays, when it is under
                       3 MB (else skipped and said in the log line), rewritten only when trades.csv is newer.

The two records never overlap: the replay stops at each market group's live start (page["shadows"]["markets"][group]
["started_utc"]); here a live trade that opened before its group's start and a replay trade that closed after it are
left out (counted). combined_equity is the replay's month-end equity of all markets, then, from the hand-over point,
the same equity plus the live book's profit since it started (each live market starts again at $10,000), the last
point marked to market.
"""
import csv
import io
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone

from .config import CFG, OUT_DIR, ROOT
from .setups import VERDICTS, _atomic, _clean, _get, _int, _iso, _ms, _num, _px, _r, _say, _text

BOOK = "b_trail"
NAME = "B trail"
SCHEMA = 1
FILE = "b_trail_book.json"
TRADES_FILE = "b_trail_history_trades.json"
WEB_ENV = "MIND15_SETUPS_WEB_DIR"
WEB_MODE = 0o644
LIVE_DIR = os.path.join(OUT_DIR, "live")
HISTORY_DIR = os.path.join(ROOT, "research", "out", "b_trail_history")
LABEL = "history replay with today's engine, in-sample, not a test"
RULE = ("The main book's entries; once a trade is 1R in profit the stop trails the last confirmed 15-minute swing or "
        "2 x ATR(14, 15m), whichever is tighter, and the book re-enters on its own clock.")
START = 10000.0
LAST_N = 50                             # live closed trades carried in the file
MAX_BYTES = 60 * 1024                   # the file stays under this (the oldest live trades shown are dropped first)
WEB_TRADES_MAX = 3 * 1024 * 1024        # the web trades file is written only under this
TRADES_MAX_BYTES = 5 * 1024 * 1024      # a live trade file larger than this is skipped
TRADE_FILE = re.compile(r"^shadow_trades_%s_([A-Z0-9]+)\.csv$" % BOOK)
HIST_COLS = ["market", "side", "time_in", "time_out", "entry", "exit", "stop", "why_out", "pnl_pct", "pnl_usd", "r",
             "fees_usd"]


# ------------------------------------------------------------------ inputs (read only, never raise)
def _groups():
    """{market: group} from the engine's universes."""
    return dict((a, g) for g, assets in CFG.get("universes", ()) for a in assets)


def read_json(path):
    try:
        with io.open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def read_live_trades(live_dir):
    """[(market, row dict)] from every shadow_trades_b_trail_<ASSET>.csv in live_dir, as written (strings)."""
    out = []
    try:
        names = sorted(os.listdir(live_dir))
    except (OSError, TypeError):
        return out
    for name in names:
        m = TRADE_FILE.match(name)
        path = os.path.join(live_dir, name)
        try:
            if not m or os.path.getsize(path) > TRADES_MAX_BYTES:
                continue
            with io.open(path, encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))
        except (OSError, ValueError, csv.Error):
            continue
        out += [(m.group(1), r) for r in rows if isinstance(r, dict)]
    return out


# ------------------------------------------------------------------ the blocks
def _starts(page):
    """{group: live start ms} from page["shadows"]["markets"][group]["started_utc"]."""
    out = {}
    for g, v in (_get(page, "shadows", "markets") or {}).items():
        ms = _ms(v.get("started_utc")) if isinstance(v, dict) else None
        if ms is not None:
            out[g] = ms
    return out


def _side(v):
    return {1.0: "LONG", -1.0: "SHORT"}.get(_num(v)) if not isinstance(v, str) or v.strip() in ("1", "-1", "1.0", "-1.0") \
        else None


def _live_trade(sym, r):
    """One live closed trade (shadow_trades CSV row) for the file, or None for a row that is not a whole trade."""
    if None in r or None in r.values():
        return None
    t_in, t_out, p_in, p_out = (_num(r.get(k)) for k in ("t_in_ms", "t_out_ms", "p_in", "p_out"))
    side = _side(r.get("side"))
    pnl = _num(r.get("pnl_usd"))
    if side is None or None in (t_in, t_out, p_in, p_out, pnl) or t_out < t_in:
        return None
    return {"market": sym, "side": side, "time_in": _iso(int(t_in)), "time_out": _iso(int(t_out)), "entry": _px(p_in),
            "exit": _px(p_out), "stop": _px(r.get("stop0")), "why_out": str(r.get("why_out") or "").strip() or None,
            "pnl_pct": _r(r.get("pnl_pct")), "pnl_usd": _r(pnl), "r": _r(r.get("r_mult")), "fees_usd": _r(r.get("fees_usd")),
            "_t_in": int(t_in), "_t_out": int(t_out)}


def live_rows(trades, starts, groups):
    """The live closed trades, once each, that opened at or after their group's live start, oldest exit first.
    -> (rows, how many were left out as before the start)"""
    keep, early = {}, 0
    for item in trades if isinstance(trades, (list, tuple)) else ():
        try:
            sym, r = item
            t = _live_trade(str(sym), r) if isinstance(r, dict) else None
        except (TypeError, ValueError):
            continue
        if t is None:
            continue
        start = starts.get(groups.get(t["market"]))
        if start is not None and t["_t_in"] < start:
            early += 1
            continue
        keep[(t["market"], t["_t_in"], t["_t_out"])] = t
    rows = sorted(keep.values(), key=lambda t: (t["_t_out"], t["_t_in"], t["market"]))
    return rows, early


def _open(view):
    """The open position of a live market view (shadows.asset_view), or None when flat."""
    st = str((view or {}).get("status") or "FLAT")
    if not st.startswith(("LONG", "SHORT")):
        return None
    return {"side": "LONG" if st.startswith("LONG") else "SHORT", "entry": _px(view.get("entry")),
            "stop": _px(view.get("stop")), "opened_utc": view.get("opened_utc"), "opened_by": view.get("opened_by"),
            "trailing": bool(view.get("trailing")),
            "stop_state": "trailing (the trade has been 1R in profit)" if view.get("trailing") else "the entry stop",
            "unrealized_usd": _r(view.get("unrealized_usd"))}


def live_block(page, rows, starts, groups, early=0):
    views = _get(page, "shadows", "books", BOOK, "assets")
    views = views if isinstance(views, dict) else {}
    markets = [a for a in groups if a in views] + [a for a in views if a not in groups]
    per = {}
    for a in markets + sorted(set(t["market"] for t in rows) - set(markets)):
        mine = [t for t in rows if t["market"] == a]
        wins = sum(1 for t in mine if t["pnl_usd"] > 0)
        v = views.get(a) if isinstance(views.get(a), dict) else {}
        per[a] = {"trades": len(mine), "wins": wins, "won_pct": _r(100.0 * wins / len(mine), 1) if mine else None,
                  "net_usd": _r(sum(t["pnl_usd"] for t in mine)) if mine else 0.0,
                  "status": str(v.get("status") or "FLAT"), "equity_usd": _r(v.get("equity")),
                  "started_utc": _iso(starts.get(groups.get(a))), "open": _open(v)}
    n = sum(p["trades"] for p in per.values())
    wins = sum(p["wins"] for p in per.values())
    eq = [p["equity_usd"] for p in per.values() if p["equity_usd"] is not None]
    rows_sb = _get(page, "scoreboard_all", "rows")
    sb = next((r for r in rows_sb if isinstance(r, dict) and r.get("book") == BOOK and r.get("kind", "shadow") == "shadow"),
              None) if isinstance(rows_sb, list) else None
    verdict = (sb or {}).get("verdict")
    total = {"trades": n, "wins": wins, "won_pct": _r(100.0 * wins / n, 1) if n else None,
             "net_usd": _r(sum(p["net_usd"] for p in per.values())),
             "open_positions": sum(1 for p in per.values() if p["open"]),
             "equity_usd": _r(sum(eq)) if eq else None, "markets": len(per),
             "profit_marked_usd": _r(sum(eq) - START * len(eq)) if eq else None}
    shown = [dict((k, v) for k, v in t.items() if not k.startswith("_")) for t in reversed(rows[-LAST_N:])]
    return {"since_utc": _iso(min(starts.values())) if starts else None, "total": total, "markets": per,
            "verdict": verdict if isinstance(verdict, str) and VERDICTS.fullmatch(verdict) else None,
            "left_out_before_start": int(early), "trades": shown,
            "note": "Forward, on paper, from each market group's start; the book started flat with $10,000 per market."}


def _month_end(m):
    """'2026-10' -> '2026-10-31'."""
    y, mo = int(m[:4]), int(m[5:7])
    nxt = datetime(y + mo // 12, mo % 12 + 1, 1, tzinfo=timezone.utc)
    return (nxt - timedelta(days=1)).strftime("%Y-%m-%d")


def history_block(summary):
    """The replay's totals, years and month-end equity curve, or None when there is no usable summary."""
    b = summary.get(BOOK) if isinstance(summary, dict) else None
    if not isinstance(b, dict) or not isinstance(b.get("total"), dict):
        return None
    t = b["total"]
    months = [m for m in (b.get("months") or []) if isinstance(m, dict) and m.get("month")]
    keys = ("trades", "won_pct", "net_usd", "fees_usd", "best_usd", "worst_usd", "start_usd", "equity_end",
            "max_dd_pct", "max_dd_usd", "markets")
    mkeys = ("trades", "won_pct", "net_usd", "best_usd", "worst_usd", "equity_end", "max_dd_pct", "from_utc", "to_utc")
    main = (summary.get("main") or {}).get("total") or {}
    ho = summary.get("handover_utc") if isinstance(summary.get("handover_utc"), dict) else {}
    return {"label": LABEL, "from_utc": _iso(_ms(t.get("from_utc"))), "to_utc": _iso(_ms(t.get("to_utc"))),
            "handover_utc": dict((g, _iso(_ms(v))) for g, v in ho.items()), "version": summary.get("version"),
            "generated_utc": summary.get("generated_utc"),
            "total": dict((k, t.get(k)) for k in keys),
            "markets": dict((a, dict((k, m.get(k)) for k in mkeys)) for a, m in (b.get("markets") or {}).items()
                            if isinstance(m, dict)),
            "years": [dict((k, y.get(k)) for k in ("year", "trades", "won_pct", "net_usd", "equity_end"))
                      for y in (b.get("years") or []) if isinstance(y, dict)],
            "curve": {"dates": [_month_end(str(m["month"])) for m in months], "equity": [m.get("equity_end") for m in months]},
            "main_book_same_span": {"trades": main.get("trades"), "net_usd": main.get("net_usd"),
                                    "equity_end": main.get("equity_end"), "max_dd_pct": main.get("max_dd_pct")}}


def combined(history, live, rows, now_iso):
    """The replay's month-end curve, the hand-over point, then the live profit added day by day (realized), the last
    point marked to market. None without a history."""
    if not history or not history["curve"]["dates"]:
        return None
    ho_utc = history.get("to_utc")
    ho_day = str(ho_utc or "")[:10]
    base = _num(history["total"].get("equity_end"))
    if base is None:
        return None
    dates, eq, part = [], [], []
    for d, e in zip(history["curve"]["dates"], history["curve"]["equity"]):
        if ho_day and d >= ho_day[:7] + "-01":                    # the hand-over month: its point is the hand-over
            break
        dates.append(d)
        eq.append(e)
        part.append("history")
    dates.append(ho_day or None)
    eq.append(_r(base))
    part.append("handover")
    k = len(dates) - 1
    run, by_day = 0.0, {}
    for t in rows:
        run += t["pnl_usd"]
        by_day[t["time_out"][:10]] = run
    for d in sorted(by_day):
        dates.append(d)
        eq.append(_r(base + by_day[d]))
        part.append("live")
    marked = (live.get("total") or {}).get("profit_marked_usd")
    dates.append(now_iso[:10])
    eq.append(_r(base + (marked if marked is not None else run)))
    part.append("live_marked" if marked is not None else "live")
    return {"dates": dates, "equity": eq, "part": part, "handover_index": k, "handover_utc": ho_utc,
            "note": "Month-end equity of the replay (all markets), then from the hand-over the replay's last equity plus "
                    "the live book's profit since its start (realized by exit day; the last point marked to market)."}


def build(page, summary=None, live_trades=(), now=None):
    if not isinstance(page, dict) or not isinstance(_get(page, "shadows", "books", BOOK, "assets"), dict):
        raise ValueError("the page has no %s book" % BOOK)
    gen = now or page.get("generated_utc") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    groups = _groups()
    starts = _starts(page)
    rows, early = live_rows(live_trades, starts, groups)
    hist = history_block(summary)
    live = live_block(page, rows, starts, groups, early)
    doc = {"generated_utc": gen, "schema": SCHEMA, "book": BOOK, "name": NAME, "rule": RULE,
           "note": "Paper only. Not advice.", "history": hist, "live": live,
           "combined_equity": combined(hist, live, rows, str(gen))}
    doc = _clean(doc)
    while len(json.dumps(doc, allow_nan=False)) > MAX_BYTES and doc["live"]["trades"]:
        doc["live"]["trades"] = doc["live"]["trades"][:-5]       # the oldest shown first
    return doc


# ------------------------------------------------------------------ the web trades file
def history_trades_doc(csv_path, starts=None, groups=None):
    """All replay trades as compact arrays (HIST_COLS); a trade that closed after its group's live start is left out."""
    starts, groups = starts or {}, groups or _groups()
    rows, late = [], 0
    with io.open(csv_path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(line for line in fh if not line.startswith("#")):
            end = starts.get(groups.get(r.get("market")))
            t_out = _ms(r.get("time_out"))
            if end is not None and t_out is not None and t_out > end:
                late += 1
                continue
            rows.append([r.get("market"), r.get("side"), r.get("time_in"), r.get("time_out"), _px(r.get("entry")),
                         _px(r.get("exit")), _px(r.get("stop")), r.get("why_out"), _r(r.get("pnl_pct")),
                         _r(r.get("pnl_usd")), _r(r.get("r"), 3), _r(r.get("fees_usd"))])
    return {"schema": SCHEMA, "book": BOOK, "label": LABEL, "columns": HIST_COLS, "rows": rows, "left_out_after_start": late}


def _web_trades(hist_dir, web_dir, starts, log):
    """b_trail_history_trades.json into the web folder only. -> a short status word for the log line."""
    src = os.path.join(hist_dir, "trades.csv")
    if not os.path.exists(src):
        return "no history trades"
    dst = os.path.join(web_dir, TRADES_FILE)
    if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
        return "history trades current"
    text = _text(json.dumps(_clean(history_trades_doc(src, starts)), allow_nan=False, separators=(",", ":")))
    if len(text.encode("utf-8")) >= WEB_TRADES_MAX:
        return "history trades skipped (%.1f MB, over 3 MB)" % (len(text.encode("utf-8")) / 2.0 ** 20)
    _atomic(dst, text, mode=WEB_MODE)
    return "history trades %.0f KB" % (len(text.encode("utf-8")) / 1024.0)


# ------------------------------------------------------------------ the file
def write(page, out_dir=None, live_dir=None, hist_dir=None, now=None, log=None):
    """Write b_trail_book.json (and its web copy). page: the page dict, or the path of page.json (out_dir then
    defaults to its folder). -> {"path", "web_path", "history": bool, "live_trades": n, "web_trades": status or None},
    or None when there is nothing to write: no page file, or a page without the B trail book (no file, no line;
    the same quiet None as stocks.maybe_run). A page that cannot be read raises."""
    if not isinstance(page, dict):
        src = os.path.abspath(str(page))
        if not os.path.exists(src):
            return None
        out_dir = out_dir or os.path.dirname(src)
        with open(src, encoding="utf-8") as fh:
            page = json.load(fh)
    if not isinstance(page, dict) or not isinstance(_get(page, "shadows", "books", BOOK, "assets"), dict):
        return None
    out_dir = out_dir or LIVE_DIR
    hist_dir = hist_dir or HISTORY_DIR
    summary = read_json(os.path.join(hist_dir, "summary.json"))
    doc = build(page, summary=summary, live_trades=read_live_trades(live_dir or LIVE_DIR), now=now)
    text = _text(json.dumps(doc, allow_nan=False))
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, FILE)
    _atomic(path, text)
    web, web_dir, wt = None, (os.environ.get(WEB_ENV) or "").strip(), None
    if web_dir:
        try:
            _atomic(os.path.join(web_dir, FILE), text, mode=WEB_MODE)
            web = os.path.join(web_dir, FILE)
        except Exception as e:
            _say(log, "b_trail book: web copy not written (%r)" % (e,))
        if web and doc["history"] is not None:
            try:
                wt = _web_trades(hist_dir, web_dir, _starts(page), log)
            except Exception as e:
                wt = "history trades not written (%r)" % (e,)
    return {"path": path, "web_path": web, "history": doc["history"] is not None,
            "history_trades": _int(_get(doc, "history", "total", "trades")), "live_trades": doc["live"]["total"]["trades"],
            "web_trades": wt, "bytes": len(text.encode("utf-8"))}


def line(info):
    """The step log's one line."""
    return "b_trail book: history %s, live %d trades -> %s%s%s" % (
        "%d trades" % info["history_trades"] if info.get("history") else "none", info["live_trades"], info["path"],
        " (web copy: %s)" % info["web_path"] if info.get("web_path") else "",
        "; %s" % info["web_trades"] if info.get("web_trades") else "")
