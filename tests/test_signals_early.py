# -*- coding: utf-8 -*-
"""signals_early (S2, H56): detection of a new pending b_targets entry, the window counted from the first bar that opens
after the alert, fills / no fills / exits through S1's state machine, the levels one bar later (page or closed-trade file),
the pairing with S1 on the same entry, and the files it keeps (idempotent, restart-safe)."""
import io
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from engine15 import signals, signals_early as se  # noqa: E402

DAY = datetime(2026, 11, 19, tzinfo=timezone.utc)
T0 = signals._ms(DAY)
BAR = signals.BAR_MS
E0 = 100.0                              # the decision close (bar -1)
N = (101.0, 101.5, 100.5, 101.0)        # holds neither E0, the stop 98 nor Target 1 103
TOUCH = (100.5, 101.0, 99.5, 100.2)     # holds E0 only
CSV_HEAD = ("t_in_ms,t_out_ms,side,p_in,p_out,why_in,why_out,pnl_pct,equity,qty,pnl_usd,fees_usd,stop0,risk_usd,r_mult,"
            "target_1,target_2,time_in,time_out")


def ts(k):
    return T0 + k * BAR


def at(minute):
    return DAY + timedelta(minutes=minute)


def utc(ms):
    return signals._dt(ms).strftime("%Y-%m-%d %H:%M")


