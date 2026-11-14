# -*- coding: utf-8 -*-
"""L1 surprise mining: the biggest 15m-to-4h moves, the engine's worst calls, and what came before.

1. Surprises. For each coin, the move from the close of bar t to the close of t+4 (1 hour) and
   t+16 (4 hours), in units of the 1-hour ATR14 known at t. A surprise is a move in the top 2% of
   absolute size (cut point from the whole history, per coin and horizon). Overlapping bars of
   one move are merged: only the biggest bar of each cluster is kept.
2. Readings before. At the close of t (before the move) every surprise is snapshotted: the L2
   state, volatility build-up, flow, distance to the 24h and 7-day highs and lows, volume, funding,
   session, hours to / since a US release (calendar on file from May 2026 only).
3. What repeats. Each yes/no precursor is compared between the surprise bars and all bars: lift
   (how many times more common before surprises) with counts, per coin and per half of history.
   A precursor is listed only if it leans the same way in all four tests. A placebo (the surprise
   times slid in time) shows how many would pass by luck.
4. The engine. For each surprise: which side the engine held (replay trades, out/replay/trades_*.csv;
   live journal, journal/*.jsonl, where it covers). Separately: the engine's worst replay trades and
   the precursors that were more common at their entries than at its entries in general.

    py -3 research/surprises.py             # full history; recent section = last 30 days
    py -3 research/surprises.py --days 7    # daily report: surprises of the last 7 days
Writes research/out/surprises.json and research/out/surprises.md (or surprises_<N>d.* with --days).
"""
import argparse
import glob
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discovery_lib as L  # noqa: E402

from engine15.config import CFG, JOURNAL_DIR, OUT_DIR as ENGINE_OUT  # noqa: E402

TOP_Q = 0.98            # a surprise: top 2% of absolute move in ATR units
HORIZONS = (4, 16)
MIN_K = 5               # a precursor needs at least this many surprise bars in every test
Z_MIN = 1.5             # ... and a binomial z of at least this in every test
WORST_Q = 0.10          # the engine's worst calls: bottom 10% of replay trades by P&L, per coin

READ_COLS = ["vol_ratio", "compress", "width24", "volsurge", "flow1h", "flow4h", "move1h", "move4h",
             "d_hi24", "d_lo24", "d_hi7d", "d_lo7d", "funding", "hrs_to_econ", "hrs_since_econ"]
READ_TEXT = {"vol_ratio": "last hour's range vs 30-day norm (x)", "compress": "last 4h range vs last 24h (x)",
             "width24": "24h range in ATR units", "volsurge": "last hour's volume vs 30-day norm (x)",
             "flow1h": "net taker buying, 1h (share of volume)", "flow4h": "net taker buying, 4h",
             "move1h": "last hour's move (ATR)", "move4h": "last 4 hours' move (ATR)",
             "d_hi24": "distance below 24h high (ATR)", "d_lo24": "distance above 24h low (ATR)",
             "d_hi7d": "distance below 7-day high (ATR)", "d_lo7d": "distance above 7-day low (ATR)",
             "funding": "funding rate", "hrs_to_econ": "hours to next US release",
             "hrs_since_econ": "hours since last US release"}


