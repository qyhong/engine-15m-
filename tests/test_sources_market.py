# -*- coding: utf-8 -*-
"""sources/market: the five market-wide cards, checked on planted files. No network, no real bars.

    py -3 -m pytest tests/test_sources_market.py -q        (from the project folder)
"""
import os
import re
import shutil
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import data  # noqa: E402
from engine15.sources import market  # noqa: E402

H, D, BAR = 3600000, 86400000, 900000
ASSETS = ("BTCUSDT", "ETHUSDT")
START = "2022-01-01"
N = 20000                                                             # 208 days of 15m bars
CUTS = (9000, 14011, 19990)


def make_bars(n=N, seed=1, start=START):
    rng = np.random.RandomState(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.002, n)))
    opn = np.concatenate([[100.0], close[:-1]])
    vol = rng.uniform(50, 150, n)
    return pd.DataFrame({"open": opn, "high": np.maximum(opn, close), "low": np.minimum(opn, close), "close": close,
                         "volume": vol, "taker_buy": vol * 0.5}, index=pd.date_range(start, periods=n, freq="15min", tz="UTC"))


def day_str(ms):
    return pd.Timestamp(int(ms), unit="ms", tz="UTC").strftime("%Y-%m-%d")


def ms_of(text):
    return int(pd.Timestamp(text, tz="UTC").timestamp() * 1000)


