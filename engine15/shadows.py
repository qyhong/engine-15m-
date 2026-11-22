# -*- coding: utf-8 -*-
"""shadows -- the challenger books: rival rules traded on paper beside the main books. PAPER ONLY.

Every challenger is the main book with ONE thing changed. It reads the SAME odds, the same
readings and the same bars as the main book at every 15-minute close, keeps its own $10,000 per
asset, its own position and its own idle clock, and starts FLAT on the session it is switched on
(forward only: nothing before that counts). The owner sees side by side which rule makes more.
Promotion is decided later on forward results (docs/CHARTER.md), never here.

    main           the main book's rule (v5), started fresh at the same moment: the yardstick
    v4             the main rule without v5's higher-timeframe bias (the release guard stays): grades H4
    h3_flip_limit  H3: a flip / decision exit closes with a limit at the next open + 0.25 x ATR(14, 15m)
                   in the position's favour (ATR at the decision bar), resting 4 bars with the stop
                   live, then at market at the next open; entries and stops at market (research/fills.py)
    b_targets      task B: half off at Target 1, the rest at Target 2 (live.plan_targets at entry),
                   the stop to break-even once Target 1 is taken; flips and stops as the main book
    b_trail        task B: once price has gone 1R in favour, the stop trails the last confirmed 15m
                   swing or 2 x ATR(14, 15m), whichever is tighter; otherwise the main book
    b_be_t1        task B / H36: the stop moves to the entry price once Target 1 trades (live from the next bar)
    b_ema20_1h_t1  task B / H36: once Target 1 has traded, a 15m close beyond the EMA20 of the 1h chart (ratcheted,
    b_sma20_1h_t1  never loosening; SMA20 for the second) exits at the next open; engine15/exits.py holds the rule
    a_pullback     task A: an ENTER or FORCED entry waits up to 8 bars for a limit at the nearest
                   Fibonacci golden-zone edge (0.5 / 0.618 of the 1h or 4h leg) or moving-average
                   support / resistance (EMA/SMA 20/50/200, 15m and 1h) within 1 x ATR(1h) in the
                   trade's favour; unfilled, it enters at market. Waiting counts as positioned, not idle.
    m_swing_1h     workstream M (H18): NOT the main book with one change but a swing book on its own odds,
    m_swing_4h     the 1h / 4h minds of engine15/intraday.py (H19): enter when the expected value after
                   costs clears the margin (1h: 0.05 R, 4h: 0), stop at structure or 1 barrier, target
                   1.5R (1h) / 1R (4h), out at the horizon; flat is allowed (no mandate). intraday.run_swing is its book.

THE BOOK (run): the same honest frame as backtest.run_book, line for line: the decision at bar i's
close fills at bar i+1's open; the protective stop is checked first inside every bar; fees per side;
full size. With no rule switched on, run() gives exactly run_book's trades and equity
(tests/test_shadows.py). Intrabar conventions of the challengers:
  * a limit (H3 exit, pullback entry) fills only if a bar trades STRICTLY through it, at the limit
    (fills.py's convention: touching is not enough, no gap bonus);
  * a stop that is live at the start of a bar comes before any target or limit in that bar;
  * Target 1 and Target 2 may both fill in one bar; the break-even stop is live from the next bar.

FORWARD BOOKS (step): called by live.step_group after the main books, state in data/shadow_state.json
(written atomically), closed trades in out/live/shadow_trades_<challenger>_<asset>.csv, a compact
summary for page.json (export.merge adds the scoreboard across markets).
"""
import json
import os
import time
from collections import OrderedDict

import numpy as np
import pandas as pd

from . import data, exits, labels, policy
from .config import CFG, DATA_DIR, OUT_DIR

START_EQUITY = 10000.0
STATE_PATH = os.path.join(DATA_DIR, "shadow_state.json")
TRADES_DIR = os.path.join(OUT_DIR, "live")

# ---- the challengers' constants, declared once (from the hypothesis texts; none tuned here)
H3_K, H3_BARS = 0.25, 4                 # research/HYPOTHESES.md H3
PART = exits.PART                       # b_targets: the share taken at Target 1 (ONE constant: exits.PART)
TRAIL_ARM_R, TRAIL_ATR = exits.TRAIL_ARM_R, exits.TRAIL_ATR   # b_trail: arm after 1R; the ATR trail distance (1.0, 2.0)
PB_BARS, PB_RANGE_ATR1H = 8, 1.0        # a_pullback: bars a limit rests; how far from price it may sit
PB_FIB_TFS = ("1h", "4h")               # fib.py draws legs on 1h, 4h and 1d (it has no 15m leg)
PB_MA_TFS = ("15m", "1h")
PB_MAS = ("ema20", "sma20", "ema50", "sma50", "ema200", "sma200")      # mavg.SR_CANDS

from .intraday import SWING_RULES as _SWING  # noqa: E402  (intraday imports nothing from here)

CHALLENGERS = OrderedDict([
    ("main", {"title": "Main rule (v5), fresh copy", "rule": {}, "cfg": {}}),
    ("v4", {"title": "v4: no higher-timeframe bias (H4)", "rule": {}, "cfg": {"htf_bias": False}}),
    ("h3_flip_limit", {"title": "H3: limit on flip exits", "rule": {"flip_limit": True}, "cfg": {}}),
    ("b_targets", {"title": "B: half at Target 1, rest at Target 2", "rule": {"targets": True, "early": True}, "cfg": {}}),
    # H67 (registered 22 Nov 2026; owner: "Test it"): b_targets, but no entry against the market's own 30-day move
    # (H65: those trades lost on history, in both halves and both market groups). A paper shadow; the vault copies
    # b_targets, never this.
    ("b_trend30", {"title": "Setups with the 30-day trend filter (H67)",
                   "rule": {"targets": True, "early": True, "trend_days": 30}, "cfg": {}}),
    # H68 (registered 22 Nov 2026; owner: "After a stop-out, wait for a real signal instead of a forced re-entry"):
    # b_targets, but after a trade ends at its entry stop ("STOP") no forced entry until a signal enters. A paper shadow.
    ("b_wait_stop", {"title": "Setups waiting for a signal after a stop-out (H68)",
                     "rule": {"targets": True, "early": True, "wait_after_stop": True}, "cfg": {}}),
    ("b_trail", {"title": "B: trailing swing / 2 ATR stop after 1R", "rule": {"trail": True}, "cfg": {}}),
    ("a_pullback", {"title": "A: wait up to 8 bars for a pullback fill", "rule": {"pullback": True}, "cfg": {}}),
    # Y, the charter's yardstick (11 Nov 2026): the same engine and odds, deciding only at 4h / daily closes
    ("y_4h", {"title": "Y: same engine, decides at 4h closes only", "rule": {"every_ms": 4 * 3600000}, "cfg": {}}),
    ("y_1d", {"title": "Y: same engine, decides at each market's daily close only", "rule": {"daily_close": True}, "cfg": {}}),
    # H5 (registered 11 Nov 2026): halve the slow daily "strategies" voice when 1h and 4h structure turn against it
    ("h5_damp", {"title": "H5: damp slow daily voices when 1h/4h structure turns", "rule": {"h5": True}, "cfg": {}}),
    # workstream M (11 Nov 2026, H18/H19, docs/INTRADAY.md): swing books on the 1h and 4h minds' own odds
    # (engine15/intraday.py): enter only when the expected value clears the margin after costs, stop at
    # structure or 1 barrier, target 1.5R (1h) / 1R (4h), out at the horizon; no mandate, flat is allowed
    ("m_swing_1h", {"title": "M: 1h swing mind (EV filter, stop/target/1h clock)", "rule": dict(_SWING["1h"]), "cfg": {}}),
    ("m_swing_4h", {"title": "M: 4h swing mind (EV filter, stop/target/4h clock)", "rule": dict(_SWING["4h"]), "cfg": {}}),
    # H36 (registered 13 Nov 2026, task B exits; research/out/exits/trail_study.md): the main book's own entries,
    # only the exit changed. History 2020-2026, 8 markets pooled, main (hold) +$329k: every exit variant made less.
    # The owner wants forward data points regardless ("Shadow test plus label").
    ("b_be_t1", {"title": "BE: stop to break-even after Target 1 (history: +$108k vs hold +$329k)",
                 "rule": {"be_t1": True}, "cfg": {}}),
    ("b_ema20_1h_t1", {"title": "EMA trail: EMA20 on 1h after Target 1 (history: -$26k vs hold +$329k)",
                       "rule": {"ma_trail": "1h ema20", "ma_arm": "t1"}, "cfg": {}}),
    ("b_sma20_1h_t1", {"title": "SMA trail: SMA20 on 1h after Target 1 (history: -$25k vs hold +$329k)",
                       "rule": {"ma_trail": "1h sma20", "ma_arm": "t1"}, "cfg": {}}),
])
# Books that FOLLOW another book's trades and add an exit of their own (engine15/floor_book.py). They are not rules
# of run(): they read the followed book's result after it ran, and a failure in one never stops the books above.
from . import floor_book  # noqa: E402  (floor_book imports nothing from here)

