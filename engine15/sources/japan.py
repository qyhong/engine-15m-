# -*- coding: utf-8 -*-
"""japan -- "Japan watch" for USDJPY: Bank of Japan meetings, Japan's releases, and intervention risk.

Three kinds of data point:

  BoJ decisions      the Bank of Japan's published Monetary Policy Meeting dates, 2018 to 2027
                     (BOJ_MEETINGS, from boj.or.jp). The decision is taken as out at 03:00 UTC (12:00
                     Tokyo) on the meeting's last day; the BoJ has no fixed time, usually 11:30-13:00 JST.
  JPY releases       every JPY event of the ForexFactory weekly calendar feed the engine already reads
                     for US releases (nfs.faireconomy.media/ff_calendar_thisweek.json), kept in
                     data/sources/jpy_events.csv. The feed shows only the current week, so this history
                     starts on the first run (10 Nov 2026) and grows; before it there is no read.
  Intervention risk  the Ministry of Finance's yen-buying interventions since 2022 (INTERVENTIONS, kept
                     as data in data/sources/jpy_interventions.csv: date, the USDJPY high that day from this
                     project's own bars, the amount from the MoF's published figures, and when the MoF
                     confirmed it), set against where USDJPY is now and how fast it got there, since speed
                     is what officials cite ("rapid, one-sided moves").

THE ONE RULE (tests/test_japan.py): a row uses only what was public at its 15m close.
  - a meeting date counts from 180 days before it (they are published a year ahead), except the 2020
    emergency changes, which count from the day they were announced or held (see BOJ_SPECIAL);
  - a feed event counts from the moment update() first saw it in the feed;
  - an intervention counts from the MoF's confirmation (same day on 22 Sep 2022, otherwise the monthly
    total published at 19:00 Tokyo on the month's last business day);
  - price speed uses the project's own closed USDJPY bars up to the row's own close.

Docs: docs/SOURCES_japan.md. No reading here is claimed to predict anything.
"""
import os
from collections import OrderedDict

import numpy as np
import pandas as pd

from . import _util as U
from ..config import DATA_DIR

SRC_DIR = os.path.join(DATA_DIR, "sources")
ASSET = "USDJPY"
FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
FEED_EVERY_MS = 3 * U.H_MS                                    # the weekly feed is asked at most every 3 hours
FEED_STALE_MS = 8 * U.D_MS                                    # a feed not read for 8 days: no release read

GROUPS = OrderedDict([("japan", ("Japan watch", ["jp_boj_next", "jp_event_next", "jp_mof_zone", "jp_speed_1w",
                                                 "jp_speed_1m", "jp_risk"]))])
APPLIES = {"japan": (ASSET,)}
FEATURES = [f for _t, fs in GROUPS.values() for f in fs]
RAW = ["jp_px", "jp_boj_hours", "jp_event_hours", "jp_mof_level", "jp_mof_dist_pct", "jp_mof_top_dist_pct",
       "jp_days_since_mof",
       "jp_chg_1w_pct", "jp_chg_1m_pct", "jp_speed_1w_z", "jp_speed_1m_z"]

BOJ_SPAN_H = 168.0                                            # jp_boj_next: 1 at the decision, 0 a week before
EVENT_SPAN_H = 24.0                                           # jp_event_next: 1 at the release, 0 a day before
ZONE_PCT = 5.0                                                # jp_mof_zone: 1 at an intervention level, 0 at 5% below
SPEED_UNIT = 3.0                                              # a move of 3 standard deviations of its kind = 1.0
NORM_DAYS, NORM_MIN_BARS = 365, 96 * 60                       # norms over a year of bars; ~60 trading days to speak
GAP_MS = 4 * U.D_MS                                           # the price "a week ago" may be up to 4 days older (weekends)
DECISION_UTC_H = 3                                            # 12:00 Tokyo

