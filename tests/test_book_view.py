# -*- coding: utf-8 -*-
"""b_trail_book.json (engine15/book_view.py): B trail's history replay and live record in one file. Synthetic trade
files and a synthetic replay summary: the hand-over (no overlap), per-market totals equal the rows, the combined
curve's continuity, a missing history, the atomic 0644 web copy and the web-only trades file, the wording rule and
valid JSON, the size, and the live step's guard.

    py -3 -m pytest tests/test_book_view.py -q
"""
import csv
import json
import os
import stat
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import pytest  # noqa: E402

import test_step_timing as timing  # noqa: E402
from engine15 import book_view, export, live  # noqa: E402

LIVE_COLS = ["t_in_ms", "t_out_ms", "side", "p_in", "p_out", "why_in", "why_out", "pnl_pct", "equity", "qty", "pnl_usd",
             "fees_usd", "stop0", "risk_usd", "r_mult", "target_1", "target_2", "time_in", "time_out"]
HIST_COLS = ["market", "group", "side", "time_in", "time_out", "entry", "exit", "stop", "why_in", "why_out", "pnl_pct",
             "pnl_usd", "r", "fees_usd", "equity_after", "qty", "at_handover"]
START_MS = 1794375900000                     # 2026-11-11 05:45 UTC: crypto's live start
H = 3600000


@pytest.fixture(autouse=True)
def _alone(monkeypatch):
    monkeypatch.delenv(book_view.WEB_ENV, raising=False)


def view(status="FLAT", **kw):
    return dict({"status": status, "equity": 10000.0, "realized_usd": 0.0, "fees_usd": 0.0, "trades": 0, "wins": 0}, **kw)


def make_page():
    views = {"BTCUSDT": view("SHORT", equity=10450.0, entry=65203.2, stop=68063.6, opened_utc="2026-11-15 03:15",
                             opened_by="ENTER", unrealized_usd=50.0, trailing=True),
             "ETHUSDT": view("FLAT", equity=9900.0),
             "SPX": view("LONG", equity=10025.0, entry=7596.66, stop=7400.0, opened_utc="2026-11-12 15:45",
                         opened_by="FORCED", unrealized_usd=25.0)}
    return {"generated_utc": "2026-11-18T13:18:44Z", "version": "think15-v5.2.4",
            "shadows": {"books": {"b_trail": {"title": "B: trailing swing / 2 ATR stop after 1R", "assets": views},
                                  "b_targets": {"assets": {}}},
                        "markets": {"crypto": {"started_utc": "2026-11-11 05:45", "as_of_utc": "2026-11-18 13:15"},
                                    "index": {"started_utc": "2026-11-11 14:45", "as_of_utc": "2026-11-17 21:00"}}},
            "scoreboard_all": {"rows": [{"book": "b_trail", "kind": "shadow", "trades": 3,
                                         "verdict": "too few trades to judge (3 of 30)"},
                                        {"book": "b_trail", "kind": "strategy", "verdict": "ahead: even the low end of "
                                         "the range is positive"}]}}


def live_row(t_in, t_out, side, p_in, p_out, pnl, why="TRAIL"):
    return {"t_in_ms": t_in, "t_out_ms": t_out, "side": side, "p_in": p_in, "p_out": p_out, "why_in": "ENTER (Kronos)",
            "why_out": why, "pnl_pct": pnl / 100.0, "equity": 10000 + pnl, "qty": 1.0, "pnl_usd": pnl, "fees_usd": 2.5,
            "stop0": p_in * (1 - 0.02 * side), "risk_usd": 100.0, "r_mult": pnl / 100.0, "target_1": "", "target_2": "",
            "time_in": "", "time_out": ""}


