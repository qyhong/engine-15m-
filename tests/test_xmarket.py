# -*- coding: utf-8 -*-
"""sources/xmarket: the five cards for gold, silver, USDJPY and the S&P 500, checked on planted files.
No network: every fetch is faked.

    py -3 -m pytest tests/test_xmarket.py -q        (from the project folder)
"""
import io
import json
import os
import re
import sys
import zipfile

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import data  # noqa: E402
from engine15.sources import xmarket as x  # noqa: E402

H, D, BAR = 3600000, 86400000, 900000
ASSETS = ("XAUUSD", "XAGUSD", "USDJPY", "SPX")
BAR_START, N_BARS = "2019-01-01", 26000                       # about 270 days of 15m bars


def ms_of(text):
    return int(pd.Timestamp(text, tz="UTC").timestamp() * 1000)


def make_bars(seed, start=BAR_START, n=N_BARS, level=100.0):
    rng = np.random.RandomState(seed)
    idx = pd.date_range(start, periods=n, freq="15min", tz="UTC")
    close = level * np.exp(np.cumsum(rng.normal(0, 0.0015, n)))
    opn = np.r_[level, close[:-1]]
    df = pd.DataFrame({"open": opn, "high": np.maximum(opn, close), "low": np.minimum(opn, close), "close": close,
                       "volume": 1.0, "taker_buy": np.nan}, index=idx)
    df.index.name = "open_time"
    keep = rng.uniform(size=n) > 0.02                          # a few missing bars
    keep[(idx.weekday == 5)] = False                          # no Saturday bars
    return df[keep]


def bdays(start="2018-01-01", end="2020-01-15"):
    return [d.strftime("%Y-%m-%d") for d in pd.bdate_range(start, end)]


def walk(rng, n, level, sd):
    return level * np.exp(np.cumsum(rng.normal(0, sd, n)))


def plant(folder, seed=0):
    """Every xm_* file, 2018 to mid-January 2020, random but plausible."""
    rng = np.random.RandomState(seed)
    os.makedirs(folder, exist_ok=True)
    days = bdays()
    n = len(days)
    levels = {"vix": (16, 0.06), "vix9d": (15, 0.08), "vix3m": (18, 0.04), "gvz": (14, 0.05), "dxy": (95, 0.004),
              "copper": (3.0, 0.012), "goldfut": (1300, 0.008), "spy": (270, 0.01), "rsp": (100, 0.01),
              "iwm": (150, 0.013), "xlk": (70, 0.013), "xlu": (55, 0.009), "smh": (100, 0.017), "gld": (125, 0.008),
              "slv": (15, 0.015)}
    for key, (lvl, sd) in levels.items():
        keep = rng.uniform(size=n) > 0.02
        pd.DataFrame({"date": np.array(days)[keep], "close": walk(rng, n, lvl, sd)[keep],
                      "volume": rng.uniform(1e6, 1e7, n)[keep]}).to_csv(x.yahoo_path(key, folder), index=False)
    for key, lvl in (("y2", 2.5), ("y10", 2.8), ("real10", 0.8)):
        keep = rng.uniform(size=n) > 0.03
        v = lvl + np.cumsum(rng.normal(0, 0.04, n))
        pd.DataFrame({"date": np.array(days)[keep], "value": np.round(v[keep], 2)}).to_csv(x.fred_path(key, folder), index=False)
    keep = rng.uniform(size=n) > 0.05
    pd.DataFrame({"date": np.array(days)[keep], "jp2": (-0.1 + np.cumsum(rng.normal(0, 0.01, n)))[keep],
                  "jp10": (0.05 + np.cumsum(rng.normal(0, 0.01, n)))[keep]}).to_csv(x.jgb_path(folder), index=False)
    t = 800 + np.cumsum(rng.normal(0, 2, n))
    pd.DataFrame({"date": days, "tonnes": t, "ounces": t * x.TROY_OZ_PER_TONNE, "close": walk(rng, n, 125, 0.008),
                  "prem_pct": rng.normal(0, 0.1, n), "volume": rng.uniform(5e6, 1e7, n)}).to_csv(x.gld_path(folder), index=False)
    sd = days[-60:]
    pd.DataFrame({"date": sd, "ounces": 3.6e8 + np.cumsum(rng.normal(0, 1e6, len(sd))),
                  "fetched_ms": x.known_ms("slv", sd) + rng.randint(0, 6, len(sd)) * H}).to_csv(x.slv_path(folder), index=False)


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    folder = str(tmp_path_factory.mktemp("xm"))
    plant(folder)
    bars = {"XAUUSD": make_bars(1, level=1300.0), "XAGUSD": make_bars(2, level=16.0),
            "USDJPY": make_bars(3, level=110.0), "SPX": make_bars(4, level=2700.0)}
    return folder, bars


