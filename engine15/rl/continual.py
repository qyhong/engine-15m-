# -*- coding: utf-8 -*-
"""continual -- training the Q agent per walk-forward fold, and keeping it learning as new 15m bars arrive.

Three ways to run the same agent through the out-of-sample span (every prediction uses only a model trained
on data before it):

  (a) static     the Phase 2 style: at each fold start (every 3 months) a fresh model is trained on the
                 previous 12 months (9 train + 3 validation for early stopping) and used, unchanged, for the
                 next 3 months.
  (b) continual  one model, trained once at the start of the out-of-sample span (= (a)'s first fold model),
                 then fine-tuned at every update (cadence in the config: daily or weekly, at the close of the
                 bar ending 00:00 UTC) on a replay buffer of the trailing 12 months with recency weights,
                 warm-started from the previous weights and optimiser state. Never reset.
  (c) continual + periodic full retrain   (a)'s fresh model at every fold start, fine-tuned at every update
                 inside the fold as in (b).

Timing honesty: an update at the close of bar U trains on decisions t <= U - n - 1 only (an n-step target for t
needs rewards up to decision t+n-1, i.e. open[t+n+1], known at the close of bar t+n, and the state at t+n) and refreshes the normaliser on bars <= U; the
decision taken at bar U's close already uses the updated model. tests/rl/test_continual.py checks that no
training sample ever reaches past the update bar and that a model is used only after it was trained.
"""
import time

import numpy as np

from . import policy3
from .qagent import Learner, q_from_w, recency_weights

BARS_DAY = 96


def update_bars(market, lo, hi, cadence_days):
    """Bars in [lo, hi) at whose close an update runs: closes at 00:00 UTC; weekly = Mondays."""
    cm = market.close_ms[lo:hi]
    on_day = (cm % 86400000) == 0
    day = cm // 86400000
    if int(cadence_days) == 7:
        sel = on_day & (((day + 3) % 7) == 0)
    else:
        sel = on_day & ((day % int(cadence_days)) == 0)
    return np.nonzero(sel)[0] + lo


def eval_q(market, Q, lo, hi, actions, pcfg, masks=None, start_ip=None):
    """Greedy policy on Q for bars [lo, hi), from flat -> quick metrics (net of the market's cost model)."""
    acts = np.asarray(actions, dtype=float)
    zero = int(np.argmin(np.abs(acts))) if start_ip is None else int(start_ip)
    ip, st = policy3.decide(Q, acts, zero, int(pcfg.get("min_hold_bars", 0)),
                            masks=None if masks is None else masks[lo:hi])
    tgt = acts[ip]
    r, g, pos = policy3.fast_net(market, tgt, lo, hi, start_pos=0.0)
    out = policy3.quick_metrics(r, pos)
    out.update(st)
    out["gross_sharpe"] = float(np.mean(g) / np.std(g) * np.sqrt(35040)) if np.std(g) > 0 else 0.0
    return out


def full_train(market, rd, b, qcfg, pcfg, actions, seed, masks=None, pause=None, where="", bc=None):
    """A fresh model on [tr_lo, val_lo), early stopping on [val_lo, tr_hi). -> (Learner, record).
    bc = (target_idx, prev_idx, steps): imitation warm start (behaviour cloning on the train slice) before RL."""
    t0 = time.time()
    raw = market.raw
    mu, sd = market.fit_norm(b["tr_lo"], b["tr_hi"])
    L = Learner(raw.shape[1], actions, qcfg, seed, mu, sd)
    ns = int(qcfg.get("n_step", 1))
    pool = np.arange(b["tr_lo"], b["val_lo"] - ns - 1)      # targets need bars up to t + n (inside the train slice)
    val_idx = np.arange(b["val_lo"], b["tr_hi"] - ns - 1)
    evals, every = int(qcfg["evals"]), int(qcfg["eval_every"])
    patience = int(qcfg.get("patience", 3))
    chunk = int(qcfg.get("chunk_steps", 500))
    best_key, best_state, hist, bad = None, None, [], 0
    bc_loss = None
    if bc is not None:
        bc_loss = L.bc(raw, rd, np.arange(b["tr_lo"], b["val_lo"]), bc[0], bc[1], int(bc[2]))
        if pause is not None:
            pause.check(where)
    for c in range(evals):
        done = 0
        while done < every:
            k = min(chunk, every - done)
            loss = L.train(raw, rd, pool, k, masks=masks)
            done += k
            if pause is not None:
                pause.check(where)
        Q = L.q(raw, rd, b["val_lo"], b["tr_hi"])
        v = eval_q(market, Q, b["val_lo"], b["tr_hi"], actions, pcfg, masks)
        vl = L.eval_loss(raw, rd, val_idx, masks)
        if qcfg.get("select_on", "val_loss") == "val_loss":
            key = (-round(vl, 7), -v["trades"])
        else:
            key = (round(v["sharpe"], 6), -v["trades"])
        hist.append({"check": c + 1, "steps": L.steps, "loss": round(loss, 5), "val_loss": round(vl, 6),
                     "val_sharpe": v["sharpe"], "val_trades": v["trades"]})
        if best_key is None or key > best_key:
            best_key, best_state, bad = key, L.state(), 0
            hist[-1]["kept"] = True
        else:
            bad += 1
            if bad >= patience:
                break
    L.load_state(best_state)
    fb = qcfg.get("fallback_val_sharpe")
    best_val = [h for h in hist if h.get("kept")][-1]["val_sharpe"]
    fallback = fb is not None and best_val < float(fb)   # 'do no harm': the fold acts neutral (see neutral_w); the
                                                         # weights are kept so continual learning can carry on
    Qtr = L.q(raw, rd, b["tr_lo"], b["val_lo"])
    tr = eval_q(market, Qtr, b["tr_lo"], b["val_lo"], actions, pcfg, masks)
    va = eval_q(market, L.q(raw, rd, b["val_lo"], b["tr_hi"]), b["val_lo"], b["tr_hi"], actions, pcfg, masks)
    kept = [h["check"] for h in hist if h.get("kept")][-1]
    rec = {"seed": int(seed), "steps_run": hist[-1]["steps"], "kept_check": kept, "checks": hist, "fallback": bool(fallback),
           "kept_val_sharpe": best_val, "bc_loss": bc_loss,
           "train": tr, "val": va, "seconds": round(time.time() - t0, 1)}
    return L, rec


