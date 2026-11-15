# -*- coding: utf-8 -*-
"""intraday -- workstream M: the intraday mind (docs/CHARTER.md M1-M6, docs/INTRADAY.md). PAPER ONLY.

The main engine asks one question: "over the next 24 HOURS, will price first move 1.5 x ATR(1h)
up or down?", then holds for days. This module asks the same voices two shorter questions and
trades them as swings with a stop, a target and a clock:

M1  SHORT-HORIZON MINDS. The same evidence (evidence.matrix) and the same voting voices
    (CFG["voting"]), each refitted on triple-barrier grades at a shorter horizon:
        1h mind   4 bars (1 hour),   barrier 0.75 x ATR(14) of the 1h chart, each side
        4h mind   16 bars (4 hours), barrier 1.0  x ATR(14) of the 1h chart
    Why 0.75 x ATR(1h) and not 1 x ATR(15m) for the 1h mind: about the same size (an hour's
    ATR is roughly twice a 15m bar's), but the 1h ATR is the yardstick every other part of the
    engine uses and it does not jump on one wide 15m bar, so a call's barrier (and the swing
    book's risk unit) is steadier; and a slightly wider barrier keeps the risk unit further
    above the round-trip cost (a 1 x ATR(15m) barrier on BTC is often no wider than 0.20%,
    the crypto round trip itself).
    The fitting is model.fit_softmax with the main engine's ridge and row step; trust and the mix
    are model.trust_path / model.mix. Refits are anchored to UTC Monday 00:00 (one fit a week, on
    every row graded before that Monday), so a fitted week can be cached (data/) and the live step
    only fits once a week.
M2  EXPECTED VALUE PER TRADE (in R, the stop distance): EV = P(target side first) x 1
    - P(stop side first) x 1 - round-trip cost / risk. The probabilities are what the mind
    predicts, for a 1-barrier move each way within the horizon; a call that times out ("neither")
    is counted at 0 R before costs. A trade is allowed only when EV >= margin.
M3  SWING TRADE MANAGEMENT (run_swing): flat until EV clears the margin; entry at the next open;
    stop at the last confirmed swing beyond the entry (plus a 0.1-barrier buffer) when it sits
    0.5 to 1.5 barriers away, else 1 barrier; target at target_r x R (or the realistic reach of the
    ltf card when asked and it lies 1R-3R away); time stop at the horizon; a stop and a target in
    one bar count as the stop; re-entry is allowed at any later close; a trade whose clock runs out
    while its own side still clears the margin is RENEWED (kept, clock restarted, no fees). No
    mandate: the swing book may stay flat as long as nothing clears the margin (no forced entries;
    the owner's always-positioned mandate stays with the main book). Size: backtest.leverage on the
    stop distance (2% of equity at risk, between 1x and the asset's cap).
M5  live_minds(): the short-horizon odds inside the live step, from the main step's own prep, with
    fitted weeks cached in data/intraday_minds_<group>.json; shadows.py trades them as m_swing_1h /
    m_swing_4h.
M6  per-step hit rates per horizon (1h, 4h, and the main 24h) per market over 7 and 30 days,
    kept in data/horizon_skill_live.json; reports.horizon_skill writes the weekly report.

Nothing here changes the main book: backtest.prepare and backtest.run_book are not touched.
"""
import json
import os
import time
from collections import OrderedDict

import numpy as np
import pandas as pd

from . import labels, model
from .config import CFG, DATA_DIR

# ---- constants, declared once before any history read (docs/INTRADAY.md)
MINDS = OrderedDict([("1h", {"horizon": 4, "barrier_atr": 0.75}),
                     ("4h", {"horizon": 16, "barrier_atr": 1.0})])
REF_24H = {"horizon": 96, "barrier_atr": 1.5}      # the main engine's question, for comparison
FIT_ITERS = 10                                      # Newton steps from zero (no warm start: cache-stable)
TRUST_DAYS = 90                                     # live: trust is walked over the last 90 days (10-day half-life)
EDGE_BAR = 0.05                                     # a "claimed edge": |P(up) - P(down)| >= 5 points (as the main page)
STRUCT_RANGE = (0.5, 1.5)                           # a swing stop is used when 0.5 to 1.5 barriers from the price
STRUCT_BUFFER = 0.1                                 # ... placed 0.1 barrier beyond the swing
REACH_RANGE = (1.0, 3.0)                            # a reach target is used when 1R to 3R away
SESSIONS = (("asia", 21, 7), ("london", 7, 12), ("overlap", 12, 16), ("ny", 16, 21))   # UTC hour of the decision close

