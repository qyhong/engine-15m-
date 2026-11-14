# -*- coding: utf-8 -*-
"""cot -- "Futures positioning (CFTC)": the weekly Commitments of Traders report for the four
non-crypto markets.

  XAUUSD   COMEX gold (088691)             disaggregated report, MANAGED MONEY
  XAGUSD   COMEX silver (084691)           disaggregated report, MANAGED MONEY
  USDJPY   CME Japanese yen (097741)       traders in financial futures, LEVERAGED FUNDS
  SPX      CME E-mini S&P 500 (13874A)     traders in financial futures, LEVERAGED FUNDS
                                           (asset managers are kept beside them for reading)

Source: the CFTC's public reporting API (publicreporting.cftc.gov, Socrata, no key), futures-only
reports. Kept from 2015 so that the 3-year percentile can speak from 2018 on.
Files: data/sources/cot_<asset>.csv (one row per report date, only ever extended) and
data/sources/cot_state.json (when the API was last asked, and reports seen to be late).

THE ONE RULE (tests/test_cot.py): positions are AS OF a Tuesday but PUBLISHED on the Friday at
15:30 New York time; a report reaches a 15m row only from its release on. The release of every
report is computed from the CFTC's calendar rules:
  - the Friday of the report's week at 15:30 ET;
  - one business day later (the Monday) when a federal holiday falls on the Wednesday, Thursday or
    Friday after the report date (this reproduces the CFTC's published 2026 schedule);
  - the actual dates of the delayed catch-up releases after the 2018-19 and 2025 shutdowns and the
    2023 ION cyber incident (RELEASE_OVERRIDES, from the CFTC's announcements);
  - and, live, a report that the API did not have when its release time had passed is used only from
    the moment update() first saw it (column known_ms).

The yen future is priced in USD per yen, the opposite of USDJPY: leveraged funds net LONG the yen
future are positioned for USDJPY to FALL. The features carry the sign of the traded market (SIGN);
the readable columns keep the CFTC's own sign (the future's terms) and say so.

Docs: docs/SOURCES_cot.md. No reading here is claimed to predict anything.
"""
import datetime as dt
import os
import time
from collections import OrderedDict

import numpy as np
import pandas as pd

from . import _util as U
from ..config import DATA_DIR

SRC_DIR = os.path.join(DATA_DIR, "sources")
API = "https://publicreporting.cftc.gov/resource/%s.json"
DISAGG, TFF = "72hh-3qpy", "gpe5-46if"                         # futures-only datasets
START = "2015-01-01"
PAUSE_S = 1.0
RECHECK_MS = 30 * 60000                                       # while a due report is missing: ask every 30 minutes
MAX_AGE_MS = 15 * U.D_MS                                      # a report may stand in for one missed week, not more

MARKETS = OrderedDict([
    # asset: (dataset, contract code, name, group read, sign for the traded market)
    ("XAUUSD", (DISAGG, "088691", "COMEX gold futures", "managed-money traders", 1.0)),
    ("XAGUSD", (DISAGG, "084691", "COMEX silver futures", "managed-money traders", 1.0)),
    ("USDJPY", (TFF, "097741", "CME Japanese yen futures", "leveraged funds", -1.0)),
    ("SPX", (TFF, "13874A", "CME E-mini S&P 500 futures", "leveraged funds", 1.0)),
])
FIELDS = {DISAGG: ("m_money_positions_long_all", "m_money_positions_short_all", None, None),
          TFF: ("lev_money_positions_long", "lev_money_positions_short",
                "asset_mgr_positions_long", "asset_mgr_positions_short")}
COLS = ["date", "oi", "long", "short", "am_long", "am_short", "first_seen_ms", "known_ms"]

LEVEL_UNIT = 30.0                                             # net as 30% of open interest = 1.0
PCTILE_WEEKS, PCTILE_MIN = 156, 52                            # 3 years of weekly reports; 1 year to speak
CHG_UNIT = 3.0                                                # a weekly change of 3 standard deviations = 1.0

