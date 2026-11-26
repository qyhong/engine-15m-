# -*- coding: utf-8 -*-
"""signals with the trailing-stop voice (docs/TRAIL_SWITCH_PLAN.md section 4): which setups become signals (only the one
setups_voice.published shows, and only while the market's voice is the one the switch asks for), a signal followed in
its OWN book across a change of voice, the trail rules bar by bar, the "stop moved" cards, the two records kept apart,
the early-signal guard, the moving-against alert, and the switch off: nothing new anywhere.

Synthetic bars, hand-made pages, a temp voice state; the switch is turned on by monkeypatching setups_voice.TRAIL_MARKETS.

    py -3 -m pytest tests/test_signals_trail.py -q
"""
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from engine15 import setups_voice, signals, signals_early  # noqa: E402
from engine15 import telegram_notify as tn  # noqa: E402

DAY = datetime(2026, 11, 17, tzinfo=timezone.utc)
T0 = signals._ms(DAY)
BAR = signals.BAR_MS
TARGETS_BOOK, TRAIL_BOOK = "b_targets", "b_trail_setups"
# the long case: E 100, the stop at the alert S0 98, so 1R = 2 and the trail arms at 102
N = (101.0, 101.5, 100.5, 101.0)        # holds neither E, S0 nor 102
TOUCH = (100.5, 101.0, 99.5, 100.2)     # holds E only
UP = (101.0, 102.5, 100.8, 102.3)       # reaches 102: the book's trail arms at this bar's close
CSV_HEAD = ("t_in_ms,t_out_ms,side,p_in,p_out,why_in,why_out,pnl_pct,equity,qty,pnl_usd,fees_usd,stop0,risk_usd,r_mult,"
            "target_1,target_2,time_in,time_out")
SIGNAL_KEYS = {"t", "id", "k", "ev", "asset", "side", "entry", "stop", "t1", "t2", "fee", "opened_utc", "bar_a_utc",
               "valid_until_utc", "msg_id"}                           # the "signal" log line as it was before the trail voice
STATE_KEYS = {"asset", "side", "entry", "stop", "t1", "t2", "fee", "opened_utc", "f_ms", "sent_ms", "a_ms",
              "valid_until_ms", "msg_id", "early_t1", "follow", "book", "id"}     # a signal in the state file, as it was


def ts(k):
    return T0 + k * BAR


def at(minute):
    return DAY + timedelta(minutes=minute)


def utc(ms):
    return signals._dt(ms).strftime("%Y-%m-%d %H:%M")


def iso(k):
    return signals._iso(ts(k))


class Sim(object):
    """One market with BOTH books on the page, fake files and a voice state file of its own. Bar k opens at 00:00 + 15k
    minutes on 17 Nov 2026. A book opens at bar 0; the page shows it after bar 0 closed, so the alert goes out in bar 1
    (bar A) and bars 2..5 may fill."""

    def __init__(self, tmp, side=1, E=100.0, S=98.0, asset="BTCUSDT", group="crypto"):
        self.asset, self.group, self.side, self.E, self.S = asset, group, side, E, S
        self.data, self.live = str(tmp / "data"), str(tmp / "live")
        os.makedirs(self.data)
        os.makedirs(self.live)
        self.state, self.log = os.path.join(self.data, "signals_state.json"), os.path.join(self.data, "signals_log.jsonl")
        self.voice_path = os.path.join(self.data, "setups_voice_state.json")
        self.sent, self.bars = [], {}
        self.views = {TARGETS_BOOK: {"status": "FLAT", "trades": 0, "wins": 0}, TRAIL_BOOK: {"status": "FLAT", "trades": 0}}

    def send(self, text, reply_to=None):
        self.sent.append((text, reply_to))
        return True, 500 + len(self.sent)

    # ---- the engine's side: the voice state, the two books, their trade files, the bars
    def voice(self, rule="trail", from_k=-4, pending=False, wait=None):
        """The state file as setups_voice.save writes it (None: no file)."""
        if rule is None:
            if os.path.exists(self.voice_path):
                os.remove(self.voice_path)
            return
        with io.open(self.voice_path, "w", encoding="utf-8") as fh:
            json.dump({"schema": 1, "markets": {self.asset: {"rule": rule, "from_utc": None if from_k is None else iso(from_k),
                                                             "pending": pending, "wait": wait}}}, fh)

    def open_trail(self, k=0, **kw):
        self.views[TRAIL_BOOK] = dict({"status": "LONG" if self.side > 0 else "SHORT", "entry": self.E, "stop": self.S,
                                       "opened_utc": utc(ts(k)), "opened_by": "ENTER", "unrealized_usd": 0.0, "trades": 0}, **kw)

    def open_targets(self, k=0, T1=103.0, T2=105.0, **kw):
        self.views[TARGETS_BOOK] = dict({"status": "LONG" if self.side > 0 else "SHORT", "entry": self.E, "stop": self.S,
                                         "opened_utc": utc(ts(k)), "opened_by": "ENTER", "target_1": T1, "target_2": T2,
                                         "t1_taken": False, "trades": 0}, **kw)

    def move(self, stop):
        """The trail book publishes a new stop (its trail has armed)."""
        self.views[TRAIL_BOOK] = dict(self.views[TRAIL_BOOK], stop=stop, trailing=True)

    def book_closes(self, k_out, why="TRAIL", book=TRAIL_BOOK, p_out=101.0, pct=0.8, r=0.4, k_in=0):
        path = signals.trades_path(self.live, self.asset, book)
        new = not os.path.exists(path)
        with io.open(path, "a", encoding="utf-8") as fh:
            fh.write((CSV_HEAD + "\n" if new else "") + "%d,%d,%d,%s,%s,ENTER,%s,%s,10000,1,%s,2,%s,200,%s,,,%s,%s\n" % (
                ts(k_in), ts(k_out), self.side, self.E, p_out, why, pct, pct * 100, self.S, r, utc(ts(k_in)), utc(ts(k_out))))
        self.views[book] = {"status": "FLAT", "trades": 1, "wins": 1}

    def write_bars(self):
        with io.open(signals.bar_path(self.data, self.asset), "wb") as fh:
            fh.write(b"ts_ms,open,high,low,close,volume,taker_buy\n")
            for k in sorted(self.bars):
                fh.write(("%d,%s,%s,%s,%s,1.0,\n" % ((ts(k),) + tuple(self.bars[k]))).encode())

    def page(self, upto):
        return {"generated_utc": "x", "markets": {self.group: [self.asset]},
                "assets": {self.asset: {"short": "BTC", "market_group": self.group, "structure": "uptrend on every horizon",
                                        "voices": [{"title": "Support and resistance", "pull_pts": 3.0 * self.side},
                                                   {"title": "Kronos candle forecast", "pull_pts": 2.0 * self.side}],
                                        "decision": "HOLD", "price": 100.0}},
                "shadows": {"books": dict((b, {"title": b, "assets": {self.asset: v}}) for b, v in self.views.items()),
                            "markets": {self.group: {"as_of_utc": utc(ts(upto + 1))}}}}

    # ---- the bot's side
    def check(self, minute, upto=None):
        upto = minute // 15 - 1 if upto is None else upto            # the page has reached the last closed bar
        return signals.run(self.page(upto), at(minute), self.send, self.data, self.live, self.state, self.log,
                           voice_path=self.voice_path)

    def play(self, bars, minute=None):
        """Add bars {k: (o, h, l, c)} and check one minute after the last of them closed."""
        self.bars.update(bars)
        self.write_bars()
        return self.check((max(self.bars) + 1) * 15 + 1 if minute is None else minute)

    def start(self, **view):
        """The preview starts with flat books; the trail book opens at bar 0; the alert goes out in bar 1 (bar A)."""
        self.check(-30)
        self.open_trail(**view)
        self.bars[0] = N
        self.write_bars()
        return self.check(16)

    def st(self):
        return signals.load_state(self.state)

    def sig(self, n=0):
        o = self.st()["open"]
        return o[sorted(o)[n]] if o else None

    def events(self):
        return [e for e in signals.read_log(self.log) if e.get("id")]

    def evs(self, sid=None):
        return [e["ev"] for e in self.events() if sid is None or e["id"] == sid]

    def last(self, ev):
        return [e for e in self.events() if e["ev"] == ev][-1]

    def texts(self):
        return [t for t, _r in self.sent]


