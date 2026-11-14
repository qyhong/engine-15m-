# -*- coding: utf-8 -*-
"""phase3pre -- the Phase 3 steps that run BEFORE the walk-forward test, and decide or check frozen settings:

    py -3 -m engine15.rl phase3-learn      learnability check on synthetic data (Q agent and PPO reference)
    py -3 -m engine15.rl phase3-cadence    update cadence: synthetic drifting edge + BTC's pre-out-of-sample window only
    py -3 -m engine15.rl phase3-risk       the new risk manager judged on buy-and-hold and momentum, no agent

None of them reads an agent result on a test window. The cadence step uses BTC data before 2020-10-01 only (the
first fold's training window): initial training on 2019-10-01 .. 2020-04-01 (early stopping on .. 2020-07-01), then
each cadence fine-tunes through 2020-07-01 .. 2020-10-01, and the cadence with the better validation Sharpe wins.
"""
import json
import os
import time

import numpy as np
import pandas as pd

from . import benchmarks, costs, learncheck, metrics, phase3, policy3, qagent, resources, risk3, walkforward
from .config import resolve
from .continual import full_train, q_of, run_span, eval_q


def _out(cfg, name, obj):
    d = resolve(cfg["report"]["out_dir"])
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, default=str)
    return p


def learn(cfg, log=print):
    resources.low_priority()
    lc_cfg = cfg["learnability"]
    qc, pc = dict(cfg["qagent"]), cfg["policy"]
    acts = cfg["families"]["base"]["actions"]
    seeds = list(lc_cfg["seeds"])
    t0 = time.time()
    out = {"criteria": lc_cfg["criteria"], "seeds": seeds, "q_agent": {}, "ppo": {}}
    for name, k in lc_cfg["scenarios"].items():
        log("Q agent, scenario %s (kappa %.3f)" % (name, k))
        rows = learncheck.run_q(name, seeds, qc, pc, acts, kappa=k, log=log, seed_base=lc_cfg["seed_base"])
        out["q_agent"][name] = {"kappa": k, "rows": rows, "summary": learncheck.summarise(rows)}
    pp = lc_cfg["ppo"]
    for name in pp["scenarios"]:
        k = lc_cfg["scenarios"][name]
        log("PPO reference, scenario %s" % name)
        rows = learncheck.run_ppo(name, seeds[:pp["seeds"]], cfg["ppo_reference"], qc, pc, acts, pp["timesteps"], kappa=k,
                                  log=log, seed_base=lc_cfg["seed_base"])
        out["ppo"][name] = {"kappa": k, "rows": rows, "summary": learncheck.summarise(rows)}
    out["verdict"] = learncheck.judge(out, lc_cfg["criteria"])
    out["minutes"] = round((time.time() - t0) / 60, 1)
    log("learnability: %s" % out["verdict"]["text"])
    return _out(cfg, "phase3_learnability.json", out)


