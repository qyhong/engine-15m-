# -*- coding: utf-8 -*-
"""phase3 -- a continuously learning 15m agent, judged out of sample after costs (paper only).

    py -3 -m engine15.rl phase3 [--offline] [--seeds N] [--assets BTCUSDT,ETHUSDT] [--fresh]

Per asset (BTC headline, ETH robustness, same frozen settings): data -> Phase 3 features (look-ahead checked on
the real data) -> for each agent family (base / meta-label / core-satellite) and seed, one after another:
fold models (fresh 12-month trains, (a) static), continual fine-tuning inside each fold ((c)) and, for the base
family, one never-reset continual model ((b)) -> Q values for every out-of-sample bar, each from a model trained
only on data before it -> the decision rules (base, filters 1-4, harnesses 5-6) -> the Phase 3 risk manager ->
the shared backtester at both fees -> per fold and stitched metrics, break-even fees, flags, verdict.

Everything heavy is saved as it finishes (models3/<work hash>/<asset>/<family>/...): a rerun with the same frozen
config resumes and recomputes only what is missing. Lean by design: below-normal priority, torch on 2 threads,
seeds and families in sequence, a pause (not a failure) when free memory falls under the floor.
"""
import copy
import gc
import json
import os
import time

import numpy as np

from . import (baselines3, benchmarks, costs, data, features, features3, metrics, policy3, qagent, report3, resources, risk3,
               train, walkforward)
from .config import config_hash, for_asset, new_run, resolve
from .continual import full_train, run_span, eval_q, q_of, neutral_w, is_fallback
from .env import Market
from .phase1 import KEYS, _seed_stats
from .qagent import Learner

MODES = {"a": "static", "b": "continual", "c": "continual_retrain"}


# ---------------------------------------------------------------- set-up
def seeds_of(cfg, n):
    s = list(cfg["seeds"])
    if n is None:
        return s
    n = int(n)
    return s[:n] if n <= len(s) else s + [max(s) + 1 + i for i in range(n - len(s))]


