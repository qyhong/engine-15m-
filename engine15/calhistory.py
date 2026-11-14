# -*- coding: utf-8 -*-
"""calhistory -- the historical US release calendar (2019 onward) and an oil event history.

econ.py's live calendar (data/econ_events.csv) starts in May 2026. This module keeps the
release times before that, to the minute in UTC, in data/sources/calendar_history.csv, with
the same columns as the live file plus `kind` and `source`:

    ts_ms, title, country, impact, forecast, previous, kind, source

forecast / previous are blank for history. US rows have country "USD"; the oil rows have
country "OIL" and impact "Medium" and are NEVER part of the release guard (econ.load_events()
reads us_events() only); oil_events() exposes them.

Where each kind comes from (the `source` column says it row by row):

  CPI, PPI, NFP   BLS release dates as archived by ALFRED (St. Louis Fed, the vintage-date
  PCE, GDP, JOLTS list of each release: rid 10, 46, 50, 54, 53, 192). bls.gov answers 403 to
                  scripts, so ALFRED's record is the official archive used. The clock time is
                  the agency's standard release time (8:30 ET; JOLTS 10:00 ET). Revision-only
                  vintages are dropped (CPI/PPI seasonal-factor days in February, extra
                  Employment Situation vintages, GDP second/third estimates).
  Retail Sales    the Census Bureau's own table of historical release dates (MARTSreleasedates
                  .xlsx), 8:30 ET; ALFRED rid 9 is the cross-check.
  FOMC            federalreserve.gov meeting calendars (fomccalendars.htm, fomchistorical2019/
                  2020.htm); the statement at 14:00 ET on the last meeting day; the 2020
                  emergency cuts at their own times (3 Mar 10:00 ET, Sun 15 Mar 17:00 ET).
  ISM Mfg PMI     derived: the first US business day of the month (the second in January),
                  10:00 ET. ISM's own calendar is not archived anywhere scriptable.
  EIA crude       the EIA's Weekly Petroleum Status Report archive (one folder per release
                  date); 10:30 ET on a Wednesday, 11:00 ET on a holiday-shifted day (rule).
  OPEC / OPEC+    derived from the public record (opec.org sits behind a bot challenge): the
                  ministerial meeting days, date only; the time is a nominal 13:00 UTC.

US daylight saving (second Sunday of March to the first Sunday of November) is handled by
et_to_utc_ms(). Shutdown delays (Dec 2018 - Jan 2019, Oct - Nov 2025) are in the source
dates themselves; rows in those windows carry ";irregular" in `source`.

    py -3 -m engine15.calhistory build      fetch everything, write the CSV, print a summary
    py -3 -m engine15.calhistory verify     cross-checks (Census vs ALFRED, live file, known dates)
"""
import calendar
import datetime as dt
import io
import os
import re
import sys
import time
import zipfile

import pandas as pd

from .config import DATA_DIR

HISTORY_CSV = os.path.join(DATA_DIR, "sources", "calendar_history.csv")
COLUMNS = ["ts_ms", "title", "country", "impact", "forecast", "previous", "kind", "source"]
LIVE_COLUMNS = ["ts_ms", "title", "country", "impact", "forecast", "previous"]
START = "2019-01-01"

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/130.0.0.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"}
TIMEOUT_S = 25
PAUSE_S = 2.0
ALFRED_URL = "https://alfred.stlouisfed.org/release/downloaddates?rid=%d&ff=txt"
CENSUS_RETAIL_XLSX = "https://www.census.gov/retail/marts/www/MARTSreleasedates.xlsx"
FED_CAL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
FED_HIST = "https://www.federalreserve.gov/monetarypolicy/fomchistorical%d.htm"
EIA_ARCHIVE = "https://www.eia.gov/petroleum/supply/weekly/archive/"

