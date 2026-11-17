# -*- coding: utf-8 -*-
"""signals: every branch of H53's followable rules on synthetic bars and page views, the two records, the cards, the
record, and the files it keeps (idempotent, restart-safe, a bar file caught half-written changes nothing)."""
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from engine15 import reports, signals  # noqa: E402

DAY = datetime(2026, 11, 17, tzinfo=timezone.utc)
T0 = signals._ms(DAY)
BAR = signals.BAR_MS
N = (101.0, 101.5, 100.5, 101.0)        # a quiet bar of the long case: holds neither E=100, S=98 nor Target 1=103
TOUCH = (100.5, 101.0, 99.5, 100.2)     # holds E only
CSV_HEAD = ("t_in_ms,t_out_ms,side,p_in,p_out,why_in,why_out,pnl_pct,equity,qty,pnl_usd,fees_usd,stop0,risk_usd,r_mult,"
            "target_1,target_2,time_in,time_out")


def ts(k):
    return T0 + k * BAR


def at(minute):
    return DAY + timedelta(minutes=minute)


def utc(ms):
    return signals._dt(ms).strftime("%Y-%m-%d %H:%M")


class Sim(object):
    """One market, a fake page and fake files. Bar k opens at 00:00 + 15k minutes on 17 Nov 2026. The book fills at the
    open of bar 0; the page shows it after bar 0 closed, so the alert goes out in bar 1 (bar A) and bars 2..5 may fill."""

    def __init__(self, tmp, side=1, E=100.0, S=98.0, T1=103.0, T2=105.0, asset="BTCUSDT", group="crypto"):
        self.asset, self.group, self.side, self.levels = asset, group, side, (E, S, T1, T2)
        self.data, self.live = str(tmp / "data"), str(tmp / "live")
        os.makedirs(self.data)
        os.makedirs(self.live)
        self.state, self.log = os.path.join(self.data, "signals_state.json"), os.path.join(self.data, "signals_log.jsonl")
        self.sent, self.bars, self.deliver, self.view = [], {}, True, {"status": "FLAT", "trades": 0, "wins": 0}
        self.voices = [{"voice": "levels", "title": "Support and resistance", "pull_pts": 3.0 * side},
                       {"voice": "kr", "title": "Kronos candle forecast (live only)", "pull_pts": 2.0 * side},
                       {"voice": "regime", "title": "Market regime", "pull_pts": 0.4 * side},
                       {"voice": "trend", "title": "Timeframe strength, 15m to weekly", "pull_pts": 0.2 * side},
                       {"voice": "x", "title": "Momentum", "pull_pts": -0.5 * side}]

    def send(self, text, reply_to=None):
        if not self.deliver:
            return False, None
        self.sent.append((text, reply_to))
        return True, 500 + len(self.sent)

    def open(self, k=0, **kw):
        E, S, T1, T2 = self.levels
        self.view = dict({"status": "LONG" if self.side > 0 else "SHORT", "entry": E, "stop": S, "opened_utc": utc(ts(k)),
                          "opened_by": "ENTER", "target_1": T1, "target_2": T2, "t1_taken": False, "trades": 0}, **kw)

    def book_closes(self, k_out, why="FLIP", p_out=101.0, pct=0.8, r=0.4, k_in=0):
        path = signals.trades_path(self.live, self.asset)
        new = not os.path.exists(path)
        with io.open(path, "a", encoding="utf-8") as fh:
            fh.write((CSV_HEAD + "\n" if new else "") + "%d,%d,%d,%s,%s,ENTER,%s,%s,10000,1,%s,2,%s,200,%s,%s,%s,%s,%s\n" % (
                ts(k_in), ts(k_out), self.side, self.levels[0], p_out, why, pct, pct * 100, self.levels[1], r,
                self.levels[2], self.levels[3], utc(ts(k_in)), utc(ts(k_out))))
        self.view = {"status": "FLAT", "trades": 1, "wins": 1}

    def write_bars(self, raw=None):
        with io.open(signals.bar_path(self.data, self.asset), "wb") as fh:
            if raw is not None:
                fh.write(raw)
                return
            fh.write(b"ts_ms,open,high,low,close,volume,taker_buy\n")
            for k in sorted(self.bars):
                fh.write(("%d,%s,%s,%s,%s,1.0,\n" % ((ts(k),) + tuple(self.bars[k]))).encode())

    def page(self, upto):
        return {"generated_utc": "x", "markets": {self.group: [self.asset]},
                "assets": {self.asset: {"short": "BTC", "market_group": self.group, "structure": "uptrend on every horizon",
                                        "voices": self.voices, "decision": "HOLD", "price": 100.0}},
                "shadows": {"books": {signals.BOOK: {"title": "B", "assets": {self.asset: self.view}}},
                            "markets": {self.group: {"as_of_utc": utc(ts(upto + 1))}}}}

    def check(self, minute, upto=None):
        upto = minute // 15 - 1 if upto is None else upto            # the page has reached the last closed bar
        return signals.run(self.page(upto), at(minute), self.send, self.data, self.live, self.state, self.log)

    def play(self, bars, minute=None):
        """Add bars {k: (o, h, l, c)} and check one minute after the last of them closed."""
        self.bars.update(bars)
        self.write_bars()
        return self.check((max(self.bars) + 1) * 15 + 1 if minute is None else minute)

    def start(self, **view):
        """The preview starts with a flat book; then the book opens at bar 0 and the alert goes out in bar 1 (bar A)."""
        self.check(-30)
        self.open(**view)
        self.bars[0] = N
        self.write_bars()
        return self.check(16)

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


