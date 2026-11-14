# -*- coding: utf-8 -*-
"""oil -- five cards for WTI and Brent crude (added 11 Nov 2026).

  eia        EIA crude inventories        hours to / since the weekly EIA report (release times from
                                          calhistory); the report's numbers from the EIA's own published
                                          history pages (no key): U.S. commercial crude stocks, Cushing,
                                          gasoline and distillate, each week's change against its 5-year norm
  opec       OPEC+ calendar               days to / since an OPEC or OPEC+ meeting (calhistory), flagged in
                                          the week before a meeting and the week after
  oilvol     Oil volatility               Cboe crude oil volatility index OVX (Yahoo daily): level, one-year
                                          percentile, 5-day change; realised volatility from this project's bars
  oilpos     Crude futures positioning    managed money in NYMEX WTI (CFTC disaggregated, futures only) and in
             (CFTC)                       ICE Brent (ICE Futures Europe's own COT files, same layout); each
                                          market reads its own exchange
  oilspread  WTI-Brent and curve          Brent minus WTI from this project's 15m bars (level, z-scores, 1-day
                                          change); front minus second month: EIA's daily NYMEX WTI contract 1 / 2
                                          (2012 - 5 Apr 2024, the EIA stopped the series) and, from 2026 on,
                                          Yahoo's daily closes of the two nearest listed contracts, archived
                                          day by day (Yahoo drops a contract once it expires)

Files: data/sources/oil_*.csv (written atomically, only ever extended) and data/sources/oil_state.json.
docs/SOURCES_oil.md is the plain-English account.

THE ONE RULE (tests/test_oil.py cuts the future off and checks): a row may use only what was public at
its 15m close.
  EIA weekly report for the week ending Friday D  from its release: calhistory's archive date and time
                                                  (Wed 10:30 ET, 11:00 ET when a holiday shifts it); when
                                                  calhistory has no row for that week, the same rule; live,
                                                  a week the EIA pages did not yet show when it was due
                                                  counts from the moment update() first saw it
  EIA 5-year norms                                only from earlier years' weeks (all long public)
  OVX close for New York date D                   from 16:30 New York on D
  CFTC report (positions as of Tuesday D)         cot.release_ms(D): Friday 15:30 ET, the CFTC's holiday
                                                  and shutdown dates; late -> from when first seen
  ICE Brent COT (as of Tuesday D)                 Friday 15:30 ET of that week (ICE publishes on the
                                                  Friday), the next business day when the Friday is a UK
                                                  holiday; late -> from when first seen
  EIA NYMEX contract 1 / 2 prices for day D       the EIA posted these once a week (Wednesday, data to
                                                  Tuesday): counted from 17:00 ET on the Thursday after
                                                  the first Wednesday after D (always at or after the post)
  Yahoo contract close for New York date D        from 17:15 New York on D (as xmarket's futures)
  OPEC meeting                                    "days to" sees a meeting only from 21 days before it
                                                  (7 for the eight-country monthly calls, 1 for meetings
                                                  that were called or moved at short notice); "days since"
                                                  counts from 13:00 UTC on the day (calhistory's nominal time)
  15m bars (realised volatility, Brent-WTI)       from the close of the bar they use
Release SCHEDULES (when the next EIA report is due) are public in advance and are read as such.

Readings (FEATURES) are in [-1, 1]; 0.0 = no read, never NaN. RAW columns are readable numbers in
natural units (NaN = no read). Nothing here is claimed to predict anything: these are data points the
engine learns from and the owner reads. Sign convention (docs/SOURCES_oil.md): positive = the side
usually read as supportive for THIS market's price (a draw bigger than the seasonal norm; managed money
net long; this market gaining on the other one; backwardation). That is a convention, not a forecast.
"""
import datetime as dt
import io
import json
import os
import re
import time
from collections import OrderedDict

import numpy as np
import pandas as pd

from . import _util as U
from ..config import DATA_DIR

OIL = ("WTI", "BRENT")
GROUPS = OrderedDict([
    ("eia", ("EIA crude inventories", ["eia_next", "eia_since", "eia_crude", "eia_cushing", "eia_products",
                                       "eia_level"])),
    ("opec", ("OPEC+ calendar", ["opec_week", "opec_after"])),
    ("oilvol", ("Oil volatility", ["ovol_level", "ovol_chg5", "ovol_rv_trend", "ovol_vrp"])),
    ("oilpos", ("Crude futures positioning (CFTC)", ["opos_level", "opos_pctile", "opos_chg"])),
    ("oilspread", ("WTI-Brent and curve", ["ospr_z20", "ospr_z250", "ospr_chg1d", "ospr_curve"])),
])
APPLIES = dict((v, OIL) for v in GROUPS)
FEATURES = [f for _t, _fs in GROUPS.values() for f in _fs]
RAW = [
    # eia
    "eia_h_to_next", "eia_h_since_last", "eia_week_age_d", "eia_crude_mb", "eia_crude_chg_mb", "eia_crude_norm_mb",
    "eia_crude_vs5y_pct", "eia_cushing_mb", "eia_cushing_chg_mb", "eia_cushing_norm_mb", "eia_gas_chg_mb",
    "eia_dist_chg_mb", "eia_prod_norm_mb",
    # opec
    "opec_days_to_next", "opec_days_since_last",
    # oilvol
    "ovol_ovx", "ovol_ovx_pct", "ovol_ovx_chg5", "ovol_rv1d", "ovol_rv5d", "ovol_rv20d", "ovol_iv_rv",
    # oilpos
    "opos_net", "opos_net_chg", "opos_oi", "opos_net_pct_oi", "opos_pctile_3y", "opos_report_age_d",
    # oilspread
    "ospr_spread", "ospr_spread_z20", "ospr_spread_z250", "ospr_spread_chg1d", "ospr_m1", "ospr_m2",
    "ospr_curve_usd", "ospr_curve_pct", "ospr_curve_age_d",
]

SRC_DIR = os.path.join(DATA_DIR, "sources")
H_MS, D_MS, MIN_MS, BAR_MS = U.H_MS, U.D_MS, 60000, U.BAR_MS

# ---- constants (docs/SOURCES_oil.md says why)
EIA_KEEP_FROM = "2012-01-01"          # five years of norms before the 2019 history (and a margin)
EIA_SERIES = OrderedDict([("crude", "WCESTUS1"),                 # U.S. ending stocks of crude excl. SPR, kb
                          ("cushing", "W_EPC0_SAX_YCUOK_MBBL"),  # Cushing, OK crude stocks, kb
                          ("gasoline", "WGTSTUS1"),              # U.S. total motor gasoline stocks, kb
                          ("distillate", "WDISTUS1")])           # U.S. distillate fuel oil stocks, kb
EIA_LEAF = "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx"
EIA_MAX_AGE = 10 * D_MS               # a weekly report stands until the next (one late week allowed)
EIA_NEAR_H = 24.0                     # eia_next / eia_since fade over 24 hours
CRUDE_UNIT, CUSHING_UNIT, PROD_UNIT = 5000.0, 1500.0, 5000.0     # kb vs the 5-year norm that reads 1.0
LEVEL_UNIT_PCT = 10.0                 # commercial crude 10% below its 5-year average for the week reads +1.0
NORM_YEARS, NORM_MIN = 5, 3

OVX_SYMBOL, OVX_KNOWN = "^OVX", (16, 30)
OVX_FROM = "2018-01-01"
PCT_DAYS, PCT_MIN = 252, 126
DAILY_MAX_AGE = 6 * D_MS
OVX_CHG5_UNIT = 0.30                  # ln(OVX / OVX five days ago) of 0.30 reads 1.0
BARS_DAY = 92                         # about one trading day of oil 15m bars (23 hours)
RV_BARS = (("1d", BARS_DAY), ("5d", 5 * BARS_DAY), ("20d", 20 * BARS_DAY))
BARS_YEAR = BARS_DAY * 252
BAR_MAX_AGE = H_MS

