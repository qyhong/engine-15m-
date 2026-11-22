# -*- coding: utf-8 -*-
"""The pure logic of the queue family H90-H106 (research/queue/walkforward.py, research/queue/pattern.py).

    py -3 -m pytest tests/test_queue_walkforward.py -q
"""
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))
sys.path.insert(0, os.path.join(ROOT, "research", "queue"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import pattern as pt  # noqa: E402
import walkforward as wf  # noqa: E402
from engine15 import shadows  # noqa: E402
from engine15.config import CFG  # noqa: E402
from test_shadows import random_inputs  # noqa: E402

BAR = 900000


def _series(n=200 * 96, seed=1, start="2021-01-01"):
    rng = np.random.RandomState(seed)
    t0 = pd.Timestamp(start, tz="UTC").value // 10 ** 6
    close_ms = t0 + BAR * (1 + np.arange(n, dtype="int64"))
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    unit = close * np.abs(rng.normal(0.01, 0.003, n))
    return close_ms, close, unit


# ------------------------------------------------------------------ the masks read no future bar
@pytest.mark.parametrize("spec", [{"kind": "tight_stop", "q": 0.33}, {"kind": "vol", "third": "top"},
                                  {"kind": "vol", "third": "bottom"}, {"kind": "hours", "h0": 6, "h1": 12},
                                  {"kind": "weekend", "mode": "sat_sun"}, {"kind": "weekend", "mode": "fri21_sun21"}])
def test_masks_use_no_future_bar(spec):
    close_ms, close, unit = _series()
    full = wf.build_mask([spec], "BTCUSDT", close_ms, close, unit)
    for cut in (40 * 96 + 7, 95 * 96 + 50, 150 * 96):
        part = wf.build_mask([spec], "BTCUSDT", close_ms[:cut], close[:cut], unit[:cut])
        assert np.array_equal(full[:cut], part)
    # changing the future does not change the past
    c2, u2 = close.copy(), unit.copy()
    c2[120 * 96:] *= 3.0
    u2[120 * 96:] *= 0.1
    alt = wf.build_mask([spec], "BTCUSDT", close_ms, c2, u2)
    assert np.array_equal(full[:120 * 96], alt[:120 * 96])


def test_masks_need_thirty_days_and_block_what_they_say():
    close_ms, close, unit = _series()
    m = wf.build_mask([{"kind": "tight_stop", "q": 0.5}], "BTCUSDT", close_ms, close, unit)
    assert not m[:30 * 96 - 1].any()                              # under 30 days of history: no block
    assert 0.3 < m[60 * 96:].mean() < 0.7
    ts = pd.to_datetime(close_ms, unit="ms", utc=True)
    w = wf.build_mask([{"kind": "weekend", "mode": "sat_sun"}], "BTCUSDT", close_ms, close, unit)
    assert np.array_equal(w, np.asarray(ts.weekday) >= 5)
    assert wf.build_mask([{"kind": "weekend", "mode": "sat_sun"}], "XAUUSD", close_ms, close, unit).sum() == 0
    h = wf.build_mask([{"kind": "hours", "h0": 18, "h1": 24}], "SPX", close_ms, close, unit)
    assert np.array_equal(h, np.asarray(ts.hour) >= 18)


def test_guard_mask_blocks_entries_and_flips_but_keeps_open_positions():
    px, odds, unit, shock, tide, bias, guard, aux = random_inputs(n=900, seed=5)
    n = len(px["close"])
    cfg = shadows.asset_cfg("XAUUSD", dict(CFG))                 # not an early-entry market: fills at the next open
    tms = np.arange(n, dtype="int64") * BAR
    rule = dict(shadows.CHALLENGERS["b_targets"]["rule"])
    run = lambda g: shadows.run(px, odds, shock, tide, unit, cfg, 1, n, bias=bias, guard=g, rule=rule, aux=aux,  # noqa
                                times_ms=tms, row_of=lambda k: aux["targets"].iloc[k])
    assert wf.merge_guard(guard, None, n) is guard               # no mask: the very same guard array
    k = 500
    m = np.zeros(n, bool)
    m[k:] = True
    b0, b1 = run(guard), run(wf.merge_guard(guard, m, n))
    t1 = b1["trades"]
    assert (t1.i_in <= k).all()                                  # nothing opened from a decision at or after bar k
    assert np.array_equal(b0["held"][:k], b1["held"][:k])        # identical before the mask
    if b1["held"][k] != 0:                                       # a position open at k is kept until its stop/target
        assert (t1.i_out >= k).any() or b1["state"]["pos"] != 0
    assert not t1.why_in.astype(str).str.contains("FLIP").loc[t1.i_in > k].any()


# ------------------------------------------------------------------ the holdout wall
def test_wall_refuses_the_holdout():
    wf.wall("2025-11-10 23:45")
    with pytest.raises(wf.HoldoutError):
        wf.wall("2025-11-11 00:00")
    with pytest.raises(pt.HoldoutError):
        pt.wall("2025-11-11")
    idx = pd.date_range("2025-11-09", "2025-11-12", freq="15min", tz="UTC")
    df = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": np.arange(len(idx), dtype=float)}, index=idx)
    d = pt.daily_from_15m(df)
    assert str(d.index[-1])[:10] == "2025-11-10" and d["bars"].iloc[-1] == 96
    with pytest.raises(pt.HoldoutError):
        pt.daily_from_15m(df, end="2025-11-12")


# ------------------------------------------------------------------ the choice rule and the statistic
def test_choice_rule():
    order = ["a", "cur", "b", "c"]
    pooled = {"a": 50.0, "cur": 10.0, "b": 40.0, "c": 60.0}
    vault = {"a": -1.0, "cur": 0.0, "b": 0.0, "c": -0.5}
    assert wf.choose(order, "cur", pooled, vault) == "b"          # a and c fail the BTC+ETH condition
    assert wf.choose(order, "cur", dict(pooled, b=10.0), vault) == "cur"   # tie with the current: the current
    assert wf.choose(order, "cur", dict(pooled, b=5.0), vault) == "cur"


def _rec(trades, eq=None):
    r = {"trades": [[int(pd.Timestamp(d, tz="UTC").value // 10 ** 6), None, 1, r_, 0.0, "ENTER", "STOP"] for d, r_ in trades],
         "bars": 100, "flat_bars": 10, "net": 0.0}
    if eq is not None:
        r["eq_ms"], r["eq"] = eq
    return r


def test_paired_monthly_statistic_on_planted_numbers():
    months = wf.month_keys("2024-01-01", "2024-12-31")
    assert len(months) == 12 and months[0] == "2024-01"
    cur = {"BTCUSDT": _rec([("2024-01-05", 1.0), ("2024-03-02", -1.0)]), "XAUUSD": _rec([("2024-02-10", 0.5)])}
    cho = {"BTCUSDT": _rec([("2024-01-05", 2.0), ("2024-03-02", 0.0)]), "XAUUSD": _rec([("2024-02-10", 1.5)])}
    v = wf.verdict_stats(cur, cho, months, ["BTCUSDT", "XAUUSD"])
    assert v["monthly_diff"] == [1.0, 1.0, 1.0] + [0.0] * 9
    assert v["boot"]["mean"] == pytest.approx(0.25)
    assert v["vault_diff"] == pytest.approx(2.0)
    assert 0 < v["boot"]["p_one_sided"] < 0.05                   # never zero: (1 + #) / (draws + 1)
    assert v["mean_r"]["current"]["mean_r"] == pytest.approx(0.5 / 3)
    # a pooled gain with a BTC+ETH loss does not pass
    cho2 = {"BTCUSDT": _rec([("2024-01-05", 0.5), ("2024-03-02", -1.0)]), "XAUUSD": _rec([("2024-02-10", 50.0)])}
    v2 = wf.verdict_stats(cur, cho2, months, ["BTCUSDT", "XAUUSD"])
    assert v2["vault_diff"] < 0 and not v2["passed"] and v2["conclusion"] == "does not"
    b = wf.boot_mean(np.array([1.0, -1.0] * 15))
    assert 0.3 < b["p_one_sided"] < 0.7


def test_worst_fall_pools_the_books():
    ms = [0, BAR, 2 * BAR]
    a = _rec([], eq=(ms, [10000.0, 12000.0, 9000.0]))
    b = _rec([], eq=(ms, [10000.0, 10000.0, 10000.0]))
    assert wf.worst_fall_pooled([a, b]) == pytest.approx((19000 / 22000 - 1) * 100)


def test_canonical_specs():
    c0, k0 = wf.canonical(wf.S(), "BTCUSDT")
    assert wf.canonical(wf.S({"stop_units": 2.0}), "BTCUSDT")[1] == k0          # the current value is the current book
    assert wf.canonical(wf.S({"stop_units": 1.5}), "BTCUSDT")[1] != k0
    wk = wf.S(mask=[{"kind": "weekend", "mode": "sat_sun"}])
    assert wf.canonical(wk, "XAUUSD")[1] == wf.canonical(wf.S(), "XAUUSD")[1]   # weekend filter: BTC and ETH only
    assert wf.canonical(wk, "ETHUSDT")[1] != wf.canonical(wf.S(), "ETHUSDT")[1]
    for sid, st in wf.STUDIES.items():
        if st["grid"]:
            labs = [k for k, _s in st["grid"]]
            assert st["current"] in labs and len(set(labs)) == len(labs)
            assert wf.canonical(dict(st["grid"])[st["current"]], "BTCUSDT")[1] == k0, sid


# ------------------------------------------------------------------ the order: choice before test, no peeking, resume
def _fake_world(monkeypatch, out, calls, fail_after=None):
    times = pd.date_range("2020-01-01", "2020-04-20 23:45", freq="15min", tz="UTC")

    def load_prep(g, assets, fits_root, limit, out_, log=print):
        lim = wf.wall(limit)
        if lim > pd.Timestamp("2020-03-31 23:45", tz="UTC"):
            assert os.path.exists(os.path.join(out, "choice.json")), "test period loaded before the choice was written"
        calls.append(("load", str(lim)))
        t = times[times <= lim]
        n = len(t)
        odds = np.full((n, 3), 0.33)
        return {"times": t, "cfg": dict(CFG), "odds": dict((a, odds) for a in assets), "birth_idx": 10,
                "ev": dict((a, None) for a in assets), "px": dict((a, {"close": np.ones(n)}) for a in assets)}

    def run_book(prep, a, spec, lo, hi, aux):
        if fail_after is not None and len([c for c in calls if c[0] == "run"]) >= fail_after:
            raise KeyboardInterrupt("planted crash")
        calls.append(("run", a, json.dumps(spec, sort_keys=True), str(prep["times"][lo])[:10]))
        n = len(prep["times"])
        su = spec["cfg"].get("stop_units", 2.0)
        i = np.arange(lo, hi - 5, 300)
        tr = pd.DataFrame({"t_in_ms": [int(prep["times"][k].value // 10 ** 6) for k in i], "t_out_ms": 0, "i_in": i,
                           "side": 1, "r_mult": [0.25 - 0.1 * su] * len(i), "pnl_usd": 1.0, "why_in": "ENTER",
                           "why_out": "STOP"})
        return {"trades": tr, "equity": np.full(n, 10000.0), "held": np.zeros(n, np.int8), "state": {}}

    monkeypatch.setattr(wf, "load_prep", load_prep)
    monkeypatch.setattr(wf, "run_book", run_book)
    monkeypatch.setattr(wf.shadows, "aux_from_ev", lambda ev, px: {"targets": pd.DataFrame()})
    monkeypatch.setattr(wf.shadows, "run_challenger", lambda name, prep, a, lo, n, aux=None: run_book(prep, a, wf.S(), lo, n, aux))


def test_choice_file_comes_first_and_unchosen_values_cannot_be_computed_on_test(monkeypatch, tmp_path):
    out = str(tmp_path / "H90")
    calls = []
    _fake_world(monkeypatch, out, calls)
    ctx = wf.Ctx("H90", out, "nofits", smoke=True, log=lambda *a: None)
    with pytest.raises(wf.PeekError):
        wf.allowed_test_labels(ctx)                               # no choice.json: nothing on test
    res = wf.run_study(ctx)
    ch = json.load(open(os.path.join(out, "choice.json")))
    assert ch["chosen"] != ch["current"]                          # smoke grid: stop_units 1.0 vs 2.0; the planted R favours ...
    assert res["conclusion"] in ("beats the current setting on later data", "does not")
    assert os.path.exists(os.path.join(out, "DONE")) and os.path.exists(os.path.join(out, "report.md"))
    # every choice-period run happened before every test-period load
    first_test = next(i for i, c in enumerate(calls) if c[0] == "load" and c[1] > "2020-03-31 23:45:00+00:00")
    assert all(not (c[0] == "run" and c[3] >= "2020-04-01") for c in calls[:first_test])
    assert all(c[1] <= "2020-04-20 23:45:00+00:00" for c in calls if c[0] == "load")
    # the gate: with choice.json but no verdict.json only the current and chosen values may run on test
    os.remove(os.path.join(out, "verdict.json"))
    ok = wf.allowed_test_labels(ctx)
    assert ok == {ch["current"], ch["chosen"]}
    gate = wf.test_gate(ctx)
    with pytest.raises(wf.PeekError):
        gate("stop_units=4")


def test_current_choice_ends_the_study_without_test_numbers(monkeypatch, tmp_path):
    out = str(tmp_path / "H92")
    calls = []
    _fake_world(monkeypatch, out, calls)
    ctx = wf.Ctx("H92", out, "nofits", smoke=True, log=lambda *a: None)
    res = wf.run_study(ctx)                                       # theta_enter does not move the planted R: a tie
    assert res["conclusion"] == "the current setting was already the choice"
    assert not any(c[0] == "load" and c[1] > "2020-03-31 23:45:00+00:00" for c in calls)
    assert not os.path.exists(os.path.join(out, "verdict.json"))


def test_resume_continues_where_it_stopped(monkeypatch, tmp_path):
    out = str(tmp_path / "H90")
    calls = []
    _fake_world(monkeypatch, out, calls, fail_after=3)
    with pytest.raises(KeyboardInterrupt):
        wf.run_study(wf.Ctx("H90", out, "nofits", smoke=True, log=lambda *a: None))
    first = [c for c in calls if c[0] == "run"]
    assert len(first) == 3 and json.load(open(os.path.join(out, "progress.json")))["done"] >= 2
    calls2 = []
    _fake_world(monkeypatch, out, calls2)
    wf.run_study(wf.Ctx("H90", out, "nofits", smoke=True, log=lambda *a: None))
    again = [c for c in calls2 if c[0] == "run"]
    done_keys = set((c[1], c[2], c[3]) for c in first)
    assert not any((c[1], c[2], c[3]) in done_keys for c in again)   # nothing finished is run twice
    assert os.path.exists(os.path.join(out, "DONE"))
    pr = json.load(open(os.path.join(out, "progress.json")))
    assert pr["done"] == pr["total"] and set(pr) >= {"done", "total", "started_utc", "updated_utc", "est_hours_left"}


def test_kitchen_sink_waits_for_its_siblings(tmp_path):
    out = str(tmp_path / "H101")
    os.makedirs(out)
    ctx = wf.Ctx("H101", out, "nofits", smoke=False, log=lambda *a: None)
    with pytest.raises(wf.NotReady):
        wf.study_grid(ctx)
    for sid in wf.FAMILY:
        d = tmp_path / sid
        d.mkdir()
        st = wf.STUDIES[sid]
        chosen = {"H90": "stop_units=3", "H97": "block_00-06"}.get(sid, st["current"])
        (d / "choice.json").write_text(json.dumps({"current": st["current"], "chosen": chosen, "specs": dict(st["grid"])}))
    grid, cur = wf.study_grid(ctx)
    assert grid[1][1] == wf.S({"stop_units": 3.0}, [{"kind": "hours", "h0": 0, "h1": 6}])


def test_estimate_prints_one_number(capsys):
    assert wf.main(["--study", "H90", "--estimate"]) == 0
    assert float(capsys.readouterr().out.strip()) > 0


# ------------------------------------------------------------------ the pattern events on planted bars
def test_ema_rsi_seeding():
    c = np.arange(1, 31, dtype=float)
    e = pt.ema(c, 10)
    assert np.isnan(e[8]) and e[9] == pytest.approx(5.5)
    assert e[10] == pytest.approx(2 / 11 * 11 + 9 / 11 * 5.5)
    r = pt.rsi(np.arange(1, 40, dtype=float))
    assert np.isnan(r[13]) and r[14] == pytest.approx(100.0)


def test_golden_and_death_cross_events():
    c = np.concatenate([np.linspace(200, 100, 300), np.linspace(100, 300, 300), np.linspace(300, 100, 300)])
    g = pt.events_for("golden_cross_long", c)
    d = pt.events_for("death_cross_short", c)
    e50, e200 = pt.ema(c, 50), pt.ema(c, 200)
    for t in g:
        assert e50[t] > e200[t] and e50[t - 1] <= e200[t - 1]
    for t in d:
        assert e50[t] < e200[t] and e50[t - 1] >= e200[t - 1]
    assert len(g) == 1 and len(d) >= 1 and g[0] < max(d)
    assert pt.events_for("golden_cross_long", c[:g[0] + 1]) == g   # known at its own close


def test_three_down_one_event_per_streak():
    c = np.array([100, 101, 97, 93, 89, 85, 80, 82, 78, 74, 70, 71], dtype=float)
    # 101 -> 97 -> 93 -> 89: -11.9% at index 4; the streak goes on to 80 (no new event); after 82: 78, 74, 70: -14.6% at 10
    assert pt.events_for("three_down_10pct_long", c) == [4, 10]
    assert pt.events_for("three_down_10pct_long", np.array([100, 99, 98, 97, 96.0])) == []


def test_rsi_reclaim_and_ema200_reclaim():
    c = np.concatenate([np.linspace(100, 120, 60), np.linspace(120, 80, 20), np.linspace(80, 95, 20)])
    r = pt.rsi(c)
    for t in pt.events_for("rsi30_reclaim_long", c):
        assert r[t - 1] <= 30 < r[t]
    c2 = np.concatenate([np.full(220, 100.0), np.linspace(100, 60, 40), np.linspace(60, 140, 60)])
    ev = pt.events_for("ema200_reclaim_after_30d_long", c2)
    e200 = pt.ema(c2, 200)
    assert len(ev) == 1
    t = ev[0]
    assert c2[t] > e200[t] and all(c2[t - k] < e200[t - k] for k in range(1, 31))


def test_mirror_of_h74_short_event():
    base = np.full(260, 100.0)
    down = np.linspace(100, 80, 30)                               # below the EMA200: the 60-day low is 80
    up = np.linspace(80, 125, 25)                                 # back above it and over 20% above 80
    fall = np.linspace(125, 110, 10)                              # the first close under the EMA10
    c = np.concatenate([base, down, up, fall, np.full(30, 110.0)])
    ev = pt.events_for("ema200_rise_ema10_break_short", c)
    e10 = pt.ema(c, 10)
    assert len(ev) == 1
    t = ev[0]
    assert c[t] < e10[t] and c[t - 1] >= e10[t - 1]
    assert pt.outcome(c, e10, t, -1, "W5") is True                # short: the close five days on is lower


def test_outcomes_and_tests():
    c = np.array([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 9, 9, 9], dtype=float)
    e10 = np.full(len(c), 12.0)
    assert pt.outcome(c, e10, 0, 1, "W5") is True and pt.outcome(c, e10, 0, -1, "W10") is False
    assert pt.outcome(c, e10, 5, 1, "W10") is None                # past the data
    assert pt.outcome(c, e10, 3, 1, "WEMA10") is False            # exit at 9 (first close below 12)
    assert pt.outcome(c, e10, 4, 1, "W5") is True
    lo, hi = pt.wilson(8, 22)
    assert lo == pytest.approx(0.197, abs=0.002) and hi == pytest.approx(0.570, abs=0.002)   # H74's 8/22
    assert pt.binom_p_upper(0, 10, 0.5) == pytest.approx(1.0)
    assert pt.binom_p_upper(10, 10, 0.5) == pytest.approx(0.5 ** 10)
    lab, _o = pt.clusters([(0, "BTCUSDT"), (5 * 86400000, "ETHUSDT"), (30 * 86400000, "BTCUSDT"), (39 * 86400000, "ETHUSDT")])
    assert lab == [0, 0, 1, 1]
    evs = [{"day_ms": i * 40 * 86400000, "coin": "BTCUSDT", "win": True} for i in range(40)]
    a = pt.analyse(evs, [("2020-%02d" % (1 + i % 12), i % 2 == 0) for i in range(400)], 0.55, draws=500)
    assert a["episodes"] == 40 and a["conclusion"] == "supported"
    a2 = pt.analyse([dict(e, win=False) for e in evs], [("2020-01", True)] * 10, 0.55, draws=200)
    assert a2["conclusion"] == "not supported"
