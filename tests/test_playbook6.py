# -*- coding: utf-8 -*-
"""tests for engine15/playbook6.py: RL Phase 6's two forward paper books (p6_mtrend, p6_p4trend), both NOT passed.

1. Interface and labels: BOOKS / step / page_block as playbook5's; "NOT passed", "1 of 8 variants", "hindsight" and the
   Phase 6 report's numbers in the texts; registered in engine15/reports.py with scoreboard titles.
2. No look-ahead: a decision at close t uses only data <= t (bars after t scrambled: the same decisions) and the newest
   model whose data end <= t; a model whose data end is after `now` is never used; fills at the NEXT open.
3. The trend fallback reproduces history's rule (phase5.oos_w, fallback="trend") on a small fixture, and the 'do no harm'
   flag of a Phase 6 model is its own validation net Sharpe < 0.5 (learn6.q_fold6's export hook), and the exported model
   gives q_fold6's own test values.
4. The record is append-only; a step again on the same bars records nothing new and gives the same rows; no model ->
   no record (no guess); shorts show as shorts.
Planted data only; the real evidence store and the live folders are never touched."""
import json
import os
import re
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine15 import playbook6 as p6  # noqa: E402
from engine15.rl import features4, forward5, forward6, pool4  # noqa: E402

CFG = forward6.load_cfg()
BOOK6, BOOK4 = "p6_mtrend", "p6_p4trend"


def _bars(n, seed):
    rng = np.random.RandomState(seed)
    close = 30000.0 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    opn = np.concatenate([[30000.0], close[:-1]])
    sp = np.abs(rng.normal(0, 0.001, n)) * close
    return pd.DataFrame({"open": opn, "high": np.maximum(opn, close) + sp, "low": np.minimum(opn, close) - sp,
                         "close": close, "volume": rng.uniform(50, 150, n)},
                        index=pd.date_range("2026-01-01", periods=n, freq="15min", tz="UTC").as_unit("ms"))


def _funding(index):
    from engine15.rl import data
    t = pd.date_range(index[0].floor("8h"), index[-1], freq="8h", tz="UTC")
    raw = t.as_unit("ms").asi8.astype("int64")
    return pd.DataFrame({"rate": np.full(len(t), 0.0001), "settle_ms": data.settlement_ms(raw)},
                        index=pd.to_datetime(raw, unit="ms", utc=True))


def _model(mid, end_ms, cols, feats, fb, wseed):
    q = CFG["qagent"]
    n, F = len(next(iter(feats.values()))), len(cols)
    seeds = {}
    for s in range(3):
        stats = {}
        for a in p6.ASSETS:
            mu, sd = pool4.norm_stats(feats[a].values, 0, n, np.arange(F))
            stats[a] = {"mu": mu.tolist(), "sd": sd.tolist()}
        seeds[str(s)] = {"weights": [(3.0 * np.random.default_rng(wseed + s).standard_normal((5, F))).tolist()],
                         "biases": [np.zeros(5).tolist()], "stats": stats,
                         "fallback": dict((a, bool(fb.get((s, a), False))) for a in p6.ASSETS),
                         "val": dict((a, {"sharpe": 0.1 if fb.get((s, a)) else 0.9}) for a in p6.ASSETS),
                         "chosen": {"shaping_value": 0.5}}
    return {"id": mid, "data_end_close_ms": int(end_ms), "data_end_utc": forward5._utc(end_ms), "columns": cols,
            "actions": CFG["actions"], "min_hold_bars": 4,
            "qagent": dict((k, q[k]) for k in ("reward_scale", "cost_mult", "obs_clip", "activation", "vol_scale",
                                               "vol_ref_annual", "vol_scale_cap", "risk_aversion", "net_arch")),
            "seeds": seeds, "info": {}}


