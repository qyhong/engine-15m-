# -*- coding: utf-8 -*-
"""models4 -- the two Phase 4 model families, both linear and regularised, trained on more data per model.

Both fit one model per walk-forward fold on every row available before the fold (expanding window, or Phase 3's 12-month
window for the ablations), pooled across assets (inputs z-scored per asset on that asset's own training rows), choose
their recency half-life (and the ridge penalty) on a validation slice only, then REFIT on everything up to the fold's
first test bar with the chosen settings. A fold whose validation-stage model nets a Sharpe under the 'do no harm' bar on
an asset's validation slice acts neutral (flat) on that asset for the fold (Phase 3's rule).

SP  supervised-then-policy (sp_fit / sp_fold): weighted ridge regression of the vol-scaled forward return over the next
    H bars, y[t] = sum_{j<H} k[t+j] g[t+j] (qagent.py's units: g = next-bar open-to-open return net of funding, k = the
    vol-target scale), on the inputs; seeds = block-bootstrap resamples of the training rows (1-week blocks). The policy
    is Phase 3's: W(x, a) = scale x (a x pred - risk_aversion x a^2 x H x v), Q = W - round-trip cost x |a - p| (qagent.
    q_from_w), decided by policy3.decide (hold by default, minimum hold). The penalty and half-life are chosen on the
    validation slice by R2 against a zero forecast (scale-aware: the policy compares the prediction's size with the cost;
    the draft's information coefficient picked over-shrunk models that never traded), not by a validation Sharpe; no
    intercept by default (spc['intercept']), so no constant drift bet.
Q   the Phase 3 afterstate Q-learner (qagent.Learner: linear W, n-step double-Q, hard-wired round-trip cost) unchanged,
    fed pooled rows: the training pool is the union of every asset's rows, sampled with recency weights; early stopping
    and the half-life choice on the validation Bellman loss; refit = a fresh learner (same seed) trained for the kept
    number of steps on all rows up to the fold.
"""
import time

import numpy as np

from . import metrics, policy3
from .pool4 import bootstrap_counts, norm_stats, normalised, recency
from .qagent import Learner, cost_matrix, q_from_w

Y = 35040


# ---------------------------------------------------------------- shared
def rd_slice(rd, lo, hi):
    return dict((k, np.asarray(v[lo:hi], dtype=np.float32)) for k, v in rd.items())


def rd_net(rd, tgt, lo, hi, start_pos=0.0):
    """Net per-bar returns of targets decided at bars lo .. hi-1 (held over the next bar): the backtester's formula on
    the reward arrays (a x g - c1 x |change|), exactly policy3.fast_net for the asset's own cost model."""
    a = np.asarray(tgt, dtype=float)
    prev = np.concatenate([[start_pos], a[:-1]])
    g = np.asarray(rd["g"][lo:hi], dtype=float)
    c1 = np.asarray(rd["c1"][lo:hi], dtype=float)
    return a * g - c1 * np.abs(a - prev), a * np.asarray(rd["rpx"][lo:hi], dtype=float)


def policy_metrics(W, rd, lo, hi, actions, qcfg, min_hold):
    """W (hi-lo, A) -> greedy Phase 3 policy from flat -> quick metrics (net of the asset's cost model)."""
    acts = np.asarray(actions, dtype=float)
    Q = q_from_w(np.asarray(W, np.float32), rd["k"][lo:hi], rd["c1"][lo:hi], cost_matrix(acts), qcfg)
    ip, st = policy3.decide(Q, acts, int(np.argmin(np.abs(acts))), int(min_hold))
    tgt = acts[ip]
    r, g = rd_net(rd, tgt, lo, hi)
    out = policy3.quick_metrics(r, tgt)
    out["gross_sharpe"] = metrics.sharpe(g)
    out["changes"] = st["changes"]
    return out


def sp_target(rd, H):
    """y[t] = sum_{j<H} k[t+j] g[t+j] (NaN where the window runs past the data)."""
    kg = np.asarray(rd["k"], dtype=np.float64) * np.asarray(rd["g"], dtype=np.float64)
    c = np.concatenate([[0.0], np.cumsum(kg)])
    n = len(kg)
    y = np.full(n, np.nan)
    m = n - H
    if m > 0:
        y[:m] = c[H:H + m] - c[:m]
    return y


