# -*- coding: utf-8 -*-
"""learn6 -- Phase 6: reward shaping that makes 'flat' score worse (owner, 12 Nov 2026: "the RL need to learn to profit
from downtrend also. stay flat should have a weak scoring so the RL will have more motivation to take long or short").

WHY NOT THE LITERAL "net return - beta x reference return". With the Phase 3/4 afterstate learner the one-bar reward of
target a is scale x (k a g - ra a^2 v); subtracting beta x k x ref x g, a term that does not depend on a, shifts every
action's value W(x, a) by the same amount, so every comparison W(a) - W(p) - cost, i.e. every decision, is unchanged
(exactly so for the Bellman fixed point; with a fitted model only noise differs). Flat does score negative in a trend,
but so does long, by the same amount. To make flat weaker the penalty must depend on the action. Two such forms, both
applied in TRAINING only (decisions and every result use the real net P&L and the full round-trip cost):

  missed  (the owner's 'opportunity-relative' idea, action-dependent): the idle part of the book is charged what the
          trend reference earned on it:  r(a) = scale x k x ( a g - beta x (1 - |a|) x ref x g ) - scale x ra a^2 v
          ref = the frozen daily 30-day momentum target (+1 / -1, both directions, decided at the same close as a).
          Flat in a trend that pays scores negative (a missed long or a missed short); flat while the reference loses
          scores positive (a loss avoided). beta in {0.25, 0.5, 1.0}, chosen on the validation slice.
  flat    (the owner's literal idea): a small charge per bar on the idle part,
          r(a) = scale x k x ( a g - (1 - |a|) x lam x 2 c1 / 96 ) - scale x ra a^2 v
          i.e. a fully flat day costs lam x one round trip. lam in {0.25, 0.5, 1.0}, chosen on the validation slice.

q_fold6 = models4.q_fold with one more choice: for each shaping value, the half-life is chosen by the validation Bellman
loss as in Phase 4 (losses of different rewards are not comparable), then the shaping value is chosen by the validation
slice's real NET Sharpe (mean over BTC and ETH, greedy policy from flat, 0.10% costs); ties -> the smaller value. Refit on
everything up to the fold with the chosen value, half-life and step count. 'Do no harm' flags are computed as in Phase 4
and stored; Phase 6 evaluates three ways of using them (current rule = flat, none, the trend reference).
"""
import time

import numpy as np

from .models4 import _concat, _q_pool, _slim, policy_metrics
from .qagent import Learner, funded_vector

REF_COL = "mom_signal"


class Learner6(Learner):
    """The Phase 3 learner with an action-dependent training-only charge on the idle part of the book."""

    def __init__(self, n_features, actions, qcfg, seed=0, mu=None, sd=None, kind=None, value=0.0):
        super().__init__(n_features, actions, qcfg, seed, mu, sd)
        self.kind, self.value = kind, float(value)

    def _targets(self, raw, rd, idx, masks):
        torch = self.torch
        c = self.cfg
        A, B = self.A, len(idx)
        n = int(c.get("n_step", 1))
        gamma = float(c["gamma"])
        scale, cm, ra = float(c["reward_scale"]), float(c["cost_mult"]), float(c.get("risk_aversion", 0.0))
        a = self.act_t.view(1, A)
        idle = (1.0 - a.abs())
        mode = c.get("funding_mode", "perp")
        F = torch.tensor(funded_vector(self.actions, mode)).view(1, A)
        r = torch.zeros(B, A)
        for j in range(n):
            ij = idx + j
            col = lambda key: torch.from_numpy(rd[key][ij]).view(B, 1)
            if mode == "perp":
                ret = a * col("g")
            else:
                ret = a * col("rpx") - F * col("rate")
            if self.kind == "missed" and self.value:
                ret = ret - self.value * idle * col("ref") * col("g")
            elif self.kind == "flat" and self.value:
                ret = ret - idle * (self.value * 2.0 / 96.0) * col("c1")
            r = r + (gamma ** j) * scale * (col("k") * ret - ra * a * a * col("v"))
        i1 = idx + n
        x1 = torch.from_numpy(self._x(raw[i1]))
        k1 = torch.from_numpy(rd["k"][i1]).view(B, 1, 1)
        c11 = torch.from_numpy(rd["c1"][i1]).view(B, 1, 1)
        cost1 = scale * cm * k1 * c11 * self.D_t.view(1, A, A)
        w1o = self.net(x1).view(B, 1, A) - cost1
        w1t = self.tgt(x1).view(B, 1, A) - cost1
        best = w1o.argmax(dim=2, keepdim=True)
        v1 = w1t.gather(2, best).squeeze(2)
        return r + (gamma ** n) * v1


def add_reference(A, col=REF_COL):
    """Put the trend reference (the frozen daily momentum target at each bar) into an asset's reward arrays."""
    if "ref" not in A.rd:
        j = A.columns.index(col)
        A.rd["ref"] = np.nan_to_num(np.asarray(A.X[:, j], dtype=np.float32), nan=0.0)
    return A


