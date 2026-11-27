# -*- coding: utf-8 -*-
"""Which paper book speaks for a market (engine15/setups_voice.py; docs/TRAIL_SWITCH_PLAN.md section 2): the changeover
to the trail book and back, one step at a time; what a market shows meanwhile; the state file; and the same through
setups.write, which moves the voices before it builds setups.json.

    py -3 -m pytest tests/test_setups_voice.py -q

THE SWITCH IS OFF in the shipped code (TRAIL_MARKETS == ()), and the first test says so. Every other test names its
markets itself (the trail_markets argument, or a monkeypatch that pytest undoes). Made-up pages, files in pytest's tmp
folders, no network.
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import pytest  # noqa: E402

from engine15 import setups  # noqa: E402
from engine15 import setups_voice as sv  # noqa: E402
from engine15 import vault_feed as vf  # noqa: E402
from engine15.config import DATA_DIR  # noqa: E402

B, E = "BTCUSDT", "ETHUSDT"
ON = (B,)
FLAT = {"status": "FLAT", "equity": 10000.0, "realized_usd": 0.0, "trades": 0, "wins": 0}


@pytest.fixture(autouse=True)
def _alone(monkeypatch, tmp_path):
    """No web folder and no real record, bar file, trade file or voice state."""
    monkeypatch.delenv(setups.WEB_ENV, raising=False)
    monkeypatch.setattr(setups, "S1_DIR", str(tmp_path / "no_s1_here"))
    monkeypatch.setattr(setups, "BARS_DIR", str(tmp_path / "no_bars_here"))
    monkeypatch.setattr(setups, "TRADES_DIR", str(tmp_path / "no_trades_here"))
    monkeypatch.setattr(sv, "STATE_PATH", str(tmp_path / "no_state_here" / "setups_voice_state.json"))


def held(opened, side="LONG", entry=100.0, stop=98.0, **kw):
    """A book's view with a setup open since `opened` ('YYYY-MM-DD HH:MM', as shadows.asset_view writes it)."""
    return dict(FLAT, status=side, entry=entry, stop=stop, opened_utc=opened, unrealized_usd=0.0, **kw)


def page(t, targets=FLAT, trail=FLAT, eth=None):
    """One step's page at bar close `t` ('2026-11-17 03:15'): BTC's view in each book (None = the page does not carry
    that book), and ETH's (targets view, trail view) when given."""
    books = {}
    for name, v, k in (("b_targets", targets, 0), ("b_trail_setups", trail, 1)):
        if v is not None:
            books[name] = {"title": name, "assets": {B: copy.deepcopy(v)}}
            if eth is not None:
                books[name]["assets"][E] = copy.deepcopy(eth[k])
    syms = [B] + ([E] if eth is not None else [])
    return {"generated_utc": t.replace(" ", "T") + ":40Z", "version": "test", "markets": {"crypto": syms},
            "assets": dict((s, {"short": s[:3], "time": t, "price": 101.0, "edge_pts": 1.0, "market_group": "crypto"})
                           for s in syms),
            "shadows": {"books": books, "markets": {"crypto": {"as_of_utc": t}}}}


def entry(rule, frm=None, pending=False, wait=None):
    return {"rule": rule, "from_utc": frm, "pending": pending, "wait": wait}


def shows(p, st, sym=B):
    """What the market shows: (the voice, the opening of the shown setup or None)."""
    got = sv.published(p, sym, st)
    assert got["book"] == sv.BOOKS[got["rule"]] and isinstance(got["open"], bool)
    return got["rule"], sv.opened_of(got["view"]) if got["open"] else None


