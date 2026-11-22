# -*- coding: utf-8 -*-
"""THE MONEY PATH, FROZEN. No network, no vault, no file outside tests/fixtures and the test's own temp folder.

The site's VIP vault copies the paper book `b_targets` through engine15/vault_feed.py (owner, 18 Nov 2026), so
the code below decides real entries, stops and exits of opted-in accounts:

    shadows.run under the b_targets rule    the book: entries (policy.decide), sizing (backtest.leverage), the stop,
                                            half at Target 1, the stop to the entry, the rest at Target 2
    live.plan_targets                       the two targets, set once at entry
    shadows.asset_view -> setups.build      the market entry of setups.json
    vault_feed.track / build_book           the book body sent to the vault and the exit intents queued

This test plays a FIXED set of 15-minute bars and readings (tests/fixtures/money_path_bars.json, one market, BTCUSDT
with its real fee and sizing from live.asset_cfg) through exactly that chain, one bar at a time as the live engine
does, and compares every closed trade, every book body and every exit intent with the record in
tests/fixtures/money_path_golden.json. ANY change to those is a failure here.

If this test fails, the change you made alters what the vault would have been told. That is never a side effect to
accept: it needs the owner's word and a version bump (CLAUDE.md, Rules). Only then rewrite the record:

    py -3 tests/test_money_path_golden.py --write-golden      (the bars are never rewritten for a rule change)

The bars themselves were made once by make_fixture() (a seeded random walk; nothing is read from the market) and are
kept as a file so that a library change can never move them.
"""
import calendar
import json
import os
import sys
import tempfile
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import exits, live, setups, shadows  # noqa: E402
from engine15 import vault_feed as vf  # noqa: E402
from engine15.config import CFG  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BARS = os.path.join(HERE, "fixtures", "money_path_bars.json")
GOLDEN = os.path.join(HERE, "fixtures", "money_path_golden.json")
SYM = "BTCUSDT"
BAR_MS = 900000
T0_MS = calendar.timegm(time.strptime("2026-11-18T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")) * 1000
TARGET_COLS = ("reach_24h_med_pct", "fib_1h_dir", "fib_1h_t1_px", "fib_1h_t2_px")
TRADE_NUM = ("p_in", "p_out", "pnl_pct", "equity", "qty", "pnl_usd", "fees_usd", "stop0", "risk_usd", "r_mult",
             "target_1", "target_2")
# i_in is left out: a book resumed from saved state does not carry the entry bar's index (t_in_ms is the entry time)
TRADE_EXACT = ("t_in_ms", "t_out_ms", "i_out", "side", "why_in", "why_out")
STATE_NUM = ("qty", "entry", "stop", "eq", "fees", "t1", "t2", "qty0")
STATE_EXACT = ("pos", "idle", "t1_hit", "why_in")


