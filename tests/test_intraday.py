# -*- coding: utf-8 -*-
"""Workstream M (engine15/intraday.py): the short-horizon minds, the EV filter and the swing book,
on planted bars. No network, no history files.

    py -3 -m pytest tests/test_intraday.py -q
"""
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import intraday, labels, model, shadows  # noqa: E402
from engine15.config import CFG  # noqa: E402

UPO, DNO, FLATO = [0.1, 0.7, 0.2], [0.1, 0.2, 0.7], [0.6, 0.2, 0.2]
CHEAP = dict(CFG, cost_side=0.0001, leverage_cap=1.0)
BARRIER = dict(intraday.SWING_RULES["1h"], stop="barrier", target="r", target_r=1.5, margin=0.05)


# ------------------------------------------------------------------ helpers
def flat_bars(n, price=100.0, wick=0.2):
    o = np.full(n, price)
    return {"open": o.copy(), "high": o + wick, "low": o - wick, "close": o.copy()}


def odds_of(n, row):
    return np.tile(np.asarray(row, float), (n, 1))


def swing(px, odds, rule=None, unit=1.0, cfg=CHEAP, lo=0, hi=None, state=None, guard=None, aux=None):
    n = len(px["close"])
    return intraday.run_swing(px, odds, np.full(n, float(unit)), cfg, lo, hi or n, state=state, guard=guard,
                              rule=rule or BARRIER, aux=aux, times_ms=np.arange(n, dtype="int64") * 900000)


# ------------------------------------------------------------------ labels at the new horizons
def test_labels_at_the_1h_and_4h_horizons():
    n = 40
    px = flat_bars(n, wick=0.0)
    atr = np.full(n, 2.0)                                        # 1h mind barrier: 0.75 x 2 = 1.5; 4h mind: 2.0
    px["high"][4] = 101.6                                        # +1.6 at bar 4 (call at bar 0: fill bar 1, window 1..4)
    y1, r1 = intraday.labels_for(px, atr, intraday.MINDS["1h"])
    assert y1[0] == labels.UP and r1[0] == 4                     # touched on the 4th bar of the window: inside 1h
    assert y1[3] == labels.UP and r1[3] == 1
    assert y1[5] == labels.NEITHER and r1[5] == 4                # nothing within 4 bars after bar 5
    y4, r4 = intraday.labels_for(px, atr, intraday.MINDS["4h"])
    assert y4[0] == labels.NEITHER                               # +1.6 is short of the 4h mind's 2.0 barrier
    px["low"][15] = 97.9                                         # -2.1 at bar 15: inside the 4h window of bar 0
    y4, r4 = intraday.labels_for(px, atr, intraday.MINDS["4h"])
    assert y4[0] == labels.DOWN and r4[0] == 15
    y1, _ = intraday.labels_for(px, atr, intraday.MINDS["1h"])
    assert y1[0] == labels.UP                                    # the 1h mind never looks that far
    assert (y4[-16:] == labels.UNKNOWN).all() and (y1[-4:] == labels.UNKNOWN).all()   # the last calls are not graded yet


def test_sessions_and_weekly_fit_points():
    t = pd.date_range("2026-11-08 20:00", periods=8 * 4 * 6, freq="15min", tz="UTC")   # Sunday 20:00 on, 48 hours
    s = intraday.session_of(t)
    close_hr = (t + pd.Timedelta(minutes=15)).hour
    assert set(s[(close_hr >= 7) & (close_hr < 12)]) == {"london"}
    assert set(s[(close_hr >= 12) & (close_hr < 16)]) == {"overlap"}
    assert set(s[(close_hr >= 16) & (close_hr < 21)]) == {"ny"}
    assert set(s[(close_hr >= 21) | (close_hr < 7)]) == {"asia"}
    fp = intraday.fit_points(t, 0, len(t))
    assert len(fp) == 2                                          # Sunday's bars, then Monday 9 Nov 00:00 on
    assert pd.Timestamp(fp[1][0], unit="ms", tz="UTC") == pd.Timestamp("2026-11-09", tz="UTC")
    assert t[fp[1][1]] == pd.Timestamp("2026-11-09", tz="UTC") and fp[1][2] == fp[1][1]


