# -*- coding: utf-8 -*-
"""RL loop round 2: evaluation and report (called by round2.py --eval / --report). Paper only.

Same frame as round 1 (round1.py functions reused): Phase 6 reproduction (rule 3) first, then the six registered variants
R2-a..R2-f, plus round 1's V2 and V5 recomputed for comparison (not re-graded, not counted)."""
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
import round2 as R2  # noqa: E402

log = R1.log
SEEDS, POOL, REF = R1.SEEDS, R1.POOL, R1.REF
ALL = [REF] + R2.COMPARE + R2.ROUND_VARIANTS


def _setup_r1():
    """round1's grading / table helpers read module globals: point them at round 2."""
    R1.N_CUM = R2.N_CUM
    R1.ROUND_VARIANTS = R2.COMPARE + R2.ROUND_VARIANTS
    R1.LABELS = R2.LABELS


def requests2(a, mom, rule, cheap_long, cheap_short):
    s = np.sign(a)
    if rule in ("a", "s", "agree", "veto", "blend"):
        return R1.requests(a, mom, rule)
    if rule == "blend_fundcap":
        r = np.clip(s + 0.5 * mom, -1.5, 1.5)
        r = np.where((r > 1.0) & ~cheap_long, 1.0, r)
        return np.where((r < -1.0) & ~cheap_short, -1.0, r)
    if rule == "blend125":
        return np.clip(s + 0.25 * mom, -1.25, 1.25)
    if rule == "longlever":
        return np.where((s > 0) & (mom > 0), 1.5, s)
    raise ValueError(rule)


def funding_flags(bars, fund):
    """H34's rule: the latest settled rate at or before the bar's close vs the median of the last 270 settlements
    (min 90). -> (cheap for a long above 1x: rate <= median, cheap for a short beyond 1x: rate >= median)."""
    from engine15.rl import store
    r = pd.Series(np.asarray(fund["rate"], dtype=float))
    med = r.rolling(270, min_periods=90).median()
    ok = med.notna().values
    lo_f, hi_f = ((r <= med).values & ok), ((r >= med).values & ok)
    s = np.asarray(fund["settle_ms"], dtype="int64")
    close_ms = store.to_ms(bars.index) + 900000
    k = np.searchsorted(s, close_ms, side="right") - 1
    kk = np.maximum(k, 0)
    return np.where(k >= 0, lo_f[kk], False), np.where(k >= 0, hi_f[kk], False)