# ------------------------------------------------------------------ the switch
def test_the_switch_in_the_shipped_code_is_btc_and_eth():
    # Switching a market on or off moves the Setups page, the signals and (BTC, ETH) the VIP vault's real orders to
    # another book. That is the owner's word, a version bump and the vault's own key together: never a change made to
    # get a test through. ON for BTC and ETH since think15-v5.2.12 (owner, 27 Nov 2026). Inside the other tests both
    # switches are off (tests/conftest.py); the shipped values are read from there.
    from conftest import SHIPPED
    assert SHIPPED["TRAIL_MARKETS"] == ("BTCUSDT", "ETHUSDT")
    # the two keys go together: no vault market on the trail voice while the feed may not send a trail book
    assert SHIPPED["SEND_TRAIL"] or not set(SHIPPED["TRAIL_MARKETS"]) & set(vf.ALLOWED)
    assert sv.TRAIL_MARKETS == () and vf.SEND_TRAIL is False             # inside a test: off (conftest)
    assert sv.BOOKS == {"targets": "b_targets", "trail": "b_trail_setups"} and sv.RULES == ("targets", "trail")
    assert sv.BOOKS["targets"] == setups.BOOK and sv.book_of("trail") == "b_trail_setups"
    assert sv.SCHEMA == 1
    for s in (B, E, "XAUUSD"):
        assert sv.want(s) == "targets" and sv.want(s, (s,)) == "trail" and sv.want(s, ()) == "targets"


def test_the_state_file_lives_in_the_data_folder(monkeypatch):
    monkeypatch.undo()                                                # the shipped path, not this file's stand-in
    assert sv.STATE_PATH == os.path.join(DATA_DIR, "setups_voice_state.json")


def test_with_the_switch_off_nothing_moves_and_every_market_is_the_targets_book():
    p = page("2026-11-17 03:15", targets=held("2026-11-17 02:30"), trail=held("2026-11-17 01:00"))
    for st in (None, {}, {"schema": 1, "markets": {}}):
        got = sv.published(p, B, st)
        assert got == {"rule": "targets", "book": "b_targets", "view": p["shadows"]["books"]["b_targets"]["assets"][B],
                       "open": True, "from_utc": None, "pending": False}
    assert sv.update(p, {}) == {"schema": 1, "markets": {}}           # the shipped switch: no market is named
    assert sv.update(p, None, trail_markets=()) == {"schema": 1, "markets": {}}
    assert shows(page("2026-11-17 03:15"), None) == ("targets", None)                 # a flat book shows nothing
    waiting = dict(FLAT, status="WAITING LONG", opened_utc="2026-11-17 02:30")
    assert shows(page("2026-11-17 03:15", targets=waiting), None) == ("targets", None)   # a resting order is no setup


# ------------------------------------------------------------------ the changeover to the trail book
def test_the_changeover_to_the_trail_book_step_by_step():
    X, A, NEW = "2026-11-17 02:30", "2026-11-17 01:00", "2026-11-17 04:15"
    st = {}
    # step 1: the switch is seen while the targets setup X is open (the trail book holds a setup A of its own)
    p = page("2026-11-17 03:15", targets=held(X), trail=held(A))
    sv.update(p, st, ON)
    assert st == {"schema": 1, "markets": {B: entry("targets", pending=True, wait=X)}}
    assert shows(p, st) == ("targets", X)                             # X goes on being shown: nothing changes inside it
    # step 2: X is still open
    p = page("2026-11-17 03:30", targets=held(X), trail=held(A))
    before = copy.deepcopy(st)
    sv.update(p, st, ON)
    assert st == before and shows(p, st) == ("targets", X)
    # step 3: the targets book no longer shows X: the voice is the trail book from this bar's close
    p = page("2026-11-17 03:45", trail=held(A))
    sv.update(p, st, ON)
    assert st["markets"][B] == entry("trail", frm="2026-11-17T03:45:00Z")
    got = sv.published(p, B, st)
    assert (got["rule"], got["book"], got["from_utc"], got["pending"]) ==         ("trail", "b_trail_setups", "2026-11-17T03:45:00Z", False)
    assert got["view"]["opened_utc"] == A and got["open"] is False    # A was already open at the changeover: not shown
    # step 4: A is still open: the market reads FLAT
    p = page("2026-11-17 04:00", targets=held("2026-11-17 04:00"), trail=held(A))     # (whatever the targets book does)
    before = copy.deepcopy(st)
    sv.update(p, st, ON)
    assert st == before and shows(p, st) == ("trail", None)
    # step 5: the trail book opens its next setup: shown from its opening
    p = page("2026-11-17 04:15", targets=held("2026-11-17 04:00"), trail=held(NEW))
    sv.update(p, st, ON)
    assert st == before and shows(p, st) == ("trail", NEW)
    # later steps change nothing about the voice
    p = page("2026-11-17 09:00", trail=held(NEW))
    sv.update(p, st, ON)
    assert st == before and shows(p, st) == ("trail", NEW)
    assert shows(page("2026-11-17 09:15"), st) == ("trail", None)     # the trail book is flat: FLAT