# ------------------------------------------------------------------ the minds: no look-ahead
def synthetic_group(n=96 * 7 * 7, seed=1, d=4):
    rng = np.random.RandomState(seed)
    times = pd.date_range("2026-01-05", periods=n, freq="15min", tz="UTC")
    X, ready, px, atr = {}, {}, {}, {}
    for a in ("A", "B"):
        x = rng.normal(0, 1, (n, d))
        drift = 0.0015 * np.tanh(x[:, 0])                        # a planted lean: feature 0 leads the next bars
        r = np.concatenate([[0.0], drift[:-1]]) + rng.normal(0, 0.003, n)
        c = 100 * np.exp(np.cumsum(r))
        o = np.concatenate([[100.0], c[:-1]])
        sp = np.abs(rng.normal(0, 0.0015, n)) * c
        px[a] = {"open": o, "high": np.maximum(o, c) + sp, "low": np.minimum(o, c) - sp, "close": c}
        X[a], ready[a], atr[a] = x, np.ones(n, bool), c * 0.004
        ready[a][:30] = False
    return times, X, ready, px, atr


VOX = ["v1", "v2", "base"]
VCOLS = {"v1": [0, 1], "v2": [2, 3], "base": []}
SMALL = dict(CFG, train_step=4, min_train_rows=60, l2=10.0)


def _cut(d, k):
    return dict((a, (dict((kk, vv[:k]) for kk, vv in v.items()) if isinstance(v, dict) else v[:k])) for a, v in d.items())


@pytest.mark.parametrize("mind", list(intraday.MINDS))
def test_short_horizon_odds_never_read_the_future(mind):
    times, X, ready, px, atr = synthetic_group()
    n, lo = len(times), 96 * 7
    full = intraday.mind_odds(X, ready, px, atr, times, VCOLS, VOX, SMALL, intraday.MINDS[mind], lo, n, 0)
    assert np.isfinite(full["odds"]["A"][lo + 96 * 7:]).all()    # the mind has a model after its first weeks
    for k in (96 * 7 * 3 + 17, 96 * 7 * 5 + 401):
        cut = intraday.mind_odds(_cut(X, k), _cut(ready, k), _cut(px, k), _cut(atr, k), times[:k], VCOLS, VOX, SMALL,
                                 intraday.MINDS[mind], lo, k, 0)
        for a in ("A", "B"):
            np.testing.assert_array_equal(full["odds"][a][:k], cut["odds"][a][:k])


def test_short_horizon_mind_learns_a_planted_lean():
    times, X, ready, px, atr = synthetic_group(seed=4)
    n, lo = len(times), 96 * 7 * 2
    r = intraday.mind_odds(X, ready, px, atr, times, VCOLS, VOX, SMALL, intraday.MINDS["1h"], lo, n, 0)
    hits = []
    for a in ("A", "B"):
        od, y = r["odds"][a][lo:], r["y"][a][lo:]
        ok = (y > 0) & np.isfinite(od[:, 0])
        edge = od[ok, labels.UP] - od[ok, labels.DOWN]
        hits.append(((edge > 0) == (y[ok] == labels.UP)).mean())
    assert min(hits) > 0.55


def test_cache_gives_the_same_odds_without_refitting():
    times, X, ready, px, atr = synthetic_group(n=96 * 7 * 4)
    n, lo = len(times), 96 * 7
    cache, msgs = {}, []
    a = intraday.mind_odds(X, ready, px, atr, times, VCOLS, VOX, SMALL, intraday.MINDS["4h"], lo, n, 0, cache, log=msgs.append)
    assert msgs and len(cache) == 3
    cache = json.loads(json.dumps(cache))                        # through JSON, as on disk
    msgs2 = []
    b = intraday.mind_odds(X, ready, px, atr, times, VCOLS, VOX, SMALL, intraday.MINDS["4h"], lo, n, 0, cache, log=msgs2.append)
    assert not msgs2                                             # no refit
    np.testing.assert_allclose(a["odds"]["A"], b["odds"]["A"], rtol=0, atol=1e-12)


