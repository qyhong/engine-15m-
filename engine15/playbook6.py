# -*- coding: utf-8 -*-
"""playbook6 -- RL Phase 6's two forward paper books. PAPER ONLY. NOT PASSED.

Owner's approval after the Phase 6 review (13 Nov 2026). Both books run exactly like playbook5's RL book (engine15/rl/
forward5.py: the step, the record, the risk manager, the book, the costs); engine15/rl/forward6.py has what differs.

  p6_mtrend   the Phase 6 PRIMARY (configs/rl/phase6.yaml, m_trend): the Q agent trained with the missed-opportunity
              reward (r_missed; beta chosen on the validation slice by the frozen rule), and in a 'do no harm' model (its
              own validation net Sharpe under 0.5, that seed and coin) the trend reference position instead of flat: the
              frozen daily 30-day momentum rule, long AND short. Weekly refit: py -3 -m engine15.rl phase6-update.
  p6_p4trend  the CONTROL (p4_trend): Phase 5's weekly Phase 4 primary models (the same files as playbook5's p5_rlq; no
              second copy is trained) with the same trend fallback instead of flat. If p6_mtrend beats p5_rlq but not this
              one, Phase 6's gain came from the momentum fallback, not from the new reward.

Both NOT passed. History (Oct 2020 - Nov 2026, out of sample, after 0.10% fees; research/out/rl/phase6_report.md): m_trend
net Sharpe BTC 0.87, ETH 0.96; p4_trend BTC 0.98, ETH 0.82; buy-and-hold perp 0.64 / 0.60. m_trend is 1 of 8 variants
tried, and the trend fallback was chosen with hindsight (the pattern was visible in Phase 4's results). Every historical
span has been seen; only the forward record is unseen.

How a step works, per coin and book: the closed bars after REGISTERED not yet decided are decided with the newest model of
that book whose data end is at or before each bar's close (Phase 4's inputs from the bar file's and the evidence store's
tails, read only; Phase 3's policy; seeds 0, 1, 2), APPENDED to research/out/rl/forward6/decisions_<book>_<asset>.jsonl,
and the book is rebuilt from that record: each seed through the Phase 3 risk manager, the MEAN of the three, decided at a
15m close and filled at the next open, 0.10% a side, half spread 0.5 bp, volatility slippage, perp funding on the whole
position both sides. Each coin has its own $10,000 book per book id from REGISTERED; spot buy-and-hold beside it. A trade =
one run of same-sign exposure. A book with no model covering a bar records nothing for it (no guess).

Rows follow docs/PLAYBOOK_INTERFACE.md: status OPEN / CLOSED, side 1 / -1, no stop and no targets, why_out "AGENT" or
"OPEN", r None, pnl_usd / fees_usd / costs_usd in the book's compounding dollars.
"""
import os
import time

import numpy as np

from . import playbook5 as p5
from .playbook5 import _dd, _px, _rnd, _side, _totals, _utc, trades

REGISTERED = "2026-11-13 03:00"     # UTC: go-live (wired ~02:47 UTC; first Phase 6 live model ready 02:44 UTC, data end 02:30); only decisions at closes after this count
STAKE = p5.STAKE
BAR_MS = p5.BAR_MS
ASSETS = p5.ASSETS
SHORT_NAME = p5.SHORT_NAME

