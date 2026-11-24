# -*- coding: utf-8 -*-
"""H108, the regime trust shadow mind (engine15/regime_trust.py), on planted inputs. No network, no data files.

    py -3 -m pytest -q -p no:cacheprovider tests/test_regime_trust.py

What is held here: the four registered buckets; each bucket's table is model.trust_path on that bucket's calls; with
one bucket the mind IS the live learner; nothing reads the future (cut the later bars off: the odds at bar t stay);
the book is the main rule on the mind's odds, starts flat, resumes exactly; no other book changes; a failure is one
log line and the step goes on; the scoreboard says NOT passed and gives no read before 30 closed trades.
"""
import copy
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import labels, leanprep, model, regime_trust as rt, reports, shadows  # noqa: E402
from engine15.config import CFG, voting_for  # noqa: E402
from engine15.evidence import FEATURES  # noqa: E402

ASSETS = ["BTCUSDT", "ETHUSDT"]
REGIMES = ["TREND_UP", "TREND_DOWN", "MOMENTUM_UP", "MOMENTUM_DOWN", "RANGE", "TRANSITION"]
V = len(model.VOICE_NAMES)
QUIET = lambda *_: None      # noqa: E731


# ------------------------------------------------------------------ planted inputs
def live_mix(prep, a, trust, lo, n):
    """The engine's own odds for rows lo .. n-1 from a trust path (rows lo .. n-1), as backtest.prepare mixes them."""
    cfg = prep["cfg"]
    votes = np.array([1.0 if v in cfg["voting"] else 0.0 for v in model.VOICE_NAMES])
    t = trust * votes
    t = model.cap_shares(t / t.sum(axis=1, keepdims=True), cfg.get("trust_cap"))
    X = prep["X"][a][lo:n]
    speaks = np.stack([(np.abs(X[:, model._COLS[v]]).sum(axis=1) > 0) if model._COLS[v] else np.zeros(n - lo, bool)
                       for v in model.VOICE_NAMES], axis=1)
    w = t * speaks
    tot = w.sum(axis=1, keepdims=True)
    w = model.cap_shares(np.where(tot > 0, w / np.where(tot > 0, tot, 1.0), t), cfg.get("trust_cap"))
    return model.mix(prep["probs"][a][lo:n], w)