FOLLOWERS = OrderedDict([
    # H61 (registered 21 Nov 2026): the one floor variant that passed on history, weakly. The owner: "Add shadow".
    (floor_book.NAME, {"title": floor_book.TITLE, "follows": "main"}),
])
TARGET_COLS = ["fib_1h_dir", "fib_1h_t1_px", "fib_1h_t2_px", "fib_4h_dir", "fib_4h_t1_px", "fib_4h_t2_px",
               "reach_24h_med_pct"]
TRADE_COLS = ["t_in_ms", "t_out_ms", "i_in", "i_out", "side", "p_in", "p_out", "why_in", "why_out", "pnl_pct",
              "equity", "qty", "pnl_usd", "fees_usd", "stop0", "risk_usd", "r_mult", "target_1", "target_2"]


# =====================================================================================
# readings the challengers need, as plain arrays (row i = known at the close of bar i)
# =====================================================================================
def _col(ev, name, n):
    if ev is not None and name in ev:
        return np.asarray(ev[name].values, dtype=float)
    return np.full(n, np.nan)


def aux_from_ev(ev, px):
    """The arrays the challengers read, from one asset's evidence frame (prep["ev"][asset])."""
    n = len(px["close"])
    aux = {"atr15": _col(ev, "atr15", n), "atr1h": _col(ev, "atr1h", n),
           "sw_lo": _col(ev, "sw_lo_15m", n), "sw_hi": _col(ev, "sw_hi_15m", n)}
    if not np.isfinite(aux["sw_lo"]).any():                  # no structure card: the same confirmed swings, here
        from .sources import structure
        _st, aux["sw_hi"], aux["sw_lo"] = structure.swings(px["high"], px["low"], structure.SWING_K["15m"])
    fib = {}
    for tf in PB_FIB_TFS:
        fib[tf] = {"dir": _col(ev, "fib_%s_dir" % tf, n), "broken": _col(ev, "fib_%s_broken" % tf, n),
                   "0.5": _col(ev, "fib_%s_r500_px" % tf, n), "0.618": _col(ev, "fib_%s_entry_px" % tf, n)}
    aux["fib"] = fib
    aux["sw_lo_1h"], aux["sw_hi_1h"] = _col(ev, "sw_lo_1h", n), _col(ev, "sw_hi_1h", n)     # the swing books (M3)
    aux["reach"] = {"1h": _col(ev, "reach_1h_med_pct", n), "4h": _col(ev, "reach_4h_med_pct", n)}
    aux["ma"] = OrderedDict(("%s %s" % (tf, m), _col(ev, "ma_%s_%s_px" % (tf, m), n)) for tf in PB_MA_TFS for m in PB_MAS)
    cols = [c for c in TARGET_COLS if ev is not None and c in ev]
    aux["targets"] = ev[cols] if cols else pd.DataFrame(index=range(n))
    return aux


def trend_move(times_ms, close, days, lo, hi):
    """H67: for each bar k in lo .. hi-1, close[k] against the close of the first bar at or after `days` days before
    bar k (its open time). NaN where there is no bar that far back (or no times): nothing is filtered there.
    -> an array as long as `close`, filled only for lo .. hi-1."""
    out = np.full(len(close), np.nan)
    if times_ms is None or hi <= lo:
        return out
    t = np.asarray(times_ms, dtype="int64")
    back = np.searchsorted(t, t[lo:hi] - int(days) * 86400000)
    ok = t[lo:hi] - t[0] >= int(days) * 86400000               # a bar that far back exists
    k = np.arange(lo, hi)
    out[k[ok]] = close[k[ok]] / close[back[ok]] - 1.0
    return out


def pullback_limit(aux, i, side, close):
    """-> (price, label) of the limit for an entry decided at the close of bar i, or None.
    Candidates in the trade's favour (below the close for a long, above for a short) and within
    PB_RANGE_ATR1H x ATR(1h): the golden-zone edges (0.5 and 0.618) of a 1h / 4h Fibonacci leg running
    the trade's way and not broken, and the 20/50/200 EMAs and SMAs of the 15m and 1h charts. The one
    nearest the price is taken (the likeliest to fill)."""
    atr = aux["atr1h"][i]
    if not (atr > 0) or close != close:
        return None
    best = None

    def consider(px, label):
        nonlocal best
        if px == px and 0 < side * (close - px) <= PB_RANGE_ATR1H * atr:
            if best is None or side * (close - px) < side * (close - best[0]):
                best = (float(px), label)

    for tf, f in aux["fib"].items():
        d = f["dir"][i]
        if d == d and int(round(d)) == side and f["broken"][i] == 0:
            for r in ("0.5", "0.618"):
                consider(f[r][i], "Fib %s %s" % (tf, r))
    for label, arr in aux["ma"].items():
        consider(arr[i], label.replace("ema", "EMA ").replace("sma", "SMA "))
    return best


# =====================================================================================
# the book
# =====================================================================================
def _stop_word(t1_hit, trail_on):
    return "STOP_BE" if t1_hit else "TRAIL" if trail_on else "STOP"


ARM_WORDS, ma_basis = exits.ARM_WORDS, exits.ma_basis          # H36: the trail's words (engine15/exits.py)


def _blank_stats():
    return {"n": 0, "wins": 0, "pnl": 0.0, "r_sum": 0.0, "r_n": 0, "win_usd": 0.0, "loss_usd": 0.0}


