# -*- coding: utf-8 -*-
"""Phase 3 pieces on planted data: features (no look-ahead), reward timing == backtester, afterstate Q structure,
decision rules (hold default, min hold, gates, band, masks, consensus), continual-learning timing, risk manager."""
import numpy as np
import pandas as pd
import pytest

from conftest import make_bars, make_funding
from engine15.rl import backtest, continual, features, features3, policy3, qagent, risk3
from engine15.rl.costs import CostModel
from engine15.rl.env import Market

QC = {"net_arch": [], "learning_rate": 5e-4, "weight_decay": 0.3, "batch_size": 64, "gamma": 0.99, "n_step": 4,
      "target_every": 50, "reward_scale": 100.0, "cost_mult": 2.0, "risk_aversion": 1.0, "vol_scale": True,
      "vol_ref_annual": 0.6, "evals": 2, "eval_every": 100, "patience": 2, "chunk_steps": 100, "select_on": "val_loss",
      "fallback_val_sharpe": None, "replay_days": 30, "half_life_days": 10, "recency_mix": 0.5, "finetune_steps": 20}
ACTS = [-1.0, -0.5, 0.0, 0.5, 1.0]


def gappy(n, seed):
    b = make_bars(n=n, seed=seed)
    rng = np.random.RandomState(seed + 7)
    b["open"] = b["open"] * np.exp(rng.normal(0, 0.002, n))
    b["high"] = np.maximum(b["high"], b[["open", "close"]].max(axis=1))
    b["low"] = np.minimum(b["low"], b[["open", "close"]].min(axis=1))
    return b


def mk(b, f, model=None):
    return Market(b, f, features3.build(b, f).astype("float32"), model or CostModel())


# ---------------------------------------------------------------- features
def test_phase3_features_never_read_the_future():
    b = make_bars(n=7000, seed=12)
    f = make_funding(b.index, seed=13)
    cuts = [3100, 4444, 5000, 6999, 96 * 50, 96 * 50 + 37]
    rep = features.lookahead_report(lambda x, y: features3.build(x, y), b, f, cuts)
    assert all(v == [] for v in rep.values()), rep
    cols = features3.build(b, f).columns
    for c in ("trend_1h", "trend_4h", "trend_1d", "px_sma_4h", "mom_signal", "vol_regime", "rv_1d_30", "tod_sin", "dow_cos"):
        assert c in cols


def test_leaky_htf_feature_is_caught():
    b = make_bars(n=4000, seed=14)

    def leaky(x, y):
        df = features3.build(x, y)
        df["peek"] = np.log(x["close"]).diff(-4).values          # the next hour: must be caught
        return df
    rep = features.lookahead_report(leaky, b, None, [2000, 3000])
    assert all("peek" in v for v in rep.values())


def test_time_features_mark_the_bar_close():
    b = make_bars(n=200, seed=15, start="2024-01-01")            # a Monday
    tf = features3.time_features(b.index)
    assert np.isclose(tf["tod_sin"][95], 0.0, atol=1e-9) and np.isclose(tf["tod_cos"][95], 1.0)    # closes at 00:00
    week = np.arctan2(tf["dow_sin"], tf["dow_cos"]) % (2 * np.pi) / (2 * np.pi)
    assert abs(week[95] - 1.0 / 7.0) < 1e-9                      # Tuesday 00:00 = 1/7 of the week (Monday = 0)


# ---------------------------------------------------------------- reward timing and Q structure
def test_reward_arrays_match_the_backtester_one_bar_at_a_time():
    b = gappy(1500, 21)
    f = make_funding(b.index, seed=22)
    m = mk(b, f)
    rd = qagent.reward_arrays(m, {"vol_scale": False})
    rng = np.random.RandomState(3)
    tgt = np.zeros(len(b))
    tgt[700:1400] = rng.choice(ACTS, 700)
    fr = backtest.run(b, tgt, m.model, f)["frame"]
    t = np.arange(700, 1398)
    prev = tgt[t - 1]
    want = tgt[t] * rd["g"][t] - rd["c1"][t] * np.abs(tgt[t] - prev)       # R with cost_mult 1, k 1, no risk term
    assert np.allclose(want, fr["r_net"].values[t + 1], atol=1e-6)
    spot = tgt[t] * rd["rpx"][t] - tgt[t] * rd["rate"][t]
    assert np.allclose(spot, tgt[t] * rd["g"][t], atol=1e-7)