# Last day of each Monetary Policy Meeting (boj.or.jp, "Monetary Policy Meetings" and the past-meetings page).
BOJ_MEETINGS = (
    "2018-01-23", "2018-03-09", "2018-04-27", "2018-06-15", "2018-07-31", "2018-09-19", "2018-10-31", "2018-12-20",
    "2019-01-23", "2019-03-15", "2019-04-25", "2019-06-20", "2019-07-30", "2019-09-19", "2019-10-31", "2019-12-19",
    "2020-01-21", "2020-03-16", "2020-04-27", "2020-05-22", "2020-06-16", "2020-07-15", "2020-09-17", "2020-10-29",
    "2020-12-18",
    "2021-01-21", "2021-03-19", "2021-04-27", "2021-06-18", "2021-07-16", "2021-09-22", "2021-10-28", "2021-12-17",
    "2022-01-18", "2022-03-18", "2022-04-28", "2022-06-17", "2022-07-21", "2022-09-22", "2022-10-28", "2022-12-20",
    "2023-01-18", "2023-03-10", "2023-04-28", "2023-06-16", "2023-07-28", "2023-09-22", "2023-10-31", "2023-12-19",
    "2024-01-23", "2024-03-19", "2024-04-26", "2024-06-14", "2024-07-31", "2024-09-20", "2024-10-31", "2024-12-19",
    "2025-01-24", "2025-03-19", "2025-05-01", "2025-06-17", "2025-07-31", "2025-09-19", "2025-10-30", "2025-12-19",
    "2026-01-23", "2026-03-19", "2026-04-28", "2026-06-16", "2026-07-31", "2026-09-18", "2026-10-30", "2026-12-18",
    "2027-01-22", "2027-03-18", "2027-04-28", "2027-06-11", "2027-07-22", "2027-09-22", "2027-10-29", "2027-12-17",
)
# 2020: the March meeting was brought forward to 16 Mar (announced Fri 13 Mar), April's was cut to one day,
# and 22 May was an extra meeting. date -> (counts from, the scheduled date it replaced or None).
BOJ_SPECIAL = {"2020-03-16": ("2020-03-13", "2020-03-19"), "2020-04-27": ("2020-04-27", "2020-04-28"),
               "2020-05-22": ("2020-05-22", None)}
BOJ_LEAD_D = 180

# Yen-buying interventions (Ministry of Finance, "Foreign Exchange Intervention Operations"). level = the
# USDJPY high that day in this project's bars; amount in JPY billion; confirmed = when the MoF said so (UTC).
INT_COLS = ["date", "level", "amount_jpy_bn", "confirmed_utc", "note"]
INTERVENTIONS = (
    ("2022-09-22", 145.90, 2838.2, "2022-09-22 09:00", "first since 1998; announced the same day"),
    ("2022-10-21", 151.94, 5620.2, "2022-10-31 10:00", "not announced; in the October total (MoF 31 Oct 2022)"),
    ("2022-10-24", 149.45, 729.6, "2022-10-31 10:00", "not announced; in the October total"),
    ("2024-04-29", 160.20, 5918.5, "2024-05-31 10:00", "after a 34-year low near 160.2; in the Apr-May total"),
    ("2024-05-01", 157.98, 3870.0, "2024-05-31 10:00", "after the FOMC; in the Apr-May total"),
    ("2024-07-11", 161.75, 3167.8, "2024-07-31 10:00", "after US CPI; the cycle high was 161.94 on 3 Jul"),
    ("2024-07-12", 159.38, 2367.0, "2024-07-31 10:00", "in the July total"),
    ("2026-04-30", 160.72, 6278.7, "2026-05-29 10:00", "record single day; in the Apr-May total"),
    ("2026-05-04", 157.30, 780.2, "2026-05-29 10:00", "Golden Week; in the Apr-May total"),
    ("2026-05-06", 157.89, 4675.9, "2026-05-29 10:00", "Golden Week; in the Apr-May total"),
)
EV_COLS = ["ts_ms", "title", "impact", "forecast", "previous", "first_seen_ms"]


# ------------------------------------------------------------------ files
def events_path(src_dir=None):
    return os.path.join(src_dir or SRC_DIR, "jpy_events.csv")


def interventions_path(src_dir=None):
    return os.path.join(src_dir or SRC_DIR, "jpy_interventions.csv")


def state_path(src_dir=None):
    return os.path.join(src_dir or SRC_DIR, "japan_state.json")


def load_events(src_dir=None):
    d = U.read_csv(events_path(src_dir), EV_COLS, dtype={"title": str, "impact": str, "forecast": str, "previous": str})
    if not len(d):
        return pd.DataFrame(columns=EV_COLS)
    d = d[EV_COLS].dropna(subset=["ts_ms"]).copy()
    d["ts_ms"] = pd.to_numeric(d["ts_ms"], errors="coerce").astype("int64")
    d["first_seen_ms"] = pd.to_numeric(d["first_seen_ms"], errors="coerce").astype(float)
    for c in ("title", "impact", "forecast", "previous"):
        d[c] = d[c].fillna("").astype(str).replace("nan", "")
    return d.drop_duplicates(["ts_ms", "title"], keep="first").sort_values("ts_ms").reset_index(drop=True)