def test_flat_at_the_first_sight_of_the_switch_changes_over_in_that_step():
    p = page("2026-11-17 03:15", trail=held("2026-11-17 03:15"))      # no targets setup to wait for
    st = sv.update(p, {}, ON)
    assert st["markets"][B] == entry("trail", frm="2026-11-17T03:15:00Z")
    assert shows(p, st) == ("trail", "2026-11-17 03:15")              # opened AT the changeover (this close): shown
    q = page("2026-11-17 03:15", trail=held("2026-11-17 03:00"))      # opened one bar before it: never shown
    assert shows(q, sv.update(q, {}, ON)) == ("trail", None)


def test_a_new_targets_setup_in_place_of_the_remembered_one_changes_over_and_is_never_shown():
    X, Y = "2026-11-17 02:30", "2026-11-17 03:30"
    st = sv.update(page("2026-11-17 03:15", targets=held(X)), {}, ON)
    p = page("2026-11-17 03:45", targets=held(Y, side="SHORT"))       # X ended and Y opened between two steps (a flip)
    sv.update(p, st, ON)
    assert st["markets"][B] == entry("trail", frm="2026-11-17T03:45:00Z")
    assert shows(p, st) == ("trail", None)                            # Y belongs to a book that no longer speaks
    assert shows(page("2026-11-17 04:00", targets=held(Y, side="SHORT")), st) == ("trail", None)


def test_two_markets_change_over_each_in_its_own_time():
    X = "2026-11-17 02:30"
    st = {}
    p = page("2026-11-17 03:15", targets=held(X), eth=(FLAT, held("2026-11-17 03:15", side="SHORT")))
    sv.update(p, st, (B, E))
    assert st["markets"] == {B: entry("targets", pending=True, wait=X), E: entry("trail", frm="2026-11-17T03:15:00Z")}
    assert shows(p, st, B) == ("targets", X) and shows(p, st, E) == ("trail", "2026-11-17 03:15")
    sv.update(p, st, (E,))                                            # BTC is taken out again before its changeover
    assert st["markets"][B] == entry("targets") and shows(p, st, B) == ("targets", X)
    assert st["markets"][E] == entry("trail", frm="2026-11-17T03:15:00Z")


# ------------------------------------------------------------------ and back
def test_the_changeover_back_is_the_mirror():
    F1, T, Z, W = "2026-11-17T03:45:00Z", "2026-11-17 04:15", "2026-11-17 04:30", "2026-11-17 05:15"
    st = {"schema": 1, "markets": {B: entry("trail", frm=F1)}}
    # step 1: the market is taken out of the switch while the trail setup T is shown
    p = page("2026-11-17 04:45", targets=held(Z), trail=held(T))
    sv.update(p, st, ())
    assert st["markets"][B] == entry("trail", frm=F1, pending=True, wait=T)
    assert shows(p, st) == ("trail", T)                               # T goes on to its own end on the trail voice
    # step 2: T has ended: the voice is the targets book again, from this bar's close
    p = page("2026-11-17 05:00", targets=held(Z))
    sv.update(p, st, ())
    assert st["markets"][B] == entry("targets", frm="2026-11-17T05:00:00Z")
    assert shows(p, st) == ("targets", None)                          # Z was open before that moment: not shown
    # step 3: the targets book's next setup is shown
    p = page("2026-11-17 05:15", targets=held(W), trail=held("2026-11-17 05:15"))
    before = copy.deepcopy(st)
    sv.update(p, st, ())
    assert st == before and shows(p, st) == ("targets", W)
    # and on again: the same rule a second time, with the new moment
    sv.update(p, st, ON)
    assert st["markets"][B] == entry("targets", frm="2026-11-17T05:00:00Z", pending=True, wait=W)
    p = page("2026-11-17 06:00", trail=held("2026-11-17 05:15"))
    sv.update(p, st, ON)
    assert st["markets"][B] == entry("trail", frm="2026-11-17T06:00:00Z") and shows(p, st) == ("trail", None)


