# -*- coding: utf-8 -*-
"""telegram_notify: alerts from changes, the chat lock, the daily summary once a day, and the key never leaking."""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import telegram_notify as tn  # noqa: E402

NOW = datetime(2026, 11, 17, 0, 1, tzinfo=timezone.utc)


def page(gen="2026-11-17T00:00:00Z"):
    return {"generated_utc": gen, "version": "think15-v5.2.3",
            "assets": {"BTCUSDT": {"short": "BTC", "position": "SHORT", "edge_pts": -4.1,
                                   "trade": {"unrealized_usd": 1200.0},
                                   "closed_trades": [{"side": -1, "pnl_usd": 250.0, "time_out": "2026-11-16 12:00:00+00:00"}]}},
            "playbook": {"playbook5": {"p5_rlq": {"totals": {"trades": 5, "net_usd": 211.5}}}}}


def score(trail=22, net=4978.0, verdict="too few trades to judge (22 of 30)"):
    return {"rows": [{"book": "b_trail", "title": "Shadow: b_trail", "trades": trail, "net_usd": net, "verdict": verdict},
                     {"book": "p1_liqhunt", "title": "Strategy: p1", "trades": 66, "net_usd": -1368.0, "verdict": "behind"}]}


def test_alerts_from_changes():
    c0, v0, n0 = tn.counts(score(22, 4978.0), page())
    prev = {"c": c0, "v": v0, "net": n0, "refits": [1, 1], "stale": False}
    c1, v1, n1 = tn.counts(score(23, 5200.0), page())
    ev = tn.events(prev, {"c": c1, "v": v1, "net": n1, "refits": [2, 1]}, page(), NOW)
    assert any("B trail (shadow)" in e and "closed 1 trade" in e and "+$222" in e for e in ev)
    assert any("Phase 5" in e for e in ev)
    c2, v2, n2 = tn.counts(score(30, 6000.0), page())
    ev2 = tn.events({"c": c1, "v": v1, "net": n1, "refits": [2, 1]}, {"c": c2, "v": v2, "net": n2, "refits": [2, 1]}, page(), NOW)
    assert any("reached" in e and "30 trades" in e and "Verdict due" in e for e in ev2)


def test_stale_and_fresh_again():
    old = page("2026-11-16T23:00:00Z")
    ev = tn.events({"c": None}, {"c": {}, "v": {}, "net": {}, "refits": []}, old, NOW)
    assert any("Engine quiet" in e for e in ev)
    ev2 = tn.events({"c": None, "stale": True}, {"c": {}, "v": {}, "net": {}, "refits": []}, page(), NOW)
    assert any("Engine back" in e for e in ev2)


def test_summary_text():
    s = tn.summary(page(), score(), NOW)
    assert "daily summary" in s and "BTC" in s and "SHORT" in s and "+$1,200" in s and "B trail" in s and "+$250" in s and "<pre>" in s


def test_chat_lock_summary_once_and_key_never_printed(monkeypatch, tmp_path, capsys):
    sent = []
    secret = "123456:SECRET-TEST-KEY"

    def fake_call(tok, method, payload, timeout=20):
        assert tok == secret
        if method == "getUpdates":
            return {"ok": True, "result": [{"update_id": 7, "message": {"chat": {"id": 42}, "text": "/start"}},
                                           {"update_id": 8, "message": {"chat": {"id": 99}, "text": "/start"}}]}
        sent.append((method, payload.get("chat_id"), payload.get("text", "")))
        return {"ok": True}
    monkeypatch.setattr(tn, "_call", fake_call)
    monkeypatch.setattr(tn, "_load", lambda p, d=None: page() if p.endswith("page.json") else score())
    monkeypatch.setattr(tn, "refit_marks", lambda: [0, 0])
    st, _ = tn.check({}, secret, now=NOW)
    assert st["chat_id"] == 42 and st["update_offset"] == 9
    assert all(chat == 42 for _m, chat, _t in sent)                  # the second chat (99) is ignored
    assert any("daily summary" in t for _m, _c, t in sent) and st["summary_day"] == "2026-11-17"
    n = len(sent)
    st, _ = tn.check(st, secret, now=NOW)                            # same day: no second summary
    assert not any("daily summary" in t for _m, _c, t in sent[n:])
    assert secret not in capsys.readouterr().out


def test_no_key_file_means_waiting(tmp_path, monkeypatch):
    monkeypatch.setattr(tn, "TOKEN_FILE", str(tmp_path / "missing"))
    assert tn.token() is None


def test_disk_low_alert_once_then_ok(monkeypatch):
    monkeypatch.setattr(tn, "_load", lambda p, d=None: page() if p.endswith("page.json") else score())
    monkeypatch.setattr(tn, "refit_marks", lambda: [0, 0])
    monkeypatch.setattr(tn, "disk_free_gb", lambda path=None: 1.5)
    st, ev = tn.check({}, None, now=NOW)
    assert any("Server disk low" in e for e in ev) and st["disk_low"]
    st, ev = tn.check(st, None, now=NOW)
    assert not any("Server disk low" in e for e in ev)                # once, not every check
    monkeypatch.setattr(tn, "disk_free_gb", lambda path=None: 6.0)
    st, ev = tn.check(st, None, now=NOW)
    assert any("disk OK again" in e for e in ev) and not st["disk_low"]
