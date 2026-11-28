# -*- coding: utf-8 -*-
"""zh -- Chinese (zh-TW and zh-CN) versions of the English text inside the website's data files.

Owner, 28 Nov 2026: "Ensure all other locale in the website are fully translate", then chose "Automatic" (each new
English sentence is translated once by an AI model and reused) and "Translate them" for the news headlines.

What it does, for one data file X.json (page.json, setups.json, news.json, ...):
  1. walks the JSON and collects every string that shows English words (keys, dates, links and codes are left out);
  2. cuts each string into pieces at "; " and " · " and masks the numbers in each piece ("lead of 6.7 pts" ->
     "lead of [[0]] pts"), so one translated pattern serves every later number;
  3. looks each pattern up in a cache file; patterns never seen are translated by Claude in batches, checked (every
     [[n]] mark kept, no banned word, no empty line) and stored;
  4. writes X.zh.json beside the file: {"schema": 1, "generated_utc", "source_md5", "zh-TW": {english: chinese},
     "zh-CN": {...}} with only the strings whose every piece is translated. The page looks a string up by its exact
     English; a string that is not in the map stays English (the page then shows its usual note line).

Safe by design: no key, no network, a refusal, a bad answer or a spent daily budget only means fewer strings in the map;
the data file itself is never touched, and nothing here runs inside the engine's step.

The file is self-contained (standard library + the anthropic package) so other jobs (the forecast's news, the books)
can copy it unchanged:

    python zh.py file IN.json [OUT.json] --cache CACHE.json [--key-file PATH]

The API key is read at run time from --key-file (default $ZH_KEY_FILE, else /etc/mind15/anthropic.key); it is never
printed or logged.
"""
import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys
import tempfile
import time

LANGS = ("zh-TW", "zh-CN")
MODEL = "claude-opus-5-5"
BATCH = 60                       # patterns per request
MAX_NEW_PER_RUN = 600            # patterns translated in one run at most (the first run of a big file takes a few)
DAY_OUTPUT_TOKENS = 400_000      # stop asking for the rest of the UTC day once this many output tokens are spent
KEY_FILE = os.environ.get("ZH_KEY_FILE", "/etc/mind15/anthropic.key")
BANNED = ("kronos", "\u514b\u7f85\u8afe\u65af", "\u514b\u7f57\u8bfa\u65af", "\u30af\u30ed\u30ce\u30b9")

# keys whose values are never shown as prose (links, ids, times, codes)
SKIP_KEYS = {"url", "link", "href", "id", "uid", "src", "image", "img", "icon", "md5", "sha", "hash", "schema",
             "generated_utc", "as_of", "ts", "time", "t", "utc", "date", "since", "until", "opened", "closed",
             "entry_utc", "exit_utc", "next_open_utc", "sym", "symbol", "ticker", "asset", "code", "why_out",
             "side", "dir", "direction", "status", "kind", "type", "key", "voice_key", "book", "tf", "interval",
             "name", "names", "short_name", "label", "tag", "tags", "source", "sources", "site", "publisher"}
WORD = re.compile(r"[A-Za-z]{2,}")
LOWER_WORD = re.compile(r"\b[a-z]{2,}\b")
ISO = re.compile(r"^\d{4}-\d\d-\d\d([ T]\d\d:\d\d(:\d\d)?(\.\d+)?(Z|[+-]\d\d:?\d\d)?)?$")
URLISH = re.compile(r"^(https?://|/|\./|\.\./)\S*$")
IDENT = re.compile(r"^[A-Za-z0-9]+(?:[_.][A-Za-z0-9]+)+$")          # field and book names: risk_to_all_stops_usd, b_trend30
SEP = re.compile(r"(; | \u00b7 )")
# a number with its sign, currency, thousands, decimals and a short unit glued to it: -1.4%, $108k, 6.7, 15m, 2x, 1R
NUM = re.compile(r"(?<![A-Za-z0-9\[])[-+\u2212]?\$?\d[\d,]*(?:\.\d+)?(?:%|bp|[kKMBxR]|[mhdw](?![A-Za-z]))?(?![\w\]])")
MARK = re.compile(r"\[\[(\d+)\]\]")
# the pages show the model's old name as the brand (the Mind 15 page replaces it in page.json's text before reading it):
# the map's keys are written the same way, so they match what the page holds, and the banned word never reaches the map
OLD_NAME = re.compile("kro" + "nos", re.I)
BRAND = "AlphaPrediction AI"

