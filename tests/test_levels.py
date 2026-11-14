# -*- coding: utf-8 -*-
"""Tests of engine15.levels (support and resistance). No network. Run from the project folder:
    py -3 -m pytest tests/test_levels.py -q
Tests on real bars read data/btcusdt_15m.csv and skip cleanly when it is missing or unreadable.
"""
import os
import sys
import time

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine15 import levels  # noqa: E402

BTC_CSV = os.path.join(ROOT, "data", "btcusdt_15m.csv")
COLS = ["open", "high", "low", "close", "volume"]


# ------------------------------------------------------------------ fixtures
def synth(n, seed=0, start=30000.0, t0="2021-01-04"):
    """A fat-tailed random walk in 15m bars (no structure: a test of mechanics, not of markets)."""
    rng = np.random.default_rng(seed)
    c = start * np.exp(np.cumsum(rng.standard_t(4, n) * 0.002))
    o = np.concatenate([[start], c[:-1]])
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.001, n)))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.001, n)))
    idx = pd.date_range(t0, periods=n, freq="15min", tz="UTC")
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": rng.lognormal(3, 0.6, n)}, index=idx)


def real_bars(tail=None):
    if not os.path.exists(BTC_CSV):
        pytest.skip("data/btcusdt_15m.csv is missing")
    try:
        df = pd.read_csv(BTC_CSV)
        df.index = pd.to_datetime(df.pop("ts_ms"), unit="ms", utc=True)
        df = df[COLS].astype(float)
    except Exception as exc:                                      # being rewritten, or not the expected file
        pytest.skip("data/btcusdt_15m.csv is not readable: %s" % exc)
    if len(df) < 5000 or df.index[0].year < 2015 or not df.index.is_monotonic_increasing or df.index.has_duplicates:
        pytest.skip("data/btcusdt_15m.csv is not a clean 15m history")
    return df if tail is None else df.iloc[-tail:]


def assert_prefix_identical(df, cuts):
    """THE ACCEPTANCE BAR: build on the whole frame and on the frame cut at each point; every
    row before the cut must be identical in both (NaN == NaN, exact floats, same text)."""
    full = levels.build(df)
    assert full.index.equals(df.index)
    for cut in cuts:
        part = levels.build(df.iloc[:cut])
        pd.testing.assert_frame_equal(full.iloc[:cut], part, check_exact=True, obj="cut at row %d" % cut)


# ------------------------------------------------------------------ 1. no look-ahead
def test_no_lookahead():
    df = synth(6000, seed=1)
    # cuts inside an hour, inside a day, on a day boundary (row 96 x k closes a UTC day), inside a week
    assert_prefix_identical(df, [397, 1000, 1001, 1002, 1003, 2880, 2881, 3555, 4999, 5999])
    gappy = synth(6000, seed=2).drop(index=synth(6000, seed=2).index[[700, 701, 702, 2500] + list(range(3000, 3130))])
    assert_prefix_identical(gappy, [650, 703, 2499, 2999, 3001, 3200, 5000])


def test_no_lookahead_real_bars():
    df = real_bars(tail=30000)
    assert_prefix_identical(df, [5000, 12345, 20001, 29000, 29999])


def test_swing_known_only_after_k_bars():
    """A swing needs k bars on each side, so it may enter the level set only k bars after it
    formed -- at every swing size, and never when fewer than k later bars exist."""
    n, at = 700, 300
    close = np.full(n, 103.70) + 0.01 * np.sin(np.arange(n))      # a quiet tape ...
    high, low = close + 0.3, close - 0.3
    low[at] = 102.40                                              # ... with one deep wick
    ok = np.ones(n, dtype=bool)
    rows, src, is_high, degree, _ = levels._swing_events(high, low, ok)
    known = dict((d, r) for r, s, h, d in zip(rows, src, is_high, degree) if s == at and not h)
    assert known == dict((d, at + k) for d, k in enumerate(levels.SWING_K))
    assert all(r - s == levels.SWING_K[d] for r, s, d in zip(rows, src, degree))
    for d, k in enumerate(levels.SWING_K):                        # cut one bar short of confirmation: unknown
        short = levels._swing_events(high[:at + k], low[:at + k], ok[:at + k])
        assert not [1 for s, dd in zip(short[1], short[3]) if s == at and dd == d]


