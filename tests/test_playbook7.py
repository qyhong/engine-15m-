# -*- coding: utf-8 -*-
"""playbook7 (H37 V4 forward pair book): it must reproduce the H37 study's V4 targets and per-bar net returns, read no
future bar, and count nothing before REGISTERED."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine15 import playbook4 as p4  # noqa: E402
from engine15 import playbook7 as p7  # noqa: E402


def _bars(days=700, end="2025-06-01"):
    from engine15 import data
    out = {}
    for a in p7.ASSETS:
        df = data.load(a)
        e = pd.Timestamp(end, tz="UTC")
        df = df[(df.index >= e - pd.Timedelta(days=days)) & (df.index < e)]
        out[a] = df[["open", "high", "low", "close"]].astype(float)
    common = out["BTCUSDT"].index.intersection(out["ETHUSDT"].index)
    return dict((a, df.loc[common]) for a, df in out.items())


@pytest.fixture(scope="module")
def bars():
    return _bars()


def test_targets_match_the_study(bars):
    ls = pytest.importorskip("research.longshort_study")
    b, e = bars["BTCUSDT"], bars["ETHUSDT"]
    fB, fE = ls.daily_feats(b.assign(volume=0.0)), ls.daily_feats(e.assign(volume=0.0))
    warm = 260 * 96                                       # after the 200-day average + 20-day slope exist
    for own, fo, fx, is_btc in (("BTCUSDT", fB, fE, True), ("ETHUSDT", fE, fB, False)):
        ref = ls.rv_targets(fo, fx, is_btc)
        mine = p7.targets(p7.daily_feats(bars[own]), p7.daily_feats(bars[p7.OTHER[own]]), is_btc)
        for leg in p7.LEGS:
            assert np.array_equal(ref[leg][warm:], mine[leg][warm:]), (own, leg)
        assert (np.asarray(mine["own_spot"][warm:]) != 1.0).any()   # the window has downtrend bars


def test_net_returns_match_the_study(bars):
    ls = pytest.importorskip("research.longshort_study")
    from engine15 import data
    from research.harness import core
    b, e = bars["BTCUSDT"], bars["ETHUSDT"]
    fuB = p4.funding_frame(data.load_funding("BTCUSDT"))
    fuE = p4.funding_frame(data.load_funding("ETHUSDT"))
    T = p7.targets(p7.daily_feats(b), p7.daily_feats(e), True)
    mB, mE = core.Market(b, fuB), core.Market(e, fuE)
    ref = ls.run_legs([(mB, T["own_spot"], False), (mB, T["own_perp"], True),
                       (mE, T["oth_spot"], False), (mE, T["oth_perp"], True)])
    MB, ME = p4.market(p4.features(b), fuB), p4.market(p4.features(e), fuE)
    mine = p7.legs_frame(dict((leg, p7.held(T[leg])) for leg in p7.LEGS), MB, ME)
    assert np.allclose(ref["r_net"], mine["r_net"], atol=1e-12)


def test_no_look_ahead(bars):
    b, e = bars["BTCUSDT"], bars["ETHUSDT"]
    full = p7.targets(p7.daily_feats(b), p7.daily_feats(e), True)
    cut = len(b) - 3 * 96 - 37                            # mid-day cut
    part = p7.targets(p7.daily_feats(b.iloc[:cut]), p7.daily_feats(e.iloc[:cut]), True)
    for leg in p7.LEGS:
        assert np.array_equal(full[leg][:cut], part[leg])


def test_forward_only(monkeypatch, bars):
    b = bars["BTCUSDT"]
    reg = b.index[-200 * 96]                              # a forward start 200 days before the window's end
    monkeypatch.setattr(p7, "REGISTERED", str(reg)[:16])
    monkeypatch.setattr(p7, "WARMUP_DAYS", 450)
    from engine15 import data
    fu = dict((a, p4.funding_frame(data.load_funding(a))) for a in p7.ASSETS)
    rows = p7.step(bars=bars, funding=fu)
    rms = p7.reg_ms()
    assert rows
    for r in rows:
        assert pd.Timestamp(r["entry_utc"], tz="UTC").value // 10**6 > rms
    for own in p7.ASSETS:
        mine = sorted([r for r in rows if r["asset"] == own], key=lambda r: r["entry_utc"])
        first = pd.Timestamp(mine[0]["entry_utc"], tz="UTC").value // 10**6
        assert first - rms <= p7.BAR_MS                    # entered at the first close after the start
        assert sum(1 for r in mine if r["status"] == "OPEN") == 1
        st = p7.LAST_STATE["p7_rvbear"][own]
        total = sum(r["pnl_usd"] for r in mine)
        assert abs((st["equity_usd"] - p7.STAKE) - total) < 0.05 * len(mine) + 0.05
        assert all(abs(sum(abs(x) for x in r["legs"].values())) <= 1.5 + 1e-12 for r in mine)
