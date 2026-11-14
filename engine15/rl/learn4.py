# -*- coding: utf-8 -*-
"""learn4 -- Phase 4 step 1: the learnability check again, at the NEW data sizes, before anything touches real data.

Phase 3 found its agent "finds the planted edge unreliably" on 9 months of synthetic 15m data. The question here: does
more data per model fix that? For each seed and scenario, two independent synthetic 15m series (synth.py: fat tails, vol
regimes, funding; the planted AR(1) signal predicts the next bar's return with information coefficient kappa) are built
over 6 years of training + 6 months of validation + a held-out test (12 months; 24 in the power check), with the FULL
Phase 4 input set (Phase 3 features + the engine's build_one readings computed on the synthetic bars + noise standing in
for the basis / Coinbase readings + the availability flags) plus the planted column. The SAME test span of series 1 is
then traded by models trained on three data sizes:

    p3_9m     series 1, the last 9 months before a 3-month validation (Phase 3's geometry and data budget)
    single_3y series 1, 3 years + 6 months validation
    pool2_6y  series 1 AND 2 pooled, 6 years each + 6 months validation (the Phase 4 primary geometry: 12 asset-years)

for both Phase 4 families (models4: SP and Q), with exactly the code the walk-forward uses (selection, refit, 'do no
harm'). Criteria = Phase 3's frozen ones (configs/rl/phase4.yaml learnability.criteria). The power check repeats the
edge / none scenarios with 10 seeds and a 24-month test at p3_9m and pool2_6y.
"""
import json
import os
import time

import numpy as np
import pandas as pd

from . import features4, policy3, qagent, synth
from .costs import CostModel
from .env import Market
from .models4 import policy_metrics, q_fold, sp_fold, sp_target

Y = 35040
M = Y // 12


class MemAsset:
    """An in-memory stand-in for pool4.Asset (synthetic series)."""

    def __init__(self, name, X, rd, t, columns, start=0):
        self.name, self.X, self.rd, self.t, self.columns = name, X, rd, t, columns
        self.n, self.start = len(t), start

    def cols(self, names):
        return np.array([self.columns.index(c) for c in names], dtype=np.intp)


def series(n, seed, kappa, fcfg, qcfg, name):
    bars, fund, pl, info = synth.make(n, seed, kappa)
    rf = features4.synthetic_readings(bars, fund, seed + 77)
    f = features4.build(bars, fund, fcfg, rf)
    f["planted"] = pl
    m = Market(bars, fund, f.astype("float32"), CostModel())
    rd = qagent.reward_arrays(m, qcfg)
    A = MemAsset(name, m.raw, rd, np.asarray(bars.index.as_unit("ms").asi8, dtype=np.int64), list(m.columns))
    return A, pl


def geometry(size, n_total, test_months):
    te_hi = n_total
    te_lo = te_hi - test_months * M
    if size == "p3_9m":
        val = te_lo - 3 * M
        lo = val - 9 * M
    elif size == "single_3y":
        val = te_lo - 6 * M
        lo = val - 36 * M
    elif size == "pool2_6y":
        val = te_lo - 6 * M
        lo = val - 72 * M
    else:
        raise ValueError(size)
    return {"lo": max(0, lo), "val": val, "te_lo": te_lo, "te_hi": te_hi}


def oracle(A, pl, lo, hi, tlo, thi):
    best = None
    for h in (0.5, 1.0, 1.5, 2.0):
        t = synth.oracle_targets(pl, h)
        r = _net(A.rd, t[lo:hi], lo, hi)
        s = policy3.quick_metrics(r, t[lo:hi])["sharpe"]
        if best is None or s > best[0]:
            best = (s, h)
    t = synth.oracle_targets(pl, best[1])
    r = _net(A.rd, t[tlo:thi], tlo, thi)
    out = policy3.quick_metrics(r, t[tlo:thi])
    out["h"] = best[1]
    return out


def _net(rd, tgt, lo, hi):
    a = np.asarray(tgt, float)
    prev = np.concatenate([[0.0], a[:-1]])
    return a * rd["g"][lo:hi] - rd["c1"][lo:hi] * np.abs(a - prev)


