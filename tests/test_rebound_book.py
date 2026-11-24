# -*- coding: utf-8 -*-
"""H117: the Setups rule with the capitulation-rebound override (shadow book b_rebound, engine15/rebound_book.py and
the rule key "rebound" in engine15/shadows.run). A paper shadow, NOT passed. No network; nothing is written outside
pytest's tmp_path.

What is held here:
  * shadows.py is a money-path file. Every book that existed before (b_targets, the vault's book, among them) gives
    what the code on main gave: tests/fixtures/rebound_main_books.json was written by THIS file run on main's code
    (commit 46df899, before the rule key existed) and is compared here; and with the key off the new lines are never
    reached (a poisoned trigger and a poisoned state are never touched).
  * with no trigger b_rebound is b_targets, bar for bar;
  * with a trigger: from SHORT, from FLAT, while LONG; the long is playbook9's trade bar by bar; the Setups rule is
    not consulted while it lives and resumes after; a second trigger is counted; restart mid-trade; no look-ahead;
  * the forward book: BTC and ETH only, guarded, a failing trigger, a failing step, a state file written by main.

    py -3 -m pytest tests/test_rebound_book.py -q
    py -3 tests/test_rebound_book.py --write-main-fixture OUT.json     (ONLY on a checkout of main's code: it refuses
                                                                         to run where the rule key exists)
"""
import copy
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from engine15 import shadows  # noqa: E402
from engine15.config import CFG  # noqa: E402

try:
    from engine15 import playbook9 as p9  # noqa: E402
    from engine15 import rebound_book as rb  # noqa: E402
except ImportError:                                              # main's code, when the fixture is written
    p9 = rb = None
import test_money_path_golden as golden  # noqa: E402
from test_shadows import aux_for, fake_prep, random_inputs  # noqa: E402

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "rebound_main_books.json")
BAR = CFG["bar_ms"]
BASE = shadows.CHALLENGERS["b_targets"]["rule"]
RULE = dict(BASE, rebound=True)
HOW_WORD = {0: "STOP", 1: "T1+STOP_BE", 2: "T1+T2", 3: "T1+TIME", 4: "TIME"}


# =====================================================================================
# what main's code gave (the fixture), and how a book is summed up
# =====================================================================================
DISCRETE = ("t_in_ms", "t_out_ms", "i_in", "i_out", "side", "why_in", "why_out")
FULL = ("b_targets", "b_trend30", "b_wait_stop", "main")        # every trade's result and exit price are kept for these


def tr_digest(tr, skip=(), full=True):
    disc = [c for c in DISCRETE if c in tr.columns and c not in skip]
    rows = [[v if isinstance(v, str) else (None if v is None or v != v else int(v)) for v in r]
            for r in tr[disc].values.tolist()]
    nums = [c for c in tr.columns if c not in DISCRETE]
    out = {"n": int(len(tr)), "rows_sha": hashlib.sha256(json.dumps(rows).encode("utf-8")).hexdigest(),
           "sums": dict((c, float(np.nansum(pd.to_numeric(tr[c], errors="coerce").values.astype(float)))) for c in nums)}
    if full:
        out.update(pnl_usd=[float(x) for x in tr["pnl_usd"]], p_out=[float(x) for x in tr["p_out"]])
    return out


def digest(res, full=True):
    held = np.asarray(res["held"]).astype(int)
    return dict(tr_digest(res["trades"], full=full), state=json.loads(json.dumps(res["state"], default=float)),
                equity_sum=float(np.nansum(res["equity"])), equity_last=float(res["equity"][-1]),
                held_abs=int(np.abs(held).sum()), held_net=int(held.sum()))


def differences(a, b, path="", rtol=1e-9):
    """Where two JSON-like values differ: exact for words, whole numbers and flags, rtol for floats (the fixture was
    written on one machine; a libm that rounds a last digit differently must not fail it)."""
    if isinstance(a, dict) or isinstance(b, dict):
        if not (isinstance(a, dict) and isinstance(b, dict)) or set(a) != set(b):
            return [path + ": keys"]
        return [d for k in sorted(a) for d in differences(a[k], b[k], "%s.%s" % (path, k), rtol)]
    if isinstance(a, (list, tuple)) or isinstance(b, (list, tuple)):
        if not (isinstance(a, (list, tuple)) and isinstance(b, (list, tuple))) or len(a) != len(b):
            return [path + ": length"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in differences(x, y, "%s[%d]" % (path, i), rtol)]
    if isinstance(a, float) or isinstance(b, float):
        if a is None or b is None or isinstance(a, (str, bool)) or isinstance(b, (str, bool)):
            return [] if a == b else [path]
        if a != a or b != b:
            return [] if (a != a and b != b) else [path]
        return [] if abs(a - b) <= rtol * max(1.0, abs(a), abs(b)) else [path]
    return [] if a == b else [path]


def golden_inputs():
    """The money-path fixture bars (a file, never recomputed) with planted readings for the other books."""
    fx = golden.load_fixture()
    aux = aux_for(fx["n"])
    aux["targets"] = fx["targets"]
    return (fx["px"], fx["odds"], fx["unit"], fx["shock"], fx["tide"], fx["bias"], fx["guard"], aux), fx["times_ms"]


def run(inp, rule, trig="none", lo=1, hi=None, state=None, cfg=None, times_ms=None):
    px, odds, unit, shock, tide, bias, guard, aux = inp
    n = len(px["close"])
    aux = aux if isinstance(trig, str) else dict(aux, rebound=trig)
    return shadows.run(px, odds, shock, tide, unit, cfg or shadows.asset_cfg("BTCUSDT", dict(CFG)), lo, hi or n,
                       state=state, bias=bias, guard=guard, rule=rule, aux=aux,
                       times_ms=np.arange(n, dtype="int64") * BAR if times_ms is None else times_ms,
                       row_of=lambda k: aux["targets"].iloc[k])


def main_books():
    """Every challenger of shadows.CHALLENGERS on the golden bars and on a longer made-up run."""
    out = {"golden_bars": {}, "synthetic_3000": {}}
    g_inp, g_ms = golden_inputs()
    s_inp = random_inputs(n=3000, seed=17)
    for name, spec in shadows.CHALLENGERS.items():
        cfg = shadows.asset_cfg("BTCUSDT", dict(CFG, **spec["cfg"]))
        out["golden_bars"][name] = digest(run(g_inp, spec["rule"], cfg=cfg, times_ms=g_ms), full=name in FULL)
        out["synthetic_3000"][name] = digest(run(s_inp, spec["rule"], cfg=cfg), full=name in FULL)
    return out


def main_state_file():
    """A shadow_state.json as the forward step writes it at session 420, and where every book stands at 700."""
    prep = fake_prep()
    sst = {"version": 1, "groups": {}, "books": {}}
    shadows.advance(prep, "crypto", ["BTCUSDT"], 420, sst, start_lo=100)
    written = json.loads(json.dumps(sst, default=float))
    _v, closed = shadows.advance(prep, "crypto", ["BTCUSDT"], 700, sst)
    after = json.loads(json.dumps(sst, default=float))
    return {"at_420": written, "at_700": after,
            "closed_420_700": dict(("%s|%s" % k, tr_digest(v, skip=("i_in",), full=k[0] in FULL))
                                   for k, v in closed.items())}


def write_main_fixture(path):
    with open(shadows.__file__, encoding="utf-8") as fh:
        if "rebound" in fh.read():
            raise SystemExit("this is not main's code: the fixture is what the code gave BEFORE the rule key existed")
    out = {"note": "Written by tests/test_rebound_book.py --write-main-fixture on main's code (commit 46df899, before "
                   "H117's rule key existed). What every book gave then. Never rewrite it to make a change pass.",
           "books": main_books(), "state_file": main_state_file()}
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, sort_keys=True, separators=(",", ":"))
        fh.write("\n")
    print("written", path, dict((k, len(v)) for k, v in out["books"].items()))


if __name__ == "__main__":
    if "--write-main-fixture" in sys.argv:
        write_main_fixture(sys.argv[sys.argv.index("--write-main-fixture") + 1])
    sys.exit(0)


# =====================================================================================
# planted inputs
# =====================================================================================
def gap_inputs(n=3000, seed=3):
    """random_inputs with a gap between a close and the next open, so a fill at the next open is not the close."""
    px, odds, unit, shock, tide, bias, guard, aux = random_inputs(n=n, seed=seed)
    rng = np.random.RandomState(seed + 1000)
    o = px["open"] * (1.0 + rng.normal(0, 0.0006, n))
    px = {"open": o, "high": np.maximum(px["high"], o), "low": np.minimum(px["low"], o), "close": px["close"]}
    return px, odds, unit, shock, tide, bias, guard, aux


def trig_at(n, ks, atr, b=None):
    """The trigger arrays as rebound_book.trigger hands them over, with rule A's onset planted at bars ks."""
    A = np.zeros(n, dtype=bool)
    A[list(ks)] = True
    B = np.full(n, -1, dtype=np.int8)
    if b is not None:
        B[list(ks)] = int(b)
    return {"A": A, "atr": np.broadcast_to(np.asarray(atr, dtype=float), (n,)).copy(), "B": B,
            "stop_atr": float(p9.STOP_ATR), "hold": int(p9.HOLD), "fee": float(p9.FEE)}


