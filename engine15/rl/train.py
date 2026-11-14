# -*- coding: utf-8 -*-
"""train -- walk-forward training harness for the PPO agent.

Per fold (Phase 1's walk-forward: 12-month train window, next 3 months test, roll 3 months):

    [ train slice: 9 months | validation: 3 months ][ test: 3 months ]
      PPO learns here         model choice only       touched ONCE, after training, never for choice

  * Features are z-scored with the TRAINING slice's mean/std only (saved with the model).
  * PPO trains on random 30-day episodes inside the training slice; every timesteps/evals steps the
    current policy is run deterministically over the validation slice (from flat, risk manager on,
    0.10% costs) and the checkpoint with the best validation Sharpe is kept (early stop after
    `patience` checks without improvement).
  * The kept policy is saved (research/out/rl/models/<config hash>/s<seed>_f<fold>.npz, ~20 KB) with
    its train and validation metrics. Nothing about the test window is looked at here.

Out of sample (evaluate_oos): ONE environment runs over the whole out-of-sample span, decision by
decision; at each decision bar the policy of the fold whose test window holds that bar acts (with
its own normaliser). Position, holding clock and the risk manager's state carry across windows,
exactly as live. The executed target series is then replayed through the shared backtester and
scored per window and stitched, like the benchmarks.
"""
import gc
import json
import os
import time

import numpy as np
import pandas as pd

from . import backtest, metrics, resources, walkforward
from .agent import NumpyPolicy, make_ppo, memory_guard
from .env import TradingEnv, frame_from_record, run_policy


def fold_bounds(index, w, val_months):
    s = lambda t: int(index.searchsorted(t))
    val_start = w["train_end"] - pd.DateOffset(months=int(val_months))
    return {"tr_lo": s(w["train_start"]), "val_lo": s(val_start), "tr_hi": s(w["train_end"]),
            "te_lo": s(w["test_start"]), "te_hi": s(w["test_end"])}


def eval_slice(market, pol, lo, hi, ecfg, rcfg):
    """Deterministic run of `pol` over bars [lo, hi), from flat, risk manager on -> metrics dict."""
    env = TradingEnv(market, lo, hi, (pol.mu, pol.sd), ecfg, rcfg, record=True)
    run_policy(env, pol.act)
    first = int(env.dec[0])
    fr = frame_from_record(env, first + 1, hi)
    out = metrics.summary(fr)
    out["min_hold_refusals"] = env.stats["min_hold_refusals"]
    out["risk_counts"] = dict(env.risk.counts) if env.risk else {}
    del env, fr
    return out


def _slim(m):
    keys = ("total_return", "sharpe", "sortino", "max_drawdown", "calmar", "turnover_per_year", "trades",
            "avg_holding_hours", "exposure", "cost_drag_per_year")
    return dict((k, m[k]) for k in keys if k in m)