# kind -> (ALFRED rid, title, ET hour, ET minute, impact)
ALFRED = {"CPI": (10, None, 8, 30, "High"), "PPI": (46, "PPI m/m", 8, 30, "High"),
          "NFP": (50, None, 8, 30, "High"), "PCE": (54, "Core PCE Price Index m/m", 8, 30, "High"),
          "GDP": (53, "Advance GDP q/q", 8, 30, "High"), "JOLTS": (192, "JOLTS Job Openings", 10, 0, "Medium"),
          "RETAIL_X": (9, None, 8, 30, "High")}
RETAIL_TITLE = "Retail Sales m/m"
ISM_TITLE = "ISM Manufacturing PMI"
EIA_TITLE = "EIA Crude Oil Inventories"
MON = [None] + [calendar.month_abbr[i] for i in range(1, 13)]
MONTHS = dict((calendar.month_name[i].lower(), i) for i in range(1, 13))

# reference-month corrections the release-month rule cannot see (a delayed release that did not
# collide with the next one): release date -> (year, month) of the data
PERIOD_FIX = {("NFP", "2025-11-20"): (2025, 9), ("PPI", "2025-11-25"): (2025, 9)}
# federal funding lapses and the catch-up after them, with the kinds whose agencies were shut
IRREGULAR = [("2018-12-22", "2019-04-30", ("GDP", "PCE", "RETAIL")),
             ("2025-10-01", "2026-04-30", ("CPI", "PPI", "NFP", "JOLTS", "GDP", "PCE", "RETAIL"))]

# 2020 emergency cuts: statement day, ET hour, ET minute
FOMC_EMERGENCY = [("2020-03-03", 10, 0), ("2020-03-15", 17, 0)]

# OPEC Conference / OPEC and non-OPEC Ministerial Meeting (ONOMM) days, and the eight-country
# OPEC+ group's monthly meetings that set output from 2025. Public record, not fetched.
OPEC_MEETINGS = [
    ("2019-07-01", "OPEC Conference"), ("2019-07-02", "OPEC+ Ministerial Meeting"),
    ("2019-12-05", "OPEC Conference"), ("2019-12-06", "OPEC+ Ministerial Meeting"),
    ("2020-03-05", "OPEC Conference"), ("2020-03-06", "OPEC+ Ministerial Meeting"),
    ("2020-04-09", "OPEC+ Ministerial Meeting"), ("2020-04-12", "OPEC+ Ministerial Meeting"),
    ("2020-06-06", "OPEC+ Ministerial Meeting"), ("2020-11-30", "OPEC Conference"),
    ("2020-12-03", "OPEC+ Ministerial Meeting"), ("2021-01-05", "OPEC+ Ministerial Meeting"),
    ("2021-03-04", "OPEC+ Ministerial Meeting"), ("2021-04-01", "OPEC+ Ministerial Meeting"),
    ("2021-06-01", "OPEC+ Ministerial Meeting"), ("2021-07-18", "OPEC+ Ministerial Meeting"),
    ("2021-09-01", "OPEC+ Ministerial Meeting"), ("2021-10-04", "OPEC+ Ministerial Meeting"),
    ("2021-11-04", "OPEC+ Ministerial Meeting"), ("2021-12-02", "OPEC+ Ministerial Meeting"),
    ("2022-01-04", "OPEC+ Ministerial Meeting"), ("2022-02-02", "OPEC+ Ministerial Meeting"),
    ("2022-03-02", "OPEC+ Ministerial Meeting"), ("2022-03-31", "OPEC+ Ministerial Meeting"),
    ("2022-05-05", "OPEC+ Ministerial Meeting"), ("2022-06-02", "OPEC+ Ministerial Meeting"),
    ("2022-06-30", "OPEC+ Ministerial Meeting"), ("2022-08-03", "OPEC+ Ministerial Meeting"),
    ("2022-09-05", "OPEC+ Ministerial Meeting"), ("2022-10-05", "OPEC+ Ministerial Meeting"),
    ("2022-12-04", "OPEC+ Ministerial Meeting"), ("2023-06-04", "OPEC+ Ministerial Meeting"),
    ("2023-11-30", "OPEC+ Ministerial Meeting"), ("2024-06-02", "OPEC+ Ministerial Meeting"),
    ("2024-12-05", "OPEC+ Ministerial Meeting"), ("2025-04-03", "OPEC+ eight-country meeting"),
    ("2025-05-03", "OPEC+ eight-country meeting"), ("2025-05-28", "OPEC+ Ministerial Meeting"),
    ("2025-05-31", "OPEC+ eight-country meeting"), ("2025-07-05", "OPEC+ eight-country meeting"),
    ("2025-08-03", "OPEC+ eight-country meeting"), ("2025-09-07", "OPEC+ eight-country meeting"),
    ("2025-10-05", "OPEC+ eight-country meeting"), ("2025-11-02", "OPEC+ eight-country meeting"),
    ("2025-11-30", "OPEC+ Ministerial Meeting"), ("2026-01-04", "OPEC+ eight-country meeting"),
    ("2026-02-01", "OPEC+ eight-country meeting"), ("2026-03-01", "OPEC+ eight-country meeting"),
]
OPEC_UTC = (13, 0)


