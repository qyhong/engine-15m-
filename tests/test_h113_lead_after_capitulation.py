# -*- coding: utf-8 -*-
"""H113's own helpers on small made-up series (no evidence store, no fits)."""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "research"))

import h113_lead_after_capitulation as h  # noqa: E402


def _t(n, start="2022-01-01"):
    return pd.date_range(start, periods=n, freq="15min", tz="UTC")


def test_segments_cut_where_registered():
    t = pd.DatetimeIndex(["2023-06-07 23:45", "2023-06-08 00:00", "2025-11-10 23:45", "2025-11-11 00:00",
                          "2026-11-18 23:45", "2026-11-19 00:00"], tz="UTC")
    want = ["h1", "h2", "h2", "holdout", "holdout", "event"]
    assert [h.seg_of(x) for x in t] == want
    assert list(h.seg_array(t)) == want


def test_window_is_the_trigger_close_and_the_next_191():
    m = h.window_mask(1000, [100])
    assert not m[99] and m[100] and m[291] and not m[292] and m.sum() == 192
    m = h.window_mask(1000, [100, 250])                       # a later trigger extends the window
    assert m[100:442].all() and not m[442] and m.sum() == 342
    s = h.bars_since(1000, [100, 250])
    assert s[99] > 10 ** 6 and s[100] == 0 and s[249] == 149 and s[250] == 0 and s[300] == 50


def test_first_at_or_above_counts_hours_from_the_anchor_close():
    path = np.array([-3.0, -2.0, np.nan, -1.0, 0.0, 6.0])
    assert h.first_at_or_above(path, 0.0) == 1.0              # the fifth close: four bars, one hour
    assert h.first_at_or_above(path, 5.0) == 1.25
    assert h.first_at_or_above(path, 10.0) is None
    assert h.first_at_or_above(np.array([0.5, -1.0]), 0.0) == 0.0


def test_confirmed_lows_need_the_drop_the_30_day_low_and_no_lower_low_for_48_hours():
    n = 96 * 60
    t = _t(n)
    low = np.full(n, 100.0)
    k1, k2, k3 = 96 * 40, 96 * 40 + 300, 96 * 50
    low[k1 - 96 * 3:k1] = np.linspace(100, 86, 96 * 3)        # a slide into a low at k1 ...
    low[k1] = 85.0
    low[k1 + 1:] = 90.0
    low[k2] = 84.0                                            # ... a lower low 75 hours later (inside 7 days) ...
    low[k3] = 80.0                                            # ... and another 10 days after the first
    lowN = pd.Series(low, index=t).rolling("30D").min().values
    cref = np.full(n, 100.0)
    lead = np.full(n, -5.0)
    ks, cand = h.confirmed_lows(t, low, lowN, cref, lead)
    assert cand == 3 and list(ks) == [k1, k3]                 # k2 is a candidate, dropped by the 7-day rule
    low2 = low.copy()
    low2[k1 + 100] = 84.5                                     # undercut inside 48 hours: k1 is no longer confirmed
    lowN2 = pd.Series(low2, index=t).rolling("30D").min().values
    ks2, _ = h.confirmed_lows(t, low2, lowN2, cref, lead)
    assert k1 not in ks2 and k1 + 100 in ks2
    ks3, _ = h.confirmed_lows(t, low, lowN, np.full(n, 90.0), lead)   # only 5.6% under a week earlier at k1
    assert k1 not in ks3 and k3 in ks3
    lead_nan = lead.copy()
    lead_nan[k1] = np.nan                                     # no Lead at the bar: not an event
    assert k1 not in h.confirmed_lows(t, low, lowN, cref, lead_nan)[0]
    ks_end, _ = h.confirmed_lows(t[:k3 + 100], low[:k3 + 100], lowN[:k3 + 100], cref[:k3 + 100], lead[:k3 + 100])
    assert k3 not in ks_end                                   # fewer than 192 bars after it: cannot be confirmed


def test_anchor_row_reads_marks_and_time_to_turn():
    n = 1000
    t = _t(n)
    lead = np.full(n, -4.0)
    lead[500 + 100:] = 1.0                                    # turns up 25 hours after bar 500
    close = np.linspace(100, 110, n)
    low = close - 1.0
    r = h.anchor_row("BTCUSDT", 500, t, lead, close, low, anchor_px=float(low[500]))
    assert r["to_zero_h"] == 25.0 and r["to_long_bar_h"] is None
    assert r["down_at_24h"] is True and r["down_at_48h"] is False and r["down_at_72h"] is False
    assert len(r["hourly"]) == 97 and r["hourly"][24] == -4.0 and r["hourly"][24 + 25] == 1.0
    assert abs(r["px_vs_low_24h"] - (close[596] / low[500] - 1) * 100) < 1e-9
    late = h.anchor_row("BTCUSDT", n - 50, t, lead, close, low)
    assert late["full_72h"] is False and late["down_at_24h"] is None
    s = h.summarise([r, dict(r, to_zero_h=None)])
    assert s["n"] == 2 and s["zero_never_in_72h"] == 1 and s["zero_median_h"] is None
    assert s["zero_within_48h_pct"] == 50.0 and s["down_at_24h_pct"] == 100.0


def _cell(n_in, m_in, n_out, m_out):
    return {"in": {"n": n_in, "mean_r": m_in}, "out": {"n": n_out, "mean_r": m_out}}


def test_verdict_follows_the_registered_condition():
    assert h.verdict(_cell(25, -0.2, 300, -0.05), _cell(20, -0.1, 300, 0.0))[0] == "PASS"
    assert h.verdict(_cell(25, -0.2, 300, -0.05), _cell(19, -0.5, 300, 0.0))[0].startswith("TOO FEW")
    assert h.verdict(_cell(25, 0.1, 300, 0.2), _cell(30, -0.1, 300, 0.0))[0] == "DOES NOT PASS"     # above zero in h1
    assert h.verdict(_cell(25, -0.1, 300, -0.2), _cell(30, -0.1, 300, 0.0))[0] == "DOES NOT PASS"   # not below the others


def test_bootstrap_of_the_difference_is_reproducible_and_centred():
    rng = np.random.default_rng(1)
    months = [202201 + i for i in range(12)]
    df = pd.DataFrame({"month": rng.choice(months, 600), "inwin": rng.random(600) < 0.2, "r": rng.normal(0, 1, 600)})
    df.loc[df.inwin, "r"] -= 0.5
    a, b = h.boot_diff(df, months, draws=2000), h.boot_diff(df, months, draws=2000)
    assert a == b and a["lo"] < a["obs"] < a["hi"] and a["obs"] < 0
    assert abs(a["obs"] - (df[df.inwin].r.mean() - df[~df.inwin].r.mean())) < 1e-12
    assert h.boot_diff(df[~df.inwin], months) is None
