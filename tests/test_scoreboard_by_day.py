# -*- coding: utf-8 -*-
"""The by-day read on the forward scoreboard (owner, 24 Nov 2026, after the live audit: "judge by day or by pair of
markets, not by trade"). It is ADDED beside the registered per-trade verdict (reports._stats, research/VERDICT_RULES.md):
these tests hold both halves of that, the new range and the old row left exactly as it was."""
import csv
import json
import math
import os

import pytest

from engine15 import reports


def test_the_registered_row_is_unchanged_and_three_keys_are_added(tmp_path, monkeypatch):
    live = tmp_path / "out" / "live"
    live.mkdir(parents=True)
    monkeypatch.setattr(reports, "ROOT", str(tmp_path))
    monkeypatch.setattr(reports, "SCOREBOARD_JSON", str(live / "scoreboard.json"))
    pnls = [100.0, -50.0, 30.0, 80.0, -20.0, 60.0] * 6                     # 36 trades
    with open(live / "shadow_trades_b_targets_BTCUSDT.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["side", "pnl_usd", "time_in", "time_out"])
        for i, p in enumerate(pnls):
            w.writerow([-1, p, "2026-11-%02d 0%d:00" % (1 + i // 3, i % 3), "2026-11-%02d 1%d:00" % (1 + i // 3, i % 3)])
    out = reports.scoreboard(log=lambda *a: None)
    row = [r for r in out["rows"] if r["book"] == "b_targets"][0]
    old = reports._stats(pnls)
    for k, v in old.items():                                               # every registered key, value for value
        assert row[k] == v
    assert set(row) - set(old) == {"book", "title", "kind", "days", "range90_by_day_usd", "verdict_by_day"}
    assert row["days"] == 12 and out["note_by_day"] == reports.BY_DAY_NOTE
    assert "per trade" in out["note"]                                      # the registered note is still there
    assert json.load(open(live / "scoreboard.json", encoding="utf-8"))["rows"] == out["rows"]


def test_results_that_move_together_within_a_day_widen_the_range():
    # the same 40 results: once spread so each day mixes wins and losses, once with whole days winning or losing
    wins, losses = [120.0] * 24, [-100.0] * 16
    mixed = [(p, "2026-11-%02d" % (1 + i % 10)) for i, p in enumerate(wins + losses)]
    lumped = [(p, "2026-11-%02d" % (1 + i // 4)) for i, p in enumerate(wins + losses)]
    a, b = reports.by_day(mixed), reports.by_day(lumped)
    assert a["days"] == b["days"] == 10
    wa = a["range90_by_day_usd"][1] - a["range90_by_day_usd"][0]
    wb = b["range90_by_day_usd"][1] - b["range90_by_day_usd"][0]
    assert wb > 3 * wa                                                     # whole days moving together: far less certain
    per_trade = reports._stats(wins + losses)                              # the registered read cannot tell them apart
    assert per_trade["verdict"].startswith("ahead") and b["verdict_by_day"].startswith("undecided")
    assert a["verdict_by_day"].startswith("ahead")


def test_the_range_is_the_cluster_formula_with_students_t():
    pairs = [(10.0, "2026-11-01"), (30.0, "2026-11-01"), (-20.0, "2026-11-02"), (40.0, "2026-11-03"), (0.0, "2026-11-03")]
    mean = 12.0
    sums = [(10 - mean) + (30 - mean), -20 - mean, (40 - mean) + (0 - mean)]
    se = math.sqrt(3 / 2.0 * sum(v * v for v in sums)) / 5
    r = reports.by_day(pairs)
    assert r["days"] == 3
    assert r["range90_by_day_usd"] == [round(mean - 2.920 * se, 2), round(mean + 2.920 * se, 2)]      # t, 2 degrees
    assert r["verdict_by_day"] == "too few trades to judge (5 of 30)"


def test_one_day_gives_no_range_and_no_verdict():
    r = reports.by_day([(50.0, "2026-11-01")] * 30)
    assert r == {"days": 1, "range90_by_day_usd": None, "verdict_by_day": "too few days to judge (1 of 2)"}
    assert reports.by_day([]) == {"days": 0, "range90_by_day_usd": None, "verdict_by_day": "no trades yet"}


def test_a_trade_without_a_day_is_a_day_of_its_own():
    r = reports.by_day([(10.0, None), (20.0, None), (30.0, "2026-11-01"), (5.0, "2026-11-01")])
    assert r["days"] == 3


def test_a_trade_closed_in_parts_counts_once_on_its_last_day():
    rows = [(("t1", -1), 100.0, "2026-11-01"), (("t1", -1), 50.0, "2026-11-03"), (None, 7.0, "2026-11-02"),
            (("t2", 1), -30.0, "2026-11-02")]
    got = reports.per_entry_days(rows)
    assert got == [(150.0, "2026-11-03"), (7.0, "2026-11-02"), (-30.0, "2026-11-02")]
    assert [p for p, _d in got] == reports.per_entry([(k, p) for k, p, _d in rows])      # per_entry's results and order


@pytest.mark.parametrize("v,day", [("2026-11-23 13:45", "2026-11-23"), ("2026-11-23 13:45:00+00:00", "2026-11-23"),
                                   ("2026-11-23T13:45:00Z", "2026-11-23"), ("", None), (None, None), ("n/a", None)])
def test_day_of_a_close_time(v, day):
    assert reports._day(v) == day


def test_t_never_tighter_than_the_table():
    assert reports._t90(1) == 6.314 and reports._t90(13) == 1.771 and reports._t90(35) == 1.697
    assert reports._t90(500) == 1.645 and reports._t90(0) is None