def run_one(fam, size, A1, A2, pl, cfg, seed, test_months, pause=None):
    qcfg = dict(cfg["qagent"])
    acts = cfg["actions"]
    mh = int(cfg["policy"]["min_hold_bars"])
    cols = [c for c in A1.columns]                       # every input incl. the planted column
    ci = A1.cols(cols)
    g = geometry(size, A1.n, test_months)
    assets = [A1, A2] if size == "pool2_6y" else [A1]
    geo = dict((A.name, dict(g)) for A in assets)
    if fam == "sp":
        W, rec = sp_fold(assets, [A1.name], ci, geo, cfg["sp"], qcfg, acts, mh, seed * 1000 + 17, pause, "learn")
    else:
        W, rec = q_fold(assets, [A1.name], ci, geo, cfg["q"], qcfg, acts, mh, seed * 1000 + 17, pause, "learn")
    W = W[A1.name]
    fb = rec["assets"][A1.name]["fallback"]
    lo, hi = g["te_lo"], g["te_hi"]
    if fb:
        a = np.asarray(acts, np.float32)
        W = np.repeat((-10.0 * np.abs(a))[None, :], hi - lo, axis=0)
    te = policy_metrics(W, A1.rd, lo, hi, acts, qcfg, mh)
    from .qagent import cost_matrix, q_from_w
    a = np.asarray(acts, float)
    Q = q_from_w(W, A1.rd["k"][lo:hi], A1.rd["c1"][lo:hi], cost_matrix(a), qcfg)
    ip, _ = policy3.decide(Q, a, int(np.argmin(np.abs(a))), mh)
    pos = a[ip]
    corr = float(np.corrcoef(pos, pl[lo:hi])[0, 1]) if np.std(pos) > 0 else 0.0
    orc = oracle(A1, pl, g["lo"], g["val"], lo, hi)
    return {"family": fam, "size": size, "seed": seed, "fallback": bool(fb),
            "train_sharpe": rec["assets"][A1.name]["train"]["sharpe"], "val_sharpe": rec["assets"][A1.name]["val"]["sharpe"],
            "test_sharpe": float(te["sharpe"]), "test_gross_sharpe": float(te["gross_sharpe"]),
            "turnover": float(te["turnover_per_year"]), "exposure": float(te["exposure"]), "corr_with_planted": corr,
            "oracle_sharpe": float(orc["sharpe"]), "chosen": rec.get("chosen"), "seconds": rec.get("seconds"),
            "train_rows": rec.get("rows_refit")}


def summarise(rows):
    if not rows:
        return {}
    f = lambda k: float(np.mean([r[k] for r in rows]))
    found = [r["test_sharpe"] > 0 and r["corr_with_planted"] > 0.1 for r in rows]
    return {"n": len(rows), "test_sharpe_mean": f("test_sharpe"), "test_sharpe_by_seed": [round(r["test_sharpe"], 3) for r in rows],
            "oracle_sharpe_mean": f("oracle_sharpe"), "train_sharpe_mean": f("train_sharpe"), "val_sharpe_mean": f("val_sharpe"),
            "turnover_mean": f("turnover"), "exposure_mean": f("exposure"), "corr_mean": f("corr_with_planted"),
            "fallback_share": float(np.mean([r["fallback"] for r in rows])),
            "found_edge_seeds": int(sum(found)), "test_sharpe_sd": float(np.std([r["test_sharpe"] for r in rows], ddof=1)) if len(rows) > 1 else 0.0}


