"""engine15.rl -- reinforcement-learning research module for Mind 15 (paper only).

Phase 1: data pipeline, point-in-time features, one shared cost model, a vectorised backtester,
benchmarks, metrics and a walk-forward splitter. Phase 2: a Gymnasium trading environment (env.py),
a risk manager (risk.py), a PPO agent (agent.py) trained per walk-forward fold (train.py, phase2.py).

    py -3 -m engine15.rl phase1              (data update -> features -> benchmarks -> report)
    py -3 -m engine15.rl phase1 --offline    (use the stored data only)
    py -3 -m engine15.rl phase2 [--offline] [--seeds N] [--timesteps N]

See docs/RL.md.
"""
