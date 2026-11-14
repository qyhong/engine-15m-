# -*- coding: utf-8 -*-
"""Phase 4: inputs are point in time and unavailable readings are never a signal; no training row reaches past its fold
(SP and Q, pooled); the reward-array P&L is the backtester's; the SP learner finds a planted edge with more data; end to end
on planted data with resume. Planted data only; the real evidence store is never read here."""
import json
import os

import numpy as np
import pandas as pd

from conftest import make_bars, make_funding
from engine15.rl import config, costs, data, features4, models4, phase4, policy3, pool4, qagent, store
from engine15.rl.env import Market

FCFG = {"return_windows": [1, 4, 16, 96, 672, 2880], "vol_windows": [16, 96, 672],
        "momentum_windows": [16, 96, 672, 2880], "volume_z_window": 672, "daily_closed": True,
        "phase3": {"htf": True, "momentum_signal": True, "time": True}}


def fake_snapshot(path, index, seed=3, nan_head=500):
    """A readings snapshot like features4.snapshot writes, with a missing head and a hole in the basis."""
    rng = np.random.default_rng(seed)
    n = len(index)
    vals = {}
    for c in list(features4.READINGS) + features4.AVAIL_COLS:
        v = rng.standard_normal(n).astype(np.float32)
        vals[c] = v
    vals["fund_raw"][:nan_head] = np.nan
    vals["pb_premium_pct"][1000:1200] = np.nan
    vals["pb_z"][1000:1200] = 0.0                      # a source module's "no read" filler
    t = np.asarray(index.as_unit("ms").asi8, dtype=np.int64)
    np.savez(path, times_ms=t, meta=json.dumps({"asset": "TEST"}), **vals)


def test_unavailable_readings_are_nan_with_a_flag_never_a_zero_signal(tmp_path):
    b = make_bars(n=3000, seed=11)
    p = str(tmp_path / "snap.npz")
    fake_snapshot(p, b.index[100:])                   # the store starts 100 bars later than the bars
    rf = features4.readings_frame(p, b.index)
    assert rf.loc[b.index[:100], list(features4.READINGS)].isna().all().all()
    assert (rf["avail_trend"].values[:100] == 0).all() and (rf["avail_trend"].values[100:] == 1).all()
    assert rf["fund_z"].iloc[100:600].isna().all() and (rf["avail_funding"].iloc[100:600] == 0).all()
    assert rf["pb_z"].iloc[1100:1300].isna().all() and (rf["avail_basis"].iloc[1100:1300] == 0).all()
    assert rf["pb_z"].iloc[1300:].notna().all()
    # downstream: z-scored per asset on the training rows, an unavailable value becomes exactly 0
    X = rf[list(features4.READINGS)].values.astype(np.float32)
    mu, sd = pool4.norm_stats(X, 0, len(X), np.arange(X.shape[1]))
    z = pool4.normalised(X, 0, len(X), np.arange(X.shape[1]), mu, sd)
    assert (z[:100] == 0).all()


def test_assembled_inputs_are_point_in_time(tmp_path):
    b = make_bars(n=96 * 50, seed=12)
    f = make_funding(b.index, seed=13)
    p = str(tmp_path / "snap.npz")
    fake_snapshot(p, b.index)
    rep = features4.features_lookahead(b, f, FCFG, p, [3100, 4000, 96 * 50 - 7])
    assert all(v == [] for v in rep.values()), rep


def test_engine_readings_survive_a_truncation_on_planted_bars():
    """The same check the real-data test runs: evidence.build_one on bars cut at t == full rows up to t."""
    from engine15 import evidence
    b = make_bars(n=96 * 80, seed=14)
    fs = pd.Series(np.random.default_rng(1).normal(1e-4, 1e-4, 240),
                   index=pd.date_range(b.index[0], periods=240, freq="8h", tz="UTC"))
    full = evidence.build_one(b, fs, None)
    for c in (96 * 40, 96 * 66 + 9):
        close = b.index[c] + pd.Timedelta(minutes=15)
        part = evidence.build_one(b.iloc[:c + 1], fs[fs.index <= close], None)
        for r in features4.BUILD_ONE:
            assert features4._cmp(full[r].values[:c + 1], part[r].values) == 0, (c, r)