def planted(n=900, seed=5, birth=60, halflife=80, horizon=24, bars=None):
    """A full-prepare-shaped prep of two markets: random bars, the real grades (labels.triple_barrier), a planted
    call of every voice at every bar from `birth` on, a regime and a volatility rank that change in blocks, and the
    engine's own trust and odds computed with the library's own functions. `bars`: reuse (and cut) another prep's."""
    rng = np.random.RandomState(seed)
    times = pd.date_range("2026-10-01", periods=n, freq="15min", tz="UTC")
    cfg = dict(CFG, assets=tuple(ASSETS), voting=voting_for("crypto"), trust_halflife=halflife, horizon=horizon)
    # no "assets" key: shadows.swing_odds then leaves the 1h / 4h swing minds out (they would fit models here)
    prep = {"cfg": cfg, "times": times, "ev": {}, "px": {}, "X": {}, "ready": {}, "y": {},
            "res": {}, "probs": {}, "odds": {}, "birth_idx": birth}
    for a in ASSETS:
        if bars is not None:
            src = bars[a]
            px = dict((k, src["px"][k][:n].copy()) for k in ("open", "high", "low", "close"))
            ev = src["ev"].iloc[:n].copy()
            X, probs = src["X"][:n].copy(), src["probs"][:n].copy()
        else:
            c = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.004, n)))
            o = np.concatenate([[100.0], c[:-1]])
            sp = np.abs(rng.normal(0, 0.003, n)) * c
            px = {"open": o, "high": np.maximum(o, c) + sp, "low": np.minimum(o, c) - sp, "close": c}
            reg = np.empty(n, dtype=object)
            vr = np.empty(n)
            for s in range(0, n, 37):                            # blocks, so every bucket holds calls
                reg[s:s + 37] = REGIMES[rng.randint(len(REGIMES))]
                vr[s:s + 37] = rng.uniform(0, 1)
            reg[:birth // 2] = None                              # the label needs 210 daily closes: none at first
            vr[:birth // 3] = np.nan
            ev = pd.DataFrame({"shock": rng.rand(n) < 0.05, "tide": rng.uniform(-1, 1, n), "atr1h": c * 0.01,
                               "atr15": c * 0.003, "htf_bias": rng.choice([-1.0, 0.0, 1.0], size=n, p=[0.2, 0.6, 0.2]),
                               "release_soon": rng.rand(n) < 0.03, "sw_lo_15m": c * 0.99, "sw_hi_15m": c * 1.01,
                               "reach_24h_med_pct": rng.uniform(0.5, 2.0, n), "regime": reg, "vol_rank": vr},
                              index=times)
            X = rng.normal(0, 1, (n, len(FEATURES))) * (rng.rand(n, len(FEATURES)) < 0.7)
            probs = rng.dirichlet(np.ones(3) * 4, size=(n, V))
            probs[:birth] = np.nan
        unit = (cfg["barrier_atr"] * ev["atr1h"]).values
        y, res = labels.triple_barrier(px["open"], px["high"], px["low"], unit, cfg["horizon"])
        prep["px"][a], prep["ev"][a], prep["X"][a], prep["probs"][a] = px, ev, X, probs
        prep["ready"][a], prep["y"][a], prep["res"][a] = np.ones(n, bool), y, res
    trust = model.trust_path(prep["probs"], prep["y"], prep["res"], cfg)
    prep["trust"] = trust
    for a in ASSETS:
        prep["odds"][a] = live_mix(prep, a, trust, 0, n)
    return prep


def cut_prep(prep, cut):
    """The same market history with every bar from `cut` on removed (the grades are worked out again)."""
    src = dict((a, {"px": prep["px"][a], "ev": prep["ev"][a], "X": prep["X"][a], "probs": prep["probs"][a]})
               for a in ASSETS)
    return planted(n=cut, birth=prep["birth_idx"], halflife=prep["cfg"]["trust_halflife"],
                   horizon=prep["cfg"]["horizon"], bars=src)


def as_lean(prep):
    """The same prep as leanprep hands it over: calls and trust kept from the birth row on (Tail)."""
    lo, n = prep["birth_idx"], len(prep["times"])
    out = dict(prep, lean_lo=lo, trust=leanprep.Tail(prep["trust"][lo:], lo, n))
    out["probs"] = dict((a, leanprep.Tail(prep["probs"][a][lo:], lo, n)) for a in ASSETS)
    return out


def fresh():
    return {"version": 1, "groups": {}, "books": {}}


# ------------------------------------------------------------------ the buckets
def test_the_buckets_are_the_four_registered_ones():
    assert rt.BUCKETS == ("trend_hi", "trend_lo", "range_hi", "range_lo") and rt.VOL_SPLIT == 0.5
    assert rt.TREND_LABELS == ("TREND_UP", "TREND_DOWN", "MOMENTUM_UP", "MOMENTUM_DOWN")
    assert rt.RANGE_LABELS == ("RANGE", "TRANSITION")
    from engine15 import indicators
    assert set(rt.TREND_LABELS) | set(rt.RANGE_LABELS) == set(indicators.REGIMES)      # every label has a side
    ev = pd.DataFrame({"regime": ["TREND_UP", "MOMENTUM_DOWN", "RANGE", "TRANSITION", "TREND_DOWN", None, "RANGE",
                                  np.nan, "SOMETHING_NEW"],
                       "vol_rank": [0.5, 0.49, 0.9, 0.0, np.nan, 0.7, 1.0, 0.2, 0.9]})
    assert list(rt.bucket_codes(ev, 0, 9)) == [0, 1, 2, 3, -1, -1, 2, -1, -1]
    assert list(rt.bucket_codes(ev, 2, 5)) == [2, 3, -1]                                 # rows lo .. n-1 only
    assert list(rt.bucket_codes(ev[["regime"]], 0, 3)) == [-1, -1, -1]                   # a reading missing: no bucket


def test_it_adds_no_config_key_and_reads_the_live_learners_constants():
    assert not [k for k in CFG if "regime_trust" in k or "bucket" in k]
    prep = planted(n=400)
    codes = dict((a, rt.bucket_codes(prep["ev"][a], 0, 400)) for a in ASSETS)
    S, _ = rt.loss_sums(prep, ASSETS, codes, 0, 400, 399)
    slow = dict(prep, cfg=dict(prep["cfg"], trust_halflife=5))                           # the live half-life is the clock
    S2, _ = rt.loss_sums(slow, ASSETS, codes, 0, 400, 399)
    assert S2.sum() < 0.5 * S.sum()
    w = rt.weights(S[0], prep["cfg"])
    assert np.allclose(w.sum(axis=-1), 1.0) and w.min() >= prep["cfg"]["trust_floor"] / 2


# ------------------------------------------------------------------ the tables
def test_each_bucket_table_is_trust_path_fed_with_that_buckets_calls():
    prep = planted()
    n, cfg = len(prep["times"]), prep["cfg"]
    codes = dict((a, rt.bucket_codes(prep["ev"][a], 0, n)) for a in ASSETS)
    assert all((codes[a] == k).sum() > 30 for a in ASSETS for k in range(4))             # every bucket holds bars
    want = []
    for k in range(len(rt.BUCKETS)):                                                     # the registered definition
        y_b = dict((a, np.where(codes[a] == k, prep["y"][a], labels.UNKNOWN).astype(np.int8)) for a in ASSETS)
        want.append(model.trust_path(prep["probs"], y_b, prep["res"], cfg))
    want = np.stack(want, axis=1)                                                        # (n, buckets, voices)
    for r0 in (prep["birth_idx"], 500, n - 1):
        S, calls = rt.loss_sums(prep, ASSETS, codes, 0, n, r0)
        got = rt.weights(S, cfg)
        assert got.shape == (n - r0, 4, V)
        assert np.allclose(got, want[r0:], rtol=1e-9, atol=1e-12)
        assert calls.sum() > 200 and (calls > 0).all()
    lean = as_lean(prep)                                                                 # the lean step's shapes
    lo = lean["lean_lo"]
    codes_l = dict((a, rt.bucket_codes(lean["ev"][a], lo, n)) for a in ASSETS)
    S, _ = rt.loss_sums(lean, ASSETS, codes_l, lo, n, n - 3)
    assert np.allclose(rt.weights(S, cfg), want[n - 3:], rtol=1e-9, atol=1e-12)


def test_with_one_bucket_the_mind_is_the_live_learner(monkeypatch):
    prep = planted()
    n, lo = len(prep["times"]), prep["birth_idx"]
    monkeypatch.setattr(rt, "bucket_codes", lambda ev, lo_, n_: np.zeros(max(n_ - lo_, 0), dtype=np.int8))
    for p in (prep, as_lean(prep)):
        od, code, _ = rt.odds(p, ASSETS, lo, n)
        for a in ASSETS:
            assert np.isfinite(od[a]).all() and np.allclose(od[a].sum(axis=1), 1.0)
            assert np.allclose(od[a], prep["odds"][a][lo:], rtol=1e-9, atol=1e-12)


def test_the_buckets_change_the_odds_and_the_cap_still_holds():
    prep = planted()
    n, lo = len(prep["times"]), prep["birth_idx"]
    od, code, _ = rt.odds(prep, ASSETS, lo + 300, n)
    a = ASSETS[0]
    assert np.abs(od[a] - prep["odds"][a][lo + 300:]).max() > 1e-3                       # not the live odds
    assert np.allclose(od[a].sum(axis=1), 1.0)
    codes = dict((x, rt.bucket_codes(prep["ev"][x], 0, n)) for x in ASSETS)
    S, _ = rt.loss_sums(prep, ASSETS, codes, 0, n, n - 1)
    votes = np.array([1.0 if v in prep["cfg"]["voting"] else 0.0 for v in model.VOICE_NAMES])
    t = rt.weights(S[0], prep["cfg"]) * votes
    t = model.cap_shares(t / t.sum(axis=1, keepdims=True), prep["cfg"]["trust_cap"])
    assert t.max() <= prep["cfg"]["trust_cap"] + 1e-9 and prep["cfg"]["trust_cap"] == 0.40


def test_a_bar_with_no_bucket_uses_the_engines_own_odds():
    prep = planted()
    n = len(prep["times"])
    for a in ASSETS:
        prep["ev"][a].loc[prep["times"][n - 5:n - 2], "vol_rank"] = np.nan
    od, code, _ = rt.odds(prep, ASSETS, n - 8, n)
    for a in ASSETS:
        assert list(code[a][3:6]) == [-1, -1, -1] and (code[a][:3] >= 0).all()
        assert np.array_equal(od[a][3:6], prep["odds"][a][n - 5:n - 2])


# ------------------------------------------------------------------ no look-ahead
def test_the_odds_never_read_the_future():
    """Cut the later bars off: the mind's odds at every bar it had already seen stay the same (as
    tests/test_engine.py::test_evidence_never_reads_the_future does for the readings)."""
    full = planted()
    n, lo = len(full["times"]), full["birth_idx"]
    whole, _, _ = rt.odds(full, ASSETS, lo, n)
    for cut in (431, 640, 860):
        part = cut_prep(full, cut)
        assert (part["y"][ASSETS[0]] != full["y"][ASSETS[0]][:cut]).any()                # grades not known yet at the cut
        got, _, _ = rt.odds(part, ASSETS, lo, cut)
        one, _, _ = rt.odds(part, ASSETS, cut - 1, cut)                                  # a live step: the last bar alone
        same_rows, _, _ = rt.odds(full, ASSETS, lo, cut)                                 # the full prep, rows below cut
        for a in ASSETS:
            assert np.allclose(got[a], whole[a][:cut - lo], rtol=1e-9, atol=1e-12), "the odds changed at cut %d" % cut
            assert np.allclose(one[a][0], whole[a][cut - 1 - lo], rtol=1e-9, atol=1e-12)
            assert np.allclose(same_rows[a], whole[a][:cut - lo], rtol=1e-9, atol=1e-12)


def test_a_grade_that_arrives_later_does_not_move_an_earlier_table():
    prep = planted()
    n, s = len(prep["times"]), 600
    codes = dict((a, rt.bucket_codes(prep["ev"][a], 0, n)) for a in ASSETS)
    before, _ = rt.loss_sums(prep, ASSETS, codes, 0, n, 400)
    a = ASSETS[0]
    late = np.where((np.arange(n) + prep["res"][a] > s) & (prep["y"][a] > 0))[0]         # graded after bar s
    assert len(late) > 20
    prep["y"][a] = prep["y"][a].copy()
    prep["y"][a][late] = 3 - prep["y"][a][late]                                          # up <-> down
    after, _ = rt.loss_sums(prep, ASSETS, codes, 0, n, 400)
    assert np.array_equal(before[:s - 400 + 1], after[:s - 400 + 1])
    assert not np.array_equal(before[s - 400 + 1:], after[s - 400 + 1:])


def test_the_book_at_bar_t_is_the_same_when_later_bars_are_removed():
    full = planted()
    cut = 640
    seen, known = fresh(), fresh()
    shadows.advance(full, "crypto", ASSETS, cut, seen, start_lo=300)                     # the future is in the prep
    _v, closed = shadows.advance(cut_prep(full, cut), "crypto", ASSETS, cut, known, start_lo=300)   # ... and cut off
    for a in ASSETS:
        x, y = seen["books"][rt.NAME][a], known["books"][rt.NAME][a]
        assert x["stats"]["n"] > 3 and len(closed[(rt.NAME, a)]) == x["stats"]["n"]
        for k in ("pos", "idle", "why_in", "pending", "stats", "mind", "t_in_ms"):
            assert x[k] == y[k], k
        for k in ("qty", "entry", "eq", "fees", "equity_marked"):
            assert abs(x[k] - y[k]) <= 1e-6 * max(1.0, abs(x[k])), k


# ------------------------------------------------------------------ the book
def test_the_book_starts_flat_and_two_steps_equal_one_long_step():
    prep = planted()
    one, two = fresh(), fresh()
    shadows.advance(prep, "crypto", ASSETS, 900, one, start_lo=300)
    _v, c_a = shadows.advance(prep, "crypto", ASSETS, 610, two, start_lo=300)
    view, c_b = shadows.advance(prep, "crypto", ASSETS, 900, two)
    assert set(one["books"][rt.NAME]) == set(ASSETS)
    for a in ASSETS:
        x, y = one["books"][rt.NAME][a], two["books"][rt.NAME][a]
        assert x["stats"]["n"] > 5 and x["mind"]["last_ms"] == shadows._ms(prep["times"][899])
        assert x["mind"]["bucket"] in rt.BUCKETS and sum(x["mind"]["bars"].values()) == 600
        for k in ("pos", "idle", "why_in", "pending", "stats", "mind"):
            assert x[k] == y[k], k
        for k in ("qty", "entry", "eq", "fees", "equity_marked"):
            assert abs(x[k] - y[k]) <= 1e-6 * max(1.0, abs(x[k])), k
        ls = one["late_starts"][rt.NAME][a]
        assert ls["ms"] == shadows._ms(prep["times"][300]) and ls["main_eq"] == shadows.START_EQUITY
        parts = [c[(rt.NAME, a)] for c in (c_a, c_b) if (rt.NAME, a) in c]
        assert sum(len(p) for p in parts) == x["stats"]["n"]
        v = view["books"][rt.NAME]["assets"][a]
        assert v["label"] == "NOT passed, paper only" and v["regime_bucket"] == x["mind"]["bucket"]
        assert v["main_equity_at_start"] == shadows.START_EQUITY and v["started_utc"] == ls["utc"]
    assert "NOT passed" in view["books"][rt.NAME]["title"] and "paper only" in view["books"][rt.NAME]["title"]


def test_the_book_is_the_main_rule_and_sizing_on_the_minds_odds(monkeypatch):
    """Hand the mind the engine's own odds: its book must be the fresh main copy's book, trade for trade."""
    prep = planted()

    def own(prep_, assets, r0, n):
        return (dict((a, np.array(prep_["odds"][a][r0:n])) for a in assets),
                dict((a, np.zeros(n - r0, dtype=np.int8)) for a in assets), np.zeros(4, dtype=np.int64))
    monkeypatch.setattr(rt, "odds", own)
    sst = fresh()
    _v, closed = shadows.advance(prep, "crypto", ASSETS, 900, sst, start_lo=300)
    for a in ASSETS:
        mind = dict(sst["books"][rt.NAME][a])
        mind.pop("mind")
        assert mind == sst["books"]["main"][a] and mind["stats"]["n"] > 5
        pd.testing.assert_frame_equal(closed[(rt.NAME, a)], closed[("main", a)])
    assert shadows.CHALLENGERS["main"]["rule"] == {} and shadows.CHALLENGERS["main"]["cfg"] == {}


def test_no_other_book_changes_when_the_mind_runs(monkeypatch):
    prep = planted()
    with_mind, without = fresh(), fresh()
    v1, c1 = shadows.advance(prep, "crypto", ASSETS, 610, with_mind, start_lo=300)
    v1, c1b = shadows.advance(prep, "crypto", ASSETS, 900, with_mind)
    saved = shadows.MINDS.pop(rt.NAME)
    try:
        v2, c2 = shadows.advance(prep, "crypto", ASSETS, 610, without, start_lo=300)
        v2, c2b = shadows.advance(prep, "crypto", ASSETS, 900, without)
    finally:
        shadows.MINDS[rt.NAME] = saved
    assert rt.NAME in with_mind["books"] and rt.NAME not in without["books"]
    for name in list(shadows.CHALLENGERS) + list(shadows.FOLLOWERS):                     # b_targets, the vault's book, too
        assert json.dumps(with_mind["books"].get(name), sort_keys=True) == \
            json.dumps(without["books"].get(name), sort_keys=True), name
        assert json.dumps(v1["books"].get(name), sort_keys=True) == json.dumps(v2["books"].get(name), sort_keys=True)
    for got, want in ((c1, c2), (c1b, c2b)):
        assert set(k for k in got if k[0] != rt.NAME) == set(want)
        for k in want:
            pd.testing.assert_frame_equal(got[k], want[k])
    assert with_mind["groups"] == without["groups"]
    b1, b2 = shadows.scoreboard({"crypto": v1}), shadows.scoreboard({"crypto": v2})
    assert [r for r in b1["rows"] if r["book"] != rt.NAME] == b2["rows"]
    assert rt.NAME not in shadows.CHALLENGERS and rt.NAME not in shadows.FOLLOWERS       # not a rule of run()


def test_a_failure_is_one_log_line_and_the_next_step_catches_up(monkeypatch):
    prep = planted()
    ref, sst, said = fresh(), fresh(), []
    shadows.advance(prep, "crypto", ASSETS, 500, ref, start_lo=300)
    shadows.advance(prep, "crypto", ASSETS, 501, ref)
    shadows.advance(prep, "crypto", ASSETS, 502, ref)
    shadows.advance(prep, "crypto", ASSETS, 500, sst, start_lo=300)
    real = rt.odds
    monkeypatch.setattr(rt, "odds", lambda *a, **k: 1 / 0)
    before = copy.deepcopy(sst["books"][rt.NAME])
    shadows.advance(prep, "crypto", ASSETS, 501, sst, log=said.append)                   # the mind fails: nothing stops
    lines = [s for s in said if "shadow mind" in s]
    assert len(lines) == 1 and rt.NAME in lines[0] and "ZeroDivisionError" in lines[0] and "\n" not in lines[0]
    assert sst["books"][rt.NAME] == before                                               # its book is as it was
    assert sst["groups"]["crypto"]["last_ms"] == shadows._ms(prep["times"][500])         # the other books went on
    assert sst["books"]["b_targets"]["BTCUSDT"]["mark_ms"] == shadows._ms(prep["times"][500])
    monkeypatch.setattr(rt, "odds", real)
    shadows.advance(prep, "crypto", ASSETS, 502, sst, log=said.append)                   # both bars, in order
    for a in ASSETS:
        x, y = sst["books"][rt.NAME][a], ref["books"][rt.NAME][a]
        for k in ("pos", "idle", "why_in", "pending", "stats", "mind"):
            assert x[k] == y[k], k
        assert abs(x["equity_marked"] - y["equity_marked"]) < 1e-6
    for name in shadows.CHALLENGERS:
        assert sst["books"][name] == ref["books"][name], name


def test_one_market_failing_does_not_stop_the_other(monkeypatch):
    prep = planted()
    sst, said = fresh(), []
    real = shadows.book_inputs

    def inputs(prep_, a):
        if a == "ETHUSDT" and said == []:
            raise RuntimeError("planted")
        return real(prep_, a)
    monkeypatch.setattr(shadows, "book_inputs", inputs)
    closed = rt.advance(prep, "crypto", ASSETS, 300, 600, sst, log=said.append)          # the mind alone
    assert list(sst["books"][rt.NAME]) == ["BTCUSDT"] and any("failed on ETHUSDT" in s for s in said)
    assert all(k[1] == "BTCUSDT" for k in closed)


def test_a_prep_without_the_voices_is_skipped_not_raised():
    prep = planted(n=400)
    del prep["probs"]                                                                    # as the older tests' preps
    sst, said = fresh(), []
    view, _ = shadows.advance(prep, "crypto", ASSETS, 400, sst, start_lo=300, log=said.append)
    assert rt.NAME not in sst["books"] and rt.NAME not in view["books"]
    assert len([s for s in said if rt.NAME in s]) == 1
    assert [r["book"] for r in shadows.scoreboard({"crypto": view})["rows"]] == list(shadows.CHALLENGERS) + \
        list(shadows.FOLLOWERS)


# ------------------------------------------------------------------ the scoreboard and the verdict words
def test_the_shadow_scoreboard_row_compares_with_the_main_copy_over_the_same_days():
    prep = planted()
    sst = fresh()
    shadows.advance(prep, "crypto", ASSETS, 500, sst, start_lo=300)                      # the group runs first
    saved_books, saved_late = sst["books"].pop(rt.NAME), sst["late_starts"].pop(rt.NAME)
    assert saved_books and saved_late
    view, _ = shadows.advance(prep, "crypto", ASSETS, 900, sst)                          # the mind joins late, flat
    row = next(r for r in shadows.scoreboard({"crypto": view})["rows"] if r["book"] == rt.NAME)
    assert row["label"] == "NOT passed, paper only" and "NOT passed" in row["title"] and row["assets"] == 2
    main_then = sum(sst["late_starts"][rt.NAME][a]["main_eq"] for a in ASSETS)
    main_now = sum(sst["books"]["main"][a]["equity_marked"] for a in ASSETS)
    mine = sum(sst["books"][rt.NAME][a]["equity_marked"] for a in ASSETS) - 2 * shadows.START_EQUITY
    assert main_then != 2 * shadows.START_EQUITY                                         # main had already traded
    assert abs(row["vs_main_usd"] - (mine - (main_now - main_then))) < 0.02
    assert row["since_utc"] == min(sst["late_starts"][rt.NAME][a]["utc"] for a in ASSETS)
    assert sst["late_starts"][rt.NAME]["BTCUSDT"]["ms"] == shadows._ms(prep["times"][500])


def _state(mind_eq, main_eq, main_then=10000.0):
    return {"books": {rt.NAME: dict((a, {"equity_marked": mind_eq, "eq": mind_eq}) for a in ASSETS),
                      "main": dict((a, {"equity_marked": main_eq, "eq": main_eq}) for a in ASSETS)},
            "late_starts": {rt.NAME: dict((a, {"ms": 1, "utc": "2026-11-25 00:00", "main_eq": main_then})
                                          for a in ASSETS)}}


def test_no_read_before_thirty_closed_trades_then_only_the_registered_words():
    assert rt.MIN_TRADES == 30 == reports.MIN_TRADES and rt.LEVEL_BAND_PTS == 1.0
    early = rt.compare(_state(12000.0, 10000.0), 29)
    assert early["read"] == "no read before 30 closed forward trades (29 of 30)"
    assert not [k for k in early if "return" in k or "difference" in k or k == "sentence"]   # no number, no word
    for mind_eq, main_eq, word, diff in ((10300.0, 10100.0, "ahead of", 2.0), (10000.0, 10100.0, "behind", -1.0),
                                         (10150.0, 10100.0, "level with", 0.5), (10100.0, 10200.0, "behind", -1.0),
                                         (10099.0, 10000.0, "level with", 0.99), (10100.0, 10000.0, "ahead of", 1.0)):
        c = rt.compare(_state(mind_eq, main_eq), 30)
        assert c["read"] == word and c["difference_pts"] == diff and c["markets"] == 2, (mind_eq, main_eq)
        assert word in c["sentence"] and "NOT passed" in c["sentence"] and c["since_utc"] == "2026-11-25 00:00"
        assert c["btc_eth_beside_not_the_rule"]["read"] == word
        for bad in ("passed the", "proven", "works", "edge", "beats"):
            assert bad not in c["sentence"]
    c = rt.compare(_state(10300.0, 10500.0, main_then=10400.0), 41)                      # main since the mind started: +1%
    assert c["main_copy_return_pct"] == 1.0 and c["mind_return_pct"] == 3.0 and c["read"] == "ahead of"
    assert rt.compare({}, 30)["read"].startswith("no read")


def test_the_forward_scoreboard_row_says_not_passed(tmp_path, monkeypatch):
    live_dir = tmp_path / "out" / "live"
    os.makedirs(str(live_dir))
    monkeypatch.setattr(reports, "ROOT", str(tmp_path))
    monkeypatch.setattr(reports, "SCOREBOARD_JSON", str(live_dir / "scoreboard.json"))
    spath = str(tmp_path / "shadow_state.json")
    monkeypatch.setattr(shadows, "STATE_PATH", spath)
    said = []
    out = reports.scoreboard([], log=said.append)                                        # the mind does not exist yet
    assert not [r for r in out["rows"] if r["book"] == rt.NAME]
    with open(spath, "w") as fh:
        json.dump(_state(10300.0, 10100.0), fh)
    out = reports.scoreboard([], log=said.append)                                        # started, no closed trade yet
    row = next(r for r in out["rows"] if r["book"] == rt.NAME)
    assert row["title"].startswith("Shadow") and "NOT passed, paper only" in row["title"] and row["kind"] == "shadow"
    assert row["passed"] is False and row["paper_only"] is True and row["hypothesis"] == "H108"
    assert row["trades"] == 0 and row["vs_main_copy"]["read"].startswith("no read before 30")
    pd.DataFrame({"time_in": ["2026-11-25 00:%02d" % i for i in range(31)], "side": 1,
                  "pnl_usd": np.linspace(-50, 80, 31)}).to_csv(str(live_dir / ("shadow_trades_%s_BTCUSDT.csv" % rt.NAME)),
                                                              index=False)
    out = reports.scoreboard([], log=said.append)
    row = next(r for r in out["rows"] if r["book"] == rt.NAME)
    assert row["trades"] == 31 and row["verdict"].split(":")[0] in ("ahead", "behind", "undecided")
    assert row["vs_main_copy"]["read"] == "ahead of" and row["vs_main_copy"]["difference_pts"] == 2.0
    monkeypatch.setattr(rt, "scoreboard_extra", lambda *a, **k: 1 / 0)                   # a failure: the scoreboard goes on
    out = reports.scoreboard([], log=said.append)
    row = next(r for r in out["rows"] if r["book"] == rt.NAME)
    assert row["title"] == "Shadow: " + rt.NAME and any("regime trust mind" in s for s in said)