def truncate_world(folder, out, cut_ms, bars):
    """Copies of every file holding only what was public at cut_ms; bars closed by cut_ms."""
    os.makedirs(out, exist_ok=True)
    specs = [(x.yahoo_path(k, folder), x.yahoo_path(k, out), x.YCOLS, "yahoo", x.YAHOO[k][1]) for k in x.YAHOO]
    specs += [(x.fred_path(k, folder), x.fred_path(k, out), x.FCOLS, "fred", None) for k in x.FRED]
    specs += [(x.jgb_path(folder), x.jgb_path(out), x.JCOLS, "jgb", None),
              (x.gld_path(folder), x.gld_path(out), x.GCOLS, "gld", None)]
    for src, dst, cols, kind, spec in specs:
        d = pd.read_csv(src, dtype={"date": str}, float_precision="round_trip")
        d[x.known_ms(kind, d["date"], spec) <= cut_ms].to_csv(dst, index=False)
    s = pd.read_csv(x.slv_path(folder), dtype={"date": str}, float_precision="round_trip")
    s[np.maximum(x.known_ms("slv", s["date"]), s["fetched_ms"].values) <= cut_ms].to_csv(x.slv_path(out), index=False)
    return dict((a, b[data.to_ms(b.index) + BAR <= cut_ms]) for a, b in bars.items())