def test_back_while_the_trail_market_shows_nothing_changes_over_at_once():
    st = {"schema": 1, "markets": {B: entry("trail", frm="2026-11-17T03:45:00Z")}}
    p = page("2026-11-17 04:00", targets=held("2026-11-17 02:00"), trail=held("2026-11-17 01:00"))   # A: never shown
    sv.update(p, st, ())
    assert st["markets"][B] == entry("targets", frm="2026-11-17T04:00:00Z") and shows(p, st) == ("targets", None)


def test_the_switch_taken_back_before_the_changeover_leaves_the_market_where_it_was():
    X = "2026-11-17 02:30"
    p = page("2026-11-17 03:15", targets=held(X), trail=held("2026-11-17 01:00"))
    st = sv.update(p, {}, ON)
    assert st["markets"][B]["pending"] is True
    sv.update(p, st, ())
    assert st["markets"][B] == entry("targets") and shows(p, st) == ("targets", X)
    assert sv.published(p, B, st) == sv.published(p, B, None)         # exactly a market that never moved


# ------------------------------------------------------------------ what a market shows meanwhile
def test_while_pending_only_the_remembered_setup_is_shown():
    X, Y = "2026-11-17 02:30", "2026-11-17 03:30"
    st = {"schema": 1, "markets": {B: entry("targets", pending=True, wait=X)}}
    assert shows(page("2026-11-17 03:15", targets=held(X)), st) == ("targets", X)
    assert shows(page("2026-11-17 03:45", targets=held(Y)), st) == ("targets", None)   # another setup: not shown
    assert shows(page("2026-11-17 03:45"), st) == ("targets", None)
    got = sv.published(page("2026-11-17 03:45", targets=held(Y)), B, st)
    assert got["pending"] is True and got["view"]["opened_utc"] == Y and got["open"] is False   # the view is still there
    none = {"schema": 1, "markets": {B: entry("targets", pending=True, wait=None)}}      # nothing was remembered
    assert shows(page("2026-11-17 03:45", targets=held(Y)), none) == ("targets", None)


def test_a_reader_a_moment_before_or_after_the_engine_never_sees_a_setup_the_page_will_not_show():
    # the Telegram bot reads the page and the state on its own clock: old state with the new page, or the other way
    X, Y, A = "2026-11-17 02:30", "2026-11-17 03:30", "2026-11-17 01:00"
    old_page, new_page = page("2026-11-17 03:15", targets=held(X), trail=held(A)), page("2026-11-17 03:45", targets=held(Y),
                                                                                       trail=held(A))
    old = sv.update(copy.deepcopy(old_page), {}, ON)
    new = sv.update(copy.deepcopy(new_page), copy.deepcopy(old), ON)
    assert shows(old_page, old) == ("targets", X) and shows(new_page, new) == ("trail", None)     # what the engine shows
    assert shows(new_page, old) == ("targets", None)                  # old state, new page: nothing yet (never Y)
    assert shows(old_page, new) == ("trail", None)                    # new state, old page: nothing (never A)
    assert shows(new_page, None) == ("targets", Y)                    # (only a reader with NO state would show Y:
    #                                                                   every reader must pass the state it loaded)


# ------------------------------------------------------------------ what is left alone
def test_a_market_whose_book_is_missing_from_the_page_is_left_alone():
    X = "2026-11-17 02:30"
    assert sv.update(page("2026-11-17 03:15", targets=held(X), trail=None), {}, ON) == {"schema": 1, "markets": {}}
    assert sv.update(page("2026-11-17 03:15", targets=None), {}, ON) == {"schema": 1, "markets": {}}
    for st in ({"schema": 1, "markets": {B: entry("targets", pending=True, wait=X)}},
               {"schema": 1, "markets": {B: entry("trail", frm="2026-11-17T03:00:00Z", pending=True, wait=X)}}):
        for p in (page("2026-11-17 03:45", trail=None), page("2026-11-17 03:45", targets=None),
                  page("2026-11-17 03:45", targets=None, trail=None), {"assets": {B: {}}}, {}, None, "not a page"):
            before = copy.deepcopy(st)
            assert sv.update(p, st, ON if st["markets"][B]["rule"] == "targets" else ()) is st and st == before
    # a market of the state that this page does not list at all, and one whose view is not a view
    st = {"schema": 1, "markets": {"XAUUSD": entry("targets", pending=True, wait=X)}}
    before = copy.deepcopy(st)
    assert sv.update(page("2026-11-17 03:45"), st, ("XAUUSD",)) == before
    p = page("2026-11-17 03:45")
    p["shadows"]["books"]["b_trail_setups"]["assets"][B] = "half a view"
    assert sv.update(p, {}, ON) == {"schema": 1, "markets": {}}
    assert sv.published(p, B, {"markets": {B: entry("trail", frm="2026-11-17T03:00:00Z")}})["view"] is None