def _setup(tmp_path, n=5600, later=False):
    bars, fund, snaps, feats = {}, {}, {}, {}
    for k, a in enumerate(p6.ASSETS):
        b = _bars(n, 30 + k)
        bars[a], fund[a] = b, _funding(b.index)
        rng = np.random.default_rng(40 + k)
        vals = dict((c, rng.standard_normal(n).astype(np.float32)) for c in list(features4.READINGS) + features4.AVAIL_COLS)
        snaps[a] = str(tmp_path / ("snap_%s.npz" % a))
        np.savez(snaps[a], times_ms=np.asarray(b.index.as_unit("ms").asi8, dtype=np.int64), meta="{}", **vals)
        feats[a] = features4.build(b, fund[a], CFG["features"], features4.readings_frame(snaps[a], b.index)).astype("float32")
    cols = list(feats["BTCUSDT"].columns)
    reg = bars["BTCUSDT"].index[4900] + pd.Timedelta("15min")
    reg_ms = int(reg.value // 10**6)
    md6, md4 = tmp_path / "models6", tmp_path / "models4"
    md6.mkdir()
    md4.mkdir()
    m6 = _model("m6_planted", reg_ms, cols, feats, {(0, "BTCUSDT"): True}, 0)
    m4 = _model("m5_planted", reg_ms, cols, feats, {(0, "BTCUSDT"): True, (0, "ETHUSDT"): True}, 10)
    with open(md6 / "model_a.json", "w") as fh:
        json.dump(m6, fh)
    with open(md4 / "model_a.json", "w") as fh:
        json.dump(m4, fh)
    if later:
        m6b = _model("m6_later", reg_ms + 300 * 900000, cols, feats, {}, 20)
        with open(md6 / "model_b.json", "w") as fh:
            json.dump(m6b, fh)
    return bars, fund, snaps, {BOOK6: str(md6), BOOK4: str(md4)}, reg, feats


def _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg, now=None, jd="fwd", readings=True):
    monkeypatch.setattr(p6, "REGISTERED", str(reg)[:16])
    return p6.step(bars=bars, funding=fund, readings=snaps if readings else None, journal_dir=str(tmp_path / jd),
                   models_dir=md, now_ms=now, launch=False, log=lambda *_: None)


def _J(tmp_path, book, a, jd="fwd"):
    return forward5.read_journal(str(tmp_path / jd / ("decisions_%s_%s.jsonl" % (book, a))))


# ---------------------------------------------------------------- 1. interface and labels
def test_interface_labels_and_registration():
    assert set(p6.BOOKS) == {BOOK6, BOOK4}
    for b, f in p6.BOOKS.items():
        assert "NOT passed" in f["title"] and "NOT passed" in f["scoreboard_title"] and "NOT passed" in p6.NOT_PASSED[b]
        assert "hindsight" in f["title"] and "hindsight" in p6.NOT_PASSED[b] and "hindsight" in p6.rule_text(b)
        assert set(f["assets"]) == {"BTCUSDT", "ETHUSDT"} and f["fallback"] == "trend"
    assert "1 of 8 variants" in p6.BOOKS[BOOK6]["title"] and "1 of 8 variants" in p6.NOT_PASSED[BOOK6]
    assert "Phase 4's results" in p6.NOT_PASSED[BOOK6] and "Phase 4's results" in p6.NOT_PASSED[BOOK4]
    for num in ("BTC 0.87, ETH 0.96", "0.64 / 0.60"):
        assert num in p6.DETAIL[BOOK6]
    for num in ("BTC 0.98, ETH 0.82", "0.64 / 0.60"):
        assert num in p6.DETAIL[BOOK4]
    for path in ("engine15/playbook6.py", "engine15/rl/forward6.py"):
        with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
            assert "kronos" not in fh.read().lower()
    from engine15 import reports
    assert "playbook6" in reports.PLAYBOOK_MODULES
    t = reports._scoreboard_titles()
    for b, f in p6.BOOKS.items():
        assert t[b] == f["scoreboard_title"]
    r = pd.Timestamp(p6.REGISTERED, tz="UTC")
    assert r.minute % 15 == 0 and r.second == 0


