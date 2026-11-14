# -*- coding: utf-8 -*-
"""engine15/sources/flows.py checked on planted data. No network, no real files.

    py -3 -m pytest tests/test_sources_flows.py -q        (from the project folder)
"""
import io
import os
import re
import sys
import time
import zipfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import data  # noqa: E402
from engine15.sources import cot, flows  # noqa: E402

A, E = "BTCUSDT", "ETHUSDT"
BAR, HOUR, DAY = flows.BAR_MS, flows.HOUR_MS, flows.DAY_MS
START = "2023-01-01"
N_DAYS = 420                                          # long enough for the 365-day windows to speak
OLD = 10 ** 13                                        # a "first seen" far in the future of every row: backfill


def make_index(n_days=N_DAYS):
    return pd.date_range(START, periods=n_days * 96, freq="15min", tz="UTC")


def make_sources(n_days=N_DAYS, seed=3):
    """-> {(kind, asset): frame} as update would store them after a backfill, with holes."""
    rng = np.random.RandomState(seed)
    t0 = int(pd.Timestamp(START, tz="UTC").value // 10 ** 6)
    out = {}
    for asset in (A, E):
        ts = np.arange(t0, t0 + n_days * DAY, BAR, dtype="int64")
        n = len(ts)
        m = pd.DataFrame({"ts_ms": ts, "oi": 1e5 * np.exp(np.cumsum(rng.normal(0, 0.002, n))), "oi_value": 1e9,
                          "top_acct_ls": np.exp(0.3 + np.cumsum(rng.normal(0, 0.003, n))),
                          "top_pos_ls": np.exp(0.2 + np.cumsum(rng.normal(0, 0.003, n))),
                          "global_ls": np.exp(0.5 + np.cumsum(rng.normal(0, 0.003, n))),
                          "taker_ls": np.exp(rng.normal(0, 0.2, n))})
        m["known_ms"] = (ts // DAY * DAY + DAY + flows.METRICS_LAG_MS).astype("int64")
        keep = np.ones(n, dtype=bool)
        keep[n // 3: n // 3 + 96 * 2] = False                         # two missing archive days
        keep[rng.rand(n) < 0.01] = False
        out[("metrics", asset)] = m[keep].reset_index(drop=True)
        hours = np.arange(t0, t0 + n_days * DAY, HOUR, dtype="int64")
        b = pd.DataFrame({"ts_ms": hours, "long": 5e4 * np.exp(np.cumsum(rng.normal(0, 0.003, len(hours)))),
                          "short": 3e3 * np.exp(np.cumsum(rng.normal(0, 0.006, len(hours))))})
        b["known_ms"] = hours + flows.BFX_LAG_MS
        out[("bitfinex", asset)] = b[rng.rand(len(b)) > 0.01].reset_index(drop=True)
        tues = pd.date_range(START, periods=n_days // 7, freq="W-TUE")
        c = pd.DataFrame({"date": tues.strftime("%Y-%m-%d"), "oi": 2e4 + rng.normal(0, 500, len(tues)),
                          "lev_long": 5e3 + np.cumsum(rng.normal(0, 200, len(tues))),
                          "lev_short": 9e3 + np.cumsum(rng.normal(0, 200, len(tues))),
                          "am_long": 4e3, "am_short": 2e3, "dealer_long": 6e3, "dealer_short": 5e3})
        c["known_ms"] = [cot.release_ms(d) for d in c["date"]]
        out[("cme", asset)] = c
        days = pd.date_range(START, periods=n_days, freq="D")
        o = pd.DataFrame({"date": days.strftime("%Y-%m-%d")})
        k = len(o)
        o["CapMVRVCur"] = np.exp(0.3 + np.cumsum(rng.normal(0, 0.02, k)))
        o["AdrActCnt"] = 8e5 * np.exp(np.cumsum(rng.normal(0, 0.03, k)))
        o["FlowInExNtv"] = rng.uniform(2e4, 4e4, k)
        o["FlowOutExNtv"] = rng.uniform(2e4, 4e4, k)
        o["SplyExNtv"] = 2.7e6 + np.cumsum(rng.normal(0, 2e3, k))
        o["HashRate"] = 6e8 * np.exp(np.cumsum(rng.normal(0.001, 0.03, k)))
        o["IssTotUSD"], o["TxCnt"], o["CapMrktCurUSD"] = 3e7, 5e5, 1e12
        o["known_ms"] = flows._day_ms(o["date"]) + DAY + flows.ONCHAIN_LAG_MS
        out[("onchain", asset)] = o[rng.rand(k) > 0.01].reset_index(drop=True)
    return out


def write_sources(src, folder):
    for (kind, asset), frame in src.items():
        flows._write(flows.path_for(kind, asset, str(folder)), frame[flows.FILES[kind]])
    return str(folder)


def same(a, b):
    return np.array_equal(a.values.astype(float), b.values.astype(float), equal_nan=True)


CUTS = (96 * 200 + 47, 96 * 300, 96 * 365 + 50, 96 * 410 - 1)


def test_no_lookahead_cutting_the_index(tmp_path):
    idx = make_index()
    folder = write_sources(make_sources(), tmp_path)
    full = flows.features(idx, A, src_dir=folder)
    assert full.attrs["errors"] == {}
    for col in flows.FEATURES:                                       # the comparison must not be zero against zero
        assert (full[col] != 0).mean() > 0.05, "%s never speaks on the planted data" % col
    for cut in CUTS:
        part = flows.features(idx[:cut], A, src_dir=folder)
        assert list(part.columns) == list(full.columns) and len(part) == cut
        assert same(full.iloc[:cut], part), "a reading changed when the index was cut at %d" % cut


def _rewrite_unknown(src, t):
    """Rewrite every stored value NOT yet known at instant t."""
    out = dict((k, f.copy()) for k, f in src.items())
    for (kind, asset), f in out.items():
        late = (f["known_ms"] > t).values
        num = [c for c in flows.FILES[kind] if c not in ("ts_ms", "date", "known_ms")]
        f.loc[late, num] = f.loc[late, num].values * np.exp(np.random.RandomState(7).normal(0, 0.3, (late.sum(), len(num))))
    return out


def test_values_not_yet_known_do_not_reach_earlier_rows(tmp_path):
    idx = make_index()
    src = make_sources()
    base_e = flows.features(idx, E, src_dir=write_sources(src, tmp_path / "base"))
    base = flows.features(idx, A, src_dir=str(tmp_path / "base"))
    close = data.to_ms(idx) + BAR
    for cut in CUTS:
        t = int(close[cut - 1])
        folder = write_sources(_rewrite_unknown(src, t), tmp_path / ("cut%d" % cut))
        for asset, b in ((A, base), (E, base_e)):
            got = flows.features(idx, asset, src_dir=folder)
            assert got.attrs["errors"] == {}
            assert same(b.iloc[:cut], got.iloc[:cut]), "data not yet known at cut %d reached an earlier row (%s)" % (cut, asset)
            if cut < 96 * 400:                                       # ... and the rewrite was a real one, in every card
                moved = (b.iloc[cut:] != got.iloc[cut:]).any()
                for card in flows.GROUPS:
                    assert moved[flows.GROUPS[card][1]].any(), "the rewrite never showed in %s" % card


def test_known_at_times_are_respected_exactly(tmp_path):
    """One planted value per source: it must appear at the first close at or after its known-at time, not before."""
    src = make_sources()
    folder = write_sources(src, tmp_path)
    for kind, raw, col, mult in (("metrics", "fl_oi", "oi", 1.0), ("bitfinex", "fl_bfx_long", "long", 1.0),
                                 ("cme", "fl_cme_lev_net_pct", None, None), ("onchain", "fl_mvrv", "CapMVRVCur", 1.0)):
        f = src[(kind, A)]
        j = len(f) // 2
        if kind == "metrics":                                         # the day's last snapshot carries the daily oi
            day = f["ts_ms"].iloc[j] // DAY * DAY
            j = int(np.where(f["ts_ms"] // DAY * DAY == day)[0][-1])
        k = int(f["known_ms"].iloc[j])
        if kind == "cme":
            oi = f["oi"].iloc[j]
            want = 100.0 * (f["lev_long"].iloc[j] - f["lev_short"].iloc[j]) / oi
        else:
            want = float(f[col].iloc[j]) * mult
        closes = np.array([k - 1, k, k + 1], dtype="int64")
        x = flows.inputs(closes, A, src_dir=folder)
        assert not np.isclose(x[raw].iloc[0], want), "%s: a value was used before it was known" % kind
        assert np.isclose(x[raw].iloc[1], want) and np.isclose(x[raw].iloc[2], want), "%s: not used once known" % kind


def test_lags_match_the_registered_rules():
    """The constants are the ones registered in research/HYPOTHESES.md H39 (rounded-up measurements)."""
    assert flows.METRICS_LAG_MS == 12 * HOUR and flows.ONCHAIN_LAG_MS == 6 * HOUR
    assert flows.BFX_LAG_MS == HOUR + 5 * 60000
    d = flows._day_ms(["2024-03-05"])[0]
    # backfill (first seen long after): the nominal time; a live fetch (seen soon after): the later of the two
    nominal = d + DAY + flows.METRICS_LAG_MS
    assert flows.known_at([nominal], nominal + 30 * DAY)[0] == nominal
    assert flows.known_at([nominal], nominal + 2 * HOUR)[0] == nominal + 2 * HOUR
    assert flows.known_at([nominal], nominal - 2 * HOUR)[0] == nominal


def test_cutoff_drops_rows_known_at_or_after_it(tmp_path):
    idx = make_index()
    src = make_sources()
    folder = write_sources(src, tmp_path)
    close = data.to_ms(idx) + BAR
    seal = int(close[96 * 300])
    a = flows.inputs(close, A, src_dir=folder, cutoff_ms=seal)
    b = flows.inputs(close, A, src_dir=write_sources(_rewrite_unknown(src, seal - 1), tmp_path / "w"), cutoff_ms=seal)
    assert same(a, b)                                                 # nothing known at/after the seal matters at all
    assert a.iloc[96 * 300 + 400:][["fl_oi_7d", "fl_mvrv_z", "fl_bfx_14d"]].isna().all().all()   # goes quiet after


def test_features_bounded_never_nan_and_no_files_is_no_read(tmp_path):
    idx = make_index()
    f = flows.features(idx, A, src_dir=write_sources(make_sources(), tmp_path))
    assert list(f.columns) == flows.FEATURES + flows.RAW
    x = f[flows.FEATURES]
    assert x.dtypes.eq(float).all() and np.isfinite(x.values).all() and x.abs().max().max() <= 3.0
    empty = flows.features(idx[:500], A, src_dir=str(tmp_path / "nothing"))
    assert empty.attrs["errors"] == {}
    assert (empty[flows.FEATURES] == 0.0).all().all() and empty[flows.RAW].isna().all().all()


def test_hash_ribbon_is_btc_for_both_coins(tmp_path):
    idx = make_index()
    folder = write_sources(make_sources(), tmp_path)
    b, e = flows.features(idx, A, src_dir=folder), flows.features(idx, E, src_dir=folder)
    assert same(b[["fl_hash_ribbon", "fl_hashrate_btc"]], e[["fl_hash_ribbon", "fl_hashrate_btc"]])
    assert not same(b[["fl_mvrv_z"]], e[["fl_mvrv_z"]])


def _zip(rows):
    text = "create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio," \
           "sum_toptrader_long_short_ratio,count_long_short_ratio,sum_taker_long_short_vol_ratio\n" + "\n".join(rows)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("BTCUSDT-metrics-2024-01-01.csv", text)
    return buf.getvalue()


def test_parse_metrics_zip():
    rows = ["2024-01-01 00:00:00,BTCUSDT,100,1000,1.1,1.2,1.3,2.0",
            "2024-01-01 00:00:00,BTCUSDT,100,1000,1.1,1.2,1.3,2.0",       # the archive repeats rows sometimes
            "2024-01-01 00:05:00,BTCUSDT,101,1000,1.1,1.2,1.3,0.5",
            "2024-01-01 00:10:00,BTCUSDT,102,1000,1.1,1.2,1.3,1.0",
            "2024-01-01 00:15:00,BTCUSDT,103,1000,1.4,1.5,1.6,4.0",
            "2024-01-01 00:17:00,BTCUSDT,999,1000,9.9,9.9,9.9,9.9"]       # off the 5-minute grid: dropped
    d = flows.parse_metrics_zip(_zip(rows))
    t0 = int(pd.Timestamp("2024-01-01", tz="UTC").value // 10 ** 6)
    assert list(d["ts_ms"]) == [t0, t0 + BAR]
    assert list(d["oi"]) == [100.0, 103.0] and np.isclose(d["global_ls"].iloc[1], 1.6)
    assert np.isclose(d["taker_ls"].iloc[0], 1.0)                      # geometric mean of 2.0, 0.5, 1.0
    assert np.isclose(d["taker_ls"].iloc[1], 4.0)
    try:
        flows.parse_metrics_zip(b"not a zip")
        raise AssertionError("a broken file was accepted")
    except zipfile.BadZipFile:
        pass


# ------------------------------------------------------------------ update, against a planted network
class Resp(object):
    def __init__(self, status, payload=None, content=b""):
        self.status_code, self._p, self.content = status, payload, content

    def json(self):
        return self._p


class FakeNet(object):
    def __init__(self, fail=()):
        self.calls, self.fail = [], fail

    def __call__(self, url, params=None):
        self.calls.append((url, dict(params or {})))
        if any(w in url for w in self.fail):
            raise RuntimeError("planted outage")
        now = int(time.time() * 1000)
        if "data.binance.vision" in url:
            day = re.search(r"(\d{4}-\d{2}-\d{2})\.zip$", url).group(1)
            if day == "2026-01-03":
                return Resp(404)
            rows = ["%s %02d:%02d:00,BTCUSDT,%d,1000,1.1,1.2,1.3,1.0" % (day, h, m, 100 + h) for h in range(24)
                    for m in range(0, 60, 5)]
            return Resp(200, content=_zip(rows))
        if "bitfinex" in url:
            first = -(-params["start"] // HOUR) * HOUR
            return Resp(200, [[t, 10.0 if "long" in url else 2.0] for t in range(first, min(params["end"], now) + 1, HOUR)][:10000])
        if "cftc" in url:
            return Resp(200, [{"report_date_as_yyyy_mm_dd": "2026-01-06T00:00:00.000", "open_interest_all": "100",
                               "lev_money_positions_long": "10", "lev_money_positions_short": "30",
                               "asset_mgr_positions_long": "5", "asset_mgr_positions_short": "1",
                               "dealer_positions_long_all": "1", "dealer_positions_short_all": "1"}])
        if "coinmetrics" in url:
            days = pd.date_range(params["start_time"], pd.Timestamp(now, unit="ms").strftime("%Y-%m-%d"), freq="D")
            return Resp(200, {"data": [dict([("asset", "btc"), ("time", d.strftime("%Y-%m-%dT00:00:00.000000000Z"))] +
                                            [(m, "1.5") for m in flows.CM_METRICS]) for d in days]})
        raise AssertionError("unexpected request %s" % url)


def test_update_is_incremental_never_changes_stored_rows(tmp_path, monkeypatch):
    src, raw = str(tmp_path / "src"), str(tmp_path / "raw")
    now = int(time.time() * 1000)
    monkeypatch.setitem(flows.METRICS_START, A, pd.Timestamp(now - 6 * DAY, unit="ms").strftime("%Y-%m-%d"))
    monkeypatch.setattr(flows, "BFX_START_MS", (now - 3 * DAY) // HOUR * HOUR)
    monkeypatch.setattr(flows, "CM_START", pd.Timestamp(now - 40 * DAY, unit="ms").strftime("%Y-%m-%d"))
    net = FakeNet()
    monkeypatch.setattr(flows, "_get", net)
    out = flows.update(log=lambda *_: None, src_dir=src, raw_dir=raw, assets=(A,))
    assert all(isinstance(v, int) for v in out.values()), out
    m = flows.load_source("metrics", A, src)
    assert len(m) == 6 * 96 and (np.diff(m.ts_ms.values) == BAR).all()          # 6 whole days, nothing of today
    assert (m["known_ms"] >= m["ts_ms"] // DAY * DAY + DAY + flows.METRICS_LAG_MS).all()
    assert len(os.listdir(os.path.join(raw, A))) == 6 and not any(f.endswith(".tmp") for f in os.listdir(os.path.join(raw, A)))
    b = flows.load_source("bitfinex", A, src)
    assert (b["ts_ms"] + HOUR <= now).all() and (b["known_ms"] >= b["ts_ms"] + flows.BFX_LAG_MS).all()
    o = flows.load_source("onchain", A, src)
    assert o["date"].iloc[-1] < pd.Timestamp(now, unit="ms").strftime("%Y-%m-%d")   # complete days only
    assert (o["known_ms"] >= flows._day_ms(o["date"]) + DAY + flows.ONCHAIN_LAG_MS).all()
    c = flows.load_source("cme", A, src)
    assert len(c) == 1 and c["known_ms"].iloc[0] >= cot.release_ms("2026-01-06")
    # plant a different value in every stored row: a second update must not touch any of them
    for kind in flows.FILES:
        f = flows.load_source(kind, A, src)
        num = [x for x in flows.FILES[kind] if x not in ("ts_ms", "date", "known_ms")]
        f[num] = 7.0
        flows._write(flows.path_for(kind, A, src), f)
    before = dict((k, flows.load_source(k, A, src)) for k in flows.FILES)
    n_calls = len(net.calls)
    flows.update(log=lambda *_: None, src_dir=src, raw_dir=raw, assets=(A,))
    for kind, f in before.items():
        g = flows.load_source(kind, A, src)
        key = flows.FILES[kind][0]
        g = g[g[key].isin(set(f[key]))].reset_index(drop=True)
        assert g.equals(f), "%s: a stored row was changed" % kind
    assert len(net.calls) - n_calls <= 12                              # a second run asks for little


def test_update_never_raises_and_a_failed_source_keeps_its_file(tmp_path, monkeypatch):
    src, raw = str(tmp_path / "src"), str(tmp_path / "raw")
    now = int(time.time() * 1000)
    monkeypatch.setitem(flows.METRICS_START, A, pd.Timestamp(now - 4 * DAY, unit="ms").strftime("%Y-%m-%d"))
    monkeypatch.setattr(flows, "BFX_START_MS", (now - 2 * DAY) // HOUR * HOUR)
    monkeypatch.setattr(flows, "CM_START", pd.Timestamp(now - 10 * DAY, unit="ms").strftime("%Y-%m-%d"))
    monkeypatch.setattr(flows, "_get", FakeNet())
    flows.update(log=lambda *_: None, src_dir=src, raw_dir=raw, assets=(A,))
    before = dict((k, open(flows.path_for(k, A, src), "rb").read()) for k in flows.FILES)
    monkeypatch.setattr(flows, "_get", FakeNet(fail=("binance", "bitfinex", "cftc", "coinmetrics")))

    def bad_log(*_):
        raise ValueError("a logger that breaks")

    out = flows.update(log=bad_log, src_dir=src, raw_dir=raw, assets=(A,))
    assert len(out) == 4
    assert all(str(v).startswith("failed: ") for k, v in out.items() if not k.startswith("metrics")), out
    for kind, blob in before.items():
        assert open(flows.path_for(kind, A, src), "rb").read() == blob


def test_a_404_in_the_archive_is_skipped_and_remembered(tmp_path, monkeypatch):
    src, raw = str(tmp_path / "src"), str(tmp_path / "raw")
    monkeypatch.setitem(flows.METRICS_START, A, "2026-01-01")
    monkeypatch.setattr(flows, "_get", FakeNet())
    now = int(pd.Timestamp("2026-01-08 05:00", tz="UTC").value // 10 ** 6)
    n = flows._update_metrics(A, src, raw, now)
    assert n == 6 * 96                                                 # 1-7 Jan minus the missing 3 Jan
    with open(os.path.join(raw, A, "_not_in_archive.txt")) as fh:
        assert fh.read().split() == ["2026-01-03"]


def test_describe(tmp_path):
    idx = make_index()
    f = flows.features(idx, A, src_dir=write_sources(make_sources(), tmp_path))
    titles = [t for t, _ in flows.GROUPS.values()]
    for i in (0, 96 * 200, len(idx) - 1):
        said = flows.describe(f.iloc[i], A)
        assert list(said) == titles
        assert all(isinstance(s, str) and len(s) > 20 and not re.search(r"\bnan\b", s) for s in said.values()), said
    assert list(flows.describe({}, E)) == titles


def test_wired_crypto_only_and_throttled(tmp_path, monkeypatch):
    """think15-v5.1.1: flows is a live source for BTC and ETH only, and the live loop's calls are throttled."""
    from engine15 import sources, evidence
    assert "flows" in sources.MODULES
    assert flows in evidence.SOURCES
    for v in flows.GROUPS:
        assert evidence.voice_applies(v, "BTCUSDT") and evidence.voice_applies(v, "ETHUSDT")
        assert not any(evidence.voice_applies(v, a) for a in ("XAUUSD", "SPX", "USDJPY", "WTI"))
    assert flows not in evidence.sources_for("XAUUSD") and flows in evidence.sources_for("BTCUSDT")
    calls = []
    for name in ("_update_metrics", "_update_bitfinex", "_update_cme", "_update_onchain"):
        monkeypatch.setattr(flows, name, (lambda n: (lambda *a, **k: calls.append(n) or 1))(name))
    monkeypatch.setattr(flows, "SRC_DIR", str(tmp_path))
    first = flows.update(log=lambda *_: None, assets=("BTCUSDT",))
    assert len(first) == 4 and len(calls) == 4
    assert flows.update(log=lambda *_: None, assets=("BTCUSDT",)) == {}          # within MIN_GAP_S: nothing asked
    assert len(calls) == 4
    assert len(flows.update(log=lambda *_: None, assets=("BTCUSDT",), force=True)) == 4
    assert len(calls) == 8

