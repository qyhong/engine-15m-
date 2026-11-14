# -*- coding: utf-8 -*-
"""equity_events -- two S&P 500 cards: the options market's put/call mood, and megacap earnings dates.

  putcall   Options mood (put/call)   daily put/call volume ratios: total, index, equity
  earnings  Megacap earnings          when the ten largest S&P 500 companies report

Both apply to SPX only (APPLIES).

PUT/CALL -- two free sources, never mixed inside one statistic:
  2006-11-01 .. 2019-10-04  Cboe's historical CSVs (cdn.cboe.com, Cboe exchange volume only):
                            total, index and equity (stock options only, ETFs excluded) ratios.
  ~2 years ago .. today     OCC's public volume query (marketdata.theocc.com/volume-query): every
                            cleared option trade of a day, all US exchanges, by underlying and put/call.
                            OCC serves only the last 2 years, so history starts 2 years before the first
                            run and grows from then on. Here "index" = cash-settled index options (SPX,
                            VIX, XSP, RUT, NDX, ...; INDEX_ROOTS, which matches OCC's own index total) and
                            "equity" = everything else (single stocks AND ETFs such as SPY and QQQ).
  The years between (Oct 2019 to two years before the first run) have no free daily source: no read.
  Cboe's own daily statistics page sits behind a bot wall and is not used.
  Percentiles and averages are taken only over days of the same source, so the two definitions never meet.
  KNOWN AT: a day's figures are used from 12:00 New York time of the next NYSE trading day (OCC was seen
  to have day D by 11:49 ET on D+1); live, a day the OCC did not have by then counts from when it was seen.

EARNINGS -- Nasdaq's public earnings calendar (api.nasdaq.com/api/calendar/earnings?date=...), one
  request per calendar day, a browser User-Agent and nothing else. MEGACAPS (state the list): NVDA, AAPL,
  MSFT, AMZN, GOOGL, META, AVGO, TSLA, BRK.B, JPM -- the ten largest S&P 500 weights in late 2026. The same
  ten are used for all history (a survivor's list: in 2018 the top ten were partly different).
  Release time: before the open = 07:00 ET, after the close = 16:05 ET; when Nasdaq gives no time, the
  company's habit (JPM before the open, Berkshire on a Saturday morning, the rest after the close).
  KNOWN AT: a date first seen live is known from that moment. A date filled in from history (backfill) is
  assumed known 7 days before the report (megacaps announce dates 2 to 5 weeks ahead), so "days to the
  next report" never looks further than 7 days. A date that later disappears from the calendar (a moved
  report) stops counting from the moment it was seen gone.

Files under data/sources/: putcall_daily.csv, earnings_megacap.csv, earnings_days.csv (which calendar days
were asked, and when), equity_events_state.json.

Docs: docs/SOURCES_equity_events.md. No reading here is claimed to predict anything.
"""
import io
import os
import time
from collections import OrderedDict

import numpy as np
import pandas as pd

from . import _util as U
from ..config import DATA_DIR

SRC_DIR = os.path.join(DATA_DIR, "sources")
ASSET = "SPX"

GROUPS = OrderedDict([
    ("putcall", ("Options mood (put/call)", ["pc_total", "pc_total_10d", "pc_index", "pc_equity"])),
    ("earnings", ("Megacap earnings", ["ern_next", "ern_week", "ern_last"])),
])
APPLIES = {"putcall": (ASSET,), "earnings": (ASSET,)}
FEATURES = [f for _t, fs in GROUPS.values() for f in fs]
RAW = ["pc_total_ratio", "pc_index_ratio", "pc_equity_ratio", "pc_spx_ratio", "pc_total_10d_avg",
       "pc_total_pctile", "pc_equity_pctile", "pc_source", "pc_day_age_d",
       "ern_days_next", "ern_n_next5", "ern_hours_since", "ern_n_last24"]

# ---- put/call
CBOE_URL = "https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/%s.csv"
CBOE_FILES = (("total", "totalpc"), ("index", "indexpc"), ("equity", "equitypc"))
OCC_URL = "https://marketdata.theocc.com/volume-query"
OCC_PARAMS = {"format": "csv", "volumeQueryType": "O", "symbolType": "ALL", "symbol": "", "reportType": "D",
              "accountType": "ALL", "productKind": "ALL", "porc": "BOTH"}
OCC_PAUSE_S = 2.0                                             # a reply is ~5 MB: be gentle
OCC_LOOKBACK_D = 730                                          # OCC refuses dates older than 2 years
OCC_RETRY_MS = 60 * 60000                                     # a day not yet out: ask again after an hour
OCC_BACKFILL_PER_CALL = 1                                     # older days filled in per update() call
INDEX_ROOTS = ("SPX", "SPXW", "XSP", "VIX", "VIXW", "NDX", "NDXP", "XND", "RUT", "RUTW", "MRUT", "DJX", "OEX",
               "XEO", "NQX", "MXEA", "MXEF", "SPESG", "XAU", "OSX", "SOX", "UTY", "BKX", "RVX", "VXN")
