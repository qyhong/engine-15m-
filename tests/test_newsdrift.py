# -*- coding: utf-8 -*-
"""H50 post-news drift study: the release event (C0, Ck, impulse, daily ATR, side) never reads bars after bar k,
needs every bar from T - 15 min to the entry bar on file, and the bracket outcome / trade keep the registered frame."""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

import newsdrift_study as nd  # noqa: E402
from engine15 import data  # noqa: E402
from engine15.sources import adr  # noqa: E402


def bars(n=96 * 60, seed=7, cash=False):
    rng = np.random.RandomState(seed)
    ret = rng.normal(0, 0.003, n) + np.where(rng.rand(n) < 0.02, rng.normal(0, 0.02, n), 0.0)
    c = 100.0 * np.exp(np.cumsum(ret))
    o = np.concatenate([[100.0], c[:-1]])
    sp = np.abs(rng.normal(0, 0.002, n)) * c
    idx = pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC")
    df = pd.DataFrame({"open": o, "high": np.maximum(o, c) + sp, "low": np.minimum(o, c) - sp, "close": c,
                       "volume": 1.0, "taker_buy": np.nan}, index=idx)
    if cash:                                                       # a cash session 14:30-21:00 UTC
        m = df.index.hour * 60 + df.index.minute
        df = df[(m >= 870) & (m < 1260)]
    return df


