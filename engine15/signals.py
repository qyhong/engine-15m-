# -*- coding: utf-8 -*-
"""signals -- the signal book S1 (research/HYPOTHESES.md, H53): b_targets as a signal a person can follow. PAPER ONLY.

It places nothing and never touches the engine: it READS the page the engine wrote (the b_targets view of every market),
the tail of the engine's own 15-minute bar files and the book's closed-trade files, and keeps two files of its own under
data/: signals_state.json (written atomically) and signals_log.jsonl (append only, one JSON line per event).

A SIGNAL is issued when the page shows a new open b_targets position in a market (a new `opened_utc`). It carries the side,
the book's entry price E, the stop S, Target 1 and Target 2 as the page shows them at that moment; 1R = |E - S|.
Every signal keeps two records: the BOOK result (as b_targets booked it, from its closed-trade file) and the FOLLOWABLE
result under H53's fixed rules. Only the followable record is judged.

THE FOLLOWABLE RULES, as implemented (H53; nothing here is tuned):
  bar A   the engine bar during which the alert was sent (the wall clock of the send). The book's fill bar F has closed by
          the time the page can show the position, so A is F+1 or later; bars F .. A never fill.
          (Since think15-v5.2.9, 22 Nov 2026, a BTC or ETH entry from flat is on the page in the step that decides
          it, so there A is F itself and the four bars are F+1 .. F+4, one bar sooner. The rules are unchanged.)
  1 entry a limit at E, filled at E on the first of the FOUR bars after bar A whose range holds E (low <= E <= high).
          The four bars are also the four 15-minute slots after A (the card's "valid until"): where the market shut in
          between, a bar that opens after that time does not fill.
  2 no fill: S or Target 1 trades in any bar from F up to the fill (a bar that holds E and S or Target 1 together is a
          no fill), or the four bars pass, or the book closes its own trade first. No result; a signal sent, not a trade.
  3 after the fill: half out at Target 1, the rest at Target 2; after Target 1 the stop is at E. The stop is looked at
          first in every bar (stop and target in one bar = the stop); a gap through the stop fills at that bar's open.
          In the bar that takes Target 1 the stop at E is live at once: if that bar also holds E the rest is out at E.
  4 the book closes its own trade for another reason while the followable trade is open: an exit alert is sent, and the
          trade closes at the OPEN of the first bar after the bar in which that exit alert was sent.
  5 costs: the market's own fee a side (config asset_cost / cost_side, the numbers playbook.fee_side returns) on every
          fill; $10,000 a signal; results in $, % and R.

Bars are processed only once CLOSED, only once each (state keeps the last bar processed per signal), and only up to the
close the page's own shadow books have reached, so the book's state and the bars never disagree. A bar file that cannot be
read (missing, empty, half-written) changes nothing: the same bars are read again at the next check.

Cards (HTML) are subscriber-facing: no research, no book names, no server details, no dollar size.
"""
import calendar
import csv
import io
import json
import math
import os
from datetime import datetime, timedelta, timezone

from . import exits
from .config import CFG

BOOK = "b_targets"                      # the signal source (shadows.py); fixed by H53
BAR_MS = int(CFG.get("bar_ms", 900000))
WINDOW = 4                              # H53 rule 1: the bars after bar A in which the limit may fill
PART = exits.PART                       # H53 rule 3: the share closed at Target 1 (ONE constant: exits.PART)
NOTIONAL = 10000.0                      # H53 rule 5: dollars a signal
CSV_WAIT_MS = 30 * 60 * 1000            # how long a closed book trade may be missing from its file before going on without
WAITING, FILLED, T1_TAKEN, CLOSED, NO_FILL = "WAITING", "FILLED", "T1_TAKEN", "CLOSED", "NO_FILL"
ACTIVE = (WAITING, FILLED, T1_TAKEN)
CODE = {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "XAUUSD": "XAU", "XAGUSD": "XAG", "USDJPY": "JPY", "SPX": "SPX", "WTI": "WTI",
        "BRENT": "BRN"}
MKT = {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "XAUUSD": "Gold", "XAGUSD": "Silver", "USDJPY": "USDJPY", "SPX": "S&P",
       "WTI": "WTI", "BRENT": "Brent"}
FOOT = u"<i>Paper signal from a model, not financial advice.</i>"
GREEN, RED, WHITE, TICK, TARGET, FLAG, WARN, CHART, DISH = (
    u"\U0001f7e2", u"\U0001f534", u"⚪", u"✅", u"\U0001f3af", u"\U0001f3c1", u"⚠️", u"\U0001f4ca",
    u"\U0001f4e1")
NO_FILL_WHY = {"window": "the entry window passed without price trading at the entry",
               "target": "price reached Target 1 before the entry filled",
               "stop": "the stop traded before the entry filled",
               "model": "the model closed its own trade before the entry filled",
               "levels": "the model's order gave no stop and targets"}           # S2 only (signals_early.py)
WHY_SKIP = ("forecast", "kronos", "alphaprediction", "base rate", "all the evidence", "owner")


# ------------------------------------------------------------------ small helpers
def _ms(dt):
    return int(calendar.timegm(dt.utctimetuple()) * 1000)