# ---------------------------------------------------------------- precursor flags
def flags(f, st, thr, times):
    """-> dict name -> (text, flag bool array, valid bool array). All known at the bar's close."""
    out = {}
    for d in L.DIM_NAMES:
        x = st[d].values
        for code, lab in enumerate(L.DIM_LABELS[d]):
            out["%s=%s" % (d, lab)] = ("L2 state: " + lab + " (" + d + ")", x == code, x >= 0)

    def col(c):
        v = f[c].values.astype(float)
        return v, np.isfinite(v)

    v, ok = col("width24")
    out["squeeze"] = ("the last 24h range is narrow (bottom fifth, in ATR units)", v <= thr["q_width24"][0], ok)
    v, ok = col("compress")
    out["vol_building"] = ("the last 4h ranges are wide against the last 24h (top fifth): volatility building",
                           v >= thr["q_compress"][0], ok)
    v, ok = col("volsurge")
    out["volume_surge"] = ("last hour's volume is high against the month (top tenth)", v >= thr["q_volsurge"][0], ok)
    v, ok = col("d_hi24")
    out["at_24h_high"] = ("within 0.5 ATR of the 24h high", v <= 0.5, ok)
    v, ok = col("d_lo24")
    out["at_24h_low"] = ("within 0.5 ATR of the 24h low", v <= 0.5, ok)
    v, ok = col("d_hi7d")
    out["at_7d_high"] = ("within 1 ATR of the 7-day high", v <= 1.0, ok)
    v, ok = col("d_lo7d")
    out["at_7d_low"] = ("within 1 ATR of the 7-day low", v <= 1.0, ok)
    v, ok = col("move4h")
    out["ran_up_4h"] = ("the last 4 hours rose hard (top tenth, ATR units)", v >= thr["q_move4h"][1], ok)
    out["ran_down_4h"] = ("the last 4 hours fell hard (bottom tenth, ATR units)", v <= thr["q_move4h"][0], ok)
    v, ok = col("flow1h")
    out["flow_buy_1h"] = ("heavy net taker BUYING in the last hour (top tenth)", v >= thr["q_flow1h"][1], ok)
    out["flow_sell_1h"] = ("heavy net taker SELLING in the last hour (bottom tenth)", v <= thr["q_flow1h"][0], ok)
    v, ok = col("funding")
    if np.isfinite(thr["q_funding"][0]):
        out["funding_high"] = ("funding rate high (top tenth): longs paying a lot", v >= thr["q_funding"][1], ok)
        out["funding_low"] = ("funding rate low (bottom tenth): shorts paying / longs cheap", v <= thr["q_funding"][0], ok)
    v, ok = col("hrs_to_econ")
    out["release_within_2h"] = ("a US high-impact release is due within 2 hours (calendar from May 2026 only)",
                                v <= 2.0, ok)
    v, ok = col("hrs_since_econ")
    out["release_last_2h"] = ("a US high-impact release printed in the last 2 hours (calendar from May 2026 only)",
                              v <= 2.0, ok)
    nxt = times + L.BAR                       # the open of the first bar of the move
    hm = nxt.hour * 100 + nxt.minute
    wk = nxt.dayofweek < 5
    allv = np.ones(len(times), dtype=bool)
    out["next_bar_1330_or_1430"] = ("the next 15m bar opens at 13:30 or 14:30 UTC on a weekday "
                                    "(US data releases / stock open)", wk & ((hm == 1330) | (hm == 1430)), allv)
    out["next_bar_top_of_hour"] = ("the next 15m bar opens on the hour", nxt.minute == 0, allv)
    out["next_bar_daily_open"] = ("the next 15m bar is the 00:00 UTC daily open", hm == 0, allv)
    return out


# ---------------------------------------------------------------- surprises
def decluster(move, thr, h, allowed):
    """Bars with |move| >= thr; overlapping bars (within h of a bigger one) are dropped. -> sorted positions."""
    a = np.abs(np.asarray(move, dtype=float))
    cand = np.where(np.isfinite(a) & (a >= thr) & allowed)[0]
    cand = cand[np.argsort(-a[cand], kind="stable")]
    taken = np.zeros(len(a), dtype=bool)
    keep = []
    for i in cand:
        if not taken[i]:
            keep.append(i)
            taken[max(0, i - h + 1):i + h] = True
    return np.sort(np.array(keep, dtype=np.int64))


def load_trades(asset, index):
    path = os.path.join(ENGINE_OUT, "replay", "trades_%s.csv" % asset)
    if not os.path.exists(path):
        return None
    t = pd.read_csv(path)
    tin = pd.to_datetime(t["time_in"], utc=True)
    tout = pd.to_datetime(t["time_out"], utc=True)
    t["pos_in"] = index.get_indexer(tin)
    t["pos_out"] = index.get_indexer(tout)
    t["decision_pos"] = t["pos_in"] - 1          # the call was made at the close of the bar before the fill
    return t


def load_journal():
    rows = []
    for p in sorted(glob.glob(os.path.join(JOURNAL_DIR, "*.jsonl"))):
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                rows.append({"asset": d.get("asset"), "close_time": pd.Timestamp(d.get("time"), tz="UTC"),
                             "position": d.get("position"), "action": d.get("action"),
                             "reason": d.get("reason"), "edge_pts": d.get("edge_pts")})
    return pd.DataFrame(rows)


