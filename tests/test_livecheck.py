# -*- coding: utf-8 -*-
"""livecheck: the calibration arithmetic on a synthetic journal and bar file, and the data-health state machine."""
import calendar
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import livecheck as lc  # noqa: E402

T0 = calendar.timegm((2026, 11, 2, 0, 0, 0)) * 1000                   # a Monday, 00:00 UTC
BAR = 900000
CFG = {"universes": (("solo", ("AAA",)),), "group_horizon": {}, "horizon": 4, "barrier_atr": 1.5, "assets": ("AAA",)}
# Flat bars (open 100, high 101, low 99, close 100): every 1h bar has a true range of 2, so ATR14(1h) = 2 and a
# barrier sits 3 above and below the next open. Bar 84 spikes up to 103.2, bar 86 falls to 96.5.
SPIKES = {84: (100.0, 103.2, 99.0, 100.0), 86: (100.0, 101.0, 96.5, 100.0)}
#       bar: (P up, P down, P neither, edge_pts as the journal rounds it)      grade, closes until known
CALLS = {80: (0.56, 0.40, 0.04, 16.0),                                # UP at 84 (4)   leaned up    right
         81: (0.46, 0.50, 0.04, -4.0),                                # UP at 84 (3)   leaned down  wrong
         82: (0.52, 0.44, 0.04, 8.0),                                 # UP at 84 (2)   leaned up    right
         84: (0.47, 0.49, 0.04, -2.0),                                # DOWN at 86 (2) leaned down  right
         85: (0.62, 0.34, 0.04, 28.0),                                # DOWN at 86 (1) leaned up    wrong
         86: (0.50, 0.46, 0.04, 4.0),                                 # NEITHER at 90 (4)
         87: (0.44, 0.44, 0.12, -0.0),                                # NEITHER at 91 (4); "-0.0" = it leaned down
         88: (0.55, 0.41, 0.04, 14.0)}                                # not known yet: the bars end at 91
GRADED = {84: (3, 2, 1, 0), 86: (2, 1, 1, 0), 90: (1, 0, 0, 1), 91: (1, 0, 0, 1)}   # the engine's graded_now per close
OUTCOME = {80: lc.UP, 81: lc.UP, 82: lc.UP, 84: lc.DOWN, 85: lc.DOWN, 86: lc.NEITHER, 87: lc.NEITHER}
BASE = (0.48, 0.48)


def stamp(k):
    """The journal time of bar k: its close."""
    s = (T0 + (k + 1) * BAR) // 1000
    return "%04d-%02d-%02d %02d:%02d" % __import__("time").gmtime(s)[:5]


def line(k, asset="AAA", graded=None, compact=False):
    e = {"asset": asset, "i": 1000 + k, "time": stamp(k), "price": 100.0}
    if k in CALLS:
        up, down, nei, edge = CALLS[k]
        e["odds"] = {"up": up, "down": down, "neither": nei}
        e["edge_pts"] = edge
        e["voices"] = [{"voice": "levels", "title": "Support and resistance", "up": 0.5, "down": 0.45, "trust": 0.4, "pull_pts": 1.0},
                       {"voice": "base", "title": "Base rate (no skill)", "up": BASE[0], "down": BASE[1], "trust": 0.0, "pull_pts": 0.0}]
    c = (graded or GRADED).get(k, (0, 0, 0, 0))
    e["graded_now"] = {"calls": c[0], "right": c[1], "wrong": c[2], "neither": c[3]}
    e["data"] = dict(("f%d" % j, 0.1234) for j in range(300))       # the bulk of a real line
    e["cards"] = [{"card": "Regime", "reading": "RANGE (daily)."}]
    return json.dumps(e, separators=(",", ":")) if compact else json.dumps(e)


