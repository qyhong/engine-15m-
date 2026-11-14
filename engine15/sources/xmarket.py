# -*- coding: utf-8 -*-
"""xmarket -- five cards for the four non-crypto markets (gold, silver, USDJPY, S&P 500).

  volx       Volatility gauges            Cboe VIX, VIX9D, VIX3M, gold volatility GVZ (Yahoo daily closes)
  rates      Rates and the dollar         US 2y / 10y / 10y real yields (FRED: DGS2, DGS10, DFII10), the dollar
                                          index (Yahoo DX-Y.NYB), Japan 2y / 10y government bond yields (Japan
                                          Ministry of Finance, daily) for the US-Japan yield gap
  metals     Metals ratios                gold/silver ratio and which metal led, from this project's own 15m
                                          bars; copper (Yahoo HG=F) and the copper/gold ratio (HG=F / GC=F)
  eqbreadth  Stock-market breadth         RSP/SPY, IWM/SPY, XLK/XLU, SMH/SPY (Yahoo daily closes)
  goldetf    Gold and silver ETF holdings GLD tonnes and premium (SPDR's own daily archive, 2004 on); SLV ounces
                                          (iShares product page: today's figure only, archived from the day this
                                          module first ran); GLD and SLV dollar volume (Yahoo) as a flow proxy

Everything is kept under data/sources/xm_*.csv (written atomically). update() extends the files;
features() only reads them. docs/SOURCES_xmarket.md is the plain-English account.

THE ONE RULE (known at the 15m close; tests/test_xmarket.py cuts the future off and checks):
  a Yahoo daily close for New York date D     is used from D at the series' close time in New York plus
                                              15 minutes (stock ETFs 16:15, Cboe indices 16:30, futures
                                              and the dollar index 17:15);
  a FRED yield for date D                     from 17:00 New York on the next US federal business day
                                              (FRED posts the H.15 yields the next business day);
  a Japan bond yield for Tokyo date D         from 00:00 UTC of D + 1 (09:00 Tokyo the next morning);
  GLD holdings for US trading date D          from 12:00 UTC of D + 1 (the same rule as the crypto ETF flows);
  an SLV holdings snapshot "as of D"          from 12:00 UTC of D + 1, and never before it was fetched;
  15m readings (gold/silver ratio, lead)      from the close of the bar they use (closed bars only).
Each reading is computed on its own series' grid with backward-looking windows, then handed to a 15m
row by an as-of join on the time it became known. A value older than its MAX_AGE is "no read".

Readings (FEATURES) are roughly in [-1, 1]; 0.0 = no read, never NaN. RAW columns are readable
numbers in natural units (NaN = no read). Nothing here is claimed to predict anything: these are data
points the engine learns from and the owner reads.
"""
import datetime as dt
import html
import io
import json
import os
import re
import time
import zipfile
from collections import OrderedDict

import numpy as np
import pandas as pd

from .. import data
from .. import extdata
from ..config import CFG, DATA_DIR

ALL4 = ("XAUUSD", "XAGUSD", "USDJPY", "SPX")
METALS = ("XAUUSD", "XAGUSD")

GROUPS = OrderedDict([
    ("volx", ("Volatility gauges", ["vx_level", "vx_front", "vx_curve", "vx_chg5", "vx_gold"])),
    ("rates", ("Rates and the dollar", ["rt_y2_5d", "rt_y10_5d", "rt_real_5d", "rt_dxy_5d", "rt_gap_5d"])),
    ("metals", ("Metals ratios", ["mt_gsr_level", "mt_gsr_trend", "mt_lead_1h", "mt_lead_4h", "mt_lead_24h",
                                  "mt_cugold_20d"])),
    ("eqbreadth", ("Stock-market breadth", ["eb_rsp_5d", "eb_rsp_20d", "eb_iwm_5d", "eb_iwm_20d", "eb_tech_5d",
                                            "eb_tech_20d", "eb_semis_20d"])),
    ("goldetf", ("Gold and silver ETF holdings", ["ge_gld_1d", "ge_gld_5d", "ge_gld_prem", "ge_slv_5d",
                                                  "ge_gld_dvol", "ge_slv_dvol"])),
])
APPLIES = {"volx": ALL4, "rates": ALL4, "metals": METALS, "eqbreadth": ("SPX",), "goldetf": METALS}
FEATURES = [f for _t, _fs in GROUPS.values() for f in _fs]
RAW = [
    # volx
    "vx_vix", "vx_vix_pct", "vx_vix_chg5", "vx_vix9d", "vx_vix3m", "vx_9d_ratio", "vx_3m_ratio",
    "vx_gvz", "vx_gvz_pct", "vx_gvz_chg5",
    # rates
    "rt_y2", "rt_y2_d1_bp", "rt_y2_d5_bp", "rt_y10", "rt_y10_d1_bp", "rt_y10_d5_bp", "rt_real10", "rt_real_d1_bp",
    "rt_real_d5_bp", "rt_curve_bp", "rt_y_age_d", "rt_dxy", "rt_dxy_d1_pct", "rt_dxy_d5_pct",
    "rt_jp2", "rt_jp10", "rt_gap2", "rt_gap2_d5_bp", "rt_gap10", "rt_gap10_d5_bp",
    # metals
    "mt_gsr", "mt_gsr_pct", "mt_gsr_chg5d_pct", "mt_lead_1h_pp", "mt_lead_4h_pp", "mt_lead_24h_pp",
    "mt_copper", "mt_copper_d1_pct", "mt_copper_d5_pct", "mt_cugold", "mt_cugold_pct", "mt_cugold_chg20_pct",
    # eqbreadth
    "eb_spy", "eb_spy_5d_pct", "eb_spy_20d_pct", "eb_rsp_spy", "eb_rsp_5d_pct", "eb_rsp_20d_pct",
    "eb_iwm_spy", "eb_iwm_5d_pct", "eb_iwm_20d_pct", "eb_xlk_xlu", "eb_xlk_5d_pct", "eb_xlk_20d_pct",
    "eb_smh_spy", "eb_smh_5d_pct", "eb_smh_20d_pct",
    # goldetf
    "ge_gld_tonnes", "ge_gld_d1_t", "ge_gld_d5_t", "ge_gld_d5_pct", "ge_gld_prem_pct", "ge_gld_age_d",
    "ge_slv_moz", "ge_slv_d1_moz", "ge_slv_d5_moz", "ge_slv_age_d",
    "ge_gld_dvol_musd", "ge_gld_dvol_x", "ge_slv_dvol_musd", "ge_slv_dvol_x",
]

# ---- where things live (module attributes so a test can point them at a temp folder)
SRC_DIR = os.path.join(DATA_DIR, "sources")

# ---- constants, declared once (docs/SOURCES_xmarket.md says why)
BAR_MS, H_MS, D_MS, MIN_MS = CFG["bar_ms"], 3600000, 86400000, 60000
FETCH_FROM = "2018-01-01"            # a year of warm-up before the 2019 history, for the one-year percentiles
PCT_DAYS, PCT_MIN = 252, 126         # percentiles: against the last 252 trading days (126 to start)
DAILY_MAX_AGE = 6 * D_MS             # a daily value goes silent 6 days after it became known (holiday + weekend)
JGB_MAX_AGE = 10 * D_MS              # Japan's Golden Week can close the bond market for five weekdays
BAR_MAX_AGE = H_MS                   # a 15m reading: one hour
GSR_TREND_BARS = 460                 # gold/silver trend: about five trading days of 15m bars (23 trading hours a day)
LEAD_BARS = (("1h", 4), ("4h", 16), ("24h", 96))   # lead windows in trading bars
SPREAD_SD_BARS, SPREAD_SD_MIN = 2880, 480          # silver-minus-gold 15m volatility: 30 trading days (5 to start)
# scales: a move of this size reads 1.0 (clipped to [-1, 1])
VIX_CHG5_UNIT = 0.30                 # ln(VIX / VIX 5 days ago) of 0.30 (about +35%)
FRONT_MID, CURVE_MID, RATIO_HALF = 0.95, 0.90, 0.15   # VIX9D/VIX centred on 0.95, VIX/VIX3M on 0.90, +-0.15 = +-1
YIELD_5D_BP, REAL_5D_BP, GAP_5D_BP = 25.0, 20.0, 25.0
DXY_5D_PCT = 1.5
GSR_TREND_UNIT = 0.05                # ln change of 5% in the ratio over five days
CUGOLD_20D_UNIT = 0.10
PAIR_UNITS = {"rsp": (1.5, 3.0), "iwm": (2.5, 5.0), "tech": (5.0, 10.0), "semis": (5.0, 10.0)}  # % over 5d, 20d
GLD_1D_PCT, GLD_5D_PCT, GLD_PREM_PCT, SLV_5D_PCT = 0.5, 1.5, 0.15, 1.5
DVOL_DAYS = 20                       # dollar volume against its 20-day median; 3x the median reads 1.0
TIMEOUT = 30
YAHOO_PAUSE = 1.0                    # seconds between Yahoo requests (shared with extdata's own clock)
OTHER_PAUSE = 1.0
RETRY_MS = 30 * MIN_MS               # a job is tried at most every 30 minutes ...
SAFETY_MS = 12 * H_MS                # ... and at least every 12 hours, even when nothing new is due
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/130.0.0.0 Safari/537.36",
              "Accept": "text/html,application/xhtml+xml,application/json,text/csv;q=0.9,*/*;q=0.8",
              "Accept-Language": "en-US,en;q=0.9"}