GROUPS = OrderedDict([("cot", ("Futures positioning (CFTC)", ["cot_level", "cot_pctile", "cot_chg"]))])
APPLIES = {"cot": tuple(MARKETS)}
FEATURES = [f for _t, fs in GROUPS.values() for f in fs]
RAW = ["cot_net", "cot_net_chg", "cot_oi", "cot_net_pct_oi", "cot_pctile_3y", "cot_am_net", "cot_report_age_d"]

# Catch-up releases that no calendar rule gives (CFTC "COT Historical Special Announcements").
RELEASE_OVERRIDES = {
    # 2018-19 lapse in appropriations: first catch-up 1 Feb 2019, then a report each Tuesday and Friday
    "2018-12-24": "2019-02-01", "2018-12-31": "2019-02-05", "2019-01-08": "2019-02-08", "2019-01-15": "2019-02-12",
    "2019-01-22": "2019-02-15", "2019-01-29": "2019-02-19", "2019-02-05": "2019-02-22", "2019-02-12": "2019-02-26",
    "2019-02-19": "2019-03-01", "2019-02-26": "2019-03-05", "2019-03-05": "2019-03-08",
    # 2023 ION cyber incident
    "2023-01-31": "2023-02-24", "2023-02-07": "2023-03-03", "2023-02-14": "2023-03-08", "2023-02-21": "2023-03-10",
    "2023-02-28": "2023-03-14", "2023-03-07": "2023-03-16", "2023-03-14": "2023-03-21",
    # 2025 lapse in appropriations (table of 9 Dec 2025)
    "2025-09-30": "2025-11-19", "2025-10-07": "2025-11-21", "2025-10-14": "2025-11-25", "2025-10-21": "2025-12-02",
    "2025-10-28": "2025-12-05", "2025-11-04": "2025-12-09", "2025-11-10": "2025-12-10", "2025-11-18": "2025-12-12",
    "2025-11-25": "2025-12-15", "2025-12-02": "2025-12-17", "2025-12-09": "2025-12-19", "2025-12-16": "2025-12-23",
}
# Days the federal government was closed by order, besides the fixed holidays.
CLOSED_DAYS = ("2018-12-05", "2018-12-24", "2019-12-24", "2020-12-24", "2024-12-24", "2025-01-09",
               "2025-12-24", "2025-12-26")


# ------------------------------------------------------------------ the release calendar
def federal_holidays(year):
    """Observed US federal holidays of one year (and orders closing the government) -> set of dates."""
    def nth(month, weekday, n):
        if n > 0:
            first = dt.date(year, month, 1)
            return first + dt.timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))
        last = dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
        return last - dt.timedelta(days=(last.weekday() - weekday) % 7)

    def observed(day):
        return day - dt.timedelta(days=1) if day.weekday() == 5 else day + dt.timedelta(days=1) if day.weekday() == 6 else day

    out = {observed(dt.date(year, 1, 1)), nth(1, 0, 3), nth(2, 0, 3), nth(5, 0, -1), observed(dt.date(year, 7, 4)),
           nth(9, 0, 1), nth(10, 0, 2), observed(dt.date(year, 11, 11)), nth(11, 3, 4), observed(dt.date(year, 12, 25))}
    if year >= 2021:
        out.add(observed(dt.date(year, 6, 19)))
    out.add(observed(dt.date(year + 1, 1, 1)))                     # a Saturday New Year is observed on 31 December
    out |= set(pd.Timestamp(d).date() for d in CLOSED_DAYS if d.startswith(str(year)))
    return out


def release_ms(report_date):
    """The moment a report with positions as of `report_date` ('YYYY-MM-DD') was / will be published, epoch ms."""
    key = str(report_date)[:10]
    if key in RELEASE_OVERRIDES:
        return U.ny_ms(RELEASE_OVERRIDES[key], 15, 30)
    d = pd.Timestamp(key).date()
    friday = d + dt.timedelta(days=(4 - d.weekday()) % 7)
    hol = federal_holidays(d.year) | federal_holidays(friday.year)
    late = any((d + dt.timedelta(days=k)) in hol and (d + dt.timedelta(days=k)).weekday() in (2, 3, 4)
               for k in range(1, (friday - d).days + 1))
    day = friday
    if late:
        day = friday + dt.timedelta(days=3)
        while day in hol or day.weekday() >= 5:
            day += dt.timedelta(days=1)
    return U.ny_ms(day, 15, 30)


