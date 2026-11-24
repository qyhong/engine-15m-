# -*- coding: utf-8 -*-
"""H112 (research/h112_entry_bar_per_market.py): the fit of the per-market bar, the scaled cfg, the read-outs and the
verdict, on planted numbers. No evidence store, no network.

    py -3 -m pytest tests/test_h112_entry_bar.py -q
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import h112_entry_bar_per_market as h  # noqa: E402
from engine15 import labels, policy  # noqa: E402
from engine15.config import CFG  # noqa: E402
from test_shadows import random_inputs, run_random  # noqa: E402


def test_lead_is_up_minus_down_in_points():
    odds = np.zeros((2, 3))
    odds[0, labels.UP], odds[0, labels.DOWN] = 0.40, 0.33
    odds[1] = np.nan
    lead = h.lead_pts(odds)
    assert lead[0] == pytest.approx(7.0) and np.isnan(lead[1])


def test_the_fitted_bar_is_cleared_as_often_as_five_points_on_crypto():
    rng = np.random.RandomState(1)
    btc, eth = np.abs(rng.normal(0, 6, 40000)), np.abs(rng.normal(0, 5, 30000))
    p = h.crypto_share([btc, eth])
    assert p == pytest.approx(((btc >= 5).sum() + (eth >= 5).sum()) / 70000.0)      # one count over both coins
    gold = np.abs(rng.normal(0, 1.5, 50000))
    gold[::7] = np.nan                                                             # sessions with no odds are no steps
    bar = h.fit_bar(gold, p)
    assert 1.0 < bar < 5.0
    assert h.share_at(gold, bar) / 100.0 == pytest.approx(p, abs=0.002)             # rounding to 0.01 point
    assert h.fit_bar(np.abs(rng.normal(0, 0.1, 5000)), p) == 1.0                    # the floor
    assert h.fit_bar(np.abs(rng.normal(0, 12, 5000)), p) > 5.0                      # no cap above 5


def test_segments_are_disjoint_and_cover_the_window():
    times = pd.date_range("2020-01-01", "2026-11-24 04:30", freq="6h", tz="UTC")
    lo, n = 10, len(times)
    s = h.seg_bounds(times, lo, n)
    assert s["h1"][0] == lo and s["forward"][1] == n
    assert s["h1"][1] == s["h2"][0] and s["h2"][1] == s["holdout"][0] and s["holdout"][1] == s["forward"][0]
    assert str(times[s["h2"][0]])[:10] == "2023-06-08" and str(times[s["h2"][1] - 1])[:10] == "2025-11-10"
    assert str(times[s["holdout"][0]])[:10] == "2025-11-11" and str(times[s["forward"][0]])[:10] == "2026-11-11"


def test_rule_cfg_scales_only_what_is_registered():
    cur = h.rule_cfg(CFG, "current", 0.4)
    assert all(cur[k] == CFG[k] for k in h.BASE)
    allb = h.rule_cfg(CFG, "all_scaled", 0.4)
    assert [allb[k] for k in ("theta_enter", "theta_enter_shock", "theta_flip", "theta_counter")] == \
        pytest.approx([0.02, 0.04, 0.04, 0.06])
    one = h.rule_cfg(CFG, "enter_only", 0.4)
    assert one["theta_enter"] == pytest.approx(0.02)
    assert all(one[k] == CFG[k] for k in ("theta_enter_shock", "theta_flip", "theta_counter"))
    for c in (allb, one):                                          # nothing else moves, and CFG itself is untouched
        assert all(c[k] == CFG[k] for k in CFG if k not in h.BASE)
    assert CFG["theta_enter"] == 0.05
    with pytest.raises(RuntimeError):
        h.rule_cfg(dict(CFG, theta_flip=0.2), "current", 1.0)


def test_the_scaled_bars_reach_the_policy():
    cfg = h.rule_cfg(dict(CFG, htf_bias=True), "all_scaled", 0.4)
    # a 3-point lead from flat: below today's 5, above the scaled 2
    assert policy.decide(0, 0, 0.365, 0.335, False, 0.0, CFG)[0] == policy.IDLE
    assert policy.decide(0, 0, 0.365, 0.335, False, 0.0, cfg)[0] == policy.ENTER
    # against the bias the scaled counter bar is 6 points: 3 does not enter, 7 does
    assert policy.decide(0, 0, 0.365, 0.335, False, 0.0, cfg, bias=-1)[0] == policy.IDLE
    assert policy.decide(0, 0, 0.385, 0.315, False, 0.0, cfg, bias=-1)[:2] == (policy.ENTER, 1)
    # held long, the other side leads by 5: a flip under the scaled bar (4), a hold under today's (10)
    assert policy.decide(1, 0, 0.31, 0.36, False, 0.0, cfg)[0] == policy.FLIP
    assert policy.decide(1, 0, 0.31, 0.36, False, 0.0, CFG)[0] == policy.HOLD
    only = h.rule_cfg(CFG, "enter_only", 0.4)
    assert policy.decide(1, 0, 0.31, 0.36, False, 0.0, only)[0] == policy.HOLD
    assert policy.decide(0, 0, 0.365, 0.335, True, 0.0, only)[0] == policy.IDLE     # high risk: still 10 points
    assert policy.decide(0, 0, 0.365, 0.335, True, 0.0, cfg)[0] == policy.IDLE      # scaled high-risk bar is 4
    assert policy.decide(0, 0, 0.375, 0.325, True, 0.0, cfg)[0] == policy.ENTER


@pytest.mark.parametrize("seed", [3, 11])
def test_book_stats_and_pool_add_up(seed):
    inp = random_inputs(seed=seed)
    n = len(inp[0]["close"])
    a = 300                                                        # a book that starts flat at session a
    b = run_random({"targets": True}, inp, lo=a, hi=n, cfg=h.rule_cfg(CFG, "all_scaled", 1.0))
    ref = run_random({"targets": True}, inp, lo=a, hi=n)
    assert len(b["trades"]) == len(ref["trades"]) and np.allclose(b["equity"][a:], ref["equity"][a:])   # scale 1 = current
    s = h.book_stats(b, a, n, fresh=True)
    tr = b["trades"]
    assert s["trades"] == len(tr) > 20
    assert sum(s["words"][w]["trades"] for w in h.WORDS) == s["trades"]
    assert sum(s["words"][w]["sum_r"] for w in h.WORDS) == pytest.approx(s["sum_r"])
    assert s["net"] == pytest.approx(b["equity"][n - 1] - h.START)
    assert s["worst_fall"] <= 0.0
    low = run_random({"targets": True}, inp, lo=a, hi=n, cfg=h.rule_cfg(CFG, "enter_only", 0.2))
    s2 = h.book_stats(low, a, n, fresh=True)
    assert s2["words"]["ENTER"]["trades"] > s["words"]["ENTER"]["trades"]          # a lower bar: more real calls
    p = h.pool([s, s2])
    assert p["trades"] == s["trades"] + s2["trades"] and p["sum_r"] == pytest.approx(s["sum_r"] + s2["sum_r"])
    assert p["mean_r"] == pytest.approx(p["sum_r"] / p["n_r"])
    assert p["net"] == pytest.approx(s["net"] + s2["net"])


def test_fall_counts_a_loss_from_the_start():
    assert h.fall([h.START * 0.9, h.START * 0.95]) == pytest.approx(-10.0)
    assert h.fall([h.START * 1.1, h.START * 0.99]) == pytest.approx(-10.0)


def test_months_and_the_bootstrap():
    months_all = h.months_between(pd.Timestamp("2023-06-08", tz="UTC"), pd.Timestamp("2023-09-02", tz="UTC"))
    assert months_all == ["2023-06", "2023-07", "2023-08", "2023-09"]
    d = h.month_sums(["2023-06", "2023-06", "2023-09"], [1.0, -0.5, 2.0], months_all)
    assert list(d) == [0.5, 0.0, 0.0, 2.0]                         # a month with no trade counts as zero
    b = h.boot_diff(np.full(24, 1.0), draws=500)
    assert b["diff"] == 24.0 and b["lo"] == b["hi"] == 24.0 and b["share_above_zero"] == 100.0
    b2 = h.boot_diff(np.array([1.0, -1.0] * 12), draws=2000)
    assert b2["lo"] < 0 < b2["hi"]
    assert h.boot_diff(np.array([1.0, -1.0] * 12), draws=2000) == b2             # seeded


def _cell(sum_r, enter=(40, 0.1), forced=(40, 0.0)):
    w = {"ENTER": {"trades": enter[0], "n_r": enter[0], "mean_r": enter[1], "sum_r": enter[0] * enter[1]},
         "FORCED": {"trades": forced[0], "n_r": forced[0], "mean_r": forced[1], "sum_r": forced[0] * forced[1]},
         "FLIP": {"trades": 0, "n_r": 0, "mean_r": None, "sum_r": 0.0}}
    return {"sum_r": sum_r, "words": w}


def test_the_verdict_needs_all_three_legs():
    cur = {"h2": _cell(10.0), "holdout": _cell(5.0)}
    ok = h.verdict({"current": cur, "all_scaled": {"h2": _cell(12.0), "holdout": _cell(6.0)}})
    assert ok["passes"] and all(ok["legs"].values())
    assert not h.verdict({"current": cur, "all_scaled": {"h2": _cell(10.0), "holdout": _cell(6.0)}})["passes"]   # equal is not higher
    assert not h.verdict({"current": cur, "all_scaled": {"h2": _cell(12.0), "holdout": _cell(4.0)}})["passes"]
    worse = {"h2": _cell(12.0, enter=(40, -0.1)), "holdout": _cell(6.0)}
    assert not h.verdict({"current": cur, "all_scaled": worse})["passes"]
    few = {"h2": _cell(12.0, forced=(29, -1.0)), "holdout": _cell(6.0)}
    v = h.verdict({"current": cur, "all_scaled": few})
    assert not v["passes"] and not v["enough_trades_leg3"]