def fine_tune(L, market, rd, U, qcfg, masks=None):
    """One scheduled update at the close of bar U: normaliser on the trailing window (bars <= U), then
    qcfg['finetune_steps'] gradient steps on decisions t in [U - replay, U - 2] with recency weights."""
    replay = int(qcfg["replay_days"]) * BARS_DAY
    lo = max(0, U - replay)
    mu, sd = market.fit_norm(lo, U + 1)
    L.set_norm(mu, sd)
    ns = int(qcfg.get("n_step", 1))
    pool = np.arange(lo, U - ns)                    # t + n <= U - 1: the last reward needs open[t+n+1], known by the close of bar U
    w = recency_weights(pool, U, float(qcfg.get("half_life_days", 0)) * BARS_DAY, float(qcfg.get("recency_mix", 0.0)))
    loss = L.train(market.raw, rd, pool, int(qcfg["finetune_steps"]), weights=w, masks=masks)
    return {"U": int(U), "pool_lo": int(pool[0]), "pool_hi": int(pool[-1]), "loss": loss}


def run_span(L, market, rd, lo, hi, qcfg, masks=None, cadence_days=None, pause=None, where="", on_update=None):
    """W values (afterstate values, qagent.py) for bars [lo, hi) with model L, fine-tuned at each update bar if
    cadence_days is set. Bars before the first update use L as given. -> (W (hi-lo, A) float32, update records).
    Q for decisions = qagent.q_from_w(W, k, c1, D, cfg)."""
    A = L.A
    Q = np.empty((hi - lo, A), dtype=np.float32)
    ups = [] if not cadence_days else list(update_bars(market, lo, hi, cadence_days))
    recs = []
    edges = [lo] + ups + [hi]
    for k in range(len(edges) - 1):
        a, b = edges[k], edges[k + 1]
        if k > 0:                                   # an update at the close of bar a, before deciding at a
            if pause is not None:
                pause.check(where)
            r = fine_tune(L, market, rd, a, qcfg, masks)
            recs.append(r)
            if on_update is not None:
                on_update(a, L)
        if b > a:
            Q[a - lo:b - lo] = L.w(market.raw[a:b])
    return Q, recs


def q_of(W, rd, lo, hi, L_or_cfg, actions):
    """Q (n, A, A) for bars [lo, hi) from stored W values."""
    from .qagent import cost_matrix
    cfg = L_or_cfg.cfg if hasattr(L_or_cfg, "cfg") else L_or_cfg
    return q_from_w(W, rd["k"][lo:hi], rd["c1"][lo:hi], cost_matrix(actions), cfg)


def neutral_w(n, actions, neutral, penalty=10.0):
    """W rows of the 'do no harm' neutral policy: -penalty x |a - neutral| (far above any cost), so the greedy policy
    moves to the neutral position (flat; 1x for core-satellite; no adjustment for residual agents) and stays."""
    a = np.asarray(actions, dtype=np.float32)
    return np.repeat((-float(penalty) * np.abs(a - float(neutral)))[None, :], int(n), axis=0).astype(np.float32)


def is_fallback(val_sharpe, qcfg):
    fb = qcfg.get("fallback_val_sharpe")
    return fb is not None and float(val_sharpe) < float(fb)
