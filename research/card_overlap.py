# -*- coding: utf-8 -*-
"""H54, duplicate cards (research/HYPOTHESES.md). PAPER ONLY. DESCRIPTIVE, IN-SAMPLE (development data only).

    python research/card_overlap.py --group fx              one market group (research server; one at a time per worker)
    python research/card_overlap.py --report --tag 20261117 merge the groups: research/out/card_overlap_<tag>.md/.json

Which voices (cards) say the same thing, and does one idea vote several times? No trading rule, no selection: nothing is
removed or merged on the strength of this.

The group stage reads the engine's evidence store data/evcache/<group>/<asset> READ-ONLY (evcache.AssetStore.load and
its mode "r" memory maps; never update / create / write / save_meta), copies the rows before 2025-11-11 00:00 UTC into
memory and lets go of the store. A store that is mid-rebuild or not on the engine's current version is not read: the
stage waits and tries again, then gives up and says so. The voices are walked forward weekly by
leanprep.walk_forward_cached (the engine's code) with the refits in a PRIVATE directory
research/out/card_overlap/fits/<group> (that function deletes refits it did not use, so it is never given the
engine's own directory). Nothing under data/ is written.

Measures (fixed in the registration before this file existed):
  pull      P(up) - P(down) of a voice's own odds, per session and asset
  speaks    at least one of the voice's readings is non-zero at the session
  M1        Spearman rho of two voices' pulls where both speak and have odds; per asset (>= 2,000 sessions), mean over assets
  M2        how often the two pulls have the same sign on those sessions
  M3        R(A in B) = mean over A's varying readings of the largest |Spearman rho| with any reading of B (X: no read = 0,
            ready sessions of the half); R(A, B) = min of the two directions; mean over assets
  s         a pair's similarity in a group: the smaller |M1| of the two halves, 0 when its sign flips
  S         across groups: the k-th largest s over the G groups where the pair is measured, k = ceil(0.75 G)
  duplicate S >= 0.85; near-duplicate 0.70 <= S < 0.85; clusters by average linkage at those thresholds
"""
import argparse
import gc
import json
import math
import os
import shutil
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research"))

OUT = os.path.join(ROOT, "research", "out", "card_overlap")
FITS = os.path.join(OUT, "fits")
CUT = "2025-11-11"            # development data only: rows strictly before 2025-11-11 00:00 UTC
SPLIT = "2023-06-07"          # first half before it, second half from it to the seal (the H6/H41/H44 split)
MIN_BOTH = 2000               # sessions a pair needs in an asset and half
DUP, NEAR = 0.85, 0.70
HALVES = ("first", "second")
GROUP_ORDER = ("crypto", "metals", "fx", "index", "energy")
NOT_CARDS = ("all", "base", "owner")


# =====================================================================================
# small pure pieces (tested by hand in the scratch checks; no engine import needed)
# =====================================================================================
def ranks(x):
    """Average ranks (ties share their mean rank), as a float array."""
    return pd.Series(np.asarray(x)).rank(method="average").to_numpy()


def pearson(a, b):
    a = a - a.mean()
    b = b - b.mean()
    d = math.sqrt(float((a * a).sum()) * float((b * b).sum()))
    return float((a * b).sum() / d) if d > 0 else float("nan")


def spearman(x, y):
    return pearson(ranks(x), ranks(y))


def rank_corr_matrix(M):
    """Spearman rho between the columns of M (rows = sessions). -> (C, varies): C[i, j] NaN where a column is constant."""
    R = np.array(pd.DataFrame(M).rank(method="average").to_numpy(dtype=np.float64))      # a writable copy
    R -= R.mean(axis=0, keepdims=True)
    sd = np.sqrt((R * R).sum(axis=0))
    varies = sd > 0
    R[:, varies] /= sd[varies]
    C = R.T @ R
    C[~varies, :] = np.nan
    C[:, ~varies] = np.nan
    return C, varies


def contained(C, varies, fa, fb):
    """R(A in B): the mean over A's varying readings of the largest |rho| with any (varying) reading of B."""
    fa = [i for i in fa if varies[i]]
    fb = [i for i in fb if varies[i]]
    if not fa or not fb:
        return float("nan")
    return float(np.abs(C[np.ix_(fa, fb)]).max(axis=1).mean())


def pair_similarity(h1, h2, signed=True):
    """The smaller |value| of the two halves; 0 when the sign differs (signed measures); None when a half is not measured."""
    if h1 is None or h2 is None or not (np.isfinite(h1) and np.isfinite(h2)):
        return None
    if signed and h1 * h2 < 0:
        return 0.0
    return float(min(abs(h1), abs(h2)))


def across_groups(values):
    """values: the pair's similarity in each group where it is measured. -> S = the k-th largest, k = ceil(0.75 G)."""
    v = sorted((x for x in values if x is not None), reverse=True)
    if not v:
        return 0.0, 0
    k = int(math.ceil(0.75 * len(v)))
    return float(v[k - 1]), len(v)


