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
    monkeypatch.setattr(tn, "LIVE", str(tmp_path / "live"))          # ... and the signal preview keeps its files there
    monkeypatch.setattr(tn, "SIGNALS_STATE", str(tmp_path / "data" / "signals_state.json"))
    monkeypatch.setattr(tn, "SIGNALS_LOG", str(tmp_path / "data" / "signals_log.jsonl"))
    monkeypatch.setattr(tn, "_SIGNALS_ERR", [None])
    monkeypatch.setattr(tn, "_SIGNALS_UNREAD", [""])
    monkeypatch.setattr(tn, "VAULT_STATE", str(tmp_path / "data" / "vault_feed_state.json"))   # never the real feed's file
    monkeypatch.setattr(tn, "_VAULT_ERR", [None])

    monkeypatch.setattr(tn, "EARLY_STATE", str(tmp_path / "data" / "signals_early_state.json"))     # H56 early preview
    monkeypatch.setattr(tn, "EARLY_LOG", str(tmp_path / "data" / "signals_early_log.jsonl"))
    monkeypatch.setattr(tn, "_EARLY_ERR", [None])
    monkeypatch.setattr(tn, "CHECK_REPORT", str(tmp_path / "data" / "check_report.json"))       # never the real report
    monkeypatch.setattr(tn, "_CHECK_ERR", [None])


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
    assert any("B trail (shadow)" in e and "closed 1 trade" in e and "+$3,330" in e for e in ev)
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
    assert "daily summary" in s and "BTC" in s and "SHORT" in s and "+$18.0k" in s and "B trail" in s and "+$3,750" in s and "<pre>" in s


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
    st = {"chat_id": 42, "summary_day": "2026-11-17", "calib_week": "2026-W47", "rank_week": "2026-W47"}
    st, _ = tn.check(st, "k", now=NOW)
    assert sent == [] and reads == []                                # a stranger gets no answer and causes no read
    holder["updates"] = [(42, "/health"), (42, "/calibration"), (99, "/calibration")]
    st, _ = tn.check(st, "k", now=NOW)
    assert [c for c, _t in sent] == [42, 42] and len(reads) == 1
    assert "data health" in sent[0][1] and "live calibration" in sent[1][1]
    assert st["update_offset"] == 13


def test_data_alert_once_in_one_message_then_recovered(monkeypatch):
    sent, _reads, holder = bot(monkeypatch)
    st = {"chat_id": 42, "summary_day": "2026-11-17", "calib_week": "2026-W47", "rank_week": "2026-W47"}
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


# ------------------------------------------------------------------ the subscriber signal preview (H53; signals.py)
def signal_page(view, as_of, gen="2026-11-17T00:00:00Z"):
    p = page(gen)
    p["markets"] = {"crypto": ["BTCUSDT"]}
    p["assets"]["BTCUSDT"].update(market_group="crypto", structure="mixed",
                                  voices=[{"title": "Momentum", "pull_pts": 1.0}, {"title": "Kronos forecast", "pull_pts": 5.0}])
    p["shadows"] = {"books": {"b_targets": {"assets": {"BTCUSDT": view}}}, "markets": {"crypto": {"as_of_utc": as_of}}}
    return p


LONG = {"status": "LONG", "entry": 100.0, "stop": 98.0, "opened_utc": "2026-11-17 00:00", "target_1": 103.0,
        "target_2": 105.0, "t1_taken": False}


def signal_bot(monkeypatch, tmp_path, refuse_replies=False):
    """A fake Telegram that numbers its messages. -> (the sendMessage payloads, the page holder)."""
    calls, holder = [], {"page": signal_page({"status": "FLAT"}, "2026-11-16 23:45"), "updates": []}

    def fake_call(tok, method, payload, timeout=20):
        if method == "getUpdates":
            ups, holder["updates"] = holder["updates"], []
            return {"ok": True, "result": [{"update_id": 10 + k, "message": {"chat": {"id": c}, "text": t}}
                                           for k, (c, t) in enumerate(ups)]}
        calls.append(dict(payload))
        if refuse_replies and "reply_to_message_id" in payload:
            return {"ok": False, "description": "Bad Request: message to be replied not found"}
        return {"ok": True, "result": {"message_id": 700 + len(calls)}}
    monkeypatch.setattr(tn, "_call", fake_call)
    monkeypatch.setattr(tn, "_load", lambda p, d=None: holder["page"] if p.endswith("page.json") else score())
    monkeypatch.setattr(tn, "refit_marks", lambda: [0, 0])
    monkeypatch.setattr(tn, "disk_free_gb", lambda path=None: 50.0)
    os.makedirs(str(tmp_path / "data"), exist_ok=True)
    return calls, holder


def bars_file(tmp_path, rows):
    with open(str(tmp_path / "data" / "btcusdt_15m.csv"), "w") as fh:
        fh.write("ts_ms,open,high,low,close,volume,taker_buy\n")
        for k, (o, h, l, c) in enumerate(rows):
            fh.write("%d,%s,%s,%s,%s,1.0,\n" % (1794873600000 + 900000 * k, o, h, l, c))


def at17(h, m):
    return datetime(2026, 11, 17, h, m, tzinfo=timezone.utc)


def run_to_fill(monkeypatch, tmp_path, **kw):
    calls, holder = signal_bot(monkeypatch, tmp_path, **kw)
    st = {"chat_id": 42, "summary_day": "2026-11-16", "calib_week": "2026-W47", "rank_week": "2026-W47"}
    st, _ = tn.check(st, "k", now=datetime(2026, 11, 16, 23, 50, tzinfo=timezone.utc))   # the preview starts, book flat
    assert calls == [] and os.path.exists(tn.SIGNALS_STATE)
    st["summary_day"] = "2026-11-17"
    holder["page"] = signal_page(dict(LONG), "2026-11-17 00:15")
    bars_file(tmp_path, [(101, 101.5, 100.5, 101)])
    st, _ = tn.check(st, "k", now=at17(0, 16))                       # the book shows a new position: the signal card
    holder["page"] = signal_page(dict(LONG), "2026-11-17 00:45", "2026-11-17T00:45:30Z")
    bars_file(tmp_path, [(101, 101.5, 100.5, 101), (101, 101.5, 100.5, 101), (100.5, 101, 99.5, 100.2)])
    st, _ = tn.check(st, "k", now=at17(0, 46))                       # the bar after bar A holds the entry: filled
    return calls, holder, st


