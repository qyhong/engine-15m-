# -*- coding: utf-8 -*-
"""Audit helpers: load live trades (main + shadow books), bars and the slim journal."""
import csv, glob, json, os, datetime as dt
A = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "audit")
MK = ["BTCUSDT", "ETHUSDT", "XAUUSD", "XAGUSD", "USDJPY", "SPX", "WTI", "BRENT"]
UTC = dt.timezone.utc

def ms(s):
    s = s.strip().replace("+00:00", "")
    fmt = "%Y-%m-%d %H:%M:%S" if s.count(":") == 2 else "%Y-%m-%d %H:%M"
    return int(dt.datetime.strptime(s, fmt).replace(tzinfo=UTC).timestamp() * 1000)

def ts(m):
    return dt.datetime.fromtimestamp(m / 1000, UTC).strftime("%m-%d %H:%M")

def bars(sym):
    rows = []
    with open(os.path.join(A, "box", sym.lower() + "_15m.csv")) as fh:
        for r in csv.DictReader(fh):
            rows.append((int(r["ts_ms"]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])))
    return rows

def trades(book):
    """book: 'main' (trades_SYM.csv) or a shadow name. -> list of dict rows (one per CSV row, parts kept)."""
    out = []
    pat = "trades_%s.csv" if book == "main" else "shadow_trades_" + book + "_%s.csv"
    for sym in MK:
        p = os.path.join(A, "out", "live", pat % sym)
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                d = dict(r); d["sym"] = sym; d["book"] = book
                d["t_in"] = ms(r["time_in"]); d["t_out"] = ms(r["time_out"])
                for k in ("side", "p_in", "p_out", "pnl_pct", "equity", "qty", "pnl_usd", "fees_usd", "stop0", "risk_usd", "r_mult", "target_1", "target_2"):
                    if k in d and d[k] not in ("", None):
                        d[k] = float(d[k])
                    elif k in d:
                        d[k] = None
                out.append(d)
    return out

def merged(rows):
    """One record per entry (sym, t_in, side): parts summed."""
    m = {}
    for r in rows:
        k = (r["sym"], r["t_in"], r["side"])
        if k not in m:
            m[k] = dict(r, parts=[r], pnl_usd=0.0, fees_usd=0.0, qty=0.0)
            m[k]["why_out"] = ""
        e = m[k]
        e["pnl_usd"] += r["pnl_usd"]; e["fees_usd"] += r["fees_usd"] or 0.0; e["qty"] += r["qty"] or 0.0
        e["t_out"] = max(e["t_out"], r["t_out"]); e["why_out"] = (e["why_out"] + "+" + r["why_out"]).strip("+")
        e["p_out_last"] = r["p_out"]
        if r["parts" if False else "t_out"] >= e["t_out"]:
            e["equity"] = r["equity"]
    return sorted(m.values(), key=lambda e: (e["t_in"], e["sym"]))

def journal():
    j = {}
    with open(os.path.join(A, "box", "journal_slim.jsonl"), encoding="utf-8") as fh:
        for ln in fh:
            r = json.loads(ln)
            j[(r["asset"], ms(r["time"]))] = r
    return j