def sp_w(pred, v, actions, qcfg, H):
    """Afterstate values of the SP policy: scale x (a x pred - risk_aversion x a^2 x H x v)."""
    a = np.asarray(actions, dtype=np.float64)[None, :]
    sc, ra = float(qcfg["reward_scale"]), float(qcfg.get("risk_aversion", 0.0))
    p = np.asarray(pred, dtype=np.float64)[:, None]
    vv = np.asarray(v, dtype=np.float64)[:, None]
    return (sc * (a * p - ra * a * a * H * vv)).astype(np.float32)


# ---------------------------------------------------------------- SP: weighted ridge
class Gram:
    """Accumulates sum w x x', sum w x y, sum w, sum w y over chunks (float64), x with an intercept column."""

    def __init__(self, F):
        self.G = np.zeros((F + 1, F + 1))
        self.b = np.zeros(F + 1)
        self.sw = 0.0
        self.rows = 0

    def add(self, x, y, w):
        ok = np.isfinite(y) & (w > 0)
        if not ok.any():
            return
        x1 = np.empty((int(ok.sum()), x.shape[1] + 1))
        x1[:, :-1] = x[ok]
        x1[:, -1] = 1.0
        ww = w[ok]
        self.G += x1.T @ (x1 * ww[:, None])
        self.b += x1.T @ (ww * y[ok])
        self.sw += float(ww.sum())
        self.rows += int(ok.sum())

    def solve(self, alpha, intercept=True):
        """Ridge, penalty alpha x sum(w) on every slope (inputs are z-scored). intercept=True: an unpenalised intercept;
        False: none (the prediction is the inputs' contribution only, so no constant drift bet)."""
        F = self.G.shape[0] - 1
        if self.sw <= 0:
            return np.zeros(F), 0.0
        if not intercept:
            beta = np.linalg.solve(self.G[:-1, :-1] + float(alpha) * self.sw * np.eye(F), self.b[:-1])
            return beta, 0.0
        mean = self.G[-1, :-1] / self.sw
        ybar = self.b[-1] / self.sw
        Gc = self.G[:-1, :-1] - self.sw * np.outer(mean, mean)
        bc = self.b[:-1] - self.sw * mean * ybar
        beta = np.linalg.solve(Gc + float(alpha) * self.sw * np.eye(F), bc)
        return beta, float(ybar - mean @ beta)


def _stage_rows(A, lo, boundary, H):
    """Training rows of asset A for a model used from bar `boundary` on: [lo, boundary - H - 1)."""
    return lo, max(lo, boundary - H - 1)


