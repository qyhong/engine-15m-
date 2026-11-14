# -*- coding: utf-8 -*-
"""engine15/sources/oil.py on planted files. No network.

    py -3 -m pytest tests/test_oil.py -q        (from the project folder)
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import calhistory  # noqa: E402
from engine15.sources import _util as U  # noqa: E402
from engine15.sources import oil  # noqa: E402

UTC = "UTC"
SHIFTED_WEEK = "2024-02-02"                         # its release planted on Thursday 11:00 ET instead of Wednesday
DELAYED_WEEK = "2023-11-03"                         # no release planted: the EIA published it with the next week
CUTS = ("2024-02-08 15:45", "2024-02-08 16:00", "2024-03-08 20:15", "2024-03-08 20:30", "2024-03-13 14:30",
        "2024-04-02 03:00", "2024-05-17 21:15", "2024-06-20 16:45")


def ny(ms):
    return pd.Timestamp(int(ms), unit="ms", tz=UTC).tz_convert(U.NY)


def plant_calendar(folder):
    rows = []
    for fri in pd.date_range("2018-06-01", "2026-10-30", freq="W-FRI"):
        d = fri.strftime("%Y-%m-%d")
        if d == DELAYED_WEEK:                                          # no release that week: published with the next
            continue
        ts = U.ny_ms(fri + pd.Timedelta(days=6), 11, 0) if d == SHIFTED_WEEK else oil.eia_rule_ms(d)
        rows.append((ts, calhistory.EIA_TITLE, "OIL", "Medium", "", "", "EIA", "test"))
    for day, title in (("2023-06-04", "OPEC+ Ministerial Meeting"), ("2023-11-30", "OPEC+ Ministerial Meeting"),
                       ("2024-06-02", "OPEC+ Ministerial Meeting")):
        rows.append((int(pd.Timestamp(day + " 13:00", tz=UTC).value // 1000000), title, "OIL", "Medium", "", "", "OPEC", "test"))
    d = pd.DataFrame(rows, columns=calhistory.COLUMNS)
    os.makedirs(folder, exist_ok=True)
    d.to_csv(os.path.join(folder, "calendar_history.csv"), index=False)


def plant(folder, seed=5):
    rng = np.random.RandomState(seed)
    plant_calendar(folder)
    weeks = pd.date_range("2012-01-06", "2024-06-28", freq="W-FRI")
    n = len(weeks)
    season = 8000 * np.sin(2 * np.pi * weeks.dayofyear.values / 365.25)
    eia = pd.DataFrame({"date": weeks.strftime("%Y-%m-%d"), "crude": 420000 + season + np.cumsum(rng.normal(0, 3000, n)),
                        "cushing": 40000 + np.cumsum(rng.normal(0, 800, n)) * 0.3,
                        "gasoline": 230000 + np.cumsum(rng.normal(0, 2000, n)) * 0.3,
                        "distillate": 130000 + np.cumsum(rng.normal(0, 2000, n)) * 0.3,
                        "first_seen_ms": np.nan, "known_ms": np.nan})
    U.write_csv(eia, oil.path("eia_weekly", folder))
    tues = pd.date_range("2015-01-06", "2024-06-25", freq="W-TUE")
    m = len(tues)
    for name, oi in (("cot_wti", 1.8e6), ("cot_brent", 2.4e6)):
        net = 150000 * np.sin(np.arange(m) / 15.0) + rng.normal(0, 15000, m)
        U.write_csv(pd.DataFrame({"date": tues.strftime("%Y-%m-%d"), "oi": oi + rng.normal(0, 5e4, m),
                                  "long": 300000 + net / 2, "short": 300000 - net / 2, "first_seen_ms": np.nan,
                                  "known_ms": np.nan}), oil.path(name, folder))
    days = pd.bdate_range("2018-01-02", "2024-06-28")
    U.write_csv(pd.DataFrame({"date": days.strftime("%Y-%m-%d"),
                              "close": 35 * np.exp(np.cumsum(rng.normal(0, 0.03, len(days))))}), oil.path("y_ovx", folder))
    ed = days[days <= "2024-04-05"]
    c1 = 70 + np.cumsum(rng.normal(0, 1, len(ed)))
    U.write_csv(pd.DataFrame({"date": ed.strftime("%Y-%m-%d"), "c1": c1, "c2": c1 - rng.normal(0.3, 0.5, len(ed))}),
                oil.path("curve_eia_wti", folder))
    for asset, root in (("WTI", "CL"), ("BRENT", "BZ")):
        yd = days[days >= "2024-04-20"]
        p = 80 + np.cumsum(rng.normal(0, 1, len(yd)))
        syms = [oil.front_two(root, x) for x in yd.strftime("%Y-%m-%d")]
        U.write_csv(pd.DataFrame({"date": yd.strftime("%Y-%m-%d"), "m1_sym": [oil.yahoo_symbol(root, s[0]) for s in syms],
                                  "m1": p, "m2_sym": [oil.yahoo_symbol(root, s[1]) for s in syms], "m2": p - 0.5}),
                    oil.path("curve_" + asset.lower(), folder))


def bars(start="2023-06-01", end="2024-06-30", seed=7):
    rng = np.random.RandomState(seed)
    idx = pd.date_range(start, end, freq="15min", tz=UTC)
    idx = idx[idx.dayofweek < 5]
    w = 75 * np.exp(np.cumsum(rng.normal(0, 0.002, len(idx))))
    b = w + 4 + np.cumsum(rng.normal(0, 0.01, len(idx)))
    fw = pd.DataFrame({"close": w}, index=idx)
    fb = pd.DataFrame({"close": b}, index=idx).iloc[::1]
    fb = fb[(fb.index.hour != 23)]                                     # Brent opens later: not every WTI bar has one
    return {"WTI": fw, "BRENT": fb}


def same(a, b):
    return list(a.columns) == list(b.columns) and np.array_equal(a.values, b.values, equal_nan=True)


def cut_files(full, part, t_ms):
    """Copy the planted files keeping only what was public at t_ms, by the module's own publication rules."""
    os.makedirs(part, exist_ok=True)
    plant_calendar(part)                                               # a release SCHEDULE is public in advance
    e = oil.eia_table(full)
    raw = pd.read_csv(oil.path("eia_weekly", full), dtype={"date": str}, float_precision="round_trip")
    keep = set(e.loc[e["known_at"] <= t_ms, "date"])
    U.write_csv(raw[raw["date"].isin(keep)], oil.path("eia_weekly", part))
    for name, mk in (("cot_wti", "wti"), ("cot_brent", "brent")):
        t = oil.cot_table(mk, full)
        raw = pd.read_csv(oil.path(name, full), dtype={"date": str}, float_precision="round_trip")
        U.write_csv(raw[raw["date"].isin(set(t.loc[t["known_at"] <= t_ms, "date"]))], oil.path(name, part))
    y = pd.read_csv(oil.path("y_ovx", full), dtype={"date": str}, float_precision="round_trip")
    U.write_csv(y[U.ny_ms_vec(y["date"].values, 16, 30) <= t_ms], oil.path("y_ovx", part))
    c = pd.read_csv(oil.path("curve_eia_wti", full), dtype={"date": str}, float_precision="round_trip")
    U.write_csv(c[oil.eia_curve_known_ms(c["date"].values) <= t_ms], oil.path("curve_eia_wti", part))
    for a in ("wti", "brent"):
        c = pd.read_csv(oil.path("curve_" + a, full), dtype={"date": str}, float_precision="round_trip")
        U.write_csv(c[U.ny_ms_vec(c["date"].values, 17, 15) <= t_ms], oil.path("curve_" + a, part))


