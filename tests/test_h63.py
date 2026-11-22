# -*- coding: utf-8 -*-
"""H63's wallet walk (research/h63_member_wallet.py): the trades as prices and bars, the three sizings, the brake,
funding, the wipe-out rule and the finish lines. Planted bars, and the gate against the Setups book's replay.

    py -3 -m pytest tests/test_h63.py -q
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import h62_setups_wide_stop as h62  # noqa: E402
import h63_member_wallet as h63  # noqa: E402
from engine15.config import CFG  # noqa: E402
from test_shadows import random_inputs  # noqa: E402

B, E = "BTCUSDT", "ETHUSDT"
S1, S2, S3 = (h63.SIZINGS[k] for k in ("S1", "S2", "S3"))


def flat_px(n, price=100.0, **bars):
    """Both coins at `price` in every bar, except bars given as coin_i=(open, high, low, close)."""
    px = dict((c, dict((k, np.full(n, float(price))) for k in ("open", "high", "low", "close"))) for c in (B, E))
    for key, v in bars.items():
        c, i = (B if key[0] == "b" else E), int(key[1:])
        for k, x in zip(("open", "high", "low", "close"), v):
            px[c][k][i] = x
    return px


def times_of(n, start="2026-01-01"):
    return pd.date_range(start, periods=n, freq="15min", tz="UTC")


def setup(coin, i_in, i_out, side=-1, entry=100.0, stop0=104.0, p_final=104.0, t1=None, i_t1=None, in_bar=True):
    return {"coin": coin, "side": side, "entry": entry, "stop0": stop0, "i_in": i_in, "i_out": i_out, "t1": t1, "i_t1": i_t1,
            "p_final": p_final, "in_bar": in_bar, "why": "x"}


def go(setups, px, sz, n=None, fee=0.0, funding=None, **kw):
    n = n or len(px[B]["close"])
    ctx = h63.context(setups, px, times_of(n), fee, funding)
    return h63.walk(ctx, 0, n, h63.member_sizer(sz), **kw)


# ---------------------------------------------------------------- the trades as prices and bars
@pytest.mark.parametrize("seed", [3, 11, 17])
def test_gate_the_paper_sizing_walk_is_the_books_equity(seed):
    inp = random_inputs(seed=seed)
    px, odds, unit, shock, tide, bias, guard, aux = inp
    n = len(px["close"])
    row_of = lambda k: aux["targets"].iloc[k]                                                    # noqa: E731
    book = h62.run_setups(px, odds, shock, tide, unit, CFG, 1, n, bias=bias, guard=guard,
                          times_ms=np.arange(n, dtype="int64") * 900000, row_of=row_of)
    ok, why, setups = h63.gate(B, book, 1, n, dict(CFG), {B: px}, row_of)
    assert ok, why
    assert len(setups) > 30 and any(s["i_t1"] is not None for s in setups)
    assert any(not s["in_bar"] for s in setups) and any(s["in_bar"] for s in setups)


def test_a_trade_with_target_1_is_split_at_the_first_bar_that_reaches_it():
    px = flat_px(8, b3=(100, 100, 95.5, 96), b5=(96, 96, 91, 92))[B]
    # short from 100: half at 96 (bar 3), the rest at 92 (bar 5): the book's row says p_out 94, "T1+T2"
    s = h63.setup_of(B, -1, 100.0, 104.0, 1, 5, 94.0, "T1+T2", 96.0, px)
    assert s["i_t1"] == 3 and abs(s["p_final"] - 92.0) < 1e-12 and s["in_bar"]
    flip = h63.setup_of(B, -1, 100.0, 104.0, 1, 6, 101.0, "FLIP", 96.0, px)
    assert flip["i_t1"] is None and flip["p_final"] == 101.0 and not flip["in_bar"]
    with pytest.raises(RuntimeError):
        h63.setup_of(B, -1, 100.0, 104.0, 1, 2, 94.0, "T1+STOP_BE", 96.0, px)      # no bar reaches 96 by bar 2


# ---------------------------------------------------------------- the sizings
def test_s1_loses_two_percent_at_the_stop_and_s2_s3_carry_the_wallet():
    px = flat_px(6, b3=(100, 104.5, 100, 104))
    one = [setup(B, 1, 3)]
    r1 = go(one, px, S1)
    assert abs(r1["wallet"] - 9800.0) < 1e-9 and r1["joined"] == 1           # 2% of 10,000 at a 4% stop: 50 units
    r2 = go(one, px, S2)
    assert abs(r2["wallet"] - 9600.0) < 1e-9                                  # 1.0x: 100 units, 4 lost on each
    r3 = go(one, px, S3)
    assert abs(r3["wallet"] - 9400.0) < 1e-9                                  # 1.5x: 150 units
    assert r1["eq"][2] == 10000.0 and abs(r1["eq"][3] - 9800.0) < 1e-9        # marked at the close, then realised


def test_s1_notional_is_capped_at_the_free_balance():
    px = flat_px(6)
    # BTC: stop 1% away -> 2% risk wants 2.0x the wallet: capped at 1.0x. ETH then has no free balance: not joined.
    r = go([setup(B, 1, None, stop0=101.0), setup(E, 2, None, stop0=101.0)], px, S1)
    assert r["capped"] == 2 and r["joined"] == 1 and r["not_joined"] == 1
    assert abs(r["open"][0]["qty"] - 100.0) < 1e-9


def test_fees_and_the_half_at_target_1():
    px = flat_px(8, b3=(100, 100, 95.5, 96), b5=(96, 96, 91, 92))
    s = [setup(B, 1, 5, p_final=92.0, t1=96.0, i_t1=3)]
    r = go(s, px, S2, fee=0.001)
    # 100 units short from 100: 50 at 96 (+200, fees 0.001*50*196), 50 at 92 (+400, fees 0.001*50*192)
    assert abs(r["wallet"] - (10000 + 200 + 400 - 9.8 - 9.6)) < 1e-9 and abs(r["fees"] - 19.4) < 1e-9
    assert abs(r["eq"][3] - (10000 + 200 - 9.8 + 50 * 4)) < 1e-9             # half realised, half marked at 96
    assert r["results"] == [(5, B, pytest.approx(580.6))]


# ---------------------------------------------------------------- the brake
def test_the_brake_trims_a_trade_to_the_days_budget_and_then_joins_nothing():
    n = 12
    px = flat_px(n, b2=(100, 110.5, 100, 110), e4=(100, 110.5, 100, 110))
    # S2, brake 15% of 10,000 = 1,500. BTC: 100 units, stop 10 away: loses 1,000. ETH: wants 90 units (wallet 9,000)
    # at a stop 10 away = 900 at risk, budget 1,500 - 1,000 = 500 -> 50 units. Then nothing is left: the third is not joined.
    s = [setup(B, 1, 2, stop0=110.0, p_final=110.0), setup(E, 3, 4, stop0=110.0, p_final=110.0), setup(B, 6, None, stop0=110.0)]
    r = go(s, px, S2)
    assert r["joined"] == 2 and r["trimmed"] == 2 and r["not_joined"] == 1
    assert abs(r["wallet"] - 8500.0) < 1e-9
    # the next UTC day starts a new budget: the same third trade, entered after midnight, is joined in full
    n2 = 110
    s2 = s[:2] + [setup(B, 100, None, stop0=110.0)]
    r2 = go(s2, flat_px(n2, b2=(100, 110.5, 100, 110), e4=(100, 110.5, 100, 110)), S2)
    assert r2["joined"] == 3 and abs(r2["open"][0]["qty"] - 85.0) < 1e-9


def test_the_other_coins_open_risk_counts_against_the_budget_until_target_1():
    px = flat_px(10, b3=(100, 100, 95.5, 96))
    # S3: BTC 150 units, stop 6 away = 900 at risk; ETH wants 150 units at 6 = 900, budget 1,500 - 900 = 600 -> 100 units
    r = go([setup(B, 1, None, stop0=106.0), setup(E, 2, None, stop0=106.0)], px, S3)
    assert r["trimmed"] == 1 and abs(sorted(p["qty"] for p in r["open"])[0] - 100.0) < 1e-9
    # after BTC's Target 1 its stop is at the entry: no open risk, ETH is joined in full (1.5 x the wallet then)
    r = go([setup(B, 1, None, stop0=106.0, t1=96.0, i_t1=3), setup(E, 4, None, stop0=106.0)], px, S3)
    eth = next(p for p in r["open"] if p["coin"] == E)
    assert r["trimmed"] == 0 and abs(eth["qty"] - 1.5 * r["wallet"] / 100.0) < 1e-9


# ---------------------------------------------------------------- funding, the wipe-out, the finish lines
def test_a_short_receives_positive_funding_and_a_long_pays_it():
    n = 40
    px = flat_px(n)
    fund = {B: (np.array([32]), np.array([0.001])), E: (np.array([32]), np.array([0.001]))}
    r = go([setup(B, 1, None)], px, S2, funding=fund)
    assert abs(r["wallet"] - 10010.0) < 1e-9 and abs(r["funding"] + 10.0) < 1e-9    # 100 units x 100 x 0.1%, received
    r = go([setup(B, 1, None, side=1, stop0=96.0)], px, S2, funding=fund)
    assert abs(r["wallet"] - 9990.0) < 1e-9
    assert go([setup(B, 1, None)], px, S2, funding=fund, funding_on=False)["wallet"] == 10000.0
    assert go([setup(B, 33, None)], px, S2, funding=fund)["wallet"] == 10000.0      # entered after the funding time


def test_the_wallet_is_wiped_out_at_the_worst_price_of_a_bar():
    # S3, both coins short 150 units from 100 with stops far away (no brake trim: the day's budget is not the point
    # here, so the stops are planted 4.9 away and the bars go through 170 without the book closing: an open trade).
    sz = dict(S3, brake=10.0)
    px = flat_px(8, b4=(100, 140, 100, 101), e4=(100, 140, 100, 101))
    s = [setup(B, 1, None, stop0=104.9), setup(E, 1, None, stop0=104.9)]
    r = go(s, px, sz)
    # at 140 on both: 10,000 - 300 x 40 < 0.5% of the notional: wiped out in bar 4
    assert r["outcome"] == "wiped" and r["end"] == 4 and r["wallet"] == 0.0 and r["eq"][4] == 0.0 and r["eq"][7] == 0.0
    assert go(s, px, sz, worst_px=False)["outcome"] is None                          # the closes alone do not show it
    px2 = flat_px(8, b4=(100, 130, 100, 101), e4=(100, 130, 100, 101))
    assert go(s, px2, sz)["outcome"] is None                                         # 10,000 - 9,000 = 1,000 > 0.5% x 39,000


def test_the_finish_lines_end_the_walk_at_the_first_close_beyond_either():
    px = flat_px(10, b3=(100, 100, 60, 60), b4=(60, 60, 30, 30))
    s = [setup(B, 1, None, stop0=104.0)]
    r = go(s, px, S3, lines=(20000.0, 5000.0))
    assert r["outcome"] == "up" and r["end"] == 4                                    # +6,000 at bar 3, +10,500 at bar 4
    assert np.isnan(r["eq"][5])
    up = flat_px(10, b3=(100, 134, 100, 134))                                        # 150 short: -5,100 at the close
    r = go(s, up, dict(S3, brake=10.0), lines=(20000.0, 5000.0))
    assert r["outcome"] == "down" and r["end"] == 3
    # a wallet started later does not join a trade that is already open
    ctx = h63.context(s, px, times_of(10), 0.0)
    late = h63.walk(ctx, 2, 10, h63.member_sizer(S3), lines=(20000.0, 5000.0), join_from=2)
    assert late["outcome"] is None and late["joined"] == 0 and late["wallet"] == 10000.0


def test_read_outs_worst_fall_losing_run_and_month_tally():
    assert abs(h63.worst_fall(np.array([100.0, 120.0, 90.0, 130.0, np.nan])) + 25.0) < 1e-9
    assert h63.losing_run([(1, B, -1.0), (2, E, -2.0), (3, B, 5.0), (4, B, -1.0)]) == 2
    rows = [{"outcome": "up", "days": 10.0, "end_equity": 2e4}, {"outcome": "down", "days": 30.0, "end_equity": 5e3},
            {"outcome": "wiped", "days": 50.0, "end_equity": 0.0}, {"outcome": "neither", "days": 365.0, "end_equity": 9e3},
            {"outcome": "unfinished", "days": 40.0, "end_equity": 1.1e4}]
    t = h63.tally(rows)
    assert (t["starts"], t["up"], t["down"], t["wiped"], t["neither"], t["unfinished"]) == (5, 1, 1, 1, 1, 1)
    assert t["median_days_to_either"] == 30.0 and t["median_days_down"] == 40.0 and t["median_end_neither"] == 9e3


def test_funding_times_land_on_the_bar_that_opens_then():
    times = times_of(100, "2026-01-01")
    f = pd.Series([0.001, 0.002, 0.003], index=pd.DatetimeIndex([
        pd.Timestamp("2026-01-01 08:00", tz="UTC"), pd.Timestamp("2026-01-01 16:00", tz="UTC") + pd.Timedelta(milliseconds=1),
        pd.Timestamp("2026-01-03 00:00", tz="UTC")]))                 # the last one is after the bars: not counted missing
    ix, rates, missing = h63.funding_bars(B, times, series=f)
    assert list(ix) == [32, 64] and list(rates) == [0.001, 0.002] and missing == 0