def compute():
    from engine15.rl import backtest, baselines3, benchmarks, costs, phase4, phase5, phase6, policy3, report4, resources
    from engine15.rl.continual import q_of
    from engine15.rl.learn6 import add_reference
    from engine15.rl.phase3 import evaluate_target
    from research.harness import core
    _setup_r1()
    resources.low_priority()
    pause = resources.MemoryPause(1500, 600, 20, log)
    t0 = time.time()
    cfg = phase6.load_cfg()
    roots = {"p6": (phase6.root6(cfg), "r_missed"), "r2": (R2.MODELS, R2.VNAME)}
    assert os.path.basename(roots["p6"][0]) == "b6a25c5d"
    acts = np.asarray(cfg["actions"], float)
    zero = int(np.argmin(np.abs(acts)))
    _, fts = phase5._assets_and_folds(cfg)
    for s in SEEDS:
        for ft in fts:
            assert R2._fold_done(os.path.join(R2.MODELS, R2.VNAME, "s%s" % s), ft["i"]), ("retrain incomplete", s, ft["i"])
    rcfg = dict(cfg["risk3"])
    profiles = costs.fee_profiles(cfg)
    head = report4.HEAD
    out = {"generated_utc": None, "n_cum": R2.N_CUM, "assets": {}, "checks": {}, "agent": {}}
    for asset in POOL:
        pause.before_start("load " + asset)
        log("%s: loading context" % asset)
        ctx = phase4.asset_ctx(cfg, asset, True, log)
        A, bars = ctx["A"], ctx["bars"]
        add_reference(A)
        mom = np.nan_to_num(np.asarray(A.rd["ref"], float), nan=0.0)
        n = len(bars)
        idx = bars.index
        lo_o, hi_o = ctx["bounds"][0]["te_lo"], ctx["bounds"][-1]["te_hi"]
        oos = np.zeros(n, bool)
        oos[lo_o:hi_o] = True
        cheap_l, cheap_s = funding_flags(bars, ctx["fund"])
        dec, fb_mask, agent = {}, {}, {}
        for mk_ in ("p6", "r2"):
            root, vname = roots[mk_]
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
                agent[(mk_, seed)] = {"fallback_folds": [int(ft["i"]) for ft, r in zip(fts, recs) if r["assets"][asset]["fallback"]],
                                      "fallback_share": float((fbm & oos).sum() / oos.sum()),
                                      "beta": [r["chosen"]["shaping_value"] for r in recs],
                                      "val_sharpe_mean": float(np.mean([r["assets"][asset]["val"]["sharpe"] for r in recs])),
                                      "long_share_decided": float(np.mean(dec[(mk_, seed, 16)][0][lo:hi] > 0)),
                                      "short_share_decided": float(np.mean(dec[(mk_, seed, 16)][0][lo:hi] < 0))}
                del Q, W, prepared, rd
        out["agent"][asset] = dict(("%s_s%s" % k, v) for k, v in agent.items())
        out["checks"]["funding_cheap_long_share_%s" % asset] = float(cheap_l[oos].mean())
        log("%s: decisions done (%.1f min)" % (asset, (time.time() - t0) / 60))
        res = {"fees": {}, "years": {}, "sides": {}, "decision_stats": {}, "book": {}}
        for vn, (mk_, mh, _, _) in R2.EXEC.items():
            res["decision_stats"][vn] = dict((s, dec[(mk_, s, mh)][1]) for s in SEEDS)
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
            for vn, (mk_, mh, band, rule) in R2.EXEC.items():
                pause.check("%s %s %s" % (vn, asset, pname))
                vr, rnets = {}, {}
                for seed in SEEDS:
                    req = requests2(dec[(mk_, seed, mh)][0], mom, rule, cheap_l, cheap_s)
                    req = np.where(oos, req, 0.0)
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
                    res["book"][vn] = R1.book_stats(rnets, r_bhs, idx, oos, core, dict((s, fb_mask[(mk_, s)]) for s in SEEDS))
                log("%s %s: %s done (%.1f min, free %.0f MB)" % (asset, pname, vn, (time.time() - t0) / 60,
                                                                  resources.free_mb() or -1))
            res["fees"][pname] = fees
        out["assets"][asset] = res
        del ctx, A, bars, dec
        import gc
        gc.collect()
    out["generated_utc"] = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    out["elapsed_min"] = round((time.time() - t0) / 60, 1)
    out["memory_events"] = pause.events
    with open(R2.RES, "w", encoding="utf-8") as fh:
        json.dump(R1.clean(out), fh, indent=1)
    log("round 2 results written: %s (%.1f min)" % (R2.RES, out["elapsed_min"]))
    return out