COT_START = "2015-01-01"
WTI_CFTC_CODE = "067651"              # NYMEX light sweet crude ("WTI-PHYSICAL" from Feb 2022)
ICE_URL = "https://www.ice.com/publicdocs/futures/COTHist%d.csv"
ICE_MARKET = "ICE Brent Crude Futures - ICE Futures Europe"
COT_COLS = ["date", "oi", "long", "short", "first_seen_ms", "known_ms"]
COT_MAX_AGE = 15 * D_MS
COT_LEVEL_UNIT, COT_CHG_UNIT = 30.0, 3.0
COT_PCT_WEEKS, COT_PCT_MIN = 156, 52

SPREAD_Z20, SPREAD_Z250, SPREAD_Z250_MIN = 20 * BARS_DAY, 250 * BARS_DAY, 50 * BARS_DAY
SPREAD_1D = 88                        # common Brent/WTI bars in a trading day (Brent trades 22 hours)
SPREAD_Z_UNIT, SPREAD_CHG_UNIT = 2.5, 1.0
CURVE_UNIT_PCT = 2.0                  # front 2% above second month (backwardation) reads +1.0
CURVE_EIA_MAX_AGE, CURVE_Y_MAX_AGE = 14 * D_MS, 6 * D_MS
CURVE_KNOWN = (17, 15)
MONTH_CODES = "FGHJKMNQUVXZ"

OPEC_LEAD_D = {"default": 21, "eight": 7, "short": 1}
OPEC_SHORT_NOTICE = ("2020-04-09", "2020-04-12", "2020-06-06", "2020-12-03", "2021-01-05", "2021-07-18",
                     "2023-11-30", "2024-12-05", "2025-05-03", "2025-05-31", "2025-07-05")
OPEC_NEAR_D = 7.0

TIMEOUT = 30
PAUSE_S = 1.5
RETRY_MS = 30 * MIN_MS
SAFETY_MS = 12 * H_MS

LAST_ERRORS = {}


# ------------------------------------------------------------------ files
def path(name, src_dir=None):
    return os.path.join(src_dir or SRC_DIR, "oil_%s.csv" % name)


def state_path(src_dir=None):
    return os.path.join(src_dir or SRC_DIR, "oil_state.json")


def _cal_path(src_dir):
    """The calendar history to read: a planted copy in src_dir (tests), else calhistory's own file."""
    if src_dir:
        p = os.path.join(src_dir, "calendar_history.csv")
        if os.path.exists(p):
            return p
    return None


def _load(name, cols, src_dir=None):
    d = U.read_csv(path(name, src_dir), cols, dtype={"date": str})
    if not len(d):
        return pd.DataFrame(dict((c, pd.Series(dtype=object if c in ("date", "m1_sym", "m2_sym") else "float64"))
                                 for c in cols))
    d = d[cols].dropna(subset=["date"]).copy()
    d["date"] = d["date"].astype(str).str[:10]
    for c in cols:
        if c not in ("date", "m1_sym", "m2_sym"):
            d[c] = pd.to_numeric(d[c], errors="coerce").astype(float)
    return d.drop_duplicates("date", keep="first").sort_values("date").reset_index(drop=True)


# ------------------------------------------------------------------ clocks
def _d(x):
    return x if isinstance(x, dt.date) and not isinstance(x, dt.datetime) else pd.Timestamp(str(x)[:10]).date()


_FED = {}


def _fed(year):
    if year not in _FED:
        from . import cot
        _FED[year] = cot.federal_holidays(year)
    return _FED[year]


def eia_rule_ms(week_end):
    """The EIA's rule for a week ending Friday `week_end`: Wednesday 10:30 ET; Thursday 11:00 ET when a
    federal holiday falls on the Monday, Tuesday or Wednesday before it."""
    d = _d(week_end)
    wed = d + dt.timedelta(days=(2 - d.weekday()) % 7 or 7)
    hol = _fed(wed.year) | _fed((wed - dt.timedelta(days=2)).year)
    if any((wed - dt.timedelta(days=k)) in hol for k in range(3)):
        return U.ny_ms(wed + dt.timedelta(days=1), 11, 0)
    return U.ny_ms(wed, 10, 30)


_EV_CACHE = {}


def _cal_events(src_dir):
    """-> (EIA release ms array from calhistory, OPEC frame [ms, day, title]); empty when the file is missing."""
    from .. import calhistory
    p = _cal_path(src_dir)
    try:
        key = (p or calhistory.HISTORY_CSV, os.path.getmtime(p or calhistory.HISTORY_CSV))
    except OSError:
        return np.array([], dtype="int64"), pd.DataFrame(columns=["ms", "day", "title"])
    if _EV_CACHE.get("key") != key:
        d = calhistory.oil_events(p)
        eia = np.sort(d.loc[d["kind"] == "EIA", "ts_ms"].values.astype("int64"))
        op = d.loc[d["kind"] == "OPEC", ["ts_ms", "title"]].copy()
        op["day"] = pd.to_datetime(op["ts_ms"], unit="ms", utc=True).dt.strftime("%Y-%m-%d")
        op = op.rename(columns={"ts_ms": "ms"}).sort_values("ms").reset_index(drop=True)
        _EV_CACHE.clear()
        _EV_CACHE.update(key=key, eia=eia, opec=op)
    return _EV_CACHE["eia"], _EV_CACHE["opec"]


def eia_release_for(week_ends, src_dir=None):
    """Release ms of the report for each week-ending Friday: the first release in calhistory's archive at
    or after the Wednesday 00:00 ET that follows the week. A report the EIA delayed (June 2022, Nov 2023,
    Christmas 2025) thus counts from the delayed release, and two weeks published together share it.
    Outside the archive's span (before 2019, or after its last row) the EIA's rule is used."""
    cal, _op = _cal_events(src_dir)
    out = np.empty(len(week_ends), dtype="int64")
    for i, w in enumerate(week_ends):
        d = _d(w)
        lo = U.ny_ms(d + dt.timedelta(days=(2 - d.weekday()) % 7 or 7), 0, 0)
        k = np.searchsorted(cal, lo, side="left")
        if len(cal) and cal[0] - 8 * D_MS <= lo and k < len(cal):
            out[i] = cal[k]
        else:
            out[i] = eia_rule_ms(d)
    return out


