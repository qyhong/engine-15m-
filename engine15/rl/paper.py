# -*- coding: utf-8 -*-
"""paper -- the Phase 3 forward paper mode (design + dry run; NOT wired into the live engine or the page).

    py -3 -m engine15.rl paper [--asset BTCUSDT] [--offline]
        At a 15m bar close: load the newest model, build the observation from the latest CLOSED bars, decide the target
        for the next bar (minimum hold, then the Phase 3 risk manager), log it, and run the scheduled fine-tune when one
        is due (every cadence_days at the 00:00 UTC bar close), saving a new model version. This is how the agent would
        keep learning live. Paper only: it writes a decision log, never an order.
    py -3 -m engine15.rl paper --dry-run-from 2026-10-01 --dry-run-to 2026-10-15
        The same step, bar by bar, on stored history as if live (data cut at each bar), then a check that every decision
        equals the batch walk-forward simulation of the same span from the same starting model.

State lives in research/out/rl/paper/<asset>/ (dry runs in .../paper_dryrun/<asset>/): state.json (agent position,
holding clock, risk-manager state, last update), decisions.jsonl (one line per bar), models/model_<UTC>.pt.
Variant: the primary agent (base family, continual mode with the frozen cadence).
"""
import json
import os
import time

import numpy as np
import pandas as pd

from . import continual, features3, phase3, policy3, qagent, resources, risk3
from .config import for_asset, resolve
from .env import Market
from .qagent import Learner

WINDOW = 6000                     # bars of history for one observation (longest feature window 2,880 + 30 closed days)


def _dir(cfg, asset, dry):
    d = os.path.join(resolve(cfg["report"]["out_dir"]), "paper_dryrun" if dry else "paper", asset)
    os.makedirs(os.path.join(d, "models"), exist_ok=True)
    return d


def _market(cfg, bars, fund):
    f = features3.build(bars, fund, cfg["features"]).astype("float32")
    from . import costs
    return Market(bars, fund, f, costs.from_cfg(cfg))


def _fund_upto(fund, close_ms):
    return fund[np.asarray(fund["settle_ms"]) <= close_ms]