def load_interventions(src_dir=None):
    """-> frame date, level, amount_jpy_bn, confirmed_ms, date_ms. The file wins when it exists (the owner may add rows)."""
    path = interventions_path(src_dir)
    d = U.read_csv(path, INT_COLS, dtype={"date": str, "confirmed_utc": str, "note": str}) if os.path.exists(path) \
        else pd.DataFrame(list(INTERVENTIONS), columns=INT_COLS)
    if not len(d):
        d = pd.DataFrame(list(INTERVENTIONS), columns=INT_COLS)
    d = d.dropna(subset=["date", "level", "confirmed_utc"]).copy()
    d["level"] = pd.to_numeric(d["level"], errors="coerce")
    d["amount_jpy_bn"] = pd.to_numeric(d["amount_jpy_bn"], errors="coerce")
    d["confirmed_ms"] = U.to_ms_vec(d["confirmed_utc"].values)
    d["date_ms"] = U.to_ms_vec(d["date"].values)
    return d.dropna(subset=["level"]).sort_values("date").reset_index(drop=True)


def boj_decisions():
    """-> frame decision_ms, known_ms, gone_ms (inf = never withdrawn), date."""
    rows = []
    replaced = dict((old, new_from) for _new, (new_from, old) in BOJ_SPECIAL.items() if old)
    for day in list(BOJ_MEETINGS) + list(replaced):
        dec = int(pd.Timestamp(day, tz="UTC").value // 1000000) + DECISION_UTC_H * U.H_MS
        if day in BOJ_SPECIAL:
            known = int(pd.Timestamp(BOJ_SPECIAL[day][0], tz="UTC").value // 1000000)
        else:
            known = dec - BOJ_LEAD_D * U.D_MS
        gone = float(pd.Timestamp(replaced[day], tz="UTC").value // 1000000) if day in replaced else np.inf
        rows.append((dec, known, gone, day))
    return pd.DataFrame(rows, columns=["decision_ms", "known_ms", "gone_ms", "date"]).sort_values("decision_ms") \
        .reset_index(drop=True)


# ------------------------------------------------------------------ update
def parse_feed(feed):
    """ForexFactory's weekly JSON -> list of (ts_ms, title, impact, forecast, previous) for JPY events."""
    out = []
    for e in feed or []:
        if str(e.get("country", "")).upper() != "JPY":
            continue
        try:
            ts = int(pd.Timestamp(e["date"]).tz_convert("UTC").value // 1000000)
        except Exception:
            continue
        out.append((ts, str(e.get("title") or ""), str(e.get("impact") or ""), str(e.get("forecast") or ""),
                    str(e.get("previous") or "")))
    return out


def update(log=print, src_dir=None):
    """Read the weekly calendar feed (at most every 3 hours) and keep the intervention table on disk.
    -> {source: rows on disk / "kept", or "failed: why"}. Never raises."""
    out = OrderedDict()
    state = U.load_state(state_path(src_dir))
    try:
        if not os.path.exists(interventions_path(src_dir)):
            U.write_csv(pd.DataFrame(list(INTERVENTIONS), columns=INT_COLS), interventions_path(src_dir))
        out["interventions"] = len(load_interventions(src_dir))
    except Exception as e:
        out["interventions"] = "failed: %s" % str(e)[:120]
    try:
        now = U.now_ms()
        if now - int(state.get("last_feed_ms", 0)) < FEED_EVERY_MS:
            out["jpy_events"] = "kept (read %.1f h ago)" % ((now - int(state["last_feed_ms"])) / float(U.H_MS))
        else:
            feed = U.get(FF_URL, pause=1.0).json()
            if not isinstance(feed, list) or not feed:
                raise RuntimeError("unexpected reply: %s" % str(feed)[:80])
            got = parse_feed(feed)
            old = load_events(src_dir)
            seen = set(zip(old["ts_ms"], old["title"])) if len(old) else set()
            add = [r + (float(now),) for r in got if (r[0], r[1]) not in seen]
            if add or not os.path.exists(events_path(src_dir)):
                new = pd.DataFrame(add, columns=EV_COLS)
                both = pd.concat([old, new], ignore_index=True) if len(old) else new
                U.write_csv(both.sort_values("ts_ms")[EV_COLS], events_path(src_dir))
            state["last_feed_ms"] = now
            state.setdefault("first_feed_ms", now)
            out["jpy_events"] = len(load_events(src_dir))
    except Exception as e:
        out["jpy_events"] = "failed: %s" % (str(e)[:120] or type(e).__name__)
    U.save_state(state_path(src_dir), state)
    for k, v in out.items():
        try:
            log("sources.japan %s: %s" % (k, v))
        except Exception:
            pass
    return out


# ------------------------------------------------------------------ readings
def _next_after(close_ms, when_ms, known_ms, gone_ms=None):
    """-> for each close, the first `when` after it among items known at or before it (and not withdrawn), else inf."""
    n = len(close_ms)
    best = np.full(n, np.inf)
    if gone_ms is None:
        gone_ms = np.full(len(when_ms), np.inf)
    for w, k, g in zip(when_ms, known_ms, gone_ms):
        lo = np.searchsorted(close_ms, k, side="left")
        hi = n if not np.isfinite(g) else np.searchsorted(close_ms, g, side="left")
        hi = min(hi, np.searchsorted(close_ms, w, side="left"))              # only while it is still ahead
        if lo < hi:
            best[lo:hi] = np.minimum(best[lo:hi], w)
    return best


def _speed(bars, close_ms):
    """-> dict of readable price-speed arrays on the rows (NaN where there is no read)."""
    c = bars["close"].astype(float).values
    t = np.asarray(bars.index.as_unit("ms").asi8, dtype="int64") + U.BAR_MS            # bar close times
    ok = np.isfinite(c) & (c > 0)
    c, t = c[ok], t[ok]
    out = {}
    if len(c) < 10:
        return out

    def back(span):
        k = np.searchsorted(t, t - span, side="right") - 1
        kk = np.maximum(k, 0)
        good = (k >= 0) & ((t - span) - t[kk] <= GAP_MS)
        return np.where(good, np.log(c / c[kk]), np.nan)

    idx = pd.DatetimeIndex(pd.to_datetime(t, unit="ms", utc=True))
    for tag, span in (("1w", 7 * U.D_MS), ("1m", 30 * U.D_MS)):
        r = back(span)
        sd = pd.Series(r, index=idx).rolling("%dD" % NORM_DAYS, min_periods=NORM_MIN_BARS).std().values
        z = r / np.where(sd > 0, sd, np.nan)
        out["chg_" + tag] = U.asof(t, 100.0 * (np.exp(r) - 1.0), close_ms, U.H_MS)
        out["z_" + tag] = U.asof(t, z, close_ms, U.H_MS)
    out["px"] = U.asof(t, c, close_ms, U.H_MS)
    return out


def features(index15, asset, bars=None, src_dir=None):
    """-> frame on index15 (15m bar OPEN times, UTC): FEATURES (0.0 = no read, never NaN) and RAW (NaN = no read).
    Only USDJPY gets readings."""
    index15 = pd.DatetimeIndex(index15)
    close_raw = np.asarray(index15.as_unit("ms").asi8, dtype="int64") + U.BAR_MS
    out = pd.DataFrame(np.nan, index=index15, columns=FEATURES + RAW)
    errors = {}
    if asset == ASSET and len(close_raw):
        order = np.argsort(close_raw, kind="stable")
        close_ms = close_raw[order]
        w = pd.DataFrame(np.nan, index=np.arange(len(close_ms)), columns=FEATURES + RAW)
        try:                                                                  # BoJ decisions
            b = boj_decisions()
            nxt = _next_after(close_ms, b["decision_ms"].values, b["known_ms"].values, b["gone_ms"].values)
            h = (nxt - close_ms) / U.H_MS
            w["jp_boj_hours"] = np.where(np.isfinite(h), h, np.nan)
            w["jp_boj_next"] = np.clip(1.0 - h / BOJ_SPAN_H, 0, 1)
        except Exception as e:
            errors["boj"] = "%s: %s" % (type(e).__name__, str(e)[:120])
        try:                                                                  # JPY high-impact releases
            st = U.load_state(state_path(src_dir))
            ev = load_events(src_dir)
            if len(ev) and st.get("first_feed_ms"):
                hi = ev[ev["impact"].str.lower() == "high"]
                nxt = _next_after(close_ms, hi["ts_ms"].values, hi["first_seen_ms"].fillna(np.inf).values) \
                    if len(hi) else np.full(len(close_ms), np.inf)
                h = (nxt - close_ms) / U.H_MS
                cover = (close_ms >= int(st["first_feed_ms"])) & \
                        (close_ms <= int(st.get("last_feed_ms", 0)) + FEED_STALE_MS)
                # the feed shows one week: "none in sight" is a read only inside the covered span
                w["jp_event_hours"] = np.where(cover & np.isfinite(h), h, np.nan)
                w["jp_event_next"] = np.where(cover, np.clip(1.0 - h / EVENT_SPAN_H, 0, 1), 0.0)
        except Exception as e:
            errors["events"] = "%s: %s" % (type(e).__name__, str(e)[:120])
        try:                                                                  # price, speed and intervention levels
            bars = U.bars_of(asset, bars)
            if bars is not None and len(bars):
                sp = _speed(bars, close_ms)
                if sp:
                    px = sp["px"]
                    w["jp_px"] = px
                    w["jp_chg_1w_pct"], w["jp_chg_1m_pct"] = sp["chg_1w"], sp["chg_1m"]
                    w["jp_speed_1w_z"], w["jp_speed_1m_z"] = sp["z_1w"], sp["z_1m"]
                    w["jp_speed_1w"] = np.clip(sp["z_1w"] / SPEED_UNIT, -1, 1)
                    w["jp_speed_1m"] = np.clip(sp["z_1m"] / SPEED_UNIT, -1, 1)
                    iv = load_interventions(src_dir)
                    if len(iv):
                        lv, conf, day = iv["level"].values, iv["confirmed_ms"].values, iv["date_ms"].values
                        above = np.full(len(close_ms), np.inf)
                        top = np.full(len(close_ms), -np.inf)
                        last = np.full(len(close_ms), -np.inf)
                        for L, k, dms in zip(lv, conf, day):
                            known = close_ms >= k
                            above = np.where(known & (L >= px), np.minimum(above, L), above)
                            top = np.where(known, np.maximum(top, L), top)
                            last = np.where(known, np.maximum(last, dms), last)
                        ref = np.where(np.isfinite(above), above, top)
                        ref = np.where(np.isfinite(ref) & np.isfinite(px), ref, np.nan)
                        dist = 100.0 * (ref / px - 1.0)
                        w["jp_mof_level"], w["jp_mof_dist_pct"] = ref, dist
                        w["jp_mof_top_dist_pct"] = np.where(np.isfinite(top) & np.isfinite(px), 100.0 * (top / px - 1.0), np.nan)
                        w["jp_days_since_mof"] = np.where(np.isfinite(last), (close_ms - last) / U.D_MS, np.nan)
                        zone = np.clip(1.0 - dist / ZONE_PCT, 0, 1)
                        w["jp_mof_zone"] = zone
                        push = np.clip(np.fmax(np.fmax(sp["z_1w"], sp["z_1m"]), 0.0) / 2.0, 0, 1)
                        w["jp_risk"] = zone * push
        except Exception as e:
            errors["price"] = "%s: %s" % (type(e).__name__, str(e)[:120])
        back = np.empty_like(order)
        back[order] = np.arange(len(order))
        out[:] = w.values[back]
    out[FEATURES] = out[FEATURES].astype(float).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    out.attrs["errors"] = errors
    return out


# ------------------------------------------------------------------ plain English
def _close_ms(row):
    try:
        return int(pd.Timestamp(row.name).value // 1000000) + U.BAR_MS
    except Exception:
        return U.now_ms()


def _intervention_at(level, close_ms, src_dir=None):
    iv = load_interventions(src_dir)
    iv = iv[(iv["confirmed_ms"] <= close_ms) & (np.abs(iv["level"] - level) < 1e-6)]
    return None if not len(iv) else iv.iloc[-1]


def _next_boj_day(row):
    h = U.num(row, "jp_boj_hours")
    if h is None:
        return None
    return pd.Timestamp(_close_ms(row) + h * U.H_MS, unit="ms", tz="UTC").strftime("%a %d %b %Y")


def _next_event(close_ms, src_dir=None):
    ev = load_events(src_dir)
    if not len(ev):
        return None
    m = (ev["impact"].str.lower() == "high") & (ev["first_seen_ms"] <= close_ms) & (ev["ts_ms"] > close_ms)
    ev = ev[m]
    return None if not len(ev) else ev.iloc[0]


def describe(row, asset):
    """One row of features() -> {card title: one plain-English sentence}. States what was read; forecasts nothing."""
    title = GROUPS["japan"][0]
    if asset != ASSET:
        return {title: "The Japan watch is read for USDJPY only."}
    bits = []
    px, ref, dist = U.num(row, "jp_px"), U.num(row, "jp_mof_level"), U.num(row, "jp_mof_dist_pct")
    if px is not None and ref is not None:
        iv = _intervention_at(ref, _close_ms(row))
        when = "" if iv is None else " (%s, JPY %.2f trillion)" % (pd.Timestamp(iv["date"]).strftime("%d %b %Y"),
                                                                    iv["amount_jpy_bn"] / 1000.0)
        bits.append("USDJPY %.2f is %.1f%% %s %.2f, %s level the Ministry of Finance intervened at%s" % (
            px, abs(dist), "below" if dist >= 0 else "above", ref,
            "the nearest" if dist >= 0 else "above the highest", when))
    elif px is not None:
        bits.append("USDJPY %.2f; no confirmed intervention on file before this close" % px)
    for tag, label, span in (("1w", "a week", "week"), ("1m", "a month", "month")):
        c, z = U.num(row, "jp_chg_%s_pct" % tag), U.num(row, "jp_speed_%s_z" % tag)
        if c is not None:
            bits.append("%+.1f%% in %s%s" % (c, label, "" if z is None else " (%+.1f standard deviations of a usual %s's move)" % (z, span)))
    d = _next_boj_day(row)
    if d:
        bits.append("next BoJ decision %s (%.1f days)" % (d, U.num(row, "jp_boj_hours") / 24.0))
    eh = U.num(row, "jp_event_hours")
    if eh is not None:
        e = _next_event(_close_ms(row))
        bits.append("next JPY high-impact release %s in %.1f hours" % ("'%s'" % e["title"] if e is not None else "", eh))
    if not bits:
        return {title: "No Japan watch read at this close."}
    return {title: "; ".join(bits)[0].upper() + "; ".join(bits)[1:] + "."}


def facts(row, asset):
    """One row of features() -> {card title: [[label, value], ...]}: prices, percentages, dates."""
    title = GROUPS["japan"][0]
    if asset != ASSET:
        return {}
    c = _close_ms(row)
    rows = []
    px = U.num(row, "jp_px")
    rows.append(["USDJPY", "n/a" if px is None else "%.3f" % px])
    ref, dist = U.num(row, "jp_mof_level"), U.num(row, "jp_mof_dist_pct")
    if ref is not None:
        iv = _intervention_at(ref, c)
        rows.append(["Reference intervention level", "%.2f%s" % (ref, "" if iv is None else " on %s (JPY %s billion)" % (
            iv["date"], format(iv["amount_jpy_bn"], ",.1f")))])
        rows.append(["Distance to it", "%.2f%% %s" % (abs(dist), "below" if dist >= 0 else "above (beyond every past level)")])
        top = U.num(row, "jp_mof_top_dist_pct")
        if top is not None:
            rows.append(["Distance to the highest intervention level", "%.2f%% %s" % (abs(top), "below" if top >= 0 else "above")])
    ds = U.num(row, "jp_days_since_mof")
    rows.append(["Last confirmed intervention", "none on file" if ds is None else "%.0f days ago" % ds])
    for tag, label in (("1w", "Change over 1 week"), ("1m", "Change over 1 month")):
        ch, z = U.num(row, "jp_chg_%s_pct" % tag), U.num(row, "jp_speed_%s_z" % tag)
        rows.append([label, "n/a" if ch is None else "%+.2f%%%s" % (ch, "" if z is None else
                                                                     " (%+.1f sd of its usual size over a year)" % z)])
    d = _next_boj_day(row)
    rows.append(["Next BoJ decision", "n/a" if d is None else "%s, about 12:00 Tokyo (%.1f days)" % (
        d, U.num(row, "jp_boj_hours") / 24.0)])
    eh = U.num(row, "jp_event_hours")
    if eh is not None:
        e = _next_event(c)
        rows.append(["Next JPY high-impact release", "%s in %.1f hours" % (e["title"] if e is not None else "?", eh)])
    else:
        rows.append(["Next JPY high-impact release", "none in this week's calendar" if
                     U.load_state(state_path()).get("first_feed_ms", 1e18) <= c else "calendar not read yet at this time"])
    return {title: rows}
