# -*- coding: utf-8 -*-
"""setups -- setups.json: one clear call per market for the subscribers' "Setups" page. PAPER ONLY.

The page is built elsewhere; this module only supplies its data file, written beside page.json after every
step. ONE voice per market: LONG, SHORT or FLAT, with the entry, the stop and two targets. The voice is the
paper book `b_targets` (shadows.py: the main book's entries, half off at Target 1, the rest at Target 2, the
stop to the entry after Target 1), the source of the signal book S1 (research/HYPOTHESES.md, H53). Where that
book is flat the market is FLAT, whatever any other book holds: no second opinion is ever shown.

    build(page, s1=None, now=None)   a PURE function of the page the engine already wrote (the dict behind
                                     out/live/page.json) and the S1 record (load_s1): no new rule, no change to
                                     any book, no price the page does not carry. The only arithmetic is named
                                     in _market: the move since the entry in %, the reward to risk from the
                                     current price, and the distance to the current stop.
    write(page, out_dir=...)         setups.json next to page.json, atomically (temp file + os.replace); also to
                                     <MIND15_SETUPS_WEB_DIR>/setups.json when that variable is set (mode 0644).
                                     It writes setup_events.json the same way first; either file failing never
                                     stops the other (one log line each).

Added to setups.json (schema 1, keys added only):
    markets[].closes / closes_step_min / closes_end_utc   the closes of the engine's own 15-minute bars
            (data/<asset>_15m.csv, read from the tail only), up to 96, oldest first, ending at the bar the page's
            price belongs to (price_bar_utc is that bar's CLOSE time, so closes_end_utc == price_bar_utc when the
            file holds it; the metals and energy markets that step one bar behind follow the page the same way).
            A bar file that cannot be read keeps the previous setups.json's closes for that market, else null.
    markets[].held_share   (20 Nov 2026) the share of the setup's starting size the book still holds: 1.0 until Target 1
            is taken, then 0.5 (shadows.held_share: qty / qty0). null when FLAT or when the book's view does not carry it.
    closed_setups   the setups book's last 30 closed trades across all markets, newest first by exit time, from
            out/live/shadow_trades_b_targets_<ASSET>.csv. opened_utc / closed_utc are the open times of the fill
            bar and of the exit bar (t_in_ms / t_out_ms, as the market's own opened_utc). `exit` is p_out, which
            shadows.run already books as the quantity-weighted average of both parts when Target 1 was taken.
build_events(log) -> setup_events.json: the followable S1 record (signals_log.jsonl) as coded events, newest first.

Nothing here places an order, opens a socket or changes a file other than setups.json and setup_events.json. Every
text in the files comes from a short fixed list (codes, names, times; no reading, no research wording, no book
name) and passes the page's own wording rule (export.py: the forecast model is never named).
"""
import csv
import io
import json
import math
import os
import re
import time
from datetime import datetime, timedelta, timezone

from .config import CFG, DATA_DIR, OUT_DIR

BOOK = "b_targets"                      # the one voice (shadows.py); fixed by H53
SCHEMA = 1
NOTE = "Experimental model. Paper only. Not advice."
BOOK_NAME = "Setups"
BOOK_RULE = "half at target 1, rest at target 2, stop to entry after target 1"
FILE = "setups.json"
WEB_ENV = "MIND15_SETUPS_WEB_DIR"       # set on the server: the folder the site serves; unset = no web copy
WEB_MODE = 0o644
LIVE_DIR = os.path.join(OUT_DIR, "live")
S1_DIR = DATA_DIR                       # signals_log.jsonl and signals_state.json (signals.py keeps them)
LOOK_AHEAD = 96 * 10                    # next_open_utc: the 15-minute slots looked at (ten days)
# the scoreboard's own verdict sentences (reports._stats), whole; any other text is left out (null)
VERDICTS = re.compile(r"no trades yet|too few trades to judge \(\d+ of \d+\)|ahead: even the low end of the range is positive"
                      r"|behind: even the high end of the range is negative|undecided: the range includes zero")
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
BAR_MS = int(CFG.get("bar_ms", 900000))
BARS_DIR = DATA_DIR                     # <asset>_15m.csv: the engine's own bars (data.py; ts_ms = the bar's open)
TRADES_DIR = LIVE_DIR                   # shadow_trades_b_targets_<ASSET>.csv (shadows.journal_trades)
CLOSES_N = 96                           # closes per market (one day of 15-minute bars)
TAIL_LINES = 200                        # the bar file is read from its end: at most this many lines ...
TAIL_BYTES = 32768                      # ... out of at most this many bytes
CLOSED_N = 30                           # closed_setups: the last closed trades shown
TRADES_MAX_BYTES = 5 * 1024 * 1024      # a trade file larger than this is skipped
TRADE_FILE = re.compile(r"^shadow_trades_%s_([A-Z0-9]+)\.csv$" % BOOK)
# why_out as shadows.run writes it for this book (parts taken earlier come first, joined by "+")
WHY_OUT = {"T1+T2": "TARGET_2", "STOP": "STOP", "T1+STOP_BE": "T1_THEN_ENTRY"}
FLIPS = ("FLIP", "FLIP_MKT", "FLIP_LMT")                        # a flip (FLIP_* are H3's limit-flip words)
EXITS = ("STEP_ASIDE",)                                         # the model's own exit to flat
# setup_events.json
EVENTS_FILE = "setup_events.json"
EVENTS_SCHEMA = 1
EVENTS_N = 100
EV_TYPE = {"signal": "NEW_SETUP", "filled": "ENTRY_FILLED", "no_fill": "NO_FILL", "t1": "TARGET_1", "closed": "CLOSED"}
NO_FILL_CODE = {"window": "WINDOW", "stop": "STOP_FIRST", "target": "TARGET_FIRST", "model": "MODEL_CLOSED"}
CLOSED_CODE = {"t2": "TARGET_2", "stop": "STOP", "stop_be": "T1_THEN_ENTRY", "model": "MODEL_CLOSED"}