def world(tmp_path, last_bar=91, lines=range(80, 92), graded=None, bars=True, compact=()):
    jd, dd = tmp_path / "journal", tmp_path / "data"
    (jd / "replay").mkdir(parents=True)
    dd.mkdir()
    (jd / "2026-11-02.jsonl").write_text("\n".join(line(k, graded=graded, compact=k in compact) for k in lines) + "\nnot json\n",
                                         encoding="utf-8")
    (jd / "2026-11-02.md").write_text("# the same day for reading", encoding="utf-8")
    (jd / "replay" / "2026-11-02.jsonl").write_text(line(80, graded={80: (999, 999, 0, 0)}), encoding="utf-8")   # never read
    if bars:
        rows = ["ts_ms,open,high,low,close,volume,taker_buy"]
        for k in range(last_bar + 1):
            o, h, l, c = SPIKES.get(k, (100.0, 101.0, 99.0, 100.0))
            rows.append("%d,%s,%s,%s,%s,1.0," % (T0 + k * BAR, o, h, l, c))
        (dd / "aaa_15m.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return str(jd), str(dd)


def test_calibration_arithmetic(tmp_path):
    jd, dd = world(tmp_path, compact=(81, 85))                       # two lines in another JSON layout: the full parse
    res = lc.calibration(jd, dd, cfg=CFG)
    s = res["markets"]["AAA"]
    assert res["since"] == res["until"] == "2026-11-02" and res["days"] == 1 and not res["partial"]
    assert s["source"] == "bars" and (s["n"], s["right"], s["wrong"], s["neither"]) == (7, 3, 2, 2)   # bar 88: not known yet
    assert s["hit_pct"] == 60.0                                      # 3 right of 5 graded up or down
    assert s["check"] == [8, 8, 8]                                   # the engine's own counts at closes 84..91, all matched
    table = dict((r["said"], (r["n"], r["avg_said_pct"], r["came_pct"])) for r in s["table"])
    assert table == {"under 45": (1, 44.0, 0.0), "45-50": (1, 49.0, 100.0), "50-55": (3, 50.7, 33.3),
                     "55-60": (1, 56.0, 100.0), "60+": (1, 62.0, 0.0)}
    brier = base = 0.0
    for k, y in OUTCOME.items():
        o = [1.0 if y == lc.UP else 0.0, 1.0 if y == lc.DOWN else 0.0, 1.0 if y == lc.NEITHER else 0.0]
        brier += sum((p - x) ** 2 for p, x in zip(CALLS[k][:3], o))
        base += sum((p - x) ** 2 for p, x in zip((BASE[0], BASE[1], 1.0 - sum(BASE)), o))
    assert s["brier"] == round(brier / 7, 4) and s["brier_base"] == round(base / 7, 4)
    # calls that do not overlap: 80 (known at 84), 84 (known at 86), 86 -> 3 calls, 2 came, 0.56 + 0.49 + 0.50 promised
    assert (s["ind_n"], s["ind_hits"], s["ind_expected"]) == (3, 2, 1.55) and s["verdict"] == "too few"
    assert res["pooled"]["n"] == 7 and res["pooled"]["hit_pct"] == 60.0


def test_date_range_and_replay_never_read(tmp_path):
    jd, dd = world(tmp_path)
    assert [d for d, _p in lc.day_files(jd)] == ["2026-11-02"]       # not the .md, not journal/replay/
    assert lc.calibration(jd, dd, start="2026-11-03", cfg=CFG)["markets"] == {}
    assert lc.calibration(jd, dd, end="2026-11-01", cfg=CFG)["days"] == 0
    assert lc.calibration(jd, dd, start="2026-11-02", end="2026-11-02", cfg=CFG)["markets"]["AAA"]["n"] == 7


def test_no_bars_means_the_engines_own_tallies_and_no_odds_check(tmp_path):
    jd, dd = world(tmp_path, bars=False)
    s = lc.calibration(jd, dd, cfg=CFG)["markets"]["AAA"]
    assert s["source"] == "journal" and "no readable price bars" in s["why"]
    assert (s["n"], s["right"], s["wrong"], s["neither"], s["hit_pct"]) == (7, 3, 2, 2, 60.0)   # the sums of graded_now
    assert s["verdict"] == "n/a" and s["table"] == [] and s["brier"] is None
    (tmp_path / "data" / "aaa_15m.csv").write_text('{\n "version": 1,\n "books": {}\n}\n', encoding="utf-8")   # not a bar file
    assert lc.calibration(jd, dd, cfg=CFG)["markets"]["AAA"]["source"] == "journal"


def test_a_regrade_that_disagrees_with_the_engine_is_not_used(tmp_path):
    wrong = dict((k, (5, 5, 0, 0)) for k in range(80, 110))          # a journal claiming grades the bars do not give
    jd, dd = world(tmp_path, last_bar=109, lines=range(80, 110), graded=wrong)
    s = lc.calibration(jd, dd, cfg=CFG)["markets"]["AAA"]
    assert s["source"] == "journal" and "matched" in s["why"] and s["table"] == []
    right = dict(GRADED)
    right[92] = (1, 0, 0, 1)                                         # with 18 more flat bars, call 88 is NEITHER at 92
    jd2, dd2 = world(tmp_path / "ok", last_bar=109, lines=range(80, 110), graded=right)
    s = lc.calibration(jd2, dd2, cfg=CFG)["markets"]["AAA"]
    assert s["source"] == "bars" and s["n"] == 8 and s["check"] == [26, 26, 26]


def test_verdict_rule():
    assert lc.verdict(99, 10, 55.0, 24.75) == "too few"              # under 100 calls that do not overlap
    assert lc.verdict(100, 40, 55.0, 24.75) == "overconfident"       # promised 55, 40 came: below the 95% interval
    assert lc.verdict(100, 70, 55.0, 24.75) == "underconfident"
    assert lc.verdict(100, 57, 55.0, 24.75) == "about right"
    assert lc.verdict(100, 46, 55.0, 24.75) == "about right" and lc.verdict(100, 45, 55.0, 24.75) == "overconfident"


def test_grade_is_the_engines_triple_barrier():
    flat = (100.0, 101.0, 99.0, 100.0)
    bars = dict((k, flat) for k in range(12))
    order = list(range(12))
    assert lc.grade(bars, order, 0, 3.0, 4) == (lc.NEITHER, 4)       # nothing touched inside the horizon
    assert lc.grade(bars, order, 8, 3.0, 4) is None                  # the horizon is not over and nothing was touched
    bars[3] = (100.0, 104.0, 96.0, 100.0)
    assert lc.grade(bars, order, 0, 3.0, 4) == (lc.NEITHER, 3)       # both barriers inside one bar: order unknown
    bars[3] = (100.0, 103.0, 99.0, 100.0)
    assert lc.grade(bars, order, 1, 3.0, 4) == (lc.UP, 2)            # a touch counts (>=)
    bars[2] = (100.0, 101.0, 97.0, 100.0)
    assert lc.grade(bars, order, 0, 3.0, 4) == (lc.DOWN, 2)          # the first touch wins
    bars[1] = (90.0, 90.5, 89.5, 90.0)                               # the barrier hangs on the NEXT bar's open
    assert lc.grade(bars, order, 0, 3.0, 4) == (lc.UP, 2)
    assert lc.grade(bars, order, 0, None, 4) is None and lc.grade(bars, order, 11, 3.0, 4) is None


def test_bars_are_read_from_the_tail(tmp_path):
    p = tmp_path / "big_15m.csv"
    rows = ["ts_ms,open,high,low,close,volume,taker_buy"]
    rows += ["%d,%.2f,%.2f,%.2f,%.2f,123.456789,61.728394" % (T0 + k * BAR, 60000 + k, 60050 + k, 59950 + k, 60010 + k)
             for k in range(40000)]
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    assert os.path.getsize(str(p)) > 4 * (1 << 19)
    got = lc.load_bars(str(p), T0 + 39000 * BAR)
    assert len(got) == 1000 and min(got) == T0 + 39000 * BAR and got[T0 + 39999 * BAR] == (99999.0, 100049.0, 99949.0, 100009.0)
    assert len(lc.load_bars(str(p), T0 + 20000 * BAR)) == 20000      # further back than the first tail: it reads more
    assert len(lc.load_bars(str(p), 0)) == 40000
    assert lc.load_bars(str(tmp_path / "missing.csv"), 0) == {}


def test_quick_parse_equals_full_parse():
    for k in CALLS:
        raw = line(k).encode("utf-8")
        assert lc._quick(raw) == lc._full(raw)
        assert lc.parse_line(raw) == lc.parse_line(line(k, compact=True).encode("utf-8"))
    asset, ts, call, counts = lc.parse_line(line(87).encode("utf-8"))
    assert (asset, ts, counts) == ("AAA", T0 + 87 * BAR, (0, 0, 0, 0)) and call[3] == -1    # "-0.0": it leaned down
    assert lc.parse_line(b"{broken") is None


# ------------------------------------------------------------------ data health
def page(t, **readings):
    return {"MKT": {"time": t, "cards": [{"card": c.replace("_", " "), "reading": r} for c, r in readings.items()]}}


def closes(n, start=0):
    return ["2026-11-02 %02d:%02d" % divmod(15 * k, 60) for k in range(start, start + n)]


@pytest.mark.parametrize("reading,silent", [
    ("No read.", True), ("", True), (None, True),
    ("No read: no closed USDJPY bar for this session.", True),
    ("No Korea premium read for BTC at this close.", True),
    ("No premium read for the ETH perpetual at this close.", True),
    ("No forecast for this session (live only).", True),
    ("No snapshot for this session (live only).", True),
    ("Money Flow Index (14): no read, USDJPY's price feed carries no usable volume.", True),
    ("A proxy, not a liquidation feed: no open-interest read at this close, so nothing to infer.", True),
    ("No megacap earnings read at this close: the calendar does not cover these days.", True),
    ("No headlines scored for this session. Next US release: Core PPI m/m in 5h. S&P 5-day +0.3 sd.", False),
    ("Volume profile: today so far no read; last 7 days POC 64636 value area 64503-64769.", False),
    ("A proxy, not a liquidation feed: no sharp open-interest drop inside a large bar in the last 4 hours.", False),
    ("RANGE (daily).", False), ("Active now: no named setup.", False),
])
def test_is_silent(reading, silent):
    assert lc.is_silent(reading) is silent


def test_silent_card_alerted_once_then_recovered():
    ts = closes(40)
    h, gone, back = lc.health_update(None, page(ts[0], Feed="Premium +0.02%.", Other="RANGE (daily).", Dead="No read."))
    assert not gone and not back
    alerts = []
    for k in range(1, 12):                                           # eleven closes without a read
        h, gone, back = lc.health_update(h, page(ts[k], Feed="No premium read at this close.", Other="RANGE (daily).", Dead="No read."))
        alerts += [(k, g) for g in gone]
        assert not back
    assert alerts == [(8, ("MKT", "Feed", ts[1], 8))]                # once, at the eighth close, never again
    v = lc.health_view(h)
    assert (v["cards"], v["reading"]) == (2, 1) and v["silent"][0]["card"] == "Feed" and v["silent"][0]["closes"] == 11
    assert [r["card"] for r in v["never"]] == ["Dead"]               # never read here: not counted, never alerted
    h, gone, back = lc.health_update(h, page(ts[12], Feed="Premium +0.01%.", Other="RANGE (daily).", Dead="No read."))
    assert not gone and back == [("MKT", "Feed", ts[1], 11)]
    v = lc.health_view(h)
    assert (v["cards"], v["reading"], v["silent"]) == (2, 2, [])
    # its own rhythm: it came back from an 11-close gap, so the next alarm waits for twice that
    for k in range(13, 13 + 22):
        h, gone, back = lc.health_update(h, page(ts[k], Feed="No read.", Other="RANGE (daily).", Dead="No read."))
        assert bool(gone) == (k == 13 + 21)


def test_closed_market_and_single_misses_raise_no_alarm():
    ts = closes(30)
    h, _g, _b = lc.health_update(None, page(ts[0], Feed="Premium +0.02%."))
    for k in range(1, 4):
        h, gone, _b = lc.health_update(h, page(ts[k], Feed="No read."))
    for _ in range(500):                                             # the weekend: the page is rewritten, no new close
        h, gone, back = lc.health_update(h, page(ts[3], Feed="No read."))
        assert not gone and not back
    assert h["c"]["MKT|Feed"]["n"] == 3 and [r["card"] for r in lc.health_view(h)["missed"]] == ["Feed"]
    for k in range(4, 30):                                           # a live-only read that misses every other close
        h, gone, back = lc.health_update(h, page(ts[k], Feed="No read." if k % 2 else "Premium +0.02%."))
        assert not gone and not back
    assert lc.health_update(h, {"MKT": {"time": None, "cards": None}})[1:] == ([], [])
    assert lc.health_update(h, None)[1:] == ([], [])


def test_a_card_the_engine_drops_is_forgotten():
    h, _g, _b = lc.health_update(None, page("2026-11-02 00:15", Feed="x 1.", Old="y 2."))
    h, _g, _b = lc.health_update(h, page("2026-11-02 00:30", Feed="x 1."))
    assert list(h["c"]) == ["MKT|Feed"]
