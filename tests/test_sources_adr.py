# -*- coding: utf-8 -*-
"""adr (daily range budget and range breaks, H44 reading-only card): no look-ahead, ranges, daily value changes only
after the daily close, describe, and NOT wired yet (the parent wires it as a new version after review)."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15.sources import adr  # noqa: E402


def bars(n=96 * 40, seed=3, gaps=False):
    rng = np.random.RandomState(seed)
    ret = rng.normal(0, 0.003, n) + np.where(rng.rand(n) < 0.02, rng.normal(0, 0.02, n), 0.0)
    c = 100.0 * np.exp(np.cumsum(ret))
    o = np.concatenate([[100.0], c[:-1]])
    sp = np.abs(rng.normal(0, 0.002, n)) * c
    idx = pd.date_range("2025-03-01", periods=n, freq="15min", tz="UTC")
    df = pd.DataFrame({"open": o, "high": np.maximum(o, c) + sp, "low": np.minimum(o, c) - sp, "close": c}, index=idx)
    if gaps:
        m = df.index.hour * 60 + df.index.minute
        df = df[(m >= 810) & (m < 1200) & (df.index.dayofweek < 5)]
    return df


def test_no_look_ahead():
    for gaps in (False, True):
        b = bars(gaps=gaps)
        full = adr.features(b.index, "TEST", bars=b)
        assert not full.attrs["errors"]
        for cut in (int(len(b) * 0.55) + 7, int(len(b) * 0.85) + 50, len(b) - 3):
            part = adr.features(b.index[:cut], "TEST", bars=b.iloc[:cut])
            a = full.iloc[:cut][adr.FEATURES + adr.RAW].values.astype(float)
            p = part[adr.FEATURES + adr.RAW].values.astype(float)
            assert np.allclose(a, p, equal_nan=True, atol=1e-9), (gaps, cut)


def test_ranges_and_values():
    b = bars()
    f = adr.features(b.index, "TEST", bars=b)
    assert not f[adr.FEATURES].isna().any().any() and (f[adr.FEATURES].abs() <= 1.0).all().all()
    assert set(np.unique(f["adr_break_dir"].dropna())) <= {-1.0, 1.0}
    assert (f["adr_break"] != 0).any()
    late = f.iloc[96 * 20:]
    assert late["adr_datr_px"].notna().all()
    # used = today's range so far / daily ATR; room up + room down = 2 - used
    u = (late["adr_day_high_px"] - late["adr_day_low_px"]) / late["adr_datr_px"]
    assert np.allclose(u, late["adr_used_x"])
    assert np.allclose(late["adr_room_up_x"] + late["adr_room_dn_x"], 2.0 - late["adr_used_x"])
    assert (late["adr_pos_pct"].between(0, 100)).all()


def test_daily_value_changes_only_after_the_daily_close():
    for gaps in (False, True):
        b = bars(gaps=gaps)
        f = adr.features(b.index, "TEST", bars=b)
        day = f.index.normalize()                                  # the UTC day each bar opens in
        per_day = f["adr_datr_px"].groupby(day).nunique(dropna=True)
        assert (per_day <= 1).all()
        # the value held on day D is the daily ATR of the last day closed before D's first bar
        d1 = adr._ohlc_daily(b)
        from engine15 import indicators
        want = indicators.atr_wilder(d1, 14)
        days = sorted(set(day))
        for k in range(20, len(days)):
            got = f["adr_datr_px"][day == days[k]].iloc[0]
            prev = want[want.index < days[k]].iloc[-1]
            assert abs(got - prev) < 1e-9


def test_describe_and_not_wired():
    b = bars()
    f = adr.features(b.index, "TEST", bars=b)
    title = "Daily range budget and range breaks"
    say = adr.describe(f.iloc[-1], "TEST")
    assert list(say) == [title] and say[title].startswith("Daily ATR(14)")
    i = int(np.flatnonzero(f["adr_break_bars"].values == 0)[-1])
    assert "Range break with momentum" in adr.describe(f.iloc[i], "TEST")[title]
    assert "no read" in adr.describe(f.iloc[0], "TEST")[title]
    assert adr.update() == {}
    from engine15 import sources
    assert "adr" in sources.MODULES                                      # wired as think15-v5.2.3 (16 Nov 2026)