# ---------------------------------------------------------------- clock
def _nth_weekday(year, month, weekday, n):
    """n-th (1-based; -1 = last) `weekday` (Mon=0) of a month -> date."""
    if n > 0:
        d = dt.date(year, month, 1)
        d += dt.timedelta(days=(weekday - d.weekday()) % 7)
        return d + dt.timedelta(weeks=n - 1)
    d = dt.date(year, month, calendar.monthrange(year, month)[1])
    return d - dt.timedelta(days=(d.weekday() - weekday) % 7)


def us_dst(day):
    """True when New York is on daylight time on this date (rules in force since 2007)."""
    day = pd.Timestamp(day).date()
    return _nth_weekday(day.year, 3, 6, 2) <= day < _nth_weekday(day.year, 11, 6, 1)


def et_to_utc_ms(day, hour, minute=0):
    """A New York wall-clock time on `day` -> UTC epoch milliseconds."""
    d = pd.Timestamp(day).date()
    off = 4 if us_dst(d) else 5
    ts = pd.Timestamp(d.year, d.month, d.day, hour, minute, tz="UTC") + pd.Timedelta(hours=off)
    return int(ts.value // 10**6)


def federal_holidays(year):
    """US federal holidays (observed dates) of a year -> set of dates."""
    def observed(d):
        return d - dt.timedelta(days=1) if d.weekday() == 5 else d + dt.timedelta(days=1) if d.weekday() == 6 else d
    h = {observed(dt.date(year, 1, 1)), _nth_weekday(year, 1, 0, 3), _nth_weekday(year, 2, 0, 3),
         _nth_weekday(year, 5, 0, -1), observed(dt.date(year, 7, 4)), _nth_weekday(year, 9, 0, 1),
         _nth_weekday(year, 10, 0, 2), observed(dt.date(year, 11, 11)), _nth_weekday(year, 11, 3, 4),
         observed(dt.date(year, 12, 25))}
    if year >= 2021:
        h.add(observed(dt.date(year, 6, 19)))
    nxt = observed(dt.date(year + 1, 1, 1))                         # New Year's Day observed on 31 Dec
    if nxt.year == year:
        h.add(nxt)
    return h


def business_days(year, month):
    hol = federal_holidays(year)
    n = calendar.monthrange(year, month)[1]
    return [dt.date(year, month, d) for d in range(1, n + 1)
            if dt.date(year, month, d).weekday() < 5 and dt.date(year, month, d) not in hol]


def ism_dates(start=START, end=None):
    """ISM Manufacturing PMI release days (derived rule): first business day; January: second."""
    lo, hi = pd.Timestamp(start).date(), pd.Timestamp(end or pd.Timestamp.now(tz="UTC").tz_localize(None)).date()
    out = []
    for y in range(lo.year, hi.year + 1):
        for m in range(1, 13):
            b = business_days(y, m)
            d = b[1] if m == 1 else b[0]
            if lo <= d <= hi:
                out.append(d)
    return out


def _irregular(day, kind=None):
    s = str(day)[:10]
    return any(a <= s <= b and (kind is None or kind in kinds) for a, b, kinds in IRREGULAR)


# ---------------------------------------------------------------- fetching (network)
_last = {"t": 0.0}


def _get(url, browser=True):
    import requests
    wait = PAUSE_S - (time.time() - _last["t"])
    if wait > 0:
        time.sleep(wait)
    try:
        # FRED / ALFRED drop connections that carry a browser User-Agent from a script (see
        # sources/xmarket.py), so those go with requests' own default agent; no e-mail anywhere.
        r = requests.get(url, headers=UA if browser else None, timeout=TIMEOUT_S)
    finally:
        _last["t"] = time.time()
    if r.status_code != 200:
        raise RuntimeError("HTTP %d from %s" % (r.status_code, url))
    return r


def parse_alfred(text):
    """ALFRED's release-dates text file -> sorted list of 'YYYY-MM-DD' (the vintage dates)."""
    return sorted(set(s.strip() for s in text.splitlines() if re.fullmatch(r"\d{4}-\d\d-\d\d", s.strip())))


def fetch_alfred(rid):
    return parse_alfred(_get(ALFRED_URL % rid, browser=False).text)


def parse_census_xlsx(content):
    """Census MARTSreleasedates.xlsx (rows = year, columns = release month, cells = day(s))
    -> sorted list of 'YYYY-MM-DD'. Read with zipfile, no Excel library needed."""
    z = zipfile.ZipFile(io.BytesIO(content))
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        ss = [re.sub(r"<[^>]+>", "", s) for s in re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode("utf-8"), re.S)]
    sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
    cols = "BCDEFGHIJKLM"
    out = []
    for row in re.findall(r"<row[^>]*>(.*?)</row>", sheet, re.S):
        cells = {}
        for ref, attr, inner in re.findall(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(.*?)</c>)', row, re.S):
            v = re.search(r"<v>(.*?)</v>", inner or "")
            v = v.group(1) if v else ""
            if 't="s"' in attr and v:
                v = ss[int(v)]
            cells[ref] = v.strip()
        y = cells.get("A", "")
        if not re.fullmatch(r"\d{4}(\.0)?", y):
            continue
        y = int(float(y))
        for k, col in enumerate(cols):
            for day in re.findall(r"\d+", cells.get(col, "").replace("N/A", "")):
                try:
                    out.append(str(dt.date(y, k + 1, int(day))))
                except ValueError:
                    pass
    return sorted(set(out))