@pytest.fixture
def on(monkeypatch):
    """The switch on for BTC (the shipped value is (): see test_the_switch_is_off_in_the_code)."""
    monkeypatch.setattr(setups_voice, "TRAIL_MARKETS", ("BTCUSDT",))


@pytest.fixture
def sim(tmp_path, on):
    """BTC on the trail voice since before the story: the switch on, the engine's state flipped at bar -4."""
    s = Sim(tmp_path)
    s.voice("trail", from_k=-4)
    return s


def filled(sim, **view):
    sim.start(**view)
    sim.play({1: N, 2: TOUCH})
    assert sim.sig()["follow"]["state"] == "FILLED"
    return sim


# ------------------------------------------------------------------ the switch is off: nothing new anywhere
def test_the_switch_is_off_in_the_code():
    assert setups_voice.TRAIL_MARKETS == () and signals.BOOK == setups_voice.BOOKS["targets"] == "b_targets"
    assert signals.trades_path("L", "BTCUSDT") == os.path.join("L", "shadow_trades_b_targets_BTCUSDT.csv")
    assert signals.trades_path("L", "BTCUSDT", "b_trail_setups") == os.path.join("L", "shadow_trades_b_trail_setups_BTCUSDT.csv")
    assert (signals.CARD_MOVE_R, signals.ARM_R) == (0.5, 1.0)


def test_switch_off_and_no_state_file_is_the_record_as_it_was(tmp_path):
    """No voice state, the switch off: the trail book on the page is not looked at, and the log lines, the state and the
    cards carry exactly what they did before the trail voice existed (no new key, the same words)."""
    sim = Sim(tmp_path)
    assert not os.path.exists(sim.voice_path) and setups_voice.TRAIL_MARKETS == ()
    sim.check(-30)
    sim.open_trail(k=0, trailing=True, stop=101.0)                   # the trail book has a setup too: never signalled
    sim.open_targets(k=0)
    sim.bars[0] = N
    sim.write_bars()
    assert sim.check(16)["new"] == 1 and len(sim.sent) == 1
    s = sim.sig()
    assert set(s) == STATE_KEYS and set(s["follow"]) == {"state", "last_bar_ms", "bars_after_a", "exits"}
    assert set(sim.last("signal")) == SIGNAL_KEYS and sim.last("signal")["t1"] == 103.0
    assert sim.sent[0][0] == "\n".join([
        u"\U0001f7e2 <b>BUY BTC</b> · signal <code>BTC-1117-01</code>", u"Limit order at <b>100.000</b>",
        u"Valid until <b>01:30 UTC</b> (the next four 15-minute bars)",
        u"<pre>Level         Price     %    R\n" + "-" * 30 + u"\nEntry       100.000\nStop          98.00  2.00  1.0\n"
        u"Target 1    103.000  3.00  1.5\nTarget 2    105.000  5.00  2.5</pre>",
        u"Why: market structure reads \"uptrend on every horizon\"; strongest on the buy side: Support and resistance.",
        u"Plan: take half at Target 1 and move the stop to the entry; the rest runs to Target 2. If the stop or Target 1 "
        u"trades before the entry fills, the signal is void.", signals.FOOT])
    sim.play({1: N, 2: TOUCH})
    sim.play({3: (101.0, 103.5, 100.5, 103.2)})
    sim.views[TRAIL_BOOK] = {"status": "FLAT", "trades": 1}          # whatever the trail book does changes nothing
    sim.play({4: (103.2, 105.2, 102.9, 105.0)})
    assert sim.evs() == ["signal", "filled", "t1", "closed"] and sim.last("closed")["why"] == "t2"
    assert sim.sent[1][0] == u"✅ <b>Entry filled</b> · <code>BTC-1117-01</code>\nBUY BTC at 100.000 (00:30 UTC bar).\n" \
                             u"Stop 98.00 · Target 1 103.000 · Target 2 105.000\n" + signals.FOOT
    keys = {"signal": SIGNAL_KEYS, "filled": {"t", "id", "k", "ev", "asset", "px", "bar_utc", "delivered"},
            "t1": {"t", "id", "k", "ev", "asset", "px", "bar_utc", "delivered"},
            "closed": {"t", "id", "k", "ev", "asset", "px", "bar_utc", "delivered", "why", "pct", "usd", "r", "avg_exit"}}
    for e in sim.events():
        assert set(e) == keys[e["ev"]], e
    assert set(sim.sig()) == STATE_KEYS and sim.sig()["stop"] == 98.0
    sb = signals.scoreboard(signals.read_log(sim.log))
    assert sb["sent"] == 1 and sb["follow"]["n"] == 1 and sb["trail"]["sent"] == 0 and sb["trail"]["follow"]["n"] == 0
    assert list(sb)[:-1] == ["live_since", "first_signal_utc", "days", "sent", "filled", "no_fill", "waiting", "in_trade",
                             "fill_rate_pct", "follow", "verdict", "book_same", "book_of_filled", "book_of_no_fill", "gate"]
    card = signals.record_card(sim.log, sim.st())
    assert "trailing" not in card and "two targets" not in card and card.count("Results are after fees") == 1
    assert not os.path.exists(sim.voice_path)                        # read only: the bot never writes the voice state


def test_a_voice_state_that_cannot_be_read_stops_the_check(tmp_path, on):
    sim = Sim(tmp_path)
    sim.voice("trail")
    sim.start()
    state, log, n = io.open(sim.state).read(), io.open(sim.log).read(), len(sim.sent)
    with io.open(sim.voice_path, "w") as fh:
        fh.write(u"{half")
    with pytest.raises(ValueError):
        sim.play({1: N, 2: TOUCH})
    assert io.open(sim.state).read() == state and io.open(sim.log).read() == log and len(sim.sent) == n
    sim.voice("trail")                                               # readable again: the same bars at the next check
    sim.check(46)
    assert sim.evs() == ["signal", "filled"]


def test_a_lost_voice_state_issues_nothing_new_and_still_follows_what_is_out(sim):
    """The file is gone while the market is on the trail voice: to the bot b_targets speaks again, which is not what the
    switch asks, so nothing new goes out (and `seen` is left alone); the trail signal out is followed in its own book."""
    filled(sim)
    sim.voice(None)
    sim.open_targets(k=3)                                            # b_targets, still running on paper, opens a setup
    sim.move(100.8)
    assert sim.play({3: UP})["new"] == 0
    assert sim.evs() == ["signal", "filled", "stop_moved"] and sim.st()["seen"] == {"BTCUSDT": utc(ts(0))}
    sim.voice("trail", from_k=-4)                                    # the engine has written it again
    assert sim.play({4: (102.3, 102.4, 100.7, 101.0)})["new"] == 0   # the same trail setup is not signalled twice
    assert sim.evs() == ["signal", "filled", "stop_moved", "closed"] and sim.last("closed")["why"] == "trail"


