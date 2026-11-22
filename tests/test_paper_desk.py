# -*- coding: utf-8 -*-
"""The paper desk (engine15/paper_desk.py; owner, 22 Nov 2026): three forward paper wallets on the Setups book's BTC and
ETH trades. Its walk must be H63's walk; its block is read only and never needs a file to exist. No network.

    py -3 -m pytest tests/test_paper_desk.py -q
"""
import csv
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import h62_setups_wide_stop as h62  # noqa: E402
import h63_member_wallet as h63  # noqa: E402
from engine15 import paper_desk as desk  # noqa: E402
from engine15 import reports, shadows  # noqa: E402
from engine15.config import CFG  # noqa: E402
from test_shadows import random_inputs  # noqa: E402

B, E = desk.COINS
BAR = desk.BAR_MS
T0 = desk.START_MS


def test_the_desk_is_h63s_three_sizings_and_rules():
    assert list(desk.SIZINGS) == list(h63.SIZINGS) == ["S1", "S2", "S3"]
    for k in desk.SIZINGS:
        a, b = dict(desk.SIZINGS[k]), dict(h63.SIZINGS[k])
        a.pop("title"), b.pop("title")
        assert a == b
    assert (desk.MAINT, desk.UP, desk.DOWN, desk.START_W, desk.PART) == (h63.MAINT, h63.UP, h63.DOWN, h63.START_W, h63.PART)
    assert desk.IN_BAR == h63.IN_BAR and desk.BOOK == "b_targets" and desk.START_MS % BAR == 0


@pytest.mark.parametrize("seed", [3, 11])
def test_the_desks_walk_gives_h63s_numbers(seed):
    # two "coins" from two random books, one wallet, every sizing, with funding and finish lines off and on
    books, px = {}, {}
    for coin, sd in ((B, seed), (E, seed + 100)):
        p, odds, unit, shock, tide, bias, guard, aux = random_inputs(seed=sd)
        n = len(p["close"])
        row_of = lambda k, aux=aux: aux["targets"].iloc[k]                                       # noqa: E731
        books[coin] = (h62.run_setups(p, odds, shock, tide, unit, CFG, 1, n, bias=bias, guard=guard,
                                      times_ms=np.arange(n, dtype="int64") * BAR, row_of=row_of), row_of)
        px[coin] = p
    setups = []
    for coin in (B, E):
        setups += h63.setups_of_book(coin, books[coin][0], px[coin], books[coin][1], last=n - 1)
    setups.sort(key=lambda s: (s["i_in"], desk.ORDER[s["coin"]]))
    times = pd.date_range("2026-01-01", periods=n, freq="15min", tz="UTC")
    tms = np.asarray(times.as_unit("ms").asi8, dtype="int64")
    fund = dict((c, (np.arange(32, n, 32), np.full(len(np.arange(32, n, 32)), 0.0003))) for c in (B, E))
    a_ctx, d_ctx = h63.context(setups, px, times, 0.001, fund), desk.context(setups, px, tms, 0.001, fund)
    assert (a_ctx["day_of"][1:] != a_ctx["day_of"][:-1]).tolist() == (d_ctx["day_of"][1:] != d_ctx["day_of"][:-1]).tolist()
    for key in desk.SIZINGS:
        for kw in ({}, {"lines": (12000.0, 8000.0)}, {"funding_on": False, "worst_px": False}):
            a = h63.walk(a_ctx, 1, n, h63.member_sizer(h63.SIZINGS[key]), **kw)
            d = desk.walk(d_ctx, 1, n, desk.member_sizer(desk.SIZINGS[key]), **kw)
            assert a["outcome"] == d["outcome"] and a["end"] == d["end"] and a["joined"] == d["joined"] > 5
            assert np.allclose(a["eq"], d["eq"], equal_nan=True) and abs(a["wallet"] - d["wallet"]) < 1e-9
            assert (a["trimmed"], a["capped"], a["not_joined"]) == (d["trimmed"], d["capped"], d["not_joined"])


