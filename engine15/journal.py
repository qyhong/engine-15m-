# -*- coding: utf-8 -*-
"""journal -- stage 5 of the thought process: WRITE DOWN what was read, what was weighed,
what was decided and why, at every 15-minute close; and how earlier calls were graded.

One entry per asset per session. An entry is a plain dict (entry) that renders to Markdown
(render) and is stored as one JSON line; a day is one file of each (write_day):
    journal/2026-11-10.md      for reading
    journal/2026-11-10.jsonl   for the discussion mode and the web page

    py -3 -m engine15 journal 2026-11-09      (writes that day of the replay to journal/replay/)
"""
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd

from . import labels, model, policy
from .config import JOURNAL_DIR, OUT_DIR
from .evidence import CARDS, FEATURES
from .indicators import label_of

SESSION = pd.Timedelta(minutes=15)
TFS = (("15m", "tr_15m"), ("1h", "tr_1h"), ("4h", "tr_4h"), ("1d", "tr_1d"), ("1w", "tr_1w"))
STRUCTURE = (                           # (weekly, 4h+1d, 15m+1h) -> words; the estate's trend-map rules
    (("UP", "UP", "UP"), "uptrend on every horizon"),
    (("DOWN", "DOWN", "DOWN"), "downtrend on every horizon"),
    (("UP", "UP", "DOWN"), "pullback inside an uptrend"),
    (("DOWN", "DOWN", "UP"), "bounce inside a downtrend"),
    (("UP", "DOWN", None), "medium-term fall inside a long-term uptrend"),
    (("DOWN", "UP", None), "medium-term rise inside a long-term downtrend"),
)
STRATS = (("st_core", "StochRSI core zone"), ("st_donch", "Donchian trend"), ("st_burst", "Burst momentum"),
          ("st_tsmom", "30-day momentum"), ("st_btc120", "BTC 120-day trend"), ("st_bh", "Weekly regime"))
WORDS = {
    "tr_15m": "15m trend", "tr_1h": "1h trend", "tr_4h": "4h trend", "tr_1d": "daily trend", "tr_1w": "weekly trend",
    "rg_TREND_UP": "regime TREND_UP", "rg_TREND_DOWN": "regime TREND_DOWN", "rg_MOMENTUM_UP": "regime MOMENTUM_UP",
    "rg_MOMENTUM_DOWN": "regime MOMENTUM_DOWN", "rg_RANGE": "regime RANGE",
    "st_core": "StochRSI core zone", "st_donch": "Donchian trend strategy", "st_burst": "Burst momentum strategy",
    "st_tsmom": "30-day momentum strategy", "st_btc120": "BTC 120-day trend", "st_bh": "weekly regime (EMA20/50)",
    "mom_1h": "last hour's move", "mom_4h": "last 4 hours' move", "mom_24h": "last 24 hours' move",
    "mom_7d": "last 7 days' move", "stretch_1h": "stretch from the 1h average",
    "stretch_4h": "stretch from the 4h average", "rangepos": "place in the 24h range",
    "k_15m": "15m StochRSI", "k_1h": "1h StochRSI", "k_4h": "4h StochRSI", "pullback": "pullback inside the trend",
    "f_volrank": "volatility level", "f_shock": "last hour's shock", "x_mom_24h": "the other coin's 24h move",
    "x_tr_1d": "the other coin's daily trend",
    "cvd_1h": "1h order flow (CVD)", "cvd_4h": "4h order flow (CVD)", "cvd_24h": "24h order flow (CVD)",
    "cvd_div": "flow / price divergence", "fund_rate": "funding rate", "fund_z": "funding vs its month",
    "fund_3d": "3-day funding paid", "oi_chg_1h": "open interest, 1h change", "oi_chg_24h": "open interest, 24h change",
    "ob_imb_05": "order book within 0.5%", "ob_imb_2": "order book within 2%", "ob_wall": "nearest liquidity wall",
    "kr_ret_15m": "Kronos 15m forecast", "kr_up_15m": "Kronos 15m paths", "kr_ret_1h": "Kronos 1h forecast",
    "kr_up_1h": "Kronos 1h paths", "news_score": "news tone", "news_heat": "news volume",
    "sr_sup_near": "support is close", "sr_res_near": "resistance is close", "sr_sup_str": "strength of the support below",
    "sr_res_str": "strength of the resistance above", "sr_room": "room up versus down", "sr_lean": "levels lean",
    "sr_break": "a level just broke", "sr_reject": "a level just held", "sr_pdh_near": "near yesterday's high",
    "sr_pdl_near": "near yesterday's low", "sr_pd_pos": "place in yesterday's range", "sr_round_near": "near a round number",
    "owner_view": "the owner's view", "ec_next": "a US release is near", "ec_prev": "a US release just printed", "mac_spx_5d": "S&P 500, 5-day move",
    "mac_dxy_5d": "dollar index, 5-day move", "mac_vix": "VIX level", "mac_y10_5d": "US 10-year yield, 5-day change",
}
SIDE = {1: "LONG", -1: "SHORT", 0: "FLAT"}


