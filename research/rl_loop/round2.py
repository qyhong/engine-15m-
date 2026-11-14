# -*- coding: utf-8 -*-
"""RL loop round 2 (research/rl_loop/LOOP_RL.md "Round 2", registered 13 Nov 2026 04:31 UTC). Paper only.

    py -3 research/rl_loop/round2.py --train    retrain r_missed on spot-long accounting (R2-d/e/f models; resumable;
                                                below-normal priority, memory-gated, heavy-job lock per seed)
    py -3 research/rl_loop/round2.py --eval     evaluate all six variants (+ the Phase 6 reproduction) and write the report
    py -3 research/rl_loop/round2.py --report   rebuild the report from research/out/rl_loop/round2_results.json

Reuses round1.py (lock, memory pause, the spot-aware risk manager, metrics, grading). Read-only use of engine15.rl and
research/harness (the retrain patches learn6's learner and validation score inside this process only); writes only under
research/out/rl_loop/.
"""
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

ROOT, OUT, POOL, SEEDS = R1.ROOT, R1.OUT, R1.POOL, R1.SEEDS
log, acquire_lock, release_lock = R1.log, R1.acquire_lock, R1.release_lock
MODELS = os.path.join(OUT, "models_r2")
VNAME = "r_missed_spot"
RES = os.path.join(OUT, "round2_results.json")
N_ROUND1 = 5
ROUND_VARIANTS = ["R2a_blend_fundcap", "R2b_blend_125", "R2c_lean_longlever", "R2d_retrain_spot_lean",
                  "R2e_retrain_spot_blend", "R2f_retrain_spot_longlever"]
N_CUM = R1.N_PHASE6 + N_ROUND1 + len(ROUND_VARIANTS)          # 19
COMPARE = ["V2_spot_lean", "V5_spot_lean_blend"]              # round 1, shown for comparison (not re-graded, not counted)
REF = R1.REF
LABELS = dict(R1.LABELS)
LABELS.update({"V2_spot_lean": "V2 spot_lean (round 1, comparison)",
               "V5_spot_lean_blend": "V5 spot_lean_blend (round 1, comparison)",
               "R2a_blend_fundcap": "R2-a blend_fundcap: V5, above 1x only when funding is cheap",
               "R2b_blend_125": "R2-b blend_125: side + 0.25 x trend",
               "R2c_lean_longlever": "R2-c lean_longlever: 1.5x only on longs with the trend",
               "R2d_retrain_spot_lean": "R2-d retrain_spot_lean: spot-trained agent, V2 execution",
               "R2e_retrain_spot_blend": "R2-e retrain_spot_blend: spot-trained agent, V5 execution",
               "R2f_retrain_spot_longlever": "R2-f retrain_spot_longlever: spot-trained agent, R2-c execution"})
SHORT = {REF: "REF", "V2_spot_lean": "V2*", "V5_spot_lean_blend": "V5*", "R2a_blend_fundcap": "R2-a",
         "R2b_blend_125": "R2-b", "R2c_lean_longlever": "R2-c", "R2d_retrain_spot_lean": "R2-d",
         "R2e_retrain_spot_blend": "R2-e", "R2f_retrain_spot_longlever": "R2-f"}
# variant -> (models, min hold bars, re-size band, request rule)
EXEC = {"V2_spot_lean": ("p6", 16, 0.40, "s"), "V5_spot_lean_blend": ("p6", 16, 0.40, "blend"),
        "R2a_blend_fundcap": ("p6", 16, 0.40, "blend_fundcap"), "R2b_blend_125": ("p6", 16, 0.40, "blend125"),
        "R2c_lean_longlever": ("p6", 16, 0.40, "longlever"), "R2d_retrain_spot_lean": ("r2", 16, 0.40, "s"),
        "R2e_retrain_spot_blend": ("r2", 16, 0.40, "blend"), "R2f_retrain_spot_longlever": ("r2", 16, 0.40, "longlever")}


