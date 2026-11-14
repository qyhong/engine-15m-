# -*- coding: utf-8 -*-
"""Phase 2 end to end on planted data (tiny PPO budget), resume, and the numpy policy copy."""
import json
import os

import numpy as np

from conftest import make_bars, make_funding
from engine15.rl import config, data, phase2, store


def tiny_cfg(tmp_path):
    cfg = config.load_phase2()
    cfg["data"]["dir"] = str(tmp_path / "data")
    cfg["report"].update({"out_dir": str(tmp_path / "out"), "runs_dir": str(tmp_path / "out" / "runs"),
                          "models_dir": str(tmp_path / "out" / "models")})
    cfg["walkforward"].update({"train_months": 2, "test_months": 1, "step_months": 1, "start": "2022-01-01",
                               "min_test_days": 10})
    cfg["benchmarks"]["random"]["seeds"] = [0, 1, 2]
    cfg["env"]["episode_decisions"] = 100
    cfg["agent"].update({"n_envs": 2, "n_steps": 128, "batch_size": 64, "n_epochs": 2})
    cfg["train"].update({"validation_months": 1, "evals": 2, "patience": 1, "memory_start_mb": 0, "memory_floor_mb": 0})
    return cfg


def test_phase2_offline_end_to_end_and_resume(tmp_path):
    cfg = tiny_cfg(tmp_path)
    bars = make_bars(n=96 * 150, seed=81, start="2022-01-01", drift=0.0001)
    store.write_frame(bars[data.BAR_COLS], data.bars_path(cfg))
    f = make_funding(bars.index, seed=82)
    store.write_frame(f[["rate"]], data.funding_path(cfg), index_name="funding_time")
    res = phase2.run(cfg, offline=True, seeds=2, timesteps=512, log=lambda m: None)
    assert res["complete"]
    out = tmp_path / "out"
    for name in ("phase2_report.md", "phase2_summary.json", "phase2_risk_log.csv", "phase2_progress.json"):
        assert (out / name).exists(), name
    summ = json.loads((out / "phase2_summary.json").read_text())
    assert summ["paper_only"] and summ["headline_fee"] == "fee_0.10%"
    strat = summ["fees"]["fee_0.10%"]["strategies"]
    for k in ("agent_seed_mean", "agent_s0", "agent_s1", "buy_hold", "momentum", "random_mean", "buy_hold_with_risk_manager"):
        assert k in strat
        for m in ("return", "sharpe", "sortino", "max_drawdown", "calmar", "turnover_per_year", "avg_holding_hours",
                  "cost_drag_per_year"):
            assert m in strat[k]["overall"]
        assert len(strat[k]["folds"]) == len(res["windows"]) >= 3
    assert set(summ["fees"]) == {"fee_0.10%", "fee_0.05%"}
    ids = {fl["id"] for fl in summ["flags"]}
    assert {"train_test_sharpe_gap", "seed_dispersion", "beats_benchmarks_in_under_half_the_folds", "fee_sign_flip",
            "high_turnover"} <= ids
    assert res["env_backtest_max_abs_diff"] < 1e-12               # env P&L == backtest P&L on the real pipeline
    models = os.listdir(res["models_dir"])
    assert sum(m.endswith(".npz") for m in models) == 2 * len(res["windows"])
    assert all(os.path.getsize(os.path.join(res["models_dir"], m)) < 100_000 for m in models if m.endswith(".npz"))
    assert "Verdict" in (out / "phase2_report.md").read_text(encoding="utf-8")
    # resume: the same config again trains nothing and gives the same agent numbers
    seen = []
    res2 = phase2.run(cfg, offline=True, seeds=2, timesteps=512, log=seen.append)
    assert not any("steps, kept check" in m for m in seen)
    a1 = res["results"]["fee_0.10%"]["agent"]["stitched"]["sharpe"]["mean"]
    a2 = res2["results"]["fee_0.10%"]["agent"]["stitched"]["sharpe"]["mean"]
    assert a1 == a2


def test_numpy_policy_matches_sb3_deterministic_action(tmp_path):
    from stable_baselines3.common.vec_env import DummyVecEnv
    from engine15.rl import agent, features
    from engine15.rl.costs import CostModel
    from engine15.rl.env import Market, TradingEnv
    cfg = tiny_cfg(tmp_path)
    b = make_bars(n=3000, seed=91)
    feats = features.build(b, None, cfg["env"]["features"]).astype("float32")
    m = Market(b, None, feats, CostModel())
    nrm = m.fit_norm(800, 2500)
    venv = DummyVecEnv([lambda: TradingEnv(m, 800, 2500, nrm, cfg["env"], cfg["risk"], episode_decisions=100, seed=1)])
    model = agent.make_ppo(venv, cfg["agent"], 3)
    model.learn(256)
    pol = agent.NumpyPolicy.from_sb3(model, *nrm)
    rng = np.random.RandomState(0)
    obs = rng.normal(0, 2, (200, m.raw.shape[1] + 3)).astype(np.float32)
    sb3, _ = model.predict(obs, deterministic=True)
    mine = np.array([pol.act(o) for o in obs])
    assert np.array_equal(sb3, mine)
    p = tmp_path / "pol.npz"
    pol.save(p)
    back = agent.NumpyPolicy.load(p)
    assert np.array_equal(np.array([back.act(o) for o in obs]), mine)
    assert os.path.getsize(p) < 50_000