def load_store(run="replay"):
    with open(os.path.join(OUT_DIR, run, "store.pkl"), "rb") as fh:
        return pickle.load(fh)


def _structure(e):
    lab = lambda v: label_of(float(np.nanmean(v))) if np.isfinite(v).any() else "NO DATA"   # noqa: E731
    tr = e["trend"]
    key = (tr["1w"][1], lab(np.array([tr["4h"][0], tr["1d"][0]], dtype=float)),
           lab(np.array([tr["15m"][0], tr["1h"][0]], dtype=float)))
    for pattern, words in STRUCTURE:
        if all(p is None or p == k for p, k in zip(pattern, key)):
            return words
    return "mixed"


def _model_at(store, i):
    best = None
    for s, w_all, n in store["models"]:
        if s <= i:
            best = (s, w_all, n)
        else:
            break
    return best


def entry(store, asset, i, raw=None, trade=None):
    """Everything the engine thought about `asset` at the close of session i.
    raw: what the live feeds returned for this session (order book, positioning, Kronos, news)."""
    cfg, ev, book = store["cfg"], store["ev"][asset].iloc[i], store["books"][asset]
    odds, probs, trust = store["odds"][asset][i], store["probs"][asset][i], store["trust"][i]
    e = {"asset": asset, "i": int(i), "time": str((store["times"][i] + SESSION).strftime("%Y-%m-%d %H:%M")),
         "price": float(ev["px"])}
    e["trend"] = dict((tf, (None if ev[col] != ev[col] else round(float(ev[col]), 2), label_of(ev[col])))
                      for tf, col in TFS)
    e["structure"] = _structure(e)
    e["regime"] = ev["regime"] if isinstance(ev["regime"], str) else "NO DATA"
    e["strategies"] = dict((name, SIDE[int(np.sign(ev[col]))]) for col, name in STRATS)
    e["risk"] = {"high": bool(ev["shock"]), "shock_ratio": None if ev["shock_ratio"] != ev["shock_ratio"]
                 else round(float(ev["shock_ratio"]), 2)}
    act = policy.WAIT if not np.isfinite(odds[0]) else None
    if act is None:
        e["odds"] = {"up": round(float(odds[labels.UP]), 3), "down": round(float(odds[labels.DOWN]), 3),
                     "neither": round(float(odds[labels.NEITHER]), 3)}
        e["edge_pts"] = round(float(odds[labels.UP] - odds[labels.DOWN]) * 100, 1)
        voices = []
        for k, v in enumerate(model.VOICE_NAMES):
            pull = float(trust[k] * (probs[k, labels.UP] - probs[k, labels.DOWN])) * 100
            voices.append({"voice": v, "title": model.VOICES[v][0], "up": round(float(probs[k, labels.UP]), 3),
                           "down": round(float(probs[k, labels.DOWN]), 3), "trust": round(float(trust[k]), 3),
                           "pull_pts": round(pull, 1)})
        e["voices"] = sorted(voices, key=lambda d: -abs(d["pull_pts"]))
        m = _model_at(store, i)
        if m is not None:
            pulls = [(f, p) for f, p in model.evidence_pulls(m[1], store["X"][asset][i].astype(float)) if abs(p) >= 0.01]
            e["for_long"] = [(WORDS.get(f, f), round(p, 2)) for f, p in pulls if p > 0][:3]
            e["for_short"] = [(WORDS.get(f, f), round(p, 2)) for f, p in pulls if p < 0][:3]
            e["model_rows"] = int(m[2])
    from .backtest import ACTIONS
    e["action"] = ACTIONS[int(book["act"][i])]
    e["reason"] = book["reason"][i]
    tr = book["trades"]
    stopped = tr[(tr.i_out == i) & (tr.why_out == "STOP")]
    e["stopped_at"] = float(stopped.p_out.iloc[0]) if len(stopped) else None
    e["position"] = SIDE[0 if len(stopped) else int(book["held"][i])]
    e["idle_sessions"] = int(book["idle"][i])
    e["stop"] = None if book["stop"][i] != book["stop"][i] else float(book["stop"][i])
    e["equity"] = None if book["equity"][i] != book["equity"][i] else round(float(book["equity"][i]), 2)
    lo = max(0, i - cfg["horizon"])
    y, res, od = store["y"][asset][lo:i], store["res"][asset][lo:i], store["odds"][asset][lo:i]
    due = (np.arange(lo, i) + res == i) & (y >= 0) & np.isfinite(od[:, 0])
    edge = od[due][:, labels.UP] - od[due][:, labels.DOWN]
    yy = y[due]
    right = int((((edge > 0) & (yy == labels.UP)) | ((edge < 0) & (yy == labels.DOWN))).sum())
    e["graded_now"] = {"calls": int(due.sum()), "right": right, "wrong": int(((yy > 0).sum()) - right),
                       "neither": int((yy == 0).sum())}
    hb = ev.get("htf_bias", 0.0)
    e["htf_bias"] = 0 if hb != hb else int(hb)                     # v5: +1 long bias, -1 short bias, 0 none
    td = ev.get("tide", 0.0)
    e["tide"] = 0.0 if td != td else round(float(td), 3)          # the mean of the 4h and daily trend scores
    e["bias_mas"] = dict((k, None if ev.get(c) is None or ev.get(c) != ev.get(c) else round(float(ev.get(c)), 4))
                         for k, c in (("ema50_1h", "bias_ema50_1h_px"), ("ema20_4h", "bias_ema20_4h_px"), ("ema50_4h", "bias_ema50_4h_px")))
    e["release_soon"] = bool(ev.get("release_soon", False))
    if e["release_soon"]:
        try:
            from . import econ as _econ
            e["econ_next"] = _econ.next_event(store["times"][i] + SESSION)
        except Exception:
            pass
    e["decision"] = _sentence(e, cfg)
    x = store["X"][asset][i]
    e["data"] = dict((f, round(float(v), 4)) for f, v in zip(FEATURES, x))
    row = store["ev"][asset].iloc[i]
    e["levels"] = None
    try:
        from . import levels
        e["levels"] = levels.describe(row)
        e["level_reads"] = dict((k, (row[k] if isinstance(row[k], str) else None if row[k] != row[k] else round(float(row[k]), 4)))
                                for k in levels.READS)
    except Exception:
        pass
    try:
        from . import econ
        e["econ_next"] = econ.next_event(store["times"][i] + SESSION)
    except Exception:
        e["econ_next"] = None
    if raw:
        e["raw"] = raw
    e["trade"] = trade                                             # execution details (live.open_trade), latest session only
    from . import facts
    e["facts"] = facts.card_facts(e, row)
    e["source_words"] = {}
    from .evidence import sources_for
    SOURCES = sources_for(asset)                                   # crypto-only cards say nothing for gold, S&P ...
    for m in SOURCES:                                              # cards 11 to 20 describe themselves
        try:
            e["source_words"].update(m.describe(row, asset))
        except Exception:
            pass
    for title, sentence in e["source_words"].items():
        e["facts"][title] = [["Now", sentence]]
    for m in SOURCES:                                              # a source that offers readable rows replaces its sentence
        if hasattr(m, "facts"):
            try:
                e["facts"].update(m.facts(row, asset))
            except Exception:
                pass
    e["cards"] = cards(e)
    try:
        from . import owner
        e["question"] = owner.question(e)
        e["owner"] = owner.standing(asset, now_ms=int((store["times"][i] + SESSION).timestamp() * 1000))
    except Exception:
        e["question"], e["owner"] = None, None
    return e


