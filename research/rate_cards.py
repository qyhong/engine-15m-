# -*- coding: utf-8 -*-
"""Card rating per market group (the owner's list, item 4, 11 Nov 2026).

research/card_rating.json rates the cards for crypto only (research/exp_memory.py, on the replay store),
and the ten voting cards were chosen from it for every market. This script rates every card that applies
to ONE market group with the same method:

    per reading: on the calls graded up or down (the engine's triple barrier, the group's own horizon)
    where the required readings exist, from 2020-01-01 on, both/all assets of the group pooled, keep
    the reading's most extreme fifth (|x| at or above the 80th percentile of its non-zero values; a
    yes/no reading: every "yes") and score the accuracy of its sign as a call of direction in the first
    and in the second half of history (halves split at the median graded row, as exp_memory.py).
    steady = the smaller distance from 50% of the two halves when both lean the same way, else 0.
    per card: its steadiest reading. combined score = 50 + steady = the worse half's accuracy in the
    reading's own direction ("with" its sign, or "against" it). Ties (steady is rounded to 0.1) go to the
    card whose two halves are further from 50% in total.

Writes research/out/card_rating_<group>.json (rows of card_rating.json's shape, [card, reading, 1st half,
2nd half, steady, direction], each with a 7th element of detail: worse half, voices, per-asset halves),
research/out/card_rating_<group>.md, and the group's voting choice into research/out/voting_by_group.json
(top ten cards by the combined score with a worse half above 50.5%; at least the three best; the owner).

DIFFERENCES FROM exp_memory.py. Evidence is built here from the bars in chunks (--chunk-months, 3) with
--warm-days (300) of warm-up, not read from out/replay/store.pkl (memory); readings whose warm-up is
longer than 300 days (the weekly trend's slowest parts) are read with less history. Readings are kept
as float32. History runs to the last bar on disk, so crypto's rating can differ from card_rating.json.
All of this history has been looked at before: a rating can rank cards, never prove an edge.

    py -3 research/rate_cards.py --group metals          (one group at a time: memory)
"""
import argparse
import ctypes
import gc
import json
import os
import shutil
import sys
import tempfile
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine15 import data, evidence, journal, labels, livefeeds  # noqa: E402
from engine15.config import CFG  # noqa: E402

OUT = os.path.join(ROOT, "research", "out")
START = pd.Timestamp(CFG["birth"], tz="UTC")
TOP_N = 10            # the ten best cards vote (owner, 10 Nov 2026)
FLOOR_STEADY = 0.5    # ... but only cards whose worse half is above 50.5%
MIN_KEEP = 3          # ... and never fewer than the three best
MIN_HALF = 200        # graded extreme rows a half needs (exp_memory.py)
MIN_FREE_MB = 1200


# ------------------------------------------------------------------ memory and priority
def free_mb():
    class MS(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    m = MS()
    m.dwLength = ctypes.sizeof(MS)
    try:
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return int(m.ullAvailPhys / 2 ** 20)
    except Exception:
        return None


def peak_mb():
    class PMC(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]
    c = PMC()
    c.cb = ctypes.sizeof(PMC)
    try:
        ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(c), c.cb)
        return int(c.PeakWorkingSetSize / 2 ** 20)
    except Exception:
        return None


def below_normal():
    try:
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    except Exception:
        pass


# ------------------------------------------------------------------ the method (exp_memory.py, per reading)
def is_yes_no(x):
    """exp_memory.py's test: a reading with at most three distinct values (sampled every 97th row) is yes/no."""
    return not len(np.unique(x[::97])) > 3


def halves(x, up, first, cut, min_half=MIN_HALF):
    """Accuracy of sign(x) as a call of direction on the extreme rows, in each half. -> (h1, h2, steady, dir)."""
    keep = (np.abs(x) >= cut) & (x != 0)
    if (keep & first).sum() < min_half or (keep & ~first).sum() < min_half:
        return (None, None, 0.0, "too little history")
    h = [float(((x[keep & m] > 0) == up[keep & m]).mean() * 100) for m in (first, ~first)]
    steady = min(abs(h[0] - 50), abs(h[1] - 50)) if (h[0] - 50) * (h[1] - 50) > 0 else 0.0
    return (round(h[0], 1), round(h[1], 1), round(steady, 1), "with" if h[0] > 50 else "against")


