# -*- coding: utf-8 -*-
"""H47 regime-split study: the regime readings never read the future (truncation on 24h and cash-hours bars), they use
closed daily bars only, R1 equals evidence.py's recipe, and the fade outcome is the mirror of the follow outcome."""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

import regime_split_study as rs  # noqa: E402
import dailybreak_study as db  # noqa: E402
from engine15 import data, indicators as ind  # noqa: E402
from engine15.sources import adr  # noqa: E402


def bars(days=420, seed=11, gaps=False):
    n = 96 * days
    rng = np.random.RandomState(seed)
    drift = np.repeat(rng.normal(0, 0.0015, days // 20 + 1), 96 * 20)[:n]        # trending and flat stretches
    ret = drift + rng.normal(0, 0.003, n) + np.where(rng.rand(n) < 0.01, rng.normal(0, 0.02, n), 0.0)
    c = 100.0 * np.exp(np.cumsum(ret))
    o = np.concatenate([[100.0], c[:-1]])
    sp = np.abs(rng.normal(0, 0.002, n)) * c
    idx = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    df = pd.DataFrame({"open": o, "high": np.maximum(o, c) + sp, "low": np.minimum(o, c) - sp, "close": c,
                       "volume": 1.0, "taker_buy": np.nan}, index=idx)
    if gaps:                                                       # a market that shuts: keep 13:30-20:00 UTC
        m = df.index.hour * 60 + df.index.minute
        df = df[(m >= 810) & (m < 1200)]
    return df


def _same(a, b, k):
    if k == "label":
        return list(a) == list(b)
    fa, fb = np.isfinite(a), np.isfinite(b)
    return np.array_equal(fa, fb) and np.allclose(a[fa], b[fb], rtol=1e-9, atol=1e-12)


def test_regimes_never_read_the_future():
    for gaps in (False, True):
        df = bars(gaps=gaps)
        n = len(df)
        G = rs.regimes(df)
        for k in rs.VALS:
            if k == "label":
                assert any(isinstance(x, str) for x in G[k]), (k, gaps)
            else:
                assert np.isfinite(G[k]).sum() > 1000, (k, gaps)
        for cut in (int(n * 0.7) + 5, int(n * 0.85) + 37, n - 3):
            P = rs.regimes(df.iloc[:cut])
            for k in rs.VALS:
                assert _same(P[k], G[k][:cut], k), (k, gaps, cut)
        tc = rs.truncation_check(df, [int(n * 0.6) + 7, n - 40])
        assert tc["mismatched_arrays"] == 0


def test_closed_daily_bars_only_by_hand():
    """ER at a row = the ratio over the daily closes of days that had CLOSED by the row's close."""
    for gaps in (False, True):
        df = bars(gaps=gaps)
        G = rs.regimes(df)
        d1 = data.resample(df, "1D")["close"]
        close_ms = data.to_ms(df.index) + 900000
        day_end = data.to_ms(d1.index) + 86400000
        rng = np.random.RandomState(3)
        checked = 0
        for i in rng.randint(len(df) // 2, len(df), 60):
            k = int(np.searchsorted(day_end, close_ms[i], side="right"))      # days with end <= row close
            c = d1.values[:k]
            want = abs(c[-1] - c[-21]) / np.abs(np.diff(c[-21:])).sum()
            assert abs(G["er"][i] - want) < 1e-9, (gaps, i)
            assert G["dir20"][i] == np.sign(c[-1] - c[-21])
            lr = np.diff(np.log(c))
            if len(lr) < 250:
                assert not np.isfinite(G["vr"][i])
                continue
            s5 = np.convolve(lr, np.ones(5), "valid")
            vr = np.var(s5[-246:], ddof=1) / (5 * np.var(lr[-250:], ddof=1))
            assert abs(G["vr"][i] - vr) < 1e-9, (gaps, i)
            checked += 1
        assert checked > 20, gaps


def test_label_equals_evidence_recipe():
    for gaps in (False, True):
        df = bars(gaps=gaps)
        assert rs.evidence_label_check(df) == 0
        labs = set(x for x in rs.regimes(df)["label"] if x)
        assert labs <= set(ind.REGIMES) and len(labs) >= 2


def test_fade_is_the_mirror_of_follow():
    df = bars(days=300)
    R = adr.readings(df, box=db.BOX)
    G = rs.regimes(df)
    seen = 0
    for lv in rs.LEVELS:
        for e in rs.events(R, G, lv):
            if e["excluded"]:
                continue
            seen += 1
            if e["hit"] is None:
                assert e["f_hit"] is None
                continue
            assert e["f_hit"] is not None and e["hit"] + e["f_hit"] <= 1
            if not e["ambiguous"]:
                assert e["hit"] + e["f_hit"] == 1
            else:
                assert e["hit"] == 0 and e["f_hit"] == 0
            s, D = e["side"], e["datr"]
            assert abs(e["f_stop"] - (e["entry"] + s * 0.5 * D)) < 1e-9          # fade stop = follow target
            v = rs.side_view(e, "fade")
            assert v["side"] == -s
    assert seen > 100


def test_buckets_aligned_and_counter():
    cut = {"er": (0.2, 0.4), "rvp": (0.33, 0.66), "vr": (0.9, 1.1)}
    B = dict((b[0], b[3]) for b in rs.bucket_defs(cut))
    assert len(B) == rs.N_BUCKETS
    base = {"adx": 30.0, "dip": 5.0, "er": 0.5, "dir20": 1.0, "rvp": 0.1, "vr": 1.5}
    up = dict(base, label="TREND_UP", side=1)
    dn = dict(base, label="TREND_UP", side=-1)
    assert B["R1a"](up) and not B["R1b"](up) and B["R1b"](dn) and B["R1e"](dn)
    assert B["R2b"](up) and B["R2c"](dn) and B["R2a"](dn)
    assert B["R3b"](up) and B["R3c"](dn) and B["R3a"](up)
    assert B["R4c"](up) and B["R5a"](up)
    none = dict(up, label=None, adx=None, er=None)
    assert B["R1e"](none) is None and B["R2a"](none) is None and B["R3a"](none) is None