SYSTEM = """You translate short pieces of English from a trading research website into Traditional Chinese (Taiwan, zh-TW)
and Simplified Chinese (China, zh-CN). The pieces are written by a paper-trading engine (market readings, decisions,
book notes), by research tools, or are news headlines. Readers are traders.

Rules:
- Keep every mark like [[0]], [[1]] exactly once each, unchanged; they stand for numbers that are filled in later.
- Keep tickers, codes and symbols as written (BTC, ETHUSDT, XAUUSD, USD/JPY, SPX, WTI, ATR(14, 15m), RSI, EMA, T02, R, sd).
- Keep product and source names as written: AlphaPrediction AI, Mind 15, Binance, OKX, Bybit, Hyperliquid, CoinDesk,
  Cointelegraph, Bloomberg, Reuters and other publishers.
- Keep "USD" as written, right after its number. "$[[0]] paper book" -> "$[[0]] 模擬帳本" (zh-TW) / "$[[0]] 模拟账本" (zh-CN),
  the amount directly before those words.
- Use the website's own words (zh-TW / zh-CN): "edge" (an advantage claim) and "lead" both = 領先 / 领先
  ("lead of [[0]] pts" -> 領先 [[0]] 點 / 领先 [[0]] 点); "pts" = 點 / 点; "long" = 做多; "short" = 做空;
  "flat" = 空手 / 空仓; "stop" = 停損 / 止损; "trailing stop" = 移動停損 / 移动止损; "target" = 目標 / 目标;
  "take profit" = 止盈; "setup" = 交易設定 / 交易设定.
- Words in capitals that are plain English (HOLD SHORT, ENTER LONG, FLAT, UP, DOWN) are translated, not kept.
- Never add claims, advice, or words that are not in the English. Keep it as short as the English.
- Plain, natural trading Chinese; no explanations, no quotes around the answer.
Answer with every id you were given."""

SCHEMA = {"type": "object", "properties": {"items": {"type": "array", "items": {
    "type": "object", "properties": {"id": {"type": "integer"}, "zh_TW": {"type": "string"}, "zh_CN": {"type": "string"}},
    "required": ["id", "zh_TW", "zh_CN"], "additionalProperties": False}}},
    "required": ["items"], "additionalProperties": False}


# ---------------------------------------------------------------- what gets translated

def wants(s):
    """True for a string a reader sees as English words (not a date, link, code or number)."""
    if not isinstance(s, str):
        return False
    t = s.strip()
    if len(t) < 2 or not WORD.search(t) or ISO.match(t) or URLISH.match(t) or IDENT.match(t):
        return False
    return bool(LOWER_WORD.search(t)) or len(WORD.findall(t)) >= 2 and not re.fullmatch(r"[A-Z0-9/=.&_\-+ ]+", t) \
        or bool(re.fullmatch(r"[A-Z][a-z]+", t))


def collect(doc):
    """Every string worth translating in a parsed JSON document (a set)."""
    out = set()

    def walk(x, key=None):
        if isinstance(x, dict):
            for k, v in x.items():
                if str(k).lower() not in SKIP_KEYS:
                    walk(v, str(k).lower())
        elif isinstance(x, list):
            for v in x:
                walk(v, key)
        elif wants(x):
            out.add(OLD_NAME.sub(BRAND, x))
    walk(doc)
    return out


def pieces(s):
    """[(piece or separator, is_separator)] for one string."""
    return [(p, bool(SEP.fullmatch(p))) for p in SEP.split(s) if p != ""]


