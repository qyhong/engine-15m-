# -*- coding: utf-8 -*-
"""The exit learner `b_learn` (engine15/learn_book.py; H109, owner 24 Nov 2026). A paper follower book: it reads six
shadow books' own records and copies the next trade of the best-weighted one. It must never look ahead, never change
another book, never stop the scoreboard, and give the same trades after a restart. No network.

    py -3 -m pytest tests/test_learn_book.py -q
"""
import csv
import json
import os
import random
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine15 import data, reports, shadows  # noqa: E402
from engine15 import learn_book as lb  # noqa: E402

B, E = lb.COINS
BAR = lb.BAR_MS
T0 = lb.START_MS
NAN = float("nan")
X, Y = "calm_agree", "wild_mixed"


# ------------------------------------------------------------------ helpers
def tr(arm, i_in, i_out, r=1.0, coin=B, side=1, eq0=10000.0):
    """A closed arm trade from bar i_in to bar i_out (bars counted from START_UTC; negative = warm-up): r x 1% of equity."""
    pnl = eq0 * 0.01 * r
    return {"arm": arm, "coin": coin, "t_in": T0 + i_in * BAR, "t_out": T0 + i_out * BAR, "side": side, "p_in": 100.0,
            "p_out": 100.0 + side * r, "why_in": "ENTER", "why_out": "FLIP", "pnl": pnl, "eq_after": eq0 + pnl,
            "eq0": eq0, "qty": 10.0, "fees": 2.0, "stop0": 100.0 - side * 3.0, "risk": 30.0, "r": r, "pnl_pct": r,
            "t1": NAN, "t2": NAN}


def op(arm, i_in, coin=B, side=1, eq0=10000.0, mark=101.0, qty=10.0):
    return {"arm": arm, "coin": coin, "t_in": T0 + i_in * BAR, "t_out": None, "side": side, "p_in": 100.0, "qty": qty,
            "why_in": "ENTER", "part_pnl": 0.0, "stop": 97.0, "stop0": 97.0, "mark": mark, "t1": NAN, "t2": NAN,
            "t1_hit": False, "eq0": eq0}


def one(_coin, _t):
    return X