def rate_reading(x, up, first, asset_of=None, min_half=MIN_HALF):
    """One reading, pooled (exactly exp_memory.py) and, when asset_of is given, per asset with the pooled
    cut and the pooled halves. -> (pooled tuple or None if the reading barely speaks, {asset: tuple})."""
    if np.abs(x).sum() == 0 or (x != 0).mean() < 0.002:
        return None, {}
    cut = 0.0 if is_yes_no(x) else np.quantile(np.abs(x[x != 0]), 0.8)
    pooled = halves(x, up, first, cut, min_half)
    per = {}
    if asset_of is not None:
        for a in np.unique(asset_of):
            m = asset_of == a
            per[str(a)] = halves(x[m], up[m], first[m], cut, min_half)
    return pooled, per


def card_rows(feat, feat_asset, card_voices, assets, words=None):
    """feat: {reading: pooled tuple}; feat_asset: {reading: {asset: tuple}}; card_voices: {card: (applying
    voices, their readings)}. -> rows [card, reading, h1, h2, steady, direction, detail], best first."""
    words = words or {}
    rows = []
    for card, (voices, fs) in card_voices.items():
        fs = [f for f in fs if f in feat]
        detail = {"voices": list(voices), "worse_half": None, "reading_key": None, "per_asset": {}}
        if not fs:
            rows.append([card, None, None, None, 0.0, "no history yet", detail])
            continue
        best = max(fs, key=lambda f: feat[f][2])                 # the first steadiest, as exp_memory.py
        h1, h2, steady, how = feat[best]
        detail["reading_key"] = best
        detail["worse_half"] = round(50.0 + steady, 1) if h1 is not None else None
        for a in assets:
            same = feat_asset.get(best, {}).get(a)
            own = [f for f in fs if a in feat_asset.get(f, {})]
            ob = max(own, key=lambda f: feat_asset[f][a][2]) if own else None
            detail["per_asset"][a] = {
                "same_reading": list(same) if same else None,
                "own_best": [words.get(ob, ob)] + list(feat_asset[ob][a]) if ob else None}
        rows.append([card, words.get(best, best), h1, h2, steady, how, detail])
    rows.sort(key=rank_key)
    return rows


def rank_key(r):
    """Best first: the worse half (steady), then on a tie the two halves' total distance from 50%."""
    both = abs(r[2] - 50) + abs(r[3] - 50) if r[2] is not None and r[3] is not None else -1.0
    return (-(r[4] or 0.0), -both)


def choose_voting(rows, top=TOP_N, floor=FLOOR_STEADY, keep=MIN_KEEP):
    """-> (cards, voices): the top `top` cards by the combined score whose worse half is above 50 + floor;
    if fewer than `keep` pass, the `keep` best regardless. The owner's voice always votes."""
    ranked = sorted(rows, key=rank_key)
    cards = [r for r in ranked if (r[4] or 0.0) > floor][:top]
    if len(cards) < keep:
        cards = ranked[:keep]
    voices = []
    for r in cards:
        for v in r[6]["voices"] if len(r) > 6 else []:
            if v not in voices:
                voices.append(v)
    if "owner" not in voices:
        voices.append("owner")
    return [r[0] for r in cards], voices


# ------------------------------------------------------------------ evidence, in chunks, to disk
def scope(assets):
    """The cards that apply to the group, each with its applying voices and their readings."""
    shown = set(t for a in assets for t in evidence.cards_for(a))
    out = {}
    for card, voices in evidence.CARDS.items():
        if card not in shown:
            continue
        vs = [v for v in voices if v in evidence.GROUPS and any(evidence.voice_applies(v, a) for a in assets)]
        fs = []
        for v in vs:
            fs += [f for f in evidence.GROUPS[v][1] if f not in fs]
        out[card] = (vs, fs)
    return out