# ------------------------------------------------------------------ 2. a planted level
def planted():
    """A triangle wave that bounces off 103.40 every 12 hours, then closes down through it,
    rallies back to it from below and fails there."""
    wick, lo_c, amp, per = 0.05, 103.45, 1.5, 48
    tri = lambda i: 1.0 - abs(((i + 25) % per) - per / 2.0) / (per / 2.0)     # 0 at a trough, 1 at a peak
    closes = [lo_c + amp * tri(i) for i in range(1, 600)]
    troughs = [i for i in range(len(closes)) if abs(closes[i] - lo_c) < 1e-9]
    last = troughs[-1]
    closes = closes[:last + 1]
    closes += [lo_c - 0.15 * s for s in range(1, 13)]             # the break: 12 bars straight down
    closes += [closes[-1]] * 30                                   # a pause, a new day
    closes += list(np.linspace(closes[-1], 103.25, 20))           # back up under the old support ...
    closes += list(np.linspace(103.25, 101.0, 30))                # ... and away again
    c = np.array(closes)
    o = np.concatenate([[c[0]], c[:-1]])
    df = pd.DataFrame({"open": o, "high": np.maximum(o, c) + wick, "low": np.minimum(o, c) - wick, "close": c,
                       "volume": 10.0}, index=pd.date_range("2021-01-04", periods=len(c), freq="15min", tz="UTC"))
    return df, troughs, last


def test_planted_support_strengthens_breaks_and_flips():
    df, troughs, last = planted()
    level = 103.40
    out = levels.build(df, _check=True)
    tol = levels.ZONE_HALF_ATR * out["sr_atr1h"]

    # each bounce is read 12 bars later (its swing is confirmed after 10): same price, more touches, more strength
    reads = out.iloc[[t + 12 for t in troughs if t + 12 < last]]
    reads = reads[reads["sup_px"].notna()]
    assert len(reads) >= 5
    assert (np.abs(reads["sup_px"] - level) <= tol.loc[reads.index]).all(), reads["sup_px"]
    assert reads["sup_kind"].str.contains("pivot zone").all(), reads["sup_kind"].tolist()
    touches, strength = reads["sup_touches"].values, reads["sup_str"].values
    assert (np.diff(touches) >= 0).all() and touches[0] >= 1 and touches[-1] >= levels.TOUCH_FULL, touches
    assert (np.diff(strength[:4]) > 0).all(), strength
    assert strength[-1] >= levels.STRONG and (reads["sr_sup_str"].values == strength).all()
    bounce = out["sr_reject"].iloc[[t + 2 for t in troughs[3:-1]]]  # two bars off the level, before the swing is known
    assert (bounce >= levels.MIN_STRENGTH).all(), "a bounce off a known support reads as a positive rejection"
    named = out["sr_event"].iloc[[t + 2 for t in troughs[3:-1]]][(bounce >= levels.STRONG).values]
    assert len(named) >= 3 and named.str.startswith("bounced off 103.4").all()    # the journal names strong ones

    # the first close below the zone is a break of support: negative, named in the journal
    brk = last + 1
    assert df["close"].iloc[brk] < level - levels.BREAK_ATR * out["sr_atr1h"].iloc[brk]
    assert out["sr_break"].iloc[brk] <= -levels.MIN_STRENGTH and abs(out["sr_break"].iloc[last]) < 0.1
    assert "broke below" in out["sr_event"].iloc[brk]
    assert abs(out["sr_break"].iloc[brk + 8]) < abs(out["sr_break"].iloc[brk]) / 3.0, "the event fades"

    # role reversal: from below, the same price is now resistance, labelled as a flipped zone
    after = out.iloc[brk + 12 + 30: brk + 12 + 30 + 20]           # the rally back under the level
    near = after[np.abs(after["res_px"] - level) <= tol.loc[after.index]]
    assert len(near) >= 5, after[["res_px", "res_kind"]]
    assert near["res_kind"].str.contains("flipped zone").all(), near["res_kind"].tolist()
    assert (out["sup_px"].iloc[brk + 1:].dropna() < level - 0.2).all(), "it is no longer support"
    text = levels.describe(near.iloc[-1])
    assert "resistance 103.4" in text and "flipped zone" in text and text.endswith(".")