def rows(res):
    return list(res["trades"].itertuples(index=False))


def p9_trade(px, k, atr):
    """playbook9's own trade for a trigger at the close of bar k: (the closed trade, its exit bar, the path)."""
    o, h, l, c = (px[x] for x in ("open", "high", "low", "close"))
    tr = p9._open_trade({"r_dist": p9.STOP_ATR * float(atr), "decided_ms": (k + 1) * BAR}, float(o[k + 1]), (k + 1) * BAR)
    path = {}
    for i in range(k + 1, len(c)):
        done = p9._walk_bar(tr, float(o[i]), float(h[i]), float(l[i]), float(c[i]), (i + 1) * BAR)
        if done is not None:
            return done, i, path
        path[i] = (tr["stop"], tr["t1_taken"], tr["q"], tr["bars"])
    return None, None, path


def not_long_at_close(base, k):
    """True when the b_targets book is short or flat at the close of bar k, before that close's decision."""
    return base["held"][k] != 1


def capit_bars(seed=5, days=62, crashes=(46, 54)):
    """Quiet bars with two capitulations: a fall of about 20% in 18 hours, then a sharp rebound."""
    rng = np.random.RandomState(seed)
    n = days * 96
    r = rng.normal(0, 0.0012, n)
    for d in crashes:
        k = d * 96
        r[k:k + 72] -= 0.22 / 72
        r[k + 72:k + 80] += 0.008
    c = 100.0 * np.exp(np.cumsum(r))
    o = np.concatenate([[100.0], c[:-1]]) * (1.0 + rng.normal(0, 0.0003, n))
    sp = np.abs(rng.normal(0, 0.0008, n)) * c
    return {"open": o, "high": np.maximum(o, c) + sp, "low": np.minimum(o, c) - sp, "close": c}


def capit_prep(odds="random", assets=("BTCUSDT", "ETHUSDT"), days=62, seed=5):
    """A prepared group on the capitulation bars. odds "none": the engine has no odds, so the Setups rule never
    trades and the book holds only the override's longs; "random": it trades all the time."""
    n = days * 96
    times = pd.date_range("2026-01-01", periods=n, freq="15min", tz="UTC")
    prep = {"cfg": dict(CFG), "times": times, "px": {}, "odds": {}, "ev": {}}
    for j, a in enumerate(assets):
        rng = np.random.RandomState(seed + 50 + j)
        px = capit_bars(seed=seed + j, days=days)
        c = px["close"]
        od = rng.dirichlet(np.ones(3) * 25, size=n) if odds == "random" else np.full((n, 3), np.nan)
        prep["px"][a], prep["odds"][a] = px, od
        prep["ev"][a] = pd.DataFrame({
            "shock": rng.rand(n) < 0.05, "tide": rng.uniform(-1, 1, n), "atr1h": c * 0.006 / CFG["barrier_atr"] * 1.5,
            "atr15": c * 0.003, "htf_bias": rng.choice([-1.0, 0.0, 1.0], size=n, p=[0.2, 0.6, 0.2]),
            "release_soon": rng.rand(n) < 0.03, "sw_lo_15m": c * 0.99, "sw_hi_15m": c * 1.01,
            "reach_24h_med_pct": rng.uniform(0.5, 2.0, n)}, index=times)
    return prep


def fresh():
    return {"version": 1, "groups": {}, "books": {}}


def without_the_side_notes(st):
    """A b_rebound state without what each rebound long records about the Setups book over the same bars: that is
    read at the end of a step, beside the read, so it depends on how long the steps were. Nothing else does."""
    st = json.loads(json.dumps(dict(st, i_in=0)))
    for rec in st["rebound"]["closed"] + [st["rebound"].get("trade") or {}, st["rebound"].get("next") or {}]:
        for key in ("setups_eq", "setups_eq_out", "setups_pct", "setups_exact"):
            rec.pop(key, None)
    return st


def frame(prep, a, hi=None):
    px = prep["px"][a]
    return pd.DataFrame(dict((k, px[k][:hi]) for k in ("open", "high", "low", "close")), index=prep["times"][:hi])


# =====================================================================================
# 1. the money path: every book that existed is what main gave; the key off never reaches the new lines
# =====================================================================================
def test_the_rule_is_b_targets_plus_one_key_and_it_cannot_reach_the_vault():
    from engine15 import setups, signals
    assert rb.rule() == dict(shadows.CHALLENGERS["b_targets"]["rule"], rebound=True) == RULE
    assert not any(spec["rule"].get("rebound") for spec in shadows.CHALLENGERS.values())
    assert rb.NAME == "b_rebound" and rb.NAME not in shadows.CHALLENGERS and rb.NAME not in shadows.FOLLOWERS
    assert shadows.MINDS[rb.NAME]["module"] is rb and rb.ASSETS == ("BTCUSDT", "ETHUSDT") and rb.BASE == "b_targets"
    assert setups.BOOK == "b_targets" and signals.BOOK == "b_targets"         # the vault's book is the Setups book
    here = os.path.dirname(shadows.__file__)
    for name in ("setups.py", "signals.py", "vault_feed.py", "policy.py", "backtest.py", "exits.py", "config.py",
                 "live.py"):
        with open(os.path.join(here, name), encoding="utf-8") as fh:
            src = fh.read()
        assert "rebound" not in src, name
    for word in ("NOT passed", "paper only"):
        assert word in rb.TITLE and word in rb.SCOREBOARD_TITLE and word in rb.LABEL + rb.TITLE
    assert rb.SCOREBOARD_TITLE.startswith("Shadow") and "never run on history" in rb.NOTE
    with open(os.path.join(here, "shadows.py"), encoding="utf-8") as fh:      # playbook9 is not on any other book's path
        assert "playbook9" not in fh.read()
    with open(os.path.join(here, "rebound_book.py"), encoding="utf-8") as fh:
        src = fh.read()
    assert src.count("import playbook9") == 1 and "    from . import playbook9 as p9" in src   # inside trigger() only


def test_every_book_that_existed_gives_what_main_gave():
    with open(FIXTURE, encoding="utf-8") as fh:
        want = json.load(fh)["books"]
    got = main_books()
    for run_name in ("golden_bars", "synthetic_3000"):
        assert set(want[run_name]) <= set(shadows.CHALLENGERS) and "b_targets" in want[run_name]
        for name in want[run_name]:
            w, g = want[run_name][name], got[run_name][name]
            assert w["rows_sha"] == g["rows_sha"] and w["n"] == g["n"], (run_name, name)
            assert differences(w, g) == [], (run_name, name)
            assert "rebound" not in g["state"], name
    assert want["golden_bars"]["b_targets"]["n"] > 20 and want["synthetic_3000"]["b_targets"]["n"] > 100


class Poison(object):
    """Anything that reads it fails the test."""

    def _boom(self, *a, **k):
        raise AssertionError("a book without the rule key reached the rebound code")
    __getitem__ = __contains__ = __iter__ = __len__ = __bool__ = get = keys = items = _boom


@pytest.mark.parametrize("name", list(shadows.CHALLENGERS))
def test_with_the_key_off_the_new_lines_are_never_reached(name):
    spec = shadows.CHALLENGERS[name]
    cfg = shadows.asset_cfg("BTCUSDT", dict(CFG, **spec["cfg"]))
    inp = random_inputs(n=1200, seed=11)
    plain = run(inp, spec["rule"], cfg=cfg)
    n = len(inp[0]["close"])
    armed = trig_at(n, range(50, n, 7), inp[0]["close"] * 0.004)             # triggers everywhere: nobody may look
    for trig in (Poison(), armed):
        got = run(inp, spec["rule"], trig=trig, cfg=cfg)
        pd.testing.assert_frame_equal(plain["trades"], got["trades"])
        assert np.array_equal(plain["equity"], got["equity"], equal_nan=True) and np.array_equal(plain["held"], got["held"])
        assert json.dumps(plain["state"], sort_keys=True, default=float) == json.dumps(got["state"], sort_keys=True, default=float)
    off = run(inp, dict(spec["rule"], rebound=False), trig=armed, cfg=cfg)   # the key present but off: the same book
    pd.testing.assert_frame_equal(plain["trades"], off["trades"])
    assert list(plain["state"]) == list(off["state"]) and "rebound" not in plain["state"]
    # a state that carries a rebound part (a b_rebound state handed to another rule by mistake) is not read either
    a = run(inp, spec["rule"], hi=600, cfg=cfg)
    st = dict(a["state"], rebound={"on": 1, "bars": 5, "hold": 6, "next": None, "trade": None})
    b0 = run(inp, spec["rule"], lo=600, state=a["state"], cfg=cfg)
    b1 = run(inp, spec["rule"], lo=600, state=st, cfg=cfg)
    pd.testing.assert_frame_equal(b0["trades"], b1["trades"])
    assert "rebound" not in b1["state"]


