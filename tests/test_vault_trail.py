# -*- coding: utf-8 -*-
"""vault_feed in trail mode (docs/TRAIL_SWITCH_PLAN.md): the trail book body, the stop moves, the close, the two
switches and the dry-run preview. No network: `post` is replaced where a pass is run.

    py -3 -m pytest tests/test_vault_trail.py -q
"""
import calendar
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import setups_voice as sv  # noqa: E402
from engine15 import vault_feed as vf  # noqa: E402

OPENED = "2026-11-26T09:00:00Z"
TRAIL_KEYS = {"symbol", "side", "entry", "stop", "price", "exit_rule", "trail_active", "entry_window_open", "opened_utc",
              "as_of_utc"}


def ep(utc):
    return calendar.timegm(time.strptime(utc, "%Y-%m-%dT%H:%M:%SZ"))


def bar(n):
    """The n-th 15-minute bar close after 09:00 UTC on 26 Nov 2026."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ep(OPENED) + 900 * n))


def trail(sym="BTCUSDT", side="SHORT", entry=60000.0, stop=61500.0, price=59900.0, active=False, window=True,
          opened=OPENED, at=None, edge=None, **kw):
    """A setups.json market on the trail voice, as setups._market writes it (FLAT: side="FLAT")."""
    m = {"symbol": sym, "short": sym[:3], "group": "crypto", "side": side, "price": price, "price_bar_utc": at or bar(0),
         "entry": None, "stop": None, "target_1": None, "target_2": None, "t1_taken": False, "held_share": None,
         "opened_utc": None, "rr_now_t1": None, "rr_now_t2": None, "entry_window_open": False,
         "entry_valid_until_utc": None, "exit_rule": "trail", "trail_active": False,
         "exit_rule_from_utc": "2026-11-26T08:00:00Z", "edge_with_position_pts": edge}
    if side != "FLAT":
        m.update(entry=entry, stop=stop, opened_utc=opened, entry_window_open=window, trail_active=active)
    m.update(kw)
    return m


def targets(sym="BTCUSDT", side="SHORT", entry=60000.0, stop=61500.0, t1=59000.0, t2=58000.0, price=59900.0,
            opened="2026-11-25T18:45:00Z", at=None, **kw):
    m = {"symbol": sym, "side": side, "price": price, "price_bar_utc": at or bar(0), "entry": entry, "stop": stop,
         "target_1": t1, "target_2": t2, "t1_taken": False, "opened_utc": opened, "rr_now_t2": None,
         "entry_window_open": False}
    m.update(kw)
    return m


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setattr(vf, "SEND_TRAIL", True)


def trade_file(d, book, sym, opened, side, p_out, why):
    path = os.path.join(str(d), "shadow_trades_%s_%s.csv" % (book, sym))
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8", newline="") as fh:
        if new:
            fh.write("t_in_ms,side,p_in,p_out,why_out,target_2\n")
        fh.write("%d,%s,60000.0,%s,%s,\n" % (ep(opened) * 1000, 1.0 if side == "LONG" else -1.0, p_out, why))


# ------------------------------------------------------------------ the switches
def test_both_switches_are_on_in_the_shipped_code():
    """ON since think15-v5.2.12 (27 Nov 2026): the owner's word in both sessions, vault package f7609091 accepts the
    trail bodies. Changing either is a real-money decision and a version bump (docs/TRAIL_SWITCH_PLAN.md). Inside the
    other tests both are off (tests/conftest.py)."""
    from shipped_values import SHIPPED
    assert SHIPPED["SEND_TRAIL"] is True
    assert SHIPPED["TRAIL_MARKETS"] == ("BTCUSDT", "ETHUSDT")


def test_a_vault_market_is_never_on_the_trail_voice_while_the_feed_cannot_send_it():
    from shipped_values import SHIPPED
    assert SHIPPED["SEND_TRAIL"] or not (set(vf.ALLOWED) & set(SHIPPED["TRAIL_MARKETS"]))
    assert vf.SEND_TRAIL or not (set(vf.ALLOWED) & set(sv.TRAIL_MARKETS))


# ------------------------------------------------------------------ the body
def test_trail_body_not_armed_short(on):
    body, why = vf.build_book(trail(edge=8.3), bar(0), lead=-8.3)
    assert why is None
    b = body["book"]
    assert set(b) == TRAIL_KEYS | {"lead_pts"}
    assert b == {"symbol": "BTCUSDT", "side": "SHORT", "entry": "60000", "stop": "61500", "price": "59900",
                 "exit_rule": "trail", "trail_active": False, "entry_window_open": True, "opened_utc": OPENED,
                 "as_of_utc": bar(0), "lead_pts": -8.3}
    for k in ("target_1", "target_2", "rr_now_t2", "t1_taken", "held_share", "exit_rule_from_utc"):
        assert k not in b


def test_trail_body_armed_stop_may_be_past_the_entry(on):
    b = vf.build_book(trail(stop=59200.0, price=58400.0, active=True, window=False), bar(9))[0]["book"]
    assert set(b) == TRAIL_KEYS                                  # no lead known: the key is left out
    assert (b["stop"], b["trail_active"], b["entry_window_open"]) == ("59200", True, False)
    b = vf.build_book(trail(side="LONG", entry=60000.0, stop=60700.0, price=61900.0, active=True), bar(9))[0]["book"]
    assert (b["side"], b["stop"]) == ("LONG", "60700")


@pytest.mark.parametrize("kw, why", [
    (dict(stop=59500.0), "levels out of order"),                 # not armed: the stop must be beyond the entry
    (dict(stop=59800.0, active=True), "stop not on the losing side of the price"),
    (dict(target_1=59000.0), "a trail book with targets"),
    (dict(t1_taken=True), "a trail book with targets"),
    (dict(trail_active=None), "bad trail_active"),
    (dict(entry_window_open="yes"), "bad entry_window_open"),
    (dict(stop=None), "levels missing (stop)"),
    (dict(price=None), "no price"),
    (dict(opened_utc="2026-11-26 09:00"), "bad opened_utc"),
])
def test_a_trail_book_that_is_not_in_order_is_not_sent(on, kw, why):
    assert vf.build_book(trail(**kw), bar(0)) == (None, why)


def test_a_flat_trail_market_is_exactly_todays_flat_body(on):
    body, why = vf.build_book(trail(side="FLAT"), bar(0))
    assert why is None
    assert body == {"book": {"symbol": "BTCUSDT", "side": "FLAT", "t1_taken": False, "entry_window_open": False,
                             "as_of_utc": bar(0), "price": "59900"}}


def test_with_the_switch_off_a_trail_body_is_never_built_unless_forced():
    assert vf.build_book(trail(), bar(0)) == (None, "trail book while SEND_TRAIL is off")
    assert vf.build_book(trail(), bar(0), force=True)[0]["book"]["exit_rule"] == "trail"


def test_a_targets_market_is_untouched():
    b = vf.build_book(targets(), bar(0))[0]["book"]
    assert "exit_rule" not in b and "trail_active" not in b and b["target_1"] == "59000" and b["t1_taken"] is False


# ------------------------------------------------------------------ the ids
def test_the_stop_move_id():
    iid = vf.ms_id("BTCUSDT", OPENED, "2026-11-26T19:15:00Z")
    assert iid == "BTCUSDT.20261126T090000Z.ms.261915"
    assert vf.INTENT_ID_RE.match(iid) and len(iid) <= 64 and not iid.startswith(("join-", "k3-", "rz-", "topup-"))
    assert vf.ms_id("BTCUSDT", OPENED, "2026-11-26T19:30:00Z") != iid
    assert vf.ms_id("BTCUSDT", OPENED, None) is None
    assert iid != vf.intent_id("BTCUSDT", OPENED, "move_stop", "futures")        # never the Target 1 move's id


def test_tighter():
    assert vf.tighter("SHORT", "61000", "61500") and not vf.tighter("SHORT", "61500", "61500")
    assert vf.tighter("LONG", "59000", "58500") and not vf.tighter("LONG", "58000", "58500")
    assert not vf.tighter("LONG", None, "1") and not vf.tighter("LONG", "1", None)


# ------------------------------------------------------------------ track: the stop moves and the close
def test_the_life_of_a_trail_setup(tmp_path):
    st, d = {}, str(tmp_path)
    assert vf.track("BTCUSDT", trail(side="FLAT"), st, d, 1000) is None
    assert vf.track("BTCUSDT", trail(edge=8.3, at=OPENED), st, d, 1001) is None      # first sight: its opening
    assert st["pos"]["BTCUSDT"]["stop_sent"] == "61500" and st["pos"]["BTCUSDT"]["lead_pts"] == -8.3
    assert st.get("intents", {}) == {}
    vf.track("BTCUSDT", trail(window=False, at=bar(1)), st, d, 1002)                 # nothing moved: nothing made
    assert st.get("intents", {}) == {}
    vf.track("BTCUSDT", trail(stop=59800.0, price=58500.0, active=True, window=False, at=bar(5)), st, d, 1003)
    (iid, it), = st["intents"].items()
    assert iid == "BTCUSDT.20261126T090000Z.ms.261015"
    assert it["body"] == {"intent_id": iid, "market": "futures", "symbol": "BTCUSDT", "action": "move_stop",
                          "side": "SELL", "stop_price": "59800", "reference_price": "58500"}
    assert vf.intent_ok(it["body"]) and it["status"] == "pending"
    assert st["pos"]["BTCUSDT"]["stop_sent"] == "59800" and st["pos"]["BTCUSDT"]["lead_pts"] == -8.3
    vf.track("BTCUSDT", trail(stop=59800.0, price=58300.0, active=True, window=False, at=bar(6)), st, d, 1004)
    assert len(st["intents"]) == 1                                                   # the same stop: no second move
    vf.track("BTCUSDT", trail(stop=59100.0, price=58000.0, active=True, window=False, at=bar(7)), st, d, 1005)
    assert len(st["intents"]) == 2
    assert st["intents"][iid]["status"] == "superseded"                              # the older move never went out
    newest = st["intents"]["BTCUSDT.20261126T090000Z.ms.261045"]
    assert newest["body"]["stop_price"] == "59100" and newest["status"] == "pending"
    newest["status"] = "sent"
    trade_file(tmp_path, "b_trail_setups", "BTCUSDT", OPENED, "SHORT", "59100.0", "TRAIL")
    trade_file(tmp_path, "b_targets", "BTCUSDT", OPENED, "SHORT", "50000.0", "T1+T2")  # the other book: never read here
    vf.track("BTCUSDT", trail(side="FLAT", price=59150.0, at=bar(8)), st, d, 1006)   # the trail stop traded
    close = st["intents"]["BTCUSDT.20261126T090000Z.close.futures"]["body"]
    assert close == {"intent_id": "BTCUSDT.20261126T090000Z.close.futures", "market": "futures", "symbol": "BTCUSDT",
                     "action": "close", "reference_price": "59100"}
    assert not any(b["body"]["action"] == "reduce" for b in st["intents"].values())
    assert st["pos"]["BTCUSDT"] is None


def test_a_long_trail_setup_moves_up_and_closes_spot_and_futures(tmp_path):
    st, d = {}, str(tmp_path)
    vf.track("ETHUSDT", trail("ETHUSDT", side="FLAT", price=1700.0), st, d, 1)
    vf.track("ETHUSDT", trail("ETHUSDT", "LONG", 1700.0, 1650.0, 1702.0, at=OPENED), st, d, 2)
    vf.track("ETHUSDT", trail("ETHUSDT", "LONG", 1700.0, 1640.0, 1760.0, at=bar(1)), st, d, 3)   # a looser stop: never sent
    assert st.get("intents", {}) == {}
    vf.track("ETHUSDT", trail("ETHUSDT", "LONG", 1700.0, 1721.5, 1765.0, active=True, at=bar(2)), st, d, 4)
    (iid, it), = st["intents"].items()
    assert it["body"]["side"] == "BUY" and it["body"]["stop_price"] == "1721.5" and it["body"]["market"] == "futures"
    vf.track("ETHUSDT", trail("ETHUSDT", side="FLAT", price=1720.0, at=bar(3)), st, d, 5)
    closes = sorted(k for k in st["intents"] if ".close." in k)
    assert closes == ["ETHUSDT.20261126T090000Z.close.futures", "ETHUSDT.20261126T090000Z.close.spot"]
    assert st["intents"][iid]["status"] == "superseded"          # the move was still unsent when the setup ended


def test_a_stop_move_without_a_price_waits_and_the_memory_is_not_moved_on(tmp_path):
    st, d = {}, str(tmp_path)
    vf.track("BTCUSDT", trail(side="FLAT"), st, d, 1)
    vf.track("BTCUSDT", trail(at=OPENED), st, d, 2)
    why = vf.track("BTCUSDT", trail(stop=61000.0, price=None, at=bar(1)), st, d, 3)
    assert why == "no reference price for the exit"
    assert st["pos"]["BTCUSDT"]["stop_sent"] == "61500" and st.get("intents", {}) == {}


def test_the_changeover_closes_the_targets_setup_from_its_own_file_then_the_trail_setup_comes_by_the_book(tmp_path, on):
    st, d = {}, str(tmp_path)
    old = "2026-11-25T18:45:00Z"
    vf.track("BTCUSDT", targets(at=bar(0)), st, d, 1)
    vf.track("BTCUSDT", targets(at=bar(1)), st, d, 2)
    trade_file(tmp_path, "b_targets", "BTCUSDT", old, "SHORT", "61500.0", "STOP")
    vf.track("BTCUSDT", trail(side="FLAT", price=61600.0, at=bar(2)), st, d, 3)      # the flip: the market reads FLAT
    (iid, it), = st["intents"].items()
    assert iid == "BTCUSDT.20261125T184500Z.close.futures" and it["body"]["reference_price"] == "61500"
    it["status"] = "sent"
    new = bar(3)
    vf.track("BTCUSDT", trail(entry=61000.0, stop=62500.0, price=61000.0, opened=new, at=new, edge=6.0), st, d, 4)
    assert len(st["intents"]) == 1 and st["pos"]["BTCUSDT"]["exit_rule"] == "trail"
    b = vf.build_book(trail(entry=61000.0, stop=62500.0, price=61000.0, opened=new, at=new), new,
                      vf.remembered_lead(st, "BTCUSDT", {"opened_utc": new}))[0]["book"]
    assert b["exit_rule"] == "trail" and b["lead_pts"] == -6.0 and b["entry_window_open"] is True


# ------------------------------------------------------------------ one pass (the vault replaced by a list)
@pytest.fixture
def passes(tmp_path, monkeypatch):
    calls, answers = [], {}
    monkeypatch.setattr(vf, "load_config", lambda p: ({"port": 1, "secret_file": "s", "ca": "a", "cert": "c", "key": "k"},
                                                      None))
    monkeypatch.setattr(vf, "read_secret", lambda p: b"x" * 32)
    monkeypatch.setattr(vf, "client_tls", lambda ca, cert, key: (object(), None))

    def post(port, secret, tls, op, body, timeout=None):
        calls.append((op, json.loads(json.dumps(body))))
        key = body.get("intent", {}).get("intent_id") if op == "submit_intent" else None
        return answers.get(key, (200, {"ok": True}))

    monkeypatch.setattr(vf, "post", post)

    def run(markets, now):
        p = tmp_path / "setups.json"
        p.write_text(json.dumps({"markets": markets}), encoding="utf-8")
        lines = []
        out = vf.run(str(p), log=lines.append, environ={vf.CONFIG_ENV: "x", vf.SYMBOLS_ENV: "BTCUSDT"},
                     state_path=str(tmp_path / "state.json"), trades_dir=str(tmp_path), now=now)
        return out, lines

    return run, calls, answers


def test_a_pass_sends_the_stop_move_before_the_book(passes, on):
    run, calls, _ = passes
    run([trail(side="FLAT")], ep(bar(0)))
    run([trail(at=bar(1), opened=bar(1), price=60000.0)], ep(bar(1)))
    del calls[:]
    out, lines = run([trail(stop=59800.0, price=58500.0, active=True, window=False, at=bar(6), opened=bar(1))],
                     ep(bar(6)))
    assert [c[0] for c in calls] == ["submit_intent", "submit_book"]
    assert calls[0][1]["intent"]["action"] == "move_stop" and calls[0][1]["intent"]["stop_price"] == "59800"
    assert calls[1][1]["book"]["stop"] == "59800" and calls[1][1]["book"]["exit_rule"] == "trail"
    assert out["books"] == ["BTCUSDT"] and len(out["intents"]) == 1


def test_a_refused_stop_move_is_final_and_does_not_hold_the_book(passes, on):
    run, calls, answers = passes
    run([trail(side="FLAT")], ep(bar(0)))
    run([trail(at=bar(1), opened=bar(1), price=60000.0)], ep(bar(1)))
    iid = vf.ms_id("BTCUSDT", bar(1), bar(6))
    answers[iid] = (403, {"ok": False, "error": "stop_not_tighter"})
    del calls[:]
    out, lines = run([trail(stop=59800.0, price=58500.0, active=True, window=False, at=bar(6), opened=bar(1))],
                     ep(bar(6)))
    assert [c[0] for c in calls] == ["submit_intent", "submit_book"]              # the book still goes this step
    del calls[:]
    run([trail(stop=59800.0, price=58400.0, active=True, window=False, at=bar(7), opened=bar(1))], ep(bar(7)))
    assert [c[0] for c in calls] == ["submit_book"]                               # and the refused move is not retried


def test_a_trail_market_while_send_trail_is_off_tells_the_vault_flat_with_an_alarm(passes):
    run, calls, _ = passes
    run([targets(at=bar(0))], ep(bar(0)))
    del calls[:]
    out, lines = run([trail(at=bar(1), opened=bar(1), price=60000.0)], ep(bar(1)))
    assert any("ALARM BTCUSDT is on the trail voice while SEND_TRAIL is off" in x for x in lines)
    ops = [(op, (b.get("intent") or b.get("book")).get("action") or (b.get("book") or {}).get("side")) for op, b in calls]
    assert ops == [("submit_intent", "close"), ("submit_book", "FLAT")]            # the earlier setup is closed first
    assert "exit_rule" not in calls[-1][1]["book"]


# ------------------------------------------------------------------ the dry run
def test_the_preview_builds_what_would_go_and_posts_nothing(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("the preview must never post")

    monkeypatch.setattr(vf, "post", boom)
    assert vf.SEND_TRAIL is False
    d = str(tmp_path)
    p1 = vf.write_preview({"BTCUSDT": trail(at=OPENED, edge=8.3), "ETHUSDT": trail("ETHUSDT", side="FLAT", price=1700.0)},
                          d, now=ep(OPENED), generated_utc=OPENED)
    doc = json.load(open(p1, encoding="utf-8"))
    assert doc["schema"] == 1 and doc["intents"] == [] and set(doc["books"]) == {"BTCUSDT", "ETHUSDT"}
    assert doc["books"]["BTCUSDT"]["body"]["book"]["exit_rule"] == "trail"
    assert doc["books"]["BTCUSDT"]["body"]["book"]["lead_pts"] == -8.3
    assert doc["books"]["ETHUSDT"]["body"]["book"]["side"] == "FLAT"
    vf.write_preview({"BTCUSDT": trail(stop=59800.0, price=58500.0, active=True, window=False, at=bar(5)),
                      "ETHUSDT": trail("ETHUSDT", side="FLAT", price=1700.0)}, d, now=ep(bar(5)), generated_utc=bar(5))
    doc = json.load(open(p1, encoding="utf-8"))
    (it,) = doc["intents"]
    assert it["action"] == "move_stop" and it["stop_price"] == "59800" and it["ok"] is True
    assert it["intent_id"] == "BTCUSDT.20261126T090000Z.ms.261015" and it["made_utc"] == bar(5)
    assert doc["books"]["BTCUSDT"]["body"]["book"]["lead_pts"] == -8.3            # remembered from the opening
    assert not os.path.exists(os.path.join(d, "vault_feed_state.json"))           # the real memory is never touched


def test_the_preview_keeps_only_the_last_intents(tmp_path):
    prev = None
    for n in range(vf.PREVIEW_INTENTS + 12):
        m = trail(stop=61500.0 - n, price=59000.0 - n, active=n > 0, window=False, at=bar(n))
        prev = vf.preview({"BTCUSDT": m}, prev, trades_dir=str(tmp_path), now=ep(bar(n)))
    assert len(prev["intents"]) == vf.PREVIEW_INTENTS == len(prev["state"]["intents"])
    assert prev["intents"][-1]["stop_price"] == vf.dec_text(61500.0 - (vf.PREVIEW_INTENTS + 11))