SOURCE_CODE = {"cboe": 1.0, "occ": 2.0}
PC_COLS = ["date", "source", "calls_total", "puts_total", "calls_index", "puts_index", "calls_equity", "puts_equity",
           "calls_spx", "puts_spx", "first_seen_ms", "known_ms"]
PC_WIN, PC_MIN = 252, 60                                      # percentiles against a year of the same source's days
PC_MAX_AGE_MS = 5 * U.D_MS

# ---- earnings
NASDAQ_URL = "https://api.nasdaq.com/api/calendar/earnings"
MEGACAPS = ("NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "AVGO", "TSLA", "BRK.B", "JPM")
HABIT = {"JPM": "bmo", "BRK.B": "sat"}                        # when Nasdaq gives no time; everyone else: after the close
WHEN = {"time-pre-market": "bmo", "time-after-hours": "amc"}
ERN_COLS = ["date", "symbol", "when", "first_seen_ms", "last_seen_ms", "gone_ms"]
DAY_COLS = ["date", "checked_ms", "n_rows", "n_megacap"]
ERN_START = "2018-01-01"
ERN_PAUSE_S = 1.0
ERN_AHEAD_D = 28                                              # the calendar is read this many days ahead
ERN_NEAR_TTL_MS, ERN_FAR_TTL_MS = 6 * U.H_MS, 24 * U.H_MS     # re-ask days within a week every 6 h, further daily
ERN_PER_CALL, ERN_BACKFILL_PER_CALL = 4, 2                    # requests per update() call
LEAD_MS = 7 * U.D_MS                                          # a backfilled date counts as known 7 days ahead
NEXT_SPAN_D = 7.0                                             # ern_next: 1 at a report, 0 at 7 days away
WEEK_DAYS = 5                                                 # ern_week: reports in the next 5 trading days
WEEK_UNIT = 5.0
LAST_SPAN_H = 24.0                                            # ern_last: 1 just after a report, 0 a day later

LAST_ERRORS = {}


# ------------------------------------------------------------------ paths
def pc_path(src_dir=None):
    return os.path.join(src_dir or SRC_DIR, "putcall_daily.csv")


def ern_path(src_dir=None):
    return os.path.join(src_dir or SRC_DIR, "earnings_megacap.csv")


def days_path(src_dir=None):
    return os.path.join(src_dir or SRC_DIR, "earnings_days.csv")


def state_path(src_dir=None):
    return os.path.join(src_dir or SRC_DIR, "equity_events_state.json")


# ------------------------------------------------------------------ calendars
_TDAYS = {}


def trading_days(lo_year=2005, hi_year=None):
    hi_year = hi_year or pd.Timestamp.now("UTC").year + 2
    key = (lo_year, hi_year)
    if key not in _TDAYS:
        _TDAYS[key] = U.nyse_trading_days(lo_year, hi_year)
    return _TDAYS[key]


def pc_known_ms(dates):
    """Day D's figures -> 12:00 New York time of the next NYSE trading day (vector over 'YYYY-MM-DD')."""
    td = trading_days()
    dates = np.asarray(dates, dtype=str)
    k = np.searchsorted(td, dates, side="right")
    nxt = td[np.minimum(k, len(td) - 1)]
    return U.ny_ms_vec(nxt, 12, 0)


# ------------------------------------------------------------------ put/call storage
def load_pc(src_dir=None):
    d = U.read_csv(pc_path(src_dir), PC_COLS)
    if not len(d):
        return pd.DataFrame(columns=PC_COLS)
    d = d[PC_COLS].dropna(subset=["date"]).copy()
    d["date"] = d["date"].astype(str).str[:10]
    d["source"] = d["source"].astype(str)
    for c in PC_COLS[2:]:
        d[c] = pd.to_numeric(d[c], errors="coerce").astype(float)
    return d.drop_duplicates("date", keep="first").sort_values("date").reset_index(drop=True)


def _save_pc(old, rows, src_dir):
    new = pd.DataFrame(rows, columns=PC_COLS)
    both = pd.concat([old, new], ignore_index=True) if len(old) else new
    both = both.drop_duplicates("date", keep="first").sort_values("date")
    U.write_csv(both[PC_COLS], pc_path(src_dir))
    return len(both)


def parse_cboe(text):
    """One of Cboe's historical put/call CSVs -> frame date ('YYYY-MM-DD'), calls, puts."""
    lines = text.splitlines()
    at = next(i for i, ln in enumerate(lines) if ln.upper().startswith("DATE,"))
    d = pd.read_csv(io.StringIO("\n".join(lines[at:])), skipinitialspace=True)
    d.columns = [c.strip().upper() for c in d.columns]
    calls = d["CALLS"] if "CALLS" in d else d["CALL"]
    puts = d["PUTS"] if "PUTS" in d else d["PUT"]
    out = pd.DataFrame({"date": pd.to_datetime(d["DATE"], format="%m/%d/%Y", errors="coerce").dt.strftime("%Y-%m-%d"),
                        "calls": pd.to_numeric(calls, errors="coerce"), "puts": pd.to_numeric(puts, errors="coerce")})
    return out.dropna().drop_duplicates("date", keep="last")


def parse_occ(text):
    """OCC's volume-query CSV for one day -> dict of call and put contracts (each trade is reported once
    per side, so the sums are halved). Raises if the reply is not the CSV."""
    if not text.lstrip().lower().startswith("quantity"):
        raise ValueError(text.strip()[:120])
    d = pd.read_csv(io.StringIO(text), usecols=["quantity", "underlying", "porc"],
                    dtype={"quantity": "float64", "underlying": str, "porc": str})
    put = (d["porc"].str.upper() == "P").values
    q = d["quantity"].fillna(0.0).values
    und = d["underlying"].fillna("").str.upper()
    idx = und.isin(INDEX_ROOTS).values
    spx = und.isin(("SPX", "SPXW")).values
    s = lambda m: float(q[m].sum()) / 2.0                     # noqa: E731
    return {"calls_total": s(~put), "puts_total": s(put), "calls_index": s(idx & ~put), "puts_index": s(idx & put),
            "calls_equity": s(~idx & ~put), "puts_equity": s(~idx & put), "calls_spx": s(spx & ~put),
            "puts_spx": s(spx & put)}


def _fetch_occ(day):
    """-> ("ok", figures) | ("not_yet", msg) | ("too_old", msg). Raises on a network failure."""
    params = dict(OCC_PARAMS, reportDate=day.replace("-", ""))
    text = U.get(OCC_URL, params, pause=OCC_PAUSE_S, timeout=U.TIMEOUT_S).text
    try:
        return "ok", parse_occ(text)
    except ValueError as e:
        msg = str(e).lower()
        if "greater than" in msg:
            return "not_yet", msg
        if "prior to" in msg:
            return "too_old", msg
        if not msg.strip():
            return "not_yet", "empty reply"
        raise RuntimeError("unexpected OCC reply: %s" % msg[:80])


def _update_cboe(src_dir, state):
    """Cboe's frozen history (to Oct 2019): fetched once."""
    old = load_pc(src_dir)
    if state.get("cboe_done") or (len(old) and (old["source"] == "cboe").any()):
        state["cboe_done"] = True
        return 0
    parts = {}
    for name, f in CBOE_FILES:
        parts[name] = parse_cboe(U.get(CBOE_URL % f, pause=1.0).text).set_index("date")
    t = parts["total"]
    rows = []
    for day in t.index:
        g = lambda name, col: float(parts[name].at[day, col]) if day in parts[name].index else np.nan   # noqa: E731
        rows.append({"date": day, "source": "cboe", "calls_total": g("total", "calls"), "puts_total": g("total", "puts"),
                     "calls_index": g("index", "calls"), "puts_index": g("index", "puts"),
                     "calls_equity": g("equity", "calls"), "puts_equity": g("equity", "puts"),
                     "calls_spx": np.nan, "puts_spx": np.nan, "first_seen_ms": np.nan, "known_ms": np.nan})
    _save_pc(old, rows, src_dir)
    state["cboe_done"] = True
    return len(rows)


def _occ_days(now):
    """NYSE trading days OCC may serve, oldest first: within 2 years, and whose session has ended."""
    today = U.ny_date(now)
    lo = (pd.Timestamp(today) - pd.Timedelta(days=OCC_LOOKBACK_D - 2)).strftime("%Y-%m-%d")
    td = trading_days()
    return td[(td >= lo) & (td < today)]


def _update_occ(src_dir, state, now, backfill_n=OCC_BACKFILL_PER_CALL, live=True):
    """The newest finished trading day once it is out, then `backfill_n` older missing days. -> requests made."""
    old = load_pc(src_dir)
    have = set(old["date"]) if len(old) else set()
    skip = set(state.get("occ_too_old", []))
    tries = state.setdefault("occ_tries", {})
    missing_after = state.setdefault("occ_missing_after_release", {})
    served = _occ_days(now)
    days = [d for d in served if d not in have and d not in skip]
    if not days:
        return 0
    rows, n = [], 0
    newest = served[-1]                                       # the last finished trading day: the live read
    queue = []
    if live and newest in days and now - int(tries.get(newest, 0)) >= OCC_RETRY_MS:
        queue.append(newest)
    queue += [d for d in reversed(days) if d != newest and now - int(tries.get(d, 0)) >= OCC_RETRY_MS][:backfill_n]
    try:
        for day in queue:
            n += 1
            tries[day] = now
            status, got = _fetch_occ(day)
            if status == "ok":
                rule = int(pc_known_ms([day])[0])
                late = day in missing_after and missing_after[day] > rule
                got.update({"date": day, "source": "occ", "first_seen_ms": float(U.now_ms()),
                            "known_ms": float(U.now_ms()) if late else np.nan})
                rows.append(got)
                tries.pop(day, None)
                missing_after.pop(day, None)
            elif status == "too_old":
                skip.add(day)
            elif now > int(pc_known_ms([day])[0]):
                missing_after.setdefault(day, now)            # due and not there: it will count from when it is seen
    finally:
        if rows:
            _save_pc(old, rows, src_dir)
        state["occ_too_old"] = sorted(skip)[-50:]
        for d in list(tries):                                 # forget attempts on days that have aged out
            if d < (days[0] if days else "9999"):
                tries.pop(d, None)
    return n


# ------------------------------------------------------------------ earnings storage
def load_ern(src_dir=None):
    d = U.read_csv(ern_path(src_dir), ERN_COLS, dtype={"date": str, "symbol": str, "when": str})
    if not len(d):
        return pd.DataFrame(columns=ERN_COLS)
    d = d[ERN_COLS].dropna(subset=["date", "symbol"]).copy()
    d["when"] = d["when"].fillna("").astype(str).replace("nan", "")
    for c in ("first_seen_ms", "last_seen_ms", "gone_ms"):
        d[c] = pd.to_numeric(d[c], errors="coerce").astype(float)
    return d.drop_duplicates(["date", "symbol"], keep="last").sort_values(["date", "symbol"]).reset_index(drop=True)


def load_days(src_dir=None):
    d = U.read_csv(days_path(src_dir), DAY_COLS, dtype={"date": str})
    if not len(d):
        return pd.DataFrame(columns=DAY_COLS)
    d = d[DAY_COLS].dropna(subset=["date"]).copy()
    for c in DAY_COLS[1:]:
        d[c] = pd.to_numeric(d[c], errors="coerce").astype(float)
    return d.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)