# The registered swing rules (H18, H19 in docs/INTRADAY.md), what the live books trade.
#  1h: declared before the history read (structure stop, 1.5R, margin 0.05 R). research/intraday_study.py
#      found no 1h variant with the 300 first-half trades needed to choose one, so the declared rule stands
#      (it will seldom trade: EV after costs cleared 0.05 R on 0% of sessions in history).
#  4h: chosen on the FIRST HALF of history (2020 to Jun 2023, all eight markets pooled, 48 variants tried):
#      structure stop, 1R target, margin 0 R. It lost after costs in both halves (-0.054 / -0.064 R a trade,
#      about 0 R before costs); it runs forward to be graded, not because history favours it.
SWING_RULES = OrderedDict([
    ("1h", {"swing": True, "mind": "1h", "horizon": 4, "barrier_atr": 0.75, "stop": "structure", "swing_tf": "15m",
            "target": "r", "target_r": 1.5, "margin": 0.05}),
    ("4h", {"swing": True, "mind": "4h", "horizon": 16, "barrier_atr": 1.0, "stop": "structure", "swing_tf": "1h",
            "target": "r", "target_r": 1.0, "margin": 0.0}),
])
DEFAULT_RULE = SWING_RULES["1h"]
TRADE_COLS = ["t_in_ms", "t_out_ms", "i_in", "i_out", "side", "p_in", "p_out", "why_in", "why_out", "pnl_pct",
              "equity", "qty", "pnl_usd", "fees_usd", "stop0", "risk_usd", "r_mult", "target_1", "target_2", "r_gross"]
START_EQUITY = 10000.0
CACHE_FMT = os.path.join(DATA_DIR, "intraday_minds_%s.json")
SKILL_PATH = os.path.join(DATA_DIR, "horizon_skill_live.json")


# =====================================================================================
# M1: the minds
# =====================================================================================
def session_of(times):
    """Session name of each decision close (bar open + 15 minutes), by UTC hour."""
    hrs = np.asarray((pd.DatetimeIndex(times) + pd.Timedelta(minutes=15)).hour)
    out = np.empty(len(hrs), dtype=object)
    for name, a, b in SESSIONS:
        m = (hrs >= a) & (hrs < b) if a < b else (hrs >= a) | (hrs < b)
        out[m] = name
    return out


def voice_set(cfg=CFG, voices=None):
    """The voices a short-horizon mind fits: the main engine's voting voices, then the no-skill base."""
    want = voices if voices is not None else cfg.get("voting") or [v for v in model.VOICE_NAMES if v not in ("all", "base")]
    vs = [v for v in model.VOICE_NAMES if v in want and v not in ("all", "base")]
    return vs + ["base"]


def cols_for(voices, feature_names=None):
    """voice -> column indices in a matrix whose columns are `feature_names` (default: all FEATURES)."""
    from .evidence import FEATURES
    names = list(feature_names) if feature_names is not None else list(FEATURES)
    pos = dict((f, k) for k, f in enumerate(names))
    return dict((v, [pos[f] for f in model.VOICES[v][1] if f in pos]) for v in voices)


def labels_for(px, atr1h, mind):
    """Triple-barrier grades of one asset at a mind's horizon and barrier."""
    unit = mind["barrier_atr"] * np.asarray(atr1h, dtype=float)
    return labels.triple_barrier(px["open"], px["high"], px["low"], unit, int(mind["horizon"]))


