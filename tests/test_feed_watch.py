# -*- coding: utf-8 -*-
"""feed_watch: a market is stale when STALE_BARS bars are due and missing while its whole group is open (27 Nov 2026)."""
import pandas as pd

from engine15 import feed_watch as fw
from engine15 import market_calendar

M = 60 * 1000


def ms(t):
    return int(pd.Timestamp(t, tz="UTC").timestamp() * 1000)


def test_crypto_counts_every_slot():
    bar = ms("2026-11-27 16:00")
    assert fw.missed("BTCUSDT", ["BTCUSDT", "ETHUSDT"], bar, bar + 14 * M) == 0
    assert fw.missed("BTCUSDT", ["BTCUSDT", "ETHUSDT"], bar, bar + 30 * M) == 1      # the 16:15 bar is due at 16:30
    assert fw.view("BTCUSDT", ["BTCUSDT"], bar, bar + 45 * M) == (45.0, False)       # two due: not yet
    assert fw.view("BTCUSDT", ["BTCUSDT"], bar, bar + 60 * M) == (60.0, True)        # three due and missing


def test_a_weekend_never_counts_and_a_fresh_open_waits_three_bars():
    idx = pd.date_range("2026-11-27 12:00", "2026-11-30 06:00", freq="15min", tz="UTC")
    mask = list(market_calendar.open_mask("XAUUSD", idx))
    last = max(i for i in range(len(idx)) if mask[i] and not all(mask[i:i + 8]))    # the last open slot before the shut
    first = next(i for i in range(last + 1, len(idx)) if mask[i])                    # the first slot after it
    assert first - last > 40                                                         # a weekend in between
    bar = int(idx[last].timestamp() * 1000)
    reopen = int(idx[first].timestamp() * 1000)
    assert fw.view("XAUUSD", ["XAUUSD", "XAGUSD"], bar, reopen)[1] is False
    assert fw.missed("XAUUSD", ["XAUUSD", "XAGUSD"], bar, reopen + 30 * M) == 2
    assert fw.view("XAUUSD", ["XAUUSD", "XAGUSD"], bar, reopen + 30 * M)[1] is False
    assert fw.view("XAUUSD", ["XAUUSD", "XAGUSD"], bar, reopen + 45 * M)[1] is True


def test_a_group_counts_only_slots_where_every_member_is_open():
    bar, now = ms("2026-11-24 22:45"), ms("2026-11-25 01:15")       # Brent shuts 23:00-01:00 UTC; WTI does not
    alone = fw.missed("WTI", ["WTI"], bar, now)
    group = fw.missed("WTI", ["WTI", "BRENT"], bar, now)
    assert alone is not None and group is not None and group < alone
    assert fw.view("WTI", ["WTI", "BRENT"], bar, now)[1] is False


def test_unknowns_are_none_and_never_raise():
    assert fw.view("NOPE", ["NOPE"], ms("2026-11-24 10:00"), ms("2026-11-24 12:00")) == (120.0, None)
    assert fw.view("BTCUSDT", ["BTCUSDT"], None, ms("2026-11-24 12:00")) == (None, None)
    assert fw.missed("BTCUSDT", ["BTCUSDT"], "garbage", 5) is None
    assert fw.missed("BTCUSDT", ["BTCUSDT"], ms("2026-11-24 12:00"), ms("2026-11-24 11:00")) == 0