def test_signal_preview_goes_to_the_owner_chat_only_under_the_preview_line(monkeypatch, tmp_path):
    assert tn.SIGNALS_PREVIEW is True and tn.SIGNALS_CHANNEL is None
    calls, holder, st = run_to_fill(monkeypatch, tmp_path)
    assert len(calls) == 2 and all(c["chat_id"] == 42 for c in calls)
    assert all(c["text"].startswith(u"\U0001f9ea Subscriber preview\n") for c in calls)
    assert "BUY BTC" in calls[0]["text"] and "BTC-1117-01" in calls[0]["text"] and "reply_to_message_id" not in calls[0]
    assert "strongest on the buy side: Momentum." in calls[0]["text"]
    assert "Entry filled" in calls[1]["text"] and calls[1]["reply_to_message_id"] == 701     # a reply to the card itself
    for c in calls:
        low = c["text"].lower()
        assert "b_targets" not in low and "shadow" not in low and "kronos" not in low and "$" not in c["text"]
        assert "alphaprediction" not in low and c["text"].endswith("not financial advice.</i>")
    st, _ = tn.check(st, "k", now=at17(0, 47))                       # the same records again: nothing is sent twice
    assert len(calls) == 2
    assert "open" not in st and "seen" not in st                     # the bot's own state does not carry the signals


def test_signal_follow_up_falls_back_to_a_plain_message_when_the_reply_fails(monkeypatch, tmp_path):
    calls, _holder, _st = run_to_fill(monkeypatch, tmp_path, refuse_replies=True)
    assert len(calls) == 3 and calls[1]["reply_to_message_id"] == 701
    assert "reply_to_message_id" not in calls[2] and calls[2]["text"] == calls[1]["text"] and "Entry filled" in calls[2]["text"]
    assert calls[2]["parse_mode"] == "HTML"


def test_an_exception_in_signals_code_never_blocks_the_admin_alerts(monkeypatch, tmp_path, capsys):
    calls, holder = signal_bot(monkeypatch, tmp_path)

    def boom(*a, **k):
        raise RuntimeError("signals are broken")
    monkeypatch.setattr(tn.signals, "run", boom)
    monkeypatch.setattr(tn, "disk_free_gb", lambda path=None: 1.5)
    st, ev = tn.check({"chat_id": 42}, "k", now=NOW)
    texts = [c["text"] for c in calls]
    assert any("Server disk low" in t for t in texts) and any("daily summary" in t for t in texts)
    assert st["summary_day"] == "2026-11-17" and st["disk_low"] and st["checked_utc"]
    st, ev = tn.check(st, "k", now=NOW)
    st, ev = tn.check(st, "k", now=NOW)
    out = capsys.readouterr().out
    assert out.count("signals failed (check: RuntimeError)") == 1    # logged once, not every minute
    assert "signals are broken" not in out
    assert tn._signals_guard("x", lambda: 7) == 7


def test_signal_commands_answer_the_locked_chat_only(monkeypatch, tmp_path):
    calls, holder, st = run_to_fill(monkeypatch, tmp_path)
    n = len(calls)
    holder["updates"] = [(99, "/signals"), (99, "/record")]
    st, _ = tn.check(st, "k", now=at17(0, 48))
    assert len(calls) == n                                           # a stranger gets no answer
    holder["updates"] = [(42, "/signals"), (42, "/record")]
    st, _ = tn.check(st, "k", now=at17(0, 49))
    a, b = calls[n]["text"], calls[n + 1]["text"]
    assert a.startswith(u"\U0001f9ea Subscriber preview\n") and "open now" in a and "BTC-1117-01 BUY       in trade" in a
    assert "the record" in b and "Signals sent                 1" in b and "Filled                1 (100%)" in b
    assert "Verdict: no trades yet." in b and "Live since 16 Nov 2026" in b
    assert calls[n]["chat_id"] == calls[n + 1]["chat_id"] == 42


def test_daily_recap_goes_with_the_daily_summary_once_the_preview_has_started(monkeypatch, tmp_path):
    calls, holder, st = run_to_fill(monkeypatch, tmp_path)
    n = len(calls)
    holder["page"] = signal_page(dict(LONG), "2026-11-18 00:00", "2026-11-18T00:00:30Z")
    st, _ = tn.check(st, "k", now=datetime(2026, 11, 18, 0, 1, tzinfo=timezone.utc))
    texts = [c["text"] for c in calls[n:]]
    assert len(texts) == 2 and "daily summary" in texts[0] and not texts[0].startswith(tn.SIGNALS_HEAD)
    assert texts[1].startswith(tn.SIGNALS_HEAD) and "daily recap" in texts[1] and "Tue 17 Nov (UTC)" in texts[1]
    assert "BTC-1117-01 BUY       in trade" in texts[1] and "Live since 16 Nov 2026" in texts[1]
    st, _ = tn.check(st, "k", now=datetime(2026, 11, 18, 0, 2, tzinfo=timezone.utc))
    assert len(calls) == n + 2                                       # once a day


def test_no_signal_files_and_no_recap_before_the_page_carries_the_book(monkeypatch, tmp_path):
    sent, _reads, _h = bot(monkeypatch)                              # the old page: no shadow books on it
    st, _ = tn.check({"chat_id": 42, "calib_week": "2026-W47", "rank_week": "2026-W47"}, "k", now=NOW)
    assert len(sent) == 1 and "daily summary" in sent[0][1]
    assert not os.path.exists(tn.SIGNALS_STATE) and not os.path.exists(tn.SIGNALS_LOG)


