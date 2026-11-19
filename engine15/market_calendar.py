"""Exchange holidays and early closes, for SCHEDULING only (when a bar is expected, whether a market shows as
open, when it opens next). Never used for readings: extdata (in the reading-cache signature) is left as it is.

    closed(asset, t)            -> True on a full holiday of that market at that UTC moment
    early_close_utc(asset, day) -> the UTC datetime that market shuts early on that (New York) date, or None
    is_open(asset, t)           -> extdata.is_open AND NOT closed AND before the early close
    open_mask(asset, idx)       -> the same for a UTC DatetimeIndex (vector form)

Pure functions, no network. All dates and times are New York wall time (the sessions of extdata are anchored on
it too). Covers 2026 and 2027 only; outside them nothing is added to extdata's own hours (which already know the
NYSE holidays for the S&P by rule, extdata.nyse_days).

How a holiday is applied, per extdata session kind:
  us_cash (S&P 500)           a full holiday is that whole calendar date; an early close shuts at 13:00.
  metal (gold, silver, WTI)   a session runs 18:00 the evening before to 17:00 on its trade date, so a full holiday
  ice (Brent)                 of trade date D shuts from D-1 17:00 to D 17:00 (it reopens at the usual evening open
                              of D, for D+1). An early close on D shuts from that time to 17:00 on D.
  fx (USDJPY)                 nothing: the engine reads Yahoo's spot JPY=X, which quotes through US holidays.

Sources and confidence:
  NYSE  the NYSE's published holiday and early-close schedule for 2026-2027 (nyse.com, "Holidays & Trading
        Hours"), the rules: New Year's Day, Martin Luther King Jr. Day (3rd Mon Jan), Washington's Birthday (3rd
        Mon Feb), Good Friday, Memorial Day (last Mon May), Juneteenth (19 Jun), Independence Day, Labor Day (1st
        Mon Sep), Thanksgiving (4th Thu Nov), Christmas; Saturday -> the Friday before, Sunday -> the Monday after,
        except a Saturday New Year's Day, which is not observed. Early close 13:00 on the day after Thanksgiving
        and on 24 December when it is a Monday-Thursday trading day (and 3 July in years it is a Mon-Thu). The
        same dates as extdata.nyse_days gives (a test checks it). Certain.
  CME   (COMEX gold/silver, NYMEX WTI on Globex) from memory of CME Group's usual holiday pattern, NOT checked
        against the 2026/2027 notices (no network here): Good Friday, Christmas Day and New Year's Day closed;
        on the US Monday holidays, Juneteenth, Independence Day and Thanksgiving Thursday the Globex session halts
        early at 13:30 New York (12:30 Chicago) and reopens 18:00 for the next day; the day after Thanksgiving
        and Christmas Eve close at 13:45 (12:45 Chicago). The closures are certain; the 13:30 / 13:45 minutes are
        the usual ones, not verified. Not modelled (unsure): 31 December, Friday 24 December 2027 (Christmas
        observed), and anything for the following Monday.
  ICE   (Brent, ICE Futures Europe) only what is certain: closed on Good Friday, Christmas Day and New Year's Day.
        Its abbreviated hours on US holidays (Thanksgiving etc.) and on 24/31 December are not modelled.
"""
import datetime as dt

import numpy as np
import pandas as pd

from . import extdata

D = dt.date
NYSE_CLOSED = frozenset([
    D(2026, 1, 1), D(2026, 1, 19), D(2026, 2, 16), D(2026, 4, 3), D(2026, 5, 25), D(2026, 6, 19), D(2026, 7, 3),
    D(2026, 9, 7), D(2026, 11, 26), D(2026, 12, 25),
    D(2027, 1, 1), D(2027, 1, 18), D(2027, 2, 15), D(2027, 3, 26), D(2027, 5, 31), D(2027, 6, 18), D(2027, 7, 5),
    D(2027, 9, 6), D(2027, 11, 25), D(2027, 12, 24),
])
NYSE_EARLY = {D(2026, 11, 27): (13, 0), D(2026, 12, 24): (13, 0), D(2027, 11, 26): (13, 0)}

