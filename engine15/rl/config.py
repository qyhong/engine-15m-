# -*- coding: utf-8 -*-
"""config -- YAML config and reproducible run folders.

Every run gets a git-free run id (UTC timestamp + a short hash of the resolved config) and
writes its full config and a manifest into its own folder, so any result can be re-made.
"""
import copy
import hashlib
import json
import os
import platform
import sys
import time

import yaml

from ..config import ROOT

DEFAULT = os.path.join(ROOT, "configs", "rl", "phase1.yaml")


def load(path=None):
    with open(path or DEFAULT, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve(rel):
    """A path in the config (relative to the project folder) -> absolute."""
    return rel if os.path.isabs(rel) else os.path.join(ROOT, rel)


def config_hash(cfg):
    return hashlib.sha1(json.dumps(cfg, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:8]


def new_run(cfg, kind="phase1", now=None):
    """-> (run_id, run_dir). Writes config.yaml and manifest.json into the run folder."""
    now = time.time() if now is None else now
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(now))
    run_id = "%s_%s_%s" % (kind, stamp, config_hash(cfg))
    run_dir = os.path.join(resolve(cfg["report"]["runs_dir"]), run_id)
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, "config.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(copy.deepcopy(cfg), f, sort_keys=False)
    manifest = {"run_id": run_id, "kind": kind, "started_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now)),
                "config_hash": config_hash(cfg), "seed": cfg.get("seed"), "python": sys.version.split()[0],
                "platform": platform.platform(), "argv": sys.argv}
    with open(os.path.join(run_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return run_id, run_dir


DEFAULT2 = os.path.join(ROOT, "configs", "rl", "phase2.yaml")


def load_phase2(path1=None, path2=None):
    """Phase 1 config (data, costs, walk-forward, benchmarks) + the Phase 2 file on top.
    Phase 2's `report` keys are merged into Phase 1's; every other Phase 2 section is added as is."""
    cfg = load(path1)
    with open(path2 or DEFAULT2, "r", encoding="utf-8") as f:
        p2 = yaml.safe_load(f)
    rep = dict(cfg.get("report", {}))
    rep.update(p2.pop("report", {}) or {})
    cfg["report"] = rep
    cfg.update(p2)
    return cfg


DEFAULT3 = os.path.join(ROOT, "configs", "rl", "phase3.yaml")


def load_phase3(path1=None, path3=None):
    """Phase 1 config (data, costs, walk-forward, benchmarks) + the Phase 3 file on top (same merge rule as
    Phase 2: `report` keys merged, every other Phase 3 section added as is)."""
    cfg = load(path1)
    with open(path3 or DEFAULT3, "r", encoding="utf-8") as f:
        p3 = yaml.safe_load(f)
    rep = dict(cfg.get("report", {}))
    rep.update(p3.pop("report", {}) or {})
    cfg["report"] = rep
    cfg.update(p3)
    return cfg


DEFAULT4 = os.path.join(ROOT, "configs", "rl", "phase4.yaml")


def load_phase4(path1=None, path4=None):
    """Phase 1 config (data, costs, walk-forward, benchmarks) + the Phase 4 file on top (same merge rule)."""
    cfg = load(path1)
    with open(path4 or DEFAULT4, "r", encoding="utf-8") as f:
        p4 = yaml.safe_load(f)
    rep = dict(cfg.get("report", {}))
    rep.update(p4.pop("report", {}) or {})
    cfg["report"] = rep
    cfg.update(p4)
    return cfg


def for_asset(cfg, asset):
    """A copy of a Phase 3 config pointed at one asset (data symbol, walk-forward start)."""
    c = copy.deepcopy(cfg)
    a = cfg["assets"][asset]
    c["data"]["symbol"] = asset
    c["walkforward"]["start"] = a.get("walkforward_start", c["walkforward"]["start"])
    return c
