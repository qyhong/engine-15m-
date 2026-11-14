# -*- coding: utf-8 -*-
"""livefeeds -- the data sources that have no free history: read them now, keep them forever.

Four sources are read once per session by the live engine (live.py) and appended to
data/live_<asset>.csv, one row per session, so that from the first live day on the engine
has these data points for its decisions and for post-mortems:

  order book   Binance spot depth (5,000 levels): how much resting size sits within 0.5%
               and 2% of the price on each side, and where the biggest wall is. The binned
               depth profile is also archived (data/raw/book_<asset>_<day>.jsonl) so a
               liquidity heatmap can be drawn and studied later.
  positioning  open interest on the USDT perpetual and its change over 1h and 24h
               (funding rates have history and live in data.py).
  Kronos       the candle forecast the estate's forecast job already publishes on this PC
               (C:/tmp/kronos/forecast/out/forecasts.json): where its median path and its
               ten sample paths end, for the 15m and the 1h forecast.
  news         the crypto headlines the same job collects (news.json), scored by a small
               word list. A headline is a data point here, not advice.

Every function returns plain numbers and never raises to the caller: a source that fails
is "no read" (NaN) for that session and the reason is returned beside it.
"""
import json
import math
import os
import time

import numpy as np
import pandas as pd

from .config import CFG, DATA_DIR
from .evidence import LIVE_RAW

KRONOS_OUT = os.environ.get("ENGINE15_KRONOS", "C:/tmp/kronos/forecast/out")
KRONOS_LEDGER = os.path.join(os.path.dirname(KRONOS_OUT), "ledger", "forecasts.jsonl")
FAPI = "https://fapi.binance.com"
BOOK_BAND = 0.02                    # the profile covers 2% each side of the mid price
BOOK_BINS = 40                      # in bins of 0.1%
NEWS_HALFLIFE_S = 2 * 3600          # a headline's weight halves every 2 hours
NEWS_WINDOW_S = 12 * 3600
GOOD = ("surge", "rally", "soar", "jump", "gain", "record high", "all-time high", "approve", "approval", "inflow",
        "adopt", "bullish", "accumulat", "upgrade", "breakout", "rebound", "recover", "climb", "rise", "buys",
        "partnership", "launch", "wins", "tops")
BAD = ("drop", "fall", "plunge", "crash", "decline", "outflow", "hack", "exploit", "ban", "lawsuit", "sue",
       "sell-off", "selloff", "liquidat", "bearish", "warn", "halt", "fraud", "reject", "slump", "tumble", "fear",
       "dump", "probe", "charges", "loses", "stolen", "delist", "cuts")


def live_path(asset):
    return os.path.join(DATA_DIR, "live_%s.csv" % asset.lower())


def load_live(asset):
    """-> frame of LIVE_RAW columns keyed by session OPEN time; empty when nothing was recorded."""
    if not os.path.exists(live_path(asset)):
        return pd.DataFrame(columns=LIVE_RAW)
    f = pd.read_csv(live_path(asset))
    f.index = pd.to_datetime(f.pop("ts_ms"), unit="ms", utc=True)
    for col in LIVE_RAW:
        if col not in f:
            f[col] = np.nan
    return f[LIVE_RAW].astype(float).sort_index()


def upsert_live(asset, rows):
    """rows: {session_open_ms: {column: value}}. Existing values are kept unless a new one is given."""
    old = load_live(asset)
    new = pd.DataFrame.from_dict(rows, orient="index")
    new.index = pd.to_datetime(new.index.astype("int64"), unit="ms", utc=True)
    for col in LIVE_RAW:
        if col not in new:
            new[col] = np.nan
    both = new[LIVE_RAW].astype(float).combine_first(old) if len(old) else new[LIVE_RAW].astype(float)
    out = both.sort_index()
    out.insert(0, "ts_ms", np.asarray(out.index.as_unit("ms").asi8, dtype="int64"))
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = live_path(asset) + ".tmp"
    out.to_csv(tmp, index=False)
    os.replace(tmp, live_path(asset))
    return len(out)


