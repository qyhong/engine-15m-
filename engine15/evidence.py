# -*- coding: utf-8 -*-
"""evidence -- stage 1 of the thought process: what the engine READS at every 15m close.

One row per closed 15-minute bar. Row i is everything the engine may know at the close of
bar i: its own closed bars and, through data.htf_on_15, only higher-timeframe bars that
have themselves closed. tests/test_no_lookahead.py cuts the future off and checks that no
row changes.

The reads are grouped into GROUPS; each group is one VOICE of the model and maps to one of
the ten decision cards (CARDS). Three groups have no history anywhere for free, so they are
read live only and start with no training rows: the order book, the Kronos candle forecast
and the news. In a replay of the past they are zero ("no read") and say nothing.
"""
import warnings
from collections import OrderedDict

import numpy as np
import pandas as pd

warnings.simplefilter("ignore", pd.errors.PerformanceWarning)    # the frame is built column by column on purpose

from . import econ
from . import owner
from . import indicators as ind
from .config import CFG
from .data import htf_on_15, resample

SOURCES = []                            # the second ten cards (engine15/sources/*.py), each one optional
try:
    import importlib
    from . import sources as _sources_pkg
    for _name in _sources_pkg.MODULES:
        try:
            SOURCES.append(importlib.import_module("engine15.sources." + _name))
        except Exception:               # pragma: no cover - a source that will not import is simply absent
            pass
except Exception:                       # pragma: no cover
    pass

try:                                    # support / resistance (engine15/levels.py)
    from . import levels as _levels
except Exception:                       # pragma: no cover - the module is optional until built
    _levels = None

REGIME_FEATS = ["rg_" + r for r in ind.REGIMES if r != "TRANSITION"]
LIVE_RAW = ["kr_ret_15m_raw", "kr_up_15m", "kr_ret_1h_raw", "kr_up_1h",         # Kronos (kronos.py)
            "ob_imb_05", "ob_imb_2", "ob_wall",                                  # order book (livefeeds.py)
            "oi_chg_1h", "oi_chg_24h",                                           # open interest (livefeeds.py)
            "news_score", "news_heat"]                                           # news (livefeeds.py)


CRYPTO_ONLY_SOURCES = ("market", "flows")            # ETF flows, stablecoins, Coinbase premium, breadth, Fear and Greed
# Voices with nothing to read outside crypto. For gold, silver, USDJPY and the S&P 500 they are
# removed (owner, 11 Nov 2026: "Remove from the new four"): no card on the page, no vote, no
# reading. "Time and session" (in the derivs module) stays: it means as much there as in crypto.
CRYPTO_ONLY_VOICES = ("flow", "funding", "book", "basis", "lsratio", "liq", "options",
                      "etf", "stable", "cbprem", "breadth", "sentiment")


def is_crypto(asset):
    return asset in CFG.get("crypto", CFG["assets"])


VOICE_ASSETS = {}                      # voice -> the assets it applies to, from a module's APPLIES
for _m in SOURCES:
    VOICE_ASSETS.update(getattr(_m, "APPLIES", {}) or {})


def voice_applies(voice, asset):
    """A voice reads, votes and shows its card only where it means something: crypto-only voices
    for BTC/ETH; a module may declare APPLIES = {voice: (assets...)} for its own voices."""
    if voice in CRYPTO_ONLY_VOICES:
        return is_crypto(asset)
    if voice in VOICE_ASSETS:
        return asset in VOICE_ASSETS[voice]
    return True


def sources_for(asset):
    """The second-ten source modules that apply to this asset."""
    out = []
    for m in SOURCES:
        name = m.__name__.rsplit(".", 1)[-1]
        if not is_crypto(asset) and name in CRYPTO_ONLY_SOURCES:
            continue
        if any(voice_applies(v, asset) for v in m.GROUPS):
            out.append(m)
    return out


def cards_for(asset):
    """The decision cards shown for this asset: a card none of whose voices apply is not shown."""
    return [t for t, vs in CARDS.items() if not vs or any(voice_applies(v, asset) for v in vs)]


def _clip(s, lim):
    return s.clip(-lim, lim)