def clusters(names, sim, thr):
    """Average linkage: join the two clusters with the highest average pairwise similarity while it is >= thr
    (ties: the pair that comes first in `names`' order). sim: {(a, b): value}, missing = 0. -> clusters of >= 2,
    each in `names`' order."""
    pos = dict((v, i) for i, v in enumerate(names))

    def s(a, b):
        return sim.get((a, b), sim.get((b, a), 0.0)) or 0.0
    cl = [[v] for v in names]
    while True:
        best, pick = None, None
        for i in range(len(cl)):
            for j in range(i + 1, len(cl)):
                avg = sum(s(a, b) for a in cl[i] for b in cl[j]) / float(len(cl[i]) * len(cl[j]))
                if avg >= thr and (best is None or avg > best + 1e-12):
                    best, pick = avg, (i, j)
        if pick is None:
            break
        i, j = pick
        merged = sorted(cl[i] + cl[j], key=lambda v: pos[v])
        cl = [c for k, c in enumerate(cl) if k not in (i, j)]
        cl.append(merged)
        cl.sort(key=lambda c: pos[c[0]])
    return [c for c in cl if len(c) > 1]


# =====================================================================================
# the group stage (research server): read-only
# =====================================================================================
def open_stores(group, assets, log, tries=12, wait_s=75):
    """The group's stores, read-only, only when the group is on the engine's current version and not being built.
    -> (stores, group meta) or raises RuntimeError after `tries`."""
    from engine15 import evcache
    base = os.path.join(evcache.CACHE_DIR, group)
    sig = evcache.code_signature()
    why = "?"
    for k in range(tries):
        try:
            with open(os.path.join(base, "group.json"), encoding="utf-8") as fh:
                gm = json.load(fh)
        except (OSError, ValueError) as e:
            gm, why = None, "group.json unreadable (%s)" % e
        if gm is not None:
            if gm.get("building"):
                why = "the store is being built"
            elif gm.get("sig") != sig:
                raise RuntimeError("%s: the evidence store is not on the engine's current version (stored %s.., code %s..)"
                                   % (group, str(gm.get("sig"))[:10], sig[:10]))
            else:
                stores = dict((a, evcache.AssetStore(os.path.join(base, a))) for a in assets)
                if all(st.load() for st in stores.values()):
                    return stores, gm
                why = "a store file is being rewritten"
        log("%s: %s; waiting %ds (try %d of %d)" % (group, why, wait_s, k + 1, tries))
        time.sleep(wait_s)
    raise RuntimeError("%s: the evidence store could not be read (%s)" % (group, why))


def snapshot(group, assets, log):
    """Rows before the cut copied into memory: times, X (float64), ready, per asset. The store is let go afterwards.
    If the store changed hands while it was being copied (a rebuild), the copy is taken again."""
    from engine15 import evcache
    for attempt in range(6):
        stores, gm = open_stores(group, assets, log)
        try:
            t_ms = stores[assets[0]].times_ms()
            for a in assets[1:]:
                if not np.array_equal(stores[a].times_ms(), t_ms):
                    raise RuntimeError("timelines differ")
            times_full = pd.DatetimeIndex(pd.to_datetime(t_ms, unit="ms", utc=True))
            n = int(times_full.searchsorted(pd.Timestamp(CUT, tz="UTC")))
            X = dict((a, np.ascontiguousarray(np.asarray(stores[a].X()[:n]), dtype=np.float64)) for a in assets)
            ready = dict((a, np.array(stores[a].ready()[:n], dtype=bool)) for a in assets)
            atr = {}
            for a in assets:
                m = stores[a].meta
                spec = dict((c[0], c) for c in m["cols"])["atr1h"]
                atr[a] = np.array(stores[a].mm(spec[1])[spec[2], :n])       # in its stored dtype, as the engine reads it
            features = list(stores[assets[0]].meta["features"])
        except Exception as e:                                   # a file swapped under the read: try again later
            log("%s: read interrupted (%s); again in 60s" % (group, e))
            for st in stores.values():
                st._mm = {}
            time.sleep(60)
            continue
        for st in stores.values():
            st._mm = {}                                          # drop the read-only maps (never close(): it flushes)
        gc.collect()
        with open(os.path.join(evcache.CACHE_DIR, group, "group.json"), encoding="utf-8") as fh:
            gm2 = json.load(fh)
        if gm2.get("building") or gm2.get("sig") != gm.get("sig") or gm2.get("n", 0) < gm.get("n", 0):
            log("%s: the store was rebuilt during the copy; again in 60s" % group)
            time.sleep(60)
            continue
        return {"times": times_full[:n], "n": n, "X": X, "ready": ready, "atr1h": atr, "features": features,
                "store": {"sig": gm.get("sig"), "updated_utc": gm.get("updated_utc"), "n": gm.get("n")}}
    raise RuntimeError("%s: no stable copy of the store" % group)