# ------------------------------------------------------------------ order book
def book_reads(bids, asks):
    """bids / asks: arrays of (price, size), best first. -> (reads, profile).
    imbalance = (bid size - ask size) / (bid size + ask size) inside the band: +1 all bids."""
    bids, asks = np.asarray(bids, dtype=float), np.asarray(asks, dtype=float)
    mid = (bids[0, 0] + asks[0, 0]) / 2.0
    bd, ad = (mid - bids[:, 0]) / mid, (asks[:, 0] - mid) / mid

    def imb(band):
        b, a = bids[bd <= band, 1].sum(), asks[ad <= band, 1].sum()
        return float((b - a) / (b + a)) if b + a > 0 else 0.0

    edges = np.linspace(0, BOOK_BAND, BOOK_BINS + 1)
    bprof = np.histogram(bd, bins=edges, weights=bids[:, 1])[0]
    aprof = np.histogram(ad, bins=edges, weights=asks[:, 1])[0]
    # the biggest wall each side, weighed by how close it is: a near, large bid wall is support
    bw, aw = int(np.argmax(bprof)), int(np.argmax(aprof))
    pull_b, pull_a = bprof[bw] / (bw + 1.0), aprof[aw] / (aw + 1.0)
    wall = float((pull_b - pull_a) / (pull_b + pull_a)) if pull_b + pull_a > 0 else 0.0
    reads = {"ob_imb_05": imb(0.005), "ob_imb_2": imb(BOOK_BAND), "ob_wall": wall}
    profile = {"mid": mid, "bid_05": float(bids[bd <= 0.005, 1].sum()), "ask_05": float(asks[ad <= 0.005, 1].sum()),
               "bid_2": float(bids[bd <= BOOK_BAND, 1].sum()), "ask_2": float(asks[ad <= BOOK_BAND, 1].sum()),
               "bin_pct": BOOK_BAND / BOOK_BINS * 100, "bids": [round(float(v), 4) for v in bprof],
               "asks": [round(float(v), 4) for v in aprof],
               "bid_wall_pct": round((bw + 0.5) * BOOK_BAND / BOOK_BINS * 100, 2),
               "ask_wall_pct": round((aw + 0.5) * BOOK_BAND / BOOK_BINS * 100, 2)}
    return reads, profile


def order_book(asset, archive=True):
    import requests
    try:
        r = requests.get(CFG["data_base_url"] + "/api/v3/depth", params={"symbol": asset, "limit": 5000}, timeout=20)
        r.raise_for_status()
        d = r.json()
        reads, profile = book_reads([(float(p), float(q)) for p, q in d["bids"]],
                                    [(float(p), float(q)) for p, q in d["asks"]])
    except Exception as e:                                          # a failed source is "no read"
        return {}, {"error": str(e)[:200]}
    if archive:
        raw = os.path.join(DATA_DIR, "raw")
        os.makedirs(raw, exist_ok=True)
        day = time.strftime("%Y-%m-%d", time.gmtime())
        with open(os.path.join(raw, "book_%s_%s.jsonl" % (asset.lower(), day)), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(profile, t=int(time.time()))) + "\n")
    return reads, profile


# ------------------------------------------------------------------ eagle view: the book out to +-10%
# Owner, 11 Nov 2026: "instead of just +-2% ... eagle view to +10% -10%". Binance spot's 5,000
# levels reach only ~1.5% on BTC (~5.5% on ETH), so the wide view comes from Coinbase's full
# order book (level 2: every price level, aggregated), keyless. A reading for the owner and the
# post-mortems; it does not vote.
EAGLE_PRODUCTS = {"BTCUSDT": "BTC-USD", "ETHUSDT": "ETH-USD"}
EAGLE_BAND, EAGLE_BINS = 0.10, 20                                   # 0.5% bins out to 10% each side


