# -*- coding: utf-8 -*-
"""learncheck -- Phase 3 step 1: can the agent and its training setup find a planted edge after costs, stay
(near) flat when there is none, and fit its own training slice? Synthetic data only; cheap.

Each scenario is a 2-year synthetic 15m series (synth.py): months 1-9 train, 10-12 validation (early stopping,
exactly as on real data), months 13-24 a held-out synthetic test. The agent is the frozen Phase 3 Q agent with
the frozen features (features3 + the planted column). Scenarios:
  edge       kappa = planted edge (realistic: a cost-aware oracle nets Sharpe ~1 at 0.10%; naive trading loses)
  none       kappa = 0 (the planted column is noise)
  drift      the edge flips sign at random (mean flip_days apart): static vs continual fine-tuning (cadences)
PPO reference: Phase 2's algorithm (Stable-Baselines3 PPO) on the same reward and observations (env3.py).
"""
import time

import numpy as np
import pandas as pd

from . import continual, features3, policy3, qagent, synth
from .costs import CostModel
from .env import Market

Y = 35040
M = Y // 12


def scenario_market(n, seed, kappa, flip_days=None, cost=None, fcfg=None):
    bars, fund, pl, info = synth.make(n, seed, kappa, flip_days=flip_days)
    f = features3.build(bars, fund, fcfg)
    f["planted"] = pl
    m = Market(bars, fund, f.astype("float32"), cost or CostModel())
    return m, pl, info


def bounds(train_months=9, val_months=3, warm=30 * 96):
    return {"tr_lo": warm, "val_lo": train_months * M, "tr_hi": (train_months + val_months) * M}


def test_metrics(market, Q, lo, hi, actions, pcfg, masks=None):
    return continual.eval_q(market, Q, lo, hi, actions, pcfg, masks)


def oracle(market, pl, b, lo, hi, regime=None):
    """Oracle hysteresis threshold chosen on the training part, scored on [lo, hi)."""
    best = None
    for h in (0.5, 1.0, 1.5, 2.0):
        t = synth.oracle_targets(pl, h, regime=regime)
        r, _, pos = policy3.fast_net(market, t[b["tr_lo"]:b["tr_hi"]], b["tr_lo"], b["tr_hi"])
        s = policy3.quick_metrics(r, pos)["sharpe"]
        if best is None or s > best[0]:
            best = (s, h)
    t = synth.oracle_targets(pl, best[1], regime=regime)
    r, g, pos = policy3.fast_net(market, t[lo:hi], lo, hi)
    out = policy3.quick_metrics(r, pos)
    out["h"] = best[1]
    return out


def _slim(m):
    return dict((k, (round(v, 4) if isinstance(v, float) else v)) for k, v in m.items())


def planted_corr(market, Q, lo, hi, actions, pcfg, pl):
    acts = np.asarray(actions, float)
    ip, _ = policy3.decide(Q, acts, int(np.argmin(np.abs(acts))), int(pcfg.get("min_hold_bars", 0)))
    pos = acts[ip]
    return float(np.corrcoef(pos, pl[lo:hi])[0, 1]) if np.std(pos) > 0 else 0.0


def run_q(scen, seeds, qcfg, pcfg, actions, train_months=9, log=print, cadences=(), flip_days=None, kappa=0.0,
          test_months=12, seed_base=1000):
    """Q agent on a scenario. -> dict per seed: train / val / test metrics (+ continual variants for drift)."""
    out = []
    n_years = (train_months + 3 + test_months) / 12.0
    for s in seeds:
        t0 = time.time()
        m, pl, info = scenario_market(int(n_years * Y), seed_base + s, kappa, flip_days)
        rd = qagent.reward_arrays(m, qcfg)
        b = bounds(train_months)
        L, rec = continual.full_train(m, rd, b, qcfg, pcfg, actions, s)
        lo, hi = b["tr_hi"], int(n_years * Y)
        st0 = L.state()
        neutral = rec["fallback"]                       # 'do no harm': the whole test year acts neutral
        Qs = (continual.q_of(continual.neutral_w(hi - lo, actions, qcfg.get("neutral_action", 0.0)), rd, lo, hi, qcfg, actions)
              if neutral else L.q(m.raw, rd, lo, hi))
        row = {"seed": s, "train": _slim(rec["train"]), "val": _slim(rec["val"]), "kept_check": rec["kept_check"],
               "test_static": _slim(test_metrics(m, Qs, lo, hi, actions, pcfg)),
               "oracle_test": _slim(oracle(m, pl, b, lo, hi, info["regime"] if flip_days else None)),
               "corr_with_planted": round(planted_corr(m, Qs, lo, hi, actions, pcfg, pl * info["regime"]), 3)}
        for cd in cadences:
            L.load_state(st0)
            Wc, _ = continual.run_span(L, m, rd, lo, hi, qcfg, cadence_days=cd)
            if neutral:
                Wc = continual.neutral_w(hi - lo, actions, qcfg.get("neutral_action", 0.0))
            Qc = continual.q_of(Wc, rd, lo, hi, qcfg, actions)
            row["test_continual_%dd" % cd] = _slim(test_metrics(m, Qc, lo, hi, actions, pcfg))
        row["seconds"] = round(time.time() - t0, 1)
        out.append(row)
        log("  %s seed %d: train Sharpe %+.2f, val %+.2f, test %+.2f (turnover %.0f/yr, exposure %.0f%%, corr %.2f), oracle %+.2f%s  [%.0fs]"
            % (scen, s, rec["train"]["sharpe"], rec["val"]["sharpe"], row["test_static"]["sharpe"],
               row["test_static"]["turnover_per_year"], 100 * row["test_static"]["exposure"], row["corr_with_planted"],
               row["oracle_test"]["sharpe"], "".join(", %s %+.2f" % (k.replace("test_", ""), row[k]["sharpe"]) for k in row if k.startswith("test_continual")),
               row["seconds"]))
    return out