def load_bars(cfg, offline, log):
    src = cfg["assets"].get(cfg["data"]["symbol"], {}).get("source", "rl_store")
    if src == "engine_file":                       # the engine's own 15m file, read only, via the loop's loader
        core, _ = baselines3._harness()
        bars, fund = core.load(cfg["data"]["symbol"], dev_only=False)
        drep = {"source": "engine data/%s_15m.csv (read only)" % cfg["data"]["symbol"].lower()}
    else:
        bars, fund, drep = data.update_all(cfg, log=log, offline=offline)
    if not len(bars):
        raise SystemExit("no bars stored for %s under %s; run without --offline first" % (cfg["data"]["symbol"],
                                                                                         resolve(cfg["data"]["dir"])))
    end = cfg.get("data_end")
    if end:
        import pandas as pd
        cut = pd.Timestamp(end, tz="UTC")
        bars = bars[bars.index < cut]
        fund = fund[np.asarray(fund["settle_ms"]) < int(cut.value // 10**6)]
    return bars, fund, drep


def build_market(cfg, bars, fund, model=None):
    feats = features3.build(bars, fund, cfg["features"]).astype("float32")
    m = Market(bars, fund, feats, model or costs.from_cfg(cfg))
    del feats
    return m


def family_actions(cfg, fam):
    return list(cfg["families"][fam]["actions"])


def family_masks(cfg, fam, market, ctx=None):
    """Per-bar allowed actions for a family (None = all allowed)."""
    fc = cfg["families"][fam]
    acts = np.asarray(family_actions(cfg, fam), float)
    if fc.get("residual"):                          # the total (baseline + adjustment) never goes short
        bt = ctx["baselines"][fc["baseline"]]
        return (bt[:, None] + acts[None, :]) >= -1e-9
    rule = fc.get("mask")
    if not rule:
        return None
    if rule == "momentum_direction":
        d = np.nan_to_num(market.raw[:, market.col("mom_signal")].astype(float))
        return (acts[None, :] == 0) | (np.sign(acts)[None, :] == d[:, None])
    raise ValueError(rule)


def htf_mask(market, actions):
    """Filter 3: a long only if the 4h trend AND the momentum signal are up, a short only if both are down."""
    acts = np.asarray(actions, float)
    t4 = np.sign(np.nan_to_num(market.raw[:, market.col("trend_4h")].astype(float)))
    mo = np.nan_to_num(market.raw[:, market.col("mom_signal")].astype(float))
    up, dn = (t4 > 0) & (mo > 0), (t4 < 0) & (mo < 0)
    return (acts[None, :] == 0) | ((acts[None, :] > 0) & up[:, None]) | ((acts[None, :] < 0) & dn[:, None])


def fam_cfg(cfg, fam):
    return cfg["families"][fam]


def fam_qcfg(cfg, fam):
    q = dict(cfg["qagent"])
    fc = fam_cfg(cfg, fam)
    q["funding_mode"] = fc.get("funding", "perp")
    q["neutral_action"] = float(fc.get("neutral", 0.0))
    if fc.get("fallback") is False:
        q["fallback_val_sharpe"] = None
    return q


def fam_context(ctx, fam):
    """(market, rd, bounds, masks) for one family: an extra input column with the baseline's target for families
    built on a loop rule, the residual funding multiplier, and the dev-span folds for those families."""
    cfg, m, rd = ctx["cfg"], ctx["market"], ctx["rd"]
    fc = fam_cfg(cfg, fam)
    base_name = fc.get("baseline")
    if base_name:
        bt = ctx["baselines"][base_name]
        mm = object.__new__(type(m))
        mm.__dict__.update(m.__dict__)
        mm.raw = np.ascontiguousarray(np.hstack([m.raw, bt[:, None].astype(np.float32)]))
        mm.columns = list(m.columns) + ["base_" + base_name]
        rdf = dict(rd)
        if fc.get("residual"):
            rdf["fmult"] = baselines3.funded_multiplier(bt)
        m, rd = mm, rdf
    bounds = ctx["bounds_dev"] if fc.get("span") == "dev" else ctx["bounds"]
    masks = family_masks(cfg, fam, m, ctx)
    return m, rd, bounds, masks


def bc_targets(ctx, fam):
    fc = fam_cfg(ctx["cfg"], fam)
    if not fc.get("warm_start"):
        return None
    acts = np.asarray(family_actions(ctx["cfg"], fam), float)
    bt = ctx["baselines"][fc["baseline"]]
    tgt = np.abs(bt[:, None] - acts[None, :]).argmin(axis=1)
    prev = np.concatenate([[tgt[0]], tgt[:-1]])
    return (tgt, prev, int(ctx["cfg"]["qagent"]["bc_steps"]))


def work_hash(cfg):
    key = dict((k, cfg[k]) for k in ("features", "families", "qagent", "policy", "continual", "train") if k in cfg)
    key.update({"walkforward": cfg["walkforward"], "costs": cfg["costs"], "data_end": cfg.get("data_end")})
    return config_hash(key)


# ---------------------------------------------------------------- training (resumable)
class Store:
    def __init__(self, root):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def p(self, *parts):
        d = os.path.join(self.root, *parts[:-1])
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, parts[-1])

    def has(self, *parts):
        return os.path.exists(os.path.join(self.root, *parts))


def _jdump(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, default=str)
    os.replace(tmp, path)


def _npsave(arr, path):
    tmp = path + ".tmp.npy"
    np.save(tmp, arr)
    os.replace(tmp, path)


def train_family(ctx, fam, seed, log, pause):
    """Fold models + (a) / (c) Q values per fold (+ (b) for the base family). Skips whatever is saved."""
    cfg, st = ctx["cfg"], ctx["store"]
    m, rd, bounds, masks = fam_context(ctx, fam)
    acts = family_actions(cfg, fam)
    qc, pc = fam_qcfg(cfg, fam), cfg["policy"]
    bc = bc_targets(ctx, fam)
    cad = int(cfg["continual"]["cadence_days"])
    modes = cfg["families"][fam]["modes"]
    tag = "s%d" % seed
    for f, b in enumerate(bounds):
        where = "%s %s %s fold %d" % (ctx["asset"], fam, tag, f)
        need_c = "c" in modes and not st.has(fam, tag, "q_c_f%02d.npy" % f)
        need_a = not st.has(fam, tag, "q_a_f%02d.npy" % f)
        if st.has(fam, tag, "fold_f%02d.pt" % f) and st.has(fam, tag, "fold_f%02d.json" % f):
            L = None
        else:
            pause.before_start(where)
            t0 = time.time()
            L, rec = full_train(m, rd, b, qc, pc, acts, seed * 1000 + f, masks, pause, where, bc=bc)
            rec.update({"fold": f, "free_mb": resources.free_mb()})
            if f == 0:
                _npsave(L.w(m.raw[b["val_lo"]:b["tr_hi"]]), st.p(fam, tag, "q_val_f00.npy"))
            L.save(st.p(fam, tag, "fold_f%02d.pt" % f), {"fold": f, "asset": ctx["asset"], "family": fam})
            _jdump(rec, st.p(fam, tag, "fold_f%02d.json" % f))
            log("%s: %d steps (kept check %d%s), train Sharpe %+.2f, val Sharpe %+.2f, %.0fs, free %.0f MB  [%.0f min]"
                % (where, rec["steps_run"], rec["kept_check"], ", neutral fallback" if rec["fallback"] else "",
                   rec["train"]["sharpe"], rec["val"]["sharpe"],
                   time.time() - t0, resources.free_mb() or -1, (time.time() - ctx["t0"]) / 60))
        if need_a or need_c:
            if L is None:
                L = Learner.load(st.p(fam, tag, "fold_f%02d.pt" % f), qc)
            if need_a:
                _npsave(L.w(m.raw[b["te_lo"]:b["te_hi"]]), st.p(fam, tag, "q_a_f%02d.npy" % f))
            if need_c:
                Q, ups = run_span(L, m, rd, b["te_lo"], b["te_hi"], qc, masks, cad, pause, where)
                _npsave(Q, st.p(fam, tag, "q_c_f%02d.npy" % f))
                del Q
        del L
        gc.collect()
    if "b" in modes:
        L = None
        for f, b in enumerate(bounds):
            where = "%s %s %s fold %d (b)" % (ctx["asset"], fam, tag, f)
            if st.has(fam, tag, "q_b_f%02d.npy" % f) and st.has(fam, tag, "b_end_f%02d.pt" % f):
                continue
            if L is None:
                L = Learner.load(st.p(fam, tag, ("fold_f00.pt" if f == 0 else "b_end_f%02d.pt" % (f - 1))), qc)
            pause.before_start(where)
            tr = eval_q(m, L.q(m.raw, rd, b["tr_lo"], b["val_lo"]), b["tr_lo"], b["val_lo"], acts, pc, masks)
            va = eval_q(m, L.q(m.raw, rd, b["val_lo"], b["tr_hi"]), b["val_lo"], b["tr_hi"], acts, pc, masks)
            Q, ups = run_span(L, m, rd, b["te_lo"], b["te_hi"], qc, masks, cad, pause, where)
            _npsave(Q, st.p(fam, tag, "q_b_f%02d.npy" % f))
            L.save(st.p(fam, tag, "b_end_f%02d.pt" % f), {"fold": f, "mode": "b"})
            _jdump({"fold": f, "train": tr, "val": va, "updates": len(ups)}, st.p(fam, tag, "b_f%02d.json" % f))
            del Q
            gc.collect()
        log("%s %s %s: continual (b) done  [%.0f min]" % (ctx["asset"], fam, tag, (time.time() - ctx["t0"]) / 60))


def neutral_folds(ctx, fam, seed, mode):
    """'Do no harm' per fold: (a)/(c) the fold's fresh model failed its validation check; (b) the continual model's
    Sharpe over the 3 months before the fold (its own causal history) is under the same bar."""
    qc = fam_qcfg(ctx["cfg"], fam)
    out = []
    for r in train_records(ctx, fam, seed, mode):
        out.append(bool(r.get("fallback")) if mode != "b" else bool(is_fallback(r["val"]["sharpe"], qc)))
    return out


def load_q(ctx, fam, seed, mode):
    """Q (n_oos, A, A) over the family's out-of-sample span from the stored W values (q_<mode>_fNN.npy hold W),
    with the neutral policy in folds flagged by neutral_folds()."""
    st = ctx["store"]
    _, rd, b, _ = fam_context(ctx, fam)
    acts = family_actions(ctx["cfg"], fam)
    nf = neutral_folds(ctx, fam, seed, mode)
    neu = float(fam_cfg(ctx["cfg"], fam).get("neutral", 0.0))
    parts = []
    for f in range(len(b)):
        W = np.load(st.p(fam, "s%d" % seed, "q_%s_f%02d.npy" % (mode, f)))
        parts.append(neutral_w(len(W), acts, neu) if nf[f] else W)
    return q_of(np.concatenate(parts), rd, b[0]["te_lo"], b[-1]["te_hi"], ctx["cfg"]["qagent"], acts)


def train_records(ctx, fam, seed, mode):
    st = ctx["store"]
    out = []
    _, _, b, _ = fam_context(ctx, fam)
    for f in range(len(b)):
        name = ("b_f%02d.json" if mode == "b" else "fold_f%02d.json") % f
        with open(st.p(fam, "s%d" % seed, name), encoding="utf-8") as fh:
            r = json.load(fh)
        if mode == "b":
            r["fallback"] = bool(is_fallback(r["val"]["sharpe"], fam_qcfg(ctx["cfg"], fam)))
        out.append(r)
    return out


# ---------------------------------------------------------------- decisions -> targets
def choose_per_fold(ctx, fam, seed, mode, Qoos, grid, kind, acts, masks):
    """Filters 2 and 4: the threshold for fold f is chosen from `grid` by net Sharpe (0.10%, no risk manager) over
    the 3 months BEFORE fold f as the variant actually ran them (fold 0: the fold-0 model on its validation slice).
    -> (per-bar array over the out-of-sample span, list of choices)."""
    m, rd, bounds = ctx["market"], ctx["rd"], ctx["bounds"]
    lo0 = bounds[0]["te_lo"]
    pc = ctx["cfg"]["policy"]
    vc = ctx["cfg"]["variants"]
    zero = int(np.argmin(np.abs(np.asarray(acts, float))))
    out = np.zeros(bounds[-1]["te_hi"] - lo0, dtype=np.float32 if kind == "thr" else bool)
    picks = []
    for f, b in enumerate(bounds):
        if f == 0:
            plo, phi = b["val_lo"], b["tr_hi"]
            Qp = q_of(np.load(ctx["store"].p(fam, "s%d" % seed, "q_val_f00.npy")), rd, plo, phi, ctx["cfg"]["qagent"], acts)
        else:
            plo, phi = bounds[f - 1]["te_lo"], bounds[f - 1]["te_hi"]
            Qp = Qoos[plo - lo0:phi - lo0]
        best = None
        for gv in grid:
            arr = per_bar(ctx, kind, gv, plo, phi)
            kw = {"thr": arr} if kind == "thr" else {"gate": arr}
            ip, stt = policy3.decide(Qp, acts, zero, int(pc["min_hold_bars"]), masks=None if masks is None else masks[plo:phi], **kw)
            r, _, pos = policy3.fast_net(m, np.asarray(acts, float)[ip], plo, phi)
            s = metrics.sharpe(r)
            key = (round(s, 6), -stt["changes"], gv)
            if best is None or key > best[0]:
                best = (key, gv)
        picks.append({"fold": f, "value": best[1], "prior_sharpe": best[0][0]})
        out[b["te_lo"] - lo0:b["te_hi"] - lo0] = per_bar(ctx, kind, best[1], b["te_lo"], b["te_hi"])
    return out, picks


def per_bar(ctx, kind, value, lo, hi):
    m, rd = ctx["market"], ctx["rd"]
    vc = ctx["cfg"]["variants"]
    if kind == "thr":           # confidence gate: advantage must beat value x round trip (reward units)
        return (float(value) * float(ctx["cfg"]["qagent"]["reward_scale"]) * rd["k"][lo:hi] * 2.0 * rd["c1"][lo:hi]).astype(np.float32)
    H = float(vc["vol_gate"]["hold_bars"])
    return m.vol[lo:hi] * np.sqrt(H) >= float(value) * 2.0 * rd["c1"][lo:hi]


DEV_FAMILY_VARIANTS = {"res_A": "r1_residual_A", "res_B": "r2_residual_B", "ws_A": "w1_warmstart_A",
                       "ws_B": "w2_warmstart_B", "scr_A": "w0_scratch_A", "scr_B": "w0_scratch_B"}


def agent_target(ctx, acts, ip, lo=None, hi=None):
    m, bounds = ctx["market"], ctx["bounds"]
    lo = bounds[0]["te_lo"] if lo is None else lo
    hi = bounds[-1]["te_hi"] if hi is None else hi
    t = np.zeros(m.n)
    t[lo:hi] = np.asarray(acts, float)[ip]
    return t


def decision_runs(ctx, log):
    """-> {variant: {"targets": {seed or 'all': target array}, "stats", "picks", "max_abs", "eval", "span"}}."""
    cfg, m, bounds = ctx["cfg"], ctx["market"], ctx["bounds"]
    lo, hi = bounds[0]["te_lo"], bounds[-1]["te_hi"]
    pc, vc = cfg["policy"], cfg["variants"]
    mh = int(pc["min_hold_bars"])
    out = {}
    seeds = ctx["seeds"]
    base_acts = family_actions(cfg, "base")
    zero = int(np.argmin(np.abs(np.asarray(base_acts, float))))
    hm = htf_mask(m, base_acts)[lo:hi]
    prepared_c = []

    def put(name, seed, t, stt, extra=None, max_abs=1.0, ev="risk3", span="full"):
        d = out.setdefault(name, {"targets": {}, "stats": {}, "picks": {}, "max_abs": max_abs, "eval": ev, "span": span})
        d["targets"][seed] = t
        d["stats"][seed] = stt
        if extra is not None:
            d["picks"][seed] = extra

    fams = ctx["families"]
    for seed in seeds:
        if "base" in fams:
            for mode in fam_cfg(cfg, "base")["modes"]:
                Q = load_q(ctx, "base", seed, mode)
                ip, stt = policy3.decide(Q, base_acts, zero, mh)
                put("agent_" + MODES[mode], seed, agent_target(ctx, base_acts, ip), stt)
                if mode == vc["mode"]:
                    prepared_c.append(policy3.prepare(Q))
                    ip, stt = policy3.decide(Q, base_acts, zero, mh, masks=hm)
                    put("v3_htf_alignment", seed, agent_target(ctx, base_acts, ip), stt)
                    thr, picks = choose_per_fold(ctx, "base", seed, mode, Q, vc["confidence_gate"]["grid"], "thr", base_acts, None)
                    ip, stt = policy3.decide(Q, base_acts, zero, mh, thr=thr)
                    put("v2_confidence_gate", seed, agent_target(ctx, base_acts, ip), stt, picks)
                    gate, picks = choose_per_fold(ctx, "base", seed, mode, Q, vc["vol_gate"]["grid"], "gate", base_acts, None)
                    ip, stt = policy3.decide(Q, base_acts, zero, mh, gate=gate)
                    put("v4_vol_cost_gate", seed, agent_target(ctx, base_acts, ip), stt, picks)
                del Q
                gc.collect()
        for fam, name in [("meta", "v5_meta_label"), ("core", "v6_core_satellite")] + list(DEV_FAMILY_VARIANTS.items()):
            if fam not in fams:
                continue
            fc = fam_cfg(cfg, fam)
            fm, frd, fb, masks = fam_context(ctx, fam)
            flo, fhi = fb[0]["te_lo"], fb[-1]["te_hi"]
            acts = family_actions(cfg, fam)
            start = int(np.argmin(np.abs(np.asarray(acts, float) - float(fc.get("start_position", 0.0)))))
            Q = load_q(ctx, fam, seed, vc["mode"])
            ip, stt = policy3.decide(Q, acts, start, mh, masks=None if masks is None else masks[flo:fhi])
            t = agent_target(ctx, acts, ip, flo, fhi)
            if fc.get("residual"):
                t[flo:fhi] += ctx["baselines"][fc["baseline"]][flo:fhi]
                stt["adjusted_share"] = float(np.mean(np.asarray(acts, float)[ip] != 0))
            put(name, seed, t, stt, max_abs=float(fc.get("max_abs", 1.0)), ev=fc.get("eval", "risk3"),
                span=fc.get("span", "full"))
            del Q
            gc.collect()
    if prepared_c:
        ip, stt = policy3.consensus(prepared_c, base_acts, zero, mh)
        put("v1_seed_consensus", "all", agent_target(ctx, base_acts, ip), stt)
    del prepared_c
    return out


# ---------------------------------------------------------------- evaluation
def break_even_fee(frame, target_sharpe=None):
    """Fee per side at which the stitched net return would be zero (positions held fixed), by bisection on
    [-1%, +5%]. With target_sharpe: the fee at which the net Sharpe equals it instead. -inf: loses even with a
    1% rebate; +inf: still positive at 5%; None: never trades."""
    rg = frame["r_gross"].values
    other = (frame["spread"] + frame["slippage"] + frame["funding"]).values
    tr = np.abs(frame["trade"].values)
    if tr.sum() == 0:
        return None

    def f(fee):
        r = rg - other - fee * tr
        if target_sharpe is None:
            return float(np.sum(np.log1p(np.maximum(r, -0.999999))))
        return metrics.sharpe(r) - target_sharpe
    a, b = -0.01, 0.05
    if f(a) < 0:
        return float("-inf")
    if f(b) > 0:
        return float("inf")
    for _ in range(60):
        c = 0.5 * (a + b)
        if f(c) > 0:
            a = c
        else:
            b = c
    return 0.5 * (a + b)


def _span_ev(frame, wins, lo, hi, ex, bh_sharpe=None):
    ev = walkforward.evaluate(frame, wins)
    fr = frame.iloc[lo:hi]
    span_t = np.asarray(ex)[lo:hi]
    ev["position_mix"] = {"long": float(np.mean(span_t > 0)), "flat": float(np.mean(span_t == 0)),
                          "short": float(np.mean(span_t < 0))}
    ev["mean_abs_position"] = float(np.mean(np.abs(span_t)))
    ev["break_even_fee"] = break_even_fee(fr)
    if bh_sharpe is not None:
        ev["fee_for_bh_sharpe"] = break_even_fee(fr, target_sharpe=bh_sharpe)
    return ev


def evaluate_target(ctx, target, model, max_abs=1.0, use_risk=True, log_events=False, ev_kind=None, span="full",
                    bh=None):
    """target -> [risk manager] -> backtester -> {"full": eval or None, "dev": eval, "risk": info}.
    ev_kind 'spot': the loop's backtester with spot long legs and no risk manager (the loop rules and the agents
    built on them)."""
    bars, fund = ctx["bars"], ctx["fund"]
    out = {"risk": None}
    if ev_kind == "spot":
        frame = baselines3.spot_frame(ctx["smkt"], target, model.fee_side, True)
        ex = np.asarray(target, float)
    else:
        lo, hi = ctx["bounds"][0]["te_lo"], ctx["bounds"][-1]["te_hi"]
        ex = target
        if use_risk:
            rinfo = risk3.apply(ctx["market"].with_model(model), target, lo, hi, dict(ctx["cfg"]["risk3"]),
                                log_events=log_events, max_abs=max_abs if max_abs > 1 else None)
            ex = rinfo["exec"]
            out["risk"] = rinfo
        from . import backtest
        frame = backtest.run(bars, ex, model, fund, max_abs=max_abs)["frame"]
    bh = bh or {}
    if span == "full":
        lo, hi = ctx["bounds"][0]["te_lo"], ctx["bounds"][-1]["te_hi"]
        out["full"] = _span_ev(frame, ctx["wins"], lo, hi, ex, bh.get("full"))
    else:
        out["full"] = None
    dlo, dhi = ctx["bounds_dev"][0]["te_lo"], ctx["bounds_dev"][-1]["te_hi"]
    out["dev"] = _span_ev(frame, ctx["wins_dev"], dlo, dhi, ex, bh.get("dev"))
    del frame
    return out


def run(cfg, offline=False, seeds=None, assets=None, fresh=False, log=print):
    t0 = time.time()
    resources.low_priority()
    resources.torch_lean(cfg["qagent"].get("torch_threads", 2))
    seeds = seeds_of(cfg, seeds)
    cfg = copy.deepcopy(cfg)
    cfg["seeds"] = seeds
    assets = assets or list(cfg["assets"])
    run_id, run_dir = new_run(cfg, "phase3")
    out_dir = resolve(cfg["report"]["out_dir"])
    os.makedirs(out_dir, exist_ok=True)
    mem = cfg["memory"]
    pause = resources.MemoryPause(mem["start_mb"], mem["floor_mb"], mem.get("poll_s", 20), log)
    log("run %s  seeds %s  assets %s  free memory %.0f MB" % (run_id, seeds, assets, resources.free_mb() or -1))
    results = {}
    for asset in assets:
        acfg = for_asset(cfg, asset)
        results[asset] = run_asset(acfg, asset, offline, seeds, fresh, pause, log, t0)
        gc.collect()
    result = {"run_id": run_id, "generated_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "config": cfg,
              "seeds": seeds, "assets": results, "elapsed_min": round((time.time() - t0) / 60, 1),
              "memory_events": pause.events}
    for name in ("phase3_learnability.json", "phase3_riskcheck.json", "phase3_cadence.json", "phase3_diag2.json",
                 "phase3_paper_dryrun.json"):
        pth = os.path.join(out_dir, name)
        if os.path.exists(pth):
            with open(pth, encoding="utf-8") as fh:
                result[name.replace("phase3_", "").replace(".json", "")] = json.load(fh)
    p2 = os.path.join(out_dir, "phase2_summary.json")
    if os.path.exists(p2):
        with open(p2, encoding="utf-8") as fh:
            result["phase2"] = json.load(fh)
    result["flags"] = report3.flags(result)
    result["verdict"] = report3.verdict(result)
    md = report3.markdown(result)
    summ = report3.summary_json(result)
    for d in (out_dir, run_dir):
        with open(os.path.join(d, "phase3_report.md"), "w", encoding="utf-8") as fh:
            fh.write(md)
        _jdump(report3.clean(summ), os.path.join(d, "phase3_summary.json"))
    _jdump(report3.clean(result), os.path.join(run_dir, "phase3_full.json"))
    log("report written: %s in %.0f min" % (os.path.join(out_dir, "phase3_report.md"), (time.time() - t0) / 60))
    result["complete"] = True
    return result


def run_asset(cfg, asset, offline, seeds, fresh, pause, log, t0):
    bars, fund, drep = load_bars(cfg, offline, log)
    pause.before_start(asset + " features")
    m = build_market(cfg, bars, fund)
    n = len(bars)
    cuts = sorted(set(int(c) for c in np.random.default_rng(cfg["seed"]).integers(5000, n - 1, 3)))
    la = features.lookahead_report(lambda b, f: features3.build(b, f, cfg["features"]), bars, fund, cuts)
    log("%s: bars %d (%s .. %s), features %d, real-data look-ahead check %s" % (asset, n, bars.index[0], bars.index[-1],
                                                                            len(m.columns), la))
    wf = cfg["walkforward"]
    wins = walkforward.windows(bars.index, wf["train_months"], wf["test_months"], wf["step_months"], wf["start"],
                               wf["min_test_days"])
    dev_n = baselines3.dev_cut_index(bars.index)
    wins_dev = walkforward.windows(bars.index[:dev_n], wf["train_months"], wf["test_months"], wf["step_months"],
                                   wf["start"], wf["min_test_days"])
    bounds = [train.fold_bounds(bars.index, w, cfg["train"]["validation_months"]) for w in wins]
    bounds_dev = [train.fold_bounds(bars.index, w, cfg["train"]["validation_months"]) for w in wins_dev]
    rd = qagent.reward_arrays(m, cfg["qagent"])
    wh = work_hash(cfg)
    root = os.path.join(resolve(cfg["report"]["models_dir"]), wh, asset)
    if fresh and os.path.isdir(root):
        import shutil
        shutil.rmtree(root)
    gi = os.path.join(resolve(cfg["report"]["models_dir"]), ".gitignore")
    if not os.path.exists(gi):
        os.makedirs(os.path.dirname(gi), exist_ok=True)
        with open(gi, "w") as f:
            f.write("# trained model files: reproducible from the config; not for version control\n*\n!.gitignore\n")
    fams = [f for f in cfg["families"] if asset in cfg["families"][f].get("assets", list(cfg["assets"]))]
    blines = baselines3.targets(bars)
    ctx = {"cfg": cfg, "asset": asset, "market": m, "rd": rd, "bars": bars, "fund": fund, "wins": wins,
           "wins_dev": wins_dev, "bounds": bounds, "bounds_dev": bounds_dev, "store": Store(root), "seeds": seeds,
           "t0": t0, "families": fams, "baselines": blines, "smkt": baselines3.spot_market(bars, fund)}
    log("%s: %d folds, out of sample %s .. %s (dev span to %s, %d folds); families %s; models in %s"
        % (asset, len(wins), wins[0]["test_start"].date(), wins[-1]["test_end"].date(), wins_dev[-1]["test_end"].date(),
           len(wins_dev), fams, root))
    for fam in fams:
        for seed in seeds:
            train_family(ctx, fam, seed, log, pause)
    log("%s: training done (%.0f min); evaluating" % (asset, (time.time() - t0) / 60))
    runs = decision_runs(ctx, log)
    profiles = costs.fee_profiles(cfg)
    targets = benchmarks.all_targets(bars, cfg["benchmarks"])
    res = {"bars": int(n), "first": str(bars.index[0]), "last": str(bars.index[-1]), "columns": m.columns,
           "lookahead_check_on_real_data": dict((str(k), v) for k, v in la.items()), "work_hash": wh, "models_dir": root,
           "windows": [dict((k, str(v.date()) if hasattr(v, "date") else v) for k, v in w.items()) for w in wins],
           "windows_dev": [dict((k, str(v.date()) if hasattr(v, "date") else v) for k, v in w.items()) for w in wins_dev],
           "fees": {}, "families": fams}
    risk_events = []
    oos_full = np.zeros(n, bool)
    oos_full[bounds[0]["te_lo"]:bounds[-1]["te_hi"]] = True
    oos_dev = np.zeros(n, bool)
    oos_dev[bounds_dev[0]["te_lo"]:bounds_dev[-1]["te_hi"]] = True
    for pname, model in profiles.items():
        first = pname == list(profiles)[0]
        B = {}
        for name, tgt in targets.items():
            B[name] = evaluate_target(ctx, np.where(oos_full, tgt.values, 0.0), model, use_risk=False)
        bh = {"full": B["buy_hold"]["full"]["stitched"]["sharpe"], "dev": B["buy_hold"]["dev"]["stitched"]["sharpe"]}
        for name in ("buy_hold", "momentum"):
            e = evaluate_target(ctx, np.where(oos_full, targets[name].values, 0.0), model, use_risk=True)
            e["full"]["risk_counts"] = e["risk"]["counts"]
            B[name + "_risk3"] = e
        B["buy_hold_spot"] = evaluate_target(ctx, np.where(oos_dev, 1.0, 0.0), model, ev_kind="spot", span="dev")
        for bn in ("A", "B"):
            B["baseline_" + bn] = evaluate_target(ctx, np.where(oos_dev, blines[bn], 0.0), model, ev_kind="spot", span="dev")
        bh["dev_spot"] = B["buy_hold_spot"]["dev"]["stitched"]["sharpe"]
        rn = [k for k in B if k.startswith("random_s")]
        full_b = {"buy_hold": B["buy_hold"]["full"], "momentum": B["momentum"]["full"],
                  "random": _seed_stats(dict((k, B[k]["full"]) for k in rn), rn),
                  "random_windows": dict((k, B[k]["full"]["windows"]) for k in rn),
                  "buy_hold_risk3": B["buy_hold_risk3"]["full"], "momentum_risk3": B["momentum_risk3"]["full"]}
        dev_b = {"buy_hold": B["buy_hold"]["dev"], "buy_hold_spot": B["buy_hold_spot"]["dev"],
                 "momentum": B["momentum"]["dev"], "baseline_A": B["baseline_A"]["dev"], "baseline_B": B["baseline_B"]["dev"],
                 "buy_hold_risk3": B["buy_hold_risk3"]["dev"], "momentum_risk3": B["momentum_risk3"]["dev"],
                 "random": _seed_stats(dict((k, B[k]["dev"]) for k in rn), rn)}
        del B
        gc.collect()
        var_full, var_dev = {}, {}
        for vname, d in runs.items():
            pf, pd_ = {}, {}
            for seed, tgt in d["targets"].items():
                lg = first and seed in (seeds[0], "all") and d["eval"] != "spot"
                e = evaluate_target(ctx, tgt, model, d["max_abs"], True, log_events=lg, ev_kind=d["eval"], span=d["span"],
                                    bh={"full": bh["full"], "dev": bh["dev_spot"] if d["eval"] == "spot" else bh["dev"]})
                extra = {"decision_stats": d["stats"][seed]}
                if d["picks"].get(seed):
                    extra["threshold_picks"] = d["picks"][seed]
                if e["risk"] is not None:
                    extra["risk_counts"] = e["risk"]["counts"]
                    if lg and e["risk"]["events"]:
                        risk_events += [dict(x, variant=vname, seed=seed) for x in e["risk"]["events"][:20000]]
                if d["eval"] != "spot":
                    raw = evaluate_target(ctx, tgt, model, d["max_abs"], False, span=d["span"])
                    rr = raw["full"] or raw["dev"]
                    extra["without_risk_manager"] = dict(rr["stitched"], break_even_fee=rr["break_even_fee"])
                for key, dst in (("full", pf), ("dev", pd_)):
                    if e[key] is not None:
                        e[key].update(extra)
                        dst[str(seed)] = e[key]
            for src, dst in ((pf, var_full), (pd_, var_dev)):
                if src:
                    dst[vname] = {"seeds": src, "mean": _seed_stats(src, sorted(src)) if len(src) > 1 else None,
                                  "eval": d["eval"], "span": d["span"]}
        res["fees"][pname] = {"model": model.as_dict(), "bench": full_b, "variants": var_full,
                              "dev": {"bench": dev_b, "variants": var_dev}}
        log("%s %s evaluated (%.0f min)" % (asset, pname, (time.time() - t0) / 60))
        gc.collect()
    tr = {}
    for fam in fams:
        for mode in cfg["families"][fam]["modes"]:
            for seed in seeds:
                recs = train_records(ctx, fam, seed, mode)          # (c) shares (a)'s fold models: same records
                tr["%s_%s_s%d" % (fam, mode, seed)] = [{"fold": i, "train_sharpe": x["train"]["sharpe"],
                                                         "val_sharpe": x["val"]["sharpe"],
                                                         "kept_check": x.get("kept_check"), "fallback": x.get("fallback"),
                                                         "steps": x.get("steps_run")} for i, x in enumerate(recs)]
    res["training"] = tr
    out_dir = resolve(cfg["report"]["out_dir"])
    report3.write_risk_log(os.path.join(out_dir, "phase3_risk_log_%s.csv" % asset.lower()), risk_events)
    del ctx, m, rd
    gc.collect()
    return res