def mask(piece):
    """(pattern, numbers): the piece with each number replaced by [[i]]."""
    nums = []

    def sub(m):
        nums.append(m.group(0))
        return "[[%d]]" % (len(nums) - 1)
    return NUM.sub(sub, piece), nums


def unmask(pattern, nums):
    return MARK.sub(lambda m: nums[int(m.group(1))] if int(m.group(1)) < len(nums) else m.group(0), pattern)


PAPER_BOOK = {"zh-TW": "模擬帳本", "zh-CN": "模拟账本"}


def good(en, zh, lang=None):
    """A translation is kept only when it keeps every mark once, is not empty, has Chinese in it (or equals the
    English for a name), and has no banned word. Book money (review of 28 Nov, H3): the Mind 15 page scales "N USD",
    "$N paper book" and "$Nk" by 15, so "USD" must stay as often as in the English, and each "$[[n]] paper book" must
    come back as "$[[n]] 模擬帳本" (zh-TW) / "$[[n]] 模拟账本" (zh-CN)."""
    if not isinstance(zh, str) or not zh.strip():
        return False
    if sorted(MARK.findall(en)) != sorted(MARK.findall(zh)):
        return False
    if en.count("USD") != zh.count("USD"):
        return False
    pb = re.findall(r"\$(\[\[\d+\]\]) paper book", en)
    if pb and lang in PAPER_BOOK:
        if sorted(re.findall(r"\$(\[\[\d+\]\])\s?" + PAPER_BOOK[lang], zh)) != sorted(pb):
            return False
    low = zh.lower()
    if any(b in low for b in BANNED):
        return False
    return bool(re.search(r"[\u3400-\u9fff]", zh)) or zh.strip() == en.strip()


# ---------------------------------------------------------------- cache

def load_cache(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) and isinstance(d.get("t"), dict) else {"t": {}, "spend": {}}
    except (OSError, ValueError):
        return {"t": {}, "spend": {}}


def write_json(path, doc):
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".zh.", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ---------------------------------------------------------------- Claude

def read_key(path=None):
    """The API key from the key file, or None. Never printed."""
    try:
        with open(path or KEY_FILE, encoding="utf-8") as f:
            k = f.read().strip()
        return k or None
    except OSError:
        return None


def make_client(key):
    import anthropic                                   # only needed when there is something to translate
    return anthropic.Anthropic(api_key=key, max_retries=3, timeout=180.0)


