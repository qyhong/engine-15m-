# -*- coding: utf-8 -*-
"""RL loop round 3 (research/rl_loop/LOOP_RL.md "Round 3", registered 13 Nov 2026 08:02 UTC). Paper only.

    py -3 research/rl_loop/round3.py --train    retrain r_missed as a long/flat agent (R3-d models; resumable;
                                                below-normal priority, memory-gated, heavy-job lock per seed)
    py -3 research/rl_loop/round3.py --eval     evaluate the four variants (+ the Phase 6 reproduction) and write the report
    py -3 research/rl_loop/round3.py --report   rebuild the report from research/out/rl_loop/round3_results.json

Reuses round1.py (lock, the spot-aware risk manager, metrics, grading) and round2.py (variant plumbing). Read-only use of
engine15.rl and research/harness (the retrain patches learn6's learner and validation score inside this process only;
nothing under engine15/ is modified); writes only under research/out/rl_loop/.
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import round1 as R1  # noqa: E402

ROOT, OUT, POOL, SEEDS = R1.ROOT, R1.OUT, R1.POOL, R1.SEEDS
log, acquire_lock, release_lock = R1.log, R1.acquire_lock, R1.release_lock
MODELS = os.path.join(OUT, "models_r3")
VNAME = "r_missed_longflat"
ACTS3 = [0.0, 0.5, 1.0]
RES = os.path.join(OUT, "round3_results.json")
START_MB, FLOOR_MB = 1600, 1500          # stricter than LOOP_RL rule 5 (1,500 / 600), as registered
N_ROUND1, N_ROUND2 = 5, 6
ROUND_VARIANTS = ["R3a_core_riskoff", "R3b_core_riskoff_125", "R3c_committee_riskoff", "R3d_retrain_longflat_riskoff"]
N_CUM = R1.N_PHASE6 + N_ROUND1 + N_ROUND2 + len(ROUND_VARIANTS)          # 23
COMPARE = ["V2_spot_lean", "R2b_blend_125", "R2f_retrain_spot_longlever"]  # earlier rounds, shown (not re-graded, not counted)
REF = R1.REF
LABELS = dict(R1.LABELS)
LABELS.update({"V2_spot_lean": "V2 spot_lean (round 1, comparison)",
               "R2b_blend_125": "R2-b blend_125 (round 2, comparison)",
               "R2f_retrain_spot_longlever": "R2-f retrain_spot_longlever (round 2, comparison)",
               "R3a_core_riskoff": "R3-a core_riskoff: long core, flat when agent not long and trend down",
               "R3b_core_riskoff_125": "R3-b core_riskoff_125: R3-a at 1.25",
               "R3c_committee_riskoff": "R3-c committee_riskoff: flat on 2 of 3 bearish votes (2 agents + trend)",
               "R3d_retrain_longflat_riskoff": "R3-d retrain_longflat_riskoff: long/flat-trained agent, R3-a rule"})
SHORT = {REF: "REF", "V2_spot_lean": "V2*", "R2b_blend_125": "R2-b*", "R2f_retrain_spot_longlever": "R2-f*",
         "R3a_core_riskoff": "R3-a", "R3b_core_riskoff_125": "R3-b", "R3c_committee_riskoff": "R3-c",
         "R3d_retrain_longflat_riskoff": "R3-d"}
# variant -> (models, min hold bars, re-size band, request rule)
EXEC = {"V2_spot_lean": ("p6", 16, 0.40, "s"), "R2b_blend_125": ("p6", 16, 0.40, "blend125"),
        "R2f_retrain_spot_longlever": ("r2", 16, 0.40, "longlever"),
        "R3a_core_riskoff": ("p6", 16, 0.40, "riskoff"), "R3b_core_riskoff_125": ("p6", 16, 0.40, "riskoff125"),
        "R3c_committee_riskoff": ("p6+r2", 16, 0.40, "committee"),
        "R3d_retrain_longflat_riskoff": ("r3", 16, 0.40, "riskoff")}


def spot_f(a):
    a = np.asarray(a, dtype=float)
    return np.maximum(a - 1.0, 0.0) + np.minimum(a, 0.0)


# ---------------------------------------------------------------- the retrain (R3-d's models)
def _patch_learn6_longflat():
    """Long/flat agent: spot-long accounting in reward and validation score (as R2-d) and the missed-opportunity
    reference clamped to its long part, max(ref, 0). This process only; engine15 files are not touched."""
    from engine15.rl import learn6, metrics, policy3
    from engine15.rl.models4 import cost_matrix, q_from_w
    from engine15.rl.qagent import funded_vector
    Base = learn6.Learner6
    if getattr(Base, "_r3_longflat", False):
        return learn6

    class Learner6LongFlat(Base):
        _r3_longflat = True

        def _targets(self, raw, rd, idx, masks):
            torch = self.torch
            c = self.cfg
            assert c.get("funding_mode") == "spot"
            assert float(self.actions.min()) >= 0.0, self.actions
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
                    ref = torch.clamp(col("ref"), min=0.0)                 # only a missed LONG move is charged
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
        """models4.policy_metrics with the spot-long net: a x rpx - f(a) x rate - c1 x |change| (as R2-d)."""
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

    learn6.Learner6 = Learner6LongFlat
    learn6.policy_metrics = spot_policy_metrics
    return learn6


def _fold_done(d, f):
    return os.path.exists(os.path.join(d, "rec_f%02d_pool.json" % f)) and all(
        os.path.exists(os.path.join(d, "w_f%02d_%s.npy" % (f, a))) for a in POOL)


def train():
    import gc
    from engine15.rl import phase4, phase5, phase6, resources
    from engine15.rl.phase3 import _jdump, _npsave
    learn6 = _patch_learn6_longflat()
    cfg = phase6.load_cfg()
    phase6.check_frozen(cfg)
    resources.low_priority()
    resources.torch_lean(cfg["qagent"].get("torch_threads", 2))
    pause = resources.MemoryPause(START_MB, FLOOR_MB, 20, log)
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
    log("round 3 retrain %s (actions %s) in %s: %d of %d fold fits already done; free %.0f MB" % (
        VNAME, ACTS3, MODELS, done_n, total, resources.free_mb() or -1))
    t0, fit_secs = time.time(), []
    for si, seed in enumerate(seeds):
        d = os.path.join(MODELS, VNAME, "s%d" % seed)
        os.makedirs(d, exist_ok=True)
        todo = [ft for ft in fts if not _fold_done(d, ft["i"])]
        if not todo:
            continue
        acquire_lock("rl_loop round 3 retrain %s seed %d" % (VNAME, seed))
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
                W, rec = learn6.q_fold6(assets, POOL, ci, geo, cfg["q"], qcfg, ACTS3, mh, seed * 1000 + f, sh,
                                        pause, where)
                for a in POOL:
                    _npsave(W[a], os.path.join(d, "w_f%02d_%s.npy" % (f, a)))
                rec.update({"fold": f, "variant": VNAME, "columns": cols, "geo": geo, "free_mb": resources.free_mb(),
                            "actions": ACTS3,
                            "accounting": "spot-long (reward incl. reference term max(ref,0), validation score); long/flat"})
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
    _jdump({"root": MODELS, "variant": VNAME, "actions": ACTS3, "minutes_this_call": round((time.time() - t0) / 60, 1),
            "memory_events": pause.events}, os.path.join(MODELS, "done.json"))
    log("round 3 retrain complete (%.0f min this call)" % ((time.time() - t0) / 60))


def main():
    if "--train" in sys.argv:
        train()
        return
    import round3_eval
    round3_eval.main()


if __name__ == "__main__":
    main()
