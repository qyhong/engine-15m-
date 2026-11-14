# -*- coding: utf-8 -*-
"""phase2 -- data -> features -> PPO per walk-forward fold (seeds one after another) -> stitched
out-of-sample evaluation against the benchmarks at both fees -> phase2_report.md + phase2_summary.json.

Lean by design (8 GB laptop beside the live engine): below-normal priority, torch on 2 threads, one
fold at a time, a fold starts only with >= memory_start_mb free and training stops cleanly under
memory_floor_mb. Every finished fold is saved at once (model .npz + record .json), so an interrupted
run resumes where it stopped (same config hash) instead of starting over.
"""
import copy
import gc
import json
import os
import time

import numpy as np

from . import benchmarks, costs, data, features, report2, resources, train, walkforward
from .config import config_hash, new_run, resolve
from .env import Market
from .phase1 import KEYS, _seed_stats


def _seeds(cfg, n):
    s = list(cfg.get("seeds", [0, 1, 2]))
    if n is None:
        return s
    n = int(n)
    return s[:n] if n <= len(s) else s + [max(s) + 1 + i for i in range(n - len(s))]


def work_hash(cfg, timesteps):
    """What the trained models depend on (not the seed list, not the memory knobs)."""
    t = dict(cfg["train"])
    for k in ("memory_start_mb", "memory_floor_mb", "memory_wait_s", "memory_retries"):
        t.pop(k, None)
    key = {"env": cfg["env"], "risk": cfg["risk"], "agent": cfg["agent"], "train": t, "timesteps": int(timesteps),
           "walkforward": cfg["walkforward"], "costs": cfg["costs"], "data": cfg["data"]["symbol"]}
    return config_hash(key)


def _win_dates(w):
    return dict((k, str(w[k])) for k in ("train_start", "train_end", "test_start", "test_end"))


def _write_progress(out_dir, prog):
    with open(os.path.join(out_dir, "phase2_progress.json"), "w", encoding="utf-8") as f:
        json.dump(prog, f, indent=1, default=str)