def q_fold6(assets, eval_names, cols, geo, qc4, qcfg, actions, min_hold, seed, shaping, pause=None, where="", export=None):
    """One pooled shaped-reward Q model for one fold and seed. shaping: {"kind": "missed" | "flat", "values": [...]}.
    -> (W test per eval asset, record) as models4.q_fold. export: a dict, filled with the refit model itself exactly as
    models4.q_fold's hook (the forward paper book of Phase 6 needs it, engine15/rl/forward6.py); the computation is
    unchanged either way."""
    t0 = time.time()
    n = int(qcfg.get("n_step", 1))
    hls = list(qc4["half_life_days"])
    evals, every, patience = int(qc4["evals"]), int(qc4["eval_every"]), int(qc4["patience"])
    chunk = int(qcfg.get("chunk_steps", 500))
    F = len(cols)
    zeros, ones = np.zeros(F, np.float32), np.ones(F, np.float32)
    kind, values = shaping["kind"], [float(v) for v in shaping["values"]]
    for A in assets:
        add_reference(A)
    rec = {"seed": int(seed), "assets": {}, "grid": {}, "shaping": kind}
    from .pool4 import norm_stats
    stats = dict((A.name, norm_stats(A.X, geo[A.name]["lo"], geo[A.name]["val"], cols)) for A in assets)
    spans = dict((A.name, (geo[A.name]["lo"], geo[A.name]["te_lo"])) for A in assets)
    raw, rd, off = _concat(assets, cols, spans, stats)
    now = max(int(A.t[min(geo[A.name]["val"], A.n - 1)]) for A in assets)
    val_idx = np.concatenate([np.arange(geo[nm]["val"], geo[nm]["te_lo"] - n - 1) + off[nm] for nm in eval_names])
    best_v = None
    for v in values:
        best_h = None
        for h in hls:
            pool, p = _q_pool(assets, geo, off, "val", n, h, now)
            L = Learner6(F, actions, qcfg, seed, zeros, ones, kind, v)
            best, hist, bad = None, [], 0
            for c in range(evals):
                done = 0
                while done < every:
                    k = min(chunk, every - done)
                    L.train(raw, rd, pool, k, weights=p)
                    done += k
                    if pause is not None:
                        pause.check(where)
                vl = L.eval_loss(raw, rd, val_idx)
                hist.append({"check": c + 1, "steps": L.steps, "val_loss": round(vl, 6)})
                if best is None or vl < best[0] - 1e-12:
                    best, bad = (vl, L.steps, L.state()), 0
                else:
                    bad += 1
                    if bad >= patience:
                        break
            key = (round(best[0], 7), -(1e9 if not h else float(h)))
            if best_h is None or key < best_h[0]:
                best_h = (key, h, best, L)
            else:
                del L
        _, h_b, (vl, kept, state), L = best_h
        L.load_state(state)
        per = {}
        for name in eval_names:
            g = geo[name]
            o = off[name]
            Wv = L.w(raw[g["val"] + o:g["te_lo"] + o])
            per[name] = policy_metrics(Wv, rd, g["val"] + o, g["te_lo"] + o, actions, qcfg, min_hold)
        score = float(np.mean([per[nm]["sharpe"] for nm in eval_names]))
        rec["grid"][str(v)] = {"half_life_days": None if not h_b else float(h_b), "kept_steps": int(kept),
                               "val_loss": vl, "val_net_sharpe": score,
                               "val": dict((nm, _slim(per[nm])) for nm in eval_names)}
        if best_v is None or score > best_v[0] + 1e-12:
            best_v = (score, v, h_b, kept, vl, L, per)
        else:
            del L
    score, v_b, h_b, kept, vl, L, per = best_v
    rec["chosen"] = {"shaping_value": v_b, "half_life_days": None if not h_b else float(h_b), "kept_steps": int(kept),
                     "val_loss": vl, "val_net_sharpe": score}
    for name in eval_names:
        g = geo[name]
        o = off[name]
        Wt = L.w(raw[g["lo"] + o:g["val"] + o])
        tr = policy_metrics(Wt, rd, g["lo"] + o, g["val"] + o, actions, qcfg, min_hold)
        fb = qc4.get("fallback_val_sharpe")
        rec["assets"][name] = {"train": _slim(tr), "val": _slim(per[name]),
                               "fallback": bool(fb is not None and per[name]["sharpe"] < float(fb))}
    del raw, rd, L, best_v
    stats = dict((A.name, norm_stats(A.X, geo[A.name]["lo"], geo[A.name]["te_lo"], cols)) for A in assets)
    spans = dict((A.name, (geo[A.name]["lo"], geo[A.name]["te_hi"] if A.name in eval_names else geo[A.name]["te_lo"]))
                 for A in assets)
    raw, rd, off = _concat(assets, cols, spans, stats)
    now = max(int(A.t[min(geo[A.name]["te_lo"], A.n - 1)]) for A in assets)
    pool, p = _q_pool(assets, geo, off, "te_lo", n, h_b, now)
    L = Learner6(F, actions, qcfg, seed, zeros, ones, kind, v_b)
    done = 0
    while done < kept:
        k = min(chunk, kept - done)
        L.train(raw, rd, pool, k, weights=p)
        done += k
        if pause is not None:
            pause.check(where)
    out = {}
    for name in eval_names:
        g = geo[name]
        o = off[name]
        out[name] = L.w(raw[g["te_lo"] + o:g["te_hi"] + o]).astype(np.float32)
    w_lin = L.weights_np()
    rec["coef"] = [[float(x) for x in row] for row in w_lin[0][-1]]
    rec["bias"] = [float(x) for x in w_lin[1][-1]]
    rec["rows_refit"] = int(len(pool))
    rec["seconds"] = round(time.time() - t0, 1)
    if export is not None:
        export.update({"weights": [w.tolist() for w in w_lin[0]], "biases": [b.tolist() for b in w_lin[1]],
                       "stats": dict((nm, {"mu": st[0].tolist(), "sd": st[1].tolist()}) for nm, st in stats.items()),
                       "chosen": dict(rec["chosen"]), "grid": dict(rec["grid"]),
                       "fallback": dict((nm, rec["assets"][nm]["fallback"]) for nm in eval_names),
                       "val": dict((nm, rec["assets"][nm]["val"]) for nm in eval_names),
                       "train": dict((nm, rec["assets"][nm]["train"]) for nm in eval_names),
                       "steps": int(L.steps), "rows_refit": int(len(pool))})
    del raw, rd, L
    return out, rec