def sp_fold(assets, eval_names, cols, geo, spc, qcfg, actions, min_hold, seed, pause=None, where=""):
    """One SP model for one fold and seed. geo: {asset: {"lo", "val", "te_lo", "te_hi"}} (bar indices; val = selection
    boundary). -> (W test per eval asset {name: (te_hi-te_lo, A)}, record)."""
    t0 = time.time()
    H = int(spc["horizon_bars"])
    alphas = [float(a) for a in spc["alphas"]]
    hls = list(spc["half_life_days"])
    block = int(spc["bootstrap_block_bars"])
    rng = np.random.default_rng(int(seed))
    F = len(cols)
    rec = {"seed": int(seed), "assets": {}, "rows_select": 0, "rows_refit": 0}
    # ---- selection stage: fit on rows before each asset's validation start, one Gram per half-life
    grams = dict((str(h), Gram(F)) for h in hls)
    stats_sel = {}
    sel_now = max(int(A.t[min(geo[A.name]["val"], A.n - 1)]) for A in assets)
    for A in assets:
        g = geo[A.name]
        lo, hi = _stage_rows(A, g["lo"], g["val"], H)
        mu, sd = norm_stats(A.X, g["lo"], g["val"], cols)
        stats_sel[A.name] = (mu, sd)
        if hi <= lo:
            continue
        y = sp_target(A.rd, H)[lo:hi]
        boot = bootstrap_counts(hi - lo, block, rng)
        for a0 in range(lo, hi, 60000):
            a1 = min(hi, a0 + 60000)
            x = normalised(A.X, a0, a1, cols, mu, sd).astype(np.float64)
            for h in hls:
                w = recency(A.t[a0:a1], sel_now, h) * boot[a0 - lo:a1 - lo]
                grams[str(h)].add(x, y[a0 - lo:a1 - lo], w)
            del x
        if pause is not None:
            pause.check(where)
    rec["rows_select"] = grams[str(hls[0])].rows
    icpt = bool(spc.get("intercept", True))
    fits = dict(((str(h), al), grams[str(h)].solve(al, icpt)) for h in hls for al in alphas)
    # ---- validation IC per combination (eval assets), then the policy check of the chosen one
    ics = dict((k, []) for k in fits)
    valx = {}
    for name in eval_names:
        A = [x for x in assets if x.name == name][0]
        g = geo[name]
        mu, sd = stats_sel[name]
        x = normalised(A.X, g["val"], g["te_lo"], cols, mu, sd).astype(np.float64)
        valx[name] = x
        y = sp_target(A.rd, H)[g["val"]:g["te_lo"]]
        ok = np.isfinite(y)
        ok[max(0, g["te_lo"] - H - 1 - g["val"]):] = False            # only targets complete before the test window
        for k, (beta, b0) in fits.items():
            p = x @ beta + b0
            if spc.get("select_on", "val_ic") == "val_r2":       # scale-aware: 1 - SSE / sum y^2 (vs a zero forecast)
                c = 1.0 - float(np.sum((y[ok] - p[ok]) ** 2)) / max(float(np.sum(y[ok] ** 2)), 1e-18) if ok.sum() > 10 else 0.0
            else:
                c = np.corrcoef(p[ok], y[ok])[0, 1] if ok.sum() > 10 and np.std(p[ok]) > 0 else 0.0
            ics[k].append(float(c) if np.isfinite(c) else 0.0)
    mean_ic = dict((k, float(np.mean(v)) if v else 0.0) for k, v in ics.items())
    # best IC; ties -> the larger penalty, then the longer half-life (None = no recency = longest)
    hl_rank = dict((str(h), (1e9 if not h else float(h))) for h in hls)
    best = max(mean_ic, key=lambda k: (round(mean_ic[k], 6), k[1], hl_rank[k[0]]))
    rec["chosen"] = {"half_life_days": None if best[0] == "None" else float(best[0]), "alpha": best[1],
                     "val_score": mean_ic[best], "select_on": spc.get("select_on", "val_ic")}
    rec["val_score_grid"] = dict(("hl=%s,alpha=%g" % k, round(v, 6)) for k, v in mean_ic.items())
    beta, b0 = fits[best]
    for name in eval_names:
        A = [x for x in assets if x.name == name][0]
        g = geo[name]
        mu, sd = stats_sel[name]
        pv = valx[name] @ beta + b0
        va = policy_metrics(sp_w(pv, A.rd["v"][g["val"]:g["te_lo"]], actions, qcfg, H), A.rd, g["val"], g["te_lo"],
                            actions, qcfg, min_hold)
        lo, hi = g["lo"], g["val"]
        tr_lo = max(lo, hi - int(spc.get("train_sharpe_bars", 10 ** 9)))
        xt = normalised(A.X, tr_lo, hi, cols, mu, sd).astype(np.float64)
        tr = policy_metrics(sp_w(xt @ beta + b0, A.rd["v"][tr_lo:hi], actions, qcfg, H), A.rd, tr_lo, hi, actions, qcfg,
                            min_hold)
        del xt
        fb = spc.get("fallback_val_sharpe")
        rec["assets"][name] = {"train": _slim(tr), "val": _slim(va),
                               "fallback": bool(fb is not None and va["sharpe"] < float(fb))}
    del valx, grams, fits
    # ---- refit on everything up to the fold with the chosen settings
    h_best = rec["chosen"]["half_life_days"]
    gram = Gram(F)
    stats_ref = {}
    ref_now = max(int(A.t[min(geo[A.name]["te_lo"], A.n - 1)]) for A in assets)
    for A in assets:
        g = geo[A.name]
        lo, hi = _stage_rows(A, g["lo"], g["te_lo"], H)
        mu, sd = norm_stats(A.X, g["lo"], g["te_lo"], cols)
        stats_ref[A.name] = (mu, sd)
        if hi <= lo:
            continue
        y = sp_target(A.rd, H)[lo:hi]
        boot = bootstrap_counts(hi - lo, block, rng)
        for a0 in range(lo, hi, 60000):
            a1 = min(hi, a0 + 60000)
            x = normalised(A.X, a0, a1, cols, mu, sd).astype(np.float64)
            gram.add(x, y[a0 - lo:a1 - lo], recency(A.t[a0:a1], ref_now, h_best) * boot[a0 - lo:a1 - lo])
            del x
        if pause is not None:
            pause.check(where)
    rec["rows_refit"] = gram.rows
    beta, b0 = gram.solve(rec["chosen"]["alpha"], icpt)
    rec["coef"] = [float(x) for x in beta]
    rec["intercept"] = b0
    out = {}
    for name in eval_names:
        A = [x for x in assets if x.name == name][0]
        g = geo[name]
        mu, sd = stats_ref[name]
        x = normalised(A.X, g["te_lo"], g["te_hi"], cols, mu, sd).astype(np.float64)
        out[name] = sp_w(x @ beta + b0, A.rd["v"][g["te_lo"]:g["te_hi"]], actions, qcfg, H)
    rec["seconds"] = round(time.time() - t0, 1)
    return out, rec