def run(cfg, offline=False, seeds=None, timesteps=None, fresh=False, log=print):
    t0 = time.time()
    resources.low_priority()
    resources.torch_lean(cfg["agent"].get("torch_threads", 2))
    seeds = _seeds(cfg, seeds)
    timesteps = int(timesteps or cfg["train"]["timesteps"])
    cfg = copy.deepcopy(cfg)
    cfg["seeds"] = seeds
    cfg["train"]["timesteps"] = timesteps
    run_id, run_dir = new_run(cfg, "phase2")
    out_dir = resolve(cfg["report"]["out_dir"])
    os.makedirs(out_dir, exist_ok=True)
    log("run %s  seeds %s  timesteps/fold %d  free memory %.0f MB" % (run_id, seeds, timesteps, resources.free_mb() or -1))

    bars, fund, drep = data.update_all(cfg, log=log, offline=offline)
    if not len(bars):
        raise SystemExit("no bars stored under %s; run without --offline first" % resolve(cfg["data"]["dir"]))
    fcfg = cfg["env"]["features"]
    feats = features.build(bars, fund, fcfg).astype("float32")
    n = len(bars)
    cuts = sorted(set(int(c) for c in np.random.default_rng(cfg["seed"]).integers(5000, n - 1, 3)))
    la = features.lookahead_report(lambda b, f: features.build(b, f, fcfg), bars, fund, cuts)
    model10 = costs.from_cfg(cfg)
    market = Market(bars, fund, feats, model10)
    del feats
    gc.collect()
    log("bars %d, features %d, real-data look-ahead check %s (%.0fs)" % (n, len(market.columns), la, time.time() - t0))

    wf = cfg["walkforward"]
    wins = walkforward.windows(bars.index, wf["train_months"], wf["test_months"], wf["step_months"], wf["start"],
                               wf["min_test_days"])
    bounds = [train.fold_bounds(bars.index, w, cfg["train"]["validation_months"]) for w in wins]
    wh = work_hash(cfg, timesteps)
    mroot = resolve(cfg["report"]["models_dir"])
    mdir = os.path.join(mroot, wh)
    os.makedirs(mdir, exist_ok=True)
    gi = os.path.join(mroot, ".gitignore")
    if not os.path.exists(gi):
        with open(gi, "w") as f:
            f.write("# trained model files: small, reproducible from the config; not for version control\n*\n!.gitignore\n")
    log("walk-forward: %d folds, out of sample %s .. %s; models in %s" % (len(wins), wins[0]["test_start"].date(),
                                                                       wins[-1]["test_end"].date(), mdir))

    tc = cfg["train"]
    pols, recs = {}, {}
    stopped = None
    mem_file = os.path.join(mdir, "memory_events.json")
    mem_events = []
    if os.path.exists(mem_file) and not fresh:
        with open(mem_file, encoding="utf-8") as fh:
            mem_events = json.load(fh)
    for seed in seeds:
        for f, (w, b) in enumerate(zip(wins, bounds)):
            base = os.path.join(mdir, "s%d_f%02d" % (seed, f))
            if not fresh and os.path.exists(base + ".npz") and os.path.exists(base + ".json"):
                with open(base + ".json", encoding="utf-8") as fh:
                    rec = json.load(fh)
                if rec.get("window") == _win_dates(w):
                    pols[(seed, f)] = train.NumpyPolicy.load(base + ".npz")
                    recs[(seed, f)] = rec
                    continue
            pol = None
            for attempt in range(int(tc.get("memory_retries", 8)) + 1):
                tw = time.time()
                if not resources.wait_for_memory(tc.get("memory_start_mb", 700), tc.get("memory_wait_s", 900), log=log):
                    mem_events.append({"seed": seed, "fold": f, "event": "waited %.0f s, memory stayed under %d MB"
                                       % (time.time() - tw, tc.get("memory_start_mb", 700)), "utc": time.strftime("%H:%M:%S", time.gmtime())})
                    continue
                if time.time() - tw > 5:
                    mem_events.append({"seed": seed, "fold": f, "event": "waited %.0f s for %d MB free before starting"
                                       % (time.time() - tw, tc.get("memory_start_mb", 700)), "utc": time.strftime("%H:%M:%S", time.gmtime())})
                free = resources.free_mb()
                try:
                    pol, rec = train.train_fold(market, b, seed, cfg, timesteps, log=log)
                    break
                except resources.MemoryLow as e:
                    mem_events.append({"seed": seed, "fold": f, "event": "training stopped (%s); fold restarts after a wait" % e,
                                       "utc": time.strftime("%H:%M:%S", time.gmtime())})
                    log("memory guard: %s; waiting, then retrying seed %d fold %d" % (e, seed, f))
                    gc.collect()
            if pol is None:
                stopped = {"seed": seed, "fold": f, "reason": "memory stayed too low after %d attempts" % (attempt + 1)}
                break
            rec.update({"fold": f, "window": _win_dates(w), "free_mb_at_start": free})
            pol.meta.update({"fold": f, "window": _win_dates(w), "columns": market.columns, "work_hash": wh})
            pol.save(base + ".npz")
            with open(base + ".json", "w", encoding="utf-8") as fh:
                json.dump(rec, fh, indent=1, default=str)
            pols[(seed, f)], recs[(seed, f)] = pol, rec
            log("seed %d fold %2d (%s..%s): %d steps, kept check %d, train Sharpe %+.2f, val Sharpe %+.2f, %.0fs, "
                "free %.0f MB  [%.0f min total]"
                % (seed, f, w["test_start"].date(), w["test_end"].date(), rec["timesteps_run"], pol.meta["kept_check"],
                   rec["train"]["sharpe"], rec["val"]["sharpe"], rec["seconds"], resources.free_mb() or -1,
                   (time.time() - t0) / 60))
            gc.collect()
        if stopped:
            break
    done = sorted(recs)
    with open(mem_file, "w", encoding="utf-8") as fh:
        json.dump(mem_events, fh, indent=1)
    prog = {"run_id": run_id, "work_hash": wh, "models_dir": mdir, "seeds": seeds, "folds": len(wins),
            "done": ["s%d_f%02d" % k for k in done], "stopped": stopped, "memory_events": mem_events,
            "updated_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())}
    _write_progress(out_dir, prog)
    if stopped:
        log("STOPPED for memory at seed %s fold %s: %s. %d of %d folds done; rerun the same command to resume."
            % (stopped["seed"], stopped["fold"], stopped["reason"], len(done), len(seeds) * len(wins)))
        return {"complete": False, "progress": prog}
    log("training done (%.0f min). Evaluating out of sample..." % ((time.time() - t0) / 60))

    # ---- out-of-sample evaluation: benchmarks and agent, both fees, same stitched span
    profiles = costs.fee_profiles(cfg)
    targets = benchmarks.all_targets(bars, cfg["benchmarks"])
    ecfg, rcfg = cfg["env"], cfg["risk"]
    res, risk_logs, checks = {}, [], {}
    for pname, model in profiles.items():
        mk = market.with_model(model)
        r = {}
        for name, tgt in targets.items():
            st = walkforward.stitch(bars.index, wins, lambda tr, te, t=tgt: t.values[te])
            r[name], _ = train.backtest_eval(bars, st, model, fund, wins)
        rnames = [k for k in r if k.startswith("random_s")]
        bh_rm_tgt, bh_rm_counts = train.constant_oos(mk, bounds, ecfg, rcfg, len(ecfg["actions"]) - 1)
        bh_rm, _ = train.backtest_eval(bars, bh_rm_tgt, model, fund, wins)
        bh_rm["risk_counts"] = bh_rm_counts
        agents = {}
        for seed in seeds:
            out = train.evaluate_oos(mk, [pols[(seed, f)] for f in range(len(wins))], bounds, ecfg, rcfg,
                                     log_events=(pname == list(profiles)[0]))
            ev, r_bt = train.backtest_eval(bars, out["target"], model, fund, wins)
            lo, hi = out["span"]
            diff = float(np.max(np.abs(out["env_r_net"][lo + 1:hi] - r_bt[lo + 1:hi])))
            checks["%s_s%d" % (pname, seed)] = diff
            ev["risk_counts"] = out["risk_counts"]
            span_t = out["target"].values[lo:hi]
            ev["position_mix"] = {"long": float(np.mean(span_t > 0)), "flat": float(np.mean(span_t == 0)),
                                  "short": float(np.mean(span_t < 0))}
            ev["min_hold_refusals"] = out["min_hold_refusals"]
            agents["agent_s%d" % seed] = ev
            if out["risk_events"]:
                for e in out["risk_events"]:
                    risk_logs.append(dict(e, seed=seed))
            del out
            gc.collect()
        res[pname] = {"model": model.as_dict(), "buy_hold": r["buy_hold"], "momentum": r["momentum"],
                      "random": _seed_stats(r, rnames), "random_seeds": dict((k, r[k]["stitched"]) for k in rnames),
                      "random_windows": dict((k, r[k]["windows"]) for k in rnames),
                      "buy_hold_risk_manager": bh_rm, "agents": agents,
                      "agent": _seed_stats(agents, sorted(agents))}
        log("%s evaluated (%.0f min)" % (pname, (time.time() - t0) / 60))
        gc.collect()
    worst = max(checks.values()) if checks else 0.0
    log("env vs backtest P&L check: max |difference| per bar %.2e" % worst)

    result = {"run_id": run_id, "generated_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "config": cfg,
              "work_hash": wh, "models_dir": mdir, "data": {"bars": drep.get("bars"), "funding": drep.get("funding")},
              "features": {"columns": market.columns, "lookahead_check_on_real_data": dict((str(k), v) for k, v in la.items())},
              "windows": [dict((k, str(v.date()) if hasattr(v, "date") else v) for k, v in w.items()) for w in wins],
              "training": dict(("s%d_f%02d" % k, v) for k, v in recs.items()), "results": res,
              "env_backtest_max_abs_diff": worst, "seeds": seeds, "timesteps": timesteps,
              "elapsed_min": round((time.time() - t0) / 60, 1), "progress": prog}
    result["flags"] = report2.flags(result)
    result["verdict"] = report2.verdict(result)
    summary = report2.summary_json(result)
    md = report2.markdown(result)
    for d in (out_dir, run_dir):
        with open(os.path.join(d, "phase2_report.md"), "w", encoding="utf-8") as fh:
            fh.write(md)
        with open(os.path.join(d, "phase2_summary.json"), "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=1, default=str)
    with open(os.path.join(run_dir, "phase2_full.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, default=str)
    report2.write_risk_log(os.path.join(out_dir, "phase2_risk_log.csv"), risk_logs)
    log("report written: %s (run folder %s) in %.0f min" % (os.path.join(out_dir, "phase2_report.md"), run_dir,
                                                           (time.time() - t0) / 60))
    result["complete"] = True
    return result