def eia_schedule(lo_ms, hi_ms, src_dir=None):
    """Every weekly EIA release time from lo_ms - 9 days to hi_ms + 9 days (calhistory, else the rule)."""
    lo = pd.Timestamp(lo_ms - 9 * D_MS, unit="ms").date()
    hi = pd.Timestamp(hi_ms + 9 * D_MS, unit="ms").date()
    first = lo - dt.timedelta(days=(lo.weekday() - 4) % 7)          # the Friday on or before lo
    fridays = [first + dt.timedelta(days=7 * k) for k in range(int((hi - first).days // 7) + 2)]
    return np.unique(eia_release_for(fridays, src_dir))


def ice_release_ms(report_date):
    """ICE Brent COT for positions as of `report_date`: the Friday of that week, 15:30 ET; the next
    business day when the Friday is a UK holiday (Good Friday, Christmas, Boxing Day, New Year)."""
    d = _d(report_date)
    fri = d + dt.timedelta(days=(4 - d.weekday()) % 7)
    while fri.weekday() >= 5 or fri in _uk_holidays(fri.year):
        fri += dt.timedelta(days=1)
    return U.ny_ms(fri, 15, 30)


def _uk_holidays(year):
    from .. import extdata
    e = extdata._easter(year)

    def nth_mon(month, n):
        if n > 0:
            first = dt.date(year, month, 1)
            return first + dt.timedelta(days=(0 - first.weekday()) % 7 + 7 * (n - 1))
        last = dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
        return last - dt.timedelta(days=last.weekday())

    s = {e - dt.timedelta(days=2), e + dt.timedelta(days=1), nth_mon(5, 1), nth_mon(5, -1), nth_mon(8, -1)}
    for m, dd in ((1, 1), (12, 25), (12, 26)):
        x = dt.date(year, m, dd)
        while x.weekday() >= 5 or x in s:
            x += dt.timedelta(days=1)
        s.add(x)
    return s


def eia_curve_known_ms(dates):
    """EIA daily NYMEX prices for day D: 17:00 ET on the Thursday after the first Wednesday after D."""
    if not len(dates):
        return np.array([], dtype="int64")
    t = pd.to_datetime(pd.Series(list(dates), dtype=str))
    wd = t.dt.weekday.values
    ahead = (2 - wd) % 7
    ahead = np.where(ahead == 0, 7, ahead) + 1
    days = (t + pd.to_timedelta(ahead, unit="D")).dt.strftime("%Y-%m-%d").values
    return U.ny_ms_vec(days, 17, 0)


def opec_meetings(src_dir=None):
    """-> frame day, title, ms (13:00 UTC, calhistory's nominal time), seen_ms (when 'days to' may see it)."""
    _eia, op = _cal_events(src_dir)
    if not len(op):
        return pd.DataFrame(columns=["day", "title", "ms", "seen_ms"])
    op = op.copy()
    lead = np.where(op["day"].isin(OPEC_SHORT_NOTICE), OPEC_LEAD_D["short"],
                    np.where(op["title"].str.contains("eight", case=False), OPEC_LEAD_D["eight"], OPEC_LEAD_D["default"]))
    day0 = U.to_ms_vec(op["day"].values)                               # 00:00 UTC of the meeting day
    op["seen_ms"] = day0 - lead.astype("int64") * D_MS
    return op[["day", "title", "ms", "seen_ms"]]


# ------------------------------------------------------------------ contract months (curve)
def _bdays_back(d, n, hol):
    while n > 0:
        d -= dt.timedelta(days=1)
        if d.weekday() < 5 and d not in hol:
            n -= 1
    return d


def contract_expiry(root, year, month):
    """Last trading day of a contract. CL (NYMEX WTI): 3 business days before the 25th of the month before
    delivery (4 when the 25th is not a business day). BZ (Brent, ICE rule): the last business day of the
    second month before delivery."""
    from .. import extdata
    if root == "CL":
        py, pm = (year, month - 1) if month > 1 else (year - 1, 12)
        hol = extdata.nyse_days(py)[0]
        d25 = dt.date(py, pm, 25)
        busy = d25.weekday() < 5 and d25 not in hol
        return _bdays_back(d25, 3 if busy else 4, hol)
    py, pm = (year, month - 2) if month > 2 else (year - 1, month + 10)
    hol = _uk_holidays(py)
    d = dt.date(py + (pm == 12), pm % 12 + 1, 1) - dt.timedelta(days=1)
    while d.weekday() >= 5 or d in hol:
        d -= dt.timedelta(days=1)
    return d


def front_two(root, day):
    """-> ((year, month) of the front contract, (year, month) of the second) trading on `day`."""
    d = _d(day)
    y, m = d.year, d.month
    found = []
    for _ in range(6):
        if contract_expiry(root, y, m) >= d:
            found.append((y, m))
            if len(found) == 2:
                return found[0], found[1]
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)
    raise ValueError("no contract found")


def yahoo_symbol(root, ym):
    return "%s%s%02d.NYM" % (root, MONTH_CODES[ym[1] - 1], ym[0] % 100)


# ------------------------------------------------------------------ parsers (pure, tested offline)
_TD = re.compile(r"<td class='(B[356])'>(.*?)</td>", re.S)


def _cell(x):
    x = re.sub(r"<[^>]+>", "", x).replace("&nbsp;", " ").strip()
    try:
        return float(x.replace(",", ""))
    except ValueError:
        return np.nan


def parse_eia_weekly(text):
    """An EIA 'LeafHandler' weekly history page -> frame date (week ending, YYYY-MM-DD), value."""
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", text, re.S):
        cells = _TD.findall(tr)
        if not cells or cells[0][0] != "B6":
            continue
        m = re.search(r"(\d{4})-([A-Za-z]{3})", cells[0][1])
        if not m:
            continue
        year = int(m.group(1))
        mon = pd.Timestamp("1 %s 2000" % m.group(2)).month
        rest = cells[1:]
        for j in range(0, len(rest) - 1, 2):
            if rest[j][0] != "B5" or rest[j + 1][0] != "B3":
                continue
            md = re.search(r"(\d{2})/(\d{2})", rest[j][1])
            v = _cell(rest[j + 1][1])
            if not md or not np.isfinite(v):
                continue
            mm, dd = int(md.group(1)), int(md.group(2))
            yy = year - 1 if (mm == 12 and mon == 1) else year + 1 if (mm == 1 and mon == 12) else year
            rows.append(("%04d-%02d-%02d" % (yy, mm, dd), v))
    d = pd.DataFrame(rows, columns=["date", "value"])
    return d.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)


def parse_eia_daily(text):
    """An EIA 'LeafHandler' daily history page (rows of one week, Monday..Friday) -> frame date, value."""
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", text, re.S):
        cells = _TD.findall(tr)
        if not cells or cells[0][0] != "B6":
            continue
        m = re.search(r"(\d{4})\s+([A-Za-z]{3})-\s*(\d{1,2})\s+to", cells[0][1].replace("&nbsp;", " "))
        if not m:
            continue
        start = pd.Timestamp("%s %s %s" % (m.group(3), m.group(2), m.group(1))).date()
        for k, (cls, inner) in enumerate(cells[1:6]):
            v = _cell(inner)
            if cls == "B3" and np.isfinite(v):
                rows.append(((start + dt.timedelta(days=k)).isoformat(), v))
    d = pd.DataFrame(rows, columns=["date", "value"])
    return d.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)


def parse_ice_cot(text, market=ICE_MARKET):
    """ICE Futures Europe's yearly COT history CSV -> rows of `market` (futures only): date, oi, long, short
    (managed money)."""
    d = pd.read_csv(io.StringIO(text.lstrip("﻿")), dtype=str, low_memory=False)
    d.columns = [str(c).replace("﻿", "").replace("ï»¿", "").strip().lower() for c in d.columns]
    name = d["market_and_exchange_names"].astype(str).str.strip()
    keep = name == market
    if "futonly_or_combined" in d.columns:
        keep &= d["futonly_or_combined"].astype(str).str.strip().str.lower().str.startswith("fut")
    d = d[keep]
    if not len(d):
        return pd.DataFrame(columns=["date", "oi", "long", "short"])
    dc = [c for c in d.columns if c.startswith("as_of_date_form_mm")]
    if dc:
        date = pd.to_datetime(d[dc[0]].astype(str).str.strip(), format="%m/%d/%Y", errors="coerce")
    else:
        date = pd.to_datetime(d["as_of_date_in_form_yymmdd"].astype(str).str.strip().str.zfill(6), format="%y%m%d",
                              errors="coerce")
    num = lambda c: pd.to_numeric(d[c].astype(str).str.replace(",", "").str.strip(), errors="coerce").values  # noqa: E731
    out = pd.DataFrame({"date": date.dt.strftime("%Y-%m-%d").values, "oi": num("open_interest_all"),
                        "long": num("m_money_positions_long_all"), "short": num("m_money_positions_short_all")})
    out = out.dropna(subset=["date", "long", "short"])
    return out.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)


# ------------------------------------------------------------------ bars
_BAR_CACHE = {}