def build_to_disk(assets, feats, tmp, chunk_months, warm_days, log, end=None):
    """Evidence chunk by chunk; per asset and chunk the kept readings go to disk as a (readings, rows)
    float32 array. -> {"times", asset: {"ready", "open", "high", "low", "close", "atr1h", "files"}}."""
    crypto = CFG.get("crypto", CFG["assets"])
    bars = dict((a, data.load(a)) for a in assets)
    if end:
        bars = dict((a, df[df.index < pd.Timestamp(end, tz="UTC")]) for a, df in bars.items())
    funding = dict((a, data.load_funding(a) if a in crypto else None) for a in assets)
    live = dict((a, livefeeds.load_live(a)) for a in assets)
    last = min(df.index[-1] for df in bars.values())
    parts = dict((a, {"ready": [], "open": [], "high": [], "low": [], "close": [], "atr1h": [], "files": []}) for a in assets)
    times = []
    c0, k = START, 0
    while c0 <= last:
        c1 = c0 + pd.DateOffset(months=chunk_months)
        t0 = time.time()
        b = dict((a, df[(df.index >= c0 - pd.Timedelta(days=warm_days)) & (df.index < c1)]) for a, df in bars.items())
        if min(len(df) for df in b.values()) == 0:
            c0 = c1
            continue
        ev = evidence.build(b, funding, live)
        idx = None
        for a in assets:
            e = ev[a]
            keep = np.asarray(e.index >= c0)
            if idx is None:
                idx = e.index[keep]
            if not keep.any():
                continue
            ready = e[evidence.REQUIRED].notna().all(axis=1).values[keep]
            X = e[feats].astype(np.float32).to_numpy()[keep]
            X[np.isnan(X)] = 0.0                                   # "no read", as evidence.matrix
            path = os.path.join(tmp, "%s_%03d.npy" % (a, k))
            np.save(path, np.ascontiguousarray(X.T))
            del X
            p = parts[a]
            p["files"].append(path)
            p["ready"].append(ready)
            bb = b[a].loc[idx]
            for col in ("open", "high", "low", "close"):
                p[col].append(bb[col].values.astype(float))
            p["atr1h"].append(e["atr1h"].values[keep].astype(float))
        if idx is not None and len(idx):
            times.append(idx)
        del ev, b
        gc.collect()
        log("  evidence %s .. %s: %d sessions (%.0fs, peak %s MB, free %s MB)" % (
            str(c0)[:10], str(min(c1, last))[:10], 0 if idx is None else len(idx), time.time() - t0, peak_mb(), free_mb()))
        c0, k = c1, k + 1
    del bars
    gc.collect()
    st = {"times": times[0].append(times[1:]) if len(times) > 1 else times[0]}
    for a in assets:
        st[a] = dict((col, np.concatenate(v)) for col, v in parts[a].items() if col != "files")
        st[a]["files"] = parts[a]["files"]
        assert len(st[a]["close"]) == len(st["times"])
    return st


def column(st, a, j):
    return np.concatenate([np.load(f, mmap_mode="r")[j] for f in st[a]["files"]]).astype(np.float64)


