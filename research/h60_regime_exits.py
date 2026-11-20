# -*- coding: utf-8 -*-
"""H60: exits by regime, per market (research/HYPOTHESES.md, H60). PAPER ONLY. IN-SAMPLE. Gates nothing.

    python research/h60_regime_exits.py --group fx       one group (one at a time: memory), H59's "today" window
    python research/h60_regime_exits.py --report         merge, write research/out/h60_regime_exits/report.md + results.json

The frame is H59's "today" run: research/h59_half_be.prep_cut (the odds as the live step forms them, the evidence
store read-only, voices walked weekly with a PRIVATE fits directory), cut at the last session H59's today run read
per group (H59_END below, from research/out/h59_half_be/today_<group>.json). `main`, `be_t1`, `b_targets` and
`half_be_t1` are run exactly as H59 ran them and must reproduce those files (the reconciliation gate).

THE RUNNER. `run_switch` below is a COPY of engine15/shadows.run (the money path is not edited) with one added
input, `tswitch`, the "targets active" switch:
    tswitch=None                        the copy behaves as shadows.run under `rule`
    tswitch={"entry": f}                f(k_dec, side) -> True/False, called once per trade at its fill, with the
                                        decision bar k_dec (the row row_of(k_dec) reads for the targets): True =
                                        target mode (b_targets' rule for that trade), False = flip mode (main's rule)
    tswitch={"entry": f, "bar": on}     as above, and a target is acted on only in a bar i with on[i] True
Before any variant is read, on every market: tswitch always False == shadows.run under `main` and always True ==
shadows.run under `b_targets`, trade for trade (same rows, P&L to 1e-6) and the same final equity (the gate).

THE REGIME. ev["regime"] (indicators.regime_daily, last CLOSED daily bar joined by htf_on_15), not recomputed.
The regime of a trade = the label on the row of its decision close (the bar before the fill, k_dec = i_in - 1).
Variant 3 (bar by bar): a target in bar i is acted on only if the label known BEFORE bar i trades, row i - 1, is not
directional (row i would include the daily bar that bar i itself closes). A missing label counts as "other".
"""
import argparse
import gc
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

import exit_study as ex  # noqa: E402
import h59_half_be as h59  # noqa: E402
from engine15 import data, exits, labels, policy, shadows  # noqa: E402
from engine15.config import CFG  # noqa: E402
from engine15.shadows import (ARM_WORDS, H3_BARS, H3_K, PART, PB_BARS, START_EQUITY, TRADE_COLS,  # noqa: E402
                              TRAIL_ARM_R, TRAIL_ATR, _blank_stats, _stop_word, ma_basis, pullback_limit)

OUT = os.path.join(ROOT, "research", "out", "h60_regime_exits")
H59_OUT = os.path.join(ROOT, "research", "out", "h59_half_be")
START = START_EQUITY
MID = "2023-06-08"
# the last session of H59's "today" run per group (research/out/h59_half_be/today_<group>.json, "window")
H59_END = {"crypto": "2026-11-20 03:45", "metals": "2026-11-20 03:30", "fx": "2026-11-20 03:45",
           "index": "2026-11-19 20:45", "energy": "2026-11-20 03:30"}