def _econ_words(e, d):
    nx = e.get("econ_next")
    cal = "No US release on the calendar." if not nx else "Next US release: %s in %.0fh%s." % (
        ", ".join(nx["titles"][:2]), nx["hours_away"],
        " (forecast %s, previous %s)" % (nx["forecast"][0], nx["previous"][0]) if nx["forecast"] and nx["forecast"][0] else "")
    return cal + " S&P 5-day %s, dollar %s, VIX %.0f." % (_sigma(d.get("mac_spx_5d", 0)), _sigma(d.get("mac_dxy_5d", 0)),
                                                         20 + 20 * d.get("mac_vix", 0))


def _sigma(v):
    return "%+.1f sd" % v


def cards(e):
    """The ten decision cards: what each source reads now, and how far it pulls the odds."""
    d, voices = e.get("data", {}), dict((v["voice"], v) for v in e.get("voices", []))
    live_seen = lambda keys: any(abs(d.get(k, 0.0)) > 0 for k in keys)          # noqa: E731
    words = {
        "Timeframe strength": " | ".join("%s %s" % (tf, lab) for tf, (_, lab) in e["trend"].items()) + ". " + e["structure"].capitalize() + ".",
        "Regime": "%s (daily)." % e["regime"],
        "Support and resistance": e.get("levels") or "No levels read.",
        "Momentum and stretch": "24h move %s, 4h move %s; 1h StochRSI %.0f, 4h StochRSI %.0f." % (
            _sigma(d.get("mom_24h", 0)), _sigma(d.get("mom_4h", 0)), 50 + 50 * d.get("k_1h", 0), 50 + 50 * d.get("k_4h", 0)),
        "Order flow (CVD)": "Net taker buying: 1h %s, 4h %s, 24h %s; flow minus price %s." % (
            _sigma(d.get("cvd_1h", 0)), _sigma(d.get("cvd_4h", 0)), _sigma(d.get("cvd_24h", 0)), _sigma(d.get("cvd_div", 0))),
        "Funding and positioning": "Funding %+.4f%% per 8h (%s vs its month)%s." % (
            d.get("fund_rate", 0) * 0.05, _sigma(d.get("fund_z", 0)),
            "; open interest %+.1f%% in 24h" % (d.get("oi_chg_24h", 0) * 10) if live_seen(["oi_chg_24h", "oi_chg_1h"]) else ""),
        "Liquidity (order book)": ("Resting size within 2%%: %s lead (%+.2f); within 0.5%%: %+.2f; nearest big wall favours %s." % (
            "bids" if d.get("ob_imb_2", 0) >= 0 else "asks", d.get("ob_imb_2", 0), d.get("ob_imb_05", 0),
            "support" if d.get("ob_wall", 0) >= 0 else "resistance")) if live_seen(["ob_imb_2", "ob_imb_05", "ob_wall"]) else "No snapshot for this session (live only).",
        "Kronos forecast": ("15m forecast: %.0f of 10 paths end higher; 1h forecast: %.0f of 10." % (
            (d.get("kr_up_15m", 0) + 1) * 5, (d.get("kr_up_1h", 0) + 1) * 5)) if live_seen(["kr_up_15m", "kr_up_1h", "kr_ret_15m", "kr_ret_1h"]) else "No forecast for this session (live only).",
        "Working strategies": (", ".join("%s %s" % (k, v) for k, v in e["strategies"].items() if v != "FLAT") or "All flat") + ".",
        "News and economic events": (("News tone %+.2f (-1 to +1), volume %.0f%% of busy. " % (d.get("news_score", 0), d.get("news_heat", 0) * 100))
                                     if live_seen(["news_score", "news_heat"]) else "No headlines scored for this session. ")
        + _econ_words(e, d),
    }
    out = []
    from .evidence import cards_for
    shown = set(cards_for(e["asset"]))                             # no crypto-only cards for gold, silver, USDJPY, S&P
    for title, names in CARDS.items():
        if title not in shown:
            continue
        vs = [voices[n] for n in names if n in voices]
        out.append({"card": title, "reading": words.get(title) or (e.get("source_words") or {}).get(title, "No read."),
                    "facts": (e.get("facts") or {}).get(title, []),
                    "pull_pts": round(sum(v["pull_pts"] for v in vs), 1),
                    "trust": round(sum(v["trust"] for v in vs), 3),
                    "lean": None if not vs else round(sum((v["up"] - v["down"]) for v in vs) / len(vs) * 100, 1)})
    return out


