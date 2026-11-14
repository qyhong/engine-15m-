# -*- coding: utf-8 -*-
"""Tests for research/fills.py (charter item E, cheaper fills)."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

import fills  # noqa: E402


def make_px(o, h, l, c=None, atr15=1.0, fund=None):
    n = len(o)
    c = o if c is None else c
    return {"times": pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC"),
            "o": np.asarray(o, float), "h": np.asarray(h, float), "l": np.asarray(l, float),
            "c": np.asarray(c, float), "atr15": np.full(n, float(atr15)), "atr1h": np.full(n, 2.0),
            "fund": np.zeros(n) if fund is None else np.asarray(fund, float)}


def make_trade(side, j_in, j_out, why_out, p_out, stop, px):
    return pd.DataFrame([{"time_in": px["times"][j_in], "side": side, "j_in": j_in, "j_out": j_out,
                          "why_out": why_out, "p_out": p_out, "stop": stop}])


def flat_bars(n=12, price=100.0, wick=0.5):
    return [price] * n, [price + wick] * n, [price - wick] * n


def test_market_matches_the_engine_formula():
    o, h, l = flat_bars()
    o[5] = 104.0
    px = make_px(o, h, l)
    tr = make_trade(1, 2, 5, "FLIP", 104.0, 90.0, px)
    sim = fills.simulate(px, tr, fills.MARKET, fills.MARKET, "spot")
    e, x, fee = 100.0, 104.0, 0.0010                       # backtest.run_book: fee * qty * (entry + exit)
    assert sim.ret.iloc[0] == pytest.approx((x - e) / e - fee * (1 + x / e))


def test_limit_needs_a_strict_trade_through():
    o, h, l = flat_bars()
    l[2] = 100.0                                           # touches the limit only: no fill
    px = make_px(o, h, l)
    tr = make_trade(1, 2, 8, "FLIP", 100.0, 90.0, px)
    assert fills.entry_leg(px, tr.iloc[0], fills.limit(0.0, 1, "skip")) is None
    l[2] = 99.99
    px = make_px(o, h, l)
    j, price, maker = fills.entry_leg(px, tr.iloc[0], fills.limit(0.0, 1, "skip"))
    assert (j, price, maker) == (2, 100.0, True)


def test_improved_limit_is_in_the_trades_favour():
    o, h, l = flat_bars(wick=3.0)
    px = make_px(o, h, l, atr15=4.0)
    long_ = make_trade(1, 2, 8, "FLIP", 100.0, 80.0, px).iloc[0]
    short = make_trade(-1, 2, 8, "FLIP", 100.0, 120.0, px).iloc[0]
    assert fills.entry_leg(px, long_, fills.limit(0.5, 1, "skip"))[1] == 98.0
    assert fills.entry_leg(px, short, fills.limit(0.5, 1, "skip"))[1] == 102.0


def test_skip_misses_and_chase_pays_the_next_open():
    o = [100.0, 100, 100, 101, 102, 103, 104, 105, 106, 107]
    h = [x + 0.5 for x in o]
    l = [x for x in o]                                     # never trades below its open: a buy limit never fills
    px = make_px(o, h, l)
    tr = make_trade(1, 2, 9, "FLIP", 107.0, 90.0, px)
    sim = fills.simulate(px, tr, fills.limit(0.0, 2, "skip"), fills.MARKET, "perp")
    assert not sim.filled.iloc[0] and sim.ret.iloc[0] == 0.0
    j, price, maker = fills.entry_leg(px, tr.iloc[0], fills.limit(0.0, 2, "chase"))
    assert (j, price, maker) == (4, 102.0, False)          # window bars 2, 3; market at the open of bar 4


def test_entry_cancelled_once_the_exit_is_decided():
    o = [100.0] * 4 + [101.0] * 8
    l = list(o)
    h = [x + 0.5 for x in o]
    px = make_px(o, h, l)
    tr = make_trade(1, 2, 4, "FLIP", 101.0, 90.0, px)       # exit decided at the close of bar 3
    assert fills.entry_leg(px, tr.iloc[0], fills.limit(0.0, 4, "chase")) is None


def test_stop_exits_stay_at_the_replays_price():
    o, h, l = flat_bars()
    l[6] = 89.0
    px = make_px(o, h, l)
    tr = make_trade(1, 2, 6, "STOP", 90.0, 90.0, px)
    sim = fills.simulate(px, tr, fills.MARKET, fills.limit(0.5, 4), "perp")
    assert sim.p_out.iloc[0] == 90.0 and not sim.maker_out.iloc[0]


def test_exit_limit_lets_the_stop_come_first_in_the_same_bar():
    o, h, l = flat_bars()
    h[6], l[6] = 105.0, 89.0                               # one bar reaches both the sell limit and the stop
    px = make_px(o, h, l)
    tr = make_trade(1, 2, 6, "FLIP", 100.0, 90.0, px)
    j, price, maker = fills.exit_leg(px, tr.iloc[0], fills.limit(0.5, 2), 2)
    assert (j, price, maker) == (6, 90.0, False)
    h[6], l[6] = 105.0, 99.0
    px = make_px(o, h, l)
    j, price, maker = fills.exit_leg(px, tr.iloc[0], fills.limit(0.5, 2), 2)
    assert (j, price, maker) == (6, 100.5, True)


def test_unfilled_exit_chases():
    o, h, l = flat_bars(wick=0.1)
    px = make_px(o, h, l)
    tr = make_trade(1, 2, 6, "FLIP", 100.0, 90.0, px)
    j, price, maker = fills.exit_leg(px, tr.iloc[0], fills.limit(0.5, 2), 2)
    assert (j, price, maker) == (8, 100.0, False)


def test_fill_decisions_never_read_ahead():
    """The limit price uses the order bar's open and the ATR of the bar before; the fill uses only
    bars from the order bar to the fill bar. Changing anything later changes nothing."""
    rng = np.random.RandomState(3)
    o = 100 + np.cumsum(rng.normal(0, 0.5, 40))
    h, l = o + rng.uniform(0.1, 1.0, 40), o - rng.uniform(0.1, 1.0, 40)
    px = make_px(o, h, l)
    px["atr15"] = rng.uniform(0.5, 1.5, 40)
    tr = make_trade(1, 10, 30, "FLIP", o[30], 80.0, px).iloc[0]
    pol = fills.limit(0.25, 4, "chase")
    first = fills.entry_leg(px, tr, pol)
    j = first[0]
    px2 = dict((k, (v.copy() if isinstance(v, np.ndarray) else v)) for k, v in px.items())
    px2["atr15"][10:] = 99.0                               # ATR from the order bar on: not known yet
    px2["h"][j + 1:] += 50.0
    px2["l"][j + 1:] -= 50.0
    assert fills.entry_leg(px2, tr, pol) == first


def test_bar_inputs_use_past_bars_only():
    n = 600
    t = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    rng = np.random.RandomState(5)
    c = 100 + np.cumsum(rng.normal(0, 0.3, n))
    bars = pd.DataFrame({"open": c, "high": c + 0.4, "low": c - 0.4, "close": c, "volume": 1.0,
                         "taker_buy": 0.5}, index=t)
    a = fills.bars_arrays(bars)
    bars2 = bars.copy()
    bars2.iloc[400:, :4] *= 3.0
    b = fills.bars_arrays(bars2)
    np.testing.assert_allclose(a["atr15"][:400], b["atr15"][:400], equal_nan=True)
    np.testing.assert_allclose(a["atr1h"][:400], b["atr1h"][:400], equal_nan=True)


def test_funding_charged_on_perp_only():
    o, h, l = flat_bars()
    fund = np.zeros(12)
    fund[5:] = 0.001                                       # one settlement of 0.1% between entry and exit
    px = make_px(o, h, l, fund=fund)
    tr = make_trade(1, 2, 8, "FLIP", 100.0, 90.0, px)
    perp = fills.simulate(px, tr, fills.MARKET, fills.MARKET, "perp")
    spot = fills.simulate(px, tr, fills.MARKET, fills.MARKET, "spot")
    assert perp.fund_frac.iloc[0] == pytest.approx(0.001) and spot.fund_frac.iloc[0] == 0.0
    short = fills.simulate(px, make_trade(-1, 2, 8, "FLIP", 100.0, 110.0, px), fills.MARKET, fills.MARKET, "perp")
    assert short.fund_frac.iloc[0] == pytest.approx(-0.001)       # a short receives it


def test_score_counts_missed_winners_and_losers():
    mkt = pd.DataFrame({"time_in": pd.date_range("2021-01-01", periods=4, freq="400D", tz="UTC"),
                        "filled": True, "ret": [0.05, -0.02, -0.01, 0.03], "fee_frac": 0.002,
                        "fund_frac": 0.0, "maker_in": False, "maker_out": False})
    sim = mkt.copy()
    sim.loc[[0, 1], "filled"] = False
    sim.loc[[0, 1], ["ret", "fee_frac"]] = 0.0
    sc = fills.score(sim, mkt)
    assert (sc["missed"], sc["missed_winners"], sc["missed_losers"]) == (2, 1, 1)
    assert sc["missed_mkt_pnl_usd"] == 300.0


@pytest.mark.skipif(not os.path.exists(os.path.join(ROOT, "out", "replay", "trades_BTCUSDT.csv"))
                    or not os.path.exists(os.path.join(ROOT, "data", "btcusdt_15m.csv")),
                    reason="needs the replay trades and the BTC bars")
def test_incumbent_reproduces_the_replay():
    from engine15 import data
    bars = data.load("BTCUSDT")
    bars = bars[bars.index >= pd.Timestamp("2019-11-01", tz="UTC")]
    px = fills.bars_arrays(bars)
    tr = fills.locate(fills.load_trades("BTCUSDT"), px)
    assert tr.open_ok.all()
    sim = fills.simulate(px, tr, fills.MARKET, fills.MARKET, "spot")
    closed = tr[tr.why_out != "OPEN"]
    np.testing.assert_allclose(sim.ret.values * 100, closed.pnl_pct.values, atol=1e-9)
    st = closed[closed.why_out == "STOP"]
    exact = ~np.isclose(st.p_out.values, px["o"][st.j_out.values])
    np.testing.assert_allclose(st.p_out.values[exact], st.stop.values[exact], rtol=1e-6)
