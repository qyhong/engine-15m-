# -*- coding: utf-8 -*-
"""phase5 -- RL Phase 5 parts 2 and 3 (part 1, the forward paper run, is forward5.py + engine15/playbook5.py). Paper only.

    py -3 -m engine15.rl phase5-ablate   part 3: train the registered input ablations (Phase 4 primary setup, inputs
                                          changed only; resumable; heavy, one process, memory-paused)
    py -3 -m engine15.rl phase5          parts 2 + 3 evaluated once -> research/out/rl/phase5_report.md / _summary.json
    py -3 -m engine15.rl phase5-report   rebuild the report from the saved evaluation (formatting only)

Part 2 (trade-less variants) keeps the Phase 4 primary's 25 x 3 trained fold models exactly (models4/<work hash>/
q_pool2_full) and changes only how their values become positions: a wider cost band (t1_band2x), a 2-day minimum hold
(t2_hold2d), or the agent as a +-0.5x tilt around a 1x spot buy-and-hold core (t3_tilt). Part 3 retrains the primary
setup without one reading group at a time (and with readings only / Phase 3 inputs only), plus a supplementary occlusion
of the trained primary. Everything is scored as Phase 4 scored its variants (same data, folds, risk manager, backtester,
fees, benchmarks, flags). Phase 4 already saw every test window through 2026-11-11: nothing here is out of sample in the
strict sense any more; both spans are reported, and anything compared with the loop's rules A / B stops at 2025-11-11.
"""
import copy
import gc
import glob
import json
import os
import time

import numpy as np
import pandas as pd

from . import backtest, baselines3, benchmarks, costs, features4, phase4, policy3, pool4, report4, resources, risk3
from . import walkforward
from .config import config_hash, new_run, resolve
from .continual import neutral_w, q_of
from .models4 import q_fold
from .phase1 import _seed_stats
from .phase3 import _jdump, _npsave, evaluate_target

PRIMARY = "q_pool2_full"
POOL = ["BTCUSDT", "ETHUSDT"]
LABELS5 = {
    "t1_band2x": "t1: wider no-trade band (2 round trips)",
    "t2_hold2d": "t2: minimum hold 2 days",
    "t3_tilt": "t3: 1x spot core +- 0.5x agent tilt",
    "a_p3_only": "ablation: Phase 3 inputs only",
    "a_readings_only": "ablation: readings only",
    "a_no_trend": "ablation: without trend readings",
    "a_no_funding": "ablation: without funding readings",
    "a_no_basis": "ablation: without basis readings",
    "a_no_flow": "ablation: without flow / CVD / Coinbase readings",
    "a_no_vol": "ablation: without volatility-regime readings",
    "a_no_levels": "ablation: without levels readings",
}


def check_frozen(cfg):
    p5 = cfg["phase5"]
    if str(p5.get("status", "")).lower() != "frozen":
        raise SystemExit("configs/rl/phase5.yaml is not frozen; parts 2 and 3 run only after the freeze")


def root4(cfg):
    return os.path.join(resolve(cfg["report"]["models_dir"]), phase4.work_hash(cfg))


def abl_root(cfg):
    key = {"p4": phase4.work_hash(cfg), "ablation": cfg["phase5"]["ablation"]["groups"],
           "variants": cfg["phase5"]["ablation"]["variants"]}
    return os.path.join(resolve(cfg["phase5"]["report"]["models_dir5"]), "ablation", config_hash(key))


def abl_columns(cfg, A, spec):
    p3 = [c for c in A.columns if c not in features4.READINGS and c not in features4.FLAGS]
    rd = [c for c in list(features4.READINGS) + features4.FLAGS if c in A.columns]
    if spec.get("inputs") == "p3":
        return p3
    if spec.get("inputs") == "readings":
        return rd
    drop = set(cfg["phase5"]["ablation"]["groups"][spec["drop"]])
    return [c for c in p3 + rd if c not in drop]


def _assets_and_folds(cfg):
    assets = dict((a, pool4.Asset(os.path.join(pool4.cache_dir(cfg), a))) for a in POOL)
    wf = cfg["walkforward"]
    idx = pd.to_datetime(assets["BTCUSDT"].t, unit="ms", utc=True)
    wins = walkforward.windows(idx, wf["train_months"], wf["test_months"], wf["step_months"], wf["start"], wf["min_test_days"])
    return assets, phase4.fold_times(cfg, wins)


