# -*- coding: utf-8 -*-
"""The whole Phase 1 runner, offline, on planted data in a temporary folder."""
import json
import os

from conftest import make_bars, make_funding
from engine15.rl import config, data, phase1, store


def test_phase1_offline_end_to_end(tmp_path):
    cfg = config.load()
    cfg["data"]["dir"] = str(tmp_path / "data")
    cfg["report"]["out_dir"] = str(tmp_path / "out")
    cfg["report"]["runs_dir"] = str(tmp_path / "out" / "runs")
    cfg["walkforward"].update({"train_months": 1, "test_months": 1, "step_months": 1, "start": "2022-01-01",
                               "min_test_days": 10})
    cfg["benchmarks"]["random"]["seeds"] = [0, 1, 2, 3, 4]
    bars = make_bars(n=96 * 130, seed=21, start="2022-01-01")
    store.write_frame(bars[data.BAR_COLS], data.bars_path(cfg))
    f = make_funding(bars.index, seed=22)
    store.write_frame(f[["rate"]], data.funding_path(cfg), index_name="funding_time")
    res = phase1.run(cfg, offline=True, log=lambda m: None)
    out = tmp_path / "out"
    assert (out / "phase1_report.md").exists() and (out / "phase1_report.json").exists()
    runs = os.listdir(out / "runs")
    assert len(runs) == 1
    rd = out / "runs" / runs[0]
    for name in ("config.yaml", "manifest.json", "phase1_report.json", "phase1_report.md"):
        assert (rd / name).exists()
    assert json.loads((rd / "manifest.json").read_text())["seed"] == cfg["seed"]
    assert set(res["results"]) == {"fee_0.10%", "fee_0.05%"}
    r = res["results"]["fee_0.10%"]
    assert len(r["buy_hold"]["windows"]) == len(res["windows"]) >= 3
    assert r["random"]["seeds"] == 5
    assert all(v == [] for v in res["features"]["lookahead_check_on_real_data"].values())
    hi, lo = res["results"]["fee_0.10%"]["momentum"]["stitched"], res["results"]["fee_0.05%"]["momentum"]["stitched"]
    assert hi["fee_per_year"] > lo["fee_per_year"]