def fit_points(times, lo, hi, every_weeks=1):
    """[(week_ms, fit_idx, seg_lo, seg_hi)]: sessions lo .. hi-1 cut at UTC Mondays 00:00 (every
    `every_weeks` weeks, counted from 1970); each segment is answered by voices fitted at fit_idx,
    the first session at or after its Monday (rows graded by then only)."""
    if hi <= lo:
        return []
    t = pd.DatetimeIndex(times[lo:hi])
    ms = np.asarray(t.as_unit("ms").asi8, dtype="int64")
    monday0 = 4 * 86400000 - 0                                    # 1970-01-05 00:00 UTC was a Monday
    span = 7 * 86400000 * int(every_weeks)
    wk = (ms - monday0) // span * span + monday0
    cut = np.flatnonzero(np.diff(wk)) + 1
    starts = np.concatenate([[0], cut])
    ends = np.concatenate([cut, [len(ms)]])
    allms = np.asarray(pd.DatetimeIndex(times).as_unit("ms").asi8, dtype="int64")
    out = []
    for s0, s1 in zip(starts, ends):
        w = int(wk[s0])
        out.append((w, int(np.searchsorted(allms, w)), lo + int(s0), lo + int(s1)))
    return out


def fit_voices(X, ready, y, cols, voices, s, floor, H, cfg):
    """One refit at session s: every voice on the rows graded by then (t <= s - H), from `floor`,
    one row per cfg["train_step"], all assets pooled. -> {voice: W} or None (too few rows)."""
    step = int(cfg["train_step"])
    rows = np.arange(floor, s - H + 1, step)
    if len(rows) == 0:
        return None
    Xs, ys = [], []
    for a in X:
        rr = rows[rows < len(y[a])]
        ok = ready[a][rr] & (y[a][rr] >= 0)
        Xs.append(np.asarray(X[a][rr[ok]], dtype=float))
        ys.append(y[a][rr[ok]])
    Xtr, ytr = np.concatenate(Xs), np.concatenate(ys)
    if len(ytr) < cfg["min_train_rows"]:
        return None
    out = {}
    for v in voices:
        W = model.fit_softmax(Xtr[:, cols[v]], ytr, cfg["l2"], None, FIT_ITERS)
        if cfg.get("even_prior"):
            W[:, 0] = W[:, 0].mean()
        out[v] = W
    return out


def walk(X, ready, y, times, cols, voices, cfg, H, lo, hi, floor, cache=None, every_weeks=1, log=None):
    """Walk the voices forward over sessions lo .. hi-1 with no look-ahead.
    cache: {str(week_ms): {voice: W as lists}}, filled in place (a fitted week never changes).
    -> {asset: (hi - lo, V, 3) probabilities}, NaN where no model or no evidence."""
    V = len(voices)
    probs = dict((a, np.full((hi - lo, V, 3), np.nan)) for a in X)
    fitted = 0
    for w, s, s0, s1 in fit_points(times, lo, hi, every_weeks):
        key = str(w)
        Ws = None
        if cache is not None and key in cache:
            Ws = dict((v, np.asarray(cache[key][v], dtype=float)) for v in voices) if cache[key] else None
        else:
            Ws = fit_voices(X, ready, y, cols, voices, s, floor, H, cfg)
            fitted += 1
            if cache is not None:
                cache[key] = None if Ws is None else dict((v, Ws[v].tolist()) for v in voices)
        if Ws is None:
            continue
        for a in X:
            seg = slice(s0, s1)
            Xa = np.asarray(X[a][seg], dtype=float)
            rd = ready[a][seg]
            for k, v in enumerate(voices):
                pr = model.predict(Ws[v], Xa[:, cols[v]])
                pr[~rd] = np.nan
                probs[a][s0 - lo:s1 - lo, k] = pr
    if log and fitted:
        log("intraday: %d weekly refit(s)" % fitted)
    return probs


def mix_odds(probs, X, y, res, cols, voices, cfg, lo, hi):
    """Trust (model.trust_path on the window) and the engine-style mix: only the voting voices share
    the trust (the base voice is fitted for grading, never mixed), and a voice with no reading on a
    session has no vote there (as backtest.prepare). -> ({asset: (hi-lo, 3)}, trust (hi-lo, V))."""
    yw = dict((a, y[a][lo:hi]) for a in probs)
    rw = dict((a, res[a][lo:hi]) for a in probs)
    trust = model.trust_path(probs, yw, rw, cfg)
    votes = np.array([0.0 if v == "base" else 1.0 for v in voices])
    trust = trust * votes
    trust = trust / np.where(trust.sum(axis=1, keepdims=True) > 0, trust.sum(axis=1, keepdims=True), 1.0)
    trust = model.cap_shares(trust, cfg.get("trust_cap"))             # v5.2: no card above the cap
    odds = {}
    for a in probs:
        Xa = np.asarray(X[a][lo:hi], dtype=float)
        speaks = np.stack([(np.abs(Xa[:, cols[v]]).sum(axis=1) > 0) if cols[v] else np.zeros(hi - lo, bool)
                           for v in voices], axis=1)
        w = trust * speaks
        tot = w.sum(axis=1, keepdims=True)
        w = np.where(tot > 0, w / np.where(tot > 0, tot, 1.0), trust)
        w = model.cap_shares(w, cfg.get("trust_cap"))
        odds[a] = model.mix(np.nan_to_num(probs[a], nan=0.0), w)
        odds[a][~np.isfinite(probs[a][:, 0, 0])] = np.nan
    return odds, trust


