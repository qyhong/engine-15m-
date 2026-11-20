# -*- coding: utf-8 -*-
"""backtest -- walk the whole thought process through history, honestly.

THE HONEST FRAME (the estate's)
  * closed bars only; a decision at the close of bar i is filled at the OPEN of bar i+1
  * 0.10% a side on every fill; a flip is two fills
  * a protective stop fills inside the bar at its level, or at the open when the bar opens
    beyond it; the stop is checked before anything else in the bar
  * 1x notional, no leverage; equity compounds; drawdown is marked to market every session
  * the model at session s has only seen calls graded by s (model.walk_forward / trust_path)

    py -3 -m engine15 backtest            (replays all history; writes out/replay/)
"""
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

from . import data, evidence, exits, labels, model, policy
from .config import CFG, OUT_DIR

START_EQUITY = 10000.0
STOP_WORDS = ("STOP", "STOP_BE")     # a stop-out; "STOP_BE" = at the entry price after Target 1 (v5.2.5, run_book)
ACTIONS = [policy.WAIT, policy.IDLE, policy.HOLD, policy.ENTER, policy.FORCED, policy.FLIP, policy.STEP_ASIDE]
ACT_CODE = dict((a, i) for i, a in enumerate(ACTIONS))


def prepare(end=None, cfg=CFG, bars=None, funding=None, live=None, log=None):
    """Bars -> evidence -> grades -> the voices' walk-forward odds -> trust -> the engine's odds."""
    t0 = time.time()
    say = log or (lambda *_: None)
    if bars is None:
        from . import livefeeds
        bars = dict((a, data.load(a)) for a in cfg["assets"])
        funding = dict((a, data.load_funding(a)) for a in cfg["assets"])
        live = dict((a, livefeeds.load_live(a)) for a in cfg["assets"])
    if end is not None:
        cut = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
        bars = dict((a, df[df.index < cut]) for a, df in bars.items())
    ev = evidence.build(bars, funding, live)
    assets = list(ev)
    times = ev[assets[0]].index
    say("evidence built: %d sessions x %d assets (%.0fs)" % (len(times), len(assets), time.time() - t0))
    X, ready, y, res, px = {}, {}, {}, {}, {}
    for a in assets:
        X[a], ready[a] = evidence.matrix(ev[a])
        b = bars[a].loc[times]
        px[a] = dict((k, b[k].values) for k in ("open", "high", "low", "close"))
        unit = (cfg["barrier_atr"] * ev[a]["atr1h"]).values
        y[a], res[a] = labels.triple_barrier(px[a]["open"], px[a]["high"], px[a]["low"], unit, cfg["horizon"])
    birth_idx = int(times.searchsorted(pd.Timestamp(cfg["birth"], tz="UTC")))
    floor_idx = int(times.searchsorted(pd.Timestamp(cfg.get("train_floor", cfg["birth"]), tz="UTC")))
    probs, models = model.walk_forward(X, ready, y, cfg, birth_idx, floor_idx=min(floor_idx, birth_idx))
    say("voices walked forward: %d refits (%.0fs)" % (len(models), time.time() - t0))
    trust = model.trust_path(probs, y, res, cfg)
    if cfg.get("voting"):                                          # only the voting cards share the trust
        votes = np.array([1.0 if v in cfg["voting"] else 0.0 for v in model.VOICE_NAMES])
        trust = trust * votes
        trust = trust / trust.sum(axis=1, keepdims=True)
    trust = model.cap_shares(trust, cfg.get("trust_cap"))             # v5.2: no card above the cap
    odds = {}
    for a in assets:                                               # a voice with no reading this session has no vote
        speaks = np.stack([(np.abs(X[a][:, model._COLS[v]]).sum(axis=1) > 0) if model._COLS[v] else np.zeros(len(times), bool)
                           for v in model.VOICE_NAMES], axis=1)
        w = trust * speaks
        tot = w.sum(axis=1, keepdims=True)
        w = np.where(tot > 0, w / np.where(tot > 0, tot, 1.0), trust)
        w = model.cap_shares(w, cfg.get("trust_cap"))
        odds[a] = model.mix(probs[a], w)
    say("trust and odds done (%.0fs)" % (time.time() - t0))
    return {"cfg": dict(cfg), "assets": assets, "times": times, "ev": ev, "px": px, "X": X, "ready": ready,
            "y": y, "res": res, "probs": probs, "models": models, "trust": trust, "odds": odds,
            "birth_idx": birth_idx}