# ---------------------------------------------------------------- part 3: training the ablations (resumable)
def ablate(cfg, log=print):
    check_frozen(cfg)
    resources.low_priority()
    resources.torch_lean(cfg["qagent"].get("torch_threads", 2))
    mem = cfg["phase5"]["memory"]
    pause = resources.MemoryPause(mem["start_mb"], mem["floor_mb"], mem.get("poll_s", 20), log)
    assets_by_name, fts = _assets_and_folds(cfg)
    root = abl_root(cfg)
    os.makedirs(root, exist_ok=True)
    t0 = time.time()
    qcfg = dict(cfg["qagent"])
    mh = int(cfg["policy"]["min_hold_bars"])
    assets = [assets_by_name[a] for a in POOL]
    log("ablation models in %s; free %.0f MB" % (root, resources.free_mb() or -1))
    for vname, spec in cfg["phase5"]["ablation"]["variants"].items():
        cols = abl_columns(cfg, assets[0], spec)
        ci = assets[0].cols(cols)
        for seed in cfg["seeds"]:
            d = os.path.join(root, vname, "s%d" % seed)
            os.makedirs(d, exist_ok=True)
            for ft in fts:
                f = ft["i"]
                recp = os.path.join(d, "rec_f%02d_pool.json" % f)
                if os.path.exists(recp) and all(os.path.exists(os.path.join(d, "w_f%02d_%s.npy" % (f, a))) for a in POOL):
                    continue
                where = "%s s%d fold %d" % (vname, seed, f)
                pause.before_start(where)
                geo = dict((A.name, phase4.geo_for(A, ft, "expanding")) for A in assets)
                W, rec = q_fold(assets, POOL, ci, geo, cfg["q"], qcfg, cfg["actions"], mh, int(seed) * 1000 + f, pause, where)
                for a in POOL:
                    _npsave(W[a], os.path.join(d, "w_f%02d_%s.npy" % (f, a)))
                rec.update({"fold": f, "variant": vname, "columns": cols, "geo": geo, "free_mb": resources.free_mb()})
                _jdump(rec, recp)
                log("%s: %s [%.0f min, free %.0f MB]" % (where, "; ".join(
                    "%s val %+.2f%s" % (a, rec["assets"][a]["val"]["sharpe"], " -> neutral" if rec["assets"][a]["fallback"] else "")
                    for a in POOL), (time.time() - t0) / 60, resources.free_mb() or -1))
                del W
                gc.collect()
        log("%s trained (%.0f min)" % (vname, (time.time() - t0) / 60))
    _jdump({"root": root, "minutes": round((time.time() - t0) / 60, 1), "memory_events": pause.events},
           os.path.join(root, "done.json"))


# ---------------------------------------------------------------- stitched values per variant
def oos_w(root, vname, seed, fts, A, acts, occlude=None, fallback="rule"):
    """W over asset A's out-of-sample span from stored fold values (neutral in 'do no harm' folds). occlude: (cols to
    zero, stats cache) -> the trained model's values with those inputs at 0 (W - x_g . coef_g). fallback (Phase 6): what
    a 'do no harm' fold does: "rule" = flat (Phase 4/5), "none" = the model's own values, "trend" = the trend reference
    position (the frozen daily momentum target, A.rd["ref"])."""
    parts, recs = [], []
    for ft in fts:
        with open(os.path.join(root, vname, "s%d" % seed, "rec_f%02d_pool.json" % ft["i"]), encoding="utf-8") as fh:
            r = json.load(fh)
        recs.append(r)
        W = np.load(os.path.join(root, vname, "s%d" % seed, "w_f%02d_%s.npy" % (ft["i"], A.name)))
        if r["assets"][A.name]["fallback"] and fallback != "none":
            if fallback == "trend":
                g = r["geo"][A.name]
                ref = np.asarray(A.rd["ref"][g["te_lo"]:g["te_hi"]], dtype=np.float32)
                parts.append((-10.0 * np.abs(np.asarray(acts, np.float32)[None, :] - ref[:, None])).astype(np.float32))
            else:
                parts.append(neutral_w(len(W), acts, 0.0))
            continue
        if occlude is not None:
            gcols, cache = occlude
            g = r["geo"][A.name]
            key = (A.name, ft["i"])
            if key not in cache:
                ci = A.cols(r["columns"])
                cache[key] = pool4.norm_stats(A.X, g["lo"], g["te_lo"], ci)
            mu, sd = cache[key]
            j = [r["columns"].index(c) for c in gcols if c in r["columns"]]
            if j:
                ci = A.cols([r["columns"][k] for k in j])
                x = pool4.normalised(A.X, g["te_lo"], g["te_hi"], ci, mu[j], sd[j])
                coef = np.asarray(r["coef"], dtype=np.float32)[:, j]
                W = (W - x @ coef.T).astype(np.float32)
        parts.append(W)
    W = np.concatenate(parts)
    lo, hi = A.at(fts[0]["test_start"]), A.at(fts[-1]["test_end"])
    assert len(W) == hi - lo, (len(W), hi - lo)
    return W, lo, hi, recs


