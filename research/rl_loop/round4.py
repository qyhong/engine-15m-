# -*- coding: utf-8 -*-
"""RL loop round 4 (research/rl_loop/LOOP_RL.md "Round 4", registered 17 Nov 2026 03:21 UTC). Paper only.

    python research/rl_loop/round4.py --check    stage 1, the gate: rebuild the input cache if it is missing, recompute the
                                                 Phase 6 primary (rule 3) and round 3's R3-b / R3-c / R3-d, compare with the
                                                 saved runs. NO round-4 variant is computed here.
    python research/rl_loop/round4.py --eval     stage 2: only if the gate passed; the two registered variants (+ the same
                                                 reference and comparison rows) and the report
    python research/rl_loop/round4.py --report   rebuild the report from research/out/rl_loop/round4_results.json

Two execution-only variants (no retrain): R4-a committee_riskoff_125, R4-b committee4_riskoff. Reuses round1.py (lock, the
spot-aware risk manager, metrics, grading), round2.py / round3.py (model locations, variant plumbing) unchanged. Read-only
use of engine15.rl and research/harness; writes only under research/out/rl_loop/ (work folder r4_work/: the rebuilt input
cache and, on the research server, the copied trained fold models and Phase 6's saved run file).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import round1 as R1  # noqa: E402
import round2 as R2  # noqa: E402
import round3 as R3  # noqa: E402

ROOT, OUT, POOL, SEEDS = R1.ROOT, R1.OUT, R1.POOL, R1.SEEDS
log, acquire_lock, release_lock = R1.log, R1.acquire_lock, R1.release_lock
WORK = os.path.join(OUT, "r4_work")
INPUTS = os.path.join(WORK, "inputs")
CACHE = os.path.join(WORK, "cache")
RES = os.path.join(OUT, "round4_results.json")
CHECK = os.path.join(OUT, "round4_check.json")
R3_RES = os.path.join(OUT, "round3_results.json")
START_MB, FLOOR_MB = 1600, 1500
N_ROUND1, N_ROUND2, N_ROUND3 = 5, 6, 4
ROUND_VARIANTS = ["R4a_committee_riskoff_125", "R4b_committee4_riskoff"]
N_CUM = R1.N_PHASE6 + N_ROUND1 + N_ROUND2 + N_ROUND3 + len(ROUND_VARIANTS)          # 25
COMPARE = ["R3b_core_riskoff_125", "R3c_committee_riskoff", "R3d_retrain_longflat_riskoff"]   # round 3: the gate + comparison
REF = R1.REF
HALF_SPLIT = "2023-06-07"                 # reported only (not a pass rule): Sharpe gap in each half of the span
LABELS = dict(R1.LABELS)
LABELS.update({"R3b_core_riskoff_125": "R3-b core_riskoff_125 (round 3, comparison)",
               "R3c_committee_riskoff": "R3-c committee_riskoff (round 3, comparison)",
               "R3d_retrain_longflat_riskoff": "R3-d retrain_longflat_riskoff (round 3, comparison)",
               "R4a_committee_riskoff_125": "R4-a committee_riskoff_125: R3-c's committee (flat on 2 of 3 bearish) at 1.25",
               "R4b_committee4_riskoff": "R4-b committee4_riskoff: flat on 3 of 4 bearish votes (3 agents + trend), 1x"})
SHORT = {REF: "REF", "R3b_core_riskoff_125": "R3-b*", "R3c_committee_riskoff": "R3-c*",
         "R3d_retrain_longflat_riskoff": "R3-d*", "R4a_committee_riskoff_125": "R4-a", "R4b_committee4_riskoff": "R4-b"}
# variant -> (models, min hold bars, re-size band, request rule)
EXEC = {"R3b_core_riskoff_125": ("p6", 16, 0.40, "riskoff125"),
        "R3c_committee_riskoff": ("p6+r2", 16, 0.40, "committee"),
        "R3d_retrain_longflat_riskoff": ("r3", 16, 0.40, "riskoff"),
        "R4a_committee_riskoff_125": ("p6+r2", 16, 0.40, "committee125"),
        "R4b_committee4_riskoff": ("p6+r2+r3", 16, 0.40, "committee4")}


def first_existing(*paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return paths[0]


def p6_full_path():
    """Phase 6's saved run file: the copy in the round-4 work folder (research server) or the original (laptop)."""
    return first_existing(os.path.join(INPUTS, "phase6_full.json"), R1.P6_FULL)


def model_roots(p6_root_original):
    """{models key: (root, variant name)}: the copies in the work folder when present, else the original locations."""
    return {"p6": (first_existing(os.path.join(INPUTS, "models6", "b6a25c5d"), p6_root_original), "r_missed"),
            "r2": (first_existing(os.path.join(INPUTS, "models_r2"), R2.MODELS), R2.VNAME),
            "r3": (first_existing(os.path.join(INPUTS, "models_r3"), R3.MODELS), R3.VNAME)}


def cache_dir(original):
    """The Phase 4 input cache: the original folder if it still holds both assets, else the round-4 work folder (rebuilt
    by engine15.rl.pool4.prepare, unchanged code)."""
    if all(os.path.exists(os.path.join(original, a, "meta.json")) for a in POOL):
        return original
    return CACHE


def main():
    import round4_eval
    round4_eval.main()


if __name__ == "__main__":
    main()
