# -*- coding: utf-8 -*-
"""engine15/sources/cryptox.py (batch 3, crypto) checked on planted data with a fake network. No real network, no
real files.

    py -3 -m pytest tests/test_sources_cryptox.py -q        (from the project folder)
"""
import os
import re
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import data  # noqa: E402
from engine15.sources import cryptox as cx  # noqa: E402
from engine15.sources import options_hist as oh  # noqa: E402

A, E = "BTCUSDT", "ETHUSDT"
BAR, HOUR, DAY = cx.BAR_MS, cx.HOUR_MS, cx.DAY_MS
START = "2024-01-01"
N_DAYS = 70
T0 = int(pd.Timestamp(START, tz="UTC").value // 10 ** 6)
FILE_DAYS = N_DAYS - 2                                  # the planted files stop two days before the bars and the index


def make_index(n_days=N_DAYS):
    return pd.date_range(START, periods=n_days * 96, freq="15min", tz="UTC")


def make_bars(asset, n_days=N_DAYS, seed=1):
    rng = np.random.RandomState(seed + (asset == E))
    idx = make_index(n_days)
    n = len(idx)
    close = (40000.0 if asset == A else 2500.0) * np.exp(np.cumsum(rng.normal(0, 0.004, n)))
    op = np.r_[close[0], close[:-1]]
    hi = np.maximum(op, close) * (1 + rng.uniform(0, 0.002, n))
    lo = np.minimum(op, close) * (1 - rng.uniform(0, 0.002, n))
    vol = rng.uniform(50, 150, n)
    return pd.DataFrame({"open": op, "high": hi, "low": lo, "close": close, "volume": vol,
                         "taker_buy": vol * rng.uniform(0.3, 0.7, n)}, index=idx)


def make_sources(bars, n_days=FILE_DAYS, seed=5):
    """-> {(kind, asset): frame} as update would store them, with holes; asset None for the shared files."""
    rng = np.random.RandomState(seed)
    out = {}
    days = pd.date_range(START, periods=n_days, freq="D")
    bdays = days[days.dayofweek < 5]
    fx = pd.DataFrame({"date": bdays.strftime("%Y-%m-%d"), "usdkrw": 1300 + np.cumsum(rng.normal(0, 3, len(bdays)))})
    fx["known_ms"] = cx._fx_known(fx["date"])
    out[("fx", None)] = fx
    c = pd.DataFrame({"date": days.strftime("%Y-%m-%d")})
    k = len(c)
    c["btc"] = 1.2e12 * np.exp(np.cumsum(rng.normal(0, 0.03, k)))
    c["eth"] = 3e11 * np.exp(np.cumsum(rng.normal(0, 0.04, k)))
    for i, a in enumerate(cx.DOM_ALTS):
        c[a] = 1e10 * (i + 1) * np.exp(np.cumsum(rng.normal(0, 0.05, k)))
    c.loc[k // 2, "xrp"] = np.nan                                       # a missing alt: like-with-like comparison
    c["known_ms"] = cx._day_ms(c["date"]) + DAY + cx.DOM_LAG_MS
    out[("caps", None)] = c
    s = pd.DataFrame({"date": days.strftime("%Y-%m-%d"), "total_usd": 1.5e11 * np.exp(np.cumsum(rng.normal(0, 0.005, k)))})
    s["known_ms"] = cx._day_ms(s["date"]) + DAY + cx.DOM_LAG_MS
    out[("stables", None)] = s
    end = T0 + n_days * DAY
    for asset in (A, E):
        b = bars[asset]
        ts = data.to_ms(b.index)
        keep = ts < end
        ts, cl = ts[keep], b["close"].values[keep]
        n = len(ts)
        fxv = np.interp(ts, cx._day_ms(fx["date"]), fx["usdkrw"].values)
        prem = 0.02 + 0.005 * np.sin(np.arange(n) / 500.0) + rng.normal(0, 0.001, n)
        up = pd.DataFrame({"ts_ms": ts, "close": cl * fxv * (1 + prem), "vol_krw": rng.uniform(1e9, 5e9, n)})
        up["known_ms"] = up["ts_ms"] + BAR + cx.BAR_LAG_MS
        out[("upbit", asset)] = up[rng.rand(n) > 0.01].reset_index(drop=True)
        pc = cl * (1 + 0.0005 + rng.normal(0, 0.0003, n))
        pv = rng.uniform(300, 900, n)
        p = pd.DataFrame({"ts_ms": ts, "open": pc, "high": pc * 1.001, "low": pc * 0.999, "close": pc, "volume": pv,
                          "taker_buy": pv * rng.uniform(0.3, 0.7, n)})
        p["known_ms"] = p["ts_ms"] + BAR + cx.BAR_LAG_MS
        out[("perp", asset)] = p[rng.rand(n) > 0.01].reset_index(drop=True)
        f8 = np.arange(T0, end, 8 * HOUR, dtype="int64")
        out[("bybit_fund", asset)] = pd.DataFrame({"ts_ms": f8, "rate": 1e-4 + rng.normal(0, 1e-4, len(f8)),
                                                   "known_ms": f8 + cx.FUND_LAG_MS})
        late = f8[len(f8) // 3:]                                       # OKX starts later: one venue fewer early on
        out[("okx_fund", asset)] = pd.DataFrame({"ts_ms": late, "rate": 1e-4 + rng.normal(0, 1e-4, len(late)),
                                                 "known_ms": late + cx.FUND_LAG_MS})
        bf = pd.DataFrame({"ts_ms": f8, "rate": 1e-4 + rng.normal(0, 1e-4, len(f8))})
        out[("binance_funding", asset)] = bf
        h = np.arange(T0, end, HOUR, dtype="int64")
        for kind, start in (("bybit_oi", 0), ("okx_oi", len(h) // 2)):
            hh = h[start:]
            out[(kind, asset)] = pd.DataFrame({"ts_ms": hh, "oi": 5e4 * np.exp(np.cumsum(rng.normal(0, 0.005, len(hh)))),
                                               "known_ms": hh + cx.OI_LAG_MS})
        g = pd.DataFrame(0.0, index=np.arange(len(h)), columns=oh.HOURLY_COLS)
        g["ts_ms"] = h
        g["n"] = rng.randint(20, 60, len(h)).astype(float)
        g["put_usd"], g["call_usd"] = rng.uniform(1e6, 5e6, len(h)), rng.uniform(1e6, 5e6, len(h))
        g["put_buy_usd"], g["call_buy_usd"] = g["put_usd"] * rng.uniform(0.3, 0.7, len(h)), g["call_usd"] * rng.uniform(0.3, 0.7, len(h))
        for side in ("rr_put", "rr_call"):
            w = rng.uniform(1, 5, len(h))
            g[side + "_w"], g[side + "_n"] = w, 5.0
            g[side + "_ivw"] = w * (55 + (5 if side == "rr_put" else 0) + rng.normal(0, 3, len(h)))
        g["atm_w"] = rng.uniform(1, 5, len(h))
        g["atm_ivw"] = g["atm_w"] * 50
        g["blk_n"] = 2.0
        for col in ("blk_put_buy_usd", "blk_put_sell_usd", "blk_call_buy_usd", "blk_call_sell_usd"):
            g[col] = rng.uniform(0, 1e6, len(h))
        g["known_ms"] = g["ts_ms"] + HOUR
        out[("hourly", asset)] = g
    return out


def write_sources(src, folder):
    folder = str(folder)
    for (kind, asset), frame in src.items():
        if kind == "binance_funding":
            os.makedirs(folder, exist_ok=True)
            frame.to_csv(os.path.join(folder, "binance_funding_%s.csv" % asset.lower()), index=False)
        elif kind == "hourly":
            oh._write(oh.path_for("hourly", asset, folder), frame[oh.HOURLY_COLS])
        else:
            cx._write(cx.path_for(kind, asset, folder), frame[cx.FILES[kind]])
    return folder


BARS = dict((a, make_bars(a)) for a in (A, E))
SRC = make_sources(BARS)


def same(a, b):
    return np.array_equal(a.values.astype(float), b.values.astype(float), equal_nan=True)


CUTS = (96 * 35 + 47, 96 * 50, 96 * 61 + 5, 96 * 69 - 1)


def test_no_lookahead_cutting_the_index_and_the_bars(tmp_path):
    idx = make_index()
    folder = write_sources(SRC, tmp_path)
    for asset in (A, E):
        full = cx.features(idx, asset, src_dir=folder, bars=BARS[asset])
        assert full.attrs["errors"] == {}, full.attrs["errors"]
        for col in cx.FEATURES:                                       # never zero against zero
            assert (full[col] != 0).mean() > 0.05, "%s never speaks on the planted data (%s)" % (col, asset)
        for cut in CUTS:
            part = cx.features(idx[:cut], asset, src_dir=folder, bars=BARS[asset])
            assert list(part.columns) == list(full.columns) and len(part) == cut
            assert same(full.iloc[:cut], part), "a reading changed when the index was cut at %d" % cut
            live = cx.features(idx[:cut], asset, src_dir=folder, bars=BARS[asset].iloc[:cut])   # bars end there too
            assert same(full.iloc[:cut], live), "a reading changed when the bars were cut at %d" % cut


def _rewrite_unknown(src, t):
    """Rewrite every stored value NOT yet known at instant t (the Binance funding file: settled after t)."""
    out = dict((k, f.copy()) for k, f in src.items())
    rng = np.random.RandomState(7)
    for (kind, asset), f in out.items():
        if kind == "binance_funding":
            late = (f["ts_ms"] + cx.FUND_LAG_MS > t).values
            f.loc[late, "rate"] = rng.normal(0, 5e-4, late.sum())
            continue
        late = (f["known_ms"] > t).values
        num = [c for c in f.columns if c not in ("ts_ms", "date", "known_ms")]
        f.loc[late, num] = f.loc[late, num].values * np.exp(rng.normal(0, 0.3, (late.sum(), len(num))))
    return out


def test_values_not_yet_known_do_not_reach_earlier_rows(tmp_path):
    idx = make_index()
    base = dict((a, cx.features(idx, a, src_dir=write_sources(SRC, tmp_path / "base"), bars=BARS[a])) for a in (A, E))
    close = data.to_ms(idx) + BAR
    for cut in CUTS[:3]:
        t = int(close[cut - 1])
        folder = write_sources(_rewrite_unknown(SRC, t), tmp_path / ("cut%d" % cut))
        for asset in (A, E):
            got = cx.features(idx, asset, src_dir=folder, bars=BARS[asset])
            assert got.attrs["errors"] == {}
            assert same(base[asset].iloc[:cut], got.iloc[:cut]), "data not yet known at %d reached an earlier row" % cut
            moved = (base[asset].iloc[cut:] != got.iloc[cut:]).any()
            for card in ("optflow", "kprem", "dom", "spotlead", "xfund"):      # the rewrite was a real one
                assert moved[cx.GROUPS[card][1]].any(), "the rewrite never showed in %s" % card


def test_known_at_times_are_respected_exactly(tmp_path):
    """The last stored row of each file, made known later at a bar close C: invisible at C - 15 min, visible at C."""
    idx = make_index()
    close = data.to_ms(idx) + BAR
    for kind, raw, col, scale in (("upbit", "kp_upbit_krw", "close", 1.5), ("bybit_fund", "xf_bybit", "rate", 9.0),
                                  ("okx_fund", "xf_okx", "rate", 9.0), ("caps", "dm_btc_share", "btc", 3.0),
                                  ("perp", "sl_basis_bp", "close", 1.01), ("bybit_oi", "xf_oi_bybit_24h", "oi", 2.0)):
        src = dict((k, f.copy()) for k, f in SRC.items())
        key = (kind, None if kind == "caps" else A)
        f = src[key]
        j = len(f) - 1
        c = int(close[np.searchsorted(close, int(f["known_ms"].iloc[j])) + 4])     # an hour after its nominal time
        f.loc[j, "known_ms"] = c
        f.loc[j, col] = f.loc[j, col] * scale
        folder = write_sources(src, tmp_path / kind)
        i = int(np.searchsorted(close, c))
        x = cx.features(idx[i - 1:i + 1], A, src_dir=folder, bars=BARS[A])
        without = dict(src)
        without[key] = f.iloc[:j]                                       # the same files without that row
        y = cx.features(idx[i - 1:i + 1], A, src_dir=write_sources(without, tmp_path / (kind + "_without")), bars=BARS[A])
        assert np.isclose(x[raw].iloc[0], y[raw].iloc[0], equal_nan=True), "%s: a value was used before it was known" % kind
        assert np.isfinite(x[raw].iloc[1]) and not np.isclose(x[raw].iloc[1], y[raw].iloc[1], equal_nan=True),             "%s: not used once known" % kind


def test_features_bounded_never_nan_and_no_files_is_no_read(tmp_path):
    idx = make_index()
    f = cx.features(idx, A, src_dir=write_sources(SRC, tmp_path), bars=BARS[A])
    assert list(f.columns) == cx.FEATURES + cx.RAW
    x = f[cx.FEATURES]
    assert x.dtypes.eq(float).all() and np.isfinite(x.values).all() and x.abs().max().max() <= 1.0
    empty = cx.features(idx, E, src_dir=str(tmp_path / "nothing"), bars=BARS[E])
    assert empty.attrs["errors"] == {}
    fetched = [c for c in cx.FEATURES + cx.RAW if not c.startswith("cg_")]   # the CME card reads the bars themselves
    assert (empty[[c for c in fetched if c in cx.FEATURES]] == 0.0).all().all()
    assert empty[[c for c in fetched if c in cx.RAW]].isna().all().all()
    assert (cx.features(idx[:10], "XAUUSD", src_dir=str(tmp_path))[cx.FEATURES] == 0.0).all().all()


def test_readings_have_the_intended_meaning(tmp_path):
    idx = make_index()
    folder = write_sources(SRC, tmp_path)
    f = cx.features(idx, A, src_dir=folder, bars=BARS[A])
    row = f.iloc[96 * 40 + 9]
    assert 1.0 < row["kp_prem_pct"] < 4.0                              # the planted premium is about 2%
    assert 1300 * 0.9 < row["kp_usdkrw"] < 1300 * 1.1
    assert 0 < row["sl_spot_share"] < 50 and 0 < row["sl_basis_bp"] < 15       # perp volume larger, perp above spot
    assert row["xf_n_venues"] == 3 and np.isclose(row["xf_avg_raw"], np.mean([row["xf_binance"], row["xf_bybit"], row["xf_okx"]]))
    assert f.iloc[96 * 5]["xf_n_venues"] == 2                          # before OKX's planted start
    c = SRC[("caps", None)]
    s = SRC[("stables", None)]
    j = 40
    tot = c.loc[j, ["btc", "eth"] + cx.DOM_ALTS].sum() + s.loc[j, "total_usd"]
    want = 100.0 * c.loc[j, "btc"] / tot
    at = int(c.loc[j, "known_ms"])
    i = int(np.searchsorted(data.to_ms(idx) + BAR, at))
    assert np.isclose(f["dm_btc_share"].iloc[i], want)
    assert np.isclose(cx._per8h(np.array([0, 4 * HOUR, 8 * HOUR]), np.array([1e-4, 1e-4, 1e-4]))[1], 2e-4)


def test_cme_sessions_are_dst_aware_and_skip_good_friday():
    s = dict(cx.cme_sessions(cx._ms("2024-03-01"), cx._ms("2024-07-10")))
    assert s[cx._ms("2024-03-08 22:00")] == cx._ms("2024-03-10 22:00")    # CST close, reopen after the DST switch
    assert s[cx._ms("2024-07-05 21:00")] == cx._ms("2024-07-07 22:00")
    assert cx._ms("2024-03-28 21:00") in s and cx._ms("2024-03-29 21:00") not in s   # Good Friday 2024


def test_cme_gap_level_fill_and_open_move(tmp_path):
    idx = pd.date_range("2024-05-13", periods=96 * 42, freq="15min", tz="UTC")       # 14 days for the daily ATR first
    close = np.full(len(idx), 100.0)
    ms = data.to_ms(idx) + BAR
    fri, sun = cx._ms("2024-06-14 21:00"), cx._ms("2024-06-16 22:00")       # CDT: 16:00 / 17:00 Chicago
    close[ms > fri] = 104.0                                              # the weekend move up: an unfilled gap at 100
    back = cx._ms("2024-06-19 12:00")
    close[ms > back] = 99.5                                              # price returns below 100: filled
    b = pd.DataFrame({"open": close, "high": close + 1.5, "low": close - 1.5, "close": close, "volume": 1.0,
                      "taker_buy": 0.5}, index=idx)
    b.iloc[0, 0] = 100.0
    f = cx.features(idx, A, src_dir=str(tmp_path), bars=b)
    at = lambda t: f.iloc[int(np.searchsorted(ms, cx._ms(t)))]          # noqa: E731
    sat = at("2024-06-15 12:00")
    assert sat["cg_cme_close"] == 100.0 and sat["cg_open_atr"] > 0 and sat["cg_open"] > 0
    mon = at("2024-06-17 12:00")
    assert np.isnan(mon["cg_open_atr"]) and mon["cg_below_lvl"] == 100.0 and mon["cg_below"] < 0
    assert np.isclose(mon["cg_below_age_d"], (cx._ms("2024-06-17 12:00") - sun) / DAY)
    assert np.isnan(at("2024-06-19 13:00")["cg_below_lvl"])             # filled


def test_describe(tmp_path):
    idx = make_index()
    folder = write_sources(SRC, tmp_path)
    titles = [t for t, _ in cx.GROUPS.values()]
    for asset in (A, E):
        f = cx.features(idx, asset, src_dir=folder, bars=BARS[asset])
        for i in (0, 96 * 45, len(idx) - 1):
            said = cx.describe(f.iloc[i], asset)
            assert list(said) == titles
            assert all(isinstance(s, str) and len(s) > 20 and not re.search(r"\bnan\b|\binf\b", s) for s in said.values()), said
            assert not any(re.search(r"\bwill\b|expect|predict", s) for s in said.values())   # no forecasts
    assert list(cx.describe({}, E)) == titles


def test_applies_crypto_only_and_names_do_not_collide():
    import importlib
    from engine15 import evidence, sources
    assert all(v == (A, E) for v in cx.APPLIES.values()) and set(cx.APPLIES) == set(cx.GROUPS)
    taken, feats = set(evidence.GROUPS) - set(cx.GROUPS), set()      # wired: evidence.GROUPS now holds cx itself
    for name in [m for m in sources.MODULES if m != "cryptox"] + ["options_hist"]:
        m = importlib.import_module("engine15.sources." + name)
        taken |= set(m.GROUPS)
        feats |= set(f for _t, fs in m.GROUPS.values() for f in fs) | set(getattr(m, "RAW", []))
    assert not (set(cx.GROUPS) & taken), set(cx.GROUPS) & taken
    assert not (set(cx.FEATURES + cx.RAW) & feats), set(cx.FEATURES + cx.RAW) & feats
    assert len(set(cx.FEATURES + cx.RAW)) == len(cx.FEATURES + cx.RAW)


def test_wired_as_v5_2_2():
    """Batch 3 (crypto) is live as think15-v5.2.2 (15 Nov 2026); options_hist itself stays out of MODULES (cryptox reads it)."""
    from engine15 import sources, evidence
    assert "cryptox" in sources.MODULES and "options_hist" not in sources.MODULES
    assert cx in evidence.SOURCES


# ------------------------------------------------------------------ update, against a planted network
class Resp(object):
    def __init__(self, status, payload=None):
        self.status_code, self._p, self.text = status, payload, ""

    def json(self):
        return self._p


def _iso(ms):
    return pd.Timestamp(int(ms), unit="ms").strftime("%Y-%m-%dT%H:%M:%S")


class FakeNet(object):
    def __init__(self, fail=()):
        self.calls, self.fail = [], fail

    def __call__(self, url, params=None):
        params = dict(params or {})
        self.calls.append((url, params))
        assert "key" not in str(params).lower() and "token" not in str(params).lower()
        if any(w in url for w in self.fail):
            raise RuntimeError("planted outage")
        now = int(time.time() * 1000)
        host = url.split("/")[2]
        if host == "api.upbit.com":
            to = cx._ms(params["to"])
            ts = [t for t in range(to - 200 * BAR, to, BAR) if t <= now][::-1]          # newest first, the live bar too
            return Resp(200, [{"candle_date_time_utc": _iso(t), "trade_price": 1e8 + t % 997,
                               "candle_acc_trade_price": 1e9} for t in ts][:int(params["count"])])
        if host == "api.frankfurter.dev":
            a, b = re.search(r"/(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})", url).groups()
            days = [d for d in pd.date_range(a, b, freq="D") if d.dayofweek < 5]
            return Resp(200, {"rates": dict((d.strftime("%Y-%m-%d"), {"KRW": 1350.0}) for d in days)})
        if host == "community-api.coinmetrics.io":
            days = pd.date_range(params["start_time"], pd.Timestamp(now, unit="ms").strftime("%Y-%m-%d"), freq="D")
            return Resp(200, {"data": [{"asset": a, "time": d.strftime("%Y-%m-%dT00:00:00.000000000Z"),
                                        "CapMrktCurUSD": "1e10"} for d in days for a in cx.DOM_CM]})
        if host == "stablecoins.llama.fi":
            days = pd.date_range(end=pd.Timestamp(now, unit="ms").normalize(), periods=40, freq="D")
            return Resp(200, [{"date": str(int(d.value // 10 ** 9)), "totalCirculatingUSD": {"peggedUSD": 1.5e11}} for d in days])
        if host == "fapi.binance.com":
            s, e = int(params["startTime"]), min(int(params["endTime"]), now)
            ts = list(range(-(-s // BAR) * BAR, e + 1, BAR))[:int(params["limit"])]
            return Resp(200, [[t, "1", "2", "0.5", "1.5", "10", t + BAR - 1, "0", 5, "6", "0", "0"] for t in ts])
        if host == "api.bybit.com":
            s, e = int(params["startTime"]), min(int(params["endTime"]), now)
            if "funding" in url:
                ts = range(-(-s // (8 * HOUR)) * 8 * HOUR, e + 1, 8 * HOUR)
                rows = [{"fundingRateTimestamp": str(t), "fundingRate": "0.0001"} for t in ts][::-1]
            else:
                ts = range(-(-s // HOUR) * HOUR, e + 1, HOUR)
                rows = [{"timestamp": str(t), "openInterest": "5000"} for t in ts][::-1]
            return Resp(200, {"retCode": 0, "result": {"list": rows[:200]}})
        if host == "www.okx.com":
            if "funding" in url:
                top = int(params.get("after", now + 1)) - 1
                ts = [t for t in range(top // (8 * HOUR) * 8 * HOUR, now - 20 * DAY, -8 * HOUR)][:100]
                return Resp(200, {"code": "0", "data": [{"fundingTime": str(t), "fundingRate": "0.0002"} for t in ts]})
            top = int(params.get("end", now))
            ts = [t for t in range(top // HOUR * HOUR, now - 3 * DAY, -HOUR)][:100]
            return Resp(200, {"code": "0", "data": [[str(t), "1", "4000", "1"] for t in ts]})
        raise AssertionError("unexpected request %s" % url)


def fake_deribit(url, params=None):
    assert url == oh.HIST and "key" not in str(params).lower()
    return {"trades": [], "has_more": False}


def _recent(monkeypatch, days=3):
    now = int(time.time() * 1000)
    d = pd.Timestamp(now - days * DAY, unit="ms").strftime("%Y-%m-%d")
    monkeypatch.setattr(cx, "UPBIT_START", d)
    monkeypatch.setattr(cx, "FX_START", pd.Timestamp(now - 20 * DAY, unit="ms").strftime("%Y-%m-%d"))
    monkeypatch.setattr(cx, "DOM_START", pd.Timestamp(now - 20 * DAY, unit="ms").strftime("%Y-%m-%d"))
    monkeypatch.setattr(cx, "BYBIT_START", d)
    for a in (A, E):
        monkeypatch.setitem(cx.PERP_START, a, d)
        monkeypatch.setitem(oh.FETCH_START, a, pd.Timestamp(now - 1 * DAY, unit="ms").strftime("%Y-%m-%d"))
    return now


def test_update_extends_and_never_changes_stored_rows(tmp_path, monkeypatch):
    src = str(tmp_path / "src")
    now = _recent(monkeypatch)
    net = FakeNet()
    monkeypatch.setattr(cx, "_get", net)
    monkeypatch.setattr(oh, "_get", fake_deribit)
    out = cx.update(log=lambda *_: None, src_dir=src, assets=(A,))
    assert all(isinstance(v, int) and v > 0 for v in out.values()), out
    assert set(out) == {"optflow_BTCUSDT", "upbit_BTCUSDT", "fx", "caps", "stables", "perp_BTCUSDT", "bybit_fund_BTCUSDT",
                        "bybit_oi_BTCUSDT", "okx_fund_BTCUSDT", "okx_oi_BTCUSDT"}
    for kind in ("upbit", "perp"):                                     # closed bars only, known after close + 1 minute
        f = cx.load_source(kind, A, src)
        assert (np.diff(f.ts_ms.values) == BAR).all() and (f.ts_ms + BAR <= now).all()
        assert (f.known_ms >= f.ts_ms + BAR + cx.BAR_LAG_MS).all()
    h = oh.load_source("hourly", A, src)
    assert (h.ts_ms + HOUR + oh.LIVE_LAG_MS <= now + 60000).all()
    assert (h.known_ms >= h.ts_ms + HOUR).all() and len(h) >= 24              # resumed hour by hour, not whole days only
    fx = cx.load_source("fx", None, src)
    assert (fx.known_ms >= cx._fx_known(fx.date)).all() and (cx._fx_known(fx.date) <= now).all()
    c = cx.load_source("caps", None, src)
    assert c.date.iloc[-1] < pd.Timestamp(now, unit="ms").strftime("%Y-%m-%d")
    for kind, lag in (("bybit_fund", cx.FUND_LAG_MS), ("okx_fund", cx.FUND_LAG_MS), ("bybit_oi", cx.OI_LAG_MS), ("okx_oi", cx.OI_LAG_MS)):
        f = cx.load_source(kind, A, src)
        assert len(f) and (f.known_ms >= f.ts_ms + lag).all() and f.ts_ms.is_monotonic_increasing
    for kind in ("bybit_oi", "okx_oi"):
        assert (cx.load_source(kind, A, src).ts_ms + HOUR <= now).all()   # only hours that have ended
    # plant a different value in every stored row: a second update must not touch any of them
    kinds = [(k, None if k in cx.GLOBAL_FILES else A) for k in cx.FILES]
    for kind, asset in kinds:
        f = cx.load_source(kind, asset, src)
        num = [x for x in cx.FILES[kind] if x not in ("ts_ms", "date", "known_ms")]
        f[num] = 7.0
        cx._write(cx.path_for(kind, asset, src), f)
    h[oh.SUM_COLS] = 7.0
    oh._write(oh.path_for("hourly", A, src), h)
    before = dict(((k, a), cx.load_source(k, a, src)) for k, a in kinds)
    n0 = len(net.calls)
    cx.update(log=lambda *_: None, src_dir=src, assets=(A,))
    for (kind, asset), f in before.items():
        g = cx.load_source(kind, asset, src)
        key = cx.FILES[kind][0]
        g = g[g[key].isin(set(f[key]))].reset_index(drop=True)
        assert g.equals(f), "%s: a stored row was changed" % kind
    g = oh.load_source("hourly", A, src)
    assert g.iloc[:len(h)].equals(h)
    assert len(net.calls) - n0 <= 14                                    # a second run asks for little


def test_update_never_raises_and_a_failed_source_keeps_its_file(tmp_path, monkeypatch):
    src = str(tmp_path / "src")
    _recent(monkeypatch)
    monkeypatch.setattr(cx, "_get", FakeNet())
    monkeypatch.setattr(oh, "_get", fake_deribit)
    cx.update(log=lambda *_: None, src_dir=src, assets=(A,))
    paths = [cx.path_for(k, None if k in cx.GLOBAL_FILES else A, src) for k in cx.FILES] + [oh.path_for("hourly", A, src)]
    before = dict((p, open(p, "rb").read()) for p in paths)
    monkeypatch.setattr(cx, "_get", FakeNet(fail=("upbit", "frankfurter", "coinmetrics", "llama", "fapi", "bybit", "okx")))

    def deribit_down(url, params=None):
        raise RuntimeError("planted outage")
    monkeypatch.setattr(oh, "_get", deribit_down)
    monkeypatch.setattr(oh, "LIVE_LAG_MS", -2 * HOUR)                   # force at least one Deribit request

    def bad_log(*_):
        raise ValueError("a logger that breaks")

    out = cx.update(log=bad_log, src_dir=src, assets=(A,))
    fails = [k for k, v in out.items() if str(v).startswith("failed: ")]
    assert set(fails) >= {"optflow_BTCUSDT", "stables", "caps"}, out
    # fx: once today's ECB rate is published (17:00 Frankfurt) the first run already holds it, the second run has no
    # day left to ask for and so cannot fail: before that hour it must fail, after it it returns the same row count.
    # (The test reads the real clock; requiring "fx" in `fails` made it fail every day from 16:00 UTC to midnight.)
    assert "fx" in fails or out["fx"] == len(cx.load_source("fx", None, src)), out
    for p, blob in before.items():
        assert open(p, "rb").read() == blob, "%s changed after a failed fetch" % os.path.basename(p)


def test_live_calls_are_throttled_and_capped(tmp_path, monkeypatch):
    calls = []

    def rec(name):
        def f(*a, **k):
            calls.append((name, a[-1] if name not in ("fx", "caps", "stables") else None))
            return {"bybit_fund": 1, "bybit_oi": 1} if name == "bybit" else ({"okx_fund": 1, "okx_oi": 1} if name == "okx" else 1)
        return f
    for name in ("upbit", "perp", "bybit", "okx", "fx", "caps", "stables"):
        monkeypatch.setattr(cx, "_update_" + name, rec(name))
    hours = []
    monkeypatch.setattr(cx._oh, "update", lambda **k: hours.append(k["max_hours"]) or {"hourly_%s" % k["assets"][0]: 5})
    monkeypatch.setattr(cx, "SRC_DIR", str(tmp_path))
    first = cx.update(log=lambda *_: None, assets=(A,))
    assert len(first) == 10 and len(calls) == 7
    assert dict(calls)["upbit"] == cx.LIVE_MAX_REQ["upbit"] and hours == [cx.LIVE_MAX_REQ["optflow_hours"]]
    assert cx.update(log=lambda *_: None, assets=(A,)) == {}           # within MIN_GAP_S: nothing asked
    assert len(calls) == 7
    forced = cx.update(log=lambda *_: None, assets=(A,), force=True)
    assert len(forced) == 10 and dict(calls[7:])["upbit"] is None and hours[-1] is None   # no cap outside the live loop
    explicit = cx.update(log=lambda *_: None, src_dir=str(tmp_path / "x"), assets=(A,), sources=("upbit",))
    assert list(explicit) == ["upbit_BTCUSDT"]                          # an explicit folder always fetches


def test_a_capped_call_resumes_where_it_stopped(tmp_path, monkeypatch):
    src = str(tmp_path)
    _recent(monkeypatch, days=6)
    net = FakeNet()
    monkeypatch.setattr(cx, "_get", net)
    now = int(time.time() * 1000)
    cx._update_upbit(A, src, now, max_req=2)
    assert len(net.calls) == 2 and len(cx.load_source("upbit", A, src)) == 400
    cx._update_upbit(A, src, now)
    f = cx.load_source("upbit", A, src)
    assert (np.diff(f.ts_ms.values) == BAR).all() and f.ts_ms.iloc[-1] + BAR <= now
    assert f.ts_ms.iloc[-1] + 2 * BAR > now - 20000                    # caught up to the last closed bar