def _bar_closes(asset, bars):
    """-> Series of 15m closes keyed by bar OPEN ms: from `bars` ({asset: frame} or a frame of this asset)
    or the project's own file (re-read only when it changes)."""
    from .. import data
    b = bars.get(asset) if isinstance(bars, dict) else None
    if b is not None:
        return pd.Series(b["close"].values.astype(float), index=pd.Index(data.to_ms(b.index), dtype="int64"))
    p = data.path_for(asset)
    if not os.path.exists(p):
        return pd.Series(dtype=float, index=pd.Index([], dtype="int64"))
    st = os.stat(p)
    key = (p, st.st_mtime_ns, st.st_size)
    if _BAR_CACHE.get(asset, (None,))[0] != key:
        d = pd.read_csv(p, usecols=["ts_ms", "close"])
        s = pd.Series(d["close"].values.astype(float), index=pd.Index(d["ts_ms"].values.astype("int64")))
        _BAR_CACHE[asset] = (key, s[~s.index.duplicated(keep="last")].sort_index())
    return _BAR_CACHE[asset][1]


# ------------------------------------------------------------------ the five cards
def _asof(known, values, close_ms, max_age):
    return U.asof(known, np.asarray(values, dtype=float), close_ms, max_age)


def _clip(x, lim=1.0):
    return np.clip(x, -lim, lim)


def eia_table(src_dir=None):
    """The stored weekly EIA numbers with every reading computed on the weekly grid, plus known_at."""
    d = _load("eia_weekly", ["date"] + list(EIA_SERIES) + ["first_seen_ms", "known_ms"], src_dir)
    d = d.dropna(subset=["crude"]).reset_index(drop=True)
    if len(d) < 2:
        return d.iloc[:0]
    t = pd.to_datetime(d["date"])
    days = (t.values.astype("datetime64[D]")).astype("int64")
    for col in EIA_SERIES:
        d[col + "_chg"] = d[col].diff().where(np.r_[np.nan, np.diff(days)] <= 8)   # a gap in the record is no change
    d["prod_chg"] = d["gasoline_chg"] + d["distillate_chg"]
    for col in ("crude_chg", "cushing_chg", "prod_chg", "crude"):
        acc = np.zeros(len(d))
        cnt = np.zeros(len(d))
        vals = d[col].values
        for k in range(1, NORM_YEARS + 1):                             # the same week in each of the 5 years before
            tgt = days - int(round(365.25 * k))
            j = np.clip(np.searchsorted(days, tgt), 1, len(days) - 1)
            j = np.where(np.abs(days[j - 1] - tgt) < np.abs(days[j] - tgt), j - 1, j)
            ok = (np.abs(days[j] - tgt) <= 3) & np.isfinite(vals[j]) & (days[j] < days)
            acc += np.where(ok, vals[j], 0.0)
            cnt += ok
        d[col + "_norm"] = np.where(cnt >= NORM_MIN, acc / np.maximum(cnt, 1), np.nan)
    rule = eia_release_for(d["date"].values, src_dir)
    late = d["known_ms"].values
    known = np.where(np.isfinite(late), np.maximum(np.nan_to_num(late, nan=0).astype("int64"), rule), rule)
    d["known_at"] = np.maximum.accumulate(known)                       # reports come out in order
    d["date_ms"] = U.ny_ms_vec(d["date"].values, 0, 0)
    return d


def _eia(out, close_ms, asset, src_dir, bars):
    if len(close_ms):
        ev = eia_schedule(int(close_ms.min()), int(close_ms.max()), src_dir)
        k = np.searchsorted(ev, close_ms, side="right")
        nxt = np.where(k < len(ev), ev[np.minimum(k, len(ev) - 1)], -1)
        lst = np.where(k > 0, ev[np.maximum(k - 1, 0)], -1)
        h_to = np.where((nxt > 0) & (nxt - close_ms <= 8 * D_MS), (nxt - close_ms) / H_MS, np.nan)
        h_since = np.where((lst > 0) & (close_ms - lst <= 8 * D_MS), (close_ms - lst) / H_MS, np.nan)
        out["eia_h_to_next"], out["eia_h_since_last"] = h_to, h_since
        out["eia_next"] = np.clip(1.0 - h_to / EIA_NEAR_H, 0.0, 1.0)
        out["eia_since"] = np.clip(1.0 - h_since / EIA_NEAR_H, 0.0, 1.0)
    t = eia_table(src_dir)
    if not len(t):
        return
    k = t["known_at"].values
    j = lambda v: _asof(k, v, close_ms, EIA_MAX_AGE)                  # noqa: E731
    kb = 1000.0                                                        # thousand barrels -> million barrels
    crude, cchg, cnorm = j(t["crude"]), j(t["crude_chg"]), j(t["crude_chg_norm"])
    cush, uchg, unorm = j(t["cushing"]), j(t["cushing_chg"]), j(t["cushing_chg_norm"])
    pchg, pnorm = j(t["prod_chg"]), j(t["prod_chg_norm"])
    lvl_norm = j(t["crude_norm"])
    vs5 = 100.0 * (crude / lvl_norm - 1.0)
    out.update({"eia_crude_mb": crude / kb, "eia_crude_chg_mb": cchg / kb, "eia_crude_norm_mb": cnorm / kb,
                "eia_crude_vs5y_pct": vs5, "eia_cushing_mb": cush / kb, "eia_cushing_chg_mb": uchg / kb,
                "eia_cushing_norm_mb": unorm / kb, "eia_gas_chg_mb": j(t["gasoline_chg"]) / kb,
                "eia_dist_chg_mb": j(t["distillate_chg"]) / kb, "eia_prod_norm_mb": pnorm / kb,
                "eia_week_age_d": (close_ms - j(t["date_ms"].astype(float))) / D_MS,
                "eia_crude": _clip(-(cchg - cnorm) / CRUDE_UNIT), "eia_cushing": _clip(-(uchg - unorm) / CUSHING_UNIT),
                "eia_products": _clip(-(pchg - pnorm) / PROD_UNIT), "eia_level": _clip(-vs5 / LEVEL_UNIT_PCT)})


def _opec(out, close_ms, asset, src_dir, bars):
    m = opec_meetings(src_dir)
    if not len(m) or not len(close_ms):
        return
    ms, seen = m["ms"].values.astype("int64"), m["seen_ms"].values.astype("int64")
    to = np.full(len(close_ms), np.nan)
    for i in range(len(m)):                                            # ~50 meetings: a loop is cheap
        live = (close_ms >= seen[i]) & (close_ms < ms[i])
        cand = (ms[i] - close_ms) / D_MS
        to = np.where(live & ~(to <= cand), cand, to)
    k = np.searchsorted(np.sort(ms), close_ms, side="right")
    srt = np.sort(ms)
    since = np.where(k > 0, (close_ms - srt[np.maximum(k - 1, 0)]) / D_MS, np.nan)
    out["opec_days_to_next"], out["opec_days_since_last"] = to, since
    out["opec_week"] = np.where(to <= OPEC_NEAR_D, np.clip(1.0 - to / OPEC_NEAR_D, 0.0, 1.0), 0.0)
    out["opec_after"] = np.where(since <= OPEC_NEAR_D, np.clip(1.0 - since / OPEC_NEAR_D, 0.0, 1.0), 0.0)


def _pct_rank(s):
    return 100.0 * s.rolling(PCT_DAYS, min_periods=PCT_MIN).rank(pct=True)


