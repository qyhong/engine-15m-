# -*- coding: utf-8 -*-
"""setups.json (engine15/setups.py): one voice per market from the b_targets view of a synthetic page, the record
blocks, the wording rule, valid JSON, the atomic write and its web copy, and the live step's guard; the closes from the
engine's bar files, closed_setups from the book's trade files, and setup_events.json from the S1 log.

    py -3 -m pytest tests/test_setups.py -q

Nothing real runs here: the pages are made up, the files live in pytest's tmp folders, and the live step is the
stand-in step of tests/test_step_timing.py (no network, no source, no book).
"""
import copy
import io
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

TOP = ["generated_utc", "version", "schema", "note", "book", "followable", "learning", "markets", "closed_setups"]
MARKET = ["symbol", "short", "group", "side", "entry", "stop", "target_1", "target_2", "t1_taken", "opened_utc", "price",
          "price_bar_utc", "unrealized_usd", "unrealized_pct", "market_open", "next_open_utc", "edge_with_position_pts",
          "hit_24h_30d_pct", "rr_now_t1", "rr_now_t2", "stop_dist_now_pct", "entry_window_open", "entry_valid_until_utc",
          "closed", "wins", "realized_usd", "closes", "closes_step_min", "closes_end_utc"]
POSITION = ["entry", "stop", "target_1", "target_2", "opened_utc", "unrealized_usd", "unrealized_pct",
            "edge_with_position_pts", "rr_now_t1", "rr_now_t2", "stop_dist_now_pct", "entry_valid_until_utc"]