def build_one(df15, funding=None, live=None):
    """Evidence of one asset from its own bars (cross-asset reads are added by build).
    funding: Series of funding rates keyed by the time each was set. live: frame of LIVE_RAW
    columns keyed by session open time (only sessions the live engine actually saw)."""
    c = df15["close"]
    ev = pd.DataFrame(index=df15.index)
    ev["px"] = c
    h1, h4, d1 = resample(df15, "1h"), resample(df15, "4h"), resample(df15, "1D")
    my_close = df15.index + pd.Timedelta(milliseconds=CFG["bar_ms"])

    # ---- 1. trend strength, every timeframe (the estate's trend-map-v1)
    ev["tr_15m"] = ind.trend_score(c)
    ev["tr_1h"] = htf_on_15(df15, "1h", ind.trend_score(h1["close"]))
    ev["tr_4h"] = htf_on_15(df15, "4h", ind.trend_score(h4["close"]))
    ev["tr_1d"] = htf_on_15(df15, "1D", ind.trend_score(d1["close"]))
    w = d1["close"].resample("W-MON", label="left", closed="left").last().dropna()
    ws = ind.trend_score(w)
    ws.index = ws.index + pd.Timedelta(days=7)                      # a week is known when it has closed
    ev["tr_1w"] = ws.reindex(my_close, method="ffill").values
    ev["tide"] = ev[["tr_4h", "tr_1d"]].mean(axis=1)

    # ---- volatility yardsticks
    ev["atr15"] = ind.atr_wilder(df15)
    ev["atr1h"] = htf_on_15(df15, "1h", ind.atr_wilder(h1))
    atr4h = htf_on_15(df15, "4h", ind.atr_wilder(h4))
    tr15 = ind.true_range(df15)
    ev["shock_ratio"] = tr15.rolling(4).mean() / tr15.rolling(96).mean()
    ev["vol_rank"] = (ev["atr1h"] / c).rolling(2880).rank(pct=True)
    ev["f_volrank"] = 2.0 * ev["vol_rank"] - 1.0
    ev["f_shock"] = ev["shock_ratio"].clip(0, 5) - 1.0
    ev["shock"] = ev["shock_ratio"] >= CFG["shock_ratio"]

    # ---- 2. regime (the estate's six labels, last closed daily bar)
    ev["regime"] = htf_on_15(df15, "1D", ind.regime_daily(d1))
    for r in ind.REGIMES:
        if r != "TRANSITION":
            ev["rg_" + r] = (ev["regime"] == r).astype(float)
    dc = d1["close"]
    rgd = pd.DataFrame({"rg_er": (dc - dc.shift(20)).abs() / dc.diff().abs().rolling(20).sum().replace(0, np.nan),
                        "rg_ret5_pct": (dc / dc.shift(5) - 1.0) * 100.0,
                        "rg_atr_x": ind.atr_simple(d1, 14) / ind.atr_simple(d1, 14).rolling(50).mean()})
    for col in rgd:                                                 # readable regime numbers for the card
        ev[col] = htf_on_15(df15, "1D", rgd[col])

    # ---- 3. support and resistance
    if _levels is not None:
        lv = _levels.build(df15)
        for col in list(_levels.FEATURES) + list(_levels.READS):
            ev[col] = lv[col].values

    # ---- 4. momentum and stretch
    lr = np.log(c).diff()
    sig = lr.rolling(672).std()
    for name, k in (("mom_1h", 4), ("mom_4h", 16), ("mom_24h", 96), ("mom_7d", 672)):
        ev[name] = _clip(np.log(c / c.shift(k)) / (sig * np.sqrt(k)), 3.0)
        ev[name.replace("mom_", "ret_") + "_pct"] = (c / c.shift(k) - 1.0) * 100.0      # readable
    ema20_1h = htf_on_15(df15, "1h", h1["close"].ewm(span=20, adjust=False, min_periods=20).mean())
    ema50_4h = htf_on_15(df15, "4h", h4["close"].ewm(span=50, adjust=False, min_periods=50).mean())
    # the higher-timeframe bias (v5, from the BTC post-mortem of 10 Nov 2026): every timeframe from
    # 1h to daily trending one way AND price on that side of the 1h EMA50 and the 4h EMA20 and EMA50,
    # which then act as resistance (price below them) or support (price above them)
    ema50_1h = htf_on_15(df15, "1h", h1["close"].ewm(span=50, adjust=False, min_periods=50).mean())
    ema20_4h = htf_on_15(df15, "4h", h4["close"].ewm(span=20, adjust=False, min_periods=20).mean())
    t1, t4, td = ev["tr_1h"], ev["tr_4h"], ev["tr_1d"]
    dn = (t1 <= -0.5) & (t4 <= -0.5) & (td <= -0.5) & (c < ema50_1h) & (c < ema20_4h) & (c < ema50_4h)
    up = (t1 >= 0.5) & (t4 >= 0.5) & (td >= 0.5) & (c > ema50_1h) & (c > ema20_4h) & (c > ema50_4h)
    ev["htf_bias"] = np.where(up, 1.0, np.where(dn, -1.0, 0.0))
    ev["bias_ema50_1h_px"], ev["bias_ema20_4h_px"], ev["bias_ema50_4h_px"] = ema50_1h, ema20_4h, ema50_4h
    ev["stretch_1h"] = _clip((c - ema20_1h) / ev["atr1h"], 4.0) / 2.0
    ev["stretch_4h"] = _clip((c - ema50_4h) / atr4h, 4.0) / 2.0
    hi, lo = df15["high"].rolling(96).max(), df15["low"].rolling(96).min()
    ev["rangepos"] = (2.0 * (c - lo) / (hi - lo).replace(0, np.nan) - 1.0).fillna(0.0)
    k4h = htf_on_15(df15, "4h", ind.stoch_rsi_k(h4["close"]))
    k1d = htf_on_15(df15, "1D", ind.stoch_rsi_k(d1["close"]))
    ev["k_15m"] = (ind.stoch_rsi_k(c) - 50.0) / 50.0
    ev["k_1h"] = (htf_on_15(df15, "1h", ind.stoch_rsi_k(h1["close"])) - 50.0) / 50.0
    ev["k_4h"] = (k4h - 50.0) / 50.0
    # a dip inside an uptrend / a bounce inside a downtrend (the estate's lesson: weakness IS
    # the long entry, but only where the larger trend is up; the mirror for shorts)
    tide = ev["tide"]
    ev["pullback"] = tide.clip(lower=0) * (-ev["k_1h"]).clip(lower=0) - (-tide).clip(lower=0) * ev["k_1h"].clip(lower=0)

    # ---- 5. order flow: cumulative volume delta (taker buys minus taker sells)
    delta = 2.0 * df15["taker_buy"] - df15["volume"]
    dsig = delta.rolling(672).std()
    for name, k in (("cvd_1h", 4), ("cvd_4h", 16), ("cvd_24h", 96)):
        ev[name] = _clip(delta.rolling(k).sum() / (dsig * np.sqrt(k)), 3.0)
        ev[name + "_raw"] = delta.rolling(k).sum()                  # readable: coins bought minus sold by takers
    ev["vol_24h"] = df15["volume"].rolling(96).sum()
    ev["cvd_div"] = _clip(ev["cvd_4h"] - ev["mom_4h"], 3.0)         # buying without price progress, or the reverse

    # ---- 6. positioning: perpetual funding (longs pay shorts when positive)
    if funding is not None and len(funding):
        f = pd.DataFrame({"rate": funding})
        f["z"] = (f["rate"] - f["rate"].rolling(90).mean()) / f["rate"].rolling(90).std().replace(0, np.nan)
        f["sum3d"] = f["rate"].rolling(9).sum()
        f = f.reindex(my_close, method="ffill")
        ev["fund_rate"] = _clip(pd.Series(f["rate"].values, index=ev.index) / 0.0005, 2.0)
        ev["fund_z"] = _clip(pd.Series(f["z"].values, index=ev.index), 3.0)
        ev["fund_3d"] = _clip(pd.Series(f["sum3d"].values, index=ev.index) / 0.0015, 2.0)
        ev["fund_raw"], ev["fund_3d_raw_pct"] = f["rate"].values, f["sum3d"].values * 100.0      # readable
    else:
        ev["fund_rate"] = ev["fund_z"] = ev["fund_3d"] = ev["fund_raw"] = ev["fund_3d_raw_pct"] = np.nan

    # ---- 9. the library's working strategies, as they stand
    ev["st_core"] = ind.strat_core_zone(k4h, k1d)
    ev["st_donch"] = htf_on_15(df15, "1D", ind.strat_donchian_c12(d1))
    ev["st_burst"] = htf_on_15(df15, "1D", ind.strat_burst2(d1))
    ev["st_tsmom"] = htf_on_15(df15, "1D", ind.strat_tsmom(d1))
    ev["st_sma120"] = htf_on_15(df15, "1D", ind.strat_sma120(d1))
    ev["st_bh"] = htf_on_15(df15, "1D", ind.strat_bh_regime(d1))

    # ---- 7, 8, 10. live-only reads: order book, Kronos forecast, news
    lv = None if live is None or not len(live) else live.reindex(df15.index)
    for col in LIVE_RAW:
        ev[col] = np.nan if lv is None or col not in lv else lv[col].values
    for col in ("kr_ret_1h_raw", "kr_up_1h"):                       # an hourly forecast stands for its hour
        ev[col] = ev[col].ffill(limit=3)
    unit = (ev["atr1h"] / c).replace(0, np.nan)
    ev["kr_ret_15m"] = _clip(ev["kr_ret_15m_raw"] / unit, 3.0) / 3.0
    ev["kr_ret_1h"] = _clip(ev["kr_ret_1h_raw"] / unit, 3.0) / 3.0
    return ev