# ------------------------------------------------------------------ one group
def run(group, chunk_months=3, warm_days=300, log=print, end=None):
    t0 = time.time()
    assets = list(dict(CFG["universes"])[group])
    cards = scope(assets)
    feats = []
    for _, fs in cards.values():
        feats += [f for f in fs if f not in feats]
    log("%s %s: %d cards, %d readings" % (group, assets, len(cards), len(feats)))
    tmp = tempfile.mkdtemp(prefix="rate_cards_%s_" % group)
    try:
        st = build_to_disk(assets, feats, tmp, chunk_months, warm_days, log, end=end)
        times = st["times"]
        horizon = CFG.get("group_horizon", {}).get(group, CFG["horizon"])
        masks, ups, orders, owners = {}, [], [], []
        for a in assets:
            s = st[a]
            y, _ = labels.triple_barrier(s["open"], s["high"], s["low"], CFG["barrier_atr"] * s["atr1h"], horizon)
            masks[a] = (y > 0) & s["ready"]
            ups.append(y[masks[a]] == labels.UP)
            orders.append(np.arange(len(times))[masks[a]])
            owners.append(np.full(int(masks[a].sum()), a, dtype=object))
        up, order, asset_of = np.concatenate(ups), np.concatenate(orders), np.concatenate(owners)
        first = order < np.median(order)
        split = times[int(np.median(order))]
        feat, feat_asset = {}, {}
        for j, f in enumerate(feats):
            x = np.concatenate([column(st, a, j)[masks[a]] for a in assets])
            pooled, per = rate_reading(x, up, first, asset_of)
            if pooled is not None:
                feat[f], feat_asset[f] = pooled, per
        rows = card_rows(feat, feat_asset, cards, assets, journal.WORDS)
        chosen, voices = choose_voting(rows)
        meta = {"group": group, "assets": assets, "window": [str(times[0])[:16], str(times[-1])[:16]],
                "split": str(split)[:16], "horizon": horizon, "graded_rows": int(len(up)),
                "graded_rows_by_asset": dict((a, int(masks[a].sum())) for a in assets),
                "up_pct": round(float(up.mean() * 100), 1), "seconds": round(time.time() - t0, 1),
                "peak_mb": peak_mb(), "voting_cards": chosen, "voting_voices": voices,
                "floor": "worse half > %.1f%%, top %d, at least %d" % (50 + FLOOR_STEADY, TOP_N, MIN_KEEP)}
        return rows, meta
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def write(group, rows, meta, out_dir=OUT):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "card_rating_%s.json" % group), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
    vpath = os.path.join(out_dir, "voting_by_group.json")
    allv = {}
    if os.path.exists(vpath):
        with open(vpath, encoding="utf-8") as fh:
            allv = json.load(fh)
    allv[group] = dict((k, meta[k]) for k in ("voting_cards", "voting_voices", "floor", "window", "split"))
    with open(vpath, "w", encoding="utf-8") as fh:
        json.dump(allv, fh, indent=1)
    L = ["# Card rating: %s (%s)" % (group, ", ".join(meta["assets"])), "",
         "Method of research/exp_memory.py: per card its steadiest raw reading (the sign of the reading in its most "
         "extreme fifth as a call of direction, on calls the triple barrier graded up or down), first half vs second "
         "half. Combined score = the worse half in the reading's own direction (50 + steady). In-sample history; "
         "a rating ranks cards, it proves no edge.", "",
         "- window %s .. %s UTC, halves split at %s; horizon %d sessions; %d graded rows (%s); up %.1f%%" % (
             meta["window"][0], meta["window"][1], meta["split"], meta["horizon"], meta["graded_rows"],
             ", ".join("%s %d" % kv for kv in meta["graded_rows_by_asset"].items()), meta["up_pct"]),
         "- voting (%s): %s" % (meta["floor"], ", ".join(meta["voting_cards"])),
         "- voting voices: %s" % ", ".join(meta["voting_voices"]),
         "- built in %ss, peak %s MB" % (meta["seconds"], meta["peak_mb"]), "",
         "| # | card | steadiest reading | 1st half | 2nd half | worse half | direction | " +
         " | ".join("%s (1st / 2nd)" % a for a in meta["assets"]) + " |",
         "|---|---|---|---|---|---|---|" + "---|" * len(meta["assets"])]
    for i, r in enumerate(rows, 1):
        d = r[6]
        per = []
        for a in meta["assets"]:
            s = (d["per_asset"].get(a) or {}).get("same_reading")
            per.append("%s / %s" % (s[0], s[1]) if s and s[0] is not None else "-")
        L.append("| %d | %s%s | %s | %s | %s | %s | %s | %s |" % (
            i, r[0], " (votes)" if r[0] in meta["voting_cards"] else "", r[1] or "-", r[2] if r[2] is not None else "-",
            r[3] if r[3] is not None else "-", d["worse_half"] if d["worse_half"] is not None else "-", r[5], " | ".join(per)))
    with open(os.path.join(out_dir, "card_rating_%s.md" % group), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", required=True, choices=[g for g, _ in CFG["universes"]])
    ap.add_argument("--chunk-months", type=int, default=3)
    ap.add_argument("--warm-days", type=int, default=300)
    ap.add_argument("--force", action="store_true", help="start with less than 1,200 MB free")
    args = ap.parse_args()
    below_normal()
    free = free_mb()
    if free is not None and free < MIN_FREE_MB and not args.force:
        print("only %s MB free (need %d): not starting" % (free, MIN_FREE_MB))
        sys.exit(2)
    log = lambda m: print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)
    rows, meta = run(args.group, args.chunk_months, args.warm_days, log=log)
    write(args.group, rows, meta)
    log("%s done in %ss, peak %s MB" % (args.group, meta["seconds"], meta["peak_mb"]))
    for r in rows[:15]:
        log("  %-40s %-34s %6s %6s %5s %s" % (r[0], r[1] or "-", r[2], r[3], r[4], r[5]))
    log("voting: %s" % meta["voting_voices"])


if __name__ == "__main__":
    main()
