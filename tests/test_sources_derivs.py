# -*- coding: utf-8 -*-
"""engine15/sources/derivs.py checked on planted data. No network, no real bars, no real files.

    py -3 -m pytest tests/test_sources_derivs.py -q        (from the project folder)
"""
import os
import re
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import data  # noqa: E402
from engine15.sources import derivs  # noqa: E402

A = "BTCUSDT"
BAR, HOUR = derivs.BAR_MS, derivs.HOUR_MS
CUTS = (1500, 3333, 4804, 5990)                       # 4804: its last bar closes exactly on an hour


def make_bars(n=6000, seed=1, start="2024-01-01"):
    rng = np.random.RandomState(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.002, n)))
    opn = np.concatenate([[100.0], close[:-1]])
    spread = np.abs(rng.normal(0, 0.001, n)) * close
    vol = rng.uniform(50, 150, n)
    return pd.DataFrame({"open": opn, "high": np.maximum(opn, close) + spread, "low": np.minimum(opn, close) - spread,
                         "close": close, "volume": vol, "taker_buy": vol * rng.uniform(0.3, 0.7, n)},
                        index=pd.date_range(start, periods=n, freq="15min", tz="UTC"))


def make_sources(bars, seed=7):
    """-> {kind: frame}: every source on the bars' time span, with holes, as update would store them."""
    rng = np.random.RandomState(seed)
    ts = data.to_ms(bars.index)
    n = len(ts)
    prem = 0.0002 * np.sin(np.arange(n) / 300.0) + rng.normal(0, 0.0002, n)
    out = {"basis": pd.DataFrame({"ts_ms": ts, "open": prem, "high": prem + 1e-4, "low": prem - 1e-4, "close": prem})}
    out["lsratio"] = pd.DataFrame({
        "ts_ms": ts, "global_ls": np.exp(0.5 + np.cumsum(rng.normal(0, 0.01, n))), "global_long": 0.6,
        "top_ls": np.exp(0.3 + np.cumsum(rng.normal(0, 0.01, n))), "top_long": 0.55,
        "taker_bs": 1.0, "taker_buy": rng.uniform(50, 150, n), "taker_sell": rng.uniform(50, 150, n)})
    d_oi = rng.normal(0, 0.002, n)
    r = np.abs(np.diff(np.log(bars["close"].values), prepend=np.nan))
    big = np.where(r > np.nanquantile(r, 0.95))[0]                    # the largest bars; bar j closes at stamp ts[j + 1]
    d_oi[big[big + 1 < n] + 1] -= 0.02                                # sharp drops inside them, for the proxy to see
    out["liq_oi"] = pd.DataFrame({"ts_ms": ts, "oi": 1e5 * np.exp(np.cumsum(d_oi)), "oi_value": 1e9})
    hours = np.arange(ts[0], ts[-1] + BAR, HOUR)
    v = 50.0 * np.exp(np.cumsum(rng.normal(0, 0.01, len(hours))))
    out["options_dvol"] = pd.DataFrame({"ts_ms": hours, "open": v, "high": v + 0.5, "low": v - 0.5, "close": v})
    live = np.arange(ts[0] + 123457, ts[-1], 7 * HOUR + 1111)         # read at odd moments, as update would
    out["options_live"] = pd.DataFrame({"ts_ms": live, "put_oi": 1.0, "call_oi": 1.0,
                                        "pc_ratio": rng.uniform(0.4, 1.2, len(live)),
                                        "skew_pts": rng.normal(2, 5, len(live)), "atm_iv": 50.0, "expiry_days": 30.0})
    for kind in ("basis", "lsratio", "liq_oi", "options_dvol"):       # holes: a missing stretch and scattered rows
        keep = np.ones(len(out[kind]), dtype=bool)
        keep[len(keep) // 2: len(keep) // 2 + 9] = False
        keep[rng.rand(len(keep)) < 0.01] = False
        out[kind] = out[kind][keep].reset_index(drop=True)
    return out


def write_sources(src, folder, asset=A):
    for kind, frame in src.items():
        derivs._write(derivs.path_for(kind, asset, str(folder)), frame[derivs.FILES[kind]])
    return str(folder)


def same(a, b):
    return np.array_equal(a.values.astype(float), b.values.astype(float), equal_nan=True)


def test_no_lookahead(tmp_path):
    """Cut the index off with the files on disk unchanged: every earlier row must stay exactly the same."""
    bars = make_bars()
    folder = write_sources(make_sources(bars), tmp_path)
    full = derivs.features(bars.index, A, src_dir=folder, bars=bars)
    assert full.attrs["errors"] == {}
    for col in derivs.FEATURES:                                      # the comparison below must not be zero against zero
        assert (full[col] != 0).mean() > 0.005, "%s never speaks on the planted data" % col
    for cut in CUTS:
        part = derivs.features(bars.index[:cut], A, src_dir=folder, bars=bars)
        assert list(part.columns) == list(full.columns) and len(part) == cut
        assert same(full.iloc[:cut], part), "a reading changed when the index was cut at %d" % cut
        part = derivs.features(bars.index[:cut], A, src_dir=folder, bars=bars.iloc[:cut])
        assert same(full.iloc[:cut], part), "a reading changed when the bars were cut at %d" % cut


def _not_yet_known(src, bars, cut):
    """Rewrite every stored value that was NOT yet known at the close of bar cut-1 (a superset of
    'stamped after the cut'), and every price bar after it. -> (sources, bars)."""
    t = int(data.to_ms(bars.index)[cut - 1]) + BAR
    lag = derivs.STATS_LAG_MS
    out = dict((k, f.copy()) for k, f in src.items())
    f = out["basis"]
    f.loc[f.ts_ms + BAR > t, ["open", "high", "low", "close"]] += 0.004
    f = out["lsratio"]
    f.loc[f.ts_ms + lag > t, ["global_ls", "global_long", "top_ls", "top_long"]] *= 3.0
    f.loc[f.ts_ms + BAR + lag > t, ["taker_bs", "taker_buy"]] *= 5.0
    f = out["liq_oi"]
    late = (f.ts_ms + lag > t).values
    f.loc[late, "oi"] *= np.exp(np.random.RandomState(cut).normal(0, 0.05, late.sum()))
    f = out["options_dvol"]
    f.loc[f.ts_ms + HOUR > t, ["open", "high", "low", "close"]] *= 2.0
    f = out["options_live"]
    f.loc[f.ts_ms > t, ["pc_ratio", "skew_pts"]] += 3.0
    later = bars.copy()
    later.iloc[cut:, :4] = later.iloc[cut:, :4] * 1.5
    return out, later


def test_rows_stamped_after_a_cut_do_not_reach_rows_before_it(tmp_path):
    bars = make_bars()
    src = make_sources(bars)
    base = derivs.features(bars.index, A, src_dir=write_sources(src, tmp_path / "base"), bars=bars)
    for cut in CUTS:
        changed, later = _not_yet_known(src, bars, cut)
        got = derivs.features(bars.index, A, src_dir=write_sources(changed, tmp_path / ("cut%d" % cut)), bars=later)
        assert got.attrs["errors"] == {}
        assert same(base.iloc[:cut], got.iloc[:cut]), "data not yet known at cut %d reached an earlier row" % cut
        moved = (base.iloc[cut:].fillna(0.0) != got.iloc[cut:].fillna(0.0)).any()
        for voice in ("basis", "lsratio", "liq", "options"):         # ... and the rewrite was a real one
            assert cut > 5000 or moved[derivs.GROUPS[voice][1]].all(), "the rewrite never showed in %s" % voice


def test_the_newest_known_value_is_used(tmp_path):
    """The other side of the rule: what WAS known at a close does reach that row (no needless lag)."""
    bars = make_bars()
    src = make_sources(bars, seed=11)
    cut = 4804
    ts = data.to_ms(bars.index)
    t = int(ts[cut - 1]) + BAR                                        # the close of bar cut-1, on an hour
    assert t % HOUR == 0
    lag = derivs.STATS_LAG_MS
    newest = {"basis": (t - BAR, "close", "pb_premium_pct"),          # stamp of the newest row known at t, its column,
              "options_dvol": (t - HOUR, "close", "op_dvol"),         # and the readable column it must show up in
              "liq_oi": (ts[ts + lag <= t].max(), "oi", "lq_oi"),
              "lsratio": (ts[ts + lag <= t].max(), "global_ls", "ls_global_ratio")}
    for kind, (stamp, col, _raw) in newest.items():                   # make sure those rows exist (no hole there)
        f = src[kind]
        if not (f.ts_ms == stamp).any():
            row = f.iloc[[0]].copy()
            row["ts_ms"] = stamp
            src[kind] = pd.concat([f, row]).sort_values("ts_ms").reset_index(drop=True)
    base = derivs.features(bars.index, A, src_dir=write_sources(src, tmp_path / "base"), bars=bars)
    for kind, (stamp, col, raw) in newest.items():
        f = src[kind]
        want = float(f.loc[f.ts_ms == stamp, col].iloc[0]) * (100.0 if kind == "basis" else 1.0)
        assert np.isclose(base[raw].iloc[cut - 1], want), "%s: the newest known %s is not the one used" % (kind, col)


def test_features_are_bounded_and_never_nan(tmp_path):
    bars = make_bars(n=4000)
    f = derivs.features(bars.index, A, src_dir=write_sources(make_sources(bars), tmp_path), bars=bars)
    assert list(f.columns) == derivs.FEATURES + derivs.RAW
    assert list(derivs.GROUPS) == ["basis", "lsratio", "liq", "options", "clock"]
    x = f[derivs.FEATURES]
    assert x.dtypes.eq(float).all() and np.isfinite(x.values).all()
    assert x.abs().max().max() <= 3.0
    for col in derivs.GROUPS["clock"][1] + ["op_dvol_rank"]:
        assert x[col].abs().max() <= 1.0
    assert x["ck_us_open_in"].min() >= 0.0


def test_no_files_is_no_read(tmp_path):
    bars = make_bars(n=1000)
    f = derivs.features(bars.index, A, src_dir=str(tmp_path), bars=bars)
    assert f.attrs["errors"] == {}
    quiet = [c for v in ("basis", "lsratio", "liq", "options") for c in derivs.GROUPS[v][1]]
    assert (f[quiet] == 0.0).all().all()
    assert f[["pb_premium_pct", "lq_oi", "op_dvol", "op_pc_ratio"]].isna().all().all()
    assert (f["ck_hour_cos"] != 0).any()                              # the clock needs no file


def test_a_stale_source_goes_quiet(tmp_path):
    bars = make_bars(n=5000)
    src = make_sources(bars)
    stop = int(data.to_ms(bars.index)[4000])
    src = dict((k, f[f.ts_ms < stop]) for k, f in src.items())        # every source ends at bar 4000
    f = derivs.features(bars.index, A, src_dir=write_sources(src, tmp_path), bars=bars)
    late = f.iloc[4000 + 100:]                                        # more than a day later
    for voice in ("basis", "lsratio", "liq"):
        assert (late[derivs.GROUPS[voice][1]] == 0.0).all().all(), voice
    assert (late[["op_dvol_rank", "op_dvol_24h", "op_iv_rv", "op_pcr", "op_skew"]] == 0.0).all().all()
    assert (f.iloc[3900:3990][["pb_level", "ls_global", "lq_4h", "op_dvol_rank", "op_pcr"]] != 0.0).any().all()


def test_liquidation_proxy_sign(tmp_path):
    """A sharp open-interest drop inside a large down bar reads negative (longs), inside an up bar positive (shorts)."""
    bars = make_bars(n=1500, seed=3)
    ts = data.to_ms(bars.index)
    rng = np.random.RandomState(5)
    oi = 1e5 * np.exp(np.cumsum(rng.normal(0, 0.001, len(ts) + 1)))
    stamps = np.concatenate([ts, [ts[-1] + BAR]])                     # a snapshot at every bar boundary
    down, up, calm = 1000, 1200, 1300
    c = bars["close"].values.copy()
    for i, mult in ((down, 0.97), (up, 1.03)):
        c[i:] = c[i:] * mult                                          # a 3% bar, about 15 sigma here
    for i in (down, up, calm):
        oi[i + 1:] = oi[i + 1:] * 0.97                                # OI falls 3% between the bar's open and close
    bars = bars.assign(close=c)
    derivs._write(derivs.path_for("liq_oi", A, str(tmp_path)), pd.DataFrame({"ts_ms": stamps, "oi": oi, "oi_value": 1.0}))
    f = derivs.features(bars.index, A, src_dir=str(tmp_path), bars=bars)
    seen = int(np.ceil(derivs.STATS_LAG_MS / float(BAR)))             # rows later that the snapshot at the close is known
    assert f["lq_bar"].iloc[down + seen] <= -1.0 and f["lq_bar"].iloc[up + seen] >= 1.0
    assert f["lq_bar"].iloc[calm + seen] == 0.0                       # an OI drop without a large bar is not an event
    assert f["lq_bar"].iloc[down] == 0.0 or seen == 0                 # and never before the snapshot is published
    assert f["lq_4h"].iloc[down + seen + 3] <= -1.0 and f["lq_4h"].iloc[up + seen + 3] >= 1.0
    assert ((f["lq_bar"] != 0).sum()) <= 6
    assert "proxy" in derivs.describe(f.iloc[down + seen], A)["Liquidation pressure (proxy)"].lower()


def test_clock():
    def row(stamp):                                                   # stamp = the bar's CLOSE; the clock is read there
        idx = pd.DatetimeIndex([pd.Timestamp(stamp, tz="UTC") - pd.Timedelta(minutes=15)])
        return derivs.features(idx, A, src_dir="no-such-folder", bars=make_bars(n=10)).iloc[0]

    r = row("2024-07-01 13:30")                                       # Monday 09:30 in New York (summer time)
    assert r["ck_us"] == 1.0 and r["ck_europe"] == 1.0 and r["ck_asia"] == -1.0 and r["ck_weekend"] == 0.0
    assert r["ck_us_open_in"] == 0.0 and r["ck_us_open_hours"] == 0.0
    r = row("2024-01-08 13:30")                                       # Monday 08:30 in New York (winter time)
    assert r["ck_us"] == -1.0 and np.isclose(r["ck_us_open_hours"], 1.0) and np.isclose(r["ck_us_open_in"], 1 / 24.0)
    r = row("2024-01-08 14:45")                                       # ... 09:45: open, the next open is tomorrow's
    assert r["ck_us"] == 1.0 and np.isclose(r["ck_us_open_hours"], 23.75)
    r = row("2024-07-06 02:00")                                       # Saturday: nothing is open, Monday is far
    assert r["ck_weekend"] == 1.0 and r["ck_asia"] == r["ck_europe"] == r["ck_us"] == -1.0 and r["ck_us_open_in"] == 1.0
    assert np.isclose(r["ck_us_open_hours"], 59.5)                    # Fri 22:00 New York -> Mon 09:30
    r = row("2024-07-02 01:00")                                       # Tuesday 10:00 in Tokyo
    assert r["ck_asia"] == 1.0 and r["ck_europe"] == -1.0 and r["ck_us"] == -1.0
    r = row("2024-07-03 00:00")                                       # midnight UTC: hour angle 0
    assert np.isclose(r["ck_hour_sin"], 0.0) and np.isclose(r["ck_hour_cos"], 1.0)
    r = row("2024-07-01 00:00")                                       # the week starts Monday 00:00 UTC
    assert np.isclose(r["ck_dow_sin"], 0.0) and np.isclose(r["ck_dow_cos"], 1.0)


def test_options_snapshot():
    now = int(pd.Timestamp("2026-11-10", tz="UTC").timestamp() * 1000)

    def opt(exp, strike, kind, oi, iv, fwd=100.0):
        return {"instrument_name": "BTC-%s-%s-%s" % (exp, strike, kind), "open_interest": oi, "mark_iv": iv,
                "underlying_price": fwd}

    book = [opt("11DEC26", 80, "P", 10, 60.0), opt("11DEC26", 90, "P", 20, 50.0), opt("11DEC26", 100, "P", 5, 40.0),
            opt("11DEC26", 100, "C", 30, 40.0), opt("11DEC26", 110, "C", 20, 38.0), opt("11DEC26", 120, "C", 10, 37.0),
            opt("11DEC26", 110, "P", 3, 38.0),                        # in the money: counts for open interest only
            opt("12NOV26", 90, "P", 100, 99.0), opt("25JUN27", 150, "C", 37, 45.0),
            {"instrument_name": "BTC-PERPETUAL", "open_interest": 1e9}]
    r = derivs.options_snapshot(book, now)
    assert r["put_oi"] == 138.0 and r["call_oi"] == 97.0 and np.isclose(r["pc_ratio"], 138.0 / 97.0)
    assert np.isclose(r["expiry_days"], 31 + 8 / 24.0)                # the 11 Dec expiry, 08:00 UTC
    assert np.isclose(r["skew_pts"], 50.0 - 38.0) and np.isclose(r["atm_iv"], 40.0)
    r = derivs.options_snapshot([opt("12NOV26", 90, "P", 100, 99.0), opt("12NOV26", 110, "C", 50, 80.0)], now)
    assert np.isclose(r["pc_ratio"], 2.0) and np.isnan(r["skew_pts"])  # no expiry 7 to 60 days out: no skew read


# ------------------------------------------------------------------ update, against a planted network
class FakeNet(object):
    def __init__(self, fail=()):
        self.calls, self.fail = [], fail

    def __call__(self, url, params):
        self.calls.append((url, dict(params)))
        if any(word in url for word in self.fail):
            raise RuntimeError("planted outage")
        now = int(time.time() * 1000)
        if "premiumIndexKlines" in url:
            first = -(-params["startTime"] // BAR) * BAR
            return [[t, "0.0001", "0.0002", "0.0", "0.00015", "0", t + BAR - 1, "0", 9, "0", "0", "0"]
                    for t in range(first, min(first + params["limit"] * BAR, now + 1), BAR)]
        if "/futures/data/" in url:
            first = -(-params["startTime"] // BAR) * BAR
            taker = "taker" in url
            return [{"timestamp": t, "longShortRatio": "1.5", "longAccount": "0.6", "buySellRatio": "1.1",
                     "buyVol": "11", "sellVol": "10", "sumOpenInterest": "100", "sumOpenInterestValue": "1000"}
                    for t in range(first, params["endTime"] + 1, BAR) if t + (BAR if taker else 0) <= now]
        if "get_volatility_index_data" in url:
            first = -(-params["start_timestamp"] // HOUR) * HOUR
            return {"result": {"data": [[t, 50.0, 51.0, 49.0, 50.5] for t in range(first, params["end_timestamp"] + 1, HOUR)
                                        if t <= now], "continuation": None}}
        if "get_book_summary_by_currency" in url:
            return {"result": [{"instrument_name": "%s-1JAN30-100-P" % params["currency"], "open_interest": 6.0},
                               {"instrument_name": "%s-1JAN30-100-C" % params["currency"], "open_interest": 10.0}]}
        raise AssertionError("unexpected request %s" % url)


def _seed(folder, days=2.0):
    """Files whose last rows are a couple of days old, as if update last ran then. -> last stamp."""
    last = (int(time.time() * 1000) - int(days * 86400000)) // HOUR * HOUR
    stamps = np.arange(last - 40 * BAR, last + 1, BAR)
    frames = {"basis": {"open": 7.0, "high": 7.0, "low": 7.0, "close": 7.0},
              "lsratio": {"global_ls": 7.0, "global_long": 7.0, "top_ls": 7.0, "top_long": 7.0,
                          "taker_bs": 7.0, "taker_buy": 7.0, "taker_sell": 7.0},
              "liq_oi": {"oi": 7.0, "oi_value": 7.0},
              "options_dvol": {"open": 7.0, "high": 7.0, "low": 7.0, "close": 7.0}}
    for kind, cols in frames.items():
        ts = stamps[stamps % HOUR == 0] if kind == "options_dvol" else stamps
        derivs._write(derivs.path_for(kind, A, folder), pd.DataFrame(dict({"ts_ms": ts}, **cols))[derivs.FILES[kind]])
    return int(last)


def test_update_is_incremental_and_keeps_what_it_had(tmp_path, monkeypatch):
    folder = str(tmp_path)
    last = _seed(folder)
    net = FakeNet()
    monkeypatch.setattr(derivs, "_get", net)
    out = derivs.update(log=lambda *_: None, src_dir=folder, assets=(A,))
    assert list(out) == ["%s_%s" % (k, A) for k in ("basis", "lsratio", "liq", "options", "options_live")]
    assert all(isinstance(v, int) for v in out.values()), out
    for url, params in net.calls:                                     # nothing older than the files was asked for
        start = params.get("startTime", params.get("start_timestamp"))
        assert start is None or start > last, url
    now = int(time.time() * 1000)
    for kind in ("basis", "lsratio", "liq_oi", "options_dvol"):
        f = derivs.load_source(kind, A, folder)
        step = HOUR if kind == "options_dvol" else BAR
        assert (f.iloc[:, 1][f.ts_ms <= last] == 7.0).all() and (f.ts_ms <= last).sum() == (41 if step == BAR else 11)
        assert (np.diff(f.ts_ms.values) == step).all(), "%s has a hole or a duplicate" % kind
        assert now - 2 * step - 60000 <= f.ts_ms.iloc[-1] <= now      # up to date ...
        assert not os.path.exists(derivs.path_for(kind, A, folder) + ".tmp")
    assert derivs.load_source("basis", A, folder).ts_ms.iloc[-1] + BAR <= now          # ... closed bars only
    assert derivs.load_source("options_dvol", A, folder).ts_ms.iloc[-1] + HOUR <= now  # ... ended hours only
    ls = derivs.load_source("lsratio", A, folder)
    assert ls.taker_buy.dropna().index[-1] <= ls.global_ls.dropna().index[-1]
    live = derivs.load_source("options_live", A, folder)
    assert len(live) == 1 and np.isclose(live.pc_ratio.iloc[0], 0.6)
    n_calls = len(net.calls)
    again = derivs.update(log=lambda *_: None, src_dir=folder, assets=(A,))
    assert again["basis_" + A] == out["basis_" + A] and again["options_live_" + A] == 2
    assert len(net.calls) - n_calls <= 7                              # a second run asks for almost nothing


def test_update_never_raises_and_a_failed_source_keeps_its_file(tmp_path, monkeypatch):
    folder = str(tmp_path)
    _seed(folder)
    before = dict((k, open(derivs.path_for(k, A, folder), "rb").read())
                  for k in ("basis", "lsratio", "liq_oi", "options_dvol"))
    monkeypatch.setattr(derivs, "_get", FakeNet(fail=("binance", "deribit")))

    def bad_log(*_):
        raise ValueError("a logger that breaks")

    out = derivs.update(log=bad_log, src_dir=folder, assets=(A,))
    assert len(out) == 5 and all(str(v).startswith("failed: ") for v in out.values()), out
    for kind, raw in before.items():
        assert open(derivs.path_for(kind, A, folder), "rb").read() == raw
    monkeypatch.setattr(derivs, "_get", FakeNet(fail=("takerlongshortRatio", "deribit")))
    out = derivs.update(log=lambda *_: None, src_dir=folder, assets=(A,))
    assert isinstance(out["basis_" + A], int) and isinstance(out["liq_" + A], int)
    assert out["lsratio_" + A].startswith("failed: taker")           # one endpoint down: the other two are still kept
    ls = derivs.load_source("lsratio", A, folder)
    assert ls.global_ls.notna().sum() > ls.taker_buy.notna().sum() == 41


def test_describe(tmp_path):
    bars = make_bars(n=4000)
    f = derivs.features(bars.index, A, src_dir=write_sources(make_sources(bars), tmp_path), bars=bars)
    titles = [title for title, _ in derivs.GROUPS.values()]
    for i in (0, 2000, 3999):
        said = derivs.describe(f.iloc[i], A)
        assert list(said) == titles
        assert all(isinstance(s, str) and len(s) > 20 and not re.search(r"nan", s) for s in said.values()), said
        assert "proxy" in said["Liquidation pressure (proxy)"].lower()
    empty = derivs.describe(derivs.features(bars.index[:5], A, src_dir="no-such-folder", bars=bars).iloc[0], A)
    assert list(empty) == titles and "No premium read" in empty["Perp basis and premium"]
    assert list(derivs.describe({}, "ETHUSDT")) == titles             # a bare dict does not break it
