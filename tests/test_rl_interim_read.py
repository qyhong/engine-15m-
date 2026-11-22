# -*- coding: utf-8 -*-
"""research/rl_interim_read.py: the registered 8-week interim read refuses to show anything before each book's date, and
on or after it prints only the registered words. Planted results only (no record is read)."""
import importlib.util
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("rl_interim_read", os.path.join(ROOT, "research", "rl_interim_read.py"))
ir = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ir)


def _ms(s):
    return int(pd.Timestamp(s, tz="UTC").value // 10**6)


def test_dates_are_the_registered_ones():
    assert ir.READS == {"p5_rlq": ("2026-11-12 04:30", "2027-01-07 04:30"),
                        "p6_mtrend": ("2026-11-13 03:00", "2027-01-08 03:00"),
                        "p6_p4trend": ("2026-11-13 03:00", "2027-01-08 03:00")}
    for b, (s, r) in ir.READS.items():
        assert pd.Timestamp(r) - pd.Timestamp(s) == pd.Timedelta(days=56)
    from engine15 import playbook5, playbook6, playbook8
    assert ir.READS["p5_rlq"][0] == playbook5.REGISTERED and ir.READS["p6_mtrend"][0] == playbook6.REGISTERED
    assert ir.YARD_START == playbook8.REGISTERED
    with open(os.path.join(ROOT, "research", "HYPOTHESES.md"), encoding="utf-8") as fh:
        reg = fh.read()
    for d in ("2027-01-07 04:30", "2027-01-08 03:00"):
        assert d in reg


def test_refuses_before_the_date_and_computes_nothing():
    def boom(book, asset):
        raise AssertionError("computed before the date")
    out = []
    res = ir.run(now_ms=_ms("2027-01-07 04:15"), out=out.append, compute_fn=boom)
    assert res == {"p5_rlq": None, "p6_mtrend": None, "p6_p4trend": None}
    assert len(out) == 3 and all("nothing is shown before then" in s for s in out)
    assert not any("ahead of" in s or "behind" in s or "level with" in s for s in out)


def test_on_the_date_prints_only_the_registered_words():
    calls = []

    def planted(book, asset):
        calls.append((book, asset))
        r = {"BTCUSDT": 7.3, "ETHUSDT": -2.0}[asset]
        lines = [ir.line(book, asset, r, "buy-and-hold", -13.0, ir.READS[book][0], ir.READS[book][1])]
        if book.startswith("p6_"):
            lines.append(ir.line(book, asset, r, "the momentum yardstick p8_mom", r - 0.4, ir.YARD_START, ir.READS[book][1]))
        return {"lines": lines, "closed_trades": 3,
                "split": {"agent_gross_usd": -10.0, "fallback_gross_usd": 800.0, "costs_usd": 20.0, "net_usd": 770.0,
                          "agent_seed_bars_pct": 20.0}}
    out = []
    res = ir.run(now_ms=_ms("2027-01-07 04:30"), out=out.append, compute_fn=planted)
    assert res["p6_mtrend"] is None and res["p6_p4trend"] is None and len(res["p5_rlq"]) == 2   # p6 is a day later
    assert {b for b, _ in calls} == {"p5_rlq"}
    reads = [s for s in out if s.startswith("Interim read")]
    assert reads[0] == ("Interim read (8 weeks; not a verdict): p5_rlq BTC +7.30% vs buy-and-hold -13.00% over "
                        "2026-11-12 04:30 to 2027-01-07 04:30 UTC: ahead of buy-and-hold by 20.30 points.")
    out2 = []
    ir.run(now_ms=_ms("2027-02-01 00:00"), out=out2.append, compute_fn=planted)
    assert any("level with the momentum yardstick p8_mom by 0.40 points" in s for s in out2)
    assert all("NOT passed" in s for s in out2 if "closed trades" in s)
    low = " ".join(out + out2).lower()
    for w in ("passed:", "proven", "significant", "edge", "beats", "works"):
        assert w not in low


def test_words():
    assert ir.words(5.0, 4.01) == "level with" and ir.words(5.0, 3.99) == "ahead of" and ir.words(3.0, 4.5) == "behind"