def _slim(m):
    keys = ("sharpe", "gross_sharpe", "total_return", "max_drawdown", "turnover_per_year", "trades", "exposure")
    return dict((k, (round(float(m[k]), 4) if isinstance(m.get(k), (float, np.floating)) else m.get(k))) for k in keys)


# ---------------------------------------------------------------- Q: the Phase 3 learner on pooled rows
def _concat(assets, cols, spans, stats):
    """spans {name: (lo, hi)} -> (raw (N, F) float32 normalised per asset, rd concat, offsets {name: offset - lo})."""
    parts, rds, off, pos = [], [], {}, 0
    for A in assets:
        lo, hi = spans[A.name]
        mu, sd = stats[A.name]
        parts.append(normalised(A.X, lo, hi, cols, mu, sd))
        rds.append(rd_slice(A.rd, lo, hi))
        off[A.name] = pos - lo
        pos += hi - lo
    raw = np.ascontiguousarray(np.concatenate(parts)) if parts else np.zeros((0, len(cols)), np.float32)
    rd = dict((k, np.concatenate([r[k] for r in rds])) for k in rds[0])
    return raw, rd, off


def _q_pool(assets, geo, off, boundary_key, n, weights_hl, now_ms):
    idx, tt = [], []
    for A in assets:
        g = geo[A.name]
        lo, hi = g["lo"], g[boundary_key] - n - 1
        if hi > lo:
            idx.append(np.arange(lo, hi) + off[A.name])
            tt.append(A.t[lo:hi])
    pool = np.concatenate(idx)
    w = recency(np.concatenate(tt), now_ms, weights_hl)
    p = None if not weights_hl else w / w.sum()
    return pool, p


