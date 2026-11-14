# -*- coding: utf-8 -*-
"""questions -- what the engine asks the owner (owner, 11 Nov 2026: "it only asks on overall scoring;
it should have more versatile ability to ask").

Each session the engine looks at what is actually happening on the chart and in its book, lists every
question it could usefully ask, and asks the most useful one it has not asked recently. Every question
is phrased so a side answers it (long / short / no view, how sure, a note), because the answer becomes a
graded reading like any card ("owner_view").

Kinds, most urgent first:
  release        a high-impact US release within 6 hours
  stop_near      the running trade is within 0.35R of its stop
  target_near    the running trade is within 0.35R of Target 1
  level_test     price within 0.3 ATR of the nearest support or resistance
  fib_zone       price in the 1h Fibonacci golden zone of the current leg
  ma_test        price testing a moving average acting as support / resistance
  bias_conflict  the 4h/daily bias points one way, the 15m/1h structure the other
  squeeze        volatility compressed (a squeeze) - which way will it break?
  liquidity      the nearest big resting pile in the wide (+-10%) order book
  card_conflict  a strong card disagrees with the engine's lean
  even           the odds are close to even
  lean           the engine leans one way: anything it cannot read?
"""
import json
import os

PRIORITY = ["release", "stop_near", "target_near", "level_test", "fib_zone", "ma_test", "bias_conflict",
            "squeeze", "liquidity", "card_conflict", "even", "lean"]
REPEAT_WINDOW = 6                      # a kind is not asked again for the same market within its last 6 questions
ALWAYS = ("release", "stop_near")      # urgent kinds may repeat
SHORT = {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "XAUUSD": "gold", "XAGUSD": "silver", "USDJPY": "USDJPY",
         "SPX": "the S&P 500", "WTI": "WTI oil", "BRENT": "Brent oil"}