# ------------------------------------------------------------------ M2: the EV filter
def test_expected_value_in_r():
    # P(win) 0.45, P(loss) 0.30, crypto 0.10% a side, price 100, risk 1.0 -> 0.15 - 0.20 = -0.05 R
    assert intraday.ev_r(0.45, 0.30, 0.001, 100.0, 1.0) == pytest.approx(-0.05)
    assert intraday.ev_r(0.45, 0.30, 0.0001, 100.0, 1.0) == pytest.approx(0.13)       # USDJPY-like costs
    side, ev = intraday.best_ev(np.array([[0.25, 0.30, 0.45]]), 0.0002, np.array([100.0]), np.array([1.0]))
    assert side[0] == -1 and ev[0] == pytest.approx(0.15 - 0.04)


def test_swing_book_trades_only_above_the_margin():
    n = 30
    px = flat_bars(n)
    weak = odds_of(n, [0.4, 0.33, 0.27])                         # edge 6 points
    assert swing(px, weak, cfg=dict(CHEAP, cost_side=0.001))["state"]["pending"] is None    # crypto cost: -0.14 R
    r = swing(px, weak, cfg=dict(CHEAP, cost_side=0.00001), hi=1)                            # 0.06 - 0.002 >= 0.05
    assert r["state"]["pending"] is not None and r["state"]["pending"][1] == 1
    assert swing(px, weak, rule=dict(BARRIER, margin=0.10), cfg=dict(CHEAP, cost_side=0.00001))["state"]["stats"]["n"] == 0
    g = np.ones(n, bool)
    assert swing(px, odds_of(n, UPO), guard=g)["state"]["stats"]["n"] == 0                   # release guard: no entry


# ------------------------------------------------------------------ M3: swing management on planted bars
def test_target_hit():
    px = flat_bars(12)
    px["high"][3] = 101.6                                        # entry 100 at bar 1, stop 99, target 101.5
    r = swing(px, odds_of(12, UPO), hi=4)
    t = r["trades"].iloc[0]
    assert (t.i_in, t.i_out, t.side, t.p_in, t.p_out, t.why_out) == (1, 3, 1, 100.0, 101.5, "TARGET")
    assert t.stop0 == 99.0 and t.target_1 == 101.5
    qty = 10000.0 / 100.0
    assert t.fees_usd == pytest.approx(0.0001 * qty * (100.0 + 101.5))
    assert t.pnl_usd == pytest.approx(qty * 1.5 - t.fees_usd)
    assert t.r_gross == pytest.approx(1.5) and t.r_mult == pytest.approx(1.5 - t.fees_usd / qty)


def test_stop_hit_and_gap_through_the_stop():
    px = flat_bars(12)
    px["low"][2] = 98.9
    t = swing(px, odds_of(12, UPO), hi=3)["trades"].iloc[0]
    assert (t.why_out, t.p_out, t.r_gross) == ("STOP", 99.0, -1.0)
    px = flat_bars(12)
    px["open"][2], px["low"][2], px["close"][2] = 98.0, 97.8, 98.0      # opens below the stop: filled at the open
    t = swing(px, odds_of(12, UPO), hi=3)["trades"].iloc[0]
    assert (t.why_out, t.p_out) == ("STOP", 98.0)


def test_stop_first_when_stop_and_target_share_a_bar():
    px = flat_bars(12)
    px["high"][2], px["low"][2] = 101.7, 98.8
    t = swing(px, odds_of(12, DNO), hi=3)["trades"].iloc[0]      # a short: stop 101, target 98.5, both inside bar 2
    assert (t.side, t.why_out, t.p_out) == (-1, "STOP", 101.0)


