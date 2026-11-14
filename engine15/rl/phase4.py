# -*- coding: utf-8 -*-
"""phase4 -- more data per model: does a 15m agent trained on longer, pooled history with economically motivated inputs
find a real out-of-sample edge? Paper only.

    py -3 -m engine15.rl phase4-learn [--offline]   learnability at the new data sizes (synthetic; before the freeze)
    py -3 -m engine15.rl phase4-check [--offline]   input caches + the no-look-ahead truncation test on real data
    py -3 -m engine15.rl phase4 [--offline] [--fresh]   the frozen walk-forward, once -> phase4_report.md / _summary.json

The walk-forward refuses to run until configs/rl/phase4.yaml is frozen (status: frozen, primary chosen). Every fold model
is saved as it finishes (models4/<work hash>/<variant>/s<seed>/): a rerun resumes. One process; assets are loaded one at
a time into memory-mapped float32 caches; below-normal priority; torch on 2 threads; a heavy step starts only with
>= start_mb free and pauses (never fails) under floor_mb.

Out of sample = Phase 1's 25 stitched 3-month test windows (2020-10-01 .. 2026-11-11), every decision from a model trained
only on data before its window. Agents run through the Phase 3 risk manager into the shared backtester at 0.10% (headline)
and 0.05% a side; everything built on or compared with the loop's rules A / B is scored only up to 2025-11-11 (the loop's
sealed holdout is 2025-11-11 .. 2026-11-11); the agents are shown on both spans, labelled.
"""
import copy
import gc
import glob
import json
import os
import time

import numpy as np
import pandas as pd

from . import baselines3, benchmarks, costs, features4, pool4, policy3, report4, resources, train, walkforward
from .config import config_hash, new_run, resolve
from .continual import neutral_w, q_of
from .env import Market
from .models4 import q_fold, sp_fold
from .phase1 import _seed_stats
from .phase3 import _jdump, _npsave, evaluate_target

PHASE3_KEYS = {"agent_continual_retrain": "phase3_agent_c", "agent_static": "phase3_agent_a"}


# ---------------------------------------------------------------- set-up
def check_frozen(cfg):
    if str(cfg.get("status", "")).lower() != "frozen" or not cfg.get("primary"):
        raise SystemExit("configs/rl/phase4.yaml is not frozen (status: frozen and a primary variant are required "
                         "before the walk-forward runs)")


def eval_assets(cfg):
    return [a for a, v in cfg["assets"].items() if v.get("eval")]


def variant_assets(cfg, vname):
    v = cfg["variants"][vname]
    if v["pool"] == "single":
        return None
    return list(cfg["pools"][v["pool"]])


def used_assets(cfg):
    out = list(eval_assets(cfg))
    for vn in cfg["variants"]:
        for a in variant_assets(cfg, vn) or []:
            if a not in out:
                out.append(a)
    return out


def input_columns(cfg, A, inputs):
    p3 = [c for c in A.columns if c not in features4.READINGS and c not in features4.FLAGS]
    if inputs == "p3":
        return p3
    return p3 + [c for c in list(features4.READINGS) + features4.FLAGS if c in A.columns]


def work_hash(cfg):
    key = dict((k, cfg[k]) for k in ("features", "qagent", "policy", "actions", "sp", "q", "train4", "variants", "pools",
                                      "assets", "walkforward", "costs", "data_end", "seeds") if k in cfg)
    return config_hash(key)


def fold_times(cfg, wins):
    t4 = cfg["train4"]
    out = []
    for w in wins:
        out.append({"i": w["i"], "w12_start": w["train_start"], "test_start": w["test_start"], "test_end": w["test_end"],
                    "val_exp": w["test_start"] - pd.DateOffset(months=int(t4["validation_months_expanding"])),
                    "val_w12": w["train_end"] - pd.DateOffset(months=int(t4["validation_months_window12"]))})
    return out


def geo_for(A, ft, window):
    if window == "window12":
        lo, val = A.at(ft["w12_start"]), A.at(ft["val_w12"])
    else:
        lo, val = A.start, A.at(ft["val_exp"])
    return {"lo": max(lo, A.start), "val": val, "te_lo": A.at(ft["test_start"]), "te_hi": A.at(ft["test_end"])}