def run_group(group, log):
    from engine15 import data, evidence, labels, leanprep, model
    from engine15.config import CFG, voting_for
    t0 = time.time()
    assets = list(dict(CFG["universes"])[group])
    snap = snapshot(group, assets, log)
    times, n = snap["times"], snap["n"]
    if snap["features"] != list(evidence.FEATURES):
        raise RuntimeError("%s: the store's feature list is not the engine's" % group)
    log("%s: %d rows before %s copied (%s .. %s), %d readings, %.0fs" % (
        group, n, CUT, str(times[0])[:16], str(times[-1])[:16], len(snap["features"]), time.time() - t0))
    cfg = dict(CFG, assets=tuple(assets), voting=voting_for(group))
    if group in CFG.get("group_horizon", {}):
        cfg["horizon"] = CFG["group_horizon"][group]
    X, ready = snap["X"], snap["ready"]
    y, res = {}, {}
    for a in assets:
        b = data.load(a)
        b = b[b.index < pd.Timestamp(CUT, tz="UTC")].reindex(times)       # later bars dropped before grading
        if b["close"].isna().any():
            raise RuntimeError("%s: %d stored sessions have no bar" % (a, int(b["close"].isna().sum())))
        y[a], res[a] = labels.triple_barrier(b["open"].values.astype(float), b["high"].values.astype(float),
                                             b["low"].values.astype(float),
                                             (cfg["barrier_atr"] * pd.Series(snap["atr1h"][a])).values, cfg["horizon"])
        del b
    birth = int(times.searchsorted(pd.Timestamp(cfg["birth"], tz="UTC")))
    floor = int(times.searchsorted(pd.Timestamp(cfg.get("train_floor", cfg["birth"]), tz="UTC")))
    fits = os.path.join(FITS, group)
    assert os.path.abspath(fits).startswith(os.path.abspath(OUT))        # never the engine's fits directory
    probs, models, frep = leanprep.walk_forward_cached(X, ready, y, cfg, birth, min(floor, birth), n, fits)
    del models
    log("%s: voices walked from %s: %d refits (%d from the private cache), %.0fs" % (
        group, cfg["birth"], frep["refits"], frep["reused"], time.time() - t0))
    lo = birth
    VN = list(model.VOICE_NAMES)
    V = len(VN)
    tl = times[lo:n]
    first = np.asarray(tl < pd.Timestamp(SPLIT, tz="UTC"))
    hmask = {"first": first, "second": ~first}
    pulls, speaks, valid = {}, {}, {}
    for a in assets:
        P = probs[a].arr
        valid[a] = np.isfinite(P[:, 0, 0])
        pulls[a] = P[:, :, labels.UP] - P[:, :, labels.DOWN]
        Xa = X[a][lo:n]
        speaks[a] = np.stack([(np.abs(Xa[:, model._COLS[v]]).sum(axis=1) > 0) if model._COLS[v] else np.zeros(n - lo, bool)
                              for v in VN], axis=1)

    # ---- which voices are measured here
    applies = dict((v, any(evidence.voice_applies(v, a) for a in assets)) for v in VN)
    counts = dict((a, dict((h, (speaks[a] & (valid[a] & hmask[h])[:, None]).sum(axis=0)) for h in HALVES)) for a in assets)
    keep, excluded = [], {}
    for i, v in enumerate(VN):
        if v in NOT_CARDS:
            continue
        if not applies[v]:
            excluded[v] = "does not apply to this market"
            continue
        ok = any(all(counts[a][h][i] >= MIN_BOTH for h in HALVES) for a in assets)
        if not ok:
            excluded[v] = "speaks on fewer than %d sessions in a half (%s)" % (MIN_BOTH, ", ".join(
                "%s %d/%d" % (a, counts[a]["first"][i], counts[a]["second"][i]) for a in assets))
            continue
        keep.append(v)
    K = len(keep)
    kidx = [VN.index(v) for v in keep]
    log("%s: %d voices measured, %d left out" % (group, K, len(excluded)))

    # ---- M1 and M2: pulls, pairwise, per asset and half
    m1 = dict((h, np.full((K, K), np.nan)) for h in HALVES)
    m2 = dict((h, np.full((K, K), np.nan)) for h in HALVES)
    nb = dict((h, np.zeros((K, K))) for h in HALVES)
    for h in HALVES:
        acc1, acc2, cnt = np.zeros((K, K)), np.zeros((K, K)), np.zeros((K, K))
        for a in assets:
            base = valid[a] & hmask[h]
            own = [base & speaks[a][:, i] for i in kidx]
            own_n = [int(m.sum()) for m in own]
            own_rank = {}
            for p in range(K):
                for q in range(p + 1, K):
                    both = own[p] & own[q]
                    k = int(both.sum())
                    if k < MIN_BOTH:
                        continue
                    xp, xq = pulls[a][both, kidx[p]], pulls[a][both, kidx[q]]
                    if k == own_n[p]:                            # p speaks nowhere else: its ranks can be reused
                        if p not in own_rank:
                            own_rank[p] = ranks(pulls[a][own[p], kidx[p]])
                        rp = own_rank[p]
                    else:
                        rp = ranks(xp)
                    if k == own_n[q]:
                        if q not in own_rank:
                            own_rank[q] = ranks(pulls[a][own[q], kidx[q]])
                        rq = own_rank[q]
                    else:
                        rq = ranks(xq)
                    rho = pearson(rp, rq)
                    if not np.isfinite(rho):                     # a pull that does not vary: not measured
                        continue
                    nz = (xp != 0) & (xq != 0)
                    if not nz.any():
                        continue
                    agree = float((np.sign(xp[nz]) == np.sign(xq[nz])).mean())
                    acc1[p, q] += rho
                    acc2[p, q] += agree
                    cnt[p, q] += 1
                    nb[h][p, q] += k
            del own, own_rank
        ok = cnt > 0
        m1[h][ok] = acc1[ok] / cnt[ok]
        m2[h][ok] = acc2[ok] / cnt[ok]
        nb[h][ok] = nb[h][ok] / cnt[ok]
        for M in (m1[h], m2[h], nb[h]):
            iu = np.triu_indices(K, 1)
            M[(iu[1], iu[0])] = M[iu]
        log("%s: pull overlap, %s half: %d pairs measured (%.0fs)" % (group, h, int(ok.sum()), time.time() - t0))

    # ---- M3: readings as the voices see them (X: no read = 0), ready sessions of the half, per asset
    r_in = dict((h, np.full((K, K), np.nan)) for h in HALVES)
    for h in HALVES:
        acc, cnt = np.zeros((K, K)), np.zeros((K, K))
        for a in assets:
            rows = np.flatnonzero(ready[a][lo:n] & hmask[h]) + lo
            if len(rows) < MIN_BOTH:
                continue
            C, varies = rank_corr_matrix(X[a][rows])
            for p in range(K):
                for q in range(K):
                    if p == q:
                        continue
                    r = contained(C, varies, model._COLS[keep[p]], model._COLS[keep[q]])
                    if np.isfinite(r):
                        acc[p, q] += r
                        cnt[p, q] += 1
            del C
            gc.collect()
        ok = cnt > 0
        r_in[h][ok] = acc[ok] / cnt[ok]
        log("%s: reading overlap, %s half done (%.0fs)" % (group, h, time.time() - t0))
    del X
    gc.collect()

    # ---- the say of each current voter, as the engine forms it
    trust = leanprep.trust_tail(probs, y, res, cfg, lo, n)
    votes = np.array([1.0 if v in cfg["voting"] else 0.0 for v in VN])
    trust = trust * votes
    trust = trust / trust.sum(axis=1, keepdims=True)
    trust = model.cap_shares(trust, cfg.get("trust_cap"))
    voters = [v for v in VN if v in cfg["voting"]]
    say = dict((v, dict((h, []) for h in HALVES)) for v in voters)
    for a in assets:
        w = trust * speaks[a]
        tot = w.sum(axis=1, keepdims=True)
        w = np.where(tot > 0, w / np.where(tot > 0, tot, 1.0), trust)
        w = model.cap_shares(w, cfg.get("trust_cap"))
        for h in HALVES:
            m = valid[a] & hmask[h]
            if m.any():
                mean = w[m].mean(axis=0)
                for v in voters:
                    say[v][h].append(float(mean[VN.index(v)]))
        del w
    say = dict((v, dict((h, round(float(np.mean(x)), 4) if x else None) for h, x in d.items())) for v, d in say.items())

    # ---- context: how large the pulls are, how often each voice speaks
    size, talk = {}, {}
    for v, i in zip(keep, kidx):
        size[v], talk[v] = {}, {}
        for h in HALVES:
            ms, ts = [], []
            for a in assets:
                base = valid[a] & hmask[h]
                sp = base & speaks[a][:, i]
                if sp.any():
                    ms.append(float(np.abs(pulls[a][sp, i]).mean() * 100))
                if base.any():
                    ts.append(float(sp.sum()) / float(base.sum()))
            size[v][h] = round(float(np.mean(ms)), 3) if ms else None
            talk[v][h] = round(float(np.mean(ts)), 4) if ts else None

    card_of, shown = {}, {}
    for title, vs in evidence.CARDS.items():
        for v in vs:
            card_of[v] = title
            shown[v] = title if len(vs) == 1 else "%s: %s" % (title, evidence.GROUPS[v][0] if v in evidence.GROUPS else v)

    def mat(M, nd=4):
        return [[None if not np.isfinite(x) else round(float(x), nd) for x in row] for row in M]
    out = {"group": group, "assets": assets, "engine_version": CFG["version"], "store": snap["store"], "rows": int(n),
           "cut": CUT, "split": SPLIT, "window": [str(tl[0])[:16], str(tl[-1])[:16]], "min_both": MIN_BOTH,
           "sessions": dict((a, dict((h, int((valid[a] & hmask[h]).sum())) for h in HALVES)) for a in assets),
           "voices": keep, "titles": dict((v, evidence.GROUPS[v][0]) for v in keep),
           "cards": dict((v, card_of.get(v, evidence.GROUPS[v][0])) for v in keep),
           "shown": dict((v, shown.get(v, evidence.GROUPS[v][0])) for v in keep),
           "n_readings": dict((v, len(model._COLS[v])) for v in keep), "excluded": excluded,
           "voters": [v for v in voters if v != "owner"], "say": say, "pull_size_pts": size, "speaks_share": talk,
           "m1": dict((h, mat(m1[h])) for h in HALVES), "m2": dict((h, mat(m2[h])) for h in HALVES),
           "n_both": dict((h, mat(nb[h], 0)) for h in HALVES), "r_in": dict((h, mat(r_in[h])) for h in HALVES),
           "refits": frep, "seconds": round(time.time() - t0, 1)}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "group_%s.json" % group), "w", encoding="utf-8") as fh:
        json.dump(out, fh)
    shutil.rmtree(fits, ignore_errors=True)                      # the private refits are temporary
    log("%s done in %.0fs: %d voices, %d voters" % (group, time.time() - t0, K, len(out["voters"])))
    return out


