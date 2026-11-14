# -*- coding: utf-8 -*-
"""The engine's own rules, checked on planted data. No network, no real bars.

    py -3 -m pytest tests -q        (from the project folder)
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import backtest, evidence, labels, livefeeds, model, policy  # noqa: E402
from engine15.config import CFG  # noqa: E402


def make_bars(n=30000, seed=1, start="2022-01-01"):
    rng = np.random.RandomState(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.002, n)))
    opn = np.concatenate([[100.0], close[:-1]])
    spread = np.abs(rng.normal(0, 0.001, n)) * close
    vol = rng.uniform(50, 150, n)
    return pd.DataFrame({"open": opn, "high": np.maximum(opn, close) + spread, "low": np.minimum(opn, close) - spread,
                         "close": close, "volume": vol, "taker_buy": vol * rng.uniform(0.3, 0.7, n)},
                        index=pd.date_range(start, periods=n, freq="15min", tz="UTC"))


def test_evidence_never_reads_the_future():
    """Cut the future off: every row the engine had already seen must stay exactly the same."""
    bars = {"BTCUSDT": make_bars(seed=1), "ETHUSDT": make_bars(seed=2)}
    full = evidence.build(bars)
    for cut in (21000, 26011, 29990):
        part = evidence.build(dict((a, df.iloc[:cut]) for a, df in bars.items()))
        for a in bars:
            x_full, _ = evidence.matrix(full[a].iloc[:cut])
            x_part, _ = evidence.matrix(part[a])
            assert np.allclose(x_full, x_part, atol=1e-9, equal_nan=True), "a reading changed when the future was cut at %d" % cut


def test_triple_barrier_grades_planted_paths():
    n = 40
    o = np.full(n, 100.0)
    h, l = o + 0.1, o - 0.1
    h[5] = 103.0            # after the call at bar 2: the upper barrier (102) is touched at bar 5
    l[20] = 97.0            # after the call at bar 15: the lower barrier is touched at bar 20
    y, res = labels.triple_barrier(o, h, l, np.full(n, 2.0), horizon=8)
    assert y[2] == labels.UP and res[2] == 3
    assert y[15] == labels.DOWN and res[15] == 5
    assert y[25] == labels.NEITHER and res[25] == 8
    assert y[n - 3] == labels.UNKNOWN            # the horizon runs past the data: not graded yet


def test_softmax_learns_a_planted_relation():
    rng = np.random.RandomState(3)
    X = rng.normal(size=(4000, 2))
    y = np.where(X[:, 0] + rng.normal(0, 0.5, 4000) > 0, labels.UP, labels.DOWN)
    W = model.fit_softmax(X, y, l2=1.0)
    p = model.predict(W, np.array([[2.0, 0.0], [-2.0, 0.0]]))
    assert p[0, labels.UP] > 0.9 and p[1, labels.DOWN] > 0.9


def test_trust_uses_only_graded_calls():
    """Trust at session s must not move when a grade that arrives AFTER s is changed."""
    rng = np.random.RandomState(4)
    n, V = 600, len(model.VOICE_NAMES)
    probs = {"A": rng.dirichlet(np.ones(3), size=(n, V))}
    y = {"A": rng.randint(0, 3, n).astype(np.int8)}
    res = {"A": np.full(n, 10, dtype=np.int32)}
    t1 = model.trust_path(probs, y, res, CFG)
    y2 = {"A": y["A"].copy()}
    y2["A"][300:] = (y2["A"][300:] + 1) % 3          # calls made from 300 on are graded from 310 on
    t2 = model.trust_path(probs, y2, res, CFG)
    assert np.allclose(t1[:310], t2[:310]) and not np.allclose(t1[310:], t2[310:])
    # every weight is floored, then all are renormalised: the guaranteed minimum is floor / (1 + V * floor)
    # (was floor / 2, which held only while there were fewer than about 55 voices; 59 from think15-v5.1.1)
    fl = CFG["trust_floor"]
    assert np.allclose(t1.sum(axis=1), 1.0) and t1.min() >= fl / (1.0 + V * fl) - 1e-12


def _book(odds, n=3000, seed=5, cfg=CFG, state=None, lo=1, hi=None):
    bars = make_bars(n, seed)
    px = dict((k, bars[k].values) for k in ("open", "high", "low", "close"))
    unit = np.full(n, 1.5)
    return backtest.run_book(px, odds, np.zeros(n, bool), np.zeros(n), unit, cfg, lo, hi or n, state=state), px


def test_mandate_never_idles_more_than_four_sessions():
    rng = np.random.RandomState(6)
    n = 3000
    odds = np.full((n, 3), 1.0 / 3)                  # no side is ever rewarding ...
    odds[:, labels.UP] += rng.normal(0, 0.01, n)     # ... the edge stays far under the 5-point bar
    odds[:, labels.DOWN] = 1 - odds[:, labels.UP] - odds[:, labels.NEITHER]
    book, _ = _book(odds)
    assert backtest.max_flat_run(book["held"], book["act"], 1, n) <= CFG["idle_max"]
    acts = set(backtest.ACTIONS[a] for a in book["act"][1:])
    assert policy.FORCED in acts and policy.IDLE in acts


def test_policy_words():
    assert policy.decide(0, 0, 0.50, 0.40, False, 0.0, CFG)[:2] == (policy.ENTER, 1)
    assert policy.decide(0, 0, 0.40, 0.50, False, 0.0, CFG)[:2] == (policy.ENTER, -1)
    assert policy.decide(0, 0, 0.44, 0.38, True, 0.0, CFG)[0] == policy.IDLE          # 6 pts: not enough in high risk
    assert policy.decide(0, 4, 0.36, 0.38, False, 0.0, CFG)[:2] == (policy.FORCED, -1)
    assert policy.decide(0, 4, 0.36, 0.38, False, 0.8, dict(CFG, trend_tiebreak=True))[:2] == (policy.FORCED, 1)      # no edge: with the trend
    assert policy.decide(0, 4, 0.36, 0.38, False, 0.8, dict(CFG, trend_tiebreak=False))[:2] == (policy.FORCED, -1)


def test_v5_bias_and_release_guard():
    c = dict(CFG, htf_bias=True, release_guard=True, theta_counter=0.15)
    # 10 Nov 13:15, BTC: a 6.1-pt long edge, every timeframe down, CPI at 13:30 -> no entry
    assert policy.decide(0, 0, 0.40, 0.339, False, -0.79, c, bias=-1, guard=True)[0] == policy.IDLE
    # the same edge without the release: still no long against the bias (needs 15 pts)
    assert policy.decide(0, 0, 0.40, 0.339, False, -0.79, c, bias=-1)[0] == policy.IDLE
    assert policy.decide(0, 0, 0.45, 0.29, False, -0.79, c, bias=-1)[:2] == (policy.ENTER, 1)      # 16 pts: allowed
    assert policy.decide(0, 0, 0.30, 0.36, False, -0.79, c, bias=-1)[:2] == (policy.ENTER, -1)     # with the bias: 5 pts
    # 14:45: forced by the mandate with a 0.3-pt long edge -> short, with the bias
    assert policy.decide(0, 4, 0.351, 0.348, False, -0.79, c, bias=-1)[:3] == (policy.FORCED, -1, "mandate_with_bias")
    # holding a long against the bias with less than 5 pts for it -> flip to short
    assert policy.decide(1, 0, 0.35, 0.37, False, -0.79, c, bias=-1)[:3] == (policy.FLIP, -1, "against_htf_bias")
    assert policy.decide(1, 0, 0.40, 0.33, False, -0.79, c, bias=-1)[0] == policy.HOLD                # a real edge for it: keep
    assert policy.decide(1, 0, 0.30, 0.45, False, 0.0, c, guard=True)[:3] == (policy.HOLD, 1, "release_guard_hold")
    assert policy.decide(0, 0, 0.40, 0.339, False, -0.79, dict(c, htf_bias=False))[0] == policy.ENTER  # off: as v4
    assert policy.decide(1, 0, 0.38, 0.44, False, 0.0, CFG)[0] == policy.HOLD          # against, but under the flip bar
    assert policy.decide(1, 0, 0.33, 0.47, False, 0.0, CFG)[:2] == (policy.FLIP, -1)
    assert policy.decide(1, 0, 0.38, 0.44, True, 0.0, dict(CFG, step_aside=True))[:2] == (policy.STEP_ASIDE, 0)
    assert policy.decide(1, 0, 0.38, 0.44, True, 0.0, dict(CFG, step_aside=False))[0] == policy.HOLD
    assert policy.decide(0, 0, None, None, False, 0.0, CFG)[0] == policy.WAIT


def test_accounting_charges_both_sides():
    n = 50
    o = np.full(n, 100.0)
    o[10:] = 110.0
    px = {"open": o, "high": o + 0.01, "low": o - 0.01, "close": o}
    odds = np.full((n, 3), 1.0 / 3)
    odds[:9] = [0.1, 0.6, 0.3]                       # long ...
    odds[9:] = [0.1, 0.2, 0.7]                       # ... then short from the close of bar 9 (filled at 110)
    book = backtest.run_book(px, odds, np.zeros(n, bool), np.zeros(n), np.full(n, 50.0), CFG, 1, n)
    first = book["trades"].iloc[0]
    assert first.side == 1 and first.p_in == 100.0 and first.p_out == 110.0 and first.why_out == policy.FLIP
    assert abs(first.pnl_pct - (10.0 - 0.1 * (100 + 110) / 100)) < 1e-6      # +10% less 0.10% on each side


def test_book_resumes_exactly():
    rng = np.random.RandomState(8)
    n = 2000
    odds = rng.dirichlet(np.ones(3) * 30, size=n)
    whole, _ = _book(odds, n=n)
    a, _ = _book(odds, n=n, hi=1200)
    b, _ = _book(odds, n=n, lo=1200, state=a["state"])
    assert abs(whole["state"]["eq"] - b["state"]["eq"]) < 1e-6
    assert np.array_equal(whole["act"][1200:], b["act"][1200:])


def test_order_book_reads():
    bids = [(100 - 0.01 * k, 1.0) for k in range(1, 300)]
    asks = [(100 + 0.01 * k, 3.0) for k in range(1, 300)]
    reads, profile = livefeeds.book_reads(bids, asks)
    assert reads["ob_imb_2"] < -0.4 and reads["ob_imb_05"] < -0.4      # three times more resting asks than bids
    assert len(profile["bids"]) == livefeeds.BOOK_BINS


def test_owner_view_is_known_only_after_it_is_given(tmp_path):
    from engine15 import owner
    p = str(tmp_path / "views.csv")
    idx = pd.date_range("2026-01-01", periods=200, freq="15min", tz="UTC")
    given = int(idx[50].timestamp() * 1000) + 60000              # one minute into session 50
    owner.tell("BTC", "long", 0.8, hours=10, now_ms=given, path=p)
    f = owner.features(idx, "BTCUSDT", path=p)["owner_view"].values
    assert f[:50].sum() == 0 and f[50] == 0.8                    # session 50 closes after the view was given
    assert f[89] == 0.8 and f[91] == 0                           # and it expires 10 hours later
    assert owner.features(idx, "ETHUSDT", path=p)["owner_view"].abs().sum() == 0


def test_answers_need_the_pin_and_leave_a_trail(tmp_path):
    from engine15 import owner
    views, pinf, trail = str(tmp_path / "v.csv"), str(tmp_path / "pin.json"), str(tmp_path / "audit.jsonl")
    owner.set_pin("7391", pin_file=pinf, audit_path=trail)
    assert "7391" not in open(pinf).read()                       # only a salted hash is kept
    owner.log_question({"question": "Which side?", "time": "2026-11-10 13:30", "asset": "BTCUSDT", "position": "LONG", "edge_pts": 6.3}, trail)
    try:
        owner.submit("0000", "stranger", "BTC", "short", views_path=views, pin_file=pinf, audit_path=trail)
        assert False, "a wrong PIN was accepted"
    except PermissionError:
        pass
    assert len(owner.load(views)) == 0
    owner.submit("7391", "owner", "BTC", "long", 0.7, note="CPI soft", views_path=views, pin_file=pinf, audit_path=trail)
    assert len(owner.load(views)) == 1
    kinds = [r["kind"] for r in owner.read_audit(trail)]
    assert kinds == ["pin_set", "question", "rejected", "answer"]
    assert "7391" not in open(trail).read() and "0000" not in open(trail).read()
    t = owner.trail(path=trail)
    assert t["refused_attempts"] == 1 and t["rows"][0]["question"] == "Which side?" and t["rows"][0]["who"] == "owner"
    for _ in range(owner.MAX_WRONG):
        try:
            owner.submit("1111", "x", "BTC", "short", views_path=views, pin_file=pinf, audit_path=trail)
        except PermissionError:
            pass
    ok, reason = owner.check_pin("7391", pinf, trail)
    assert not ok and reason.startswith("locked")                # even the right PIN waits out the lock


def test_headline_scoring():
    assert livefeeds.score_headline("Bitcoin surges to record high as ETF inflows jump") > 0
    assert livefeeds.score_headline("Exchange hack triggers sell-off, prices plunge") < 0
    assert livefeeds.score_headline("Foundation names new director") == 0


def test_plan_targets():
    from engine15 import live
    row = {"fib_1h_dir": -1.0, "fib_1h_t1_px": 72765.0, "fib_1h_t2_px": 71817.0, "reach_24h_med_pct": 3.3}
    t = live.plan_targets(-1, 73500.0, 74200.0, row)            # short, 700 risk: the 1.272 is 735 away (1.05R)
    assert t["target_1"] == 72765.0 and "1.272" in t["target_1_basis"] and t["target_2"] == 71817.0
    t = live.plan_targets(1, 73500.0, 72800.0, row)             # long: the leg runs the other way -> a day's travel
    assert abs(t["target_1"] - 73500.0 * 1.033) < 1e-6 and t["target_2"] > t["target_1"]
    t = live.plan_targets(1, 100.0, 99.0, {})                   # nothing read: 1.5R and 2R
    assert (t["target_1"], t["target_2"]) == (101.5, 102.25)
    assert live.plan_targets(1, 100.0, None, {}) == {}


def test_leverage_rule():
    from engine15.backtest import leverage
    c = dict(CFG, risk_per_trade=0.02)
    assert leverage(dict(c, leverage_cap=1.0), 100.0, 3.0) == 1.0          # crypto: always 1x
    assert abs(leverage(dict(c, leverage_cap=100.0), 158.76, 0.52) - 0.02 / (0.52 / 158.76)) < 1e-9   # USDJPY ~6.1x
    assert leverage(dict(c, leverage_cap=5.0), 100.0, 0.1) == 5.0          # capped
    assert leverage(dict(c, leverage_cap=5.0), 100.0, 3.0) == 1.0          # never below 1x


def test_late_feed_fills_one_bar_later():
    import numpy as np
    from engine15 import backtest, labels
    n = 12
    c = 100.0 + np.arange(n, dtype=float)
    px = {"open": c, "high": c + 0.2, "low": c - 0.2, "close": c}
    odds = np.tile([0.2, 0.6, 0.2], (n, 1))                     # UP edge on every bar
    z = np.zeros(n)
    b0 = backtest.run_book(px, odds, z.astype(bool), z, np.full(n, 0.5), dict(CFG, step_aside=False), 1, n)
    b1 = backtest.run_book(px, odds, z.astype(bool), z, np.full(n, 0.5), dict(CFG, step_aside=False, fill_delay_bars=1), 1, n)
    first0, first1 = int(np.argmax(b0["held"] == 1)), int(np.argmax(b1["held"] == 1))
    assert first0 == 2 and first1 == 3                            # decided at bar 1's close: fill at bar 2 vs bar 3


def test_risk_budget_shrinks_or_skips_entries():
    import numpy as np
    from engine15 import backtest
    n = 8
    c = np.full(n, 100.0)
    px = {"open": c, "high": c + 0.1, "low": c - 0.1, "close": c}
    odds = np.tile([0.2, 0.6, 0.2], (n, 1)); z = np.zeros(n)
    full = backtest.run_book(px, odds, z.astype(bool), z, np.full(n, 1.0), dict(CFG), 1, n)["state"]["qty"]
    half = backtest.run_book(px, odds, z.astype(bool), z, np.full(n, 1.0), dict(CFG, risk_budget_usd=100.0), 1, n)["state"]["qty"]
    none = backtest.run_book(px, odds, z.astype(bool), z, np.full(n, 1.0), dict(CFG, risk_budget_usd=0.0), 1, n)["state"]["pos"]
    risk_full = full * CFG["stop_units"] * 1.0
    assert abs(half * CFG["stop_units"] - 100.0) < 1e-9 and risk_full > 100.0 and none == 0


def test_risk_budget_reads_other_books():
    from engine15 import live
    st = {"books": {"BTCUSDT": {"pos": -1, "qty": 0.1, "entry": 70000.0, "stop": 72000.0, "eq": 10000.0}}}
    b = live.risk_budget("ETHUSDT", st)
    assert abs(b - (0.10 * 10000.0 * len([a for _, x in live.universes() for a in x]) - 200.0)) < 1e-6
