# -*- coding: utf-8 -*-
"""H122 (engine15/cards6.py, cards6_books.py): the commodity cards and their paper books.
What is held here: the mind odds move the Lead by 2.0 points per full card; C1, C2, C5 follow H122's rules on planted
bars; no card reads the future (real bars cut off: the votes before the cut stay); a card book enters at the next
open, stops and leaves when the card does; the kill rules; a full shadows.advance step creates the five books on
metals only, starts them flat, and leaves every other book (b_targets included) exactly as it was."""
import copy
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine15 import cards6, cards6_books, labels, model, shadows  # noqa: E402
from engine15.config import CFG, DATA_DIR, voting_for  # noqa: E402
from engine15.evidence import FEATURES  # noqa: E402

BAR = cards6.BAR_MS


def grid(n, start="2026-10-05 00:00"):
    t = pd.date_range(start, periods=n, freq="15min", tz="UTC")
    return t, cards6._ms(t)


# ------------------------------------------------------------------ the mixing
def test_one_full_card_moves_the_lead_two_points_and_muting_silences_it():
    live = np.array([[0.30, 0.35, 0.35], [0.20, 0.50, 0.30]])
    out = cards6.mind_odds(live, {"c1": np.array([1.0, 0.0]), "c2": np.array([0.0, 0.0]), "c5": np.array([-0.5, 0.0])})
    lead = (out[:, 1] - out[:, 2]) * 100
    assert abs(lead[0] - (0.0 * 0.8 + 2.0 - 1.0)) < 1e-9          # two cards: live x 0.8, +2.0 and -1.0
    assert abs(lead[1] - 20.0) < 1e-9 and np.allclose(out[1], live[1])
    assert np.allclose(out.sum(axis=1), 1.0)
    m = cards6.mind_odds(live, {"c1": np.array([1.0, 0.0]), "c5": np.array([-0.5, 0.0])}, muted=("c1",))
    assert abs((m[0, 1] - m[0, 2]) * 100 - (-1.0)) < 1e-9
    nan = cards6.mind_odds(np.full((1, 3), np.nan), {"c1": np.array([1.0])})
    assert np.isnan(nan).all()


# ------------------------------------------------------------------ C1
def test_c1_full_half_silent_and_the_close_back():
    t, ms = grid(60)
    o = np.full(60, 100.0)
    c = np.full(60, 100.0)
    atr = np.full(60, 1.0)
    R = 20
    rel = np.array([ms[R] + 5 * 60 * 1000])                     # 5 minutes into bar R
    c[R + 1:] = 101.6                                            # I = 1.6: full, up
    v = cards6.c1_votes(ms, o, c, atr, rel, 0, 60)
    assert v[R] == 0 and (v[R + 1:R + 17] == 1.0).all() and v[R + 17] == 0
    c[R + 1:] = 101.2                                            # I = 1.2: half
    assert (cards6.c1_votes(ms, o, c, atr, rel, 0, 60)[R + 1:R + 17] == 0.5).all()
    c[R + 1:] = 100.8                                            # I = 0.8: silent
    assert not cards6.c1_votes(ms, o, c, atr, rel, 0, 60).any()
    c[R + 1:] = 101.6
    c[R + 6:] = 99.9                                             # a close back below R's open: silent for good
    v = cards6.c1_votes(ms, o, c, atr, rel, 0, 60)
    assert (v[R + 1:R + 6] == 1.0).all() and not v[R + 6:].any()
    assert (cards6.c1_votes(ms, o, c, atr, rel, R + 3, 60) == v[R + 3:]).all()   # rows from r0 only, same values