def test_q_is_w_minus_a_hard_wired_round_trip_cost():
    b = make_bars(n=3000, seed=31)
    m = mk(b, None)
    rd = qagent.reward_arrays(m, QC)
    L = qagent.Learner(m.raw.shape[1], ACTS, QC, 0, *m.fit_norm(500, 2500))
    L.train(m.raw, rd, np.arange(800, 2400), 30)
    Q = L.q(m.raw, rd, 2500, 2600)
    W = L.w(m.raw[2500:2600])
    for p in range(5):
        assert np.allclose(Q[:, p, p], W[:, p], atol=1e-6)                 # holding is free
    c = 100 * 2 * rd["k"][2500:2600] * rd["c1"][2500:2600]
    assert np.allclose(W[:, 4] - Q[:, 0, 4], 2.0 * c, rtol=1e-4)            # -1 -> +1 costs 2 units x a round trip


def test_untrained_agent_holds_and_starts_flat():
    b = make_bars(n=3000, seed=32)
    m = mk(b, None)
    rd = qagent.reward_arrays(m, QC)
    L = qagent.Learner(m.raw.shape[1], ACTS, QC, 0)
    Q = L.q(m.raw, rd, 1000, 2000)
    ip, st = policy3.decide(Q, ACTS, 2, 0)
    assert st["changes"] == 0 and (ip == 2).all()