def leverage(cfg, price, stop_dist):
    """How many times equity a new position carries (owner, 11 Nov 2026: USDJPY up to 100x, the
    S&P 500, gold and silver up to 5x, "you choose how much"; crypto stays 1x, full size).
    Rule: size so a stop-out loses about `risk_per_trade` of equity (2%, near what a full-size
    crypto trade risks at its usual 2-3% stop), never below 1x and never above the asset's cap:
        leverage = clip(risk_per_trade / (stop distance / price), 1, max_leverage)."""
    cap = float(cfg.get("leverage_cap", 1.0) or 1.0)             # this asset's cap (live.asset_cfg sets it)
    if cap <= 1.0 or not stop_dist or stop_dist != stop_dist or price <= 0:
        return 1.0
    return float(min(cap, max(1.0, cfg.get("risk_per_trade", 0.02) / (stop_dist / price))))


def run_book(px, odds, shock, tide, unit, cfg, lo, hi, cost_mult=1.0, state=None, bias=None, guard=None, t1_of=None,
             t2_of=None):
    """One asset's paper book over sessions lo .. hi-1. -> dict of per-session arrays and trades.
    `state` (the dict a previous call returned under "state") resumes a book exactly where it
    stopped: the live engine advances one session at a time this way.
    Break-even after Target 1 (v5.2.5; only where cfg["be_t1"] is exactly True AND t1_of is given, else nothing changes):
    t1_of(i, side, entry, stop) -> Target 1 of a trade filled at bar i's open (None: that trade has no target and
    keeps its entry stop). Once a bar trades through Target 1 (read after that bar's stop check) the stop moves to
    the entry price, live from the next bar and never looser (exits.be_stop, the b_be_t1 shadow's rule); a stop-out
    there is booked as "STOP_BE".
    Half at Target 1 (v5.2.6; only with the rule above AND cfg["half_t1"] exactly True): in the bar that trades
    through Target 1, half the position (exits.PART) is closed AT Target 1 (a limit, as the shadow books fill it)
    and the stop of the rest goes to the entry; the rest leaves at that stop or on a flip. The half is a closed
    trade the moment it closes (owner, 20 Nov 2026: "It should reflect on the close trade also"): its own row,
    why_out "T1", its own quantity, result and fees; the rest gets a second row when it closes (why_out as for any
    exit: "STOP_BE", "FLIP" ...). Both rows carry the same entry (i_in, p_in), which is how they are told to be one
    trade (reports.per_entry counts them once).
    state["half_due"] (set by live.adopt_be_t1 for a trade whose Target 1 traded before the rule existed): the half
    is closed at the next bar's OPEN instead, why_out "T1_LATE"; nothing is back-dated to the target's price.
    The rest at Target 2 (v5.2.7; only with both rules above AND cfg["t2_exit"] exactly True AND t2_of given, the
    planner of Target 2 with t1_of's arguments): once Target 1 has traded, a bar that trades through Target 2 closes
    what is left AT Target 2, why_out "T2" (read after the stop check and after Target 1, so both targets may fill
    in one bar, as in the Setups book, shadows.run). The book is then flat and the mandate counts from zero.
    -> also "parts": [(bar, price, quantity, net usd, tag)] for the halves closed in lo .. hi-1."""
    o, h, l, c = px["open"], px["high"], px["low"], px["close"]
    n = len(c)
    act = np.zeros(n, dtype=np.int8)
    held = np.zeros(n, dtype=np.int8)           # the position carried through session i
    idle_arr = np.zeros(n, dtype=np.int8)
    stop_arr = np.full(n, np.nan)
    eq_arr = np.full(n, np.nan)
    reason = np.empty(n, dtype=object)
    trades = []
    fee = cfg["cost_side"] * cost_mult
    pos, idle, qty, entry, stop, eq = 0, 0, 0.0, 0.0, np.nan, START_EQUITY
    t_in, why_in, pending = -1, "", None
    # v5.2.5: the stop to entry after Target 1. Only on exactly True, which live.asset_cfg sets for the markets in
    # CFG["be_t1"]: the raw CFG holds the LIST of those markets there, and a list must never switch the rule on.
    be = cfg.get("be_t1") is True and t1_of is not None
    half = be and cfg.get("half_t1") is True                      # v5.2.6: half off at Target 1 (needs the rule above)
    t2x = half and cfg.get("t2_exit") is True and t2_of is not None   # v5.2.7: the rest out at Target 2 (needs both)
    t1, t1_hit, stop0, t2 = None, False, np.nan, None
    part, half_due, parts = None, False, []                       # the half already closed; one owed at the next open
    fees_paid = [float((state or {}).get("fees", 0.0))]           # every fee this book has paid, across steps
    if state:
        pos, idle, qty, entry, eq = state["pos"], state["idle"], state["qty"], state["entry"], state["eq"]
        stop = np.nan if state["stop"] is None else state["stop"]
        why_in, pending = state["why_in"], tuple(state["pending"]) if state["pending"] else None
        if be and pos != 0:
            t1, t1_hit = state.get("t1"), bool(state.get("t1_hit", False))
            t2 = state.get("t2") if t2x else None
            stop0 = stop if state.get("stop0") is None else state["stop0"]
            if half:
                part = dict(state["part"]) if state.get("part") else None
                half_due = bool(state.get("half_due", False)) and part is None

    def close(i, price, why):
        nonlocal pos, qty, eq, stop, t1, t1_hit, stop0, part, half_due, t2
        gross = qty * pos * (price - entry)
        fees = fee * qty * (entry + price)
        eq += gross - fees
        fees_paid[0] += fees
        trades.append((t_in, i, pos, entry, price, why_in, why, (gross - fees) / (qty * entry) * 100.0, eq,
                       qty, gross - fees, fees))                  # after a half at Target 1: the row of the rest
        pos, qty, stop = 0, 0.0, np.nan
        t1, t1_hit, stop0, t2 = None, False, np.nan, None
        part, half_due = None, False

    def take_half(i, price, tag):
        """Close exits.PART of the position at `price` (the same arithmetic as close, for that share) and book it
        as a closed trade of its own at once."""
        nonlocal qty, eq, part
        q = qty * exits.PART
        gross = q * pos * (price - entry)
        fees = fee * q * (entry + price)
        eq += gross - fees
        fees_paid[0] += fees
        part = {"pnl": float(gross - fees), "fees": float(fees), "qpx": float(q * price), "q": float(q), "tag": tag}
        parts.append((i, float(price), float(q), float(gross - fees), tag))
        trades.append((t_in, i, pos, entry, price, why_in, tag, (gross - fees) / (q * entry) * 100.0, eq,
                       q, gross - fees, fees))
        qty -= q

    p_up, p_dn = odds[:, labels.UP], odds[:, labels.DOWN]
    for i in range(lo, hi):
        if pending is not None and len(pending) > 3 and pending[3] > 0:   # a late feed: the order waits a bar
            pending = tuple(pending[:3]) + (pending[3] - 1,)
        elif pending is not None:                                 # 1. fills at this open
            a, target, why = pending[:3]
            if pos != 0 and target != pos:
                close(i, o[i], a)
            if target != 0 and pos == 0:
                lev = leverage(cfg, o[i], cfg["stop_units"] * unit[i - 1])
                q = eq * lev / o[i]
                rb = cfg.get("risk_budget_usd")                   # total-risk cap across all books (live only)
                r = q * cfg["stop_units"] * unit[i - 1]
                if rb is not None and r == r and r > rb:
                    q = q * max(rb, 0.0) / r                      # shrink to what the cap leaves (nothing: no entry)
                if q > 0:
                    pos, entry, qty, t_in, why_in = target, o[i], q, i, a
                    stop = entry - pos * cfg["stop_units"] * unit[i - 1]
                    t1, t1_hit, stop0, t2 = None, False, stop, None
                    if be:
                        t1 = t1_of(i, pos, entry, stop)
                    if t2x:
                        t2 = t2_of(i, pos, entry, stop)
            pending = None
        if half_due:                                              # 1b. a half owed from before the rule: at this open
            if pos != 0 and part is None:
                take_half(i, o[i], "T1_LATE")
            half_due = False
        held[i] = pos
        stop_why = "STOP_BE" if (be and t1_hit) else "STOP"       # after Target 1 the stop sits at the entry
        if pos == 1 and l[i] <= stop:                             # 2. the protective stop
            close(i, min(o[i], stop), stop_why)
            idle = 0
        elif pos == -1 and h[i] >= stop:
            close(i, max(o[i], stop), stop_why)
            idle = 0
        if be and pos != 0 and t1 is not None and not t1_hit and exits.reached(pos, h[i], l[i], t1):
            t1_hit = True                                         # 2b. Target 1 traded in this bar: the stop goes to
            if half:                                              # the entry, live from the next bar, never looser;
                take_half(i, float(t1), "T1")                     # under half_t1 half is closed at the target first
            stop = exits.be_stop(pos, entry, stop)
        if t2x and pos != 0 and t1_hit and t2 is not None and exits.reached(pos, h[i], l[i], t2):
            close(i, float(t2), "T2")                             # 2c. Target 2 traded: what is left goes AT Target 2
            idle = 0
        pu = p_up[i]                                              # 3. the decision at this close
        a, target, why = policy.decide(pos, idle, None if pu != pu else pu, p_dn[i], bool(shock[i]),
                                       tide[i] if tide[i] == tide[i] else 0.0, cfg,
                                       bias=0 if bias is None or bias[i] != bias[i] else int(bias[i]),
                                       guard=False if guard is None else bool(guard[i]))
        if a == policy.IDLE:
            idle += 1
        elif a == policy.STEP_ASIDE:
            idle = 1
        elif a != policy.HOLD:
            idle = 0
        if a in (policy.ENTER, policy.FORCED, policy.FLIP, policy.STEP_ASIDE):
            delay = int(cfg.get("fill_delay_bars", 0) or 0)       # bars a late feed adds before a fill is possible
            if not (delay and pending is not None and pending[1] == target):   # an order already waiting keeps its place
                pending = (a, target, why) if not delay else (a, target, why, delay)
        act[i], idle_arr[i], stop_arr[i], reason[i] = ACT_CODE[a], idle, stop, why
        eq_arr[i] = eq + (qty * pos * (c[i] - entry) if pos else 0.0)
    end_state = {"pos": int(pos), "idle": int(idle), "qty": float(qty), "entry": float(entry),
                 "stop": None if stop != stop else float(stop), "eq": float(eq), "why_in": why_in,
                 "pending": list(pending) if pending else None, "entered_here": bool(t_in >= 0),
                 "i_in": int(t_in), "fees": fees_paid[0]}
    if be:                                                        # only books under the rule carry these (others unchanged)
        end_state.update(t1=None if (t1 is None or not pos) else float(t1), t1_hit=bool(t1_hit and pos),
                         stop0=None if (stop0 != stop0 or not pos) else float(stop0), be_t1=True)
    if half:
        end_state.update(half_t1=True, part=part if pos else None, half_due=bool(half_due and pos))
    if t2x:
        end_state.update(t2_exit=True, t2=None if (t2 is None or not pos) else float(t2))
    if pos != 0:                                                  # still open: mark it, charge nothing more
        trades.append((t_in, hi - 1, pos, entry, c[hi - 1], why_in, "OPEN", (pos * (c[hi - 1] - entry) / entry
                                                                             - fee) * 100.0, eq_arr[hi - 1],
                       qty, qty * pos * (c[hi - 1] - entry) - fee * qty * entry, fee * qty * entry))
    tr = pd.DataFrame(trades, columns=["i_in", "i_out", "side", "p_in", "p_out", "why_in", "why_out",
                                       "pnl_pct", "equity", "qty", "pnl_usd", "fees_usd"])
    return {"act": act, "held": held, "idle": idle_arr, "stop": stop_arr, "equity": eq_arr,
            "reason": reason, "trades": tr, "state": end_state, "parts": parts}


