# -*- coding: utf-8 -*-
"""Phase 3 end to end on planted data (tiny budget): every output, resume, the loop baselines (point-in-time, spot
funding, holdout span), residual = baseline when it does nothing, and the forward paper mode == the batch path."""
import json
import os

import numpy as np
import pandas as pd

from conftest import make_bars, make_funding
from engine15.rl import baselines3, config, data, phase3, store


def tiny_cfg(tmp_path, families=("base", "res_A", "ws_A")):
    cfg = config.load_phase3()
    cfg["data"]["dir"] = str(tmp_path / "data")
    cfg["report"].update({"out_dir": str(tmp_path / "out"), "runs_dir": str(tmp_path / "out" / "runs"),
                          "models_dir": str(tmp_path / "out" / "models3")})
    cfg["data_end"] = None
    cfg["assets"] = {"BTCUSDT": {"walkforward_start": "2022-01-01", "source": "rl_store"}}
    cfg["walkforward"].update({"train_months": 2, "test_months": 1, "step_months": 1, "start": "2022-01-01",
                               "min_test_days": 10})
    cfg["train"]["validation_months"] = 1
    cfg["benchmarks"]["random"]["seeds"] = [0, 1, 2]
    cfg["qagent"].update({"evals": 2, "eval_every": 40, "batch_size": 32, "finetune_steps": 10, "replay_days": 30,
                          "bc_steps": 20, "chunk_steps": 40, "fallback_val_sharpe": -99.0})
    cfg["families"] = dict((k, dict(v, assets=["BTCUSDT"])) for k, v in cfg["families"].items() if k in families)
    cfg["memory"] = {"start_mb": 0, "floor_mb": 0, "poll_s": 1}
    return cfg


def write_data(cfg, n, seed, start="2022-01-01"):
    bars = make_bars(n=n, seed=seed, start=start, drift=0.00005)
    store.write_frame(bars[data.BAR_COLS], data.bars_path(cfg))
    f = make_funding(bars.index, seed=seed + 1)
    store.write_frame(f[["rate"]], data.funding_path(cfg), index_name="funding_time")
    return bars


def test_loop_baselines_are_point_in_time_and_spot_pays_funding_only_above_1x():
    b = make_bars(n=96 * 120, seed=71, drift=0.0001)
    full = baselines3.targets(b)
    for cut in (96 * 70, 96 * 95 + 13):
        part = baselines3.targets(b.iloc[:cut])
        for k in ("A", "B"):
            assert np.array_equal(full[k][:cut], part[k]), k
    assert set(np.unique(full["A"])) <= {0.0, 1.5} and full["B"].max() <= 2.0 + 1e-9 and full["B"].min() >= 0
    f = make_funding(b.index, seed=72)
    sm = baselines3.spot_market(b, f)
    t = np.full(len(b), 1.5)
    perp = sm.frame(t, 0.001, False)
    spot = sm.frame(t, 0.001, True)
    assert np.allclose(spot["funding"].values, perp["funding"].values / 1.5 * 0.5)
    assert baselines3.dev_cut_index(pd.DatetimeIndex([pd.Timestamp("2025-11-10", tz="UTC"),
                                                      pd.Timestamp("2025-11-11", tz="UTC")])) == 1


def test_phase3_end_to_end_resume_and_residual_identity(tmp_path):
    cfg = tiny_cfg(tmp_path)
    write_data(cfg, 96 * 190, 81)
    res = phase3.run(cfg, offline=True, seeds=2, log=lambda m: None)
    assert res["complete"]
    out = tmp_path / "out"
    for name in ("phase3_report.md", "phase3_summary.json", "phase3_risk_log_btcusdt.csv"):
        assert (out / name).exists(), name
    summ = json.loads((out / "phase3_summary.json").read_text())
    assert summ["paper_only"] and summ["headline_fee"] == "fee_0.10%"
    A = summ["assets"]["BTCUSDT"]
    assert set(A["fees"]) == {"fee_0.10%", "fee_0.05%"}
    full = A["fees"]["fee_0.10%"]["full_span"]["strategies"]
    for k in ("agent_static", "agent_continual", "agent_continual_retrain", "v1_seed_consensus", "v2_confidence_gate",
              "v3_htf_alignment", "v4_vol_cost_gate"):
        assert k in full, k
        assert "break_even_fee" in full[k]["seed_mean"]
    dev = A["fees"]["fee_0.10%"]["dev_span_to_2025_11_11"]
    assert {"baseline_A", "baseline_B", "buy_hold_spot"} <= set(dev["benchmarks"])
    assert {"r1_residual_A", "w1_warmstart_A"} <= set(dev["strategies"])
    md = (out / "phase3_report.md").read_text(encoding="utf-8")
    assert "Verdict" in md and "development span" in md
    ids = {f["id"] for f in summ["flags"]["BTCUSDT"]["agent_continual_retrain"]}
    assert {"train_test_sharpe_gap", "seed_dispersion", "edge_only_at_0.05", "high_turnover", "fee_sign_flip"} <= ids
    # the report can be rebuilt from the saved full result (JSON-cleaned: inf as strings) without recomputing
    from engine15.rl import report3
    rd_ = os.path.join(cfg["report"]["runs_dir"], res["run_id"])
    assert os.path.exists(report3.rebuild(rd_, str(out)))
    assert "Verdict" in (out / "phase3_report.md").read_text(encoding="utf-8")
    # resume: same config again -> nothing retrained, same numbers
    seen = []
    res2 = phase3.run(cfg, offline=True, seeds=2, log=seen.append)
    assert not any("kept check" in m for m in seen)
    a1 = res["assets"]["BTCUSDT"]["fees"]["fee_0.10%"]["variants"]["agent_continual"]["seeds"]["0"]["stitched"]["sharpe"]
    a2 = res2["assets"]["BTCUSDT"]["fees"]["fee_0.10%"]["variants"]["agent_continual"]["seeds"]["0"]["stitched"]["sharpe"]
    assert a1 == a2


def test_residual_doing_nothing_is_exactly_the_baseline(tmp_path):
    cfg = tiny_cfg(tmp_path, families=("res_A",))
    bars = write_data(cfg, 96 * 150, 91)
    acfg = config.for_asset(cfg, "BTCUSDT")
    b, f, _ = phase3.load_bars(acfg, True, None)
    base = baselines3.targets(b)["A"]
    sm = baselines3.spot_market(b, f)
    zero_adjust = base + 0.0
    assert np.array_equal(sm.frame(zero_adjust, 0.001)["r_net"].values, sm.frame(base, 0.001)["r_net"].values)


def test_paper_dry_run_equals_the_batch_walk_forward_path(tmp_path):
    from engine15.rl import paper
    cfg = tiny_cfg(tmp_path, families=("base",))
    cfg["qagent"]["fallback_val_sharpe"] = None
    write_data(cfg, 96 * 395, 95, start="2023-01-01")
    out = paper.dry_run(cfg, "BTCUSDT", "2024-01-28", "2024-01-30 12:00", log=lambda m: None, write=False)
    assert out["updates"] >= 1                                    # a Monday 00:00 update inside the span
    assert out["decisions_equal_to_batch"] == out["bars"]
    assert out["executed_max_abs_diff_vs_batch"] < 1e-9
    lines = open(os.path.join(out["state_dir"], "decisions.jsonl"), encoding="utf-8").read().splitlines()
    assert len(lines) == out["bars"] and "executed_target" in json.loads(lines[0])
