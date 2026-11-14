# -*- coding: utf-8 -*-
"""diag2 -- DIAGNOSTIC ONLY (not a result): what the Phase 3 filters / harnesses would have done to the Phase 2
PPO agent's out-of-sample trades. It replays Phase 2's saved models on Phase 2's test windows, which have already
been looked at, so nothing here is out-of-sample evidence; it only shows whether filtering a no-edge agent can
help at all. Thresholds are fixed in configs/rl/phase3.yaml (diag2 section) and are not tuned here.

Phase 2 targets are replayed WITHOUT Phase 2's risk manager (minimum hold kept), then each filter is applied to
the target series bar by bar, then the shared backtester scores it at both fees:
  consensus   all seeds' targets on the same side -> that side; all flat -> flat; otherwise hold the last
  confidence  a new target is accepted only if PPO's probability of the chosen action >= prob_min; else hold
  htf         a long only if trend_4h > 0 and the momentum signal is long; a short only if both are short; else flat
  vol_gate    a change only when vol x sqrt(H) >= M x round-trip cost; else hold
  meta_label  direction = the momentum signal; in (1x) only when PPO is on the same side, else flat
  core_sat    1 + 0.5 x PPO target (0.5x .. 1.5x of buy-and-hold)
"""
import gc
import os

import numpy as np
import pandas as pd

from . import backtest, config, costs, data, features, features3, train, walkforward
from .config import resolve
from .env import Market, TradingEnv, run_policy


def phase2_targets(log=print, offline=True):
    cfg = config.load_phase2()
    bars, fund, _ = data.update_all(cfg, log=None, offline=offline)
    feats = features.build(bars, fund, cfg["env"]["features"]).astype("float32")
    model = costs.from_cfg(cfg)
    m = Market(bars, fund, feats, model)
    del feats
    wf = cfg["walkforward"]
    wins = walkforward.windows(bars.index, wf["train_months"], wf["test_months"], wf["step_months"], wf["start"],
                               wf["min_test_days"])
    bounds = [train.fold_bounds(bars.index, w, cfg["train"]["validation_months"]) for w in wins]
    wh = "9ae64989"
    mdir = os.path.join(resolve(cfg["report"]["models_dir"]), wh)
    seeds = cfg["seeds"]
    lo, hi = bounds[0]["te_lo"], bounds[-1]["te_hi"]
    te_lo = np.array([b["te_lo"] for b in bounds])
    out = {}
    for s in seeds:
        pols = [train.NumpyPolicy.load(os.path.join(mdir, "s%d_f%02d.npz" % (s, f))) for f in range(len(wins))]
        fold_of = lambda i: int(np.searchsorted(te_lo, i, side="right") - 1)
        env = TradingEnv(m, lo, hi, lambda i: (pols[fold_of(i)].mu, pols[fold_of(i)].sd), cfg["env"], None, record=True)
        prob = np.full(m.n, np.nan)

        def act(obs):
            i = int(env.dec[env.p])
            lg = pols[fold_of(i)].logits(obs)
            e = np.exp(lg - lg.max())
            a = int(np.argmax(lg))
            prob[i] = e[a] / e.sum()
            return a
        run_policy(env, act)
        t = np.nan_to_num(env.tgt_rec, nan=0.0)
        t[:lo] = 0.0
        out[s] = {"target": t, "prob": prob}
        log("phase 2 replay seed %d done" % s)
        del env
        gc.collect()
    return {"cfg": cfg, "bars": bars, "fund": fund, "wins": wins, "span": (lo, hi), "seeds": seeds, "agents": out}


def apply_filters(rep, dcfg, c3):
    """-> {filter name: [target series per seed] or one series (consensus)}."""
    bars, fund = rep["bars"], rep["fund"]
    lo, hi = rep["span"]
    f3 = features3.build(bars, fund, c3["features"])
    trend4 = np.sign(np.nan_to_num(f3["trend_4h"].values))
    mom = f3["mom_signal"].values
    model = costs.from_cfg(rep["cfg"])
    vol = model.bar_vol(bars)
    c1 = model.fee_side + model.half_spread_bps * 1e-4 + model.slippage_coef * vol
    gate = vol * np.sqrt(float(dcfg["vol_gate_hold_bars"])) >= float(dcfg["vol_gate_mult"]) * 2.0 * c1
    seeds = rep["seeds"]
    T = {s: rep["agents"][s]["target"] for s in seeds}
    P = {s: rep["agents"][s]["prob"] for s in seeds}
    res = {"unfiltered": [T[s] for s in seeds]}

    def hold_filter(t, ok):
        out = t.copy()
        cur = 0.0
        for i in range(lo, hi):
            if ok[i]:
                cur = t[i]
            out[i] = cur
        return out
    # decisions are hourly; between decisions the raw target is unchanged, so 'hold the last accepted' is exact
    res["confidence"] = [hold_filter(T[s], np.nan_to_num(P[s], nan=0.0) >= float(dcfg["prob_min"])) for s in seeds]
    res["htf"] = [np.where((np.sign(T[s]) == 0) | ((np.sign(T[s]) == trend4) & (np.sign(T[s]) == mom)), T[s], 0.0) for s in seeds]
    res["vol_gate"] = [hold_filter(T[s], gate) for s in seeds]
    res["meta_label"] = [np.where(np.sign(T[s]) == mom, mom, 0.0) for s in seeds]
    res["core_sat"] = [np.where(np.arange(len(T[s])) >= lo, 1.0 + 0.5 * T[s], 0.0) for s in seeds]
    stack = np.stack([np.sign(T[s]) for s in seeds])
    allp, alln, allz = (stack > 0).all(0), (stack < 0).all(0), (stack == 0).all(0)
    cons = np.zeros(len(bars))
    cur = 0.0
    for i in range(lo, hi):
        if allp[i]:
            cur = 1.0
        elif alln[i]:
            cur = -1.0
        elif allz[i]:
            cur = 0.0
        cons[i] = cur
    res["consensus"] = [cons]
    for k in res:
        for t in res[k]:
            t[:lo] = 0.0
    return res


def score(rep, res):
    bars, fund, wins = rep["bars"], rep["fund"], rep["wins"]
    out = {}
    for pname, model in costs.fee_profiles(rep["cfg"]).items():
        o = {}
        for k, lst in res.items():
            sts = []
            for t in lst:
                bt = backtest.run(bars, t, model, fund, max_abs=1.5 if k == "core_sat" else 1.0)
                ev = walkforward.evaluate(bt["frame"], wins)["stitched"]
                from .phase3 import break_even_fee
                om = walkforward.oos_mask(bars.index, wins)
                ev["break_even_fee"] = break_even_fee(bt["frame"][om])
                sts.append(ev)
                del bt
            o[k] = sts
        out[pname] = o
    return out
