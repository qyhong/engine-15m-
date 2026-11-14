# -*- coding: utf-8 -*-
"""RL loop round 1 (research/rl_loop/LOOP_RL.md, registered 13 Nov 2026 04:10 UTC). Paper only.

    py -3 research/rl_loop/round1.py            compute (heavy-job lock, memory pause) + report
    py -3 research/rl_loop/round1.py --report   rebuild the report from research/out/rl_loop/round1_results.json

Reuses the Phase 6 primary's trained fold models (models6/b6a25c5d/r_missed, trend fallback) unchanged; only execution,
accounting and sizing change (variants V1-V5). Read-only use of engine15.rl and research/harness; writes only under
research/out/rl_loop/.
"""
import json
import os
import sys
import time
from collections import deque

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

OUT = os.path.join(ROOT, "research", "out", "rl_loop")
LOCK = os.path.join(ROOT, "research", "out", "heavy_job.lock")
FWD_LOCK = os.path.join(ROOT, "research", "out", "rl", "forward5", "update.lock")
P6_FULL = os.path.join(ROOT, "research", "out", "rl", "runs", "phase6_20261112T141341Z_30a4dd4f", "phase6_full.json")
RES = os.path.join(OUT, "round1_results.json")
PROG = os.path.join(OUT, "progress.log")
POOL = ["BTCUSDT", "ETHUSDT"]
SEEDS = ["0", "1", "2"]
N_PHASE6 = 8
ROUND_VARIANTS = ["V1_spot", "V2_spot_lean", "V3_spot_lean_agree", "V4_spot_lean_agree_veto", "V5_spot_lean_blend"]
N_CUM = N_PHASE6 + len(ROUND_VARIANTS)
N_STRATEGY_LOOP = 1910
REF = "REF_m_trend_perp"
LABELS = {REF: "Phase 6 primary m_trend, reproduced (perp, as Phase 6)",
          "V1_spot": "V1 spot: m_trend, spot longs",
          "V2_spot_lean": "V2 spot_lean: side only, hold 4 h, band 0.40",
          "V3_spot_lean_agree": "V3 spot_lean_agree: 1.5x when agent = trend",
          "V4_spot_lean_agree_veto": "V4 spot_lean_agree_veto: 1.5x with trend, flat against",
          "V5_spot_lean_blend": "V5 spot_lean_blend: side + 0.5 x trend"}
# execution per variant: (min hold bars, re-size band, request rule)
EXEC = {"V1_spot": (4, 0.20, "a"), "V2_spot_lean": (16, 0.40, "s"), "V3_spot_lean_agree": (16, 0.40, "agree"),
        "V4_spot_lean_agree_veto": (16, 0.40, "veto"), "V5_spot_lean_blend": (16, 0.40, "blend")}


def log(msg):
    line = "%s  %s" % (time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), msg)
    print(line, flush=True)
    os.makedirs(OUT, exist_ok=True)
    with open(PROG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


# ---------------------------------------------------------------- shared heavy-job lock
def _pid_alive(pid):
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, int(pid))          # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = k.GetExitCodeProcess(h, ctypes.byref(code))
        k.CloseHandle(h)
        return bool(ok) and code.value == 259                # STILL_ACTIVE
    except Exception:
        return True


