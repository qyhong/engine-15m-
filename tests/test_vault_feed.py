# -*- coding: utf-8 -*-
"""vault_feed: the BTC/ETH setups book and the exit-only intents to the VIP vault on 127.0.0.1.

    py -3 -m pytest tests/test_vault_feed.py -q

No network beyond 127.0.0.1. A fake vault (its own HMAC, time window, one-time number and body checks, written from
the vault's api.py / API.md, not from vault_feed) serves most tests; the end-to-end test runs the REAL vault code from
its worktree (C:\\tmp\\kronos\\wt-vip-vault), skipped when that worktree or its `cryptography` is missing.
"""
import calendar
import csv
import hashlib
import hmac
import json
import os
import re
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import vault_feed as vf  # noqa: E402

VAULT_WT = r"C:\tmp\kronos\wt-vip-vault"
SECRET = bytes(range(32, 64))
OPENED = "2026-11-18T09:00:00Z"
BOOK_KEYS = {"symbol", "side", "entry", "stop", "target_1", "target_2", "t1_taken", "entry_window_open", "price",
             "rr_now_t2", "opened_utc", "as_of_utc"}


def ep(utc):
    return calendar.timegm(time.strptime(utc, "%Y-%m-%dT%H:%M:%SZ"))


def bar(n):
    """The n-th 15-minute bar close after 10:00 UTC on 18 Nov 2026."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ep("2026-11-18T10:00:00Z") + 900 * n))


def mkt(sym="BTCUSDT", side="LONG", entry=65000.0, stop=64000.0, t1=66000.0, t2=67000.0, price=65203.2,
        t1_taken=False, window=False, opened=OPENED, at=None, rr="auto", **kw):
    """A market entry as setups._market writes it (the keys the feed reads, plus a few it must ignore)."""
    m = {"symbol": sym, "short": sym[:3], "group": "crypto", "side": side, "price": price, "price_bar_utc": at or bar(1),
         "entry": None, "stop": None, "target_1": None, "target_2": None, "t1_taken": False, "opened_utc": None,
         "rr_now_t1": None, "rr_now_t2": None, "entry_window_open": False, "entry_valid_until_utc": None,
         "closes": [1.0, 2.0], "market_open": True, "unrealized_usd": 12.5}
    if side != "FLAT":
        if t1_taken:
            stop = entry                                          # setups.py: after Target 1 the stop is the entry
        m.update(entry=entry, stop=stop, target_1=t1, target_2=t2, t1_taken=t1_taken, opened_utc=opened,
                 entry_window_open=window)
        if rr == "auto" and price is not None:
            sg = 1 if side == "LONG" else -1
            rw, rk = sg * (t2 - price), sg * (price - stop)
            rr = round(rw / rk, 2) if rw > 0 and rk > 0 else None
        m["rr_now_t2"] = rr
    m.update(kw)
    return m


# ------------------------------------------------------------------ a fake vault, written from the vault's api.py
class FakeVault:
    def __init__(self, secret=SECRET):
        self.secret, self.got, self.replies, self.nonces, self.refused = secret, [], [], set(), []
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                return

            def _send(self, status, obj):
                raw = json.dumps(obj).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                why = fake.check(self.path, self.headers, raw)
                if why:
                    fake.refused.append(why)
                    return self._send(404, {"ok": False, "error": "not_found"})
                op, body = self.path[4:], json.loads(raw)
                fake.got.append((op, body))
                st, out = fake.replies.pop(0) if fake.replies else (200, {"ok": True, "accepted": True})
                self._send(st, out)

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.srv.daemon_threads = True
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = "http://127.0.0.1:%d" % self.srv.server_address[1]

    def check(self, path, h, raw):
        """-> None, or why it is refused (the vault answers every refusal the same: 404)."""
        if not re.match(r"^/v1/(submit_book|submit_intent)$", path) or h.get("X-Ait-Caller") != "engine":
            return "path or caller"
        ts, nonce, sig = h.get("X-Ait-Ts") or "", h.get("X-Ait-Nonce") or "", h.get("X-Ait-Sig") or ""
        if not re.match(r"^[0-9]{1,12}\Z", ts) or abs(time.time() - int(ts)) > 30:
            return "time"
        if not re.match(r"^[A-Za-z0-9_-]{16,64}$", nonce) or nonce in self.nonces:
            return "nonce"
        msg = "POST\n%s\n%s\n%s\n%s" % (path, ts, nonce, hashlib.sha256(raw).hexdigest())
        if not hmac.compare_digest(hmac.new(self.secret, msg.encode(), hashlib.sha256).hexdigest(), sig):
            return "signature"
        self.nonces.add(nonce)
        if raw != json.dumps(json.loads(raw), sort_keys=True).encode():
            return "body not canonical"
        body = json.loads(raw)
        if path.endswith("submit_book"):
            if set(body) != {"book"} or set(body["book"]) - BOOK_KEYS:
                return "book fields"
        elif set(body) != {"intent"} or body["intent"].get("action") not in ("close", "reduce", "move_stop"):
            return "intent fields"
        return None

    def ops(self, op):
        return [b for o, b in self.got if o == op]

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


@pytest.fixture
def fake():
    f = FakeVault()
    yield f
    f.close()


class Feed:
    """Steps of the feed in a temp folder: setups.json, the trade files, the state, the secret file."""

    def __init__(self, tmp, url, secret=SECRET):
        self.tmp, self.lines = tmp, []
        self.secret = tmp / "vault_engine_secret"
        self.secret.write_text(secret.hex() + "\n", encoding="ascii")
        self.env = {vf.URL_ENV: url, vf.SECRET_ENV: str(self.secret)}
        self.state = str(tmp / "data" / "vault_feed_state.json")

    def step(self, *markets, now=None, **env):
        p = self.tmp / "setups.json"
        p.write_text(json.dumps({"generated_utc": "2026-11-18T10:17:03Z", "markets": list(markets)}), encoding="utf-8")
        start = len(self.lines)
        syms = ",".join(m["symbol"] for m in markets if m["symbol"] in vf.ALLOWED)      # (the real file has both)
        out = vf.run(str(p), log=self.lines.append, environ=dict(self.env, **dict({vf.SYMBOLS_ENV: syms}, **env)),
                     state_path=self.state,
                     now=time.time() if now is None else now)
        self.new = self.lines[start:]
        return out

    def trade(self, sym, why, p_out, side=1, p_in=65000.0, stop0=64000.0, t1=66000.0, t2=67000.0, opened=OPENED):
        path = self.tmp / ("shadow_trades_b_targets_%s.csv" % sym)
        cols = ["t_in_ms", "t_out_ms", "side", "p_in", "p_out", "why_in", "why_out", "pnl_pct", "equity", "qty",
                "pnl_usd", "fees_usd", "stop0", "risk_usd", "r_mult", "target_1", "target_2", "time_in", "time_out"]
        new = not path.exists()
        with open(path, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(cols)
            w.writerow([ep(opened) * 1000, ep(opened) * 1000 + 3600000, side, p_in, p_out, "ENTER", why, 1.0, 10100,
                        0.1, 100, 2, stop0, 100, 1.0, t1, t2, "x", "y"])

    def saved(self):
        with open(self.state, encoding="utf-8") as fh:
            return json.load(fh)


@pytest.fixture
def feed(tmp_path, fake):
    return Feed(tmp_path, fake.url)


# ------------------------------------------------------------------ the book body
def test_long_book_decimal_strings_and_real_booleans():
    body, why = vf.build_book(mkt(price=65203.200000001), bar(1))
    assert why is None
    assert body == {"book": {"symbol": "BTCUSDT", "side": "LONG", "entry": "65000", "stop": "64000", "target_1": "66000",
                             "target_2": "67000", "price": "65203.2", "t1_taken": False, "entry_window_open": False,
                             "opened_utc": OPENED, "as_of_utc": bar(1), "rr_now_t2": "1.49"}}
    assert body["book"]["t1_taken"] is False and body["book"]["entry_window_open"] is False


def test_short_book_and_window_flag():
    body, _ = vf.build_book(mkt("ETHUSDT", "SHORT", entry=3100.55, stop=3180.0, t1=3020.1, t2=2950.0, price=3098.0,
                                window=True), bar(2))
    assert body == {"book": {"symbol": "ETHUSDT", "side": "SHORT", "entry": "3100.55", "stop": "3180", "target_1": "3020.1",
                             "target_2": "2950", "price": "3098", "t1_taken": False, "entry_window_open": True,
                             "opened_utc": OPENED, "as_of_utc": bar(2), "rr_now_t2": "1.8"}}


def test_flat_book_carries_no_levels():
    body, _ = vf.build_book(mkt(side="FLAT", price=65100.0), bar(3))
    assert body == {"book": {"symbol": "BTCUSDT", "side": "FLAT", "price": "65100", "t1_taken": False,
                             "entry_window_open": False, "as_of_utc": bar(3)}}


def test_t1_taken_flag_passes_when_levels_are_in_order():
    m = mkt(price=66100.0)
    m["t1_taken"] = True                                           # (a book whose stop stayed below the entry)
    body, _ = vf.build_book(m, bar(1))
    assert body["book"]["t1_taken"] is True


def test_decimal_text():
    assert vf.dec_text(65203.200000001) == "65203.2" and vf.dec_text(3020.1) == "3020.1"
    assert vf.dec_text(812.12345) == "812.123" and vf.dec_text(1.234567) == "1.23457" and vf.dec_text(70000) == "70000"
    for bad in (None, True, 0, -1, float("nan"), float("inf"), "x"):
        assert vf.dec_text(bad) is None


def test_rr_sent_only_when_the_vault_would_agree():
    assert vf.build_book(mkt(rr=1.49), bar(1))[0]["book"]["rr_now_t2"] == "1.49"
    assert "rr_now_t2" not in vf.build_book(mkt(rr=3.0), bar(1))[0]["book"]       # disagrees: left out, book still sent
    assert vf.build_book(mkt(price=67100.0, rr=None), bar(1))[0]["book"]["rr_now_t2"] is None   # past target 2


def test_levels_out_of_order_or_missing_are_not_sent():
    assert vf.build_book(mkt(stop=65500.0), bar(1)) == (None, "levels out of order")
    assert vf.build_book(mkt("ETHUSDT", "SHORT", entry=3000.0, stop=2900.0, t1=2950.0, t2=2900.0, price=3000.0),
                         bar(1)) == (None, "levels out of order")
    after_t1 = vf.build_book(mkt(t1_taken=True), bar(1))[0]["book"]        # stop == entry after T1: sent (vault a88253e)
    assert after_t1["t1_taken"] is True and after_t1["stop"] == after_t1["entry"]
    assert vf.build_book(mkt(t1_taken=False, stop=65000.0), bar(1)) == (None, "levels out of order")   # not without T1
    assert vf.build_book(mkt(target_2=None), bar(1)) == (None, "levels missing (target_2)")
    assert vf.build_book(mkt(price=None), bar(1)) == (None, "no price")
    assert vf.build_book(mkt(), None) == (None, "no price bar time")
    assert vf.build_book(mkt(t1_taken="yes"), bar(1))[1] == "bad t1_taken"


def test_a_bad_market_is_one_line_and_the_other_still_goes(feed, fake):
    feed.step(mkt(stop=65500.0), mkt("ETHUSDT", entry=3000.0, stop=2900.0, t1=3100.0, t2=3200.0, price=3010.0))
    assert feed.new == ["vault: BTCUSDT not sent (levels out of order)", "vault: ETHUSDT LONG sent (as_of %s)" % bar(1)]
    assert [b["book"]["symbol"] for b in fake.ops("submit_book")] == ["ETHUSDT"]


# ------------------------------------------------------------------ scope, change detection, as_of
def test_only_btc_and_eth(feed, fake):
    xau = mkt("XAUUSD", entry=2600.0, stop=2590.0, t1=2610.0, t2=2620.0, price=2601.0)
    feed.step(mkt(), mkt("ETHUSDT", side="FLAT", price=3000.0), xau, **{vf.SYMBOLS_ENV: "XAUUSD, btcusdt ,SPX,ETHUSDT"})
    assert sorted(b["book"]["symbol"] for b in fake.ops("submit_book")) == ["BTCUSDT", "ETHUSDT"]
    assert feed.step(mkt(at=bar(2)), xau, **{vf.SYMBOLS_ENV: "XAUUSD"}) == {"books": [], "intents": []}
    assert len(fake.got) == 2 and feed.new == []
    feed.step(mkt(at=bar(3)), xau, **{vf.SYMBOLS_ENV: "BTCUSDT"})
    assert len(fake.got) == 3 and fake.got[-1][1]["book"]["symbol"] == "BTCUSDT"


def test_unchanged_is_not_resent_and_the_heartbeat_keeps_it_fresh(feed, fake):
    flat = dict(side="FLAT", price=65000.0)
    feed.step(mkt(**flat))
    feed.step(mkt(**flat))                                         # the same step again: nothing
    assert len(fake.got) == 1 and feed.new == []
    feed.step(mkt(at=bar(2), **flat))                              # a new bar, nothing else changed: the heartbeat
    assert [b["book"]["as_of_utc"] for b in fake.ops("submit_book")] == [bar(1), bar(2)]
    feed.step(mkt(at=bar(2), side="FLAT", price=65010.0))          # another body under the same as_of: never sent
    assert feed.new == ["vault: BTCUSDT not sent (same as_of, different body)"] and len(fake.got) == 2
    feed.step(mkt(at=bar(1), **flat))
    assert feed.new == ["vault: BTCUSDT not sent (as_of older than the last sent)"] and len(fake.got) == 2
    feed.step(mkt(at=bar(3)))                                      # it opened: sent
    assert fake.got[-1][1]["book"]["side"] == "LONG"
    st = feed.saved()["book"]["BTCUSDT"]
    assert st["as_of"] == bar(3) and len(st["content"]) == 64


def test_a_refused_book_is_logged_with_the_vault_code_and_resent_next_bar(feed, fake):
    fake.replies = [(400, {"ok": False, "error": "bad_request", "field": "stop"}), (409, {"ok": False, "error": "book_stale"})]
    feed.step(mkt())
    assert feed.new == ["vault: BTCUSDT not sent (refused 400 bad_request field=stop)"]
    feed.step(mkt(at=bar(2)))
    assert feed.new == ["vault: BTCUSDT not sent (refused 409 book_stale)"]
    fake.replies = [(500, {"ok": False, "error": "internal"})]
    feed.step(mkt(at=bar(3)))
    assert feed.new == ["vault: BTCUSDT not sent (vault error 500 internal)"]
    feed.step(mkt(at=bar(3)))
    assert feed.new == ["vault: BTCUSDT LONG sent (as_of %s)" % bar(3)]


# ------------------------------------------------------------------ configuration and failures
def test_off_without_url(tmp_path):
    lines = []
    assert vf.run(str(tmp_path / "nothing.json"), log=lines.append, environ={}) is None
    assert lines == [] and not list(tmp_path.iterdir())


@pytest.mark.parametrize("url", ["http://localhost:8443", "http://10.0.0.5:8443", "https://127.0.0.1:8443",
                                 "http://127.0.0.1", "http://127.0.0.1:8443/v1/x", "http://u:p@127.0.0.1:8443",
                                 "http://127.0.0.1.evil.test:80", "ftp://127.0.0.1:21", "garbage"])
def test_only_127_0_0_1_is_ever_called(tmp_path, fake, url):
    f = Feed(tmp_path, url)
    f.step(mkt())
    assert len(f.new) == 1 and f.new[0].startswith("vault: BTCUSDT not sent (vault url not allowed") and not fake.got
    assert vf.check_url(fake.url) == (fake.url, None) and vf.check_url(fake.url + "/")[0] == fake.url


def test_secret_file_missing_or_unreadable(tmp_path, fake):
    f = Feed(tmp_path, fake.url)
    f.step(mkt(), **{vf.SECRET_ENV: str(tmp_path / "missing")})
    assert f.new == ["vault: BTCUSDT not sent (secret file unreadable)"]
    f.secret.write_text("not hex at all", encoding="ascii")
    f.step(mkt())
    assert f.new == ["vault: BTCUSDT not sent (secret file unreadable)"]
    f.secret.write_text("ab" * 16, encoding="ascii")              # 16 bytes: too short for the vault
    f.step(mkt())
    f.step(mkt(), **{vf.SECRET_ENV: ""})
    assert f.new == ["vault: BTCUSDT not sent (secret file not set)"]
    assert not fake.got and SECRET.hex() not in " ".join(f.lines)
    f.secret.write_text(SECRET.hex(), encoding="ascii")
    f.step(mkt())
    assert f.new == ["vault: BTCUSDT LONG sent (as_of %s)" % bar(1)]


def test_a_wrong_secret_is_the_vaults_404(tmp_path, fake):
    f = Feed(tmp_path, fake.url, secret=b"\x01" * 32)
    f.step(mkt())
    assert f.new == ["vault: BTCUSDT not sent (refused 404 not_found)"] and fake.refused == ["signature"]


def test_vault_down_connection_refused(tmp_path):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()                                                     # nothing listens there now
    f = Feed(tmp_path, "http://127.0.0.1:%d" % port)
    f.step(mkt())
    assert f.new == ["vault: BTCUSDT not sent (vault down: connection refused)"]


def test_vault_down_timeout(tmp_path, monkeypatch):
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(5)                                                 # accepts, never answers
    monkeypatch.setattr(vf, "TIMEOUT_S", 0.4)
    try:
        f = Feed(tmp_path, "http://127.0.0.1:%d" % srv.getsockname()[1])
        t0 = time.time()
        f.step(mkt(), mkt("ETHUSDT", side="FLAT", price=3000.0))
        assert time.time() - t0 < 3
        assert f.new == ["vault: BTCUSDT not sent (vault down: timeout)", "vault: ETHUSDT not sent (vault down: timeout)"]
    finally:
        srv.close()


def test_never_raises(tmp_path, fake, monkeypatch):
    f = Feed(tmp_path, fake.url)
    monkeypatch.setattr(vf, "build_book", lambda *a: 1 / 0)
    assert f.step(mkt()) == {"books": [], "intents": []}
    assert f.new == ["vault: not sent (ZeroDivisionError)"]
    (tmp_path / "setups.json").write_text("{not json", encoding="utf-8")
    lines = []
    vf.run(str(tmp_path / "setups.json"), log=lines.append, environ=f.env, state_path=f.state)
    assert lines == ["vault: BTCUSDT,ETHUSDT not sent (setups.json unreadable)"]


def test_the_step_goes_on_when_the_vault_is_down(tmp_path, monkeypatch):
    """live.step with the feed switched on and every socket closed: one vault line, the push and the rest unchanged."""
    import test_step_timing as tst
    from engine15 import live, setups
    calls, lines = [], []
    tst._stand_ins(monkeypatch, tmp_path, calls)                 # (socket.socket raises: no network at all)
    sp = tmp_path / "setups.json"
    sp.write_text(json.dumps({"markets": [mkt()]}), encoding="utf-8")
    monkeypatch.setattr(setups, "write", lambda page, **k: {"markets": 1, "path": str(sp), "web_path": None})
    sec = tmp_path / "s"
    sec.write_text(SECRET.hex(), encoding="ascii")
    monkeypatch.setenv(vf.URL_ENV, "http://127.0.0.1:9")
    monkeypatch.setenv(vf.SECRET_ENV, str(sec))
    monkeypatch.setenv(vf.SYMBOLS_ENV, "BTCUSDT")
    monkeypatch.setattr(vf, "STATE_PATH", str(tmp_path / "vault_feed_state.json"))
    out = live.step(log=lines.append, fetch=True)
    assert out == [{"asset": "AAA"}, {"asset": "BBB"}]
    vault = [x for x in lines if x.startswith("vault:")]
    assert len(vault) == 1 and vault[0].startswith("vault: BTCUSDT not sent (vault down: "), vault
    assert "web push: ok (a stand-in, nothing sent)" in lines and lines[-1].startswith("step done in ")
    assert "push" in calls                                         # (the vault lap is under 0.05 s: not listed)


# ------------------------------------------------------------------ the signature is the vault's own
def _vault_api():
    if not os.path.isdir(os.path.join(VAULT_WT, "vault", "server", "aitvault")):
        pytest.skip("the vault worktree is not here")
    sys.dont_write_bytecode = True                                # nothing written into the vault's worktree
    sys.path.insert(0, os.path.join(VAULT_WT, "vault", "server"))
    sys.path.insert(0, os.path.join(VAULT_WT, "vault", "tests"))
    try:
        from aitvault import api
    except ImportError as e:
        pytest.skip("the vault code cannot be imported here (%s)" % e)
    return api


def test_signature_equals_the_vault_client():
    api = _vault_api()
    path, raw = "/v1/submit_book", vf.encode({"book": {"symbol": "BTCUSDT", "side": "FLAT", "as_of_utc": bar(1)}})
    client = api.VaultClient("engine", SECRET, host="127.0.0.1", port=1, clock=lambda: 1795000000.7)
    theirs = client.headers(path, raw)
    mine = vf.headers(SECRET, path, raw, ts=theirs["X-Ait-Ts"], nonce=theirs["X-Ait-Nonce"])
    assert mine == theirs
    for args in ((SECRET, "POST", "/v1/submit_intent", "1", "n" * 16, b"{}"), (b"k" * 40, "POST", "/v1/x", 2, "a" * 64, b"")):
        assert vf.body_sig(*args) == api.body_sig(*args)
    assert vf.encode({"b": 1, "a": [True, None]}) == json.dumps({"b": 1, "a": [True, None]}, sort_keys=True).encode()
    h = vf.headers(SECRET, path, raw)
    assert re.match(api.NONCE_RE.pattern, h["X-Ait-Nonce"]) and abs(int(h["X-Ait-Ts"]) - time.time()) < 5


# ------------------------------------------------------------------ the exits
def test_target_1_on_a_long_reduce_both_and_stop_to_entry_on_futures(feed, fake):
    feed.step(mkt())                                               # first sight: no history is acted on
    assert not fake.ops("submit_intent")
    feed.step(mkt(at=bar(2), t1_taken=True, price=66080.5))
    its = [b["intent"] for b in fake.ops("submit_intent")]
    assert its == [
        {"intent_id": "BTCUSDT.20261118T090000Z.reduce.spot", "market": "spot", "symbol": "BTCUSDT", "action": "reduce",
         "fraction": 0.5, "reference_price": "66000"},
        {"intent_id": "BTCUSDT.20261118T090000Z.reduce.futures", "market": "futures", "symbol": "BTCUSDT",
         "action": "reduce", "fraction": 0.5, "reference_price": "66000"},
        {"intent_id": "BTCUSDT.20261118T090000Z.move_stop.futures", "market": "futures", "symbol": "BTCUSDT",
         "action": "move_stop", "side": "BUY", "stop_price": "65000", "reference_price": "66080.5"}]
    assert feed.new[:3] == ["vault: BTCUSDT reduce spot sent (id BTCUSDT.20261118T090000Z.reduce.spot)",
                            "vault: BTCUSDT reduce futures sent (id BTCUSDT.20261118T090000Z.reduce.futures)",
                            "vault: BTCUSDT move_stop futures sent (id BTCUSDT.20261118T090000Z.move_stop.futures)"]
    assert feed.new[3].startswith("vault: BTCUSDT LONG sent") and len(fake.ops("submit_book")) == 2   # the T1 book goes too
    feed.step(mkt(at=bar(3), t1_taken=True, price=66200.0))        # once only
    assert len(fake.ops("submit_intent")) == 3


def test_target_1_on_a_short_futures_only(feed, fake):
    eth = dict(sym="ETHUSDT", side="SHORT", entry=3000.0, stop=3100.0, t1=2900.0, t2=2800.0)
    feed.step(mkt(price=2990.0, **eth))
    feed.step(mkt(price=2895.0, t1_taken=True, at=bar(2), **eth))
    its = [b["intent"] for b in fake.ops("submit_intent")]
    assert [(i["action"], i["market"]) for i in its] == [("reduce", "futures"), ("move_stop", "futures")]
    assert its[1]["side"] == "SELL" and its[1]["stop_price"] == "3000" and its[1]["reference_price"] == "2895"


def test_target_1_with_the_price_back_through_the_entry_closes_futures(feed, fake):
    feed.step(mkt())
    feed.step(mkt(at=bar(2), t1_taken=True, price=64990.0))
    its = [b["intent"] for b in fake.ops("submit_intent")]
    assert [(i["action"], i["market"]) for i in its] == [("reduce", "spot"), ("close", "futures")]
    assert its[0]["reference_price"] == "64990"                    # T1 is 1.5% off the price now: the price now
    assert its[1] == {"intent_id": "BTCUSDT.20261118T090000Z.close.futures", "market": "futures", "symbol": "BTCUSDT",
                      "action": "close", "reference_price": "64990"}
    feed.trade("BTCUSDT", "T1+STOP_BE", 65500.0)                   # then the book's stop at the entry: the spot rest
    feed.step(mkt(side="FLAT", price=64950.0, at=bar(3)))
    its = [b["intent"] for b in fake.ops("submit_intent")]
    assert [(i["action"], i["market"]) for i in its[2:]] == [("close", "spot")]     # the futures close was already sent


@pytest.mark.parametrize("why,p_out,now,ref", [
    ("STOP", 63990.5, 64010.0, "63990.5"),              # stopped: the fill
    ("T1+T2", 66480.0, 66990.0, "67000"),               # target 2 (p_out is the average of both parts)
    ("T1+STOP_BE", 65500.0, 64980.0, "65000"),          # stopped at the entry after target 1
    ("STEP_ASIDE", 65410.0, 65420.0, "65410"),          # the model's own exit
    ("T1+FLIP_MKT", 65800.0, 65555.5, "65555.5"),       # a flip after target 1: the price now
    ("STOP", 63990.5, 66000.0, "66000"),                # an exit price more than 1.5% from the price now: the price now
])
def test_each_exit_kind_closes_spot_and_futures_once(feed, fake, why, p_out, now, ref):
    feed.step(mkt())
    feed.trade("BTCUSDT", why, p_out)
    feed.step(mkt(side="FLAT", price=now, at=bar(2)))
    its = [b["intent"] for b in fake.ops("submit_intent")]
    assert its == [{"intent_id": "BTCUSDT.20261118T090000Z.close.%s" % m, "market": m, "symbol": "BTCUSDT",
                    "action": "close", "reference_price": ref} for m in ("spot", "futures")]
    assert fake.ops("submit_book")[-1]["book"]["side"] == "FLAT"
    feed.step(mkt(side="FLAT", price=now, at=bar(3)))
    assert len(fake.ops("submit_intent")) == 2


def test_an_exit_that_cannot_be_priced_holds_that_markets_book_too(feed, fake):
    feed.step(mkt())
    feed.step(mkt(side="FLAT", price=None, at=bar(2)))            # no trade row and no price: no reference for the close
    assert feed.new == ["vault: BTCUSDT not sent (exit not queued: no reference price for the exit)"]
    assert len(fake.got) == 1 and feed.saved()["pos"]["BTCUSDT"]["opened_utc"] == OPENED
    feed.step(mkt(side="FLAT", price=64500.0, at=bar(3)))          # the next step closes it, then the FLAT book
    assert [(o, b["intent"]["action"] if o == "submit_intent" else b["book"]["side"]) for o, b in fake.got[1:]] == [
        ("submit_intent", "close"), ("submit_intent", "close"), ("submit_book", "FLAT")]


def test_close_without_a_trade_row_uses_the_price_now(feed, fake):
    feed.step(mkt())
    feed.step(mkt(side="FLAT", price=64321.0, at=bar(2)))
    assert [b["intent"]["reference_price"] for b in fake.ops("submit_intent")] == ["64321", "64321"]


def test_flip_closes_the_old_side_and_the_new_side_comes_by_the_book(feed, fake):
    feed.step(mkt())
    feed.trade("BTCUSDT", "FLIP_MKT", 65300.0)
    short = mkt(side="SHORT", entry=65300.0, stop=66300.0, t1=64300.0, t2=63300.0, price=65290.0,
                opened="2026-11-18T10:15:00Z", at=bar(2))
    feed.step(short)
    its = [b["intent"] for b in fake.ops("submit_intent")]
    assert [(i["action"], i["market"], i["reference_price"]) for i in its] == [("close", "spot", "65300"),
                                                                                ("close", "futures", "65300")]
    assert fake.ops("submit_book")[-1]["book"]["side"] == "SHORT"
    feed.trade("BTCUSDT", "STOP", 66310.0, side=-1, p_in=65300.0, opened="2026-11-18T10:15:00Z")
    feed.step(mkt(side="FLAT", price=66320.0, at=bar(3)))          # a short closing: futures only, never spot
    its = [b["intent"] for b in fake.ops("submit_intent")]
    assert [(i["intent_id"], i["reference_price"]) for i in its[2:]] == [("BTCUSDT.20261118T101500Z.close.futures", "66310")]


def test_exits_are_retried_until_the_vault_answers(feed, fake):
    feed.step(mkt())
    fake.replies = [(503, {"ok": False, "error": "busy"})] * 3
    feed.step(mkt(at=bar(2), t1_taken=True, price=66080.5))
    assert len(fake.ops("submit_intent")) == 3 and [i["status"] for i in feed.saved()["intents"].values()] == ["pending"] * 3
    feed.step(mkt(at=bar(3), t1_taken=True, price=66400.0))        # the same bodies again (the price now is not rebuilt)
    its = [b["intent"] for b in fake.ops("submit_intent")]
    assert its[3:] == its[:3] and [i["status"] for i in feed.saved()["intents"].values()] == ["sent"] * 3
    feed.step(mkt(at=bar(4), t1_taken=True, price=66400.0))
    assert len(fake.ops("submit_intent")) == 6


def test_exits_queued_while_the_secret_is_unreadable_go_later(feed, fake):
    feed.step(mkt(), **{vf.SECRET_ENV: "/nope"})
    feed.step(mkt(side="FLAT", price=64000.0, at=bar(2)), **{vf.SECRET_ENV: "/nope"})
    assert not fake.got
    feed.step(mkt(side="FLAT", price=64100.0, at=bar(3)))
    assert [b["intent"]["reference_price"] for b in fake.ops("submit_intent")] == ["64000", "64000"]


def test_a_refused_exit_is_not_retried_and_a_stuck_one_is_given_up(feed, fake):
    feed.step(mkt())
    fake.replies = [(409, {"ok": False, "error": "intent_conflict"}), (400, {"ok": False, "error": "not_allowed",
                                                                              "why": "symbol not on the owner's list"})]
    feed.step(mkt(side="FLAT", price=64000.0, at=bar(2)))
    assert feed.new[:2] == ["vault: BTCUSDT close spot not sent (refused 409 intent_conflict)",
                            "vault: BTCUSDT close futures not sent (refused 400 not_allowed why=symbol not on the owner's list)"]
    feed.step(mkt(side="FLAT", price=64000.0, at=bar(3)))
    assert len(fake.ops("submit_intent")) == 2
    eth = dict(sym="ETHUSDT", entry=3000.0, stop=2900.0, t1=3100.0, t2=3200.0)
    t = time.time()
    feed.step(mkt(price=3010.0, **eth), now=t, **{vf.SECRET_ENV: "/nope"})
    feed.step(mkt(side="FLAT", price=2950.0, at=bar(2), **eth), now=t, **{vf.SECRET_ENV: "/nope"})
    feed.step(mkt(side="FLAT", price=2950.0, at=bar(3), **eth), now=t + 86401)
    assert "vault: ETHUSDT close spot not sent (given up after 24 h)" in feed.new
    assert not [b for b in fake.ops("submit_intent") if b["intent"]["symbol"] == "ETHUSDT"]


def test_ids_are_stable_and_never_the_vaults_own_and_open_never_goes(feed, fake):
    assert vf.intent_id("ETHUSDT", OPENED, "close", "futures") == "ETHUSDT.20261118T090000Z.close.futures"
    pos = {"side": "LONG", "opened_utc": OPENED, "entry": "65000", "target_1": "66000", "t1_taken": False}
    a, b = vf.t1_intents("BTCUSDT", pos, "66010"), vf.t1_intents("BTCUSDT", pos, "66010")
    assert a == b and all(vf.intent_ok(x) and not x["intent_id"].startswith(("join-", "k3-")) for x in a)
    assert all(re.match(r"^[A-Za-z0-9_.:-]{1,64}$", x["intent_id"]) for x in a)
    good = a[0]
    assert not vf.intent_ok(dict(good, action="open", side="BUY", size_pct=10))
    assert not vf.intent_ok(dict(good, intent_id="join-1")) and not vf.intent_ok(dict(good, intent_id="k3-x"))
    assert not vf.intent_ok(dict(good, symbol="XAUUSD")) and not vf.intent_ok(dict(good, size_pct=10))
    assert not vf.intent_ok(dict(a[2], market="spot"))            # move_stop: futures only
    assert vf.ACTIONS == ("close", "reduce", "move_stop")
    # a queued body tampered into an "open" in the state file is refused, never sent
    feed.step(mkt())
    st = feed.saved()
    st["intents"]["x"] = {"body": dict(good, action="open"), "status": "pending", "made": time.time(), "seq": 1}
    with open(feed.state, "w", encoding="utf-8") as fh:
        json.dump(st, fh)
    feed.step(mkt(at=bar(2)))
    assert "vault: BTCUSDT open spot not sent (not an allowed exit)" in feed.new
    assert all(b["intent"]["action"] != "open" for b in fake.ops("submit_intent"))


def test_state_file_is_written_atomically(feed):
    feed.step(mkt())
    st = feed.saved()
    assert set(st) >= {"book", "pos", "intents"} and st["pos"]["BTCUSDT"]["opened_utc"] == OPENED
    assert not os.path.exists(feed.state + ".tmp")


# ------------------------------------------------------------------ end to end: the REAL vault code
def test_end_to_end_against_the_real_vault(tmp_path):
    api = _vault_api()
    try:
        from fakes import Rig
        from aitvault.vault import dispatch  # noqa: F401
    except ImportError as e:
        pytest.skip("the vault test rig cannot be imported here (%s)" % e)
    rig = Rig()
    sec = tmp_path / "engine.secret"
    sec.write_text(SECRET.hex() + "\n", encoding="ascii")          # the format the vault's Callers.from_config reads
    callers = api.Callers.from_config({"engine": {"secret_file": str(sec), "ips": ["127.0.0.1"]}})
    srv = api.serve_tcp(rig.vault, api.Authenticator(callers, rig.store, clock=time.time), "127.0.0.1", 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        f = Feed(tmp_path, "http://127.0.0.1:%d" % srv.server_address[1])
        now = time.time()
        t = [time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(now) // 900 * 900 - 900 * (4 - i))) for i in range(5)]
        opened = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ep(t[0]) - 3600))

        def at(i):
            rig.clock.t = ep(t[i]) + 60                           # the vault's clock: a minute after the bar closed
            return t[i]

        btc = dict(entry=65000.0, stop=64000.0, t1=66000.0, t2=67000.0, opened=opened)
        eth = dict(sym="ETHUSDT", side="SHORT", entry=3000.0, stop=3100.0, t1=2900.0, t2=2800.0, opened=opened)

        def held(sym):
            r = rig.store.one("SELECT body FROM book WHERE symbol = ?", (sym,))
            return json.loads(r[0]) if r else None

        f.step(mkt(price=65203.2, at=at(0), **btc), mkt(price=2990.0, at=at(0), **eth), now=now)
        assert f.new == ["vault: BTCUSDT LONG sent (as_of %s)" % t[0], "vault: ETHUSDT SHORT sent (as_of %s)" % t[0]]
        assert held("BTCUSDT") == {"symbol": "BTCUSDT", "side": "LONG", "entry": "65000", "stop": "64000",
                                   "target_1": "66000", "target_2": "67000", "price": "65203.2", "t1_taken": False,
                                   "entry_window_open": False, "opened_utc": opened, "as_of_utc": t[0], "rr_now_t2": "1.49"}
        f.step(mkt(price=65203.2, at=at(0), **btc), mkt(price=2990.0, at=at(0), **eth), now=now)
        assert f.new == []                                         # unchanged: nothing sent
        os.remove(f.state)                                         # a lost state: the same as_of again is the vault's duplicate
        f.step(mkt(price=65203.2, at=at(0), **btc), mkt(price=2990.0, at=at(0), **eth), now=now)
        assert f.new == ["vault: BTCUSDT LONG sent (as_of %s, duplicate)" % t[0],
                         "vault: ETHUSDT SHORT sent (as_of %s, duplicate)" % t[0]]
        # target 1 on both: reduce (+ spot for the long) and the stop to the entry on futures; the books after T1 go too
        f.step(mkt(price=66080.5, t1_taken=True, at=at(1), **btc), mkt(price=2895.0, t1_taken=True, at=at(1), **eth), now=now)
        rows = dict((r["id"], json.loads(r["body"])) for r in rig.store.q("SELECT id, body FROM intents"))
        assert rows == {
            "BTCUSDT.%s.reduce.spot" % opened.replace("-", "").replace(":", ""):
                {"intent_id": "BTCUSDT.%s.reduce.spot" % opened.replace("-", "").replace(":", ""), "market": "spot",
                 "symbol": "BTCUSDT", "action": "reduce", "fraction": 0.5, "reference_price": "66000"},
            "BTCUSDT.%s.reduce.futures" % opened.replace("-", "").replace(":", ""):
                {"intent_id": "BTCUSDT.%s.reduce.futures" % opened.replace("-", "").replace(":", ""), "market": "futures",
                 "symbol": "BTCUSDT", "action": "reduce", "fraction": 0.5, "reference_price": "66000"},
            "BTCUSDT.%s.move_stop.futures" % opened.replace("-", "").replace(":", ""):
                {"intent_id": "BTCUSDT.%s.move_stop.futures" % opened.replace("-", "").replace(":", ""),
                 "market": "futures", "symbol": "BTCUSDT", "action": "move_stop", "side": "BUY", "stop_price": "65000",
                 "reference_price": "66080.5"},
            "ETHUSDT.%s.reduce.futures" % opened.replace("-", "").replace(":", ""):
                {"intent_id": "ETHUSDT.%s.reduce.futures" % opened.replace("-", "").replace(":", ""), "market": "futures",
                 "symbol": "ETHUSDT", "action": "reduce", "fraction": 0.5, "reference_price": "2900"},
            "ETHUSDT.%s.move_stop.futures" % opened.replace("-", "").replace(":", ""):
                {"intent_id": "ETHUSDT.%s.move_stop.futures" % opened.replace("-", "").replace(":", ""),
                 "market": "futures", "symbol": "ETHUSDT", "action": "move_stop", "side": "SELL", "stop_price": "3000",
                 "reference_price": "2895"}}
        assert len([x for x in f.new if " sent (id " in x]) == 5
        # the books after T1 (stop == entry) are accepted by the vault since a88253e: both are sent and held with t1_taken
        assert sum(x.startswith(("vault: BTCUSDT LONG sent", "vault: ETHUSDT SHORT sent")) for x in f.new) == 2
        assert not any("not sent" in x for x in f.new)
        # a lost state re-sends the same ids with the same bodies: the vault's harmless duplicate
        st = json.load(open(f.state, encoding="utf-8"))
        for it in st["intents"].values():
            it["status"] = "pending"
        json.dump(st, open(f.state, "w", encoding="utf-8"))
        f.step(mkt(price=66080.5, t1_taken=True, at=at(1), **btc), mkt(price=2895.0, t1_taken=True, at=at(1), **eth), now=now)
        assert len([x for x in f.new if x.endswith(", duplicate)")]) == 5
        # BTC reaches target 2, ETH is stopped at its entry: closes, then FLAT books
        f.trade("BTCUSDT", "T1+T2", 66500.0, opened=opened)
        f.trade("ETHUSDT", "T1+STOP_BE", 2950.0, side=-1, p_in=3000.0, stop0=3100.0, t1=2900.0, t2=2800.0, opened=opened)
        f.step(mkt(side="FLAT", price=66990.0, at=at(2)), mkt("ETHUSDT", side="FLAT", price=3004.0, at=at(2)), now=now)
        closes = dict((r["id"], json.loads(r["body"])) for r in rig.store.q("SELECT id, body FROM intents")
                      if json.loads(r["body"])["action"] == "close")
        assert sorted((b["symbol"], b["market"], b["reference_price"]) for b in closes.values()) == [
            ("BTCUSDT", "futures", "67000"), ("BTCUSDT", "spot", "67000"), ("ETHUSDT", "futures", "3000")]
        assert held("BTCUSDT") == {"symbol": "BTCUSDT", "side": "FLAT", "price": "66990", "as_of_utc": t[2]}
        assert held("ETHUSDT")["side"] == "FLAT"
        assert not [r for r in rig.store.q("SELECT body FROM intents") if json.loads(r["body"])["action"] == "open"]
        # a book the vault refuses comes back with its code: an as_of older than 1,800 s
        rig.clock.t = ep(t[3]) + 1900
        f.step(mkt(side="FLAT", price=66990.0, at=t[3]), mkt("ETHUSDT", side="FLAT", price=3004.0, at=t[3]), now=now)
        assert f.new == ["vault: BTCUSDT not sent (refused 409 book_stale)", "vault: ETHUSDT not sent (refused 409 book_stale)"]
        # the vault's own address binding: the engine caller from 127.0.0.1 only (the test front is bound to it)
        audit = [r["event"] for r in rig.store.q("SELECT event FROM audit")]
        assert audit.count("book") == 6 and audit.count("intent") == 8          # 4 books + the 2 books after T1
    finally:
        srv.shutdown()
        srv.server_close()
        rig.close()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