def test_a_bar_file_caught_mid_write_is_said_once_and_changes_nothing(monkeypatch, tmp_path, capsys):
    calls, holder, st = run_to_fill(monkeypatch, tmp_path)
    state = open(tn.SIGNALS_STATE).read()
    open(str(tmp_path / "data" / "btcusdt_15m.csv"), "w").close()    # caught empty, as the engine rewrites it
    holder["page"] = signal_page(dict(LONG), "2026-11-17 01:00", "2026-11-17T01:00:30Z")
    for m in (1, 2, 3):
        st, _ = tn.check(st, "k", now=at17(1, m))
    assert open(tn.SIGNALS_STATE).read() == state and len(calls) == 2
    assert capsys.readouterr().out.count("bars not readable now, will retry (BTCUSDT)") == 1
    bars_file(tmp_path, [(101, 101.5, 100.5, 101), (101, 101.5, 100.5, 101), (100.5, 101, 99.5, 100.2), (101, 103.5, 100.5, 103)])
    st, _ = tn.check(st, "k", now=at17(1, 4))                        # whole again: the bar is read now
    assert len(calls) == 3 and "Target 1 hit" in calls[2]["text"] and calls[2]["reply_to_message_id"] == 701


def test_dollars_display_at_15x_and_tables_stay_narrow():
    assert tn.DISPLAY_X == 15
    assert tn._usd(222.0) == "+$3,330" and tn._usd(-1368.0) == "-$20,520"
    assert tn._usd_short(60.0) == "+$900" and tn._usd_short(1000.0) == "+$15.0k" and tn._usd_short(-9120.0) == "-$137k"
    assert tn._usd_short(80000.0) == "+$1.20M"
    assert max(len(tn._usd_short(x)) for x in (9.5, 123.4, -1368.0, 12400.0, -99999.0)) <= 9


# ------------------------------------------------------------------ VIP vault exit instructions (the feed's state, read only)
import json  # noqa: E402

VNOW = datetime(2026, 11, 19, 10, 30, tzinfo=timezone.utc)
MADE = VNOW.timestamp() - 600
VST = {"chat_id": 42, "summary_day": "2026-11-19", "calib_week": "2026-W47", "rank_week": "2026-W47"}


def intent(sym, opened, action, market, status, ref="65203.2", **extra):
    iid = "%s.%s.%s.%s" % (sym, opened, action, market)
    body = dict({"intent_id": iid, "market": market, "symbol": sym, "action": action, "reference_price": ref}, **extra)
    return iid, {"body": body, "status": status, "made": MADE, "seq": 1}


def vault_state(intents, book=None, extra=None):
    os.makedirs(os.path.dirname(tn.VAULT_STATE), exist_ok=True)
    doc = dict({"intents": dict(intents), "pos": {}, "seq": len(intents)}, **(extra or {}))
    if book is not None:
        doc["book"] = book
    with open(tn.VAULT_STATE, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)


def vault_bot(monkeypatch, ok=True):
    sent, holder = [], {"ok": ok}

    def fake_call(tok, method, payload, timeout=20):
        if method == "getUpdates":
            return {"ok": True, "result": []}
        sent.append(payload.get("text", ""))
        return {"ok": holder["ok"]}
    monkeypatch.setattr(tn, "_call", fake_call)
    monkeypatch.setattr(tn, "_load", lambda p, d=None: page("2026-11-19T10:29:00Z") if p.endswith("page.json") else score())
    monkeypatch.setattr(tn, "refit_marks", lambda: [0, 0])
    monkeypatch.setattr(tn, "disk_free_gb", lambda path=None: 50.0)
    return sent, holder


def vault_cards(sent):
    return [t for t in sent if "VIP vault" in t]


def three():
    a = intent("BTCUSDT", "20261118T101500Z", "close", "spot", "sent")
    b = intent("ETHUSDT", "20261118T091500Z", "reduce", "futures", "refused", ref="3120.55", fraction=0.5)
    c = intent("ETHUSDT", "20261118T091500Z", "move_stop", "futures", "expired", ref="3120.55", side="SELL",
               stop_price="3180.4")
    return dict([a, b, c])


def test_vault_accepted_refused_given_up_one_card_each_never_twice(monkeypatch):
    sent, _h = vault_bot(monkeypatch)
    vault_state(three())
    st, ev = tn.check(dict(VST), "k", now=VNOW)
    cards = vault_cards(sent)
    assert len(cards) == 3 and all(c.startswith(u"\U0001f3e6 <b>VIP vault · exit instruction</b>") for c in cards)
    close, = [c for c in cards if "BTC spot" in c]
    assert "<b>close the position</b>" in close and "Reference price 65,203.2" in close
    assert "Setup: long opened 18 Nov 10:15 UTC" in close and "Accepted by the vault" in close
    reduce_, = [c for c in cards if "take half (reduce 50%)" in c]
    assert "ETH futures" in reduce_ and "Refused:" in reduce_ and "Setup: short opened 18 Nov 09:15 UTC" in reduce_
    stop, = [c for c in cards if "move the stop to the entry at 3,180.4" in c]
    assert "Not delivered for 24 h, given up" in stop and "Made 19 Nov 10:20 UTC" in stop
    assert set(st["vault_alerted"]) == set(three())
    st, ev = tn.check(st, "k", now=VNOW)                             # the same file again: nothing new
    assert len(vault_cards(sent)) == 3
    st = json.loads(json.dumps(st))                                  # a restart from the saved bot state
    st, ev = tn.check(st, "k", now=VNOW)
    assert len(vault_cards(sent)) == 3


def test_vault_pending_waits_then_alerts_once_when_final(monkeypatch):
    sent, _h = vault_bot(monkeypatch)
    iid, it = intent("BTCUSDT", "20261118T101500Z", "close", "futures", "pending")
    vault_state({iid: it})
    st, _ = tn.check(dict(VST), "k", now=VNOW)
    assert vault_cards(sent) == []
    it.update(status="refused", why="refused 400 stale_reference")   # a code, if the feed ever keeps one
    vault_state({iid: it})
    st, _ = tn.check(st, "k", now=VNOW)
    st, _ = tn.check(st, "k", now=VNOW)
    cards = vault_cards(sent)
    assert len(cards) == 1 and "Refused: refused 400 stale_reference" in cards[0]
    assert "Setup: short opened" in cards[0]                          # a futures-only setup is a short book


