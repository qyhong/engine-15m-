# -*- coding: utf-8 -*-
"""signals_early -- the early signal book S2 (research/HYPOTHESES.md, H56 and its implementation note). PAPER ONLY.

The same b_targets entries as S1 (signals.py), announced at the engine's DECISION close instead of one bar after the fill.
It places nothing and never touches the engine: it READS the page (the b_targets view of every market, whose `next_open`
shows the order the book will fill at the next open), the tail of the engine's 15-minute bar files and the book's
closed-trade files, and keeps two files of its own: data/signals_early_state.json (atomic) and
data/signals_early_log.jsonl (append only).

SINCE think15-v5.2.9 (22 Nov 2026): on BTC and ETH the book itself books a new entry from flat at the decision close
(CFG["early_entry"]), so there is no pending order to see and S1 (signals.py) is issued in that step with its levels.
S2 therefore no longer fires for those entries; it still fires for BTC and ETH flips and for every other market, and
its BTC and ETH record from that date is flips only. Nothing below was changed.

A SIGNAL is issued when a market's b_targets view shows a NEW pending entry (`next_open` "... -> LONG" / "... -> SHORT",
never an exit or a flip to flat). It carries the side and E0 = the decision close (the close of the bar the page's shadow
books have reached, read from the engine's own bar file).

THE IMPLEMENTATION CHOICE (H56 note, 19 Nov 2026, decided from the code before any live S2 signal): the stop and targets
are NOT on the S2 card. The book sets them at the fill from the fill price (shadows.run -> open_pos: entry = the next
OPEN, stop = entry - side x stop_units x unit, live.plan_targets(side, entry, stop, readings)), which is unknown at the
decision close, and the page carries neither the unit nor the readings. They follow as a reply one bar later, taken from
the page when the position appears (the same levels S1 shows), or from the book's closed-trade file (stop0, target_1,
target_2) when the trade closed inside its fill bar or Target 1 had already traded when the page first showed it.

THE FOLLOWABLE RULES (H56; everything not restated is S1's, run by signals.step_bar / signals._advance unchanged):
  bar A   the 15-minute slot during which the S2 alert is sent.
  window  the four slots A .. A+3 (valid until A's open + 60 minutes). A bar may fill only if it OPENS at or after the
          send time: `first_ms` = the send time rounded UP to a bar open. A page-driven alert is always sent after A's
          open, so bar A in practice never fills and A+1 .. A+3 can (`window` = the countable bars, 3 or 4).
  entry   a limit at E0. A stop or Target 1 trading in bar A or any later bar before the fill voids (S1 rule 2).
  after   half at Target 1, the rest at Target 2, the stop to E0 after Target 1, same bar = the stop, a gap through the
          stop fills at the open, the book's own other exits followed one bar later (S1 rules 3-5). 1R = |E0 - S|.
Bars are run through the state machine only once the levels are known, from bar A on, and only up to the close the page
has reached (as in S1).

PAIRING with S1: an S2 signal and the S1 signal of the SAME b_targets entry share the entry's `opened_utc` (S1's log key
"asset|opened_utc"). Per signal a no fill counts 0; an entry S1 never signalled (e.g. the trade closed inside its fill
bar, which the page never shows) counts S1 as 0 once the book's trade is closed.

Cards (HTML) are subscriber-facing: plain words, no book names, no research words, no forecast model name.
"""
import csv
import io
import json

from . import signals as s1
from .config import CFG

BAR_MS = s1.BAR_MS
WINDOW_SLOTS = 4                        # H56: the four 15-minute slots after A's open, A included
AWAIT = "AWAIT_LEVELS"                  # the S2 alert is out; the book's stop and targets are not known yet
LEVELS_WAIT_MS = s1.CSV_WAIT_MS         # how long the levels may be missing after the pending order is gone
RULER = u"\U0001f4d0"
SIDE_WORD = {1: "LONG", -1: "SHORT"}