# FRED drops connections that carry a browser User-Agent from a non-browser client (tested 11 Nov 2026);
# it answers the plain default of the requests library, which names no person and no address.
FRED_HEADERS = {}

# key -> (Yahoo symbol, (hour, minute) New York when its daily close counts as known)
YAHOO = OrderedDict([
    ("vix", ("^VIX", (16, 30))), ("vix9d", ("^VIX9D", (16, 30))), ("vix3m", ("^VIX3M", (16, 30))),
    ("gvz", ("^GVZ", (16, 30))),
    ("dxy", ("DX-Y.NYB", (17, 15))), ("copper", ("HG=F", (17, 15))), ("goldfut", ("GC=F", (17, 15))),
    ("spy", ("SPY", (16, 15))), ("rsp", ("RSP", (16, 15))), ("iwm", ("IWM", (16, 15))), ("xlk", ("XLK", (16, 15))),
    ("xlu", ("XLU", (16, 15))), ("smh", ("SMH", (16, 15))), ("gld", ("GLD", (16, 15))), ("slv", ("SLV", (16, 15))),
])
FRED = OrderedDict([("y2", "DGS2"), ("y10", "DGS10"), ("real10", "DFII10")])
YAHOO_URL = extdata.YF_URL
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
MOF_URLS = ("https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv",
            "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv")
GLD_URL = "https://api.spdrgoldshares.com/api/v1/historical-archive?product=gld&exchange=NYSE&lang=en"
SLV_URL = "https://www.ishares.com/us/products/239855/ishares-silver-trust-fund"

YCOLS = ["date", "close", "volume"]
FCOLS = ["date", "value"]
JCOLS = ["date", "jp2", "jp10"]
GCOLS = ["date", "tonnes", "ounces", "close", "prem_pct", "volume"]
SCOLS = ["date", "ounces", "fetched_ms"]
TROY_OZ_PER_TONNE = 32150.7466


# ------------------------------------------------------------------ files
def _path(name, src_dir=None):
    return os.path.join(src_dir or SRC_DIR, "xm_%s.csv" % name)


def yahoo_path(key, src_dir=None):
    return _path("y_" + key, src_dir)


def fred_path(key, src_dir=None):
    return _path("fred_" + key, src_dir)


def jgb_path(src_dir=None):
    return _path("jgb", src_dir)


def gld_path(src_dir=None):
    return _path("gld_holdings", src_dir)


def slv_path(src_dir=None):
    return _path("slv_holdings", src_dir)


def state_path(src_dir=None):
    return os.path.join(src_dir or SRC_DIR, "xm_state.json")


def _read(path, cols):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return pd.DataFrame(columns=cols)
    try:
        d = pd.read_csv(path, float_precision="round_trip", dtype={"date": str})
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=cols)
    for c in cols:
        if c not in d.columns:
            d[c] = np.nan
    return d[cols]


def _write(df, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


# ------------------------------------------------------------------ clocks
def _day_ms(dates):
    """'YYYY-MM-DD' strings -> epoch ms of 00:00 UTC that day."""
    dates = list(dates)
    if not dates:
        return np.array([], dtype="int64")
    return data.to_ms(pd.DatetimeIndex(pd.to_datetime(pd.Index(dates, dtype=str), format="%Y-%m-%d", utc=True)))


def _ny_wall_ms(dates, hh, mm):
    """New York wall time hh:mm on each date -> epoch ms (US daylight-saving rule, no tz database needed)."""
    local = _day_ms(dates) + hh * H_MS + mm * MIN_MS
    return local - extdata._manual_offset_ms(local + 5 * H_MS, extdata.NY)


def _ny_date(ts_s):
    """Epoch seconds -> the New York calendar date, 'YYYY-MM-DD'."""
    ms = np.asarray(ts_s, dtype="int64") * 1000
    loc = ms + extdata._manual_offset_ms(ms, extdata.NY)
    return pd.to_datetime(loc, unit="ms").strftime("%Y-%m-%d")


def _nth(year, month, weekday, n):
    if n > 0:
        first = dt.date(year, month, 1)
        return first + dt.timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))
    last = dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
    return last - dt.timedelta(days=(last.weekday() - weekday) % 7)


def _observed(day):
    return day - dt.timedelta(days=1) if day.weekday() == 5 else day + dt.timedelta(days=1) if day.weekday() == 6 else day


_HOL = {}


def _holidays(cal, year):
    """cal 'nyse': NYSE full closures; 'fed': US federal holidays (the Board, hence FRED's H.15 yields);
    'none': weekends only."""
    key = (cal, year)
    if key not in _HOL:
        if cal == "nyse":
            _HOL[key] = extdata.nyse_days(year)[0]
        elif cal == "fed":
            s = {_observed(dt.date(year, 1, 1)), _nth(year, 1, 0, 3), _nth(year, 2, 0, 3), _nth(year, 5, 0, -1),
                 _observed(dt.date(year, 7, 4)), _nth(year, 9, 0, 1), _nth(year, 10, 0, 2),
                 _observed(dt.date(year, 11, 11)), _nth(year, 11, 3, 4), _observed(dt.date(year, 12, 25))}
            if year >= 2021:
                s.add(_observed(dt.date(year, 6, 19)))
            _HOL[key] = s
        else:
            _HOL[key] = set()
    return _HOL[key]


def _next_bday(date_str, cal):
    d = dt.date.fromisoformat(str(date_str)[:10]) + dt.timedelta(days=1)
    while d.weekday() >= 5 or d in _holidays(cal, d.year):
        d += dt.timedelta(days=1)
    return d.isoformat()


def known_ms(kind, dates, spec=None):
    """THE PUBLICATION RULE: the epoch ms at which the value for each date became public."""
    dates = [str(x)[:10] for x in dates]
    if not dates:
        return np.array([], dtype="int64")
    if kind == "yahoo":
        hh, mm = spec
        return _ny_wall_ms(dates, hh, mm)
    if kind == "fred":
        return _ny_wall_ms([_next_bday(x, "fed") for x in dates], 17, 0)
    if kind == "jgb":
        return _day_ms(dates) + D_MS
    if kind in ("gld", "slv"):
        return _day_ms(dates) + D_MS + 12 * H_MS
    raise ValueError(kind)


def _next_known(kind, last_date, spec=None):
    """When the value after `last_date` should be public (for the fetch schedule)."""
    cal = "fed" if kind == "fred" else "none" if kind == "jgb" else "nyse"
    return int(known_ms(kind, [_next_bday(last_date, cal)], spec)[0])


def _now_ms():
    return int(time.time() * 1000)


# ------------------------------------------------------------------ loaders (features side)
def _daily(path, cols, kind, spec=None):
    """A daily file -> frame indexed by date string (sorted, unique), value columns + known_ms."""
    d = _read(path, cols)
    d = d[d["date"].notna()].copy()
    if not len(d):
        out = pd.DataFrame(columns=cols[1:] + ["known_ms"])
        out.index.name = "date"
        return out
    d["date"] = d["date"].astype(str).str[:10]
    d = d.drop_duplicates("date", keep="last").sort_values("date").set_index("date")
    out = d[cols[1:]].apply(pd.to_numeric, errors="coerce").astype(float)
    k = known_ms(kind, out.index, spec)
    if kind == "slv":
        k = np.maximum(k, out["fetched_ms"].fillna(0).values.astype("int64"))
    out["known_ms"] = k
    return out


def _ydaily(key, src_dir):
    d = _daily(yahoo_path(key, src_dir), YCOLS, "yahoo", YAHOO[key][1])
    return d[d["close"] > 0] if len(d) else d


def _fdaily(key, src_dir):
    d = _daily(fred_path(key, src_dir), FCOLS, "fred")
    return d.dropna(subset=["value"]) if len(d) else d


def _pair(a, b, ca="close", cb="close"):
    """Two daily frames -> one frame of the dates both have: a, b, known_ms (the later of the two)."""
    j = pd.DataFrame({"a": a[ca], "ka": a["known_ms"]}).join(pd.DataFrame({"b": b[cb], "kb": b["known_ms"]}), how="inner")
    j = j.dropna(subset=["a", "b"])
    return pd.DataFrame({"a": j["a"], "b": j["b"], "known_ms": np.maximum(j["ka"].values, j["kb"].values)}, index=j.index)