def run(px, odds, shock, tide, unit, cfg, lo, hi, state=None, bias=None, guard=None, rule=None, aux=None,
        times_ms=None, row_of=None):
    """One asset's book over sessions lo .. hi-1 under `rule` (flags: flip_limit, targets, trail,
    pullback; none = the main book). `state` resumes a book exactly where an earlier call stopped.
    row_of(k) -> the readings row at decision bar k for live.plan_targets (b_targets only).
    -> {"trades": closed trades, "equity": marked equity per session, "held": side held, "state": ...}"""
    rule = rule or {}
    if rule.get("swing"):                                        # workstream M: a different book (intraday.run_swing)
        from .intraday import run_swing
        return run_swing(px, odds, unit, cfg, lo, hi, state=state, guard=guard, rule=rule, aux=aux, times_ms=times_ms)
    flip_limit, use_targets, trail, pullback = (bool(rule.get(k)) for k in ("flip_limit", "targets", "trail", "pullback"))
    be_t1, half_t1 = bool(rule.get("be_t1")), bool(rule.get("half_t1"))          # H36: break-even / half at Target 1
    # v5.2.9 (owner, 22 Nov 2026, "Cut the 15-minute delay"): a new entry from flat is booked AT THE CLOSE THAT DECIDES
    # IT, at that close's price, instead of at the next bar's open one step later. It is the same moment (a close is the
    # next bar's open time) and uses closed bars only; the position is then in the book's state, and so on the page, in
    # setups.json and in the vault's book, in the step that decided it. Only where the rule asks ("early") AND config
    # names the market (CFG["early_entry"] -> asset_cfg's "early_fill", exactly True: a cfg that did not come through
    # asset_cfg never has it) AND fills are not delayed. Flips and exits keep their timing.
    early = bool(rule.get("early")) and cfg.get("early_fill") is True and not int(cfg.get("fill_delay_bars", 0) or 0)
    ma_key, ma_arm = rule.get("ma_trail"), rule.get("ma_arm", "1r")              # H36: the moving-average trail
    ma_arr = aux["ma"][ma_key] if ma_key else None
    need_t1 = use_targets or be_t1 or half_t1 or (ma_key is not None and ma_arm == "t1")
    every_ms = int(rule.get("every_ms") or 0)                    # Y yardsticks: decide only at 4h / daily closes
    decide_mask = rule.get("decide_mask")                        # y_1d: decide only at the market's own daily close
    o, h, l, c = px["open"], px["high"], px["low"], px["close"]
    n = len(c)
    held = np.zeros(n, dtype=np.int8)
    eq_arr = np.full(n, np.nan)
    trades = []
    fee = cfg["cost_side"]
    tms = (lambda i: None) if times_ms is None else (lambda i: int(times_ms[i]))
    st = json.loads(json.dumps(state)) if state else {}         # a private copy: the caller's state is never changed
    pos, idle, qty, entry = st.get("pos", 0), st.get("idle", 0), st.get("qty", 0.0), st.get("entry", 0.0)
    eq = st.get("eq", START_EQUITY)
    stop = np.nan if st.get("stop") is None else st["stop"]
    why_in = st.get("why_in", "")
    pending = tuple(st["pending"]) if st.get("pending") else None
    fees_paid = float(st.get("fees", 0.0))
    t_in, t_in_ms = -1, st.get("t_in_ms")
    stop0 = np.nan if st.get("stop0") is None else st["stop0"]
    qty0 = st.get("qty0", qty)
    tg = {"t1": st.get("t1"), "t2": st.get("t2"), "t1_basis": st.get("t1_basis"), "t2_basis": st.get("t2_basis"),
          "t1_hit": bool(st.get("t1_hit", False))}
    part = dict(st.get("part") or {"pnl": 0.0, "fees": 0.0, "qpx": 0.0, "q": 0.0, "tags": []})
    trail_on = bool(st.get("trail_on", False))
    ma_on = bool(st.get("ma_on", False))                         # H36: the MA trail is armed
    trail_px = st.get("trail_px")                                # H36: its level (ratcheted, never loosens)
    leg = dict(st["leg"]) if st.get("leg") else None            # h3: the old position closing on a limit
    order = dict(st["order"]) if st.get("order") else None      # a_pullback: an entry limit resting
    stats = dict(st.get("stats") or _blank_stats())
    wait_stop = bool(rule.get("wait_after_stop"))                # H68: no forced entry after an entry-stop exit
    ws = dict(st.get("wait_stop") or {"on": 0, "blocked": 0, "episodes": 0}) if wait_stop else None

    def book_trade(i, price, why, p_in, side, q0, s0, wi, ti, ti_ms, pnl, fees_t, t1=None, t2=None):
        risk = q0 * abs(p_in - s0) if s0 == s0 else np.nan
        r = pnl / risk if risk and risk == risk else np.nan
        trades.append((ti_ms, tms(i), ti, i, side, p_in, price, wi, why, pnl / (q0 * p_in) * 100.0, eq,
                       q0, pnl, fees_t, s0, risk, r, t1, t2))
        stats["n"] += 1
        stats["wins"] += int(pnl > 0)
        stats["pnl"] += pnl
        stats["win_usd" if pnl > 0 else "loss_usd"] += pnl if pnl > 0 else -pnl
        if r == r:
            stats["r_sum"] += r
            stats["r_n"] += 1

    def close(i, price, why):
        """Close what is left of the position at `price` (run_book's formula, plus any partials)."""
        nonlocal pos, qty, eq, stop, fees_paid, part, trail_on, ma_on, trail_px
        gross = qty * pos * (price - entry)
        fees = fee * qty * (entry + price)
        eq += gross - fees
        fees_paid += fees
        if part["q"]:                                            # b_targets: Target 1 was taken earlier
            tot_q = part["q"] + qty
            p_out = (part["qpx"] + qty * price) / tot_q
            book_trade(i, p_out, "+".join(part["tags"] + [why]), entry, pos, tot_q, stop0, why_in, t_in, t_in_ms,
                       part["pnl"] + gross - fees, part["fees"] + fees, tg["t1"], tg["t2"])
        else:
            book_trade(i, price, why, entry, pos, qty, stop0, why_in, t_in, t_in_ms, gross - fees, fees, tg["t1"], tg["t2"])
        pos, qty, stop = 0, 0.0, np.nan
        part = {"pnl": 0.0, "fees": 0.0, "qpx": 0.0, "q": 0.0, "tags": []}
        trail_on = ma_on = False
        trail_px = None
        tg.update(t1=None, t2=None, t1_basis=None, t2_basis=None, t1_hit=False)

    def take_part(i, price, q, tag):
        nonlocal qty, eq, fees_paid
        gross = q * pos * (price - entry)
        fees = fee * q * (entry + price)
        eq += gross - fees
        fees_paid += fees
        part["pnl"] += gross - fees
        part["fees"] += fees
        part["qpx"] += q * price
        part["q"] += q
        part["tags"].append(tag)
        qty -= q

    def close_leg(i, price, why):
        nonlocal leg, eq, fees_paid
        g = leg
        gross = g["qty"] * g["side"] * (price - g["entry"])
        fees = fee * g["qty"] * (g["entry"] + price)
        eq += gross - fees
        fees_paid += fees
        book_trade(i, price, why, g["entry"], g["side"], g["qty"], g["stop0"] if g["stop0"] is not None else np.nan,
                   g["why_in"], g["i_in"], g["t_in_ms"], gross - fees, fees, g.get("t1"), g.get("t2"))
        leg = None

    def open_pos(i, side, price, why, k_dec, at_ms=None):
        nonlocal pos, entry, qty, t_in, t_in_ms, why_in, stop, stop0, qty0, trail_on, ma_on, trail_px
        from .backtest import leverage as _lev                    # the main book's own sizing rule
        pos, entry, qty, t_in, why_in = side, price, eq * _lev(cfg, price, cfg["stop_units"] * unit[i - 1]) / price, i, why
        t_in_ms = tms(i) if at_ms is None else at_ms              # an early entry: bar i may not be in the data yet
        stop = entry - pos * cfg["stop_units"] * unit[i - 1]
        stop0, qty0, trail_on = stop, qty, False
        ma_on, trail_px = False, None
        if ws is not None:
            ws["on"] = 0                                         # H68: a trade is entered: the wait is over
        tg.update(t1=None, t2=None, t1_basis=None, t2_basis=None, t1_hit=False)
        if need_t1 and row_of is not None:
            from .live import plan_targets
            t = plan_targets(int(pos), float(entry), float(stop), row_of(k_dec))
            tg.update(t1=t.get("target_1"), t2=t.get("target_2"), t1_basis=t.get("target_1_basis"),
                      t2_basis=t.get("target_2_basis"))

    def stop_hit(i, side, level):
        return (side == 1 and l[i] <= level) or (side == -1 and h[i] >= level)

    def stop_px(i, side, level):
        return min(o[i], level) if side == 1 else max(o[i], level)

    p_up, p_dn = odds[:, labels.UP], odds[:, labels.DOWN]
    trend_days = int(rule.get("trend_days") or 0)                # H67: the market's own N-day move at each deciding close
    move = (aux or {}).get("trend_move") if trend_days else None
    if trend_days and move is None:
        move = trend_move(times_ms, c, trend_days, lo, hi)
    for i in range(lo, hi):
        # ---- 1. fills at this open
        if leg is not None and leg["left"] <= 0:                 # h3: the limit rested its 4 bars: market now
            close_leg(i, o[i], "FLIP_MKT")
        if order is not None and order["left"] <= 0:             # a_pullback: no fill in 8 bars: market now
            open_pos(i, order["side"], o[i], order["a"] + "_MKT", i - 1)
            order = None
        if pending is not None and len(pending) > 3 and pending[3] > 0:   # a late feed: the order waits a bar
            pending = tuple(pending[:3]) + (pending[3] - 1,)
        elif pending is not None:
            a, target, why = pending[:3]
            if pos != 0 and target != pos:
                if flip_limit:                                   # H3: the old position closes on a limit
                    if leg is not None:                          # an older limit still resting: chase it now
                        close_leg(i, o[i], "FLIP_MKT")
                    s0 = None if stop0 != stop0 else float(stop0)
                    leg = {"side": int(pos), "qty": float(qty), "entry": float(entry), "stop": float(stop), "stop0": s0,
                           "why_in": why_in, "i_in": int(t_in), "t_in_ms": t_in_ms, "left": H3_BARS,
                           "limit": float(o[i] + pos * H3_K * aux["atr15"][i - 1])}
                    if leg["limit"] != leg["limit"]:             # no ATR yet: the plain market exit
                        leg["limit"] = float(o[i])
                    pos, qty, stop = 0, 0.0, np.nan
                    trail_on = ma_on = False
                    trail_px = None
                    tg.update(t1=None, t2=None, t1_basis=None, t2_basis=None, t1_hit=False)
                else:
                    close(i, o[i], a)
            if target != 0 and pos == 0:
                open_pos(i, target, o[i], a, i - 1)
            pending = None
        if order is not None:                                    # a_pullback: does this bar fill the limit?
            s, lim = order["side"], order["limit"]
            if (s == 1 and l[i] < lim) or (s == -1 and h[i] > lim):
                open_pos(i, s, lim, order["a"] + "_LMT", i - 1)
                order = None
            else:
                order["left"] -= 1
        held[i] = pos
        # ---- 2. the protective stops, first inside the bar
        if leg is not None:
            if stop_hit(i, leg["side"], leg["stop"]):
                close_leg(i, stop_px(i, leg["side"], leg["stop"]), "STOP")
            elif (leg["side"] == 1 and h[i] > leg["limit"]) or (leg["side"] == -1 and l[i] < leg["limit"]):
                close_leg(i, leg["limit"], "FLIP_LMT")
            else:
                leg["left"] -= 1
        be_moved = tg["t1_hit"] and (use_targets or be_t1)       # the stop sits at break-even
        if pos == 1 and l[i] <= stop:
            word = _stop_word(be_moved, trail_on)
            close(i, min(o[i], stop), word)
            idle = 0
            if ws is not None and word == "STOP":
                ws["on"] = 1                                     # H68: out at the entry stop: wait for a signal
        elif pos == -1 and h[i] >= stop:
            word = _stop_word(be_moved, trail_on)
            close(i, max(o[i], stop), word)
            idle = 0
            if ws is not None and word == "STOP":
                ws["on"] = 1
        # ---- 2b. targets (b_targets): Target 1 then Target 2, both may fill in one bar
        if use_targets and pos != 0 and tg["t1"] is not None:
            reach = (lambda t: h[i] >= t) if pos == 1 else (lambda t: l[i] <= t)
            if not tg["t1_hit"] and reach(tg["t1"]):
                take_part(i, tg["t1"], qty * PART, "T1")
                tg["t1_hit"] = True
                stop = entry                                     # break-even, live from the next bar
            if tg["t1_hit"] and tg["t2"] is not None and pos != 0 and reach(tg["t2"]):
                close(i, tg["t2"], "T2")
                idle = 0
        elif need_t1 and pos != 0 and tg["t1"] is not None and not tg["t1_hit"]:
            # H36: Target 1 trades in this bar (after the stop check). Half off (half_t1); the stop to
            # break-even (be_t1), live from the next bar and only ever tighter; arms a "t1" MA trail.
            if exits.reached(pos, h[i], l[i], tg["t1"]):
                tg["t1_hit"] = True
                if half_t1:
                    take_part(i, tg["t1"], qty * PART, "T1")
                if be_t1:
                    stop = exits.be_stop(pos, entry, stop)
        # ---- 2c. the trailing stop (b_trail), set at this close for the bars that follow
        if trail and pos != 0 and stop0 == stop0:
            R = abs(entry - stop0)
            if not trail_on and R > 0 and pos * ((h[i] if pos == 1 else l[i]) - entry) >= TRAIL_ARM_R * R:
                trail_on = True
            if trail_on:
                cands = [c[i] - pos * TRAIL_ATR * aux["atr15"][i]]
                sw = aux["sw_lo"][i] if pos == 1 else aux["sw_hi"][i]
                if sw == sw and pos * (c[i] - sw) > 0:
                    cands.append(sw)
                cands = [x for x in cands if x == x]
                if cands:
                    tight = max(cands) if pos == 1 else min(cands)
                    stop = max(stop, tight) if pos == 1 else min(stop, tight)
        # ---- 2d. the moving-average trail (H36), read at this close: the level is the MA of bars <= i
        # (15m, or the last CLOSED 1h bar via mavg's htf join), ratcheted so it never loosens; a close
        # beyond it against the position exits at the next open. It counts only once it is tighter
        # than the protective stop, which stays live inside every bar.
        ma_exit = False
        if ma_arr is not None and pos != 0 and stop0 == stop0:
            ma_on, trail_px, ma_exit = exits.ma_trail_step(pos, entry, stop, stop0, ma_on, trail_px, ma_arm, tg["t1_hit"],
                                                           h[i], l[i], c[i], ma_arr[i])
        # ---- 3. the decision at this close (a resting entry limit counts as the position it will be)
        if (every_ms and times_ms is not None and (int(times_ms[i]) + CFG["bar_ms"]) % every_ms) or \
                (decide_mask is not None and not decide_mask[i]):
            eq_arr[i] = eq + (qty * pos * (c[i] - entry) if pos else 0.0) + \
                (leg["qty"] * leg["side"] * (c[i] - leg["entry"]) if leg is not None else 0.0)
            continue                                             # not a 4h / daily close: no decision, stops still live
        intent = pos if pos != 0 else (order["side"] if order is not None else 0)
        pu = p_up[i]
        a, target, why = policy.decide(intent, idle, None if pu != pu else pu, p_dn[i], bool(shock[i]),
                                       tide[i] if tide[i] == tide[i] else 0.0, cfg,
                                       bias=0 if bias is None or bias[i] != bias[i] else int(bias[i]),
                                       guard=False if guard is None else bool(guard[i]))
        if ws is not None and ws["on"] and pos == 0 and a == policy.FORCED:
            a, target, why = policy.IDLE, 0, "wait_for_signal_after_stop"   # H68: only a signal enters now
            ws["blocked"] += 1
            if ws["on"] == 1:
                ws["on"], ws["episodes"] = 2, ws["episodes"] + 1
        if move is not None and target != 0 and a in (policy.ENTER, policy.FORCED, policy.FLIP):
            mv = move[i]
            if mv == mv and mv != 0 and (mv > 0) != (target > 0):    # H67: the new side is against the N-day move
                if a == policy.FLIP:
                    target, why = 0, "trend_filter_flat"          # the position is closed at the next open; nothing opens
                else:
                    a, target, why = policy.IDLE, 0, "trend_filter"   # no entry; the idle count goes on
        if a == policy.IDLE:
            idle += 1
        elif a == policy.STEP_ASIDE:
            idle = 1
        elif a != policy.HOLD:
            idle = 0
        if order is not None and a in (policy.FLIP, policy.STEP_ASIDE):     # the waiting entry is called off
            order = None                                         # (a FLIP then enters the other side, below)
        if a in (policy.ENTER, policy.FORCED, policy.FLIP, policy.STEP_ASIDE):
            lim = None
            if pullback and pos == 0 and target != 0 and a in (policy.ENTER, policy.FORCED, policy.FLIP):
                lim = pullback_limit(aux, i, target, c[i])
            if lim is not None:
                order = {"side": int(target), "limit": lim[0], "basis": lim[1], "left": PB_BARS, "a": a, "why": why}
            elif (early and pos == 0 and target != 0 and pending is None and leg is None
                  and a in (policy.ENTER, policy.FORCED)):
                # v5.2.9: held from the next bar on (bar i + 1), entered at this close's price; the stop and the targets
                # come from this bar's own readings, exactly what the fill one bar later used. held[i] stays flat.
                open_pos(i + 1, target, c[i], a, i,
                         at_ms=None if times_ms is None else int(times_ms[i]) + CFG["bar_ms"])
            elif not (a == policy.STEP_ASIDE and pos == 0):
                delay = int(cfg.get("fill_delay_bars", 0) or 0)   # same late-feed rule as the main book
                if not (delay and pending is not None and pending[1] == target):
                    pending = (a, target, why) if not delay else (a, target, why, delay)
        elif ma_exit and pos != 0 and not (pending is not None and pending[1] == 0):
            # H36: the MA trail closes the position at the next open (a flip or step-aside decided at this
            # close takes precedence above). Flat after it, the normal rules decide from the next close.
            delay = int(cfg.get("fill_delay_bars", 0) or 0)
            pending = ("TRAIL_MA", 0, "ma_trail") if not delay else ("TRAIL_MA", 0, "ma_trail", delay)
        eq_arr[i] = eq + (qty * pos * (c[i] - entry) if pos else 0.0) + \
            (leg["qty"] * leg["side"] * (c[i] - leg["entry"]) if leg is not None else 0.0)
    if hi > lo:
        last = hi - 1
    else:
        last = None
    end = {"pos": int(pos), "idle": int(idle), "qty": float(qty), "entry": float(entry),
           "stop": None if stop != stop else float(stop), "eq": float(eq), "why_in": why_in,
           "pending": list(pending) if pending else None, "fees": float(fees_paid), "i_in": int(t_in),
           "t_in_ms": t_in_ms if pos else None, "stop0": None if (stop0 != stop0 or not pos) else float(stop0),
           "qty0": float(qty0) if pos else 0.0, "t1": tg["t1"], "t2": tg["t2"], "t1_basis": tg["t1_basis"],
           "t2_basis": tg["t2_basis"], "t1_hit": tg["t1_hit"], "part": part if part["q"] else None,
           "trail_on": trail_on, "leg": leg, "order": order, "stats": stats}
    if ma_key or be_t1 or half_t1:                               # H36 books only (older books' state unchanged)
        end.update(ma_on=bool(ma_on and pos), trail_px=None if (trail_px is None or not pos) else float(trail_px),
                   trail_basis=ma_basis(ma_key) if ma_key else None,
                   trail_arm=ARM_WORDS.get(ma_arm) if ma_key else None, be_t1=be_t1, half_t1=half_t1)
    if ws is not None:                                           # H68 books only (every other book's state unchanged)
        end["wait_stop"] = {"on": int(ws["on"]), "blocked": int(ws["blocked"]), "episodes": int(ws["episodes"])}
    if last is not None:
        end["mark"] = float(c[last])
        end["mark_ms"] = tms(last)
        end["equity_marked"] = float(eq_arr[last])
    tr = pd.DataFrame(trades, columns=TRADE_COLS)
    return {"trades": tr, "equity": eq_arr, "held": held, "state": end}