def q_fold(assets, eval_names, cols, geo, qc4, qcfg, actions, min_hold, seed, pause=None, where="", export=None):
    """One pooled Q model for one fold and seed (see the module docstring). -> (W test per eval asset, record).
    export: a dict, filled with the refit model itself (Phase 5's forward paper run needs it): linear weights and
    bias, the per-asset z-score stats of the refit rows, the chosen settings and the 'do no harm' flags. Phase 4
    passes nothing; the computation is unchanged either way."""
    t0 = time.time()
    n = int(qcfg.get("n_step", 1))
    hls = list(qc4["half_life_days"])
    evals, every, patience = int(qc4["evals"]), int(qc4["eval_every"]), int(qc4["patience"])
    chunk = int(qcfg.get("chunk_steps", 500))
    F = len(cols)
    zeros, ones = np.zeros(F, np.float32), np.ones(F, np.float32)
    rec = {"seed": int(seed), "assets": {}, "hl": {}}
    # ---- selection stage
    stats = dict((A.name, norm_stats(A.X, geo[A.name]["lo"], geo[A.name]["val"], cols)) for A in assets)
    spans = dict((A.name, (geo[A.name]["lo"], geo[A.name]["te_lo"])) for A in assets)
    raw, rd, off = _concat(assets, cols, spans, stats)
    now = max(int(A.t[min(geo[A.name]["val"], A.n - 1)]) for A in assets)
    val_idx = np.concatenate([np.arange(geo[nm]["val"], geo[nm]["te_lo"] - n - 1) + off[nm] for nm in eval_names])
    best_all = None
    for h in hls:
        pool, p = _q_pool(assets, geo, off, "val", n, h, now)
        L = Learner(F, actions, qcfg, seed, zeros, ones)
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
        rec["hl"][str(h)] = {"val_loss": round(best[0], 6), "kept_steps": best[1], "checks": hist}
        key = (round(best[0], 7), -(1e9 if not h else float(h)))
        if best_all is None or key < best_all[0]:
            best_all = (key, h, best, L)
        else:
            del L
    _, h_best, (vl, kept, state), L = best_all
    L.load_state(state)
    rec["chosen"] = {"half_life_days": None if not h_best else float(h_best), "kept_steps": int(kept), "val_loss": vl}
    for name in eval_names:
        g = geo[name]
        o = off[name]
        Wv = L.w(raw[g["val"] + o:g["te_lo"] + o])
        va = policy_metrics(Wv, rd, g["val"] + o, g["te_lo"] + o, actions, qcfg, min_hold)
        Wt = L.w(raw[g["lo"] + o:g["val"] + o])
        tr = policy_metrics(Wt, rd, g["lo"] + o, g["val"] + o, actions, qcfg, min_hold)
        fb = qc4.get("fallback_val_sharpe")
        rec["assets"][name] = {"train": _slim(tr), "val": _slim(va),
                               "fallback": bool(fb is not None and va["sharpe"] < float(fb))}
    del raw, rd, L, best_all
    # ---- refit: fresh learner, kept steps, all rows up to the fold
    stats = dict((A.name, norm_stats(A.X, geo[A.name]["lo"], geo[A.name]["te_lo"], cols)) for A in assets)
    spans = dict((A.name, (geo[A.name]["lo"], geo[A.name]["te_hi"] if A.name in eval_names else geo[A.name]["te_lo"]))
                 for A in assets)
    raw, rd, off = _concat(assets, cols, spans, stats)
    now = max(int(A.t[min(geo[A.name]["te_lo"], A.n - 1)]) for A in assets)
    pool, p = _q_pool(assets, geo, off, "te_lo", n, h_best, now)
    L = Learner(F, actions, qcfg, seed, zeros, ones)
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
    rec["coef"] = [[float(v) for v in row] for row in w_lin[0][-1]]
    rec["rows_refit"] = int(len(pool))
    rec["seconds"] = round(time.time() - t0, 1)
    if export is not None:
        export.update({"weights": [w.tolist() for w in w_lin[0]], "biases": [b.tolist() for b in w_lin[1]],
                       "stats": dict((nm, {"mu": st[0].tolist(), "sd": st[1].tolist()}) for nm, st in stats.items()),
                       "chosen": dict(rec["chosen"]), "fallback": dict((nm, rec["assets"][nm]["fallback"]) for nm in eval_names),
                       "val": dict((nm, rec["assets"][nm]["val"]) for nm in eval_names),
                       "train": dict((nm, rec["assets"][nm]["train"]) for nm in eval_names),
                       "steps": int(L.steps), "rows_refit": int(len(pool))})
    del raw, rd, L
    return out, rec