HINDSIGHT = "the trend fallback was chosen with hindsight (the pattern was visible in Phase 4's results)"
NOT_PASSED = {
    "p6_mtrend": ("RL agent, Phase 6 primary (missed-opportunity reward, trend fallback), forward paper; NOT passed: "
                  "1 of 8 variants tried, and %s." % HINDSIGHT),
    "p6_p4trend": ("RL control: Phase 4 primary with the trend fallback, forward paper; NOT passed: %s." % HINDSIGHT),
}
DETAIL = {
    "p6_mtrend": ("History (Oct 2020 - Nov 2026, out of sample, after 0.10% fees): net Sharpe BTC 0.87, ETH 0.96 vs "
                  "buy-and-hold perp 0.64 / 0.60 (Phase 4 primary as it was: 0.48 / 0.77). Every historical span has been "
                  "seen; only this forward record is unseen."),
    "p6_p4trend": ("The control for p6_mtrend: the same Phase 4 primary models as the RL book p5_rlq, holding the daily "
                   "momentum position instead of flat in 'do no harm' models. History (Oct 2020 - Nov 2026, after 0.10% "
                   "fees): net Sharpe BTC 0.98, ETH 0.82 vs buy-and-hold perp 0.64 / 0.60. If p6_mtrend does no better "
                   "than this book, Phase 6's gain came from the fallback, not the new reward. Only this forward record "
                   "is unseen."),
}
BOOKS = {
    "p6_mtrend": {"title": "RL agent, Phase 6 primary (missed-opportunity reward, trend fallback), forward paper; NOT "
                           "passed: 1 of 8 variants tried, trend fallback chosen with hindsight",
                  "short": "RL Phase 6 book", "hypothesis": "RL Phase 6 forward (primary)", "registered": REGISTERED,
                  "assets": ASSETS, "models": "phase6", "fallback": "trend",
                  "scoreboard_title": "Strategy: RL agent, Phase 6 primary, missed-opportunity reward + trend fallback "
                                      "(NOT passed: 1 of 8 variants, fallback chosen with hindsight; forward paper)"},
    "p6_p4trend": {"title": "RL control: Phase 4 primary with the trend fallback, forward paper; NOT passed: trend "
                            "fallback chosen with hindsight",
                   "short": "RL control book", "hypothesis": "RL Phase 6 forward (control)", "registered": REGISTERED,
                   "assets": ASSETS, "models": "phase4", "fallback": "trend",
                   "scoreboard_title": "Strategy: RL control, Phase 4 primary + trend fallback (NOT passed: fallback "
                                       "chosen with hindsight; forward paper)"},
}

LAST_STATE = {}
LAST_RUN = {}