def picks(res):
    return [(c["coin"], (c["t_in"] - T0) // BAR, c["arm"], c["table"]) for c in res["choices"]]


FILE_COLS = ["t_in_ms", "t_out_ms", "side", "p_in", "p_out", "why_in", "why_out", "pnl_pct", "equity", "qty", "pnl_usd",
             "fees_usd", "stop0", "risk_usd", "r_mult", "target_1", "target_2", "time_in", "time_out"]


def write_arm(live, arm, coin, trades, mode="w"):
    """The arm's record as shadows.journal_trades writes it."""
    os.makedirs(live, exist_ok=True)
    path = os.path.join(live, "shadow_trades_%s_%s.csv" % (arm, coin))
    new = mode == "w" or not os.path.exists(path)
    with open(path, mode, newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(FILE_COLS)
        for t in trades:
            w.writerow([t["t_in"], t["t_out"], t["side"], t["p_in"], t["p_out"], t["why_in"], t["why_out"], t["pnl_pct"],
                        t["eq_after"], t["qty"], t["pnl"], t["fees"], t["stop0"], t["risk"], t["r"], "", "",
                        lb._utc(t["t_in"]), lb._utc(t["t_out"])])
    return path


def bars(n_before=45 * 96, n_after=3 * 96, seed=7, wild_from=None):
    """Random 15m bars from n_before bars before START_UTC: [(ts, o, h, l, c)]. wild_from: the bar (counted from
    START_UTC) from which the range is five times wider."""
    rng = np.random.RandomState(seed)
    out, px = [], 100.0
    for i in range(-n_before, n_after):
        k = 5.0 if wild_from is not None and i >= wild_from else 1.0
        o = px
        c = max(1.0, o * (1.0 + 0.002 * k * rng.randn()))
        hi, lo = max(o, c) * (1.0 + 0.001 * k * rng.rand()), min(o, c) * (1.0 - 0.001 * k * rng.rand())
        out.append((T0 + i * BAR, o, hi, lo, c))
        px = c
    return out


def write_bars(d, coin, rows):
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "%s_15m.csv" % coin.lower()), "w") as fh:
        fh.write("ts_ms,open,high,low,close,volume,taker_buy\n")
        for b in rows:
            fh.write("%d,%r,%r,%r,%r,1.0,0.5\n" % tuple(b))


def planted(tmp_path, arms=None, state=None, btc=None, eth=None):
    """A data dir with bars and a live dir with the arms' records -> (live, data, state path)."""
    d, lv = str(tmp_path / "data"), str(tmp_path / "live")
    write_bars(d, B, btc if btc is not None else bars(seed=7))
    write_bars(d, E, eth if eth is not None else bars(seed=8))
    os.makedirs(lv, exist_ok=True)
    for (arm, coin), trades in (arms or {}).items():
        write_arm(lv, arm, coin, trades)
    sp = os.path.join(d, "shadow_state.json")
    with open(sp, "w") as fh:
        json.dump({"books": state or {}}, fh)
    return lv, d, sp


def own_file(lv, coin):
    return os.path.join(lv, "shadow_trades_%s_%s.csv" % (lb.NAME, coin))


def own_rows(lv, coin):
    with open(own_file(lv, coin), newline="") as fh:
        return list(csv.DictReader(fh))


# ------------------------------------------------------------------ the registration (H109) is what the code holds
def test_the_constants_are_the_registered_ones_and_the_book_never_calls_itself_passed():
    assert lb.ARMS == ("b_targets", "main", "b_trail", "b_be_t1", "b_ema20_1h_t1", "b_sma20_1h_t1")
    assert all(a in shadows.CHALLENGERS for a in lb.ARMS)            # arms the shadow books really run
    assert lb.COINS == ("BTCUSDT", "ETHUSDT") and len(lb.BUCKETS) == 4 and len(set(lb.BUCKETS)) == 4
    assert (lb.HALF_LIFE_MS, lb.ETA, lb.MIN_BUCKET_TRADES) == (30 * 86400000, 0.5, 12)
    assert (lb.VOL_NOW, lb.VOL_REF, lb.TREND_N, lb.STALE_MS, lb.READ_AT) == (96, 2880, 20, 3600000, (30, 60))
    assert lb.START_UTC == "2026-11-25T00:00:00Z" and lb.START_MS % BAR == 0 and lb.NAME == "b_learn"
    assert reports.SHADOW_TITLES[lb.NAME] == lb.SCOREBOARD_TITLE and lb.SCOREBOARD_TITLE.startswith("Shadow: b_learn")
    for text in (lb.SCOREBOARD_TITLE, lb.NOTE):
        assert "NOT passed" in text and "paper only" in text.lower()
        assert "edge" not in text.lower() and "kronos" not in text.lower()
    assert "unproven" in lb.NOTE                                    # the plain warning travels with the numbers
    from engine15.config import CFG
    assert not any("learn" in k for k in CFG)                       # its constants live in its own module


def test_it_is_not_on_the_money_path_and_is_not_a_rule_of_the_shadow_books():
    assert lb.NAME not in shadows.CHALLENGERS and lb.NAME not in shadows.FOLLOWERS
    with open(os.path.join(ROOT, "tools", "money_files.txt")) as fh:
        assert "learn_book" not in fh.read()
    for mod in ("vault_feed.py", "setups.py", "signals.py"):
        with open(os.path.join(ROOT, "engine15", mod), encoding="utf-8") as fh:
            src = fh.read()
        assert "learn_book" not in src and "b_learn" not in src     # nothing of it reaches the vault or the Setups feed


# ------------------------------------------------------------------ the market state: closed bars only
def test_a_reading_never_changes_when_later_bars_are_removed_or_earlier_ones_added():
    rows = bars(n_before=40 * 96, n_after=2 * 96, seed=3, wild_from=-200)
    a = np.asarray(rows, dtype=float)
    ts = a[:, 0].astype("int64")
    wild, agree = lb.regimes(ts, a[:, 2], a[:, 3], a[:, 4])
    assert np.isfinite(wild[-300:]).all() and np.isfinite(agree[-300:]).all()
    rng = random.Random(1)
    for k in [len(ts) - 1] + [rng.randrange(len(ts) - 600, len(ts)) for _ in range(12)]:
        w, g = lb.regimes(ts[:k + 1], a[:k + 1, 2], a[:k + 1, 3], a[:k + 1, 4])      # the file as it stood at bar k
        assert w[k] == wild[k] and g[k] == agree[k]
        cut = rng.randrange(1, 400)                                 # a shorter tail of the same file
        w, g = lb.regimes(ts[cut:k + 1], a[cut:k + 1, 2], a[cut:k + 1, 3], a[cut:k + 1, 4])
        assert w[-1] == wild[k] and g[-1] == agree[k]
    assert wild[-1] == 1.0                                          # the last 200 bars are five times wider: wild


def test_the_bucket_is_read_from_the_last_bar_closed_by_the_entry_and_from_nothing_after_it():
    rows = bars(n_before=40 * 96, n_after=96, seed=5)
    a = np.asarray(rows, dtype=float)
    ts = a[:, 0].astype("int64")
    reg = (ts,) + lb.regimes(ts, a[:, 2], a[:, 3], a[:, 4])
    T = T0 + 20 * BAR
    got = lb.bucket_at(reg, T)
    assert got in lb.BUCKETS
    k = int(np.searchsorted(ts, T))                                 # the bar that OPENS at T and every later one go wild
    b = a.copy()
    b[k:, 2] *= 3.0
    b[k:, 4] *= 2.0
    assert lb.bucket_at((ts,) + lb.regimes(ts, b[:, 2], b[:, 3], b[:, 4]), T) == got
    assert lb.bucket_at(reg, int(ts[-1]) + BAR + lb.STALE_MS) in lb.BUCKETS           # one hour old: still a reading
    assert lb.bucket_at(reg, int(ts[-1]) + 2 * BAR + lb.STALE_MS) is None             # older: no reading
    assert lb.bucket_at(reg, int(ts[0])) is None and lb.bucket_at(None, T) is None
    assert lb.bucket_at(reg, int(ts[2000]) + BAR) is None           # the look-backs are not filled that early


def test_calm_or_wild_and_agree_or_mixed_mean_what_the_registration_says():
    n = 40 * 96
    ts = T0 + BAR * np.arange(-n, 0, dtype="int64")
    up = 100.0 * (1.0 + 0.0005) ** np.arange(n)                     # a steady rise: both trends up
    wide = np.where(np.arange(n) >= n - 96, 0.0005, 0.001)          # the last 24 hours' bars are half as wide
    wild, agree = lb.regimes(ts, up * (1 + wide), up * (1 - wide), up)
    assert agree[-1] == 1.0 and wild[-1] == 0.0                     # under the 30-day median: calm
    dn = up.copy()
    dn[-80:] = dn[-81] * (1.0 - 0.004) ** np.arange(1, 81)          # the last 20 hours fall below the 4h average only
    hi, lo = dn * 1.001, dn * 0.999
    wild, agree = lb.regimes(ts, hi, lo, dn)
    assert agree[-1] == 0.0                                         # 4h down, daily still up: mixed
    assert wild[-1] == 1.0                                          # and the bars are wider than the 30-day median


# ------------------------------------------------------------------ the learner and the follower
def test_with_no_information_it_copies_the_setups_book_and_earns_that_trades_return():
    closed = [tr("b_trail", 1, 4, r=2.0), tr("b_targets", 2, 6, r=1.5, eq0=12000.0), tr("main", 2, 9, r=3.0)]
    res = lb.walk(closed, [], one)
    assert picks(res) == [(B, 2, "b_targets", "pooled")]            # every score is zero: the first in ARMS
    t = res["trades"][B][0]
    assert abs(t["pnl"] - 150.0) < 1e-9 and abs(res["equity"][B] - 10150.0) < 1e-9    # 1.5% of ITS 10,000, not of 12,000
    assert abs(t["qty"] - 10.0 * 10000.0 / 12000.0) < 1e-9 and t["r"] == 1.5 and t["eq_after"] == res["equity"][B]
    assert res["equity"][E] == 10000.0 and res["trades"][E] == [] and res["open"] == {B: None, E: None}


def test_it_follows_the_arm_with_the_best_decayed_r_in_the_entrys_bucket():
    warm = []
    for i in range(6):                                              # bucket X: the trail earned, the Setups book lost
        warm += [tr("b_trail", -200 + 10 * i, -195 + 10 * i, r=1.0), tr("b_targets", -200 + 10 * i, -196 + 10 * i, r=-0.5)]
    for i in range(6):                                              # bucket Y: the hold copy earned, the trail lost
        warm += [tr("main", -400 + 10 * i, -395 + 10 * i, r=2.0, coin=E), tr("b_trail", -400 + 10 * i, -396 + 10 * i, r=-1.0, coin=E)]
    xs = set(t["t_in"] for t in warm if t["coin"] == B)
    fwd = [tr("main", 1, 3), tr("b_trail", 5, 8, r=0.5), tr("b_trail", 20, 22, coin=E), tr("main", 21, 30, coin=E, r=4.0)]
    xs |= {T0 + 1 * BAR, T0 + 5 * BAR}
    res = lb.walk(warm + fwd, [], lambda c, t: X if t in xs else Y)
    assert picks(res) == [(B, 5, "b_trail", X), (E, 21, "main", Y)]  # each bucket's own table (12 closed trades each)
    assert res["tables"][X]["leader"] == "b_trail" and res["tables"][Y]["leader"] == "main"
    assert res["tables"][X]["in_use"] and res["tables"][X]["closed_trades"] == 14 == res["tables"][Y]["closed_trades"]
    w = res["tables"][X]["weights"]
    assert abs(sum(w.values()) - 1.0) < 1e-3 and w["b_trail"] == max(w.values()) and w["b_targets"] == min(w.values())
    # one trade of each bucket fewer before the start: 11 each, so the pooled table decides (the hold copy, +12R)
    # until a bucket has its 12th closed trade (X at bar 3: from then on X's own table, where the trail leads)
    few = [t for t in warm if t["t_in"] not in (T0 - 200 * BAR, T0 - 400 * BAR) or t["arm"] != "b_trail"]
    res = lb.walk(few + fwd, [], lambda c, t: X if t in xs else Y)
    assert picks(res) == [(B, 1, "main", "pooled"), (B, 5, "b_trail", X), (E, 21, "main", "pooled")]
    assert res["tables"]["pooled"]["leader"] == "main" and res["tables"]["pooled"]["closed_trades"] == 26


def test_an_old_reward_counts_for_less_than_a_recent_one():
    day = 96
    old = tr("main", -90 * day, -90 * day + 4, r=3.0)               # +3R ninety days ago: three half-lives, 0.375R now
    new = tr("b_trail", -day, -day + 4, r=1.0)                      # +1R yesterday
    fwd = [tr("main", 2, 5), tr("b_trail", 3, 6)]
    assert picks(lb.walk([old, new] + fwd, [], one)) == [(B, 3, "b_trail", "pooled")]
    same_age = tr("main", -day - 1, -day + 3, r=3.0)
    assert picks(lb.walk([same_age, new] + fwd, [], one)) == [(B, 2, "main", "pooled")]
    res = lb.walk([old], [], one, as_of_ms=old["t_out"] + 3 * lb.HALF_LIFE_MS)
    assert abs(res["tables"]["pooled"]["scores_r"]["main"] - 0.375) < 1e-9


def test_a_reward_counts_only_for_entries_strictly_after_it_closed():
    lead = tr("b_trail", 1, 6, r=5.0)                               # the trail's +5R closes AT bar 6
    at6 = [tr("b_trail", 6, 8), tr("b_targets", 6, 9)]
    assert picks(lb.walk([lead] + at6, [], one)) == [(B, 6, "b_targets", "pooled")]   # not known at bar 6: still a tie
    at7 = [tr("b_trail", 7, 8), tr("b_targets", 7, 9)]
    assert picks(lb.walk([lead] + at7, [], one)) == [(B, 7, "b_trail", "pooled")]


def test_one_trade_at_a_time_and_only_an_arms_own_flip_is_free_in_the_bar_it_leaves():
    closed = [tr("b_targets", 2, 6, r=1.0),                        # copied (tie): bars 2 to 6
              tr("b_trail", 1, 4, r=5.0),                          # the trail leads from bar 5 on
              tr("b_trail", 5, 6, r=0.1),                          # its entry while b_learn is in a trade: not taken
              tr("b_trail", 6, 8, r=0.1),                          # another arm's entry in the bar b_learn leaves: not taken
              tr("b_trail", 9, 12, r=0.1),                         # taken
              tr("b_trail", 12, 15, r=0.1, side=-1),               # the same arm's flip at bar 12: taken
              tr("b_targets", 15, 18, r=1.0)]                      # not the leader: ignored
    res = lb.walk(closed, [], one)
    assert picks(res) == [(B, 2, "b_targets", "pooled"), (B, 9, "b_trail", "pooled"), (B, 12, "b_trail", "pooled")]
    assert [t["side"] for t in res["trades"][B]] == [1, 1, -1]
    eq = 10000.0 * 1.01 * 1.001 * 1.001
    assert abs(res["equity"][B] - eq) < 1e-6


def test_an_open_trade_of_the_leader_is_held_and_marked_and_nothing_else_is_taken_meanwhile():
    closed = [tr("b_targets", 1, 3, r=1.0), tr("main", 8, 9, r=9.0), tr("main", 10, 12, r=1.0)]
    res = lb.walk(closed, [op("b_targets", 5, eq0=20000.0, mark=103.0, qty=40.0)], one)
    assert picks(res) == [(B, 1, "b_targets", "pooled"), (B, 5, "b_targets", "pooled")]
    o = res["open"][B]
    assert o["arm"] == "b_targets" and o["side"] == 1 and abs(o["scale"] - 10100.0 / 20000.0) < 1e-12
    assert abs(o["unrealized"] - 40.0 * 3.0 * 10100.0 / 20000.0) < 1e-9      # the arm's open result, at this book's size
    assert len(res["trades"][B]) == 1 and res["next"][X] == ("main", "pooled")   # the hold copy would be next


def test_a_trade_without_a_reading_is_neither_followed_nor_used_for_weights():
    blind = set([T0 - 50 * BAR, T0 + 2 * BAR])
    closed = [tr("b_trail", -50, -40, r=9.0), tr("b_targets", 2, 4), tr("b_targets", 6, 8), tr("main", 7, 9)]
    res = lb.walk(closed, [], lambda c, t: None if t in blind else X)
    assert res["no_reading"] == 2 and picks(res) == [(B, 6, "b_targets", "pooled")]
    assert res["tables"]["pooled"]["scores_r"]["b_trail"] == 0.0    # the +9R with no reading taught nothing


def records(seed, n_days=6):
    """Random records of the six arms on both coins around START_UTC -> closed trades (each arm one trade at a time)."""
    rng = random.Random(seed)
    out = []
    for coin in lb.COINS:
        for arm in lb.ARMS:
            i, eq = -n_days * 96 + rng.randrange(0, 20), 10000.0 + rng.randrange(0, 3000)
            while i < n_days * 96:
                j = i + rng.randrange(1, 40)
                r = round(rng.gauss(0.1, 1.2), 3)
                t = tr(arm, i, j, r=r, coin=coin, side=rng.choice((1, -1)), eq0=eq)
                eq = t["eq_after"]
                out.append(t)
                i = j + rng.choice((0, 0, 1, 3, 8))               # a flip (the same bar) or a wait
    return out


def as_it_stood(closed, cut, bar_done):
    """The arms' records as the engine held them around time `cut`, everything later removed. bar_done False: at the
    close that ends at `cut` (rows closed before it; a trade still running is open; an entry at `cut` is there only if
    its arm was flat, as the Setups book's early entry is). bar_done True: one step later, after the bar that opens at
    `cut` has closed (rows closed in it are written, entries at its open are booked)."""
    if bar_done:
        keep = [t for t in closed if t["t_out"] <= cut]
        live = [t for t in closed if t["t_in"] <= cut < t["t_out"]]
    else:
        keep = [t for t in closed if t["t_out"] < cut]
        live = [t for t in closed if t["t_in"] < cut <= t["t_out"]]
        busy = set((t["arm"], t["coin"]) for t in live)
        live += [t for t in closed if t["t_in"] == cut < t["t_out"] and (t["arm"], t["coin"]) not in busy]
    opens = [dict(op(t["arm"], 0, coin=t["coin"], side=t["side"], eq0=t["eq0"]), t_in=t["t_in"]) for t in live]
    return keep, opens


@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_no_choice_changes_when_later_trades_are_removed_from_the_arms_records(seed):
    closed = records(seed)
    bucket = lambda c, t: lb.BUCKETS[(t // BAR + len(c)) % 4]       # noqa: E731  (a fixed reading per coin and time)
    full = lb.walk(closed, [], bucket)
    assert len(full["choices"]) > 20 and len(set(c["arm"] for c in full["choices"])) > 1
    assert len(set(c["table"] for c in full["choices"])) > 1        # pooled first, then the buckets' own tables
    rng = random.Random(seed)
    for _ in range(40):
        cut = T0 + rng.randrange(1, 6 * 96) * BAR
        for bar_done in (False, True):
            keep, opens = as_it_stood(closed, cut, bar_done)
            part = lb.walk(keep, opens, bucket)
            if bar_done:
                assert part["choices"] == [c for c in full["choices"] if c["t_in"] <= cut]
            else:
                assert [c for c in part["choices"] if c["t_in"] < cut] == [c for c in full["choices"] if c["t_in"] < cut]
                assert all(c in full["choices"] for c in part["choices"])
            done = [t for c in lb.COINS for t in part["trades"][c]]
            want = [t for c in lb.COINS for t in full["trades"][c] if t["t_out"] < cut or (bar_done and t["t_out"] == cut)]
            assert [(t["coin"], t["t_in"], t["arm"], t["pnl"]) for t in done] == \
                [(t["coin"], t["t_in"], t["arm"], t["pnl"]) for t in want]
    # and the one entry, said directly: remove every arm trade that closed at or after an entry, the choice there stays
    for ch in full["choices"][::5]:
        before = [t for t in closed if t["t_out"] < ch["t_in"]]
        mine = [t for t in closed if t["coin"] == ch["coin"] and t["arm"] == ch["arm"] and t["t_in"] == ch["t_in"]]
        alone = lb.walk(before + mine, [], bucket)
        assert [c for c in alone["choices"] if c["t_in"] == ch["t_in"] and c["coin"] == ch["coin"]] == [ch]


# ------------------------------------------------------------------ the files: read only, recomputed, hardened
def test_from_files_it_copies_writes_its_record_and_gives_the_same_bytes_after_a_restart(tmp_path):
    arms = {("b_targets", B): [tr("b_targets", -30, -20, r=1.0), tr("b_targets", 4, 9, r=2.0)],
            ("b_trail", B): [tr("b_trail", -30, -25, r=0.5), tr("b_trail", 5, 7, r=1.0)],
            ("main", E): [tr("main", 3, 12, r=-1.0, coin=E)]}
    st = {"b_targets": {E: {"pos": -1, "entry": 50.0, "qty": 20.0, "eq": 10000.0, "t_in_ms": T0 + 20 * BAR, "stop": 53.0,
                            "stop0": 53.0, "mark": 49.0, "why_in": "FORCED"}, B: {"pos": 0}}}
    lv, d, sp = planted(tmp_path, arms, st)
    before = dict((p, open(os.path.join(lv, p), "rb").read()) for p in os.listdir(lv))
    blk = lb.step(live_dir=lv, data_dir=d, state_path=sp)
    for p, body in before.items():                                  # the arms' records are read, never written
        assert open(os.path.join(lv, p), "rb").read() == body
    assert blk["status"] == "running" and blk["trades"] == 1 and blk["label"] == "paper only, NOT passed"
    rows = own_rows(lv, B)
    assert list(rows[0].keys()) == lb.COLS and len(rows) == 1 and rows[0]["arm"] == "b_targets"
    assert rows[0]["bucket"] in lb.BUCKETS and rows[0]["table"] == "pooled" and rows[0]["time_in"] == lb._utc(T0 + 4 * BAR)
    assert abs(float(rows[0]["pnl_usd"]) - 200.0) < 1e-9 and abs(float(rows[0]["equity"]) - 10200.0) < 1e-9
    assert not os.path.exists(own_file(lv, E))                      # no closed trade on ETH: no file
    c = blk["coins"]
    assert c[B]["status"] == "FLAT" and c[B]["trades"] == 1 and c[B]["would_follow"] == "b_targets"
    assert c[E]["status"] == "SHORT" and c[E]["following"] == "b_targets" and c[E]["unrealized_usd"] == 20.0
    assert blk["followed"]["b_targets"] == 1 and blk["equity"] == 20220.0 and blk["next_read_at"] == 30
    same = blk["same_days"]
    assert same["b_learn"] == {"trades": 1, "wins": 1, "sum_r": 2.0, "ret_pct": 1.0}
    assert same["b_trail"]["sum_r"] == 1.0 and same["main"]["sum_r"] == -1.0 and blk["best_single_arm"] == "b_targets"
    assert blk["left_out"] == {"no_reading": 0, "odd_rows": 0} and 0.0 <= c[B]["flat_share_pct"] <= 100.0
    json.dumps(blk, allow_nan=False)                                # the block is plain JSON
    # a restart: nothing was kept, the same bytes come back, and an unchanged record is not written again
    body, stamp = open(own_file(lv, B), "rb").read(), os.path.getmtime(own_file(lv, B))
    os.utime(own_file(lv, B), (stamp - 100, stamp - 100))
    assert lb.step(live_dir=lv, data_dir=d, state_path=sp)["coins"] == blk["coins"]
    assert os.path.getmtime(own_file(lv, B)) == stamp - 100
    os.remove(own_file(lv, B))                                      # its record lost: rebuilt from the arms' records
    lb.step(live_dir=lv, data_dir=d, state_path=sp)
    assert open(own_file(lv, B), "rb").read() == body
    # the open ETH trade closes: the arm's row arrives while its state still shows it open (file first, then state)
    write_arm(lv, "b_targets", E, [dict(tr("b_targets", 20, 26, r=0.5, coin=E, side=-1), p_in=50.0)])
    blk = lb.step(live_dir=lv, data_dir=d, state_path=sp)
    assert blk["trades"] == 2 and blk["coins"][E]["status"] == "FLAT" and len(own_rows(lv, E)) == 1
    assert lb.step(live_dir=lv, data_dir=d, state_path=sp, write=False)["trades"] == 2


def test_from_files_the_trades_before_a_cut_do_not_change_when_everything_after_it_is_removed(tmp_path):
    closed = [t for t in records(11, n_days=2)]
    by = {}
    for t in closed:
        by.setdefault((t["arm"], t["coin"]), []).append(t)
    btc, eth = bars(seed=21, wild_from=-60), bars(seed=22, wild_from=40)
    lv, d, sp = planted(tmp_path / "full", by, btc=btc, eth=eth)
    _blk, full, ok = lb.compute(lv, d, sp)
    assert all(ok.values()) and sum(len(v) for v in full.values()) > 5
    assert len(set(t["bucket"] for v in full.values() for t in v)) > 1          # the bars give more than one state
    for cut_bar in (60, 110, 170):
        cut = T0 + cut_bar * BAR
        part = dict((k, [t for t in v if t["t_out"] <= cut]) for k, v in by.items())   # after the bar at `cut` closed
        state = {}
        for (arm, coin), v in by.items():
            for t in v:
                if t["t_in"] <= cut < t["t_out"]:                    # still running then: an open trade in the state
                    state.setdefault(arm, {})[coin] = {"pos": t["side"], "entry": t["p_in"], "qty": t["qty"],
                                                       "eq": t["eq0"], "t_in_ms": t["t_in"], "mark": t["p_in"]}
        lv2, d2, sp2 = planted(tmp_path / ("cut%d" % cut_bar), part, state,
                               btc=[b for b in btc if b[0] <= cut], eth=[b for b in eth if b[0] <= cut])
        _b, got, ok = lb.compute(lv2, d2, sp2)
        assert all(ok.values())
        for c in lb.COINS:
            want = [(t["t_in"], t["arm"], t["bucket"], t["table"], t["pnl"]) for t in full[c] if t["t_out"] <= cut]
            assert [(t["t_in"], t["arm"], t["bucket"], t["table"], t["pnl"]) for t in got[c]] == want


def test_missing_files_duplicated_rows_and_odd_state_leave_a_trade_out_and_never_raise(tmp_path):
    # nothing at all: no bars, no records, no state
    e = str(tmp_path / "empty")
    blk = lb.step(live_dir=e, data_dir=e, state_path=os.path.join(e, "none.json"))
    assert blk["status"] == "the bar files could not be read at this step" and blk["trades"] == 0
    assert not os.path.exists(e) or not os.listdir(e)               # and it wrote nothing
    good = tr("b_targets", 4, 9, r=2.0)
    arms = {("b_targets", B): [good, good,                         # the same row twice (a crash between file and state)
                               tr("b_targets", 6, 12, r=1.0),      # starts before the one before it ended
                               dict(tr("b_targets", 20, 24), r=NAN),                   # no R: not a reward
                               dict(tr("b_targets", 30, 34), eq_after=-5.0),           # an equity that cannot be
                               dict(tr("b_targets", 40, 38))]}     # out before in
    st = {"b_targets": {E: {"pos": 1, "entry": None, "qty": 1.0, "eq": 10000.0, "t_in_ms": T0 + 5 * BAR},   # no entry
                        B: {"pos": 1, "entry": 100.0, "qty": 1.0, "eq": 10000.0, "t_in_ms": T0 + 5 * BAR}},  # inside a closed trade
          "main": {B: "nonsense", E: {"pos": -1, "entry": 50.0, "qty": 2.0, "eq": 0.0, "t_in_ms": T0 + 5 * BAR}},
          "b_trail": [1, 2, 3]}
    lv, d, sp = planted(tmp_path / "odd", arms, st)
    with open(os.path.join(lv, "shadow_trades_b_trail_%s.csv" % B), "w") as fh:
        fh.write("t_in_ms,t_out_ms,side\nnot,a,row\n12,,\n")        # a garbled record
    with open(os.path.join(lv, "shadow_trades_main_%s.csv" % B), "w") as fh:
        fh.write("")                                                # an empty one
    blk = lb.step(live_dir=lv, data_dir=d, state_path=sp)
    assert blk["status"] == "running" and blk["trades"] == 1 and len(own_rows(lv, B)) == 1
    assert blk["left_out"]["odd_rows"] == 9                         # 4 odd rows, 2 garbled lines, 3 odd open trades
    assert blk["coins"][B]["status"] == "FLAT" and blk["coins"][E]["status"] == "FLAT"
    # the state file itself unreadable: open trades are unknown, said, and the record on file is not touched
    with open(sp, "w") as fh:
        fh.write("{ not json")
    body = open(own_file(lv, B), "rb").read()
    blk = lb.step(live_dir=lv, data_dir=d, state_path=sp)
    assert "could not be read" in blk["status"] and open(own_file(lv, B), "rb").read() == body


def test_a_bar_file_that_cannot_be_read_never_shortens_the_record(tmp_path):
    lv, d, sp = planted(tmp_path, {("b_targets", B): [tr("b_targets", 4, 9, r=2.0)]})
    assert lb.step(live_dir=lv, data_dir=d, state_path=sp)["trades"] == 1
    body = open(own_file(lv, B), "rb").read()
    with open(os.path.join(d, "%s_15m.csv" % B.lower()), "a") as fh:
        fh.write("garbled,line\n")                                  # signals.read_bars refuses the whole read
    blk = lb.step(live_dir=lv, data_dir=d, state_path=sp)
    assert blk["trades"] == 0 and blk["left_out"]["no_reading"] == 1 and "could not be read" in blk["status"]
    assert open(own_file(lv, B), "rb").read() == body               # the trade is not lost from the record
    # too little history for the look-backs: no reading, so nothing is followed (and nothing crashes)
    lv2, d2, sp2 = planted(tmp_path / "short", {("b_targets", B): [tr("b_targets", 4, 9, r=2.0)]},
                           btc=bars(n_before=10 * 96), eth=bars(n_before=10 * 96, seed=8))
    blk = lb.step(live_dir=lv2, data_dir=d2, state_path=sp2)
    assert blk["status"] == "running" and blk["trades"] == 0 and blk["left_out"]["no_reading"] == 1
    assert blk["coins"][B]["bucket_now"] is None and not os.path.exists(own_file(lv2, B))


def test_before_its_start_it_only_warms_up(tmp_path):
    warm = [tr("b_trail", -60, -50, r=3.0), tr("b_targets", -40, -30, r=1.0)]
    lv, d, sp = planted(tmp_path, {("b_trail", B): [warm[0]], ("b_targets", B): [warm[1]]},
                        btc=bars(n_after=0), eth=bars(n_after=0, seed=8))
    blk = lb.step(live_dir=lv, data_dir=d, state_path=sp)
    assert blk["status"].startswith("not started") and blk["trades"] == 0 and blk["equity"] == 20000.0
    assert blk["tables"]["pooled"]["leader"] == "b_trail" and blk["tables"]["pooled"]["closed_trades"] == 2
    assert all(v["trades"] == 0 for v in blk["same_days"].values()) and blk["best_single_arm"] is None
    assert not os.path.exists(own_file(lv, B))


# ------------------------------------------------------------------ on the scoreboard like a shadow book
def test_the_scoreboard_shows_it_as_a_shadow_not_passed_and_survives_its_failure(tmp_path, monkeypatch):
    arms = {("b_targets", B): [tr("b_targets", 4, 9, r=2.0), tr("b_targets", 12, 15, r=-1.0)],
            ("b_trail", E): [tr("b_trail", 2, 5, r=1.0, coin=E)]}
    root = tmp_path / "root"
    lv, d, sp = planted(root, arms)
    os.makedirs(str(root / "out"))
    os.rename(lv, str(root / "out" / "live"))
    monkeypatch.setattr(reports, "ROOT", str(root))
    monkeypatch.setattr(reports, "SCOREBOARD_JSON", str(root / "out" / "live" / "scoreboard.json"))
    monkeypatch.setattr(data, "DATA_DIR", d)
    monkeypatch.setattr(lb, "STATE_PATH", sp)
    said = []
    out = reports.scoreboard([], log=said.append)
    row = dict((r["book"], r) for r in out["rows"])
    mine = row["b_learn"]
    assert mine["title"] == lb.SCOREBOARD_TITLE and mine["kind"] == "shadow" and "NOT passed" in mine["title"]
    assert mine["trades"] == 2 and mine["verdict"].startswith("too few trades to judge (2 of 30)")
    assert mine["net_usd"] == round(200.0 - 102.0, 2)               # +2% of 10,000, then -1% of 10,200
    assert row["b_targets"]["title"] == "Shadow: b_targets" and row["b_trail"]["trades"] == 1    # the others as before
    assert out["exit_learner"]["trades"] == 2 and out["exit_learner"]["book"] == "b_learn"
    with open(str(root / "out" / "live" / "scoreboard.json")) as fh:
        assert json.load(fh)["exit_learner"]["hypothesis"] == "H109"
    assert not any("exit learner" in s for s in said)
    monkeypatch.setattr(lb, "step", lambda *a, **k: 1 / 0)          # the learner fails: one line, the scoreboard goes on
    out = reports.scoreboard([], log=said.append)
    assert "exit_learner" not in out and any(s.startswith("exit learner:") for s in said)
    row = dict((r["book"], r) for r in out["rows"])
    assert row["b_targets"]["trades"] == 2 and row["b_learn"]["trades"] == 2 and "paper_desk" in out


def test_its_bar_reader_reads_what_the_engines_reader_reads_and_refuses_what_it_refuses(tmp_path):
    from engine15 import signals
    d = str(tmp_path)
    rows = bars(n_before=30 * 96, n_after=40, seed=9)
    write_bars(d, B, rows)
    path = signals.bar_path(d, B)
    for since in (T0 - 5 * BAR, T0 - 2000 * BAR, T0 - 10 ** 12, T0 + 38 * BAR):
        want = signals.read_bars(path, since, cap=lb.BARS_CAP)
        ts, o, h, l, c = lb.read_bars(path, since, chunk=4096)
        assert [tuple(x) for x in zip(ts.tolist(), o.tolist(), h.tolist(), l.tolist(), c.tolist())] == want
    assert lb.read_bars(path, T0 + 39 * BAR) is None and signals.read_bars(path, T0 + 39 * BAR) == []   # nothing newer
    with open(path, "a") as fh:
        fh.write("%d,1.0,1.0,1.0" % (T0 + 40 * BAR))                # a line still being written: not read, not fatal
    assert len(lb.read_bars(path, T0 - 5 * BAR)[0]) == 44 == len(signals.read_bars(path, T0 - 5 * BAR))
    for junk in ("\n%d,1.0,1.0,1.0,1.0,1,1\n" % (T0 + 30 * BAR),   # a time that goes back
                 "\n%d,1.0,1.0,-1.0,1.0,1,1\n" % (T0 + 41 * BAR),  # a price below zero
                 "\n%d,1.0,1.0,1.0,1.0,1,1\n" % (T0 + 41 * BAR + 7),   # not a bar time
                 "\nhalf,a\n"):
        write_bars(d, E, rows)
        with open(signals.bar_path(d, E), "a") as fh:
            fh.write("%d,1.0,1.0,1.0,1.0,1,1" % (T0 + 40 * BAR) + junk)
        assert lb.read_bars(signals.bar_path(d, E), T0 - 5 * BAR) is None
        assert signals.read_bars(signals.bar_path(d, E), T0 - 5 * BAR) is None
    assert lb.read_bars(os.path.join(d, "none.csv"), 0) is None
    open(os.path.join(d, "empty.csv"), "w").close()
    assert lb.read_bars(os.path.join(d, "empty.csv"), 0) is None