# ------------------------------------------------------------------ small helpers
def _num(v):
    """A finite number, or None (NaN, infinity, text, true/false and nothing are all None)."""
    if isinstance(v, bool):
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _r(v, d=2):
    v = _num(v)
    return None if v is None else round(v, d) + 0.0               # (+ 0.0: never "-0.0")


def _int(v):
    v = _num(v)
    return 0 if v is None else int(v)


def _px(v):
    """A price as the page rounds the book's levels (shadows._px): 5 decimals under 100, 3 under 1000, else 2."""
    v = _num(v)
    return None if v is None else round(v, 5 if abs(v) < 100 else 3 if abs(v) < 1000 else 2) + 0.0


def _text(s):
    """The page's wording rule (export.rewrite_merged): the forecast model is never named."""
    return None if s is None else str(s).replace("Kronos", "AlphaPrediction AI").replace("kronos", "candle_forecast")


def _verdict(v):
    return v if isinstance(v, str) and VERDICTS.fullmatch(v) else None


def _ms(t):
    """Epoch ms of a time: a datetime (naive = UTC), '2026-11-17 03:15' (the page), '2026-11-17T03:42:19Z'
    (generated_utc, the S1 log) or epoch ms. None if it is not a time."""
    if t is None or isinstance(t, bool):
        return None
    if isinstance(t, datetime):
        t = t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t.astimezone(timezone.utc)
        return int(round((t - _EPOCH).total_seconds() * 1000))
    if isinstance(t, (int, float)):
        return int(t) if math.isfinite(t) else None
    s = str(t).strip().replace("T", " ")
    for fmt, cut in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d %H:%M", 16)):
        try:
            d = datetime.strptime(s[:cut], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        return int((d - _EPOCH).total_seconds() * 1000)
    return None


def _iso(ms):
    return None if ms is None else (_EPOCH + timedelta(milliseconds=int(ms))).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(d, *keys):
    """d[k1][k2]... through dicts and lists, or None."""
    for k in keys:
        try:
            d = d[k]
        except (KeyError, IndexError, TypeError):
            return None
    return d


def _clean(x):
    """Valid JSON only: a number that is not finite becomes null; every text passes the wording rule."""
    if isinstance(x, dict):
        return dict((k, _clean(v)) for k, v in x.items())
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    if isinstance(x, str):
        return _text(x)
    return x


# ------------------------------------------------------------------ what the engine wrote (read only)
def book_views(page):
    """{market: the b_targets view} from the page (shadows -> books -> b_targets -> assets), or None if it is not there."""
    v = _get(page, "shadows", "books", BOOK, "assets")
    return v if isinstance(v, dict) else None


def _order(page, assets):
    """The markets in the page's own order: group by group (page["markets"]), then any other market it shows."""
    out = []
    groups = page.get("markets") if isinstance(page.get("markets"), dict) else {}
    for members in groups.values():
        out += [a for a in (members if isinstance(members, (list, tuple)) else []) if a not in out]
    return out + [a for a in assets if a not in out]


def _group(page, sym, asset):
    g = (asset or {}).get("market_group")
    if g:
        return g
    groups = page.get("markets") if isinstance(page.get("markets"), dict) else {}
    return next((k for k, members in groups.items() if isinstance(members, (list, tuple)) and sym in members), None)


def market_hours(sym, now_ms):
    """(market_open, next_open_utc) at that moment, by the engine's own trading-hours rule: crypto never shuts;
    the others ask market_calendar.is_open (extdata's weekly hours and daily breaks, plus the exchange holidays
    and early closes of 2026-2027: NYSE for the S&P, CME for gold, silver and WTI, ICE for Brent; USDJPY has
    none). next_open_utc is the first 15-minute slot at which that same rule says open, when the market is shut
    now. (None, None) when it cannot be told."""
    if now_ms is None:
        return None, None
    try:
        if sym in CFG.get("crypto", ()):
            return True, None
        from . import extdata, market_calendar
        if sym not in extdata.MARKETS:
            return None, None
        import pandas as pd
        t = pd.Timestamp(int(now_ms), unit="ms", tz="UTC")
        if market_calendar.is_open(sym, t):
            return True, None
        idx = pd.date_range(t.ceil("15min"), periods=LOOK_AHEAD, freq="15min")
        k = next((i for i, x in enumerate(market_calendar.open_mask(sym, idx)) if x), None)
        return False, None if k is None else _iso(int(round(idx[k].timestamp() * 1000)))
    except Exception:
        return None, None


# ------------------------------------------------------------------ the S1 record (signals.py), read only
def load_s1(data_dir=None):
    """{"scoreboard": signals.scoreboard over data/signals_log.jsonl, "state": data/signals_state.json}; a part
    that is missing or cannot be read is None. Never raises."""
    d = data_dir or S1_DIR
    out = {"scoreboard": None, "state": None}
    try:
        from . import signals
        p = os.path.join(d, "signals_log.jsonl")
        if os.path.exists(p):
            out["scoreboard"] = signals.scoreboard(signals.read_log(p))
    except Exception:
        out["scoreboard"] = None
    try:
        from . import signals
        out["state"] = signals.load_state(os.path.join(d, "signals_state.json"))
    except Exception:
        out["state"] = None
    return out


def _followable(s1):
    """The record a subscriber can really get (H53's followable rules): numbers null and counts 0 when there is
    no signal yet or the log could not be read."""
    out = {"live_since_utc": None, "signals": 0, "filled": 0, "fill_rate_pct": None, "closed": 0, "won_pct": None,
           "net_pct": None, "net_r": None, "verdict": None}
    s1 = s1 if isinstance(s1, dict) else {}
    sb, st = s1.get("scoreboard"), s1.get("state")
    sb, st = sb if isinstance(sb, dict) else None, st if isinstance(st, dict) else {}
    out["live_since_utc"] = _iso(_ms((sb or {}).get("live_since") or st.get("live_since")))
    if sb is None:
        return out
    f = sb.get("follow") if isinstance(sb.get("follow"), dict) else {}
    sent, closed = _int(sb.get("sent")), _int(f.get("n"))
    out.update(signals=sent, filled=_int(sb.get("filled")), closed=closed, verdict=_verdict(sb.get("verdict")),
               fill_rate_pct=_r(sb.get("fill_rate_pct")) if sent else None)
    if closed:
        out.update(won_pct=_r(f.get("won_pct")), net_pct=_r(f.get("net_pct")), net_r=_r(f.get("net_r")))
    return out


def _waiting(state, now_ms):
    """{(market, opened 'YYYY-MM-DD HH:MM'): valid-until ms} of the signals still waiting inside their entry window."""
    out = {}
    signals_open = state.get("open") if isinstance(state, dict) else None
    for sig in signals_open.values() if isinstance(signals_open, dict) else ():
        try:
            until = int(sig["valid_until_ms"])
            if sig["follow"]["state"] == "WAITING" and now_ms is not None and now_ms < until:
                out[(sig["asset"], str(sig["opened_utc"])[:16].replace("T", " "))] = until
        except (KeyError, TypeError, ValueError):
            continue
    return out


# ------------------------------------------------------------------ the engine's bars (read only, the tail only)
def bar_path(bars_dir, sym):
    return os.path.join(bars_dir, "%s_15m.csv" % str(sym).lower())


def read_closes(path):
    """[(bar open ms, close)] of the last whole bars of an engine bar file (at most TAIL_LINES lines out of the last
    TAIL_BYTES bytes), oldest first; None when the read cannot be trusted: missing, empty, or any line that is not a
    whole bar (the engine may be rewriting the file). A failed read is never 'no bars'. Never raises."""
    try:
        size = os.path.getsize(path)
        if size <= 0:
            return None
        start = max(0, size - TAIL_BYTES)
        with io.open(path, "rb") as fh:
            fh.seek(start)
            raw = fh.read(size - start)
    except (OSError, ValueError):
        return None
    lines = raw.split(b"\n")
    if start:
        lines = lines[1:]                                         # the first line of a tail may be cut
    if not raw.endswith(b"\n"):
        lines = lines[:-1]                                        # the last line may still be being written
    lines = [ln.strip() for ln in lines if ln.strip()][-TAIL_LINES:]
    out = []
    for ln in lines:
        if ln.startswith(b"ts_ms"):
            continue
        f = ln.split(b",")
        try:
            ts, c = int(f[0]), float(f[4])
        except (ValueError, IndexError):
            return None
        if ts % BAR_MS or not (math.isfinite(c) and c > 0) or (out and ts <= out[-1][0]):
            return None
        out.append((ts, c))
    return out or None


def _closes(rows, end_ms, prev):
    """(closes, closes_end_utc) for one market: the last CLOSES_N closes of bars that have closed by end_ms (the
    page's price bar; None = the last bars there are), else the previous file's own, else (None, None)."""
    if rows:
        sel = [(ts, c) for ts, c in rows if end_ms is None or ts + BAR_MS <= end_ms][-CLOSES_N:]
        if sel:
            return [_px(c) for _ts, c in sel], _iso(sel[-1][0] + BAR_MS)
    prev = prev if isinstance(prev, dict) else {}
    old, end = prev.get("closes"), _ms(prev.get("closes_end_utc"))
    if isinstance(old, list) and old and all(_num(x) is not None for x in old):
        return [_px(x) for x in old[-CLOSES_N:]], _iso(end)
    return None, None


# ------------------------------------------------------------------ the setups book's closed trades (read only)
def read_trades(trades_dir):
    """[(market, row dict)] from every shadow_trades_b_targets_<ASSET>.csv in trades_dir, as written (strings).
    A file larger than TRADES_MAX_BYTES or that cannot be read is skipped. Never raises."""
    out = []
    try:
        names = sorted(os.listdir(trades_dir))
    except (OSError, TypeError):
        return out
    for name in names:
        m = TRADE_FILE.match(name)
        path = os.path.join(trades_dir, name)
        try:
            if not m or os.path.getsize(path) > TRADES_MAX_BYTES:
                continue
            with io.open(path, encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))
        except (OSError, ValueError, csv.Error):
            continue
        out += [(m.group(1), r) for r in rows if isinstance(r, dict)]
    return out


