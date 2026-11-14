# -*- coding: utf-8 -*-
"""The shared cost model and the vectorised backtester, on hand-made series."""
import numpy as np
import pandas as pd
import pytest

from engine15.rl import backtest, costs
from engine15.rl.costs import CostModel


def flat_bars(n=20, price=100.0, start="2022-01-01 00:00"):
    idx = pd.date_range(start, periods=n, freq="15min", tz="UTC").as_unit("ms")
    p = np.full(n, price)
    return pd.DataFrame({"open": p, "high": p, "low": p, "close": p, "volume": np.ones(n)}, index=idx)


def fee_only(fee=0.001, delay=1):
    return CostModel(fee_side=fee, half_spread_bps=0.0, slippage_coef=0.0, funding=True, delay_bars=delay)


def one_funding(bars, at, rate):
    s = int(pd.Timestamp(at, tz="UTC").value // 10**6)
    return pd.DataFrame({"rate": [rate], "settle_ms": [s]}, index=pd.to_datetime([s], unit="ms", utc=True))


def test_flat_strategy_costs_nothing():
    b = flat_bars()
    b["close"] = b["open"] * np.linspace(1, 1.1, len(b))
    f = one_funding(b, "2022-01-01 01:00", 0.01)
    res = backtest.run(b, np.zeros(len(b)), CostModel(), f)
    fr = res["frame"]
    assert (fr[["fee", "spread", "slippage", "funding", "r_gross", "r_net"]].values == 0).all()
    assert fr["equity_net"].iloc[-1] == 1.0 and len(res["trades"]) == 0


def test_one_bar_delay_decision_at_close_fills_next_open():
    b = flat_bars(10)
    b["open"] = 100.0 + np.arange(10)                            # opens 100, 101, ...
    b["close"] = b["open"]
    tgt = np.zeros(10)
    tgt[3:] = 1.0                                                 # decided at the close of bar 3
    fr = backtest.run(b, tgt, fee_only(0.0))["frame"]
    assert list(fr["pos"].values[:5]) == [0, 0, 0, 0, 1]          # held from the open of bar 4
    assert fr["r_gross"].iloc[3] == 0.0
    assert np.isclose(fr["r_gross"].iloc[4], 105.0 / 104.0 - 1)   # open 4 -> open 5


def test_longer_delay_is_honoured_and_zero_delay_is_refused():
    b = flat_bars(10)
    tgt = np.zeros(10)
    tgt[2] = 1.0
    fr = backtest.run(b, tgt, fee_only(0.0, delay=3))["frame"]
    assert fr["pos"].iloc[5] == 1.0 and fr["pos"].iloc[4] == 0.0
    with pytest.raises(ValueError):
        CostModel(delay_bars=0)


def test_fees_are_charged_per_side_and_scale_with_size():
    b = flat_bars(10)
    tgt = np.array([1, 1, -1, -1, 0.5, 0.5, 0, 0, 0, 0], dtype=float)
    fr = backtest.run(b, tgt, fee_only(0.001))["frame"]
    # trades at bars 1 (+1), 3 (-2: a flip is two sides), 5 (+1.5), 7 (-0.5)
    assert np.allclose(fr["fee"].values[[1, 3, 5, 7]], [0.001, 0.002, 0.0015, 0.0005])
    assert np.isclose(fr["fee"].sum(), 0.005)
    assert np.isclose(fr["equity_net"].iloc[-1], np.prod(1 - fr["fee"].values))


def test_funding_signs_long_pays_short_receives():
    b = flat_bars(12)
    f = one_funding(b, "2022-01-01 01:00", 0.0005)              # settles at the END of bar 00:45
    long_ = backtest.run(b, np.ones(12), fee_only(0.0), f)["frame"]
    short = backtest.run(b, -np.ones(12), fee_only(0.0), f)["frame"]
    k = b.index.get_loc(pd.Timestamp("2022-01-01 00:45", tz="UTC"))
    assert np.isclose(long_["funding"].iloc[k], 0.0005)          # cost > 0: paid
    assert np.isclose(short["funding"].iloc[k], -0.0005)         # cost < 0: received
    assert np.isclose(long_["funding"].sum(), 0.0005)
    neg = one_funding(b, "2022-01-01 01:00", -0.0005)
    assert backtest.run(b, np.ones(12), fee_only(0.0), neg)["frame"]["funding"].sum() < 0   # longs receive a negative rate


def test_funding_goes_to_the_position_held_through_the_settlement():
    b = flat_bars(12)
    f = one_funding(b, "2022-01-01 01:00", 0.001)
    tgt = np.zeros(12)
    tgt[k := b.index.get_loc(pd.Timestamp("2022-01-01 00:45", tz="UTC"))] = 1.0   # decided AT the settlement close
    fr = backtest.run(b, tgt, fee_only(0.0), f)["frame"]
    assert fr["funding"].sum() == 0.0                            # filled after the settlement: pays nothing
    tgt2 = np.zeros(12)
    tgt2[k - 1] = 1.0                                             # filled at the open of the settlement bar
    assert np.isclose(backtest.run(b, tgt2, fee_only(0.0), f)["frame"]["funding"].sum(), 0.001)


def test_spread_and_slippage_components():
    b = flat_bars(300)
    rng = np.random.RandomState(0)
    b["close"] = 100 * np.exp(np.cumsum(rng.normal(0, 0.004, 300)))
    b["open"] = np.r_[100.0, b["close"].values[:-1]]
    m = CostModel(fee_side=0.0, half_spread_bps=2.0, slippage_coef=0.5, slippage_vol_window=96, delay_bars=1)
    tgt = np.zeros(300)
    tgt[200] = 1.0
    fr = backtest.run(b, tgt, m)["frame"]
    vol = m.bar_vol(b)
    assert np.isclose(fr["spread"].iloc[201], 2e-4)
    assert np.isclose(fr["slippage"].iloc[201], 0.5 * vol[200])  # vol from the DECISION bar
    assert np.isclose(fr["slippage"].iloc[202], 0.5 * vol[201])  # closing the position
    assert fr["slippage"].sum() > 0


def test_buy_and_hold_equals_price_path_minus_one_entry_cost():
    b = flat_bars(50)
    b["open"] = 100.0 * 1.001 ** np.arange(50)
    b["close"] = np.r_[b["open"].values[1:], b["open"].values[-1] * 1.001]
    fr = backtest.run(b, np.ones(50), fee_only(0.001))["frame"]
    want = (1 - 0.001) * b["close"].iloc[-1] / b["open"].iloc[1]
    assert np.isclose(fr["equity_net"].iloc[-1], want, rtol=1e-6)


def test_nan_target_means_flat_and_targets_are_clipped():
    b = flat_bars(6)
    fr = backtest.run(b, [np.nan, 3.0, -7.0, np.nan, 0, 0], fee_only(0.0))["frame"]
    assert list(fr["pos"]) == [0.0, 0.0, 1.0, -1.0, 0.0, 0.0]


def test_fee_profiles_show_both_fees():
    cfg = {"costs": {"fee_side": 0.001, "fee_side_alt": 0.0005, "half_spread_bps": 0.5, "slippage_coef": 0.1,
                     "slippage_vol_window": 96, "funding": True, "delay_bars": 1}}
    p = costs.fee_profiles(cfg)
    assert [m.fee_side for m in p.values()] == [0.001, 0.0005]
    assert list(p) == ["fee_0.10%", "fee_0.05%"]


def test_step_formula_matches_vectorised_run():
    """The simulator's per-bar call and the backtester give the same costs (one model)."""
    b = flat_bars(200)
    rng = np.random.RandomState(1)
    b["close"] = 100 * np.exp(np.cumsum(rng.normal(0, 0.003, 200)))
    b["open"] = np.r_[100.0, b["close"].values[:-1]]
    f = one_funding(b, "2022-01-01 08:00", 0.0003)
    m = CostModel()
    tgt = rng.choice([-1.0, 0.0, 1.0], 200)
    fr = backtest.run(b, tgt, m, f)["frame"]
    vol, rate = m.bar_vol(b), m.funding_on_bars(b.index, f)
    prev = 0.0
    for k in range(1, 200):
        pos = tgt[k - 1]
        c = m.step(pos - prev, pos, vol[k - 1], rate[k])
        for key in ("fee", "spread", "slippage", "funding"):
            assert np.isclose(c[key], fr[key].iloc[k])
        prev = pos