def _pct_rank(s):
    return 100.0 * s.rolling(PCT_DAYS, min_periods=PCT_MIN).rank(pct=True)


def _clip(x, lim=1.0):
    return np.clip(x, -lim, lim)


def _asof(known, values, close_ms, max_age):
    """THE NO-LOOKAHEAD JOIN. For each 15m close: the last value known at or before it (NaN if
    none, or if that value is older than max_age)."""
    values = np.asarray(values, dtype=float)
    out = np.full(len(close_ms), np.nan)
    known = np.asarray(known, dtype="int64")
    have = ~np.isnan(values)
    if not have.any():
        return out
    order = np.argsort(known[have], kind="stable")
    k_ms, v = known[have][order], values[have][order]
    k = np.searchsorted(k_ms, close_ms, side="right") - 1
    kk = np.maximum(k, 0)
    hit = (k >= 0) & ((close_ms - k_ms[kk]) <= max_age)
    out[hit] = v[kk[hit]]
    return out


def _put(out, close_ms, frame, max_age, known=None):
    """Every column of `frame` onto the 15m rows by the as-of join on frame.known_ms."""
    if frame is None or not len(frame):
        return
    k = frame["known_ms"].values if known is None else known
    for col in frame.columns:
        if col != "known_ms":
            out[col] = _asof(k, frame[col].values, close_ms, max_age)


def _age_days(out, close_ms, frame, col, max_age):
    """Days from the observation date (00:00 UTC) to the row's close, for the value the row uses."""
    if frame is None or not len(frame):
        return
    out[col] = (close_ms - _asof(frame["known_ms"].values, _day_ms(frame.index), close_ms, max_age)) / D_MS


# ------------------------------------------------------------------ the five cards
def _volx(out, close_ms, asset, src_dir, bars):
    vix = _ydaily("vix", src_dir)
    if len(vix):
        c = vix["close"]
        pct = _pct_rank(c)
        f = pd.DataFrame({"vx_vix": c, "vx_vix_pct": pct, "vx_vix_chg5": c - c.shift(5),
                          "vx_level": (pct / 50.0 - 1.0), "vx_chg5": _clip(np.log(c / c.shift(5)) / VIX_CHG5_UNIT),
                          "known_ms": vix["known_ms"]})
        _put(out, close_ms, f, DAILY_MAX_AGE)
        for key, ratio_col, feat, mid in (("vix9d", "vx_9d_ratio", "vx_front", FRONT_MID),
                                          ("vix3m", "vx_3m_ratio", "vx_curve", CURVE_MID)):
            other = _ydaily(key, src_dir)
            if not len(other):
                continue
            p = _pair(other, vix) if key == "vix9d" else _pair(vix, other)    # VIX9D/VIX and VIX/VIX3M
            r = p["a"] / p["b"]
            g = pd.DataFrame({"vx_" + key: (p["a"] if key == "vix9d" else p["b"]), ratio_col: r,
                              feat: _clip((r - mid) / RATIO_HALF), "known_ms": p["known_ms"]})
            _put(out, close_ms, g, DAILY_MAX_AGE)
    gvz = _ydaily("gvz", src_dir)
    if len(gvz):
        c = gvz["close"]
        pct = _pct_rank(c)
        f = pd.DataFrame({"vx_gvz": c, "vx_gvz_pct": pct, "vx_gvz_chg5": c - c.shift(5), "known_ms": gvz["known_ms"]})
        if asset in METALS:                                          # the gold-volatility reading: gold and silver only
            f["vx_gold"] = pct / 50.0 - 1.0
        _put(out, close_ms, f, DAILY_MAX_AGE)


def _yield_frame(d, name, unit):
    v = d["value"]
    d1, d5 = 100.0 * v.diff(), 100.0 * (v - v.shift(5))
    return pd.DataFrame({"rt_%s" % name: v, "rt_%s_d1_bp" % name: d1, "rt_%s_d5_bp" % name: d5,
                         "_f": _clip(d5 / unit), "known_ms": d["known_ms"]})


def _rates(out, close_ms, asset, src_dir, bars):
    y = {}
    for key, name, feat, unit in (("y2", "y2", "rt_y2_5d", YIELD_5D_BP), ("y10", "y10", "rt_y10_5d", YIELD_5D_BP),
                                  ("real10", "real", "rt_real_5d", REAL_5D_BP)):
        d = _fdaily(key, src_dir)
        y[key] = d
        if not len(d):
            continue
        f = _yield_frame(d, name, unit).rename(columns={"_f": feat})
        if name == "real":
            f = f.rename(columns={"rt_real": "rt_real10"})
        _put(out, close_ms, f, DAILY_MAX_AGE)
    if len(y["y10"]) and len(y["y2"]):
        p = _pair(y["y10"], y["y2"], "value", "value")
        _put(out, close_ms, pd.DataFrame({"rt_curve_bp": 100.0 * (p["a"] - p["b"]), "known_ms": p["known_ms"]}),
             DAILY_MAX_AGE)
    ref = y["y10"] if len(y["y10"]) else y["y2"]
    _age_days(out, close_ms, ref, "rt_y_age_d", DAILY_MAX_AGE)
    dxy = _ydaily("dxy", src_dir)
    if len(dxy):
        c = dxy["close"]
        d5 = 100.0 * (c / c.shift(5) - 1.0)
        _put(out, close_ms, pd.DataFrame({"rt_dxy": c, "rt_dxy_d1_pct": 100.0 * (c / c.shift(1) - 1.0),
                                          "rt_dxy_d5_pct": d5, "rt_dxy_5d": _clip(d5 / DXY_5D_PCT),
                                          "known_ms": dxy["known_ms"]}), DAILY_MAX_AGE)
    jgb = _daily(jgb_path(src_dir), JCOLS, "jgb")
    if len(jgb):
        _put(out, close_ms, pd.DataFrame({"rt_jp2": jgb["jp2"], "rt_jp10": jgb["jp10"], "known_ms": jgb["known_ms"]}),
             JGB_MAX_AGE)
        for tenor, us in (("2", y["y2"]), ("10", y["y10"])):
            if not len(us):
                continue
            jp = jgb["jp" + tenor].dropna()
            if not len(jp):
                continue
            # each US date takes the latest Japan date at or before it (Tokyo closes first); no older than JGB_MAX_AGE
            ud, jd = _day_ms(us.index), _day_ms(jp.index)
            k = np.searchsorted(jd, ud, side="right") - 1
            ok = (k >= 0) & ((ud - jd[np.maximum(k, 0)]) <= JGB_MAX_AGE)
            jv = np.where(ok, jp.values[np.maximum(k, 0)], np.nan)
            # known: the later of the US value and that Japan value (the US one, by the rules above)
            kn = np.maximum(us["known_ms"].values, np.where(ok, jgb.loc[jp.index, "known_ms"].values[np.maximum(k, 0)], 0))
            gap = pd.Series(us["value"].values - jv, index=us.index)
            g = pd.DataFrame({"rt_gap" + tenor: gap, "rt_gap%s_d5_bp" % tenor: 100.0 * (gap - gap.shift(5))})
            if tenor == "2" and asset == "USDJPY":
                g["rt_gap_5d"] = _clip(g["rt_gap2_d5_bp"] / GAP_5D_BP)
            g["known_ms"] = kn
            _put(out, close_ms, g, DAILY_MAX_AGE)


def _bar_closes(asset, bars):
    """-> Series of 15m closes keyed by bar OPEN ms (the project's own bars, or `bars` when given)."""
    if bars is not None and asset in bars:
        b = bars[asset]
        return pd.Series(b["close"].values.astype(float), index=pd.Index(data.to_ms(b.index), dtype="int64"))
    path = data.path_for(asset)
    if not os.path.exists(path):
        return pd.Series(dtype=float, index=pd.Index([], dtype="int64"))
    st = os.stat(path)
    key = (path, st.st_mtime_ns, st.st_size)
    if _BAR_CACHE.get(asset, (None,))[0] != key:                   # read again only when the file has changed
        d = pd.read_csv(path, usecols=["ts_ms", "close"])
        s = pd.Series(d["close"].values.astype(float), index=pd.Index(d["ts_ms"].values.astype("int64")))
        _BAR_CACHE[asset] = (key, s[~s.index.duplicated(keep="last")].sort_index())
    return _BAR_CACHE[asset][1]


_BAR_CACHE = {}                                                    # asset -> ((path, mtime, size), closes): ~3 MB each


