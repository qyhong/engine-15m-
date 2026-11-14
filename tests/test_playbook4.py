# -*- coding: utf-8 -*-
"""tests for engine15/playbook4.py: the strategy loop's round-2 rules as forward paper books (NOT passed).

1. Reproduction: on a historical slice of the harness's own development data, playbook4's targets, held positions
   and per-bar net returns equal research/harness round 2's (R2.h30(1.5, 0), R2.h31(4.0), core.Market spot) to 1e-12.
2. Over the full development span, stitched to the walk-forward out-of-sample window as round 2 did, the CAGR equals
   the frozen round-2 result in research/out/harness/harness_summary_round2.json (so the parameters are the same).
3. No look-ahead: computing on truncated bars gives the same targets, positions and returns on every earlier bar.
4. Warm-up: starting WARMUP_DAYS before a date gives the same trades afterwards as starting from the beginning
   (sizes and returns equal to 1e-12: pandas' rolling std rounds differently from a different start).
5. The forward book: only trades decided after REGISTERED count; the book is $10,000 flat until then.
Tests 1, 2 and 4 read the stored history and are skipped if it is missing."""
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine15 import playbook4 as p4  # noqa: E402
from engine15.config import CFG  # noqa: E402

TOL = 1e-12
SUMMARY = os.path.join(ROOT, "research", "out", "harness", "harness_summary_round2.json")
LOOP_NAMES = {"p4_h30spot": "H29 H30 1.5x/0x spot longs", "p4_h31trail": "H29 H31 trail 4 ATR spot longs"}


def _harness():
    try:
        from research.harness import core, round2
        return core, round2
    except Exception as e:                                   # pragma: no cover
        pytest.skip("harness not importable: %r" % (e,))


def _dev(asset):
    core, _ = _harness()
    try:
        return core.load(asset, dev_only=True)
    except Exception as e:                                   # pragma: no cover
        pytest.skip("no stored history for %s: %r" % (asset, e))


