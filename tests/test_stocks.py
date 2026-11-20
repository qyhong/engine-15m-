# -*- coding: utf-8 -*-
"""stocks.json (engine15/stocks.py): the S&P 500 model read on single stocks. Synthetic bars, a synthetic index
model (a fits folder and an S&P journal entry made up here), a stand-in Yahoo; nothing real is fetched or read.

    py -3 -m pytest tests/test_stocks.py -q
"""
import json
import math
import os
import re
import socket
import stat
import sys

import numpy as np
import pandas as pd
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import test_step_timing as timing  # noqa: E402
from engine15 import data, export, extdata, labels, live, model, setups, stocks  # noqa: E402
from engine15.config import CFG, voting_for  # noqa: E402
from engine15.evidence import FEATURES  # noqa: E402

DAY0 = "2026-09-01"


# ------------------------------------------------------------------ synthetic material
def cash_bars(days=62, seed=1, start=DAY0, p0=100.0):
    """15m bars inside US cash hours only (extdata.open_mask), a random walk."""
    grid = pd.date_range(start, periods=days * 96, freq="15min", tz="UTC")
    grid = grid[extdata.open_mask("SPX", grid)]
    rng = np.random.RandomState(seed)
    n = len(grid)
    close = p0 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    opn = np.concatenate([[p0], close[:-1]])
    spread = np.abs(rng.normal(0, 0.0015, n)) * close
    vol = rng.uniform(1e5, 3e5, n)
    df = pd.DataFrame({"open": opn, "high": np.maximum(opn, close) + spread, "low": np.minimum(opn, close) - spread,
                       "close": close, "volume": vol, "taker_buy": np.nan}, index=grid)
    df.index.name = "open_time"
    return df


def daily_bars(before, n=330, seed=7, p0=100.0):
    days = pd.bdate_range(end=pd.Timestamp(before).tz_convert("UTC").normalize() - pd.Timedelta(days=1), periods=n, tz="UTC")
    rng = np.random.RandomState(seed)
    close = p0 * np.exp(np.cumsum(rng.normal(0, 0.012, n)))
    close *= p0 / close[-1]
    opn = np.concatenate([[close[0]], close[:-1]]) * (1 + rng.normal(0, 0.002, n))
    hi = np.maximum(opn, close) * (1 + np.abs(rng.normal(0, 0.006, n)))
    lo = np.minimum(opn, close) * (1 - np.abs(rng.normal(0, 0.006, n)))
    df = pd.DataFrame({"open": opn, "high": hi, "low": lo, "close": close, "volume": rng.uniform(2e7, 4e7, n),
                       "taker_buy": np.nan}, index=days)
    df.index.name = "open_time"
    return df