def build(bars, funding=None, live=None, rows=None):
    """bars: {asset: 15m frame}. -> {asset: evidence frame} on the common index, with the
    cross-asset reads added (for two assets: each one reads the other).
    rows: positions on the common index to keep (sorted). Every reading is still computed over
    all history, then only those rows are kept, one piece at a time, so the result equals
    build(...)[asset].iloc[rows] exactly at a fraction of the memory (evcache.py, the live step)."""
    common = None
    for df in bars.values():
        common = df.index if common is None else common.intersection(df.index)
    if rows is None:
        cut, index = (lambda f: f), common
    else:
        rows = np.asarray(rows, dtype=np.int64)
        cut, index = (lambda f: f.iloc[rows]), common[rows]
    out = {}
    for a, df in bars.items():
        out[a] = cut(build_one(df.loc[common], (funding or {}).get(a), (live or {}).get(a)))
    assets = list(out)
    macro = cut(econ.features(common))                             # economic calendar and macro tape: the same for every coin
    for a in assets:
        for col in list(econ.FEATURES) + list(econ.RAW):
            out[a][col] = macro[col].values
        # v5 release guard: a high-impact US release within the next hour (ec_next = 1 - hours ahead / 24)
        out[a]["release_soon"] = macro["ec_next"].values >= 1.0 - 1.0 / 24.0 - 1e-9
        out[a]["owner_view"] = cut(owner.features(common, a))["owner_view"].values      # the owner's own view, when given
        extra = []
        mods = sources_for(a)
        for m in mods:                                             # the second ten cards
            f = cut(m.features(common, a))
            extra.append(f[[col for col in f.columns if col not in out[a].columns]])
            del f
        for m in SOURCES:                                          # a card that does not apply: "no read"
            if m not in mods:
                cols = [f for feats in (t[1] for t in m.GROUPS.values()) for f in feats]
                extra.append(pd.DataFrame(np.nan, index=index, columns=[c for c in dict.fromkeys(cols) if c not in out[a].columns]))
        if extra:
            add = pd.concat(extra, axis=1)
            add = add.loc[:, ~add.columns.duplicated()]
            add.index = out[a].index
            out[a] = pd.concat([out[a], add], axis=1)
        keep = set(c for v in GROUPS if voice_applies(v, a) for c in GROUPS[v][1])
        for v in GROUPS:                                           # a voice that does not apply reads nothing here
            if not voice_applies(v, a):
                for col in GROUPS[v][1]:
                    if col not in keep:                            # a column another voice still uses stays
                        out[a][col] = np.nan
        others = [o for o in assets if o != a]
        if others:                                                 # alone in its market (USDJPY, S&P): no read
            out[a]["x_mom_24h"] = out[others[0]]["mom_24h"].values
            out[a]["x_tr_1d"] = out[others[0]]["tr_1d"].values
        else:
            out[a]["x_mom_24h"] = out[a]["x_tr_1d"] = np.nan
        btc = out.get("BTCUSDT", out[a])
        out[a]["st_btc120"] = btc["st_sma120"].values          # the estate's BTC trend switch, for every coin
    return out