def test_agent_learns_a_strong_planted_edge():
    from engine15.rl import learncheck
    m, pl, _ = learncheck.scenario_market(2 * 35040 // 3, 5, 0.08)
    q = dict(QC, n_step=8, evals=3, eval_every=600, batch_size=128)
    rd = qagent.reward_arrays(m, q)
    b = {"tr_lo": 3000, "val_lo": 15000, "tr_hi": 19000}
    L, rec = continual.full_train(m, rd, b, q, {"min_hold_bars": 4}, ACTS, 1)
    Q = L.q(m.raw, rd, 19000, len(pl))
    ip, _ = policy3.decide(Q, ACTS, 2, 4)
    pos = np.asarray(ACTS)[ip]
    assert np.corrcoef(pos, pl[19000:])[0, 1] > 0.2


# ---------------------------------------------------------------- decisions
def test_decide_hold_min_hold_gate_band_and_forced():
    n = 12
    Q = np.zeros((n, 3, 3), np.float32)
    Q[:, :, 2] = 1.0                                              # every bar: action 2 looks better than holding
    ip, st = policy3.decide(Q, [-1, 0, 1], 1, min_hold=0)
    assert ip[0] == 2 and st["changes"] == 1
    ip, st = policy3.decide(Q, [-1, 0, 1], 1, min_hold=5, since0=0)
    assert (ip[:5] == 1).all() and ip[5] == 2 and st["min_hold_refusals"] == 5
    gate = np.zeros(n, bool)
    gate[7] = True
    ip, st = policy3.decide(Q, [-1, 0, 1], 1, gate=gate)
    assert (ip[:7] == 1).all() and ip[7] == 2
    ip, st = policy3.decide(Q, [-1, 0, 1], 1, thr=np.full(n, 2.0, np.float32))
    assert (ip == 1).all() and st["band_holds"] == n
    masks = np.ones((n, 3), bool)
    masks[3:, 2] = False
    masks[3:, 1] = False                                          # only 'short' allowed from bar 3: forced move
    ip, st = policy3.decide(Q, [-1, 0, 1], 1, min_hold=100, masks=masks)
    assert ip[3] == 0 and st["forced"] >= 1


def test_consensus_needs_every_seed():
    n = 6
    A = [-1, 0, 1]
    q1 = np.zeros((n, 3, 3), np.float32)
    q1[:, :, 2] = 1.0
    q2 = q1.copy()
    q2[:3, :, 2] = 0.0
    q2[:3, :, 0] = 1.0                                            # seed 2 wants short for the first 3 bars
    ip, st = policy3.consensus([policy3.prepare(q1), policy3.prepare(q2)], A, 1)
    assert (ip[:3] == 1).all() and (ip[3:] == 2).all() and st["disagree_holds"] == 3


def test_fast_net_equals_backtest():
    b = gappy(1200, 41)
    f = make_funding(b.index, seed=42)
    m = mk(b, f)
    rng = np.random.RandomState(1)
    t = np.zeros(len(b))
    t[300:1100] = rng.choice(ACTS, 800)
    r, g, pos = policy3.fast_net(m, t[300:1100], 300, 1100, start_pos=t[299])
    fr = backtest.run(b, t, m.model, f)["frame"]
    assert np.allclose(r, fr["r_net"].values[301:1100], atol=1e-15)


# ---------------------------------------------------------------- continual-learning timing
def test_updates_are_weekly_mondays_and_never_train_on_the_future():
    b = make_bars(n=96 * 60, seed=51, start="2024-01-01")
    m = mk(b, None)
    ups = continual.update_bars(m, 0, m.n, 7)
    for u in ups:
        t = b.index[u] + pd.Timedelta(minutes=15)
        assert t.hour == 0 and t.minute == 0 and t.dayofweek == 0
    rd = qagent.reward_arrays(m, QC)
    L = qagent.Learner(m.raw.shape[1], ACTS, QC, 0, *m.fit_norm(0, 2000))
    U = int(ups[-1])
    rec = continual.fine_tune(L, m, rd, U, QC)
    assert rec["pool_hi"] + QC["n_step"] <= U - 1                # an n-step target closes by bar U


def test_run_span_switches_model_exactly_at_the_update_bar():
    b = make_bars(n=96 * 50, seed=52, start="2024-01-01")
    m = mk(b, None)
    rd = qagent.reward_arrays(m, QC)
    L = qagent.Learner(m.raw.shape[1], ACTS, QC, 0, *m.fit_norm(0, 2000))
    L.train(m.raw, rd, np.arange(100, 2000), 50)
    lo, hi = 96 * 35, 96 * 50
    st0 = L.state()
    W, ups = continual.run_span(L, m, rd, lo, hi, QC, cadence_days=7)
    u = ups[0]["U"]
    L.load_state(st0)
    W0 = L.w(m.raw[lo:hi])
    assert np.allclose(W[:u - lo], W0[:u - lo])                  # before the update: the old model
    assert not np.allclose(W[u - lo:u - lo + 50], W0[u - lo:u - lo + 50])   # from the update bar on: the new one


def test_neutral_fallback_goes_to_the_neutral_position_and_stays():
    W = continual.neutral_w(20, [0.0, 0.5, 1.0, 1.5], 1.0)
    rd = {"k": np.ones(20, np.float32), "c1": np.full(20, 0.0015, np.float32)}
    Q = continual.q_of(W, rd, 0, 20, QC, [0.0, 0.5, 1.0, 1.5])
    ip, _ = policy3.decide(Q, [0.0, 0.5, 1.0, 1.5], 3, 0)
    assert (ip == 2).all()


# ---------------------------------------------------------------- risk manager
RC = {"enabled": True, "vol_target": 0.6, "max_position": 1.0, "vol_short": "rv_672", "vol_long": "rv_672",
      "rebalance_band": 0.2, "dd_window_bars": 960, "dd_levels": [0.05, 0.10], "dd_factors": [0.75, 0.5]}


def test_risk3_sizes_by_vol_brakes_softly_and_logs_reasons():
    b = make_bars(n=5000, seed=61)
    b.loc[b.index[3000:3300], "close"] *= np.exp(np.cumsum(np.random.RandomState(2).normal(0, 0.02, 300)))
    b["open"] = np.concatenate([[b["close"].iloc[0]], b["close"].values[:-1]])
    b["high"] = b[["open", "close"]].max(axis=1) * 1.001
    b["low"] = b[["open", "close"]].min(axis=1) * 0.999
    m = mk(b, None)
    t = np.zeros(len(b))
    t[1000:] = 1.0
    r = risk3.apply(m, t, 1000, len(b), RC)
    ex = r["exec"][1000:]
    assert ex.max() <= 1.0 + 1e-12 and ex.min() > 0.0            # resized, never forced flat (soft brake)
    assert ex.min() < 0.8                                         # high vol / drawdown cut the size
    assert len(r["events"]) > 0 and all(e["reason"] for e in r["events"])
    assert (np.abs(np.diff(ex)) > 0).sum() <= len(r["events"]) + 1   # every change is logged


def test_risk3_never_reads_after_the_decision_bar():
    b = gappy(4000, 62)
    f = make_funding(b.index, seed=63)
    full = mk(b, f)
    t = np.zeros(len(b))
    t[1500:] = np.where(np.arange(len(b) - 1500) % 300 < 150, 1.0, -0.5)
    a = risk3.apply(full, t, 1500, len(b), RC)["exec"]
    for cut in (2600, 3333):
        bc = b.iloc[:cut]
        fc = f[np.asarray(f["settle_ms"]) <= int(bc.index[-1].value // 10**6) + 900000]
        part = mk(bc, fc)
        p = risk3.apply(part, t[:cut], 1500, cut, RC)["exec"]
        assert np.array_equal(a[:cut], p)


def test_risk3_stepper_is_the_same_code_as_apply():
    b = gappy(3000, 64)
    m = mk(b, None)
    t = np.zeros(len(b))
    t[1200:] = np.where(np.arange(len(b) - 1200) % 200 < 120, 1.0, 0.0)
    a = risk3.apply(m, t, 1200, len(b), RC)
    st = risk3.Stepper(RC, m.model)
    c = m.col("rv_672")
    out = [st.step(i, t[i], m.close_ms[i], m.r_bar[i], m.r_px[i - 1], m.vol[i - 1], m.rate[i], float(m.raw[i, c]),
                   float(m.raw[i, c])) for i in range(1200, len(b))]
    assert np.allclose(out, a["exec"][1200:], atol=0, rtol=0)