# ------------------------------------------------------------------ which setups become signals
def test_switch_on_but_no_state_yet_issues_nothing_new(tmp_path, on):
    """The bot read the page a moment before the engine wrote its state: b_targets still speaks, the switch asks for the
    trail book, so nothing new goes out in either book. Nothing is marked as seen either."""
    sim = Sim(tmp_path)
    sim.check(-30)
    sim.open_targets(k=0)
    sim.open_trail(k=0)
    sim.bars[0] = N
    sim.write_bars()
    assert sim.check(16)["new"] == 0 and sim.sent == [] and sim.st()["seen"] == {} and sim.evs() == []


def test_a_market_waiting_to_change_voice_issues_nothing_new(tmp_path, on):
    sim = Sim(tmp_path)
    sim.check(-30)
    sim.open_targets(k=0)
    sim.open_trail(k=0)
    sim.bars[0] = N
    sim.write_bars()
    sim.voice("targets", from_k=None, pending=True, wait=utc(ts(0)))   # the remembered setup is the one shown ...
    assert sim.check(16)["new"] == 0 and sim.sent == []                # ... and still it is not a NEW signal
    sim.voice("targets", from_k=None, pending=True, wait=utc(ts(-8)))  # another setup than the remembered one: not shown
    assert sim.check(17)["new"] == 0 and sim.sent == [] and sim.st()["seen"] == {}


def test_after_the_flip_only_a_trail_setup_opened_at_or_after_it_is_signalled(tmp_path, on):
    sim = Sim(tmp_path)
    sim.check(-30)
    sim.voice("trail", from_k=1)                                     # the voice flipped at the close 00:15
    sim.open_trail(k=0)                                              # opened before it: never shown, never signalled
    sim.open_targets(k=0)                                            # the old voice's book no longer speaks
    sim.bars[0] = N
    sim.write_bars()
    assert sim.check(16)["new"] == 0 and sim.sent == [] and sim.st()["seen"] == {}
    sim.open_trail(k=1)                                              # the trail book's next setup, at the flip's own close
    info = sim.play({1: N})
    assert info["new"] == 1 and sim.evs() == ["signal"] and sim.st()["seen"] == {"BTCUSDT": utc(ts(1))}
    s, e = sim.sig(), sim.last("signal")
    assert s["rule"] == "trail" and (s["entry"], s["stop"], s["stop0"], s["t1"], s["t2"]) == (100.0, 98.0, 98.0, None, None)
    assert e["rule"] == "trail" and e["t1"] is None and e["t2"] is None and e["stop"] == 98.0
    assert set(e) == SIGNAL_KEYS | {"rule"}


def test_first_run_on_the_trail_voice_does_not_signal_what_is_open(sim):
    sim.voice("trail", from_k=-50)
    sim.open_trail(k=-40)
    info = sim.check(-30)
    assert info["started"] and sim.sent == [] and sim.st()["seen"] == {"BTCUSDT": utc(ts(-40))}
    assert [e["ev"] for e in signals.read_log(sim.log)] == ["start", "seen_not_signalled"]
    sim.open_trail(k=0)                                              # the NEXT one is the first signal
    sim.bars[0] = N
    sim.write_bars()
    assert sim.check(16)["new"] == 1 and sim.sig()["rule"] == "trail"


def test_going_back_is_the_mirror(tmp_path):
    """The switch off again while the state still says trail: nothing new until the voice has flipped back, then the
    b_targets setup opened at or after that flip is a b_targets signal like any other."""
    sim = Sim(tmp_path)
    sim.check(-30)
    sim.voice("trail", from_k=-4, pending=True, wait=None)
    sim.open_targets(k=0)
    sim.open_trail(k=0)
    sim.bars[0] = N
    sim.write_bars()
    assert sim.check(16)["new"] == 0 and sim.sent == []
    sim.voice("targets", from_k=1)
    assert sim.check(17)["new"] == 0                                 # opened before the flip back: not shown
    sim.open_targets(k=1)
    assert sim.play({1: N})["new"] == 1 and "rule" not in sim.sig() and set(sim.last("signal")) == SIGNAL_KEYS


def test_a_targets_signal_is_followed_to_its_end_in_its_own_book_across_a_flip(tmp_path, monkeypatch):
    sim = Sim(tmp_path)                                              # the switch off, no state: a b_targets signal
    sim.check(-30)
    sim.open_targets(k=0)
    sim.bars[0] = N
    sim.write_bars()
    sim.check(16)
    sim.play({1: N, 2: TOUCH})
    assert sim.evs() == ["signal", "filled"] and "rule" not in sim.sig()
    monkeypatch.setattr(setups_voice, "TRAIL_MARKETS", ("BTCUSDT",))  # the switch goes on: the engine remembers the setup
    sim.voice("targets", from_k=None, pending=True, wait=utc(ts(0)))
    sim.open_trail(k=2)                                              # the trail book holds a setup of its own: not shown
    sim.play({3: (101.0, 103.5, 100.5, 103.2)})                      # Target 1, by the b_targets rules
    assert sim.evs() == ["signal", "filled", "t1"] and sim.st()["seen"] == {"BTCUSDT": utc(ts(0))}
    sim.book_closes(5, why="T1+FLIP", book=TARGETS_BOOK, p_out=102.0, pct=2.3, r=1.15)   # b_targets leaves at bar 5's open
    sim.voice("trail", from_k=5)                                     # ... and the voice flips at that step
    sim.open_trail(k=5)                                              # the trail book's next setup opens in it
    sim.play({4: N, 5: N})
    one, two = "BTC-1117-01", "BTC-1117-02"
    assert sim.evs(one) == ["signal", "filled", "t1", "book_closed", "model_exit"]
    assert sim.last("book_closed")["why_out"] == "T1+FLIP"           # read from b_targets' own trade file
    assert sim.evs(two) == ["signal"] and sim.last("signal")["rule"] == "trail"
    sim.play({6: N})                                                 # the alert's own bar
    sim.play({7: (101.2, 101.6, 99.9, 101.4)})                       # b_targets rule 4: the open after it; the trail one fills
    assert sim.evs(one)[-1] == "closed" and sim.evs(two) == ["signal", "filled"]
    c = [e for e in sim.events() if e["ev"] == "closed"][0]
    assert c["why"] == "model" and c["px"] == 101.2 and c["avg_exit"] == pytest.approx(102.1)   # half at 103, half at 101.2
    assert list(sim.st()["open"]) == [two]
    sb = signals.scoreboard(signals.read_log(sim.log))
    assert (sb["sent"], sb["filled"], sb["follow"]["n"], sb["book_same"]["n"]) == (1, 1, 1, 1)
    assert (sb["trail"]["sent"], sb["trail"]["filled"], sb["trail"]["in_trade"], sb["trail"]["follow"]["n"]) == (1, 1, 1, 0)


# ------------------------------------------------------------------ the trail signal and its card
def test_trail_signal_card_and_record_of_the_signal(sim):
    sim.start()
    s = sim.sig()
    assert s["id"] == "BTC-1117-01" and s["rule"] == "trail" and s["side"] == 1 and s["fee"] == 0.001
    assert s["f_ms"] == ts(0) and s["a_ms"] == ts(1) and s["valid_until_ms"] == ts(6) and s["follow"]["state"] == "WAITING"
    assert signals.arm_price(s) == 102.0 and signals.book_of(s) == "b_trail_setups"
    card, reply = sim.sent[0]
    assert reply is None and card == "\n".join([
        u"\U0001f7e2 <b>BUY BTC</b> · signal <code>BTC-1117-01</code>", u"Limit order at <b>100.000</b>",
        u"Valid until <b>01:30 UTC</b> (the next four 15-minute bars)",
        u"<pre>Level         Price     %    R\n" + "-" * 30 + u"\nEntry       100.000\nStop          98.00  2.00  1.0</pre>",
        u"Why: market structure reads \"uptrend on every horizon\"; strongest on the buy side: Support and resistance.",
        u"Plan: no fixed target. Once price reaches <b>102.000</b> (one risk unit in the trade's favour) the stop starts to "
        u"follow price, and the trade runs until the stop is hit. If the stop or that price trades before the entry fills, "
        u"the signal is void.", signals.FOOT])
    e = sim.last("signal")
    assert e["entry"] == 100.0 and e["bar_a_utc"] == "2026-11-17T00:15:00Z" and e["valid_until_utc"] == "2026-11-17T01:30:00Z"


