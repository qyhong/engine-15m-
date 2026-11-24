# -*- coding: utf-8 -*-
"""Back at a capitulation low: the retest levels playbook9 recomputes from the bars and the two Telegram notices.
A NOTICE, not a setup, not a hypothesis: no trade is opened, closed or changed by any of it.

1. The level rules on made-up bars, each held to research/h116_retest_capitulation_low.machine: the level, each state,
   each way a level dies, the same-low rule, the 30-day life, the break.
2. Parity with that script on the real BTC and ETH bars (skipped when the files are not there): at a set of test dates
   the 93-day tail gives the script's levels, arming bars, first-touch bars and states; and at the end of the data copy
   of 24 Nov 2026 it finds the two levels H116 published.
3. No look-ahead: what is known at a bar is the same when later bars are appended.
4. The step: the levels sit beside the trades and never change them; no new bar, no work; a failure is one line.
5. The page block.
6. The two notice texts, held exactly.
7. Delivery: once per level, across a restart, never after 48 hours, a failed send retried, the owner's chat only, and
   the capitulation-long cards as they were.

Every file a test writes is under pytest's tmp_path; the real data folder is only read.
"""
import inspect
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import test_playbook9 as tp  # noqa: E402  (its synthetic market and its fake bot)
from engine15 import data  # noqa: E402
from engine15 import playbook9 as p9  # noqa: E402
from engine15 import telegram_notify as tn  # noqa: E402

h116 = pytest.importorskip("research.h116_retest_capitulation_low")
h107 = pytest.importorskip("research.h107_capitulation_rebound")

BTC, ETH = "BTCUSDT", "ETHUSDT"
QUIET = tp.QUIET
BAR = p9.BAR_MS
DAY_BARS = 96
LIFE_BARS = p9.LEVEL_LIFE_DAYS * DAY_BARS
# the script's state names -> this module's
STATES = {"undercut": ("dead",), "no_bounce": ("waiting",), "armed_no_touch": ("armed",), "retest": ("touched", "broken")}


def held_to_the_script(mine, ref, l):
    """Level for level: the trigger bar, the low, its bar, the last bar, the arming bar, the undercut bar, the first
    touch and the state are the script's; the break is the script's sweep bar where the script looked for one, and in
    every case the first bar from the first touch to the last bar with a low under the level."""
    assert len(mine) == len(ref)
    for m, r in zip(mine, ref):
        for key in ("k", "L", "b", "e", "a", "u", "f"):
            assert m[key] == r[key], (key, m, r)
        assert m["state"] in STATES[r["state"]], (m, r)
        if r["s"] is not None:
            assert m["s"] == r["s"]
        elif r["c1"] is None:                                       # the script walked every bar to e and saw no sweep
            assert m["s"] is None
        if m["f"] is None:
            assert m["s"] is None and m["state"] in ("waiting", "dead", "armed")
        else:
            under = np.flatnonzero(l[m["f"]:m["e"] + 1] < m["L"])
            assert m["s"] == (m["f"] + int(under[0]) if len(under) else None)
            assert m["state"] == ("broken" if len(under) else "touched")


