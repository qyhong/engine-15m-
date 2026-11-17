# -*- coding: utf-8 -*-
"""RL loop round 4: the gate, the evaluation and the report (called by round4.py --check / --eval / --report). Paper only.

Same frame as rounds 1-3 (round1.py functions reused). Stage 1 (--check) computes only the Phase 6 primary (rule 3) and
round 3's R3-b / R3-c / R3-d and compares them with the saved runs; stage 2 (--eval) refuses to start unless that gate
passed, then computes the two registered variants R4-a, R4-b beside the same reference and comparison rows."""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import round1 as R1  # noqa: E402
import round3 as R3  # noqa: E402
import round3_eval as R3E  # noqa: E402
import round4 as R4  # noqa: E402

log = R1.log
SEEDS, POOL, REF = R1.SEEDS, R1.POOL, R1.REF
H = "fee_0.10%"
TOL_RET, TOL_SH = 0.005, 0.005


def _setup_r1(variants):
    """round1's grading / table helpers read module globals: point them at round 4."""
    R1.N_CUM = R4.N_CUM
    R1.ROUND_VARIANTS = list(variants)
    R1.LABELS = R4.LABELS
    R1.P6_FULL = R4.p6_full_path()


def requests4(dec, mk_, seed, mh, mom, rule):
    """Request series for one variant and seed. dec[(models, seed, min hold)] = (decided action series, stats)."""
    if rule in ("committee125", "committee4"):
        b1 = (np.sign(dec[("p6", seed, mh)][0]) <= 0).astype(int)
        b2 = (np.sign(dec[("r2", seed, mh)][0]) <= 0).astype(int)
        bm = (mom == -1).astype(int)
        if rule == "committee125":
            return np.where(b1 + b2 + bm >= 2, 0.0, 1.25)
        b3 = (np.sign(dec[("r3", seed, mh)][0]) == 0).astype(int)
        return np.where(b1 + b2 + b3 + bm >= 3, 0.0, 1.0)
    return R3E.requests3(dec, mk_, seed, mh, mom, rule)


def halves(book, r_bhs, idx, oos, core):
    """Reported only: the seed-mean book against spot buy-and-hold in each half of the span split at R4.HALF_SPLIT."""
    cut = pd.Timestamp(R4.HALF_SPLIT, tz=idx.tz)
    out = {}
    for nm, msk in (("first", oos & np.asarray(idx < cut)), ("second", oos & np.asarray(idx >= cut))):
        o, p, se = core.boot_sharpe_diff_z(book[msk], r_bhs[msk], idx[msk])
        out[nm] = {"sharpe_minus_bh": o, "p": p, "se": se, "book_sharpe": float(core.metrics.sharpe(book[msk])),
                   "bh_sharpe": float(core.metrics.sharpe(r_bhs[msk])),
                   "book_return": float(np.prod(1 + book[msk]) - 1), "bh_return": float(np.prod(1 + r_bhs[msk]) - 1)}
    return out