def parse_nasdaq(payload):
    """Nasdaq's calendar JSON for one day -> (rows in total, [(symbol, when)] for the megacaps)."""
    rows = ((payload or {}).get("data") or {}).get("rows") or []
    out = []
    for r in rows:
        sym = str(r.get("symbol") or "").strip().upper().replace("/", ".")
        if sym in MEGACAPS:
            out.append((sym, WHEN.get(str(r.get("time") or ""), "")))
    return len(rows), out


def _apply_day(ern, days, day, got, n_rows, now):
    """Merge one asked day into the tables (in place on copies) -> (ern, days)."""
    on = ern["date"] == day
    listed = dict(got)
    for i in ern.index[on]:
        sym = ern.at[i, "symbol"]
        if sym in listed:
            ern.at[i, "last_seen_ms"] = float(now)
            if listed[sym]:
                ern.at[i, "when"] = listed[sym]
            if np.isfinite(ern.at[i, "gone_ms"]):
                ern.at[i, "gone_ms"] = np.nan                 # back on the calendar
        elif not np.isfinite(ern.at[i, "gone_ms"]):
            ern.at[i, "gone_ms"] = float(now)                 # no longer listed on that day: moved or cancelled
    have = set(ern.loc[on, "symbol"])
    add = [{"date": day, "symbol": s, "when": w, "first_seen_ms": float(now), "last_seen_ms": float(now),
            "gone_ms": np.nan} for s, w in got if s not in have]
    if add:
        ern = pd.concat([ern, pd.DataFrame(add, columns=ERN_COLS)], ignore_index=True)
    days = days[days["date"] != day]
    days = pd.concat([days, pd.DataFrame([{"date": day, "checked_ms": float(now), "n_rows": float(n_rows),
                                           "n_megacap": float(len(got))}])], ignore_index=True)
    return ern, days