def _mem_asset(name, n, seed, kappa=0.0, start="2021-01-01"):
    from engine15.rl import learn4, synth
    bars, fund, pl, _ = synth.make(n, seed, kappa, start=start)
    f = features4.build(bars, fund, FCFG, None)
    f["planted"] = pl
    m = Market(bars, fund, f.astype("float32"), costs.CostModel())
    rd = qagent.reward_arrays(m, config.load_phase4()["qagent"])
    return learn4.MemAsset(name, np.array(m.raw), dict((k, np.array(v)) for k, v in rd.items()),
                           np.asarray(bars.index.as_unit("ms").asi8, dtype=np.int64), list(m.columns)), m, pl


def test_reward_array_pnl_equals_the_backtesters_formula():
    A, m, _ = _mem_asset("S", 96 * 40, 21)
    t = np.sign(np.sin(np.arange(1000) / 37.0)) * 0.5
    lo, hi = 500, 1500
    r1, _ = models4.rd_net(A.rd, t, lo, hi)
    r2, _, _ = policy3.fast_net(m, t, lo, hi)
    assert np.allclose(r1[:-1], r2, atol=1e-12)        # fast_net realises bars lo+1 .. hi-1


def _cfg4():
    c = config.load_phase4()
    c["sp"] = dict(c["sp"], alphas=[0.1, 1.0], half_life_days=[None, 30])
    c["q"] = dict(c["q"], evals=2, eval_every=60, patience=1, half_life_days=[None, 30])
    c["qagent"] = dict(c["qagent"], batch_size=64, chunk_steps=60)
    return c


def _geo(A, n_test=96 * 10, lo=3000, val_bars=96 * 15):
    te_hi = A.n
    te_lo = te_hi - n_test
    return {"lo": lo, "val": te_lo - val_bars, "te_lo": te_lo, "te_hi": te_hi}


def test_no_training_row_reaches_past_the_fold_sp_and_q():
    c = _cfg4()
    A1, _, _ = _mem_asset("A1", 96 * 70, 31, 0.02)
    A2, _, _ = _mem_asset("A2", 96 * 70, 32, 0.02)
    cols = A1.cols(A1.columns)
    geo = {"A1": _geo(A1), "A2": _geo(A2)}
    for fam in ("sp", "q"):
        fn = models4.sp_fold if fam == "sp" else models4.q_fold
        sub = c["sp"] if fam == "sp" else c["q"]
        W1, r1 = fn([A1, A2], ["A1"], cols, geo, sub, c["qagent"], c["actions"], 4, 7)
        # scramble everything at or after the first test bar, in both assets: the fitted model must not move
        for A in (A1, A2):
            lo = geo[A.name]["te_lo"]
            A.X[lo:] = np.random.default_rng(5).standard_normal(A.X[lo:].shape).astype(np.float32)
            for k in ("g", "rpx", "rate", "k", "c1", "v"):
                A.rd[k][lo:] = A.rd[k][lo:][::-1] * 3.0
        W2, r2 = fn([A1, A2], ["A1"], cols, geo, sub, c["qagent"], c["actions"], 4, 7)
        assert np.allclose(np.asarray(r1["coef"]), np.asarray(r2["coef"])), fam
        assert r1["assets"]["A1"]["val"] == r2["assets"]["A1"]["val"], fam
        A1, _, _ = _mem_asset("A1", 96 * 70, 31, 0.02)
        A2, _, _ = _mem_asset("A2", 96 * 70, 32, 0.02)