# ------------------------------------------------------------------ the bars (made once, then a file)
def make_fixture(n=480, seed=20261120):
    """A seeded random walk near 65,000 with every input the book reads. Rounded here: the file IS the fixture."""
    rng = np.random.RandomState(seed)
    c = np.round(65000.0 * np.exp(np.cumsum(rng.normal(0, 0.004, n))), 2)
    o = np.concatenate([[65000.0], c[:-1]])
    sp = np.round(np.abs(rng.normal(0, 0.003, n)) * c, 2)
    odds = np.round(rng.dirichlet(np.ones(3) * 25, size=n), 4)
    odds[:5] = np.nan                                             # still learning at the start: WAIT
    mode = rng.choice(3, size=n, p=[0.4, 0.3, 0.3])              # where the targets come from: reach / 1.5R / a Fib leg
    d = rng.choice([-1.0, 1.0], size=n)
    reach = np.where(mode == 0, np.round(rng.uniform(0.5, 2.0, n), 2), np.nan)
    f1 = np.where(mode == 2, np.round(c * (1 + d * rng.uniform(0.004, 0.012, n)), 2), np.nan)
    f2 = np.where(mode == 2, np.round(c * (1 + d * rng.uniform(0.013, 0.030, n)), 2), np.nan)

    def col(a):
        return [None if x != x else float(x) for x in a]

    return {"note": "Made once by tests/test_money_path_golden.py make_fixture(n=%d, seed=%d). Never edit." % (n, seed),
            "symbol": SYM, "t0_ms": T0_MS, "bar_ms": BAR_MS,
            "open": col(o), "high": col(np.maximum(o, c) + sp), "low": col(np.minimum(o, c) - sp), "close": col(c),
            "odds": [col(r) for r in odds], "unit": col(np.round(c * 0.004, 2)),
            "shock": [bool(x) for x in rng.rand(n) < 0.05], "tide": col(np.round(rng.uniform(-1, 1, n), 3)),
            "bias": col(rng.choice([-1.0, 0.0, 1.0], size=n, p=[0.2, 0.6, 0.2])),
            "guard": [bool(x) for x in rng.rand(n) < 0.03],
            "edge_pts": col(np.round((odds[:, 1] - odds[:, 2]) * 100, 2)),
            "reach_24h_med_pct": col(reach), "fib_1h_dir": col(np.where(mode == 2, d, np.nan)),
            "fib_1h_t1_px": col(f1), "fib_1h_t2_px": col(f2)}


def load_fixture():
    with open(BARS, encoding="utf-8") as fh:
        f = json.load(fh)

    def arr(k):
        return np.array([np.nan if x is None else x for x in f[k]], dtype=float)

    n = len(f["close"])
    return {"n": n, "px": dict((k, arr(k)) for k in ("open", "high", "low", "close")),
            "odds": np.array([[np.nan if x is None else x for x in r] for r in f["odds"]], dtype=float),
            "unit": arr("unit"), "shock": np.array(f["shock"], dtype=bool), "tide": arr("tide"), "bias": arr("bias"),
            "guard": np.array(f["guard"], dtype=bool), "edge": arr("edge_pts"),
            "targets": pd.DataFrame(dict((k, arr(k)) for k in TARGET_COLS)),
            "times_ms": f["t0_ms"] + np.arange(n, dtype="int64") * f["bar_ms"]}


# ------------------------------------------------------------------ the chain, one bar at a time
def _iso(ms):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ms // 1000))


def _num(x):
    return None if x is None or x != x else float(x)


def _run(fx, lo, hi, state=None):
    spec = shadows.CHALLENGERS[setups.BOOK]
    cfg = live.asset_cfg(SYM, dict(CFG, **spec["cfg"]))          # as shadows.run_challenger builds it
    tgt = fx["targets"]
    return shadows.run(fx["px"], fx["odds"], fx["shock"], fx["tide"], fx["unit"], cfg, lo, hi, state=state,
                       bias=fx["bias"], guard=fx["guard"], rule=spec["rule"], times_ms=fx["times_ms"],
                       row_of=lambda k: tgt.iloc[k])


def _trade(row):
    out = dict((k, _num(row[k])) for k in TRADE_NUM)
    out.update((k, row[k] if isinstance(row[k], str) else int(row[k])) for k in TRADE_EXACT)
    return out


def _market(fx, i, state):
    """The setups.json market entry the feed reads, from the book's state after bar i (as the page carries it)."""
    close_ms = int(fx["times_ms"][i]) + BAR_MS
    stamp = _iso(close_ms)
    page = {"name": "Mind 15", "generated_utc": stamp, "version": "golden", "markets": {"crypto": [SYM]},
            "assets": {SYM: {"short": "BTC", "time": stamp[:16].replace("T", " "), "price": float(fx["px"]["close"][i]),
                             "edge_pts": _num(fx["edge"][i]), "market_group": "crypto"}},
            "shadows": {"books": {setups.BOOK: {"assets": {SYM: shadows.asset_view(state)}}},
                        "markets": {"crypto": {"as_of_utc": stamp[:16].replace("T", " ")}}}}
    return setups.build(page)["markets"][0]