# ------------------------------------------------------------------ what the page says
def pending_entry(view):
    """The side of a NEW pending entry in a b_targets view (`next_open` "ENTER -> LONG"), or None: an exit, a flip to flat,
    no pending order, or an order to the side already held."""
    if not isinstance(view, dict):
        return None
    nxt = str(view.get("next_open") or "")
    side = {"LONG": 1, "SHORT": -1}.get(nxt.rsplit("->", 1)[-1].strip()) if "->" in nxt else None
    if side is None or view.get("status") == SIDE_WORD[side]:
        return None
    return side


def fingerprint(view):
    """One pending order seen on several pages (a late-feed market fills one bar later) is ONE signal: the order, the
    position and the trade count stay the same until it fills."""
    return "%s|%s|%s" % (view.get("next_open"), view.get("status"), view.get("trades"))


def delay_bars(asset):
    return int(CFG.get("fill_delay", {}).get(asset, 0) or 0)


def decision_close(data_dir, asset, dec_ms):
    """E0: the close of the bar that closed at dec_ms (the decision bar), from the engine's bar file; None if not read."""
    bars = s1.read_bars(s1.bar_path(data_dir, asset), dec_ms - 3 * BAR_MS)
    for b in bars or []:
        if b[0] == dec_ms - BAR_MS:
            return b[4]
    return None