def spot_f(a):
    """Funded part of a position under spot-long accounting: long up to 1x unfunded; shorts and the part above 1x perp."""
    a = np.asarray(a, dtype=float)
    return np.maximum(a - 1.0, 0.0) + np.minimum(a, 0.0)


# ---------------------------------------------------------------- the retrain (R2-d's models)
def _patch_learn6():
    """Spot-long accounting in the learner (reward incl. the reference term) and in the validation score; this process only."""
    from engine15.rl import learn6, metrics, policy3
    from engine15.rl.models4 import cost_matrix, q_from_w
    from engine15.rl.qagent import funded_vector
    Base = learn6.Learner6
    if getattr(Base, "_r2_spot", False):
        return learn6

    class Learner6Spot(Base):
        _r2_spot = True

        def _targets(self, raw, rd, idx, masks):
            torch = self.torch
            c = self.cfg
            assert c.get("funding_mode") == "spot"
            A, B = self.A, len(idx)
            n = int(c.get("n_step", 1))
            gamma = float(c["gamma"])
            scale, cm, ra = float(c["reward_scale"]), float(c["cost_mult"]), float(c.get("risk_aversion", 0.0))
            a = self.act_t.view(1, A)
            idle = (1.0 - a.abs())
            F = torch.tensor(funded_vector(self.actions, "spot")).view(1, A)
            r = torch.zeros(B, A)
            for j in range(n):
                ij = idx + j
                col = lambda key: torch.from_numpy(rd[key][ij]).view(B, 1)
                ret = a * col("rpx") - F * col("rate")
                if self.kind == "missed" and self.value:
                    ref = col("ref")
                    ret = ret - self.value * idle * (ref * col("rpx") - torch.clamp(ref, max=0.0) * col("rate"))
                elif self.kind == "flat" and self.value:
                    ret = ret - idle * (self.value * 2.0 / 96.0) * col("c1")
                r = r + (gamma ** j) * scale * (col("k") * ret - ra * a * a * col("v"))
            i1 = idx + n
            x1 = torch.from_numpy(self._x(raw[i1]))
            k1 = torch.from_numpy(rd["k"][i1]).view(B, 1, 1)
            c11 = torch.from_numpy(rd["c1"][i1]).view(B, 1, 1)
            cost1 = scale * cm * k1 * c11 * self.D_t.view(1, A, A)
            w1o = self.net(x1).view(B, 1, A) - cost1
            w1t = self.tgt(x1).view(B, 1, A) - cost1
            best = w1o.argmax(dim=2, keepdim=True)
            v1 = w1t.gather(2, best).squeeze(2)
            return r + (gamma ** n) * v1

    def spot_policy_metrics(W, rd, lo, hi, actions, qcfg, min_hold):
        """models4.policy_metrics with the spot-long net: a x rpx - f(a) x rate - c1 x |change|."""
        acts = np.asarray(actions, dtype=float)
        Q = q_from_w(np.asarray(W, np.float32), rd["k"][lo:hi], rd["c1"][lo:hi], cost_matrix(acts), qcfg)
        ip, st = policy3.decide(Q, acts, int(np.argmin(np.abs(acts))), int(min_hold))
        tgt = acts[ip]
        prev = np.concatenate([[0.0], tgt[:-1]])
        rpx = np.asarray(rd["rpx"][lo:hi], dtype=float)
        rate = np.asarray(rd["rate"][lo:hi], dtype=float)
        c1 = np.asarray(rd["c1"][lo:hi], dtype=float)
        r = tgt * rpx - spot_f(tgt) * rate - c1 * np.abs(tgt - prev)
        out = policy3.quick_metrics(r, tgt)
        out["gross_sharpe"] = metrics.sharpe(tgt * rpx)
        out["changes"] = st["changes"]
        return out

    learn6.Learner6 = Learner6Spot
    learn6.policy_metrics = spot_policy_metrics
    return learn6


def _fold_done(d, f):
    return os.path.exists(os.path.join(d, "rec_f%02d_pool.json" % f)) and all(
        os.path.exists(os.path.join(d, "w_f%02d_%s.npy" % (f, a))) for a in POOL)


