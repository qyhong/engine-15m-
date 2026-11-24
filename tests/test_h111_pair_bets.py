# -*- coding: utf-8 -*-
"""H111 (research/h111_pair_bets.py): the arithmetic on trades, on made-up trades. No store, no engine run."""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "research"))

import h111_pair_bets as h  # noqa: E402

B = h.BAR_MS


def T(market, t_in, t_out, side, why="STOP", pnl=-100.0, eq_after=9900.0):
    return {"market": market, "t_in_ms": t_in * B, "t_out_ms": t_out * B, "side": side, "why_out": why, "pnl_usd": pnl,
            "equity": eq_after, "r_mult": pnl / 100.0}


def frame(rows):
    return h.add_points(pd.DataFrame(rows))


def test_points_are_percent_of_the_equity_before_the_trade():
    tr = frame([T("BTCUSDT", 0, 4, 1, pnl=-200.0, eq_after=9800.0), T("BTCUSDT", 5, 9, 1, "T1+T2", pnl=490.0, eq_after=10290.0)])
    assert np.allclose(tr.pts.values, [-2.0, 5.0])


def test_unknown_exit_word_stops_the_study():
    try:
        frame([T("BTCUSDT", 0, 4, 1, "MYSTERY")])
    except RuntimeError:
        return
    raise AssertionError("an unknown exit word must stop the study")


def test_v1_halves_only_the_later_trade_on_the_same_side():
    tr = frame([T("BTCUSDT", 0, 10, -1), T("ETHUSDT", 3, 12, -1),          # ETH opens while BTC is short: ETH half
                T("BTCUSDT", 20, 30, 1), T("ETHUSDT", 22, 28, -1),         # other side: full
                T("XAUUSD", 3, 12, -1), T("USDJPY", 3, 12, -1)])           # not a partner of BTC: full
    assert list(h.v1_weights(tr)) == [1.0, 0.5, 1.0, 1.0, 1.0, 1.0]


def test_v1_tie_both_half_and_strict_both_full():
    tr = frame([T("WTI", 5, 10, 1), T("BRENT", 5, 11, 1)])
    assert list(h.v1_weights(tr, True)) == [0.5, 0.5]
    assert list(h.v1_weights(tr, False)) == [1.0, 1.0]


def test_v1_open_to_the_bar():
    # the partner stopped INSIDE bar 10: still open at bar 10's open -> half; entered one bar later -> full
    tr = frame([T("XAUUSD", 0, 10, 1, "STOP"), T("XAGUSD", 10, 15, 1), T("XAUUSD", 20, 30, 1, "STOP"), T("XAGUSD", 31, 35, 1)])
    assert list(h.v1_weights(tr)) == [1.0, 0.5, 1.0, 1.0]
    # the partner left by a FLIP at bar 10's open: already closed at that moment -> full
    tr = frame([T("XAUUSD", 0, 10, 1, "FLIP"), T("XAGUSD", 10, 15, 1), T("XAUUSD", 20, 30, 1, "T1+FLIP"), T("XAGUSD", 30, 35, 1)])
    assert list(h.v1_weights(tr)) == [1.0, 1.0, 1.0, 1.0]


def test_v2_drops_the_fifth_on_one_side_and_counts_only_kept_trades():
    rows = [T(m, i, 100, -1) for i, m in enumerate(["BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD"])]
    rows += [T("USDJPY", 10, 50, -1),       # the 5th short: dropped
             T("SPX", 11, 50, 1),           # a long: kept
             T("WTI", 12, 50, -1),          # still four kept shorts open (USDJPY was dropped): dropped
             T("BRENT", 101, 120, -1)]      # the four were stopped inside bar 100: closed by bar 101: kept
    keep = h.v2_keep(frame(rows))
    assert list(keep) == [True, True, True, True, False, True, False, True]


def test_v2_ties_follow_the_fixed_order():
    rows = [T(m, 0, 50, 1) for m in ["BRENT", "WTI", "SPX", "USDJPY", "XAGUSD", "XAUUSD"]]
    keep = h.v2_keep(frame(rows))                     # order XAU, XAG, JPY, SPX kept; WTI is the 5th, Brent the 6th
    assert dict(zip([r["market"] for r in rows], keep)) == {"BRENT": False, "WTI": False, "SPX": True, "USDJPY": True,
                                                            "XAGUSD": True, "XAUUSD": True}