def test_vault_card_retried_when_telegram_fails_and_old_intents_skipped(monkeypatch):
    sent, holder = vault_bot(monkeypatch, ok=False)
    iid, it = intent("BTCUSDT", "20261118T101500Z", "close", "spot", "sent")
    old_id, old = intent("ETHUSDT", "20261110T101500Z", "close", "spot", "sent")
    old["made"] = VNOW.timestamp() - 5 * 86400                        # finished days ago: no card after a fresh start
    vault_state({iid: it, old_id: old})
    st, _ = tn.check(dict(VST), "k", now=VNOW)
    assert st.get("vault_alerted") == {}                              # not delivered: not remembered
    holder["ok"], sent[:] = True, []
    st, _ = tn.check(st, "k", now=VNOW)
    assert len(vault_cards(sent)) == 1 and list(st["vault_alerted"]) == [iid]


def test_vault_memory_is_capped(monkeypatch):
    vault_bot(monkeypatch)
    vault_state({})
    now_s = VNOW.timestamp()
    st = {"vault_alerted": dict(("X.%d" % k, now_s - k) for k in range(tn.VAULT_MEMORY_MAX + 50))}
    st["vault_alerted"]["ancient"] = now_s - tn.VAULT_MEMORY_S - 1
    tn.vault_check(st, "k", 42, VNOW)
    assert len(st["vault_alerted"]) == tn.VAULT_MEMORY_MAX and "ancient" not in st["vault_alerted"]
    assert "X.0" in st["vault_alerted"]                              # the newest are kept


@pytest.mark.parametrize("content", [None, b"", b"{not json", b"[1, 2]", b'{"intents": [1, 2]}',
                                     b'{"intents": {"a": 5, "b": {"status": "sent", "made": "x"}, '
                                     b'"c": {"status": "sent", "made": 1}, "d": {"status": "sent", "made": 1e12}}}',
                                     b"\xff\xfe garbage"])
def test_vault_missing_or_garbled_file_no_card_no_crash(monkeypatch, capsys, content):
    sent, _h = vault_bot(monkeypatch)
    monkeypatch.setattr(tn, "disk_free_gb", lambda path=None: 1.5)
    if content is not None:
        os.makedirs(os.path.dirname(tn.VAULT_STATE), exist_ok=True)
        with open(tn.VAULT_STATE, "wb") as fh:
            fh.write(content)
    st, _ = tn.check(dict(VST), "k", now=VNOW)
    assert vault_cards(sent) == [] and any("Server disk low" in t for t in sent)
    assert "vault alerts failed" not in capsys.readouterr().out


def test_vault_too_large_file_is_not_read(monkeypatch):
    sent, _h = vault_bot(monkeypatch)
    monkeypatch.setattr(tn, "VAULT_READ_MAX", 200)
    vault_state(three())
    tn.check(dict(VST), "k", now=VNOW)
    assert vault_cards(sent) == []


def test_vault_exception_never_stops_the_other_alerts(monkeypatch, capsys):
    sent, _h = vault_bot(monkeypatch)
    monkeypatch.setattr(tn, "disk_free_gb", lambda path=None: 1.5)

    def boom(path=None):
        raise RuntimeError("vault read broke")
    monkeypatch.setattr(tn, "_vault_read", boom)
    st = dict(VST, summary_day="2026-11-18")
    st, _ = tn.check(st, "k", now=VNOW)
    st, _ = tn.check(st, "k", now=VNOW)
    assert any("Server disk low" in t for t in sent) and any("daily summary" in t for t in sent)
    out = capsys.readouterr().out
    assert out.count("vault alerts failed (RuntimeError)") == 1 and "vault read broke" not in out


def test_vault_cards_carry_no_secret_no_url_no_dollars(monkeypatch):
    sent, _h = vault_bot(monkeypatch)
    ints = three()
    for it in ints.values():                                          # whatever else might sit beside an intent
        it.update(secret="deadbeef" * 8, nonce="n0nce-SHOULD-NOT-SHOW")
    vault_state(ints, extra={"secret_file": "/etc/ait-engine/engine.secret", "host": "127.0.0.1"})
    tn.check(dict(VST), "k", now=VNOW)
    cards = vault_cards(sent)
    assert len(cards) == 3
    for c in cards:
        for bad in ("deadbeef", "n0nce", "/etc/", "engine.secret", "http", "127.0.0.1", "$", "BTCUSDT.2026", "intent_id"):
            assert bad not in c


def test_vault_sends_failing_once_then_back(monkeypatch):
    sent, _h = vault_bot(monkeypatch)
    iid, it = intent("BTCUSDT", "20261118T101500Z", "close", "futures", "pending")
    it["made"] = VNOW.timestamp() - 47 * 60
    vault_state({iid: it}, book={"BTCUSDT": {"content": "h", "as_of": "2026-11-19T09:30:00Z"}})
    t = VNOW.timestamp()
    os.utime(tn.VAULT_STATE, (t - 60, t - 60))                       # the feed is running (wrote a minute ago)
    st, _ = tn.check(dict(VST), "k", now=VNOW)
    fail = [c for c in vault_cards(sent) if "sends failing" in c]
    assert len(fail) == 1 and "1 exit instruction waiting, the oldest for 47 min" in fail[0]
    assert "no book accepted for 60 min (newest: bar of 19 Nov 09:30 UTC)" in fail[0] and st["vault_failing"]
    os.utime(tn.VAULT_STATE, (t - 60, t - 60))
    st, _ = tn.check(st, "k", now=VNOW)
    assert len([c for c in vault_cards(sent) if "sends failing" in c]) == 1      # once
    it["status"] = "sent"
    vault_state({iid: it}, book={"BTCUSDT": {"content": "h", "as_of": "2026-11-19T10:15:00Z"}})
    os.utime(tn.VAULT_STATE, (t - 60, t - 60))
    st, _ = tn.check(st, "k", now=VNOW)
    assert any("sends going through again" in c for c in vault_cards(sent)) and not st["vault_failing"]
    assert any("Accepted by the vault" in c for c in vault_cards(sent))


def test_vault_old_book_alone_is_not_failing_when_the_feed_is_not_running(monkeypatch):
    sent, _h = vault_bot(monkeypatch)
    vault_state({}, book={"BTCUSDT": {"content": "h", "as_of": "2026-11-19T06:00:00Z"}})
    t = VNOW.timestamp() - 3 * 3600
    os.utime(tn.VAULT_STATE, (t, t))                                  # feature off / feed stopped: the file is old
    st, _ = tn.check(dict(VST), "k", now=VNOW)
    assert vault_cards(sent) == [] and not st.get("vault_failing")