def test_release_times_for_metals_and_oil():
    t_oil = cards6.release_times("WTI", until_ms=int(pd.Timestamp("2026-12-31", tz="UTC").value // 10 ** 6))
    days = pd.to_datetime(t_oil, unit="ms", utc=True)
    assert len(t_oil) > 300 and set(days[-20:].dayofweek) <= {2, 3}   # Wednesdays (Thursdays in a holiday week)
    t_m = cards6.release_times("XAUUSD", until_ms=int(pd.Timestamp("2026-12-31", tz="UTC").value // 10 ** 6))
    assert len(t_m) > 200 and (np.diff(t_m) > 0).all()


# ------------------------------------------------------------------ C2
def test_c2_a_lagging_asset_gets_the_leaders_direction_until_it_catches_up(monkeypatch):
    monkeypatch.setattr(cards6.rolls, "near_switch", lambda *a, **k: False)
    rng = np.random.RandomState(3)
    n = 2600
    t, ms = grid(n)
    rl = rng.normal(0, 0.001, n)
    ra = -0.8 * rl + rng.normal(0, 0.0004, n)                    # the asset moves against the leader (gold vs USDJPY)
    k = 2500
    rl[k] = 0.006                                                # the leader jumps 6 sd ...
    ra[k] = 0.0                                                  # ... the asset has not moved yet
    lead = 100 * np.exp(np.cumsum(rl))
    c = 100 * np.exp(np.cumsum(ra))
    o = np.r_[c[0], c[:-1]]
    v = cards6.c2_votes("XAUUSD", ms, o, c, lead, 2400, n)
    assert v[k - 2400] == -1.0 and (v[k - 2400:k - 2400 + 4] == -1.0).all() and v[k - 2400 + 4] == 0
    c2 = c.copy()
    c2[k + 1:] *= np.exp(-0.0045)                                # it catches up at the next bar (>= 0.8 E): silent
    v2 = cards6.c2_votes("XAUUSD", ms, np.r_[c2[0], c2[:-1]], c2, lead, 2400, n)
    assert v2[k - 2400] == -1.0 and not v2[k - 2400 + 1:k - 2400 + 4].any()
    lead2 = lead.copy()
    lead2[k + 1] = np.nan                                        # the leader's bar missing: silent from there
    v3 = cards6.c2_votes("XAUUSD", ms, o, c, lead2, 2400, n)
    assert v3[k - 2400] == -1.0 and not v3[k - 2400 + 1:k - 2400 + 4].any()


# ------------------------------------------------------------------ C5
def test_c5_a_planted_weekly_drift_is_found_and_needs_both_halves(monkeypatch):
    monkeypatch.setattr(cards6.rolls, "near_switch", lambda *a, **k: False)
    rng = np.random.RandomState(11)
    t = pd.date_range("2024-01-01", "2026-03-01", freq="15min", tz="UTC")
    t = t[t.dayofweek < 5]
    ms = cards6._ms(t)
    loc = cards6._ny(ms + BAR)
    r = rng.normal(0, 0.001, len(t))
    hot = (loc.dayofweek == 1) & (loc.hour == 10) & (loc.minute == 0)   # Tuesday 10:00 New York closes: up after
    idx = np.where(hot)[0]
    for i in idx:
        r[i + 1:i + 17] += 0.0004
    c = 100 * np.exp(np.cumsum(r))
    p5 = cards6.c5_prepare("XAUUSD", ms, c)
    r0 = len(ms) - 96 * 10
    v = cards6.c5_votes(p5, r0, len(ms))
    assert all(v[i - r0] == 1.0 for i in idx if i >= r0 and not p5["excl"][i])
    close = p5["close"][r0:]
    hot_t = p5["close"][idx]
    near = np.array([np.abs(hot_t - x).min() < 5 * 3600 * 1000 for x in close])
    # away from the planted slot it speaks only by chance: 3-10% of bars on pure noise (240 slots tested; H122 named
    # the multiple-testing risk; K3 pauses it above 60%)
    assert np.count_nonzero(v[~near]) <= 0.15 * (~near).sum()
    r2 = r.copy()
    for i in idx[:len(idx) // 2]:                                # the older half drifts the other way
        r2[i + 1:i + 17] -= 0.0008
    p5b = cards6.c5_prepare("XAUUSD", ms, 100 * np.exp(np.cumsum(r2)))
    vb = cards6.c5_votes(p5b, r0, len(ms))
    assert not any(vb[i - r0] for i in idx if i >= r0)


# ------------------------------------------------------------------ no look-ahead, on the stored bars
def _real(asset, tail):
    path = os.path.join(DATA_DIR, "%s_15m.csv" % asset.lower())
    if not os.path.exists(path):
        pytest.skip("no stored bars")
    df = pd.read_csv(path).tail(tail).reset_index(drop=True)
    t = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
    px = dict((k, df[k].values.astype(float)) for k in ("open", "high", "low", "close"))
    tr = (df["high"] - df["low"]).rolling(56, min_periods=8).mean() * 2.0
    ev = pd.DataFrame({"atr1h": tr.values}, index=t)
    return t, px, ev


@pytest.mark.parametrize("asset", ["XAUUSD", "WTI"])
def test_no_card_reads_the_future(asset):
    t, px, ev = _real(asset, 80000)
    n = len(t)
    cut, r0 = n - 400, n - 1400
    full = cards6.votes(asset, t, px, ev, r0, n)
    part = cards6.votes(asset, t[:cut], dict((k, v[:cut]) for k, v in px.items()), ev.iloc[:cut], r0, cut)
    for k in cards6.CARDS:
        assert np.array_equal(full[k][:cut - r0], part[k]), k
    said = dict((k, int(np.count_nonzero(full[k]))) for k in cards6.CARDS)
    assert said["c1"] + said["c2"] + said["c5"] > 0, said


# ------------------------------------------------------------------ a card's book
def test_card_book_enters_next_open_stops_and_leaves_with_the_card():
    t, ms = grid(40)
    c = np.full(40, 100.0)
    o, h, l = c.copy(), c + 0.1, c - 0.1
    unit = np.full(40, 1.0)
    vote = np.zeros(40)
    vote[5:10] = 1.0                                             # long from the close of 5 to the close of 9
    vote[20:30] = -1.0
    l[25] = 97.0 - 0.5                                           # the short is not hit by a low ...
    h[25] = 102.5                                                # ... but by a high beyond entry + 2 units
    cfg = {"cost_side": 0.0, "risk_per_trade": 0.02, "leverage_cap": 5.0, "stop_units": 2.0}
    st, tr = cards6.card_book(None, ms, o, h, l, c, unit, vote, 0, 40, cfg)
    assert len(tr) == 2
    a, b = tr
    assert a[2] == 6 and a[3] == 11 and a[8] == "CARD_OFF" and a[4] == 1      # in at the open after 5; silent at 10
    assert b[2] == 21 and b[8] == "STOP" and b[4] == -1 and abs(b[6] - 102.0) < 1e-9
    assert abs(b[16] - (-1.0)) < 1e-9                            # a full stop is -1R (no fees here)
    assert st["pos"] == 0 and st["stats"]["n"] == 2                       # no new entry while it still says short
    st1, tr1 = cards6.card_book(None, ms, o, h, l, c, unit, vote[:15], 0, 15, cfg)
    st2, tr2 = cards6.card_book(st1, ms, o, h, l, c, unit, vote[15:], 15, 40, cfg)
    assert [x[:9] for x in tr1 + tr2] == [x[:9] for x in tr]     # two steps = one long step


def test_kill_rules():
    assert cards6.kill_state([-1.0] * 4, None, "c1")[0]                         # K1 at -4R
    assert not cards6.kill_state([-1.0] * 3 + [0.5], None, "c1")[0]
    m, why = cards6.kill_state([1.0] * 3 + [-1.0] * 9, None, "c2")              # K2 from 12 trades
    assert m and why.startswith("K1") or why.startswith("K2")
    assert cards6.kill_state([], 0.45, "c1")[0] and not cards6.kill_state([], 0.45, "c5")[0]   # K3 40% / 60%


# ------------------------------------------------------------------ the books in a real step
def planted_metals(n=1200, seed=4):
    rng = np.random.RandomState(seed)
    assets = ["XAUUSD", "XAGUSD"]
    times = pd.date_range("2026-10-05", periods=n, freq="15min", tz="UTC")
    cfg = dict(CFG, assets=tuple(assets), voting=voting_for("metals"), horizon=24)
    prep = {"cfg": cfg, "times": times, "ev": {}, "px": {}, "X": {}, "ready": {}, "y": {}, "res": {}, "probs": {},
            "odds": {}, "birth_idx": 60}
    V = len(model.VOICE_NAMES)
    for a in assets:
        c = 2000.0 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
        o = np.r_[c[0], c[:-1]]
        sp = np.abs(rng.normal(0, 0.002, n)) * c
        px = {"open": o, "high": np.maximum(o, c) + sp, "low": np.minimum(o, c) - sp, "close": c}
        ev = pd.DataFrame({"shock": rng.rand(n) < 0.03, "tide": rng.uniform(-1, 1, n), "atr1h": c * 0.006,
                           "atr15": c * 0.002, "htf_bias": np.zeros(n), "release_soon": np.zeros(n, bool),
                           "sw_lo_15m": c * 0.99, "sw_hi_15m": c * 1.01, "reach_24h_med_pct": np.ones(n)}, index=times)
        probs = rng.dirichlet(np.ones(3) * 4, size=(n, V))
        unit = (cfg["barrier_atr"] * ev["atr1h"]).values
        y, res = labels.triple_barrier(px["open"], px["high"], px["low"], unit, cfg["horizon"])
        od = rng.dirichlet(np.ones(3) * 3, size=n)
        prep["px"][a], prep["ev"][a], prep["probs"][a], prep["odds"][a] = px, ev, probs, od
        prep["X"][a] = rng.normal(0, 1, (n, len(FEATURES)))
        prep["ready"][a], prep["y"][a], prep["res"][a] = np.ones(n, bool), y, res
    return prep, assets


def test_a_step_starts_the_five_books_flat_on_metals_and_changes_no_other_book(monkeypatch):
    prep, assets = planted_metals()
    rng = np.random.RandomState(9)
    fake = dict((a, {"c1": np.zeros(1200), "c2": np.zeros(1200), "c5": np.zeros(1200)}) for a in assets)
    for a in assets:
        for k in cards6.CARDS:
            fake[a][k][rng.rand(1200) < 0.15] = rng.choice([-1.0, -0.5, 0.5, 1.0], size=1)

    def votes(prep_, group, todo, r0, n, log):
        return dict((a, dict(dict((k, fake[a][k][r0:n]) for k in cards6.CARDS), _lead_missing=0)) for a in todo)
    monkeypatch.setattr(cards6_books, "_group_votes", votes)
    monkeypatch.setattr(shadows, "swing_odds", lambda *a, **k: {})
    with_cards = {"version": 1, "groups": {}, "books": {}}
    shadows.advance(prep, "metals", assets, 1200, with_cards, start_lo=600)
    names = [b.NAME for b in cards6_books.BOOKS]
    for nm in names:
        assert set(with_cards["books"][nm]) == set(assets), nm
        assert with_cards["late_starts"][nm][assets[0]]["ms"] == shadows._ms(prep["times"][600])
    assert sum(with_cards["books"]["c6_c1"][a]["stats"]["n"] for a in assets) > 3
    mind = with_cards["books"]["m_cards6"][assets[0]]
    assert set(mind["mind"]["cards_now"]) == set(cards6.CARDS)
    saved = dict(shadows.MINDS)
    try:
        for nm in names:
            shadows.MINDS.pop(nm)
        without = {"version": 1, "groups": {}, "books": {}}
        shadows.advance(prep, "metals", assets, 1200, without, start_lo=600)
    finally:
        shadows.MINDS.clear()
        shadows.MINDS.update(saved)
    for nm, books in without["books"].items():
        assert with_cards["books"][nm] == books, nm               # b_targets and every other book: unchanged
    crypto = {"version": 1, "groups": {}, "books": {}}
    cp, _ = planted_metals()
    cp = dict(cp, px={"BTCUSDT": cp["px"]["XAUUSD"]}, ev={"BTCUSDT": cp["ev"]["XAUUSD"]},
              odds={"BTCUSDT": cp["odds"]["XAUUSD"]}, X={"BTCUSDT": cp["X"]["XAUUSD"]},
              probs={"BTCUSDT": cp["probs"]["XAUUSD"]}, y={"BTCUSDT": cp["y"]["XAUUSD"]},
              res={"BTCUSDT": cp["res"]["XAUUSD"]}, ready={"BTCUSDT": cp["ready"]["XAUUSD"]})
    shadows.advance(cp, "crypto", ["BTCUSDT"], 1200, crypto, start_lo=600)
    assert not any(nm in crypto["books"] for nm in names)        # crypto: the cards6 books never start


def test_m1_stops_a_mind_far_behind_its_yardstick():
    b = [x for x in cards6_books.BOOKS if x.NAME == "m_cards6"][0]
    sst = {"books": {"m_cards6": {"XAUUSD": {"stats": {"r_sum": -5.0}}}, "b_targets": {"XAUUSD": {"stats": {"r_sum": 3.0}}}},
           "late_starts": {"m_cards6": {"XAUUSD": {"yard_r_sum": 1.0}}}}
    b._kills(sst)
    assert sst["cards6"]["stopped"]["m_cards6"].startswith("M1")
    sst["cards6"]["stopped"] = {}
    sst["books"]["b_targets"]["XAUUSD"]["stats"]["r_sum"] = 1.5
    b._kills(sst)
    assert not sst["cards6"]["stopped"]


def test_usdjpy_is_read_only_up_to_the_fx_groups_last_step(tmp_path, monkeypatch):
    """The parallel step must give the same votes as one group after another (tests/test_parallel_step.py)."""
    import json
    from engine15 import config
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    pd.DataFrame({"ts_ms": [0, BAR, 2 * BAR], "close": [1.0, 2.0, 3.0]}).to_csv(tmp_path / "usdjpy_15m.csv", index=False)
    assert cards6.load_leader("USDJPY") is None                  # no fx mark yet: no leader
    (tmp_path / "live_state.json").write_text(json.dumps({"last_ms": {"fx": BAR}}), encoding="utf-8")
    s = cards6.load_leader("USDJPY")
    assert list(s.index) == [0, BAR] and list(s.values) == [1.0, 2.0]
