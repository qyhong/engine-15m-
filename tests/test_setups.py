# -*- coding: utf-8 -*-
"""setups.json (engine15/setups.py): one voice per market from the b_targets view of a synthetic page, the record
blocks, the wording rule, valid JSON, the atomic write and its web copy, and the live step's guard.

    py -3 -m pytest tests/test_setups.py -q

Nothing real runs here: the pages are made up, the files live in pytest's tmp folders, and the live step is the
stand-in step of tests/test_step_timing.py (no network, no source, no book).
"""
import copy
import json
import os
import stat
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import pytest  # noqa: E402

import test_step_timing as timing  # noqa: E402
from engine15 import export, live, setups, signals  # noqa: E402

TOP = ["generated_utc", "version", "schema", "note", "book", "followable", "learning", "markets"]
MARKET = ["symbol", "short", "group", "side", "entry", "stop", "target_1", "target_2", "t1_taken", "opened_utc", "price",
          "price_bar_utc", "unrealized_usd", "unrealized_pct", "market_open", "next_open_utc", "edge_with_position_pts",
          "hit_24h_30d_pct", "rr_now_t1", "rr_now_t2", "stop_dist_now_pct", "entry_window_open", "entry_valid_until_utc",
          "closed", "wins", "realized_usd"]
POSITION = ["entry", "stop", "target_1", "target_2", "opened_utc", "unrealized_usd", "unrealized_pct",
            "edge_with_position_pts", "rr_now_t1", "rr_now_t2", "stop_dist_now_pct", "entry_valid_until_utc"]