def book_inputs(prep, a):
    """The main book's own inputs for one asset (backtest._books / live.step_group)."""
    ev, cfg = prep["ev"][a], prep["cfg"]
    return dict(px=prep["px"][a], odds=prep["odds"][a], shock=ev["shock"].values, tide=ev["tide"].values,
                unit=(cfg["barrier_atr"] * ev["atr1h"]).values,
                bias=ev["htf_bias"].values if "htf_bias" in ev else None,
                guard=ev["release_soon"].values if "release_soon" in ev else None)


def asset_cfg(a, cfg):
    return dict(cfg, cost_side=CFG.get("asset_cost", {}).get(a, cfg["cost_side"]),
                leverage_cap=CFG.get("max_leverage", {}).get(a, 1.0),
                fill_delay_bars=CFG.get("fill_delay", {}).get(a, 0),
                early_fill=a in (CFG.get("early_entry") or ()))   # v5.2.9: only a rule that asks for it uses this


def daily_close_mask(asset, times):
    """True on the bar that ends each market's trading day: the last bar before the market shuts
    (S&P 16:00 New York; gold, silver, USDJPY, oil at their daily break / 17:00 New York). Crypto
    never shuts: its day ends at 00:00 UTC. Known from the market calendar, never from future bars."""
    bar = pd.Timedelta(milliseconds=CFG["bar_ms"])
    idx = pd.DatetimeIndex(times)
    try:
        from . import extdata
        if asset in extdata.MARKETS:
            if extdata.MARKETS[asset]["session"] == "fx":            # FX trades through: its day ends at 17:00 New York
                loc = extdata._local(idx + bar, extdata.NY)
                return np.asarray((np.asarray(loc.hour) == 17) & (np.asarray(loc.minute) == 0)) & np.asarray(extdata.open_mask(asset, idx))
            open_now = extdata.open_mask(asset, idx)
            open_next = extdata.open_mask(asset, idx + bar)
            return np.asarray(open_now & ~open_next)
    except Exception:
        pass
    ms = data.to_ms(idx)
    return (np.asarray(ms, dtype="int64") + CFG["bar_ms"]) % 86400000 == 0