# =====================================================================================
# 2. no trigger: b_rebound is b_targets, bar for bar
# =====================================================================================
@pytest.mark.parametrize("seed", [3, 11, 17])
def test_with_no_trigger_the_book_is_b_targets_bar_for_bar(seed):
    inp = gap_inputs(n=2500, seed=seed)
    n = len(inp[0]["close"])
    base = run(inp, BASE)
    for trig in (None, trig_at(n, [], 1.0)):                     # no trigger arrays at all / arrays with no trigger
        got = run(inp, RULE, trig=trig)
        pd.testing.assert_frame_equal(base["trades"], got["trades"])
        assert np.array_equal(base["equity"], got["equity"], equal_nan=True) and np.array_equal(base["held"], got["held"])
        st = dict(got["state"])
        assert st.pop("rebound") == shadows._rebound_state(None) and st == base["state"]
    assert len(base["trades"]) > 80
    sa = sb = None                                               # and one bar at a time, as the live step runs it
    for i in range(1, 700):
        a = run(inp, BASE, lo=i, hi=i + 1, state=sa)
        b = run(inp, RULE, trig=None, lo=i, hi=i + 1, state=sb)
        sa, sb = json.loads(json.dumps(a["state"])), json.loads(json.dumps(b["state"]))
        assert dict((k, v) for k, v in sb.items() if k != "rebound") == sa, i
        pd.testing.assert_frame_equal(a["trades"], b["trades"])


def test_a_trigger_without_an_atr_is_no_trigger():
    inp = gap_inputs(n=1200, seed=3)
    n = len(inp[0]["close"])
    base = run(inp, BASE)
    for atr in (np.nan, 0.0, -1.0, np.inf):
        got = run(inp, RULE, trig=trig_at(n, range(100, n, 9), atr))
        pd.testing.assert_frame_equal(base["trades"], got["trades"])
        assert got["state"]["rebound"]["seen"] == 0


# =====================================================================================
# 3. the long is playbook9's trade, bar by bar
# =====================================================================================
def _cases():
    """(seed, k, ATR as a share of price): triggers at bars where b_targets is not long, at several stop sizes."""
    out = []
    for seed in (3, 11, 17, 23):
        inp = gap_inputs(n=1600, seed=seed)
        base = run(inp, BASE)
        ks = [k for k in range(60, 1300, 53) if not_long_at_close(base, k)]
        out += [(seed, k, s) for j, k in enumerate(ks) for s in ((0.002, 0.004, 0.008, 0.02, 0.05)[j % 5],)]
    return out


def test_the_long_is_playbook9s_trade_bar_by_bar():
    seen, cache = set(), {}
    for seed, k, share in _cases():
        inp = cache.setdefault(seed, gap_inputs(n=1600, seed=seed))
        px = inp[0]
        n = len(px["close"])
        atr = float(px["close"][k] * share)
        trig = trig_at(n, [k], atr)
        done, j, path = p9_trade(px, k, atr)
        if done is None:
            continue
        seen.add(done["how"])
        whole = run(inp, RULE, trig=trig)
        mine = [t for t in rows(whole) if t.why_in == "REBOUND"]
        assert len(mine) == 1, (seed, k)
        t = mine[0]
        # the entry, the stop and the targets: playbook9's own numbers, to the last digit
        assert (t.i_in, t.p_in, t.stop0, t.target_1, t.target_2) == (k + 1, done["entry"], done["stop0"], done["t1"], done["t2"])
        assert t.p_in == px["open"][k + 1] and t.side == 1 and t.t_in_ms == (k + 1) * BAR
        # the exit: the same bar, the same kind, the same price; R the same
        assert (t.i_out, t.why_out) == (j, HOW_WORD[done["how"]]), (seed, k, t.why_out, done["how"])
        want_out = done["exit"] if done["how"] in (0, 4) else 0.5 * done["t1"] + 0.5 * done["exit"]
        assert t.p_out == pytest.approx(want_out, rel=1e-12) and t.r_mult == pytest.approx(done["r"], rel=1e-9, abs=1e-12)
        rec = whole["state"]["rebound"]["closed"][-1]
        assert rec["r_h107"] == pytest.approx(done["r"], rel=1e-9, abs=1e-12) and rec["r"] == pytest.approx(t.r_mult)
        assert rec["bars"] == done["bars"] == j - k and rec["why_out"] == t.why_out and rec["entry"] == done["entry"]
        assert rec["r_dist"] == done["r_dist"] and rec["decided_ms"] == (k + 1) * BAR and rec["from"] in ("SHORT", "FLAT")
        # ... and bar by bar while it is open: the stop, Target 1 taken, the share still held, the bar count
        st = run(inp, RULE, trig=trig, hi=k + 1)["state"]
        assert st["pending"] == ["REBOUND", 1, "rebound_A"] and st["rebound"]["next"]["r_dist"] == done["r_dist"]
        for i in range(k + 1, j):
            st = json.loads(json.dumps(run(inp, RULE, trig=trig, lo=i, hi=i + 1, state=st)["state"]))
            stop, t1_taken, q, bars = path[i]
            assert (st["pos"], st["stop"], st["t1_hit"], st["rebound"]["bars"], st["rebound"]["on"]) == (1, stop, t1_taken, bars, 1)
            assert st["qty"] == pytest.approx(st["qty0"] * q, rel=1e-12) and st["idle"] == 0 and st["pending"] is None
            assert (st["entry"], st["t1"], st["t2"], st["stop0"]) == (done["entry"], done["t1"], done["t2"], done["stop0"])
        last = run(inp, RULE, trig=trig, lo=j, hi=j + 1, state=st)
        assert last["state"]["pos"] == 0 and last["state"]["rebound"]["on"] == 0 and last["state"]["idle"] == 0
        ended = rows(last)                                       # (in its entry bar: the short it replaced comes first)
        assert ended[-1].why_in == "REBOUND" and all(x.why_out.endswith("REBOUND") for x in ended[:-1]) and len(ended) <= 2
    assert seen == {0, 1, 2, 3, 4}                               # a stop, T1 then the entry, T1 and T2, T1 then time, time


def test_size_and_fee_are_the_setups_books_and_r_is_recorded_both_ways():
    from engine15 import backtest
    inp = gap_inputs(n=1600, seed=11)
    px = inp[0]
    n = len(px["close"])
    base = run(inp, BASE)
    k = next(k for k in range(200, 900) if not_long_at_close(base, k))
    atr = float(px["close"][k] * 0.004)
    done, _j, _p = p9_trade(px, k, atr)
    # BTC as it runs: 1x, the whole book, 0.10% a side: R is H107's
    cfg = shadows.asset_cfg("BTCUSDT", dict(CFG))
    assert cfg["cost_side"] == p9.FEE == 0.001 and cfg["leverage_cap"] == 1.0 and p9.STOP_ATR == 3.0 and p9.HOLD == 192
    assert CFG["stop_units"] * CFG["barrier_atr"] == p9.STOP_ATR  # the engine's own stop, as when H107 was registered
    got = run(inp, RULE, trig=trig_at(n, [k], atr), cfg=cfg)
    all_rows = rows(got)
    t = [x for x in all_rows if x.why_in == "REBOUND"][0]
    before = [x for x in all_rows if x.i_out <= k + 1 and x.why_in != "REBOUND"]
    eq_then = before[-1].equity if before else shadows.START_EQUITY
    assert t.qty == pytest.approx(eq_then / t.p_in, rel=1e-12)   # the whole book at 1x, compounding as the book does
    rec = got["state"]["rebound"]["closed"][-1]
    assert rec["r"] == pytest.approx(rec["r_h107"], rel=1e-9) and rec["fee_ref"] == p9.FEE
    # another fee and a leverage cap: the book's own numbers, and H107's R kept beside the book's
    cfg2 = dict(cfg, cost_side=0.0004, leverage_cap=5.0)
    got2 = run(inp, RULE, trig=trig_at(n, [k], atr), cfg=cfg2)
    rows2 = rows(got2)
    t2 = [x for x in rows2 if x.why_in == "REBOUND"][0]
    before2 = [x for x in rows2 if x.i_out <= k + 1 and x.why_in != "REBOUND"]
    eq2 = before2[-1].equity if before2 else shadows.START_EQUITY
    lev = backtest.leverage(cfg2, t2.p_in, p9.STOP_ATR * atr)
    assert lev > 1.0 and t2.qty == pytest.approx(eq2 * lev / t2.p_in, rel=1e-12)
    rec2 = got2["state"]["rebound"]["closed"][-1]
    assert rec2["r_h107"] == pytest.approx(done["r"], rel=1e-9) and rec2["r"] > rec2["r_h107"]   # a lower fee: a better R
    assert (t2.p_in, t2.stop0, t2.target_1, t2.i_out, t2.why_out) == (t.p_in, t.stop0, t.target_1, t.i_out, t.why_out)


# =====================================================================================
# 4. the override: from SHORT, from FLAT, while LONG
# =====================================================================================
def _short_cases(inp, base):
    """(k, with a part) for b_targets shorts still open at the close of bar k: plain, and after their Target 1."""
    plain = part = None
    lows = inp[0]["low"]
    for t in rows(base):
        if t.side != -1 or t.i_out - t.i_in < 6:
            continue
        if not t.why_out.startswith("T1") and plain is None:
            plain = (t.i_in + 2, t)
        if t.why_out.startswith("T1") and part is None:
            hit = next(i for i in range(t.i_in, t.i_out + 1) if lows[i] <= t.target_1)
            if hit + 1 < t.i_out:
                part = (hit + 1, t)
    return plain, part


