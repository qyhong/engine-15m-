# -*- coding: utf-8 -*-
"""rl_lab -- the RL block of page.json for the site's Lab tab (key "rl_lab"). Read only; it decides nothing.

Owner, 22 Nov 2026: "Run all above" (task 8 of the RL audit of 21 Nov 2026: "Write an RL block into the page data for the
Lab tab (status, fallback flags, refit history); the site session displays it"). This project only writes the data; the
site session builds the tab from the field list in docs/RL.md ("The page's rl_lab block").

Built from what the RL books already keep: their page blocks in out/live/playbook.json (reports.playbook_block: states
per coin with the split and the drift reading), their decision records (research/out/rl/forward5, forward6, forward8:
since when each seed is on its model or its fallback, when each model was first used) and their model files
(research/out/rl/models5/live, models6/live: the refit history and which seeds passed validation). Nothing here trains,
decides or writes anything but the returned dict; export.merge calls block() inside its own try/except, so a failure here
never stops the page. None of these books has passed.
"""
import os
import time

SCHEMA = 1
NEED = 30                                       # the verdict rule: 30 closed forward trades per coin
LATE_S = 1800                                   # a decision recorded more than 30 minutes after its close is late (playbooks)
STALE_S = 2 * 3600                              # no decision for 2 hours -> status "stale"
ASSETS = ("BTCUSDT", "ETHUSDT")
BOOKS = {                                       # book -> page module, kind, model folder, record folder, fallback kind
    "p5_rlq": {"module": "playbook5", "kind": "agent", "models": "phase5", "record": "forward5", "fallback": "flat"},
    "p6_mtrend": {"module": "playbook6", "kind": "agent", "models": "phase6", "record": "forward6", "fallback": "momentum"},
    "p6_p4trend": {"module": "playbook6", "kind": "control", "models": "phase5", "record": "forward6", "fallback": "momentum"},
}
YARDSTICK = {"book": "p8_mom", "module": "playbook8", "record": "forward8", "for": ("p6_mtrend", "p6_p4trend")}
NOTE = ("None of these books has passed. They are forward paper books: no RL agent has passed its test against "
        "buy-and-hold, and no verdict comes before 30 closed forward trades per coin. Where a seed fails its own "
        "validation it holds a fallback (flat in p5_rlq, the daily 30-day momentum position in the Phase 6 books); the "
        "split shows how much of each result the fallback earned. The momentum yardstick p8_mom trades that fallback "
        "rule alone, so that its result is not credited to an agent.")
VERDICT_RULE = ("No verdict before 30 closed forward trades per coin; then, after fees, against spot and perp buy-and-hold "
                "since go-live (and for the Phase 6 books against p5_rlq and each other). Paper only.")

_JCACHE = {}


def _utc(ms):
    import pandas as pd
    return None if ms is None else str(pd.Timestamp(int(ms), unit="ms", tz="UTC"))[:16]


