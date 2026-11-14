# -*- coding: utf-8 -*-
"""policy3 -- turning Q values into 15m decisions, with inaction as the default.

At the close of every 15m bar the agent holds position p (its own last target, before risk sizing) and may
change it. The greedy choice is argmax over allowed actions of Q(x_t, p); then, in this order:

  forced     if p itself is not allowed at t (a mask closed it, e.g. the momentum direction flipped under the
             meta-labeling harness, or the higher-timeframe filter says flat), move to the best allowed action;
  min hold   otherwise a change is refused until min_hold bars after the last change;
  gate       a change is refused while the bar's gate is closed (volatility / cost gate);
  band       a change needs Q(x,p)[a] - Q(x,p)[p] > thr[t] x |a - p| (confidence gate; thr in reward units);
  hold       otherwise p stays. Holding is free.

consensus() runs several seeds' Q arrays as one book: a change happens only when EVERY seed wants to leave p
and they agree on the side (then the smallest size they agree on), otherwise hold.

fast_net() is the backtester's per-bar formula on Market arrays (tests check it equals backtest.run), used for
validation inside training windows.
"""
import numpy as np

from . import metrics


def prepare(Q, masks=None):
    """Q (n, P, A) -> best allowed action per (t, p), its advantage over holding, and forced flags."""
    n, P, A = Q.shape
    q = Q if masks is None else np.where(masks[:, None, :], Q, -np.inf)
    best = q.argmax(axis=2).astype(np.int16)
    qb = np.take_along_axis(q, best[:, :, None].astype(np.int64), axis=2)[:, :, 0]
    diag = Q[:, np.arange(P), np.arange(P)]
    adv = (qb - diag).astype(np.float32)
    forced = np.zeros((n, P), bool) if masks is None else ~masks[:, :P]
    return best, adv, forced


def decide(Q, actions, start_ip, min_hold=0, since0=None, masks=None, gate=None, thr=None, prepared=None):
    """-> (ip array of action indices decided at each bar, stats dict)."""
    best, adv, forced = prepared if prepared is not None else prepare(Q, masks)
    acts = np.asarray(actions, dtype=float)
    n = best.shape[0]
    out = np.empty(n, dtype=np.int16)
    ip = int(start_ip)
    since = int(min_hold if since0 is None else since0)
    st = {"changes": 0, "forced": 0, "min_hold_refusals": 0, "gate_refusals": 0, "band_holds": 0}
    bl, al, fl = best.tolist(), adv.tolist(), forced.tolist()
    gl = gate.tolist() if gate is not None else None
    tl = thr.tolist() if thr is not None else None
    for t in range(n):
        b = bl[t][ip]
        if b != ip:
            if fl[t][ip]:
                st["forced"] += 1
                ip, since = b, 0
                st["changes"] += 1
            elif since < min_hold:
                st["min_hold_refusals"] += 1
            elif gl is not None and not gl[t]:
                st["gate_refusals"] += 1
            elif tl is not None and al[t][ip] <= tl[t] * abs(acts[b] - acts[ip]):
                st["band_holds"] += 1
            else:
                ip, since = b, 0
                st["changes"] += 1
        out[t] = ip
        since += 1
    return out, st


def consensus(prepared_list, actions, start_ip, min_hold=0, since0=None):
    """Several seeds as one book: change only if every seed wants to leave p and all agree on the side."""
    acts = np.asarray(actions, dtype=float)
    lists = [(b.tolist(), f.tolist()) for b, _, f in prepared_list]
    n = prepared_list[0][0].shape[0]
    out = np.empty(n, dtype=np.int16)
    ip = int(start_ip)
    since = int(min_hold if since0 is None else since0)
    st = {"changes": 0, "forced": 0, "min_hold_refusals": 0, "disagree_holds": 0}
    zero = int(np.argmin(np.abs(acts)))
    for t in range(n):
        want = [bl[t][ip] for bl, _ in lists]
        forced = any(fl[t][ip] for _, fl in lists)
        if all(w != ip for w in want):
            sv = [acts[w] for w in want]
            if all(v > 0 for v in sv) or all(v < 0 for v in sv):
                cand = min(want, key=lambda w: abs(acts[w]))
            elif all(v == 0 for v in sv):
                cand = want[0]
            else:
                cand = zero if forced else ip
        else:
            cand = zero if forced else ip
        if cand != ip:
            if not forced and since < min_hold:
                st["min_hold_refusals"] += 1
            else:
                st["forced"] += int(forced)
                ip, since = cand, 0
                st["changes"] += 1
        elif all(w != ip for w in want):
            st["disagree_holds"] += 1
        out[t] = ip
        since += 1
    return out, st


def fast_net(market, tgt, lo, hi, start_pos=0.0):
    """Per-bar net and gross returns for bars lo+1 .. hi-1 of a target series decided at bars lo .. hi-1
    (the backtester's formula with delay 1: position at k = target at k-1, costs on the trade at k's open).
    start_pos = the position held over bar lo."""
    m, mod = market, market.model
    t = np.asarray(tgt, dtype=float)
    pos = t[:-1]                                         # held over bars lo+1 .. hi-1
    prev = np.concatenate([[start_pos], pos[:-1]])
    k = np.arange(lo + 1, hi)
    trade = np.abs(pos - prev)
    c = (mod.fee_side + mod.half_spread_bps * 1e-4 + mod.slippage_coef * m.vol[k - 1]) * trade
    f = pos * m.rate[k] if mod.funding else 0.0
    gross = pos * m.r_px[k]
    return gross - c - f, gross, pos


def quick_metrics(r_net, pos):
    eq = np.cumprod(1.0 + r_net)
    yrs = len(r_net) / metrics.BARS_PER_YEAR
    tr = np.abs(np.diff(pos, prepend=pos[0] if len(pos) else 0.0))
    return {"sharpe": metrics.sharpe(r_net), "total_return": float(eq[-1] - 1.0) if len(eq) else 0.0,
            "max_drawdown": metrics.max_drawdown(np.concatenate([[1.0], eq])),
            "turnover_per_year": float(tr.sum() / yrs) if yrs else 0.0,
            "trades": int(np.count_nonzero(tr)), "exposure": float(np.mean(pos != 0)) if len(pos) else 0.0}
