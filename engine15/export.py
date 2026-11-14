# -*- coding: utf-8 -*-
"""export -- page.json: everything the web tab shows, in one small file.

The tab (a sub-tab of alphaprediction.ai/aitrading) only ever reads this file; it never
talks to the engine. Whitelisted fields only: prices, readings, odds, decisions, the paper
book. Nothing here is advice and the file says so.
"""
import json
import os
import time

import numpy as np
import pandas as pd

from . import labels, model
from .evidence import CARDS


NAMES = {"BTCUSDT": "Bitcoin", "ETHUSDT": "Ether", "XAUUSD": "Gold", "XAGUSD": "Silver",
         "USDJPY": "US dollar / yen", "SPX": "S&P 500", "WTI": "WTI crude oil", "BRENT": "Brent crude oil"}
SHORT = {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "XAUUSD": "GOLD", "XAGUSD": "SILVER", "USDJPY": "USDJPY", "SPX": "S&P 500",
         "WTI": "WTI", "BRENT": "BRENT"}


def _candles(store, asset, k=96):
    """The last 96 closed 15m candles: [open time (s), open, high, low, close]."""
    px, t, n = store["px"][asset], store["times"], len(store["times"])
    d = 2 if px["close"][n - 1] >= 1000 else 3        # USDJPY and silver move in the third decimal
    return [[int(t[i].timestamp()), round(float(px["open"][i]), d), round(float(px["high"][i]), d),
             round(float(px["low"][i]), d), round(float(px["close"][i]), d)] for i in range(max(0, n - k), n)]


def _stance(store, asset, k=96):
    """The engine's side during each of those candles, from its journal: 1 long, -1 short, 0 flat,
    null where it has no live journal entry (before it went live)."""
    from . import journal
    t, n = store["times"], len(store["times"])
    days = sorted(set(str((t[i] + journal.SESSION).date()) for i in range(max(0, n - k - 1), n)))
    seen = {}
    for day in days:
        for e in journal.read_day(day):
            if e["asset"] == asset:
                seen[e["time"]] = {"LONG": 1, "SHORT": -1, "FLAT": 0}.get(e["position"], 0)
    # the side held DURING candle i is the position recorded at the close of candle i
    return [seen.get((t[i] + journal.SESSION).strftime("%Y-%m-%d %H:%M")) for i in range(max(0, n - k), n)]


def _extras():
    """Slow-moving material: the trade-score baseline, the card rating, the shadow book."""
    import json as _json
    from . import shadow
    from .config import OUT_DIR, ROOT
    out = {"shadow": shadow.book()}
    for key, path in (("scorecard_replay", os.path.join(OUT_DIR, "replay", "scorecard.json")),
                      ("card_rating", os.path.join(ROOT, "research", "card_rating.json"))):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                out[key] = _json.load(fh)
    return out


def group_of(asset):
    """The market group an asset is thought about in (config universes)."""
    from .config import CFG
    for g, assets in CFG.get("universes", (("crypto", CFG["assets"]),)):
        if asset in assets:
            return g
    return None


def group_rating(group, asset=None, out_dir=None):
    """The market group's card rating (research/out/card_rating_<group>.json, research/rate_cards.py) for the
    page: rows [card, steadiest reading, 1st half, 2nd half, steady, direction, detail], best first; the detail
    is cut to the worse half, whether the card votes for this market, and this asset's own halves of that
    reading. None when the group has not been rated."""
    from .config import CFG, ROOT, voting_for
    path = os.path.join(out_dir or os.path.join(ROOT, "research", "out"), "card_rating_%s.json" % group)
    if not group or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            rows = json.load(fh)
    except Exception:
        return None
    votes = set(voting_for(group, CFG))
    out = []
    for r in rows:
        d = r[6] if len(r) > 6 and isinstance(r[6], dict) else {}
        mine = ((d.get("per_asset") or {}).get(asset) or {}).get("same_reading") if asset else None
        out.append(list(r[:6]) + [{"worse_half": d.get("worse_half"),
                                   "votes": bool(d.get("voices")) and any(v in votes for v in d.get("voices", [])),
                                   "this_asset": mine}])
    return out


def _closed(asset):
    from . import live
    return live.closed_trades(asset)


def _learning(store, lo, hi):
    """How the engine's graded calls have gone over sessions lo .. hi-1."""
    right = wrong = neither = 0
    e_right = e_calls = 0
    for a in store["assets"]:
        y, od = store["y"][a][lo:hi], store["odds"][a][lo:hi]
        ok = (y >= 0) & np.isfinite(od[:, 0])
        yy, edge = y[ok].astype(int), od[ok][:, labels.UP] - od[ok][:, labels.DOWN]
        hit = ((edge > 0) & (yy == labels.UP)) | ((edge < 0) & (yy == labels.DOWN))
        right, neither = right + int(hit.sum()), neither + int((yy == 0).sum())
        wrong += int((yy > 0).sum() - hit.sum())
        sure = (np.abs(edge) >= 0.05) & (yy > 0)                   # only the calls where it claimed an edge
        e_right, e_calls = e_right + int((hit & sure).sum()), e_calls + int(sure.sum())
    return _rates({"right": right, "wrong": wrong, "neither": neither, "edge_calls": e_calls, "edge_right": e_right})