def _ms(utc):
    import pandas as pd
    return int(pd.Timestamp(utc, tz="UTC").value // 10**6)


def _journal(path):
    """A decision record, cached by size and modification time (the page is rewritten often)."""
    from .rl import forward5 as f5
    try:
        st = os.stat(path)
    except OSError:
        return []
    key = (st.st_size, st.st_mtime)
    hit = _JCACHE.get(path)
    if hit and hit[0] == key:
        return hit[1]
    J = f5.read_journal(path)
    _JCACHE[path] = (key, J)
    return J


def journal_path(book, asset, dirs):
    d = dirs[BOOKS[book]["record"] if book in BOOKS else YARDSTICK["record"]]
    return os.path.join(d, "decisions_%s.jsonl" % asset if book == "p5_rlq" else "decisions_%s_%s.jsonl" % (book, asset))


def seed_modes(J):
    """Per seed, from the record: its mode now ("model" / "fallback") and the close of the first decision of the current
    unbroken run in that mode (since when)."""
    if not J:
        return []
    last = J[-1]["fb"]
    out = []
    for s, fb in enumerate(last):
        k = len(J) - 1
        while k > 0 and len(J[k - 1]["fb"]) > s and bool(J[k - 1]["fb"][s]) == bool(fb):
            k -= 1
        out.append({"seed": s, "mode": "fallback" if fb else "model", "since_utc": _utc(J[k]["c"])})
    return out


def refits(book, mdir, J, assets=ASSETS):
    """The book's model history, oldest first: id, data end, created, first and last decision with it, and per coin which
    seeds passed validation (own validation net Sharpe at least 0.5: on its model) with their validation Sharpe."""
    from .rl import forward5 as f5
    from .rl import forward6 as f6
    used = {}
    for r in J:
        u = used.setdefault(r["m"], [r["c"], r["c"]])
        u[1] = r["c"]
    out = []
    for end, p in f5.list_models(mdir):
        try:
            m = f5.load_model(p)
            modes = f6.model_modes(m, assets)
        except Exception:
            continue
        u = used.get(m.get("id"))
        out.append({"model_id": m.get("id"), "data_end_utc": _utc(end), "created_utc": m.get("created_utc"),
                    "first_decision_utc": _utc(u[0]) if u else None, "last_decision_utc": _utc(u[1]) if u else None,
                    "seeds_passed_validation": dict((a, [x["seed"] for x in modes[a] if x["mode"] == "model"]) for a in assets),
                    "val_net_sharpe": dict((a, [x["val_net_sharpe"] for x in modes[a]]) for a in assets)})
    return out


def _coin(st, J, now_ms, fallback_kind):
    """One book on one coin, from its page state and its record."""
    sm = seed_modes(J)
    n_fb = sum(1 for x in sm if x["mode"] == "fallback")
    closed = int(st.get("closed") or 0)
    dec = int(st.get("decisions") or len(J) or 0)
    late = int(st.get("late_decisions") or 0)
    last_c = J[-1]["c"] if J else None
    return {"status": "stale" if last_c is None or now_ms - int(last_c) > STALE_S * 1000 else "running",
            "position": st.get("book_position"), "exposure": st.get("rule_exposure"),
            "equity_usd": st.get("equity_usd"), "return_pct": st.get("return_pct"),
            "bh_spot_equity_usd": st.get("bh_spot_equity_usd"), "bh_spot_return_pct": st.get("bh_spot_return_pct"),
            "max_dd_pct": st.get("max_dd_pct"), "bh_max_dd_pct": st.get("bh_max_dd_pct"),
            "closed_trades": closed, "trades_needed": NEED, "progress_pct": round(min(100.0, 100.0 * closed / NEED), 1),
            "seeds": len(sm), "seeds_on_model": len(sm) - n_fb, "seeds_on_fallback": n_fb, "fallback_kind": fallback_kind,
            "seed_modes": sm, "split": st.get("split"), "input_drift": st.get("input_drift"),
            "model_id": st.get("model"), "model_data_end_utc": st.get("model_data_end_utc"),
            "last_decision_utc": st.get("last_decision_utc") or _utc(last_c), "decisions": dec, "late_decisions": late,
            "late_share_pct": round(100.0 * late / dec, 1) if dec else None}


def default_dirs():
    from .rl import forward5 as f5
    from .rl import forward6 as f6
    from .rl.config import resolve
    cfg = f5.load_cfg()                                            # paths only (forward6's need no config)
    return ({"forward5": f5.forward_dir(cfg), "forward6": f6.forward_dir(cfg), "forward8": resolve("research/out/rl/forward8")},
            {"phase5": f5.live_models_dir(cfg), "phase6": f6.live_models_dir(cfg)})


def interim_dates():
    """The registered 8-week interim read (research/HYPOTHESES.md; research/rl_interim_read.py)."""
    import importlib.util
    from .config import ROOT
    p = os.path.join(ROOT, "research", "rl_interim_read.py")
    spec = importlib.util.spec_from_file_location("rl_interim_read", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict((b, {"start_utc": s, "read_utc": r}) for b, (s, r) in mod.READS.items()), mod.YARD_START


def block(pb=None, record_dirs=None, models_dirs=None, now_ms=None, log=print):
    """-> the rl_lab dict (schema SCHEMA). pb: the playbook page blocks (default reports.playbook_block())."""
    if pb is None:
        from . import reports
        pb = reports.playbook_block() or {}
    if record_dirs is None or models_dirs is None:
        rd, md = default_dirs()
        record_dirs, models_dirs = record_dirs or rd, models_dirs or md
    now = int(time.time() * 1000) if now_ms is None else int(now_ms)
    try:
        interim, yard_start = interim_dates()
    except Exception as e:
        log("rl_lab interim dates: %r" % (e,))
        interim, yard_start = {}, None
    yb = (pb.get(YARDSTICK["module"]) or {}).get(YARDSTICK["book"]) or {}
    out = {"schema": SCHEMA, "generated_utc": _utc(now), "note": NOTE, "verdict_rule": VERDICT_RULE, "not_passed": True,
           "interim_read": {"books": interim, "words": "interim; per comparison only 'ahead of', 'behind' or 'level with' "
                                                       "(within 1.0 percentage point), with the numbers",
                            "changes_nothing": "the 30-closed-trades-per-coin rule still decides; every book stays NOT passed",
                            "registered": "research/HYPOTHESES.md, 'Interim read of the RL forward books at 8 weeks'"},
           "books": {}}
    for book, facts in BOOKS.items():
        try:
            b = (pb.get(facts["module"]) or {}).get(book) or {}
            states = b.get("books") or {}
            coins = {}
            for a in ASSETS:
                try:
                    J = _journal(journal_path(book, a, record_dirs))
                    if a not in states and not J:
                        continue
                    c = _coin(states.get(a) or {}, J, now, facts["fallback"])
                    if book in YARDSTICK["for"]:
                        ys = ((yb.get("books") or {}).get(a) or {})
                        c["momentum_yardstick"] = (ys.get("same_days") or {}).get(book)
                    coins[a] = c
                except Exception as e:
                    log("rl_lab %s %s: %r" % (book, a, e))
            J_all = []
            for a in ASSETS:
                J_all += _journal(journal_path(book, a, record_dirs))
            J_all.sort(key=lambda r: r["c"])
            try:
                hist = refits(book, models_dirs[facts["models"]], J_all)
            except Exception as e:
                log("rl_lab %s refits: %r" % (book, e))
                hist = []
            out["books"][book] = {"title": b.get("title"), "kind": facts["kind"], "not_passed": True,
                                  "started_utc": (b.get("registered") or "").replace(" UTC", "") or
                                  (interim.get(book) or {}).get("start_utc"),
                                  "interim_read_utc": (interim.get(book) or {}).get("read_utc"),
                                  "fallback_kind": facts["fallback"], "coins": coins, "split": b.get("split"),
                                  "totals": b.get("totals"), "refits": hist}
        except Exception as e:
            log("rl_lab %s: %r" % (book, e))
    try:
        coins = {}
        for a, s in (yb.get("books") or {}).items():
            J = _journal(journal_path(YARDSTICK["book"], a, record_dirs))
            coins[a] = {"status": "stale" if not J or now - int(J[-1]["c"]) > STALE_S * 1000 else "running",
                        "position": s.get("book_position"), "equity_usd": s.get("equity_usd"),
                        "return_pct": s.get("return_pct"), "bh_spot_return_pct": s.get("bh_spot_return_pct"),
                        "max_dd_pct": s.get("max_dd_pct"), "closed_trades": s.get("closed"),
                        "daily_direction": s.get("daily_direction"), "momentum_30d_pct": s.get("momentum_30d_pct"),
                        "last_decision_utc": s.get("last_decision_utc"), "late_decisions": s.get("late_decisions"),
                        "decisions": s.get("decisions"), "same_days": s.get("same_days") or {}}
        out["momentum_yardstick"] = {"book": YARDSTICK["book"], "for": list(YARDSTICK["for"]),
                                     "started_utc": (yb.get("registered") or "").replace(" UTC", "") or yard_start,
                                     "not_a_hypothesis": True, "coins": coins, "totals": yb.get("totals"),
                                     "note": "The Phase 6 books' daily 30-day momentum fallback alone, through the same "
                                             "code, fees and decision times. It starts later than the RL books, so they "
                                             "are compared with it over the same days only (same_days)."}
    except Exception as e:
        log("rl_lab yardstick: %r" % (e,))
        out["momentum_yardstick"] = None
    return out