@pytest.mark.parametrize("seed", [3, 11])
def test_from_short_the_short_is_closed_and_the_long_opened_at_the_same_fill(seed):
    inp = gap_inputs(n=3000, seed=seed)
    px = inp[0]
    n = len(px["close"])
    base = run(inp, BASE)
    fee = shadows.asset_cfg("BTCUSDT", dict(CFG))["cost_side"]
    plain, part = _short_cases(inp, base)
    assert plain is not None and part is not None
    for (k, was), with_part in ((plain, False), (part, True)):
        atr = float(px["close"][k] * 0.004)
        got = run(inp, RULE, trig=trig_at(n, [k], atr, b=1))
        all_rows = rows(got)
        j = next(i for i, t in enumerate(all_rows) if t.why_in == "REBOUND")
        short, long_ = all_rows[j - 1], all_rows[j]
        fill = px["open"][k + 1]
        # the short: the very trade b_targets held, closed at the next open
        assert (short.side, short.i_in, short.p_in, short.qty, short.stop0) == (-1, was.i_in, was.p_in, was.qty, was.stop0)
        assert short.i_out == k + 1 and short.why_out == ("T1+REBOUND" if with_part else "REBOUND")
        if with_part:
            half = 0.5 * was.qty
            want = (half * (was.p_in - was.target_1) - fee * half * (was.p_in + was.target_1)
                    + half * (was.p_in - fill) - fee * half * (was.p_in + fill))
            assert short.p_out == pytest.approx(0.5 * was.target_1 + 0.5 * fill, rel=1e-12)
        else:
            want = was.qty * (was.p_in - fill) - fee * was.qty * (was.p_in + fill)
            assert short.p_out == fill
        assert short.pnl_usd == pytest.approx(want, rel=1e-9, abs=1e-9)          # the short's result, booked as a flip's
        assert short.r_mult == pytest.approx(want / (was.qty * abs(was.p_in - was.stop0)), rel=1e-9)
        # the long: the same bar, the same price, sized on the book's equity after the short
        assert (long_.i_in, long_.p_in, long_.t_in_ms) == (k + 1, fill, short.t_out_ms) and long_.side == 1
        assert long_.qty == pytest.approx(short.equity / fill, rel=1e-12)
        assert long_.stop0 == fill - p9.STOP_ATR * atr and long_.target_1 == fill + p9.STOP_ATR * atr
        # everything before the trigger is b_targets, untouched
        pd.testing.assert_frame_equal(got["trades"].iloc[:j - 1].reset_index(drop=True),
                                      base["trades"][base["trades"].i_out <= k].reset_index(drop=True))
        assert np.array_equal(got["equity"][1:k + 1], base["equity"][1:k + 1]) and got["held"][k + 1] == 1
        r = got["state"]["rebound"]
        assert (r["seen"], r["from_short"], r["from_flat"], r["while_long"], r["in_trade"]) == (1, 1, 0, 0, 0)
        assert r["closed"][-1]["from"] == "SHORT" and r["closed"][-1]["rule_b"] is True


def test_from_flat_the_long_opens_at_the_next_open_and_the_setups_entry_of_that_close_is_not_taken():
    inp = gap_inputs(n=3000, seed=3)
    px = inp[0]
    n = len(px["close"])
    base = run(inp, BASE)
    # closes at which b_targets, flat, enters at once (the early entry: booked at the deciding close's price)
    early = [t for t in rows(base) if t.why_in in ("ENTER", "FORCED") and t.p_in == px["close"][t.i_in - 1]
             and base["held"][t.i_in - 1] == 0]
    assert len(early) > 10
    for was in (early[3], next(t for t in early if t.side == -1), next(t for t in early if t.side == 1)):
        k = was.i_in - 1
        atr = float(px["close"][k] * 0.004)
        got = run(inp, RULE, trig=trig_at(n, [k], atr, b=0))
        t = next(x for x in rows(got) if x.i_in == k + 1)
        assert t.why_in == "REBOUND" and t.side == 1 and t.p_in == px["open"][k + 1] != px["close"][k]
        assert t.stop0 == t.p_in - p9.STOP_ATR * atr
        assert not any(x.i_in == k + 1 and x.why_in != "REBOUND" for x in rows(got))   # the Setups entry was not taken
        r = got["state"]["rebound"]
        assert (r["seen"], r["from_short"], r["from_flat"]) == (1, 0, 1) and r["closed"][-1]["rule_b"] is False
        st = run(inp, RULE, trig=trig_at(n, [k], atr), hi=k + 1)["state"]      # at the trigger's close: flat, waiting
        assert st["pos"] == 0 and st["pending"] == ["REBOUND", 1, "rebound_A"] and st["idle"] == 0
        assert shadows.asset_view(dict(st))["next_open"] == "REBOUND -> LONG"
    # and with no odds at all (the Setups rule never trades): the book holds only the override's long
    quiet = list(inp)
    quiet[1] = np.full((n, 3), np.nan)
    got = run(tuple(quiet), RULE, trig=trig_at(n, [500], float(px["close"][500] * 0.004)))
    assert [t.why_in for t in rows(got)] == ["REBOUND"] and rows(got)[0].i_in == 501
    assert got["state"]["rebound"]["closed"][-1]["from"] == "FLAT" and not got["held"][:501].any()


def test_while_the_book_is_long_a_trigger_is_counted_and_nothing_changes():
    inp = gap_inputs(n=3000, seed=3)
    n = len(inp[0]["close"])
    base = run(inp, BASE)
    longs = [t for t in rows(base) if t.side == 1 and t.i_out - t.i_in >= 6]
    ks = [t.i_in + 2 for t in longs[:6]]
    got = run(inp, RULE, trig=trig_at(n, ks, inp[0]["close"] * 0.004))
    pd.testing.assert_frame_equal(base["trades"], got["trades"])
    assert np.array_equal(base["equity"], got["equity"], equal_nan=True) and np.array_equal(base["held"], got["held"])
    r = got["state"]["rebound"]
    assert (r["seen"], r["while_long"], r["from_short"], r["from_flat"], r["in_trade"]) == (6, 6, 0, 0, 0)
    assert r["closed"] == [] and "REBOUND" not in set(got["trades"].why_in)
    # the Setups rule decided those closes as always: a flip out of the long at such a close stands
    flips = [t for t in rows(base) if t.side == 1 and t.why_out.endswith("FLIP")]
    k = flips[0].i_out - 1                                       # the close that decided the flip; the book is long
    got = run(inp, RULE, trig=trig_at(n, [k], inp[0]["close"] * 0.004))
    pd.testing.assert_frame_equal(base["trades"], got["trades"])
    assert got["state"]["rebound"]["while_long"] == 1


# =====================================================================================
# 5. while it lives the Setups rule is not consulted; it resumes after; a second trigger is counted
# =====================================================================================
def _long_lived(seed=3, n=3000):
    """A trigger whose stop and targets are out of reach: the long lives its 192 bars."""
    inp = gap_inputs(n=n, seed=seed)
    base = run(inp, BASE)
    k = next(k for k in range(400, 900) if not_long_at_close(base, k))
    return inp, base, k, inp[0]["close"] * 0.2


def test_while_the_long_lives_the_setups_rule_is_not_consulted_and_then_it_resumes():
    inp, base, k, atr = _long_lived()
    px = inp[0]
    n = len(px["close"])
    trig = trig_at(n, [k], atr)
    got = run(inp, RULE, trig=trig)
    j = k + p9.HOLD                                              # the 192nd bar: k+1 is the first
    t = next(x for x in rows(got) if x.why_in == "REBOUND")
    assert (t.i_in, t.i_out, t.why_out, t.p_out) == (k + 1, j, "TIME", px["close"][j])
    assert t.t_out_ms == j * BAR and (got["held"][k + 1:j + 1] == 1).all() and got["held"][j + 1] == 0
    inside = [x for x in rows(got) if k + 1 <= x.i_in <= j and x.why_in != "REBOUND"]
    assert inside == []                                          # no flip, no step-aside, no forced entry in 48 hours
    there = [x for x in rows(base) if k + 1 <= x.i_in <= j]
    assert len(there) >= 4 and any(x.side == -1 for x in there)  # ... where b_targets traded, shorts among them
    mid = run(inp, RULE, trig=trig, hi=k + 100)["state"]
    assert (mid["pos"], mid["idle"], mid["pending"], mid["why_in"]) == (1, 0, None, "REBOUND")
    assert mid["rebound"]["on"] == 1 and mid["rebound"]["bars"] == 99
    # when it ends: flat, the idle count at zero, no Setups decision at that close (b_targets would enter at once)
    end = run(inp, RULE, trig=trig, hi=j + 1)["state"]
    assert (end["pos"], end["idle"], end["pending"], end["rebound"]["on"]) == (0, 0, None, 0)
    assert not any(x.i_in == j + 1 for x in rows(got))
    # from the next close on it is the Setups rule again: the same book as b_targets started from that state
    plain = dict((key, v) for key, v in end.items() if key != "rebound")
    a = run(inp, RULE, trig=trig, lo=j + 1, state=end)
    b = run(inp, BASE, lo=j + 1, state=plain)
    pd.testing.assert_frame_equal(a["trades"], b["trades"])
    assert np.array_equal(a["equity"][j + 1:], b["equity"][j + 1:]) and len(a["trades"]) > 50
    nxt = rows(a)[0]
    assert nxt.i_in >= j + 2 and nxt.why_in in ("ENTER", "FORCED")
    if nxt.why_in == "FORCED":                                   # the mandate counted from zero after the long ended
        assert nxt.i_in >= j + 2 + CFG["idle_max"]
    st = json.loads(json.dumps(end))
    idles = []
    for i in range(j + 1, nxt.i_in):
        st = json.loads(json.dumps(run(inp, RULE, trig=trig, lo=i, hi=i + 1, state=st)["state"]))
        idles.append(st["idle"])
    assert idles[:-1] == list(range(1, len(idles)))             # 1, 2, ... from the first close after it ended