def test_books_block_accounting_fills_and_shorts(monkeypatch, tmp_path):
    bars, fund, snaps, md, reg, feats = _setup(tmp_path)
    t0 = time.time()
    rows = _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg)
    assert time.time() - t0 < 10.0
    blk = p6.page_block(rows)
    pos_re = re.compile(r"^(flat|(long|short) \d+\.\d\dx since \d{4}-\d\d-\d\d \d\d:\d\d UTC)$")
    for book in (BOOK6, BOOK4):
        b = blk[book]
        for k in ("title", "hypothesis", "registered", "not_passed", "rule", "note", "books", "open", "recent", "totals"):
            assert k in b
        assert b["not_passed"] is True and "NOT passed" in b["note"] and "hindsight" in b["note"]
        assert set(b["books"]) == {"BTCUSDT", "ETHUSDT"}
        for a, s in b["books"].items():
            for k in ("book_position", "equity_usd", "return_pct", "bh_spot_equity_usd", "bh_spot_return_pct", "max_dd_pct",
                      "bh_max_dd_pct", "rule_exposure", "last_close_utc", "forward_trades", "seed_modes", "model",
                      "momentum_30d_pct", "daily_direction", "fallback_seeds"):
                assert k in s, k
            assert s["fallback_seeds"] == (1 if (a == "BTCUSDT" or book == BOOK4) else 0) == s["seed_modes"].count("trend")
            c = bars[a]["close"].values
            assert abs(s["momentum_30d_pct"] - 100 * (c[-1] / c[-1 - 2880] - 1)) < 0.01
            assert s["daily_direction"] == int(feats[a]["mom_signal"].values[-1]) and s["daily_direction"] in (-1, 1)
            assert pos_re.match(s["book_position"]), s["book_position"]
            if s["rule_exposure"]:
                assert s["book_position"].startswith("long" if s["rule_exposure"] > 0 else "short")
            J = _J(tmp_path, book, a)
            assert J and min(r["c"] for r in J) > p6.reg_ms()                 # forward only
            assert len(J) == len(bars[a]) - 4901
            mine = [r for r in rows if r["asset"] == a and r["book"] == book]
            assert len(mine) >= 3
            assert abs(sum(r["pnl_usd"] for r in mine) - (s["equity_usd"] - p6.STAKE)) < 0.05 + 0.01 * len(mine)
            op = bars[a]["open"]
            for r in mine:                                                     # filled at the NEXT open
                assert abs(r["entry"] - op.loc[pd.Timestamp(r["entry_utc"], tz="UTC")]) < 1e-6
                if r["status"] == "CLOSED":
                    assert abs(r["exit"] - op.loc[pd.Timestamp(r["exit_utc"], tz="UTC")]) < 1e-6
    for r in rows:
        assert r["status"] in ("OPEN", "CLOSED") and r["side"] in (1, -1) and "NOT passed" in r["text"]
        assert r["why_out"] in ("AGENT", "OPEN") and r["r"] is None and r["stop"] is None
        assert r["entry_utc"] > str(reg)[:16]
        assert ("short" in r["text"].split(":")[1].split("(")[0]) == (r["side"] == -1)
    assert any(r["side"] == -1 for r in rows) and any(r["side"] == 1 for r in rows)