def eagle_profile(bids, asks, band=EAGLE_BAND, nbins=EAGLE_BINS):
    """bids / asks: (price, size), best first. -> profile dict (sizes per 0.5% bin, walls, totals)."""
    bids, asks = np.asarray(bids, dtype=float), np.asarray(asks, dtype=float)
    mid = (bids[0, 0] + asks[0, 0]) / 2.0
    bd, ad = (mid - bids[:, 0]) / mid, (asks[:, 0] - mid) / mid
    edges = np.linspace(0, band, nbins + 1)
    bprof = np.histogram(bd, bins=edges, weights=bids[:, 1])[0]
    aprof = np.histogram(ad, bins=edges, weights=asks[:, 1])[0]
    bw, aw = int(np.argmax(bprof)), int(np.argmax(aprof))
    bin_pct = band / nbins * 100
    skip = max(1, int(round(1.0 / bin_pct)))                        # "far" walls: beyond the first 1% (market makers sit nearer)
    fb, fa = skip + int(np.argmax(bprof[skip:])), skip + int(np.argmax(aprof[skip:]))

    def tot(d, side, lim):
        return float(side[d <= lim, 1].sum())
    b5, a5, b10, a10 = tot(bd, bids, 0.05), tot(ad, asks, 0.05), tot(bd, bids, band), tot(ad, asks, band)
    return {"mid": mid, "bin_pct": bin_pct, "reach_pct": band * 100,
            "bids": [round(float(v), 4) for v in bprof], "asks": [round(float(v), 4) for v in aprof],
            "bid_5": b5, "ask_5": a5, "bid_10": b10, "ask_10": a10,
            "imb_5": round((b5 - a5) / (b5 + a5), 3) if b5 + a5 else None,
            "imb_10": round((b10 - a10) / (b10 + a10), 3) if b10 + a10 else None,
            "bid_wall_pct": round((bw + 0.5) * bin_pct, 2), "bid_wall_px": round(mid * (1 - (bw + 0.5) * bin_pct / 100), 2),
            "bid_wall_size": round(float(bprof[bw]), 4),
            "ask_wall_pct": round((aw + 0.5) * bin_pct, 2), "ask_wall_px": round(mid * (1 + (aw + 0.5) * bin_pct / 100), 2),
            "ask_wall_size": round(float(aprof[aw]), 4),
            "bid_far_wall_pct": round((fb + 0.5) * bin_pct, 2), "bid_far_wall_px": round(mid * (1 - (fb + 0.5) * bin_pct / 100), 2),
            "bid_far_wall_size": round(float(bprof[fb]), 4),
            "ask_far_wall_pct": round((fa + 0.5) * bin_pct, 2), "ask_far_wall_px": round(mid * (1 + (fa + 0.5) * bin_pct / 100), 2),
            "ask_far_wall_size": round(float(aprof[fa]), 4)}


def eagle_book(asset, archive=True):
    """-> ({}, profile): the wide book (no model reads yet: live-only, it would start with no history)."""
    prod = EAGLE_PRODUCTS.get(asset)
    if not prod:
        return {}, None
    import requests
    try:
        r = requests.get("https://api.exchange.coinbase.com/products/%s/book" % prod, params={"level": 2},
                         headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=30)
        r.raise_for_status()
        d = r.json()
        prof = eagle_profile([(float(p), float(q)) for p, q, *_ in d["bids"]],
                             [(float(p), float(q)) for p, q, *_ in d["asks"]])
        prof["source"] = "Coinbase %s full order book" % prod
    except Exception as e:
        return {}, {"error": str(e)[:200]}
    if archive:
        raw = os.path.join(DATA_DIR, "raw")
        os.makedirs(raw, exist_ok=True)
        day = time.strftime("%Y-%m-%d", time.gmtime())
        with open(os.path.join(raw, "eagle_%s_%s.jsonl" % (asset.lower(), day)), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(prof, t=int(time.time()))) + "\n")
    return {}, prof


# ------------------------------------------------------------------ open interest
def open_interest(asset):
    import requests
    try:
        r = requests.get(FAPI + "/futures/data/openInterestHist", timeout=20,
                         params={"symbol": asset, "period": "15m", "limit": 97})
        r.raise_for_status()
        oi = [float(x["sumOpenInterest"]) for x in r.json()]
        ch1, ch24 = oi[-1] / oi[-5] - 1.0, oi[-1] / oi[0] - 1.0
    except Exception as e:
        return {}, {"error": str(e)[:200]}
    return ({"oi_chg_1h": max(-1.0, min(1.0, ch1 / 0.02)), "oi_chg_24h": max(-1.0, min(1.0, ch24 / 0.10))},
            {"open_interest": oi[-1], "change_1h_pct": round(ch1 * 100, 2), "change_24h_pct": round(ch24 * 100, 2)})


# ------------------------------------------------------------------ Kronos
def _kronos_cell(last_close, median_closes, path_ends):
    ups = [1.0 if p > last_close else 0.0 for p in path_ends]
    return median_closes[-1] / last_close - 1.0, 2.0 * (sum(ups) / len(ups)) - 1.0