def _dt(ms):
    return datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=int(ms))


def _iso(ms):
    return _dt(ms).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hm(ms):
    return _dt(ms).strftime("%H:%M")


def _parse_utc(s):
    """'2026-11-15 03:15' (the page) or '2026-11-15T03:15:00Z' (the log) -> epoch ms; None if it is not a time."""
    try:
        return _ms(datetime.strptime(str(s)[:16].replace("T", " "), "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc))
    except (TypeError, ValueError):
        return None


def _num(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _p(v):
    """A price for a card: 65,203.20 / 159.765 / 47.085 / 54.103 (at most three decimals; the log keeps the full price)."""
    v = float(v)
    if abs(v) >= 1000:
        return "{:,.2f}".format(v)
    if abs(v) >= 100:
        return "%.3f" % v
    s = ("%.3f" % v).rstrip("0")
    whole, _dot, frac = s.partition(".")
    return whole + "." + frac.ljust(2, "0")


def _pct(v):
    return "%+.2f%%" % v


def _r(v):
    return "-" if v is None else "%+.2fR" % v


def _mk(asset):
    return MKT.get(asset, asset)


def fee_side(asset):
    """The market's own fee a side, as a fraction: the same numbers as playbook.fee_side (which needs pandas to import)."""
    return float(CFG.get("asset_cost", {}).get(asset, CFG["cost_side"]))


# ------------------------------------------------------------------ what the engine wrote (read only)
def book_views(page):
    """{market: the b_targets view} from the page (shadows -> books -> b_targets -> assets), or None if it is not there."""
    try:
        v = page["shadows"]["books"][BOOK]["assets"]
    except (KeyError, TypeError):
        return None
    return v if isinstance(v, dict) else None


def as_of_ms(page, asset):
    """The close (epoch ms) the shadow books of this market's group have reached on this page; None if not stated."""
    try:
        group = (page.get("assets") or {}).get(asset, {}).get("market_group")
        if not group:
            group = next(g for g, members in (page.get("markets") or {}).items() if asset in members)
        return _parse_utc(page["shadows"]["markets"][group]["as_of_utc"])
    except (KeyError, TypeError, AttributeError, StopIteration):
        return None


def bar_path(data_dir, asset):
    return os.path.join(data_dir, "%s_15m.csv" % asset.lower())


def trades_path(live_dir, asset):
    return os.path.join(live_dir, "shadow_trades_%s_%s.csv" % (BOOK, asset))


def _parse_bars(lines):
    """Bar lines -> [(ts, open, high, low, close)], or None when any line is not a whole bar (a half-written file)."""
    out, last = [], None
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith(b"ts_ms"):
            continue
        f = ln.split(b",")
        if len(f) < 5:
            return None
        try:
            ts = int(f[0])
            o, h, l, c = (float(x) for x in f[1:5])
        except ValueError:
            return None
        if ts % BAR_MS or not all(math.isfinite(x) and x > 0 for x in (o, h, l, c)) or (last is not None and ts <= last):
            return None
        out.append((ts, o, max(o, h, l, c), min(o, h, l, c), c))
        last = ts
    return out


def read_bars(path, since_ms, chunk=8192, cap=1 << 23):
    """The engine's closed bars after since_ms, from the TAIL of its bar file: [(ts, open, high, low, close)].
    None when the read cannot be trusted (missing, empty, garbled, or the tail does not reach back to since_ms): the
    caller changes nothing and reads again at the next check. A failed read is never 'no bars'."""
    try:
        size = os.path.getsize(path)
        if size <= 0:
            return None
        back = chunk
        with io.open(path, "rb") as fh:
            while True:
                start = max(0, size - back)
                fh.seek(start)
                raw = fh.read(size - start)
                lines = raw.split(b"\n")
                if start:
                    lines = lines[1:]                                 # the first line of a tail may be cut
                if not raw.endswith(b"\n"):
                    lines = lines[:-1]                                # the last line may still be being written
                rows = _parse_bars(lines)
                if rows is None:
                    return None
                if start == 0 or (rows and rows[0][0] <= since_ms):
                    break
                if back >= cap:
                    return None
                back *= 4
    except OSError:
        return None
    if not rows:
        return None
    return [b for b in rows if b[0] > since_ms]


def read_trade(path, t_in_ms):
    """The book's closed trade that was opened at t_in_ms, from its closed-trade file; None if it is not (yet) there."""
    try:
        with io.open(path, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
    except (OSError, ValueError, csv.Error):
        return None
    for r in reversed(rows):
        t_in, t_out, pct, p_out = _num(r.get("t_in_ms")), _num(r.get("t_out_ms")), _num(r.get("pnl_pct")), _num(r.get("p_out"))
        if t_in is None or int(t_in) != int(t_in_ms) or pct is None or t_out is None:
            continue
        return {"t_out_ms": int(t_out), "p_in": _num(r.get("p_in")), "p_out": p_out, "why_out": str(r.get("why_out") or ""),
                "pct": pct, "r": _num(r.get("r_mult")), "own_usd": _num(r.get("pnl_usd"))}
    return None


# ------------------------------------------------------------------ results
def result(side, entry, stop, fee, exits):
    """One trade's result after fees, the book's own arithmetic (shadows.run): exits = [(price, share)], shares sum to 1.
    -> {"pct", "usd" (on $10,000), "r" (None when the stop is at the entry), "avg_exit"}"""
    avg = sum(px * w for px, w in exits)
    net = side * (avg - entry) / entry - fee * (entry + avg) / entry
    risk = abs(entry - stop)
    return {"pct": 100.0 * net, "usd": NOTIONAL * net, "r": net * entry / risk if risk > 0 else None, "avg_exit": avg}


def _stop_traded(side, lo, hi, level):
    return lo <= level if side > 0 else hi >= level


def _reached(side, lo, hi, level):
    return hi >= level if side > 0 else lo <= level


def _stop_fill(side, o, level):
    """A stop's fill: the level, or the bar's open when the bar gapped through it."""
    return min(o, level) if side > 0 else max(o, level)


# ------------------------------------------------------------------ the followable state machine (H53)
def _no_fill(sig, ts, reason):
    sig["follow"].update(state=NO_FILL, reason=reason, end_ms=ts)
    return [{"ev": "no_fill", "reason": reason, "bar_ms": ts}]


def _close(sig, ts, px, why):
    f = sig["follow"]
    f["exits"].append([px, 1.0 - sum(x[1] for x in f["exits"]), why])
    res = result(sig["side"], sig["entry"], sig["stop"], sig["fee"], [(p, w) for p, w, _y in f["exits"]])
    f.update(state=CLOSED, end_ms=ts, why=why, result=res)
    return [dict({"ev": "closed", "why": why, "px": px, "bar_ms": ts}, **res)]


def _book_reason(sig):
    """Why a signal that was still waiting ends when the book closed first, from the book's own exit words."""
    why = str(sig["book"].get("why_out") or "")
    return "target" if "T1" in why else "stop" if "STOP" in why else "model"


def step_bar(sig, bar):
    """Advance ONE signal by ONE closed bar (ts, open, high, low, close). Changes sig; -> the events of this bar."""
    ts, o, h, l, _c = bar
    f, side, E, S, T1, T2 = sig["follow"], sig["side"], sig["entry"], sig["stop"], sig["t1"], sig["t2"]
    if f["state"] == WAITING:
        b = sig["book"]
        if ts >= sig["valid_until_ms"]:
            return _no_fill(sig, ts, "window")                        # a bar after the stated validity (a session gap)
        if b.get("closed") and (b.get("t_out_ms") is None or ts >= b["t_out_ms"]):
            return _no_fill(sig, ts, _book_reason(sig))               # rule 2: the book closed its own trade first
        if _stop_traded(side, l, h, S):
            return _no_fill(sig, ts, "stop")                          # rule 2, also when the bar holds E
        if _reached(side, l, h, T1):
            return _no_fill(sig, ts, "target")
        if ts < sig.get("first_ms", sig["a_ms"] + BAR_MS):
            return []                                                 # S1: bar A and the bars before it never fill
        f["bars_after_a"] += 1                                        # (S2, H56: the bars that open before the alert)
        if l <= E <= h:
            f.update(state=FILLED, fill_ms=ts)
            return [{"ev": "filled", "px": E, "bar_ms": ts}]
        return _no_fill(sig, ts, "window") if f["bars_after_a"] >= sig.get("window", WINDOW) else []
    if f["state"] not in (FILLED, T1_TAKEN):
        return []
    alert = f.get("exit_alert_ms")
    if alert is not None and ts > alert:
        return _close(sig, ts, o, "model")                            # rule 4: the open of the bar after the exit alert's bar
    ev = []
    if f["state"] == FILLED:
        if _stop_traded(side, l, h, S):
            return _close(sig, ts, _stop_fill(side, o, S), "stop")    # the stop first, whatever else the bar holds
        if not _reached(side, l, h, T1):
            return []
        f["exits"].append([T1, PART, "t1"])
        f.update(state=T1_TAKEN, t1_ms=ts)
        ev.append({"ev": "t1", "px": T1, "bar_ms": ts})
        if _stop_traded(side, l, h, E):                               # the stop is at E from Target 1 on: this bar too
            return ev + _close(sig, ts, E, "stop_be")
    else:
        if _stop_traded(side, l, h, E):
            return _close(sig, ts, _stop_fill(side, o, E), "stop_be")
    if _reached(side, l, h, T2):
        return ev + _close(sig, ts, T2, "t2")
    return ev


# ------------------------------------------------------------------ state and log (data/ only)
def load_state(path):
    """The state, or None when there is no file yet (the first run). A file that cannot be read raises: it is never
    replaced by an empty state."""
    if not os.path.exists(path):
        return None
    with io.open(path, encoding="utf-8") as fh:
        st = json.load(fh)
    if not isinstance(st, dict) or "open" not in st or "seen" not in st:
        raise ValueError("signals state has an unexpected shape")
    return st


def save_state(path, st):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=1, sort_keys=True)
    os.replace(tmp, path)


def append_log(path, rows):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with io.open(path, "a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + u"\n")


def read_log(path):
    """Every event once, in order ((signal, event) is the key: a line written twice after a crash counts once)."""
    out, seen = [], set()
    try:
        with io.open(path, encoding="utf-8") as fh:
            for ln in fh:
                try:
                    e = json.loads(ln)
                except ValueError:
                    continue
                k = (e.get("k"), e.get("ev"))
                if isinstance(e, dict) and k not in seen:
                    seen.add(k)
                    out.append(e)
    except OSError:
        pass
    return out


# ------------------------------------------------------------------ a new signal
def _next_id(st, asset, now):
    key = "%s-%s" % (CODE.get(asset, asset[:3]), now.strftime("%Y%m%d"))
    n = int(st["seq"].get(key, 0)) + 1
    return key, n, "%s-%s-%02d" % (CODE.get(asset, asset[:3]), now.strftime("%m%d"), n)


def build_signal(asset, view, now_ms):
    """-> (signal, None) from the page's view of a new open position, or (None, why it cannot be a signal)."""
    side = {"LONG": 1, "SHORT": -1}.get(view.get("status"))
    f_ms = _parse_utc(view.get("opened_utc"))
    E, S, T1, T2 = (_num(view.get(k)) for k in ("entry", "stop", "target_1", "target_2"))
    if side is None or f_ms is None or None in (E, S, T1, T2) or min(E, S, T1, T2) <= 0:
        return None, "the page gives no complete entry, stop and targets"
    early = bool(view.get("t1_taken")) or S == E                      # Target 1 traded before the alert: the stop shown is E
    if side * (T1 - E) <= 0 or side * (T2 - T1) <= 0 or (side * (E - S) <= 0 and not early):
        return None, "the stop and targets are not on their own sides of the entry"
    a_ms = max(now_ms - now_ms % BAR_MS, f_ms)                        # bar A: the bar during which the alert is sent
    sig = {"asset": asset, "side": side, "entry": E, "stop": S, "t1": T1, "t2": T2, "fee": fee_side(asset),
           "opened_utc": str(view.get("opened_utc")), "f_ms": f_ms, "sent_ms": now_ms, "a_ms": a_ms,
           "valid_until_ms": a_ms + (WINDOW + 1) * BAR_MS, "msg_id": None, "early_t1": early,
           "follow": {"state": WAITING, "last_bar_ms": f_ms - BAR_MS, "bars_after_a": 0, "exits": []},
           "book": {"closed": False}}
    return sig, None


def why_sentence(d, side):
    """ONE plain sentence from what the page says for this market: its structure and the strongest readings on the side."""
    word = "buy" if side > 0 else "sell"
    names = []
    voices = [v for v in (d or {}).get("voices") or [] if isinstance(v, dict) and _num(v.get("pull_pts")) is not None]
    for v in sorted(voices, key=lambda x: -side * float(x["pull_pts"])):
        if side * float(v["pull_pts"]) < 0.1 or len(names) == 3:
            break
        t = str(v.get("title") or "").split(" (")[0].split(",")[0].strip()
        if t.lower().startswith("the library's "):
            t = t[len("the library's "):].capitalize()
        if t and not any(s in t.lower() for s in WHY_SKIP) and t not in names:
            names.append(t)
    if not names:                                                     # no voice on this side: the plain-worded reasons
        for item in (d or {}).get("for_long" if side > 0 else "for_short") or []:
            t = str(item[0] if isinstance(item, (list, tuple)) and item else "")
            if " " in t and "_" not in t and not any(s in t.lower() for s in WHY_SKIP) and len(names) < 3:
                names.append(t)
    struct = str((d or {}).get("structure") or "").strip().rstrip(".")
    lead = "market structure reads \"%s\"" % struct if struct else ""
    if names:
        tail = "strongest on the %s side: %s" % (word, names[0] if len(names) == 1 else
                                                 ", ".join(names[:-1]) + " and " + names[-1])
        return "Why: %s." % ("; ".join(x for x in (lead, tail) if x))
    if lead:
        return "Why: %s, and the model's combined reading favours the %s side." % (lead, word)
    return "Why: the model's combined reading of this market favours the %s side." % word


# ------------------------------------------------------------------ cards (HTML, subscriber-facing)
def _head(sig):
    return u"%s %s" % ("BUY" if sig["side"] > 0 else "SELL", _esc(_mk(sig["asset"])))


def _dist(sig, level):
    """(distance from the entry in %, the same in R or None)."""
    d = abs(level - sig["entry"])
    risk = abs(sig["entry"] - sig["stop"])
    return 100.0 * d / sig["entry"], (d / risk if risk > 0 else None)


def signal_card(sig, asset_page=None):
    rows = ["%-8s %10s %5s %4s" % ("Level", "Price", "%", "R"), "-" * 30, "%-8s %10s" % ("Entry", _p(sig["entry"]))]
    for name, level in (("Stop", sig["stop"]), ("Target 1", sig["t1"]), ("Target 2", sig["t2"])):
        pct, r = _dist(sig, level)
        rows.append("%-8s %10s %5.2f %4s" % (name, _p(level), pct, "-" if r is None else "%.1f" % r))
    L = [u"%s <b>%s</b> · signal <code>%s</code>" % (GREEN if sig["side"] > 0 else RED, _head(sig), sig["id"]),
         u"Limit order at <b>%s</b>" % _p(sig["entry"]),
         u"Valid until <b>%s UTC</b> (the next four 15-minute bars)" % _hm(sig["valid_until_ms"]),
         "<pre>%s</pre>" % _esc("\n".join(rows)), _esc(why_sentence(asset_page, sig["side"]))]
    if sig.get("early_t1"):
        L.append(u"%s Target 1 was already reached before this alert: do not enter." % WARN)
    else:
        L.append(u"Plan: take half at Target 1 and move the stop to the entry; the rest runs to Target 2. "
                 u"If the stop or Target 1 trades before the entry fills, the signal is void.")
    return "\n".join(L + [FOOT])


def _result_line(res):
    return u"Result <b>%s</b> · <b>%s</b> after fees" % (_pct(res["pct"]), _r(res.get("r")))


def follow_card(sig, e):
    """The follow-up message of one event (sent as a reply to the signal's own message)."""
    sid, head, ev = sig["id"], _head(sig), e["ev"]
    at = u"%s UTC bar" % _hm(e["bar_ms"]) if e.get("bar_ms") is not None else ""
    if ev == "filled":
        L = [u"%s <b>Entry filled</b> · <code>%s</code>" % (TICK, sid),
             u"%s at %s (%s)." % (head, _p(e["px"]), at),
             u"Stop %s · Target 1 %s · Target 2 %s" % (_p(sig["stop"]), _p(sig["t1"]), _p(sig["t2"]))]
    elif ev == "no_fill":
        L = [u"%s <b>No fill: signal expired</b> · <code>%s</code>" % (WHITE, sid),
             u"%s: %s. No trade, no result. Cancel the order." % (head, NO_FILL_WHY.get(e["reason"], e["reason"]))]
    elif ev == "t1":
        pct, _r_ = _dist(sig, e["px"])
        L = [u"%s <b>Target 1 hit: take half, move stop to entry</b> · <code>%s</code>" % (TARGET, sid),
             u"%s: half closed at %s (%+.2f%%, %s)." % (head, _p(e["px"]), pct, at),
             u"Stop for the rest is now the entry %s · Target 2 %s" % (_p(sig["entry"]), _p(sig["t2"]))]
    elif ev == "model_exit":
        L = [u"%s <b>The model has closed its trade: exit now</b> · <code>%s</code>" % (WARN, sid),
             u"%s: close what is open at the market. The result follows at the next bar's open." % head]
    elif ev == "closed":
        dot = GREEN if e["pct"] >= 0 else RED
        title, line = {
            "t2": (u"%s <b>Target 2 hit: closed</b>" % FLAG, u"%s: the rest closed at %s (%s)." % (head, _p(e["px"]), at)),
            "stop": (u"%s <b>Stopped</b>" % dot, u"%s: stopped at %s (%s)." % (head, _p(e["px"]), at)),
            "stop_be": (u"%s <b>Stopped at entry</b>" % dot,
                        u"%s: half was taken at Target 1, the rest closed at %s (%s)." % (head, _p(e["px"]), at)),
            "model": (u"%s <b>Closed by the model</b>" % dot, u"%s: closed at %s, the open of the %s." % (head, _p(e["px"]), at)),
        }[e["why"]]
        L = [u"%s · <code>%s</code>" % (title, sid), line, _result_line(e)]
    else:
        L = [u"<code>%s</code> %s" % (sid, _esc(ev))]
    return "\n".join(L + [FOOT])


# ------------------------------------------------------------------ one check
def _deliver(send, text, reply_to=None):
    """-> (delivered, message id). A send that fails never stops the record."""
    try:
        r = send(text, reply_to)
    except Exception:
        return False, None
    if isinstance(r, tuple):
        return bool(r[0]), (r[1] if len(r) > 1 else None)
    return bool(r), None


def _row(sig, now_ms, ev, **kw):
    return dict({"t": _iso(now_ms), "id": sig.get("id"), "k": sig.get("k") or "%s|%s" % (sig["asset"], sig["opened_utc"]),
                 "ev": ev,
                 "asset": sig["asset"]}, **kw)


def _emit(sig, e, now_ms, send, log):
    ok, _mid = _deliver(send, follow_card(sig, e), sig.get("msg_id"))
    kw = dict((k, v) for k, v in e.items() if k not in ("ev", "bar_ms"))
    if e.get("bar_ms") is not None:
        kw["bar_utc"] = _iso(e["bar_ms"])
    log.append(_row(sig, now_ms, e["ev"], delivered=ok, **kw))


def _advance(sig, view, page, now_ms, send, data_dir, live_dir, log, info):
    asset, f, b = sig["asset"], sig["follow"], sig["book"]
    if not b["closed"] and isinstance(view, dict) and view.get("status") is not None:     # a missing view is not a close
        if view.get("status") not in ("LONG", "SHORT") or str(view.get("opened_utc")) != sig["opened_utc"]:
            row = read_trade(trades_path(live_dir, asset), sig["f_ms"])
            if row is None:
                b.setdefault("gone_ms", now_ms)
                if now_ms - b["gone_ms"] < CSV_WAIT_MS:
                    return                                            # the engine's trade file is read again next check
                b.update(closed=True, known=False)
                log.append(_row(sig, now_ms, "book_closed", known=False))
            else:
                r = row["r"]
                if r is None and row["p_in"] and abs(sig["entry"] - sig["stop"]) > 0:
                    r = row["pct"] / 100.0 * row["p_in"] / abs(sig["entry"] - sig["stop"])
                b.update(closed=True, known=True, t_out_ms=row["t_out_ms"], p_out=row["p_out"], why_out=row["why_out"],
                         pct=row["pct"], r=r, usd=NOTIONAL * row["pct"] / 100.0)
                log.append(_row(sig, now_ms, "book_closed", known=True, t_out_utc=_iso(row["t_out_ms"]), p_out=row["p_out"],
                                why_out=row["why_out"], pct=row["pct"], r=r, usd=b["usd"], own_usd=row["own_usd"],
                                follow_state=f["state"]))
    if f["state"] not in ACTIVE:
        return
    upto = as_of_ms(page, asset)
    bars = read_bars(bar_path(data_dir, asset), f["last_bar_ms"]) if upto is not None else None
    if bars is None:
        info["bars_unread"].append(asset)
        return                                                        # nothing changes: the same bars next check
    for bar in bars:
        if bar[0] <= f["last_bar_ms"]:
            continue
        if bar[0] + BAR_MS > min(upto, now_ms):
            break                                                     # not closed yet, or the page has not reached it
        evs = step_bar(sig, bar)
        f["last_bar_ms"] = bar[0]
        for e in evs:
            _emit(sig, e, now_ms, send, log)
        if f["state"] not in ACTIVE:
            return
    if b["closed"]:
        if f["state"] == WAITING:                                     # rule 2: the book closed first
            if b.get("t_out_ms") is None or upto >= b["t_out_ms"]:    # every bar before its exit has been looked at
                for e in _no_fill(sig, None, _book_reason(sig)):
                    _emit(sig, e, now_ms, send, log)
        elif f.get("exit_alert_ms") is None:                          # rule 4: the exit alert goes out now, in this bar
            f["exit_alert_ms"] = now_ms - now_ms % BAR_MS
            _emit(sig, {"ev": "model_exit", "alert_bar_utc": _iso(f["exit_alert_ms"])}, now_ms, send, log)
    if f["state"] == WAITING and upto >= sig["valid_until_ms"]:       # every bar inside the validity has been looked at
        for e in _no_fill(sig, None, "window"):
            _emit(sig, e, now_ms, send, log)


def run(page, now, send, data_dir, live_dir, state_path, log_path):
    """ONE check: follow the signals already out, then issue a signal for every new open position on the page.
    send(text, reply_to=None) -> (delivered, message id). Light: the page in hand, the state file, and the tail of the bar
    file of each market with a signal in progress. Running it twice on the same records changes nothing the second time.
    -> {"started", "new", "events", "bars_unread"}"""
    info = {"started": False, "new": 0, "events": 0, "bars_unread": []}
    views = book_views(page)
    if views is None:
        return info
    now_ms = _ms(now)
    st, log = load_state(state_path), []
    if st is None:                                                    # the first run: nothing already open is signalled
        st = {"version": 1, "live_since": _iso(now_ms), "seen": {}, "seq": {}, "open": {}}
        log.append({"t": _iso(now_ms), "k": "start", "ev": "start", "live_since": st["live_since"]})
        for asset, view in sorted(views.items()):
            if isinstance(view, dict) and view.get("status") in ("LONG", "SHORT") and view.get("opened_utc"):
                st["seen"][asset] = str(view["opened_utc"])
                log.append({"t": _iso(now_ms), "k": "%s|%s" % (asset, view["opened_utc"]), "ev": "seen_not_signalled",
                            "asset": asset, "why": "already open when the preview started"})
        append_log(log_path, log)
        save_state(state_path, st)
        info["started"] = True
        return info
    before = json.dumps(st, sort_keys=True)
    for sid in sorted(st["open"], key=lambda k: (st["open"][k]["sent_ms"], k)):
        sig = st["open"][sid]
        _advance(sig, views.get(sig["asset"]), page, now_ms, send, data_dir, live_dir, log, info)
        if sig["follow"]["state"] not in ACTIVE and sig["book"]["closed"]:
            del st["open"][sid]                                       # both records are final: it lives on in the log
    live_ms = _parse_utc(st.get("live_since")) or now_ms
    for asset, view in sorted(views.items()):
        if not isinstance(view, dict) or view.get("status") not in ("LONG", "SHORT") or not view.get("opened_utc"):
            continue
        key = str(view["opened_utc"])
        if st["seen"].get(asset) == key:
            continue
        sig, why_not = build_signal(asset, view, now_ms)
        if sig is not None and sig["f_ms"] + BAR_MS <= live_ms:
            sig, why_not = None, "already open when the preview started"
        if sig is None:
            st["seen"][asset] = key
            log.append({"t": _iso(now_ms), "k": "%s|%s" % (asset, key), "ev": "seen_not_signalled", "asset": asset,
                        "why": why_not})
            continue
        seq_key, n, sig["id"] = _next_id(st, asset, now)
        ok, mid = _deliver(send, signal_card(sig, (page.get("assets") or {}).get(asset)))
        if not ok:
            continue                                                  # not sent, so not a signal: tried again next check
        sig["msg_id"] = mid
        st["seq"] = dict((k, v) for k, v in st["seq"].items() if k[-8:] == seq_key[-8:])   # today's counters only
        st["seq"][seq_key] = n
        st["seen"][asset] = key
        st["open"][sig["id"]] = sig
        info["new"] += 1
        log.append(_row(sig, now_ms, "signal", side=sig["side"], entry=sig["entry"], stop=sig["stop"], t1=sig["t1"],
                        t2=sig["t2"], fee=sig["fee"], opened_utc=sig["opened_utc"], bar_a_utc=_iso(sig["a_ms"]),
                        valid_until_utc=_iso(sig["valid_until_ms"]), msg_id=mid))
        if sig["early_t1"]:                                           # Target 1 traded before the alert: rule 2, at once
            for e in _no_fill(sig, None, "target"):
                _emit(sig, e, now_ms, send, log)
    info["events"] = len(log)
    if log:
        append_log(log_path, log)
    if json.dumps(st, sort_keys=True) != before:
        save_state(state_path, st)
    return info


# ------------------------------------------------------------------ the record
def _stats(xs):
    """The scoreboard's own rule (reports._stats): count, net, mean and the 90% range of the mean, and its verdict words."""
    from .reports import _stats as rule
    return rule(list(xs))


def _sum(rows):
    """Net and mean of a set of results in %, R and $ (the $ on $10,000 a signal)."""
    pct = [r["pct"] for r in rows if r.get("pct") is not None]
    rr = [r["r"] for r in rows if r.get("r") is not None]
    s, sr = _stats([NOTIONAL * p / 100.0 for p in pct]), _stats(rr)
    rng = s.get("range90_usd")
    return {"n": len(pct), "net_usd": s["net_usd"], "mean_usd": s["mean_usd"], "range90_usd": rng,
            "net_pct": round(sum(pct), 3), "mean_pct": round(sum(pct) / len(pct), 3) if pct else None,
            "range90_pct": None if not rng else [round(rng[0] / 100.0, 3), round(rng[1] / 100.0, 3)],
            "net_r": round(sum(rr), 3), "mean_r": sr["mean_usd"], "range90_r": sr.get("range90_usd"),
            "won_pct": s.get("won_pct"), "verdict": s["verdict"]}


def scoreboard(events):
    """The running record over the log: signals sent, the fill rate, the followable trades (the judged record), the book
    result of the SAME signals, and what the signals that did not fill made at the book's own price."""
    by = {}
    for e in events:
        if e.get("id"):
            by.setdefault(e["k"], {})[e["ev"]] = e
    sigs = [s for s in by.values() if "signal" in s]
    filled = [s for s in sigs if "filled" in s]
    nofill = [s for s in sigs if "no_fill" in s]
    closed = [s["closed"] for s in filled if "closed" in s]
    book = lambda rows: [s["book_closed"] for s in rows if s.get("book_closed", {}).get("known")]   # noqa: E731
    start = next((e for e in events if e.get("ev") == "start"), None)
    first = min((s["signal"]["t"] for s in sigs), default=None)
    last = max((e.get("t") for e in events if e.get("t")), default=None)
    days = None
    if first and last:
        days = round((_parse_utc(last) - _parse_utc(first)) / 86400000.0, 1)
    follow = _sum(closed)
    return {"live_since": (start or {}).get("live_since"), "first_signal_utc": first, "days": days,
            "sent": len(sigs), "filled": len(filled), "no_fill": len(nofill),
            "waiting": len(sigs) - len(filled) - len(nofill), "in_trade": len(filled) - len(closed),
            "fill_rate_pct": round(100.0 * len(filled) / len(sigs), 1) if sigs else None,
            "follow": follow, "verdict": follow["verdict"],
            "book_same": _sum(book(sigs)), "book_of_filled": _sum(book(filled)), "book_of_no_fill": _sum(book(nofill)),
            "gate": {"signals": len(sigs), "min_signals": 100, "days": days, "min_days": 60,
                     "met": bool(len(sigs) >= 100 and (days or 0) >= 60 and follow["verdict"].startswith("ahead"))}}


def _since(iso):
    ms = _parse_utc(iso)
    if ms is None:
        return "?"
    d = _dt(ms)
    return "%d %s" % (d.day, d.strftime("%b %Y"))


def _record_lines(sb):
    f = sb["follow"]
    rows = ["%-17s %12s" % ("Signals sent", sb["sent"]),
            "%-17s %12s" % ("Filled", "%d (%s)" % (sb["filled"], "-" if sb["fill_rate_pct"] is None
                                                   else "%.0f%%" % sb["fill_rate_pct"])),
            "%-17s %12s" % ("No fill", sb["no_fill"])]
    if sb["waiting"]:
        rows.append("%-17s %12s" % ("Waiting for entry", sb["waiting"]))
    if sb["in_trade"]:
        rows.append("%-17s %12s" % ("In a trade now", sb["in_trade"]))
    rows.append("%-17s %12s" % ("Trades closed", f["n"]))
    if f["n"]:
        rows += ["%-17s %12s" % ("Won", "%.0f%%" % f["won_pct"]),
                 "%-9s %9s %10s" % ("Net", _r(f["net_r"]), _pct(f["net_pct"])),
                 "%-9s %9s %10s" % ("Per trade", _r(f["mean_r"]), _pct(f["mean_pct"]))]
        if f["range90_pct"]:
            rows += ["90% range, per trade", "%30s" % ("%s to %s" % (_pct(f["range90_pct"][0]), _pct(f["range90_pct"][1])))]
    L = ["<pre>%s</pre>" % _esc("\n".join(rows)), u"Verdict: %s." % _esc(sb["verdict"])]
    b, nf = sb["book_same"], sb["book_of_no_fill"]
    if b["n"]:
        L.append(u"The same signals at the model's own entry price: %d closed, net %s (%s)."
                 % (b["n"], _pct(b["net_pct"]), _r(b["net_r"])))
    if nf["n"]:
        L.append(u"Signals that did not fill would have made, at the model's own price: %d closed, net %s (%s)."
                 % (nf["n"], _pct(nf["net_pct"]), _r(nf["net_r"])))
    L.append(u"Results are after fees, every signal the same size. Only filled trades are judged.")
    return L


def _live_line(sb, st=None):
    since = sb.get("live_since") or (st or {}).get("live_since")
    return u"Live since %s: positions already open then were not signalled." % _since(since)


def record_card(log_path, st=None):
    """The /record answer: the running record of the signals."""
    sb = scoreboard(read_log(log_path))
    return "\n".join([u"%s <b>Signals · the record</b>" % CHART, _live_line(sb, st)] + _record_lines(sb) + [FOOT])


def _outcome(s):
    if "closed" in s:
        return _r(s["closed"].get("r")) if s["closed"].get("r") is not None else _pct(s["closed"]["pct"])
    if "no_fill" in s:
        return "no fill"
    if "t1" in s:
        return "open, T1 hit"
    return "in trade" if "filled" in s else "waiting"


def recap_card(log_path, now, st=None, extra=None):
    """The daily recap: yesterday's signals one line each, then the running record (extra: lines put before the foot)."""
    events = read_log(log_path)
    day = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    by = {}
    for e in events:
        if e.get("id"):
            by.setdefault(e["k"], {})[e["ev"]] = e
    rows = ["%-11s %-4s %13s" % (s["signal"]["id"], "BUY" if s["signal"].get("side", 0) > 0 else "SELL", _outcome(s))
            for s in by.values() if "signal" in s and str(s["signal"].get("t", ""))[:10] == day]
    d = now - timedelta(days=1)
    L = [u"%s <b>Signals · daily recap</b>" % CHART, u"%s (UTC)" % d.strftime("%a %d %b"),
         "<pre>%s</pre>" % _esc("\n".join(rows)) if rows else u"No signals yesterday.",
         u"<b>Running record</b>"]
    sb = scoreboard(events)
    return "\n".join(L + [_live_line(sb, st)] + _record_lines(sb) + [x for x in (extra or []) if x] + [FOOT])


def open_card(st, now=None):
    """The /signals answer: the signals in progress and where each stands."""
    head = u"%s <b>Signals · open now</b>" % DISH
    rows = []
    for sid in sorted((st or {}).get("open") or {}, key=lambda k: st["open"][k]["sent_ms"]):
        s = st["open"][sid]
        f = s["follow"]
        if f["state"] not in ACTIVE:
            continue
        side = "BUY" if s["side"] > 0 else "SELL"
        if f["state"] == WAITING:
            late = now is not None and _ms(now) > s["valid_until_ms"] + 2 * BAR_MS     # its bars have not been read yet
            rows += ["%-11s %-4s %13s" % (sid, side, "being checked" if late else "waiting"),
                     " limit %s to %s" % (_p(s["entry"]), _hm(s["valid_until_ms"]))]
        else:
            rows += ["%-11s %-4s %13s" % (sid, side, "T1 hit" if f["state"] == T1_TAKEN else "in trade"),
                     " stop %s" % _p(s["entry"] if f["state"] == T1_TAKEN else s["stop"]),
                     " next %s" % _p(s["t2"] if f["state"] == T1_TAKEN else s["t1"])]
            if f.get("exit_alert_ms") is not None:
                rows.append(" model closed: exit now")
    if st is None:
        return "\n".join([head, u"The signals have not started yet.", FOOT])
    body = "<pre>%s</pre>" % _esc("\n".join(rows)) if rows else u"No signal is open."
    return "\n".join([head, body, FOOT])
