# -*- coding: utf-8 -*-
"""facts -- the raw data points behind each card, in units a person reads.

WHY (owner, 10 Nov 2026): "The 10 cards should not be just scoring. It should consist on data
that people like me can read and understand ... display the raw datapoint also."

card_facts(e, row) -> {card title: [[label, value], ...]}: prices, percentages, counts and
names, never a scaled model number. `row` is the evidence row of that session; live-only
sources are read from e["raw"] (what livefeeds.collect returned for the session).
"""
import math

SIDE = {1: "long", -1: "short", 0: "flat"}


def _ok(v):
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def _px(v):
    if not _ok(v):
        return "n/a"
    return ("{:,.0f}" if abs(v) >= 10000 else "{:,.2f}").format(v)


def _pct(v, dp=2):
    return "n/a" if not _ok(v) else ("%+." + str(dp) + "f%%") % v


def _get(row, key):
    try:
        v = row[key]
    except (KeyError, IndexError):
        return None
    return v if _ok(v) else None


def _qty(v):
    if not _ok(v):
        return "n/a"
    return "{:+,.0f}".format(v) if abs(v) >= 100 else "{:+,.1f}".format(v)


def card_facts(e, row):
    coin = e["asset"][:3]
    raw = e.get("raw") or {}
    f = {}

    f["Timeframe strength"] = [[tf, "%s (%s)" % (lab, "n/a" if sc is None else "%+.2f" % sc)] for tf, (sc, lab) in e["trend"].items()]

    f["Regime"] = [["Label", e["regime"]],
                   ["Efficiency ratio, 20 days", "n/a" if _get(row, "rg_er") is None else "%.2f (trend at 0.35, range at 0.20)" % row["rg_er"]],
                   ["5-day return", _pct(_get(row, "rg_ret5_pct"), 1)],
                   ["Daily ATR vs its 50-day mean", "n/a" if _get(row, "rg_atr_x") is None else "%.2fx" % row["rg_atr_x"]]]

    lv = e.get("level_reads") or {}
    f["Support and resistance"] = [
        ["Resistance", "%s (%s, %.1f ATR above)" % (_px(lv.get("res_px")), lv.get("res_kind") or "n/a", lv.get("res_dist_atr") or 0)] if _ok(lv.get("res_px")) else ["Resistance", "none read"],
        ["Support", "%s (%s, %.1f ATR below)" % (_px(lv.get("sup_px")), lv.get("sup_kind") or "n/a", lv.get("sup_dist_atr") or 0)] if _ok(lv.get("sup_px")) else ["Support", "none read"],
        ["Yesterday's high / low", "%s / %s" % (_px(lv.get("pd_high")), _px(lv.get("pd_low")))],
        ["Last week's high / low", "%s / %s" % (_px(lv.get("pw_high")), _px(lv.get("pw_low")))]]

    d = e.get("data", {})
    f["Momentum and stretch"] = [
        ["Return 1h / 4h", "%s / %s" % (_pct(_get(row, "ret_1h_pct")), _pct(_get(row, "ret_4h_pct")))],
        ["Return 24h / 7d", "%s / %s" % (_pct(_get(row, "ret_24h_pct")), _pct(_get(row, "ret_7d_pct"), 1))],
        ["StochRSI 15m / 1h / 4h", "%.0f / %.0f / %.0f" % (50 + 50 * d.get("k_15m", 0), 50 + 50 * d.get("k_1h", 0), 50 + 50 * d.get("k_4h", 0))],
        ["Distance from the 1h average", "%+.1f ATR" % (2 * d.get("stretch_1h", 0))]]

    f["Order flow (CVD)"] = [
        ["Net taker buying, 1h", "%s %s" % (_qty(_get(row, "cvd_1h_raw")), coin)],
        ["Net taker buying, 4h", "%s %s" % (_qty(_get(row, "cvd_4h_raw")), coin)],
        ["Net taker buying, 24h", "%s %s" % (_qty(_get(row, "cvd_24h_raw")), coin)],
        ["Volume, 24h", "n/a" if _get(row, "vol_24h") is None else "{:,.0f} {}".format(row["vol_24h"], coin)]]

    fr = _get(row, "fund_raw")
    pos = raw.get("positioning") or {}
    f["Funding and positioning"] = [
        ["Funding rate", "n/a" if fr is None else "%+.4f%% per 8h (%+.1f%% a year)" % (fr * 100, fr * 100 * 3 * 365)],
        ["Funding paid over 3 days", _pct(_get(row, "fund_3d_raw_pct"), 3)],
        ["Open interest", "{:,.0f} {}".format(pos["open_interest"], coin) if pos.get("open_interest") else "no live read"],
        ["Open interest, 1h / 24h", "%s / %s" % (_pct(pos.get("change_1h_pct")), _pct(pos.get("change_24h_pct"))) if pos.get("open_interest") else "no live read"]]

    bk = raw.get("book") or {}
    if bk.get("mid"):
        f["Liquidity (order book)"] = [
            ["Bids / asks within 0.5%", "{:,.0f} / {:,.0f} {}".format(bk.get("bid_05", 0), bk.get("ask_05", 0), coin)],
            ["Bids / asks within 2%", "{:,.0f} / {:,.0f} {}".format(bk.get("bid_2", 0), bk.get("ask_2", 0), coin)],
            ["Biggest bid wall", "%.2f%% below (%s)" % (bk.get("bid_wall_pct", 0), _px(bk["mid"] * (1 - bk.get("bid_wall_pct", 0) / 100)))],
            ["Biggest ask wall", "%.2f%% above (%s)" % (bk.get("ask_wall_pct", 0), _px(bk["mid"] * (1 + bk.get("ask_wall_pct", 0) / 100)))]]
    else:
        f["Liquidity (order book)"] = [["Snapshot", "none for this session (live only)"]]

    kr = raw.get("kronos") or {}
    rows = []
    for tf, span in (("15m", "next 2 hours"), ("1h", "next 8 hours")):
        c = kr.get(tf) or {}
        if c.get("fresh") and "median_end" in c:
            rows.append(["%s forecast, %s" % (tf, span), "%s (%s)" % (_px(c["median_end"]), _pct(c["move_pct"]))])
            rows.append(["%s paths ending higher" % tf, "%.0f of 10" % (c["paths_up"] * 10)])
    f["Kronos forecast"] = rows or [["Forecast", "none for this session (live only)"]]

    f["Working strategies"] = [[name, side.lower()] for name, side in e["strategies"].items()]

    nx = e.get("econ_next")
    rows = [["Next US release", "none on the calendar" if not nx else "%s, %s UTC (in %.0fh)" % (", ".join(nx["titles"][:2]), nx["time_utc"][5:], nx["hours_away"])]]
    if nx and nx.get("forecast") and any(nx["forecast"]):
        k = next(i for i, v in enumerate(nx["forecast"]) if v)
        rows.append(["Forecast / previous", "%s / %s (%s)" % (nx["forecast"][k], nx["previous"][k], nx["titles"][k])])
    rows.append(["S&P 500 / VIX", "%s / %s" % (_px(_get(row, "raw_spx")), "n/a" if _get(row, "raw_vix") is None else "%.1f" % row["raw_vix"])])
    rows.append(["Dollar index / US 10-year", "%s / %s" % ("n/a" if _get(row, "raw_dxy") is None else "%.2f" % row["raw_dxy"],
                                                       "n/a" if _get(row, "raw_y10") is None else "%.2f%%" % row["raw_y10"])])
    for n in (raw.get("news") or [])[:2]:
        if "title" in n:
            rows.append(["%s" % (n.get("source") or "News"), n["title"][:90]])
    f["News and economic events"] = rows
    return f