def fetch_census_retail():
    return parse_census_xlsx(_get(CENSUS_RETAIL_XLSX).content)


def parse_fomc_calendar(html):
    """fomccalendars.htm -> list of decision dates (last meeting day), notation votes and
    cancelled meetings left out."""
    out = []
    for blk in re.split(r'<h4><a id="\d+">', html)[1:]:
        m = re.match(r"(\d{4}) FOMC Meetings", blk)
        if not m:
            continue
        y = int(m.group(1))
        for mon, days in re.findall(r'fomc-meeting__month[^>]*><strong>([^<]+)</strong>.*?fomc-meeting__date[^>]*>([^<]+)<', blk, re.S):
            if re.search(r"notation|cancel", days, re.I):
                continue
            mon_last = mon.split("/")[-1].strip().lower()
            mi = [v for k, v in MONTHS.items() if k.startswith(mon_last[:3])]
            nums = re.findall(r"\d+", days)
            if not mi or not nums:
                continue
            out.append(dt.date(y, mi[0], int(nums[-1])))
    return sorted(set(out))


def parse_fomc_historical(html):
    """fomchistoricalYYYY.htm -> decision dates of the scheduled meetings (the headings
    'January 29-30 Meeting - 2019', 'April/May 30-1 Meeting - 2019'); unscheduled meetings,
    notation votes and cancelled meetings are left out (the emergency cuts are added by hand)."""
    out = []
    for head in re.findall(r"<h5[^>]*>([^<]+)</h5>", html):
        m = re.match(r"\s*([A-Za-z/]+) ([\d\-]+) Meeting - (\d{4})", head)
        if not m:
            continue
        mon_last = m.group(1).split("/")[-1].lower()
        mi = [v for k, v in MONTHS.items() if k.startswith(mon_last[:3])]
        out.append(dt.date(int(m.group(3)), mi[0], int(re.findall(r"\d+", m.group(2))[-1])))
    return sorted(set(out))


