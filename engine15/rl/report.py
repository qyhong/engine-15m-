# -*- coding: utf-8 -*-
"""report -- the Phase 1 report: flags, a plain-English summary and the markdown tables."""
import numpy as np


def _pct(x, d=1):
    return ("%+." + str(d) + "f%%") % (100.0 * x)


def _f(x, d=2):
    return ("%." + str(d) + "f") % x


def _window_flags(name, wins, fee):
    out = []
    lr = np.array([np.log1p(w["total_return"]) for w in wins])
    tot = lr.sum()
    pos_share = float((lr > 0).mean()) if len(lr) else 0.0
    if tot > 0 and lr.max() >= tot:
        w = wins[int(lr.argmax())]
        out.append("%s at %s: the stitched gain rests on one window (%s..%s, %s); without it the rest lose money."
                   % (name, fee, w["test_start"], w["test_end"], _pct(w["total_return"])))
    if len(lr) and (pos_share < 0.5) and tot > 0:
        out.append("%s at %s: positive overall but only %.0f%% of windows were positive." % (name, fee, 100 * pos_share))
    return out


def flags(res):
    out = []
    for fee, r in res["results"].items():
        for name in ("buy_hold", "momentum"):
            st = r[name]["stitched"]
            out += _window_flags(name, r[name]["windows"], fee)
            if st["total_return_gross"] > 0 and st["total_return"] <= 0:
                out.append("%s at %s: positive before costs (%s) but negative after (%s): costs decide it."
                           % (name, fee, _pct(st["total_return_gross"]), _pct(st["total_return"])))
        rs = r["random_seeds"]
        tr = [s["total_return"] for s in rs.values()]
        if min(tr) < 0 < max(tr):
            out.append("random at %s: the sign of the result depends on the seed (%s to %s)." % (fee, _pct(min(tr)), _pct(max(tr))))
        sh = np.array([s["sharpe"] for s in rs.values()])
        for name in ("buy_hold", "momentum"):
            s = r[name]["stitched"]["sharpe"]
            if s > sh.max():
                out.append("%s at %s: Sharpe %.2f is above every random seed (max %.2f)." % (name, fee, s, sh.max()))
            elif s < sh.min():
                out.append("%s at %s: Sharpe %.2f is below every random seed (min %.2f)." % (name, fee, s, sh.min()))
    gaps = res["data"]["bars"].get("gap_events", 0)
    if gaps:
        out.append("data: %d exchange gaps (%d missing bars) are reported, not filled; returns span them open to open."
                   % (gaps, res["data"]["bars"].get("missing_bars", 0)))
    return out


def summary_lines(res):
    fees = list(res["results"])
    lines = []
    for fee in fees:
        r = res["results"][fee]
        bh, mo, ra = r["buy_hold"]["stitched"], r["momentum"]["stitched"], r["random"]["stitched"]
        lines.append(
            "At %s a side, out of sample (%s to %s): buy-and-hold %s (Sharpe %.2f, max drawdown %.0f%%); "
            "daily 30-day momentum %s (Sharpe %.2f, %.0f trades a year, turnover %.0fx a year, cost drag %.0f%% a year); "
            "random agent %s on average over %d seeds (Sharpe %.2f +- %.2f)."
            % (fee.replace("fee_", ""), bh["test_start"], bh["test_end"], _pct(bh["total_return"], 0), bh["sharpe"],
               100 * bh["max_drawdown"], _pct(mo["total_return"], 0), mo["sharpe"], mo["trades"] / max(mo["years"], 1e-9),
               mo["turnover_per_year"], 100 * mo["cost_drag_per_year"], _pct(ra["total_return"]["mean"], 0),
               r["random"]["seeds"], ra["sharpe"]["mean"], ra["sharpe"]["sd"]))
    r0 = res["results"][fees[0]]
    bh = r0["buy_hold"]["stitched"]
    lines.append("Buy-and-hold before costs: %s; holding the perpetual long paid %.1f%% of equity a year in funding, "
                 "which is most of the gap between its gross and net results (spot would not pay it)."
                 % (_pct(bh["total_return_gross"], 0), 100 * bh["funding_per_year"]))
    mo = r0["momentum"]["stitched"]
    lines.append("Momentum before costs: %s (gross Sharpe %.2f). The gap to its net result is the cost of "
                 "its turnover." % (_pct(mo["total_return_gross"], 0), mo["sharpe_gross"]))
    lines.append("Buy-and-hold's number is BTC's drift over these years, not skill; the random agent shows what "
                 "costs and luck alone do to a strategy that trades once a day. No benchmark was trained or tuned; "
                 "the rules were written in the config before the first run.")
    return lines


COLS = [("total_return", "Net return", _pct), ("total_return_gross", "Gross return", _pct), ("cagr", "CAGR", _pct),
        ("sharpe", "Sharpe", _f), ("sortino", "Sortino", _f), ("max_drawdown", "Max DD", lambda x: "%.1f%%" % (100 * x)),
        ("calmar", "Calmar", _f), ("turnover_per_year", "Turnover/yr", lambda x: "%.0f" % x),
        ("avg_holding_hours", "Avg hold (h)", lambda x: "%.1f" % x),
        ("cost_drag_per_year", "Cost drag/yr", lambda x: "%.1f%%" % (100 * x)),
        ("funding_per_year", "Funding paid/yr", lambda x: "%+.1f%%" % (100 * x))]


