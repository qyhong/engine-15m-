# -*- coding: utf-8 -*-
"""The book allocator a_alloc (engine15/book_alloc.py; H110, research/HYPOTHESES.md). PAPER ONLY, read only.

What is held here: the registered constants and book list; shares always inside the cap and the floor and adding up to
1; NO LOOKAHEAD (a day's shares do not change when every later row is removed); the daily result and the two wallets on
a hand-worked case; a missing, broken or unknown book file degrades to "left out", never an error; the scoreboard
carries the block and survives an allocator that fails.
"""
import importlib
import json
import math
import os
import random
import time

import numpy as np
import pytest

from engine15 import book_alloc as ba
from engine15 import reports

H, DAY = 3600000, ba.DAY_MS
N = len(ba.BOOKS)


def at(day, hour=0.0):
    return ba.START_MS + int(day * DAY + hour * H)


def now_at(day, hour=0.0):
    return at(day, hour) / 1000.0


def stamp(ms, main=False):
    return time.strftime("%Y-%m-%d %H:%M:%S+00:00" if main else "%Y-%m-%d %H:%M", time.gmtime(ms // 1000))


def main_file(d, market, rows):
    """The main books' file: time strings, as backtest writes them. rows: (t_in_ms, t_out_ms, side, pnl)."""
    with open(os.path.join(str(d), "trades_%s.csv" % market), "w", encoding="utf-8", newline="") as fh:
        fh.write("side,p_in,p_out,why_in,why_out,pnl_pct,equity,time_out,time_in,fees_usd,pnl_usd,qty\n")
        for t_in, t_out, side, pnl in rows:
            fh.write("%d,100,101,ENTER,STOP,0,10000,%s,%s,1.0,%r,1\n" % (side, stamp(t_out, True), stamp(t_in, True), pnl))


def shadow_file(d, book, market, rows):
    """A shadow book's file: millisecond columns first, as shadows.journal_trades writes them."""
    with open(os.path.join(str(d), "shadow_trades_%s_%s.csv" % (book, market)), "w", encoding="utf-8", newline="") as fh:
        fh.write("t_in_ms,t_out_ms,side,p_in,p_out,why_in,why_out,pnl_pct,equity,qty,pnl_usd,fees_usd,stop0,risk_usd,"
                 "r_mult,target_1,target_2,time_in,time_out\n")
        for t_in, t_out, side, pnl in rows:
            fh.write("%d,%d,%d,100,101,ENTER,STOP,0,10000,1,%r,1.0,99,100,1.0,,,%s,%s\n" % (
                t_in, t_out, side, pnl, stamp(t_in), stamp(t_out)))


def prow(book, market, t_in, t_out, pnl, side=1, status="CLOSED"):
    return {"book": book, "asset": market, "status": status, "side": side, "entry_utc": stamp(t_in),
            "exit_utc": stamp(t_out) if status == "CLOSED" else None, "pnl_usd": pnl}


def share_of(out, book, kind=None):
    return [r for r in out["shares_today"] if r["book"] == book and (kind is None or r["kind"] == kind)][0]


# ------------------------------------------------------------------ the registration
def test_the_constants_are_h110s():
    assert ba.START_UTC == "2026-11-25T00:00:00Z" and ba.START_W == 10000.0 and ba.NAME == "a_alloc"
    assert (ba.CAP, ba.FLOOR_X, ba.FLOOR_TRADES, ba.RET_CLIP, ba.READ_DAYS, ba.Z90) == (0.25, 0.5, 30, 0.05, (30, 60), 1.645)
    assert N == 37 and sum(1 for k in ba.BOOKS if k[0] == "shadow") == 17 and sum(1 for k in ba.BOOKS if k[0] == "strategy") == 19
    textbook = math.sqrt(8 * math.log(N) / 60.0) / (2 * ba.RET_CLIP)
    assert round(textbook, 2) == 6.94 and ba.ETA == round(textbook)
    assert "NOT passed" in ba.NOTE and "cannot create an edge that none of the books has" in ba.NOTE
    assert "open trades are not marked" in ba.NOTE


def test_every_registered_book_is_a_book_of_the_engine_with_its_markets():
    from engine15 import shadows
    from engine15.config import CFG
    markets = [a for _g, mine in CFG["universes"] for a in mine]
    in_code = set(shadows.CHALLENGERS) | set(shadows.FOLLOWERS)
    strat = {}
    for name in reports.PLAYBOOK_MODULES:
        strat.update(importlib.import_module("engine15." + name).BOOKS)
    for (kind, book), m in ba.BOOKS.items():
        if kind == "shadow":
            assert book in in_code and m == 8
        elif kind == "strategy":
            assert book in strat and m == len(strat[book]["assets"]), book
        else:
            assert (kind, book) == ("main", "main") and m == 8
    assert len(markets) == 8


# ------------------------------------------------------------------ the cap, the floor, the sum
@pytest.mark.parametrize("seed", range(40))
def test_shares_are_inside_the_cap_and_the_floor_and_add_up_to_one(seed):
    rng = np.random.RandomState(seed)
    n = int(rng.randint(1, 61))
    score = rng.normal(0, [0.01, 0.1, 1.0, 20.0][seed % 4], n)
    if seed % 5 == 0:
        score[:] = 0.0
    protected = rng.rand(n) < [0.0, 0.5, 1.0][seed % 3]
    s, cash = ba.shares_for(score, protected)
    assert len(s) == n and abs(s.sum() + cash - 1.0) < 1e-9 and cash >= 0
    assert s.max() <= ba.CAP + 1e-12 and s.min() >= 0
    floor = min(ba.FLOOR_X / n, ba.CAP)
    assert (s[protected] >= floor - 1e-12).all()
    assert cash == 0.0 if n >= 4 else abs(cash - (1 - n * ba.CAP)) < 1e-12
    for i in range(n):                                            # a better score never means a smaller share
        for j in range(n):
            if score[i] > score[j] and protected[i] == protected[j]:
                assert s[i] >= s[j] - 1e-12


def test_equal_scores_are_equal_shares_and_the_cap_binds_on_a_runaway_book():
    s, cash = ba.shares_for(np.zeros(N), np.ones(N, bool))
    assert np.allclose(s, 1.0 / N) and cash == 0.0
    score = np.zeros(N)
    score[3] = 5.0                                                # exp(35): far past the cap
    s, _ = ba.shares_for(score, np.ones(N, bool))
    assert abs(s[3] - ba.CAP) < 1e-12 and abs(s.sum() - 1.0) < 1e-9
    assert np.allclose(np.delete(s, 3), 0.75 / (N - 1))           # the rest share what is left, above their floor
    score[5] = -5.0                                               # a protected loser sits on the floor ...
    s, _ = ba.shares_for(score, np.ones(N, bool))
    assert abs(s[5] - ba.FLOOR_X / N) < 1e-12
    prot = np.ones(N, bool)
    prot[5] = False                                               # ... and after 30 trades it has none
    s, _ = ba.shares_for(score, prot)
    assert s[5] < 1e-6 and abs(s.sum() - 1.0) < 1e-9


# ------------------------------------------------------------------ the block on planted records
def test_before_the_start_it_says_so_holds_equal_shares_and_needs_no_file(tmp_path):
    out = ba.block(live_dir=str(tmp_path / "nowhere"), now=now_at(-1, 5))
    assert out["status"].startswith("not started") and out["equity"] == 10000.0 and out["yardstick_equity"] == 10000.0
    assert out["days"] == 0 and out["daily"] == [] and out["passed"] is False and out["books"] == N
    assert len(out["shares_today"]) == N and all(abs(r["share_pct"] - 100.0 / N) < 1e-3 for r in out["shares_today"])
    assert out["reads"]["30"]["word"] == "too early to read (0 of 30 days)"
    json.dumps(out)


def test_a_hand_worked_three_days(tmp_path):
    d = tmp_path
    # day 0: b_trail +800 on BTC (8 markets: +1.0% of its base), p9_cascade -100 (2 markets: -0.5%)
    # day 1: the main books +400 (+0.5%); day 2 (today, not over): b_trail -160 (-0.2%)
    shadow_file(d, "b_trail", "BTCUSDT", [(at(0, 1), at(0, 5), 1, 800.0), (at(1, 2), at(2, 3), -1, -160.0)])
    main_file(d, "XAUUSD", [(at(0, 6), at(1, 7), 1, 400.0)])
    rows = [prow("p9_cascade", "ETHUSDT", at(0, 2), at(0, 9), -100.0),
            prow("p9_cascade", "BTCUSDT", at(2, 1), None, -55.0, status="OPEN")]      # an open trade is not marked
    out = ba.block(rows, live_dir=str(d), now=now_at(2, 12))
    assert out["status"] == "running" and out["days"] == 3 and out["days_complete"] == 2 and out["today"] == "2026-11-27"
    day = out["daily"]
    assert [r["complete"] for r in day] == [True, True, False] and [r["trades"] for r in day] == [2, 1, 1]
    # day 0: every book holds 1/37, so the two wallets are the same
    y0 = (0.01 - 0.005) / N
    assert day[0]["alloc_pct"] == day[0]["yardstick_pct"] == round(y0 * 100, 4) and day[0]["turnover_pct"] == 0.0
    # day 1: weights exp(7 x score); nothing reaches the cap or the floor, so shares = raw / sum
    raw = {"b_trail": math.exp(7 * 0.01), "p9_cascade": math.exp(7 * -0.005)}
    tot = (N - 2) + sum(raw.values())
    a1, y1 = (1.0 / tot) * 0.005, 0.005 / N                       # the main books had score 0 on day 1
    assert day[1]["alloc_pct"] == round(a1 * 100, 4) and day[1]["yardstick_pct"] == round(y1 * 100, 4)
    assert day[1]["top_book"] == "b_trail" and day[1]["top_share_pct"] == round(100 * raw["b_trail"] / tot, 3)
    # day 2 (so far): the main books' day-1 gain is in the weights now
    raw2 = dict(raw, main=math.exp(7 * 0.005))
    tot2 = (N - 3) + sum(raw2.values())
    a2, y2 = (raw2["b_trail"] / tot2) * -0.002, -0.002 / N
    assert day[2]["alloc_pct"] == round(a2 * 100, 4) and day[2]["yardstick_pct"] == round(y2 * 100, 4)
    assert out["equity"] == round(10000 * (1 + y0) * (1 + a1) * (1 + a2), 2)
    assert out["yardstick_equity"] == round(10000 * (1 + y0) * (1 + y1) * (1 + y2), 2)
    assert out["curve"]["alloc"][-1] == out["equity"] and len(out["curve"]["yardstick"]) == 3
    bt = share_of(out, "b_trail")
    assert bt["share_pct"] == round(100 * raw2["b_trail"] / tot2, 3) and bt["trades"] == 2 and bt["floor"] is True
    assert bt["net_usd"] == 640.0 and bt["score_pct"] == 1.0 and bt["markets"] == 8
    assert share_of(out, "main", "main")["share_pct"] == round(100 * raw2["main"] / tot2, 3)
    assert share_of(out, "main", "shadow")["share_pct"] == round(100 / tot2, 3)        # the hold copy is another book
    assert share_of(out, "p9_cascade")["net_usd"] == -100.0
    assert abs(sum(r["share_pct"] for r in out["shares_today"]) + out["cash_pct"] - 100.0) < 0.05
    assert out["reads"]["30"]["word"] == "too early to read (2 of 30 days)" and out["verdict"].startswith("NOT passed")
    json.dumps(out)


def test_a_trade_opened_before_the_start_never_counts_and_a_close_at_midnight_is_the_new_days(tmp_path):
    d = tmp_path
    shadow_file(d, "b_targets", "BTCUSDT", [(at(-1, 20), at(0, 5), 1, 900.0),     # opened before the start: out
                                            (at(0, 6), at(1, 0), 1, 800.0)])      # closes at day 1 00:00: day 1's
    out = ba.block(live_dir=str(d), now=now_at(1, 2))
    assert [r["trades"] for r in out["daily"]] == [0, 1]
    assert share_of(out, "b_targets")["net_usd"] == 800.0
    assert share_of(out, "b_targets")["share_pct"] == round(100.0 / N, 3)         # day 1's shares did not see it
    assert out["daily"][1]["alloc_pct"] == out["daily"][1]["yardstick_pct"] > 0
    out = ba.block(live_dir=str(d), now=now_at(2, 2))
    assert share_of(out, "b_targets")["share_pct"] > 100.0 / N                    # day 2's did


def planted_year(d, seed, days, per_day=6):
    rng = random.Random(seed)
    files, rows = {}, []
    keys = list(ba.BOOKS)
    for day in range(days):
        for _ in range(per_day):
            kind, book = rng.choice(keys)
            t_in = at(day, rng.uniform(0, 20))
            t_out = t_in + int(rng.choice([0.25, 1, 6, 30, 70]) * H)
            pnl = round(rng.gauss(20, 400), 2)
            market = rng.choice(["BTCUSDT", "ETHUSDT", "XAUUSD"])
            if kind == "strategy":
                rows.append(prow(book, market, t_in, t_out, pnl, side=rng.choice([1, -1])))
            else:
                files.setdefault((kind, book, market), []).append((t_in, t_out, rng.choice([1, -1]), pnl))
    for (kind, book, market), r in files.items():
        (main_file(d, market, r) if kind == "main" else shadow_file(d, book, market, r))
    return rows


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_no_lookahead_a_days_shares_do_not_change_when_later_days_are_removed(tmp_path, seed):
    full_dir, days = tmp_path / "full", 45
    full_dir.mkdir()
    rows = planted_year(full_dir, seed, days)
    trades, left, other, bad = ba.read_books(str(full_dir), rows)
    assert not left and not other and not bad and sum(len(v) for v in trades.values()) > 200
    bases = [ba.STAKE * ba.BOOKS[k] for k in trades]
    full = ba.walk(*ba.day_tables(trades, bases, days))
    assert np.abs(full["shares"] - 1.0 / N).max() > 0.002          # the weights do move in this record
    for cut in (1, 2, 7, 20, 31, 44):
        kept = dict((k, [t for t in v if t[2] < at(cut)]) for k, v in trades.items())    # rows closed before day `cut`
        assert sum(len(v) for v in kept.values()) < sum(len(v) for v in trades.values())
        part = ba.walk(*ba.day_tables(kept, bases, cut + 1))
        assert np.array_equal(part["shares"][:cut + 1], full["shares"][:cut + 1])         # days 0 .. cut: bit for bit
        assert np.array_equal(part["a_eq"][:cut], full["a_eq"][:cut]) and np.array_equal(part["y_eq"][:cut], full["y_eq"][:cut])
    # and through the block: the shares shown at a day's first minute are the shares shown at its last
    a = ba.block(rows, live_dir=str(full_dir), now=now_at(20, 0.01))
    b = ba.block(rows, live_dir=str(full_dir), now=now_at(20, 23.9))
    key = lambda o: sorted((r["kind"], r["book"], r["share_pct"]) for r in o["shares_today"])   # noqa: E731
    days_of = lambda o: [dict(r, complete=None) for r in o["daily"][:20]]                       # noqa: E731
    assert key(a) == key(b) and days_of(a) == days_of(b) and a["cash_pct"] == b["cash_pct"] == 0.0


@pytest.mark.parametrize("seed", [4, 5])
def test_every_day_of_a_walk_keeps_the_cap_the_floor_and_the_sum(tmp_path, seed):
    days = 80
    rows = planted_year(tmp_path, seed, days, per_day=12)
    rows += [prow("p10_round", "BTCUSDT", at(k, 1), at(k, 2), 2500.0) for k in range(days)]      # a runaway winner
    rows += [prow("p1_liqhunt", "BTCUSDT", at(k, 3), at(k, 4), -2500.0) for k in range(days)]    # and a steady loser
    trades, _l, _o, _b = ba.read_books(str(tmp_path), rows)
    keys = list(trades)
    w = ba.walk(*ba.day_tables(trades, [ba.STAKE * ba.BOOKS[k] for k in keys], days))
    s = w["shares"]
    assert np.allclose(s.sum(axis=1) + w["cash"], 1.0, atol=1e-9) and (w["cash"] == 0).all()
    assert s.max() <= ba.CAP + 1e-12 and s.min() >= 0
    prot = w["count"] < ba.FLOOR_TRADES
    assert (s[prot] >= ba.FLOOR_X / N - 1e-12).all()
    win, lose = keys.index(("strategy", "p10_round")), keys.index(("strategy", "p1_liqhunt"))
    assert abs(s[-1, win] - ba.CAP) < 1e-9                         # held AT the cap, never above
    d30 = int(np.argmax(w["count"][:, lose] >= ba.FLOOR_TRADES))   # the first day that sees its 30th closed trade
    assert 10 < d30 < days
    assert abs(s[d30 - 1, lose] - ba.FLOOR_X / N) < 1e-12          # on the floor while it has under 30 trades
    assert s[d30, lose] < ba.FLOOR_X / N / 10                      # and let go after its 30th
    assert w["a_eq"][-1] > w["y_eq"][-1]                           # (planted: the winner was there to be found)


# ------------------------------------------------------------------ odd inputs degrade, they never stop the step
def test_a_broken_file_leaves_its_book_out_and_the_rest_carries_on(tmp_path):
    d = tmp_path
    shadow_file(d, "b_trail", "BTCUSDT", [(at(0, 1), at(0, 5), 1, 800.0)])
    shadow_file(d, "v4", "WTI", [(at(0, 1), at(0, 5), 1, 80.0)])
    with open(str(d / "shadow_trades_v4_BRENT.csv"), "wb") as fh:                 # no header a trade could be read under
        fh.write(b"\xff\xfe\x00garbage,,,\n1,2,3\n")
    with open(str(d / "shadow_trades_y_1d_SPX.csv"), "wb") as fh:                 # an empty file
        fh.write(b"")
    out = ba.block(live_dir=str(d), now=now_at(1, 2))
    assert sorted(r["book"] for r in out["books_left_out"]) == ["v4", "y_1d"] and out["books"] == N - 2
    assert "2 book(s) left out" in out["status"] and out["status"].startswith("running")
    assert len(out["shares_today"]) == N - 2 and not [r for r in out["shares_today"] if r["book"] in ("v4", "y_1d")]
    assert share_of(out, "b_trail")["net_usd"] == 800.0
    assert out["daily"][0]["yardstick_pct"] == round(100 * 0.01 / (N - 2), 4)     # the yardstick is the same books
    assert abs(sum(r["share_pct"] for r in out["shares_today"]) - 100.0) < 0.05
    json.dumps(out)


def test_a_garbled_row_is_skipped_a_row_written_twice_counts_once_and_an_unknown_book_is_named(tmp_path):
    d = tmp_path
    shadow_file(d, "b_trail", "BTCUSDT", [(at(0, 1), at(0, 5), 1, 800.0), (at(0, 1), at(0, 5), 1, 800.0)])
    with open(str(d / "shadow_trades_b_trail_BTCUSDT.csv"), "a", encoding="utf-8") as fh:
        fh.write("not,a,row\n\n17,x,1,,,,,,,,nan,,,,,,,,\n")
    shadow_file(d, "b_learn", "BTCUSDT", [(at(0, 1), at(0, 5), 1, 999.0)])        # a book H110 did not register
    main_file(d, "SPX", [(at(0, 2), at(0, 4), 1, 100.0), (at(0, 2), at(0, 9), 1, 60.0)])   # one trade closed in parts
    rows = [prow("p3_orb", "SPX", at(0, 1), at(0, 2), 30.0), prow("p3_orb", "SPX", at(0, 1), at(0, 2), 30.0),
            prow("p99_new", "SPX", at(0, 1), at(0, 2), 30.0), "junk", None,
            dict(prow("p3_orb", "SPX", at(0, 3), at(0, 4), 30.0), exit_utc="soon"),
            dict(prow("p3_orb", "SPX", at(0, 3), at(0, 4), 30.0), pnl_usd=None)]
    out = ba.block(rows, live_dir=str(d), now=now_at(1, 2))
    assert out["status"] == "running" and out["books_left_out"] == [] and out["rows_skipped"] == 3
    assert out["books_not_registered"] == [{"book": "b_learn", "kind": "shadow"}, {"book": "p99_new", "kind": "strategy"}]
    assert (share_of(out, "b_trail")["net_usd"], share_of(out, "b_trail")["trades"]) == (800.0, 1)
    assert (share_of(out, "p3_orb")["net_usd"], share_of(out, "p3_orb")["trades"]) == (30.0, 1)
    assert (share_of(out, "main", "main")["net_usd"], share_of(out, "main", "main")["trades"]) == (160.0, 1)
    assert out["daily"][0]["trades"] == 3


def test_strategy_rows_that_cannot_be_walked_leave_the_strategy_books_out_only(tmp_path):
    shadow_file(tmp_path, "b_trail", "BTCUSDT", [(at(0, 1), at(0, 5), 1, 800.0)])
    out = ba.block(12345, live_dir=str(tmp_path), now=now_at(1, 2))
    assert out["books"] == N - 19 and len(out["books_left_out"]) == 19
    assert all(r["kind"] == "strategy" for r in out["books_left_out"]) and share_of(out, "b_trail")["net_usd"] == 800.0


def test_with_fewer_than_four_books_the_cap_holds_and_the_rest_is_cash(tmp_path, monkeypatch):
    few = ba.OrderedDict([(("shadow", "b_trail"), 8), (("strategy", "p3_orb"), 6), (("main", "main"), 8)])
    monkeypatch.setattr(ba, "BOOKS", few)
    shadow_file(tmp_path, "b_trail", "BTCUSDT", [(at(0, 1), at(0, 5), 1, 800.0)])
    out = ba.block([], live_dir=str(tmp_path), now=now_at(1, 2))
    assert [r["share_pct"] for r in out["shares_today"]] == [25.0, 25.0, 25.0] and out["cash_pct"] == 25.0
    assert out["daily"][0]["alloc_pct"] == round(100 * 0.25 * 0.01, 4)
    assert out["daily"][0]["yardstick_pct"] == round(100 * 0.01 / 3, 4)


def test_a_clock_far_past_the_start_is_an_error_the_scoreboard_would_log(tmp_path):
    with pytest.raises(RuntimeError):
        ba.block(live_dir=str(tmp_path), now=now_at(ba.MAX_DAYS + 5))


def test_an_absurd_row_cannot_put_a_non_number_into_the_scoreboard(tmp_path):
    rows = [prow("p4_gapfill", "SPX", at(k, 1), at(k, 2), 1e306) for k in range(3)]    # the wallet overflows to infinity
    with pytest.raises(ValueError):
        ba.block(rows, live_dir=str(tmp_path), now=now_at(3, 2))
    out = ba.block([prow("p4_gapfill", "SPX", at(0, 1), at(0, 2), -1e9)], live_dir=str(tmp_path), now=now_at(1, 2))
    assert out["equity"] == 0.0 and out["yardstick_equity"] == 0.0                     # a wallet stops at zero, not below


def test_times_are_read_as_utc_in_every_form_the_books_write():
    ms = at(3, 17.25)
    for v in (ms, str(ms), "%d.0" % ms, stamp(ms), stamp(ms, True), stamp(ms).replace(" ", "T") + "Z",
              stamp(ms) + ":00.000+00:00", " %s UTC " % stamp(ms)):
        assert ba._ms(v) == ms, v
    for v in ("", "soon", None, "nan", "inf", "2026-11-28 17:15:00+08:00", "2026-13-01 00:00", "20261128 1715", "2026-11-28"):
        with pytest.raises((ValueError, TypeError, IndexError)):
            ba._ms(v)


# ------------------------------------------------------------------ the verdict
def test_the_read_is_ahead_behind_or_level_by_the_range_of_the_daily_difference():
    y = np.zeros(60)
    assert ba.read_of(y[:29], y[:29], 30) == {"days": 30, "word": "too early to read (29 of 30 days)"}
    rng = np.random.RandomState(7)
    noise = rng.normal(0, 0.001, 60)
    up = ba.read_of(0.001 + noise, y, 30)
    assert up["word"] == "ahead" and up["range90_daily_diff_pct"][0] > 0 and up["diff_pts"] > 0
    assert ba.read_of(-0.001 + noise, y, 60)["word"] == "behind"
    lvl = ba.read_of(noise * 5, y, 30)
    assert lvl["word"] == "level" and lvl["range90_daily_diff_pct"][0] < 0 < lvl["range90_daily_diff_pct"][1]
    assert ba.read_of(y, y, 30)["word"] == "level"                 # the same wallet is level with itself
    d = 0.001 + noise[:30]                                         # the scoreboard's formula, by hand
    half = 1.645 * d.std(ddof=1) / math.sqrt(30)
    assert up["range90_daily_diff_pct"] == [round((d.mean() - half) * 100, 4), round((d.mean() + half) * 100, 4)]


def test_the_first_read_uses_the_first_30_completed_days_and_later_days_do_not_move_it(tmp_path):
    rows = planted_year(tmp_path, 9, 50)
    a = ba.block(rows, live_dir=str(tmp_path), now=now_at(30, 0.5))    # day 29 ended half an hour ago: not complete yet
    assert a["days_complete"] == 29 and a["reads"]["30"]["word"].startswith("too early")
    b = ba.block(rows, live_dir=str(tmp_path), now=now_at(30, 1.5))
    c = ba.block(rows, live_dir=str(tmp_path), now=now_at(49, 12))
    assert b["days_complete"] == 30 and b["reads"]["30"]["word"] in ("ahead", "behind", "level")
    assert b["reads"]["30"] == c["reads"]["30"] and c["reads"]["60"]["word"] == "too early to read (49 of 60 days)"
    assert "first read (30 days): %s" % b["reads"]["30"]["word"] in b["verdict"]
    assert len(c["daily"]) == 50 and len(c["curve"]["alloc"]) == 50
    long = ba.block(rows, live_dir=str(tmp_path), now=now_at(200, 12))
    assert len(long["daily"]) == ba.ROWS_KEPT and len(long["curve"]["alloc"]) == 201 and long["reads"]["60"]["days"] == 60


# ------------------------------------------------------------------ the scoreboard
def test_the_scoreboard_carries_the_block_and_survives_an_allocator_that_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(reports, "SCOREBOARD_JSON", str(tmp_path / "scoreboard.json"))
    monkeypatch.setattr(ba, "LIVE_DIR", str(tmp_path))
    shadow_file(tmp_path, "b_trail", "BTCUSDT", [(at(0, 1), at(0, 5), 1, 800.0)])
    rows = [prow("p3_orb", "SPX", at(0, 1), at(0, 2), 30.0)]
    before = dict((k, v) for k, v in reports.scoreboard(rows, log=lambda *_a: None).items() if k != "a_alloc")
    out = reports.scoreboard(rows, log=lambda *_a: None)
    assert out["a_alloc"]["book"] == "a_alloc" and out["a_alloc"]["passed"] is False and out["a_alloc"]["books"] == N
    assert "p3_orb" in [r["book"] for r in out["rows"]]            # the scoreboard's own rows are as they were
    with open(str(tmp_path / "scoreboard.json")) as fh:
        assert json.load(fh)["a_alloc"]["started_utc"] == ba.START_UTC
    said = []
    monkeypatch.setattr(ba, "block", lambda *a, **k: 1 / 0)
    out = reports.scoreboard(rows, log=said.append)
    assert "a_alloc" not in out and any("book allocator" in s for s in said)
    assert [r for r in out["rows"]] == before["rows"] and out.get("paper_desk", {}).keys() == before.get("paper_desk", {}).keys()