def fetch_fomc():
    days = parse_fomc_calendar(_get(FED_CAL).text)
    for y in (2019, 2020):
        days += parse_fomc_historical(_get(FED_HIST % y).text)
    return sorted(set(days))


def parse_eia_archive(html):
    return sorted(set("%s-%s-%s" % t for t in re.findall(r"archive/\d{4}/(\d{4})_(\d\d)_(\d\d)/", html)))


def fetch_eia():
    return parse_eia_archive(_get(EIA_ARCHIVE).text)


# ---------------------------------------------------------------- choosing the release days
def keep_main(kind, dates):
    """Drop the revision-only vintages from an ALFRED date list (see the module text)."""
    dates = sorted(dates)
    if kind in ("CPI", "PPI"):                                      # February seasonal-factor days
        drop = set()
        for a, b in zip(dates, dates[1:]):
            if a[5:7] == "02" and b[5:7] == "02" and a[:4] == b[:4] and (pd.Timestamp(b) - pd.Timestamp(a)).days <= 7:
                drop.add(a)
        return [d for d in dates if d not in drop]
    if kind == "NFP":                                               # one Employment Situation a month: the first
        seen, out = set(), []
        for d in dates:
            if d[:7] not in seen:
                seen.add(d[:7])
                out.append(d)
        return out
    if kind == "GDP":                                               # the advance (initial) estimate per quarter
        out, prev = [], None                                        # >= 20 days after the quarter, >= 45 after the last advance
        for y in range(int(dates[0][:4]) - 1, int(dates[-1][:4]) + 1):
            for qm in (3, 6, 9, 12):
                qend = pd.Timestamp(y, qm, 1) + pd.offsets.MonthEnd(0)
                first = [d for d in dates if pd.Timestamp(d) >= qend + pd.Timedelta(days=20)
                         and (prev is None or pd.Timestamp(d) >= prev + pd.Timedelta(days=45))]
                if first and pd.Timestamp(first[0]) < qend + pd.Timedelta(days=120):
                    out.append(first[0])
                    prev = pd.Timestamp(first[0])
        return sorted(set(out))
    if kind == "RETAIL_X":                                          # late-April / late-Sept annual revisions
        out = []
        for d in dates:
            same = [x for x in dates if x[:7] == d[:7] and x != d]
            if same and int(d[8:]) >= 20 and d[5:7] in ("04", "09") and not _irregular(d) and min(same) < d:
                continue
            out.append(d)
        return out
    return dates


def periods(kind, dates, lag=1):
    """Reference month of each release: release month - lag; when two releases land on the same
    month (a delayed one catching up), the earlier is moved back a month, repeatedly."""
    ref = []
    for d in dates:
        p = pd.Timestamp(d[:7] + "-01") - pd.DateOffset(months=lag)
        ref.append([p.year, p.month])
    for d_i in range(len(dates)):
        fix = PERIOD_FIX.get((kind, dates[d_i]))
        if fix:
            ref[d_i] = list(fix)
    for i in range(len(ref) - 1, 0, -1):
        while (ref[i - 1][0], ref[i - 1][1]) >= (ref[i][0], ref[i][1]):
            p = pd.Timestamp(ref[i][0], ref[i][1], 1) - pd.DateOffset(months=1)
            ref[i - 1] = [p.year, p.month]
    return [(y, m) for y, m in ref]