def play(fx, trades_dir):
    """-> {"trades", "state_end", "books", "refused", "intents"}: what the vault would have been told, in order.
    The feed's guard (exits only for a setup whose entry window it saw open) is off here, as in the feed's own
    mechanics tests: the entry window comes from the S1 record, which is not part of this fixture."""
    old_guard, vf.EXITS_ONLY_IF_WINDOW_SEEN = vf.EXITS_ONLY_IF_WINDOW_SEEN, False
    try:
        state, feed = None, {}
        trades, books, refused, intents, last, sent = [], [], [], [], None, set()
        for i in range(1, fx["n"]):
            b = _run(fx, i, i + 1, state)
            state = json.loads(json.dumps(b["state"]))            # the live engine keeps the state as JSON
            closed = b["trades"][b["trades"].why_out != "OPEN"]
            if len(closed):
                shadows.journal_trades({(setups.BOOK, SYM): closed}, out_dir=trades_dir)
                trades += [_trade(r) for _, r in closed.iterrows()]
            m = _market(fx, i, state)
            why = vf.track(SYM, m, feed, trades_dir, float(i))
            assert why is None, (i, why)
            for iid, it in sorted(feed.get("intents", {}).items(), key=lambda kv: kv[1]["seq"]):
                if iid not in sent:
                    assert vf.intent_ok(it["body"]), it["body"]
                    sent.add(iid)
                    intents.append({"i": i, "body": it["body"]})
            body, reason = vf.build_book(m, m.get("price_bar_utc"))
            if body is None:
                refused.append({"i": i, "reason": reason})
                continue
            bk = body["book"]
            key = tuple(bk.get(k) for k in ("side", "entry", "stop", "target_1", "target_2", "t1_taken", "opened_utc"))
            if key != last:                                       # a new setup, Target 1 taken, or flat: keep the body
                books.append({"i": i, "body": body})
                last = key
        end = dict((k, _num(state.get(k))) for k in STATE_NUM)
        end.update((k, state.get(k)) for k in STATE_EXACT)
        return {"trades": trades, "state_end": end, "books": books, "refused": refused, "intents": intents}
    finally:
        vf.EXITS_ONLY_IF_WINDOW_SEEN = old_guard


def _close(a, b):
    if a is None or b is None:
        return a is b
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


# ------------------------------------------------------------------ the tests
def test_the_money_path_gives_the_recorded_trades_books_and_intents(tmp_path):
    with open(GOLDEN, encoding="utf-8") as fh:
        want = json.load(fh)
    got = play(load_fixture(), str(tmp_path))
    got = json.loads(json.dumps(got))                             # the same shapes as the record
    assert len(got["trades"]) == len(want["trades"]), "the number of closed trades changed"
    for k, (g, w) in enumerate(zip(got["trades"], want["trades"])):
        for c in TRADE_EXACT:
            assert g[c] == w[c], "trade %d: %s is %r, the record says %r" % (k, c, g[c], w[c])
        for c in TRADE_NUM:
            assert _close(g[c], w[c]), "trade %d: %s is %r, the record says %r" % (k, c, g[c], w[c])
    for c in STATE_EXACT:
        assert got["state_end"][c] == want["state_end"][c], c
    for c in STATE_NUM:
        assert _close(got["state_end"][c], want["state_end"][c]), c
    assert got["books"] == want["books"], "a book body sent to the vault changed"
    assert got["refused"] == want["refused"], "which books are refused changed"
    assert got["intents"] == want["intents"], "an exit intent changed"