# ---------------------------------------------------------------- 1. the rules on made-up bars
N, K = 4000, 100                                                    # bars; the trigger bar. The low (100.0) is at bar K - 4
T0_MS = int(pd.Timestamp("2022-01-01", tz="UTC").value // 10**6)
ARM = (1.0 + p9.LEVEL_ARM) * 100.0                                  # 105
ZONE = (1.0 + p9.LEVEL_ZONE) * 100.0                                # 101.5 (as the float the rule computes)


def flat(n=N):
    """Flat bars at 104 with a low of 100 at bar K - 4 and rule A's onset at bar K."""
    open_ms = T0_MS + BAR * np.arange(n, dtype="int64")
    c = np.full(n, 104.0)
    fx = {"open_ms": open_ms, "t": pd.to_datetime(open_ms, unit="ms", utc=True), "o": c.copy(), "h": c + 0.2,
          "l": c - 0.2, "c": c, "atr1h": np.full(n, 1.0), "A": np.zeros(n, bool)}
    fx["l"][K - 4] = 100.0
    fx["A"][K] = True
    return fx


def bar(fx, j, low=None, high=None):
    if low is not None:
        fx["l"][j] = low
    if high is not None:
        fx["h"][j] = high


def levels(fx, n=None):
    fx["low16"] = pd.Series(fx["l"]).rolling(16, min_periods=16).min().values
    mine = p9.levels_of(fx, n)
    ref, _dup = h116.machine(fx, n=n)
    held_to_the_script(mine, ref, fx["l"])
    return mine


def one(fx, n=None):
    out = levels(fx, n)
    assert len(out) == 1
    return out[0]


def test_the_constants_are_h116s():
    assert (p9.LEVEL_ZONE, p9.LEVEL_ARM, p9.LEVEL_LIFE_DAYS) == (h116.REG["zone"], h116.REG["bounce"], h116.REG["life_days"])
    assert (tn.ZONE_PCT, tn.ZONE_DROP, tn.ZONE_BOUNCE_ATR) == (p9.LEVEL_ZONE, p9.DROP, p9.BOUNCE_ATR)
    assert tn.ZONE_COINS == p9.ASSETS and tn.ZONE_BAR_S * 1000 == p9.BAR_MS
    assert tn.ZONE_WINDOW_S == p9.LEVEL_KEEP_DAYS * 86400 == 48 * 3600     # a level is listed as long as it can be sent
    assert p9.LEVEL_TAIL_BARS == 93 * 96 and p9.LEVEL_TAIL_DAYS == 30 + 2 + 30 + 30 + 1


def test_the_level_is_the_low_the_trigger_came_off_and_waits_for_a_bounce():
    lv = one(flat())
    assert (lv["k"], lv["L"], lv["b"], lv["e"]) == (K, 100.0, K - 4, K + LIFE_BARS)
    assert lv["state"] == "waiting" and lv["a"] is None and lv["f"] is None       # 104.2 is not 5% above 100
    fx = flat()
    bar(fx, K - 2, low=100.0)                                       # the same low twice in the 16 bars: b is the FIRST
    assert one(fx)["b"] == K - 4


def test_armed_at_the_first_high_five_percent_above_the_low_also_before_the_trigger():
    fx = flat()
    bar(fx, 200, high=np.nextafter(ARM, 0))                         # a hair under 105: not armed
    assert one(fx)["state"] == "waiting"
    bar(fx, 250, high=ARM)                                          # exactly 105: armed
    bar(fx, 300, high=120.0)
    lv = one(fx)
    assert lv["state"] == "armed" and lv["a"] == 250 and lv["f"] is None
    fx = flat()
    bar(fx, K - 2, high=106.0)                                      # two bars after the low, before the trigger bar
    assert one(fx)["a"] == K - 2
    fx = flat()
    bar(fx, K - 4, high=106.0)                                      # the low's own bar does not arm (a bar AFTER b)
    assert one(fx)["state"] == "waiting"


def test_dead_when_the_low_is_undercut_before_or_in_the_arming_bar():
    fx = flat()
    bar(fx, 150, low=99.99)                                         # under the low before any bounce
    bar(fx, 200, high=106.0)
    bar(fx, 300, low=101.0)
    lv = one(fx)
    assert lv["state"] == "dead" and lv["u"] == 150 and lv["a"] is None and lv["f"] is None and lv["s"] is None
    fx = flat()
    bar(fx, 200, high=106.0, low=99.0)                              # the bounce and the undercut in one bar: dead
    assert one(fx)["state"] == "dead" and one(fx)["u"] == 200
    fx = flat()
    bar(fx, 150, low=100.0)                                         # AT the low is not under it
    bar(fx, 200, high=106.0)
    assert one(fx)["state"] == "armed"
    fx = flat()
    bar(fx, K - 1, low=99.0)                                        # a lower low inside the 16 bars is simply the level
    lv = one(fx)
    assert (lv["L"], lv["b"], lv["state"], lv["a"]) == (99.0, K - 1, "armed", K)     # 104.2 is 5% above 99


def test_first_touch_is_the_first_low_in_the_zone_after_both_the_arming_bar_and_the_trigger():
    fx = flat()
    bar(fx, 200, high=106.0)
    bar(fx, 300, low=np.nextafter(ZONE, np.inf))                    # a hair above the zone: no touch
    assert one(fx)["state"] == "armed"
    bar(fx, 310, low=ZONE)                                          # exactly 1.5% above the low: the first touch
    bar(fx, 320, low=100.5)
    lv = one(fx)
    assert (lv["state"], lv["a"], lv["f"], lv["s"]) == ("touched", 200, 310, None)
    fx = flat()
    bar(fx, 150, low=101.0)                                         # in the zone before it is armed: not a touch
    bar(fx, 200, high=106.0, low=101.0)                             # nor in the arming bar itself
    assert one(fx)["state"] == "armed"
    bar(fx, 201, low=101.0)
    assert one(fx)["f"] == 201
    fx = flat()
    bar(fx, K - 3, high=106.0)                                      # armed before the trigger ...
    bar(fx, K - 1, low=100.4)
    bar(fx, K, low=100.4)                                           # ... a low in the zone up to the trigger bar is no touch
    assert one(fx)["state"] == "armed"
    bar(fx, K + 1, low=101.2)
    assert one(fx)["f"] == K + 1


def test_broken_at_the_first_low_under_the_level_from_the_first_touch_on():
    fx = flat()
    bar(fx, 200, high=106.0)
    bar(fx, 300, low=101.0)
    bar(fx, 310, low=100.0)                                         # AT the low: touched, not broken
    assert one(fx)["state"] == "touched"
    bar(fx, 330, low=99.99)
    bar(fx, 340, low=95.0)
    lv = one(fx)
    assert (lv["state"], lv["f"], lv["s"]) == ("broken", 300, 330)
    fx = flat()
    bar(fx, 200, high=106.0)
    bar(fx, 300, low=99.0)                                          # into the zone and through the low in one bar
    lv = one(fx)
    assert (lv["state"], lv["f"], lv["s"]) == ("broken", 300, 300)


def test_the_same_low_again_within_30_days_is_one_level_and_after_30_days_a_new_one():
    for gap, n_levels in ((8, 1), (LIFE_BARS, 1), (LIFE_BARS + 1, 2)):
        fx = flat()
        k2 = K + gap
        bar(fx, k2 - 3, low=100.0)                                  # exactly the same low, and rule A fires again
        fx["A"][k2] = True
        out = levels(fx)
        assert len(out) == n_levels, gap
        assert (out[0]["k"], out[0]["L"], out[0]["b"]) == (K, 100.0, K - 4)
        if n_levels == 2:
            assert (out[1]["k"], out[1]["L"], out[1]["b"]) == (k2, 100.0, k2 - 3)
    fx = flat()
    bar(fx, K + 5, low=99.5)                                        # another low: its own level, and the first one is dead
    fx["A"][K + 8] = True
    out = levels(fx)
    assert [(lv["L"], lv["state"]) for lv in out] == [(100.0, "dead"), (99.5, "waiting")]


def test_a_level_counts_only_at_bars_that_open_within_30_days_of_the_trigger_bar():
    e = K + LIFE_BARS
    fx = flat()
    bar(fx, e + 1, high=106.0)                                      # the bounce one bar too late
    assert one(fx)["state"] == "waiting"
    bar(fx, e, high=106.0)                                          # in the last bar that counts
    assert one(fx)["a"] == e
    fx = flat()
    bar(fx, 200, high=106.0)
    bar(fx, e + 1, low=101.0)                                       # the touch one bar too late
    assert one(fx)["state"] == "armed"
    bar(fx, e, low=101.0)
    bar(fx, e + 1, low=99.0)                                        # ... and a break after the last bar is not a break
    lv = one(fx)
    assert (lv["state"], lv["f"], lv["s"], lv["e"]) == ("touched", e, None, e)
    fx = flat()
    fx["open_ms"][K + 50:] += 3 * 86400000                          # three days without bars: the life is time, not bars
    fx["t"] = pd.to_datetime(fx["open_ms"], unit="ms", utc=True)
    assert one(fx)["e"] == e - 3 * DAY_BARS


def test_the_rows_keep_a_level_for_its_30_days_and_two_more():
    fx = flat()
    bar(fx, 200, high=106.0)
    bar(fx, 300, low=101.0)
    bar(fx, 330, low=99.0)
    bar(fx, 400, low=97.5)
    e = K + LIFE_BARS
    cut = lambda n: dict((key, v[:n]) for key, v in fx.items())    # noqa: E731
    rows = p9.level_rows(BTC, cut(500), levels(fx, 500))
    assert len(rows) == 1
    r = rows[0]
    at = lambda i: T0_MS + BAR * i                                  # noqa: E731
    assert r == {"id": "BTCUSDT|%d" % (at(K) + BAR), "asset": BTC, "L": 100.0, "zone_top": ZONE, "arm_price": ARM,
                 "state": "broken", "live": True, "low_open_ms": at(K - 4), "trigger_close_ms": at(K) + BAR,
                 "live_until_ms": at(e) + BAR, "armed_open_ms": at(200), "dead_open_ms": None, "touch_open_ms": at(300),
                 "broken_open_ms": at(330), "new_low": 97.5}
    assert p9.level_rows(BTC, cut(340), levels(fx, 340))[0]["new_low"] == 99.0       # the new low SO FAR
    last_live = p9.level_rows(BTC, cut(e), levels(fx, e))[0]                         # the newest bar is e - 1
    assert last_live["live"] is True
    assert p9.level_rows(BTC, cut(e + 1), levels(fx, e + 1))[0]["live"] is False      # its last bar has closed
    keep = e + p9.LEVEL_KEEP_DAYS * DAY_BARS
    assert len(p9.level_rows(BTC, cut(keep + 1), levels(fx, keep + 1))) == 1          # still listed two days on ...
    assert p9.level_rows(BTC, cut(keep + 2), levels(fx, keep + 2)) == []              # ... and then dropped
    assert p9.level_rows(BTC, cut(0), []) == []
    json.dumps(rows, allow_nan=False)


# ---------------------------------------------------------------- 2. parity with the research script on the real bars
def _real(coin):
    ddir = os.path.join(ROOT, "data")
    for suf in ("_15m.csv", "_funding.csv"):
        if not os.path.exists(os.path.join(ddir, coin.lower() + suf)):
            pytest.skip("no %s%s in data/: the parity check needs the real bars" % (coin.lower(), suf))
    df, fund = h107.load(coin, ddir)
    fx = h107.features(df, fund)
    ref, dup = h116.machine(fx)                                     # every level of the whole file, as the script finds them
    return {"coin": coin, "df": df, "fx": fx, "ref": ref, "dup": dup, "open_ms": data.to_ms(df.index)}


@pytest.fixture(scope="module", params=p9.ASSETS)
def real(request):
    return _real(request.param)


def test_parity_on_the_whole_file_every_level_is_the_scripts(real):
    mine = p9.features(real["df"], None)
    got = p9.levels_of(mine)
    held_to_the_script(got, real["ref"], real["fx"]["l"])
    assert len(got) >= 50 and real["dup"] >= 10
    assert sum(lv["state"] == "dead" for lv in got) >= 5 and sum(lv["s"] is not None for lv in got) >= 20
    # the same-low rule on this history: every repeat came within four hours of the level's own trigger (the same low
    # bar), so the chain of equal lows across 30 days that no tail could follow never happened here
    t, by_low = real["fx"]["t"], {}
    made = set(lv["k"] for lv in real["ref"])
    for lv in real["ref"]:
        by_low.setdefault(lv["L"], []).append(lv["k"])
    for k in np.flatnonzero(real["fx"]["A"]):
        if int(k) not in made:
            first = max(x for x in by_low[float(real["fx"]["low16"][k])] if x < k)
            assert t[k] - t[first] <= pd.Timedelta(hours=4)


def _test_ends(real):
    """The test dates: for every level of the file its trigger bar, its first-touch bar, its break bar and the last bar
    it is listed at, the bar after that, and 30 random bars."""
    n, ends = len(real["df"]), set()
    mine = p9.levels_of(p9.features(real["df"], None))
    for lv in mine:
        ends |= {lv["k"], lv["f"], lv["s"], lv["e"] + p9.LEVEL_KEEP_DAYS * DAY_BARS, lv["e"] + p9.LEVEL_KEEP_DAYS * DAY_BARS + 1}
    rng = np.random.RandomState(20261124)
    ends |= set(rng.randint(p9.LEVEL_TAIL_BARS, n, 30).tolist()) | {n - 1}
    return sorted(e for e in ends if e is not None and p9.LEVEL_TAIL_BARS <= e < n)


def test_parity_at_the_test_dates_the_93_day_tail_gives_the_scripts_levels_bars_and_states(real):
    coin, df, fx, open_ms = real["coin"], real["df"], real["fx"], real["open_ms"]
    ends, compared, states = _test_ends(real), 0, set()
    assert len(ends) >= 100
    listed = (p9.LEVEL_LIFE_DAYS + p9.LEVEL_KEEP_DAYS) * 86400000
    for end in ends:
        cut = df.iloc[end + 1 - p9.LEVEL_TAIL_BARS:end + 1]            # what the live step reads when bar `end` is the newest
        g = p9.features(cut, None)
        got = p9.levels_of(g)
        rows = p9.level_rows(coin, g, got)
        ref, _dup = h116.machine(fx, n=end + 1)                        # the script on the whole file up to that bar
        want = [lv for lv in ref if int(open_ms[lv["k"]]) >= int(open_ms[end]) - listed]
        off = end + 1 - len(cut)                                       # tail index -> file index
        mine = [lv for lv in got if int(g["open_ms"][lv["k"]]) >= int(open_ms[end]) - listed]
        shifted = [dict(lv, **dict((key, None if lv[key] is None else lv[key] + off) for key in "kbeaufs")) for lv in mine]
        held_to_the_script(shifted, want, fx["l"][:end + 1])
        assert [r["id"] for r in rows] == ["%s|%d" % (coin, int(open_ms[lv["k"]]) + BAR) for lv in want], end
        for r, lv in zip(rows, want):
            at = lambda i: None if i is None else int(open_ms[i])   # noqa: E731
            assert (r["L"], r["low_open_ms"], r["armed_open_ms"], r["touch_open_ms"], r["dead_open_ms"]) == (
                lv["L"], at(lv["b"]), at(lv["a"]), at(lv["f"]), at(lv["u"])), (end, r, lv)
            assert r["state"] in STATES[lv["state"]] and r["zone_top"] == (1 + h116.REG["zone"]) * lv["L"]
            assert r["live_until_ms"] == int(open_ms[lv["k"]]) + p9.LEVEL_LIFE_DAYS * 86400000 + BAR
            states.add(r["state"])
        compared += len(want)
    assert compared >= 200 and states == {"waiting", "dead", "armed", "touched", "broken"}


EVENT_LAST = "2026-11-24 04:30"                                     # the last bar of the data copy H116's event.json was made from
EVENT = {BTC: (55130.00, "2026-11-21 06:15", 55956.95, "2026-11-21 06:45"),
         ETH: (1538.00, "2026-11-21 04:00", 1561.07, "2026-11-21 06:30")}


def _ms(text):
    return int(pd.Timestamp(text, tz="UTC").value // 10**6)


def test_parity_at_the_end_of_the_data_copy_the_two_levels_h116_published(real, tmp_path):
    coin, df = real["coin"], real["df"]
    end = int(df.index.searchsorted(pd.Timestamp(EVENT_LAST, tz="UTC")))
    if end >= len(df) or df.index[end] != pd.Timestamp(EVENT_LAST, tz="UTC"):
        pytest.skip("the bars on file do not hold the 24 Nov 2026 04:30 UTC bar")
    L, low_bar, top, armed = EVENT[coin]
    st = {}
    assert p9._step_levels(st, coin, {coin: df}, _ms(EVENT_LAST) + BAR + 20000) is True
    blk = st["zone"][coin]
    assert blk["as_of_utc"] == "2026-11-24 04:45" and blk["bars"] == p9.LEVEL_TAIL_BARS
    lv = [r for r in blk["levels"] if r["trigger_close_ms"] == _ms("2026-11-21 06:45")]
    assert len(lv) == 1 and lv[0] is blk["levels"][-1]              # the newest level of the coin
    lv = lv[0]
    assert lv["L"] == L and lv["low_open_ms"] == _ms(low_bar) and lv["zone_top"] == top
    assert lv["state"] == "armed" and lv["armed_open_ms"] == _ms(armed) and lv["live"] is True
    assert lv["touch_open_ms"] is None and lv["broken_open_ms"] is None and lv["new_low"] is None
    assert lv["live_until_ms"] == _ms("2026-12-21 06:45")
    assert not any(r["live"] and r["state"] in ("waiting", "armed") for r in blk["levels"][:-1])   # the only one waiting
    page = p9.page_levels(st)[coin][-1]
    assert page == {"L": L, "low_utc": low_bar, "made_utc": "2026-11-21 06:45", "zone_top": top, "state": "armed",
                    "live": True, "live_until_utc": "2026-12-21 06:45", "touch_utc": None, "broken_utc": None,
                    "new_low": None, "as_of_utc": "2026-11-24 04:45"}
    path = os.path.join(ROOT, "research", "out", "h116_retest_capitulation_low", "event.json")
    if os.path.exists(path):                                        # ... and it is what the study wrote down
        with open(path, encoding="utf-8") as fh:
            ev = json.load(fh)[coin]
        if ev["last_bar_open_utc"] == EVENT_LAST:
            row = ev["levels"][-1]
            assert (row["L"], row["low_bar_open_utc"], row["retest_zone_top"], row["armed_at_bar_open_utc"]) == (
                L, low_bar, top, armed)
            assert row["state_at_last_bar"] == "armed_no_touch" and row["live_until_close_utc"] == "2026-12-21 06:45"
            assert row["first_touch_bar_open_utc"] is None and abs(blk["atr_1h"] - ev["atr1h_at_last_bar"]) < 1e-9
            assert blk["close"] == ev["last_close"]


def test_the_step_reads_the_real_files_tail_writes_only_its_own_state_and_is_cheap(tmp_path, monkeypatch):
    for coin in p9.ASSETS:
        if not os.path.exists(data.path_for(coin)) or not len(data.load_funding(coin)):
            pytest.skip("no %s bars or funding in data/" % coin)
    path, said = str(tmp_path / "capit_long_state.json"), []
    last = int(p9.tail_bars(BTC, 1).index[-1].value // 10**6)
    rows = p9.step(now_ms=last + BAR + 20000, state_path=path, log=said.append)
    st = tp.state_of(path)
    assert rows == [] and st["closed"] == [] and st["alerts"] == []          # the levels open no trade
    for coin in p9.ASSETS:
        blk = st["zone"][coin]
        assert blk["as_of_open_ms"] == last and blk["bars"] == p9.LEVEL_TAIL_BARS and blk["atr_1h"] > 0
        assert all(r["asset"] == coin for r in blk["levels"])
    assert 0 < p9.LAST_RUN["seconds"] < 3.0                                  # two coins, a new bar each (about 0.1 s in use)
    assert sorted(os.listdir(str(tmp_path))) == ["capit_long_state.json"]    # nothing else is written anywhere
    assert not any("failed" in s or "not updated" in s for s in said)
    stamp = os.path.getmtime(path)
    p9.step(now_ms=last + BAR + 400000, state_path=path, log=said.append)    # no new bar: nothing is read or written
    assert os.path.getmtime(path) == stamp and p9.LAST_RUN["seconds"] < 1.0


# ---------------------------------------------------------------- a synthetic capitulation that is revisited and broken
SK = tp.K                                                           # the bar at whose close the synthetic rule A fires


def retest_frame(up_bars=30, down_bars=30, wait=10, break_bars=8, after=120, back=1.011, under=0.985):
    """tp.synth's capitulation and trigger, then: up to 7% above the low, back down to 1.1% above it (inside the zone),
    ten bars there, down to 1.5% under it, and flat. -> (frame, the low)."""
    base = tp.synth()
    L = float(p9.features(base, None)["low16"][SK])
    head = base.iloc[:SK + 2]
    c0 = float(head["close"].iloc[-1])
    path = list(np.linspace(c0, 1.07 * L, up_bars + 1)[1:]) + list(np.linspace(1.07 * L, back * L, down_bars + 1)[1:])
    path += [back * L] * wait + list(np.linspace(back * L, under * L, break_bars + 1)[1:]) + [under * L] * after
    c = np.array(path)
    o = np.concatenate([[c0], c[:-1]])
    idx = pd.date_range(head.index[-1] + pd.Timedelta(minutes=15), periods=len(c), freq="15min", name="open_time")
    tail = pd.DataFrame({"open": o, "high": np.maximum(o, c) * 1.0002, "low": np.minimum(o, c) * 0.9998, "close": c,
                         "volume": 1.0, "taker_buy": 0.5}, index=idx)
    return pd.concat([head, tail]), L


@pytest.fixture(scope="module")
def market():
    df, L = retest_frame()
    fx = p9.features(df, None)
    lv = p9.levels_of(fx)
    assert len(lv) == 1 and lv[0]["k"] == SK and lv[0]["L"] == L and lv[0]["state"] == "broken"
    assert SK < lv[0]["a"] < lv[0]["f"] < lv[0]["s"] < len(df) - 50
    return {"df": df, "L": L, "fx": fx, "lv": lv[0], "fund": tp.funding(df)}


# ---------------------------------------------------------------- 3. no look-ahead
def test_no_lookahead_what_is_known_at_a_bar_is_the_same_when_later_bars_are_appended(market):
    df, fx, final = market["df"], market["fx"], market["lv"]
    seen = set()
    for n in range(SK - 3, len(df) + 1):
        cut = p9.features(df.iloc[:n], None)                        # the readings recomputed on the bars up to n - 1
        got = p9.levels_of(cut)
        assert got == p9.levels_of(fx, n)                           # ... and the whole frame read up to n - 1: the same
        if n <= SK:
            assert got == []                                        # the trigger bar has not closed: no level yet
            continue
        lv = got[0]
        assert (lv["k"], lv["L"], lv["b"]) == (final["k"], final["L"], final["b"]) and len(got) == 1
        for key in ("a", "f", "s", "u"):                            # a bar, once found, never moves; none is found early
            assert lv[key] == (final[key] if final[key] is not None and final[key] < n else None), (n, key)
        seen.add(lv["state"])
        rows = p9.level_rows(BTC, cut, got)
        assert rows[0]["new_low"] == (None if lv["s"] is None else float(np.min(df["low"].values[lv["s"]:n])))
    assert seen == {"waiting", "armed", "touched", "broken"}


def test_no_lookahead_on_the_real_bars_the_tail_and_the_whole_file_agree_at_each_test_date(real):
    df, open_ms = real["df"], real["open_ms"]
    full = p9.features(df, None)
    listed = (p9.LEVEL_LIFE_DAYS + p9.LEVEL_KEEP_DAYS) * 86400000
    for end in _test_ends(real)[::7]:
        whole = p9.levels_of(full, end + 1)                         # the whole file, read up to that bar only
        off = end + 1 - p9.LEVEL_TAIL_BARS
        tail = p9.levels_of(p9.features(df.iloc[off:end + 1], None))
        tail = [dict(lv, **dict((key, None if lv[key] is None else lv[key] + off) for key in "kbeaufs")) for lv in tail]
        new = lambda lv: int(open_ms[lv["k"]]) >= int(open_ms[end]) - listed     # noqa: E731
        assert [lv for lv in tail if new(lv)] == [lv for lv in whole if new(lv)], end


# ---------------------------------------------------------------- 4. the step
def run(market, path, first, last, log=QUIET, bot=None, monkeypatch=None):
    """The live step after each bar from `first` to `last`; with a bot state, one notice check a minute after each
    step, the bot's state going through its file each time. -> [(bar, notice)]."""
    df, out = market["df"], []
    for i in range(first, last + 1):
        p9.step(bars={BTC: df.iloc[:i + 1]}, now_ms=tp.close_ms(df, i) + 20000, funding={BTC: market["fund"]},
                state_path=path, log=log)
        if bot is not None:
            now = datetime.fromtimestamp(tp.close_ms(df, i) / 1000.0 + 60, timezone.utc)
            out += [(i, card) for card in tn.zone_check(bot, "k", 42, now)]
            saved = json.loads(json.dumps(bot))                     # the bot restarts: its state comes back from its file
            bot.clear()
            bot.update(saved)
    return out


def test_the_levels_sit_beside_the_trades_and_change_none_of_them(market, tmp_path):
    df, lv = market["df"], market["lv"]
    path, said = str(tmp_path / "capit_long_state.json"), []
    run(market, path, SK - 2, len(df) - 1, log=said.append)
    st = tp.state_of(path)
    ref = p9.replay(BTC, df, market["fund"], st["started_ms"])      # the book's own code with no levels anywhere
    assert tp.same(st["closed"], ref["closed"]) and tp.same(st["alerts"], ref["alerts"]) and tp.same(st["books"], ref["books"])
    assert len(st["closed"]) == 2 and len(st["alerts"]) == 1 and p9._valid(st)
    assert set(st) == set(ref) | {"zone", "state_note"} and set(st["zone"]) == {BTC}
    blk = st["zone"][BTC]
    assert blk["as_of_open_ms"] == st["last_open_ms"][BTC] and blk["bars"] == len(df)
    row = blk["levels"][0]
    at = lambda i: int(market["fx"]["open_ms"][i])                  # noqa: E731
    assert (row["state"], row["touch_open_ms"], row["broken_open_ms"]) == ("broken", at(lv["f"]), at(lv["s"]))
    assert row["id"] == st["alerts"][0]["id"]                       # the level carries the id of the trigger that made it
    assert abs(row["new_low"] - 0.985 * market["L"] * 0.9998) < 1e-9 and blk["low_4h"] == row["new_low"]
    words = [s for s in said if "A notice only, no trade" in s]     # one line per change of state
    assert [w.split(" UTC is ")[1].split(" ")[0] for w in words] == ["waiting", "armed", "touched", "broken"]
    assert tp.same(p9.rows_of(st), p9.rows_of(ref))                 # the rows of the two books are what they were


def test_a_step_with_no_new_bar_computes_nothing_and_a_restart_gives_the_same_bytes(market, tmp_path, monkeypatch):
    lv = market["lv"]
    one_, two = str(tmp_path / "one" / "s.json"), str(tmp_path / "two" / "s.json")
    run(market, one_, SK - 2, lv["s"] + 3)
    run(market, two, SK - 2, lv["f"])
    p9.LAST_RUN.clear()                                             # stopped at the first touch; nothing in memory survives
    run(market, two, lv["f"] + 1, lv["s"] + 3)
    with open(one_, "rb") as a, open(two, "rb") as b:
        before = a.read()
        assert before == b.read()                                   # byte for byte the state of the run that never stopped
    calls = []
    real_levels = p9.levels_of
    monkeypatch.setattr(p9, "levels_of", lambda fx, n=None: calls.append(1) or real_levels(fx, n))
    df = market["df"]
    p9.step(bars={BTC: df.iloc[:lv["s"] + 4]}, now_ms=tp.close_ms(df, lv["s"] + 3) + 500000, funding={BTC: market["fund"]},
            state_path=one_, log=QUIET)
    assert calls == []
    with open(one_, "rb") as fh:
        assert fh.read() == before
    run(market, one_, lv["s"] + 4, lv["s"] + 4)
    assert calls == [1]                                             # one new bar: computed once


def test_a_failure_in_the_levels_is_one_line_and_the_trades_go_on(market, tmp_path, monkeypatch):
    lv = market["lv"]
    good, bad, said = str(tmp_path / "good.json"), str(tmp_path / "bad.json"), []
    run(market, good, SK - 2, lv["a"])
    run(market, bad, SK - 2, SK - 1)

    def boom(*a, **k):
        raise RuntimeError("planted")
    monkeypatch.setattr(p9, "levels_of", boom)
    run(market, bad, SK, lv["a"], log=said.append)
    a, b = tp.state_of(good), tp.state_of(bad)
    for key in ("alerts", "books", "closed", "skipped", "last_open_ms", "readings"):
        assert tp.same(a[key], b[key]), key                         # the trades are exactly those of the run that worked
    assert len(b["alerts"]) == 1 and "entry" in b["alerts"][0]      # the trigger was taken and filled as ever
    assert b["zone"][BTC]["levels"] == [] and b["zone"][BTC]["as_of_open_ms"] < a["zone"][BTC]["as_of_open_ms"]   # as last computed
    lines = [s for s in said if "retest levels" in s]
    assert len(lines) == lv["a"] - SK + 1 and not any("failed" in s for s in said)
    assert lines[0] == "playbook9 BTCUSDT: the retest levels were not updated (RuntimeError('planted')); the trades " \
                       "are not affected"
    monkeypatch.undo()
    run(market, bad, lv["a"] + 1, lv["a"] + 1)                      # the next good step has the levels again
    assert tp.state_of(bad)["zone"][BTC]["levels"][0]["state"] == "armed"


def test_an_older_state_without_levels_or_with_a_garbled_one_is_taken_up(market, tmp_path):
    lv, df = market["lv"], market["df"]
    path = str(tmp_path / "s.json")
    run(market, path, SK - 2, lv["a"])
    junks = (None, "x", [1], {BTC: 5}, {BTC: {"as_of_open_ms": "late", "levels": "none"}},
             {ETH: {"levels": [7, {"L": 1.0}, {"L": 1.0, "low_open_ms": "x"}]}, BTC: {"levels": [None]}})
    for j, junk in enumerate(junks):
        st = tp.state_of(path)
        st.pop("zone")
        if junk is not None:
            st["zone"] = junk
        p9.save_state(st, path)
        i = lv["a"] + 1 + j
        said = []
        rows = p9.step(bars={BTC: df.iloc[:i + 1]}, now_ms=tp.close_ms(df, i) + 20000, funding={BTC: market["fund"]},
                       state_path=path, log=said.append)
        assert tp.state_of(path)["zone"][BTC]["levels"][0]["state"] == "armed"
        assert not any("not updated" in s or "failed" in s for s in said) and len(rows) == 2
        assert p9.LAST_RUN["levels"][BTC][0]["state"] == "armed"
    assert p9.LAST_RUN["levels"][ETH] == []                         # a coin with no bars this step: its junk is not shown
    assert p9.page_levels({"zone": 5}) == {} and p9.page_levels({}) == {}


def test_the_bars_asked_for_are_the_93_day_tail_and_no_bar_that_has_not_closed(market, monkeypatch):
    asked = []
    df = market["df"]
    monkeypatch.setattr(p9, "tail_bars", lambda asset, nrows, path=None: asked.append((asset, nrows)) or df)
    now = tp.close_ms(df, 4600) + 1
    got = p9._level_frame(BTC, None, now)
    assert asked == [(BTC, p9.LEVEL_TAIL_BARS + 8)] and got.index[-1] == df.index[4600]     # bar 4601 has not closed
    long = pd.concat([df] * 3)
    long.index = pd.date_range(df.index[0], periods=len(long), freq="15min", name="open_time")
    assert len(p9._level_frame(BTC, {BTC: long}, tp.close_ms(long, len(long) - 1))) == p9.LEVEL_TAIL_BARS
    assert p9._level_frame(ETH, {BTC: long}, now) is None


# ---------------------------------------------------------------- 5. the page block
def test_the_page_block_lists_the_levels_per_coin_and_says_it_is_a_notice(market, tmp_path):
    lv, df = market["lv"], market["df"]
    path = str(tmp_path / "s.json")
    run(market, path, SK - 2, lv["f"] + 2)
    rows = p9.rows_of(tp.state_of(path))
    blk = p9.page_block(rows)
    assert set(blk) == set(p9.BOOKS)
    for b in blk.values():
        assert set(b["levels"]) == {BTC} and len(b["levels"][BTC]) == 1
        r = b["levels"][BTC][0]
        assert r == {"L": market["L"], "low_utc": p9._utc(int(market["fx"]["open_ms"][lv["b"]])),
                     "made_utc": p9._utc(tp.close_ms(df, SK)), "zone_top": round((1.0 + p9.LEVEL_ZONE) * market["L"], 6),
                     "state": "touched", "live": True, "live_until_utc": p9._utc(tp.close_ms(df, SK) + 30 * 86400000),
                     "touch_utc": p9._utc(int(market["fx"]["open_ms"][lv["f"]])), "broken_utc": None, "new_low": None,
                     "as_of_utc": p9._utc(tp.close_ms(df, lv["f"] + 2))}
        assert "not a setup" in b["levels_note"] and "77 retests" in b["levels_note"] and "no trade" in b["levels_note"].lower()
        assert b["not_passed"] is True and "NOT passed" in b["title"]     # the book's own block is as it was
    json.dumps(blk, allow_nan=False)
    old = set(tp.p9.page_block([])["p9_rebound_a"]) - {"levels", "levels_note"}
    assert old == {"title", "hypothesis", "registered", "not_passed", "rule", "open", "recent", "totals", "by_asset",
                   "started_utc", "coins", "signals_not_taken_while_in_a_trade", "pass_rule", "note", "step_seconds"}


# ---------------------------------------------------------------- 6. the two notices, word for word
# BTC with the numbers of the data copy's last bar (24 Nov 2026 04:30 UTC: ATR(1h) 713.08, the close a week earlier
# 65,042.94) and a made-up touch of the 21 Nov level in that bar.
LEVEL = {"id": "BTCUSDT|1795243500000", "asset": BTC, "L": 55130.0, "zone_top": 55956.95, "arm_price": 57886.5,
         "state": "touched", "live": True, "low_open_ms": 1795241700000, "trigger_close_ms": 1795243500000,
         "live_until_ms": 1797835500000, "armed_open_ms": 1795243500000, "dead_open_ms": None,
         "touch_open_ms": 1795494600000, "broken_open_ms": None, "new_low": None}
BLOCK = {"as_of_open_ms": 1795494600000, "as_of_utc": "2026-11-24 04:45", "bars": 8928, "close": 55870.0,
         "atr_1h": 713.076174071917, "low_4h": 55801.5, "low_30d": 55130.0, "week_ago_close": 65042.94,
         "fresh_30d_low": False, "drop_enough": True, "all_three": False, "levels": [LEVEL]}
TOUCHED = datetime(2026, 11, 24, 4, 45, tzinfo=timezone.utc)        # the close of the first-touch bar
BROKE_MS = 1795494600000 + 5 * 900000                               # the 05:45 bar: a low under the level
BROKEN_LEVEL = dict(LEVEL, state="broken", broken_open_ms=BROKE_MS, new_low=54200.0)
BROKEN_BLOCK = dict(BLOCK, as_of_open_ms=BROKE_MS, as_of_utc="2026-11-24 06:00", close=54650.0, low_4h=54200.0,
                    low_30d=54200.0, fresh_30d_low=True, levels=[BROKEN_LEVEL])
BROKE = datetime(2026, 11, 24, 6, 0, tzinfo=timezone.utc)


def test_the_zone_notice_text():
    card = tn.zone_touch_card(LEVEL, BLOCK, TOUCHED + timedelta(minutes=1))
    assert card.split("\n") == [
        u"\U0001f4cd <b>Back at the capitulation low · BTC</b>",
        u"A 15m low reached the zone in the bar that closed at 04:45 UTC (Tue 24 Nov).",
        u"Low <b>55,130.00</b>, made Sat 21 Nov (the 06:15 UTC bar)",
        u"Zone 55,130.00 to <b>55,956.95</b> (the low to 1.5% above it)",
        u"Price now <b>55,870.00</b> (the 04:45 UTC close)",
        u"<b>A notice, NOT a setup.</b> No trade is opened here.",
        u"On history (77 retests, 2019 to 2025): in 88% price traded under the low within 4 days (median lowest point "
        u"6.6% below it).",
        u"A day after the first touch price was higher in 58% (median +1.9%).",
        u"The long needs a low under 55,130.00, then a 15m close 2 x ATR(1h) above that new low (ATR(1h) is 713.08 now: "
        u"1,426.15 above it).",
        u"That low must also be 10% under the close a week earlier: at or under 58,538.65 now.",
        u"A separate alert comes if the long fires.",
        u"<i>Buying the retest itself was tested (H116): too few trades to judge, a small loss on those.</i>"]
    assert "edge" not in card.lower() and "proven" not in card.lower() and "$" not in card


def test_the_break_notice_text():
    card = tn.zone_broken_card(BROKEN_LEVEL, BROKEN_BLOCK, BROKE + timedelta(minutes=1))
    assert card.split("\n") == [
        u"\U0001f53b <b>Capitulation low broken · BTC</b>",
        u"A 15m low went under <b>55,130.00</b> (the low of Sat 21 Nov) in the bar that closed at 06:00 UTC (Tue 24 Nov).",
        u"New low so far <b>54,200.00</b>",
        u"Price now <b>54,650.00</b> (the 06:00 UTC close)",
        u"<b>A notice, NOT a setup.</b> No trade is opened here.",
        u"The long (rule A) needs a 15m close at or above <b>55,626.15</b>: the 4-hour low 54,200.00 + 2 x ATR(1h) 713.08.",
        u"Its other two conditions must hold at that close too:",
        u"• a fresh 30-day low in the last 4 hours: true now",
        u"• that low 10% under the close a week earlier (65,042.94), so at or under 58,538.65: true now (-16.7%)",
        u"These numbers move with every bar. A separate alert comes if the long fires.",
        u"<i>The long is paper only, NOT passed. On history rule A was flat over 123 trades; rule B had 32 trades, too "
        u"few to judge.</i>"]
    assert "edge" not in card.lower() and "proven" not in card.lower() and "$" not in card


def test_the_notice_variants_late_old_readings_first_notice_and_conditions_not_met():
    late = tn.zone_touch_card(LEVEL, BLOCK, TOUCHED + timedelta(hours=2, minutes=10))
    lines = late.split("\n")
    assert lines[-2] == u"⚠️ Late: price reached the zone 2 h 10 min ago."
    assert lines[4] == u"Last price <b>55,870.00</b> (the 04:45 UTC close, Tue 24 Nov)"      # not "now" any more
    assert len(lines) == 13
    on_time = tn.zone_touch_card(LEVEL, BLOCK, TOUCHED + timedelta(minutes=29))
    assert "Late" not in on_time and "Price now" in on_time
    eth = tn.zone_touch_card(dict(LEVEL, asset=ETH, L=1538.0, low_open_ms=1795233600000),
                             dict(BLOCK, close=1559.5, atr_1h=22.893379958480008, week_ago_close=1820.0), TOUCHED)
    assert u"· ETH</b>" in eth and u"Low <b>1,538.00</b>, made Sat 21 Nov (the 04:00 UTC bar)" in eth
    assert u"Zone 1,538.00 to <b>1,561.07</b>" in eth and u"(ATR(1h) is 22.8934 now: 45.7868 above it)" in eth
    first = tn.zone_broken_card(BROKEN_LEVEL, BROKEN_BLOCK, BROKE + timedelta(minutes=1), first=True).split("\n")
    assert first[4] == (u"First notice for this low: price reached its zone (up to 55,956.95) in the bar that closed at "
                        u"04:45 UTC (Tue 24 Nov).") and len(first) == 12
    weak = dict(BROKEN_BLOCK, week_ago_close=59800.0, drop_enough=False, fresh_30d_low=False)
    card = tn.zone_broken_card(BROKEN_LEVEL, weak, BROKE + timedelta(minutes=50))
    assert u"• a fresh 30-day low in the last 4 hours: NOT true now" in card
    assert u"(59,800.00), so at or under 53,820.00: NOT true now (-9.4%)" in card
    assert u"⚠️ Late: the low broke 50 min ago." in card
    fired = tn.zone_broken_card(BROKEN_LEVEL, dict(BROKEN_BLOCK, all_three=True), BROKE)
    assert u"All three conditions of the long (rule A) held at the last close. If it fired, its own alert says so." in fired
    assert "needs a 15m close" not in fired


@pytest.mark.parametrize("lv, blk", [
    (None, BLOCK), (LEVEL, None), (dict(LEVEL, asset="XAUUSD"), BLOCK), (dict(LEVEL, L="x"), BLOCK),
    (dict(LEVEL, L=0.0), BLOCK), (dict(LEVEL, low_open_ms=None), BLOCK), (LEVEL, dict(BLOCK, atr_1h=None)),
    (LEVEL, dict(BLOCK, atr_1h=float("nan"))), (LEVEL, dict(BLOCK, close=None)), (LEVEL, dict(BLOCK, as_of_open_ms="?")),
    (LEVEL, dict(BLOCK, week_ago_close=None)), (dict(LEVEL, touch_open_ms=None), BLOCK)])
def test_a_level_that_cannot_be_read_gives_no_notice(lv, blk):
    assert tn.zone_touch_card(lv, blk, TOUCHED) is None
    broken = None if lv is None else dict(lv, broken_open_ms=BROKE_MS, new_low=54200.0)
    assert tn.zone_broken_card(broken, None if blk is None else dict(blk, low_4h=54200.0), BROKE) is None
    assert tn.zone_broken_card(dict(BROKEN_LEVEL, new_low=55130.0), BROKEN_BLOCK, BROKE) is None     # not under the level
    assert tn.zone_broken_card(dict(BROKEN_LEVEL, new_low=None), BROKEN_BLOCK, BROKE) is None
    assert tn.zone_broken_card(BROKEN_LEVEL, dict(BROKEN_BLOCK, low_4h=None), BROKE) is None


# ---------------------------------------------------------------- 7. delivery
def bot(monkeypatch, ok=True):
    sent, holder = tp._bot(monkeypatch, ok)
    monkeypatch.setattr(tn, "_ZONE_ERR", [None])
    return sent, holder


def write_state(path, levels=(), block=BLOCK, alerts=(), closed=(), eth=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    zone = {BTC: dict(block, levels=list(levels))}
    if eth is not None:
        zone[ETH] = eth
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"version": 1, "alerts": list(alerts), "closed": list(closed), "zone": zone}, fh)


@pytest.fixture()
def capit_file(tmp_path, monkeypatch):
    path = str(tmp_path / "data" / "capit_long_state.json")
    monkeypatch.setattr(tn, "CAPIT_STATE", path)
    return path


def test_each_notice_is_sent_once_per_level_also_across_a_restart(capit_file, monkeypatch):
    sent, _h = bot(monkeypatch)
    st, now = {"chat_id": 42}, TOUCHED + timedelta(minutes=1)
    write_state(capit_file, [dict(LEVEL, state="armed", touch_open_ms=None)])
    assert tn.zone_check(st, "k", 42, now - timedelta(minutes=16)) == [] and sent == []      # armed: nothing to say
    write_state(capit_file, [LEVEL])
    done = tn.zone_check(st, "k", 42, now)
    assert len(done) == 1 and sent == [(42, done[0])] and done[0] == tn.zone_touch_card(LEVEL, BLOCK, now)
    assert st["zone_alerted"] == {"z|" + LEVEL["id"]: now.timestamp()}
    assert tn.zone_check(st, "k", 42, now + timedelta(minutes=1)) == [] and len(sent) == 1
    st = json.loads(json.dumps(st))                                 # the bot restarts: its state comes back from its file
    write_state(capit_file, [LEVEL], dict(BLOCK, as_of_open_ms=BLOCK["as_of_open_ms"] + 900000, close=55990.0))
    assert tn.zone_check(st, "k", 42, now + timedelta(minutes=16)) == [] and len(sent) == 1   # still touched: no second one
    write_state(capit_file, [BROKEN_LEVEL], BROKEN_BLOCK)
    done = tn.zone_check(st, "k", 42, BROKE + timedelta(minutes=1))
    assert len(done) == 1 and "Capitulation low broken" in sent[1][1] and "First notice" not in sent[1][1]
    assert set(st["zone_alerted"]) == {"z|" + LEVEL["id"], "x|" + LEVEL["id"]}
    st = json.loads(json.dumps(st))
    lower = dict(BROKEN_LEVEL, new_low=53000.0)                     # it keeps falling: the level has had its two notices
    write_state(capit_file, [lower], dict(BROKEN_BLOCK, as_of_open_ms=BROKE_MS + 900000, close=53100.0, low_4h=53000.0))
    assert tn.zone_check(st, "k", 42, BROKE + timedelta(minutes=16)) == [] and len(sent) == 2
    other = dict(LEVEL, id="BTCUSDT|1795500000000", L=54000.0, touch_open_ms=BROKE_MS + 20 * 900000)
    write_state(capit_file, [lower, other], dict(BROKEN_BLOCK, as_of_open_ms=BROKE_MS + 20 * 900000, close=54500.0))
    done = tn.zone_check(st, "k", 42, BROKE + timedelta(hours=5, minutes=16))
    assert len(done) == 1 and u"Low <b>54,000.00</b>" in done[0]    # another level: its own notice
    assert len(sent) == 3 and all(chat == 42 for chat, _t in sent)


def test_a_level_first_seen_already_broken_gets_one_notice_not_two(capit_file, monkeypatch):
    sent, _h = bot(monkeypatch)
    st = {"chat_id": 42}
    write_state(capit_file, [BROKEN_LEVEL], BROKEN_BLOCK)
    done = tn.zone_check(st, "k", 42, BROKE + timedelta(minutes=1))
    assert len(done) == 1 and len(sent) == 1 and "First notice for this low" in done[0]
    assert set(st["zone_alerted"]) == {"z|" + LEVEL["id"], "x|" + LEVEL["id"]}
    assert tn.zone_check(st, "k", 42, BROKE + timedelta(minutes=2)) == [] and len(sent) == 1
    same_bar = dict(BROKEN_LEVEL, touch_open_ms=BROKE_MS)           # into the zone and under the low in one bar
    write_state(capit_file, [same_bar], BROKEN_BLOCK)
    done = tn.zone_check({"chat_id": 42}, "k", 42, BROKE + timedelta(minutes=1))
    assert len(done) == 1 and "in the bar that closed at 06:00 UTC (Tue 24 Nov)." in done[0].split("\n")[4]


def test_a_failed_send_is_retried_and_nothing_older_than_48_hours_is_sent(capit_file, monkeypatch):
    sent, holder = bot(monkeypatch, ok=False)
    write_state(capit_file, [LEVEL])
    st = {"chat_id": 42}
    assert tn.zone_check(st, "k", 42, TOUCHED + timedelta(minutes=1)) == [] and not st.get("zone_alerted")
    holder["ok"] = True
    done = tn.zone_check(st, "k", 42, TOUCHED + timedelta(minutes=2))
    assert len(done) == 1 and len(sent) == 1 and "z|" + LEVEL["id"] in st["zone_alerted"]
    assert len(tn.zone_check({}, "k", 42, TOUCHED + timedelta(hours=48))) == 1               # at 48 hours: still sent
    assert tn.zone_check({}, "k", 42, TOUCHED + timedelta(hours=48, seconds=1)) == [] and len(sent) == 2
    write_state(capit_file, [BROKEN_LEVEL], BROKEN_BLOCK)
    assert tn.zone_check({}, "k", 42, BROKE + timedelta(hours=48, seconds=1)) == []          # an old break: nothing,
    assert len(sent) == 2                                                                     # and not its old touch either
    assert len(tn.zone_check({}, "k", 42, TOUCHED + timedelta(hours=48, seconds=1))) == 1    # a break inside 48 hours is sent
    holder["ok"] = False                                            # the break fails after the touch went out
    st = {"zone_alerted": {"z|" + LEVEL["id"]: TOUCHED.timestamp()}}
    assert tn.zone_check(st, "k", 42, BROKE + timedelta(minutes=1)) == [] and set(st["zone_alerted"]) == {"z|" + LEVEL["id"]}
    holder["ok"] = True
    assert len(tn.zone_check(st, "k", 42, BROKE + timedelta(minutes=2))) == 1 and "First notice" not in sent[-1][1]


def test_the_memory_is_capped_and_a_garbled_memory_or_file_is_no_crash(capit_file, monkeypatch, capsys):
    sent, _h = bot(monkeypatch)
    write_state(capit_file, [LEVEL])
    now = TOUCHED + timedelta(minutes=1)
    old = dict(("z|X|%d" % i, now.timestamp() - 40 * 86400) for i in range(5))
    many = dict(("z|Y|%d" % i, now.timestamp() - i) for i in range(1, 500))
    st = {"zone_alerted": dict(old, **many)}
    tn.zone_check(st, "k", 42, now)
    assert len(st["zone_alerted"]) == tn.ZONE_MEMORY_MAX and "z|" + LEVEL["id"] in st["zone_alerted"]
    assert not any(k.startswith("z|X|") for k in st["zone_alerted"])
    st = {"zone_alerted": "garbled"}
    assert len(tn.zone_check(st, "k", 42, now)) == 1 and isinstance(st["zone_alerted"], dict)
    n = len(sent)
    for content in (None, b"", b"{oops", b"[1]", b'{"zone": 7}', b'{"zone": {"BTCUSDT": 5, "ETHUSDT": {"levels": 3}}}',
                    b'{"zone": {"BTCUSDT": {"levels": [1, null, {"id": 5}, {"id": "a", "asset": "BTCUSDT"}, '
                    b'{"id": "b", "asset": "ETHUSDT", "touch_open_ms": 1}, {"id": "c", "asset": "BTCUSDT", '
                    b'"touch_open_ms": "x"}]}, "XAUUSD": {"levels": [{"id": "d", "asset": "XAUUSD", "touch_open_ms": 1}]}}}'):
        if content is None:
            os.remove(capit_file)
        else:
            with open(capit_file, "wb") as fh:
                fh.write(content)
        assert tn.zone_check({"chat_id": 42}, "k", 42, now) == []
    assert len(sent) == n and "failed" not in capsys.readouterr().out
    write_state(capit_file, [LEVEL])
    monkeypatch.setattr(tn, "CAPIT_READ_MAX", 50)                   # a file too large is not read
    assert tn.zone_check({}, "k", 42, now) == [] and len(sent) == n


def test_the_check_sends_to_the_locked_chat_only_and_a_failure_there_stops_nothing(capit_file, monkeypatch, capsys):
    sent, _h = bot(monkeypatch)
    tp._quiet_check(monkeypatch)
    eth_level = dict(LEVEL, id="ETHUSDT|1795243500000", asset=ETH, L=1538.0, low_open_ms=1795233600000)
    eth = dict(BLOCK, close=1559.5, atr_1h=22.893379958480008, week_ago_close=1820.0, levels=[eth_level])
    write_state(capit_file, [LEVEL], alerts=[tp.EVENT], eth=eth)    # a trigger of the long two days old, and two touches
    now = TOUCHED + timedelta(minutes=1)
    day = now.strftime("%Y-%m-%d")
    st, ev = tn.check({"chat_id": 4242, "summary_day": day}, "k", now=now)
    assert [chat for chat, _t in sent] == [4242, 4242] and ["BTC" in t for _c, t in sent] == [True, False]
    assert sum("Back at the capitulation low" in e for e in ev) == 2 and "capit_alerted" in st
    st, ev = tn.check(st, "k", now=now + timedelta(minutes=1))
    assert len(sent) == 2 and not any("capitulation low" in e for e in ev)
    assert tn.SIGNALS_CHANNEL is None and tn.SIGNALS_PREVIEW is True          # there is no subscriber channel at all
    src = inspect.getsource(tn.zone_check)
    assert src.count("_send(") == 1 and "_send(tok, chat, card)" in src       # one way out: the chat the check hands in,
    assert "_signal_send" not in src and "_early_send" not in src and "SIGNALS" not in src   # never the signals' sender
    assert inspect.getsource(tn.check).count('zone_check(st, tok, st["chat_id"], now)') == 1
    st0, ev0 = tn.check({"summary_day": day}, "k", now=now)         # no chat locked in yet: nothing leaves
    assert len(sent) == 2 and "zone_alerted" not in st0
    monkeypatch.setattr(tn, "_zone_levels", lambda doc: 1 / 0)
    write_state(capit_file, [BROKEN_LEVEL], BROKEN_BLOCK, alerts=[dict(tp.EVENT, id="BTCUSDT|9", decided_ms=BROKE_MS)])
    st, ev = tn.check(st, "k", now=BROKE + timedelta(minutes=1))    # the notice code breaks: the check goes on,
    assert st["checked_utc"] and "capitulation-low notices failed (ZeroDivisionError)" in capsys.readouterr().out
    assert len(sent) == 3 and "Capitulation long" in sent[-1][1]    # ... and the long's own card still went out
    tn.check(st, "k", now=BROKE + timedelta(minutes=2))
    assert "failed" not in capsys.readouterr().out                  # printed once


def test_the_capitulation_long_cards_are_what_they_were(capit_file, monkeypatch):
    sent, _h = bot(monkeypatch)
    now = tp.DEC + timedelta(minutes=2)
    plain = str(os.path.join(os.path.dirname(capit_file), "plain.json"))
    tp._write_state(plain, [tp.EVENT], tp.CLOSED)                   # the book's state as it was before there were levels
    monkeypatch.setattr(tn, "CAPIT_STATE", plain)
    a = {"chat_id": 42}
    before = tn.capit_check(a, "k", 42, now) + tn.capit_check(a, "k", 42, datetime(2026, 11, 23, 6, 47, tzinfo=timezone.utc))
    assert tn.zone_check(a, "k", 42, now) == [] and a.get("zone_alerted") == {}      # no "zone" in the file: no notice
    monkeypatch.setattr(tn, "CAPIT_STATE", capit_file)
    write_state(capit_file, [BROKEN_LEVEL], BROKEN_BLOCK, alerts=[tp.EVENT], closed=tp.CLOSED)
    b = {"chat_id": 42}
    after = tn.capit_check(b, "k", 42, now) + tn.capit_check(b, "k", 42, datetime(2026, 11, 23, 6, 47, tzinfo=timezone.utc))
    assert before == after and len(before) == 2 and a["capit_alerted"] == b["capit_alerted"]
    assert before[0] == tn.capit_trigger_card(tp.EVENT, now) and before[1] == tn.capit_close_card(BTC, tp.CLOSED, tp.CLOSED)
    assert "zone_alerted" not in b
    tn.zone_check(b, "k", 42, BROKE + timedelta(minutes=1))
    assert set(b["zone_alerted"]) == {"z|" + LEVEL["id"], "x|" + LEVEL["id"]} and a["capit_alerted"] == b["capit_alerted"]


def test_from_the_books_step_to_the_two_notices(market, capit_file, monkeypatch):
    """End to end: the state file the book writes is the file the bot reads; one notice at the first touch, one at
    the break, none before, between or after, with the bot restarting after every check."""
    sent, _h = bot(monkeypatch)
    lv, df = market["lv"], market["df"]
    got = run(market, capit_file, SK - 2, len(df) - 1, bot={"chat_id": 42})
    assert [i for i, _c in got] == [lv["f"], lv["s"]] and len(sent) == 2
    touch, broke = got[0][1], got[1][1]
    L = market["L"]
    assert touch.startswith(u"\U0001f4cd <b>Back at the capitulation low · BTC</b>") and "Late" not in touch
    assert u"Zone %s to <b>%s</b>" % (tn._adv_px(L), tn._adv_px((1.0 + p9.LEVEL_ZONE) * L)) in touch
    assert u"Price now <b>%s</b>" % tn._adv_px(float(df["close"].iloc[lv["f"]])) in touch
    assert broke.startswith(u"\U0001f53b <b>Capitulation low broken · BTC</b>") and "First notice" not in broke
    fx = p9.features(df.iloc[:lv["s"] + 1], None)
    need = float(fx["low16"][-1] + 2.0 * fx["atr1h"][-1])
    assert u"needs a 15m close at or above <b>%s</b>" % tn._adv_px(need) in broke
    assert u"New low so far <b>%s</b>" % tn._adv_px(float(df["low"].iloc[lv["s"]])) in broke
    assert u"a fresh 30-day low in the last 4 hours: true now" in broke


def test_the_bot_still_never_imports_the_book_and_no_money_file_knows_the_levels():
    with open(tn.__file__, encoding="utf-8") as fh:
        src = fh.read()
    assert "import playbook9" not in src and "from .playbook9" not in src and "playbook9 import" not in src
    with open(os.path.join(ROOT, "tools", "money_files.txt"), encoding="utf-8") as fh:
        money = [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
    assert "engine15/playbook9.py" not in money and "engine15/telegram_notify.py" not in money
    for rel in money:
        if rel.endswith(".py"):
            with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
                body = fh.read()
            assert "levels_of" not in body and "zone_check" not in body and "zone_alerted" not in body, rel
            assert "LEVEL_TAIL" not in body and "capit_long" not in body, rel
