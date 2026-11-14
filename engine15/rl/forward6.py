# -*- coding: utf-8 -*-
"""forward6 -- RL Phase 6's forward paper books (engine15/playbook6.py). PAPER ONLY. NOT PASSED.

A thin layer over forward5.py (same data, inputs, policy, risk manager, book and cost model); only three things differ:

1. THE PHASE 6 MODEL (book p6_mtrend). Training: learn6.q_fold6 with the missed-opportunity reward (r_missed; beta in
   {0.25, 0.5, 1.0} chosen on the validation slice by the frozen selection rule of configs/rl/phase6.yaml: per beta the
   half-life by the validation Bellman loss, then the beta with the best validation net Sharpe, mean of BTC and ETH, ties
   -> the smaller), on forward5.train_model's data and geometry (the engine's 15m files up to the update, expanding from
   2019, validation = the last 6 months, refit on every row up to the data end; seeds 0, 1, 2, learner seed s x 1000 +
   500). The model file goes to research/out/rl/models6/live/model_<UTC>.json. Book p6_p4trend reuses Phase 5's weekly
   Phase 4 primary models (research/out/rl/models5/live); no second copy is trained.

2. THE 'DO NO HARM' MODE. Exactly Phase 6's rule in history (phase5.oos_w with fallback="trend"): a model whose own
   validation net Sharpe (that seed, that coin, on its validation slice) is under 0.5 (Phase 4's fallback_val_sharpe) does
   not use its values; it holds the trend reference position: W = -10 x |a - ref|, ref = the frozen daily 30-day momentum
   target at the bar (features3's mom_signal, +1 / -1), which then goes through the same Phase 3 policy and risk manager.
   The flag is fixed when the model is trained (stored per seed and coin in the model file) and each record says each
   seed's mode ("model" / "trend").

3. THE WEEKLY REFIT of the Phase 6 model: `py -3 -m engine15.rl phase6-update`, a separate below-normal-priority process,
   >= 1,500 MB free, sharing playbook5's refit lock (research/out/rl/forward5/update.lock), so that two refits never run at
   once; while Phase 5's refit is due it goes first. Nothing is trained inside the live step.
"""
import os

from . import forward5 as f5
from .config import resolve

FORWARD_DIR = "research/out/rl/forward6"
MODELS_DIR = "research/out/rl/models6/live"
CACHE_ROOT = "research/out/rl/phase6_cache"
FALLBACK = "trend"
MODEL_KIND = "phase6 primary (r_missed, beta on validation, q_pool2_full family) refit"
_CFG = {}


def load_cfg():
    """forward5's config (Phase 1 + 4 + 5) with configs/rl/phase6.yaml under cfg['phase6'] (cached)."""
    if "cfg" not in _CFG:
        from . import phase6
        cfg = phase6.load_cfg()
        phase6.check_frozen(cfg)
        _CFG["cfg"] = cfg
    return _CFG["cfg"]


def forward_dir(cfg=None):
    return resolve(FORWARD_DIR)


def live_models_dir(cfg=None):
    return resolve(MODELS_DIR)


def p4_models_dir(cfg):
    """Phase 5's weekly Phase 4 primary models (book p6_p4trend; never trained here)."""
    return f5.live_models_dir(cfg)


# ---------------------------------------------------------------- training (the update subprocess; heavy)
def _fit6(cfg):
    from .learn6 import q_fold6
    sh = dict(cfg["phase6"]["variants_train"][cfg["phase6"]["variants"][cfg["phase6"]["primary"]]["train"]])

    def fit(assets, names, ci, geo, c, seed, pause, where, export):
        return q_fold6(assets, names, ci, geo, c["q"], dict(c["qagent"]), c["actions"], int(c["policy"]["min_hold_bars"]),
                       seed, sh, pause, where, export=export)
    return fit


def train_model(cfg, until_ms=None, log=print, pause=None, out_dir=None, keep_cache=False, seeds=None):
    """Refit the Phase 6 primary's model (r_missed) on everything up to until_ms; write it atomically. -> path."""
    return f5.train_model(cfg, until_ms=until_ms, log=log, pause=pause, out_dir=out_dir or live_models_dir(cfg),
                          keep_cache=keep_cache, seeds=seeds, fit=_fit6(cfg), tag="phase6", id_prefix="m6_",
                          kind=MODEL_KIND, cache_root=resolve(CACHE_ROOT))


# ---------------------------------------------------------------- the weekly refit
def update_due(cfg, now_ms=None):
    import time
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    ms = f5.list_models(live_models_dir(cfg))
    return (not ms) or ms[-1][0] < f5.last_monday_ms(now_ms)


def _phase5_first(cfg, now_ms=None):
    return "waiting for the phase5 refit" if f5.update_due(cfg, now_ms) else None


def maybe_launch_update(cfg, now_ms=None, log=print, free_mb=None, launcher=None):
    """Called by playbook6's step: start `py -3 -m engine15.rl phase6-update` if due, no refit (Phase 5's or this one)
    holds the shared lock, Phase 5's is not due, the last attempt is 30+ minutes old and >= 1,500 MB are free."""
    os.makedirs(forward_dir(cfg), exist_ok=True)
    return f5.maybe_launch_update(cfg, now_ms=now_ms, log=log, free_mb=free_mb, launcher=launcher, due=update_due,
                                  command="phase6-update", status_dir=forward_dir(cfg), tag="phase6", hold=_phase5_first)


def update_cli(cfg, log=print, force=False):
    return f5.update_cli(cfg, log=log, force=force, train=train_model, due=update_due, status_dir=forward_dir(cfg),
                         tag="phase6")


def model_modes(model, assets=f5.ASSETS):
    """{asset: [mode per seed]} of a model file: "trend" where its own validation net Sharpe is under 0.5, else "model";
    with the validation Sharpe and (Phase 6 models) the chosen beta."""
    out = {}
    for a in assets:
        row = []
        for s in sorted(model["seeds"], key=int):
            m = model["seeds"][s]
            row.append({"seed": int(s), "mode": FALLBACK if m["fallback"].get(a, False) else "model",
                        "val_net_sharpe": (m.get("val") or {}).get(a, {}).get("sharpe"),
                        "beta": (m.get("chosen") or {}).get("shaping_value")})
        out[a] = row
    return out
