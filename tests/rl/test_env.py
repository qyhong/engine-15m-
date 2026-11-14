# -*- coding: utf-8 -*-
"""The Phase 2 environment: no look-ahead in observations, and env P&L == backtest P&L."""
import numpy as np
import pandas as pd
import pytest

from conftest import make_bars, make_funding
from engine15.rl import backtest, features
from engine15.rl.costs import CostModel
from engine15.rl.env import Market, TradingEnv, frame_from_record, run_policy

ECFG = {"decision_every_bars": 4, "min_hold_bars": 0, "turnover_penalty": 0.0, "reward_scale": 1.0,
        "obs_clip": 5.0, "actions": [-1.0, 0.0, 1.0]}
FCFG = {"return_windows": [1, 4, 16, 96], "vol_windows": [16, 96, 672], "momentum_windows": [16, 96],
        "volume_z_window": 672, "daily_closed": True}


def gappy_bars(n, seed):
    """Bars whose next open differs from the close (so a peek at open[t+1] would show)."""
    b = make_bars(n=n, seed=seed)
    rng = np.random.RandomState(seed + 7)
    b["open"] = b["open"] * np.exp(rng.normal(0, 0.002, n))
    b["high"] = np.maximum(b["high"], b[["open", "close"]].max(axis=1))
    b["low"] = np.minimum(b["low"], b[["open", "close"]].min(axis=1))
    return b


def market(b, f, model=None):
    feats = features.build(b, f, FCFG).astype("float32")
    return Market(b, f, feats, model or CostModel())


def norm(m):
    return m.fit_norm(800, 2000)


def drive(env, actions, marks=None):
    obs, _ = env.reset(options={"position": 0.0})
    seen = [obs]
    for a in actions:
        obs, r, term, trunc, _ = env.step(a)
        seen.append(obs)
        if marks is not None and env.risk is not None:
            marks.append(env.risk.equity)                       # what the risk manager saw at the last bar
        if term or trunc:
            break
    return seen


RISK = {"enabled": True, "max_position": 1.0, "max_daily_loss": 0.01, "kill_drawdown": 0.03, "kill_cooldown_bars": 96,
        "vol_breaker_mult": 1.2, "vol_breaker_max_position": 0.5}


RISK_LOOSE = dict(RISK, max_daily_loss=0.99, kill_drawdown=0.99)      # never flattens: positions stay on