# ------------------------------------------------------------------ a signal is issued
def test_first_run_does_not_signal_positions_already_open(sim):
    sim.open(k=-40)
    info = sim.check(-30)                                            # the preview starts: this position is old
    assert info["started"] and sim.sent == [] and sim.st()["seen"] == {"BTCUSDT": utc(ts(-40))}
    log = signals.read_log(sim.log)
    assert [e["ev"] for e in log] == ["start", "seen_not_signalled"] and sim.st()["open"] == {}
    sim.check(-29)
    assert sim.sent == []
    sim.open(k=0)                                                    # the NEXT new position is the first signal
    sim.bars[0] = N
    sim.write_bars()
    info = sim.check(16)
    assert info["new"] == 1 and len(sim.sent) == 1 and sim.evs() == ["signal"]
    assert "Live since 16 Nov 2026: positions already open then were not signalled." in signals.recap_card(
        sim.log, at(24 * 60), sim.st())


def test_a_position_opened_before_the_preview_but_seen_later_is_not_signalled(sim):
    sim.check(60)                                                    # the preview starts at 01:00
    sim.open(k=0)                                                    # opened 00:00, its bar closed before the start
    sim.check(61)
    assert sim.sent == [] and sim.st()["seen"]["BTCUSDT"] == utc(ts(0)) and sim.st()["open"] == {}


def test_signal_card_and_record_of_the_signal(sim):
    sim.start()
    s = sim.sig()
    assert s["id"] == "BTC-1117-01" and s["side"] == 1 and (s["entry"], s["stop"], s["t1"], s["t2"]) == (100.0, 98.0, 103.0, 105.0)
    assert s["f_ms"] == ts(0) and s["a_ms"] == ts(1) and s["valid_until_ms"] == ts(6)   # the close of the 4th bar after A
    assert s["fee"] == 0.001 and s["msg_id"] == 501 and s["follow"]["state"] == "WAITING"
    card, reply = sim.sent[0]
    assert reply is None and "BUY BTC" in card and "BTC-1117-01" in card and "Limit order at <b>100.000</b>" in card
    assert "Valid until <b>01:30 UTC</b>" in card
    assert "Stop          98.00  2.00  1.0" in card and "Target 1    103.000  3.00  1.5" in card
    assert "Target 2    105.000  5.00  2.5" in card
    assert 'Why: market structure reads "uptrend on every horizon"; strongest on the buy side: Support and resistance, ' \
           'Market regime and Timeframe strength.' in card
    assert card.endswith("Paper signal from a model, not financial advice.</i>")
    e = sim.last("signal")
    assert e["entry"] == 100.0 and e["bar_a_utc"] == "2026-11-17T00:15:00Z" and e["valid_until_utc"] == "2026-11-17T01:30:00Z"


def test_ids_count_per_market_and_day(sim):
    sim.start()
    sim.book_closes(1, why="FLIP")
    sim.open(k=2)
    sim.play({1: N, 2: N})
    ids = [e["id"] for e in sim.events() if e["ev"] == "signal"]
    assert ids == ["BTC-1117-01", "BTC-1117-02"]


def test_a_card_that_is_not_delivered_is_not_a_signal(sim):
    sim.check(-30)
    sim.open()
    sim.bars[0] = N
    sim.write_bars()
    sim.deliver = False
    sim.check(16)
    assert sim.st()["open"] == {} and sim.evs() == []
    sim.deliver = True
    sim.check(31)                                                    # sent one bar later: bar A is the bar of the send
    assert sim.sig()["a_ms"] == ts(2) and sim.sig()["id"] == "BTC-1117-01"


def test_target_1_already_taken_before_the_alert_is_a_no_fill_at_once(sim):
    sim.start(t1_taken=True, stop=100.0)
    assert sim.evs() == ["signal", "no_fill"] and sim.last("no_fill")["reason"] == "target"
    assert "do not enter" in sim.sent[0][0] and "No fill: signal expired" in sim.sent[1][0]