def read_entry_row(path, t_in_cands, side):
    """The book's closed trade opened at one of t_in_cands on this side (with its stop and targets), or None."""
    try:
        with io.open(path, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
    except (OSError, ValueError, csv.Error):
        return None
    for r in reversed(rows):
        t_in, sd = s1._num(r.get("t_in_ms")), s1._num(r.get("side"))
        if t_in is None or int(t_in) not in t_in_cands or sd is None or int(sd) != side:
            continue
        t_out, pct = s1._num(r.get("t_out_ms")), s1._num(r.get("pnl_pct"))
        if t_out is None or pct is None:
            continue
        return {"t_in_ms": int(t_in), "t_out_ms": int(t_out), "p_in": s1._num(r.get("p_in")), "p_out": s1._num(r.get("p_out")),
                "why_out": str(r.get("why_out") or ""), "pct": pct, "r": s1._num(r.get("r_mult")),
                "own_usd": s1._num(r.get("pnl_usd")), "stop": s1._num(r.get("stop0")), "t1": s1._num(r.get("target_1")),
                "t2": s1._num(r.get("target_2"))}
    return None


# ------------------------------------------------------------------ a new early signal
def build_signal(asset, side, e0, dec_ms, now_ms, view):
    a_ms = now_ms - now_ms % BAR_MS                                   # bar A: the slot during which the alert is sent
    first_ms = -(-now_ms // BAR_MS) * BAR_MS                          # the first bar that opens at or after the alert
    valid = a_ms + WINDOW_SLOTS * BAR_MS
    dec_utc = s1._dt(dec_ms).strftime("%Y-%m-%d %H:%M")
    return {"asset": asset, "side": side, "entry": float(e0), "stop": None, "t1": None, "t2": None, "fee": s1.fee_side(asset),
            "k": "%s|%s" % (asset, dec_utc), "dec_ms": dec_ms, "decision_utc": dec_utc, "next_open": view.get("next_open"),
            "fp": fingerprint(view), "opened_utc": None, "f_ms": None, "sent_ms": now_ms, "a_ms": a_ms,
            "first_ms": first_ms, "window": int((valid - first_ms) // BAR_MS), "valid_until_ms": valid, "msg_id": None,
            "early_t1": False, "follow": {"state": AWAIT, "last_bar_ms": a_ms - BAR_MS, "bars_after_a": 0, "exits": []},
            "book": {"closed": False}}


# ------------------------------------------------------------------ cards (HTML, subscriber-facing)
def _bars_word(n):
    return "bar" if n == 1 else "bars"


def signal_card(sig, asset_page=None):
    mins = max(15, int(round((sig["dec_ms"] + (delay_bars(sig["asset"]) + 1) * BAR_MS - sig["sent_ms"]) / 60000.0)) + 2)
    L = [u"%s <b>%s</b> · early signal <code>%s</code>" % (s1.GREEN if sig["side"] > 0 else s1.RED, s1._head(sig), sig["id"]),
         u"Limit order at <b>%s</b> (the last 15-minute close)" % s1._p(sig["entry"]),
         u"Valid until <b>%s UTC</b> (the next %d full 15-minute %s)" % (s1._hm(sig["valid_until_ms"]), sig["window"],
                                                                         _bars_word(sig["window"])),
         u"Stop and targets follow as a reply in about %d minutes, once the model's own order has filled." % mins,
         s1._esc(s1.why_sentence(asset_page, sig["side"])),
         u"Plan: take half at Target 1 and move the stop to the entry; the rest runs to Target 2. "
         u"If the stop or Target 1 trades before the entry fills, the signal is void.", s1.FOOT]
    return "\n".join(L)


def _sane(sig):
    side, E = sig["side"], sig["entry"]
    return side * (E - sig["stop"]) > 0 and side * (sig["t1"] - E) > 0


def levels_card(sig, now_ms):
    rows = ["%-8s %10s %5s %4s" % ("Level", "Price", "%", "R"), "-" * 30, "%-8s %10s" % ("Entry", s1._p(sig["entry"]))]
    for name, level in (("Stop", sig["stop"]), ("Target 1", sig["t1"]), ("Target 2", sig["t2"])):
        pct, r = s1._dist(sig, level)
        rows.append("%-8s %10s %5.2f %4s" % (name, s1._p(level), pct, "-" if r is None else "%.1f" % r))
    until = s1._hm(sig["valid_until_ms"])
    L = [u"%s <b>Stop and targets</b> · <code>%s</code>" % (RULER, sig["id"]),
         u"%s: limit at %s, %s %s UTC." % (s1._head(sig), s1._p(sig["entry"]),
                                           "valid until" if now_ms < sig["valid_until_ms"] else "it was valid until", until),
         "<pre>%s</pre>" % s1._esc("\n".join(rows))]
    if _sane(sig):
        L.append(u"Plan: take half at Target 1 and move the stop to the entry; the rest runs to Target 2.")
    else:
        L.append(u"%s The stop or Target 1 is already past the entry price: this signal cannot fill. Cancel the order."
                 % s1.WARN)
    return "\n".join(L + [s1.FOOT])


# ------------------------------------------------------------------ the levels, one bar after the alert
def _book_from_row(sig, row):
    r = row["r"]
    if r is None and row["p_in"] and row["stop"] is not None and abs(row["p_in"] - row["stop"]) > 0:
        r = row["pct"] / 100.0 * row["p_in"] / abs(row["p_in"] - row["stop"])
    sig["book"].update(closed=True, known=True, t_out_ms=row["t_out_ms"], p_out=row["p_out"], why_out=row["why_out"],
                       pct=row["pct"], r=r, usd=s1.NOTIONAL * row["pct"] / 100.0)
    return r


def _set_levels(sig, f_ms, E_book, S, T1, T2, source, now_ms, send, log):
    sig.update(stop=float(S), t1=float(T1), t2=float(T2), f_ms=int(f_ms), book_entry=E_book,
               opened_utc=s1._dt(f_ms).strftime("%Y-%m-%d %H:%M"))
    f = sig["follow"]
    f.update(state=s1.WAITING, last_bar_ms=min(sig["a_ms"], int(f_ms)) - BAR_MS)
    ok, _mid = s1._deliver(send, levels_card(sig, now_ms), sig.get("msg_id"))
    log.append(s1._row(sig, now_ms, "levels", entry_utc=sig["opened_utc"], stop=sig["stop"], t1=sig["t1"], t2=sig["t2"],
                       book_entry=E_book, source=source, delivered=ok))


def _levels(sig, view, live_dir, now_ms, send, log):
    """Look for the book's stop and targets of this entry: the page's open position, else its closed-trade row."""
    asset, side = sig["asset"], sig["side"]
    cands = [sig["dec_ms"] + j * BAR_MS for j in range(delay_bars(asset) + 1)]
    on_page = isinstance(view, dict) and view.get("status") == SIDE_WORD[side] and s1._parse_utc(view.get("opened_utc")) in cands
    if on_page:
        E, S, T1, T2 = (s1._num(view.get(k)) for k in ("entry", "stop", "target_1", "target_2"))
        if not view.get("t1_taken") and None not in (E, S, T1, T2) and S != E:
            return _set_levels(sig, s1._parse_utc(view["opened_utc"]), E, S, T1, T2, "page", now_ms, send, log)
    row = read_entry_row(s1.trades_path(live_dir, asset), cands, side)
    if row is not None:
        if None in (row["stop"], row["t1"], row["t2"]) or row["stop"] == row["p_in"]:
            r = _book_from_row(sig, row)
            log.append(s1._row(sig, now_ms, "book_closed", known=True, t_out_utc=s1._iso(row["t_out_ms"]), p_out=row["p_out"],
                               why_out=row["why_out"], pct=row["pct"], r=r, usd=sig["book"]["usd"], own_usd=row["own_usd"],
                               follow_state=s1.NO_FILL))
            return _no_levels(sig, now_ms, send, log)
        _set_levels(sig, row["t_in_ms"], row["p_in"], row["stop"], row["t1"], row["t2"], "trades", now_ms, send, log)
        r = _book_from_row(sig, row)
        log.append(s1._row(sig, now_ms, "book_closed", known=True, t_out_utc=s1._iso(row["t_out_ms"]), p_out=row["p_out"],
                           why_out=row["why_out"], pct=row["pct"], r=r, usd=sig["book"]["usd"], own_usd=row["own_usd"],
                           follow_state=s1.WAITING))
        return None
    if on_page or not isinstance(view, dict) or view.get("status") is None or fingerprint(view) == sig["fp"]:
        sig.pop("gone_ms", None)
        return None                                                   # still pending / still open: read again next check
    sig.setdefault("gone_ms", now_ms)
    if now_ms - sig["gone_ms"] >= LEVELS_WAIT_MS:
        sig["book"].update(closed=True, known=False)
        log.append(s1._row(sig, now_ms, "book_closed", known=False))
        return _no_levels(sig, now_ms, send, log)
    return None


def _no_levels(sig, now_ms, send, log):
    for e in s1._no_fill(sig, None, "levels"):
        s1._emit(sig, e, now_ms, send, log)


# ------------------------------------------------------------------ one check
def run(page, now, send, data_dir, live_dir, state_path, log_path):
    """ONE check: follow the early signals out, then issue one for every new pending b_targets entry on the page.
    send(text, reply_to=None) -> (delivered, message id). Running it twice on the same records changes nothing.
    -> {"started", "new", "events", "bars_unread"}"""
    info = {"started": False, "new": 0, "events": 0, "bars_unread": []}
    views = s1.book_views(page)
    if views is None:
        return info
    now_ms = s1._ms(now)
    st, log = s1.load_state(state_path), []
    if st is None:                                                    # the first run: orders already waiting are not signalled
        st = {"version": 1, "live_since": s1._iso(now_ms), "seen": {}, "seq": {}, "open": {}}
        log.append({"t": s1._iso(now_ms), "k": "start", "ev": "start", "live_since": st["live_since"]})
        for asset, view in sorted(views.items()):
            if pending_entry(view) is not None:
                st["seen"][asset] = fingerprint(view)
                log.append({"t": s1._iso(now_ms), "k": "%s|%s" % (asset, fingerprint(view)), "ev": "seen_not_signalled",
                            "asset": asset, "why": "already waiting when the preview started"})
        s1.append_log(log_path, log)
        s1.save_state(state_path, st)
        info["started"] = True
        return info
    before = json.dumps(st, sort_keys=True)
    for sid in sorted(st["open"], key=lambda k: (st["open"][k]["sent_ms"], k)):
        sig = st["open"][sid]
        view = views.get(sig["asset"])
        if sig["follow"]["state"] == AWAIT:
            _levels(sig, view, live_dir, now_ms, send, log)
        if sig["follow"]["state"] != AWAIT:
            s1._advance(sig, view, page, now_ms, send, data_dir, live_dir, log, info)
        if sig["follow"]["state"] not in s1.ACTIVE + (AWAIT,) and sig["book"]["closed"]:
            del st["open"][sid]                                       # both records are final: it lives on in the log
    for asset, view in sorted(views.items()):
        side = pending_entry(view)
        if side is None or st["seen"].get(asset) == fingerprint(view):
            continue
        dec_ms = s1.as_of_ms(page, asset)
        e0 = decision_close(data_dir, asset, dec_ms) if dec_ms is not None else None
        if e0 is None:
            info["bars_unread"].append(asset)
            continue                                                  # read again next check
        sig = build_signal(asset, side, e0, dec_ms, now_ms, view)
        seq_key, n, sid = s1._next_id(st, asset, now)
        sig["id"] = sid + "e"
        ok, mid = s1._deliver(send, signal_card(sig, (page.get("assets") or {}).get(asset)))
        if not ok:
            continue                                                  # not sent, so not a signal: tried again next check
        sig["msg_id"] = mid
        st["seq"] = dict((k, v) for k, v in st["seq"].items() if k[-8:] == seq_key[-8:])
        st["seq"][seq_key] = n
        st["seen"][asset] = sig["fp"]
        st["open"][sig["id"]] = sig
        info["new"] += 1
        log.append(s1._row(sig, now_ms, "signal", side=side, entry=sig["entry"], fee=sig["fee"], next_open=sig["next_open"],
                           decision_utc=sig["decision_utc"], bar_a_utc=s1._iso(sig["a_ms"]),
                           first_bar_utc=s1._iso(sig["first_ms"]), window=sig["window"],
                           valid_until_utc=s1._iso(sig["valid_until_ms"]), msg_id=mid))
    info["events"] = len(log)
    if log:
        s1.append_log(log_path, log)
    if json.dumps(st, sort_keys=True) != before:
        s1.save_state(state_path, st)
    return info


# ------------------------------------------------------------------ the record and the paired comparison with S1
def _by_key(events):
    by = {}
    for e in events:
        if e.get("id"):
            by.setdefault(e["k"], {})[e["ev"]] = e
    return by


def _final(s):
    """A signal's result per signal in % (a no fill = 0), or None while it is not final."""
    if "closed" in s:
        return s["closed"]["pct"]
    if "no_fill" in s:
        return 0.0
    return None


def paired(events2, events1):
    """S2 minus S1 per b_targets entry, over the S2 signals whose result and S1 counterpart are both final."""
    one = _by_key(events1)
    rows, waiting, no_levels = [], 0, 0
    for k, s in sorted(_by_key(events2).items()):
        if "signal" not in s:
            continue
        if "levels" not in s:
            no_levels += "no_fill" in s
            waiting += "no_fill" not in s
            continue
        r2 = _final(s)
        k1 = "%s|%s" % (s["signal"]["asset"], s["levels"]["entry_utc"])
        t = one.get(k1) or {}
        if "signal" in t:
            r1, sent1 = _final(t), True
        else:
            r1, sent1 = (0.0 if "book_closed" in s else None), False    # S1 can no longer signal once the trade is closed
        if r2 is None or r1 is None:
            waiting += 1
            continue
        rows.append({"id": s["signal"]["id"], "entry_k": k1, "early_pct": r2, "regular_pct": r1, "early_filled": "filled" in s,
                     "regular_sent": sent1, "regular_filled": "filled" in t})
    n = len(rows)
    diffs = [s1.NOTIONAL * (r["early_pct"] - r["regular_pct"]) / 100.0 for r in rows]
    stt = s1._stats(diffs)
    rng = stt.get("range90_usd")
    sent1 = [r for r in rows if r["regular_sent"]]
    mean = lambda xs: round(sum(xs) / len(xs), 3) if xs else None    # noqa: E731
    return {"n": n, "waiting": waiting, "no_levels": no_levels, "no_regular": n - len(sent1),
            "early_fill_pct": round(100.0 * sum(r["early_filled"] for r in rows) / n, 1) if n else None,
            "regular_fill_pct": round(100.0 * sum(r["regular_filled"] for r in sent1) / len(sent1), 1) if sent1 else None,
            "early_mean_pct": mean([r["early_pct"] for r in rows]), "regular_mean_pct": mean([r["regular_pct"] for r in rows]),
            "diff_mean_pct": None if stt["mean_usd"] is None else round(stt["mean_usd"] / 100.0, 3),
            "diff_range90_pct": None if not rng else [round(rng[0] / 100.0, 3), round(rng[1] / 100.0, 3)],
            "verdict": stt["verdict"], "rows": rows}


def scoreboard(log_path, s1_log_path):
    """The early record (S1's scoreboard over the S2 log), S1's own fill rate, and the paired comparison."""
    e2, e1 = s1.read_log(log_path), s1.read_log(s1_log_path)
    return {"early": s1.scoreboard(e2), "regular_fill_pct": s1.scoreboard(e1)["fill_rate_pct"], "paired": paired(e2, e1)}


def _pc(v):
    return "-" if v is None else s1._pct(v)


def _paired_lines(p, regular_fill):
    if not p["n"]:
        L = [u"Beside the regular signals: no paired result yet."]
    else:
        rows = ["%-17s %12s" % ("Paired signals", p["n"]),
                "%-17s %12s" % ("Early filled", "-" if p["early_fill_pct"] is None else "%.0f%%" % p["early_fill_pct"]),
                "%-17s %12s" % ("Regular filled", "-" if p["regular_fill_pct"] is None else "%.0f%%" % p["regular_fill_pct"]),
                "%-17s %12s" % ("Early per signal", _pc(p["early_mean_pct"])),
                "%-17s %12s" % ("Regular per sig.", _pc(p["regular_mean_pct"])),
                "%-17s %12s" % ("Difference", _pc(p["diff_mean_pct"]))]
        if p["diff_range90_pct"]:
            rows += ["90% range, difference", "%30s" % ("%s to %s" % (_pc(p["diff_range90_pct"][0]),
                                                                    _pc(p["diff_range90_pct"][1])))]
        L = [u"<b>Beside the regular signals, on the same trades</b>", "<pre>%s</pre>" % s1._esc("\n".join(rows)),
             u"Difference = early minus regular, per signal; a signal that did not fill counts as 0. Verdict on the "
             u"difference: %s." % s1._esc(p["verdict"])]
        if p["no_regular"]:
            L.append(u"%d of them had no regular signal (the model's trade ended inside its first bar): 0 there."
                     % p["no_regular"])
    if regular_fill is not None:
        L.append(u"All regular signals: %.0f%% filled." % regular_fill)
    return L


def record_card(log_path, s1_log_path, st=None):
    """The /early answer: the early signals' own record and the paired comparison with the regular signals."""
    sb = scoreboard(log_path, s1_log_path)
    since = sb["early"].get("live_since") or (st or {}).get("live_since")
    L = [u"%s <b>Early signals · the record</b>" % s1.CHART,
         u"Live since %s: orders already waiting then were not signalled." % s1._since(since)]
    return "\n".join(L + s1._record_lines(sb["early"]) + _paired_lines(sb["paired"], sb["regular_fill_pct"]) + [s1.FOOT])


def recap_line(log_path, s1_log_path, now):
    """One line for the daily recap: yesterday's early signals, the running fill rate and the paired difference."""
    from datetime import timedelta
    day = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    by = _by_key(s1.read_log(log_path))
    y = [s for s in by.values() if "signal" in s and str(s["signal"].get("t", ""))[:10] == day]
    sb = scoreboard(log_path, s1_log_path)
    e, p = sb["early"], sb["paired"]
    if not e["sent"]:
        return u"\U0001f9ea Early signal preview: no early signals yet."
    s = u"\U0001f9ea Early signal preview: yesterday %d sent; in all %d sent, %s filled" % (
        len(y), e["sent"], "-" if e["fill_rate_pct"] is None else "%.0f%%" % e["fill_rate_pct"])
    if p["n"]:
        s += u"; early minus regular %s per signal over %d paired" % (_pc(p["diff_mean_pct"]), p["n"])
        if p["diff_range90_pct"]:
            s += u" (90%% range %s to %s)" % (_pc(p["diff_range90_pct"][0]), _pc(p["diff_range90_pct"][1]))
    return s + u". /early for the record."