# ------------------------------------------------------------------ 3. output contract
def check_contract(df, out):
    assert out.index.equals(df.index) and len(out) == len(df)
    assert set(levels.FEATURES) <= set(out.columns) and set(levels.READS) <= set(out.columns)
    assert not set(levels.FEATURES) & set(levels.READS)
    f = out[levels.FEATURES]
    assert all(str(t) == "float64" for t in f.dtypes)
    assert not f.isna().any().any() and np.isfinite(f.values).all()
    assert (f.values >= -1.0).all() and (f.values <= 1.0).all()
    for col in ("sr_sup_near", "sr_res_near", "sr_sup_str", "sr_res_str", "sr_pdh_near", "sr_pdl_near", "sr_round_near"):
        assert (out[col] >= 0.0).all(), col
    has_s, has_r = out["sup_px"].notna(), out["res_px"].notna()
    assert (out.loc[has_s, "sup_px"] < df.loc[has_s, "close"]).all()       # support is below the close ...
    assert (out.loc[has_r, "res_px"] >= df.loc[has_r, "close"]).all()      # ... resistance at or above it
    assert (out.loc[has_s, "sup_str"] >= levels.MIN_STRENGTH).all() and (out.loc[~has_s, "sup_str"] == 0).all()
    assert (out.loc[has_r, "res_str"] >= levels.MIN_STRENGTH).all() and (out.loc[~has_r, "res_str"] == 0).all()
    assert (out.loc[has_s, "sup_dist_atr"] <= levels.SEARCH_ATR + 1e-9).all()
    assert (out.loc[has_s, "sup_kind"] != "").all() and (out.loc[~has_s, "sup_kind"] == "").all()
    warm = out.iloc[2000:]                                        # after warm-up the module does read
    assert has_s.iloc[2000:].mean() > 0.5 and has_r.iloc[2000:].mean() > 0.5
    assert warm[levels.FEATURES].std().min() > 0.01, "no feature may be dead"
    for i in (0, 50, len(out) // 2, len(out) - 1):                # describe() never fails, warm or not
        text = levels.describe(out.iloc[i])
        assert isinstance(text, str) and text.endswith(".") and "nan" not in text.lower()


def test_output_contract():
    df = synth(8000, seed=3)
    out = levels.build(df, _check=True)                           # _check: the live list's bookkeeping holds
    check_contract(df, out)
    assert (out[levels.FEATURES].iloc[:40] == 0.0).all().all(), "before the hourly ATR exists: no read = 0.0"
    assert out["sup_px"].iloc[:40].isna().all()


def test_output_contract_real_bars():
    df = real_bars(tail=30000)
    check_contract(df, levels.build(df, _check=True))


def test_prior_day_levels_only_after_the_day_closed():
    df = synth(96 * 12, seed=4)                                   # starts 00:00 UTC: 96 bars = one UTC day
    out = levels.build(df)
    day = df.resample("1D").agg({"high": "max", "low": "min", "close": "last"})
    for k in (3, 7):                                              # the bars of day k
        rows = out.iloc[96 * k: 96 * (k + 1)]
        assert (rows["pd_high"].iloc[:-1] == day["high"].iloc[k - 1]).all()   # all but the last bar: day k-1
        assert rows["pd_high"].iloc[-1] == day["high"].iloc[k]                # the 23:45 bar's close ends day k
        assert rows["pd_low"].iloc[-2] == day["low"].iloc[k - 1] and rows["pd_close"].iloc[-1] == day["close"].iloc[k]
    week1 = df.iloc[:96 * 7]                                      # 2021-01-04 is a Monday
    assert out["pw_high"].iloc[:96 * 7 - 1].isna().all()
    assert out["pw_high"].iloc[96 * 7 - 1] == week1["high"].max() and out["pw_low"].iloc[96 * 8] == week1["low"].min()


def test_round_grid():
    step, idx, mant = levels._round_grid(np.array([74321.0, 40100.0, 20000.0, 3700.0, 0.5]))
    assert step.tolist() == [1000.0, 500.0, 250.0, 50.0, 0.01]
    assert (idx * step).tolist() == [74000.0, 40000.0, 20000.0, 3700.0, 0.5]


# ------------------------------------------------------------------ 4. speed guard
def test_speed_guard():
    """30,000 bars in under 6 seconds is the same pace as the full 275,000-bar history in under
    a minute (measured: well under a second here; the loop is linear in bars)."""
    df = synth(30000, seed=5)
    t0 = time.perf_counter()
    levels.build(df)
    assert time.perf_counter() - t0 < 6.0