def max_flat_run(held, act, lo, hi):
    """The longest run of whole sessions spent flat once the engine has a model."""
    live = act[lo:hi] != ACT_CODE[policy.WAIT]
    first = int(np.argmax(live)) + 1 if live.any() else hi - lo
    best = run = 0
    for v in held[lo + first:hi]:
        run = run + 1 if v == 0 else 0
        best = max(best, run)
    return best


def summarize(book, times, lo, hi, cost_rt):
    eq = book["equity"][lo:hi]
    ok = np.isfinite(eq)
    eq = eq[ok]
    if len(eq) == 0:
        return {}
    t = times[lo:hi][ok]
    years = max((t[-1] - t[0]).total_seconds() / (365.25 * 86400), 1e-9)
    ret = eq[-1] / START_EQUITY - 1.0
    peak = np.maximum.accumulate(eq)
    dd = float((eq / peak - 1.0).min())
    tr = book["trades"]
    closed = tr[tr.why_out != "OPEN"]
    held = book["held"][lo:hi]
    act = book["act"][lo:hi]
    live = act != ACT_CODE[policy.WAIT]
    by_year = {}
    s = pd.Series(eq, index=t)
    for yr, grp in s.groupby(s.index.year):
        start = s[s.index < grp.index[0]]
        base = start.iloc[-1] if len(start) else START_EQUITY
        by_year[int(yr)] = round(float(grp.iloc[-1] / base - 1.0) * 100, 1)
    cagr = (1.0 + ret) ** (1.0 / years) - 1.0 if ret > -1 else -1.0
    return {
        "return_pct": round(ret * 100, 1), "cagr_pct": round(cagr * 100, 1), "max_drawdown_pct": round(dd * 100, 1),
        "calmar": round(cagr / abs(dd), 2) if dd < 0 else None, "years": round(years, 2),
        "trades": int(len(closed)), "trades_per_year": round(len(closed) / years, 1),
        "win_rate_pct": round(float((closed.pnl_pct > 0).mean() * 100), 1) if len(closed) else None,
        "avg_net_per_trade_pct": round(float(closed.pnl_pct.mean()), 3) if len(closed) else None,
        "avg_net_vs_round_trip": round(float(closed.pnl_pct.mean() / (cost_rt * 100)), 2) if len(closed) else None,
        "time_long_pct": round(float((held[live] == 1).mean() * 100), 1) if live.any() else 0.0,
        "time_short_pct": round(float((held[live] == -1).mean() * 100), 1) if live.any() else 0.0,
        "time_flat_pct": round(float((held[live] == 0).mean() * 100), 1) if live.any() else 0.0,
        "flips": int((closed.why_out == policy.FLIP).sum()), "stops": int(closed.why_out.isin(STOP_WORDS).sum()),
        "step_asides": int((closed.why_out == policy.STEP_ASIDE).sum()),
        "forced_entries": int((closed.why_in == policy.FORCED).sum()),
        "max_flat_sessions_in_a_row": int(max_flat_run(book["held"], book["act"], lo, hi)),
        "by_year_pct": by_year,
    }