# ---------------------------------------------------------------- training (resumable)
def train_variant(cfg, vname, assets_by_name, fts, seeds, root, pause, log, t0):
    v = cfg["variants"][vname]
    qcfg = dict(cfg["qagent"])
    acts = cfg["actions"]
    mh = int(cfg["policy"]["min_hold_bars"])
    evals = eval_assets(cfg)
    groups = [(evals, variant_assets(cfg, vname))] if v["pool"] != "single" else [([a], [a]) for a in evals]
    for seed in seeds:
        for ft in fts:
            f = ft["i"]
            for ev_names, pool in groups:
                tag = "_".join(ev_names) if v["pool"] == "single" else "pool"
                d = os.path.join(root, vname, "s%d" % seed)
                recp = os.path.join(d, "rec_f%02d_%s.json" % (f, tag))
                if os.path.exists(recp) and all(os.path.exists(os.path.join(d, "w_f%02d_%s.npy" % (f, a))) for a in ev_names):
                    continue
                os.makedirs(d, exist_ok=True)
                where = "%s s%d fold %d %s" % (vname, seed, f, tag)
                pause.before_start(where)
                assets = [assets_by_name[a] for a in pool]
                cols = input_columns(cfg, assets[0], v["inputs"])
                geo = dict((A.name, geo_for(A, ft, v["window"])) for A in assets)
                ci = assets[0].cols(cols)
                for A in assets[1:]:
                    assert [A.columns[i] for i in A.cols(cols)] == cols
                fseed = int(seed) * 1000 + f
                if v["model"] == "sp":
                    W, rec = sp_fold(assets, ev_names, ci, geo, cfg["sp"], qcfg, acts, mh, fseed, pause, where)
                else:
                    W, rec = q_fold(assets, ev_names, ci, geo, cfg["q"], qcfg, acts, mh, fseed, pause, where)
                for a in ev_names:
                    _npsave(W[a], os.path.join(d, "w_f%02d_%s.npy" % (f, a)))
                rec.update({"fold": f, "variant": vname, "columns": cols, "geo": geo, "free_mb": resources.free_mb()})
                _jdump(rec, recp)
                log("%s: %s  [%.0f min, free %.0f MB]" % (where, "; ".join(
                    "%s train %+.2f val %+.2f%s" % (a, rec["assets"][a]["train"]["sharpe"], rec["assets"][a]["val"]["sharpe"],
                                                     " -> neutral" if rec["assets"][a]["fallback"] else "") for a in ev_names)
                    + "; chosen %s; %.0fs" % (rec.get("chosen"), rec.get("seconds", 0)),
                    (time.time() - t0) / 60, resources.free_mb() or -1))
                del W
                gc.collect()


def load_records(root, vname, seed, fts, asset, single):
    tag = asset if single else "pool"
    out = []
    for ft in fts:
        with open(os.path.join(root, vname, "s%d" % seed, "rec_f%02d_%s.json" % (ft["i"], tag)), encoding="utf-8") as fh:
            out.append(json.load(fh))
    return out


def oos_q(cfg, root, vname, seed, fts, A):
    """Q over the out-of-sample span of asset A from the stored W per fold (neutral in 'do no harm' folds)."""
    acts = cfg["actions"]
    single = cfg["variants"][vname]["pool"] == "single"
    recs = load_records(root, vname, seed, fts, A.name, single)
    parts = []
    for ft, r in zip(fts, recs):
        W = np.load(os.path.join(root, vname, "s%d" % seed, "w_f%02d_%s.npy" % (ft["i"], A.name)))
        parts.append(neutral_w(len(W), acts, 0.0) if r["assets"][A.name]["fallback"] else W)
    W = np.concatenate(parts)
    lo, hi = A.at(fts[0]["test_start"]), A.at(fts[-1]["test_end"])
    assert len(W) == hi - lo, (len(W), hi - lo)
    rd = dict((k, np.asarray(v)) for k, v in A.rd.items())
    return q_of(W, rd, lo, hi, cfg["qagent"], acts), lo, hi, recs


