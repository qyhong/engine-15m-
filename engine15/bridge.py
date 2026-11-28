# -*- coding: utf-8 -*-
"""bridge -- 15-minute bars from a second source when the usual feed serves none for an open market. PAPER MARKETS ONLY
(gold, silver, WTI, Brent, and since 28 Nov 2026 the S&P 500 and USDJPY: none of them reaches the VIP vault).

Why (owner, 26 Nov 2026, US Thanksgiving: "Should check on future or other source. The price still moving from my
end"): Yahoo's chart for GC=F / SI=F / CL=F / BZ=F stopped at midnight New York although the futures traded on and its own
quote kept moving. The engine then had no bar for hours: no decision, no stop or target looked at, a stale price on the
Setups page with the market shown open.

What it does. live._update_bars calls `fill(asset)` after extdata.update found no new bar. When ALL of this holds
    * the market is one of SOURCES and is open now by the engine's own calendar (market_calendar.is_open);
    * its last stored bar is at least MIN_STALE_BARS closed bars behind the clock (Yahoo's futures bars run 10-15
      minutes late in normal hours, so a short lag never starts a bridge);
    * a source has a 15-minute bar at the very time of the last stored bar (the anchor) and closed bars after it;
then the source's bars after the anchor are scaled by  stored close / source close  at the anchor and appended. The
exchange contracts follow spot or their own index, a little off the front-month future (gold about 0.4%), so the scale
joins them to the stored series without a jump; from there on the bridge carries the source's MOVES. Bars outside the
market's hours are left out, and the bridge ends where the calendar says the market halts. Volume is 0 (another
venue's size means nothing here). Every bridge is one line in the log and one row in data/bridge_bars.csv.

Once a bridge has begun the market stays bridged bar by bar (the newest stored bar is a bridged one: the last row of
data/bridge_bars.csv says so) until the usual feed is seen alive again (it serves a bar from the last 45 minutes): then
the bridge stands back. When the usual feed comes back it appends after the last bar as always. Bars it later serves for the bridged hours are
not taken (the stored series is never rewritten), and its futures-roll check (extdata.roll_adjust) reads the overlap as
it always did.

A source's answer is checked before it is used: every bar on the 15-minute grid, prices positive, high >= low, and the
bridged move since the anchor not beyond MAX_MOVE (a wrong contract or a broken answer is refused, not appended).
Sources are tried in order; a failure is one log line and the next step tries again. Nothing here raises.

The S&P 500 (added 28 Nov 2026; docs/FEED_PLAN.md has the numbers). Its sources trade round the clock: Hyperliquid's
xyz:SP500 follows the index itself, the SPY contracts follow the fund at about a tenth of the index (the scale takes
that up). Only bars inside the cash session are kept, so the first bridged bar of a day opens where the contract stood
at 09:30 New York: the overnight move arrives as the opening gap, as it does on the usual feed. Measured from the box
over 19-27 Nov 2026 against the stored ^GSPC bars (138 pairs of 15-minute returns): correlation 0.998 / 0.998 / 0.997.
USDJPY (added 28 Nov 2026 as a ROUGH bridge, on the owner's word in this project: "Add rough bridge", after first
leaving it out): Hyperliquid's xyz:JPY, quoted as yen per dollar like the stored JPY=X (159.39 against 159.52 on 28 Nov).
It follows the level within about 5 basis points (p95 after scaling), but its 15-minute returns correlate only 0.79 with
the stored ones (0.93 at 1 hour, 0.97 at 4 hours; docs/FEED_PLAN.md): a bridged USDJPY bar is noisier than a usual one.
It is used, like every source here, only while the usual feed serves no bar for an open market.
"""
import os
import time

import numpy as np
import pandas as pd

from . import data, extdata