def _cut(bars, fund, start, end):
    b = bars[(bars.index >= start) & (bars.index < end)]
    lo = int(b.index[0].value // 10**6)
    hi = int(b.index[-1].value // 10**6) + p4.BAR_MS
    s = np.asarray(fund["settle_ms"], dtype="int64")
    return b, fund[(s >= lo) & (s <= hi)]


def synth(n=20000, seed=5, start="2024-01-01"):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=n, freq="15min", tz="UTC", name="open_time")
    drift = np.where((np.arange(n) // 4000) % 2 == 0, 0.0004, -0.0003)
    lr = rng.normal(drift, 0.004, n)
    c = 30000 * np.exp(np.cumsum(lr))
    o = np.concatenate([[c[0]], c[:-1]]) * (1 + rng.normal(0, 0.0003, n))
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.001, n)))
    lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.001, n)))
    bars = pd.DataFrame({"open": o, "high": h, "low": lo, "close": c, "volume": 1.0, "taker_buy": 0.5}, index=idx)
    st = (np.arange(0, n, 32) * p4.BAR_MS + int(idx[0].value // 10**6)).astype("int64")
    fund = pd.DataFrame({"rate": rng.normal(0.0001, 0.0001, len(st)), "settle_ms": st},
                        index=pd.to_datetime(st, unit="ms", utc=True))
    return bars, fund


def test_parameters_are_round2_and_fee_is_the_engine_crypto_fee():
    _, round2 = _harness()
    assert (p4.H30_U, p4.H30_D) in round2.H30_KEYS
    assert p4.H31_M in round2.H31_KEYS
    core, _ = _harness()
    assert p4.FEE == core.FEE_HEAD == float(CFG.get("asset_cost", {}).get("BTCUSDT", CFG["cost_side"]))
    assert p4.HALF_SPREAD_BPS == core.COST_KW["half_spread_bps"] and p4.SLIP_COEF == core.COST_KW["slippage_coef"]
    assert p4.SLIP_WIN == core.COST_KW["slippage_vol_window"] and p4.BPY == core.BPY
    assert p4.ASSETS == ("BTCUSDT", "ETHUSDT")
    for b in p4.BOOKS.values():
        assert "NOT passed" in b["title"] and "NOT passed" in b["scoreboard_title"]


@pytest.mark.parametrize("asset", ["BTCUSDT", "ETHUSDT"])
def test_reproduces_harness_round2_on_a_historical_slice(asset):
    core, round2 = _harness()
    bars, fund = _dev(asset)
    b, f = _cut(bars, fund, "2021-06-01", "2023-06-01")
    feats = core.features(b)
    ex = round2.extra_features(b, feats)
    r2 = round2.R2(b, feats, ex)
    mkt = core.Market(b, f)
    _, _, R = p4.compute(b, f)
    for book, tgt in (("p4_h30spot", r2.h30(1.5, 0.0)), ("p4_h31trail", r2.h31(4.0))):
        fr = mkt.frame(tgt, core.FEE_HEAD, True)
        mine = R[book]
        assert np.max(np.abs(mine["target"] - tgt)) <= TOL
        assert np.max(np.abs(mine["frame"]["pos"] - fr["pos"].values)) <= TOL
        assert np.max(np.abs(mine["frame"]["r_net"] - fr["r_net"].values)) <= TOL
        assert np.count_nonzero(np.diff(fr["pos"].values)) > 20          # the slice really trades


@pytest.mark.parametrize("asset", ["BTCUSDT", "ETHUSDT"])
def test_full_development_span_matches_frozen_round2_cagr(asset):
    if not os.path.exists(SUMMARY):
        pytest.skip("no round-2 summary")
    core, _ = _harness()
    from engine15.rl import metrics, walkforward
    bars, fund = _dev(asset)
    wins = core.windows(bars.index)
    oos = walkforward.oos_mask(bars.index, wins)
    F, M, R = p4.compute(bars, fund)
    with open(SUMMARY, encoding="utf-8") as fh:
        S = json.load(fh)["results"][asset]["strategies"]
    for book, name in LOOP_NAMES.items():
        r = p4.frame(np.where(oos, R[book]["target"], 0.0), M)["r_net"]
        want = S[name]["res"]["fee_0.10%"]["cagr"]
        assert abs(metrics.cagr(r[oos]) - want) <= 1e-9, (book, metrics.cagr(r[oos]), want)


def test_no_lookahead_truncation():
    bars, fund = synth()
    _, _, full = p4.compute(bars, fund)
    for k in (9000, 13457, 19999):
        b = bars.iloc[:k]
        lim = int(b.index[-1].value // 10**6) + p4.BAR_MS
        _, _, part = p4.compute(b, fund[fund["settle_ms"] <= lim])
        for book in p4.BOOKS:
            assert np.array_equal(part[book]["target"], full[book]["target"][:k])
            assert np.array_equal(part[book]["frame"]["pos"], full[book]["frame"]["pos"][:k])
            # the last bar is marked at its close (no next open yet); every earlier bar is identical
            assert np.max(np.abs(part[book]["frame"]["r_net"][:k - 1] - full[book]["frame"]["r_net"][:k - 1])) <= TOL
    assert np.count_nonzero(np.diff(full["p4_h30spot"]["frame"]["pos"])) > 4
    assert np.count_nonzero(np.diff(full["p4_h31trail"]["frame"]["pos"])) > 4


def test_step_rows_do_not_change_when_later_bars_arrive(monkeypatch):
    bars, fund = synth(n=20000, start="2025-08-01")
    monkeypatch.setattr(p4, "REGISTERED", "2025-09-15 00:00")
    monkeypatch.setattr(p4, "WARMUP_DAYS", 30)
    ms = p4._to_ms(bars.index) + p4.BAR_MS
    full = p4.step({"BTCUSDT": bars}, funding={"BTCUSDT": fund})
    cut_ms = int(ms[15000])
    part = p4.step({"BTCUSDT": bars}, now_ms=cut_ms, funding={"BTCUSDT": fund})
    closed_part = [r for r in part if r["status"] == "CLOSED"]
    closed_full = [r for r in full if r["status"] == "CLOSED" and r["exit_utc"] <= closed_part[-1]["exit_utc"]]
    assert closed_part and closed_part == closed_full
    for r in full:
        assert r["setup_utc"] > "2025-09-15 00:00"                    # only trades decided after registration


def test_forward_book_flat_until_registration_and_counts_only_later_decisions():
    bars, fund = synth(n=30000)
    F, M, R = p4.compute(bars, fund)
    for at in (7000, 10000):                                           # 10000 falls inside a run decided earlier
        rms = int(F["close_ms"][at])
        for book, T in R.items():
            trades, fb, eq = p4.forward_book(T, F, M, rms)
            first = trades[0]["s"]
            assert np.all(eq[:first] == p4.STAKE)                      # flat $10,000 until the first forward entry
            assert all(F["close_ms"][t["s"] - 1] > rms for t in trades)
            pre = [r for r in p4.runs(T["frame"]["pos"]) if r[0] > 0 and F["close_ms"][r[0] - 1] <= rms]
            assert pre                                                 # warm-up runs exist and are excluded whole
            assert all(np.all(fb["pos"][s:e + 1] == 0) for s, e in pre)
            closed = [t for t in trades if t["closed"]]
            assert closed
            last = closed[-1]["x"]
            assert abs(sum(t["pnl"] for t in closed) - (eq[last] - p4.STAKE)) < 1e-6   # trade P&L sums to equity
            for t in closed:                                           # inside forward runs: the rule's returns
                seg = slice(t["s"], t["x"] + 1)
                assert np.max(np.abs(fb["r_net"][seg] - T["frame"]["r_net"][seg])) <= TOL
        assert any(s <= at < e for s, e in p4.runs(R["p4_h30spot"]["frame"]["pos"])) == (at == 10000)


@pytest.mark.parametrize("asset", ["ETHUSDT"])
def test_warmup_anchor_gives_the_same_positions(asset):
    bars, fund = _dev(asset)
    _, _, full = p4.compute(bars, fund)
    day = pd.Timestamp("2024-06-01", tz="UTC")
    b, f = _cut(bars, fund, day - pd.Timedelta(days=p4.WARMUP_DAYS), "2025-11-11")
    _, _, part = p4.compute(b, f)
    sel = np.asarray(bars.index >= b.index[0]) & np.asarray(bars.index < "2025-11-11")
    after = np.asarray(b.index >= day)
    for book in p4.BOOKS:
        pa, pf = part[book]["frame"]["pos"][after], full[book]["frame"]["pos"][sel][after]
        assert np.array_equal(pa == 0, pf == 0)                        # same trades, bar for bar
        assert np.max(np.abs(pa - pf)) <= TOL                          # sizes equal up to rolling-std rounding
        assert np.max(np.abs(part[book]["frame"]["r_net"][after][:-1] - full[book]["frame"]["r_net"][sel][after][:-1])) <= TOL


def test_page_block_shape_and_labels():
    bars, fund = synth(n=20000, start="2025-08-01")
    old = p4.REGISTERED
    try:
        p4.REGISTERED = "2025-09-15 00:00"
        rows = p4.step({"BTCUSDT": bars, "ETHUSDT": bars}, funding={"BTCUSDT": fund, "ETHUSDT": fund})
        pb = p4.page_block(rows)
    finally:
        p4.REGISTERED = old
    assert set(pb) == set(p4.BOOKS)
    for book, b in pb.items():
        assert "NOT passed" in b["title"] and b["not_passed"] is True
        assert b["rule"].startswith(p4.NOT_PASSED) and "spot" in b["note"] and "perps" in b["note"]
        assert set(b["books"]) == {"BTCUSDT", "ETHUSDT"}
        assert b["totals"]["trades"] == len([r for r in rows if r["book"] == book and r["status"] == "CLOSED"])
        for r in rows:
            assert r["side"] == 1 and r["status"] in ("WAITING", "OPEN", "CLOSED")
    json.dumps(pb)