def chart_payload(df, now):
    """Yahoo's chart JSON for these bars plus the live element Yahoo always appends (parse_chart drops it)."""
    ts = [int(t) // 1000 for t in data.to_ms(df.index)]
    ts.append(ts[-1] + 900 if ts else int(now))
    q = dict((k, [float(v) for v in df[k].values] + [None]) for k in ("open", "high", "low", "close", "volume"))
    return {"chart": {"result": [{"meta": {"regularMarketTime": int(now)}, "timestamp": ts, "indicators": {"quote": [q]}}]}}


def daily_payload(df):
    ts = [int(t) // 1000 + 14 * 3600 + 1800 for t in data.to_ms(df.index)]      # Yahoo stamps a day at 09:30 New York
    q = dict((k, [float(v) for v in df[k].values]) for k in ("open", "high", "low", "close", "volume"))
    return {"chart": {"result": [{"meta": {}, "timestamp": ts, "indicators": {"quote": [q]}}]}}


def make_fit(seed=3):
    rng = np.random.RandomState(seed)
    return dict((v, rng.normal(0, 0.08, (2, len(model._COLS[v]) + 1))) for v in model.VOICE_NAMES)


def spx_entry(close_key, raw_fit, seed=5, trust=None):
    """An S&P journal entry as live.step writes one: readings ("data", rounded to 4 decimals), each voice's answer
    (up / down, rounded to 3) from the even-prior fit, and the trust (voting voices only)."""
    rng = np.random.RandomState(seed)
    x = np.round(rng.normal(0, 0.5, len(FEATURES)), 4)
    votes = voting_for("index")
    if trust is None:
        trust = dict((v, 1.0 / len(votes)) for v in votes)
    voices = []
    for v in model.VOICE_NAMES:
        p = model.predict(stocks.even_prior(raw_fit[v]), x[model._COLS[v]][None, :])[0]
        voices.append({"voice": v, "title": model.VOICES[v][0], "up": round(float(p[1]), 3), "down": round(float(p[2]), 3),
                       "trust": round(float(trust.get(v, 0.0)), 3), "pull_pts": 0.0})
    return {"asset": "SPX", "time": close_key, "voices": voices, "data": dict(zip(FEATURES, (float(v) for v in x)))}


def write_fits(fits_dir, raw_fit, name="a" * 32):
    os.makedirs(fits_dir, exist_ok=True)
    np.savez(os.path.join(fits_dir, name + ".npz"), **raw_fit)


class Yahoo:
    """The stand-in feed: bars up to `now`; a ticker in `broken` raises; every request is counted."""

    def __init__(self, bars, daily, now, broken=()):
        self.bars, self.daily, self.now, self.broken = bars, daily, now, set(broken)
        self.calls = []

    def chart(self, symbol, rng):
        self.calls.append(("15m", symbol, rng))
        if symbol in self.broken:
            raise RuntimeError("no answer")
        df = self.bars[symbol]
        return chart_payload(df[df.index + pd.Timedelta(minutes=15) <= pd.Timestamp(self.now, unit="s", tz="UTC")], self.now)

    def day(self, symbol, rng, timeout):
        self.calls.append(("1d", symbol, rng))
        if symbol in self.broken:
            raise RuntimeError("no answer")
        return daily_payload(self.daily[symbol])


@pytest.fixture
def world(tmp_path, monkeypatch):
    """Two tickers, a top5 file, a fits folder, the stand-in feed, all in tmp_path; the network closed."""
    def no_network(*a, **k):
        raise AssertionError("the test tried to open a socket")
    monkeypatch.setattr(socket, "socket", no_network)
    monkeypatch.delenv(stocks.WEB_ENV, raising=False)
    monkeypatch.delenv(stocks.STOCKS_ENV, raising=False)
    bars = {"AAA": cash_bars(seed=1).iloc[:-10], "BBB": cash_bars(seed=2, p0=50.0).iloc[:-10]}     # end mid-session
    daily = dict((t, daily_bars(b.index[0], seed=k + 11, p0=float(b["open"].iloc[0]))) for k, (t, b) in enumerate(bars.items()))
    last = bars["AAA"].index[-1]
    now = (last + pd.Timedelta(minutes=15)).timestamp() + 100
    top5 = tmp_path / "top5.json"
    top5.write_text(json.dumps({"schema": 1, "generated_utc": "2026-11-02T20:07:00Z", "tickers": ["AAA", "BBB"]}))
    monkeypatch.setenv(stocks.TOP5_ENV, str(top5))
    paths = stocks.Paths(data_dir=str(tmp_path / "data"), journal_dir=str(tmp_path / "journal"), out_dir=str(tmp_path / "live"))
    raw = make_fit()
    write_fits(paths.fits, raw)
    feed = Yahoo(bars, daily, now)
    monkeypatch.setattr(extdata, "fetch_chart", feed.chart)
    monkeypatch.setattr(stocks, "_daily_chart", feed.day)
    monkeypatch.setattr(extdata, "YF_PAUSE", 0.0)
    w = type("World", (), {})()
    w.tmp, w.bars, w.daily, w.now, w.top5, w.paths, w.raw, w.feed = tmp_path, bars, daily, now, top5, paths, raw, feed
    w.entry = lambda key, **k: spx_entry(key, raw, **k)
    w.key = stocks._close_key(int(data.to_ms(bars["AAA"].index[-1:])[0]))
    return w


def _doc(info):
    with open(info["path"], encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------ tickers
def test_tickers_file_env_default_and_validation(tmp_path):
    f = tmp_path / "top5.json"
    env = {stocks.TOP5_ENV: str(f)}
    state = {}
    assert stocks.resolve_tickers(state, env) == (list(stocks.DEFAULT), "default", None)       # nothing anywhere
    assert stocks.resolve_tickers({}, dict(env, MIND15_STOCKS="msft, aapl")) == (["MSFT", "AAPL"], "env", None)
    f.write_text(json.dumps({"schema": 1, "generated_utc": "2026-11-17T09:07:00Z",
                             "tickers": ["ddog", "T", "MU", "BRK.B", "ARGX", "NVDA", "AMD"]}))
    got = stocks.resolve_tickers(state, dict(env, MIND15_STOCKS="MSFT"))
    assert got == (["DDOG", "T", "MU", "BRK.B", "ARGX"], "top5.json", "2026-11-17T09:07:00Z")  # file order, at most 5
    assert state["last_list"] == {"tickers": ["DDOG", "T", "MU", "BRK.B", "ARGX"], "generated_utc": "2026-11-17T09:07:00Z"}
    for bad in ("{not json", json.dumps({"tickers": "NVDA"}), json.dumps({"tickers": ["NVDA", "no way!"]}),
                json.dumps({"tickers": ["TOOLONGSYMBOL1"]}), json.dumps(["NVDA"])):
        f.write_text(bad)                                               # malformed: the last list used, with its time
        assert stocks.resolve_tickers(state, dict(env, MIND15_STOCKS="MSFT")) == (
            ["DDOG", "T", "MU", "BRK.B", "ARGX"], "last list", "2026-11-17T09:07:00Z")
    os.remove(str(f))                                                   # missing: the same
    assert stocks.resolve_tickers(state, env)[1] == "last list"
    f.write_text(json.dumps({"generated_utc": "2026-11-18T09:07:00Z", "tickers": []}))         # a thin month: valid
    assert stocks.resolve_tickers(state, env) == ([], "top5.json", "2026-11-18T09:07:00Z")
    assert state["last_list"]["tickers"] == []
    assert stocks.valid_symbol("brk-b") == "BRK-B" and stocks.valid_symbol("A B") is None and stocks.valid_symbol(7) is None
    assert stocks.resolve_tickers({}, {stocks.TOP5_ENV: str(f) + ".missing", "MIND15_STOCKS": "ok,bad sym"})[1] == "default"


def test_empty_list_writes_an_empty_stocks_list(world):
    world.top5.write_text(json.dumps({"generated_utc": "2026-11-18T09:07:00Z", "tickers": []}))
    doc = _doc(stocks.run([], paths=world.paths, now=world.now))
    assert doc["stocks"] == [] and doc["tickers_source"] == "top5.json" and doc["tickers_as_of_utc"] == "2026-11-18T09:07:00Z"
    assert doc["model"] == "S&P 500 model applied to single stocks; not validated on single stocks"
    assert doc["note"] == "Paper model reading. Not a recommendation." and doc["schema"] == 1
    assert world.feed.calls == []


# ------------------------------------------------------------------ readings
def test_readings_never_read_the_future():
    df = cash_bars(days=62, seed=4)
    daily = daily_bars(df.index[0], seed=9)
    full = stocks.readings(df, daily, "AAA")
    entry = {"ec_next": 0.3, "mac_vix": 0.2}
    for cut in (len(df) - 150, len(df) - 37, len(df) - 1):
        part = stocks.readings(df.iloc[:cut], daily, "AAA")
        for k in (cut - 1, cut - 2, cut - 30):
            a = stocks.feature_vector(full.iloc[k], entry)
            b = stocks.feature_vector(part.iloc[k], entry)
            assert np.allclose(a, b, atol=1e-9), "a reading changed when the future was cut at %d (row %d)" % (cut, k)
            for c in stocks.REQUIRED + ["atr1h", "shock", "tide", "htf_bias"]:
                x, y = full[c].iloc[k], part[c].iloc[k]
                assert (x == y) or (pd.isna(x) and pd.isna(y)) or abs(float(x) - float(y)) < 1e-9, (c, k, x, y)


def test_daily_placeholders_keep_the_daily_bars_and_only_agreeing_readings_are_kept():
    df = cash_bars(days=62, seed=4)
    daily = daily_bars(df.index[0], seed=9)
    for two in (False, True):                                          # both shapes give back the daily bars exactly
        ph = stocks.placeholders(daily, df.index[0], two=two)
        assert ph.index.min() >= daily.index.min() and ph.index.max() < df.index[0]
        assert extdata.open_mask("SPX", ph.index, calendar=False).all()
        back = data.resample(ph, "1D")
        assert np.allclose(back[["open", "high", "low", "close"]].values, daily[["open", "high", "low", "close"]].values)
    ev = stocks.readings(df, daily, "AAA")
    row = ev.iloc[-1]
    assert all(isinstance(row[c], str) or np.isfinite(float(row[c])) for c in stocks.REQUIRED)
    real = stocks.evidence_frame(df, "AAA").iloc[-1]
    assert pd.isna(real["tr_1d"]) and np.isfinite(row["tr_1d"])        # the daily trend needs the daily bars
    x = stocks.feature_vector(row, {})
    reading, cards = stocks.reading_cards(x)
    for v in stocks.SKIP_VOICES + stocks.MARKET_VOICES:                # index-only and market-wide: not from the stock
        assert v not in reading
    assert "regime" in reading and "mavg" in reading and len(cards) > 40


def test_market_wide_cards_come_from_the_spx_entry():
    df = cash_bars(days=62, seed=4)
    ev = stocks.readings(df, daily_bars(df.index[0], seed=9), "AAA")
    raw = make_fit()
    e = spx_entry("2026-11-02 21:00", raw)
    x = stocks.feature_vector(ev.iloc[-1], e["data"])
    pos = dict((f, i) for i, f in enumerate(FEATURES))
    for v in stocks.MARKET_VOICES:
        for f in model.VOICES[v][1]:
            assert x[pos[f]] == e["data"][f]
    for v in ("overnight", "putcall", "earnings", "cot", "owner", "kronos", "news"):
        assert not np.abs(x[model._COLS[v]]).any()


# ------------------------------------------------------------------ the index model and the stance
def test_match_fit_finds_the_refit_the_spx_call_used(tmp_path):
    raw, other = make_fit(3), make_fit(4)
    e = spx_entry("2026-11-02 21:00", raw)
    fits = str(tmp_path / "fits")
    write_fits(fits, other, "b" * 32)
    write_fits(fits, raw, "a" * 32)
    os.utime(os.path.join(fits, "b" * 32 + ".npz"), (2e9, 2e9))         # the wrong one is the newest file
    name, W = stocks.match_fit(e, fits)
    assert name == "a" * 32 + ".npz"
    for v in model.VOICE_NAMES:
        assert np.allclose(W[v], stocks.even_prior(raw[v]))
    assert stocks.match_fit(e, str(tmp_path / "none"))[1] is None
    os.remove(os.path.join(fits, "a" * 32 + ".npz"))
    assert stocks.match_fit(e, fits)[1] is None                         # no file gives back the call's answers
    before = sorted(os.listdir(fits))
    stocks.match_fit(e, fits)
    assert sorted(os.listdir(fits)) == before                           # read only


def test_stance_arithmetic_is_the_engines_mix():
    raw = make_fit(3)
    W = dict((v, stocks.even_prior(raw[v])) for v in model.VOICE_NAMES)
    rng = np.random.RandomState(1)
    x = rng.normal(0, 0.5, len(FEATURES))
    silent = model.VOICE_NAMES.index("mavg")
    x[model._COLS["mavg"]] = 0.0                                        # a voice with no reading has no say
    trust = np.zeros(len(model.VOICE_NAMES))
    for v, t in (("mavg", 0.3), ("regime", 0.5), ("levels", 0.1), ("fib", 0.1)):
        trust[model.VOICE_NAMES.index(v)] = t
    odds, w, probs = stocks.stance_odds(x, trust, W)
    assert w[silent] == 0.0
    # by hand: regime 0.5/0.7, levels 0.1/0.7, fib 0.1/0.7 -> regime is above the 40% cap: cut to 0.4, the rest shared
    raw_w = np.array([0.5, 0.1, 0.1]) / 0.7
    capped = model.cap_shares(raw_w[None, :], CFG["trust_cap"])[0]
    assert abs(capped[0] - 0.4) < 1e-12
    idx = [model.VOICE_NAMES.index(v) for v in ("regime", "levels", "fib")]
    assert np.allclose(w[idx], capped) and abs(w.sum() - 1) < 1e-12
    p = np.stack([model.predict(W[v], x[model._COLS[v]][None, :])[0] for v in ("regime", "levels", "fib")])
    assert np.allclose(odds, (capped[:, None] * p).sum(axis=0))
    assert np.allclose(probs[idx], p)


def test_the_entry_bar_is_the_policys():
    cfg = stocks.index_cfg()
    assert cfg["theta_enter"] == 0.05 and cfg["horizon"] == 26

    def odds(score):                                                    # P(up) - P(down) = score points
        return np.array([0.4, 0.3 + score / 200.0, 0.3 - score / 200.0])
    assert stocks.decide(odds(4.9), False, 0.0, 0, False)[0] == "FLAT"
    assert stocks.decide(odds(5.1), False, 0.0, 0, False)[0] == "LONG"
    assert stocks.decide(odds(-5.1), False, 0.0, 0, False)[0] == "SHORT"
    assert stocks.decide(odds(9.0), True, 0.0, 0, False)[0] == "FLAT"       # high risk: 10 points
    assert stocks.decide(odds(10.5), True, 0.0, 0, False)[0] == "LONG"
    assert stocks.decide(odds(12.0), False, 0.0, -1, False)[0] == "FLAT"    # against the higher-timeframe bias: 15
    assert stocks.decide(odds(15.5), False, 0.0, -1, False)[0] == "LONG"
    assert stocks.decide(odds(-6.0), False, 0.0, -1, False)[0] == "SHORT"   # with it: 5
    assert stocks.decide(odds(30.0), False, 0.0, 0, True) == ("FLAT", "release_guard")


def test_reasons():
    W = dict((v, np.zeros((2, len(model._COLS[v]) + 1))) for v in model.VOICE_NAMES)
    probs = np.full((len(model.VOICE_NAMES), 3), 1 / 3.0)
    w = np.zeros(len(model.VOICE_NAMES))
    for v, up in (("mavg", 0.6), ("regime", 0.5), ("fib", 0.45), ("levels", 0.2)):
        k = model.VOICE_NAMES.index(v)
        probs[k] = [1 - up - (0.7 - up), up, 0.7 - up]
        w[k] = 0.25
    r = stocks.reason("LONG", 12.0, w, probs)
    assert r == "Strongest on the long side: Moving averages, Market regime and Fibonacci retracement."
    assert stocks.reason("FLAT", 2.1, w, probs, "no_side_rewarding").startswith("No card leans clearly")
    assert "10-point bar for high risk" in stocks.reason("FLAT", -7.0, w, probs, "no_side_rewarding_high_risk", shock=True)
    assert "15-point" in stocks.reason("FLAT", 8.0, w, probs, "no_side_rewarding")
    assert "release" in stocks.reason("FLAT", 30.0, w, probs, "release_guard")
    for s in (r, stocks.reason("SHORT", -9.0, w, -probs + 2 / 3.0)):
        assert not re.search(r"\bedge\b", s, re.I) and "$" not in s and "kronos" not in s.lower()
    del W


# ------------------------------------------------------------------ grading
def test_grading_is_the_triple_barrier():
    n = 40
    idx = pd.date_range("2026-11-02 14:30", periods=n, freq="15min", tz="UTC")
    flat = pd.DataFrame({"open": 100.0, "high": 100.2, "low": 99.8, "close": 100.0, "volume": 1.0, "taker_buy": np.nan}, index=idx)
    t0 = int(data.to_ms(idx[:1])[0])
    assert stocks.grade_one(flat, t0, 1.0) == labels.NEITHER           # 26 bars, no barrier
    assert stocks.grade_one(flat.iloc[:20], t0, 1.0) == labels.UNKNOWN  # the horizon has not passed
    up = flat.copy()
    up.iloc[5, up.columns.get_loc("high")] = 101.5
    assert stocks.grade_one(up, t0, 1.0) == labels.UP
    assert stocks.grade_one(up.iloc[:7], t0, 1.0) == labels.UP          # known at the first touch
    dn = flat.copy()
    dn.iloc[3, dn.columns.get_loc("low")] = 98.5
    assert stocks.grade_one(dn, t0, 1.0) == labels.DOWN
    late = flat.copy()
    late.iloc[28, late.columns.get_loc("high")] = 105.0                  # after 26 bars: does not count
    assert stocks.grade_one(late, t0, 1.0) == labels.NEITHER
    both = flat.copy()
    both.iloc[4, both.columns.get_loc("high")] = 102.0
    both.iloc[4, both.columns.get_loc("low")] = 98.0
    assert stocks.grade_one(both, t0, 1.0) == labels.NEITHER             # both in one bar: order unknown
    y, _ = labels.triple_barrier(up["open"].values, up["high"].values, up["low"].values, np.full(n, 1.0), 26)
    assert int(y[0]) == stocks.grade_one(up, t0, 1.0)                   # the same as the engine's own call
    rows = {"A|1": {"ticker": "A", "bar_ms": 1, "side": "LONG"}, "A|2": {"ticker": "A", "bar_ms": 2, "side": "SHORT"},
            "A|3": {"ticker": "A", "bar_ms": 3, "side": "LONG"}, "A|4": {"ticker": "A", "bar_ms": 4, "side": "FLAT"},
            "A|5": {"ticker": "A", "bar_ms": 5, "side": "LONG"}}
    rec = stocks._record(rows, {"A|1": labels.UP, "A|2": labels.UP, "A|3": labels.NEITHER, "A|4": labels.DOWN})
    assert rec["graded"] == 2 and rec["hit_pct"] == 50.0 and rec["neither"] == 1
    assert stocks._record({}, {}) == {"graded": 0, "hit_pct": None, "neither": 0, "since_utc": None}


# ------------------------------------------------------------------ the run, end to end
def test_run_writes_a_stance_per_ticker(world):
    info = stocks.run([world.entry(world.key)], paths=world.paths, now=world.now)
    doc = _doc(info)
    assert info["tickers"] == 2 and doc["tickers_source"] == "top5.json" and doc["tickers_as_of_utc"] == "2026-11-02T20:07:00Z"
    assert [s["ticker"] for s in doc["stocks"]] == ["AAA", "BBB"]
    keys = ["ticker", "side", "as_of_utc", "market_open", "price", "price_bar_utc", "score", "p_up", "p_down", "reason",
            "cards_reading", "cards_total", "record", "stale", "error"]
    for s in doc["stocks"]:
        assert all(k in s for k in keys), s
        assert s["side"] in ("LONG", "SHORT", "FLAT") and s["error"] is None and s["stale"] is False and s["market_open"]
        assert abs(s["score"] - round((s["p_up"] - s["p_down"]) * 100, 1)) <= 0.15
        assert s["as_of_utc"] == s["price_bar_utc"] == world.key.replace(" ", "T") + ":00Z"
        assert 0 < s["cards_reading"] < s["cards_total"] and s["record"] == {"graded": 0, "hit_pct": None, "since_utc": s["as_of_utc"]}
        if s["side"] == "FLAT":
            assert s["reason"].startswith("No card leans clearly") or "bar" in s["reason"] or "release" in s["reason"]
        else:
            assert abs(s["score"]) >= 5 and s["reason"].startswith("Strongest on the %s side" % s["side"].lower())
    assert doc["pooled_record"] == {"graded": 0, "hit_pct": None, "since_utc": doc["stocks"][0]["as_of_utc"]}
    # one 60-day 15m request and one daily request per ticker, no more
    assert sorted(world.feed.calls) == [("15m", "AAA", "60d"), ("15m", "BBB", "60d"), ("1d", "AAA", "10y"), ("1d", "BBB", "10y")]
    assert os.path.exists(world.paths.bars15("AAA")) and os.path.exists(world.paths.bars1d("BBB"))
    log = open(world.paths.log, encoding="utf-8").read().splitlines()
    assert len(log) == 2 and json.loads(log[0])["ticker"] == "AAA" and json.loads(log[0])["unit"] > 0


def test_run_is_idempotent_and_restart_safe(world):
    entry = world.entry(world.key)
    first = _doc(stocks.run([entry], paths=world.paths, now=world.now))
    n_calls = len(world.feed.calls)
    again = _doc(stocks.run([entry], paths=world.paths, now=world.now + 30))          # the same close again
    assert [s["side"] for s in again["stocks"]] == [s["side"] for s in first["stocks"]]
    assert [s["score"] for s in again["stocks"]] == [s["score"] for s in first["stocks"]]
    assert len(world.feed.calls) == n_calls                                            # up to date: nothing fetched
    assert len(open(world.paths.log, encoding="utf-8").read().splitlines()) == 2        # no second log line
    with open(world.paths.log, "a", encoding="utf-8") as fh:                            # a crash between log and state:
        fh.write(open(world.paths.log, encoding="utf-8").read().splitlines()[0] + "\n")  # the line twice counts once
    assert len(stocks.read_log(world.paths.log)) == 2
    st = stocks.load_state(world.paths)
    assert st["logged"]["AAA"] == int(data.to_ms(world.bars["AAA"].index[-1:])[0]) and st["model"]["file"].endswith(".npz")
    assert st["last_list"]["tickers"] == ["AAA", "BBB"]


def test_next_close_new_stance_then_graded(world):
    cut = len(world.bars["AAA"]) - 30                                   # start 30 bars back, then step forward
    t_cut = world.bars["AAA"].index[cut - 1]
    now0 = (t_cut + pd.Timedelta(minutes=15)).timestamp() + 100
    world.feed.now = now0
    k0 = stocks._close_key(int(data.to_ms(world.bars["AAA"].index[cut - 1:cut])[0]))
    stocks.run([world.entry(k0)], paths=world.paths, now=now0)
    t_last = world.bars["AAA"].index[-1]
    world.feed.now = world.now
    doc = _doc(stocks.run([world.entry(world.key)], paths=world.paths, now=world.now))
    rows = stocks.read_log(world.paths.log)
    assert len(rows) == 4                                               # two closes x two tickers
    st = stocks.load_state(world.paths)
    for t in ("AAA", "BBB"):
        first = rows["%s|%d" % (t, int(data.to_ms(world.bars[t].index[cut - 1:cut])[0]))]
        y = stocks.grade_one(world.bars[t], first["bar_ms"], first["unit"])
        assert y != labels.UNKNOWN                                        # 29 bars later: decided
        key = "%s|%d" % (t, first["bar_ms"])
        if first["side"] in ("LONG", "SHORT"):
            assert st["grades"][key] == y
            rec = [s for s in doc["stocks"] if s["ticker"] == t][0]["record"]
            assert rec["graded"] == (1 if y in (labels.UP, labels.DOWN) else 0)
        else:
            assert key not in st["grades"]
    assert t_last > t_cut and doc["pooled_record"]["since_utc"] == k0.replace(" ", "T") + ":00Z"
    assert [c for c in world.feed.calls if c[0] == "1d"] == [("1d", "AAA", "10y"), ("1d", "BBB", "10y")]   # once each
    assert [c[2] for c in world.feed.calls if c[0] == "15m"] == ["60d", "60d", "5d", "5d"]


def test_closed_market_keeps_the_last_stance(world):
    first = _doc(stocks.run([world.entry(world.key)], paths=world.paths, now=world.now))        # mid-session
    assert all(s["market_open"] for s in first["stocks"])
    world.feed.bars = {"AAA": cash_bars(seed=1), "BBB": cash_bars(seed=2, p0=50.0)}             # the rest of the day
    last = world.feed.bars["AAA"].index[-1]
    k_close = stocks._close_key(int(data.to_ms(world.feed.bars["AAA"].index[-1:])[0]))
    after = (last + pd.Timedelta(minutes=15)).timestamp() + 60                                  # the step after the close
    world.feed.now = after
    closing = _doc(stocks.run([world.entry(k_close)], paths=world.paths, now=after))
    assert [s["as_of_utc"] for s in closing["stocks"]] == [k_close.replace(" ", "T") + ":00Z"] * 2
    assert all(s["market_open"] is False and s["side"] in ("LONG", "SHORT", "FLAT") for s in closing["stocks"])
    world.feed.calls[:] = []
    world.feed.broken = {"AAA", "BBB"}                                  # any request would fail: none may be made
    sat = pd.Timestamp(k_close, tz="UTC").normalize() + pd.Timedelta(days=(5 - pd.Timestamp(k_close).weekday()) % 7, hours=15)
    assert not extdata.is_open("SPX", sat)
    world.top5.write_text(json.dumps({"generated_utc": "2026-11-07T15:07:00Z", "tickers": ["AAA", "BBB"]}))
    doc = _doc(stocks.run([], paths=world.paths, now=sat.timestamp()))
    assert world.feed.calls == []
    assert doc["tickers_as_of_utc"] == "2026-11-07T15:07:00Z" and doc["market_open"] is False
    for a, b in zip(closing["stocks"], doc["stocks"]):
        assert b["side"] == a["side"] and b["score"] == a["score"] and b["as_of_utc"] == a["as_of_utc"]
        assert b["market_open"] is False and b["stale"] is False and b["error"] is None
    assert len(stocks.read_log(world.paths.log)) == 4                   # no new stance while closed


def test_a_holiday_is_closed_not_stale(world):
    """Thanksgiving (Thursday 26 November 2026) and the Friday after its 13:00 New York early close: the US market
    reads closed (market_calendar), so a last bar hours old is not stale and nothing is fetched again."""
    start = "2026-09-25"
    bars = {"AAA": cash_bars(days=64, seed=1, start=start), "BBB": cash_bars(days=64, seed=2, p0=50.0, start=start)}
    assert bars["AAA"].index[-1] == pd.Timestamp("2026-11-27 17:45", tz="UTC")       # Friday's early close
    for label, end, now in (("thanksgiving", "2026-11-25 20:45", "2026-11-26 19:00"),
                            ("friday", "2026-11-27 17:45", "2026-11-27 21:00")):
        part = dict((t, b[b.index <= pd.Timestamp(end, tz="UTC")]) for t, b in bars.items())
        world.feed.bars = part
        world.feed.daily = dict((t, daily_bars(b.index[0], seed=k + 11, p0=float(b["open"].iloc[0])))
                                for k, (t, b) in enumerate(part.items()))
        t_now = pd.Timestamp(now, tz="UTC").timestamp()
        world.feed.now = t_now
        key = stocks._close_key(int(data.to_ms(part["AAA"].index[-1:])[0]))
        doc = _doc(stocks.run([world.entry(key)], paths=world.paths, now=t_now))
        assert doc["market_open"] is False, label
        for s in doc["stocks"]:
            assert s["market_open"] is False and s["stale"] is False and s["error"] is None, (label, s)
            assert s["as_of_utc"] == key.replace(" ", "T") + ":00Z", label
        n = len(world.feed.calls)
        stocks.run([], paths=world.paths, now=t_now + 3600)                           # an hour later: up to date
        assert len(world.feed.calls) == n, label


def test_a_failing_ticker_is_null_with_a_reason(world):
    world.feed.broken = {"BBB"}
    doc = _doc(stocks.run([world.entry(world.key)], paths=world.paths, now=world.now))
    a, b = doc["stocks"]
    assert a["side"] in ("LONG", "SHORT", "FLAT") and a["error"] is None
    assert b["side"] is None and b["score"] is None and b["stale"] is True and b["price"] is None
    assert b["error"] == "the price feed did not answer (RuntimeError)"
    assert len(stocks.read_log(world.paths.log)) == 1


def test_no_index_model_is_null_with_a_reason(world):
    for f in os.listdir(world.paths.fits):
        os.remove(os.path.join(world.paths.fits, f))
    doc = _doc(stocks.run([world.entry(world.key)], paths=world.paths, now=world.now))
    assert [s["side"] for s in doc["stocks"]] == [None, None]
    assert [s["error"] for s in doc["stocks"]] == ["the S&P 500 model is not available"] * 2
    doc = _doc(stocks.run([], paths=world.paths, now=world.now))         # and no S&P entry for the close
    assert doc["stocks"][0]["error"] == "no S&P 500 reading at this close yet"


def test_spx_entry_from_the_journal(world):
    os.makedirs(world.paths.journal)
    e = world.entry(world.key)
    with open(os.path.join(world.paths.journal, world.key[:10] + ".jsonl"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"asset": "BTCUSDT", "time": world.key}) + "\n" + json.dumps(e) + "\n")
    doc = _doc(stocks.run([], paths=world.paths, now=world.now))
    assert all(s["side"] in ("LONG", "SHORT", "FLAT") for s in doc["stocks"])


def test_web_copy_is_atomic_and_0644(world, monkeypatch):
    web = world.tmp / "www"
    web.mkdir()
    monkeypatch.setenv(stocks.WEB_ENV, str(web))
    calls = []
    real_chmod, real_replace = os.chmod, os.replace
    monkeypatch.setattr(stocks.os, "chmod", lambda p, mode: calls.append(("chmod", p, mode)) or real_chmod(p, mode))
    monkeypatch.setattr(stocks.os, "replace", lambda a, b: calls.append(("replace", a, b)) or real_replace(a, b))
    info = stocks.run([world.entry(world.key)], paths=world.paths, now=world.now)
    target = str(web / "stocks.json")
    assert info["web_path"] == target and stocks.line(info) == "stocks: 2 tickers -> %s (web copy: %s)" % (info["path"], target)
    assert open(info["path"], "rb").read() == open(target, "rb").read()
    assert os.listdir(str(web)) == ["stocks.json"]
    mine = [c for c in calls if c[-1] in (target, target + ".tmp") or c[1] in (target, target + ".tmp")]
    assert mine == [("chmod", target + ".tmp", 0o644), ("replace", target + ".tmp", target)]
    if os.name == "posix":
        assert stat.S_IMODE(os.stat(target).st_mode) == 0o644
    monkeypatch.setenv(stocks.WEB_ENV, str(world.tmp / "no_such_dir"))   # a web copy that fails stops nothing
    lines = []
    info = stocks.run([world.entry(world.key)], paths=world.paths, now=world.now, log=lines.append)
    assert info["web_path"] is None and os.path.exists(info["path"]) and lines[0].startswith("stocks: web copy not written (")


def test_output_has_no_edge_no_model_name_no_nan(world):
    e = world.entry(world.key)
    e["data"]["mac_vix"] = float("nan")
    text = open(stocks.run([e], paths=world.paths, now=world.now)["path"], encoding="utf-8").read()
    assert "NaN" not in text and "Infinity" not in text
    doc = json.loads(text)

    def strings(x):
        if isinstance(x, dict):
            for v in x.values():
                yield from strings(v)
        elif isinstance(x, list):
            for v in x:
                yield from strings(v)
        elif isinstance(x, str):
            yield x
        elif isinstance(x, float):
            assert math.isfinite(x)
    for s in strings(doc):
        assert not re.search(r"\bedge\b", s, re.I) and "kronos" not in s.lower() and "$" not in s, s


def test_earnings_from_the_stored_file_only(world):
    os.makedirs(os.path.dirname(world.paths.earnings))
    with open(world.paths.earnings, "w", encoding="utf-8") as fh:
        fh.write("date,symbol,when,first_seen_ms,last_seen_ms,gone_ms\n2026-08-26,AAA,,1,1,\n"
                 "2026-11-19,AAA,amc,1,1,\n2026-11-04,AAA,bmo,1,1,5\n2026-12-01,AAA,,1,1,\n")
    doc = _doc(stocks.run([world.entry(world.key)], paths=world.paths, now=world.now))
    a, b = doc["stocks"]
    assert a["earnings_utc"] == "2026-11-19T00:00:00Z" and a["earnings_session"] == "after the close"
    assert b["earnings_utc"] is None and b["earnings_session"] is None


# ------------------------------------------------------------------ the live step's hook
def _hook_step(monkeypatch, tmp_path, spx=True):
    calls, lines = [], []
    timing._stand_ins(monkeypatch, tmp_path, calls)
    monkeypatch.setattr(stocks, "JOURNAL_DIR", str(tmp_path / "journal"))      # (the data folder: live.STATE's)
    monkeypatch.setattr(setups, "write", lambda page, out_dir=None, log=print: {"markets": 8, "path": "x"})

    def step_group(g, assets, state, log=print, fetch=True):
        calls.append("group " + g)
        if g != "crypto":
            return None
        rows = [{"asset": a} for a in assets] + ([{"asset": "SPX", "time": "2026-11-02 21:00"}] if spx else [])
        return rows, "page.json"
    monkeypatch.setattr(live, "step_group", step_group)
    return calls, lines


def test_hook_runs_after_setups_and_before_the_push(monkeypatch, tmp_path):
    calls, lines = _hook_step(monkeypatch, tmp_path)
    seen = []
    monkeypatch.setattr(stocks, "run", lambda out, **k: seen.append((out, k)) or {"tickers": 5, "path": "P", "web_path": None})
    live.step(log=lines.append, fetch=True)
    assert len(seen) == 1 and seen[0][0][-1]["asset"] == "SPX" and seen[0][1]["paths"].out == str(tmp_path / "live")
    assert seen[0][1]["paths"].data == str(tmp_path)                    # beside the (stand-in) live state, never data/
    mine = [x for x in lines if x.startswith("stocks:")]
    assert mine == ["stocks: 5 tickers -> P"]
    assert lines.index("setups: 8 markets -> x") < lines.index(mine[0]) < lines.index("web push: ok (a stand-in, nothing sent)")


def test_hook_skips_without_a_new_spx_close(monkeypatch, tmp_path):
    calls, lines = _hook_step(monkeypatch, tmp_path, spx=False)
    monkeypatch.setattr(stocks, "run", lambda *a, **k: 1 / 0)
    live.step(log=lines.append, fetch=True)
    assert [x for x in lines if x.startswith("stocks:")] == []          # no pass ever: nothing to do, nothing to say
    st = tmp_path / "stocks_state.json"                                 # an earlier pass with the same list: skipped
    st.write_text(json.dumps({"last_used": {"tickers": list(stocks.DEFAULT), "source": "default", "as_of": None}}))
    monkeypatch.setenv(stocks.TOP5_ENV, str(tmp_path / "missing.json"))
    monkeypatch.delenv(stocks.STOCKS_ENV, raising=False)
    del lines[:]
    live.step(log=lines.append, fetch=True)
    assert [x for x in lines if x.startswith("stocks:")] == ["stocks: skipped (no new S&P 500 close and the list is unchanged)"]
    monkeypatch.setenv(stocks.STOCKS_ENV, "MSFT")                       # the list changed: it runs (and here fails)
    del lines[:]
    out = live.step(log=lines.append, fetch=True)
    assert [x for x in lines if x.startswith("stocks:")] == ["stocks: not written (ZeroDivisionError('division by zero'))"]
    assert out and lines[-1].startswith("step done in ") and "web push: ok (a stand-in, nothing sent)" in lines


def test_an_exception_in_stocks_never_breaks_the_step(monkeypatch, tmp_path):
    calls, lines = _hook_step(monkeypatch, tmp_path)

    def boom(*a, **k):
        raise RuntimeError("stocks is broken today")
    monkeypatch.setattr(stocks, "maybe_run", boom)
    out = live.step(log=lines.append, fetch=True)
    assert out == [{"asset": "AAA"}, {"asset": "BBB"}, {"asset": "SPX", "time": "2026-11-02 21:00"}]
    assert [x for x in lines if x.startswith("stocks:")] == ["stocks: not written (RuntimeError('stocks is broken today'))"]
    assert calls.count("push") == 1 and lines[-1].startswith("step done in ") and lines[-2].startswith("timing step: ")
    assert not os.path.exists(str(tmp_path / "live" / "stocks.json"))


def test_stocks_is_on_the_step_clock(monkeypatch, tmp_path):
    calls, lines = _hook_step(monkeypatch, tmp_path)

    def slow(out, **k):
        import time
        time.sleep(0.12)
        return {"tickers": 0, "path": "P", "web_path": None}
    monkeypatch.setattr(stocks, "run", slow)
    live.step(log=lines.append, fetch=True)
    t = [x for x in lines if x.startswith("timing step: ")]
    assert len(t) == 1 and " | stocks 0." in t[0], t


def test_the_hook_touches_none_of_the_engines_files(monkeypatch, tmp_path):
    """The stocks pass writes only its own files: data/stocks*, out/live/stocks.json."""
    world_dir = tmp_path / "w"
    calls, lines = _hook_step(monkeypatch, tmp_path)
    seen = []
    monkeypatch.setattr(stocks, "run", lambda out, **k: seen.append(k["paths"]) or {"tickers": 0, "path": "P"})
    live.step(log=lines.append, fetch=True)
    p = seen[0]
    for f in (p.state, p.log, p.bars15("X"), p.bars1d("X")):
        assert os.path.basename(f).startswith("stocks") or os.path.basename(os.path.dirname(f)) == "stocks"
    assert p.fits.endswith(os.path.join("evcache", "index", "fits")) and not world_dir.exists()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