def _oilvol(out, close_ms, asset, src_dir, bars):
    y = _load("y_ovx", ["date", "close"], src_dir)
    y = y[y["close"] > 0].reset_index(drop=True)
    ovx = None
    if len(y):
        c = y["close"]
        k = U.ny_ms_vec(y["date"].values, *OVX_KNOWN)
        j = lambda v: _asof(k, v, close_ms, DAILY_MAX_AGE)              # noqa: E731
        pct = _pct_rank(c)
        ovx = j(c)
        out.update({"ovol_ovx": ovx, "ovol_ovx_pct": j(pct), "ovol_ovx_chg5": j(c - c.shift(5)),
                    "ovol_level": j(pct / 50.0 - 1.0), "ovol_chg5": _clip(j(np.log(c / c.shift(5))) / OVX_CHG5_UNIT)})
    s = _bar_closes(asset, bars)
    s = s[s > 0]
    if len(s):
        kms = s.index.values.astype("int64") + BAR_MS
        r = np.log(s).diff()
        rv = {}
        for tag, n in RV_BARS:
            rv[tag] = _asof(kms, (r.rolling(n, min_periods=int(n * 0.8)).std() * np.sqrt(BARS_YEAR) * 100.0).values,
                            close_ms, BAR_MAX_AGE)
            out["ovol_rv" + tag] = rv[tag]
        out["ovol_rv_trend"] = _clip(np.log(rv["5d"] / rv["20d"]) / np.log(2.0))
        if ovx is not None:
            ratio = ovx / rv["20d"]
            out["ovol_iv_rv"] = ratio
            out["ovol_vrp"] = _clip(np.log(ratio) / np.log(2.0))


def cot_table(market, src_dir=None):
    """market 'wti' (CFTC) or 'brent' (ICE) -> the stored reports with readings and known_at (as cot.table)."""
    from . import cot
    d = _load("cot_" + market, COT_COLS, src_dir)
    if not len(d):
        return d
    net = d["long"] - d["short"]
    oi = d["oi"].where(d["oi"] > 0)
    d["net"], d["net_chg"], d["net_pct"] = net, net.diff(), 100.0 * net / oi
    d["pctile"] = d["net_pct"].rolling(COT_PCT_WEEKS, min_periods=COT_PCT_MIN).rank(pct=True)
    dp = d["net_pct"].diff()
    sd = dp.rolling(COT_PCT_WEEKS, min_periods=COT_PCT_MIN).std()
    d["chg_z"] = dp / sd.where(sd > 0)
    rel = cot.release_ms if market == "wti" else ice_release_ms
    rule = np.array([rel(x) for x in d["date"]], dtype="int64")
    late = d["known_ms"].values
    known = np.where(np.isfinite(late), np.maximum(np.nan_to_num(late, nan=0).astype("int64"), rule), rule)
    d["known_at"] = np.maximum.accumulate(known)
    d["date_ms"] = U.ny_ms_vec(d["date"].values, 0, 0)
    return d


def _oilpos(out, close_ms, asset, src_dir, bars):
    t = cot_table("wti" if asset == "WTI" else "brent", src_dir)
    if not len(t):
        return
    k = t["known_at"].values
    j = lambda v: _asof(k, v, close_ms, COT_MAX_AGE)                  # noqa: E731
    out.update({"opos_level": _clip(j(t["net_pct"]) / COT_LEVEL_UNIT), "opos_pctile": 2.0 * j(t["pctile"]) - 1.0,
                "opos_chg": _clip(j(t["chg_z"]) / COT_CHG_UNIT), "opos_net": j(t["net"]), "opos_net_chg": j(t["net_chg"]),
                "opos_oi": j(t["oi"]), "opos_net_pct_oi": j(t["net_pct"]), "opos_pctile_3y": 100.0 * j(t["pctile"]),
                "opos_report_age_d": (close_ms - j(t["date_ms"].astype(float))) / D_MS})


CURVE_COLS = ["date", "m1_sym", "m1", "m2_sym", "m2"]


