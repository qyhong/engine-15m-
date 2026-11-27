# -*- coding: utf-8 -*-
"""THE MONEY PATH ON THE TRAIL VOICE, FROZEN (docs/TRAIL_SWITCH_PLAN.md). No network, no vault.

The twin of tests/test_money_path_golden.py for a market whose voice is the trailing-stop book `b_trail_setups`
(setups_voice.py). The same fixed bars (tests/fixtures/money_path_bars.json, BTCUSDT) go through

    shadows.run under the b_trail_setups rule    the book: the early entry, the first stop, the trail after 1R
    shadows.asset_view -> setups.build(voice=)   the market entry of setups.json on the trail voice
    vault_feed.track / build_book                the trail book body and the move_stop / close intents

one bar at a time, and every closed trade, every book body and every intent is compared with the record in
tests/fixtures/money_path_trail_golden.json. While the switches are off (setups_voice.TRAIL_MARKETS, vault_feed.SEND_TRAIL)
nothing of this reaches the vault; the record is kept so that the day they go on, what the vault is told is exactly what
was reviewed. After that day a failure here is what a failure of the first golden test is: the owner's word and a
version bump, then

    py -3 tests/test_money_path_trail_golden.py --write-golden

The trail reads two inputs the first fixture does not hold: the 15-minute ATR and the confirmed 15-minute swings. They
are made here from the fixture's own bars (a 14-bar mean of the true range; structure.swings, as shadows.aux_from_ev
does when no structure card is there), so the record freezes the chain, not an indicator.
"""
import json
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import test_money_path_golden as g  # noqa: E402
from engine15 import live, setups, setups_voice, shadows  # noqa: E402
from engine15.sources import structure  # noqa: E402
from engine15 import vault_feed as vf  # noqa: E402
from engine15.config import CFG  # noqa: E402

GOLDEN = os.path.join(g.HERE, "fixtures", "money_path_trail_golden.json")
BOOK = setups_voice.book_of(setups_voice.TRAIL)
SYM, BAR_MS = g.SYM, g.BAR_MS
ATR_N = 14


def aux_of(fx):
    h, l, c = fx["px"]["high"], fx["px"]["low"], fx["px"]["close"]
    prev = np.concatenate(([c[0]], c[:-1]))
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev), np.abs(l - prev)))
    atr = np.full(len(c), np.nan)
    for i in range(ATR_N - 1, len(c)):
        atr[i] = tr[i - ATR_N + 1:i + 1].mean()
    _st, sw_hi, sw_lo = structure.swings(h, l, structure.SWING_K["15m"])
    return {"atr15": atr, "sw_lo": sw_lo, "sw_hi": sw_hi}


def _run(fx, aux, lo, hi, state=None):
    spec = shadows.CHALLENGERS[BOOK]
    cfg = live.asset_cfg(SYM, dict(CFG, **spec["cfg"]))
    return shadows.run(fx["px"], fx["odds"], fx["shock"], fx["tide"], fx["unit"], cfg, lo, hi, state=state,
                       bias=fx["bias"], guard=fx["guard"], rule=spec["rule"], times_ms=fx["times_ms"], aux=aux)


def _market(fx, i, state, voice, trades_dir):
    close_ms = int(fx["times_ms"][i]) + BAR_MS
    stamp = g._iso(close_ms)
    page = {"name": "Mind 15", "generated_utc": stamp, "version": "golden", "markets": {"crypto": [SYM]},
            "assets": {SYM: {"short": "BTC", "time": stamp[:16].replace("T", " "), "price": float(fx["px"]["close"][i]),
                             "edge_pts": g._num(fx["edge"][i]), "market_group": "crypto"}},
            "shadows": {"books": {setups.BOOK: {"assets": {SYM: shadows.asset_view({})}},      # the other voice: flat
                                  BOOK: {"assets": {SYM: shadows.asset_view(state)}}},
                        "markets": {"crypto": {"as_of_utc": stamp[:16].replace("T", " ")}}}}
    m = setups.build(page, voice=voice, trail_trades=setups.read_trades(trades_dir, BOOK))["markets"][0]
    if m.get("side") in ("LONG", "SHORT"):                        # the S1 record is not part of this fixture: the window
        m["entry_window_open"] = m.get("opened_utc") == m.get("price_bar_utc")     # is open at the setup's opening step
    return m


