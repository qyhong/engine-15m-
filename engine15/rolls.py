# -*- coding: utf-8 -*-
"""rolls -- when the futures behind the stored bars switch contracts (the "roll calendar"). Scheduling only: pure
functions, no network, never used by the live engine's readings or books.

Owner, 28 Nov 2026 (the six commodity cards, H122: "Calendar first"): the cards C2, C3, C5 and C6 must stay silent
around a contract switch, because the stored series is NOT adjusted there.

What the stored series does at a switch (measured on the box on 28 Nov 2026 against Yahoo's single-contract charts,
60 days of 15-minute bars, the median gap per UTC day between the stored close and each contract's close):
    WTI   (CL=F)  followed CLZ26 until 18 Nov 2026, CLF27 from then (median gap 0.0 bp): a step of about -1.4%
    Brent (BZ=F)  followed BZF27 until 18 Nov 2026, BZG27 from then (5.6 / 0.0 bp): a step of about -3.0%,
                  twelve days before BZF27's last trading day (30 Nov). Yahoo moved BZ=F on the same day as CL=F.
    Gold  (GC=F)  followed GCZ26 until 24 Nov 2026, GCG27 from 25 Nov (0.0 bp): a step of about +0.8%
    Silver(SI=F)  followed SIZ26 until 24 Nov 2026, SIH27 from 25 Nov (0.0 bp): a step of about +1.2%
    S&P   (ES=F)  follows ESZ26 (the overnight card's file); its switch to ESH27 is still ahead.
None of these steps was adjusted: extdata.roll_adjust acts only when Yahoo re-serves old bars at the new prices, and
it did not (no data/rolls.csv on the box). Expired contracts are not served by Yahoo, so older switches cannot be
measured; they are FORECAST by the rules below, which are fitted to the one cycle seen (said, not hidden).

The rules (exchange rules; Yahoo's offset from them is from the cycle above, one observation each):
    CL   last trading day (LTD) of month M: 3 business days before the 25th of M-1 (4 if the 25th is not a business
         day). Yahoo switches CL=F 2 business days before the LTD.               (seen: LTD 20 Nov -> 18 Nov)
    BZ   Yahoo switches BZ=F on the day it switches CL=F (BZ month M+1 with CL month M).   (seen: 18 Nov, both)
    GC   active months G J M Q V Z; first notice day (FND) of M: the last business day of M-1. Yahoo switches GC=F
         2 business days before the FND.                                          (seen: FND 30 Nov -> 25 Nov)
    SI   active months H K N U Z; the same rule as GC.                           (seen: FND 30 Nov -> 25 Nov)
    ES   quarterly H M U Z, expiry the 3rd Friday; the usual roll date 8 calendar days before (a Thursday). Not seen.
Business days: weekdays that are not NYSE holidays (market_calendar's 2026-2027 table; calhistory's federal holidays
plus Good Friday in other years, an approximation good enough for a window of a day or two).

    near_switch(asset, t, bdays=1)   True within `bdays` business days (New York dates) of a seen or forecast switch
    switches(asset, start, end)      [(date, "seen" | "forecast", text)] between two dates
"""
import datetime as dt

D = dt.date
PRODUCT = {"WTI": "CL", "BRENT": "BZ", "XAUUSD": "GC", "XAGUSD": "SI", "ES": "ES", "SPX": "ES"}
MONTHS = {"CL": tuple(range(1, 13)), "BZ": tuple(range(1, 13)), "GC": (2, 4, 6, 8, 10, 12), "SI": (3, 5, 7, 9, 12),
          "ES": (3, 6, 9, 12)}
CODE = "FGHJKMNQUVXZ"
SEEN = {   # product -> [(the first New York date on the new contract, from, to)]: measured 28 Nov 2026 (docstring)
    "CL": [(D(2026, 11, 18), "CLZ26", "CLF27")],
    "BZ": [(D(2026, 11, 18), "BZF27", "BZG27")],
    "GC": [(D(2026, 11, 25), "GCZ26", "GCG27")],
    "SI": [(D(2026, 11, 25), "SIZ26", "SIH27")],
    "ES": [],
}
YAHOO_LEAD_BDAYS = {"CL": 2, "GC": 2, "SI": 2}
ES_LEAD_DAYS = 8