def mind_odds(X, ready, px, atr1h, times, cols, voices, cfg, mind, lo, hi, floor, cache=None, every_weeks=1, log=None):
    """One short-horizon mind over sessions lo .. hi-1 of a market group.
    -> {"y", "res": full-length per asset; "probs", "odds": full-length (n, V, 3) / (n, 3), NaN outside
        lo .. hi-1; "trust": (hi-lo, V)}"""
    H = int(mind["horizon"])
    n = len(times)
    y, res = {}, {}
    for a in X:
        y[a], res[a] = labels_for(px[a], atr1h[a], mind)
    pw = walk(X, ready, y, times, cols, voices, cfg, H, lo, hi, floor, cache, every_weeks, log)
    ow, trust = mix_odds(pw, X, y, res, cols, voices, cfg, lo, hi)
    if lo == 0 and hi == n:                                      # the whole span (history study): no copies
        return {"y": y, "res": res, "probs": pw, "odds": ow, "trust": trust}
    probs, odds = {}, {}
    for a in X:
        probs[a] = np.full((n, len(voices), 3), np.nan)
        probs[a][lo:hi] = pw[a]
        odds[a] = np.full((n, 3), np.nan)
        odds[a][lo:hi] = ow[a]
    return {"y": y, "res": res, "probs": probs, "odds": odds, "trust": trust}