ORDER = ["BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "USDJPY", "SPX", "WTI", "BRENT"]
OTHER_BOOKS = ("b_targets", "b_trail", "b_be_t1", "h3_flip", "a_pullback", "m_swing", "y_4h", "shadow", "main book",
               "playbook", "challenger")


@pytest.fixture(autouse=True)
def _alone(monkeypatch, tmp_path):
    """No web folder, no real S1 record, no real bar or trade file unless a test asks for one."""
    monkeypatch.delenv(setups.WEB_ENV, raising=False)
    monkeypatch.setattr(setups, "S1_DIR", str(tmp_path / "no_s1_here"))
    monkeypatch.setattr(setups, "BARS_DIR", str(tmp_path / "no_bars_here"))
    monkeypatch.setattr(setups, "TRADES_DIR", str(tmp_path / "no_trades_here"))


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
    assert sorted(os.listdir(str(live_dir))) == ["page.json", "setup_events.json", "setups.json"]   # no temp file left
    other = tmp_path / "elsewhere" / "deep"                           # from the dict, into a folder that is made
    assert setups.write(make_page(), out_dir=str(other))["path"] == str(other / "setups.json")
    assert sorted(os.listdir(str(other))) == ["setup_events.json", "setups.json"]
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
    assert seen == [("setup_events.json.tmp", "setup_events.json", True), ("setups.json.tmp", "setups.json", True)]
    with open(path, encoding="utf-8") as fh:
        assert fh.read() == first                                     # the old file, untouched
    assert sorted(os.listdir(str(live_dir))) == ["page.json", "setup_events.json", "setups.json"]
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
    assert info["web_path"] is None and os.listdir(str(web)) == []
    assert lines == ["setup_events: 0 events -> %s" % str(live_dir / "setup_events.json")]
    del lines[:]
    monkeypatch.setenv(setups.WEB_ENV, "   ")                         # blank is unset
    assert setups.write(make_page(), out_dir=str(live_dir), log=lines.append)["web_path"] is None
    monkeypatch.setenv(setups.WEB_ENV, str(web))
    del lines[:]
    calls = []
    real_chmod, real_replace = os.chmod, os.replace
    monkeypatch.setattr(setups.os, "chmod", lambda p, mode: calls.append(("chmod", p, mode)) or real_chmod(p, mode))
    monkeypatch.setattr(setups.os, "replace", lambda a, b: calls.append(("replace", a, b)) or real_replace(a, b))
    info = setups.write(make_page(), out_dir=str(live_dir), log=lines.append)
    target, events = str(web / "setups.json"), str(web / "setup_events.json")
    assert info == {"markets": 8, "path": str(live_dir / "setups.json"), "web_path": target}
    assert lines == ["setup_events: 0 events -> %s (web copy: %s)" % (str(live_dir / "setup_events.json"), events)]
    assert setups.line(info) == "setups: 8 markets -> %s (web copy: %s)" % (info["path"], target)
    with open(info["path"], "rb") as a, open(target, "rb") as b:
        assert a.read() == b.read()                                   # the same JSON, byte for byte
    assert sorted(os.listdir(str(web))) == ["setup_events.json", "setups.json"]
    # each file: the local file first; then the web copy: a temp file in the web folder itself, 0644 before the rename
    local_ev = str(live_dir / "setup_events.json")
    assert calls == [("replace", local_ev + ".tmp", local_ev), ("chmod", events + ".tmp", 0o644),
                     ("replace", events + ".tmp", events),
                     ("replace", info["path"] + ".tmp", info["path"]), ("chmod", target + ".tmp", 0o644),
                     ("replace", target + ".tmp", target)]
    with open(local_ev, "rb") as a, open(events, "rb") as b:
        assert a.read() == b.read()
    if os.name == "posix":
        assert stat.S_IMODE(os.stat(target).st_mode) == 0o644 and stat.S_IMODE(os.stat(events).st_mode) == 0o644


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
        mine = [x for x in lines if x.startswith("setups:")]
        assert len(mine) == 1 and mine[0].startswith("setups: web copy not written (") and "\n" not in mine[0]
        ev = [x for x in lines if x.startswith("setup_events:")]      # the events file: its own two lines
        assert len(ev) == 2 and ev[0].startswith("setup_events: web copy not written (") and ev[1].startswith(
            "setup_events: 0 events -> ") and len(lines) == 3
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
    assert info["web_path"] is None
    assert [x for x in lines if x.startswith("setups:")] == ["setups: web copy not written (PermissionError('read-only web folder'))"]
    assert (web / "setups.json").read_bytes() == old and sorted(os.listdir(str(web))) == ["setup_events.json", "setups.json"]
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
    assert sorted(os.listdir(os.path.dirname(page_path))) == ["page.json", "setup_events.json", "setups.json"]
    ev = [x for x in lines if x.startswith("setup_events:")]
    assert ev == ["setup_events: 0 events -> %s" % os.path.join(os.path.dirname(page_path), "setup_events.json")]
    assert lines.index(ev[0]) < lines.index(mine[0])


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


# ------------------------------------------------------------------ closes (the engine's own bars)
BAR = 900000
HEADER = "ts_ms,open,high,low,close,volume,taker_buy\n"


def bar_lines(last_open, n, base, step=1.0):
    """n bar lines ending with the bar that opens at last_open ('YYYY-MM-DD HH:MM'); close = base + k * step."""
    end = setups._ms(last_open)
    out = []
    for k in range(n):
        ts = end - (n - 1 - k) * BAR
        c = base + k * step
        out.append("%d,%r,%r,%r,%r,10.0,5.0\n" % (ts, c, c + 1, c - 1, c))
    return out


def write_bars(d, sym, last_open, n, base, step=1.0, header=True):
    os.makedirs(str(d), exist_ok=True)
    path = os.path.join(str(d), "%s_15m.csv" % sym.lower())
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write((HEADER if header else "") + "".join(bar_lines(last_open, n, base, step)))
    return path


def all_bars(d):
    """Bar files for the eight markets of make_page, each holding bars beyond the page's price bar."""
    write_bars(d, "BTCUSDT", "2026-11-17 03:30", 300, 100000.0, 1.234567)      # two bars newer than the page
    write_bars(d, "ETHUSDT", "2026-11-17 03:00", 50, 1800.0)                   # fewer than 96 bars
    write_bars(d, "XAUUSD", "2026-11-17 03:15", 150, 3800.123456, 0.5)         # fill_delay 1: one bar newer
    write_bars(d, "XAGUSD", "2026-11-17 02:45", 150, 47.123456, 0.001)         # fill_delay 1: the file is behind the page
    write_bars(d, "USDJPY", "2026-11-17 03:15", 150, 159.123456, 0.001)
    write_bars(d, "SPX", "2026-11-16 20:45", 150, 7400.0, 0.25)                # shut: the last bar there is
    write_bars(d, "WTI", "2026-11-17 03:30", 150, 85.0, 0.01)                  # no page time: the energy close
    write_bars(d, "BRENT", "2026-11-17 03:00", 150, 93.0, 0.01)


def built_with_bars(d, page=None, prev=None):
    syms = ORDER
    bars = dict((a, setups.read_closes(setups.bar_path(str(d), a))) for a in syms)
    return setups.build(page or make_page(), bars=bars, prev=prev)


def test_closes_window_and_end(tmp_path):
    all_bars(tmp_path / "bars")
    got = by_symbol(built_with_bars(tmp_path / "bars"))
    m = got["BTCUSDT"]                                                # the page's price bar opens 03:00, closes 03:15
    assert m["closes_step_min"] == 15 and len(m["closes"]) == 96
    assert m["closes_end_utc"] == m["price_bar_utc"] == "2026-11-17T03:15:00Z"
    k = 300 - 3                                                       # the bar opening 03:00 is the 298th of 300
    assert m["closes"][-1] == round(100000.0 + k * 1.234567, 2) and m["closes"][0] == round(100000.0 + (k - 95) * 1.234567, 2)
    assert m["closes"] == sorted(m["closes"])                         # oldest first
    m = got["ETHUSDT"]
    assert len(m["closes"]) == 50 and m["closes"][-1] == 1849.0 and m["closes_end_utc"] == "2026-11-17T03:15:00Z"
    m = got["XAUUSD"]                                                 # one bar behind: the same bar as the page's price
    assert m["closes_end_utc"] == "2026-11-17T03:15:00Z" and m["closes"][-1] == round(3800.123456 + 148 * 0.5, 2)
    m = got["XAGUSD"]                                                 # the file holds less than the page: its last bar
    assert m["closes_end_utc"] == "2026-11-17T03:00:00Z" and m["closes"][-1] == round(47.123456 + 149 * 0.001, 5)
    m = got["USDJPY"]                                                 # page time 03:30: the bar that opens 03:15
    assert m["closes_end_utc"] == "2026-11-17T03:30:00Z" and m["closes"][-1] == round(159.123456 + 149 * 0.001, 3)
    m = got["SPX"]
    assert m["closes_end_utc"] == m["price_bar_utc"] == "2026-11-16T21:00:00Z" and len(m["closes"]) == 96
    m = got["WTI"]                                                    # no asset time: the energy books' close
    assert m["closes_end_utc"] == "2026-11-17T03:15:00Z" and m["closes"][-1] == round(85.0 + 147 * 0.01, 5)
    assert all(isinstance(x, float) for mk in got.values() for x in mk["closes"])
    # no price bar at all (no time anywhere): the last bars there are
    page = make_page()
    page["assets"]["WTI"] = {"short": "WTI"}
    page["shadows"]["markets"]["energy"].pop("as_of_utc")
    m = by_symbol(built_with_bars(tmp_path / "bars", page))["WTI"]
    assert m["price_bar_utc"] is None and m["closes_end_utc"] == "2026-11-17T03:45:00Z" and len(m["closes"]) == 96


def test_metals_and_energy_step_one_bar_behind(tmp_path):
    """fill_delay 1 (config): the page's price is the bar the engine has, one bar behind the clock; the closes end
    there too, never on a newer bar the file may already hold."""
    from engine15.config import CFG
    assert all(CFG["fill_delay"].get(a) == 1 for a in ("XAUUSD", "XAGUSD", "WTI", "BRENT"))
    d = tmp_path / "bars"
    page = make_page()
    for a in ("XAUUSD", "BRENT"):
        page["assets"][a]["time"] = "2026-11-17 03:00"               # the page one bar behind the crypto markets
        write_bars(d, a, "2026-11-17 03:15", 120, 50.0, 0.25)        # the file already holds two newer bars
    got = by_symbol(setups.build(page, bars=dict((a, setups.read_closes(setups.bar_path(str(d), a)))
                                                 for a in ("XAUUSD", "BRENT"))))
    for a in ("XAUUSD", "BRENT"):
        assert got[a]["price_bar_utc"] == got[a]["closes_end_utc"] == "2026-11-17T03:00:00Z"
        assert got[a]["closes"][-1] == 50.0 + 117 * 0.25 and len(got[a]["closes"]) == 96
    assert got["BTCUSDT"]["closes"] is None and got["BTCUSDT"]["closes_end_utc"] is None    # no file read: null


def test_read_closes_reads_only_the_tail_and_trusts_no_garbled_read(tmp_path, monkeypatch):
    d = tmp_path / "bars"
    path = write_bars(d, "BTCUSDT", "2026-11-17 03:00", 5000, 100.0, 0.001)
    assert os.path.getsize(path) > 4 * setups.TAIL_BYTES
    rows = setups.read_closes(path)
    assert 96 <= len(rows) <= setups.TAIL_LINES and rows[-1][0] == setups._ms("2026-11-17 03:00")
    assert all(b[0] - a[0] == BAR for a, b in zip(rows, rows[1:]))
    seen, real_open = [], io.open

    class Spy(object):
        def __init__(self, fh):
            self.fh = fh

        def __enter__(self):
            return self

        def __exit__(self, *a):
            self.fh.close()

        def seek(self, n):
            seen.append(("seek", n))
            return self.fh.seek(n)

        def read(self, n=-1):
            data = self.fh.read(n)
            seen.append(("read", len(data)))
            return data
    monkeypatch.setattr(setups.io, "open", lambda p, mode="r", *a, **k: Spy(real_open(p, mode, *a, **k)))
    assert setups.read_closes(path) == rows
    monkeypatch.undo()
    size = os.path.getsize(path)
    assert seen == [("seek", size - setups.TAIL_BYTES), ("read", setups.TAIL_BYTES)]     # the tail only, one read
    with open(path, "a", encoding="utf-8") as fh:                     # a line still being written: left out
        fh.write("1794886200000,100.0,10")
    assert setups.read_closes(path)[-1] == rows[-1]
    for junk in ("", "{\n \"started_utc\": \"2026-11-10T13:26:48Z\",\n \"last_session_ms\": 1794884400000\n}\n",
                 HEADER, HEADER + "1794884400000,1,2,3\n", HEADER + "1794884400000,1,2,0.5,nan,1,1\n",
                 HEADER + "1794884400001,1,2,0.5,1,1,1\n",                                     # not on a 15-minute open
                 HEADER + "1794884400000,1,2,0.5,1,1,1\n1794884400000,1,2,0.5,1,1,1\n"):       # not increasing
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(junk)
        assert setups.read_closes(path) is None, junk
    lines = bar_lines("2026-11-17 03:00", 300, 100.0)                  # one bad line in the middle of the tail
    lines[250] = "1794,abc,1,1,1,1,1\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(HEADER + "".join(lines))
    assert setups.read_closes(path) is None
    assert setups.read_closes(str(d / "no_such_15m.csv")) is None
    write_bars(d, "ETHUSDT", "2026-11-17 03:00", 3, 1.0, header=False)                       # no header: fine
    assert [c for _t, c in setups.read_closes(setups.bar_path(str(d), "ETHUSDT"))] == [1.0, 2.0, 3.0]
    with open(path, "wb") as fh:                                      # Windows line ends
        fh.write("".join(bar_lines("2026-11-17 03:00", 4, 7.0)).replace("\n", "\r\n").encode())
    assert [c for _t, c in setups.read_closes(path)] == [7.0, 8.0, 9.0, 10.0]


def test_a_bar_file_that_cannot_be_read_keeps_the_previous_closes(tmp_path):
    d, live_dir = tmp_path / "bars", tmp_path / "live"
    all_bars(d)
    first = setups.write(make_page(), out_dir=str(live_dir), bars_dir=str(d))
    before = by_symbol(json.load(open(first["path"], encoding="utf-8")))
    assert before["BTCUSDT"]["closes"] and before["XAUUSD"]["closes"]
    open(setups.bar_path(str(d), "BTCUSDT"), "w").close()             # empty
    with open(setups.bar_path(str(d), "XAUUSD"), "w", encoding="utf-8") as fh:
        fh.write('{\n "started_utc": "2026-11-10T13:26:48Z"\n}\n')    # not a bar file at all (the archive's gold file)
    os.remove(setups.bar_path(str(d), "SPX"))                          # missing
    write_bars(d, "ETHUSDT", "2026-11-17 03:00", 60, 2000.0)          # read fine: new closes
    second = setups.write(make_page(), out_dir=str(live_dir), bars_dir=str(d))
    after = by_symbol(json.load(open(second["path"], encoding="utf-8")))
    for a in ("BTCUSDT", "XAUUSD", "SPX"):
        assert after[a]["closes"] == before[a]["closes"] and after[a]["closes_end_utc"] == before[a]["closes_end_utc"]
    assert after["ETHUSDT"]["closes"][-1] == 2059.0 and len(after["ETHUSDT"]["closes"]) == 60
    # no previous file (or one that cannot be read): null
    for prev in (None, "{ half a file"):
        other = tmp_path / ("fresh%d" % (prev is None))
        other.mkdir()
        if prev:
            (other / "setups.json").write_text(prev, encoding="utf-8")
        got = by_symbol(json.load(open(setups.write(make_page(), out_dir=str(other), bars_dir=str(d))["path"],
                                       encoding="utf-8")))
        assert got["BTCUSDT"]["closes"] is None and got["XAUUSD"]["closes_end_utc"] is None
        assert got["XAUUSD"]["closes_step_min"] == 15 and got["ETHUSDT"]["closes"][-1] == 2059.0
    # a previous file with junk in its closes is not used
    junk = {"markets": [{"symbol": "BTCUSDT", "closes": [1.0, "x"], "closes_end_utc": "2026-11-17T03:15:00Z"},
                        {"symbol": "XAUUSD", "closes": "many"}, "nonsense"]}
    got = by_symbol(setups.build(make_page(), bars={}, prev=junk))
    assert got["BTCUSDT"]["closes"] is None and got["XAUUSD"]["closes"] is None
    got = by_symbol(setups.build(make_page(), bars={}, prev={"markets": [{"symbol": "SPX", "closes": [7400.123456]}]}))
    assert got["SPX"]["closes"] == [7400.12] and got["SPX"]["closes_end_utc"] is None


# ------------------------------------------------------------------ closed_setups (the book's trade files)
TCOLS = ["t_in_ms", "t_out_ms", "side", "p_in", "p_out", "why_in", "why_out", "pnl_pct", "equity", "qty", "pnl_usd",
         "fees_usd", "stop0", "risk_usd", "r_mult", "target_1", "target_2", "time_in", "time_out"]


def trow(t_in, t_out, side, p_in, p_out, why, pct, usd=12.3456, stop0=None, r=0.98765, t1=None, t2=None):
    t_in, t_out = setups._ms(t_in), setups._ms(t_out)
    return [t_in, t_out, side, p_in, p_out, "ENTER", why, pct, 10000.0, 1.0, usd, 1.0,
            stop0 if stop0 is not None else p_in * (1 - 0.01 * side), 100.0, r,
            t1 if t1 is not None else p_in * (1 + 0.01 * side), t2 if t2 is not None else p_in * (1 + 0.02 * side),
            "x", "y"]


def write_trades(d, sym, rows, book="b_targets", extra=""):
    os.makedirs(str(d), exist_ok=True)
    path = os.path.join(str(d), "shadow_trades_%s_%s.csv" % (book, sym))
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(",".join(TCOLS) + "\n")
        for r in rows:
            fh.write((r if isinstance(r, str) else ",".join(repr(x) if isinstance(x, float) else str(x) for x in r)) + "\n")
        fh.write(extra)
    return path


def test_why_out_codes():
    assert setups.why_code("T1+T2") == "TARGET_2" and setups.why_code("STOP") == "STOP"
    assert setups.why_code("T1+STOP_BE") == "T1_THEN_ENTRY"
    assert setups.why_code("FLIP") == "FLIP" and setups.why_code("T1+FLIP") == "T1_THEN_FLIP"
    assert setups.why_code("FLIP_MKT") == "FLIP" and setups.why_code("T1+FLIP_LMT") == "T1_THEN_FLIP"
    assert setups.why_code("STEP_ASIDE") == "EXIT" and setups.why_code("T1+STEP_ASIDE") == "T1_THEN_EXIT"
    for w in ("TRAIL", "T1+TRAIL", "STOP_BE", "T1+STOP", "T2", "ENTER", "FORCED", "", None, "stop", "T1+", "T1+T2+X"):
        assert setups.why_code(w) == "OTHER", w


def test_closed_setups_order_limit_mapping(tmp_path):
    d = tmp_path / "trades"
    # BTC: 20 trades one hour apart, the why_out words in turn; ETH: 20 more, half an hour later each
    words = ["T1+T2", "STOP", "T1+STOP_BE", "FLIP", "T1+FLIP", "STEP_ASIDE", "T1+STEP_ASIDE", "TRAIL", "T1+TRAIL"]

    def hour(h, m=0):
        return setups._iso(setups._ms("2026-11-01 00:00") + (h * 60 + m) * 60000)
    btc = [trow(hour(h), hour(h, 45), 1 if h % 2 else -1, 100000.0 + h, 100100.123456 + h, words[h % len(words)], 0.123456 * h)
           for h in range(20)]
    eth = [trow(hour(h, 15), hour(h, 30 + 60), -1, 2000.0, 1990.0, "T1+T2", 1.0) for h in range(20)]
    write_trades(d, "BTCUSDT", btc)
    write_trades(d, "ETHUSDT", eth)
    rows = setups.read_trades(str(d))
    assert len(rows) == 40 and rows[0][0] == "BTCUSDT"
    cs = setups.build(make_page(), trades=rows)["closed_setups"]
    assert len(cs) == 30
    assert [c["closed_utc"] for c in cs] == sorted([c["closed_utc"] for c in cs], reverse=True)       # newest first
    assert list(cs[0]) == ["symbol", "side", "opened_utc", "closed_utc", "entry", "exit", "stop", "target_1", "target_2",
                           "t1_taken", "why_out", "result_pct", "result_usd", "r"]
    assert cs[0]["symbol"] == "ETHUSDT" and cs[0]["closed_utc"] == hour(20, 30)
    assert setups._closed_setups(rows + [("X", "junk"), "junk", None]) == cs
    by = dict(((c["symbol"], c["opened_utc"]), c) for c in (setups._closed_trade(a, r) for a, r in rows))
    expect = {"T1+T2": ("TARGET_2", True), "STOP": ("STOP", False), "T1+STOP_BE": ("T1_THEN_ENTRY", True),
              "FLIP": ("FLIP", False), "T1+FLIP": ("T1_THEN_FLIP", True), "STEP_ASIDE": ("EXIT", False),
              "T1+STEP_ASIDE": ("T1_THEN_EXIT", True), "TRAIL": ("OTHER", False), "T1+TRAIL": ("OTHER", True)}
    for h in range(9):
        c = by[("BTCUSDT", hour(h))]
        assert (c["why_out"], c["t1_taken"]) == expect[words[h]], words[h]
    c = by[("BTCUSDT", hour(3))]
    assert c["side"] == "LONG" and c["entry"] == 100003.0 and c["exit"] == 100103.12 and c["closed_utc"] == hour(3, 45)
    assert c["result_pct"] == 0.37 and c["result_usd"] == 12.35 and c["r"] == 0.99
    assert c["stop"] == 99002.97 and c["target_1"] == 101003.03 and c["target_2"] == 102003.06
    assert by[("BTCUSDT", hour(2))]["side"] == "SHORT"


def test_closed_setups_two_part_exit_and_garbled_rows(tmp_path):
    """p_out is already the average exit when Target 1 took half (shadows.run: (q1 * T1 + q2 * exit) / (q1 + q2),
    q1 = q2 = half): it is shown as it is."""
    d = tmp_path / "trades"
    t1, t2 = 71954.54248, 70971.58762
    rows = [trow("2026-11-11 06:45", "2026-11-13 00:30", -1, 73659.98, (t1 + t2) / 2, "T1+T2", 2.785, t1=t1, t2=t2),
            trow("2026-11-14 15:30", "2026-11-15 03:00", -1, 65214.46, (62915.93844 + 65214.46) / 2, "T1+STOP_BE", 1.56,
                 t1=62915.93844, t2=61766.67766),
            "1794379500000,1794529800000,-1,73659.98",                                    # cut short
            "1794379500000,1794529800000,-1,abc,1,ENTER,STOP,1,1,1,1,1,1,1,1,1,1,x,y",     # a word for a price
            "1794379500000,,-1,100,101,ENTER,STOP,1,1,1,1,1,1,1,1,1,1,x,y",                 # not closed (no exit time)
            "1794379500000,1794529800000,0,100,101,ENTER,STOP,1,1,1,1,1,1,1,1,1,1,x,y",     # no side
            "1794379500000,1794529800000,1,100,101,ENTER,STOP,,1,1,1,1,1,1,1,1,1,x,y",      # no result
            "1794529800000,1794379500000,1,100,101,ENTER,STOP,1,1,1,1,1,1,1,1,1,1,x,y",     # out before in
            "1794379500000,1794529800000,1,100,101,ENTER,STOP,1,1,1,1,1,1,1,1,1,1,x,y,extra",   # one field too many
            "1794379500000,1794529800000,1,nan,101,ENTER,STOP,1,1,1,1,1,1,1,1,1,1,x,y"]
    write_trades(d, "BTCUSDT", rows, extra="1794379500000,17945")      # a last line cut while written
    cs = setups.build(make_page(), trades=setups.read_trades(str(d)))["closed_setups"]
    assert len(cs) == 2
    assert cs[1]["exit"] == round((t1 + t2) / 2, 2) and cs[1]["t1_taken"] is True and cs[1]["why_out"] == "TARGET_2"
    assert cs[0]["exit"] == round((62915.93844 + 65214.46) / 2, 2) and cs[0]["why_out"] == "T1_THEN_ENTRY"
    # a row written twice (a step re-run) counts once
    write_trades(d, "BTCUSDT", rows[:2] + rows[:1])
    assert len(setups.build(make_page(), trades=setups.read_trades(str(d)))["closed_setups"]) == 2
    # other books, other names and a file too large are not read
    write_trades(d, "BTCUSDT", rows[:1], book="b_trail")
    write_trades(d, "btc", rows[:1])
    write_trades(d, "ETHUSDT", rows[:2] * 5)
    assert sorted(set(s for s, _r in setups.read_trades(str(d)))) == ["BTCUSDT", "ETHUSDT"]
    small = os.path.getsize(os.path.join(str(d), "shadow_trades_b_targets_BTCUSDT.csv"))
    assert os.path.getsize(os.path.join(str(d), "shadow_trades_b_targets_ETHUSDT.csv")) > small
    old = setups.TRADES_MAX_BYTES
    try:
        setups.TRADES_MAX_BYTES = small
        assert sorted(set(s for s, _r in setups.read_trades(str(d)))) == ["BTCUSDT"]
    finally:
        setups.TRADES_MAX_BYTES = old
    assert setups.TRADES_MAX_BYTES == 5 * 1024 * 1024
    assert setups.read_trades(str(tmp_path / "nowhere")) == [] and setups.build(make_page())["closed_setups"] == []


def test_write_reads_the_trade_files(tmp_path):
    d = tmp_path / "trades"
    write_trades(d, "XAUUSD", [trow("2026-11-12 10:15", "2026-11-16 05:45", -1, 3951.6, 3872.1145592483376, "T1+T2",
                                    1.9718771596267997, usd=334.94500863303784, r=1.6054859383373836)])
    info = setups.write(make_page(), out_dir=str(tmp_path / "live"), trades_dir=str(d))
    cs = json.load(open(info["path"], encoding="utf-8"))["closed_setups"]
    assert cs == [{"symbol": "XAUUSD", "side": "SHORT", "opened_utc": "2026-11-12T10:15:00Z",
                   "closed_utc": "2026-11-16T05:45:00Z", "entry": 3951.6, "exit": 3872.11, "stop": 3991.12,
                   "target_1": 3912.08, "target_2": 3872.57, "t1_taken": True, "why_out": "TARGET_2", "result_pct": 1.97,
                   "result_usd": 334.95, "r": 1.61}]


# ------------------------------------------------------------------ setup_events.json
def ev(sid, key, kind, t, **kw):
    return dict({"t": t, "id": sid, "k": key, "ev": kind, "asset": key.split("|")[0], "delivered": True}, **kw)


def event_log():
    """Every kind signals.py logs: start, seen_not_signalled, signal, filled, t1, model_exit, closed (t2, stop,
    stop_be, model), no_fill (window, stop, target, model; one without a bar), book_closed."""
    a, b, c, d = "BTCUSDT|2026-11-17 05:00", "XAUUSD|2026-11-17 06:00", "SPX|2026-11-17 15:00", "ETHUSDT|2026-11-17 07:00"
    e, f, g, h = "WTI|2026-11-17 08:00", "BRENT|2026-11-17 08:30", "USDJPY|2026-11-17 09:00", "XAGUSD|2026-11-17 09:30"
    i, j = "BTCUSDT|2026-11-17 10:00", "ETHUSDT|2026-11-17 11:00"

    def sig(sid, key, t, side, entry, stop, t1, t2, until):
        return ev(sid, key, "signal", t, side=side, entry=entry, stop=stop, t1=t1, t2=t2, fee=0.0005, opened_utc=key[-16:],
                  bar_a_utc=t[:14] + "00:00Z", valid_until_utc=until, msg_id=7)
    return [
        {"t": "2026-11-17T04:58:00Z", "k": "start", "ev": "start", "live_since": "2026-11-17T04:58:00Z"},
        {"t": "2026-11-17T04:58:00Z", "k": "SPX|2026-11-16 20:00", "ev": "seen_not_signalled", "asset": "SPX",
         "why": "already open when the preview started"},
        sig("BTC-1117-01", a, "2026-11-17T05:16:00Z", 1, 100000.123456, 99000.0, 101000.0, 102000.0, "2026-11-17T06:30:00Z"),
        ev("BTC-1117-01", a, "filled", "2026-11-17T05:46:00Z", px=100000.123456, bar_utc="2026-11-17T05:30:00Z"),
        ev("BTC-1117-01", a, "t1", "2026-11-17T07:01:00Z", px=101000.0, bar_utc="2026-11-17T06:45:00Z"),
        ev("BTC-1117-01", a, "closed", "2026-11-17T09:01:00Z", why="t2", px=102000.0, bar_utc="2026-11-17T08:45:00Z",
           pct=1.4567, usd=145.67, r=1.4321, avg_exit=101500.0),
        ev("BTC-1117-01", a, "book_closed", "2026-11-17T09:16:00Z", known=True, why_out="T1+T2", pct=1.5, r=1.5, usd=150.0),
        sig("XAU-1117-01", b, "2026-11-17T06:16:00Z", -1, 4000.0, 4040.0, 3960.0, 3920.0, "2026-11-17T07:30:00Z"),
        ev("XAU-1117-01", b, "filled", "2026-11-17T06:31:00Z", px=4000.0, bar_utc="2026-11-17T06:15:00Z"),
        ev("XAU-1117-01", b, "closed", "2026-11-17T08:01:00Z", why="stop", px=4040.0, bar_utc="2026-11-17T07:45:00Z",
           pct=-1.05, usd=-105.0, r=-1.0),
        sig("SPX-1117-01", c, "2026-11-17T15:16:00Z", 1, 7400.0, 7350.0, 7450.0, 7500.0, "2026-11-17T16:30:00Z"),
        ev("SPX-1117-01", c, "no_fill", "2026-11-17T16:31:00Z", reason="window", bar_utc="2026-11-17T16:30:00Z"),
        sig("ETH-1117-01", d, "2026-11-17T07:16:00Z", -1, 2000.0, 2050.0, 1950.0, 1900.0, "2026-11-17T08:30:00Z"),
        ev("ETH-1117-01", d, "filled", "2026-11-17T07:31:00Z", px=2000.0, bar_utc="2026-11-17T07:15:00Z"),
        ev("ETH-1117-01", d, "t1", "2026-11-17T08:01:00Z", px=1950.0, bar_utc="2026-11-17T07:45:00Z"),
        ev("ETH-1117-01", d, "closed", "2026-11-17T08:01:00Z", why="stop_be", px=2000.0, bar_utc="2026-11-17T07:45:00Z",
           pct=1.2, usd=120.0, r=0.5),
        sig("WTI-1117-01", e, "2026-11-17T08:16:00Z", 1, 85.0, 84.0, 86.0, 87.0, "2026-11-17T09:30:00Z"),
        ev("WTI-1117-01", e, "no_fill", "2026-11-17T08:31:00Z", reason="stop", bar_utc="2026-11-17T08:15:00Z"),
        sig("BRN-1117-01", f, "2026-11-17T08:46:00Z", 1, 95.0, 94.0, 96.0, 97.0, "2026-11-17T10:00:00Z"),
        ev("BRN-1117-01", f, "no_fill", "2026-11-17T09:01:00Z", reason="target", bar_utc="2026-11-17T08:45:00Z"),
        sig("JPY-1117-01", g, "2026-11-17T09:16:00Z", 1, 159.5, 159.0, 160.0, 160.5, "2026-11-17T10:30:00Z"),
        ev("JPY-1117-01", g, "book_closed", "2026-11-17T09:31:00Z", known=True, why_out="FLIP", pct=-0.1, r=-0.2, usd=-10.0),
        ev("JPY-1117-01", g, "no_fill", "2026-11-17T09:31:00Z", reason="model"),                 # no bar: after the bars
        sig("XAG-1117-01", h, "2026-11-17T09:46:00Z", -1, 47.5, 48.0, 47.0, 46.5, "2026-11-17T11:00:00Z"),
        sig("BTC-1117-02", i, "2026-11-17T10:16:00Z", 1, 101000.0, 100000.0, 102000.0, 103000.0, "2026-11-17T11:30:00Z"),
        ev("BTC-1117-02", i, "filled", "2026-11-17T10:46:00Z", px=101000.0, bar_utc="2026-11-17T10:30:00Z"),
        ev("BTC-1117-02", i, "book_closed", "2026-11-17T11:16:00Z", known=True, why_out="STEP_ASIDE", pct=0.1, r=0.1, usd=10.0),
        ev("BTC-1117-02", i, "model_exit", "2026-11-17T11:16:00Z", alert_bar_utc="2026-11-17T11:15:00Z"),
        ev("BTC-1117-02", i, "closed", "2026-11-17T11:31:00Z", why="model", px=101200.0, bar_utc="2026-11-17T11:30:00Z",
           pct=0.1, usd=10.0, r=0.1),
        sig("ETH-1117-02", j, "2026-11-17T11:16:00Z", 1, 2010.0, 2000.0, 2015.0, 2020.0, "2026-11-17T12:30:00Z"),
        ev("ETH-1117-02", j, "no_fill", "2026-11-17T11:16:00Z", reason="target"),                # Target 1 before the alert
    ]


EVENT_KEYS = ["id", "signal_id", "type", "symbol", "side", "utc", "bar_utc", "entry", "stop", "target_1", "target_2", "price",
              "entry_valid_until_utc", "result_pct", "r", "reason_code"]


def test_events_mapping_for_every_kind():
    doc = setups.build_events(event_log(), generated_utc="2026-11-17T12:00:00Z")
    assert list(doc) == ["generated_utc", "schema", "live_since_utc", "events"]
    assert (doc["generated_utc"], doc["schema"], doc["live_since_utc"]) == ("2026-11-17T12:00:00Z", 1, "2026-11-17T04:58:00Z")
    evs = doc["events"]
    assert all(list(e) == EVENT_KEYS for e in evs)
    assert len(evs) == 25                                             # 31 lines - start, seen, 3 book_closed, model_exit
    by = dict((e["id"], e) for e in evs)
    e = by["BTC-1117-01:NEW_SETUP"]
    assert e == {"id": "BTC-1117-01:NEW_SETUP", "signal_id": "BTC-1117-01", "type": "NEW_SETUP", "symbol": "BTCUSDT",
                 "side": "LONG", "utc": "2026-11-17T05:16:00Z", "bar_utc": None, "entry": 100000.12, "stop": 99000.0,
                 "target_1": 101000.0, "target_2": 102000.0, "price": None, "entry_valid_until_utc": "2026-11-17T06:30:00Z",
                 "result_pct": None, "r": None, "reason_code": None}
    e = by["BTC-1117-01:ENTRY_FILLED"]
    assert (e["utc"], e["bar_utc"], e["price"], e["entry"], e["side"]) == ("2026-11-17T05:46:00Z", "2026-11-17T05:30:00Z",
                                                                           100000.12, 100000.12, "LONG")
    assert e["entry_valid_until_utc"] is None and e["result_pct"] is None
    assert (by["BTC-1117-01:TARGET_1"]["price"], by["BTC-1117-01:TARGET_1"]["utc"]) == (101000.0, "2026-11-17T07:01:00Z")
    e = by["BTC-1117-01:CLOSED"]
    assert (e["reason_code"], e["result_pct"], e["r"], e["price"], e["bar_utc"]) == ("TARGET_2", 1.46, 1.43, 102000.0,
                                                                                    "2026-11-17T08:45:00Z")
    assert by["XAU-1117-01:CLOSED"]["reason_code"] == "STOP" and by["XAU-1117-01:CLOSED"]["side"] == "SHORT"
    assert by["XAU-1117-01:CLOSED"]["r"] == -1.0 and by["XAU-1117-01:CLOSED"]["result_pct"] == -1.05
    assert by["ETH-1117-01:CLOSED"]["reason_code"] == "T1_THEN_ENTRY"
    assert by["BTC-1117-02:CLOSED"]["reason_code"] == "MODEL_CLOSED" and by["BTC-1117-02:CLOSED"]["utc"] == "2026-11-17T11:31:00Z"
    nf = dict((e["signal_id"], e) for e in evs if e["type"] == "NO_FILL")
    assert dict((k, v["reason_code"]) for k, v in nf.items()) == {"SPX-1117-01": "WINDOW", "WTI-1117-01": "STOP_FIRST",
                                                                  "BRN-1117-01": "TARGET_FIRST", "JPY-1117-01": "MODEL_CLOSED",
                                                                  "ETH-1117-02": "TARGET_FIRST"}
    assert nf["JPY-1117-01"]["bar_utc"] is None and nf["JPY-1117-01"]["utc"] == "2026-11-17T09:31:00Z"
    assert all(v["result_pct"] is None and v["r"] is None and v["price"] is None for v in nf.values())
    assert set(e["type"] for e in evs) == {"NEW_SETUP", "ENTRY_FILLED", "NO_FILL", "TARGET_1", "CLOSED"}
    assert not any(e["type"] in ("MODEL_EXIT",) or "book" in e["id"].lower() for e in evs)
    # a waiting signal (XAG) is only its NEW_SETUP; a signal line that was lost leaves its events with no levels
    assert [e["type"] for e in evs if e["signal_id"] == "XAG-1117-01"] == ["NEW_SETUP"]
    lost = [x for x in event_log() if not (x["ev"] == "signal" and x.get("id") == "XAU-1117-01")]
    e = dict((x["id"], x) for x in setups.build_events(lost)["events"])["XAU-1117-01:CLOSED"]
    assert (e["symbol"], e["side"], e["entry"], e["reason_code"]) == ("XAUUSD", None, None, "STOP")
    # an unknown reason is no code, not a sentence
    odd = event_log() + [ev("BTC-1117-09", "BTCUSDT|2026-11-17 12:00", "no_fill", "2026-11-17T12:31:00Z", reason="later")]
    got = dict((x["id"], x) for x in setups.build_events(odd)["events"])["BTC-1117-09:NO_FILL"]
    assert got["reason_code"] is None and got["type"] == "NO_FILL"


def test_events_newest_first_and_utc_is_the_log_time():
    evs = setups.build_events(event_log())["events"]
    keys = [(e["utc"]) for e in evs]
    assert keys == sorted(keys, reverse=True)
    assert [e["id"] for e in evs[:5]] == ["SPX-1117-01:NO_FILL", "SPX-1117-01:NEW_SETUP", "BTC-1117-02:CLOSED",
                                          "ETH-1117-02:NO_FILL", "ETH-1117-02:NEW_SETUP"]   # same time: the later line first
    assert evs[-1]["id"] == "BTC-1117-01:NEW_SETUP"
    # ETH-1117-01's TARGET_1 and CLOSED share 08:01: CLOSED (written after) comes first
    i, j = [e["id"] for e in evs].index("ETH-1117-01:CLOSED"), [e["id"] for e in evs].index("ETH-1117-01:TARGET_1")
    assert i < j
    assert setups.build_events([])["events"] == [] and setups.build_events(None)["live_since_utc"] is None
    assert setups.build_events([], live_since="2026-11-17T04:58:00Z")["live_since_utc"] == "2026-11-17T04:58:00Z"


def test_events_limit_100_newest_first():
    log = [{"t": "2026-11-17T00:00:00Z", "k": "start", "ev": "start", "live_since": "2026-11-17T00:00:00Z"}]
    for n in range(80):
        t0 = setups._ms("2026-11-17 01:00") + n * 3600000
        key = "BTCUSDT|%s" % setups._iso(t0)[:16].replace("T", " ")
        sid = "BTC-%s-%02d" % (setups._iso(t0)[5:10].replace("-", ""), n % 24 + 1)
        log += [ev(sid, key, "signal", setups._iso(t0 + 60000), side=1, entry=1.0, stop=0.5, t1=2.0, t2=3.0,
                   valid_until_utc=setups._iso(t0 + 4500000)),
                ev(sid, key, "no_fill", setups._iso(t0 + 1800000), reason="window", bar_utc=setups._iso(t0 + 900000))]
    evs = setups.build_events(log)["events"]
    assert len(evs) == 100 and len(set(e["id"] for e in evs)) == 100
    assert evs[0]["utc"] == setups._iso(setups._ms("2026-11-17 01:00") + 79 * 3600000 + 1800000)
    assert [e["utc"] for e in evs] == sorted([e["utc"] for e in evs], reverse=True)
    assert evs[-1]["utc"] == setups._iso(setups._ms("2026-11-17 01:00") + 30 * 3600000 + 60000)    # the 60 oldest left out
    assert evs[-1]["type"] == "NEW_SETUP" and evs[-2]["type"] == "NO_FILL"


def test_event_ids_are_stable_and_never_repeat(tmp_path):
    log = event_log()
    a, b = setups.build_events(log), setups.build_events(copy.deepcopy(log))
    assert a == b                                                     # the same log, the same file
    ids = [e["id"] for e in a["events"]]
    assert len(ids) == len(set(ids))
    assert all(i == "%s:%s" % (e["signal_id"], e["type"]) for i, e in zip(ids, a["events"]))
    # more lines appended later: every earlier event keeps its id
    more = log + [ev("XAG-1117-01", "XAGUSD|2026-11-17 09:30", "filled", "2026-11-17T12:01:00Z", px=47.5,
                     bar_utc="2026-11-17T11:45:00Z")]
    c = setups.build_events(more)
    assert dict((e["id"], e) for e in c["events"] if e["id"] in ids) == dict((e["id"], e) for e in a["events"])
    # a signal id that comes back for another position (no year in the id; a new state file restarts the counter)
    again = more + [ev("BTC-1117-01", "BTCUSDT|2027-11-17 05:00", "signal", "2027-11-17T05:16:00Z", side=-1, entry=90000.0,
                       stop=91000.0, t1=89000.0, t2=88000.0, valid_until_utc="2027-11-17T06:30:00Z"),
                    ev("BTC-1117-01", "BTCUSDT|2027-11-17 05:00", "filled", "2027-11-17T05:46:00Z", px=90000.0,
                       bar_utc="2027-11-17T05:30:00Z")]
    d = setups.build_events(again)
    ids2 = [e["id"] for e in d["events"]]
    assert len(ids2) == len(set(ids2))
    assert ids2[:2] == ["BTC-1117-01:ENTRY_FILLED:20271117T0530", "BTC-1117-01:NEW_SETUP:20271117T0516"]
    assert "BTC-1117-01:NEW_SETUP" in ids2 and dict((e["id"], e) for e in d["events"])["BTC-1117-01:NEW_SETUP"]["side"] == "LONG"
    assert d["events"][1]["side"] == "SHORT" and d["events"][1]["entry"] == 90000.0
    assert setups.build_events(again) == d
    # the same through the file: signals' own reader (a line written twice counts once, a cut line is skipped)
    dd = tmp_path / "data"
    dd.mkdir()
    with open(str(dd / "signals_log.jsonl"), "w", encoding="utf-8") as fh:
        fh.write("".join(json.dumps(r) + "\n" for r in log + log[3:5]) + "{ a line cut sho")
    for _ in range(2):
        info = setups.write_events(str(tmp_path / "live"), data_dir=str(dd), generated_utc="2026-11-17T12:00:00Z")
        got = json.load(open(info["path"], encoding="utf-8"))
        assert got == dict(json.loads(json.dumps(a)), generated_utc="2026-11-17T12:00:00Z") and info["events"] == 25
    assert setups.events_line(info) == "setup_events: 25 events -> %s" % info["path"]


def test_events_no_free_text_no_nan():
    log = event_log()
    log[5] = dict(log[5], pct=float("nan"), r=float("inf"))           # BTC-1117-01's close
    log[2] = dict(log[2], entry=float("nan"), stop="soon", why="Kronos sees an edge")
    log.append(ev("BTC-1118-01", "BTCUSDT|2026-11-18 00:00", "signal", "2026-11-18T00:16:00Z", side=1, entry=1.0, stop=0.5,
                  t1=2.0, t2=3.0, valid_until_utc="later"))
    doc = setups.build_events(log, generated_utc="2026-11-17T12:00:00Z")
    text = json.dumps(doc, allow_nan=False)
    assert "NaN" not in text and "Infinity" not in text and "kronos" not in text.lower() and "edge" not in text.lower()
    c = dict((e["id"], e) for e in doc["events"])["BTC-1117-01:CLOSED"]
    assert c["result_pct"] is None and c["r"] is None and c["entry"] is None and c["stop"] is None
    codes = set(setups.EV_TYPE.values()) | set(setups.NO_FILL_CODE.values()) | set(setups.CLOSED_CODE.values()) | \
        {"LONG", "SHORT"} | set(ORDER)
    for d in (doc, setups.build_events(event_log())):
        for e in d["events"]:
            for k, v in e.items():
                if isinstance(v, str):
                    assert v in codes or setups._ms(v) is not None or k in ("id", "signal_id"), (k, v)
                    assert " " not in v, (k, v)                       # a code, a name, a time: never a sentence


def test_closes_and_closed_setups_no_free_text_no_nan_small_file(tmp_path):
    all_bars(tmp_path / "bars")
    d = tmp_path / "trades"
    for n, a in enumerate(ORDER):
        write_trades(d, a, [trow(setups._iso(setups._ms("2026-11-10 00:00") + (n * 10 + k) * 3600000),
                                 setups._iso(setups._ms("2026-11-10 00:30") + (n * 10 + k) * 3600000), 1,
                                 123456.789012, 123999.123456, "T1+STOP_BE", 1.23456789, usd=float("nan"), r=float("inf"))
                            for k in range(10)])
    info = setups.write(make_page(), out_dir=str(tmp_path / "live"), bars_dir=str(tmp_path / "bars"), trades_dir=str(d))
    text = open(info["path"], encoding="utf-8").read()
    doc = json.loads(text)
    assert "NaN" not in text and "Infinity" not in text and len(doc["closed_setups"]) == 30
    assert doc["closed_setups"][0]["result_usd"] is None and doc["closed_setups"][0]["r"] is None
    assert all(len(m["closes"]) <= 96 for m in doc["markets"]) and sum(len(m["closes"]) for m in doc["markets"]) == 96 * 7 + 50
    size = os.path.getsize(info["path"])
    assert size < 30000, size                                         # the whole file stays small
    allowed = set(setups.WHY_OUT.values()) | {"FLIP", "T1_THEN_FLIP", "EXIT", "T1_THEN_EXIT", "OTHER", "LONG", "SHORT"} | set(ORDER)
    for c in doc["closed_setups"]:
        for k, v in c.items():
            if isinstance(v, str):
                assert v in allowed or setups._ms(v) is not None, (k, v)


def test_one_file_failing_does_not_stop_the_other(tmp_path, monkeypatch):
    live_dir = tmp_path / "live"
    dd = tmp_path / "data"
    dd.mkdir()
    with open(str(dd / "signals_log.jsonl"), "w", encoding="utf-8") as fh:
        fh.write("".join(json.dumps(r) + "\n" for r in event_log()))
    # the events file fails: setups.json is written all the same, one line says so
    real = setups.build_events
    monkeypatch.setattr(setups, "build_events", lambda *a, **k: 1 / 0)
    lines = []
    info = setups.write(make_page(), out_dir=str(live_dir), data_dir=str(dd), log=lines.append)
    assert lines == ["setup_events: not written (ZeroDivisionError('division by zero'))"]
    assert json.load(open(info["path"], encoding="utf-8"))["followable"]["signals"] == 10
    assert not os.path.exists(str(live_dir / "setup_events.json"))
    monkeypatch.setattr(setups, "build_events", real)
    # setups.json fails (a page it cannot use, a page that is not there): the events file is written, then it raises
    for page in ({"shadows": None, "generated_utc": "2026-11-17T12:00:00Z"}, str(tmp_path / "no_page.json")):
        lines = []
        if os.path.exists(str(live_dir / "setup_events.json")):
            os.remove(str(live_dir / "setup_events.json"))
        with pytest.raises((ValueError, FileNotFoundError)):
            setups.write(page, out_dir=str(live_dir), data_dir=str(dd), log=lines.append)
        got = json.load(open(str(live_dir / "setup_events.json"), encoding="utf-8"))
        assert len(got["events"]) == 25 and lines == ["setup_events: 25 events -> %s" % str(live_dir / "setup_events.json")]
        assert setups._ms(got["generated_utc"]) is not None
    # the events web copy fails alone: both local files, the setups web copy
    web = tmp_path / "www"
    web.mkdir()
    monkeypatch.setenv(setups.WEB_ENV, str(web))
    real_replace = os.replace

    def replace(src, dst):
        if dst == str(web / "setup_events.json"):
            raise PermissionError("no")
        return real_replace(src, dst)
    monkeypatch.setattr(setups.os, "replace", replace)
    lines = []
    info = setups.write(make_page(), out_dir=str(live_dir), data_dir=str(dd), log=lines.append)
    assert info["web_path"] == str(web / "setups.json") and os.listdir(str(web)) == ["setups.json"]
    assert lines == ["setup_events: web copy not written (PermissionError('no'))",
                     "setup_events: 25 events -> %s" % str(live_dir / "setup_events.json")]


def test_step_writes_both_files_and_an_events_failure_never_breaks_it(monkeypatch, tmp_path):
    calls, lines, page_path = _step(monkeypatch, tmp_path)
    monkeypatch.setattr(setups, "load_events", lambda data_dir=None: 1 / 0)
    out = live.step(log=lines.append, fetch=True)
    _same_step(out, calls, lines, page_path)
    assert [x for x in lines if x.startswith("setup_events:")] == ["setup_events: not written (ZeroDivisionError('division by zero'))"]
    assert [x for x in lines if x.startswith("setups:")] == ["setups: 8 markets -> %s" % os.path.join(os.path.dirname(page_path), "setups.json")]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