def _sentence(e, cfg):
    a, pos, edge = e["action"], e["position"], e.get("edge_pts", 0.0)
    better = "LONG" if edge > 0 else "SHORT"
    bar = cfg["theta_enter_shock"] * 100 if e["risk"]["high"] else cfg["theta_enter"] * 100
    flip = cfg["theta_flip"] * 100
    if a == policy.WAIT:
        return "LEARNING: not enough graded calls yet to form odds. Flat."
    why, d = e.get("reason"), e.get("data", {})
    bias_word = "SHORT" if (e.get("htf_bias") or 0) < 0 else "LONG"
    if why == "release_guard":
        nx = e.get("econ_next") or {}
        return "STAND ASIDE: %s is due within the hour (%s UTC). No new position into a high-impact release." % (
            ", ".join(nx.get("titles", [])[:2]) or "a high-impact US release", nx.get("time_utc", "?")[11:16])
    if why == "release_guard_hold":
        return "HOLD %s through the release window: no flip in the hour before a high-impact US release; the stop stays live." % pos
    if why == "against_htf_bias":
        return ("FLIP to %s at the next open: every timeframe from 1h to daily trends %s and price is %s the 1h EMA50 and the "
                "4h EMA20/50, and the %s position has less than a 5-pt edge for it." % (
                    bias_word, "down" if bias_word == "SHORT" else "up", "below" if bias_word == "SHORT" else "above", pos))
    if why == "mandate_with_bias":
        return ("ENTER %s at the next open BY MANDATE: flat for %d sessions, the limit, no side cleared the bar (edge %.1f pts), "
                "so it takes the higher-timeframe bias: 1h to daily trend %s, price %s the 1h EMA50 and 4h EMA20/50." % (
                    bias_word, cfg["idle_max"], abs(edge), "down" if bias_word == "SHORT" else "up",
                    "below" if bias_word == "SHORT" else "above"))
    if why == "counter_bias_clears_bar":
        return "ENTER %s at the next open AGAINST the higher-timeframe bias: its edge of %.1f pts clears the %.0f-pt counter-trend bar." % (
            better, abs(edge), cfg.get("theta_counter", 0.15) * 100)
    if a == policy.HOLD:
        mine = edge if pos == "LONG" else -edge
        if mine >= 0:
            return "HOLD %s: the edge is still with the position (%+.1f pts)." % (pos, mine)
        return "HOLD %s: the odds lean against it (%+.1f pts) but not by the %.0f pts a flip must pay for." % (pos, mine, flip)
    if a == policy.FLIP:
        return "FLIP to %s at the next open: the %s side leads by %.1f pts, past the %.0f-pt flip bar." % (
            better, better.lower(), abs(edge), flip)
    if a == policy.ENTER:
        return "ENTER %s at the next open: its edge of %.1f pts clears the %.0f-pt bar%s." % (
            better, abs(edge), bar, " for high risk" if e["risk"]["high"] else "")
    if a == policy.FORCED and e.get("reason") == "mandate_with_trend":
        side = "LONG" if (e.get("tide") or 0.0) > 0 else "SHORT"   # the same tide the policy used (set before this sentence)
        return ("ENTER %s at the next open BY MANDATE: flat for %d sessions, the limit. Neither side cleared the %.0f-pt bar "
                "(the edge is %.1f pts), so it takes the side of the 4h and daily trend." % (side, cfg["idle_max"], bar, abs(edge)))
    if a == policy.FORCED:
        return ("ENTER %s at the next open BY MANDATE: flat for %d sessions, the limit. Neither side cleared the "
                "%.0f-pt bar; %s is the better of the two (%.1f pts)." % (better, cfg["idle_max"], bar, better.lower(), abs(edge)))
    if a == policy.IDLE:
        return "SIT OUT, session %d of %d: the better side leads by only %.1f pts against a %.0f-pt bar%s." % (
            e["idle_sessions"], cfg["idle_max"], abs(edge), bar, " (risk is high)" if e["risk"]["high"] else "")
    if a == policy.STEP_ASIDE:
        return "STEP ASIDE at the next open: risk is high and the edge has left the position (%+.1f pts for it)." % (
            edge if pos == "LONG" else -edge)
    return a