def test_time_stop_at_the_horizon_and_renewal():
    n = 12
    px = flat_bars(n)
    od = odds_of(n, UPO)
    od[1:] = FLATO                                               # the edge is gone after the entry decision
    r = swing(px, od)
    t = r["trades"].iloc[0]
    assert (t.i_in, t.i_out, t.why_out, t.p_out) == (1, 5, "TIME", 100.0)    # held bars 1-4 (4 bars), out at bar 5's open
    assert len(r["trades"]) == 1 and r["state"]["pos"] == 0
    r = swing(px, odds_of(n, UPO))                               # the edge stays: the trade is renewed, not churned
    assert len(r["trades"]) == 0 and r["state"]["pos"] == 1 and r["state"]["renewals"] >= 2
    od = odds_of(n, UPO)
    od[4] = DNO                                                  # at the due close the other side clears
    r = swing(px, od, hi=7)
    t = r["trades"].iloc[0]
    assert (t.why_out, t.i_out) == ("TIME", 5) and r["state"]["pos"] == -1 and r["held"][5] == -1


def test_re_entry_after_a_target():
    px = flat_bars(12)
    px["high"][3] = 101.6
    r = swing(px, odds_of(12, UPO), hi=9)
    tr = r["trades"]
    assert tr.iloc[0].why_out == "TARGET" and r["state"]["pos"] == 1
    assert r["held"][4] == 1                                     # decided at bar 3's close, in again at bar 4's open
    assert r["state"]["entry"] == 100.0 and r["state"]["t1"] == 101.5


def test_structure_stop_when_a_swing_is_in_reach():
    n = 12
    px = flat_bars(n)
    aux = {"sw_lo": np.full(n, 99.2), "sw_hi": np.full(n, 103.0)}   # long: 99.2 - 0.1 barrier = 99.1, 0.9 away: used
    r = swing(px, odds_of(n, UPO), rule=dict(BARRIER, stop="structure", swing_tf="15m"), aux=aux, hi=2)
    assert r["state"]["stop"] == pytest.approx(99.1) and r["state"]["t1"] == pytest.approx(100 + 1.5 * 0.9)
    r = swing(px, odds_of(n, DNO), rule=dict(BARRIER, stop="structure", swing_tf="15m"), aux=aux, hi=2)
    assert r["state"]["stop"] == pytest.approx(101.0)           # short: 103.1 is 3.1 barriers away: 1 barrier instead
    aux["reach"] = {"1h": np.full(n, 1.2)}                       # a realistic reach of 1.2% = 1.2 price units (1R-3R)
    r = swing(px, odds_of(n, UPO), rule=dict(BARRIER, target="reach"), aux=aux, hi=2)
    assert r["state"]["t1"] == pytest.approx(101.2)


def test_leverage_sizes_the_stop_to_two_percent():
    px = flat_bars(6)
    r = swing(px, odds_of(6, UPO), cfg=dict(CHEAP, leverage_cap=5.0), hi=2)      # 1% stop -> 2x
    assert r["state"]["qty"] * 100.0 / 10000.0 == pytest.approx(2.0)