# ---------------------------------------------------------------- report
def report(res):
    _setup_r1()
    fl = R1.floors()
    G = dict((vn, R1.grade(res, vn, fl)) for vn in ALL)
    b, e = res["assets"]["BTCUSDT"], res["assets"]["ETHUSDT"]
    H = "fee_0.10%"
    sv = R1.seedvals
    pct = R1.pct
    L = []
    w = L.append
    w("# RL loop round 2: leverage where it is cheap, smaller tilts, and the agent retrained on spot accounting")
    w("")
    w("Generated %s. Paper only. Rules: `research/rl_loop/LOOP_RL.md` (frozen 13 Nov 2026 04:10 UTC; round 2 registered "
      "04:31 UTC, before any round-2 result). Seeds 0, 1, 2; 25 walk-forward folds, out of sample 2020-10-01 .. 2026-11-11. "
      "R2-a..c reuse Phase 6's trained `m_trend` models; R2-d..f use the round-2 retrain `r_missed_spot` (Phase 6's r_missed "
      "procedure with spot-long accounting in the reward, the reference term and the validation score; trend fallback). "
      "**RL variants tried, cumulative: %d** (Phase 6's 8 + round 1's 5 + round 2's 6). Evaluation compute: %.1f min "
      "(retrain: see below)." % (res["generated_utc"], R2.N_CUM, res["elapsed_min"]))
    w("")
    w("**Honesty.** No historical span is unseen for RL (Phase 4-6 scored every window; this loop was designed after Phase 6's "
      "and round 1's per-fold results; the trend fallback was chosen with hindsight). A pass would not be proof of an edge, "
      "only a proposal for a forward paper book, confirmed at 30 forward trades. Spot longs = long part up to 1x as spot "
      "(no funding); shorts and exposure above 1x are perp. Leverage (R2-a, b, c, e, f reach 1.25-1.5x) raises return and "
      "drawdown together and leaves Sharpe unchanged only before costs; after fees, slippage and funding on the part above "
      "1x it lowers Sharpe unless the extra exposure sits where the edge is larger.")
    w("")
    ck = res["checks"]
    rf = b["fees"][H]["variants"][REF]
    with open(R1.P6_FULL, encoding="utf-8") as fh:
        p6v = json.load(fh)["assets"]["BTCUSDT"]["fees"][H]["variants"]["m_trend"]["seeds"]
    d_ret = abs(np.mean(sv(rf, "full", "total_return")) - np.mean([p6v[s]["stitched"]["total_return"] for s in SEEDS]))
    d_sh = abs(np.mean(sv(rf, "full", "sharpe")) - np.mean([p6v[s]["stitched"]["sharpe"] for s in SEEDS]))
    repro_ok = d_ret < 0.005 and d_sh < 0.005
    w("**Reproduction check (rule 3).** Phase 6 primary through this harness: BTC %s, Sharpe %.3f (Phase 6: +458.6%%, 0.87); "
      "ETH %s, Sharpe %.3f (+709.1%%, 0.96); differences vs Phase 6's saved run (BTC seed mean): return %.2e, Sharpe %.2e -> %s. "
      "risk_run vs risk3.apply max |difference|: %s." % (
          pct(np.mean(sv(rf, "full", "total_return"))), np.mean(sv(rf, "full", "sharpe")),
          pct(np.mean(sv(e["fees"][H]["variants"][REF], "full", "total_return"))),
          np.mean(sv(e["fees"][H]["variants"][REF], "full", "sharpe")), d_ret, d_sh,
          "OK" if repro_ok else "FAILED: the round stops (rule 3)",
          ", ".join("%s %.1e" % (k.replace("risk_run_equals_risk3_", ""), v) for k, v in ck.items() if k.startswith("risk_run"))))
    w("")
    w("Floors applied (max of the quoted value and the unrounded Phase 6 seed mean): BTC full %.4f, BTC to 2025-11-11 %.4f, "
      "ETH full %.4f." % (fl["btc_full"], fl["btc_dev"], fl["eth_full"]))
    w("")
    w("## Verdict")
    w("")
    passed = [vn for vn in R2.ROUND_VARIANTS if G[vn]["pass"]] if repro_ok else []
    if not repro_ok:
        w("**STOPPED: the harness does not reproduce the Phase 6 primary; no variant is graded.**")
    elif passed:
        w("**PASS (historical, not proof): %s.** Proposed for a forward paper book (the session lead and the owner decide)." %
          ", ".join(R2.LABELS[p] for p in passed))
    else:
        best = max(R2.ROUND_VARIANTS, key=lambda vn: (G[vn]["met"], np.mean(sv(b["fees"][H]["variants"][vn], "full", "sharpe"))))
        fails = [k for k, ok in G[best]["rules"].items() if not ok]
        w("**No pass in round 2.** Best by rules met: %s, %d of %d rules; fails %s." % (
            R2.LABELS[best], G[best]["met"], G[best]["of"], ", ".join("`%s`" % f for f in fails)))
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
            R2.LABELS[vn], pct(np.mean(sv(vb, "full", "total_return"))), pct(np.mean(sv(vb, "full", "cagr"))),
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
    w("REF = Phase 6 as it is (perp accounting) and V2* / V5* = round 1's variants recomputed in this run: shown for "
      "comparison, graded for information, not round-2 variants and not counted again.")
    w("")
    w("## Every rule, every variant (PASS / fail)")
    w("")
    keys = list(G[R2.ROUND_VARIANTS[0]]["rules"])
    w("| Rule | " + " | ".join(R2.SHORT[vn] for vn in ALL) + " |")
    w("|---|" + "---|" * len(ALL))
    for k in keys:
        w("| `%s` | " % k + " | ".join("PASS" if G[vn]["rules"][k] else "fail" for vn in ALL) + " |")
    w("| rules met | " + " | ".join("%d / %d" % (G[vn]["met"], G[vn]["of"]) for vn in ALL) + " |")
    w("| fold share (seed-mean per fold), full / to 2025-11-11 | " + " | ".join(
        "%.0f%% / %.0f%%" % (100 * G[vn]["fold_share"], 100 * G[vn]["fold_share_dev"]) for vn in ALL) + " |")
    w("| fold share by seed 0 / 1 / 2 | " + " | ".join(
        " / ".join("%.0f%%" % (100 * G[vn]["fold_share_by_seed"][s]) for s in SEEDS) for vn in ALL) + " |")
    w("| seed-mean book Sharpe - B&H (p; threshold %.5f) | " % (0.05 / R2.N_CUM) + " | ".join(
        "%+.2f (p %.3f)" % (b["book"][vn]["sharpe_minus_bh"], b["book"][vn]["p"]) for vn in ALL) + " |")
    w("| Sharpe edge needed at that threshold / with the strategy loop's 1,910 added | " + " | ".join(
        "%.2f / %.2f" % (b["book"][vn]["edge_needed"], b["book"][vn]["edge_needed_with_strategy_loop"]) for vn in ALL) + " |")
    w("| deflated-Sharpe probability (N = %d) | " % R2.N_CUM + " | ".join("%.3f" % b["book"][vn]["dsr"] for vn in ALL) + " |")
    w("")
    w("Bootstrap on daily returns of the seed-mean book (per-bar mean of the three seeds' net returns) against spot "
      "buy-and-hold, BTC full span; Bonferroni over %d RL variants. REF / V2* / V5* graded here with N = %d for "
      "information only (round 1 graded them with N = 13)." % (R2.N_CUM, R2.N_CUM))
    w("")
    # fold by fold (the binding rule)
    bh = b["fees"][H]["bench"]["buy_hold_spot"]["full"]
    bhs, bhr = np.asarray(bh["fold_sharpe"]), np.asarray(bh["fold_return"])
    w("## Fold by fold, BTC, 0.10%: seed-mean Sharpe of each fold vs spot buy-and-hold's (* = above: counts for S1)")
    w("")
    w("| Fold | B&H Sharpe | B&H return | " + " | ".join(R2.SHORT[vn] for vn in ALL) + " |")
    w("|---|---|---|" + "---|" * len(ALL))
    fsh = dict((vn, np.mean([b["fees"][H]["variants"][vn][s]["full"]["fold_sharpe"] for s in SEEDS], axis=0)) for vn in ALL)
    for i in range(len(bhs)):
        w("| %d | %.2f | %s | " % (i, bhs[i], pct(bhr[i], 0)) + " | ".join(
            "%.2f%s" % (fsh[vn][i], "*" if fsh[vn][i] > bhs[i] else "") for vn in ALL) + " |")
    w("| folds above | | | " + " | ".join("%d / %d" % (int(np.sum(fsh[vn] > bhs)), len(bhs)) for vn in ALL) + " |")
    up = bhs > 1.0
    w("| of which B&H fold Sharpe > 1 (bull folds, %d) | | | " % int(up.sum()) + " | ".join(
        "%d" % int(np.sum((fsh[vn] > bhs) & up)) for vn in ALL) + " |")
    w("")
    _setup_r1()
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
            w("| %s | " % R2.LABELS[vn] + " | ".join(pct(np.mean([y[vn][s][yy] for s in SEEDS]), 0) for yy in yrs) + " |")
        for bn, lab in (("buy_hold_spot", "Buy-and-hold (spot)"), ("buy_hold_perp", "Buy-and-hold (perp)"), ("momentum", "Momentum")):
            w("| %s | " % lab + " | ".join(pct(y[bn][yy], 0) for yy in yrs) + " |")
        w("")
    w("## Long vs short, and the agent's folds vs the fallback folds (0.10%, full span, seed means)")
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
                R2.LABELS[vn], a, 100 * m_("long"), 100 * m_("short"), 100 * m_("flat"), 100 * m_("above_1x"),
                pct(m_("net_long_py")), pct(m_("net_short_py")),
                ", ".join(pct(pb[s]["ret_agent_folds"], 0) for s in SEEDS),
                ", ".join(pct(pb[s]["ret_fallback_folds"], 0) for s in SEEDS)))
    w("")
    w("## The agents: Phase 6's r_missed vs the round-2 spot-trained r_missed_spot")
    w("")
    w("| Asset | Models | Fallback share of the span (s0 / s1 / s2) | Fallback folds (s0; s1; s2) | Mean validation net Sharpe (s0 / s1 / s2) | Beta chosen 0.25 / 0.5 / 1.0 (all seeds) | Decided long / short (hold 16) |")
    w("|---|---|---|---|---|---|---|")
    for a in POOL:
        ag = res["agent"][a]
        for mk_, lab in (("p6", "Phase 6 r_missed (perp-trained; perp validation)"), ("r2", "r_missed_spot (spot-trained; spot validation)")):
            rows = [ag["%s_s%s" % (mk_, s)] for s in SEEDS]
            betas = sum((r["beta"] for r in rows), [])
            w("| %s | %s | %s | %s | %s | %d / %d / %d | %.0f%% / %.0f%% |" % (
                a, lab, " / ".join("%.0f%%" % (100 * r["fallback_share"]) for r in rows),
                "; ".join(",".join(str(x) for x in r["fallback_folds"]) or "-" for r in rows),
                " / ".join("%.2f" % r["val_sharpe_mean"] for r in rows),
                sum(1 for x in betas if x == 0.25), sum(1 for x in betas if x == 0.5), sum(1 for x in betas if x == 1.0),
                100 * np.mean([r["long_share_decided"] for r in rows]), 100 * np.mean([r["short_share_decided"] for r in rows])))
    w("")
    w("The validation Sharpe of the two model sets is not on the same accounting (perp vs spot), so the fallback folds "
      "differ partly because the bar (0.5) is applied to a different number; this was registered before the run.")
    w("")
    w("Funding-cheap share of the BTC out-of-sample bars (R2-a, long side): %.0f%%; ETH %.0f%%." % (
        100 * res["checks"]["funding_cheap_long_share_BTCUSDT"], 100 * res["checks"]["funding_cheap_long_share_ETHUSDT"]))
    w("")
    w("Machine-readable: `research/out/rl_loop/round2_results.json`, grades `round2_grades.json`; state: "
      "`research/out/rl_loop/loop_state.json`. Nothing here is wired into the live engine or the forward books.")
    md = "\n".join(L) + "\n"
    with open(os.path.join(R1.OUT, "round2_report.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    with open(os.path.join(R1.OUT, "round2_grades.json"), "w", encoding="utf-8") as fh:
        json.dump(R1.clean({"floors": fl, "grades": G, "repro_ok": repro_ok}), fh, indent=1)
    log("report written: research/out/rl_loop/round2_report.md")
    return G


def main():
    if "--report" in sys.argv:
        with open(R2.RES, encoding="utf-8") as fh:
            res = json.load(fh)
        report(res)
        return
    R1.acquire_lock("rl_loop round 2 evaluation")
    try:
        res = compute()
    finally:
        R1.release_lock()
    res = json.loads(json.dumps(R1.clean(res)))
    report(res)


if __name__ == "__main__":
    main()