def skill(prep, lo, hi):
    """Are the odds worth anything? Graded calls made in sessions lo .. hi-1."""
    out = {"voices": {}, "calibration": [], "by_month": {}}
    rows = []
    for a in prep["assets"]:
        y, probs, odds = prep["y"][a][lo:hi], prep["probs"][a][lo:hi], prep["odds"][a][lo:hi]
        ok = (y >= 0) & np.isfinite(odds[:, 0])
        yi = y[ok].astype(int)
        ll_mix = -np.log(np.clip(odds[ok][np.arange(ok.sum()), yi], 1e-9, 1))
        ll_v = -np.log(np.clip(probs[ok][np.arange(ok.sum())[:, None], np.arange(probs.shape[1])[None, :],
                                         yi[:, None]], 1e-9, 1))
        edge = odds[ok][:, labels.UP] - odds[ok][:, labels.DOWN]
        rows.append(pd.DataFrame({"t": prep["times"][lo:hi][ok], "y": yi, "ll": ll_mix, "edge": edge,
                                  **dict(("v_" + v, ll_v[:, k]) for k, v in enumerate(model.VOICE_NAMES))}))
    d = pd.concat(rows)
    if not len(d):
        return out
    base = d["v_base"].mean()

    def hits(g, bar=0.05):
        g = g[(g.edge.abs() >= bar) & (g.y > 0)]
        if not len(g):
            return None, 0
        return round(float((((g.edge > 0) & (g.y == labels.UP)) | ((g.edge < 0) & (g.y == labels.DOWN))).mean() * 100), 1), int(len(g))

    out["calls_graded"] = int(len(d))
    out["logloss_engine"], out["logloss_base_rate"] = round(float(d.ll.mean()), 4), round(float(base), 4)
    out["skill_vs_base_rate_pct"] = round(float(1 - d.ll.mean() / base) * 100, 2)
    out["direction_hit_pct_when_edge_5pts"], out["direction_calls"] = hits(d)
    for v in model.VOICE_NAMES:
        out["voices"][v] = round(float(1 - d["v_" + v].mean() / base) * 100, 2)
    d["bucket"] = pd.qcut(d.edge, 5, labels=False, duplicates="drop")
    for _, g in d.groupby("bucket"):
        out["calibration"].append({"edge_said": round(float(g.edge.mean()) * 100, 1),
                                   "edge_happened": round(float(((g.y == labels.UP).mean() - (g.y == labels.DOWN).mean()) * 100), 1),
                                   "calls": int(len(g))})
    for m, g in d.groupby(d.t.dt.strftime("%Y-%m")):
        hit, n = hits(g)
        out["by_month"][m] = {"skill_pct": round(float(1 - g.ll.mean() / g["v_base"].mean()) * 100, 2),
                              "hit_pct": hit, "direction_calls": n}
    return out


