# -*- coding: utf-8 -*-
"""The pure logic of the queue family H80-H89 (research/queue/placebo.py): the scramblers keep what they must keep and
break what they must break, the research-side loop copy and the trade replay are the engine's book (the gates), a
draw is reproducible on its own, and resuming never repeats or double-counts a draw.

    py -3 -m pytest tests/test_queue_placebo.py -q
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

import placebo as P  # noqa: E402
from engine15 import shadows  # noqa: E402
from engine15.config import CFG  # noqa: E402
from test_shadows import random_inputs  # noqa: E402

BAR = 900000
DAY = 86400000


# ------------------------------------------------------------------ the holdout
def test_the_cut_is_before_the_holdout_and_later_cuts_are_refused():
    assert P.CUT == "2025-11-10 23:45" and P.SMOKE_CUT <= P.CUT
    with pytest.raises(RuntimeError):
        P.group_end("crypto", ["BTCUSDT"], "2025-11-11 00:00")


# ------------------------------------------------------------------ time shift (H80, H83, H85)
def _grid(days, gaps=False):
    t = np.arange(0, days * DAY, BAR, dtype="int64")
    if gaps:                                                     # drop weekends (like a market that shuts)
        dow = (t // DAY) % 7
        t = t[dow < 5]
    return t


@pytest.mark.parametrize("gaps", [False, True])
@pytest.mark.parametrize("u", [0.0, 0.37, 0.999])
def test_shift_moves_every_row_at_least_the_minimum_both_ways(gaps, u):
    t = _grid(400, gaps)
    lo, hi = 5, len(t)
    src = P.shift_src(t, lo, hi, u, 30)
    W = int(t[hi - 1] - t[lo]) + BAR
    d = (t[lo:hi] - t[src]) % W                                  # how far back, round the circle
    assert d.min() >= 30 * DAY and (W - d).min() >= 30 * DAY
    assert src.min() >= lo and src.max() < hi


def test_shift_on_a_regular_grid_is_a_permutation_and_keeps_the_series_behaviour():
    t = _grid(300)
    lo, hi = 3, len(t)
    src = P.shift_src(t, lo, hi, 0.5, 30)
    assert sorted(src.tolist()) == list(range(lo, hi))           # nothing lost, nothing doubled
    rng = np.random.default_rng(0)
    x = np.zeros(len(t))
    e = rng.normal(size=len(t))
    for i in range(1, len(t)):                                   # an AR(1) series: persistent like odds or a trend
        x[i] = 0.98 * x[i - 1] + e[i]
    y = P.apply_src(x, src, lo, hi)
    assert np.array_equal(y[:lo], x[:lo])                        # rows before lo untouched
    assert np.allclose(np.sort(y[lo:hi]), np.sort(x[lo:hi]))     # same values

    def ac1(z):
        return np.corrcoef(z[:-1], z[1:])[0, 1]
    assert abs(ac1(y[lo:hi]) - ac1(x[lo:hi])) < 0.005           # its own behaviour kept (one seam only)
    assert abs(np.corrcoef(x[lo:hi], y[lo:hi])[0, 1]) < 0.2     # its link to the moment broken


def test_shift_offset_is_common_for_equal_windows_and_differs_between_draws():
    t = _grid(200)
    a = P.shift_src(t, 1, len(t), 0.2, 30)
    b = P.shift_src(t, 1, len(t), 0.2, 30)
    c = P.shift_src(t, 1, len(t), 0.7, 30)
    assert np.array_equal(a, b) and not np.array_equal(a, c)


def test_shift_refuses_a_window_too_short():
    with pytest.raises(ValueError):
        P.shift_src(_grid(50), 0, len(_grid(50)), 0.5, 30)


# ------------------------------------------------------------------ month shuffle (H86) and permutations (H81)
def test_month_shuffle_keeps_rows_in_their_month_and_is_a_permutation():
    times = pd.date_range("2021-01-01", periods=96 * 120, freq="15min", tz="UTC")
    month = np.asarray(times.year * 12 + times.month - 1)
    lo, hi = 10, len(times)
    src = P.month_shuffle_src(month, lo, hi, np.random.default_rng(1))
    assert sorted(src.tolist()) == list(range(lo, hi))
    assert np.array_equal(month[src], month[lo:hi])
    assert (src != np.arange(lo, hi)).mean() > 0.99               # order broken
    unit = np.random.default_rng(2).lognormal(size=len(times))
    u2 = P.apply_src(unit, src, lo, hi)
    for m in np.unique(month[lo:hi]):                            # each month keeps its own values (typical size)
        sel = month[lo:hi] == m
        assert np.allclose(np.sort(u2[lo:hi][sel]), np.sort(unit[lo:hi][sel]))


def test_permute_within_keeps_each_groups_long_short_share():
    rng = np.random.default_rng(5)
    groups = rng.integers(0, 40, 3000)
    side = rng.choice([-1, 1], 3000)
    src = P.permute_within(groups, np.random.default_rng(9))
    assert sorted(src.tolist()) == list(range(3000))
    assert np.array_equal(groups[src], groups)
    for g in np.unique(groups):
        assert side[src][groups == g].sum() == side[groups == g].sum()
    assert (side[src] != side).mean() > 0.3


def test_a_draw_is_reproducible_on_its_own():
    a = P.draw_rng(P.STUDIES["H80"]["seed"], 17, 3).random(5)
    _ = [P.draw_rng(P.STUDIES["H80"]["seed"], k, 3).random(5) for k in range(17)]
    b = P.draw_rng(P.STUDIES["H80"]["seed"], 17, 3).random(5)
    c = P.draw_rng(P.STUDIES["H80"]["seed"], 18, 3).random(5)
    assert np.array_equal(a, b) and not np.array_equal(a, c)
    assert len(set(s["seed"] for s in P.STUDIES.values())) == len(P.STUDIES)


# ------------------------------------------------------------------ the gates on random bars
def _ctx(inp, asset):
    px, odds, unit, shock, tide, bias, guard, aux = inp
    n = len(px["close"])
    cfg = shadows.asset_cfg(asset, dict(CFG))
    tgt = aux["targets"]
    tarr = dict((c, np.asarray(tgt[c].values, dtype=float)) for c in tgt.columns)
    times = pd.date_range("2022-01-01", periods=n, freq="15min", tz="UTC")
    return {"a": asset, "lo": 1, "n": n, "mid": n // 2, "aux": aux, "cfg": cfg,
            "inp": {"px": px, "odds": odds, "shock": shock, "tide": tide, "unit": unit, "bias": bias, "guard": guard},
            "tms": np.arange(n, dtype="int64") * BAR, "month": np.asarray(times.year * 12 + times.month - 1),
            "row_of": lambda k: tgt.iloc[k], "trow": lambda k: dict((c, v[k]) for c, v in tarr.items())}


@pytest.mark.parametrize("asset", ["BTCUSDT", "XAUUSD", "SPX"])   # early entry / a fill delay / neither
@pytest.mark.parametrize("seed", [3, 11, 17])
@pytest.mark.parametrize("rule", [P.RULE_CURRENT, P.RULE_WAIT, P.RULE_TREND])
def test_the_loop_copy_is_the_engines_book(asset, seed, rule):
    inp = random_inputs(n=4000 if rule.get("trend_days") else 1500, seed=seed)   # the filter needs 30 days of bars
    ctx = _ctx(inp, asset)
    ref = P.run_book(ctx, rule)
    mine = P.copy_book(ctx, rule)
    ok, why = P.same_book(ref, mine, ctx["lo"], ctx["n"])
    assert ok, why
    assert len(ref["trades"]) > 30
    if rule.get("wait_after_stop"):
        assert mine["wait"] == dict(ref["state"]["wait_stop"]) and mine["wait"]["episodes"] > 0


def test_a_random_trigger_changes_the_wait_book():
    inp = random_inputs(n=1500, seed=11)
    ctx = _ctx(inp, "BTCUSDT")
    real = P.copy_book(ctx, P.RULE_WAIT)
    always = P.copy_book(ctx, P.RULE_WAIT, trigger=lambda w: True)
    never = P.copy_book(ctx, P.RULE_WAIT, trigger=lambda w: False)
    cur = P.run_book(ctx, P.RULE_CURRENT)
    assert always["wait"]["episodes"] > real["wait"]["episodes"]
    ok, _ = P.same_book(cur, never, ctx["lo"], ctx["n"])          # a trigger that never fires is the current rule
    assert ok


@pytest.mark.parametrize("asset", ["BTCUSDT", "XAUUSD", "SPX"])
@pytest.mark.parametrize("seed", [3, 11])
def test_the_trade_replay_gives_every_real_trade(asset, seed):
    inp = random_inputs(n=1500, seed=seed)
    ctx = _ctx(inp, asset)
    book = P.run_book(ctx, P.RULE_CURRENT)
    ok, bad = P.replay_gate(ctx, book["trades"])
    assert ok and bad == 0
    s = P.real_slots(book["trades"])
    assert s["open_exit"].any() and (~s["open_exit"]).any()     # both kinds of end were met


def test_the_replay_gate_catches_a_wrong_trade():
    inp = random_inputs(n=1500, seed=3)
    ctx = _ctx(inp, "BTCUSDT")
    tr = P.run_book(ctx, P.RULE_CURRENT)["trades"].copy()
    tr.loc[tr.index[5], "r_mult"] += 0.01
    ok, bad = P.replay_gate(ctx, tr)
    assert not ok and bad == 1


def test_the_other_side_is_a_real_other_trade():
    inp = random_inputs(n=1500, seed=3)
    ctx = _ctx(inp, "SPX")
    tr = P.run_book(ctx, P.RULE_CURRENT)["trades"]
    s = P.real_slots(tr)
    px, unit = ctx["inp"]["px"], ctx["inp"]["unit"]
    other = [P.replay_trade(-s["side"][j], s["i_in"][j], s["p_in"][j], s["i_in"][j] - 1, s["i_out"][j], s["open_exit"][j],
                            px, unit, ctx["cfg"], ctx["trow"])[0] for j in range(len(tr))]
    assert np.isfinite(other).all() and np.corrcoef(other, s["r"])[0, 1] < 0


def test_h82_draw_keeps_counts_and_months():
    inp = random_inputs(n=3000, seed=17)
    ctx = _ctx(inp, "SPX")
    book = P.run_book(ctx, P.RULE_CURRENT)
    ctx["slots"] = P.real_slots(book["trades"])
    rows = np.arange(ctx["lo"] + 1, ctx["n"] - 1)
    ctx["valid_by_month"] = dict((int(m), rows[ctx["month"][rows] == m]) for m in np.unique(ctx["month"][rows]))
    a = P.trade_draw("H82", {"SPX": ctx}, 4, 0)["SPX"]["s"]
    b = P.trade_draw("H82", {"SPX": ctx}, 4, 0)["SPX"]["s"]
    c = P.trade_draw("H82", {"SPX": ctx}, 5, 0)["SPX"]["s"]
    assert a == b and a != c
    assert a[0] == int(np.isfinite(ctx["slots"]["r"]).sum())     # every real trade placed once


# ------------------------------------------------------------------ checkpoints: resuming never repeats a draw
def test_a_torn_last_line_is_dropped(tmp_path):
    p = str(tmp_path / "d.jsonl")
    P.append_line(p, {"k": 0})
    P.append_line(p, {"k": 1})
    with open(p, "a") as fh:
        fh.write('{"k": 2, "m": {')
    assert [r["k"] for r in P.read_lines(p)] == [0, 1]
    P.append_line(p, {"k": 2})
    assert [r["k"] for r in P.read_lines(p)] == [0, 1, 2]


def test_resume_never_repeats_or_double_counts(tmp_path, monkeypatch):
    calls = []

    class Stop(Exception):
        pass

    def fake_load(g, assets, fits, out, cut):
        times = pd.date_range("2021-01-01", periods=10, freq="15min", tz="UTC")
        return {"times": times, "_load_s": 0.0}

    monkeypatch.setattr(P, "load_group", fake_load)
    monkeypatch.setattr(P, "market_ctx", lambda prep, a: {"lo": 1, "n": 10})
    monkeypatch.setattr(P, "real_books_for", lambda study, ctxs, gl, prep=None: dict(
        (a, {"current": [1] * P.NSTAT, "real": [1] * P.NSTAT}) for a in ctxs))
    limit = {"n": 5}

    def fake_draw(study, ctxs, k, gi):
        if len(calls) >= limit["n"]:
            raise Stop()
        calls.append((gi, k))
        return dict((a, {"s": [k] * P.NSTAT}) for a in ctxs)

    monkeypatch.setattr(P, "book_draw", fake_draw)
    monkeypatch.setattr(P, "BATCH", 1)                                  # every draw its own checkpoint line
    groups = [("index", ["SPX"]), ("fx", ["USDJPY"])]
    args = type("A", (), {"fits_dir": str(tmp_path)})()
    out = str(tmp_path / "out")
    os.makedirs(out)
    with pytest.raises(Stop):
        P.run_draw_study("H80", args, out, groups, P.CUT, 4)
    limit["n"] = 100
    fp = P.run_draw_study("H80", args, out, groups, P.CUT, 4)
    assert sorted(calls) == sorted(set(calls)) and len(calls) == 8      # each (group, draw) computed exactly once
    for g, _a in groups:
        ks = [k for r in P.read_lines(os.path.join(out, "draws_%s.jsonl" % g)) for k in r["ks"]]
        assert sorted(ks) == [0, 1, 2, 3]                               # each draw recorded once
    reals, D, ex, meta = P.collect(out, groups, fp, 4)
    assert np.array_equal(D[:, P.MARKETS.index("SPX"), 0], [0, 1, 2, 3])
    pr = json.load(open(os.path.join(out, "progress.json")))
    assert pr["done"] == 8 and pr["total"] == 8 and set(pr) >= {"done", "total", "started_utc", "updated_utc", "est_hours_left"}
    n_before = len(calls)
    P.run_draw_study("H80", args, out, groups, P.CUT, 4)               # a third run does nothing
    assert len(calls) == n_before


def test_draws_from_another_configuration_are_not_counted(tmp_path):
    out = str(tmp_path)
    P.append_line(os.path.join(out, "draws_index.jsonl"), {"fp": "other", "ks": [0], "m": [{"SPX": {"s": [9] * P.NSTAT}}]})
    P.write_json(os.path.join(out, "real_index.json"), {"real": {}, "end": "", "gate": {}, "windows": {}})
    _r, D, _e, _m = P.collect(out, [("index", ["SPX"])], P.fingerprint("H80", 2, P.CUT), 2)
    assert np.isnan(D).all()


# ------------------------------------------------------------------ p-values
def test_p_value_counts_ties_as_at_least_as_good_and_is_plus_one_corrected():
    d = np.array([0.1, 0.2, 0.3, np.nan])
    p = P.pvals(0.2, d)
    assert p["p_upper"] == pytest.approx((1 + 2) / 5) and p["p_lower"] == pytest.approx((1 + 2) / 5)
    assert P.pvals(9.0, d)["p_upper"] == pytest.approx(1 / 5)


def test_estimates_cover_the_family():
    hours = dict((s, P.estimate_hours(s)) for s in P.STUDIES)
    assert sum(hours.values()) >= 60
    for s in ("H80", "H82", "H83", "H84", "H85", "H86"):
        assert 8 <= hours[s] <= 16, (s, hours[s])


def test_a_kill_inside_a_batch_records_each_draw_once(tmp_path, monkeypatch):
    """With several draws per line, a kill loses only the unwritten batch: those draws are computed again on the
    resume, and every draw is still recorded (and counted) exactly once."""
    monkeypatch.setattr(P, "load_group", lambda g, assets, fits, out, cut: {
        "times": pd.date_range("2021-01-01", periods=10, freq="15min", tz="UTC"), "_load_s": 0.0})
    monkeypatch.setattr(P, "market_ctx", lambda prep, a: {"lo": 1, "n": 10})
    monkeypatch.setattr(P, "real_books_for", lambda study, ctxs, gl, prep=None: dict(
        (a, {"current": [1] * P.NSTAT, "real": [1] * P.NSTAT}) for a in ctxs))
    monkeypatch.setattr(P, "BATCH", 3)
    state = {"n": 0, "stop_at": 7}

    def fake_draw(study, ctxs, k, gi):
        if state["n"] == state["stop_at"]:
            raise KeyboardInterrupt()
        state["n"] += 1
        return dict((a, {"s": [k] * P.NSTAT}) for a in ctxs)
    monkeypatch.setattr(P, "book_draw", fake_draw)
    args = type("A", (), {"fits_dir": str(tmp_path)})()
    out = str(tmp_path / "o")
    os.makedirs(out)
    with pytest.raises(KeyboardInterrupt):
        P.run_draw_study("H80", args, out, [("index", ["SPX"])], P.CUT, 10)
    state["stop_at"] = -1
    fp = P.run_draw_study("H80", args, out, [("index", ["SPX"])], P.CUT, 10)
    ks = [k for r in P.read_lines(os.path.join(out, "draws_index.jsonl")) for k in r["ks"]]
    assert sorted(ks) == list(range(10))
    _r, D, _e, _m = P.collect(out, [("index", ["SPX"])], fp, 10)
    assert np.array_equal(D[:, P.MARKETS.index("SPX"), 0], np.arange(10))


@pytest.mark.parametrize("asset", ["BTCUSDT", "XAUUSD", "SPX"])
def test_the_machinery_replay_is_the_book_where_the_book_ended_on_its_own_exits(asset):
    """H81/H82 score trades under the exits machinery alone (own stop, targets, a 30-day cap), never the real trade's
    end. Where the real trade did end at its own stop or Target 2 inside the cap, the two must agree exactly."""
    inp = random_inputs(n=3000, seed=11)
    ctx = _ctx(inp, asset)
    tr = P.run_book(ctx, P.RULE_CURRENT)["trades"]
    s = P.real_slots(tr)
    own = [j for j in range(len(tr)) if not s["open_exit"][j] and s["i_out"][j] <= P.cap_bar(ctx["tms"], s["i_in"][j], ctx["n"])]
    assert len(own) > 20
    for j in own:
        assert P.machine_r(ctx, int(s["side"][j]), int(s["i_in"][j]), float(s["p_in"][j])) == pytest.approx(s["r"][j], abs=1e-9)


def test_the_cap_is_thirty_days_of_time():
    t = np.arange(0, 100 * DAY, BAR, dtype="int64")
    e = P.cap_bar(t, 10, len(t))
    assert t[e] < t[10] + 30 * DAY <= t[e + 1]


def test_flipping_a_side_has_no_built_in_advantage_on_bars_without_information():
    """On random-walk bars with uninformative odds the machinery replay of the flipped side must average the same R
    as the real side (a replay that ended trades where the real side was stopped would favour the flip by ~1R)."""
    d = []
    for seed in range(12):
        ctx = _ctx(random_inputs(n=3000, seed=100 + seed), "SPX")
        tr = P.run_book(ctx, P.RULE_CURRENT)["trades"]
        s = P.real_slots(tr)
        for j in range(len(tr)):
            a = P.machine_r(ctx, int(s["side"][j]), int(s["i_in"][j]), float(s["p_in"][j]))
            b = P.machine_r(ctx, -int(s["side"][j]), int(s["i_in"][j]), float(s["p_in"][j]))
            d.append(b - a)
    d = np.array(d)
    assert len(d) > 3000 and abs(np.nanmean(d)) < 4 * np.nanstd(d) / np.sqrt(len(d)) + 0.01


# ------------------------------------------------------------------ H81b / H82b: the causal placebos
def test_trailing_long_share_reads_only_earlier_sides():
    rng = np.random.default_rng(81)
    side = rng.choice([-1, 1], 300)
    p = P.trailing_long_share(side)
    assert p[0] == 0.5 and p[1] == (1.0 if side[0] == 1 else 0.0)
    for j in (1, 7, 19, 20, 21, 150, 299):
        assert p[j] == pytest.approx(np.mean(side[max(0, j - 20):j] == 1))
        planted = side.copy()
        planted[j:] = -planted[j:]                                       # the trade's own and every later side changed
        assert np.array_equal(P.trailing_long_share(planted)[:j + 1], p[:j + 1])


def test_trailing_gap_reads_only_earlier_entries():
    rng = np.random.default_rng(82)
    pos = np.cumsum(rng.integers(1, 400, 200))
    L = P.trailing_gap(pos)
    assert L[0] == 1 and L[1] == pos[1] - pos[0]
    for j in (1, 5, 20, 21, 120, 199):
        assert L[j] == max(1, int(np.median(np.diff(pos)[max(0, j - 20):j])))
        planted = pos.copy()
        planted[j + 1:] = planted[j] + 1 + np.arange(len(pos) - j - 1)  # every later entry moved right next to j
        assert np.array_equal(P.trailing_gap(planted)[:j + 1], L[:j + 1])
    off = P.h82b_offsets(L, rng.random(len(L)))
    assert (off >= 0).all() and (off < L).all()
    assert (P.h82b_offsets(np.array([1, 5]), np.array([0.999999, 0.999999])) == [0, 4]).all()


def _causal_ctx(seed, asset):
    ctx = _ctx(random_inputs(n=3000, seed=seed), asset)
    book = P.run_book(ctx, P.RULE_CURRENT)
    sl = P.real_slots(book["trades"])
    sl["r_mach"] = np.array([P.machine_r(ctx, int(sl["side"][j]), int(sl["i_in"][j]), float(sl["p_in"][j]))
                             for j in range(len(sl["side"]))])
    ctx["slots"] = sl
    return ctx


def _poison_before(ctx, i_cut):
    """A copy of ctx whose prices and stop unit are scrambled on every bar before i_cut."""
    c2 = dict(ctx)
    px = dict((k, np.array(v, copy=True)) for k, v in ctx["inp"]["px"].items())
    unit = np.array(ctx["inp"]["unit"], copy=True)
    for k in px:
        px[k][:i_cut] = px[k][:i_cut] * 1.7 + 3.0
    unit[:i_cut] = unit[:i_cut] * 3.0
    c2["inp"] = dict(ctx["inp"], px=px, unit=unit)
    sl = dict(ctx["slots"])                                              # the gate compares with the poisoned replay
    old, new = ctx["inp"]["px"], px                                      # entry prices follow their own convention
    sl["p_in"] = np.array([new["close"][i - 1] if p == old["close"][i - 1] else new["open"][i]
                           for p, i in zip(sl["p_in"], sl["i_in"])])
    sl["r_mach"] = np.array([P.machine_r(c2, int(sl["side"][j]), int(sl["i_in"][j]), float(sl["p_in"][j]))
                             for j in range(len(sl["side"]))])
    c2["slots"] = sl
    return c2


@pytest.mark.parametrize("asset", ["BTCUSDT", "SPX"])                   # early entry / open entry
def test_h82b_windows_start_at_the_real_entry_and_read_nothing_before_the_decision(asset):
    ctx = _causal_ctx(17, asset)
    rec = P.causal_outcomes("H82b", ctx)
    s = ctx["slots"]
    L = np.asarray(rec["L"])
    tab = np.asarray(rec["tab"])
    off = np.r_[0, np.cumsum(L)[:-1]]
    assert len(L) == len(s["side"]) > 30 and (L >= 1).all() and L.max() > 1
    assert np.allclose(tab[off], s["r_mach"], atol=1e-12, equal_nan=True)  # offset 0 is the real trade
    if asset == "BTCUSDT":
        assert any(rec["early"])
    # planted: prices and stop unit scrambled before trade j's decision row leave trade j's whole window unchanged
    for j in (len(L) // 3, len(L) // 2, len(L) - 2):
        i_dec = int(s["i_in"][j]) - 1
        rec2 = P.causal_outcomes("H82b", _poison_before(ctx, i_dec))
        seg = slice(off[j], off[j] + L[j])
        assert rec2["L"][j] == L[j]
        assert np.allclose(np.asarray(rec2["tab"])[seg], tab[seg], atol=1e-12, equal_nan=True)


def test_h81b_outcomes_and_draw_never_use_a_later_side_or_an_earlier_bar():
    ctx = _causal_ctx(11, "BTCUSDT")
    rec = P.causal_outcomes("H81b", ctx)
    s = ctx["slots"]
    own = np.where(s["side"] == 1, rec["r_plus"], rec["r_minus"])
    assert np.allclose(own, s["r_mach"], atol=1e-12, equal_nan=True)
    j = len(s["side"]) // 2
    rec2 = P.causal_outcomes("H81b", _poison_before(ctx, int(s["i_in"][j]) - 1))
    assert rec2["r_plus"][j] == pytest.approx(rec["r_plus"][j], abs=1e-12)
    assert rec2["r_minus"][j] == pytest.approx(rec["r_minus"][j], abs=1e-12)
    # the draw: with the sides from trade j on changed, the placebo sides of trades 0..j stay the same
    groups = [("crypto", ["BTCUSDT", "ETHUSDT"])]
    D = P.causal_concat({"crypto": {"markets": {"BTCUSDT": rec, "ETHUSDT": dict(rec)}}}, groups)
    side2 = np.array(rec["side"])
    side2[j:] = -side2[j:]
    rec_b = dict(rec, side=side2.tolist(), p_long=P.trailing_long_share(side2).tolist())
    D2 = P.causal_concat({"crypto": {"markets": {"BTCUSDT": rec_b, "ETHUSDT": dict(rec)}}}, groups)
    for k in range(5):
        u = P.draw_rng(P.STUDIES["H81b"]["seed"], k).random((2, D["T"]))
        a = P.h81b_sides(D["p_long"], u[0])
        b = P.h81b_sides(D2["p_long"], u[0])
        assert np.array_equal(a[:j + 1], b[:j + 1])
    st = P.causal_draw("H81b", D, 3, P.STUDIES["H81b"]["seed"])
    assert set(st) == {"main", "coin"} and st["main"][P.MARKETS.index("BTCUSDT"), 0] == np.isfinite(own).sum()
    assert np.array_equal(st["main"], P.causal_draw("H81b", D, 3, P.STUDIES["H81b"]["seed"])["main"])


def _fake_causal(monkeypatch):
    rng = np.random.default_rng(5)

    def outcomes(study_, ctx):
        nt = 40
        side = rng.choice([-1, 1], nt)
        rec = {"side": side.tolist(), "h2": [i >= 20 for i in range(nt)], "real_r": [0.0] * nt,
               "r_mach": rng.normal(size=nt).tolist()}
        if study_ == "H81b":
            rec.update(r_plus=rng.normal(size=nt).tolist(), r_minus=rng.normal(size=nt).tolist(),
                       p_long=P.trailing_long_share(side).tolist())
        else:
            L = rng.integers(1, 6, nt)
            rec.update(L=L.tolist(), tab=rng.normal(size=int(L.sum())).tolist(), early=[False] * nt, L_median=3.0,
                       share_window_past_next_entry=0.0)
        return rec
    monkeypatch.setattr(P, "load_group", lambda g, assets, fits, out, cut: {
        "times": pd.date_range("2021-01-01", periods=10, freq="15min", tz="UTC"), "_load_s": 0.0})
    monkeypatch.setattr(P, "market_ctx", lambda prep, a: {"lo": 1, "n": 10, "a": a})
    monkeypatch.setattr(P, "real_books_for", lambda study_, ctxs, gl, prep=None: dict(
        (a, {"current": [1] * P.NSTAT, "real": [1] * P.NSTAT}) for a in ctxs))
    monkeypatch.setattr(P, "causal_outcomes", outcomes)
    monkeypatch.setattr(P, "CAUSAL_BLOCK", 3)


@pytest.mark.parametrize("study", ["H81b", "H82b"])
def test_causal_resume_never_double_counts_a_draw(tmp_path, monkeypatch, study):
    import shutil
    _fake_causal(monkeypatch)
    real_draw = P.causal_draw
    calls = []
    state = {"stop_at": 7}

    def counted(study_, D, k, seed):
        if len(calls) == state["stop_at"]:
            raise KeyboardInterrupt()
        calls.append(k)
        return real_draw(study_, D, k, seed)
    monkeypatch.setattr(P, "causal_draw", counted)
    args = type("A", (), {"fits_dir": str(tmp_path)})()
    groups = [("index", ["SPX"]), ("fx", ["USDJPY"])]
    out = str(tmp_path / "o")
    os.makedirs(out)
    with pytest.raises(KeyboardInterrupt):
        P.run_causal_study(study, args, out, groups, P.CUT, 10)
    assert calls == list(range(7))
    state["stop_at"] = -1
    reals, S, gates, win, extra = P.run_causal_study(study, args, out, groups, P.CUT, 10)
    assert calls[7:] == [6, 7, 8, 9]                                     # only the unwritten block is computed again
    n_before = len(calls)
    _r2, S2, _g2, _w2, _e2 = P.run_causal_study(study, args, out, groups, P.CUT, 10)
    assert len(calls) == n_before                                        # a third run computes nothing
    out2 = str(tmp_path / "fresh")                                       # the same outcomes, one uninterrupted run
    os.makedirs(out2)
    for g, _a in groups:
        shutil.copy(os.path.join(out, "outcomes_%s.json" % g), os.path.join(out2, "outcomes_%s.json" % g))
    _r3, S3, _g3, _w3, _e3 = P.run_causal_study(study, args, out2, groups, P.CUT, 10)
    for nm in S:
        assert np.isfinite(S[nm][:, P.MARKETS.index("SPX"), 0]).all()
        assert np.array_equal(S[nm], S3[nm]) and np.array_equal(S[nm], S2[nm])
    files = sorted(f for f in os.listdir(out) if f.startswith("draws_%s_" % study))
    assert files == ["draws_%s_%04d.npz" % (study, b) for b in range(4)]


def test_random_walk_check_causal_placebos_find_nothing_and_old_designs_tilt():
    """On driftless random walks no causal rule earns anything. The causal placebos (H81b trailing share, H81b coin,
    H82b trailing-gap window) must show no difference from the toy book for a momentum, a reversal and a coin rule; the
    designs found to look ahead must show their tilt (so the check can see one)."""
    res = P.rw_check(walks=16, draws=100, years=2)
    for rule in ("momentum", "reversal", "coin"):
        for d in ("h81b_trailing", "h81b_coin", "h82b_trailing_gap"):
            c = res[rule][d]
            assert abs(c["gap_mean"]) < 3.5 * c["gap_se"] + 0.005, (rule, d, c)
    m, r = res["momentum"]["h81_month_perm"], res["reversal"]["h81_month_perm"]
    assert m["gap_mean"] > 2.5 * m["gap_se"] and r["gap_mean"] < -2.5 * r["gap_se"]   # the old H81 tilt
    for rule in ("momentum", "reversal", "coin"):            # the window that runs to the NEXT real entry leaks the end
        c = res[rule]["h82b_window_to_next_entry"]
        assert c["gap_mean"] < -3 * c["gap_se"], (rule, c)