def _window_pct(x_ms, x, day_ms, day_v, n=PCT_DAYS, nmin=PCT_MIN):
    """Percentile (0-100) of each x against the last n daily values known at or before x_ms."""
    out = np.full(len(x), np.nan)
    if not len(day_v):
        return out
    k = np.searchsorted(day_ms, x_ms, side="right")             # daily values known by then: day_v[:k]
    for kk in np.unique(k):
        lo = max(0, kk - n)
        if kk - lo < nmin:
            continue
        w = np.sort(day_v[lo:kk])
        rows = np.nonzero(k == kk)[0]
        xs = x[rows]
        out[rows] = 100.0 * (np.searchsorted(w, xs, side="left") + np.searchsorted(w, xs, side="right")) / (2.0 * len(w))
    return out


def _metals(out, close_ms, asset, src_dir, bars):
    xau, xag = _bar_closes("XAUUSD", bars), _bar_closes("XAGUSD", bars)
    if len(xau) and len(xag):
        j = pd.DataFrame({"au": xau, "ag": xag}).dropna()
        j = j[(j["au"] > 0) & (j["ag"] > 0)]
        if len(j):
            kms = j.index.values.astype("int64") + BAR_MS                # a bar is known at its close
            r = j["au"] / j["ag"]
            lr = np.log(r)
            # daily values for the percentile: the last bar of each UTC day, used only from the day's end
            # (00:00 UTC next day): whether a bar is a day's last one is only known once the day is over
            day = (kms - 1) // D_MS                                      # a bar closing at 00:00 belongs to the day before
            last = np.r_[day[1:] != day[:-1], True]
            pct = _window_pct(kms, r.values, (day[last] + 1) * D_MS, r.values[last])
            sp = np.log(j["ag"]) - np.log(j["au"])                         # silver minus gold
            sd = sp.diff().rolling(SPREAD_SD_BARS, min_periods=SPREAD_SD_MIN).std()
            f = pd.DataFrame({"mt_gsr": r.values, "mt_gsr_pct": pct,
                              "mt_gsr_chg5d_pct": 100.0 * (r / r.shift(GSR_TREND_BARS) - 1.0).values,
                              "mt_gsr_level": pct / 50.0 - 1.0,
                              "mt_gsr_trend": _clip((lr - lr.shift(GSR_TREND_BARS)) / GSR_TREND_UNIT).values},
                             index=j.index)
            for tag, k in LEAD_BARS:
                f["mt_lead_%s_pp" % tag] = 100.0 * ((j["ag"] / j["ag"].shift(k)) - (j["au"] / j["au"].shift(k))).values
                f["mt_lead_%s" % tag] = _clip((sp - sp.shift(k)) / (sd.where(sd > 0) * np.sqrt(k)) / 2.0).values
            f["known_ms"] = kms
            _put(out, close_ms, f, BAR_MAX_AGE)
    cu, au = _ydaily("copper", src_dir), _ydaily("goldfut", src_dir)
    if len(cu):
        c = cu["close"]
        _put(out, close_ms, pd.DataFrame({"mt_copper": c, "mt_copper_d1_pct": 100.0 * (c / c.shift(1) - 1.0),
                                          "mt_copper_d5_pct": 100.0 * (c / c.shift(5) - 1.0),
                                          "known_ms": cu["known_ms"]}), DAILY_MAX_AGE)
        if len(au):
            p = _pair(cu, au)
            r = 1000.0 * p["a"] / p["b"]
            _put(out, close_ms, pd.DataFrame({"mt_cugold": r, "mt_cugold_pct": _pct_rank(r),
                                              "mt_cugold_chg20_pct": 100.0 * (r / r.shift(20) - 1.0),
                                              "mt_cugold_20d": _clip(np.log(r / r.shift(20)) / CUGOLD_20D_UNIT),
                                              "known_ms": p["known_ms"]}), DAILY_MAX_AGE)


PAIRS = (("rsp", "rsp", "spy", "eb_rsp_spy", "eb_rsp"), ("iwm", "iwm", "spy", "eb_iwm_spy", "eb_iwm"),
         ("tech", "xlk", "xlu", "eb_xlk_xlu", "eb_xlk"), ("semis", "smh", "spy", "eb_smh_spy", "eb_smh"))
PAIR_FEATS = {"rsp": ("eb_rsp_5d", "eb_rsp_20d"), "iwm": ("eb_iwm_5d", "eb_iwm_20d"),
              "tech": ("eb_tech_5d", "eb_tech_20d"), "semis": (None, "eb_semis_20d")}


def _eqbreadth(out, close_ms, asset, src_dir, bars):
    spy = _ydaily("spy", src_dir)
    if len(spy):
        c = spy["close"]
        _put(out, close_ms, pd.DataFrame({"eb_spy": c, "eb_spy_5d_pct": 100.0 * (c / c.shift(5) - 1.0),
                                          "eb_spy_20d_pct": 100.0 * (c / c.shift(20) - 1.0),
                                          "known_ms": spy["known_ms"]}), DAILY_MAX_AGE)
    frames = {"spy": spy}
    for tag, a, b, ratio_col, pre in PAIRS:
        for key in (a, b):
            if key not in frames:
                frames[key] = _ydaily(key, src_dir)
        if not len(frames[a]) or not len(frames[b]):
            continue
        p = _pair(frames[a], frames[b])
        r = p["a"] / p["b"]
        lr = np.log(r)
        u5, u20 = PAIR_UNITS[tag]
        f = pd.DataFrame({ratio_col: r, pre + "_5d_pct": 100.0 * (r / r.shift(5) - 1.0),
                          pre + "_20d_pct": 100.0 * (r / r.shift(20) - 1.0), "known_ms": p["known_ms"]})
        f5, f20 = PAIR_FEATS[tag]
        if f5:
            f[f5] = _clip(100.0 * (lr - lr.shift(5)) / u5)
        f[f20] = _clip(100.0 * (lr - lr.shift(20)) / u20)
        _put(out, close_ms, f, DAILY_MAX_AGE)


def _goldetf(out, close_ms, asset, src_dir, bars):
    g = _daily(gld_path(src_dir), GCOLS, "gld")
    if len(g):
        t = g["tonnes"].where(g["tonnes"] > 0)
        t = t.where(t.notna(), g["ounces"] / TROY_OZ_PER_TONNE)
        g = g.assign(tonnes=t).dropna(subset=["tonnes"])
        t = g["tonnes"]
        d1, d5 = t.diff(), t - t.shift(5)
        f = pd.DataFrame({"ge_gld_tonnes": t, "ge_gld_d1_t": d1, "ge_gld_d5_t": d5,
                          "ge_gld_d5_pct": 100.0 * (t / t.shift(5) - 1.0), "ge_gld_prem_pct": g["prem_pct"],
                          "ge_gld_1d": _clip(100.0 * (t / t.shift(1) - 1.0) / GLD_1D_PCT),
                          "ge_gld_5d": _clip(100.0 * (t / t.shift(5) - 1.0) / GLD_5D_PCT),
                          "ge_gld_prem": _clip(g["prem_pct"] / GLD_PREM_PCT), "known_ms": g["known_ms"]})
        _put(out, close_ms, f, DAILY_MAX_AGE)
        _age_days(out, close_ms, g, "ge_gld_age_d", DAILY_MAX_AGE)
    s = _daily(slv_path(src_dir), SCOLS, "slv")
    if len(s):
        s = s.dropna(subset=["ounces"])
        s = s[s["ounces"] > 0]
    if len(s):
        moz = s["ounces"] / 1e6
        dm = pd.Series(_day_ms(s.index).astype(float), index=s.index)
        d1 = (moz - moz.shift(1)).where(dm - dm.shift(1) <= 5 * D_MS)      # only against a recent snapshot:
        d5 = (moz - moz.shift(5)).where(dm - dm.shift(5) <= 9 * D_MS)      # a gap in the archive is no change
        f = pd.DataFrame({"ge_slv_moz": moz, "ge_slv_d1_moz": d1, "ge_slv_d5_moz": d5,
                          "ge_slv_5d": _clip(100.0 * d5 / (moz - d5) / SLV_5D_PCT), "known_ms": s["known_ms"]})
        _put(out, close_ms, f, DAILY_MAX_AGE)
        _age_days(out, close_ms, s, "ge_slv_age_d", DAILY_MAX_AGE)
    for key, pre in (("gld", "ge_gld"), ("slv", "ge_slv")):
        y = _ydaily(key, src_dir)
        if not len(y):
            continue
        dv = (y["close"] * y["volume"]).where(y["volume"] > 0) / 1e6
        x = dv / dv.rolling(DVOL_DAYS, min_periods=10).median()
        _put(out, close_ms, pd.DataFrame({pre + "_dvol_musd": dv, pre + "_dvol_x": x,
                                          pre + "_dvol": _clip(np.log(x) / np.log(3.0)), "known_ms": y["known_ms"]}),
             DAILY_MAX_AGE)


_CARDS = OrderedDict([("volx", _volx), ("rates", _rates), ("metals", _metals), ("eqbreadth", _eqbreadth),
                      ("goldetf", _goldetf)])