BAR_MS = 900000
MIN_STALE_BARS = 3                      # closed bars the store must be behind before a bridge starts (45 minutes)
MAX_BARS = 400                          # at most this many bars in one bridge (about four days)
MAX_MOVE = 0.15                         # a bridged close more than 15% off the anchor is refused as a wrong answer
TIMEOUT = 15
UA = "Mozilla/5.0"
LOG_FILE = "bridge_bars.csv"
# the same market on public venues the box reaches without a key; tried in this order
SOURCES = {
    "XAUUSD": (("binance", "XAUUSDT"), ("okx", "XAU-USDT-SWAP")),
    "XAGUSD": (("binance", "XAGUSDT"), ("okx", "XAG-USDT-SWAP")),
    "WTI": (("binance", "CLUSDT"), ("okx", "CL-USDT-SWAP")),
    "BRENT": (("hyperliquid", "xyz:BRENTOIL"),),
    "SPX": (("hyperliquid", "xyz:SP500"), ("okx", "SPY-USDT-SWAP"), ("binance", "SPYUSDT")),
    "USDJPY": (("hyperliquid", "xyz:JPY"),),                  # rough (owner, 28 Nov 2026): see the docstring
}


# ------------------------------------------------------------------ the sources (each: closed or not, the caller cuts)
def _get(url, params):
    import requests
    r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _binance(symbol, start_ms, end_ms):
    k = _get("https://fapi.binance.com/fapi/v1/klines",
             {"symbol": symbol, "interval": "15m", "startTime": int(start_ms), "endTime": int(end_ms), "limit": 1000})
    return [(int(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4])) for x in k]


def _okx(inst, start_ms, end_ms):
    out, after = [], int(end_ms) + BAR_MS
    for _ in range(6):                                           # newest first, 100 a page
        k = _get("https://www.okx.com/api/v5/market/candles",
                 {"instId": inst, "bar": "15m", "after": str(after), "limit": "100"}).get("data") or []
        if not k:
            break
        out += [(int(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4])) for x in k]
        after = min(int(x[0]) for x in k)
        if after <= start_ms:
            break
    return sorted(x for x in out if start_ms <= x[0] <= end_ms)


def _hyperliquid(coin, start_ms, end_ms):
    import requests
    r = requests.post("https://api.hyperliquid.xyz/info", headers={"User-Agent": UA}, timeout=TIMEOUT,
                      json={"type": "candleSnapshot",
                            "req": {"coin": coin, "interval": "15m", "startTime": int(start_ms), "endTime": int(end_ms)}})
    r.raise_for_status()
    return [(int(x["t"]), float(x["o"]), float(x["h"]), float(x["l"]), float(x["c"])) for x in r.json()]


FETCH = {"binance": _binance, "okx": _okx, "hyperliquid": _hyperliquid}


# ------------------------------------------------------------------ the bridge
def scaled(rows, anchor_ms, anchor_close, now_ms):
    """A source's rows [(open ms, o, h, l, c)] -> (the CLOSED bars after the anchor scaled to the stored level as
    [(ms, o, h, l, c)], the scale), or (None, why not)."""
    rows = sorted(set(rows))
    if any(t % BAR_MS for t, *_ in rows) or any(not (min(o, h, l, c) > 0 and h >= max(o, c) and l <= min(o, c))
                                               for _t, o, h, l, c in rows):
        return None, "a bar off the 15-minute grid or with impossible prices"
    at = dict((t, c) for t, _o, _h, _l, c in rows)
    if anchor_ms not in at:
        return None, "no bar at the last stored bar's time"
    ratio = float(anchor_close) / at[anchor_ms]
    new = [(t, o * ratio, h * ratio, l * ratio, c * ratio) for t, o, h, l, c in rows
           if t > anchor_ms and t + BAR_MS <= now_ms][:MAX_BARS]
    if not new:
        return None, "no closed bar after the last stored one"
    if any(abs(c / float(anchor_close) - 1.0) > MAX_MOVE for _t, _o, _h, _l, c in new):
        return None, "a move of more than %d%% since the last stored bar" % round(MAX_MOVE * 100)
    return new, ratio


def _note(asset, source, symbol, ratio, n, first_ms, last_ms):
    try:
        p = os.path.join(os.path.dirname(data.path_for(asset)), LOG_FILE)
        head = not os.path.exists(p)
        with open(p, "a", encoding="utf-8") as fh:
            if head:
                fh.write("t_utc,asset,source,symbol,ratio,bars,first_bar_utc,last_bar_utc\n")
            f = lambda ms: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ms // 1000))      # noqa: E731
            fh.write("%s,%s,%s,%s,%.6f,%d,%s,%s\n" % (f(int(time.time() * 1000)), asset, source, symbol, ratio, n,
                                                      f(first_ms), f(last_ms)))
    except OSError:
        pass


