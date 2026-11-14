# -*- coding: utf-8 -*-
"""Harness tests: no look-ahead (truncation), cost accounting identical to engine15.rl.backtest, fill timing,
the sealed holdout. Synthetic bars; one test reads the real store if present.  py -3 -m pytest research/harness/tests -q"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

from research.harness import core, families  # noqa: E402
from engine15.rl import backtest as rlbt  # noqa: E402


def synth(n=9000, seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2021-01-01", periods=n, freq="15min", tz="UTC")
    lr = rng.normal(0.00002, 0.004, n)
    c = 30000 * np.exp(np.cumsum(lr))
    o = np.concatenate([[c[0]], c[:-1]]) * (1 + rng.normal(0, 0.0003, n))
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.001, n)))
    lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.001, n)))
    bars = pd.DataFrame({"open": o, "high": h, "low": lo, "close": c, "volume": 1.0}, index=idx)
    st = (np.arange(0, n, 32) * 900000 + int(idx[0].value // 10**6)).astype("int64")
    fund = pd.DataFrame({"rate": rng.normal(0.0001, 0.0001, len(st)), "settle_ms": st},
                        index=pd.to_datetime(st, unit="ms", utc=True))
    return bars, fund


def test_lean_backtest_equals_rl_backtest():
    bars, fund = synth()
    mkt = core.Market(bars, fund)
    rng = np.random.default_rng(0)
    tgt = np.round(rng.uniform(-1, 1, len(bars)) * 2) / 2
    for fee in (core.FEE_HEAD, core.FEE_ALT):
        ref = rlbt.run(bars, tgt, core.model(fee), fund)["frame"]
        fr = mkt.frame(tgt, fee)
        for col in ("pos", "trade", "r_gross", "fee", "spread", "slippage", "funding", "r_net"):
            assert np.allclose(fr[col].values, ref[col].values, atol=1e-15, rtol=0), col
        assert np.allclose(mkt.net(tgt, fee), ref["r_net"].values, atol=1e-15, rtol=0)


def test_leverage_is_linear_and_fees_charged_per_side():
    bars, fund = synth()
    mkt = core.Market(bars, fund)
    t = np.zeros(len(bars))
    t[100:200] = 1.0
    assert np.allclose(mkt.net(1.5 * t), 1.5 * mkt.net(t), atol=1e-15)
    fr = mkt.frame(t, 0.001)
    assert fr["trade"].values[101] == 1.0 and fr["trade"].values[201] == -1.0     # fills at the NEXT open
    assert fr["trade"].values[100] == 0.0
    assert abs(fr["fee"].sum() - 2 * 0.001) < 1e-15                                # one fee each side
    # break-even fee: at that fee the compounded net return is ~0
    oos = np.ones(len(bars), dtype=bool)
    be = core.breakeven_fee(mkt.frame(np.sign(np.sin(np.arange(len(bars)) / 50.0)), 0.001), oos)
    if be is not None and np.isfinite(be):
        r = mkt.net(np.sign(np.sin(np.arange(len(bars)) / 50.0)), be)
        assert abs(np.sum(np.log1p(r))) < 1e-6


def _targets(bars):
    f = core.features(bars)
    c = bars["close"].values
    f1, f2, f3 = families.F1(f, c), families.F2(f, c), families.F3(f, c)
    out = {"feat_" + k: f[k].values.astype(float) for k in f.columns}
    for key in [("mom", 0.0, "both", 1.5, "active", 16, 96), ("mr", 2.0, "4h", 0.0, "all", 1, 0),
                ("ema", 1.0, "1d", 2.5, "all", 96, 0)]:
        out["f1_%s" % (key,)] = f1.target(key)
    for key in families.f2_keys():
        out["f2_%s" % (key,)] = f2.target(key)
    for key in families.f3_keys()[:6]:
        out["f3_%s" % (key,)] = f3.target(key)
    return out


@pytest.mark.parametrize("cut", [7000, 8203])
def test_no_lookahead_truncation(cut):
    """Every feature and target at row t computed on bars[:cut] equals the full-data value for t < cut."""
    bars, _ = synth()
    full = _targets(bars)
    part = _targets(bars.iloc[:cut])
    for k in full:
        a, b = np.asarray(full[k][:cut], dtype=float), np.asarray(part[k], dtype=float)
        ok = np.isclose(a, b, equal_nan=True, atol=1e-9)
        assert ok.all(), "%s differs at %s" % (k, np.nonzero(~ok)[0][:5])


def test_truncation_check_catches_a_leak():
    bars, _ = synth()
    leak = lambda b: np.sign(b["close"].shift(-1) - b["close"]).fillna(0).values     # next bar: a peek
    a, b = leak(bars)[:7000], leak(bars.iloc[:7000])
    assert not np.array_equal(a, b)


def test_random_matched_has_the_same_number_of_changes():
    idx = pd.date_range("2021-01-01", periods=5000, freq="15min", tz="UTC")
    oos = np.zeros(5000, dtype=bool)
    oos[1000:] = True
    p = np.zeros(4000)
    p[100:900] = 1
    p[2000:3000] = -1
    r = core.random_matched(idx, oos, p, 1)
    assert np.count_nonzero(np.diff(r[oos], prepend=0.0)) == np.count_nonzero(np.diff(p, prepend=0.0))
    assert (r[~oos] == 0).all()


def test_sealed_holdout_is_not_loaded():
    p = os.path.join(ROOT, "data", "rl", "btcusdt_perp_15m.csv.gz")
    if not os.path.exists(p):
        pytest.skip("no BTC store")
    bars, fund = core.load("BTCUSDT", dev_only=True)
    assert bars.index[-1] < core.HOLDOUT_START
    assert (np.asarray(fund["settle_ms"]) < core.HOLDOUT_START.value // 10**6).all()


def _r2_targets(bars):
    from research.harness import round2
    f = core.features(bars)
    ex = round2.extra_features(bars, f)
    r = round2.R2(bars, f, ex)
    out = {"ex_" + k: ex[k].values for k in ex.columns}
    for k in round2.H25_KEYS[:4]:
        out["h25_%s" % (k,)] = r.h25(k)
    for v in ("ls", "lo", "lo15"):
        out["h26_" + v] = r.h26(v)
    out["h28"] = r.h28()
    for U, D in round2.H30_KEYS:
        out["h30_%g_%g" % (U, D)] = r.h30(U, D)
    for m in round2.H31_KEYS:
        out["h31_%g" % m] = r.h31(m)
    return out


@pytest.mark.parametrize("cut", [10500, 11777])
def test_round2_no_lookahead(cut):
    bars, _ = synth(n=12500, seed=5)
    full, part = _r2_targets(bars), _r2_targets(bars.iloc[:cut])
    for k in full:
        a, b = np.asarray(full[k][:cut], dtype=float), np.asarray(part[k], dtype=float)
        ok = np.isclose(a, b, equal_nan=True, atol=1e-9)
        assert ok.all(), "%s differs at %s" % (k, np.nonzero(~ok)[0][:5])


def test_spot_mode_funds_only_leverage_and_shorts():
    bars, fund = synth()
    mkt = core.Market(bars, fund)
    for lvl, funded in ((1.0, 0.0), (0.5, 0.0), (1.5, 0.5), (-0.5, -0.5)):
        t = np.full(len(bars), lvl)
        fr = mkt.frame(t, 0.001, spot=True)
        assert np.allclose(fr["funding"].values, funded * np.r_[0.0, np.ones(len(bars) - 1)] * mkt.rate, atol=1e-15)
    t = np.full(len(bars), 0.7)
    assert np.allclose(mkt.frame(t, 0.001, spot=False)["funding"].values, mkt.frame(t, 0.001)["pos"].values * mkt.rate)


def test_calendar_momentum_no_lookahead_and_matches_crypto_rule():
    from research.harness import round3
    bars, _ = synth(n=12000, seed=9)
    de = round3.day_end_flags(bars.index)
    full = round3.mom_cal(bars, 30, de)
    part = round3.mom_cal(bars.iloc[:10000], 30, de[:10000])
    assert np.array_equal(full[:9999], part[:9999])
    # on a 24/7 grid without gaps it is the frozen daily momentum rule
    ref = core.benchmarks.momentum(bars["close"]).values
    assert np.array_equal(full[:-1], ref[:-1])
