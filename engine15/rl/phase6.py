# -*- coding: utf-8 -*-
"""phase6 -- RL Phase 6: shaped rewards so that 'flat' scores weakly, symmetric long / short, and three 'do no harm'
modes. Paper only.

    py -3 -m engine15.rl phase6-train    train r_missed and r_flat (learn6.q_fold6; resumable; heavy, memory-paused)
    py -3 -m engine15.rl phase6          evaluate every registered variant once -> research/out/rl/phase6_report.md
    py -3 -m engine15.rl phase6-report   rebuild the report from the saved evaluation (formatting only)

Config: configs/rl/phase6.yaml (frozen before any Phase 6 number). Same data, folds, inputs, risk manager, backtester,
fees, benchmarks and flags as Phase 4; evaluation through phase5.evaluate_asset (Phase 4's scoring) plus the Phase 6
analytics: time long / short / flat, P&L from long bars vs short bars, downtrend periods and down months.
"""
import copy
import gc
import glob
import json
import os
import time

import numpy as np
import pandas as pd
import yaml

from . import backtest, costs, phase4, phase5, report4, resources
from .config import config_hash, new_run, resolve
from .learn6 import add_reference, q_fold6
from .phase3 import _jdump, _npsave

P6_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "configs", "rl",
                       "phase6.yaml")
POOL = phase5.POOL


def load_cfg(path6=None):
    from .forward5 import load_cfg as l5
    cfg = copy.deepcopy(l5())
    with open(path6 or P6_PATH, encoding="utf-8") as fh:
        cfg["phase6"] = yaml.safe_load(fh)
    return cfg


def check_frozen(cfg):
    if str(cfg["phase6"].get("status", "")).lower() != "frozen":
        raise SystemExit("configs/rl/phase6.yaml is not frozen")


def root6(cfg):
    p6 = cfg["phase6"]
    key = {"p4": phase4.work_hash(cfg), "train": p6["variants_train"], "selection": p6["selection"],
           "reference": p6["reference"]}
    return os.path.join(resolve(p6["report"]["models_dir6"]), config_hash(key))


# ---------------------------------------------------------------- training (resumable)
def train(cfg, log=print):
    check_frozen(cfg)
    resources.low_priority()
    resources.torch_lean(cfg["qagent"].get("torch_threads", 2))
    mem = cfg["phase6"]["memory"]
    pause = resources.MemoryPause(mem["start_mb"], mem["floor_mb"], mem.get("poll_s", 20), log)
    assets_by_name, fts = phase5._assets_and_folds(cfg)
    assets = [add_reference(assets_by_name[a]) for a in POOL]
    root = root6(cfg)
    os.makedirs(root, exist_ok=True)
    cols = phase4.input_columns(cfg, assets[0], "full")
    ci = assets[0].cols(cols)
    qcfg = dict(cfg["qagent"])
    mh = int(cfg["policy"]["min_hold_bars"])
    t0 = time.time()
    log("phase 6 models in %s; free %.0f MB" % (root, resources.free_mb() or -1))
    for vname, sh in cfg["phase6"]["variants_train"].items():
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
                W, rec = q_fold6(assets, POOL, ci, geo, cfg["q"], qcfg, cfg["actions"], mh, int(seed) * 1000 + f, sh, pause,
                                 where)
                for a in POOL:
                    _npsave(W[a], os.path.join(d, "w_f%02d_%s.npy" % (f, a)))
                rec.update({"fold": f, "variant": vname, "columns": cols, "geo": geo, "free_mb": resources.free_mb()})
                _jdump(rec, recp)
                log("%s: chosen %s; %s [%.0f min, free %.0f MB]" % (where, rec["chosen"]["shaping_value"], "; ".join(
                    "%s val %+.2f%s" % (a, rec["assets"][a]["val"]["sharpe"], " -> fallback" if rec["assets"][a]["fallback"] else "")
                    for a in POOL), (time.time() - t0) / 60, resources.free_mb() or -1))
                del W
                gc.collect()
        log("%s trained (%.0f min)" % (vname, (time.time() - t0) / 60))
    _jdump({"root": root, "minutes": round((time.time() - t0) / 60, 1), "memory_events": pause.events},
           os.path.join(root, "done.json"))