def render(e):
    px = ("%.2f" % e["price"]) if e["price"] < 10000 else ("%.0f" % e["price"])
    lines = ["**%s %s** · %s" % (e["asset"][:3], px, e["decision"])]
    if e.get("version_note"):
        lines.append("- New version: %s" % e["version_note"])
    if e.get("stopped_at"):
        lines.append("- Stopped out this session at %.2f." % e["stopped_at"])
    tr = " · ".join("%s %s%s" % (tf, lab, "" if sc is None else " (%+.2f)" % sc) for tf, (sc, lab) in e["trend"].items())
    lines.append("- Read: %s. Structure: %s. Regime: %s. Risk: %s." % (
        tr, e["structure"], e["regime"], "HIGH (last hour %sx normal)" % e["risk"]["shock_ratio"] if e["risk"]["high"] else "normal"))
    if e.get("levels"):
        lines.append("- Levels: %s" % e["levels"])
    on = ", ".join("%s %s" % (k, v) for k, v in e["strategies"].items() if v != "FLAT")
    lines.append("- Library strategies: %s." % (on or "all flat"))
    if "odds" in e:
        o = e["odds"]
        lines.append("- Odds, next 24h: up first %.0f%%, down first %.0f%%, neither %.0f%% -> %s edge %.1f pts." % (
            o["up"] * 100, o["down"] * 100, o["neither"] * 100, "long" if e["edge_pts"] >= 0 else "short", abs(e["edge_pts"])))
        top = [v for v in e["voices"] if v["voice"] != "base"][:4]
        lines.append("- Voices (pull in pts, trust): " + "; ".join(
            "%s %+.1f (%.0f%%)" % (v["title"], v["pull_pts"], v["trust"] * 100) for v in top) + ".")
        if e.get("for_long") or e.get("for_short"):
            lines.append("- For long: %s. For short: %s." % (
                ", ".join(w for w, _ in e.get("for_long", [])) or "nothing", ", ".join(w for w, _ in e.get("for_short", [])) or "nothing"))
    g = e["graded_now"]
    if g["calls"]:
        lines.append("- Graded this session: %d earlier calls (%d right, %d wrong, %d neither)." % (
            g["calls"], g["right"], g["wrong"], g["neither"]))
    if e.get("owner"):
        lines.append("- Your view: %s, conviction %.0f%%, %s h left. %s" % (
            e["owner"]["side"], e["owner"]["conviction"] * 100, e["owner"]["hours_left"], e["owner"]["note"]))
    if e.get("question"):
        lines.append("- Question for you: %s" % e["question"])
    t = e.get("trade")
    if t and t["status"] != "FLAT":
        lines.append("- Trade: %s %s %s ($%s) from %s, opened %s UTC by %s; stop %s (%.2f%% away, $%s at risk); marked %s: "
                     "%+.2f USD (%+.2f%%); fees $%.2f in, about $%.2f out." % (
                         t["status"], t["quantity"], e["asset"][:3], format(t["notional_usd"], ",.0f"), t["entry_price"],
                         t.get("opened_utc") or "earlier", t.get("opened_by") or "-", t["stop_price"], t["stop_distance_pct"] or 0,
                         format(t["risk_to_stop_usd"] or 0, ",.0f"), t["mark_price"], t["unrealized_usd"], t["unrealized_pct"],
                         t["entry_fee_usd"], t["exit_fee_est_usd"]))
    elif t:
        lines.append("- Trade: none open (idle %d of %d sessions). Realised so far %+.2f USD; fees paid $%.2f.%s" % (
            t["idle_sessions"], t["idle_max"], t["realized_usd"], t["fees_paid_usd"],
            " Next open: %s." % t["next_open"] if t.get("next_open") else ""))
    tail = "- Book: %s" % e["position"]
    if e["stop"]:
        tail += ", stop %.2f" % e["stop"]
    if e["equity"]:
        tail += ", equity $%s" % format(e["equity"], ",.0f")
    lines.append(tail + ".")
    return "\n".join(lines)


