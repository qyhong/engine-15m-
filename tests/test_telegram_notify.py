# -*- coding: utf-8 -*-
"""telegram_notify: alerts from changes, the chat lock, the daily summary once a day, and the key never leaking."""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from engine15 import telegram_notify as tn  # noqa: E402

NOW = datetime(2026, 11, 17, 0, 1, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def no_real_records(monkeypatch, tmp_path):
    """No test reads a real journal or bar file: the calibration card looks into an empty folder."""
    monkeypatch.setattr(tn, "JOURNAL", str(tmp_path / "journal"))
    monkeypatch.setattr(tn, "BARS", str(tmp_path / "data"))


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


# ------------------------------------------------------------------ data health and the weekly calibration card
def feeds_page(t, **readings):
    p = page()
    p["assets"]["BTCUSDT"].update(time=t, cards=[{"card": c.replace("_", " "), "reading": r} for c, r in readings.items()])
    p["assets"]["SPX"] = {"short": "S&P", "position": "FLAT", "time": "2026-11-13 21:00",      # closed since Friday
                          "cards": [{"card": "Options mood (put/call)", "reading": "No read."}]}
    return p


def calib_result(n=120):
    table = [{"said": "45-50", "n": 80, "avg_said_pct": 48.7, "came_pct": 46.2},
             {"said": "50-55", "n": 40, "avg_said_pct": 51.2, "came_pct": 55.0}]
    return {"since": "2026-11-10", "until": "2026-11-16", "days": 7, "partial": False, "min_ind": 100, "markets": {
        "BTCUSDT": {"n": n, "right": 70, "wrong": 44, "neither": 6, "hit_pct": 61.4, "source": "bars", "verdict": "too few",
                    "ind_n": 33, "table": table, "brier": 0.5462, "brier_base": 0.5638},
        "XAUUSD": {"n": 369 if n else 0, "right": 158, "wrong": 211, "neither": 0, "hit_pct": 42.8, "source": "journal",
                   "verdict": "n/a", "why": "no readable price bars (xauusd_15m.csv)", "table": [], "brier": None,
                   "brier_base": None},
        "SPX": {"n": 0, "right": 0, "wrong": 0, "neither": 0, "hit_pct": None, "source": "journal", "verdict": "n/a"}},
        "pooled": {"n": n, "hit_pct": 61.4, "brier": 0.5462, "brier_base": 0.5638, "table": table}}


def bot(monkeypatch, updates=()):
    """A fake Telegram and a fake calibration read. -> (sent messages, the calibration reads made, the page holder)."""
    sent, reads, holder = [], [], {"page": page(), "updates": list(updates)}

    def fake_call(tok, method, payload, timeout=20):
        if method == "getUpdates":
            ups, holder["updates"] = holder["updates"], []
            return {"ok": True, "result": [{"update_id": 10 + k, "message": {"chat": {"id": c}, "text": t}}
                                           for k, (c, t) in enumerate(ups)]}
        sent.append((payload.get("chat_id"), payload.get("text", "")))
        return {"ok": True}

    def fake_read(now=None):
        reads.append(now)
        return calib_result()
    monkeypatch.setattr(tn, "_call", fake_call)
    monkeypatch.setattr(tn, "_load", lambda p, d=None: holder["page"] if p.endswith("page.json") else score())
    monkeypatch.setattr(tn, "refit_marks", lambda: [0, 0])
    monkeypatch.setattr(tn, "disk_free_gb", lambda path=None: 50.0)
    monkeypatch.setattr(tn, "calibration_now", fake_read)
    return sent, reads, holder


def test_weekly_calibration_once_per_iso_week(monkeypatch):
    sent, reads, _h = bot(monkeypatch)
    st = {"chat_id": 42}
    at = lambda d, h=0, m=1: datetime(2026, 11, d, h, m, tzinfo=timezone.utc)   # noqa: E731
    for now in (at(16), at(16, 0, 2), at(16, 12), at(17), at(18), at(22, 23, 59)):   # Monday 16 Nov to Sunday 22 Nov
        st, _ = tn.check(st, "k", now=now)
    cal = [i for i, (_c, t) in enumerate(sent) if "live calibration" in t]
    assert cal == [1] and len(reads) == 1 and st["calib_week"] == "2026-W47"   # right after Monday's summary, once
    assert sum("daily summary" in t for _c, t in sent) == 4          # the daily summary still goes out every day
    st, _ = tn.check(st, "k", now=at(23))                            # the next Monday
    assert sum("live calibration" in t for _c, t in sent) == 2 and st["calib_week"] == "2026-W48"
    st2, _ = tn.check({"chat_id": 42}, "k", now=at(18))              # a bot started midweek: that week's first summary
    assert st2["calib_week"] == "2026-W47" and sum("live calibration" in t for _c, t in sent) == 3


def test_weekly_calibration_with_no_data_or_a_failure_is_not_retried(monkeypatch):
    sent, reads, _h = bot(monkeypatch)

    def nothing(now=None):
        reads.append(now)
        return calib_result(n=0)
    monkeypatch.setattr(tn, "calibration_now", nothing)
    st, _ = tn.check({"chat_id": 42}, "k", now=NOW)
    st, _ = tn.check(st, "k", now=NOW)
    assert len(reads) == 1 and not any("live calibration" in t for _c, t in sent)   # nothing graded: no card, no retry

    def boom(now=None):
        reads.append(now)
        raise OSError("disk")
    monkeypatch.setattr(tn, "calibration_now", boom)
    st, _ = tn.check({"chat_id": 42}, "k", now=NOW)
    st, _ = tn.check(st, "k", now=NOW)
    assert len(reads) == 2 and st["summary_day"] == "2026-11-17"     # the summary still went out; one try only
    assert sum("daily summary" in t for _c, t in sent) == 2


def test_real_read_of_an_empty_journal_sends_no_card(monkeypatch):
    sent, _reads, _h = bot(monkeypatch)
    monkeypatch.undo()                                               # the real calibration_now ...
    monkeypatch.setattr(tn, "JOURNAL", os.path.join(os.path.dirname(__file__), "no_such_journal"))
    monkeypatch.setattr(tn, "BARS", os.path.join(os.path.dirname(__file__), "no_such_data"))
    res = tn.calibration_now(NOW)                                    # ... on a folder that does not exist
    assert res["markets"] == {} and res["days"] == 0
    assert "No graded live forecasts" in tn.calibration_card(res)


def test_chat_lock_on_health_and_calibration(monkeypatch):
    sent, reads, holder = bot(monkeypatch, [(99, "/health"), (99, "/calibration"), (99, "/summary")])
    st = {"chat_id": 42, "summary_day": "2026-11-17", "calib_week": "2026-W47"}
    st, _ = tn.check(st, "k", now=NOW)
    assert sent == [] and reads == []                                # a stranger gets no answer and causes no read
    holder["updates"] = [(42, "/health"), (42, "/calibration"), (99, "/calibration")]
    st, _ = tn.check(st, "k", now=NOW)
    assert [c for c, _t in sent] == [42, 42] and len(reads) == 1
    assert "data health" in sent[0][1] and "live calibration" in sent[1][1]
    assert st["update_offset"] == 13


def test_data_alert_once_in_one_message_then_recovered(monkeypatch):
    sent, _reads, holder = bot(monkeypatch)
    st = {"chat_id": 42, "summary_day": "2026-11-17", "calib_week": "2026-W47"}
    ts = ["2026-11-17 %02d:%02d" % divmod(15 * k, 60) for k in range(1, 40)]
    good = dict(Korea_premium="Upbit +2.1%.", Spot_vs_perp_leadership="Spot 12%.", Regime="RANGE (daily).")
    dead = dict(Korea_premium="No Korea premium read for BTC at this close.",
                Spot_vs_perp_leadership="No spot against perpetual read for BTC at this close.", Regime="RANGE (daily).")
    holder["page"] = feeds_page(ts[0], **good)
    st, ev = tn.check(st, "k", now=NOW)
    assert not sent
    for k in range(1, 12):
        holder["page"] = feeds_page(ts[k], **dead)
        for _ in range(3):                                           # the bot checks more often than the market closes
            st, ev = tn.check(st, "k", now=NOW)
    alerts = [t for _c, t in sent if "Data feed silent" in t]
    assert len(alerts) == 1 and len(sent) == 1                       # two cards, ONE message, once
    assert "Korea premium" in alerts[0] and "Spot vs perp leadership" in alerts[0] and "8 closes" in alerts[0]
    assert "S&amp;P" not in alerts[0] and "Options mood" not in alerts[0]   # the closed market: no alarm
    line = [ln for ln in tn.summary(holder["page"], score(), NOW, st["health"]).split("\n") if " Data: " in ln]
    assert line == [tn.WARN + u" Data: 1 of 3 cards reading · silent: Korea premium, Spot vs perp leadership"]
    card = tn.health_card(st["health"])
    assert "1 of 3 cards reading" in card and "since 17 Nov 00:30 UTC" in card and "Never read here" in card
    holder["page"] = feeds_page(ts[12], **good)
    st, ev = tn.check(st, "k", now=NOW)
    assert len(sent) == 2 and "Data back" in sent[1][1] and "Korea premium" in sent[1][1] and "Data feed silent" not in sent[1][1]
    assert tn.OK + " Data: 3 of 3 cards reading" in tn.summary(holder["page"], score(), NOW, st["health"])
    st, ev = tn.check(st, "k", now=NOW)
    assert len(sent) == 2


def test_feed_outage_is_one_capped_message():
    gone = [("BTCUSDT", "Card %02d (detail)" % k, "2026-11-17 01:00", 8) for k in range(30)]
    msg = tn.health_alert(gone, [("ETHUSDT", "Fear and Greed", "2026-11-16 20:00", 12)])
    assert msg.count(u"•") == tn.LIST_MAX + 1 and "+22 more" in msg and "Data back" in msg and "/health" in msg
    assert "Card 00: BTC" in msg and "(detail)" not in msg
    assert tn.health_alert([], []) is None


def test_calibration_and_health_card_text():
    card = tn.calibration_card(calib_result())
    assert "live calibration" in card and "Live data since 10 Nov 2026" in card and "paper only" in card
    assert "not proof of an edge" in card and "too few" in card and "most so far: BTC 33" in card
    assert "Gold    369 43% n/a *" in card and "* Gold: no readable price bars" in card and "S&amp;P" not in card
    assert "Brier 0.546 against 0.564" in card
    for block in card.split("<pre>")[1:]:
        assert all(len(ln) <= 30 for ln in block.split("</pre>")[0].split("\n"))   # a phone screen
    wide = calib_result()
    wide["markets"]["BTCUSDT"].update(n=8640, verdict="underconfident")
    assert "BTC    8640 61% underconfident" in tn.calibration_card(wide)
    assert "No graded live forecasts" in tn.calibration_card({"markets": {}})
    assert "No cards seen yet" in tn.health_card(None) and tn.health_line(None) is None
