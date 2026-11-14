# -*- coding: utf-8 -*-
"""tests for research/longshort_study.py (H37, exploration; paper only).

1. No look-ahead: every target computed on truncated bars equals the one computed on the full bars at every earlier bar.
2. The downtrend rule reads closed daily bars only: it changes only at the 15m bar ending 00:00 UTC and equals the
   rule computed from the daily closes up to the previous UTC day.
3. Funding sign: a perp short is PAID a positive rate and pays a negative one; a spot leg pays no funding.
4. Accounting: a single spot / perp leg reproduces the harness's core.Market (spot=True / False) exactly; fees are charged
   on both legs of a hedge.
5. Gross exposure never exceeds 1.5 in any registered variant.
6. The study loader never returns a holdout bar (skipped if the stored history is missing)."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from research import longshort_study as ls  # noqa: E402
from research.harness import core  # noqa: E402


def synth(n=96 * 420, seed=3, start="2021-01-01"):
    """Up 150 days, down 150, up again: enough for SMA200 and several D turns."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=n, freq="15min", tz="UTC", name="open_time")
    day = np.arange(n) // 96
    drift = np.where(day < 210, 0.00006, np.where(day < 330, -0.00008, 0.00007))
    lr = rng.normal(drift, 0.003, n)
    c = 100.0 * np.exp(np.cumsum(lr))
    o = np.concatenate([[100.0], c[:-1]])
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.001, n)))
    lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.001, n)))
    bars = pd.DataFrame({"open": o, "high": h, "low": lo, "close": c, "volume": 1.0}, index=idx)
    st = np.arange(int(idx[0].value // 10**6) + 8 * 3600000, int(idx[-1].value // 10**6), 8 * 3600000, dtype="int64")
    rate = rng.normal(0.0001, 0.0002, len(st))
    fund = pd.DataFrame({"rate": rate, "settle_ms": st}, index=pd.to_datetime(st, unit="ms", utc=True))
    return bars, fund


def _cut_fund(fund, bars):
    hi = int(bars.index[-1].value // 10**6) + ls.BAR_MS
    return fund[np.asarray(fund["settle_ms"]) <= hi]


def test_no_lookahead_truncation():
    bars, fund = synth()
    full, _ = ls.coin_targets(bars, fund)
    assert (full["V1_dial0"][1] < 0).any(), "synthetic data must reach the downtrend regime"
    assert (full["V5_fr_hedge"][1] < 0).any(), "synthetic data must trigger the failed-rally hedge"
    for cut in (96 * 260 + 37, 96 * 300 + 5, 96 * 360 + 71):
        b = bars.iloc[:cut]
        part, _ = ls.coin_targets(b, _cut_fund(fund, b))
        for k in full:
            for leg in (0, 1):
                assert np.array_equal(full[k][leg][:cut], part[k][leg]), (k, leg, cut)
    # the V4 sleeve too
    bars2, _ = synth(seed=9)
    fa, fb = ls.daily_feats(bars), ls.daily_feats(bars2)
    t_full = ls.rv_targets(fa, fb, True)
    cut = 96 * 300 + 11
    t_part = ls.rv_targets(ls.daily_feats(bars.iloc[:cut]), ls.daily_feats(bars2.iloc[:cut]), True)
    for k in t_full:
        assert np.array_equal(t_full[k][:cut], t_part[k]), k


def test_downtrend_rule_uses_closed_daily_bars_only():
    bars, _ = synth()
    f = ls.daily_feats(bars)
    D = f["D"].values
    ch = np.nonzero(np.diff(D) != 0)[0] + 1
    assert len(ch) > 0
    assert f["is_daily"].values[ch].all(), "D may change only at the bar ending 00:00 UTC"
    # recompute from daily closes: at a row closing at 00:00 UTC of day k+1, D is the rule on days <= k
    dc = bars["close"].resample("1D").last()
    sma = dc.rolling(200).mean()
    rule = ((dc < sma) & (sma < sma.shift(20))).astype(float)
    rows = np.nonzero(f["is_daily"].values)[0]
    for t in rows[250::7]:
        day_closed = bars.index[t].floor("1D")              # the bar opening 23:45 ends the day it opened in
        assert D[t] == rule.loc[day_closed], bars.index[t]
        if t + 50 < len(D):
            assert D[t + 50] == D[t]                         # unchanged until the next daily close


def test_funding_sign_short_paid_spot_none():
    bars, fund = synth(n=96 * 10)
    mkt = core.Market(bars, fund)
    n = len(bars)
    short = ls.run_legs([(mkt, -np.ones(n), True)])
    spot = ls.run_legs([(mkt, np.ones(n), False)])
    k = np.nonzero(mkt.rate != 0)[0]
    k = k[k > 1]
    pos_r, neg_r = k[mkt.rate[k] > 0], k[mkt.rate[k] < 0]
    assert len(pos_r) and len(neg_r)
    assert (short["funding"][pos_r] > 0).all(), "a short must receive a positive rate"
    assert (short["funding"][neg_r] < 0).all(), "a short must pay a negative rate"
    assert np.allclose(short["funding"][k], mkt.rate[k])
    assert (spot["funding"] == 0).all(), "spot pays no funding"
    long_perp = ls.run_legs([(mkt, np.ones(n), True)])
    assert np.allclose(long_perp["funding"], -mkt.rate * ls.held(np.ones(n)))


def test_single_leg_matches_harness_and_fees_on_both_legs():
    bars, fund = synth(n=96 * 30)
    mkt = core.Market(bars, fund)
    rng = np.random.default_rng(1)
    t = np.round(rng.uniform(-1, 1, len(bars)) * 4) / 4
    t = pd.Series(t).where(np.arange(len(t)) % 37 == 0).ffill().fillna(0.0).values
    ts = np.clip(t, 0, 1)
    assert np.allclose(ls.run_legs([(mkt, ts, False)])["r_net"], mkt.net(ts, core.FEE_HEAD, spot=True), atol=1e-15)
    assert np.allclose(ls.run_legs([(mkt, t, True)])["r_net"], mkt.net(t, core.FEE_HEAD, spot=False), atol=1e-15)
    # a hedge from spot 1 to spot 0.75 + perp -0.75 trades 1.0 in total and pays the fee on 1.0
    n = len(bars)
    s = np.where(np.arange(n) >= 100, 0.75, 1.0)
    p = np.where(np.arange(n) >= 100, -0.75, 0.0)
    r = ls.run_legs([(mkt, s, False), (mkt, p, True)])
    assert r["fees"][101] == pytest.approx(core.FEE_HEAD * 1.0)
    assert r["net"][101] == pytest.approx(0.0) and r["gross"][101] == pytest.approx(1.5)


def test_gross_cap_all_variants():
    bars, fund = synth()
    T, f = ls.coin_targets(bars, fund)
    for k, (s, p) in T.items():
        assert (np.abs(s) + np.abs(p)).max() <= ls.GROSS_MAX + 1e-12, k
        assert (s >= 0).all(), k
    bars2, _ = synth(seed=9)
    t = ls.rv_targets(f, ls.daily_feats(bars2), False)
    g = sum(np.abs(v) for v in t.values())
    assert g.max() <= ls.GROSS_MAX + 1e-12


def test_loader_never_returns_holdout_bars():
    try:
        bars, fund = core.load("ETHUSDT", dev_only=True)
    except Exception as e:                                   # pragma: no cover
        pytest.skip("no stored history: %r" % (e,))
    assert bars.index[-1] < core.HOLDOUT_START
    assert (np.asarray(fund["settle_ms"]) < int(core.HOLDOUT_START.value // 10**6)).all()