def test_a_second_trigger_during_the_trade_is_counted_not_taken_and_one_at_its_last_close_is_taken():
    inp, base, k, atr = _long_lived()
    px = inp[0]
    n = len(px["close"])
    j = k + p9.HOLD
    got = run(inp, RULE, trig=trig_at(n, [k, k + 10, k + 100], atr))
    mine = [x for x in rows(got) if x.why_in == "REBOUND"]
    assert len(mine) == 1 and (mine[0].i_in, mine[0].i_out, mine[0].why_out) == (k + 1, j, "TIME")   # not prolonged
    r = got["state"]["rebound"]
    assert (r["seen"], r["in_trade"], r["from_short"] + r["from_flat"], r["while_long"]) == (3, 2, 1, 0)
    # at the close of the very bar in which it ended the book is flat: that trigger is taken (as playbook9 does)
    got = run(inp, RULE, trig=trig_at(n, [k, j], atr))
    mine = [x for x in rows(got) if x.why_in == "REBOUND"]
    assert [(x.i_in, x.i_out) for x in mine] == [(k + 1, j), (j + 1, j + p9.HOLD)]
    assert mine[1].p_in == px["open"][j + 1] and [c["from"] for c in got["state"]["rebound"]["closed"]][1] == "FLAT"
    assert got["state"]["rebound"]["in_trade"] == 0
    # only the last REBOUND_KEPT longs stay in the state
    many = trig_at(n, range(100, n - 10, 3), px["close"] * 0.0005)                # tiny stops: they end fast
    r = run(inp, RULE, trig=many)["state"]["rebound"]
    assert r["from_short"] + r["from_flat"] > shadows.REBOUND_KEPT >= len(r["closed"]) == 50


# =====================================================================================
# 6. a restart mid-trade, and no look-ahead
# =====================================================================================
@pytest.mark.parametrize("share", [0.004, 0.2])
def test_a_restart_at_any_bar_gives_the_whole_run(share):
    inp = gap_inputs(n=1800, seed=11)
    px = inp[0]
    n = len(px["close"])
    base = run(inp, BASE)
    ks = [k for k in range(300, 1500, 211) if not_long_at_close(base, k)]
    trig = trig_at(n, ks, px["close"] * share, b=1)
    whole = run(inp, RULE, trig=trig)
    assert sum(1 for t in rows(whole) if t.why_in == "REBOUND") >= 3
    cols = [c for c in shadows.TRADE_COLS if c != "i_in"]
    k0 = ks[0]
    cuts = [k0, k0 + 1, k0 + 2, k0 + 3, k0 + 50, k0 + p9.HOLD, k0 + p9.HOLD + 1] + list(range(350, 1700, 97))
    for cut in cuts:
        a = run(inp, RULE, trig=trig, hi=cut)
        saved = json.loads(json.dumps(a["state"]))               # through the file, as the live step does
        b = run(inp, RULE, trig=trig, lo=cut, state=saved)
        joined = pd.concat([a["trades"], b["trades"]], ignore_index=True)
        pd.testing.assert_frame_equal(whole["trades"][cols], joined[cols])
        assert np.array_equal(whole["equity"][cut:], b["equity"][cut:]) and np.array_equal(whole["held"][cut:], b["held"][cut:])
        assert json.dumps(b["state"], sort_keys=True) == json.dumps(dict(whole["state"], i_in=b["state"]["i_in"]), sort_keys=True)
    mid = run(inp, RULE, trig=trig, hi=k0 + 3)["state"]          # a restart with the long open: it is all in the state
    if mid["pos"] == 1 and mid["why_in"] == "REBOUND":
        assert mid["rebound"]["on"] == 1 and mid["rebound"]["trade"]["entry"] == mid["entry"] and mid["rebound"]["hold"] == 192
        v = dict(shadows.asset_view(mid), **rb.view_extra(mid))
        assert v["status"] == "LONG" and v["rebound_long"] is True and v["opened_by"] == "REBOUND"
        assert v["target_1"] is not None and v["rebound_time_exit_utc"] == rb._utc((k0 + 1 + p9.HOLD) * BAR)


def test_the_book_reads_nothing_after_the_bar_it_decides_at():
    inp = gap_inputs(n=1500, seed=11)
    n = len(inp[0]["close"])
    base = run(inp, BASE)
    ks = [k for k in range(200, 1400, 61) if not_long_at_close(base, k)]
    atr = inp[0]["close"] * 0.004
    whole = run(inp, RULE, trig=trig_at(n, ks, atr))
    assert sum(1 for t in rows(whole) if t.why_in == "REBOUND") >= 5
    for k in (410, 777, 1203):
        rng = np.random.RandomState(k)
        px, odds, unit, shock, tide, bias, guard, aux = [copy.deepcopy(x) for x in inp]
        f = slice(k + 1, None)
        m = n - k - 1
        for key in px:
            px[key][f] = px[key][f] * rng.uniform(0.9, 1.1, m)
        odds[f] = rng.dirichlet(np.ones(3), size=m)
        unit[f], tide[f], bias[f], shock[f], guard[f] = unit[f] * 3, -tide[f], -bias[f], ~shock[f], ~guard[f]
        aux["targets"].iloc[k + 1:] = 9.0
        trig = trig_at(n, ks, atr)
        trig["A"][f] = ~trig["A"][f]                             # the future's triggers and ATR are scrambled too
        trig["atr"][f] = trig["atr"][f] * rng.uniform(0.2, 5.0, m)
        cut = run((px, odds, unit, shock, tide, bias, guard, aux), RULE, trig=trig)
        assert np.array_equal(whole["equity"][1:k + 1], cut["equity"][1:k + 1]) and np.array_equal(whole["held"][:k + 1], cut["held"][:k + 1])
        w, c = whole["trades"], cut["trades"]
        pd.testing.assert_frame_equal(w[w.i_out <= k].reset_index(drop=True), c[c.i_out <= k].reset_index(drop=True))
        a = run(inp, RULE, trig=trig_at(n, ks, atr), hi=k + 1)["state"]
        b = run((px, odds, unit, shock, tide, bias, guard, aux), RULE, trig=trig, hi=k + 1)["state"]
        assert a == b


# =====================================================================================
# 7. the trigger: playbook9's readings on the book's own bars, the tail, nothing from the future
# =====================================================================================
def test_the_trigger_is_playbook9s_rule_a_on_the_books_own_bars():
    prep = capit_prep(odds="none", assets=("BTCUSDT",), days=100, seed=5)
    px, n = prep["px"]["BTCUSDT"], len(prep["times"])
    t_ms = np.asarray(prep["times"].as_unit("ms").asi8, dtype="int64")
    fx = p9.features(frame(prep, "BTCUSDT"), None)
    lo = 80 * 96
    hits = np.where(fx["A"])[0]
    assert len(hits) >= 2 and (hits < lo).any()
    whole = rb.trigger(px, t_ms, 0, n)                           # from the first bar: the very frame, the very numbers
    assert np.array_equal(whole["A"], fx["A"]) and np.array_equal(whole["atr"], fx["atr1h"], equal_nan=True)
    assert (whole["stop_atr"], whole["hold"], whole["fee"]) == (p9.STOP_ATR, p9.HOLD, p9.FEE) == (3.0, 192, 0.001)
    # a live step: the last 45 days plus the new bars; only lo .. hi-1 is filled
    prep2 = capit_prep(odds="none", assets=("BTCUSDT",), days=100, seed=5)
    px2 = dict((k, v.copy()) for k, v in prep2["px"]["BTCUSDT"].items())
    k = 90 * 96                                                  # a third capitulation, inside the live window
    r = np.diff(np.log(px2["close"]), prepend=np.log(px2["close"][0]))
    r[k:k + 72] -= 0.22 / 72
    r[k + 72:k + 80] += 0.008
    c = px2["close"][0] * np.exp(np.cumsum(r))
    scale = c / px2["close"]
    px2 = dict((key, v * scale) for key, v in px2.items())
    fx2 = p9.features(pd.DataFrame(px2, index=prep["times"]), None)
    late = np.where(fx2["A"][lo:])[0] + lo
    assert len(late) >= 1
    tail = rb.trigger(px2, t_ms, lo, n)
    assert np.array_equal(tail["A"][lo:], fx2["A"][lo:]) and not tail["A"][:lo].any() and np.isnan(tail["atr"][:lo]).all()
    assert np.allclose(tail["atr"][lo:], fx2["atr1h"][lo:], rtol=1e-9, atol=0.0)   # Wilder's average has forgotten its start
    # one bar at a time, as the live step asks: the same flags, and the bars after hi are never read
    for i in list(late) + [int(late[0]) - 1, int(late[0]) + 1, lo, n - 1]:
        one = rb.trigger(px2, t_ms, i, i + 1)
        assert bool(one["A"][i]) == bool(fx2["A"][i]) and one["A"].sum() == int(fx2["A"][i])
        assert one["atr"][i] == pytest.approx(fx2["atr1h"][i], rel=1e-9)
        junk = dict((key, np.concatenate([v[:i + 1], v[i + 1:] * 0.5])) for key, v in px2.items())
        again = rb.trigger(junk, t_ms, i, i + 1)                 # everything after bar i halved: nothing changes
        assert np.array_equal(one["A"], again["A"]) and np.array_equal(one["atr"], again["atr"], equal_nan=True)
    # bars that are not numbers are left out, as a bar file without them
    holes = dict((key, v.copy()) for key, v in px2.items())
    holes["close"][lo - 500] = np.nan
    assert np.array_equal(rb.trigger(holes, t_ms, lo, n)["A"][lo:], fx2["A"][lo:])
    # nothing to do, nothing done
    assert not rb.trigger(px2, t_ms, n, n)["A"].any()