# ---------------------------------------------------------------- evaluation
def asset_ctx(cfg, asset, offline, log):
    bars, fund = pool4.load_bars(cfg, asset, offline, log)
    A = pool4.Asset(os.path.join(pool4.cache_dir(cfg), asset))
    assert A.n == len(bars), (asset, A.n, len(bars))
    feats = pd.DataFrame(np.asarray(A.X), index=bars.index, columns=A.columns)
    m = Market(bars, fund, feats, pool4.asset_model(cfg, asset))
    del feats
    wf = cfg["walkforward"]
    wins = walkforward.windows(bars.index, wf["train_months"], wf["test_months"], wf["step_months"], wf["start"],
                               wf["min_test_days"])
    dev_n = baselines3.dev_cut_index(bars.index)
    wins_dev = walkforward.windows(bars.index[:dev_n], wf["train_months"], wf["test_months"], wf["step_months"], wf["start"],
                                   wf["min_test_days"])
    bounds = [train.fold_bounds(bars.index, w, 3) for w in wins]
    bounds_dev = [train.fold_bounds(bars.index, w, 3) for w in wins_dev]
    return {"cfg": cfg, "asset": asset, "market": m, "bars": bars, "fund": fund, "wins": wins, "wins_dev": wins_dev,
            "bounds": bounds, "bounds_dev": bounds_dev, "smkt": baselines3.spot_market(bars, fund), "A": A}


def phase3_reference(cfg, log):
    """The Phase 3 agents' out-of-sample evaluations (same data, folds, backtester, risk manager) from its saved run."""
    pat = resolve(cfg["phase3_reference"]["runs_glob"])
    runs = sorted(r for r in glob.glob(pat) if os.path.exists(os.path.join(r, "phase3_full.json")))
    if not runs:
        log("no Phase 3 run found under %s; the Phase 3 benchmark is left out" % pat)
        return None, None
    p = os.path.join(runs[-1], "phase3_full.json")
    with open(p, encoding="utf-8") as fh:
        full = json.load(fh)
    out = {}
    for asset, A in full["assets"].items():
        out[asset] = {}
        for fee, r in A["fees"].items():
            out[asset][fee] = {"full": {}, "dev": {}}
            for k, nm in PHASE3_KEYS.items():
                if k in r["variants"]:
                    out[asset][fee]["full"][nm] = r["variants"][k]
                if k in r["dev"]["variants"]:
                    out[asset][fee]["dev"][nm] = r["dev"]["variants"][k]
    return out, os.path.basename(runs[-1])