CME_CLOSED = frozenset([D(2026, 1, 1), D(2026, 4, 3), D(2026, 12, 25), D(2027, 1, 1), D(2027, 3, 26)])
_CME_HALT, _CME_SHORT = (13, 30), (13, 45)
CME_EARLY = {
    D(2026, 1, 19): _CME_HALT, D(2026, 2, 16): _CME_HALT, D(2026, 5, 25): _CME_HALT, D(2026, 6, 19): _CME_HALT,
    D(2026, 7, 3): _CME_HALT, D(2026, 9, 7): _CME_HALT, D(2026, 11, 26): _CME_HALT, D(2026, 11, 27): _CME_SHORT,
    D(2026, 12, 24): _CME_SHORT,
    D(2027, 1, 18): _CME_HALT, D(2027, 2, 15): _CME_HALT, D(2027, 5, 31): _CME_HALT, D(2027, 6, 18): _CME_HALT,
    D(2027, 7, 5): _CME_HALT, D(2027, 9, 6): _CME_HALT, D(2027, 11, 25): _CME_HALT, D(2027, 11, 26): _CME_SHORT,
}
ICE_CLOSED = frozenset([D(2026, 1, 1), D(2026, 4, 3), D(2026, 12, 25), D(2027, 1, 1), D(2027, 3, 26)])

CALENDARS = {                     # session kind -> (full holidays, early closes {date: (hour, minute)})
    "us_cash": (NYSE_CLOSED, NYSE_EARLY),
    "metal": (CME_CLOSED, CME_EARLY),
    "ice": (ICE_CLOSED, {}),
    "fx": (frozenset(), {}),
}
DAY_END = 17 * 60                 # New York minutes: a futures trade date ends at 17:00 (the S&P at 16:00)


def _kind(asset):
    m = extdata.MARKETS.get(asset)
    return m["session"] if m else None


def _ny(idx):
    """A UTC DatetimeIndex -> (New York dates as datetime64[D], New York minutes of the day)."""
    loc = extdata._local(idx, extdata.NY)
    return np.asarray(loc.normalize(), dtype="datetime64[D]"), np.asarray(loc.hour) * 60 + np.asarray(loc.minute)


def _as_index(t):
    return pd.DatetimeIndex([extdata._as_utc(t)])


def _closed_mask(kind, idx):
    shut, early = CALENDARS.get(kind, (frozenset(), {}))
    if not len(idx):
        return np.zeros(0, dtype=bool)
    day, mins = _ny(idx)
    trade = day if kind == "us_cash" else day + (mins >= DAY_END).astype("int64").astype("timedelta64[D]")
    out = np.isin(trade, np.array(sorted(shut), dtype="datetime64[D]")) if shut else np.zeros(len(idx), dtype=bool)
    for d, (h, m) in early.items():
        out |= (day == np.datetime64(d, "D")) & (mins >= h * 60 + m) & (mins < DAY_END)
    return out


def closed(asset, t):
    """True when that UTC moment falls on a full holiday of the asset's market (any kind of market the engine knows;
    crypto and unknown symbols: False). `t`: datetime/Timestamp (naive = UTC) or epoch ms."""
    kind = _kind(asset)
    if kind is None:
        return False
    shut = CALENDARS.get(kind, (frozenset(), {}))[0]
    day, mins = _ny(_as_index(t))
    d = day[0] if kind == "us_cash" else day[0] + np.timedelta64(int(mins[0] >= DAY_END), "D")
    return d.astype(dt.date) in shut


def early_close_utc(asset, day):
    """The tz-aware UTC Timestamp at which the asset's market shuts early on that New York date, or None."""
    kind = _kind(asset)
    if kind is None:
        return None
    day = pd.Timestamp(day).date()
    hm = CALENDARS.get(kind, (frozenset(), {}))[1].get(day)
    if hm is None:
        return None
    t = pd.Timestamp(dt.datetime(day.year, day.month, day.day, hm[0], hm[1]))
    if extdata.TZ_OK:
        return t.tz_localize(extdata.NY).tz_convert("UTC")
    ms = int(t.value // 10 ** 6)                       # no tz database: extdata's own daylight-saving rule
    off = int(extdata._manual_offset_ms(np.array([ms - 5 * 3600000]), extdata.NY)[0])
    return pd.Timestamp(ms - off, unit="ms", tz="UTC")


def open_mask(asset, idx, feed=False):
    """extdata.open_mask (the weekly hours, daily breaks, NYSE rule) AND NOT a holiday AND before an early close."""
    m = np.asarray(extdata.open_mask(asset, idx, feed=feed), dtype=bool)
    kind = _kind(asset)
    return m & ~_closed_mask(kind, idx) if kind else m


def is_open(asset, t, feed=False):
    """extdata.is_open(asset, t) and not a holiday of that market and not after its early close that day."""
    return bool(open_mask(asset, _as_index(t), feed=feed)[0])