# ---------------------------------------------------------------- the block, on planted files
def write_bars(d, coin, bars):
    with open(os.path.join(d, "%s_15m.csv" % coin.lower()), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ts_ms", "open", "high", "low", "close", "volume", "taker_buy"])
        for i, o, h, l, c in bars:
            w.writerow([T0 + (i - 2) * BAR, o, h, l, c, 1.0, 0.5])    # two bars before the desk starts, then its own


def write_trades(d, coin, rows):
    with open(os.path.join(d, "shadow_trades_b_targets_%s.csv" % coin), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(shadows.TRADE_COLS + ["time_in", "time_out"])
        for r in rows:
            w.writerow([r.get(k, "") for k in shadows.TRADE_COLS] + ["", ""])


def flat(n, **over):
    bars = [(100.0, 100.0, 100.0, 100.0)] * (n + 2)
    for k, v in over.items():
        bars[int(k[1:]) + 2] = v
    return bars


def planted(tmp_path, btc_bars, eth_bars, btc_trades=(), eth_trades=(), state=None, funding=True):
    d, lv = str(tmp_path / "data"), str(tmp_path / "live")
    os.makedirs(d), os.makedirs(lv)
    if not isinstance(btc_bars[0], list):                          # bars as (i, o, h, l, c) keep their own times when
        btc_bars = [[i] + list(b) for i, b in enumerate(btc_bars)]   # a bar is taken out of the list
        eth_bars = [[i] + list(b) for i, b in enumerate(eth_bars)]
    write_bars(d, B, btc_bars), write_bars(d, E, eth_bars)
    write_trades(lv, B, btc_trades), write_trades(lv, E, eth_trades)
    if funding:
        for c in (B, E):
            with open(os.path.join(d, "%s_funding.csv" % c.lower()), "w") as fh:
                fh.write("ts_ms,rate\n%d,0.001\n" % (T0 + 4 * BAR))
    sp = os.path.join(d, "shadow_state.json")
    with open(sp, "w") as fh:
        json.dump({"books": {"b_targets": state or {}}}, fh)
    return desk.block(live_dir=lv, data_dir=d, state_path=sp)


def trade(i_in, i_out, side=-1, p_in=100.0, p_out=104.0, stop0=104.0, why="STOP", t1=96.0):
    return {"t_in_ms": T0 + i_in * BAR, "t_out_ms": T0 + i_out * BAR, "side": side, "p_in": p_in, "p_out": p_out,
            "stop0": stop0, "why_in": "ENTER", "why_out": why, "target_1": t1, "target_2": 92.0}


def test_before_its_first_bar_the_desk_says_so_and_needs_no_file(tmp_path):
    out = desk.block(live_dir=str(tmp_path), data_dir=str(tmp_path), state_path=str(tmp_path / "none.json"),
                     now=(desk.START_MS - 60000) / 1000.0)
    assert out["status"].startswith("no bar of the desk yet") and [w["status"] for w in out["wallets"]] == ["not started"] * 3
    assert [w["equity"] for w in out["wallets"]] == [10000.0] * 3 and out["started_utc"] == desk.START_UTC


def test_three_wallets_on_one_stopped_trade_and_one_open_trade(tmp_path):
    n = 10
    # BTC short 100 -> stopped at 104 in bar 3; ETH short from 100 at bar 5, still open, marked at 98 at the end
    btc = flat(n, b3=(100.0, 104.5, 100.0, 104.0))
    eth = flat(n, b8=(100.0, 100.0, 98.0, 98.0), b9=(98.0, 98.0, 98.0, 98.0))
    state = {E: {"pos": -1, "entry": 100.0, "stop0": 104.0, "t_in_ms": T0 + 5 * BAR, "t1": 96.0, "t1_hit": False},
             B: {"pos": 0}}
    out = planted(tmp_path, btc, eth, btc_trades=[trade(1, 3)], state=state, funding=False)
    w = dict((x["key"], x) for x in out["wallets"])
    fee = CFG["cost_side"]
    # S1: 2% of 10,000 over a 4% stop = 50 units: -200 and fees 0.001*50*204; then ETH: 2% of the wallet again
    w1 = 10000 - 200 - fee * 50 * 204
    q1 = min(0.02 * w1 / 4.0, w1 / 100.0)
    assert abs(w["S1"]["wallet"] - round(w1, 2)) < 0.011 and abs(w["S1"]["equity"] - round(w1 + q1 * 2.0, 2)) < 0.011
    w2 = 10000 - 400 - fee * 100 * 204                             # S2: 100 units
    assert abs(w["S2"]["wallet"] - round(w2, 2)) < 0.011 and abs(w["S2"]["equity"] - round(w2 + (w2 / 100.0) * 2.0, 2)) < 0.011
    w3 = 10000 - 600 - fee * 150 * 204                             # S3: 150 units
    assert abs(w["S3"]["wallet"] - round(w3, 2)) < 0.011
    for k in ("S1", "S2", "S3"):
        assert w[k]["status"] == "running" and w[k]["joined"] == 2 and w[k]["closed"] == 1 and w[k]["wins"] == 0
        assert w[k]["open"][0]["coin"] == E and w[k]["open"][0]["side"] == "SHORT" and w[k]["ended_utc"] is None
    assert w["S3"]["open"][0]["notional_x_wallet"] == 1.5 and w["S2"]["open"][0]["notional_x_wallet"] == 1.0
    assert out["trades"] == 2 and out["status"] == "running" and out["as_of_utc"] == desk._iso(T0 + n * BAR)
    assert out["funding"].startswith("not counted")                # no funding file here: said, not hidden


def test_a_trade_opened_before_the_start_is_not_joined_and_an_entry_waits_for_its_bar(tmp_path):
    n = 6
    state = {B: {"pos": -1, "entry": 100.0, "stop0": 104.0, "t_in_ms": T0 - BAR, "t1": 96.0, "t1_hit": False},
             E: {"pos": 1, "entry": 100.0, "stop0": 96.0, "t_in_ms": T0 + n * BAR, "t1": 104.0, "t1_hit": False}}
    old = dict(trade(1, 3), t_in_ms=T0 - 2 * BAR, t_out_ms=T0 - BAR)
    out = planted(tmp_path, flat(n), flat(n), btc_trades=[old], state=state)
    assert out["trades"] == 0 and out["entries_waiting_for_their_bar"] == 1
    assert all(w["joined"] == 0 and w["equity"] == 10000.0 and w["open"] == [] for w in out["wallets"])


def test_funding_is_counted_and_a_finish_line_stops_a_wallet(tmp_path):
    n = 12
    # BTC short from 100 at bar 1, held: receives 0.1% at bar 4. Then the price falls to 30 in bar 7: the 3x book
    # (150 units, +10,500) passes +100% there; the 100% book (100 units, +7,000) and the 2% rule do not.
    btc = flat(n, b6=(100.0, 100.0, 60.0, 60.0), b7=(60.0, 60.0, 30.0, 30.0), b8=(30.0, 30.0, 30.0, 30.0),
               b9=(30.0, 30.0, 30.0, 30.0), b10=(30.0, 30.0, 30.0, 30.0), b11=(30.0, 30.0, 30.0, 30.0))
    state = {B: {"pos": -1, "entry": 100.0, "stop0": 104.0, "t_in_ms": T0 + BAR, "t1": 20.0, "t1_hit": False}}
    out = planted(tmp_path, btc, flat(n), state=state)
    w = dict((x["key"], x) for x in out["wallets"])
    assert "funding" not in out
    assert w["S2"]["funding_paid_usd"] == -10.0 and w["S3"]["funding_paid_usd"] == -15.0   # received, so "paid" is negative
    assert w["S3"]["status"] == "reached +100%" and w["S3"]["ended_utc"] == desk._iso(T0 + 8 * BAR)   # +10,500 at bar 7
    assert w["S3"]["equity"] == 20515.0                             # it stops at the close that crossed the line
    assert w["S2"]["status"] == "running" and w["S2"]["equity"] == 17010.0 and w["S2"]["ended_utc"] is None
    assert w["S1"]["status"] == "running" and 10000 < w["S1"]["equity"] < 20000


def test_a_row_written_twice_counts_once_and_a_trade_without_its_bar_is_left_out_not_fatal(tmp_path):
    n = 12
    btc = flat(n, b3=(100.0, 104.5, 100.0, 104.0))
    # the engine wrote the same closed trade twice (a crash between the file and the state): one trade
    out = planted(tmp_path / "a", btc, flat(n), btc_trades=[trade(1, 3), trade(1, 3)])
    assert out["trades"] == 1 and out["trades_left_out"] == 0 and all(w["joined"] == 1 for w in out["wallets"])
    # a second trade that starts while the first is still open, and one whose exit bar is not in the file: both are
    # left out and said; the desk goes on with the rest
    odd = dict(trade(2, 5), side=1, stop0=96.0, p_out=96.0)
    eth = [[i] + list(b) for i, b in enumerate(flat(n)) if i != 6 + 2]     # ETH has no bar 6: the common times lose it
    btc = [[i] + list(b) for i, b in enumerate(btc)]
    out = planted(tmp_path / "b", btc, eth, btc_trades=[trade(1, 3), odd, trade(4, 6)])
    assert out["trades"] == 1 and out["trades_left_out"] == 2 and out["status"].startswith("running; 2 trade(s) left out")
    assert all(w["joined"] == 1 and w["status"] == "running" for w in out["wallets"])
    # an open trade whose state does not add up (Target 1 marked taken, no Target 1 price): left out, not a crash
    state = {B: {"pos": -1, "entry": 100.0, "stop0": 104.0, "t_in_ms": T0 + BAR, "t1": None, "t1_hit": True},
             E: {"pos": 1, "entry": 100.0, "stop0": None, "t_in_ms": T0 + BAR}}
    out = planted(tmp_path / "c", flat(n), flat(n), state=state)
    assert out["trades"] == 0 and out["trades_left_out"] == 2


def test_bar_files_that_cannot_be_read_after_the_start_are_said_not_called_not_started(tmp_path):
    d = str(tmp_path)
    late = (desk.START_MS + 10 * BAR) / 1000.0
    out = desk.block(live_dir=d, data_dir=d, state_path=os.path.join(d, "none.json"), now=late)
    assert out["status"] == "the bar files could not be read at this step"
    assert [w["status"] for w in out["wallets"]] == ["not read"] * 3 and out["wallets"][0]["equity"] is None
    early = (desk.START_MS - 3600000) / 1000.0
    out = desk.block(live_dir=d, data_dir=d, state_path=os.path.join(d, "none.json"), now=early)
    assert out["status"].startswith("no bar of the desk yet") and out["wallets"][0]["equity"] == 10000.0


def test_the_scoreboard_carries_the_block_and_survives_a_desk_that_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(reports, "SCOREBOARD_JSON", str(tmp_path / "scoreboard.json"))
    out = reports.scoreboard([], log=lambda *_a: None)
    assert out["paper_desk"]["started_utc"] == desk.START_UTC and len(out["paper_desk"]["wallets"]) == 3
    with open(str(tmp_path / "scoreboard.json")) as fh:
        assert json.load(fh)["paper_desk"]["wallets"][0]["key"] == "S1"
    said = []
    monkeypatch.setattr(desk, "block", lambda *a, **k: 1 / 0)
    out = reports.scoreboard([], log=said.append)
    assert "paper_desk" not in out and "rows" in out and any("paper desk" in s for s in said)
