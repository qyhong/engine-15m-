# -*- coding: utf-8 -*-
"""tests for engine15/playbook3.py: P6 VWAP, P7 session plays, P8 fair value gap, P9 cascades, P10 round
numbers, P11 releases, P12 the crypto US-open range.

Hand-made bars that fire and do not fire each book; session clocks across daylight saving; the fill rules
(next open, stop first inside one bar); fees and the minimum stop; no position across a market break; and
that no trade changes when later bars are added (no look-ahead)."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import data, extdata  # noqa: E402
from engine15 import playbook3 as pb  # noqa: E402

BAR = pd.Timedelta(minutes=15)


def frame(start, rows, volume=100.0, taker=None):
    """rows: (open, high, low, close) tuples or close floats (a bar of +-0.05) -> gapless 15m frame from `start` UTC."""
    rows = [(r, r + 0.05, r - 0.05, r) if np.isscalar(r) else r for r in rows]
    idx = pd.date_range(pd.Timestamp(start, tz="UTC"), periods=len(rows), freq="15min", name="open_time")
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx, dtype=float)
    df["volume"] = volume
    df["taker_buy"] = df["volume"] / 2.0 if taker is None else taker
    return df


def wiggle(n, base=100.0, amp=0.1):
    """n bars whose closes alternate base - amp / base + amp."""
    return [base + (amp if i % 2 else -amp) for i in range(n)]


def utc(ms):
    return str(pd.Timestamp(int(ms), unit="ms", tz="UTC"))[:16]


def run_rows(book, df, asset, p, now_ms=None, events=None, bias=None):
    ctx = pb.Ctx(df, asset, now_ms, events=events, funding=pd.Series(dtype=float))
    if bias is not None:
        ctx._c["bias"] = np.full(ctx.n, bias)
    S, T = pb.run(book, ctx, p)
    return ctx, S, T


def at(ctx, S, T, j=0):
    k = T["k"][j]
    return utc(ctx.ms[S["i"][k]]), int(S["side"][k]), float(S["stop"][k])


# ---------------------------------------------------------------- P6 VWAP
FADE = {"mode": "fade", "k": 2.0, "entry": "close", "target": "vwap", "regime": "adx"}


def vwap_day(spike, after):
    """Gold: a quiet previous day, then a day whose first 3 hours wiggle around 100, a spike bar, then `after`."""
    return frame("2026-01-13 00:00", [100.0] * 96 + wiggle(12) + [spike] + after)


def test_vwap_fade_fires_beyond_the_band_and_reaches_vwap():
    df = vwap_day((100.0, 101.2, 99.95, 101.0), [(100.9, 100.95, 100.5, 100.6), (100.6, 100.6, 99.9, 100.0)] + [100.0] * 6)
    ctx, S, T = run_rows("p6_vwap", df, "XAUUSD", FADE)
    when, side, stop = at(ctx, S, T)
    assert when == "2026-01-14 03:00" and side == -1
    vw, _sd, _n = ctx.vwap()
    k = T["k"][0]
    assert stop == pytest.approx(101.2 + pb.PAD_ATR * ctx.atr1h()[S["i"][k]])
    assert T["entry"][0] == pytest.approx(100.9) and T["t2"][0] == pytest.approx(vw[S["i"][k]])
    assert pb.WHY[T["why"][0]] == "T2" and T["exit"][0] == pytest.approx(vw[S["i"][k]])


def test_vwap_fade_does_not_fire_inside_the_band_or_in_a_trend():
    df = vwap_day((100.0, 100.2, 99.95, 100.12), [100.0] * 8)
    ctx, S, T = run_rows("p6_vwap", df, "XAUUSD", FADE)
    assert len(S["i"]) == 0
    df = vwap_day((100.0, 101.2, 99.95, 101.0), [100.0] * 8)
    ctx, S, T = run_rows("p6_vwap", df, "XAUUSD", dict(FADE, regime="nobias"), bias=1)   # a bias on: not a range
    assert len(S["i"]) == 0


def test_vwap_fade_back_inside_waits_for_the_close_back():
    df = vwap_day((100.0, 101.2, 99.95, 101.0), [(101.0, 101.4, 100.9, 101.3), (101.3, 101.35, 100.3, 100.4),
                                                 (100.4, 100.45, 100.0, 100.1)] + [100.0] * 6)
    ctx, S, T = run_rows("p6_vwap", df, "XAUUSD", dict(FADE, entry="back"))
    when, side, stop = at(ctx, S, T)
    assert when == "2026-01-14 03:30" and side == -1
    assert stop == pytest.approx(101.4 + pb.PAD_ATR * ctx.atr1h()[S["i"][T["k"][0]]])     # the excursion's high
    assert pb.WHY[T["why"][0]] == "T2"
    # the next open already beyond VWAP: the target is behind the entry, so no trade
    df = vwap_day((100.0, 101.2, 99.95, 101.0), [(101.0, 101.4, 100.9, 101.3), (101.3, 101.35, 100.3, 100.4)] + [100.0] * 6)
    ctx, S, T = run_rows("p6_vwap", df, "XAUUSD", dict(FADE, entry="back"))
    assert len(S["i"]) == 1 and len(T["k"]) == 0


def test_vwap_reclaim_buys_the_first_tag_with_the_bias():
    rows = [100.0] * 96 + [100.0 + 0.1 * i for i in range(12)] + [(101.2, 101.25, 100.3, 101.15)] + [101.2] * 8
    p = {"mode": "reclaim", "stop": "bar", "target": "2R"}
    ctx, S, T = run_rows("p6_vwap", frame("2026-01-13 00:00", rows), "XAUUSD", p, bias=1)
    vw, _sd, _n = ctx.vwap()
    i = 96 + 12
    assert vw[i] > 100.3 and vw[i] < 101.15
    assert [int(x) for x in S["i"]] == [i] and S["side"][0] == 1
    ctx, S, T = run_rows("p6_vwap", frame("2026-01-13 00:00", rows), "XAUUSD", p, bias=0)
    assert len(S["i"]) == 0


# ---------------------------------------------------------------- P7 session plays
def test_asian_range_and_london_open_follow_uk_daylight_saving():
    winter = frame("2026-01-14 00:00", [100.0] * 40)
    summer = frame("2026-07-15 00:00", [100.0] * 40)
    for df, open_utc, bars in ((winter, "2026-01-14 08:00", 32), (summer, "2026-07-15 07:00", 28)):
        ctx = pb.Ctx(df, "XAUUSD")
        L = ctx.london_asia()
        assert [utc(x) for x in L["start"]] == [open_utc]
        assert int(L["a"][0]) == bars                                  # the Asian range = every bar from 00:00 UTC
    sat = pb.Ctx(frame("2026-01-17 00:00", [100.0] * 60), "XAUUSD")   # Saturday: no London session
    assert len(sat.london_asia()["a"]) == 0


JUDAS = {"play": "judas", "window": 8, "target": "opp"}


def gold_london(after, day="2026-01-14", open_bars=32):
    """The previous afternoon flat, an Asian session wiggling 99.9-100.1 (range 99.85-100.15), then `after` from the London open."""
    prev = frame(str(pd.Timestamp(day) - pd.Timedelta(hours=10))[:16], [100.0] * 40)
    today = frame(day + " 00:00", wiggle(open_bars) + after)
    return pd.concat([prev, today])


def test_london_false_move_fades_the_take_out():
    after = [(100.0, 100.6, 99.95, 100.5),          # 08:00 takes out the Asian high
             (100.5, 100.55, 100.0, 100.05),        # 08:15 closes back inside: decide
             (100.05, 100.1, 99.95, 100.0), (100.0, 100.0, 99.7, 99.75)] + [99.75] * 4
    ctx, S, T = run_rows("p7_session", gold_london(after), "XAUUSD", JUDAS)
    when, side, stop = at(ctx, S, T)
    assert when == "2026-01-14 08:15" and side == -1
    assert stop == pytest.approx(100.6 + pb.PAD_ATR * ctx.atr1h()[S["i"][T["k"][0]]])
    assert T["t2"][0] == pytest.approx(99.85)                          # the far side of the Asian range
    assert pb.WHY[T["why"][0]] == "T2" and T["exit"][0] == pytest.approx(99.85)


def test_london_false_move_does_not_fire_without_the_reversal_or_late():
    after = [(100.0, 100.6, 99.95, 100.5)] + [100.5] * 10           # stays out: a breakout, not a false move
    ctx, S, T = run_rows("p7_session", gold_london(after), "XAUUSD", JUDAS)
    assert len(S["i"]) == 0
    late = [100.0] * 9 + [(100.0, 100.6, 99.95, 100.5), (100.5, 100.55, 100.0, 100.05)] + [100.0] * 4
    ctx, S, T = run_rows("p7_session", gold_london(late), "XAUUSD", JUDAS)   # the take-out came after 8 bars
    assert len(S["i"]) == 0
    ctx, S, T = run_rows("p7_session", gold_london(after), "SPX", JUDAS)
    assert len(S["i"]) == 0                                            # not an S&P play


def test_london_false_move_in_summer_uses_07_utc():
    after = [(100.0, 100.6, 99.95, 100.5), (100.5, 100.55, 100.0, 100.05)] + [100.0] * 6
    ctx, S, T = run_rows("p7_session", gold_london(after, "2026-07-15", 28), "XAUUSD", JUDAS)
    assert at(ctx, S, T)[0] == "2026-07-15 07:15"


def test_asian_range_breakout_and_stop_first():
    after = [(100.0, 100.6, 99.95, 100.5), (100.55, 100.6, 100.5, 100.55)] + [100.55] * 4
    p = {"play": "abo", "stop": "far", "target": "2R"}
    ctx, S, T = run_rows("p7_session", gold_london(after), "XAUUSD", p)
    when, side, stop = at(ctx, S, T)
    assert when == "2026-01-14 08:00" and side == 1 and stop == pytest.approx(99.85)
    assert T["entry"][0] == pytest.approx(100.55) and T["t2"][0] == pytest.approx(100.55 + 2 * 0.7)
    # one bar through both the stop and the target: the stop counts
    after = [(100.0, 100.6, 99.95, 100.5), (100.55, 103.0, 99.0, 100.0)] + [100.0] * 4
    ctx, S, T = run_rows("p7_session", gold_london(after), "XAUUSD", p)
    assert pb.WHY[T["why"][0]] == "STOP" and T["exit"][0] == pytest.approx(99.85)
    fee = 0.0002
    gross = (99.85 / 100.55 - 1) * 10000
    fees = fee * 10000 * (1 + 99.85 / 100.55)
    assert T["fees"][0] == pytest.approx(fees) and T["pnl"][0] == pytest.approx(gross - fees)
    assert T["r"][0] == pytest.approx((gross - fees) / (10000 * 0.7 / 100.55)) and T["r"][0] < -1.0
    ctx, S, T = run_rows("p7_session", gold_london(after), "XAGUSD", p)
    assert len(S["i"]) == 0                                            # the Asian breakout is gold and USDJPY only


def test_asian_breakout_is_flat_eight_hours_after_the_london_open():
    after = [(100.0, 100.6, 99.95, 100.5)] + [100.55] * 40
    ctx, S, T = run_rows("p7_session", gold_london(after), "XAUUSD", {"play": "abo", "stop": "far", "target": "3R"})
    assert pb.WHY[T["why"][0]] == "TIME" and utc(T["exit_ms"][0]) == "2026-01-14 16:00"


def test_new_york_drift_weekdays_only_and_minimum_stop():
    rows = wiggle(96 * 3, amp=1.0)                                     # Thursday to Saturday, hourly range about 2
    df = frame("2026-01-15 00:00", rows)
    p = {"play": "drift", "hour": 16, "stop_atr": 1.5}
    ctx, S, T = run_rows("p7_session", df, "BTCUSDT", p)
    assert [utc(ctx.ms[i]) for i in S["i"]] == ["2026-01-15 15:45", "2026-01-16 15:45"]   # Thursday, Friday; not Saturday
    assert (S["side"] == 1).all() and len(T["k"]) == 2
    assert pb.WHY[T["why"][0]] == "TIME" and utc(T["exit_ms"][0]) == "2026-01-15 20:00"   # 4 hours
    quiet = frame("2026-01-15 00:00", wiggle(96 * 2, amp=0.05))         # a 1.5-ATR stop under 4 fees (0.40%): not traded
    ctx, S, T = run_rows("p7_session", quiet, "BTCUSDT", p)
    assert len(S["i"]) == 2 and len(T["k"]) == 0
    ctx, S, T = run_rows("p7_session", df, "XAUUSD", p)
    assert len(S["i"]) == 0


# ---------------------------------------------------------------- P8 fair value gap
FVG = {"zone": "fvg", "k": 0.5, "target": "2R", "filter": None}


def fvg_bars(back):
    pre = wiggle(80)
    imp = [(100.0, 100.1, 99.9, 100.0), (100.0, 101.0, 99.95, 100.95), (100.95, 101.5, 100.6, 101.4),
           (101.4, 101.8, 101.3, 101.7)]
    return frame("2026-01-14 00:00", pre + imp + [back] + [(101.0, 103.5, 100.95, 103.4)] + [103.4] * 6)


def test_fvg_fires_on_the_return_and_holds():
    ctx, S, T = run_rows("p8_fvg", fvg_bars((101.6, 101.65, 100.5, 100.7)), "XAUUSD", FVG)
    when, side, stop = at(ctx, S, T)
    assert when == "2026-01-14 21:00" and side == 1                   # the 85th bar: the return into the gap
    assert stop == pytest.approx(100.1 - pb.PAD_ATR * ctx.atr1h()[S["i"][T["k"][0]]])
    assert S["x1"][T["k"][0]] == pytest.approx(100.6) and S["x2"][T["k"][0]] == pytest.approx(100.1)
    assert pb.WHY[T["why"][0]] == "T2"
    ctx, S, T = run_rows("p8_fvg", fvg_bars((101.6, 101.65, 100.5, 100.7)), "XAUUSD", dict(FVG, target="ext"))
    k = T["k"][0]
    assert T["t1"][0] == pytest.approx(101.8)                          # half at the impulse extreme
    assert S["mode"][k] == pb.M_SPLIT


def test_fvg_does_not_fire_when_the_return_closes_through_or_the_gap_is_small():
    ctx, S, T = run_rows("p8_fvg", fvg_bars((101.6, 101.65, 99.7, 99.8)), "XAUUSD", FVG)
    assert not np.isclose(S["x1"], 100.6).any()                        # that gap gives no trade (a later gap may)
    ctx, S, T = run_rows("p8_fvg", fvg_bars((101.6, 101.65, 100.5, 100.7)), "XAUUSD", dict(FVG, k=50.0))
    assert len(S["i"]) == 0


def test_order_block_zone_is_the_last_opposite_candle():
    pre = wiggle(80)
    imp = [(100.2, 100.25, 99.8, 99.9), (99.9, 100.1, 99.85, 100.0), (100.0, 101.0, 99.95, 100.95), (100.95, 101.5, 100.6, 101.4),
           (101.4, 101.8, 101.3, 101.7), (101.6, 101.65, 100.5, 100.7),       # back in the gap: not yet the block
           (100.7, 100.75, 100.0, 100.05)] + [100.05] * 6                    # into the block (99.8-100.25), closes above 99.8
    df = frame("2026-01-14 00:00", pre + imp)
    ctx, S, T = run_rows("p8_fvg", df, "XAUUSD", dict(FVG, zone="ob"))
    k = int(np.flatnonzero(S["side"] == 1)[0])
    assert S["x1"][k] == pytest.approx(100.25) and S["x2"][k] == pytest.approx(99.8)   # the down candle before the impulse
    assert utc(ctx.ms[S["i"][k]]) == utc(df.index[80 + 6].value // 10**6)


# ---------------------------------------------------------------- P9 cascades
CASC = {"mode": "cont", "x": 2.0, "vol": 1.5, "target": "2R", "filter": None}


def cascade_bars(vol=400.0, share=0.25, after=None):
    pre = wiggle(200)
    n = len(pre)
    drop = [(100.0, 100.05, 99.3, 99.4)]
    after = after if after is not None else [(99.4, 99.45, 98.8, 98.9), (98.9, 99.0, 98.5, 98.6)] + [98.6] * 20
    df = frame("2026-01-10 00:00", pre + drop + after)
    df.iloc[n, df.columns.get_loc("volume")] = vol
    df.iloc[n, df.columns.get_loc("taker_buy")] = vol * share
    return df, n


def test_cascade_continuation_fires_on_the_first_bar():
    df, n = cascade_bars()
    ctx, S, T = run_rows("p9_cascade", df, "BTCUSDT", CASC)
    assert [int(x) for x in S["i"]] == [n] and S["side"][0] == -1
    assert S["stop"][0] == pytest.approx(100.15)                       # where the move began (the 4-bar high)


def test_cascade_needs_volume_and_one_sided_takers_and_crypto():
    df, n = cascade_bars(vol=100.0)
    assert len(run_rows("p9_cascade", df, "BTCUSDT", CASC)[1]["i"]) == 0
    df, n = cascade_bars(share=0.5)
    assert len(run_rows("p9_cascade", df, "BTCUSDT", CASC)[1]["i"]) == 0
    df, n = cascade_bars()
    assert len(run_rows("p9_cascade", df, "XAUUSD", CASC)[1]["i"]) == 0


def test_cascade_bounce_waits_for_the_reversal_bar():
    after = [(99.4, 99.45, 98.8, 98.9), (98.9, 99.0, 98.5, 98.6), (98.6, 99.2, 98.55, 99.1)] + [99.1] * 20
    df, n = cascade_bars(after=after)
    p = dict(CASC, mode="bounce")
    ctx, S, T = run_rows("p9_cascade", df, "BTCUSDT", p)
    assert [int(x) for x in S["i"]] == [n + 3] and S["side"][0] == 1   # 99.1 closed above the previous high 99.0
    assert S["stop"][0] == pytest.approx(98.5 - pb.PAD_ATR * ctx.atr1h()[n + 3])
    ctx, S, T = run_rows("p9_cascade", df, "BTCUSDT", dict(p, target="half"))
    assert T["t2"][0] == pytest.approx((100.15 + 98.5) / 2)            # half the cascade back


# ---------------------------------------------------------------- P10 round numbers
def test_round_number_rejection_on_the_first_touch():
    rows = wiggle(120, base=4040.0, amp=1.0) + [(4045.0, 4051.0, 4044.0, 4046.0)] + [(4046.0, 4046.5, 4040.0, 4041.0)] + [4041.0] * 20
    p = {"mode": "reject", "grid": "base", "target": "2R"}
    ctx, S, T = run_rows("p10_round", frame("2026-01-14 00:00", rows), "XAUUSD", p)
    assert [int(x) for x in S["i"]] == [120] and S["side"][0] == -1 and S["x1"][0] == pytest.approx(4050.0)
    assert S["stop"][0] == pytest.approx(4051.0 + pb.PAD_ATR * ctx.atr1h()[120])
    rows2 = rows[:60] + [(4045.0, 4051.0, 4044.0, 4046.0)] + rows[60:]     # touched an hour or two earlier: not the first
    ctx, S, T = run_rows("p10_round", frame("2026-01-14 00:00", rows2), "XAUUSD", p)
    assert 121 not in [int(x) for x in S["i"]]


def test_round_number_magnet_first_approach():
    rows = wiggle(120, base=4037.0, amp=3.0) + [(4037.0, 4045.5, 4036.5, 4045.0), (4045.0, 4051.0, 4044.5, 4050.5)] + [4050.0] * 10
    p = {"mode": "magnet", "grid": "base", "y": 1.0, "stop": "full"}
    ctx, S, T = run_rows("p10_round", frame("2026-01-14 00:00", rows), "XAUUSD", p)
    assert [int(x) for x in S["i"]] == [120] and S["side"][0] == 1
    assert T["t2"][0] == pytest.approx(4050.0) and S["stop"][0] == pytest.approx(4045.0 - 5.0)
    assert pb.WHY[T["why"][0]] == "T2"


# ---------------------------------------------------------------- P11 releases
def release_bars(bar):
    return frame("2026-01-13 13:30", [100.0] * 96 + [bar] + [100.6] * 20)


EVENTS = [(int(pd.Timestamp("2026-01-14 13:30", tz="UTC").value // 10**6), 1, "NFP Dec 2025")]


def test_release_follow_and_fade():
    df = release_bars((100.0, 100.7, 99.9, 100.6))
    ctx, S, T = run_rows("p11_release", df, "XAUUSD", {"mode": "follow", "min_atr": 0.5}, events=EVENTS)
    when, side, stop = at(ctx, S, T)
    assert when == "2026-01-14 13:30" and side == 1 and stop == pytest.approx(99.9)
    assert pb.WHY[T["why"][0]] == "TIME" and utc(T["exit_ms"][0]) == "2026-01-14 17:45"   # 16 bars after the 13:45 entry
    ctx, S, T = run_rows("p11_release", df, "XAUUSD", {"mode": "fade", "min_atr": 0.5}, events=EVENTS)
    assert S["side"][0] == -1 and T["t2"][0] == pytest.approx(100.0)
    small = release_bars((100.0, 100.08, 99.95, 100.04))
    ctx, S, T = run_rows("p11_release", small, "XAUUSD", {"mode": "follow", "min_atr": 0.5}, events=EVENTS)
    assert len(S["i"]) == 0
    ctx, S, T = run_rows("p11_release", df, "XAUUSD", {"mode": "follow", "min_atr": 0.5}, events=[])
    assert len(S["i"]) == 0


def test_release_calendar_skips_cpi():
    ctx = pb.Ctx(frame("2026-05-01 00:00", [100.0] * 10), "BTCUSDT")
    ms, kinds, titles = ctx.events()
    assert len(ms) and not any("CPI" in t.upper() for t in titles)
    assert set(kinds) <= {0, 1, 2}


# ---------------------------------------------------------------- P12 crypto US-open range
def test_us_open_range_follows_new_york_daylight_saving():
    for day, open_utc in (("2026-01-14", "14:30"), ("2026-07-15", "13:30")):
        o = pd.Timestamp(day + " " + open_utc, tz="UTC")
        pre = frame(str(o - pd.Timedelta(hours=6))[:16], [100.0] * 24)
        orr = frame(str(o)[:16], [(100.0, 101.0, 99.5, 100.5), (100.5, 100.8, 99.0, 100.0), (100.0, 101.6, 99.9, 101.5)]
                    + [(101.6, 107.0, 101.5, 106.9)] + [106.9] * 10)       # 2R = 101.6 + 2 x 2.6 = 106.8
        ctx, S, T = run_rows("p12_orb_us", pd.concat([pre, orr]), "BTCUSDT", pb.RULES["p12_orb_us"], bias=1)
        assert [utc(ctx.ms[i]) for i in S["i"]] == [str(o + pd.Timedelta(minutes=30))[:16]]
        assert S["side"][0] == 1 and S["stop"][0] == pytest.approx(99.0)
        assert pb.WHY[T["why"][0]] == "T2"
        ctx, S, T = run_rows("p12_orb_us", pd.concat([pre, orr]), "BTCUSDT", pb.RULES["p12_orb_us"], bias=-1)
        assert len(S["i"]) == 0                                        # against the bias: no trade
        ctx, S, T = run_rows("p12_orb_us", pd.concat([pre, orr]), "SPX", pb.RULES["p12_orb_us"], bias=1)
        assert len(S["i"]) == 0
    assert pb.BOOKS["p12_orb_us"].get("forward_only") is True


# ---------------------------------------------------------------- market breaks, waiting
def test_no_position_is_held_through_a_market_break():
    df, n = cascade_bars(after=[(99.4, 99.45, 99.0, 99.1), (99.1, 99.2, 99.0, 99.1)])
    later = frame(str(df.index[-1] + pd.Timedelta(hours=10))[:16], [99.1] * 30)
    ctx, S, T = run_rows("p9_cascade", pd.concat([df, later]), "BTCUSDT", dict(CASC, target="3R"))
    assert pb.WHY[T["why"][0]] == "TIME"
    assert utc(T["exit_ms"][0]) == utc(df.index[-1].value // 10**6 + pb.BAR_MS)


def test_waiting_then_open():
    df, n = cascade_bars(after=[])
    ctx, S, T = run_rows("p9_cascade", df, "BTCUSDT", CASC)
    assert T["status"][0] == pb.ST_WAIT
    df, n = cascade_bars(after=[(99.4, 99.45, 99.2, 99.3)])
    ctx, S, T = run_rows("p9_cascade", df, "BTCUSDT", CASC)
    assert T["status"][0] == pb.ST_OPEN and T["entry"][0] == pytest.approx(99.4)


# ---------------------------------------------------------------- no look-ahead
def walk(start, n, seed, asset="BTCUSDT", vol=0.004):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(pd.Timestamp(start, tz="UTC"), periods=n, freq="15min", name="open_time")
    if asset == "SPX":
        idx = idx[extdata.open_mask("SPX", idx)]
    elif asset in ("XAUUSD", "XAGUSD", "USDJPY"):
        idx = idx[extdata.open_mask(asset, idx, calendar=False)]
    m = len(idx)
    jump = np.zeros(m)
    breaks = np.flatnonzero(np.diff(data.to_ms(idx)) > 3 * pb.HOUR_MS) + 1
    jump[breaks] = rng.normal(0, 0.004, len(breaks))
    ret = rng.normal(0, vol, m)
    shock = rng.random(m) < 0.004                                      # now and then a violent bar on heavy volume
    ret[shock] *= 10
    c = 100.0 * np.exp(np.cumsum(ret + jump))
    o = np.r_[100.0, c[:-1]] * np.exp(jump + rng.normal(0, vol / 4, m))
    h = np.maximum(o, c) * np.exp(np.abs(rng.normal(0, vol, m)))
    l = np.minimum(o, c) * np.exp(-np.abs(rng.normal(0, vol, m)))
    v = rng.uniform(50, 150, m) * np.where(shock, 6.0, 1.0)
    share = np.where(shock, np.where(ret > 0, 0.7, 0.3), rng.uniform(0.4, 0.6, m))
    df = pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": v}, index=idx)
    df["taker_buy"] = v * share
    return df


def _key(ctx, S, T, j):
    k = T["k"][j]
    return (int(ctx.ms[S["i"][k]]), int(S["side"][k]), round(float(S["stop"][k]), 9))


WALK_EVENTS = [(int(d.value // 10**6), i % 2, "event %d" % i)       # every Wednesday 13:30 UTC (a made-up calendar)
               for i, d in enumerate(pd.date_range("2025-10-01 13:30", "2026-04-15", freq="W-WED", tz="UTC"))]

CASES = [("p6_vwap", "BTCUSDT", {"mode": "fade", "k": 2.0, "entry": "back", "target": "vwap", "regime": "adx"}),
         ("p6_vwap", "USDJPY", {"mode": "reclaim", "stop": "atr", "target": "3R"}),
         ("p7_session", "XAUUSD", {"play": "judas", "window": 12, "target": "opp"}),
         ("p7_session", "USDJPY", {"play": "abo", "stop": "mid", "target": "2R"}),
         ("p7_session", "ETHUSDT", {"play": "drift", "hour": 18, "stop_atr": 3.0}),
         ("p8_fvg", "SPX", {"zone": "fvg", "k": 0.5, "target": "ext", "filter": None}),
         ("p8_fvg", "BTCUSDT", {"zone": "ob", "k": 0.5, "target": "2R", "filter": None}),
         ("p9_cascade", "BTCUSDT", {"mode": "cont", "x": 2.0, "vol": 1.5, "target": "2R", "filter": None}),
         ("p9_cascade", "ETHUSDT", {"mode": "bounce", "x": 2.0, "vol": 1.5, "target": "half", "filter": None}),
         ("p10_round", "XAGUSD", {"mode": "magnet", "grid": "base", "y": 1.0, "stop": "full"}),
         ("p10_round", "BTCUSDT", {"mode": "reject", "grid": "base", "target": "2R"}),
         ("p11_release", "XAUUSD", {"mode": "follow", "min_atr": 0.2}),
         ("p11_release", "ETHUSDT", {"mode": "fade", "min_atr": 0.2}),
         ("p12_orb_us", "BTCUSDT", [{"orb": "us_open"}])]

STEPS = {"XAGUSD": 1.0, "BTCUSDT": 1.0}                                # walks start at 100: small round steps so they trade


@pytest.mark.parametrize("book,asset,p", CASES)
def test_truncated_bars_give_the_same_trades(book, asset, p, monkeypatch):
    if book == "p10_round":
        monkeypatch.setitem(pb.ROUND_STEPS["base"], asset, STEPS[asset])
    vol = 0.0015 if asset in ("SPX", "XAUUSD", "USDJPY", "XAGUSD") else 0.004
    df = walk("2025-10-01", 96 * 200, seed=sum(map(ord, book + asset)), asset=asset, vol=vol)
    ev = WALK_EVENTS if book == "p11_release" else None
    bias = 1 if book == "p12_orb_us" else None
    full_ctx, fS, fT = run_rows(book, df, asset, p, events=ev, bias=bias)
    assert len(fT["k"]) >= (2 if book == "p11_release" else 4), "the case should trade"
    for frac in (0.55, 0.8):
        cut = df.index[int(len(df) * frac)]
        part = df[df.index <= cut]
        ctx, S, T = run_rows(book, part, asset, p, events=ev, bias=bias)
        cut_close = int(cut.value // 10**6) + pb.BAR_MS
        full = dict((_key(full_ctx, fS, fT, j), j) for j in range(len(fT["k"])))
        for j in range(len(T["k"])):
            if T["status"][j] == pb.ST_WAIT:
                continue
            key = _key(ctx, S, T, j)
            assert key in full, "a trade seen on fewer bars must exist on all bars"
            fj = full[key]
            if T["status"][j] == pb.ST_CLOSED:
                assert fT["status"][fj] == pb.ST_CLOSED
                assert fT["exit"][fj] == pytest.approx(T["exit"][j]) and fT["r"][fj] == pytest.approx(T["r"][j])
                assert T["exit_ms"][j] <= cut_close
        mine = set(_key(ctx, S, T, j) for j in range(len(T["k"])))
        for key, fj in full.items():
            if fT["status"][fj] == pb.ST_CLOSED and fT["exit_ms"][fj] <= cut_close - pb.BAR_MS and key[0] + pb.BAR_MS <= cut_close:
                assert key in mine


def test_step_rows_with_now_ms_match_truncated_bars():
    bars = {"BTCUSDT": walk("2026-06-01", 96 * 170, seed=5),
            "XAUUSD": walk("2026-06-01", 96 * 170, seed=6, asset="XAUUSD", vol=0.0015),
            "SPX": walk("2026-06-01", 96 * 170, seed=7, asset="SPX", vol=0.0015)}
    now = int(pd.Timestamp("2026-11-16 18:00", tz="UTC").value // 10**6)
    a = pb.step(bars, now_ms=now)
    cut = dict((k, v[v.index + BAR <= pd.Timestamp(now, unit="ms", tz="UTC")]) for k, v in bars.items())
    b = pb.step(cut)
    assert a == b and len(a) > 0
    later = pb.step(bars, now_ms=now + 2 * pb.DAY_MS)
    seen = dict(((r["book"], r["asset"], r["setup_utc"]), r) for r in later)
    for r in a:
        if r["status"] == "CLOSED":
            assert seen[(r["book"], r["asset"], r["setup_utc"])] == r
    assert all(r["setup_utc"] >= "2026-11-11" for r in a)
    keys = {"book", "asset", "status", "side", "setup_utc", "entry_utc", "entry", "stop", "target_1", "target_2",
            "exit_utc", "exit", "why_out", "r", "pnl_usd", "fees_usd", "text"}
    for r in a:
        assert keys <= set(r)
        assert r["status"] in ("WAITING", "OPEN", "CLOSED") and r["side"] in (1, -1)
        assert r["book"] in pb.BOOKS and r["asset"] in pb.BOOKS[r["book"]]["assets"]
        if r["status"] == "CLOSED":
            assert r["why_out"] in ("STOP", "T1", "T2", "TIME")
    blk = pb.page_block(a)
    assert set(blk) == set(pb.BOOKS)
    for b_ in blk.values():
        assert {"title", "hypothesis", "open", "recent", "totals", "rule"} <= set(b_)
        assert len(b_["recent"]) <= 5


def test_book_ids_do_not_clash_with_the_other_modules():
    from engine15 import playbook, playbook2
    assert not set(pb.BOOKS) & (set(playbook.BOOKS) | set(playbook2.BOOKS))
    assert [pb.BOOKS[b]["hypothesis"] for b in sorted(pb.BOOKS, key=lambda x: int(x[1:].split("_")[0]))] == \
        ["H%d" % i for i in range(11, 18)]