def _books(prep, odds_of, lo, hi, cost_mult=1.0):
    cfg = prep["cfg"]
    out = {}
    for a in prep["assets"]:
        ev = prep["ev"][a]
        out[a] = run_book(prep["px"][a], odds_of(a), ev["shock"].values, ev["tide"].values,
                          (cfg["barrier_atr"] * ev["atr1h"]).values, cfg, lo, hi, cost_mult,
                          bias=ev["htf_bias"].values if "htf_bias" in ev else None,
                          guard=ev["release_soon"].values if "release_soon" in ev else None)
    return out


def evaluate(prep, start, end=None, controls=0, seed=7, log=None):
    """The engine, its benchmarks and its controls over [start, end]."""
    say = log or (lambda *_: None)
    cfg, times = prep["cfg"], prep["times"]
    lo = max(int(times.searchsorted(pd.Timestamp(start, tz="UTC"))), prep["birth_idx"])
    hi = len(times) if end is None else int(times.searchsorted(pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)))
    rt = 2 * cfg["cost_side"]
    books = _books(prep, lambda a: prep["odds"][a], lo, hi)
    res = {"window": [str(times[lo]), str(times[hi - 1])], "engine": {}, "cost_stress": {}, "buy_and_hold": {},
           "voices_alone": {}, "tide_only": {}, "shifted_control": {}}
    for a in prep["assets"]:
        res["engine"][a] = summarize(books[a], times, lo, hi, rt)
        c, o = prep["px"][a]["close"], prep["px"][a]["open"]
        seg = c[lo:hi] / o[lo]
        res["buy_and_hold"][a] = {"return_pct": round(float(seg[-1] * (1 - rt) - 1) * 100, 1),
                                  "max_drawdown_pct": round(float((seg / np.maximum.accumulate(seg) - 1).min()) * 100, 1)}
    say("engine walked")
    for mult in (1.5, 2.2):
        b = _books(prep, lambda a: prep["odds"][a], lo, hi, mult)
        res["cost_stress"]["x%s" % mult] = dict((a, summarize(b[a], times, lo, hi, rt)["return_pct"]) for a in prep["assets"])
    for k, v in enumerate(model.VOICE_NAMES):
        b = _books(prep, lambda a: prep["probs"][a][:, k, :], lo, hi)
        res["voices_alone"][v] = dict((a, {"return_pct": s["return_pct"], "max_drawdown_pct": s["max_drawdown_pct"],
                                           "trades": s["trades"]})
                                      for a, s in ((a, summarize(b[a], times, lo, hi, rt)) for a in prep["assets"]))

    def tide_odds(a):
        lab = np.sign(prep["ev"][a]["tide"].fillna(0).values) * (prep["ev"][a]["tide"].abs().fillna(0).values >= 0.5)
        od = np.full((len(times), 3), 1.0 / 3)
        od[:, labels.UP] += 0.1 * lab
        od[:, labels.DOWN] -= 0.1 * lab
        od[~np.isfinite(prep["odds"][a][:, 0])] = np.nan
        return od
    b = _books(prep, tide_odds, lo, hi)
    res["tide_only"] = dict((a, summarize(b[a], times, lo, hi, rt)["return_pct"]) for a in prep["assets"])
    say("benchmarks walked")
    rng = np.random.RandomState(seed)
    month = 30 * 96
    draws = dict((a, []) for a in prep["assets"])
    for _ in range(controls):
        k = int(rng.randint(month, max(hi - lo - month, month + 1)))

        def shifted(a):
            od = prep["odds"][a].copy()
            od[lo:hi] = np.roll(od[lo:hi], k, axis=0)
            return od
        b = _books(prep, shifted, lo, hi)
        for a in prep["assets"]:
            draws[a].append(summarize(b[a], times, lo, hi, rt)["return_pct"])
    for a in prep["assets"] if controls else []:
        d = np.array(draws[a])
        mine = res["engine"][a]["return_pct"]
        res["shifted_control"][a] = {"draws": int(len(d)), "median_return_pct": round(float(np.median(d)), 1),
                                     "p95_return_pct": round(float(np.percentile(d, 95)), 1),
                                     "engine_beats_pct_of_draws": round(float((mine > d).mean() * 100), 1)}
    res["skill"] = skill(prep, lo, hi)
    trust = prep["trust"][lo:hi]
    res["trust_mean"] = dict((v, round(float(trust[:, k].mean()), 3)) for k, v in enumerate(model.VOICE_NAMES))
    res["trust_last"] = dict((v, round(float(trust[-1, k]), 3)) for k, v in enumerate(model.VOICE_NAMES))
    return res, books, (lo, hi)


