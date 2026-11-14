# -*- coding: utf-8 -*-
"""Look-ahead tests: features must never read the future.

1. For random cut points t, features computed on data truncated at t equal the full-data
   features up to t (within 1e-12 absolute / 1e-9 relative; in practice bit for bit).
2. Each funding value appears only at or after its settlement time, and from the first bar
   whose close reaches that settlement.
3. A deliberately leaky feature is caught by the same check (the check has teeth).
"""
import numpy as np
import pandas as pd

from conftest import make_bars, make_funding
from engine15.rl import data, features, store


def _builder(b, f):
    return features.build(b, f)


def test_truncated_features_equal_full_features_at_random_cuts():
    bars = make_bars(n=5000, seed=7)
    fund = make_funding(bars.index, seed=8)
    rng = np.random.default_rng(11)
    cuts = sorted(set(int(c) for c in rng.integers(700, len(bars) - 1, 8))) + [len(bars) - 1, 1000]
    rep = features.lookahead_report(_builder, bars, fund, cuts)
    assert all(v == [] for v in rep.values()), rep


def test_truncated_features_are_bit_for_bit():
    bars = make_bars(n=3000, seed=3)
    fund = make_funding(bars.index, seed=4)
    full = features.build(bars, fund)
    for cut in (1500, 2222, 2999):
        part = features.build(bars.iloc[:cut], fund)
        a, b = full.iloc[:cut].values, part.values
        assert np.array_equal(np.isnan(a), np.isnan(b))
        ok = ~np.isnan(a)
        assert np.max(np.abs(a[ok] - b[ok])) <= 1e-12


def test_cut_at_end_of_day_and_mid_day_keeps_daily_feature():
    bars = make_bars(n=2000, seed=5)
    full = features.build(bars, None)
    for cut in (96 * 10, 96 * 10 + 37):                         # exactly at a day's last bar, and mid-day
        part = features.build(bars.iloc[:cut], None)
        x, y = full["ret_1d_closed"].values[:cut], part["ret_1d_closed"].values
        assert np.allclose(x, y, equal_nan=True, atol=1e-15)


def test_daily_feature_uses_only_closed_days():
    bars = make_bars(n=96 * 4, seed=6)
    f = features.build(bars, None)
    day1 = bars.iloc[:96]
    want = np.log(day1["close"].iloc[-1] / day1["open"].iloc[0])
    assert np.isnan(f["ret_1d_closed"].iloc[:95]).all()        # day 1 not closed yet
    assert np.isclose(f["ret_1d_closed"].iloc[95], want)        # its last bar's close closes the day
    assert np.isclose(f["ret_1d_closed"].iloc[96 + 50], want)


def test_funding_appears_only_at_or_after_settlement():
    bars = make_bars(n=3000, seed=9)
    fund = make_funding(bars.index, seed=10)
    f = features.build(bars, fund)
    close_ms = store.to_ms(bars.index) + 900000
    s = np.asarray(fund["settle_ms"], dtype="int64")
    r = fund["rate"].values
    seen = f["funding_rate"].values
    for j in range(1, len(s) - 1):
        first = np.searchsorted(close_ms, s[j], side="left")     # first bar whose close reaches the settlement
        if first >= len(close_ms):
            continue
        assert seen[first] == r[j], "rate %d not visible at its settlement bar" % j
        if first > 0:
            assert seen[first - 1] != r[j] or r[j - 1] == r[j], "rate %d visible before its settlement" % j
    # and nowhere does a bar carry a rate settled after its close
    k = np.searchsorted(s, close_ms, side="right") - 1
    ok = k >= 0
    assert np.all(s[k[ok]] <= close_ms[ok])


def test_settlement_snapping_never_moves_a_stamp_earlier_than_its_grid_time():
    raw = np.array([1568102400000, 1568102400002, 1568102400047, 1568102400000 + 120000, 1568102400000 + 900000])
    s = data.settlement_ms(raw, 900000, 60)
    assert list(s) == [1568102400000, 1568102400000, 1568102400000, 1568102400000 + 900000, 1568102400000 + 900000]
    assert np.all(s >= raw - 60000)


def test_time_to_next_funding_counts_down_from_past_settlements():
    bars = make_bars(n=200, seed=1, start="2022-01-01")
    fund = make_funding(bars.index, jitter=False)
    f = features.build(bars, fund)
    h = f["hours_to_funding"]
    # bar 08:00 closes at 08:15: last settlement 08:00, previous 00:00 -> next 16:00 -> 7.75 h
    assert np.isclose(h.loc[pd.Timestamp("2022-01-01 08:00", tz="UTC")], 7.75)
    assert np.isnan(h.iloc[0])                                  # one settlement seen: no interval yet


def test_a_deliberate_lookahead_feature_is_caught():
    bars = make_bars(n=3000, seed=12)
    fund = make_funding(bars.index, seed=13)

    def leaky(b, f):
        out = features.build(b, f)
        out["peek"] = b["close"].shift(-1) / b["close"] - 1.0           # tomorrow's return: a leak
        out["centered"] = b["close"].rolling(9, center=True).mean()     # a centred window: a leak
        return out

    rep = features.lookahead_report(leaky, bars, fund, [1200, 2500])
    for cut, bad in rep.items():
        assert "peek" in bad and "centered" in bad, rep
        assert set(bad) <= {"peek", "centered"}, rep


def test_funding_read_early_is_caught():
    """A builder that shows each rate one bar BEFORE its settlement must fail the check."""
    bars = make_bars(n=3000, seed=14)
    fund = make_funding(bars.index, seed=15)

    def early(b, f):
        g = f.copy()
        g["settle_ms"] = g["settle_ms"] - 900000
        return features.build(b, g)

    def honest_cut_report(builder):
        full = builder(bars, fund)
        bad = 0
        for cut in range(1000, 1070):                           # every cut over two settlement cycles
            t_close = int(store.to_ms(bars.index[cut - 1:cut])[0]) + 900000
            part = builder(bars.iloc[:cut], fund[fund["settle_ms"] <= t_close])
            x, y = full["funding_rate"].values[:cut], part["funding_rate"].values
            bad += int(not np.allclose(x, y, equal_nan=True))
        return bad

    assert honest_cut_report(lambda b, f: features.build(b, f)) == 0
    assert honest_cut_report(early) > 0