def test_incomplete_levels_are_seen_but_not_signalled(sim):
    sim.check(-30)
    sim.open(target_1=None)
    sim.check(16)
    assert sim.sent == [] and sim.st()["seen"]["BTCUSDT"] == utc(ts(0))
    assert signals.read_log(sim.log)[-1]["ev"] == "seen_not_signalled"


# ------------------------------------------------------------------ rule 1: the entry
@pytest.mark.parametrize("n", [1, 2, 3, 4])
def test_fill_on_each_of_the_four_bars_after_bar_a(sim, n):
    sim.start()
    bars = dict((k, N) for k in range(1, 1 + n))
    bars[1 + n] = TOUCH
    sim.play(bars)
    f = sim.sig()["follow"]
    assert f["state"] == "FILLED" and f["fill_ms"] == ts(1 + n) and f["bars_after_a"] == n
    assert sim.evs() == ["signal", "filled"] and sim.last("filled")["px"] == 100.0
    text, reply = sim.sent[-1]
    assert "Entry filled" in text and reply == 501                   # a reply to the signal's own message


def test_bar_a_touch_is_not_a_fill_and_the_window_passes(sim):
    sim.start()
    sim.play({1: TOUCH, 2: N, 3: N, 4: N})                           # bar A holds E: it never counts
    assert sim.sig()["follow"]["state"] == "WAITING" and sim.evs() == ["signal"]
    sim.play({5: N})                                                 # the fourth bar after A passes
    assert sim.evs() == ["signal", "no_fill"] and sim.last("no_fill")["reason"] == "window"
    assert sim.last("no_fill")["bar_utc"] == "2026-11-17T01:15:00Z"
    sim.play({6: TOUCH})                                             # a fifth bar is too late
    assert sim.evs() == ["signal", "no_fill"]
    assert "the entry window passed" in sim.sent[-1][0] and sim.sent[-1][1] == 501


def test_the_window_is_also_the_stated_validity_when_the_market_shuts(sim):
    sim.start()
    sim.play({1: N, 2: N})
    sim.play({40: TOUCH})                                            # the next bar the market prints is hours later
    assert sim.evs() == ["signal", "no_fill"] and sim.last("no_fill")["reason"] == "window"


def test_the_window_passes_by_the_page_clock_when_bars_are_missing(sim):
    sim.start()
    sim.play({1: N, 2: N})
    sim.check(91, upto=4)                                            # the page has reached 01:15: still inside the validity
    assert sim.evs() == ["signal"]
    sim.check(106, upto=5)                                           # ... and now the close of the fourth slot, 01:30
    assert sim.evs() == ["signal", "no_fill"] and sim.last("no_fill")["reason"] == "window"


# ------------------------------------------------------------------ rule 2: no fill
@pytest.mark.parametrize("bar,reason", [
    ((101.0, 101.5, 97.9, 99.0), "stop"),                            # the stop trades (and the bar holds E too)
    ((101.0, 103.1, 100.5, 102.0), "target"),                        # Target 1 trades
    ((100.5, 103.0, 99.5, 102.0), "target"),                         # a bar that holds E and Target 1 together
    ((100.5, 101.0, 98.0, 99.0), "stop"),                            # a bar that holds E and S together
    ((100.5, 103.5, 97.5, 99.0), "stop")])                           # all three
@pytest.mark.parametrize("k", [1, 3])                                # in bar A itself, or in a later bar before the fill
def test_stop_or_target_before_the_fill_is_a_no_fill(sim, bar, reason, k):
    sim.start()
    bars = dict((j, N) for j in range(1, k))
    bars[k] = bar
    bars[k + 1] = TOUCH                                              # would have filled afterwards
    sim.play(bars)
    assert sim.evs() == ["signal", "no_fill"] and sim.last("no_fill")["reason"] == reason
    assert sim.sig()["follow"]["state"] == "NO_FILL"
    assert signals.scoreboard(signals.read_log(sim.log))["follow"]["n"] == 0     # a signal sent, not a trade


def test_book_closes_before_the_fill(sim):
    sim.start()
    sim.play({1: N, 2: N})
    sim.book_closes(3, why="FLIP", pct=0.5, r=0.25)                  # the book left at the open of bar 3 ...
    sim.play({3: TOUCH})                                             # ... so bar 3 cannot fill
    assert sim.evs() == ["signal", "book_closed", "no_fill"] and sim.last("no_fill")["reason"] == "model"
    assert "the model closed its own trade before the entry filled" in sim.sent[-1][0]
    assert sim.st()["open"] == {}                                    # both records final: only the log keeps it
    sb = signals.scoreboard(signals.read_log(sim.log))
    assert (sb["sent"], sb["filled"], sb["no_fill"], sb["fill_rate_pct"]) == (1, 0, 1, 0.0)
    assert sb["book_of_no_fill"]["n"] == 1 and sb["book_of_no_fill"]["net_pct"] == 0.5 and sb["book_of_no_fill"]["net_r"] == 0.25