def ask(client, patterns):
    """{pattern: (zh_TW, zh_CN)} for one batch (only the answers that pass good()), and output tokens spent."""
    items = [{"id": i, "en": p} for i, p in enumerate(patterns)]
    r = client.beta.messages.create(
        model=MODEL, max_tokens=16000, system=SYSTEM,
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": json.dumps({"items": items}, ensure_ascii=False)}])
    spent = int(getattr(getattr(r, "usage", None), "output_tokens", 0) or 0)
    if getattr(r, "stop_reason", None) in ("refusal", "max_tokens"):
        return {}, spent
    text = next((b.text for b in r.content if getattr(b, "type", "") == "text"), "")
    try:
        got = json.loads(text).get("items", [])
    except ValueError:
        return {}, spent
    out = {}
    for it in got:
        i = it.get("id")
        if isinstance(i, int) and 0 <= i < len(patterns):
            p = patterns[i]
            tw, cn = it.get("zh_TW"), it.get("zh_CN")
            if good(p, tw, "zh-TW") and good(p, cn, "zh-CN"):
                out[p] = (tw.strip(), cn.strip())
    return out, spent


def fill(cache, wanted, client, log=print, now=None):
    """Translate the patterns in `wanted` that the cache lacks (within the run and day limits). Returns how many were
    added. `client` may be None (then nothing is asked)."""
    t = cache.setdefault("t", {})
    spend = cache.setdefault("spend", {})
    day = (now or _dt.datetime.now(_dt.timezone.utc)).strftime("%Y-%m-%d")
    for d in list(spend):
        if d < day:
            del spend[d]
    todo = sorted(p for p in wanted if p not in t)[:MAX_NEW_PER_RUN]
    if not todo or client is None:
        return 0
    added = 0
    for i in range(0, len(todo), BATCH):
        if spend.get(day, 0) >= DAY_OUTPUT_TOKENS:
            log("zh: daily budget spent (%d output tokens); the rest waits for tomorrow" % spend.get(day, 0))
            break
        batch = todo[i:i + BATCH]
        try:
            got, spent = ask(client, batch)
        except Exception as e:                         # network, rate limit, bad request: try again next run
            log("zh: request failed (%s); %d patterns wait for the next run" % (type(e).__name__, len(todo) - i))
            break
        spend[day] = spend.get(day, 0) + spent
        for p, (tw, cn) in got.items():
            t[p] = {"zh-TW": tw, "zh-CN": cn}
            added += 1
    return added


# ---------------------------------------------------------------- maps

def translate(s, cache, lang):
    """The Chinese for one whole string, or None when any piece is missing."""
    t = cache.get("t", {})
    out = []
    for p, is_sep in pieces(s):
        if is_sep:
            out.append("\uff1b" if p == "; " else p)
            continue
        lead = p[:len(p) - len(p.lstrip())]
        trail = p[len(p.rstrip()):]
        core = p.strip()
        if not core:
            out.append(p)
            continue
        if not wants(core):                            # a piece that is only a number, code or name stays as it is
            out.append(p)
            continue
        pat, nums = mask(core)
        hit = t.get(pat)
        if not hit or not hit.get(lang):
            return None
        out.append(lead + unmask(hit[lang], nums) + trail)
    return "".join(out)


def patterns_of(strings):
    want = set()
    for s in strings:
        for p, is_sep in pieces(s):
            core = p.strip()
            if not is_sep and core and wants(core):
                want.add(mask(core)[0])
    return want


def build_map(doc, cache, source_md5=""):
    strings = collect(doc)
    m = {"schema": 1, "generated_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
         "source_md5": source_md5, "strings": len(strings)}
    for lang in LANGS:
        m[lang] = {}
        for s in strings:
            z = translate(s, cache, lang)
            if z is not None:
                m[lang][s] = z
    m["translated"] = len(m[LANGS[0]])
    return m


def zh_path(path):
    root, ext = os.path.splitext(path)
    return root + ".zh" + (ext or ".json")


def run_file(src, out=None, cache_path=None, client=None, log=print):
    """Translate one data file: fill the cache, write the map. Returns (translated, total) or None when the file
    could not be read."""
    try:
        with open(src, "rb") as f:
            raw = f.read()
        doc = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError):
        return None
    cache_path = cache_path or os.path.join(os.path.dirname(os.path.abspath(src)), ".zh_cache.json")
    cache = load_cache(cache_path)
    strings = collect(doc)
    added = fill(cache, patterns_of(strings), client, log=log)
    if added:
        write_json(cache_path, cache)
    m = build_map(doc, cache, hashlib.md5(raw).hexdigest())
    write_json(out or zh_path(src), m)
    return m["translated"], m["strings"]


def main(argv=None):
    ap = argparse.ArgumentParser(description="write the Chinese map (X.zh.json) for a data file")
    ap.add_argument("cmd", choices=["file"])
    ap.add_argument("src")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--cache", required=True)
    ap.add_argument("--key-file")
    a = ap.parse_args(argv)
    key = read_key(a.key_file)
    client = make_client(key) if key else None
    if client is None:
        print("zh: no API key file; the map is written from the cache only")
    t0 = time.time()
    r = run_file(a.src, a.out, a.cache, client)
    if r is None:
        print("zh: could not read %s" % a.src)
        return 1
    print("zh: %s: %d of %d strings in Chinese (%.1fs)" % (os.path.basename(a.src), r[0], r[1], time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