LAST_ERRORS = {}


def features(index15, asset, bars=None, src_dir=None, strict=False):
    """-> frame on index15 (15m bar OPEN times, UTC; a row is known at open + 15 min): every feature
    in GROUPS (float, 0.0 = no read, never NaN) and the readable RAW columns (NaN = no read).
    Only the cards APPLIES gives this asset are computed; the rest stay "no read".

    bars     optional {asset: 15m frame} instead of the project's bar files (the metals card reads
             XAUUSD and XAGUSD whichever of the two is asked for)
    strict   raise on a broken source instead of leaving its card silent (tests)"""
    index15 = pd.DatetimeIndex(index15)
    close_ms = data.to_ms(index15) + BAR_MS
    cols = {}                                                        # column -> numpy array (one frame is built at the end)
    errors = {}
    for name, fn in _CARDS.items():
        if asset not in APPLIES[name]:
            continue
        try:
            fn(cols, close_ms, asset, src_dir, bars)
        except Exception as e:                                       # a broken file silences its card, not the engine
            if strict:
                raise
            errors[name] = "%s: %s" % (type(e).__name__, str(e)[:160])
            for f in GROUPS[name][1]:
                cols.pop(f, None)
    block = np.full((len(index15), len(FEATURES) + len(RAW)), np.nan)
    for j, c in enumerate(FEATURES + RAW):
        if c in cols:
            block[:, j] = np.asarray(cols.pop(c), dtype=float)
    block[~np.isfinite(block)] = np.nan
    nf = len(FEATURES)
    block[:, :nf] = np.clip(np.nan_to_num(block[:, :nf], nan=0.0), -1.0, 1.0)
    out = pd.DataFrame(block, index=index15, columns=FEATURES + RAW, copy=False)
    out.attrs["errors"] = errors
    LAST_ERRORS.clear()
    LAST_ERRORS.update(errors)
    return out


# ------------------------------------------------------------------ plain English
def _n(row, key):
    try:
        v = float(row[key])
    except (KeyError, TypeError, ValueError, IndexError):
        return None
    return v if np.isfinite(v) else None


def _ord(p):
    k = int(round(p))
    suf = "th" if 10 <= k % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(k % 10, "th")
    return "%d%s" % (k, suf)


def _pctile(p):
    return "percentile n/a" if p is None else "%s percentile of the past year" % _ord(p)


def _obs_date(row, age_d):
    """The observation date behind a value: the row's close minus its age in days."""
    try:
        close = pd.Timestamp(row.name) + pd.Timedelta(milliseconds=BAR_MS)
        return (close - pd.Timedelta(days=float(age_d))).strftime("%d %b %Y").lstrip("0")
    except Exception:
        return "an unknown date"


def _sg(x, fmt="%+.1f", none="n/a"):
    return none if x is None else fmt % x


def _volx_words(row, asset):
    v = _n(row, "vx_vix")
    if v is None:
        return "No read: no VIX close is on file for this time."
    s = "VIX %.1f (%s, %s points over 5 days)" % (v, _pctile(_n(row, "vx_vix_pct")), _sg(_n(row, "vx_vix_chg5")))
    r9, r3 = _n(row, "vx_9d_ratio"), _n(row, "vx_3m_ratio")
    if r9 is not None:
        s += "; VIX9D/VIX %.2f (%s)" % (r9, "above 1: the next nine days are priced above the month, near-term fear"
                                       if r9 > 1 else "below 1: no extra near-term fear priced")
    if r3 is not None:
        s += "; VIX/VIX3M %.2f (%s)" % (r3, "above 1, backwardation: fear now is priced above the next three months"
                                       if r3 > 1 else "below 1, contango: the usual calm shape")
    if asset in METALS:
        g = _n(row, "vx_gvz")
        s += ("; gold volatility (GVZ) %.1f, %s, %s points over 5 days" % (g, _pctile(_n(row, "vx_gvz_pct")),
                                                                          _sg(_n(row, "vx_gvz_chg5")))
              if g is not None else "; no gold-volatility (GVZ) close on file")
    return s + "."


def _rates_words(row, asset):
    y2, y10, re10 = _n(row, "rt_y2"), _n(row, "rt_y10"), _n(row, "rt_real10")
    dxy = _n(row, "rt_dxy")
    if y2 is None and y10 is None and dxy is None:
        return "No read: no Treasury yield or dollar-index value is on file for this time."
    bits = []
    for v, d1, d5, label in ((y2, "rt_y2_d1_bp", "rt_y2_d5_bp", "US 2-year"), (y10, "rt_y10_d1_bp", "rt_y10_d5_bp", "10-year"),
                             (re10, "rt_real_d1_bp", "rt_real_d5_bp", "10-year real")):
        if v is not None:
            bits.append("%s %.2f%% (%s bp on the day, %s bp over 5 days)" % (label, v, _sg(_n(row, d1), "%+.0f"),
                                                                           _sg(_n(row, d5), "%+.0f")))
    s = ", ".join(bits)
    if _n(row, "rt_curve_bp") is not None:
        s += "; 10-year minus 2-year %+.0f bp" % _n(row, "rt_curve_bp")
    if _n(row, "rt_y_age_d") is not None:
        s += " (Treasury yields of %s)" % _obs_date(row, _n(row, "rt_y_age_d"))
    if dxy is not None:
        s += "%sdollar index %.2f (%s%% on the day, %s%% over 5 days)" % (
            "; " if s else "", dxy, _sg(_n(row, "rt_dxy_d1_pct"), "%+.2f"), _sg(_n(row, "rt_dxy_d5_pct"), "%+.2f"))
    if asset == "USDJPY":
        g2, jp2 = _n(row, "rt_gap2"), _n(row, "rt_jp2")
        if g2 is not None:
            d5 = _n(row, "rt_gap2_d5_bp")
            s += "; US-Japan 2-year gap %.2f points on the Treasury date, %s bp over 5 US trading days%s" % (
                g2, _sg(d5, "%+.0f"), "" if d5 is None or d5 == 0 else " (%s)" % ("widening" if d5 > 0 else "narrowing"))
            if _n(row, "rt_gap10") is not None:
                s += ", 10-year gap %.2f points" % _n(row, "rt_gap10")
            if jp2 is not None:
                s += "; latest Japan 2-year %.3f%%, 10-year %s (Ministry of Finance, daily)" % (jp2, _f(_n(row, "rt_jp10"), "%.3f", "%"))
        else:
            s += "; no US-Japan yield gap on file"
    return s[0].upper() + s[1:] + "."


def _metals_words(row, asset):
    r = _n(row, "mt_gsr")
    parts = []
    if r is not None:
        c5 = _n(row, "mt_gsr_chg5d_pct")
        s = "Gold/silver ratio %.1f (%s)" % (r, _pctile(_n(row, "mt_gsr_pct")))
        if c5 is not None:
            s += ", %+.1f%% over about five trading days (%s)" % (
                c5, "silver gaining on gold" if c5 < 0 else "gold gaining on silver")
        parts.append(s)
        leads = [_n(row, "mt_lead_%s_pp" % t) for t, _k in LEAD_BARS]
        if any(x is not None for x in leads):
            l24 = leads[2]
            parts.append("silver minus gold over the last 1h / 4h / 24h of trading: %s percentage points%s" % (
                " / ".join(_sg(x, "%+.2f") for x in leads),
                "" if l24 is None or l24 == 0 else " (%s led over 24h)" % ("silver" if l24 > 0 else "gold")))
    cu = _n(row, "mt_copper")
    if cu is not None:
        s = "copper $%.3f/lb (%s%% on the day, %s%% over 5 days)" % (cu, _sg(_n(row, "mt_copper_d1_pct")),
                                                                   _sg(_n(row, "mt_copper_d5_pct")))
        cg = _n(row, "mt_cugold")
        if cg is not None:
            c20 = _n(row, "mt_cugold_chg20_pct")
            s += "; copper/gold ratio (x1000) %.3f, %s, %s%% over 20 days%s" % (
                cg, _pctile(_n(row, "mt_cugold_pct")), _sg(c20),
                "" if c20 is None else " (copper %s gold)" % ("outrunning" if c20 > 0 else "lagging"))
        parts.append(s)
    if not parts:
        return "No read: no gold/silver bars and no copper close are on file for this time."
    return parts[0][0].upper() + parts[0][1:] + "".join("; " + p for p in parts[1:]) + "."