def same(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return a.shape == b.shape and bool(np.all((a == b) | (np.isnan(a) & np.isnan(b))))


# ------------------------------------------------------------------ the publication rules
def test_known_times():
    # a Cboe close (16:30 New York) in winter and in summer
    assert x.known_ms("yahoo", ["2019-03-05"], (16, 30))[0] == ms_of("2019-03-05 21:30")
    assert x.known_ms("yahoo", ["2019-07-02"], (16, 30))[0] == ms_of("2019-07-02 20:30")
    # stock ETFs 16:15, futures 17:15
    assert x.known_ms("yahoo", ["2019-07-02"], x.YAHOO["spy"][1])[0] == ms_of("2019-07-02 20:15")
    assert x.known_ms("yahoo", ["2019-12-02"], x.YAHOO["copper"][1])[0] == ms_of("2019-12-02 22:15")
    # FRED: 17:00 New York on the next federal business day
    assert x.known_ms("fred", ["2019-07-05"])[0] == ms_of("2019-07-08 21:00")          # Friday -> Monday
    assert x.known_ms("fred", ["2019-07-03"])[0] == ms_of("2019-07-05 21:00")          # over Independence Day
    assert x.known_ms("fred", ["2019-10-11"])[0] == ms_of("2019-10-15 21:00")          # over Columbus Day
    assert x.known_ms("fred", ["2019-11-08"])[0] == ms_of("2019-11-12 22:00")          # over Veterans Day (winter)
    # Japan: 00:00 UTC next day; GLD / SLV: 12:00 UTC next day
    assert x.known_ms("jgb", ["2019-05-07"])[0] == ms_of("2019-05-08 00:00")
    assert x.known_ms("gld", ["2019-05-07"])[0] == ms_of("2019-05-08 12:00")


def test_a_close_is_seen_only_once_final(world):
    folder, bars = world
    vix = pd.read_csv(x.yahoo_path("vix", folder), dtype={"date": str}).set_index("date")["close"]
    day, prev = "2019-03-05", vix.index[vix.index.get_loc("2019-03-05") - 1]
    idx = pd.DatetimeIndex([pd.Timestamp("2019-03-05 21:00", tz="UTC"), pd.Timestamp("2019-03-05 21:15", tz="UTC")])
    f = x.features(idx, "SPX", src_dir=folder, bars=bars, strict=True)
    assert f["vx_vix"].iloc[0] == pytest.approx(vix[prev])          # closes 21:15 UTC: still the day before
    assert f["vx_vix"].iloc[1] == pytest.approx(vix[day])           # closes 21:30 UTC: the day's close is public


def test_fred_yield_waits_for_the_next_business_day(world):
    folder, bars = world
    y = pd.read_csv(x.fred_path("y10", folder), dtype={"date": str}).set_index("date")["value"]
    d = "2019-07-03"
    assert d in y.index
    prev = y.index[y.index.get_loc(d) - 1]
    idx = pd.DatetimeIndex([pd.Timestamp("2019-07-04 21:00", tz="UTC"), pd.Timestamp("2019-07-05 20:45", tz="UTC")])
    f = x.features(idx, "USDJPY", src_dir=folder, bars=bars, strict=True)
    assert f["rt_y10"].iloc[0] == pytest.approx(y[prev])            # 4 July: FRED does not post
    assert f["rt_y10"].iloc[1] == pytest.approx(y[d])               # 5 July 17:00 New York


# ------------------------------------------------------------------ no look-ahead
@pytest.mark.parametrize("asset", ASSETS)
def test_no_lookahead_truncation(world, tmp_path, asset):
    """Cut every file and the bars at a moment T: every row that closed by T is unchanged."""
    folder, bars = world
    idx = bars[asset].index
    full = x.features(idx, asset, src_dir=folder, bars=bars, strict=True)
    for k, cut in enumerate(("2019-04-17 20:45", "2019-07-05 21:00", "2019-09-02 13:15")):
        cut_ms = ms_of(cut)
        out = str(tmp_path / ("cut%d" % k))
        tb = truncate_world(folder, out, cut_ms, bars)
        sub = idx[data.to_ms(idx) + BAR <= cut_ms]
        part = x.features(sub, asset, src_dir=out, bars=tb, strict=True)
        ref = full.loc[sub]
        for col in x.FEATURES + x.RAW:
            assert same(part[col].values, ref[col].values), "%s %s changed when the future was cut at %s" % (asset, col, cut)


def test_future_edits_do_not_reach_the_past(world, tmp_path):
    folder, bars = world
    out = str(tmp_path / "edited")
    os.makedirs(out)
    cut_ms = ms_of("2019-06-14 00:00")
    for name in os.listdir(folder):
        d = pd.read_csv(os.path.join(folder, name), dtype={"date": str}, float_precision="round_trip")
        later = pd.to_datetime(d["date"], utc=True) >= pd.Timestamp("2019-06-10", tz="UTC")
        for c in d.columns:
            if c not in ("date", "fetched_ms"):
                d.loc[later, c] = d.loc[later, c] * 1.37
        d.to_csv(os.path.join(out, name), index=False)
    b2 = dict((a, b.copy()) for a, b in bars.items())
    for a in b2:
        late = data.to_ms(b2[a].index) + BAR > cut_ms
        b2[a].loc[late, "close"] *= 1.5
    for asset in ASSETS:
        idx = bars[asset].index
        idx = idx[data.to_ms(idx) + BAR <= ms_of("2019-06-10 20:00")]       # before any edited value was public
        a = x.features(idx, asset, src_dir=folder, bars=bars, strict=True)
        b = x.features(idx, asset, src_dir=out, bars=b2, strict=True)
        for col in x.FEATURES + x.RAW:
            assert same(a[col].values, b[col].values), (asset, col)


# ------------------------------------------------------------------ the contract
def test_features_contract(world):
    folder, bars = world
    for asset in ASSETS:
        f = x.features(bars[asset].index, asset, src_dir=folder, bars=bars, strict=True)
        assert list(f.columns) == x.FEATURES + x.RAW
        assert not f[x.FEATURES].isna().any().any()
        assert (f[x.FEATURES].abs() <= 1.0).all().all()
        late = f.index >= pd.Timestamp("2019-06-01", tz="UTC")
        for voice, (_title, feats) in x.GROUPS.items():
            live = (f.loc[late, feats] != 0).any().any()
            assert live == (asset in x.APPLIES[voice]), (asset, voice)
        assert f.attrs["errors"] == {}
    btc = x.features(bars["SPX"].index[:100], "BTCUSDT", src_dir=folder, bars=bars)
    assert (btc[x.FEATURES] == 0).all().all()
    assert set(x.APPLIES) == set(x.GROUPS)
    assert len(set(x.FEATURES)) == len(x.FEATURES) and not set(x.FEATURES) & set(x.RAW)


def test_gold_reading_only_for_metals_and_gap_only_for_yen(world):
    folder, bars = world
    idx = bars["SPX"].index[-500:]
    spx = x.features(idx, "SPX", src_dir=folder, bars=bars)
    jpy = x.features(idx, "USDJPY", src_dir=folder, bars=bars)
    gold = x.features(idx, "XAUUSD", src_dir=folder, bars=bars)
    assert (spx["vx_gold"] == 0).all() and (gold["vx_gold"] != 0).any()
    assert (spx["rt_gap_5d"] == 0).all() and (gold["rt_gap_5d"] == 0).all() and (jpy["rt_gap_5d"] != 0).any()


def test_missing_and_broken_files_are_no_read(tmp_path, world):
    _folder, bars = world
    empty = str(tmp_path / "empty")
    os.makedirs(empty)
    none = {"XAUUSD": bars["XAUUSD"].iloc[:0], "XAGUSD": bars["XAGUSD"].iloc[:0]}
    f = x.features(bars["XAUUSD"].index[-200:], "XAUUSD", src_dir=empty, bars=none)
    assert (f[x.FEATURES] == 0).all().all() and f[x.RAW].isna().all().all()
    with open(x.yahoo_path("vix", empty), "w") as fh:
        fh.write("this is not,a csv\n\x00\x01")
    f = x.features(bars["SPX"].index[-50:], "SPX", src_dir=empty, bars=none)
    assert not f[x.FEATURES].isna().any().any()


def test_gold_silver_ratio_and_lead(world):
    folder, bars = world
    f = x.features(bars["XAUUSD"].index, "XAUUSD", src_dir=folder, bars=bars, strict=True)
    au, ag = bars["XAUUSD"]["close"], bars["XAGUSD"]["close"]
    both = au.index.intersection(ag.index)
    t = both[-1]
    assert f.loc[t, "mt_gsr"] == pytest.approx(au[t] / ag[t])
    j = pd.DataFrame({"au": au, "ag": ag}).dropna()
    k = 16
    want = 100.0 * (j["ag"].iloc[-1] / j["ag"].iloc[-1 - k] - j["au"].iloc[-1] / j["au"].iloc[-1 - k])
    assert f.loc[t, "mt_lead_4h_pp"] == pytest.approx(want)
    p = f["mt_gsr_pct"].dropna()
    assert len(p) and p.between(0, 100).all()


def test_describe_and_facts(world):
    folder, bars = world
    for asset in ASSETS:
        f = x.features(bars[asset].index[-300:], asset, src_dir=folder, bars=bars)
        row = f.iloc[-1]
        words, rows = x.describe(row, asset), x.facts(row, asset)
        titles = [x.GROUPS[v][0] for v in x.GROUPS if asset in x.APPLIES[v]]
        assert list(words) == titles and list(rows) == titles
        for title, s in words.items():
            assert isinstance(s, str) and len(s) > 20 and not re.search(r"\bnan\b", s.lower()) and not s.startswith("No read"), (asset, title, s)
        for title, lst in rows.items():
            assert lst and all(len(r) == 2 and not re.search(r"\bnan\b", str(r[1]).lower()) for r in lst)
    blank = pd.Series(np.nan, index=x.FEATURES + x.RAW, name=pd.Timestamp("2019-05-01", tz="UTC"))
    for asset in ASSETS:
        for title, s in x.describe(blank, asset).items():
            assert not re.search(r"\bnan\b", s.lower())
        x.facts(blank, asset)
    assert x.describe(blank, "BTCUSDT") == {}


def test_breadth_states():
    r = lambda **k: pd.Series(dict(("eb_%s_20d_pct" % a, v) for a, v in k.items()))       # noqa: E731
    assert x.breadth_state(r(spy=4, rsp=-2, iwm=-3, xlk=1)) == "narrow rally"
    assert x.breadth_state(r(spy=4, rsp=1, iwm=2, xlk=1)) == "broad rally"
    assert x.breadth_state(r(spy=-4, rsp=0.5, iwm=-1, xlk=-5)) == "risk-off rotation"
    assert x.breadth_state(r(spy=-4, rsp=2, iwm=1, xlk=0)) == "selloff led by the biggest names"
    assert x.breadth_state(r(spy=0.2, rsp=0.1, iwm=0, xlk=0)) == "mixed"


# ------------------------------------------------------------------ parsers
def test_parse_yahoo_daily():
    ts = [int(pd.Timestamp(s, tz="UTC").timestamp()) for s in
          ("2019-03-04 14:30", "2019-03-05 14:30", "2019-03-09 05:00", "2019-03-05 20:59", "2019-03-06 14:30")]
    payload = {"chart": {"result": [{"timestamp": ts, "indicators": {"quote": [{
        "close": [10.0, 11.0, None, 11.5, 12.0], "volume": [1, 2, 3, 4, None]}]}}]}}
    d = x.parse_yahoo_daily(payload)
    assert list(d["date"]) == ["2019-03-04", "2019-03-05", "2019-03-06"]
    assert list(d["close"]) == [10.0, 11.5, 12.0]                     # a repeated date: the later stamp wins
    # a stamp at 01:00 UTC is still the previous New York day
    p2 = {"chart": {"result": [{"timestamp": [int(pd.Timestamp("2019-03-06 01:00", tz="UTC").timestamp())],
                                "indicators": {"quote": [{"close": [5.0]}]}}]}}
    assert list(x.parse_yahoo_daily(p2)["date"]) == ["2019-03-05"]


def test_parse_fred_and_mof():
    d = x.parse_fred_csv("observation_date,DGS2\n2019-01-01,.\n2019-01-02,2.50\n2019-01-03,2.39\n")
    assert list(d["date"]) == ["2019-01-02", "2019-01-03"] and list(d["value"]) == [2.50, 2.39]
    d = x.parse_fred_csv("DATE,DGS2\n2019-01-02,2.5\n")
    assert len(d) == 1
    mof = ("Interest Rate,,,,,,,,,,,,,,,(Unit : %)\nDate,1Y,2Y,3Y,4Y,5Y,6Y,7Y,8Y,9Y,10Y,15Y,20Y,25Y,30Y,40Y\n"
           "1974/9/24,10.327,9.362,8.83,8.515,8.348,8.29,8.24,8.121,8.127,-,-,-,-,-,-\n"
           "2026/11/5,1.658,1.86,1.953,2.108,2.21,2.299,2.396,2.536,2.669,2.806,3.336,3.64,3.949,3.91\n"
           "2026/11/9,1.595,1.778,1.871,2.011,2.115,2.198,2.302,2.446,2.584,2.724,3.289,3.604,3.939,3.911,3.941\n"
           ",,,,,,,,,,,,,,,\n\"  If you cannot download the latest csv data...\",,,,\n")
    d = x.parse_mof_csv(mof)
    assert list(d["date"]) == ["1974-09-24", "2026-11-05", "2026-11-09"]
    assert d["jp2"].tolist() == [9.362, 1.86, 1.778]
    assert np.isnan(d["jp10"].iloc[0]) and d["jp10"].iloc[2] == 2.724


def _xlsx(rows):
    strings, sheet = [], []
    def s(v):
        if v not in strings:
            strings.append(v)
        return strings.index(v)
    for i, r in enumerate(rows, 1):
        cells = []
        for j, v in enumerate(r):
            ref = "%s%d" % ("ABCDEFGHIJK"[j], i)
            if isinstance(v, str):
                cells.append('<c r="%s" t="s"><v>%d</v></c>' % (ref, s(v)))
            else:
                cells.append('<c r="%s"><v>%r</v></c>' % (ref, v))
        sheet.append('<row r="%d">%s</row>' % (i, "".join(cells)))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/sharedStrings.xml", "<sst>%s</sst>" % "".join("<si><t>%s</t></si>" % v for v in strings))
        z.writestr("xl/worksheets/sheet1.xml", "<worksheet><sheetData><row r=\"1\"><c r=\"A1\"><v>0</v></c></row></sheetData></worksheet>")
        z.writestr("xl/worksheets/sheet2.xml", "<worksheet><sheetData>%s</sheetData></worksheet>" % "".join(sheet))
    return buf.getvalue()


def test_parse_gld_xlsx():
    head = ["Date", "Closing Price", "Ounces of Gold per Share", "NAV/Share at 10:30am NYT",
            "Indicative Price per Share at 4:15pm NYT", "Mid point of bid/ask spread at 4:15pm NYT",
            "Premium/Discount of GLD Mid Point vs Indicative Value of GLD at 4:15pm NYT", "Daily Share Volume",
            "Total Ounces of Gold in the Trust", "Tonnes of Gold", "Total Net Asset Value in the Trust"]
    rows = [head, ["06-Nov-2026", 372.52, 0.0916, 371.1, 372.57, 372.57, -0.0008, 7769739, 33481010.44, 1041.37, 1.3e11],
            ["07-Nov-2026", "US Holiday", "US Holiday", "", "", "", "", "", "", "", ""],
            ["09-Nov-2026", 379.53, 0.0916, 377.27, 379.33, 379.51, 0.048, 7568607, 33517665.76, 1042.51, 1.3e11]]
    d = x.parse_gld_xlsx(_xlsx(rows))
    assert list(d["date"]) == ["2026-11-06", "2026-11-09"]
    assert d["tonnes"].tolist() == [1041.37, 1042.51] and d["prem_pct"].tolist() == [-0.0008, 0.048]
    assert d["volume"].iloc[1] == 7568607


def test_parse_slv_page():
    js = '"ounces":{"visible":true,"label":"Ounces in Trust","formattedValue":"504,630,049.40","sortOrder":49,' \
         '"formattedAsOfDate":"Nov 09, 2026","name":"ounces"}'
    assert x.parse_slv_page("<html>" + js + "</html>") == ("2026-11-09", 504630049.40)
    assert x.parse_slv_page("<div data='" + js.replace('"', "&quot;") + "'>") == ("2026-11-09", 504630049.40)
    assert x.parse_slv_page("<html>nothing here</html>") is None


# ------------------------------------------------------------------ fetching (faked)
class FakeResp(object):
    def __init__(self, payload=None, text="", content=b"", status=200):
        self._payload, self.text, self.content, self.status_code = payload, text, content, status

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP %d" % self.status_code)


def test_update_never_raises_and_keeps_old_files(tmp_path, monkeypatch):
    import requests
    folder = str(tmp_path / "src")
    plant(folder)
    before = dict((n, open(os.path.join(folder, n), "rb").read()) for n in os.listdir(folder))

    def boom(self, *a, **k):
        raise requests.ConnectionError("no network in tests")
    monkeypatch.setattr(requests.Session, "get", boom)
    monkeypatch.setattr(x, "OTHER_PAUSE", 0.0)
    monkeypatch.setattr(x, "YAHOO_PAUSE", 0.0)
    got = x.update(log=None, force=True, src_dir=folder)
    assert len(got) == len(x.YAHOO) + len(x.FRED) + 3
    assert all(str(v).startswith("failed") for v in got.values())
    for n, b in before.items():
        assert open(os.path.join(folder, n), "rb").read() == b
    # a second call within RETRY_MS does not ask again
    again = x.update(log=None, src_dir=folder)
    assert all(v == "fresh" for v in again.values())


def test_yahoo_job_stores_only_final_closes(tmp_path, monkeypatch):
    folder = str(tmp_path / "y")
    os.makedirs(folder)
    monkeypatch.setattr(x, "YAHOO_PAUSE", 0.0)
    ts = [int(pd.Timestamp(s, tz="UTC").timestamp()) for s in ("2019-03-04 14:30", "2019-03-05 14:30")]
    payload = {"chart": {"result": [{"timestamp": ts, "indicators": {"quote": [{"close": [10.0, 11.0], "volume": [1, 2]}]}}]}}

    class Sess(object):
        def get(self, url, params=None, headers=None, timeout=None):
            assert timeout <= 30 and "@" not in str(headers)
            return FakeResp(payload)
    now = ms_of("2019-03-05 21:00")                                   # 16:00 New York: the 5 March close is not final yet
    assert x._job_yahoo(Sess(), "spy", folder, now) == 1
    assert list(pd.read_csv(x.yahoo_path("spy", folder))["date"]) == ["2019-03-04"]
    assert x._job_yahoo(Sess(), "spy", folder, ms_of("2019-03-05 21:15")) == 2


def test_schedule():
    last = "2019-03-05"                                               # a Tuesday
    nxt = x._next_known("yahoo", last, (16, 30))
    assert nxt == ms_of("2019-03-06 21:30")
    assert not x._due("yahoo", (16, 30), last, nxt - 2 * H, nxt - H)  # nothing new yet
    assert x._due("yahoo", (16, 30), last, nxt - 2 * H, nxt)          # the next close is public
    assert not x._due("yahoo", (16, 30), last, nxt - 60000, nxt)      # tried a minute ago: wait
    assert x._due("yahoo", (16, 30), None, 0, nxt)                    # no file: fetch
    fri = x._next_known("fred", "2019-03-08")                          # Friday's yield posts Monday; Monday's posts Tuesday
    assert fri == ms_of("2019-03-12 21:00")


def test_full_history_is_fast_enough(world):
    import time
    folder, bars = world
    t = time.time()
    x.features(bars["XAUUSD"].index, "XAUUSD", src_dir=folder, bars=bars)
    assert time.time() - t < 5.0
