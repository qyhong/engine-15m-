# -*- coding: utf-8 -*-
"""playbook9 (H115): H107's capitulation-rebound long, rules A and B, as two forward paper books, and their Telegram
cards. PAPER ONLY, NOT passed.

1. Labels and registration: ids, "NOT passed" on every title, the frozen constants are H107's, nothing on the money path.
2. The trade, bar by bar, against hand-worked results and the research script's own bar-by-bar walk.
3. Parity with research/h107_capitulation_rebound.py on the real BTC and ETH bars and funding (skipped when the files
   are not there): flags, entries, stops, targets, exits and R, trade for trade.
4. No look-ahead: a decision at a bar's close is the same on data cut at that bar.
5. Forward only: nothing before the start (or before REGISTERED) is ever written into the record.
6. Funding: missing or stale means rule B does not fire, and one line says so.
7. State: atomic, a restart mid-trade resumes exactly, a missing or unreadable file starts flat and says so.
8. It never stops a step.
9. Rows, the page block, the scoreboard and the allocator.
10. The Telegram cards: text, once per trigger, the owner's chat only, a failure never matters.
11. The vault feed's inputs do not change.

Every file a test writes is under pytest's tmp_path; the real data folder is only read.
"""
import ast
import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine15 import book_alloc as ba  # noqa: E402
from engine15 import data  # noqa: E402
from engine15 import playbook9 as p9  # noqa: E402
from engine15 import reports  # noqa: E402
from engine15 import telegram_notify as tn  # noqa: E402

BTC, ETH = "BTCUSDT", "ETHUSDT"
T0 = pd.Timestamp("2027-01-04 00:00", tz="UTC")          # synthetic bars: after REGISTERED
K = 4513                                                  # the one bar at whose close the synthetic rule A fires
QUIET = lambda *_a, **_k: None                            # noqa: E731


# ---------------------------------------------------------------- synthetic bars with one capitulation rebound
def synth(after=0.0004, seed=7, t0=T0, days=44, fall=0.16, fall_bars=288, pop=0.012, tail_days=4, base=100.0):
    """44 quiet days, a 16% fall over three days to a fresh 30-day low, a rebound of 1.2% in three bars, then a
    drift of `after` a bar: 0.0004 -> Target 1 and 2 after 47 bars; -0.0005 -> stopped after 37 bars with a second
    signal on the way; 0.00012 -> Target 1 then the 48-hour exit."""
    rng = np.random.RandomState(seed)
    r = list(rng.normal(0, 0.0006, days * 96))
    r += list(np.log(1 - fall) / fall_bars + rng.normal(0, 0.0012, fall_bars))
    r += [pop / 3.0] * 3
    r += list(after + rng.normal(0, 0.0008, tail_days * 96))
    c = base * np.exp(np.cumsum(r))
    o = np.concatenate([[base], c[:-1]])
    wig = np.abs(rng.normal(0, 0.0004, len(c)))
    idx = pd.date_range(t0, periods=len(c), freq="15min", name="open_time")
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) * (1 + wig), "low": np.minimum(o, c) * (1 - wig), "close": c,
                         "volume": 1.0, "taker_buy": 0.5}, index=idx)


def funding(df, rate=-0.0002, until=None):
    """A rate set every 8 hours (00:00, 08:00, 16:00 UTC), as data.load_funding gives it."""
    return pd.Series(rate, index=pd.date_range(df.index[0].floor("8h"), until if until is not None else df.index[-1],
                                               freq="8h"))


def close_ms(df, i):
    return int(data.to_ms(df.index[i:i + 1])[0]) + p9.BAR_MS


def run_steps(df, fund, path, first, last, every=1, log=QUIET, lag_ms=20000):
    """The live step, called after bar `first` closed and then after every `every` bars up to bar `last`: each call
    sees only the bars closed by its own clock."""
    rows = []
    for i in list(range(first, last, every)) + [last]:
        rows = p9.step(bars={BTC: df.iloc[:i + 1]}, now_ms=close_ms(df, i) + lag_ms, funding={BTC: fund},
                       state_path=path, log=log)
    return rows


def state_of(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def same(a, b, skip=("seen_ms", "late", "state_note")):
    """Equal, floats to 1e-9 relative (a reading from a 45-day tail and from the whole file differ in the last bit)."""
    if isinstance(a, dict) and isinstance(b, dict):
        ka, kb = set(a) - set(skip), set(b) - set(skip)
        return ka == kb and all(same(a[k], b[k], skip) for k in ka)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(same(x, y, skip) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return a is not None and b is not None and abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))
    return a == b


@pytest.fixture(scope="module")
def up():
    return synth(0.0004)


@pytest.fixture(scope="module")
def down():
    return synth(-0.0005)


# ---------------------------------------------------------------- 1. labels and registration
def test_books_titles_and_registration():
    assert set(p9.BOOKS) == {"p9_rebound_a", "p9_rebound_b"} and p9.RULES == {"p9_rebound_a": "A", "p9_rebound_b": "B"}
    for book, f in p9.BOOKS.items():
        assert "NOT passed" in f["title"] and "NOT passed" in f["scoreboard_title"]
        assert f["scoreboard_title"].startswith("Strategy")       # the bot's ranking tells strategy rows by this word
        assert f["assets"] == (BTC, ETH) and f["registered"] == p9.REGISTERED == "2026-11-24 12:50"
        assert "H115" in f["hypothesis"]
    assert "playbook9" in reports.PLAYBOOK_MODULES
    assert reports._scoreboard_titles()["p9_rebound_a"] == p9.BOOKS["p9_rebound_a"]["scoreboard_title"]
    import importlib
    seen = {}
    for name in reports.PLAYBOOK_MODULES:                         # the ids are free: no other module has them
        for b in importlib.import_module("engine15." + name).BOOKS:
            assert b not in seen, (b, name, seen.get(b))
            seen[b] = name
    for text in (p9.NOT_PASSED, p9.HISTORY, p9.PASS_RULE, p9.rule_text("p9_rebound_a"), p9.rule_text("p9_rebound_b")):
        low = text.lower()
        assert "proven" not in low and "edge" not in low
    assert "flat over 123 trades" in p9.HISTORY and "32 trades" in p9.HISTORY and "too few" in p9.HISTORY
    assert "never by itself reaches the vault" in p9.PASS_RULE and "stays NOT passed" in p9.PASS_RULE
    with open(os.path.join(ROOT, "research", "HYPOTHESES.md"), encoding="utf-8") as fh:
        reg = fh.read()
    assert "## H115." in reg and reg.index("## H115.") > reg.index("## H114.")


def test_the_frozen_constants_are_h107s():
    assert (p9.LOOK, p9.LOW_DAYS, p9.DROP_DAYS, p9.DROP, p9.BOUNCE_ATR, p9.HOLD) == (16, 30, 7, 0.10, 2.0, 192)
    assert p9.STOP_ATR == 3.0 and p9.FEE == 0.0010 and p9.STAKE == 10000.0 and p9.ASSETS == (BTC, ETH)
    assert p9.FUND_MAX_AGE_MS == 9 * 3600000
    h = pytest.importorskip("research.h107_capitulation_rebound")
    assert h.REG == {"look": p9.LOOK, "low_days": p9.LOW_DAYS, "drop_days": p9.DROP_DAYS, "drop": p9.DROP,
                     "bounce_atr": p9.BOUNCE_ATR, "hold": p9.HOLD}
    assert h.STOP_ATR == p9.STOP_ATR and h.FEE == p9.FEE and tuple(h.COINS) == p9.ASSETS


