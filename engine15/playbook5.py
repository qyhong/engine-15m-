# -*- coding: utf-8 -*-
"""playbook5 -- the RL agent (Phase 4's primary) run FORWARD as a paper book. PAPER ONLY. NOT PASSED.

RL Phase 5, part 1 (owner's choice after the Phase 4 review, 12 Nov 2026: "Trade-less variant + paper"). The agent is
Phase 4's primary: the Q agent pooled on BTC+ETH, expanding window from 2019, Phase 3 features + 18 Mind 15 readings
(research/out/rl/phase4_report.md, configs/rl/phase4.yaml, configs/rl/phase5.yaml). In history it had an edge before
costs (BTC gross Sharpe 0.78, break-even fee about 0.30% a side) but after 0.10% fees it trailed buy-and-hold (Sharpe
0.48 vs 0.64). NOT passed: it runs forward on paper to collect unseen evidence, nothing more.

How a step works (engine15/rl/forward5.py has the details and the training):
  * per coin, the closed bars after REGISTERED that are not decided yet are decided with the newest model whose data
    end is at or before each bar's close: Phase 4's inputs built from the bar file's tail and the evidence store's tail
    rows (read only), the model's values, Phase 3's policy (round-trip cost band, minimum hold 1 h), per seed (0, 1, 2);
  * the decisions are appended to research/out/rl/forward5/decisions_<asset>.jsonl (the record; never rewritten);
  * the book is rebuilt from the record: each seed through the Phase 3 risk manager, the book holds the MEAN of the three
    seeds' executed positions (long or short, at most 1x), decided at a 15m close and filled at the next open, with the
    shared cost model (0.10% a side, half spread 0.5 bp, volatility slippage, perp funding on the whole position);
  * if the weekly refit is due, a separate below-normal-priority process is started (py -3 -m engine15.rl
    phase5-update; >= 1,500 MB free, never two at once). It is never trained inside the step.
Each coin (BTCUSDT, ETHUSDT) has its own $10,000 book from REGISTERED; spot buy-and-hold over the same span is shown
beside it. A trade = one run of same-sign book exposure (re-sizes inside it belong to it).

Rows follow docs/PLAYBOOK_INTERFACE.md: status OPEN / CLOSED, side 1 / -1, no stop and no targets, why_out "AGENT" (the
agent or the risk manager went flat or turned) or "OPEN", r None (no fixed risk unit), pnl_usd / fees_usd / costs_usd in
the book's compounding dollars.
"""
import time

import numpy as np
import pandas as pd

REGISTERED = "2026-11-12 04:30"     # UTC: go-live (first live model ready 04:19 UTC); only decisions at closes after this count
STAKE = 10000.0
BAR_MS = 900000
ASSETS = ("BTCUSDT", "ETHUSDT")
SHORT_NAME = {"BTCUSDT": "BTC", "ETHUSDT": "ETH"}
BOOK = "p5_rlq"

NOT_PASSED = ("RL agent (Phase 4 primary), forward paper; NOT passed: after fees it trailed buy-and-hold in history.")
DETAIL = ("History (Oct 2020 - Nov 2026, out of sample): an edge before costs (BTC gross Sharpe 0.78, break-even fee "
          "about 0.30% a side; ETH 1.11, about 0.42%), but after 0.10% fees BTC Sharpe 0.48 vs buy-and-hold 0.64; "
          "ETH 0.77 vs 0.60 (momentum 0.83). Every historical span has been seen; only this forward record is unseen.")

BOOKS = {
    BOOK: {"title": "RL agent (Phase 4 primary), forward paper; NOT passed: after fees it trailed buy-and-hold in history",
           "short": "RL book", "hypothesis": "RL Phase 5 forward", "registered": REGISTERED, "assets": ASSETS,
           "scoreboard_title": "Strategy: RL agent, Phase 4 primary (NOT passed, forward paper)"},
}

LAST_STATE = {}
LAST_RUN = {}