def why_code(why):
    """The page's code for a raw why_out (see WHY_OUT, FLIPS, EXITS); anything else is OTHER."""
    w = str(why or "").strip()
    if w in WHY_OUT:
        return WHY_OUT[w]
    t1, tail = (True, w[3:]) if w.startswith("T1+") else (False, w)
    if tail in FLIPS:
        return "T1_THEN_FLIP" if t1 else "FLIP"
    if tail in EXITS:
        return "T1_THEN_EXIT" if t1 else "EXIT"
    return "OTHER"


def _closed_trade(sym, r):
    """One closed-setup entry from a trade row, or None for a row that is not a whole closed trade."""
    if None in r or None in r.values():                           # a row with too many or too few fields
        return None
    t_in, t_out, p_in, p_out, pct = (_num(r.get(k)) for k in ("t_in_ms", "t_out_ms", "p_in", "p_out", "pnl_pct"))
    side = {1.0: "LONG", -1.0: "SHORT"}.get(_num(r.get("side")))
    if side is None or None in (t_in, t_out, p_in, p_out, pct) or t_out < t_in or p_in <= 0 or p_out <= 0:
        return None
    why = str(r.get("why_out") or "").strip()
    return {"symbol": sym, "side": side, "opened_utc": _iso(int(t_in)), "closed_utc": _iso(int(t_out)),
            "entry": _px(p_in), "exit": _px(p_out), "stop": _px(r.get("stop0")), "target_1": _px(r.get("target_1")),
            "target_2": _px(r.get("target_2")), "t1_taken": why.startswith("T1"), "why_out": why_code(why),
            "result_pct": _r(pct), "result_usd": _r(r.get("pnl_usd")), "r": _r(r.get("r_mult"))}


