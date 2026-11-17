# -*- coding: utf-8 -*-
"""stocks -- the S&P 500 model read on single stocks: the Setups page's top five House buys. PAPER ONLY.

The owner (17 Nov 2026), asked how to apply the S&P analytics to the top five stocks House members bought, chose
"S&P model on each stock": the cards the S&P 500 call uses, read on each stock's own bars (plus the market-wide
cards exactly as the S&P call has them), combined with the S&P group's LEARNED voices and trust. Nothing is
refitted here and nothing of the index group is written: the voices are the index group's own weekly refit
(read from data/evcache/index/fits/, the file whose answers match the S&P call's journal entry) and the trust is
the trust that call used (its journal entry). Labelled "not validated on single stocks"; every stance is graded
live with the engine's own triple barrier so a hit rate builds up.

    tickers   MIND15_TOP5_FILE (default /var/lib/aitrading-top5/top5.json, the website's file; order kept,
              an empty list is valid); unreadable: the last list used (state), else MIND15_STOCKS, else
              the default five. At most five; symbols A-Z, digits, '.', '-', up to 10 characters.
    bars      Yahoo 15m bars (60 days, then 5 days, extdata.fetch_chart / parse_chart: closed bars only, the
              same feed-delay and forming-bar rules as the S&P 500), US cash hours only, kept growing in
              data/stocks/<TICKER>_15m.csv; daily bars (10 years, once) in data/stocks/<TICKER>_1d.csv for the
              days before the first stored 15m bar.
    readings  the engine's own code (evidence.build_one, every source module's features(..., bars=)).
              Daily bars enter as one placeholder 15m bar per day before the first real 15m bar; the
              readings are made twice with two different placeholder shapes (one bar a day, or two bars at
              different hours with the same daily bar) and a reading is kept only where both agree, i.e. it
              depends on the daily bars and the real 15m bars only. Elsewhere the reading made on the real
              15m bars alone is used (NaN = no read). Market-wide cards (calendar and macro tape, volatility
              gauges, rates and the dollar, stock-market breadth) are copied from the S&P call's own readings
              at the same close. Index-only cards (S&P futures overnight, put/call, megacap earnings, CFTC S&P
              positioning, the candle forecast, the owner's S&P view) and live-only news: no read.
    stance    the voices' answers on the stock's readings, mixed as the engine mixes (trust x speaks,
              trust_cap), P(up) - P(down) in points; LONG / SHORT only where policy.decide, flat with an idle
              clock of 0, would ENTER (5 points, 10 when risk is high, 15 against the higher-timeframe bias,
              none in the hour before a high-impact US release); else FLAT. No book, stop, target or size.
    grading   labels.triple_barrier on the stock's bars, 1.5 x ATR14 of the hourly chart, 26 bars (one US
              session); NEITHER is not counted in the hit rate, as the engine counts.
    output    out/live/stocks.json and <MIND15_SETUPS_WEB_DIR>/stocks.json (atomic, 0644). Log of every new
              stance: data/stocks_log.jsonl; state: data/stocks_state.json.
"""
import json
import math
import os
import re
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from . import data, extdata, labels, model, policy
from .config import CFG, DATA_DIR, JOURNAL_DIR, OUT_DIR, voting_for

SCHEMA = 1
NOTE = "Paper model reading. Not a recommendation."
MODEL = "S&P 500 model applied to single stocks; not validated on single stocks"
FILE = "stocks.json"
WEB_ENV = "MIND15_SETUPS_WEB_DIR"
WEB_MODE = 0o644
TOP5_ENV = "MIND15_TOP5_FILE"
TOP5_DEFAULT = "/var/lib/aitrading-top5/top5.json"
STOCKS_ENV = "MIND15_STOCKS"
DEFAULT = ("NVDA", "ARGX", "MU", "T", "DDOG")
MAX_TICKERS = 5
SYMBOL = re.compile(r"^[A-Z0-9.\-]{1,10}$")
GROUP, INDEX = "index", "SPX"
SESSION = "SPX"                          # the US cash session (extdata.open_mask): the stocks keep the S&P's hours
HORIZON = int(CFG.get("group_horizon", {}).get(GROUP, CFG["horizon"]))
BUDGET_S = 40.0                          # never more than this of a step
REQUEST_TIMEOUT_S = 8.0                  # one Yahoo request, at most (the budget shrinks it further)
STALE_S = 2 * 3600                       # a last bar older than this while the market is open: stale
DAILY_RANGE = "10y"
BAR_MS = int(CFG["bar_ms"])
LIVE_DIR = os.path.join(OUT_DIR, "live")
# cards that describe the S&P itself or that only exist live: no read for a single stock
SKIP_VOICES = ("overnight", "putcall", "earnings", "cot", "kronos", "owner", "news", "cross")
# market-wide cards: the S&P call's own readings at the same close
MARKET_VOICES = ("macro", "volx", "rates", "eqbreadth")
REQUIRED = [c for c in ("tr_15m", "tr_1h", "tr_4h", "tr_1d", "atr1h", "mom_7d", "k_4h", "stretch_4h", "regime")]
#   (evidence.REQUIRED without vol_rank: it ranks 30 days of 15m volatility over 2,880 15m bars, more than the
#    60 days of 15m bars Yahoo serves, so it would never read for a stock)
EDGE_WORD = re.compile(r"\bedge\b", re.I)
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