# =====================================================================================
# M2: expected value per trade
# =====================================================================================
def ev_r(p_win, p_loss, cost_side, price, risk):
    """Expected value in R of a trade risking `risk` (price units) with a target as far as the stop:
    P(win) x 1 - P(loss) x 1 - round-trip cost / risk. NaN where it cannot be read."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.asarray(p_win, float) - np.asarray(p_loss, float) - 2.0 * cost_side * np.asarray(price, float) / np.asarray(risk, float)


def best_ev(odds, cost_side, price, risk):
    """Per session: (side +1/-1, EV in R of that side) for a 1-barrier stop and target."""
    up = ev_r(odds[:, labels.UP], odds[:, labels.DOWN], cost_side, price, risk)
    dn = ev_r(odds[:, labels.DOWN], odds[:, labels.UP], cost_side, price, risk)
    side = np.where(dn > up, -1, 1)
    return side, np.where(side == 1, up, dn)


# =====================================================================================
# M3: the swing book
# =====================================================================================
def _blank_stats():
    return {"n": 0, "wins": 0, "pnl": 0.0, "r_sum": 0.0, "r_n": 0, "win_usd": 0.0, "loss_usd": 0.0}


def run_swing(px, odds, unit, cfg, lo, hi, state=None, guard=None, rule=None, aux=None, times_ms=None):
    """One asset's swing book over sessions lo .. hi-1 (rules in the module text).
    odds: the mind's (n, 3) odds; unit: the mind's barrier in price (barrier_atr x ATR(1h)) per session.
    aux (optional): {"sw_lo", "sw_hi"} 15m swings, {"sw_lo_1h", "sw_hi_1h"}, {"reach": {"1h": %, "4h": %}}.
    state resumes a book exactly where an earlier call stopped.
    -> {"trades", "equity", "held", "state"} (shadows.run's shape)."""
    from .backtest import leverage
    rule = dict(DEFAULT_RULE, **(rule or {}))
    H, margin, k_r = int(rule["horizon"]), float(rule["margin"]), float(rule["target_r"])
    use_struct, use_reach = rule.get("stop") == "structure", rule.get("target") == "reach"
    aux = aux or {}
    tf = rule.get("swing_tf", "15m")
    sw_lo = aux.get("sw_lo" if tf == "15m" else "sw_lo_" + tf) if use_struct else None
    sw_hi = aux.get("sw_hi" if tf == "15m" else "sw_hi_" + tf) if use_struct else None
    reach = (aux.get("reach") or {}).get(rule.get("mind", "1h")) if use_reach else None
    n = len(px["close"])
    held = np.zeros(n, dtype=np.int8)
    eq_arr = np.full(n, np.nan)
    trades = []
    fee = cfg["cost_side"]
    tms = (lambda i: None) if times_ms is None else (lambda i: int(times_ms[i]))

    def seg(a):                                                  # plain floats for sessions lo .. hi-1 (speed)
        return None if a is None else np.asarray(a, dtype=float)[lo:hi].tolist()
    o, h, l, c = (seg(px[k]) for k in ("open", "high", "low", "close"))
    p_up, p_dn, un = seg(odds[:, labels.UP]), seg(odds[:, labels.DOWN]), seg(unit)
    sw_lo, sw_hi, reach = seg(sw_lo), seg(sw_hi), seg(reach)
    gd = None if guard is None else np.asarray(guard, dtype=bool)[lo:hi].tolist()
    st = json.loads(json.dumps(state)) if state else {}
    pos, qty, entry, eq = st.get("pos", 0), st.get("qty", 0.0), st.get("entry", 0.0), st.get("eq", START_EQUITY)
    nan = float("nan")
    stop = nan if st.get("stop") is None else st["stop"]
    stop0 = nan if st.get("stop0") is None else st["stop0"]
    target = nan if st.get("t1") is None else st["t1"]
    bars, why_in, t_in, t_in_ms = int(st.get("bars", 0)), st.get("why_in", ""), -1, st.get("t_in_ms")
    pending = list(st["pending"]) if st.get("pending") else None   # ["SWING", side, stop_lvl, dist, reach_pct, ev]
    fees_paid = float(st.get("fees", 0.0))
    renewals = int(st.get("renewals", 0))
    stats = dict(st.get("stats") or _blank_stats())
    lo_k, hi_k = STRUCT_RANGE

    def close(i, price, why):
        nonlocal pos, qty, eq, stop, stop0, target, fees_paid, bars
        gross = qty * pos * (price - entry)
        fees = fee * qty * (entry + price)
        eq += gross - fees
        fees_paid += fees
        risk = qty * abs(entry - stop0) if stop0 == stop0 else nan
        r = (gross - fees) / risk if risk and risk == risk else nan
        rg = gross / risk if risk and risk == risk else nan
        trades.append((t_in_ms, tms(i), t_in, i, pos, entry, price, why_in, why, (gross - fees) / (qty * entry) * 100.0,
                       eq, qty, gross - fees, fees, stop0, risk, r, target, None, rg))
        stats["n"] += 1
        stats["wins"] += int(gross - fees > 0)
        stats["pnl"] += gross - fees
        stats["win_usd" if gross - fees > 0 else "loss_usd"] += abs(gross - fees)
        if r == r:
            stats["r_sum"] += r
            stats["r_n"] += 1
        pos, qty, stop, stop0, target, bars = 0, 0.0, nan, nan, nan, 0

    def open_pos(i, j, p):
        nonlocal pos, qty, entry, stop, stop0, target, bars, why_in, t_in, t_in_ms
        side, lvl, dist, rch = int(p[1]), p[2], float(p[3]), p[4]
        e = o[j]
        if lvl is not None and lo_k * dist <= side * (e - lvl) <= hi_k * dist:
            s = float(lvl)
        else:
            s = e - side * dist
        R = abs(e - s)
        tgt_d = k_r * R
        if rch is not None and rch == rch:
            rd = rch / 100.0 * e
            if REACH_RANGE[0] * R <= rd <= REACH_RANGE[1] * R:
                tgt_d = rd
        pos, entry, stop, stop0, target, bars = side, e, s, s, e + side * tgt_d, 0
        qty = eq * leverage(cfg, e, R) / e
        why_in, t_in, t_in_ms = "EV %+.2fR" % p[5], i, tms(i)

    for j in range(hi - lo):
        i = lo + j
        if pos != 0 and bars >= H:                               # 1. the clock ran out: out at this open
            close(i, o[j], "TIME")
        if pending is not None:                                  # 2. an entry decided at the last close
            if pos == 0:
                open_pos(i, j, pending)
            pending = None
        held[i] = pos
        if pos != 0:                                             # 3. stop first, then the target
            bars += 1
            if (pos == 1 and l[j] <= stop) or (pos == -1 and h[j] >= stop):
                close(i, min(o[j], stop) if pos == 1 else max(o[j], stop), "STOP")
            elif (pos == 1 and h[j] >= target) or (pos == -1 and l[j] <= target):
                close(i, target, "TARGET")
        due = pos != 0 and bars >= H                             # 4. the decision at this close
        pu, dist = p_up[j], un[j]
        if (pos == 0 or due) and pu == pu and dist == dist and dist > 0 and not (gd is not None and gd[j]):
            best = None
            cj = c[j]
            for side in (1, -1):
                lvl, risk = None, dist                           # the stop: a swing in reach, else 1 barrier
                if sw_lo is not None and sw_hi is not None:
                    sw = sw_lo[j] if side == 1 else sw_hi[j]
                    if sw == sw:
                        cand = sw - side * STRUCT_BUFFER * dist
                        d = side * (cj - cand)
                        if lo_k * dist <= d <= hi_k * dist:
                            lvl, risk = cand, d
                pw, pl = (pu, p_dn[j]) if side == 1 else (p_dn[j], pu)
                ev = pw - pl - 2.0 * fee * cj / risk             # M2: EV in R after the round trip
                if ev == ev and ev >= margin and (best is None or ev > best[5]):
                    best = ["SWING", side, lvl, dist, None if reach is None else reach[j], ev]
            if best is not None:
                if due and best[1] == pos:                       # same side still clears: keep it, restart the clock
                    bars = 0
                    renewals += 1
                else:
                    pending = best
        eq_arr[i] = eq + (qty * pos * (c[j] - entry) if pos else 0.0)
    end = {"pos": int(pos), "qty": float(qty), "entry": float(entry), "stop": None if stop != stop else float(stop),
           "stop0": None if stop0 != stop0 else float(stop0), "t1": None if target != target else float(target),
           "t2": None, "eq": float(eq), "why_in": why_in, "pending": pending, "fees": float(fees_paid),
           "bars": int(bars), "i_in": int(t_in), "t_in_ms": t_in_ms if pos else None, "renewals": renewals,
           "idle": 0, "stats": stats}
    if hi > lo:
        end["mark"] = float(c[-1])
        end["mark_ms"] = tms(hi - 1)
        end["equity_marked"] = float(eq_arr[hi - 1])
    if trades:
        tr = pd.DataFrame(trades, columns=TRADE_COLS)
    else:                                                        # no trades: the same column types as a filled frame
        tr = pd.DataFrame(dict((k, pd.Series(dtype=_EMPTY_TYPES.get(k, "float64"))) for k in TRADE_COLS))
    return {"trades": tr, "equity": eq_arr, "held": held, "state": end}


_EMPTY_TYPES = {"t_in_ms": "int64", "t_out_ms": "int64", "i_in": "int64", "i_out": "int64", "side": "int64",
                "why_in": "str", "why_out": "str", "target_2": "object"}


# =====================================================================================
# M5 / M6: inside the live step
# =====================================================================================
def _sig(cfg, voices, mind):
    return "|".join([",".join(voices), str(mind["horizon"]), str(mind["barrier_atr"]), str(cfg["l2"]),
                     str(cfg["train_step"]), str(cfg.get("train_floor")), str(cfg["min_train_rows"]),
                     str(bool(cfg.get("even_prior"))), str(FIT_ITERS)])


def load_cache(group, path=None):
    p = path or CACHE_FMT % group
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as fh:
                return json.load(fh)
        except (ValueError, OSError):
            pass
    return {}


def save_cache(cache, group, path=None):
    p = path or CACHE_FMT % group
    with open(p + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(cache, fh)
    os.replace(p + ".tmp", p)


def skill_window(times, y, odds, hi, days):
    """Graded calls made in the last `days` days before session hi: direction hit rate and the hit
    rate of claimed-edge calls (|edge| >= 5 points). Only grades already known count."""
    if odds is None or y is None:
        return None
    t_end = times[hi - 1]
    lo = int(times.searchsorted(t_end - pd.Timedelta(days=days), side="right"))
    yy, od = y[lo:hi], odds[lo:hi]
    ok = (yy > 0) & np.isfinite(od[:, 0])
    edge = od[ok][:, labels.UP] - od[ok][:, labels.DOWN]
    hit = ((edge > 0) & (yy[ok] == labels.UP)) | ((edge < 0) & (yy[ok] == labels.DOWN))
    sure = np.abs(edge) >= EDGE_BAR
    return {"calls": int(ok.sum()), "hit_pct": round(100.0 * hit.mean(), 1) if ok.any() else None,
            "edge_calls": int(sure.sum()), "edge_hit_pct": round(100.0 * hit[sure].mean(), 1) if sure.any() else None}


def live_minds(prep, group, cache_path=None, skill_path=None, log=print):
    """The 1h and 4h minds on the live step's own prep (no new evidence is built). Weekly fits are
    cached; a step normally only predicts and walks trust over the last TRUST_DAYS days.
    -> {mind: {"odds": {asset: (n, 3)}, "y": {asset}, "unit_atr": barrier_atr}, "_seconds": float}"""
    t0 = time.time()
    cfg, times = prep["cfg"], prep["times"]
    n = len(times)
    assets = list(prep["assets"]) if "assets" in prep else list(prep["X"])
    voices = voice_set(cfg)
    cols = dict((v, model._COLS[v]) for v in voices)
    lo = max(int(prep.get("birth_idx", 0)), int(times.searchsorted(times[-1] - pd.Timedelta(days=TRUST_DAYS))))
    floor = int(times.searchsorted(pd.Timestamp(cfg.get("train_floor", cfg["birth"]), tz="UTC")))
    cache = load_cache(group, cache_path)
    X = dict((a, prep["X"][a]) for a in assets)
    ready = dict((a, prep["ready"][a]) for a in assets)
    px = dict((a, prep["px"][a]) for a in assets)
    atr = dict((a, prep["ev"][a]["atr1h"].values) for a in assets)
    out = {}
    first_week = fit_points(times, lo, n)[0][0] if n > lo else None
    for name, mind in MINDS.items():
        sig = _sig(cfg, voices, mind)
        mc = cache.get(name) if isinstance(cache.get(name), dict) and cache[name].get("sig") == sig else {"sig": sig, "weeks": {}}
        r = mind_odds(X, ready, px, atr, times, cols, voices, cfg, mind, lo, n, floor, mc["weeks"], log=log)
        if first_week is not None:                               # keep only the weeks still inside the window
            mc["weeks"] = dict((k, v) for k, v in mc["weeks"].items() if int(k) >= first_week)
        cache[name] = mc
        out[name] = {"odds": r["odds"], "y": r["y"], "barrier_atr": mind["barrier_atr"]}
    try:
        save_cache(cache, group, cache_path)
    except OSError as e:
        log("intraday: cache not saved (%r)" % (e,))
    try:
        update_skill(prep, group, out, skill_path)
    except Exception as e:                                       # a report never stops a step
        log("intraday: skill not updated (%r)" % (e,))
    out["_seconds"] = round(time.time() - t0, 2)
    return out


def update_skill(prep, group, minds, path=None):
    """Hit rates per horizon per market, last 7 and 30 days, into data/horizon_skill_live.json."""
    path = path or SKILL_PATH
    times, n = prep["times"], len(prep["times"])
    assets = list(prep["assets"]) if "assets" in prep else list(prep["X"])
    rows = {}
    for a in assets:
        r = {}
        for name in MINDS:
            r[name] = dict((("d%d" % d), skill_window(times, minds[name]["y"][a], minds[name]["odds"][a], n, d))
                           for d in (7, 30))
        main_h = int(prep["cfg"].get("horizon", 96))
        r["24h"] = dict((("d%d" % d), skill_window(times, prep["y"][a], prep["odds"][a], n, d)) for d in (7, 30))
        r["24h"]["bars"] = main_h
        rows[a] = r
    doc = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
        except (ValueError, OSError):
            doc = {}
    doc.setdefault("groups", {})[group] = {"as_of_utc": str(times[-1] + pd.Timedelta(minutes=15))[:16], "assets": rows}
    doc["updated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(doc, fh)
    os.replace(path + ".tmp", path)
    return doc