def _stitched_table(r):
    head = "| Strategy | " + " | ".join(c[1] for c in COLS) + " |\n|---|" + "---|" * len(COLS) + "\n"
    rows = []
    for name in ("buy_hold", "momentum"):
        st = r[name]["stitched"]
        rows.append("| %s | " % name + " | ".join(fn(st[k]) for k, _, fn in COLS) + " |")
    ra = r["random"]["stitched"]
    rows.append("| random (mean of %d) | " % r["random"]["seeds"] + " | ".join(fn(ra[k]["mean"]) for k, _, fn in COLS) + " |")
    rows.append("| random (sd) | " + " | ".join(fn(ra[k]["sd"]).replace("+", "") for k, _, fn in COLS) + " |")
    rows.append("| random (min .. max) | " + " | ".join("%s .. %s" % (fn(ra[k]["min"]), fn(ra[k]["max"])) for k, _, fn in COLS) + " |")
    return head + "\n".join(rows) + "\n"


def _window_table(r):
    head = ("| # | Test window | B&H net | B&H Sharpe | Mom net | Mom gross | Mom Sharpe | Random net (mean +- sd) | Random Sharpe |\n"
            "|---|---|---|---|---|---|---|---|---|\n")
    rows = []
    for bh, mo, ra in zip(r["buy_hold"]["windows"], r["momentum"]["windows"], r["random"]["windows"]):
        rows.append("| %d | %s .. %s | %s | %.2f | %s | %s | %.2f | %s +- %.1f%% | %.2f |"
                    % (bh["window"], bh["test_start"], bh["test_end"], _pct(bh["total_return"]), bh["sharpe"],
                       _pct(mo["total_return"]), _pct(mo["total_return_gross"]), mo["sharpe"], _pct(ra["total_return"]),
                       100 * ra["total_return_sd"], ra["sharpe"]))
    return head + "\n".join(rows) + "\n"


def markdown(res):
    cfg, d = res["config"], res["data"]
    b = d["bars"]
    c = cfg["costs"]
    s = ["# RL Phase 1 report: benchmarks after costs, walk-forward out of sample", "",
         "Run `%s`, generated %s. BTCUSDT perpetual (Binance USD-M), 15-minute bars. Paper only." % (res["run_id"], res["generated_utc"]),
         "", "## Summary", ""]
    s += ["- " + x for x in res["summary"]]
    s += ["", "## Flags", ""]
    s += ["- " + x for x in res["flags"]] or ["- none"]
    s += ["", "## Data", "",
          "- Bars: %d, first %s, last %s (open times, UTC)." % (b["rows"], b["first_bar"], b["last_bar"]),
          "- Gaps: %d events, %d missing bars (reported, not filled). Largest: %s."
          % (b.get("gap_events", 0), b.get("missing_bars", 0),
             "; ".join("%s -> %s (%d bars)" % tuple(g) for g in b.get("largest_gaps", [])[:5]) or "none"),
          "- Cleaning: %d duplicates, %d pre-listing placeholder bars, %d OHLC-invalid bars dropped. %d zero-volume bars kept: "
          "Binance serves exchange downtime as flat no-trade bars rather than missing ones, so these are the series' real "
          "outages (e.g. %s)."
          % (b.get("duplicates_dropped", 0), b.get("pre_listing_bars_dropped", 0), b.get("ohlc_invalid_dropped", 0),
             b.get("zero_volume_bars", 0), ", ".join(b.get("zero_volume_examples", [])[:4]) or "none"),
          "- Funding: %s rows. Open interest: live only, OFF in backtests (free history ~30 days)." % d["funding"].get("rows"),
          "", "## Method", "",
          "- Decision at each bar's close, fill at the open of the next bar (delay %d bar). Returns open to open; equity compounds."
          % c["delay_bars"],
          "- Costs (one model, `engine15/rl/costs.py`): taker fee %.2f%% a side (also shown at %.2f%%), half-spread %.1f bps, "
          "slippage %.2f x per-bar realised vol (%d bars) x |trade|, funding on the position held at each settlement."
          % (100 * c["fee_side"], 100 * c["fee_side_alt"], c["half_spread_bps"], c["slippage_coef"], c["slippage_vol_window"]),
          "- Walk-forward: %d-month train, %d-month test, step %d months, %d test windows (%s .. %s). Benchmarks do not train; "
          "their target series is stitched over the test windows and backtested once, so positions carry across windows."
          % (cfg["walkforward"]["train_months"], cfg["walkforward"]["test_months"], cfg["walkforward"]["step_months"],
             len(res["windows"]), res["windows"][0]["test_start"], res["windows"][-1]["test_end"]),
          "- Sharpe and Sortino are annualised for 15m bars: 365 x 96 = 35,040 bars a year, risk-free 0.",
          "- Rules: buy-and-hold = +1 always; random = uniform draw from {-1, 0, +1} once a day at 00:00 UTC, seeds %s "
          "(both fixed before the first run). Momentum (frozen 11 Nov 2026, Phase 2 task 1, before any agent result): "
          "decide once a day at the 00:00 UTC bar close, fill at the next open, sign of the %d-day return, %s. It replaces "
          "Phase 1's sign-of-96-bar-return-at-every-close rule, which traded ~1,800 times a year (a straw man)."
          % (cfg["benchmarks"]["random"]["seeds"], cfg["benchmarks"]["momentum"]["lookback_days"],
             cfg["benchmarks"]["momentum"].get("sides", "long_short").replace("_", "/")), ""]
    for fee, r in res["results"].items():
        s += ["## Stitched out of sample, %s a side" % fee.replace("fee_", ""), "", _stitched_table(r)]
    for fee, r in res["results"].items():
        s += ["## Per test window, %s a side" % fee.replace("fee_", ""), "", _window_table(r)]
    s += ["Every metric for every window and seed is in `phase1_report.json`.", ""]
    return "\n".join(s)