class Sim(object):
    """One market. The book decides at the close of bar -1 (00:00), the page shows the pending order from then on; the
    early alert goes out at 00:02, in bar 0 (bar A); the book fills at bar 0's open at 100.3 with stop 98, Target 1 103
    and Target 2 105; the page shows the position after bar 0 closed."""

    def __init__(self, tmp, asset="BTCUSDT", group="crypto", side=1):
        self.asset, self.group, self.side = asset, group, side
        self.data, self.live = str(tmp / "data"), str(tmp / "live")
        os.makedirs(self.data)
        os.makedirs(self.live)
        self.state, self.log = os.path.join(self.data, "signals_early_state.json"), os.path.join(self.data, "e.jsonl")
        self.s1_log = os.path.join(self.data, "signals_log.jsonl")
        self.sent, self.deliver = [], True
        self.view = {"status": "FLAT", "trades": 0, "wins": 0}
        self.bars = {-2: (99.0, 100.5, 98.8, 99.5), -1: (99.5, 100.4, 99.4, E0)}

    def send(self, text, reply_to=None):
        if not self.deliver:
            return False, None
        self.sent.append((text, reply_to))
        return True, 900 + len(self.sent)

    def pend(self, nxt="ENTER -> LONG", **kw):
        self.view = dict(self.view, next_open=nxt, **kw)

    def filled(self, k=0, E=100.3, S=98.0, T1=103.0, T2=105.0, **kw):
        self.view = dict({"status": "LONG" if self.side > 0 else "SHORT", "entry": E, "stop": S, "opened_utc": utc(ts(k)),
                          "opened_by": "ENTER", "target_1": T1, "target_2": T2, "t1_taken": False, "trades": 0}, **kw)

    def trade_row(self, k_in, k_out, why="STOP", p_in=100.3, p_out=98.0, pct=-2.3, r=-1.0, S=98.0, T1=103.0, T2=105.0):
        path = signals.trades_path(self.live, self.asset)
        new = not os.path.exists(path)
        with io.open(path, "a", encoding="utf-8") as fh:
            fh.write((CSV_HEAD + "\n" if new else "") + "%d,%d,%d,%s,%s,ENTER,%s,%s,10000,1,%s,2,%s,200,%s,%s,%s,%s,%s\n" % (
                ts(k_in), ts(k_out), self.side, p_in, p_out, why, pct, pct * 100, S, r, T1, T2, utc(ts(k_in)), utc(ts(k_out))))

    def write_bars(self):
        with io.open(signals.bar_path(self.data, self.asset), "wb") as fh:
            fh.write(b"ts_ms,open,high,low,close,volume,taker_buy\n")
            for k in sorted(self.bars):
                fh.write(("%d,%s,%s,%s,%s,1.0,\n" % ((ts(k),) + tuple(self.bars[k]))).encode())

    def page(self, upto):
        return {"generated_utc": "x", "markets": {self.group: [self.asset]},
                "assets": {self.asset: {"short": "BTC", "market_group": self.group, "structure": "uptrend on every horizon",
                                        "voices": [{"title": "Support and resistance", "pull_pts": 3.0 * self.side},
                                                   {"title": "Kronos candle forecast", "pull_pts": 2.0 * self.side}]}},
                "shadows": {"books": {signals.BOOK: {"assets": {self.asset: self.view}}},
                            "markets": {self.group: {"as_of_utc": utc(ts(upto + 1))}}}}

    def check(self, minute, upto=None):
        self.write_bars()
        upto = (minute // 15) - 1 if upto is None else upto
        return se.run(self.page(upto), at(minute), self.send, self.data, self.live, self.state, self.log)

    def start(self, minute=2, **kw):
        """The preview starts with a flat book at 23:50; the book decides at 00:00; the alert goes out at `minute`."""
        self.check(-10)
        self.pend(**kw)
        return self.check(minute)

    def play(self, bars, minute=None):
        self.bars.update(bars)
        return self.check((max(self.bars) + 1) * 15 + 1 if minute is None else minute)

    def st(self):
        return signals.load_state(self.state)

    def sig(self):
        o = self.st()["open"]
        return o[sorted(o)[0]] if o else None

    def events(self):
        return [e for e in signals.read_log(self.log) if e.get("id")]

    def evs(self):
        return [e["ev"] for e in self.events()]

    def last(self, ev):
        return [e for e in self.events() if e["ev"] == ev][-1]

    def texts(self):
        return [t for t, _r in self.sent]


@pytest.fixture
def sim(tmp_path):
    return Sim(tmp_path)


# ------------------------------------------------------------------ detection
def test_pending_entry_reads_only_new_entries():
    assert se.pending_entry({"status": "FLAT", "next_open": "ENTER -> LONG"}) == 1
    assert se.pending_entry({"status": "FLAT", "next_open": "FORCED -> SHORT"}) == -1
    assert se.pending_entry({"status": "LONG", "next_open": "FLIP -> SHORT"}) == -1          # a flip into a new entry
    assert se.pending_entry({"status": "LONG", "next_open": "STEP_ASIDE -> FLAT"}) is None   # an exit
    assert se.pending_entry({"status": "SHORT", "next_open": "TRAIL_MA -> FLAT"}) is None
    assert se.pending_entry({"status": "LONG", "next_open": "ENTER -> LONG"}) is None        # the side already held
    assert se.pending_entry({"status": "FLAT"}) is None and se.pending_entry(None) is None


def test_a_new_pending_entry_is_signalled_with_e0_and_no_levels(sim):
    info = sim.start()
    assert info["new"] == 1 and len(sim.sent) == 1
    card = sim.texts()[0]
    assert "BUY BTC" in card and "early signal <code>BTC-1119-01e</code>" in card
    assert "Limit order at <b>100.000</b>" in card and "Valid until <b>01:00 UTC</b> (the next 3 full 15-minute bars)" in card
    assert "Stop and targets follow as a reply" in card and "Target 1 trades before the entry fills" in card
    assert "<pre>" not in card and "Target 2 1" not in card and card.endswith("not financial advice.</i>")
    low = card.lower()
    assert "kronos" not in low and "b_targets" not in low and "shadow" not in low and "edge" not in low
    s = sim.sig()
    assert s["follow"]["state"] == se.AWAIT and s["entry"] == E0 and s["a_ms"] == ts(0) and s["first_ms"] == ts(1)
    assert s["valid_until_ms"] == ts(4) and s["window"] == 3 and s["k"] == "BTCUSDT|2026-11-19 00:00"
    e = sim.last("signal")
    assert e["decision_utc"] == "2026-11-19 00:00" and e["bar_a_utc"] == "2026-11-19T00:00:00Z"
    assert e["first_bar_utc"] == "2026-11-19T00:15:00Z" and e["window"] == 3


def test_exits_and_flats_are_not_signals(sim):
    sim.check(-10)
    sim.filled(k=-20)
    sim.pend("STEP_ASIDE -> FLAT")
    sim.check(2)
    sim.view = {"status": "FLAT", "trades": 3, "next_open": "TRAIL_MA -> FLAT"}
    sim.check(17)
    assert sim.sent == [] and sim.st()["open"] == {}


def test_a_flip_into_the_other_side_is_a_signal(sim):
    sim.check(-10)
    sim.filled(k=-20)
    sim.pend("FLIP -> SHORT")
    sim.check(2)
    assert len(sim.sent) == 1 and "SELL BTC" in sim.texts()[0]


def test_first_run_does_not_signal_orders_already_waiting(sim):
    sim.pend()
    info = sim.check(2)
    assert info["started"] and sim.sent == [] and sim.st()["seen"]["BTCUSDT"] == se.fingerprint(sim.view)
    assert [e["ev"] for e in signals.read_log(sim.log)] == ["start", "seen_not_signalled"]
    sim.check(3)
    assert sim.sent == []


def test_a_late_feed_market_shows_the_same_order_on_two_pages_one_signal(tmp_path):
    g = Sim(tmp_path, asset="XAUUSD", group="metals")
    assert se.delay_bars("XAUUSD") == 1
    g.start()
    g.bars[0] = N
    g.check(16)                                                      # the same pending, one page later: no second signal
    assert len(g.sent) == 1 and g.sig()["follow"]["state"] == se.AWAIT
    g.filled(k=1)                                                    # the book filled at bar 1's open (one bar later)
    g.bars[1] = N
    g.check(31)
    assert g.sig()["follow"]["state"] == signals.WAITING and g.last("levels")["entry_utc"] == "2026-11-19 00:15"


# ------------------------------------------------------------------ levels and the window
def test_levels_follow_from_the_page_and_bar_a_never_fills_after_the_alert(sim):
    sim.start()
    sim.filled()
    info = sim.play({0: TOUCH})                                      # bar A holds E0 but opened before the alert
    assert info["events"] == 1 and sim.evs() == ["signal", "levels"]
    lv = sim.texts()[1]
    assert sim.sent[1][1] == 901 and "Stop and targets" in lv and "limit at 100.000, valid until 01:00 UTC" in lv
    assert "Stop          98.00  2.00  1.0" in lv and "Target 1    103.000  3.00  1.5" in lv
    s = sim.sig()
    assert (s["stop"], s["t1"], s["t2"], s["opened_utc"], s["book_entry"]) == (98.0, 103.0, 105.0, "2026-11-19 00:00", 100.3)
    assert s["follow"]["state"] == signals.WAITING and s["follow"]["bars_after_a"] == 0
    sim.play({1: TOUCH})                                             # the first bar that opens after the alert: filled at E0
    assert sim.last("filled")["px"] == E0 and sim.last("filled")["bar_utc"] == "2026-11-19T00:15:00Z"
    assert "Entry filled" in sim.texts()[2] and sim.sent[2][1] == 901


def test_an_alert_sent_at_the_bar_open_counts_bar_a(sim):
    sim.start(minute=0)
    s = sim.sig()
    assert s["first_ms"] == ts(0) and s["window"] == 4 and s["valid_until_ms"] == ts(4)
    assert "the next 4 full 15-minute bars" in sim.texts()[0]
    sim.filled()
    sim.play({0: TOUCH})
    assert sim.evs() == ["signal", "levels", "filled"] and sim.last("filled")["bar_utc"] == "2026-11-19T00:00:00Z"


def test_three_quiet_bars_after_the_alert_end_the_window(sim):
    sim.start()
    sim.filled()
    sim.play({0: N, 1: N, 2: N})
    assert sim.sig()["follow"]["state"] == signals.WAITING
    sim.play({3: N})                                                 # the last of the slots A..A+3
    e = sim.last("no_fill")
    assert e["reason"] == "window" and e["bar_utc"] == "2026-11-19T00:45:00Z" and "No fill" in sim.texts()[-1]


def test_the_stop_in_bar_a_voids_before_any_fill(sim):
    sim.start()
    sim.filled()
    sim.play({0: (100.3, 100.6, 97.9, 98.5)})
    assert sim.last("no_fill")["reason"] == "stop"


def test_fill_target_1_then_target_2_with_r_on_e0(sim):
    sim.start()
    sim.filled()
    sim.play({0: N, 1: TOUCH, 2: (101.0, 103.5, 100.6, 103.2), 3: (103.2, 105.5, 102.5, 105.1)})
    assert sim.evs() == ["signal", "levels", "filled", "t1", "closed"]
    c = sim.last("closed")
    fee = signals.fee_side("BTCUSDT")
    avg = 0.5 * 103.0 + 0.5 * 105.0
    net = (avg - E0) / E0 - fee * (E0 + avg) / E0
    assert c["why"] == "t2" and c["pct"] == pytest.approx(100 * net) and c["r"] == pytest.approx(net * E0 / 2.0)


def test_the_models_own_exit_is_followed_one_bar_later(sim):
    sim.start()
    sim.filled()
    sim.play({0: N, 1: TOUCH})
    sim.view = {"status": "FLAT", "trades": 1, "wins": 0}
    sim.trade_row(0, 2, why="FLIP", p_out=100.8, pct=0.4, r=0.2)
    sim.play({2: N}, minute=46)                                      # the exit alert goes out in bar 3
    assert sim.last("model_exit")["alert_bar_utc"] == "2026-11-19T00:45:00Z"
    sim.play({3: N, 4: (100.9, 101.2, 100.4, 101.0)})
    c = sim.last("closed")
    assert c["why"] == "model" and c["px"] == 100.9 and sim.st()["open"] == {}


def test_an_instant_stop_out_takes_its_levels_from_the_trade_file(sim):
    sim.start()
    sim.view = {"status": "FLAT", "trades": 1, "wins": 0}             # the page never shows the position
    sim.trade_row(0, 0, why="STOP")
    sim.play({0: (100.3, 100.4, 97.5, 97.8)})
    assert sim.evs() == ["signal", "levels", "book_closed", "no_fill"]
    assert sim.last("levels")["source"] == "trades" and sim.last("no_fill")["reason"] == "stop"
    assert sim.st()["open"] == {}


def test_target_1_already_taken_on_the_page_waits_for_the_trade_file(sim):
    sim.start()
    sim.filled(stop=100.3, t1_taken=True)
    sim.view["stop"] = 100.3
    sim.play({0: N, 1: TOUCH})
    assert sim.evs() == ["signal"] and sim.sig()["follow"]["state"] == se.AWAIT
    sim.view = {"status": "FLAT", "trades": 1, "wins": 1}
    sim.trade_row(0, 2, why="T1+STOP_BE", p_out=101.65, pct=1.3, r=0.6)
    sim.play({2: (101.0, 103.4, 100.8, 102.0)})
    assert sim.evs()[:3] == ["signal", "levels", "book_closed"] and sim.last("levels")["stop"] == 98.0
    assert "filled" in sim.evs() and "t1" in sim.evs()                # bar 1 filled at E0, bar 2 took Target 1


def test_levels_that_never_come_end_as_no_fill(sim):
    sim.start()
    sim.view = {"status": "FLAT", "trades": 0, "wins": 0}             # the order is gone, nothing in the trade file
    sim.check(20)
    assert sim.sig()["follow"]["state"] == se.AWAIT
    sim.check(20 + 31)
    assert sim.last("no_fill")["reason"] == "levels" and "gave no stop and targets" in sim.texts()[-1]
    assert sim.st()["open"] == {}


# ------------------------------------------------------------------ the files: idempotent and restart-safe
def test_running_twice_changes_nothing_and_a_failed_send_is_retried(sim):
    sim.check(-10)
    sim.pend()
    sim.deliver = False
    sim.check(2)
    assert sim.st()["open"] == {} and sim.events() == []             # not delivered: not a signal
    sim.deliver = True
    sim.check(3)
    assert len(sim.sent) == 1 and sim.sig()["sent_ms"] == signals._ms(at(3))
    state, log = open(sim.state).read(), open(sim.log).read()
    sim.check(3)
    sim.check(4)
    assert open(sim.state).read() == state and open(sim.log).read() == log and len(sim.sent) == 1
    sim.filled()
    sim.play({0: N, 1: TOUCH})
    n = len(sim.sent)
    sim.play({}, minute=31)                                           # the same records again (a restart reads the files)
    assert len(sim.sent) == n


def test_a_broken_state_file_is_never_replaced(sim):
    sim.start()
    with open(sim.state, "w") as fh:
        fh.write("{half")
    with pytest.raises(ValueError):
        sim.check(5)


# ------------------------------------------------------------------ the pairing with S1
def s1_events(sim, key, filled=True, pct=None):
    rows = [{"t": "2026-11-19T00:16:10Z", "k": "start", "ev": "start", "live_since": "2026-11-18T00:00:00Z"},
            {"t": "2026-11-19T00:16:10Z", "id": "BTC-1119-01", "k": key, "ev": "signal", "asset": "BTCUSDT", "side": 1}]
    if filled:
        rows.append({"t": "2026-11-19T00:46:10Z", "id": "BTC-1119-01", "k": key, "ev": "filled", "asset": "BTCUSDT"})
        if pct is not None:
            rows.append({"t": "2026-11-19T01:16:10Z", "id": "BTC-1119-01", "k": key, "ev": "closed", "asset": "BTCUSDT",
                         "pct": pct, "r": 0.1})
    else:
        rows.append({"t": "2026-11-19T01:31:10Z", "id": "BTC-1119-01", "k": key, "ev": "no_fill", "asset": "BTCUSDT",
                     "reason": "window"})
    signals.append_log(sim.s1_log, rows)


def test_paired_with_s1_on_the_same_entry(sim):
    sim.start()
    sim.filled()
    sim.play({0: N, 1: TOUCH, 2: (101.0, 103.5, 100.6, 103.2), 3: (103.2, 105.5, 102.5, 105.1)})
    p = se.scoreboard(sim.log, sim.s1_log)["paired"]
    assert p["n"] == 0 and p["waiting"] == 1                          # S1 has no record yet and the book is still open
    s1_events(sim, "BTCUSDT|2026-11-19 00:00", pct=0.5)
    sb = se.scoreboard(sim.log, sim.s1_log)
    p, early = sb["paired"], sb["early"]
    c = sim.last("closed")
    assert p["n"] == 1 and p["no_regular"] == 0 and p["rows"][0]["entry_k"] == "BTCUSDT|2026-11-19 00:00"
    assert p["diff_mean_pct"] == pytest.approx(round(c["pct"] - 0.5, 3)) and p["early_fill_pct"] == 100.0
    assert p["regular_fill_pct"] == 100.0 and early["sent"] == 1 and early["filled"] == 1 and sb["regular_fill_pct"] == 100.0
    card = se.record_card(sim.log, sim.s1_log, sim.st())
    assert "Early signals · the record" in card and "Paired signals" in card and "Difference" in card
    assert "Live since 18 Nov 2026" in card and card.endswith("not financial advice.</i>") and "edge" not in card.lower()


def test_an_s1_no_fill_counts_zero_in_the_pair(sim):
    sim.start()
    sim.filled()
    sim.play({0: N, 1: N, 2: N, 3: N})                                # S2: no fill
    s1_events(sim, "BTCUSDT|2026-11-19 00:00", filled=False)
    p = se.scoreboard(sim.log, sim.s1_log)["paired"]
    assert p["n"] == 1 and p["diff_mean_pct"] == 0.0 and p["early_fill_pct"] == 0.0 and p["regular_fill_pct"] == 0.0


def test_an_s2_with_no_s1_counterpart_pairs_against_zero(sim):
    sim.start()
    sim.view = {"status": "FLAT", "trades": 1, "wins": 0}
    sim.trade_row(0, 0, why="STOP")
    sim.play({0: (100.3, 100.4, 97.5, 97.8)})
    p = se.scoreboard(sim.log, sim.s1_log)["paired"]
    assert p["n"] == 1 and p["no_regular"] == 1 and p["diff_mean_pct"] == 0.0 and p["regular_fill_pct"] is None
    card = se.record_card(sim.log, sim.s1_log)
    assert "1 of them had no regular signal" in card


def test_recap_line(sim):
    assert se.recap_line(sim.log, sim.s1_log, at(60 * 24)).endswith("no early signals yet.")
    sim.start()
    line = se.recap_line(sim.log, sim.s1_log, at(60 * 24 + 1))
    assert line.startswith(u"\U0001f9ea Early signal preview: yesterday 1 sent; in all 1 sent, 0% filled")
