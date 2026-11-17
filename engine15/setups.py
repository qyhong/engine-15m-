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

Nothing here places an order, opens a socket or changes a file other than setups.json. Every text in the file
comes from a short fixed list (no reading, no research wording, no book name) and passes the page's own wording
rule (export.py: the forecast model is never named).
"""
import json
import math
import os
import re
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
    the others ask extdata.is_open (weekly hours, the daily breaks, NYSE holidays for the S&P; public holidays
    of gold, silver, oil and USDJPY are not modelled there). next_open_utc is the first 15-minute slot at which
    that same rule says open, when the market is shut now. (None, None) when it cannot be told."""
    if now_ms is None:
        return None, None
    try:
        if sym in CFG.get("crypto", ()):
            return True, None
        from . import extdata
        if sym not in extdata.MARKETS:
            return None, None
        import pandas as pd
        t = pd.Timestamp(int(now_ms), unit="ms", tz="UTC")
        if extdata.is_open(sym, t):
            return True, None
        idx = pd.date_range(t.ceil("15min"), periods=LOOK_AHEAD, freq="15min")
        k = next((i for i, x in enumerate(extdata.open_mask(sym, idx)) if x), None)
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


# ------------------------------------------------------------------ the blocks
def _rr(sgn, price, stop, target):
    """Reward to risk FROM THE CURRENT PRICE, in the trade's direction; None when a number is missing or the
    price is already at or beyond the target or the stop."""
    if None in (price, stop, target):
        return None
    reward, risk = sgn * (target - price), sgn * (price - stop)
    return None if reward <= 0 or risk <= 0 else _r(reward / risk)


def _market(page, sym, asset, view, waiting, now_ms):
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
         "entry": None, "stop": None, "target_1": None, "target_2": None, "t1_taken": False, "opened_utc": None,
         "price": _px(price), "price_bar_utc": _iso(bar), "unrealized_usd": None, "unrealized_pct": None,
         "market_open": is_open, "next_open_utc": next_open, "edge_with_position_pts": None,
         "hit_24h_30d_pct": _r(_get(page, "horizon_skill", "markets", sym, "24h", "d30", 0)),
         "rr_now_t1": None, "rr_now_t2": None, "stop_dist_now_pct": None,
         "entry_window_open": False, "entry_valid_until_utc": None,
         "closed": _int(view.get("trades")), "wins": _int(view.get("wins")), "realized_usd": _r(view.get("realized_usd"))}
    if not sgn:
        return m
    entry, t1, t2 = _num(view.get("entry")), _num(view.get("target_1")), _num(view.get("target_2"))
    taken = bool(view.get("t1_taken"))
    stop = entry if taken and entry is not None else _num(view.get("stop"))   # after Target 1 the stop is the entry
    opened = _ms(view.get("opened_utc"))
    edge = _num(asset.get("edge_pts"))                            # P(up) - P(down), in points: positive favours LONG
    until = waiting.get((sym, str(view.get("opened_utc"))[:16].replace("T", " ")))
    m.update(entry=_px(entry), stop=_px(stop), target_1=_px(t1), target_2=_px(t2), t1_taken=taken, opened_utc=_iso(opened),
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


def build(page, s1=None, now=None):
    """The Setups file as a dict. page: the engine's page (page.json); s1: load_s1()'s record, or None (no
    record: zeros and nulls); now: the moment the trading hours and the entry windows are asked about (a
    datetime, an ISO time or epoch ms; default: the page's own generated_utc, so the same page always gives the
    same file). Raises ValueError when the page has no view of the book at all: a file that would call every
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
    return _clean({"generated_utc": page.get("generated_utc"), "version": page.get("version"), "schema": SCHEMA,
                   "note": NOTE, "book": _book(page, [views.get(a) for a in order]), "followable": _followable(s1),
                   "learning": _learning(page),
                   "markets": [_market(page, a, assets.get(a), views.get(a), waiting, now_ms) for a in order]})


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


def write(page, out_dir=None, s1=None, now=None, data_dir=None, log=None):
    """Write setups.json. page: the page dict, or the path of page.json (then out_dir defaults to its folder:
    the file lands next to it). s1 None = read the S1 record from data_dir (default data/).
    When MIND15_SETUPS_WEB_DIR is set the same text is also written to <that folder>/setups.json (mode 0644);
    a web copy that fails is said in one line through `log` and stops nothing: the local file is already there.
    -> {"markets": how many, "path": the local file, "web_path": the web copy or None}"""
    if not isinstance(page, dict):
        src = os.path.abspath(str(page))
        with open(src, encoding="utf-8") as fh:
            page = json.load(fh)
        out_dir = out_dir or os.path.dirname(src)
    out_dir = out_dir or LIVE_DIR
    doc = build(page, s1=load_s1(data_dir) if s1 is None else s1, now=now)
    text = _text(json.dumps(doc, allow_nan=False))                # (the wording rule once more, on the whole text)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, FILE)
    _atomic(path, text)
    web, web_dir = None, (os.environ.get(WEB_ENV) or "").strip()
    if web_dir:
        try:
            _atomic(os.path.join(web_dir, FILE), text, mode=WEB_MODE)
            web = os.path.join(web_dir, FILE)
        except Exception as e:
            try:
                (log or (lambda *_: None))("setups: web copy not written (%r)" % (e,))
            except Exception:
                pass
    return {"markets": len(doc["markets"]), "path": path, "web_path": web}


def line(info):
    """The step log's one line for a written file."""
    return "setups: %d markets -> %s%s" % (info["markets"], info["path"],
                                           " (web copy: %s)" % info["web_path"] if info.get("web_path") else "")