def breadth_state(row):
    """-> a short label of the last 20 trading days, or None: narrow rally / broad rally / risk-off
    rotation / selloff led by the biggest names / broad selloff / mixed. Thresholds are in % points."""
    spy, rsp, iwm, tech = (_n(row, k) for k in ("eb_spy_20d_pct", "eb_rsp_20d_pct", "eb_iwm_20d_pct", "eb_xlk_20d_pct"))
    if spy is None or rsp is None:
        return None
    if spy > 1.0 and rsp < -1.0:
        return "narrow rally"
    if spy > 1.0 and rsp >= 0.0 and (iwm is None or iwm >= 0.0):
        return "broad rally"
    if spy < -1.0 and tech is not None and tech < -2.0:
        return "risk-off rotation"
    if spy < -1.0 and rsp > 1.0:
        return "selloff led by the biggest names"
    if spy < -1.0:
        return "broad selloff"
    return "mixed"


STATE_WORDS = {"narrow rally": "a narrow rally: the index is rising on its largest names while the average stock lags",
               "broad rally": "a broad rally: the average stock and small caps are keeping up with the index",
               "risk-off rotation": "a risk-off rotation: utilities are beating tech while the index falls",
               "selloff led by the biggest names": "the index is falling, led by its largest names (the average stock holds up better)",
               "broad selloff": "a broad selloff: the index is falling without a clear defensive rotation",
               "mixed": "mixed: no clear breadth pattern"}


def _eq_words(row, asset):
    st = breadth_state(row)
    if st is None:
        return "No read: no SPY / RSP closes are on file for this time."
    s = ("Over 20 trading days, %s. SPY %s%% (5 days %s%%); against SPY: equal-weight RSP %s, small caps IWM %s, "
         "semis SMH %s points; tech XLK against utilities XLU %s points") % (
        STATE_WORDS[st], _sg(_n(row, "eb_spy_20d_pct")), _sg(_n(row, "eb_spy_5d_pct")),
        _sg(_n(row, "eb_rsp_20d_pct")), _sg(_n(row, "eb_iwm_20d_pct")), _sg(_n(row, "eb_smh_20d_pct")),
        _sg(_n(row, "eb_xlk_20d_pct")))
    return s + " (5-day: RSP %s, IWM %s, XLK/XLU %s)." % (
        _sg(_n(row, "eb_rsp_5d_pct")), _sg(_n(row, "eb_iwm_5d_pct")), _sg(_n(row, "eb_xlk_5d_pct")))


def _etf_words(row, asset):
    t = _n(row, "ge_gld_tonnes")
    parts = []
    if t is not None:
        s = "GLD holds %s tonnes of gold (%s t on the day, %s t over 5 days, %s%%; holdings of %s)" % (
            format(t, ",.1f"), _sg(_n(row, "ge_gld_d1_t")), _sg(_n(row, "ge_gld_d5_t")),
            _sg(_n(row, "ge_gld_d5_pct"), "%+.2f"), _obs_date(row, _n(row, "ge_gld_age_d") or 0.0))
        if _n(row, "ge_gld_prem_pct") is not None:
            s += ", trading %s%% against its indicative value at 4:15pm New York" % _sg(_n(row, "ge_gld_prem_pct"), "%+.3f")
        parts.append(s)
    m = _n(row, "ge_slv_moz")
    if m is not None:
        parts.append("SLV holds %s million ounces of silver (%s Moz on the day, %s Moz over 5 days)" % (
            format(m, ",.1f"), _sg(_n(row, "ge_slv_d1_moz")), _sg(_n(row, "ge_slv_d5_moz"))))
    else:
        parts.append("no SLV holdings figure for this time (iShares shows only the current figure; the archive "
                     "builds from the first day this card ran)")
    dv = []
    for key, name in (("ge_gld", "GLD"), ("ge_slv", "SLV")):
        musd, x = _n(row, key + "_dvol_musd"), _n(row, key + "_dvol_x")
        if musd is not None:
            dv.append("%s $%s million (%s its 20-day median)" % (name, format(musd, ",.0f"), "n/a" if x is None else "%.1fx" % x))
    if dv:
        parts.append("dollar volume, a proxy for activity not direction: " + ", ".join(dv))
    if t is None and m is None and not dv:
        return "No read: no GLD / SLV holdings or volume are on file for this time."
    return parts[0][0].upper() + parts[0][1:] + "".join("; " + p for p in parts[1:]) + "."


_WORDS = OrderedDict([("volx", _volx_words), ("rates", _rates_words), ("metals", _metals_words),
                      ("eqbreadth", _eq_words), ("goldetf", _etf_words)])


def describe(row, asset):
    """One row of features() -> {card title: one plain-English sentence}, for the cards that apply to
    this asset. States what was read; forecasts nothing."""
    out = OrderedDict()
    for name, fn in _WORDS.items():
        if asset in APPLIES[name]:
            try:
                out[GROUPS[name][0]] = fn(row, asset)
            except Exception as e:                                   # pragma: no cover - a sentence never breaks a page
                out[GROUPS[name][0]] = "No read (%s)." % type(e).__name__
    return out


def _f(x, fmt, unit=""):
    return "n/a" if x is None else (fmt % x) + unit


def facts(row, asset):
    """One row of features() -> {card title: [[label, value], ...]}: levels, percentiles and changes in
    natural units (never a scaled model number), for the cards that apply to this asset."""
    n = lambda k: _n(row, k)                                         # noqa: E731
    out = OrderedDict()
    if asset in APPLIES["volx"]:
        rows = [["VIX", "n/a" if n("vx_vix") is None else "%.2f (%s; %s over 5 days)" % (
                    n("vx_vix"), _pctile(n("vx_vix_pct")), _sg(n("vx_vix_chg5"), "%+.2f"))],
                ["VIX9D / VIX3M", "%s / %s" % (_f(n("vx_vix9d"), "%.2f"), _f(n("vx_vix3m"), "%.2f"))],
                ["VIX9D / VIX (above 1 = near-term fear)", _f(n("vx_9d_ratio"), "%.3f")],
                ["VIX / VIX3M (above 1 = backwardation)", _f(n("vx_3m_ratio"), "%.3f")]]
        if asset in METALS:
            rows.append(["Gold volatility GVZ", "n/a" if n("vx_gvz") is None else "%.2f (%s; %s over 5 days)" % (
                n("vx_gvz"), _pctile(n("vx_gvz_pct")), _sg(n("vx_gvz_chg5"), "%+.2f"))])
        out[GROUPS["volx"][0]] = rows
    if asset in APPLIES["rates"]:
        def yl(v, d1, d5):
            return "n/a" if n(v) is None else "%.2f%% (day %s bp, 5 days %s bp)" % (
                n(v), _sg(n(d1), "%+.0f"), _sg(n(d5), "%+.0f"))
        rows = [["US 2-year yield", yl("rt_y2", "rt_y2_d1_bp", "rt_y2_d5_bp")],
                ["US 10-year yield", yl("rt_y10", "rt_y10_d1_bp", "rt_y10_d5_bp")],
                ["US 10-year real yield (TIPS)", yl("rt_real10", "rt_real_d1_bp", "rt_real_d5_bp")],
                ["10-year minus 2-year", _f(n("rt_curve_bp"), "%+.0f", " bp")],
                ["Treasury data of", "n/a" if n("rt_y_age_d") is None else _obs_date(row, n("rt_y_age_d"))],
                ["Dollar index (DXY)", "n/a" if n("rt_dxy") is None else "%.2f (day %s%%, 5 days %s%%)" % (
                    n("rt_dxy"), _sg(n("rt_dxy_d1_pct"), "%+.2f"), _sg(n("rt_dxy_d5_pct"), "%+.2f"))]]
        if asset == "USDJPY":
            rows += [["Japan 2-year / 10-year (MOF, daily)", "%s / %s" % (_f(n("rt_jp2"), "%.3f", "%"),
                                                                         _f(n("rt_jp10"), "%.3f", "%"))],
                     ["US-Japan 2-year gap", "n/a" if n("rt_gap2") is None else "%.2f points (5 days %s bp)" % (
                         n("rt_gap2"), _sg(n("rt_gap2_d5_bp"), "%+.0f"))],
                     ["US-Japan 10-year gap", "n/a" if n("rt_gap10") is None else "%.2f points (5 days %s bp)" % (
                         n("rt_gap10"), _sg(n("rt_gap10_d5_bp"), "%+.0f"))]]
        out[GROUPS["rates"][0]] = rows
    if asset in APPLIES["metals"]:
        out[GROUPS["metals"][0]] = [
            ["Gold/silver ratio", "n/a" if n("mt_gsr") is None else "%.2f (%s)" % (n("mt_gsr"), _pctile(n("mt_gsr_pct")))],
            ["Ratio, ~5 trading days", _f(n("mt_gsr_chg5d_pct"), "%+.2f", "%")],
            ["Silver minus gold, 1h / 4h / 24h", "%s pp" % " / ".join(_sg(n("mt_lead_%s_pp" % t), "%+.2f") for t, _k in LEAD_BARS)],
            ["Copper (HG=F)", "n/a" if n("mt_copper") is None else "$%.3f/lb (day %s%%, 5 days %s%%)" % (
                n("mt_copper"), _sg(n("mt_copper_d1_pct"), "%+.2f"), _sg(n("mt_copper_d5_pct"), "%+.2f"))],
            ["Copper/gold (x1000)", "n/a" if n("mt_cugold") is None else "%.3f (%s; 20 days %s%%)" % (
                n("mt_cugold"), _pctile(n("mt_cugold_pct")), _sg(n("mt_cugold_chg20_pct"), "%+.1f"))]]
    if asset in APPLIES["eqbreadth"]:
        def pr(lvl, a, b):
            return "n/a" if n(lvl) is None else "%.4f (5 days %s%%, 20 days %s%%)" % (
                n(lvl), _sg(n(a), "%+.2f"), _sg(n(b), "%+.2f"))
        st = breadth_state(row)
        out[GROUPS["eqbreadth"][0]] = [
            ["Reading (20 days)", "n/a" if st is None else st],
            ["SPY", "n/a" if n("eb_spy") is None else "%.2f (5 days %s%%, 20 days %s%%)" % (
                n("eb_spy"), _sg(n("eb_spy_5d_pct"), "%+.2f"), _sg(n("eb_spy_20d_pct"), "%+.2f"))],
            ["Equal weight RSP/SPY", pr("eb_rsp_spy", "eb_rsp_5d_pct", "eb_rsp_20d_pct")],
            ["Small caps IWM/SPY", pr("eb_iwm_spy", "eb_iwm_5d_pct", "eb_iwm_20d_pct")],
            ["Tech vs utilities XLK/XLU", pr("eb_xlk_xlu", "eb_xlk_5d_pct", "eb_xlk_20d_pct")],
            ["Semis SMH/SPY", pr("eb_smh_spy", "eb_smh_5d_pct", "eb_smh_20d_pct")]]
    if asset in APPLIES["goldetf"]:
        def dv(k):
            return "n/a" if n(k + "_dvol_musd") is None else "$%s million (%s the 20-day median)" % (
                format(n(k + "_dvol_musd"), ",.0f"), "n/a" if n(k + "_dvol_x") is None else "%.1fx" % n(k + "_dvol_x"))
        out[GROUPS["goldetf"][0]] = [
            ["GLD gold held", "n/a" if n("ge_gld_tonnes") is None else "%s t (day %s t, 5 days %s t = %s%%; as of %s)" % (
                format(n("ge_gld_tonnes"), ",.1f"), _sg(n("ge_gld_d1_t"), "%+.2f"), _sg(n("ge_gld_d5_t"), "%+.2f"),
                _sg(n("ge_gld_d5_pct"), "%+.2f"), _obs_date(row, n("ge_gld_age_d") or 0.0))],
            ["GLD vs indicative value, 4:15pm NY", _f(n("ge_gld_prem_pct"), "%+.3f", "%")],
            ["SLV silver held", "not on file (current figure only, archived from the first run)" if n("ge_slv_moz") is None
             else "%s Moz (day %s, 5 days %s)" % (format(n("ge_slv_moz"), ",.2f"), _sg(n("ge_slv_d1_moz"), "%+.2f"),
                                                  _sg(n("ge_slv_d5_moz"), "%+.2f"))],
            ["GLD dollar volume (activity, not direction)", dv("ge_gld")],
            ["SLV dollar volume (activity, not direction)", dv("ge_slv")]]
    return out