def _ask_days(now):
    """-> calendar days worth asking for, newest information first: (window days due, backfill days)."""
    today = pd.Timestamp(U.ny_date(now))
    window = [(today + pd.Timedelta(days=k)) for k in range(-3, ERN_AHEAD_D + 1)]
    window = [d for d in window if d.dayofweek != 6]
    hist = pd.date_range(ERN_START, today - pd.Timedelta(days=4), freq="D")
    hist = hist[hist.dayofweek != 6]
    return [d.strftime("%Y-%m-%d") for d in window], [d.strftime("%Y-%m-%d") for d in hist[::-1]]


def _update_earnings(src_dir, now, per_call=ERN_PER_CALL, backfill_n=ERN_BACKFILL_PER_CALL):
    ern, days = load_ern(src_dir), load_days(src_dir)
    checked = dict(zip(days["date"], days["checked_ms"])) if len(days) else {}
    window, hist = _ask_days(now)
    today = U.ny_date(now)
    due = []
    for d in window:
        last = checked.get(d)
        if last is None:
            due.append(d)
        elif d < today:
            if last < U.ny_ms((pd.Timestamp(d) + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), 0):
                due.append(d)                                 # asked before the day was over: ask once more
        else:
            ttl = ERN_NEAR_TTL_MS if (pd.Timestamp(d) - pd.Timestamp(today)).days <= 7 else ERN_FAR_TTL_MS
            if now - last >= ttl:
                due.append(d)
    queue = due[:per_call] + [d for d in hist if d not in checked][:backfill_n]
    n, err = 0, None
    try:
        for d in queue:
            payload = U.get(NASDAQ_URL, {"date": d}, pause=ERN_PAUSE_S).json()
            n_rows, got = parse_nasdaq(payload)
            code = ((payload or {}).get("status") or {}).get("rCode") if isinstance(payload, dict) else None
            if code not in (200, None) or not isinstance(payload, dict):
                raise RuntimeError("unexpected reply for %s: %s" % (d, str(payload)[:80]))
            ern, days = _apply_day(ern, days, d, got, n_rows, U.now_ms())
            n += 1
    except Exception as e:
        err = e
    if n:
        U.write_csv(ern.sort_values(["date", "symbol"])[ERN_COLS], ern_path(src_dir))
        U.write_csv(days.sort_values("date")[DAY_COLS], days_path(src_dir))
    if err is not None:
        raise RuntimeError("%s (asked %d days first)" % (str(err)[:120], n))
    return n