# name -> (title, features). Each group is one voice.
GROUPS = OrderedDict([
    ("trend", ("Timeframe strength, 15m to weekly", ["tr_15m", "tr_1h", "tr_4h", "tr_1d", "tr_1w"])),
    ("regime", ("Market regime", REGIME_FEATS)),
    ("levels", ("Support and resistance", list(_levels.FEATURES) if _levels is not None else [])),
    ("momentum", ("Momentum", ["mom_1h", "mom_4h", "mom_24h", "mom_7d"])),
    ("meanrev", ("Stretch and exhaustion", ["stretch_1h", "stretch_4h", "rangepos", "k_15m", "k_1h", "k_4h"])),
    ("pullback", ("Pullback inside the trend", ["pullback", "tr_1d", "k_1h"])),
    ("flow", ("Order flow (CVD)", ["cvd_1h", "cvd_4h", "cvd_24h", "cvd_div"])),
    ("funding", ("Funding and positioning", ["fund_rate", "fund_z", "fund_3d", "oi_chg_1h", "oi_chg_24h"])),
    ("book", ("Order-book liquidity (live only)", ["ob_imb_05", "ob_imb_2", "ob_wall"])),
    ("kronos", ("Kronos candle forecast (live only)", ["kr_ret_15m", "kr_up_15m", "kr_ret_1h", "kr_up_1h"])),
    ("strategies", ("The library's working strategies",
                    ["st_core", "st_donch", "st_burst", "st_tsmom", "st_btc120", "st_bh"])),
    ("news", ("News (live only)", ["news_score", "news_heat"])),
    ("macro", ("Economic calendar and macro tape", list(econ.FEATURES))),
    ("risk", ("Risk and volatility", ["f_volrank", "f_shock"])),
    ("cross", ("The other coin", ["x_mom_24h", "x_tr_1d"])),
    ("owner", ("The owner's view", list(owner.FEATURES))),
])
if not GROUPS["levels"][1]:
    del GROUPS["levels"]
