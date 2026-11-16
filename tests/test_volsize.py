# -*- coding: utf-8 -*-
"""H52 (research/volsize_study.py): no look-ahead in the forecast, the reference, the weights and the proxy sides;
the trade / proxy accounting and the exposure-matching constant on hand-made examples."""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

import volsize_study as vs  # noqa: E402
from engine15 import data  # noqa: E402


def _bars(days=110, seed=3, cash=False):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2021-01-01", periods=days * 96, freq="15min", tz="UTC")
    if cash:                                             # a cash-hours market: 14:30-20:45 UTC weekdays only
        m = (idx.weekday < 5) & (((idx.hour == 14) & (idx.minute >= 30)) | ((idx.hour >= 15) & (idx.hour < 21)))
        idx = idx[m]
    n = len(idx)
    vol = 0.002 * np.exp(np.cumsum(rng.normal(0, 0.03, n)))  # clustered volatility
    c = 100 * np.exp(np.cumsum(rng.normal(0, 1, n) * vol))
    o = np.r_[100.0, c[:-1]] * (1 + rng.normal(0, 1e-4, n))
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, vol)))
    l_ = np.minimum(o, c) * (1 - np.abs(rng.normal(0, vol)))
    return pd.DataFrame({"open": o, "high": h, "low": l_, "close": c, "volume": 1.0}, index=idx)


def _all_at(df, B, at):
    sig = vs.har_sigma(df["close"].values, B)
    end, _ = vs.day_ends(df.index)
    tms = np.asarray(data.to_ms(df.index))
    ref = vs.reference(sig, tms, end, at)
    return sig, ref, dict((v, vs.weight(v, sig[at], *ref)) for v in vs.VARIANTS)


def test_bars_per_day():
    assert vs.bars_per_day(_bars(30).index) == 96
    assert vs.bars_per_day(_bars(30, cash=True).index) == 26


def test_har_by_hand():
    df = _bars(40)
    B = 96
    sig = vs.har_sigma(df["close"].values, B)
    r = np.r_[np.nan, np.diff(np.log(df["close"].values))]
    assert np.isnan(sig[22 * B - 1]) and np.isfinite(sig[22 * B])
    for i in (22 * B, 22 * B + 517, len(df) - 1):
        v = [np.mean(r[i - k * B + 1:i + 1] ** 2) for k in (1, 5, 22)]
        assert np.isclose(sig[i], np.sqrt(B * np.mean(v)), rtol=1e-10)


