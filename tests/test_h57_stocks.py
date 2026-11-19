# -*- coding: utf-8 -*-
"""H57 (research/h57_data.py, research/h57_stocks.py): stock stances on history. Synthetic bars and a synthetic
index model only; nothing is fetched.

    py -3 -m pytest tests/test_h57_stocks.py -q
"""
import lzma
import os
import struct
import sys

import numpy as np
import pandas as pd
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))
sys.path.insert(0, HERE)

import h57_data as hd  # noqa: E402
import h57_stocks as hs  # noqa: E402
from engine15 import data, extdata, labels, model, stocks  # noqa: E402
from engine15.config import CFG, voting_for  # noqa: E402
from engine15.evidence import FEATURES  # noqa: E402


def cash_bars(days, start, seed=1, p0=100.0):
    grid = pd.date_range(start, periods=days * 96, freq="15min", tz="UTC")
    grid = grid[extdata.open_mask("SPX", grid)]
    rng = np.random.RandomState(seed)
    n = len(grid)
    close = p0 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    opn = np.concatenate([[p0], close[:-1]])
    spread = np.abs(rng.normal(0, 0.0015, n)) * close
    df = pd.DataFrame({"open": opn, "high": np.maximum(opn, close) + spread, "low": np.minimum(opn, close) - spread,
                       "close": close, "volume": rng.randint(100, 1000, n).astype(float), "taker_buy": np.nan},
                      index=pd.DatetimeIndex(grid, name="open_time"))
    return df[data.COLS]


# ------------------------------------------------------------------ h57_data pure pieces
def test_instrument_names():
    assert hd.instrument("NVDA") == "NVDAUSUSD"
    assert hd.instrument("BRK.B") == "BRKBUSUSD"
    assert hd.instrument("META") == "FBUSUSD"


def test_decode_drops_flat_filler_and_scales():
    rows = [(0, 100000, 101000, 99000, 102000, 5.0), (60, 101000, 101000, 101000, 101000, 0.0),
            (120, 101000, 100500, 100000, 101500, 2.0)]
    raw = lzma.compress(b"".join(hd.ROW.pack(*r) for r in rows), format=lzma.FORMAT_ALONE)
    out = hd.decode(raw, 1000, 1000)
    assert len(out) == 2
    ts, o, h, lo, c, v = out[0]
    assert (ts, o, h, lo, c, v) == (1000, 100.0, 102.0, 99.0, 101.0, 5.0)
    assert out[1][0] == 1000 + 120000
    assert hd.decode(b"", 0, 1000) == []


def test_bucket_cash15_and_seal():
    idx = pd.date_range("2025-11-07 15:00", periods=60, freq="1min", tz="UTC")       # Friday, in the session (EST)
    m1 = pd.DataFrame({"open": np.arange(60.0) + 1, "high": np.arange(60.0) + 2, "low": np.arange(60.0),
                       "close": np.arange(60.0) + 1.5, "volume": 1.0, "taker_buy": np.nan}, index=idx)
    b = hd.bucket(m1, 15)
    assert len(b) == 4 and b["open"].iloc[0] == 1.0 and b["close"].iloc[0] == 15.5 and b["volume"].iloc[0] == 15
    assert b["high"].iloc[0] == 16.0 and b["low"].iloc[0] == 0.0
    late = m1.copy()
    late.index = late.index + pd.Timedelta(days=4)                                    # Tuesday 2025-11-11: sealed
    assert len(hd.cash15(hd.bucket(late, 15))) == 0
    night = m1.copy()
    night.index = night.index - pd.Timedelta(hours=8)                                 # 07:00 UTC: not cash hours
    assert len(hd.cash15(hd.bucket(night, 15))) == 0
    assert len(hd.cash15(b)) == 4


def test_daily_of_keys_by_new_york_date():
    b = cash_bars(3, "2024-03-04")
    d = hd.daily_of(b)
    assert list(d.index.strftime("%Y-%m-%d")) == ["2024-03-04", "2024-03-05", "2024-03-06"]
    day = b[b.index.normalize() == pd.Timestamp("2024-03-05", tz="UTC")]
    assert d["open"].iloc[1] == day["open"].iloc[0] and d["close"].iloc[1] == day["close"].iloc[-1]
    assert d["high"].iloc[1] == day["high"].max()


def test_split_factors():
    idx = pd.DatetimeIndex(pd.to_datetime(["2024-06-07", "2024-06-10", "2024-06-11"]).tz_localize("UTC"))
    sp = [(pd.Timestamp("2024-06-10", tz="UTC"), 10.0)]
    assert list(hd.split_factors(idx, sp, {})) == [0.1, 1.0, 1.0]
    assert list(hd.split_factors(idx, sp, {sp[0][0]: True})) == [1.0, 1.0, 1.0]