def reg_ms():
    return int(pd.Timestamp(REGISTERED, tz="UTC").value // 10**6)


def _utc(ms):
    return None if ms is None else str(pd.Timestamp(int(ms), unit="ms", tz="UTC"))[:16]


def _rnd(v, k=6):
    return None if v is None or v != v else round(float(v), k)


def _px(v):
    if v is None or v != v:
        return "n/a"
    a = abs(v)
    return "{:,.0f}".format(v) if a >= 10000 else "{:,.1f}".format(v) if a >= 1000 else "{:,.2f}".format(v)


def _dd(eq):
    if not len(eq):
        return 0.0
    peak = np.maximum.accumulate(eq)
    return float(np.max(1.0 - eq / peak))


def _side(x):
    return "long" if x > 0 else "short" if x < 0 else "flat"


# ---------------------------------------------------------------- trades from the book frame
def runs(pos):
    """Runs of same-sign non-zero held exposure: [(s, e)]."""
    sg = np.sign(np.asarray(pos, dtype=float))
    out, s = [], None
    for t, v in enumerate(sg.tolist()):
        if s is not None and v != sg[s]:
            out.append((s, t - 1))
            s = None
        if s is None and v != 0:
            s = t
    if s is not None:
        out.append((s, len(sg) - 1))
    return out


def trades(B):
    """Book frame (from REGISTERED) -> trades with P&L split so that every bar's result is counted once (a turn's
    trade cost is shared: the exit part to the old trade, the entry part to the new one)."""
    fr, eq = B["frame"], B["equity"]
    pos = fr["pos"].values
    trade = fr["trade"].values
    unit = fr["fee"].values + fr["spread"].values + fr["slippage"].values
    a = np.abs(trade)
    cu = np.where(a > 0, unit / np.where(a > 0, a, 1.0), 0.0)
    feeu = np.where(a > 0, fr["fee"].values / np.where(a > 0, a, 1.0), 0.0)
    eprev = np.concatenate([[STAKE], eq[:-1]])
    gross, fund = fr["r_gross"].values, fr["funding"].values
    o = B["bars"]["open"].values[B["lo"]:]
    cm = B["close_ms"][B["lo"]:]
    n = len(pos)
    out = []
    for s, e in runs(pos):
        x = e + 1
        closed = x < n
        entry_part = abs(pos[s])                                 # the entry part of the trade at bar s
        body = gross[s:e + 1] - fund[s:e + 1]
        costs = unit[s:e + 1].copy()
        costs[0] = cu[s] * entry_part
        fees = feeu[s:e + 1] * a[s:e + 1]
        fees[0] = feeu[s] * entry_part
        pnl = float(np.sum((body - costs) * eprev[s:e + 1]))
        fee_usd = float(np.sum(fees * eprev[s:e + 1]))
        cost_usd = float(np.sum((costs - fees) * eprev[s:e + 1]) + np.sum(fund[s:e + 1] * eprev[s:e + 1]))
        if closed:
            pnl -= cu[x] * abs(pos[e]) * eprev[x]
            fee_usd += feeu[x] * abs(pos[e]) * eprev[x]
            cost_usd += (cu[x] - feeu[x]) * abs(pos[e]) * eprev[x]
        out.append({"s": s, "e": e, "closed": closed, "side": int(np.sign(pos[s])), "e0": float(eprev[s]),
                    "pnl": pnl, "fees": fee_usd, "costs": cost_usd, "entry": float(o[s]),
                    "exit": float(o[x]) if closed else None, "entry_ms": int(cm[s - 1]) if s >= 1 else int(cm[0]),
                    "exit_ms": int(cm[e]) if closed else None, "x_entry": float(pos[s]), "x_now": float(pos[e]),
                    "x_max": float(np.max(np.abs(pos[s:e + 1]))),
                    "resizes": int(np.count_nonzero(np.diff(pos[s:e + 1])))})
    return out


def sentence(asset, t, B):
    a = SHORT_NAME.get(asset, asset)
    head = "RL book, %s: %s %.2fx (mean of 3 seed agents) from %s, entry decided at the %s UTC close" % (
        a, _side(t["side"]), abs(t["x_entry"]), _px(t["entry"]), _utc(t["entry_ms"]))
    if t["resizes"]:
        head += ", re-sized %d time%s" % (t["resizes"], "" if t["resizes"] == 1 else "s")
    if t["closed"]:
        out = "%s. Closed at %s (the agent or the risk manager went flat or turned at the %s UTC close): %+.2f%%, %+.2f USD " \
              "after %.2f USD fees and %.2f USD spread, slippage and funding." % (
                  head, _px(t["exit"]), _utc(t["exit_ms"]), 100 * t["pnl"] / t["e0"], t["pnl"], t["fees"], t["costs"])
    else:
        cm = B["close_ms"]
        out = "%s, now %s %.2fx. Open, marked at the %s UTC close %s: %+.2f%%, %+.2f USD so far (fees %.2f USD)." % (
            head, _side(t["x_now"]), abs(t["x_now"]), _utc(cm[-1]), _px(B["bars"]["close"].values[-1]),
            100 * t["pnl"] / t["e0"], t["pnl"], t["fees"])
    return out + " Paper, forward, NOT passed."


def _row(asset, t, B):
    return {"book": BOOK, "asset": asset, "status": "CLOSED" if t["closed"] else "OPEN", "side": t["side"],
            "setup_utc": _utc(t["entry_ms"]), "entry_utc": _utc(t["entry_ms"]), "entry": _rnd(t["entry"]),
            "stop": None, "target_1": None, "target_2": None,
            "exit_utc": _utc(t["exit_ms"]) if t["closed"] else None, "exit": _rnd(t["exit"]),
            "why_out": "AGENT" if t["closed"] else "OPEN", "r": None, "pnl_usd": _rnd(t["pnl"], 2),
            "fees_usd": _rnd(t["fees"], 2), "costs_usd": _rnd(t["costs"], 2), "pnl_pct": _rnd(100 * t["pnl"] / t["e0"], 3),
            "exposure_entry": _rnd(t["x_entry"], 4), "exposure_now": _rnd(t["x_now"], 4), "exposure_max": _rnd(t["x_max"], 4),
            "equity_before_usd": _rnd(t["e0"], 2), "text": sentence(asset, t, B)}


def _state(asset, B, journal, tr, model_end, update_status):
    cm = B["close_ms"]
    last = journal[-1]
    held_next = float(B["book"][-1])                              # decided at the last close, held from the next open
    eq, beq = B["equity"], B["bh_equity"]
    st = {"last_close_utc": _utc(cm[-1]), "close": _rnd(B["bars"]["close"].values[-1]),
          "rule_exposure": _rnd(held_next, 4), "equity_usd": _rnd(eq[-1], 2), "return_pct": _rnd(100 * (eq[-1] / STAKE - 1), 3),
          "bh_spot_equity_usd": _rnd(beq[-1], 2), "bh_spot_return_pct": _rnd(100 * (beq[-1] / STAKE - 1), 3),
          "max_dd_pct": _rnd(100 * _dd(eq), 3), "bh_max_dd_pct": _rnd(100 * _dd(beq), 3),
          "forward_trades": len(tr), "closed": sum(1 for t in tr if t["closed"]),
          "seed_requests": [float(x) for x in last["req"]],
          "seed_exposures": [_rnd(x, 4) for x in B["exec"][:, -1]],
          "seed_fallback": [bool(x) for x in last["fb"]], "model": last["m"], "model_data_end_utc": model_end,
          "decisions": len(journal), "last_decision_utc": _utc(last["c"]),
          "late_decisions": int(sum(1 for r in journal if r.get("lag_s", 0) > 1800)),
          "update": update_status}
    bk = np.sign(B["book"])
    if held_next != 0:
        j = len(bk) - 1
        while j > 0 and bk[j - 1] == bk[-1]:
            j -= 1
        st["book_position"] = "%s %.2fx since %s UTC" % (_side(held_next), abs(held_next), _utc(cm[j]))
    else:
        st["book_position"] = "flat"
    st["decision"] = ("At the %s UTC close the three seed agents asked for %s (%s); after the risk manager the book holds "
                      "%s %.2fx from the next open." % (
                          _utc(last["c"]), ", ".join("%+.1f" % x for x in last["req"]),
                          "a 'do no harm' fold is flat" if any(last["fb"]) else "model " + str(last["m"]),
                          _side(held_next), abs(held_next)))
    return st


# ---------------------------------------------------------------- live interface
def step(bars=None, now_ms=None, funding=None, readings=None, journal_dir=None, models_dir=None, launch=True,
         cfg=None, log=print):
    """bars: {asset: 15m frame} (None reads the tails of the engine's files); funding: {asset: frame rate / settle_ms};
    readings: {asset: snapshot .npz path} (None = the evidence store, read only). journal_dir / models_dir: defaults
    under research/out/rl. -> rows (docs/PLAYBOOK_INTERFACE.md). Records new decisions; never trains."""
    from .rl import forward5 as f5
    t_start = time.time()
    cfg = cfg or f5.load_cfg()
    jd = journal_dir or f5.forward_dir(cfg)
    md = models_dir or f5.live_models_dir(cfg)
    rms = reg_ms()
    W = int(cfg["phase5"]["forward"]["feature_window_bars"])
    now = int(time.time() * 1000) if now_ms is None else int(now_ms)
    models = [(e, f5.load_model(p)) for e, p in f5.list_models(md)]
    rows = []
    LAST_STATE.clear()
    upd = None
    if launch and bars is None:
        try:
            upd = f5.maybe_launch_update(cfg, log=log)
        except Exception as e:                                    # never let the update break the step
            upd = "launch failed: %r" % (e,)
    import os
    os.makedirs(jd, exist_ok=True)
    for asset in ASSETS:
        try:
            nrows = W + 900 + max(0, (now - rms) // BAR_MS) + 10
            if bars is None:
                df = f5.tail_bars(asset, nrows)
            else:
                df = bars.get(asset)
                if df is None:
                    continue
                df = df[["open", "high", "low", "close", "volume"]].astype(float)
            df = df[np.asarray(df.index.as_unit("ms").asi8) + BAR_MS <= now].iloc[-nrows:]
            if funding is not None and funding.get(asset) is not None:
                fund = funding[asset]
            else:
                from . import data
                fund = f5.funding_frame(data.load_funding(asset))
            fund = fund[np.asarray(fund["settle_ms"], dtype="int64") <= now]
            if len(df) < W + 10:
                continue
            t0 = int(df.index[max(0, len(df) - nrows)].value // 10**6)
            snap = (readings or {}).get(asset)
            times, raw, last = f5.readings_tail(asset, t0, snapshot=snap)
            keep = times + BAR_MS <= now
            if not keep.all():
                times = times[keep]
                raw = dict((k, v[keep]) for k, v in raw.items())
                last = int(times[-1]) if len(times) else None
            jp = os.path.join(jd, "decisions_%s.jsonl" % asset)
            lock = os.path.join(jd, "step_%s.lock" % asset)
            try:
                fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                locked = True
            except FileExistsError:
                locked = False
                if time.time() - os.path.getmtime(lock) > 600:
                    os.remove(lock)
            if locked:
                try:
                    f5.advance(asset, cfg, rms, jp, models, df, fund, (times, raw, last), log=log)
                finally:
                    os.remove(lock)
            journal = f5.read_journal(jp)
            B = f5.risk_and_book(cfg, df, fund, journal, rms)
            if B is None:
                continue
            tr = trades(B)
            for t in tr:
                rows.append(_row(asset, t, B))
            mend = dict((m["id"], m["data_end_utc"]) for _, m in models).get(journal[-1]["m"])
            LAST_STATE.setdefault(BOOK, {})[asset] = _state(asset, B, journal, tr, mend, upd)
        except Exception as e:
            log("playbook5 %s failed: %r" % (asset, e))
            continue
    LAST_RUN.update({"seconds": round(time.time() - t_start, 2), "update": upd, "utc": _utc(now)})
    return rows


def _totals(closed):
    n = len(closed)
    if not n:
        return {"trades": 0, "won": 0, "win_rate_pct": None, "avg_r": None, "net_usd": 0.0, "fees_usd": 0.0,
                "costs_usd": 0.0}
    won = sum(1 for r in closed if r["pnl_usd"] > 0)
    return {"trades": n, "won": won, "win_rate_pct": round(100.0 * won / n, 1), "avg_r": None,
            "avg_pct": round(sum(r["pnl_pct"] for r in closed) / n, 3),
            "net_usd": round(sum(r["pnl_usd"] for r in closed), 2), "fees_usd": round(sum(r["fees_usd"] for r in closed), 2),
            "costs_usd": round(sum(r.get("costs_usd") or 0.0 for r in closed), 2)}


def rule_text():
    return ("%s Every 15-minute close, per coin: Phase 4's inputs (Phase 3 price, volatility, momentum and funding "
            "features plus 18 Mind 15 readings: trend, funding, basis, order flow, volatility regime, levels) go into "
            "three seed copies of the Q agent (pooled BTC+ETH, trained on every bar since 2019, refit weekly in a separate "
            "process); each picks a target in {-1, -0.5, 0, 0.5, 1} only when its value beats a full round-trip cost, "
            "holds at least 1 hour, and is sized by the Phase 3 risk manager (60%%-a-year vol target, drawdown brake). The "
            "book holds the mean of the three, filled at the next 15m open; 0.10%% a side, spread 0.5 bp, volatility "
            "slippage, perp funding. A model judged harmful on the last 6 months ('do no harm') keeps its seed flat. %s "
            "BTC and ETH, each its own $10,000 paper book from %s UTC; only decisions after that count." % (
                NOT_PASSED, DETAIL, REGISTERED))


def page_block(rows):
    out = {}
    for book, facts in BOOKS.items():
        mine = [r for r in rows if r["book"] == book]
        closed = sorted([r for r in mine if r["status"] == "CLOSED"], key=lambda r: r["exit_utc"] or "")
        live = [dict((k, r.get(k)) for k in ("asset", "status", "side", "setup_utc", "entry", "stop", "target_1",
                                              "target_2", "r", "pnl_usd", "text"))
                for r in mine if r["status"] in ("WAITING", "OPEN")]
        per = {}
        for a in facts["assets"]:
            t = _totals([r for r in closed if r["asset"] == a])
            if t["trades"]:
                per[a] = t
        out[book] = {"title": facts["title"], "hypothesis": facts["hypothesis"], "registered": facts["registered"] + " UTC",
                     "not_passed": True, "rule": rule_text(), "open": live,
                     "recent": [dict((k, r.get(k)) for k in ("asset", "side", "entry_utc", "entry", "exit_utc", "exit",
                                                              "why_out", "r", "pnl_usd", "pnl_pct", "text"))
                                for r in closed[-5:]],
                     "totals": _totals(closed), "by_asset": per, "books": dict(LAST_STATE.get(book, {})),
                     "pass_rule": ("No forward verdict before 30 closed forward trades per coin; then, after fees, against "
                                   "spot and perp buy-and-hold since go-live (configs/rl/phase5.yaml). A forward pass "
                                   "would still not make it a passed rule in history."),
                     "note": NOT_PASSED + " " + DETAIL, "step_seconds": LAST_RUN.get("seconds")}
    return out


def main(argv=None):
    rows = step()
    for r in rows:
        print(r["text"])
    for book, b in page_block(rows).items():
        print(book, b["totals"], "step %.2fs" % (b["step_seconds"] or 0))
        for a, s in b["books"].items():
            print("  ", a, s)


if __name__ == "__main__":
    main()