def test_the_module_imports_nothing_from_research_or_the_money_path_and_no_money_file_knows_it():
    with open(p9.__file__, encoding="utf-8") as fh:
        src = fh.read()
    mods = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            mods |= set(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            mods |= set("%s%s.%s" % ("." * node.level, node.module or "", a.name) for a in node.names)
    assert mods == {"copy", "io", "json", "math", "os", "time", "numpy", "pandas", "..data", "..indicators",
                    ".config.DATA_DIR", ".config.OUT_DIR"}
    assert "requests" not in src and "http" not in src and "socket" not in src     # no network: it sends nothing
    with open(os.path.join(ROOT, "tools", "money_files.txt"), encoding="utf-8") as fh:
        money = [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
    assert "engine15/vault_feed.py" in money and "engine15/playbook9.py" not in money
    for rel in money:
        if rel.endswith(".py"):
            with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
                body = fh.read()
            assert "playbook9" not in body and "capit_long" not in body and "p9_rebound" not in body, rel


# ---------------------------------------------------------------- 2. the trade, bar by bar
def _trade(P=100.0, R=3.0):
    return p9._open_trade({"r_dist": R, "decided_ms": 0, "book": "p9_rebound_a", "asset": BTC, "rule": "A"}, P, 0)


def _walk(bars, hold=None, monkeypatch=None):
    if hold is not None:
        monkeypatch.setattr(p9, "HOLD", hold)
    tr, done = _trade(), None
    for j, (o, h, l, c) in enumerate(bars):
        assert done is None
        done = p9._walk_bar(tr, o, h, l, c, (j + 1) * p9.BAR_MS)
    return tr, done


def _research_r(bars):
    """The research script's bar-by-bar walk of the same bars (None when the script is not there)."""
    try:
        from research import h107_capitulation_rebound as h
    except Exception:
        return None
    o, hi, lo, c = (np.array([100.0] + [b[i] for b in bars]) for i in range(4))
    fx = {"o": o, "h": hi, "l": lo, "c": c, "atr1h": np.full(len(o), 1.0)}
    return h.walk_loop(fx, 0, len(bars))


@pytest.mark.parametrize("bars, how, r, exit_px", [
    # stopped: the stop is 97; out at the stop
    ([(100, 101, 98, 99), (99, 99.5, 96.5, 97.2)], 0, (-3.0 - 0.001 * (100 + 97)) / 3.0, 97.0),
    # a gap through the stop: out at the open
    ([(100, 100.5, 99, 99.5), (95, 96, 94, 95.5)], 0, (-5.0 - 0.001 * (100 + 95)) / 3.0, 95.0),
    # stop and Target 1 in one bar: the stop is looked at first
    ([(100, 104, 96, 103)], 0, (-3.0 - 0.001 * (100 + 97)) / 3.0, 97.0),
    # Target 1 (the low under the entry in that bar does not stop it), then stopped at the entry the next bar
    ([(100, 103.5, 99.5, 103), (103, 103.2, 99.9, 100.5)], 1, (1.5 - 0.001 * (100 + 0.5 * 103 + 0.5 * 100)) / 3.0, 100.0),
    # after Target 1 a gap under the entry: the rest out at the open
    ([(100, 103.5, 99.5, 103), (99, 99.5, 98, 99.2)], 1, (1.5 - 0.5 - 0.001 * (100 + 0.5 * 103 + 0.5 * 99)) / 3.0, 99.0),
    # Target 1 and Target 2 in the same bar
    ([(100, 106.5, 99, 106)], 2, (1.5 + 3.0 - 0.001 * (100 + 0.5 * 103 + 0.5 * 106)) / 3.0, 106.0),
    # Target 1, then Target 2 two bars later
    ([(100, 103.1, 100, 103), (103, 105, 102, 104), (104, 106.2, 103, 106)], 2,
     (1.5 + 3.0 - 0.001 * (100 + 0.5 * 103 + 0.5 * 106)) / 3.0, 106.0),
])
def test_each_exit_by_hand_and_against_the_research_walk(bars, how, r, exit_px):
    tr, done = _walk(bars)
    assert done is not None and done["how"] == how and done["why_out"] == p9.HOW[how]
    assert done["exit"] == exit_px and abs(done["r"] - r) < 1e-12
    assert abs(done["pnl_usd"] - p9.STAKE * done["pct"]) < 1e-9 and abs(done["pct"] - r * 3.0 / 100.0) < 1e-12
    assert abs(done["fees_usd"] - p9.STAKE * tr["fees"] / 100.0) < 1e-9
    ref = _research_r(bars)
    if ref is not None:
        assert abs(ref - done["r"]) < 1e-12


def test_the_time_exit_is_the_close_of_the_last_bar_with_or_without_target_1(monkeypatch):
    flat = [(100, 101, 99, 100.5), (100.5, 101, 99.5, 100.2), (100.2, 102, 99, 101.5)]
    tr, done = _walk(flat, hold=3, monkeypatch=monkeypatch)
    assert done["how"] == 4 and done["exit"] == 101.5 and abs(done["r"] - (1.5 - 0.001 * (100 + 101.5)) / 3.0) < 1e-12
    assert abs(_research_r(flat) - done["r"]) < 1e-12 if _research_r(flat) is not None else True
    t1 = [(100, 103.2, 99.5, 102), (102, 103, 100.5, 101), (101, 102, 100.2, 101.8)]
    tr, done = _walk(t1, hold=3, monkeypatch=monkeypatch)
    assert done["how"] == 3 and done["t1_taken"] and done["exit"] == 101.8
    assert abs(done["r"] - (1.5 + 0.9 - 0.001 * (100 + 0.5 * 103 + 0.5 * 101.8)) / 3.0) < 1e-12
    assert abs(_research_r(t1) - done["r"]) < 1e-12 if _research_r(t1) is not None else True
    tr, done = _walk(t1[:2], hold=3, monkeypatch=monkeypatch)        # still open after two bars: marked, not closed
    assert done is None and tr["bars"] == 2 and tr["stop"] == 100.0 and tr["mark"] == 101.0
    assert abs(tr["r_mark"] - (1.5 + 0.5 - 0.001 * (100 + 0.5 * 103 + 0.5 * 101)) / 3.0) < 1e-12


# ---------------------------------------------------------------- 3. parity with the research script on the real files
def _real(coin):
    h = pytest.importorskip("research.h107_capitulation_rebound")
    ddir = os.path.join(ROOT, "data")
    for suf in ("_15m.csv", "_funding.csv"):
        if not os.path.exists(os.path.join(ddir, coin.lower() + suf)):
            pytest.skip("no %s%s in data/: the parity check needs the real bars and funding" % (coin.lower(), suf))
    df, fund = h.load(coin, ddir)
    fx = h.features(df, fund)
    k0 = int(fx["t"].searchsorted(pd.Timestamp(h.START, tz="UTC")))
    return {"h": h, "df": df, "fund": fund, "fx": fx, "k0": k0, "k1": len(df) - 1, "open_ms": data.to_ms(df.index)}


@pytest.fixture(scope="module", params=p9.ASSETS)
def real(request):
    return dict(_real(request.param), coin=request.param)


def test_parity_flags_equal_the_research_script_on_every_bar(real):
    mine = p9.features(real["df"], real["fund"])
    for key in ("A", "B", "trig"):
        assert np.array_equal(mine[key], real["fx"][key]), key
    assert np.allclose(mine["atr1h"], real["fx"]["atr1h"], rtol=0, atol=0, equal_nan=True)
    assert int(mine["A"].sum()) >= 100 and int(mine["B"].sum()) >= 10
    known = np.isfinite(mine["fund"])                            # the staleness guard never bound in this history:
    assert not (mine["A"] & known & ~mine["fund_fresh"]).any()   # it changes nothing here, it only protects the live read
    assert not (known & ~mine["fund_fresh"]).any()               # ... at any bar: no rate was ever older than 9 hours


def test_parity_trades_equal_the_research_script_trade_for_trade(real):
    h, fx, k0, k1, coin = real["h"], real["fx"], real["k0"], real["k1"], real["coin"]
    start_ms = int(real["open_ms"][k0])                           # the close of bar k0 - 1: bars from k0 on can decide
    st = p9.replay(coin, real["df"], real["fund"], start_ms)
    total = 0
    for book, rule in p9.RULES.items():
        ks, w, skipped = h.trades_of(fx, rule, k0, k1, p9.HOLD)
        mine = [t for t in st["closed"] if t["book"] == book]
        mk = [int(np.searchsorted(real["open_ms"], t["k_open_ms"])) for t in mine]
        keep = [i for i, k in enumerate(mk) if k + p9.HOLD <= k1]  # the script drops a trade that cannot run 48 hours
        assert [mk[i] for i in keep] == [int(k) for k in ks], (coin, rule)
        assert len(ks) >= 10
        for j, i in enumerate(keep):
            t = mine[i]
            R = h.STOP_ATR * fx["atr1h"][ks[j]]                    # the script's own R, T1 = P + R, T2 = P + 2R
            assert t["entry"] == w["entry"][j] and t["stop0"] == w["stop"][j] and t["r_dist"] == R, (coin, rule, j)
            assert t["t1"] == w["entry"][j] + R and t["t2"] == w["entry"][j] + 2 * R
            assert t["how"] == int(w["how"][j]) and abs(t["r"] - w["r"][j]) < 1e-9 and abs(t["pct"] - w["pct"][j]) < 1e-12
            x = int(np.searchsorted(real["open_ms"], t["exit_close_ms"] - p9.BAR_MS))
            assert x == int(w["xbar"][j]), (coin, rule, j)
            assert abs(h.walk_loop(fx, int(ks[j]), p9.HOLD) - t["r"]) < 1e-9
        assert st["skipped"][book][coin] >= skipped                # every signal the script skipped was counted here
        total += len(ks)
    assert total > 0


def test_parity_the_21_nov_2026_event_is_the_one_h107_reported(real):
    coin = real["coin"]
    dec = int(pd.Timestamp("2026-11-21 06:45", tz="UTC").value // 10**6)
    if int(real["open_ms"][-1]) + p9.BAR_MS < dec + p9.HOLD * p9.BAR_MS:
        pytest.skip("the bars on file end before 23 Nov 2026 06:45 UTC")
    st = p9.replay(coin, real["df"].iloc[-96 * 80:], real["fund"], dec - 10 * 86400000)
    ev = [t for t in st["closed"] if t["decided_ms"] == dec]
    assert sorted(t["rule"] for t in ev) == ["A", "B"]
    want_close, want_r = {BTC: (57194.94, 1.31), ETH: (1613.76, 1.16)}[coin]      # H107's event read, published 23 Nov
    for t in ev:
        assert t["close"] == want_close and round(t["r"], 2) == want_r and t["why_out"] == "T1+TIME"
        assert t["exit_close_ms"] == dec + p9.HOLD * p9.BAR_MS and t["funding"] < 0 and t["funding_fresh"]


def test_no_lookahead_on_the_real_bars_a_45_day_tail_cut_at_the_bar_gives_the_same_decision(real):
    df, fund, fx = real["df"], real["fund"], real["fx"]
    full = p9.features(df, fund)
    rng = np.random.RandomState(20261124)
    bars = sorted(set(np.flatnonzero(fx["A"]).tolist()) | set(rng.randint(real["k0"], real["k1"] + 1, 40).tolist()))
    want = p9.TAIL_BARS + 8
    fms = data.to_ms(fund.index)
    for k in bars:
        if k < want:
            continue
        cut = df.iloc[k + 1 - want:k + 1]                          # what the live step reads when bar k is the newest
        fcut = fund[fms <= int(real["open_ms"][k]) + p9.BAR_MS]    # nothing set after that bar's close
        g = p9.features(cut, fcut)
        for key in ("A", "B", "trig", "fund_fresh"):
            assert bool(g[key][-1]) == bool(full[key][k]), (k, key)
        assert np.isclose(g["atr1h"][-1], full["atr1h"][k], rtol=1e-9, atol=0, equal_nan=True), k
        assert (g["fund"][-1] == full["fund"][k]) or (np.isnan(g["fund"][-1]) and np.isnan(full["fund"][k]))


def test_the_tail_reader_gives_what_data_load_gives(real, tmp_path):
    coin, df = real["coin"], real["df"]
    got = p9.tail_bars(coin, 700)
    assert got.index.equals(df.index[-700:]) and list(got.columns) == data.COLS
    assert np.array_equal(got.values, df.iloc[-700:].values, equal_nan=True)
    small = str(tmp_path / "x_15m.csv")
    data.save("x", df.iloc[-50:], path=small)
    assert p9.tail_bars("x", 500, path=small).index.equals(df.index[-50:])      # a file shorter than what was asked


# ---------------------------------------------------------------- 4. no look-ahead (synthetic; runs without the real files)
def test_the_synthetic_market_fires_once_and_only_at_the_rebound(up, down):
    for df in (up, down):
        fx = p9.features(df, funding(df))
        assert K in np.flatnonzero(fx["A"]).tolist() and bool(fx["B"][K]) and not fx["A"][:K].any()
        assert fx["is_low"][K] and fx["drop"][K] and fx["bounce"][K] and not fx["trig"][K - 1]


def test_no_lookahead_a_decision_is_the_same_on_data_cut_at_its_bar(up):
    fund = funding(up)
    full = p9.features(up, fund)
    for k in (K - 2, K - 1, K, K + 1, K + 30):
        cut = up.iloc[:k + 1]
        g = p9.features(cut, fund[fund.index <= cut.index[-1] + pd.Timedelta(minutes=15)])
        for key in ("A", "B", "trig", "is_low", "drop", "bounce", "fund_fresh"):
            assert bool(g[key][-1]) == bool(full[key][k]), (k, key)
        for key in ("atr1h", "low16", "lowN", "cref", "fund"):
            assert g[key][-1] == full[key][k], (k, key)
    # the bars after K changed beyond recognition: nothing decided up to K moves
    wild = up.copy()
    wild.iloc[K + 1:, :4] = wild.iloc[K + 1:, :4] * 3.0
    start = close_ms(up, 4400)
    a = p9.replay(BTC, up.iloc[:K + 1], fund, start)
    b = p9.replay(BTC, wild, fund, start)
    fill = ("entry", "stop", "t1", "t2")                           # added to the alert one bar later, at the fill
    assert same(a["alerts"], b["alerts"], skip=fill) and len(a["alerts"]) == 1 and not set(fill) & set(a["alerts"][0])
    assert a["alerts"][0]["decided_ms"] == close_ms(up, K)
    for book in p9.RULES:
        assert a["books"][book][BTC]["pending"] is not None
        assert b["closed"] and all(t["k_open_ms"] == a["books"][book][BTC]["pending"]["k_open_ms"]
                                   for t in b["closed"] if t["book"] == book and t["decided_ms"] == close_ms(up, K))


def test_funding_set_after_the_close_is_never_read(up):
    k_close = pd.Timestamp(close_ms(up, K), unit="ms", tz="UTC")
    late = pd.Series([0.0003, -0.0009], index=[k_close - pd.Timedelta(hours=2), k_close + pd.Timedelta(milliseconds=1)])
    fx = p9.features(up, late)
    assert fx["fund"][K] == 0.0003 and not fx["B"][K] and fx["A"][K]          # the negative rate came 1 ms too late
    assert fx["fund"][K + 1] == -0.0009
    on_time = pd.Series([0.0003, -0.0009], index=[k_close - pd.Timedelta(hours=2), k_close])
    assert p9.features(up, on_time)["B"][K]                                    # set AT the close: known, as in H107


# ---------------------------------------------------------------- 5. forward only
def test_the_step_takes_the_trigger_fills_at_the_next_open_and_equals_the_replay(up, tmp_path):
    path = str(tmp_path / "state" / "capit_long_state.json")
    fund, said = funding(up), []
    rows = run_steps(up, fund, path, 4400, K, log=said.append)
    st = state_of(path)
    assert st["started_ms"] == close_ms(up, 4400) and st["started_utc"] == "2027-02-18 20:15"
    assert [r["status"] for r in rows] == ["WAITING", "WAITING"] and all(r["entry"] is None for r in rows)
    assert len(st["alerts"]) == 1 and st["alerts"][0]["rules"] == ["A", "B"] and "entry" not in st["alerts"][0]
    assert sum("rules A and B fired" in s for s in said) == 1 and sum("no state file" in s for s in said) == 1
    rows = run_steps(up, fund, path, K + 1, K + 1)
    st = state_of(path)
    assert [r["status"] for r in rows] == ["OPEN", "OPEN"]
    for r in rows:
        assert r["entry"] == round(float(up["open"].iloc[K + 1]), 6) and r["side"] == 1
        assert r["stop"] < r["entry"] < r["target_1"] < r["target_2"] and r["setup_utc"] == "2027-02-20 00:30"
        assert abs((r["target_1"] - r["entry"]) - (r["entry"] - r["stop"])) < 1e-6
        assert abs((r["entry"] - r["stop"]) - 3.0 * st["alerts"][0]["atr1h"]) < 1e-6
    assert st["alerts"][0]["entry"] == float(up["open"].iloc[K + 1])           # the alert now holds the paper fill
    rows = run_steps(up, fund, path, K + 2, K + 60)
    st = state_of(path)
    assert [(r["status"], r["why_out"]) for r in rows] == [("CLOSED", "T1+T2")] * 2
    ref = p9.replay(BTC, up.iloc[:K + 61], fund, close_ms(up, 4400))
    assert same(st["closed"], ref["closed"]) and same(st["alerts"], ref["alerts"]) and same(st["books"], ref["books"])
    assert all(t["late"] is False and t["seen_ms"] == t["decided_ms"] + 20000 for t in st["closed"])
    assert os.listdir(os.path.dirname(path)) == ["capit_long_state.json"]      # one file, nothing left beside it


def test_a_trigger_before_the_start_is_never_written_into_the_record(up, tmp_path):
    path = str(tmp_path / "capit_long_state.json")
    fund = funding(up)
    rows = run_steps(up, fund, path, K + 3, K + 3)                 # the book is deployed three bars AFTER the signal
    st = state_of(path)
    assert rows == [] and st["started_ms"] == close_ms(up, K + 3) and st["alerts"] == [] and st["closed"] == []
    rows = run_steps(up, fund, path, K + 4, len(up) - 1, every=11)
    st = state_of(path)
    assert rows == [] and st["closed"] == [] and st["alerts"] == []
    assert all(s[BTC] == {"pending": None, "open": None} for s in st["books"].values())
    assert st["last_open_ms"][BTC] == int(data.to_ms(up.index[-1:])[0])
    assert p9.replay(BTC, up, fund, close_ms(up, 4400))["closed"]  # ... although the rule itself traded there


def test_the_start_is_the_first_steps_clock_so_a_bar_file_that_is_behind_brings_nothing_in(up, tmp_path):
    path = str(tmp_path / "capit_long_state.json")
    fund = funding(up)
    # the first step runs just after bar K + 1 closed, but the bar file still ends three bars before the signal
    assert p9.step(bars={BTC: up.iloc[:K - 2]}, now_ms=close_ms(up, K + 1) + 20000, funding={BTC: fund}, state_path=path,
                   log=QUIET) == []
    assert state_of(path)["started_ms"] == close_ms(up, K + 1) and state_of(path)["last_open_ms"] == {}
    rows = run_steps(up, fund, path, K + 2, K + 60, every=3)       # the missing bars arrive: they closed before the start
    st = state_of(path)
    assert rows == [] and st["alerts"] == [] and st["closed"] == []
    assert st["last_open_ms"][BTC] == int(data.to_ms(up.index[K + 60:K + 61])[0])


def test_nothing_before_registered_counts_even_with_no_state(tmp_path):
    old = synth(0.0004, t0=pd.Timestamp("2026-07-06 00:00", tz="UTC"))          # the same market, before REGISTERED
    path = str(tmp_path / "capit_long_state.json")
    rows = run_steps(old, funding(old), path, 4400, K + 60, every=5)
    st = state_of(path)
    assert rows == [] and st["started_ms"] == p9.reg_ms() and st["alerts"] == [] and st["closed"] == []
    assert p9.features(old, funding(old))["A"][K]                  # the signal was there; it was history, so not taken


def test_a_gap_is_caught_up_bar_by_bar_and_a_trigger_found_late_is_marked(down, tmp_path):
    fund = funding(down)
    one, gap = str(tmp_path / "one.json"), str(tmp_path / "gap.json")
    run_steps(down, fund, one, 4400, K + 45)
    run_steps(down, fund, gap, 4400, K - 6)                        # ... then the engine is down for 51 bars
    said = []
    rows = run_steps(down, fund, gap, K + 45, K + 45, log=said.append)
    a, b = state_of(one), state_of(gap)
    assert same(a["closed"], b["closed"]) and same(a["alerts"], b["alerts"]) and same(a["skipped"], b["skipped"])
    assert [t["why_out"] for t in a["closed"]] == ["STOP", "STOP"] and a["closed"][0]["bars"] == 37
    assert a["skipped"]["p9_rebound_a"][BTC] == 1                  # a second signal while the trade was open: counted
    assert all(t["late"] is False for t in a["closed"]) and all(t["late"] is True for t in b["closed"])
    assert b["alerts"][0]["late"] is True and any("(found late)" in s for s in said)
    assert sum("fired again" in s and "counted, not taken" in s for s in said) >= 1


# ---------------------------------------------------------------- 6. funding: missing or stale
def test_the_staleness_limit_is_nine_hours_to_the_millisecond(up):
    c = close_ms(up, K)
    for age, fresh in ((9 * 3600000, True), (9 * 3600000 + 1, False), (8 * 3600000, True), (17 * 3600000, False)):
        f = pd.Series([-0.0002], index=[pd.Timestamp(c - age, unit="ms", tz="UTC")])
        fx = p9.features(up, f)
        assert bool(fx["fund_fresh"][K]) is fresh and bool(fx["B"][K]) is fresh and fx["A"][K]
        assert p9.features(up, f, max_age_ms=None)["B"][K]         # without the guard the old rate would have fired


@pytest.mark.parametrize("kind, why, word", [("stale", "funding_stale", "is stale"),
                                             ("missing", "funding_missing", "no funding reading"),
                                             ("positive", "funding_not_negative", None)])
def test_rule_b_does_not_fire_without_a_fresh_negative_rate_and_says_so_once(up, tmp_path, kind, why, word):
    c = pd.Timestamp(close_ms(up, K), unit="ms", tz="UTC")
    fund = {"stale": funding(up, -0.0002, until=c - pd.Timedelta(hours=20)), "missing": None,
            "positive": funding(up, 0.0001)}[kind]
    path, said = str(tmp_path / "capit_long_state.json"), []
    run_steps(up, fund, path, 4400, K + 60, every=4, log=said.append)
    st = state_of(path)
    assert [t["rule"] for t in st["closed"]] == ["A"] and st["books"]["p9_rebound_b"][BTC] == {"pending": None, "open": None}
    assert st["alerts"][0]["rules"] == ["A"] and st["alerts"][0]["not_taken"] == {"B": why}
    lines = [s for s in said if "rule B does not fire" in s]
    assert len(lines) == (0 if word is None else 1)
    if word:
        assert word in lines[0] and "rule A fired" in lines[0]
    if kind == "stale":
        assert st["alerts"][0]["funding"] == -0.0002 and st["alerts"][0]["funding_fresh"] is False
        assert "limit 9 h" in lines[0]
    if kind == "missing":
        assert st["alerts"][0]["funding"] is None and st["alerts"][0]["funding_set_ms"] is None


# ---------------------------------------------------------------- 7. the state
def test_a_restart_mid_trade_resumes_exactly(up, tmp_path):
    fund = funding(up)
    one, two = str(tmp_path / "one" / "s.json"), str(tmp_path / "two" / "s.json")
    run_steps(up, fund, one, 4400, K + 60)
    run_steps(up, fund, two, 4400, K + 20)                         # stopped with both trades open ...
    mid = state_of(two)
    assert all(mid["books"][b][BTC]["open"] is not None for b in p9.RULES) and mid["closed"] == []
    moved = str(tmp_path / "three" / "s.json")
    os.makedirs(os.path.dirname(moved))
    shutil.copy(two, moved)
    p9.LAST_RUN.clear()                                            # ... and nothing in memory survives the restart
    rows = run_steps(up, fund, moved, K + 21, K + 60)
    with open(one, "rb") as a, open(moved, "rb") as b:
        assert a.read() == b.read()                                # byte for byte the state of the run that never stopped
    assert [r["why_out"] for r in rows] == ["T1+T2", "T1+T2"]


def test_a_step_with_no_new_bar_changes_nothing(up, tmp_path):
    path = str(tmp_path / "s.json")
    fund = funding(up)
    run_steps(up, fund, path, 4400, K + 5)
    with open(path, "rb") as fh:
        before = fh.read()
    stamp = os.path.getmtime(path)
    r1 = p9.step(bars={BTC: up.iloc[:K + 6]}, now_ms=close_ms(up, K + 5) + 500000, funding={BTC: fund}, state_path=path,
                 log=QUIET)
    with open(path, "rb") as fh:
        assert fh.read() == before
    assert os.path.getmtime(path) == stamp and [r["status"] for r in r1] == ["OPEN", "OPEN"]


@pytest.mark.parametrize("content", [b"{not json", b"", b"[1, 2]", b'{"version": 1}', b'{"version": 99, "started_ms": 1}'])
def test_an_unreadable_state_file_starts_flat_is_kept_aside_and_is_logged(up, tmp_path, content):
    path, said = str(tmp_path / "capit_long_state.json"), []
    fund = funding(up)
    run_steps(up, fund, path, 4400, K + 5)                         # two open trades on file ...
    with open(path, "wb") as fh:
        fh.write(content)                                          # ... and the file is lost to garbage
    rows = run_steps(up, fund, path, K + 6, K + 6, log=said.append)
    st = state_of(path)
    assert rows == [] and st["closed"] == [] and st["alerts"] == [] and st["started_ms"] == close_ms(up, K + 6)
    assert sum("cannot be read" in s and "starts flat" in s for s in said) == 1
    kept = [f for f in os.listdir(str(tmp_path)) if ".bad-" in f]
    assert len(kept) == 1
    with open(str(tmp_path / kept[0]), "rb") as fh:
        assert fh.read() == content                                # the unreadable file is still there for a person
    assert "corrupt" in st["state_note"]
    rows = run_steps(up, fund, path, K + 7, K + 60, every=9, log=said.append)
    assert rows == [] and sum("cannot be read" in s for s in said) == 1        # said once, and it runs on


def test_a_missing_state_file_starts_flat_and_is_logged(up, tmp_path):
    path, said = str(tmp_path / "deep" / "er" / "capit_long_state.json"), []
    rows = run_steps(up, funding(up), path, 4400, 4400, log=said.append)
    assert rows == [] and sum("no state file" in s and "starts flat" in s for s in said) == 1
    assert state_of(path)["state_note"].endswith("(missing state file)")
    assert p9.load_state_readonly(path)[1] is None and p9.load_state_readonly(path + ".x") == (None, "missing")


def test_the_write_is_atomic_a_failed_write_leaves_the_old_state_and_is_logged(up, tmp_path, monkeypatch):
    path, said = str(tmp_path / "capit_long_state.json"), []
    fund = funding(up)
    run_steps(up, fund, path, 4400, K + 5)
    with open(path, "rb") as fh:
        before = fh.read()
    real_replace = os.replace

    def boom(a, b):
        raise OSError("planted")
    monkeypatch.setattr(p9.os, "replace", boom)
    rows = run_steps(up, fund, path, K + 6, K + 6, log=said.append)
    monkeypatch.setattr(p9.os, "replace", real_replace)
    with open(path, "rb") as fh:
        assert fh.read() == before                                 # never a half-written state
    assert sum("could not be written" in s for s in said) == 1 and [r["status"] for r in rows] == ["OPEN", "OPEN"]
    run_steps(up, fund, path, K + 7, K + 60)                       # the next step redoes what was not saved
    ref = str(tmp_path / "ref.json")
    run_steps(up, fund, ref, 4400, K + 60)
    assert same(state_of(path)["closed"], state_of(ref)["closed"])
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    assert "NaN" not in text and "Infinity" not in text


# ---------------------------------------------------------------- 8. it never stops a step
def test_a_failure_is_one_line_and_the_step_goes_on(up, tmp_path, monkeypatch):
    path, said = str(tmp_path / "capit_long_state.json"), []
    fund = funding(up)
    run_steps(up, fund, path, 4400, K + 5)
    with open(path, "rb") as fh:
        before = fh.read()

    def boom(*a, **k):
        raise RuntimeError("planted")
    monkeypatch.setattr(p9, "features", boom)
    rows = p9.step(bars={BTC: up.iloc[:K + 9], ETH: up.iloc[:K + 9]}, now_ms=close_ms(up, K + 8) + 1, funding={},
                   state_path=path, log=said.append)
    assert [s for s in said if "failed" in s] == ["playbook9 BTCUSDT failed: RuntimeError('planted')",
                                                  "playbook9 ETHUSDT failed: RuntimeError('planted')"]
    assert [r["status"] for r in rows] == ["OPEN", "OPEN"]         # what the state holds is still reported
    with open(path, "rb") as fh:
        assert fh.read() == before                                 # and a failed coin leaves no half-made step
    monkeypatch.setattr(p9, "load_state", boom)
    said2 = []
    assert p9.step(bars={BTC: up}, now_ms=close_ms(up, K + 9), state_path=path, log=said2.append) == []
    assert said2 == ["playbook9 failed: RuntimeError('planted')"]
    assert p9.step(bars={BTC: up}, now_ms=close_ms(up, K + 9), state_path=path, log=boom) == []     # even a broken log
    monkeypatch.setattr(reports, "PLAYBOOK_MODULES", ("playbook9",))
    monkeypatch.setattr(reports, "PLAYBOOK_JSON", str(tmp_path / "playbook.json"))
    monkeypatch.setattr(p9, "step", boom)
    out = []
    assert reports.playbooks(log=out.append) == [] and any("playbook playbook9 failed" in s for s in out)


def test_bars_that_are_missing_or_too_short_do_nothing(up, tmp_path):
    path, said = str(tmp_path / "capit_long_state.json"), []
    assert p9.step(bars={}, now_ms=close_ms(up, 100), funding={}, state_path=path, log=said.append) == []
    assert p9.step(bars={BTC: up.iloc[:40], ETH: up.iloc[:0]}, now_ms=close_ms(up, 39) + 1, funding={}, state_path=path,
                   log=said.append) == []
    assert not any("failed" in s for s in said)


def test_the_step_is_cheap_and_reports_its_cost(up, tmp_path):
    path = str(tmp_path / "capit_long_state.json")
    run_steps(up, funding(up), path, 4400, 4401)
    both = {BTC: up.iloc[:4403], ETH: up.iloc[:4403]}
    p9.step(bars=both, now_ms=close_ms(up, 4402) + 1, funding={BTC: funding(up), ETH: funding(up)}, state_path=path,
            log=QUIET)
    assert 0 < p9.LAST_RUN["seconds"] < 2.0                        # two coins, a new bar each: far under a second in use
    assert p9.page_block([])["p9_rebound_a"]["step_seconds"] == p9.LAST_RUN["seconds"]


# ---------------------------------------------------------------- 9. rows, the page block, the scoreboard, the allocator
@pytest.fixture()
def closed_rows(up, down):
    """Four closed trades: both rules on a rebound that ran and on one that failed (two states, as two coins)."""
    rows = []
    for df, asset in ((up, BTC), (down, ETH)):
        st = p9.replay(asset, df, funding(df), close_ms(df, 4400))
        rows += [r for r in p9.rows_of(st) if r["status"] == "CLOSED"]
    return rows


def test_rows_follow_the_interface_and_carry_r_and_dollars(closed_rows, up):
    assert len(closed_rows) == 4
    for r in closed_rows:
        for key in ("book", "asset", "status", "side", "setup_utc", "entry_utc", "entry", "stop", "target_1", "target_2",
                    "exit_utc", "exit", "why_out", "r", "pnl_usd", "fees_usd", "text"):
            assert key in r
        assert r["book"] in p9.BOOKS and r["side"] == 1 and r["status"] == "CLOSED"
        assert abs(r["pnl_usd"] - r["r"] * (r["entry"] - r["stop"]) / r["entry"] * p9.STAKE) < 0.02
        assert 19.0 < r["fees_usd"] < 21.5 and r["exit_utc"] > r["entry_utc"]
        assert "NOT passed" in r["text"] and "Paper" in r["text"] and ("%+.2fR" % r["r"]) in r["text"]
    won = [r for r in closed_rows if r["asset"] == BTC]
    lost = [r for r in closed_rows if r["asset"] == ETH]
    assert all(r["why_out"] == "T1+T2" and r["r"] > 1.3 for r in won)
    assert all(r["why_out"] == "STOP" and -1.2 < r["r"] < -1.0 for r in lost)
    json.dumps(closed_rows, allow_nan=False)


def test_the_page_block_says_not_passed_and_shows_the_open_trade(up, tmp_path, closed_rows):
    path = str(tmp_path / "capit_long_state.json")
    rows = run_steps(up, funding(up), path, 4400, K + 10)
    blk = p9.page_block(rows + closed_rows)
    assert set(blk) == set(p9.BOOKS)
    for book, b in blk.items():
        assert "NOT passed" in b["title"] and b["not_passed"] is True and "NOT passed" in b["note"]
        assert "FAILED" in b["note"] and "flat over 123 trades" in b["note"] and "too few" in b["note"]
        assert b["registered"] == "2026-11-24 12:50 UTC" and b["started_utc"] == "2027-02-18 20:15"
        assert b["totals"]["trades"] == 2 and b["totals"]["won"] == 1 and b["totals"]["avg_r"] is not None
        assert abs(b["totals"]["net_usd"] - sum(r["pnl_usd"] for r in closed_rows if r["book"] == book)) < 0.01
        assert set(b["by_asset"]) == {BTC, ETH} and len(b["recent"]) == 2
        assert len(b["open"]) == 1 and b["open"][0]["status"] == "OPEN" and b["open"][0]["target_1"] > b["open"][0]["entry"]
        assert "books" not in b                                    # the web tab's per-coin rows are for other books
        coin = b["coins"][BTC]
        assert coin["last_close_utc"] == p9._utc(close_ms(up, K + 10)) and coin["funding_fresh"] is True
        assert "vault" in b["pass_rule"] and "30 closed forward trades" in b["pass_rule"]
    assert "Rule B" in blk["p9_rebound_b"]["rule"] and "Rule B" not in blk["p9_rebound_a"]["rule"]
    json.dumps(blk, allow_nan=False)


def test_the_scoreboard_and_the_allocator_read_the_rows(closed_rows, tmp_path, monkeypatch):
    live = tmp_path / "out" / "live"
    live.mkdir(parents=True)
    monkeypatch.setattr(reports, "ROOT", str(tmp_path))
    monkeypatch.setattr(reports, "SCOREBOARD_JSON", str(live / "scoreboard.json"))
    monkeypatch.setattr(ba, "LIVE_DIR", str(live))
    said = []
    out = reports.scoreboard(closed_rows, log=said.append)
    mine = dict((r["book"], r) for r in out["rows"] if r["book"] in p9.BOOKS)
    assert set(mine) == set(p9.BOOKS)
    for book, r in mine.items():
        assert r["title"] == p9.BOOKS[book]["scoreboard_title"] and "NOT passed" in r["title"] and r["kind"] == "strategy"
        assert r["trades"] == 2 and r["verdict"] == "too few trades to judge (2 of 30)"
        assert r["days"] == 1                                      # both coins closed on one UTC day: one day, not two
        assert abs(r["net_usd"] - sum(x["pnl_usd"] for x in closed_rows if x["book"] == book)) < 0.01
    assert not any("book allocator" in s for s in said)
    # H110 fixed its 37 books at registration: a book that joins later is named as not registered and gets no share
    names = [(x["kind"], x["book"]) for x in out["a_alloc"]["books_not_registered"]]
    assert ("strategy", "p9_rebound_a") in names and ("strategy", "p9_rebound_b") in names
    assert not any(k[1] in p9.BOOKS for k in ba.BOOKS) and out["a_alloc"]["books_left_out"] == []
    assert not any(x.get("book") in p9.BOOKS for x in out["a_alloc"].get("shares_today") or [])
    json.dumps(out, allow_nan=False)


# ---------------------------------------------------------------- 10. the Telegram cards
EVENT = {  # the 21 Nov 2026 trigger as the book would have written it (bars and funding of the box's files)
    "id": "BTCUSDT|1795243500000", "asset": BTC, "rules": ["A", "B"], "decided_ms": 1795243500000,
    "decided_utc": "2026-11-21 06:45", "close": 57194.94, "atr1h": 843.2618331368108, "r_dist": 2529.7854994104323,
    "funding": -6.069e-05, "funding_set_ms": 1795219200002, "funding_fresh": True, "late": False, "not_taken": {},
    "entry_est": 57194.94, "stop_est": 54665.15450058957, "t1_est": 59724.72549941044, "t2_est": 62254.510998820864,
    "risk_pct": 4.423093195675058, "time_exit_ms": 1795416300000, "time_exit_utc": "2026-11-23 06:45"}
DEC = datetime(2026, 11, 21, 6, 45, tzinfo=timezone.utc)
CLOSED = [{"id": "p9_rebound_%s|BTCUSDT|1795243500000" % x.lower(), "book": "p9_rebound_%s" % x.lower(), "asset": BTC,
           "rule": x, "entry": 57193.99, "exit": 61530.01, "exit_close_ms": 1795416300000, "why_out": "T1+TIME",
           "r": 1.310420139465617, "pnl_usd": 579.6206676532821} for x in ("A", "B")]


def test_the_trigger_card_text():
    card = tn.capit_trigger_card(EVENT, DEC + timedelta(minutes=3))
    assert card.split("\n") == [
        u"\U0001f3af <b>Capitulation long · BTC</b>",
        u"Rules A and B fired at the 06:45 UTC close (Sat 21 Nov).",
        u"Entry near <b>57,194.94</b> (paper fill: next bar's open)",
        u"Stop <b>54,665.15</b> · risk 4.4%",
        u"Target 1 <b>59,724.73</b>: half off, then stop at entry",
        u"Target 2 62,254.51: the rest",
        u"Time exit 06:45 UTC, Mon 23 Nov (48 h)",
        u"Funding -0.0061%: shorts are paying.",
        u"<i>Paper only, NOT passed. On history rule A was flat over 123 trades; rule B had 32 trades, too few to judge.</i>"]
    assert max(len(ln) for ln in card.split("\n")[:-1]) <= 60       # short lines; the last one is the honest line
    low = card.lower()
    assert "proven" not in low and "edge" not in low and "guarantee" not in low and "signal" not in low


def test_the_trigger_card_variants_one_rule_late_and_after_the_fill():
    now = DEC + timedelta(minutes=3)
    a_only = dict(EVENT, rules=["A"], funding=3.6e-05, not_taken={"B": "funding_not_negative"})
    card = tn.capit_trigger_card(a_only, now)
    assert "Rule A fired at the 06:45 UTC close (Sat 21 Nov)." in card and "Rules A and B" not in card
    assert "Rule B did not fire: funding +0.0036%, shorts are not paying." in card and "shorts are paying" not in card
    assert "Rule B did not fire: the funding reading is stale." in tn.capit_trigger_card(
        dict(a_only, not_taken={"B": "funding_stale"}), now)
    assert "Rule B did not fire: no funding reading." in tn.capit_trigger_card(
        dict(a_only, funding=None, not_taken={"B": "funding_missing"}), now)
    assert "Rule B is already in a trade: not taken again." in tn.capit_trigger_card(
        dict(a_only, not_taken={"B": "in_trade"}), now)
    b_only = tn.capit_trigger_card(dict(EVENT, rules=["B"], not_taken={"A": "in_trade"}), now)
    assert "Rule B fired" in b_only and "Rule A is already in a trade: not taken again." in b_only
    assert "Late" not in card
    late = tn.capit_trigger_card(EVENT, DEC + timedelta(hours=3, minutes=10))
    assert u"Late: this fired 3 h 10 min ago; the price has moved since." in late
    assert "Late: this fired 3 min ago" in tn.capit_trigger_card(dict(EVENT, late=True), now)
    filled = tn.capit_trigger_card(dict(EVENT, entry=57193.99, stop=54664.20450058956, t1=59723.77549941043,
                                        t2=62253.56099882086), now)
    assert "Entry <b>57,193.99</b> (the paper fill)" in filled and "Stop <b>54,664.20</b>" in filled
    eth = tn.capit_trigger_card(dict(EVENT, asset=ETH, entry_est=1613.76, stop_est=1534.02, t1_est=1693.50,
                                     t2_est=1773.24, funding=-0.00018843), now)
    assert u"Capitulation long · ETH" in eth and "Entry near <b>1,613.76</b>" in eth and "risk 4.9%" in eth
    for bad in (None, {}, dict(EVENT, rules=[]), dict(EVENT, asset="DOGE"), dict(EVENT, stop_est=None),
                dict(EVENT, stop_est=99999.0), dict(EVENT, decided_ms="x"), dict(EVENT, time_exit_ms=None)):
        assert tn.capit_trigger_card(bad, now) is None


def test_the_close_card_text():
    card = tn.capit_close_card(BTC, CLOSED, CLOSED)
    assert card.split("\n") == [
        u"\U0001f7e2 <b>Capitulation long · BTC · closed</b>",
        u"Rule A: <b>+1.31R</b> (+$8,694)",                        # the bot shows paper dollars at 15x (DISPLAY_X)
        u"57,193.99 → 61,530.01 · Target 1, then the 48 h exit",
        u"Rule B: <b>+1.31R</b> (+$8,694)",
        u"57,193.99 → 61,530.01 · Target 1, then the 48 h exit",
        u"Out at the 06:45 UTC close (Mon 23 Nov).",
        u"So far: rule A 1 closed, +1.31R · rule B 1 closed, +1.31R",
        u"<i>Paper only, NOT passed.</i>"]
    lost = dict(CLOSED[0], r=-1.04, pnl_usd=-460.0, exit=54664.2, why_out="STOP")
    card = tn.capit_close_card(BTC, [lost], [lost, CLOSED[1]])
    assert card.startswith(u"\U0001f534") and "Rule A: <b>-1.04R</b> (-$6,900)" in card and u"· stopped" in card
    assert tn.capit_close_card(BTC, [], CLOSED) is None and tn.capit_close_card(BTC, [{"rule": "A"}], CLOSED) is None


def _bot(monkeypatch, ok=True):
    sent, holder = [], {"ok": ok}

    def fake_call(tok, method, payload, timeout=20):
        if method == "getUpdates":
            return {"ok": True, "result": []}
        if holder["ok"]:
            sent.append((payload.get("chat_id"), payload.get("text", "")))
        return {"ok": holder["ok"]}
    monkeypatch.setattr(tn, "_call", fake_call)
    monkeypatch.setattr(tn, "_CAPIT_ERR", [None])
    return sent, holder


def _write_state(path, alerts=(), closed=()):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"version": 1, "alerts": list(alerts), "closed": list(closed)}, fh)


@pytest.fixture()
def capit_file(tmp_path, monkeypatch):
    path = str(tmp_path / "data" / "capit_long_state.json")
    monkeypatch.setattr(tn, "CAPIT_STATE", path)
    return path


def test_a_trigger_is_sent_once_to_the_owners_chat_and_never_again_after_a_restart(capit_file, monkeypatch):
    sent, _h = _bot(monkeypatch)
    _write_state(capit_file, [EVENT])
    st, now = {"chat_id": 42}, DEC + timedelta(minutes=2)
    done = tn.capit_check(st, "k", 42, now)
    assert len(done) == 1 and len(sent) == 1 and sent[0][0] == 42 and "Rules A and B fired" in sent[0][1]
    assert st["capit_alerted"] == {"t|" + EVENT["id"]: now.timestamp()}
    assert tn.capit_check(st, "k", 42, now + timedelta(minutes=1)) == [] and len(sent) == 1
    again = json.loads(json.dumps(st))                             # the bot restarts: its state comes back from its file
    _write_state(capit_file, [dict(EVENT, entry=57193.99, stop=54664.2, t1=59723.78, t2=62253.56)])   # the fill arrived
    assert tn.capit_check(again, "k", 42, now + timedelta(minutes=16)) == [] and len(sent) == 1
    eth = dict(EVENT, id="ETHUSDT|1795243500000", asset=ETH, entry_est=1613.76, stop_est=1534.02, t1_est=1693.5,
               t2_est=1773.24)
    _write_state(capit_file, [EVENT, eth])                         # another coin at the same close: its own card
    assert len(tn.capit_check(again, "k", 42, now + timedelta(minutes=17))) == 1 and "ETH" in sent[-1][1]
    assert len(sent) == 2 and all(chat == 42 for chat, _t in sent)


def test_a_failed_send_is_retried_and_old_triggers_are_not_sent(capit_file, monkeypatch):
    sent, holder = _bot(monkeypatch, ok=False)
    _write_state(capit_file, [EVENT])
    st = {"chat_id": 42}
    assert tn.capit_check(st, "k", 42, DEC + timedelta(minutes=2)) == [] and not st.get("capit_alerted")
    holder["ok"] = True
    assert len(tn.capit_check(st, "k", 42, DEC + timedelta(minutes=3))) == 1 and len(sent) == 1
    st2 = {"chat_id": 42}                                          # a bot that was away for more than 48 hours
    assert tn.capit_check(st2, "k", 42, DEC + timedelta(hours=48, minutes=1)) == [] and len(sent) == 1
    late = tn.capit_check({"chat_id": 42}, "k", 42, DEC + timedelta(hours=5))
    assert len(late) == 1 and "Late: this fired 5 h 00 min ago" in late[0]


def test_closed_trades_get_one_card_per_coin_and_close(capit_file, monkeypatch):
    sent, _h = _bot(monkeypatch)
    out = datetime(2026, 11, 23, 6, 45, tzinfo=timezone.utc)
    _write_state(capit_file, [EVENT], CLOSED)
    st = {"chat_id": 42, "capit_alerted": {"t|" + EVENT["id"]: DEC.timestamp()}}
    done = tn.capit_check(st, "k", 42, out + timedelta(minutes=2))
    assert len(done) == 1 and "closed" in sent[0][1] and "Rule A" in sent[0][1] and "Rule B" in sent[0][1]
    assert tn.capit_check(st, "k", 42, out + timedelta(minutes=3)) == [] and len(sent) == 1
    assert set(st["capit_alerted"]) == {"t|" + EVENT["id"], "c|" + CLOSED[0]["id"], "c|" + CLOSED[1]["id"]}
    later = dict(CLOSED[0], id="p9_rebound_a|BTCUSDT|1795400000000", exit_close_ms=1795416300000 + 900000, r=-1.05,
                 pnl_usd=-470.0, why_out="STOP")
    _write_state(capit_file, [EVENT], CLOSED + [later])
    done = tn.capit_check(st, "k", 42, out + timedelta(minutes=20))
    assert len(done) == 1 and "Rule A: <b>-1.05R</b>" in done[0] and "Rule B" not in done[0].split("So far")[0]
    assert "rule A 2 closed, +0.26R" in done[0]


def test_the_memory_is_capped_and_a_garbled_memory_is_started_again(capit_file, monkeypatch):
    sent, _h = _bot(monkeypatch)
    _write_state(capit_file, [EVENT])
    now = DEC + timedelta(minutes=2)
    old = dict(("t|X|%d" % i, now.timestamp() - 40 * 86400) for i in range(5))
    many = dict(("t|Y|%d" % i, now.timestamp() - i) for i in range(1, 500))
    st = {"capit_alerted": dict(old, **many)}
    tn.capit_check(st, "k", 42, now)
    assert len(st["capit_alerted"]) == tn.CAPIT_MEMORY_MAX and "t|" + EVENT["id"] in st["capit_alerted"]
    assert not any(k.startswith("t|X|") for k in st["capit_alerted"])
    st = {"capit_alerted": "garbled"}
    assert len(tn.capit_check(st, "k", 42, now)) == 1 and isinstance(st["capit_alerted"], dict)


@pytest.mark.parametrize("content", [None, b"", b"{oops", b"[1]", b'{"alerts": "x", "closed": 7}',
                                     b'{"alerts": [1, null, {"id": 5}, {"id": "a", "decided_ms": "b"}], "closed": [3, {}]}'])
def test_a_missing_or_garbled_state_file_is_no_card_and_no_crash(capit_file, monkeypatch, capsys, content):
    sent, _h = _bot(monkeypatch)
    if content is not None:
        os.makedirs(os.path.dirname(capit_file), exist_ok=True)
        with open(capit_file, "wb") as fh:
            fh.write(content)
    st = {"chat_id": 42}
    assert tn.capit_check(st, "k", 42, DEC + timedelta(minutes=2)) == [] and sent == []
    assert "failed" not in capsys.readouterr().out


def test_a_file_too_large_is_not_read(capit_file, monkeypatch):
    sent, _h = _bot(monkeypatch)
    _write_state(capit_file, [EVENT])
    monkeypatch.setattr(tn, "CAPIT_READ_MAX", 50)
    assert tn.capit_check({}, "k", 42, DEC + timedelta(minutes=2)) == [] and sent == []


def _quiet_check(monkeypatch):
    monkeypatch.setattr(tn, "_load", lambda p, d=None: None)
    monkeypatch.setattr(tn, "refit_marks", lambda: [0, 0])
    monkeypatch.setattr(tn, "disk_free_gb", lambda path=None: 50.0)
    monkeypatch.setattr(tn, "vault_check", lambda st, tok, chat, now: [])
    monkeypatch.setattr(tn, "history_check", lambda st, tok, chat, now: [])
    monkeypatch.setattr(tn, "signals_check", lambda *a, **k: None)
    monkeypatch.setattr(tn, "early_check", lambda *a, **k: None)


def test_the_check_sends_the_card_to_the_locked_chat_only_and_a_failure_there_stops_nothing(capit_file, monkeypatch, capsys):
    sent, _h = _bot(monkeypatch)
    _quiet_check(monkeypatch)
    _write_state(capit_file, [EVENT])
    now = DEC + timedelta(minutes=2)
    st = {"chat_id": 4242, "summary_day": now.strftime("%Y-%m-%d")}
    st, ev = tn.check(st, "k", now=now)
    assert [chat for chat, _t in sent] == [4242] and any("Capitulation long" in e for e in ev)
    st, ev = tn.check(st, "k", now=now + timedelta(minutes=1))
    assert len(sent) == 1 and not any("Capitulation long" in e for e in ev)
    assert tn.SIGNALS_CHANNEL is None and tn.SIGNALS_PREVIEW is True          # there is no subscriber channel at all
    st0, ev0 = tn.check({"summary_day": now.strftime("%Y-%m-%d")}, "k", now=now)   # no chat yet: nothing leaves
    assert len(sent) == 1 and "capit_alerted" not in st0
    monkeypatch.setattr(tn, "_capit_read", lambda path=None: 1 / 0)
    st, ev = tn.check(st, "k", now=now + timedelta(minutes=2))                 # the alert code breaks: the check goes on
    assert st["checked_utc"] and "capitulation-long alerts failed (ZeroDivisionError)" in capsys.readouterr().out
    tn.check(st, "k", now=now + timedelta(minutes=3))
    assert "failed" not in capsys.readouterr().out                             # printed once


def test_the_bot_reads_the_books_file_and_never_imports_the_book():
    with open(tn.__file__, encoding="utf-8") as fh:
        src = fh.read()
    assert "import playbook9" not in src and "from .playbook9" not in src and "playbook9 import" not in src
    assert os.path.basename(tn.CAPIT_STATE) == os.path.basename(p9.STATE_PATH) == "capit_long_state.json"
    assert tn.CAPIT_RULES == p9.RULES and set(tn.CAPIT_HOW) == set(p9.HOW)
    assert tn.CAPIT_WINDOW_S == p9.HOLD * p9.BAR_MS // 1000


def test_the_generic_close_card_stays_quiet_for_these_books_and_30_trades_still_alerts():
    title = p9.BOOKS["p9_rebound_a"]["scoreboard_title"]

    def cur(n, net):
        c, v, m = tn.counts({"rows": [{"book": "p9_rebound_a", "title": title, "trades": n, "net_usd": net,
                                       "verdict": "too few trades to judge (%d of 30)" % n}]}, {})
        return {"c": c, "v": v, "net": m, "refits": []}
    assert "p9_rebound_a".startswith(tn.QUIET) and "p9_cascade".startswith(tn.QUIET)
    assert tn.events(cur(3, 100.0), cur(4, 300.0), None) == []     # its own close card says it (capit_check), once
    ev = tn.events(cur(29, 100.0), cur(30, 300.0), None)
    assert len(ev) == 1 and "Capitulation long A (NOT passed)" in ev[0] and "30 trades" in ev[0]
    assert tn._rname("p9_rebound_b") == "Capit long B" and len(tn._rname("p9_rebound_a")) <= 12


def test_from_the_books_step_to_the_card(up, capit_file, monkeypatch):
    """End to end: the state file the book writes is the file the bot reads."""
    sent, _h = _bot(monkeypatch)
    fund = funding(up)
    run_steps(up, fund, capit_file, 4400, K)
    dec = datetime.fromtimestamp(close_ms(up, K) / 1000.0, timezone.utc)
    st = {"chat_id": 42}
    done = tn.capit_check(st, "k", 42, dec + timedelta(seconds=80))
    assert len(done) == 1 and "Rules A and B fired at the 00:30 UTC close (Sat 20 Feb)." in done[0]
    assert "Entry near" in done[0] and "Time exit 00:30 UTC, Mon 22 Feb (48 h)" in done[0] and "Late" not in done[0]
    run_steps(up, fund, capit_file, K + 1, K + 60)
    out_ms = state_of(capit_file)["closed"][0]["exit_close_ms"]
    done = tn.capit_check(st, "k", 42, datetime.fromtimestamp(out_ms / 1000.0 + 90, timezone.utc))
    assert len(done) == 1 and "closed" in done[0] and "Target 1 and Target 2" in done[0] and "+1.3" in done[0]
    assert len(sent) == 2 and tn.capit_check(st, "k", 42, datetime.fromtimestamp(out_ms / 1000.0 + 200, timezone.utc)) == []


# ---------------------------------------------------------------- 11. the vault feed's inputs do not change
def test_the_setups_document_the_vault_feed_reads_is_the_same_with_the_books_on_the_page(up, tmp_path, monkeypatch):
    ts = pytest.importorskip("test_setups")
    from engine15 import setups
    monkeypatch.delenv(setups.WEB_ENV, raising=False)
    for name in ("S1_DIR", "BARS_DIR", "TRADES_DIR"):              # no real record, bar or trade file (as test_setups)
        monkeypatch.setattr(setups, name, str(tmp_path / ("no_" + name)))
    page = ts.make_page()
    before = setups.build(json.loads(json.dumps(page)))
    rows = run_steps(up, funding(up), str(tmp_path / "s.json"), 4400, K + 10)
    assert [r["status"] for r in rows] == ["OPEN", "OPEN"]
    page["playbook"] = dict(page.get("playbook") or {}, playbook9=json.loads(json.dumps(p9.page_block(rows))))
    assert setups.build(json.loads(json.dumps(page))) == before
    assert sorted(os.listdir(str(tmp_path))) == ["s.json"]         # the book wrote its own state and nothing else


# ---------------------------------------------------------------- 12. the rebound signal file (the vault's dry run)
def _sig(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def test_the_signal_file_follows_rule_a_waiting_open_and_closed(up, tmp_path):
    path, sig = str(tmp_path / "capit_long_state.json"), str(tmp_path / "out" / "rebound_signal.json")
    fund = funding(up)
    for i in list(range(4400, K)) + [K]:
        p9.step(bars={BTC: up.iloc[:i + 1]}, now_ms=close_ms(up, i) + 20000, funding={BTC: fund}, state_path=path,
                log=QUIET, signal_path=sig)
        if i == 4400:
            s = _sig(sig)
            assert s["markets"][BTC] == {"state": "none"} and s["markets"][ETH] == {"state": "none"}
    s = _sig(sig)
    assert s["schema"] == 1 and s["book"] == "p9_rebound_a" and s["paper_only"] is True and s["passed"] is False
    w = s["markets"][BTC]
    assert w["state"] == "waiting" and w["id"] == "BTCUSDT.20270220T003000Z.rebound"
    assert w["decided_utc"] == w["entry_utc"] == "2027-02-20T00:30:00Z" and w["rule_b_too"] is True
    assert w["stop_est"] < w["entry_est"] < w["target_1_est"] < w["target_2_est"]
    assert w["time_exit_utc"] == "2027-02-22T00:30:00Z"
    p9.step(bars={BTC: up.iloc[:K + 2]}, now_ms=close_ms(up, K + 1) + 20000, funding={BTC: fund}, state_path=path,
            log=QUIET, signal_path=sig)
    o, row = _sig(sig)["markets"][BTC], [r for r in p9.rows_of(state_of(path)) if r["book"] == "p9_rebound_a"][0]
    assert o["state"] == "open" and o["id"] == w["id"] and o["entry_utc"] == "2027-02-20T00:30:00Z"
    assert (o["entry"], o["stop"], o["target_1"], o["target_2"]) == (row["entry"], row["stop"], row["target_1"],
                                                                     row["target_2"])
    assert o["stop_now"] == o["stop"] and o["t1_taken"] is False
    for i in range(K + 2, K + 61):
        p9.step(bars={BTC: up.iloc[:i + 1]}, now_ms=close_ms(up, i) + 20000, funding={BTC: fund}, state_path=path,
                log=QUIET, signal_path=sig)
    c = _sig(sig)["markets"][BTC]
    assert c["state"] == "none" and c["last_closed"]["id"] == w["id"] and c["last_closed"]["why_out"] == "T1+T2"


def test_only_the_live_step_writes_the_signal_file_by_default(up, tmp_path, monkeypatch):
    path = str(tmp_path / "state" / "capit_long_state.json")
    live = str(tmp_path / "live" / "rebound_signal.json")
    monkeypatch.setattr(p9, "SIGNAL_PATH", live)
    p9.step(bars={BTC: up.iloc[:4401]}, now_ms=close_ms(up, 4400) + 1, funding={}, state_path=path, log=QUIET)
    assert not os.path.exists(live) and os.listdir(os.path.dirname(path)) == ["capit_long_state.json"]
    monkeypatch.setattr(p9, "STATE_PATH", path)
    p9.step(bars={BTC: up.iloc[:4402]}, now_ms=close_ms(up, 4401) + 1, funding={}, log=QUIET)
    assert _sig(live)["generated_utc"] is not None and sorted(os.listdir(os.path.dirname(live))) == ["rebound_signal.json"]


def test_a_signal_file_that_cannot_be_written_is_one_line_and_the_trades_go_on(up, tmp_path, monkeypatch):
    path, said = str(tmp_path / "capit_long_state.json"), []
    def boom(*_a, **_k):
        raise OSError("disk full")
    monkeypatch.setattr(p9, "write_signal", boom)
    run_steps(up, funding(up), path, 4400, K + 1, log=said.append)
    assert state_of(path)["books"]["p9_rebound_a"][BTC]["open"] is not None
    p9.step(bars={BTC: up.iloc[:K + 3]}, now_ms=close_ms(up, K + 2) + 1, funding={}, state_path=path, log=said.append,
            signal_path=str(tmp_path / "x.json"))
    assert sum("rebound signal file was not written" in s for s in said) == 1
