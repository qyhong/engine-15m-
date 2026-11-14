# -*- coding: utf-8 -*-
"""py -3 -m engine15.rl <command> [--offline] [--config PATH]

phase1          data update -> features -> benchmarks -> walk-forward report (research/out/rl/)
phase2          PPO agent per walk-forward fold -> phase2_report.md / phase2_summary.json
                options: --seeds N, --timesteps N, --fresh
phase3          Phase 3: the continuously learning cost-aware 15m agent, every frozen variant, BTC (+ ETH) -> phase3_report.md
                / phase3_summary.json; resumes from finished folds. options: --seeds N, --assets BTCUSDT,ETHUSDT, --fresh
phase3-learn    learnability check on synthetic data (run before the freeze)
phase3-power    SUPPLEMENTARY learnability power check (more seeds, longer test; added after the frozen check failed)
phase3-cadence  update-cadence choice on synthetic data + BTC before 2020-10-01 (run before the freeze)
phase3-risk     the Phase 3 risk manager judged on buy-and-hold and momentum, no agent (run before the freeze)
phase3-report   rebuild phase3_report.md / phase3_summary.json from the latest run's saved results (formatting only)
phase3-diag2    DIAGNOSTIC: the Phase 3 filters applied to the Phase 2 agent's trades (uses seen test data; not a result)
phase4          Phase 4: more data per model (expanding, pooled, Mind 15 readings); the frozen walk-forward, once ->
                phase4_report.md / phase4_summary.json; resumes from saved fold models. options: --fresh
phase4-learn    Phase 4 learnability check at the new data sizes (synthetic; run before the freeze)
phase4-check    Phase 4 input caches + the no-look-ahead truncation test of every input on real data
phase4-report   rebuild phase4_report.md / phase4_summary.json from the latest run (formatting only)
phase5-update   Phase 5: the weekly refit of the forward paper agent (a separate below-normal process; lock; >= 1,500 MB
                free); writes research/out/rl/models5/live/model_<UTC>.json atomically. --fresh = even if not due
phase5-repro    Phase 5: rebuild Phase 4's fold-24 models with the export hook and check them against Phase 4's files
phase5-ablate   Phase 5 part 3: train the registered input ablations (resumable, heavy)
phase5          Phase 5 parts 2 and 3: evaluate the trade-less variants and the ablations -> phase5_report.md
phase5-report   rebuild phase5_report.md / phase5_summary.json from the saved evaluation (formatting only)
phase6-train    Phase 6: train the shaped-reward agents (flat scores weakly; resumable, heavy)
phase6          Phase 6: evaluate every registered variant -> phase6_report.md / phase6_summary.json
phase6-report   rebuild phase6_report.md from the saved evaluation (formatting only)
phase6-update   the weekly refit of the Phase 6 forward paper model (book p6_mtrend; a separate below-normal process;
                shares phase5-update's lock; >= 1,500 MB free); writes research/out/rl/models6/live/model_<UTC>.json.
                --fresh = even if not due
paper           forward paper mode: decide the next 15m bar with the newest model, log it, run the scheduled update
                options: --asset, --dry-run-from DATE --dry-run-to DATE (historical bars as if live; nothing is wired live)
data            data update only
--offline       use the stored data (no network)
Paper only: public market data, no keys, no orders. Every run lowers its own priority.
"""
import argparse
import sys