# ------------------------------------------------------------------ small helpers
def _num(v):
    if isinstance(v, bool):
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _r(v, d):
    v = _num(v)
    return None if v is None else round(v, d) + 0.0


def _iso(ms):
    return None if ms is None else (_EPOCH + timedelta(milliseconds=int(ms))).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now():
    return time.time()


def _clean(x):
    """Valid JSON only (a number that is not finite is null); the forecast model is never named."""
    if isinstance(x, dict):
        return dict((k, _clean(v)) for k, v in x.items())
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (float, np.floating)):
        x = float(x)
        return x if math.isfinite(x) else None
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, str):
        return x.replace("Kronos", "AlphaPrediction AI").replace("kronos", "candle_forecast")
    return x


def _atomic(path, text, mode=None):
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


class Paths:
    """Where everything lives (the tests point it at a temp folder)."""

    def __init__(self, data_dir=None, journal_dir=None, out_dir=None, fits_dir=None):
        self.data = data_dir or DATA_DIR
        self.journal = journal_dir or JOURNAL_DIR
        self.out = out_dir or LIVE_DIR
        self.fits = fits_dir or os.path.join(self.data, "evcache", GROUP, "fits")
        self.stocks = os.path.join(self.data, "stocks")
        self.state = os.path.join(self.data, "stocks_state.json")
        self.log = os.path.join(self.data, "stocks_log.jsonl")
        self.earnings = os.path.join(self.data, "sources", "earnings_megacap.csv")

    def bars15(self, t):
        return os.path.join(self.stocks, "%s_15m.csv" % t)

    def bars1d(self, t):
        return os.path.join(self.stocks, "%s_1d.csv" % t)