# ------------------------------------------------------------------ storage
def path_for(asset, src_dir=None):
    return os.path.join(src_dir or SRC_DIR, "cot_%s.csv" % asset.lower())


def state_path(src_dir=None):
    return os.path.join(src_dir or SRC_DIR, "cot_state.json")


def load(asset, src_dir=None):
    """-> the stored reports of one market, date ascending and unique (empty frame when there is no file)."""
    d = U.read_csv(path_for(asset, src_dir), COLS)
    if not len(d):
        return pd.DataFrame(dict((c, pd.Series(dtype="float64" if c != "date" else object)) for c in COLS))
    d = d[COLS].dropna(subset=["date"]).copy()
    d["date"] = d["date"].astype(str).str[:10]
    for c in COLS[1:]:
        d[c] = pd.to_numeric(d[c], errors="coerce").astype(float)
    return d.drop_duplicates("date", keep="first").sort_values("date").reset_index(drop=True)


# ------------------------------------------------------------------ network (update only)
def fetch(asset, since=None):
    """All reports of one market dated after `since` (or from START) -> list of row dicts. Raises on failure."""
    ds, code = MARKETS[asset][0], MARKETS[asset][1]
    lf, sf, alf, asf = FIELDS[ds]
    sel = ["report_date_as_yyyy_mm_dd", "open_interest_all", lf, sf] + [f for f in (alf, asf) if f]
    where = "cftc_contract_market_code='%s' AND report_date_as_yyyy_mm_dd %s '%sT00:00:00'" % (
        code, ">" if since else ">=", since or START)
    rows = U.get(API % ds, {"$select": ",".join(sel), "$where": where, "$order": "report_date_as_yyyy_mm_dd ASC",
                            "$limit": 5000}, pause=PAUSE_S).json()
    if not isinstance(rows, list):
        raise RuntimeError("unexpected reply: %s" % str(rows)[:80])
    out = []
    for r in rows:
        f = lambda k: float(r[k]) if k and r.get(k) not in (None, "") else np.nan     # noqa: E731
        out.append({"date": str(r["report_date_as_yyyy_mm_dd"])[:10], "oi": f("open_interest_all"),
                    "long": f(lf), "short": f(sf), "am_long": f(alf), "am_short": f(asf)})
    return out


def _update_one(asset, src_dir, state, now):
    old = load(asset, src_dir)
    st = state.setdefault(asset, {})
    last = old["date"].iloc[-1] if len(old) else None
    if last is not None:
        due = release_ms((pd.Timestamp(last) + pd.Timedelta(days=7)).strftime("%Y-%m-%d"))
        if now < due:
            return len(old)                                   # the next report is not out yet: nothing to ask
        if now - int(st.get("last_check_ms", 0)) < RECHECK_MS:
            return len(old)
    rows = fetch(asset, since=last)
    st["last_check_ms"] = now
    if last is not None and not rows:
        st.setdefault("missing_since_ms", now)                # due and not there: a late report
        return len(old)
    late_since = st.pop("missing_since_ms", None)
    for r in rows:
        r["first_seen_ms"] = float(now)
        # a report the API did not have after its release time counts only from when it was first seen
        r["known_ms"] = float(now) if late_since is not None and late_since > release_ms(r["date"]) else np.nan
    new = pd.DataFrame(rows, columns=COLS)
    both = pd.concat([old, new], ignore_index=True) if len(old) else new
    both = both.drop_duplicates("date", keep="first").sort_values("date")
    U.write_csv(both[COLS], path_for(asset, src_dir))
    return len(both)