def test_a_page_without_a_bar_time_changes_nothing_over():
    p = page("2026-11-17 03:15")
    del p["assets"][B]["time"]
    del p["shadows"]["markets"]["crypto"]["as_of_utc"]
    st = sv.update(p, {}, ON)
    assert st["markets"][B] == entry("targets", pending=True, wait=None)      # seen, but no moment to start from
    assert shows(p, st) == ("targets", None)
    sv.update(page("2026-11-17 03:30"), st, ON)                       # the next step has one
    assert st["markets"][B] == entry("trail", frm="2026-11-17T03:30:00Z")
    # the group's own clock stands in when the asset carries no time (setups.py's price_bar_utc does the same)
    q = page("2026-11-17 03:15")
    del q["assets"][B]["time"]
    assert sv.bar_utc(q, B) == "2026-11-17T03:15:00Z" == sv.bar_utc(page("2026-11-17 03:15"), B)


def test_an_entry_that_is_not_an_entry_is_no_entry():
    p = page("2026-11-17 03:15", targets=held("2026-11-17 02:30"))
    for bad in ("x", None, [], {"rule": "something else"}, {"from_utc": "2026-11-17T03:00:00Z"}):
        assert sv.published(p, B, {"markets": {B: bad}}) == sv.published(p, B, None)


# ------------------------------------------------------------------ the state file
def test_no_file_and_nothing_to_recover_is_an_empty_state_and_save_writes_nothing(tmp_path):
    path = str(tmp_path / "setups_voice_state.json")
    st = sv.load(path)
    assert st == {"schema": 1, "markets": {}} == sv.load(path, prev_doc={"markets": [{"symbol": B, "side": "LONG"}]})
    assert sv.save(path, st) is False and sv.save(path, {}) is False and sv.save(path, None) is False
    assert os.listdir(str(tmp_path)) == []                            # the switch off leaves no file


def test_save_is_atomic_and_load_gives_the_state_back(tmp_path):
    path = str(tmp_path / "setups_voice_state.json")
    st = {"schema": 1, "markets": {B: entry("trail", frm="2026-11-17T03:45:00Z"),
                                   E: entry("targets", pending=True, wait="2026-11-17 02:30")}}
    assert sv.save(path, st) is True
    assert os.listdir(str(tmp_path)) == ["setups_voice_state.json"]   # no temp file left
    assert sv.load(path) == st
    assert sv.save(path, copy.deepcopy(st)) is False                  # nothing changed: nothing is written
    st["markets"][B]["pending"] = True
    assert sv.save(path, st) is True and sv.load(path)["markets"][B]["pending"] is True
    with open(path, encoding="utf-8") as fh:
        assert json.load(fh) == st


def test_a_lost_file_is_rebuilt_from_the_previous_setups_json(tmp_path):
    path = str(tmp_path / "setups_voice_state.json")
    voice = {"schema": 1, "markets": {B: entry("trail", frm="2026-11-17T03:45:00Z"),
                                      E: entry("targets", pending=True, wait="2026-11-17 02:30")}}
    p = page("2026-11-17 04:15", trail=held("2026-11-17 04:15"), eth=(held("2026-11-17 02:30"), FLAT))
    prev = setups.build(p, voice=voice)                               # the file the engine wrote last
    assert [m.get("exit_rule") for m in prev["markets"]] == ["trail", None]
    got = sv.load(path, prev_doc=prev)
    # the trail market comes back with its starting time; a market that was only WAITING starts again as "just seen"
    assert got == {"schema": 1, "markets": {B: entry("trail", frm="2026-11-17T03:45:00Z")}} == sv.recover(prev)
    assert sv.published(p, B, got) == sv.published(p, B, voice)       # and shows what it showed
    sv.update(p, got, (B, E))
    assert got["markets"][E] == voice["markets"][E]                   # the wait is found again at the next step
    assert not os.path.exists(path)                                   # load never writes
    # only whole entries are taken from the file
    odd = {"markets": [{"symbol": B, "exit_rule": "trail"}, {"symbol": E, "exit_rule": "trail", "exit_rule_from_utc": "soon"},
                       {"symbol": 7, "exit_rule": "trail", "exit_rule_from_utc": "2026-11-17T03:45:00Z"}, "x", None,
                       {"symbol": "XAUUSD", "exit_rule": "targets", "exit_rule_from_utc": "2026-11-17T03:45:00Z"},
                       {"symbol": "SPX", "exit_rule": "trail", "exit_rule_from_utc": "2026-11-17 03:45"}]}
    assert sv.recover(odd) == {"schema": 1, "markets": {"SPX": entry("trail", frm="2026-11-17T03:45:00Z")}}
    for nothing in (None, {}, [], "x", {"markets": None}, {"markets": "x"}):
        assert sv.recover(nothing) == {"schema": 1, "markets": {}}