def store_from(prep, books, span):
    """Everything the journal, the post-mortem and the page need, in one dict."""
    f32 = lambda d: dict((a, d[a].astype(np.float32)) for a in prep["assets"])      # noqa: E731
    if "lean_lo" in prep:                                          # the live step's lean prep: X is a memory map
        from .leanprep import Tail
        lo, n = prep["lean_lo"], len(prep["times"])
        X32 = dict((a, Tail(np.asarray(prep["X"][a][lo:n]).astype(np.float32), lo, n)) for a in prep["assets"])
    else:
        X32 = f32(prep["X"])
    return {"cfg": prep["cfg"], "assets": prep["assets"], "times": prep["times"], "span": span, "ev": prep["ev"],
            "px": prep["px"], "X": X32, "probs": f32(prep["probs"]), "odds": f32(prep["odds"]),
            "y": prep["y"], "res": prep["res"], "trust": prep["trust"].astype(np.float32),
            "models": [(s, w["all"], n) for s, w, n in prep["models"]], "books": books}


def save_run(name, prep, res, books, span):
    out = os.path.join(OUT_DIR, name)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    for a in prep["assets"]:
        tr = books[a]["trades"].copy()
        tr.insert(0, "time_in", prep["times"][tr.i_in.values])
        tr.insert(1, "time_out", prep["times"][tr.i_out.values])
        tr.to_csv(os.path.join(out, "trades_%s.csv" % a), index=False)
    store = store_from(prep, books, span)
    with open(os.path.join(out, "store.pkl"), "wb") as fh:
        pickle.dump(store, fh, protocol=4)
    return out


def main(argv):
    """py -3 -m engine15 backtest [controls]  -- replay all history (the engine's warm-up and its
    first post-mortem material). Not a pass/fail test: see THOUGHT_PROCESS.md, "What the replay is"."""
    prep = prepare(log=print)
    res, books, span = evaluate(prep, CFG["birth"], controls=int(argv[0]) if argv else 0, log=print)
    out = save_run("replay", prep, res, books, span)
    brief = dict((k, res[k]) for k in ("window", "engine", "buy_and_hold", "tide_only", "cost_stress"))
    print(json.dumps(brief, indent=1))
    print(json.dumps(dict((k, v) for k, v in res["skill"].items() if k != "by_month"), indent=1))
    print("trust (mean):", res["trust_mean"])
    print("saved to", out)


if __name__ == "__main__":
    main(sys.argv[1:])
