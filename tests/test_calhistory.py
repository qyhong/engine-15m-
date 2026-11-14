# -*- coding: utf-8 -*-
"""engine15/calhistory.py and its join into econ.load_events(). No network.

    py -3 -m pytest tests/test_calhistory.py -q        (from the project folder)
"""
import datetime as dt
import io
import os
import sys
import zipfile

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import calhistory as ch  # noqa: E402
from engine15 import econ  # noqa: E402


def utc_ms(text):
    return int(pd.Timestamp(text, tz="UTC").value // 10**6)


# ---------------------------------------------------------------- clock
def test_dst_conversion_known_times():
    assert ch.et_to_utc_ms("2022-06-10", 8, 30) == utc_ms("2022-06-10 12:30")     # CPI, daylight time
    assert ch.et_to_utc_ms("2022-01-12", 8, 30) == utc_ms("2022-01-12 13:30")     # CPI, standard time
    assert ch.et_to_utc_ms("2020-03-06", 8, 30) == utc_ms("2020-03-06 13:30")     # the Friday before the switch
    assert ch.et_to_utc_ms("2020-03-08", 17, 0) == utc_ms("2020-03-08 21:00")     # switch day (2nd Sunday of March)
    assert ch.et_to_utc_ms("2020-10-30", 8, 30) == utc_ms("2020-10-30 12:30")
    assert ch.et_to_utc_ms("2020-11-01", 17, 0) == utc_ms("2020-11-01 22:00")     # back on standard time


def test_dst_matches_tz_database():
    zoneinfo = pytest.importorskip("zoneinfo")
    try:
        ny = zoneinfo.ZoneInfo("America/New_York")
    except Exception:
        pytest.skip("no tz database")
    day = dt.date(2019, 1, 1)
    while day <= dt.date(2026, 12, 31):
        want = dt.datetime(day.year, day.month, day.day, 8, 30, tzinfo=ny).astimezone(dt.timezone.utc)
        assert ch.et_to_utc_ms(day, 8, 30) == int(want.timestamp() * 1000), day
        day += dt.timedelta(days=3)


def test_holidays_and_ism_rule():
    assert dt.date(2021, 12, 31) in ch.federal_holidays(2021)                   # New Year 2022 observed on Fri 31 Dec
    assert dt.date(2021, 6, 18) in ch.federal_holidays(2021)                    # Juneteenth from 2021
    assert dt.date(2020, 6, 19) not in ch.federal_holidays(2020)
    ism = set(ch.ism_dates("2020-01-01", "2023-12-31"))
    assert dt.date(2021, 1, 5) in ism and dt.date(2021, 1, 4) not in ism         # January: second business day
    assert dt.date(2023, 1, 4) in ism                                            # 2 Jan 2023 a holiday
    assert dt.date(2020, 9, 1) in ism and dt.date(2022, 8, 1) in ism


# ---------------------------------------------------------------- choosing release days
def test_keep_main_drops_revision_vintages():
    cpi = ["2022-01-12", "2022-02-08", "2022-02-10", "2022-03-10"]
    assert ch.keep_main("CPI", cpi) == ["2022-01-12", "2022-02-10", "2022-03-10"]
    nfp = ["2024-01-05", "2024-01-10", "2024-08-02", "2024-08-21"]
    assert ch.keep_main("NFP", nfp) == ["2024-01-05", "2024-08-02"]
    gdp = ["2025-07-30", "2025-09-25", "2025-12-23", "2026-01-22", "2026-02-20", "2026-03-13", "2026-04-09", "2026-04-30", "2026-05-28"]
    assert ch.keep_main("GDP", gdp) == ["2025-07-30", "2025-12-23", "2026-02-20", "2026-04-30"]


def test_periods_cascade_and_fix():
    # Census after the 2018-19 shutdown: Dec, Jan, Feb, Mar data released 14 Feb, 11 Mar, 1 Apr, 18 Apr
    p = ch.periods("RETAIL", ["2019-02-14", "2019-03-11", "2019-04-01", "2019-04-18", "2019-05-15"])
    assert p == [(2018, 12), (2019, 1), (2019, 2), (2019, 3), (2019, 4)]
    p = ch.periods("NFP", ["2025-09-05", "2025-11-20", "2025-12-16", "2026-01-09"])
    assert p == [(2025, 8), (2025, 9), (2025, 11), (2025, 12)]


def test_parsers():
    txt = "Release: CPI\nName  1949-03-24  2026-11-10\n\n2022-06-10\n2022-07-13\n"
    assert ch.parse_alfred(txt) == ["2022-06-10", "2022-07-13"]
    cal = ('<h4><a id="1">2024 FOMC Meetings</a></h4>'
           '<div class="fomc-meeting__month x"><strong>Apr/May</strong></div><div class="fomc-meeting__date y">30-1</div>'
           '<div class="fomc-meeting__month x"><strong>August</strong></div><div class="fomc-meeting__date y">22 (notation vote)</div>'
           '<div class="fomc-meeting__month x"><strong>December</strong></div><div class="fomc-meeting__date y">17-18*</div>')
    assert ch.parse_fomc_calendar(cal) == [dt.date(2024, 5, 1), dt.date(2024, 12, 18)]
    hist = ('<h5 class="p">March 2 (unscheduled) Meeting - 2020</h5><h5 class="p">March 17-18 (cancelled) Meeting - 2020</h5>'
            '<h5 class="p">November 4-5 Meeting - 2020</h5>')
    assert ch.parse_fomc_historical(hist) == [dt.date(2020, 11, 5)]
    assert ch.parse_eia_archive('href="/petroleum/supply/weekly/archive/2020/2020_01_03/wpsr_2020_01_03.php"') == ["2020-01-03"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/sharedStrings.xml", "<sst><si><t>N/A</t></si><si><t>1**,18**</t></si></sst>")
        z.writestr("xl/worksheets/sheet1.xml",
                   '<worksheet><sheetData><row r="5"><c r="A5"><v>2019</v></c><c r="B5" t="s"><v>0</v></c>'
                   '<c r="C5"><v>14</v></c><c r="E5" t="s"><v>1</v></c></row></sheetData></worksheet>')
    assert ch.parse_census_xlsx(buf.getvalue()) == ["2019-02-14", "2019-04-01", "2019-04-18"]


# ---------------------------------------------------------------- build on planted dates
def planted():
    return {"CPI": ["2021-12-10", "2022-01-12", "2022-02-08", "2022-02-10", "2022-06-10"],
            "PPI": ["2022-01-13"], "NFP": ["2022-01-07", "2022-01-12"], "PCE": ["2022-01-28"],
            "GDP": ["2021-10-28", "2021-12-22", "2022-01-27", "2022-02-24"], "JOLTS": ["2022-01-04"],
            "RETAIL": ["2022-01-14"], "FOMC": [dt.date(2022, 1, 26), dt.date(2022, 3, 16)],
            "EIA": ["2022-01-05", "2022-01-20"]}


def test_build_planted(tmp_path):
    d, _ = ch.build(start="2022-01-01", end="2022-03-01", fetched=planted(), log=lambda *a: None)
    assert list(d.columns) == ch.COLUMNS
    cpi = d[d.kind == "CPI"]
    assert list(cpi.title) == ["CPI Dec 2021", "CPI Jan 2022"] and utc_ms("2022-02-10 13:30") in set(cpi.ts_ms)
    assert utc_ms("2022-02-08 13:30") not in set(d.ts_ms)                        # seasonal-factor day dropped
    assert list(d[d.kind == "NFP"].ts_ms) == [utc_ms("2022-01-07 13:30")]
    assert list(d[d.kind == "GDP"].ts_ms) == [utc_ms("2022-01-27 13:30")]
    assert list(d[d.kind == "FOMC"].title) == ["FOMC Jan 2022"]                  # March is after `end`
    assert utc_ms("2022-01-26 19:00") in set(d[d.kind == "FOMC"].ts_ms)
    eia = d[d.kind == "EIA"]
    assert set(eia.country) == {"OIL"} and set(eia.impact) == {"Medium"}
    assert list(eia.ts_ms) == [utc_ms("2022-01-05 15:30"), utc_ms("2022-01-20 16:00")]  # Wed 10:30 / holiday Thu 11:00
    assert (d.ts_ms < utc_ms("2022-03-01")).all()
    assert set(d[d.kind == "ISM"].ts_ms) == {utc_ms("2022-01-04 15:00"), utc_ms("2022-02-01 15:00")}
    path = str(tmp_path / "hist.csv")
    d.to_csv(path, index=False)
    us = ch.us_events(path)
    assert list(us.columns) == ch.LIVE_COLUMNS
    assert set(us.country) == {"USD"} and "JOLTS Job Openings" not in set(us.title)
    assert set(ch.oil_events(path).kind) == {"EIA", "OPEC"}                    # OPEC+ met 4 Jan and 2 Feb 2022


# ---------------------------------------------------------------- the join into econ
def live_frame():
    return pd.DataFrame({"ts_ms": [utc_ms("2026-05-12 12:30"), utc_ms("2026-06-05 12:30")],
                         "title": ["CPI Apr 2026", "NFP May 2026"], "country": ["USD", "USD"],
                         "impact": ["High", "High"], "forecast": ["0.3%", ""], "previous": ["0.2%", ""]})


def hist_frame():
    rows = [(utc_ms("2026-05-12 12:30"), "CPI Apr 2026", "USD", "High", "", "", "CPI", "x"),
            (utc_ms("2022-06-10 12:30"), "CPI May 2022", "USD", "High", "", "", "CPI", "x"),
            (utc_ms("2022-06-15 15:30"), ch.EIA_TITLE, "OIL", "Medium", "", "", "EIA", "x")]
    return pd.DataFrame(rows, columns=ch.COLUMNS)


def test_merge_dedups_live_wins():
    m = ch.merge(live_frame(), hist_frame()[ch.LIVE_COLUMNS])
    assert len(m) == 4 and m.ts_ms.is_monotonic_increasing
    apr = m[m.title == "CPI Apr 2026"]
    assert len(apr) == 1 and apr.forecast.iloc[0] == "0.3%"                     # the live row won
    assert len(ch.merge(live_frame(), None)) == 2


def test_load_events_with_and_without_history(tmp_path, monkeypatch):
    live_path, hist_path = str(tmp_path / "econ_events.csv"), str(tmp_path / "calendar_history.csv")
    live_frame().to_csv(live_path, index=False)
    monkeypatch.setattr(econ, "EVENTS_CSV", live_path)
    monkeypatch.setattr(ch, "HISTORY_CSV", hist_path)                           # missing file
    ev = econ.load_events()
    assert len(ev) == 2 and list(ev.columns) == ch.LIVE_COLUMNS
    hist_frame().to_csv(hist_path, index=False)
    ev = econ.load_events()
    assert len(ev) == 3 and set(ev.country) == {"USD"}                          # the oil row stays out of the guard
    assert ev[ev.title == "CPI Apr 2026"].forecast.iloc[0] == "0.3%"
    assert len(econ._load_live()) == 2                                           # update_calendar's base stays live-only
    nxt = econ.next_event(pd.Timestamp("2022-06-10 00:00", tz="UTC"))
    assert nxt["time_utc"] == "2022-06-10 12:30" and nxt["titles"] == ["CPI May 2022"]
    monkeypatch.setattr(econ, "EVENTS_CSV", str(tmp_path / "none.csv"))
    ev = econ.load_events()
    assert len(ev) == 2 and list(ev.title) == ["CPI May 2022", "CPI Apr 2026"]
    os.remove(hist_path)
    assert len(econ.load_events()) == 0


# ---------------------------------------------------------------- the file on disk
needs_file = pytest.mark.skipif(not os.path.exists(ch.HISTORY_CSV), reason="no calendar_history.csv")


@needs_file
def test_history_file_known_dates():
    h = ch.load_history()
    have = set(zip(h.kind, h.ts_ms))
    assert ("CPI", utc_ms("2022-06-10 12:30")) in have
    assert ("FOMC", utc_ms("2020-03-15 21:00")) in have                         # Sunday emergency cut, 17:00 EDT
    assert ("FOMC", utc_ms("2020-03-03 15:00")) in have                         # 10:00 EST
    assert ("NFP", utc_ms("2020-07-02 12:30")) in have                          # Thursday: 3 July holiday
    assert ("NFP", utc_ms("2019-03-08 13:30")) in have                          # not the first Friday
    assert ("NFP", utc_ms("2019-03-01 13:30")) not in have
    assert ("NFP", utc_ms("2020-01-10 13:30")) in have
    assert ("RETAIL", utc_ms("2019-02-14 13:30")) in have                       # 2018-19 shutdown delay
    assert ("CPI", utc_ms("2025-10-24 12:30")) in have                          # 2025 shutdown delay
    ny = pd.to_datetime(h.ts_ms, unit="ms", utc=True).dt.tz_convert("America/New_York").dt.strftime("%H:%M")
    assert set(ny[h.kind.isin(["CPI", "PPI", "NFP", "RETAIL", "GDP", "PCE"])]) == {"08:30"}
    assert set(ny[h.kind == "ISM"]) == {"10:00"}
    us = econ.load_events()
    assert set(us.country) == {"USD"} and not us.duplicated(["ts_ms", "title"]).any()
    assert set(ch.oil_events().kind) == {"EIA", "OPEC"}