def write_sources(folder, bars, seed=0):
    """Plant all five sources: hourly files over the bars' span, daily files from 400 days before it."""
    rng = np.random.RandomState(seed)
    os.makedirs(folder, exist_ok=True)
    t0 = int(data.to_ms(bars["BTCUSDT"].index)[0])
    hours = np.arange(t0, t0 + (N // 4) * H, H, dtype="int64")
    for a in ASSETS:
        hourly = market._hourly_close(a, bars).reindex(hours).ffill().bfill().values
        prem = 0.0005 * np.sin(np.arange(len(hours)) / 150.0) + rng.normal(0, 0.0004, len(hours))
        keep = rng.uniform(size=len(hours)) > 0.01                    # a few hours with no Coinbase candle
        pd.DataFrame({"ts_ms": hours[keep], "close": (hourly * (1 + prem))[keep]}).to_csv(market.coinbase_path(a, folder), index=False)
    for i, coin in enumerate(market.COINS):
        listed = i * 200                                              # coins list at different times
        px = 10.0 * np.exp(np.cumsum(rng.normal(0, 0.006, len(hours))))
        pd.DataFrame({"ts_ms": hours[listed:], "close": px[listed:]}).to_csv(market.coin_path(coin, folder), index=False)
    days = np.arange(t0 - 400 * D, t0 + (N // 96 + 2) * D, D, dtype="int64")
    dates = [day_str(x) for x in days]
    supply = 1e11 * np.exp(np.cumsum(rng.normal(0.0005, 0.002, len(days))))
    pd.DataFrame({"date": dates, "total_usd": supply, "usd_pegged": supply * 0.98}).to_csv(market.stable_path(folder), index=False)
    fng = np.clip(50 + np.cumsum(rng.normal(0, 6, len(days))), 3, 97).round()
    phase = np.arange(len(days)) % 60                                  # fear, neutral and greed all occur
    fng = np.where(phase < 20, np.clip(fng, 3, 20), np.where(phase < 40, np.clip(fng, 35, 65), np.clip(fng, 80, 97)))
    pd.DataFrame({"date": dates, "value": fng.astype(int)}).to_csv(market.fng_path(folder), index=False)
    week = np.array([pd.Timestamp(int(x), unit="ms", tz="UTC").dayofweek < 5 for x in days])
    for key in ("btc", "eth"):
        flow = rng.normal(20, 250, len(days)).round(1)
        pd.DataFrame({"date": np.array(dates)[week], "net_musd": flow[week], "n_funds": 11}).to_csv(market.etf_path(key, folder), index=False)


def planted(tmp_path, name="src"):
    bars = {"BTCUSDT": make_bars(seed=1), "ETHUSDT": make_bars(seed=2)}
    folder = str(tmp_path / name)
    write_sources(folder, bars)
    return bars, folder


def same(a, b):
    return list(a.columns) == list(b.columns) and np.array_equal(a.values, b.values, equal_nan=True)


def test_groups_and_shape(tmp_path):
    bars, folder = planted(tmp_path)
    assert list(market.GROUPS) == ["etf", "stable", "cbprem", "breadth", "sentiment"]
    assert [t for t, _ in market.GROUPS.values()] == ["Spot ETF flows", "Stablecoin supply", "Coinbase premium",
                                                      "Market breadth and ETH/BTC", "Fear and Greed"]
    for a in ASSETS:
        f = market.features(bars[a].index, a, src_dir=folder, bars=bars, strict=True)
        assert f.index.equals(bars[a].index)
        x = f[market.FEATURES]
        assert not x.isna().any().any() and (x.dtypes == float).all()
        assert float(x.abs().max().max()) <= 3.0
        for col in ["brd_above_24h", "brd_above_7d", "brd_above_30d", "fng_level", "fng_extreme"]:
            assert float(x[col].abs().max()) <= 1.0
        for col in market.FEATURES:                                   # the planted data gives every reading something to say
            assert (x[col] != 0).mean() > 0.2, col
        assert set(np.unique(x["fng_extreme"])) == {-1.0, 0.0, 1.0}


def test_no_lookahead(tmp_path):
    """Cut the index (and the bars) off: every row already seen must stay exactly the same."""
    bars, folder = planted(tmp_path)
    for a in ASSETS:
        full = market.features(bars[a].index, a, src_dir=folder, bars=bars, strict=True)
        for cut in CUTS:
            part = market.features(bars[a].index[:cut], a, src_dir=folder, bars=bars, strict=True)
            assert same(full.iloc[:cut], part), "%s: a reading changed when the index was cut at %d" % (a, cut)
            short = dict((k, df.iloc[:cut]) for k, df in bars.items())
            part = market.features(bars[a].index[:cut], a, src_dir=folder, bars=short, strict=True)
            assert same(full.iloc[:cut], part), "%s: a reading changed when the bars were cut at %d" % (a, cut)


def test_future_source_rows_do_not_leak(tmp_path):
    """Change every source row that could not have been known at a cut (an hourly bar that ends
    after it, a daily value whose day ends after it, a 15m bar that closes after it): no reading
    at or before the cut may move, and readings after it must."""
    bars, folder = planted(tmp_path)
    rng = np.random.RandomState(7)
    base = dict((a, market.features(bars[a].index, a, src_dir=folder, bars=bars, strict=True)) for a in ASSETS)
    for n, cut in enumerate(CUTS[:2]):
        t_close = int(data.to_ms(bars["BTCUSDT"].index)[cut - 1]) + BAR
        alt = str(tmp_path / ("alt%d" % n))
        shutil.copytree(folder, alt)
        for name in os.listdir(alt):
            path = os.path.join(alt, name)
            d = pd.read_csv(path, float_precision="round_trip")    # rows before the cut are rewritten exactly as they were
            if "ts_ms" in d.columns:
                future = (d["ts_ms"].values + H) > t_close
                d["close"] = d["close"].astype(float)
                d.loc[future, "close"] = d.loc[future, "close"] * rng.uniform(0.5, 2.0, int(future.sum()))
                d = d[~future | (rng.uniform(size=len(d)) > 0.05)]    # and some future rows vanish
            else:
                future = (market._day_ms(d["date"].values) + D) > t_close
                for col in d.columns[1:]:
                    d[col] = d[col].astype(float)
                    d.loc[future, col] = (d.loc[future, col] * rng.uniform(0.5, 2.0, int(future.sum()))).round(0)
            assert future.any() and not future.all()
            d.to_csv(path, index=False)
        alt_bars = {}
        for a, df in bars.items():
            df = df.copy()
            future = (data.to_ms(df.index) + BAR) > t_close
            df.loc[future, "close"] = df.loc[future, "close"] * rng.uniform(0.8, 1.25, int(future.sum()))
            alt_bars[a] = df
        for a in ASSETS:
            got = market.features(bars[a].index, a, src_dir=alt, bars=alt_bars, strict=True)
            assert same(base[a].iloc[:cut], got.iloc[:cut]), "%s: a future source row reached a row before %d" % (a, cut)
            for voice, (_title, feats) in market.GROUPS.items():      # the change was real: every card moved afterwards
                assert not np.array_equal(base[a][feats].values[cut:], got[feats].values[cut:]), voice


def test_values_appear_exactly_when_known(tmp_path):
    """One planted value per source: it must show up on the first 15m row whose close is at or
    after the moment it became known, and not one row earlier."""
    n = 6000
    idx = pd.date_range("2022-03-01", periods=n, freq="15min", tz="UTC")
    flat = pd.DataFrame({"open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 1.0, "taker_buy": 0.5}, index=idx)
    bars = {"BTCUSDT": flat.copy(), "ETHUSDT": flat.copy()}
    jump_bar = pd.Timestamp("2022-04-10 05:15", tz="UTC")             # ETH doubles inside the 05:00 hour
    bars["ETHUSDT"].loc[bars["ETHUSDT"].index >= jump_bar, "close"] = 200.0
    folder = str(tmp_path / "exact")
    os.makedirs(folder)
    t0 = ms_of("2022-03-01")
    hours = np.arange(t0, t0 + (n // 4) * H, H, dtype="int64")
    spike = ms_of("2022-04-10 07:00")                                 # Coinbase 1% rich in the 07:00 hour only
    pd.DataFrame({"ts_ms": hours, "close": np.where(hours == spike, 101.0, 100.0)}).to_csv(market.coinbase_path("BTCUSDT", folder), index=False)
    lift = ms_of("2022-04-12 09:00")                                  # every altcoin doubles from the 09:00 hour on
    for coin in market.COINS:
        pd.DataFrame({"ts_ms": hours, "close": np.where(hours >= lift, 2.0, 1.0)}).to_csv(market.coin_path(coin, folder), index=False)
    days = np.arange(t0 - 30 * D, t0 + 70 * D, D, dtype="int64")
    dates = np.array([day_str(x) for x in days])
    pd.DataFrame({"date": dates, "value": np.where(dates == "2022-03-10", 10, 50)}).to_csv(market.fng_path(folder), index=False)
    supply = np.where(dates >= "2022-03-15", 2e11, 1e11)
    pd.DataFrame({"date": dates, "total_usd": supply, "usd_pegged": supply}).to_csv(market.stable_path(folder), index=False)
    pd.DataFrame({"date": dates, "net_musd": np.where(dates == "2022-03-16", 999.0, 1.0), "n_funds": 11}).to_csv(market.etf_path("btc", folder), index=False)

    f = market.features(idx, "BTCUSDT", src_dir=folder, bars=bars, strict=True)

    def first(mask):
        return f.index[np.flatnonzero(np.asarray(mask))[0]]

    def last(mask):
        return f.index[np.flatnonzero(np.asarray(mask))[-1]]

    # daily, stamped 10 Mar: known from 00:00 on 11 Mar = the close of the 23:45 bar of 10 Mar; gone a day later
    assert first(f.fng_value == 10) == pd.Timestamp("2022-03-10 23:45", tz="UTC")
    assert last(f.fng_value == 10) == pd.Timestamp("2022-03-11 23:30", tz="UTC")
    assert (f.fng_extreme[f.fng_value == 10] == -1.0).all() and (f.fng_extreme[f.fng_value != 10] == 0.0).all()
    assert first(f.stb_total_busd == 200.0) == pd.Timestamp("2022-03-15 23:45", tz="UTC")
    # an ETF flow for trading date 16 Mar: known from 12:00 UTC on 17 Mar
    assert first(f.etf_net_musd == 999.0) == pd.Timestamp("2022-03-17 11:45", tz="UTC")
    assert last(f.etf_net_musd == 999.0) == pd.Timestamp("2022-03-18 11:30", tz="UTC")
    # hourly, stamped 07:00: known from 08:00 = the close of the 07:45 bar; replaced an hour later
    rich = np.isclose(f.cbp_bps, 100.0)
    assert first(rich) == pd.Timestamp("2022-04-10 07:45", tz="UTC") and last(rich) == pd.Timestamp("2022-04-10 08:30", tz="UTC")
    assert first(f.brd_pct_24h == 100.0) == pd.Timestamp("2022-04-12 09:45", tz="UTC")
    assert first(f.brd_above_24h == 1.0) == pd.Timestamp("2022-04-12 09:45", tz="UTC")
    # the project's own bars: ETH doubled at 05:15, the ETH/BTC ratio may say so only once the 05:00 hour has ended
    assert first(f.brd_ethbtc == 2.0) == pd.Timestamp("2022-04-10 05:45", tz="UTC")
    assert first(f.brd_ethbtc_1d != 0) == pd.Timestamp("2022-04-10 05:45", tz="UTC")


def test_stale_and_missing_sources_say_nothing(tmp_path, monkeypatch):
    bars, folder = planted(tmp_path)
    idx = bars["BTCUSDT"].index
    empty = str(tmp_path / "none")
    os.makedirs(empty)
    monkeypatch.setattr(market, "BARS_PATH", lambda asset: str(tmp_path / "no_such_bars.csv"))
    f = market.features(idx, "BTCUSDT", src_dir=empty, strict=True)  # no files, no bars: nothing to read
    assert (f[market.FEATURES] == 0).all().all() and f[market.RAW].isna().all().all()
    for name in os.listdir(folder):                                   # every source stops 60 days before the end
        d = pd.read_csv(os.path.join(folder, name), float_precision="round_trip")
        stop = int(data.to_ms(idx)[-1]) - 60 * D
        keep = (d["ts_ms"].values < stop) if "ts_ms" in d.columns else (market._day_ms(d["date"].values) < stop)
        d[keep].to_csv(os.path.join(folder, name), index=False)
    f = market.features(idx, "BTCUSDT", src_dir=folder, bars=bars, strict=True)
    tail = f.iloc[-96 * 50:]                                          # 10 days after the stop every outside source is silent
    outside = [c for c in market.FEATURES if not c.startswith("brd_ethbtc")]
    assert (tail[outside] == 0).all().all()
    assert (f.iloc[:-96 * 70][outside] != 0).any().all()


def test_describe(tmp_path):
    bars, folder = planted(tmp_path)
    f = market.features(bars["ETHUSDT"].index, "ETHUSDT", src_dir=folder, bars=bars, strict=True)
    titles = [t for t, _ in market.GROUPS.values()]
    for row in (f.iloc[-1], f.iloc[0], f.iloc[-1].to_dict(), {}):
        said = market.describe(row, "ETHUSDT", src_dir=folder)
        assert list(said) == titles
        assert all(isinstance(s, str) and s.endswith(".") and not re.search(r"nan", s.lower()) for s in said.values()), said
    said = market.describe(f.iloc[-1], "ETHUSDT", src_dir=folder)
    assert "Ether ETFs" in said["Spot ETF flows"] and "ETH/BTC" in said["Market breadth and ETH/BTC"]
    assert market.describe({}, "ETHUSDT", src_dir=str(tmp_path / "nowhere"))["Spot ETF flows"].startswith("No source reachable")


ETF_HTML = """<table class="etf"><tr><th>Date</th><th>AAA</th><th>BBB</th><th>Total</th></tr>
<tr><td>Fee</td><td>0.25%</td><td>0.20%</td><td></td></tr>
<tr><td>11 Jan 2024</td><td><span class="g">111.7</span></td><td><span class="r">(95.1)</span></td><td>16.6</td></tr>
<tr><td>12 Jan 2024</td><td>1,386.0</td><td>-</td><td>1,386.0</td></tr>
<tr><td>15 Jan 2024</td><td>-</td><td>-</td><td>0.0</td></tr>
<tr><td>16 Jan 2024</td><td>0.0</td><td>(594.4)</td><td><span>(594.4)</span></td></tr>
<tr><td>17 Jan 2024</td><td>5.0</td><td>6.0</td><td>11.0</td></tr>
<tr><td>18 Jan 2024</td><td>7.0</td><td>-</td><td>7.0</td></tr>
<tr><td>19 Jan 2024</td><td>-</td><td>-</td><td>0.0</td></tr>
<tr><td>Total</td><td>1,509.7</td><td>(683.5)</td><td>826.2</td></tr></table>"""


class Reply(object):
    def __init__(self, text="", payload=None):
        self.text, self.payload = text, payload

    def json(self):
        return self.payload


def test_etf_table_parse():
    d = market.parse_etf_table(ETF_HTML)
    assert list(d.columns) == ["date", "net_musd", "n_funds"]
    assert list(d.date) == ["2024-01-11", "2024-01-12", "2024-01-16", "2024-01-17", "2024-01-18"]   # the all-dash days are left out
    assert list(d.net_musd) == [16.6, 1386.0, -594.4, 11.0, 7.0] and list(d.n_funds) == [2, 1, 2, 2, 1]


def test_update_stores_only_what_is_closed_and_known(tmp_path, monkeypatch):
    """A canned network: update() must keep closed hours, finished days and published flows only,
    extend its files on the next call, and write ts_ms / date first."""
    now = [ms_of("2024-01-19 10:30")]
    asked = []

    def fake_get(sess, url, params=None):
        asked.append(url)
        if "farside" in url:
            return Reply(text=ETF_HTML)
        if "llama" in url:
            return Reply(payload=[{"date": str((ms_of("2023-11-01") + i * D) // 1000),
                                   "totalCirculatingUSD": {"peggedUSD": 1e11 + i, "peggedEUR": 1e9}} for i in range(80)])
        if "alternative" in url:
            return Reply(payload={"data": [{"value": str(40 + i % 7), "timestamp": str((ms_of("2023-11-01") + i * D) // 1000)}
                                           for i in range(79, -1, -1)]})
        if "coinbase" in url:
            lo, hi = ms_of(params["start"]) // 1000, ms_of(params["end"]) // 1000
            return Reply(payload=[[t, 1.0, 3.0, 2.0, 2.5, 9.0] for t in range(hi, lo - 1, -3600)])   # newest first, like the venue
        first = max(params["startTime"], ms_of("2024-01-10"))        # Binance: "listed" on 10 Jan, the forming hour included
        stamps = list(range(first, min(first + 1000 * H, now[0]), H))
        return Reply(payload=[[t, "1", "1", "1", "7.5", "1", t + H - 1] for t in stamps])

    monkeypatch.setattr(market, "_get", fake_get)
    monkeypatch.setattr(market, "_now_ms", lambda: now[0])
    monkeypatch.setattr(market, "START_MS", ms_of("2024-01-01"))
    monkeypatch.setattr(market, "CB_PAUSE", 0.0)
    monkeypatch.setattr(market, "BN_PAUSE", 0.0)
    monkeypatch.setattr(market.time, "sleep", lambda s: None)
    folder = str(tmp_path / "upd")
    got = market.update(log=None, src_dir=folder)
    assert all(isinstance(v, int) for v in got.values()), got
    assert len(got) == 4 + 2 + len(market.COINS)
    etf = pd.read_csv(market.etf_path("btc", folder))
    assert list(etf.columns) == ["date", "net_musd", "n_funds"]
    assert list(etf.date) == ["2024-01-11", "2024-01-12", "2024-01-16", "2024-01-17"]     # 18 Jan is not known before 12:00 on the 19th
    st = pd.read_csv(market.stable_path(folder))
    assert st.columns[0] == "date" and st.date.iloc[-1] == "2024-01-18" and st.total_usd.iloc[0] == 1e11 + 1e9
    fg = pd.read_csv(market.fng_path(folder))
    assert fg.columns[0] == "date" and fg.date.iloc[-1] == "2024-01-19" and fg.date.is_monotonic_increasing
    cb = pd.read_csv(market.coinbase_path("BTCUSDT", folder))
    assert cb.columns[0] == "ts_ms" and cb.ts_ms.iloc[0] == ms_of("2024-01-01") and cb.ts_ms.iloc[-1] == ms_of("2024-01-19 09:00")
    assert (np.diff(cb.ts_ms) == H).all() and (cb.close == 2.5).all()
    sol = pd.read_csv(market.coin_path("SOL", folder))
    assert sol.ts_ms.iloc[0] == ms_of("2024-01-10") and sol.ts_ms.iloc[-1] == ms_of("2024-01-19 09:00") and (sol.close == 7.5).all()
    assert not [n for n in os.listdir(folder) if n.endswith(".tmp")]

    asked[:] = []
    now[0] = ms_of("2024-01-19 13:05")                                # two and a half hours on: only the hourly files are asked
    got = market.update(log=None, src_dir=folder)
    assert not [u for u in asked if "farside" in u or "llama" in u or "alternative" in u]
    assert got["coinbase_btc"] == len(cb) + 3 and got["breadth_sol"] == len(sol) + 3
    got = market.update(log=None, src_dir=folder, force=True)         # asked again: 18 Jan's flow has now been published
    assert list(pd.read_csv(market.etf_path("btc", folder)).date)[-1] == "2024-01-18" and got["etf_btc"] == 5


def test_update_never_raises_and_keeps_old_files(tmp_path, monkeypatch):
    bars, folder = planted(tmp_path)

    def down(sess, url, params=None):
        raise IOError("network is down")

    monkeypatch.setattr(market, "_get", down)
    monkeypatch.setattr(market.time, "sleep", lambda s: None)
    before = dict((n, open(os.path.join(folder, n), "rb").read()) for n in os.listdir(folder))
    lines = []
    got = market.update(log=lines.append, src_dir=folder, force=True)
    assert len(got) == 16 and all(str(v).startswith("failed: ") for v in got.values()), got
    assert len(lines) == 16
    assert before == dict((n, open(os.path.join(folder, n), "rb").read()) for n in os.listdir(folder))
    fresh = str(tmp_path / "fresh")                                   # nothing on disk and nothing reachable: empty files, no read
    got = market.update(log=None, src_dir=fresh, force=True)
    assert all(str(v).startswith("failed: ") for v in got.values())
    assert os.path.exists(market.etf_path("btc", fresh)) and len(pd.read_csv(market.etf_path("btc", fresh))) == 0
    f = market.features(bars["BTCUSDT"].index[:500], "BTCUSDT", src_dir=fresh, bars=bars, strict=True)
    assert (f[[c for c in market.FEATURES if not c.startswith("brd_ethbtc")]] == 0).all().all()
    assert market.describe(f.iloc[-1], "BTCUSDT", src_dir=fresh)["Spot ETF flows"].startswith("No source reachable")


def test_default_paths_can_be_pointed_elsewhere(tmp_path, monkeypatch):
    """Without src_dir / bars the module reads SRC_DIR and BARS_PATH; both can be overridden."""
    bars, folder = planted(tmp_path)
    for a, df in bars.items():
        data.save(a, df, path=str(tmp_path / ("%s_15m.csv" % a.lower())))
    monkeypatch.setattr(market, "SRC_DIR", folder)
    monkeypatch.setattr(market, "BARS_PATH", lambda asset: str(tmp_path / ("%s_15m.csv" % asset.lower())))
    for a in ASSETS:
        on_disk = market.features(bars[a].index, a, strict=True)
        handed = market.features(bars[a].index, a, src_dir=folder, bars=bars, strict=True)
        assert np.allclose(on_disk.values, handed.values, atol=1e-9, equal_nan=True)