def train():
    import gc
    from engine15.rl import phase4, phase5, phase6, resources
    from engine15.rl.phase3 import _jdump, _npsave
    learn6 = _patch_learn6()
    cfg = phase6.load_cfg()
    phase6.check_frozen(cfg)
    resources.low_priority()
    resources.torch_lean(cfg["qagent"].get("torch_threads", 2))
    pause = resources.MemoryPause(1500, 600, 20, log)
    assets_by_name, fts = phase5._assets_and_folds(cfg)
    assets = [learn6.add_reference(assets_by_name[a]) for a in POOL]
    cols = phase4.input_columns(cfg, assets[0], "full")
    ci = assets[0].cols(cols)
    qcfg = dict(cfg["qagent"])
    qcfg["funding_mode"] = "spot"
    mh = int(cfg["policy"]["min_hold_bars"])
    sh = cfg["phase6"]["variants_train"]["r_missed"]
    seeds = [int(s) for s in cfg["seeds"]]
    total = len(seeds) * len(fts)
    done_n = sum(_fold_done(os.path.join(MODELS, VNAME, "s%d" % s), ft["i"]) for s in seeds for ft in fts)
    log("round 2 retrain %s in %s: %d of %d fold fits already done; free %.0f MB" % (
        VNAME, MODELS, done_n, total, resources.free_mb() or -1))
    t0, fit_secs = time.time(), []
    for si, seed in enumerate(seeds):
        d = os.path.join(MODELS, VNAME, "s%d" % seed)
        os.makedirs(d, exist_ok=True)
        todo = [ft for ft in fts if not _fold_done(d, ft["i"])]
        if not todo:
            continue
        acquire_lock("rl_loop round 2 retrain %s seed %d" % (VNAME, seed))
        try:
            for ft in todo:
                f = ft["i"]
                while os.path.exists(R1.FWD_LOCK):
                    log("forward5 update.lock held; training paused 60 s")
                    time.sleep(60)
                where = "%s s%d fold %d" % (VNAME, seed, f)
                pause.before_start(where)
                ts = time.time()
                geo = dict((A.name, phase4.geo_for(A, ft, "expanding")) for A in assets)
                W, rec = learn6.q_fold6(assets, POOL, ci, geo, cfg["q"], qcfg, cfg["actions"], mh, seed * 1000 + f, sh,
                                        pause, where)
                for a in POOL:
                    _npsave(W[a], os.path.join(d, "w_f%02d_%s.npy" % (f, a)))
                rec.update({"fold": f, "variant": VNAME, "columns": cols, "geo": geo, "free_mb": resources.free_mb(),
                            "accounting": "spot-long (reward incl. reference term, validation score)"})
                _jdump(rec, os.path.join(d, "rec_f%02d_pool.json" % f))
                done_n += 1
                fit_secs.append(time.time() - ts)
                eta = np.mean(fit_secs[-10:]) * (total - done_n) / 60.0
                log("%s: beta %s; %s [%.1f min this fit, %.0f min elapsed, %d/%d done, ETA %.0f min, free %.0f MB]" % (
                    where, rec["chosen"]["shaping_value"], "; ".join(
                        "%s val %+.2f%s" % (a, rec["assets"][a]["val"]["sharpe"], " -> fallback" if rec["assets"][a]["fallback"] else "")
                        for a in POOL), fit_secs[-1] / 60, (time.time() - t0) / 60, done_n, total, eta,
                    resources.free_mb() or -1))
                del W
                gc.collect()
        finally:
            release_lock()
        if si < len(seeds) - 1:
            log("seed %d trained; lock released, 90 s gap so the other heavy job can interleave" % seed)
            time.sleep(90)
    _jdump({"root": MODELS, "variant": VNAME, "minutes_this_call": round((time.time() - t0) / 60, 1),
            "memory_events": pause.events}, os.path.join(MODELS, "done.json"))
    log("round 2 retrain complete (%.0f min this call)" % ((time.time() - t0) / 60))


def main():
    if "--train" in sys.argv:
        train()
        return
    import round2_eval
    round2_eval.main()


if __name__ == "__main__":
    main()