def train_fold(market, b, seed, cfg, timesteps, log=print):
    """-> (NumpyPolicy, record). Raises resources.MemoryLow if the memory guard trips."""
    from stable_baselines3.common.vec_env import DummyVecEnv
    ecfg, rcfg, acfg, tcfg = cfg["env"], cfg["risk"], cfg["agent"], cfg["train"]
    t0 = time.time()
    mu, sd = market.fit_norm(b["tr_lo"], b["val_lo"])
    n_envs = int(acfg.get("n_envs", 4))

    def mk(i):
        return lambda: TradingEnv(market, b["tr_lo"], b["val_lo"], (mu, sd), ecfg, rcfg,
                                  episode_decisions=int(ecfg["episode_decisions"]), seed=int(seed) * 1000 + i,
                                  random_start_position=bool(ecfg.get("random_start_position", True)))
    venv = DummyVecEnv([mk(i) for i in range(n_envs)])
    model = make_ppo(venv, acfg, seed)
    guard = memory_guard(float(tcfg.get("memory_floor_mb", resources.FLOOR_MB)))
    evals = max(1, int(tcfg.get("evals", 5)))
    chunk = max(int(acfg["n_steps"]) * n_envs, int(timesteps) // evals)
    patience = int(tcfg.get("patience", 2))
    best, best_key, hist, bad = None, None, [], 0
    for c in range(evals):
        model.learn(chunk, reset_num_timesteps=(c == 0), callback=guard)
        if guard.tripped is not None:
            del model, venv
            gc.collect()
            raise resources.MemoryLow("free memory %.0f MB < floor during training" % guard.tripped)
        pol = NumpyPolicy.from_sb3(model, mu, sd)
        v = eval_slice(market, pol, b["val_lo"], b["tr_hi"], ecfg, rcfg)
        key = (round(v["sharpe"], 6), -v["trades"])
        hist.append({"check": c + 1, "timesteps": int(model.num_timesteps), "val": _slim(v)})
        if best_key is None or key > best_key:
            best, best_key, bad = pol, key, 0
            hist[-1]["kept"] = True
        else:
            bad += 1
            if bad >= patience:
                break
    steps = int(model.num_timesteps)
    del model, venv
    gc.collect()
    tr = eval_slice(market, best, b["tr_lo"], b["val_lo"], ecfg, rcfg)
    va = [h for h in hist if h.get("kept")][-1]["val"]
    rec = {"seed": int(seed), "timesteps_run": steps, "checks": hist, "train": _slim(tr), "val": va,
           "seconds": round(time.time() - t0, 1)}
    best.meta.update({"seed": int(seed), "kept_check": [h["check"] for h in hist if h.get("kept")][-1]})
    return best, rec


def evaluate_oos(market, pols, bounds, ecfg, rcfg, log_events=True):
    """pols[f] / bounds[f] per fold -> dict(target=Series over the full index (0 before the span),
    env_r_net=array, risk_events, risk_counts, min_hold_refusals)."""
    lo, hi = bounds[0]["te_lo"], bounds[-1]["te_hi"]
    te_lo = np.array([b["te_lo"] for b in bounds])

    def fold_of(i):
        return int(np.searchsorted(te_lo, i, side="right") - 1)

    env = TradingEnv(market, lo, hi, lambda i: (pols[fold_of(i)].mu, pols[fold_of(i)].sd), ecfg, rcfg,
                     record=True, log_risk_events=log_events)

    def act(obs):
        return pols[fold_of(int(env.dec[env.p]))].act(obs)
    run_policy(env, act)
    tgt = np.nan_to_num(env.tgt_rec, nan=0.0)
    tgt[:lo] = 0.0
    out = {"target": pd.Series(tgt, index=market.index), "env_r_net": env.r_net.copy(),
           "risk_events": list(env.risk.events) if env.risk else [],
           "risk_counts": dict(env.risk.counts) if env.risk else {},
           "min_hold_refusals": env.stats["min_hold_refusals"], "span": (lo, hi)}
    del env
    return out


def constant_oos(market, bounds, ecfg, rcfg, action_index):
    """A constant request (e.g. always long) through the same env + risk manager: a reference for
    how much the risk manager alone changes buy-and-hold."""
    nf = market.raw.shape[1]
    lo, hi = bounds[0]["te_lo"], bounds[-1]["te_hi"]
    env = TradingEnv(market, lo, hi, (np.zeros(nf, np.float32), np.ones(nf, np.float32)), ecfg, rcfg,
                     record=True, log_risk_events=False)
    run_policy(env, lambda obs: action_index)
    tgt = np.nan_to_num(env.tgt_rec, nan=0.0)
    tgt[:lo] = 0.0
    counts = dict(env.risk.counts) if env.risk else {}
    del env
    return pd.Series(tgt, index=market.index), counts


def backtest_eval(bars, target, model, funding, wins):
    bt = backtest.run(bars, target, model, funding)
    ev = walkforward.evaluate(bt["frame"], wins)
    r_net = bt["frame"]["r_net"].values.copy()
    del bt
    return ev, r_net