def _easter(y):
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return D(y, month, day)


_HOL = {}


def _holidays(y):
    if y not in _HOL:
        try:
            from .market_calendar import NYSE_CLOSED
            known = set(d for d in NYSE_CLOSED if d.year == y)
        except Exception:
            known = set()
        if not known:
            from .calhistory import federal_holidays
            known = set(federal_holidays(y)) | {_easter(y) - dt.timedelta(days=2)}
            known -= {d for d in known if d.month == 10 or (d.month == 11 and d.day < 20)}   # Columbus / Veterans Day
        _HOL[y] = frozenset(known)
    return _HOL[y]


def is_bday(d):
    return d.weekday() < 5 and d not in _holidays(d.year)


def add_bdays(d, n):
    step = 1 if n >= 0 else -1
    while n:
        d += dt.timedelta(days=step)
        if is_bday(d):
            n -= step
    return d


def _last_bday(y, m):
    d = (D(y + (m == 12), m % 12 + 1, 1)) - dt.timedelta(days=1)
    while not is_bday(d):
        d -= dt.timedelta(days=1)
    return d


def _prev_month(y, m):
    return (y - 1, 12) if m == 1 else (y, m - 1)


def cl_ltd(y, m):
    """The last trading day of the CL contract for delivery month (y, m)."""
    py, pm = _prev_month(y, m)
    d25 = D(py, pm, 25)
    return add_bdays(d25, -3 if is_bday(d25) else -4)


def _forecast(product, y, m):
    """Yahoo's switch AWAY from the contract of delivery month (y, m), by the rules in the docstring."""
    if product == "CL":
        return add_bdays(cl_ltd(y, m), -YAHOO_LEAD_BDAYS["CL"])
    if product == "BZ":                                   # BZ month M+1 leaves with CL month M
        py, pm = _prev_month(y, m)
        return add_bdays(cl_ltd(py, pm), -YAHOO_LEAD_BDAYS["CL"])
    if product in ("GC", "SI"):
        py, pm = _prev_month(y, m)
        return add_bdays(_last_bday(py, pm), -YAHOO_LEAD_BDAYS[product])
    if product == "ES":
        first = D(y, m, 1)
        third_friday = first + dt.timedelta(days=(4 - first.weekday()) % 7 + 14)
        return third_friday - dt.timedelta(days=ES_LEAD_DAYS)
    raise KeyError(product)


def switches(asset, start, end):
    """[(New York date, "seen" | "forecast", text)] of the switches of this asset's series between start and end
    (dates), sorted. A forecast within 3 days of a seen switch is replaced by the seen one."""
    p = PRODUCT.get(asset)
    if p is None:
        return []
    out = [(d, "seen", "%s -> %s" % (a, b)) for d, a, b in SEEN[p] if start <= d <= end]
    for y in range(start.year - 1, end.year + 2):
        for m in MONTHS[p]:
            try:
                d = _forecast(p, y, m)
            except ValueError:
                continue
            if start <= d <= end and not any(abs((d - s).days) <= 3 for s, _k, _t in out if _k == "seen"):
                out.append((d, "forecast", "leaves %s%s%d" % (p, CODE[m - 1], y % 100)))
    return sorted(out)


def _ny_date(t):
    import pandas as pd
    ts = pd.Timestamp(int(t), unit="ms", tz="UTC") if isinstance(t, (int, float)) else pd.Timestamp(t)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    try:
        ts = ts.tz_convert("America/New_York")
    except Exception:                                    # no tz database: a fixed five hours is near enough here
        ts = ts - pd.Timedelta(hours=5)
    return ts.date()


def near_switch(asset, t, bdays=1):
    """True when t (epoch ms or a timestamp) falls within `bdays` business days of a switch of this asset's series
    (New York dates; the switch day itself included). Unknown assets: False."""
    if PRODUCT.get(asset) is None:
        return False
    d = _ny_date(t)
    lo, hi = d - dt.timedelta(days=10), d + dt.timedelta(days=10)
    for s, _k, _t in switches(asset, lo, hi):
        a, b = (s, d) if s <= d else (d, s)
        n, x = 0, a
        while x < b:
            x += dt.timedelta(days=1)
            if is_bday(x):
                n += 1
        if n <= bdays:
            return True
    return False