# =====================================================================================
# the report (anywhere: reads only this study's group files and Task 8's rating files)
# =====================================================================================
def load_groups():
    G = {}
    for g in GROUP_ORDER:
        p = os.path.join(OUT, "group_%s.json" % g)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                G[g] = json.load(fh)
    return G


def load_rating(tag):
    """Task 8's rating: {group: {voice: (rank, card, h1, h2, worse half, direction)}}."""
    out = {}
    d = os.path.join(ROOT, "research", "out", "card_rating_%s" % tag)
    for g in GROUP_ORDER:
        p = os.path.join(d, "card_rating_%s.json" % g)
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as fh:
            rows = json.load(fh)
        out[g] = {}
        for i, r in enumerate(rows, 1):
            for v in r[6].get("voices", []):
                out[g][v] = (i, r[0], r[2], r[3], r[6].get("worse_half"), r[5])
    return out


def group_sims(d):
    """-> (s {(a, b): pull similarity}, r {(a, b): reading similarity}, rin {(a, b): min over halves of R(a in b)})."""
    vs = d["voices"]
    s, r, rin = {}, {}, {}
    for i, a in enumerate(vs):
        for j, b in enumerate(vs):
            if i == j:
                continue
            x = [d["r_in"][h][i][j] for h in HALVES]
            if None not in x:
                rin[(a, b)] = min(x)
            if j < i:
                continue
            v = pair_similarity(d["m1"]["first"][i][j], d["m1"]["second"][i][j], signed=True)
            if v is not None:
                s[(a, b)] = v
            y = [d["r_in"][h][j][i] for h in HALVES]
            if None not in x and None not in y:
                r[(a, b)] = min(min(x[0], y[0]), min(x[1], y[1]))
    return s, r, rin