# ------------------------------------------------------------------ update
def update(log=print, src_dir=None):
    """Keep the three files fresh. -> {source: what happened, or "failed: why"}. Never raises.
    Cheap: put/call asks OCC for a day only once its session is over (then hourly until it is out) and
    fills in at most one older day per call; the earnings calendar re-asks a day within a week every
    6 hours, further days daily, at most 4 days (+2 history days) per call, a pause between requests."""
    out = OrderedDict()
    state = U.load_state(state_path(src_dir))
    now = U.now_ms()
    jobs = (("putcall_cboe", lambda: _update_cboe(src_dir, state)),
            ("putcall_occ", lambda: _update_occ(src_dir, state, now)),
            ("earnings", lambda: _update_earnings(src_dir, now)))
    for name, job in jobs:
        try:
            out[name] = "%d requests" % int(job()) if name != "putcall_cboe" else "%d rows added" % int(job())
        except Exception as e:
            out[name] = "failed: %s" % (str(e)[:150] or type(e).__name__)
        try:
            log("sources.equity_events %s: %s" % (name, out[name]))
        except Exception:
            pass
    U.save_state(state_path(src_dir), state)
    return out


def backfill(log=print, src_dir=None, occ_days=None, earnings_days=None):
    """One-off history fill (not called by the live loop): up to `occ_days` OCC days and `earnings_days`
    calendar days, newest first, with the usual pauses. Safe to stop and run again."""
    state = U.load_state(state_path(src_dir))
    done = {"occ": 0, "earnings": 0}
    try:
        _update_cboe(src_dir, state)
    except Exception as e:
        log("cboe failed: %s" % e)
    left = occ_days or 0
    while left > 0:
        k = min(10, left)
        try:
            n = _update_occ(src_dir, state, U.now_ms(), backfill_n=k, live=False)
        except Exception as e:
            log("occ failed: %s" % str(e)[:120])
            time.sleep(30)
            n = 1
        U.save_state(state_path(src_dir), state)
        if n == 0:
            break
        done["occ"] += n
        left -= n
        log("occ: %d days asked, %d rows on file" % (done["occ"], len(load_pc(src_dir))))
    left = earnings_days or 0
    while left > 0:
        k = min(20, left)
        try:
            n = _update_earnings(src_dir, U.now_ms(), per_call=0, backfill_n=k)
        except Exception as e:
            log("earnings failed: %s" % str(e)[:120])
            time.sleep(30)
            n = 1
        if n == 0:
            break
        done["earnings"] += n
        left -= n
        log("earnings: %d days asked" % done["earnings"])
    return done


# ------------------------------------------------------------------ readings: put/call
def _pctile(s, win=PC_WIN, minp=PC_MIN):
    return s.rolling(win, min_periods=minp).rank(pct=True)


def pc_table(src_dir=None):
    """-> one row per day with ratios, 10-day average and percentiles, each computed within its own source."""
    d = load_pc(src_dir)
    if not len(d):
        return d
    parts = []
    for src, g in d.groupby("source", sort=False):
        g = g.sort_values("date").copy()
        r = lambda p, c: g[p] / g[c].where(g[c] > 0)          # noqa: E731
        g["total"], g["index"], g["equity"], g["spx"] = (r("puts_total", "calls_total"), r("puts_index", "calls_index"),
                                                         r("puts_equity", "calls_equity"), r("puts_spx", "calls_spx"))
        g["total_10d"] = g["total"].rolling(10, min_periods=8).mean()
        for c in ("total", "total_10d", "index", "equity"):
            g[c + "_p"] = _pctile(g[c])
        g["code"] = SOURCE_CODE.get(src, np.nan)
        parts.append(g)
    d = pd.concat(parts).sort_values("date").reset_index(drop=True)
    rule = pc_known_ms(d["date"].values)
    late = d["known_ms"].values
    known = np.where(np.isfinite(late), np.maximum(np.nan_to_num(late, nan=0).astype("int64"), rule), rule)
    d["known_at"] = np.maximum.accumulate(known)              # a day is used only once every earlier day is known
    d["date_ms"] = U.ny_ms_vec(d["date"].values, 16, 0)
    return d