def cadence(cfg, log=print, offline=True):
    resources.low_priority()
    cc = cfg["cadence_choice"]
    qc, pc = dict(cfg["qagent"]), cfg["policy"]
    acts = cfg["families"]["base"]["actions"]
    t0 = time.time()
    res = {"rule": cc["rule"], "candidates": cc["candidates"], "synthetic": {}, "btc_pre_oos": {}}
    # 1) synthetic drifting edge
    for cd in cc["candidates"]:
        q = dict(qc, finetune_steps=int(cc["steps_per_update"][str(cd)]))
        rows = learncheck.run_q("drift", cc["synthetic_seeds"], q, pc, acts, kappa=cc["synthetic_kappa"],
                                flip_days=cc["synthetic_flip_days"], cadences=(cd,), log=log, seed_base=cc["seed_base"])
        res["synthetic"][str(cd)] = {"continual": float(np.mean([r["test_continual_%dd" % cd]["sharpe"] for r in rows])),
                                     "static": float(np.mean([r["test_static"]["sharpe"] for r in rows])),
                                     "by_seed": [r["test_continual_%dd" % cd]["sharpe"] for r in rows]}
    # 2) BTC before the first test window only
    acfg = phase3.for_asset(cfg, "BTCUSDT")
    bars, fund, _ = phase3.load_bars(acfg, offline, log)
    cut = pd.Timestamp(cc["btc_end"], tz="UTC")
    bars = bars[bars.index < cut]
    fund = fund[np.asarray(fund["settle_ms"]) < int(cut.value // 10**6)]
    m = phase3.build_market(acfg, bars, fund)
    rd = qagent.reward_arrays(m, qc)
    s = lambda t: int(bars.index.searchsorted(pd.Timestamp(t, tz="UTC")))
    b = {"tr_lo": s(cc["btc_train"][0]), "val_lo": s(cc["btc_train"][1]), "tr_hi": s(cc["btc_val"][0])}
    vlo, vhi = s(cc["btc_val"][0]), len(bars)
    for seed in cc["btc_seeds"]:
        L, rec = full_train(m, rd, b, qc, pc, acts, 50000 + seed)
        st0 = L.state()
        row = {"static": eval_q(m, L.q(m.raw, rd, vlo, vhi), vlo, vhi, acts, pc)["sharpe"], "fallback": rec["fallback"]}
        for cd in cc["candidates"]:
            L.load_state(st0)
            q = dict(qc, finetune_steps=int(cc["steps_per_update"][str(cd)]))
            L.cfg = q
            W, _ = run_span(L, m, rd, vlo, vhi, q, cadence_days=cd)
            row[str(cd)] = eval_q(m, q_of(W, rd, vlo, vhi, q, acts), vlo, vhi, acts, pc)["sharpe"]
        res["btc_pre_oos"][str(seed)] = row
        log("BTC pre-OOS seed %d: %s" % (seed, row))
    score = {}
    for cd in cc["candidates"]:
        btc = float(np.mean([res["btc_pre_oos"][str(sd)][str(cd)] for sd in cc["btc_seeds"]]))
        syn = res["synthetic"][str(cd)]["continual"]
        score[str(cd)] = {"btc_val_sharpe": btc, "synthetic_test_sharpe": syn, "score": 0.5 * (btc + syn)}
    best = max(cc["candidates"], key=lambda c: (round(score[str(c)]["score"], 6), c))   # ties -> the longer cadence
    res["score"], res["chosen_cadence_days"] = score, int(best)
    res["minutes"] = round((time.time() - t0) / 60, 1)
    log("cadence: %s -> %d day(s)" % (score, best))
    return _out(cfg, "phase3_cadence.json", res)


def riskcheck(cfg, log=print, offline=True):
    """The Phase 3 risk manager on buy-and-hold and momentum (no agent), both fees, out-of-sample span and the
    pre-out-of-sample year, against the raw benchmarks and Phase 2's limits (from phase2_summary.json)."""
    resources.low_priority()
    out = {"rule": cfg["risk_check"]["pass_rule"], "risk3": cfg["risk3"], "assets": {}}
    for asset in cfg["risk_check"]["assets"]:
        acfg = phase3.for_asset(cfg, asset)
        bars, fund, _ = phase3.load_bars(acfg, offline, log)
        m = phase3.build_market(acfg, bars, fund)
        wf = acfg["walkforward"]
        wins = walkforward.windows(bars.index, wf["train_months"], wf["test_months"], wf["step_months"], wf["start"],
                                   wf["min_test_days"])
        lo = int(bars.index.searchsorted(wins[0]["test_start"]))
        pre = int(bars.index.searchsorted(pd.Timestamp(wf["start"], tz="UTC")))
        targets = benchmarks.all_targets(bars, acfg["benchmarks"])
        a = {}
        for pname, model in costs.fee_profiles(acfg).items():
            mk = m.with_model(model)
            r = {}
            for name in ("buy_hold", "momentum"):
                t = targets[name].values.copy()
                for span, (s0, s1) in (("oos", (lo, len(bars))), ("pre_oos", (pre, lo))):
                    tt = np.zeros(len(bars))
                    tt[s0:s1] = t[s0:s1]
                    from . import backtest
                    fr_raw = backtest.run(bars, tt, model, fund)["frame"].iloc[s0:s1]
                    ri = risk3.apply(mk, tt, s0, s1, cfg["risk3"], log_events=False)
                    fr_rm = backtest.run(bars, ri["exec"], model, fund)["frame"].iloc[s0:s1]
                    r["%s_%s" % (name, span)] = {"raw": metrics.summary(fr_raw), "risk3": metrics.summary(fr_rm),
                                                 "counts": ri["counts"],
                                                 "mean_size": float(np.mean(np.abs(ri["exec"][s0:s1])))}
            a[pname] = r
        h = a[list(a)[0]]
        rule = cfg["risk_check"]
        checks = {}
        for name in ("buy_hold", "momentum"):
            x = h["%s_oos" % name]
            checks[name] = {"sharpe_raw": x["raw"]["sharpe"], "sharpe_risk3": x["risk3"]["sharpe"],
                            "maxdd_raw": x["raw"]["max_drawdown"], "maxdd_risk3": x["risk3"]["max_drawdown"],
                            "pass": bool(x["risk3"]["sharpe"] >= rule["min_sharpe_ratio"] * x["raw"]["sharpe"]
                                         and x["risk3"]["max_drawdown"] < x["raw"]["max_drawdown"])}
        a["checks"] = checks
        a["pass"] = all(c["pass"] for c in checks.values())
        out["assets"][asset] = a
        log("%s risk check: %s" % (asset, json.dumps(checks)))
    p2 = os.path.join(resolve(cfg["report"]["out_dir"]), "phase2_summary.json")
    if os.path.exists(p2):
        with open(p2, encoding="utf-8") as f:
            s2 = json.load(f)
        out["phase2_limits_on_buy_hold"] = s2["fees"]["fee_0.10%"]["strategies"]["buy_hold_with_risk_manager"]["overall"]
    out["pass"] = all(v["pass"] for v in out["assets"].values())
    return _out(cfg, "phase3_riskcheck.json", out)


def diag2(cfg, log=print):
    """DIAGNOSTIC ONLY: the Phase 3 filters on the Phase 2 agent's (already seen) test-window trades."""
    from . import diag2 as d2
    resources.low_priority()
    rep = d2.phase2_targets(log=log)
    res = d2.apply_filters(rep, cfg["diag2"], cfg)
    sc = d2.score(rep, res)
    rows = {}
    for k in res:
        a, b = sc["fee_0.10%"][k], sc["fee_0.05%"][k]
        mean = lambda lst, key: float(np.mean([x[key] for x in lst]))
        be = [x.get("break_even_fee") for x in a]
        rows[k] = {"return": mean(a, "total_return"), "sharpe": mean(a, "sharpe"), "max_drawdown": mean(a, "max_drawdown"),
                   "trades_per_year": float(np.mean([x["trades"] / x["years"] for x in a])),
                   "avg_holding_hours": mean(a, "avg_holding_hours"), "turnover_per_year": mean(a, "turnover_per_year"),
                   "break_even_fee": float(np.mean([x for x in be if x is not None])) if any(x is not None for x in be) else None,
                   "return_005": mean(b, "total_return"), "sharpe_005": mean(b, "sharpe"), "series": len(a)}
    out = {"label": "DIAGNOSTIC ONLY - uses Phase 2 test windows that were already seen; not a result",
           "thresholds": cfg["diag2"], "rows": rows,
           "note": "Unfiltered = the Phase 2 PPO's own targets without Phase 2's risk manager. Thresholds fixed in phase3.yaml "
                   "(diag2), not tuned here."}
    log("diag2: " + "; ".join("%s Sharpe %.2f trades/yr %.0f" % (k, v["sharpe"], v["trades_per_year"]) for k, v in rows.items()))
    return _out(cfg, "phase3_diag2.json", out)


def learn_power(cfg, log=print, seeds=10, test_months=24):
    """SUPPLEMENTARY (added after the frozen learnability check failed; no setting changed): the same frozen agent on
    more synthetic series with a longer test, to tell 'cannot learn' from 'the 5-seed, 12-month check is too noisy'."""
    resources.low_priority()
    lc_cfg = cfg["learnability"]
    qc, pc = dict(cfg["qagent"]), cfg["policy"]
    acts = cfg["families"]["base"]["actions"]
    out = {"label": "supplementary, added after the frozen check failed; no agent setting changed", "seeds": seeds,
           "test_months": test_months, "q_agent": {}}
    for name in ("edge", "none"):
        k = lc_cfg["scenarios"][name]
        rows = learncheck.run_q(name, list(range(seeds)), qc, pc, acts, kappa=k, log=log, seed_base=4000,
                                test_months=test_months)
        sm = learncheck.summarise(rows)
        sm["fallback_share"] = float(np.mean([r["test_static"]["trades"] == 0 for r in rows]))
        sm["corr_with_planted_mean"] = float(np.mean([r["corr_with_planted"] for r in rows]))
        sm["traded_seeds_test_sharpe_mean"] = (float(np.mean([r["test_static"]["sharpe"] for r in rows if r["test_static"]["trades"] > 0]))
                                               if any(r["test_static"]["trades"] > 0 for r in rows) else None)
        out["q_agent"][name] = {"kappa": k, "summary": sm, "rows": rows}
    p = os.path.join(resolve(cfg["report"]["out_dir"]), "phase3_learnability.json")
    with open(p, encoding="utf-8") as f:
        base = json.load(f)
    base["supplementary_power_check"] = out
    with open(p, "w", encoding="utf-8") as f:
        json.dump(base, f, indent=1, default=str)
    log("power check: " + "; ".join("%s: test Sharpe %.2f (oracle %.2f), abstained %.0f%%, corr %.2f"
                                    % (k, v["summary"]["sharpe_mean"], v["summary"]["oracle_sharpe_mean"],
                                       100 * v["summary"]["fallback_share"], v["summary"]["corr_with_planted_mean"])
                                    for k, v in out["q_agent"].items()))
    return p