def test_a_fill_in_a_bar_before_the_book_closed_stands(sim):
    sim.start()
    sim.book_closes(3, why="FLIP")
    sim.play({1: N, 2: TOUCH, 3: N}, minute=61)                      # all seen at once: bar 2 is before the book's exit
    assert sim.evs()[:3] == ["signal", "book_closed", "filled"]


def test_book_stop_while_waiting_reads_as_the_stop(sim):
    sim.start()
    sim.book_closes(2, why="STOP", pct=-2.2, r=-1.1)
    sim.play({1: N, 2: (100.2, 100.4, 100.1, 100.3)})                # the page's rounded stop did not quite trade
    assert sim.last("no_fill")["reason"] == "stop"


def test_a_closed_book_trade_missing_from_its_file_waits_then_goes_on(sim):
    sim.start()
    sim.view = {"status": "FLAT"}                                    # the page says closed, the file has no row yet
    sim.play({1: N, 2: TOUCH})
    assert sim.evs() == ["signal"] and sim.sig()["follow"]["last_bar_ms"] == ts(-1)   # nothing advanced
    sim.check(46 + 31)                                               # half an hour on: without the row
    assert sim.evs() == ["signal", "book_closed", "no_fill"] and sim.last("book_closed")["known"] is False


def test_a_market_missing_from_the_page_is_not_a_close(sim):
    sim.start()
    page = sim.page(1)
    page["shadows"]["books"][signals.BOOK]["assets"] = {}
    signals.run(page, at(31), sim.send, sim.data, sim.live, sim.state, sim.log)
    assert sim.sig()["book"]["closed"] is False and sim.evs() == ["signal"]


# ------------------------------------------------------------------ rule 3: after the fill
def filled(sim, **view):
    sim.start(**view)
    sim.play({1: N, 2: TOUCH})
    assert sim.sig()["follow"]["state"] == "FILLED"
    return sim


def test_target_1_then_target_2(sim):
    filled(sim)
    sim.play({3: (101.0, 103.5, 100.5, 103.2)})
    f = sim.sig()["follow"]
    assert f["state"] == "T1_TAKEN" and f["exits"] == [[103.0, 0.5, "t1"]]
    assert "Target 1 hit: take half, move stop to entry" in sim.sent[-1][0] and sim.sent[-1][1] == 501
    sim.play({4: (103.2, 105.2, 102.9, 105.0)})
    c = sim.last("closed")
    assert sim.evs() == ["signal", "filled", "t1", "closed"] and c["why"] == "t2" and c["px"] == 105.0
    assert c["pct"] == pytest.approx(4.0 - 0.1 * 2.04) and c["r"] == pytest.approx(3.796 / 2.0)     # half at 103, half at 105
    assert c["usd"] == pytest.approx(379.6) and c["avg_exit"] == pytest.approx(104.0)
    assert "Target 2 hit: closed" in sim.sent[-1][0] and "+3.80%" in sim.sent[-1][0] and "+1.90R" in sim.sent[-1][0]


def test_target_1_then_stop_at_entry(sim):
    filled(sim)
    sim.play({3: (101.0, 103.5, 100.5, 103.2), 4: (102.0, 102.5, 99.9, 100.1)})
    c = sim.last("closed")
    assert c["why"] == "stop_be" and c["px"] == 100.0 and c["pct"] == pytest.approx(1.5 - 0.1 * 2.015)
    assert "Stopped at entry" in sim.sent[-1][0]


def test_target_1_and_target_2_in_one_bar(sim):
    filled(sim)
    sim.play({3: (101.0, 105.5, 100.5, 105.0)})
    assert sim.evs() == ["signal", "filled", "t1", "closed"] and sim.last("closed")["why"] == "t2"


def test_the_bar_that_takes_target_1_and_holds_the_entry_stops_the_rest_at_entry(sim):
    filled(sim)
    sim.play({3: (101.0, 105.5, 99.8, 105.0)})                       # Target 1, Target 2 and E in one bar: the stop
    c = sim.last("closed")
    assert sim.evs() == ["signal", "filled", "t1", "closed"] and c["why"] == "stop_be" and c["px"] == 100.0


def test_stop_and_target_in_one_bar_is_the_stop(sim):
    filled(sim)
    sim.play({3: (101.0, 103.5, 97.9, 99.0)})
    c = sim.last("closed")
    assert sim.evs() == ["signal", "filled", "closed"] and c["why"] == "stop" and c["px"] == 98.0
    assert c["pct"] == pytest.approx(-2.0 - 0.1 * 1.98) and c["r"] == pytest.approx(-2.198 / 2.0)
    assert "<b>Stopped</b>" in sim.sent[-1][0] and "-2.20%" in sim.sent[-1][0] and "-1.10R" in sim.sent[-1][0]