# ---------------------------------------------------------------- 2. no look-ahead
def test_no_lookahead_data_and_models(monkeypatch, tmp_path):
    bars, fund, snaps, md, reg, _ = _setup(tmp_path, later=True)
    a0 = "BTCUSDT"
    cut = 5100                                                     # decide up to bar 5100's close only
    cut_close = int(bars[a0].index[cut].value // 10**6) + 900000
    _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg, now=cut_close, jd="cut")
    later_end = int(reg.value // 10**6) + 300 * 900000
    assert cut_close < later_end
    for book in (BOOK6, BOOK4):
        J = _J(tmp_path, book, a0, "cut")
        assert J and max(r["c"] for r in J) <= cut_close
        if book == BOOK6:
            assert {r["m"] for r in J} == {"m6_planted"}                  # the later model's data end is after now
    # the future scrambled (bars and readings after the cut): every decision up to the cut is the same
    sb = dict((a, b.copy()) for a, b in bars.items())
    rng = np.random.default_rng(9)
    for a in sb:
        k = sb[a].index[cut + 1:]
        f = rng.uniform(0.7, 1.3, len(k))
        for c in ("open", "high", "low", "close"):
            sb[a].loc[k, c] = sb[a].loc[k, c].values * f
    ss = {}
    for a in snaps:
        z = dict(np.load(snaps[a]))
        for c in z:
            if c not in ("times_ms", "meta"):
                z[c] = z[c].copy()
                z[c][cut + 1:] = rng.standard_normal(len(z[c]) - cut - 1).astype(np.float32)
        ss[a] = str(tmp_path / ("scr_%s.npz" % a))
        np.savez(ss[a], **z)
    _step(monkeypatch, tmp_path, sb, fund, ss, md, reg, jd="full")
    for book in (BOOK6, BOOK4):
        for a in p6.ASSETS:
            A, B = _J(tmp_path, book, a, "cut"), _J(tmp_path, book, a, "full")
            Bc = [r for r in B if r["c"] <= cut_close]
            assert len(A) == len(Bc) > 0
            for x, y in zip(A, Bc):
                assert (x["t"], x["ip"], x["req"], x["m"], x.get("mode")) == (y["t"], y["ip"], y["req"], y["m"], y.get("mode"))
    # the newest model whose data end <= the bar's close decides
    B = _J(tmp_path, BOOK6, a0, "full")
    assert all(r["m"] == ("m6_later" if r["c"] >= later_end else "m6_planted") for r in B)
    assert {r["m"] for r in B} == {"m6_planted", "m6_later"}


# ---------------------------------------------------------------- 3. the trend fallback = history's rule
def test_trend_mode_follows_the_reference_and_records_modes(monkeypatch, tmp_path):
    bars, fund, snaps, md, reg, feats = _setup(tmp_path)
    _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg)
    for book, trend_seeds in ((BOOK6, {"BTCUSDT": [0], "ETHUSDT": []}), (BOOK4, {"BTCUSDT": [0], "ETHUSDT": [0]})):
        for a in p6.ASSETS:
            J = _J(tmp_path, book, a)
            want = ["trend" if s in trend_seeds[a] else "model" for s in range(3)]
            assert all(r["mode"] == want for r in J)
            ref = np.nan_to_num(feats[a]["mom_signal"].astype(np.float32).values)
            ms = np.asarray(bars[a].index.as_unit("ms").asi8)
            r_at = ref[np.searchsorted(ms, [r["t"] for r in J])]
            assert np.mean(np.abs(r_at) > 0) > 0.9
            for s in trend_seeds[a]:
                req = np.array([r["req"][s] for r in J])
                assert np.mean(req == r_at) > 0.98                           # holds the daily momentum position
                assert (req < 0).any() or (r_at >= 0).all()