def _putcall(out, close_ms, src_dir):
    t = pc_table(src_dir)
    if not len(t):
        return
    k = t["known_at"].values
    j = lambda c: U.asof(k, t[c].values, close_ms, PC_MAX_AGE_MS)            # noqa: E731
    for f, c in (("pc_total", "total_p"), ("pc_total_10d", "total_10d_p"), ("pc_index", "index_p"),
                 ("pc_equity", "equity_p")):
        out[f] = 2.0 * j(c) - 1.0
    for f, c in (("pc_total_ratio", "total"), ("pc_index_ratio", "index"), ("pc_equity_ratio", "equity"),
                 ("pc_spx_ratio", "spx"), ("pc_total_10d_avg", "total_10d"), ("pc_source", "code")):
        out[f] = j(c)
    out["pc_total_pctile"] = 100.0 * j("total_p")
    out["pc_equity_pctile"] = 100.0 * j("equity_p")
    out["pc_day_age_d"] = (close_ms - j("date_ms")) / float(U.D_MS)


# ------------------------------------------------------------------ readings: earnings
def release_ms(dates, symbols, whens):
    """-> epoch ms each report is out: before the open 07:00 ET, after the close 16:05 ET, Berkshire 08:00 ET."""
    dates = np.asarray(dates, dtype=str)
    w = np.array([wh if wh in ("bmo", "amc") else HABIT.get(s, "amc") for s, wh in zip(symbols, whens)], dtype=object)
    out = U.ny_ms_vec(dates, 16, 5)
    if (w == "bmo").any():
        out[w == "bmo"] = U.ny_ms_vec(dates[w == "bmo"], 7, 0)
    if (w == "sat").any():
        out[w == "sat"] = U.ny_ms_vec(dates[w == "sat"], 8, 0)
    return out


def events(src_dir=None):
    """-> the stored megacap reports with release_ms, known_ms and gone_ms (inf = still listed), oldest first."""
    e = load_ern(src_dir)
    if not len(e):
        return e.assign(release_ms=pd.Series(dtype="int64"), known_ms=pd.Series(dtype="int64"),
                        gone=pd.Series(dtype=float))
    e = e.copy()
    e["release_ms"] = release_ms(e["date"].values, e["symbol"].values, e["when"].values)
    first = e["first_seen_ms"].fillna(np.inf).values
    live = first < e["release_ms"].values                     # seen on the calendar before it happened
    e["known_ms"] = np.where(live, np.nan_to_num(first, posinf=0), e["release_ms"].values - LEAD_MS).astype("int64")
    e["gone"] = e["gone_ms"].fillna(np.inf).astype(float)
    return e.sort_values("release_ms").reset_index(drop=True)


def _coverage(close_ms, src_dir):
    """-> bool per close: every weekday from the day before to 7 days after the close's New York date was asked."""
    days = load_days(src_dir)
    if not len(days):
        return np.zeros(len(close_ms), dtype=bool)
    asked = pd.DatetimeIndex(pd.to_datetime(days["date"]))
    lo, hi = asked.min(), asked.max()
    cal = pd.date_range(lo, hi, freq="D")
    ok = pd.Series(cal.isin(asked) | (cal.dayofweek >= 5), index=cal)      # weekends need not be asked
    span = ok.astype(int).rolling(9, min_periods=9).sum() == 9             # D-1 .. D+7 all asked
    span = span.shift(-7)                                                  # label each window by D
    ny = pd.to_datetime(close_ms, unit="ms", utc=True).tz_convert(U.NY).tz_localize(None).normalize()
    res = span.reindex(ny).fillna(False).values.astype(bool)
    return res