def engine_side(trades, journal, asset, index, j):
    """Side held during bar j (the first bar of a move). -> (side, source, detail)."""
    if journal is not None and len(journal):
        close_j = index[j] + L.BAR
        hit = journal[(journal.asset == asset) & (journal.close_time == close_j)]
        if len(hit):
            r = hit.iloc[0]
            side = {"LONG": 1, "SHORT": -1}.get(r["position"], 0)
            dec = journal[(journal.asset == asset) & (journal.close_time == index[j])]
            det = ("live journal: %s at %s; decision at the surprise bar: %s (%s, edge %s pts)" % (
                r["position"], L.fmt_time(close_j),
                dec.iloc[0]["action"] if len(dec) else "?", dec.iloc[0]["reason"] if len(dec) else "?",
                dec.iloc[0]["edge_pts"] if len(dec) else "?"))
            return side, "live", det
    if trades is not None and len(trades):
        live = trades[(trades.pos_in <= j) & (trades.pos_out > j)]
        if len(live):
            r = live.iloc[0]
            return int(r["side"]), "replay", "replay trade %s from %s (%s), out %s (%s), %+.2f%%" % (
                "LONG" if r["side"] == 1 else "SHORT", L.fmt_time(index[int(r["pos_in"])]), r["why_in"],
                L.fmt_time(index[int(r["pos_out"])]), r["why_out"], r["pnl_pct"])
        if trades.pos_in.min() <= j <= trades.pos_out.max():
            return 0, "replay", "flat in the replay"
    return None, "none", "no engine record for this time"


def verdict(side, direction):
    if side is None:
        return "no record"
    if side == 0:
        return "flat (missed)"
    return "right side" if side == direction else "WRONG side"


# ---------------------------------------------------------------- lift
def lift_table(fl, slices, events_by_slice, cache=None):
    """fl: flags; slices: dict key -> bool mask of base bars; events_by_slice: key -> positions.
    cache: a dict reused across calls for the base rates. -> {flag: {slice: {k, n, share, base, lift, z}}}"""
    out = {}
    cache = {} if cache is None else cache
    for name, (_, x, ok) in fl.items():
        row = {}
        for key, base in slices.items():
            if (name, key) not in cache:
                b = base & ok
                cache[(name, key)] = float(x[b].mean()) if b.any() else np.nan
            p0 = cache[(name, key)]
            ev = events_by_slice[key]
            ev = ev[ok[ev]]
            n = len(ev)
            k = int(x[ev].sum()) if n else 0
            share = k / n if n else np.nan
            with np.errstate(invalid="ignore", divide="ignore"):
                lift = share / p0 if p0 and p0 == p0 else np.nan
                z = (k - n * p0) / np.sqrt(n * p0 * (1 - p0)) if n and 0 < p0 < 1 else np.nan
            row[key] = {"k": k, "n": n, "share": _r(share, 4), "base": _r(p0, 4), "lift": _r(lift, 3), "z": _r(z, 2)}
        out[name] = row
    return out


def passes(row, keys, direction):
    vals = [row[k] for k in keys]
    if any(v["lift"] is None or v["z"] is None for v in vals):
        return False
    if direction > 0:
        return all(v["lift"] > 1 and v["k"] >= MIN_K and v["z"] >= Z_MIN for v in vals)
    return all(v["lift"] < 1 and v["n"] * (v["base"] or 0) >= MIN_K and v["z"] <= -Z_MIN for v in vals)