def specs(cfg):
    p5 = cfg["phase5"]
    r4, ra = root4(cfg), abl_root(cfg)
    out = {PRIMARY: {"root": r4, "model": PRIMARY}}
    tl = p5["trade_less"]
    out["t1_band2x"] = {"root": r4, "model": PRIMARY, "cost_mult": float(tl["t1_band2x"]["decision_cost_mult"])}
    out["t2_hold2d"] = {"root": r4, "model": PRIMARY, "min_hold": int(tl["t2_hold2d"]["min_hold_bars"])}
    out["t3_tilt"] = {"root": r4, "model": PRIMARY, "tilt": (float(tl["t3_tilt"]["core"]), float(tl["t3_tilt"]["tilt"]))}
    for vn in p5["ablation"]["variants"]:
        if os.path.exists(os.path.join(ra, vn, "s%d" % cfg["seeds"][-1], "rec_f24_pool.json")):
            out[vn] = {"root": ra, "model": vn}
    for g in p5["ablation"]["groups"]:
        out["o_no_" + g] = {"root": r4, "model": PRIMARY, "occlude": g}
    return out


def _daily(r, index):
    s = pd.Series(np.log1p(np.asarray(r, float)), index=index)
    return s.groupby(s.index.floor("1D")).sum()


def _corr(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 10 or np.std(a[ok]) == 0 or np.std(b[ok]) == 0:
        return None
    return float(np.corrcoef(a[ok], b[ok])[0, 1])


def evaluate_asset(cfg, ctx, sp, fts, seeds, log, t0, keep_exec=False):
    asset, A, bars = ctx["asset"], ctx["A"], ctx["bars"]
    acts = np.asarray(cfg["actions"], float)
    zero = int(np.argmin(np.abs(acts)))
    mh = int(cfg["policy"]["min_hold_bars"])
    n = len(bars)
    lo_o, hi_o = ctx["bounds"][0]["te_lo"], ctx["bounds"][-1]["te_hi"]
    targets, stats, training, cache = {}, {}, {}, {}
    for vname, s in sp.items():
        if "tilt" in s:
            continue
        qc = dict(cfg["qagent"])
        if s.get("cost_mult"):
            qc["cost_mult"] = s["cost_mult"]
        occ = None
        if s.get("occlude"):
            occ = (cfg["phase5"]["ablation"]["groups"][s["occlude"]], cache)
        for seed in seeds:
            W, lo, hi, recs = oos_w(s["root"], s["model"], seed, fts, A, list(acts), occ, s.get("fallback", "rule"))
            rd = dict((k, np.asarray(v)) for k, v in A.rd.items())
            Q = q_of(W, rd, lo, hi, qc, list(acts))
            ip, st = policy3.decide(Q, acts, zero, int(s.get("min_hold", mh)))
            t = np.zeros(n)
            t[lo:hi] = acts[ip]
            targets.setdefault(vname, {})[str(seed)] = t
            stats.setdefault(vname, {})[str(seed)] = st
            training.setdefault(vname, {})[str(seed)] = [
                {"fold": r["fold"], "train_sharpe": r["assets"][asset]["train"]["sharpe"],
                 "val_sharpe": r["assets"][asset]["val"]["sharpe"], "fallback": r["assets"][asset]["fallback"],
                 "chosen": r.get("chosen"), "rows_refit": r.get("rows_refit")} for r in recs]
            del Q, W
    for vname, s in sp.items():
        if "tilt" in s:
            targets[vname] = targets[s["model"]]
            stats[vname] = stats[s["model"]]
            training[vname] = training[s["model"]]
    oos_full = np.zeros(n, bool)
    oos_full[lo_o:hi_o] = True
    oos_dev = np.zeros(n, bool)
    oos_dev[ctx["bounds_dev"][0]["te_lo"]:ctx["bounds_dev"][-1]["te_hi"]] = True
    btargets = benchmarks.all_targets(bars, cfg["benchmarks"])
    blines = baselines3.targets(bars)
    res = {"bars": n, "first": str(bars.index[0]), "last": str(bars.index[-1]), "fees": {}, "training": training,
           "decision_stats": stats}
    for pname, model in costs.fee_profiles(cfg).items():
        B = {}
        for name, tgt in btargets.items():
            B[name] = evaluate_target(ctx, np.where(oos_full, tgt.values, 0.0), model, use_risk=False)
        bh = {"full": B["buy_hold"]["full"]["stitched"]["sharpe"], "dev": B["buy_hold"]["dev"]["stitched"]["sharpe"]}
        for name in ("buy_hold", "momentum"):
            B[name + "_risk3"] = evaluate_target(ctx, np.where(oos_full, btargets[name].values, 0.0), model, use_risk=True)
        B["buy_hold_spot"] = evaluate_target(ctx, np.where(oos_full, 1.0, 0.0), model, ev_kind="spot", span="full")
        bhs = {"full": B["buy_hold_spot"]["full"]["stitched"]["sharpe"], "dev": B["buy_hold_spot"]["dev"]["stitched"]["sharpe"]}
        if asset in cfg["phase3_reference"].get("loop_rules_assets", ["BTCUSDT"]):
            for bn in ("A", "B"):
                B["baseline_" + bn] = evaluate_target(ctx, np.where(oos_dev, blines[bn], 0.0), model, ev_kind="spot",
                                                      span="dev")
        rn = [k for k in B if k.startswith("random_s")]
        keys = ("buy_hold", "momentum", "buy_hold_risk3", "momentum_risk3", "buy_hold_spot")
        full_b = dict((k, B[k]["full"]) for k in keys)
        full_b["random"] = _seed_stats(dict((k, B[k]["full"]) for k in rn), rn)
        dev_b = dict((k, B[k]["dev"]) for k in keys)
        dev_b["random"] = _seed_stats(dict((k, B[k]["dev"]) for k in rn), rn)
        if "baseline_A" in B:
            dev_b["baseline_A"], dev_b["baseline_B"] = B["baseline_A"]["dev"], B["baseline_B"]["dev"]
        del B
        gc.collect()
        vf, vd, execs = {}, {}, {}
        for vname, s in sp.items():
            pf, pd_ = {}, {}
            for seed, tgt in targets[vname].items():
                if "tilt" in s:
                    core, tilt = s["tilt"]
                    ex = risk3.apply(ctx["market"].with_model(model), tgt, lo_o, hi_o, dict(cfg["risk3"]), log_events=False)["exec"]
                    e_t = np.where(oos_full, core + tilt * ex, 0.0)
                    e = evaluate_target(ctx, e_t, model, ev_kind="spot", span="full", bh=bhs)
                    e["risk"] = {"exec": e_t, "counts": None}
                else:
                    e = evaluate_target(ctx, tgt, model, 1.0, True, bh=bh)
                if vname == PRIMARY:
                    execs[seed] = np.asarray(e["risk"]["exec"], float)
                if keep_exec and pname == report4.HEAD:
                    res.setdefault("_exec", {}).setdefault(vname, {})[seed] = np.asarray(e["risk"]["exec"], np.float32)
                extra = {"decision_stats": stats[vname][seed],
                         "risk_counts": (e.get("risk") or {}).get("counts") if isinstance(e.get("risk"), dict) else None}
                for key, dst in (("full", pf), ("dev", pd_)):
                    x = dict(e[key])
                    x.update(extra)
                    dst[seed] = x
            ev = "spot" if "tilt" in s else "risk3"
            vf[vname] = {"seeds": pf, "mean": _seed_stats(pf, sorted(pf)), "eval": ev, "span": "full"}
            vd[vname] = {"seeds": pd_, "mean": _seed_stats(pd_, sorted(pd_)), "eval": ev, "span": "dev"}
        res["fees"][pname] = {"model": model.as_dict(), "bench": full_b, "variants": vf, "phase3": {},
                              "dev": {"bench": dev_b, "variants": vd, "phase3": {}}}
        if pname == report4.HEAD and execs:
            res["correlations"] = correlations(ctx, model, execs, btargets["momentum"].values, blines["A"], oos_full, oos_dev)
        log("%s %s evaluated (%.0f min)" % (asset, pname, (time.time() - t0) / 60))
        gc.collect()
    return res


def correlations(ctx, model, execs, mom_t, a_t, oos_full, oos_dev):
    """Primary (mean of seeds' executed positions) vs the daily momentum rule and rule A: per-bar position and daily net
    return correlations. Rule A: up to 2025-11-11 only."""
    bars, fund = ctx["bars"], ctx["fund"]
    ag = np.mean([execs[s] for s in sorted(execs)], axis=0)
    fr_ag = backtest.run(bars, ag, model, fund)["frame"]
    mom = np.where(oos_full, mom_t, 0.0)
    fr_mo = backtest.run(bars, mom, model, fund)["frame"]
    aa = np.where(oos_dev, a_t, 0.0)
    fr_a = baselines3.spot_frame(ctx["smkt"], aa, model.fee_side, True)
    out = {}
    for span, m in (("full", oos_full), ("dev", oos_dev)):
        idx = bars.index[m]
        d_ag = _daily(fr_ag["r_net"].values[m], idx)
        d_mo = _daily(fr_mo["r_net"].values[m], idx)
        d_bh = _daily(np.asarray(ctx["market"].r_px)[m], idx)
        o = {"position_vs_momentum": _corr(ag[m], mom[m]), "daily_return_vs_momentum": _corr(d_ag.values, d_mo.values),
             "daily_return_vs_buy_hold": _corr(d_ag.values, d_bh.values),
             "same_side_as_momentum_when_in_market": float(np.mean(np.sign(ag[m][ag[m] != 0]) == np.sign(mom[m][ag[m] != 0])))
             if np.any(ag[m] != 0) else None,
             "long_share": float(np.mean(ag[m] > 0)), "short_share": float(np.mean(ag[m] < 0))}
        if span == "dev":
            d_a = _daily(fr_a["r_net"].values[m], idx)
            o["position_vs_rule_A"] = _corr(ag[m], aa[m])
            o["daily_return_vs_rule_A"] = _corr(d_ag.values, d_a.values)
        out[span] = o
    return out


# ---------------------------------------------------------------- entry points
def run(cfg, log=print):
    check_frozen(cfg)
    t0 = time.time()
    resources.low_priority()
    cfg = copy.deepcopy(cfg)
    seeds = list(cfg["seeds"])
    c4 = dict(cfg)
    c4["report"] = dict(cfg["report"])
    run_id, run_dir = new_run(cfg, "phase5")
    mem = cfg["phase5"]["memory"]
    pause = resources.MemoryPause(mem["start_mb"], mem["floor_mb"], mem.get("poll_s", 20), log)
    _, fts = _assets_and_folds(cfg)
    sp = specs(cfg)
    log("run %s; variants %s" % (run_id, list(sp)))
    results = {}
    for asset in POOL:
        pause.before_start("evaluate " + asset)
        ctx = phase4.asset_ctx(cfg, asset, True, log)
        results[asset] = evaluate_asset(cfg, ctx, sp, fts, seeds, log, t0)
        del ctx
        gc.collect()
    rc = {"primary": PRIMARY, "variants": dict((k, v) for k, v in sp.items()), "flags": cfg["flags"],
          "phase5": cfg["phase5"]}
    result = {"run_id": run_id, "generated_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "config": rc,
              "seeds": seeds, "assets": results, "elapsed_min": round((time.time() - t0) / 60, 1),
              "memory_events": pause.events}
    for name in ("phase5_repro.json", "phase5_forward_check.json"):
        p = os.path.join(resolve(cfg["report"]["out_dir"]), name)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                result[name[7:-5]] = json.load(fh)
    abl_done = os.path.join(abl_root(cfg), "done.json")
    if os.path.exists(abl_done):
        with open(abl_done, encoding="utf-8") as fh:
            result["ablation_training"] = json.load(fh)
    from . import report5
    _jdump(report4.clean(result), os.path.join(run_dir, "phase5_full.json"))
    out = report5.write(result, resolve(cfg["report"]["out_dir"]), run_dir)
    log("report written: %s (%.0f min)" % (out, (time.time() - t0) / 60))
    return result


def rebuild(cfg, log=print):
    runs = sorted(r for r in glob.glob(os.path.join(resolve(cfg["report"]["runs_dir"]), "phase5_*"))
                  if os.path.exists(os.path.join(r, "phase5_full.json")))
    with open(os.path.join(runs[-1], "phase5_full.json"), encoding="utf-8") as fh:
        result = json.load(fh)
    from . import report5
    return report5.write(result, resolve(cfg["report"]["out_dir"]), None)