_first = list(GROUPS.items())
_owner = _first.pop()                                            # keep the owner's voice last
GROUPS = OrderedDict(_first)
SOURCE_CARDS = OrderedDict()                                     # card title -> voices, for cards 11 to 20
for _m in SOURCES:
    for _voice, (_title, _feats) in _m.GROUPS.items():
        GROUPS[_voice] = (_title, list(_feats))
        SOURCE_CARDS[_title] = [_voice]
GROUPS[_owner[0]] = _owner[1]
# The ten decision cards of the page: card title -> the voices behind it.
CARDS = OrderedDict([
    ("Timeframe strength", ["trend"]), ("Regime", ["regime"]), ("Support and resistance", ["levels"]),
    ("Momentum and stretch", ["momentum", "meanrev", "pullback"]), ("Order flow (CVD)", ["flow"]),
    ("Funding and positioning", ["funding"]), ("Liquidity (order book)", ["book"]),
    ("Kronos forecast", ["kronos"]), ("Working strategies", ["strategies"]),
    ("News and economic events", ["news", "macro"]),
])
CARDS.update(SOURCE_CARDS)                                       # twenty cards in all
FEATURES = []
for _title, _feats in GROUPS.values():
    FEATURES += [f for f in _feats if f not in FEATURES]
REQUIRED = ["tr_15m", "tr_1h", "tr_4h", "tr_1d", "atr1h", "mom_7d", "vol_rank", "k_4h", "stretch_4h", "regime"]


def matrix(ev):
    """-> (X, ready): the feature matrix (a missing optional read = 0, "no read") and the rows
    where every REQUIRED read exists."""
    ready = ev[REQUIRED].notna().all(axis=1).values
    return ev[FEATURES].astype(float).fillna(0.0).values, ready