def compute(stage):
    from engine15.rl import backtest, baselines3, benchmarks, costs, phase4, phase5, phase6, policy3, pool4, report4, resources
    from engine15.rl.continual import q_of
    from engine15.rl.learn6 import add_reference
    from engine15.rl.phase3 import evaluate_target
    from research.harness import core
    assert stage in ("check", "eval")
    variants = list(R4.COMPARE) + (list(R4.ROUND_VARIANTS) if stage == "eval" else [])
    _setup_r1(variants)
    resources.low_priority()
    pause = resources.MemoryPause(R4.START_MB, R4.FLOOR_MB, 20, log)
    t0 = time.time()
    cfg = phase6.load_cfg()                                    # a deep copy: the change below stays in this process
    p6root = phase6.root6(cfg)
    assert os.path.basename(p6root) == "b6a25c5d", p6root
    cache = R4.cache_dir(pool4.cache_dir(cfg))
    cfg["report"]["cache_dir"] = cache
    out = {"generated_utc": None, "stage": stage, "n_cum": R4.N_CUM, "assets": {}, "checks": {}, "agent": {},
           "cache_dir": os.path.relpath(cache, R1.ROOT), "host": "laptop (Windows)" if sys.platform == "win32" else "research server (Linux)"}
    store_meta = {}
    for asset in POOL:                                         # rebuild the input cache only if it is missing
        built = not os.path.exists(os.path.join(cache, asset, "meta.json"))
        if built:
            assert stage == "check", "the input cache must be built by --check, before any round-4 variant is computed"
            from engine15.rl import features4
            mp = os.path.join(features4.store_path(asset), "meta.json")
            m0 = os.path.getmtime(mp)
            pause.before_start("cache " + asset)
            log("%s: building the input cache in %s" % (asset, cache))
            pool4.prepare(cfg, asset, offline=True, log=log)
            store_meta[asset] = {"store_meta_mtime_before": m0, "store_meta_mtime_after": os.path.getmtime(mp)}
        snap = os.path.join(cache, "readings_%s.npz" % asset)
        if os.path.exists(snap):
            z = np.load(snap, allow_pickle=False)
            sm = json.loads(str(z["meta"]))
            sm.pop("columns", None)
            sm["built_this_call"] = bool(built)
            sm.update(store_meta.get(asset, {}))
            out["checks"]["readings_snapshot_%s" % asset] = sm
    acts5 = np.asarray(cfg["actions"], float)
    acts3 = np.asarray(R3.ACTS3, float)
    mr = R4.model_roots(p6root)
    roots = {"p6": mr["p6"] + (acts5,), "r2": mr["r2"] + (acts5,), "r3": mr["r3"] + (acts3,)}
    out["model_roots"] = dict((k, os.path.relpath(v[0], R1.ROOT)) for k, v in roots.items())
    out["p6_full"] = os.path.relpath(R1.P6_FULL, R1.ROOT)
    _, fts = phase5._assets_and_folds(cfg)
    for mk_ in ("p6", "r2", "r3"):
        root, vname, _ = roots[mk_]
        for s in SEEDS:
            for ft in fts:
                assert R3._fold_done(os.path.join(root, vname, "s%s" % s), ft["i"]), ("models incomplete", mk_, s, ft["i"])
    rcfg = dict(cfg["risk3"])
    profiles = costs.fee_profiles(cfg)
    head = report4.HEAD
    assert head == H
    for asset in POOL:
        pause.before_start("load " + asset)
        log("%s: loading context" % asset)
        ctx = phase4.asset_ctx(cfg, asset, True, log)
        A, bars = ctx["A"], ctx["bars"]
        add_reference(A)
        mom = np.nan_to_num(np.asarray(A.rd["ref"], float), nan=0.0)
        assert set(np.unique(mom)).issubset({-1.0, 0.0, 1.0}), np.unique(mom)
        n = len(bars)
        idx = bars.index
        lo_o, hi_o = ctx["bounds"][0]["te_lo"], ctx["bounds"][-1]["te_hi"]
        oos = np.zeros(n, bool)
        oos[lo_o:hi_o] = True
        dec, fb_mask, agent = {}, {}, {}
        for mk_ in ("p6", "r2", "r3"):
            root, vname, acts = roots[mk_]
            zero = int(np.argmin(np.abs(acts)))
            for seed in SEEDS:
                pause.check("decide %s %s s%s" % (mk_, asset, seed))
                W, lo, hi, recs = phase5.oos_w(root, vname, int(seed), fts, A, list(acts), None, "trend")
                assert (lo, hi) == (lo_o, hi_o)
                rd = dict((k, np.asarray(v)) for k, v in A.rd.items())
                Q = q_of(W, rd, lo, hi, dict(cfg["qagent"]), list(acts))
                prepared = policy3.prepare(Q)
                for mh in ((4, 16) if mk_ == "p6" else (16,)):
                    ip, st = policy3.decide(Q, acts, zero, mh, prepared=prepared)
                    t = np.zeros(n)
                    t[lo:hi] = acts[ip]
                    dec[(mk_, seed, mh)] = (t, st)
                fbm = np.zeros(n, bool)
                for ft, r in zip(fts, recs):
                    if r["assets"][asset]["fallback"]:
                        fbm[A.at(ft["test_start"]):A.at(ft["test_end"])] = True
                fb_mask[(mk_, seed)] = fbm
                d16 = dec[(mk_, seed, 16)][0][lo:hi]
                agent[(mk_, seed)] = {"fallback_folds": [int(ft["i"]) for ft, r in zip(fts, recs) if r["assets"][asset]["fallback"]],
                                      "fallback_share": float((fbm & oos).sum() / oos.sum()),
                                      "beta": [r["chosen"]["shaping_value"] for r in recs],
                                      "val_sharpe_mean": float(np.mean([r["assets"][asset]["val"]["sharpe"] for r in recs])),
                                      "long_share_decided": float(np.mean(d16 > 0)),
                                      "short_share_decided": float(np.mean(d16 < 0)),
                                      "flat_share_decided": float(np.mean(d16 == 0))}
                del Q, W, prepared, rd
        out["agent"][asset] = dict(("%s_s%s" % k, v) for k, v in agent.items())
        out["checks"]["trend_down_share_%s" % asset] = float(np.mean(mom[oos] == -1))
        log("%s: decisions done (%.1f min)" % (asset, (time.time() - t0) / 60))
        res = {"fees": {}, "years": {}, "sides": {}, "decision_stats": {}, "book": {}, "flat_share": {}, "halves": {}}
        for vn in variants:
            mk1 = R4.EXEC[vn][0].split("+")[0]
            res["decision_stats"][vn] = dict((s, dec[(mk1, s, R4.EXEC[vn][1])][1]) for s in SEEDS)
        res["decision_stats"][REF] = dict((s, dec[("p6", s, 4)][1]) for s in SEEDS)
        btg = benchmarks.all_targets(bars, cfg["benchmarks"])
        for pname, model in profiles.items():
            mk = ctx["market"].with_model(model)
            fees = {"bench": {}, "variants": {}}
            fr_bhs = baselines3.spot_frame(ctx["smkt"], np.where(oos, 1.0, 0.0), model.fee_side, True)
            fr_bhp = backtest.run(bars, np.where(oos, 1.0, 0.0), model, ctx["fund"])["frame"]
            fr_mom = backtest.run(bars, np.where(oos, btg["momentum"].values, 0.0), model, ctx["fund"])["frame"]
            bm = {}
            for bn, fr, ex in (("buy_hold_spot", fr_bhs, np.where(oos, 1.0, 0.0)), ("buy_hold_perp", fr_bhp, np.where(oos, 1.0, 0.0)),
                               ("momentum", fr_mom, np.where(oos, btg["momentum"].values, 0.0))):
                bm[bn] = {"full": R1.frame_metrics(fr, ctx, ex, None, "full"), "dev": R1.frame_metrics(fr, ctx, ex, None, "dev")}
                if pname == head:
                    res["years"][bn] = R1.years_of(fr["r_net"].values, idx, oos)
                    res["sides"][bn] = R1.side_split(fr, oos)
            fees["bench"] = bm
            bhsh = {"full": bm["buy_hold_spot"]["full"]["stitched"]["sharpe"], "dev": bm["buy_hold_spot"]["dev"]["stitched"]["sharpe"]}
            r_bhs = fr_bhs["r_net"].values.copy()
            del fr_bhp, fr_mom
            # rule 3: Phase 6's own path
            pause.check("reference %s %s" % (asset, pname))
            vr, rnets = {}, {}
            for seed in SEEDS:
                tgt = dec[("p6", seed, 4)][0]
                e = evaluate_target(ctx, tgt, model, 1.0, True, bh=None)
                ex = np.asarray(e["risk"]["exec"], float)
                fr = backtest.run(bars, ex, model, ctx["fund"])["frame"]
                vr[seed] = {"full": R1.frame_metrics(fr, ctx, ex, bhsh["full"], "full"),
                            "dev": R1.frame_metrics(fr, ctx, ex, bhsh["dev"], "dev"), "risk_counts": e["risk"]["counts"]}
                if seed == "0":
                    mine, _ = R1.risk_run(mk, tgt, lo_o, hi_o, rcfg, 0.20, False, 1.0)
                    out["checks"]["risk_run_equals_risk3_%s_%s" % (asset, pname)] = float(np.max(np.abs(mine - ex)))
                if pname == head:
                    rnets[seed] = fr["r_net"].values.copy()
                    res["years"].setdefault(REF, {})[seed] = R1.years_of(fr["r_net"].values, idx, oos)
                    res["sides"].setdefault(REF, {})[seed] = R1.side_split(fr, oos)
                del fr, e
            fees["variants"][REF] = vr
            if pname == head:
                res["book"][REF] = R1.book_stats(rnets, r_bhs, idx, oos, core, dict((s, fb_mask[("p6", s)]) for s in SEEDS))
                bk = np.mean([rnets[s] for s in SEEDS], axis=0)
                res["book"][REF]["corr_bh_daily"], res["book"][REF]["te_bh_ann"] = R3E.daily_corr(bk, r_bhs, idx, oos)
                res["halves"][REF] = halves(bk, r_bhs, idx, oos, core)
            for vn in variants:
                mk_, mh, band, rule = R4.EXEC[vn]
                pause.check("%s %s %s" % (vn, asset, pname))
                mk1 = mk_.split("+")[0]
                vr, rnets = {}, {}
                for seed in SEEDS:
                    req = requests4(dec, mk_, seed, mh, mom, rule)
                    req = np.where(oos, req, 0.0)
                    if pname == head:
                        res["flat_share"].setdefault(vn, {})[seed] = float(np.mean(req[oos] == 0))
                    ex, cnt = R1.risk_run(mk, req, lo_o, hi_o, rcfg, band, True, 1.5)
                    fr = baselines3.spot_frame(ctx["smkt"], ex, model.fee_side, True)
                    vr[seed] = {"full": R1.frame_metrics(fr, ctx, ex, bhsh["full"], "full"),
                                "dev": R1.frame_metrics(fr, ctx, ex, bhsh["dev"], "dev"), "risk_counts": cnt}
                    if pname == head:
                        rnets[seed] = fr["r_net"].values.copy()
                        res["years"].setdefault(vn, {})[seed] = R1.years_of(fr["r_net"].values, idx, oos)
                        res["sides"].setdefault(vn, {})[seed] = R1.side_split(fr, oos)
                    del fr
                fees["variants"][vn] = vr
                if pname == head:
                    fbm_v = dict((s, fb_mask[(mk1, s)]) for s in SEEDS)
                    res["book"][vn] = R1.book_stats(rnets, r_bhs, idx, oos, core, fbm_v)
                    bk = np.mean([rnets[s] for s in SEEDS], axis=0)
                    res["book"][vn]["corr_bh_daily"], res["book"][vn]["te_bh_ann"] = R3E.daily_corr(bk, r_bhs, idx, oos)
                    res["halves"][vn] = halves(bk, r_bhs, idx, oos, core)
                log("%s %s: %s done (%.1f min, free %.0f MB)" % (asset, pname, R4.SHORT[vn], (time.time() - t0) / 60,
                                                                  resources.free_mb() or -1))
            res["fees"][pname] = fees
        out["assets"][asset] = res
        del ctx, A, bars, dec
        import gc
        gc.collect()
    out["generated_utc"] = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    out["elapsed_min"] = round((time.time() - t0) / 60, 1)
    out["memory_events"] = pause.events
    return out