def test_an_unreadable_file_is_never_taken_for_an_empty_one(tmp_path):
    path = str(tmp_path / "setups_voice_state.json")
    prev = {"markets": [{"symbol": B, "exit_rule": "trail", "exit_rule_from_utc": "2026-11-17T03:45:00Z"}]}
    for text in ("{ half a sta", "", "[]", '{"schema": 1}', '{"markets": []}', "null"):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        with pytest.raises(ValueError):                               # nothing to recover: the step publishes nothing
            sv.load(path)
        with pytest.raises(ValueError):
            sv.load(path, prev_doc={"markets": [{"symbol": B, "side": "FLAT"}]})
        assert sv.load(path, prev_doc=prev) == {"schema": 1, "markets": {B: entry("trail", frm="2026-11-17T03:45:00Z")}}
        with open(path, encoding="utf-8") as fh:
            assert fh.read() == text                                  # load does not repair the file itself
    os.remove(path)
    os.mkdir(path)                                                    # something that cannot be opened at all
    with pytest.raises(OSError):
        sv.load(path)
    assert sv.load(path, prev_doc=prev)["markets"][B]["rule"] == "trail"


# ------------------------------------------------------------------ through setups.write
def read(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def btc(info):
    return dict((m["symbol"], m) for m in read(info["path"])["markets"])[B]


def test_write_moves_the_voice_then_builds_the_file_and_back(tmp_path, monkeypatch):
    data, live = tmp_path / "data", tmp_path / "live"
    data.mkdir()
    state = str(data / "setups_voice_state.json")
    kw = dict(out_dir=str(live), data_dir=str(data), trades_dir=str(tmp_path / "trades"))
    X, A, NEW = "2026-11-17 02:30", "2026-11-17 01:00", "2026-11-17 03:45"
    # the switch off: today's file, and no state file
    off = btc(setups.write(page("2026-11-17 03:00", targets=held(X), trail=held(A)), **kw))
    assert off["side"] == "LONG" and "exit_rule" not in off and os.listdir(str(data)) == []
    monkeypatch.setattr(sv, "TRAIL_MARKETS", ON)
    # step 1: seen while X is open: X is still shown, exactly as before
    m = btc(setups.write(page("2026-11-17 03:15", targets=held(X), trail=held(A)), **kw))
    assert read(state) == {"schema": 1, "markets": {B: entry("targets", pending=True, wait=X)}}
    assert m["side"] == "LONG" and m["opened_utc"] == "2026-11-17T02:30:00Z" and list(m) == list(off)
    # step 2: X has ended: the trail voice, FLAT (A was already open)
    m = btc(setups.write(page("2026-11-17 03:30", trail=held(A)), **kw))
    assert read(state)["markets"][B] == entry("trail", frm="2026-11-17T03:30:00Z")
    assert (m["side"], m["entry"], m["exit_rule"], m["trail_active"], m["exit_rule_from_utc"]) == \
        ("FLAT", None, "trail", False, "2026-11-17T03:30:00Z")
    # step 3: the trail book's next setup, from its opening
    step3 = page("2026-11-17 03:45", trail=held(NEW, entry=101.0, stop=99.0))
    m = btc(setups.write(step3, **kw))
    assert (m["side"], m["entry"], m["stop"], m["opened_utc"], m["exit_rule"], m["trail_active"]) == \
        ("LONG", 101.0, 99.0, "2026-11-17T03:45:00Z", "trail", False)
    shown = read(str(live / "setups.json"))
    # the state file is lost: rebuilt from the setups.json of the step before, and the file comes out the same
    os.remove(state)
    assert btc(setups.write(step3, **kw)) == m and read(str(live / "setups.json")) == shown
    assert read(state) == {"schema": 1, "markets": {B: entry("trail", frm="2026-11-17T03:30:00Z")}}
    # the trail arms; the stop moves
    m = btc(setups.write(page("2026-11-17 04:00", trail=held(NEW, entry=101.0, stop=101.5, trailing=True)), **kw))
    assert (m["stop"], m["trail_active"], m["opened_utc"]) == (101.5, True, "2026-11-17T03:45:00Z")
    # BACK: the market is taken out; the shown trail setup lives on, then the targets book speaks again
    monkeypatch.setattr(sv, "TRAIL_MARKETS", ())
    Z = "2026-11-17 04:00"
    armed = held(NEW, entry=101.0, stop=101.5, trailing=True)
    m = btc(setups.write(page("2026-11-17 04:15", targets=held(Z), trail=armed), **kw))
    assert read(state)["markets"][B] == entry("trail", frm="2026-11-17T03:30:00Z", pending=True, wait=NEW)
    assert (m["side"], m["exit_rule"], m["stop"]) == ("LONG", "trail", 101.5)
    m = btc(setups.write(page("2026-11-17 04:30", targets=held(Z)), **kw))
    assert read(state)["markets"][B] == entry("targets", frm="2026-11-17T04:30:00Z")
    assert m["side"] == "FLAT" and list(m) == list(off)               # Z is not shown; no trail key is left
    m = btc(setups.write(page("2026-11-17 04:45", targets=held("2026-11-17 04:45", entry=102.0, stop=100.0)), **kw))
    assert (m["side"], m["entry"], m["opened_utc"]) == ("LONG", 102.0, "2026-11-17T04:45:00Z") and list(m) == list(off)


def test_write_publishes_nothing_when_the_state_cannot_be_read_or_saved(tmp_path, monkeypatch):
    data, live = tmp_path / "data", tmp_path / "live"
    data.mkdir()
    state = str(data / "setups_voice_state.json")
    kw = dict(out_dir=str(live), data_dir=str(data))
    with open(state, "w", encoding="utf-8") as fh:
        fh.write("{ half a sta")
    lines = []
    with pytest.raises(ValueError):                                   # nothing to recover it from: no setups.json yet
        setups.write(page("2026-11-17 03:15", targets=held("2026-11-17 02:30")), log=lines.append, **kw)
    assert not os.path.exists(str(live / "setups.json")) and not os.path.exists(str(live / "landing.json"))
    os.remove(state)
    first = setups.write(page("2026-11-17 03:15", targets=held("2026-11-17 02:30")), **kw)
    before = open(first["path"], encoding="utf-8").read()
    # a state that cannot be SAVED: the changeover is not shown either (it would be made again one step later)
    monkeypatch.setattr(sv, "TRAIL_MARKETS", ON)

    def no_disk(path, st):
        raise OSError("the disk said no")
    monkeypatch.setattr(sv, "save", no_disk)
    with pytest.raises(OSError):
        setups.write(page("2026-11-17 03:30"), **kw)
    assert open(first["path"], encoding="utf-8").read() == before and not os.path.exists(state)


def test_without_a_data_folder_write_uses_the_modules_own_state_path(tmp_path, monkeypatch):
    path = tmp_path / "elsewhere" / "setups_voice_state.json"
    path.parent.mkdir()
    monkeypatch.setattr(sv, "STATE_PATH", str(path))
    monkeypatch.setattr(sv, "TRAIL_MARKETS", ON)
    m = btc(setups.write(page("2026-11-17 03:15", trail=held("2026-11-17 03:15")), out_dir=str(tmp_path / "live")))
    assert read(str(path))["markets"][B] == entry("trail", frm="2026-11-17T03:15:00Z")
    assert (m["side"], m["exit_rule"], m["opened_utc"]) == ("LONG", "trail", "2026-11-17T03:15:00Z")