@pytest.mark.parametrize("view,why", [
    (dict(stop=None), "the page gives no complete entry and stop"),
    (dict(stop=100.0), "the stop is not on its own side of the entry"),
    (dict(stop=100.5), "the stop is not on its own side of the entry")])
def test_a_trail_view_without_a_usable_stop_is_seen_but_not_signalled(sim, view, why):
    sim.check(-30)
    sim.open_trail(**view)
    sim.check(16)
    assert sim.sent == [] and sim.st()["seen"]["BTCUSDT"] == utc(ts(0))
    assert signals.read_log(sim.log)[-1]["ev"] == "seen_not_signalled" and signals.read_log(sim.log)[-1]["why"] == why


def test_a_trail_already_armed_when_first_seen_is_a_ran_no_fill_at_once(sim):
    sim.start(trailing=True, stop=100.6)                             # the stop shown has already moved past the entry
    assert sim.evs() == ["signal", "no_fill"] and sim.last("no_fill")["reason"] == "ran"
    assert "do not enter" in sim.sent[0][0] and "Stop        100.600</pre>" in sim.sent[0][0]
    assert "No fill: signal expired" in sim.sent[1][0] and sim.sent[1][1] == 501
    assert "price moved one risk unit in the trade's favour before the entry filled" in sim.sent[1][0]


# ------------------------------------------------------------------ trail rule 1: the entry
@pytest.mark.parametrize("n", [1, 2, 3, 4])
def test_fill_on_each_of_the_four_bars_after_bar_a(sim, n):
    sim.start()
    bars = dict((k, N) for k in range(1, 1 + n))
    bars[1 + n] = TOUCH
    sim.play(bars)
    f = sim.sig()["follow"]
    assert f["state"] == "FILLED" and f["fill_ms"] == ts(1 + n) and f["bars_after_a"] == n
    assert sim.evs() == ["signal", "filled"] and sim.last("filled")["px"] == 100.0
    assert sim.sent[-1] == (u"✅ <b>Entry filled</b> · <code>BTC-1117-01</code>\nBUY BTC at 100.000 (%s UTC bar).\n"
                            u"Stop 98.00 · no fixed target. The stop starts to follow price once price reaches 102.000.\n"
                            % signals._hm(ts(1 + n)) + signals.FOOT, 501)


def test_bar_a_touch_is_not_a_fill_and_the_window_passes(sim):
    sim.start()
    sim.play({1: TOUCH, 2: N, 3: N, 4: N})                           # bar A holds E: it never counts
    assert sim.sig()["follow"]["state"] == "WAITING" and sim.evs() == ["signal"]
    sim.play({5: N})
    assert sim.evs() == ["signal", "no_fill"] and sim.last("no_fill")["reason"] == "window"
    sim.play({6: TOUCH})                                             # a fifth bar is too late
    assert sim.evs() == ["signal", "no_fill"] and "the entry window passed" in sim.sent[-1][0]


# ------------------------------------------------------------------ trail rule 2: no fill
@pytest.mark.parametrize("bar,reason", [
    ((101.0, 101.5, 97.9, 99.0), "stop"),                            # the stop trades (and the bar holds E too)
    ((101.0, 102.0, 100.5, 101.8), "ran"),                           # price reaches E + 1R exactly
    ((100.5, 102.1, 99.5, 101.9), "ran"),                            # a bar that holds E and E + 1R together
    ((100.5, 101.0, 98.0, 99.0), "stop"),                            # a bar that holds E and S0 together
    ((100.5, 102.5, 97.5, 99.0), "stop")])                           # all three: the stop is looked at first
@pytest.mark.parametrize("k", [1, 3])                                # in bar A itself, or in a later bar before the fill
def test_stop_or_one_r_in_favour_before_the_fill_is_a_no_fill(sim, bar, reason, k):
    sim.start()
    bars = dict((j, N) for j in range(1, k))
    bars[k] = bar
    bars[k + 1] = TOUCH                                              # would have filled afterwards
    sim.play(bars)
    assert sim.evs() == ["signal", "no_fill"] and sim.last("no_fill")["reason"] == reason
    assert sim.sig()["follow"]["state"] == "NO_FILL"
    assert signals.scoreboard(signals.read_log(sim.log))["trail"]["follow"]["n"] == 0     # a signal sent, not a trade
    if reason == "ran":
        assert sim.sent[-1][0] == u"⚪ <b>No fill: signal expired</b> · <code>BTC-1117-01</code>\nBUY BTC: price moved one " \
                                  u"risk unit in the trade's favour before the entry filled. No trade, no result. Cancel " \
                                  u"the order.\n" + signals.FOOT


def test_one_tick_short_of_one_r_is_not_ran(sim):
    sim.start()
    sim.play({1: N, 2: (101.0, 101.99, 100.5, 101.5), 3: TOUCH})
    assert sim.evs() == ["signal", "filled"]


def test_the_book_saying_its_trail_armed_while_the_signal_waits_is_ran(sim):
    """The book arms on its own unrounded prices: when its view says so and every bar has been looked at, the signal
    is void even if the page's rounded levels did not quite show it (the vault's line for a join)."""
    sim.start()
    sim.move(100.4)
    sim.play({1: N, 2: (101.0, 101.99, 100.5, 101.5)})
    assert sim.evs() == ["signal", "no_fill"] and sim.last("no_fill")["reason"] == "ran"
    assert "bar_utc" not in sim.last("no_fill")


def test_the_book_view_is_not_asked_while_a_bar_is_still_to_come(sim):
    sim.start()
    sim.move(100.4)
    sim.bars.update({1: N})
    sim.write_bars()
    sim.check(46, upto=2)                                            # the page has reached bar 2, the bar file has not
    assert sim.evs() == ["signal"] and sim.sig()["follow"]["last_bar_ms"] == ts(1)
    sim.play({2: TOUCH})                                             # bar 2 arrives: the bars decide, and it fills
    assert sim.evs() == ["signal", "filled", "stop_moved"] and sim.sig()["stop"] == 100.4   # then the book's stop is taken


@pytest.mark.parametrize("why,reason", [("TRAIL", "ran"), ("STOP", "stop"), ("FLIP", "model")])
def test_the_book_closes_before_the_fill(sim, why, reason):
    sim.start()
    sim.play({1: N, 2: N})
    sim.book_closes(3, why=why)                                      # the book left at the open of bar 3 ...
    sim.play({3: TOUCH})                                             # ... so bar 3 cannot fill
    assert sim.evs() == ["signal", "book_closed", "no_fill"] and sim.last("no_fill")["reason"] == reason
    assert sim.st()["open"] == {}
    sb = signals.scoreboard(signals.read_log(sim.log))
    assert sb["sent"] == 0 and sb["book_of_no_fill"]["n"] == 0       # nothing of it in H53's record
    assert (sb["trail"]["sent"], sb["trail"]["no_fill"], sb["trail"]["book_of_no_fill"]["n"]) == (1, 1, 1)