def judge(summ, crit):
    """Phase 3's frozen criteria for one (family, size): summ = {scenario: summary}."""
    e, z = summ.get(crit["edge_scenario"]), summ.get(crit["none_scenario"])
    out = {}
    if e:
        out["finds_planted_edge"] = bool(e["test_sharpe_mean"] >= crit["edge_min_test_sharpe"]
                                         and e["test_sharpe_mean"] >= crit["edge_min_oracle_share"] * e["oracle_sharpe_mean"])
        out["fits_training_slice"] = bool(e["train_sharpe_mean"] >= crit["min_train_sharpe"])
    if z:
        out["near_flat_without_edge"] = bool(z["test_sharpe_mean"] >= crit["none_min_test_sharpe"]
                                             and z["turnover_mean"] <= crit["none_max_turnover"]
                                             and z["exposure_mean"] <= crit["none_max_exposure"])
    out["pass"] = bool(out) and all(out.values())
    return out


def run(cfg, out_path, log=print, pause=None):
    """Both checks; resumable (finished rows are kept in <out>.partial.jsonl). -> result dict (also written)."""
    lc = cfg["learnability"]
    fcfg = cfg["features"]
    qcfg = cfg["qagent"]
    part = out_path + ".partial.jsonl"
    done = {}
    if os.path.exists(part):
        with open(part, encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                done[(r["check"], r["scenario"], r["seed"], r["size"], r["family"])] = r
    t0 = time.time()
    plans = [("main", lc["scenarios"], lc["seeds"], lc["sizes"], int(lc["test_months"]), int(lc["seed_base"]))]
    pw = lc["power"]
    plans.append(("power", dict((k, lc["scenarios"][k]) for k in pw["scenarios"]), list(range(int(pw["seeds"]))),
                  pw["sizes"], int(pw["test_months"]), int(pw["seed_base"])))
    for check, scen, seeds, sizes, tm, base in plans:
        n_total = int((72 + 6 + tm) * M)
        for sname, kappa in scen.items():
            for s in seeds:
                need = [(sz, fam) for sz in sizes for fam in lc["families"] if (check, sname, s, sz, fam) not in done]
                if not need:
                    continue
                if pause is not None:
                    pause.before_start("learnability %s %s seed %d" % (check, sname, s))
                ts = time.time()
                A1, pl = series(n_total, base + s, float(kappa), fcfg, qcfg, "S1")
                A2 = None
                if any(sz == "pool2_6y" for sz, _ in need):
                    A2, _ = series(n_total, base + 500 + s, float(kappa), fcfg, qcfg, "S2")
                tb = time.time() - ts
                for sz, fam in need:
                    r = run_one(fam, sz, A1, A2, pl, cfg, s, tm, pause)
                    r.update({"check": check, "scenario": sname, "kappa": float(kappa)})
                    done[(check, sname, s, sz, fam)] = r
                    with open(part, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps(r, default=str) + "\n")
                    log("  %s %s seed %d %s %s: train %+.2f val %+.2f test %+.2f (gross %+.2f, turnover %.0f/yr, exposure %.0f%%, corr %.2f%s) oracle %+.2f [%.0fs]"
                        % (check, sname, s, sz, fam, r["train_sharpe"], r["val_sharpe"], r["test_sharpe"], r["test_gross_sharpe"],
                           r["turnover"], 100 * r["exposure"], r["corr_with_planted"], ", neutral" if r["fallback"] else "",
                           r["oracle_sharpe"], r["seconds"] or 0))
                log("  (series built in %.0fs; %.0f min so far)" % (tb, (time.time() - t0) / 60))
                del A1, A2
    res = {"criteria": lc["criteria"], "families": lc["families"], "sizes": lc["sizes"], "main": {}, "power": {},
           "rows": list(done.values())}
    for check in ("main", "power"):
        for fam in lc["families"]:
            for sz in (lc["sizes"] if check == "main" else pw["sizes"]):
                summ = {}
                for sname in (lc["scenarios"] if check == "main" else pw["scenarios"]):
                    rows = sorted([r for k, r in done.items() if k[0] == check and k[1] == sname and k[3] == sz and k[4] == fam],
                                  key=lambda r: r["seed"])
                    summ[sname] = summarise(rows)
                res[check]["%s/%s" % (fam, sz)] = {"summary": summ, "judge": judge(summ, lc["criteria"])}
    res["minutes"] = round((time.time() - t0) / 60, 1)
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)
    os.replace(tmp, out_path)
    return res