def _rates(c):
    c = dict(c, calls_graded=c["right"] + c["wrong"] + c["neither"])
    c["hit_pct"] = round(100.0 * c["right"] / max(c["right"] + c["wrong"], 1), 1)
    c["edge_hit_pct"] = round(100.0 * c["edge_right"] / c["edge_calls"], 1) if c["edge_calls"] else None
    return c


def build_page(store, state, entries, journal_tail=24):
    times, n = store["times"], len(store["times"])
    page = {"name": "Mind 15", "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "version": store["cfg"]["version"], "note": "Experimental model. Paper only. Not advice.",
            "mandate": {"idle_max_sessions": store["cfg"]["idle_max"], "session_minutes": 15,
                        "enter_bar_pts": store["cfg"]["theta_enter"] * 100,
                        "enter_bar_high_risk_pts": store["cfg"]["theta_enter_shock"] * 100,
                        "flip_bar_pts": store["cfg"]["theta_flip"] * 100},
            "cards": list(CARDS), "assets": {}, "voices": dict((v, model.VOICES[v][0]) for v in model.VOICE_NAMES)}
    for a in store["assets"]:
        mine = [e for e in entries if e["asset"] == a]
        if not mine:
            continue
        # the timeline shows the last day's entries, read back from the journal files
        from . import journal as _journal
        day = mine[-1]["time"][:10]
        prior = str((pd.Timestamp(day) - pd.Timedelta(days=1)).date())
        past = [e for d in (prior, day) for e in _journal.read_day(d) if e["asset"] == a]
        keyed = dict((e["time"], e) for e in past + mine)
        mine = [keyed[k] for k in sorted(keyed)]
        e, book = mine[-1], (state or {}).get("books", {}).get(a, {})
        px = store["px"][a]["close"]
        spark = [[int(times[i].timestamp()), round(float(px[i]), 2)] for i in range(max(0, n - 192), n)]
        page["assets"][a] = {
            "name": NAMES.get(a, a), "short": SHORT.get(a, a),
            "fee_pct_side": round(100 * store["cfg"].get("asset_cost", {}).get(a, store["cfg"]["cost_side"]), 3),
            "time": e["time"], "price": e["price"], "position": e["position"], "decision": e["decision"],
            "action": e["action"], "odds": e.get("odds"), "edge_pts": e.get("edge_pts"),
            "idle_sessions": e["idle_sessions"], "stop": e["stop"], "equity": e["equity"],
            "entry": book.get("entry") if book.get("pos") else None, "risk_high": e["risk"]["high"],
            "structure": e["structure"], "regime": e["regime"], "trend": e["trend"],
            "htf_bias": {1: "LONG", -1: "SHORT"}.get(e.get("htf_bias"), "NONE"), "bias_mas": e.get("bias_mas"),
            "release_soon": e.get("release_soon", False),
            "cards": e.get("cards", []), "voices": e.get("voices", []),
            "for_long": e.get("for_long", []), "for_short": e.get("for_short", []),
            "level_reads": e.get("level_reads"), "raw": e.get("raw"),
            "question": e.get("question"), "owner": e.get("owner"),
            "trade": e.get("trade"), "closed_trades": _closed(a),
            "journal": [{"time": x["time"], "action": x["action"], "position": x["position"], "price": x["price"],
                         "edge_pts": x.get("edge_pts"), "decision": x["decision"]} for x in mine[-journal_tail:]][::-1],
            "candles_24h": _candles(store, a), "stance_24h": _stance(store, a),   # (price_48h dropped 11 Nov: unused by the page)
            # v5.1: this market's own card rating (its group's) and the voices that vote here
            "market_group": group_of(a), "card_rating": group_rating(group_of(a), a),
            "voting_voices": list(store["cfg"].get("voting") or model.VOICE_NAMES),
        }
    page.update(_extras())
    page["voting_voices"] = list(store["cfg"].get("voting") or model.VOICE_NAMES)
    from . import owner
    page["questions_and_answers"] = dict(owner.trail(30), pin_required=owner.pin_is_set())
    lo7, lo30 = max(0, n - 7 * 96), max(0, n - 30 * 96)
    page["learning"] = {"last_7_days": _learning(store, lo7, n), "last_30_days": _learning(store, lo30, n),
                        "trust": dict((v, round(float(store["trust"][n - 1][k]), 3)) for k, v in enumerate(model.VOICE_NAMES))}
    return page