def _trunc_check(cash):
    df = _bars(200 if cash else 130, cash=cash)
    B = vs.bars_per_day(df.index)
    n = len(df)
    at = np.arange(n // 2, n, 37)
    sig, ref, W = _all_at(df, B, at)
    assert np.isfinite(ref[0]).sum() > 10
    for cut in (int(n * 0.6), int(n * 0.83), n - 5):
        d2 = df.iloc[:cut]
        a2 = at[at < cut]
        s2, r2, W2 = _all_at(d2, B, a2)
        assert np.allclose(sig[:cut], s2, rtol=1e-12, equal_nan=True)
        for x, y in zip(ref, r2):
            assert np.allclose(x[:len(a2)], y, rtol=1e-12, equal_nan=True)
        for v in vs.VARIANTS:
            assert np.allclose(W[v][:len(a2)], W2[v], rtol=1e-12, equal_nan=True)
        pf = [d for d in vs.proxy_decisions(df, B) if d[0] < cut - 2 * B]
        pc = [d for d in vs.proxy_decisions(d2, B) if d[0] < cut - 2 * B]
        assert pf == pc and len(pf) > 20


def test_truncation_24h():
    _trunc_check(False)


def test_truncation_cash_hours():
    _trunc_check(True)


def test_reference_by_hand_and_strictly_before():
    df = _bars(130)
    B = 96
    sig = vs.har_sigma(df["close"].values, B)
    end, _ = vs.day_ends(df.index)
    tms = np.asarray(data.to_ms(df.index))
    i = int(np.where(end)[0][100])                       # a day-end bar: it must NOT be in its own reference
    m, q33, q67 = vs.reference(sig, tms, end, [i])
    e = np.where(end & np.isfinite(sig))[0]
    e = e[(e < i) & (tms[e] > tms[i] - 365 * 86400000)]
    assert np.isclose(m[0], np.median(sig[e]))
    assert np.isclose(q67[0], np.percentile(sig[e], 200 / 3.0))
    # changing sigma at the decision bar itself does not change its reference
    s2 = sig.copy()
    s2[i] *= 10
    assert np.isclose(vs.reference(s2, tms, end, [i])[0][0], m[0])
    # too few day-ends -> no reference -> every weight 1
    j = int(np.where(end & np.isfinite(sig))[0][5])
    r = vs.reference(sig, tms, end, [j])
    assert np.isnan(r[0][0])
    for v in vs.VARIANTS:
        assert vs.weight(v, sig[[j]], *r)[0] == 1.0


def test_weights():
    s = np.array([0.5, 1.0, 2.0, 100.0])
    m, q33, q67 = np.ones(4), np.full(4, 0.8), np.full(4, 1.5)
    assert np.allclose(vs.weight("S0", s, m, q33, q67), 1)
    assert np.allclose(vs.weight("S1", s, m, q33, q67), [2, 1, 0.5, 0.25])
    assert np.allclose(vs.weight("S2", s, m, q33, q67), [4, 1, 0.25, 0.25])
    assert np.allclose(vs.weight("S3", s, m, q33, q67), [np.sqrt(2), 1, np.sqrt(0.5), 0.25])
    assert np.allclose(vs.weight("S4", s, m, q33, q67), [1, 1, 0.5, 0.25])
    assert np.allclose(vs.weight("S5", s, m, q33, q67), [1, 1, 0.5, 0.5])
    assert np.allclose(vs.weight("S6", s, m, q33, q67), [1.5, 1, 0.5, 0.5])


def test_trade_accounting():
    o = np.array([10, 11, 12, 13, 14, 15, 16, 17.0])
    c = np.array([11, 12, 13, 14, 15, 16, 17, 18.0])
    fee = 0.001
    trades = [(2, 5, 1, 12.0, 14.5), (5, 5, -1, 15.0, 15.5), (6, 7, -1, 16.0, 17.0)]
    w = np.array([2.0, 1.0, 0.5])
    pnl, expo = vs.trade_pnl(o, c, trades, w, fee, len(o))
    want = 0.0
    for (i_in, i_out, s, p_in, p_out), wk in zip(trades, w):
        q = wk * vs.CAPITAL / p_in
        want += q * s * (p_out - p_in) - fee * q * (p_in + p_out)
    assert np.isclose(pnl.sum(), want)
    assert np.allclose(expo, [0, 0, 2e4, 2e4, 2e4, 1e4, 5e3, 0])
    assert pnl[:2].sum() == 0                            # nothing before the entry bar


def test_proxy_accounting_and_next_open_fill():
    o = np.array([10, 10, 11, 12, 12, 13.0])
    c = np.array([10, 11, 12, 12, 13, 13.0])
    fee = 0.001
    dec = [(1, 1), (3, -1)]
    pnl, expo = vs.proxy_pnl(o, c, dec, np.array([1.0, 2.0]), fee, len(o), 0)
    q1 = 1e4 / o[2]
    q2 = -2e4 / o[4]
    want = q1 * (o[4] - o[2]) - fee * q1 * o[2] + q2 * (c[5] - o[4]) - fee * abs(q2 - q1) * o[4]
    assert np.isclose(pnl.sum(), want)
    assert pnl[:2].sum() == 0 and expo[1] == 0 and expo[2] > 0   # the decision at bar 1 fills at bar 2's open


def test_proxy_side_reads_only_past_closes():
    df = _bars(80)
    B = 96
    dec = vs.proxy_decisions(df, B)
    tms = np.asarray(data.to_ms(df.index))
    c = df["close"].values
    for i, s in dec[::7]:
        j = int(np.searchsorted(tms, tms[i] - 30 * 86400000, side="right")) - 1
        assert j < i and s == int(np.sign(c[i] / c[j] - 1))
        d2 = df.copy()
        d2.iloc[i + 1:, d2.columns.get_loc("close")] *= 3.0         # change every later close
        assert (i, s) in vs.proxy_decisions(d2, B)


def test_exposure_matching_constant():
    idx = pd.date_range(vs.START, periods=96 * 4, freq="15min", tz="UTC")
    cal = pd.date_range(vs.START, periods=4, freq="D", tz="UTC")
    pnl = np.zeros(len(idx))
    pnl[100] = 50.0
    S = {}
    for a in vs.ASSETS:
        S[a] = {"proxy": dict((v, {"pnl": pnl * (2 if v == "S1" else 1), "expo": np.full(len(idx), vs.CAPITAL * (2 if v == "S1" else 1)),
                                    "w": np.ones(1), "entry_t": None, "fees": None}) for v in vs.VARIANTS)}
    out = vs.summarise(dict((a, idx) for a in vs.ASSETS), S, cal)
    p0, p1 = out["proxy"]["S0"]["all"]["pooled"], out["proxy"]["S1"]["all"]["pooled"]
    assert out["proxy"]["S1"]["all"]["markets"]["BTCUSDT"]["match_k"] == 0.5
    assert p0["return_pct"] == p1["return_pct"] and p0["max_dd_pct"] == p1["max_dd_pct"]