def summarise(rows, key="test_static"):
    sh = [r[key]["sharpe"] for r in rows]
    return {"sharpe_mean": float(np.mean(sh)), "sharpe_by_seed": [round(x, 3) for x in sh],
            "turnover_mean": float(np.mean([r[key]["turnover_per_year"] for r in rows])),
            "exposure_mean": float(np.mean([r[key]["exposure"] for r in rows])),
            "train_sharpe_mean": float(np.mean([r["train"]["sharpe"] for r in rows])),
            "oracle_sharpe_mean": float(np.mean([r["oracle_test"]["sharpe"] for r in rows]))}


def cost_drag(market, Q, lo, hi, actions, pcfg):
    acts = np.asarray(actions, float)
    ip, _ = policy3.decide(Q, acts, int(np.argmin(np.abs(acts))), int(pcfg.get("min_hold_bars", 0)))
    t = acts[ip]
    r, g, pos = policy3.fast_net(market, t, lo, hi)
    return float((g - r).sum() / ((hi - lo) / Y))


def run_ppo(scen, seeds, acfg, qcfg, pcfg, actions, timesteps, n_years=2, kappa=0.0, log=print, episode_bars=2048,
            seed_base=1000):
    """Phase 2's algorithm (SB3 PPO, Phase 2 hyperparameters) on the same reward / observations (env3.Env3).
    No validation choice: the final policy is scored (PPO's Phase 2 early stopping kept mostly the first check)."""
    from stable_baselines3.common.vec_env import DummyVecEnv
    from . import agent, env3
    out = []
    for s in seeds:
        t0 = time.time()
        m, pl, info = scenario_market(n_years * Y, seed_base + s, kappa)
        rd = qagent.reward_arrays(m, qcfg)
        b = bounds()
        mu, sd = m.fit_norm(b["tr_lo"], b["tr_hi"])
        A = len(actions)
        mk = lambda i: (lambda: env3.Env3(m.raw, rd, b["tr_lo"], b["val_lo"], mu, sd, actions, qcfg,
                                          int(pcfg.get("min_hold_bars", 0)), episode_bars, seed=s * 100 + i))
        venv = DummyVecEnv([mk(i) for i in range(int(acfg.get("n_envs", 4)))])
        model = agent.make_ppo(venv, acfg, s)
        model.learn(int(timesteps))
        pol = agent.NumpyPolicy.from_sb3(model, mu, sd)
        del model, venv
        lo, hi = b["tr_hi"], n_years * Y
        tr = test_metrics(m, env3.logits_all(pol, m.raw[b["tr_lo"]:b["val_lo"]], A), b["tr_lo"], b["val_lo"], actions, pcfg)
        Qt = env3.logits_all(pol, m.raw[lo:hi], A)
        te = test_metrics(m, Qt, lo, hi, actions, pcfg)
        row = {"seed": s, "train": _slim(tr), "test_static": _slim(te),
               "oracle_test": _slim(oracle(m, pl, b, lo, hi)), "seconds": round(time.time() - t0, 1),
               "corr_with_planted": round(planted_corr(m, Qt, lo, hi, actions, pcfg, pl), 3)}
        out.append(row)
        log("  PPO %s seed %d: train Sharpe %+.2f, test %+.2f (turnover %.0f/yr, exposure %.0f%%), oracle %+.2f  [%.0fs]"
            % (scen, s, tr["sharpe"], te["sharpe"], te["turnover_per_year"], 100 * te["exposure"],
               row["oracle_test"]["sharpe"], row["seconds"]))
    return out


def judge(out, crit):
    """Pass / fail of the frozen learnability criteria (configs/rl/phase3.yaml, learnability.criteria)."""
    q = out["q_agent"]
    res = {}
    e = q[crit["edge_scenario"]]["summary"]
    res["finds_planted_edge"] = bool(e["sharpe_mean"] >= crit["edge_min_test_sharpe"]
                                     and e["sharpe_mean"] >= crit["edge_min_oracle_share"] * e["oracle_sharpe_mean"])
    res["fits_training_slice"] = bool(e["train_sharpe_mean"] >= crit["min_train_sharpe"])
    nz = q[crit["none_scenario"]]["summary"]
    res["near_flat_without_edge"] = bool(nz["sharpe_mean"] >= crit["none_min_test_sharpe"]
                                         and nz["turnover_mean"] <= crit["none_max_turnover"]
                                         and nz["exposure_mean"] <= crit["none_max_exposure"])
    res["pass"] = all(res.values())
    parts = []
    for k, v in q.items():
        sm = v["summary"]
        parts.append("%s (kappa %.3f): test Sharpe %.2f vs oracle %.2f, train %.2f, turnover %.0f/yr, exposure %.0f%%"
                     % (k, v["kappa"], sm["sharpe_mean"], sm["oracle_sharpe_mean"], sm["train_sharpe_mean"],
                        sm["turnover_mean"], 100 * sm["exposure_mean"]))
    for k, v in out.get("ppo", {}).items():
        sm = v["summary"]
        parts.append("PPO %s: test Sharpe %.2f, train %.2f, turnover %.0f/yr" % (k, sm["sharpe_mean"], sm["train_sharpe_mean"],
                                                                                  sm["turnover_mean"]))
    res["text"] = ("PASS" if res["pass"] else "FAIL") + " (" + ", ".join("%s=%s" % (k, v) for k, v in res.items()
                                                                           if k not in ("pass",)) + "). " + "; ".join(parts)
    return res