def test_rule_bs_flag_is_recorded_from_the_funding_file_and_only_read_at_a_trigger(monkeypatch):
    prep = capit_prep(odds="none", assets=("BTCUSDT",))
    px, n = prep["px"]["BTCUSDT"], len(prep["times"])
    t_ms = np.asarray(prep["times"].as_unit("ms").asi8, dtype="int64")
    lo = 4328
    calls = []
    monkeypatch.setattr(rb, "funding_of", lambda a: calls.append(a) or pd.Series(dtype=float))
    quiet = rb.trigger(px, t_ms, lo, lo + 30, asset="BTCUSDT")   # no trigger in these bars: the file is not opened
    assert not quiet["A"].any() and calls == []
    got = rb.trigger(px, t_ms, lo, n, asset="BTCUSDT")
    hits = np.where(got["A"])[0]
    assert len(hits) >= 2 and calls == ["BTCUSDT"] and (got["B"][hits] == -1).all()      # no funding reading: unknown
    stamps = pd.date_range(prep["times"][0], prep["times"][-1], freq="8h")
    neg = rb.trigger(px, t_ms, lo, n, funding=pd.Series(-0.0001, index=stamps))
    pos = rb.trigger(px, t_ms, lo, n, funding=pd.Series(0.0001, index=stamps))
    stale = rb.trigger(px, t_ms, lo, n, funding=pd.Series(-0.0001, index=stamps[:3]))
    assert (neg["B"][hits] == 1).all() and (pos["B"][hits] == 0).all() and (stale["B"][hits] == -1).all()
    for other in (neg, pos, stale):                              # rule A's trigger does not depend on the funding
        assert np.array_equal(other["A"], got["A"]) and np.array_equal(other["atr"], got["atr"], equal_nan=True)
    monkeypatch.setattr(rb, "funding_of", lambda a: 1 / 0)       # a funding file that cannot be read: still rule A
    broken = rb.trigger(px, t_ms, lo, n, asset="BTCUSDT")
    assert np.array_equal(broken["A"], got["A"]) and (broken["B"] == -1).all()


# =====================================================================================
# 8. the forward book (shadows.advance): BTC and ETH only, guarded, forward only
# =====================================================================================
LO = 4328                                                        # 45 days and 8 bars in: the trigger's frame starts at bar 0


def test_the_forward_book_takes_playbook9s_trades_one_for_one(monkeypatch):
    """No odds, so the Setups rule never trades: the book holds exactly the override's longs, and they are the trades
    playbook9's own book makes on the same bars from the same start."""
    monkeypatch.setattr(rb, "funding_of", lambda a: pd.Series(dtype=float))
    prep = capit_prep(odds="none")
    n = len(prep["times"])
    sst, said = fresh(), []
    view, closed = shadows.advance(prep, "crypto", list(rb.ASSETS), n, sst, start_lo=LO, log=said.append)
    total = 0
    for a in rb.ASSETS:
        open_ms = np.asarray(prep["times"].as_unit("ms").asi8, dtype="int64")
        ref = p9.replay(a, frame(prep, a), None, int(open_ms[LO]))
        want = [t for t in ref["closed"] if t["book"] == "p9_rebound_a"]
        got = rows({"trades": closed[(rb.NAME, a)]})
        assert len(want) == len(got) >= 2, a
        total += len(got)
        for w, g in zip(want, got):
            assert (g.why_in, g.side, g.p_in, g.stop0, g.target_1, g.target_2) == ("REBOUND", 1, w["entry"], w["stop0"], w["t1"], w["t2"])
            assert g.t_in_ms == w["entry_open_ms"] and g.t_out_ms + BAR == w["exit_close_ms"] and g.why_out == HOW_WORD[w["how"]]
            assert g.r_mult == pytest.approx(w["r"], rel=1e-9, abs=1e-12)
        st = sst["books"][rb.NAME][a]
        r = st["rebound"]
        assert r["from_flat"] == len(got) and r["from_short"] == 0 and r["while_long"] == 0
        assert r["in_trade"] == ref["skipped"]["p9_rebound_a"][a] and r["seen"] == len(got) + r["in_trade"]
        assert [c["decided_ms"] for c in r["closed"]] == [w["decided_ms"] for w in want]
        assert st[rb.META]["last_ms"] == int(open_ms[n - 1]) and st[rb.META]["no_trigger_steps"] == 0
        assert st["stats"]["n"] == len(got)
        ls = sst["late_starts"][rb.NAME][a]
        assert ls["ms"] == int(open_ms[LO]) and ls["main_eq"] == ls["setups_eq"] == shadows.START_EQUITY
        assert ls["own_eq"] == st["equity_marked"] and ls["ref_utc"] == rb._utc(int(open_ms[n - 1]) + BAR)   # one step here
        v = view["books"][rb.NAME]["assets"][a]
        assert v["label"] == "NOT passed, paper only" and v["rebound_triggers"]["seen"] == r["seen"]
        assert v["started_utc"] == ls["utc"] and v["trades"] == len(got)
    assert "NOT passed" in view["books"][rb.NAME]["title"] and total >= 4
    assert any(rb.NAME in m and "taken from FLAT" in m for m in said) and any("closed (" in m for m in said)
    board = shadows.scoreboard({"crypto": view})
    row = [x for x in board["rows"] if x["book"] == rb.NAME][0]
    assert row["assets"] == 2 and row["label"] == rb.LABEL and row["trades"] == total and "since_utc" in row


def test_steps_of_any_size_give_the_one_long_step_and_a_restart_mid_trade_resumes(tmp_path, monkeypatch):
    monkeypatch.setattr(rb, "funding_of", lambda a: pd.Series(dtype=float))
    prep = capit_prep(odds="random")
    n = len(prep["times"])
    one = fresh()
    _v, c_one = shadows.advance(prep, "crypto", list(rb.ASSETS), n, one, start_lo=LO)
    took = [one["books"][rb.NAME][a]["rebound"] for a in rb.ASSETS]
    assert sum(t["from_short"] + t["from_flat"] for t in took) >= 1 and all(t["seen"] >= 2 for t in took)
    assert sum(t["while_long"] for t in took) >= 1               # both kinds of trigger are in this run
    first = min(c["decided_ms"] for a in rb.ASSETS for c in one["books"][rb.NAME][a]["rebound"]["closed"])
    k = int(np.searchsorted(np.asarray(prep["times"].as_unit("ms").asi8, dtype="int64"), first))    # the fill bar
    path = str(tmp_path / "shadow_state.json")
    two = fresh()
    stops = sorted(set(list(range(LO + 37, n, 211)) + [k - 1, k, k + 1, k + 2, k + 3, k + 40, n]))
    parts = []
    start_lo = LO
    for hi in stops:
        _v, c = shadows.advance(prep, "crypto", list(rb.ASSETS), hi, two, start_lo=start_lo)
        start_lo = None
        parts.append(c)
        shadows.save_state(two, path)                            # every step through the file: a restart each time
        two = shadows.load_state(path)
        if hi == k + 2:
            mid = two["books"][rb.NAME]
            assert any(mid[a]["rebound"]["on"] == 1 and mid[a]["why_in"] == "REBOUND" for a in rb.ASSETS)
    cols = [c for c in shadows.TRADE_COLS if c != "i_in"]
    note = [c for a in rb.ASSETS for c in two["books"][rb.NAME][a]["rebound"]["closed"] if c["decided_ms"] == first][0]
    assert note["setups_eq"] is not None and isinstance(note["setups_pct"], float)       # what b_targets did meanwhile
    assert note["setups_exact"] is False                         # ... (it closed in a step of many bars: marked so)
    for a in rb.ASSETS:
        x, y = one["books"][rb.NAME][a], two["books"][rb.NAME][a]
        assert differences(without_the_side_notes(x), without_the_side_notes(y), rtol=1e-9) == [], a
        joined = pd.concat([p[(rb.NAME, a)] for p in parts if (rb.NAME, a) in p], ignore_index=True)
        w = c_one[(rb.NAME, a)].reset_index(drop=True)
        assert list(w.why_in) == list(joined.why_in) and list(w.why_out) == list(joined.why_out)
        assert list(w.t_in_ms) == list(joined.t_in_ms) and list(w.t_out_ms) == list(joined.t_out_ms)
        assert np.allclose(w.pnl_usd.values, joined.pnl_usd.values, rtol=1e-9) and len(w) > 20
        assert ("REBOUND" in set(w.why_in)) == bool(x["rebound"]["closed"]) and len(joined[cols]) == len(w)
        for name in ("b_targets", "main"):                       # and the books beside it, as ever
            assert one["books"][name][a] == two["books"][name][a]