def evaluate_asset(cfg, ctx, root, fts, seeds, log, t0, p3ref):
    asset, A, bars = ctx["asset"], ctx["A"], ctx["bars"]
    acts = np.asarray(cfg["actions"], float)
    zero = int(np.argmin(np.abs(acts)))
    mh = int(cfg["policy"]["min_hold_bars"])
    n = len(bars)
    lo_o, hi_o = ctx["bounds"][0]["te_lo"], ctx["bounds"][-1]["te_hi"]
    assert lo_o == A.at(fts[0]["test_start"]) and hi_o == A.at(fts[-1]["test_end"])
    targets, stats, train = {}, {}, {}
    for vname, v in cfg["variants"].items():
        for seed in seeds:
            Q, lo, hi, recs = oos_q(cfg, root, vname, seed, fts, A)
            ip, st = policy3.decide(Q, acts, zero, mh)
            t = np.zeros(n)
            t[lo:hi] = acts[ip]
            targets.setdefault(vname, {})[str(seed)] = t
            stats.setdefault(vname, {})[str(seed)] = st
            train.setdefault(vname, {})[str(seed)] = [{"fold": r["fold"], "train_sharpe": r["assets"][asset]["train"]["sharpe"],
                                                       "train_gross_sharpe": r["assets"][asset]["train"].get("gross_sharpe"),
                                                       "val_sharpe": r["assets"][asset]["val"]["sharpe"],
                                                       "fallback": r["assets"][asset]["fallback"], "chosen": r.get("chosen"),
                                                       "rows_refit": r.get("rows_refit")} for r in recs]
            del Q
    oos_full = np.zeros(n, bool)
    oos_full[lo_o:hi_o] = True
    oos_dev = np.zeros(n, bool)
    oos_dev[ctx["bounds_dev"][0]["te_lo"]:ctx["bounds_dev"][-1]["te_hi"]] = True
    btargets = benchmarks.all_targets(bars, cfg["benchmarks"])
    blines = baselines3.targets(bars) if asset in cfg["phase3_reference"].get("loop_rules_assets", ["BTCUSDT"]) else None
    res = {"bars": n, "first": str(bars.index[0]), "last": str(bars.index[-1]), "columns": A.columns,
           "windows": [dict((k, str(v.date()) if hasattr(v, "date") else v) for k, v in w.items()) for w in ctx["wins"]],
           "windows_dev": [dict((k, str(v.date()) if hasattr(v, "date") else v) for k, v in w.items()) for w in ctx["wins_dev"]],
           "fees": {}, "training": train, "decision_stats": stats}
    for pname, model in costs.fee_profiles(cfg).items():
        B = {}
        for name, tgt in btargets.items():
            B[name] = evaluate_target(ctx, np.where(oos_full, tgt.values, 0.0), model, use_risk=False)
        bh = {"full": B["buy_hold"]["full"]["stitched"]["sharpe"], "dev": B["buy_hold"]["dev"]["stitched"]["sharpe"]}
        for name in ("buy_hold", "momentum"):
            B[name + "_risk3"] = evaluate_target(ctx, np.where(oos_full, btargets[name].values, 0.0), model, use_risk=True)
        B["buy_hold_spot"] = evaluate_target(ctx, np.where(oos_full, 1.0, 0.0), model, ev_kind="spot", span="full")
        if blines is not None:
            for bn in ("A", "B"):
                B["baseline_" + bn] = evaluate_target(ctx, np.where(oos_dev, blines[bn], 0.0), model, ev_kind="spot",
                                                      span="dev")
        rn = [k for k in B if k.startswith("random_s")]
        full_b = dict((k, B[k]["full"]) for k in ("buy_hold", "momentum", "buy_hold_risk3", "momentum_risk3", "buy_hold_spot"))
        full_b["random"] = _seed_stats(dict((k, B[k]["full"]) for k in rn), rn)
        dev_b = dict((k, B[k]["dev"]) for k in ("buy_hold", "momentum", "buy_hold_risk3", "momentum_risk3", "buy_hold_spot"))
        dev_b["random"] = _seed_stats(dict((k, B[k]["dev"]) for k in rn), rn)
        if blines is not None:
            dev_b["baseline_A"], dev_b["baseline_B"] = B["baseline_A"]["dev"], B["baseline_B"]["dev"]
        del B
        gc.collect()
        vf, vd = {}, {}
        for vname in cfg["variants"]:
            pf, pd_ = {}, {}
            for seed, tgt in targets[vname].items():
                e = evaluate_target(ctx, tgt, model, 1.0, True, bh={"full": bh["full"], "dev": bh["dev"]})
                raw = evaluate_target(ctx, tgt, model, 1.0, False)
                extra = {"decision_stats": stats[vname][seed], "risk_counts": e["risk"]["counts"] if e["risk"] else None}
                for key, dst in (("full", pf), ("dev", pd_)):
                    rr = raw[key]
                    x = dict(e[key])
                    x.update(extra)
                    x["without_risk_manager"] = dict(rr["stitched"], break_even_fee=rr["break_even_fee"])
                    dst[seed] = x
            vf[vname] = {"seeds": pf, "mean": _seed_stats(pf, sorted(pf)), "eval": "risk3", "span": "full"}
            vd[vname] = {"seeds": pd_, "mean": _seed_stats(pd_, sorted(pd_)), "eval": "risk3", "span": "dev"}
        ref = (p3ref or {}).get(asset, {}).get(pname, {"full": {}, "dev": {}})
        res["fees"][pname] = {"model": model.as_dict(), "bench": full_b, "variants": vf, "phase3": ref["full"],
                              "dev": {"bench": dev_b, "variants": vd, "phase3": ref["dev"]}}
        log("%s %s evaluated (%.0f min)" % (asset, pname, (time.time() - t0) / 60))
        gc.collect()
    return res


# ---------------------------------------------------------------- entry points
def prepare_all(cfg, offline, log, pause):
    for a in used_assets(cfg):
        pause.before_start("cache " + a)
        pool4.prepare(cfg, a, offline, log)
        gc.collect()