def _r(x, nd=4):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if not np.isfinite(x) else round(x, nd)


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--days", type=int, default=None, help="list the surprises of the last N days (daily report)")
    ap.add_argument("--placebo", type=int, default=30, help="placebo runs with surprise times slid (default 30)")
    ap.add_argument("--out", default=L.OUT_DIR)
    a = ap.parse_args(argv)
    t0 = time.time()
    recent_days = a.days or 30
    journal = load_journal()
    groups = [(h, g) for h in HORIZONS for g in ("any", "up", "down")]

    per_asset = {}
    surprises = []
    worst_rows, entry_flags_all, worst_flags_all = [], [], []
    for asset in CFG["assets"]:
        b = L.build(asset)
        df, f, st, half, thr = b["df"], b["f"], b["st"], b["half"], b["thr"]
        index = df.index
        mv = L.surprise_moves(df, f["atr1h"].values)
        fl = flags(f, st, thr, index)
        inwin = half > 0
        cut = {}
        ev = {}
        for h in HORIZONS:
            m = mv["m%d" % h].values
            cut[h] = float(np.nanquantile(np.abs(m[inwin]), TOP_Q))
            ev[h] = decluster(m, cut[h], h, inwin)
        slices = {"H1": half == 1, "H2": half == 2}
        ev_slices = {}
        for h, g in groups:
            e = ev[h]
            m = mv["m%d" % h].values
            if g == "up":
                e = e[m[e] > 0]
            elif g == "down":
                e = e[m[e] < 0]
            for hk in slices:
                ev_slices[(h, g, hk)] = e[half[e] == (1 if hk == "H1" else 2)]
        lifts = {}
        bcache = {}
        for h, g in groups:
            lifts["%d_%s" % (h, g)] = lift_table(fl, slices, dict((hk, ev_slices[(h, g, hk)]) for hk in slices), bcache)
        # chance a big move follows, per flag (all bars, not declustered)
        cond = {}
        for h in HORIZONS:
            big = np.abs(mv["m%d" % h].values) >= cut[h]
            okm = np.isfinite(mv["m%d" % h].values) & inwin
            cond[h] = dict((name, _r(big[x & ok & okm].mean() if (x & ok & okm).any() else np.nan, 4))
                           for name, (_, x, ok) in fl.items())
            cond[h]["__all__"] = _r(big[okm].mean(), 4)
        per_asset[asset] = {"cut_atr": cut, "events": dict((h, len(ev[h])) for h in HORIZONS),
                            "lifts": lifts, "cond": cond}

        # placebo: slide the surprise times (same offset for both coins via a shared seed)
        rng = np.random.RandomState(15)
        nwin = int(inwin.sum())
        w0 = int(np.argmax(inwin))
        plc = []
        for r in range(a.placebo):
            off = int(rng.randint(nwin // 10, nwin - nwin // 10))
            pl = {}
            for h, g in groups:
                e = ev_slices[(h, g, "H1")].tolist() + ev_slices[(h, g, "H2")].tolist()
                e = np.array(e, dtype=np.int64)
                e = w0 + (e - w0 + off) % nwin
                pl["%d_%s" % (h, g)] = lift_table(fl, slices, {"H1": e[half[e] == 1], "H2": e[half[e] == 2]}, bcache)
            plc.append(pl)
        per_asset[asset]["placebo"] = plc

        trades = load_trades(asset, index)
        c = df["close"].values
        jr = journal[journal.asset == asset] if len(journal) else None
        for h in HORIZONS:
            m = mv["m%d" % h].values
            for i in ev[h]:
                direction = 1 if m[i] > 0 else -1
                j = i + 1
                side, src, det = engine_side(trades, jr, asset, index, j) if j < len(index) else (None, "none", "")
                surprises.append({
                    "asset": asset, "pos": int(i), "horizon_bars": h,
                    "start_utc": L.fmt_time(index[i] + L.BAR), "end_utc": L.fmt_time(index[i + h] + L.BAR),
                    "move_atr": round(float(m[i]), 2), "move_pct": round(float((c[i + h] / c[i] - 1) * 100), 2),
                    "direction": "UP" if direction > 0 else "DOWN", "half": int(half[i]),
                    "state": dict((d, L.DIM_LABELS[d][int(st[d].values[i])] if st[d].values[i] >= 0 else None)
                                  for d in L.DIM_NAMES),
                    "readings": dict((k, _r(f[k].values[i], 4 if k in ("funding",) else 3)) for k in READ_COLS),
                    "precursors": [name for name, (_, x, ok) in fl.items() if ok[i] and x[i]
                                   and not name.split("=")[0] in L.DIM_NAMES],
                    "engine_side": {1: "LONG", -1: "SHORT", 0: "FLAT", None: None}[side], "engine_source": src,
                    "engine_detail": det, "engine_verdict": verdict(side, direction)})

        # the engine's worst calls vs all its calls
        if trades is not None:
            tr = trades[(trades.why_out != "OPEN") & (trades.decision_pos >= 0)].copy()
            lim = tr["pnl_pct"].quantile(WORST_Q)
            worst = tr[tr.pnl_pct <= lim]
            dpos = tr["decision_pos"].values.astype(int)
            wpos = worst["decision_pos"].values.astype(int)
            for name, (_, x, ok) in fl.items():
                entry_flags_all.append((asset, name, int((x & ok)[dpos].sum()), int(ok[dpos].sum())))
                worst_flags_all.append((asset, name, int((x & ok)[wpos].sum()), int(ok[wpos].sum())))
            for _, r in worst.iterrows():
                i = int(r["decision_pos"])
                worst_rows.append({
                    "asset": asset, "decision_utc": L.fmt_time(index[i] + L.BAR),
                    "exit_utc": L.fmt_time(index[int(r["pos_out"])]), "side": "LONG" if r["side"] == 1 else "SHORT",
                    "why_in": r["why_in"], "why_out": r["why_out"], "pnl_pct": round(float(r["pnl_pct"]), 2),
                    "bars_held": int(r["pos_out"] - r["pos_in"]),
                    "state": dict((d, L.DIM_LABELS[d][int(st[d].values[i])] if st[d].values[i] >= 0 else None)
                                  for d in L.DIM_NAMES),
                    "precursors": [name for name, (_, x, ok) in fl.items() if ok[i] and x[i]
                                   and not name.split("=")[0] in L.DIM_NAMES],
                    "readings": dict((k, _r(f[k].values[i], 3)) for k in READ_COLS)})
            per_asset[asset]["trades"] = {"closed": int(len(tr)), "worst_cut_pct": round(float(lim), 2),
                                          "worst_n": int(len(worst))}
        flag_text = dict((name, t) for name, (t, _, _) in fl.items())
        end_ts = b["end"]
        window = {"start": str(b["start"]), "mid": str(b["mid"]), "end": str(b["end"])}
        del b, df, f, st, mv, fl
        print("%s done (%.1fs, peak %s MB)" % (asset, time.time() - t0, L.peak_mb()))

    assets = list(per_asset)
    keys4 = [(asset, hk) for asset in assets for hk in ("H1", "H2")]

    def combined_row(gk, name, src):
        return dict(("%s %s" % (asset[:3], hk), src[asset][gk][name][hk]) for asset, hk in keys4)

    precursors, n_tests, real_pass = [], 0, 0
    for h, g in groups:
        gk = "%d_%s" % (h, g)
        for name in flag_text:
            row = combined_row(gk, name, dict((asset, per_asset[asset]["lifts"]) for asset in assets))
            usable = [v for v in row.values() if v["n"] and v["base"] is not None]
            if len(usable) < 4:
                continue
            n_tests += 2
            for direction in (1, -1):
                if passes(row, list(row), direction):
                    real_pass += 1
                    lifts = [v["lift"] for v in row.values()]
                    precursors.append({"group": gk, "flag": name, "text": flag_text[name],
                                       "more_or_less": "more often" if direction > 0 else "less often",
                                       "min_lift": min(lifts) if direction > 0 else max(lifts),
                                       "min_abs_z": min(abs(v["z"]) for v in row.values()),
                                       "chance_big_move": dict((asset, {"with": per_asset[asset]["cond"][h].get(name),
                                                                        "all_bars": per_asset[asset]["cond"][h]["__all__"]})
                                                               for asset in assets),
                                       "tests": row})
    plc_counts, plc_hits = [], {}
    for r in range(a.placebo):
        cnt = 0
        for h, g in groups:
            gk = "%d_%s" % (h, g)
            for name in flag_text:
                row = combined_row(gk, name, dict((asset, per_asset[asset]["placebo"][r]) for asset in assets))
                if len([v for v in row.values() if v["n"] and v["base"] is not None]) < 4:
                    continue
                for d in (1, -1):
                    if passes(row, list(row), d):
                        cnt += 1
                        plc_hits[(gk, name, d)] = plc_hits.get((gk, name, d), 0) + 1
        plc_counts.append(cnt)
    for p in precursors:
        d = 1 if p["more_or_less"] == "more often" else -1
        p["placebo_pass_share"] = round(plc_hits.get((p["group"], p["flag"], d), 0) / float(max(a.placebo, 1)), 3)
        p["robust"] = bool(p["placebo_pass_share"] <= 0.10)
    plc = np.array(plc_counts, dtype=float) if plc_counts else np.array([np.nan])
    luck = {"tests": n_tests, "passed": real_pass,
            "how_tests_are_counted": "%d precursors x %d surprise groups (1h and 4h; any, up, down) x 2 "
                                     "(more often / less often), where all four tests have data" % (len(flag_text), len(groups)),
            "placebo_runs": len(plc_counts), "placebo_mean": _r(plc.mean(), 2),
            "placebo_p95": _r(np.percentile(plc, 95), 1), "placebo_max": _r(plc.max(), 0),
            "robust_rule": "a passing precursor is 'robust' if it passed in at most 10% of the placebo runs itself",
            "rule": "lift on the same side of 1 in all four tests (BTC/ETH x first/second half), "
                    "at least %d surprise bars each, binomial |z| >= %.1f each" % (MIN_K, Z_MIN)}
    precursors.sort(key=lambda p: (p["more_or_less"] != "more often", not p["robust"], -p["min_abs_z"]))
    luck["passed_and_rarely_by_luck"] = sum(p["robust"] for p in precursors)

    # the engine's worst calls: pooled lift vs all its entries
    worst_lift = []
    for name in flag_text:
        e = [x for x in entry_flags_all if x[1] == name]
        w = [x for x in worst_flags_all if x[1] == name]
        ke, ne = sum(x[2] for x in e), sum(x[3] for x in e)
        kw, nw = sum(x[2] for x in w), sum(x[3] for x in w)
        if ne and nw and ke:
            p0 = ke / ne
            worst_lift.append({"flag": name, "text": flag_text[name], "worst_k": kw, "worst_n": nw,
                               "all_k": ke, "all_n": ne, "lift": round((kw / nw) / p0, 2),
                               "z": _r((kw - nw * p0) / np.sqrt(nw * p0 * (1 - p0)), 2) if 0 < p0 < 1 else None,
                               "per_coin": dict((x[0], "%d/%d" % (x[2], x[3])) for x in w)})
    worst_lift.sort(key=lambda r: -(r["z"] or 0))
    worst_rows.sort(key=lambda r: r["pnl_pct"])

    # recent surprises
    since = end_ts - pd.Timedelta(days=recent_days)
    recent = [s for s in surprises if pd.Timestamp(s["start_utc"].replace(" UTC", ""), tz="UTC") >= since]
    recent.sort(key=lambda s: -abs(s["move_atr"]))
    verdicts = {}
    for s in surprises:
        verdicts.setdefault(s["engine_verdict"], 0)
        verdicts[s["engine_verdict"]] += 1

    report = {
        "what": "Mind 15 surprise mining (charter L1). Leads, not proven edges.",
        "generated_utc": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M"),
        "window": window, "recent_days": recent_days, "assets": assets,
        "definition": {"surprise": "top %.0f%% of |close(t+h) - close(t)| / ATR14(1h at t), h = 4 and 16 bars, "
                                   "per coin, cut from %s on; overlapping bars merged" % ((1 - TOP_Q) * 100, window["start"][:10]),
                       "cut_atr": dict((asset, per_asset[asset]["cut_atr"]) for asset in assets),
                       "surprises_found": dict((asset, per_asset[asset]["events"]) for asset in assets)},
        "precursors": precursors, "luck": luck,
        "engine_at_surprises": verdicts,
        "engine_worst_calls": {"rule": "bottom %.0f%% of closed replay trades by P&L, per coin" % (WORST_Q * 100),
                               "per_coin": dict((asset, per_asset[asset].get("trades")) for asset in assets),
                               "precursor_lift_vs_all_entries": worst_lift[:15], "worst": worst_rows[:20]},
        "recent_surprises": recent,
        "all_surprises": surprises,
        "precursor_text": flag_text,
        "notes": ["Replay trades carry the time of the fill (next open); the call was made at the close of the "
                  "bar before, which is where readings are snapshotted.",
                  "The live journal covers only the days it has run; elsewhere the engine's side comes from the "
                  "replay trades (no per-bar odds: out/replay/store.pkl is deliberately not loaded).",
                  "The economic calendar on file starts May 2026, so the two release precursors cannot be tested "
                  "in the first half and are skipped by the four-test rule."],
    }
    report["runtime_s"] = round(time.time() - t0, 1)
    report["peak_mb"] = L.peak_mb()
    os.makedirs(a.out, exist_ok=True)
    stem = "surprises" if a.days is None else "surprises_%dd" % a.days
    with open(os.path.join(a.out, stem + ".json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, default=str)
    with open(os.path.join(a.out, stem + ".md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(render_md(report, a.days)) + "\n")
    print("\nSurprises of the last %d days (UTC, start of the move):" % recent_days)
    for s in sorted(recent, key=lambda s: s["start_utc"]):
        print("  %s  %s  %-4s %+6.2f ATR (%+.2f%%) over %dh  engine: %s" % (
            s["start_utc"], s["asset"][:3], s["direction"], s["move_atr"], s["move_pct"], s["horizon_bars"] // 4,
            s["engine_verdict"]))
    print("precursors passing all four tests: %d (placebo mean %s, max %s) of %d tests" % (
        real_pass, luck["placebo_mean"], luck["placebo_max"], n_tests))
    print("wrote %s in %.1fs, peak %s MB" % (os.path.join(a.out, stem + ".json/.md"), time.time() - t0, L.peak_mb()))
    return report


def render_md(rep, days):
    assets = rep["assets"]
    lk = rep["luck"]
    keys = ["%s %s" % (a[:3], h) for a in assets for h in ("H1", "H2")]
    md = ["# Surprise mining (charter L1)%s" % ("" if days is None else ": last %d days" % days), "",
          "Generated %s. History %s to %s; first half H1 to %s, second half H2 after. All times UTC." % (
              rep["generated_utc"], rep["window"]["start"][:10], rep["window"]["end"][:16], rep["window"]["mid"][:10]),
          "",
          "**These are leads, not proven edges.** Anything worth keeping goes into `research/HYPOTHESES.md` "
          "and is graded forward.", "",
          "## What counts as a surprise", "",
          "A move from the close of a 15m bar to the close 1 hour (4 bars) or 4 hours (16 bars) later, measured in "
          "units of the 1-hour ATR at the start, in the top 2% by size for that coin. Cut points: " + "; ".join(
              "%s %.2f ATR (1h) / %.2f ATR (4h)" % (a[:3], rep["definition"]["cut_atr"][a][4], rep["definition"]["cut_atr"][a][16])
              for a in assets) + ". Overlapping bars of one move count once. Found: " + "; ".join(
              "%s %d (1h) and %d (4h)" % (a[:3], rep["definition"]["surprises_found"][a][4], rep["definition"]["surprises_found"][a][16])
              for a in assets) + ".", "",
          "Where the engine stood when they started (replay and live): " + ", ".join(
              "%s %d" % (k, v) for k, v in sorted(rep["engine_at_surprises"].items(), key=lambda kv: -kv[1])) + ".", ""]
    rec = rep["recent_surprises"]
    title = "## The %d biggest surprises of the last %d days" % (min(10, len(rec)), rep["recent_days"])
    md += [title, ""]
    if not rec:
        md += ["None in this window (a 4-hour move needs 4 hours of bars after it, so the newest bars cannot be judged yet).", ""]
    else:
        md += ["| Start (UTC) | Coin | Move | Over | Before it | Engine |", "|---|---|---|---|---|---|"]
        for s in rec[:10]:
            st = s["state"]
            before = "%s, trend %s, flow %s, %s, last hour %s" % (
                st["vol"], st["trend"], st["flow"], st["place"], st["move"])
            if s["precursors"]:
                before += "; " + ", ".join(s["precursors"])
            md.append("| %s | %s | %s %+.1f ATR (%+.2f%%) | %dh | %s | %s: %s |" % (
                s["start_utc"].replace(" UTC", ""), s["asset"][:3], s["direction"], s["move_atr"], s["move_pct"],
                s["horizon_bars"] // 4, before, s["engine_verdict"], s["engine_detail"]))
        md.append("")
    md += ["## What repeats before surprises", "",
           "Lift = how many times more common a reading was at the close just before a surprise than at an "
           "ordinary bar (1.00 = no difference). k/n = surprise bars with the reading / all surprise bars. "
           "Listed only if it leans the same way in all four tests (BTC and ETH, H1 and H2). 'Chance' = how "
           "often a top-2% move followed any bar with this reading, against all bars.", "",
           "**Luck count:** %d tests (%s); %d passed (%s). With the surprise times slid to random places (%d "
           "placebo runs) %s passed on average (95th percentile %s, max %s). Big moves bunch together in "
           "volatile weeks, so the simple z-score overstates the evidence; the placebo keeps that bunching. "
           "Per reading, 'Luck' is the share of placebo runs in which that same reading passed too: "
           "**%d** passing readings passed in at most 10%% of placebo runs ('robust')." % (
               lk["tests"], lk["how_tests_are_counted"], lk["passed"], lk["rule"], lk["placebo_runs"],
               lk["placebo_mean"], lk["placebo_p95"], lk["placebo_max"], lk["passed_and_rarely_by_luck"]), ""]
    gname = {"4_any": "big 1h moves, either way", "4_up": "big 1h moves UP", "4_down": "big 1h moves DOWN",
             "16_any": "big 4h moves, either way", "16_up": "big 4h moves UP", "16_down": "big 4h moves DOWN"}
    more = [p for p in rep["precursors"] if p["more_or_less"] == "more often"]
    less = [p for p in rep["precursors"] if p["more_or_less"] == "less often"]
    for label, rows in (("More common before surprises", more), ("Less common before surprises", less)):
        md += ["### %s" % label, ""]
        if not rows:
            md += ["None passed.", ""]
            continue
        md += ["| Before | Reading | " + " | ".join("%s lift (k/n)" % k for k in keys) + " | Chance with / all bars | Luck |",
               "|---|---|" + "---|" * len(keys) + "---|---|"]
        for p in rows[:25]:
            cells = ["%.2f (%d/%d)" % (p["tests"][k]["lift"], p["tests"][k]["k"], p["tests"][k]["n"]) for k in keys]
            ch = "; ".join("%s %.1f%% / %.1f%%" % (a[:3], 100 * (p["chance_big_move"][a]["with"] or 0),
                                                 100 * (p["chance_big_move"][a]["all_bars"] or 0)) for a in assets)
            md.append("| %s | %s: %s | %s | %s | %.0f%% |" % (gname[p["group"]], p["flag"], p["text"], " | ".join(cells), ch,
                                                           100 * p["placebo_pass_share"]))
        md.append("")
    ew = rep["engine_worst_calls"]
    md += ["## The engine's worst calls (history replay)", "",
           "Rule: %s. %s. Readings are taken at the close where the call was made." % (
               ew["rule"], "; ".join("%s: %s closed trades, worst cut %s%%, %s worst" % (
                   a[:3], (ew["per_coin"][a] or {}).get("closed"), (ew["per_coin"][a] or {}).get("worst_cut_pct"),
                   (ew["per_coin"][a] or {}).get("worst_n")) for a in assets)), "",
           "Readings more common at the worst calls than at all the engine's entries (small samples: read "
           "as hints only):", "",
           "| Reading | Worst calls with it | All entries with it | Lift | z |", "|---|---|---|---|---|"]
    for r in ew["precursor_lift_vs_all_entries"][:10]:
        md.append("| %s: %s | %d/%d | %d/%d | %.2f | %s |" % (r["flag"], r["text"], r["worst_k"], r["worst_n"],
                                                            r["all_k"], r["all_n"], r["lift"], r["z"]))
    md += ["", "The ten worst:", "", "| Call (UTC) | Coin | Side | Why in -> why out | P&L | Held | State at the call |",
           "|---|---|---|---|---|---|---|"]
    for r in ew["worst"][:10]:
        st = r["state"]
        md.append("| %s | %s | %s | %s -> %s | %+.2f%% | %.1f h | %s, trend %s, %s, flow %s, %s, last hour %s%s |" % (
            r["decision_utc"].replace(" UTC", ""), r["asset"][:3], r["side"], r["why_in"], r["why_out"], r["pnl_pct"],
            r["bars_held"] / 4.0, st["vol"], st["trend"], st["session"], st["flow"], st["place"], st["move"],
            ("; " + ", ".join(r["precursors"])) if r["precursors"] else ""))
    md += ["", "## Limits", ""] + ["- " + n for n in rep["notes"]] + [
        "- Surprises are measured close to close; a fill at the next open would see slightly less.",
        "- Lift says a reading is more common before big moves; it does not say the move's direction "
        "unless the group is 'UP' or 'DOWN', and even then it is not a trade until graded forward.", ""]
    return md


if __name__ == "__main__":
    main()