def bridged_last(asset):
    """The open time (ms) of the last bar the bridge appended for this market, or None."""
    try:
        p = os.path.join(os.path.dirname(data.path_for(asset)), LOG_FILE)
        with open(p, encoding="utf-8") as fh:
            rows = [ln.strip().split(",") for ln in fh.readlines()[-200:]]
        last = next((r for r in reversed(rows) if len(r) >= 8 and r[1] == asset), None)
        return None if last is None else int(pd.Timestamp(last[7]).value // 1000000)
    except (OSError, ValueError):
        return None


def feed_alive(asset, now_ms):
    """True when the usual feed serves a closed bar from the last MIN_STALE_BARS bars (one request). A failure is
    'not alive'."""
    try:
        df, _info = extdata.yahoo_bars(asset, "1d")
        return bool(len(df)) and now_ms - (int(df.index[-1].value // 1000000) + BAR_MS) < MIN_STALE_BARS * BAR_MS
    except Exception:
        return False


def fill(asset, log=print, now=None, fetch=None, is_open=None, alive=None):
    """Append bridged bars for one market when the usual feed has fallen behind while the market is open.
    -> (all stored bars or None when nothing was done, number of bars appended). Never raises.
    now (epoch s), fetch ({source: function}), is_open ((asset, time -> bool), (asset, index -> mask)) and alive
    ((asset, now ms) -> bool) are the tests'."""
    try:
        if asset not in SOURCES:
            return None, 0
        now_ms = int((time.time() if now is None else now) * 1000)
        if is_open is None:
            from . import market_calendar
            open_at, open_mask = market_calendar.is_open, market_calendar.open_mask
        else:
            open_at, open_mask = is_open
        if not open_at(asset, pd.Timestamp(now_ms, unit="ms", tz="UTC")):
            return None, 0
        old = extdata._stored(asset)
        if not len(old):
            return None, 0
        anchor_ms = int(old.index[-1].value // 1000000)
        lag = now_ms - (anchor_ms + BAR_MS)
        bridging = bridged_last(asset) == anchor_ms              # the newest stored bar is a bridged one
        if lag < BAR_MS or (not bridging and lag < MIN_STALE_BARS * BAR_MS):
            return None, 0                                       # no bar is missing, or the usual lag of the feed
        if bridging and (alive or feed_alive)(asset, now_ms):
            return None, 0                                       # the usual feed is back: it takes over from here
        anchor_close = float(old["close"].iloc[-1])
        why = []
        for source, symbol in SOURCES[asset]:
            try:
                rows = (fetch or FETCH)[source](symbol, anchor_ms, now_ms)
                new, ratio = scaled(rows, anchor_ms, anchor_close, now_ms)
            except Exception as e:                               # network, HTTP status, a broken answer
                new, ratio = None, "%s: %s" % (type(e).__name__, str(e)[:80])
            if new is None:
                why.append("%s %s: %s" % (source, symbol, ratio))
                continue
            df = extdata._frame([r[0] for r in new], [r[1] for r in new], [r[2] for r in new], [r[3] for r in new],
                                [r[4] for r in new], [0.0] * len(new))
            df = df[np.asarray(open_mask(asset, df.index), dtype=bool)]         # the market's own hours only
            if not len(df):
                why.append("%s %s: no bar inside the market's hours" % (source, symbol))
                continue
            out = extdata._tidy(asset, pd.concat([old, df]))
            try:
                extdata._save(asset, out)
            except OSError as e:
                log("%s: could not write %d bridged bars, keeping the stored file (%s)" % (asset, len(df), e))
                return None, 0
            first, last = int(df.index[0].value // 1000000), int(df.index[-1].value // 1000000)
            _note(asset, source, symbol, ratio, len(df), first, last)
            log("%s: %d bars bridged from %s %s (the usual feed served none since %s UTC); scaled by %.6f" % (
                asset, len(df), source, symbol, time.strftime("%H:%M", time.gmtime((anchor_ms + BAR_MS) // 1000)), ratio))
            return out, int(len(df))
        log("%s: the feed is %d minutes behind an open market and no bridge was possible (%s)" % (
            asset, (now_ms - anchor_ms - BAR_MS) // 60000, "; ".join(why)))
        return None, 0
    except Exception as e:                                       # the bridge never stops a step
        try:
            log("%s: bridge failed (%s: %s)" % (asset, type(e).__name__, e))
        except Exception:
            pass
        return None, 0