def report(tag, summary=None, log=print):
    G = load_groups()
    if not G:
        raise SystemExit("no group results under %s" % OUT)
    rating = load_rating(tag)
    groups = [g for g in GROUP_ORDER if g in G]
    order = []                                                   # the engine's voice order over all groups
    try:
        from engine15 import model
        order = [v for v in model.VOICE_NAMES if any(v in G[g]["voices"] for g in groups)]
    except Exception:
        for g in groups:
            order += [v for v in G[g]["voices"] if v not in order]
    title = {}
    for g in groups:
        for v in G[g]["voices"]:
            title.setdefault(v, G[g].get("shown", G[g]["cards"])[v])
    sims = dict((g, group_sims(G[g])) for g in groups)
    S, RS, pairs = {}, {}, []
    for i, a in enumerate(order):
        for b in order[i + 1:]:
            key = (a, b)
            sv = [sims[g][0].get(key, sims[g][0].get((b, a))) for g in groups]
            rv = [sims[g][1].get(key, sims[g][1].get((b, a))) for g in groups]
            S[key], gs = across_groups(sv)
            RS[key], gr = across_groups(rv)
            if gs or gr:
                pairs.append((a, b, S[key], gs, RS[key], gr))
    measured = sum(1 for p in pairs if p[3] > 0)

    def label(x):
        return "duplicate" if x >= DUP else ("near-duplicate" if x >= NEAR else "")

    def rlabel(x):
        return "reads alike" if x >= DUP else ("reads nearly alike" if x >= NEAR else "")

    def idx(g, v):
        return G[g]["voices"].index(v) if v in G[g]["voices"] else None

    def cell(g, a, b, what, h):
        i, j = idx(g, a), idx(g, b)
        if i is None or j is None:
            return None
        return G[g][what][h][i][j]

    def rate(g, v):
        return rating.get(g, {}).get(v)

    def best_member(g, members):
        have = [(rate(g, v)[4] or 0.0, -rate(g, v)[0], v) for v in members if rate(g, v) and v in G[g]["voices"]]
        if not have:
            return None
        w, _, v = max(have)
        return v, rate(g, v)

    def fmt(x, nd=2):
        return "-" if x is None else "%.*f" % (nd, x)

    def name(v):
        return "%s (`%s`)" % (title.get(v, v), v)

    res = {"tag": tag, "groups": groups, "cut": CUT, "split": SPLIT, "thresholds": {"duplicate": DUP, "near": NEAR},
           "pairs_measured": measured, "voices": order, "titles": title,
           "group_meta": dict((g, dict((k, G[g][k]) for k in ("assets", "engine_version", "store", "rows", "window",
                                                                "sessions", "voices", "excluded", "voters", "say",
                                                                "pull_size_pts", "speaks_share", "refits", "seconds")))
                              for g in groups)}
    L = ["# Duplicate cards (H54): which cards say the same thing, and does one idea vote several times?", "",
         "Tag %s. Engine %s. DESCRIPTIVE, in-sample history before the sealed holdout (%s); halves split at %s. "
         "Registered in research/HYPOTHESES.md (H54) before this code existed. **Nothing here removes, merges or "
         "re-weights a card: that is a new engine version and the owner's decision.** A high overlap says two cards lean "
         "together; it does not say either of them is right, and it proves no edge." % (
             tag, G[groups[0]]["engine_version"], CUT, SPLIT), ""]
    if summary and os.path.exists(summary):
        with open(summary, encoding="utf-8") as fh:
            L += [fh.read().rstrip(), ""]
    L += ["## How it was measured", "",
          "- Groups: %s. %s" % (", ".join("%s (%s; %d rows, sessions %s .. %s)" % (
              g, ", ".join(G[g]["assets"]), G[g]["rows"], G[g]["window"][0], G[g]["window"][1]) for g in groups),
              "Not run: %s." % ", ".join(g for g in GROUP_ORDER if g not in G) if len(groups) < len(GROUP_ORDER) else ""),
          "- A voice's **pull** = P(up) - P(down) of its own odds, formed as the engine forms them (weekly refits walked "
          "forward from 2020). **Pull overlap** = Spearman rank correlation of two voices' pulls on the sessions where both "
          "speak (at least %d a half and asset); **agreement** = how often the two pulls have the same sign there; "
          "**reading overlap** = how closely each reading of one card is matched by some reading of the other (mean of the "
          "best |rank correlation|, the weaker direction)." % MIN_BOTH,
          "- In a group a pair's similarity is the weaker half's |pull overlap| (0 if its sign flips). Across groups: the "
          "value reached in at least three quarters of the groups where both cards are measured. **Duplicate: >= %.2f. "
          "Near-duplicate: >= %.2f.** Clusters: average linkage at those thresholds." % (DUP, NEAR),
          "- Pairs measured: %d (across %d voices). No significance test is run; the thresholds are conventions fixed "
          "before looking." % (measured, len(order)), ""]

    # ---- 1. pairs at or above 0.70
    top = sorted([p for p in pairs if p[2] >= NEAR], key=lambda p: -p[2])
    res["pairs"] = []
    L += ["## 1. Pairs that vote alike (pull overlap at or above %.2f across groups)" % NEAR, ""]
    if top:
        L += ["Per group: pull overlap 1st half / 2nd half (agreement % in the weaker half), then reading overlap of the "
              "weaker half.", "",
              "| card A | card B | S | label | groups | " + " | ".join(groups) + " | readings |",
              "|---|---|---|---|---|" + "---|" * len(groups) + "---|"]
    else:
        L += ["None.", ""]
    for a, b, s, gs, rs, gr in top:
        cells, pg = [], {}
        for g in groups:
            x1, x2 = cell(g, a, b, "m1", "first"), cell(g, a, b, "m1", "second")
            if x1 is None or x2 is None:
                cells.append("-")
                continue
            ag = [cell(g, a, b, "m2", h) for h in HALVES]
            rr = sims[g][1].get((a, b), sims[g][1].get((b, a)))
            cells.append("%s / %s (%s%%)%s" % (fmt(x1), fmt(x2), "-" if None in ag else "%.0f" % (min(ag) * 100),
                                              "" if rr is None else ", r %.2f" % rr))
            pg[g] = {"m1": [x1, x2], "m2": ag, "reading": rr}
        L.append("| %s | %s | %.2f | %s | %d | %s | %s |" % (name(a), name(b), s, label(s), gs, " | ".join(cells),
                                                           ("%.2f %s" % (rs, rlabel(rs))).strip() if gr else "-"))
        res["pairs"].append({"a": a, "b": b, "S": round(s, 4), "label": label(s), "groups_measured": gs,
                             "reading_S": round(rs, 4), "reading_label": rlabel(rs), "per_group": pg})
    L.append("")

    # ---- 1b. pairs that read alike but do not vote alike
    ronly = sorted([p for p in pairs if p[4] >= NEAR and p[2] < NEAR], key=lambda p: -p[4])
    res["reads_alike_only"] = [{"a": a, "b": b, "reading_S": round(rs, 4), "S": round(s, 4), "groups": gr}
                               for a, b, s, gs, rs, gr in ronly]
    L += ["## 2. Pairs that READ alike (reading overlap at or above %.2f) but whose votes overlap less than %.2f" % (NEAR, NEAR), ""]
    if ronly:
        L += ["| card A | card B | reading overlap | label | pull overlap S |", "|---|---|---|---|---|"]
        for a, b, s, gs, rs, gr in ronly:
            L.append("| %s | %s | %.2f | %s | %.2f |" % (name(a), name(b), rs, rlabel(rs), s))
    else:
        L.append("None.")
    L.append("")

    # ---- contained in
    cont = []
    for a in order:
        for b in order:
            if a == b:
                continue
            v, k = across_groups([sims[g][2].get((a, b)) for g in groups])
            if k and v >= DUP:
                cont.append((a, b, v, k))
    res["contained"] = [{"a": a, "b": b, "value": round(v, 4), "groups": k} for a, b, v, k in cont]
    L += ["## 3. Cards whose readings are contained in another card (R(A in B) at or above %.2f in both halves)" % DUP, ""]
    if cont:
        L += ["| card A | is contained in card B | R(A in B) | groups |", "|---|---|---|---|"]
        for a, b, v, k in sorted(cont, key=lambda c: -c[2]):
            L.append("| %s | %s | %.2f | %d |" % (name(a), name(b), v, k))
    else:
        L.append("None.")
    L.append("")

    # ---- 4. clusters across groups
    res["clusters_across"] = {}
    L += ["## 4. Clusters across the groups", ""]
    for kind, sim in (("pull", S), ("reading", RS)):
        for thr in (DUP, NEAR):
            cl = clusters(order, sim, thr)
            res["clusters_across"]["%s_%.2f" % (kind, thr)] = cl
            L += ["**%s overlap, threshold %.2f (%s): %d cluster%s**" % (
                kind.capitalize(), thr, ("duplicates" if thr == DUP else "near-duplicates") if kind == "pull" else
                ("reads alike" if thr == DUP else "reads nearly alike"), len(cl), "" if len(cl) == 1 else "s"), ""]
            for k, c in enumerate(cl, 1):
                L.append("%d. %s" % (k, "; ".join(name(v) for v in c)))
                for g in groups:
                    if sum(1 for v in c if v in G[g]["voices"]) < 2:      # the cluster does not exist in this group
                        continue
                    bm = best_member(g, c)
                    if bm:
                        v, r = bm
                        L.append("   - %s: best rated %s (rank %d, worse half %s%%; halves %s / %s, %s)" % (
                            g, title.get(v, v), r[0], r[4], r[2], r[3], r[5]))
            L.append("")

    # ---- 5. per group: clusters and their share of the vote
    res["per_group"] = {}
    L += ["## 5. Per market group: clusters among its cards, and how much of the vote each holds", "",
          "Share of the say = the engine's voting weights on this history (trust over all voices, the group's voters "
          "only, the 40% cap, the silent-voice rule), mean over the sessions of each half. \"Voters\" excludes the "
          "owner's voice.", ""]
    for g in groups:
        d = G[g]
        vs, voters, say = d["voices"], d["voters"], d["say"]
        s_g, r_g, _ = sims[g]
        L += ["### %s (%s): %d cards measured, %d voters" % (g, ", ".join(d["assets"]), len(vs), len(voters)), "",
              "Voters and their share of the say (1st half / 2nd half): " + "; ".join(
                  "%s %s / %s" % (title.get(v, "`%s`" % v), "-" if say[v]["first"] is None else "%.0f%%" % (say[v]["first"] * 100),
                                 "-" if say[v]["second"] is None else "%.0f%%" % (say[v]["second"] * 100)) for v in voters) + ".", ""]
        pg = {"voters": voters, "clusters": {}}
        for kind, sim in (("pull", s_g), ("reading", r_g)):
            for thr in (DUP, NEAR):
                cl = clusters(vs, sim, thr)
                rows = []
                for c in cl:
                    vin = [v for v in c if v in voters]
                    sh = [sum(say[v][h] or 0.0 for v in vin) for h in HALVES]
                    bm = best_member(g, c)
                    rows.append({"members": c, "voters_in": vin, "say": [round(x, 4) for x in sh],
                                 "best": None if not bm else {"voice": bm[0], "rank": bm[1][0], "worse_half": bm[1][4]}})
                pg["clusters"]["%s_%.2f" % (kind, thr)] = rows
                multi = [r for r in rows if len(r["voters_in"]) >= 2]
                L += ["**%s overlap >= %.2f: %d cluster%s, %d holding two or more voters**" % (
                    kind.capitalize(), thr, len(rows), "" if len(rows) == 1 else "s", len(multi)), ""]
                if rows:
                    L += ["| cluster | cards | voters in it | share of voters | share of the say (1st / 2nd) | best rated |",
                          "|---|---|---|---|---|---|"]
                    for k, r in enumerate(rows, 1):
                        b = r["best"]
                        L.append("| %d | %s | %s | %d of %d | %.0f%% / %.0f%% | %s |" % (
                            k, "; ".join("%s%s" % (title.get(v, v), " (votes)" if v in voters else "") for v in r["members"]),
                            ", ".join(title.get(v, v) for v in r["voters_in"]) or "-", len(r["voters_in"]), len(voters),
                            r["say"][0] * 100, r["say"][1] * 100,
                            "-" if not b else "%s (rank %d, %s%%)" % (title.get(b["voice"], b["voice"]), b["rank"], b["worse_half"])))
                    L.append("")
        # how many separate ideas vote: voters after joining those in one near-duplicate cluster
        near = pg["clusters"]["pull_%.2f" % NEAR]
        joined = sum(len(r["voters_in"]) - 1 for r in near if len(r["voters_in"]) >= 2)
        pg["separate_voting_ideas_near"] = len(voters) - joined
        dupc = pg["clusters"]["pull_%.2f" % DUP]
        pg["separate_voting_ideas_dup"] = len(voters) - sum(len(r["voters_in"]) - 1 for r in dupc if len(r["voters_in"]) >= 2)
        L += ["Separate voting ideas: %d voters make %d separate ideas at the near-duplicate threshold (%d at the "
              "duplicate threshold)." % (len(voters), pg["separate_voting_ideas_near"], pg["separate_voting_ideas_dup"]), ""]
        # voter-voter table
        L += ["Voter against voter, pull overlap 1st / 2nd half:", "",
              "| | " + " | ".join("`%s`" % v for v in voters if v in vs) + " |", "|---|" + "---|" * len([v for v in voters if v in vs])]
        vv = [v for v in voters if v in vs]
        for a in vv:
            row = []
            for b in vv:
                if a == b:
                    row.append("")
                    continue
                x1, x2 = cell(g, a, b, "m1", "first"), cell(g, a, b, "m1", "second")
                row.append("-" if x1 is None or x2 is None else "%s / %s" % (fmt(x1), fmt(x2)))
            L.append("| `%s` | %s |" % (a, " | ".join(row)))
        notin = [v for v in voters if v not in vs]
        if notin:
            L += ["", "Voters not measured here: " + "; ".join("%s (%s)" % (v, d["excluded"].get(v, "?")) for v in notin) + "."]
        if d["excluded"]:
            L += ["", "Left out of this group: " + "; ".join("`%s` (%s)" % kv for kv in sorted(d["excluded"].items())) + "."]
        L.append("")
        res["per_group"][g] = pg

    # ---- context: the size of the pulls
    L += ["## 6. Context: how hard each card pulls and how often it speaks", "",
          "Mean |pull| in points (P(up) - P(down), x100) on the sessions where the card speaks, 1st / 2nd half; a card "
          "whose pull is a fraction of a point barely moves the odds whatever it overlaps with.", "",
          "| card | " + " | ".join(groups) + " |", "|---|" + "---|" * len(groups)]
    for v in order:
        row = []
        for g in groups:
            z = G[g]["pull_size_pts"].get(v)
            row.append("-" if not z or z["first"] is None or z["second"] is None else "%.2f / %.2f%s" % (
                z["first"], z["second"], " (votes)" if v in G[g]["voters"] else ""))
        L.append("| %s | %s |" % (name(v), " | ".join(row)))
    L.append("")
    out_md = os.path.join(ROOT, "research", "out", "card_overlap_%s.md" % tag)
    with open(out_md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    with open(os.path.join(ROOT, "research", "out", "card_overlap_%s.json" % tag), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    log("report: %s (%d pairs measured, %d at or above %.2f)" % (out_md, measured, len(top), NEAR))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", choices=GROUP_ORDER)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--tag", default="20261117")
    ap.add_argument("--summary", default=None, help="a hand-written plain-English summary (markdown) to put on top")
    args = ap.parse_args()
    log = lambda m: print("[%s] %s" % (time.strftime("%H:%M:%S", time.gmtime()), m), flush=True)
    if args.group:
        try:
            os.nice(10)
        except Exception:
            pass
        run_group(args.group, log)
    if args.report:
        report(args.tag, args.summary, log)


if __name__ == "__main__":
    main()