# ------------------------------------------------------------------ measures
def test_wilson_and_non_overlap():
    lo, hi = hs.wilson(60, 100)
    assert abs(lo - 0.5020) < 1e-3 and abs(hi - 0.6906) < 1e-3
    assert hs.wilson(0, 0) == (None, None)
    i = np.array([0, 1, 5, 6, 30, 31])
    res = np.array([5, 3, 26, 2, 1, 1])
    keep = hs.non_overlap(i, res)
    assert list(keep) == [True, False, True, False, False, True]       # 5 >= 0+5; 30 < 5+26; 31 >= 5+26


def test_refit_at_and_month_windows():
    starts = np.array([10, 20, 40])
    assert hs.refit_at(5, starts, 10) == -1
    assert hs.refit_at(10, starts, 10) == 0 and hs.refit_at(19, starts, 10) == 0
    assert hs.refit_at(25, starts, 10) == 1
    assert hs.refit_at(30, starts, 10) == -1                          # a skipped refit: no model there
    assert hs.refit_at(45, starts, 10) == 2
    idx = pd.DatetimeIndex(pd.to_datetime(["2024-01-15", "2024-03-02"]).tz_localize("UTC"))
    w = hs.month_windows(idx)
    assert [str(m)[:10] for m, _, _ in w] == ["2024-01-01", "2024-02-01", "2024-03-01"]
    assert str(w[0][2])[:10] == "2023-11-02"


def test_measure_pass_logic():
    rng = np.random.RandomState(3)
    rows = []
    for t in ("AAA", "BBB"):
        for k in range(400):
            side = "LONG" if k % 2 else "SHORT"
            y = labels.UP if (side == "LONG") == (rng.rand() < 0.8) else labels.DOWN
            rows.append({"ticker": t, "bar_ms": 1600000000000 + k * 900000 * 30, "i": k * 30, "res": 10, "side": side,
                         "y": y, "p_up": 0.5, "p_down": 0.3})
    r = hs.measure(pd.DataFrame(rows), ["AAA", "BBB"])
    assert r["pass"]["PASS"] and r["pooled"]["full"]["nov_graded"] == 800
    for row in rows:                                                   # every call wrong: no pass
        row["y"] = labels.DOWN if row["side"] == "LONG" else labels.UP
    r = hs.measure(pd.DataFrame(rows), ["AAA", "BBB"])
    assert not r["pass"]["PASS"] and r["pooled"]["full"]["nov_hit"] == 0.0


# ------------------------------------------------------------------ no look-ahead: the S&P walk-forward
def _small_cfg():
    cfg = dict(CFG, assets=("SPX",), voting=voting_for("index"))
    cfg.update(horizon=26, refit_every=150, train_days=4000, train_step=4, min_train_rows=60)
    return cfg


def _synthetic_index(n, seed=7):
    rng = np.random.RandomState(seed)
    X = rng.normal(0, 1, (n, len(FEATURES)))
    X[:, rng.rand(len(FEATURES)) < 0.5] = 0.0
    p = 100 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    o = np.concatenate([[100.0], p[:-1]])
    h = np.maximum(o, p) * (1 + np.abs(rng.normal(0, 0.002, n)))
    lo = np.minimum(o, p) * (1 - np.abs(rng.normal(0, 0.002, n)))
    unit = np.full(n, 0.6)
    return X, o, h, lo, unit


def test_walk_model_never_uses_later_rows(tmp_path):
    cfg = _small_cfg()
    n, n1, birth = 1500, 1000, 200
    X, o, h, lo, unit = _synthetic_index(n)
    out = {}
    for name, m in (("full", n), ("cut", n1)):
        y, res = labels.triple_barrier(o[:m], h[:m], lo[:m], unit[:m], cfg["horizon"])   # grades from bars up to m only
        out[name] = hs.walk_model({"SPX": X[:m]}, {"SPX": np.ones(m, bool)}, {"SPX": y}, {"SPX": res}, cfg,
                                  birth, birth, m, str(tmp_path / name))
    s_full, W_full, tr_full = out["full"]
    s_cut, W_cut, tr_cut = out["cut"]
    assert len(s_cut) and set(s_cut) <= set(s_full)
    k = len(s_cut)
    assert list(s_full[:k]) == list(s_cut)
    for v in model.VOICE_NAMES:
        assert np.array_equal(W_full[v][:k], W_cut[v])
    assert np.allclose(tr_full[:n1 - birth], tr_cut, rtol=0, atol=1e-12)
    # changing every row from n1 on changes nothing before n1
    X2 = X.copy()
    X2[n1:] = 9.0
    y, res = labels.triple_barrier(o, h, lo, unit, cfg["horizon"])
    s2, W2, tr2 = hs.walk_model({"SPX": X2}, {"SPX": np.ones(n, bool)}, {"SPX": y}, {"SPX": res}, cfg, birth, birth, n,
                                str(tmp_path / "x2"))
    for v in model.VOICE_NAMES:
        assert np.array_equal(W2[v][:k], W_cut[v])
    assert np.allclose(tr2[:n1 - birth], tr_cut, rtol=0, atol=1e-12)