def portfolio(assets):
    """All the books together: how much is long, how much short, and what all the stops risk at once.
    (A readout: no limit is enforced; the owner's books stay full size.)"""
    long_n = short_n = risk = eq = 0.0
    n_long = n_short = 0
    for a, A in (assets or {}).items():
        t = (A or {}).get("trade") or {}
        eq += float(t.get("equity_marked") or A.get("equity") or 0.0)
        notional = float(t.get("notional_usd") or 0.0)
        if t.get("status") == "LONG":
            long_n, n_long = long_n + notional, n_long + 1
        elif t.get("status") == "SHORT":
            short_n, n_short = short_n + notional, n_short + 1
        risk += float(t.get("risk_to_stop_usd") or 0.0)
    return {"equity_usd": round(eq, 2), "long_usd": round(long_n, 2), "short_usd": round(short_n, 2),
            "net_usd": round(long_n - short_n, 2), "gross_usd": round(long_n + short_n, 2),
            "gross_x_equity": round((long_n + short_n) / eq, 2) if eq else None,
            "n_long": n_long, "n_short": n_short, "risk_to_all_stops_usd": round(risk, 2),
            "risk_to_all_stops_pct": round(100 * risk / eq, 2) if eq else None,
            "note": "If every open trade hit its stop at once, the books together would lose risk_to_all_stops_usd."}


def merge(fragments, order):
    """One page from each market group's own page (crypto first). Learning counts are summed over
    every market; trust stays per market, because each market's voices learn on their own."""
    have = [g for g in order if g in fragments]
    page = json.loads(json.dumps(fragments[have[0]]))
    page["assets"], page["markets"] = {}, {}
    page["learning"]["trust_by_market"] = {}
    for g in have:
        f = fragments[g]
        page["assets"].update(f["assets"])
        page["markets"][g] = list(f["assets"])
        page["learning"]["trust_by_market"][g] = f["learning"]["trust"]
    for span in ("last_7_days", "last_30_days"):
        tot = dict((k, 0) for k in ("right", "wrong", "neither", "edge_calls", "edge_right"))
        for g in have:
            for k in tot:
                tot[k] += fragments[g]["learning"][span].get(k, 0)
        page["learning"][span] = _rates(tot)
        page["learning"][span]["by_market"] = dict((g, fragments[g]["learning"][span]) for g in have)
    page["generated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    page["portfolio"] = portfolio(page["assets"])                  # all books together: long, short, risk to all stops
    page.pop("shadows", None)                                      # the challenger books, every market in one block
    views = dict((g, fragments[g]["shadows"]) for g in have if fragments[g].get("shadows"))
    if views:
        try:
            from . import shadows
            page["shadows"] = merge_shadows(views, shadows.scoreboard(views))
        except Exception:
            page["shadows"] = None
    try:                                                           # charter L1: the last day's biggest surprises
        from . import reports
        page["surprises"] = reports.page_block()
        page["playbook"] = reports.playbook_block()                # strategy books: setups, trades, totals
        page["scoreboard_all"] = reports.scoreboard_block()        # charter L4: every book, forward, with ranges
    except Exception:
        page["surprises"] = page.get("surprises")
    try:                                                           # charter M6: hit rate per horizon per market
        from . import reports
        page["horizon_skill"] = reports.horizon_skill_block()
        page["ideas"] = reports.ideas_block()                      # charter L3: the idea queue
    except Exception:
        page["horizon_skill"] = None
    return page


def merge_shadows(views, board):
    """The challengers of every market group as one block: per challenger, every asset's book."""
    books = {}
    for g, v in views.items():
        for name, b in v["books"].items():
            books.setdefault(name, {"title": b["title"], "assets": {}})["assets"].update(b["assets"])
    return {"scoreboard": board, "books": books,
            "markets": dict((g, {"started_utc": v.get("started_utc"), "as_of_utc": v.get("as_of_utc"),
                                 "assets": v["assets"]}) for g, v in views.items())}


def write_page(store, state, entries, out_dir, group="crypto", shadows=None):
    """Write this market group's part (page_<group>.json) and the merged page.json. `shadows`: this
    group's challenger books (shadows.step); when absent the last written view is kept."""
    os.makedirs(out_dir, exist_ok=True)
    frag = build_page(store, state, entries)
    if shadows is None:
        try:
            with open(os.path.join(out_dir, "page_%s.json" % group), encoding="utf-8") as fh:
                shadows = json.load(fh).get("shadows")
        except Exception:
            shadows = None
    if shadows is not None:
        frag["shadows"] = shadows
    with open(os.path.join(out_dir, "page_%s.json.tmp" % group), "w", encoding="utf-8") as fh:
        json.dump(frag, fh)
    os.replace(os.path.join(out_dir, "page_%s.json.tmp" % group), os.path.join(out_dir, "page_%s.json" % group))
    return rewrite_merged(out_dir)


def rewrite_merged(out_dir):
    """page.json again from every group's page_<group>.json, picking up the strategy books and the
    scoreboard as they stand now (live.step calls it after the books ran on the new bars)."""
    from .config import CFG
    order = [g for g, _ in CFG.get("universes", (("crypto", ()),))]
    fragments = {}
    for g in order:
        p = os.path.join(out_dir, "page_%s.json" % g)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                fragments[g] = json.load(fh)
    path = os.path.join(out_dir, "page.json")
    tmp = path + ".tmp"
    text = json.dumps(merge(fragments, order))
    # The public site never names the forecast model: it is "AlphaPrediction AI" there (the
    # /aitrading pages' rule). This file is public, so the name is replaced in keys and text alike.
    text = text.replace("Kronos", "AlphaPrediction AI").replace("kronos", "candle_forecast")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)
    return path