ORDER = ["BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "USDJPY", "SPX", "WTI", "BRENT"]
OTHER_BOOKS = ("b_targets", "b_trail", "b_be_t1", "h3_flip", "a_pullback", "m_swing", "y_4h", "shadow", "main book",
               "playbook", "challenger")


@pytest.fixture(autouse=True)
def _alone(monkeypatch, tmp_path):
    """No web folder and no real S1 record unless a test asks for one."""
    monkeypatch.delenv(setups.WEB_ENV, raising=False)
    monkeypatch.setattr(setups, "S1_DIR", str(tmp_path / "no_s1_here"))


def view(status="FLAT", **kw):
    return dict({"status": status, "equity": 10000.0, "realized_usd": 0.0, "fees_usd": 0.0, "trades": 0, "wins": 0}, **kw)


def asset(short, group, price, edge, position="FLAT", time="2026-11-17 03:15", **kw):
    return dict({"name": short + " (long name)", "short": short, "time": time, "price": price, "position": position,
                 "edge_pts": edge, "market_group": group, "decision": "a sentence", "cards": [], "voices": []}, **kw)


def make_page():
    """Eight markets: LONG, SHORT after Target 1, FLAT while the main book is short, WAITING, the price beyond
    Target 2, a shut market, a view with fields missing, the price beyond the stop."""
    views = {
        "BTCUSDT": view("LONG", equity=10600.25, realized_usd=500.25, trades=4, wins=3, entry=100000.0, stop=98000.0,
                        opened_utc="2026-11-17 02:30", opened_by="ENTER", unrealized_usd=100.0, target_1=103000.0,
                        target_2=105000.0, t1_taken=False),
        # Target 1 taken: the view may still show the first stop in the bar it was taken; the stop is the entry
        "ETHUSDT": view("SHORT", equity=10300.0, realized_usd=150.0, trades=2, wins=1, entry=2000.0, stop=2100.0,
                        opened_utc="2026-11-16 09:15", unrealized_usd=75.0, target_1=1900.0, target_2=1800.0, t1_taken=True),
        "XAUUSD": view("FLAT", equity=10766.21, realized_usd=766.21, trades=2, wins=2),
        "XAGUSD": view("WAITING LONG", limit=47.0, limit_basis="a pullback", bars_left=3, entry=47.1, stop=46.0,
                       target_1=48.0, target_2=49.0),
        "USDJPY": view("LONG", equity=10100.0, realized_usd=-25.5, trades=3, wins=1, entry=159.765, stop=159.222,
                       opened_utc="2026-11-13 07:45", unrealized_usd=210.0, target_1=160.413, target_2=160.85, t1_taken=False),
        "SPX": view("SHORT", equity=10245.0, entry=7596.66, stop=7740.72, opened_utc="2026-11-11 15:45",
                    unrealized_usd=245.0, target_1=7251.01, target_2=7124.64, t1_taken=False),
        "WTI": {"status": "LONG", "entry": 85.0},                 # nothing else: no stop, no targets, no record
        "BRENT": view("LONG", equity=9900.0, realized_usd=-288.55, trades=1, wins=0, entry=95.0, stop=94.0,
                      opened_utc="2026-11-12 19:15", unrealized_usd=-150.0, target_1=97.0, target_2=98.0, t1_taken=False),
    }
    main = dict((a, view("SHORT", entry=4029.2, stop=4085.66, opened_utc="2026-11-11 18:30", unrealized_usd=999.0))
                for a in views)
    return {
        "name": "Mind 15", "generated_utc": "2026-11-17T03:42:19Z", "version": "think15-v5.2.4",
        "note": "Experimental model. Paper only. Not advice.",
        "markets": {"crypto": ["BTCUSDT", "ETHUSDT"], "metals": ["XAUUSD", "XAGUSD"], "fx": ["USDJPY"], "index": ["SPX"],
                    "energy": ["WTI", "BRENT"]},
        "assets": {
            "BTCUSDT": asset("BTC", "crypto", 101000.0, 2.5, "LONG"),
            "ETHUSDT": asset("ETH", "crypto", 1850.0, -4.5, "SHORT"),
            "XAUUSD": asset("GOLD", "metals", 3876.2, -0.7, "SHORT", stop=4085.6644, entry=4029.2,
                            trade={"status": "SHORT", "entry_price": 4029.2, "stop_price": 4085.66,
                                   "target_1_price": 3954.54, "unrealized_usd": 1279.97}),
            "XAGUSD": asset("SILVER", "metals", 47.455, -0.5, "SHORT"),
            "USDJPY": asset("USDJPY", "fx", 160.90001, 0.2, "LONG", time="2026-11-17 03:30"),
            "SPX": asset("S&P 500", "index", 7420.19, 3.0, "SHORT", time="2026-11-16 21:00"),
            "WTI": {"name": "WTI crude oil", "short": "WTI"},     # no price, no time, no edge, no group
            "BRENT": asset("BRENT", "energy", 93.5, 1.1, "SHORT"),
        },
        "shadows": {
            "scoreboard": {"rows": [{"book": "b_targets", "equity": 1.0, "trades": 99}]},
            "books": {"main": {"title": "Main rule (v5), fresh copy", "assets": main},
                      "b_targets": {"title": "B: half at Target 1, rest at Target 2", "assets": views}},
            "markets": {"crypto": {"as_of_utc": "2026-11-17 03:15", "assets": {}},
                        "energy": {"as_of_utc": "2026-11-17 03:15", "assets": {"WTI": {"price": 85.11}}}},
        },
        "scoreboard_all": {"rows": [
            {"book": "main", "title": "Main books (live)", "kind": "main", "trades": 5, "verdict": "too few trades to judge (5 of 30)"},
            {"book": "b_targets", "title": "Shadow: b_targets", "kind": "shadow", "trades": 12, "net_usd": 1102.4,
             "verdict": "too few trades to judge (12 of 30)", "won_pct": 58.3}]},
        "learning": {"last_7_days": {"right": 10, "wrong": 10, "neither": 5, "hit_pct": 50.0, "edge_hit_pct": 60.6},
                     "last_30_days": {"right": 60, "wrong": 40, "neither": 9, "hit_pct": 60.0}, "trust": {"kr": 0.2}},
        "horizon_skill": {"markets": {"BTCUSDT": {"24h": {"d7": [65.4, 72.2, 223], "d30": [53.9, 48.4, 440]}},
                                      "ETHUSDT": {"24h": {"d30": [None, None, 0]}}}},
    }


def by_symbol(doc):
    return dict((m["symbol"], m) for m in doc["markets"])


def strings(x):
    """Every text VALUE in a document (keys are machine names and are not looked at)."""
    if isinstance(x, dict):
        return [s for v in x.values() for s in strings(v)]
    if isinstance(x, list):
        return [s for v in x for s in strings(v)]
    return [x] if isinstance(x, str) else []


# ------------------------------------------------------------------ the shape
def test_schema_names_order_and_top_level():
    doc = setups.build(make_page())
    assert list(doc) == TOP
    assert (doc["generated_utc"], doc["version"], doc["schema"]) == ("2026-11-17T03:42:19Z", "think15-v5.2.4", 1)
    assert doc["note"] == "Experimental model. Paper only. Not advice."
    assert [m["symbol"] for m in doc["markets"]] == ORDER            # the page's own order, all eight
    assert all(list(m) == MARKET for m in doc["markets"])
    assert [m["short"] for m in doc["markets"]] == ["BTC", "ETH", "GOLD", "SILVER", "USDJPY", "S&P 500", "WTI", "BRENT"]
    assert [m["group"] for m in doc["markets"]] == ["crypto", "crypto", "metals", "metals", "fx", "index", "energy", "energy"]
    assert [m["side"] for m in doc["markets"]] == ["LONG", "SHORT", "FLAT", "FLAT", "LONG", "SHORT", "LONG", "LONG"]
    assert set(m["side"] for m in doc["markets"]) <= {"LONG", "SHORT", "FLAT"}


def test_build_is_pure():
    page = make_page()
    before = copy.deepcopy(page)
    a, b = setups.build(page), setups.build(page)
    assert page == before and a == b                                  # the page is not touched; the same page, the same file


def test_no_view_of_the_book_is_an_error_not_eight_flats():
    page = make_page()
    del page["shadows"]["books"]["b_targets"]
    with pytest.raises(ValueError):
        setups.build(page)
    page["shadows"] = None                                            # export.merge leaves None when the block failed
    with pytest.raises(ValueError):
        setups.build(page)
    with pytest.raises(ValueError):
        setups.build({"shadows": {"books": {"b_targets": {"assets": {}}}}, "assets": {}})
    with pytest.raises(ValueError):
        setups.build([1, 2])
    # a market the book has not started in yet holds nothing: FLAT
    page = make_page()
    del page["shadows"]["books"]["b_targets"]["assets"]["BRENT"]
    m = by_symbol(setups.build(page))["BRENT"]
    assert m["side"] == "FLAT" and m["closed"] == 0 and m["realized_usd"] is None and m["price"] == 93.5


# ------------------------------------------------------------------ one voice per market
def test_long():
    m = by_symbol(setups.build(make_page()))["BTCUSDT"]
    assert (m["side"], m["entry"], m["stop"], m["target_1"], m["target_2"]) == ("LONG", 100000.0, 98000.0, 103000.0, 105000.0)
    assert m["t1_taken"] is False and m["opened_utc"] == "2026-11-17T02:30:00Z"
    assert (m["price"], m["price_bar_utc"]) == (101000.0, "2026-11-17T03:15:00Z")
    assert (m["unrealized_usd"], m["unrealized_pct"]) == (100.0, 1.0)
    assert m["rr_now_t1"] == 0.67 and m["rr_now_t2"] == 1.33          # 2000 / 3000 and 4000 / 3000 from the price
    assert m["stop_dist_now_pct"] == 2.97                             # 3000 / 101000
    assert m["edge_with_position_pts"] == 2.5                         # up-minus-down +2.5 with a LONG: agrees
    assert m["hit_24h_30d_pct"] == 53.9
    assert (m["closed"], m["wins"], m["realized_usd"]) == (4, 3, 500.25)
    assert (m["market_open"], m["next_open_utc"]) == (True, None)
    assert (m["entry_window_open"], m["entry_valid_until_utc"]) == (False, None)


def test_short_after_target_1_the_stop_is_the_entry():
    m = by_symbol(setups.build(make_page()))["ETHUSDT"]
    assert m["side"] == "SHORT" and m["t1_taken"] is True
    assert (m["entry"], m["stop"]) == (2000.0, 2000.0)                # not the 2100 the view still showed
    assert m["rr_now_t1"] is None
    assert m["rr_now_t2"] == 0.33                                     # (1850 - 1800) / (2000 - 1850)
    assert m["stop_dist_now_pct"] == 8.11                             # 150 / 1850
    assert m["unrealized_pct"] == 7.5
    assert m["edge_with_position_pts"] == 4.5                         # -4.5 with a SHORT: agrees
    assert m["hit_24h_30d_pct"] is None                               # the page has the market but no number
    page = make_page()                                                # the price back behind the entry: nothing to say
    page["assets"]["ETHUSDT"]["price"] = 2010.0
    m = by_symbol(setups.build(page))["ETHUSDT"]
    assert (m["rr_now_t2"], m["stop_dist_now_pct"], m["unrealized_pct"]) == (None, None, -0.5)


def test_edge_sign_positive_means_it_agrees_with_the_side():
    page = make_page()
    got = by_symbol(setups.build(page))
    assert got["SPX"]["edge_with_position_pts"] == -3.0               # +3.0 (favours up) against a SHORT
    assert got["USDJPY"]["edge_with_position_pts"] == 0.2
    assert got["BRENT"]["edge_with_position_pts"] == 1.1
    assert got["XAUUSD"]["edge_with_position_pts"] is None            # FLAT
    page["assets"]["BTCUSDT"]["edge_pts"] = -2.5
    page["assets"]["ETHUSDT"]["edge_pts"] = None
    got = by_symbol(setups.build(page))
    assert got["BTCUSDT"]["edge_with_position_pts"] == -2.5 and got["ETHUSDT"]["edge_with_position_pts"] is None


def test_flat_while_the_main_book_is_positioned_is_flat_with_nulls():
    doc = setups.build(make_page())
    m = by_symbol(doc)["XAUUSD"]
    assert m["side"] == "FLAT" and m["t1_taken"] is False and m["entry_window_open"] is False
    assert all(m[k] is None for k in POSITION)
    assert (m["price"], m["price_bar_utc"]) == (3876.2, "2026-11-17T03:15:00Z")      # the price is still shown
    assert (m["closed"], m["wins"], m["realized_usd"]) == (2, 2, 766.21)             # and the book's record there
    text = json.dumps(m)
    assert "4029.2" not in text and "4085" not in text and "3954" not in text and "1279.97" not in text   # no second voice


def test_waiting_is_flat():
    m = by_symbol(setups.build(make_page()))["XAGUSD"]
    assert m["side"] == "FLAT" and all(m[k] is None for k in POSITION) and "47.1" not in json.dumps(m)


def test_price_beyond_the_target_or_the_stop():
    got = by_symbol(setups.build(make_page()))
    m = got["USDJPY"]                                                 # 160.9 is past Target 2 (160.85)
    assert m["price"] == 160.9 and m["price_bar_utc"] == "2026-11-17T03:30:00Z"
    assert (m["rr_now_t1"], m["rr_now_t2"]) == (None, None) and m["stop_dist_now_pct"] == 1.04
    m = got["BRENT"]                                                  # 93.5 is through the stop (94)
    assert (m["rr_now_t1"], m["rr_now_t2"], m["stop_dist_now_pct"]) == (None, None, None)
    assert m["unrealized_pct"] == -1.58 and m["stop"] == 94.0
    page = make_page()                                                # exactly at the stop, exactly at Target 1
    page["assets"]["BRENT"]["price"] = 94.0
    page["assets"]["BTCUSDT"]["price"] = 103000.0
    got = by_symbol(setups.build(page))
    assert (got["BRENT"]["rr_now_t1"], got["BRENT"]["stop_dist_now_pct"]) == (None, None)
    assert got["BTCUSDT"]["rr_now_t1"] is None and got["BTCUSDT"]["rr_now_t2"] == 0.4


def test_missing_fields_are_null():
    page = make_page()
    m = by_symbol(setups.build(page))["WTI"]
    assert m["side"] == "LONG" and m["entry"] == 85.0 and m["group"] == "energy"
    assert all(m[k] is None for k in ("stop", "target_1", "target_2", "opened_utc", "unrealized_usd", "rr_now_t1",
                                      "rr_now_t2", "stop_dist_now_pct", "edge_with_position_pts", "hit_24h_30d_pct",
                                      "realized_usd"))
    assert (m["price"], m["price_bar_utc"]) == (85.11, "2026-11-17T03:15:00Z")       # the book's own mark and close
    assert m["unrealized_pct"] == 0.13 and (m["closed"], m["wins"], m["t1_taken"]) == (0, 0, False)
    for k in ("learning", "horizon_skill", "scoreboard_all", "markets", "version"):
        page.pop(k)
    doc = setups.build(page)
    assert doc["learning"] == {"hit_7d_pct": None, "n_7d": None, "hit_30d_pct": None, "n_30d": None}
    assert doc["book"]["verdict"] is None and doc["version"] is None
    assert [m["symbol"] for m in doc["markets"]] == ORDER             # the assets' own order when the group list is gone
    assert by_symbol(doc)["BTCUSDT"]["hit_24h_30d_pct"] is None and by_symbol(doc)["WTI"]["group"] is None
    page["assets"]["BTCUSDT"] = None                                  # an asset entry that is not there at all
    m = by_symbol(setups.build(page))["BTCUSDT"]
    assert (m["side"], m["price"], m["short"], m["rr_now_t1"], m["entry"]) == ("LONG", None, "BTCUSDT", None, 100000.0)


def test_a_shut_market():
    got = by_symbol(setups.build(make_page()))                        # "now" is the page's own time: Tuesday 03:42 UTC
    assert (got["SPX"]["market_open"], got["SPX"]["next_open_utc"]) == (False, "2026-11-17T14:30:00Z")
    assert got["SPX"]["price_bar_utc"] == "2026-11-16T21:00:00Z" and got["SPX"]["side"] == "SHORT"
    assert all(got[a]["market_open"] is True and got[a]["next_open_utc"] is None for a in ORDER if a != "SPX")
    sat = by_symbol(setups.build(make_page(), now=datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)))
    assert [sat[a]["market_open"] for a in ORDER] == [True, True, False, False, False, False, False, False]
    assert sat["XAUUSD"]["next_open_utc"] == sat["WTI"]["next_open_utc"] == "2026-11-15T23:00:00Z"   # Sunday 18:00 New York
    assert sat["USDJPY"]["next_open_utc"] == "2026-11-15T22:00:00Z"
    assert sat["BRENT"]["next_open_utc"] == "2026-11-16T01:00:00Z"
    assert sat["SPX"]["next_open_utc"] == "2026-11-16T14:30:00Z" and sat["BTCUSDT"]["next_open_utc"] is None
    assert setups.build(make_page(), now="2026-11-14 12:00") == setups.build(make_page(), now="2026-11-14T12:00:00Z")
    assert setups.market_hours("NOSUCH", 0) == (None, None) and setups.market_hours("SPX", None) == (None, None)
    page = make_page()
    page["generated_utc"] = "not a time"                              # no clock to ask: not said, not guessed
    assert all(m["market_open"] is None and m["next_open_utc"] is None for m in setups.build(page)["markets"])