# ---------------------------------------------------------------- the gate (stage 1)
def gate(res):
    """(i) rule 3 against Phase 6's saved run; (ii) R3-b / R3-c / R3-d against round 3's saved results."""
    sv = R1.seedvals
    with open(R4.p6_full_path(), encoding="utf-8") as fh:
        p6 = json.load(fh)
    g = {"tolerance": {"return": TOL_RET, "sharpe": TOL_SH}, "rule3": {}, "compare": [], "risk_run": {}}
    for a in POOL:
        p6v = p6["assets"][a]["fees"][H]["variants"]["m_trend"]["seeds"]
        rf = res["assets"][a]["fees"][H]["variants"][REF]
        new_r, old_r = float(np.mean(sv(rf, "full", "total_return"))), float(np.mean([p6v[s]["stitched"]["total_return"] for s in SEEDS]))
        new_s, old_s = float(np.mean(sv(rf, "full", "sharpe"))), float(np.mean([p6v[s]["stitched"]["sharpe"] for s in SEEDS]))
        g["rule3"][a] = {"return_new": new_r, "return_saved": old_r, "sharpe_new": new_s, "sharpe_saved": old_s,
                         "d_return_abs": abs(new_r - old_r), "d_sharpe": abs(new_s - old_s),
                         "max_seed_d_return_abs": float(max(abs(rf[s]["full"]["stitched"]["total_return"] - p6v[s]["stitched"]["total_return"]) for s in SEEDS)),
                         "max_seed_d_sharpe": float(max(abs(rf[s]["full"]["stitched"]["sharpe"] - p6v[s]["stitched"]["sharpe"]) for s in SEEDS))}
    b3 = g["rule3"]["BTCUSDT"]
    g["rule3_ok"] = bool(b3["d_return_abs"] < TOL_RET and b3["d_sharpe"] < TOL_SH)
    with open(R4.R3_RES, encoding="utf-8") as fh:
        r3 = json.load(fh)
    ok2 = True
    for vn in R4.COMPARE:
        for a in POOL:
            new = res["assets"][a]["fees"][H]["variants"][vn]
            old = r3["assets"][a]["fees"][H]["variants"][vn]
            nr, orr = float(np.mean(sv(new, "full", "total_return"))), float(np.mean(sv(old, "full", "total_return")))
            ns, os_ = float(np.mean(sv(new, "full", "sharpe"))), float(np.mean(sv(old, "full", "sharpe")))
            row = {"variant": vn, "asset": a, "return_new": nr, "return_saved": orr, "sharpe_new": ns, "sharpe_saved": os_,
                   "d_return_rel": abs(nr - orr) / abs(orr), "d_sharpe": abs(ns - os_),
                   "max_seed_d_return_abs": float(max(abs(new[s]["full"]["stitched"]["total_return"] - old[s]["full"]["stitched"]["total_return"]) for s in SEEDS)),
                   "max_seed_d_sharpe": float(max(abs(new[s]["full"]["stitched"]["sharpe"] - old[s]["full"]["stitched"]["sharpe"]) for s in SEEDS))}
            row["ok"] = bool(row["d_return_rel"] < TOL_RET and row["d_sharpe"] < TOL_SH)
            ok2 = ok2 and row["ok"]
            g["compare"].append(row)
    g["compare_ok"] = bool(ok2)
    g["risk_run"] = dict((k, v) for k, v in res["checks"].items() if k.startswith("risk_run"))
    g["gate_ok"] = bool(g["rule3_ok"] and g["compare_ok"])
    return g


