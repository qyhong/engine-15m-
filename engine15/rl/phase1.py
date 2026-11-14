# -*- coding: utf-8 -*-
"""phase1 -- data update -> features -> benchmarks -> walk-forward evaluation -> report."""
import gc
import json
import os
import time

import numpy as np

from . import backtest, benchmarks, costs, data, features, report, walkforward
from .config import new_run, resolve

KEYS = ["total_return", "total_return_gross", "cagr", "sharpe", "sortino", "max_drawdown", "calmar",
        "turnover_per_year", "trades", "avg_holding_hours", "exposure", "cost_drag_per_year",
        "fee_per_year", "spread_per_year", "slippage_per_year", "funding_per_year"]


def _seed_stats(results, names):
    """Random seeds -> mean / sd / min / max of every stitched metric, and per-window means."""
    st = [results[n]["stitched"] for n in names]
    agg = {}
    for k in KEYS:
        v = np.array([s[k] for s in st], dtype=float)
        agg[k] = {"mean": float(v.mean()), "sd": float(v.std(ddof=1)) if len(v) > 1 else 0.0,
                  "min": float(v.min()), "max": float(v.max())}
    nwin = len(results[names[0]]["windows"])
    per = []
    for i in range(nwin):
        w = [results[n]["windows"][i] for n in names]
        row = {"window": i, "test_start": w[0]["test_start"], "test_end": w[0]["test_end"]}
        for k in ("total_return", "sharpe", "max_drawdown"):
            v = np.array([x[k] for x in w], dtype=float)
            row[k] = float(v.mean())
            row[k + "_sd"] = float(v.std(ddof=1)) if len(v) > 1 else 0.0
        per.append(row)
    return {"seeds": len(names), "stitched": agg, "windows": per}


def run(cfg, offline=False, log=print):
    t0 = time.time()
    run_id, run_dir = new_run(cfg, "phase1")
    log("run %s" % run_id)
    bars, fund, drep = data.update_all(cfg, log=log, offline=offline)
    if not len(bars):
        raise SystemExit("no bars stored under %s; run without --offline first" % resolve(cfg["data"]["dir"]))
    log("bars %d (%s .. %s), funding %d rows (%.0fs)" % (len(bars), bars.index[0], bars.index[-1], len(fund), time.time() - t0))

    feats = features.build(bars, fund, cfg["features"])
    n = len(bars)
    cuts = sorted(set(int(c) for c in np.random.default_rng(cfg["seed"]).integers(2000, n - 1, 3)))
    la = features.lookahead_report(lambda b, f: features.build(b, f, cfg["features"]), bars, fund, cuts)
    frep = {"columns": list(feats.columns), "rows": int(len(feats)),
            "first_complete_row": str(feats.dropna().index[0]) if feats.dropna().shape[0] else None,
            "nan_share": dict((c, round(float(feats[c].isna().mean()), 5)) for c in feats.columns),
            "lookahead_check_on_real_data": dict((str(k), v) for k, v in la.items()),
            "open_interest": "live only; OFF in backtests (free history ~30 days)"}
    log("features %s; real-data look-ahead check: %s (%.0fs)" % (len(feats.columns), la, time.time() - t0))
    del feats
    gc.collect()

    wf = cfg["walkforward"]
    wins = walkforward.windows(bars.index, wf["train_months"], wf["test_months"], wf["step_months"], wf["start"],
                               wf["min_test_days"])
    log("walk-forward: %d test windows, %s .. %s" % (len(wins), wins[0]["test_start"].date(), wins[-1]["test_end"].date()))
    targets = benchmarks.all_targets(bars, cfg["benchmarks"])
    profiles = costs.fee_profiles(cfg)
    out = {}
    for pname, model in profiles.items():
        res = {}
        for name, tgt in targets.items():
            st = walkforward.stitch(bars.index, wins, lambda tr, te, t=tgt: t.values[te])
            bt = backtest.run(bars, st, model, fund)
            res[name] = walkforward.evaluate(bt["frame"], wins)
            del bt
        rnames = [k for k in res if k.startswith("random_s")]
        out[pname] = {"model": model.as_dict(), "buy_hold": res["buy_hold"], "momentum": res["momentum"],
                      "random": _seed_stats(res, rnames),
                      "random_seeds": dict((k, res[k]["stitched"]) for k in rnames)}
        log("%s done (%.0fs)" % (pname, time.time() - t0))
        gc.collect()

    result = {"run_id": run_id, "generated_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
              "config": cfg, "data": drep, "features": frep,
              "windows": [dict((k, str(v.date()) if hasattr(v, "date") else v) for k, v in w.items()) for w in wins],
              "results": out, "annualisation": "15m bars, 365 x 96 = 35,040 bars a year"}
    result["flags"] = report.flags(result)
    result["summary"] = report.summary_lines(result)
    out_dir = resolve(cfg["report"]["out_dir"])
    os.makedirs(out_dir, exist_ok=True)
    md = report.markdown(result)
    for d in (out_dir, run_dir):
        with open(os.path.join(d, "phase1_report.json"), "w", encoding="utf-8") as f:
            json.dump(result, f, indent=1, default=str)
        with open(os.path.join(d, "phase1_report.md"), "w", encoding="utf-8") as f:
            f.write(md)
    log("report written: %s (run folder %s) in %.0fs" % (os.path.join(out_dir, "phase1_report.md"), run_dir, time.time() - t0))
    return result