def update(log=print, src_dir=None, assets=None):
    """Fetch new weekly reports when one is due. -> {asset: rows on disk, or "failed: why"}. Never raises;
    a failure keeps the old file. Asks the API only once a report's release time has passed (then every
    30 minutes until it appears), so a normal week costs one request per market."""
    out = OrderedDict()
    try:
        state = U.load_state(state_path(src_dir))
    except Exception:
        state = {}
    for asset in assets or MARKETS:
        try:
            out[asset] = int(_update_one(asset, src_dir, state, U.now_ms()))
        except Exception as e:
            out[asset] = "failed: %s" % (str(e)[:150] or type(e).__name__)
        try:
            log("sources.cot %s: %s" % (asset, out[asset]))
        except Exception:
            pass
    U.save_state(state_path(src_dir), state)
    return out


# ------------------------------------------------------------------ the readings
def table(asset, src_dir=None):
    """-> the stored reports with every reading computed on the report grid, plus known_at (epoch ms)."""
    d = load(asset, src_dir)
    if not len(d):
        return d
    net = d["long"] - d["short"]
    oi = d["oi"].where(d["oi"] > 0)
    d["net"] = net
    d["net_chg"] = net.diff()
    d["net_pct"] = 100.0 * net / oi
    d["am_net"] = d["am_long"] - d["am_short"]
    d["pctile"] = d["net_pct"].rolling(PCTILE_WEEKS, min_periods=PCTILE_MIN).rank(pct=True)
    dp = d["net_pct"].diff()
    sd = dp.rolling(PCTILE_WEEKS, min_periods=PCTILE_MIN).std()
    d["chg_z"] = dp / sd.where(sd > 0)
    rule = np.array([release_ms(x) for x in d["date"]], dtype="int64")
    late = d["known_ms"].values
    known = np.where(np.isfinite(late), np.maximum(np.nan_to_num(late, nan=0).astype("int64"), rule), rule)
    # a report is used only once every earlier report is out too (the CFTC publishes in order), so the
    # weekly change and the percentile, computed on the report grid, never lean on an unpublished week
    d["known_at"] = np.maximum.accumulate(known)
    d["date_ms"] = U.ny_ms_vec(d["date"].values, 0, 0)
    return d


def features(index15, asset, bars=None, src_dir=None):
    """-> frame on index15 (15m bar OPEN times, UTC): FEATURES (0.0 = no read, never NaN) and RAW (NaN = no read)."""
    index15 = pd.DatetimeIndex(index15)
    close_ms = np.asarray(index15.as_unit("ms").asi8, dtype="int64") + U.BAR_MS
    out = pd.DataFrame(np.nan, index=index15, columns=FEATURES + RAW)
    errors = {}
    if asset in MARKETS:
        try:
            t = table(asset, src_dir)
            if len(t):
                sign = MARKETS[asset][4]
                k = t["known_at"].values
                j = lambda v: U.asof(k, v, close_ms, MAX_AGE_MS)                    # noqa: E731
                out["cot_level"] = np.clip(sign * j(t["net_pct"]) / LEVEL_UNIT, -1, 1)
                out["cot_pctile"] = sign * (2.0 * j(t["pctile"]) - 1.0)
                out["cot_chg"] = np.clip(sign * j(t["chg_z"]) / CHG_UNIT, -1, 1)
                for col, src in (("cot_net", "net"), ("cot_net_chg", "net_chg"), ("cot_oi", "oi"),
                                 ("cot_net_pct_oi", "net_pct"), ("cot_am_net", "am_net")):
                    out[col] = j(t[src])
                out["cot_pctile_3y"] = 100.0 * j(t["pctile"])
                rep = j(t["date_ms"].astype(float))
                out["cot_report_age_d"] = (close_ms - rep) / float(U.D_MS)
        except Exception as e:                                # a broken file is "no read", not a crash
            errors["cot"] = "%s: %s" % (type(e).__name__, str(e)[:160])
            out[:] = np.nan
    out[FEATURES] = out[FEATURES].astype(float).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    out.attrs["errors"] = errors
    return out