def test_the_other_six_markets_have_no_book_and_no_other_book_changes_when_this_one_runs(monkeypatch):
    monkeypatch.setattr(rb, "funding_of", lambda a: pd.Series(dtype=float))
    prep = capit_prep(odds="random", assets=("BTCUSDT", "XAUUSD"))
    n = len(prep["times"])
    with_book, without = fresh(), fresh()
    v1, c1 = shadows.advance(prep, "mixed", ["BTCUSDT", "XAUUSD"], 5000, with_book, start_lo=LO)
    v1, c1b = shadows.advance(prep, "mixed", ["BTCUSDT", "XAUUSD"], n, with_book)
    saved = shadows.MINDS.pop(rb.NAME)
    try:
        v2, c2 = shadows.advance(prep, "mixed", ["BTCUSDT", "XAUUSD"], 5000, without, start_lo=LO)
        v2, c2b = shadows.advance(prep, "mixed", ["BTCUSDT", "XAUUSD"], n, without)
    finally:
        shadows.MINDS[rb.NAME] = saved
    assert set(with_book["books"][rb.NAME]) == {"BTCUSDT"} and rb.NAME not in without["books"]
    assert set(with_book["late_starts"][rb.NAME]) == {"BTCUSDT"} and set(v1["books"][rb.NAME]["assets"]) == {"BTCUSDT"}
    assert with_book["books"][rb.NAME]["BTCUSDT"]["rebound"]["seen"] >= 2                # the override did act here
    assert not any(k == (rb.NAME, "XAUUSD") for k in list(c1) + list(c1b))
    for name in list(shadows.CHALLENGERS) + list(shadows.FOLLOWERS):                     # b_targets, the vault's book, too
        assert json.dumps(with_book["books"].get(name), sort_keys=True) == json.dumps(without["books"].get(name), sort_keys=True), name
        assert json.dumps(v1["books"].get(name), sort_keys=True) == json.dumps(v2["books"].get(name), sort_keys=True)
    for got, want in ((c1, c2), (c1b, c2b)):
        assert set(k for k in got if k[0] != rb.NAME) == set(want)
        for k in want:
            pd.testing.assert_frame_equal(got[k], want[k])
    assert with_book["groups"] == without["groups"]
    b1, b2 = shadows.scoreboard({"mixed": v1}), shadows.scoreboard({"mixed": v2})
    assert [r for r in b1["rows"] if r["book"] != rb.NAME] == b2["rows"]
    # a group with none of the two coins: the module does nothing at all
    metals = capit_prep(odds="random", assets=("XAUUSD", "XAGUSD"), days=10)
    sst = fresh()
    view, closed = shadows.advance(metals, "metals", ["XAUUSD", "XAGUSD"], 960, sst, start_lo=300)
    assert rb.NAME not in sst["books"] and rb.NAME not in view["books"] and rb.NAME not in (sst.get("late_starts") or {})


def test_with_no_trigger_the_forward_book_is_the_setups_books_twin():
    prep = fake_prep()                                           # 700 bars: under 30 days, so rule A cannot fire
    sst = fresh()
    _v, closed = shadows.advance(prep, "crypto", ["BTCUSDT"], 420, sst, start_lo=100)
    _v, closed2 = shadows.advance(prep, "crypto", ["BTCUSDT"], 700, sst)
    mine = dict(sst["books"][rb.NAME]["BTCUSDT"])
    assert mine.pop("rebound") == shadows._rebound_state(None) and mine.pop(rb.META)["no_trigger_steps"] == 0
    assert mine == sst["books"]["b_targets"]["BTCUSDT"] and mine["stats"]["n"] > 10
    for c in (closed, closed2):
        pd.testing.assert_frame_equal(c[(rb.NAME, "BTCUSDT")], c[("b_targets", "BTCUSDT")])
    alone = shadows.run_challenger("b_targets", prep, "BTCUSDT", 100, 700)               # shadows' own way to run b_targets
    assert mine["eq"] == alone["state"]["eq"] and mine["stats"] == alone["state"]["stats"]


def test_a_trigger_that_cannot_be_computed_leaves_the_setups_rule_and_one_log_line(monkeypatch):
    prep = fake_prep()
    ref, sst, said = fresh(), fresh(), []
    shadows.advance(prep, "crypto", ["BTCUSDT"], 700, ref, start_lo=100)

    def boom(*_a, **_k):
        raise RuntimeError("planted")
    monkeypatch.setattr(rb, "trigger", boom)
    view, closed = shadows.advance(prep, "crypto", ["BTCUSDT"], 420, sst, start_lo=100, log=said.append)
    lines = [m for m in said if "could not be computed" in m]
    assert len(lines) == 1 and "planted" in lines[0] and "runs as the Setups rule" in lines[0]
    monkeypatch.undo()
    import engine15
    monkeypatch.setitem(sys.modules, "engine15.playbook9", None)                          # the module does not import
    monkeypatch.delattr(engine15, "playbook9")
    said2 = []
    shadows.advance(prep, "crypto", ["BTCUSDT"], 700, sst, log=said2.append)
    assert len([m for m in said2 if "could not be computed" in m]) == 1
    mine = dict(sst["books"][rb.NAME]["BTCUSDT"])
    assert mine.pop(rb.META)["no_trigger_steps"] == 2 and mine.pop("rebound") == shadows._rebound_state(None)
    assert mine == sst["books"]["b_targets"]["BTCUSDT"]          # that step ran as the Setups rule, exactly
    for name in list(shadows.CHALLENGERS) + list(shadows.FOLLOWERS):
        assert sst["books"].get(name) == ref["books"].get(name), name                    # and no step was stopped


def test_an_open_rebound_long_is_still_managed_when_the_trigger_cannot_be_computed(monkeypatch):
    monkeypatch.setattr(rb, "funding_of", lambda a: pd.Series(dtype=float))
    prep = capit_prep(odds="none", assets=("BTCUSDT",))
    n = len(prep["times"])
    ref = fresh()
    shadows.advance(prep, "crypto", ["BTCUSDT"], n, ref, start_lo=LO)
    first = ref["books"][rb.NAME]["BTCUSDT"]["rebound"]["closed"][0]
    k = int(np.searchsorted(np.asarray(prep["times"].as_unit("ms").asi8, dtype="int64"), first["decided_ms"]))
    sst = fresh()
    shadows.advance(prep, "crypto", ["BTCUSDT"], k + 2, sst, start_lo=LO)                 # the long is open
    assert sst["books"][rb.NAME]["BTCUSDT"]["rebound"]["on"] == 1
    monkeypatch.setattr(rb, "trigger", lambda *a, **k_: 1 / 0)
    said = []
    _v, closed = shadows.advance(prep, "crypto", ["BTCUSDT"], n, sst, log=said.append)
    got = rows({"trades": closed[(rb.NAME, "BTCUSDT")]})
    assert len(got) == 1 and got[0].why_in == "REBOUND"          # its own stop, targets and time exit ended it
    rec = sst["books"][rb.NAME]["BTCUSDT"]["rebound"]["closed"]
    assert len(rec) == 1 and rec[0]["exit"] == first["exit"] and rec[0]["why_out"] == first["why_out"]
    assert any("could not be computed" in m for m in said)       # ... and the later triggers were not seen