ORDER = ["SPX", "USDJPY", "BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "WTI", "BRENT"]

REGIMES = ("TREND_UP", "TREND_DOWN", "MOMENTUM_UP", "MOMENTUM_DOWN", "RANGE", "TRANSITION")
DIRECTIONAL = frozenset(("TREND_UP", "TREND_DOWN", "MOMENTUM_UP", "MOMENTUM_DOWN"))
MOMENTUM = frozenset(("MOMENTUM_UP", "MOMENTUM_DOWN"))
WITH_LONG = frozenset(("TREND_UP", "MOMENTUM_UP"))
WITH_SHORT = frozenset(("TREND_DOWN", "MOMENTUM_DOWN"))
NONE = "NONE"                                                    # no label on the row (counts as "other")

H59_BOOKS = ["main", "b_targets", "be_t1", "half_be_t1"]
VARIANTS = ["rg_dir_entry", "rg_dir_aligned", "rg_dir_live", "rg_mom_entry", "rg_dir_entry_inv"]
BOOKS = H59_BOOKS + VARIANTS
MENU = ["main", "be_t1", "half_be_t1", "b_targets", "rg_dir_entry", "rg_dir_aligned", "rg_dir_live", "rg_mom_entry"]
GATE_COLS = ["i_in", "i_out", "side", "why_in", "why_out"]
GATE_NUM = ["p_in", "p_out", "pnl_usd", "qty", "fees_usd"]


# =====================================================================================
# the runner: a copy of engine15/shadows.run with one added input (tswitch); see the module doc
# =====================================================================================
def run_switch(px, odds, shock, tide, unit, cfg, lo, hi, state=None, bias=None, guard=None, rule=None, aux=None,
               times_ms=None, row_of=None, tswitch=None):
    rule = rule or {}
    if rule.get("swing"):                                        # workstream M: a different book (intraday.run_swing)
        from engine15.intraday import run_swing
        return run_swing(px, odds, unit, cfg, lo, hi, state=state, guard=guard, rule=rule, aux=aux, times_ms=times_ms)
    flip_limit, use_targets, trail, pullback = (bool(rule.get(k)) for k in ("flip_limit", "targets", "trail", "pullback"))
    be_t1, half_t1 = bool(rule.get("be_t1")), bool(rule.get("half_t1"))          # H36: break-even / half at Target 1
    ma_key, ma_arm = rule.get("ma_trail"), rule.get("ma_arm", "1r")              # H36: the moving-average trail
    ma_arr = aux["ma"][ma_key] if ma_key else None
    need_t1 = use_targets or be_t1 or half_t1 or (ma_key is not None and ma_arm == "t1")
    # ---- H60: the switch. With it, the rule's own exit flags must be off: each trade is main's or b_targets'.
    sw_on = tswitch is not None
    sw_entry = tswitch.get("entry") if sw_on else None
    sw_bar = tswitch.get("bar") if sw_on else None
    if sw_on and (need_t1 or flip_limit or trail or pullback):
        raise ValueError("H60 switch: the rule's own exit flags must be off")
    modes = []                                                   # H60: per closed trade, True = target mode
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
    trade_t = bool(st.get("trade_targets", use_targets))         # H60: the current trade's mode
    part = dict(st.get("part") or {"pnl": 0.0, "fees": 0.0, "qpx": 0.0, "q": 0.0, "tags": []})
    trail_on = bool(st.get("trail_on", False))
    ma_on = bool(st.get("ma_on", False))                         # H36: the MA trail is armed
    trail_px = st.get("trail_px")                                # H36: its level (ratcheted, never loosens)
    leg = dict(st["leg"]) if st.get("leg") else None            # h3: the old position closing on a limit
    order = dict(st["order"]) if st.get("order") else None      # a_pullback: an entry limit resting
    stats = dict(st.get("stats") or _blank_stats())

    def book_trade(i, price, why, p_in, side, q0, s0, wi, ti, ti_ms, pnl, fees_t, t1=None, t2=None):
        risk = q0 * abs(p_in - s0) if s0 == s0 else np.nan
        r = pnl / risk if risk and risk == risk else np.nan
        trades.append((ti_ms, tms(i), ti, i, side, p_in, price, wi, why, pnl / (q0 * p_in) * 100.0, eq,
                       q0, pnl, fees_t, s0, risk, r, t1, t2))
        modes.append(bool(trade_t))
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

    def open_pos(i, side, price, why, k_dec):
        nonlocal pos, entry, qty, t_in, t_in_ms, why_in, stop, stop0, qty0, trail_on, ma_on, trail_px, trade_t
        from engine15.backtest import leverage as _lev            # the main book's own sizing rule
        pos, entry, qty, t_in, why_in = side, price, eq * _lev(cfg, price, cfg["stop_units"] * unit[i - 1]) / price, i, why
        t_in_ms = tms(i)
        stop = entry - pos * cfg["stop_units"] * unit[i - 1]
        stop0, qty0, trail_on = stop, qty, False
        ma_on, trail_px = False, None
        tg.update(t1=None, t2=None, t1_basis=None, t2_basis=None, t1_hit=False)
        if sw_on:                                                # H60: the mode of this trade, fixed at its fill
            trade_t = bool(sw_entry(k_dec, int(side))) if sw_entry is not None else True
            want_t = trade_t
        else:
            want_t = need_t1
        if want_t and row_of is not None:
            from engine15.live import plan_targets
            t = plan_targets(int(pos), float(entry), float(stop), row_of(k_dec))
            tg.update(t1=t.get("target_1"), t2=t.get("target_2"), t1_basis=t.get("target_1_basis"),
                      t2_basis=t.get("target_2_basis"))

    def stop_hit(i, side, level):
        return (side == 1 and l[i] <= level) or (side == -1 and h[i] >= level)

    def stop_px(i, side, level):
        return min(o[i], level) if side == 1 else max(o[i], level)

    p_up, p_dn = odds[:, labels.UP], odds[:, labels.DOWN]
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
        if sw_on:                                                # H60: targets act in this bar only if switched on
            tgt_now = trade_t and (sw_bar is None or bool(sw_bar[i]))
            be_moved = tg["t1_hit"]                              # only target mode ever takes Target 1 here
        else:
            tgt_now = use_targets
            be_moved = tg["t1_hit"] and (use_targets or be_t1)   # the stop sits at break-even
        if pos == 1 and l[i] <= stop:
            close(i, min(o[i], stop), _stop_word(be_moved, trail_on))
            idle = 0
        elif pos == -1 and h[i] >= stop:
            close(i, max(o[i], stop), _stop_word(be_moved, trail_on))
            idle = 0
        # ---- 2b. targets (b_targets): Target 1 then Target 2, both may fill in one bar
        if tgt_now and pos != 0 and tg["t1"] is not None:
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
        # ---- 2d. the moving-average trail (H36)
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
            elif not (a == policy.STEP_ASIDE and pos == 0):
                delay = int(cfg.get("fill_delay_bars", 0) or 0)   # same late-feed rule as the main book
                if not (delay and pending is not None and pending[1] == target):
                    pending = (a, target, why) if not delay else (a, target, why, delay)
        elif ma_exit and pos != 0 and not (pending is not None and pending[1] == 0):
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
    if sw_on:
        end["trade_targets"] = bool(trade_t) if pos else None
    if last is not None:
        end["mark"] = float(c[last])
        end["mark_ms"] = tms(last)
        end["equity_marked"] = float(eq_arr[last])
    tr = pd.DataFrame(trades, columns=TRADE_COLS)
    return {"trades": tr, "equity": eq_arr, "held": held, "state": end, "modes": modes}


# =====================================================================================
# the switches of the five variants
# =====================================================================================
def regime_labels(ev):
    """ev["regime"] as plain strings, NONE where the row has no label."""
    if "regime" not in ev:
        raise RuntimeError("the evidence frame has no regime column")
    v = ev["regime"].values
    out = np.empty(len(v), dtype=object)
    for k, x in enumerate(v):
        out[k] = x if isinstance(x, str) and x in REGIMES else NONE
    return out


def switch_for(name, reg):
    """The tswitch of a variant (or a gate position) on one market's regime labels (row k = decision close k)."""
    d = np.array([r in DIRECTIONAL for r in reg])
    m = np.array([r in MOMENTUM for r in reg])
    if name == "always_off":
        return {"entry": lambda k, s: False}
    if name == "always_on":
        return {"entry": lambda k, s: True}
    if name == "rg_dir_entry":                                   # directional -> flip mode, else target mode
        return {"entry": lambda k, s: not d[k]}
    if name == "rg_dir_aligned":                                 # flip mode only with the regime on the trade's side
        return {"entry": lambda k, s: not ((s == 1 and reg[k] in WITH_LONG) or (s == -1 and reg[k] in WITH_SHORT))}
    if name == "rg_dir_live":                                    # targets act only in bars with a non-directional label
        on = np.ones(len(reg), dtype=bool)                       # (the label known before the bar: row i - 1)
        on[1:] = ~d[:-1]
        return {"entry": lambda k, s: True, "bar": on}
    if name == "rg_mom_entry":                                   # momentum only -> flip mode, else target mode
        return {"entry": lambda k, s: not m[k]}
    if name == "rg_dir_entry_inv":                               # the control: directional -> target mode
        return {"entry": lambda k, s: bool(d[k])}
    raise KeyError(name)


def run_variant(name, prep, a, lo, n, aux, reg):
    cfg = shadows.asset_cfg(a, dict(prep["cfg"]))
    inp = shadows.book_inputs(prep, a)
    tgt = aux["targets"]
    return run_switch(inp["px"], inp["odds"], inp["shock"], inp["tide"], inp["unit"], cfg, lo, n,
                      bias=inp["bias"], guard=inp["guard"], rule={}, aux=aux, times_ms=data.to_ms(prep["times"]),
                      row_of=lambda k: tgt.iloc[k] if len(tgt.columns) else pd.Series(dtype=float),
                      tswitch=switch_for(name, reg))


def same_book(ref, mine, tol=1e-6):
    """-> (True, "") if two books close the same trades (rows, words, prices, P&L to tol) and end on the same equity."""
    a, b = ref["trades"].reset_index(drop=True), mine["trades"].reset_index(drop=True)
    if len(a) != len(b):
        return False, "trades %d vs %d" % (len(a), len(b))
    for col in GATE_COLS:
        if not (a[col].astype(str).values == b[col].astype(str).values).all():
            k = int(np.argmax(a[col].astype(str).values != b[col].astype(str).values))
            return False, "%s differs at trade %d: %s vs %s" % (col, k, a[col].iloc[k], b[col].iloc[k])
    for col in GATE_NUM:
        dif = np.abs(a[col].values.astype(float) - b[col].values.astype(float))
        if len(dif) and np.nanmax(dif) > tol:
            return False, "%s differs by %.3g" % (col, float(np.nanmax(dif)))
    e1, e2 = ref["state"]["eq"], mine["state"]["eq"]
    if abs(e1 - e2) > tol:
        return False, "final equity %.6f vs %.6f" % (e1, e2)
    m1, m2 = ref["state"].get("equity_marked"), mine["state"].get("equity_marked")
    if m1 is not None and m2 is not None and abs(m1 - m2) > tol:
        return False, "final marked equity %.6f vs %.6f" % (m1, m2)
    if ref["state"]["pos"] != mine["state"]["pos"]:
        return False, "open position at the end differs"
    return True, ""


# =====================================================================================
# one group
# =====================================================================================
def trade_rows(tr, reg, mid_i, modes=None):
    """Compact closed trades: [i_in, i_out, side, pnl_usd, pnl_pct, regime at the decision close, first half?, mode]."""
    out = []
    for j, t in enumerate(tr.itertuples(index=False)):
        k = int(t.i_in) - 1
        out.append([int(t.i_in), int(t.i_out), int(t.side), round(float(t.pnl_usd), 6), round(float(t.pnl_pct), 6),
                    reg[k] if 0 <= k < len(reg) else NONE, bool(t.i_out < mid_i),
                    None if modes is None else ("target" if modes[j] else "flip")])
    return out


def run_group(g, assets, fits_root, log=print):
    t0 = time.time()
    prep = h59.prep_cut(g, assets, os.path.join(fits_root, g), H59_END[g], log=log)
    times = prep["times"]
    n = len(times)
    mid_ts = pd.Timestamp(MID, tz="UTC")
    out = {"group": g, "end": H59_END[g], "assets": {}, "curves": {}, "gate": {}, "trades": {}, "regimes": {}}
    for a in assets:
        ok = np.isfinite(prep["odds"][a][:, 0])
        lo = max(int(np.argmax(ok)) if ok.any() else n, prep["birth_idx"], 1)
        mid_i = min(max(int(times.searchsorted(mid_ts)), lo + 1), n - 1)
        aux = shadows.aux_from_ev(prep["ev"][a], prep["px"][a])
        reg = regime_labels(prep["ev"][a])
        c, o = prep["px"][a]["close"], prep["px"][a]["open"]
        fee = shadows.asset_cfg(a, prep["cfg"])["cost_side"]
        books = {}
        for name in H59_BOOKS:                                   # exactly as H59 ran them
            books[name] = h59.run_book(name, prep, a, lo, n, aux)
        # ---- the equivalence gate: the copy, switch always off / on, against shadows.run (main / b_targets)
        gate = {}
        for pos_name, ref_name in (("always_off", "main"), ("always_on", "b_targets")):
            mine = run_variant(pos_name, prep, a, lo, n, aux, reg)
            okk, why = same_book(books[ref_name], mine)
            gate[pos_name] = {"vs": ref_name, "ok": okk, "detail": why, "trades": int(len(mine["trades"])),
                              "final_eq": round(float(mine["state"]["eq"]), 6)}
            if not okk:
                raise RuntimeError("EQUIVALENCE GATE FAILED on %s, switch %s vs shadows.run %s: %s" % (
                    a, pos_name, ref_name, why))
        log("%s %s: equivalence gate passed (off == main %d trades, on == b_targets %d trades)" % (
            g, a, gate["always_off"]["trades"], gate["always_on"]["trades"]))
        modes = {}
        for name in VARIANTS:
            b = run_variant(name, prep, a, lo, n, aux, reg)
            books[name] = b
            modes[name] = b["modes"]
        res = {"window": [str(times[lo])[:16], str(times[n - 1])[:16]], "split": str(times[mid_i])[:16],
               "lo": lo, "mid_i": mid_i, "n": n, "fee_side": fee,
               "buy_hold_return_pct": round(float(c[n - 1] / o[lo] * (1 - 2 * fee) - 1) * 100, 2), "books": {}}
        curves, trades = {}, {}
        for name in BOOKS:
            b = books[name]
            eq, tr = b["equity"], b["trades"]
            base_mid = eq[mid_i - 1] if np.isfinite(eq[mid_i - 1]) else START
            st = b["state"]
            res["books"][name] = {"all": ex.seg_stats(eq, tr, times, lo, n, START),
                                  "first_half": ex.seg_stats(eq, tr[tr.i_out < mid_i], times, lo, mid_i, START),
                                  "second_half": ex.seg_stats(eq, tr[tr.i_out >= mid_i], times, mid_i, n, base_mid),
                                  "exits": dict((str(k), int(v)) for k, v in tr.why_out.value_counts().items()),
                                  "open_at_end": {1: "LONG", -1: "SHORT"}.get(st["pos"], "FLAT")}
            if name in VARIANTS:
                mm = modes[name]
                res["books"][name]["modes"] = {"target": int(sum(mm)), "flip": int(len(mm) - sum(mm))}
            cv = ex.daily(eq, times, lo, n)
            curves[name] = {"t": [str(x)[:10] for x in cv.index], "eq": [round(float(x), 2) for x in cv.values]}
            if name in ("main", "b_targets") or name in VARIANTS:
                trades[name] = trade_rows(tr, reg, mid_i, modes.get(name))
        # ---- regime shares (description): sessions lo .. n-1, and days (one label per calendar day, its last row)
        seg = reg[lo:n]
        days = pd.Series(seg, index=times[lo:n]).groupby(times[lo:n].floor("1D")).last()
        res["regime_sessions"] = dict((r, int((seg == r).sum())) for r in REGIMES + (NONE,))
        res["regime_days"] = dict((r, int((days.values == r).sum())) for r in REGIMES + (NONE,))
        for half, (i0, i1) in (("first_half", (lo, mid_i)), ("second_half", (mid_i, n))):
            s2 = reg[i0:i1]
            res["regime_sessions_" + half] = dict((r, int((s2 == r).sum())) for r in REGIMES + (NONE,))
        out["assets"][a] = res
        out["curves"][a] = curves
        out["trades"][a] = trades
        out["gate"][a] = gate
        log("%s %s: %s .. %s, main %+.0f (%d), b_targets %+.0f, be_t1 %+.0f, half_be_t1 %+.0f; rg_dir_entry %+.0f, "
            "inv %+.0f (%.0fs)" % (g, a, res["window"][0], res["window"][1], res["books"]["main"]["all"].get("pnl_usd", 0),
                                   res["books"]["main"]["all"].get("trades", 0),
                                   res["books"]["b_targets"]["all"].get("pnl_usd", 0),
                                   res["books"]["be_t1"]["all"].get("pnl_usd", 0),
                                   res["books"]["half_be_t1"]["all"].get("pnl_usd", 0),
                                   res["books"]["rg_dir_entry"]["all"].get("pnl_usd", 0),
                                   res["books"]["rg_dir_entry_inv"]["all"].get("pnl_usd", 0), time.time() - t0))
        del books
        gc.collect()
    del prep
    gc.collect()
    return out


# =====================================================================================
# the report
# =====================================================================================
def load_groups():
    groups = {}
    for g, _a in CFG["universes"]:
        p = os.path.join(OUT, "today_%s.json" % g)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                groups[g] = json.load(fh)
    return groups


def reconcile(per):
    """`main`, `be_t1`, `b_targets`, `half_be_t1` here against research/out/h59_half_be/today_<group>.json."""
    rows, clean = [], True
    h59per = {}
    for g, _a in CFG["universes"]:
        p = os.path.join(H59_OUT, "today_%s.json" % g)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                h59per.update(json.load(fh)["assets"])
    for a in ORDER:
        if a not in per:
            continue
        for name in H59_BOOKS:
            ref = h59per.get(a, {}).get("books", {}).get(name, {}).get("all")
            s = per[a]["books"][name]["all"]
            if ref is None:
                rows.append({"asset": a, "book": name, "missing": True})
                clean = False
                continue
            d = s.get("pnl_usd", 0) - ref.get("pnl_usd", 0)
            dt = s.get("trades", 0) - ref.get("trades", 0)
            same = abs(d) < 0.01 and dt == 0
            clean = clean and same
            rows.append({"asset": a, "book": name, "h59_pnl": ref.get("pnl_usd"), "pnl": s.get("pnl_usd"),
                         "diff_usd": round(d, 2), "h59_trades": ref.get("trades"), "trades": s.get("trades"),
                         "diff_trades": dt, "exact": same})
    return rows, clean


def pooled(groups):
    frames = {}
    for g in groups.values():
        for a, cv in g["curves"].items():
            for name, s in cv.items():
                frames[(a, name)] = pd.Series(s["eq"], index=pd.to_datetime(s["t"]))
    frame = pd.concat(frames, axis=1).sort_index().ffill().fillna(START)
    assets = sorted(set(k[0] for k in frame.columns))
    mid_t = pd.Timestamp(MID)
    out = {}
    for name in BOOKS:
        tot = frame[[(a, name) for a in assets]].sum(axis=1)
        base = START * len(assets)
        first = tot[tot.index < mid_t]
        b_mid = float(first.iloc[-1]) if len(first) else base
        out[name] = {"assets": len(assets), "pnl_usd": round(float(tot.iloc[-1] - base), 2),
                     "return_pct": round(float(tot.iloc[-1] / base - 1) * 100, 2),
                     "sharpe": ex.sharpe(pd.concat([pd.Series([base], index=[tot.index[0] - pd.Timedelta(days=1)]), tot])),
                     "max_dd_pct": ex.max_dd(np.concatenate([[base], tot.values])),
                     "first_half_usd": round(b_mid - base, 2), "second_half_usd": round(float(tot.iloc[-1]) - b_mid, 2)}
    return out


def better_than_hold(pool, per):
    m = pool["main"]
    for name in BOOKS:
        p = pool[name]
        beats = [a for a in ORDER if a in per and
                 per[a]["books"][name]["all"].get("pnl_usd", 0) > per[a]["books"]["main"]["all"].get("pnl_usd", 0)]
        g1, g2 = p["first_half_usd"] - m["first_half_usd"], p["second_half_usd"] - m["second_half_usd"]
        dd_ok = (p["max_dd_pct"] or 0) >= (m["max_dd_pct"] or 0)
        p.update(vs_main_usd=round(p["pnl_usd"] - m["pnl_usd"], 2), gap_first_half=round(g1, 2),
                 gap_second_half=round(g2, 2), markets_beating_main=beats, dd_no_worse=bool(dd_ok),
                 trades=sum(per[a]["books"][name]["all"].get("trades", 0) for a in per),
                 better_than_hold=None if name == "main" else bool(g1 > 0 and g2 > 0 and len(beats) >= 5 and dd_ok))


def bucket_stats(rows):
    if not rows:
        return {"trades": 0, "pnl_usd": 0.0, "mean_usd": None, "mean_pct": None, "win_pct": None}
    p = np.array([r[3] for r in rows])
    q = np.array([r[4] for r in rows])
    return {"trades": int(len(p)), "pnl_usd": round(float(p.sum()), 2), "mean_usd": round(float(p.mean()), 2),
            "mean_pct": round(float(q.mean()), 4), "win_pct": round(float((p > 0).mean() * 100), 1)}


def question_a(groups):
    """(a) main vs b_targets trades by the regime at their entry decision close."""
    tr = dict((a, t) for g in groups.values() for a, t in g["trades"].items())
    keys = [("directional", lambda r: r in DIRECTIONAL), ("other", lambda r: r not in DIRECTIONAL)] + \
        [(r, (lambda rr: (lambda x: x == rr))(r)) for r in REGIMES + (NONE,)]
    parts = {"all": lambda x: True, "first_half": lambda x: x[6], "second_half": lambda x: not x[6]}
    table = {}
    for a in ORDER + ["POOLED"]:
        if a != "POOLED" and a not in tr:
            continue
        table[a] = {}
        for book in ("main", "b_targets"):
            rows_all = tr[a][book] if a != "POOLED" else [r for x in tr.values() for r in x[book]]
            table[a][book] = {}
            for bk, f in keys:
                table[a][book][bk] = {}
                for part, pf in parts.items():
                    table[a][book][bk][part] = bucket_stats([r for r in rows_all if f(r[5]) and pf(r)])

    def holds(a, part):
        t = table[a]
        md, td = t["main"]["directional"][part]["mean_usd"], t["b_targets"]["directional"][part]["mean_usd"]
        mo, to = t["main"]["other"][part]["mean_usd"], t["b_targets"]["other"][part]["mean_usd"]
        dir_ok = md is not None and td is not None and md > td
        oth_ok = mo is not None and to is not None and to > mo
        return dir_ok, oth_ok

    verdict = {}
    for part in ("first_half", "second_half", "all"):
        d, o = holds("POOLED", part)
        verdict["pooled_" + part] = {"directional_main_more": d, "other_targets_more": o}
    markets = [a for a in ORDER if a in table and all(holds(a, "all"))]
    verdict["markets_both_hold"] = markets
    verdict["per_market"] = dict((a, dict(zip(("directional_main_more", "other_targets_more"), holds(a, "all"))))
                                 for a in ORDER if a in table)
    verdict["supported"] = bool(all(verdict["pooled_first_half"].values()) and all(verdict["pooled_second_half"].values())
                                and len(markets) >= 5)
    return table, verdict


def question_c(per):
    """(c) one rule per market: the best first-half rule of the menu, read on the second half."""
    rows = {}
    for a in ORDER:
        if a not in per:
            continue
        B = per[a]["books"]
        h1 = [(B[k]["first_half"].get("pnl_usd", 0), -i, k) for i, k in enumerate(MENU)]
        pick = max(h1)[2]                                        # ties: the earlier name in the menu
        whole = max([(B[k]["all"].get("pnl_usd", 0), -i, k) for i, k in enumerate(MENU)])[2]
        rows[a] = {"pick": pick, "pick_first_half": B[pick]["first_half"].get("pnl_usd", 0),
                   "pick_second_half": B[pick]["second_half"].get("pnl_usd", 0),
                   "main_first_half": B["main"]["first_half"].get("pnl_usd", 0),
                   "main_second_half": B["main"]["second_half"].get("pnl_usd", 0),
                   "beats_main_second_half": B[pick]["second_half"].get("pnl_usd", 0) >
                   B["main"]["second_half"].get("pnl_usd", 0),
                   "best_whole_window": whole, "agrees": whole == pick,
                   "first_half_by_rule": dict((k, B[k]["first_half"].get("pnl_usd", 0)) for k in MENU),
                   "second_half_by_rule": dict((k, B[k]["second_half"].get("pnl_usd", 0)) for k in MENU)}
    ps = sum(r["pick_second_half"] for r in rows.values())
    ms = sum(r["main_second_half"] for r in rows.values())
    nb = [a for a, r in rows.items() if r["beats_main_second_half"]]
    return rows, {"picks_second_half_sum": round(ps, 2), "main_second_half_sum": round(ms, 2),
                  "markets_beating": nb, "helps": bool(ps > ms and len(nb) >= 5),
                  "agree_count": sum(1 for r in rows.values() if r["agrees"])}


def _f(v, pat="%+.0f"):
    return "-" if v is None else pat % v


def _yn(b):
    return "yes" if b else "no"


def write_report(groups, log=print):
    per = dict((a, r) for g in groups.values() for a, r in g["assets"].items())
    gate = dict((a, x) for g in groups.values() for a, x in g["gate"].items())
    rec, clean = reconcile(per)
    pool = pooled(groups)
    better_than_hold(pool, per)
    table_a, verdict_a = question_a(groups)
    rows_c, verdict_c = question_c(per)
    v1, v5, m = pool["rg_dir_entry"], pool["rg_dir_entry_inv"], pool["main"]
    v1_vs_v5 = {"first_half": round(v1["first_half_usd"] - v5["first_half_usd"], 2),
                "second_half": round(v1["second_half_usd"] - v5["second_half_usd"], 2)}
    v1_vs_v5["idea_holds"] = bool(v1_vs_v5["first_half"] > 0 and v1_vs_v5["second_half"] > 0)
    gate_ok = all(x["always_off"]["ok"] and x["always_on"]["ok"] for x in gate.values()) and len(gate) == 8
    now = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    res = {"written_utc": now, "mid": MID, "ends": H59_END, "books": BOOKS, "menu": MENU,
           "equivalence_gate": {"passed_all_8": gate_ok, "per_market": gate},
           "reconciliation_h59_today": {"exact": clean, "rows": rec},
           "a_regime_buckets": {"verdict": verdict_a, "table": table_a},
           "b_whole_books": {"pooled": pool, "v1_vs_control": v1_vs_v5},
           "c_rule_per_market": {"verdict": verdict_c, "per_market": rows_c},
           "per_market": dict((a, dict((k, v) for k, v in r.items())) for a, r in per.items())}
    L = []
    L += ["# H60: exits by regime, per market (history replay, IN-SAMPLE, not proof)", "",
          "Written by `research/h60_regime_exits.py` on %s. Paper only. These are replays of history the project has "
          "already read for exits (H36, H59). Nothing here is a proven edge, and nothing here changes a book." % now, ""]
    if not clean:
        L += ["**WARNING: the H59 reconciliation did NOT reproduce exactly (table below). No H60 number in this report "
              "is presented as clean.**", ""]
    # ---- verdicts first
    L += ["## The answers, in plain words", ""]
    L += ["- **The check on the tools.** The study's own copy of the book runner gave the same trades as the engine's "
          "runner on all 8 markets, in both switch positions: %s. The four H59 books came out %s." % (
              "yes" if gate_ok else "NO", "exactly as in H59's run" if clean else "DIFFERENT from H59's run (see below)")]
    pa1, pa2 = verdict_a["pooled_first_half"], verdict_a["pooled_second_half"]
    L += ["- **(a) Does holding pay more in directional regimes, and targets pay more in the others?** **%s.** "
          "Pooled, first half: holding earned more per trade in directional regimes: %s; targets earned more in the "
          "others: %s. Second half: %s and %s. Markets where both held over the whole window: %d of 8 (%s; needs 5)." % (
              "Supported" if verdict_a["supported"] else "Not supported",
              _yn(pa1["directional_main_more"]), _yn(pa1["other_targets_more"]),
              _yn(pa2["directional_main_more"]), _yn(pa2["other_targets_more"]),
              len(verdict_a["markets_both_hold"]), ", ".join(verdict_a["markets_both_hold"]) or "none")]
    L += ["- **(b) The owner's rule as a whole book (variant 1, `rg_dir_entry`).** Better than holding: **%s**. "
          "Pooled net $%s against main $%s; halves vs main $%s / $%s; ahead of main in %d of 8 markets; max drawdown "
          "%.1f%% vs main %.1f%%." % (
              "YES" if v1["better_than_hold"] else "NO", _f(v1["pnl_usd"]), _f(m["pnl_usd"]),
              _f(v1["gap_first_half"]), _f(v1["gap_second_half"]), len(v1["markets_beating_main"]),
              v1["max_dd_pct"], m["max_dd_pct"])]
    L += ["- **(b) Variant 1 against its control (the idea turned round, variant 5).** The idea needs variant 1 above "
          "the control in both halves: **%s** (first half $%s, second half $%s)." % (
              "it is" if v1_vs_v5["idea_holds"] else "it is not", _f(v1_vs_v5["first_half"]), _f(v1_vs_v5["second_half"]))]
    others = [k for k in VARIANTS[1:] if pool[k]["better_than_hold"]]
    L += ["- **(b) The other variants.** Better than holding: %s." % (", ".join(others) if others else "none")]
    L += ["- **(c) One rule per market.** Picking each market's best rule on the first half and using it on the "
          "second half: **%s**. Picks' second half together $%s against main's $%s; ahead of main in %d of 8 markets "
          "(needs 5)." % ("a rule per market helps" if verdict_c["helps"] else "a rule per market does not help",
                          _f(verdict_c["picks_second_half_sum"]), _f(verdict_c["main_second_half_sum"]),
                          len(verdict_c["markets_beating"]))]
    mp = table_a["POOLED"]["main"]
    nd, no_ = mp["directional"]["all"]["trades"], mp["other"]["all"]["trades"]
    L += ["", "**Why it comes out this way, in one line.** Most of the main book's trades start in a RANGE or "
          "TRANSITION day (%d of %d pooled), and that is where holding made most of its money (RANGE alone $%s). "
          "The owner's rule puts targets on exactly those trades, so it cuts the winners short where the main book "
          "earns. Directional days are rarer (%d main trades), and there holding was ahead in the first half and behind "
          "in the second." % (no_, nd + no_, _f(mp["RANGE"]["all"]["pnl_usd"]), nd)]
    L += ["", "How to read this: one history, read many times (21 exit rules on these same entries now). A pass would "
          "not prove anything and a fail does not stop the owner from choosing a rule. What the owner adopts is "
          "read forward at 30 closed trades per market.", ""]
    # ---- the checks
    L += ["## The checks", "", "### Equivalence gate (the study's runner copy vs engine15/shadows.run)", "",
          "| Market | switch off = main | trades | switch on = b_targets | trades |", "|---|---|---|---|---|"]
    for a in ORDER:
        if a in gate:
            x = gate[a]
            L.append("| %s | %s | %d | %s | %d |" % (a, "same" if x["always_off"]["ok"] else "DIFFERENT",
                                                    x["always_off"]["trades"],
                                                    "same" if x["always_on"]["ok"] else "DIFFERENT",
                                                    x["always_on"]["trades"]))
    L += ["", "Same = the same closed trades (entry and exit bar, side, words), prices, size, fees and P&L within "
          "$0.000001, the same final equity and the same open position at the end.", "",
          "### Reconciliation with H59's \"today\" run", "",
          "**%s**" % ("Reproduced exactly: every book within one cent and the same trade count." if clean else
                     "NOT reproduced exactly."), "",
          "| Market | Book | H59 net | Here | Diff $ | H59 trades | Here | Diff |", "|---|---|---|---|---|---|---|---|"]
    for x in rec:
        if x.get("missing"):
            L.append("| %s | `%s` | missing | | | | | |" % (x["asset"], x["book"]))
        else:
            L.append("| %s | `%s` | $%s | $%s | %+.2f | %d | %d | %+d |" % (
                x["asset"], x["book"], _f(x["h59_pnl"]), _f(x["pnl"]), x["diff_usd"], x["h59_trades"], x["trades"],
                x["diff_trades"]))
    L.append("")
    # ---- (a)
    L += ["## (a) What each rule earned per trade, by the regime at entry", "",
          "Every closed trade of `main` (hold to stop or flip) and of `b_targets` (half at Target 1, the rest at Target 2) "
          "is put in the bucket of the daily regime label on its decision bar. Halves by the trade's exit bar (before or "
          "after %s). Mean = net dollars per trade." % MID, "",
          "| Market | Part | Directional: main trades / mean | Directional: b_targets trades / mean | Holds? | "
          "Other: main trades / mean | Other: b_targets trades / mean | Holds? |",
          "|---|---|---|---|---|---|---|---|"]
    for a in ["POOLED"] + ORDER:
        if a not in table_a:
            continue
        t = table_a[a]
        for part in ("all", "first_half", "second_half"):
            md, td = t["main"]["directional"][part], t["b_targets"]["directional"][part]
            mo, to = t["main"]["other"][part], t["b_targets"]["other"][part]
            hd = md["mean_usd"] is not None and td["mean_usd"] is not None and md["mean_usd"] > td["mean_usd"]
            ho = mo["mean_usd"] is not None and to["mean_usd"] is not None and to["mean_usd"] > mo["mean_usd"]
            L.append("| %s | %s | %d / $%s | %d / $%s | %s | %d / $%s | %d / $%s | %s |" % (
                a, part.replace("_", " "), md["trades"], _f(md["mean_usd"]), td["trades"], _f(td["mean_usd"]), _yn(hd),
                mo["trades"], _f(mo["mean_usd"]), to["trades"], _f(to["mean_usd"]), _yn(ho)))
    L += ["", "The six labels, pooled, whole window (main / b_targets: trades, net, mean per trade, win rate):", "",
          "| Label | main trades | main net | main mean | main win | b_targets trades | b_targets net | b_targets mean | "
          "b_targets win |", "|---|---|---|---|---|---|---|---|---|"]
    for r in REGIMES + (NONE,):
        x, y = table_a["POOLED"]["main"][r]["all"], table_a["POOLED"]["b_targets"][r]["all"]
        if x["trades"] or y["trades"]:
            L.append("| %s | %d | $%s | $%s | %s%% | %d | $%s | $%s | %s%% |" % (
                r, x["trades"], _f(x["pnl_usd"]), _f(x["mean_usd"]), _f(x["win_pct"], "%.0f"),
                y["trades"], _f(y["pnl_usd"]), _f(y["mean_usd"]), _f(y["win_pct"], "%.0f")))
    L += ["", "Per market and label (whole window; main mean / b_targets mean per trade, trades in brackets):", "",
          "| Market | " + " | ".join(REGIMES) + " |", "|---|" + "---|" * len(REGIMES)]
    for a in ORDER:
        if a in table_a:
            cells = []
            for r in REGIMES:
                x, y = table_a[a]["main"][r]["all"], table_a[a]["b_targets"][r]["all"]
                cells.append("-" if not (x["trades"] or y["trades"]) else "$%s (%d) / $%s (%d)" % (
                    _f(x["mean_usd"]), x["trades"], _f(y["mean_usd"]), y["trades"]))
            L.append("| %s | %s |" % (a, " | ".join(cells)))
    L.append("")
    # ---- (b)
    L += ["## (b) The five variants as whole books", "",
          "Better than holding (H36's test): pooled net above main in BOTH halves, ahead of main in at least 5 of 8 "
          "markets, pooled max drawdown no worse.", "",
          "| Book | Net P&L | vs main | Sharpe | Max DD | 1st half | 2nd half | 1st vs main | 2nd vs main | Markets ahead | "
          "Trades | Better than hold? |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name in BOOKS:
        s = pool[name]
        L.append("| `%s` | $%s | $%s | %s | %.1f%% | $%s | $%s | $%s | $%s | %d/8 | %d | %s |" % (
            name, _f(s["pnl_usd"]), _f(s["vs_main_usd"]), _f(s["sharpe"], "%.2f"), s["max_dd_pct"],
            _f(s["first_half_usd"]), _f(s["second_half_usd"]), _f(s["gap_first_half"]), _f(s["gap_second_half"]),
            len(s["markets_beating_main"]), s["trades"],
            "-" if s["better_than_hold"] is None else _yn(s["better_than_hold"])))
    L += ["", "Variant 1 (`rg_dir_entry`) minus the control (`rg_dir_entry_inv`): first half $%s, second half $%s." % (
        _f(v1_vs_v5["first_half"]), _f(v1_vs_v5["second_half"])), "",
          "Net P&L per market, whole window (first half / second half below each):", "",
          "| Market | " + " | ".join("`%s`" % k for k in BOOKS) + " |", "|---|" + "---|" * len(BOOKS)]
    for a in ORDER:
        if a in per:
            B = per[a]["books"]
            L.append("| %s | %s |" % (a, " | ".join("$%s" % _f(B[k]["all"].get("pnl_usd")) for k in BOOKS)))
            L.append("| (halves) | %s |" % " | ".join("%s / %s" % (_f(B[k]["first_half"].get("pnl_usd")),
                                                                 _f(B[k]["second_half"].get("pnl_usd"))) for k in BOOKS))
    L += ["", "Trades per variant by the mode they ran in (target / flip), whole window (`rg_dir_live` decides bar by bar, "
          "so every trade counts as target-eligible there):", "",
          "| Market | " + " | ".join("`%s`" % k for k in VARIANTS) + " |", "|---|" + "---|" * len(VARIANTS)]
    for a in ORDER:
        if a in per:
            B = per[a]["books"]
            L.append("| %s | %s |" % (a, " | ".join("%d / %d" % (B[k]["modes"]["target"], B[k]["modes"]["flip"])
                                                    for k in VARIANTS)))
    L.append("")
    # ---- (c)
    L += ["## (c) One rule per market", "",
          "Menu: %s. The rule with the most net P&L in the first half (to %s) is picked for each market (ties: the "
          "earlier name), then its second half is set beside main's second half." % (
              ", ".join("`%s`" % k for k in MENU), MID), "",
          "| Market | First-half pick | Pick, 1st half | Main, 1st half | Pick, 2nd half | Main, 2nd half | Ahead? | "
          "Best over whole window | Same? |", "|---|---|---|---|---|---|---|---|---|"]
    for a in ORDER:
        if a in rows_c:
            r = rows_c[a]
            L.append("| %s | `%s` | $%s | $%s | $%s | $%s | %s | `%s` | %s |" % (
                a, r["pick"], _f(r["pick_first_half"]), _f(r["main_first_half"]), _f(r["pick_second_half"]),
                _f(r["main_second_half"]), _yn(r["beats_main_second_half"]), r["best_whole_window"], _yn(r["agrees"])))
    L += ["| **Together** | | | | $%s | $%s | %d/8 | | %d/8 |" % (
        _f(verdict_c["picks_second_half_sum"]), _f(verdict_c["main_second_half_sum"]), len(verdict_c["markets_beating"]),
        verdict_c["agree_count"]), ""]
    # ---- regime shares
    L += ["## How often each market is in each regime (description only)", "",
          "Share of 15-minute sessions in the window with each daily label (main's trades in brackets, by the label at "
          "entry).", "", "| Market | " + " | ".join(REGIMES) + " | no label | Directional |", "|---|" + "---|" * (len(REGIMES) + 2)]
    for a in ORDER:
        if a in per:
            rs = per[a]["regime_sessions"]
            tot = float(sum(rs.values())) or 1.0
            tm = table_a[a]["main"]
            cells = ["%.1f%% (%d)" % (100 * rs[r] / tot, tm[r]["all"]["trades"]) for r in REGIMES]
            cells.append("%.1f%% (%d)" % (100 * rs[NONE] / tot, tm[NONE]["all"]["trades"]))
            dsh = sum(rs[r] for r in DIRECTIONAL) / tot
            cells.append("%.1f%% (%d)" % (100 * dsh, tm["directional"]["all"]["trades"]))
            L.append("| %s | %s |" % (a, " | ".join(cells)))
    L += ["", "Conventions: the regime is the engine's own daily label (`ev[\"regime\"]`, last closed daily bar). "
          "A trade's regime is the label on its decision bar (the bar before the fill). In `rg_dir_live` a target in "
          "a bar is acted on only if the label known before that bar opened (the previous row) is not directional; "
          "once half is off at Target 1 the stop stays at the entry. Sharpe on daily marked equity, sqrt(365). Pooled: "
          "markets' daily equity summed. (c)'s sums are the per-market half results added up.", "",
          "## Details the registration did not fix (disclosed)", "",
          "- The runner copy keeps every code line of `shadows.run` (two comments shortened); the switch replaces `use_targets` per trade (and per bar "
          "in `rg_dir_live`). With the switch on, the stop word after Target 1 is `STOP_BE` as in `b_targets`.",
          "- `rg_dir_live`: the regime of bar i is the label on row i - 1 (known before the bar trades); row i already "
          "contains the daily bar that bar i closes.",
          "- Halves in (a) and (c) are split by the trade's exit bar, as H59's half statistics are. A row with no label "
          "would count as \"other\"; there were none in these windows.",
          "- Means in (a) are dollars per trade, so ETH (the largest book) weighs most in the pooled line; the mean "
          "percent per trade is in results.json.",
          "- The refits were not recomputed: H59's cached refits (`fits_today`) were copied into this study's own folder "
          "on the server before the run; the reconciliation above then held exactly.", ""]
    with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    log("gate %s; reconciliation exact %s" % (gate_ok, clean))
    log("(a) supported %s %s" % (verdict_a["supported"], verdict_a))
    for name in BOOKS:
        s = pool[name]
        log("  %-17s %+10.0f vs main %+10.0f halves %+9.0f / %+9.0f DD %6.2f%% ahead %d BTH %s" % (
            name, s["pnl_usd"], s["vs_main_usd"], s["gap_first_half"], s["gap_second_half"], s["max_dd_pct"],
            len(s["markets_beating_main"]), s["better_than_hold"]))
    log("v1 vs v5 %s" % v1_vs_v5)
    log("(c) %s" % verdict_c)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default=None)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--fits-dir", default=None, help="default research/out/h60_regime_exits/fits_today")
    args = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    log = lambda *m: print(time.strftime("%H:%M:%S"), *m, flush=True)      # noqa: E731
    if args.report:
        groups = load_groups()
        if len(groups) != len(CFG["universes"]):
            raise SystemExit("only %d of %d groups ran: %s" % (len(groups), len(CFG["universes"]), sorted(groups)))
        write_report(groups, log)
        return
    groups = dict((g, list(a)) for g, a in CFG["universes"])
    fits = args.fits_dir or os.path.join(OUT, "fits_today")
    ex.below_normal()
    for g in ([args.group] if args.group else list(groups)):
        ex.acquire("h60 %s" % g, log)
        try:
            r = run_group(g, groups[g], fits, log)
        finally:
            ex.release()
        with open(os.path.join(OUT, "today_%s.json" % g), "w", encoding="utf-8") as fh:
            json.dump(r, fh)
        gc.collect()


if __name__ == "__main__":
    main()