def test_the_record_covers_every_branch_of_the_rule():
    """The fixture is only a freeze if it walks through each way a setup can end and each way a target is planned."""
    with open(GOLDEN, encoding="utf-8") as fh:
        want = json.load(fh)
    whys = [t["why_out"] for t in want["trades"]]
    assert len(whys) >= 30
    for w in ("STOP", "T1+T2", "T1+STOP_BE"):
        assert w in whys, w
    assert any(w.startswith("T1+") and not w.endswith(("T2", "STOP_BE")) for w in whys)      # a flip after Target 1
    assert any(w in ("FLIP", "STEP_ASIDE") for w in whys)
    assert set(t["side"] for t in want["trades"]) == {1, -1}
    assert set(t["why_in"] for t in want["trades"]) >= {"FORCED", "FLIP"}
    acts = set((x["body"]["action"], x["body"]["market"]) for x in want["intents"])
    assert acts == {("close", "spot"), ("close", "futures"), ("reduce", "spot"), ("reduce", "futures"),
                    ("move_stop", "futures")}
    sides = set(x["body"]["book"]["side"] for x in want["books"])
    assert sides == {"LONG", "SHORT", "FLAT"}
    assert any(x["body"]["book"].get("t1_taken") for x in want["books"])


def test_one_run_over_all_bars_equals_the_bar_by_bar_run(tmp_path):
    fx = load_fixture()
    whole = _run(fx, 1, fx["n"])
    w = [_trade(r) for _, r in whole["trades"][whole["trades"].why_out != "OPEN"].iterrows()]
    g = play(fx, str(tmp_path))["trades"]
    assert len(w) == len(g)
    for a, b in zip(w, g):
        assert all(a[c] == b[c] for c in TRADE_EXACT) and all(_close(a[c], b[c]) for c in TRADE_NUM)


def test_the_bars_are_the_ones_that_were_made():
    """The file is what make_fixture() made: nobody edited a bar to make a change pass."""
    with open(BARS, encoding="utf-8") as fh:
        f = json.load(fh)
    made = json.loads(json.dumps(make_fixture()))
    assert f["t0_ms"] == made["t0_ms"] and len(f["close"]) == len(made["close"]) == 480
    for k in ("open", "high", "low", "close", "unit", "tide"):
        assert all(_close(a, b) for a, b in zip(f[k], made[k])), k
    assert f["shock"] == made["shock"] and f["guard"] == made["guard"] and f["bias"] == made["bias"]


def test_the_names_and_shares_the_vault_relies_on():
    assert setups.BOOK == "b_targets"
    assert shadows.CHALLENGERS["b_targets"]["rule"] == {"targets": True, "early": True}      # v5.2.9: the early entry
    assert shadows.CHALLENGERS["b_targets"]["cfg"] == {} and CFG["early_entry"] == ("BTCUSDT", "ETHUSDT")
    assert shadows.PART == exits.PART == vf.REDUCE_FRACTION == 0.5        # the share closed at Target 1, everywhere
    assert vf.ACTIONS == ("close", "reduce", "move_stop")                 # exits only: never "open"
    assert vf.ALLOWED == ("BTCUSDT", "ETHUSDT")                           # the owner's two markets, no more
    assert vf.SEND_CONTRACT_1 is False                                    # no key the live vault does not know


# ------------------------------------------------------------------ writing the record (owner's word only)
if __name__ == "__main__":
    if "--write-fixture" in sys.argv:
        if os.path.exists(BARS):
            sys.exit("the bars exist already and are never rewritten: %s" % BARS)
        os.makedirs(os.path.dirname(BARS), exist_ok=True)
        with open(BARS, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(make_fixture(), fh, separators=(",", ":"))
        print("wrote", BARS)
    elif "--write-golden" in sys.argv:
        with tempfile.TemporaryDirectory() as d:
            rec = play(load_fixture(), d)
        rec = dict({"note": "What the money path gives on money_path_bars.json. Rewritten only on the owner's word, with "
                            "a version bump (see tests/test_money_path_golden.py).", "engine_version": CFG["version"]},
                   **rec)
        with open(GOLDEN, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(rec, fh, indent=1, sort_keys=True)
            fh.write("\n")
        print("wrote %s: %d trades, %d book bodies, %d intents, %d refused" % (
            GOLDEN, len(rec["trades"]), len(rec["books"]), len(rec["intents"]), len(rec["refused"])))
    else:
        sys.exit("use --write-fixture (once) or --write-golden (owner's word only)")
