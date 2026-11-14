# -*- coding: utf-8 -*-
"""engine15/sources/equity_events.py (put/call and megacap earnings) on planted files. No network.

    py -3 -m pytest tests/test_equity_events.py -q        (from the project folder)
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15.sources import _util as U  # noqa: E402
from engine15.sources import equity_events as E  # noqa: E402

CBOE_TEXT = ("Disclaimer line\n, PRODUCT: TOTAL,,EXCHANGE: Cboe,\nDATE,CALLS,PUTS,TOTAL,P/C Ratio\n"
             "11/1/2006,1401036,1271445,2672481,0.91\n11/2/2006,1348240,1218592,2566832,0.9\n")
OCC_TEXT = ("quantity,underlying,symbol,actype,porc,exchange,actdate\n"
            "100,SPY,SPY,C,C,CBOE,11/09/2026\n100,SPY,SPY,M,C,CBOE,11/09/2026\n"
            "60,SPY,SPY,C,P,CBOE,11/09/2026\n60,SPY,SPY,M,P,CBOE,11/09/2026\n"
            "40,SPX,SPXW,C,P,CBOE,11/09/2026\n40,SPX,SPXW,F,P,CBOE,11/09/2026\n"
            "20,VIX,VIX,C,C,CBOE,11/09/2026\n20,VIX,VIX,M,C,CBOE,11/09/2026\n")
CUTS = ("2024-01-12 12:00", "2024-02-14 21:05", "2024-02-21 21:10", "2024-03-25 16:00")


def ms(text):
    return int(U.to_ms_vec([text])[0])


def plant_pc(folder, start="2023-01-02", end="2024-03-29", seed=2):
    rng = np.random.RandomState(seed)
    days = [d for d in E.trading_days() if start <= d <= end]
    n = len(days)
    calls = rng.uniform(3e7, 5e7, n)
    d = pd.DataFrame({"date": days, "source": "occ", "calls_total": calls, "puts_total": calls * rng.uniform(0.6, 1.1, n),
                      "calls_index": calls * 0.05, "puts_index": calls * 0.05 * rng.uniform(1.0, 1.6, n),
                      "calls_equity": calls * 0.95, "puts_equity": calls * 0.95 * rng.uniform(0.5, 1.0, n),
                      "calls_spx": calls * 0.04, "puts_spx": calls * 0.05, "first_seen_ms": np.nan, "known_ms": np.nan})
    U.write_csv(d, E.pc_path(folder))
    return d


def plant_earnings(folder):
    late = float(ms("2024-06-01"))                                      # filled in from history, long after
    rows = [("2024-01-12", "JPM", "bmo", late, late, np.nan),
            ("2024-01-25", "AAPL", "", float(ms("2024-01-02")), float(ms("2024-01-19")), float(ms("2024-01-20"))),
            ("2024-02-01", "AAPL", "amc", float(ms("2024-01-20")), float(ms("2024-02-01")), np.nan),
            ("2024-01-30", "MSFT", "amc", float(ms("2024-01-05")), float(ms("2024-01-30")), np.nan),
            ("2024-02-21", "NVDA", "amc", late, late, np.nan)]
    U.write_csv(pd.DataFrame(rows, columns=E.ERN_COLS), E.ern_path(folder))
    days = pd.date_range("2023-12-20", "2024-04-15", freq="D")
    days = days[days.dayofweek != 6].strftime("%Y-%m-%d")
    U.write_csv(pd.DataFrame({"date": days, "checked_ms": 0.0, "n_rows": 100.0, "n_megacap": 0.0}), E.days_path(folder))


def idx15(start="2023-12-01", end="2024-04-01"):
    return pd.date_range(start, end, freq="15min", tz="UTC")


def row_at(f, close_text):
    return f.loc[pd.Timestamp(close_text, tz="UTC") - pd.Timedelta(minutes=15)]


def same(a, b):
    return list(a.columns) == list(b.columns) and np.array_equal(a.values, b.values, equal_nan=True)


def test_parsers():
    c = E.parse_cboe(CBOE_TEXT)
    assert c["date"].tolist() == ["2006-11-01", "2006-11-02"] and c["puts"].iloc[0] == 1271445
    o = E.parse_occ(OCC_TEXT)
    assert o["calls_total"] == 120 and o["puts_total"] == 100                 # each trade is on two lines
    assert o["calls_index"] == 20 and o["puts_index"] == 40 and o["puts_spx"] == 40
    assert o["calls_equity"] == 100 and o["puts_equity"] == 60
    with pytest.raises(ValueError):
        E.parse_occ("Report date cannot be greater than 11/09/2026")
    n, got = E.parse_nasdaq({"data": {"rows": [{"symbol": "NVDA", "time": "time-after-hours"},
                                               {"symbol": "BRK.B", "time": "time-not-supplied"},
                                               {"symbol": "XYZ", "time": "time-pre-market"}]}})
    assert n == 3 and got == [("NVDA", "amc"), ("BRK.B", "")]


def test_putcall_known_next_trading_day_noon(tmp_path):
    plant_pc(str(tmp_path))
    f = E.features(idx15("2024-03-20", "2024-03-30"), "SPX", src_dir=str(tmp_path))
    # Friday 22 Mar's figures: from Monday 25 Mar 12:00 New York (16:00 UTC, daylight time)
    assert row_at(f, "2024-03-25 15:45")["pc_day_age_d"] > 3.5
    assert row_at(f, "2024-03-25 16:00")["pc_day_age_d"] == pytest.approx(68 / 24.0)      # since Friday's 16:00 ET close
    d = E.load_pc(str(tmp_path)).set_index("date").loc["2024-03-22"]
    assert row_at(f, "2024-03-25 16:00")["pc_total_ratio"] == pytest.approx(d["puts_total"] / d["calls_total"])


def test_no_lookahead_truncation(tmp_path):
    full_dir = str(tmp_path / "full")
    pc = plant_pc(full_dir)
    plant_earnings(full_dir)
    idx = idx15()
    full = E.features(idx, "SPX", src_dir=full_dir)
    assert full["pc_total_ratio"].notna().sum() > 1000 and full["ern_n_next5"].notna().sum() > 1000
    known_pc = E.pc_table(full_dir)["known_at"].values
    ev = E.events(full_dir)
    for cut in CUTS:
        t = pd.Timestamp(cut, tz="UTC")
        t_ms = int(t.value // 1000000)
        part_dir = str(tmp_path / ("cut%d" % t_ms))
        U.write_csv(pc[known_pc <= t_ms], E.pc_path(part_dir))
        keep = ev[ev["known_ms"] <= t_ms].copy()                            # what the calendar had shown by T
        keep.loc[keep["gone_ms"] > t_ms, "gone_ms"] = np.nan                 # not yet seen gone
        U.write_csv(keep[E.ERN_COLS], E.ern_path(part_dir))
        U.write_csv(pd.read_csv(E.days_path(full_dir)), E.days_path(part_dir))
        sub = idx[idx + pd.Timedelta(minutes=15) <= t]
        part = E.features(sub, "SPX", src_dir=part_dir)
        assert same(part, full.loc[sub]), cut


def test_earnings_rules(tmp_path):
    plant_earnings(str(tmp_path))
    f = E.features(idx15(), "SPX", src_dir=str(tmp_path))
    nvda = ms("2024-02-21 21:05")                                         # 16:05 New York, winter time
    # filled in from history: known only 7 days ahead
    assert row_at(f, "2024-02-14 21:00")["ern_days_next"] != row_at(f, "2024-02-14 21:00")["ern_days_next"]
    assert row_at(f, "2024-02-14 21:15")["ern_days_next"] == pytest.approx(7.0 - 10 / 1440.0)
    # seen live on 5 Jan: MSFT 30 Jan is in the 5-day count on Mon 29 Jan with AAPL 1 Feb (moved from 25 Jan)
    r = row_at(f, "2024-01-29 15:00")
    assert r["ern_n_next5"] == 2
    # the 25 Jan AAPL date counted until it was seen gone on 20 Jan
    assert row_at(f, "2024-01-22 15:00")["ern_n_next5"] == 0                # 22 Jan: 5 trading days end 29 Jan
    assert row_at(f, "2024-01-19 15:00")["ern_n_next5"] == 1                # 19 Jan: AAPL 25 Jan still listed
    # just after NVDA: reported in the last 24 hours
    after = row_at(f, "2024-02-22 15:00")
    assert after["ern_n_last24"] == 1 and after["ern_hours_since"] == pytest.approx((ms("2024-02-22 15:00") - nvda) / 3.6e6)
    assert 0 < after["ern_last"] < 1
    assert row_at(f, "2024-02-23 15:00")["ern_n_last24"] == 0
    # JPM before the open: 07:00 New York = 12:00 UTC
    assert row_at(f, "2024-01-12 12:00")["ern_n_last24"] == 1 and row_at(f, "2024-01-12 11:45")["ern_n_last24"] == 0


def test_bounded_never_nan_and_other_assets(tmp_path):
    plant_pc(str(tmp_path))
    plant_earnings(str(tmp_path))
    f = E.features(idx15(), "SPX", src_dir=str(tmp_path))
    assert not f[E.FEATURES].isna().any().any()
    assert (f[E.FEATURES].abs() <= 1.0).all().all()
    g = E.features(idx15()[:500], "XAUUSD", src_dir=str(tmp_path))
    assert (g[E.FEATURES] == 0).all().all() and g[E.RAW].isna().all().all()
    h = E.features(idx15("2025-01-01", "2025-01-05"), "SPX", src_dir=str(tmp_path))     # outside every file
    assert (h[E.FEATURES] == 0).all().all() and h[E.RAW].isna().all().all()


def test_update_is_bounded_polite_and_never_raises(tmp_path, monkeypatch):
    folder = str(tmp_path)
    calls = []

    class R:
        def __init__(self, text=None, js=None):
            self.text, self._js = text, js

        def json(self):
            return self._js

    def fake_get(url, params=None, pause=1.0, timeout=30):
        calls.append(url)
        if "cboe" in url:
            return R(text=CBOE_TEXT)
        if "theocc" in url:
            return R(text=OCC_TEXT)
        if params and params.get("date") == "2026-11-19":
            return R(js={"data": {"rows": [{"symbol": "NVDA", "time": "time-after-hours"}]}, "status": {"rCode": 200}})
        return R(js={"data": {"rows": []}, "status": {"rCode": 200}})

    now = [ms("2026-11-16 15:00")]
    monkeypatch.setattr(U, "get", fake_get)
    monkeypatch.setattr(U, "now_ms", lambda: now[0])
    out = E.update(log=None, src_dir=folder)
    assert not any(str(v).startswith("failed") for v in out.values()), out
    n_occ = sum("theocc" in c for c in calls)
    n_ern = sum("nasdaq" in c for c in calls)
    assert n_occ == 1 + E.OCC_BACKFILL_PER_CALL and n_ern == E.ERN_PER_CALL + E.ERN_BACKFILL_PER_CALL
    pc = E.load_pc(folder)
    assert (pc["source"] == "cboe").sum() == 2 and (pc["source"] == "occ").sum() == 2
    for _ in range(10):                                                   # the window fills over a few calls
        E.update(log=None, src_dir=folder)
    e = E.load_ern(folder)
    assert e["symbol"].tolist() == ["NVDA"] and e["first_seen_ms"].iloc[0] == now[0]
    assert sum("cboe" in c for c in calls) == 3                           # Cboe's frozen history: fetched once
    calls.clear()
    E.update(log=None, src_dir=folder)                                    # window fresh, OCC asked within the hour
    assert sum("nasdaq" in c for c in calls) <= E.ERN_BACKFILL_PER_CALL and sum("theocc" in c for c in calls) <= 1

    def broken(*a, **k):
        raise RuntimeError("down")
    monkeypatch.setattr(U, "get", broken)
    now[0] += 7 * U.H_MS
    before = (len(E.load_pc(folder)), len(E.load_ern(folder)))
    out = E.update(log=None, src_dir=folder)
    assert any(str(v).startswith("failed") for v in out.values())
    assert (len(E.load_pc(folder)), len(E.load_ern(folder))) == before


def test_describe_and_facts(tmp_path, monkeypatch):
    monkeypatch.setattr(E, "SRC_DIR", str(tmp_path))                     # describe / facts name companies from the file
    plant_pc(str(tmp_path))
    plant_earnings(str(tmp_path))
    f = E.features(idx15(), "SPX", src_dir=str(tmp_path))
    r = row_at(f, "2024-01-29 15:00")
    say = E.describe(r, "SPX")
    assert "put/call" in say["Options mood (put/call)"] and "MSFT" in say["Megacap earnings"]
    facts = E.facts(r, "SPX")
    rows = dict(facts["Megacap earnings"])
    assert "MSFT" in rows["This week"] and "AAPL" in rows["This week"]