def _earnings(out, close_ms, src_dir):
    e = events(src_dir)
    cover = _coverage(close_ms, src_dir)
    if not cover.any():
        return
    n = len(close_ms)
    rel, known, gone = e["release_ms"].values, e["known_ms"].values, e["gone"].values
    nxt = np.full(n, np.inf)
    last = np.full(n, -np.inf)
    n5 = np.zeros(n)
    n24 = np.zeros(n)
    td = trading_days()
    ny = pd.to_datetime(close_ms, unit="ms", utc=True).tz_convert(U.NY).strftime("%Y-%m-%d").values
    k = np.searchsorted(td, ny, side="right") + WEEK_DAYS - 1                 # the 5th trading day after today
    horizon = U.ny_ms_vec(td[np.minimum(k, len(td) - 1)], 23, 59)
    c = close_ms.astype(float)
    for r, kn, g in zip(rel, known, gone):
        lo = np.searchsorted(close_ms, kn, side="left")                      # rows from when it was known ...
        hi = np.searchsorted(close_ms, g, side="left") if np.isfinite(g) else n
        if lo < hi:                                                          # ... until it was seen gone
            sl = slice(lo, hi)
            ahead = (c[sl] < r)
            nxt[sl] = np.where(ahead, np.minimum(nxt[sl], r), nxt[sl])
            n5[sl] += (ahead & (r <= horizon[sl]))
        if g > r:                                                            # it happened (not moved before)
            a = np.searchsorted(close_ms, r, side="left")
            if a < n:
                last[a:] = np.maximum(last[a:], r)
                b = np.searchsorted(close_ms, r + LAST_SPAN_H * U.H_MS, side="left")
                n24[a:b] += 1
    days_next = (nxt - c) / U.D_MS
    hours_since = (c - last) / U.H_MS
    days_next = np.where(np.isfinite(days_next) & (days_next <= NEXT_SPAN_D), days_next, np.nan)
    hours_since = np.where(np.isfinite(hours_since), hours_since, np.nan)
    out["ern_days_next"] = np.where(cover, days_next, np.nan)
    out["ern_n_next5"] = np.where(cover, n5, np.nan)
    out["ern_hours_since"] = np.where(cover & (hours_since <= 30 * 24), hours_since, np.nan)
    out["ern_n_last24"] = np.where(cover, n24, np.nan)
    out["ern_next"] = np.where(cover, np.clip(1.0 - days_next / NEXT_SPAN_D, 0, 1), np.nan)
    out["ern_week"] = np.where(cover, np.clip(n5 / WEEK_UNIT, 0, 1), np.nan)
    out["ern_last"] = np.where(cover, np.clip(1.0 - hours_since / LAST_SPAN_H, 0, 1), np.nan)


def features(index15, asset, bars=None, src_dir=None):
    """-> frame on index15 (15m bar OPEN times, UTC): FEATURES (0.0 = no read, never NaN) and RAW (NaN = no read).
    Only SPX gets readings; any other asset gets an all-no-read frame."""
    index15 = pd.DatetimeIndex(index15)
    close_ms = np.asarray(index15.as_unit("ms").asi8, dtype="int64") + U.BAR_MS
    out = pd.DataFrame(np.nan, index=index15, columns=FEATURES + RAW)
    LAST_ERRORS.clear()
    if asset == ASSET and len(close_ms):
        order = np.argsort(close_ms, kind="stable")
        work = pd.DataFrame(np.nan, index=np.arange(len(close_ms)), columns=FEATURES + RAW)
        for name, fn in (("putcall", _putcall), ("earnings", _earnings)):
            try:
                fn(work, close_ms[order], src_dir)
            except Exception as e:                            # a broken file silences its card, not the engine
                LAST_ERRORS[name] = "%s: %s" % (type(e).__name__, str(e)[:160])
                pre = "pc_" if name == "putcall" else "ern_"
                work[[c for c in FEATURES + RAW if c.startswith(pre)]] = np.nan
        back = np.empty_like(order)
        back[order] = np.arange(len(order))
        out[:] = work.values[back]
    out[FEATURES] = out[FEATURES].astype(float).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    out.attrs["errors"] = dict(LAST_ERRORS)
    return out