def _px(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "?"
    return "{:,.3f}".format(v) if abs(v) < 100 else "{:,.2f}".format(v) if abs(v) < 1000 else "{:,.0f}".format(v)


def _num(d, k):
    try:
        v = float((d or {}).get(k))
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def candidates(e):
    """-> [(kind, question)] for everything worth asking about this journal entry."""
    a = e.get("asset", "")
    coin = SHORT.get(a, a[:3])
    d, lv, t = e.get("data") or {}, e.get("level_reads") or {}, e.get("trade") or {}
    out = []
    price = _num(e, "price")
    edge = e.get("edge_pts")
    nx = e.get("econ_next")
    if nx and 0 <= (nx.get("hours_away") or 99) <= 6:
        out.append(("release", "US %s prints in %.0f hours. Do you expect it to push %s up or down, and how sure are you?"
                    % ((nx.get("titles") or ["data"])[0], max(nx["hours_away"], 1), coin)))
    side = t.get("status")
    entry, stop, mark, t1 = _num(t, "entry_price"), _num(t, "stop_price"), _num(t, "mark_price"), _num(t, "target_1_price")
    if side in ("LONG", "SHORT") and entry and stop and mark and abs(entry - stop) > 0:
        R = abs(entry - stop)
        if abs(mark - stop) <= 0.35 * R:
            out.append(("stop_near", "My %s on %s from %s is close to its stop at %s (price %s). Will the move against me go on "
                        "(answer %s) or turn back my way (answer %s)?" % (side.lower(), coin, _px(entry), _px(stop), _px(mark),
                                                                        "short" if side == "LONG" else "long", side.lower())))
        if t1 and abs(t1 - mark) <= 0.35 * R and (t1 - mark) * (1 if side == "LONG" else -1) > 0:
            out.append(("target_near", "%s is near my Target 1 at %s (price %s). Will it reach the target (answer %s) or turn "
                        "back first (answer %s)?" % (coin, _px(t1), _px(mark), side.lower(), "short" if side == "LONG" else "long")))
    sd, rd = _num(lv, "sup_dist_atr"), _num(lv, "res_dist_atr")
    if sd is not None and sd <= 0.3 and (rd is None or sd <= rd):
        out.append(("level_test", "%s at %s is testing support at %s (%s). Will it hold (long) or break (short)?"
                    % (coin, _px(price), _px(lv.get("sup_px")), lv.get("sup_kind") or "a level")))
    elif rd is not None and rd <= 0.3:
        out.append(("level_test", "%s at %s is testing resistance at %s (%s). Will it break up (long) or reject (short)?"
                    % (coin, _px(price), _px(lv.get("res_px")), lv.get("res_kind") or "a level")))
    gz = _num(d, "fib_gz_1h")
    if gz is not None and abs(gz) >= 0.5:
        up = gz > 0
        out.append(("fib_zone", "%s has pulled back into the 1h Fibonacci golden zone (0.5-0.618) of its %s-leg. Is this a "
                    "pullback to %s (answer %s) or is the leg failing (answer %s)?" % (
                        coin, "up" if up else "down", "buy" if up else "sell", "long" if up else "short", "short" if up else "long")))
    mt = _num(d, "mas_test_1h")
    if mt is not None and abs(mt) > 0.3:
        sup = mt > 0
        out.append(("ma_test", "%s is testing a 1h moving average as %s. Will it %s (answer %s) or give way (answer %s)?" % (
            coin, "support" if sup else "resistance", "hold and bounce" if sup else "hold and reject", "long" if sup else "short",
            "short" if sup else "long")))
    bias = e.get("htf_bias") or 0
    m15, m1h = _num(d, "ms_15m") or 0, _num(d, "ms_1h") or 0
    if bias and ((m15 and m15 * bias < 0) or (m1h and m1h * bias < 0)):
        out.append(("bias_conflict", "The 4h and daily trend on %s point %s, but the %s structure has turned %s. A pullback to "
                    "trade with the trend (answer %s) or the start of a turn (answer %s)?" % (
                        coin, "down" if bias < 0 else "up", "1h" if m1h * bias < 0 else "15m", "up" if bias < 0 else "down",
                        "short" if bias < 0 else "long", "long" if bias < 0 else "short")))
    sq = _num(d, "tq_squeeze")
    if sq is not None and sq > 0:
        out.append(("squeeze", "Volatility on %s is squeezed tight (a squeeze). Which way do you expect it to break, and how sure "
                    "are you?" % coin))
    eg = ((e.get("raw") or {}).get("book_eagle") or {})
    bw, aw, mid = _num(eg, "bid_far_wall_px"), _num(eg, "ask_far_wall_px"), _num(eg, "mid")
    if bw and aw and mid:
        out.append(("liquidity", "The wide order book on %s has a big pile of buyers near %s (%.1f%% below) and sellers near %s "
                    "(%.1f%% above). Which one will price reach first: the sellers above (long) or the buyers below (short)?" % (
                        coin, _px(bw), (1 - bw / mid) * 100, _px(aw), (aw / mid - 1) * 100)))
    if edge is not None:
        lean = "long" if edge > 0 else "short"
        against = [c for c in e.get("cards", []) if c.get("lean") is not None and c["lean"] * edge < 0]
        if against:
            worst = max(against, key=lambda c: abs(c["lean"]))
            if abs(worst["lean"]) >= 8:
                out.append(("card_conflict", "I lean %s on %s, but %s points the other way (%.0f pts). Which do you believe here?"
                            % (lean, coin, worst["card"], abs(worst["lean"]))))
        if abs(edge) < 5:
            out.append(("even", "My odds on %s are close to even (%.1f pts). Which side do you favour for the next 24 hours, and why?"
                        % (coin, abs(edge))))
        else:
            out.append(("lean", "I lean %s on %s with an edge of %.1f pts. Do you see something I cannot read: a headline, a flow, "
                        "a level?" % (lean, coin, abs(edge))))
    else:
        out.append(("even", "I am still learning and have no odds for %s yet. Which side do you favour for the next 24 hours?" % coin))
    return out


def recent_kinds(asset, path=None, tail_bytes=200000):
    """The kinds of the last questions asked about `asset` (newest last), read from the audit trail's tail."""
    from . import owner
    p = path or owner.AUDIT
    if not os.path.exists(p):
        return []
    with open(p, "rb") as fh:
        fh.seek(0, 2)
        size = fh.tell()
        fh.seek(max(0, size - tail_bytes))
        lines = fh.read().decode("utf-8", "ignore").splitlines()[1:] if size > tail_bytes else fh.read().decode("utf-8", "ignore").splitlines()
    kinds = []
    for ln in lines:
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if r.get("kind") == "question" and r.get("asset") == asset and r.get("question_kind"):
            kinds.append(r["question_kind"])
    return kinds


def ask(e, recent=None):
    """-> (kind, question): the most useful question not asked recently for this market."""
    cands = candidates(e)
    if not cands:
        return None, None
    recent = recent if recent is not None else recent_kinds(e.get("asset", ""))
    last = set(recent[-REPEAT_WINDOW:])
    order = dict((k, i) for i, k in enumerate(PRIORITY))
    cands.sort(key=lambda kv: order.get(kv[0], 99))
    for kind, q in cands:
        if kind in ALWAYS or kind not in last:
            return kind, q
    return cands[0]