def check(cfg, offline=True, log=print):
    """Caches + the real-data truncation test -> phase4_lookahead.json."""
    resources.low_priority()
    mem = cfg["memory"]
    pause = resources.MemoryPause(mem["start_mb"], mem["floor_mb"], mem.get("poll_s", 20), log)
    prepare_all(cfg, offline, log, pause)
    pause.before_start("look-ahead check")
    rep = features4.lookahead(used_assets(cfg), n_cuts=int(cfg["lookahead"]["cuts"]), seed=int(cfg["lookahead"]["seed"]),
                              log=log, extra_cuts=int(cfg["lookahead"]["cuts_other"]))
    # the assembled matrix on the RL bars (Phase 3 features + snapshot readings + flags), cut at random bars
    rep["assembled"] = {}
    for a in eval_assets(cfg):
        bars, fund = pool4.load_bars(cfg, a, offline, log)
        snap = os.path.join(pool4.cache_dir(cfg), "readings_%s.npz" % a)
        rng = np.random.default_rng(int(cfg["lookahead"]["seed"]) + 1)
        cuts = sorted(int(c) for c in rng.integers(5000, len(bars) - 1, int(cfg["lookahead"]["cuts"])))
        la = features4.features_lookahead(bars, fund, cfg["features"], snap, cuts)
        rep["assembled"][a] = dict((str(bars.index[k]), v) for k, v in la.items())
        log("assembled inputs %s: %s" % (a, rep["assembled"][a]))
        del bars, fund
    rep["clean"] = bool(rep["clean"] and all(not v for d in rep["assembled"].values() for v in d.values()))
    rep["memory_events"] = pause.events
    p = os.path.join(resolve(cfg["report"]["out_dir"]), "phase4_lookahead.json")
    _jdump(report4.clean(rep), p)
    log("look-ahead check: %s -> %s" % ("CLEAN" if rep["clean"] else "NOT CLEAN", p))
    return rep


def learn(cfg, log=print):
    from . import learn4
    resources.low_priority()
    resources.torch_lean(cfg["qagent"].get("torch_threads", 2))
    mem = cfg["memory"]
    pause = resources.MemoryPause(mem["start_mb"], mem["floor_mb"], mem.get("poll_s", 20), log)
    out = os.path.join(resolve(cfg["report"]["out_dir"]), "phase4_learnability.json")
    res = learn4.run(cfg, out, log=log, pause=pause)
    res["memory_events"] = pause.events
    _jdump(report4.clean(res), out)
    for k, v in res["main"].items():
        log("learnability %s: %s | edge test Sharpe %.2f (oracle %.2f), found in %s seeds; none: Sharpe %.2f turnover %.0f exposure %.0f%%"
            % (k, "PASS" if v["judge"]["pass"] else "FAIL", v["summary"]["edge"]["test_sharpe_mean"],
               v["summary"]["edge"]["oracle_sharpe_mean"], v["summary"]["edge"]["found_edge_seeds"],
               v["summary"]["none"]["test_sharpe_mean"], v["summary"]["none"]["turnover_mean"],
               100 * v["summary"]["none"]["exposure_mean"]))
    return res