# ------------------------------------------------------------------ the one rule
def test_no_lookahead_truncation(tmp_path):
    """Cut everything at T (files to what was public, bars to closed ones): every row up to T is unchanged."""
    full_dir = str(tmp_path / "full")
    plant(full_dir)
    bs = bars()
    for asset in oil.OIL:
        idx = bs[asset].index
        full = oil.features(idx, asset, bars=bs, src_dir=full_dir, strict=True)
        for col in ("eia_crude_mb", "opos_net", "ovol_ovx", "ovol_rv20d", "ospr_spread", "ospr_curve_pct",
                    "opec_days_since_last", "eia_h_to_next"):
            assert full[col].notna().sum() > 1000, (asset, col)
        for cut in CUTS:
            t = pd.Timestamp(cut, tz=UTC)
            t_ms = int(t.value // 1000000)
            part_dir = str(tmp_path / ("cut%d" % t_ms))
            if not os.path.exists(part_dir):
                cut_files(full_dir, part_dir, t_ms)
            pb = dict((a, f[f.index + pd.Timedelta(minutes=15) <= t]) for a, f in bs.items())
            sub = idx[idx + pd.Timedelta(minutes=15) <= t]
            part = oil.features(sub, asset, bars=pb, src_dir=part_dir, strict=True)
            assert same(part, full.loc[sub]), (asset, cut)


def test_eia_week_reaches_rows_only_from_its_release(tmp_path):
    plant(str(tmp_path))
    bs = bars()
    idx = bs["WTI"].index[(bs["WTI"].index >= "2024-02-05") & (bs["WTI"].index < "2024-02-12")]
    f = oil.features(idx, "WTI", bars=bs, src_dir=str(tmp_path))
    rel = pd.Timestamp(oil.eia_release_for([SHIFTED_WEEK], str(tmp_path))[0], unit="ms", tz=UTC)
    assert ny(rel.value // 1000000).strftime("%a %H:%M") == "Thu 11:00"                # the calendar, not the rule
    assert rel == pd.Timestamp("2024-02-08 16:00", tz=UTC)
    raw = pd.read_csv(oil.path("eia_weekly", str(tmp_path))).set_index("date")
    want = raw.loc[SHIFTED_WEEK, "crude"] / 1000.0
    at = f.loc[rel - pd.Timedelta(minutes=15)]                         # the bar closing at the release
    before = f.loc[rel - pd.Timedelta(minutes=30)]
    assert at["eia_crude_mb"] == pytest.approx(want)
    assert before["eia_crude_mb"] != pytest.approx(want)
    assert at["eia_h_since_last"] == pytest.approx(0.0) and at["eia_since"] == pytest.approx(1.0)
    assert before["eia_h_to_next"] == pytest.approx(0.25)


def test_delayed_report_counts_from_the_delayed_release(tmp_path):
    plant_calendar(str(tmp_path))
    a, b = oil.eia_release_for([DELAYED_WEEK, "2023-11-10"], str(tmp_path))
    assert a == b and ny(a).strftime("%a %Y-%m-%d %H:%M") == "Wed 2023-11-15 10:30"   # not the rule's 8 Nov
    early = oil.eia_release_for(["2018-01-05"], str(tmp_path))[0]                     # before the archive: the rule
    assert ny(early).strftime("%a %Y-%m-%d %H:%M") == "Wed 2018-01-10 10:30"


def test_late_week_counts_from_when_it_was_seen(tmp_path):
    folder = str(tmp_path)
    plant(folder)
    raw = pd.read_csv(oil.path("eia_weekly", folder), dtype={"date": str}, float_precision="round_trip")
    rel = int(oil.eia_release_for(["2024-03-01"], folder)[0])
    seen = rel + 5 * U.H_MS
    raw.loc[raw["date"] == "2024-03-01", "known_ms"] = float(seen)
    U.write_csv(raw, oil.path("eia_weekly", folder))
    idx = pd.date_range("2024-03-05", "2024-03-08", freq="15min", tz=UTC)
    f = oil.features(idx, "WTI", bars=bars(), src_dir=folder)
    t = pd.Timestamp(seen, unit="ms", tz=UTC)
    assert f.loc[t - pd.Timedelta(minutes=30), "eia_week_age_d"] > 7.5                 # still the week before
    assert f.loc[t - pd.Timedelta(minutes=15), "eia_week_age_d"] < 7.5


def test_seasonal_norm_uses_only_earlier_years(tmp_path):
    folder = str(tmp_path)
    plant(folder)
    t = oil.eia_table(folder).set_index("date")
    raw = pd.read_csv(oil.path("eia_weekly", folder), dtype={"date": str}, float_precision="round_trip").set_index("date")
    chg = raw["crude"].diff()
    d = "2024-03-01"
    prior = [chg.index[np.argmin(np.abs(pd.to_datetime(chg.index) - (pd.Timestamp(d) - pd.Timedelta(days=round(365.25 * k)))))]
             for k in range(1, 6)]
    assert all(p < d for p in prior)
    assert t.loc[d, "crude_chg_norm"] == pytest.approx(chg.loc[prior].mean())
    early = t.loc["2014-01-03"]                                        # fewer than 3 earlier years: no norm
    assert not np.isfinite(early["crude_chg_norm"])


# ------------------------------------------------------------------ calendars
def test_release_rules():
    assert ny(oil.eia_rule_ms("2026-10-30")).strftime("%a %Y-%m-%d %H:%M") == "Wed 2026-11-04 10:30"
    assert ny(oil.eia_rule_ms("2026-11-06")).strftime("%a %Y-%m-%d %H:%M") == "Thu 2026-11-12 11:00"   # Veterans Day
    assert ny(oil.ice_release_ms("2026-11-03")).strftime("%a %Y-%m-%d %H:%M") == "Fri 2026-11-06 15:30"
    assert ny(oil.ice_release_ms("2024-03-26")).strftime("%a %Y-%m-%d") == "Tue 2024-04-02"            # Easter
    k = oil.eia_curve_known_ms(["2024-04-02", "2024-04-03", "2024-04-05"])                           # Tue, Wed, Fri
    assert [ny(x).strftime("%a %Y-%m-%d %H:%M") for x in k] == ["Thu 2024-04-04 17:00", "Thu 2024-04-11 17:00",
                                                                 "Thu 2024-04-11 17:00"]


def test_contract_months():
    assert oil.contract_expiry("CL", 2026, 12).isoformat() == "2026-11-20"
    assert oil.contract_expiry("BZ", 2027, 1).isoformat() == "2026-11-30"
    assert [oil.yahoo_symbol("CL", x) for x in oil.front_two("CL", "2026-11-11")] == ["CLZ26.NYM", "CLF27.NYM"]
    assert [oil.yahoo_symbol("CL", x) for x in oil.front_two("CL", "2026-11-23")] == ["CLF27.NYM", "CLG27.NYM"]
    assert [oil.yahoo_symbol("BZ", x) for x in oil.front_two("BZ", "2026-12-01")] == ["BZG27.NYM", "BZH27.NYM"]


def test_opec_visibility_and_flags(tmp_path):
    plant(str(tmp_path))
    idx = pd.date_range("2023-05-01", "2023-12-10", freq="15min", tz=UTC)
    f = oil.features(idx, "WTI", bars=bars(), src_dir=str(tmp_path))
    jun = pd.Timestamp("2023-06-04 13:00", tz=UTC)
    assert np.isnan(f.loc[jun - pd.Timedelta(days=22), "opec_days_to_next"])           # regular: seen 21 days ahead
    assert f.loc[jun - pd.Timedelta(days=20), "opec_days_to_next"] > 19
    assert f.loc[jun - pd.Timedelta(days=20), "opec_week"] == 0
    assert 0 < f.loc[jun - pd.Timedelta(days=3, minutes=15), "opec_week"] < 1          # the week before: flagged
    assert f.loc[jun + pd.Timedelta(days=1), "opec_after"] > 0
    nov = pd.Timestamp("2023-11-30 13:00", tz=UTC)                                     # moved at short notice
    assert np.isnan(f.loc[nov - pd.Timedelta(days=3), "opec_days_to_next"])
    assert f.loc[nov - pd.Timedelta(hours=6), "opec_days_to_next"] == pytest.approx(0.25, abs=0.02)


# ------------------------------------------------------------------ shape and signs
def test_bounded_never_nan_and_no_file_is_no_read(tmp_path):
    plant(str(tmp_path))
    bs = bars()
    for asset in oil.OIL:
        f = oil.features(bs[asset].index, asset, bars=bs, src_dir=str(tmp_path))
        assert not f[oil.FEATURES].isna().any().any()
        assert (f[oil.FEATURES].abs() <= 1.0).all().all()
        assert list(f.columns) == oil.FEATURES + oil.RAW
    empty_dir = str(tmp_path / "none")
    os.makedirs(empty_dir)
    pd.DataFrame(columns=calhistory.COLUMNS).to_csv(os.path.join(empty_dir, "calendar_history.csv"), index=False)
    idx = bs["WTI"].index[:500]
    e = oil.features(idx, "WTI", bars={"WTI": bs["WTI"].iloc[:0], "BRENT": bs["BRENT"].iloc[:0]}, src_dir=empty_dir)
    timing = ["eia_next", "eia_since"]                                 # the EIA schedule rule still speaks
    assert (e[[c for c in oil.FEATURES if c not in timing]] == 0).all().all()
    assert e[[c for c in oil.RAW if not c.startswith("eia_h_")]].isna().all().all()
    other = oil.features(idx, "XAUUSD", bars=bs, src_dir=str(tmp_path))
    assert (other[oil.FEATURES] == 0).all().all() and other[oil.RAW].isna().all().all()


def test_signs(tmp_path):
    plant(str(tmp_path))
    bs = bars()
    idx = bs["WTI"].index[bs["WTI"].index >= "2024-01-02"]
    w = oil.features(idx, "WTI", bars=bs, src_dir=str(tmp_path))
    b = oil.features(idx, "BRENT", bars=bs, src_dir=str(tmp_path))
    for c in ("ospr_z20", "ospr_z250", "ospr_chg1d"):                  # the spread: one market's gain is the other's loss
        assert np.allclose(w[c], -b[c])
    ok = w["eia_crude_chg_mb"].notna() & w["eia_crude_norm_mb"].notna()
    draw = (w["eia_crude_chg_mb"] - w["eia_crude_norm_mb"])[ok]
    assert (np.sign(w.loc[ok, "eia_crude"]) == -np.sign(draw)).all()   # a draw beyond the norm reads positive
    late = w[w.index >= "2024-05-01"]                                  # Yahoo rows only: front 0.50 above second
    assert late["ospr_curve_pct"].notna().all() and (late["ospr_curve_pct"] > 0).all() and (late["ospr_curve"] > 0).all()


def test_full_history_is_fast(tmp_path):
    import time
    plant(str(tmp_path))
    bs = bars("2019-01-01", "2024-06-30")
    t = time.time()
    oil.features(bs["WTI"].index, "WTI", bars=bs, src_dir=str(tmp_path))
    assert time.time() - t < 10.0


# ------------------------------------------------------------------ parsers
def test_parsers():
    weekly = ("<tr><td class='B6'>&nbsp;&nbsp;2026-Oct</td><td class='B5'>10/02&nbsp;</td><td class='B3'>424,134&nbsp;</td>"
              "<td class='B5'>10/09&nbsp;</td><td class='B3'>415,577&nbsp;</td><td class='B5'>&nbsp;</td><td class='B3'>&nbsp;</td></tr>"
              "<tr><td class='B6'>&nbsp;&nbsp;2027-Jan</td><td class='B5'>01/01&nbsp;</td><td class='B3'>400,000</td></tr>")
    w = oil.parse_eia_weekly(weekly)
    assert w.values.tolist() == [["2026-10-02", 424134.0], ["2026-10-09", 415577.0], ["2027-01-01", 400000.0]]
    daily = ("<tr><td class='B6'>&nbsp;&nbsp;2018 Dec-31 to Jan- 4</td><td class='B3'>45.41</td><td class='B3'></td>"
             "<td class='B3'>46.54</td><td class='B3'>47.09</td><td class='B3'>47.96</td></tr>")
    d = oil.parse_eia_daily(daily)
    assert d["date"].tolist() == ["2018-12-31", "2019-01-02", "2019-01-03", "2019-01-04"]
    ice = ("﻿Market_and_Exchange_Names,As_of_Date_In_Form_YYMMDD,As_of_Date_Form_MM/DD/YYYY,Open_Interest_All,"
           "M_Money_Positions_Long_All,M_Money_Positions_Short_All,FutOnly_or_Combined\n"
           "ICE Brent Crude Futures - ICE Futures Europe,261103,11/03/2026,2433965,290089,118486,FutOnly\n"
           "ICE Brent Crude Futures and Options - ICE Futures Europe,261103,11/03/2026,3000000,1,2,Combined\n"
           "ICE Gasoil Futures - ICE Futures Europe,261103,11/03/2026,1,1,1,FutOnly\n")
    c = oil.parse_ice_cot(ice)
    assert c.values.tolist() == [["2026-11-03", 2433965.0, 290089.0, 118486.0]]


# ------------------------------------------------------------------ update
def test_update_is_throttled_and_never_raises(tmp_path, monkeypatch):
    folder = str(tmp_path)
    plant_calendar(folder)
    calls = []
    weeks = pd.date_range("2012-01-06", "2026-10-30", freq="W-FRI").strftime("%Y-%m-%d")
    eia = pd.DataFrame({"date": weeks, "crude": 4e5, "cushing": 3e4, "gasoline": 2e5, "distillate": 1e5})
    tues = pd.date_range("2015-01-06", "2026-11-03", freq="W-TUE").strftime("%Y-%m-%d")
    cot = pd.DataFrame({"date": tues, "oi": 1e6, "long": 2e5, "short": 1e5})
    ydays = pd.bdate_range("2026-09-01", "2026-11-11").strftime("%Y-%m-%d")

    def rec(name, value):
        def fn(*a, **k):
            calls.append(name)
            return value() if callable(value) else value.copy()
        return fn
    monkeypatch.setattr(oil, "fetch_eia_weekly", rec("eia", eia))
    monkeypatch.setattr(oil, "fetch_cftc_wti", rec("cftc", lambda: cot.copy()))
    monkeypatch.setattr(oil, "fetch_ice_brent", rec("ice", lambda: cot.copy()))
    monkeypatch.setattr(oil, "fetch_eia_curve", rec("eiac", pd.DataFrame({"date": ["2024-04-04", "2024-04-05"],
                                                                          "c1": [86.6, 86.9], "c2": [85.9, 86.1]})))
    monkeypatch.setattr(oil, "_yahoo_daily", lambda sess, sym, start: (calls.append("y:" + sym),
                                                                      pd.DataFrame({"date": ydays, "close": 80.0,
                                                                                    "volume": 0.0}))[1])
    now = [int(pd.Timestamp("2026-11-11 23:00", tz=UTC).value // 1000000)]
    monkeypatch.setattr(U, "now_ms", lambda: now[0])
    out = oil.update(log=None, src_dir=folder)
    assert all(isinstance(v, int) and v > 0 for v in out.values()), out
    assert {"eia", "cftc", "ice", "eiac", "y:^OVX", "y:CLZ26.NYM", "y:CLF27.NYM", "y:BZF27.NYM", "y:BZG27.NYM"} <= set(calls)
    n = len(calls)
    out = oil.update(log=None, src_dir=folder)                         # nothing new is due: no request at all
    assert len(calls) == n and set(out.values()) == {"fresh"}
    curve = pd.read_csv(oil.path("curve_wti", folder))
    assert set(curve["m1_sym"]) == {"CLZ26.NYM"} and curve["date"].min() >= "2026-10-21"      # only its front-month days
    now[0] = int(pd.Timestamp("2026-11-12 17:00", tz=UTC).value // 1000000)               # the next EIA report is due
    out = oil.update(log=None, src_dir=folder)
    assert calls.count("eia") == 2 and "missing_since_ms" in U.load_state(oil.state_path(folder))["eia_weekly"]

    def broken(*a, **k):
        raise RuntimeError("network down")
    for name in ("fetch_eia_weekly", "fetch_cftc_wti", "fetch_ice_brent", "_yahoo_daily"):
        monkeypatch.setattr(oil, name, broken)
    now[0] += 2 * U.D_MS
    out = oil.update(log=None, src_dir=folder)
    assert any(str(v).startswith("failed") for v in out.values())
    assert len(pd.read_csv(oil.path("eia_weekly", folder))) == len(eia)


def test_describe_and_facts(tmp_path):
    plant(str(tmp_path))
    bs = bars()
    for asset in oil.OIL:
        f = oil.features(bs[asset].index, asset, bars=bs, src_dir=str(tmp_path))
        row = f.loc[pd.Timestamp("2024-06-03 15:00", tz=UTC)]
        words = oil.describe(row, asset)
        assert list(words) == [t for t, _fs in oil.GROUPS.values()]
        assert "million barrels" in words["EIA crude inventories"]
        assert "OVX" in words["Oil volatility"]
        assert ("NYMEX WTI" if asset == "WTI" else "ICE Brent") in words["Crude futures positioning (CFTC)"]
        assert "Brent minus WTI" in words["WTI-Brent and curve"]
        facts = oil.facts(row, asset)
        assert list(facts) == list(words) and all(len(v) >= 2 for v in facts.values())
    assert oil.describe(f.iloc[0], "XAUUSD") == {} and oil.facts(f.iloc[0], "XAUUSD") == {}