def test_q_pool_never_crosses_an_asset_boundary():
    A1, _, _ = _mem_asset("A1", 96 * 40, 41)
    A2, _, _ = _mem_asset("A2", 96 * 40, 42)
    geo = {"A1": _geo(A1, 96 * 5, 500, 96 * 5), "A2": _geo(A2, 96 * 5, 500, 96 * 5)}
    cols = A1.cols(A1.columns[:10])
    stats = dict((A.name, pool4.norm_stats(A.X, geo[A.name]["lo"], geo[A.name]["val"], cols)) for A in (A1, A2))
    spans = dict((A.name, (geo[A.name]["lo"], geo[A.name]["te_lo"])) for A in (A1, A2))
    raw, rd, off = models4._concat([A1, A2], cols, spans, stats)
    pool, _ = models4._q_pool([A1, A2], geo, off, "val", 16, None, 0)
    seg2 = off["A2"] + geo["A2"]["lo"]
    a1 = pool[pool < seg2]
    assert a1.max() + 16 + 1 < seg2 and a1.max() + 16 < geo["A1"]["val"] + off["A1"]


def test_sp_finds_a_strong_planted_edge():
    c = _cfg4()
    c["sp"] = dict(c["sp"], half_life_days=[None, 365])
    A1, _, pl = _mem_asset("A1", 96 * 330, 51, 0.06)
    A2, _, _ = _mem_asset("A2", 96 * 330, 52, 0.06)
    geo = {"A1": {"lo": 3500, "val": 96 * 210, "te_lo": 96 * 270, "te_hi": 96 * 330}}
    geo["A2"] = dict(geo["A1"])
    W, rec = models4.sp_fold([A1, A2], ["A1"], A1.cols(A1.columns), geo, c["sp"], c["qagent"], c["actions"], 4, 3)
    g = geo["A1"]
    te = models4.policy_metrics(W["A1"], A1.rd, g["te_lo"], g["te_hi"], c["actions"], c["qagent"], 4)
    coef = np.abs(np.asarray(rec["coef"]))
    assert te["sharpe"] > 1.0 and rec["chosen"]["select_on"] == "val_r2"
    assert rec["intercept"] == 0.0
    assert int(np.argmax(coef)) == A1.columns.index("planted") and rec["coef"][A1.columns.index("planted")] > 0


def test_bootstrap_and_recency_weights():
    rng = np.random.default_rng(0)
    c = pool4.bootstrap_counts(1000, 100, rng)
    assert len(c) == 1000 and c.sum() == 1000 and set(np.unique(c)) <= set(range(11))
    assert np.all(c.reshape(10, 100) == c.reshape(10, 100)[:, :1])
    w = pool4.recency(np.array([0, 86400000 * 10]), 86400000 * 10, 10)
    assert np.allclose(w, [0.5, 1.0])
    assert np.allclose(pool4.recency(np.array([0, 5]), 10, None), 1.0)


# ---------------------------------------------------------------- end to end
def tiny_cfg(tmp_path):
    cfg = config.load_phase4()
    cfg["status"], cfg["primary"] = "frozen", "sp_pool2_full"
    cfg["data"]["dir"] = str(tmp_path / "data")
    cfg["report"].update({"out_dir": str(tmp_path / "out"), "runs_dir": str(tmp_path / "out" / "runs"),
                          "models_dir": str(tmp_path / "out" / "models4"), "cache_dir": str(tmp_path / "out" / "cache")})
    cfg["data_end"] = None
    cfg["assets"] = {"BTCUSDT": {"source": "rl_store", "eval": True}}
    cfg["pools"] = {"pool2": ["BTCUSDT"]}
    cfg["variants"] = {"sp_pool2_full": {"model": "sp", "pool": "pool2", "window": "expanding", "inputs": "full"},
                       "q_pool2_full": {"model": "q", "pool": "pool2", "window": "expanding", "inputs": "full"},
                       "sp_single12_p3": {"model": "sp", "pool": "single", "window": "window12", "inputs": "p3"}}
    cfg["walkforward"].update({"train_months": 2, "test_months": 1, "step_months": 1, "start": "2022-02-01",
                               "min_test_days": 10})
    cfg["train4"] = {"warmup_days": 31, "validation_months_expanding": 1, "validation_months_window12": 1}
    cfg["sp"] = dict(cfg["sp"], alphas=[0.1, 1.0], half_life_days=[None, 60], fallback_val_sharpe=-99.0)
    cfg["q"] = dict(cfg["q"], evals=2, eval_every=40, patience=1, half_life_days=[None], fallback_val_sharpe=-99.0)
    cfg["qagent"] = dict(cfg["qagent"], batch_size=32, chunk_steps=40)
    cfg["benchmarks"]["random"]["seeds"] = [0, 1, 2]
    cfg["phase3_reference"] = {"runs_glob": str(tmp_path / "none" / "phase3_*"), "loop_rules_assets": ["BTCUSDT"]}
    cfg["memory"] = {"start_mb": 0, "floor_mb": 0, "poll_s": 1}
    cfg["seeds"] = [0, 1]
    return cfg