# ------------------------------------------------------------------ parsers (pure, tested offline)
def parse_yahoo_daily(payload):
    """Yahoo chart JSON (interval 1d) -> frame date (New York), close, volume. Null closes, weekend
    stamps and repeated dates (the last one wins) are dropped. Says nothing about whether a day is final."""
    res = payload["chart"]["result"][0]
    ts = list(res.get("timestamp") or [])
    q = ((res.get("indicators") or {}).get("quote") or [{}])[0] or {}
    if not ts:
        return pd.DataFrame(columns=YCOLS)

    def col(k):
        v = list(q.get(k) or [])[:len(ts)]
        return pd.to_numeric(pd.Series(v + [None] * (len(ts) - len(v)), dtype=object), errors="coerce").values

    d = pd.DataFrame({"date": _ny_date(ts), "close": col("close"), "volume": col("volume")})
    wd = pd.to_datetime(d["date"]).dt.weekday.values
    d = d[(d["close"] > 0) & (wd < 5)]
    return d.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)


def parse_fred_csv(text):
    """FRED's fredgraph.csv -> frame date, value (missing '.' days dropped)."""
    d = pd.read_csv(io.StringIO(text), dtype=str)
    if d.shape[1] < 2:
        raise ValueError("unexpected FRED reply")
    d = pd.DataFrame({"date": d.iloc[:, 0].astype(str).str[:10], "value": pd.to_numeric(d.iloc[:, 1], errors="coerce")})
    d = d[d["date"].str.match(r"^\d{4}-\d{2}-\d{2}$")].dropna(subset=["value"])
    return d.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)


_MOF_ROW = re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2}),(.*)$")


def parse_mof_csv(text):
    """Japan Ministry of Finance JGB benchmark yields (jgbcme*.csv) -> frame date, jp2, jp10 (in %)."""
    rows, cols = [], None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Date,"):
            cols = [c.strip() for c in line.split(",")]
            continue
        m = _MOF_ROW.match(line)
        if not m or cols is None:
            continue
        rec = dict(zip(cols, ["Date"] + m.group(4).split(",")))

        def num(k):
            try:
                return float(rec.get(k, ""))
            except ValueError:
                return np.nan
        rows.append(("%04d-%02d-%02d" % (int(m.group(1)), int(m.group(2)), int(m.group(3))), num("2Y"), num("10Y")))
    d = pd.DataFrame(rows, columns=JCOLS)
    d = d.dropna(subset=["jp2", "jp10"], how="all")
    return d.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)


_MON = dict((m, i + 1) for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split()))


def parse_gld_xlsx(content):
    """SPDR Gold Shares' historical archive (xlsx, read with the standard library) -> frame
    date, tonnes, ounces, close, prem_pct, volume. Holiday rows (no numbers) are dropped."""
    z = zipfile.ZipFile(io.BytesIO(content))
    names = z.namelist()
    strings = []
    if "xl/sharedStrings.xml" in names:
        ss = z.read("xl/sharedStrings.xml").decode("utf-8", "replace")
        for si in re.findall(r"<si>(.*?)</si>", ss, re.S):
            strings.append(re.sub(r"<[^>]+>", "", "".join(re.findall(r"<t[^>]*>(.*?)</t>", si, re.S))).strip())
    best = None
    for nm in names:
        if nm.startswith("xl/worksheets/sheet") and nm.endswith(".xml"):
            x = z.read(nm).decode("utf-8", "replace")
            if best is None or len(x) > len(best):
                best = x
    if best is None:
        raise ValueError("no worksheet in the GLD archive")
    cell = re.compile(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(.*?)</c>)', re.S)
    table = []
    for r in re.findall(r"<row[^>]*>(.*?)</row>", best, re.S):
        rec = {}
        for ref, attrs, inner in cell.findall(r):
            inner = inner or ""
            v = re.search(r"<v>(.*?)</v>", inner, re.S)
            if 't="s"' in attrs and v:
                try:
                    rec[ref] = strings[int(v.group(1))]
                except (ValueError, IndexError):
                    rec[ref] = ""
            elif 't="inlineStr"' in attrs:
                rec[ref] = re.sub(r"<[^>]+>", "", inner).strip()
            elif v:
                rec[ref] = v.group(1)
        table.append(rec)
    want = OrderedDict([("date", lambda h: h == "date"), ("close", lambda h: h.startswith("closing price")),
                        ("prem_pct", lambda h: h.startswith("premium/discount")),
                        ("volume", lambda h: h.startswith("daily share volume")),
                        ("ounces", lambda h: h.startswith("total ounces")), ("tonnes", lambda h: h.startswith("tonnes"))])
    head, at = None, {}
    for i, rec in enumerate(table):
        low = dict((k, str(v).strip().lower()) for k, v in rec.items())
        if any(v == "date" for v in low.values()) and any(v.startswith("tonnes") or v.startswith("total ounces")
                                                         for v in low.values()):
            for field, test in want.items():
                for k, v in low.items():
                    if test(v):
                        at[field] = k
                        break
            head = i
            break
    if head is None or "date" not in at:
        raise ValueError("GLD archive: header row not found")

    def num(rec, field):
        try:
            return float(str(rec.get(at.get(field, "?"), "")).replace(",", ""))
        except ValueError:
            return np.nan
    rows = []
    for rec in table[head + 1:]:
        m = re.match(r"^(\d{1,2})-([A-Za-z]{3})-(\d{4})$", str(rec.get(at["date"], "")).strip())
        if not m or m.group(2).lower() not in _MON:
            continue
        t, oz = num(rec, "tonnes"), num(rec, "ounces")
        if not (t > 0 or oz > 0):
            continue
        rows.append(("%04d-%02d-%02d" % (int(m.group(3)), _MON[m.group(2).lower()], int(m.group(1))),
                     t, oz, num(rec, "close"), num(rec, "prem_pct"), num(rec, "volume")))
    d = pd.DataFrame(rows, columns=GCOLS)
    return d.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)