def test_the_bot_never_imports_the_vault_feed():
    src = open(tn.__file__, encoding="utf-8").read()
    assert "import vault_feed" not in src and "vault_feed import" not in src and "from .vault_feed" not in src

# ------------------------------------------------------------------ the early signal preview (H56; signals_early.py)
PENDING = {"status": "FLAT", "trades": 0, "next_open": "ENTER -> LONG"}


def early_bars(tmp_path, rows):
    """Bars from 16 Nov 23:45 (the decision bar, close 100) on."""
    with open(str(tmp_path / "data" / "btcusdt_15m.csv"), "w") as fh:
        fh.write("ts_ms,open,high,low,close,volume,taker_buy\n")
        for k, (o, h, l, c) in enumerate(rows):
            fh.write("%d,%s,%s,%s,%s,1.0,\n" % (1794873600000 + 900000 * (k - 1), o, h, l, c))


def run_to_early(monkeypatch, tmp_path):
    calls, holder = signal_bot(monkeypatch, tmp_path)
    st = {"chat_id": 42, "summary_day": "2026-11-16", "calib_week": "2026-W47", "rank_week": "2026-W47"}
    st, _ = tn.check(st, "k", now=datetime(2026, 11, 16, 23, 50, tzinfo=timezone.utc))   # both previews start, book flat
    assert calls == [] and os.path.exists(tn.EARLY_STATE) and os.path.exists(tn.SIGNALS_STATE)
    st["summary_day"] = "2026-11-17"
    holder["page"] = signal_page(dict(PENDING), "2026-11-17 00:00")
    early_bars(tmp_path, [(99.5, 100.4, 99.4, 100.0)])
    st, _ = tn.check(st, "k", now=at17(0, 2))                        # the model decided at 00:00: the early card
    return calls, holder, st


def test_early_preview_goes_to_the_owner_chat_under_its_own_line(monkeypatch, tmp_path):
    calls, holder, st = run_to_early(monkeypatch, tmp_path)
    assert len(calls) == 1 and calls[0]["chat_id"] == 42 and "reply_to_message_id" not in calls[0]
    t = calls[0]["text"]
    assert t.startswith(u"\U0001f9ea Early signal preview\n") and not t.startswith(tn.SIGNALS_HEAD)
    assert "BUY BTC" in t and "BTC-1117-01e" in t and "Limit order at <b>100.000</b>" in t and "<pre>" not in t
    low = t.lower()
    assert "b_targets" not in low and "shadow" not in low and "kronos" not in low and "edge" not in low
    assert t.endswith("Paper signal from a model, not financial advice.</i>")
    holder["page"] = signal_page(dict(LONG), "2026-11-17 00:15", "2026-11-17T00:15:30Z")   # the book filled: both speak
    early_bars(tmp_path, [(99.5, 100.4, 99.4, 100.0), (101, 101.5, 100.5, 101)])
    st, _ = tn.check(st, "k", now=at17(0, 16))
    texts = [c["text"] for c in calls[1:]]
    assert len(texts) == 2 and texts[0].startswith(tn.SIGNALS_HEAD) and "BTC-1117-01</code>" in texts[0]
    assert texts[1].startswith(tn.EARLY_HEAD) and "Stop and targets" in texts[1] and calls[2]["reply_to_message_id"] == 701
    st, _ = tn.check(st, "k", now=at17(0, 17))
    assert len(calls) == 3                                           # nothing twice
    assert "open" not in st and "seen" not in st


def test_early_command_and_the_recap_line(monkeypatch, tmp_path):
    calls, holder, st = run_to_early(monkeypatch, tmp_path)
    holder["updates"] = [(99, "/early")]
    st, _ = tn.check(st, "k", now=at17(0, 3))
    assert len(calls) == 1                                           # a stranger gets no answer
    holder["updates"] = [(42, "/early")]
    st, _ = tn.check(st, "k", now=at17(0, 4))
    t = calls[1]["text"]
    assert t.startswith(tn.EARLY_HEAD + "\n") and u"Early signals · the record" in t and "Signals sent                 1" in t
    assert "no paired result yet" in t
    holder["page"] = signal_page(dict(PENDING), "2026-11-18 00:00", "2026-11-18T00:00:30Z")
    st, _ = tn.check(st, "k", now=datetime(2026, 11, 18, 0, 1, tzinfo=timezone.utc))
    recap = [c["text"] for c in calls if "daily recap" in c["text"]]
    assert len(recap) == 1 and recap[0].startswith(tn.SIGNALS_HEAD)
    assert u"\U0001f9ea Early signal preview: yesterday 1 sent; in all 1 sent" in recap[0]


def test_an_exception_in_early_code_never_blocks_s1_or_the_alerts(monkeypatch, tmp_path, capsys):
    from engine15 import signals_early

    def boom(*a, **k):
        raise RuntimeError("early signals are broken")
    monkeypatch.setattr(signals_early, "run", boom)
    monkeypatch.setattr(signals_early, "recap_line", boom)
    calls, holder, st = run_to_fill(monkeypatch, tmp_path)           # S1 card and its fill, exactly as without S2
    assert len(calls) == 2 and all(c["text"].startswith(tn.SIGNALS_HEAD) for c in calls)
    open(tn.EARLY_STATE, "w").close()                                # the early preview "started": the recap asks it
    monkeypatch.setattr(tn, "disk_free_gb", lambda path=None: 1.5)
    holder["page"] = signal_page(dict(LONG), "2026-11-18 00:00", "2026-11-18T00:00:30Z")
    st, _ = tn.check(st, "k", now=datetime(2026, 11, 18, 0, 1, tzinfo=timezone.utc))
    texts = [c["text"] for c in calls[2:]]
    assert any("Server disk low" in x for x in texts) and any("daily summary" in x for x in texts)
    recap = [x for x in texts if "daily recap" in x]
    assert len(recap) == 1 and "Early signal preview:" not in recap[0]
    st, _ = tn.check(st, "k", now=datetime(2026, 11, 18, 0, 2, tzinfo=timezone.utc))
    out = capsys.readouterr().out
    assert out.count("early signals failed (check: RuntimeError)") == 1 and "early signals are broken" not in out
    assert "signals failed (check" not in out.replace("early signals failed (check", "")      # S1 never failed
    assert tn._early_guard("x", lambda: 7) == 7