def test_a_closed_trail_trade_is_read_from_the_trail_books_own_file(sim):
    sim.start()
    sim.play({1: N, 2: TOUCH})
    sim.book_closes(4, why="FLIP", book=TARGETS_BOOK)                # a b_targets row with the same opening time: not it
    sim.views[TRAIL_BOOK] = {"status": "FLAT", "trades": 1}
    sim.play({3: N, 4: N})
    assert sim.evs() == ["signal", "filled"] and sim.sig()["book"]["closed"] is False     # waits for its own file
    sim.book_closes(4, why="FLIP", pct=0.5, r=0.25)
    sim.check(77)
    assert sim.last("book_closed")["pct"] == 0.5 and sim.last("book_closed")["why_out"] == "FLIP"


# ------------------------------------------------------------------ trail rule 3: after the fill
def test_the_first_stop_never_moved_is_a_stop(sim):
    filled(sim)
    sim.play({3: (101.0, 103.5, 97.9, 99.0)})                        # 1R in favour and the stop in one bar: the stop
    c = sim.last("closed")
    assert sim.evs() == ["signal", "filled", "closed"] and c["why"] == "stop" and c["px"] == 98.0
    assert c["pct"] == pytest.approx(-2.0 - 0.1 * 1.98) and c["r"] == pytest.approx(-2.198 / 2.0)
    assert sim.sent[-1][0] == u"\U0001f534 <b>Stopped</b> · <code>BTC-1117-01</code>\nBUY BTC: stopped at 98.00 (00:45 UTC bar)." \
                              u"\nResult <b>-2.20%</b> · <b>-1.10R</b> after fees\n" + signals.FOOT


def test_a_gap_through_the_first_stop_fills_at_the_open(sim):
    filled(sim)
    sim.play({3: (97.0, 97.5, 96.0, 96.5)})
    c = sim.last("closed")
    assert c["why"] == "stop" and c["px"] == 97.0 and c["pct"] == pytest.approx(-3.0 - 0.1 * 1.97)


def test_no_targets_the_trade_runs_until_the_trailing_stop(sim):
    filled(sim)
    sim.play({3: (101.0, 103.5, 100.5, 103.2), 4: (103.2, 105.2, 102.9, 105.0)})    # b_targets' Target 1 and 2: nothing here
    assert sim.evs() == ["signal", "filled"] and sim.sig()["follow"]["state"] == "FILLED"
    sim.move(103.0)                                                  # published at the close of bar 5 ...
    sim.play({5: (105.0, 106.0, 104.5, 105.5)})
    assert sim.sig()["stop"] == 103.0 and sim.sig()["stop0"] == 98.0
    sim.play({6: (105.5, 105.8, 102.9, 103.1)})                      # ... and met by bar 6
    c = sim.last("closed")
    assert sim.evs() == ["signal", "filled", "stop_moved", "closed"] and c["why"] == "trail" and c["px"] == 103.0
    assert c["bar_utc"] == "2026-11-17T01:30:00Z" and c["avg_exit"] == 103.0
    assert c["pct"] == pytest.approx(3.0 - 0.1 * 2.03) and c["usd"] == pytest.approx(279.7)
    assert c["r"] == pytest.approx(2.797 / 2.0)                      # R on S0 (98), not on the stop that moved
    assert sim.sent[-1] == (u"\U0001f7e2 <b>Trailing stop hit: closed</b> · <code>BTC-1117-01</code>\nBUY BTC: closed at "
                            u"103.000 (01:30 UTC bar).\nResult <b>+2.80%</b> · <b>+1.40R</b> after fees\n" + signals.FOOT, 501)


def test_a_gap_through_the_trailing_stop_fills_at_the_open(sim):
    filled(sim)
    sim.move(101.0)
    sim.play({3: UP})
    sim.play({4: (100.2, 100.6, 99.8, 100.1)})                       # opens below the stop
    c = sim.last("closed")
    assert c["why"] == "trail" and c["px"] == 100.2 and c["pct"] == pytest.approx(0.2 - 0.1 * 2.002)


def test_each_bar_meets_the_stop_published_at_the_close_before_it(sim):
    filled(sim)
    sim.move(100.6)                                                  # set at the close of bar 3, which itself dips to 100.5
    sim.play({3: (101.0, 102.5, 100.5, 102.3)})
    assert sim.evs() == ["signal", "filled", "stop_moved"] and sim.sig()["stop"] == 100.6     # bar 3 met the old stop
    sim.play({4: (102.3, 102.4, 100.55, 101.0)})
    assert sim.last("closed")["why"] == "trail" and sim.last("closed")["px"] == 100.6


def test_the_stop_only_ever_tightens(sim):
    filled(sim)
    sim.move(101.0)
    sim.play({3: UP})
    for k, looser in ((4, 100.2), (5, 98.0), (6, None), (7, "x"), (8, -5.0)):
        sim.move(looser)
        sim.play({k: (102.0, 102.4, 101.5, 102.0)})
        assert sim.sig()["stop"] == 101.0 and sim.sig()["follow"]["state"] == "FILLED"
    assert sim.evs() == ["signal", "filled", "stop_moved"]


def test_several_bars_in_one_check_use_the_older_stop_then_rule_4_ends_the_trade(sim):
    """The bot was away: the book trailed and was stopped at 101.0 in bar 4, the bars 3..5 arrive in one check. They all
    meet the stop the signal had (98), so the followable trade is still open; the book has closed: H53 rule 4."""
    filled(sim)
    sim.book_closes(4, why="TRAIL", p_out=101.0, pct=0.8, r=0.4)
    sim.play({3: UP, 4: (102.0, 102.2, 100.9, 101.2), 5: (101.2, 101.5, 100.8, 101.0)})
    f = sim.sig()["follow"]
    assert sim.evs() == ["signal", "filled", "book_closed", "model_exit"] and f["exit_alert_ms"] == ts(6)
    assert sim.sig()["stop"] == 98.0 and f["state"] == "FILLED" and "exit now" in sim.sent[-1][0]
    sim.play({6: N})
    sim.play({7: (101.3, 101.6, 100.9, 101.4)})
    c = sim.last("closed")
    assert c["why"] == "model" and c["px"] == 101.3 and "Closed by the model" in sim.sent[-1][0]
    assert sim.st()["open"] == {}


def test_a_stop_is_not_taken_while_a_bar_before_the_page_close_is_still_to_come(sim):
    filled(sim)
    sim.move(100.6)
    sim.check(61, upto=3)                                            # the page is at the close of bar 3, the bar file is not
    assert sim.sig()["stop"] == 98.0 and sim.evs() == ["signal", "filled"]
    sim.play({3: (101.0, 102.5, 100.5, 102.3)})                      # bar 3 meets 98, then the stop is taken
    assert sim.sig()["stop"] == 100.6 and sim.sig()["follow"]["state"] == "FILLED"


# ------------------------------------------------------------------ trail rule 4: the book closes its own trade
def test_book_exit_closes_at_the_open_of_the_bar_after_the_exit_alert(sim):
    filled(sim)
    sim.move(100.5)
    sim.play({3: UP})
    sim.book_closes(4, why="FLIP", p_out=102.3, pct=2.1, r=1.05)     # the book left at the open of bar 4
    sim.play({4: (102.3, 102.6, 101.8, 102.0)})                      # seen in bar 5: the exit alert goes now
    assert sim.evs() == ["signal", "filled", "stop_moved", "book_closed", "model_exit"]
    assert sim.sig()["follow"]["exit_alert_ms"] == ts(5) and sim.sig()["stop"] == 100.5
    sim.play({5: (102.0, 102.2, 101.0, 101.5)})                      # the alert's own bar: still open, the stop live
    assert sim.sig()["follow"]["state"] == "FILLED"
    sim.play({6: (101.6, 101.9, 101.2, 101.4)})
    c = sim.last("closed")
    assert c["why"] == "model" and c["px"] == 101.6 and c["bar_utc"] == "2026-11-17T01:30:00Z"
    assert c["pct"] == pytest.approx(1.6 - 0.1 * 2.016) and sim.st()["open"] == {}
    sb = signals.scoreboard(signals.read_log(sim.log))["trail"]
    assert sb["follow"]["n"] == 1 and sb["book_same"]["net_pct"] == 2.1 and sb["book_of_filled"]["net_r"] == 1.05