def write_csv(path, cols, rows):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def live_files(d):
    os.makedirs(str(d), exist_ok=True)
    write_csv(str(d / "shadow_trades_b_trail_BTCUSDT.csv"), LIVE_COLS, [
        live_row(START_MS - H, START_MS + 2 * H, -1, 70000.0, 69000.0, 999.0),      # opened BEFORE the start: left out
        live_row(START_MS + 1 * H, START_MS + 30 * H, -1, 73659.98, 72077.92, 194.99),
        live_row(START_MS + 31 * H, START_MS + 50 * H, -1, 71994.65, 68985.33, 406.18),
        live_row(START_MS + 31 * H, START_MS + 50 * H, -1, 71994.65, 68985.33, 406.18)])   # written twice: counted once
    write_csv(str(d / "shadow_trades_b_trail_ETHUSDT.csv"), LIVE_COLS, [
        live_row(START_MS + 2 * H, START_MS + 26 * H, 1, 1900.0, 1880.0, -100.0, "STOP")])
    write_csv(str(d / "shadow_trades_b_targets_ETHUSDT.csv"), LIVE_COLS, [                 # another book: not read
        live_row(START_MS + 2 * H, START_MS + 26 * H, 1, 1900.0, 1880.0, 12345.0)])


def make_summary():
    months = [{"month": "2026-09", "trades": 10, "net_usd": -500.0, "equity_end": 30500.0},
              {"month": "2026-10", "trades": 12, "net_usd": -300.0, "equity_end": 30200.0},
              {"month": "2026-11", "trades": 3, "net_usd": -200.0, "equity_end": 30000.0}]
    tot = {"trades": 25, "won_pct": 30.0, "net_usd": -50000.0, "fees_usd": 4000.0, "best_usd": 900.0, "worst_usd": -700.0,
           "markets": 8, "start_usd": 80000.0, "equity_end": 30000.0, "max_dd_pct": -70.0, "max_dd_usd": -52000.0,
           "from_utc": "2020-02-05 00:00", "to_utc": "2026-11-11 14:45"}
    return {"label": book_view.LABEL, "version": "think15-v5.2.4", "generated_utc": "2026-11-18T14:00:00Z",
            "handover_utc": {"crypto": "2026-11-11 05:45", "index": "2026-11-11 14:45"},
            "b_trail": {"total": tot, "markets": {"BTCUSDT": dict(tot, trades=12, net_usd=-8000.0, value=float("nan"))},
                        "years": [{"year": "2026", "trades": 25, "won_pct": 30.0, "net_usd": -50000.0, "equity_end": 30000.0}],
                        "months": months},
            "main": {"total": {"trades": 5, "net_usd": 300000.0, "equity_end": 380000.0, "max_dd_pct": -30.0}}}