def random_case(n=1500, seed=3):
    rng = np.random.RandomState(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    o = np.concatenate([[100.0], c[:-1]])
    sp = np.abs(rng.normal(0, 0.002, n)) * c
    px = {"open": o, "high": np.maximum(o, c) + sp, "low": np.minimum(o, c) - sp, "close": c}
    odds = rng.dirichlet(np.ones(3) * 4, size=n)
    odds[:7] = np.nan
    unit = c * 0.004
    guard = rng.rand(n) < 0.03
    aux = {"sw_lo": c * (1 - rng.uniform(0, 0.008, n)), "sw_hi": c * (1 + rng.uniform(0, 0.008, n)),
           "sw_lo_1h": c * (1 - rng.uniform(0, 0.01, n)), "sw_hi_1h": c * (1 + rng.uniform(0, 0.01, n)),
           "reach": {"1h": rng.uniform(0.2, 1.0, n), "4h": rng.uniform(0.4, 2.0, n)}}
    return px, odds, unit, guard, aux


@pytest.mark.parametrize("rule", [dict(intraday.SWING_RULES["1h"]), dict(intraday.SWING_RULES["4h"], target="reach")])
def test_swing_book_never_reads_the_future_and_resumes_exactly(rule):
    px, odds, unit, guard, aux = random_case()
    n = len(odds)
    cfg = dict(CHEAP, cost_side=0.0002, leverage_cap=5.0)
    run = lambda p, od, u, g, ax, lo=0, hi=n, state=None: intraday.run_swing(            # noqa: E731
        p, od, u, cfg, lo, hi, state=state, guard=g, rule=rule, aux=ax, times_ms=np.arange(n, dtype="int64") * 900000)
    whole = run(px, odds, unit, guard, aux)
    assert len(whole["trades"]) > 30
    for k in (400, 1111):
        rng = np.random.RandomState(k)
        p2 = dict((key, v.copy()) for key, v in px.items())
        f = slice(k + 1, None)
        for key in p2:
            p2[key][f] = p2[key][f] * rng.uniform(0.95, 1.05, n - k - 1)
        od2, u2, g2 = odds.copy(), unit.copy(), ~guard
        od2[f] = rng.dirichlet(np.ones(3), size=n - k - 1)
        u2[f] = u2[f] * 2
        ax2 = {"sw_lo": aux["sw_lo"] * 0.99, "sw_hi": aux["sw_hi"] * 1.01, "sw_lo_1h": aux["sw_lo_1h"] * 0.98,
               "sw_hi_1h": aux["sw_hi_1h"] * 1.02, "reach": dict((h, v * 3) for h, v in aux["reach"].items())}
        for key in ("sw_lo", "sw_hi", "sw_lo_1h", "sw_hi_1h"):
            ax2[key][:k + 1] = aux[key][:k + 1]
        for h in ax2["reach"]:
            ax2["reach"][h][:k + 1] = aux["reach"][h][:k + 1]
        cut = run(p2, od2, u2, np.concatenate([guard[:k + 1], g2[k + 1:]]), ax2)
        assert np.array_equal(whole["equity"][:k + 1], cut["equity"][:k + 1])
        assert np.array_equal(whole["held"][:k + 1], cut["held"][:k + 1])
        w, c = whole["trades"], cut["trades"]
        pd.testing.assert_frame_equal(w[w.i_out <= k].reset_index(drop=True), c[c.i_out <= k].reset_index(drop=True))
    for k in (333, 900):                                         # two calls = one long call
        a = run(px, odds, unit, guard, aux, hi=k)
        b = run(px, odds, unit, guard, aux, lo=k, state=json.loads(json.dumps(a["state"])))
        joined = pd.concat([a["trades"], b["trades"]], ignore_index=True)
        cols = [c for c in intraday.TRADE_COLS if c != "i_in"]
        pd.testing.assert_frame_equal(whole["trades"][cols], joined[cols])
        assert np.array_equal(whole["equity"][k:], b["equity"][k:])
        assert whole["state"]["eq"] == b["state"]["eq"]


# ------------------------------------------------------------------ M5 / M6: inside the live step
def live_prep(days=100, seed=2):
    from engine15.evidence import FEATURES
    rng = np.random.RandomState(seed)
    n = days * 96
    times = pd.date_range("2026-08-01", periods=n, freq="15min", tz="UTC")
    prep = {"cfg": dict(CFG, train_floor="2026-08-01", birth="2026-08-01", min_train_rows=60, train_step=8),
            "times": times, "assets": ["BTCUSDT"], "X": {}, "ready": {}, "px": {}, "ev": {}, "y": {}, "odds": {},
            "birth_idx": 0}
    for a in prep["assets"]:
        c = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
        o = np.concatenate([[100.0], c[:-1]])
        sp = np.abs(rng.normal(0, 0.002, n)) * c
        prep["px"][a] = {"open": o, "high": np.maximum(o, c) + sp, "low": np.minimum(o, c) - sp, "close": c}
        prep["X"][a] = rng.normal(0, 1, (n, len(FEATURES))) * (rng.rand(len(FEATURES)) < 0.5)
        prep["ready"][a] = np.ones(n, bool)
        prep["ev"][a] = pd.DataFrame({"atr1h": c * 0.005, "shock": np.zeros(n, bool), "tide": np.zeros(n),
                                      "htf_bias": np.zeros(n), "release_soon": np.zeros(n, bool),
                                      "sw_lo_15m": c * 0.995, "sw_hi_15m": c * 1.005}, index=times)
        prep["y"][a], _ = labels.triple_barrier(o, prep["px"][a]["high"], prep["px"][a]["low"], c * 0.0075, 96)
        prep["odds"][a] = rng.dirichlet(np.ones(3) * 10, size=n)
    return prep


def test_live_minds_cache_skill_and_weekly_report(tmp_path):
    from engine15 import reports
    prep = live_prep()
    cpath, spath = str(tmp_path / "minds.json"), str(tmp_path / "skill.json")
    msgs = []
    one = intraday.live_minds(prep, "crypto", cache_path=cpath, skill_path=spath, log=msgs.append)
    assert any("refit" in m for m in msgs)
    two_msgs = []
    two = intraday.live_minds(prep, "crypto", cache_path=cpath, skill_path=spath, log=two_msgs.append)
    assert not any("refit" in m for m in two_msgs)               # the cached weeks are reused
    for m in intraday.MINDS:
        od1, od2 = one[m]["odds"]["BTCUSDT"], two[m]["odds"]["BTCUSDT"]
        assert np.isfinite(od1[-96:]).all()
        np.testing.assert_allclose(od1, od2, rtol=0, atol=1e-12)
    doc = json.load(open(spath))
    row = doc["groups"]["crypto"]["assets"]["BTCUSDT"]
    assert set(row) == {"1h", "4h", "24h"} and row["1h"]["d30"]["calls"] > row["1h"]["d7"]["calls"] > 0
    out = str(tmp_path / "out")
    assert reports.horizon_skill_weekly(live_path=spath, out_dir=out, log=lambda *_: None)
    assert not reports.horizon_skill_weekly(live_path=spath, out_dir=out, log=lambda *_: None)    # once a week
    assert os.path.exists(os.path.join(out, "horizon_skill.md"))
    blk = reports.horizon_skill_block(live_path=spath)
    assert len(blk["markets"]["BTCUSDT"]["4h"]["d7"]) == 3 and len(json.dumps(blk)) < 2000


def test_swing_challengers_on_the_shadow_scoreboard():
    assert {"m_swing_1h", "m_swing_4h"} <= set(shadows.CHALLENGERS)
    prep = live_prep(days=30)
    n = len(prep["times"])
    lo = n - 96 * 5
    flat = shadows.run_challenger("m_swing_1h", prep, "BTCUSDT", lo, n)          # no odds: it stays flat
    assert len(flat["trades"]) == 0 and flat["state"]["pos"] == 0
    od = np.tile([0.1, 0.8, 0.1], (n, 1))
    sw = {"1h": {"odds": {"BTCUSDT": od}}, "4h": {"odds": {"BTCUSDT": od}}}
    b = shadows.run_challenger("m_swing_1h", prep, "BTCUSDT", lo, n, swing=sw)
    assert len(b["trades"]) > 3 and set(b["trades"].why_out) <= {"STOP", "TARGET", "TIME"}
    v = shadows.asset_view(b["state"])
    assert v["trades"] == len(b["trades"]) and v["status"] in ("LONG", "SHORT", "FLAT")