def releases(days=60):
    """13:30 UTC every day (CPI-like) and 19:00 UTC every third day (FOMC-like)."""
    rows = []
    base = pd.Timestamp("2025-01-01", tz="UTC")
    for d in range(days):
        t = base + pd.Timedelta(days=d)
        rows.append({"ts_ms": int((t + pd.Timedelta(hours=13, minutes=30)).value // 10**6), "type": "CPI", "kinds": "CPI",
                     "titles": "", "irregular": False, "coreleased": ""})
        if d % 3 == 0:
            rows.append({"ts_ms": int((t + pd.Timedelta(hours=19)).value // 10**6), "type": "FOMC", "kinds": "FOMC",
                         "titles": "", "irregular": False, "coreleased": ""})
    return pd.DataFrame(rows)


def _R(df):
    return adr.readings(df, box=96)


def test_events_never_read_the_future():
    rel = releases()
    for cash in (False, True):
        df = bars(cash=cash)
        n = len(df)
        full_R = _R(df)
        for k in nd.KS:
            full = nd.release_events(full_R, rel, k)
            fk = nd.event_key(full)
            assert len(fk) > 10, (cash, k)
            for cut in list(range(int(n * 0.5), int(n * 0.5) + 100)) + [n - 2, n - 1]:
                part = nd.event_key(nd.release_events(_R(df.iloc[:cut]), rel, k), cut)
                assert part == nd.event_key(full, cut), (cash, k, cut)


def test_changing_bars_after_bar_k_changes_nothing():
    rel = releases()
    df = bars()
    R = _R(df)
    for k in nd.KS:
        for ev in [e for e in nd.release_events(R, rel, k) if e["status"] == "ok"][5:12]:
            d2 = df.copy()
            j = ev["i"] + 1
            d2.iloc[j:, :4] = d2.iloc[j:, :4].values * 1.37        # every bar after bar k scaled
            ev2 = [e for e in nd.release_events(_R(d2), rel, k) if e["T"] == ev["T"]][0]
            for key in ("i0", "i", "e", "c0", "ck", "D", "imp", "side", "a15"):
                assert ev2[key] == ev[key], (k, key)


def test_event_by_hand():
    rel = releases()
    df = bars()
    R = _R(df)
    ms = data.to_ms(df.index)
    for k in nd.KS:
        for ev in nd.release_events(R, rel, k):
            if ev["status"] != "ok":
                continue
            T = ev["T"]
            i0 = int(np.flatnonzero(ms == T - nd.BAR_MS)[0])
            assert ev["i0"] == i0 and ev["i"] == i0 + k and ev["e"] == i0 + k + 1
            assert ms[ev["i"]] == T + (k - 1) * nd.BAR_MS         # bar k opens 15(k-1) min after T, closes 15k after
            c0, ck = df["close"].iloc[i0], df["close"].iloc[i0 + k]
            assert ev["c0"] == c0 and ev["ck"] == ck
            assert abs(ev["imp"] - (ck - c0) / R["datr"][i0 + k]) < 1e-12
            assert ev["side"] == np.sign(ck - c0)


def test_closed_market_and_gaps_drop_the_release():
    rel = releases()
    df = bars(cash=True)                                           # 13:30 UTC is before the 14:30 open
    R = _R(df)
    evs = nd.release_events(R, rel, 1)
    assert all(e["status"] == "closed" for e in evs if e["type"] == "CPI")
    assert any(e["status"] == "ok" for e in evs if e["type"] == "FOMC")
    full = bars()
    T = int(rel["ts_ms"].iloc[20])
    drop = full.index[data.to_ms(full.index) == T + nd.BAR_MS]     # bar 2 after the release missing
    g = full.drop(drop)
    e1 = [e for e in nd.release_events(_R(g), rel, 1) if e["T"] == T][0]
    e4 = [e for e in nd.release_events(_R(g), rel, 4) if e["T"] == T][0]
    assert e1["status"] == "closed"                                # entry bar (k=1) missing
    assert e4["status"] == "closed"                                # a bar inside the 60 min window missing


def test_outcome_and_trade_by_hand():
    """A hand-made path: flat, then a release bar up, then a slow climb. WITH long wins, FADE short loses."""
    n = 96 * 30
    idx = pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC")
    rng = np.random.RandomState(3)
    c = 100.0 + np.cumsum(rng.normal(0, 0.05, n))
    o = np.r_[c[0], c[:-1]]
    df = pd.DataFrame({"open": o, "high": np.maximum(o, c) + 0.02, "low": np.minimum(o, c) - 0.02, "close": c,
                       "volume": 1.0, "taker_buy": np.nan}, index=idx)
    day = 20
    T = pd.Timestamp("2025-01-01", tz="UTC") + pd.Timedelta(days=day, hours=13, minutes=30)
    ms = data.to_ms(idx)
    iT = int(np.flatnonzero(ms == int(T.value // 10**6))[0])
    base = df["close"].iloc[iT - 1]
    path = np.r_[base + 3.0, base + 3.0 + 0.1 * np.arange(1, n - iT)]
    df.iloc[iT:, df.columns.get_loc("close")] = path
    df.iloc[iT:, df.columns.get_loc("open")] = np.r_[base, path[:-1]]
    df["high"] = np.maximum(df["open"], df["close"]) + 0.02
    df["low"] = np.minimum(df["open"], df["close"]) - 0.02
    rel = pd.DataFrame([{"ts_ms": int(T.value // 10**6), "type": "CPI", "kinds": "CPI", "titles": "", "irregular": False,
                         "coreleased": ""}])
    R = _R(df)
    ev = [e for e in nd.release_events(R, rel, 1) if e["status"] == "ok"][0]
    assert ev["side"] == 1 and ev["imp"] > 0
    rows = nd.rows_of(R, [ev], "TEST", 0.001, 0, int(pd.Timestamp("2026-01-01", tz="UTC").value // 10**6))
    r = rows[0]
    assert r["with_day"] == 1 and r["fade_day"] == 0
    tw, tf = r["with_trade"], r["fade_trade"]
    assert tw["why_out"] == "TARGET" and abs(tw["exit"] - (tw["entry"] + 0.5 * ev["D"])) < 1e-9
    assert tf["why_out"] == "STOP" and tf["pnl_usd"] < 0
    assert tw["entry"] == df["open"].iloc[ev["e"]]
    assert r["drift_day"] > 0
    # one position per market: a second row entering while the first trade is open is skipped
    r2 = dict(r, entry_ms=r["entry_ms"] + nd.BAR_MS, e=r["e"] + 1)
    assert len(nd.trades_of([r, r2], "with")) == 1


def test_load_releases_groups_minutes():
    hist = pd.DataFrame([
        {"ts_ms": 1000 * 900, "title": "CPI x", "country": "USD", "impact": "High", "forecast": "", "previous": "",
         "kind": "CPI", "source": "official:alfred"},
        {"ts_ms": 1000 * 900, "title": "Retail", "country": "USD", "impact": "High", "forecast": "", "previous": "",
         "kind": "RETAIL", "source": "official:census"},
        {"ts_ms": 2000 * 900, "title": "ISM", "country": "USD", "impact": "High", "forecast": "", "previous": "",
         "kind": "ISM", "source": "derived:rule"},
        {"ts_ms": 3000 * 900, "title": "GDP", "country": "USD", "impact": "High", "forecast": "", "previous": "",
         "kind": "GDP", "source": "official:alfred;irregular"},
        {"ts_ms": 3000 * 900, "title": "PCE", "country": "USD", "impact": "High", "forecast": "", "previous": "",
         "kind": "PCE", "source": "official:alfred"},
    ])
    rel = nd.load_releases(hist)
    assert list(rel["ts_ms"]) == [1000 * 900, 3000 * 900]
    assert rel["type"].tolist() == ["CPI", "PCE"] and rel["coreleased"].iloc[0] == "RETAIL"
    assert bool(rel["irregular"].iloc[1]) and rel["kinds"].iloc[1] == "PCE+GDP"