def _row(day, hour, minute, title, country, impact, kind, source):
    if _irregular(day, kind):
        source += ";irregular"
    return (et_to_utc_ms(day, hour, minute), title, country, impact, "", "", kind, source)


def build(start=START, end=None, fetched=None, log=print):
    """-> the history frame. `fetched` may hold pre-fetched date lists (tests); otherwise each
    source is fetched once, with a pause between requests. Only releases before `end` (default
    now) are kept: the live file owns the future."""
    end_ms = int(pd.Timestamp(end, tz="UTC").value // 10**6) if end else int(time.time() * 1000)
    lo = str(pd.Timestamp(start).date())
    f = dict(fetched or {})
    rows = []

    def got(key, fn):
        if key not in f:
            try:
                f[key] = fn()
                log("  %-10s %d dates" % (key, len(f[key])))
            except Exception as e:
                f[key] = None
                log("  %-10s FAILED: %s" % (key, str(e)[:100]))
        return f[key]

    for kind, (rid, title, hh, mm, impact) in ALFRED.items():
        if kind == "RETAIL_X":
            continue
        ds = got(kind, lambda rid=rid: fetch_alfred(rid))
        if not ds:
            continue
        ds = keep_main(kind, [d for d in ds if d >= str(pd.Timestamp(lo) - pd.Timedelta(days=400))[:10]])
        if kind in ("CPI", "NFP"):
            per = periods(kind, ds, 1)
            names = ["%s %s %d" % (kind, MON[m], y) for y, m in per]
        else:
            names = [title] * len(ds)
        src = "official:alfred rid=%d (%s dates), %02d:%02d ET standard time" % (rid, "BLS" if rid in (10, 46, 50, 192) else "BEA", hh, mm)
        for d, name in zip(ds, names):
            if d >= lo:
                rows.append(_row(d, hh, mm, name, "USD", impact, kind, src))

    retail = got("RETAIL", fetch_census_retail)
    if retail:
        for d in retail:
            if d >= lo:
                rows.append(_row(d, 8, 30, RETAIL_TITLE, "USD", "High", "RETAIL",
                                 "official:census MARTSreleasedates.xlsx, 08:30 ET"))
    else:                                                           # fall back on ALFRED's record
        ds = got("RETAIL_X", lambda: fetch_alfred(9))
        for d in keep_main("RETAIL_X", ds or []):
            if d >= lo:
                rows.append(_row(d, 8, 30, RETAIL_TITLE, "USD", "High", "RETAIL", "official:alfred rid=9 (Census dates), 08:30 ET"))

    fomc = got("FOMC", fetch_fomc)
    for d in fomc or []:
        if str(d) >= lo:
            rows.append(_row(d, 14, 0, "FOMC %s %d" % (MON[d.month], d.year), "USD", "High", "FOMC",
                             "official:federalreserve.gov meeting calendar, statement 14:00 ET"))
    for d, hh, mm in FOMC_EMERGENCY:
        if d >= lo:
            rows.append(_row(d, hh, mm, "FOMC Mar 2020 emergency cut", "USD", "High", "FOMC",
                             "official:federalreserve.gov unscheduled meeting, statement %02d:%02d ET" % (hh, mm)))

    for d in ism_dates(lo, end):
        rows.append(_row(d, 10, 0, ISM_TITLE, "USD", "High", "ISM",
                         "derived:rule first US business day (Jan: second), 10:00 ET"))

    eia = got("EIA", fetch_eia)
    for d in eia or []:
        if d >= lo:
            wed = pd.Timestamp(d).weekday() == 2
            rows.append(_row(d, 10 if wed else 11, 30 if wed else 0, EIA_TITLE, "OIL", "Medium", "EIA",
                             "official:eia.gov WPSR archive date; time rule %s" % ("Wed 10:30 ET" if wed else "holiday-shifted 11:00 ET")))
    for d, title in OPEC_MEETINGS:
        if d >= lo:
            ts = int(pd.Timestamp(d + " %02d:%02d" % OPEC_UTC, tz="UTC").value // 10**6)
            rows.append((ts, title, "OIL", "Medium", "", "", "OPEC", "derived:public record (date only; time nominal 13:00 UTC)"))

    d = pd.DataFrame(rows, columns=COLUMNS)
    d = d[d.ts_ms < end_ms]
    d = d.drop_duplicates(["ts_ms", "title"], keep="first").sort_values(["ts_ms", "title"]).reset_index(drop=True)
    d["ts_ms"] = d["ts_ms"].astype("int64")
    return d, f


def update(path=None, log=print, **kw):
    d, f = build(log=log, **kw)
    path = path or HISTORY_CSV
    if not len(d):
        return 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    d.to_csv(tmp, index=False)
    os.replace(tmp, path)
    _cache.clear()
    return len(d)


# ---------------------------------------------------------------- reading
_cache = {}


def load_history(path=None):
    """The whole history file (US and OIL rows); empty frame with COLUMNS when it is missing."""
    path = path or HISTORY_CSV
    if not os.path.exists(path):
        return pd.DataFrame(columns=COLUMNS)
    key = (path, os.path.getmtime(path))
    if key not in _cache:
        _cache.clear()
        d = pd.read_csv(path, dtype={"forecast": str, "previous": str, "title": str}).fillna("")
        d["ts_ms"] = d["ts_ms"].astype("int64")
        _cache[key] = d
    return _cache[key].copy()


def us_events(path=None):
    """US High-impact rows in the live file's six columns: what the release guard may see."""
    d = load_history(path)
    d = d[(d["country"] == "USD") & (d["impact"] == "High")]
    return d[LIVE_COLUMNS].reset_index(drop=True)


def oil_events(path=None):
    """The oil rows (EIA weekly crude report, OPEC / OPEC+ meetings). Never fed to the guard."""
    d = load_history(path)
    return d[d["country"] == "OIL"].reset_index(drop=True)


def merge(live, hist):
    """Union of the live calendar and the history, one row per (ts_ms, title); the live row wins."""
    live = live[LIVE_COLUMNS] if len(live) else pd.DataFrame(columns=LIVE_COLUMNS)
    if hist is None or not len(hist):
        return live.reset_index(drop=True)
    hist = hist[LIVE_COLUMNS]
    parts = [p for p in (live, hist) if len(p)]
    d = pd.concat(parts, ignore_index=True)
    d["ts_ms"] = d["ts_ms"].astype("int64")
    d = d.drop_duplicates(["ts_ms", "title"], keep="first")         # live rows come first
    return d.sort_values("ts_ms", kind="stable").reset_index(drop=True).fillna("")


# ---------------------------------------------------------------- checks
KNOWN = [  # (kind, New York date, ET hour, ET minute): dates checked by hand against the agencies' releases
    ("CPI", "2022-06-10", 8, 30), ("CPI", "2025-10-24", 8, 30), ("CPI", "2019-01-11", 8, 30),
    ("NFP", "2020-07-02", 8, 30), ("NFP", "2019-03-08", 8, 30), ("NFP", "2021-07-02", 8, 30),
    ("NFP", "2020-01-10", 8, 30), ("FOMC", "2020-03-15", 17, 0), ("FOMC", "2020-03-03", 10, 0),
    ("FOMC", "2022-06-15", 14, 0), ("FOMC", "2019-07-31", 14, 0), ("GDP", "2019-02-28", 8, 30),
    ("GDP", "2025-12-23", 8, 30), ("RETAIL", "2019-02-14", 8, 30), ("PPI", "2022-07-14", 8, 30),
]


def verify(hist=None, fetched=None, live=None, log=print):
    """Cross-checks. -> dict of findings (also printed)."""
    hist = load_history() if hist is None else hist
    out = {}
    have = set(zip(hist.kind, hist.ts_ms.astype("int64")))
    miss = [k for k in KNOWN if (k[0], et_to_utc_ms(k[1], k[2], k[3])) not in have]
    out["known_dates_missing"] = miss
    log("known dates: %d checked, %d missing %s" % (len(KNOWN), len(miss), miss))
    f = fetched or {}
    if f.get("RETAIL") and f.get("RETAIL_X"):
        lo = START
        a = set(d for d in f["RETAIL"] if d >= lo)
        b = set(d for d in keep_main("RETAIL_X", f["RETAIL_X"]) if d >= lo)
        hi = max(b)
        a = set(d for d in a if d <= hi)
        out["retail_census_not_alfred"] = sorted(a - b)
        out["retail_alfred_not_census"] = sorted(b - a)
        log("retail: Census %d vs ALFRED %d dates; Census-only %s; ALFRED-only %s"
            % (len(a), len(b), sorted(a - b), sorted(b - a)))
    if live is not None and len(live):
        lv = live.copy()
        lv["ts_ms"] = lv["ts_ms"].astype("int64")
        h = hist[hist.country == "USD"]
        lo, hi = int(h.ts_ms.min()), int(h.ts_ms.max())
        lv = lv[(lv.ts_ms >= lo) & (lv.ts_ms <= hi)]
        checked, bad = 0, []
        for ts, title in zip(lv.ts_ms, lv.title):
            k = str(title).split()[0].upper()
            if k in ("CPI", "NFP", "FOMC"):
                checked += 1
                if ts not in set(h[h.kind == k].ts_ms):
                    bad.append((str(pd.Timestamp(ts, unit="ms", tz="UTC"))[:16], title))
        out["live_overlap_checked"], out["live_overlap_mismatch"] = checked, bad
        log("live file overlap (CPI/NFP/FOMC): %d checked, mismatches %s" % (checked, bad))
    return out


def summary(hist=None):
    hist = load_history() if hist is None else hist
    g = hist.groupby("kind").agg(rows=("ts_ms", "size"), first=("ts_ms", "min"), last=("ts_ms", "max"),
                                 source=("source", lambda s: s.iloc[0].split(",")[0].split(";")[0]))
    g["first"] = [str(pd.Timestamp(x, unit="ms", tz="UTC"))[:16] for x in g["first"]]
    g["last"] = [str(pd.Timestamp(x, unit="ms", tz="UTC"))[:16] for x in g["last"]]
    return g


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else "summary"
    if cmd == "build":
        d, f = build()
        os.makedirs(os.path.dirname(HISTORY_CSV), exist_ok=True)
        d.to_csv(HISTORY_CSV + ".tmp", index=False)
        os.replace(HISTORY_CSV + ".tmp", HISTORY_CSV)
        _cache.clear()
        print("wrote %d rows -> %s" % (len(d), HISTORY_CSV))
        if "RETAIL_X" not in f:
            try:
                f["RETAIL_X"] = fetch_alfred(9)
            except Exception as e:
                print("ALFRED rid 9 cross-check failed:", e)
        from . import econ
        verify(d, f, econ._load_live() if hasattr(econ, "_load_live") else None)
        print(summary(d).to_string())
    elif cmd == "verify":
        from . import econ
        verify(live=econ._load_live() if hasattr(econ, "_load_live") else None)
    else:
        print(summary().to_string())


if __name__ == "__main__":
    main()