# ------------------------------------------------------------------ plain English
def _close_ms(row):
    try:
        return int(pd.Timestamp(row.name).value // 1000000) + U.BAR_MS
    except Exception:
        return U.now_ms()


def _pc_day(row):
    age = U.num(row, "pc_day_age_d")
    if age is None:
        return "the last day"
    return pd.Timestamp(_close_ms(row) - age * U.D_MS, unit="ms", tz="UTC").tz_convert(U.NY).strftime("%a %d %b %Y")


def _upcoming(close_ms, src_dir=None):
    """-> [(release_ms, symbol, when)] known at close_ms and not gone, released after it, within 14 days."""
    e = events(src_dir)
    if not len(e):
        return []
    m = (e["known_ms"] <= close_ms) & (e["gone"] > close_ms) & (e["release_ms"] > close_ms) & \
        (e["release_ms"] <= close_ms + 14 * U.D_MS)
    return [(int(r.release_ms), r.symbol, r.when) for r in e[m].itertuples()]


def _recent(close_ms, src_dir=None, hours=72):
    e = events(src_dir)
    if not len(e):
        return []
    m = (e["release_ms"] <= close_ms) & (e["release_ms"] > close_ms - hours * U.H_MS) & (e["gone"] > e["release_ms"])
    return [(int(r.release_ms), r.symbol, r.when) for r in e[m].itertuples()]


def _when_words(sym, when, ms):
    w = when if when in ("bmo", "amc") else HABIT.get(sym, "amc")
    day = pd.Timestamp(ms, unit="ms", tz="UTC").tz_convert(U.NY).strftime("%a %d %b")
    tag = {"bmo": "before the open", "amc": "after the close", "sat": "Saturday morning"}[w]
    return "%s %s %s%s" % (sym, day, tag, "" if when in ("bmo", "amc") else " (usual time; not confirmed)")


def describe(row, asset):
    """One row of features() -> {card title: one plain-English sentence}. States what was read; forecasts nothing."""
    say = OrderedDict()
    tp, te = GROUPS["putcall"][0], GROUPS["earnings"][0]
    if asset != ASSET:
        return OrderedDict([(tp, "Put/call ratios are read for the S&P 500 only."),
                            (te, "Megacap earnings are read for the S&P 500 only.")])
    tot = U.num(row, "pc_total_ratio")
    if tot is None:
        say[tp] = ("No put/call read at this close: Cboe's free history ends 4 Oct 2019 and OCC serves only the last "
                   "two years, so days outside those spans (or a feed that has not updated) have no figure.")
    else:
        src = "Cboe exchange" if U.num(row, "pc_source") == 1.0 else "all US exchanges (OCC)"
        bits = ["total put/call %.2f" % tot]
        if U.num(row, "pc_total_10d_avg") is not None:
            bits.append("10-day average %.2f" % U.num(row, "pc_total_10d_avg"))
        if U.num(row, "pc_total_pctile") is not None:
            bits.append("%s percentile of its last year" % U.ordinal(U.num(row, "pc_total_pctile")))
        if U.num(row, "pc_index_ratio") is not None:
            bits.append("index options %.2f" % U.num(row, "pc_index_ratio"))
        if U.num(row, "pc_equity_ratio") is not None:
            bits.append("equity options %.2f" % U.num(row, "pc_equity_ratio"))
        say[tp] = "Options volume on %s, %s: %s." % (_pc_day(row), src, "; ".join(bits))
    days, n5, hrs = U.num(row, "ern_days_next"), U.num(row, "ern_n_next5"), U.num(row, "ern_hours_since")
    if n5 is None:
        say[te] = "No megacap earnings read at this close: the calendar does not cover these days."
    else:
        c = _close_ms(row)
        up = _upcoming(c)
        s = ("Next megacap report: %s (in %.1f days)" % (_when_words(*up[0][1:], up[0][0]), days)
             if up and days is not None else "No megacap report in the next 7 days")
        s += "; %d of the ten report in the next 5 trading days" % n5
        rec = _recent(c, hours=24)
        if rec:
            s += "; reported in the last 24 hours: %s" % ", ".join(r[1] for r in rec)
        elif hrs is not None:
            s += "; the last megacap report was %.0f hours ago" % hrs
        say[te] = s + "."
    return say


def facts(row, asset):
    """One row of features() -> {card title: [[label, value], ...]}: ratios, dates and names a person reads."""
    tp, te = GROUPS["putcall"][0], GROUPS["earnings"][0]
    if asset != ASSET:
        return {}
    pc = []
    if U.num(row, "pc_total_ratio") is None:
        pc.append(["Status", "no put/call figure for this close (Cboe history ends Oct 2019; OCC serves 2 years)"])
    else:
        pc.append(["Day", "%s (%s)" % (_pc_day(row), "Cboe exchange only" if U.num(row, "pc_source") == 1.0
                                       else "all US exchanges, OCC cleared volume")])
        for lab, key in (("Total put/call", "pc_total_ratio"), ("10-day average", "pc_total_10d_avg"),
                         ("Index options put/call", "pc_index_ratio"), ("Equity options put/call", "pc_equity_ratio"),
                         ("SPX options put/call", "pc_spx_ratio")):
            v = U.num(row, key)
            if v is not None:
                pc.append([lab, "%.2f" % v])
        for lab, key in (("Total, percentile of last year", "pc_total_pctile"),
                         ("Equity, percentile of last year", "pc_equity_pctile")):
            v = U.num(row, key)
            pc.append([lab, "n/a (under 60 days of this source)" if v is None else "%.0f" % v])
    er = [["Watch list", ", ".join(MEGACAPS)]]
    if U.num(row, "ern_n_next5") is None:
        er.append(["Status", "the earnings calendar does not cover this close"])
    else:
        c = _close_ms(row)
        up = _upcoming(c)
        today = U.ny_date(c)
        wk_end = (pd.Timestamp(today) + pd.Timedelta(days=6 - pd.Timestamp(today).dayofweek)).strftime("%Y-%m-%d")
        this_w = [u for u in up if U.ny_date(u[0]) <= wk_end]
        next_w = [u for u in up if U.ny_date(u[0]) > wk_end]
        er.append(["This week", "; ".join(_when_words(s, w, r) for r, s, w in this_w) or "none"])
        er.append(["Next week", "; ".join(_when_words(s, w, r) for r, s, w in next_w) or "none"])
        er.append(["Reports in the next 5 trading days", "%d" % U.num(row, "ern_n_next5")])
        rec = _recent(c, hours=24)
        er.append(["Reported in the last 24 hours", ", ".join(_when_words(s, w, r) for r, s, w in rec) or "none"])
    return {tp: pc, te: er}