def reg_ms():
    import pandas as pd
    return int(pd.Timestamp(REGISTERED, tz="UTC").value // 10**6)


def _modes_text(modes):
    n = sum(1 for m in modes if m == "trend")
    if not n:
        return "every seed on its model"
    return "%d of %d seed%s holding the daily momentum position ('do no harm': validation net Sharpe under 0.5)" % (
        n, len(modes), "" if len(modes) == 1 else "s")


def sentence(book, asset, t, B):
    a = SHORT_NAME.get(asset, asset)
    head = "%s, %s: %s %.2fx (mean of 3 seed agents) from %s, entry decided at the %s UTC close" % (
        BOOKS[book]["short"], a, _side(t["side"]), abs(t["x_entry"]), _px(t["entry"]), _utc(t["entry_ms"]))
    if t["resizes"]:
        head += ", re-sized %d time%s" % (t["resizes"], "" if t["resizes"] == 1 else "s")
    if t["closed"]:
        out = "%s. Closed at %s (the agents or the risk manager went flat or turned at the %s UTC close): %+.2f%%, %+.2f " \
              "USD after %.2f USD fees and %.2f USD spread, slippage and funding." % (
                  head, _px(t["exit"]), _utc(t["exit_ms"]), 100 * t["pnl"] / t["e0"], t["pnl"], t["fees"], t["costs"])
    else:
        cm = B["close_ms"]
        out = "%s, now %s %.2fx. Open, marked at the %s UTC close %s: %+.2f%%, %+.2f USD so far (fees %.2f USD)." % (
            head, _side(t["x_now"]), abs(t["x_now"]), _utc(cm[-1]), _px(B["bars"]["close"].values[-1]),
            100 * t["pnl"] / t["e0"], t["pnl"], t["fees"])
    return out + " Paper, forward, NOT passed."


def _row(book, asset, t, B):
    r = p5._row(asset, t, B)
    r["book"] = book
    r["text"] = sentence(book, asset, t, B)
    return r


def _momentum(close):
    """The coin's 30-day return at the last close (%) and the frozen daily 30-day momentum rule's current sign (decided at
    the last 00:00 UTC close: what a seed in trend mode holds), as playbook4's fields."""
    from .rl import benchmarks
    c = np.asarray(close.values, dtype=float)
    w = 30 * int(86400000 // BAR_MS)
    mom = 100.0 * (c[-1] / c[-1 - w] - 1.0) if len(c) > w and c[-1 - w] > 0 else None
    d = benchmarks.momentum(close.astype(float), 30, True, BAR_MS).values
    return {"momentum_30d_pct": _rnd(mom, 2), "daily_direction": int(d[-1]) if len(d) else 0}


def _state(book, asset, B, journal, tr, model, update_status):
    cm = B["close_ms"]
    last = journal[-1]
    held_next = float(B["book"][-1])                              # decided at the last close, held from the next open
    eq, beq = B["equity"], B["bh_equity"]
    modes = last.get("mode") or ["trend" if f else "model" for f in last["fb"]]
    st = {"last_close_utc": _utc(cm[-1]), "close": _rnd(B["bars"]["close"].values[-1]),
          "rule_exposure": _rnd(held_next, 4), "equity_usd": _rnd(eq[-1], 2), "return_pct": _rnd(100 * (eq[-1] / STAKE - 1), 3),
          "bh_spot_equity_usd": _rnd(beq[-1], 2), "bh_spot_return_pct": _rnd(100 * (beq[-1] / STAKE - 1), 3),
          "max_dd_pct": _rnd(100 * _dd(eq), 3), "bh_max_dd_pct": _rnd(100 * _dd(beq), 3),
          "forward_trades": len(tr), "closed": sum(1 for t in tr if t["closed"]),
          "seed_requests": [float(x) for x in last["req"]],
          "seed_exposures": [_rnd(x, 4) for x in B["exec"][:, -1]],
          "seed_fallback": [bool(x) for x in last["fb"]], "seed_modes": list(modes),
          "fallback_rule": "a seed whose model's own validation net Sharpe (that coin) is under 0.5 holds the daily 30-day "
                           "momentum position (long or short) instead of its values; fixed when the model is trained",
          "model": last["m"], "model_data_end_utc": model.get("data_end_utc") if model else None,
          "decisions": len(journal), "last_decision_utc": _utc(last["c"]),
          "late_decisions": int(sum(1 for r in journal if r.get("lag_s", 0) > 1800)),
          "update": update_status}
    st.update(_momentum(B["bars"]["close"]))
    st["fallback_seeds"] = int(sum(1 for m in modes if m == "trend"))
    if model:
        from .rl import forward6 as f6
        st["seed_val_net_sharpe"] = [m["val_net_sharpe"] for m in f6.model_modes(model, (asset,))[asset]]
        betas = [m["beta"] for m in f6.model_modes(model, (asset,))[asset]]
        if any(b is not None for b in betas):
            st["seed_beta"] = betas
    bk = np.sign(B["book"])
    if held_next != 0:
        j = len(bk) - 1
        while j > 0 and bk[j - 1] == bk[-1]:
            j -= 1
        st["book_position"] = "%s %.2fx since %s UTC" % (_side(held_next), abs(held_next), _utc(cm[j]))
    else:
        st["book_position"] = "flat"
    st["decision"] = ("At the %s UTC close the three seed agents asked for %s (model %s; %s); after the risk manager the "
                      "book holds %s %.2fx from the next open." % (
                          _utc(last["c"]), ", ".join("%+.1f" % x for x in last["req"]), last["m"], _modes_text(modes),
                          _side(held_next), abs(held_next)))
    return st


def models_dirs(cfg):
    from .rl import forward6 as f6
    return {"p6_mtrend": f6.live_models_dir(cfg), "p6_p4trend": f6.p4_models_dir(cfg)}


# ---------------------------------------------------------------- live interface
def step(bars=None, now_ms=None, funding=None, readings=None, journal_dir=None, models_dir=None, launch=True,
         cfg=None, log=print):
    """bars: {asset: 15m frame} (None reads the tails of the engine's files); funding: {asset: frame rate / settle_ms};
    readings: {asset: snapshot .npz path} (None = the evidence store, read only). journal_dir: default
    research/out/rl/forward6; models_dir: {book: folder} (default: models6/live for p6_mtrend, models5/live for
    p6_p4trend). -> rows (docs/PLAYBOOK_INTERFACE.md). Records new decisions; never trains."""
    from .rl import forward5 as f5
    from .rl import forward6 as f6
    t_start = time.time()
    cfg = cfg or f6.load_cfg()
    jd = journal_dir or f6.forward_dir(cfg)
    md = dict(models_dirs(cfg), **(models_dir or {}))
    rms = reg_ms()
    W = int(cfg["phase5"]["forward"]["feature_window_bars"])
    now = int(time.time() * 1000) if now_ms is None else int(now_ms)
    models = dict((b, [(e, f5.load_model(p)) for e, p in f5.list_models(md[b])]) for b in BOOKS)
    rows = []
    LAST_STATE.clear()
    upd = None
    if launch and bars is None:
        try:
            upd = f6.maybe_launch_update(cfg, log=log)
        except Exception as e:                                    # never let the update break the step
            upd = "launch failed: %r" % (e,)
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
        except Exception as e:
            log("playbook6 %s data failed: %r" % (asset, e))
            continue
        feats_cache = {}                                           # both books decide on the same inputs
        for book, facts in BOOKS.items():
            try:
                jp = os.path.join(jd, "decisions_%s_%s.jsonl" % (book, asset))
                lock = os.path.join(jd, "step_%s_%s.lock" % (book, asset))
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
                        f5.advance(asset, cfg, rms, jp, models[book], df, fund, (times, raw, last), log=log,
                                   fallback=facts["fallback"], feats_cache=feats_cache)
                    finally:
                        os.remove(lock)
                journal = f5.read_journal(jp)
                B = f5.risk_and_book(cfg, df, fund, journal, rms)
                if B is None:
                    continue
                tr = trades(B)
                for t in tr:
                    rows.append(_row(book, asset, t, B))
                mdl = dict((m["id"], m) for _, m in models[book]).get(journal[-1]["m"])
                LAST_STATE.setdefault(book, {})[asset] = _state(book, asset, B, journal, tr, mdl,
                                                                upd if facts["models"] == "phase6" else "phase5's refit")
                try:                                              # who earned it, and the drift reading (page only)
                    LAST_STATE[book][asset].update(f5.health_fields(cfg, B, journal, STAKE))
                except Exception as e:
                    log("playbook6 %s %s health fields failed: %r" % (book, asset, e))
            except Exception as e:
                log("playbook6 %s %s failed: %r" % (book, asset, e))
                continue
    LAST_RUN.update({"seconds": round(time.time() - t_start, 2), "update": upd, "utc": _utc(now),
                     "models": dict((b, [m["id"] for _, m in v]) for b, v in models.items())})
    return rows


def rule_text(book):
    if book == "p6_mtrend":
        agent = ("three seed copies of the Phase 6 Q agent (pooled BTC+ETH, trained on every bar since 2019 with the "
                 "missed-opportunity reward: in training only, the idle part of the book is charged what the daily "
                 "momentum rule earned on it, beta chosen on the last 6 months; refit weekly in a separate process)")
    else:
        agent = ("three seed copies of the Phase 4 primary Q agent (the same weekly models as the RL book p5_rlq; no "
                 "second copy is trained)")
    return ("%s Every 15-minute close, per coin: Phase 4's inputs (Phase 3 price, volatility, momentum and funding "
            "features plus 18 Mind 15 readings) go into %s; each picks a target in {-1, -0.5, 0, 0.5, 1} only when its "
            "value beats a full round-trip cost, holds at least 1 hour, and is sized by the Phase 3 risk manager (60%%-a-"
            "year vol target, drawdown brake). A seed whose model scored a validation net Sharpe under 0.5 on the last 6 "
            "months ('do no harm') holds the daily 30-day momentum position, long or short, instead of going flat. The "
            "book holds the mean of the three, filled at the next 15m open; 0.10%% a side, spread 0.5 bp, volatility "
            "slippage, perp funding both sides. %s BTC and ETH, each its own $10,000 paper book from %s UTC; only "
            "decisions after that count." % (NOT_PASSED[book], agent, DETAIL[book], REGISTERED))


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
                     "not_passed": True, "rule": rule_text(book), "open": live,
                     "recent": [dict((k, r.get(k)) for k in ("asset", "side", "entry_utc", "entry", "exit_utc", "exit",
                                                              "why_out", "r", "pnl_usd", "pnl_pct", "text"))
                                for r in closed[-5:]],
                     "totals": _totals(closed), "by_asset": per, "books": dict(LAST_STATE.get(book, {})),
                     "split": p5._sum_splits(LAST_STATE.get(book, {})),
                     "pass_rule": ("No forward verdict before 30 closed forward trades per coin; then, after fees, against "
                                   "spot and perp buy-and-hold since go-live, against the RL book p5_rlq and against each "
                                   "other (p6_mtrend vs the control p6_p4trend). A forward pass would still not make it a "
                                   "passed rule in history."),
                     "note": NOT_PASSED[book] + " " + DETAIL[book], "step_seconds": LAST_RUN.get("seconds")}
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