COMMANDS = ["phase1", "phase2", "phase3", "phase3-learn", "phase3-power", "phase3-cadence", "phase3-risk", "phase3-diag2", "phase3-report",
            "phase4", "phase4-learn", "phase4-check", "phase4-report", "phase5-update", "phase5-repro", "phase5-ablate",
            "phase5", "phase5-report", "phase6-train", "phase6", "phase6-report", "phase6-update", "paper", "data"]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="py -3 -m engine15.rl")
    ap.add_argument("command", choices=COMMANDS)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--config", default=None)
    ap.add_argument("--config2", default=None, help="Phase 2 config (default configs/rl/phase2.yaml)")
    ap.add_argument("--config3", default=None, help="Phase 3 config (default configs/rl/phase3.yaml)")
    ap.add_argument("--config4", default=None, help="Phase 4 config (default configs/rl/phase4.yaml)")
    ap.add_argument("--seeds", type=int, default=None)
    ap.add_argument("--timesteps", type=int, default=None)
    ap.add_argument("--assets", default=None)
    ap.add_argument("--asset", default="BTCUSDT")
    ap.add_argument("--dry-run-from", dest="dry_from", default=None)
    ap.add_argument("--dry-run-to", dest="dry_to", default=None)
    ap.add_argument("--fresh", action="store_true")
    a = ap.parse_args(argv)
    from . import config, resources
    resources.low_priority()
    cfg = config.load(a.config)
    log = lambda m: print(m, flush=True)
    if a.command == "data":
        import json
        from . import data
        _, _, rep = data.update_all(cfg, log=print, offline=a.offline)
        print(json.dumps(rep, indent=1, default=str))
        return 0
    if a.command == "phase2":
        from . import phase2
        cfg = config.load_phase2(a.config, a.config2)
        res = phase2.run(cfg, offline=a.offline, seeds=a.seeds, timesteps=a.timesteps, fresh=a.fresh, log=log)
        return 0 if res.get("complete") else 3
    if a.command == "phase6-update":
        from . import forward6
        return forward6.update_cli(forward6.load_cfg(), log=log, force=a.fresh)
    if a.command.startswith("phase6"):
        from . import phase6
        cfg6 = phase6.load_cfg()
        if a.command == "phase6-train":
            phase6.train(cfg6, log=log)
        elif a.command == "phase6":
            phase6.run(cfg6, log=log)
        else:
            log(phase6.rebuild(cfg6, log=log))
        return 0
    if a.command.startswith("phase5"):
        from . import forward5
        cfg5 = forward5.load_cfg()
        if a.command == "phase5-update":
            return forward5.update_cli(cfg5, log=log, force=a.fresh)
        if a.command == "phase5-repro":
            import json
            from .config import resolve
            path, rep = forward5.reproduce_phase4_fold(cfg5, log=log)
            with open(resolve("research/out/rl/phase5_repro.json"), "w", encoding="utf-8") as fh:
                json.dump(rep, fh, indent=1)
            log("reproduction exact: %s -> %s" % (rep["exact"], path))
            return 0 if rep["exact"] else 3
        from . import phase5
        if a.command == "phase5-ablate":
            phase5.ablate(cfg5, log=log)
        elif a.command == "phase5":
            phase5.run(cfg5, log=log)
        elif a.command == "phase5-report":
            log(phase5.rebuild(cfg5, log=log))
        return 0
    if a.command.startswith("phase4"):
        from . import phase4
        cfg4 = config.load_phase4(a.config, a.config4)
        if a.command == "phase4":
            res = phase4.run(cfg4, offline=a.offline, fresh=a.fresh, log=log)
            return 0 if res.get("complete") else 3
        if a.command == "phase4-learn":
            phase4.learn(cfg4, log=log)
        elif a.command == "phase4-check":
            phase4.check(cfg4, offline=True if a.offline else False, log=log)
        elif a.command == "phase4-report":
            log(phase4.rebuild(cfg4, log=log))
        return 0
    if a.command.startswith("phase3") or a.command == "paper":
        cfg3 = config.load_phase3(a.config, a.config3)
        if a.command == "phase3":
            from . import phase3
            assets = a.assets.split(",") if a.assets else None
            res = phase3.run(cfg3, offline=a.offline, seeds=a.seeds, assets=assets, fresh=a.fresh, log=log)
            return 0 if res.get("complete") else 3
        if a.command == "paper":
            from . import paper
            if a.dry_from:
                paper.dry_run(cfg3, a.asset, a.dry_from, a.dry_to, log=log)
            else:
                paper.step(cfg3, a.asset, offline=a.offline, log=log)
            return 0
        from . import phase3pre
        if a.command == "phase3-learn":
            phase3pre.learn(cfg3, log=log)
        elif a.command == "phase3-power":
            phase3pre.learn_power(cfg3, log=log)
        elif a.command == "phase3-cadence":
            phase3pre.cadence(cfg3, log=log, offline=True)
        elif a.command == "phase3-risk":
            phase3pre.riskcheck(cfg3, log=log, offline=True)
        elif a.command == "phase3-report":
            import glob
            import os
            from . import report3
            from .config import resolve
            runs = sorted(glob.glob(os.path.join(resolve(cfg3["report"]["runs_dir"]), "phase3_*")))
            runs = [r for r in runs if os.path.exists(os.path.join(r, "phase3_full.json"))]
            log(report3.rebuild(runs[-1], resolve(cfg3["report"]["out_dir"])))
        elif a.command == "phase3-diag2":
            phase3pre.diag2(cfg3, log=log)
        return 0
    from . import phase1
    phase1.run(cfg, offline=a.offline, log=log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