def test_stop_and_target_2_in_one_bar_after_target_1_is_the_stop(sim):
    filled(sim)
    sim.play({3: (101.0, 103.5, 100.5, 103.2), 4: (103.0, 105.5, 99.9, 104.0)})
    assert sim.last("closed")["why"] == "stop_be" and sim.last("closed")["px"] == 100.0


def test_a_gap_through_the_stop_fills_at_the_open(sim):
    filled(sim)
    sim.play({3: (97.0, 97.5, 96.0, 96.5)})
    c = sim.last("closed")
    assert c["why"] == "stop" and c["px"] == 97.0 and c["pct"] == pytest.approx(-3.0 - 0.1 * 1.97)


def test_a_gap_through_the_entry_stop_after_target_1_fills_at_the_open(sim):
    filled(sim)
    sim.play({3: (101.0, 103.5, 100.5, 103.2), 4: (99.0, 99.5, 98.5, 99.2)})
    c = sim.last("closed")
    assert c["why"] == "stop_be" and c["px"] == 99.0 and c["avg_exit"] == pytest.approx(101.0)


def test_short_side_mirrors(tmp_path):
    sim = Sim(tmp_path, side=-1, E=100.0, S=102.0, T1=97.0, T2=95.0, asset="XAUUSD", group="metals")
    sim.start()
    assert "SELL Gold" in sim.sent[0][0] and sim.sig()["id"] == "XAU-1117-01" and sim.sig()["fee"] == 0.0002
    sim.play({1: (99.0, 99.5, 98.5, 99.0), 2: (99.5, 100.5, 99.0, 99.8)})          # bar 2 holds E
    sim.play({3: (99.0, 99.5, 96.8, 97.2), 4: (97.0, 97.5, 94.9, 95.0)})
    c = sim.last("closed")
    assert sim.evs() == ["signal", "filled", "t1", "closed"] and c["why"] == "t2"
    assert c["pct"] == pytest.approx(4.0 - 0.02 * 1.96) and c["r"] == pytest.approx((4.0 - 0.0392) / 2.0)


def test_short_stop_gap(tmp_path):
    sim = Sim(tmp_path, side=-1, E=100.0, S=102.0, T1=97.0, T2=95.0)
    sim.start()
    sim.play({1: (99.0, 99.5, 98.5, 99.0), 2: (99.5, 100.5, 99.0, 99.8), 3: (103.0, 103.5, 102.5, 103.0)})
    assert sim.last("closed")["why"] == "stop" and sim.last("closed")["px"] == 103.0


# ------------------------------------------------------------------ rule 4: the book closes its own trade
def test_book_exit_closes_at_the_open_of_the_bar_after_the_exit_alert(sim):
    filled(sim)
    sim.book_closes(4, why="FLIP", p_out=101.0, pct=0.8, r=0.4)      # the book left at the open of bar 4
    sim.play({3: N, 4: N})                                           # seen at 01:16, in bar 5: the exit alert goes now
    f = sim.sig()["follow"]
    assert sim.evs() == ["signal", "filled", "book_closed", "model_exit"] and f["exit_alert_ms"] == ts(5)
    assert f["state"] == "FILLED" and "exit now" in sim.sent[-1][0] and sim.sent[-1][1] == 501
    sim.play({5: N})                                                 # the alert's own bar: still open
    assert sim.sig()["follow"]["state"] == "FILLED"
    sim.play({6: (101.2, 101.6, 100.9, 101.4)})                      # closed at the OPEN of the bar after it
    c = sim.last("closed")
    assert c["why"] == "model" and c["px"] == 101.2 and c["bar_utc"] == "2026-11-17T01:30:00Z"
    assert c["pct"] == pytest.approx(1.2 - 0.1 * 2.012)
    assert "Closed by the model" in sim.sent[-1][0] and sim.st()["open"] == {}
    sb = signals.scoreboard(signals.read_log(sim.log))
    assert sb["follow"]["n"] == 1 and sb["book_same"]["n"] == 1 and sb["book_same"]["net_pct"] == 0.8
    assert sb["book_of_filled"]["net_r"] == 0.4 and sb["book_of_no_fill"]["n"] == 0


def test_the_stop_stays_live_in_the_exit_alert_bar(sim):
    filled(sim)
    sim.book_closes(4, why="FLIP")
    sim.play({3: N, 4: N})
    sim.play({5: (101.0, 101.2, 97.5, 98.2), 6: N})
    assert sim.last("closed")["why"] == "stop" and sim.last("closed")["bar_utc"] == "2026-11-17T01:15:00Z"