_SLV_OBJ = re.compile(r'"ounces"\s*:\s*\{(.*?)\}', re.S)


def parse_slv_page(text):
    """The iShares Silver Trust product page -> (as-of date 'YYYY-MM-DD', ounces in trust) or None.
    The page embeds its figures as JSON, sometimes HTML-escaped (&quot;)."""
    if "&quot;" in text:
        text = html.unescape(text)
    for body in _SLV_OBJ.findall(text):
        v = re.search(r'"formattedValue"\s*:\s*"([\d,\.]+)"', body)
        a = re.search(r'"formattedAsOfDate"\s*:\s*"([A-Za-z]{3}) (\d{1,2}), (\d{4})"', body)
        if v and a and a.group(1).lower() in _MON:
            return ("%04d-%02d-%02d" % (int(a.group(3)), _MON[a.group(1).lower()], int(a.group(2))),
                    float(v.group(1).replace(",", "")))
    return None


# ------------------------------------------------------------------ fetch
def _load_state(src_dir):
    try:
        with open(state_path(src_dir), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _save_state(state, src_dir):
    try:
        p = state_path(src_dir)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=1, sort_keys=True)
        os.replace(tmp, p)
    except Exception:
        pass


def _last_date(path, cols):
    d = _read(path, cols)
    d = d[d["date"].notna()]
    return str(d["date"].astype(str).str[:10].max()) if len(d) else None


def _merge(old, new, cols, since=FETCH_FROM, keep="last"):
    """Old rows plus new ones; on a repeated date the new row wins (keep='last') or the stored one stays."""
    old = old.copy()
    old["date"] = old["date"].astype(str).str[:10]
    allr = pd.concat([old[cols], new[cols]]) if len(old) else new[cols]
    return allr[allr["date"] >= since].drop_duplicates("date", keep=keep).sort_values("date")


def _get(sess, url, params=None, headers=None):
    try:
        r = sess.get(url, params=params, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        return r
    finally:
        if OTHER_PAUSE:
            time.sleep(OTHER_PAUSE)                                  # one polite pause after every request


def _yahoo_json(sess, symbol, start_day):
    wait = YAHOO_PAUSE - (time.time() - extdata._last_request[0])    # one clock for every Yahoo request in the project
    if wait > 0:
        time.sleep(wait)
    p1 = int(_day_ms([start_day])[0] // 1000)
    try:
        r = sess.get(YAHOO_URL + symbol, params={"interval": "1d", "period1": p1, "period2": int(time.time()) + 86400},
                     headers=BROWSER_UA, timeout=TIMEOUT)
    finally:
        extdata._last_request[0] = time.time()
    r.raise_for_status()
    return r.json()


def _job_yahoo(sess, key, d, now_ms):
    path = yahoo_path(key, d)
    old = _read(path, YCOLS)
    last = _last_date(path, YCOLS)
    start = FETCH_FROM if last is None else (dt.date.fromisoformat(last) - dt.timedelta(days=21)).isoformat()
    new = parse_yahoo_daily(_yahoo_json(sess, YAHOO[key][0], start))
    new = new[known_ms("yahoo", new["date"], YAHOO[key][1]) <= now_ms]            # a day is stored once its close is final
    if not len(new) and not len(old):
        raise RuntimeError("no final daily closes in the reply")
    allr = _merge(old, new, YCOLS)
    _write(allr, path)
    return len(allr)


def _job_fred(sess_fred, key, d, now_ms):
    path = fred_path(key, d)
    new = parse_fred_csv(_get(sess_fred, FRED_URL, {"id": FRED[key], "cosd": FETCH_FROM}, headers=FRED_HEADERS).text)
    new = new[known_ms("fred", new["date"]) <= now_ms]
    if len(new) < 30:
        raise RuntimeError("only %d rows in the FRED reply" % len(new))
    allr = _merge(_read(path, FCOLS), new, FCOLS)
    _write(allr, path)
    return len(allr)


def _decode(content):
    for enc in ("utf-8", "cp932"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    return content.decode("latin-1", "replace")


def _job_jgb(sess, d, now_ms):
    path = jgb_path(d)
    old = _read(path, JCOLS)
    last = _last_date(path, JCOLS)
    behind = last is None or (dt.date.fromtimestamp(now_ms / 1000.0) - dt.date.fromisoformat(last)).days > 7
    urls = list(MOF_URLS) if behind else [MOF_URLS[1]]                # the full history only when missing or behind
    parts = [parse_mof_csv(_decode(_get(sess, u, headers=BROWSER_UA).content)) for u in urls]
    new = pd.concat(parts)
    new = new[known_ms("jgb", new["date"]) <= now_ms]
    if not len(new) and not len(old):
        raise RuntimeError("no rows in the MOF files")
    allr = _merge(old, new, JCOLS)
    _write(allr, path)
    return len(allr)


def _job_gld(sess, d, now_ms):
    path = gld_path(d)
    new = parse_gld_xlsx(_get(sess, GLD_URL, headers=BROWSER_UA).content)
    new = new[known_ms("gld", new["date"]) <= now_ms]
    if len(new) < 30:
        raise RuntimeError("only %d rows in the GLD archive" % len(new))
    allr = _merge(_read(path, GCOLS), new, GCOLS)
    _write(allr, path)
    return len(allr)


def _job_slv(sess, d, now_ms):
    path = slv_path(d)
    got = parse_slv_page(_get(sess, SLV_URL, headers=BROWSER_UA).text)
    if got is None:
        raise RuntimeError("no 'Ounces in Trust' figure found on the iShares page")
    new = pd.DataFrame([(got[0], got[1], now_ms)], columns=SCOLS)
    allr = _merge(_read(path, SCOLS), new, SCOLS, keep="first")         # a date keeps its first snapshot
    _write(allr, path)
    return len(allr)


def _jobs(sess, sess_fred, d):
    out = []
    for key, (_sym, hm) in YAHOO.items():
        out.append(("yahoo_" + key, yahoo_path(key, d), YCOLS, "yahoo", hm,
                    lambda now, key=key: _job_yahoo(sess, key, d, now)))
    for key in FRED:
        out.append(("fred_" + key, fred_path(key, d), FCOLS, "fred", None,
                    lambda now, key=key: _job_fred(sess_fred, key, d, now)))
    out.append(("jgb", jgb_path(d), JCOLS, "jgb", None, lambda now: _job_jgb(sess, d, now)))
    out.append(("gld_holdings", gld_path(d), GCOLS, "gld", None, lambda now: _job_gld(sess, d, now)))
    out.append(("slv_holdings", slv_path(d), SCOLS, "slv", None, lambda now: _job_slv(sess, d, now)))
    return out


def _due(kind, spec, last, last_try, now_ms):
    if now_ms - last_try < RETRY_MS:
        return False
    if last is None or now_ms - last_try >= SAFETY_MS:
        return True
    try:
        return _next_known(kind, last, spec) <= now_ms
    except Exception:
        return True


def update(log=print, force=False, src_dir=None):
    """Fetch / extend every xm_* file under data/sources/. -> {job: rows on disk, "fresh", or "failed: why"}.
    Never raises; a failed job keeps its old file and is tried again after RETRY_MS. A job runs only
    when a newer value should be public by now (its publication rule), at least every SAFETY_MS, or
    when its file is missing; so most 15-minute calls make no request at all. force=True asks every
    source now."""
    out = OrderedDict()
    try:
        import requests
        d = src_dir or SRC_DIR
        os.makedirs(d, exist_ok=True)
        sess, sess_fred = requests.Session(), requests.Session()
        state = _load_state(d)
        now = _now_ms()
        for name, path, cols, kind, spec, job in _jobs(sess, sess_fred, d):
            try:
                last = _last_date(path, cols)
                if not force and not _due(kind, spec, last, int(state.get(name, 0)), now):
                    out[name] = "fresh"
                    continue
                state[name] = _now_ms()
                out[name] = int(job(_now_ms()))
            except Exception as e:                                    # a failed source keeps its old file
                out[name] = "failed: %s" % (str(e)[:120] or type(e).__name__)
        _save_state(state, d)
    except Exception as e:
        out["all"] = "failed: %s" % (str(e)[:120] or type(e).__name__)
    try:
        if log:
            done = ["%s %s" % (k, v) for k, v in out.items() if v != "fresh"]
            log("sources.xmarket: %s" % ("; ".join(done) if done else "all fresh"))
    except Exception:
        pass
    return out