# ------------------------------------------------------------------ the weekly ranking (owner, 19 Nov 2026)
def rank_page(trail=20, trail_pnl=5407.89, fvg=20, fvg_net=504.15, p1_retired=True):
    """A realistic page: the shadows scoreboard (marked, 8 markets) and the strategy / RL / pair books (closed only)."""
    sh = [{"book": "main", "title": "Main rule (v5), fresh copy", "assets": 8, "pnl_usd": 4517.86, "return_pct": 5.65,
           "trades": 2, "win_rate_pct": 0.0},
          {"book": "b_trail", "title": "B trail", "assets": 8, "pnl_usd": trail_pnl, "return_pct": 6.76, "trades": trail},
          {"book": "b_targets", "title": "B targets", "assets": 8, "pnl_usd": 3497.49, "return_pct": 4.37, "trades": 15},
          {"book": "m_swing_4h", "title": "M 4h", "assets": 8, "pnl_usd": -195.19, "return_pct": -0.24, "trades": 1},
          {"book": "m_swing_1h", "title": "M 1h", "assets": 8, "pnl_usd": 0.0, "return_pct": 0.0, "trades": 0}]
    ba = lambda *a: dict((x, {"trades": 1}) for x in a)                                  # noqa: E731
    six = ("BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "USDJPY", "SPX")
    p1 = {"title": "Liquidation hunt (retired 15 Nov 2026)", "totals": {"trades": 66, "net_usd": -1367.6}, "by_asset": ba(*six)}
    if p1_retired:
        p1["retired"] = "2026-11-15 06:15"
    else:
        p1["title"] = "Liquidation hunt"
    return {"generated_utc": "2026-11-23T00:00:00Z", "version": "think15-v5.2.3", "assets": {},
            "shadows": {"scoreboard": {"rows": sh}},
            "playbook": {"playbook": {"p1_liqhunt": p1, "p2_trap": {"totals": {"trades": 0, "net_usd": 0.0}, "by_asset": {}}},
                         "playbook3": {"p8_fvg": {"totals": {"trades": fvg, "net_usd": fvg_net}, "by_asset": ba(*six)},
                                       "p10_round": {"totals": {"trades": 67, "net_usd": -531.15}, "by_asset": ba(*six)}},
                         "playbook5": {"p5_rlq": {"totals": {"trades": 5, "net_usd": 211.53}, "by_asset": ba("BTCUSDT")}},
                         "playbook6": {"p6_p4trend": {"totals": {"trades": 2, "net_usd": 424.67}, "by_asset": ba("BTCUSDT")}},
                         "playbook7": {"p7_rvbear": {"totals": {"trades": 1, "net_usd": -587.29}, "by_asset": ba("BTCUSDT")}}}}


def rank_score(fvg_verdict="too few trades to judge (20 of 30)"):
    return {"rows": [{"book": "main", "title": "Main books (live)", "trades": 5, "net_usd": -1332.0, "verdict": "ahead: x"},
                     {"book": "b_trail", "title": "Shadow: b_trail", "trades": 20, "net_usd": 4526.0,
                      "verdict": "too few trades to judge (20 of 30)"},
                     {"book": "p8_fvg", "title": "Strategy: p8_fvg", "trades": 20, "net_usd": 504.15, "verdict": fvg_verdict},
                     {"book": "p1_liqhunt", "title": "Strategy: p1_liqhunt", "trades": 66, "net_usd": -1367.6,
                      "verdict": "behind: even the high end of the range is negative"}]}


def _pre_rows(card, k):
    """The rows of the k-th <pre> table of a card (header and rule dropped)."""
    return card.split("<pre>")[k + 1].split("</pre>")[0].split("\n")[2:]


RNOW = datetime(2026, 11, 23, 0, 1, tzinfo=timezone.utc)


def test_ranking_order_and_percent_maths_marked_vs_closed():
    books = dict((b["id"], b) for b in tn.ranking_books(rank_page(), rank_score()))
    assert abs(books["s:b_trail"]["ret"] - 5407.89 / 80000 * 100) < 1e-9          # marked, incl. open: $10k x 8 markets
    assert abs(books["s:m_swing_4h"]["ret"] - (-195.19 / 80000 * 100)) < 1e-9
    assert abs(books["p:p8_fvg"]["ret"] - 504.15 / 60000 * 100) < 1e-9            # closed only: 6 markets traded
    assert abs(books["p:p5_rlq"]["ret"] - 211.53 / 20000 * 100) < 1e-9            # RL: BTC and ETH by design (2)
    assert abs(books["p:p6_p4trend"]["ret"] - 424.67 / 20000 * 100) < 1e-9
    assert abs(books["p:p7_rvbear"]["ret"] - (-587.29 / 10000 * 100)) < 1e-9      # the pair book: 1
    assert books["s:main"]["kind"] == "main" and books["p:p8_fvg"]["kind"] == "strat"
    assert books["p:p8_fvg"]["verdict"] == "too few" and books["p:p1_liqhunt"]["verdict"] == "behind"
    assert books["s:main"]["verdict"] == ""                                        # 'Main books (live)' is not the shadow copy
    card = tn.ranking_card(list(books.values()), now=RNOW)
    t1, t2 = _pre_rows(card, 0), _pre_rows(card, 1)
    assert t1[0].startswith(" 1 B trail") and "+6.76%" in t1[0] and t1[0].rstrip().endswith("20")
    assert t1[1].startswith(" 2 Main") and "+5.65%" in t1[1]
    assert t1[2].startswith(" 3 B targets") and t1[3].startswith(" 4 M swing 4h") and "-0.24%" in t1[3]
    assert "M swing 1h" not in "\n".join(t1) and "No trades yet: M swing 1h" in card       # 0 trades: one line
    assert t2[0].startswith(" 1 P6 RL ctrl") and "+2.12%" in t2[0]                # 424.67 / 20,000
    assert [r[3:14].strip() for r in t2[:5]] == ["P6 RL ctrl", "P5 RL", "P8 FVG", "P10 round", "P7 pair"]
    assert "-5.87%" in t2[4] and "No trades yet: P2 trap" in card.split("Strategy and RL books")[1]
    assert "weekly ranking" in card and "paper only · returns since 11 Nov 2026 · not advice" in card
    assert "edge" not in card.lower() and "kronos" not in card.lower()


def test_ranking_retired_at_the_bottom_unranked_and_tables_narrow():
    card = tn.ranking_card(tn.ranking_books(rank_page(), rank_score()), now=RNOW)
    t2 = _pre_rows(card, 1)
    i = next(k for k, r in enumerate(t2) if "retired" in r)
    assert t2[-1].startswith("-- P1 liq hunt") and "-2.28%" in t2[-1] and i == len(t2) - 2   # after every ranked row
    assert all(not r.startswith("--") for r in t2[:i])
    for k in (0, 1):
        pre = card.split("<pre>")[k + 1].split("</pre>")[0]
        assert max(len(ln) for ln in pre.split("\n")) <= 30
    t2b = _pre_rows(tn.ranking_card(tn.ranking_books(rank_page(p1_retired=False), rank_score())), 1)
    assert not any("retired" in r for r in t2b) and any(r.startswith(" 5 P1 liq hunt") for r in t2b)   # not retired: ranked


def test_ranking_this_week_diff_30_trades_verdict_retired_and_movers():
    prev = tn.ranking_snapshot(tn.ranking_books(rank_page(trail=27, trail_pnl=4000.0, fvg=26, p1_retired=False), rank_score()))
    books = tn.ranking_books(rank_page(trail=31, trail_pnl=5600.0, fvg=30, fvg_net=-300.0),
                             rank_score("ahead: the range is above zero"))
    card = tn.ranking_card(books, prev, "2026-11-16T00:01:00Z", RNOW)
    week = card.split("This week")[1]
    assert "(since 16 Nov)" in week
    assert "B trail reached <b>30 trades</b> (31)" in week and "P8 FVG reached <b>30 trades</b> (30)" in week
    assert "P8 FVG verdict now <b>ahead</b> (was too few)" in week
    assert "P1 liq hunt retired" in week
    assert "Best mover: B trail +2.00 pts, now +7.00% (+$84.0k)" in week          # (5600-4000)/80,000; $ at 15x
    assert "Worst mover: P8 FVG -1.34 pts, now -0.50% (-$4,500)" in week           # (-300-504.15)/60,000
    assert "Main reached" not in week and "B targets" not in week                  # no checkpoint, no move
    assert "First weekly card" in tn.ranking_card(books, None)


def ranking_bot(monkeypatch, pg=None, sc=None, updates=()):
    sent, holder = [], {"page": rank_page() if pg is None else pg, "score": rank_score() if sc is None else sc,
                        "updates": list(updates)}

    def fake_call(tok, method, payload, timeout=20):
        if method == "getUpdates":
            ups, holder["updates"] = holder["updates"], []
            return {"ok": True, "result": [{"update_id": 50 + k, "message": {"chat": {"id": c}, "text": t}}
                                           for k, (c, t) in enumerate(ups)]}
        sent.append((payload.get("chat_id"), payload.get("text", "")))
        return {"ok": True}
    monkeypatch.setattr(tn, "_call", fake_call)
    monkeypatch.setattr(tn, "_load", lambda p, d=None: holder["page"] if p.endswith("page.json") else holder["score"])
    monkeypatch.setattr(tn, "refit_marks", lambda: [0, 0])
    monkeypatch.setattr(tn, "disk_free_gb", lambda path=None: 50.0)
    monkeypatch.setattr(tn, "calibration_now", lambda now=None: calib_result(n=0))
    monkeypatch.setattr(tn, "_RANK_ERR", [None])
    return sent, holder


def test_weekly_ranking_once_per_iso_week_and_snapshot(monkeypatch):
    sent, holder = ranking_bot(monkeypatch)
    at = lambda d, h=0, m=1: datetime(2026, 11, d, h, m, tzinfo=timezone.utc)   # noqa: E731
    st = {"chat_id": 42}
    for now in (at(16), at(16, 0, 2), at(17), at(22, 23, 59)):                # Monday 16 Nov to Sunday 22 Nov
        st, _ = tn.check(st, "k", now=now)
    rk = [i for i, (_c, t) in enumerate(sent) if "weekly ranking" in t]
    assert rk == [1] and st["rank_week"] == "2026-W47" and st["rank_prev_utc"] == "2026-11-16T00:01:00Z"
    assert st["rank_prev"]["s:b_trail"] == {"t": 20, "v": "too few", "r": round(5407.89 / 800, 4), "x": False}
    assert "First weekly card" in sent[1][1]
    holder["page"] = rank_page(trail=30, trail_pnl=6000.0)
    st, _ = tn.check(st, "k", now=at(23))                                     # the next Monday: second card, with the diff
    rk = [t for _c, t in sent if "weekly ranking" in t]
    assert len(rk) == 2 and st["rank_week"] == "2026-W48" and "B trail reached <b>30 trades</b>" in rk[1]
    assert "(since 16 Nov)" in rk[1] and st["rank_prev"]["s:b_trail"]["t"] == 30
    assert sum("daily summary" in t for _c, t in sent) == 4


def test_ranking_command_chat_lock_and_snapshot_unchanged(monkeypatch):
    sent, holder = ranking_bot(monkeypatch, updates=[(99, "/ranking")])
    snap = {"s:b_trail": {"t": 25, "v": "too few", "r": 6.0, "x": False}}
    st = {"chat_id": 42, "summary_day": "2026-11-17", "calib_week": "2026-W47", "rank_week": "2026-W47",
          "rank_prev": dict(snap), "rank_prev_utc": "2026-11-16T00:01:00Z"}
    st, _ = tn.check(st, "k", now=NOW)
    assert sent == []                                                          # a stranger gets no answer
    holder["updates"] = [(42, "/ranking"), (99, "/ranking")]
    st, _ = tn.check(st, "k", now=NOW)
    assert [c for c, _t in sent] == [42] and "weekly ranking" in sent[0][1] and "Best mover: B trail" in sent[0][1]
    assert st["rank_prev"] == snap                                             # /ranking never moves the snapshot


GARBLED = [
    (None, None),
    ({"generated_utc": "2026-11-17T00:00:00Z", "shadows": "garbled", "playbook": [1, 2]}, None),
    ({"generated_utc": "2026-11-17T00:00:00Z", "shadows": {"scoreboard": "x"}, "playbook": {"playbook5": None}},
     {"rows": [{"book": "p8_fvg", "title": "Strategy: p8_fvg", "trades": 0, "net_usd": 0, "verdict": None}]}),
    ({"generated_utc": "2026-11-17T00:00:00Z",
      "shadows": {"scoreboard": {"rows": [None, {"book": "b_trail", "assets": 0, "pnl_usd": "abc", "trades": "x"},
                                          {"book": "b_targets", "assets": "8", "pnl_usd": float("nan"), "trades": 3}]}},
      "playbook": {"playbook3": {"p8_fvg": {"totals": "nope"}, "p6_vwap": {"totals": {"trades": 3, "net_usd": None}}},
                   "playbook5": "garbled"}}, {"rows": [{"book": "b_trail", "title": "Shadow: b_trail", "verdict": 7}]}),
]


@pytest.mark.parametrize("pg,sc", GARBLED)
def test_ranking_with_missing_or_garbled_data_never_stops_the_summary(monkeypatch, pg, sc):
    sent, holder = ranking_bot(monkeypatch)
    holder["page"], holder["score"] = pg, sc
    st, _ = tn.check({"chat_id": 42}, "k", now=NOW)
    assert any("daily summary" in t for _c, t in sent) and st["summary_day"] == "2026-11-17" and st["rank_week"] == "2026-W47"
    assert not any("weekly ranking" in t for _c, t in sent) and "rank_prev" not in st     # no books: no card, no snapshot
    holder["updates"] = [(42, "/ranking")]
    st, _ = tn.check(st, "k", now=NOW)
    assert "No forward books in the page yet" in sent[-1][1]


def test_ranking_failure_is_guarded_and_printed_once(monkeypatch, capsys):
    sent, holder = ranking_bot(monkeypatch)

    def boom(*a, **k):
        raise RuntimeError("ranking broke")
    monkeypatch.setattr(tn, "ranking_books", boom)
    monkeypatch.setattr(tn, "disk_free_gb", lambda path=None: 1.5)
    st, _ = tn.check({"chat_id": 42}, "k", now=NOW)
    holder["updates"] = [(42, "/ranking"), (42, "/ranking")]
    st, _ = tn.check(st, "k", now=NOW)
    texts = [t for _c, t in sent]
    assert any("daily summary" in t for t in texts) and any("Server disk low" in t for t in texts)
    assert not any("weekly ranking" in t for t in texts) and st["rank_week"] == "2026-W47"
    out = capsys.readouterr().out
    assert out.count("ranking failed (weekly: RuntimeError)") == 1 and out.count("ranking failed (/ranking: RuntimeError)") == 1
    assert "ranking broke" not in out


# ------------------------------------------------------------------ the feed's memory lost (vault_feed.memory_alarm)
def test_vault_memory_lost_is_one_card_per_setup(monkeypatch):
    sent, _h = vault_bot(monkeypatch)
    lost = {"BTCUSDT": {"side": "LONG", "opened_utc": "2026-11-18T09:00:00Z", "since": MADE, "why": "missing"},
            "ETHUSDT": {"side": "SHORT", "opened_utc": "2026-11-19T02:15:00Z", "since": MADE, "why": "unreadable"}}
    vault_state({}, extra={"alarm": {"memory_lost": lost}})
    st, _ = tn.check(dict(VST), "k", now=VNOW)
    cards = [c for c in vault_cards(sent) if "feed memory lost" in c]
    assert len(cards) == 2
    assert "long setup opened 18 Nov 09:00 UTC" in cards[0] and "was missing" in cards[0] and "<b>no exit</b>" in cards[0]
    assert "short setup opened 19 Nov 02:15 UTC" in cards[1] and "could not be read" in cards[1]
    for c in cards:
        assert "http" not in c and "$" not in c and "vault_feed" not in c and "stop on the exchange" in c
    st, _ = tn.check(st, "k", now=VNOW)
    assert len([c for c in vault_cards(sent) if "feed memory lost" in c]) == 2          # once each
    lost["BTCUSDT"]["opened_utc"] = "2026-11-19T10:00:00Z"                               # another setup: its own card
    vault_state({}, extra={"alarm": {"memory_lost": lost}})
    st, _ = tn.check(st, "k", now=VNOW)
    assert len([c for c in vault_cards(sent) if "feed memory lost" in c]) == 3


def test_vault_memory_lost_card_is_retried_and_a_garbled_alarm_is_no_card(monkeypatch):
    sent, holder = vault_bot(monkeypatch, ok=False)
    vault_state({}, extra={"alarm": {"memory_lost": {"BTCUSDT": {"side": "LONG", "opened_utc": "2026-11-18T09:00:00Z"}}}})
    st, _ = tn.check(dict(VST), "k", now=VNOW)
    assert not [k for k in st.get("vault_alerted", {}) if k.startswith("memory_lost")]   # not delivered: not remembered
    holder["ok"] = True
    st, _ = tn.check(st, "k", now=VNOW)
    assert [k for k in st["vault_alerted"] if k.startswith("memory_lost")]
    n = len(sent)
    for bad in ({"alarm": "x"}, {"alarm": {"memory_lost": ["BTCUSDT"]}}, {"alarm": {"memory_lost": {"BTCUSDT": 7}}}):
        vault_state({}, extra=bad)
        tn.check(dict(VST), "k", now=VNOW)
    assert not [c for c in sent[n:] if "feed memory lost" in c]


def test_vault_memory_lost_card_says_when_later_exits_still_go(monkeypatch):
    sent, _h = vault_bot(monkeypatch)
    vault_state({}, extra={"alarm": {"memory_lost": {"BTCUSDT": {"side": "SHORT", "opened_utc": "2026-11-15T03:15:00Z",
                                                                "since": MADE, "why": "missing", "exits": "later"}}}})
    tn.check(dict(VST), "k", now=VNOW)
    card = [c for c in vault_cards(sent) if "feed memory lost" in c][0]
    assert "Later exits for this setup will be sent" in card and "no exit</b> for this setup" not in card