# ------------------------------------------------------------------ the record blocks
def test_book_block():
    b = setups.build(make_page())["book"]
    assert list(b) == ["name", "rule", "closed", "won", "won_pct", "net_usd", "equity_usd", "verdict"]
    assert b["name"] == "Setups" and b["rule"] == "half at target 1, rest at target 2, stop to entry after target 1"
    assert (b["closed"], b["won"], b["won_pct"]) == (12, 7, 58.33)    # the sum of the rows below
    assert b["net_usd"] == 1102.41 and b["equity_usd"] == 71911.46
    assert b["verdict"] == "too few trades to judge (12 of 30)"
    page = make_page()
    for v in page["shadows"]["books"]["b_targets"]["assets"].values():
        v.update(trades=0, wins=0)
    page["scoreboard_all"]["rows"][1]["verdict"] = "no trades yet"
    b = setups.build(page)["book"]
    assert (b["closed"], b["won"], b["won_pct"], b["verdict"]) == (0, 0, None, "no trades yet")


def test_learning_block():
    assert setups.build(make_page())["learning"] == {"hit_7d_pct": 50.0, "n_7d": 20, "hit_30d_pct": 60.0, "n_30d": 100}


def _row(sid, key, ev, t, **kw):
    return dict({"t": t, "id": sid, "k": key, "ev": ev, "asset": key.split("|")[0]}, **kw)