def test_fallback_reproduces_phase6_history_rule(tmp_path):
    """phase5.oos_w (Phase 6's evaluation, fallback="trend") and forward5.model_w (the live book) give the same values
    and, through the Phase 3 policy, the same positions, on the same reference."""
    from engine15.rl import continual, phase5, policy3
    acts = list(CFG["actions"])
    n, lo, hi = 400, 100, 340
    rng = np.random.default_rng(3)
    ref = np.repeat(rng.choice([-1.0, 1.0], n // 96 + 1), 96)[:n].astype(np.float32)
    ref[:20] = np.nan                                                   # undefined head -> 0, as add_reference

    class A:
        name = "BTCUSDT"
        rd = {"ref": np.nan_to_num(ref, nan=0.0), "k": np.ones(n, np.float32), "c1": np.full(n, 0.0012, np.float32)}
        t = np.arange(n, dtype=np.int64) * 900000 + 1767225600000

        @staticmethod
        def at(ts):
            return int(np.searchsorted(A.t, int(ts.value // 10**6)))
    d = tmp_path / "v" / "s0"
    d.mkdir(parents=True)
    np.save(d / "w_f00_BTCUSDT.npy", rng.standard_normal((hi - lo, 5)).astype(np.float32))
    with open(d / "rec_f00_pool.json", "w") as fh:
        json.dump({"assets": {"BTCUSDT": {"fallback": True}}, "geo": {"BTCUSDT": {"lo": 0, "te_lo": lo, "te_hi": hi}},
                   "columns": []}, fh)
    fts = [{"i": 0, "test_start": pd.Timestamp(int(A.t[lo]), unit="ms", tz="UTC"),
            "test_end": pd.Timestamp(int(A.t[hi]), unit="ms", tz="UTC")}]
    Wh, _, _, _ = phase5.oos_w(str(tmp_path), "v", 0, fts, A, acts, None, "trend")
    model = {"actions": acts, "seeds": {"0": {"fallback": {"BTCUSDT": True}}}}
    feats = pd.DataFrame({"mom_signal": ref[lo:hi]})
    Wl = forward5.model_w(model, 0, "BTCUSDT", feats, "trend")
    assert np.array_equal(Wh, Wl)
    q = CFG["qagent"]
    Qh = continual.q_of(Wh, A.rd, lo, hi, q, acts)
    ih, _ = policy3.decide(Qh, np.asarray(acts), 2, 4)
    il, _ = forward5.decisions([(model, slice(0, hi - lo))], ("BTCUSDT", feats), A.rd["k"][lo:hi], A.rd["c1"][lo:hi],
                               acts, q, 4, {0: (2, 4)}, [0], fallback="trend")
    assert np.array_equal(ih, il[0])
    # the flat rule is untouched (playbook5)
    assert np.array_equal(forward5.model_w(model, 0, "BTCUSDT", feats), continual.neutral_w(hi - lo, acts, 0.0))


def test_phase6_model_flag_is_its_own_validation_sharpe_and_export_is_exact():
    """learn6.q_fold6's export: 'do no harm' = that seed's own validation net Sharpe < 0.5 per coin (Phase 4's rule, as in
    history), and the exported model reproduces q_fold6's own test values through forward5.model_w."""
    from engine15.rl import config, costs, learn4, learn6, qagent, synth
    from engine15.rl.env import Market
    c = config.load_phase4()
    c["q"] = dict(c["q"], evals=2, eval_every=60, patience=1, half_life_days=[None, 30])
    c["qagent"] = dict(c["qagent"], batch_size=64, chunk_steps=60)
    fcfg = {"return_windows": [1, 4, 16, 96, 672, 2880], "vol_windows": [16, 96, 672],
            "momentum_windows": [16, 96, 672, 2880], "volume_z_window": 672, "daily_closed": True,
            "phase3": {"htf": True, "momentum_signal": True, "time": True}}
    assets = []
    for nm, sd in (("BTCUSDT", 31), ("ETHUSDT", 32)):
        bars, fund, _, _ = synth.make(96 * 70, sd, 0.02, start="2021-01-01")
        m = Market(bars, fund, features4.build(bars, fund, fcfg, None).astype("float32"), costs.CostModel())
        rd = qagent.reward_arrays(m, c["qagent"])
        assets.append(learn4.MemAsset(nm, np.array(m.raw), dict((k, np.array(v)) for k, v in rd.items()),
                                      np.asarray(bars.index.as_unit("ms").asi8, dtype=np.int64), list(m.columns)))
    geo = {}
    for A in assets:
        geo[A.name] = {"lo": 3000, "val": A.n - 96 * 10 - 96 * 15, "te_lo": A.n - 96 * 10, "te_hi": A.n}
    cols = assets[0].cols(assets[0].columns)
    ex = {}
    W, rec = learn6.q_fold6(assets, ["BTCUSDT", "ETHUSDT"], cols, geo, c["q"], c["qagent"], c["actions"], 4, 7,
                            {"kind": "missed", "values": [0.25, 1.0]}, export=ex)
    for a in ("BTCUSDT", "ETHUSDT"):
        assert ex["fallback"][a] == (ex["val"][a]["sharpe"] < float(c["q"]["fallback_val_sharpe"])) == rec["assets"][a]["fallback"]
    assert ex["chosen"]["shaping_value"] in (0.25, 1.0)
    model = {"actions": c["actions"], "columns": list(assets[0].columns), "qagent": c["qagent"],
             "seeds": {"0": dict(ex, fallback={"BTCUSDT": False, "ETHUSDT": False})}}
    for A in assets:
        g = geo[A.name]
        feats = pd.DataFrame(A.X[g["te_lo"]:g["te_hi"]], columns=A.columns)
        Wl = forward5.model_w(model, 0, A.name, feats, "trend")
        assert np.allclose(Wl, W[A.name], atol=1e-4)
    modes = forward6.model_modes({"seeds": {"0": ex}})
    for a in ("BTCUSDT", "ETHUSDT"):
        assert modes[a][0]["mode"] == ("trend" if ex["fallback"][a] else "model")


# ---------------------------------------------------------------- 4. the record
def test_record_append_only_and_idempotent(monkeypatch, tmp_path):
    bars, fund, snaps, md, reg, _ = _setup(tmp_path)
    c1 = int(bars["BTCUSDT"].index[5000].value // 10**6) + 900000
    _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg, now=c1)
    paths = [str(tmp_path / "fwd" / ("decisions_%s_%s.jsonl" % (b, a))) for b in p6.BOOKS for a in p6.ASSETS]
    before = [open(p, "rb").read() for p in paths]
    rows = _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg)
    after = [open(p, "rb").read() for p in paths]
    for x, y in zip(before, after):
        assert len(y) > len(x) and y.startswith(x)                    # appended, never rewritten
    rows2 = _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg)
    assert [open(p, "rb").read() for p in paths] == after             # the same bars again: nothing new
    assert [(r["book"], r["pnl_usd"]) for r in rows2] == [(r["book"], r["pnl_usd"]) for r in rows]


def test_nothing_before_registered_and_no_model_no_record(monkeypatch, tmp_path):
    bars, fund, snaps, md, reg, _ = _setup(tmp_path)
    now = int(reg.value // 10**6)                                     # exactly at go-live: nothing yet
    rows = _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg, now=now)
    assert rows == [] and p6.LAST_STATE == {}
    rows = _step(monkeypatch, tmp_path, bars, fund, snaps, md, reg, now=now + 2 * 900000)
    blk = p6.page_block(rows)
    for book in p6.BOOKS:
        for a, s in blk[book]["books"].items():
            assert s["decisions"] == 2 and abs(s["equity_usd"] - p6.STAKE) < 50
    # the Phase 6 model not ready: p6_mtrend records nothing (no guess); the control still runs
    empty = tmp_path / "none"
    empty.mkdir()
    rows = _step(monkeypatch, tmp_path, bars, fund, snaps, dict(md, **{BOOK6: str(empty)}), reg, jd="nomodel")
    assert not any(r["book"] == BOOK6 for r in rows) and any(r["book"] == BOOK4 for r in rows)
    for a in p6.ASSETS:
        assert _J(tmp_path, BOOK6, a, "nomodel") == [] and _J(tmp_path, BOOK4, a, "nomodel")


def test_refit_launcher_gates(monkeypatch, tmp_path):
    """The Phase 6 refit: only when due, never while a refit (either) holds the shared lock, after Phase 5's, and only
    with >= 1,500 MB free; never inside the step (launch=False in every step above)."""
    cfg = CFG
    monkeypatch.setattr(forward6, "FORWARD_DIR", str(tmp_path / "f6"))
    monkeypatch.setattr(forward6, "MODELS_DIR", str(tmp_path / "m6"))
    f5dir = tmp_path / "f5"
    f5dir.mkdir()
    monkeypatch.setattr(forward5, "forward_dir", lambda c: str(f5dir))
    monkeypatch.setattr(forward5, "update_due", lambda c, now_ms=None: False)
    calls = []
    go = lambda: calls.append(1)                                      # noqa: E731
    assert forward6.maybe_launch_update(cfg, free_mb=500, launcher=go) == "low memory" and not calls
    os.remove(str(tmp_path / "f6" / "update_attempt.json"))
    with open(str(f5dir / "update.lock"), "w") as fh:                 # a refit (Phase 5's or 6's) is running
        json.dump({"pid": os.getpid()}, fh)
    assert forward6.maybe_launch_update(cfg, free_mb=4000, launcher=go) == "running" and not calls
    os.remove(str(f5dir / "update.lock"))
    monkeypatch.setattr(forward5, "update_due", lambda c, now_ms=None: True)
    assert forward6.maybe_launch_update(cfg, free_mb=4000, launcher=go) == "waiting for the phase5 refit"
    monkeypatch.setattr(forward5, "update_due", lambda c, now_ms=None: False)
    assert forward6.maybe_launch_update(cfg, free_mb=4000, launcher=go) == "launched" and calls == [1]
    assert forward6.maybe_launch_update(cfg, free_mb=4000, launcher=go) == "waiting to retry" and calls == [1]