def play(fx, trades_dir):
    """-> {"trades", "books", "refused", "intents"}: what the vault would be told on the trail voice, in order."""
    old = vf.SEND_TRAIL
    vf.SEND_TRAIL = True
    try:
        aux = aux_of(fx)
        voice = {"schema": 1, "markets": {SYM: {"rule": setups_voice.TRAIL, "from_utc": g._iso(int(fx["times_ms"][0])),
                                                "pending": False, "wait": None}}}
        state, feed = None, {}
        trades, books, refused, intents, last, sent = [], [], [], [], None, set()
        for i in range(1, fx["n"]):
            b = _run(fx, aux, i, i + 1, state)
            state = json.loads(json.dumps(b["state"]))
            closed = b["trades"][b["trades"].why_out != "OPEN"]
            if len(closed):
                shadows.journal_trades({(BOOK, SYM): closed}, out_dir=trades_dir)
                trades += [g._trade(r) for _, r in closed.iterrows()]
            m = _market(fx, i, state, voice, trades_dir)
            why = vf.track(SYM, m, feed, trades_dir, float(i))
            assert why is None, (i, why)
            for iid, it in sorted(feed.get("intents", {}).items(), key=lambda kv: kv[1]["seq"]):
                if iid not in sent:
                    assert vf.intent_ok(it["body"]), it["body"]
                    sent.add(iid)
                    intents.append({"i": i, "body": it["body"]})
            view = {"shadows": {"books": {BOOK: {"assets": {SYM: shadows.asset_view(state)}}}}}
            body, reason = vf.build_book(m, m.get("price_bar_utc"), vf.remembered_lead(feed, SYM, m), False,
                                         vf.remembered_opened_by(feed, SYM, m, view))        # v5.2.11: opened_by
            if body is None:
                refused.append({"i": i, "reason": reason})
                continue
            bk = body["book"]
            key = tuple(bk.get(k) for k in ("side", "entry", "stop", "trail_active", "entry_window_open", "opened_utc"))
            if key != last:                                       # a new setup, a stop that moved, the window, or flat
                books.append({"i": i, "body": body})
                last = key
        return {"trades": trades, "books": books, "refused": refused, "intents": intents}
    finally:
        vf.SEND_TRAIL = old