def load_state(paths):
    try:
        with open(paths.state, encoding="utf-8") as fh:
            st = json.load(fh)
        return st if isinstance(st, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(paths, st):
    os.makedirs(os.path.dirname(paths.state), exist_ok=True)
    _atomic(paths.state, json.dumps(_clean(st), allow_nan=False))


# ------------------------------------------------------------------ the tickers
def valid_symbol(s):
    if not isinstance(s, str):
        return None
    s = s.strip().upper()
    return s if SYMBOL.match(s) else None


def _symbols(items):
    """[valid symbols] in order (duplicates dropped), or None when any entry is not a symbol."""
    out = []
    for s in items:
        v = valid_symbol(s)
        if v is None:
            return None
        if v not in out:
            out.append(v)
    return out[:MAX_TICKERS]


def read_top5(path):
    """The website's file -> (tickers, generated_utc) or None when missing, unreadable or malformed.
    An empty "tickers" list is valid (a thin month)."""
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(doc, dict) or not isinstance(doc.get("tickers"), list):
        return None
    got = _symbols(doc["tickers"])
    if got is None:
        return None
    gen = doc.get("generated_utc")
    return got, gen if isinstance(gen, str) else None


def resolve_tickers(state, env=None):
    """-> (tickers, source, as_of_utc). The file first; else the last list used (kept in the state); else
    MIND15_STOCKS; else the default five. A good file is remembered in state["last_list"]."""
    env = os.environ if env is None else env
    path = (env.get(TOP5_ENV) or "").strip() or TOP5_DEFAULT
    got = read_top5(path)
    if got is not None:
        state["last_list"] = {"tickers": got[0], "generated_utc": got[1]}
        return list(got[0]), "top5.json", got[1]
    last = state.get("last_list")
    if isinstance(last, dict) and isinstance(last.get("tickers"), list) and _symbols(last["tickers"]) is not None:
        return _symbols(last["tickers"]), "last list", last.get("generated_utc")
    raw = (env.get(STOCKS_ENV) or "").strip()
    if raw:
        got = _symbols([s for s in raw.split(",") if s.strip()])
        if got:
            return got, "env", None
    return list(DEFAULT), "default", None


# ------------------------------------------------------------------ bars (Yahoo, through extdata)
def _ysym(t):
    return t.replace(".", "-")                                  # BRK.B is BRK-B on Yahoo


def last_session_bar_ms(now):
    """Open time (ms) of the last 15m slot of the US cash session that has closed by `now`, or None."""
    end = pd.Timestamp(int(now // 900) * 900 - 900, unit="s", tz="UTC")
    grid = pd.date_range(end - pd.Timedelta(days=12), end, freq="15min")
    m = extdata.open_mask(SESSION, grid)
    return int(data.to_ms(grid[m])[-1]) if m.any() else None


def _load(path):
    return data.load("x", path=path) if os.path.exists(path) else None


def _timeout(budget_left):
    return max(1.0, min(REQUEST_TIMEOUT_S, budget_left))


def fetch_15m(ticker, path, now, budget_left=REQUEST_TIMEOUT_S, log=None):
    """Extend the stored 15m bars with every closed bar since the last one. ONE request (60 days when nothing
    is stored or the store is more than 4 days old, else 5). -> (bars or None, error or None)."""
    old = _load(path)
    rng = "60d" if old is None or not len(old) or now - old.index[-1].timestamp() > 4 * 86400 else "5d"
    keep_t = extdata.YF_TIMEOUT
    try:
        extdata.YF_TIMEOUT = _timeout(budget_left)              # the step's budget: never a 30-second wait here
        payload = extdata.fetch_chart(_ysym(ticker), rng)
        new, _info = extdata.parse_chart(payload, now=now)
    except Exception as e:
        return old, "the price feed did not answer (%s)" % type(e).__name__
    finally:
        extdata.YF_TIMEOUT = keep_t
    new = new[extdata.open_mask(SESSION, new.index, calendar=False)]      # US cash hours only
    new = new[~new.index.duplicated(keep="last")].sort_index()
    if old is not None and len(old):
        new = new[new.index > old.index[-1]]
        df = pd.concat([old, new]) if len(new) else old
    else:
        df = new
    if not len(df):
        return None, "no price data from the feed"
    if len(new):
        data.save("x", df, path=path)
    return df, None


def _daily_chart(symbol, rng, timeout):
    """ONE request for daily bars: extdata.fetch_chart's request with interval 1d (fetch_chart asks for 15m
    only), the same host, User-Agent and pause rule (extdata._last_request is shared)."""
    import requests
    wait = extdata.YF_PAUSE - (time.time() - extdata._last_request[0])
    if wait > 0:
        time.sleep(wait)
    try:
        r = requests.get(extdata.YF_URL + symbol, params={"interval": "1d", "range": rng},
                         headers={"User-Agent": extdata.YF_UA}, timeout=timeout)
    finally:
        extdata._last_request[0] = time.time()
    r.raise_for_status()
    return r.json()


def parse_daily(payload):
    """Yahoo's daily chart JSON -> a frame in data.COLS keyed by the day's UTC midnight (the key resample('1D')
    gives a day). Rows with a missing or non-positive price are dropped. The caller uses only days before its
    first stored 15m bar, so the day still trading never enters."""
    res = payload["chart"]["result"][0]
    ts = res.get("timestamp") or []
    q = ((res.get("indicators") or {}).get("quote") or [{}])[0] or {}
    raw = pd.DataFrame({"t": pd.Series(ts, dtype="int64")})
    for k in ("open", "high", "low", "close", "volume"):
        col = list(q.get(k) or [])[:len(ts)]
        raw[k] = pd.to_numeric(pd.Series(col + [None] * (len(ts) - len(col)), dtype=object), errors="coerce")
    ok = raw[["open", "high", "low", "close"]].notna().all(axis=1) & (raw[["open", "high", "low", "close"]] > 0).all(axis=1)
    raw = raw[ok]
    day = pd.to_datetime(raw.t.values, unit="s", utc=True)
    day = extdata._local(pd.DatetimeIndex(day), extdata.NY).normalize()          # the New York trading date
    df = pd.DataFrame({"open": raw.open.values, "high": np.maximum(raw.high.values, raw[["open", "close"]].max(axis=1).values),
                       "low": np.minimum(raw.low.values, raw[["open", "close"]].min(axis=1).values),
                       "close": raw.close.values, "volume": raw.volume.fillna(0).values, "taker_buy": np.nan},
                      index=pd.DatetimeIndex(pd.to_datetime(np.asarray(day)).tz_localize("UTC"), name="open_time"))
    return df[~df.index.duplicated(keep="last")].sort_index()[data.COLS].astype(float)


def fetch_daily(ticker, path, budget_left=REQUEST_TIMEOUT_S):
    """Daily bars, fetched once (the file is kept: they are only used before the first stored 15m bar).
    -> (bars or None, error or None)."""
    old = _load(path)
    if old is not None and len(old):
        return old, None
    try:
        df = parse_daily(_daily_chart(_ysym(ticker), DAILY_RANGE, _timeout(budget_left)))
    except Exception as e:
        return None, "daily bars did not load (%s)" % type(e).__name__
    if not len(df):
        return None, "no daily bars from the feed"
    data.save("x", df, path=path)
    return df, None


# ------------------------------------------------------------------ readings (the engine's own code)
def _voice_sets():
    """(the S&P model's cards, the ones read on the stock's own bars, the market-wide ones)."""
    from . import evidence
    spx = [v for v in evidence.GROUPS if evidence.voice_applies(v, INDEX)]
    cards = [v for v in spx if v != "cross"]                   # "the other coin": never reads for a market alone
    own = [v for v in cards if v not in SKIP_VOICES and v not in MARKET_VOICES]
    market = [v for v in cards if v in MARKET_VOICES]
    return cards, own, market


def _own_modules(own):
    from . import evidence
    return [m for m in evidence.SOURCES if any(v in own for v in m.GROUPS)]


def evidence_frame(df15, ticker):
    """Every reading the engine makes from one asset's own bars: evidence.build_one, then each source module
    with a card read on the stock's bars (features(index, ticker, bars=df15)). Nothing else is read."""
    from . import evidence
    _, own, _ = _voice_sets()
    ev = evidence.build_one(df15)
    extra = []
    for m in _own_modules(own):
        f = m.features(df15.index, ticker, bars=df15)
        extra.append(f[[c for c in f.columns if c not in ev.columns]])
    if extra:
        add = pd.concat(extra, axis=1)
        add = add.loc[:, ~add.columns.duplicated()]
        ev = pd.concat([ev, add], axis=1)
    ev = ev.copy()
    ev["st_btc120"] = ev["st_sma120"]                          # evidence.build: an asset without BTC reads its own
    return ev


def placeholders(daily, before, two=False):
    """Daily bars before `before` (the first real 15m bar) as 15m rows: one per day at the session's first
    slot, or (two=True) two rows six hours apart that make the very same daily bar. Their daily (and weekly)
    aggregates equal the daily bars; anything finer than a day differs between the two shapes."""
    d = daily[daily.index < before.normalize()] if len(daily) else daily
    if not len(d):
        return d
    summer = d.index + pd.Timedelta(hours=13, minutes=30)         # 09:30 New York in daylight saving time
    first = pd.DatetimeIndex(np.where(extdata.open_mask(SESSION, summer, calendar=False), summer,
                                      summer + pd.Timedelta(hours=1)))
    if not two:
        out = d.copy()
        out.index = first
        return out
    mid = (d["open"] + d["close"]) / 2.0
    a = pd.DataFrame({"open": d["open"].values, "high": d["high"].values, "low": d["low"].values, "close": mid.values,
                      "volume": d["volume"].values / 2.0, "taker_buy": np.nan}, index=first)
    b = pd.DataFrame({"open": mid.values, "high": np.maximum(mid, d["close"]).values, "low": np.minimum(mid, d["close"]).values,
                      "close": d["close"].values, "volume": d["volume"].values / 2.0, "taker_buy": np.nan},
                     index=first + pd.Timedelta(hours=6))
    out = pd.concat([a, b]).sort_index()
    return out[data.COLS]


def _numeric(s):
    return pd.api.types.is_numeric_dtype(s.dtype) or pd.api.types.is_bool_dtype(s.dtype)


def _same(a, b):
    """Element-wise: the two frames agree (NaN with NaN; numbers within 1e-6; text equal)."""
    out = pd.DataFrame(False, index=a.index, columns=a.columns)
    for c in a.columns:
        x, y = a[c], b[c]
        if not (_numeric(x) and _numeric(y)):
            out[c] = ((x.isna() & y.isna()) | (x.astype(object).astype(str) == y.astype(object).astype(str))).values
        else:
            xv, yv = x.values.astype(float), y.values.astype(float)
            both = np.isnan(xv) & np.isnan(yv)
            with np.errstate(invalid="ignore"):
                close = np.abs(xv - yv) <= 1e-6 * (1.0 + np.abs(xv))
            out[c] = both | close
    return out


def readings(df15, daily, ticker):
    """The stock's readings on its own 15m rows (see the module doc): where the readings made with the two
    placeholder shapes agree, that reading; else the reading made on the real 15m bars alone."""
    real = evidence_frame(df15, ticker)
    if daily is None or not len(daily):
        return real
    ph_a, ph_b = placeholders(daily, df15.index[0]), placeholders(daily, df15.index[0], two=True)
    if not len(ph_a):
        return real
    a = evidence_frame(pd.concat([ph_a, df15]), ticker).loc[df15.index]
    b = evidence_frame(pd.concat([ph_b, df15]), ticker).loc[df15.index]
    cols = [c for c in real.columns if c in a.columns and c in b.columns]
    a, b = a[cols], b[cols]
    same = _same(a, b)
    out = real.copy()
    for c in cols:
        keep = same[c].values
        if keep.any():
            col = out[c].astype(float) if _numeric(a[c]) and _numeric(out[c]) else out[c].astype(object)
            col[keep] = np.asarray(a[c].values, dtype=col.dtype)[keep]
            out[c] = col
    return out


def feature_vector(row, spx_data):
    """The model's feature vector for a stock at one close: own cards from `row`, market-wide cards from the
    S&P call's readings (`spx_data`: the journal entry's "data"), everything else 0 (no read)."""
    from .evidence import FEATURES
    _, own, market = _voice_sets()
    x = np.zeros(len(FEATURES))
    pos = dict((f, i) for i, f in enumerate(FEATURES))
    for v in market:
        for f in model.VOICES[v][1]:
            x[pos[f]] = _num((spx_data or {}).get(f)) or 0.0
    for v in own:
        for f in model.VOICES[v][1]:
            val = _num(row.get(f)) if hasattr(row, "get") else None
            x[pos[f]] = 0.0 if val is None else val
    return x


def reading_cards(x):
    """-> (the S&P cards with a read for this stock, all of them)."""
    cards, _, _ = _voice_sets()
    reading = [v for v in cards if model._COLS[v] and np.abs(x[model._COLS[v]]).sum() > 0]
    return reading, cards


# ------------------------------------------------------------------ the index model (read only)
def even_prior(W):
    W = np.array(W, dtype=float, copy=True)
    W[:, 0] = W[:, 0].mean()
    return W


def entry_trust(entry):
    """The trust each voice had in the S&P call (journal entry "voices"), on model.VOICE_NAMES."""
    got = dict((v.get("voice"), _num(v.get("trust"))) for v in (entry or {}).get("voices") or [] if isinstance(v, dict))
    t = np.array([got.get(v) or 0.0 for v in model.VOICE_NAMES])
    return t / t.sum() if t.sum() > 0 else t


def _entry_x(entry):
    from .evidence import FEATURES
    d = (entry or {}).get("data") or {}
    return np.array([_num(d.get(f)) or 0.0 for f in FEATURES])


def match_fit(entry, fits_dir, prefer=None, tol=0.006):
    """The weekly refit the S&P call used: the file in the index group's fits folder whose voices give back
    the entry's own answers (up / down, rounded to 3 decimals there) on the entry's readings. Read only.
    -> (file name, {voice: W after the even prior}) or (None, None)."""
    voices = dict((v.get("voice"), v) for v in (entry or {}).get("voices") or [] if isinstance(v, dict))
    check = [v for v in model.VOICE_NAMES if v in voices and (_num(voices[v].get("trust")) or 0) > 0 and model._COLS[v]]
    if not check or not os.path.isdir(fits_dir):
        return None, None
    x = _entry_x(entry)
    files = [f for f in os.listdir(fits_dir) if f.endswith(".npz") and not f.endswith(".tmp.npz")]
    files.sort(key=lambda f: (f != prefer, -os.path.getmtime(os.path.join(fits_dir, f))))
    for f in files:
        try:
            with np.load(os.path.join(fits_dir, f)) as z:
                W = dict((v, even_prior(z[v])) for v in model.VOICE_NAMES if v in z.files)
        except Exception:
            continue
        if any(v not in W for v in model.VOICE_NAMES):
            continue
        ok = True
        for v in check:
            p = model.predict(W[v], x[model._COLS[v]][None, :])[0]
            if abs(p[labels.UP] - _num(voices[v].get("up"))) > tol or abs(p[labels.DOWN] - _num(voices[v].get("down"))) > tol:
                ok = False
                break
        if ok:
            return f, W
    return None, None


def stance_odds(x, trust, W, cap=None):
    """The engine's mix for one row (leanprep.prepare_live): a voice with no reading has no say, trust
    renormalised over the voices that speak, capped (model.cap_shares), then model.mix.
    -> (odds [neither, up, down], weights, probs (voices, 3))."""
    cap = CFG.get("trust_cap") if cap is None else cap
    probs = np.stack([model.predict(W[v], x[model._COLS[v]][None, :])[0] for v in model.VOICE_NAMES])
    speaks = np.array([bool(model._COLS[v]) and np.abs(x[model._COLS[v]]).sum() > 0 for v in model.VOICE_NAMES])
    w = trust * speaks
    tot = w.sum()
    w = w / tot if tot > 0 else np.array(trust, dtype=float)
    w = model.cap_shares(w[None, :], cap)[0]
    odds = model.mix(probs[None, :, :], w[None, :])[0]
    return odds, w, probs


def index_cfg():
    cfg = dict(CFG, voting=voting_for(GROUP))
    cfg["horizon"] = HORIZON
    return cfg


def decide(odds, shock, tide, bias, guard, cfg=None):
    """policy.decide for a flat book with an empty idle clock: ENTER -> LONG / SHORT, anything else FLAT.
    -> (side, policy reason code)."""
    cfg = cfg or index_cfg()
    act, target, why = policy.decide(0, 0, float(odds[labels.UP]), float(odds[labels.DOWN]), bool(shock),
                                     0.0 if tide is None else float(tide), cfg, bias=int(bias or 0), guard=bool(guard))
    if act == policy.ENTER and target:
        return ("LONG" if target > 0 else "SHORT"), why
    return "FLAT", why


def _title(v):
    t = str(model.VOICES[v][0]).split(" (")[0].split(",")[0].strip()
    if t.lower().startswith("the library's "):
        t = t[len("the library's "):].capitalize()
    return t


def reason(side, score, w, probs, why=None, shock=False, cfg=None):
    """One plain sentence: the two or three cards pulling hardest toward the side, or why it is FLAT."""
    cfg = cfg or index_cfg()
    if side in ("LONG", "SHORT"):
        sg = 1 if side == "LONG" else -1
        pulls = sorted(((float(w[k] * (probs[k, labels.UP] - probs[k, labels.DOWN]) * 100.0), v)
                        for k, v in enumerate(model.VOICE_NAMES)), key=lambda pv: -sg * pv[0])
        names = []
        for p, v in pulls:
            if sg * p < 0.1 or len(names) == 3:
                break
            t = _title(v)
            if t and t not in names and "kronos" not in t.lower() and not EDGE_WORD.search(t):
                names.append(t)
        if names:
            listed = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
            return "Strongest on the %s side: %s." % (side.lower(), listed)
        return "The cards together favour the %s side." % side.lower()
    if why == "release_guard":
        return "A high-impact US release is due within the hour, so no stance is taken into it."
    lean = "long" if score > 0 else "short"
    if why == "no_side_rewarding" or why == "no_side_rewarding_high_risk":
        need = (cfg["theta_enter_shock"] if shock else cfg["theta_enter"]) * 100
        if abs(score) >= need:
            return ("The cards lean %s (%+.1f points) against the trend on every timeframe, short of the %.0f-point "
                    "bar for that." % (lean, score, cfg.get("theta_counter", 0.15) * 100))
        return "No card leans clearly: the combined reading is %+.1f points, inside the %.0f-point bar%s." % (
            score, need, " for high risk" if shock else "")
    return "No card leans clearly."


# ------------------------------------------------------------------ the S&P call's entries
def spx_entries(out=None, journal_dir=None, days=()):
    """{close time "YYYY-MM-DD HH:MM": entry} of the S&P call: this step's entries first, then the journal day
    files of `days` (only the S&P lines are parsed)."""
    got = {}
    for d in days:
        p = os.path.join(journal_dir or JOURNAL_DIR, "%s.jsonl" % d)
        if not os.path.exists(p):
            continue
        try:
            with open(p, encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith('{"asset": "%s"' % INDEX):
                        try:
                            e = json.loads(line)
                        except ValueError:
                            continue
                        got[e.get("time")] = e
        except OSError:
            continue
    for e in out or []:
        if isinstance(e, dict) and e.get("asset") == INDEX and e.get("time"):
            got[e["time"]] = e
    return got


def _close_key(open_ms):
    return pd.Timestamp(int(open_ms) + BAR_MS, unit="ms", tz="UTC").strftime("%Y-%m-%d %H:%M")


# ------------------------------------------------------------------ earnings (stored file only)
def earnings_next(ticker, paths, now):
    """The next earnings day stored by sources/equity_events.py (its megacap list only; never fetched here).
    -> (ISO date "YYYY-MM-DDT00:00:00Z" or None, "before the open" / "after the close" / None)."""
    try:
        e = pd.read_csv(paths.earnings, dtype={"date": str, "symbol": str, "when": str})
    except Exception:
        return None, None
    today = extdata._local(pd.DatetimeIndex([pd.Timestamp(now, unit="s", tz="UTC")]), extdata.NY)[0].strftime("%Y-%m-%d")
    gone = e["gone_ms"] if "gone_ms" in e.columns else pd.Series(np.nan, index=e.index)
    rows = e[(e["symbol"].astype(str).str.upper() == ticker) & (e["date"].astype(str) >= today) & gone.isna()]
    if not len(rows):
        return None, None
    r = rows.sort_values("date").iloc[0]
    when = {"bmo": "before the open", "amc": "after the close"}.get(str(r.get("when") or "").strip().lower())
    return "%sT00:00:00Z" % str(r["date"])[:10], when


# ------------------------------------------------------------------ grading (labels.triple_barrier)
def grade_one(bars, bar_ms, unit, horizon=HORIZON):
    """The engine's grade of a call made at the close of the bar opened at bar_ms: UP / DOWN / NEITHER, or
    UNKNOWN while it is not decided yet (or the bar is not stored)."""
    if unit is None or not unit > 0 or bars is None or not len(bars):
        return labels.UNKNOWN
    ms = data.to_ms(bars.index)
    i = int(np.searchsorted(ms, int(bar_ms)))
    if i >= len(ms) or ms[i] != int(bar_ms):
        return labels.UNKNOWN
    sl = bars.iloc[i:i + horizon + 1]
    have = len(sl)
    pad = np.full(horizon + 1 - have, np.nan)                     # bars not there yet: no touch can happen in them
    o, h, l = (np.concatenate([sl[k].values.astype(float), pad]) for k in ("open", "high", "low"))
    u = np.full(horizon + 1, np.nan)
    u[0] = float(unit)
    y, res = labels.triple_barrier(o, h, l, u, horizon)
    if have < horizon + 1 and int(res[0]) > have - 1:              # decided only by bars that exist
        return labels.UNKNOWN
    return int(y[0])


def read_log(path):
    """The stance log, one row per (ticker, bar) (a repeated line, after a restart, counts once)."""
    rows = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and r.get("ticker") and r.get("bar_ms") is not None:
                    rows.setdefault("%s|%d" % (r["ticker"], int(r["bar_ms"])), r)
    except OSError:
        pass
    return rows


def _record(rows, grades):
    graded = right = neither = 0
    since = None
    for k, r in rows.items():
        t = r.get("bar_ms")
        since = t if since is None else min(since, t)
        if r.get("side") not in ("LONG", "SHORT"):
            continue
        y = grades.get(k)
        if y == labels.NEITHER:
            neither += 1
        elif y in (labels.UP, labels.DOWN):
            graded += 1
            right += int((y == labels.UP) == (r["side"] == "LONG"))
    return {"graded": graded, "hit_pct": None if not graded else round(100.0 * right / graded, 1),
            "neither": neither, "since_utc": None if since is None else _iso(int(since) + BAR_MS)}


def grade_all(paths, state, bars_of):
    """Grade every logged stance whose grade is now known; -> ({ticker: record}, pooled record)."""
    rows = read_log(paths.log)
    grades = state.setdefault("grades", {})
    for k, r in rows.items():
        if k in grades or r.get("side") not in ("LONG", "SHORT"):
            continue
        y = grade_one(bars_of(r["ticker"]), r["bar_ms"], _num(r.get("unit")))
        if y != labels.UNKNOWN:
            grades[k] = y
    per = {}
    for t in sorted(set(r["ticker"] for r in rows.values())):
        per[t] = _record(dict((k, r) for k, r in rows.items() if r["ticker"] == t), grades)
    return per, _record(rows, grades)


# ------------------------------------------------------------------ one ticker
def _stance(ticker, df15, daily, spx, fit, paths, now, cfg):
    """The stance at the stock's last closed bar. -> (stance dict or None, error or None)."""
    ev = readings(df15, daily, ticker)
    row = ev.iloc[-1]
    bar_ms = int(data.to_ms(df15.index[-1:])[0])
    missing = [c for c in REQUIRED if not (isinstance(row.get(c), str) or _num(row.get(c)) is not None)]
    if missing:
        return None, "not enough price history for the model's required readings"
    entry = spx.get(_close_key(bar_ms))
    if entry is None:
        return None, "no S&P 500 reading at this close yet"
    if not entry.get("voices"):
        return None, "the S&P 500 model had no odds at this close"
    trust = entry_trust(entry)
    x = feature_vector(row, entry.get("data"))
    odds, w, probs = stance_odds(x, trust, fit)
    score = float(odds[labels.UP] - odds[labels.DOWN]) * 100.0
    ec = _num((entry.get("data") or {}).get("ec_next"))
    guard = ec is not None and ec >= 1.0 - 1.0 / 24.0 - 1e-9          # evidence.build's release_soon
    shock = bool(row.get("shock")) if row.get("shock") == row.get("shock") else False
    tide, bias = _num(row.get("tide")), _num(row.get("htf_bias"))
    side, why = decide(odds, shock, tide, bias, guard, cfg)
    reading, cards = reading_cards(x)
    unit = _num(row.get("atr1h"))
    return {"bar_ms": bar_ms, "side": side, "score": round(score, 1), "p_up": round(float(odds[labels.UP]), 3),
            "p_down": round(float(odds[labels.DOWN]), 3), "p_neither": round(float(odds[labels.NEITHER]), 3),
            "reason": reason(side, score, w, probs, why, shock, cfg), "policy_reason": why,
            "cards_reading": len(reading), "cards_total": len(cards), "price": float(df15["close"].iloc[-1]),
            "unit": None if unit is None else cfg["barrier_atr"] * unit,
            "made_utc": _iso(int(now * 1000))}, None


# ------------------------------------------------------------------ the run
def run(out=None, paths=None, now=None, fetch=True, log=None, env=None, budget_s=BUDGET_S):
    """One pass: tickers, bars, stances for new closed bars, grading, the file. -> info dict."""
    t0 = time.time()
    say = log or (lambda *_: None)
    paths = paths or Paths()
    now = _now() if now is None else float(now)
    state = load_state(paths)
    tickers, source, as_of = resolve_tickers(state, env)
    market_open = extdata.is_open(SESSION, int(now * 1000))
    last_slot = last_session_bar_ms(now)
    cfg = index_cfg()
    stances = state.setdefault("stances", {})
    logged = state.setdefault("logged", {})
    os.makedirs(paths.stocks, exist_ok=True)
    bars_cache, errors = {}, {}
    needs = set()                                                # days whose S&P journal lines may be needed
    for t in tickers:
        left = budget_s - (time.time() - t0)
        if left <= 2.0:
            errors[t] = "not refreshed this step (time budget)"
            continue
        df = _load(paths.bars15(t))
        stored_to = None if df is None or not len(df) else int(data.to_ms(df.index[-1:])[0])
        if fetch and (stored_to is None or last_slot is None or stored_to < last_slot):
            df, err = fetch_15m(t, paths.bars15(t), now, left, log=say)
            if err:
                errors[t] = err
        elif df is None:
            errors[t] = "no price data stored"
        if df is not None and len(df):
            bars_cache[t] = df
            needs.add(_close_key(int(data.to_ms(df.index[-1:])[0]))[:10])
    spx = spx_entries(out, paths.journal, sorted(needs))
    fit_name, fit = None, None
    for t in tickers:
        df = bars_cache.get(t)
        if df is None or t in errors:
            continue
        bar_ms = int(data.to_ms(df.index[-1:])[0])
        old = stances.get(t)
        if isinstance(old, dict) and old.get("bar_ms") == bar_ms and old.get("side"):
            continue                                             # this close already has its stance
        left = budget_s - (time.time() - t0)
        if left <= 2.0:
            errors[t] = "not refreshed this step (time budget)"
            continue
        daily, derr = (None, None)
        if fetch or os.path.exists(paths.bars1d(t)):
            daily, derr = fetch_daily(t, paths.bars1d(t), left) if fetch else (_load(paths.bars1d(t)), None)
        if fit is None:
            entry = spx.get(_close_key(bar_ms))
            if entry is None:
                errors[t] = "no S&P 500 reading at this close yet"
                continue
            fit_name, fit = match_fit(entry, paths.fits, prefer=(state.get("model") or {}).get("file"))
            if fit is None:
                errors[t] = "the S&P 500 model is not available"
                continue
            state["model"] = {"file": fit_name, "matched_at": entry.get("time")}
        try:
            st, err = _stance(t, df, daily, spx, fit, paths, now, cfg)
        except Exception as e:
            st, err = None, "the readings could not be made (%s)" % type(e).__name__
        if err:
            errors[t] = err
            continue
        if derr:
            st["daily_note"] = derr
        stances[t] = st
        if logged.get(t) != bar_ms:                              # one log line per ticker per new closed bar
            row = dict(ticker=t, bar_ms=bar_ms, as_of_utc=_iso(bar_ms + BAR_MS), side=st["side"], score=st["score"],
                       p_up=st["p_up"], p_down=st["p_down"], unit=st["unit"], price=st["price"], logged_utc=st["made_utc"])
            with open(paths.log, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(_clean(row), allow_nan=False) + "\n")
            logged[t] = bar_ms
        save_state(paths, state)
    per, pooled = grade_all(paths, state, lambda t: bars_cache.get(t) if t in bars_cache else _load(paths.bars15(t)))
    state["last_used"] = {"tickers": tickers, "source": source, "as_of": as_of}
    doc = build(tickers, source, as_of, stances, bars_cache, errors, per, pooled, market_open, now, paths)
    save_state(paths, state)
    info = write(doc, paths.out, log=say)
    info["seconds"] = round(time.time() - t0, 1)
    return info


def build(tickers, source, as_of, stances, bars, errors, per, pooled, market_open, now, paths):
    items = []
    empty = {"graded": 0, "hit_pct": None, "neither": 0, "since_utc": None}
    for t in tickers:
        st = stances.get(t) if isinstance(stances.get(t), dict) else None
        df = bars.get(t)
        last_ms = None if df is None or not len(df) else int(data.to_ms(df.index[-1:])[0])
        err = errors.get(t)
        fresh = st is not None and st.get("bar_ms") == last_ms and err is None
        old = last_ms is not None and now - (last_ms + BAR_MS) / 1000.0 > STALE_S
        earn, earn_when = earnings_next(t, paths, now)
        rec = per.get(t, empty)
        items.append({
            "ticker": t, "side": st["side"] if fresh else None,
            "as_of_utc": _iso(st["bar_ms"] + BAR_MS) if fresh else None, "market_open": bool(market_open),
            "price": _r(df["close"].iloc[-1], 4) if last_ms is not None else None,
            "price_bar_utc": _iso(last_ms + BAR_MS) if last_ms is not None else None,
            "score": _r(st["score"], 1) if fresh else None, "p_up": _r(st["p_up"], 3) if fresh else None,
            "p_down": _r(st["p_down"], 3) if fresh else None, "reason": st["reason"] if fresh else None,
            "cards_reading": st["cards_reading"] if fresh else None, "cards_total": st["cards_total"] if fresh else len(_voice_sets()[0]),
            "record": {"graded": rec["graded"], "hit_pct": rec["hit_pct"], "since_utc": rec["since_utc"]},
            "stale": bool(err is not None or not fresh or (market_open and old)),
            "error": err if err else (None if fresh else "no stance yet for the last close"),
            "earnings_utc": earn, "earnings_session": earn_when})
    return _clean({"generated_utc": _iso(int(now * 1000)), "schema": SCHEMA, "note": NOTE, "model": MODEL,
                   "tickers_as_of_utc": as_of, "tickers_source": source, "market_open": bool(market_open),
                   "stocks": items,
                   "pooled_record": {"graded": pooled["graded"], "hit_pct": pooled["hit_pct"], "since_utc": pooled["since_utc"]}})


def write(doc, out_dir=None, log=None):
    out_dir = out_dir or LIVE_DIR
    text = json.dumps(_clean(doc), allow_nan=False)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, FILE)
    _atomic(path, text)
    web, web_dir = None, (os.environ.get(WEB_ENV) or "").strip()
    if web_dir:
        try:
            _atomic(os.path.join(web_dir, FILE), text, mode=WEB_MODE)
            web = os.path.join(web_dir, FILE)
        except Exception as e:
            try:
                (log or (lambda *_: None))("stocks: web copy not written (%r)" % (e,))
            except Exception:
                pass
    return {"tickers": len(doc["stocks"]), "path": path, "web_path": web}


# ------------------------------------------------------------------ the live step's hook
def maybe_run(out, out_dir=None, data_dir=None, log=None, paths=None, now=None, fetch=True, env=None):
    """live.step's call, after setups.json. Work only when the S&P 500 stepped in this step (a new US cash close)
    or the ticker list changed since the last pass; else nothing: the last file stands, said in the log once there
    has been a pass (before the first pass, None and no line: nothing to say).
    data_dir: the folder of the live state (live.STATE's), so a test's stand-in step never reads the real one."""
    paths = paths or Paths(data_dir=data_dir, out_dir=out_dir)
    spx_new = any(isinstance(e, dict) and e.get("asset") == INDEX for e in (out or []))
    if not spx_new:
        state = load_state(paths)
        if not state:
            return None
        tickers, source, as_of = resolve_tickers(dict(state), env)
        last = state.get("last_used") or {}
        if tickers == last.get("tickers") and source == last.get("source") and as_of == last.get("as_of"):
            return {"skipped": "no new S&P 500 close and the list is unchanged"}
    return run(out, paths=paths, now=now, fetch=fetch, log=log, env=env)


def line(info):
    if info.get("skipped"):
        return "stocks: skipped (%s)" % info["skipped"]
    return "stocks: %d tickers -> %s%s" % (info["tickers"], info["path"],
                                           " (web copy: %s)" % info["web_path"] if info.get("web_path") else "")