def test_the_trailing_stop_stays_live_in_the_exit_alert_bar(sim):
    filled(sim)
    sim.move(100.5)
    sim.play({3: UP})
    sim.book_closes(4, why="FLIP")
    sim.play({4: (102.3, 102.6, 101.8, 102.0)})
    sim.play({5: (102.0, 102.2, 100.4, 100.6), 6: N})
    assert sim.last("closed")["why"] == "trail" and sim.last("closed")["bar_utc"] == "2026-11-17T01:15:00Z"


def test_book_and_followable_stopped_in_the_same_bar_need_no_exit_alert(sim):
    filled(sim)
    sim.move(101.0)
    sim.play({3: UP})
    sim.book_closes(4, why="TRAIL", p_out=101.0, pct=0.8, r=0.4)
    sim.play({4: (102.0, 102.2, 100.9, 101.2)})
    assert sim.evs() == ["signal", "filled", "stop_moved", "book_closed", "closed"] and sim.last("closed")["why"] == "trail"


# ------------------------------------------------------------------ the "stop moved" cards
def stops(sim):
    return [(e["kind"], e["px"], e["bar_utc"][11:16]) for e in sim.events() if e["ev"] == "stop_moved"]


def test_stop_cards_armed_then_past_entry_then_every_half_r(sim):
    filled(sim)
    quiet = (102.0, 102.4, 101.8, 102.0)
    sim.move(99.0)                                                   # off S0, still on the loss side of the entry
    sim.play({3: UP})
    assert stops(sim) == [("armed", 99.0, "00:45")]
    assert sim.sent[-1] == (
        u"\U0001f6e1\ufe0f <b>Stop moved: it now follows price</b> · <code>BTC-1117-01</code>\nBUY BTC: the stop is now "
        u"<b>99.00</b> (after the 00:45 UTC bar).\nPrice has moved one risk unit in the trade's favour: from here the stop "
        u"follows price and is never moved back.\nStopped there: <b>-1.20%</b> · <b>-0.60R</b> after fees.\n" + signals.FOOT, 501)
    sim.move(99.9)                                                   # 0.45R on, not past the entry: no card
    sim.play({4: quiet})
    assert len(stops(sim)) == 1 and sim.sig()["stop"] == 99.9 and sim.sig()["follow"]["stop_card"] == 99.0
    sim.move(100.4)                                                  # the first time past the entry, however small the move
    sim.play({5: quiet})
    assert stops(sim)[-1] == ("past_entry", 100.4, "01:15")
    assert sim.sent[-1][0] == (
        u"\U0001f6e1\ufe0f <b>Stop moved past the entry</b> · <code>BTC-1117-01</code>\nBUY BTC: the stop is now <b>100.400</b> "
        u"(after the 01:15 UTC bar).\nThe stop follows price and is now past the entry.\n"
        u"Stopped there: <b>+0.20%</b> · <b>+0.10R</b> after fees.\n" + signals.FOOT)
    n = len(sim.sent)
    for k, px in ((6, 100.7), (7, 101.1), (8, 101.39)):              # 0.15R, 0.35R, 0.495R since the last card: no card
        sim.move(px)
        sim.play({k: quiet})
    assert len(sim.sent) == n and len(stops(sim)) == 2 and sim.sig()["stop"] == 101.39
    sim.move(101.4)                                                  # half an R since the last card (100.4)
    sim.play({9: quiet})
    assert stops(sim)[-1] == ("step", 101.4, "02:15")
    assert sim.sent[-1][0] == (
        u"\U0001f6e1\ufe0f <b>Stop moved</b> · <code>BTC-1117-01</code>\nBUY BTC: the stop is now <b>101.400</b> (after the "
        u"02:15 UTC bar).\nStopped there: <b>+1.20%</b> · <b>+0.60R</b> after fees.\n" + signals.FOOT)
    sim.move(101.9)                                                  # measured from the last CARD, not from the last move
    sim.play({10: (102.5, 102.9, 102.2, 102.6)})
    assert len(stops(sim)) == 3
    sim.move(102.4)
    sim.play({11: (102.8, 103.2, 102.6, 103.0)})
    assert [s[0] for s in stops(sim)] == ["armed", "past_entry", "step", "step"]
    assert sim.evs() == ["signal", "filled", "stop_moved", "stop_moved", "stop_moved", "stop_moved"]   # each kept by read_log
    e = sim.last("stop_moved")
    assert set(e) == {"t", "id", "k", "ev", "asset", "kind", "px", "bar_utc", "delivered"} and e["delivered"] is True


def test_a_first_move_already_past_the_entry_is_one_card(sim):
    filled(sim)
    sim.move(100.8)
    sim.play({3: UP})
    assert stops(sim) == [("past_entry", 100.8, "00:45")] and len(sim.sent) == 3
    f = sim.sig()["follow"]
    assert f["past_entry"] is True and f["stop_card"] == 100.8
    sim.move(101.0)                                                  # no "armed" card afterwards, and 0.1R is no step
    sim.play({4: (102.0, 102.4, 101.8, 102.0)})
    assert len(stops(sim)) == 1


def test_stop_cards_are_sent_once(sim):
    filled(sim)
    sim.move(100.8)
    sim.play({3: UP})
    state, log, n = io.open(sim.state).read(), io.open(sim.log).read(), len(sim.sent)
    for _ in range(3):
        sim.check(61)
    assert io.open(sim.state).read() == state and io.open(sim.log).read() == log and len(sim.sent) == n


def test_short_side_mirrors(tmp_path, on):
    sim = Sim(tmp_path, side=-1, E=100.0, S=102.0)
    sim.voice("trail")
    sim.start()
    assert "SELL BTC" in sim.sent[0][0] and "Once price reaches <b>98.00</b>" in sim.sent[0][0]
    sim.play({1: (99.0, 99.5, 98.5, 99.0), 2: (99.5, 100.5, 99.0, 99.8)})          # bar 2 holds E
    assert sim.evs() == ["signal", "filled"]
    sim.move(101.0)
    sim.play({3: (99.0, 99.4, 97.8, 98.0)})
    sim.move(99.5)
    sim.play({4: (98.0, 98.4, 97.5, 97.9)})
    sim.move(99.9)                                                   # looser for a short: not taken
    sim.play({5: (97.9, 98.2, 97.4, 97.6)})
    assert stops(sim) == [("armed", 101.0, "00:45"), ("past_entry", 99.5, "01:00")] and sim.sig()["stop"] == 99.5
    sim.play({6: (99.8, 100.0, 99.0, 99.2)})                         # opens above the stop: the open
    c = sim.last("closed")
    assert c["why"] == "trail" and c["px"] == 99.8 and c["pct"] == pytest.approx(0.2 - 0.1 * 1.998)
    assert c["r"] == pytest.approx((0.2 - 0.1998) / 2.0)


def test_a_short_that_runs_before_the_fill(tmp_path, on):
    sim = Sim(tmp_path, side=-1, E=100.0, S=102.0)
    sim.voice("trail")
    sim.start()
    sim.play({1: (99.0, 99.5, 98.5, 99.0), 2: (99.0, 100.2, 97.9, 98.2)})          # holds E and E - 1R
    assert sim.last("no_fill")["reason"] == "ran"