def test_measures_worst_fall_starts_from_zero():
    m = h.measures([-1.0, 2.0, -3.0, 1.0, 4.0])
    assert m["total"] == 3.0 and m["worst_day"] == -3.0 and m["worst_fall"] == 3.0 and m["ratio"] == 1.0
    assert h.measures([-2.0, -1.0, 5.0])["worst_fall"] == 3.0          # a fall from the starting zero counts
    assert h.measures([1.0, 2.0])["ratio"] is None                     # no fall: no ratio
    half = h.measures(np.array([-1.0, 2.0, -3.0, 1.0, 4.0]) * 0.5)
    assert abs(half["ratio"] - m["ratio"]) < 1e-12                     # betting less does not change the ratio


def test_verdict_needs_a_total_above_zero_in_each_leg():
    seg = lambda total, fall: {"total": total, "worst_fall": fall, "ratio": total / fall}   # noqa: E731
    v0 = {"all": seg(10, 10), "h1": seg(5, 5), "h2": seg(-4, 8), "holdout": seg(3, 6)}
    v1 = {"all": seg(9, 6), "h1": seg(5, 4), "h2": seg(-3, 9), "holdout": seg(3, 5)}
    v = h.verdict(v0, v1)
    assert v["legs"] == {"h1": True, "h2": False, "holdout": True, "total_kept": True} and not v["pass"]
    assert v["brief_wording"]["h2"] is True and v["brief_wording_pass"]
    v1["all"] = seg(8, 6)
    assert h.verdict(v0, v1)["legs"]["total_kept"] is False


def test_segments_do_not_overlap_and_cover_every_day():
    day = lambda s: int(pd.Timestamp(s, tz="UTC").value // (h.DAY_MS * 10 ** 6))   # noqa: E731
    d0, d1 = day("2020-02-05"), day("2026-11-24")
    segs = h.seg_days(d0, d1)
    days = np.arange(d0, d1 + 1)
    lab = h.seg_of_day(days, segs)
    assert (lab != "").all()
    assert lab[days == day("2023-06-07")][0] == "h1" and lab[days == day("2023-06-08")][0] == "h2"
    assert lab[days == day("2025-11-10")][0] == "h2" and lab[days == day("2025-11-11")][0] == "holdout"
    assert lab[days == day("2026-11-10")][0] == "holdout" and lab[days == day("2026-11-11")][0] == "forward"


def test_analyse_runs_end_to_end_and_v1_never_changes_an_unpaired_market():
    rng = np.random.default_rng(1)
    rows, meta = [], {}
    day0 = int(pd.Timestamp("2023-05-01", tz="UTC").value // 10 ** 6) // B
    for m in h.ORDER:
        t, eq = day0, 10000.0
        for _ in range(60):
            dur = int(rng.integers(4, 200))
            pnl = float(rng.normal(0, 150))
            eq += pnl
            rows.append(T(m, t, t + dur, int(rng.choice([-1, 1])), str(rng.choice(["STOP", "T1+T2", "T1+STOP_BE", "FLIP"])), pnl, eq))
            t += dur + 1 + int(rng.integers(0, 3))        # a new trade never opens in the bar the last one was stopped in
        meta[m] = {"first_ms": day0 * B, "last_ms": (t + 5) * B, "open_side": 0, "open_t_in_ms": None, "end_equity": eq}
    last = max(v["last_ms"] for v in meta.values())
    for v in meta.values():
        v["last_ms"] = last
    res, tr = h.analyse(pd.DataFrame(rows), meta, draws=20)
    assert (tr.w_v1[tr.market.isin(["USDJPY", "SPX"])] == 1).all()
    assert abs(res["variants"]["V0"]["all"]["total"] - tr.pts.sum()) < 1e-9
    assert abs(sum(res["variants"]["V0"][k]["total"] for k in ("h1", "h2", "holdout", "forward")) - tr.pts.sum()) < 1e-9
    assert abs(sum(res["same_side"]["segments"]["all"]["most_pct"]) - 100) < 1e-6
    assert set(res["verdict"]["legs"]) == {"h1", "h2", "holdout", "total_kept"}
    assert (tr.w_v1 <= tr.w_v1s).all()
    h.write_report(res, str(os.environ.get("H111_TEST_OUT") or __import__("tempfile").mkdtemp()))