# ------------------------------------------------------------------ plain English
def _who(asset):
    return MARKETS[asset][3] if asset in MARKETS else "speculators"


def _report_day(row):
    age = U.num(row, "cot_report_age_d")
    if age is None:
        return None
    try:
        close = pd.Timestamp(row.name) + pd.Timedelta(milliseconds=U.BAR_MS)
        return (close - pd.Timedelta(days=age)).tz_convert(U.NY).strftime("%a %d %b %Y")
    except Exception:
        return None


def _side_words(asset, net):
    """The net position in the future's own terms, and what it means for the traded market."""
    side = "long" if net >= 0 else "short"
    if asset == "USDJPY":
        return "net %s the yen future %s contracts, i.e. positioned for USDJPY to %s" % (
            side, format(abs(net), ",.0f"), "fall" if net >= 0 else "rise")
    return "net %s %s contracts" % (side, format(abs(net), ",.0f"))


def describe(row, asset):
    """One row of features() -> {card title: one plain-English sentence}. States what was read; forecasts nothing."""
    title = GROUPS["cot"][0]
    if asset not in MARKETS:
        return {title: "No CFTC positioning is read for %s." % asset}
    net = U.num(row, "cot_net")
    if net is None:
        return {title: "No CFTC report on file for %s at this close (none published yet, or the last is over two "
                       "weeks old)." % MARKETS[asset][2]}
    chg, pct, pc = U.num(row, "cot_net_chg"), U.num(row, "cot_net_pct_oi"), U.num(row, "cot_pctile_3y")
    s = "In the CFTC report for %s (positions as of %s), %s were %s" % (
        MARKETS[asset][2], _report_day(row) or "the last report", _who(asset), _side_words(asset, net))
    if pct is not None:
        s += " (%.1f%% of open interest)" % pct
    if chg is not None:
        s += ", %s%s on the week" % ("+" if chg >= 0 else "-", format(abs(chg), ",.0f"))
    if pc is not None:
        s += "; that net share sits at the %s percentile of the last 3 years" % U.ordinal(pc)
    return {title: s + "."}


def facts(row, asset):
    """One row of features() -> {card title: [[label, value], ...]} in contracts and percentages."""
    title = GROUPS["cot"][0]
    if asset not in MARKETS:
        return {title: [["Source", "no CFTC market is mapped to %s" % asset]]}
    net = U.num(row, "cot_net")
    rows = [["Market and group", "%s, %s (CFTC %s)" % (MARKETS[asset][2], _who(asset),
                                                        "disaggregated" if MARKETS[asset][0] == DISAGG else
                                                        "traders in financial futures")]]
    if net is None:
        return {title: rows + [["Report", "no report on file for this close"]]}
    chg, oi, pct = U.num(row, "cot_net_chg"), U.num(row, "cot_oi"), U.num(row, "cot_net_pct_oi")
    pc, am, age = U.num(row, "cot_pctile_3y"), U.num(row, "cot_am_net"), U.num(row, "cot_report_age_d")
    rows.append(["Positions as of", "%s (%s days before this close; published the following Friday 15:30 ET)" % (
        _report_day(row) or "n/a", "n/a" if age is None else "%.1f" % age)])
    rows.append(["Net position", _side_words(asset, net)])
    rows.append(["Weekly change", "n/a" if chg is None else "%s contracts" % format(chg, "+,.0f")])
    rows.append(["Open interest", "n/a" if oi is None else "%s contracts" % format(oi, ",.0f")])
    rows.append(["Net as % of open interest", "n/a" if pct is None else "%+.1f%%" % pct])
    rows.append(["3-year percentile", "not enough history" if pc is None else
                 "%.0f (0 = most short, 100 = most long in 3 years)" % pc])
    if am is not None:
        rows.append(["Asset managers, net", "%s contracts" % format(am, "+,.0f")])
    if asset == "USDJPY":
        rows.append(["Sign", "the yen future is USD per yen: net long the future = positioned against USDJPY"])
    return {title: rows}