# ---------------------------------------------------------------- evaluation
def specs(cfg):
    r4, r6 = phase5.root4(cfg), root6(cfg)
    out = {}
    for vn, v in cfg["phase6"]["variants"].items():
        if v["train"] == "phase4_primary":
            out[vn] = {"root": r4, "model": phase5.PRIMARY, "fallback": v["fallback"]}
        else:
            out[vn] = {"root": r6, "model": v["train"], "fallback": v["fallback"]}
    return out


def periods(cfg, bars_btc):
    out = {}
    for name, (a, b) in cfg["phase6"]["downtrends"]["periods"].items():
        if a == "btc_2025_high":
            c = bars_btc["close"]
            y = c[(c.index >= pd.Timestamp("2025-01-01", tz="UTC")) & (c.index < pd.Timestamp("2026-01-01", tz="UTC"))]
            d = y.resample("1D").last().idxmax()
            a = str(d.date())
        out[name] = (pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC"))
    return out


def analytics(cfg, ctx, ex_by_var, sp, pers):
    """Per variant (seed means): time long / short / flat, net and gross P&L a year from long bars and from short bars,
    returns in the downtrend periods, down / up months. HEAD fee; full span and to 2025-11-11."""
    bars, fund = ctx["bars"], ctx["fund"]
    model = costs.from_cfg(cfg)
    n = len(bars)
    lo_o, hi_o = ctx["bounds"][0]["te_lo"], ctx["bounds"][-1]["te_hi"]
    masks = {"full": np.zeros(n, bool), "dev": np.zeros(n, bool)}
    masks["full"][lo_o:hi_o] = True
    masks["dev"][ctx["bounds_dev"][0]["te_lo"]:ctx["bounds_dev"][-1]["te_hi"]] = True
    idx = bars.index
    out = {}
    bh = backtest.run(bars, masks["full"].astype(float), model, fund)["frame"]
    mom_t = np.where(masks["full"], ctx["mom_target"], 0.0)
    mom = backtest.run(bars, mom_t, model, fund)["frame"]
    close = bars["close"]

    def per_frame(fr, m):
        pos, rn, rg = fr["pos"].values, fr["r_net"].values, fr["r_gross"].values
        yrs = m.sum() / 35040.0
        return {"long_share": float(np.mean(pos[m] > 0)), "short_share": float(np.mean(pos[m] < 0)),
                "flat_share": float(np.mean(pos[m] == 0)),
                "net_long_per_year": float(rn[m & (pos > 0)].sum() / yrs), "net_short_per_year": float(rn[m & (pos < 0)].sum() / yrs),
                "gross_long_per_year": float(rg[m & (pos > 0)].sum() / yrs), "gross_short_per_year": float(rg[m & (pos < 0)].sum() / yrs),
                "net_flat_bars_per_year": float(rn[m & (pos == 0)].sum() / yrs)}

    def period_ret(fr, a, b):
        m = (idx >= a) & (idx < b) & masks["full"]
        return float(np.prod(1.0 + fr["r_net"].values[m]) - 1.0) if m.any() else None

    mm = masks["full"]
    mon = pd.DatetimeIndex(idx[mm]).tz_localize(None).to_period("M")
    coin_m = pd.Series(np.log(close.values[mm]), index=mon).groupby(level=0).agg(lambda x: x.iloc[-1] - x.iloc[0])

    def monthly(fr):
        r = pd.Series(np.log1p(fr["r_net"].values[mm]), index=mon).groupby(level=0).sum()
        down = coin_m < 0
        return {"down_months": int(down.sum()), "up_months": int((~down).sum()),
                "mean_down_month_pct": float(100 * (np.exp(r[down]).mean() - 1)) if down.any() else None,
                "mean_up_month_pct": float(100 * (np.exp(r[~down]).mean() - 1)) if (~down).any() else None,
                "share_down_months_profitable": float(np.mean(r[down] > 0)) if down.any() else None}

    ref = {"buy_hold": bh, "momentum": mom}
    for name, fr in ref.items():
        out[name] = {"periods": dict((p, period_ret(fr, a, b)) for p, (a, b) in pers.items()), "monthly": monthly(fr),
                     "full": per_frame(fr, masks["full"]), "dev": per_frame(fr, masks["dev"])}
    for vn, by_seed in ex_by_var.items():
        rows = []
        for s, ex in sorted(by_seed.items()):
            if sp[vn].get("tilt"):
                continue
            fr = backtest.run(bars, np.asarray(ex, float), model, fund)["frame"]
            rows.append({"periods": dict((p, period_ret(fr, a, b)) for p, (a, b) in pers.items()), "monthly": monthly(fr),
                         "full": per_frame(fr, masks["full"]), "dev": per_frame(fr, masks["dev"])})
            del fr
        if not rows:
            continue
        mean = lambda xs: None if any(x is None for x in xs) else float(np.mean(xs))
        agg = {"periods": dict((p, mean([r["periods"][p] for r in rows])) for p in pers),
               "monthly": dict((k, mean([r["monthly"][k] for r in rows])) for k in rows[0]["monthly"]),
               "full": dict((k, mean([r["full"][k] for r in rows])) for k in rows[0]["full"]),
               "dev": dict((k, mean([r["dev"][k] for r in rows])) for k in rows[0]["dev"]),
               "by_seed_periods": [r["periods"] for r in rows]}
        out[vn] = agg
    return out


def run(cfg, log=print):
    check_frozen(cfg)
    t0 = time.time()
    resources.low_priority()
    cfg = copy.deepcopy(cfg)
    seeds = list(cfg["seeds"])
    run_id, run_dir = new_run(cfg, "phase6")
    mem = cfg["phase6"]["memory"]
    pause = resources.MemoryPause(mem["start_mb"], mem["floor_mb"], mem.get("poll_s", 20), log)
    _, fts = phase5._assets_and_folds(cfg)
    sp = specs(cfg)
    log("run %s; variants %s" % (run_id, list(sp)))
    results, anal, pers = {}, {}, None
    for asset in POOL:
        pause.before_start("evaluate " + asset)
        ctx = phase4.asset_ctx(cfg, asset, True, log)
        add_reference(ctx["A"])
        from . import benchmarks
        ctx["mom_target"] = benchmarks.all_targets(ctx["bars"], cfg["benchmarks"])["momentum"].values
        if pers is None:
            pers = periods(cfg, ctx["bars"]) if asset == "BTCUSDT" else None
        res = phase5.evaluate_asset(cfg, ctx, sp, fts, seeds, log, t0, keep_exec=True)
        ex = res.pop("_exec", {})
        anal[asset] = analytics(cfg, ctx, ex, sp, pers)
        del ex
        results[asset] = res
        del ctx
        gc.collect()
    rc = {"primary": cfg["phase6"]["primary"], "variants": sp, "flags": cfg["phase6"]["flags"], "phase6": cfg["phase6"]}
    result = {"run_id": run_id, "generated_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "config": rc,
              "seeds": seeds, "assets": results, "analytics": anal,
              "periods": dict((k, [str(a.date()), str(b)]) for k, (a, b) in pers.items()),
              "elapsed_min": round((time.time() - t0) / 60, 1), "memory_events": pause.events}
    for name in ("phase5_summary.json",):
        p = os.path.join(resolve(cfg["report"]["out_dir"]), name)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                result["phase5"] = json.load(fh)
    done = os.path.join(root6(cfg), "done.json")
    if os.path.exists(done):
        with open(done, encoding="utf-8") as fh:
            result["training_run"] = json.load(fh)
    _jdump(report4.clean(result), os.path.join(run_dir, "phase6_full.json"))
    from . import report6
    out = report6.write(result, resolve(cfg["report"]["out_dir"]), run_dir)
    log("report written: %s (%.0f min)" % (out, (time.time() - t0) / 60))
    return result


def rebuild(cfg, log=print):
    runs = sorted(r for r in glob.glob(os.path.join(resolve(cfg["report"]["runs_dir"]), "phase6_*"))
                  if os.path.exists(os.path.join(r, "phase6_full.json")))
    with open(os.path.join(runs[-1], "phase6_full.json"), encoding="utf-8") as fh:
        result = json.load(fh)
    from . import report6
    return report6.write(result, resolve(cfg["report"]["out_dir"]), None)