def _want():
    with open(GOLDEN, encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------ the tests
def test_the_trail_voice_gives_the_recorded_trades_books_and_intents(tmp_path):
    want = _want()
    got = json.loads(json.dumps(play(g.load_fixture(), str(tmp_path))))
    assert len(got["trades"]) == len(want["trades"]), "the number of closed trades changed"
    for k, (a, w) in enumerate(zip(got["trades"], want["trades"])):
        for c in g.TRADE_EXACT:
            assert a[c] == w[c], "trade %d: %s is %r, the record says %r" % (k, c, a[c], w[c])
        for c in g.TRADE_NUM:
            assert g._close(a[c], w[c]), "trade %d: %s is %r, the record says %r" % (k, c, a[c], w[c])
    assert got["books"] == want["books"], "a trail book body changed"
    assert got["refused"] == want["refused"], "which books are refused changed"
    assert got["intents"] == want["intents"], "a trail intent changed"


def test_the_record_walks_through_the_trail_rule():
    want = _want()
    whys = [t["why_out"] for t in want["trades"]]
    assert len(whys) >= 30 and "TRAIL" in whys and "STOP" in whys
    assert not any("T1" in w or "T2" in w for w in whys)                                  # no targets, ever
    assert set(t["side"] for t in want["trades"]) == {1, -1}
    acts = set((x["body"]["action"], x["body"]["market"]) for x in want["intents"])
    assert acts == {("close", "spot"), ("close", "futures"), ("move_stop", "futures")}    # never a reduce
    assert want["refused"] == []
    sides = set(x["body"]["book"]["side"] for x in want["books"])
    assert sides >= {"LONG", "SHORT"}
    for x in want["books"]:
        b = x["body"]["book"]
        if b["side"] == "FLAT":
            assert "exit_rule" not in b and b["t1_taken"] is False                        # today's FLAT body
        else:
            assert b["exit_rule"] == "trail" and isinstance(b["trail_active"], bool)
            assert not {"target_1", "target_2", "rr_now_t2", "t1_taken"} & set(b)
    assert any(x["body"]["book"].get("trail_active") for x in want["books"])


def test_every_stop_move_is_tighter_than_the_one_before_and_each_setup_opens_at_its_first_sight():
    want = _want()
    last = {}                                                     # the setup (id prefix) -> the last stop sent
    for x in want["intents"]:
        b = x["body"]
        if b["action"] != "move_stop":
            continue
        setup = b["intent_id"].rsplit(".", 2)[0]
        stop, long = float(b["stop_price"]), b["side"] == "BUY"
        if setup in last:
            assert stop > last[setup] if long else stop < last[setup], b
        last[setup] = stop
        assert (stop < float(b["reference_price"])) if long else (stop > float(b["reference_price"])), b
    ids = [x["body"]["intent_id"] for x in want["intents"]]
    assert len(ids) == len(set(ids))
    seen = set()
    for x in want["books"]:
        b = x["body"]["book"]
        if b["side"] != "FLAT" and b["opened_utc"] not in seen:
            seen.add(b["opened_utc"])
            if b["opened_utc"] == b["as_of_utc"]:                 # an early entry: on the book in the step that decides it
                assert b["trail_active"] is False and b["entry_window_open"] is True


def test_one_run_over_all_bars_equals_the_bar_by_bar_run(tmp_path):
    fx = g.load_fixture()
    whole = _run(fx, aux_of(fx), 1, fx["n"])
    w = [g._trade(r) for _, r in whole["trades"][whole["trades"].why_out != "OPEN"].iterrows()]
    got = play(fx, str(tmp_path))["trades"]
    assert len(w) == len(got)
    for a, b in zip(w, got):
        assert all(a[c] == b[c] for c in g.TRADE_EXACT) and all(g._close(a[c], b[c]) for c in g.TRADE_NUM)


def test_the_names_the_trail_voice_relies_on():
    assert BOOK == "b_trail_setups"
    assert shadows.CHALLENGERS[BOOK]["rule"] == {"trail": True, "early": True} and shadows.CHALLENGERS[BOOK]["cfg"] == {}
    assert (shadows.TRAIL_ARM_R, shadows.TRAIL_ATR) == (1.0, 2.0)
    from conftest import SHIPPED                                            # ON since think15-v5.2.12
    assert SHIPPED["SEND_TRAIL"] is True and SHIPPED["TRAIL_MARKETS"] == ("BTCUSDT", "ETHUSDT")


# ------------------------------------------------------------------ writing the record
if __name__ == "__main__":
    if "--write-golden" in sys.argv:
        with tempfile.TemporaryDirectory() as d:
            rec = play(g.load_fixture(), d)
        rec = dict({"note": "What the money path gives on money_path_bars.json when the market is on the trail voice. "
                            "Once the switches are on: rewritten only on the owner's word, with a version bump.",
                    "engine_version": CFG["version"]}, **rec)
        with open(GOLDEN, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(rec, fh, indent=1, sort_keys=True)
            fh.write("\n")
        print("wrote %s: %d trades, %d book bodies, %d intents, %d refused" % (
            GOLDEN, len(rec["trades"]), len(rec["books"]), len(rec["intents"]), len(rec["refused"])))
    else:
        sys.exit("use --write-golden")