def test_a_failing_step_is_one_log_line_no_other_book_is_touched_and_the_next_step_catches_up(monkeypatch):
    monkeypatch.setattr(rb, "funding_of", lambda a: pd.Series(dtype=float))
    prep = capit_prep(odds="random")
    n = len(prep["times"])
    ref, sst, said = fresh(), fresh(), []
    for hi, lo in ((5000, LO), (5001, None), (5002, None), (n, None)):
        shadows.advance(prep, "crypto", list(rb.ASSETS), hi, ref, start_lo=lo)
    shadows.advance(prep, "crypto", list(rb.ASSETS), 5000, sst, start_lo=LO)
    before = copy.deepcopy(sst["books"][rb.NAME])
    real = shadows.run

    def broken(*a, **k):
        if (k.get("rule") or {}).get("rebound"):
            raise RuntimeError("planted")
        return real(*a, **k)
    monkeypatch.setattr(shadows, "run", broken)
    shadows.advance(prep, "crypto", list(rb.ASSETS), 5001, sst, log=said.append)
    shadows.advance(prep, "crypto", list(rb.ASSETS), 5002, sst, log=said.append)
    assert len([m for m in said if "%s failed on" % rb.NAME in m and "planted" in m]) == 4      # two coins, two steps
    assert sst["books"][rb.NAME] == before                       # not advanced, not damaged
    monkeypatch.undo()
    monkeypatch.setattr(rb, "funding_of", lambda a: pd.Series(dtype=float))
    shadows.advance(prep, "crypto", list(rb.ASSETS), n, sst)
    for name in list(shadows.CHALLENGERS) + list(shadows.FOLLOWERS):
        assert sst["books"].get(name) == ref["books"].get(name), name
    for a in rb.ASSETS:                                          # the two bars it missed were walked at the next step
        x, y = ref["books"][rb.NAME][a], sst["books"][rb.NAME][a]
        assert differences(without_the_side_notes(x), without_the_side_notes(y), rtol=1e-9) == [], a
    # the module itself failing to load: shadows still loads and every other book runs (the registration is guarded)
    with open(shadows.__file__, encoding="utf-8") as fh:
        src = fh.read()
    block = src[src.index("    from . import rebound_book"):]
    assert block.index("except Exception:") < block.index("TARGET_COLS")


def test_a_state_file_written_by_main_loads_and_every_book_goes_on_as_on_main(tmp_path):
    """The live file holds the vault's open setup under b_targets. A file written by main's code (kept in the fixture)
    is loaded by this code and stepped on: every book that was in it ends where main's own code took it, nothing
    that was in it is re-keyed, and the new book starts flat at the first new bar."""
    with open(FIXTURE, encoding="utf-8") as fh:
        fx = json.load(fh)["state_file"]
    assert rb.NAME not in fx["at_420"]["books"] and "b_targets" in fx["at_420"]["books"]
    path = str(tmp_path / "shadow_state.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(fx["at_420"], fh, indent=1)
    prep = fake_prep()
    sst = shadows.load_state(path)
    assert differences(sst, fx["at_420"]) == []
    _v, closed = shadows.advance(prep, "crypto", ["BTCUSDT"], 700, sst)
    now = json.loads(json.dumps(sst, default=float))
    assert set(fx["at_700"]["books"]) | {rb.NAME} == set(now["books"])
    for name, want in fx["at_700"]["books"].items():             # b_targets first of all
        assert differences(want, now["books"][name]) == [], name
    assert differences(fx["at_700"]["groups"], now["groups"]) == []
    for key, want in fx["closed_420_700"].items():
        name, a = key.split("|")
        got = tr_digest(closed[(name, a)], skip=("i_in",), full=name in FULL)
        assert want["rows_sha"] == got["rows_sha"] and differences(want, got) == [], key
    assert "b_targets|BTCUSDT" in fx["closed_420_700"] and fx["closed_420_700"]["b_targets|BTCUSDT"]["n"] > 5
    late = dict(now.get("late_starts") or {})
    ls = late.pop(rb.NAME)["BTCUSDT"]
    assert late == (fx["at_700"].get("late_starts") or {})
    t420 = shadows._ms(prep["times"][420])
    assert ls["ms"] == t420 and ls["main_eq"] == fx["at_420"]["books"]["main"]["BTCUSDT"]["equity_marked"]
    mine = now["books"][rb.NAME]["BTCUSDT"]
    first = closed[(rb.NAME, "BTCUSDT")].iloc[0]
    assert first.t_in_ms >= t420 and mine["stats"]["n"] == len(closed[(rb.NAME, "BTCUSDT")]) > 3    # flat at bar 420
    # through the live step's own door (load, advance, save) the file keeps every old book and gains one
    shadows.step(prep, "crypto", ["BTCUSDT"], 700, path=path, out_dir=str(tmp_path), log=lambda *_: None)
    again = shadows.load_state(path)
    assert differences(again["books"]["b_targets"], fx["at_700"]["books"]["b_targets"]) == []
    assert os.path.exists(str(tmp_path / ("shadow_trades_%s_BTCUSDT.csv" % rb.NAME)))
    # a file from before the book existed that already holds a b_rebound-free late_starts and odd keys is left as is
    assert again["version"] == fx["at_420"]["version"]


# =====================================================================================
# 9. the scoreboard row and the registered comparison
# =====================================================================================
def _sst_for_compare(own=(10300.0, 10100.0), setups=(10050.0, 10150.0)):
    st = {"version": 1, "groups": {}, "books": {rb.NAME: {}, "b_targets": {}}, "late_starts": {rb.NAME: {}}}
    for a, o, s in zip(rb.ASSETS, own, setups):
        st["books"][rb.NAME][a] = {"pos": 0, "eq": o, "equity_marked": o, "rebound": dict(
            shadows._rebound_state(None), seen=3, from_short=1, from_flat=1, while_long=1,
            closed=[{"r": 1.0, "pct": 2.0, "pnl_usd": 200.0, "rule_b": True, "setups_pct": -1.0},
                    {"r": -1.0, "pct": -3.0, "pnl_usd": -300.0, "rule_b": False, "setups_pct": None}])}
        st["books"]["b_targets"][a] = {"pos": 0, "eq": s, "equity_marked": s}
        st["late_starts"][rb.NAME][a] = {"ms": 0, "utc": "2026-11-25 00:15", "ref_utc": "2026-11-25 00:15",
                                         "main_eq": 10000.0, "own_eq": 10000.0, "setups_eq": 10020.0}
    return st


def test_the_comparison_with_the_setups_book_and_the_overrides_own_record(tmp_path):
    sst = _sst_for_compare()
    early = rb.compare(sst, 29)
    assert early["read"].startswith("no read before 30") and "difference_pts" not in early and "sentence" not in early
    out = rb.compare(sst, 30)
    # own: +300 +100 = +2.00% of 20,000; the Setups book from its own start marks: +30 +130 = +0.80%
    assert (out["return_pct"], out["setups_book_return_pct"], out["difference_pts"], out["read"]) == (2.0, 0.8, 1.2, "ahead of")
    assert out["markets"] == 2 and out["since_utc"] == "2026-11-25 00:15" and "NOT passed" in out["sentence"]
    assert rb.compare(_sst_for_compare(own=(10100.0, 10100.0)), 40)["read"] == "level with"
    assert rb.compare(_sst_for_compare(own=(9900.0, 10000.0)), 40)["read"] == "behind"
    gone = _sst_for_compare()
    gone["late_starts"] = {}
    assert rb.compare(gone, 40)["read"].startswith("no read: the books' state")
    rec = rb.record(sst)
    assert (rec["seen"], rec["from_short"], rec["from_flat"], rec["while_long"], rec["in_trade"]) == (6, 2, 2, 2, 0)
    assert rec["rebound_longs_closed"] == 4 and rec["mean_r"] == 0.0 and rec["net_usd"] == -200.0 and rec["rule_b_true"] == 2
    assert rec["against_setups_same_bars"]["trades"] == 2 and rec["against_setups_same_bars"]["rebound_long_mean_pct"] == 2.0
    assert "no verdict" in rec["note"]
    # reports.scoreboard's row: nothing before the book exists, then the label and both blocks
    path = str(tmp_path / "s.json")
    assert rb.scoreboard_extra(0, state_path=path) is None
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"version": 1, "groups": {}, "books": {"b_targets": {}}}, fh)
    assert rb.scoreboard_extra(0, state_path=path) is None
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(sst, fh)
    row = rb.scoreboard_extra(0, state_path=path)
    assert row["title"] == rb.SCOREBOARD_TITLE and row["passed"] is False and row["paper_only"] is True
    assert row["hypothesis"] == "H117" and row["vs_setups_book"]["closed_trades"] == 0 and row["override"]["seen"] == 6
    json.dumps(row)


def test_the_scoreboard_shows_the_book_with_its_label(tmp_path, monkeypatch):
    from engine15 import reports
    live = tmp_path / "out" / "live"
    os.makedirs(str(live))
    pd.DataFrame({"pnl_usd": [10.0, -5.0], "time_in": ["2026-11-25 00:15", "2026-11-25 03:15"], "side": [1, -1],
                  "time_out": ["2026-11-25 01:00", "2026-11-25 04:00"]}).to_csv(
        str(live / ("shadow_trades_%s_BTCUSDT.csv" % rb.NAME)), index=False)
    state = str(tmp_path / "shadow_state.json")
    with open(state, "w", encoding="utf-8") as fh:
        json.dump(_sst_for_compare(), fh)
    monkeypatch.setattr(reports, "ROOT", str(tmp_path))
    monkeypatch.setattr(reports, "SCOREBOARD_JSON", str(live / "scoreboard.json"))
    monkeypatch.setattr(shadows, "STATE_PATH", state)
    out = reports.scoreboard(log=lambda *_: None)
    row = [r for r in out["rows"] if r["book"] == rb.NAME][0]
    assert row["title"] == rb.SCOREBOARD_TITLE and row["kind"] == "shadow" and row["label"] == rb.LABEL
    assert row["trades"] == 2 and row["passed"] is False and row["vs_setups_book"]["read"].startswith("no read before 30")
    assert row["override"]["from_short"] == 2