def h5_odds(prep, a, factor=0.5):
    """H5: the engine's odds with the "strategies" voice's trust share halved on sessions where the
    1h and 4h market structure (ms_1h, ms_4h) both point against that voice's lean; the freed share
    goes to the other speaking voices pro rata (the same mixing as backtest.prepare)."""
    from . import model
    names = list(model.VOICE_NAMES)
    if "strategies" not in names or any(key not in prep for key in ("probs", "trust", "X", "ev")):
        return prep["odds"][a]                                   # nothing to damp with: the main odds
    k = names.index("strategies")
    if "lean_lo" in prep:                                        # the live step's lean prep: rows from lean_lo only
        return _h5_odds_lean(prep, a, k, factor)                 # (before it there are no calls: NaN, as here)
    probs, trust, X, ev = prep["probs"][a], np.array(prep["trust"], dtype=float), prep["X"][a], prep["ev"][a]
    n = len(prep["times"])
    speaks = np.stack([(np.abs(X[:, model._COLS[v]]).sum(axis=1) > 0) if model._COLS[v] else np.zeros(n, bool)
                       for v in names], axis=1)
    lean = probs[:, k, labels.UP] - probs[:, k, labels.DOWN]
    m1 = ev["ms_1h"].fillna(0).values if "ms_1h" in ev else np.zeros(n)
    m4 = ev["ms_4h"].fillna(0).values if "ms_4h" in ev else np.zeros(n)
    turn = (np.sign(m1) == np.sign(m4)) & (np.sign(m1) != 0) & (np.sign(m1) * np.nan_to_num(lean) < 0)
    w = trust * speaks
    w[turn, k] *= factor
    tot = w.sum(axis=1, keepdims=True)
    w = np.where(tot > 0, w / np.where(tot > 0, tot, 1.0), trust)
    return model.mix(probs, w)