def acquire_lock(label):
    while True:
        if os.path.exists(FWD_LOCK):
            log("forward5 update.lock held; waiting 60 s")
            time.sleep(60)
            continue
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, json.dumps({"pid": os.getpid(), "label": label,
                                     "utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())}).encode())
            os.close(fd)
            log("heavy_job.lock taken (pid %d, %s)" % (os.getpid(), label))
            return
        except FileExistsError:
            try:
                with open(LOCK, encoding="utf-8") as fh:
                    held = json.load(fh)
                pid = int(held.get("pid", -1))
            except Exception:
                held, pid = {}, -1
            if pid > 0 and _pid_alive(pid):
                log("heavy_job.lock held by pid %d (%s); waiting 60 s" % (pid, held.get("label")))
                time.sleep(60)
                continue
            log("heavy_job.lock held by dead pid %s; taking it over" % pid)
            try:
                os.remove(LOCK)
            except FileNotFoundError:
                pass


def release_lock():
    try:
        with open(LOCK, encoding="utf-8") as fh:
            mine = int(json.load(fh).get("pid", -1)) == os.getpid()
        if mine:                                             # remove only after the handle is closed (Windows)
            os.remove(LOCK)
            log("heavy_job.lock released")
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------- the risk manager with spot accounting and a band
def risk_run(market, target, lo, hi, rcfg, band, spot, want_cap=1.5):
    """risk3.Stepper's rules exactly (vol size min(1, vt / vol), soft brake on the rolling-peak drawdown, re-size only on
    a new request, a request of 0, or a drift above `band`), with (a) the equity marks' funding on the spot-long
    accounting when spot=True (long part up to 1x unfunded) and (b) executed = request x size capped at want_cap, so a
    request of 1.5 reaches 1.5 x size. With spot=False, band=0.20 and requests in [-1, 1] it equals risk3.apply."""
    from engine15.rl import risk3
    cfg = risk3.Risk3Config.from_cfg(rcfg)
    tgt = np.nan_to_num(np.asarray(target, dtype=float), nan=0.0)
    out = tgt.copy()
    m, mod = market, market.model
    cs, cl = m.col(cfg.vol_short), m.col(cfg.vol_long)
    rs = (m.raw[:, cs].astype(float) if cs is not None else m.vol).tolist()
    rl = (m.raw[:, cl].astype(float) if cl is not None else m.vol).tolist()
    d = int(mod.delay_bars)
    W = int(cfg.dd_window_bars)
    hist = deque([0.0] * (d + 1), maxlen=d + 1)
    for k in range(lo - d - 1, lo):
        hist.append(float(out[k]) if k >= 0 else 0.0)
    prev_pos = float(out[lo - d - 1]) if lo - d - 1 >= 0 else 0.0
    cur = float(hist[-1])
    last_req = None
    eq, pending = 1.0, None
    peak_q = deque()
    ann = float(np.sqrt(risk3.BARS_PER_YEAR))
    r_px, r_bar, vol, rate = m.r_px.tolist(), m.r_bar.tolist(), m.vol.tolist(), m.rate.tolist()
    tl = tgt.tolist()
    fee, hs, sc = float(mod.fee_side), float(mod.half_spread_bps) * 1e-4, float(mod.slippage_coef)
    fund_on = bool(mod.funding)
    vt, lv, fc = float(cfg.vol_target), list(cfg.dd_levels), list(cfg.dd_factors)
    counts = {"vol_resize": 0, "brake_resize": 0, "brake_on_bars": 0}
    for t in range(lo, hi):
        if pending is not None:
            ppos, pc = pending
            eq *= (1.0 + ppos * (r_px[t - 1] if t >= 1 else 0.0) - pc)
        pos = hist[-d]
        trade = pos - prev_pos
        c1 = (fee + hs + sc * (vol[t - d] if t - d >= 0 else 0.0)) * abs(trade)
        if fund_on:
            fpos = (min(pos, 0.0) + max(pos - 1.0, 0.0)) if spot else pos
            fund = fpos * rate[t]
        else:
            fund = 0.0
        mark = eq * (1.0 + pos * r_bar[t] - c1 - fund)
        pending = (pos, c1 + fund)
        prev_pos = pos
        while peak_q and peak_q[-1][1] <= mark:
            peak_q.pop()
        peak_q.append((t, mark))
        while peak_q[0][0] <= t - W:
            peak_q.popleft()
        peak = peak_q[0][1]
        dd = 1.0 - mark / peak if peak > 0 else 0.0
        a, b = rs[t], rl[t]
        v = max(a if a == a else 0.0, b if b == b else 0.0) * ann
        vsize = min(1.0, vt / v) if v > 0 else 1.0
        bf = 1.0
        for l_, f_ in zip(lv, fc):
            if dd >= l_:
                bf = f_
        if bf < 1.0:
            counts["brake_on_bars"] += 1
        req = tl[t]
        want = req * vsize * bf
        if abs(want) > want_cap:
            want = want_cap if want > 0 else -want_cap
        if req == 0.0:
            new = 0.0
        elif last_req is None or req != last_req:
            new = want
        elif abs(want - cur) > band:
            new = want
        else:
            new = cur
        if new != cur and req != 0.0 and req == last_req:
            counts["brake_resize" if bf < 1.0 else "vol_resize"] += 1
        cur = new
        last_req = req
        hist.append(new)
        out[t] = new
    return out, counts


# ---------------------------------------------------------------- compute
def requests(a, mom, rule):
    s = np.sign(a)
    if rule == "a":
        return a.copy()
    if rule == "s":
        return s
    if rule == "agree":
        return np.where((s != 0) & (s == mom), 1.5 * s, s)
    if rule == "veto":
        return np.where((s != 0) & (s == mom), 1.5 * s, 0.0)
    if rule == "blend":
        return np.clip(s + 0.5 * mom, -1.5, 1.5)
    raise ValueError(rule)


def frame_metrics(frame, ctx, ex, bh_sharpe, span):
    from engine15.rl.phase3 import _span_ev
    if span == "full":
        lo, hi, wins = ctx["bounds"][0]["te_lo"], ctx["bounds"][-1]["te_hi"], ctx["wins"]
    else:
        lo, hi, wins = ctx["bounds_dev"][0]["te_lo"], ctx["bounds_dev"][-1]["te_hi"], ctx["wins_dev"]
    ev = _span_ev(frame, wins, lo, hi, ex, bh_sharpe)
    st = dict(ev["stitched"])
    st["trades_per_year"] = st["trades"] / st["years"]
    return {"stitched": st, "fold_sharpe": [w["sharpe"] for w in ev["windows"]],
            "fold_return": [w["total_return"] for w in ev["windows"]], "break_even_fee": ev["break_even_fee"],
            "position_mix": ev["position_mix"], "mean_abs_position": ev["mean_abs_position"]}


def side_split(frame, oos):
    pos, rn, rg = frame["pos"].values, frame["r_net"].values, frame["r_gross"].values
    yrs = oos.sum() / 35040.0
    return {"long": float(np.mean(pos[oos] > 0)), "short": float(np.mean(pos[oos] < 0)), "flat": float(np.mean(pos[oos] == 0)),
            "above_1x": float(np.mean(np.abs(pos[oos]) > 1.0 + 1e-9)),
            "net_long_py": float(rn[oos & (pos > 0)].sum() / yrs), "net_short_py": float(rn[oos & (pos < 0)].sum() / yrs),
            "gross_long_py": float(rg[oos & (pos > 0)].sum() / yrs), "gross_short_py": float(rg[oos & (pos < 0)].sum() / yrs)}


def years_of(r, idx, oos):
    s = pd.Series(np.log1p(r[oos]), index=idx[oos])
    g = s.groupby(s.index.year).sum()
    return dict((str(y), float(np.expm1(v))) for y, v in g.items())


def compute():
    from engine15.rl import backtest, baselines3, benchmarks, costs, phase4, phase5, phase6, policy3, report4, resources, risk3
    from engine15.rl.continual import q_of
    from engine15.rl.learn6 import add_reference
    from engine15.rl.phase3 import evaluate_target
    from research.harness import core
    resources.low_priority()
    pause = resources.MemoryPause(1500, 600, 20, log)
    t0 = time.time()
    cfg = phase6.load_cfg()
    root = phase6.root6(cfg)
    assert os.path.basename(root) == "b6a25c5d" and os.path.isdir(os.path.join(root, "r_missed")), root
    acts = np.asarray(cfg["actions"], float)
    zero = int(np.argmin(np.abs(acts)))
    _, fts = phase5._assets_and_folds(cfg)
    rcfg = dict(cfg["risk3"])
    profiles = costs.fee_profiles(cfg)
    head = report4.HEAD
    out = {"generated_utc": None, "n_cum": N_CUM, "assets": {}, "checks": {}}
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
        oos_dev = np.zeros(n, bool)
        oos_dev[ctx["bounds_dev"][0]["te_lo"]:ctx["bounds_dev"][-1]["te_hi"]] = True
        # the agent's decisions per seed (hold 4 = Phase 6; hold 16 = the lean variants), and its fallback folds
        dec, fb_mask = {}, {}
        for seed in SEEDS:
            pause.check("decide %s s%s" % (asset, seed))
            W, lo, hi, recs = phase5.oos_w(root, "r_missed", int(seed), fts, A, list(acts), None, "trend")
            assert (lo, hi) == (lo_o, hi_o)
            rd = dict((k, np.asarray(v)) for k, v in A.rd.items())
            Q = q_of(W, rd, lo, hi, dict(cfg["qagent"]), list(acts))
            prepared = policy3.prepare(Q)
            for mh in (4, 16):
                ip, st = policy3.decide(Q, acts, zero, mh, prepared=prepared)
                t = np.zeros(n)
                t[lo:hi] = acts[ip]
                dec[(seed, mh)] = (t, st)
            fbm = np.zeros(n, bool)
            for ft, r in zip(fts, recs):
                if r["assets"][asset]["fallback"]:
                    fbm[A.at(ft["test_start"]):A.at(ft["test_end"])] = True
            fb_mask[seed] = fbm
            del Q, W, prepared, rd
        log("%s: decisions done (%.1f min)" % (asset, (time.time() - t0) / 60))
        res = {"fees": {}, "years": {}, "sides": {}, "fold_split": {}, "decision_stats": {}, "book": {}}
        for vn, (mh, _, _) in EXEC.items():
            res["decision_stats"][vn] = dict((s, dec[(s, mh)][1]) for s in SEEDS)
        res["decision_stats"][REF] = dict((s, dec[(s, 4)][1]) for s in SEEDS)
        btg = benchmarks.all_targets(bars, cfg["benchmarks"])
        for pname, model in profiles.items():
            mk = ctx["market"].with_model(model)
            fees = {"bench": {}, "variants": {}}
            # benchmarks (as Phase 6: perp buy-and-hold and momentum without the risk manager; spot buy-and-hold)
            fr_bhs = baselines3.spot_frame(ctx["smkt"], np.where(oos, 1.0, 0.0), model.fee_side, True)
            fr_bhp = backtest.run(bars, np.where(oos, 1.0, 0.0), model, ctx["fund"])["frame"]
            fr_mom = backtest.run(bars, np.where(oos, btg["momentum"].values, 0.0), model, ctx["fund"])["frame"]
            bm = {}
            for bn, fr, ex in (("buy_hold_spot", fr_bhs, np.where(oos, 1.0, 0.0)), ("buy_hold_perp", fr_bhp, np.where(oos, 1.0, 0.0)),
                               ("momentum", fr_mom, np.where(oos, btg["momentum"].values, 0.0))):
                bm[bn] = {"full": frame_metrics(fr, ctx, ex, None, "full"), "dev": frame_metrics(fr, ctx, ex, None, "dev")}
                if pname == head:
                    res["years"][bn] = years_of(fr["r_net"].values, idx, oos)
                    res["sides"][bn] = side_split(fr, oos)
            fees["bench"] = bm
            bhsh = {"full": bm["buy_hold_spot"]["full"]["stitched"]["sharpe"], "dev": bm["buy_hold_spot"]["dev"]["stitched"]["sharpe"]}
            r_bhs = fr_bhs["r_net"].values.copy()
            del fr_bhp, fr_mom
            # the reference: Phase 6's own path (risk3.apply + perp backtester), and the risk_run equivalence check
            pause.check("reference %s %s" % (asset, pname))
            vr = {}
            rnets = {}
            for seed in SEEDS:
                tgt = dec[(seed, 4)][0]
                e = evaluate_target(ctx, tgt, model, 1.0, True, bh=None)
                ex = np.asarray(e["risk"]["exec"], float)
                fr = backtest.run(bars, ex, model, ctx["fund"])["frame"]
                vr[seed] = {"full": frame_metrics(fr, ctx, ex, bhsh["full"], "full"),
                            "dev": frame_metrics(fr, ctx, ex, bhsh["dev"], "dev"), "risk_counts": e["risk"]["counts"]}
                if seed == "0":
                    mine, _ = risk_run(mk, tgt, lo_o, hi_o, rcfg, 0.20, False, 1.0)
                    out["checks"]["risk_run_equals_risk3_%s_%s" % (asset, pname)] = float(np.max(np.abs(mine - ex)))
                if pname == head:
                    rnets[seed] = fr["r_net"].values.copy()
                    res.setdefault("years", {}).setdefault(REF, {})[seed] = years_of(fr["r_net"].values, idx, oos)
                    res["sides"].setdefault(REF, {})[seed] = side_split(fr, oos)
                del fr, e
            fees["variants"][REF] = vr
            if pname == head:
                res["book"][REF] = book_stats(rnets, r_bhs, idx, oos, core, fb_mask)
            log("%s %s: reference done (%.1f min)" % (asset, pname, (time.time() - t0) / 60))
            for vn, (mh, band, rule) in EXEC.items():
                pause.check("%s %s %s" % (vn, asset, pname))
                vr, rnets = {}, {}
                for seed in SEEDS:
                    req = requests(dec[(seed, mh)][0], mom, rule)
                    req = np.where(oos, req, 0.0)
                    ex, cnt = risk_run(mk, req, lo_o, hi_o, rcfg, band, True, 1.5)
                    fr = baselines3.spot_frame(ctx["smkt"], ex, model.fee_side, True)
                    vr[seed] = {"full": frame_metrics(fr, ctx, ex, bhsh["full"], "full"),
                                "dev": frame_metrics(fr, ctx, ex, bhsh["dev"], "dev"), "risk_counts": cnt}
                    if pname == head:
                        rnets[seed] = fr["r_net"].values.copy()
                        res["years"].setdefault(vn, {})[seed] = years_of(fr["r_net"].values, idx, oos)
                        res["sides"].setdefault(vn, {})[seed] = side_split(fr, oos)
                    del fr
                fees["variants"][vn] = vr
                if pname == head:
                    res["book"][vn] = book_stats(rnets, r_bhs, idx, oos, core, fb_mask)
                log("%s %s: %s done (%.1f min, free %.0f MB)" % (asset, pname, vn, (time.time() - t0) / 60,
                                                                  resources.free_mb() or -1))
            res["fees"][pname] = fees
        res["years"]["_spot_bh"] = res["years"]["buy_hold_spot"]
        out["assets"][asset] = res
        del ctx, A, bars, dec
        import gc
        gc.collect()
    out["generated_utc"] = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    out["elapsed_min"] = round((time.time() - t0) / 60, 1)
    out["memory_events"] = pause.events
    with open(RES, "w", encoding="utf-8") as fh:
        json.dump(clean(out), fh, indent=1)
    log("results written: %s (%.1f min)" % (RES, out["elapsed_min"]))
    return out


def book_stats(rnets, r_bhs, idx, oos, core, fb_mask):
    """Seed-mean book (per-bar mean of the seeds' net returns): bootstrap vs spot buy-and-hold, deflated Sharpe; per-seed
    p; return in the agent's folds vs the fallback folds."""
    book = np.mean([rnets[s] for s in SEEDS], axis=0)
    obs, p, se = core.boot_sharpe_diff_z(book[oos], r_bhs[oos], idx[oos])
    per = {}
    for s in SEEDS:
        o, ps, ss = core.boot_sharpe_diff_z(rnets[s][oos], r_bhs[oos], idx[oos])
        ag, fb = oos & ~fb_mask[s], oos & fb_mask[s]
        per[s] = {"sharpe_minus_bh": o, "p": ps, "se": ss,
                  "ret_agent_folds": float(np.prod(1 + rnets[s][ag]) - 1), "ret_fallback_folds": float(np.prod(1 + rnets[s][fb]) - 1),
                  "fallback_share": float(fb.sum() / oos.sum())}
    from statistics import NormalDist
    z_need = NormalDist().inv_cdf(1 - 0.05 / N_CUM)
    z_need_all = NormalDist().inv_cdf(1 - 0.05 / (N_CUM + N_STRATEGY_LOOP))
    return {"sharpe_minus_bh": obs, "p": p, "se": se, "p_threshold": 0.05 / N_CUM, "edge_needed": z_need * se,
            "p_threshold_with_strategy_loop": 0.05 / (N_CUM + N_STRATEGY_LOOP), "edge_needed_with_strategy_loop": z_need_all * se,
            "dsr": core.deflated_sharpe(book[oos], N_CUM), "book_sharpe": float(core.metrics.sharpe(book[oos])),
            "book_total_return": float(np.prod(1 + book[oos]) - 1), "per_seed": per}


def clean(o):
    if isinstance(o, dict):
        return dict((str(k), clean(v)) for k, v in o.items())
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        if f != f:
            return None
        if f in (float("inf"), float("-inf")):
            return "inf" if f > 0 else "-inf"
        return f
    return o


# ---------------------------------------------------------------- grading (LOOP_RL.md, frozen)
def floors():
    with open(P6_FULL, encoding="utf-8") as fh:
        p6 = json.load(fh)
    def m(asset, span):
        v = p6["assets"][asset]["fees"]["fee_0.10%"]
        v = v["variants"]["m_trend"] if span == "full" else v["dev"]["variants"]["m_trend"]
        return float(np.mean([v["seeds"][s]["stitched"]["sharpe"] for s in SEEDS]))
    return {"btc_full": max(0.87, m("BTCUSDT", "full")), "btc_dev": max(1.05, m("BTCUSDT", "dev")),
            "eth_full": max(0.96, m("ETHUSDT", "full"))}


def seedvals(v, span, key):
    return [v[s][span]["stitched"][key] for s in SEEDS]


def grade(res, vn, fl):
    out = {}
    b = res["assets"]["BTCUSDT"]
    e = res["assets"]["ETHUSDT"]
    H, L = "fee_0.10%", "fee_0.05%"

    def target_rules(asset_res, span, floor, prefix):
        v = asset_res["fees"][H]["variants"][vn]
        bh = asset_res["fees"][H]["bench"]["buy_hold_spot"][span]["stitched"]
        tr, cg = seedvals(v, span, "total_return"), seedvals(v, span, "cagr")
        sh, dd = seedvals(v, span, "sharpe"), seedvals(v, span, "max_drawdown")
        return {prefix + "return_gt_bh": bool(np.mean(tr) > bh["total_return"]),
                prefix + "mean_cagr_gt_bh": bool(np.mean(cg) > bh["cagr"]),
                prefix + "sharpe_ge_floor": bool(np.mean(sh) >= floor),
                prefix + "sharpe_gt_bh": bool(np.mean(sh) > bh["sharpe"]),
                prefix + "every_seed_sharpe_gt_bh": bool(min(sh) > bh["sharpe"]),
                prefix + "every_seed_dd_le_bh": bool(max(dd) <= bh["max_drawdown"])}
    out.update(target_rules(b, "full", fl["btc_full"], "T_"))
    out.update(target_rules(b, "dev", fl["btc_dev"], "T4_dev_"))
    v = b["fees"][H]["variants"][vn]
    bh = b["fees"][H]["bench"]["buy_hold_spot"]["full"]
    fsh = np.mean([v[s]["full"]["fold_sharpe"] for s in SEEDS], axis=0)
    fs = float(np.mean(fsh > np.asarray(bh["fold_sharpe"])))
    out["S1_fold_share_ge_half"] = bool(fs >= 0.5)

    def beats(fee):
        vv = b["fees"][fee]["variants"][vn]
        bb = b["fees"][fee]["bench"]["buy_hold_spot"]["full"]["stitched"]
        return np.mean(seedvals(vv, "full", "sharpe")) > bb["sharpe"] and np.mean(seedvals(vv, "full", "calmar")) > bb["calmar"]
    out["S2_no_fee_only_at_0.05"] = bool(not (beats(L) and not beats(H)))
    out["S3_trades_le_100_every_seed"] = bool(max(seedvals(v, "full", "trades_per_year")) <= 100)
    out["S3_turnover_le_100_every_seed"] = bool(max(seedvals(v, "full", "turnover_per_year")) <= 100)
    bk = b["book"][vn]
    out["S4_significant"] = bool(bk["p"] <= 0.05 / N_CUM)
    ve = e["fees"][H]["variants"][vn]
    bhe = e["fees"][H]["bench"]["buy_hold_spot"]["full"]["stitched"]
    out["E1_eth_sharpe_ge_floor"] = bool(np.mean(seedvals(ve, "full", "sharpe")) >= fl["eth_full"])
    out["E2_eth_return_gt_bh"] = bool(np.mean(seedvals(ve, "full", "total_return")) > bhe["total_return"])
    out["E2_eth_mean_cagr_gt_bh"] = bool(np.mean(seedvals(ve, "full", "cagr")) > bhe["cagr"])
    out["E3_eth_every_seed_dd_le_bh"] = bool(max(seedvals(ve, "full", "max_drawdown")) <= bhe["max_drawdown"])
    fs_seed = dict((s, float(np.mean(np.asarray(v[s]["full"]["fold_sharpe"]) > np.asarray(bh["fold_sharpe"])))) for s in SEEDS)
    bhd = b["fees"][H]["bench"]["buy_hold_spot"]["dev"]
    fsd = float(np.mean(np.mean([v[s]["dev"]["fold_sharpe"] for s in SEEDS], axis=0) > np.asarray(bhd["fold_sharpe"])))
    return {"rules": out, "pass": all(out.values()), "met": sum(out.values()), "of": len(out), "fold_share": fs,
            "fold_share_by_seed": fs_seed, "fold_share_dev": fsd}


# ---------------------------------------------------------------- report
def pct(x, d=1):
    return "-" if x is None else ("%+.*f%%" % (d, 100 * x))


def fee_str(x):
    if x is None:
        return "-"
    if isinstance(x, str):
        return "> 5%" if x == "inf" else "< -1%"
    return "%.3f%%" % (100 * x)


ROW_KEYS = ("total_return", "cagr", "sharpe", "sortino", "max_drawdown", "calmar", "turnover_per_year", "trades_per_year",
            "avg_holding_hours", "cost_drag_per_year", "funding_per_year", "sharpe_gross")


def row_of(st, bef):
    return "| %s | %s | %.2f | %.2f | %.0f%% | %.2f | %.0f | %.0f | %.0f | %.1f%% | %.1f%% | %.2f | %s |" % (
        pct(st["total_return"]), pct(st["cagr"]), st["sharpe"], st["sortino"], 100 * st["max_drawdown"], st["calmar"],
        st["turnover_per_year"], st["trades_per_year"], st["avg_holding_hours"], 100 * st["cost_drag_per_year"],
        100 * st["funding_per_year"], st["sharpe_gross"], fee_str(bef))


HDR = ("| Strategy | Net return | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover/yr | Trades/yr | Avg hold (h) | "
       "Cost drag/yr | Funding/yr | Gross Sharpe | Break-even fee |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")


def table(res, asset, fee, span):
    f = res["assets"][asset]["fees"][fee]
    lines = [HDR]
    for vn in [REF] + ROUND_VARIANTS:
        v = f["variants"][vn]
        mean = dict((k, float(np.mean([v[s][span]["stitched"][k] for s in SEEDS]))) for k in ROW_KEYS)
        bef = [v[s][span]["break_even_fee"] for s in SEEDS]
        bef_m = float(np.mean(bef)) if all(isinstance(x, float) for x in bef) else None
        lines.append(("| **%s, mean of 3 seeds** " % LABELS[vn]) + row_of(mean, bef_m))
        for s in SEEDS:
            lines.append(("| &nbsp;&nbsp;seed %s " % s) + row_of(v[s][span]["stitched"], v[s][span]["break_even_fee"]))
    for bn, lab in (("buy_hold_spot", "Buy-and-hold (spot)"), ("buy_hold_perp", "Buy-and-hold (perp)"),
                    ("momentum", "Momentum (daily 30-day, long/short, perp)")):
        st = f["bench"][bn][span]["stitched"]
        lines.append(("| %s " % lab) + row_of(st, f["bench"][bn][span]["break_even_fee"]))
    return "\n".join(lines)


def report(res):
    fl = floors()
    G = dict((vn, grade(res, vn, fl)) for vn in [REF] + ROUND_VARIANTS)
    b, e = res["assets"]["BTCUSDT"], res["assets"]["ETHUSDT"]
    H = "fee_0.10%"
    L = []
    w = L.append
    w("# RL loop round 1: execution, accounting and sizing of the Phase 6 primary")
    w("")
    w("Generated %s. Paper only. Rules: `research/rl_loop/LOOP_RL.md` (frozen 13 Nov 2026 04:10 UTC, before any result). "
      "Seeds 0, 1, 2; 25 walk-forward folds, out of sample 2020-10-01 .. 2026-11-11; Phase 6's trained `m_trend` models "
      "(r_missed, trend fallback) reused unchanged. **RL variants tried, cumulative: %d** (Phase 6's 8 + round 1's 5). "
      "Compute: %.1f min." % (res["generated_utc"], N_CUM, res["elapsed_min"]))
    w("")
    w("**Honesty.** No historical span is unseen for RL (Phase 4-6 scored every window; this loop was designed after Phase 6's "
      "per-fold results; the trend fallback was chosen with hindsight). A pass here would not be proof of an edge, only a "
      "proposal for a forward paper book, confirmed at 30 forward trades. Spot longs = long part up to 1x held as spot (no "
      "funding); shorts and exposure above 1x are perp. Leverage (V3-V5 reach 1.5x) raises return and drawdown together and "
      "leaves Sharpe unchanged only before costs.")
    w("")
    ck = res["checks"]
    rf = b["fees"][H]["variants"][REF]
    w("**Reproduction check (rule 3).** Phase 6 primary through this harness: BTC %s, Sharpe %.3f (Phase 6 report: +458.6%%, "
      "0.87); ETH %s, Sharpe %.3f (+709.1%%, 0.96). The spot-aware risk manager with perp accounting and Phase 6's band equals "
      "`risk3.apply`: max |difference| in executed position %s." % (
          pct(np.mean(seedvals(rf, "full", "total_return"))), np.mean(seedvals(rf, "full", "sharpe")),
          pct(np.mean(seedvals(e["fees"][H]["variants"][REF], "full", "total_return"))),
          np.mean(seedvals(e["fees"][H]["variants"][REF], "full", "sharpe")),
          ", ".join("%s %.1e" % (k.replace("risk_run_equals_risk3_", ""), v) for k, v in ck.items())))
    w("")
    w("Floors applied (max of the quoted value and the unrounded Phase 6 seed mean): BTC full %.4f, BTC to 2025-11-11 %.4f, "
      "ETH full %.4f." % (fl["btc_full"], fl["btc_dev"], fl["eth_full"]))
    w("")
    passed = [vn for vn in ROUND_VARIANTS if G[vn]["pass"]]
    with open(P6_FULL, encoding="utf-8") as fh:
        p6v = json.load(fh)["assets"]["BTCUSDT"]["fees"][H]["variants"]["m_trend"]["seeds"]
    d_ret = abs(np.mean(seedvals(rf, "full", "total_return")) - np.mean([p6v[s]["stitched"]["total_return"] for s in SEEDS]))
    d_sh = abs(np.mean(seedvals(rf, "full", "sharpe")) - np.mean([p6v[s]["stitched"]["sharpe"] for s in SEEDS]))
    repro_ok = d_ret < 0.005 and d_sh < 0.005
    w("Reproduction differences vs Phase 6's saved run (BTC seed mean): return %.2e, Sharpe %.2e -> %s." % (
        d_ret, d_sh, "OK" if repro_ok else "FAILED: the round stops (rule 3)"))
    w("")
    w("## Verdict")
    w("")
    if not repro_ok:
        w("**STOPPED: the harness does not reproduce the Phase 6 primary; no variant is graded.**")
        passed = []
    elif passed:
        w("**PASS (historical, not proof): %s.** Proposed for a forward paper book (the session lead and the owner decide)." %
          ", ".join(passed))
    else:
        best = max(ROUND_VARIANTS, key=lambda vn: (G[vn]["met"], np.mean(seedvals(b["fees"][H]["variants"][vn], "full", "sharpe"))))
        fails = [k for k, ok in G[best]["rules"].items() if not ok]
        w("**No pass in round 1.** Best by rules met: %s, %d of %d rules; fails %s." % (
            LABELS[best], G[best]["met"], G[best]["of"], ", ".join("`%s`" % f for f in fails)))
    w("")
    # headline comparison
    w("## Headline: BTC and ETH, full span, 0.10% a side, seed means, against spot buy-and-hold")
    w("")
    w("| Variant | BTC return | BTC mean CAGR | BTC Sharpe (seeds) | BTC max DD (worst seed) | BTC trades/yr (max seed) | "
      "ETH return | ETH Sharpe | ETH max DD (worst) | Rules met |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for vn in [REF] + ROUND_VARIANTS:
        vb, ve = b["fees"][H]["variants"][vn], e["fees"][H]["variants"][vn]
        sh = seedvals(vb, "full", "sharpe")
        w("| %s | %s | %s | %.2f (%s) | %.0f%% (%.0f%%) | %.0f (%.0f) | %s | %.2f | %.0f%% (%.0f%%) | %d / %d |" % (
            LABELS[vn], pct(np.mean(seedvals(vb, "full", "total_return"))), pct(np.mean(seedvals(vb, "full", "cagr"))),
            np.mean(sh), ", ".join("%.2f" % x for x in sh), 100 * np.mean(seedvals(vb, "full", "max_drawdown")),
            100 * max(seedvals(vb, "full", "max_drawdown")), np.mean(seedvals(vb, "full", "trades_per_year")),
            max(seedvals(vb, "full", "trades_per_year")), pct(np.mean(seedvals(ve, "full", "total_return"))),
            np.mean(seedvals(ve, "full", "sharpe")), 100 * np.mean(seedvals(ve, "full", "max_drawdown")),
            100 * max(seedvals(ve, "full", "max_drawdown")), G[vn]["met"], G[vn]["of"]))
    for a, lab in (("BTCUSDT", "BTC"), ("ETHUSDT", "ETH")):
        st = res["assets"][a]["fees"][H]["bench"]["buy_hold_spot"]["full"]["stitched"]
        w("| %s spot buy-and-hold | %s | %s | %.2f | %.0f%% | 0 | | | | |" % (lab, pct(st["total_return"]), pct(st["cagr"]),
                                                                       st["sharpe"], 100 * st["max_drawdown"]))
    w("")
    w("The reference row is Phase 6 as it is (perp accounting): graded for information, not a round-1 variant.")
    w("")
    # rules table
    w("## Every rule, every variant (PASS / fail)")
    w("")
    keys = list(G[ROUND_VARIANTS[0]]["rules"])
    w("| Rule | " + " | ".join(vn.split("_", 1)[0] if vn != REF else "REF" for vn in [REF] + ROUND_VARIANTS) + " |")
    w("|---|" + "---|" * (1 + len(ROUND_VARIANTS)))
    for k in keys:
        w("| `%s` | " % k + " | ".join("PASS" if G[vn]["rules"][k] else "fail" for vn in [REF] + ROUND_VARIANTS) + " |")
    w("| fold share (seed-mean per fold), full / to 2025-11-11 | " + " | ".join(
        "%.0f%% / %.0f%%" % (100 * G[vn]["fold_share"], 100 * G[vn]["fold_share_dev"]) for vn in [REF] + ROUND_VARIANTS) + " |")
    w("| fold share by seed 0 / 1 / 2 | " + " | ".join(
        " / ".join("%.0f%%" % (100 * G[vn]["fold_share_by_seed"][s]) for s in SEEDS) for vn in [REF] + ROUND_VARIANTS) + " |")
    w("| seed-mean book Sharpe - B&H (p; threshold %.4f) | " % (0.05 / N_CUM) + " | ".join(
        "%+.2f (p %.3f)" % (b["book"][vn]["sharpe_minus_bh"], b["book"][vn]["p"]) for vn in [REF] + ROUND_VARIANTS) + " |")
    w("| Sharpe edge needed at that threshold / with the strategy loop's 1,910 added | " + " | ".join(
        "%.2f / %.2f" % (b["book"][vn]["edge_needed"], b["book"][vn]["edge_needed_with_strategy_loop"]) for vn in [REF] + ROUND_VARIANTS) + " |")
    w("| deflated-Sharpe probability (N = %d) | " % N_CUM + " | ".join("%.3f" % b["book"][vn]["dsr"] for vn in [REF] + ROUND_VARIANTS) + " |")
    w("")
    w("Bootstrap on daily returns of the seed-mean book (per-bar mean of the three seeds' net returns) against spot "
      "buy-and-hold, BTC full span; Bonferroni over %d RL variants." % N_CUM)
    w("")
    for a, lab in (("BTCUSDT", "BTCUSDT"), ("ETHUSDT", "ETHUSDT")):
        w("## %s, 2020-10-01 .. 2026-11-11, 0.10%% a side" % lab)
        w("")
        w(table(res, a, "fee_0.10%", "full"))
        w("")
        w("### %s, 0.05%% a side" % lab)
        w("")
        w(table(res, a, "fee_0.05%", "full"))
        w("")
        w("### %s, up to 2025-11-11, 0.10%%" % lab)
        w("")
        w(table(res, a, "fee_0.10%", "dev"))
        w("")
    # calendar years
    for a in POOL:
        y = res["assets"][a]["years"]
        yrs = sorted(y["buy_hold_spot"])
        w("## Calendar-year net returns, %s, 0.10%% (seed means; 2020 from 1 Oct, 2026 to 11 Nov)" % a)
        w("")
        w("| Variant | " + " | ".join(yrs) + " |")
        w("|---|" + "---|" * len(yrs))
        for vn in [REF] + ROUND_VARIANTS:
            w("| %s | " % LABELS[vn] + " | ".join(pct(np.mean([y[vn][s][yy] for s in SEEDS]), 0) for yy in yrs) + " |")
        for bn, lab in (("buy_hold_spot", "Buy-and-hold (spot)"), ("buy_hold_perp", "Buy-and-hold (perp)"), ("momentum", "Momentum")):
            w("| %s | " % lab + " | ".join(pct(y[bn][yy], 0) for yy in yrs) + " |")
        w("")
    # long / short and fold split
    w("## Long vs short, and the agent's folds vs the fallback folds (0.10%, full span, seed means)")
    w("")
    w("| Variant | Asset | Long / short / flat (time) | Time above 1x | Net from long bars /yr | Net from short bars /yr | "
      "Return in agent folds (by seed) | Return in fallback folds (by seed) |")
    w("|---|---|---|---|---|---|---|---|")
    for vn in [REF] + ROUND_VARIANTS:
        for a in POOL:
            sd = res["assets"][a]["sides"][vn]
            m_ = lambda k: float(np.mean([sd[s][k] for s in SEEDS]))
            pb = res["assets"][a]["book"][vn]["per_seed"]
            w("| %s | %s | %.0f%% / %.0f%% / %.0f%% | %.0f%% | %s | %s | %s | %s |" % (
                LABELS[vn], a, 100 * m_("long"), 100 * m_("short"), 100 * m_("flat"), 100 * m_("above_1x"),
                pct(m_("net_long_py")), pct(m_("net_short_py")),
                ", ".join(pct(pb[s]["ret_agent_folds"], 0) for s in SEEDS),
                ", ".join(pct(pb[s]["ret_fallback_folds"], 0) for s in SEEDS)))
    w("")
    w("Fallback folds (validation net Sharpe under 0.5: the daily momentum position is held instead of the agent's) cover "
      "%s of the BTC span by seed. In V3-V5 they are held at a 1.5x request (agent = trend by construction)." % ", ".join(
          "%.0f%%" % (100 * b["book"][REF]["per_seed"][s]["fallback_share"]) for s in SEEDS))
    w("")
    w("## Decision counts (agent changes over the span, by seed; min hold refusals)")
    w("")
    for a in POOL:
        ds = res["assets"][a]["decision_stats"]
        w("- %s: hold 4 bars: %s; hold 16 bars: %s" % (a, ", ".join("%d (%d)" % (ds[REF][s]["changes"], ds[REF][s]["min_hold_refusals"]) for s in SEEDS),
                                                     ", ".join("%d (%d)" % (ds["V2_spot_lean"][s]["changes"], ds["V2_spot_lean"][s]["min_hold_refusals"]) for s in SEEDS)))
    w("")
    w("Machine-readable: `research/out/rl_loop/round1_results.json`; state: `research/out/rl_loop/loop_state.json`. "
      "Nothing here is wired into the live engine or the forward books.")
    md = "\n".join(L) + "\n"
    with open(os.path.join(OUT, "round1_report.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    with open(os.path.join(OUT, "round1_grades.json"), "w", encoding="utf-8") as fh:
        json.dump(clean({"floors": fl, "grades": G}), fh, indent=1)
    log("report written: research/out/rl_loop/round1_report.md")
    return G


def main():
    if "--report" in sys.argv:
        with open(RES, encoding="utf-8") as fh:
            res = json.load(fh)
        report(res)
        return
    acquire_lock("rl_loop round 1 evaluation")
    try:
        res = compute()
    finally:
        release_lock()
    res = json.loads(json.dumps(clean(res)))
    report(res)


if __name__ == "__main__":
    main()