def day_entries(store, date):
    t = store["times"]
    day = pd.Timestamp(date, tz="UTC")
    closes = t + SESSION
    idx = np.where((closes > day) & (closes <= day + pd.Timedelta(days=1)))[0]
    return [(i, [entry(store, a, int(i)) for a in store["assets"]]) for i in idx]


def render_day(date, entries):
    """entries: a day's entry dicts, any order. -> the Markdown day file."""
    entries = sorted(entries, key=lambda e: (e["time"], e["asset"]))
    assets = sorted(set(e["asset"] for e in entries))
    md = ["# Trading journal, %s (UTC)" % date, "",
          "Paper book. One entry per coin at every 15-minute close: what was read, the odds, the decision and why.", "",
          "| coin | first price | last price | equity at the first close | at the last | decisions that changed the book |",
          "|---|---|---|---|---|---|"]
    for a in assets:
        es = [e for e in entries if e["asset"] == a]
        moves = sum(1 for e in es if e["action"] in (policy.ENTER, policy.FORCED, policy.FLIP, policy.STEP_ASIDE))
        stops = sum(1 for e in es if e["stopped_at"])
        md.append("| %s | %.2f | %.2f | %s | %s | %d%s |" % (a, es[0]["price"], es[-1]["price"], es[0]["equity"],
                                                          es[-1]["equity"], moves, " + %d stop-outs" % stops if stops else ""))
    md.append("")
    last = None
    for e in entries:
        if e["time"] != last:
            md.append("## %s UTC" % e["time"][11:])
            last = e["time"]
        md.append(render(e))
        md.append("")
    return "\n".join(md)