@pytest.mark.parametrize("risk", [None, RISK, RISK_LOOSE])
def test_observation_at_t_never_uses_data_after_t(risk):
    b = gappy_bars(3000, 31)
    f = make_funding(b.index, seed=32)
    full = market(b, f)
    mu, sd = norm(full)
    rng = np.random.RandomState(5)
    acts = rng.randint(0, 3, 600) if risk is not RISK_LOOSE else rng.choice([0, 2], 600)   # loose: never flat
    lo = 800
    for cut in (1500, 2003, 2600):
        bc = b.iloc[:cut]
        t_close = int(bc.index[-1].value // 10**6) + 900000
        fc = f[np.asarray(f["settle_ms"]) <= t_close]
        part = market(bc, fc)
        e_full = TradingEnv(full, lo, len(b), (mu, sd), ECFG, risk)
        e_part = TradingEnv(part, lo, cut, (mu, sd), ECFG, risk)
        # every decision of the cut env, including the last one (its bar is cut - 1 when cut is on the hour)
        ma, mp = [], []
        a = drive(e_full, acts, ma)
        p = drive(e_part, acts, mp)
        nd = len(e_part.dec)
        assert nd > 10 and len(p) >= nd
        assert (cut % 4 != 0) or e_part.dec[-1] == cut - 1
        for k in range(nd):
            assert e_full.dec[k] == e_part.dec[k]
            assert np.array_equal(a[k], p[k]), "obs %d (bar %d) differs when data after it is removed" % (k, e_part.dec[k])
        if risk is not None:                                     # equity the risk manager acts on: bar closes only
            assert np.array_equal(np.array(ma[:nd - 1]), np.array(mp[:nd - 1]))


def test_env_pnl_equals_backtest_pnl_for_the_same_targets():
    b = gappy_bars(4000, 41)
    f = make_funding(b.index, seed=42)
    m = market(b, f)
    rng = np.random.RandomState(9)
    acts = rng.randint(0, 3, 2000)
    lo, hi = 1000, 3600
    for ecfg, risk in ((ECFG, None), (dict(ECFG, min_hold_bars=12, turnover_penalty=0.001), RISK)):
        env = TradingEnv(m, lo, hi, norm(m), ecfg, risk, record=True)
        it = iter(acts)
        run_policy(env, lambda obs: next(it))
        tgt = np.nan_to_num(env.tgt_rec, nan=0.0)
        tgt[:lo] = 0.0
        assert np.isnan(env.tgt_rec[lo:hi]).sum() == 0
        fr = backtest.run(b, tgt, m.model, f)["frame"]
        sl = slice(lo, hi)
        assert np.allclose(env.r_net[sl], fr["r_net"].values[sl], atol=1e-15, rtol=0)
        assert np.allclose(env.pos_rec[sl], fr["pos"].values[sl])
        for c in ("fee", "spread", "slippage", "funding"):
            assert np.allclose(env.cost[c][sl], fr[c].values[sl], atol=1e-15, rtol=0)
        assert fr["trade"].abs().sum() > 10
        if risk:
            assert sum(env.risk.counts.values()) > 0          # the risk manager actually acted here


def test_decision_at_close_fills_next_open_and_reward_is_net_log_return():
    b = gappy_bars(1500, 51)
    m = market(b, None, CostModel(fee_side=0.001, half_spread_bps=0.0, slippage_coef=0.0, funding=False))
    ecfg = dict(ECFG, turnover_penalty=0.0005, reward_scale=10.0)
    env = TradingEnv(m, 800, 1500, norm(m), ecfg, None, record=True)
    env.reset(options={"position": 0.0})
    i = env.dec[0]
    _, r, *_ = env.step(2)                                       # long
    assert env.pos_rec[i] == 0.0 and env.pos_rec[i + 1] == 1.0  # filled at the open of the next bar
    net = np.array([m.r_px[j] - (0.001 if j == i + 1 else 0.0) for j in range(i + 1, i + 5)])
    assert np.isclose(r, 10.0 * (np.log1p(net).sum() - 0.0005 * 1.0))


def test_min_hold_refuses_early_changes():
    b = gappy_bars(1500, 61)
    m = market(b, None)
    env = TradingEnv(m, 800, 1500, norm(m), dict(ECFG, min_hold_bars=16), None, record=True)
    env.reset(options={"position": 0.0, "since": 0})
    env.step(2)                                                  # 0 bars held: refused
    assert env.cur == 0.0 and env.stats["min_hold_refusals"] == 1
    for _ in range(4):
        env.step(1)                                              # stay flat 16 bars
    env.step(2)
    assert env.cur == 1.0
    env.step(0)                                                  # just changed: refused
    assert env.cur == 1.0


def test_training_episodes_are_random_and_bounded():
    b = gappy_bars(3000, 71)
    m = market(b, None)
    env = TradingEnv(m, 800, 2800, norm(m), ECFG, None, episode_decisions=50, seed=3, random_start_position=True)
    starts, n = set(), 0
    for _ in range(5):
        env.reset()
        starts.add(env.p0)
        steps = 0
        while True:
            _, _, term, trunc, _ = env.step(env.action_space.sample())
            steps += 1
            if term or trunc:
                break
        assert steps == 50 and trunc and not term
        n += 1
    assert len(starts) > 1
    assert env.observation_space.shape == (m.raw.shape[1] + 3,)