# ------------------------------------------------------------------ the record and the cards
def story(tmp_path, monkeypatch):
    """One market, one log: a b_targets winner (T1 + T2) before the switch; then on the trail voice a trade closed by its
    trailing stop, a no fill that ran, and one in its trade with a trailing stop."""
    sim = Sim(tmp_path)
    sim.check(-30)
    sim.open_targets(k=0)
    sim.bars[0] = N
    sim.write_bars()
    sim.check(16)
    sim.play({1: N, 2: TOUCH})
    sim.play({3: (101.0, 103.5, 100.5, 103.2), 4: (103.2, 105.2, 102.9, 105.0)})
    sim.book_closes(4, why="T1+T2", book=TARGETS_BOOK, p_out=104.0, pct=3.796, r=1.898)
    monkeypatch.setattr(setups_voice, "TRAIL_MARKETS", ("BTCUSDT",))
    sim.voice("trail", from_k=5)
    sim.play({5: N})
    sim.open_trail(k=6)                                              # the second signal, a trail one: alert in bar 7
    sim.play({6: N})
    sim.play({7: N, 8: TOUCH})
    sim.move(101.0)
    sim.play({9: UP})
    sim.book_closes(10, why="TRAIL", p_out=101.0, pct=0.8, r=0.4, k_in=6)
    sim.play({10: (102.0, 102.2, 100.9, 101.2)})
    sim.open_trail(k=11)                                             # the third: price runs before the fill
    sim.play({11: N})
    sim.play({12: (101.0, 102.2, 100.6, 102.0)})
    sim.book_closes(13, why="FLIP", p_out=102.0, pct=1.8, r=0.9, k_in=11)
    sim.play({13: N})
    sim.open_trail(k=14)                                             # the fourth: filled, its stop trailing
    sim.play({14: N})
    sim.play({15: N, 16: TOUCH})
    sim.move(100.8)
    sim.play({17: UP})
    return sim


def test_the_two_records_are_never_pooled(tmp_path, monkeypatch):
    sim = story(tmp_path, monkeypatch)
    sb = signals.scoreboard(signals.read_log(sim.log))
    assert (sb["sent"], sb["filled"], sb["no_fill"], sb["waiting"], sb["in_trade"]) == (1, 1, 0, 0, 0)
    f = sb["follow"]
    assert f["n"] == 1 and f["net_usd"] == 379.6 and f["net_r"] == 1.898 and sb["book_same"]["net_pct"] == 3.796
    assert sb["gate"]["signals"] == 1 and sb["first_signal_utc"] == "2026-11-17T00:16:00Z"
    assert sb["days"] == 0.1                                         # H53's clock stops at its own last line (01:31)
    t = sb["trail"]
    assert (t["sent"], t["filled"], t["no_fill"], t["waiting"], t["in_trade"], t["fill_rate_pct"]) == (3, 2, 1, 0, 1, 66.7)
    assert t["follow"]["n"] == 1 and t["follow"]["net_pct"] == pytest.approx(1.0 - 0.1 * 2.01) and t["follow"]["won_pct"] == 100.0
    assert t["book_same"]["n"] == 2 and t["book_same"]["net_pct"] == pytest.approx(2.6) and t["book_of_no_fill"]["net_pct"] == 1.8
    assert t["first_signal_utc"] == "2026-11-17T01:46:00Z" and t["verdict"] == "too few trades to judge (1 of 30)"
    assert "gate" not in t and "live_since" not in t and "trail" not in t


def test_scoreboard_with_trail_signals_only_and_with_none():
    rows = [{"t": "2026-11-17T00:00:00Z", "k": "start", "ev": "start", "live_since": "2026-11-17T00:00:00Z"}]
    sb = signals.scoreboard(rows)
    assert sb["sent"] == 0 and sb["trail"]["sent"] == 0 and sb["trail"]["fill_rate_pct"] is None
    assert sb["trail"]["follow"]["n"] == 0 and sb["trail"]["days"] is None and sb["gate"]["met"] is False
    rows += [{"t": "2026-11-18T00:00:00Z", "id": "B-1", "k": "BTCUSDT|a", "ev": "signal", "side": 1, "rule": "trail"},
             {"t": "2026-11-18T01:00:00Z", "id": "B-1", "k": "BTCUSDT|a", "ev": "filled"},
             {"t": "2026-11-19T00:00:00Z", "id": "B-1", "k": "BTCUSDT|a", "ev": "closed", "why": "trail", "pct": 1.5, "r": 0.75}]
    sb = signals.scoreboard(rows)
    assert sb["sent"] == 0 and sb["follow"]["n"] == 0 and sb["first_signal_utc"] is None and sb["days"] is None
    assert sb["trail"]["sent"] == 1 and sb["trail"]["follow"]["net_r"] == 0.75 and sb["trail"]["days"] == 1.0


def test_record_recap_and_open_cards_with_both_kinds(tmp_path, monkeypatch):
    sim = story(tmp_path, monkeypatch)
    card = signals.record_card(sim.log, sim.st())
    two, three = card.index("<b>Signals with two targets</b>"), card.index("<b>Signals with a trailing stop</b>")
    assert two < three and "Signals sent                 1" in card[two:three] and "Signals sent                 3" in card[three:]
    assert "Net          +1.90R     +3.80%" in card[two:three] and "Net          +0.40R     +0.80%" in card[three:]
    assert "In a trade now               1" in card[three:] and card.count("Results are after fees") == 1
    assert "The same signals at the model's own entry price: 2 closed, net +2.60% (+1.30R)." in card[three:]
    recap = signals.recap_card(sim.log, at(24 * 60), sim.st())
    assert "BTC-1117-01 BUY         +1.90R" in recap and "BTC-1117-02 BUY         +0.40R" in recap
    assert "BTC-1117-03 BUY        no fill" in recap and "BTC-1117-04 BUY       in trade" in recap
    assert "<b>Signals with a trailing stop</b>" in recap
    opened = signals.open_card(sim.st())
    assert "BTC-1117-04 BUY       in trade\n stop 100.800, trailing" in opened and "next" not in opened


def test_open_card_of_a_trail_signal_before_and_after_its_stop_moves(sim):
    sim.start()
    assert "BTC-1117-01 BUY        waiting\n limit 100.000 to 01:30" in signals.open_card(sim.st())
    sim.play({1: N, 2: TOUCH})
    assert "BTC-1117-01 BUY       in trade\n stop 98.00\n trails from 102.000</pre>" in signals.open_card(sim.st())
    sim.move(100.5)
    sim.play({3: UP})
    sim.book_closes(4, why="FLIP")
    sim.play({4: (102.3, 102.6, 101.8, 102.0)})
    assert " stop 100.500, trailing\n model closed: exit now</pre>" in signals.open_card(sim.st())


