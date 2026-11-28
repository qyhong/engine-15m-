# -*- coding: utf-8 -*-
"""feed_watch -- has a market's price feed stopped? One rule, read by setups.py (the "stale" key of each market in
setups.json) and by telegram_notify.py (one alert when a market's prices stop, one when they come back).

Owner, 27 Nov 2026 ("any 10 tasks we can do today": 1 a server-side alert when prices stop, 2 show "stale" on the
page). On 26-27 Nov the usual feed for gold, silver and oil stopped for most of a day while the markets were open, and
nothing on the server said so: the cards' own data check counts closes that came, so a feed that sends no bar at all is
never counted, and the laptop's 8-hourly price check runs only while the laptop is awake.

The rule: count the 15-minute bars that should have arrived since the last one the engine has. A bar is due for each
slot after the last bar's slot whose 15 minutes have ended by now, while the market's whole GROUP is open at that slot
(a group steps as one: WTI waits while Brent is shut 23:00-01:00 UTC). STALE_BARS or more due and missing: stale.
So a weekend, a holiday, an early close or a daily break never counts, and a market that has just opened is not stale
until STALE_BARS of its own open slots have passed without a bar. Crypto never shuts. Read only; never raises.
"""
STALE_BARS = 3                       # 45 minutes of open market without a bar (the price check's own limit)
SLOT_MS = 15 * 60 * 1000
LOOK_MAX = 96 * 14                   # at most fourteen days of slots are looked at; older is simply stale


def _open_mask(sym, idx):
    from .config import CFG
    if sym in CFG.get("crypto", ()):
        return [True] * len(idx)
    from . import extdata, market_calendar
    if sym not in extdata.MARKETS:
        return None
    return list(market_calendar.open_mask(sym, idx))


def missed(sym, mates, bar_ms, now_ms):
    """The number of bars due and not here: slots after bar_ms (the open time of the last bar the engine has) whose
    15 minutes have ended by now_ms, with every market of the group open. None when it cannot be told."""
    try:
        if bar_ms is None or now_ms is None:
            return None
        import pandas as pd
        first, last = int(bar_ms) + SLOT_MS, int(now_ms) - SLOT_MS    # a slot is due once its 15 minutes have ended
        if last < first:
            return 0
        n = min(int((last - first) // SLOT_MS) + 1, LOOK_MAX)
        idx = pd.date_range(pd.Timestamp(last - (n - 1) * SLOT_MS, unit="ms", tz="UTC"), periods=n, freq="15min")
        both = [True] * n
        for a in (list(mates) or [sym]):
            m = _open_mask(a, idx)
            if m is None:
                return None
            both = [x and bool(y) for x, y in zip(both, m)]
        return sum(both)
    except Exception:
        return None


def view(sym, mates, bar_ms, now_ms):
    """(bar_age_min, stale) for setups.json: the minutes since the last bar's open time (one decimal) and True / False,
    or None when it cannot be told."""
    age = None if bar_ms is None or now_ms is None else round((int(now_ms) - int(bar_ms)) / 60000.0, 1)
    n = missed(sym, mates, bar_ms, now_ms)
    return age, (None if n is None else n >= STALE_BARS)