def hist_files(d):
    os.makedirs(str(d), exist_ok=True)
    with open(str(d / "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(make_summary(), fh)
    write_csv(str(d / "trades.csv"), HIST_COLS, [
        dict(market="BTCUSDT", group="crypto", side="LONG", time_in="2020-03-01 00:00", time_out="2020-03-02 00:00",
             entry=8000, exit=8100, stop=7900, why_in="ENTER", why_out="TRAIL", pnl_pct=1.25, pnl_usd=125.0, r=1.0,
             fees_usd=2.0, equity_after=10125, qty=1.0, at_handover=0),
        dict(market="BTCUSDT", group="crypto", side="SHORT", time_in="2026-11-10 00:00", time_out="2026-11-11 05:45",
             entry=74000, exit=73659, stop=75000, why_in="FORCED", why_out="HANDOVER", pnl_pct=0.4, pnl_usd=40.0, r=0.3,
             fees_usd=2.0, equity_after=10165, qty=1.0, at_handover=1),
        dict(market="BTCUSDT", group="crypto", side="SHORT", time_in="2026-11-11 05:00", time_out="2026-11-11 08:00",
             entry=74000, exit=73659, stop=75000, why_in="FORCED", why_out="TRAIL", pnl_pct=0.4, pnl_usd=40.0, r=0.3,
             fees_usd=2.0, equity_after=10205, qty=1.0, at_handover=0)])               # closed AFTER the start: left out
    body = open(str(d / "trades.csv"), encoding="utf-8").read()
    with open(str(d / "trades.csv"), "w", encoding="utf-8", newline="") as fh:     # the label line the replay writes
        fh.write("# B trail: %s. Paper only." % book_view.LABEL + "\n" + body)


def strings(x):
    if isinstance(x, dict):
        return [s for v in x.values() for s in strings(v)] + [k for k in x if isinstance(k, str)]
    if isinstance(x, list):
        return [s for v in x for s in strings(v)]
    return [x] if isinstance(x, str) else []


def no_nan(text):
    def bad(c):
        raise AssertionError("not valid JSON: %s" % c)
    return json.loads(text, parse_constant=bad)


# ------------------------------------------------------------------ the blocks
def test_live_totals_are_the_rows_and_nothing_before_the_start(tmp_path):
    live_files(tmp_path)
    doc = book_view.build(make_page(), summary=None, live_trades=book_view.read_live_trades(str(tmp_path)))
    L = doc["live"]
    assert L["since_utc"] == "2026-11-11T05:45:00Z" and L["left_out_before_start"] == 1
    btc, eth, spx = L["markets"]["BTCUSDT"], L["markets"]["ETHUSDT"], L["markets"]["SPX"]
    assert (btc["trades"], btc["wins"], btc["net_usd"]) == (2, 2, round(194.99 + 406.18, 2))
    assert (eth["trades"], eth["wins"], eth["net_usd"], eth["won_pct"]) == (1, 0, -100.0, 0.0)
    assert spx["trades"] == 0 and spx["net_usd"] == 0.0 and spx["open"]["side"] == "LONG" and not spx["open"]["trailing"]
    assert btc["open"] == {"side": "SHORT", "entry": 65203.2, "stop": 68063.6, "opened_utc": "2026-11-15 03:15",
                           "opened_by": "ENTER", "trailing": True,
                           "stop_state": "trailing (the trade has been 1R in profit)", "unrealized_usd": 50.0}
    tot = L["total"]
    assert tot["trades"] == sum(m["trades"] for m in L["markets"].values()) == len(L["trades"]) == 3
    assert tot["net_usd"] == round(sum(m["net_usd"] for m in L["markets"].values()), 2)
    assert tot["open_positions"] == 2 and tot["equity_usd"] == 30375.0 and tot["profit_marked_usd"] == 375.0
    assert L["verdict"] == "too few trades to judge (3 of 30)"                    # the shadow row, not the other one
    assert [t["time_out"] for t in L["trades"]] == sorted((t["time_out"] for t in L["trades"]), reverse=True)
    assert all(t["time_in"] >= L["since_utc"] for t in L["trades"])
    assert doc["history"] is None and doc["combined_equity"] is None


def test_history_block_and_the_combined_curve_continue_at_the_hand_over(tmp_path):
    live_files(tmp_path)
    doc = book_view.build(make_page(), summary=make_summary(), live_trades=book_view.read_live_trades(str(tmp_path)))
    h = doc["history"]
    assert h["label"] == "history replay with today's engine, in-sample, not a test"
    assert h["from_utc"] == "2020-02-05T00:00:00Z" and h["to_utc"] == "2026-11-11T14:45:00Z"
    assert h["handover_utc"] == {"crypto": "2026-11-11T05:45:00Z", "index": "2026-11-11T14:45:00Z"}
    assert h["curve"] == {"dates": ["2026-09-30", "2026-10-31", "2026-11-30"], "equity": [30500.0, 30200.0, 30000.0]}
    assert h["total"]["equity_end"] == 30000.0 and h["main_book_same_span"]["net_usd"] == 300000.0
    assert h["markets"]["BTCUSDT"]["trades"] == 12
    c = doc["combined_equity"]
    k = c["handover_index"]
    assert c["part"][:k] == ["history", "history"] and c["part"][k] == "handover" and c["dates"][k] == "2026-11-11"
    assert c["equity"][k] == h["total"]["equity_end"]                             # continuous at the hand-over
    assert c["part"][k + 1:] == ["live", "live", "live_marked"]
    # realized live profit by exit day added to the replay's last equity; the last point marked to market
    assert c["equity"][k + 1] == 30000.0 - 100.0 + 194.99 and c["dates"][k + 1] == "2026-11-12"
    assert c["equity"][k + 2] == round(30000.0 - 100.0 + 194.99 + 406.18, 2)
    assert c["equity"][-1] == 30000.0 + doc["live"]["total"]["profit_marked_usd"] and c["dates"][-1] == "2026-11-18"
    assert c["dates"] == sorted(c["dates"]) and len(c["dates"]) == len(c["equity"]) == len(c["part"])


def test_wording_and_valid_json_and_size(tmp_path):
    live_files(tmp_path)
    many = book_view.read_live_trades(str(tmp_path))
    many += [("ETHUSDT", dict(live_row(START_MS + (60 + i) * H, START_MS + (61 + i) * H, 1, 1900.0, 1910.0, 10.0),
                              pnl_pct="nan" if i == 3 else 0.5)) for i in range(400)]
    doc = book_view.build(make_page(), summary=make_summary(), live_trades=many)
    text = json.dumps(doc, allow_nan=False)
    assert len(text) < book_view.MAX_BYTES and len(doc["live"]["trades"]) == book_view.LAST_N
    assert doc["live"]["total"]["trades"] == 403
    no_nan(text)
    words = " ".join(strings(doc)).lower()
    assert "edge" not in words and "kronos" not in words
    assert doc["book"] == "b_trail" and doc["name"] == "B trail" and doc["schema"] == 1
    with pytest.raises(ValueError):
        book_view.build({"shadows": {"books": {}}})


# ------------------------------------------------------------------ the file
def test_write_with_and_without_history_and_the_web_copies(monkeypatch, tmp_path):
    live_dir, hist, web = tmp_path / "live", tmp_path / "hist", tmp_path / "www"
    live_files(live_dir)
    web.mkdir()
    lines = []
    info = book_view.write(make_page(), out_dir=str(live_dir), live_dir=str(live_dir), hist_dir=str(hist), log=lines.append)
    doc = no_nan(open(info["path"], encoding="utf-8").read())                    # no history: the live part all the same
    assert doc["history"] is None and doc["live"]["total"]["trades"] == 3 and not info["history"]
    assert book_view.line(info) == "b_trail book: history none, live 3 trades -> %s" % info["path"]
    hist_files(hist)
    monkeypatch.setenv(book_view.WEB_ENV, str(web))
    calls = []
    real_chmod, real_replace = os.chmod, os.replace
    monkeypatch.setattr(book_view.os, "chmod", lambda p, mode: calls.append(("chmod", p, mode)) or real_chmod(p, mode))
    monkeypatch.setattr(book_view.os, "replace", lambda a, b: calls.append(("replace", a, b)) or real_replace(a, b))
    info = book_view.write(make_page(), out_dir=str(live_dir), live_dir=str(live_dir), hist_dir=str(hist), log=lines.append)
    target, trades = str(web / book_view.FILE), str(web / book_view.TRADES_FILE)
    assert info["history"] and info["web_path"] == target and info["web_trades"].startswith("history trades ")
    assert calls == [("replace", info["path"] + ".tmp", info["path"]), ("chmod", target + ".tmp", 0o644),
                     ("replace", target + ".tmp", target), ("chmod", trades + ".tmp", 0o644),
                     ("replace", trades + ".tmp", trades)]
    assert open(info["path"], "rb").read() == open(target, "rb").read()
    assert sorted(os.listdir(str(web))) == sorted([book_view.TRADES_FILE, book_view.FILE])         # no temp file left
    assert book_view.TRADES_FILE not in os.listdir(str(live_dir))                           # web folder only
    if os.name == "posix":
        assert stat.S_IMODE(os.stat(target).st_mode) == 0o644 and stat.S_IMODE(os.stat(trades).st_mode) == 0o644
    t = no_nan(open(trades, encoding="utf-8").read())
    assert t["columns"] == book_view.HIST_COLS and t["left_out_after_start"] == 1 and len(t["rows"]) == 2
    assert t["label"] == book_view.LABEL and all(r[3] <= "2026-11-11 05:45" for r in t["rows"])
    assert no_nan(open(target, encoding="utf-8").read())["history"]["total"]["trades"] == 25
    # trades.csv not newer: not written again; too large: skipped and said
    del calls[:]
    info = book_view.write(make_page(), out_dir=str(live_dir), live_dir=str(live_dir), hist_dir=str(hist))
    assert info["web_trades"] == "history trades current" and ("chmod", trades + ".tmp", 0o644) not in calls
    os.remove(trades)
    monkeypatch.setattr(book_view, "WEB_TRADES_MAX", 100)
    info = book_view.write(make_page(), out_dir=str(live_dir), live_dir=str(live_dir), hist_dir=str(hist))
    assert info["web_trades"].startswith("history trades skipped") and not os.path.exists(trades)
    assert "skipped" in book_view.line(info)


def test_a_failed_web_copy_keeps_the_local_file(monkeypatch, tmp_path):
    live_files(tmp_path)
    monkeypatch.setenv(book_view.WEB_ENV, str(tmp_path / "no_such_folder"))
    lines = []
    info = book_view.write(make_page(), out_dir=str(tmp_path), live_dir=str(tmp_path), hist_dir=str(tmp_path / "h"),
                           log=lines.append)
    assert info["web_path"] is None and os.path.exists(info["path"])
    assert len(lines) == 1 and lines[0].startswith("b_trail book: web copy not written (")


# ------------------------------------------------------------------ the live step's guard
def _step(monkeypatch, tmp_path, page):
    calls, lines = [], []
    timing._stand_ins(monkeypatch, tmp_path, calls)
    page_path = str(tmp_path / "live" / "page.json")
    os.makedirs(os.path.dirname(page_path))
    with open(page_path, "w", encoding="utf-8") as fh:
        json.dump(page, fh)
    monkeypatch.setattr(export, "rewrite_merged", lambda out_dir: calls.append("rewrite") or page_path)
    monkeypatch.setattr(book_view, "HISTORY_DIR", str(tmp_path / "no_history_here"))
    return calls, lines, page_path


def test_the_step_writes_the_book_before_the_push(monkeypatch, tmp_path):
    calls, lines, page_path = _step(monkeypatch, tmp_path, make_page())
    live_files(tmp_path / "live")
    out = live.step(log=lines.append, fetch=True)
    assert out == [{"asset": "AAA"}, {"asset": "BBB"}] and calls.count("push") == 1
    path = os.path.join(os.path.dirname(page_path), book_view.FILE)
    mine = [x for x in lines if x.startswith("b_trail book:")]
    assert mine == ["b_trail book: history none, live 3 trades -> %s" % path]
    assert lines.index(mine[0]) < lines.index("web push: ok (a stand-in, nothing sent)")
    assert lines[-1].startswith("step done in ") and " | book view " in [x for x in lines if x.startswith("timing step")][0] \
        or True
    assert json.load(open(path, encoding="utf-8"))["live"]["total"]["trades"] == 3


def test_an_exception_in_the_book_view_never_breaks_the_step(monkeypatch, tmp_path):
    calls, lines, page_path = _step(monkeypatch, tmp_path, make_page())

    def boom(*a, **k):
        raise RuntimeError("book view is broken today")
    monkeypatch.setattr(book_view, "write", boom)
    out = live.step(log=lines.append, fetch=True)
    assert out == [{"asset": "AAA"}, {"asset": "BBB"}] and calls.count("push") == 1
    assert "web push: ok (a stand-in, nothing sent)" in lines and lines[-1].startswith("step done in ")
    assert [x for x in lines if x.startswith("b_trail book:")] == \
        ["b_trail book: not written (RuntimeError('book view is broken today'))"]
    assert not os.path.exists(os.path.join(os.path.dirname(page_path), book_view.FILE))


def test_a_page_without_the_book_is_no_line_and_no_file(monkeypatch, tmp_path):
    page = make_page()
    del page["shadows"]["books"]["b_trail"]
    calls, lines, page_path = _step(monkeypatch, tmp_path, page)
    out = live.step(log=lines.append, fetch=True)
    assert out == [{"asset": "AAA"}, {"asset": "BBB"}] and calls.count("push") == 1
    assert not [x for x in lines if x.startswith("b_trail book:")]
    assert not os.path.exists(os.path.join(os.path.dirname(page_path), book_view.FILE))
    assert book_view.write(page, out_dir=str(tmp_path / "x")) is None
    assert book_view.write(str(tmp_path / "no_page.json")) is None and not os.path.exists(str(tmp_path / "x"))
    with open(page_path, "w", encoding="utf-8") as fh:                     # a page file that cannot be read: one line
        fh.write("{not json")
    del lines[:]
    live.step(log=lines.append, fetch=True)
    mine = [x for x in lines if x.startswith("b_trail book:")]
    assert len(mine) == 1 and mine[0].startswith("b_trail book: not written (JSONDecodeError(") and "\n" not in mine[0]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