# ------------------------------------------------------------------ no look-ahead: the stance
def _fake_spx(times_ms, seed=11):
    rng = np.random.RandomState(seed)
    n = len(times_ms)
    W = {}
    k = 4
    for v in model.VOICE_NAMES:
        W[v] = rng.normal(0, 0.05, (k, 2, len(model._COLS[v]) + 1))
    names = hs.market_features()
    trust = rng.rand(n, len(model.VOICE_NAMES))
    trust = trust / trust.sum(axis=1, keepdims=True)
    every = n // k + 1
    return {"times_ms": np.asarray(times_ms), "mk": rng.normal(0, 0.5, (n, len(names))), "mk_names": np.array(names),
            "trust": trust, "birth": np.array(0), "starts": np.arange(k) * every, "every": np.array(every),
            "ready": np.ones(n, bool), "W": W, "pos": dict((int(t), i) for i, t in enumerate(times_ms))}


def test_stance_identical_with_and_without_later_bars():
    pre = cash_bars(500, "2022-08-01", seed=2, p0=60.0)
    b15 = cash_bars(120, "2024-01-01", seed=4, p0=80.0)
    daily = hd.daily_of(pre[pre.index < b15.index[0]])
    spx = _fake_spx(data.to_ms(b15.index))
    at = hs.SpxAt(spx)
    cfg = stocks.index_cfg()
    cut = pd.Timestamp("2024-03-19 17:00", tz="UTC")
    full = hs.stances(b15, daily, "TEST", at, cfg)
    part = hs.stances(b15[b15.index <= cut], daily, "TEST", at, cfg)
    cut_ms = int(cut.timestamp() * 1000)
    a = full[full["bar_ms"] <= cut_ms].reset_index(drop=True)
    b = part.reset_index(drop=True)
    assert len(a) > 500 and len(a) == len(b)
    pd.testing.assert_frame_equal(a, b)
    assert set(full["side"]) <= {"LONG", "SHORT", "FLAT"}


def test_stance_row_matches_stocks_stance():
    """stance_row gives stocks._stance's side and odds for the same readings, trust and refit."""
    pre = cash_bars(400, "2023-01-01", seed=5, p0=40.0)
    b15 = cash_bars(70, "2024-05-01", seed=6, p0=50.0)
    daily = hd.daily_of(pre[pre.index < b15.index[0]])
    spx = _fake_spx(data.to_ms(b15.index))
    at = hs.SpxAt(spx)
    cfg = stocks.index_cfg()
    ms = int(data.to_ms(b15.index[-1:])[0])
    trust, W, feats = at(ms)
    entry = {"time": stocks._close_key(ms), "asset": "SPX", "data": feats,
             "voices": [{"voice": v, "trust": float(trust[k])} for k, v in enumerate(model.VOICE_NAMES)]}
    want, err = stocks._stance("TEST", b15, daily, {entry["time"]: entry}, W, stocks.Paths(), 0.0, cfg)
    assert err is None
    ev = stocks.readings(b15, daily, "TEST")
    got = hs.stance_row(ev.iloc[-1], at(ms), cfg)
    assert got["side"] == want["side"]
    assert abs(got["p_up"] - want["p_up"]) < 6e-4 and abs(got["p_down"] - want["p_down"]) < 6e-4
    assert abs(got["unit"] - want["unit"]) < 1e-9


def test_grade_is_the_engines_triple_barrier():
    b15 = cash_bars(10, "2024-02-05", seed=9)
    st = pd.DataFrame({"bar_ms": data.to_ms(b15.index[[3, 50, 100]]), "unit": [0.5, 0.2, 0.8]})
    g = hs.grade(b15, st)
    for k, (ms, u) in enumerate(zip(st["bar_ms"], st["unit"])):
        assert int(g["y"].iloc[k]) == stocks.grade_one(b15, int(ms), u)