def gate_lines(g):
    L = []
    for a in POOL:
        r = g["rule3"][a]
        L.append("Phase 6 primary %s: return %+.4f%% (saved %+.4f%%), Sharpe %.4f (saved %.4f); max per-seed difference: "
                 "return %.2e, Sharpe %.2e" % (a, 100 * r["return_new"], 100 * r["return_saved"], r["sharpe_new"],
                                              r["sharpe_saved"], r["max_seed_d_return_abs"], r["max_seed_d_sharpe"]))
    for r in g["compare"]:
        L.append("%s %s: return %+.4f%% (round 3 saved %+.4f%%, relative difference %.2e), Sharpe %.4f (saved %.4f, "
                 "difference %.2e); max per-seed difference: return %.2e, Sharpe %.2e -> %s" % (
                     R4.SHORT[r["variant"]], r["asset"], 100 * r["return_new"], 100 * r["return_saved"], r["d_return_rel"],
                     r["sharpe_new"], r["sharpe_saved"], r["d_sharpe"], r["max_seed_d_return_abs"], r["max_seed_d_sharpe"],
                     "ok" if r["ok"] else "DIFFERENT"))
    return L


def check():
    R1.acquire_lock("rl_loop round 4 gate (stage 1)")
    try:
        res = compute("check")
    finally:
        R1.release_lock()
    res = json.loads(json.dumps(R1.clean(res)))
    os.makedirs(R4.WORK, exist_ok=True)
    with open(os.path.join(R4.WORK, "round4_check_results.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    g = gate(res)
    g.update({"generated_utc": res["generated_utc"], "elapsed_min": res["elapsed_min"], "host": res["host"],
              "cache_dir": res["cache_dir"], "model_roots": res["model_roots"], "p6_full": res["p6_full"],
              "snapshots": dict((k, v) for k, v in res["checks"].items() if k.startswith("readings_snapshot"))})
    with open(R4.CHECK, "w", encoding="utf-8") as fh:
        json.dump(R1.clean(g), fh, indent=1)
    for line in gate_lines(g):
        log("gate: " + line)
    log("gate: rule 3 %s; round-3 rows %s -> %s" % ("OK" if g["rule3_ok"] else "FAILED", "OK" if g["compare_ok"] else "FAILED",
                                                  "GATE PASSED: stage 2 may run" if g["gate_ok"] else
                                                  "GATE FAILED: round 4 is NOT RUN (no round-4 variant was computed)"))
    return g


# ---------------------------------------------------------------- report
def report(res):
    _setup_r1(R4.COMPARE + R4.ROUND_VARIANTS)
    ALL = [REF] + R4.COMPARE + R4.ROUND_VARIANTS
    fl = R1.floors()
    G = dict((vn, R1.grade(res, vn, fl)) for vn in ALL)
    g = gate(res)
    with open(R4.CHECK, encoding="utf-8") as fh:
        g1 = json.load(fh)
    b, e = res["assets"]["BTCUSDT"], res["assets"]["ETHUSDT"]
    sv = R1.seedvals
    pct = R1.pct
    L = []
    w = L.append
    w("# RL loop round 4: the committee at 1.25, and a four-vote committee")
    w("")
    w("Generated %s. Paper only. Rules: `research/rl_loop/LOOP_RL.md` (frozen 13 Nov 2026 04:10 UTC; round 4 registered "
      "17 Nov 2026 03:21 UTC, before any round-4 code was written). Seeds 0, 1, 2; 25 walk-forward folds, out of sample "
      "2020-10-01 .. 2026-11-11. Both variants are execution-only: R4-a uses Phase 6's trained `m_trend` models with round "
      "2's `r_missed_spot`; R4-b uses those and round 3's `r_missed_longflat`; nothing was retrained. **RL variants tried, "
      "cumulative: %d** (Phase 6's 8 + round 1's 5 + round 2's 6 + round 3's 4 + round 4's 2). Evaluation compute: %.1f min "
      "(host `%s`)." % (res["generated_utc"], R4.N_CUM, res["elapsed_min"], res.get("host")))
    w("")
    w("**Honesty.** No historical span is unseen for RL (Phase 4-6 scored every window; this loop was designed after Phase 6's "
      "and rounds 1-3's per-fold results; the trend fallback was chosen with hindsight). A pass would not be proof of an edge, "
      "only a proposal for a forward paper book, confirmed at 30 forward trades. Spot longs = long part up to 1x as spot "
      "(no funding); exposure above 1x and shorts are perp. Leverage (R4-a and R3-b* request 1.25) raises return and drawdown "
      "together and leaves Sharpe unchanged only before costs; after fees, slippage and funding on the part above 1x it "
      "lowers Sharpe unless the extra exposure sits where the edge is larger.")
    w("")
    w("**Where it ran, and the inputs.** Rounds 1-3 ran on the laptop; its RL input cache and evidence store were deleted in "
      "the owner-approved cleanup. Round 4 ran on the research server: input cache `%s` rebuilt by the unchanged "
      "`engine15.rl.pool4.prepare` from the server's bar and funding files (cut at 2026-11-11 11:30) and the server's "
      "evidence store (read only); trained fold models %s and Phase 6's saved run `%s` copied from the laptop." % (
          res["cache_dir"], ", ".join("`%s`" % v for v in res["model_roots"].values()), res["p6_full"]))
    for a in POOL:
        sm = res["checks"].get("readings_snapshot_%s" % a) or g1.get("snapshots", {}).get("readings_snapshot_%s" % a)
        if sm:
            w("- Readings snapshot %s: %s rows, %s .. %s, evidence store created %s, read %s UTC." % (
                a, sm.get("rows"), sm.get("first"), sm.get("last"), sm.get("store_created"), sm.get("read_utc")))
    w("")
    w("**Gate, stage 1 (run %s, before any round-4 variant was computed): %s.**" % (
        g1.get("generated_utc"), "PASSED" if g1.get("gate_ok") else "FAILED"))
    for line in gate_lines(g1):
        w("- " + line)
    w("")
    ck = res["checks"]
    rf = b["fees"][H]["variants"][REF]
    r3b = g["rule3"]["BTCUSDT"]
    repro_ok = bool(g["rule3_ok"])
    w("**Reproduction check (rule 3), this run.** Phase 6 primary through this harness: BTC %s, Sharpe %.3f (Phase 6: +458.6%%, "
      "0.87); ETH %s, Sharpe %.3f (+709.1%%, 0.96); differences vs Phase 6's saved run (BTC seed mean): return %.2e, Sharpe "
      "%.2e -> %s. Round 3's R3-b / R3-c / R3-d against round 3's saved results in this run: %s (largest relative return "
      "difference %.2e, largest Sharpe difference %.2e). risk_run vs risk3.apply max |difference|: %s." % (
          pct(np.mean(sv(rf, "full", "total_return"))), np.mean(sv(rf, "full", "sharpe")),
          pct(np.mean(sv(e["fees"][H]["variants"][REF], "full", "total_return"))),
          np.mean(sv(e["fees"][H]["variants"][REF], "full", "sharpe")), r3b["d_return_abs"], r3b["d_sharpe"],
          "OK" if repro_ok else "FAILED: the round stops (rule 3)", "OK" if g["compare_ok"] else "DIFFERENT",
          max(r["d_return_rel"] for r in g["compare"]), max(r["d_sharpe"] for r in g["compare"]),
          ", ".join("%s %.1e" % (k.replace("risk_run_equals_risk3_", ""), v) for k, v in ck.items() if k.startswith("risk_run"))))
    w("")
    w("Floors applied (max of the quoted value and the unrounded Phase 6 seed mean): BTC full %.4f, BTC to 2025-11-11 %.4f, "
      "ETH full %.4f." % (fl["btc_full"], fl["btc_dev"], fl["eth_full"]))
    w("")
    w("## Verdict")
    w("")
    graded = repro_ok and g["compare_ok"]
    passed = [vn for vn in R4.ROUND_VARIANTS if G[vn]["pass"]] if graded else []
    if not graded:
        w("**STOPPED: the harness does not reproduce the saved runs; no variant is graded.**")
    elif passed:
        w("**PASS (historical, not proof): %s.** Proposed for a forward paper book (the session lead and the owner decide)." %
          ", ".join(R4.LABELS[p] for p in passed))
    else:
        w("**No pass in round 4.**")
        for vn in R4.ROUND_VARIANTS:
            fails = [k for k, ok in G[vn]["rules"].items() if not ok]
            w("- %s: %d of %d rules; fails %s." % (R4.LABELS[vn], G[vn]["met"], G[vn]["of"], ", ".join("`%s`" % f for f in fails)))
    w("")
    w("## Headline: BTC and ETH, full span, 0.10% a side, seed means, against spot buy-and-hold")
    w("")
    w("| Variant | BTC return | BTC mean CAGR | BTC Sharpe (seeds) | BTC max DD (worst seed) | BTC trades/yr (max seed) | "
      "BTC to 2025-11-11: return / Sharpe | ETH return | ETH Sharpe | ETH max DD (worst) | Rules met |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    for vn in ALL:
        vb, ve = b["fees"][H]["variants"][vn], e["fees"][H]["variants"][vn]
        sh = sv(vb, "full", "sharpe")
        w("| %s | %s | %s | %.2f (%s) | %.0f%% (%.0f%%) | %.0f (%.0f) | %s / %.2f | %s | %.2f | %.0f%% (%.0f%%) | %d / %d |" % (
            R4.LABELS[vn], pct(np.mean(sv(vb, "full", "total_return"))), pct(np.mean(sv(vb, "full", "cagr"))),
            np.mean(sh), ", ".join("%.2f" % x for x in sh), 100 * np.mean(sv(vb, "full", "max_drawdown")),
            100 * max(sv(vb, "full", "max_drawdown")), np.mean(sv(vb, "full", "trades_per_year")),
            max(sv(vb, "full", "trades_per_year")), pct(np.mean(sv(vb, "dev", "total_return"))),
            np.mean(sv(vb, "dev", "sharpe")), pct(np.mean(sv(ve, "full", "total_return"))),
            np.mean(sv(ve, "full", "sharpe")), 100 * np.mean(sv(ve, "full", "max_drawdown")),
            100 * max(sv(ve, "full", "max_drawdown")), G[vn]["met"], G[vn]["of"]))
    for a, lab in (("BTCUSDT", "BTC"), ("ETHUSDT", "ETH")):
        st = res["assets"][a]["fees"][H]["bench"]["buy_hold_spot"]["full"]["stitched"]
        sd = res["assets"][a]["fees"][H]["bench"]["buy_hold_spot"]["dev"]["stitched"]
        w("| %s spot buy-and-hold | %s | %s | %.2f | %.0f%% | 0 | %s / %.2f | | | | |" % (
            lab, pct(st["total_return"]), pct(st["cagr"]), st["sharpe"], 100 * st["max_drawdown"], pct(sd["total_return"]), sd["sharpe"]))
    w("")
    w("REF = Phase 6 as it is (perp accounting); R3-b*, R3-c* and R3-d* (round 3) recomputed in this run: the gate's rows, "
      "shown for comparison, graded here with N = %d for information, not round-4 variants and not counted again." % R4.N_CUM)
    w("")
    w("## Every rule, every variant (PASS / fail)")
    w("")
    keys = list(G[R4.ROUND_VARIANTS[0]]["rules"])
    w("| Rule | " + " | ".join(R4.SHORT[vn] for vn in ALL) + " |")
    w("|---|" + "---|" * len(ALL))
    for k in keys:
        w("| `%s` | " % k + " | ".join("PASS" if G[vn]["rules"][k] else "fail" for vn in ALL) + " |")
    w("| rules met | " + " | ".join("%d / %d" % (G[vn]["met"], G[vn]["of"]) for vn in ALL) + " |")
    w("| fold share (seed-mean per fold), full / to 2025-11-11 | " + " | ".join(
        "%.0f%% / %.0f%%" % (100 * G[vn]["fold_share"], 100 * G[vn]["fold_share_dev"]) for vn in ALL) + " |")
    w("| fold share by seed 0 / 1 / 2 | " + " | ".join(
        " / ".join("%.0f%%" % (100 * G[vn]["fold_share_by_seed"][s]) for s in SEEDS) for vn in ALL) + " |")
    w("| seed-mean book Sharpe - B&H (p; threshold %.5f) | " % (0.05 / R4.N_CUM) + " | ".join(
        "%+.2f (p %.4f)" % (b["book"][vn]["sharpe_minus_bh"], b["book"][vn]["p"]) for vn in ALL) + " |")
    w("| bootstrap standard error of that gap | " + " | ".join("%.2f" % b["book"][vn]["se"] for vn in ALL) + " |")
    w("| Sharpe edge needed at that threshold / with the strategy loop's 1,910 added | " + " | ".join(
        "%.2f / %.2f" % (b["book"][vn]["edge_needed"], b["book"][vn]["edge_needed_with_strategy_loop"]) for vn in ALL) + " |")
    w("| daily correlation with B&H / tracking error a year (seed-mean book) | " + " | ".join(
        "%.2f / %.0f%%" % (b["book"][vn]["corr_bh_daily"], 100 * b["book"][vn]["te_bh_ann"]) for vn in ALL) + " |")
    w("| deflated-Sharpe probability (N = %d) | " % R4.N_CUM + " | ".join("%.3f" % b["book"][vn]["dsr"] for vn in ALL) + " |")
    for nm, lab in (("first", "first half, to %s" % R4.HALF_SPLIT), ("second", "second half, from %s" % R4.HALF_SPLIT)):
        w("| reported, not a rule: book Sharpe - B&H, %s (p; book return vs B&H) | " % lab + " | ".join(
            "%+.2f (p %.3f; %s vs %s)" % (b["halves"][vn][nm]["sharpe_minus_bh"], b["halves"][vn][nm]["p"],
                                           pct(b["halves"][vn][nm]["book_return"], 0), pct(b["halves"][vn][nm]["bh_return"], 0))
            for vn in ALL) + " |")
    w("")
    w("Bootstrap on daily returns of the seed-mean book (per-bar mean of the three seeds' net returns) against spot "
      "buy-and-hold, BTC full span; Bonferroni over %d RL variants (p <= %.5f; with the strategy loop's 1,910 added: %.1e). "
      "REF and the comparison rows are graded here with N = %d for information only." % (
          R4.N_CUM, 0.05 / R4.N_CUM, 0.05 / (R4.N_CUM + R1.N_STRATEGY_LOOP), R4.N_CUM))
    w("")
    bh = b["fees"][H]["bench"]["buy_hold_spot"]["full"]
    bhs, bhr = np.asarray(bh["fold_sharpe"]), np.asarray(bh["fold_return"])
    w("## Fold by fold, BTC, 0.10%: seed-mean Sharpe of each fold vs spot buy-and-hold's (* = above: counts for S1)")
    w("")
    w("| Fold | B&H Sharpe | B&H return | " + " | ".join(R4.SHORT[vn] for vn in ALL) + " |")
    w("|---|---|---|" + "---|" * len(ALL))
    fsh = dict((vn, np.mean([b["fees"][H]["variants"][vn][s]["full"]["fold_sharpe"] for s in SEEDS], axis=0)) for vn in ALL)
    for i in range(len(bhs)):
        w("| %d | %.2f | %s | " % (i, bhs[i], pct(bhr[i], 0)) + " | ".join(
            "%.2f%s" % (fsh[vn][i], "*" if fsh[vn][i] > bhs[i] else "") for vn in ALL) + " |")
    w("| folds above | | | " + " | ".join("%d / %d" % (int(np.sum(fsh[vn] > bhs)), len(bhs)) for vn in ALL) + " |")
    for lab, msk in (("bull folds, B&H fold Sharpe > 1", bhs > 1.0), ("flat-ish folds, 0 to 1", (bhs >= 0) & (bhs <= 1.0)),
                     ("bear folds, below 0", bhs < 0)):
        w("| of which %s (%d) | | | " % (lab, int(msk.sum())) + " | ".join(
            "%d" % int(np.sum((fsh[vn] > bhs) & msk)) for vn in ALL) + " |")
    w("")
    for a in POOL:
        w("## %s, 2020-10-01 .. 2026-11-11, 0.10%% a side" % a)
        w("")
        w(R1.table(res, a, "fee_0.10%", "full"))
        w("")
        w("### %s, 0.05%% a side" % a)
        w("")
        w(R1.table(res, a, "fee_0.05%", "full"))
        w("")
        w("### %s, up to 2025-11-11, 0.10%%" % a)
        w("")
        w(R1.table(res, a, "fee_0.10%", "dev"))
        w("")
    for a in POOL:
        y = res["assets"][a]["years"]
        yrs = sorted(y["buy_hold_spot"])
        w("## Calendar-year net returns, %s, 0.10%% (seed means; 2020 from 1 Oct, 2026 to 11 Nov)" % a)
        w("")
        w("| Variant | " + " | ".join(yrs) + " |")
        w("|---|" + "---|" * len(yrs))
        for vn in ALL:
            w("| %s | " % R4.LABELS[vn] + " | ".join(pct(np.mean([y[vn][s][yy] for s in SEEDS]), 0) for yy in yrs) + " |")
        for bn, lab in (("buy_hold_spot", "Buy-and-hold (spot)"), ("buy_hold_perp", "Buy-and-hold (perp)"), ("momentum", "Momentum")):
            w("| %s | " % lab + " | ".join(pct(y[bn][yy], 0) for yy in yrs) + " |")
        w("")
    w("## Long vs short vs flat, and the agent's folds vs the fallback folds (0.10%, full span, seed means)")
    w("")
    w("| Variant | Asset | Long / short / flat (time) | Time above 1x | Net from long bars /yr | Net from short bars /yr | "
      "Return in agent folds (by seed) | Return in fallback folds (by seed) |")
    w("|---|---|---|---|---|---|---|---|")
    for vn in ALL:
        for a in POOL:
            sd = res["assets"][a]["sides"][vn]
            m_ = lambda k: float(np.mean([sd[s][k] for s in SEEDS]))
            pb = res["assets"][a]["book"][vn]["per_seed"]
            w("| %s | %s | %.0f%% / %.0f%% / %.0f%% | %.0f%% | %s | %s | %s | %s |" % (
                R4.LABELS[vn], a, 100 * m_("long"), 100 * m_("short"), 100 * m_("flat"), 100 * m_("above_1x"),
                pct(m_("net_long_py")), pct(m_("net_short_py")),
                ", ".join(pct(pb[s]["ret_agent_folds"], 0) for s in SEEDS),
                ", ".join(pct(pb[s]["ret_fallback_folds"], 0) for s in SEEDS)))
    w("")
    w("The fallback split of R3-c*, R4-a and R4-b uses the Phase 6 agent's fallback folds.")
    w("")
    w("## The agents (unchanged; reused trained models)")
    w("")
    w("| Asset | Models | Fallback share of the span (s0 / s1 / s2) | Fallback folds (s0; s1; s2) | Decided long / short / flat (hold 16) |")
    w("|---|---|---|---|---|")
    for a in POOL:
        ag = res["agent"][a]
        for mk_, lab in (("p6", "Phase 6 r_missed (perp-trained, long/short)"), ("r2", "r_missed_spot (spot-trained, long/short)"),
                         ("r3", "r_missed_longflat (spot, long/flat, long-only reference)")):
            rows = [ag["%s_s%s" % (mk_, s)] for s in SEEDS]
            w("| %s | %s | %s | %s | %.0f%% / %.0f%% / %.0f%% |" % (
                a, lab, " / ".join("%.0f%%" % (100 * r["fallback_share"]) for r in rows),
                "; ".join(",".join(str(x) for x in r["fallback_folds"]) or "-" for r in rows),
                100 * np.mean([r["long_share_decided"] for r in rows]), 100 * np.mean([r["short_share_decided"] for r in rows]),
                100 * np.mean([r["flat_share_decided"] for r in rows])))
    w("")
    shown = R4.COMPARE + R4.ROUND_VARIANTS
    w("Requested-flat share of the out-of-sample span (seed mean), BTC: " + ", ".join(
        "%s %.0f%%" % (R4.SHORT[vn], 100 * np.mean(list(b["flat_share"][vn].values()))) for vn in shown) +
      "; ETH: " + ", ".join("%s %.0f%%" % (R4.SHORT[vn], 100 * np.mean(list(e["flat_share"][vn].values()))) for vn in shown) +
      ". Daily trend down (m = -1): BTC %.0f%%, ETH %.0f%% of the span." % (
          100 * res["checks"]["trend_down_share_BTCUSDT"], 100 * res["checks"]["trend_down_share_ETHUSDT"]))
    w("")
    w("Machine-readable: `research/out/rl_loop/round4_results.json`, grades `round4_grades.json`, gate `round4_check.json`; "
      "state: `research/out/rl_loop/loop_state.json`. Nothing here is wired into the live engine or the forward books.")
    md = "\n".join(L) + "\n"
    with open(os.path.join(R1.OUT, "round4_report.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    with open(os.path.join(R1.OUT, "round4_grades.json"), "w", encoding="utf-8") as fh:
        json.dump(R1.clean({"floors": fl, "grades": G, "repro_ok": repro_ok, "compare_ok": g["compare_ok"], "graded": graded,
                            "n_cum": R4.N_CUM, "p_threshold": 0.05 / R4.N_CUM,
                            "halves": dict((vn, b["halves"][vn]) for vn in ALL),
                            "book": dict((vn, dict((k, v) for k, v in b["book"][vn].items() if k != "per_seed")) for vn in ALL)}),
                  fh, indent=1)
    log("report written: research/out/rl_loop/round4_report.md")
    return G


def main():
    if "--report" in sys.argv:
        with open(R4.RES, encoding="utf-8") as fh:
            res = json.load(fh)
        report(res)
        return
    if "--check" in sys.argv:
        g = check()
        sys.exit(0 if g["gate_ok"] else 3)
    if "--eval" in sys.argv:
        if not os.path.exists(R4.CHECK):
            raise SystemExit("round 4: run --check first (the gate has not been run)")
        with open(R4.CHECK, encoding="utf-8") as fh:
            g1 = json.load(fh)
        if not g1.get("gate_ok"):
            raise SystemExit("round 4: the gate FAILED; the round is NOT RUN (see %s)" % R4.CHECK)
        if os.path.exists(R4.RES):
            raise SystemExit("round 4: results already exist (%s); a round is not re-run (LOOP_RL.md, Rounds 2)" % R4.RES)
        R1.acquire_lock("rl_loop round 4 evaluation (stage 2)")
        try:
            res = compute("eval")
        finally:
            R1.release_lock()
        res = json.loads(json.dumps(R1.clean(res)))
        with open(R4.RES, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=1)
        log("round 4 results written: %s (%.1f min)" % (R4.RES, res["elapsed_min"]))
        report(res)
        return
    raise SystemExit("usage: round4.py --check | --eval | --report")


if __name__ == "__main__":
    main()