def test_phase4_end_to_end_and_resume(tmp_path):
    cfg = tiny_cfg(tmp_path)
    bars = make_bars(n=96 * 200, seed=61, start="2022-01-01", drift=0.00005)
    store.write_frame(bars[data.BAR_COLS], data.bars_path(cfg))
    f = make_funding(bars.index, seed=62)
    store.write_frame(f[["rate"]], data.funding_path(cfg), index_name="funding_time")
    os.makedirs(cfg["report"]["cache_dir"], exist_ok=True)
    fake_snapshot(os.path.join(cfg["report"]["cache_dir"], "readings_BTCUSDT.npz"), bars.index)   # never the real store
    os.makedirs(cfg["report"]["out_dir"], exist_ok=True)
    with open(os.path.join(cfg["report"]["out_dir"], "phase4_lookahead.json"), "w") as fh:
        json.dump({"clean": True, "assets": {}}, fh)
    res = phase4.run(cfg, offline=True, log=lambda m: None)
    assert res["complete"]
    out = tmp_path / "out"
    summ = json.loads((out / "phase4_summary.json").read_text())
    assert summ["paper_only"] and summ["primary"] == "sp_pool2_full" and summ["headline_fee"] == "fee_0.10%"
    A = summ["assets"]["BTCUSDT"]["fees"]
    assert set(A) == {"fee_0.10%", "fee_0.05%"}
    for span in ("full_span", "to_2025_11_11"):
        st = A["fee_0.10%"][span]["strategies"]
        assert {"sp_pool2_full", "q_pool2_full", "sp_single12_p3"} <= set(st)
        assert "break_even_fee" in st["sp_pool2_full"]["seed_mean"] and len(st["sp_pool2_full"]["seeds"]) == 2
    dev = A["fee_0.10%"]["to_2025_11_11"]["benchmarks"]
    assert {"baseline_A", "baseline_B", "buy_hold_spot", "buy_hold", "momentum"} <= set(dev)
    assert "baseline_A" not in A["fee_0.10%"]["full_span"]["benchmarks"]      # the loop's rules: never past 2025-11-11
    ids = {f["id"] for f in summ["flags"]["BTCUSDT"]["sp_pool2_full"]}
    assert {"train_test_sharpe_gap", "seed_dispersion", "beats_benchmarks_in_under_half_the_folds", "fee_sign_flip",
            "high_turnover", "degenerate_policy"} <= ids
    md = (out / "phase4_report.md").read_text(encoding="utf-8")
    assert "## Verdict" in md and "2025-11-11" in md and "Edge before costs" in md
    # resume: nothing is retrained
    root = res["models_dir"]
    stamps = dict((p, os.path.getmtime(os.path.join(dp, p))) for dp, _, fs in os.walk(root) for p in fs)
    res2 = phase4.run(cfg, offline=True, log=lambda m: None)
    stamps2 = dict((p, os.path.getmtime(os.path.join(dp, p))) for dp, _, fs in os.walk(root) for p in fs)
    assert stamps == stamps2 and res2["verdict"]["text"] == res["verdict"]["text"]


def test_walkforward_refuses_an_unfrozen_config(tmp_path):
    cfg = tiny_cfg(tmp_path)
    cfg["status"] = "draft"
    try:
        phase4.run(cfg, offline=True, log=lambda m: None)
    except SystemExit as e:
        assert "not frozen" in str(e)
    else:
        raise AssertionError("an unfrozen config must not run the walk-forward")
