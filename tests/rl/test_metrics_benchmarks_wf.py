# -*- coding: utf-8 -*-
"""Metrics on known series; benchmark rules; the walk-forward splitter."""
import numpy as np
import pandas as pd

from conftest import make_bars
from engine15.rl import backtest, benchmarks, metrics, walkforward
from engine15.rl.costs import CostModel


def test_bars_per_year_is_365_times_96():
    assert metrics.BARS_PER_YEAR == 35040


def test_sharpe_and_sortino_on_a_known_series():
    r = np.array([0.01, -0.01, 0.02, -0.02] * 10)
    assert metrics.sharpe(r) == 0.0
    r2 = np.array([0.002, 0.0, 0.002, 0.0])
    want = 0.001 / np.std(r2, ddof=1) * np.sqrt(35040)
    assert np.isclose(metrics.sharpe(r2), want)
    r3 = np.array([0.03, -0.01, 0.03, -0.01])
    dd = np.sqrt(np.mean(np.array([0, -0.01, 0, -0.01]) ** 2))
    assert np.isclose(metrics.sortino(r3), 0.01 / dd * np.sqrt(35040))
    assert metrics.sortino(np.array([0.01, 0.02])) == 0.0        # no downside: reported as 0, not infinity


def test_max_drawdown_cagr_calmar():
    eq = np.array([1.0, 1.2, 0.9, 1.1, 0.6, 1.5])
    assert np.isclose(metrics.max_drawdown(eq), 0.5)
    r = np.full(35040, (1.21) ** (1 / 35040) - 1)                 # +21% in exactly one year
    assert np.isclose(metrics.cagr(r), 0.21)
    r2 = np.r_[np.full(17520, 0.0), -0.1, np.full(17519, 0.0)]
    assert np.isclose(metrics.calmar(r2), -0.1 / 0.1)


def test_turnover_holding_and_cost_drag():
    pos = np.array([0, 1, 1, 1, -1, -1, 0, 0, 0.5, 0.5])
    assert np.isclose(metrics.turnover(pos, per_year=10), 1 + 2 + 1 + 0.5)
    assert metrics.holding_runs(pos) == [3, 2, 2]
    fr = pd.DataFrame({"r_gross": np.full(10, 0.001), "r_net": np.full(10, 0.0005), "pos": np.ones(10),
                       "fee": np.full(10, 0.0005), "spread": 0.0, "slippage": 0.0, "funding": 0.0})
    s = metrics.summary(fr, per_year=10)
    assert np.isclose(s["cost_drag_per_year"], 0.005) and np.isclose(s["fee_per_year"], 0.005)
    assert s["avg_holding_bars"] == 10 and s["exposure"] == 1.0


def test_retired_every_bar_momentum_is_sign_of_96_bar_return():
    b = make_bars(n=500, seed=4)
    t = benchmarks.momentum_every_bar(b["close"], 96)
    r = np.log(b["close"]).diff(96)
    assert (t.iloc[:96] == 0).all()
    assert np.array_equal(t.values[96:], np.sign(r.values[96:]))


def test_momentum_decides_once_a_day_on_the_30_day_sign():
    b = make_bars(n=96 * 80, seed=4)
    t = benchmarks.momentum(b["close"], 30)
    ch = np.nonzero(np.diff(t.values) != 0)[0] + 1
    assert len(ch) > 0
    assert all(b.index[i].hour == 23 and b.index[i].minute == 45 for i in ch)   # bar ending 00:00 UTC
    r = np.log(b["close"]).diff(30 * 96).values
    dec = np.nonzero((b.index.hour == 23) & (b.index.minute == 45))[0]
    for i in dec:
        exp = np.sign(r[i]) if not np.isnan(r[i]) else 0.0
        assert t.values[i] == exp
        assert (t.values[i:i + 96] == exp).all()                 # held until the next decision
    assert (t.values[:30 * 96] == 0).all()                       # not enough history -> flat
    lf = benchmarks.momentum(b["close"], 30, long_short=False)
    assert set(np.unique(lf.values)) <= {0.0, 1.0} and set(np.unique(t.values)) <= {-1.0, 0.0, 1.0}
    assert len(np.unique(t.values)) >= 2


def test_random_agent_is_reproducible_and_on_schedule():
    b = make_bars(n=96 * 20, seed=4)
    a1 = benchmarks.random_agent(b.index, 3)
    a2 = benchmarks.random_agent(b.index, 3)
    a3 = benchmarks.random_agent(b.index, 4)
    assert a1.equals(a2) and not a1.equals(a3)
    ch = np.nonzero(np.diff(a1.values) != 0)[0] + 1
    assert all(b.index[i].hour == 23 and b.index[i].minute == 45 for i in ch)   # bar ending 00:00 UTC
    assert set(np.unique(a1.values)) <= {-1.0, 0.0, 1.0}


def test_walkforward_windows_never_overlap_and_train_precedes_test():
    idx = pd.date_range("2020-01-01", "2023-02-15", freq="15min", tz="UTC").as_unit("ms")
    wins = walkforward.windows(idx, 12, 3, 3, "2020-01-01", 30)
    assert len(wins) >= 8
    for w in wins:
        assert w["train_end"] == w["test_start"] and w["train_start"] < w["train_end"] < w["test_end"]
    for a, b in zip(wins, wins[1:]):
        assert a["test_end"] == b["test_start"]                  # back to back: one unbroken OOS span
    assert wins[-1]["test_end"] <= idx[-1] + pd.Timedelta("15min")


def test_walkforward_drops_a_too_short_final_window():
    idx = pd.date_range("2020-01-01", "2021-04-10", freq="15min", tz="UTC").as_unit("ms")
    wins = walkforward.windows(idx, 12, 3, 3, "2020-01-01", 30)
    assert len(wins) == 1                                         # Apr 1-10 is under 30 days


def test_stitch_and_evaluate_slice_one_continuous_backtest():
    b = make_bars(n=96 * 120, seed=5, start="2022-01-01")
    wins = walkforward.windows(b.index, 1, 1, 1, "2022-01-01", 10)
    seen = []

    def fn(tr, te):
        seen.append((tr.sum(), te.sum()))
        assert b.index[tr].max() < b.index[te].min()             # training data ends before the test starts
        return np.ones(te.sum())
    st = walkforward.stitch(b.index, wins, fn)
    assert (st[b.index < wins[0]["test_start"]] == 0).all()
    fr = backtest.run(b, st, CostModel())["frame"]
    ev = walkforward.evaluate(fr, wins)
    assert len(ev["windows"]) == len(wins) == len(seen)
    assert ev["windows"][1]["trades"] == 0                       # buy-and-hold already in: no re-entry cost
    lr = sum(np.log1p(w["total_return"]) for w in ev["windows"])
    assert np.isclose(lr, np.log1p(ev["stitched"]["total_return"]))