def test_book_exit_after_target_1_closes_the_rest_at_the_next_open(sim):
    filled(sim)
    sim.play({3: (101.0, 103.5, 100.5, 103.2)})
    sim.book_closes(4, why="T1+FLIP")
    sim.play({4: (103.0, 103.4, 102.0, 102.5)})
    sim.play({5: (102.5, 102.8, 102.1, 102.4), 6: (102.4, 102.6, 102.0, 102.2)})
    c = sim.last("closed")
    assert c["why"] == "model" and c["px"] == 102.4 and c["avg_exit"] == pytest.approx(102.7)


def test_book_and_followable_stopped_in_the_same_bar_need_no_exit_alert(sim):
    filled(sim)
    sim.book_closes(3, why="STOP", p_out=98.0, pct=-2.2, r=-1.1)
    sim.play({3: (101.0, 101.2, 97.5, 98.2)})
    assert sim.evs() == ["signal", "filled", "book_closed", "closed"] and sim.last("closed")["why"] == "stop"


# ------------------------------------------------------------------ rule 5: costs
def test_fees_are_the_book_arithmetic_and_the_market_fee():
    assert signals.fee_side("BTCUSDT") == 0.001 and signals.fee_side("USDJPY") == 0.0001 and signals.fee_side("WTI") == 0.0004
    r = signals.result(1, 200.0, 190.0, 0.001, [(210.0, 0.5), (220.0, 0.5)])
    qty = signals.NOTIONAL / 200.0                                   # shadows.run: gross - fee * q * (entry + price) per part
    usd = 0.5 * qty * (210.0 - 200.0) + 0.5 * qty * (220.0 - 200.0) - 0.001 * 0.5 * qty * (200.0 + 210.0) \
        - 0.001 * 0.5 * qty * (200.0 + 220.0)
    assert r["usd"] == pytest.approx(usd) and r["pct"] == pytest.approx(usd / 100.0) and r["r"] == pytest.approx(usd / (qty * 10.0))
    assert signals.result(-1, 100.0, 100.0, 0.0, [(99.0, 1.0)])["r"] is None      # no stop distance: no R


# ------------------------------------------------------------------ once only, and the files
def test_idempotent_and_restart_safe(sim):
    filled(sim)
    state, log, n = io.open(sim.state).read(), io.open(sim.log).read(), len(sim.sent)
    for _ in range(3):                                               # the same bars again, each time from the files
        sim.check(46)
    assert io.open(sim.state).read() == state and io.open(sim.log).read() == log and len(sim.sent) == n
    sim.play({3: (101.0, 103.5, 100.5, 103.2)})
    sim.check(61)
    sim.check(62)
    assert sim.evs() == ["signal", "filled", "t1"] and len(sim.sent) == n + 1
    assert not os.path.exists(sim.state + ".tmp")                    # written through a temp file and os.replace


def test_bars_beyond_the_page_are_not_processed(sim):
    sim.start()
    sim.bars.update({1: N, 2: TOUCH})
    sim.write_bars()
    sim.check(46, upto=1)                                            # the bar file is ahead of the page's shadow books
    assert sim.sig()["follow"]["last_bar_ms"] == ts(1) and sim.evs() == ["signal"]
    sim.check(47, upto=2)
    assert sim.evs() == ["signal", "filled"]


@pytest.mark.parametrize("raw", [
    b"", b"ts_ms,open,high,low,close,volume,taker_buy\n", None,
    b"ts_ms,open,high,low,close,volume,taker_buy\n%d,101,101.5,100.5,101,1,\n%d,100.5,10" % (ts(1), ts(2)),
    b"ts_ms,open,high,low,close,volume,taker_buy\n%d,101,101.5,100.5,101,1,\n\x00\x00garbage\n%d,100.5,101,99.5,100.2,1,\n"
    % (ts(1), ts(2)),
    b"ts_ms,open,high,low,close,volume,taker_buy\n%d,101,101.5,100.5,101,1,\n%d,100.5,101,99.5,100.2,1,\n" % (ts(2), ts(1))])
def test_a_garbled_or_empty_bar_file_changes_nothing(sim, raw):
    sim.start()
    state, log = io.open(sim.state).read(), io.open(sim.log).read()
    if raw is None:
        os.remove(signals.bar_path(sim.data, "BTCUSDT"))
    else:
        sim.write_bars(raw)
    info = sim.check(46)
    if raw is not None and raw.endswith(b",10"):                     # a last line still being written: the whole bars count
        assert sim.sig()["follow"]["last_bar_ms"] == ts(1) and sim.evs() == ["signal"]
    else:
        assert info["bars_unread"] == ["BTCUSDT"]
        assert io.open(sim.state).read() == state and io.open(sim.log).read() == log
    sim.play({1: N, 2: TOUCH})                                       # the file is whole again at the next check
    assert sim.evs() == ["signal", "filled"]