class Paper:
    """One paper book: model + decision state + risk-manager stepper. step(i) decides at the close of bar i using
    bars [.. i] only."""

    def __init__(self, cfg, asset, bars, fund, L, state_dir, log=print):
        self.cfg, self.asset, self.bars, self.fund, self.L, self.dir, self.log = cfg, asset, bars, fund, L, state_dir, log
        fam = cfg["families"]["base"]
        self.acts = np.asarray(fam["actions"], float)
        self.ip = int(np.argmin(np.abs(self.acts)))
        self.mh = int(cfg["policy"]["min_hold_bars"])
        self.since = self.mh
        self.qc = dict(cfg["qagent"])
        self.cad = int(cfg["continual"]["cadence_days"])
        if self.cad != 7:
            self.qc["finetune_steps"] = int(cfg["cadence_choice"]["steps_per_update"][str(self.cad)])
        from . import costs
        self.model = costs.from_cfg(cfg)
        self.rs = risk3.Stepper(cfg["risk3"], self.model, log_events=True)
        self.n_dec = 0
        self.log_path = os.path.join(state_dir, "decisions.jsonl")
        self.version = None
        self.neutral = False                # 'do no harm' flag: set by the bootstrap's validation, re-checked quarterly
        self.last_check = None

    def _window_market(self, lo, i):
        b = self.bars.iloc[lo:i + 1]
        close_ms = int(b.index[-1].value // 10**6) + 900000
        return _market(self.cfg, b, _fund_upto(self.fund, close_ms))

    def update_due(self, i):
        cm = int(self.bars.index[i].value // 10**6) + 900000
        if cm % 86400000:
            return False
        day = cm // 86400000
        return ((day + 3) % 7 == 0) if self.cad == 7 else (day % self.cad == 0)

    def fine_tune(self, i):
        """The scheduled update at bar i's close: replay window + warm-up, same code as the walk-forward."""
        replay = int(self.qc["replay_days"]) * 96
        lo = max(0, i - replay - WINDOW)
        m = self._window_market(lo, i)
        rd = qagent.reward_arrays(m, self.qc)
        U = i - lo
        rec = continual.fine_tune(self.L, m, rd, U, self.qc)
        if self.last_check is None or i - self.last_check >= 91 * 96:     # quarterly do-no-harm re-check, causal
            v = continual.eval_q(m, self.L.q(m.raw, rd, U - 92 * 96, U), U - 92 * 96, U, self.acts, self.cfg["policy"])
            self.neutral = bool(continual.is_fallback(v["sharpe"], self.qc))
            self.last_check = i
            rec["recheck_sharpe_3m"] = v["sharpe"]
            rec["neutral"] = self.neutral
        stamp = str(self.bars.index[i] + pd.Timedelta(minutes=15)).replace(":", "").replace(" ", "T")[:15]
        path = os.path.join(self.dir, "models", "model_%s.pt" % stamp)
        self.L.save(path, {"asset": self.asset, "updated_at_bar_close": str(self.bars.index[i] + pd.Timedelta(minutes=15))})
        self.version = os.path.basename(path)
        return rec

    def step(self, i):
        """Decide at the close of bar i (data after bar i is never touched)."""
        upd = None
        if self.update_due(i):
            upd = self.fine_tune(i)
        lo = max(0, i - WINDOW + 1)
        m = self._window_market(lo, i)
        rd = qagent.reward_arrays(m, self.qc)
        j = i - lo
        if self.neutral:
            Q = continual.q_of(continual.neutral_w(1, self.acts, 0.0), rd, j, j + 1, self.qc, self.acts)
        else:
            Q = self.L.q(m.raw, rd, j, j + 1)
        ip, st = policy3.decide(Q, self.acts, self.ip, self.mh, since0=self.since)
        new_ip = int(ip[0])
        if new_ip != self.ip:
            self.since = 0
        self.since += 1
        self.ip = new_ip
        req = float(self.acts[new_ip])
        rcol = lambda name: float(m.raw[j, m.col(name)]) if m.col(name) is not None else float(m.vol[j])
        rc = self.rs.cfg
        ex = self.rs.step(i, req, int(m.close_ms[j]), float(m.r_bar[j]), float(m.r_px[j - 1]) if j >= 1 else 0.0,
                          float(m.vol[j - 1]) if j >= 1 else 0.0, float(m.rate[j]), rcol(rc.vol_short), rcol(rc.vol_long))
        rec = {"bar_close_utc": str(self.bars.index[i] + pd.Timedelta(minutes=15)), "asset": self.asset,
               "agent_target": req, "executed_target": float(ex), "risk_size": float(self.rs.size),
               "q_values": [round(float(x), 5) for x in Q[0, int(np.argmin(np.abs(self.acts - req)))]],
               "decision": st, "model": self.version, "update": upd, "fill": "next bar open (paper)"}
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        self.n_dec += 1
        return req, ex


def bootstrap_model(cfg, bars, fund, i, seed=0, log=print):
    """A first model at bar i's close: a fresh 12-month fold-style train (9 train + 3 validation) on bars before it."""
    lo = max(0, i - 365 * 96 - WINDOW)
    b = bars.iloc[lo:i + 1]
    m = _market(cfg, b, _fund_upto(fund, int(b.index[-1].value // 10**6) + 900000))
    rd = qagent.reward_arrays(m, cfg["qagent"])
    hi = len(b)
    bnd = {"tr_lo": hi - 365 * 96, "val_lo": hi - 92 * 96, "tr_hi": hi}
    L, rec = continual.full_train(m, rd, bnd, cfg["qagent"], cfg["policy"], cfg["families"]["base"]["actions"], seed)
    return L, rec


def dry_run(cfg, asset, start, end, log=print, seed=0, write=True):
    """Paper steps on stored history as if live, then compare with the batch simulation from the same start model."""
    resources.low_priority()
    acfg = for_asset(cfg, asset)
    bars, fund, _ = phase3.load_bars(acfg, True, log)
    i0 = int(bars.index.searchsorted(pd.Timestamp(start, tz="UTC")))
    i1 = int(bars.index.searchsorted(pd.Timestamp(end, tz="UTC"))) if end else min(len(bars), i0 + 14 * 96)
    d = _dir(acfg, asset, True)
    for f in os.listdir(os.path.join(d, "models")):
        os.remove(os.path.join(d, "models", f))
    if os.path.exists(os.path.join(d, "decisions.jsonl")):
        os.remove(os.path.join(d, "decisions.jsonl"))
    t0 = time.time()
    L, rec = bootstrap_model(acfg, bars, fund, i0 - 1, seed, log)
    p0 = os.path.join(d, "models", "model_bootstrap.pt")
    L.save(p0, {"asset": asset, "bootstrap": True})
    pb = Paper(acfg, asset, bars, fund, L, d, log)
    pb.version = os.path.basename(p0)
    pb.neutral, pb.last_check = bool(rec["fallback"]), i0 - 1
    reqs, exs = [], []
    for i in range(i0, i1):
        r, e = pb.step(i)
        reqs.append(r)
        exs.append(e)
    secs = time.time() - t0
    # batch: the walk-forward code path on full-history arrays, from the same bootstrap model
    m = phase3.build_market(acfg, bars, fund)
    rd = qagent.reward_arrays(m, acfg["qagent"])
    Lb = Learner.load(p0, acfg["qagent"])
    qc = dict(acfg["qagent"])
    if int(acfg["continual"]["cadence_days"]) != 7:
        qc["finetune_steps"] = int(acfg["cadence_choice"]["steps_per_update"][str(acfg["continual"]["cadence_days"])])
    W, ups = continual.run_span(Lb, m, rd, i0, i1, qc, cadence_days=int(acfg["continual"]["cadence_days"]))
    acts = np.asarray(acfg["families"]["base"]["actions"], float)
    if rec["fallback"]:
        W = continual.neutral_w(i1 - i0, acts, 0.0)
    Q = continual.q_of(W, rd, i0, i1, qc, acts)
    ip, _ = policy3.decide(Q, acts, int(np.argmin(np.abs(acts))), int(acfg["policy"]["min_hold_bars"]))
    tb = np.zeros(m.n)
    tb[i0:i1] = acts[ip]
    ri = risk3.apply(m, tb, i0, i1, acfg["risk3"], log_events=False)
    same_req = int(np.sum(np.asarray(reqs) == acts[ip]))
    ex_diff = float(np.max(np.abs(np.asarray(exs) - ri["exec"][i0:i1])))
    out = {"asset": asset, "span": [str(bars.index[i0]), str(bars.index[i1 - 1])], "bars": i1 - i0, "updates": len(ups),
           "decisions_equal_to_batch": same_req, "executed_max_abs_diff_vs_batch": ex_diff,
           "changes": int(np.count_nonzero(np.diff(np.asarray(reqs)))), "seconds": round(secs, 1),
           "bootstrap_fallback": rec["fallback"], "state_dir": d}
    out["text"] = ("Dry run %s, %s to %s (%d bars as if live, data cut at each bar, %d scheduled update(s), %.0f s): %d of %d "
                   "decisions equal the batch walk-forward simulation from the same start model; executed targets after the "
                   "risk manager differ by at most %.1e. %d target change(s). Log: %s/decisions.jsonl. Nothing is wired into "
                   "the live engine or the page." % (asset, out["span"][0], out["span"][1], out["bars"], out["updates"], secs,
                                                    same_req, out["bars"], ex_diff, out["changes"], d))
    log(out["text"])
    if write:
        with open(os.path.join(resolve(acfg["report"]["out_dir"]), "phase3_paper_dryrun.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1, default=str)
    return out


def step(cfg, asset, offline=False, log=print):
    """One live paper step at the latest closed bar (design; the owner decides whether to schedule it)."""
    resources.low_priority()
    acfg = for_asset(cfg, asset)
    bars, fund, _ = phase3.load_bars(acfg, offline, log)
    d = _dir(acfg, asset, False)
    mdir = os.path.join(d, "models")
    models = sorted(f for f in os.listdir(mdir) if f.endswith(".pt"))
    i = len(bars) - 1
    stp = os.path.join(d, "state.json")
    if models:
        L = Learner.load(os.path.join(mdir, models[-1]), acfg["qagent"])
    else:
        L, brec = bootstrap_model(acfg, bars, fund, i, 0, log)
        L.save(os.path.join(mdir, "model_bootstrap.pt"), {"asset": asset, "bootstrap": True, "fallback": brec["fallback"]})
        models = ["model_bootstrap.pt"]
    pb = Paper(acfg, asset, bars, fund, L, d, log)
    pb.version = models[-1]
    if not os.path.exists(stp):
        pb.last_check = i
        pb.neutral = bool(L.meta.get("fallback", False)) if getattr(L, "meta", None) else bool(brec["fallback"])
    if os.path.exists(stp):
        with open(stp, encoding="utf-8") as f:
            s = json.load(f)
        if s.get("last_bar") == str(bars.index[i]):
            log("bar %s already decided" % bars.index[i])
            return s
        pb.ip, pb.since = int(s["ip"]), int(s["since"])
        pb.neutral, pb.last_check = bool(s.get("neutral", False)), s.get("last_check")
        rs = pb.rs
        rs.eq, rs.prev_pos, rs.cur, rs.last_req = s["risk"]["eq"], s["risk"]["prev_pos"], s["risk"]["cur"], s["risk"]["last_req"]
        rs.pending = tuple(s["risk"]["pending"]) if s["risk"]["pending"] else None
        rs.hist.extend(s["risk"]["hist"])
        from collections import deque
        rs.peak_q = deque(tuple(x) for x in s["risk"]["peak_q"])
    req, ex = pb.step(i)
    rs = pb.rs
    s = {"last_bar": str(bars.index[i]), "ip": pb.ip, "since": pb.since, "agent_target": req, "executed_target": ex,
         "neutral": pb.neutral, "last_check": pb.last_check,
         "model": pb.version, "risk": {"eq": rs.eq, "prev_pos": rs.prev_pos, "cur": rs.cur, "last_req": rs.last_req,
                                       "pending": list(rs.pending) if rs.pending else None, "hist": list(rs.hist),
                                       "peak_q": [list(x) for x in rs.peak_q]}}
    with open(stp, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=1, default=str)
    log("paper %s at %s close: agent %+.1f, executed %+.2f (model %s)" % (asset, bars.index[i], req, ex, pb.version))
    return s