def read_day(date, out_dir=None):
    path = os.path.join(out_dir or JOURNAL_DIR, "%s.jsonl" % date)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def save_entries(entries, out_dir=None):
    """Add entries to their days' files (an entry for the same coin and time replaces the old one).
    -> the day files written."""
    out_dir = out_dir or JOURNAL_DIR
    os.makedirs(out_dir, exist_ok=True)
    by_day, written = {}, []
    for e in entries:
        by_day.setdefault(e["time"][:10], []).append(e)
    for date, new in sorted(by_day.items()):
        merged = dict(((e["asset"], e["time"]), e) for e in read_day(date, out_dir))
        merged.update(((e["asset"], e["time"]), e) for e in new)
        es = sorted(merged.values(), key=lambda e: (e["time"], e["asset"]))
        with open(os.path.join(out_dir, "%s.jsonl" % date), "w", encoding="utf-8") as fh:
            for e in es:
                fh.write(json.dumps(e) + "\n")
        path = os.path.join(out_dir, "%s.md" % date)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(render_day(date, es))
        written.append(path)
    return written


def write_day(store, date, out_dir=None):
    """One day of a replay, written from the run's store (to journal/replay/ by default)."""
    entries = [e for _, es in day_entries(store, date) for e in es]
    return save_entries(entries, out_dir or os.path.join(JOURNAL_DIR, "replay"))[0] if entries else None


def main(argv):
    if not argv:
        print(__doc__)
        return
    store = load_store(argv[1] if len(argv) > 1 else "replay")
    print(write_day(store, argv[0]) or "no sessions on that date in this run")


if __name__ == "__main__":
    main(sys.argv[1:])