def test_read_bars_reads_only_the_tail_and_reaches_back(tmp_path):
    path = str(tmp_path / "x_15m.csv")
    with io.open(path, "wb") as fh:
        fh.write(b"ts_ms,open,high,low,close,volume,taker_buy\n")
        for k in range(5000):
            fh.write(b"%d,100.0,101.0,99.0,100.5,1.0,\n" % ts(k))
    got = signals.read_bars(path, ts(4996), chunk=64)                # a tiny first chunk grows until it reaches back
    assert [b[0] for b in got] == [ts(4997), ts(4998), ts(4999)] and got[0][1:] == (100.0, 101.0, 99.0, 100.5)
    assert signals.read_bars(path, ts(4999)) == []                   # read fine, nothing new: not a failure
    assert signals.read_bars(path, ts(10), chunk=64, cap=256) is None            # cannot reach back: not trusted
    assert signals.read_bars(str(tmp_path / "none.csv"), 0) is None


def test_a_state_file_that_cannot_be_read_is_never_replaced(sim):
    sim.start()
    with io.open(sim.state, "w") as fh:
        fh.write(u"{half")
    with pytest.raises(ValueError):
        sim.check(31)
    assert io.open(sim.state).read() == u"{half"


def test_no_page_view_means_no_files(sim):
    info = signals.run({"assets": {}}, at(0), sim.send, sim.data, sim.live, sim.state, sim.log)
    assert info["started"] is False and not os.path.exists(sim.state) and not os.path.exists(sim.log)


# ------------------------------------------------------------------ the record and the cards
def full_story(tmp_path):
    """Three signals on one market: a winner (T1 + T2), a no fill the book won, and one still waiting."""
    sim = Sim(tmp_path)
    filled(sim)
    sim.play({3: (101.0, 103.5, 100.5, 103.2), 4: (103.2, 105.2, 102.9, 105.0)})
    sim.book_closes(4, why="T1+T2", p_out=104.0, pct=3.796, r=1.898)
    sim.open(k=6)
    sim.play({5: N, 6: N})                                           # the second signal: alert in bar 7
    sim.book_closes(9, why="FLIP", p_out=101.0, pct=0.8, r=0.4, k_in=6)
    sim.play({7: N, 8: N, 9: N})
    sim.open(k=10)
    sim.play({10: N})                                                # the third: waiting
    return sim


def test_scoreboard_and_record_card(tmp_path):
    sim = full_story(tmp_path)
    sb = signals.scoreboard(signals.read_log(sim.log))
    assert (sb["sent"], sb["filled"], sb["no_fill"], sb["waiting"], sb["in_trade"]) == (3, 1, 1, 1, 0)
    assert sb["fill_rate_pct"] == 33.3 and sb["live_since"] == "2026-11-16T23:30:00Z"
    f = sb["follow"]
    assert f["n"] == 1 and f["won_pct"] == 100.0 and f["net_usd"] == 379.6 and f["net_pct"] == 3.796 and f["net_r"] == 1.898
    assert sb["verdict"] == reports._stats([379.6])["verdict"] == "too few trades to judge (1 of 30)"
    assert sb["book_same"]["n"] == 2 and sb["book_same"]["net_pct"] == pytest.approx(4.596)
    assert sb["book_of_no_fill"]["n"] == 1 and sb["book_of_no_fill"]["net_pct"] == 0.8
    assert sb["gate"]["met"] is False
    card = signals.record_card(sim.log, sim.st())
    assert "Signals sent                 3" in card and "Filled                 1 (33%)" in card
    assert "Net          +1.90R     +3.80%" in card and "Verdict: too few trades to judge (1 of 30)." in card
    assert "The same signals at the model's own entry price: 2 closed, net +4.60% (+2.30R)." in card
    assert "Signals that did not fill would have made, at the model's own price: 1 closed, net +0.80% (+0.40R)." in card


def test_verdict_wording_is_the_scoreboards_own(tmp_path):
    rows = [{"t": "2026-11-17T00:00:00Z", "k": "start", "ev": "start", "live_since": "2026-11-17T00:00:00Z"}]
    usd = []
    for i in range(30):
        k, pct = "BTCUSDT|%d" % i, 1.0 + 0.1 * (i % 5)
        usd.append(100.0 * pct)
        rows += [{"t": "2026-11-17T00:00:00Z", "id": "B-%d" % i, "k": k, "ev": "signal", "side": 1},
                 {"t": "2026-11-17T01:00:00Z", "id": "B-%d" % i, "k": k, "ev": "filled"},
                 {"t": "2026-11-17T02:00:00Z", "id": "B-%d" % i, "k": k, "ev": "closed", "pct": pct, "r": pct / 2, "usd": 100 * pct}]
    sb = signals.scoreboard(rows)
    ref = reports._stats(usd)
    assert sb["verdict"] == ref["verdict"] == "ahead: even the low end of the range is positive"
    assert sb["follow"]["range90_usd"] == ref["range90_usd"] and sb["follow"]["mean_usd"] == ref["mean_usd"]
    assert sb["follow"]["range90_pct"] == [round(x / 100.0, 3) for x in ref["range90_usd"]]