def _oilspread(out, close_ms, asset, src_dir, bars):
    w, b = _bar_closes("WTI", bars), _bar_closes("BRENT", bars)
    sign = -1.0 if asset == "WTI" else 1.0                             # positive = this market gaining on the other
    if len(w) and len(b):
        j = pd.DataFrame({"w": w, "b": b}).dropna()
        j = j[(j["w"].abs() > 0) & (j["b"].abs() > 0)]
        if len(j):
            sp = j["b"] - j["w"]
            kms = j.index.values.astype("int64") + BAR_MS
            z20 = (sp - sp.rolling(SPREAD_Z20, min_periods=SPREAD_Z20 // 4).mean()) / \
                sp.rolling(SPREAD_Z20, min_periods=SPREAD_Z20 // 4).std()
            z250 = (sp - sp.rolling(SPREAD_Z250, min_periods=SPREAD_Z250_MIN).mean()) / \
                sp.rolling(SPREAD_Z250, min_periods=SPREAD_Z250_MIN).std()
            chg = sp - sp.shift(SPREAD_1D)
            a = lambda v: _asof(kms, np.asarray(v, dtype=float), close_ms, BAR_MAX_AGE)   # noqa: E731
            z20r, z250r, chgr = a(z20), a(z250), a(chg)
            out.update({"ospr_spread": a(sp), "ospr_spread_z20": z20r, "ospr_spread_z250": z250r,
                        "ospr_spread_chg1d": chgr, "ospr_z20": _clip(sign * z20r / SPREAD_Z_UNIT),
                        "ospr_z250": _clip(sign * z250r / SPREAD_Z_UNIT), "ospr_chg1d": _clip(sign * chgr / SPREAD_CHG_UNIT)})
    # the curve: Yahoo archive first, EIA's 2012-2024 contract prices where Yahoo has nothing (WTI only)
    frames = []
    yc = _load("curve_" + asset.lower(), CURVE_COLS, src_dir).dropna(subset=["m1", "m2"])
    if len(yc):
        frames.append((yc["m1"].values, yc["m2"].values, U.ny_ms_vec(yc["date"].values, *CURVE_KNOWN),
                       U.ny_ms_vec(yc["date"].values, 0, 0), CURVE_Y_MAX_AGE))
    if asset == "WTI":
        ec = _load("curve_eia_wti", ["date", "c1", "c2"], src_dir).dropna(subset=["c1", "c2"])
        if len(ec):
            frames.append((ec["c1"].values, ec["c2"].values, eia_curve_known_ms(ec["date"].values),
                           U.ny_ms_vec(ec["date"].values, 0, 0), CURVE_EIA_MAX_AGE))
    m1 = m2 = age = None
    for f1, f2, kn, dms, mx in frames:
        a1, a2 = _asof(kn, f1, close_ms, mx), _asof(kn, f2, close_ms, mx)
        ad = (close_ms - _asof(kn, dms.astype(float), close_ms, mx)) / D_MS
        if m1 is None:
            m1, m2, age = a1, a2, ad
        else:
            fill = ~np.isfinite(m1)
            m1, m2, age = np.where(fill, a1, m1), np.where(fill, a2, m2), np.where(fill, ad, age)
    if m1 is not None:
        cu = m1 - m2
        cp = 100.0 * cu / np.where(np.abs(m1) > 1.0, np.abs(m1), np.nan)   # April 2020: a negative front month
        out.update({"ospr_m1": m1, "ospr_m2": m2, "ospr_curve_usd": cu, "ospr_curve_pct": cp, "ospr_curve_age_d": age,
                    "ospr_curve": _clip(cp / CURVE_UNIT_PCT)})


_CARDS = OrderedDict([("eia", _eia), ("opec", _opec), ("oilvol", _oilvol), ("oilpos", _oilpos), ("oilspread", _oilspread)])


def features(index15, asset, bars=None, src_dir=None, strict=False):
    """-> frame on index15 (15m bar OPEN times, UTC; a row is known at open + 15 min): FEATURES (float,
    0.0 = no read, never NaN) and RAW (NaN = no read). Only WTI and BRENT get readings; any other asset
    gets the empty frame. bars: optional {asset: 15m frame} instead of the project's files (the spread
    card reads both WTI and BRENT). strict: raise on a broken source (tests)."""
    index15 = pd.DatetimeIndex(index15)
    close_ms = np.asarray(index15.as_unit("ms").asi8, dtype="int64") + BAR_MS
    if isinstance(bars, pd.DataFrame):                                 # one frame: this asset's own bars
        bars = {asset: bars}
    cols, errors = {}, {}
    for name, fn in _CARDS.items():
        if asset not in APPLIES[name]:
            continue
        part = {}
        try:
            fn(part, close_ms, asset, src_dir, bars)
            cols.update(part)
        except Exception as e:                                        # a broken file silences its card, not the engine
            if strict:
                raise
            errors[name] = "%s: %s" % (type(e).__name__, str(e)[:160])
    block = np.full((len(index15), len(FEATURES) + len(RAW)), np.nan)
    for i, c in enumerate(FEATURES + RAW):
        if c in cols:
            block[:, i] = np.asarray(cols[c], dtype=float)
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
    return U.num(row, key)


def _sg(x, fmt="%+.1f"):
    return "n/a" if x is None else fmt % x


def _f(x, fmt, unit=""):
    return "n/a" if x is None else (fmt % x) + unit


def _close(row):
    try:
        return pd.Timestamp(row.name) + pd.Timedelta(milliseconds=BAR_MS)
    except Exception:
        return None


def _when(row, days_back, fmt="%a %d %b %Y"):
    c = _close(row)
    if c is None or days_back is None:
        return "n/a"
    return (c - pd.Timedelta(days=days_back)).tz_convert(U.NY).strftime(fmt)


def _hours(h):
    if h is None:
        return "n/a"
    return "%.1f hours" % h if h < 48 else "%.1f days" % (h / 24.0)


def _eia_words(row, asset):
    to, since = _n(row, "eia_h_to_next"), _n(row, "eia_h_since_last")
    s = "Next weekly EIA petroleum report in %s, the last one %s ago" % (_hours(to), _hours(since))
    crude = _n(row, "eia_crude_mb")
    if crude is None:
        return s + "; no EIA stock figures on file for this time."
    ch, nm, vs = _n(row, "eia_crude_chg_mb"), _n(row, "eia_crude_norm_mb"), _n(row, "eia_crude_vs5y_pct")
    s += ". Week ending %s: U.S. commercial crude %.1f million barrels, %s Mb on the week" % (
        _when(row, _n(row, "eia_week_age_d"), "%d %b %Y"), crude, _sg(ch))
    if nm is not None:
        s += " against a 5-year norm of %s Mb for that week" % _sg(nm)
        if ch is not None:
            s += " (%s)" % ("a bigger draw than usual" if ch < nm else "a bigger build than usual")
    if vs is not None:
        s += ", %s%% against its 5-year average level" % _sg(vs)
    cu = _n(row, "eia_cushing_mb")
    if cu is not None:
        s += "; Cushing %.1f Mb (%s Mb, norm %s)" % (cu, _sg(_n(row, "eia_cushing_chg_mb")),
                                                  _sg(_n(row, "eia_cushing_norm_mb")))
    s += "; gasoline %s Mb, distillate %s Mb (products norm %s Mb)" % (
        _sg(_n(row, "eia_gas_chg_mb")), _sg(_n(row, "eia_dist_chg_mb")), _sg(_n(row, "eia_prod_norm_mb")))
    return s + "."


def _opec_words(row, asset):
    to, since = _n(row, "opec_days_to_next"), _n(row, "opec_days_since_last")
    c = _close(row)
    m = opec_meetings()
    title_to = title_since = None
    if c is not None and len(m):
        cms = int(c.value // 1000000)
        if to is not None:
            hit = m[(m["ms"] - cms - to * D_MS).abs() < H_MS]
            title_to = None if not len(hit) else "%s on %s" % (hit["title"].iloc[0], hit["day"].iloc[0])
        if since is not None:
            hit = m[(cms - m["ms"] - since * D_MS).abs() < H_MS]
            title_since = None if not len(hit) else "%s on %s" % (hit["title"].iloc[-1], hit["day"].iloc[-1])
    if to is not None:
        s = "Next meeting in %.1f days (%s)%s" % (to, title_to or "on the calendar",
                                                 ", inside the week before it" if to <= OPEC_NEAR_D else "")
    else:
        s = "No OPEC or OPEC+ meeting on the calendar in the next three weeks"
    if since is not None:
        s += "; the last, %s, was %.0f days ago" % (title_since or "on file", since)
        if to is None and since > 45:
            s += " (the meeting calendar in calhistory may need its newer dates)"
    return s + "."


def _vol_words(row, asset):
    v = _n(row, "ovol_ovx")
    parts = []
    if v is not None:
        p = _n(row, "ovol_ovx_pct")
        parts.append("Crude oil volatility index OVX %.1f (%s, %s points over 5 days)" % (
            v, "percentile n/a" if p is None else "%s percentile of the past year" % U.ordinal(p),
            _sg(_n(row, "ovol_ovx_chg5"))))
    r1, r5, r20 = _n(row, "ovol_rv1d"), _n(row, "ovol_rv5d"), _n(row, "ovol_rv20d")
    if r20 is not None or r5 is not None:
        parts.append("%s realised volatility from the 15m bars %s%% (1 day) / %s%% (5 days) / %s%% (20 days), annualised"
                     % ("WTI" if asset == "WTI" else "Brent", _f(r1, "%.0f"), _f(r5, "%.0f"), _f(r20, "%.0f")))
    ivr = _n(row, "ovol_iv_rv")
    if ivr is not None:
        parts.append("OVX is %.2fx the 20-day realised figure" % ivr)
    if not parts:
        return "No read: no OVX close and no bars on file for this time."
    return parts[0] + "".join("; " + p for p in parts[1:]) + "."


def _pos_words(row, asset):
    mk = "NYMEX WTI crude (CFTC)" if asset == "WTI" else "ICE Brent crude (ICE Futures Europe)"
    net = _n(row, "opos_net")
    if net is None:
        return "No managed-money report on file for %s at this close (none published yet, or the last is over two weeks old)." % mk
    s = "In the latest report for %s (positions as of %s), managed money was net %s %s contracts" % (
        mk, _when(row, _n(row, "opos_report_age_d")), "long" if net >= 0 else "short", format(abs(net), ",.0f"))
    pct, chg, pc = _n(row, "opos_net_pct_oi"), _n(row, "opos_net_chg"), _n(row, "opos_pctile_3y")
    if pct is not None:
        s += " (%.1f%% of open interest)" % pct
    if chg is not None:
        s += ", %s on the week" % format(chg, "+,.0f")
    if pc is not None:
        s += "; that net share sits at the %s percentile of the last 3 years" % U.ordinal(pc)
    return s + "."


def _spread_words(row, asset):
    sp = _n(row, "ospr_spread")
    parts = []
    if sp is not None:
        parts.append("Brent minus WTI $%.2f (z-score %s over 20 days, %s over a year; %s on the day)" % (
            sp, _sg(_n(row, "ospr_spread_z20"), "%+.1f"), _sg(_n(row, "ospr_spread_z250"), "%+.1f"),
            _sg(_n(row, "ospr_spread_chg1d"), "%+.2f")))
    cp = _n(row, "ospr_curve_pct")
    if cp is not None:
        parts.append("front month minus second month %s (%s%%, %s; prices of %s)" % (
            _sg(_n(row, "ospr_curve_usd"), "%+.2f"), _sg(cp, "%+.2f"), "backwardation" if cp > 0 else "contango",
            _when(row, _n(row, "ospr_curve_age_d"), "%d %b %Y")))
    else:
        parts.append("no front-versus-second-month prices on file for this time (free history: WTI 2012 to "
                     "April 2024 from the EIA, then Yahoo's live contracts from Nov 2026)")
    if sp is None and cp is None:
        return "No read: no Brent and WTI bars at a common time and no curve prices."
    return parts[0][0].upper() + parts[0][1:] + "".join("; " + p for p in parts[1:]) + "."


_WORDS = OrderedDict([("eia", _eia_words), ("opec", _opec_words), ("oilvol", _vol_words), ("oilpos", _pos_words),
                      ("oilspread", _spread_words)])


def describe(row, asset):
    """One row of features() -> {card title: one plain-English sentence}, for WTI and BRENT. States what was
    read; forecasts nothing."""
    out = OrderedDict()
    for name, fn in _WORDS.items():
        if asset in APPLIES[name]:
            try:
                out[GROUPS[name][0]] = fn(row, asset)
            except Exception as e:                                    # pragma: no cover
                out[GROUPS[name][0]] = "No read (%s)." % type(e).__name__
    return out


def facts(row, asset):
    """One row of features() -> {card title: [[label, value], ...]} in natural units."""
    n = lambda k: _n(row, k)                                           # noqa: E731
    out = OrderedDict()
    if asset not in OIL:
        return out
    out[GROUPS["eia"][0]] = [
        ["Next EIA weekly report in", _hours(n("eia_h_to_next"))],
        ["Last EIA weekly report", "n/a" if n("eia_h_since_last") is None else _hours(n("eia_h_since_last")) + " ago"],
        ["Week ending", _when(row, n("eia_week_age_d"), "%d %b %Y")],
        ["U.S. commercial crude", _f(n("eia_crude_mb"), "%.1f", " Mb") + " (%s%% vs 5-year average)" % _sg(n("eia_crude_vs5y_pct"))],
        ["Crude change / 5-year norm", "%s / %s Mb" % (_sg(n("eia_crude_chg_mb")), _sg(n("eia_crude_norm_mb")))],
        ["Cushing stocks, change / norm", "%s (%s / %s Mb)" % (_f(n("eia_cushing_mb"), "%.1f", " Mb"),
                                                             _sg(n("eia_cushing_chg_mb")), _sg(n("eia_cushing_norm_mb")))],
        ["Gasoline / distillate change", "%s / %s Mb (products norm %s)" % (
            _sg(n("eia_gas_chg_mb")), _sg(n("eia_dist_chg_mb")), _sg(n("eia_prod_norm_mb")))]]
    out[GROUPS["opec"][0]] = [
        ["Days to next meeting", "none on the calendar within 3 weeks" if n("opec_days_to_next") is None
         else "%.1f" % n("opec_days_to_next")],
        ["Days since last meeting", _f(n("opec_days_since_last"), "%.0f")]]
    out[GROUPS["oilvol"][0]] = [
        ["OVX (Cboe crude oil volatility)", "n/a" if n("ovol_ovx") is None else "%.2f (%s; %s over 5 days)" % (
            n("ovol_ovx"), "percentile n/a" if n("ovol_ovx_pct") is None else "%s percentile of the past year" % U.ordinal(n("ovol_ovx_pct")),
            _sg(n("ovol_ovx_chg5"), "%+.2f"))],
        ["Realised vol 1d / 5d / 20d (annualised)", "%s / %s / %s" % (_f(n("ovol_rv1d"), "%.1f", "%"), _f(n("ovol_rv5d"), "%.1f", "%"),
                                                                     _f(n("ovol_rv20d"), "%.1f", "%"))],
        ["OVX / 20-day realised", _f(n("ovol_iv_rv"), "%.2f", "x")]]
    out[GROUPS["oilpos"][0]] = [
        ["Market", "NYMEX WTI, CFTC disaggregated, managed money" if asset == "WTI" else
         "ICE Brent, ICE Futures Europe COT, managed money"],
        ["Positions as of", _when(row, n("opos_report_age_d"))],
        ["Net position", "n/a" if n("opos_net") is None else "%s contracts" % format(n("opos_net"), "+,.0f")],
        ["Weekly change", "n/a" if n("opos_net_chg") is None else "%s contracts" % format(n("opos_net_chg"), "+,.0f")],
        ["Net as % of open interest", _f(n("opos_net_pct_oi"), "%+.1f", "%")],
        ["3-year percentile", _f(n("opos_pctile_3y"), "%.0f")]]
    out[GROUPS["oilspread"][0]] = [
        ["Brent - WTI (15m bars)", _f(n("ospr_spread"), "$%.2f")],
        ["z-score 20 days / 1 year", "%s / %s" % (_sg(n("ospr_spread_z20"), "%+.2f"), _sg(n("ospr_spread_z250"), "%+.2f"))],
        ["1-day change", _sg(n("ospr_spread_chg1d"), "%+.2f")],
        ["Front / second month", "%s / %s" % (_f(n("ospr_m1"), "%.2f"), _f(n("ospr_m2"), "%.2f"))],
        ["Front - second (+ = backwardation)", "n/a" if n("ospr_curve_usd") is None else "%+.2f (%+.2f%%), prices of %s" % (
            n("ospr_curve_usd"), n("ospr_curve_pct") or 0.0, _when(row, n("ospr_curve_age_d"), "%d %b %Y"))]]
    return out


# ------------------------------------------------------------------ fetch (update only)
def _sleep_after():
    if PAUSE_S:
        time.sleep(PAUSE_S)


def _get_text(url, params=None):
    r = U.get(url, params=params, pause=PAUSE_S, timeout=TIMEOUT)
    return r.content.decode("utf-8-sig", "replace")


def fetch_eia_weekly():
    """-> frame date, crude, cushing, gasoline, distillate (thousand barrels) from the EIA's history pages."""
    parts = []
    for key, sid in EIA_SERIES.items():
        d = parse_eia_weekly(_get_text(EIA_LEAF, {"n": "PET", "s": sid, "f": "W"}))
        if len(d) < 100:
            raise RuntimeError("EIA %s: only %d weeks parsed" % (sid, len(d)))
        parts.append(d.set_index("date")["value"].rename(key))
    out = pd.concat(parts, axis=1).sort_index()
    out = out[out.index >= EIA_KEEP_FROM]
    return out.reset_index().rename(columns={"index": "date"})


def fetch_eia_curve():
    parts = []
    for key, sid in (("c1", "RCLC1"), ("c2", "RCLC2")):
        d = parse_eia_daily(_get_text(EIA_LEAF, {"n": "PET", "s": sid, "f": "D"}))
        if len(d) < 1000:
            raise RuntimeError("EIA %s: only %d days parsed" % (sid, len(d)))
        parts.append(d.set_index("date")["value"].rename(key))
    out = pd.concat(parts, axis=1).sort_index().dropna()
    return out[out.index >= EIA_KEEP_FROM].reset_index().rename(columns={"index": "date"})


def fetch_cftc_wti(since=None):
    from . import cot
    sel = ["report_date_as_yyyy_mm_dd", "open_interest_all", "m_money_positions_long_all", "m_money_positions_short_all"]
    where = "cftc_contract_market_code='%s' AND report_date_as_yyyy_mm_dd %s '%sT00:00:00'" % (
        WTI_CFTC_CODE, ">" if since else ">=", since or COT_START)
    rows = U.get(cot.API % cot.DISAGG, {"$select": ",".join(sel), "$where": where,
                                        "$order": "report_date_as_yyyy_mm_dd ASC", "$limit": 5000},
                 pause=PAUSE_S, timeout=TIMEOUT).json()
    if not isinstance(rows, list):
        raise RuntimeError("unexpected reply: %s" % str(rows)[:80])
    f = lambda r, k: float(r[k]) if r.get(k) not in (None, "") else np.nan    # noqa: E731
    return pd.DataFrame([{"date": str(r["report_date_as_yyyy_mm_dd"])[:10], "oi": f(r, "open_interest_all"),
                          "long": f(r, "m_money_positions_long_all"), "short": f(r, "m_money_positions_short_all")}
                         for r in rows], columns=["date", "oi", "long", "short"])


def fetch_ice_brent(years):
    parts = []
    for y in years:
        try:
            parts.append(parse_ice_cot(_get_text(ICE_URL % y)))
        except Exception:
            if y == max(years):
                raise
    if not parts:
        return pd.DataFrame(columns=["date", "oi", "long", "short"])
    d = pd.concat(parts, ignore_index=True)
    return d.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)


def _yahoo_daily(sess, symbol, start_day):
    from . import xmarket
    return xmarket.parse_yahoo_daily(xmarket._yahoo_json(sess, symbol, start_day))


# ---- jobs: each returns rows on disk; raises on failure
def _merge_write(old, new, cols, name, d, keep="first"):
    both = pd.concat([old[cols], new[cols]], ignore_index=True) if len(old) else new[cols]
    both = both.drop_duplicates("date", keep=keep).sort_values("date")
    U.write_csv(both, path(name, d))
    return len(both)


def _weekly_job(name, cols, d, st, now, release_of, fetch_new):
    """The cot pattern: ask only once the next report's release has passed (then every 30 minutes until it
    is there); a report that was due and missing counts from when it is first seen."""
    old = _load(name, cols, d)
    last = old["date"].iloc[-1] if len(old) else None
    if last is not None:
        due = release_of((pd.Timestamp(last) + pd.Timedelta(days=7)).strftime("%Y-%m-%d"))
        if now < due:
            return "fresh"
    if now - int(st.get("last_check_ms", 0)) < RETRY_MS:
        return "fresh"
    st["last_check_ms"] = now
    new = fetch_new(last)
    new = new[new["date"] > last] if last is not None else new
    new = new[[release_of(x) <= now for x in new["date"]]] if len(new) else new
    if last is not None and not len(new):
        st.setdefault("missing_since_ms", now)
        return len(old)
    late = st.pop("missing_since_ms", None)
    new = new.copy()
    new["first_seen_ms"] = float(now)
    new["known_ms"] = [float(now) if late is not None and late > release_of(x) else np.nan for x in new["date"]]
    return _merge_write(old, new, cols, name, d)


def _job_eia(d, st, now):
    cols = ["date"] + list(EIA_SERIES) + ["first_seen_ms", "known_ms"]

    def fetch_new(last):
        f = fetch_eia_weekly()
        return f.dropna(subset=list(EIA_SERIES))                       # a week counts once all four series show it
    return _weekly_job("eia_weekly", cols, d, st, now, lambda w: int(eia_release_for([w], d)[0]), fetch_new)


def _job_cot_wti(d, st, now):
    from . import cot
    return _weekly_job("cot_wti", COT_COLS, d, st, now, cot.release_ms, fetch_cftc_wti)


def _job_cot_brent(d, st, now):
    def fetch_new(last):
        y_now = pd.Timestamp(now, unit="ms").year
        y0 = int(COT_START[:4]) if last is None else min(int(last[:4]), y_now)
        return fetch_ice_brent(list(range(y0, y_now + 1)))
    return _weekly_job("cot_brent", COT_COLS, d, st, now, ice_release_ms, fetch_new)


def _daily_due(last, st, now, known_hm, cal="nyse"):
    if now - int(st.get("last_try_ms", 0)) < RETRY_MS:
        return False
    if last is None or now - int(st.get("last_try_ms", 0)) >= SAFETY_MS:
        return True
    from . import xmarket
    return xmarket._next_known("yahoo", last, known_hm) <= now


def _job_ovx(d, st, now, sess):
    old = _load("y_ovx", ["date", "close"], d)
    last = old["date"].iloc[-1] if len(old) else None
    if not _daily_due(last, st, now, OVX_KNOWN):
        return "fresh"
    st["last_try_ms"] = now
    start = OVX_FROM if last is None else (pd.Timestamp(last) - pd.Timedelta(days=21)).strftime("%Y-%m-%d")
    new = _yahoo_daily(sess, OVX_SYMBOL, start)[["date", "close"]]
    new = new[U.ny_ms_vec(new["date"].values, *OVX_KNOWN) <= now] if len(new) else new
    if not len(new) and not len(old):
        raise RuntimeError("no final OVX closes in the reply")
    return _merge_write(old, new, ["date", "close"], "y_ovx", d, keep="last")


def _job_curve_yahoo(asset, d, st, now, sess):
    root = "CL" if asset == "WTI" else "BZ"
    name = "curve_" + asset.lower()
    old = _load(name, CURVE_COLS, d)
    last = old["date"].iloc[-1] if len(old) else None
    if not _daily_due(last, st, now, CURVE_KNOWN):
        return "fresh"
    st["last_try_ms"] = now
    today = U.ny_date(now)
    a, b = front_two(root, today)
    s1, s2 = yahoo_symbol(root, a), yahoo_symbol(root, b)
    start = (pd.Timestamp(today) - pd.Timedelta(days=60)).strftime("%Y-%m-%d")
    y1 = _yahoo_daily(sess, s1, start).set_index("date")["close"]
    y2 = _yahoo_daily(sess, s2, start).set_index("date")["close"]
    j = pd.DataFrame({"m1": y1, "m2": y2}).dropna()
    rows = []
    for day, r in j.iterrows():
        if U.ny_ms(day, *CURVE_KNOWN) > now:                           # a day is stored once its close is final
            continue
        if front_two(root, day) != (a, b):                             # only days these two were front and second
            continue
        rows.append((day, s1, float(r["m1"]), s2, float(r["m2"])))
    new = pd.DataFrame(rows, columns=CURVE_COLS)
    if not len(new):
        return len(old)
    return _merge_write(old, new, CURVE_COLS, name, d, keep="last")


def _job_curve_eia(d, st, now):
    if os.path.exists(path("curve_eia_wti", d)):
        return "fresh"                                                  # the EIA stopped the series in April 2024
    if now - int(st.get("last_try_ms", 0)) < 6 * H_MS:
        return "fresh"
    st["last_try_ms"] = now
    f = fetch_eia_curve()
    U.write_csv(f[["date", "c1", "c2"]], path("curve_eia_wti", d))
    return len(f)


def update(log=print, src_dir=None, force=False):
    """Fetch / extend the oil_* files. -> {job: rows on disk, "fresh", or "failed: why"}. Never raises; a
    failed job keeps its old file and is tried again after 30 minutes. Each job asks only when something
    new should be public by now (weekly reports after their release, daily closes after the close), so
    most 15-minute calls make no request. force=True forgets the throttles (not the release rule)."""
    out = OrderedDict()
    try:
        import requests
        d = src_dir or SRC_DIR
        os.makedirs(d, exist_ok=True)
        state = U.load_state(state_path(d))
        if force:
            for v in state.values():
                if isinstance(v, dict):
                    v.pop("last_try_ms", None)
                    v.pop("last_check_ms", None)
        sess = requests.Session()
        jobs = [("eia_weekly", lambda st, now: _job_eia(d, st, now)),
                ("cot_wti", lambda st, now: _job_cot_wti(d, st, now)),
                ("cot_brent", lambda st, now: _job_cot_brent(d, st, now)),
                ("y_ovx", lambda st, now: _job_ovx(d, st, now, sess)),
                ("curve_wti", lambda st, now: _job_curve_yahoo("WTI", d, st, now, sess)),
                ("curve_brent", lambda st, now: _job_curve_yahoo("BRENT", d, st, now, sess)),
                ("curve_eia_wti", lambda st, now: _job_curve_eia(d, st, now))]
        for name, job in jobs:
            st = state.setdefault(name, {})
            try:
                out[name] = job(st, U.now_ms())
            except Exception as e:                                     # a failed source keeps its old file
                st["last_try_ms"] = st["last_check_ms"] = U.now_ms()
                out[name] = "failed: %s" % (str(e)[:120] or type(e).__name__)
            U.save_state(state_path(d), state)
    except Exception as e:
        out["all"] = "failed: %s" % (str(e)[:120] or type(e).__name__)
    try:
        if log:
            done = ["%s %s" % (k, v) for k, v in out.items() if v != "fresh"]
            log("sources.oil: %s" % ("; ".join(done) if done else "all fresh"))
    except Exception:
        pass
    return out