def _h5_odds_lean(prep, a, k, factor):
    """h5_odds on leanprep's prep: the same arithmetic on rows lean_lo .. n-1, NaN before."""
    from . import model
    names = list(model.VOICE_NAMES)
    n, lo = len(prep["times"]), int(prep["lean_lo"])
    probs, trust = prep["probs"][a].arr, np.array(prep["trust"].arr, dtype=float)
    X, ev = np.asarray(prep["X"][a][lo:n]), prep["ev"][a]
    speaks = np.stack([(np.abs(X[:, model._COLS[v]]).sum(axis=1) > 0) if model._COLS[v] else np.zeros(n - lo, bool)
                       for v in names], axis=1)
    lean = probs[:, k, labels.UP] - probs[:, k, labels.DOWN]
    m1 = ev["ms_1h"].fillna(0).values[lo:] if "ms_1h" in ev else np.zeros(n - lo)
    m4 = ev["ms_4h"].fillna(0).values[lo:] if "ms_4h" in ev else np.zeros(n - lo)
    turn = (np.sign(m1) == np.sign(m4)) & (np.sign(m1) != 0) & (np.sign(m1) * np.nan_to_num(lean) < 0)
    w = trust * speaks
    w[turn, k] *= factor
    tot = w.sum(axis=1, keepdims=True)
    w = np.where(tot > 0, w / np.where(tot > 0, tot, 1.0), trust)
    out = np.full((n, 3), np.nan)
    out[lo:] = model.mix(probs, w)
    return out


def run_challenger(name, prep, a, lo, hi, cfg=None, state=None, aux=None, swing=None):
    """One challenger on one asset of a prepared market group (live or history).
    swing: intraday.live_minds' output, the odds of the swing books (absent: they stay flat)."""
    spec = CHALLENGERS[name]
    cfg = asset_cfg(a, dict(cfg or prep["cfg"], **spec["cfg"]))
    inp = book_inputs(prep, a)
    if spec["rule"].get("swing"):
        rule = spec["rule"]
        n = len(inp["px"]["close"])
        od = ((swing or {}).get(rule["mind"]) or {}).get("odds", {}).get(a)
        if od is None:
            od = np.full((n, 3), np.nan)
        unit = rule["barrier_atr"] * np.asarray(prep["ev"][a]["atr1h"].values, dtype=float)
        aux = aux if aux is not None else aux_from_ev(prep["ev"][a], inp["px"])
        return run(inp["px"], od, inp["shock"], inp["tide"], unit, cfg, lo, hi, state=state, guard=inp["guard"],
                   rule=rule, aux=aux, times_ms=data.to_ms(prep["times"]))
    if spec["rule"].get("h5"):
        inp = dict(inp, odds=h5_odds(prep, a))
    rule = spec["rule"]
    if rule.get("daily_close"):
        rule = dict(rule, decide_mask=daily_close_mask(a, prep["times"]))
    aux = aux if aux is not None else aux_from_ev(prep["ev"][a], inp["px"])
    tgt = aux["targets"]
    times_ms = data.to_ms(prep["times"])
    return run(inp["px"], inp["odds"], inp["shock"], inp["tide"], inp["unit"], cfg, lo, hi, state=state,
               bias=inp["bias"], guard=inp["guard"], rule=rule, aux=aux, times_ms=times_ms,
               row_of=lambda k: tgt.iloc[k] if len(tgt.columns) else pd.Series(dtype=float))


# =====================================================================================
# forward books, one step per closed session (called by live.step_group)
# =====================================================================================
def load_state(path=STATE_PATH):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {"version": 1, "groups": {}, "books": {}}


def save_state(st, path=STATE_PATH):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=1, default=float)
    os.replace(tmp, path)


def _ms(t):
    return int(pd.Timestamp(t).timestamp() * 1000)


def _utc(ms):
    return None if ms is None else str(pd.Timestamp(int(ms), unit="ms", tz="UTC"))[:16]


def _main_marked(book, mark):
    if not book:
        return None
    unreal = book["qty"] * book["pos"] * (mark - book["entry"]) if book.get("pos") else 0.0
    return float(book["eq"] + unreal)


def swing_odds(prep, group, log=print):
    """The 1h / 4h minds' odds for the swing books (intraday.live_minds), or None when the prep has no
    evidence matrix (tests) or they fail (the other books go on)."""
    if not any(s["rule"].get("swing") for s in CHALLENGERS.values()):
        return None
    if any(k not in prep for k in ("X", "ready", "ev", "y", "odds", "assets")):
        return None
    try:
        from . import intraday
        out = intraday.live_minds(prep, group, log=log)
        log("%s: intraday minds (1h, 4h) in %.1fs" % (group, out.get("_seconds", 0.0)))
        return out
    except Exception as e:
        log("%s: intraday minds failed: %r" % (group, e))
        return None


