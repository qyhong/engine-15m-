# -*- coding: utf-8 -*-
"""The trail mode of setups.json (engine15/setups.py; docs/TRAIL_SWITCH_PLAN.md sections 1 and 3) and the book behind it,
b_trail_setups (shadows.CHALLENGERS: the trailing stop with the Setups book's early entry).

    py -3 -m pytest tests/test_setups_trail.py -q

The switch (setups_voice.TRAIL_MARKETS) is OFF in the shipped code and stays off here: every test hands build() a voice
state of its own. Nothing real runs: made-up pages, planted bars, files in pytest's tmp folders, no network.
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
import pytest  # noqa: E402

import test_setups as ts  # noqa: E402
from engine15 import book_alloc, learn_book, policy, setups, setups_voice, shadows  # noqa: E402
from engine15 import vault_feed as vf  # noqa: E402
from engine15.config import CFG  # noqa: E402
from test_shadows import LONG, SHORT, aux_for, bars, go, random_inputs, run_random  # noqa: E402

BOOK = "b_trail_setups"
RULE = shadows.CHALLENGERS[BOOK]["rule"]
BAR = CFG["bar_ms"]
FROM = "2026-11-17T02:00:00Z"                                       # the changeover of the made-up trail markets
TRAIL_KEYS = ["exit_rule", "trail_active", "exit_rule_from_utc", "trail_from"]


@pytest.fixture(autouse=True)
def _alone(monkeypatch, tmp_path):
    """No web folder, no real S1 record, bar file, trade file or voice state unless a test makes one."""
    monkeypatch.delenv(setups.WEB_ENV, raising=False)
    monkeypatch.setattr(setups, "S1_DIR", str(tmp_path / "no_s1_here"))
    monkeypatch.setattr(setups, "BARS_DIR", str(tmp_path / "no_bars_here"))
    monkeypatch.setattr(setups, "TRADES_DIR", str(tmp_path / "no_trades_here"))
    monkeypatch.setattr(setups_voice, "STATE_PATH", str(tmp_path / "no_state_here" / "setups_voice_state.json"))


def btc():
    return shadows.asset_cfg("BTCUSDT", dict(CFG))


# ------------------------------------------------------------------ the book: the registration
def test_the_book_is_registered_after_b_trail_and_nowhere_it_should_not_be():
    names = list(shadows.CHALLENGERS)
    assert names[names.index("b_trail") + 1] == BOOK                 # right after the yardstick it copies
    spec = shadows.CHALLENGERS[BOOK]
    assert spec["rule"] == {"trail": True, "early": True} and spec["cfg"] == {}
    assert "trailing stop" in spec["title"] and "BTC and ETH" in spec["title"]
    assert shadows.CHALLENGERS["b_trail"]["rule"] == {"trail": True}                         # the yardstick: untouched
    assert shadows.CHALLENGERS["b_targets"]["rule"] == {"targets": True, "early": True}      # the vault's book: untouched
    assert setups_voice.BOOKS == {"targets": "b_targets", "trail": BOOK}
    assert (setups.BOOK, setups.TRAIL_BOOK, setups.TRAIL) == ("b_targets", BOOK, "trail")
    assert setups.START_EQUITY == shadows.START_EQUITY == 10000.0
    # registered research sets are not widened by a new book (H109, H110)
    assert BOOK not in learn_book.ARMS and ("shadow", BOOK) not in book_alloc.BOOKS
    assert BOOK not in shadows.FOLLOWERS and BOOK not in shadows.MINDS


# ------------------------------------------------------------------ the book: trail and early entry together
def planted():
    """Bar 1 decides a long at its close (100.4) although its high ran far above; bar 2 opens elsewhere (100.9).
    Entry stop = 100.4 - 2 x 2.0 = 96.4 (R = 4). Bar 5 reaches 1R; from then the stop trails 2 x ATR(15m) = 2 behind
    the close, or the swing low 101 when that is tighter: 102 after bar 5, 103 after bar 6, still 103 after bar 7 (its
    close fell: never looser), and bar 8 trades through 103."""
    px = bars(20)
    px["close"][1], px["high"][1] = 100.4, 110.0
    px["open"][2], px["high"][2] = 100.9, 101.4
    px["high"][5], px["close"][5] = 105.0, 104.0
    px["open"][6], px["close"][6], px["high"][6], px["low"][6] = 104.0, 105.0, 105.5, 103.5
    px["open"][7], px["close"][7], px["high"][7], px["low"][7] = 105.0, 104.0, 105.5, 103.5
    px["open"][8], px["close"][8], px["high"][8], px["low"][8] = 104.0, 102.5, 104.5, 102.0
    aux = aux_for(20)
    aux["sw_lo"][:] = 101.0
    return px, aux


def walk(px, aux, cfg, rule=RULE, odds=LONG, hi=12):
    """One bar a call, the state kept as JSON between calls (as the live engine does). -> [(state, closed trades)]"""
    out, st = [], None
    for i in range(1, hi):
        b = go(px, odds, rule, aux=aux, lo=i, hi=i + 1, cfg=cfg, state=st)
        st = json.loads(json.dumps(b["state"]))
        out.append((st, [t for t in b["trades"].itertuples() if t.why_out != "OPEN"]))
    return out


def test_an_early_entry_is_booked_at_the_deciding_close_and_then_trails():
    px, aux = planted()
    steps = walk(px, aux, btc())
    st1 = steps[0][0]                                                 # after bar 1, the bar whose close decided
    assert st1["pos"] == 1 and st1["pending"] is None and st1["why_in"] == policy.ENTER
    assert st1["entry"] == px["close"][1] == 100.4 != px["open"][2]   # the deciding close, not the next open
    assert st1["t_in_ms"] == 1 * BAR + BAR                            # opened AT that close (= the next bar's open time)
    assert st1["stop"] == st1["stop0"] == 96.4
    # block 2c ran for bar 1 before the entry was booked: bar 1's own high (110, far past 1R) arms nothing
    assert st1["trail_on"] is False
    v = shadows.asset_view(dict(st1))
    assert v["status"] == "LONG" and v["entry"] == 100.4 and v["stop"] == 96.4 and v["unrealized_usd"] == 0.0
    assert "trailing" not in v and "target_1" not in v and "held_share" not in v     # no targets in this book
    stops = [s["stop"] for s, _c in steps[:7]]                        # after bars 1 .. 7
    assert stops == [96.4, 96.4, 96.4, 96.4, 102.0, 103.0, 103.0]
    assert all(b >= a for a, b in zip(stops, stops[1:]))              # a long's stop only ever rises
    assert [s["trail_on"] for s, _c in steps[:7]] == [False] * 4 + [True] * 3        # armed by bar 5's high (1R)
    armed = shadows.asset_view(dict(steps[4][0]))
    assert armed["trailing"] is True and armed["stop"] == 102.0 and armed["entry"] == 100.4
    assert not any(c for _s, c in steps[:7])
    (t,) = steps[7][1]                                                # bar 8: the trailing stop trades
    assert (t.why_in, t.why_out, t.p_in, t.p_out) == (policy.ENTER, "TRAIL", 100.4, 103.0)
    assert t.t_in_ms == 2 * BAR and t.t_out_ms == 8 * BAR and t.stop0 == 96.4
    assert t.target_1 is None and t.target_2 is None                  # the trade file's target columns stay empty
    # one call over all the bars books the same trade
    whole = go(px, LONG, RULE, aux=aux, hi=12, cfg=btc())["trades"].iloc[0]
    assert (whole.why_out, whole.p_in, whole.p_out) == ("TRAIL", 100.4, 103.0)
    assert (whole.t_in_ms, whole.t_out_ms) == (2 * BAR, 8 * BAR)


def test_the_same_bars_without_the_early_entry_fill_one_bar_later_at_the_open():
    px, aux = planted()
    for rule, cfg in ((RULE, shadows.asset_cfg("USDJPY", dict(CFG))),         # the rule asks, the market is not named
                      ({"trail": True}, btc())):                             # the market is named, b_trail does not ask
        steps = walk(px, aux, cfg, rule=rule)
        st1, st2 = steps[0][0], steps[1][0]
        assert st1["pos"] == 0 and st1["pending"][:2] == [policy.ENTER, 1]
        assert st2["pos"] == 1 and st2["entry"] == px["open"][2] == 100.9 and st2["t_in_ms"] == 2 * BAR


def test_the_first_stop_trades_before_the_trail_arms():
    px, aux = planted()
    px["open"][3], px["low"][3], px["close"][3] = 100.0, 96.0, 96.2   # bar 3 trades through 96.4 before any 1R
    steps = walk(px, aux, btc(), hi=5)
    (t,) = steps[2][1]
    assert (t.why_out, t.p_in, t.p_out, t.t_in_ms) == ("STOP", 100.4, 96.4, 2 * BAR)


def test_a_short_mirrors_it():
    px = bars(20)
    px["close"][1] = 99.6                                             # entry 99.6, stop 103.6
    px["low"][5], px["close"][5] = 95.0, 96.0                         # 1R: stop = 96 + 2 = 98
    px["open"][6], px["close"][6], px["high"][6], px["low"][6] = 96.0, 95.0, 96.5, 94.5      # 97
    px["open"][7], px["close"][7], px["high"][7], px["low"][7] = 95.0, 96.0, 96.5, 94.5      # 98 would be looser: 97
    px["open"][8], px["high"][8], px["low"][8], px["close"][8] = 96.0, 97.5, 95.5, 97.2
    steps = walk(px, aux_for(20), btc(), odds=SHORT)
    stops = [s["stop"] for s, _c in steps[:7]]
    assert stops == [103.6, 103.6, 103.6, 103.6, 98.0, 97.0, 97.0] and all(b <= a for a, b in zip(stops, stops[1:]))
    (t,) = steps[7][1]
    assert (t.side, t.why_out, t.p_in, t.p_out, t.t_in_ms) == (-1, "TRAIL", 99.6, 97.0, 2 * BAR)


@pytest.mark.parametrize("seed", [3, 11])
def test_on_random_bars_the_stop_only_tightens_and_every_stop_exit_is_trail_or_stop(seed):
    inp = random_inputs(seed=seed)
    px = inp[0]
    n = len(px["close"])
    st, rows, early = None, [], 0
    for i in range(1, n):
        prev = st
        b = run_random(RULE, inp, lo=i, hi=i + 1, state=st, cfg=btc())
        st = json.loads(json.dumps(b["state"]))
        rows += [t for t in b["trades"].itertuples() if t.why_out != "OPEN"]
        same = prev and prev["pos"] and st["pos"] == prev["pos"] and st["t_in_ms"] == prev["t_in_ms"]
        if same:                                                      # the same setup one bar on
            assert st["pos"] * (st["stop"] - prev["stop"]) >= 0, i    # never looser
            assert st["trail_on"] or st["stop"] == st["stop0"]        # and it moves only once the trail has armed
            assert st["trail_on"] >= prev["trail_on"]                 # armed stays armed
        if st["pos"] and st["t_in_ms"] == i * BAR + BAR:              # booked at this close: an early entry
            early += 1
            assert st["entry"] == px["close"][i] and st["why_in"] in (policy.ENTER, policy.FORCED)
            assert st["stop"] == st["stop0"] and st["trail_on"] is False
    words = set(t.why_out for t in rows)
    assert early > 20 and len(rows) > 40
    assert words <= {"TRAIL", "STOP", policy.FLIP, policy.STEP_ASIDE} and {"TRAIL", "STOP"} <= words
    assert all(t.target_1 is None or t.target_1 != t.target_1 for t in rows)             # never a target
    # where every bar opens at the close before it, the early book IS b_trail (the entry price is the same number)
    a, b = run_random(RULE, inp, cfg=btc())["trades"], run_random({"trail": True}, inp, cfg=btc())["trades"]
    assert len(a) == len(b) == len(rows)
    for c in ("side", "p_in", "p_out", "why_in", "why_out", "t_in_ms", "t_out_ms", "pnl_usd"):
        x, y = a[c].values, b[c].values
        assert (x == y).all() if x.dtype.kind in "OU" else np.allclose(x.astype(float), y.astype(float)), c


# ------------------------------------------------------------------ made-up pages with both books
def tview(status="FLAT", **kw):
    return ts.view(status, **kw)


def trail_views():
    """The trail book on the page: BTC long and armed (its stop is past the entry), ETH short and not armed, the rest
    flat or holding a setup of their own."""
    return {
        "BTCUSDT": tview("LONG", equity=10270.25, realized_usd=110.25, trades=9, wins=6, entry=100200.0, stop=100650.0,
                         opened_utc="2026-11-17 02:45", opened_by="ENTER", unrealized_usd=160.0, trailing=True),
        "ETHUSDT": tview("SHORT", equity=9990.0, realized_usd=-30.0, trades=1, wins=0, entry=1900.0, stop=1960.0,
                         opened_utc="2026-11-17 03:00", opened_by="FORCED", unrealized_usd=20.0),
        "XAUUSD": tview("FLAT", equity=10010.0, realized_usd=10.0, trades=1, wins=1),
        "XAGUSD": tview("FLAT"),
        "USDJPY": tview("LONG", entry=160.2, stop=159.9, opened_utc="2026-11-17 03:15", unrealized_usd=5.0),
        "SPX": tview("FLAT"),
        "WTI": tview("FLAT"),
        "BRENT": tview("SHORT", entry=94.0, stop=93.8, opened_utc="2026-11-17 02:15", unrealized_usd=40.0, trailing=True),
    }


def make_page(trail=True):
    page = ts.make_page()
    if trail:
        page["shadows"]["books"][BOOK] = {"title": shadows.CHALLENGERS[BOOK]["title"], "assets": trail_views()}
    return page


def voice(*syms, **kw):
    """A voice state with these markets on the trail voice since FROM (or from_utc=...)."""
    return {"schema": 1, "markets": dict((s, {"rule": "trail", "from_utc": kw.get("from_utc", FROM), "pending": False,
                                               "wait": None}) for s in syms)}


def old_build(page, s1=None, now=None, bars=None, trades=None, prev=None):
    """setups.build as it was before the trail mode, put together again from the same parts: the yardstick of the
    switch-off tests (and the reason those parts must not change for a market on the default voice)."""
    views = setups.book_views(page)
    assets = page["assets"]
    order = setups._order(page, assets)
    now_ms = setups._ms(now) if now is not None else setups._ms(page.get("generated_utc"))
    waiting = setups._waiting((s1 or {}).get("state") if isinstance(s1, dict) else None, now_ms)
    bars, old = bars if isinstance(bars, dict) else {}, setups._prev_markets(prev)
    return setups._clean({
        "generated_utc": page.get("generated_utc"), "version": page.get("version"), "schema": setups.SCHEMA,
        "note": setups.NOTE, "book": setups._book(page, [views.get(a) for a in order]),
        "followable": setups._followable(s1), "learning": setups._learning(page),
        "markets": [setups._market(page, a, assets.get(a), views.get(a), waiting, now_ms, bars.get(a), old.get(a))
                    for a in order],
        "closed_setups": setups._closed_setups(trades)})


def text(doc):
    return json.dumps(doc, allow_nan=False)                          # key order included: the file's own bytes


# ------------------------------------------------------------------ the switch off: the file as it always was
def test_with_the_switch_off_the_document_is_what_it_always_was(tmp_path):
    assert setups_voice.TRAIL_MARKETS == ()
    d = tmp_path / "trades"
    ts.write_trades(d, "BTCUSDT", [ts.trow("2026-11-16 01:00", "2026-11-16 03:00", 1, 100000.0, 101000.0, "T1+T2", 1.0)])
    ts.write_trades(d, "BTCUSDT", [ts.trow("2026-11-17 02:15", "2026-11-17 03:00", 1, 100000.0, 100500.0, "TRAIL", 0.5)],
                    book=BOOK)                                        # the trail book's file is there and is not read
    trades = setups.read_trades(str(d))
    s1 = {"scoreboard": None, "state": ts._state()}
    for page in (ts.make_page(), make_page()):                        # without and with the trail book on the page
        want = old_build(page, s1=s1, trades=trades)
        inert = {"schema": 1, "markets": {"BTCUSDT": {"rule": "targets", "from_utc": None, "pending": False, "wait": None},
                                          "ETHUSDT": "not an entry", "XAUUSD": {"rule": "something else"}}}
        for v in (None, {}, {"schema": 1, "markets": {}}, {"markets": None}, "not a state", ["x"], inert):
            got = setups.build(page, s1=s1, trades=trades, voice=v, trail_trades=setups.read_trades(str(d), BOOK))
            assert got == want and text(got) == text(want), v
        assert text(setups.build(page, s1=s1, trades=trades)) == text(want)
        assert all(list(m) == ts.MARKET for m in want["markets"])     # no new key anywhere
        assert "exit_rule" not in text(want) and "trail" not in text(want).lower()
    assert text(setups.build(make_page())) == text(setups.build(ts.make_page()))     # the trail book changes nothing


def test_write_with_the_switch_off_leaves_no_state_file_and_the_same_bytes(tmp_path):
    data, live = tmp_path / "data", tmp_path / "live"
    data.mkdir()
    for k in range(3):                                                # several steps: nothing accumulates
        info = setups.write(make_page(), out_dir=str(live), data_dir=str(data))
        with open(info["path"], encoding="utf-8") as fh:
            assert fh.read() == setups._text(text(old_build(make_page(), prev=None if k == 0 else {})))
        assert os.listdir(str(data)) == []                            # no voice state, and no temp file
    assert sorted(os.listdir(str(live))) == ["landing.json", "setup_events.json", "setups.json"]


# ------------------------------------------------------------------ a market on the trail voice, field by field
def test_a_trail_market_armed():
    doc = setups.build(make_page(), voice=voice("BTCUSDT"))
    m = ts.by_symbol(doc)["BTCUSDT"]
    assert list(m) == ts.MARKET + TRAIL_KEYS                          # keys added only, at the end
    assert m == {"symbol": "BTCUSDT", "short": "BTC", "group": "crypto", "side": "LONG",
                 "entry": 100200.0, "stop": 100650.0,                 # the stop as the book holds it: past the entry
                 "target_1": None, "target_2": None, "t1_taken": False, "held_share": None,
                 "opened_utc": "2026-11-17T02:45:00Z", "price": 101000.0, "price_bar_utc": "2026-11-17T03:15:00Z",
                 "unrealized_usd": 160.0, "unrealized_pct": 0.8, "market_open": True, "next_open_utc": None,
                 "edge_with_position_pts": 2.5, "hit_24h_30d_pct": 53.9, "rr_now_t1": None, "rr_now_t2": None,
                 "stop_dist_now_pct": 0.35, "entry_window_open": False, "entry_valid_until_utc": None,
                 "closed": 0, "wins": 0, "realized_usd": 0.0,        # no trade file: what the page showed is nothing yet
                 "closes": None, "closes_step_min": 15, "closes_end_utc": None,
                 "exit_rule": "trail", "trail_active": True, "exit_rule_from_utc": FROM,
                 "trail_from": None}                                  # armed: there is no arming price any more
    others = [x for x in doc["markets"] if x["symbol"] != "BTCUSDT"]
    assert others == [x for x in setups.build(ts.make_page())["markets"] if x["symbol"] != "BTCUSDT"]    # as today
    assert all(list(x) == ts.MARKET for x in others)                  # a targets market carries no new key
    assert vf.is_trail(m) and not any(vf.is_trail(x) for x in others)
    body, why = vf.build_trail_book(m, m["price_bar_utc"], force=True)       # the feed's own checks take this entry
    assert why is None and float(body["book"]["stop"]) == 100650.0 and body["book"]["trail_active"] is True


def test_a_trail_market_not_armed_and_its_entry_window():
    s1 = {"scoreboard": None, "state": ts._state(opened="2026-11-17 03:00", who="ETHUSDT")}
    m = ts.by_symbol(setups.build(make_page(), s1=s1, voice=voice("ETHUSDT")))["ETHUSDT"]
    assert list(m) == ts.MARKET + TRAIL_KEYS
    assert (m["side"], m["entry"], m["stop"], m["opened_utc"]) == ("SHORT", 1900.0, 1960.0, "2026-11-17T03:00:00Z")
    assert (m["exit_rule"], m["trail_active"], m["exit_rule_from_utc"]) == ("trail", False, FROM)
    assert m["trail_from"] == 1840.0                                  # a short: the entry less the stop's distance (1R)
    assert (m["target_1"], m["target_2"], m["t1_taken"], m["held_share"], m["rr_now_t1"], m["rr_now_t2"]) == \
        (None, None, False, None, None, None)
    assert m["unrealized_usd"] == 20.0 and m["unrealized_pct"] == 2.63       # 100 x (1900 - 1850) / 1900
    assert m["edge_with_position_pts"] == 4.5 and m["stop_dist_now_pct"] == 5.95
    assert (m["entry_window_open"], m["entry_valid_until_utc"]) == (True, "2026-11-17T04:15:00Z")   # the S1 waiting map
    body, why = vf.build_trail_book(m, m["price_bar_utc"], force=True)
    assert why is None and body["book"]["trail_active"] is False
    # the window is the trail setup's own: a signal of the targets book's setup (another opening) opens nothing
    other = {"scoreboard": None, "state": ts._state(opened="2026-11-16 09:15", who="ETHUSDT")}
    m = ts.by_symbol(setups.build(make_page(), s1=other, voice=voice("ETHUSDT")))["ETHUSDT"]
    assert (m["entry_window_open"], m["entry_valid_until_utc"]) == (False, None)


def test_trail_active_is_only_the_views_own_true_and_targets_are_never_read_from_a_trail_view():
    page = make_page()
    v = page["shadows"]["books"][BOOK]["assets"]
    v["BTCUSDT"].update(trailing="yes", target_1=103000.0, target_2=105000.0, t1_taken=True, held_share=0.5)
    m = ts.by_symbol(setups.build(page, voice=voice("BTCUSDT")))["BTCUSDT"]
    assert m["trail_active"] is False                                 # exactly True, nothing merely truthy
    assert (m["target_1"], m["target_2"], m["t1_taken"], m["held_share"], m["rr_now_t1"], m["rr_now_t2"]) == \
        (None, None, False, None, None, None)
    assert m["stop"] == 100650.0                                      # the book's stop, never "the entry after Target 1"
    v["BTCUSDT"].update(trailing=True, stop=101500.0)                 # a stop beyond the price: no distance is made up
    m = ts.by_symbol(setups.build(page, voice=voice("BTCUSDT")))["BTCUSDT"]
    assert m["trail_active"] is True and m["stop"] == 101500.0 and m["stop_dist_now_pct"] is None
    assert vf.build_trail_book(m, m["price_bar_utc"], force=True)[0] is None     # and the feed refuses such a book


def test_a_flat_trail_market_keeps_the_three_keys():
    doc = setups.build(make_page(), voice=voice("XAUUSD", "BTCUSDT", from_utc="2026-11-17T03:00:00Z"))
    by = ts.by_symbol(doc)
    for sym in ("XAUUSD",                                             # the trail book is flat
                "BTCUSDT"):                                           # it holds a setup opened BEFORE the changeover
        m = by[sym]
        assert list(m) == ts.MARKET + TRAIL_KEYS and m["side"] == "FLAT"
        for k in ts.POSITION + ["held_share"]:
            assert m[k] is None, (sym, k)
        assert (m["t1_taken"], m["entry_window_open"]) == (False, False)
        assert (m["exit_rule"], m["trail_active"], m["exit_rule_from_utc"]) == ("trail", False, "2026-11-17T03:00:00Z")
        assert m["trail_from"] is None                                # FLAT: nothing to arm
        assert m["price"] is not None and m["price_bar_utc"] is not None
    assert by["BTCUSDT"]["price"] == 101000.0 and "100200" not in text(doc) and "100650" not in text(doc)   # no level leaks
    # setups_voice.recover rebuilds the state from exactly these keys
    assert setups_voice.recover(doc) == {"schema": 1, "markets": {
        "BTCUSDT": {"rule": "trail", "from_utc": "2026-11-17T03:00:00Z", "pending": False, "wait": None},
        "XAUUSD": {"rule": "trail", "from_utc": "2026-11-17T03:00:00Z", "pending": False, "wait": None}}}
    assert setups.build(make_page(), voice=setups_voice.recover(doc)) == doc


def test_a_trail_market_without_the_trail_book_on_the_page_is_an_error_not_a_flat():
    with pytest.raises(ValueError):
        setups.build(make_page(trail=False), voice=voice("BTCUSDT"))
    page = make_page()
    page["shadows"]["books"][BOOK]["assets"] = None
    with pytest.raises(ValueError):
        setups.build(page, voice=voice("BTCUSDT"))
    del page["shadows"]["books"][BOOK]["assets"]
    page["shadows"]["books"][BOOK]["assets"] = {"ETHUSDT": tview()}   # the book is there, this one market is not: FLAT,
    m = ts.by_symbol(setups.build(page, voice=voice("BTCUSDT")))["BTCUSDT"]      # as a missing b_targets view is today
    assert m["side"] == "FLAT" and m["exit_rule"] == "trail"


# ------------------------------------------------------------------ a market that is changing over, or changed back
def test_a_market_waiting_for_the_changeover_shows_only_the_remembered_setup():
    today = ts.by_symbol(setups.build(ts.make_page()))
    wait = {"schema": 1, "markets": {"BTCUSDT": {"rule": "targets", "from_utc": None, "pending": True,
                                                 "wait": "2026-11-17 02:30"}}}
    doc = setups.build(make_page(), voice=wait)
    assert doc == setups.build(ts.make_page())                        # the remembered setup: today's file, no new key
    wait["markets"]["BTCUSDT"]["wait"] = "2026-11-16 20:00"           # the book now holds ANOTHER setup: not shown
    doc = setups.build(make_page(), voice=wait)
    m = ts.by_symbol(doc)["BTCUSDT"]
    assert list(m) == ts.MARKET and m["side"] == "FLAT" and all(m[k] is None for k in ts.POSITION)
    assert (m["closed"], m["wins"], m["realized_usd"]) == (4, 3, 500.25)          # the totals stay the book's own
    assert doc["book"] == setups.build(ts.make_page())["book"]                    # targets voice: today's book block
    assert [x for x in doc["markets"] if x["symbol"] != "BTCUSDT"] == \
        [x for x in today.values() if x["symbol"] != "BTCUSDT"]


def test_a_market_that_changed_back_hides_a_targets_setup_opened_before_that_moment():
    back = {"schema": 1, "markets": {"BTCUSDT": {"rule": "targets", "from_utc": "2026-11-17T03:00:00Z", "pending": False,
                                                 "wait": None}}}
    m = ts.by_symbol(setups.build(make_page(), voice=back))["BTCUSDT"]            # its setup opened 02:30: hidden
    assert list(m) == ts.MARKET and m["side"] == "FLAT" and m["entry"] is None and m["closed"] == 4
    back["markets"]["BTCUSDT"]["from_utc"] = "2026-11-17T02:30:00Z"               # opened AT that moment: shown
    doc = setups.build(make_page(), voice=back)
    assert doc == setups.build(ts.make_page())
    assert doc["book"]["rule"] == setups.BOOK_RULE and doc["book"]["verdict"] == "too few trades to judge (12 of 30)"


# ------------------------------------------------------------------ the record: what the page showed
def trail_row(t_in, t_out, side, p_in, p_out, why, pct, usd, **kw):
    r = ts.trow(t_in, t_out, side, p_in, p_out, why, pct, usd=usd, **kw)
    r[15] = r[16] = ""                                                # the trail book's file: no target columns
    return r


def split_files(d):
    """BTC changed over at 02:00 on the 17th. The targets book: two trades closed before (+100, -40), one opened by a
    flip in the changeover bar itself (01:45, closed after: +333, never shown, so never counted) and one opened after
    (+500, never shown). The trail book: one opened before (+900, already open at the changeover: never shown), one
    opened AT 02:00 (+60.5), two after (-20.25, +10). ETH never changed: one targets trade; its trail file is ignored."""
    ts.write_trades(d, "BTCUSDT", [
        ts.trow("2026-11-15 01:00", "2026-11-15 05:00", 1, 100000.0, 102000.0, "T1+T2", 1.0, usd=100.0),
        ts.trow("2026-11-16 22:00", "2026-11-17 01:45", -1, 100000.0, 100400.0, "STOP", -0.4, usd=-40.0),
        ts.trow("2026-11-17 01:45", "2026-11-17 02:30", 1, 100000.0, 103330.0, "T1+T2", 3.33, usd=333.0),
        ts.trow("2026-11-17 02:15", "2026-11-17 02:45", 1, 100000.0, 105000.0, "T1+T2", 5.0, usd=500.0)])
    ts.write_trades(d, "BTCUSDT", [
        trail_row("2026-11-17 01:45", "2026-11-17 02:15", 1, 100000.0, 109000.0, "TRAIL", 9.0, 900.0),
        trail_row("2026-11-17 02:00", "2026-11-17 02:15", 1, 100000.0, 100605.0, "TRAIL", 0.6, 60.5),
        trail_row("2026-11-17 02:15", "2026-11-17 02:30", -1, 100000.0, 100202.5, "STOP", -0.2, -20.25),
        trail_row("2026-11-17 02:30", "2026-11-17 02:45", 1, 100000.0, 100100.0, "FLIP", 0.1, 10.0)], book=BOOK)
    ts.write_trades(d, "ETHUSDT", [ts.trow("2026-11-16 03:00", "2026-11-16 04:00", -1, 2000.0, 1990.0, "T1+T2", 0.5, usd=50.0)])
    ts.write_trades(d, "ETHUSDT", [trail_row("2026-11-16 05:00", "2026-11-16 06:00", 1, 2000.0, 2100.0, "TRAIL", 5.0, 777.0)],
                    book=BOOK)
    return setups.read_trades(str(d)), setups.read_trades(str(d), BOOK)


def test_read_trades_takes_the_book_as_a_parameter(tmp_path):
    t, tt = split_files(tmp_path / "trades")
    assert [(s, r["pnl_usd"]) for s, r in t] == [("BTCUSDT", "100.0"), ("BTCUSDT", "-40.0"), ("BTCUSDT", "333.0"),
                                                 ("BTCUSDT", "500.0"),
                                                 ("ETHUSDT", "50.0")]
    assert [(s, r["pnl_usd"]) for s, r in tt] == [("BTCUSDT", "900.0"), ("BTCUSDT", "60.5"), ("BTCUSDT", "-20.25"),
                                                  ("BTCUSDT", "10.0"), ("ETHUSDT", "777.0")]
    assert all(r["target_1"] == "" and r["target_2"] == "" for _s, r in tt)
    assert setups.read_trades(str(tmp_path / "trades"), "b_trail") == []          # the yardstick's files are another book's
    assert setups.read_trades(str(tmp_path / "nowhere"), BOOK) == []


def test_the_record_of_a_trail_market_is_split_at_the_changeover(tmp_path):
    t, tt = split_files(tmp_path / "trades")
    doc = setups.build(make_page(), trades=t, trail_trades=tt, voice=voice("BTCUSDT"))
    by = ts.by_symbol(doc)
    m = by["BTCUSDT"]
    assert (m["closed"], m["wins"], m["realized_usd"]) == (5, 3, 110.25)          # 2 before + 3 from 02:00 on
    assert (by["ETHUSDT"]["closed"], by["ETHUSDT"]["wins"], by["ETHUSDT"]["realized_usd"]) == (2, 1, 150.0)   # its view
    cs = doc["closed_setups"]
    assert [(c["symbol"], c["opened_utc"][8:16], c["why_out"], c["result_usd"]) for c in cs] == [
        ("BTCUSDT", "17T02:30", "FLIP", 10.0), ("BTCUSDT", "17T02:15", "STOP", -20.25),
        ("BTCUSDT", "17T02:00", "TRAIL_STOP", 60.5), ("BTCUSDT", "16T22:00", "STOP", -40.0),
        ("ETHUSDT", "16T03:00", "TARGET_2", 50.0), ("BTCUSDT", "15T01:00", "TARGET_2", 100.0)]
    assert all(list(c) == list(cs[0]) for c in cs)                    # the same keys on every row
    for c in cs[:3]:                                                  # the trail book's rows: no targets
        assert (c["target_1"], c["target_2"], c["t1_taken"]) == (None, None, False) and c["stop"] is not None
    assert cs[3]["target_1"] is not None and cs[5]["t1_taken"] is True
    # the record is the sum of exactly those rows of that market
    mine = [c for c in cs if c["symbol"] == "BTCUSDT"]
    assert len(mine) == m["closed"] and sum(c["result_usd"] > 0 for c in mine) == m["wins"]
    assert round(sum(c["result_usd"] for c in mine), 2) == m["realized_usd"]
    # a row written twice counts once; a row that is not a whole trade counts nowhere
    doc2 = setups.build(make_page(), trades=t + t[:2] + [("BTCUSDT", {"t_in_ms": "x"}), "junk"],
                        trail_trades=tt + tt[1:3] + [("BTCUSDT", {}), None], voice=voice("BTCUSDT"))
    assert doc2 == doc
    # without the trail book's files only the targets trades from before the changeover are left
    m = ts.by_symbol(setups.build(make_page(), trades=t, voice=voice("BTCUSDT")))["BTCUSDT"]
    assert (m["closed"], m["wins"], m["realized_usd"]) == (2, 1, 60.0)
    # the same files with the switch off: the targets book's rows, all of them, and no trail row
    off = setups.build(make_page(), trades=t, trail_trades=tt)
    assert [c["result_usd"] for c in off["closed_setups"]] == [500.0, 333.0, -40.0, 50.0, 100.0]
    assert "TRAIL_STOP" not in text(off)


def test_closed_setups_codes_of_the_trail_book():
    assert setups.why_code("TRAIL", trail=True) == "TRAIL_STOP" and setups.why_code("STOP", trail=True) == "STOP"
    assert setups.why_code("FLIP", trail=True) == "FLIP" and setups.why_code("STEP_ASIDE", trail=True) == "EXIT"
    assert setups.why_code("T1+TRAIL", trail=True) == "OTHER" and setups.why_code("trail", trail=True) == "OTHER"
    for w in ("TRAIL", "T1+TRAIL"):                                   # the targets book has no such exit: as before
        assert setups.why_code(w) == setups.why_code(w, trail=False) == "OTHER"
    assert (setups.TRAIL_WORD, setups.TRAIL_CODE) == ("TRAIL", "TRAIL_STOP")
    assert shadows._stop_word(False, True) == setups.TRAIL_WORD       # the word shadows.run writes for it


def test_write_reads_the_trail_books_files_only_for_a_market_on_the_trail_voice(tmp_path):
    d, data, live = tmp_path / "trades", tmp_path / "data", tmp_path / "live"
    split_files(d)
    data.mkdir()
    with open(str(data / "setups_voice_state.json"), "w", encoding="utf-8") as fh:
        json.dump(voice("BTCUSDT"), fh)                               # (the switch itself is off: update changes over
    info = setups.write(make_page(), out_dir=str(live), data_dir=str(data), trades_dir=str(d))   # back; see below)
    doc = json.load(open(info["path"], encoding="utf-8"))
    m = ts.by_symbol(doc)["BTCUSDT"]
    assert (m["exit_rule"], m["closed"], m["wins"], m["realized_usd"]) == ("trail", 5, 3, 110.25)
    assert [c["why_out"] for c in doc["closed_setups"]][:3] == ["FLIP", "STOP", "TRAIL_STOP"]
    # the shipped switch names no market, so the state now waits to change BACK when the shown trail setup ends
    st = json.load(open(str(data / "setups_voice_state.json"), encoding="utf-8"))
    assert st["markets"]["BTCUSDT"] == {"rule": "trail", "from_utc": FROM, "pending": True, "wait": "2026-11-17 02:45"}


# ------------------------------------------------------------------ the book block
def test_the_book_block_with_one_market_on_the_trail_voice(tmp_path):
    t, tt = split_files(tmp_path / "trades")
    doc = setups.build(make_page(), trades=t, trail_trades=tt, voice=voice("BTCUSDT"))
    b, today = doc["book"], setups.build(ts.make_page())["book"]
    assert list(b) == list(today) == ["name", "rule", "closed", "won", "won_pct", "net_usd", "equity_usd", "verdict"]
    assert b["name"] == "Setups" and b["rule"] == setups.BOOK_RULE_MIXED
    assert b["verdict"] is None                                       # one scoreboard row no longer describes it
    # the totals stay the sum of the rows: BTC's 4 / 3 / +500.25 give way to 5 / 3 / +110.25
    assert (b["closed"], b["won"]) == (12 - 4 + 5, 7 - 3 + 3) == (sum(m["closed"] for m in doc["markets"]),
                                                                   sum(m["wins"] for m in doc["markets"]))
    assert b["won_pct"] == 53.85 and b["net_usd"] == round(1102.41 - 500.25 + 110.25, 2)
    assert b["net_usd"] == round(sum(m["realized_usd"] or 0.0 for m in doc["markets"]), 2)
    # equity: BTC's 10600.25 gives way to 10000 + its realized record + the shown setup's open result
    assert b["equity_usd"] == round(71911.46 - 10600.25 + 10000.0 + 110.25 + 160.0, 2)
    flat = setups.build(make_page(), trades=t, trail_trades=tt, voice=voice("BTCUSDT", from_utc="2026-11-17T03:00:00Z"))
    assert ts.by_symbol(flat)["BTCUSDT"]["side"] == "FLAT"            # nothing shown: no open result is counted
    m = ts.by_symbol(flat)["BTCUSDT"]
    assert (m["closed"], m["realized_usd"]) == (4, 893.0)            # all four targets trades closed before 03:00
    assert flat["book"]["equity_usd"] == round(71911.46 - 10600.25 + 10000.0 + 893.0, 2)


def test_the_rule_text_is_one_of_three_and_names_no_book():
    page = make_page()
    every = voice(*ts.ORDER)
    texts = {0: setups.build(page)["book"]["rule"], 1: setups.build(page, voice=voice("BTCUSDT", "ETHUSDT"))["book"]["rule"],
             8: setups.build(page, voice=every)["book"]["rule"]}
    assert texts == {0: setups.BOOK_RULE, 1: setups.BOOK_RULE_MIXED, 8: setups.BOOK_RULE_TRAIL}
    assert setups.BOOK_RULE == "half at target 1, rest at target 2, stop to entry after target 1"
    assert setups.BOOK_RULE_TRAIL == "no targets; from 1R in favour the stop trails the 15m swing or 2 ATR"
    assert setups.BOOK_RULE in setups.BOOK_RULE_MIXED and "the stop trails the 15m swing or 2 ATR" in setups.BOOK_RULE_MIXED
    doc = setups.build(page, voice=every)
    assert doc["book"]["verdict"] is None and all(m["exit_rule"] == "trail" for m in doc["markets"])
    assert [m["side"] for m in doc["markets"]] == ["LONG", "SHORT", "FLAT", "FLAT", "LONG", "FLAT", "FLAT", "SHORT"]
    for d in (doc, setups.build(page, voice=voice("BTCUSDT", "ETHUSDT"))):     # the wording rule of the whole file
        for s in ts.strings(d):
            low = s.lower()
            assert "kronos" not in low and not any(b in low for b in ts.OTHER_BOOKS), s
        json.loads(json.dumps(d, allow_nan=False))


# ------------------------------------------------------------------ the landing file
def test_the_landing_of_a_trail_market_is_new_then_running_and_leaks_no_level():
    s1 = {"scoreboard": None, "state": ts._state(opened="2026-11-17 02:45")}
    page = make_page()
    doc = setups.build(page, s1=s1, voice=voice("BTCUSDT", "ETHUSDT", "XAUUSD"))
    land = setups.build_landing(doc, page)
    board = dict((b["symbol"], b) for b in land["board"])
    assert list(board["BTCUSDT"]) == ["symbol", "short", "side", "opened_utc", "state", "rr_now_t2", "market_open"]
    assert board["BTCUSDT"] == {"symbol": "BTCUSDT", "short": "BTC", "side": "LONG", "opened_utc": "2026-11-17T02:45:00Z",
                                "state": "new", "rr_now_t2": None, "market_open": True}          # its window is open
    assert (board["ETHUSDT"]["side"], board["ETHUSDT"]["state"], board["ETHUSDT"]["rr_now_t2"]) == ("SHORT", "running", None)
    assert (board["XAUUSD"]["side"], board["XAUUSD"]["state"], board["XAUUSD"]["opened_utc"]) == ("FLAT", "flat", None)
    assert land["record"]["verdict"] is None and land["record"]["open"] == sum(m["side"] != "FLAT" for m in doc["markets"])
    txt = json.dumps(land["board"])
    for k in ("entry", "stop", "target_1", "target_2", "price", "trail_active", "exit_rule"):
        assert '"%s"' % k not in txt
    for level in ("100200", "100650", "1960"):                        # the trail setups' entry and stops
        assert level not in json.dumps(land)
    # there is no Target 1 to be "near": a trail market at its entry is running, where a targets market would be near
    m = {"side": "LONG", "entry": 100.0, "stop": 90.0, "target_1": 120.0, "price": 101.0, "t1_taken": False,
         "entry_window_open": False}
    assert setups._state(m) == "near" and setups._state(dict(m, exit_rule="trail", target_1=None)) == "running"
    assert setups._state(dict(m, exit_rule="trail")) == "running"     # whatever else the entry holds
    assert setups._state(dict(m, exit_rule="trail", entry_window_open=True)) == "new"
    assert setups._state(dict(m, exit_rule="trail", side="FLAT")) == "flat"


# ------------------------------------------------------------------ setup_events.json
def row(sid, key, ev, t, **kw):
    """One line of the S1 log (a stop_moved row has a field called `kind`, so the event's own name is `ev` here)."""
    return dict({"t": t, "id": sid, "k": key, "ev": ev, "asset": key.split("|")[0], "delivered": True}, **kw)


def trail_log():
    a, b = "BTCUSDT|2026-11-18 05:00", "ETHUSDT|2026-11-18 06:00"
    return [
        row("BTC-1118-01", a, "signal", "2026-11-18T05:01:00Z", side=1, entry=100000.0, stop=98000.0, t1=None, t2=None,
              rule="trail", fee=0.0005, opened_utc="2026-11-18 05:00", valid_until_utc="2026-11-18T06:15:00Z", msg_id=9),
        row("BTC-1118-01", a, "filled", "2026-11-18T05:31:00Z", px=100000.0, bar_utc="2026-11-18T05:15:00Z"),
        row("BTC-1118-01", a, "stop_moved", "2026-11-18T07:01:00Z", px=100400.123456, bar_utc="2026-11-18T06:45:00Z",
              kind="armed"),
        row("BTC-1118-01", a, "stop_moved", "2026-11-18T07:16:00Z", px=100900.0, bar_utc="2026-11-18T07:00:00Z",
              kind="past_entry"),
        row("BTC-1118-01", a, "stop_moved", "2026-11-18T09:01:00Z", px=102000.0, bar_utc="2026-11-18T08:45:00Z",
              kind="step"),
        row("BTC-1118-01", a, "stop_moved", "2026-11-18T09:01:30Z", px=102100.0, bar_utc="2026-11-18T08:45:00Z",
              kind="something new"),                                  # the same bar again, a kind not on the list
        row("BTC-1118-01", a, "closed", "2026-11-18T10:01:00Z", why="trail", px=102000.0, bar_utc="2026-11-18T09:45:00Z",
              pct=1.9, usd=190.0, r=0.95),
        row("ETH-1118-01", b, "signal", "2026-11-18T06:01:00Z", side=-1, entry=2000.0, stop=2060.0, t1=None, t2=None,
              rule="trail", valid_until_utc="2026-11-18T07:15:00Z"),
        row("ETH-1118-01", b, "no_fill", "2026-11-18T06:31:00Z", reason="ran", bar_utc="2026-11-18T06:15:00Z"),
    ]


def test_events_of_a_trail_signal():
    assert (setups.EV_TYPE["stop_moved"], setups.CLOSED_CODE["trail"], setups.NO_FILL_CODE["ran"]) == \
        ("STOP_MOVED", "TRAIL_STOP", "RAN_FIRST")
    assert setups.MOVED_CODE == {"armed": "TRAIL_ARMED", "past_entry": "PAST_ENTRY", "step": "STEP"}
    doc = setups.build_events(trail_log(), generated_utc="2026-11-18T12:00:00Z")
    evs = doc["events"]
    assert len(evs) == 9 and all(list(e) == ts.EVENT_KEYS for e in evs)          # the same keys as every other event
    by = dict((e["id"], e) for e in evs)
    assert sorted(by) == ["BTC-1118-01:CLOSED", "BTC-1118-01:ENTRY_FILLED", "BTC-1118-01:NEW_SETUP",
                          "BTC-1118-01:STOP_MOVED:20261118T0645", "BTC-1118-01:STOP_MOVED:20261118T0700",
                          "BTC-1118-01:STOP_MOVED:20261118T0845", "BTC-1118-01:STOP_MOVED:20261118T0845:2",
                          "ETH-1118-01:NEW_SETUP", "ETH-1118-01:NO_FILL"]
    new = by["BTC-1118-01:NEW_SETUP"]
    assert (new["entry"], new["stop"], new["target_1"], new["target_2"]) == (100000.0, 98000.0, None, None)
    assert new["entry_valid_until_utc"] == "2026-11-18T06:15:00Z" and new["reason_code"] is None
    e = by["BTC-1118-01:STOP_MOVED:20261118T0645"]
    assert e == {"id": "BTC-1118-01:STOP_MOVED:20261118T0645", "signal_id": "BTC-1118-01", "type": "STOP_MOVED",
                 "symbol": "BTCUSDT", "side": "LONG", "utc": "2026-11-18T07:01:00Z", "bar_utc": "2026-11-18T06:45:00Z",
                 "entry": 100000.0, "stop": 100400.12,                # the NEW stop, not the signal's first one
                 "target_1": None, "target_2": None, "price": None, "entry_valid_until_utc": None, "result_pct": None,
                 "r": None, "reason_code": "TRAIL_ARMED"}
    assert [(by[k]["stop"], by[k]["reason_code"]) for k in sorted(by) if ":STOP_MOVED:" in k] == [
        (100400.12, "TRAIL_ARMED"), (100900.0, "PAST_ENTRY"), (102000.0, "STEP"), (102100.0, None)]
    c = by["BTC-1118-01:CLOSED"]
    assert (c["reason_code"], c["price"], c["stop"], c["result_pct"], c["r"]) == ("TRAIL_STOP", 102000.0, 98000.0, 1.9, 0.95)
    n = by["ETH-1118-01:NO_FILL"]
    assert (n["reason_code"], n["side"], n["stop"], n["target_1"], n["price"]) == ("RAN_FIRST", "SHORT", 2060.0, None, None)
    assert [e["utc"] for e in evs] == sorted([e["utc"] for e in evs], reverse=True)
    for s in ts.strings(doc):
        assert "kronos" not in s.lower() and "something new" not in s
    json.loads(json.dumps(doc, allow_nan=False))
    assert setups.build_events(trail_log(), generated_utc="2026-11-18T12:00:00Z") == doc     # the same log, the same ids


def test_todays_events_come_out_exactly_as_before_beside_trail_rows():
    alone = setups.build_events(ts.event_log(), generated_utc="2026-11-17T12:00:00Z")["events"]
    mixed = setups.build_events(ts.event_log() + trail_log(), generated_utc="2026-11-17T12:00:00Z")["events"]
    assert [e for e in mixed if not e["signal_id"].endswith("-1118-01")] == alone
    assert not any(e["type"] == "STOP_MOVED" or e["reason_code"] in ("TRAIL_STOP", "RAN_FIRST") for e in alone)
    # a stop_moved row with no signal id is left out like any other; one for an unknown signal still has its stop
    odd = [dict(row("X-1", "WTI|2026-11-18 01:00", "stop_moved", "2026-11-18T02:00:00Z", px=80.123456, kind="step")),
           {"t": "2026-11-18T02:00:00Z", "ev": "stop_moved", "k": "WTI|2026-11-18 01:00", "px": 80.0}]
    (e,) = setups.build_events(odd)["events"]
    assert (e["id"], e["symbol"], e["side"]) == ("X-1:STOP_MOVED:20261118T0200", "WTI", None)
    assert (e["stop"], e["entry"]) == (80.12346, None)


# ------------------------------------------------------------------ nothing about the inputs is changed
def test_build_on_a_voice_state_is_pure(tmp_path):
    t, tt = split_files(tmp_path / "trades")
    page, v = make_page(), voice("BTCUSDT", "ETHUSDT")
    before = copy.deepcopy((page, v, t, tt))
    one = setups.build(page, trades=t, trail_trades=tt, voice=v)
    assert (page, v, t, tt) == before and setups.build(page, trades=t, trail_trades=tt, voice=v) == one
