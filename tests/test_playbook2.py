# -*- coding: utf-8 -*-
"""tests for engine15/playbook2.py: P3 opening range breakout, P4 S&P gap fill, P5 squeeze breakout.

Hand-made bars that fire and do not fire each book; session clocks across daylight saving; the fill
rules (next open, stop first inside one bar, a gap through the stop); fees; one trade at a time; and
that no row changes when later bars are added (no look-ahead)."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import data, extdata  # noqa: E402
from engine15 import playbook2 as pb  # noqa: E402

BAR = pd.Timedelta(minutes=15)


def frame(start, rows):
    """rows: list of (open, high, low, close) or close floats -> 15m frame from `start` (UTC), gapless."""
    rows = [(r, r + 0.05, r - 0.05, r) if np.isscalar(r) else r for r in rows]
    idx = pd.date_range(pd.Timestamp(start, tz="UTC"), periods=len(rows), freq="15min", name="open_time")
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx, dtype=float)
    df["volume"] = 100.0
    df["taker_buy"] = 50.0
    return df


def utc(ms):
    return str(pd.Timestamp(int(ms), unit="ms", tz="UTC"))[:16]


def run_rows(book, df, asset, p, now_ms=None):
    ctx = pb.Ctx(df, asset, now_ms)
    S, T = pb.run(book, ctx, p)
    return ctx, S, T


# ---------------------------------------------------------------- clocks
def _window(kind, day):
    ms = int(pd.Timestamp(day, tz="UTC").value // 10**6)
    st, en = pb.session_windows(kind, ms, ms)
    k = int(np.flatnonzero((st >= ms) & (st < ms + pb.DAY_MS))[0])
    return utc(st[k]), utc(en[k])


def test_sp500_cash_open_follows_new_york_daylight_saving():
    assert _window("ny_cash", "2026-07-15") == ("2026-07-15 13:30", "2026-07-15 20:00")
    assert _window("ny_cash", "2026-01-15") == ("2026-01-15 14:30", "2026-01-15 21:00")
    assert _window("ny_cash", "2026-03-10") == ("2026-03-10 13:30", "2026-03-10 20:00")   # US on summer time, UK not yet
    assert _window("ny_cash", "2026-11-27") == ("2026-11-27 14:30", "2026-11-27 18:00")   # half day: shut at 13:00 New York
    assert _window("us_open", "2026-11-03") == ("2026-11-03 14:30", "2026-11-03 22:30")   # crypto: 8 hours from the US open


def test_london_open_follows_uk_daylight_saving():
    assert _window("london", "2026-07-15") == ("2026-07-15 07:00", "2026-07-15 15:00")
    assert _window("london", "2026-01-15") == ("2026-01-15 08:00", "2026-01-15 16:00")
    assert _window("london", "2026-03-10") == ("2026-03-10 08:00", "2026-03-10 16:00")
    assert _window("london", "2026-10-26") == ("2026-10-26 08:00", "2026-10-26 16:00")    # the Monday after the UK change
    assert _window("tokyo", "2026-07-15") == ("2026-07-15 00:00", "2026-07-15 08:00")


def test_no_session_on_holidays_and_weekends():
    ms = int(pd.Timestamp("2026-11-26", tz="UTC").value // 10**6)               # Thanksgiving: NYSE shut
    st, _en = pb.session_windows("ny_cash", ms, ms)
    assert not ((st >= ms) & (st < ms + pb.DAY_MS)).any()
    st, _en = pb.session_windows("us_open", ms, ms)
    assert not ((st >= ms) & (st < ms + pb.DAY_MS)).any()
    sat = int(pd.Timestamp("2026-11-14", tz="UTC").value // 10**6)
    st, _en = pb.session_windows("london", sat, sat)
    assert not ((st >= sat) & (st < sat + pb.DAY_MS)).any()
    st, _en = pb.session_windows("utc0", sat, sat)
    assert ((st >= sat) & (st < sat + pb.DAY_MS)).sum() == 1                  # crypto trades every day


# ---------------------------------------------------------------- P3 opening range breakout
ORB = {"or_len": 30, "stop": "far", "target": "2R", "filter": None}


def gold_day(after):
    """A winter Wednesday, gold: quiet bars 06:00-08:00 UTC, the London opening range 08:00-08:30 (99-101),
    then `after` (list of bars from 08:30 UTC)."""
    pre = [100.0] * 8
    orr = [(100.0, 101.0, 99.5, 100.5), (100.5, 100.8, 99.0, 100.0)]
    return frame("2026-01-14 06:00", pre + orr + after)


def test_orb_long_breakout_reaches_2r():
    after = [(100.0, 101.6, 99.9, 101.5),          # 08:30 closes above the range: decide
             (101.6, 102.0, 101.4, 101.8),         # 08:45 entry at 101.6
             (101.8, 106.0, 101.7, 105.9)]         # 2R = 101.6 + 2 x 2.6 = 106.8 not yet
    after += [(105.9, 107.0, 105.5, 106.9)] + [106.9] * 4
    ctx, S, T = run_rows("p3_orb", gold_day(after), "XAUUSD", ORB)
    assert len(T["k"]) == 1
    k = T["k"][0]
    assert S["side"][k] == 1 and utc(ctx.ms[S["i"][k]]) == "2026-01-14 08:30"
    assert T["entry"][0] == pytest.approx(101.6) and S["stop"][k] == pytest.approx(99.0)
    assert T["t2"][0] == pytest.approx(101.6 + 2 * 2.6)
    assert pb.WHY[T["why"][0]] == "T2" and T["exit"][0] == pytest.approx(106.8)
    fee = 0.0002
    gross = (106.8 / 101.6 - 1) * 10000
    fees = fee * 10000 * (1 + 106.8 / 101.6)
    assert T["fees"][0] == pytest.approx(fees) and T["pnl"][0] == pytest.approx(gross - fees)
    assert T["r"][0] == pytest.approx((gross - fees) / (10000 * 2.6 / 101.6))


def test_orb_does_not_fire_inside_the_range_and_times_out_at_session_end():
    ctx, S, T = run_rows("p3_orb", gold_day([100.0] * 40), "XAUUSD", ORB)
    assert len(S["i"]) == 0 and len(T["k"]) == 0
    # a breakout that goes nowhere: closed at the close of the last bar before 16:00 London
    after = [(100.0, 101.6, 99.9, 101.5)] + [101.6] * 40
    ctx, S, T = run_rows("p3_orb", gold_day(after), "XAUUSD", ORB)
    assert pb.WHY[T["why"][0]] == "TIME"
    assert utc(T["exit_ms"][0]) == "2026-01-14 16:00"
    assert T["exit"][0] == pytest.approx(101.6)


def test_orb_mid_stop_and_one_r():
    after = [(100.0, 101.6, 99.9, 101.5), (101.6, 101.7, 101.5, 101.6), (101.6, 103.3, 101.5, 103.0)] + [103.0] * 4
    ctx, S, T = run_rows("p3_orb", gold_day(after), "XAUUSD", dict(ORB, stop="mid", target="1R"))
    assert S["stop"][T["k"][0]] == pytest.approx(100.0)
    assert pb.WHY[T["why"][0]] == "T1" and T["exit"][0] == pytest.approx(103.2)


def test_stop_comes_first_when_stop_and_target_share_a_bar():
    after = [(100.0, 101.6, 99.9, 101.5), (101.6, 110.0, 98.0, 101.0)] + [101.0] * 4
    ctx, S, T = run_rows("p3_orb", gold_day(after), "XAUUSD", dict(ORB, target="1R"))
    assert pb.WHY[T["why"][0]] == "STOP" and T["exit"][0] == pytest.approx(99.0)
    assert T["r"][0] < -1.0                                                   # a full loss plus the fees


def test_a_gap_through_the_stop_fills_at_the_open():
    after = [(100.0, 101.6, 99.9, 101.5), (101.6, 101.7, 101.4, 101.5), (97.0, 97.5, 96.5, 97.0)] + [97.0] * 4
    ctx, S, T = run_rows("p3_orb", gold_day(after), "XAUUSD", ORB)
    assert pb.WHY[T["why"][0]] == "STOP" and T["exit"][0] == pytest.approx(97.0)


def test_an_entry_that_opens_beyond_the_stop_is_not_taken():
    after = [(100.0, 101.6, 99.9, 101.5), (98.0, 98.5, 97.5, 98.0)] + [98.0] * 4
    ctx, S, T = run_rows("p3_orb", gold_day(after), "XAUUSD", ORB)
    assert len(S["i"]) == 1 and len(T["k"]) == 0


def test_split_target_moves_the_stop_to_entry_after_t1():
    after = [(100.0, 101.6, 99.9, 101.5), (101.6, 101.7, 101.5, 101.6),
             (101.6, 104.3, 101.5, 104.0),        # T1 104.2 fills
             (104.0, 104.1, 101.0, 101.2)] + [101.2] * 4   # back through the entry: the rest out at 101.6
    ctx, S, T = run_rows("p3_orb", gold_day(after), "XAUUSD", dict(ORB, target="split"))
    assert T["t1_hit"][0] and pb.WHY[T["why"][0]] == "STOP"
    assert T["exit"][0] == pytest.approx((104.2 + 101.6) / 2)


def test_crypto_fee_and_minimum_stop():
    """BTC at 0.10% a side: a stop nearer than 4 fees (0.40%) is not traded."""
    pre = [100.0] * 4
    orr = [(100.0, 100.1, 99.9, 100.0), (100.0, 100.1, 99.95, 100.05)]       # a 0.2% range: too tight
    df = frame("2026-01-14 00:00", orr + [(100.05, 100.2, 100.0, 100.15)] + [100.15] * 40)
    ctx, S, T = run_rows("p3_orb", df, "BTCUSDT", ORB)
    assert len(S["i"]) >= 1 and len(T["k"]) == 0
    orr = [(100.0, 101.0, 99.5, 100.5), (100.5, 100.8, 99.0, 100.0)]
    df = frame("2026-01-14 00:00", orr + [(100.0, 101.6, 99.9, 101.5), (101.6, 101.7, 101.5, 101.6)] + [101.6] * 40)
    ctx, S, T = run_rows("p3_orb", df, "BTCUSDT", ORB)
    assert ctx.fee == 0.001
    j = 0
    exit_ = T["exit"][j]
    assert T["fees"][j] == pytest.approx(0.001 * 10000 * (1 + exit_ / 101.6))
    del pre


# ---------------------------------------------------------------- P4 gap fill (S&P cash hours only)
GAP = {"mode": "fill", "band": ("pct", 0.10, 0.50), "entry": "c15", "target": "full"}


def spx_days(day1, day2):
    """Two winter S&P cash sessions (14:30-21:00 UTC) with the given bars (lists of 26)."""
    a = frame("2026-01-13 14:30", day1)
    b = frame("2026-01-14 14:30", day2)
    return pd.concat([a, b])


def test_gap_fill_fires_and_fills():
    d1 = [100.0] * 26
    d2 = [(100.3, 100.35, 100.15, 100.2),        # gaps up 0.30%, the first bar closes back below the open
          (100.2, 100.25, 100.1, 100.15),         # entry short at 100.2
          (100.15, 100.16, 99.9, 99.95)] + [99.95] * 23
    ctx, S, T = run_rows("p4_gapfill", spx_days(d1, d2), "SPX", GAP)
    assert len(T["k"]) == 1
    k = T["k"][0]
    assert S["side"][k] == -1 and utc(ctx.ms[S["i"][k]]) == "2026-01-14 14:30"
    assert T["entry"][0] == pytest.approx(100.2) and S["stop"][k] == pytest.approx(100.35)
    assert pb.WHY[T["why"][0]] == "T2" and T["exit"][0] == pytest.approx(100.0)
    assert ctx.fee == 0.0002


def test_gap_fill_does_not_fire_when_the_first_bar_extends_or_the_gap_is_out_of_band():
    d1 = [100.0] * 26
    extend = [(100.3, 100.5, 100.28, 100.45)] + [100.45] * 25
    ctx, S, T = run_rows("p4_gapfill", spx_days(d1, extend), "SPX", GAP)
    assert len(S["i"]) == 0
    ctx, S, T = run_rows("p4_gapfill", spx_days(d1, extend), "SPX", dict(GAP, entry="now"))
    assert len(S["i"]) == 1                                                  # "immediately" does not wait for it
    big = [(100.8, 100.85, 100.6, 100.7)] + [100.7] * 25
    ctx, S, T = run_rows("p4_gapfill", spx_days(d1, big), "SPX", GAP)
    assert len(S["i"]) == 0


def test_gap_and_go_trades_with_a_gap_that_holds():
    d1 = [100.0] * 26
    d2 = [(100.3, 100.4, 100.2, 100.35), (100.35, 100.5, 100.3, 100.45), (100.46, 100.5, 100.4, 100.48)] + [100.48] * 23
    ctx, S, T = run_rows("p4_gapfill", spx_days(d1, d2), "SPX", {"mode": "go", "band": ("pct", 0.10, 0.50), "target": "2R"})
    k = T["k"][0]
    assert S["side"][k] == 1 and S["stop"][k] == pytest.approx(100.2)
    assert utc(ctx.ms[S["i"][k] + 1]) == "2026-01-14 15:00"                     # entry at 10:00 New York
    assert pb.WHY[T["why"][0]] == "TIME" and utc(T["exit_ms"][0]) == "2026-01-14 21:00"   # flat by 16:00 New York


def test_spx_orb_uses_the_cash_open_in_both_seasons():
    summer = frame("2026-07-14 13:30", [100.0] * 26)
    winter = frame("2026-01-14 14:30", [100.0] * 26)
    ctx = pb.Ctx(pd.concat([winter, summer]), "SPX")
    E = pb.orb_events(ctx, 15)
    assert [utc(x) for x in E["start"]] == ["2026-01-14 14:30", "2026-07-14 13:30"]


# ---------------------------------------------------------------- P5 squeeze
SQ = {"tf": "15m", "N": 6, "dir": "break", "target": "1R", "hold": 16, "filter": None}


TIGHT = 30
REL = 30 + TIGHT                                                                 # the row of the release bar


def squeeze_bars(release_close=106.0):
    """30 trending bars (closes spread out: no squeeze), 30 bars whose closes stand still inside wide
    ranges (Bollinger inside Keltner: the squeeze is on from the 20th of them), then a release bar."""
    trend = [(80.0 + i, 80.6 + i, 79.6 + i, 80.0 + i) for i in range(30)]
    flat = [(100.0, 100.5, 99.5, 100.0 + (0.01 if i % 2 else -0.01)) for i in range(TIGHT)]
    rel = [(100.0, release_close + 0.2, 99.8, release_close)]
    after = [(release_close, release_close + 0.5, release_close - 0.3, release_close + 0.3)]
    after += [(release_close + 0.3, release_close + 12.0, release_close, release_close + 11.0)] + [release_close + 11.0] * 20
    return frame("2026-01-14 00:00", trend + flat + rel + after)


def test_squeeze_release_breakout_long():
    ctx, S, T = run_rows("p5_squeeze", squeeze_bars(), "BTCUSDT", SQ)
    R = pb.sq_releases(ctx, "15m", 6)
    assert list(R["d"][:1]) == [REL] and R["len"][0] >= 6
    k = T["k"][0]
    assert S["side"][k] == 1
    assert S["i"][k] == REL                                                      # the release bar closed above the range
    assert S["stop"][k] == pytest.approx(99.5)                                   # the squeeze's low
    assert T["entry"][0] == pytest.approx(106.0)
    assert pb.WHY[T["why"][0]] == "T1" and T["exit"][0] == pytest.approx(106.0 + 6.5)


def test_squeeze_does_not_fire_when_too_short_or_no_break():
    ctx, S, T = run_rows("p5_squeeze", squeeze_bars(), "BTCUSDT", dict(SQ, N=60))
    assert len(S["i"]) == 0
    # released by a slow drift that never closes beyond the squeeze's 99.5-100.5: no "break" trade
    trend = [(80.0 + i, 80.6 + i, 79.6 + i, 80.0 + i) for i in range(30)]
    flat = [(100.0, 100.5, 99.5, 100.0 + (0.01 if i % 2 else -0.01)) for i in range(TIGHT)]
    drift = [(x, x + 0.02, x - 0.02, x) for x in np.linspace(99.55, 100.45, 20)]
    ctx, S, T = run_rows("p5_squeeze", frame("2026-01-14 00:00", trend + flat + drift), "BTCUSDT", SQ)
    assert len(pb.sq_releases(ctx, "15m", 6)["d"]) >= 1
    assert len(S["i"]) == 0


def test_squeeze_trade_is_closed_before_a_market_break():
    df = squeeze_bars()
    df = df[df.index <= df.index[REL + 1]]                                       # the market shuts after the entry bar ...
    later = frame(str(df.index[-1] + pd.Timedelta(hours=10))[:16], [106.0] * 10)   # ... and reopens 10 hours later
    ctx, S, T = run_rows("p5_squeeze", pd.concat([df, later]), "XAUUSD", dict(SQ, target="2R"))
    assert pb.WHY[T["why"][0]] == "TIME"
    assert utc(T["exit_ms"][0]) == utc(df.index[REL + 1].value // 10**6 + pb.BAR_MS)
    assert T["exit"][0] == pytest.approx(df["close"].iloc[REL + 1])


# ---------------------------------------------------------------- one at a time, waiting, open
def test_one_open_trade_per_book_per_asset():
    df = gold_day([(100.0, 101.6, 99.9, 101.5)] + [101.6] * 40)
    ctx = pb.Ctx(df, "XAUUSD")
    i = np.array([10, 12])                                                       # the second decided while the first is open
    S = {"i": i, "side": np.array([1, 1]), "stop": np.array([99.0, 99.0]), "t1k": np.zeros(2, int), "t1v": np.ones(2),
         "t2k": np.zeros(2, int), "t2v": np.full(2, 2.0), "mode": np.full(2, pb.M_T2), "last": np.array([40, 40]),
         "done": np.array([True, True]), "can_wait": np.array([False, False]), "ev": np.zeros(2, int), "lab": np.zeros(2, int)}
    T = pb.simulate(ctx, S)
    assert list(T["k"]) == [0]


def test_waiting_then_open_rows():
    after = [(100.0, 101.6, 99.9, 101.5)]
    df = gold_day(after)
    ctx, S, T = run_rows("p3_orb", df, "XAUUSD", ORB)
    assert T["status"][0] == pb.ST_WAIT                                          # decided on the last bar: next open pending
    df = gold_day(after + [(101.6, 102.0, 101.4, 101.8)])
    ctx, S, T = run_rows("p3_orb", df, "XAUUSD", ORB)
    assert T["status"][0] == pb.ST_OPEN and T["entry"][0] == pytest.approx(101.6)


# ---------------------------------------------------------------- no look-ahead
def walk(start, n, seed, asset="BTCUSDT", vol=0.004):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(pd.Timestamp(start, tz="UTC"), periods=n, freq="15min", name="open_time")
    if asset == "SPX":
        idx = idx[extdata.open_mask("SPX", idx)]
    elif asset in ("XAUUSD", "XAGUSD", "USDJPY"):
        idx = idx[extdata.open_mask(asset, idx, calendar=False)]
    m = len(idx)
    jump = np.zeros(m)
    breaks = np.flatnonzero(np.diff(data.to_ms(idx)) > 3 * pb.HOUR_MS) + 1       # the market reopens: an overnight gap
    jump[breaks] = rng.normal(0, 0.004, len(breaks))
    c = 100.0 * np.exp(np.cumsum(rng.normal(0, vol, m) + jump))
    o = np.r_[100.0, c[:-1]] * np.exp(jump + rng.normal(0, vol / 4, m))
    h = np.maximum(o, c) * np.exp(np.abs(rng.normal(0, vol, m)))
    l = np.minimum(o, c) * np.exp(-np.abs(rng.normal(0, vol, m)))
    df = pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": rng.uniform(50, 150, m)}, index=idx)
    df["taker_buy"] = df["volume"] / 2
    return df


def _key(ctx, S, T, j):
    k = T["k"][j]
    return (int(ctx.ms[S["i"][k]]), int(S["side"][k]), round(float(S["stop"][k]), 9))


CASES = [("p3_orb", "BTCUSDT", {"or_len": 15, "stop": "mid", "target": "split", "filter": "narrow"}),
         ("p3_orb", "SPX", {"or_len": 30, "stop": "far", "target": "reach", "filter": "gap"}),
         ("p3_orb", "USDJPY", {"or_len": 30, "stop": "far", "target": "2R", "filter": "htf"}),
         ("p4_gapfill", "SPX", {"mode": "fill", "band": ("atr", 0.25, 1.0), "entry": "now", "target": "split"}),
         ("p4_gapfill", "SPX", {"mode": "go", "band": ("pct", 0.1, 0.5), "target": "1R"}),
         ("p5_squeeze", "ETHUSDT", {"tf": "15m", "N": 6, "dir": "macd", "target": "reach", "hold": 16, "filter": "vol"}),
         ("p5_squeeze", "XAUUSD", {"tf": "1h", "N": 6, "dir": "break", "target": "split", "hold": 32, "filter": "session"})]


@pytest.mark.parametrize("book,asset,p", CASES)
def test_truncated_bars_give_the_same_trades(book, asset, p):
    vol = 0.0015 if asset in ("SPX", "XAUUSD", "USDJPY") else 0.004
    df = walk("2025-10-01", 96 * 200, seed=sum(map(ord, book + asset)), asset=asset, vol=vol)
    full_ctx, fS, fT = run_rows(book, df, asset, p)
    assert len(fT["k"]) > 3, "the case should trade"
    for frac in (0.55, 0.8):
        cut = df.index[int(len(df) * frac)]
        part = df[df.index <= cut]
        ctx, S, T = run_rows(book, part, asset, p)
        cut_close = int(cut.value // 10**6) + pb.BAR_MS
        full = dict((_key(full_ctx, fS, fT, j), j) for j in range(len(fT["k"])))
        for j in range(len(T["k"])):
            if T["status"][j] == pb.ST_WAIT:                                     # its fill is not known yet
                continue
            key = _key(ctx, S, T, j)
            assert key in full, "a trade seen on fewer bars must exist on all bars"
            fj = full[key]
            if T["status"][j] == pb.ST_CLOSED:
                assert fT["status"][fj] == pb.ST_CLOSED
                assert fT["exit"][fj] == pytest.approx(T["exit"][j]) and fT["r"][fj] == pytest.approx(T["r"][j])
                assert T["exit_ms"][j] <= cut_close
        # every full-history trade decided and closed before the cut is also on the shorter history
        mine = set(_key(ctx, S, T, j) for j in range(len(T["k"])))
        for key, fj in full.items():
            if fT["status"][fj] == pb.ST_CLOSED and fT["exit_ms"][fj] <= cut_close - pb.BAR_MS and key[0] + pb.BAR_MS <= cut_close:
                assert key in mine


def test_step_rows_with_now_ms_match_truncated_bars():
    bars = {"BTCUSDT": walk("2026-08-01", 96 * 110, seed=5), "SPX": walk("2026-08-01", 96 * 110, seed=6, asset="SPX", vol=0.0015)}
    now = int(pd.Timestamp("2026-11-16 18:00", tz="UTC").value // 10**6)
    a = pb.step(bars, now_ms=now)
    cut = dict((k, v[v.index + BAR <= pd.Timestamp(now, unit="ms", tz="UTC")]) for k, v in bars.items())
    b = pb.step(cut)
    assert a == b and len(a) > 0
    # a later step never rewrites a trade that had already closed
    later = pb.step(bars, now_ms=now + 2 * pb.DAY_MS)
    seen = dict(((r["book"], r["asset"], r["setup_utc"]), r) for r in later)
    for r in a:
        if r["status"] == "CLOSED":
            assert seen[(r["book"], r["asset"], r["setup_utc"])] == r
    assert all(r["setup_utc"] >= "2026-11-11" for r in a)
    keys = {"book", "asset", "status", "side", "setup_utc", "entry_utc", "entry", "stop", "target_1", "target_2",
            "exit_utc", "exit", "why_out", "r", "pnl_usd", "fees_usd", "text"}
    for r in a:
        assert keys <= set(r)
        assert r["status"] in ("WAITING", "OPEN", "CLOSED") and r["side"] in (1, -1)
        if r["status"] == "CLOSED":
            assert r["why_out"] in ("STOP", "T1", "T2", "TIME")
    blk = pb.page_block(a)
    assert set(blk) == set(pb.BOOKS)
    for b_ in blk.values():
        assert {"title", "hypothesis", "open", "recent", "totals"} <= set(b_)
        assert len(b_["recent"]) <= 5
