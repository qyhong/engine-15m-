# -*- coding: utf-8 -*-
"""H51 cross-market study: the partner reading uses only partner bars closed by the event bar's close, the
confirmed / divergent / unconfirmed logic is the registered one (checked by hand), the inverse relation flips the side,
and the 'any partner' rule combines as registered."""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

import crossmarket_study as cm  # noqa: E402
import dailybreak_study as db  # noqa: E402
from engine15.sources import adr  # noqa: E402


def bars(n=96 * 60, seed=7, cash=False, shock=None):
    rng = np.random.RandomState(seed)
    base = rng.normal(0, 0.003, n) if shock is None else shock + rng.normal(0, 0.0015, n)
    ret = base + np.where(rng.rand(n) < 0.02, rng.normal(0, 0.02, n), 0.0)
    c = 100.0 * np.exp(np.cumsum(ret))
    o = np.concatenate([[100.0], c[:-1]])
    sp = np.abs(rng.normal(0, 0.002, n)) * c
    idx = pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC")
    df = pd.DataFrame({"open": o, "high": np.maximum(o, c) + sp, "low": np.minimum(o, c) - sp, "close": c,
                       "volume": 1.0, "taker_buy": np.nan}, index=idx)
    if cash:                                                   # a market that shuts: keep 13:30-20:00 UTC
        m = df.index.hour * 60 + df.index.minute
        df = df[(m >= 810) & (m < 1200)]
    return df


def pair(cash_b=False):
    rng = np.random.RandomState(3)
    common = rng.normal(0, 0.0025, 96 * 60)
    return bars(seed=11, shock=common), bars(seed=12, shock=common, cash=cash_b)


def by_hand(B, RB, level, ms_i, want):
    hi, lo = (RB["pdh"], RB["pdl"]) if level == "pday" else (RB["box_hi"], RB["box_lo"])
    bms = RB["ms"]
    w = np.flatnonzero((bms > ms_i - 4 * cm.BAR_MS) & (bms <= ms_i))
    if not len(w):
        return "noread", None
    conf = False
    for j in w:
        if want > 0 and np.isfinite(hi[j]) and RB["c"][j] > hi[j]:
            conf = True
        if want < 0 and np.isfinite(lo[j]) and RB["c"][j] < lo[j]:
            conf = True
    m = want * (RB["c"][w[-1]] - RB["o"][w[0]]) / RB["atr15"][w[-1]]
    if conf:
        return "confirmed", m
    return ("divergent" if m <= -1.0 else "unconfirmed"), m


def test_partner_reading_by_hand_and_window():
    for cash_b in (False, True):
        A, B = pair(cash_b)
        RA, RB = adr.readings(A, box=db.BOX), adr.readings(B, box=db.BOX)
        for level in cm.LEVELS:
            PB = cm.partner_frame(RB, level)
            evs, _x = cm.events(RA, level)
            assert len(evs) > 20
            seen = set()
            for e in evs:
                for r in (1, -1):
                    pr = cm.partner_reading(PB, e["ms"], r * e["side"])
                    st, m = by_hand(B, RB, level, e["ms"], r * e["side"])
                    assert pr["status"] == st, (cash_b, level, e["i"], r)
                    if m is not None:
                        assert abs(pr["move_atr"] - m) < 1e-9
                    seen.add(st)
            assert {"confirmed", "unconfirmed"} <= seen
            if cash_b:
                assert "noread" in seen


def test_partner_never_reads_bars_after_the_event_close():
    for cash_b in (False, True):
        A, B = pair(cash_b)
        RA = adr.readings(A, box=db.BOX)
        RB = adr.readings(B, box=db.BOX)
        for level in cm.LEVELS:
            full = cm.partner_frame(RB, level)
            evs, _x = cm.events(RA, level)
            for e in evs[:: max(1, len(evs) // 30)]:
                cut = pd.Timestamp(e["ms"], unit="ms", tz="UTC")
                Bt = B[B.index <= cut]                       # bars opening at or before the event bar's open
                if len(Bt) < 200:
                    continue
                part = cm.partner_frame(adr.readings(Bt, box=db.BOX), level)
                for want in (1, -1):
                    a, b = cm.partner_reading(full, e["ms"], want), cm.partner_reading(part, e["ms"], want)
                    assert a["status"] == b["status"], (cash_b, level, e["i"])
                    assert (a["move_atr"] is None) == (b["move_atr"] is None)
                    if a["move_atr"] is not None:
                        assert abs(a["move_atr"] - b["move_atr"]) < 1e-9
                # changing every partner bar AFTER the event's close changes nothing
                B2 = B.copy()
                later = B2.index > cut
                B2.loc[later, ["open", "high", "low", "close"]] *= 1.5
                p2 = cm.partner_frame(adr.readings(B2, box=db.BOX), level)
                for want in (1, -1):
                    assert cm.partner_reading(p2, e["ms"], want)["status"] == cm.partner_reading(full, e["ms"], want)["status"]


def test_both_frames_truncated_give_the_same_readings():
    A, B = pair(True)
    dfs = {"BTCUSDT": A, "SPX": B}
    old = dict(cm.PAIRS)
    try:
        cm.PAIRS.clear()
        cm.PAIRS["P5"] = ("SPX", "BTCUSDT", 1)
        for a in dfs:
            for lv in cm.LEVELS:
                t = cm.truncation_check(dfs, a, lv, cuts_frac=(0.5, 0.8))
                assert t["compared"] > 0 and t["mismatched"] == 0, (a, lv, t)
    finally:
        cm.PAIRS.clear()
        cm.PAIRS.update(old)


def test_inverse_relation_flips_the_side():
    A, B = pair()
    RA, RB = adr.readings(A, box=db.BOX), adr.readings(B, box=db.BOX)
    PB = cm.partner_frame(RB, "pday")
    evs, _x = cm.events(RA, "pday")
    partners = [("PX", "B", -1)]
    cm.read_events(evs, {("B", "pday"): PB}, partners, "pday")
    for e in evs:
        want = cm.partner_reading(PB, e["ms"], -e["side"])
        assert e["p_PX"] == want["status"]


def test_combine_rule():
    assert cm.combine(["noread", "noread"]) == "noread"
    assert cm.combine(["confirmed", "noread"]) == "confirmed"
    assert cm.combine(["confirmed", "divergent"]) == "mixed"
    assert cm.combine(["divergent", "unconfirmed"]) == "divergent"
    assert cm.combine(["unconfirmed", "noread"]) == "unconfirmed"
    assert cm.combine(["confirmed", "unconfirmed"]) == "confirmed"


def test_fade_is_the_mirror_and_counts():
    A, _B = pair()
    RA = adr.readings(A, box=db.BOX)
    evs, _x = cm.events(RA, "pday")
    for e in evs:
        if e["hit"] is not None and e["f_hit"] is not None:
            assert e["hit"] + e["f_hit"] <= 1
        if e["hit"] == 1:
            assert e["f_hit"] == 0
    assert cm.N_TESTS == 48 and abs(cm.ALPHA - 0.05 / 48) < 1e-15
    assert len(cm.VARIANTS) == 8
