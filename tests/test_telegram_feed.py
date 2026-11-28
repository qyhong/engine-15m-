# -*- coding: utf-8 -*-
"""telegram_notify.feed_stale_update: one alert when a market's prices stop, one when they are back (27 Nov 2026)."""
from datetime import datetime, timezone

from engine15 import telegram_notify as tn

NOW = datetime(2026, 11, 27, 17, 20, tzinfo=timezone.utc)


def doc(gen="2026-11-27T17:03:16Z", **stale):
    ms = []
    for sym in ("BTCUSDT", "XAUUSD", "XAGUSD"):
        s = stale.get(sym, False)
        ms.append({"symbol": sym, "stale": s, "price_bar_utc": "2026-11-27T15:45:00Z" if s else "2026-11-27T17:00:00Z",
                   "bar_age_min": 78.3 if s else 3.3})
    return {"generated_utc": gen, "markets": ms}


def test_one_alert_when_prices_stop_then_quiet_then_back():
    st, card = tn.feed_stale_update(None, doc(), NOW)
    assert st == {} and card is None
    st, card = tn.feed_stale_update(st, doc(XAUUSD=True, XAGUSD=True), NOW)
    assert st == {"XAUUSD": "2026-11-27T15:45:00Z", "XAGUSD": "2026-11-27T15:45:00Z"}
    assert "Prices stopped" in card and "Gold" in card and "Silver" in card and "15:45 UTC (78 min)" in card
    assert "BTC" not in card
    st2, card = tn.feed_stale_update(st, doc(XAUUSD=True, XAGUSD=True), NOW)
    assert st2 == st and card is None                                   # said once
    st3, card = tn.feed_stale_update(st2, doc(XAGUSD=True), NOW)
    assert st3 == {"XAGUSD": "2026-11-27T15:45:00Z"}
    assert "Prices back" in card and "Gold" in card and "Silver" not in card and "Prices stopped" not in card


def test_an_old_or_odd_setups_file_is_not_read():
    prev = {"XAUUSD": "2026-11-27T15:45:00Z"}
    assert tn.feed_stale_update(prev, doc(gen="2026-11-27T16:00:00Z", BTCUSDT=True), NOW) == (prev, None)
    assert tn.feed_stale_update(prev, None, NOW) == (prev, None)
    assert tn.feed_stale_update(prev, {"generated_utc": "x", "markets": []}, NOW) == (prev, None)
    assert tn.feed_stale_update(prev, {"markets": "x"}, NOW) == (prev, None)


def test_unknown_keeps_what_we_had():
    d = doc()
    d["markets"][1]["stale"] = None                                      # cannot be told (an older engine: no key)
    st, card = tn.feed_stale_update({"XAUUSD": "2026-11-27T15:45:00Z"}, d, NOW)
    assert st == {"XAUUSD": "2026-11-27T15:45:00Z"} and card is None


def test_check_sends_it_with_the_other_alerts(monkeypatch, tmp_path):
    import json
    p = tmp_path / "setups.json"
    p.write_text(json.dumps(doc(XAUUSD=True)), encoding="utf-8")
    monkeypatch.setattr(tn, "SETUPS", str(p))
    monkeypatch.setattr(tn, "PAGE", str(tmp_path / "none.json"))
    monkeypatch.setattr(tn, "SCORE", str(tmp_path / "none2.json"))
    st, ev = tn.check({}, None, send=False, now=NOW)
    assert st["feed_stale"] == {"XAUUSD": "2026-11-27T15:45:00Z"}
    assert any("Prices stopped" in e for e in ev)