def write_log(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    a, b, c = "BTCUSDT|2026-11-17 05:00", "XAUUSD|2026-11-17 06:00", "SPX|2026-11-17 15:00"
    rows = [{"t": "2026-11-17T04:58:00Z", "k": "start", "ev": "start", "live_since": "2026-11-17T04:58:00Z"},
            _row("BTC-1117-01", a, "signal", "2026-11-17T05:16:00Z", side=1),
            _row("BTC-1117-01", a, "filled", "2026-11-17T05:46:00Z", px=100.0),
            _row("BTC-1117-01", a, "closed", "2026-11-17T09:01:00Z", why="t2", pct=1.5, usd=150.0, r=1.2),
            _row("XAU-1117-01", b, "signal", "2026-11-17T06:16:00Z", side=-1),
            _row("XAU-1117-01", b, "filled", "2026-11-17T06:31:00Z", px=4000.0),
            _row("XAU-1117-01", b, "closed", "2026-11-17T08:01:00Z", why="stop", pct=-0.8, usd=-80.0, r=-1.0),
            _row("SPX-1117-01", c, "signal", "2026-11-17T15:16:00Z", side=1),
            _row("SPX-1117-01", c, "no_fill", "2026-11-17T16:31:00Z", reason="window")]
    with open(str(d / "signals_log.jsonl"), "w", encoding="utf-8") as fh:
        fh.write("".join(json.dumps(r) + "\n" for r in rows) + "{ a line cut sho")
    return str(d)


def test_followable_with_a_log(tmp_path):
    s1 = setups.load_s1(write_log(tmp_path))
    f = setups.build(make_page(), s1=s1)["followable"]
    assert list(f) == ["live_since_utc", "signals", "filled", "fill_rate_pct", "closed", "won_pct", "net_pct", "net_r", "verdict"]
    assert f == {"live_since_utc": "2026-11-17T04:58:00Z", "signals": 3, "filled": 2, "fill_rate_pct": 66.7, "closed": 2,
                 "won_pct": 50.0, "net_pct": 0.7, "net_r": 0.2, "verdict": "too few trades to judge (2 of 30)"}


def test_followable_without_a_log(tmp_path):
    empty = {"live_since_utc": None, "signals": 0, "filled": 0, "fill_rate_pct": None, "closed": 0, "won_pct": None,
             "net_pct": None, "net_r": None, "verdict": None}
    assert setups.build(make_page())["followable"] == empty                              # no record handed in
    assert setups.load_s1(str(tmp_path / "nowhere")) == {"scoreboard": None, "state": None}
    assert setups.build(make_page(), s1=setups.load_s1(str(tmp_path / "nowhere")))["followable"] == empty
    for junk in ("nonsense", {"scoreboard": "x", "state": 7}, {"scoreboard": {"follow": None, "sent": "many"}}):
        f = setups.build(make_page(), s1=junk)["followable"]
        assert (f["signals"], f["filled"], f["closed"], f["won_pct"], f["net_pct"], f["net_r"]) == (0, 0, 0, None, None, None)
    d = tmp_path / "data"
    d.mkdir()
    (d / "signals_log.jsonl").write_text("not json at all\n{\n", encoding="utf-8")      # a log, no signal in it yet
    (d / "signals_state.json").write_text(json.dumps({"version": 1, "live_since": "2026-11-17T04:58:00Z", "seen": {},
                                                      "seq": {}, "open": {}}), encoding="utf-8")
    f = setups.build(make_page(), s1=setups.load_s1(str(d)))["followable"]
    assert f == dict(empty, live_since_utc="2026-11-17T04:58:00Z", verdict="no trades yet")
    (d / "signals_state.json").write_text("{ half a file", encoding="utf-8")            # a state that cannot be read
    assert setups.load_s1(str(d))["state"] is None


def test_followable_log_that_cannot_be_read(tmp_path, monkeypatch):
    d = write_log(tmp_path)
    monkeypatch.setattr(signals, "scoreboard", lambda events: 1 / 0)
    assert setups.load_s1(d)["scoreboard"] is None
    f = setups.build(make_page(), s1=setups.load_s1(d))["followable"]
    assert (f["signals"], f["closed"], f["fill_rate_pct"], f["verdict"]) == (0, 0, None, None)


def _state(follow="WAITING", opened="2026-11-17 02:30", until="2026-11-17 04:15", who="BTCUSDT"):
    return {"version": 1, "live_since": "2026-11-17T01:00:00Z", "seen": {}, "seq": {}, "open": {
        "BTC-1117-01": {"asset": who, "opened_utc": opened, "valid_until_ms": setups._ms(until), "sent_ms": 1,
                        "follow": {"state": follow}},
        "bad": {"asset": "ETHUSDT"}, "worse": None}}


def test_entry_window():
    def btc(state, **kw):
        return by_symbol(setups.build(make_page(), s1={"scoreboard": None, "state": state}, **kw))["BTCUSDT"]
    m = btc(_state())                                                 # waiting, and 03:42 is before 04:15
    assert (m["entry_window_open"], m["entry_valid_until_utc"]) == (True, "2026-11-17T04:15:00Z")
    for state, kw in ((_state(), {"now": "2026-11-17T04:15:00Z"}),    # the window has passed
                      (_state(follow="FILLED"), {}), (_state(follow="NO_FILL"), {}),
                      (_state(opened="2026-11-16 22:00"), {}),         # a signal of an earlier position
                      (_state(who="XAUUSD"), {}), (None, {}), ({"open": "x"}, {})):
        m = btc(state, **kw)
        assert (m["entry_window_open"], m["entry_valid_until_utc"]) == (False, None)
    doc = setups.build(make_page(), s1={"scoreboard": None, "state": _state(who="XAUUSD", opened="2026-11-17 02:30")})
    assert not any(m["entry_window_open"] for m in doc["markets"])    # a FLAT market has no window
    assert doc["followable"]["live_since_utc"] == "2026-11-17T01:00:00Z"


# ------------------------------------------------------------------ valid JSON, the wording rule
def test_no_nan_or_infinity_in_the_output():
    nan, inf = float("nan"), float("inf")
    page = make_page()
    page["assets"]["BTCUSDT"].update(price=nan, edge_pts=inf)
    page["assets"]["ETHUSDT"].update(price=inf)
    page["assets"]["SPX"].update(price=True)                          # not a number either
    v = page["shadows"]["books"]["b_targets"]["assets"]
    v["USDJPY"].update(stop=nan, target_1=-inf, unrealized_usd=nan, realized_usd=inf, trades=nan, equity=nan)
    v["BRENT"].update(entry=nan, target_2="soon")
    page["learning"]["last_7_days"].update(hit_pct=nan, right=inf)
    page["horizon_skill"]["markets"]["BTCUSDT"]["24h"]["d30"][0] = nan
    s1 = {"scoreboard": {"sent": 2, "filled": 1, "fill_rate_pct": nan, "verdict": "no trades yet",
                         "follow": {"n": 1, "won_pct": nan, "net_pct": inf, "net_r": -inf}}, "state": None}
    doc = setups.build(page, s1=s1)
    text = json.dumps(doc, allow_nan=False)                           # raises on NaN / Infinity
    assert "NaN" not in text and "Infinity" not in text and json.loads(text) == doc
    got = by_symbol(doc)
    assert got["BTCUSDT"]["price"] is None and got["BTCUSDT"]["rr_now_t1"] is None and got["BTCUSDT"]["edge_with_position_pts"] is None
    assert got["ETHUSDT"]["price"] is None and got["ETHUSDT"]["stop_dist_now_pct"] is None and got["SPX"]["price"] is None
    assert (got["USDJPY"]["stop"], got["USDJPY"]["target_1"], got["USDJPY"]["unrealized_usd"], got["USDJPY"]["closed"]) == (None, None, None, 0)
    assert got["BRENT"]["entry"] is None and got["BRENT"]["target_2"] is None and got["BRENT"]["unrealized_pct"] is None
    assert doc["learning"]["hit_7d_pct"] is None and doc["learning"]["n_7d"] is None
    assert doc["followable"]["fill_rate_pct"] is None and doc["followable"]["net_r"] is None
    page = make_page()                                                # a tiny loss rounds to 0.0, never to "-0.0"
    page["assets"]["BTCUSDT"]["price"] = 99999.9
    page["shadows"]["books"]["b_targets"]["assets"]["BTCUSDT"]["unrealized_usd"] = -0.001
    m = by_symbol(setups.build(page))["BTCUSDT"]
    assert (m["unrealized_pct"], m["unrealized_usd"]) == (0.0, 0.0) and "-0.0," not in json.dumps(m)


def test_wording_rule_no_model_name_no_free_text_no_edge():
    page = make_page()
    A = page["assets"]["BTCUSDT"]
    A.update(decision="Kronos sees an edge here; b_targets agrees", structure="an edge of the range",
             cards=[{"card": "Kronos candle forecast (live only)", "reading": "kronos says up, a proven edge"}],
             voices=[{"voice": "kr", "title": "Kronos candle forecast"}], raw={"kronos": {"p_up": 0.6}},
             for_long=[["Kronos", 2.0]], question="what edge do you see?", short="Kronos BTC")
    page["version"] = "think15-kronos"
    page["shadows"]["books"]["b_targets"]["assets"]["BTCUSDT"].update(opened_by="FORCED by Kronos", stop_basis="the edge")
    page["scoreboard_all"]["rows"][1]["verdict"] = "ahead: Kronos and b_targets have a proven edge"   # known word, bad tail
    s1 = {"scoreboard": {"sent": 1, "filled": 0, "follow": {"n": 0}, "verdict": "the shadow book b_trail has an edge"},
          "state": None}
    doc = setups.build(page, s1=s1)
    assert "kronos" not in json.dumps(doc).lower()                    # the forecast model is never named, keys included
    assert doc["version"] == "think15-candle_forecast" and by_symbol(doc)["BTCUSDT"]["short"] == "AlphaPrediction AI BTC"
    # a verdict that is not one of the scoreboard's own sentences, whole, is dropped
    assert doc["followable"]["verdict"] is None and doc["book"]["verdict"] is None
    page["scoreboard_all"]["rows"][1]["verdict"] = "ahead: even the low end of the range is positive"
    good = setups.build(page, s1=s1)
    assert good["book"]["verdict"] == "ahead: even the low end of the range is positive"
    for d in (doc, good, setups.build(make_page())):
        texts = strings(d)
        assert not any("kronos" in s.lower() for s in texts)
        assert not any("edge" in s.lower() for s in texts)            # display text never says "edge" (keys may)
        assert not any(w in s.lower() for s in texts for w in OTHER_BOOKS)               # no book names, no research words
        assert not any(w in s for s in texts for w in ("FORCED", "ENTER", "decision", "range of", "pullback", "sentence"))
        allowed = set(ORDER) | {"BTC", "ETH", "GOLD", "SILVER", "S&P 500", "AlphaPrediction AI BTC", "crypto", "metals",
                                "fx", "index", "energy", "LONG", "SHORT", "FLAT", "Setups", setups.NOTE, setups.BOOK_RULE,
                                "think15-candle_forecast", "think15-v5.2.4"}
        for s in texts:                                               # every text is a name, a time or a fixed sentence
            assert s in allowed or setups._verdict(s) is not None or setups._ms(s) is not None, s
    assert "edge_with_position_pts" in json.dumps(setups.build(make_page()))             # the machine name stays


# ------------------------------------------------------------------ the file
def test_write_is_atomic_and_lands_next_to_the_page(tmp_path, monkeypatch):
    live_dir = tmp_path / "live"
    live_dir.mkdir()
    page_path = str(live_dir / "page.json")
    with open(page_path, "w", encoding="utf-8") as fh:
        json.dump(make_page(), fh)
    info = setups.write(page_path)                                    # from the path: next to page.json
    path = str(live_dir / "setups.json")
    assert info == {"markets": 8, "path": path, "web_path": None}
    assert setups.line(info) == "setups: 8 markets -> %s" % path
    with open(path, encoding="utf-8") as fh:
        first = fh.read()
    assert json.loads(first) == setups.build(make_page()) and "NaN" not in first
    assert sorted(os.listdir(str(live_dir))) == ["page.json", "setups.json"]             # no temp file left
    other = tmp_path / "elsewhere" / "deep"                           # from the dict, into a folder that is made
    assert setups.write(make_page(), out_dir=str(other))["path"] == str(other / "setups.json")
    assert os.listdir(str(other)) == ["setups.json"]
    # the rename is the only moment the file changes: a write that dies before it leaves the old file whole
    seen = []
    real = os.replace

    def replace(src, dst):
        seen.append((os.path.basename(src), os.path.basename(dst), os.path.dirname(src) == os.path.dirname(dst)))
        with open(src, encoding="utf-8") as fh:
            json.loads(fh.read())                                     # the temp file is complete before the rename
        raise OSError("the disk said no")
    monkeypatch.setattr(setups.os, "replace", replace)
    changed = make_page()
    changed["version"] = "think15-next"
    with pytest.raises(OSError):
        setups.write(changed, out_dir=str(live_dir))
    monkeypatch.setattr(setups.os, "replace", real)
    assert seen == [("setups.json.tmp", "setups.json", True)]
    with open(path, encoding="utf-8") as fh:
        assert fh.read() == first                                     # the old file, untouched
    assert sorted(os.listdir(str(live_dir))) == ["page.json", "setups.json"]
    assert json.loads(open(str(live_dir / "setups.json"), encoding="utf-8").read())["version"] == "think15-v5.2.4"
    setups.write(changed, out_dir=str(live_dir))
    assert json.load(open(path, encoding="utf-8"))["version"] == "think15-next"
    with pytest.raises(Exception):                                    # a page that is not there, or not JSON
        setups.write(str(live_dir / "no_page.json"))
    (live_dir / "broken.json").write_text("{ half a page", encoding="utf-8")
    with pytest.raises(ValueError):
        setups.write(str(live_dir / "broken.json"))


def test_write_reads_the_s1_record_from_the_data_folder(tmp_path):
    d = write_log(tmp_path)
    info = setups.write(make_page(), out_dir=str(tmp_path / "live"), data_dir=d)
    assert json.load(open(info["path"], encoding="utf-8"))["followable"]["signals"] == 3
    info = setups.write(make_page(), out_dir=str(tmp_path / "live"))  # the default folder (none here): zeros
    assert json.load(open(info["path"], encoding="utf-8"))["followable"]["signals"] == 0


def test_web_copy_only_when_the_variable_is_set(tmp_path, monkeypatch):
    live_dir, web = tmp_path / "live", tmp_path / "www"
    web.mkdir()
    lines = []
    info = setups.write(make_page(), out_dir=str(live_dir), log=lines.append)            # unset: no web copy
    assert info["web_path"] is None and os.listdir(str(web)) == [] and lines == []
    monkeypatch.setenv(setups.WEB_ENV, "   ")                         # blank is unset
    assert setups.write(make_page(), out_dir=str(live_dir), log=lines.append)["web_path"] is None
    monkeypatch.setenv(setups.WEB_ENV, str(web))
    calls = []
    real_chmod, real_replace = os.chmod, os.replace
    monkeypatch.setattr(setups.os, "chmod", lambda p, mode: calls.append(("chmod", p, mode)) or real_chmod(p, mode))
    monkeypatch.setattr(setups.os, "replace", lambda a, b: calls.append(("replace", a, b)) or real_replace(a, b))
    info = setups.write(make_page(), out_dir=str(live_dir), log=lines.append)
    target = str(web / "setups.json")
    assert info == {"markets": 8, "path": str(live_dir / "setups.json"), "web_path": target} and lines == []
    assert setups.line(info) == "setups: 8 markets -> %s (web copy: %s)" % (info["path"], target)
    with open(info["path"], "rb") as a, open(target, "rb") as b:
        assert a.read() == b.read()                                   # the same JSON, byte for byte
    assert os.listdir(str(web)) == ["setups.json"]
    # the local file first; then the web copy: a temp file in the web folder itself, 0644 before the rename
    assert calls == [("replace", info["path"] + ".tmp", info["path"]), ("chmod", target + ".tmp", 0o644),
                     ("replace", target + ".tmp", target)]
    if os.name == "posix":
        assert stat.S_IMODE(os.stat(target).st_mode) == 0o644


def test_web_copy_that_fails_stops_nothing(tmp_path, monkeypatch):
    live_dir = tmp_path / "live"
    not_a_dir = tmp_path / "a_file"
    not_a_dir.write_text("x", encoding="utf-8")
    for bad in (str(tmp_path / "no" / "such" / "folder"), str(not_a_dir)):
        monkeypatch.setenv(setups.WEB_ENV, bad)
        lines = []
        info = setups.write(make_page(), out_dir=str(live_dir), log=lines.append)
        assert info["web_path"] is None and info["markets"] == 8
        assert json.load(open(info["path"], encoding="utf-8"))["schema"] == 1            # the local file is there
        assert len(lines) == 1 and lines[0].startswith("setups: web copy not written (") and "\n" not in lines[0]
        assert setups.line(info) == "setups: 8 markets -> %s" % info["path"]
        assert setups.write(make_page(), out_dir=str(live_dir), log=None)["web_path"] is None          # no log: still fine
        assert setups.write(make_page(), out_dir=str(live_dir), log=lambda *_: 1 / 0)["web_path"] is None
    assert not os.path.exists(str(tmp_path / "no"))                   # the web folder is never made here
    web = tmp_path / "www"                                            # a rename that fails leaves the old web copy whole
    web.mkdir()
    monkeypatch.setenv(setups.WEB_ENV, str(web))
    setups.write(make_page(), out_dir=str(live_dir))
    old = (web / "setups.json").read_bytes()
    real = os.replace

    def replace(src, dst):
        if os.path.dirname(dst) == str(web):
            raise PermissionError("read-only web folder")
        return real(src, dst)
    monkeypatch.setattr(setups.os, "replace", replace)
    changed, lines = make_page(), []
    changed["version"] = "think15-next"
    info = setups.write(changed, out_dir=str(live_dir), log=lines.append)
    assert info["web_path"] is None and lines == ["setups: web copy not written (PermissionError('read-only web folder'))"]
    assert (web / "setups.json").read_bytes() == old and os.listdir(str(web)) == ["setups.json"]
    assert json.load(open(info["path"], encoding="utf-8"))["version"] == "think15-next"


# ------------------------------------------------------------------ the live step's guard
def _step(monkeypatch, tmp_path, with_page=True):
    """The stand-in step of test_step_timing, with a real page file behind export.rewrite_merged."""
    calls, lines = [], []
    timing._stand_ins(monkeypatch, tmp_path, calls)
    page_path = str(tmp_path / "live" / "page.json")
    if with_page:
        os.makedirs(os.path.dirname(page_path))
        with open(page_path, "w", encoding="utf-8") as fh:
            json.dump(make_page(), fh)
    monkeypatch.setattr(export, "rewrite_merged", lambda out_dir: calls.append("rewrite") or page_path)
    return calls, lines, page_path


def _same_step(out, calls, lines, page_path):
    """The step, the page and the push went on as ever."""
    assert out == [{"asset": "AAA"}, {"asset": "BBB"}]
    assert calls.count("push") == 1 and "web push: ok (a stand-in, nothing sent)" in lines
    assert lines[-1].startswith("step done in ") and lines[-1].endswith("page %s" % page_path)
    assert lines[-2].startswith("timing step: ")
    assert json.load(open(page_path, encoding="utf-8")) == make_page()               # the page file is not touched


def test_step_writes_setups_after_the_page_and_before_the_push(monkeypatch, tmp_path):
    calls, lines, page_path = _step(monkeypatch, tmp_path)
    out = live.step(log=lines.append, fetch=True)
    _same_step(out, calls, lines, page_path)
    path = os.path.join(os.path.dirname(page_path), "setups.json")
    mine = [x for x in lines if x.startswith("setups:")]
    assert mine == ["setups: 8 markets -> %s" % path]
    assert lines.index(mine[0]) < lines.index("web push: ok (a stand-in, nothing sent)")
    doc = json.load(open(path, encoding="utf-8"))
    assert doc["schema"] == 1 and [m["symbol"] for m in doc["markets"]] == ORDER
    assert sorted(os.listdir(os.path.dirname(page_path))) == ["page.json", "setups.json"]


def test_an_exception_in_setups_never_breaks_the_step(monkeypatch, tmp_path):
    calls, lines, page_path = _step(monkeypatch, tmp_path)

    def boom(*a, **k):
        raise RuntimeError("setups is broken today")
    monkeypatch.setattr(setups, "write", boom)
    out = live.step(log=lines.append, fetch=True)
    _same_step(out, calls, lines, page_path)
    assert [x for x in lines if x.startswith("setups:")] == ["setups: not written (RuntimeError('setups is broken today'))"]
    assert not os.path.exists(os.path.join(os.path.dirname(page_path), "setups.json"))


def test_a_page_setups_cannot_use_never_breaks_the_step(monkeypatch, tmp_path):
    calls, lines, page_path = _step(monkeypatch, tmp_path)
    page = make_page()
    page["shadows"] = None                                            # the challenger block failed in this step
    with open(page_path, "w", encoding="utf-8") as fh:
        json.dump(page, fh)
    out = live.step(log=lines.append, fetch=True)
    assert out == [{"asset": "AAA"}, {"asset": "BBB"}] and calls.count("push") == 1 and lines[-1].startswith("step done in ")
    mine = [x for x in lines if x.startswith("setups:")]
    assert len(mine) == 1 and mine[0].startswith("setups: not written (ValueError(") and "\n" not in mine[0]
    # no page file at all (the stand-in page of test_step_timing): one line, and the push still goes out
    calls, lines, page_path = _step(monkeypatch, tmp_path / "second", with_page=False)
    out = live.step(log=lines.append, fetch=True)
    assert out == [{"asset": "AAA"}, {"asset": "BBB"}] and calls.count("push") == 1 and lines[-1].startswith("step done in ")
    mine = [x for x in lines if x.startswith("setups:")]
    assert len(mine) == 1 and mine[0].startswith("setups: not written (FileNotFoundError(") and "\n" not in mine[0]


def test_a_failed_web_copy_in_the_step_keeps_the_local_file_and_the_push(monkeypatch, tmp_path):
    calls, lines, page_path = _step(monkeypatch, tmp_path)
    monkeypatch.setenv(setups.WEB_ENV, str(tmp_path / "no_such_web_folder"))
    out = live.step(log=lines.append, fetch=True)
    _same_step(out, calls, lines, page_path)
    path = os.path.join(os.path.dirname(page_path), "setups.json")
    mine = [x for x in lines if x.startswith("setups:")]
    assert len(mine) == 2 and mine[0].startswith("setups: web copy not written (") and mine[1] == "setups: 8 markets -> %s" % path
    assert os.path.exists(path)
    web = tmp_path / "www"                                            # and with a folder that works: both files, one line
    web.mkdir()
    monkeypatch.setenv(setups.WEB_ENV, str(web))
    del lines[:]
    live.step(log=lines.append, fetch=True)
    assert [x for x in lines if x.startswith("setups:")] == ["setups: 8 markets -> %s (web copy: %s)" % (path, str(web / "setups.json"))]
    assert (web / "setups.json").read_bytes() == open(path, "rb").read()


def test_setups_is_on_the_step_clock(monkeypatch, tmp_path):
    calls, lines, page_path = _step(monkeypatch, tmp_path)
    real = setups.write

    def slow(*a, **k):
        import time
        time.sleep(0.12)
        return real(*a, **k)
    monkeypatch.setattr(setups, "write", slow)
    live.step(log=lines.append, fetch=True)
    t = [x for x in lines if x.startswith("timing step: ")]
    assert len(t) == 1 and " | setups 0." in t[0], t


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