def _closed_setups(trades):
    """The last CLOSED_N closed trades over every market, newest first by exit time (a row written twice counts once)."""
    keep = {}
    for item in trades if isinstance(trades, (list, tuple)) else ():
        try:
            sym, r = item
            t = _closed_trade(str(sym), r) if isinstance(r, dict) else None
        except (TypeError, ValueError):
            continue
        if t is not None:
            keep[(t["symbol"], t["opened_utc"], t["closed_utc"])] = t
    rows = sorted(keep.values(), key=lambda t: (t["closed_utc"], t["opened_utc"], t["symbol"]), reverse=True)
    return rows[:CLOSED_N]


# ------------------------------------------------------------------ the blocks
def _rr(sgn, price, stop, target):
    """Reward to risk FROM THE CURRENT PRICE, in the trade's direction; None when a number is missing or the
    price is already at or beyond the target or the stop."""
    if None in (price, stop, target):
        return None
    reward, risk = sgn * (target - price), sgn * (price - stop)
    return None if reward <= 0 or risk <= 0 else _r(reward / risk)


def _share(v):
    """held_share as the book's view gives it: a number in (0, 1], else None (never guessed from t1_taken)."""
    v = _num(v)
    return round(v, 6) if v is not None and 0 < v <= 1 else None


def _market(page, sym, asset, view, waiting, now_ms, bars=None, prev=None):
    asset = asset if isinstance(asset, dict) else {}
    view = view if isinstance(view, dict) else {}
    group = _group(page, sym, asset)
    side = view.get("status") if view.get("status") in ("LONG", "SHORT") else "FLAT"     # "WAITING ..." is FLAT
    sgn = {"LONG": 1, "SHORT": -1}.get(side, 0)
    price, bar = _num(asset.get("price")), _ms(asset.get("time"))
    if price is None:                                             # the book's own mark and the close it has reached
        price, bar = _num(_get(page, "shadows", "markets", group, "assets", sym, "price")), None
    if bar is None:
        bar = _ms(_get(page, "shadows", "markets", group, "as_of_utc"))
    is_open, next_open = market_hours(sym, now_ms)
    m = {"symbol": sym, "short": asset.get("short") or sym, "group": group, "side": side,
         "entry": None, "stop": None, "target_1": None, "target_2": None, "t1_taken": False, "held_share": None,
         "opened_utc": None,
         "price": _px(price), "price_bar_utc": _iso(bar), "unrealized_usd": None, "unrealized_pct": None,
         "market_open": is_open, "next_open_utc": next_open, "edge_with_position_pts": None,
         "hit_24h_30d_pct": _r(_get(page, "horizon_skill", "markets", sym, "24h", "d30", 0)),
         "rr_now_t1": None, "rr_now_t2": None, "stop_dist_now_pct": None,
         "entry_window_open": False, "entry_valid_until_utc": None,
         "closed": _int(view.get("trades")), "wins": _int(view.get("wins")), "realized_usd": _r(view.get("realized_usd"))}
    closes, closes_end = _closes(bars, bar, prev)                 # the bars up to the one the price belongs to
    m.update(closes=closes, closes_step_min=BAR_MS // 60000, closes_end_utc=closes_end)
    if not sgn:
        return m
    entry, t1, t2 = _num(view.get("entry")), _num(view.get("target_1")), _num(view.get("target_2"))
    taken = bool(view.get("t1_taken"))
    stop = entry if taken and entry is not None else _num(view.get("stop"))   # after Target 1 the stop is the entry
    opened = _ms(view.get("opened_utc"))
    edge = _num(asset.get("edge_pts"))                            # P(up) - P(down), in points: positive favours LONG
    until = waiting.get((sym, str(view.get("opened_utc"))[:16].replace("T", " ")))
    m.update(entry=_px(entry), stop=_px(stop), target_1=_px(t1), target_2=_px(t2), t1_taken=taken, opened_utc=_iso(opened),
             held_share=_share(view.get("held_share")),
             unrealized_usd=_r(view.get("unrealized_usd")),
             unrealized_pct=_r(100.0 * sgn * (price - entry) / entry) if price is not None and entry else None,
             edge_with_position_pts=None if edge is None else _r(sgn * edge),
             rr_now_t1=None if taken else _rr(sgn, price, stop, t1), rr_now_t2=_rr(sgn, price, stop, t2),
             entry_window_open=until is not None, entry_valid_until_utc=_iso(until))
    if price and stop is not None and sgn * (price - stop) > 0:
        m["stop_dist_now_pct"] = _r(100.0 * sgn * (price - stop) / price)
    return m


def _book(page, views):
    """The book over every market shown: closed trades, wins, realized net and marked equity summed from its
    per-market views (so the totals are the sum of the rows below), the verdict from the forward scoreboard."""
    vs = [v for v in views if isinstance(v, dict)]
    closed, won = sum(_int(v.get("trades")) for v in vs), sum(_int(v.get("wins")) for v in vs)
    net = [_num(v.get("realized_usd")) for v in vs]
    eq = [_num(v.get("equity")) for v in vs]
    rows = _get(page, "scoreboard_all", "rows")
    row = next((r for r in rows if isinstance(r, dict) and r.get("book") == BOOK and r.get("kind", "shadow") == "shadow"),
               None) if isinstance(rows, list) else None
    return {"name": BOOK_NAME, "rule": BOOK_RULE, "closed": closed, "won": won,
            "won_pct": _r(100.0 * won / closed) if closed else None,
            "net_usd": _r(sum(x for x in net if x is not None)) if any(x is not None for x in net) else None,
            "equity_usd": _r(sum(x for x in eq if x is not None)) if any(x is not None for x in eq) else None,
            "verdict": _verdict((row or {}).get("verdict"))}


def _learning(page):
    """The engine's own direction hit rates over 7 and 30 days, all markets (the page's learning block);
    n = the calls graded up or down that the rate is a share of."""
    out = {}
    for key, span in (("7d", "last_7_days"), ("30d", "last_30_days")):
        d = _get(page, "learning", span)
        d = d if isinstance(d, dict) else {}
        right, wrong = _num(d.get("right")), _num(d.get("wrong"))
        out["hit_%s_pct" % key] = _r(d.get("hit_pct"))
        out["n_%s" % key] = None if right is None or wrong is None else int(right + wrong)
    return out


def _prev_markets(prev):
    """{market: its entry} of the previous setups.json (for the closes it held), or {}."""
    ms = prev.get("markets") if isinstance(prev, dict) else None
    return dict((m.get("symbol"), m) for m in ms if isinstance(m, dict)) if isinstance(ms, list) else {}


def build(page, s1=None, now=None, bars=None, trades=None, prev=None):
    """The Setups file as a dict. page: the engine's page (page.json); s1: load_s1()'s record, or None (no
    record: zeros and nulls); now: the moment the trading hours and the entry windows are asked about (a
    datetime, an ISO time or epoch ms; default: the page's own generated_utc, so the same page always gives the
    same file). bars: {market: read_closes() of its bar file, or None when it could not be read}; trades:
    read_trades(); prev: the previous setups.json as a dict (its closes stand in for a bar file that cannot be
    read). Raises ValueError when the page has no view of the book at all: a file that would call every
    market FLAT for want of data is never written."""
    if not isinstance(page, dict):
        raise ValueError("the page is not a JSON object")
    views = book_views(page)
    if views is None:
        raise ValueError("the page has no %s view" % BOOK)
    assets = page.get("assets") if isinstance(page.get("assets"), dict) else {}
    order = _order(page, assets)
    if not order:
        raise ValueError("the page lists no market")
    now_ms = _ms(now) if now is not None else _ms(page.get("generated_utc"))
    waiting = _waiting((s1 or {}).get("state") if isinstance(s1, dict) else None, now_ms)
    bars, old = bars if isinstance(bars, dict) else {}, _prev_markets(prev)
    return _clean({"generated_utc": page.get("generated_utc"), "version": page.get("version"), "schema": SCHEMA,
                   "note": NOTE, "book": _book(page, [views.get(a) for a in order]), "followable": _followable(s1),
                   "learning": _learning(page),
                   "markets": [_market(page, a, assets.get(a), views.get(a), waiting, now_ms, bars.get(a), old.get(a))
                               for a in order],
                   "closed_setups": _closed_setups(trades)})


# ------------------------------------------------------------------ setup_events.json (the followable S1 record)
def _stamp(ms):
    return None if ms is None else (_EPOCH + timedelta(milliseconds=int(ms))).strftime("%Y%m%dT%H%M")


def build_events(log_events, generated_utc=None, live_since=None):
    """setup_events.json as a dict, a PURE function of the S1 log (signals.read_log: one line per (signal, kind),
    in the order written). Kinds kept: signal -> NEW_SETUP, filled -> ENTRY_FILLED, no_fill -> NO_FILL, t1 ->
    TARGET_1, closed -> CLOSED. Left out: start and seen_not_signalled (no signal), book_closed (the book's own
    record, not the followable one) and model_exit (an alert while the trade is still open: its CLOSED with
    MODEL_CLOSED follows at the next bar's open). `utc` is the log's `t` for every event: the moment the engine
    recorded it and sent the alert; `bar_utc` is the open of the bar the event happened in, when it is a bar's.
    The levels are the signal's own, as sent. id = <signal_id>:<type>; no kind repeats for one signal, so a
    suffix (:<bar or event time>, then :2, :3 ...) is added only when a signal id comes back for another position
    (the ids carry no year, and a new state file restarts the day's counter). The ids are given in log order over
    the whole log before the newest EVENTS_N are kept: the same log always gives the same ids.
    live_since: the log's first start line, else this argument (the state file's)."""
    rows = [e for e in (log_events or ()) if isinstance(e, dict)]
    sigs = {}
    for e in rows:
        if e.get("ev") == "signal" and e.get("k") not in sigs:
            sigs[e.get("k")] = e
    live_since = next((e.get("live_since") for e in rows if e.get("ev") == "start"), None) or live_since
    owner, taken, out = {}, set(), []
    for n, e in enumerate(rows):
        typ, sid = EV_TYPE.get(e.get("ev")), e.get("id")
        if typ is None or not isinstance(sid, str) or not sid.strip():
            continue
        k, sig = e.get("k"), sigs.get(e.get("k")) or {}
        t_ms, bar_ms = _ms(e.get("t")), _ms(e.get("bar_utc"))
        base = "%s:%s" % (sid, typ)
        eid, when = base, _stamp(bar_ms if bar_ms is not None else t_ms) or str(n)
        if owner.setdefault(base, k) != k or base in taken:
            eid = "%s:%s" % (base, when)
        j = 2
        while eid in taken:
            eid, j = "%s:%s:%d" % (base, when, j), j + 1
        taken.add(eid)
        sym = e.get("asset") or sig.get("asset") or (str(k).split("|")[0] if k else None)
        why = e.get("reason") if typ == "NO_FILL" else e.get("why") if typ == "CLOSED" else None
        out.append((t_ms, n, {
            "id": eid, "signal_id": sid, "type": typ, "symbol": sym,
            "side": {1: "LONG", -1: "SHORT"}.get(_int(sig.get("side"))),
            "utc": _iso(t_ms), "bar_utc": _iso(bar_ms),
            "entry": _px(sig.get("entry")), "stop": _px(sig.get("stop")),
            "target_1": _px(sig.get("t1")), "target_2": _px(sig.get("t2")),
            "price": _px(e.get("px")) if typ in ("ENTRY_FILLED", "TARGET_1", "CLOSED") else None,
            "entry_valid_until_utc": _iso(_ms(sig.get("valid_until_utc"))) if typ == "NEW_SETUP" else None,
            "result_pct": _r(e.get("pct")) if typ == "CLOSED" else None,
            "r": _r(e.get("r")) if typ == "CLOSED" else None,
            "reason_code": (NO_FILL_CODE if typ == "NO_FILL" else CLOSED_CODE).get(why) if why is not None else None}))
    out.sort(key=lambda x: (x[0] if x[0] is not None else -1, x[1]), reverse=True)
    return _clean({"generated_utc": generated_utc, "schema": EVENTS_SCHEMA, "live_since_utc": _iso(_ms(live_since)),
                   "events": [x[2] for x in out[:EVENTS_N]]})


def load_events(data_dir=None):
    """(the S1 log through signals' own reader, live_since from the state file or None). A log that is not there
    is no event; a state that cannot be read is no live_since."""
    from . import signals
    d = data_dir or S1_DIR
    p = os.path.join(d, "signals_log.jsonl")
    events = signals.read_log(p) if os.path.exists(p) else []
    try:
        st = signals.load_state(os.path.join(d, "signals_state.json"))
    except Exception:
        st = None
    return events, st.get("live_since") if isinstance(st, dict) else None


# ------------------------------------------------------------------ landing.json (open: no levels of open setups)
# Served WITHOUT a session (the public landing page). Owner's rule there: "Counts only, no percent": no percent return
# and no money figure anywhere in this file; no entry, stop or target of an OPEN setup.
LANDING_FILE = "landing.json"
NEAR_FRAC = 0.35                         # "near the entry": within this share of the entry-to-stop distance


def _state(m):
    """new / near / running / flat, the Setups page's own rule (codes only)."""
    side = m.get("side")
    if side not in ("LONG", "SHORT"):
        return "flat"
    if m.get("entry_window_open"):
        return "new"
    e, st, t1, px = _num(m.get("entry")), _num(m.get("stop")), _num(m.get("target_1")), _num(m.get("price"))
    if not m.get("t1_taken") and None not in (e, st, t1, px) and e != st:
        lo, hi = sorted((st, t1))
        if lo < px < hi and abs(px - e) <= NEAR_FRAC * abs(e - st):
            return "near"
    return "running"


def _since(page):
    ms = [_ms(_get(page, "shadows", "markets", g, "started_utc")) for g in (_get(page, "shadows", "markets") or {})]
    ms = [x for x in ms if x is not None]
    return _iso(min(ms)) if ms else None


def build_landing(doc, page=None):
    """The open landing file from a built setups.json document (and the page, for the book's start): the board
    (side and state per market, no levels), the record, wins per market and the newest five CLOSED setups. Nothing
    that would give away an open setup's entry, stop or targets."""
    ms = [m for m in (doc.get("markets") or []) if isinstance(m, dict)]
    book = doc.get("book") or {}
    closed, won = _int(book.get("closed")), _int(book.get("won"))
    return {"generated_utc": doc.get("generated_utc"), "schema": 1,
            "board": [{"symbol": m.get("symbol"), "short": m.get("short"),
                       "side": m.get("side") if m.get("side") in ("LONG", "SHORT") else "FLAT",
                       "opened_utc": m.get("opened_utc") if m.get("side") in ("LONG", "SHORT") else None,
                       "state": _state(m),
                       "rr_now_t2": m.get("rr_now_t2") if m.get("side") in ("LONG", "SHORT") else None,
                       "market_open": m.get("market_open")} for m in ms],
            "record": {"closed": closed, "won": won, "lost": max(0, closed - won),
                       "open": sum(1 for m in ms if m.get("side") in ("LONG", "SHORT")),
                       "since_utc": _since(page) if isinstance(page, dict) else None,
                       "verdict": book.get("verdict"), "judged_at": 30},
            "by_market": [{"symbol": m.get("symbol"), "short": m.get("short"), "closed": _int(m.get("closed")),
                           "wins": _int(m.get("wins"))} for m in ms],
            "closed_setups": [dict((k, v) for k, v in c.items() if k not in ("result_pct", "result_usd"))
                              for c in (doc.get("closed_setups") or [])[:5] if isinstance(c, dict)]}


# ------------------------------------------------------------------ the file
def _atomic(path, text, mode=None):
    """Write `text` to `path` through a temp file in the same folder and os.replace; `mode` is set on the temp
    file before the rename, so the file is never seen half-written or with another mode."""
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _say(log, text):
    try:
        (log or (lambda *_: None))(text)
    except Exception:
        pass


def _publish(name, doc, out_dir, log, tag):
    """The JSON text of doc to <out_dir>/<name> and, when MIND15_SETUPS_WEB_DIR is set, to <that folder>/<name>
    (mode 0644), both atomically. A web copy that fails is one line through `log` and stops nothing.
    -> (local path, web path or None)"""
    text = _text(json.dumps(doc, allow_nan=False))                # (the wording rule once more, on the whole text)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    _atomic(path, text)
    web, web_dir = None, (os.environ.get(WEB_ENV) or "").strip()
    if web_dir:
        try:
            _atomic(os.path.join(web_dir, name), text, mode=WEB_MODE)
            web = os.path.join(web_dir, name)
        except Exception as e:
            _say(log, "%s: web copy not written (%r)" % (tag, e))
    return path, web


def _read_json(path):
    try:
        with io.open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def write_events(out_dir=None, data_dir=None, generated_utc=None, log=None):
    """Write setup_events.json (beside setups.json; web copy as setups.json's). generated_utc: the page's own
    (default: the clock). -> {"events": how many, "path", "web_path"}"""
    events, live_since = load_events(data_dir)
    if generated_utc is None:
        generated_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    doc = build_events(events, generated_utc=generated_utc, live_since=live_since)
    path, web = _publish(EVENTS_FILE, doc, out_dir or LIVE_DIR, log, "setup_events")
    return {"events": len(doc["events"]), "path": path, "web_path": web}


def events_line(info):
    """The step log's one line for a written events file."""
    return "setup_events: %d events -> %s%s" % (info["events"], info["path"],
                                                " (web copy: %s)" % info["web_path"] if info.get("web_path") else "")


def write(page, out_dir=None, s1=None, now=None, data_dir=None, log=None, bars_dir=None, trades_dir=None):
    """Write setup_events.json, then setups.json. page: the page dict, or the path of page.json (then out_dir
    defaults to its folder: the files land next to it). s1 None = read the S1 record from data_dir (default
    data/); the bar files from bars_dir (default data/), the trade files from trades_dir (default out/live/), the
    previous setups.json from out_dir.
    When MIND15_SETUPS_WEB_DIR is set the same texts are also written to that folder (mode 0644); a web copy that
    fails is said in one line through `log` and stops nothing: the local file is already there. The events file
    is written first and on its own: its failure is one line through `log` ("setup_events: not written (...)")
    and setups.json is written all the same; a page setups.json cannot use (or cannot read) still gets the events
    file and then raises, as before.
    -> {"markets": how many, "path": the local file, "web_path": the web copy or None}"""
    err = None
    if not isinstance(page, dict):
        src = os.path.abspath(str(page))
        out_dir = out_dir or os.path.dirname(src)
        try:
            with open(src, encoding="utf-8") as fh:
                page = json.load(fh)
        except Exception as e:
            page, err = None, e
    out_dir = out_dir or LIVE_DIR
    try:
        gen = page.get("generated_utc") if isinstance(page, dict) else None
        _say(log, events_line(write_events(out_dir, data_dir=data_dir, generated_utc=gen, log=log)))
    except Exception as e:
        _say(log, "setup_events: not written (%r)" % (e,))
    if err is not None:
        raise err
    assets = page.get("assets") if isinstance(page, dict) and isinstance(page.get("assets"), dict) else {}
    syms = _order(page, assets) if isinstance(page, dict) else []
    bars =dict((a, read_closes(bar_path(bars_dir or BARS_DIR, a))) for a in syms if isinstance(a, str))
    doc = build(page, s1=load_s1(data_dir) if s1 is None else s1, now=now, bars=bars,
                trades=read_trades(trades_dir or TRADES_DIR), prev=_read_json(os.path.join(out_dir, FILE)))
    path, web = _publish(FILE, doc, out_dir, log, "setups")
    try:                                                          # the open landing file: its own guard, one line
        lp, lw = _publish(LANDING_FILE, build_landing(doc, page), out_dir, log, "landing")
        _say(log, "landing: %d markets -> %s%s" % (len(doc["markets"]), lp, " (web copy: %s)" % lw if lw else ""))
    except Exception as e:
        _say(log, "landing: not written (%r)" % (e,))
    return {"markets": len(doc["markets"]), "path": path, "web_path": web}


def line(info):
    """The step log's one line for a written file."""
    return "setups: %d markets -> %s%s" % (info["markets"], info["path"],
                                           " (web copy: %s)" % info["web_path"] if info.get("web_path") else "")