def test_recap_and_open_cards(tmp_path):
    sim = full_story(tmp_path)
    recap = signals.recap_card(sim.log, at(24 * 60), sim.st())       # the next midnight: yesterday is 17 Nov
    assert "daily recap" in recap and "Tue 17 Nov (UTC)" in recap and "Running record" in recap
    assert "BTC-1117-01 BUY         +1.90R" in recap and "BTC-1117-02 BUY        no fill" in recap
    assert "BTC-1117-03 BUY        waiting" in recap and "Live since 16 Nov 2026" in recap
    assert "No signals yesterday." in signals.recap_card(sim.log, at(3 * 24 * 60), sim.st())
    card = signals.open_card(sim.st())
    assert "BTC-1117-03 BUY        waiting" in card and "limit 100.000 to 04:00" in card and "BTC-1117-01" not in card
    assert "have not started" in signals.open_card(None)
    sim.play({11: N, 12: TOUCH})
    assert "in trade" in signals.open_card(sim.st()) and "stop 98.00" in signals.open_card(sim.st())


def test_nothing_subscriber_facing_names_the_book_the_research_or_a_dollar_size(tmp_path):
    sim = full_story(tmp_path)
    sim.play({11: N, 12: TOUCH, 13: (101.0, 101.2, 97.5, 98.2)})     # a filled one that is stopped, for its card too
    other = Sim(tmp_path / "b")
    os.makedirs(str(tmp_path / "b"), exist_ok=True)
    filled(other)
    other.book_closes(4, why="FLIP")
    other.play({3: N, 4: N})
    other.play({5: N, 6: N})
    texts = sim.texts() + other.texts() + [signals.record_card(sim.log, sim.st()), signals.open_card(sim.st()),
                                           signals.recap_card(sim.log, at(24 * 60), sim.st())]
    kinds = ("Entry filled", "No fill: signal expired", "Target 1 hit", "Target 2 hit: closed", "<b>Stopped</b>",
             "exit now", "Closed by the model")
    assert all(any(k in t for t in texts) for k in kinds)
    for t in texts:
        low = t.lower()
        assert "b_targets" not in low and "shadow" not in low and "kronos" not in low and "$" not in t
        assert "forecast" not in low and "10,000" not in t and "10000" not in t
        assert t.endswith("Paper signal from a model, not financial advice.</i>")
        for block in t.split("<pre>")[1:]:
            assert all(len(ln) <= 30 for ln in block.split("</pre>")[0].split("\n")), block   # a phone screen


def test_why_sentence_falls_back_to_plain_reasons_and_never_to_internal_names():
    d = {"structure": "mixed", "voices": [], "for_long": [["eld_bull_1d", 0.14], ["daily trend", 0.13], ["last 7 days' move", 0.1]],
         "for_short": [["ma_d200_4h", -0.3], ["regime MOMENTUM_DOWN", -0.2]]}
    assert signals.why_sentence(d, 1) == 'Why: market structure reads "mixed"; strongest on the buy side: daily trend and ' \
                                         "last 7 days' move."
    assert signals.why_sentence(d, -1) == 'Why: market structure reads "mixed", and the model\'s combined reading favours ' \
                                          "the sell side."
    assert signals.why_sentence(None, -1) == "Why: the model's combined reading of this market favours the sell side."
    lib = {"voices": [{"title": "The library's working strategies", "pull_pts": -1.0}, {"title": "The owner's view", "pull_pts": -2}]}
    assert signals.why_sentence(lib, -1) == "Why: strongest on the sell side: Working strategies."


def test_prices_print_with_at_most_three_decimals():
    assert [signals._p(v) for v in (65203.2, 7596.66, 159.765, 47.085, 48.38975, 91.3731, 85.0, 54.10301)] == [
        "65,203.20", "7,596.66", "159.765", "47.085", "48.39", "91.373", "85.00", "54.103"]


def test_log_lines_written_twice_count_once(sim):
    filled(sim)
    with io.open(sim.log, encoding="utf-8") as fh:
        lines = fh.read()
    with io.open(sim.log, "a", encoding="utf-8") as fh:
        fh.write(lines + u"{not json\n")
    assert sim.evs() == ["signal", "filled"] and all(json.loads(ln) for ln in lines.splitlines())