def advance(prep, group, assets, n, sst, cfg=None, start_lo=None, main_books=None, log=None):
    """Advance every challenger of one market group to session n-1 (pure: changes `sst` only).
    A group seen for the first time starts at session n-1 (start_lo overrides, for tests).
    -> (summary of the group, {(challenger, asset): closed-trades frame})"""
    times = prep["times"]
    g = sst["groups"].get(group)
    if g is None:
        lo = n - 1 if start_lo is None else int(start_lo)
        g = sst["groups"][group] = {"started_ms": _ms(times[lo]),          # the session whose close they first read
                                    "started_utc": str(times[lo] + pd.Timedelta(milliseconds=CFG["bar_ms"]))[:16],
                                    "start_close": dict((a, float(prep["px"][a]["close"][lo])) for a in assets),
                                    "main_start_eq": dict((a, _main_marked((main_books or {}).get(a),
                                                                           float(prep["px"][a]["close"][lo])))
                                                          for a in assets), "last_ms": None}
    elif g.get("last_ms") is None:                               # started, but no session was processed yet
        lo = int(times.searchsorted(pd.Timestamp(g["started_ms"], unit="ms", tz="UTC")))
    else:
        lo = int(times.searchsorted(pd.Timestamp(g["last_ms"], unit="ms", tz="UTC"), side="right"))
    closed = {}
    if lo < n:
        swing = swing_odds(prep, group, log=log or (lambda *_: None))
        late = g.get("last_ms") is not None                      # a book added after the group started (H36 ...)
        for a in assets:
            aux = aux_from_ev(prep["ev"][a], prep["px"][a])
            main_before = (sst["books"].get("main") or {}).get(a) or {}
            main_run = None
            for name in CHALLENGERS:
                books = sst["books"].setdefault(name, {})
                if late and books.get(a) is None and name != "main":
                    # starts flat now: remember when, and the fresh main copy's marked equity then, so the
                    # scoreboard compares it with main over the same time only
                    sst.setdefault("late_starts", {}).setdefault(name, {})[a] = {
                        "ms": _ms(times[lo]), "utc": str(times[lo] + pd.Timedelta(milliseconds=CFG["bar_ms"]))[:16],
                        "main_eq": main_before.get("equity_marked", main_before.get("eq"))}
                b = run_challenger(name, prep, a, lo, n, cfg=cfg, state=books.get(a), aux=aux, swing=swing)
                books[a] = b["state"]
                if len(b["trades"]):
                    closed[(name, a)] = b["trades"]
                if name == "main":
                    main_run = b
            for name in FOLLOWERS:                               # after every book above; never in their way
                try:
                    fbooks = sst["books"].get(name) or {}
                    fee = asset_cfg(a, dict(cfg or prep["cfg"]))["cost_side"]
                    rows, fst = floor_book.follow(main_before, main_run, prep["px"][a], data.to_ms(times), lo, n, fee,
                                                  state=fbooks.get(a))
                    if fst.get("copied_ms") is not None and "copied_utc" not in fst:
                        fst["copied_utc"] = str(times[lo] + pd.Timedelta(milliseconds=CFG["bar_ms"]))[:16]
                    sst["books"].setdefault(name, {})[a] = fst
                    if rows:
                        closed[(name, a)] = pd.DataFrame(rows, columns=TRADE_COLS)
                except Exception as e:
                    (log or (lambda *_: None))("%s: follower book %s failed on %s: %r" % (group, name, a, e))
        g["last_ms"] = _ms(times[n - 1])
    return summary(group, assets, sst, prep, n, main_books), closed


def _px(v):
    if v is None or v != v:
        return None
    v = float(v)
    return round(v, 5 if abs(v) < 100 else 3 if abs(v) < 1000 else 2)


def held_share(st):
    """The share of the position's starting size still held: qty / qty0, in (0, 1] (1.0 until a part is closed, then
    1 - PART). None when the book is flat or the state does not carry both sizes."""
    st = st or {}
    q, q0 = st.get("qty"), st.get("qty0")
    if not st.get("pos") or not isinstance(q, (int, float)) or not isinstance(q0, (int, float)):
        return None
    if not (q0 > 0 and 0 < q <= q0 * (1 + 1e-9)):
        return None
    return round(min(1.0, q / q0), 6)


def asset_view(st):
    """The compact page view of one challenger's book on one asset."""
    st = st or {}
    mark = st.get("mark")
    pos = st.get("pos", 0)
    stats = st.get("stats") or _blank_stats()
    v = {"status": {1: "LONG", -1: "SHORT"}.get(pos, "FLAT"), "equity": round(st.get("equity_marked", st.get("eq", START_EQUITY)), 2),
         "realized_usd": round(st.get("eq", START_EQUITY) - START_EQUITY, 2), "fees_usd": round(st.get("fees", 0.0), 2),
         "trades": stats["n"], "wins": stats["wins"]}
    if pos:
        v.update(entry=_px(st["entry"]), stop=_px(st.get("stop")), opened_utc=_utc(st.get("t_in_ms")),
                 opened_by=st.get("why_in"), unrealized_usd=round(st["qty"] * pos * (mark - st["entry"]), 2) if mark else None)
        if st.get("t1") is not None:
            v.update(target_1=_px(st["t1"]), target_2=_px(st.get("t2")), t1_taken=bool(st.get("t1_hit")))
            hs = held_share(st)                                  # 20 Nov 2026: what is left after Target 1, published
            if hs is not None:
                v["held_share"] = hs
        if st.get("trail_on"):
            v["trailing"] = True
        if st.get("trail_basis"):                                # H36 MA trail: its level for the page
            v.update(trail_basis=st["trail_basis"], trail_arm=st.get("trail_arm"), trail_armed=bool(st.get("ma_on")),
                     trail_price=_px(st.get("trail_px")) if st.get("ma_on") else None)
        if st.get("be_t1") or st.get("half_t1"):                 # H36: where the stop stands and why
            moved = bool(st.get("t1_hit")) and bool(st.get("be_t1"))
            v["stop_basis"] = "break-even (Target 1 traded)" if moved else "the entry stop (2 barriers)"
    if st.get("floor") is not None:                              # the profit-floor follower (floor_book.py)
        v["floor_armed"] = bool(st["floor"].get("armed"))
        if pos:
            v["stop_basis"] = ("the floor: a third of the best closed profit" if v["floor_armed"]
                               else "the entry stop (the floor arms at 3R)")
        elif st.get("wait_main"):
            v["waiting_for"] = "the hold copy's next entry"
        if st.get("copied_utc"):
            v["copied_from_main_utc"] = st["copied_utc"]
    if st.get("order"):
        o = st["order"]
        v.update(status="WAITING " + {1: "LONG", -1: "SHORT"}[o["side"]], limit=_px(o["limit"]), limit_basis=o["basis"],
                 bars_left=int(o["left"]))
    if st.get("leg"):
        lg = st["leg"]
        v["closing"] = {"side": {1: "LONG", -1: "SHORT"}[lg["side"]], "limit": _px(lg["limit"]), "bars_left": int(lg["left"])}
    if st.get("pending"):
        v["next_open"] = "%s -> %s" % (st["pending"][0], {1: "LONG", -1: "SHORT", 0: "FLAT"}[int(st["pending"][1])])
    return v


