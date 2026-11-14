# -*- coding: utf-8 -*-
"""study -- one asset, development data only (bars before the sealed holdout): benchmarks, the three
walk-forward-selected families (H20, H22, H23), the fixed ladder (H21), and every number the report needs."""
import gc
import time

import numpy as np

from . import core, families

FAMS = {
    "H20": ("Family 1: filter stack on 15m bases (walk-forward selected)", families.F1, families.f1_keys, families.f1_name),
    "H22": ("Family 2: meta-labeling on daily momentum (walk-forward selected)", families.F2, families.f2_keys, families.f2_name),
    "H23": ("Family 3: core-satellite overlay (walk-forward selected)", families.F3, families.f3_keys, families.f3_name),
}
KEEP = ["total_return", "total_return_gross", "cagr", "sharpe", "sharpe_gross", "sortino", "max_drawdown", "calmar",
        "turnover_per_year", "trades", "years", "avg_holding_hours", "exposure", "cost_drag_per_year", "fee_per_year",
        "funding_per_year"]


def _m(st):
    out = dict((k, st[k]) for k in KEEP if k in st)
    out["trades_per_year"] = st["trades"] / st["years"] if st["years"] else 0.0
    return out


class Study:
    def __init__(self, asset, log=print, dev_only=True):
        self.asset, self.log = asset, log
        self.bars, self.fund = core.load(asset, dev_only=dev_only)
        self.feats = core.features(self.bars)
        self.mkt = core.Market(self.bars, self.fund)
        self.wins = core.windows(self.bars.index)
        self.oos = core.walkforward.oos_mask(self.bars.index, self.wins)
        close = self.bars["close"].values
        self.obj = dict((h, FAMS[h][1](self.feats, close)) for h in FAMS)
        log("%s: %d dev bars %s .. %s; %d folds, OOS %s .. %s" % (
            asset, len(self.bars), self.bars.index[0], self.bars.index[-1], len(self.wins),
            self.wins[0]["test_start"].date(), self.wins[-1]["test_end"].date()))

    # -------------------------------------------------------------- one strategy, every number
    def score(self, target, name, fees=(core.FEE_HEAD, core.FEE_ALT), rand=True):
        out = {"name": name}
        for fee in fees:
            ev, fr = core.evaluate(self.mkt, target, self.wins, fee)
            tag = "fee_%.2f%%" % (fee * 100)
            out[tag] = {"stitched": _m(ev["stitched"]),
                        "folds": [dict(window=w["window"], test_start=w["test_start"], test_end=w["test_end"],
                                       total_return=w["total_return"], sharpe=w["sharpe"], max_drawdown=w["max_drawdown"],
                                       trades=w["trades"]) for w in ev["windows"]]}
            if fee == core.FEE_HEAD:
                out["breakeven_fee"] = core.breakeven_fee(fr, self.oos)
                self._r_head = fr["r_net"].values.copy()
                pos_oos = fr["pos"].values[self.oos].copy()
            del fr
        if rand:
            rs = []
            for s in range(10):
                t = core.random_matched(self.bars.index, self.oos, pos_oos, s)
                ev, fr = core.evaluate(self.mkt, t, self.wins, core.FEE_HEAD)
                rs.append(ev["stitched"])
                del fr
            out["random_matched"] = {"sharpe_mean": float(np.mean([r["sharpe"] for r in rs])),
                                     "cagr_mean": float(np.mean([r["cagr"] for r in rs])),
                                     "total_return_mean": float(np.mean([r["total_return"] for r in rs])),
                                     "max_drawdown_mean": float(np.mean([r["max_drawdown"] for r in rs]))}
        return out

    def benchmarks(self):
        idx = self.bars.index
        bh = np.ones(len(idx))
        mom = core.benchmarks.momentum(self.bars["close"]).values
        res = {"buy_hold": self.score(bh, "Buy-and-hold", rand=False)}
        self.r_bh = self._r_head
        res["momentum"] = self.score(mom, "Momentum (daily, 30-day, long/short)", rand=False)
        self.r_mom = self._r_head
        rr = []
        for s in range(10):
            t = core.benchmarks.random_agent(idx, s)
            ev, fr = core.evaluate(self.mkt, t, self.wins, core.FEE_HEAD)
            rr.append(_m(ev["stitched"]))
            del fr
        res["random_daily"] = {"name": "Random agent, daily redraw (Phase 1), mean of 10",
                               "fee_0.10%": {"stitched": dict((k, float(np.mean([r[k] for r in rr]))) for k in rr[0])}}
        self.bench = res
        return res

    def significance(self, n_graded, n_trials):
        obs, p = core.boot_sharpe_diff(self._r_head[self.oos], self.r_bh[self.oos], self.bars.index[self.oos])
        dsr = core.deflated_sharpe(self._r_head[self.oos], n_trials)
        return {"sharpe_minus_bh": obs, "boot_p": p, "bonferroni_alpha": 0.05 / n_graded,
                "significant": bool(p <= 0.05 / n_graded), "deflated_sharpe_prob": dsr, "dsr_trials": n_trials}

    # -------------------------------------------------------------- a walk-forward-selected family
    def family(self, h):
        t0 = time.time()
        title, _, keyf, namef = FAMS[h]
        keys = keyf()
        ob = self.obj[h]
        self.log("%s %s: %d variants" % (self.asset, h, len(keys)))
        choice, expl = core.select(self.mkt, self.wins, keys, ob.target, log=self.log)
        tgt = core.stitch(self.bars.index, self.wins, choice, ob.target)
        res = self.score(tgt, title)
        res["_r"] = self._r_head
        res["variants"] = len(keys)
        res["selected"] = [namef(k) for k in choice]
        res["selected_keys"] = [list(k) if not isinstance(k, tuple) else [list(x) if isinstance(x, tuple) else x for x in k]
                                for k in choice]
        res["seconds"] = round(time.time() - t0, 1)
        # training-data exploration (labelled as such): per variant, mean over folds' train windows
        res["train_exploration"] = [{"variant": namef(k), "trades_per_year": float(expl["trades_per_year"][j].mean()),
                                     "sharpe": float(expl["sharpe"][j].mean()), "cagr": float(expl["cagr"][j].mean())}
                                    for j, k in enumerate(keys)]
        self.log("%s %s done in %.0fs" % (self.asset, h, time.time() - t0))
        gc.collect()
        return res, tgt

    def ladder(self):
        out = []
        ob = self.obj["H20"]
        for b, lvl, key in families.ladder():
            r = self.score(ob.target(key), "%s %s" % (b, lvl))
            r["base"], r["level"], r["variant"] = b, lvl, families.f1_name(key)
            r["_r"] = self._r_head
            out.append(r)
        return out