def test_nothing_of_a_trail_signal_names_a_target_the_book_the_research_or_a_dollar_size(tmp_path, monkeypatch, on):
    texts = []
    a = Sim(tmp_path / "a")                                          # filled, armed, past the entry, a step, the trailing stop
    a.voice("trail")
    filled(a)
    for k, px, bar in ((3, 99.0, UP), (4, 100.2, (102.0, 102.4, 101.8, 102.0)), (5, 101.3, (102.0, 102.9, 101.8, 102.6))):
        a.move(px)
        a.play({k: bar})
    texts += [signals.open_card(a.st())]
    a.play({6: (102.6, 102.8, 101.2, 101.4)})
    b = Sim(tmp_path / "b")                                          # the first stop; then one that ran before the fill
    b.voice("trail")
    filled(b)
    texts += [signals.open_card(b.st())]
    b.play({3: (101.0, 101.2, 97.5, 98.2)})
    c = Sim(tmp_path / "c")                                          # the model's exit; one armed at first sight; a window
    c.voice("trail")
    filled(c)
    c.book_closes(4, why="FLIP")
    c.play({3: N, 4: N})
    c.play({5: N, 6: N})
    c.open_trail(k=7, trailing=True, stop=100.4)
    c.play({7: N})
    c.open_trail(k=9)
    c.play({8: N, 9: N})
    texts += [signals.open_card(c.st())]
    c.play({10: (101.0, 102.3, 100.6, 102.0)})
    c.open_trail(k=12)
    c.play({11: N, 12: N})
    c.play({13: N, 14: N, 15: N, 16: N, 17: N})
    for s in (a, b, c):
        texts += s.texts() + [signals.record_card(s.log, s.st()), signals.recap_card(s.log, at(24 * 60), s.st())]
    kinds = ("signal <code>", "Entry filled", "No fill: signal expired", "it now follows price", "Stop moved past the entry",
             "<b>Stop moved</b>", "Trailing stop hit: closed", "<b>Stopped</b>", "exit now", "Closed by the model",
             "do not enter", "the entry window passed", "moved one risk unit in the trade's favour before the entry filled",
             "Signals with a trailing stop", "trails from", ", trailing")
    assert all(any(k in t for t in texts) for k in kinds), [k for k in kinds if not any(k in t for t in texts)]
    for t in texts:
        low = t.lower()
        assert "Target" not in t and "target 1" not in low and "target 2" not in low and "targets" not in low
        assert "T1" not in t and "T2" not in t and "None" not in t and "\n next " not in t
        assert "b_trail" not in low and "b_targets" not in low and "shadow" not in low and "kronos" not in low
        assert "forecast" not in low and "$" not in t and "10,000" not in t and "10000" not in t and u"—" not in t
        assert t.endswith("Paper signal from a model, not financial advice.</i>")
        for block in t.split("<pre>")[1:]:
            assert all(len(ln) <= 30 for ln in block.split("</pre>")[0].split("\n")), block   # a phone screen


def test_read_log_keeps_every_stop_move_and_counts_a_line_written_twice_once(sim):
    filled(sim)
    sim.move(99.0)
    sim.play({3: UP})
    sim.move(100.2)
    sim.play({4: (102.0, 102.4, 101.8, 102.0)})
    with io.open(sim.log, encoding="utf-8") as fh:
        lines = fh.read()
    with io.open(sim.log, "a", encoding="utf-8") as fh:
        fh.write(lines)
    assert sim.evs() == ["signal", "filled", "stop_moved", "stop_moved"]


# ------------------------------------------------------------------ the early signals (S2): nothing for a trail market
def test_the_early_signals_issue_nothing_for_a_market_on_or_going_to_the_trail_voice(tmp_path, monkeypatch):
    sim = Sim(tmp_path)
    sim.bars = {-2: (99.0, 100.5, 98.8, 99.5), -1: (99.5, 100.4, 99.4, 100.0)}
    sim.write_bars()
    state, log = os.path.join(sim.data, "signals_early_state.json"), os.path.join(sim.data, "signals_early_log.jsonl")

    def check(minute):
        return signals_early.run(sim.page(minute // 15 - 1), at(minute), sim.send, sim.data, sim.live, state, log,
                                 voice_path=sim.voice_path)
    check(-10)                                                       # the preview starts, nothing pending
    sim.views[TARGETS_BOOK] = {"status": "FLAT", "trades": 0, "next_open": "ENTER -> LONG"}
    page = sim.page(-1)
    flipped = {"markets": {"BTCUSDT": {"rule": "trail", "from_utc": iso(-4), "pending": False, "wait": None}}}
    assert signals_early.on_trail(page, "BTCUSDT", {}) is False and signals_early.on_trail(page, "BTCUSDT", flipped) is True
    monkeypatch.setattr(setups_voice, "TRAIL_MARKETS", ("BTCUSDT",))  # the switch on, the engine's state not yet flipped
    assert signals_early.on_trail(page, "BTCUSDT", {}) is True and signals_early.on_trail(page, "ETHUSDT", {}) is False
    assert check(2)["new"] == 0 and sim.sent == []
    monkeypatch.setattr(setups_voice, "TRAIL_MARKETS", ())           # the switch taken back, the voice still on trail
    sim.voice("trail", pending=True)
    assert check(3)["new"] == 0 and sim.sent == []
    sim.voice(None)                                                  # no state, the switch off: S2 as it always was
    assert check(4)["new"] == 1 and "early signal" in sim.sent[0][0] and "Target 1" in sim.sent[0][0]


# ------------------------------------------------------------------ the bot: the moving-against alert and the names
def adverse_page(price, targets, trail):
    return {"generated_utc": "2026-11-22T10:46:00Z",
            "shadows": {"books": {"b_targets": {"assets": {"ETHUSDT": targets}}, "b_trail_setups": {"assets": {"ETHUSDT": trail}}},
                        "markets": {"crypto": {"as_of_utc": "2026-11-22 10:45", "assets": {"ETHUSDT": {"price": price}}}}}}


def test_the_moving_against_alert_reads_the_book_the_page_shows():
    targets = {"status": "SHORT", "entry": 3000.0, "stop": 3100.0, "opened_utc": "2026-11-22 08:00", "target_1": 2900.0,
               "target_2": 2800.0, "t1_taken": False}
    trail = {"status": "LONG", "entry": 3100.0, "stop": 3000.0, "opened_utc": "2026-11-22 09:00"}
    page = adverse_page(3050.0, targets, trail)                      # half way to the stop of either book's trade
    for voice in (None, {}, {"markets": {}}, {"markets": {"BTCUSDT": {"rule": "trail", "from_utc": "2026-11-22T08:30:00Z"}}}):
        st, cards = tn.adverse_update(None, page, voice)             # no entry for this market: b_targets, as before
        assert len(cards) == 1 and "ETH short" in cards[0] and st["ETHUSDT"]["id"] == "2026-11-22 08:00|SHORT"
    assert tn.adverse_update(None, page) == tn.adverse_update(None, page, None)
    on_trail = {"markets": {"ETHUSDT": {"rule": "trail", "from_utc": "2026-11-22T08:30:00Z", "pending": False, "wait": None}}}
    st, cards = tn.adverse_update(None, page, on_trail)
    assert len(cards) == 1 and "ETH long" in cards[0] and "entry 3,100.00" in cards[0] and "Stop 3,000.00" in cards[0]
    assert st["ETHUSDT"]["id"] == "2026-11-22 09:00|LONG"
    st2, cards = tn.adverse_update(st, adverse_page(3020.0, targets, dict(trail, stop=3015.0, trailing=True)), on_trail)
    assert cards == [] and st2["ETHUSDT"]["t1"] is True              # its trailing stop has armed: no card any more
    late = {"markets": {"ETHUSDT": {"rule": "trail", "from_utc": "2026-11-22T09:15:00Z", "pending": False, "wait": None}}}
    st3, cards = tn.adverse_update(st, page, late)                   # opened before the voice began: the page shows FLAT
    assert cards == [] and "ETHUSDT" not in st3
    gone = adverse_page(3050.0, targets, trail)
    del gone["shadows"]["books"]["b_trail_setups"]
    st4, cards = tn.adverse_update(st, gone, on_trail)               # the page does not carry that book: nothing changes
    assert cards == [] and st4["ETHUSDT"] == st["ETHUSDT"]


def test_the_trail_book_has_a_name_in_the_bot():
    assert tn._name("b_trail_setups|ETHUSDT") == "Setups trail (shadow)" and tn._tname("b_trail_setups") == "Setups trail"
