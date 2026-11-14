# -*- coding: utf-8 -*-
"""The two strategy books (engine15/playbook.py) on hand-made bars. No network, no real bars."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import playbook as pb  # noqa: E402

P1_RULE = {"k": 0.25, "m": 0, "exit": "fixed", "confirm": None}
P2_RULE = {"level": "pday", "j": 2, "exit": "fixed", "filter": None}


def quiet(n, start="2024-01-01", base=100.0):
    """n bars wobbling +/- 0.3 around base: a calm range with a known high near base + 0.4."""
    c = base + 0.3 * np.sin(np.arange(n) / 3.0)
    o = np.concatenate([[c[0]], c[:-1]])
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) + 0.1, "low": np.minimum(o, c) - 0.1, "close": c,
                         "volume": 100.0, "taker_buy": 50.0},
                        index=pd.date_range(start, periods=n, freq="15min", tz="UTC"))


def put(df, i, o, h, l, c, v=100.0):
    df.iloc[i, :5] = [o, h, l, c, v]


def walk(n, seed=1):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    o = np.concatenate([[c[0]], c[:-1]])
    w = np.abs(rng.normal(0, 0.002, n)) * c
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) + w, "low": np.minimum(o, c) - w, "close": c,
                         "volume": rng.uniform(50, 150, n), "taker_buy": rng.uniform(20, 80, n)},
                        index=pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC"))


# ---------------------------------------------------------------- P1 liquidation hunt
def test_sweep_and_reclaim_fires_a_short():
    df = quiet(300)
    x = 250
    put(df, x, 100.2, 101.6, 100.1, 100.3)                 # spikes far above the 24h high and closes back below
    P = pb.prepare(df, "TEST")
    sigs = [s for s in pb.p1_signals(P, P1_RULE) if s["i_dec"] == x]
    assert len(sigs) == 1 and sigs[0]["side"] == -1
    s = sigs[0]
    assert s["wick_pct"] >= 50 and s["level"] < 101.6
    assert abs(s["stop"] - (101.6 + 0.1 * P["atr"][x])) < 1e-9
    assert "Liquidation hunt" in pb.sentence(dict(pb.simulate(P, [s], "fixed", 16, 0.001)[0]), P)


def test_sweep_that_closes_beyond_does_not_fire():
    df = quiet(300)
    x = 250
    put(df, x, 100.2, 101.6, 100.1, 101.5)                 # closes beyond every pool: a breakout, not a hunt
    for i in range(x + 1, 300):                            # and keeps going up
        put(df, i, 101.5 + 0.1 * (i - x - 1), 101.7 + 0.1 * (i - x), 101.4 + 0.1 * (i - x - 1), 101.6 + 0.1 * (i - x))
    P = pb.prepare(df, "TEST")
    assert not [s for s in pb.p1_signals(P, P1_RULE) if x <= s["i_dec"] <= x + 3]
    # with m = 2, the same bars do not fire either: no close came back below the pool
    assert not [s for s in pb.p1_signals(P, dict(P1_RULE, m=2)) if s["side"] < 0 and x <= s["i_dec"] <= x + 3]


def test_reclaim_within_two_bars_needs_m2():
    df = quiet(300)
    x = 250
    put(df, x, 100.2, 100.95, 100.1, 100.7)                # closes above the 24h high (about 100.5), below 101 ...
    put(df, x + 1, 100.7, 100.75, 100.1, 100.15)           # ... and back below it on the next bar
    P = pb.prepare(df, "TEST")
    assert not [s for s in pb.p1_signals(P, P1_RULE) if s["side"] < 0 and s["i_dec"] in (x, x + 1)]
    got = [s for s in pb.p1_signals(P, dict(P1_RULE, m=2)) if s["side"] < 0 and s["i_dec"] == x + 1]
    assert len(got) == 1 and got[0]["i_start"] == x and got[0]["extreme"] == 100.95 and got[0]["pool"] in ("24h high", "7-day high", "swing high")


# ---------------------------------------------------------------- P2 breakout trap
def two_days():
    df = quiet(192 + 60)                                   # day 1 and part of day 2
    return df


def test_failed_breakout_fires_a_short():
    df = two_days()
    pdh = df["high"].iloc[:96].max()
    b = 96 + 30
    put(df, b, 100.2, pdh + 0.6, 100.1, pdh + 0.5)         # closes above the prior-day high: buyers are in
    put(df, b + 1, pdh + 0.5, pdh + 0.55, 99.9, 100.0)     # back inside on the next bar: trapped
    P = pb.prepare(df, "TEST")
    sigs = [s for s in pb.p2_signals(P, P2_RULE) if s["i_dec"] == b + 1]
    assert len(sigs) == 1 and sigs[0]["side"] == -1 and sigs[0]["i_start"] == b
    assert abs(sigs[0]["level"] - pdh) < 1e-9
    assert abs(sigs[0]["stop"] - (pdh + 0.6 + 0.1 * P["atr"][b + 1])) < 1e-9


def test_held_breakout_does_not_fire():
    df = two_days()
    pdh = df["high"].iloc[:96].max()
    b = 96 + 30
    put(df, b, 100.2, pdh + 0.6, 100.1, pdh + 0.5)
    for i in range(b + 1, b + 8):                          # holds above the level
        put(df, i, pdh + 0.5, pdh + 0.7, pdh + 0.3, pdh + 0.55)
    P = pb.prepare(df, "TEST")
    assert not [s for s in pb.p2_signals(P, P2_RULE) if b < s["i_dec"] <= b + 4 and s["side"] < 0]


def test_too_late_back_inside_does_not_fire_with_j2():
    df = two_days()
    pdh = df["high"].iloc[:96].max()
    b = 96 + 30
    put(df, b, 100.2, pdh + 0.6, 100.1, pdh + 0.5)
    put(df, b + 1, pdh + 0.5, pdh + 0.6, pdh + 0.3, pdh + 0.4)
    put(df, b + 2, pdh + 0.4, pdh + 0.5, pdh + 0.2, pdh + 0.3)
    put(df, b + 3, pdh + 0.3, pdh + 0.35, 99.9, 100.0)     # back inside on the third bar
    P = pb.prepare(df, "TEST")
    assert not [s for s in pb.p2_signals(P, P2_RULE) if s["side"] < 0 and s["i_dec"] == b + 3]
    assert [s for s in pb.p2_signals(P, dict(P2_RULE, j=4)) if s["side"] < 0 and s["i_dec"] == b + 3]


# ---------------------------------------------------------------- the paper trade
def _sig(i, side, stop):
    return {"book": "p1_liqhunt", "i_dec": i, "i_start": i, "side": side, "stop": stop, "pool": "24h high", "level": 101.0,
            "extreme": stop, "wick_pct": 60.0, "vratio": float("nan"), "taker_share": float("nan"), "fund_rank": float("nan"),
            "t1_cands": [("VWAP", 99.0)], "t2_cand": ("24h low", 98.0)}


def test_stop_first_when_stop_and_target_in_one_bar():
    df = quiet(60)
    i = 40
    put(df, i + 1, 100.0, 100.0, 100.0, 100.0)             # entry bar: opens at 100, goes nowhere
    put(df, i + 2, 100.0, 101.2, 98.5, 99.0)               # touches the stop (101) AND both targets (99, 98)
    P = pb.prepare(df, "TEST")
    t = pb.simulate(P, [_sig(i, -1, 101.0)], "fixed", 16, 0.001)[0]
    assert t["status"] == "CLOSED" and t["why_out"] == "STOP" and t["exit"] == 101.0 and not t["t1_hit"]
    assert t["exit_bar"] == i + 2


def test_gap_through_stop_fills_at_open_and_gap_at_entry_skips():
    df = quiet(60)
    i = 40
    put(df, i + 1, 100.0, 100.0, 100.0, 100.0)
    put(df, i + 2, 101.5, 101.6, 101.4, 101.5)             # opens beyond the stop
    P = pb.prepare(df, "TEST")
    t = pb.simulate(P, [_sig(i, -1, 101.0)], "fixed", 16, 0.001)[0]
    assert t["why_out"] == "STOP" and t["exit"] == 101.5
    put(df, i + 1, 101.2, 101.3, 101.1, 101.2)             # the entry open itself is beyond the stop: no trade
    P = pb.prepare(df, "TEST")
    assert pb.simulate(P, [_sig(i, -1, 101.0)], "fixed", 16, 0.001) == []


def test_fees_and_partial_exits():
    df = quiet(80)
    i = 40
    for j in range(i + 1, 80):
        put(df, j, 100.0, 100.0, 100.0, 100.0)             # flat: the trade times out at its entry price
    P = pb.prepare(df, "TEST")
    for fee in (0.001, 0.0002):
        t = pb.simulate(P, [_sig(i, -1, 101.0)], "fixed", 16, fee)[0]
        assert t["why_out"] == "TIME" and t["exit"] == 100.0
        assert abs(t["fees_usd"] - 2 * fee * pb.STAKE) < 1e-9
        assert abs(t["pnl_usd"] + 2 * fee * pb.STAKE) < 1e-9
        assert abs(t["r"] - t["pnl_usd"] / (pb.STAKE * 1.0 / 100.0)) < 1e-9
    assert pb.fee_side("BTCUSDT") == 0.001 and pb.fee_side("XAUUSD") == 0.0002
    # half at 1R (99), the rest at 2R (98): +1.5R before fees
    put(df, i + 2, 100.0, 100.0, 97.9, 98.0)
    P = pb.prepare(df, "TEST")
    t = pb.simulate(P, [_sig(i, -1, 101.0)], "fixed", 16, 0.001)[0]
    assert t["why_out"] == "T2" and t["t1_hit"] and abs(t["exit"] - 98.5) < 1e-9
    assert abs(t["gross_usd"] - 150.0) < 1e-6
    # after Target 1 the stop sits at the entry from the next bar
    put(df, i + 2, 100.0, 100.0, 98.9, 99.0)
    put(df, i + 3, 99.0, 100.1, 99.0, 100.0)
    P = pb.prepare(df, "TEST")
    t = pb.simulate(P, [_sig(i, -1, 101.0)], "fixed", 16, 0.001)[0]
    assert t["why_out"] == "STOP" and t["t1_hit"] and abs(t["exit"] - 99.5) < 1e-9


def test_one_trade_at_a_time():
    df = quiet(80)
    for j in range(41, 80):
        put(df, j, 100.0, 100.0, 100.0, 100.0)
    P = pb.prepare(df, "TEST")
    tr = pb.simulate(P, [_sig(40, -1, 101.0), _sig(45, -1, 101.0), _sig(57, -1, 101.0)], "fixed", 16, 0.001)
    assert [t["i_dec"] for t in tr] == [40, 57]            # 45 came while the first trade was open (exit at bar 57's open)


# ---------------------------------------------------------------- no look-ahead
def test_no_lookahead_signals_and_levels():
    df = walk(3000)
    full = pb.prepare(df, "TEST")
    rules = [("p1_liqhunt", dict(P1_RULE, m=2)), ("p1_liqhunt", P1_RULE), ("p2_trap", P2_RULE),
             ("p2_trap", {"level": "swing", "j": 4, "exit": "struct", "filter": None}),
             ("p2_trap", {"level": "n48", "j": 4, "exit": "struct", "filter": None})]
    want = dict((i, pb.signals(b, full, r)) for i, (b, r) in enumerate(rules))
    for cut in (1500, 2222, 2999):
        P = pb.prepare(df.iloc[:cut], "TEST")
        for key in ("sw_hi", "sw_lo", "hi24", "lo7d", "pdh", "pdl", "rup", "n48_hi", "vwap", "vratio", "atr"):
            a, b = P[key], full[key][:cut]
            assert np.array_equal(np.isnan(a), np.isnan(b)) and np.allclose(a[~np.isnan(a)], b[~np.isnan(b)]), key
        for i, (b, r) in enumerate(rules):
            got = [(s["i_dec"], s["side"], round(s["stop"], 9)) for s in pb.signals(b, P, r)]
            exp = [(s["i_dec"], s["side"], round(s["stop"], 9)) for s in want[i] if s["i_dec"] < cut]
            assert got == exp
        # trades closed in the truncated run are the same trades in the full run
        for b, r in rules:
            fullt = set((t["entry_ms"], t["exit_ms"], round(t["r"], 9)) for t in pb.simulate(full, pb.signals(b, full, r), r["exit"], 16, 0.001)
                        if t["status"] == "CLOSED")
            for t in pb.simulate(P, pb.signals(b, P, r), r["exit"], 16, 0.001):
                if t["status"] == "CLOSED":
                    assert (t["entry_ms"], t["exit_ms"], round(t["r"], 9)) in fullt


def test_pools_are_known_before_the_bar():
    df = quiet(300)
    x = 250
    put(df, x, 100.2, 105.0, 100.1, 104.0)
    P = pb.prepare(df, "TEST")
    assert P["hi24"][x] < 101.0 and P["hi24"][x + 1] == 105.0   # the spike is a pool only for the bars after it
    assert not (P["sw_hi"][x:x + pb.SWING_K + 1] == 105.0).any()  # a swing is known only SWING_K bars later
    assert P["sw_hi"][x + pb.SWING_K + 1] == 105.0


# ---------------------------------------------------------------- the live interface
def test_step_rows_and_page_block():
    df = quiet(96 * 30, start="2026-10-20")
    x = int(np.searchsorted(df.index, pd.Timestamp("2026-11-12 10:00", tz="UTC")))
    put(df, x, 100.2, 101.6, 100.1, 100.3)
    rows = pb.step({"XAUUSD": df})
    assert rows and all(r["book"] in pb.BOOKS for r in rows)
    need = ("book", "asset", "status", "side", "setup_utc", "entry_utc", "entry", "stop", "target_1", "target_2",
            "exit_utc", "exit", "why_out", "r", "pnl_usd", "fees_usd", "text")
    for r in rows:
        assert all(k in r for k in need)
        assert r["status"] in ("WAITING", "OPEN", "CLOSED") and r["setup_utc"] >= pb.REGISTERED
    assert any(r["setup_utc"] == "2026-11-12 10:15" and r["side"] == -1 for r in rows)
    assert pb.step({"XAUUSD": df}) == rows                       # stateless and deterministic
    early = pb.step({"XAUUSD": df}, now_ms=int(pd.Timestamp("2026-11-12 10:15", tz="UTC").value // 10**6))
    assert all(r["setup_utc"] <= "2026-11-12 10:15" for r in early)
    w = [r for r in early if r["setup_utc"] == "2026-11-12 10:15"]
    assert w and w[0]["status"] == "WAITING" and w[0]["entry"] is None
    blk = pb.page_block(rows)
    assert set(blk) == set(pb.BOOKS)
    for b in blk.values():
        assert {"title", "hypothesis", "open", "recent", "totals"} <= set(b) and len(b["recent"]) <= 5
