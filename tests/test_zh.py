# -*- coding: utf-8 -*-
"""engine15.zh: the Chinese maps for the website's data files (owner, 28 Nov 2026: "Automatic", "Translate them").
No network: the model is a fake client."""
import json
import types

from engine15 import zh


class FakeClient:
    """Answers like the model would: zh-TW = "繁:" + pattern, zh-CN = "简:" + pattern (marks kept)."""
    def __init__(self, drop_marks=False, refuse=False, tokens=100):
        self.calls = []
        self.drop_marks, self.refuse, self.tokens = drop_marks, refuse, tokens
        self.beta = types.SimpleNamespace(messages=types.SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        items = json.loads(kw["messages"][0]["content"])["items"]
        out = []
        for it in items:
            en = it["en"]
            if self.drop_marks:
                en = zh.MARK.sub("", en)
            out.append({"id": it["id"], "zh_TW": "繁:" + en, "zh_CN": "简:" + en})
        text = types.SimpleNamespace(type="text", text=json.dumps({"items": out}, ensure_ascii=False))
        return types.SimpleNamespace(content=[text], stop_reason="refusal" if self.refuse else "end_turn",
                                     usage=types.SimpleNamespace(output_tokens=self.tokens))


DOC = {"generated_utc": "2026-11-28T12:00:00Z",
       "assets": {"BTCUSDT": {"decision": "HOLD SHORT: the lead is still with the position (+6.7 pts).",
                              "sym": "BTCUSDT", "url": "https://example.com/a b",
                              "facts": [["Trend", "Downtrend (last swing high 62,126.09, low 58,469.93)"],
                                        ["Wall", "Biggest ask wall; 1h move 0.4 sd · 4h move 1.2 sd"]],
                              "when": "2026-11-28 12:00", "code": "TRAIL_STOP", "book": "b_trail_setups",
                              "id_like": "risk_to_all_stops_usd", "n": 3}},
       "items": [{"title": "Bitcoin tops $61,000 as Nasdaq futures extend rebound", "source": "CoinDesk"}]}


def test_collect_takes_prose_and_leaves_codes_dates_links_and_names():
    got = zh.collect(DOC)
    assert "HOLD SHORT: the lead is still with the position (+6.7 pts)." in got
    assert "Bitcoin tops $61,000 as Nasdaq futures extend rebound" in got
    assert "Trend" in got
    for no in ("BTCUSDT", "https://example.com/a b", "2026-11-28 12:00", "TRAIL_STOP", "b_trail_setups",
               "risk_to_all_stops_usd", "2026-11-28T12:00:00Z", "CoinDesk"):
        assert no not in got, no


def test_mask_round_trips_numbers():
    s = "Downtrend (last swing high 62,126.09, low 58,469.93) -1.4% $108k 15m 2x 1R"
    pat, nums = zh.mask(s)
    assert "62" not in pat and "[[0]]" in pat
    assert zh.unmask(pat, nums) == s
    assert zh.mask("lead of 6.7 pts")[0] == zh.mask("lead of 12 pts")[0]       # one pattern for every number


def test_run_writes_the_map_and_reuses_the_cache(tmp_path):
    src = tmp_path / "page.json"
    src.write_text(json.dumps(DOC), encoding="utf-8")
    cache = tmp_path / "cache.json"
    c = FakeClient()
    done, total = zh.run_file(str(src), cache_path=str(cache), client=c, log=lambda *a: None)
    assert done == total and total > 0
    m = json.loads((tmp_path / "page.zh.json").read_text(encoding="utf-8"))
    assert m["schema"] == 1 and m["translated"] == total
    s = "HOLD SHORT: the lead is still with the position (+6.7 pts)."
    assert m["zh-TW"][s] == "繁:HOLD SHORT: the lead is still with the position (+6.7 pts)."
    assert m["zh-CN"][s].startswith("简:")
    # pieces are translated one by one and joined with the Chinese semicolon; numbers come back as they were
    w = m["zh-TW"]["Biggest ask wall; 1h move 0.4 sd · 4h move 1.2 sd"]
    assert w == "繁:Biggest ask wall；繁:1h move 0.4 sd · 繁:4h move 1.2 sd"
    # a later file with new numbers asks nothing new
    DOC2 = json.loads(json.dumps(DOC))
    DOC2["assets"]["BTCUSDT"]["decision"] = "HOLD SHORT: the lead is still with the position (+9.1 pts)."
    src.write_text(json.dumps(DOC2), encoding="utf-8")
    c2 = FakeClient()
    zh.run_file(str(src), cache_path=str(cache), client=c2, log=lambda *a: None)
    assert c2.calls == []
    m2 = json.loads((tmp_path / "page.zh.json").read_text(encoding="utf-8"))
    assert m2["zh-TW"]["HOLD SHORT: the lead is still with the position (+9.1 pts)."].endswith("(+9.1 pts).")


def test_request_shape():
    c = FakeClient()
    zh.fill({"t": {}}, {"lead of [[0]] pts"}, c, log=lambda *a: None)
    kw = c.calls[0]
    assert kw["model"] == "claude-opus-5-5"
    assert kw["fallbacks"] == "default" and kw["betas"] == ["server-side-fallback-2026-07-01"]
    assert kw["output_config"]["format"]["type"] == "json_schema"
    assert "thinking" not in kw and "temperature" not in kw


def test_bad_answers_are_not_kept(tmp_path):
    for c in (FakeClient(drop_marks=True), FakeClient(refuse=True)):
        cache = {"t": {}}
        assert zh.fill(cache, {"lead of [[0]] pts"}, c, log=lambda *a: None) == 0
        assert cache["t"] == {}
    assert not zh.good("x", "Kronos 說")
    assert not zh.good("lead", "")
    assert not zh.good("lead", "still English")
    assert zh.good("CoinDesk", "CoinDesk")


def test_no_client_no_key_means_cache_only(tmp_path):
    src = tmp_path / "x.json"
    src.write_text(json.dumps(DOC), encoding="utf-8")
    done, total = zh.run_file(str(src), cache_path=str(tmp_path / "c.json"), client=None, log=lambda *a: None)
    assert done == 0 and total > 0
    assert zh.read_key(str(tmp_path / "missing.key")) is None


def test_daily_budget_stops_asking():
    import datetime as dt
    now = dt.datetime(2026, 11, 28, tzinfo=dt.timezone.utc)
    cache = {"t": {}, "spend": {"2026-11-28": zh.DAY_OUTPUT_TOKENS}}
    c = FakeClient()
    assert zh.fill(cache, {"a pattern"}, c, log=lambda *a: None, now=now) == 0 and c.calls == []
    cache["spend"] = {"2026-11-27": zh.DAY_OUTPUT_TOKENS}                       # yesterday's spend does not count
    assert zh.fill(cache, {"a pattern"}, c, log=lambda *a: None, now=now) == 1


def test_request_failure_is_quiet():
    class Boom(FakeClient):
        def create(self, **kw):
            raise RuntimeError("down")
    logs = []
    assert zh.fill({"t": {}}, {"a pattern"}, Boom(), log=logs.append) == 0
    assert logs and "next run" in logs[0]


def test_live_run_writes_maps_and_web_copies(tmp_path, monkeypatch):
    from engine15 import zh_live
    live, data, web = tmp_path / "live", tmp_path / "data", tmp_path / "web"
    for d in (live, data, web):
        d.mkdir()
    (live / "page.json").write_text(json.dumps(DOC), encoding="utf-8")
    (live / "setups.json").write_text(json.dumps({"markets": {"BTCUSDT": {"why": "No side clears the bar."}}}), encoding="utf-8")
    monkeypatch.setattr(zh_live, "LIVE", str(live))
    monkeypatch.setattr(zh_live, "CACHE", str(data / "zh_cache.json"))
    monkeypatch.setattr(zh_live, "LOG", str(live / "zh.log"))
    monkeypatch.setenv("MIND15_SETUPS_WEB_DIR", str(web))
    done = zh_live.run(client=FakeClient(), push_page=False)
    assert set(done) == {"page.json", "setups.json"}
    assert (live / "page.zh.json").exists() and (live / "setups.zh.json").exists()
    assert (web / "setups.zh.json").exists() and not (web / "page.zh.json").exists()   # page.zh.json goes by push
    m = json.loads((web / "setups.zh.json").read_text(encoding="utf-8"))
    assert m["zh-CN"]["No side clears the bar."] == "简:No side clears the bar."


def test_live_does_nothing_without_a_key(tmp_path, monkeypatch):
    from engine15 import live, zh_live
    monkeypatch.setattr(zh, "KEY_FILE", str(tmp_path / "none.key"))
    assert not zh_live.ready()
    assert zh_live.main([]) == 0
    assert live.start_zh(log=lambda *a: None) is False


def test_push_file_only_takes_listed_names(monkeypatch):
    from engine15 import push
    monkeypatch.setenv("ENGINE15_PUSH", "1")
    ok, msg = push.push_file("x", "../../etc/passwd")
    assert not ok and "refused" in msg
    assert "page.zh.json" in push._remote("page.zh.json") and "/var/www/aitrading/mind15" in push._remote("page.zh.json")


def test_old_model_name_becomes_the_brand_in_keys():
    got = zh.collect({"a": "Kro" + "nos forecast: up 3 of 5."})
    assert got == {"AlphaPrediction AI forecast: up 3 of 5."}