def kronos(asset, session_close_s, path=None):
    """The forecast made from the candle that closed at session_close_s; a forecast with any
    other origin is not this session's read (stale or early) and is left out."""
    reads, raw = {}, {}
    try:
        with open(os.path.join(path or KRONOS_OUT, "forecasts.json"), encoding="utf-8") as fh:
            series = json.load(fh)["series"][asset]
    except Exception as e:
        return {}, {"error": str(e)[:200]}
    for tf, key, period in (("15m", "15m", 900), ("1h", "1h", 3600)):
        cell = series.get(tf)
        if not cell or not cell.get("median") or not cell.get("history"):
            continue
        fresh = cell["origin_t"] == session_close_s if tf == "15m" else \
            0 <= session_close_s - cell["origin_t"] < period
        raw[tf] = {"origin_t": cell["origin_t"], "fresh": bool(fresh)}
        if not fresh:
            continue
        ret, up = _kronos_cell(cell["history"][-1][4], [c[4] for c in cell["median"]],
                               [p[-1][1] for p in cell["paths"]])
        reads["kr_ret_%s_raw" % key], reads["kr_up_%s" % key] = ret, up
        raw[tf].update(median_end=cell["median"][-1][4], move_pct=round(ret * 100, 3), paths_up=round((up + 1) / 2, 2))
    return reads, raw


def kronos_backfill(assets, ledger=None, max_lag_s=600):
    """Every 15m / 1h forecast the estate's ledger holds becomes that session's read, provided
    it was generated within max_lag_s of its candle's close (so it existed at decision time).
    -> {asset: rows written}."""
    out = dict((a, {}) for a in assets)
    path = ledger or KRONOS_LEDGER
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("coin") not in out or r.get("tf") not in ("15m", "1h"):
                continue
            made = pd.Timestamp(r["generated_utc"]).timestamp()
            if not 0 <= made - r["origin_t"] <= max_lag_s:
                continue
            ret, up = _kronos_cell(r["last_c"], [c[4] for c in r["median"]], [p[-1] for p in r["paths"]])
            key = (r["origin_t"] - 900) * 1000                      # the session that closed at the origin
            out[r["coin"]].setdefault(key, {}).update({"kr_ret_%s_raw" % r["tf"]: ret, "kr_up_%s" % r["tf"]: up})
    return dict((a, upsert_live(a, rows)) for a, rows in out.items() if rows)


# ------------------------------------------------------------------ news
def score_headline(title):
    t = title.lower()
    good, bad = sum(w in t for w in GOOD), sum(w in t for w in BAD)
    return (good - bad) / float(good + bad) if good + bad else 0.0


def news(asset, now_s=None, path=None):
    """-> (reads, items): a time-decayed score of the last 12 hours' headlines for this coin.
    Headlines tagged with this coin count fully, untagged crypto headlines half, others not."""
    now_s = now_s or time.time()
    coin = asset.replace("USDT", "")
    try:
        with open(os.path.join(path or KRONOS_OUT, "news.json"), encoding="utf-8") as fh:
            items = json.load(fh)["items"]
    except Exception as e:
        return {}, [{"error": str(e)[:200]}]
    num = den = 0.0
    kept = []
    for it in items:
        age = now_s - it.get("t", 0)
        if not 0 <= age <= NEWS_WINDOW_S:
            continue
        coins = it.get("coins") or []
        w = 1.0 if coin in coins else 0.5 if not coins else 0.0
        if w == 0.0:
            continue
        s = score_headline(it.get("title", ""))
        decay = w * math.pow(0.5, age / NEWS_HALFLIFE_S)
        num, den = num + decay * s, den + decay
        kept.append({"t": it["t"], "title": it["title"], "source": it.get("source"), "url": it.get("url"),
                     "score": round(s, 2), "weight": round(decay, 3)})
    reads = {"news_score": num / den if den > 0 else 0.0, "news_heat": min(1.0, den / 5.0)}
    return reads, sorted(kept, key=lambda d: -d["weight"])[:8]


def collect(asset, session_close_s):
    """Read every live source once for the session that just closed. -> (reads, raw)."""
    reads, raw = {}, {}
    for name, fn in (("book", lambda: order_book(asset)), ("book_eagle", lambda: eagle_book(asset)),
                     ("positioning", lambda: open_interest(asset)),
                     ("kronos", lambda: kronos(asset, session_close_s)), ("news", lambda: news(asset))):
        r, payload = fn()
        reads.update(r)
        raw[name] = payload
    return reads, raw