def run(cfg, offline=False, fresh=False, log=print):
    check_frozen(cfg)
    t0 = time.time()
    resources.low_priority()
    resources.torch_lean(cfg["qagent"].get("torch_threads", 2))
    cfg = copy.deepcopy(cfg)
    seeds = list(cfg["seeds"])
    run_id, run_dir = new_run(cfg, "phase4")
    out_dir = resolve(cfg["report"]["out_dir"])
    os.makedirs(out_dir, exist_ok=True)
    mem = cfg["memory"]
    pause = resources.MemoryPause(mem["start_mb"], mem["floor_mb"], mem.get("poll_s", 20), log)
    log("run %s  seeds %s  primary %s  free memory %.0f MB" % (run_id, seeds, cfg["primary"], resources.free_mb() or -1))
    la_p = os.path.join(out_dir, "phase4_lookahead.json")
    if not os.path.exists(la_p):
        check(cfg, offline, log)
    with open(la_p, encoding="utf-8") as fh:
        la = json.load(fh)
    if not la.get("clean"):
        raise SystemExit("the look-ahead check is not clean (%s); fix the inputs before any walk-forward" % la_p)
    prepare_all(cfg, offline, log, pause)
    wh = work_hash(cfg)
    root = os.path.join(resolve(cfg["report"]["models_dir"]), wh)
    if fresh and os.path.isdir(root):
        import shutil
        shutil.rmtree(root)
    os.makedirs(root, exist_ok=True)
    gi = os.path.join(resolve(cfg["report"]["models_dir"]), ".gitignore")
    if not os.path.exists(gi):
        with open(gi, "w") as f:
            f.write("# trained model files: reproducible from the config; not for version control\n*\n!.gitignore\n")
    assets_by_name = dict((a, pool4.Asset(os.path.join(pool4.cache_dir(cfg), a))) for a in used_assets(cfg))
    btc = assets_by_name[eval_assets(cfg)[0]]
    wf = cfg["walkforward"]
    idx = pd.to_datetime(btc.t, unit="ms", utc=True)
    wins = walkforward.windows(idx, wf["train_months"], wf["test_months"], wf["step_months"], wf["start"], wf["min_test_days"])
    fts = fold_times(cfg, wins)
    log("%d folds, out of sample %s .. %s; variants %s; models in %s" % (len(fts), fts[0]["test_start"].date(),
                                                                         fts[-1]["test_end"].date(), list(cfg["variants"]), root))
    order = [cfg["primary"]] + [v for v in cfg["variants"] if v != cfg["primary"]]
    for vname in order:
        train_variant(cfg, vname, assets_by_name, fts, seeds, root, pause, log, t0)
        log("%s trained (%.0f min)" % (vname, (time.time() - t0) / 60))
    del assets_by_name
    gc.collect()
    p3ref, p3run = phase3_reference(cfg, log)
    results = {}
    for asset in eval_assets(cfg):
        pause.before_start("evaluate " + asset)
        ctx = asset_ctx(cfg, asset, offline, log)
        results[asset] = evaluate_asset(cfg, ctx, root, fts, seeds, log, t0, p3ref)
        del ctx
        gc.collect()
    result = {"run_id": run_id, "generated_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "config": cfg,
              "seeds": seeds, "assets": results, "elapsed_min": round((time.time() - t0) / 60, 1),
              "memory_events": pause.events, "work_hash": wh, "models_dir": root, "phase3_run": p3run,
              "folds": [dict((k, str(v)) for k, v in ft.items()) for ft in fts]}
    for name in ("phase4_learnability.json", "phase4_lookahead.json"):
        pth = os.path.join(out_dir, name)
        if os.path.exists(pth):
            with open(pth, encoding="utf-8") as fh:
                result[name.replace("phase4_", "").replace(".json", "")] = json.load(fh)
    result["flags"] = report4.flags(result)
    result["verdict"] = report4.verdict(result)
    md = report4.markdown(result)
    summ = report4.summary_json(result)
    for d in (out_dir, run_dir):
        with open(os.path.join(d, "phase4_report.md"), "w", encoding="utf-8") as fh:
            fh.write(md)
        _jdump(report4.clean(summ), os.path.join(d, "phase4_summary.json"))
    _jdump(report4.clean(result), os.path.join(run_dir, "phase4_full.json"))
    log("report written: %s in %.0f min" % (os.path.join(out_dir, "phase4_report.md"), (time.time() - t0) / 60))
    result["complete"] = True
    return result


def rebuild(cfg, log=print):
    """Rebuild the report from the latest run's saved phase4_full.json (formatting only)."""
    runs = sorted(r for r in glob.glob(os.path.join(resolve(cfg["report"]["runs_dir"]), "phase4_*"))
                  if os.path.exists(os.path.join(r, "phase4_full.json")))
    with open(os.path.join(runs[-1], "phase4_full.json"), encoding="utf-8") as fh:
        result = json.load(fh)
    result["flags"] = report4.flags(result)
    result["verdict"] = report4.verdict(result)
    out_dir = resolve(cfg["report"]["out_dir"])
    with open(os.path.join(out_dir, "phase4_report.md"), "w", encoding="utf-8") as fh:
        fh.write(report4.markdown(result))
    _jdump(report4.clean(report4.summary_json(result)), os.path.join(out_dir, "phase4_summary.json"))
    return os.path.join(out_dir, "phase4_report.md")