def summary(group, assets, sst, prep=None, n=None, main_books=None):
    """-> {"started_utc", "assets": {...}, "books": {challenger: {asset: view}}} for one market group."""
    g = sst["groups"].get(group) or {}
    last = g.get("last_ms")
    out = {"started_utc": g.get("started_utc"), "as_of_utc": None if last is None else _utc(last + CFG["bar_ms"]), "assets": {},
           "books": OrderedDict()}
    fee_of = lambda a: CFG.get("asset_cost", {}).get(a, CFG["cost_side"])      # noqa: E731
    for a in assets:
        now = float(prep["px"][a]["close"][n - 1]) if prep is not None else None
        c0 = (g.get("start_close") or {}).get(a)
        row = {"start_price": _px(c0), "price": _px(now)}
        if now and c0:
            row["buy_hold_equity"] = round(START_EQUITY * now / c0 * (1 - 2 * fee_of(a)), 2)
        m0 = (g.get("main_start_eq") or {}).get(a)
        m1 = _main_marked((main_books or {}).get(a), now) if now else None
        if m0 is not None and m1 is not None:
            row["main_book_change_usd"] = round(m1 - m0, 2)
        out["assets"][a] = row
    late = sst.get("late_starts") or {}
    for name, spec in CHALLENGERS.items():
        out["books"][name] = {"title": spec["title"],
                              "assets": dict((a, asset_view(sst["books"].get(name, {}).get(a))) for a in assets)}
        for a in assets:
            ls = (late.get(name) or {}).get(a)
            if ls:                                               # joined after the group's start
                out["books"][name]["assets"][a].update(started_utc=ls["utc"], main_equity_at_start=ls["main_eq"])
    for name, spec in FOLLOWERS.items():
        if any(sst["books"].get(name, {}).get(a) for a in assets):
            out["books"][name] = {"title": spec["title"], "follows": spec["follows"],
                                  "assets": dict((a, asset_view(sst["books"].get(name, {}).get(a))) for a in assets)}
    return out


def scoreboard(groups):
    """Across market groups: each challenger's total equity against the fresh main copy, the main
    book's own change and buy-and-hold over the same time. groups: {group: summary}."""
    rows, names = [], list(CHALLENGERS) + list(FOLLOWERS)
    titles = dict((k, v["title"]) for k, v in list(CHALLENGERS.items()) + list(FOLLOWERS.items()))
    assets = dict((a, r) for s in groups.values() for a, r in s["assets"].items())
    main_since = {}                                              # books that joined late: main's change since then
    same_assets = {}                                             # followers: against the followed book, same assets only
    for name in names:
        eq = tr = fees = wins = 0.0
        k = 0
        since, starts = 0.0, []
        for s in groups.values():
            for a, v in s["books"].get(name, {}).get("assets", {}).items():
                eq, tr, fees, wins, k = eq + v["equity"], tr + v["trades"], fees + v["fees_usd"], wins + v["wins"], k + 1
                if name in FOLLOWERS:
                    f_eq = s["books"].get(FOLLOWERS[name]["follows"], {}).get("assets", {}).get(a, {}).get("equity")
                    if f_eq is not None:
                        same_assets[name] = same_assets.get(name, 0.0) + v["equity"] - f_eq
                    if v.get("copied_from_main_utc"):
                        starts.append(v["copied_from_main_utc"])
                if v.get("main_equity_at_start") is not None:
                    m_now = s["books"].get("main", {}).get("assets", {}).get(a, {}).get("equity")
                    since += (m_now - v["main_equity_at_start"]) if m_now is not None else 0.0
                    starts.append(v["started_utc"])
        if not k:
            continue
        rows.append({"book": name, "title": titles[name], "assets": k, "equity": round(eq, 2),
                     "pnl_usd": round(eq - START_EQUITY * k, 2), "return_pct": round((eq / (START_EQUITY * k) - 1) * 100, 2),
                     "trades": int(tr), "win_rate_pct": round(100.0 * wins / tr, 1) if tr else None, "fees_usd": round(fees, 2)})
        if name in FOLLOWERS:                                    # a copy of the followed book when it started: its
            rows[-1]["follows"] = FOLLOWERS[name]["follows"]     # P&L includes that book's until then; vs_main is
            if starts:                                           # what its own exit has changed since
                rows[-1]["since_utc"] = min(starts)
        elif starts:
            rows[-1]["since_utc"] = min(starts)
            main_since[name] = since
    base = next((r for r in rows if r["book"] == "main"), None)
    for r in rows:
        if r["book"] in FOLLOWERS:
            r["vs_main_usd"] = None if r["book"] not in same_assets else round(same_assets[r["book"]], 2)
        elif r["book"] in main_since:                            # same time only: P&L since it started minus main's
            r["vs_main_usd"] = round(r["pnl_usd"] - main_since[r["book"]], 2)
        else:
            r["vs_main_usd"] = None if base is None else round(r["equity"] - base["equity"], 2)
    bh = [r["buy_hold_equity"] for r in assets.values() if "buy_hold_equity" in r]
    mc = [r["main_book_change_usd"] for r in assets.values() if "main_book_change_usd" in r]
    starts = [s["started_utc"] for s in groups.values() if s.get("started_utc")]
    return {"since_utc": min(starts) if starts else None, "rows": rows,
            "buy_and_hold": {"assets": len(bh), "equity": round(sum(bh), 2),
                             "pnl_usd": round(sum(bh) - START_EQUITY * len(bh), 2)} if bh else None,
            "main_book_actual": {"assets": len(mc), "pnl_usd": round(sum(mc), 2),
                                 "note": "the running main book's change since the challengers started"} if mc else None,
            "note": "Paper only. Forward from the start time; promotion is decided on forward results (charter)."}


def journal_trades(closed, times=None, out_dir=TRADES_DIR):
    """Append closed trades to out/live/shadow_trades_<challenger>_<asset>.csv."""
    os.makedirs(out_dir, exist_ok=True)
    for (name, a), tr in closed.items():
        rows = tr.assign(time_in=[_utc(x) for x in tr.t_in_ms], time_out=[_utc(x) for x in tr.t_out_ms])
        rows = rows.drop(columns=["i_in", "i_out"])
        path = os.path.join(out_dir, "shadow_trades_%s_%s.csv" % (name, a))
        rows.to_csv(path, mode="a", header=not os.path.exists(path), index=False)


def step(prep, group, assets, n, cfg=None, main_books=None, path=STATE_PATH, out_dir=TRADES_DIR, log=print):
    """The live step's hook: advance, journal, save. -> the group's summary for page.json."""
    sst = load_state(path)
    view, closed = advance(prep, group, list(assets), n, sst, cfg=cfg, main_books=main_books, log=log)
    if "X" in prep:                                              # M6: the weekly skill-per-horizon report (live only)
        try:
            from . import reports
            reports.horizon_skill_weekly(log=log)
        except Exception as e:
            log("%s: horizon skill report failed: %r" % (group, e))
    if closed:
        journal_trades(closed, out_dir=out_dir)
    sst["updated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_state(sst, path)
    if closed:
        log("%s: shadow books closed %d trade(s): %s" % (group, sum(len(t) for t in closed.values()),
                                                         ", ".join("%s %s" % k for k in closed)))
    return view
